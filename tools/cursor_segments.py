"""Cursor quota segment builders; depends on shared formatting and Cursor payload modules."""
# pyright: strict

import time
from datetime import datetime
from typing import TYPE_CHECKING, NamedTuple

from common_fmt import util_window_gap
from common_types import DIM, RESET, util_first_fitting, util_gap_color, util_gap_sign
from cursor_payload import core_cursor_data

if TYPE_CHECKING:
    from common_render import Context, Theme

# ═══ 7. seg_ — segment builders seg_x(ctx, avail, theme); auto-discovered registry


def _quota(ctx: "Context"):
    return core_cursor_data(ctx).quota


def _marker(state: str, wide: bool) -> str:
    suffix = (" ≈ stale" if wide else " ≈*") if state == "stale" else " ≈"
    return f"{DIM}{suffix}{RESET}"


def _window_gap(pct: float, window: tuple[int, int] | None, now: float) -> float | None:
    if window is None:
        return None
    return util_window_gap(pct, window[0] / 1000, window[1] / 1000, now)


class Gauge(NamedTuple):
    value: str
    pct: float
    window: tuple[int, int] | None
    now: float
    state: str
    wide: bool


def _colored(gauge: Gauge, theme: "Theme") -> str:
    gap = _window_gap(gauge.pct, gauge.window, gauge.now)
    color = theme.c("WHITE") if gap is None else util_gap_color(abs(gap), theme)
    sign = util_gap_sign(gap) if gauge.wide and gap is not None else ""
    return f"{color}{sign}{gauge.value}{RESET}{_marker(gauge.state, gauge.wide)}"


def _included(ctx: "Context", avail: int, theme: "Theme", api: bool) -> str | None:
    key = "cursor_api" if api else "cursor_included"
    if not ctx.line_conf.segments.get(key, False):
        return None
    quota = _quota(ctx)
    pct = quota.api_pct if api else quota.included_pct
    if quota.state not in ("ok", "stale") or pct is None:
        return None
    now = time.time()
    text = "api" if api else "inc"
    value = f"{round(pct)}%"
    wide_value = _colored(
        Gauge(value, pct, quota.included_window, now, quota.state, True), theme
    )
    narrow_value = _colored(
        Gauge(value, pct, quota.included_window, now, quota.state, False), theme
    )
    wide = f"{text} {wide_value}"
    narrow = f"{text} {narrow_value}"
    return util_first_fitting([wide, narrow], avail)


def seg_cursor_included(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    return _included(ctx, avail, theme, False)


def seg_cursor_api(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    return _included(ctx, avail, theme, True)


def seg_cursor_extra(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    quota = _quota(ctx)
    if quota.state not in ("ok", "stale") or quota.od_kind == "unavailable":
        return None
    if quota.od_kind == "disabled":
        value = f"{DIM}extra off{RESET}{_marker(quota.state, True)}"
        return util_first_fitting([value], avail)
    if quota.od_used_usd is None:
        return None
    if quota.od_kind == "unlimited":
        text = f"extra ${quota.od_used_usd:.2f}"
        value = f"{theme.c('WHITE')}{text}{RESET}{_marker(quota.state, True)}"
        return util_first_fitting([value], avail)
    if quota.od_kind != "fixed" or not quota.od_ceiling_usd:
        return None
    pct = quota.od_used_usd / quota.od_ceiling_usd * 100
    window = ((quota.cycle_start_ms, quota.cycle_end_ms)
              if quota.cycle_start_ms is not None and quota.cycle_end_ms is not None else None)
    amount = f"${quota.od_used_usd:.2f}/${quota.od_ceiling_usd:.2f}"
    now = time.time()
    wide_value = _colored(Gauge(amount, pct, window, now, quota.state, True), theme)
    narrow_value = _colored(Gauge(amount, pct, window, now, quota.state, False), theme)
    wide = f"extra {wide_value}"
    narrow = f"extra {narrow_value}"
    return util_first_fitting([wide, narrow], avail)


def seg_cursor_reset(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    quota = _quota(ctx)
    if quota.state not in ("ok", "stale") or quota.cycle_end_ms is None:
        return None
    reset = quota.cycle_end_ms / 1000
    wide = f"↺ {datetime.fromtimestamp(reset).strftime('%b %d %H:%M')}{_marker(quota.state, True)}"
    narrow = f"↺ {datetime.fromtimestamp(reset).strftime('%b %d')}{_marker(quota.state, False)}"
    return util_first_fitting([wide, narrow], avail)
