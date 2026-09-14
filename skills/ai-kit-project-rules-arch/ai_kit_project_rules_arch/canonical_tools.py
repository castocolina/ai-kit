"""Hardcoded per-stack canonical architecture-fitness-tool baseline
(ROADMAP Phase 12 Success Criterion 4; this plan's D-A10).

This is HARDCODED baseline knowledge, with NO staleness mechanism, NO
research dispatch, and NO cache (12-01 D-A6) -- unlike the Phase 10 and
Phase 11 siblings' per-stack tooling, which genuinely goes stale, an
architecture-fitness tool choice per ecosystem is a stable, well-settled
fact rather than a fast-moving lint roster. Confirmed by research
(`docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`,
the `ai-kit-project-rules-arch` component section) as the most-recommended
pattern in each ecosystem at the time this skill was designed.

The Rust and Go rows are a RECORDED GAP, not an unfinished row: no equally
canonical, dedicated architecture-fitness tool surfaced in that research
for either ecosystem, so this skill declines to assert a false canonical
choice for them rather than inventing one. Asserting a confident-sounding
but ungrounded tool name for an ecosystem that has none would violate
PROJECT.md's core value directly -- nothing is presented with more
certainty than its sourcing.
"""

from __future__ import annotations

# ONE definition site, keyed on exactly the five stack names
# `ai_kit_rules_common.stack_detect.detect_stacks` can return. A stack name
# with no row here (impossible today, since the marker table is fixed) must
# still produce an honest "no baseline recorded" clause via the accessor
# below, never a silent omission.
_CANONICAL_TOOLS: dict[str, str] = {
    "python": (
        "import-linter -- static, AST-only via Grimp, safe against "
        "untrusted target-repo code, and config-DSL 'contracts' that "
        "express layering rules declaratively."
    ),
    "node": (
        "dependency-cruiser -- the broadest static rule surface "
        "(circular dependencies, path-based layering, orphan detection) "
        "with no build or type-system dependency."
    ),
    "java": (
        "ArchUnit -- runs as ordinary JUnit tests in the normal test "
        "suite rather than as a side lint pass, the most consistently "
        "recommended pattern across sources surveyed, since a failing "
        "named test is a stronger CI signal than a side lint-pass "
        "failure."
    ),
    "rust": (
        "known gap -- no equally canonical, dedicated "
        "architecture-fitness tool surfaced in research for Rust, and "
        "this skill declines to assert a false canonical choice for it."
    ),
    "go": (
        "known gap -- no equally canonical, dedicated "
        "architecture-fitness tool surfaced in research for Go, and this "
        "skill declines to assert a false canonical choice for it."
    ),
}

_NO_STACK_DETECTED_TEXT = (
    "No language-stack marker file was detected in this repo, so this "
    "skill has no per-stack canonical architecture-fitness-tool "
    "recommendation to add."
)


def canonical_tool_advice(stacks: set[str]) -> str:
    """Deterministic per-stack advice text for `stacks` (the exact set
    `detect_stacks(repo_root)` returns).

    Iterates `stacks` in SORTED order so a multi-stack repo produces the
    SAME string on every run, never a set-iteration-order-dependent one.
    An empty `stacks` returns an explicit no-stack-detected statement --
    never a silent omission, and never a default to Python.
    """
    if not stacks:
        return _NO_STACK_DETECTED_TEXT
    clauses = []
    for stack in sorted(stacks):
        text = _CANONICAL_TOOLS.get(
            stack,
            f"no canonical-tool baseline is recorded for stack '{stack}' in this skill.",
        )
        clauses.append(f"For {stack}: {text}")
    return " ".join(clauses)


__all__ = ["canonical_tool_advice"]
