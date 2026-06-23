import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
import tomllib
import unittest
from unittest import mock

_HERE = os.path.dirname(__file__)
_MODULE_PATH = os.path.join(_HERE, "..", "tools", "status-line.py")


def load_module():
    spec = importlib.util.spec_from_file_location("status_line", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod          # register so @dataclass can resolve cls.__module__
    spec.loader.exec_module(mod)
    return mod


sl = load_module()

THEME = sl.core_default_theme()

ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def strip(s):
    return ANSI_RE.sub("", s)


NOW = 1_000_000  # fixed epoch for deterministic rate-limit tests


def _ctx_from_env(raw, env, cfg, t_start=None):
    """Resolve the per-render SHELL inputs from `env` and build a Context — the
    test-side mirror of what safe_render does in production (terminal size, HOME,
    claude_dir, effort). Returns (ctx, cols, lines) for call-site convenience."""
    cols, lines, assumed = sl.probe_terminal_size(env)
    home = env.get("HOME", "")
    claude_dir = env.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
    ctx = sl.core_build_context(raw, cfg, sl.core_default_theme(), cols, lines, assumed, t_start,
                           effort=sl.cfg_resolve_effort(raw, env), home=home, claude_dir=claude_dir)
    return ctx, cols, lines


def _data(**over):
    """Build a seeded Context for unit tests. Cheap eager fields are passed as
    constructor kwargs; expensive cached_property probes are injected into
    __dict__ to bypass computation entirely (no filesystem/git/process calls)."""
    eager = {
        "model_name": "Opus 4.8", "model_id": "claude-opus-4-8",
        "effort": "high", "work_dir": "/home/u/proj", "home": "/home/u",
        "clock": "14:30", "added": 12, "removed": 3, "cost": 0.5,
        "total_ms": 65000, "api_ms": 4200, "context_pct": 12,
        "context_max": 1_000_000, "rate_limits": {},
        "cols": 200, "lines": 50, "dim_assumed": False, "t_start": None,
        "transcript": "", "session": "", "claude_dir": "/home/u/.claude",
        "slowest": None,
    }
    probe_defaults = {
        "branch": "main", "dirty": "modified", "is_worktree": False,
        "in_repo": False, "wt_name": "",
        "ago": "5m 0s ago", "effort_auto": False,
        "todo_state": None, "todo_text": None,
        "chat_bytes": 305000, "mem_bytes": 448_790_528,
    }
    # Route overrides: eager fields go to the constructor, probes go to __dict__
    eager_over = {k: over.pop(k) for k in list(over) if k in eager}
    probe_over = {**probe_defaults, **over}
    eager.update(eager_over)
    ctx = sl.Context(raw={}, config=sl.cfg_default_config(), theme=THEME, **eager)
    # Seed cached_property slots directly so probes never fire during tests
    ctx.__dict__["_git"] = sl.GitSnapshot(
        in_repo=probe_over["in_repo"], branch=probe_over["branch"],
        dirty=probe_over["dirty"], is_worktree=probe_over["is_worktree"],
        wt_name=probe_over["wt_name"])
    ctx.__dict__["_todo"] = (probe_over["todo_state"], probe_over["todo_text"])
    for k in ("ago", "effort_auto", "chat_bytes", "mem_bytes"):
        ctx.__dict__[k] = probe_over[k]
    if "failed" in over:                 # render-bookkeeping override (else fresh set)
        ctx.failed = over["failed"]
    return ctx


class TestPickColor(unittest.TestCase):
    def test_context_ramp_bands(self):
        cases = [
            (5, THEME.c("WHITE")), (9, THEME.c("WHITE")),
            (10, THEME.c("CYAN")), (14, THEME.c("CYAN")),
            (15, THEME.c("BLUE")), (19, THEME.c("BLUE")),
            (20, THEME.c("GREEN")), (24, THEME.c("GREEN")),
            (25, THEME.c("YELLOW")), (29, THEME.c("YELLOW")),
            (30, THEME.c("ORANGE+bold")), (39, THEME.c("ORANGE+bold")),
            (40, THEME.c("RED+bold")), (49, THEME.c("RED+bold")),
            (50, THEME.c("MAGENTA_DARK+bold")), (99, THEME.c("MAGENTA_DARK+bold")),
        ]
        for pct, want in cases:
            self.assertEqual(sl.util_pick_color(pct, THEME.ramps["context"]), want, pct)

    def test_rate_ramp_bands(self):
        cases = [(0, THEME.c("GREEN")), (49, THEME.c("GREEN")), (50, THEME.c("YELLOW")),
                 (79, THEME.c("YELLOW")), (80, THEME.c("RED+bold")), (100, THEME.c("RED+bold"))]
        for pct, want in cases:
            self.assertEqual(sl.util_rate_color(pct, THEME), want, pct)

    def test_slowest_ramp_bands(self):
        # The single shared SLO/SLA ramp for the slowest segment: green under the
        # SLO (15ms), yellow under the SLA (40ms), red+bold beyond. Thresholds are
        # nanoseconds (matching data["slowest"]'s perf_counter_ns value).
        ms = 1_000_000
        cases = [
            (10 * ms, THEME.c("GREEN")), (14 * ms, THEME.c("GREEN")),
            (15 * ms, THEME.c("YELLOW")), (39 * ms, THEME.c("YELLOW")),
            (40 * ms, THEME.c("RED+bold")), (200 * ms, THEME.c("RED+bold")),
        ]
        for ns, want in cases:
            self.assertEqual(sl.util_pick_color(ns, THEME.ramps["slowest"]), want, ns)

    def test_slowest_ramp_override_replaces_band(self):
        # [ramp.slowest] in config REPLACES the default band wholesale.
        cfg = sl.cfg_default_config()._replace(ramps={"slowest": {"100ms": "CYAN", "inf": "WHITE"}})
        theme = sl.core_build_theme(cfg)
        ms = 1_000_000
        self.assertEqual(sl.util_pick_color(50 * ms, theme.ramps["slowest"]), theme.c("CYAN"))
        self.assertEqual(sl.util_pick_color(200 * ms, theme.ramps["slowest"]), theme.c("WHITE"))


class TestFormatters(unittest.TestCase):
    def test_fmt_number(self):
        self.assertEqual(sl.fmt_number(1234567), "1,234,567")

    def test_fmt_time_ms(self):
        self.assertEqual(sl.fmt_time_ms(500), "500ms")
        self.assertEqual(sl.fmt_time_ms(1500), "1s")
        self.assertEqual(sl.fmt_time_ms(65000), "1m 5s")
        self.assertEqual(sl.fmt_time_ms(3_700_000), "1h 1m")

    def test_fmt_tokens(self):
        self.assertEqual(sl.fmt_tokens(200000), "200K")
        self.assertEqual(sl.fmt_tokens(1_000_000), "1M")
        self.assertEqual(sl.fmt_tokens(999), "999")

    def test_fmt_ago(self):
        self.assertEqual(sl.fmt_ago(0), "just now")
        self.assertEqual(sl.fmt_ago(30), "30s ago")
        self.assertEqual(sl.fmt_ago(90), "1m 30s ago")
        self.assertEqual(sl.fmt_ago(3700), "1h 1m ago")

    def test_fmt_bytes(self):
        self.assertEqual(sl.fmt_bytes(512), "512B")
        self.assertEqual(sl.fmt_bytes(1536), "1.5KB")
        self.assertEqual(sl.fmt_bytes(305000), "298KB")  # ceil rounding

    def test_fmt_duration(self):
        # adaptive ns/µs/ms/s; one decimal when the scaled value is < 10
        self.assertEqual(sl.fmt_duration(0), "0ns")
        self.assertEqual(sl.fmt_duration(840), "840ns")
        self.assertEqual(sl.fmt_duration(1500), "1.5µs")
        self.assertEqual(sl.fmt_duration(12_000), "12µs")
        self.assertEqual(sl.fmt_duration(4_100_000), "4.1ms")
        self.assertEqual(sl.fmt_duration(45_000_000), "45ms")
        self.assertEqual(sl.fmt_duration(1_200_000_000), "1.2s")


class TestVisibleWidth(unittest.TestCase):
    def test_plain_ascii(self):
        self.assertEqual(sl.util_visible_width("hello"), 5)

    def test_ansi_is_zero_width(self):
        self.assertEqual(sl.util_visible_width(f'{THEME.c("RED")}hi{sl.RESET}'), 2)

    def test_smp_emoji_is_two_cells(self):
        for ch in "📊📝🧠💬📡💾🧮🌿🌳📃":
            self.assertEqual(sl.util_char_width(ch), 2, ch)

    def test_wide_bmp_symbols_are_two_cells(self):
        for ch in "⏰⏸⚡":
            self.assertEqual(sl.util_char_width(ch), 2, ch)

    def test_box_drawing_is_one_cell(self):
        for ch in "▁▃▄▆█▌░":
            self.assertEqual(sl.util_char_width(ch), 1, ch)

    def test_narrow_symbols_are_one_cell(self):
        for ch in "✗~↺":
            self.assertEqual(sl.util_char_width(ch), 1, ch)

    def test_combining_mark_is_zero(self):
        self.assertEqual(sl.util_visible_width("é"), 1)  # e + combining acute

    def test_mixed_segment(self):
        self.assertEqual(sl.util_visible_width("📊 12%"), 6)

    def test_variation_selector_is_zero_width(self):
        self.assertEqual(sl.util_char_width("️"), 0)  # VS16 emoji presentation
        self.assertEqual(sl.util_char_width("︎"), 0)  # VS15 text presentation

    def test_glyph_plus_vs16_measures_as_two(self):
        # ⏸ (modeled wide) + VS16 must stay 2 cells, not inflate to 3.
        self.assertEqual(sl.util_visible_width("⏸️ x"), 4)  # 2 + 0 + 1(space) + 1(x)


class TestFirstFitting(unittest.TestCase):
    def test_returns_richest_that_fits(self):
        self.assertEqual(sl.util_first_fitting(["abcdef", "abc", "a"], 4), "abc")

    def test_returns_first_when_all_fit(self):
        self.assertEqual(sl.util_first_fitting(["ab", "a"], 10), "ab")

    def test_none_when_nothing_fits(self):
        self.assertIsNone(sl.util_first_fitting(["abcdef", "abcd"], 3))

    def test_ignores_falsy_variants(self):
        self.assertEqual(sl.util_first_fitting([None, "", "ok"], 5), "ok")


class TestIconHelper(unittest.TestCase):
    def test_wide_emoji_gets_single_space(self):
        self.assertEqual(sl.util_icon("\U0001F4C3", "x"), "\U0001F4C3 x")  # 📃 x

    def test_narrow_rendering_glyph_gets_vs16(self):
        # ⏱ ⏸ ⚡ are modeled wide but render narrow bare -> force emoji presentation.
        self.assertEqual(sl.util_icon("⏱", "x"), "⏱️ x")  # ⏱️ x
        self.assertEqual(sl.util_icon("⏸", "x"), "⏸️ x")  # ⏸️ x
        self.assertEqual(sl.util_icon("⚡", "x"), "⚡️ x")  # ⚡️ x

    def test_already_wide_bmp_alarm_clock_no_vs16(self):
        self.assertEqual(sl.util_icon("⏰", "x"), "⏰ x")  # ⏰ is EAW=W already

    def test_icon_width_is_two_plus_space_plus_text(self):
        self.assertEqual(sl.util_visible_width(sl.util_icon("⏸", "12:00")), 8)  # 2+1+5


class TestNoCollapsedIcons(unittest.TestCase):
    # The five segments that previously glued the glyph to the value.
    def test_collapsers_have_a_space_after_the_icon(self):
        cases = {
            "⏰": sl.seg_clock(_data(), 80, THEME),                 # ⏰
            "\U0001F4C3": sl.seg_lines(_data(), 80, THEME),            # 📃
            "\U0001FA99": sl.seg_cost(_data(cost=0.5), 80, THEME),     # 🪙
            "\U0001F4AC": sl.seg_total_time(_data(), 80, THEME),       # 💬
            "\U0001F4E1": sl.seg_api_time(_data(), 80, THEME),         # 📡
        }
        for glyph, out in cases.items():
            plain = strip(out)
            self.assertTrue(plain.startswith(glyph), plain)
            after = plain[len(glyph):]
            self.assertTrue(after.startswith(" "), f"icon collapsed: {plain!r}")

    def test_no_segment_emits_glyph_then_nonspace(self):
        # Property check across the iconed builders at a wide budget.
        builders = [sl.seg_clock, sl.seg_lines, lambda d, a, t: sl.seg_cost(_data(cost=0.5), a, t),
                    sl.seg_total_time, sl.seg_api_time, sl.seg_render_time,
                    lambda d, a, t: sl.seg_context(_data(), a, t),
                    sl.seg_chat_size, sl.seg_memory]
        for b in builders:
            out = b(_data(t_start=sl.time.perf_counter_ns()), 120, THEME)
            if not out:
                continue
            plain = strip(out)
            for i, ch in enumerate(plain[:-1]):
                # An icon (wide glyph) must be followed by a space or VS16 — never
                # glued to text. Skip bar/box cells, which are legitimately wide.
                if sl.util_char_width(ch) == 2 and ch not in "█▌░":
                    nxt = plain[i + 1]
                    self.assertIn(nxt, (" ", "️"), f"{plain!r} collapses at {i}")


class TestEffortTable(unittest.TestCase):
    def test_effort_colors(self):
        want = {
            "low": THEME.c("CYAN"), "medium": THEME.c("BLUE"),
            "high": THEME.c("YELLOW"), "xhigh": THEME.c("ORANGE"), "max": THEME.c("RED"),
        }
        for level, color in want.items():
            self.assertEqual(THEME.effort[level][0], color, level)

    def test_effort_fill_counts(self):
        want = {"low": 1, "medium": 2, "high": 3, "xhigh": 4, "max": 5}
        for level, n in want.items():
            filled = THEME.effort[level][1].split(THEME.c("GREY"))[0]
            count = sum(filled.count(c) for c in "▁▃▄▆█")
            self.assertEqual(count, n, level)


class TestCooperativeBuilders(unittest.TestCase):
    def test_branch_content_then_self_hide(self):
        self.assertIn("main", sl.seg_branch(_data(branch="main"), 50, THEME))
        self.assertIsNone(sl.seg_branch(_data(branch="main"), 5, THEME))    # no room
        self.assertIsNone(sl.seg_branch(_data(branch=""), 200, THEME))      # no data

    def test_branch_has_static_icon_not_worktree_state(self):
        # branch carries its own STATIC 🌿 icon, but it must NOT encode worktree
        # state: no 🌳 (that meaning moved to the dedicated `worktree` ⎇ segment),
        # and the icon never changes with is_worktree.
        outs = []
        for wt in (True, False):
            out = sl.seg_branch(_data(branch="main", is_worktree=wt), 100, THEME)
            self.assertIn("main", out)
            self.assertIn("🌿", out)        # own branch icon restored
            self.assertNotIn("🌳", out)     # never the worktree-tree glyph
            self.assertNotIn("⎇", out)      # ⎇ belongs to the worktree segment
            outs.append(out)
        self.assertEqual(outs[0], outs[1])  # identical regardless of worktree state

    def test_worktree_active_shows_name_cyan(self):
        out = sl.seg_worktree(
            _data(in_repo=True, is_worktree=True, wt_name="feat-x"), 100, THEME)
        self.assertIn("⎇ feat-x", strip(out))
        self.assertIn(THEME.c("CYAN"), out)        # active form is cyan
        self.assertNotIn("\033[9m", out)           # NOT struck

    def test_worktree_main_checkout_struck_placeholder(self):
        out = sl.seg_worktree(_data(in_repo=True, is_worktree=False), 100, THEME)
        self.assertIn("⎇ wt", strip(out))
        self.assertIn("\033[9m", out)              # strikethrough SGR
        self.assertIn(THEME.c("GREY"), out)        # dimmed/grey, distinct from cyan

    def test_worktree_hidden_outside_repo(self):
        self.assertIsNone(sl.seg_worktree(_data(in_repo=False), 100, THEME))

    def test_worktree_name_truncated_to_20_cols(self):
        out = sl.seg_worktree(
            _data(in_repo=True, is_worktree=True, wt_name="a" * 40), 100, THEME)
        self.assertIn("…", out)
        # visible width (glyph + space + truncated name) stays within ~22 cols
        self.assertLessEqual(sl.util_visible_width(strip(out)), 24)

    def test_effort_full_then_compact_then_hide(self):
        self.assertIn("high", strip(sl.seg_effort(_data(effort="high"), 30, THEME)))
        compact = strip(sl.seg_effort(_data(effort="high"), 10, THEME))
        self.assertNotIn("high", compact)
        self.assertIn("▁▃▄", compact)
        self.assertIsNone(sl.seg_effort(_data(effort="high"), 5, THEME))
        self.assertIsNone(sl.seg_effort(_data(effort=""), 200, THEME))

    def test_effort_all_levels_full(self):
        for level in ("low", "medium", "high", "xhigh", "max"):
            out = strip(sl.seg_effort(_data(effort=level), 30, THEME))
            self.assertIn(level, out)
            self.assertTrue(out.startswith("🧠"))

    def test_context_three_tiers_never_none(self):
        self.assertIn("of 1M", strip(sl.seg_context(_data(context_pct=12), 200, THEME)))
        mid = strip(sl.seg_context(_data(context_pct=12), 18, THEME))
        self.assertNotIn("of 1M", mid)
        self.assertIn("█", mid)
        self.assertEqual(strip(sl.seg_context(_data(context_pct=12), 8, THEME)), "📊 12%")
        self.assertIsNotNone(sl.seg_context(_data(context_pct=12), 2, THEME))  # floor

    def test_context_low_pct_half_bar_and_zero_empty(self):
        self.assertIn("▌", strip(sl.seg_context(_data(context_pct=5), 200, THEME)))
        zero = strip(sl.seg_context(_data(context_pct=0), 200, THEME))
        self.assertNotIn("█", zero)
        self.assertNotIn("▌", zero)

    def test_render_time_times_self_then_self_hide(self):
        d = _data(t_start=sl.time.perf_counter_ns())
        out = sl.seg_render_time(d, 200, THEME)
        self.assertIn(THEME.c("GREEN"), out)            # fast run -> SLO green band
        out_s = strip(out)
        self.assertTrue(out_s.startswith("⏱"))          # stopwatch mark
        self.assertRegex(out_s, r"\d+(\.\d+)?(ns|µs|ms|s)$")  # a formatted duration
        self.assertIsNone(sl.seg_render_time(_data(), 200, THEME))  # no t_start -> omit
        self.assertIsNone(sl.seg_render_time(d, 1, THEME))         # no room -> hide

    def test_render_time_colors_by_slo_sla_ramp(self):
        # a slow run (200ms ago) lands in the red+bold band (beyond the SLA)
        slow = _data(t_start=sl.time.perf_counter_ns() - 200_000_000)
        self.assertIn(THEME.c("RED+bold"), sl.seg_render_time(slow, 200, THEME))

    def test_dimensions_content_then_self_hide(self):
        self.assertEqual(strip(sl.seg_dimensions(_data(cols=120, lines=40), 200, THEME)),
                         "120×40")
        self.assertIsNone(sl.seg_dimensions(_data(cols=120, lines=40), 3, THEME))

    def test_chat_memory_self_hide_when_cramped(self):
        self.assertIsNotNone(sl.seg_chat_size(_data(), 200, THEME))
        self.assertIsNone(sl.seg_chat_size(_data(), 3, THEME))
        self.assertIsNone(sl.seg_chat_size(_data(chat_bytes=None), 200, THEME))
        self.assertIsNone(sl.seg_memory(_data(mem_bytes=None), 200, THEME))

    def test_rate_limits_shows_reset_then_drops_suffix_when_narrow(self):
        rl = {"five_hour": {"used_percentage": 42, "resets_at": NOW + 3600}}
        self.assertIn("↺", strip(sl.seg_rate_limits(_data(rate_limits=rl), 200, THEME)))
        narrow = strip(sl.seg_rate_limits(_data(rate_limits=rl), 12, THEME))
        self.assertNotIn("↺", narrow)
        self.assertIn("5h", narrow)
        self.assertIsNone(sl.seg_rate_limits(_data(rate_limits={}), 200, THEME))

    def test_model_and_clock(self):
        self.assertEqual(strip(sl.seg_model(_data(), 200, THEME)), "Opus 4.8")
        self.assertEqual(strip(sl.seg_clock(_data(), 200, THEME)), "⏰ 14:30")

    def test_todo_truncates_and_hides(self):
        self.assertIn("hello", strip(sl.seg_todo(
            _data(todo_state="in_progress", todo_text="hello"), 200, THEME)))
        self.assertIsNone(sl.seg_todo(
            _data(todo_state="in_progress", todo_text="hello"), 8, THEME))

    def test_rate_visibility_independent_of_clock(self):
        # Every bucket shows regardless of how its resets_at compares to the
        # clock — a past reset must NOT hide a bucket (timezone/clock changes
        # must never affect which limits are visible).
        rl = {"five_hour": {"used_percentage": 42, "resets_at": NOW + 3600},
              "seven_day": {"used_percentage": 13, "resets_at": NOW - 60}}  # past reset
        out = strip(sl.seg_rate_limits(_data(rate_limits=rl), 200, THEME))
        self.assertIn("5h: 42%", out)
        self.assertIn("7d: 13%", out)      # past-reset bucket still shown

    def test_rate_past_reset_bucket_still_shown(self):
        rl = {"five_hour": {"used_percentage": 50, "resets_at": NOW - 1}}
        out = strip(sl.seg_rate_limits(_data(rate_limits=rl), 200, THEME))
        self.assertIn("5h: 50%", out)

    def test_rate_no_resets_at_kept_without_suffix(self):
        rl = {"five_hour": {"used_percentage": 30}}  # no reset stamp -> just the %
        out = strip(sl.seg_rate_limits(_data(rate_limits=rl), 200, THEME))
        self.assertIn("5h: 30%", out)
        self.assertNotIn("↺", out)

    def test_rate_far_future_bucket_shows_long_date_when_room(self):
        rl = {"seven_day": {"used_percentage": 30, "resets_at": NOW + 7 * 86400}}
        wide = strip(sl.seg_rate_limits(_data(rate_limits=rl), 200, THEME))
        self.assertRegex(wide, r"↺ [A-Z][a-z]{2} \d\d")   # e.g. "↺ Jan 19"

    def test_path_never_none(self):
        self.assertIsNotNone(sl.seg_path(_data(), 1, THEME))

    def test_builders_registry_complete(self):
        for key in ("path", "branch", "dirty", "todo", "model", "time_ago",
                    "clock", "effort", "lines", "cost", "total_time", "api_time",
                    "render_time", "dimensions", "context", "chat_size", "memory",
                    "rate_limits"):
            self.assertIn(key, sl.BUILDERS, key)
            self.assertTrue(callable(sl.BUILDERS[key]))

    def test_discovered_builders_cover_segments(self):
        # The registry is auto-discovered from the seg_* functions (FR-A.3, D7):
        # every SEGMENTS key has a discovered builder and discovery finds no stray
        # keys — guards the convention so adding a seg_x just works.
        self.assertEqual(set(sl.BUILDERS), set(sl.SEGMENTS))
        self.assertTrue(all(callable(fn) for fn in sl.BUILDERS.values()))


class TestDisplayDir(unittest.TestCase):
    def test_short_path_kept_whole(self):
        self.assertEqual(sl.util_display_dir("/home/u/proj", "/home/u"), "~/proj")

    def test_long_path_collapses_to_basename(self):
        long = "/home/u/very/long/path/exceeding/twenty/chars"
        self.assertEqual(sl.util_display_dir(long, "/home/u"), "chars")

    def test_no_ellipsis_prefix(self):
        long = "/home/u/very/long/path/exceeding/twenty/chars"
        self.assertNotIn("/", sl.util_display_dir(long, "/home/u"))


class TestPackLine(unittest.TestCase):
    def test_keeps_segments_that_fit(self):
        out = sl.core_pack(["model", "clock"], _data(), 200)
        self.assertIn("Opus 4.8", strip(out))
        self.assertIn("⏰ 14:30", strip(out))
        self.assertIn(" | ", out)

    def test_best_fit_skips_overflow_keeps_smaller(self):
        out = strip(sl.core_pack(["model", "clock"], _data(model_name="X" * 60), 30))
        self.assertIn("⏰ 14:30", out)
        self.assertNotIn("XXXX", out)

    def test_flag_off_segment_not_built(self):
        sl.SEGMENTS["clock"] = False
        try:
            out = strip(sl.core_pack(["model", "clock"], _data(), 200))
            self.assertNotIn("⏰", out)
        finally:
            sl.SEGMENTS["clock"] = True

    def test_pinned_path_present_even_when_too_narrow(self):
        out = strip(sl.core_pack(["path", "branch"],
                                 _data(work_dir="/home/u/proj", home="/home/u"), 5))
        self.assertIn("proj", out)

    def test_pinned_context_present_even_when_too_narrow(self):
        out = strip(sl.core_pack(["dimensions", "context"],
                                 _data(cols=300, lines=80, context_pct=12), 8))
        self.assertIn("12%", out)

    def test_respects_right_margin(self):
        out = sl.core_pack(["model", "clock", "effort", "lines"], _data(), 60)
        self.assertLessEqual(sl.util_visible_width(out), 60 - sl.RIGHT_MARGIN)


class TestSlowestTiming(unittest.TestCase):
    def test_probe_cost_counted_in_triggering_segment(self):
        # FR-A.2 / FR-R.2: a Context cached_property probe runs synchronously on
        # first read, so its cost lands INSIDE the measured build of the segment
        # that reads it — not amortized to µs. A live (un-seeded) Context whose
        # git probe sleeps proves the `branch` segment is crowned ms-scale, and
        # that the probe actually fired during core_pack (not pre-seeded).
        def slow_git(*_a, **_k):
            time.sleep(0.005)
            return sl.GitSnapshot(in_repo=True, branch="main", dirty="clean",
                                  is_worktree=False, wt_name="")
        cfg = sl.cfg_default_config()
        cfg.segments.update({"slowest": True, "branch": True})
        ctx = sl.core_build_context(
            raw={"workspace": {"current_dir": "/tmp"}}, config=cfg, theme=THEME,
            cols=200, lines=50, dim_assumed=False, t_start=sl.time.perf_counter_ns(),
            effort="high", home="/home/u", claude_dir="/home/u/.claude")
        with mock.patch.object(sl, "probe_git_snapshot", side_effect=slow_git):
            sl.core_pack(["branch"], ctx, 200, cfg=cfg)
        # The cached_property must have run during core_pack (proves laziness):
        self.assertIsNotNone(ctx.__dict__.get("_git"))
        name, ns = ctx.slowest
        self.assertEqual(name, "branch")
        self.assertGreaterEqual(ns, 4_000_000)   # >= ~4ms: probe cost is inside the build

    @staticmethod
    def _slow(data, avail, theme):
        time.sleep(0.005)
        return "SLOW"

    @staticmethod
    def _fast(data, avail, theme):
        return "FAST"

    def test_pack_line_records_slowest_builder(self):
        # With `slowest` enabled the packer times each builder and records the max
        # as ctx.slowest = (name, ns) — the exact attribute seg_slowest reads.
        builders = {"fast_seg": self._fast, "slow_seg": self._slow}
        cfg = sl.cfg_default_config()
        cfg.segments.update({"slowest": True, "fast_seg": True, "slow_seg": True})
        data = _data()
        sl.core_pack(["fast_seg", "slow_seg"], data, 200, cfg=cfg, builders=builders)
        name, ns = data.slowest
        self.assertEqual(name, "slow_seg")
        self.assertIsInstance(ns, int)
        self.assertGreater(ns, 0)

    def test_slowest_accumulates_max_across_lines(self):
        # core_render() packs each layout line sharing one ctx; the running max
        # must survive across core_pack calls (slow line first, fast line second).
        builders = {"fast_seg": self._fast, "slow_seg": self._slow}
        cfg = sl.cfg_default_config()
        cfg.segments.update({"slowest": True, "fast_seg": True, "slow_seg": True})
        data = _data()
        sl.core_pack(["slow_seg"], data, 200, cfg=cfg, builders=builders)
        sl.core_pack(["fast_seg"], data, 200, cfg=cfg, builders=builders)
        self.assertEqual(data.slowest[0], "slow_seg")   # not overwritten by the fast line

    def test_failed_builder_not_recorded_as_slowest(self):
        # A segment that crashes never rendered, so its time must not crown it the
        # slowest culprit (else seg_slowest would name a broken segment).
        def boom(data, avail, theme):
            raise RuntimeError("nope")
        builders = {"boom": boom, "fast_seg": self._fast}
        cfg = sl.cfg_default_config()
        cfg.segments.update({"slowest": True, "boom": True, "fast_seg": True})
        data = _data()
        sl.core_pack(["boom", "fast_seg"], data, 200, cfg=cfg, builders=builders)
        self.assertNotEqual((data.slowest or (None,))[0], "boom")

    def test_empty_output_builder_not_recorded_as_slowest(self):
        # A segment that renders nothing (e.g. a failing external provider that is
        # gracefully omitted) is not a visible culprit, so it isn't crowned slowest.
        def empty(data, avail, theme):
            return None
        builders = {"empty_seg": empty, "fast_seg": self._fast}
        cfg = sl.cfg_default_config()
        cfg.segments.update({"slowest": True, "empty_seg": True, "fast_seg": True})
        data = _data()
        sl.core_pack(["empty_seg", "fast_seg"], data, 200, cfg=cfg, builders=builders)
        self.assertNotEqual((data.slowest or (None,))[0], "empty_seg")

    def test_slowest_built_after_non_meta_regardless_of_position(self):
        # FR-R.3: with the two-pass packer, every non-meta build is timed in pass 1
        # before any meta segment is built in pass 2, so slowest no longer has to be
        # last on its line — it sits right after render_time.
        line = next(l for l in sl.LAYOUT if "slowest" in l.segments)
        self.assertNotEqual(line.segments[-1], "slowest")
        self.assertEqual(line.segments.index("slowest"),
                         line.segments.index("render_time") + 1)

    def test_later_segment_reported_even_when_slowest_precedes_it(self):
        # Two-pass: a slow non-meta segment is timed in pass 1, so seg_slowest names
        # it even when `slowest` is positioned BEFORE it in the key order.
        builders = dict(sl.BUILDERS)
        builders["slow_seg"] = self._slow
        cfg = sl.cfg_default_config()
        cfg.segments.update({"slowest": True, "slow_seg": True})
        data = _data()
        out = sl.core_pack(["slowest", "slow_seg"], data, 200, cfg=cfg, builders=builders)
        self.assertEqual(data.slowest[0], "slow_seg")
        self.assertIn("slow_seg", strip(out))      # seg_slowest (built in pass 2) names it

    def test_render_time_not_crowned_slowest(self):
        # M1: render_time is a meta-segment (reports the whole render); never a culprit.
        def slow_rt(data, avail, theme):
            time.sleep(0.005)
            return "RT"
        builders = {"render_time": slow_rt, "fast_seg": self._fast}
        cfg = sl.cfg_default_config()
        cfg.segments.update({"slowest": True, "render_time": True, "fast_seg": True})
        data = _data()
        sl.core_pack(["render_time", "fast_seg"], data, 200, cfg=cfg, builders=builders)
        self.assertNotEqual((data.slowest or (None,))[0], "render_time")

    def test_overflow_dropped_segment_not_recorded_slowest(self):
        # L1: a slow segment whose output is too wide to fit is dropped — it never
        # rendered, so it must not be crowned slowest.
        def slow_wide(data, avail, theme):
            time.sleep(0.005)
            return "X" * 100
        builders = {"wide_seg": slow_wide, "fast_seg": self._fast}
        cfg = sl.cfg_default_config()
        cfg.segments.update({"slowest": True, "wide_seg": True, "fast_seg": True})
        data = _data()
        sl.core_pack(["fast_seg", "wide_seg"], data, 20, cfg=cfg, builders=builders)
        self.assertNotEqual((data.slowest or (None,))[0], "wide_seg")

    def test_slowest_readout_hidden_when_disabled(self):
        # Builds are always timed now (negligible, and FR-R.1 drops the per-segment
        # special case) — but with `slowest` disabled its readout is gated off and
        # never renders. The internal max may be tracked; the user never sees it.
        cfg = sl.cfg_default_config()
        cfg.segments["slowest"] = False
        theme = sl.core_build_theme(cfg)
        env = {"HOME": "/h", "STATUSLINE_COLS": "200", "STATUSLINE_LINES": "50"}
        with mock.patch.object(sl, "probe_git_snapshot",
                               return_value=sl.GitSnapshot(True, "m", "clean", False, "")):
            data, _cols, _lines = _ctx_from_env(
                {"workspace": {"current_dir": "."}, "transcript_path": ""}, env, cfg)
            out = "\n".join(sl.core_render(data, cfg, theme))
        self.assertNotIn("🐌", strip(out))


class TestSlowestSegment(unittest.TestCase):
    def test_renders_culprit_name_and_duration(self):
        out = sl.seg_slowest(_data(slowest=("git", 30_000_000)), 200, THEME)
        self.assertIn("🐌", out)
        self.assertIn("git", strip(out))       # names the culprit segment
        self.assertIn("30ms", strip(out))      # and its duration

    def test_colored_by_single_slowest_ramp(self):
        # 30ms -> YELLOW band, 100ms -> RED+bold — the one shared slowest ramp.
        self.assertIn(THEME.c("YELLOW"),
                      sl.seg_slowest(_data(slowest=("git", 30_000_000)), 200, THEME))
        self.assertIn(THEME.c("RED+bold"),
                      sl.seg_slowest(_data(slowest=("ext", 100_000_000)), 200, THEME))

    def test_omitted_when_no_timing(self):
        self.assertIsNone(sl.seg_slowest(_data(), 200, THEME))   # no data["slowest"]

    def test_on_by_default_and_registered(self):
        self.assertTrue(sl.SEGMENTS["slowest"])
        self.assertIn("slowest", sl.BUILDERS)


class TestRenderLayout(unittest.TestCase):
    def test_three_lines_when_tall_and_wide(self):
        self.assertEqual(len(sl.core_render(_data())), 3)

    def test_line_gating_by_rows(self):
        self.assertEqual(len(sl.core_render(_data(lines=10))), 1)   # identity only
        self.assertEqual(len(sl.core_render(_data(lines=25))), 2)   # + model row

    def test_identity_line_never_empty(self):
        out = sl.core_render(_data(branch="", dirty="clean", todo_text=None))
        self.assertTrue(out[0].strip())

    def test_context_pinned(self):
        self.assertIn("context", sl.PINNED)
        self.assertIn("path", sl.PINNED)


class TestDocumentation(unittest.TestCase):
    def _src(self):
        with open(_MODULE_PATH) as f:
            return f.read()

    def test_module_lists_all_segments(self):
        src = self._src()
        for key in ("path", "branch", "dirty", "todo", "model", "time_ago",
                    "clock", "effort", "lines", "total_time", "api_time",
                    "render_time", "dimensions", "context", "chat_size", "memory",
                    "rate_limits"):
            self.assertIn(key, src, key)

    def test_has_customization_guide(self):
        src = self._src()
        for phrase in ("HOW TO CUSTOMIZE", "Add a NEW segment",
                       "Reorder", "Re-enable", "auto-deprioritize"):
            self.assertIn(phrase, src, phrase)


class TestProcAndGit(unittest.TestCase):
    def test_proc_rss_and_git_smoke(self):
        rss = sl.probe_rss_bytes()
        self.assertTrue(rss is None or isinstance(rss, int))
        with tempfile.TemporaryDirectory() as home:
            env = {"HOME": home}
            cfg = sl.cfg_default_config()._replace(cache_base=sl.cfg_cache_base(env))
            snap = sl.probe_git_snapshot(".", cfg)
        self.assertIn(snap.dirty, ("clean", "untracked", "modified"))
        self.assertIsInstance(snap.is_worktree, bool)
        self.assertIsInstance(snap.wt_name, str)

    def test_branch_from_porcelain_header(self):
        self.assertEqual(sl.util_branch_from_porcelain("## main"), "main")
        self.assertEqual(sl.util_branch_from_porcelain("## main...origin/main"), "main")
        self.assertEqual(
            sl.util_branch_from_porcelain("## feat/x...origin/feat/x [ahead 18]"), "feat/x")
        self.assertEqual(sl.util_branch_from_porcelain("## HEAD (no branch)"), "")   # detached
        self.assertEqual(sl.util_branch_from_porcelain("## No commits yet on main"), "main")
        self.assertEqual(sl.util_branch_from_porcelain("## Initial commit on dev"), "dev")
        self.assertEqual(sl.util_branch_from_porcelain(""), "")                      # not a repo

    def _home_env(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        return {"HOME": d}

    def test_git_snapshot_dirty_parsing(self):
        # probe_git_snapshot parses branch + dirty from the porcelain --branch output;
        # mock subprocess so the test is independent of the live working tree.
        def fake_run(cmd, **kw):
            class R:
                returncode = 0
                stdout = ("## main...origin/main [ahead 1]\n M tools/x.py\n?? new.py\n"
                          if "status" in cmd else ".git\n.git\n/repo\n")
            return R()
        env = self._home_env()
        cfg = sl.cfg_default_config()._replace(cache_base=sl.cfg_cache_base(env))
        with mock.patch.object(sl.subprocess, "run", side_effect=fake_run):
            snap = sl.probe_git_snapshot(".", cfg)
            self.assertEqual(snap.branch, "main")
            self.assertEqual(snap.dirty, "untracked")   # ?? present -> untracked
            self.assertFalse(snap.is_worktree)          # git-dir == git-common-dir

    def test_git_snapshot_always_does_full_untracked_walk(self):
        # The probe owns its policy: it ALWAYS does the full untracked walk (no
        # per-call gating knob). Laziness — not a flag — gates whether it runs.
        env = self._home_env()
        cfg = sl.cfg_default_config()._replace(cache_base=sl.cfg_cache_base(env))
        seen = []
        def fake_run(cmd, *, _seen=seen, **kw):
            _seen.append(cmd)
            class R:
                returncode = 0
                stdout = "## main\n"
            return R()
        with mock.patch.object(sl.subprocess, "run", side_effect=fake_run):
            sl.probe_git_snapshot(".", cfg)
        status_cmd = next(c for c in seen if "status" in c)
        self.assertNotIn("--untracked-files=no", status_cmd)   # always the full walk

    def test_git_snapshot_always_runs_worktree_probe(self):
        # The probe always runs the worktree rev-parse (no want_worktree knob);
        # laziness gates whether probe_git_snapshot is called at all, not this rev-parse.
        env = self._home_env()
        cfg = sl.cfg_default_config()._replace(cache_base=sl.cfg_cache_base(env))
        seen = []
        def fake_run(cmd, *, _seen=seen, **kw):
            _seen.append(cmd)
            class R:
                returncode = 0
                stdout = "## main\n" if "status" in cmd else ".git\n.git\n/repo\n"
            return R()
        with mock.patch.object(sl.subprocess, "run", side_effect=fake_run):
            sl.probe_git_snapshot(".", cfg)
        self.assertTrue(any("rev-parse" in c for c in seen))

    def test_git_snapshot_clean_and_worktree_name(self):
        def fake_run(cmd, **kw):
            class R:
                returncode = 0
                stdout = ("## main\n" if "status" in cmd
                          else "/wt/.git/worktrees/feat-x\n/main/.git\n/path/to/feat-x\n")
            return R()
        env = self._home_env()
        cfg = sl.cfg_default_config()._replace(cache_base=sl.cfg_cache_base(env))
        with mock.patch.object(sl.subprocess, "run", side_effect=fake_run):
            snap = sl.probe_git_snapshot(".", cfg)
            self.assertEqual((snap.branch, snap.dirty), ("main", "clean"))
            self.assertTrue(snap.is_worktree)        # git-dir != git-common-dir
            self.assertTrue(snap.in_repo)
            self.assertEqual(snap.wt_name, "feat-x")  # basename of --show-toplevel

    def test_worktree_info_cached_within_ttl(self):
        # Second call within the TTL must NOT re-run the rev-parse (cached on disk).
        env = self._home_env()
        cache_base = sl.cfg_cache_base(env)
        cfg = sl.cfg_default_config()._replace(cache_base=cache_base, git={"cache_ttl": 100})
        calls = []
        def fake_run(cmd, **kw):
            calls.append(cmd)
            class R:
                returncode = 0
                stdout = "## main\n" if "status" in cmd else ".git\n.git\n/repo\n"
            return R()
        with mock.patch.object(sl.subprocess, "run", side_effect=fake_run):
            sl.probe_git_snapshot(".", cfg)
            sl.probe_git_snapshot(".", cfg)
        self.assertEqual(sum("rev-parse" in c for c in calls), 1)   # only once

    def test_worktree_cache_bypassed_when_ttl_zero(self):
        env = self._home_env()
        cache_base = sl.cfg_cache_base(env)
        cfg = sl.cfg_default_config()._replace(cache_base=cache_base, git={"cache_ttl": 0})
        calls = []
        def fake_run(cmd, **kw):
            calls.append(cmd)
            class R:
                returncode = 0
                stdout = "## main\n" if "status" in cmd else ".git\n.git\n/repo\n"
            return R()
        with mock.patch.object(sl.subprocess, "run", side_effect=fake_run):
            sl.probe_git_snapshot(".", cfg)
            sl.probe_git_snapshot(".", cfg)
        self.assertEqual(sum("rev-parse" in c for c in calls), 2)   # ttl<=0 always runs

    def test_worktree_cache_not_written_when_ttl_zero(self):
        # ttl<=0 forces a fresh probe every render, so the cache file is never
        # read — it must therefore never be WRITTEN either (no wasted disk I/O on
        # the hot render path).
        env = self._home_env()
        cache_base = sl.cfg_cache_base(env)
        cfg = sl.cfg_default_config()._replace(cache_base=cache_base, git={"cache_ttl": 0})
        def fake_run(cmd, **kw):
            class R:
                returncode = 0
                stdout = "## main\n" if "status" in cmd else ".git\n.git\n/repo\n"
            return R()
        with mock.patch.object(sl.subprocess, "run", side_effect=fake_run):
            sl.probe_git_snapshot(".", cfg)
        self.assertFalse(os.path.exists(sl.util_git_cache_path(".", cache_base)))


class TestCurrentTodo(unittest.TestCase):
    """probe_current_todo prefers Claude's materialized task/todo state on disk over
    replaying the transcript."""

    def _write(self, path, obj):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(obj, f)

    def test_pick_helpers(self):
        self.assertEqual(
            sl.util_pick_from_tasks(
                [{"status": "in_progress", "activeForm": "Doing X", "subject": "X"}]),
            ("in_progress", "Doing X"))
        self.assertEqual(
            sl.util_pick_from_tasks([{"status": "pending", "subject": "Y"}]),
            ("pending", "Y"))
        self.assertIsNone(sl.util_pick_from_tasks([{"status": "completed", "subject": "Z"}]))
        self.assertEqual(
            sl.util_pick_from_todos([{"status": "in_progress", "activeForm": "Doing"}]),
            ("in_progress", "Doing"))

    def test_reads_managed_tasks_dir(self):
        with tempfile.TemporaryDirectory() as cd:
            s = "sess1"
            self._write(os.path.join(cd, "tasks", s, "1.json"),
                        {"id": "1", "subject": "first", "activeForm": "Doing first",
                         "status": "completed"})
            self._write(os.path.join(cd, "tasks", s, "2.json"),
                        {"id": "2", "subject": "second", "activeForm": "Doing second",
                         "status": "in_progress"})
            self.assertEqual(sl.probe_current_todo("", s, cd), ("in_progress", "Doing second"))

    def test_tasks_dir_all_done_is_authoritative(self):
        # Dir has files but none active -> (None, None); must NOT replay transcript.
        with tempfile.TemporaryDirectory() as cd:
            s = "sess2"
            self._write(os.path.join(cd, "tasks", s, "1.json"),
                        {"id": "1", "subject": "x", "activeForm": "X", "status": "completed"})
            with mock.patch.object(sl, "probe_todo_from_transcript") as tr:
                result = sl.probe_current_todo("/some/transcript.jsonl", s, cd)
                self.assertEqual(result, (None, None))
                tr.assert_not_called()

    def test_reads_todos_dir_when_no_tasks(self):
        with tempfile.TemporaryDirectory() as cd:
            s = "sess3"
            self._write(os.path.join(cd, "todos", f"{s}-agent-abc.json"),
                        [{"status": "in_progress", "activeForm": "Todo active", "content": "c"}])
            self.assertEqual(sl.probe_current_todo("", s, cd), ("in_progress", "Todo active"))

    def test_falls_back_to_transcript(self):
        with tempfile.TemporaryDirectory() as cd:
            tp = os.path.join(cd, "t.jsonl")
            with open(tp, "w") as f:
                f.write(json.dumps({"message": {"content": [
                    {"type": "tool_use", "name": "TaskCreate",
                     "input": {"subject": "A", "activeForm": "Doing A"}}]}}) + "\n")
                f.write(json.dumps({"message": {"content": [
                    {"type": "tool_use", "name": "TaskUpdate",
                     "input": {"taskId": 1, "status": "in_progress"}}]}}) + "\n")
            # session has no materialized dirs under cd -> transcript replay
            self.assertEqual(sl.probe_current_todo(tp, "nosession", cd), ("in_progress", "Doing A"))

    def test_tasks_dir_preferred_over_transcript(self):
        with tempfile.TemporaryDirectory() as cd:
            s = "sess4"
            self._write(os.path.join(cd, "tasks", s, "1.json"),
                        {"id": "1", "subject": "win", "activeForm": "From tasks dir",
                         "status": "in_progress"})
            with mock.patch.object(sl, "probe_todo_from_transcript") as tr:
                self.assertEqual(
                    sl.probe_current_todo("/x.jsonl", s, cd), ("in_progress", "From tasks dir"))
                tr.assert_not_called()

    def test_safe_session_rejects_traversal(self):
        self.assertTrue(sl.util_safe_session("b6de6c0c-9229-407f-9d33-b157970f2e9f"))
        for bad in ("../evil", "a/b", "..", r"a\b", ""):
            self.assertFalse(sl.util_safe_session(bad), bad)

    def test_traversal_session_does_not_escape_dir(self):
        # A crafted session id with ../ must not read .json outside the tasks dir;
        # the materialized tiers bail and we fall through to the transcript.
        with tempfile.TemporaryDirectory() as cd:
            self._write(os.path.join(cd, "secret.json"),
                        [{"status": "in_progress", "activeForm": "LEAK"}])
            with mock.patch.object(sl, "probe_todo_from_transcript",
                                   return_value=(None, None)) as tr:
                self.assertEqual(sl.probe_current_todo("", "../", cd), (None, None))
                tr.assert_called_once()   # fell through, did not traverse

    def test_no_session_goes_straight_to_transcript(self):
        patch_target = "probe_todo_from_transcript"
        with mock.patch.object(sl, patch_target, return_value=("pending", "P")) as tr:
            self.assertEqual(sl.probe_current_todo("/x.jsonl"), ("pending", "P"))
            tr.assert_called_once()


class TestEndToEnd(unittest.TestCase):
    def test_build_and_render(self):
        raw = {
            "model": {"display_name": "Opus 4.8", "id": "claude-opus-4-8"},
            "effort": {"level": "high"},
            "workspace": {"current_dir": os.getcwd()},
            "context_window": {"used_percentage": 47, "context_window_size": 1_000_000},
            "cost": {"total_lines_added": 12, "total_lines_removed": 3,
                     "total_duration_ms": 65000, "total_api_duration_ms": 4200},
        }
        env = {"STATUSLINE_COLS": "200", "STATUSLINE_LINES": "50", "HOME": "/home/u"}
        cfg = sl.cfg_default_config()
        data, _cols, _lines = _ctx_from_env(raw, env, cfg)
        out = sl.core_render(data)
        self.assertEqual(len(out), 3)
        self.assertIn("Opus 4.8", strip(out[1]))
        self.assertIn("47%", strip(out[2]))


class TestLazyCompute(unittest.TestCase):
    """A disabled segment skips its probe across the WHOLE render; an enabled one
    runs it exactly once, inside its measured build (FR-R.2 option A). Probes no
    longer run in build_data — they are deferred to the segment that reads them,
    so these drive the full build_data + render path."""
    RAW = {"workspace": {"current_dir": "."}, "transcript_path": ""}
    EFFORT_RAW = {"workspace": {"current_dir": "."}, "transcript_path": "",
                  "effort": {"level": "high"}}
    ENV = {"STATUSLINE_COLS": "200", "STATUSLINE_LINES": "50", "HOME": "/home/u"}

    def _build_and_render(self, segs, raw=None, cfg=None):
        if cfg is None:
            cfg = sl.cfg_default_config()
        cfg.segments.clear()                       # cfg is a namedtuple; mutate the dict
        cfg.segments.update(dict.fromkeys(sl.SEGMENTS, False))
        cfg.segments.update(segs)
        theme = sl.core_build_theme(cfg)
        # build_data is segment-agnostic; cfg.segments gates probes via render().
        data, _cols, _lines = _ctx_from_env(raw or self.RAW, self.ENV, cfg)
        sl.core_render(data, cfg, theme)
        return data

    def test_disabled_segments_skip_their_probes(self):
        with mock.patch.object(sl, "probe_git_snapshot") as gi,\
             mock.patch.object(sl, "probe_current_todo") as ct,\
             mock.patch.object(sl, "probe_rss_bytes") as rss,\
             mock.patch.object(sl, "probe_effort_setting_is_auto") as ea:
            self._build_and_render(dict.fromkeys(sl.SEGMENTS, False))
            gi.assert_not_called()
            ct.assert_not_called()
            rss.assert_not_called()
            ea.assert_not_called()

    def test_enabled_segments_run_their_probes(self):
        segs = {"branch": True, "todo": True, "memory": True, "effort": True}
        with mock.patch.object(sl, "probe_git_snapshot",
                               return_value=sl.GitSnapshot(True, "m", "clean", False, "")) as gi,\
             mock.patch.object(sl, "probe_current_todo", return_value=(None, None)) as ct,\
             mock.patch.object(sl, "probe_rss_bytes", return_value=1) as rss,\
             mock.patch.object(sl, "probe_effort_setting_is_auto", return_value=True) as ea:
            self._build_and_render(segs, raw=self.EFFORT_RAW)
            gi.assert_called_once()      # branch built -> git probe runs
            ct.assert_called_once()      # todo built  -> transcript parse runs
            rss.assert_called_once()     # memory built
            ea.assert_called_once()      # effort built (level present -> auto checked)

    def test_dirty_alone_still_triggers_git(self):
        # branch + dirty share one probe_git_snapshot call; either flag must trigger it.
        with mock.patch.object(sl, "probe_git_snapshot",
                               return_value=sl.GitSnapshot(True, "", "modified", False, "")) as gi:
            self._build_and_render({"dirty": True})
            gi.assert_called_once()

    def test_none_segments_computes_everything(self):
        # build_data is segment-agnostic: it never gates by flag. Rendering an
        # all-on config fires the probes (here the todo parse).
        cfg = sl.cfg_default_config()
        theme = sl.core_build_theme(cfg)
        with mock.patch.object(sl, "probe_current_todo", return_value=(None, None)) as ct,\
             mock.patch.object(sl, "probe_git_snapshot",
                               return_value=sl.GitSnapshot(True, "m", "clean", False, "")):
            data, _cols, _lines = _ctx_from_env(self.RAW, self.ENV, cfg)
            sl.core_render(data, cfg, theme)
            ct.assert_called_once()

    def test_git_ttl_threaded_to_snapshot(self):
        # The resolved [git] cache_ttl flows through build_data into probe_git_snapshot
        # via the Config object (D8 — consumers read cache_ttl off the object).
        cfg = sl.cfg_default_config()._replace(git={"cache_ttl": 42})
        with mock.patch.object(sl, "probe_git_snapshot",
                               return_value=sl.GitSnapshot(True, "m", "clean", False, "")) as gs:
            self._build_and_render({"worktree": True}, cfg=cfg)
            # probe_git_snapshot receives the config; the ttl is read off it.
            args = gs.call_args
            passed_cfg = args.args[1] if args.args[1:] else args.kwargs.get("config")
            self.assertEqual((passed_cfg.git or {}).get("cache_ttl"), 42)

    def test_git_probe_fires_for_any_git_segment_agnostically(self):
        # build_data is segment-agnostic: probe_git_snapshot runs once whenever ANY of
        # branch/dirty/worktree is built — in full (no per-segment untracked/
        # want_worktree flags threaded in) — and not at all when none are.
        for branch_on, dirty_on, wt_on in (
            (True, False, True), (True, False, False),
            (False, True, False), (False, False, True),
            (True, True, True),
        ):
            with mock.patch.object(
                    sl, "probe_git_snapshot",
                    return_value=sl.GitSnapshot(True, "m", "clean", False, "")) as gi:
                self._build_and_render(
                    {"branch": branch_on, "dirty": dirty_on, "worktree": wt_on})
                gi.assert_called_once()
                # No segment-derived flags leak into the call (agnostic probe).
                self.assertNotIn("untracked", gi.call_args.kwargs)
                self.assertNotIn("want_worktree", gi.call_args.kwargs)

        with mock.patch.object(
                sl, "probe_git_snapshot",
                return_value=sl.GitSnapshot(True, "m", "clean", False, "")) as gi:
            self._build_and_render({"branch": False, "dirty": False, "worktree": False})
            gi.assert_not_called()                  # no git segment built -> no probe


class TestBlueFix(unittest.TestCase):
    def test_blue_is_lightened_256color(self):
        # 1;34 bold-ANSI-blue reads purple on many terminals; use lightened 256-color blue.
        self.assertEqual(THEME.c("BLUE"), "\033[38;5;39m")

    def test_lightblue_defined_for_chat_ramp(self):
        self.assertEqual(THEME.c("LIGHTBLUE"), "\033[38;5;75m")

    def test_path_emits_true_blue_not_bold_ansi(self):
        out = sl.seg_path(_data(), 80, THEME)
        self.assertIn("38;5;39", out)
        self.assertNotIn("\033[1;34m", out)


class TestChatSizeRamp(unittest.TestCase):
    KB = 1024
    MB = 1024 * 1024

    def test_ramp_bands(self):
        KB, MB = self.KB, self.MB
        cases = [
            (400 * KB, THEME.c("WHITE")), (512 * KB, THEME.c("CYAN")),
            (900 * KB, THEME.c("CYAN")),
            (1 * MB, THEME.c("LIGHTBLUE")), (1 * MB + 1, THEME.c("LIGHTBLUE")),
            (2 * MB, THEME.c("GREEN")), (3 * MB, THEME.c("YELLOW")), (4 * MB, THEME.c("ORANGE")),
            (5 * MB, THEME.c("RED+bold")), (5 * MB + 1, THEME.c("RED+bold")),
            (9 * MB, THEME.c("RED+bold")),
            (10 * MB, THEME.c("MAGENTA")), (20 * MB, THEME.c("MAGENTA")),
        ]
        for n, want in cases:
            self.assertEqual(sl.util_pick_color(n, THEME.ramps["chat_size"]), want, n)

    def test_seg_chat_size_colors_the_size(self):
        out = sl.seg_chat_size(_data(chat_bytes=6 * self.MB), 40, THEME)
        self.assertIn("💾", out)
        self.assertIn(THEME.c("RED+bold"), out)       # 6 MB -> red band

    def test_seg_chat_size_none_when_no_bytes(self):
        self.assertIsNone(sl.seg_chat_size(_data(chat_bytes=None), 40, THEME))


class TestEffortAutoSetting(unittest.TestCase):
    def test_auto_appends_bracket_when_room(self):
        out = strip(sl.seg_effort(_data(effort="high", effort_auto=True), 40, THEME))
        self.assertIn("high", out)
        self.assertIn("[auto]", out)

    def test_resolved_level_keeps_its_color_in_auto(self):
        out = sl.seg_effort(_data(effort="high", effort_auto=True), 40, THEME)
        self.assertIn(f'{THEME.c("YELLOW")}high', out)   # level keeps its fixed color

    def test_auto_compacts_to_asterisk_when_tight(self):
        out = strip(sl.seg_effort(_data(effort="medium", effort_auto=True), 18, THEME))
        self.assertIn("medium*", out)
        self.assertNotIn("[auto]", out)

    def test_non_auto_has_no_annotation(self):
        out = strip(sl.seg_effort(_data(effort="high", effort_auto=False), 40, THEME))
        self.assertIn("high", out)
        self.assertNotIn("[auto]", out)
        self.assertNotIn("*", out)


class TestEffortSettingAuto(unittest.TestCase):
    def _dirs(self):
        proj = tempfile.mkdtemp()
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, proj, ignore_errors=True)
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        return proj, home

    def _write(self, root, name, obj):
        path = os.path.join(root, ".claude", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(obj, f)

    def test_absent_everywhere_is_auto(self):
        proj, home = self._dirs()
        self.assertTrue(sl.probe_effort_setting_is_auto(proj, home))

    def test_explicit_user_level_is_not_auto(self):
        proj, home = self._dirs()
        self._write(home, "settings.json", {"effortLevel": "high"})
        self.assertFalse(sl.probe_effort_setting_is_auto(proj, home))

    def test_literal_auto_value_is_auto(self):
        proj, home = self._dirs()
        self._write(home, "settings.json", {"effortLevel": "auto"})
        self.assertTrue(sl.probe_effort_setting_is_auto(proj, home))

    def test_project_setting_wins_over_user(self):
        proj, home = self._dirs()
        self._write(home, "settings.json", {"effortLevel": "auto"})
        self._write(proj, "settings.json", {"effortLevel": "high"})
        self.assertFalse(sl.probe_effort_setting_is_auto(proj, home))

    def test_keyless_file_falls_through_to_next(self):
        proj, home = self._dirs()
        self._write(proj, "settings.local.json", {"model": "opus"})  # present, no effortLevel
        self._write(home, "settings.json", {"effortLevel": "max"})
        self.assertFalse(sl.probe_effort_setting_is_auto(proj, home))

    def test_local_json_wins_over_project_and_user(self):
        proj, home = self._dirs()
        self._write(proj, "settings.local.json", {"effortLevel": "high"})
        self._write(proj, "settings.json", {"effortLevel": "auto"})
        self._write(home, "settings.json", {"effortLevel": "auto"})
        self.assertFalse(sl.probe_effort_setting_is_auto(proj, home))


class TestResolveEffort(unittest.TestCase):
    def test_level_auto_normalized_away(self):
        # "auto" is a *setting*, never a resolved level — it must not survive here.
        self.assertEqual(sl.cfg_resolve_effort({"effort": {"level": "auto"}}, {}), "")

    def test_env_auto_normalized_away(self):
        self.assertEqual(sl.cfg_resolve_effort({}, {"CLAUDE_EFFORT": "auto"}), "")

    def test_case_normalized(self):
        self.assertEqual(sl.cfg_resolve_effort({"effort": {"level": "HIGH"}}, {}), "high")

    def test_level_wins_over_env(self):
        self.assertEqual(
            sl.cfg_resolve_effort({"effort": {"level": "high"}}, {"CLAUDE_EFFORT": "auto"}),
            "high")

    def test_missing_is_empty(self):
        self.assertEqual(sl.cfg_resolve_effort({}, {}), "")


class TestProcRssLinux(unittest.TestCase):
    def test_returns_none_when_no_claude_ancestor(self):
        # the wezterm bug: walk finds no `claude`, must return None (not a stray RSS)
        comm = {10: "zsh", 11: "wezterm-gui", 1: "systemd"}
        ppid = {10: 11, 11: 1, 1: 0}
        with mock.patch.object(sl.os.path, "isdir", return_value=True),\
             mock.patch.object(sl.os, "getppid", return_value=10),\
             mock.patch.object(sl, "probe_comm_via_proc", side_effect=comm.get),\
             mock.patch.object(sl, "probe_ppid_via_proc", side_effect=ppid.get),\
             mock.patch.object(sl, "probe_rss_kb_via_proc", side_effect=lambda p: 5000):
            self.assertIsNone(sl.probe_rss_bytes())

    def test_returns_rss_when_claude_found(self):
        comm = {10: "zsh", 11: "claude", 1: "systemd"}
        ppid = {10: 11, 11: 1, 1: 0}
        with mock.patch.object(sl.os.path, "isdir", return_value=True),\
             mock.patch.object(sl.os, "getppid", return_value=10),\
             mock.patch.object(sl, "probe_comm_via_proc", side_effect=comm.get),\
             mock.patch.object(sl, "probe_ppid_via_proc", side_effect=ppid.get),\
             mock.patch.object(sl, "probe_rss_kb_via_proc",
                               side_effect=lambda p: 204800 if p == 11 else 5000):
            self.assertEqual(sl.probe_rss_bytes(), 204800 * 1024)


class TestProcRssMacOS(unittest.TestCase):
    def test_ps_fallback_when_no_proc(self):
        comm = {10: "login", 11: "claude", 1: "launchd"}
        ppid = {10: 11, 11: 1, 1: 0}
        rss = {11: 307200, 10: 100}
        with mock.patch.object(sl.os.path, "isdir", return_value=False),\
             mock.patch.object(sl.os, "getppid", return_value=10),\
             mock.patch.object(sl, "probe_comm_via_ps", side_effect=comm.get),\
             mock.patch.object(sl, "probe_ppid_via_ps", side_effect=ppid.get),\
             mock.patch.object(sl, "probe_rss_kb_via_ps", side_effect=rss.get):
            self.assertEqual(sl.probe_rss_bytes(), 307200 * 1024)

    def test_ps_field_parses_one_value(self):
        class R:
            stdout = "  12345\n"
        with mock.patch.object(sl.subprocess, "run", return_value=R()):
            self.assertEqual(sl.probe_ps_field(99, "rss"), "12345")


class TestTputFallback(unittest.TestCase):
    def test_tput_used_when_stty_yields_nothing(self):
        def fake_run(cmd, **kw):
            class R:
                stdout = ""
            r = R()
            if cmd[:1] == ["stty"]:
                r.stdout = ""               # stty size unavailable
            elif cmd == ["tput", "cols"]:
                r.stdout = "123\n"
            elif cmd == ["tput", "lines"]:
                r.stdout = "44\n"
            return r
        with mock.patch.object(sl.subprocess, "run", side_effect=fake_run),\
             mock.patch("builtins.open", mock.mock_open(read_data="")):
            cols, lines, assumed = sl.probe_terminal_size({})
        self.assertEqual((cols, lines), (123, 44))
        self.assertFalse(assumed)


class TestConfigScaffold(unittest.TestCase):
    def test_default_config_matches_globals(self):
        cfg = sl.cfg_default_config()
        self.assertEqual(cfg.segments, dict(sl.SEGMENTS))
        self.assertEqual(cfg.layout, list(sl.LAYOUT))
        self.assertEqual(cfg.palette, {})

    def test_default_config_is_a_snapshot(self):
        cfg = sl.cfg_default_config()
        cfg.segments["clock"] = not cfg.segments["clock"]
        self.assertNotEqual(cfg.segments["clock"], sl.SEGMENTS["clock"])  # snapshot, not alias


class TestEnvBool(unittest.TestCase):
    def test_true_tokens(self):
        for v in ("1", "true", "T", "y", "Yes", "on", "ON"):
            self.assertIs(sl.cfg_env_bool({"X": v}, "X"), True, v)

    def test_false_tokens(self):
        for v in ("0", "false", "F", "n", "No", "off", "OFF"):
            self.assertIs(sl.cfg_env_bool({"X": v}, "X"), False, v)

    def test_unset_is_none(self):
        self.assertIsNone(sl.cfg_env_bool({}, "X"))

    def test_unrecognized_is_none(self):
        self.assertIsNone(sl.cfg_env_bool({"X": "maybe"}, "X"))
        self.assertIsNone(sl.cfg_env_bool({"X": ""}, "X"))


class TestConfigPathAndLoad(unittest.TestCase):
    def test_explicit_path_wins(self):
        env = {"CC_AI_KIT_CONFIG": "/tmp/x.toml", "HOME": "/home/u"}
        self.assertEqual(sl.cfg_config_path(env), "/tmp/x.toml")

    def test_xdg_path(self):
        env = {"XDG_CONFIG_HOME": "/cfg", "HOME": "/home/u"}
        self.assertEqual(sl.cfg_config_path(env), "/cfg/ai-kit/statusline.toml")

    def test_home_default_path(self):
        env = {"HOME": "/home/u"}
        self.assertEqual(sl.cfg_config_path(env), "/home/u/.config/ai-kit/statusline.toml")

    def test_missing_file_is_empty(self):
        self.assertEqual(sl.cfg_load_toml("/no/such/file.toml"), {})

    def test_malformed_file_is_empty_no_crash(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("this is = = not toml")
            path = f.name
        try:
            self.assertEqual(sl.cfg_load_toml(path), {})
        finally:
            os.unlink(path)

    def test_valid_file_parses(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("[segments]\ncost = true\n")
            path = f.name
        try:
            self.assertEqual(sl.cfg_load_toml(path), {"segments": {"cost": True}})
        finally:
            os.unlink(path)


class TestResolveSegments(unittest.TestCase):
    def _write(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(body)
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_defaults_when_no_file_no_env(self):
        env = {"CC_AI_KIT_CONFIG": "/no/such.toml", "HOME": "/h"}
        cfg = sl.cfg_load_config(env)
        self.assertEqual(cfg.segments, dict(sl.SEGMENTS))
        self.assertEqual(cfg.layout, list(sl.LAYOUT))
        self.assertEqual(cfg.palette, {})

    def test_file_overrides_default(self):
        path = self._write("[segments]\ncost = true\nmemory = false\n")
        cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertTrue(cfg.segments["cost"])      # default False -> True
        self.assertFalse(cfg.segments["memory"])   # default True  -> False
        self.assertTrue(cfg.segments["clock"])     # untouched default

    def test_env_overrides_file(self):
        path = self._write("[segments]\ncost = true\n")
        env = {"CC_AI_KIT_CONFIG": path, "HOME": "/h", "CC_AI_KIT_SEGMENT_COST": "0"}
        cfg = sl.cfg_load_config(env)
        self.assertFalse(cfg.segments["cost"])     # env beats file

    def test_unknown_segment_key_ignored(self):
        path = self._write("[segments]\nbogus = true\n")
        cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertNotIn("bogus", cfg.segments)

    def test_wrong_type_value_ignored(self):
        # `cost = "true"` (string, not bool) is a known key but a bad value:
        # it must be dropped (keeping the default), not silently coerced.
        path = self._write('[segments]\ncost = "true"\n')
        cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.segments["cost"], sl.SEGMENTS["cost"])  # default kept


class TestGitConfig(unittest.TestCase):
    def _write(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(body)
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_cache_ttl_default_5(self):
        # Default [git] config carries cache_ttl=5 and nothing else.
        cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": "/no/such.toml", "HOME": "/h"})
        self.assertEqual(cfg.git, {"cache_ttl": 5})

    def test_cache_ttl_from_toml(self):
        path = self._write("[git]\ncache_ttl = 20\n")
        cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.git["cache_ttl"], 20)

    def test_cache_ttl_env_overrides_toml(self):
        # Precedence: default 5 < TOML [git] cache_ttl < env CC_AI_KIT_GIT_TTL.
        path = self._write("[git]\ncache_ttl = 20\n")
        env = {"CC_AI_KIT_CONFIG": path, "HOME": "/h", "CC_AI_KIT_GIT_TTL": "99"}
        self.assertEqual(sl.cfg_load_config(env).git["cache_ttl"], 99)

    def test_cache_ttl_env_over_default(self):
        env = {"CC_AI_KIT_CONFIG": "/no/such.toml", "HOME": "/h",
               "CC_AI_KIT_GIT_TTL": "0"}
        self.assertEqual(sl.cfg_load_config(env).git["cache_ttl"], 0)

    def test_cache_ttl_bad_toml_type_ignored(self):
        path = self._write('[git]\ncache_ttl = "soon"\n')   # string, not int
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.git["cache_ttl"], 5)            # default kept
        self.assertIn("cache_ttl", buf.getvalue())           # and warned

    def test_legacy_worktree_key_tolerated_with_cache_ttl(self):
        # Legacy `[git] worktree` is silently accepted (no warning), no effect;
        # cache_ttl alongside it still resolves.
        for val in ("true", "false", '"true"'):
            path = self._write(f"[git]\nworktree = {val}\ncache_ttl = 12\n")
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
            self.assertEqual(cfg.git, {"cache_ttl": 12}, val)
            self.assertNotIn("worktree", buf.getvalue(), val)   # no warning

    def test_worktree_env_no_longer_read(self):
        # CC_AI_KIT_GIT_WORKTREE is retired — setting it does not affect cfg.git.
        env = {"CC_AI_KIT_CONFIG": "/no/such.toml", "HOME": "/h",
               "CC_AI_KIT_GIT_WORKTREE": "1"}
        self.assertEqual(sl.cfg_load_config(env).git, {"cache_ttl": 5})

    def test_unknown_git_key_warns(self):
        path = self._write("[git]\nbogus = true\n")
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertNotIn("bogus", cfg.git)             # bogus dropped
        self.assertIn("bogus", buf.getvalue())         # and warned

    def test_check_flags_unknown_and_bad_ttl_but_not_legacy_worktree(self):
        # `bogus` and a bad cache_ttl are flagged; legacy `worktree` is NOT.
        path = self._write('[git]\nbogus = true\nworktree = "x"\ncache_ttl = "nope"\n')
        errors = sl.validate_config_file(path, {"HOME": "/h"})
        self.assertTrue(any("bogus" in e for e in errors), errors)
        self.assertTrue(any("cache_ttl" in e for e in errors), errors)
        self.assertFalse(any("worktree" in e for e in errors), errors)


class TestWorktreeSegmentToggle(unittest.TestCase):
    """The worktree feature is now a segment toggle, ON by default."""

    def _write(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(body)
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_worktree_segment_on_by_default(self):
        self.assertIs(sl.SEGMENTS.get("worktree"), True)
        cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": "/no/such.toml", "HOME": "/h"})
        self.assertTrue(cfg.segments["worktree"])

    def test_worktree_segment_disable_via_toml(self):
        path = self._write("[segments]\nworktree = false\n")
        cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertFalse(cfg.segments["worktree"])

    def test_worktree_segment_disable_via_env(self):
        env = {"CC_AI_KIT_CONFIG": "/no/such.toml", "HOME": "/h",
               "CC_AI_KIT_SEGMENT_WORKTREE": "0"}
        self.assertFalse(sl.cfg_load_config(env).segments["worktree"])


class TestRenderWithConfig(unittest.TestCase):
    def test_pack_line_honors_cfg_segments(self):
        cfg = sl.Config(segments={**sl.SEGMENTS, "clock": False},
                        layout=list(sl.LAYOUT), palette={}, ramps={})
        out = strip(sl.core_pack(["model", "clock"], _data(), 200, cfg))
        self.assertNotIn("⏰", out)
        self.assertIn("Opus 4.8", out)

    def test_render_honors_cfg_layout(self):
        cfg = sl.Config(segments=dict(sl.SEGMENTS),
                        layout=[sl.Line(0, ["model"])], palette={}, ramps={})
        lines = sl.core_render(_data(), cfg)
        self.assertEqual(len(lines), 1)
        self.assertIn("Opus 4.8", strip(lines[0]))

    def test_render_default_cfg_unchanged(self):
        # No cfg arg -> same as today (three rows when tall+wide).
        self.assertEqual(len(sl.core_render(_data())), 3)


class TestMainUsesConfig(unittest.TestCase):
    def _run_main(self, raw, env):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(raw))),\
             mock.patch.object(sys, "argv", ["status-line.py"]),\
             mock.patch.dict(os.environ, env, clear=True),\
             redirect_stdout(buf):
            sl.main()
        return buf.getvalue()

    def test_segment_hidden_via_env(self):
        raw = {"workspace": {"current_dir": "/tmp"}, "model": {"display_name": "Opus"},
               "context_window": {"used_percentage": 10}}
        # PATH is preserved: build_data shells out to `git` (unguarded), and
        # clear=True would otherwise strip it and crash main().
        env = {"HOME": "/tmp", "STATUSLINE_COLS": "200", "STATUSLINE_LINES": "50",
               "PATH": os.environ.get("PATH", ""),
               "CC_AI_KIT_SEGMENT_CLOCK": "0", "CC_AI_KIT_CONFIG": "/no/such.toml"}
        out = strip(self._run_main(raw, env))
        self.assertNotIn("⏰", out)
        self.assertIn("Opus", out)


class TestResolveLayout(unittest.TestCase):
    def _write(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(body)
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_no_line_keeps_default_layout(self):
        cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": "/no/such.toml", "HOME": "/h"})
        self.assertEqual(cfg.layout, list(sl.LAYOUT))

    def test_line_replaces_layout(self):
        path = self._write(
            '[[line]]\nmin_rows = 0\nsegments = ["path", "model"]\n'
            '[[line]]\nmin_rows = 25\nsegments = ["context"]\n')
        cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.layout,
                         [sl.Line(0, ["path", "model"]), sl.Line(25, ["context"])])

    def test_line_missing_min_rows_defaults_zero(self):
        path = self._write('[[line]]\nsegments = ["path"]\n')
        cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.layout, [sl.Line(0, ["path"])])


class TestPaletteFromConfig(unittest.TestCase):
    def _write(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(body)
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_palette_parsed_into_config(self):
        path = self._write('[palette]\nBLUE = "1;34"\n')
        cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.palette, {"BLUE": "1;34"})

    def test_unknown_palette_key_dropped(self):
        path = self._write('[palette]\nNOTACOLOR = "1;34"\n')
        cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.palette, {})

    def test_main_applies_palette(self):
        import io
        from contextlib import redirect_stdout
        path = self._write('[palette]\nBLUE = "1;34"\n')
        raw = {"workspace": {"current_dir": "/tmp"}, "model": {"display_name": "Opus"},
               "context_window": {"used_percentage": 10}}
        env = {"HOME": "/tmp", "STATUSLINE_COLS": "200", "STATUSLINE_LINES": "50",
               "PATH": os.environ.get("PATH", ""),  # keep PATH so git in build_data resolves
               "CC_AI_KIT_CONFIG": path}
        buf = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(raw))),\
             mock.patch.object(sys, "argv", ["status-line.py"]),\
             mock.patch.dict(os.environ, env, clear=True), redirect_stdout(buf):
            sl.main()
        # path segment is BLUE; overridden blue (1;34) must appear in the raw output.
        self.assertIn("\033[1;34m", buf.getvalue())


class TestSampleRecipe(unittest.TestCase):
    SAMPLE = os.path.join(_HERE, "..", "tools", "statusline.toml.sample")

    def _uncomment(self):
        # Data lines are "# " prefixed; prose is "## " prefixed. Reconstruct the
        # intended config by taking the single-hash data lines, stripping "# ".
        with open(self.SAMPLE) as f:
            lines = f.read().splitlines()
        return "\n".join(ln[2:] for ln in lines if ln.startswith("# "))

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(self.SAMPLE))

    def test_as_shipped_is_all_commented_noop(self):
        # No active (uncommented) TOML keys: every non-blank line is a comment.
        with open(self.SAMPLE) as f:
            for ln in f:
                s = ln.strip()
                if s:
                    self.assertTrue(s.startswith("#"), f"active line in sample: {ln!r}")

    def test_uncommented_matches_internal_defaults(self):
        parsed = tomllib.loads(self._uncomment())
        self.assertEqual(parsed.get("version"), 1)
        self.assertEqual(parsed.get("segments"), dict(sl.SEGMENTS))
        want = [{"min_rows": ln.min_rows, "segments": ln.segments} for ln in sl.LAYOUT]
        self.assertEqual(parsed.get("line"), want)
        # The [palette] block documents every overridable color with its real
        # default; assert it so the recipe can't silently drift from the code.
        self.assertEqual(parsed.get("palette"), dict(sl._PALETTE_DEFAULTS))
        # [ramp.*] blocks document the real default tables.
        want_ramps = {
            band: {str(thr): spec for thr, spec in pairs}
            for band, pairs in sl._RAMP_DEFAULTS.items()
        }
        self.assertEqual(parsed.get("ramp"), want_ramps)
        # [git] knobs document their real defaults too.
        self.assertEqual(parsed.get("git"), dict(sl._GIT_DEFAULTS))


class TestCLI(unittest.TestCase):
    def _write(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(body)
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_parse_args_defaults(self):
        ns = sl.parse_args([])
        self.assertFalse(ns.print_config)
        self.assertIs(ns.check, sl._NO_CHECK)

    def test_print_config_emits_resolved_json(self):
        cfg = sl.Config(segments={"path": True}, layout=[sl.Line(0, ["path"])],
                        palette={"BLUE": "1;34"}, ramps={})
        out = sl.cmd_print_config(cfg, {})
        parsed = json.loads(out)
        self.assertEqual(parsed["segments"], {"path": True})
        self.assertEqual(parsed["layout"], [{"min_rows": 0, "segments": ["path"]}])
        self.assertEqual(parsed["palette"], {"BLUE": "1;34"})

    def test_check_valid_returns_zero(self):
        path = self._write('[segments]\ncost = true\n')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 0)

    def test_check_unknown_segment_returns_one(self):
        path = self._write('[segments]\nbogus = true\n')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_bad_layout_ref_returns_one(self):
        path = self._write('[[line]]\nsegments = ["nope"]\n')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_malformed_returns_one(self):
        path = self._write('= = not toml')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_bad_palette_hex_returns_one(self):
        path = self._write('[palette]\nBLUE = "#zzz"\n')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_unknown_modifier_returns_one(self):
        path = self._write('[palette]\nRED = "31+blink"\n')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_bad_ramp_color_returns_one(self):
        path = self._write('[ramp.context]\n10 = "NOTACOLOR"\n')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_bad_ramp_threshold_returns_one(self):
        path = self._write('[ramp.context]\noops = "RED"\n')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_valid_palette_and_ramp_returns_zero(self):
        path = self._write('[palette]\nBLUE = "#3399ff"\n'
                           '[ramp.rate]\n50 = "GREEN"\ninf = "RED+bold"\n')
        self.assertEqual(sl.cmd_check(path, {"HOME": "/h"}), 0)


class TestParseColor(unittest.TestCase):
    PAL = {"RED": "31", "BLUE": "38;5;39", "ORANGE": "38;5;208"}

    def test_palette_name(self):
        self.assertEqual(sl.util_parse_color("RED", self.PAL), "\033[31m")
        self.assertEqual(sl.util_parse_color("BLUE", self.PAL), "\033[38;5;39m")

    def test_raw_sgr_passthrough(self):
        self.assertEqual(sl.util_parse_color("38;5;33"), "\033[38;5;33m")
        self.assertEqual(sl.util_parse_color("1;31"), "\033[1;31m")

    def test_hex_six(self):
        self.assertEqual(sl.util_parse_color("#3399ff"), "\033[38;2;51;153;255m")

    def test_hex_short_expands(self):
        self.assertEqual(sl.util_parse_color("#39f"), "\033[38;2;51;153;255m")

    def test_hex_alpha_stripped(self):
        self.assertEqual(sl.util_parse_color("#3399ffcc"), "\033[38;2;51;153;255m")

    def test_modifier_bold_on_name(self):
        self.assertEqual(sl.util_parse_color("RED+bold", self.PAL), "\033[1;31m")

    def test_modifier_on_hex(self):
        self.assertEqual(sl.util_parse_color("#3399ff+bold"), "\033[1;38;2;51;153;255m")

    def test_modifiers_canonical_order(self):
        # underline(4)+bold(1) -> ascending 1;4 regardless of input order
        self.assertEqual(sl.util_parse_color("RED+underline+bold", self.PAL), "\033[1;4;31m")

    def test_all_modifiers(self):
        self.assertEqual(sl.util_parse_color("RED+bold+dim+italic+underline", self.PAL),
                         "\033[1;2;3;4;31m")

    def test_unknown_name_is_none(self):
        self.assertIsNone(sl.util_parse_color("NOTACOLOR", self.PAL))

    def test_name_without_palette_is_none(self):
        self.assertIsNone(sl.util_parse_color("RED"))

    def test_unknown_modifier_is_none(self):
        self.assertIsNone(sl.util_parse_color("RED+blink", self.PAL))

    def test_bad_hex_is_none(self):
        self.assertIsNone(sl.util_parse_color("#zzz"))
        self.assertIsNone(sl.util_parse_color("#12345"))   # 5 nibbles, not 3/6/8

    def test_empty_is_none(self):
        self.assertIsNone(sl.util_parse_color(""))
        self.assertIsNone(sl.util_parse_color(None))


class TestParseThreshold(unittest.TestCase):
    def test_percent_int(self):
        self.assertEqual(sl.util_parse_threshold(10), 10)
        self.assertEqual(sl.util_parse_threshold("25"), 25)

    def test_inf(self):
        self.assertEqual(sl.util_parse_threshold("inf"), float("inf"))
        self.assertEqual(sl.util_parse_threshold(float("inf")), float("inf"))

    def test_byte_suffixes(self):
        self.assertEqual(sl.util_parse_threshold("512k"), 512 * 1024)
        self.assertEqual(sl.util_parse_threshold("5M"), 5 * 1024 * 1024)
        self.assertEqual(sl.util_parse_threshold("1G"), 1024 ** 3)

    def test_time_suffixes(self):
        # render_time thresholds resolve to nanoseconds
        self.assertEqual(sl.util_parse_threshold("100ns"), 100)
        self.assertEqual(sl.util_parse_threshold("500us"), 500_000)
        self.assertEqual(sl.util_parse_threshold("500µs"), 500_000)
        self.assertEqual(sl.util_parse_threshold("50ms"), 50_000_000)
        self.assertEqual(sl.util_parse_threshold("2s"), 2_000_000_000)

    def test_bad_key_raises(self):
        with self.assertRaises(ValueError):
            sl.util_parse_threshold("nonsense")
        with self.assertRaises(ValueError):
            sl.util_parse_threshold("5MB")   # only single-letter k/M/G suffix


class TestTheme(unittest.TestCase):
    def test_c_resolves_and_memoizes(self):
        t = sl.core_default_theme()
        first = t.c("RED")
        self.assertTrue(first.startswith("\033["))
        self.assertEqual(t.c("RED"), first)          # same object/value, cached
        self.assertIn("RED", t._cache)

    def test_c_modifier(self):
        t = sl.core_default_theme()
        self.assertEqual(t.c("RED+bold"), sl.util_parse_color("RED+bold", t.palette))

    def test_c_invalid_is_empty_string(self):
        t = sl.core_default_theme()
        self.assertEqual(t.c("NOTACOLOR"), "")        # never raises, no color


class TestBuildTheme(unittest.TestCase):
    def _cfg(self, palette=None, ramps=None):
        return sl.Config(segments=dict(sl.SEGMENTS), layout=list(sl.LAYOUT),
                         palette=palette or {}, ramps=ramps or {})

    def test_palette_merges_over_defaults(self):
        t = sl.core_build_theme(self._cfg(palette={"BLUE": "1;34"}))
        self.assertEqual(t.palette["BLUE"], "1;34")
        self.assertEqual(t.palette["RED"], sl._PALETTE_DEFAULTS["RED"])  # untouched

    def test_palette_hex_override_resolved_to_params(self):
        t = sl.core_build_theme(self._cfg(palette={"BLUE": "#3399ff"}))
        self.assertEqual(t.palette["BLUE"], "38;2;51;153;255")

    def test_bad_palette_value_keeps_default(self):
        t = sl.core_build_theme(self._cfg(palette={"BLUE": "#zzz"}))
        self.assertEqual(t.palette["BLUE"], sl._PALETTE_DEFAULTS["BLUE"])

    def test_ramp_replaced_whole(self):
        t = sl.core_build_theme(self._cfg(ramps={"rate": {"50": "GREEN", "inf": "RED"}}))
        self.assertEqual([c for _, c in t.ramps["rate"]],
                         [t.c("GREEN"), t.c("RED")])
        self.assertEqual([ceil for ceil, _ in t.ramps["rate"]], [50, float("inf")])

    def test_unspecified_ramp_keeps_default(self):
        t = sl.core_build_theme(self._cfg(ramps={"rate": {"inf": "RED"}}))
        self.assertEqual(len(t.ramps["context"]), len(sl._RAMP_DEFAULTS["context"]))

    def test_bad_band_color_falls_back_to_default_band(self):
        # context default band at ceil 10 is WHITE; a bad override color for that
        # band falls back to the default band's resolved color.
        bad = {"10": "NOPE", "inf": "RED"}
        t = sl.core_build_theme(self._cfg(ramps={"context": bad}))
        self.assertEqual(t.ramps["context"][0], (10, t.c("WHITE")))

    def test_bad_threshold_keeps_whole_default_ramp(self):
        t = sl.core_build_theme(self._cfg(ramps={"context": {"oops": "RED"}}))
        self.assertEqual(t.ramps["context"], sl.core_default_theme().ramps["context"])

    def test_effort_derives_from_palette(self):
        t = sl.core_default_theme()
        self.assertEqual(t.effort["low"][0], t.c("CYAN"))
        self.assertEqual(t.effort["max"][0], t.c("RED"))
        self.assertEqual(t.effort["low"][1].count("▁"), 1)
        # full ladder: every glyph present, no trailing grey segment for max
        self.assertTrue(t.effort["max"][1].startswith(t.c("RED")))


class TestRampFromConfig(unittest.TestCase):
    def _write(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(body)
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_ramp_parsed_into_config(self):
        path = self._write('[ramp.rate]\n50 = "GREEN"\ninf = "RED+bold"\n')
        cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.ramps, {"rate": {"50": "GREEN", "inf": "RED+bold"}})

    def test_unknown_ramp_dropped(self):
        path = self._write('[ramp.bogus]\n10 = "RED"\n')
        cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.ramps, {})

    def test_no_ramp_block_is_empty(self):
        cfg = sl.cfg_load_config({"CC_AI_KIT_CONFIG": "/no/such.toml", "HOME": "/h"})
        self.assertEqual(cfg.ramps, {})


class TestRendererRobustness(unittest.TestCase):
    def test_doctor_cmd_is_concrete(self):
        cmd = sl.core_doctor_cmd()
        # A copy-pasteable command, not a bare flag: ends with --doctor,
        # names a python executable, and references this script's path.
        self.assertTrue(cmd.endswith("--doctor"), cmd)
        self.assertIn("status-line.py", cmd)
        self.assertRegex(cmd, r"^\S*python\S*\s")

    def test_warn_is_an_sgr_code(self):
        self.assertTrue(sl._WARN.startswith("\033["))
        self.assertTrue(sl._WARN.endswith("m"))

    def test_safe_build_passes_through_ok_builder(self):
        def good(data, avail, theme):
            return "HELLO"
        ctx = _data()
        with mock.patch.dict(sl.BUILDERS, {"path": good}):
            out = sl.core_safe_build("path", ctx, 40, THEME)
        self.assertEqual(out, "HELLO")
        self.assertEqual(ctx.failed, set())

    def test_safe_build_records_and_marks_on_raise(self):
        def boom(data, avail, theme):
            raise RuntimeError("kaboom")
        ctx = _data()
        with mock.patch.dict(sl.BUILDERS, {"path": boom}):
            out = sl.core_safe_build("path", ctx, 40, THEME)
        self.assertIn("path", ctx.failed)
        self.assertIn("path", strip(out))          # name shown when width allows
        self.assertLessEqual(sl.util_visible_width(out), 40)

    def test_safe_build_bare_marker_when_no_room_for_name(self):
        def boom(data, avail, theme):
            raise RuntimeError("x")
        ctx = _data()
        with mock.patch.dict(sl.BUILDERS, {"context": boom}):
            out = sl.core_safe_build("context", ctx, 1, THEME)
        self.assertIn("context", ctx.failed)
        self.assertNotIn("context", strip(out))    # name dropped, icon kept

    def test_pack_line_survives_a_raising_pinned_builder(self):
        # "path" is PINNED — even when its builder raises, the line still renders
        # the other segments and records the failure.
        def boom(data, avail, theme):
            raise ValueError("nope")
        cfg = sl.cfg_default_config()
        def ok(data, avail, theme):
            return "CTX"
        ctx = _data()
        with mock.patch.dict(sl.BUILDERS, {"path": boom, "context": ok}):
            line = sl.core_pack(["path", "context"], ctx, 80, cfg, THEME)
        self.assertIn("path", ctx.failed)
        self.assertIn("CTX", strip(line))          # the healthy segment still shows

    def test_diagnostic_line_none_when_no_failures(self):
        self.assertIsNone(sl.core_diagnostic_line(set()))

    def test_diagnostic_line_lists_failures_and_doctor(self):
        line = strip(sl.core_diagnostic_line({"git", "context"}))
        self.assertIn("2 segments failed", line)
        self.assertIn("context, git", line)         # sorted
        self.assertIn("--doctor", line)

    def test_render_appends_diagnostic_on_builder_crash(self):
        def boom(data, avail, theme):
            raise RuntimeError("x")
        cfg = sl.cfg_default_config()
        layout = [sl.Line(0, ["path"])]
        cfg = cfg._replace(layout=layout)
        with mock.patch.dict(sl.BUILDERS, {"path": boom}):
            out = sl.core_render(_data(cols=80, lines=40), cfg, THEME)
        self.assertTrue(any("--doctor" in strip(l) for l in out))
        self.assertTrue(any("path" in strip(l) for l in out))

    def test_render_no_diagnostic_when_healthy(self):
        cfg = sl.cfg_default_config()
        out = sl.core_render(_data(cols=80, lines=40), cfg, THEME)
        self.assertFalse(any("--doctor" in strip(l) for l in out))

    def test_safe_render_returns_diagnostic_on_catastrophic_failure(self):
        cfg = sl.cfg_default_config()
        theme = THEME
        with mock.patch.object(sl, "core_build_context", side_effect=RuntimeError("boom")):
            out = sl.safe_render({}, os.environ, cfg, theme, 0)
        self.assertEqual(len(out), 1)
        self.assertIn("status-line error", strip(out[0]))
        self.assertIn("--doctor", strip(out[0]))

    def test_safe_render_normal_path(self):
        cfg = sl.cfg_default_config()
        out = sl.safe_render({}, os.environ, cfg, THEME, 0)
        self.assertIsInstance(out, list)
        self.assertFalse(any("status-line error" in strip(l) for l in out))

    # A fresh /clear session sends context_window/cost PRESENT but with null inner
    # fields (no tokens/cost accrued yet). dict.get(k, default) returns None for a
    # present-but-null key, so int()/math on it raised inside build_data and the
    # whole bar collapsed to "status-line error". Coalesce null -> 0 instead.
    _NEW_SESSION_RAW = {
        "model": {"display_name": "Opus", "id": "claude-opus-4-8"},
        "workspace": {"current_dir": "."},
        "transcript_path": "",
        "context_window": {"used_percentage": None, "context_window_size": None},
        "cost": {"total_lines_added": None, "total_lines_removed": None,
                 "total_cost_usd": None, "total_duration_ms": None,
                 "total_api_duration_ms": None},
    }

    def test_build_data_tolerates_present_but_null_fields(self):
        data, _cols, _lines = _ctx_from_env(
            dict(self._NEW_SESSION_RAW), os.environ, sl.cfg_default_config())
        self.assertEqual(data.context_pct, 0)
        self.assertEqual(data.context_max, 0)
        self.assertEqual(data.added, 0)
        self.assertEqual(data.removed, 0)
        self.assertEqual(data.cost, 0)
        self.assertEqual(data.total_ms, 0)
        self.assertEqual(data.api_ms, 0)

    def test_render_new_session_no_error_no_warn(self):
        cfg = sl.cfg_default_config()
        out = sl.safe_render(dict(self._NEW_SESSION_RAW), os.environ, cfg, THEME, 0)
        text = "\n".join(strip(l) for l in out)
        self.assertNotIn("status-line error", text)
        self.assertNotIn("⚠", text)        # no per-segment crashes either
        self.assertTrue(text.strip())       # and the bar is not blank


class TestRenderDataLazy(unittest.TestCase):
    """FR-R.2 (option A): expensive probes run inside the measured build of the
    segment that reads them, not eagerly in build_data — so the cost is captured
    by core_safe_build's timing and the shared probe still runs at most once."""

    def test_git_probe_deferred_to_render_and_runs_once(self):
        snap = sl.GitSnapshot(True, "main", "modified", False, "")
        raw = {"workspace": {"current_dir": "/repo"}, "session_id": "s"}
        cfg = sl.cfg_default_config()
        theme = sl.core_build_theme(cfg)
        with mock.patch.object(sl, "probe_git_snapshot", return_value=snap) as gs:
            data, _cols, _lines = _ctx_from_env(raw, {"HOME": "/h"}, cfg)
            self.assertEqual(gs.call_count, 0, "git probe must NOT run during build_data")
            sl.core_render(data, cfg, theme)
            self.assertEqual(gs.call_count, 1, "git probe runs exactly once during render")

    def test_disabled_git_segments_skip_the_probe(self):
        raw = {"workspace": {"current_dir": "/repo"}}
        cfg = sl.cfg_default_config()
        cfg.segments["branch"] = False
        cfg.segments["dirty"] = False
        cfg.segments["worktree"] = False
        theme = sl.core_build_theme(cfg)
        with mock.patch.object(sl, "probe_git_snapshot") as gs:
            data, _cols, _lines = _ctx_from_env(raw, {"HOME": "/h"}, cfg)
            sl.core_render(data, cfg, theme)
            self.assertEqual(gs.call_count, 0, "no git segment enabled => no git probe")


class TestSlowestTruthful(unittest.TestCase):
    """FR-R.2 acceptance: `slowest` names a real contributor whose cost is the
    same order of magnitude as the render — ms-scale, not the µs of a cache hit."""

    def test_slowest_captures_probe_cost_not_microseconds(self):
        raw = {"workspace": {"current_dir": "/repo"}, "session_id": "s"}
        cfg = sl.cfg_default_config()
        theme = sl.core_build_theme(cfg)

        def slow_git(*_a, **_k):                 # a 20ms git status
            time.sleep(0.02)
            return sl.GitSnapshot(True, "main", "modified", False, "")

        with mock.patch.object(sl, "probe_git_snapshot", side_effect=slow_git):
            data, _cols, _lines = _ctx_from_env(raw, {"HOME": "/h"}, cfg)
            sl.core_render(data, cfg, theme)
        name, ns = data.slowest
        self.assertIn(name, ("branch", "dirty", "worktree"))  # a real git consumer
        self.assertGreater(ns, 1_000_000)                     # >1ms, not µs


class TestTwoPassLayout(unittest.TestCase):
    """FR-R.3: a measured pass times every non-meta segment, then assembly places
    render_time/slowest at their LAYOUT positions — so slowest no longer has to be
    last on its line and sits adjacent to render_time by default."""

    def _diag_line(self):
        raw = {"workspace": {"current_dir": "/repo"}, "session_id": "s",
               "cost": {"total_cost_usd": 0.5}}
        cfg = sl.cfg_default_config()
        theme = sl.core_build_theme(cfg)
        with mock.patch.object(sl, "probe_git_snapshot",
                               return_value=sl.GitSnapshot(True, "main", "modified", False, "")):
            data, _c, _l = _ctx_from_env(raw, {"HOME": "/h"}, cfg,
                                         t_start=time.perf_counter_ns())
            out = sl.core_render(data, cfg, theme)
        return next(strip(l) for l in out if "⏱" in strip(l))

    def test_slowest_adjacent_to_render_time(self):
        diag = self._diag_line()
        i, j = diag.index("⏱"), diag.index("🐌")
        self.assertGreater(j, i)              # slowest comes after render_time
        self.assertNotIn("📊", diag[i:j])     # context not wedged between them

    def test_slowest_not_forced_last_in_layout(self):
        line = next(l for l in sl.LAYOUT if "slowest" in l.segments)
        self.assertNotEqual(line.segments[-1], "slowest")
        self.assertEqual(line.segments.index("slowest"),
                         line.segments.index("render_time") + 1)


class TestGoldenOutput(unittest.TestCase):
    """Snapshot guard for the measured-pass restructure (FR-R.1/2/3). Renders a
    set of representative inputs through build_data + render with every
    non-deterministic probe mocked, and compares to a committed expected.txt.
    t_start=None makes render_time self-omit and `slowest` is unset, so the
    snapshot captures the NON-meta segment output exactly — which is what the
    restructure must preserve. Regenerate intentionally with UPDATE_GOLDEN=1."""

    GOLDEN = os.path.join(os.path.dirname(__file__), "fixtures", "golden")
    ENV = {"HOME": "/home/dev"}

    @contextlib.contextmanager
    def _deterministic(self):
        snap = sl.GitSnapshot(in_repo=True, branch="main", dirty="modified",
                              is_worktree=False, wt_name="")
        with mock.patch.object(sl.time, "strftime", return_value="14:30"),\
             mock.patch.object(sl.time, "time", return_value=NOW),\
             mock.patch.object(sl, "probe_git_snapshot", return_value=snap),\
             mock.patch.object(sl, "probe_rss_bytes", return_value=448_790_528),\
             mock.patch.object(sl, "probe_transcript_bytes", return_value=305_000),\
             mock.patch.object(sl, "probe_current_todo", return_value=(None, None)),\
             mock.patch.object(sl, "probe_effort_setting_is_auto", return_value=False):
            yield

    def _render_all(self):
        with open(os.path.join(self.GOLDEN, "inputs.json"), encoding="utf-8") as f:
            cases = json.load(f)
        cfg = sl.cfg_default_config()
        # The meta segments report the render itself and are inherently
        # non-deterministic (render_time / slowest durations) and are exactly what
        # the restructure changes — exclude them so the golden guards only the
        # non-meta segment output it is meant to protect.
        cfg.segments["render_time"] = False
        cfg.segments["slowest"] = False
        theme = sl.core_build_theme(cfg)
        blocks = []
        with self._deterministic():
            for c in cases:
                env = {**self.ENV,
                       "STATUSLINE_COLS": str(c["cols"]),
                       "STATUSLINE_LINES": str(c["lines"])}
                data, _cols, _lines = _ctx_from_env(c["raw"], env, cfg, t_start=None)
                out = sl.core_render(data, cfg, theme)
                blocks.append(f"### {c['name']}\n" + "\n".join(strip(l) for l in out))
        return "\n\n".join(blocks) + "\n"

    def test_matches_golden(self):
        expected_path = os.path.join(self.GOLDEN, "expected.txt")
        actual = self._render_all()
        if os.environ.get("UPDATE_GOLDEN"):
            with open(expected_path, "w", encoding="utf-8") as f:
                f.write(actual)
        with open(expected_path, encoding="utf-8") as f:
            self.assertEqual(actual, f.read())


class TestDoctor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Resolve config to a path that does NOT exist → defaults, which are valid.
        self.env = {"HOME": self.tmp,
                    "CC_AI_KIT_CONFIG": os.path.join(self.tmp, "absent.toml")}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_doctor_ok_on_defaults(self):
        rc = sl.cmd_doctor(self.env)
        self.assertEqual(rc, 0)

    def test_doctor_flags_a_raising_builder(self):
        def boom(data, avail, theme):
            raise RuntimeError("x")
        with mock.patch.dict(sl.BUILDERS, {"path": boom}):
            rc = sl.cmd_doctor(self.env)
        self.assertEqual(rc, 1)

    def test_doctor_flags_a_raising_disabled_builder(self):
        # A builder that is DISABLED by default (`cost`) must still be dry-rendered:
        # the doctor exists to catch a builder that would crash once enabled.
        self.assertFalse(sl.cfg_default_config().segments.get("cost"))
        def boom(data, avail, theme):
            raise RuntimeError("x")
        with mock.patch.dict(sl.BUILDERS, {"cost": boom}):
            rc = sl.cmd_doctor(self.env)
        self.assertEqual(rc, 1)

    def test_doctor_flags_invalid_config_file(self):
        bad = os.path.join(self.tmp, "bad.toml")
        with open(bad, "w") as f:
            f.write("[segments]\nthis_is_not_a_segment = true\n")
        env = dict(self.env, CC_AI_KIT_CONFIG=bad)
        rc = sl.cmd_doctor(env)
        self.assertEqual(rc, 1)

    def test_check_flag_still_works(self):
        # Back-compat: --check path is untouched.
        rc = sl.cmd_check(os.path.join(self.tmp, "absent.toml"), self.env)
        self.assertEqual(rc, 1)   # absent file → cmd_check reports it (existing behavior)


if __name__ == "__main__":
    unittest.main(verbosity=2)
