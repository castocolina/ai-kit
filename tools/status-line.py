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

from claude_host import main

# ═══ 1. DEFAULTS — data-only: segment/layout/palette/ramp tables + type decls ═
# ═══ 2. cfg_ — config loading & resolution (the only block that reads config env)
# ═══ 3. probe_ — side-effecting data gatherers (git / proc / fs / subprocess) ═
# ═══ 4. fmt_ — pure formatters (number / tokens / duration / bytes / ago) ═════
# ═══ 5. util_ — pure non-format helpers (color / width / truncate / fit / parse)
# ═══ 6. core_ — render machinery: Context, Theme, registry, packer, render ════
# ═══ 7. seg_ — segment builders seg_x(ctx, avail, theme); auto-discovered registry
# ═══ 8. SHELL — side effects only: env capture, stdin, print, render entrypoint ═


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
