"""Live tool-presence detection -- delegates to the shared
`ai_kit_rules_common.tool_presence` module (identical logic, shared across
the rules-checker skill family). Re-exported here under this skill's own
package namespace so existing imports (`from ai_kit_agents_md_rules_checker
import tool_presence`) keep working unchanged.
"""

from __future__ import annotations

from ai_kit_rules_common.tool_presence import MODERN_CLI_TOOLS, check_tool_presence

__all__ = ["MODERN_CLI_TOOLS", "check_tool_presence"]
