"""This skill's namespace binding of the shared generic cache engine
(`ai_kit_rules_common.stack_cache`), under the `project-rules-precommit`
cache namespace (the skill name minus the `ai-kit-` prefix, mirroring the
sibling `ai-kit-project-rules-makefile` skill's own convention).

Known open discrepancy, deliberately unfixed here (this skill inherits the
shipped value verbatim, changing neither side): `.planning/intel/
constraints.md` and the design spec both state the cache staleness
threshold as 180 days, while the shared `ai_kit_rules_common.stack_cache`
module ships `STALE_AFTER_DAYS = 30`. Plan 10-01 observed this first and
deliberately left it; this is the second phase to observe it unfixed.
"""

from __future__ import annotations

from ai_kit_rules_common import stack_cache as _shared

STALE_AFTER_DAYS = _shared.STALE_AFTER_DAYS

_NAMESPACE = "project-rules-precommit"
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
    "CACHE_ROOT",
    "STALE_AFTER_DAYS",
    "cache_path",
    "get_stack_tooling",
    "read_stack_cache",
    "write_stack_cache",
]
