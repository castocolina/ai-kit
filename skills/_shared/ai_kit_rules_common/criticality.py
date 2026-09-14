"""Shared criticality band vocabulary for the ai-kit rules-checker skill
family.

Phase 15's orchestrator orders findings across six domains using this
vocabulary, so a private copy per skill would let two domains drift apart
silently -- this is why the bands live here rather than inside any one
checker skill's own module.

`CRITICALITY_CRITICAL`/`CRITICALITY_HIGH`/`CRITICALITY_MEDIUM` are chosen to
equal `ai-kit-project-rules-agents`'s existing `rules.py` literals verbatim.
`rules.py` is deliberately NOT repointed at this module in this phase --
Phase 9 just closed that file, and repointing it is a separate, reversible
follow-up rather than this phase's business. A non-vacuous drift guard
(`tests/test_ai_kit_rules_common.py`) pins the two sources against each
other so they cannot silently disagree.

`CRITICALITY_ADVISORY` is the non-blocking fourth band plan 10-02's ordering
heuristic needs; the sibling skill's `rules.py` has no equivalent value.
"""

from __future__ import annotations

CRITICALITY_CRITICAL = 1
CRITICALITY_HIGH = 2
CRITICALITY_MEDIUM = 3
CRITICALITY_ADVISORY = 4

__all__ = [
    "CRITICALITY_ADVISORY",
    "CRITICALITY_CRITICAL",
    "CRITICALITY_HIGH",
    "CRITICALITY_MEDIUM",
]
