"""Builds the tool-preference prose appended to a dispatch prompt -- never includes anything
not deterministically confirmed for the target CLI (design spec §9: 'never pass a subagent
prose it would have to infer/guess about when the answer should be certain')."""

import json
import os


def resolve_shared_tooling_reference_path() -> str | None:
    """Always resolves relative to this installed package -- ai-kit-spec-review/references/
    tooling-guidance.md ships as this module's own sibling in every install shape (plugin,
    ~/.claude/skills, or a dev checkout), so no 3-candidate search is needed the way SKILL.md
    prose requires elsewhere in this repo (that pattern exists only because prose has no
    __file__ equivalent). Returns None if the file doesn't actually exist on disk (a corrupted/
    partial install) -- same never-guess-if-uncertain convention resolve_agents_tooling_path
    already follows; build_tooling_guidance's `if shared_reference_path:` check already omits
    the line cleanly for a None value, no separate handling needed there."""
    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(package_dir, "references", "tooling-guidance.md")
    return candidate if os.path.isfile(candidate) else None


def build_tooling_guidance(cli: str, tool_availability: dict, agents_tooling_path,
                            codegraph_registered: bool, shared_reference_path=None) -> str:
    lines = []
    if shared_reference_path:
        # Emitted as a NAMED variable, not a bare path: ai-kit-spec-review-checklist's own
        # "Tool preference during review" rule keys off the literal name SHARED_TOOLING_PATH,
        # and a rule gated on a name the dispatched prompt never uses can never fire.
        lines.append(f"SHARED_TOOLING_PATH = {shared_reference_path}")
        lines.append(
            f"Read {shared_reference_path} for this repo's confirmed tool preferences."
        )
    if agents_tooling_path:
        lines.append(f"AGENTS_TOOLING_PATH = {agents_tooling_path}")
        lines.append(f"Read {agents_tooling_path} for confirmed tool preferences on this machine.")
    if tool_availability:
        # Same reason as SHARED_TOOLING_PATH above: the checklist's legacy-tool-usage rule is
        # explicitly gated on "the modern equivalent's presence is confirmed in
        # tool_availability" -- so the dispatched reviewer has to actually RECEIVE that map,
        # under that name, or the rule is gated on data it was never shown. Compact JSON with
        # sorted keys: small, flat, and stable across runs (no prompt churn from dict order).
        lines.append(
            "TOOL_AVAILABILITY = "
            + json.dumps(tool_availability, sort_keys=True, separators=(",", ":"))
        )
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
