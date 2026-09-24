"""Makefile/pre-commit tooling-payload validator, relocated here by Phase 9
per `.planning/milestones/v1.2-phases/09-agents-md-checker-prune-ai-kit-project-rules-agents/
09-CONTEXT.md` D-04.

Wired by Phase 10: this skill's `stack_cache.py` imports `ALL_TOOLING_KEYS`/
`REQUIRED_STATIC_TARGETS`/`RESEARCH_CATEGORIES` from here (the single
definition site for the tooling key schema -- see `stack_cache.py`'s own
docstring and threat row T-10-02), and this skill's `cli.py` calls
`validate_tooling_payload` directly from its `cache-update` subcommand.

Pre-move test coverage for this validator (payload shape, unknown-key
rejection, missing/empty `(source: ...)` citation rejection) is recoverable
verbatim from Phase 9's prune commit's PARENT (the rename commit), under
`tests/test_ai_kit_project_rules_agents.py`, by test-class name:
`TestCacheUpdateValidation`.
"""

from __future__ import annotations

import re

# Copied verbatim from the pruned `ai-kit-project-rules-agents` skill's
# `stack_cache.py` (Phase 9's prune commit) so Phase 10 inherits the
# cache-payload contract instead of re-deriving it from the design spec.
REQUIRED_STATIC_TARGETS = (
    "setup-env",
    "validate",
    "test",
    "test-unit",
    "test-integration",
    "e2e-test",
    "arch-test",
)

# Tool-category recommendations the research prompt asks for that do NOT
# map 1:1 to one of the 7 static target names above. `validate-order` and
# `precommit-vs-prepush-split` are deliberately NOT members: both are
# process/structural facts readable directly from the target repo's own
# files (see makefile_checker.check_validate_order and
# check_precommit_prepush_split), not a tool pick that benefits from
# research -- a category with no research-fillable content would be a
# perpetual, unsatisfiable false positive.
RESEARCH_CATEGORIES = (
    "formatter",
    "security-scanner",
    "code-smell-detector",
    "duplicate-code-detector",
    "dead-code-detector",
)

ALL_TOOLING_KEYS = REQUIRED_STATIC_TARGETS + RESEARCH_CATEGORIES

# At least one character that is neither whitespace nor a closing paren must
# immediately follow "(source:" (and any whitespace after it) -- rejects a
# bare substring match against "(source:)" or "(source: )" (Cycle 4 MEDIUM).
_SOURCE_CITATION_RE = re.compile(r"\(source:\s*[^\s)]")


def validate_tooling_payload(data) -> str | None:
    """Return a one-line error string, or `None` if `data` is valid.

    `data` must be a JSON object; every key must be a member of
    `ALL_TOOLING_KEYS`; every value must be a non-empty `str` carrying a
    non-empty `(source: ...)` citation. Never merely checking for the bare
    substring `"(source:"` -- `"...(source:)"` and `"...(source: )"` are
    both rejected too (Cycle 3/Cycle 4 fixes).
    """
    if not isinstance(data, dict):
        return "tooling JSON must be an object, not a list/scalar"
    for key, value in data.items():
        if key not in ALL_TOOLING_KEYS:
            return f"unknown tooling key: {key!r}"
        if not isinstance(value, str) or not value:
            return f"value for {key!r} must be a non-empty string"
        if _SOURCE_CITATION_RE.search(value) is None:
            return (
                f"value for {key!r} is missing a non-empty (source: ...) "
                "citation"
            )
    return None


__all__ = [
    "ALL_TOOLING_KEYS",
    "REQUIRED_STATIC_TARGETS",
    "RESEARCH_CATEGORIES",
    "validate_tooling_payload",
]
