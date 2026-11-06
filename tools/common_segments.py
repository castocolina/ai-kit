"""Host-neutral segment builders for the Phase 23 D-02 status-line split."""
# pyright: strict

import math
import time
from typing import TYPE_CHECKING

from common_probe import probe_git_for, probe_transcript_ago
from common_types import (
    CONTEXT_BAR_CELLS,
    RESET,
    fmt_duration,
    fmt_tokens,
    util_dirty_mark,
    util_display_dir,
    util_first_fitting,
    util_icon,
    util_pick_color,
    util_two_state_cap,
)

if TYPE_CHECKING:
    from common_render import Context, Theme

# ═══ 7. seg_ — segment builders seg_x(ctx, avail, theme); auto-discovered registry




# ── identity line ────────────────────────────────────────────────────────────
def seg_path(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    snap = probe_git_for(ctx)
    if snap.in_repo and snap.root_name:
        # Inside a repo, tier on the repo ROOT (not the cwd) through the same
        # shared helper: full ~-relative → parent/name → name cap. basename of
        # the stripped root IS root_name, so this is byte-identical to the
        # inlined ladder it replaces (D-05: no second copy of the tiering).
        shown = (util_display_dir(snap.root_path, ctx.home) if snap.root_path
                 else util_two_state_cap(snap.root_name, 30, 20))
    else:
        shown = util_display_dir(ctx.work_dir, ctx.home)
    return util_icon("📂", f"{theme.c('BLUE')}{shown}{RESET}")  # floor


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
    return util_first_fitting([util_icon("✏", mark)], avail) if mark else None


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


# ── model row ────────────────────────────────────────────────────────────────
def seg_model(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    name = ctx.model_name or ctx.model_id
    if not name:
        return None
    if ctx.model_max:  # D-05: after param_summary, which the name already carries
        name += " · max"
    return util_first_fitting([util_icon("🤖", f"{theme.c('CYAN')}{name}{RESET}")], avail)


def seg_alt_time_clock(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    return util_first_fitting([util_icon("⏰", ctx.clock)], avail)


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
    # R8: a row count of 0 or less is no measurement; the width stands alone.
    size = f"{ctx.cols}×{ctx.lines}" if ctx.lines > 0 else f"{ctx.cols}"
    return util_first_fitting([util_icon("📐", f"{size}{mark}")], avail)


def seg_alt_time_ago(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    # Shared by both hosts (D-06).
    ago = probe_transcript_ago(ctx)
    if not ago:
        return None
    return util_first_fitting([util_icon("⌛", f"{theme.c('WHITE')}{ago}{RESET}")], avail)


def seg_context(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    if ctx.context_pct is None:
        return None
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
    full = (
        util_icon("📊", f"{bar} {color}{pct}% of {fmt_tokens(ctx.context_max)}{RESET}")
        if ctx.context_max is not None
        else None
    )
    return util_first_fitting([full, mid, pct_only], avail) or pct_only  # floor
