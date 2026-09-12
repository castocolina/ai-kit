"""Remediation payload builder -- delegates to the shared
`ai_kit_rules_common.remediation` module. Re-exported here under this
skill's own package namespace so existing imports
(`from ai_kit_agents_md_rules_checker import remediation`) keep working
unchanged.
"""

from __future__ import annotations

from ai_kit_rules_common.remediation import build_remediation

__all__ = ["build_remediation"]
