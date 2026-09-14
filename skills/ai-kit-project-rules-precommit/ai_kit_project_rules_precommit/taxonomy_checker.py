"""Classify every tool a target repo's `.pre-commit-config.yaml` declares
into exactly one of the shared catalog's six taxonomy categories, with its
confidence recorded (ROADMAP Phase 11 Success Criterion 2).

Resolution order, stopping at the first hit (a hook lands in EXACTLY one of
the outcomes below):

  1. The shared catalog's tool index (baseline entries + D-T7's four cited
     supplements), longest entry first, token-bounded (D-T2). Confidence
     `"baseline"`.
  2. The shared catalog's out-of-taxonomy markers (D-T4). Not a category,
     not a research need.
  3. This skill's own per-stack cache, for every detected stack. Confidence
     `"cache"`, carrying the answering stack and a `stale` boolean (D-T3).
     Runs AFTER step 1 by construction: a cache entry naming a tool the
     catalog already indexes can never reach this step.
  4. The catalog's ambiguous-tool defaults (D-T3). Confidence `"inferred"`.
  5. Nothing matched: unclassified, carrying the detected stacks so a
     research pass knows what to research.

Plan 11-02's Task 3 adds the Duplicate-code/Dead-code absence checks on top
of `classify_precommit_tools`'s result, computed from the classification
rather than a second keyword scan (D-T5) -- not yet present here.
"""

from __future__ import annotations

import os
from typing import cast

from ai_kit_rules_common.criticality import CRITICALITY_MEDIUM
from ai_kit_rules_common.makefile_parse import recipe_mentions_target
from ai_kit_rules_common.precommit_parse import parse_precommit_hooks
from ai_kit_rules_common.stack_detect import detect_stacks
from ai_kit_rules_common.tool_catalog import (
    AMBIGUOUS_TOOL_DEFAULTS,
    OUT_OF_TAXONOMY_GROUPS,
    TAXONOMY_CATEGORIES,
    TOOL_CATEGORY_INDEX,
)

from . import stack_cache

# D-T2: longest catalog entry first, so a longer, more specific entry (e.g.
# "eslint-plugin-security") is never shadowed by a shorter one it contains
# (e.g. "eslint") -- `recipe_mentions_target`'s token-boundary semantics
# already prevent the false match, this ordering is what makes the FIRST
# match found also the most specific one.
_SORTED_INDEX_ENTRIES = tuple(sorted(TOOL_CATEGORY_INDEX, key=len, reverse=True))


def _extract_cached_tool_name(value: str) -> str:
    """A cache payload value is free-form text ending in a `(source: ...)`
    citation (gated by `validate_stack_payload`). Everything before that
    citation parenthesis is the recommended tool name."""
    idx = value.find("(source:")
    tool = value[:idx] if idx != -1 else value
    return tool.strip()


def _classify_one_hook(
    hook_id: str,
    entry: str | None,
    stacks: set[str],
    cache_root: str | None,
) -> dict:
    haystack = f"{hook_id} {entry or ''}".casefold()

    # 1. Catalog index (baseline + D-T7 supplements), longest-first.
    for catalog_entry in _SORTED_INDEX_ENTRIES:
        if recipe_mentions_target(haystack, catalog_entry.casefold()):
            return {
                "outcome": "classified",
                "category": TOOL_CATEGORY_INDEX[catalog_entry],
                "hook": {
                    "hook_id": hook_id,
                    "hook_entry": entry,
                    "matched": catalog_entry,
                    "confidence": "baseline",
                    "stale": False,
                },
            }

    # 2. Out-of-taxonomy markers (D-T4) -- a real third outcome, not a gap.
    for group_name, group in OUT_OF_TAXONOMY_GROUPS.items():
        for marker in cast("tuple[str, ...]", group["markers"]):
            if recipe_mentions_target(haystack, marker.casefold()):
                return {
                    "outcome": "out_of_taxonomy",
                    "hook": {
                        "hook_id": hook_id,
                        "hook_entry": entry,
                        "marker": marker,
                        "group": group_name,
                        "reason": group["reason"],
                    },
                }

    # 3. This skill's own per-stack cache. Unreachable for any tool the
    # index already answers (step 1 ran first).
    for stack in sorted(stacks):
        cache_result = stack_cache.read_stack_cache(stack, cache_root=cache_root)
        data = cache_result["data"] or {}
        for category, cached_value in data.items():
            tool_name = _extract_cached_tool_name(cached_value)
            if tool_name and recipe_mentions_target(haystack, tool_name.casefold()):
                return {
                    "outcome": "classified",
                    "category": category,
                    "hook": {
                        "hook_id": hook_id,
                        "hook_entry": entry,
                        "matched": tool_name,
                        "confidence": "cache",
                        "stale": cache_result["state"] == "stale",
                        "stack": stack,
                    },
                }

    # 4. Ambiguous-tool defaults (D-T3's `inferred` path).
    for tool_name, category in AMBIGUOUS_TOOL_DEFAULTS.items():
        if recipe_mentions_target(haystack, tool_name.casefold()):
            return {
                "outcome": "classified",
                "category": category,
                "hook": {
                    "hook_id": hook_id,
                    "hook_entry": entry,
                    "matched": tool_name,
                    "confidence": "inferred",
                    "stale": False,
                },
            }

    # 5. Nothing matched.
    return {
        "outcome": "unclassified",
        "hook": {
            "hook_id": hook_id,
            "hook_entry": entry,
            "stacks": sorted(stacks),
        },
    }


def classify_precommit_tools(
    repo_root: str,
    cache_root: str | None = None,
    detected_stacks: set[str] | None = None,
) -> dict:
    """Classify every hook `repo_root`'s `.pre-commit-config.yaml` declares.

    Returns `{"taxonomy": {category: [hook, ...] for each of the six
    categories}, "out_of_taxonomy": [hook, ...], "unclassified": [hook,
    ...]}`. Every hook appears in EXACTLY one outcome -- the first-hit
    resolution order in `_classify_one_hook` is what guarantees it.

    `detected_stacks` is an injectable override (defaults to
    `detect_stacks(repo_root)`) so a caller can classify against a
    synthetic stack set without needing real marker files on disk.
    """
    precommit_path = os.path.join(repo_root, ".pre-commit-config.yaml")
    hooks = parse_precommit_hooks(precommit_path)
    stacks = detect_stacks(repo_root) if detected_stacks is None else detected_stacks

    taxonomy: dict[str, list[dict]] = {category: [] for category in TAXONOMY_CATEGORIES}
    out_of_taxonomy: list[dict] = []
    unclassified: list[dict] = []

    for hook_id in sorted(hooks):
        entry = hooks[hook_id]
        outcome = _classify_one_hook(hook_id, entry, stacks, cache_root)
        if outcome["outcome"] == "classified":
            taxonomy[outcome["category"]].append(outcome["hook"])
        elif outcome["outcome"] == "out_of_taxonomy":
            out_of_taxonomy.append(outcome["hook"])
        else:
            unclassified.append(outcome["hook"])

    return {
        "taxonomy": taxonomy,
        "out_of_taxonomy": out_of_taxonomy,
        "unclassified": unclassified,
    }


def build_unclassified_findings(classification: dict) -> list[dict]:
    """D-T6's pinned vocabulary for a hook the catalog cannot answer:
    `category: "tool-taxonomy"`, `issue: "unclassified_tool"`, medium
    criticality, `needs_research: True`, no `recommendation` (routes to
    `blocked` rather than guessing)."""
    findings = []
    for hook in classification["unclassified"]:
        hook_id = hook["hook_id"]
        summary = (
            f"pre-commit hook '{hook_id}' does not match the shared catalog, "
            "any out-of-taxonomy marker, or any per-stack cache entry -- "
            "its taxonomy category needs research"
        )
        findings.append(
            {
                "category": "tool-taxonomy",
                "issue": "unclassified_tool",
                "target": hook_id,
                "hook_id": hook_id,
                "recommendation": None,
                "needs_research": True,
                "criticality": CRITICALITY_MEDIUM,
                "summary": summary,
                "stacks": hook.get("stacks", []),
            }
        )
    return findings


__all__ = [
    "build_unclassified_findings",
    "classify_precommit_tools",
]
