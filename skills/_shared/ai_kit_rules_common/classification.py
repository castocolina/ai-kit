"""Generic rule-classification engine (moved from
`ai-kit-project-rules-agents/ai_kit_project_rules_agents/
rule_checker.py`, generalized to take a `rules` tuple as a parameter
instead of importing one fixed module's `RULES`).

A rule whose `condition` is not met in the caller's environment is
skipped/reframed as `"not_applicable"`, never flagged as a generic gap.
"""

from __future__ import annotations

import functools
import math
import re
from collections.abc import Sequence
from decimal import Decimal

CONDITION_ALWAYS = "always"
CONDITION_OPENGSD = "opengsd"
CONDITION_STACK_DETECTED = "stack-detected"

# 26 D-27 / SPEC R9: a stated share above this cap is a finding (40% of the available CPUs).
_SHARE_CAP = Decimal("40")
_PROSE_SHARE_RE = re.compile(
    r"(\d+(?:\.\d+)?)%\s+of\s+(?:the\s+)?(?:available\s+)?(?:cpus?|cores?|processors?)\b"
)
_TEST_WORD_RE = re.compile(r"\btests?\b")
# A count follows the flag after `=` or spaces; a suffix `%` (the number is the share) or `c`
# (the number is a per-core multiplier, so 0.41c is 41%). A literal count carries no suffix.
_COUNT_AFTER = r"(?:\s*=\s*|\s+)(\d+(?:\.\d+)?)(%|c)?(?!\w)"
_UNVERIFIED_CLAUSE = (
    "{stack}: no verified form exists; follow the rule above with this stack's own test "
    "runner (unverified)."
)


def condition_state(condition: str, tool_presence: dict) -> str:
    """Tri-state: `"met"`, `"unmet"` or `"unverified"`.

    `unverified` is only produced by the `opengsd` identity probe (26 D-19): the rule is not
    applicable, but the caller must report that it could not be proven, never silently skip it.
    """
    if condition == CONDITION_ALWAYS:
        return "met"
    if condition.startswith("tool-presence:"):
        name = condition.split(":", 1)[1]
        return "met" if tool_presence.get(name, False) else "unmet"
    if condition == CONDITION_OPENGSD:
        status = tool_presence.get("opengsd")
        if status == "ok":
            return "met"
        if status == "unverified":
            return "unverified"
    if condition == CONDITION_STACK_DETECTED:
        return "met" if tool_presence.get("stacks") else "unmet"
    return "unmet"


def evaluate_condition(condition: str, tool_presence: dict) -> bool:
    return condition_state(condition, tool_presence) == "met"


def _not_applicable(rule: dict, state: str, tool_presence: dict) -> dict:
    if state == "unverified":
        reason = (
            f"condition '{rule['condition']}' unverified: "
            f"{tool_presence.get(rule['condition'] + '_reason', 'not proven')}"
        )
        finding = {
            "id": rule["id"],
            "status": "not_applicable",
            "unverified": True,
            "reason": reason,
        }
    else:
        finding = {
            "id": rule["id"],
            "status": "not_applicable",
            "reason": f"condition '{rule['condition']}' not met in this environment",
        }
    finding.update(
        {
            "matched_signals": [],
            "criticality": rule["criticality"],
            "summary": rule["summary"],
        }
    )
    if rule.get("verbatim"):
        finding["verbatim"] = True
    return finding


def _is_tool_scoped_groups(signals: tuple) -> bool:
    """True when `signals` is shaped as a tuple of `(tool_name, phrases)`.

    Distinguished from plain grouped signals (tuple of tuples-of-phrases,
    every element a plain string) by the presence of a nested tuple as the
    SECOND element of the first group.
    """
    group0 = signals[0]
    return (
        isinstance(group0, tuple)
        and len(group0) == 2
        and isinstance(group0[0], str)
        and isinstance(group0[1], tuple)
    )


def _classify_flat(text: str, signals: tuple) -> tuple[str, list[str]]:
    matched = sorted(p for p in signals if p in text)
    n_matched = len(matched)
    n_total = len(signals)
    if n_matched == 0:
        return "missing", matched
    if n_matched == n_total or (n_total >= 3 and n_matched >= math.ceil(n_total / 2)):
        return "present", matched
    return "near_miss", matched


def _classify_plain_groups(text: str, groups: tuple) -> tuple[str, list[str]]:
    matched: set[str] = set()
    satisfied = 0
    for group in groups:
        group_matches = [p for p in group if p in text]
        if group_matches:
            satisfied += 1
            matched.update(group_matches)
    if satisfied == 0:
        status = "missing"
    elif satisfied == len(groups):
        status = "present"
    else:
        status = "near_miss"
    return status, sorted(matched)


def _classify_tool_scoped_groups(
    text: str, groups: tuple, tool_presence: dict
) -> tuple[str, list[str], list[str]]:
    required = [
        (tool_name, phrases)
        for tool_name, phrases in groups
        if tool_presence.get(f"modern-cli:{tool_name}", False)
    ]
    if not required:
        return "not_applicable", [], []
    matched: set[str] = set()
    missing_tools: list[str] = []
    satisfied = 0
    for tool_name, phrases in required:
        group_matches = [p for p in phrases if p in text]
        if group_matches:
            satisfied += 1
            matched.update(group_matches)
        else:
            missing_tools.append(tool_name)
    if satisfied == 0:
        status = "missing"
    elif satisfied == len(required):
        status = "present"
    else:
        status = "near_miss"
    return status, sorted(matched), sorted(missing_tools)


@functools.cache
def _flag_pattern(flag: str) -> re.Pattern[str]:
    """A dash flag (or build-setting word) only at a token start, then its count."""
    return re.compile(rf"(?<![\w-]){re.escape(flag.lower())}{_COUNT_AFTER}")


@functools.cache
def _runner_pattern(runner: str) -> re.Pattern[str]:
    """A runner phrase: its words in order as whole words, up to 200 characters between them.

    The gap is bounded so one very long line scans in linear time (T-26-30).
    """
    words = [re.escape(word) for word in runner.lower().split()]
    return re.compile(r"\b" + r"\b.{0,200}\b".join(words) + r"\b")


def _count_is_hardcoded(number: str, suffix: str) -> bool:
    if not suffix:
        return True
    share = Decimal(number) * (100 if suffix == "c" else 1)
    return share > _SHARE_CAP


def _flags_hardcode_count(line: str, flags: Sequence[str]) -> bool:
    for flag in flags:
        for match in _flag_pattern(flag).finditer(line):
            if _count_is_hardcoded(match.group(1), match.group(2) or ""):
                return True
    return False


def _line_is_hardcoded(line: str, forms: Sequence[dict], generic_flags: Sequence[str]) -> bool:
    if any(Decimal(m.group(1)) > _SHARE_CAP for m in _PROSE_SHARE_RE.finditer(line)):
        return True
    if _TEST_WORD_RE.search(line) and _flags_hardcode_count(line, generic_flags):
        return True
    for form in forms:
        runners = form["runners"]
        # A row with no catalog runner (Gradle) scans its build-setting words on every line.
        if runners and not any(_runner_pattern(runner).search(line) for runner in runners):
            continue
        if _flags_hardcode_count(line, form["count_flags"]):
            return True
    return False


def hardcoded_worker_counts(
    text: str, forms: Sequence[dict], generic_flags: Sequence[str]
) -> list[str]:
    """Stripped lines of `text` that state a literal worker count or a share above 40%.

    A literal count or a share over the cap next to a test command is a finding (26 D-27).
    Each line appears once, in text order.
    """
    found: list[str] = []
    seen: set[str] = set()
    for raw in (text or "").splitlines():
        stripped = raw.strip()
        if not stripped or stripped in seen:
            continue
        if _line_is_hardcoded(raw.lower(), forms, generic_flags):
            seen.add(stripped)
            found.append(stripped)
    return found


def _form_selection(
    stacks: Sequence[str], markers: Sequence[str], forms: Sequence[dict]
) -> tuple[list[str], list[str], list[dict]]:
    """Clauses (deduplicated, in stack then table order), unverified stacks, selected rows."""
    clauses: list[str] = []
    unverified: list[str] = []
    selected: list[dict] = []
    for stack in stacks:
        rows = [
            row
            for row in forms
            if row["stack"] == stack and any(marker in markers for marker in row["markers"])
        ]
        if not rows:
            unverified.append(stack)
            clause = _UNVERIFIED_CLAUSE.format(stack=stack)
            if clause not in clauses:
                clauses.append(clause)
            continue
        selected.extend(rows)
        for row in rows:
            if row["clause"] not in clauses:
                clauses.append(row["clause"])
    return clauses, unverified, selected


def _stack_form_status(generic_status: str, row_flags: list[bool], has_counts: bool) -> str:
    if has_counts:
        return "near_miss"
    if generic_status == "present" and all(row_flags):
        return "present"
    if generic_status == "missing" and not any(row_flags):
        return "missing"
    return "near_miss"


def _row_hits(selected: Sequence[dict], lowered: str) -> tuple[list[bool], set[str]]:
    """Per selected row, whether any of its signals is in the text, and the phrases hit."""
    flags: list[bool] = []
    matched: set[str] = set()
    for row in selected:
        hits = [phrase for phrase in row["signals"] if phrase in lowered]
        flags.append(bool(hits))
        matched.update(hits)
    return flags, matched


def _stack_form_finding(rule: dict, text: str, presence: dict) -> dict:
    """R20-shaped rule (`stack_forms`): the generic groups, each selected stack row, the counts.

    Unverified stacks do not lower the status: the clause the user writes says so, and the
    composed text must classify as present (26 D-27 round trip).
    """
    lowered = text.lower()
    generic_status, generic_matched = _classify_plain_groups(lowered, rule["signals"])
    stacks = list(presence.get("stacks", []))
    clauses, unverified, selected = _form_selection(
        stacks, list(presence.get("stack_markers", [])), rule["stack_forms"]
    )
    row_flags, row_matched = _row_hits(selected, lowered)
    counts = hardcoded_worker_counts(text, rule["stack_forms"], rule["count_flags"])
    finding = {
        "id": rule["id"],
        "status": _stack_form_status(generic_status, row_flags, bool(counts)),
        "matched_signals": sorted(set(generic_matched) | row_matched),
        "criticality": rule["criticality"],
        "summary": "\n".join([rule["summary"], *clauses]),
        "signals": rule["signals"],
        "stacks": stacks,
        "unverified_stacks": unverified,
        "hardcoded_counts": counts,
    }
    if rule.get("verbatim"):
        finding["verbatim"] = True
    return finding


def check_rules(
    text: str,
    tool_presence: dict,
    rules: tuple[dict, ...],
    include_present: bool = False,
) -> list[dict]:
    """Classify every rule in `rules` with a non-empty `signals` tuple.

    Filtered by "has non-empty signals", NOT by any `category` field --
    a caller's rule may carry a category label for its own bookkeeping
    while still having a signals-checkable prose clause.
    """
    lowered = (text or "").lower()
    findings: list[dict] = []
    for rule in rules:
        signals = rule["signals"]
        if not signals:
            continue
        state = condition_state(rule["condition"], tool_presence)
        if state != "met":
            findings.append(_not_applicable(rule, state, tool_presence))
            continue

        if rule.get("stack_forms") is not None:
            findings.append(_stack_form_finding(rule, text or "", tool_presence))
            continue

        missing_tools: list[str] | None = None
        if isinstance(signals[0], tuple):
            if _is_tool_scoped_groups(signals):
                status, matched, missing_tools = _classify_tool_scoped_groups(
                    lowered, signals, tool_presence
                )
            else:
                status, matched = _classify_plain_groups(lowered, signals)
        else:
            status, matched = _classify_flat(lowered, signals)

        finding = {
            "id": rule["id"],
            "status": status,
            "matched_signals": matched,
            "criticality": rule["criticality"],
            "summary": rule["summary"],
            "signals": signals,
        }
        if missing_tools is not None:
            finding["missing_tools"] = missing_tools
        if rule.get("verbatim"):
            finding["verbatim"] = True
        findings.append(finding)

    if include_present:
        return findings
    return [f for f in findings if f["status"] != "present"]


__all__ = [
    "CONDITION_ALWAYS",
    "CONDITION_OPENGSD",
    "CONDITION_STACK_DETECTED",
    "check_rules",
    "condition_state",
    "evaluate_condition",
    "hardcoded_worker_counts",
]
