"""Claude host entrypoints for the Phase 23 D-02 status-line split."""
# pyright: strict

import claude_segments
import common_segments
from claude_payload import core_claude_context
from common_render import Host, core_discover_builders
from common_types import (
    RAMP_DEFAULTS as RAMP_BANDS,
)
from common_types import (
    ConfigSpec,
    Line,
)

SEGMENTS = {
    "path": True,
    "git_branch": True,
    "git_dirty": True,
    "alt_git_worktree": False,
    "model": True,
    "effort": True,
    "context": True,
    "todo": True,
    "alt_time_ago": False,
    "alt_time_clock": False,
    "alt_cost": False,
    "alt_time_session": False,
    "alt_time_api": False,
    "render_time": True,
    "slowest": True,
    "alt_term_dimensions": False,
    "lines": False,
    "chat_size": True,
    "alt_process_memory": False,
    "alt_h_rate_limit": False,
    "alt_w_rate_limit": False,
}
LAYOUT = [
    Line(0, ["path", "git_branch", "alt_git_worktree", "git_dirty"]),
    Line(20, ["model", "effort", "context", "todo"]),
    Line(
        30,
        [
            "render_time",
            "slowest",
            "alt_term_dimensions",
            "alt_time_ago",
            "alt_time_clock",
            "lines",
            "alt_cost",
            "alt_time_session",
            "alt_time_api",
            "chat_size",
            "alt_process_memory",
            "alt_h_rate_limit",
            "alt_w_rate_limit",
        ],
    ),
]
PINNED = {"path", "context"}
RIGHT_MARGIN = 4
EFFORT_DEFAULTS = {
    "low": ("CYAN", 1),
    "medium": ("BLUE", 2),
    "high": ("YELLOW", 3),
    "xhigh": ("ORANGE", 4),
    "max": ("RED", 5),
}
RAMP_DEFAULTS_CLAUDE = {
    "context": RAMP_BANDS["context"],
    "rate": [(50, "GREEN"), (80, "YELLOW"), ("inf", "RED+bold")],
    "chat_size": [
        ("512k", "WHITE"),
        ("1M", "CYAN"),
        ("2M", "LIGHTBLUE"),
        ("3M", "GREEN"),
        ("4M", "YELLOW"),
        ("5M", "ORANGE"),
        ("10M", "RED+bold"),
        ("inf", "MAGENTA"),
    ],
    "render_time": RAMP_BANDS["render_time"],
    "slowest": RAMP_BANDS["slowest"],
}

# ═══ 6. core_ — render machinery: Context, Theme, registry, packer, render ════

SPEC = ConfigSpec(
    "CC_AI_KIT_",
    "claude-statusline.toml",
    SEGMENTS,
    LAYOUT,
    RAMP_DEFAULTS_CLAUDE,
    "segments",
    "segments",
    "AI_KIT_SEGMENT_",
)
BUILDERS = core_discover_builders(common_segments, claude_segments)
HOST = Host(
    "claude",
    SPEC,
    core_claude_context,
    BUILDERS,
    frozenset(PINNED),
    RIGHT_MARGIN,
    EFFORT_DEFAULTS,
    "--doctor",
)


# HOW TO CUSTOMIZE
# The SEGMENTS and LAYOUT tables above are Claude's defaults. Add a NEW segment by
# implementing a seg_<id> builder in common_segments.py or claude_segments.py and
# placing its key in LAYOUT and SEGMENTS. Current keys include path, git_branch,
# git_dirty, todo, model, effort, context, lines, chat_size, alt_time_ago,
# alt_time_clock, alt_time_session, alt_time_api, alt_term_dimensions,
# alt_process_memory, alt_h_rate_limit and alt_w_rate_limit. The customization guide
# also explains how to Re-enable segments; all builders auto-deprioritize to fit.
# Reorder keys in LAYOUT to change priority; flip a SEGMENTS value to hide or
# re-enable an existing segment. Builders auto-deprioritize when their content does
# not fit, so each should offer progressively smaller variants.
#
# The registry is DERIVED from common_segments and claude_segments; do not maintain
# a separate key-to-function list.

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


# ═══ 7. seg_ — segment builders seg_x(ctx, avail, theme); auto-discovered registry


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
