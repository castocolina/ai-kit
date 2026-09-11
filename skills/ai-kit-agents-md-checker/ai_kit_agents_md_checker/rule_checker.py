"""Workflow-rule prose checker with live tool-presence conditioning.

D-07: a rule whose `condition` is not met in this environment is skipped/
reframed as `"not_applicable"`, never flagged as a generic gap.
"""

from __future__ import annotations

import math

from .rules import CONDITION_ALWAYS, RULES


def evaluate_condition(condition: str, tool_presence: dict) -> bool:
    if condition == CONDITION_ALWAYS:
        return True
    if condition.startswith("tool-presence:"):
        name = condition.split(":", 1)[1]
        return bool(tool_presence.get(name, False))
    return False


def _is_tool_scoped_groups(signals: tuple) -> bool:
    """True when `signals` is R06-shaped: a tuple of `(tool_name, phrases)`.

    Distinguished from R04-shaped plain groups (tuple of tuples-of-phrases,
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


def check_workflow_rules(
    agents_md_text: str, tool_presence: dict, include_present: bool = False
) -> list[dict]:
    """Classify every rule with a non-empty `signals` tuple.

    Filtered by "has non-empty signals", NOT by `category == "workflow"` --
    R02 has `category == "makefile"` for its own Makefile-shape bookkeeping
    but a non-empty `signals` tuple for its separate prose clause, so this
    filter is what brings R02 into workflow-prose checking.
    """
    text = (agents_md_text or "").lower()
    findings: list[dict] = []
    for rule in RULES:
        signals = rule["signals"]
        if not signals:
            continue
        if not evaluate_condition(rule["condition"], tool_presence):
            findings.append(
                {
                    "id": rule["id"],
                    "status": "not_applicable",
                    "reason": (
                        f"condition '{rule['condition']}' not met in this "
                        "environment"
                    ),
                    "matched_signals": [],
                    "criticality": rule["criticality"],
                    "summary": rule["summary"],
                }
            )
            continue

        missing_tools: list[str] | None = None
        if isinstance(signals[0], tuple):
            if _is_tool_scoped_groups(signals):
                status, matched, missing_tools = _classify_tool_scoped_groups(
                    text, signals, tool_presence
                )
            else:
                status, matched = _classify_plain_groups(text, signals)
        else:
            status, matched = _classify_flat(text, signals)

        finding = {
            "id": rule["id"],
            "status": status,
            "matched_signals": matched,
            "criticality": rule["criticality"],
            "summary": rule["summary"],
        }
        if missing_tools is not None:
            finding["missing_tools"] = missing_tools
        findings.append(finding)

    if include_present:
        return findings
    return [f for f in findings if f["status"] != "present"]


__all__ = [
    "check_workflow_rules",
    "evaluate_condition",
]
