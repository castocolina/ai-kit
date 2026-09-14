"""Remediation payload builder -- delegates to the shared
`ai_kit_rules_common.remediation` module. Re-exported here under this
skill's own package namespace so `from ai_kit_project_rules_docker import
remediation` works unchanged, matching the sibling skills' own
`remediation.py`.
"""

from __future__ import annotations

from ai_kit_rules_common.remediation import build_remediation

__all__ = ["build_remediation"]
