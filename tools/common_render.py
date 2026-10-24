"""Render types and builder aliases for the Phase 23 D-02 status-line split."""
# pyright: strict

import json
import os
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from types import ModuleType
from typing import TYPE_CHECKING, Any, NamedTuple, Optional, cast

from common_config import cfg_default_config, cfg_load_config
from common_types import (
    DIM,
    EFFORT_GLYPHS,
    PALETTE_DEFAULTS,
    RESET,
    SEP,
    SLOWEST_META,
    WARN,
    ConfigSpec,
    Env,
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


class Host(NamedTuple):
    name: str
    config: ConfigSpec
    build_context: Callable[[dict[str, Any], "Config", "Theme", Env, int | None], "Context"]
    builders: dict[str, Builder]
    pinned: frozenset[str]
    right_margin: int
    effort_defaults: dict[str, tuple[str, int]]
    doctor_suffix: str


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

    raw: dict[str, Any]  # incoming status JSON (the ONLY dict-style member)
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


def core_doctor_cmd(suffix: str) -> str:
    """A concrete, copy-pasteable doctor invocation for THIS install — resolved
    from the running interpreter and the SIBLING statusline-doctor.py path
    (~-collapsed). Never a bare '--doctor', which would assume the user is sitting
    in a repo clone. Builds the string only; it does not import the doctor module,
    so it stays usable from inside a failed render."""
    py = os.path.basename(sys.executable) or "python3"
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "statusline-doctor.py")
    home = os.path.expanduser("~")
    if path == home or path.startswith(home + os.sep):
        path = "~" + path[len(home) :]
    return f"{py} {path} {suffix}"


class Theme:
    """Resolved colors for one render. `palette` maps NAME -> bare SGR params;
    `ramps` band -> [(ceil, escape)]; `effort` level -> (escape, bar). `c()`
    memoizes util_parse_color and never raises (invalid spec -> '')."""

    def __init__(
        self,
        palette: dict[str, str],
        ramps: dict[str, list[tuple[float, str]]],
        effort: dict[str, tuple[str, str]],
    ) -> None:
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
            continue  # unknown keys already warned in cfg_load_config
        esc = util_parse_color(value, palette=None)
        if esc is None:
            print(
                f"{DIM}status-line: bad palette {name}={value!r} — keeping default{RESET}",
                file=sys.stderr,
            )
            continue
        palette[name] = esc[2:-1]  # strip "\033[" .. "m" -> bare params
    return palette


def core_resolve_ramp(
    pairs: Any, palette: dict[str, str], band: str, fallback: list[tuple[float, str]] | None
) -> list[tuple[float, str]]:
    """Resolve [(threshold, colorspec)] -> [(ceil, escape)] sorted ascending.
    A bad band color falls back to that ceil's color in `fallback`; a bad
    threshold abandons the override and returns `fallback` whole. `fallback` is
    None only when resolving the built-in defaults (known-good)."""
    fb: dict[float, str] = dict(fallback) if fallback else {}
    out: list[tuple[float, str]] = []
    for thr, spec in cast(list[Any], pairs) if pairs else []:
        try:
            ceil = util_parse_threshold(thr)
        except ValueError:
            print(
                f"{DIM}status-line: bad ramp [{band}] threshold {thr!r} — keeping default{RESET}",
                file=sys.stderr,
            )
            return list(fallback) if fallback else out
        esc = util_parse_color(spec, palette)
        if esc is None:
            esc = fb.get(ceil, "")
            print(
                f"{DIM}status-line: bad ramp [{band}] color {spec!r} — using default band{RESET}",
                file=sys.stderr,
            )
        out.append((ceil, esc))
    out.sort(key=lambda ce: ce[0])
    return out


def core_build_effort(
    palette: dict[str, str], table: dict[str, tuple[str, int]]
) -> dict[str, tuple[str, str]]:
    """level -> (color escape, bar string). Filled glyphs in the level's color,
    the rest in grey (the effort-ladder layout)."""
    grey = util_parse_color("GREY", palette) or ""
    out: dict[str, tuple[str, str]] = {}
    for level, (name, n) in table.items():
        color = util_parse_color(name, palette) or ""
        rest = EFFORT_GLYPHS[n:]
        bar = f"{color}{EFFORT_GLYPHS[:n]}" + (f"{grey}{rest}" if rest else "")
        out[level] = (color, bar)
    return out


def core_build_theme(cfg: "Config", host: Host) -> "Theme":
    """Resolve a Config's palette + ramps + effort into a Theme."""
    palette = core_resolve_palette(cfg.palette)
    ramps: dict[str, list[tuple[float, str]]] = {}
    for band, default_pairs in host.config.ramp_defaults.items():
        default_ramp = core_resolve_ramp(default_pairs, palette, band, None)
        override = (cfg.ramps or {}).get(band)
        ramps[band] = (
            default_ramp
            if override is None
            else core_resolve_ramp(override.items(), palette, band, default_ramp)
        )
    return Theme(palette, ramps, core_build_effort(palette, host.effort_defaults))


def core_default_theme(host: Host) -> "Theme":
    """Theme from cfg_default_config() (no overrides)."""
    return core_build_theme(cfg_default_config(host.config), host)


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
    provider env mirror, and cwd = workspace dir. Returns the raw first
    non-empty stdout line, or None on timeout / non-zero exit / no output."""
    pos = util_position_str(spec.position)
    payload = json.dumps(
        {
            **(ctx.raw or {}),
            "segment": {"id": spec.id, "avail_cols": avail, "line": spec.line, "position": pos},
        }
    )
    env = dict(os.environ)
    line_conf = getattr(ctx, "line_conf", None)
    external = line_conf.external if line_conf is not None else None
    prefix = external.env_prefix if external is not None else ""
    env.update(
        {
            prefix + "COLS": str(avail),
            prefix + "ID": spec.id,
            prefix + "LINE": str(spec.line),
            prefix + "POSITION": pos,
        }
    )
    try:
        proc = subprocess.run(
            [spec.path],
            input=payload,
            capture_output=True,
            text=True,
            timeout=spec.timeout,
            cwd=ctx.work_dir or ".",
            env=env,
            check=False,
        )
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
    enabled: list[str],
    built: dict[str, str],
    budget: int,
    sep_w: int,
    pinned: frozenset[str],
) -> str:
    """Assemble in layout order, fitting left->right with every width known."""
    kept: list[str] = []
    used = 0
    for key in enabled:
        s = built.get(key)
        if not s:
            continue
        sep = sep_w if kept else 0
        if key in pinned or used + sep + util_visible_width(s) <= budget:
            kept.append(s)
            used += util_visible_width(s) + sep
    return SEP.join(kept)


def core_diagnostic_line(failed: set[str], doctor: str) -> str | None:
    """One line naming the segments that crashed this render, pointing at the
    doctor. Returns None when nothing failed (no cost on the happy path)."""
    if not failed:
        return None
    names = ", ".join(sorted(failed))
    n = len(failed)
    noun = "segment" if n == 1 else "segments"
    return f"{WARN}⚠ {n} {noun} failed: {names} — run the doctor: {doctor}{RESET}"


def core_discover_builders(*modules: ModuleType | type) -> dict[str, "Builder"]:
    """The built-in builder map, derived by convention from this module's
    `seg_<key>` functions (the homologous suffix is the segment key). Replaces the
    hand-maintained BUILDERS literal (FR-A.3, D7): adding a `seg_x` auto-registers
    it. SEGMENTS/LAYOUT stay explicit defaults tables — discovery removes only the
    redundant name->fn list, never the tables that encode intent."""
    builders: dict[str, Builder] = {}
    for module in modules:
        for name, fn in vars(module).items():
            if name.startswith("seg_") and callable(fn):
                segment_id = name[len("seg_") :]
                if segment_id in builders:
                    raise ValueError(f"duplicate segment id: {segment_id}")
                builders[segment_id] = cast(Builder, fn)
    return builders


def core_builders_for(cfg: "Config", host: Host) -> dict[str, "Builder"]:
    """The built-in BUILDERS merged with one synthetic builder per external
    provider (keyed by id). External ids never collide with built-ins by design;
    if a user names one after a built-in, the external wins for that render."""
    builders = dict(host.builders)
    for spec in cfg.external.providers if cfg.external else []:
        builders[spec.id] = core_make_external_builder(spec)
    return builders


def core_safe_build(
    key: str,
    ctx: "Context",
    avail: int,
    theme: "Theme",
    builders: dict[str, "Builder"],
) -> str | None:
    """Invoke one segment builder in isolation. On ANY exception, record `key`
    in `ctx.failed` and return a width-bounded warning marker instead of
    propagating — so a single bad segment can never blank the whole bar. The
    marker shows the segment name when it fits `avail`, else just the icon.
    `builders` defaults to the built-in BUILDERS registry."""
    try:
        return builders[key](ctx, avail, theme)
    except Exception:  # pylint: disable=broad-exception-caught  # never-blank isolation
        ctx.failed.add(key)
        named = f"{WARN}⚠{key}{RESET}"
        if util_visible_width(named) <= avail:
            return named
        return f"{WARN}⚠{RESET}"


def core_measure_all(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    ctx: "Context",
    cfg: "Config",
    budget: int,
    sep_w: int,
    theme: "Theme",
    builders: dict[str, "Builder"],
    pinned: frozenset[str],
) -> dict[tuple[int, str], str]:
    """Phase A: build + time every active non-meta segment across ALL rendered
    layout lines, crowning the single GLOBAL slowest (FR-4). Each line is walked
    left->right with its own shrinking `used_est` so `avail` (hence variant
    selection inside builders) matches the per-line fit exactly. Lines gated out
    by terminal height are skipped (via core_gated_lines), so their segments are
    never built/timed/crowned. Returns built strings keyed by `(line_index, key)`."""
    built: dict[tuple[int, str], str] = {}
    for line_index, enabled in core_gated_lines(ctx, cfg):
        used_est = 0
        for key in enabled:
            if key in SLOWEST_META:
                continue
            sep = sep_w if used_est else 0
            avail = max(budget - used_est - sep, 0)
            t0 = time.perf_counter_ns()
            s = core_safe_build(key, ctx, avail, theme, builders)
            ns = time.perf_counter_ns() - t0
            if not s:
                continue
            if key in pinned or util_visible_width(s) <= avail:
                built[(line_index, key)] = s
                used_est += util_visible_width(s) + sep
                core_crown_slowest(ctx, key, ns)
    return built


def core_build_meta(
    ctx: "Context",
    cfg: "Config",
    budget: int,
    theme: "Theme",
    builders: dict[str, "Builder"],
) -> dict[str, str]:
    """Phase B: build the meta segments (`render_time`, `slowest`) ONCE, now that
    every non-meta build is timed and `ctx.slowest`/`t_start` are settled (FR-4).
    A meta key is built when it is enabled on any height-gated-in line; the dict
    keying dedupes. Each is offered the full `budget` (it is placed per line in
    Phase C). Returns the shared meta strings reused across all lines."""
    meta_built: dict[str, str] = {}
    for _, enabled in core_gated_lines(ctx, cfg):
        for key in enabled:
            if key not in SLOWEST_META or key in meta_built:
                continue
            s = core_safe_build(key, ctx, budget, theme, builders)
            if s:
                meta_built[key] = s
    return meta_built


def core_render(
    ctx: "Context", host: Host, cfg: Optional["Config"] = None, theme: Optional["Theme"] = None
) -> list[str]:
    """Render up to len(cfg.layout) lines, gated by terminal height and width,
    in three phases (FR-4): Phase A measures + times every active non-meta segment
    across ALL gated-in lines and crowns the single GLOBAL slowest; Phase B builds
    the meta segments (`render_time`, `slowest`) ONCE off that settled state; Phase
    C assembles each gated-in line from its slice of Phase-A strings plus the shared
    meta. A trailing diagnostic line is appended only when a builder crashed. Reads
    geometry (cols/lines) and the shared `failed` set off `ctx`."""
    cfg = cfg or ctx.line_conf
    theme = theme or ctx.theme
    builders = core_builders_for(cfg, host)
    budget = ctx.cols - host.right_margin
    sep_w = util_visible_width(SEP)
    built = core_measure_all(ctx, cfg, budget, sep_w, theme, builders, host.pinned)  # Phase A
    meta_built = core_build_meta(ctx, cfg, budget, theme, builders)  # Phase B
    out: list[str] = []
    for line_index, enabled in core_gated_lines(ctx, cfg):  # Phase C
        line_built = {k: v for (i, k), v in built.items() if i == line_index}
        line_built.update(meta_built)
        packed = core_assemble_line(enabled, line_built, budget, sep_w, host.pinned)
        if packed:
            out.append(packed)
    diag = core_diagnostic_line(ctx.failed, core_doctor_cmd(host.doctor_suffix))
    if diag:
        out.append(diag)
    return out


# ═══ 8. SHELL — side effects only: env capture, stdin, print, render entrypoint ═


def safe_render(host: Host, raw: dict[str, Any], env: Env, t_start: int | None) -> list[str]:
    """Build context and render; failures produce one diagnostic line."""
    try:
        cfg = cfg_load_config(env, host.config)
        theme = core_build_theme(cfg, host)
        ctx = host.build_context(raw, cfg, theme, env, t_start)
        return core_render(ctx, host)
    except Exception:  # pylint: disable=broad-exception-caught  # never-blank isolation
        return [
            f"{WARN}⚠ status-line error — run the doctor: "
            f"{core_doctor_cmd(host.doctor_suffix)}{RESET}"
        ]


def main(host: Host) -> None:
    """CLI entrypoint: render the status line from stdin."""
    t_start = time.perf_counter_ns()
    try:
        raw: dict[str, Any] = json.load(sys.stdin)
    except (ValueError, OSError):
        raw = {}
    env = os.environ
    print("\n".join(safe_render(host, raw, env, t_start)))
