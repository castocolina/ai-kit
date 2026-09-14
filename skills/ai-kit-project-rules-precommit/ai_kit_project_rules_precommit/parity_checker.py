"""Bidirectional Makefile <-> `.pre-commit-config.yaml` parity check
(ROADMAP Phase 11 Success Criterion 1, this plan's D-P1/D-P2/D-P3/D-P4).

OWNERSHIP NOTE (D-P3): the sibling `ai-kit-project-rules-makefile` skill
already unions pre-commit hook ids into its own required Makefile target
set, so a hook with no matching target produces a `makefile`-kind finding
THERE and a `precommit-parity`-kind `hook_without_target` finding HERE for
the very same hook. This is a KNOWN, DELIBERATE cross-domain overlap, not a
bug: the sibling's finding says "add this target" (a Makefile-completeness
concern), this skill's finding says "the two files disagree about the tool
set" (a parity concern). Neither is suppressed here, this module never
reaches into the sibling to deduplicate, and this module never reuses the
sibling's `issue` strings. Phase 15's orchestrator is the only component
allowed to merge across domains (`.planning/intel/constraints.md`,
cross-skill remediation merging ownership).
"""

from __future__ import annotations

import os
import re

from ai_kit_rules_common.criticality import CRITICALITY_HIGH
from ai_kit_rules_common.makefile_parse import (
    parse_makefile_prerequisites,
    parse_makefile_recipe,
    parse_makefile_targets,
)
from ai_kit_rules_common.precommit_parse import parse_precommit_hooks
from ai_kit_rules_common.tool_catalog import resolve_tool_category

# D-P2 clause (ii)'s pinned vocabulary: the sibling skill's `validate-<...>`
# alias family (`CATEGORY_ALIAS_MAP` in
# `ai_kit_project_rules_makefile/makefile_checker.py`) plus its bare
# category short-names. Read, never imported -- this skill does not import
# the sibling's package (constraints.md shared-package import convention).
_CLAUSE_II_ALIASES = (
    "validate-format",
    "validate-security",
    "validate-lint",
    "validate-duplicate",
    "validate-dead",
)
_CLAUSE_II_SHORT_NAMES = ("format", "lint", "security", "duplicate", "dead")
_CLAUSE_II_NAMES = frozenset(_CLAUSE_II_ALIASES) | frozenset(_CLAUSE_II_SHORT_NAMES)

# D-P2 clause (i): the token sequence `pre-commit run <hook-id>`, anywhere
# on a real recipe line, behind any leading runner prefix (`uv run`,
# `poetry run`, `npx`, `env VAR=x`, ...) -- never enumerated, simply
# ignored by searching rather than anchoring. Token-boundary semantics
# mirror `recipe_mentions_target`'s: `pre-commit` and `run` each require a
# non-identifier/non-hyphen character (or start-of-line) immediately
# before them, so `my-pre-commit run x` or `overrun x` cannot false-match.
# The captured group is "the token immediately after `run`" -- the
# delegated hook id.
_DELEGATE_RE = re.compile(
    r"(?<![-\w])pre-commit(?![-\w])[ \t]+(?<![-\w])run(?![-\w])[ \t]+(\S+)"
)

# Clause (iii)'s ONE runner-prefix recognizer (plan 11-02). Generic --
# recognizes the SHAPE "<runner> run <rest>" (this repository's own
# convention, `uv run <tool> <args>`, e.g. `Makefile:109-110`/`:116-117`),
# never a specific runner name. Clause (i) needs no equivalent of its own:
# its `_DELEGATE_RE` search is already prefix-agnostic because it searches
# for the FIXED LITERAL `pre-commit run` anywhere on the line, so whatever
# precedes it (`uv run`, `poetry run`, `env VAR=x`, or nothing) never has to
# be identified. Clause (iii) has no fixed literal to anchor a search
# around -- it must name the first real token itself -- which is why this
# is the ONE prefix-recognition helper this predicate needs, at exactly one
# call site.
_RUNNER_PREFIX_RE = re.compile(
    r"^(?<![-\w])[A-Za-z0-9_.-]+(?![-\w])[ \t]+(?<![-\w])run(?![-\w])[ \t]+"
)


def _first_token_after_runner_prefix(line: str) -> str | None:
    """Strip a leading `<runner> run` prefix (if present) and return the
    first remaining whitespace-delimited token, or `None` if nothing
    remains."""
    stripped = _RUNNER_PREFIX_RE.sub("", line, count=1)
    tokens = stripped.split()
    return tokens[0] if tokens else None


def normalize_name(name: str) -> str:
    """D-P1: casefold, with `_` folded to `-`.

    A hook id and a Makefile target match when their normalized forms are
    equal -- not exact-string (`py_compile`/`py-compile` are the same
    tool), and not fuzzy/substring (`ruff`/`ruff-format` are two different
    tools in two different taxonomy categories, so this function never
    strips suffixes or checks containment)."""
    return name.strip().casefold().replace("_", "-")


def _real_recipe_lines(recipe_text: str) -> list[str]:
    """Real lines of a recipe: blank lines and comment-only lines (first
    non-whitespace character starts a Make comment) are never real."""
    lines = []
    for line in recipe_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    return lines


def classify_target_shape(name: str, recipe_text: str, prerequisites: set[str]) -> dict:
    """D-P2: is `name` a "single-tool Makefile target" -- a SHAPE, not a
    name list?

    Returns `{"tool_shaped": bool, "clause": "i"|"ii"|None, "identity":
    str|None}`. `identity` is the name to match against pre-commit hook ids
    via `normalize_name`: for a clause-(i) delegate it is the delegated
    hook id extracted from the recipe (e.g. a `validate-dead` target
    delegating to `pre-commit run vulture` matches a `vulture` hook, not a
    `validate-dead` one -- the recipe's own delegation makes the tool
    identity unambiguous); for a clause-(ii) short-name/alias match it is
    the target's own name, since there is no recipe to extract an id from.

    THE ONE PREDICATE plan 11-02 extends with clause (iii) over the shared
    catalog's real tool names -- every tool-shaped judgement routes through
    this function, which is why 11-02 has exactly one place to add it.
    Clause (iii): a target whose OWN NAME resolves via the shared catalog's
    `resolve_tool_category`, OR whose single recipe line's tool token
    (after skipping a leading `<runner> run` prefix) resolves, is
    tool-shaped -- `identity` is the target's own name either way (matching
    clause (ii)'s convention: Direction B then asks "is there a hook of
    that target's name").

    The ≤2-real-line cap is a GLOBAL AND over every clause, evaluated
    FIRST: a recipe exceeding it is never tool-shaped no matter what it is
    named, so a later clause cannot bypass it and reclassify a long recipe
    as a single tool. A target with prerequisites and an empty recipe is an
    AGGREGATE (no single hook it could correspond to) and is never
    tool-shaped either, regardless of clause.
    """
    real_lines = _real_recipe_lines(recipe_text)
    not_shaped = {"tool_shaped": False, "clause": None, "identity": None}

    if len(real_lines) > 2:
        return not_shaped
    if not real_lines and prerequisites:
        return not_shaped

    for line in real_lines:
        match = _DELEGATE_RE.search(line)
        if match is not None:
            return {"tool_shaped": True, "clause": "i", "identity": match.group(1)}

    if normalize_name(name) in _CLAUSE_II_NAMES:
        return {"tool_shaped": True, "clause": "ii", "identity": name}

    # Clause (iii), a THIRD OR, evaluated under the SAME cap as clauses (i)
    # and (ii) (both early-return checks above already ran) -- never beside
    # it, never bypassing it.
    if resolve_tool_category(name) is not None:
        return {"tool_shaped": True, "clause": "iii", "identity": name}

    if len(real_lines) == 1:
        candidate = _first_token_after_runner_prefix(real_lines[0])
        if candidate is not None and resolve_tool_category(candidate) is not None:
            return {"tool_shaped": True, "clause": "iii", "identity": name}

    return not_shaped


def check_parity(repo_root: str) -> list[dict]:
    """Bidirectional Makefile/`.pre-commit-config.yaml` parity check (SC1).

    Direction A (hook -> target): for every hook id, if no Makefile target
    normalizes to the same name (D-P1), emit `issue: "hook_without_target"`
    naming the hook id, its `entry:` command when it has one, and
    recommending the single-tool target that would satisfy it. This
    direction is name-based only -- it does not consult
    `classify_target_shape` -- because a target with ANY name that already
    normalizes to the hook id is already satisfying it.

    Direction B (target -> hook): for every TOOL-SHAPED Makefile target
    (via `classify_target_shape`), if no hook id normalizes to that
    target's effective identity, emit `issue: "target_without_hook"`
    naming the target and recommending EITHER a matching hook OR an
    explicit statement that the target is deliberately non-gating (D-P2b,
    mandatory in every finding this direction produces -- this repository's
    own `format`, `security-scanner` and `duplicate-code` targets are
    deliberately outside its gate and say so in Makefile comments, so a
    recommendation that only ever said "add a hook" would tell a
    maintainer to undo a considered decision).

    Both directions carry `category: "precommit-parity"`, `CRITICALITY_HIGH`,
    `needs_research: False`, a `recommendation`, and a `summary` equal to
    the recommendation. Neither direction stands in for the other: a repo
    failing both produces two findings.

    Degradation, not crashes: an absent `Makefile` means every hook is
    unmatched (direction A fires for all of them, direction B has nothing
    to iterate); an absent `.pre-commit-config.yaml` means every
    tool-shaped target is unmatched. Both shared parsers already return
    empty results for an absent file -- this function adds no second
    existence check with different semantics.
    """
    makefile_path = os.path.join(repo_root, "Makefile")
    precommit_path = os.path.join(repo_root, ".pre-commit-config.yaml")

    targets = parse_makefile_targets(makefile_path)
    hooks = parse_precommit_hooks(precommit_path)

    normalized_targets = {normalize_name(t): t for t in targets}
    normalized_hooks = {normalize_name(h): h for h in hooks}

    findings: list[dict] = []

    # Direction A: hook -> target.
    for hook_id in sorted(hooks):
        if normalize_name(hook_id) in normalized_targets:
            continue
        entry = hooks[hook_id]
        delegate = f"uv run pre-commit run {hook_id} --all-files"
        recommendation = (
            f"add a Makefile target for pre-commit hook '{hook_id}' "
            f"(e.g. `{delegate}`)"
        )
        if entry:
            recommendation += f" -- the hook's own `entry:` command is: {entry}"
        findings.append(
            {
                "category": "precommit-parity",
                "issue": "hook_without_target",
                "hook_id": hook_id,
                "entry": entry,
                "recommendation": recommendation,
                "needs_research": False,
                "criticality": CRITICALITY_HIGH,
                "summary": recommendation,
            }
        )

    # Direction B: tool-shaped target -> hook.
    for target in sorted(targets):
        recipe_text = parse_makefile_recipe(makefile_path, target)
        prerequisites = parse_makefile_prerequisites(makefile_path, target)
        shape = classify_target_shape(target, recipe_text, prerequisites)
        if not shape["tool_shaped"]:
            continue
        identity = shape["identity"]
        if normalize_name(identity) in normalized_hooks:
            continue
        recommendation = (
            f"target '{target}' has no matching pre-commit hook for '{identity}' -- "
            f"either add a pre-commit hook id matching '{identity}', or record in the "
            f"Makefile (a comment beside the '{target}' target) that it is "
            "deliberately non-gating"
        )
        findings.append(
            {
                "category": "precommit-parity",
                "issue": "target_without_hook",
                "target": target,
                "identity": identity,
                "clause": shape["clause"],
                "recommendation": recommendation,
                "needs_research": False,
                "criticality": CRITICALITY_HIGH,
                "summary": recommendation,
            }
        )

    return findings


__all__ = ["check_parity", "classify_target_shape", "normalize_name"]
