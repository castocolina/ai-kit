#!/usr/bin/env python3
"""Cursor Agent statusline POC — not production; duplicates lean status-line patterns."""

from __future__ import annotations

import json
import math
import os
import re
import sys
import tempfile
import time
import tomllib
import unicodedata
from pathlib import Path
from types import SimpleNamespace
from typing import Any, BinaryIO

# ── constants ──────────────────────────────────────────────────────────────────

RESET = "\033[0m"
_DIM = "\033[90m"
SEP = " | "
_SLOWEST_META = frozenset({"render_time", "slowest"})
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")
_WIDE_BMP = {0x23F0, 0x23F1, 0x23F8, 0x26A1}

_PALETTE_DEFAULTS = {
    "GREY": "90",
    "WHITE": "97",
    "CYAN": "36",
    "GREEN": "32",
    "RED": "31",
    "YELLOW": "33",
    "ORANGE": "38;5;208",
    "BLUE": "38;5;39",
}

# Resolved ns ceilings for util_pick_color (50ms/150ms, 15ms/40ms).
_RAMP_NS = {
    "render_time": [(50_000_000.0, "GREEN"), (150_000_000.0, "YELLOW"), (math.inf, "RED")],
    "slowest": [(15_000_000.0, "GREEN"), (40_000_000.0, "YELLOW"), (math.inf, "RED")],
}

SEGMENTS: dict[str, bool] = {
    "path": True,
    "git_branch": True,
    "alt_git_worktree": True,
    "git_dirty": True,
    "model_compact": True,
    "included_total": True,
    "included_auto": True,
    "included_api": True,
    "reset": True,
    "on_demand": True,
    "process_memory": True,
    "system_memory": True,
    "render_time": True,
    "slowest": True,
}

LAYOUT: list[tuple[int, list[str]]] = [
    (0, ["path", "git_branch", "alt_git_worktree", "git_dirty"]),
    (0, ["model_compact"]),
    (0, ["included_total", "included_auto", "included_api", "reset", "on_demand"]),
    (0, ["process_memory", "system_memory", "render_time", "slowest"]),
]


class Config:
    """Resolved POC config: segments map + layout rows."""

    def __init__(
        self,
        segments: dict[str, bool],
        layout: list[tuple[int, list[str]]],
    ) -> None:
        self.segments = segments
        self.layout = layout


class Theme:
    """Palette + resolved ramps; `.c(name)` returns an SGR prefix."""

    def __init__(
        self,
        palette: dict[str, str],
        ramps: dict[str, list[tuple[float, str]]],
    ) -> None:
        self.palette = palette
        self.ramps = ramps
        self._cache: dict[str, str] = {}

    def c(self, name: str) -> str:
        if name not in self._cache:
            params = self.palette.get(name, "")
            self._cache[name] = f"\033[{params}m" if params else ""
        return self._cache[name]


def default_theme() -> Theme:
    palette = dict(_PALETTE_DEFAULTS)
    ramps: dict[str, list[tuple[float, str]]] = {}
    for band, pairs in _RAMP_NS.items():
        resolved: list[tuple[float, str]] = []
        for ceil, color in pairs:
            if color == "RED":
                resolved.append((ceil, f"\033[1;{palette['RED']}m"))
            else:
                resolved.append((ceil, f"\033[{palette[color]}m"))
        ramps[band] = resolved
    return Theme(palette, ramps)


def util_char_width(ch: str) -> int:
    if unicodedata.combining(ch):
        return 0
    o = ord(ch)
    if 0xFE00 <= o <= 0xFE0F:
        return 0
    if o >= 0x1F300:
        return 2
    if o in _WIDE_BMP:
        return 2
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def util_visible_width(s: str) -> int:
    return sum(util_char_width(c) for c in _ANSI_RE.sub("", s))


def util_pick_color(pct: float, ramp: list[tuple[float, str]]) -> str:
    for ceil, color in ramp:
        if pct < ceil:
            return color
    return ramp[-1][1]


def util_gap_color(delta: float, theme: Theme) -> str:
    if delta <= 5.0:
        return theme.c("GREEN")
    if delta < 11.0:
        return theme.c("YELLOW")
    if delta <= 15.0:
        return theme.c("ORANGE")
    return theme.c("RED")


def util_first_fitting(variants: list[str | None], avail: int) -> str | None:
    for v in variants:
        if v and util_visible_width(v) <= avail:
            return v
    return None


def util_icon(glyph: str, text: str) -> str:
    return f"{glyph} {text}"


def util_two_state_cap(s: str, high: int, low: int) -> str:
    if util_visible_width(s) <= high:
        return s
    out: list[str] = []
    width = 0
    for c in s:
        cw = util_char_width(c)
        if width + cw > low - 1:
            break
        out.append(c)
        width += cw
    return "".join(out) + "…"


def fmt_tokens(n: int | float) -> str:
    n = int(n)
    if n >= 1_000_000:
        return f"{n // 1_000_000}M"
    if n >= 1000:
        return f"{n // 1000}K"
    return str(n)


def fmt_bytes(n: int | float) -> str:
    n = int(n)
    if n < 1024:
        return f"{n}B"
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(n)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    if v < 10:
        return f"{math.ceil(v * 10) / 10:.1f}{units[i]}"
    return f"{math.ceil(v)}{units[i]}"


def fmt_duration(ns: int | float) -> str:
    ns = int(ns)
    if ns < 1000:
        return f"{ns}ns"
    for div, suffix in ((1_000_000_000, "s"), (1_000_000, "ms"), (1000, "µs")):
        if ns >= div:
            v = ns / div
            return f"{v:.1f}{suffix}" if v < 10 else f"{v:.0f}{suffix}"
    return f"{ns}ns"


def config_path(env: dict[str, str]) -> Path:
    explicit = env.get("AI_KIT_CURSOR_POC_CONFIG_FILE")
    if explicit:
        return Path(os.path.expanduser(explicit))
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
    return Path(base) / "ai-kit" / "cursor-statusline-poc.toml"


def load_config(env: dict[str, str]) -> Config:
    segments = dict(SEGMENTS)
    layout = list(LAYOUT)
    path = config_path(env)
    if not path.is_file():
        return Config(segments=segments, layout=layout)
    try:
        with path.open("rb") as fh:
            raw = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return Config(segments=segments, layout=layout)
    file_seg = raw.get("segments") or {}
    if isinstance(file_seg, dict):
        for k, v in file_seg.items():
            if k in segments and isinstance(v, bool):
                segments[k] = v
    lines = raw.get("line")
    if lines:
        new_layout: list[tuple[int, list[str]]] = []
        for ln in lines:
            if not isinstance(ln, dict):
                continue
            segs = ln.get("segments") or []
            if not isinstance(segs, list):
                continue
            min_rows = int(ln.get("min_rows") or 0)
            new_layout.append((min_rows, [str(s) for s in segs]))
        if new_layout:
            layout = new_layout
    return Config(segments=segments, layout=layout)


def fetch_quota(env: dict[str, str], *, now: float | int, urlopen: Any = None) -> dict[str, Any]:
    """Stub until Task 4 — hide-shaped empty quota."""
    del env, now, urlopen
    return {
        "total_pct": None,
        "auto_pct": None,
        "api_pct": None,
        "on_demand": {"kind": "unavailable"},
        "cycle_start_ms": 0,
        "cycle_end_ms": 0,
        "fetched_at": 0,
        "stale": False,
    }


def build_context(
    payload: dict[str, Any],
    env: dict[str, str],
    *,
    now: float | int | None = None,
    theme: Theme | None = None,
    config: Config | None = None,
) -> SimpleNamespace:
    del now  # Task 5 uses now for quota; Task 1 keeps signature stable.
    model = payload.get("model") if isinstance(payload.get("model"), dict) else {}
    workspace = payload.get("workspace") if isinstance(payload.get("workspace"), dict) else {}
    ctx_win = payload.get("context_window") if isinstance(payload.get("context_window"), dict) else {}
    cols_raw = payload.get("render_width_chars")
    cols = int(cols_raw) if isinstance(cols_raw, int) and cols_raw > 0 else 80
    pct_raw = ctx_win.get("used_percentage")
    context_pct: float | None
    if isinstance(pct_raw, (int, float)):
        context_pct = float(pct_raw)
    else:
        context_pct = None
    size_raw = ctx_win.get("context_window_size")
    context_max = int(size_raw) if isinstance(size_raw, int) and size_raw > 0 else 0
    cfg = config if config is not None else load_config(env)
    th = theme if theme is not None else default_theme()
    return SimpleNamespace(
        work_dir=str(workspace.get("current_dir") or ""),
        home=env.get("HOME", ""),
        model_name=str(model.get("display_name") or ""),
        param_summary=str(model.get("param_summary") or ""),
        max_mode=bool(model.get("max_mode")),
        context_pct=context_pct,
        context_max=context_max,
        cols=cols,
        config=cfg,
        theme=th,
        t_start=None,
        slowest=None,
        _git=None,
    )


# ── segment stubs / Task 1 bodies ──────────────────────────────────────────────


def seg_path(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del avail
    name = os.path.basename(ctx.work_dir.rstrip("/")) or ctx.work_dir or "?"
    return f"{theme.c('BLUE')}{name}{RESET}"


def seg_model_compact(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del theme
    name = ctx.model_name
    if not name:
        return None
    parts = [name]
    if ctx.context_max > 0:
        parts.append(fmt_tokens(ctx.context_max))
    if ctx.param_summary:
        parts.append(ctx.param_summary)
    if ctx.context_pct is not None:
        parts.append(f"{int(ctx.context_pct)}%")
    if ctx.max_mode:
        parts.append("max")
    text = " · ".join(parts)
    if util_visible_width(text) > avail > 0:
        # Truncate coarsely for POC.
        while parts and util_visible_width(" · ".join(parts)) > avail:
            if len(parts) > 1:
                parts.pop()
            else:
                break
        text = " · ".join(parts)
    return text


def seg_git_branch(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del ctx, avail, theme
    return None


def seg_alt_git_worktree(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del ctx, avail, theme
    return None


def seg_git_dirty(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del ctx, avail, theme
    return None


def seg_process_memory(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del ctx, avail, theme
    return None


def seg_system_memory(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del ctx, avail, theme
    return None


def seg_render_time(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del ctx, avail, theme
    return None


def seg_slowest(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del ctx, avail, theme
    return None


def seg_included_total(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del ctx, avail, theme
    return None


def seg_included_auto(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del ctx, avail, theme
    return None


def seg_included_api(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del ctx, avail, theme
    return None


def seg_reset(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del ctx, avail, theme
    return None


def seg_on_demand(ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    del ctx, avail, theme
    return None


BUILDERS: dict[str, Any] = {
    "path": seg_path,
    "git_branch": seg_git_branch,
    "alt_git_worktree": seg_alt_git_worktree,
    "git_dirty": seg_git_dirty,
    "model_compact": seg_model_compact,
    "included_total": seg_included_total,
    "included_auto": seg_included_auto,
    "included_api": seg_included_api,
    "reset": seg_reset,
    "on_demand": seg_on_demand,
    "process_memory": seg_process_memory,
    "system_memory": seg_system_memory,
    "render_time": seg_render_time,
    "slowest": seg_slowest,
}


def _safe_build(key: str, ctx: SimpleNamespace, avail: int, theme: Theme) -> str | None:
    fn = BUILDERS.get(key)
    if fn is None:
        return None
    try:
        return fn(ctx, avail, theme)
    except Exception:  # noqa: BLE001 — never-blank isolation
        return None


def _crown_slowest(ctx: SimpleNamespace, key: str, ns: int) -> None:
    if key in _SLOWEST_META:
        return
    cur = ctx.slowest
    if cur is None or ns > cur[1]:
        ctx.slowest = (key, ns)


def core_render(ctx: SimpleNamespace) -> str:
    cfg: Config = ctx.config
    theme: Theme = ctx.theme
    budget = ctx.cols
    sep_w = util_visible_width(SEP)
    built: dict[tuple[int, str], str] = {}

    # Pass A — non-meta
    for line_i, (_min_rows, keys) in enumerate(cfg.layout):
        used = 0
        for key in keys:
            if not cfg.segments.get(key, False):
                continue
            if key in _SLOWEST_META:
                continue
            sep = sep_w if used else 0
            avail = max(budget - used - sep, 0)
            t0 = time.perf_counter_ns()
            s = _safe_build(key, ctx, avail, theme)
            ns = time.perf_counter_ns() - t0
            if not s:
                continue
            if util_visible_width(s) <= avail or avail == budget:
                built[(line_i, key)] = s
                used += util_visible_width(s) + sep
                _crown_slowest(ctx, key, ns)

    # Pass B — meta once
    meta_built: dict[str, str] = {}
    for _min_rows, keys in cfg.layout:
        for key in keys:
            if key not in _SLOWEST_META or key in meta_built:
                continue
            if not cfg.segments.get(key, False):
                continue
            s = _safe_build(key, ctx, budget, theme)
            if s:
                meta_built[key] = s

    # Assemble
    lines_out: list[str] = []
    for line_i, (_min_rows, keys) in enumerate(cfg.layout):
        line_built = {k: v for (i, k), v in built.items() if i == line_i}
        line_built.update(meta_built)
        kept: list[str] = []
        used = 0
        for key in keys:
            if not cfg.segments.get(key, False):
                continue
            s = line_built.get(key)
            if not s:
                continue
            sep = sep_w if kept else 0
            if used + sep + util_visible_width(s) <= budget:
                kept.append(s)
                used += util_visible_width(s) + sep
        if kept:
            lines_out.append(SEP.join(kept))
    return "\n".join(lines_out)


def render_for_test(
    payload: dict[str, Any],
    env: dict[str, str],
    *,
    now: float | int | None = None,
) -> str:
    theme = default_theme()
    config = load_config(env)
    ctx = build_context(payload, env, now=now, theme=theme, config=config)
    ctx.t_start = time.perf_counter_ns()
    return core_render(ctx)


def render_from_raw(
    raw: bytes,
    env: dict[str, str],
    *,
    dump_payload_path: str | None = None,
    now: float | int | None = None,
) -> str:
    if dump_payload_path:
        path = Path(dump_payload_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".poc-dump.", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(raw)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    try:
        if not raw.strip():
            return ""
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            return ""
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError):
        return ""
    return render_for_test(payload, env, now=now)


def safe_render(
    raw: bytes,
    env: dict[str, str],
    *,
    now: float | int | None = None,
) -> str:
    try:
        return render_from_raw(raw, env, now=now)
    except Exception:  # noqa: BLE001 — never raises
        return ""


def main(
    argv: list[str] | None = None,
    stdin: BinaryIO | None = None,
    env: dict[str, str] | None = None,
) -> int:
    argv = list(sys.argv if argv is None else argv)
    env = dict(os.environ if env is None else env)
    dump_path: str | None = None
    if "--dump-payload" in argv:
        i = argv.index("--dump-payload")
        if i + 1 < len(argv):
            dump_path = argv[i + 1]
    src = sys.stdin.buffer if stdin is None else stdin
    raw = src.read()
    out = render_from_raw(raw, env, dump_payload_path=dump_path)
    if out:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
