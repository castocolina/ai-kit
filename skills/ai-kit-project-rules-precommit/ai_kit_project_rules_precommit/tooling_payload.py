"""This skill's cache-payload schema binding.

`ALL_TOOLING_KEYS` IS the shared taxonomy vocabulary from
`skills/_shared/ai_kit_rules_common/tool_catalog.py`, imported and aliased,
never re-declared or re-derived: the six category names are what a research
pass fills for a stack outside the five baseline stacks (11-02 adds those
baseline tables). One definition site -- the same discipline Phase 10's
`SCHEMA-SINGLE-SOURCE-OK` criterion enforces for its own schema, and the
same reason: the validator that gates every cache write and the classifier
that reads the cache must agree about what a valid key is.
"""

from __future__ import annotations

from ai_kit_rules_common.stack_cache import validate_stack_payload
from ai_kit_rules_common.tool_catalog import TAXONOMY_CATEGORIES

ALL_TOOLING_KEYS = TAXONOMY_CATEGORIES


def validate_tooling_payload(data) -> str | None:
    """Delegate to the shared generic validator with this skill's own six
    taxonomy keys. Return a one-line error string, or `None` if valid."""
    return validate_stack_payload(data, ALL_TOOLING_KEYS)


__all__ = ["ALL_TOOLING_KEYS", "validate_tooling_payload"]
