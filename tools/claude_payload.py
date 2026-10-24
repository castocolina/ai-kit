"""The Claude payload context builder for the Phase 23 D-02 status-line split."""
# pyright: strict

import os
import time
from typing import TYPE_CHECKING, Any, cast

from common_render import Context

if TYPE_CHECKING:
    from common_render import Theme
    from common_types import Config

# ═══ 2. cfg_ — config loading & resolution (the only block that reads config env)


def cfg_resolve_effort(raw: dict[str, Any]) -> str:
    """The *resolved* effort level (low..max) as a normalized lowercase string, or "".

    This is the live per-turn level the API reported, read from raw["effort"]["level"]
    (JSON + settings only — FR-1.9 dropped the CLAUDE_EFFORT env source). It is never
    "auto" — auto is a *setting*, detected separately from disk by
    probe_effort_setting_is_auto. A stray "auto" in the resolved field (transition states)
    is normalized away so it can't reach the level table."""
    effort_block: dict[str, Any] = cast(dict[str, Any], raw.get("effort") or {})
    level: str = str(effort_block.get("level") or "").strip().lower()
    return "" if level == "auto" else level

# ═══ 6. core_ — render machinery: Context, Theme, registry, packer, render ════


def core_build_context(raw: dict[str, Any], config: "Config", theme: "Theme",  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
                  cols: int, lines: int, dim_assumed: bool, t_start: int | None,
                  effort: str, home: str, claude_dir: str) -> "Context":
    """Assemble the per-render Context from the parsed status JSON and the
    already-resolved per-render inputs. Segment-agnostic and env-free: every
    env read happened in the CONFIG block; the SHELL hands the resolved values
    here. Expensive probes are deferred via probe_cache memoization."""
    model: dict[str, Any] = cast(dict[str, Any], raw.get("model") or {})
    cost: dict[str, Any] = cast(dict[str, Any], raw.get("cost") or {})
    ctx_win: dict[str, Any] = cast(dict[str, Any], raw.get("context_window") or {})
    workspace: dict[str, Any] = cast(dict[str, Any], raw.get("workspace") or {})
    work_dir: str = os.path.abspath(str(workspace.get("current_dir") or "."))
    transcript: str = str(raw.get("transcript_path") or "")
    # session_id locates the materialized task/todo state probe_current_todo prefers
    # over replaying the transcript; it also equals the transcript file basename.
    session: str = str(raw.get("session_id") or (
        os.path.splitext(os.path.basename(transcript))[0] if transcript else ""))
    return Context(
        raw=raw, line_conf=config, theme=theme,
        cols=cols, lines=lines, dim_assumed=dim_assumed, t_start=t_start,
        model_name=str(model.get("display_name") or ""),
        model_id=str(model.get("id") or "unknown"),
        effort=effort, work_dir=work_dir, home=home,
        clock=time.strftime("%H:%M"),
        # `or 0` (not get's default) so a PRESENT-but-null field — what a fresh
        # /clear session sends before any tokens/cost accrue — coalesces to 0
        # instead of raising on int()/math and blanking the whole bar.
        added=int(cost.get("total_lines_added") or 0),
        removed=int(cost.get("total_lines_removed") or 0),
        cost=float(cost.get("total_cost_usd") or 0),
        total_ms=int(cost.get("total_duration_ms") or 0),
        api_ms=int(cost.get("total_api_duration_ms") or 0),
        context_pct=int(ctx_win.get("used_percentage") or 0),
        context_max=int(ctx_win.get("context_window_size") or 0),
        rate_limits=cast(dict[str, Any], raw.get("rate_limits") or {}),
        transcript=transcript, session=session, claude_dir=claude_dir,
    )
