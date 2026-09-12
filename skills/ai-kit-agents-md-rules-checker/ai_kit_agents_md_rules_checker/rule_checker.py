"""Workflow-rule prose checker with live tool-presence conditioning.

D-07: a rule whose `condition` is not met in this environment is skipped/
reframed as `"not_applicable"`, never flagged as a generic gap.

The actual classification engine lives in `ai_kit_rules_common.
classification` (shared across the rules-checker skill family). This
module's only job is binding that generic engine to THIS skill's own
17-rule `RULES` tuple.
"""

from __future__ import annotations

from ai_kit_rules_common.classification import check_rules, evaluate_condition

from .rules import RULES


def check_workflow_rules(
    agents_md_text: str, tool_presence: dict, include_present: bool = False
) -> list[dict]:
    return check_rules(agents_md_text, tool_presence, RULES, include_present=include_present)


__all__ = [
    "check_workflow_rules",
    "evaluate_condition",
]
