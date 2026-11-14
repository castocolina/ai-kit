"""Builds the tool-preference prose appended to a dispatch prompt -- never includes anything
not deterministically confirmed for the target CLI (design spec §9: 'never pass a subagent
prose it would have to infer/guess about when the answer should be certain')."""

import json
import os

from ai_kit_spec.detection import CBM_NAME, CBM_REGISTRATION_KEYS, runtime_id

# codebase-memory-mcp tools in documented priority order: a lane reaches for the first one that
# answers its question.
CBM_TOOLS = (
    "search_graph",
    "trace_path",
    "get_code_snippet",
    "query_graph",
    "get_architecture",
    "check_index_coverage",
)


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


def resolve_cross_ai_template_path() -> str | None:
    """Package-relative path to references/cross-ai.mjs (template v7), or None if missing."""
    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(package_dir, "references", "cross-ai.mjs")
    return candidate if os.path.isfile(candidate) else None


def _code_index_line(mcp: bool, runtime: str) -> str:
    """One guidance line for codebase-memory-mcp. The MCP list only when the host config
    registers the server; otherwise the CLI form. Never both for the same lane."""
    tools = ", ".join(CBM_TOOLS)
    if mcp:
        # A config entry is evidence of configuration, not of tools usable in this session.
        if CBM_REGISTRATION_KEYS[runtime] is None:
            evidence = "inferred from its extension file"
        else:
            evidence = "read from its config"
        return (
            "codebase-memory-mcp's tools are configured for this CLI "
            f"({evidence}, not tested in this session): before broad file reads or grep, use "
            f"{tools}; when list_projects shows no project for this checkout, run "
            "index_repository on it first."
        )
    return (
        "codebase-memory-mcp is installed (no MCP registration confirmed for this CLI): run "
        "`codebase-memory-mcp cli <tool> --flag value` with the tools "
        f"{tools} (`codebase-memory-mcp cli <tool> --help` lists the flags); when "
        "`codebase-memory-mcp cli list_projects` shows no project for this checkout, run "
        "`codebase-memory-mcp cli index_repository --repo-path .` first."
    )


def build_tooling_guidance(cli: str, tool_availability: dict, agents_tooling_path,
                            code_index_registered: bool, shared_reference_path=None) -> str:
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
    # The caller may forward a legacy id (cursor-agent); normalize it the way the registration
    # reader does, so an alias gets the same guidance as its table id. A runtime without a
    # registration reader (grok) never gets the MCP list, even with an inconsistent True.
    if tool_availability.get(CBM_NAME):
        name = runtime_id(cli)
        mcp = bool(code_index_registered) and name in CBM_REGISTRATION_KEYS
        lines.append(_code_index_line(mcp, name))
    return "\n".join(lines)
