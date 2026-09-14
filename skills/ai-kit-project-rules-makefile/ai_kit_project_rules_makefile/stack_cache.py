"""This skill's namespace binding of the shared generic cache engine
(`ai_kit_rules_common.stack_cache`), under the `project-rules-makefile`
cache namespace.

The tooling key schema (`REQUIRED_STATIC_TARGETS`/`RESEARCH_CATEGORIES`/
`ALL_TOOLING_KEYS`) is imported from `.tooling_payload` rather than declared
here -- that module is the single source of truth Phase 9 relocated it to,
and both the `SCHEMA-SINGLE-SOURCE-OK` acceptance criterion and threat row
T-10-02 assume exactly one definition site for those three names.
"""

from __future__ import annotations

from ai_kit_rules_common import stack_cache as _shared

from .tooling_payload import ALL_TOOLING_KEYS, REQUIRED_STATIC_TARGETS, RESEARCH_CATEGORIES

STALE_AFTER_DAYS = _shared.STALE_AFTER_DAYS

_NAMESPACE = "project-rules-makefile"
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
