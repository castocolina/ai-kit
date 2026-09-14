"""Tool-pair evaluation against the design spec's locked "Confirmed
redundant-vs-complementary pairs" table (ROADMAP Phase 11 Success
Criterion 5's golangci clause, 11-CONTEXT D-03/D-04).

This module adds NO tool knowledge of its own. Every relationship
judgement is sourced to the shared catalog's own
`REDUNDANT_VS_COMPLEMENTARY_PAIRS` table -- a row, or nothing. This module
iterates that table directly (rather than enumerating ad-hoc pairs of
detected tools and hoping to find a row for them) precisely so the tenth
row's skip is an EXPLICIT, mark-driven decision rather than an accident of
a name failing to match: see below.

Nothing (11-CONTEXT D-04) is presumed-complementary, the default, and is
never flagged: an unresearched pair flagged as redundant would claim
confidence this skill does not have, which PROJECT.md's core value
forbids. Do NOT substitute a heuristic, a same-category-implies-redundant
rule, or a "probably" here -- the pairs table simply never being asked
about a pair it does not carry IS the whole mechanism, and this is the one
place a future contributor is most likely to "fix" by adding a fallback.

One row of the ten-row table is deliberately out of this mechanism's
reach: the Python row pairing a linter's security RULE FAMILY (`ruff S`
rules) against a dedicated security scanner (`bandit`) is not a pair of
hooks -- one side is a rule selector inside another tool's configuration,
which no repo runs as its own hook. Plan 11-02 marked that member in
`rule_family_members` precisely so this module can recognize and skip the
row BY READING THE MARK, before ever asking whether either member is
"present" -- never by relying on "ruff S rules" simply never matching a
real hook id (which it never would anyway, making that skip invisible and
untested rather than a documented limit). Generic hook-pair evaluation
therefore covers NINE of the ten researched rows; the tenth is a
configuration-family relationship this skill does not evaluate. This
module never invents a hook name for the rule family to make the count
reach ten, never drops the row from the table, and never folds it into
`ruff_checks.py`'s three named ruff clauses (that would widen ROADMAP
SC5's scope beyond what this plan has).
"""

from __future__ import annotations

import os

from ai_kit_rules_common.criticality import CRITICALITY_MEDIUM
from ai_kit_rules_common.tool_catalog import REDUNDANT_VS_COMPLEMENTARY_PAIRS

from . import config_read
from .taxonomy_checker import classify_precommit_tools

# Relationships this module flags, and their D-C7-pinned issue values.
# "complementary"/"overlapping" emit nothing (the spec is explicit that a
# fast/narrow tool paired with a slow/wide one for different failure
# classes is intentional layering -- flagging it would train a user to
# ignore this skill).
_FLAGGED_ISSUE_BY_RELATIONSHIP = {
    "redundant": "confirmed_redundant_pair",
    "supersession": "superseded_tool",
}


def _detected_tool_names(repo_root: str) -> set[str]:
    """Every tool name this run's classification actually placed into a
    category -- the `matched` catalog-entry string, preserving the
    catalog's own casing, which is what the pairs table's `tools` tuples
    use verbatim."""
    classification = classify_precommit_tools(repo_root)
    names: set[str] = set()
    for hooks in classification["taxonomy"].values():
        for hook in hooks:
            matched = hook.get("matched")
            if isinstance(matched, str):
                names.add(matched)
    return names


def _pair_finding(tool_a: str, tool_b: str, row: dict) -> dict | None:
    relationship = row["relationship"]
    issue = _FLAGGED_ISSUE_BY_RELATIONSHIP.get(relationship)
    if issue is None:
        return None
    recommendation = (
        f"'{tool_a}' and '{tool_b}' ({row['ecosystem']}) are a "
        f"{relationship} pair -- {row['reason']}"
    )
    return {
        "category": "tool-pair",
        "issue": issue,
        "tools": [tool_a, tool_b],
        "ecosystem": row["ecosystem"],
        "relationship": relationship,
        "recommendation": recommendation,
        "needs_research": False,
        "advisory": True,
        "criticality": CRITICALITY_MEDIUM,
        "summary": recommendation,
    }


# The Go golangci-lint precondition (ROADMAP SC5's final clause). The
# spec's ONE confirmed fully-redundant Go pairing is confirmed BECAUSE the
# bundling tool has that linter enabled. `enable:` alone is ADDITIVE in
# golangci-lint -- it does NOT replace the default set (cross-AI review
# cycle 3, LOW: corrected from earlier imprecise prose). The default set
# is only replaced when `disable-all: true` (or `default: none`) is
# paired with an `enable:` list. So: the bundled linter counts as enabled
# unless the configuration explicitly disables it (a `disable:` list
# naming it), OR the configuration replaces the default set with one that
# omits it (`disable-all: true`/`default: none` plus an `enable:` list
# that does not name it). With no golangci configuration present at all,
# the default set applies and the finding stands -- the spec's own Go
# baseline row names that linter among the defaults. No other row in the
# table carries a precondition today; this is a data-shaped check (keyed
# off the row's own ecosystem/relationship), never a second branch a later
# row would have to duplicate.
_GOLANGCI_CANDIDATES = (".golangci.yml", ".golangci.yaml", ".golangci.toml", ".golangci.json")


def _identity_reader(path: str) -> str:
    return path


def _golangci_bundles_staticcheck(repo_root: str) -> bool:
    matched, _content = config_read.first_existing_candidate(
        repo_root, _GOLANGCI_CANDIDATES, _identity_reader
    )
    if matched is None:
        # No config at all: the default set applies, and staticcheck is
        # among the defaults (the spec's own Go baseline row).
        return True
    abs_path = os.path.join(repo_root, matched)

    disable = config_read.read_config_value(abs_path, ("linters", "disable"))
    disable_list = disable if isinstance(disable, list) else []
    if any(isinstance(item, str) and item.strip() == "staticcheck" for item in disable_list):
        return False

    disable_all = config_read.read_config_value(abs_path, ("linters", "disable-all"))
    default_mode = config_read.read_config_value(abs_path, ("linters", "default"))
    replaces_default_set = (
        isinstance(disable_all, str) and disable_all.strip().lower() == "true"
    ) or (isinstance(default_mode, str) and default_mode.strip().lower() == "none")
    if replaces_default_set:
        enable = config_read.read_config_value(abs_path, ("linters", "enable"))
        enable_list = enable if isinstance(enable, list) else []
        return any(
            isinstance(item, str) and item.strip() == "staticcheck" for item in enable_list
        )

    return True


def build_pair_findings(repo_root: str) -> list[dict]:
    """Evaluate the shared catalog's locked pairs table directly, row by
    row -- never an ad-hoc enumeration of detected-tool combinations. For
    each row:

    1. A row carrying a `rule_family_members` mark is skipped EXPLICITLY,
       before either member's presence is even checked (D-03's tenth row).
    2. Otherwise, both members must be present in this run's
       classification (a set-membership check against
       `_detected_tool_names`) for the row to apply at all.
    3. The Go redundancy row is additionally gated on
       `_golangci_bundles_staticcheck`.
    4. `redundant`/`supersession` emit one finding each;
       `complementary`/`overlapping` (and any pair with no row at all --
       D-04's default, since this loop never considers a pair outside the
       table) emit nothing.

    One finding per unordered pair: this loop visits each table row
    exactly once, so a pair cannot be double-counted regardless of how
    many OTHER tools share its category in the same repo.
    """
    detected = _detected_tool_names(repo_root)
    findings: list[dict] = []

    for row in REDUNDANT_VS_COMPLEMENTARY_PAIRS:
        if row.get("rule_family_members"):
            continue
        tool_a, tool_b = row["tools"]
        if tool_a not in detected or tool_b not in detected:
            continue

        if row["ecosystem"] == "Go" and row["relationship"] == "redundant":
            if not _golangci_bundles_staticcheck(repo_root):
                continue

        finding = _pair_finding(tool_a, tool_b, row)
        if finding is not None:
            findings.append(finding)

    return findings


__all__ = ["build_pair_findings"]
