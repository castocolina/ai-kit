"""Render types and builder aliases for the Phase 23 D-02 status-line split."""
# pyright: strict

import json
import os
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from common_config import cfg_default_config
from common_types import (
    DIM,
    EFFORT_DEFAULTS,
    EFFORT_GLYPHS,
    PALETTE_DEFAULTS,
    PINNED,
    RAMP_DEFAULTS,
    RESET,
    SEP,
    SLOWEST_META,
    WARN,
    util_parse_color,
    util_parse_threshold,
    util_position_str,
    util_sanitize_external,
    util_visible_width,
)

if TYPE_CHECKING:
    from common_types import Config, ExtSpec

# ═══ 1. DEFAULTS — data-only: segment/layout/palette/ramp tables + type decls ═


# A builder takes (ctx, avail_cols, theme) and returns a rendered string or None.
Builder = Callable[["Context", int, "Theme"], str | None]

# ═══ 6. core_ — render machinery: Context, Theme, registry, packer, render ════




def core_str_set() -> set[str]:
    """Typed factory for Context.failed — bare `set` loses the generic parameter."""
    return set()


def core_probe_cache() -> dict[str, Any]:
    """Typed factory for Context.probe_cache — bare `dict` loses the generic parameter."""
    return {}


@dataclass
class Context:  # pylint: disable=too-many-instance-attributes  # per-render bag (D1)
    """Per-render bag handed to every builder (D1). Eager inputs are resolved at
    the SHELL/CONFIG boundary; expensive probes are memoized via `probe_cache`
    so each probe runs synchronously on first access — its cost lands inside the
    *measured* build of the first segment that reads it (FR-R.2) and later reads
    are free. Render bookkeeping (`failed`, `slowest`) lives here too. Attribute
    access only — never `ctx[...]` (D4). `raw` keeps `.get()`-chain access."""
    raw: dict[str, Any]             # incoming status JSON (the ONLY dict-style member)
    line_conf: "Config"
    theme: "Theme"
    # per-render terminal geometry (resolved by the SHELL; D6 — never on Config)
    cols: int
    lines: int
    dim_assumed: bool
    t_start: int | None
    # cheap eager fields (were build_data's `base`)
    model_name: str
    model_id: str
    effort: str
    work_dir: str
    home: str
    clock: str
    added: int
    removed: int
    cost: float
    total_ms: int
    api_ms: int
    context_pct: int
    context_max: int
    rate_limits: dict[str, Any]
    # probe inputs (locate materialized todo/task state; feed the memoized probes)
    transcript: str
    session: str
    claude_dir: str
    # render bookkeeping (D1) — mutated during the render
    failed: set[str] = field(default_factory=core_str_set)
    slowest: tuple[str, int] | None = None
    # memoization cache for per-render probes (keyed by probe name)
    probe_cache: dict[str, Any] = field(default_factory=core_probe_cache)


def core_doctor_cmd() -> str:
    """A concrete, copy-pasteable doctor invocation for THIS install — resolved
    from the running interpreter and the SIBLING statusline-doctor.py path
    (~-collapsed). Never a bare '--doctor', which would assume the user is sitting
    in a repo clone. Builds the string only; it does not import the doctor module,
    so it stays usable from inside a failed render."""
    py = os.path.basename(sys.executable) or "python3"
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "statusline-doctor.py")
    home = os.path.expanduser("~")
    if path == home or path.startswith(home + os.sep):
        path = "~" + path[len(home):]
    return f"{py} {path} --doctor"


class Theme:
    """Resolved colors for one render. `palette` maps NAME -> bare SGR params;
    `ramps` band -> [(ceil, escape)]; `effort` level -> (escape, bar). `c()`
    memoizes util_parse_color and never raises (invalid spec -> '')."""

    def __init__(self, palette: dict[str, str],
                 ramps: dict[str, list[tuple[float, str]]],
                 effort: dict[str, tuple[str, str]]) -> None:
        self.palette = palette
        self.ramps = ramps
        self.effort = effort
        self._cache: dict[str, str] = {}

    def c(self, spec: str) -> str:
        """Resolve a color spec to an SGR string, memoizing the lookup."""
        if spec not in self._cache:
            self._cache[spec] = util_parse_color(spec, self.palette) or ""
        return self._cache[spec]


def core_resolve_palette(overrides: Any) -> dict[str, str]:
    """Merge _PALETTE_DEFAULTS with `overrides` ({NAME: spec}); each override
    value is parsed (hex / raw SGR / +mods — no name nesting) to bare params. A
    bad value warns and keeps the default."""
    palette = dict(PALETTE_DEFAULTS)
    for name, value in cast(dict[str, Any], overrides or {}).items():
        if name not in PALETTE_DEFAULTS:
            continue                       # unknown keys already warned in cfg_load_config
        esc = util_parse_color(value, palette=None)
        if esc is None:
            print(f"{DIM}status-line: bad palette {name}={value!r} — keeping "
                  f"default{RESET}", file=sys.stderr)
            continue
        palette[name] = esc[2:-1]          # strip "\033[" .. "m" -> bare params
    return palette


def core_resolve_ramp(pairs: Any, palette: dict[str, str], band: str,
                  fallback: list[tuple[float, str]] | None) -> list[tuple[float, str]]:
    """Resolve [(threshold, colorspec)] -> [(ceil, escape)] sorted ascending.
    A bad band color falls back to that ceil's color in `fallback`; a bad
    threshold abandons the override and returns `fallback` whole. `fallback` is
    None only when resolving the built-in defaults (known-good)."""
    fb: dict[float, str] = dict(fallback) if fallback else {}
    out: list[tuple[float, str]] = []
    for thr, spec in (cast(list[Any], pairs) if pairs else []):
        try:
            ceil = util_parse_threshold(thr)
        except ValueError:
            print(f"{DIM}status-line: bad ramp [{band}] threshold {thr!r} — "
                  f"keeping default{RESET}", file=sys.stderr)
            return list(fallback) if fallback else out
        esc = util_parse_color(spec, palette)
        if esc is None:
            esc = fb.get(ceil, "")
            print(f"{DIM}status-line: bad ramp [{band}] color {spec!r} — using "
                  f"default band{RESET}", file=sys.stderr)
        out.append((ceil, esc))
    out.sort(key=lambda ce: ce[0])
    return out


def core_build_effort(palette: dict[str, str]) -> dict[str, tuple[str, str]]:
    """level -> (color escape, bar string). Filled glyphs in the level's color,
    the rest in grey (the effort-ladder layout)."""
    grey = util_parse_color("GREY", palette) or ""
    out: dict[str, tuple[str, str]] = {}
    for level, (name, n) in EFFORT_DEFAULTS.items():
        color = util_parse_color(name, palette) or ""
        rest = EFFORT_GLYPHS[n:]
        bar = f"{color}{EFFORT_GLYPHS[:n]}" + (f"{grey}{rest}" if rest else "")
        out[level] = (color, bar)
    return out


def core_build_theme(cfg: "Config") -> "Theme":
    """Resolve a Config's palette + ramps + effort into a Theme."""
    palette = core_resolve_palette(cfg.palette)
    ramps: dict[str, list[tuple[float, str]]] = {}
    for band, default_pairs in RAMP_DEFAULTS.items():
        default_ramp = core_resolve_ramp(default_pairs, palette, band, None)
        override = (cfg.ramps or {}).get(band)
        ramps[band] = (default_ramp if override is None
                       else core_resolve_ramp(override.items(), palette, band, default_ramp))
    return Theme(palette, ramps, core_build_effort(palette))


def core_default_theme() -> "Theme":
    """Theme from cfg_default_config() (no overrides)."""
    return core_build_theme(cfg_default_config())


def core_cache_read(spec: "ExtSpec") -> str | None:
    """Cached raw output line if present and younger than ttl, else None.
    ttl <= 0 always misses (forces a re-run every render)."""
    if spec.ttl <= 0:
        return None
    try:
        age = time.time() - os.stat(spec.cache_path).st_mtime
    except OSError:
        return None
    if age >= spec.ttl:
        return None
    try:
        with open(spec.cache_path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def core_cache_write(spec: "ExtSpec", text: str) -> None:
    """Best-effort: persist raw output. Unwritable cache dir -> silently skip."""
    try:
        os.makedirs(os.path.dirname(spec.cache_path), exist_ok=True)
        with open(spec.cache_path, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass


def core_run_provider(spec: "ExtSpec", ctx: "Context", avail: int) -> str | None:
    """Spawn the provider with the status JSON + segment block on stdin, the
    AI_KIT_SEGMENT_* env mirror, and cwd = workspace dir. Returns the raw first
    non-empty stdout line, or None on timeout / non-zero exit / no output."""
    pos = util_position_str(spec.position)
    payload = json.dumps({**(ctx.raw or {}),
                          "segment": {"id": spec.id, "avail_cols": avail,
                                      "line": spec.line, "position": pos}})
    env = dict(os.environ)
    env.update({"AI_KIT_SEGMENT_COLS": str(avail), "AI_KIT_SEGMENT_ID": spec.id,
                "AI_KIT_SEGMENT_LINE": str(spec.line), "AI_KIT_SEGMENT_POSITION": pos})
    try:
        proc = subprocess.run(
            [spec.path], input=payload, capture_output=True, text=True,
            timeout=spec.timeout, cwd=ctx.work_dir or ".", env=env, check=False)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        if line.strip():
            return line
    return None


def core_run_external(spec: "ExtSpec", ctx: "Context", avail: int) -> str | None:
    """TTL-cached, timeout-bounded provider invocation. Returns the sanitized,
    width-fitted segment string, or None to omit the segment."""
    raw_line = core_cache_read(spec)
    if raw_line is None:
        raw_line = core_run_provider(spec, ctx, avail)
        if raw_line is None:
            return None
        core_cache_write(spec, raw_line)
    return util_sanitize_external(raw_line, avail)


def core_make_external_builder(spec: "ExtSpec") -> "Builder":
    """Wrap an ExtSpec as a seg_x(ctx, avail, theme)-shaped builder so the packer
    treats it exactly like a built-in. theme is unused (the provider colors itself)."""
    def _builder(ctx: "Context", avail: int, theme: "Theme") -> str | None:
        return core_run_external(spec, ctx, avail)
    return _builder


def core_crown_slowest(ctx: "Context", key: str, ns: int) -> None:
    """Record the slowest non-meta, non-crashed segment build this render — the
    single place the running max is tracked (FR-R.1). The meta segments report
    the whole render, not one builder, so they are never the culprit; a crashed
    segment (in `ctx.failed`) reports its warning marker's time, not real work."""
    if key in SLOWEST_META or key in ctx.failed:
        return
    cur = ctx.slowest
    if cur is None or ns > cur[1]:
        ctx.slowest = (key, ns)


def core_gated_lines(ctx: "Context", cfg: "Config") -> Iterator[tuple[int, list[str]]]:
    """Yield `(line_index, enabled_keys)` for each layout line that clears the
    terminal-height gate (`ctx.lines >= min_rows`). The single place the per-line
    height gate AND the enabled-segment filter are computed — all three render
    phases (measure / meta / assemble) consume it, so a future gate-rule change
    lives in exactly one spot."""
    for line_index, ln in enumerate(cfg.layout):
        if ctx.lines < ln.min_rows:
            continue
        yield line_index, [k for k in ln.segments if cfg.segments.get(k, False)]


def core_assemble_line(
    enabled: list[str], built: dict[str, str], budget: int, sep_w: int,
) -> str:
    """Assemble in layout order, fitting left->right with every width known."""
    kept: list[str] = []
    used = 0
    for key in enabled:
        s = built.get(key)
        if not s:
            continue
        sep = sep_w if kept else 0
        if key in PINNED or used + sep + util_visible_width(s) <= budget:
            kept.append(s)
            used += util_visible_width(s) + sep
    return SEP.join(kept)


def core_diagnostic_line(failed: set[str]) -> str | None:
    """One line naming the segments that crashed this render, pointing at the
    doctor. Returns None when nothing failed (no cost on the happy path)."""
    if not failed:
        return None
    names = ", ".join(sorted(failed))
    n = len(failed)
    noun = "segment" if n == 1 else "segments"
    return (f"{WARN}⚠ {n} {noun} failed: {names} — "
            f"run the doctor: {core_doctor_cmd()}{RESET}")
