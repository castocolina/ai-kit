"""Claude rate-limit helpers for the Phase 23 D-02 status-line split."""
# pyright: strict

import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from common_types import RESET, util_gap_color, util_gap_sign, util_icon

if TYPE_CHECKING:
    from common_render import Theme

# ═══ 4. fmt_ — pure formatters (number / tokens / duration / bytes / ago) ═════


_NUM_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "fifteen": 15,
    "twenty": 20, "thirty": 30, "sixty": 60,
}


_UNIT_ABBR = {
    "hour": "h", "hours": "h", "day": "d", "days": "d",
    "week": "w", "weeks": "w", "month": "mo", "months": "mo",
}


def fmt_rate_key_label(key: str) -> str:
    """five_hour -> '5h', thirty_day -> '30d'. Unknown words pass through."""
    num, _, unit = key.partition("_")
    num = _NUM_WORDS.get(num, num)
    unit = _UNIT_ABBR.get(unit, unit)
    return f"{num}{unit}"

# ═══ 5. util_ — pure non-format helpers (color / width / truncate / fit / parse)


_UNIT_SECONDS = {
    "hour": 3600, "hours": 3600, "day": 86400, "days": 86400,
    "week": 604800, "weeks": 604800, "month": 2_592_000, "months": 2_592_000,
}


def util_rate_window_seconds(key: str) -> int | None:
    """five_hour -> 5*3600, seven_day -> 7*86400. None when either the
    number word or the unit word is unrecognized -- mirrors
    fmt_rate_key_label's own "unknown words pass through" leniency rather
    than raising."""
    num, _, unit = key.partition("_")
    n = _NUM_WORDS.get(num)
    secs = _UNIT_SECONDS.get(unit)
    if n is None or secs is None:
        return None
    return n * secs


def util_rate_gap(pct: float, key: str, reset: int | None, now: float) -> float | None:
    """Signed percentage-point gap between used_percentage and the window's
    elapsed percentage (positive: usage ahead of elapsed time; negative:
    behind). None when the window can't be reliably derived (unparseable
    key, missing reset, a resets_at already in the past [remaining_pct < 0],
    or a resets_at implying more time remaining than the key's parsed
    window allows [remaining_pct > 100] -- clock skew or window/key
    mismatch). Replaces the pace ratio (pct / elapsed_fraction): the gap
    is computed from the remaining percentage directly -- no division by
    an elapsed fraction -- so elapsed == 0 (window just started) is a
    normal computable case, not a fallback."""
    window_seconds = util_rate_window_seconds(key)
    if window_seconds is None or reset is None:
        return None
    remaining_pct = (reset - now) * 100.0 / window_seconds
    if remaining_pct < 0.0 or remaining_pct > 100.0:
        return None
    return pct - (100.0 - remaining_pct)


def _rate_bucket_hourly(key: str) -> bool:
    """True if `key` (e.g. 'five_hour') names an hourly bucket; False for
    anything else (day/week/month buckets, or any future unit Anthropic might
    add — this is a catch-all, not an enumeration)."""
    _, _, unit = key.partition("_")
    return unit in ("hour", "hours")


def util_hour_reset_suffix(reset: int | None) -> str:
    """Time-only reset stamp for the hourly bucket — never a date, since a
    5-hour window can't meaningfully cross into a different day."""
    if reset is None:
        return ""
    return f" (↺ {datetime.fromtimestamp(reset).strftime('%H:%M')})"


def util_week_reset_suffix(reset: int | None) -> str:
    """Weekday + time reset stamp for the weekly bucket (e.g. 'Sun 14:10')."""
    if reset is None:
        return ""
    return f" (↺ {datetime.fromtimestamp(reset).strftime('%a %H:%M')})"


def util_rate_group_str(
    rate_limits: dict[str, Any], hourly: bool, show_reset: bool, theme: "Theme",
) -> str | None:
    """Format only the buckets whose unit matches `hourly` (True: hour(s);
    False: everything else — day/week/month) into one icon string, or None
    when no matching bucket reports a percentage."""
    suffix_fn = util_hour_reset_suffix if hourly else util_week_reset_suffix
    parts: list[str] = []
    now = time.time()
    # Visibility never depends on comparing resets_at against the clock: a bucket
    # is shown whenever it reports a percentage, regardless of whether its reset
    # is in the past or future, so a wrong system clock or timezone change can
    # never hide a bucket. Color, however, now does depend on the clock: the
    # gap below weighs used_percentage against how much of the bucket's window
    # has already elapsed (elapsed pct, via `now` and each bucket's resets_at).
    for key in sorted(rate_limits):
        if _rate_bucket_hourly(key) != hourly:
            continue
        info: dict[str, Any] = cast(dict[str, Any], rate_limits[key] or {})
        pct_raw: Any = info.get("used_percentage")
        if pct_raw is None:
            continue
        pct = float(pct_raw)
        reset: int | None = (int(info["resets_at"]) if info.get("resets_at") is not None
                             else None)
        gap = util_rate_gap(pct, key, reset, now)
        if gap is None:
            color = theme.c("WHITE")
            sign = ""
        else:
            color = util_gap_color(abs(gap), theme)
            # Same tier gate as the reset suffix (spec: the narrow/terse tier
            # omits the pace sign) -- seg_alt_h_rate_limit renders the terse
            # tier via util_rate_group_str(rl, True, False, theme), so an
            # ungated sign would leak into it.
            sign = util_gap_sign(gap) if show_reset else ""
        parts.append(f"{fmt_rate_key_label(key)}: {color}{sign}{round(pct)}%{RESET}"
                     + (suffix_fn(reset) if show_reset else ""))
    return util_icon("⚡", " | ".join(parts)) if parts else None
