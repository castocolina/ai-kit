"""Host-neutral format helpers for the Phase 23 D-02 status-line split."""
# pyright: strict

from typing import Any

from common_types import Env

# ═══ 1. DEFAULTS — data-only: segment/layout/palette/ramp tables + type decls ═


_ENV_TRUE = {"1", "true", "t", "y", "yes", "on"}


_ENV_FALSE = {"0", "false", "f", "n", "no", "off"}

# ═══ 2. cfg_ — config loading & resolution (the only block that reads config env)


# kind -> (human description for messages, env-string parser).
# Open dispatch: add a kind by adding one row (no caller edits). bool/int only
# (FR scope; no float/list config field exists — YAGNI).
def cfg_coerce_env_bool(raw: str) -> tuple[Any, bool]:
    """(value, recognized). Unrecognized -> (None, False) = tri-state no-override."""
    v = raw.strip().lower()
    if v in _ENV_TRUE:
        return True, True
    if v in _ENV_FALSE:
        return False, True
    return None, False


def cfg_env_label(path: tuple[str, ...], prefix: str) -> str:
    """Message subject for an env field = the projected env var name."""
    head = "SEGMENT" if path[0] == "segments" else path[0].upper()
    return prefix + "_".join([head, *(p.upper() for p in path[1:])])


def cfg_env_segment_keys(env: Env, prefix: str) -> list[str]:
    """Lower-cased segment keys present under the supplied host prefix in env."""
    pre = prefix + "SEGMENT_"
    return [k[len(pre) :].lower() for k in env if k.startswith(pre)]


# ═══ 5. util_ — pure non-format helpers (window gauge) ═══════════════════════


def util_window_gap(
    pct: float, start: float | None, end: float | None, now: float
) -> float | None:
    """Compare usage with elapsed window time, or None when the window is invalid."""
    if start is None or end is None or end <= start:
        return None
    remaining = (end - now) * 100.0 / (end - start)
    if remaining < 0.0 or remaining > 100.0:
        return None
    return pct - (100.0 - remaining)
