"""This skill's aggregator (REQ-rules-arch), plan 12-01's tracer subject.

Scope boundary: this skill checks the FORM of a repo's architecture-fitness
Makefile wiring -- does an arch-test-shaped target exist, and does it
actually run when `test` runs -- and deliberately does NOT attempt
dependency-direction or layering-boundary enforcement across a repo's
source tree. That fuller ambition is a known gap this milestone does not
close (ROADMAP Phase 12, backlog "Phase 999.3").

`check_arch_rules(repo_root)` is a flat-list aggregator plan 12-02 extends
by appending ONE call inside the target-FOUND branch below (the AST-only
check), plus recommendation text attached to the missing-target finding in
the target-ABSENT branch (the per-stack canonical-tool text) -- never a
uniform two-call extension, and never a fourth top-level call.

Every finding this module returns carries EXACTLY the six fields D-A3
pins: `category`, `issue`, `criticality`, `summary`, `recommendation`,
`needs_research`. No finding ever carries a `target` key -- `remediation.py`'s
`build_remediation` reads `finding.get("target", finding.get("category"))`,
so a `target` key would silently repoint the remediate `id` at a Makefile
target name instead of the finding's `category`, collapsing this skill's two
findings' ids together (and colliding with an unrelated `makefile` finding
about a same-named target in the merged list Phase 15 reads). Name the
target inside `summary`/`recommendation` prose instead.
"""

from __future__ import annotations

import os
import re
from collections import deque

from ai_kit_rules_common.criticality import CRITICALITY_HIGH
from ai_kit_rules_common.makefile_parse import (
    parse_makefile_prerequisites,
    parse_makefile_recipe,
    parse_makefile_targets_ordered,
    recipe_mentions_target,
)

# D-A1 -- arch-test-SHAPED is a naming RULE, not a literal. Normalize a
# target name by casefolding it and folding `_` to `-`, then fully match
# EITHER pattern below with `re.fullmatch` (no trailing `$` in either
# pattern -- `fullmatch` already anchors both ends; combining it with an
# explicit `$` is the belt-and-braces D-A1 forbids, because it makes the
# obvious non-vacuity mutation -- dropping a `$` -- a silent no-op).
_ARCH_SHAPE_PATTERN_DIRECT = r"(arch|architecture)(-(test|tests|check|checks|lint|fitness|rules))?"
_ARCH_SHAPE_PATTERN_PREFIXED = r"(test|check|lint)-(arch|architecture)(-(test|tests|check|checks))?"

# D-A2 clause (ii) -- the prerequisite-graph walk's two termination guards,
# written first rather than as later hardening (T-12-01). Reaching either
# bound before the target is found ends the walk and falls through to
# clause (iii); it never by itself decides the target IS chained.
_CHAIN_DEPTH_BOUND = 8
_CHAIN_BREADTH_BOUND = 512


def normalize_target_name(name: str) -> str:
    """D-A1's normalization: casefold, then fold `_` to `-`."""
    return name.casefold().replace("_", "-")


def is_arch_test_shaped(name: str) -> bool:
    """D-A1's shape predicate -- fully anchored, single mechanism
    (`re.fullmatch`, no trailing `$`). `archive`, `arch-docs`, and
    `architecture-diagrams` do not qualify; `arch-test`, `arch_test`,
    `arch`, `arch-check`, `architecture-test`, `test-arch`, and
    `check-architecture` all do."""
    normalized = normalize_target_name(name)
    return bool(
        re.fullmatch(_ARCH_SHAPE_PATTERN_DIRECT, normalized)
        or re.fullmatch(_ARCH_SHAPE_PATTERN_PREFIXED, normalized)
    )


def find_arch_test_shaped_target(targets_ordered: list[str]) -> str | None:
    """The FIRST target in Makefile declaration order satisfying D-A1's
    shape rule, or `None`. `targets_ordered` must come from the shared
    `parse_makefile_targets_ordered` -- never a header scan written here,
    and never the set-returning `parse_makefile_targets`, which has no
    order to iterate."""
    for name in targets_ordered:
        if is_arch_test_shaped(name):
            return name
    return None


def _reachable_via_prerequisite_graph(
    makefile_path: str,
    target_name: str,
    depth_bound: int = _CHAIN_DEPTH_BOUND,
    breadth_bound: int = _CHAIN_BREADTH_BOUND,
) -> bool:
    """D-A2 clauses (i) and (ii): breadth-first from `test` over
    `parse_makefile_prerequisites`, carrying a visited set, a depth bound,
    and a breadth bound. A cyclic prerequisite chain terminates (the
    visited set never re-queues a node); a bushy one terminates (the
    breadth bound stops the walk once `breadth_bound` distinct targets
    have been visited). Reaching either bound before `target_name` is
    found returns `False` -- an honest "not proven chained by this
    mechanism" rather than a guess."""
    visited: set[str] = {"test"}
    queue: deque[tuple[str, int]] = deque([("test", 0)])
    while queue:
        current, depth = queue.popleft()
        if depth >= depth_bound:
            continue
        for prereq in parse_makefile_prerequisites(makefile_path, current):
            if prereq == target_name:
                return True
            if prereq in visited:
                continue
            if len(visited) >= breadth_bound:
                return False
            visited.add(prereq)
            queue.append((prereq, depth + 1))
    return False


def is_chained(makefile_path: str, target_name: str) -> bool:
    """D-A2: `target_name` is CHAINED into `test` when any of three real
    mechanisms holds -- a direct prerequisite of `test`, a transitive
    prerequisite reachable through the prerequisite graph (clauses (i)/(ii),
    both covered by the same bounded BFS), or `test`'s own recipe invoking
    the target by name (clause (iii), via the shared token-boundary-aware
    `recipe_mentions_target`)."""
    if _reachable_via_prerequisite_graph(makefile_path, target_name):
        return True
    test_recipe = parse_makefile_recipe(makefile_path, "test")
    return recipe_mentions_target(test_recipe, target_name)


def _missing_target_finding() -> dict:
    """D-A3's existence finding. States the STRUCTURAL fix only -- add an
    arch-test-shaped target and chain it into `test` -- and names no tool
    for any language; plan 12-02 owns the per-stack canonical-tool text and
    ADDS it to this same finding rather than replacing a placeholder."""
    recommendation = (
        "This repo has no arch-test-shaped Makefile target (a target named "
        "e.g. 'arch-test', 'arch', 'arch-check', or 'architecture-test'). "
        "Add one that runs this repo's architecture-fitness checks, and "
        "chain it into 'test' -- as a direct or transitive prerequisite, or "
        "by invoking it from 'test''s recipe -- so it actually runs."
    )
    return {
        "category": "arch-test-target",
        "issue": "arch_test_target_missing",
        "criticality": CRITICALITY_HIGH,
        "summary": recommendation,
        "recommendation": recommendation,
        "needs_research": False,
    }


def _not_chained_finding(target_name: str, test_target_exists: bool) -> dict:
    """D-A3's chaining finding. `CRITICALITY_HIGH` on purpose: an
    arch-test target that exists but is never reached is strictly worse
    than an absent one, because the repo looks covered and is not."""
    if test_target_exists:
        recommendation = (
            f"'{target_name}' exists but 'test' never reaches it -- it is "
            f"not a direct or transitive prerequisite of 'test', and "
            f"'test''s recipe does not invoke it by name. Add it as a "
            f"prerequisite of 'test' (or of an aggregate target 'test' "
            f"already depends on), or invoke it from 'test''s recipe, so "
            f"it actually runs when 'test' runs."
        )
    else:
        recommendation = (
            f"'{target_name}' exists but this repo declares no 'test' "
            f"aggregate target at all, so '{target_name}' has nothing to "
            f"be chained into. Add a 'test' target and make "
            f"'{target_name}' one of its prerequisites (directly, "
            f"transitively, or via a recipe invocation)."
        )
    return {
        "category": "arch-test-chaining",
        "issue": "arch_test_not_chained",
        "criticality": CRITICALITY_HIGH,
        "summary": recommendation,
        "recommendation": recommendation,
        "needs_research": False,
    }


def check_arch_rules(repo_root: str) -> list[dict]:
    """Return a flat list of findings for `repo_root`.

    Resolves the Makefile path once, finds the arch-test-shaped target
    once (D-A1), then branches (D-A4): an absent target returns the single
    existence finding and returns immediately; a present target runs the
    chaining check (and, from plan 12-02 onward, the AST-only check)
    against that same named target -- the target's name is a value passed
    to every downstream check, never re-derived, so D-A1 cannot
    accidentally run twice with different results.

    Degradation, not crashes: an absent `Makefile` means no targets (the
    shared parsers already return empty results for an absent file), so
    the existence finding fires and nothing else does.
    """
    makefile_path = os.path.join(repo_root, "Makefile")
    targets_ordered = parse_makefile_targets_ordered(makefile_path)
    target_name = find_arch_test_shaped_target(targets_ordered)
    if target_name is None:
        return [_missing_target_finding()]

    findings: list[dict] = []
    if not is_chained(makefile_path, target_name):
        test_target_exists = "test" in targets_ordered
        findings.append(_not_chained_finding(target_name, test_target_exists))

    return findings


__all__ = [
    "check_arch_rules",
    "find_arch_test_shaped_target",
    "is_arch_test_shaped",
    "is_chained",
    "normalize_target_name",
]
