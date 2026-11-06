"""Cursor host defaults and HOST assembly; imports Cursor and host-neutral modules only."""
# pyright: strict

from typing import Any

import common_segments
import cursor_segments
from common_render import Host, core_discover_builders
from common_types import RAMP_DEFAULTS, ConfigSpec, Line
from cursor_payload import core_cursor_context

# ═══ 1. DEFAULTS — Cursor segment registry and layout ════════════════════════

SEGMENTS = {
    "path": True,
    "git_branch": True,
    "git_dirty": True,
    "alt_git_worktree": False,
    "model": True,
    "context": True,
    "cursor_included": True,
    "cursor_api": False,
    "cursor_extra": True,
    "cursor_reset": True,
    "render_time": False,
    "slowest": False,
    "alt_time_clock": False,
    "alt_term_dimensions": False,
}
LAYOUT = [
    Line(0, ["path", "git_branch", "alt_git_worktree", "git_dirty"]),
    Line(0, ["model", "context", "cursor_included", "cursor_api", "cursor_extra", "cursor_reset"]),
    Line(0, ["render_time", "slowest", "alt_time_clock", "alt_term_dimensions"]),
]
PINNED = {"path", "context"}
# `extra_alert_usd` None: no override, the alert uses the Cursor spend limit (D-12).
HOST_SCALARS: dict[str, dict[str, Any]] = {"cursor": {"extra_alert": True, "extra_alert_usd": None}}

# ═══ 6. core_ — host spec and renderer contract ═════════════════════════════

SPEC = ConfigSpec(
    "AI_KIT_CURSOR_",
    "cursor-statusline.toml",
    SEGMENTS,
    LAYOUT,
    RAMP_DEFAULTS,
    "segments-cursor",
    "segments-cursor",
    "AI_KIT_CURSOR_PROVIDER_",
    host_scalars=HOST_SCALARS,
)
BUILDERS = core_discover_builders(common_segments, cursor_segments)
HOST = Host(
    "cursor", SPEC, core_cursor_context, BUILDERS, frozenset(PINNED), 0, {},
    "--doctor --host cursor",
)
