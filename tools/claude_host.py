"""Claude host entrypoints for the Phase 23 D-02 status-line split."""
# pyright: strict

import json
import os
import sys
import time
from typing import TYPE_CHECKING, Any, Optional, cast

import claude_segments
import common_segments
from claude_payload import cfg_resolve_effort, core_build_context
from common_config import cfg_load_config
from common_probe import probe_terminal_size
from common_render import (
    core_assemble_line,
    core_build_theme,
    core_crown_slowest,
    core_diagnostic_line,
    core_doctor_cmd,
    core_gated_lines,
    core_make_external_builder,
)
from common_types import (
    PINNED,
    RESET,
    RIGHT_MARGIN,
    SEP,
    SLOWEST_META,
    WARN,
    Env,
    util_visible_width,
)

if TYPE_CHECKING:
    from common_render import Builder, Context, Theme
    from common_types import Config

# ═══ 6. core_ — render machinery: Context, Theme, registry, packer, render ════


# Editable surface (SEGMENTS + LAYOUT) is at the top of the file; the registry
# is DERIVED by convention from the seg_* functions above — no hand-maintained
# key->fn list to drift (FR-A.3, D7).
def core_discover_builders() -> dict[str, "Builder"]:
    """The built-in builder map, derived by convention from this module's
    `seg_<key>` functions (the homologous suffix is the segment key). Replaces the
    hand-maintained BUILDERS literal (FR-A.3, D7): adding a `seg_x` auto-registers
    it. SEGMENTS/LAYOUT stay explicit defaults tables — discovery removes only the
    redundant name->fn list, never the tables that encode intent."""
    return cast(
        dict[str, "Builder"],
        {
            name[len("seg_"):]: fn
            for module in (common_segments, claude_segments)
            for name, fn in vars(module).items()
            if name.startswith("seg_") and callable(fn)
        },
    )


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


BUILDERS = core_discover_builders()   # module-level snapshot; same shape as the old literal

# ═══ 8. SHELL — side effects only: env capture, stdin, print, render entrypoint ═


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
