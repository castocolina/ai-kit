#!/usr/bin/env python3
"""Prompt renderer for the goal-prompt skill (GPS-01..04; SPEC R2, R3; D-12..D-15, D-25..D-28).

The template lives in ../assets/prompt-template.md, split into named sections by `=== NAME ===`
lines. `PromptTemplate` uses the rare delimiter `§§` so `$?`, `${PIPESTATUS[0]}` and JSON braces
stay literal, and `fill` substitutes strictly: a missing key is a GuardError, never a blank.
A file holds one block per ranked strategy, the recommended first. An autonomous block carries
the rails inline; every other block shares one `## Rails` section after the COPY TO HERE marker.
stdlib only.
"""

from __future__ import annotations

import functools
import os
import re
import string
import subprocess
import tempfile
import textwrap
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from gp_common import GuardError, is_machine_path, phase_key, scan_text, slugify, unique_path
from gp_scope import Plan
from gp_sections import (
    GSD_FAMILIES,
    LINE_CAP,
    TURN_FLOOR,
    Work,
    assemble_rails,
    fit_line,
    goal_block,
    loop_block,
    objective_cut,
    objective_text,
    plain_block,
    rail_sections,
    resolve_turn_cap,
    strategy_heading,
)

__all__ = [
    "FULL_GOAL_HEADING",
    "FULL_OBJECTIVE_HEADING",
    "GOAL_POINTER_THRESHOLD",
    "GOAL_STYLES",
    "Block",
    "BlockView",
    "PromptTemplate",
    "RenderContext",
    "build_blocks",
    "check_condition",
    "check_fields",
    "check_text",
    "choose_path",
    "fill",
    "load_template",
    "render",
    "write_atomic",
]

_TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "assets", "prompt-template.md"
)
_SECTION_RE = re.compile(r"^=== (\w+) ===$", re.MULTILINE)
HEADINGS = (
    "OBJECTIVE",
    "ROLE",
    "RULES FOR EVERY PLAN",
    "ORDER",
    "QUOTA",
    "DECISIONS",
    "SAFETY",
    "DONE WHEN",
    "CLEANUP",
    "STOP IF",
    "REPORT",
)
DELIMITER = "§§"
FENCE = "````"
OPEN_MARKER = "▼▼▼ COPY FROM HERE ▼▼▼"
CLOSE_MARKER = "▲▲▲ COPY TO HERE ▲▲▲"
SHARED_HEADING = "## Rails"
AUTONOMOUS_PREFIX = "/gsd-autonomous"
GOAL_CAP = 4000
GOAL_BUDGET = 1800
GOAL_POINTER_THRESHOLD = 1000  # an inline condition longer than this moves to `## Full goal`
GOAL_STYLES = ("auto", "inline", "pointer")
FULL_GOAL_HEADING = "## Full goal"
FULL_OBJECTIVE_HEADING = "## Full objective"
FULL_SECTION_RE = re.compile(r"\n(## Full (?:objective|goal))\n")
OBJECTIVE_POINTER_MARK = "section Full objective)"
FULL_GOAL_WIDTH = 100
INLINE_CAP = 7000
RULE_CAP = 60
WRAPPER_SENTENCES = 3
WRAPPER_SHARE = 0.15
UNIT_SENTENCE = "Unit tests alone never count as done."
GOAL_PREFIX = "/goal "
POINTER_PREFIX = "/goal read document `"
POINTER_LINE = (
    "/goal read document `{path}` at section `Full goal` and finish only when that section's "
    "DONE WHEN conditions hold"
)
POINTER_WARNING = (
    "goal form pointer: the /goal line points at section Full goal of the file; that the host "
    "follows /goal read document ... at section ... is unverified"
)
FLAG_RE = re.compile(r"--[A-Za-z]")
JEV_RE = re.compile(r"\bjev", re.IGNORECASE)
SKIP_RE = re.compile(r"skip.*test tier", re.IGNORECASE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
GSD_KINDS = ("gsd", "opengsd", "gsd-unproven")
GSD_SCOPE_KINDS = ("opengsd", "gsd-unproven", "both")
GIT_TIMEOUT = 20
WRAPPER_OPENGSD = (
    "This project is OpenGSD, so the run uses /gsd-autonomous with convergence. Paste the block "
    "between the markers into a fresh session in this repository."
)
WRAPPER_UNPROVEN = (
    "This project has GSD but no verified OpenGSD identity, so /gsd-autonomous is unverified "
    "here. Paste one block between the markers into a fresh session in this repository."
)
WRAPPER_BY_ID = {
    "goal": "The recommended block is one /goal condition that stops when DONE WHEN holds.",
    "loop": "The recommended block is a loop that keeps the work going until DONE WHEN holds.",
    "plain": "The recommended block is a plain paragraph that relies on the QUOTA A wake.",
}
PASTE_ONE = "Paste one block between the markers into a fresh session in this repository."


class PromptTemplate(string.Template):
    """`§§KEY` placeholders with upper-case keys; NOFLAG keeps the key pattern case-sensitive."""

    delimiter = "§§"
    idpattern = r"[A-Z][A-Z0-9_]*"
    flags = re.NOFLAG


@functools.lru_cache(maxsize=1)
def load_template() -> dict[str, str]:
    """Section name -> body, with the leading and trailing blank lines removed."""
    with open(_TEMPLATE_PATH, encoding="utf-8") as handle:
        parts = _SECTION_RE.split(handle.read())
    return {name: body.strip("\n") for name, body in zip(parts[1::2], parts[2::2], strict=True)}


def fill(name: str, values: Mapping[str, str]) -> str:
    """Render one template section. A missing key or an unknown section raises GuardError."""
    sections = load_template()
    if name not in sections:
        raise GuardError(f"unknown template section: {name}")
    try:
        return PromptTemplate(sections[name]).substitute(values)
    except KeyError as exc:
        raise GuardError(f"template key missing: {exc.args[0]}") from exc


def check_condition(text: str) -> None:
    """A `/goal` condition may hold at most GOAL_CAP code points (len of a str counts them)."""
    size = len(text)
    if size > GOAL_CAP:
        raise GuardError(f"/goal condition is {size} code points; the cap is {GOAL_CAP}")


def check_fields(answers: Mapping[str, Any], home: str) -> None:
    """Path fields must be repo-relative. Messages name the field, never the value."""
    output_dir = answers.get("output_dir")
    if output_dir and is_machine_path(str(output_dir), home):
        raise GuardError("field output_dir holds a machine path")
    work_set = answers.get("work_set") or {}
    if any(is_machine_path(str(path), home) for path in work_set.get("files") or []):
        raise GuardError("field work_set.files holds a machine path")
    if any(is_machine_path(str(path), home) for path in answers.get("mockups") or []):
        raise GuardError("field mockups holds a machine path")


def _fenced_blocks(lines: list[str]) -> tuple[list[list[str]], bool]:
    """Lines of each four-backtick block, and whether the last block was left open."""
    blocks: list[list[str]] = []
    current: list[str] = []
    inside = False
    for line in lines:
        if line == FENCE:
            if inside:
                blocks.append(current)
                current = []
            inside = not inside
        elif inside:
            current.append(line)
    return blocks, inside


def _sections(body: list[str]) -> dict[str, list[str]]:
    """Lines under each labeled heading of a block (the first line is excluded by the caller)."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in body:
        if line in HEADINGS:
            current = line
            sections[line] = []
        elif current is not None:
            sections[current].append(line)
    return sections


def _goal_problems(condition: str) -> list[str]:
    try:
        check_condition(condition)
    except GuardError as exc:
        return [str(exc)]
    if len(condition) > GOAL_BUDGET:
        return [f"/goal condition over the {GOAL_BUDGET}-character budget"]
    return []


def _rule_lines(body: list[str]) -> list[str]:
    return [line for line in body if line.strip() and line not in HEADINGS]


def _rule_problems(lines: list[str]) -> list[str]:
    rules = _rule_lines(lines)
    problems: list[str] = []
    if len(rules) > RULE_CAP:
        problems.append(f"more than {RULE_CAP} rule lines")
    if any(len(line) > LINE_CAP for line in rules):
        problems.append(f"rule line over {LINE_CAP} characters")
    return problems


def _section_problems(sections: dict[str, list[str]]) -> list[str]:
    problems: list[str] = []
    done = sections.get("DONE WHEN")
    if done is not None and not any(UNIT_SENTENCE in line for line in done):
        problems.append(f"DONE WHEN lacks '{UNIT_SENTENCE}'")
    gated = [*sections.get("DONE WHEN", []), *sections.get("STOP IF", [])]
    if any(JEV_RE.search(line) for line in gated):
        problems.append("jev inside DONE WHEN or STOP IF")
    return problems


def _flag_section(body: list[str]) -> str:
    """The heading above the first flag-like line ("" when none), so the refusal names a field."""
    heading = "the lines before the first heading"
    for line in body:
        if line in HEADINGS:
            heading = line
        elif FLAG_RE.search(line):
            return heading
    return ""


def _inline_problems(lines: list[str], opengsd_block: bool) -> list[str]:
    """The inline autonomous block: size, flags-only line 1, the rule caps and, for GSD scopes,
    all eleven sections."""
    body = lines[1:]
    problems: list[str] = []
    if len("\n".join(lines)) > INLINE_CAP:
        problems.append(f"OpenGSD block over {INLINE_CAP} characters")
    flagged = _flag_section(body)
    if flagged:
        problems.append(f"flag-like token after line 1 of the block, in {flagged}")
    problems += _rule_problems(body)
    if opengsd_block:
        sections = _sections(body)
        problems += [f"section missing: {name}" for name in HEADINGS if name not in sections]
    return problems


def _full_goal_lines(text: str) -> list[str] | None:
    """Lines of the `## Full goal` section after the COPY TO HERE marker; None when absent."""
    _, found, after = text.partition(CLOSE_MARKER)
    _, heading, body = after.partition(f"\n{FULL_GOAL_HEADING}\n")
    return body.split("\n") if found and heading else None


def _block_problems(lines: list[str], opengsd_block: bool) -> list[str]:
    problems: list[str] = []
    if lines and lines[0].startswith(AUTONOMOUS_PREFIX):
        problems += _inline_problems(lines, opengsd_block)
    if lines and lines[0].startswith(GOAL_PREFIX) and not lines[0].startswith(POINTER_PREFIX):
        problems += _goal_problems("\n".join([lines[0][len(GOAL_PREFIX) :], *lines[1:]]))
    return problems + _section_problems(_sections(lines[1:]))


def _shared_rails(text: str) -> list[str]:
    """Lines of the shared `## Rails` section after the COPY TO HERE marker; [] when absent."""
    _, found, after = text.partition(CLOSE_MARKER)
    _, heading, rails = after.partition(f"\n{SHARED_HEADING}\n")
    rails = FULL_SECTION_RE.split(rails)[0]
    return rails.split("\n") if found and heading else []


def _rails_problems(text: str) -> list[str]:
    lines = _shared_rails(text)
    if not lines:
        return []
    return _rule_problems(lines) + _section_problems(_sections(lines))


def _wrapper_problems(text: str) -> list[str]:
    """The prose before the COPY marker: at most three sentences and 15 percent of the file."""
    head, found, _ = text.partition(OPEN_MARKER)
    if not found:
        return []
    title, _, rest = head.partition("\n")
    wrapper = (rest if title.startswith("# ") else head).strip()
    problems: list[str] = []
    if wrapper and len(SENTENCE_SPLIT_RE.split(wrapper)) > WRAPPER_SENTENCES:
        problems.append("wrapper over three sentences")
    if len(wrapper) > WRAPPER_SHARE * len(text):
        problems.append("wrapper over 15 percent of the file")
    return problems


def _scan_lines(text: str) -> list[str]:
    """The lines the per-line checks read. A wrapped `## Full goal` or `## Full objective` body
    counts as one line, as the text it replaces did, so a wrap cannot split a phrase past a
    check."""
    parts = FULL_SECTION_RE.split(text)
    lines = parts[0].split("\n")
    for heading, body in zip(parts[1::2], parts[2::2], strict=True):
        lines += [heading, " ".join(body.split())]
    return lines


def check_text(
    text: str,
    *,
    opengsd_block: bool,
    home: str = "",
    secrets: tuple[str, ...] | list[str] = (),
) -> list[str]:
    """Problem kinds in a generated file; [] when it may be written. Never echoes a value.

    `opengsd_block` requires every inline autonomous block to carry all eleven sections.
    """
    lines = text.split("\n")
    problems = scan_text(text, home=home, secrets=secrets)
    if any(line.startswith(POINTER_PREFIX) for line in lines) and _full_goal_lines(text) is None:
        problems.append("/goal pointer without a Full goal section")
    if OBJECTIVE_POINTER_MARK in text and f"\n{FULL_OBJECTIVE_HEADING}\n" not in text:
        problems.append("objective pointer without a Full objective section")
    if "--no-verify" in text:
        problems.append("contains --no-verify")
    if DELIMITER in text:
        problems.append("template delimiter left in the output")
    if text.count(OPEN_MARKER) != 1 or text.count(CLOSE_MARKER) != 1:
        problems.append("copy markers not exactly once each")
    for line in _scan_lines(text):
        if SKIP_RE.search(line):
            problems.append("skipped test tier")
        if JEV_RE.search(line) and "advisory" not in line.lower():
            problems.append("jev mentioned without the word advisory")
        if FENCE in line and line != FENCE:
            problems.append("four-backtick token outside a fence line")
    blocks, unclosed = _fenced_blocks(lines)
    if unclosed:
        problems.append("unclosed four-backtick fence")
    for block in blocks:
        problems += _block_problems(block, opengsd_block)
    problems += _rails_problems(text)
    problems += _wrapper_problems(text)
    return list(dict.fromkeys(problems))


class RenderContext(NamedTuple):
    """Where and how a render writes: repo root, date, home to refuse, secrets, output override."""

    repo: str
    today: str
    home: str
    secrets: tuple[str, ...]
    out_dir: str | None


class BlockView(NamedTuple):
    """What the blocks need: the file's repo-relative path, the objective clause for a `/goal`
    condition, the flags-only `/gsd-autonomous` line ("" when there is none), the rails and the
    turn cap (the floor when a caller does not derive one; None: no cap)."""

    path: str
    objective: str
    first_line: str
    rails: str
    turn_cap: int | None = TURN_FLOOR
    goal_style: str = "auto"


class Block(NamedTuple):
    """One strategy's block: its heading, the fenced text, the text after `/goal ` ("" when
    none), whether the rails travel inline, and the full condition when the `/goal` line is a
    pointer to the `## Full goal` section ("" otherwise)."""

    heading: str
    text: str
    condition: str
    inline: bool
    full_goal: str = ""


def _unverified_note(strategy: Mapping[str, Any]) -> str:
    """Says in the paste text that a primitive is unverified; "" when the strategy is verified."""
    if strategy.get("label") != "unverified":
        return ""
    return f" Primitive unverified on this host: {strategy.get('primitive') or strategy['id']}."


def _use_pointer(style: str, condition: str) -> bool:
    """`pointer` always, `inline` never, `auto` when the inline condition is over the threshold."""
    return style == "pointer" or (style == "auto" and len(condition) > GOAL_POINTER_THRESHOLD)


def _goal_style(answers: Mapping[str, Any]) -> str:
    style = answers.get("goal_style") or "auto"
    if style not in GOAL_STYLES:
        raise GuardError(f"field goal_style must be one of {', '.join(GOAL_STYLES)}")
    return str(style)


def _one_block(strategy: Mapping[str, Any], heading: str, view: BlockView) -> Block:
    kind = strategy["id"]
    if kind == "autonomous":
        # The first line stays flags-only (D-12), so the label lives in the heading alone.
        text = fill("BLOCK_INLINE", {"FIRST_LINE": view.first_line, "RAILS": view.rails})
        return Block(heading, text, "", True)
    if kind == "goal":
        lines = goal_block(view.path, view.objective, view.turn_cap)
    elif kind == "loop":
        lines = loop_block(view.path, strategy.get("primitive"))
    elif kind == "plain":
        lines = plain_block(view.path)
    else:
        raise GuardError(f"unknown strategy: {kind}")
    lines[-1] += _unverified_note(strategy)
    condition = lines[0][len(GOAL_PREFIX) :] if kind == "goal" else ""
    full_goal = ""
    if kind == "goal" and _use_pointer(view.goal_style, condition):
        full_goal = condition
        lines = [POINTER_LINE.format(path=view.path) + _unverified_note(strategy)]
        condition = lines[0][len(GOAL_PREFIX) :]
    text = fill("BLOCK_PLAIN", {"BODY": "\n".join(lines)})
    return Block(heading, text, condition, False, full_goal)


def build_blocks(
    strategies: Sequence[Mapping[str, Any]], view: BlockView
) -> list[Block]:
    """One block per strategy, the recommended first; each heading numbers its position."""
    ordered = sorted(strategies, key=lambda strategy: not strategy.get("recommended"))
    return [
        _one_block(strategy, strategy_heading(strategy, index), view)
        for index, strategy in enumerate(ordered, start=1)
    ]


def _ignored(repo: str, relpath: str) -> bool:
    """True when git ignores `relpath`; a missing git or a non-repo counts as not ignored."""
    try:
        result = subprocess.run(
            ["git", "-C", repo, "check-ignore", "-q", relpath],
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def choose_path(repo: str, kind: str, today: str, slug: str, out_dir: str | None) -> str:
    """A new repo-relative POSIX path for the goal file. Never returns an existing path."""
    if out_dir is not None:
        directory = out_dir
    elif kind in GSD_KINDS:
        directory = ".planning/goals"
    elif kind == "superpowers":
        directory = "docs/superpowers/goals"
    elif kind == "none":
        if not _ignored(repo, "tmp/x"):
            raise GuardError("tmp/ is not git-ignored: add it to .gitignore or pass output_dir")
        directory = "tmp"
    else:
        raise GuardError(f"unknown goal kind: {kind}")
    _require_inside(repo, os.path.join(repo, directory))
    path = unique_path(os.path.join(repo, directory), f"{today}-{slug}.md")
    return os.path.relpath(path, repo).replace(os.sep, "/")


def _require_inside(repo: str, directory: str) -> None:
    """Refuse a directory whose resolved path (symlinks followed) leaves the repository."""
    root = os.path.realpath(repo)
    if os.path.commonpath([root, os.path.realpath(directory)]) != root:
        raise GuardError("output directory resolves outside the repository")


def write_atomic(repo: str, relpath: str, text: str) -> None:
    """Write a temp file beside the target, then hard-link it into place; never overwrites."""
    target = os.path.join(repo, relpath)
    if os.path.exists(target):
        raise GuardError(f"refusing to overwrite {relpath}")
    directory = os.path.dirname(target)
    _require_inside(repo, directory)
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".goal-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        # os.link fails when the target appeared since the check; os.replace would overwrite it.
        os.link(tmp_path, target)
    except FileExistsError as exc:
        raise GuardError(f"refusing to overwrite {relpath}") from exc
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _readiness_warnings(readiness: Mapping[str, Any]) -> list[str]:
    """Stdout-only warnings from the readiness problems; they never enter the goal file."""
    return [f"cross-AI readiness failed: {problem}" for problem in readiness.get("problems") or []]


def _plan(entry: Mapping[str, Any]) -> Plan:
    return Plan(
        file=str(entry["file"]),
        title=str(entry.get("title") or ""),
        depends_on=tuple(entry.get("depends_on") or ()),
        free_text=tuple(entry.get("free_text") or ()),
        tasks=int(entry.get("tasks") or 0),
    )


def _check_contiguous(roadmap_order: Sequence[str] | None, numbers: Sequence[str]) -> None:
    """/gsd-autonomous takes one --from/--to range, so a gapped set would run unselected phases."""
    if not roadmap_order or len(numbers) < 2:
        return
    start = roadmap_order.index(numbers[0])
    if list(roadmap_order[start : start + len(numbers)]) != list(numbers):
        raise GuardError("the phases are not a contiguous roadmap run; select a range")


def _phase_work(scope: Mapping[str, Any], work_set: Mapping[str, Any]) -> Work:
    if scope["kind"] not in GSD_SCOPE_KINDS:
        raise GuardError("phases work set needs a GSD scope in the detect result")
    try:
        numbers = sorted({str(n) for n in work_set.get("numbers") or []}, key=phase_key)
    except ValueError as exc:
        raise GuardError("a phase number is not a dotted integer") from exc
    selected = [p for p in scope["phases"] if str(p["number"]) in numbers]
    if not numbers or {str(p["number"]) for p in selected} != set(numbers):
        raise GuardError("a phase in the work set is not in the detected scope")
    selected.sort(key=lambda p: phase_key(str(p["number"])))
    _check_contiguous(scope.get("roadmap_order"), numbers)
    family = "opengsd" if scope.get("identity") == "opengsd" else "gsd-unproven"
    return Work(family, "phases " + ", ".join(numbers), selected, ())


def _plan_work(scope: Mapping[str, Any], work_set: Mapping[str, Any]) -> Work:
    if scope["kind"] not in ("superpowers", "both"):
        raise GuardError("plans work set needs superpowers plans in the detect result")
    names = {os.path.basename(str(path)) for path in work_set.get("files") or []}
    if not names:
        raise GuardError("plans work set names no plan files")
    known = {entry["file"]: entry for entry in scope["plans"]}
    if not all(name in known for name in names):
        raise GuardError("a plan in the work set is not in the detected scope")
    plans = [_plan(known[name]) for name in sorted(names)]
    count = len(plans)
    titles = ", ".join(plan.title or plan.file for plan in plans)
    desc = f"{count} plan{'' if count == 1 else 's'}: {titles}"
    return Work("superpowers", desc, (), tuple(plans))


def _free_work(work_set: Mapping[str, Any]) -> Work:
    text = " ".join(str(work_set.get("text") or "").split())
    if not text:
        raise GuardError("free work set holds no text")
    return Work("none", text)


def _work(detect: Mapping[str, Any], answers: Mapping[str, Any]) -> Work:
    work_set = answers.get("work_set") or {}
    kind = work_set.get("kind")
    if kind == "phases":
        return _phase_work(detect["scope"], work_set)
    if kind == "plans":
        return _plan_work(detect["scope"], work_set)
    if kind == "free":
        return _free_work(work_set)
    raise GuardError("work_set kind must be phases, plans or free")


def _autonomous_line(work: Work) -> str:
    numbers = [str(p["number"]) for p in work.phases]
    if work.family not in GSD_FAMILIES or not numbers:
        return ""
    if len(numbers) == 1:
        flags = f"--only {numbers[0]}"
    else:
        flags = f"--from {numbers[0]} --to {numbers[-1]}"
    return f"/gsd-autonomous {flags} --converge"


def _wrapper(family: str, first_id: str) -> str:
    """The prose before the markers: at most three sentences, naming the recommended block."""
    if first_id == "autonomous":
        return WRAPPER_OPENGSD if family == "opengsd" else WRAPPER_UNPROVEN
    return f"{WRAPPER_BY_ID[first_id]} {PASTE_ONE}"


def _wrapped_section(heading: str, text: str) -> str:
    """`heading` and `text` wrapped at FULL_GOAL_WIDTH, no line cap; "" when `text` is empty."""
    if not text:
        return ""
    body = textwrap.fill(
        text, width=FULL_GOAL_WIDTH, break_long_words=False, break_on_hyphens=False
    )
    return f"\n\n{heading}\n\n{body}"


def _full_sections(blocks: Sequence[Block], full_objective: str) -> str:
    """`## Full objective` then `## Full goal` at the bottom of the file; "" when neither is
    needed."""
    full_goal = next((block.full_goal for block in blocks if block.full_goal), "")
    return _wrapped_section(FULL_OBJECTIVE_HEADING, full_objective) + _wrapped_section(
        FULL_GOAL_HEADING, full_goal
    )


def _compose(
    title: str, wrapper: str, blocks: Sequence[Block], rails: str, full_objective: str = ""
) -> str:
    body = "\n\n".join(f"{block.heading}\n\n{block.text}" for block in blocks)
    shared = f"{SHARED_HEADING}\n\n{rails}" if any(not b.inline for b in blocks) else ""
    text = fill(
        "FILE",
        {"TITLE": title, "WRAPPER": wrapper, "BLOCKS": body, "SHARED_RAILS": shared},
    )
    return text.rstrip("\n") + _full_sections(blocks, full_objective) + "\n"


def _check_strategies(strategies: Sequence[Mapping[str, Any]], family: str) -> None:
    if not strategies:
        raise GuardError("the detect result holds no strategy")
    if family not in GSD_FAMILIES and any(s["id"] == "autonomous" for s in strategies):
        raise GuardError("autonomous needs a GSD phases work set")


def render(
    detect: Mapping[str, Any], answers: Mapping[str, Any], ctx: RenderContext
) -> dict[str, Any]:
    """Write one goal file (a block per ranked strategy) and return the stdout contract.

    Guard failures write nothing.
    """
    check_fields(answers, ctx.home)
    work = _work(detect, answers)
    strategies = sorted(detect["strategies"], key=lambda s: not s.get("recommended"))
    _check_strategies(strategies, work.family)
    relpath = choose_path(
        ctx.repo,
        work.family,
        ctx.today,
        slugify(work.scope_desc),
        answers.get("output_dir") or ctx.out_dir,
    )
    sections = rail_sections(detect, answers, work, relpath)
    rails = assemble_rails(sections)
    view = BlockView(
        path=relpath,
        objective=objective_text(answers, work.scope_desc),
        first_line=_autonomous_line(work),
        rails=rails,
        turn_cap=resolve_turn_cap(answers, work),
        goal_style=_goal_style(answers),
    )
    blocks = build_blocks(strategies, view)
    text = _compose(
        fit_line("Goal prompt: ", work.scope_desc, prefix="# "),
        _wrapper(work.family, strategies[0]["id"]),
        blocks,
        rails,
        " ".join(str(answers.get("objective") or "").split()) if objective_cut(answers) else "",
    )
    problems = check_text(
        text,
        opengsd_block=work.family in GSD_FAMILIES,
        home=ctx.home,
        secrets=ctx.secrets,
    )
    if problems:
        raise GuardError("; ".join(problems))
    write_atomic(ctx.repo, relpath, text)
    pointer = [block for block in blocks if block.full_goal]
    goal_blocks = [block for block in blocks if block.condition]
    return {
        "path": relpath,
        "strategies": [
            {
                "id": s["id"],
                "recommended": bool(s.get("recommended")),
                "reason": s.get("reason", ""),
                "label": s.get("label", ""),
            }
            for s in strategies
        ],
        "full_objective": objective_cut(answers),
        "goal_form": (
            None if not goal_blocks else "pointer" if pointer else "inline"
        ),
        "conditions": [
            {
                "strategy": "goal",
                "chars": len(block.condition),
                **({"full_chars": len(block.full_goal)} if block.full_goal else {}),
            }
            for block in goal_blocks
        ],
        "sections": [heading for heading, _ in sections],
        "paste_chars": sum(len(block.text) for block in blocks),
        "rails_lines": len(_rule_lines(rails.split("\n"))),
        "warnings": [
            *(
                _readiness_warnings(detect["readiness"])
                if work.family in GSD_FAMILIES and not answers.get("native_execution")
                else []
            ),
            *([POINTER_WARNING] if pointer else []),
        ],
    }
