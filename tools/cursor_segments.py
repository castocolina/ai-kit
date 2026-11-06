"""Cursor quota segment builders; depends on shared formatting and Cursor payload modules."""
# pyright: strict

import math
import time
from datetime import datetime
from typing import TYPE_CHECKING, NamedTuple, cast

from common_fmt import util_window_gap
from common_types import (
    DIM,
    RESET,
    fmt_bytes,
    util_first_fitting,
    util_gap_color,
    util_gap_sign,
    util_icon,
)
from cursor_payload import core_cursor_data
from cursor_probes import probe_cursor_rss
from cursor_quota import core_extra_alert

if TYPE_CHECKING:
    from common_render import Context, Theme
    from cursor_quota import QuotaResult

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


def _gauge_color_sign(gauge: Gauge, theme: "Theme") -> tuple[str, str]:
    gap = _window_gap(gauge.pct, gauge.window, gauge.now)
    color = theme.c("WHITE") if gap is None else util_gap_color(abs(gap), theme)
    sign = util_gap_sign(gap) if gauge.wide and gap is not None else ""
    return color, sign


def _colored(gauge: Gauge, theme: "Theme") -> str:
    color, sign = _gauge_color_sign(gauge, theme)
    return f"{color}{sign}{gauge.value}{RESET}"


def _days_left(end_ms: int, now: float) -> int:
    # A reset at or before the render moment counts as passed (0d), never negative.
    return max(0, math.ceil((end_ms - now * 1000) / 86_400_000))


def _reset_date(end_ms: int) -> str:
    return datetime.fromtimestamp(end_ms / 1000).strftime("%b %d")


def _fold_end(quota: "QuotaResult") -> int | None:
    # The folded reset follows the window the included gauge measures.
    if quota.included_window is not None:
        return quota.included_window[1]
    return quota.cycle_end_ms


def _cycle_end(quota: "QuotaResult") -> int | None:
    if quota.cycle_end_ms is not None:
        return quota.cycle_end_ms
    if quota.included_window is not None:
        return quota.included_window[1]
    return None


def _extra_window(quota: "QuotaResult") -> tuple[int, int] | None:
    if quota.cycle_start_ms is not None and quota.cycle_end_ms is not None:
        return (quota.cycle_start_ms, quota.cycle_end_ms)
    return None


def _extra_alert(ctx: "Context", quota: "QuotaResult") -> bool:
    # A missing host_knobs falls to core_extra_alert's own defaults (D-12).
    return core_extra_alert((ctx.line_conf.host_knobs or {}).get("cursor"), quota).fires


def _included_variants(
    quota: "QuotaResult", pct: float, api: bool, theme: "Theme"
) -> list[str | None]:
    now = time.time()
    label = "api" if api else "inc"
    value = f"{round(pct)}%"
    wide = Gauge(value, pct, quota.included_window, now, quota.state, True)
    narrow = Gauge(value, pct, quota.included_window, now, quota.state, False)
    mw = _marker(quota.state, True)
    mn = _marker(quota.state, False)
    variants: list[str | None] = []
    fold = _fold_end(quota)
    if not api and fold is not None:
        reset = f"↺ {_reset_date(fold)}, {_days_left(fold, now)}d"
        variants.append(util_icon("⚡", f"{label}: {_colored(wide, theme)} ({reset}){mw}"))
    variants.append(util_icon("⚡", f"{label}: {_colored(wide, theme)}{mw}"))
    variants.append(util_icon("⚡", f"{label}: {_colored(narrow, theme)}{mn}"))
    return variants


def _included(ctx: "Context", avail: int, theme: "Theme", api: bool) -> str | None:
    # No self-enablement check: the packer already filters disabled segment keys
    # (common_render), and double-gating here only defeated the doctor's
    # every-builder dry render of the default-off cursor_api segment.
    quota = _quota(ctx)
    pct = quota.api_pct if api else quota.included_pct
    if quota.state not in ("ok", "stale") or pct is None:
        return None
    variants = _included_variants(quota, pct, api, theme)
    return util_first_fitting(variants, avail)


def seg_cursor_included(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    return _included(ctx, avail, theme, False)


def seg_cursor_api(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    return _included(ctx, avail, theme, True)


def _fixed_extra(
    quota: "QuotaResult", ceiling: float, alert: bool, theme: "Theme", avail: int
) -> str | None:
    used = cast(float, quota.od_used_usd)
    now = time.time()
    variants: list[str | None] = []
    for wide_form in (True, False):
        gauge = Gauge(
            f"${used:.2f}/${ceiling:.2f}",
            used / ceiling * 100,
            _extra_window(quota),
            now,
            quota.state,
            wide_form,
        )
        color, sign = _gauge_color_sign(gauge, theme)
        # D-03: only the used amount turns bold red; the sign and the ceiling keep the gauge colour.
        if alert:
            amount = f"{color}{sign}{RESET}{theme.c('RED+bold')}${used:.2f}{RESET}"
            value = f"{amount}{color}/${ceiling:.2f}{RESET}"
        else:
            value = f"{color}{sign}${used:.2f}/${ceiling:.2f}{RESET}"
        variants.append(util_icon("🪙", f"extra: {value}{_marker(quota.state, wide_form)}"))
    return util_first_fitting(variants, avail)


def seg_cursor_extra(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    quota = _quota(ctx)
    if quota.state not in ("ok", "stale") or quota.od_kind == "unavailable":
        return None
    if quota.od_kind == "disabled":
        value = f"{DIM}extra off{RESET}{_marker(quota.state, True)}"
        return util_first_fitting([util_icon("🪙", value)], avail)
    if quota.od_used_usd is None:
        return None
    used = quota.od_used_usd
    alert = _extra_alert(ctx, quota)
    if quota.od_kind == "unlimited":
        color = theme.c("RED+bold") if alert else theme.c("WHITE")
        value = f"{color}${used:.2f}{RESET}{_marker(quota.state, True)}"
        return util_first_fitting([util_icon("🪙", f"extra: {value}")], avail)
    if quota.od_kind != "fixed" or not quota.od_ceiling_usd:
        return None
    return _fixed_extra(quota, quota.od_ceiling_usd, alert, theme, avail)


def seg_cursor_reset(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    quota = _quota(ctx)
    end = _cycle_end(quota)
    if quota.state not in ("ok", "stale") or end is None:
        return None
    now = time.time()
    date = _reset_date(end)
    wide = util_icon("↺", f"{date} ({_days_left(end, now)}d){_marker(quota.state, True)}")
    narrow = util_icon("↺", f"{date}{_marker(quota.state, False)}")
    return util_first_fitting([wide, narrow], avail)


def seg_alt_process_memory(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    n = probe_cursor_rss(ctx)
    if n is None:
        return None
    return util_first_fitting([util_icon("🧮", fmt_bytes(n))], avail)
