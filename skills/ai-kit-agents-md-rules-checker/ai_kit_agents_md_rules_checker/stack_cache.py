"""This skill's Makefile-tooling schema, bound to the shared generic cache
engine in `ai_kit_rules_common.stack_cache` under this skill's own cache
namespace (`agents-md-rules-checker`).

NOTE: `REQUIRED_STATIC_TARGETS`/`RESEARCH_CATEGORIES`/`ALL_TOOLING_KEYS`
below are Makefile-tooling-specific, not generic -- they stay HERE (not in
the shared package) because `makefile_checker.py` still lives in this
skill. A follow-up plan relocates both this schema and `makefile_checker.py`
together into a dedicated `ai-kit-makefile-rules-checker` skill; this
module's job until then is unchanged from before this refactor.
"""

from __future__ import annotations

from ai_kit_rules_common import stack_cache as _shared

STALE_AFTER_DAYS = _shared.STALE_AFTER_DAYS

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

_NAMESPACE = "agents-md-rules-checker"
CACHE_ROOT = _shared.default_cache_root(_NAMESPACE)


def cache_path(stack: str, cache_root: str | None = None) -> str:
    return _shared.cache_path(stack, cache_root or CACHE_ROOT)


def read_stack_cache(stack: str, cache_root: str | None = None) -> dict:
    return _shared.read_stack_cache(stack, cache_root or CACHE_ROOT)


def write_stack_cache(stack: str, data: dict, cache_root: str | None = None) -> None:
    _shared.write_stack_cache(stack, data, cache_root or CACHE_ROOT)


def get_stack_tooling(
    stack: str, cache_root: str | None = None
) -> tuple[dict | None, bool]:
    return _shared.get_stack_tooling(stack, cache_root or CACHE_ROOT)


__all__ = [
    "ALL_TOOLING_KEYS",
    "CACHE_ROOT",
    "REQUIRED_STATIC_TARGETS",
    "RESEARCH_CATEGORIES",
    "STALE_AFTER_DAYS",
    "cache_path",
    "get_stack_tooling",
    "read_stack_cache",
    "write_stack_cache",
]
