#!/usr/bin/env python3
"""Section builders for the goal-prompt rails (GPS-02..04; D-26..D-28; SPEC R3).

Each builder returns plain rule lines: no bullets, no headings. `assemble_rails` adds the `- `
bullets and the section headings. A line that starts with three spaces is a sub-line and keeps
its text unprefixed. Every fixed line stays at most LINE_CAP characters (guards are in gp_render).
Variable text (a plan title, the objective, a free-text dependency) is cut by `fit_line` so its
line fits; a list of work items or a command is never cut, because a cut list would hide work from
the run: `wrap_items` breaks it between items onto three-space continuation sub-lines.
stdlib only; gp_e2e and gp_common are the only siblings used.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

import gp_e2e
from gp_common import GuardError, phase_key
from gp_scope import Plan, dependents, execution_order

__all__ = [
    "GSD_FAMILIES",
    "LINE_CAP",
    "Work",
    "assemble_rails",
    "cleanup_lines",
    "decision_lines",
    "done_lines",
    "fit_line",
    "generic_rule_lines",
    "goal_block",
    "loop_block",
    "objective_cut",
    "objective_lines",
    "objective_text",
    "order_lines",
    "plain_block",
    "plan_rule_lines",
    "quota_lines",
    "rail_sections",
    "report_lines",
    "role_lines",
    "safety_lines",
    "stop_lines",
    "strategy_heading",
    "superpowers_order_lines",
    "superpowers_rule_lines",
    "turn_cap",
    "work_items",
    "wrap_items",
]

LINE_CAP = 200
GOAL_SCOPE_CAP = 600  # the scope clause of a /goal condition; the 1,800 budget holds the rest
RULE_BULLET = "- "
SUB_INDENT = "   "
ELLIPSIS = "..."
TURN_FLOOR = 60
TURN_PER_ITEM = 40
GSD_FAMILIES = ("opengsd", "gsd-unproven")
GOAL_EVIDENCE = "exit code and count line"
UNIT_CLAUSE = "Unit tests alone never count as done."
OBJECTIVE_TAIL = ", each verified. Then leave the repository clean."
OBJECTIVE_POINTER = " (full text: {path}section Full objective)"
# Only the `/loop` row is typed as a `/loop` command; a schedule or wake tool never becomes an
# interval loop, and an OS timer or no primitive falls to the plain paragraph.
LOOP_COMMAND = "/loop"
SCHEDULE_TOOLS = ("CronCreate one-shot", "CronCreate recurring", "ScheduleWakeup")
PLAIN_FLAG = "flagged: no goal, loop or schedule primitive"


class Work(NamedTuple):
    """What the prompt covers: a family (opengsd | gsd-unproven | superpowers | none), the scope
    text the objective names, and the selected phases (GSD) or plans (superpowers)."""

    family: str
    scope_desc: str
    phases: Sequence[Mapping[str, Any]] = ()
    plans: Sequence[Plan] = ()


CROSS_AI_RULE = (
    "Every PLAN.md frontmatter carries cross_ai: true, so GSD delegates it to cross-AI."
)
NATIVE_RULE = (
    "Native execution was chosen when this prompt was written: plans omit cross_ai: true "
    "and run in this session."
)
READINESS_RULES = (
    "First step, before any execution: confirm .planning/config.json enables "
    "workflow.cross_ai_execution and sets workflow.cross_ai_command.",
    "Then confirm the runner script exists, that its argv listing names at least one installed "
    "CLI, and that every default reviewer CLI is installed.",
    "These checks prove installation only, never quota or auth. If any check fails, stop and "
    "report what to fix.",
)
GAP_KINDS = (
    ("No CONTEXT (discuss, then plan)", lambda p: not p["has_context"]),
    ("No SPEC (spec, then discuss, then plan)", lambda p: not p["has_spec"]),
    (
        "Plans already exist (execute them; the plan checker still runs)",
        lambda p: p["plan_count"] > 0,
    ),
    ("Already verified (verify only)", lambda p: p["has_verification"]),
)
CREATE_FIRST = (
    "No e2e suite exists. The first task, before any feature plan, creates one that launches the "
    "real app (a PTY drive for a terminal UI, a browser for a web UI) and make it pass."
)
EVIDENCE = (
    "Print each command with its exact exit code, its count line and the last 20 lines of "
    "output, ANSI codes stripped."
)
MOCKUP_REVIEW = (
    "Mockup fidelity: capture e2e screenshots or TUI text snapshots, print their paths, and list "
    "them for human review against {mockups}. No automated judge decides it."
)
DONE_TAIL = (
    "Print the paths of the screenshots or TUI text snapshots the e2e run produced.",
    "Start each long-lived e2e process in its own process group and record its group id in "
    "tmp/. After the run kill those groups and print a process listing (ps) that shows none "
    "remain.",
    "Phase status: VERIFICATION shows passed for every phase in scope, or the item is listed as "
    "human verification with its reason.",
    "Unit tests alone never count as done.",
)


def turn_cap(items: int) -> int:
    """The turn cap in STOP IF and in a /goal condition: 40 turns per item, never below 60."""
    return max(TURN_FLOOR, TURN_PER_ITEM * items)


def work_items(work: Work) -> int:
    """The items the turn cap counts: phases, else plans, else one free-text task."""
    return len(work.phases) or len(work.plans) or 1


def _one_line(text: str) -> str:
    return " ".join(str(text).split())


def fit_line(
    head: str, variable: str, tail: str = "", prefix: str = RULE_BULLET, cap: int = LINE_CAP
) -> str:
    """`head` + `variable` + `tail` as one line that, with `prefix` in front, fits LINE_CAP. A
    variable that is too long is cut and ends with `...`. A str slices by code point, so a
    multi-byte character is never split. A fixed head or tail too long for the line is left for
    the cap guard in gp_render to refuse."""
    room = cap - len(prefix) - len(head) - len(tail)
    if len(variable) > room:
        variable = variable[: max(room - len(ELLIPSIS), 0)].rstrip() + ELLIPSIS
    return f"{head}{variable}{tail}"


def wrap_items(
    head: str, items: Sequence[str], tail: str = "", sep: str = ", ", section: str = "a rule"
) -> list[str]:
    """`head`, the items joined by `sep`, then `tail`, filled greedily onto rule lines of LINE_CAP.
    The first line is a bullet (a sub-line when `head` starts with SUB_INDENT); later lines are
    SUB_INDENT continuations. A break falls only between items, so none is cut or dropped; an item
    too long for a line of its own raises GuardError naming `section`."""
    room = LINE_CAP if head.startswith(SUB_INDENT) else LINE_CAP - len(RULE_BULLET)
    pieces = [f"{item}{sep}" for item in items[:-1]] + [f"{items[-1]}{tail}"] if items else [tail]
    lines: list[str] = []
    current = head
    for piece in pieces:
        if len((current + piece).rstrip()) <= room:
            current += piece
            continue
        if len((SUB_INDENT + piece).rstrip()) > LINE_CAP:
            raise GuardError(
                f"rule line over {LINE_CAP} characters in {section}: "
                "one list item or command word is longer than a line"
            )
        if current.strip():
            lines.append(current.rstrip())
        current = SUB_INDENT + piece
        room = LINE_CAP
    lines.append(current.rstrip())
    return lines


def _paren(label: str) -> str:
    return f" ({label})" if label else ""


def role_lines() -> list[str]:
    return [
        "You are the orchestrator: the session that received this prompt. Dispatch plan work to "
        "subagents, reusing one or starting a fresh one, as you judge best.",
        "Verify every result yourself; never accept a reported pass.",
    ]


def objective_cut(answers: Mapping[str, Any]) -> bool:
    """True when the user's objective is too long for one rule line, so the file keeps its full
    text in a `## Full objective` section."""
    objective = _one_line(answers.get("objective") or "")
    return len(RULE_BULLET) + len(objective) > LINE_CAP


def objective_lines(answers: Mapping[str, Any], scope_desc: str, path: str = "") -> list[str]:
    """OBJECTIVE rule lines. `scope_desc` is `phases 16, 16.1, 17` or `3 plans: <titles>`; each
    line is cut to fit LINE_CAP, so a long title or objective never refuses generation. A cut
    objective ends with a pointer to the file's `## Full objective` section (`path` names it)."""
    lines = [fit_line("Finish ", scope_desc, OBJECTIVE_TAIL)]
    objective = _one_line(answers.get("objective") or "")
    if objective_cut(answers):
        tail = OBJECTIVE_POINTER.format(path=f"{path} " if path else "")
        lines.append(fit_line("", objective, tail))
    elif objective:
        lines.append(objective)
    return lines


def objective_text(answers: Mapping[str, Any], scope_desc: str) -> str:
    """The objective on one line for a `/goal` condition (its own cap, GOAL_CAP). The scope clause
    is cut at GOAL_SCOPE_CAP, so many plan titles cannot exhaust the condition budget;
    the user's own objective text stays uncut."""
    objective = _one_line(answers.get("objective") or "")
    scope = fit_line("Finish ", scope_desc, OBJECTIVE_TAIL, prefix="", cap=GOAL_SCOPE_CAP)
    return " ".join(part for part in (scope, objective) if part)


def plan_rule_lines(candidate_skills: Sequence[str], native: bool) -> list[str]:
    """Rules that bind each plan. Native swaps the first rule and drops the readiness step."""
    lines = [NATIVE_RULE] if native else [CROSS_AI_RULE, *READINESS_RULES]
    lines += [
        "Reviewers come from .planning/config.json. Probe each one once before the first review. "
        "Record any failure; never substitute a model.",
        "Read AGENTS.md first, then each phase SPEC and CONTEXT. Their decisions are locked; never "
        "re-discuss them.",
        *wrap_items(
            "Read a skill only when the task needs it. Candidate skills: ",
            list(candidate_skills) or ["none"],
            ".",
            section="RULES FOR EVERY PLAN",
        ),
        "Pre-commit hooks always run on every commit; fix a real failure at its root, never skip "
        "it.",
    ]
    return lines


def superpowers_rule_lines(candidate_skills: Sequence[str]) -> list[str]:
    """Superpowers plans: one subagent per plan in dependency order, verified by the orchestrator"""
    return [
        "Dispatch each plan's work to a subagent, one plan at a time. Reuse a subagent or start a "
        "fresh one as you judge best; no two plans share the working tree at once.",
        "You own AGENTS.md compliance and the deterministic rails; read AGENTS.md first. The "
        "subagent implements, you verify.",
        "After each plan, run its done checks yourself and print their output before starting "
        "the next plan.",
        "A failed plan stops only the plans that depend on it; every independent plan still runs.",
        *wrap_items(
            "Read a skill only when the task needs it. Candidate skills: ",
            list(candidate_skills) or ["none"],
            ".",
            section="RULES FOR EVERY PLAN",
        ),
        "Pre-commit hooks always run on every commit; fix a real failure at its root, never skip "
        "it.",
    ]


def generic_rule_lines(candidate_skills: Sequence[str]) -> list[str]:
    """Free-text work with no plan files: the same verification and skill rules, no plan loop."""
    return [
        "Work the task in order and verify each step yourself; never accept a reported pass.",
        "You own AGENTS.md compliance; read AGENTS.md first.",
        *wrap_items(
            "Read a skill only when the task needs it. Candidate skills: ",
            list(candidate_skills) or ["none"],
            ".",
            section="RULES FOR EVERY PLAN",
        ),
        "Pre-commit hooks always run on every commit; fix a real failure at its root, never skip "
        "it.",
    ]


def superpowers_order_lines(plans: Sequence[Plan], order: Sequence[str]) -> list[str]:
    """Order and stop scope. A single plan with no free text has no lines at all."""
    by_file = {plan.file: plan for plan in plans}
    lines: list[str] = []
    if len(plans) > 1:
        lines += wrap_items("Plans in order: ", list(order), ".", section="ORDER")
        for name in order:
            children = dependents(plans, name)
            if children:
                lines += wrap_items(
                    f"If {name} fails, skip its dependents: ",
                    list(children),
                    ".",
                    section="ORDER",
                )
    for name in order:
        for text in by_file[name].free_text:
            note = _one_line(text).rstrip(".")
            lines.append(fit_line("Dependency to confirm before starting: ", note, "."))
    return lines


def goal_block(path: str, objective: str, cap: int, evidence: str = GOAL_EVIDENCE) -> list[str]:
    """One `/goal` line: the objective, the rails section and DONE WHEN, evidence, a turn cap."""
    condition = _one_line(
        f"{objective} Done when every DONE WHEN item in {path} section Rails holds, with the "
        f"{evidence} of "
        f"every command printed. {UNIT_CLAUSE} If it does not hold, stop and report after "
        f"{cap} turns."
    )
    return [f"/goal {condition}"]


def _continue(path: str) -> str:
    return f"Continue the work described in {path} section Rails"


def plain_block(path: str) -> list[str]:
    """A paragraph that relies on the QUOTA A wake (an OS timer or no primitive at all)."""
    return [
        f"{_continue(path)}; stop and report once DONE WHEN holds. The OS-timer wake of QUOTA A "
        "re-enters this session."
    ]


def loop_block(path: str, primitive: str | None, interval: str = "30m") -> list[str]:
    """A `/loop` line only for the `/loop` row; a schedule or wake tool names itself, an OS timer
    or none gets the plain paragraph. The block is labelled by the same row it types."""
    if primitive == LOOP_COMMAND:
        return [f"/loop {interval} {_continue(path)}; stop and report once DONE WHEN holds."]
    if primitive in SCHEDULE_TOOLS:
        return [
            f"{_continue(path)}; stop and report once DONE WHEN holds. The {primitive} wake of "
            "QUOTA A re-enters this session."
        ]
    return plain_block(path)


def strategy_heading(strategy: Mapping[str, Any], index: int) -> str:
    """`## Strategy N (recommended): id`, with the plain flag and any unverified label."""
    recommended = " (recommended)" if strategy.get("recommended") else ""
    flag = f" ({PLAIN_FLAG})" if strategy["id"] == "plain" else ""
    label = ""
    if strategy.get("label") == "unverified":
        label = f" [unverified: {strategy.get('primitive') or strategy['id']}]"
    return f"## Strategy {index}{recommended}: {strategy['id']}{flag}{label}"


def order_lines(phases: Sequence[Mapping[str, Any]], native: bool = False) -> list[str]:
    """Numeric order, then one line per gap kind that has at least one phase. Native execution
    keeps its plans without cross_ai: true, so it never lists the cross_ai gap."""
    ordered = sorted(phases, key=lambda p: phase_key(p["number"]))
    lines = wrap_items(
        "Phases in numeric order: ", [p["number"] for p in ordered], ".", section="ORDER"
    )
    for label, applies in GAP_KINDS:
        listed = [p["number"] for p in ordered if applies(p)]
        if listed:
            lines += wrap_items(f"{label}: ", listed, ".", section="ORDER")
    if not native:
        missing = [
            p["number"]
            for p in ordered
            if p["plan_count"] > 0 and p["cross_ai_plans"] < p["plan_count"]
        ]
        if missing:
            lines += wrap_items(
                "Existing plans missing cross_ai: true (add it, then execute): ",
                missing,
                ".",
                section="ORDER",
            )
    return lines


def quota_lines(wake: Mapping[str, Any], runner: Mapping[str, Any]) -> list[str]:
    """Two separate directives: A is this session's own wake, B is the cross-AI children."""
    primitive = wake.get("primitive")
    if primitive:
        wake_line = f"   Wake primitive on this host: {primitive}{_paren(wake.get('label', ''))}."
    else:
        wake_line = "   Wake primitive on this host: none found."
    lines = [
        "A. This session (its own quota): before the first plan, arm the ai-kit-session-wake "
        "skill, a self-resume by session id at the host-reported reset when known, else hourly.",
        "   Run its done step when the run ends. Only this orchestrator arms or disarms it.",
        wake_line,
        "B. Cross-AI children (a child CLI hits its limit): follow the ai-kit-cross-ai skill. The "
        "runner cross-ai.mjs owns the retry ladder and never switches CLI, provider or model.",
        "   Read its last AIKIT-XAI status line before acting.",
        "   A quota stop whose AIKIT-XAI line has a whole-number retry_after_s: wait that exact "
        "time once (one one-shot job, never a fixed-interval re-check), "
        "then re-invoke the same lane.",
        "   Check the working tree and resume only the unfinished work. After stopped=hard-waits "
        "or stopped=cap schedule nothing more.",
        "   A quota stop without retry_after_s is an owner stop: report the evidence and stop. "
        "Whether this host can run a one-shot job is unverified.",
    ]
    command = _one_line(runner.get("command") or "")
    if command:
        lines += wrap_items(
            "   Runner: ",
            command.split(" "),
            f"{_paren(runner.get('label', ''))}.",
            sep=" ",
            section="QUOTA",
        )
    return lines


def decision_lines() -> list[str]:
    return [
        "Verifiable questions: check and fix them directly; do not ask.",
        "Gray areas: ask the jev-fast-decision skill and follow its SKILL.md. Advisory only: on "
        "needs_fallback or no answer you decide; verify before acting. Prefer the best design over "
        "the easiest.",
        "Never pause for questions or UAT. Put a blocking item in the ledger and continue.",
        "Never remove existing features.",
    ]


def safety_lines() -> list[str]:
    return [
        "Never touch the real ~/.claude, ~/.cursor, ~/.config/opencode, ~/.codex, ~/.pi or ~/.gsd; "
        "use a scratch HOME.",
        "Never print secrets. Never push. Never stage everything blindly.",
        "Pre-commit hooks and every test tier always run; no step may skip one.",
    ]


def cleanup_lines() -> list[str]:
    # Each rule is its own line under LINE_CAP. No flag-like token: the OpenGSD block refuses one
    # after line 1 (the workflow greps it), so the porcelain and force rules use words.
    return [
        "Leave no stray files: commit, ignore or remove each.",
        "Act only on worktrees, branches and tags this run created and recorded in a run ledger "
        "under tmp/.",
        "Anything older or not owned by this run is reported, never removed.",
        "Mark each backlog entry finished in this run done in the backlog's Done list, with the "
        "date and what delivered it; delete no entry or directory; list the rest.",
        "Before any merge or removal, the porcelain form of git status must be empty in that "
        "worktree and in the main checkout.",
        "Never force a merge, removal or branch delete. On a conflict or a dirty tree, stop and "
        "report.",
        "Merge the working branch into the main checkout; never push.",
        "Archive the unmerged work of each worktree this run created as a tag, then remove that "
        "worktree and its branch; remove this worktree last.",
    ]


def stop_lines(cap: int, opengsd: bool) -> list[str]:
    lines = [
        "The same failure repeats 3 times with no progress.",
        f"Stop after {cap} turns and report.",
        "A decision blocks other work and nothing resolves it.",
        "A step needs a real config write, a login or sudo.",
    ]
    if opengsd:
        lines.append("Every cross-AI candidate for a role is unusable.")
    lines.append("In each case park the item, continue independent work, then report.")
    return lines


def report_lines(jev: Mapping[str, Any]) -> list[str]:
    lines = [
        "Per item: status, verification, the evidence printed, the cross-AI CLI used.",
        "The ledger of your decisions, the commits made, nothing pushed.",
    ]
    if jev.get("usable"):
        lines.append(
            "Advisory (not a gate): ask the jev-fast-decision skill one choice item (follow its "
            "SKILL.md), objectives all, mostly, partly or not met, from text summaries only."
        )
        lines.append(
            "Report jev's advisory answer under that heading; needs_fallback or no answer means "
            "you judge it yourself."
        )
    else:
        reason = _one_line(jev.get("reason") or "no usable backend")
        lines.append(fit_line("The advisory closeness check was omitted: ", reason, "."))
    return lines


def _marker_labels(commands: Sequence[Mapping[str, str]]) -> str:
    labels: list[str] = []
    for entry in commands:
        for row in gp_e2e.markers_for_text(entry["command"]):
            if row["marker"] is None:
                continue
            label = f"'{row['marker']}' for {row['runner']}"
            if not row["verified"]:
                label += " (unverified)"
            if label not in labels:
                labels.append(label)
    return "; ".join(labels)


def _e2e_lines(commands: Sequence[Mapping[str, str]]) -> list[str]:
    lines = []
    for entry in commands:
        inferred = entry["confidence"] == "inferred"
        suffix = " (inferred: confirm it runs the real app)" if inferred else ""
        lines.append(
            f"E2E: `{entry['command']}` exits 0 and prints a test count above zero. Exit 0 with a "
            f"zero count is not green.{suffix}"
        )
    markers = _marker_labels(commands)
    lines.append(
        f"Zero-count markers: {markers}."
        if markers
        else "Zero-count markers: read the count line yourself."
    )
    return lines


def done_lines(e2e: Mapping[str, Any], mockups: Sequence[Any]) -> list[str]:
    """DONE WHEN: the create-first task when no e2e suite exists, the detected e2e commands
    otherwise, and a human-review line when mockups are given. Free text collapses to one line."""
    gates = list(e2e.get("gates") or [])
    fallback = ["the project's lint and unit commands (none detected: find them)"]
    none = bool(e2e.get("none"))
    lines = [CREATE_FIRST] if none else []
    lines += [EVIDENCE, *wrap_items("Gates first: ", gates or fallback, ".", section="DONE WHEN")]
    if not none:
        lines += _e2e_lines(e2e["commands"])
    if mockups:
        head, _, tail = MOCKUP_REVIEW.partition("{mockups}")
        mockup_names = [_one_line(mockup) for mockup in mockups]
        lines += wrap_items(head, mockup_names, tail, section="DONE WHEN")
    lines += list(DONE_TAIL)
    return lines


def assemble_rails(sections: Sequence[tuple[str, Sequence[str]]]) -> str:
    """Headings on their own lines, rules as `- ` bullets, one blank line between sections."""
    parts = []
    for heading, lines in sections:
        body = [heading]
        body += [line if line.startswith("   ") else f"- {line}" for line in lines]
        parts.append("\n".join(body))
    return "\n\n".join(parts)


def _rules_and_order(
    detect: Mapping[str, Any], answers: Mapping[str, Any], work: Work
) -> tuple[list[str], list[str]]:
    """The rule lines and the ORDER lines (empty when the work has no order) for one family."""
    skills = detect["candidate_skills"]
    if work.family in GSD_FAMILIES:
        native = bool(answers.get("native_execution"))
        return plan_rule_lines(skills, native), order_lines(work.phases, native)
    if work.family == "superpowers":
        return superpowers_rule_lines(skills), superpowers_order_lines(
            work.plans, execution_order(work.plans)
        )
    return generic_rule_lines(skills), []


def rail_sections(
    detect: Mapping[str, Any], answers: Mapping[str, Any], work: Work, path: str = ""
) -> list[tuple[str, list[str]]]:
    """The labeled sections of D-28 for one work family; ORDER is present only when it has lines."""
    rules, order = _rules_and_order(detect, answers, work)
    sections: list[tuple[str, list[str]]] = [
        ("OBJECTIVE", objective_lines(answers, work.scope_desc, path)),
        ("ROLE", role_lines()),
        ("RULES FOR EVERY PLAN", rules),
    ]
    if order:
        sections.append(("ORDER", order))
    return [
        *sections,
        ("QUOTA", quota_lines(detect["wake"], detect["runner"])),
        ("DECISIONS", decision_lines()),
        ("SAFETY", safety_lines()),
        ("DONE WHEN", done_lines(detect["e2e"], answers.get("mockups") or [])),
        ("CLEANUP", cleanup_lines()),
        ("STOP IF", stop_lines(turn_cap(work_items(work)), work.family == "opengsd")),
        ("REPORT", report_lines(detect["jev"])),
    ]
