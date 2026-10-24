#!/usr/bin/env python3
"""Claude Code status line — modular Python port of statusline.sh.

Reads the status JSON on stdin and prints up to three ANSI-colored lines.
Layout is driven by SEGMENTS (on/off), LAYOUT (template), and BUILDERS
(key -> builder(ctx, avail)). The packer is the authority on show/hide;
builders auto-deprioritize to fit. See the "HOW TO CUSTOMIZE" block near the
bottom. Stdlib only. The .sh original is kept as a fallback.
"""
# pyright: strict
# ARCHITECTURE — functional core / imperative shell, one file, nine role blocks.
# This module RENDERS ONLY: read stdin JSON -> pack -> print. Config introspection
# (--doctor / --check / --print-config) lives in the sibling statusline-doctor.py,
# which imports this render core one-way (never the reverse).
# Every top-level function carries a role prefix and lives in the matching block,
# so a reader can locate (and lift out) a whole role by name. Block order
# (functional core first, imperative shell last):
#   1. DEFAULTS  data only — SEGMENTS/LAYOUT/PINNED + palette/ramp/effort tables +
#                tuning scalars + fixed colors + type decls (Config/Line/
#                GitSnapshot/ExtSpec). No logic; edit a default here.
#   2. cfg_      config loading & resolution — the ONLY block that reads config
#                env/TOML -> one immutable Config (settings + resolved cache paths).
#   3. probe_    side-effecting data gatherers (git / proc / ps / fs / subprocess);
#                each owns its caching/TTL. Memoized per render so the cost lands
#                in the measured build of the first segment that calls it (FR-R.2).
#   4. fmt_      pure formatters (number / tokens / duration / bytes / ago).
#   5. util_     pure non-format helpers (color / width / truncate / fit / parse).
#   6. core_     render machinery — Context (attribute access only, D4), Theme, the
#                builder registry, the packer, and render.
#   7. seg_      seg_x(ctx, avail, theme) -> str | None, self-sourcing; the builder
#                map is auto-discovered from seg_* names (add a seg_x, it registers).
#   8. SHELL     side effects only (env capture, stdin, print); the render entrypoint.
#   9. HOW TO CUSTOMIZE — the segment-authoring guide. Introspection itself
#                (--doctor/--check/--print-config) is extracted to the sibling
#                statusline-doctor.py; this module no longer accepts those flags.
# To add a segment: write seg_<key>(ctx, avail, theme) in the seg_ block; add <key>
# to a LAYOUT line; add <key>: True to SEGMENTS. The registry wires itself.
# pylint: disable=invalid-name  # installed script name is hyphenated (status-line.py)

import json
import math
import os
import subprocess
import sys
import time
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Optional, cast

from claude_payload import cfg_resolve_effort, core_build_context
from claude_probes import (
    probe_ago,
    probe_chat_compaction,
    probe_chat_size,
    probe_effort_auto,
    probe_rss,
    probe_todo,
)
from claude_segments import util_rate_group_str
from common_config import cfg_default_config, cfg_load_config
from common_probe import probe_git_for, probe_terminal_size
from common_render import Theme
from common_types import (
    BG_LIGHTGRAY,
    CONTEXT_BAR_CELLS,
    DIM,
    EFFORT_DEFAULTS,
    EFFORT_GLYPHS,
    PALETTE_DEFAULTS,
    PATH_MAX_LEN,
    PINNED,
    RAMP_DEFAULTS,
    RESET,
    RIGHT_MARGIN,
    SEP,
    SLOWEST_META,
    WARN,
    Env,
    fmt_bytes,
    fmt_duration,
    fmt_number,
    fmt_time_ms,
    fmt_tokens,
    util_dirty_mark,
    util_display_dir,
    util_first_fitting,
    util_icon,
    util_parse_color,
    util_parse_threshold,
    util_pick_color,
    util_position_str,
    util_sanitize_external,
    util_two_state_cap,
    util_visible_width,
)

if TYPE_CHECKING:
    from common_render import Builder, Context
    from common_types import Config, ExtSpec

# ═══ 1. DEFAULTS — data-only: segment/layout/palette/ramp tables + type decls ═
# ═══ 2. cfg_ — config loading & resolution (the only block that reads config env)
# ═══ 3. probe_ — side-effecting data gatherers (git / proc / fs / subprocess) ═
# ═══ 4. fmt_ — pure formatters (number / tokens / duration / bytes / ago) ═════
# ═══ 5. util_ — pure non-format helpers (color / width / truncate / fit / parse)
# ═══ 6. core_ — render machinery: Context, Theme, registry, packer, render ════


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


# Editable surface (SEGMENTS + LAYOUT) is at the top of the file; the registry
# is DERIVED by convention from the seg_* functions above — no hand-maintained
# key->fn list to drift (FR-A.3, D7).
def core_discover_builders() -> dict[str, "Builder"]:
    """The built-in builder map, derived by convention from this module's
    `seg_<key>` functions (the homologous suffix is the segment key). Replaces the
    hand-maintained BUILDERS literal (FR-A.3, D7): adding a `seg_x` auto-registers
    it. SEGMENTS/LAYOUT stay explicit defaults tables — discovery removes only the
    redundant name->fn list, never the tables that encode intent."""
    # cast: globals() returns dict[str, Any]; the comprehension filters to seg_*
    # callables matching the Builder protocol — types are erased at this stdlib boundary.
    return cast(dict[str, "Builder"], {name[len("seg_"):]: fn
                                       for name, fn in globals().items()
                                       if name.startswith("seg_") and callable(fn)})


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


def core_builders_for(cfg: "Config") -> dict[str, "Builder"]:
    """The built-in BUILDERS merged with one synthetic builder per external
    provider (keyed by id). External ids never collide with built-ins by design;
    if a user names one after a built-in, the external wins for that render."""
    builders = dict(BUILDERS)
    for spec in (cfg.external.providers if cfg.external else []):
        builders[spec.id] = core_make_external_builder(spec)
    return builders


# RENDER CONTRACT (how a line becomes text):
#   * One registry, one gate. Built-in and external segments share a single
#     name->builder map (`core_builders_for`) and a single on/off gate
#     (`cfg.segments.get(name, False)`). Every builder is `seg_x(ctx, avail,
#     theme) -> str | None` and is interchangeable to the packer.
#   * One guarded entry. `core_safe_build` is the only place a builder is called; on
#     any exception it records the key in `failed` and returns a width-bounded
#     ⚠ marker, so one bad segment can never blank the bar (never-blank).
#   * Three phases. `core_render` orchestrates Phase A (`core_measure_all` —
#     build + time EVERY non-meta segment across ALL gated-in lines, with
#     `core_crown_slowest` tracking the single GLOBAL running max into
#     `ctx.slowest`), Phase B (`core_build_meta`), and Phase C
#     (`core_assemble_line`, per line). The Phase-A timing bracket captures each
#     segment's first-read probe cost (FR-R.2), so the crowned time is the
#     segment's REAL cost.
#   * Two meta segments. `render_time` and `slowest` (`_SLOWEST_META`) report the
#     whole render, not one builder, so they are built ONCE in Phase B (after
#     every non-meta build is timed, GLOBALLY — so the readout is the same on any
#     line) and placed at their LAYOUT position in assembly — never forced last,
#     never crowned as the culprit.
def core_safe_build(
    key: str, ctx: "Context", avail: int, theme: "Theme",
    builders: dict[str, "Builder"] | None = None,
) -> str | None:
    """Invoke one segment builder in isolation. On ANY exception, record `key`
    in `ctx.failed` and return a width-bounded warning marker instead of
    propagating — so a single bad segment can never blank the whole bar. The
    marker shows the segment name when it fits `avail`, else just the icon.
    `builders` defaults to the built-in BUILDERS registry."""
    builders = builders if builders is not None else BUILDERS
    try:
        return builders[key](ctx, avail, theme)
    except Exception:  # pylint: disable=broad-exception-caught  # never-blank isolation
        ctx.failed.add(key)
        named = f"{WARN}⚠{key}{RESET}"
        if util_visible_width(named) <= avail:
            return named
        return f"{WARN}⚠{RESET}"


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


def core_measure_all(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    ctx: "Context", cfg: "Config", budget: int, sep_w: int,
    theme: "Theme", builders: dict[str, "Builder"],
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
            if key in PINNED or util_visible_width(s) <= avail:
                built[(line_index, key)] = s
                used_est += util_visible_width(s) + sep
                core_crown_slowest(ctx, key, ns)
    return built


def core_build_meta(
    ctx: "Context", cfg: "Config", budget: int,
    theme: "Theme", builders: dict[str, "Builder"],
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


def core_render(
    ctx: "Context", cfg: Optional["Config"] = None, theme: Optional["Theme"] = None
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
    builders = core_builders_for(cfg)
    budget = ctx.cols - RIGHT_MARGIN
    sep_w = util_visible_width(SEP)
    built = core_measure_all(ctx, cfg, budget, sep_w, theme, builders)   # Phase A
    meta_built = core_build_meta(ctx, cfg, budget, theme, builders)      # Phase B
    out: list[str] = []
    for line_index, enabled in core_gated_lines(ctx, cfg):               # Phase C
        line_built = {k: v for (i, k), v in built.items() if i == line_index}
        line_built.update(meta_built)
        packed = core_assemble_line(enabled, line_built, budget, sep_w)
        if packed:
            out.append(packed)
    diag = core_diagnostic_line(ctx.failed)
    if diag:
        out.append(diag)
    return out


# ═══ 7. seg_ — segment builders seg_x(ctx, avail, theme); auto-discovered registry


# ── identity line ────────────────────────────────────────────────────────────
def seg_path(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    snap = probe_git_for(ctx)
    if snap.in_repo and snap.root_name:
        if snap.root_path:
            root = snap.root_path.rstrip("/")
            in_home = ctx.home and root.startswith(ctx.home)
            full = ("~" + root[len(ctx.home):]) if in_home else root
            parent = os.path.basename(os.path.dirname(root))
            structural = util_first_fitting([full, f"{parent}/{snap.root_name}"], PATH_MAX_LEN)
            shown = (structural if structural is not None
                     else util_two_state_cap(snap.root_name, 30, 20))
        else:
            # root_path unknown -> name-only floor
            shown = util_two_state_cap(snap.root_name, 30, 20)
    else:
        shown = util_display_dir(ctx.work_dir, ctx.home)
    return f"{theme.c('BLUE')}{shown}{RESET}"  # floor


def seg_git_branch(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    branch = probe_git_for(ctx).branch
    if not branch:
        return None
    # git_branch carries its own STATIC 🌿 icon. It does NOT encode worktree state
    # (no 🌳) — that moved to the dedicated `alt_git_worktree` ⎇ segment (FR-7.2);
    # the leaf glyph here is purely "this is the branch". Falls back to the bare
    # name when too narrow for the icon, so the branch never drops just for it.
    shown = util_two_state_cap(branch, 30, 20)
    return util_first_fitting([f"{theme.c('GREY')}[{util_icon('🌿', shown)}]{RESET}",
                           f"{theme.c('GREY')}[{shown}]{RESET}"], avail)


def seg_git_dirty(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    mark = util_dirty_mark(probe_git_for(ctx).dirty, theme)
    return util_first_fitting([mark], avail) if mark else None


def seg_alt_git_worktree(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    # alt_git_worktree names the ACTIVE linked worktree the session sits in —
    # never a list. Mirrors git_dirty's "absence is the neutral state": hidden
    # outside a repo. On the main checkout it shows a dimmed, struck `⎇ wt`
    # placeholder — GREY (not just strikethrough) so it stays distinct from the
    # cyan active form even on terminals that don't render SGR-9.
    snap = probe_git_for(ctx)
    if not snap.in_repo:
        return None
    if not snap.is_worktree:
        return util_first_fitting([f"{theme.c('GREY')}\033[9m⎇ wt{RESET}"], avail)
    name = util_two_state_cap(snap.wt_name or "", 30, 20)
    return util_first_fitting([f"{theme.c('CYAN')}⎇ {name}{RESET}"], avail)


def seg_todo(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    state, text = probe_todo(ctx)
    if not text:
        return None
    limit = avail - 4                      # room for icon + space + ellipsis
    if limit < 6:                          # too cramped to be useful -> hide
        return None
    if len(text) > limit:
        text = text[:limit - 1] + "…"
    if state == "in_progress":
        return util_icon("📝", f"{theme.c('YELLOW')}{text}{RESET}")
    if state == "pending":
        return util_icon("⏸", f"{theme.c('GREY')}{text}{RESET}")
    return None


# ── model row ────────────────────────────────────────────────────────────────
def seg_model(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    name = ctx.model_name or ctx.model_id
    if not name:
        return None
    return util_first_fitting([f"{theme.c('CYAN')}{name}{RESET}"], avail)


def seg_alt_time_ago(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    ago = probe_ago(ctx)
    if not ago:
        return None
    return util_first_fitting([f"{theme.c('WHITE')}{ago}{RESET}"], avail)


def seg_alt_time_clock(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    return util_first_fitting([util_icon("⏰", ctx.clock)], avail)


def seg_effort(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    level = ctx.effort
    if not level:
        return None
    # Unknown level (stale/future): no color on the word, all-grey ladder — a safe
    # degraded display. cfg_resolve_effort already strips "auto", so it never lands here.
    color, bar = theme.effort.get(level.lower(), ("", f"{theme.c('GREY')}▁▃▄▆█"))
    word = f"{color}{level}{RESET}"
    bars = util_icon("🧠", f"{bar}{RESET}")
    if probe_effort_auto(ctx):
        # effortLevel is unset/auto in settings: flag the resolved level as
        # auto-chosen. The flag degrades [auto] -> * -> dropped as space tightens.
        variants = [f"{bars} {word} {theme.c('GREY')}[auto]{RESET}",
                    f"{bars} {color}{level}*{RESET}",
                    f"{bars} {word}",
                    bars]
    else:
        variants = [f"{bars} {word}", bars]
    return util_first_fitting(variants, avail)


def seg_lines(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    body = (f"{BG_LIGHTGRAY}{theme.c('GREEN')}+{fmt_number(ctx.added)}{RESET}"
            f"/{BG_LIGHTGRAY}{theme.c('RED')}-{fmt_number(ctx.removed)}{RESET}")
    return util_first_fitting([util_icon("📃", body)], avail)


def seg_alt_cost(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    return util_first_fitting([util_icon("🪙", f"${float(ctx.cost):.3f}")], avail)


def seg_alt_time_session(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    return util_first_fitting([util_icon("💬", fmt_time_ms(ctx.total_ms))], avail)


def seg_alt_time_api(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    return util_first_fitting([util_icon("📡", fmt_time_ms(ctx.api_ms))], avail)


# ── diagnostics row ──────────────────────────────────────────────────────────
# status-line's own run time, SLO/SLA-colored
def seg_render_time(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    t0 = ctx.t_start
    if t0 is None:                      # not timed (e.g. direct builder calls) -> omit
        return None
    elapsed = time.perf_counter_ns() - t0
    color = util_pick_color(elapsed, theme.ramps["render_time"])
    return util_first_fitting([util_icon("⏱", f"{color}{fmt_duration(elapsed)}{RESET}")], avail)


# slowest single segment this render, SLO/SLA-colored
def seg_slowest(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    slow = ctx.slowest
    if not slow:                            # timing off (segment disabled) -> omit
        return None
    name, ns = slow
    color = util_pick_color(ns, theme.ramps["slowest"])
    dur = f"{color}{fmt_duration(ns)}{RESET}"
    # drop name when tight
    return util_first_fitting([util_icon("🐌", f"{name} {dur}"), util_icon("🐌", dur)], avail)


def seg_alt_term_dimensions(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    mark = "?" if ctx.dim_assumed else ""
    return util_first_fitting([f"{ctx.cols}×{ctx.lines}{mark}"], avail)


def seg_context(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    pct = int(ctx.context_pct)
    color = util_pick_color(pct, theme.ramps["context"])
    pct_only = util_icon("📊", f"{color}{pct}%{RESET}")
    # Measure in half-cells (5% each) and round up, so any pct > 0 shows >= ▌.
    halves = 0 if pct <= 0 else min(2 * CONTEXT_BAR_CELLS, math.ceil(pct / 5))
    full_n, half = divmod(halves, 2)
    bar_f = "█" * full_n + ("▌" if half else "")
    bar_e = "░" * (CONTEXT_BAR_CELLS - full_n - half)
    bar = f"{color}{bar_f}{theme.c('GREY')}{bar_e}{RESET}"
    mid = util_icon("📊", f"{bar} {color}{pct}%{RESET}")
    full = util_icon("📊", f"{bar} {color}{pct}% of {fmt_tokens(ctx.context_max)}{RESET}")
    return util_first_fitting([full, mid, pct_only], avail) or pct_only  # floor


def seg_chat_size(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    compaction = probe_chat_compaction(ctx)
    if compaction is None:
        return None
    since, count = compaction
    # memoized — free, already computed above; probe_chat_compaction is None
    # exactly when this is None, so it's safe to narrow here.
    total = cast(int, probe_chat_size(ctx))
    color = util_pick_color(since, theme.ramps["chat_size"])
    if count == 0:
        return util_first_fitting(
            [util_icon("💾", f"{color}{fmt_bytes(since)}{RESET}")], avail)
    rich = util_icon("💾", f"{color}{fmt_bytes(since)}/{fmt_bytes(total)} ({count}x){RESET}")
    terse = util_icon("💾", f"{color}{fmt_bytes(since)}{RESET}")
    return util_first_fitting([rich, terse], avail)


def seg_alt_process_memory(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    n = probe_rss(ctx)
    if n is None:
        return None
    return util_first_fitting([util_icon("🧮", fmt_bytes(n))], avail)


def seg_alt_h_rate_limit(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    rl = ctx.rate_limits
    if not rl:
        return None
    return util_first_fitting(
        [util_rate_group_str(rl, True, True, theme),
         util_rate_group_str(rl, True, False, theme)], avail)


def seg_alt_w_rate_limit(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    rl = ctx.rate_limits
    if not rl:
        return None
    return util_first_fitting(
        [util_rate_group_str(rl, False, True, theme),
         util_rate_group_str(rl, False, False, theme)], avail)


BUILDERS = core_discover_builders()   # module-level snapshot; same shape as the old literal


# Contract: every builder is seg_x(ctx, avail, theme) -> str | None.
#   avail = display cells available to this segment at its position.
#   Return None when there is no data, OR when even the smallest variant does
#   not fit avail (the builder self-deprioritizes). Otherwise return the richest
#   variant that fits, via util_first_fitting([rich, ..., minimal], avail).
# The packer (Phase A, core_measure_all) supplies avail and owns the final keep/skip decision.
# To add a segment: write seg_x(ctx, avail, theme), list its key in a LAYOUT line,
# add a SEGMENTS flag. The registry auto-discovers seg_* (no BUILDERS edit). See
# the HOW TO CUSTOMIZE block below.

# NOTE: the effort bars live on the Theme (theme.effort), resolved by
# core_build_effort from the palette so a [palette] override re-colors them too.
# `ultracode` is NOT a level (it reports as xhigh + standing multi-agent
# permission), and `auto` is a *setting*, not a resolved level — neither belongs
# in the table. The auto setting is surfaced as a "[auto]" suffix in seg_effort.


# ═══ 8. SHELL — side effects only: env capture, stdin, print, render entrypoint ═


def safe_render(raw: dict[str, Any], env: Env, cfg: "Config", theme: "Theme",
                t_start: int) -> list[str]:
    """Build context and render; on ANY unexpected failure return a single
    diagnostic line instead of a blank bar. Never raises. This is the backstop
    above core_safe_build's per-segment isolation (covers core_build_context itself)."""
    try:
        cols, lines, assumed = probe_terminal_size(env)
        home = env.get("HOME", "")
        claude_dir = env.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
        ctx = core_build_context(raw, cfg, theme, cols, lines, assumed, t_start,
                            effort=cfg_resolve_effort(raw),
                            home=home, claude_dir=claude_dir)
        return core_render(ctx)
    except Exception:  # pylint: disable=broad-exception-caught  # never-blank isolation
        return [f"{WARN}⚠ status-line error — "
                f"run the doctor: {core_doctor_cmd()}{RESET}"]


def main() -> None:
    """CLI entrypoint: render the status line from stdin. Renders only — config
    introspection (--doctor / --check / --print-config) lives in the sibling
    statusline-doctor.py, which imports this module one-way."""
    t0 = time.perf_counter_ns()        # for the optional `render_time` self-timing segment
    env = os.environ                   # single SHELL-boundary read (FR-A.1)
    cfg = cfg_load_config(env)
    theme = core_build_theme(cfg)
    try:
        raw: dict[str, Any] = json.load(sys.stdin)
    except (ValueError, OSError):
        raw = {}
    print("\n".join(safe_render(raw, env, cfg, theme, t0)))


# ═══ 9. HOW TO CUSTOMIZE — this module renders only. Config introspection
# (--doctor / --check / --print-config) lives in the sibling statusline-doctor.py,
# which imports this render core one-way. See that script to validate config and
# dry-render every builder.


# Three knobs at the top of the file drive everything:
#
#   SEGMENTS  — on/off flag per segment. False hides it everywhere and its
#               builder is never called (saves compute). Keep "path" True.
#   LAYOUT    — the template: a list of Line(min_rows, [segment keys]). Key order
#               in each list is LEFT->RIGHT priority; leftmost survive when the
#               terminal is narrow. min_rows gates the whole row by terminal rows.
#   BUILDERS  — auto-discovered from the seg_* functions (key = the suffix after
#               "seg_"). Not hand-maintained: write a seg_x and it registers.
#
# How show/hide is decided: the packer (Phase A, core_measure_all) is the authority. It offers
# each builder the space available at its spot (avail) and keeps the result only
# if it is non-empty and fits; otherwise it skips it and tries the next. A
# builder cooperates by auto-deprioritizing itself — returning a compact variant
# for a small avail, or None when even its smallest variant will not fit.
# PINNED segments ("path", "context") are kept even if they overflow.
#
# Available segments (key -> what it shows):
#   path                 working dir (~-collapsed; basename if long)   [pinned]
#   git_branch           git branch name
#   alt_git_worktree     ⎇ active linked-worktree name (struck ⎇ wt on the main checkout)
#   git_dirty            ✗ untracked / ~ modified marker
#   todo                 active TODO / task (truncated to fit)
#   model                model display name
#   alt_time_ago         time since last transcript activity
#   alt_time_clock       ⏰ wall clock HH:MM
#   effort               🧠 effort ramp bar (+ level word when room)
#   lines                📃 +added/-removed line counts
#   alt_cost             🪙 session cost in USD (off by default)
#   alt_time_session     💬 total session duration
#   alt_time_api         📡 total API duration
#   render_time          ⏱ status-line.py's own run time, SLO/SLA-colored via the
#                        render_time ramp
#   slowest              🐌 the slowest single segment this render (name + duration),
#                        SLO/SLA-colored via the shared slowest ramp
#   alt_term_dimensions  terminal COLS×ROWS (off by default; debug)
#   context              📊 context-window usage bar + percent         [pinned]
#   chat_size            💾 bytes since last compaction/total on disk (+ count)
#   alt_process_memory   🧮 agent process memory (RSS)
#   alt_h_rate_limit     ⚡ 5-hour rate-limit bucket (time-only reset)
#   alt_w_rate_limit     ⚡ 7-day rate-limit bucket (weekday reset)
#
# Common edits:
#   * Toggle a segment:       flip its SEGMENTS[...] value.
#   * Reorder within a line:  move its key within that Line's list.
#   * Move to another line:   cut its key from one Line list, paste into another.
#   * Re-enable a removed one: ensure (a) SEGMENTS[key] is True and (b) the key is
#                             in some LAYOUT line. (The seg_* builder is discovered
#                             automatically.) Both are required for it to show.
#   * Add a NEW segment:
#       1. Write a builder:  def seg_foo(ctx, avail, theme):
#              if no_data: return None
#              return util_first_fitting([rich_form, compact_form], avail)
#          (return None to hide; read what you need from `ctx`; let the builder
#          auto-deprioritize via util_first_fitting on the avail it is offered). The
#          registry discovers seg_foo by name — no BUILDERS edit needed.
#       2. Place it:         add  "foo"  to a LAYOUT line where you want it.
#       3. Flag it:          add  "foo": True  to SEGMENTS.
#       4. Test it:          add a case in tests/test_status_line.py.

if __name__ == "__main__":
    main()
