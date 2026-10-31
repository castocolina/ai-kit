#!/usr/bin/env python3
"""Prompt renderer for the goal-prompt skill (GPS-02..04; SPEC R3; D-12..D-15, D-25..D-28).

The template lives in ../assets/prompt-template.md, split into named sections by `=== NAME ===`
lines. `PromptTemplate` uses the rare delimiter `§§` so `$?`, `${PIPESTATUS[0]}` and JSON braces
stay literal, and `fill` substitutes strictly: a missing key is a GuardError, never a blank.
stdlib only.
"""

from __future__ import annotations

import functools
import os
import re
import string
import subprocess
import tempfile
from collections.abc import Mapping
from typing import Any, NamedTuple

from gp_common import GuardError, is_machine_path, phase_key, scan_text, slugify, unique_path
from gp_sections import assemble_rails, rail_sections

__all__ = [
    "PromptTemplate",
    "RenderContext",
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
GOAL_CAP = 4000
GOAL_BUDGET = 1800
INLINE_CAP = 7000
RULE_CAP = 60
LINE_CAP = 200
WRAPPER_SENTENCES = 3
WRAPPER_SHARE = 0.15
UNIT_SENTENCE = "Unit tests alone never count as done."
GOAL_PREFIX = "/goal "
FLAG_RE = re.compile(r"--[A-Za-z]")
JEV_RE = re.compile(r"\bjev", re.IGNORECASE)
SKIP_RE = re.compile(r"skip.*test tier", re.IGNORECASE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
GSD_KINDS = ("gsd", "opengsd", "gsd-unproven")
GIT_TIMEOUT = 20
WRAPPER_OPENGSD = (
    "This project is OpenGSD, so the run uses /gsd-autonomous with convergence. Paste the block "
    "between the markers into a fresh session in this repository."
)


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


def _block_problems(lines: list[str], opengsd_block: bool) -> list[str]:
    body = lines[1:]
    problems: list[str] = []
    if opengsd_block:
        if len("\n".join(lines)) > INLINE_CAP:
            problems.append(f"OpenGSD block over {INLINE_CAP} characters")
        if any(FLAG_RE.search(line) for line in body):
            problems.append("flag-like token after line 1 of the block")
        rules = _rule_lines(body)
        if len(rules) > RULE_CAP:
            problems.append(f"more than {RULE_CAP} rule lines")
        if any(len(line) > LINE_CAP for line in rules):
            problems.append(f"rule line over {LINE_CAP} characters")
    if lines and lines[0].startswith(GOAL_PREFIX):
        problems += _goal_problems("\n".join([lines[0][len(GOAL_PREFIX) :], *body]))
    sections = _sections(body)
    if opengsd_block:
        problems += [f"section missing: {name}" for name in HEADINGS if name not in sections]
    done = sections.get("DONE WHEN")
    if done is not None and not any(UNIT_SENTENCE in line for line in done):
        problems.append(f"DONE WHEN lacks '{UNIT_SENTENCE}'")
    gated = [*sections.get("DONE WHEN", []), *sections.get("STOP IF", [])]
    if any(JEV_RE.search(line) for line in gated):
        problems.append("jev inside DONE WHEN or STOP IF")
    return problems


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


def check_text(
    text: str,
    *,
    opengsd_block: bool,
    home: str = "",
    secrets: tuple[str, ...] | list[str] = (),
) -> list[str]:
    """Problem kinds in a generated file; [] when it may be written. Never echoes a value."""
    lines = text.split("\n")
    problems = scan_text(text, home=home, secrets=secrets)
    if "--no-verify" in text:
        problems.append("contains --no-verify")
    if DELIMITER in text:
        problems.append("template delimiter left in the output")
    for line in lines:
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
    problems += _wrapper_problems(text)
    return list(dict.fromkeys(problems))


class RenderContext(NamedTuple):
    """Where and how a render writes: repo root, date, home to refuse, secrets, output override."""

    repo: str
    today: str
    home: str
    secrets: tuple[str, ...]
    out_dir: str | None


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
    path = unique_path(os.path.join(repo, directory), f"{today}-{slug}.md")
    return os.path.relpath(path, repo).replace(os.sep, "/")


def write_atomic(repo: str, relpath: str, text: str) -> None:
    """Write through a temp file in the target directory, then os.replace; never overwrites."""
    target = os.path.join(repo, relpath)
    if os.path.exists(target):
        raise GuardError(f"refusing to overwrite {relpath}")
    directory = os.path.dirname(target)
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".goal-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_path, target)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _readiness_warnings(readiness: Mapping[str, Any]) -> list[str]:
    checks = {
        "runner_ok": "cross-AI runner not ready",
        "cli_listed": "runner lists no installed CLI",
        "reviewers_ok": "a default reviewer CLI is missing",
    }
    return [message for key, message in checks.items() if readiness.get(key) is False]


def render(
    detect: Mapping[str, Any], answers: Mapping[str, Any], ctx: RenderContext
) -> dict[str, Any]:
    """Write the OpenGSD goal file and return the stdout contract. Guard failures write nothing."""
    check_fields(answers, ctx.home)
    scope = detect["scope"]
    work_set = answers["work_set"]
    if scope["kind"] != "opengsd" or work_set["kind"] != "phases":
        raise NotImplementedError("only the OpenGSD phases case renders; plan 27-07 adds more")
    numbers = sorted({str(n) for n in work_set["numbers"]}, key=phase_key)
    selected = [p for p in scope["phases"] if p["number"] in numbers]
    if sorted(p["number"] for p in selected) != sorted(numbers):
        raise GuardError("a phase in the work set is not in the detected scope")
    if len(numbers) == 1:
        flags = f"--only {numbers[0]}"
    else:
        flags = f"--from {numbers[0]} --to {numbers[-1]}"
    scope_desc = "phases " + ", ".join(numbers)
    rails = assemble_rails(rail_sections(detect, answers, scope_desc, selected))
    block = fill(
        "BLOCK_INLINE",
        {"FIRST_LINE": f"/gsd-autonomous {flags} --converge", "RAILS": rails},
    )
    text = fill(
        "FILE",
        {
            "TITLE": f"Goal prompt: {scope_desc}",
            "WRAPPER": WRAPPER_OPENGSD,
            "BLOCKS": block,
            "SHARED_RAILS": "",
        },
    )
    text = text.rstrip("\n") + "\n"
    problems = check_text(text, opengsd_block=True, home=ctx.home, secrets=ctx.secrets)
    if problems:
        raise GuardError("; ".join(problems))
    out_dir = answers.get("output_dir") or ctx.out_dir
    relpath = choose_path(ctx.repo, scope["kind"], ctx.today, slugify(scope_desc), out_dir)
    write_atomic(ctx.repo, relpath, text)
    return {
        "path": relpath,
        "strategies": [{"id": "autonomous", "recommended": True}],
        "conditions": [],
        "sections": list(HEADINGS),
        "paste_chars": len(block),
        "rails_lines": len(_rule_lines(block.split("\n")[1:])),
        "warnings": _readiness_warnings(detect["readiness"]),
    }
