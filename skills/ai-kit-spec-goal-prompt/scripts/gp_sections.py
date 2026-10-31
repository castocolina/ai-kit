#!/usr/bin/env python3
"""Section builders for the goal-prompt rails (GPS-02..04; D-26..D-28; SPEC R3).

Each builder returns plain rule lines: no bullets, no headings. `assemble_rails` adds the `- `
bullets and the section headings. A line that starts with three spaces is a sub-line and keeps
its text unprefixed. Every fixed line stays at most 200 characters (guards are in gp_render).
stdlib only; gp_e2e and gp_common are the only siblings used.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import gp_e2e
from gp_common import phase_key

__all__ = [
    "TURN_CAP",
    "assemble_rails",
    "cleanup_lines",
    "decision_lines",
    "done_lines",
    "objective_lines",
    "order_lines",
    "plan_rule_lines",
    "quota_lines",
    "rail_sections",
    "report_lines",
    "role_lines",
    "safety_lines",
    "stop_lines",
]

TURN_CAP = 200
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
DONE_TAIL = (
    "Print the paths of the screenshots or TUI text snapshots the e2e run produced.",
    "Start each long-lived e2e process in its own process group and record its group id in "
    "tmp/. After the run kill those groups and print a process listing (ps) that shows none "
    "remain.",
    "Phase status: VERIFICATION shows passed for every phase in scope, or the item is listed as "
    "human verification with its reason.",
    "Unit tests alone never count as done.",
)


def _one_line(text: str) -> str:
    return " ".join(str(text).split())


def _paren(label: str) -> str:
    return f" ({label})" if label else ""


def role_lines() -> list[str]:
    return [
        "You are the orchestrator: the session that received this prompt. Dispatch plan work to "
        "subagents, reusing one or starting a fresh one, as you judge best.",
        "Verify every result yourself; never accept a reported pass.",
    ]


def objective_lines(answers: Mapping[str, Any], scope_desc: str) -> list[str]:
    """`scope_desc` is `phases 16, 16.1, 17` or `3 plans: <titles>`; the objective follows."""
    lines = [f"Finish {scope_desc}, each verified. Then leave the repository clean."]
    objective = _one_line(answers.get("objective") or "")
    if objective:
        lines.append(objective)
    return lines


def plan_rule_lines(candidate_skills: Sequence[str], native: bool) -> list[str]:
    """Rules that bind each plan. Native swaps the first rule and drops the readiness step."""
    lines = [NATIVE_RULE] if native else [CROSS_AI_RULE, *READINESS_RULES]
    skills = ", ".join(candidate_skills) or "none"
    lines += [
        "Reviewers come from .planning/config.json. Probe each one once before the first review. "
        "Record any failure; never substitute a model.",
        "Read AGENTS.md first, then each phase SPEC and CONTEXT. Their decisions are locked; never "
        "re-discuss them.",
        f"Read a skill only when the task needs it. Candidate skills: {skills}.",
        "Pre-commit hooks always run on every commit; fix a real failure at its root, never skip "
        "it.",
    ]
    return lines


def order_lines(phases: Sequence[Mapping[str, Any]]) -> list[str]:
    """Numeric order, then one line per gap kind that has at least one phase."""
    ordered = sorted(phases, key=lambda p: phase_key(p["number"]))
    lines = [f"Phases in numeric order: {', '.join(p['number'] for p in ordered)}."]
    for label, applies in GAP_KINDS:
        listed = [p["number"] for p in ordered if applies(p)]
        if listed:
            lines.append(f"{label}: {', '.join(listed)}.")
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
        "   On a quota stop, re-check every 10 minutes for at most 4 hours, resume only the "
        "unfinished work after checking the working tree, then stop and report.",
    ]
    command = runner.get("command") or ""
    if command:
        lines.append(f"   Runner: {command}{_paren(runner.get('label', ''))}.")
    return lines


def decision_lines() -> list[str]:
    return [
        "Verifiable questions: check and fix them directly; do not ask.",
        "Gray areas: use the decide.py ladder of the ai-kit-gsd-spec-discuss skill. Its answers "
        "are advisory; verify before acting. Prefer the best design over the easiest.",
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
    return [
        "Leave no stray files: commit, ignore or remove each.",
        "Remove the backlog entries and directories of finished work; list the rest.",
        "Merge the working branch into the main checkout; never push.",
        "Archive unmerged work of every intermediate worktree as a tag, then remove the worktree "
        "and its branch; remove this worktree last.",
    ]


def stop_lines(turn_cap: int, opengsd: bool) -> list[str]:
    lines = [
        "The same failure repeats 3 times with no progress.",
        f"Stop after {turn_cap} turns and report.",
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
            "Advisory (not a gate): run one decide.py choice item, objectives all, mostly, partly "
            "or not met, from text summaries only; report the answer under that heading."
        )
    else:
        reason = _one_line(jev.get("reason") or "no usable backend")
        lines.append(f"The advisory closeness check was omitted: {reason}.")
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


def done_lines(e2e: Mapping[str, Any], mockups: Sequence[Any]) -> list[str]:
    """DONE WHEN for detected e2e commands. The none case and mockups arrive in plan 27-08."""
    if e2e.get("none") or mockups:
        raise NotImplementedError("DONE WHEN without e2e commands or with mockups: plan 27-08")
    gates = list(e2e.get("gates") or [])
    gate_text = ", ".join(gates) or (
        "the project's lint and unit commands (none detected: find them)"
    )
    lines = [
        "Print each command with its exact exit code, its count line and the last 20 lines of "
        "output, ANSI codes stripped.",
        f"Gates first: {gate_text}.",
    ]
    for entry in e2e["commands"]:
        inferred = entry["confidence"] == "inferred"
        suffix = " (inferred: confirm it runs the real app)" if inferred else ""
        lines.append(
            f"E2E: `{entry['command']}` exits 0 and prints a test count above zero. Exit 0 with a "
            f"zero count is not green.{suffix}"
        )
    markers = _marker_labels(e2e["commands"])
    if markers:
        lines.append(f"Zero-count markers: {markers}.")
    else:
        lines.append("Zero-count markers: read the count line yourself.")
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


def rail_sections(
    detect: Mapping[str, Any],
    answers: Mapping[str, Any],
    scope_desc: str,
    phases: Sequence[Mapping[str, Any]],
) -> list[tuple[str, list[str]]]:
    """The eleven labeled sections of D-28, built from detect, answers and the selected phases."""
    native = bool(answers.get("native_execution"))
    opengsd = detect["scope"]["kind"] == "opengsd"
    return [
        ("OBJECTIVE", objective_lines(answers, scope_desc)),
        ("ROLE", role_lines()),
        ("RULES FOR EVERY PLAN", plan_rule_lines(detect["candidate_skills"], native)),
        ("ORDER", order_lines(phases)),
        ("QUOTA", quota_lines(detect["wake"], detect["runner"])),
        ("DECISIONS", decision_lines()),
        ("SAFETY", safety_lines()),
        ("DONE WHEN", done_lines(detect["e2e"], answers.get("mockups") or [])),
        ("CLEANUP", cleanup_lines()),
        ("STOP IF", stop_lines(TURN_CAP, opengsd)),
        ("REPORT", report_lines(detect["jev"])),
    ]
