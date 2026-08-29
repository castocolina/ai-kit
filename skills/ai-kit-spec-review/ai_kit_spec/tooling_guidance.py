"""Builds the tool-preference prose appended to a dispatch prompt -- never includes anything
not deterministically confirmed for the target CLI (design spec §9: 'never pass a subagent
prose it would have to infer/guess about when the answer should be certain')."""


def build_tooling_guidance(cli: str, tool_availability: dict, agents_tooling_path,
                            codegraph_registered: bool) -> str:
    lines = []
    if agents_tooling_path:
        lines.append(f"Read {agents_tooling_path} for confirmed tool preferences on this machine.")
    # Hard-omit grok regardless of what the caller passes for codegraph_registered -- confirmed
    # unsupported (design spec, Global Constraints above). Defense in depth: check_codegraph_
    # mcp_healthy("grok") already always returns False, but this function must never emit
    # codegraph guidance for grok even if a caller passes an inconsistent/stale True by mistake.
    if cli != "grok" and codegraph_registered and tool_availability.get("codegraph"):
        lines.append(
            "codegraph_explore (MCP) is available and confirmed registered for this CLI -- "
            "prefer it over broad file reads for architecture/cross-reference questions, "
            "unless another tool is genuinely simpler for a specific lookup."
        )
    return "\n".join(lines)
