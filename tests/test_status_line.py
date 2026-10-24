import contextlib
import importlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from typing import Any
from unittest import mock

_HERE = os.path.dirname(__file__)
_TOOLS_DIR = os.path.abspath(os.path.join(_HERE, "..", "tools"))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)
import datetime

claude_host: Any = importlib.import_module("claude_host")  # pre-split parity
claude_payload: Any = importlib.import_module("claude_payload")  # pre-split parity
claude_probes: Any = importlib.import_module("claude_probes")  # pre-split parity
claude_segments: Any = importlib.import_module("claude_segments")  # pre-split parity
common_config: Any = importlib.import_module("common_config")  # pre-split parity
common_fmt: Any = importlib.import_module("common_fmt")  # pre-split parity
common_probe: Any = importlib.import_module("common_probe")  # pre-split parity
common_render: Any = importlib.import_module("common_render")  # pre-split parity
common_segments: Any = importlib.import_module("common_segments")  # pre-split parity
common_types: Any = importlib.import_module("common_types")  # pre-split parity

_MODULE_PATH = os.path.join(_HERE, "..", "tools", "claude-status-line.py")


def load_module():
    spec = importlib.util.spec_from_file_location("status_line", _MODULE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # register so @dataclass can resolve cls.__module__
    spec.loader.exec_module(mod)
    return mod


sl = load_module()

THEME = common_render.core_default_theme(claude_host.HOST)

ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def strip(s):
    return ANSI_RE.sub("", s)


NOW = 1_000_000  # fixed epoch for deterministic rate-limit tests


def _ctx_from_env(raw, env, cfg, t_start=None):
    """Resolve the per-render SHELL inputs from `env` and build a Context — the
    test-side mirror of what safe_render does in production (terminal size, HOME,
    claude_dir, effort). Returns (ctx, cols, lines) for call-site convenience."""
    cols, lines, assumed = common_probe.probe_terminal_size(env)
    home = env.get("HOME", "")
    claude_dir = env.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
    ctx = claude_payload.core_build_context(
        raw,
        cfg,
        common_render.core_default_theme(claude_host.HOST),
        cols,
        lines,
        assumed,
        t_start,
        effort=claude_payload.cfg_resolve_effort(raw),
        home=home,
        claude_dir=claude_dir,
    )
    return ctx, cols, lines


def _data(**over):
    """Build a seeded Context for unit tests. Cheap eager fields are passed as
    constructor kwargs; expensive probe results are injected into probe_cache
    to bypass computation entirely (no filesystem/git/process calls)."""
    eager = {
        "model_name": "Opus 4.8",
        "model_id": "claude-opus-4-8",
        "work_dir": "/home/u/proj",
        "home": "/home/u",
        "clock": "14:30",
        "context_pct": 12,
        "context_max": 1_000_000,
        "cols": 200,
        "lines": 50,
        "dim_assumed": False,
        "t_start": None,
        "slowest": None,
    }
    probe_defaults = {
        "branch": "main",
        "dirty": "modified",
        "is_worktree": False,
        "in_repo": False,
        "wt_name": "",
        "root_name": "",
        "root_path": "",
        "ago": "5m 0s ago",
        "effort_auto": False,
        "todo_state": None,
        "todo_text": None,
        "chat_bytes": 305000,
        "mem_bytes": 448_790_528,
        "chat_since": None,
        "chat_compactions": 0,
    }
    # Route overrides: eager fields go to the constructor, probes go to probe_cache
    claude_fields = {
        "effort": "high",
        "added": 12,
        "removed": 3,
        "cost": 0.5,
        "total_ms": 65000,
        "api_ms": 4200,
        "rate_limits": {},
        "transcript": "",
        "session": "",
        "claude_dir": "/home/u/.claude",
    }
    host = {key: over.pop(key, value) for key, value in claude_fields.items()}
    eager_over = {k: over.pop(k) for k in list(over) if k in eager}
    probe_over = {**probe_defaults, **over}
    eager.update(eager_over)
    ctx = common_render.Context(
        raw={}, line_conf=common_config.cfg_default_config(claude_host.SPEC), theme=THEME,
        host=claude_payload.ClaudeData(**host), **eager
    )
    # Seed probe_cache directly so probes never fire during tests
    ctx.probe_cache["git"] = common_types.GitSnapshot(
        in_repo=probe_over["in_repo"],
        branch=probe_over["branch"],
        dirty=probe_over["dirty"],
        is_worktree=probe_over["is_worktree"],
        wt_name=probe_over["wt_name"],
        root_name=probe_over["root_name"],
        root_path=probe_over["root_path"],
    )
    ctx.probe_cache["todo"] = (probe_over["todo_state"], probe_over["todo_text"])
    ctx.probe_cache["ago"] = probe_over["ago"]
    ctx.probe_cache["effort_auto"] = probe_over["effort_auto"]
    ctx.probe_cache["chat_size"] = probe_over["chat_bytes"]
    if probe_over["chat_bytes"] is None:
        ctx.probe_cache["chat_compaction"] = None
    else:
        since = (
            probe_over["chat_bytes"]
            if probe_over["chat_since"] is None
            else probe_over["chat_since"]
        )
        ctx.probe_cache["chat_compaction"] = (since, probe_over["chat_compactions"])
    ctx.probe_cache["rss"] = probe_over["mem_bytes"]
    if "failed" in over:  # render-bookkeeping override (else fresh set)
        ctx.failed = over["failed"]
    return ctx


def _pack(keys, ctx, cols, cfg=None, theme=None, builders=None):
    """Single-line pack helper for tests: run the three render phases (measure +
    global meta + assemble) for ONE layout line and return its text. Mirrors the
    old `core_pack` contract over the new `core_measure_all` / `core_build_meta` /
    `core_assemble_line` structure so per-line packing assertions stay focused."""
    cfg = cfg or ctx.line_conf
    theme = theme or ctx.theme
    builders = (
        builders if builders is not None else common_render.core_builders_for(cfg, claude_host.HOST)
    )
    budget = cols - claude_host.RIGHT_MARGIN
    sep_w = common_types.util_visible_width(common_types.SEP)
    cfg = cfg._replace(layout=[common_types.Line(min_rows=0, segments=list(keys))])
    built = common_render.core_measure_all(
        ctx, cfg, budget, sep_w, theme, builders, claude_host.HOST.pinned
    )
    meta_built = common_render.core_build_meta(ctx, cfg, budget, theme, builders)
    enabled = [k for k in keys if cfg.segments.get(k, False)]
    line_built = {k: v for (_i, k), v in built.items()}
    line_built.update(meta_built)
    return common_render.core_assemble_line(
        enabled, line_built, budget, sep_w, claude_host.HOST.pinned
    )


def _load_cfg_with_toml(toml_text, **env_extra):
    """Write `toml_text` to a temp file and resolve a Config from it via
    cfg_load_config, pointing CC_AI_KIT_CONFIG_FILE at it. Returns the Config.
    The temp file is removed when the interpreter exits (best-effort)."""
    with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
        f.write(toml_text)
        path = f.name
    env = {"HOME": "/h", "CC_AI_KIT_CONFIG_FILE": path, **env_extra}
    try:
        return common_config.cfg_load_config(env, claude_host.SPEC)
    finally:
        with contextlib.suppress(OSError):
            os.unlink(path)


class TestPickColor(unittest.TestCase):
    def test_context_ramp_bands(self):
        cases = [
            (5, THEME.c("WHITE")),
            (9, THEME.c("WHITE")),
            (10, THEME.c("CYAN")),
            (14, THEME.c("CYAN")),
            (15, THEME.c("BLUE")),
            (19, THEME.c("BLUE")),
            (20, THEME.c("GREEN")),
            (24, THEME.c("GREEN")),
            (25, THEME.c("YELLOW")),
            (29, THEME.c("YELLOW")),
            (30, THEME.c("ORANGE+bold")),
            (39, THEME.c("ORANGE+bold")),
            (40, THEME.c("RED+bold")),
            (49, THEME.c("RED+bold")),
            (50, THEME.c("MAGENTA_DARK+bold")),
            (99, THEME.c("MAGENTA_DARK+bold")),
        ]
        for pct, want in cases:
            self.assertEqual(common_types.util_pick_color(pct, THEME.ramps["context"]), want, pct)

    def test_rate_ramp_bands(self):
        # [ramp.rate] still resolves into theme.ramps["rate"] (config parse
        # compat, kept so existing overrides don't error) but quota coloring
        # no longer reads it -- assert the resolved structure directly,
        # without the pace-era color helper (this refactoring deletes it).
        self.assertEqual(
            [(ceil, c) for ceil, c in THEME.ramps["rate"]],
            [
                (50.0, THEME.c("GREEN")),
                (80.0, THEME.c("YELLOW")),
                (float("inf"), THEME.c("RED+bold")),
            ],
        )

    def test_slowest_ramp_bands(self):
        # The single shared SLO/SLA ramp for the slowest segment: green under the
        # SLO (15ms), yellow under the SLA (40ms), red+bold beyond. Thresholds are
        # nanoseconds (matching data["slowest"]'s perf_counter_ns value).
        ms = 1_000_000
        cases = [
            (10 * ms, THEME.c("GREEN")),
            (14 * ms, THEME.c("GREEN")),
            (15 * ms, THEME.c("YELLOW")),
            (39 * ms, THEME.c("YELLOW")),
            (40 * ms, THEME.c("RED+bold")),
            (200 * ms, THEME.c("RED+bold")),
        ]
        for ns, want in cases:
            self.assertEqual(common_types.util_pick_color(ns, THEME.ramps["slowest"]), want, ns)

    def test_slowest_ramp_override_replaces_band(self):
        # [ramp.slowest] in config REPLACES the default band wholesale.
        cfg = common_config.cfg_default_config(claude_host.SPEC)._replace(
            ramps={"slowest": {"100ms": "CYAN", "inf": "WHITE"}}
        )
        theme = common_render.core_build_theme(cfg, claude_host.HOST)
        ms = 1_000_000
        self.assertEqual(
            common_types.util_pick_color(50 * ms, theme.ramps["slowest"]), theme.c("CYAN")
        )
        self.assertEqual(
            common_types.util_pick_color(200 * ms, theme.ramps["slowest"]), theme.c("WHITE")
        )


class TestWindowSeconds(unittest.TestCase):
    """Pure-function tests for util_rate_window_seconds (the window-key
    parser util_rate_gap now depends on). The four parsing tests are
    unchanged from the pace-ratio era; the pace-ratio tests that shared
    this class are deleted along with their helpers -- per
    docs/superpowers/specs/2026-10-09-statusline-quota-window-gap-design.md
    §Tests: "Keep util_rate_window_seconds parsing tests. They are
    unchanged"."""

    def test_window_seconds_parses_known_keys(self):
        self.assertEqual(claude_segments.util_rate_window_seconds("five_hour"), 5 * 3600)
        self.assertEqual(claude_segments.util_rate_window_seconds("seven_day"), 7 * 86400)

    def test_window_seconds_none_when_both_words_unknown(self):
        self.assertIsNone(claude_segments.util_rate_window_seconds("nonsense_unit"))

    def test_window_seconds_none_when_only_number_word_unknown(self):
        # "hour" IS a valid _UNIT_SECONDS key; "eleven" is NOT in _NUM_WORDS --
        # isolates a ONE-SIDED lookup failure.
        self.assertIsNone(claude_segments.util_rate_window_seconds("eleven_hour"))

    def test_window_seconds_none_when_only_unit_word_unknown(self):
        # Mirror case: "five" IS a valid _NUM_WORDS key; "fortnight" is NOT in
        # _UNIT_SECONDS.
        self.assertIsNone(claude_segments.util_rate_window_seconds("five_fortnight"))


class TestWindowGap(unittest.TestCase):
    def test_window_gap_bounds_and_empty_window(self):
        self.assertEqual(common_fmt.util_window_gap(50, 0, 100, 40), 10.0)
        self.assertIsNone(common_fmt.util_window_gap(50, 100, 100, 100))
        self.assertIsNone(common_fmt.util_window_gap(50, 0, 100, -1))
        self.assertIsNone(common_fmt.util_window_gap(50, 0, 100, 101))
        self.assertIsNone(common_fmt.util_window_gap(50, None, 100, 1))
        self.assertIsNone(common_fmt.util_window_gap(50, 0, None, 1))

    def test_rate_adapter_matches_original_arithmetic_exactly(self):
        import random

        rng = random.Random(2307)
        keys = ("five_hour", "seven_day", "thirty_day", "nonsense_unit")
        for _ in range(200):
            pct = rng.uniform(0, 100)
            key = rng.choice(keys)
            window = claude_segments.util_rate_window_seconds(key)
            reset = rng.randint(NOW - 1000, NOW + 40_000_000)
            now = rng.uniform(NOW - 1000, NOW + 1000)
            expected = None
            if window is not None:
                remaining = (reset - now) * 100.0 / window
                if 0.0 <= remaining <= 100.0:
                    expected = pct - (100.0 - remaining)
            self.assertEqual(claude_segments.util_rate_gap(pct, key, reset, now), expected)

    def test_gap_colors_pin_adjacent_spec_edges(self):
        cases = [(5.0, "GREEN"), (10.99, "YELLOW"), (11.0, "ORANGE"),
                 (15.0, "ORANGE"), (15.01, "RED")]
        for gap, color in cases:
            self.assertEqual(common_types.util_gap_color(gap, THEME), THEME.c(color), gap)

    def test_raw_gap_sign_is_glued_to_rounded_percentage(self):
        with mock.patch.object(time, "time", return_value=NOW):
            rl = {"five_hour": {"used_percentage": 50.49, "resets_at": NOW + 9000}}
            out = claude_segments.seg_alt_h_rate_limit(_data(rate_limits=rl), 200, THEME)
        self.assertIn("-50%", strip(out))


class TestRateGap(unittest.TestCase):
    """Pure-function tests for util_rate_gap (SIGNED percentage-point gap
    between used_percentage and the window's elapsed percentage),
    util_gap_color (absolute-gap band picker, inclusive bounds), and
    util_gap_sign -- the quota-window coloring defined by
    docs/superpowers/specs/2026-10-09-statusline-quota-window-gap-design.md."""

    def test_gap_signed_behind_and_ahead(self):
        # 45% of a 5h window elapsed (reset = NOW + 0.55 * 18000 = NOW + 9900):
        # 50% used is 5 points AHEAD (+5); 40% used is 5 points BEHIND (-5).
        self.assertAlmostEqual(claude_segments.util_rate_gap(50, "five_hour", NOW + 9900, NOW), 5.0)
        self.assertAlmostEqual(
            claude_segments.util_rate_gap(40, "five_hour", NOW + 9900, NOW), -5.0
        )

    def test_gap_color_bands_inclusive_bounds(self):
        cases = [
            (5.0, "GREEN"),
            (5.001, "YELLOW"),
            (10.999, "YELLOW"),
            (11.0, "ORANGE"),
            (15.0, "ORANGE"),
            (15.001, "RED"),
        ]
        for delta, want in cases:
            self.assertEqual(common_types.util_gap_color(delta, THEME), THEME.c(want), delta)

    def test_gap_live_spec_case_45_elapsed(self):
        # Spec worked checks: 45% elapsed + 43% used -> delta 2 GREEN;
        # 45% elapsed + 15% used -> delta 30 RED.
        gap_ok = claude_segments.util_rate_gap(43, "five_hour", NOW + 9900, NOW)
        self.assertAlmostEqual(gap_ok, -2.0)
        self.assertEqual(common_types.util_gap_color(abs(gap_ok), THEME), THEME.c("GREEN"))
        gap_bad = claude_segments.util_rate_gap(15, "five_hour", NOW + 9900, NOW)
        self.assertAlmostEqual(gap_bad, -30.0)
        self.assertEqual(common_types.util_gap_color(abs(gap_bad), THEME), THEME.c("RED"))

    def test_gap_at_window_start_color_and_gap(self):
        # elapsed_fraction == 0 (the old 1e-9 guard is gone): 0% used is a
        # 0 gap, grading GREEN; 6% used is a 6-point gap, grading YELLOW --
        # the spec's §Tests start-of-window cases pinned at BOTH levels.
        gap_zero = claude_segments.util_rate_gap(0, "five_hour", NOW + 5 * 3600, NOW)
        self.assertAlmostEqual(gap_zero, 0.0)
        self.assertEqual(common_types.util_gap_color(gap_zero, THEME), THEME.c("GREEN"))
        gap_six = claude_segments.util_rate_gap(6, "five_hour", NOW + 5 * 3600, NOW)
        self.assertAlmostEqual(gap_six, 6.0)
        self.assertEqual(common_types.util_gap_color(gap_six, THEME), THEME.c("YELLOW"))

    def test_gap_at_exact_reset_elapsed_is_100(self):
        # reset == now: elapsed_pct 100 (remaining_pct 0.0 exact). 100% used
        # -> 0 gap; 0% used -> -100.
        self.assertAlmostEqual(claude_segments.util_rate_gap(100, "five_hour", NOW, NOW), 0.0)
        self.assertAlmostEqual(claude_segments.util_rate_gap(0, "five_hour", NOW, NOW), -100.0)

    def test_gap_missing_reset_is_none(self):
        self.assertIsNone(claude_segments.util_rate_gap(50, "five_hour", None, NOW))

    def test_gap_past_reset_is_none(self):
        self.assertIsNone(claude_segments.util_rate_gap(50, "five_hour", NOW - 1, NOW))

    def test_gap_clock_skew_is_none(self):
        # 6h remaining of a 5h window: remaining_pct = 120 > 100.
        self.assertIsNone(claude_segments.util_rate_gap(50, "five_hour", NOW + 3600 * 6, NOW))

    def test_gap_unknown_key_is_none(self):
        self.assertIsNone(claude_segments.util_rate_gap(50, "nonsense_unit", NOW + 3600, NOW))

    def test_gap_sign_marks(self):
        # Sign is the INVERTED gap direction, glued to the displayed
        # percentage by the caller: + = usage at or behind the window clock
        # (under pace), - = usage ahead (burning faster than the clock).
        self.assertEqual(common_types.util_gap_sign(5.0), "-")
        self.assertEqual(common_types.util_gap_sign(-5.0), "+")
        self.assertEqual(common_types.util_gap_sign(0.0), "+")
        self.assertEqual(common_types.util_gap_sign(0.4), "-")
        self.assertEqual(common_types.util_gap_sign(-0.4), "+")
        self.assertEqual(common_types.util_gap_sign(-55.0), "+")


class TestFormatters(unittest.TestCase):
    def test_fmt_number(self):
        self.assertEqual(common_types.fmt_number(1234567), "1,234,567")

    def test_fmt_time_ms(self):
        self.assertEqual(common_types.fmt_time_ms(500), "500ms")
        self.assertEqual(common_types.fmt_time_ms(1500), "1s")
        self.assertEqual(common_types.fmt_time_ms(65000), "1m 5s")
        self.assertEqual(common_types.fmt_time_ms(3_700_000), "1h 1m")

    def test_fmt_tokens(self):
        self.assertEqual(common_types.fmt_tokens(200000), "200K")
        self.assertEqual(common_types.fmt_tokens(1_000_000), "1M")
        self.assertEqual(common_types.fmt_tokens(999), "999")

    def test_fmt_ago(self):
        self.assertEqual(common_types.fmt_ago(0), "just now")
        self.assertEqual(common_types.fmt_ago(30), "30s ago")
        self.assertEqual(common_types.fmt_ago(90), "1m 30s ago")
        self.assertEqual(common_types.fmt_ago(3700), "1h 1m ago")

    def test_fmt_bytes(self):
        self.assertEqual(common_types.fmt_bytes(512), "512B")
        self.assertEqual(common_types.fmt_bytes(1536), "1.5KB")
        self.assertEqual(common_types.fmt_bytes(305000), "298KB")  # ceil rounding

    def test_fmt_duration(self):
        # adaptive ns/µs/ms/s; one decimal when the scaled value is < 10
        self.assertEqual(common_types.fmt_duration(0), "0ns")
        self.assertEqual(common_types.fmt_duration(840), "840ns")
        self.assertEqual(common_types.fmt_duration(1500), "1.5µs")
        self.assertEqual(common_types.fmt_duration(12_000), "12µs")
        self.assertEqual(common_types.fmt_duration(4_100_000), "4.1ms")
        self.assertEqual(common_types.fmt_duration(45_000_000), "45ms")
        self.assertEqual(common_types.fmt_duration(1_200_000_000), "1.2s")


class TestVisibleWidth(unittest.TestCase):
    def test_plain_ascii(self):
        self.assertEqual(common_types.util_visible_width("hello"), 5)

    def test_ansi_is_zero_width(self):
        self.assertEqual(
            common_types.util_visible_width(f"{THEME.c('RED')}hi{common_types.RESET}"), 2
        )

    def test_smp_emoji_is_two_cells(self):
        for ch in "📊📝🧠💬📡💾🧮🌿🌳📃":
            self.assertEqual(common_types.util_char_width(ch), 2, ch)

    def test_wide_bmp_symbols_are_two_cells(self):
        for ch in "⏰⏸⚡":
            self.assertEqual(common_types.util_char_width(ch), 2, ch)

    def test_box_drawing_is_one_cell(self):
        for ch in "▁▃▄▆█▌░":
            self.assertEqual(common_types.util_char_width(ch), 1, ch)

    def test_narrow_symbols_are_one_cell(self):
        for ch in "✗~↺":
            self.assertEqual(common_types.util_char_width(ch), 1, ch)

    def test_combining_mark_is_zero(self):
        self.assertEqual(common_types.util_visible_width("é"), 1)  # e + combining acute

    def test_mixed_segment(self):
        self.assertEqual(common_types.util_visible_width("📊 12%"), 6)

    def test_variation_selector_is_zero_width(self):
        self.assertEqual(common_types.util_char_width("️"), 0)  # VS16 emoji presentation
        self.assertEqual(common_types.util_char_width("︎"), 0)  # VS15 text presentation

    def test_glyph_plus_vs16_measures_as_two(self):
        # ⏸ (modeled wide) + VS16 must stay 2 cells, not inflate to 3.
        self.assertEqual(common_types.util_visible_width("⏸️ x"), 4)  # 2 + 0 + 1(space) + 1(x)


class TestFirstFitting(unittest.TestCase):
    def test_returns_richest_that_fits(self):
        self.assertEqual(common_types.util_first_fitting(["abcdef", "abc", "a"], 4), "abc")

    def test_returns_first_when_all_fit(self):
        self.assertEqual(common_types.util_first_fitting(["ab", "a"], 10), "ab")

    def test_none_when_nothing_fits(self):
        self.assertIsNone(common_types.util_first_fitting(["abcdef", "abcd"], 3))

    def test_ignores_falsy_variants(self):
        self.assertEqual(common_types.util_first_fitting([None, "", "ok"], 5), "ok")


class TestTwoStateCap(unittest.TestCase):
    def test_returns_unchanged_when_it_fits_high(self):
        self.assertEqual(common_types.util_two_state_cap("proj", 30, 20), "proj")

    def test_boundary_exactly_at_high_is_unchanged(self):
        s = "a" * 30
        self.assertEqual(common_types.util_two_state_cap(s, 30, 20), s)

    def test_one_over_high_clips_to_low(self):
        # 31 > high(30) -> util_trunc_cols(s, 20): limit-1=19 reserved for
        # text, appends 19 'a's and stops (19+1>19) -> 19 a's + "…", 20
        # display columns wide, matching low.
        s = "a" * 31
        out = common_types.util_two_state_cap(s, 30, 20)
        self.assertEqual(out, "a" * 19 + "…")
        self.assertEqual(common_types.util_visible_width(out), 20)

    def test_far_over_high_still_clips_to_exactly_low(self):
        out = common_types.util_two_state_cap("a" * 40, 30, 20)
        self.assertEqual(out, "a" * 19 + "…")
        self.assertEqual(common_types.util_visible_width(out), 20)


class TestIconHelper(unittest.TestCase):
    def test_wide_emoji_gets_single_space(self):
        self.assertEqual(common_types.util_icon("\U0001f4c3", "x"), "\U0001f4c3 x")  # 📃 x

    def test_narrow_rendering_glyph_gets_vs16(self):
        # ⏱ ⏸ ⚡ are modeled wide but render narrow bare -> force emoji presentation.
        self.assertEqual(common_types.util_icon("⏱", "x"), "⏱️ x")  # ⏱️ x
        self.assertEqual(common_types.util_icon("⏸", "x"), "⏸️ x")  # ⏸️ x
        self.assertEqual(common_types.util_icon("⚡", "x"), "⚡️ x")  # ⚡️ x

    def test_already_wide_bmp_alarm_clock_no_vs16(self):
        self.assertEqual(common_types.util_icon("⏰", "x"), "⏰ x")  # ⏰ is EAW=W already

    def test_icon_width_is_two_plus_space_plus_text(self):
        self.assertEqual(
            common_types.util_visible_width(common_types.util_icon("⏸", "12:00")), 8
        )  # 2+1+5


class TestNoCollapsedIcons(unittest.TestCase):
    # The five segments that previously glued the glyph to the value.
    def test_collapsers_have_a_space_after_the_icon(self):
        cases = {
            "⏰": common_segments.seg_alt_time_clock(_data(), 80, THEME),  # ⏰
            "\U0001f4c3": claude_segments.seg_lines(_data(), 80, THEME),  # 📃
            "\U0001fa99": claude_segments.seg_alt_cost(_data(cost=0.5), 80, THEME),  # 🪙
            "\U0001f4ac": claude_segments.seg_alt_time_session(_data(), 80, THEME),  # 💬
            "\U0001f4e1": claude_segments.seg_alt_time_api(_data(), 80, THEME),  # 📡
        }
        for glyph, out in cases.items():
            plain = strip(out)
            self.assertTrue(plain.startswith(glyph), plain)
            after = plain[len(glyph) :]
            self.assertTrue(after.startswith(" "), f"icon collapsed: {plain!r}")

    def test_no_segment_emits_glyph_then_nonspace(self):
        # Property check across the iconed builders at a wide budget.
        builders = [
            common_segments.seg_alt_time_clock,
            claude_segments.seg_lines,
            lambda d, a, t: claude_segments.seg_alt_cost(_data(cost=0.5), a, t),
            claude_segments.seg_alt_time_session,
            claude_segments.seg_alt_time_api,
            common_segments.seg_render_time,
            lambda d, a, t: common_segments.seg_context(_data(), a, t),
            claude_segments.seg_chat_size,
            claude_segments.seg_alt_process_memory,
        ]
        for b in builders:
            out = b(_data(t_start=time.perf_counter_ns()), 120, THEME)
            if not out:
                continue
            plain = strip(out)
            for i, ch in enumerate(plain[:-1]):
                # An icon (wide glyph) must be followed by a space or VS16 — never
                # glued to text. Skip bar/box cells, which are legitimately wide.
                if common_types.util_char_width(ch) == 2 and ch not in "█▌░":
                    nxt = plain[i + 1]
                    self.assertIn(nxt, (" ", "️"), f"{plain!r} collapses at {i}")


class TestEffortTable(unittest.TestCase):
    def test_effort_colors(self):
        want = {
            "low": THEME.c("CYAN"),
            "medium": THEME.c("BLUE"),
            "high": THEME.c("YELLOW"),
            "xhigh": THEME.c("ORANGE"),
            "max": THEME.c("RED"),
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
        self.assertIn("main", common_segments.seg_git_branch(_data(branch="main"), 50, THEME))
        self.assertIsNone(common_segments.seg_git_branch(_data(branch="main"), 5, THEME))  # no room
        self.assertIsNone(common_segments.seg_git_branch(_data(branch=""), 200, THEME))  # no data

    def test_branch_has_static_icon_not_worktree_state(self):
        # branch carries its own STATIC 🌿 icon, but it must NOT encode worktree
        # state: no 🌳 (that meaning moved to the dedicated `worktree` ⎇ segment),
        # and the icon never changes with is_worktree.
        outs = []
        for wt in (True, False):
            out = common_segments.seg_git_branch(_data(branch="main", is_worktree=wt), 100, THEME)
            self.assertIn("main", out)
            self.assertIn("🌿", out)  # own branch icon restored
            self.assertNotIn("🌳", out)  # never the worktree-tree glyph
            self.assertNotIn("⎇", out)  # ⎇ belongs to the worktree segment
            outs.append(out)
        self.assertEqual(outs[0], outs[1])  # identical regardless of worktree state

    def test_branch_full_up_to_30_cols(self):
        branch = "feature/" + "x" * 20  # 28 cols, under the 30 cap
        out = common_segments.seg_git_branch(_data(branch=branch), 100, THEME)
        self.assertIn(branch, strip(out))
        self.assertNotIn("…", out)

    def test_branch_over_30_truncates_to_20(self):
        branch = "feature/" + "x" * 50  # 58 cols, over the 30 cap
        out = common_segments.seg_git_branch(_data(branch=branch), 100, THEME)
        expected = "feature/" + "x" * 11 + "…"  # util_trunc_cols(branch, 20)
        self.assertIn(expected, strip(out))
        self.assertEqual(common_types.util_visible_width(expected), 20)

    def test_branch_hides_when_even_20col_form_does_not_fit_avail(self):
        branch = "feature/" + "x" * 50
        self.assertIsNone(common_segments.seg_git_branch(_data(branch=branch), 5, THEME))

    def test_worktree_active_shows_name_cyan(self):
        out = common_segments.seg_alt_git_worktree(
            _data(in_repo=True, is_worktree=True, wt_name="feat-x"), 100, THEME
        )
        self.assertIn("⎇ feat-x", strip(out))
        self.assertIn(THEME.c("CYAN"), out)  # active form is cyan
        self.assertNotIn("\033[9m", out)  # NOT struck

    def test_worktree_main_checkout_struck_placeholder(self):
        out = common_segments.seg_alt_git_worktree(
            _data(in_repo=True, is_worktree=False), 100, THEME
        )
        self.assertIn("⎇ wt", strip(out))
        self.assertIn("\033[9m", out)  # strikethrough SGR
        self.assertIn(THEME.c("GREY"), out)  # dimmed/grey, distinct from cyan

    def test_worktree_hidden_outside_repo(self):
        self.assertIsNone(common_segments.seg_alt_git_worktree(_data(in_repo=False), 100, THEME))

    def test_worktree_name_full_up_to_30_cols(self):
        name = "a" * 28
        out = common_segments.seg_alt_git_worktree(
            _data(in_repo=True, is_worktree=True, wt_name=name), 100, THEME
        )
        self.assertIn(name, strip(out))
        self.assertNotIn("…", out)

    def test_worktree_name_over_30_truncates_to_20(self):
        name = "a" * 60
        out = common_segments.seg_alt_git_worktree(
            _data(in_repo=True, is_worktree=True, wt_name=name), 100, THEME
        )
        expected = "a" * 19 + "…"  # util_trunc_cols(name, 20)
        self.assertIn(expected, strip(out))
        self.assertEqual(common_types.util_visible_width(expected), 20)

    def test_worktree_name_hides_when_even_20col_form_does_not_fit_avail(self):
        name = "a" * 60
        self.assertIsNone(
            common_segments.seg_alt_git_worktree(
                _data(in_repo=True, is_worktree=True, wt_name=name), 5, THEME
            )
        )

    def test_effort_full_then_compact_then_hide(self):
        self.assertIn("high", strip(claude_segments.seg_effort(_data(effort="high"), 30, THEME)))
        compact = strip(claude_segments.seg_effort(_data(effort="high"), 10, THEME))
        self.assertNotIn("high", compact)
        self.assertIn("▁▃▄", compact)
        self.assertIsNone(claude_segments.seg_effort(_data(effort="high"), 5, THEME))
        self.assertIsNone(claude_segments.seg_effort(_data(effort=""), 200, THEME))

    def test_effort_all_levels_full(self):
        for level in ("low", "medium", "high", "xhigh", "max"):
            out = strip(claude_segments.seg_effort(_data(effort=level), 30, THEME))
            self.assertIn(level, out)
            self.assertTrue(out.startswith("🧠"))

    def test_context_three_tiers_never_none(self):
        self.assertIn(
            "of 1M", strip(common_segments.seg_context(_data(context_pct=12), 200, THEME))
        )
        mid = strip(common_segments.seg_context(_data(context_pct=12), 18, THEME))
        self.assertNotIn("of 1M", mid)
        self.assertIn("█", mid)
        self.assertEqual(
            strip(common_segments.seg_context(_data(context_pct=12), 8, THEME)), "📊 12%"
        )
        self.assertIsNotNone(common_segments.seg_context(_data(context_pct=12), 2, THEME))  # floor

    def test_context_hides_when_percent_is_missing(self):
        self.assertIsNone(common_segments.seg_context(_data(context_pct=None), 200, THEME))

    def test_context_omits_max_when_missing(self):
        out = strip(common_segments.seg_context(_data(context_max=None), 200, THEME))
        self.assertIn("12%", out)
        self.assertNotIn(" of ", out)

    def test_context_low_pct_half_bar_and_zero_empty(self):
        self.assertIn("▌", strip(common_segments.seg_context(_data(context_pct=5), 200, THEME)))
        zero = strip(common_segments.seg_context(_data(context_pct=0), 200, THEME))
        self.assertNotIn("█", zero)
        self.assertNotIn("▌", zero)

    def test_render_time_times_self_then_self_hide(self):
        d = _data(t_start=time.perf_counter_ns())
        out = common_segments.seg_render_time(d, 200, THEME)
        self.assertIn(THEME.c("GREEN"), out)  # fast run -> SLO green band
        out_s = strip(out)
        self.assertTrue(out_s.startswith("⏱"))  # stopwatch mark
        self.assertRegex(out_s, r"\d+(\.\d+)?(ns|µs|ms|s)$")  # a formatted duration
        self.assertIsNone(
            common_segments.seg_render_time(_data(), 200, THEME)
        )  # no t_start -> omit
        self.assertIsNone(common_segments.seg_render_time(d, 1, THEME))  # no room -> hide

    def test_render_time_colors_by_slo_sla_ramp(self):
        # a slow run (200ms ago) lands in the red+bold band (beyond the SLA)
        slow = _data(t_start=time.perf_counter_ns() - 200_000_000)
        self.assertIn(THEME.c("RED+bold"), common_segments.seg_render_time(slow, 200, THEME))

    def test_dimensions_content_then_self_hide(self):
        self.assertEqual(
            strip(common_segments.seg_alt_term_dimensions(_data(cols=120, lines=40), 200, THEME)),
            "120×40",
        )
        self.assertIsNone(
            common_segments.seg_alt_term_dimensions(_data(cols=120, lines=40), 3, THEME)
        )

    def test_chat_memory_self_hide_when_cramped(self):
        self.assertIsNotNone(claude_segments.seg_chat_size(_data(), 200, THEME))
        self.assertIsNone(claude_segments.seg_chat_size(_data(), 3, THEME))
        self.assertIsNone(claude_segments.seg_chat_size(_data(chat_bytes=None), 200, THEME))
        self.assertIsNone(claude_segments.seg_alt_process_memory(_data(mem_bytes=None), 200, THEME))

    def test_h_rate_limit_shows_time_only_reset_then_drops_it_when_narrow(self):
        rl = {"five_hour": {"used_percentage": 42, "resets_at": NOW + 3600}}
        rich = strip(claude_segments.seg_alt_h_rate_limit(_data(rate_limits=rl), 200, THEME))
        self.assertIn("5h: 42%", rich)
        self.assertIn("↺", rich)
        # time-only reset stamp — no date component at all
        dt = datetime.datetime.fromtimestamp(NOW + 3600)
        self.assertIn(dt.strftime("%H:%M"), rich)
        self.assertNotIn(dt.strftime("%b"), rich)
        narrow = strip(claude_segments.seg_alt_h_rate_limit(_data(rate_limits=rl), 10, THEME))
        self.assertEqual(narrow, "⚡️ 5h: 42%")
        self.assertIsNone(claude_segments.seg_alt_h_rate_limit(_data(rate_limits={}), 200, THEME))

    def test_h_rate_limit_hides_when_no_hourly_bucket(self):
        rl = {"seven_day": {"used_percentage": 13, "resets_at": NOW + 86400}}
        self.assertIsNone(claude_segments.seg_alt_h_rate_limit(_data(rate_limits=rl), 200, THEME))

    def test_h_rate_limit_ignores_weekly_bucket(self):
        rl = {
            "five_hour": {"used_percentage": 42, "resets_at": NOW + 3600},
            "seven_day": {"used_percentage": 13, "resets_at": NOW + 86400},
        }
        out = strip(claude_segments.seg_alt_h_rate_limit(_data(rate_limits=rl), 200, THEME))
        self.assertIn("5h:", out)
        self.assertNotIn("7d:", out)

    def test_w_rate_limit_shows_weekday_reset_then_drops_it_when_narrow(self):
        rl = {"seven_day": {"used_percentage": 13, "resets_at": NOW + 86400}}
        rich = strip(claude_segments.seg_alt_w_rate_limit(_data(rate_limits=rl), 200, THEME))
        self.assertIn("7d: 13%", rich)
        dt = datetime.datetime.fromtimestamp(NOW + 86400)
        self.assertIn(dt.strftime("%a"), rich)
        self.assertIn(dt.strftime("%H:%M"), rich)
        self.assertNotIn(dt.strftime("%b %d"), rich)
        narrow = strip(claude_segments.seg_alt_w_rate_limit(_data(rate_limits=rl), 10, THEME))
        self.assertEqual(narrow, "⚡️ 7d: 13%")
        self.assertIsNone(claude_segments.seg_alt_w_rate_limit(_data(rate_limits={}), 200, THEME))

    def test_w_rate_limit_hides_when_no_weekly_bucket(self):
        rl = {"five_hour": {"used_percentage": 42, "resets_at": NOW + 3600}}
        self.assertIsNone(claude_segments.seg_alt_w_rate_limit(_data(rate_limits=rl), 200, THEME))

    def test_rate_limit_no_reset_stamp_when_absent(self):
        rl_h = {"five_hour": {"used_percentage": 30}}
        self.assertEqual(
            strip(claude_segments.seg_alt_h_rate_limit(_data(rate_limits=rl_h), 200, THEME)),
            "⚡️ 5h: 30%",
        )
        rl_w = {"seven_day": {"used_percentage": 30}}
        self.assertEqual(
            strip(claude_segments.seg_alt_w_rate_limit(_data(rate_limits=rl_w), 200, THEME)),
            "⚡️ 7d: 30%",
        )

    def test_h_rate_limit_shows_bucket_even_with_past_reset(self):
        rl = {"five_hour": {"used_percentage": 50, "resets_at": NOW - 1}}
        out = strip(claude_segments.seg_alt_h_rate_limit(_data(rate_limits=rl), 200, THEME))
        self.assertIn("5h: 50%", out)

    def test_w_rate_limit_shows_bucket_even_with_past_reset(self):
        rl = {"seven_day": {"used_percentage": 50, "resets_at": NOW - 1}}
        out = strip(claude_segments.seg_alt_w_rate_limit(_data(rate_limits=rl), 200, THEME))
        self.assertIn("7d: 50%", out)

    def test_h_rate_limit_colors_by_absolute_gap(self):
        # Absolute-gap direction (spec): 45% of a 5h window elapsed, 15%
        # used is 30 points apart -> RED; 43% used is 2 points -> GREEN.
        # Reverses the pace ratio's "low usage late in the window is calm".
        # Separate calls -- same key in a shared dict would collide.
        with mock.patch.object(time, "time", return_value=NOW):
            rl_low = {"five_hour": {"used_percentage": 15, "resets_at": NOW + 9900}}
            out_low = claude_segments.seg_alt_h_rate_limit(_data(rate_limits=rl_low), 200, THEME)
            self.assertIn(THEME.c("RED"), out_low)
            self.assertNotIn(THEME.c("GREEN"), out_low)
            self.assertIn("+15%", strip(out_low))

            rl_ok = {"five_hour": {"used_percentage": 43, "resets_at": NOW + 9900}}
            out_ok = claude_segments.seg_alt_h_rate_limit(_data(rate_limits=rl_ok), 200, THEME)
            self.assertIn(THEME.c("GREEN"), out_ok)
            self.assertNotIn(THEME.c("RED"), out_ok)
            self.assertIn("+43%", strip(out_ok))

    def test_h_rate_limit_negative_sign_marks_usage_ahead(self):
        # Sign inverted from the gap direction: 50% used with 45% elapsed is
        # 5 points AHEAD of the clock -> '-' glued to the percentage. gap =
        # 50 - (100.0 - 9900.0 * 100.0 / 18000) = 5.0 float-exact, so
        # abs(gap) hits the GREEN band's <= 5.0 boundary exactly.
        with mock.patch.object(time, "time", return_value=NOW):
            rl = {"five_hour": {"used_percentage": 50, "resets_at": NOW + 9900}}
            out = claude_segments.seg_alt_h_rate_limit(_data(rate_limits=rl), 200, THEME)
            self.assertIn("-50%", strip(out))
            self.assertIn(THEME.c("GREEN"), out)

    def test_h_rate_limit_unreliable_window_paints_white_no_marker(self):
        # Past reset and clock skew both make the gap uncomputable: WHITE,
        # no marker, bucket still visible (spec fallback, not the old ramp).
        # The marker-absence asserts are per spec ("the fallback case renders
        # no marker"); the missing-reset case is equality-pinned separately
        # by test_rate_limit_no_reset_stamp_when_absent.
        with mock.patch.object(time, "time", return_value=NOW):
            rl_past = {"five_hour": {"used_percentage": 50, "resets_at": NOW - 1}}
            out_past = claude_segments.seg_alt_h_rate_limit(_data(rate_limits=rl_past), 200, THEME)
            self.assertIn(THEME.c("WHITE"), out_past)
            self.assertNotIn(THEME.c("RED"), out_past)
            self.assertNotIn("+", strip(out_past))
            self.assertNotIn("-", strip(out_past))

            rl_skew = {"five_hour": {"used_percentage": 50, "resets_at": NOW + 3600 * 6}}
            out_skew = claude_segments.seg_alt_h_rate_limit(_data(rate_limits=rl_skew), 200, THEME)
            self.assertIn(THEME.c("WHITE"), out_skew)
            self.assertNotIn("+", strip(out_skew))
            self.assertNotIn("-", strip(out_skew))

    def test_h_rate_limit_live_regression_low_pct_late_in_window_is_red(self):
        # Reversal pinned by the spec: the Phase 8.1 live case (25% used,
        # 4h of a 5h window elapsed -> 80%) was GREEN under the pace ratio
        # (25/0.8 = 31.25); the absolute gap is 55 points -> RED.
        with mock.patch.object(time, "time", return_value=NOW):
            rl = {"five_hour": {"used_percentage": 25, "resets_at": NOW + 3600}}
            out = claude_segments.seg_alt_h_rate_limit(_data(rate_limits=rl), 200, THEME)
            self.assertIn(THEME.c("RED"), out)
            self.assertNotIn(THEME.c("GREEN"), out)
            self.assertIn("+25%", strip(out))

    def test_h_rate_limit_display_unchanged_by_color_refactor(self):
        # Rich-tier text: the pace sign glued to the percentage (42 used,
        # 80% elapsed -> usage behind the clock -> '+'), then the reset
        # suffix; the terse/narrow tier stays byte-identical (its own test
        # pins that).
        with mock.patch.object(time, "time", return_value=NOW):
            rl = {"five_hour": {"used_percentage": 42, "resets_at": NOW + 3600}}
            out = strip(claude_segments.seg_alt_h_rate_limit(_data(rate_limits=rl), 200, THEME))
            self.assertEqual(
                out,
                f"⚡️ 5h: +42% (↺ {datetime.datetime.fromtimestamp(NOW + 3600).strftime('%H:%M')})",
            )

    def test_weekly_drops_before_hourly_under_column_pressure(self):
        # No resets_at, so each segment's terse form is its only form: "5h: 42%"
        # / "7d: 13%" (7 chars of content) plus util_icon's "⚡️ "
        # (2-wide glyph + 1 space) = 10 display cells each. Joined by SEP
        # (" | " = 3 cells), both together need 23 cells.
        #
        # budget = cols - RIGHT_MARGIN(4). At budget=15 the hourly segment (built
        # first, avail=15) fits in full (10 <= 15, used_est becomes 10); the
        # weekly segment then gets avail = max(15 - 10 - 3, 0) = 2, which is
        # below its 10-cell terse form, so it self-hides (returns None) and
        # never reaches the assembled line. At budget=23 (cols=27) both fit —
        # confirming this width genuinely distinguishes "only one fits" from
        # "both fit" rather than being trivially large.
        rl = {"five_hour": {"used_percentage": 42}, "seven_day": {"used_percentage": 13}}
        ctx = _data(rate_limits=rl)
        keys = ["alt_h_rate_limit", "alt_w_rate_limit"]
        cfg = ctx.line_conf
        cfg = cfg._replace(
            segments={**cfg.segments, "alt_h_rate_limit": True, "alt_w_rate_limit": True}
        )

        tight = strip(_pack(keys, ctx, 19, cfg=cfg))  # budget = 19 - 4 = 15
        self.assertIn("5h: 42%", tight)
        self.assertNotIn("7d:", tight)

        roomy = strip(_pack(keys, ctx, 27, cfg=cfg))  # budget = 27 - 4 = 23
        self.assertIn("5h: 42%", roomy)
        self.assertIn("7d: 13%", roomy)

    def test_model_and_clock(self):
        self.assertEqual(strip(common_segments.seg_model(_data(), 200, THEME)), "Opus 4.8")
        self.assertEqual(strip(common_segments.seg_alt_time_clock(_data(), 200, THEME)), "⏰ 14:30")

    def test_todo_truncates_and_hides(self):
        self.assertIn(
            "hello",
            strip(
                claude_segments.seg_todo(
                    _data(todo_state="in_progress", todo_text="hello"), 200, THEME
                )
            ),
        )
        self.assertIsNone(
            claude_segments.seg_todo(_data(todo_state="in_progress", todo_text="hello"), 8, THEME)
        )

    def test_path_never_none(self):
        self.assertIsNotNone(common_segments.seg_path(_data(), 1, THEME))

    def test_builders_registry_complete(self):
        for key in (
            "path",
            "git_branch",
            "git_dirty",
            "todo",
            "model",
            "alt_time_ago",
            "alt_time_clock",
            "effort",
            "lines",
            "alt_cost",
            "alt_time_session",
            "alt_time_api",
            "render_time",
            "alt_term_dimensions",
            "context",
            "chat_size",
            "alt_process_memory",
            "alt_h_rate_limit",
            "alt_w_rate_limit",
        ):
            self.assertIn(key, claude_host.BUILDERS, key)
            self.assertTrue(callable(claude_host.BUILDERS[key]))

    def test_discovered_builders_cover_segments(self):
        # The registry is auto-discovered from the seg_* functions (FR-A.3, D7):
        # every SEGMENTS key has a discovered builder and discovery finds no stray
        # keys — guards the convention so adding a seg_x just works.
        self.assertEqual(set(claude_host.BUILDERS), set(claude_host.SEGMENTS))
        self.assertTrue(all(callable(fn) for fn in claude_host.BUILDERS.values()))


class TestDisplayDir(unittest.TestCase):
    def test_short_path_kept_whole(self):
        self.assertEqual(common_types.util_display_dir("/home/u/proj", "/home/u"), "~/proj")

    def test_medium_path_collapses_to_parent_slash_name(self):
        # full (~/workspaces/very-long-organization-name-here/short-repo) is
        # 56 cols, over the 50 structural cap -> falls to parent/name, which
        # is 43 cols, under the cap -> shown.
        work_dir = "/home/u/workspaces/very-long-organization-name-here/short-repo"
        self.assertEqual(
            common_types.util_display_dir(work_dir, "/home/u"),
            "very-long-organization-name-here/short-repo",
        )

    def test_falls_to_basename_alone_when_both_structural_forms_too_long(self):
        # full is 73 cols and parent/name is 71 cols, both over the 50
        # structural cap -> falls to the basename alone; "short-name" (10
        # cols) fits the 30-col name-floor high threshold, so it's shown
        # unclipped.
        work_dir = "/home/u/" + "a" * 60 + "/short-name"
        self.assertEqual(common_types.util_display_dir(work_dir, "/home/u"), "short-name")

    def test_basename_clipped_to_20_when_over_30(self):
        # full is 88 cols and parent/name is 75 cols, both over the 50
        # structural cap; the basename alone ("another-very-long-repository-name",
        # 33 cols) exceeds the 30-col name-floor high threshold, so it's
        # clipped to 20 via util_two_state_cap.
        work_dir = (
            "/home/u/workspaces/very-long-organization-name-here-extended"
            "/another-very-long-repository-name"
        )
        self.assertEqual(common_types.util_display_dir(work_dir, "/home/u"), "another-very-long-r…")

    def test_no_ellipsis_when_a_variant_fits_whole(self):
        work_dir = "/home/u/workspaces/very-long-organization-name-here/short-repo"
        self.assertNotIn("…", common_types.util_display_dir(work_dir, "/home/u"))


class TestPackLine(unittest.TestCase):
    def test_keeps_segments_that_fit(self):
        claude_host.SEGMENTS["alt_time_clock"] = True
        try:
            out = _pack(["model", "alt_time_clock"], _data(), 200)
            self.assertIn("Opus 4.8", strip(out))
            self.assertIn("⏰ 14:30", strip(out))
            self.assertIn(" | ", out)
        finally:
            claude_host.SEGMENTS["alt_time_clock"] = False

    def test_best_fit_skips_overflow_keeps_smaller(self):
        claude_host.SEGMENTS["alt_time_clock"] = True
        try:
            out = strip(_pack(["model", "alt_time_clock"], _data(model_name="X" * 60), 30))
            self.assertIn("⏰ 14:30", out)
            self.assertNotIn("XXXX", out)
        finally:
            claude_host.SEGMENTS["alt_time_clock"] = False

    def test_flag_off_segment_not_built(self):
        # alt_time_clock is already OFF by default; this test confirms the flag is honoured.
        out = strip(_pack(["model", "alt_time_clock"], _data(), 200))
        self.assertNotIn("⏰", out)

    def test_pinned_path_present_even_when_too_narrow(self):
        out = strip(
            _pack(["path", "git_branch"], _data(work_dir="/home/u/proj", home="/home/u"), 5)
        )
        self.assertIn("proj", out)

    def test_pinned_context_present_even_when_too_narrow(self):
        out = strip(
            _pack(["alt_term_dimensions", "context"], _data(cols=300, lines=80, context_pct=12), 8)
        )
        self.assertIn("12%", out)

    def test_respects_right_margin(self):
        out = _pack(["model", "alt_time_clock", "effort", "lines"], _data(), 60)
        self.assertLessEqual(common_types.util_visible_width(out), 60 - claude_host.RIGHT_MARGIN)


class TestMetaPositionIndependent(unittest.TestCase):
    """FR-4.5: meta segments (`slowest`, `render_time`) report the WHOLE render,
    so their value must be identical no matter which layout line they sit on.
    The three-phase packer crowns `ctx.slowest` globally across ALL lines (Phase A)
    before any meta is built (Phase B), making the readout position-independent."""

    @staticmethod
    def _slow_seg(_ctx, _avail, _theme):
        time.sleep(0.005)
        return "SLOW"

    def _make_cfg_with_slowest_on_line(self, line_idx: int):
        """A two-line config: `slow_seg` always lives on line 1 (so it is the
        global slowest), while the `slowest` readout is placed on `line_idx`."""
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        segs = {k: False for k in cfg.segments}
        for k in ("path", "model", "slowest", "slow_seg"):
            segs[k] = True
        lines = [
            common_types.Line(min_rows=1, segments=["path", "model"]),
            common_types.Line(min_rows=1, segments=["path", "slow_seg"]),
        ]
        lines[line_idx] = common_types.Line(
            min_rows=1, segments=[*lines[line_idx].segments, "slowest"]
        )
        return cfg._replace(layout=lines, segments=segs)

    def _render_slowest_on(self, line_idx: int) -> str:
        cfg = self._make_cfg_with_slowest_on_line(line_idx)
        ctx = _data()
        with mock.patch.dict(claude_host.BUILDERS, {"slow_seg": self._slow_seg}):
            rendered = common_render.core_render(ctx, claude_host.HOST, cfg=cfg)
        # seg_slowest emits "🐌 <name> <dur>"; assert on the crowned NAME (the
        # position-dependent part), not the duration (real-time jitter would make
        # the exact ms flaky across two independent renders).
        for line in rendered:
            m = re.search(r"(\w+) [\d.]+ms", strip(line))
            if m:
                return m.group(1)
        return ""

    def test_slowest_same_regardless_of_line(self):
        """slowest readout is identical whether `slowest` is on line 0 or line 1."""
        slowest0 = self._render_slowest_on(0)
        slowest1 = self._render_slowest_on(1)
        self.assertTrue(slowest0, "slowest segment not found in layout 0 output")
        self.assertTrue(slowest1, "slowest segment not found in layout 1 output")
        self.assertEqual(slowest0, "slow_seg")  # the global slowest, not a fast same-line peer
        self.assertEqual(
            slowest0, slowest1, f"slowest differs by position: {slowest0!r} vs {slowest1!r}"
        )


class TestSlowestTiming(unittest.TestCase):
    def test_probe_cost_counted_in_triggering_segment(self):
        # FR-A.2 / FR-R.2: a memoized probe runs synchronously on first access,
        # so its cost lands INSIDE the measured build of the segment that reads it
        # — not amortized to µs. A live (un-seeded) Context whose git probe sleeps
        # proves the `branch` segment is crowned ms-scale, and that the probe
        # actually fired during the measure phase (not pre-seeded).
        def slow_git(*_a, **_k):
            time.sleep(0.005)
            return common_types.GitSnapshot(
                in_repo=True, branch="main", dirty="clean", is_worktree=False, wt_name=""
            )

        cfg = common_config.cfg_default_config(claude_host.SPEC)
        cfg.segments.update({"slowest": True, "git_branch": True})
        ctx = claude_payload.core_build_context(
            raw={"workspace": {"current_dir": "/tmp"}},
            config=cfg,
            theme=THEME,
            cols=200,
            lines=50,
            dim_assumed=False,
            t_start=time.perf_counter_ns(),
            effort="high",
            home="/home/u",
            claude_dir="/home/u/.claude",
        )
        with mock.patch.object(common_probe, "probe_git_snapshot", side_effect=slow_git):
            _pack(["git_branch"], ctx, 200, cfg=cfg)
        # The probe must have run during the measure phase (proves laziness via probe_cache):
        cache = ctx.probe_cache
        self.assertIsNotNone(cache)
        assert cache is not None
        self.assertIsNotNone(cache.get("git"))
        name, ns = ctx.slowest
        self.assertEqual(name, "git_branch")
        self.assertGreaterEqual(ns, 4_000_000)  # >= ~4ms: probe cost is inside the build

    @staticmethod
    def _slow(data, avail, theme):
        del avail
        time.sleep(0.005)
        return "SLOW"

    @staticmethod
    def _fast(data, avail, theme):
        del avail
        return "FAST"

    def test_pack_line_records_slowest_builder(self):
        # With `slowest` enabled the packer times each builder and records the max
        # as ctx.slowest = (name, ns) — the exact attribute seg_slowest reads.
        builders = {"fast_seg": self._fast, "slow_seg": self._slow}
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        cfg.segments.update({"slowest": True, "fast_seg": True, "slow_seg": True})
        data = _data()
        _pack(["fast_seg", "slow_seg"], data, 200, cfg=cfg, builders=builders)
        name, ns = data.slowest
        self.assertEqual(name, "slow_seg")
        self.assertIsInstance(ns, int)
        self.assertGreater(ns, 0)

    def test_slowest_accumulates_max_across_lines(self):
        # core_render() measures all layout lines against one ctx; the running max
        # must survive across measure passes (slow line first, fast line second).
        builders = {"fast_seg": self._fast, "slow_seg": self._slow}
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        cfg.segments.update({"slowest": True, "fast_seg": True, "slow_seg": True})
        data = _data()
        _pack(["slow_seg"], data, 200, cfg=cfg, builders=builders)
        _pack(["fast_seg"], data, 200, cfg=cfg, builders=builders)
        self.assertEqual(data.slowest[0], "slow_seg")  # not overwritten by the fast line

    def test_failed_builder_not_recorded_as_slowest(self):
        # A segment that crashes never rendered, so its time must not crown it the
        # slowest culprit (else seg_slowest would name a broken segment).
        def boom(data, avail, theme):
            del avail
            raise RuntimeError("nope")

        builders = {"boom": boom, "fast_seg": self._fast}
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        cfg.segments.update({"slowest": True, "boom": True, "fast_seg": True})
        data = _data()
        _pack(["boom", "fast_seg"], data, 200, cfg=cfg, builders=builders)
        self.assertNotEqual((data.slowest or (None,))[0], "boom")

    def test_empty_output_builder_not_recorded_as_slowest(self):
        # A segment that renders nothing (e.g. a failing external provider that is
        # gracefully omitted) is not a visible culprit, so it isn't crowned slowest.
        def empty(data, avail, theme):
            del avail
            return None

        builders = {"empty_seg": empty, "fast_seg": self._fast}
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        cfg.segments.update({"slowest": True, "empty_seg": True, "fast_seg": True})
        data = _data()
        _pack(["empty_seg", "fast_seg"], data, 200, cfg=cfg, builders=builders)
        self.assertNotEqual((data.slowest or (None,))[0], "empty_seg")

    def test_slowest_built_after_non_meta_regardless_of_position(self):
        # FR-R.3: every non-meta build is timed in Phase A (core_measure_all) before
        # any meta segment is built in Phase B (core_build_meta), so slowest no longer
        # has to be last on its line — it sits right after render_time.
        line = next(l for l in claude_host.LAYOUT if "slowest" in l.segments)
        self.assertNotEqual(line.segments[-1], "slowest")
        self.assertEqual(line.segments.index("slowest"), line.segments.index("render_time") + 1)

    def test_later_segment_reported_even_when_slowest_precedes_it(self):
        # Phase A times a slow non-meta segment before Phase B builds meta, so
        # seg_slowest names it even when `slowest` is positioned BEFORE it in the key order.
        builders = dict(claude_host.BUILDERS)
        builders["slow_seg"] = self._slow
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        cfg.segments.update({"slowest": True, "slow_seg": True})
        data = _data()
        out = _pack(["slowest", "slow_seg"], data, 200, cfg=cfg, builders=builders)
        self.assertEqual(data.slowest[0], "slow_seg")
        self.assertIn("slow_seg", strip(out))  # seg_slowest (built in Phase B) names it

    def test_render_time_not_crowned_slowest(self):
        # M1: render_time is a meta-segment (reports the whole render); never a culprit.
        def slow_rt(data, avail, theme):
            del avail
            time.sleep(0.005)
            return "RT"

        builders = {"render_time": slow_rt, "fast_seg": self._fast}
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        cfg.segments.update({"slowest": True, "render_time": True, "fast_seg": True})
        data = _data()
        _pack(["render_time", "fast_seg"], data, 200, cfg=cfg, builders=builders)
        self.assertNotEqual((data.slowest or (None,))[0], "render_time")

    def test_overflow_dropped_segment_not_recorded_slowest(self):
        # L1: a slow segment whose output is too wide to fit is dropped — it never
        # rendered, so it must not be crowned slowest.
        def slow_wide(data, avail, theme):
            del avail
            time.sleep(0.005)
            return "X" * 100

        builders = {"wide_seg": slow_wide, "fast_seg": self._fast}
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        cfg.segments.update({"slowest": True, "wide_seg": True, "fast_seg": True})
        data = _data()
        _pack(["fast_seg", "wide_seg"], data, 20, cfg=cfg, builders=builders)
        self.assertNotEqual((data.slowest or (None,))[0], "wide_seg")

    def test_slowest_readout_hidden_when_disabled(self):
        # Builds are always timed now (negligible, and FR-R.1 drops the per-segment
        # special case) — but with `slowest` disabled its readout is gated off and
        # never renders. The internal max may be tracked; the user never sees it.
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        cfg.segments["slowest"] = False
        theme = common_render.core_build_theme(cfg, claude_host.HOST)
        env = {"HOME": "/h", "STATUSLINE_COLS": "200", "STATUSLINE_LINES": "50"}
        with mock.patch.object(
            common_probe,
            "probe_git_snapshot",
            return_value=common_types.GitSnapshot(True, "m", "clean", False, ""),
        ):
            data, _cols, _lines = _ctx_from_env(
                {"workspace": {"current_dir": "."}, "transcript_path": ""}, env, cfg
            )
            out = "\n".join(common_render.core_render(data, claude_host.HOST, cfg, theme))
        self.assertNotIn("🐌", strip(out))


class TestSlowestSegment(unittest.TestCase):
    def test_renders_culprit_name_and_duration(self):
        out = common_segments.seg_slowest(_data(slowest=("git", 30_000_000)), 200, THEME)
        self.assertIn("🐌", out)
        self.assertIn("git", strip(out))  # names the culprit segment
        self.assertIn("30ms", strip(out))  # and its duration

    def test_colored_by_single_slowest_ramp(self):
        # 30ms -> YELLOW band, 100ms -> RED+bold — the one shared slowest ramp.
        self.assertIn(
            THEME.c("YELLOW"),
            common_segments.seg_slowest(_data(slowest=("git", 30_000_000)), 200, THEME),
        )
        self.assertIn(
            THEME.c("RED+bold"),
            common_segments.seg_slowest(_data(slowest=("ext", 100_000_000)), 200, THEME),
        )

    def test_omitted_when_no_timing(self):
        self.assertIsNone(common_segments.seg_slowest(_data(), 200, THEME))  # no data["slowest"]

    def test_on_by_default_and_registered(self):
        self.assertTrue(claude_host.SEGMENTS["slowest"])
        self.assertIn("slowest", claude_host.BUILDERS)


class TestRenderLayout(unittest.TestCase):
    def test_three_lines_when_tall_and_wide(self):
        self.assertEqual(len(common_render.core_render(_data(), claude_host.HOST)), 3)

    def test_line_gating_by_rows(self):
        self.assertEqual(
            len(common_render.core_render(_data(lines=10), claude_host.HOST)), 1
        )  # identity only
        self.assertEqual(
            len(common_render.core_render(_data(lines=25), claude_host.HOST)), 2
        )  # + model row

    def test_identity_line_never_empty(self):
        out = common_render.core_render(
            _data(branch="", dirty="clean", todo_text=None), claude_host.HOST
        )
        self.assertTrue(out[0].strip())

    def test_context_pinned(self):
        self.assertIn("context", claude_host.PINNED)
        self.assertIn("path", claude_host.PINNED)


class TestDocumentation(unittest.TestCase):
    def _src(self):
        with open(os.path.join(_TOOLS_DIR, "claude_host.py"), encoding="utf-8") as f:
            return f.read()

    def test_module_lists_all_segments(self):
        src = self._src()
        for key in (
            "path",
            "git_branch",
            "git_dirty",
            "todo",
            "model",
            "alt_time_ago",
            "alt_time_clock",
            "effort",
            "lines",
            "alt_time_session",
            "alt_time_api",
            "render_time",
            "alt_term_dimensions",
            "context",
            "chat_size",
            "alt_process_memory",
            "alt_h_rate_limit",
            "alt_w_rate_limit",
        ):
            self.assertIn(key, src, key)

    def test_has_customization_guide(self):
        src = self._src()
        for phrase in (
            "HOW TO CUSTOMIZE",
            "Add a NEW segment",
            "Reorder",
            "Re-enable",
            "auto-deprioritize",
        ):
            self.assertIn(phrase, src, phrase)


class TestProcAndGit(unittest.TestCase):
    def test_proc_rss_and_git_smoke(self):
        rss = claude_probes.probe_rss_bytes()
        self.assertTrue(rss is None or isinstance(rss, int))
        with tempfile.TemporaryDirectory() as home:
            env = {"HOME": home}
            cfg = common_config.cfg_default_config(claude_host.SPEC)._replace(
                cache_base=common_config.cfg_cache_base(env)
            )
            snap = common_probe.probe_git_snapshot(".", cfg)
        self.assertIn(snap.dirty, ("clean", "untracked", "modified"))
        self.assertIsInstance(snap.is_worktree, bool)
        self.assertIsInstance(snap.wt_name, str)

    def test_slow_git_times_out_to_empty_snapshot(self):
        with tempfile.TemporaryDirectory() as root:
            bindir = os.path.join(root, "bin")
            os.mkdir(bindir)
            git = os.path.join(bindir, "git")
            with open(git, "w", encoding="utf-8") as script:
                script.write("#!/bin/sh\nsleep 5\n")
            os.chmod(git, 0o755)
            with (
                mock.patch.dict(os.environ, {"PATH": bindir + os.pathsep + os.defpath}),
                mock.patch.object(common_probe, "GIT_TIMEOUT_S", 0.2),
            ):
                started = time.monotonic()
                snapshot = common_probe.probe_git_snapshot(root)
            self.assertLess(time.monotonic() - started, 2)
            self.assertFalse(snapshot.in_repo)
            self.assertEqual(snapshot.branch, "")

    def test_entry_render_survives_slow_git(self):
        with tempfile.TemporaryDirectory(prefix="slow-git-entry-") as root:
            bindir = os.path.join(root, "bin")
            os.mkdir(bindir)
            git = os.path.join(bindir, "git")
            with open(git, "w", encoding="utf-8") as script:
                script.write("#!/bin/sh\nsleep 5\n")
            os.chmod(git, 0o755)
            started = time.monotonic()
            output = run_entry(root, "{}", {"PATH": bindir + os.pathsep + os.defpath})
            self.assertLess(time.monotonic() - started, 6)
            self.assertIn("slow-git-entry-", output)

    def test_branch_from_porcelain_header(self):
        self.assertEqual(common_types.util_branch_from_porcelain("## main"), "main")
        self.assertEqual(common_types.util_branch_from_porcelain("## main...origin/main"), "main")
        self.assertEqual(
            common_types.util_branch_from_porcelain("## feat/x...origin/feat/x [ahead 18]"),
            "feat/x",
        )
        self.assertEqual(
            common_types.util_branch_from_porcelain("## HEAD (no branch)"), ""
        )  # detached
        self.assertEqual(
            common_types.util_branch_from_porcelain("## No commits yet on main"), "main"
        )
        self.assertEqual(common_types.util_branch_from_porcelain("## Initial commit on dev"), "dev")
        self.assertEqual(common_types.util_branch_from_porcelain(""), "")  # not a repo

    def _home_env(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        return {"HOME": d}

    def test_git_snapshot_dirty_parsing(self):
        # probe_git_snapshot parses branch + dirty from the porcelain --branch output;
        # mock subprocess so the test is independent of the live working tree.
        def fake_run(cmd, **kw):
            del kw

            class R:
                returncode = 0
                stdout = (
                    "## main...origin/main [ahead 1]\n M tools/x.py\n?? new.py\n"
                    if "status" in cmd
                    else ".git\n.git\n/repo\n"
                )

            return R()

        env = self._home_env()
        cfg = common_config.cfg_default_config(claude_host.SPEC)._replace(
            cache_base=common_config.cfg_cache_base(env)
        )
        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            snap = common_probe.probe_git_snapshot(".", cfg)
            self.assertEqual(snap.branch, "main")
            self.assertEqual(snap.dirty, "untracked")  # ?? present -> untracked
            self.assertFalse(snap.is_worktree)  # git-dir == git-common-dir

    def test_git_snapshot_always_does_full_untracked_walk(self):
        # The probe owns its policy: it ALWAYS does the full untracked walk (no
        # per-call gating knob). Laziness — not a flag — gates whether it runs.
        env = self._home_env()
        cfg = common_config.cfg_default_config(claude_host.SPEC)._replace(
            cache_base=common_config.cfg_cache_base(env)
        )
        seen = []

        def fake_run(cmd, *, _seen=seen, **kw):
            del kw
            _seen.append(cmd)

            class R:
                returncode = 0
                stdout = "## main\n"

            return R()

        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            common_probe.probe_git_snapshot(".", cfg)
        status_cmd = next(c for c in seen if "status" in c)
        self.assertNotIn("--untracked-files=no", status_cmd)  # always the full walk

    def test_git_snapshot_always_runs_worktree_probe(self):
        # The probe always runs the worktree rev-parse (no want_worktree knob);
        # laziness gates whether probe_git_snapshot is called at all, not this rev-parse.
        env = self._home_env()
        cfg = common_config.cfg_default_config(claude_host.SPEC)._replace(
            cache_base=common_config.cfg_cache_base(env)
        )
        seen = []

        def fake_run(cmd, *, _seen=seen, **kw):
            del kw
            _seen.append(cmd)

            class R:
                returncode = 0
                stdout = "## main\n" if "status" in cmd else ".git\n.git\n/repo\n"

            return R()

        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            common_probe.probe_git_snapshot(".", cfg)
        self.assertTrue(any("rev-parse" in c for c in seen))

    def test_git_snapshot_clean_and_worktree_name(self):
        def fake_run(cmd, **kw):
            del kw

            class R:
                returncode = 0
                stdout = (
                    "## main\n"
                    if "status" in cmd
                    else "/wt/.git/worktrees/feat-x\n/main/.git\n/path/to/feat-x\n"
                )

            return R()

        env = self._home_env()
        cfg = common_config.cfg_default_config(claude_host.SPEC)._replace(
            cache_base=common_config.cfg_cache_base(env)
        )
        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            snap = common_probe.probe_git_snapshot(".", cfg)
            self.assertEqual((snap.branch, snap.dirty), ("main", "clean"))
            self.assertTrue(snap.is_worktree)  # git-dir != git-common-dir
            self.assertTrue(snap.in_repo)
            self.assertEqual(snap.wt_name, "feat-x")  # basename of --show-toplevel
            self.assertEqual(snap.root_name, "main")  # dirname of --git-common-dir
            self.assertEqual(snap.root_path, "/main")  # --git-common-dir's dirname, absolute

    def test_git_snapshot_root_name_non_worktree(self):
        def fake_run(cmd, **kw):
            del kw

            class R:
                returncode = 0
                stdout = "## main\n" if "status" in cmd else "/repo/.git\n/repo/.git\n/repo\n"

            return R()

        env = self._home_env()
        cfg = common_config.cfg_default_config(claude_host.SPEC)._replace(
            cache_base=common_config.cfg_cache_base(env)
        )
        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            snap = common_probe.probe_git_snapshot(".", cfg)
            self.assertFalse(snap.is_worktree)
            self.assertEqual(snap.root_name, "repo")
            self.assertEqual(snap.root_path, "/repo")

    def test_probe_git_worktree_info_requests_absolute_paths(self):
        # --git-common-dir must be absolute or root_name's dirname() math breaks.
        seen = []

        def fake_run(cmd, **kw):
            del kw
            seen.append(cmd)

            class R:
                returncode = 0
                stdout = "/repo/.git\n/repo/.git\n/repo\n"

            return R()

        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            common_probe.probe_git_worktree_info(".")
        self.assertIn("--path-format=absolute", seen[0])

    def test_probe_git_worktree_info_bare_repo_common_dir_guard(self):
        # --git-common-dir doesn't always end in "/.git" — a bare repo's
        # common-dir IS the repo dir itself. root_name must not blindly take
        # dirname() of a path that isn't "<root>/.git"; it should fall back
        # to the common-dir's own basename instead of walking one level too
        # far up (which would report the bare repo's PARENT dir as the name).
        def fake_run(cmd, **kw):
            del kw

            class R:
                returncode = 0
                stdout = "/srv/bare-repo\n/srv/bare-repo\n/srv/bare-repo\n"

            return R()

        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            in_repo, _is_worktree, _name, root_name, root_path = (
                common_probe.probe_git_worktree_info(".")
            )
        self.assertTrue(in_repo)
        self.assertEqual(root_name, "bare-repo")
        self.assertEqual(root_path, "/srv/bare-repo")

    def test_worktree_info_cached_within_ttl(self):
        # Second call within the TTL must NOT re-run the rev-parse (cached on disk).
        env = self._home_env()
        cache_base = common_config.cfg_cache_base(env)
        cfg = common_config.cfg_default_config(claude_host.SPEC)._replace(
            cache_base=cache_base, git={"cache_ttl": 100}
        )
        calls = []

        def fake_run(cmd, **kw):
            del kw
            calls.append(cmd)

            class R:
                returncode = 0
                stdout = "## main\n" if "status" in cmd else ".git\n.git\n/repo\n"

            return R()

        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            common_probe.probe_git_snapshot(".", cfg)
            common_probe.probe_git_snapshot(".", cfg)
        self.assertEqual(sum("rev-parse" in c for c in calls), 1)  # only once

    def test_worktree_cache_bypassed_when_ttl_zero(self):
        env = self._home_env()
        cache_base = common_config.cfg_cache_base(env)
        cfg = common_config.cfg_default_config(claude_host.SPEC)._replace(
            cache_base=cache_base, git={"cache_ttl": 0}
        )
        calls = []

        def fake_run(cmd, **kw):
            del kw
            calls.append(cmd)

            class R:
                returncode = 0
                stdout = "## main\n" if "status" in cmd else ".git\n.git\n/repo\n"

            return R()

        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            common_probe.probe_git_snapshot(".", cfg)
            common_probe.probe_git_snapshot(".", cfg)
        self.assertEqual(sum("rev-parse" in c for c in calls), 2)  # ttl<=0 always runs

    def test_worktree_cache_not_written_when_ttl_zero(self):
        # ttl<=0 forces a fresh probe every render, so the cache file is never
        # read — it must therefore never be WRITTEN either (no wasted disk I/O on
        # the hot render path).
        env = self._home_env()
        cache_base = common_config.cfg_cache_base(env)
        cfg = common_config.cfg_default_config(claude_host.SPEC)._replace(
            cache_base=cache_base, git={"cache_ttl": 0}
        )

        def fake_run(cmd, **kw):
            del kw

            class R:
                returncode = 0
                stdout = "## main\n" if "status" in cmd else ".git\n.git\n/repo\n"

            return R()

        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            common_probe.probe_git_snapshot(".", cfg)
        self.assertFalse(os.path.exists(common_types.util_git_cache_path(".", cache_base)))


class TestCurrentTodo(unittest.TestCase):
    """probe_current_todo prefers Claude's materialized task/todo state on disk over
    replaying the transcript."""

    def _write(self, path, obj):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(obj, f)

    def test_pick_helpers(self):
        self.assertEqual(
            claude_probes.util_pick_from_tasks(
                [{"status": "in_progress", "activeForm": "Doing X", "subject": "X"}]
            ),
            ("in_progress", "Doing X"),
        )
        self.assertEqual(
            claude_probes.util_pick_from_tasks([{"status": "pending", "subject": "Y"}]),
            ("pending", "Y"),
        )
        self.assertIsNone(
            claude_probes.util_pick_from_tasks([{"status": "completed", "subject": "Z"}])
        )
        self.assertEqual(
            claude_probes.util_pick_from_todos([{"status": "in_progress", "activeForm": "Doing"}]),
            ("in_progress", "Doing"),
        )

    def test_reads_managed_tasks_dir(self):
        with tempfile.TemporaryDirectory() as cd:
            s = "sess1"
            self._write(
                os.path.join(cd, "tasks", s, "1.json"),
                {"id": "1", "subject": "first", "activeForm": "Doing first", "status": "completed"},
            )
            self._write(
                os.path.join(cd, "tasks", s, "2.json"),
                {
                    "id": "2",
                    "subject": "second",
                    "activeForm": "Doing second",
                    "status": "in_progress",
                },
            )
            self.assertEqual(
                claude_probes.probe_current_todo("", s, cd), ("in_progress", "Doing second")
            )

    def test_tasks_dir_all_done_is_authoritative(self):
        # Dir has files but none active -> (None, None); must NOT replay transcript.
        with tempfile.TemporaryDirectory() as cd:
            s = "sess2"
            self._write(
                os.path.join(cd, "tasks", s, "1.json"),
                {"id": "1", "subject": "x", "activeForm": "X", "status": "completed"},
            )
            with mock.patch.object(claude_probes, "probe_todo_from_transcript") as tr:
                result = claude_probes.probe_current_todo("/some/transcript.jsonl", s, cd)
                self.assertEqual(result, (None, None))
                tr.assert_not_called()

    def test_reads_todos_dir_when_no_tasks(self):
        with tempfile.TemporaryDirectory() as cd:
            s = "sess3"
            self._write(
                os.path.join(cd, "todos", f"{s}-agent-abc.json"),
                [{"status": "in_progress", "activeForm": "Todo active", "content": "c"}],
            )
            self.assertEqual(
                claude_probes.probe_current_todo("", s, cd), ("in_progress", "Todo active")
            )

    def test_falls_back_to_transcript(self):
        with tempfile.TemporaryDirectory() as cd:
            tp = os.path.join(cd, "t.jsonl")
            with open(tp, "w") as f:
                f.write(
                    json.dumps(
                        {
                            "message": {
                                "content": [
                                    {
                                        "type": "tool_use",
                                        "name": "TaskCreate",
                                        "input": {"subject": "A", "activeForm": "Doing A"},
                                    }
                                ]
                            }
                        }
                    )
                    + "\n"
                )
                f.write(
                    json.dumps(
                        {
                            "message": {
                                "content": [
                                    {
                                        "type": "tool_use",
                                        "name": "TaskUpdate",
                                        "input": {"taskId": 1, "status": "in_progress"},
                                    }
                                ]
                            }
                        }
                    )
                    + "\n"
                )
            # session has no materialized dirs under cd -> transcript replay
            self.assertEqual(
                claude_probes.probe_current_todo(tp, "nosession", cd), ("in_progress", "Doing A")
            )

    def test_tasks_dir_preferred_over_transcript(self):
        with tempfile.TemporaryDirectory() as cd:
            s = "sess4"
            self._write(
                os.path.join(cd, "tasks", s, "1.json"),
                {
                    "id": "1",
                    "subject": "win",
                    "activeForm": "From tasks dir",
                    "status": "in_progress",
                },
            )
            with mock.patch.object(claude_probes, "probe_todo_from_transcript") as tr:
                self.assertEqual(
                    claude_probes.probe_current_todo("/x.jsonl", s, cd),
                    ("in_progress", "From tasks dir"),
                )
                tr.assert_not_called()

    def test_safe_session_rejects_traversal(self):
        self.assertTrue(common_types.util_safe_session("b6de6c0c-9229-407f-9d33-b157970f2e9f"))
        for bad in ("../evil", "a/b", "..", r"a\b", ""):
            self.assertFalse(common_types.util_safe_session(bad), bad)

    def test_traversal_session_does_not_escape_dir(self):
        # A crafted session id with ../ must not read .json outside the tasks dir;
        # the materialized tiers bail and we fall through to the transcript.
        with tempfile.TemporaryDirectory() as cd:
            self._write(
                os.path.join(cd, "secret.json"), [{"status": "in_progress", "activeForm": "LEAK"}]
            )
            with mock.patch.object(
                claude_probes, "probe_todo_from_transcript", return_value=(None, None)
            ) as tr:
                self.assertEqual(claude_probes.probe_current_todo("", "../", cd), (None, None))
                tr.assert_called_once()  # fell through, did not traverse

    def test_no_session_goes_straight_to_transcript(self):
        patch_target = "probe_todo_from_transcript"
        with mock.patch.object(claude_probes, patch_target, return_value=("pending", "P")) as tr:
            self.assertEqual(claude_probes.probe_current_todo("/x.jsonl"), ("pending", "P"))
            tr.assert_called_once()


class TestEndToEnd(unittest.TestCase):
    def test_build_and_render(self):
        raw = {
            "model": {"display_name": "Opus 4.8", "id": "claude-opus-4-8"},
            "effort": {"level": "high"},
            "workspace": {"current_dir": os.getcwd()},
            "context_window": {"used_percentage": 47, "context_window_size": 1_000_000},
            "cost": {
                "total_lines_added": 12,
                "total_lines_removed": 3,
                "total_duration_ms": 65000,
                "total_api_duration_ms": 4200,
            },
        }
        env = {"STATUSLINE_COLS": "200", "STATUSLINE_LINES": "50", "HOME": "/home/u"}
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        data, _cols, _lines = _ctx_from_env(raw, env, cfg)
        out = common_render.core_render(data, claude_host.HOST)
        self.assertEqual(len(out), 3)
        self.assertIn("Opus 4.8", strip(out[1]))
        self.assertIn("47%", strip(out[1]))


class TestLazyCompute(unittest.TestCase):
    """A disabled segment skips its probe across the WHOLE render; an enabled one
    runs it exactly once, inside its measured build (FR-R.2 option A). Probes no
    longer run in build_data — they are deferred to the segment that reads them,
    so these drive the full build_data + render path."""

    RAW = {"workspace": {"current_dir": "."}, "transcript_path": ""}
    EFFORT_RAW = {
        "workspace": {"current_dir": "."},
        "transcript_path": "",
        "effort": {"level": "high"},
    }
    ENV = {"STATUSLINE_COLS": "200", "STATUSLINE_LINES": "50", "HOME": "/home/u"}

    def _build_and_render(self, segs, raw=None, cfg=None):
        if cfg is None:
            cfg = common_config.cfg_default_config(claude_host.SPEC)
        cfg.segments.clear()  # cfg is a namedtuple; mutate the dict
        cfg.segments.update(dict.fromkeys(claude_host.SEGMENTS, False))
        cfg.segments.update(segs)
        theme = common_render.core_build_theme(cfg, claude_host.HOST)
        # build_data is segment-agnostic; cfg.segments gates probes via render().
        data, _cols, _lines = _ctx_from_env(raw or self.RAW, self.ENV, cfg)
        common_render.core_render(data, claude_host.HOST, cfg, theme)
        return data

    def test_disabled_segments_skip_their_probes(self):
        with (
            mock.patch.object(common_probe, "probe_git_snapshot") as gi,
            mock.patch.object(claude_probes, "probe_current_todo") as ct,
            mock.patch.object(claude_probes, "probe_rss_bytes") as rss,
            mock.patch.object(claude_probes, "probe_effort_setting_is_auto") as ea,
        ):
            self._build_and_render(dict.fromkeys(claude_host.SEGMENTS, False))
            gi.assert_not_called()
            ct.assert_not_called()
            rss.assert_not_called()
            ea.assert_not_called()

    def test_enabled_segments_run_their_probes(self):
        segs = {"git_branch": True, "todo": True, "alt_process_memory": True, "effort": True}
        with (
            mock.patch.object(
                common_probe,
                "probe_git_snapshot",
                return_value=common_types.GitSnapshot(True, "m", "clean", False, ""),
            ) as gi,
            mock.patch.object(claude_probes, "probe_current_todo", return_value=(None, None)) as ct,
            mock.patch.object(claude_probes, "probe_rss_bytes", return_value=1) as rss,
            mock.patch.object(
                claude_probes, "probe_effort_setting_is_auto", return_value=True
            ) as ea,
        ):
            self._build_and_render(segs, raw=self.EFFORT_RAW)
            gi.assert_called_once()  # branch built -> git probe runs
            ct.assert_called_once()  # todo built  -> transcript parse runs
            rss.assert_called_once()  # memory built
            ea.assert_called_once()  # effort built (level present -> auto checked)

    def test_dirty_alone_still_triggers_git(self):
        # git_branch + git_dirty share one probe_git_snapshot call; either triggers it.
        with mock.patch.object(
            common_probe,
            "probe_git_snapshot",
            return_value=common_types.GitSnapshot(True, "", "modified", False, ""),
        ) as gi:
            self._build_and_render({"git_dirty": True})
            gi.assert_called_once()

    def test_none_segments_computes_everything(self):
        # build_data is segment-agnostic: it never gates by flag. Rendering an
        # all-on config fires the probes (here the todo parse).
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        theme = common_render.core_build_theme(cfg, claude_host.HOST)
        with (
            mock.patch.object(claude_probes, "probe_current_todo", return_value=(None, None)) as ct,
            mock.patch.object(
                common_probe,
                "probe_git_snapshot",
                return_value=common_types.GitSnapshot(True, "m", "clean", False, ""),
            ),
        ):
            data, _cols, _lines = _ctx_from_env(self.RAW, self.ENV, cfg)
            common_render.core_render(data, claude_host.HOST, cfg, theme)
            ct.assert_called_once()

    def test_git_ttl_threaded_to_snapshot(self):
        # The resolved [git] cache_ttl flows through build_data into probe_git_snapshot
        # via the Config object (D8 — consumers read cache_ttl off the object).
        cfg = common_config.cfg_default_config(claude_host.SPEC)._replace(git={"cache_ttl": 42})
        with mock.patch.object(
            common_probe,
            "probe_git_snapshot",
            return_value=common_types.GitSnapshot(True, "m", "clean", False, ""),
        ) as gs:
            self._build_and_render({"alt_git_worktree": True}, cfg=cfg)
            # probe_git_snapshot receives the config; the ttl is read off it.
            args = gs.call_args
            passed_cfg = args.args[1] if args.args[1:] else args.kwargs.get("config")
            assert passed_cfg is not None
            self.assertEqual((passed_cfg.git or {}).get("cache_ttl"), 42)

    def test_git_probe_fires_for_any_git_segment_agnostically(self):
        # build_data is segment-agnostic: probe_git_snapshot runs once whenever ANY of
        # git_branch/git_dirty/alt_git_worktree is built — in full (no per-segment
        # untracked/want_worktree flags threaded in) — and not at all when none are.
        for branch_on, dirty_on, wt_on in (
            (True, False, True),
            (True, False, False),
            (False, True, False),
            (False, False, True),
            (True, True, True),
        ):
            with mock.patch.object(
                common_probe,
                "probe_git_snapshot",
                return_value=common_types.GitSnapshot(True, "m", "clean", False, ""),
            ) as gi:
                self._build_and_render(
                    {"git_branch": branch_on, "git_dirty": dirty_on, "alt_git_worktree": wt_on}
                )
                gi.assert_called_once()
                # No segment-derived flags leak into the call (agnostic probe).
                self.assertNotIn("untracked", gi.call_args.kwargs)
                self.assertNotIn("want_worktree", gi.call_args.kwargs)

        with mock.patch.object(
            common_probe,
            "probe_git_snapshot",
            return_value=common_types.GitSnapshot(True, "m", "clean", False, ""),
        ) as gi:
            self._build_and_render(
                {"git_branch": False, "git_dirty": False, "alt_git_worktree": False}
            )
            gi.assert_not_called()  # no git segment built -> no probe


class TestBlueFix(unittest.TestCase):
    def test_blue_is_lightened_256color(self):
        # 1;34 bold-ANSI-blue reads purple on many terminals; use lightened 256-color blue.
        self.assertEqual(THEME.c("BLUE"), "\033[38;5;39m")

    def test_lightblue_defined_for_chat_ramp(self):
        self.assertEqual(THEME.c("LIGHTBLUE"), "\033[38;5;75m")

    def test_path_emits_true_blue_not_bold_ansi(self):
        out = common_segments.seg_path(_data(), 80, THEME)
        self.assertIn("38;5;39", out)
        self.assertNotIn("\033[1;34m", out)


class TestSegPathProjectRoot(unittest.TestCase):
    def test_shows_root_name_inside_a_repo(self):
        ctx = _data(
            in_repo=True, root_name="ai-kit", work_dir="/home/u/proj/.claude/worktrees/feat-x"
        )
        out = common_segments.seg_path(ctx, 80, THEME)
        self.assertIn("ai-kit", out)
        self.assertNotIn("feat-x", out)

    def test_ignores_cwd_depth_inside_a_repo(self):
        ctx = _data(
            in_repo=True, root_name="ai-kit", work_dir="/home/u/proj/very/deeply/nested/subdir"
        )
        out = common_segments.seg_path(ctx, 80, THEME)
        self.assertIn("ai-kit", out)

    def test_non_worktree_short_subdir_shows_root_not_old_cwd_display(self):
        # Regression pin for the deliberately widened scope (confirmed with the
        # user; see the plan's "Correction to / supersession of the sibling
        # design spec" section): a short subdirectory of the MAIN checkout
        # (not a worktree, and under PATH_MAX_LEN so the old code path never
        # truncated it) used to render via util_display_dir as "~/proj/tools".
        # It must now render the project root name instead, proving the
        # substitution applies to every git-repo session, not only worktrees.
        work_dir = "/home/u/proj/tools"
        home = "/home/u"
        old_display = common_types.util_display_dir(work_dir, home)
        self.assertEqual(old_display, "~/proj/tools")  # sanity: old behavior would show this
        ctx = _data(in_repo=True, root_name="proj", work_dir=work_dir, home=home)
        out = common_segments.seg_path(ctx, 80, THEME)
        self.assertIn("proj", out)
        self.assertNotIn(old_display, out)

    def test_truncates_long_root_name_when_root_path_unknown(self):
        # root_path unset (as every GitSnapshot built before Task 1 shipped,
        # or cache read from a pre-Task-1 disk cache) -> no structural
        # cascade is attempted; falls straight to the name floor
        # (util_two_state_cap(root_name, 30, 20)), which clips a 60-col name.
        long_name = "a" * 60
        ctx = _data(in_repo=True, root_name=long_name)
        out = common_segments.seg_path(ctx, 80, THEME)
        self.assertIn("…", out)
        self.assertNotIn(long_name, out)

    def test_shows_full_home_relative_root_path_when_short(self):
        ctx = _data(in_repo=True, root_name="proj", root_path="/home/u/proj", home="/home/u")
        out = common_segments.seg_path(ctx, 80, THEME)
        self.assertIn("~/proj", strip(out))

    def test_falls_to_parent_slash_name_when_full_path_too_long(self):
        # full (~/workspaces/very-long-organization-name-here/short-repo) is
        # 56 cols, over the 50 structural cap -> falls to parent/name (43
        # cols, fits).
        root_path = "/home/u/workspaces/very-long-organization-name-here/short-repo"
        ctx = _data(in_repo=True, root_name="short-repo", root_path=root_path, home="/home/u")
        out = common_segments.seg_path(ctx, 80, THEME)
        self.assertIn("very-long-organization-name-here/short-repo", strip(out))
        self.assertNotIn("~/workspaces", strip(out))

    def test_falls_to_root_name_unclipped_when_both_structural_forms_too_long(self):
        # full (73 cols) and parent/name (71 cols) both exceed the 50
        # structural cap; root_name alone ("short-name", 10 cols) fits the
        # 30-col name-floor high threshold, so it's shown unclipped.
        root_path = "/home/u/" + "a" * 60 + "/short-name"
        ctx = _data(in_repo=True, root_name="short-name", root_path=root_path, home="/home/u")
        out = common_segments.seg_path(ctx, 80, THEME)
        self.assertIn("short-name", strip(out))
        self.assertNotIn("…", strip(out))

    def test_falls_to_root_name_clipped_when_over_30(self):
        # full (88 cols) and parent/name (75 cols) both exceed the 50
        # structural cap; root_name alone ("another-very-long-repository-name",
        # 33 cols) exceeds the 30-col name-floor high threshold, so it's
        # clipped to 20.
        root_path = (
            "/home/u/workspaces/very-long-organization-name-here-extended"
            "/another-very-long-repository-name"
        )
        ctx = _data(
            in_repo=True,
            root_name="another-very-long-repository-name",
            root_path=root_path,
            home="/home/u",
        )
        out = common_segments.seg_path(ctx, 80, THEME)
        self.assertIn("another-very-long-r…", strip(out))
        self.assertNotIn("very-long-organization-name-here-extended/", strip(out))

    def test_shows_raw_absolute_root_path_when_not_under_home(self):
        # root_path doesn't start with ctx.home -> the home-relative "~"
        # substitution is skipped and the raw absolute root_path is used
        # verbatim as the first structural variant (design doc §3 edge case:
        # "Repo root not under ctx.home" falls back to the raw absolute path).
        ctx = _data(in_repo=True, root_name="proj", root_path="/mnt/other/proj", home="/home/u")
        out = common_segments.seg_path(ctx, 80, THEME)
        self.assertIn("/mnt/other/proj", strip(out))
        self.assertNotIn("~", strip(out))

    def test_falls_through_to_display_dir_when_root_name_empty(self):
        # in_repo=True but root_name=="" fails the `if snap.in_repo and
        # snap.root_name:` guard (pre-existing, unchanged by this plan) -> the
        # non-repo util_display_dir branch runs instead, exactly as it did
        # before this plan touched seg_path.
        ctx = _data(
            in_repo=True,
            root_name="",
            root_path="/home/u/proj",
            work_dir="/home/u/proj",
            home="/home/u",
        )
        out = common_segments.seg_path(ctx, 80, THEME)
        self.assertEqual(strip(out), common_types.util_display_dir("/home/u/proj", "/home/u"))

    def test_falls_back_to_cwd_outside_a_repo(self):
        ctx = _data(in_repo=False, work_dir="/home/u/scratch", home="/home/u")
        out = common_segments.seg_path(ctx, 80, THEME)
        self.assertIn(common_types.util_display_dir("/home/u/scratch", "/home/u"), out)


class TestProbeTranscriptCompaction(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write(self, lines):
        path = os.path.join(self.tmp, "transcript.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
        return path

    def test_no_boundary_since_equals_total(self):
        path = self._write(
            [
                json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}}),
                json.dumps(
                    {"type": "assistant", "message": {"role": "assistant", "content": "hey"}}
                ),
            ]
        )
        total = os.path.getsize(path)
        since, count = claude_probes.probe_transcript_compaction(path, total)
        self.assertEqual(count, 0)
        self.assertEqual(since, total)

    def test_one_boundary_since_is_tail_only(self):
        pre = json.dumps({"type": "user", "message": {"role": "user", "content": "long history"}})
        boundary = json.dumps(
            {
                "type": "system",
                "subtype": "compact_boundary",
                "compactMetadata": {"trigger": "manual", "preTokens": 100000, "postTokens": 500},
            }
        )
        post = json.dumps({"type": "user", "message": {"role": "user", "content": "new turn"}})
        path = self._write([pre, boundary, post])
        total = os.path.getsize(path)
        since, count = claude_probes.probe_transcript_compaction(path, total)
        self.assertEqual(count, 1)
        # since = the boundary line + everything after it, not the pre-boundary line
        expected_since = len((boundary + "\n" + post + "\n").encode("utf-8"))
        self.assertEqual(since, expected_since)
        self.assertLess(since, total)

    def test_three_boundaries_counted(self):
        boundary = json.dumps(
            {
                "type": "system",
                "subtype": "compact_boundary",
                "compactMetadata": {"trigger": "auto"},
            }
        )
        path = self._write([boundary, "x", boundary, "y", boundary, "z"])
        total = os.path.getsize(path)
        since, count = claude_probes.probe_transcript_compaction(path, total)
        self.assertEqual(count, 3)
        expected_since = len((boundary + "\nz\n").encode("utf-8"))
        self.assertEqual(since, expected_since)

    def test_malformed_boundary_shape_is_ignored(self):
        # matches the substring but wrong "type", and a non-JSON line — neither counts
        wrong_type = json.dumps({"type": "user", "subtype": "compact_boundary"})
        not_json = '{"subtype":"compact_boundary", not valid json'
        path = self._write([wrong_type, not_json])
        total = os.path.getsize(path)
        since, count = claude_probes.probe_transcript_compaction(path, total)
        self.assertEqual(count, 0)
        self.assertEqual(since, total)

    def test_missing_file_returns_total_zero(self):
        since, count = claude_probes.probe_transcript_compaction(
            os.path.join(self.tmp, "nonexistent.jsonl"), 12345
        )
        self.assertEqual((since, count), (12345, 0))


class TestChatSizeRamp(unittest.TestCase):
    KB = 1024
    MB = 1024 * 1024

    def test_ramp_bands(self):
        KB, MB = self.KB, self.MB
        cases = [
            (400 * KB, THEME.c("WHITE")),
            (512 * KB, THEME.c("CYAN")),
            (900 * KB, THEME.c("CYAN")),
            (1 * MB, THEME.c("LIGHTBLUE")),
            (1 * MB + 1, THEME.c("LIGHTBLUE")),
            (2 * MB, THEME.c("GREEN")),
            (3 * MB, THEME.c("YELLOW")),
            (4 * MB, THEME.c("ORANGE")),
            (5 * MB, THEME.c("RED+bold")),
            (5 * MB + 1, THEME.c("RED+bold")),
            (9 * MB, THEME.c("RED+bold")),
            (10 * MB, THEME.c("MAGENTA")),
            (20 * MB, THEME.c("MAGENTA")),
        ]
        for n, want in cases:
            self.assertEqual(common_types.util_pick_color(n, THEME.ramps["chat_size"]), want, n)

    def test_seg_chat_size_colors_the_size(self):
        out = claude_segments.seg_chat_size(_data(chat_bytes=6 * self.MB), 40, THEME)
        self.assertIn("💾", out)
        self.assertIn(THEME.c("RED+bold"), out)  # 6 MB -> red band

    def test_seg_chat_size_none_when_no_bytes(self):
        self.assertIsNone(claude_segments.seg_chat_size(_data(chat_bytes=None), 40, THEME))

    def test_never_compacted_shows_total_only_at_both_tiers(self):
        out_wide = strip(claude_segments.seg_chat_size(_data(chat_bytes=850_000), 200, THEME))
        out_narrow = strip(claude_segments.seg_chat_size(_data(chat_bytes=850_000), 40, THEME))
        self.assertEqual(out_wide, out_narrow)
        self.assertIn(common_types.fmt_bytes(850_000), out_wide)
        self.assertNotIn("/", out_wide)
        self.assertNotIn("x)", out_wide)

    def test_compacted_shows_since_over_total_with_count_when_room(self):
        out = strip(
            claude_segments.seg_chat_size(
                _data(chat_bytes=4_200_000, chat_since=320_000, chat_compactions=3), 200, THEME
            )
        )
        self.assertIn(
            f"{common_types.fmt_bytes(320_000)}/{common_types.fmt_bytes(4_200_000)} (3x)", out
        )

    def test_compacted_drops_to_since_only_when_narrow(self):
        out = strip(
            claude_segments.seg_chat_size(
                _data(chat_bytes=4_200_000, chat_since=320_000, chat_compactions=3), 12, THEME
            )
        )
        self.assertEqual(out, f"💾 {common_types.fmt_bytes(320_000)}")

    def test_ramp_color_driven_by_since_not_total(self):
        # 6 MB total but only 900 KB since last compaction -> CYAN band, not RED
        out = claude_segments.seg_chat_size(
            _data(chat_bytes=6 * self.MB, chat_since=900 * self.KB, chat_compactions=1), 200, THEME
        )
        self.assertIn(THEME.c("CYAN"), out)
        self.assertNotIn(THEME.c("RED+bold"), out)


class TestEffortAutoSetting(unittest.TestCase):
    def test_auto_appends_bracket_when_room(self):
        out = strip(claude_segments.seg_effort(_data(effort="high", effort_auto=True), 40, THEME))
        self.assertIn("high", out)
        self.assertIn("[auto]", out)

    def test_resolved_level_keeps_its_color_in_auto(self):
        out = claude_segments.seg_effort(_data(effort="high", effort_auto=True), 40, THEME)
        self.assertIn(f"{THEME.c('YELLOW')}high", out)  # level keeps its fixed color

    def test_auto_compacts_to_asterisk_when_tight(self):
        out = strip(claude_segments.seg_effort(_data(effort="medium", effort_auto=True), 18, THEME))
        self.assertIn("medium*", out)
        self.assertNotIn("[auto]", out)

    def test_non_auto_has_no_annotation(self):
        out = strip(claude_segments.seg_effort(_data(effort="high", effort_auto=False), 40, THEME))
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
        self.assertTrue(claude_probes.probe_effort_setting_is_auto(proj, home))

    def test_explicit_user_level_is_not_auto(self):
        proj, home = self._dirs()
        self._write(home, "settings.json", {"effortLevel": "high"})
        self.assertFalse(claude_probes.probe_effort_setting_is_auto(proj, home))

    def test_literal_auto_value_is_auto(self):
        proj, home = self._dirs()
        self._write(home, "settings.json", {"effortLevel": "auto"})
        self.assertTrue(claude_probes.probe_effort_setting_is_auto(proj, home))

    def test_project_setting_wins_over_user(self):
        proj, home = self._dirs()
        self._write(home, "settings.json", {"effortLevel": "auto"})
        self._write(proj, "settings.json", {"effortLevel": "high"})
        self.assertFalse(claude_probes.probe_effort_setting_is_auto(proj, home))

    def test_keyless_file_falls_through_to_next(self):
        proj, home = self._dirs()
        self._write(proj, "settings.local.json", {"model": "opus"})  # present, no effortLevel
        self._write(home, "settings.json", {"effortLevel": "max"})
        self.assertFalse(claude_probes.probe_effort_setting_is_auto(proj, home))

    def test_local_json_wins_over_project_and_user(self):
        proj, home = self._dirs()
        self._write(proj, "settings.local.json", {"effortLevel": "high"})
        self._write(proj, "settings.json", {"effortLevel": "auto"})
        self._write(home, "settings.json", {"effortLevel": "auto"})
        self.assertFalse(claude_probes.probe_effort_setting_is_auto(proj, home))


class TestResolveEffort(unittest.TestCase):
    def test_level_auto_normalized_away(self):
        # "auto" is a *setting*, never a resolved level — it must not survive here.
        self.assertEqual(claude_payload.cfg_resolve_effort({"effort": {"level": "auto"}}), "")

    def test_case_normalized(self):
        self.assertEqual(claude_payload.cfg_resolve_effort({"effort": {"level": "HIGH"}}), "high")

    def test_missing_is_empty(self):
        # FR-1.9: effort resolves from JSON + settings only; no CLAUDE_EFFORT env source.
        self.assertEqual(claude_payload.cfg_resolve_effort({}), "")


class TestProcRssLinux(unittest.TestCase):
    def test_returns_none_when_no_claude_ancestor(self):
        # the wezterm bug: walk finds no `claude`, must return None (not a stray RSS)
        comm = {10: "zsh", 11: "wezterm-gui", 1: "systemd"}
        ppid = {10: 11, 11: 1, 1: 0}
        with (
            mock.patch.object(os.path, "isdir", return_value=True),
            mock.patch.object(os, "getppid", return_value=10),
            mock.patch.object(claude_probes, "probe_comm_via_proc", side_effect=comm.get),
            mock.patch.object(claude_probes, "probe_ppid_via_proc", side_effect=ppid.get),
            mock.patch.object(claude_probes, "probe_rss_kb_via_proc", side_effect=lambda p: 5000),
        ):
            self.assertIsNone(claude_probes.probe_rss_bytes())

    def test_returns_rss_when_claude_found(self):
        comm = {10: "zsh", 11: "claude", 1: "systemd"}
        ppid = {10: 11, 11: 1, 1: 0}
        with (
            mock.patch.object(os.path, "isdir", return_value=True),
            mock.patch.object(os, "getppid", return_value=10),
            mock.patch.object(claude_probes, "probe_comm_via_proc", side_effect=comm.get),
            mock.patch.object(claude_probes, "probe_ppid_via_proc", side_effect=ppid.get),
            mock.patch.object(
                claude_probes,
                "probe_rss_kb_via_proc",
                side_effect=lambda p: 204800 if p == 11 else 5000,
            ),
        ):
            self.assertEqual(claude_probes.probe_rss_bytes(), 204800 * 1024)


class TestProcRssMacOS(unittest.TestCase):
    def test_ps_fallback_when_no_proc(self):
        comm = {10: "login", 11: "claude", 1: "launchd"}
        ppid = {10: 11, 11: 1, 1: 0}
        rss = {11: 307200, 10: 100}
        with (
            mock.patch.object(os.path, "isdir", return_value=False),
            mock.patch.object(os, "getppid", return_value=10),
            mock.patch.object(claude_probes, "probe_comm_via_ps", side_effect=comm.get),
            mock.patch.object(claude_probes, "probe_ppid_via_ps", side_effect=ppid.get),
            mock.patch.object(claude_probes, "probe_rss_kb_via_ps", side_effect=rss.get),
        ):
            self.assertEqual(claude_probes.probe_rss_bytes(), 307200 * 1024)

    def test_ps_field_parses_one_value(self):
        class R:
            stdout = "  12345\n"

        with mock.patch.object(subprocess, "run", return_value=R()):
            self.assertEqual(common_probe.probe_ps_field(99, "rss"), "12345")


class TestTputFallback(unittest.TestCase):
    def test_tput_used_when_stty_yields_nothing(self):
        def fake_run(cmd, **kw):
            del kw

            class R:
                stdout = ""

            r = R()
            if cmd[:1] == ["stty"]:
                r.stdout = ""  # stty size unavailable
            elif cmd == ["tput", "cols"]:
                r.stdout = "123\n"
            elif cmd == ["tput", "lines"]:
                r.stdout = "44\n"
            return r

        with (
            mock.patch.object(subprocess, "run", side_effect=fake_run),
            mock.patch("builtins.open", mock.mock_open(read_data="")),
        ):
            cols, lines, assumed = common_probe.probe_terminal_size({})
        self.assertEqual((cols, lines), (123, 44))
        self.assertFalse(assumed)


class TestConfigScaffold(unittest.TestCase):
    def test_default_config_matches_globals(self):
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        self.assertEqual(cfg.segments, dict(claude_host.SEGMENTS))
        self.assertEqual(cfg.layout, list(claude_host.LAYOUT))
        self.assertEqual(cfg.palette, {})

    def test_default_config_is_a_snapshot(self):
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        cfg.segments["alt_time_clock"] = not cfg.segments["alt_time_clock"]
        self.assertNotEqual(
            cfg.segments["alt_time_clock"], claude_host.SEGMENTS["alt_time_clock"]
        )  # snapshot, not alias


class TestEnvBool(unittest.TestCase):
    def test_env_bool_via_coerce(self):
        for v in ("1", "true", "t", "y", "yes", "on", "TRUE", "On"):
            self.assertEqual(common_config.cfg_coerce(v, "bool", "env", "X"), (True, None), v)
        for v in ("0", "false", "f", "n", "no", "off", "OFF"):
            self.assertEqual(common_config.cfg_coerce(v, "bool", "env", "X"), (False, None), v)
        self.assertEqual(common_config.cfg_coerce("maybe", "bool", "env", "X"), (None, None))
        self.assertEqual(common_config.cfg_coerce("", "bool", "env", "X"), (None, None))

    def test_cfg_warn_format(self):
        """cfg_warn wraps a core message in the fixed dim render-format on stderr."""
        from contextlib import redirect_stderr

        buf = io.StringIO()
        with redirect_stderr(buf):
            common_config.cfg_warn("segment 'x' must be true/false, got 'maybe' — ignored")
        expected = (
            f"{common_types.DIM}status-line: segment 'x' must be true/false, "
            f"got 'maybe' — ignored{common_types.RESET}\n"
        )
        self.assertEqual(buf.getvalue(), expected)


class TestCfgCoerce(unittest.TestCase):
    def test_cfg_coerce_env_bool(self):
        self.assertEqual(common_config.cfg_coerce("yes", "bool", "env", "X"), (True, None))
        self.assertEqual(common_config.cfg_coerce("OFF", "bool", "env", "X"), (False, None))
        # unrecognized env bool is tri-state no-override (silent), NOT a problem:
        self.assertEqual(common_config.cfg_coerce("maybe", "bool", "env", "X"), (None, None))
        self.assertEqual(common_config.cfg_coerce("", "bool", "env", "X"), (None, None))

    def test_cfg_coerce_env_int(self):
        self.assertEqual(
            common_config.cfg_coerce("10", "int", "env", "CC_AI_KIT_GIT_CACHE_TTL"), (10, None)
        )
        v, prob = common_config.cfg_coerce("x", "int", "env", "CC_AI_KIT_GIT_CACHE_TTL")
        self.assertIsNone(v)
        self.assertEqual(prob, "CC_AI_KIT_GIT_CACHE_TTL must be an integer, got 'x' — ignored")

    def test_cfg_coerce_toml_bool(self):
        self.assertEqual(
            common_config.cfg_coerce(True, "bool", "toml", "segment 'alt_cost'"), (True, None)
        )
        # a TOML STRING for a bool key is rejected (strict) — NOT parsed like env:
        v, prob = common_config.cfg_coerce("true", "bool", "toml", "segment 'alt_cost'")
        self.assertIsNone(v)
        self.assertEqual(prob, "segment 'alt_cost' must be true/false, got 'true' — ignored")

    def test_cfg_coerce_toml_int(self):
        self.assertEqual(common_config.cfg_coerce(5, "int", "toml", "[git] cache_ttl"), (5, None))
        # bool is not an int here:
        v, prob = common_config.cfg_coerce(True, "int", "toml", "[git] cache_ttl")
        self.assertIsNone(v)
        self.assertEqual(prob, "[git] cache_ttl must be an integer, got True — ignored")


class TestCfgSourceGet(unittest.TestCase):
    def test_cfg_source_get_env_projection(self):
        env = {"CC_AI_KIT_GIT_CACHE_TTL": "9", "CC_AI_KIT_SEGMENT_ALT_COST": "1"}
        self.assertEqual(
            common_config.cfg_source_get(
                "env", {}, env, ("git", "cache_ttl"), claude_host.SPEC.env_prefix
            ),
            "9",
        )
        self.assertEqual(
            common_config.cfg_source_get(
                "env", {}, env, ("segments", "alt_cost"), claude_host.SPEC.env_prefix
            ),
            "1",
        )
        self.assertIsNone(
            common_config.cfg_source_get(
                "env", {}, env, ("git", "missing"), claude_host.SPEC.env_prefix
            )
        )

    def test_cfg_source_get_toml_nested(self):
        raw = {"git": {"cache_ttl": 7}, "segments": {"alt_cost": True}}
        self.assertEqual(
            common_config.cfg_source_get(
                "toml", raw, {}, ("git", "cache_ttl"), claude_host.SPEC.env_prefix
            ),
            7,
        )
        self.assertIs(
            common_config.cfg_source_get(
                "toml", raw, {}, ("segments", "alt_cost"), claude_host.SPEC.env_prefix
            ),
            True,
        )
        self.assertIsNone(
            common_config.cfg_source_get(
                "toml", raw, {}, ("git", "missing"), claude_host.SPEC.env_prefix
            )
        )


class TestCfgBind(unittest.TestCase):
    def test_single_reader_auto_extends(self):
        """FR-6 proof: a NEW typed field binds via the generic access/convert layer
        with NO env-reader edits — cfg_source_get projects the name, cfg_coerce types it."""
        raw = {"newgroup": {"flag": True}}
        env = {"CC_AI_KIT_NEWGROUP_FLAG": "off"}
        self.assertEqual(
            common_config.cfg_source_get(
                "toml", raw, env, ("newgroup", "flag"), claude_host.SPEC.env_prefix
            ),
            True,
        )
        self.assertEqual(
            common_config.cfg_source_get(
                "env", raw, env, ("newgroup", "flag"), claude_host.SPEC.env_prefix
            ),
            "off",
        )
        self.assertEqual(common_config.cfg_coerce("off", "bool", "env", "X"), (False, None))

    def test_cfg_bind_scalars_precedence_and_problems(self):
        raw = {"git": {"cache_ttl": 8}}
        # env overrides git cache_ttl; default is 5, TOML(8) already applied by caller,
        # env(12) wins here.
        git, ext_dir, ext_ttl, probs = common_config.cfg_bind_scalars(
            raw,
            {"CC_AI_KIT_GIT_CACHE_TTL": "12"},
            {"cache_ttl": 8},
            "/d",
            10,
            claude_host.SPEC.env_prefix,
        )
        self.assertEqual(git["cache_ttl"], 12)
        self.assertEqual((ext_dir, ext_ttl), ("/d", 10))
        self.assertEqual(probs, [])
        # env external dir + ttl override
        _git2, ext_dir2, ext_ttl2, probs2 = common_config.cfg_bind_scalars(
            raw,
            {"CC_AI_KIT_EXTERNAL_DIR": "/x", "CC_AI_KIT_EXTERNAL_CACHE_TTL": "20"},
            {"cache_ttl": 8},
            "/d",
            10,
            claude_host.SPEC.env_prefix,
        )
        self.assertEqual((ext_dir2, ext_ttl2), ("/x", 20))
        self.assertEqual(probs2, [])
        # invalid env int -> falls back AND records a problem
        _, _, _, probs3 = common_config.cfg_bind_scalars(
            raw,
            {"CC_AI_KIT_GIT_CACHE_TTL": "x"},
            {"cache_ttl": 8},
            "/d",
            10,
            claude_host.SPEC.env_prefix,
        )
        self.assertIn("CC_AI_KIT_GIT_CACHE_TTL must be an integer, got 'x' — ignored", probs3)

    def test_cfg_bind_segments_env_override(self):
        segs, probs = common_config.cfg_bind_segments(
            {},
            {"CC_AI_KIT_SEGMENT_ALT_COST": "0"},
            {"alt_cost": True, "path": True},
            claude_host.SPEC.env_prefix,
        )
        self.assertIs(segs["alt_cost"], False)  # env override applied
        self.assertIs(segs["path"], True)  # untouched
        self.assertEqual(probs, [])
        # unknown segment env key -> silently skipped (not a known key)
        segs2, probs2 = common_config.cfg_bind_segments(
            {}, {"CC_AI_KIT_SEGMENT_BOGUS": "1"}, {"alt_cost": True}, claude_host.SPEC.env_prefix
        )
        self.assertNotIn("bogus", segs2)
        self.assertEqual(probs2, [])
        # env bad-bool stays silent (tri-state): unrecognized string -> no override, no problem
        segs3, probs3 = common_config.cfg_bind_segments(
            {},
            {"CC_AI_KIT_SEGMENT_ALT_COST": "maybe"},
            {"alt_cost": True},
            claude_host.SPEC.env_prefix,
        )
        self.assertIs(segs3["alt_cost"], True)
        self.assertEqual(probs3, [])


class TestConfigPathAndLoad(unittest.TestCase):
    def test_alternate_host_prefix_selects_config_and_segment(self):
        spec = common_types.ConfigSpec(
            "XX_",
            "other.toml",
            claude_host.SEGMENTS,
            claude_host.LAYOUT,
            claude_host.RAMP_DEFAULTS_CLAUDE,
            "segments",
            "segments",
            "XX_SEGMENT_",
        )
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as handle:
            handle.write("[segments]\\npath = true\\n")
            path = handle.name
        self.addCleanup(os.unlink, path)
        env = {
            "XX_CONFIG_FILE": path,
            "XX_SEGMENT_PATH": "0",
            "CC_AI_KIT_SEGMENT_PATH": "1",
            "HOME": "/h",
        }
        self.assertEqual(common_config.cfg_config_path(env, spec), path)
        self.assertFalse(common_config.cfg_load_config(env, spec).segments["path"])

    def test_explicit_path_wins(self):
        env = {"CC_AI_KIT_CONFIG_FILE": "/tmp/x.toml", "HOME": "/home/u"}
        self.assertEqual(common_config.cfg_config_path(env, claude_host.SPEC), "/tmp/x.toml")

    def test_xdg_path(self):
        env = {"XDG_CONFIG_HOME": "/cfg", "HOME": "/home/u"}
        self.assertEqual(
            common_config.cfg_config_path(env, claude_host.SPEC),
            "/cfg/ai-kit/claude-statusline.toml"
        )

    def test_home_default_path(self):
        env = {"HOME": "/home/u"}
        self.assertEqual(
            common_config.cfg_config_path(env, claude_host.SPEC),
            "/home/u/.config/ai-kit/claude-statusline.toml",
        )

    def test_missing_file_is_empty(self):
        self.assertEqual(common_config.cfg_load_toml("/no/such/file.toml"), {})

    def test_malformed_file_is_empty_no_crash(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("this is = = not toml")
            path = f.name
        try:
            self.assertEqual(common_config.cfg_load_toml(path), {})
        finally:
            os.unlink(path)

    def test_valid_file_parses(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("[segments]\ncost = true\n")
            path = f.name
        try:
            self.assertEqual(common_config.cfg_load_toml(path), {"segments": {"cost": True}})
        finally:
            os.unlink(path)


class TestResolveSegments(unittest.TestCase):
    def _write(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(body)
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_defaults_when_no_file_no_env(self):
        env = {"CC_AI_KIT_CONFIG_FILE": "/no/such.toml", "HOME": "/h"}
        cfg = common_config.cfg_load_config(env, claude_host.SPEC)
        self.assertEqual(cfg.segments, dict(claude_host.SEGMENTS))
        self.assertEqual(cfg.layout, list(claude_host.LAYOUT))
        self.assertEqual(cfg.palette, {})

    def test_file_overrides_default(self):
        path = self._write("[segments]\nalt_cost = true\nalt_process_memory = false\n")
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": path, "HOME": "/h"}, claude_host.SPEC
        )
        self.assertTrue(cfg.segments["alt_cost"])  # default False -> True
        self.assertFalse(cfg.segments["alt_process_memory"])  # default False, still False
        self.assertTrue(cfg.segments["model"])  # untouched default (non-alt)

    def test_env_overrides_file(self):
        path = self._write("[segments]\nalt_cost = true\n")
        env = {"CC_AI_KIT_CONFIG_FILE": path, "HOME": "/h", "CC_AI_KIT_SEGMENT_ALT_COST": "0"}
        cfg = common_config.cfg_load_config(env, claude_host.SPEC)
        self.assertFalse(cfg.segments["alt_cost"])  # env beats file

    def test_unknown_segment_key_ignored(self):
        path = self._write("[segments]\nbogus = true\n")
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": path, "HOME": "/h"}, claude_host.SPEC
        )
        self.assertNotIn("bogus", cfg.segments)

    def test_wrong_type_value_ignored(self):
        # `alt_cost = "true"` (string, not bool) is a known key but a bad value:
        # it must be dropped (keeping the default), not silently coerced.
        path = self._write('[segments]\nalt_cost = "true"\n')
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": path, "HOME": "/h"}, claude_host.SPEC
        )
        self.assertEqual(cfg.segments["alt_cost"], claude_host.SEGMENTS["alt_cost"])  # default kept

    def test_render_silent_on_broken_config(self):
        """cfg_load_config emits NOTHING to stderr even when env/TOML has bad values."""
        from contextlib import redirect_stderr

        env = {"CC_AI_KIT_GIT_CACHE_TTL": "not-an-int", "CC_AI_KIT_SEGMENT_NOPE": "1"}
        buf = io.StringIO()
        with redirect_stderr(buf):
            cfg = common_config.cfg_load_config(env, claude_host.SPEC)
        self.assertEqual(buf.getvalue(), "")
        self.assertEqual(cfg.git["cache_ttl"], common_types.GIT_CACHE_TTL)

    def test_verbose_reports_problems(self):
        """cfg_load_config_verbose returns problems without printing."""
        env = {"CC_AI_KIT_GIT_CACHE_TTL": "not-an-int"}
        _, problems = common_config.cfg_load_config_verbose(env, claude_host.SPEC)
        self.assertIn(
            "CC_AI_KIT_GIT_CACHE_TTL must be an integer, got 'not-an-int' — ignored",
            problems,
        )


class TestGitConfig(unittest.TestCase):
    def _write(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(body)
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_cache_ttl_default_5(self):
        # Default [git] config carries cache_ttl=5 and nothing else.
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": "/no/such.toml", "HOME": "/h"}, claude_host.SPEC
        )
        self.assertEqual(cfg.git, {"cache_ttl": 5})

    def test_cache_ttl_from_toml(self):
        path = self._write("[git]\ncache_ttl = 20\n")
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": path, "HOME": "/h"}, claude_host.SPEC
        )
        self.assertEqual(cfg.git["cache_ttl"], 20)

    def test_cache_ttl_env_overrides_toml(self):
        # Precedence: default 5 < TOML [git] cache_ttl < env CC_AI_KIT_GIT_CACHE_TTL.
        path = self._write("[git]\ncache_ttl = 20\n")
        env = {"CC_AI_KIT_CONFIG_FILE": path, "HOME": "/h", "CC_AI_KIT_GIT_CACHE_TTL": "99"}
        self.assertEqual(common_config.cfg_load_config(env, claude_host.SPEC).git["cache_ttl"], 99)

    def test_cache_ttl_env_over_default(self):
        env = {
            "CC_AI_KIT_CONFIG_FILE": "/no/such.toml",
            "HOME": "/h",
            "CC_AI_KIT_GIT_CACHE_TTL": "0",
        }
        self.assertEqual(common_config.cfg_load_config(env, claude_host.SPEC).git["cache_ttl"], 0)

    def test_cache_ttl_bad_toml_type_ignored(self):
        path = self._write('[git]\ncache_ttl = "soon"\n')  # string, not int
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": path, "HOME": "/h"}, claude_host.SPEC
        )
        self.assertEqual(cfg.git["cache_ttl"], 5)  # default kept; render is silent

    def test_worktree_env_no_longer_read(self):
        # CC_AI_KIT_GIT_WORKTREE is retired — setting it does not affect cfg.git.
        env = {
            "CC_AI_KIT_CONFIG_FILE": "/no/such.toml",
            "HOME": "/h",
            "CC_AI_KIT_GIT_WORKTREE": "1",
        }
        self.assertEqual(common_config.cfg_load_config(env, claude_host.SPEC).git, {"cache_ttl": 5})

    def test_unknown_git_key_ignored_silently(self):
        path = self._write("[git]\nbogus = true\n")
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": path, "HOME": "/h"}, claude_host.SPEC
        )
        self.assertNotIn("bogus", cfg.git)  # bogus dropped; render is silent


class TestWorktreeSegmentToggle(unittest.TestCase):
    """The worktree feature is now a segment toggle, ON by default."""

    def _write(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(body)
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_worktree_segment_off_by_default(self):
        # alt_git_worktree is opt-in (OFF by default) since the alt_* default flip.
        self.assertIs(claude_host.SEGMENTS.get("alt_git_worktree"), False)
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": "/no/such.toml", "HOME": "/h"}, claude_host.SPEC
        )
        self.assertFalse(cfg.segments["alt_git_worktree"])

    def test_worktree_segment_disable_via_toml(self):
        path = self._write("[segments]\nalt_git_worktree = false\n")
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": path, "HOME": "/h"}, claude_host.SPEC
        )
        self.assertFalse(cfg.segments["alt_git_worktree"])

    def test_worktree_segment_disable_via_env(self):
        env = {
            "CC_AI_KIT_CONFIG_FILE": "/no/such.toml",
            "HOME": "/h",
            "CC_AI_KIT_SEGMENT_ALT_GIT_WORKTREE": "0",
        }
        self.assertFalse(
            common_config.cfg_load_config(env, claude_host.SPEC).segments["alt_git_worktree"]
        )


class TestRenderWithConfig(unittest.TestCase):
    def test_pack_line_honors_cfg_segments(self):
        cfg = common_types.Config(
            segments={**claude_host.SEGMENTS, "alt_time_clock": False},
            layout=list(claude_host.LAYOUT),
            palette={},
            ramps={},
        )
        out = strip(_pack(["model", "alt_time_clock"], _data(), 200, cfg))
        self.assertNotIn("⏰", out)
        self.assertIn("Opus 4.8", out)

    def test_render_honors_cfg_layout(self):
        cfg = common_types.Config(
            segments=dict(claude_host.SEGMENTS),
            layout=[common_types.Line(0, ["model"])],
            palette={},
            ramps={},
        )
        lines = common_render.core_render(_data(), claude_host.HOST, cfg)
        self.assertEqual(len(lines), 1)
        self.assertIn("Opus 4.8", strip(lines[0]))

    def test_render_default_cfg_unchanged(self):
        # No cfg arg -> same as today (three rows when tall+wide).
        self.assertEqual(len(common_render.core_render(_data(), claude_host.HOST)), 3)


class TestMainUsesConfig(unittest.TestCase):
    def _run_main(self, raw, env):
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with (
            mock.patch.object(sys, "stdin", io.StringIO(json.dumps(raw))),
            mock.patch.object(sys, "argv", ["claude-status-line.py"]),
            mock.patch.dict(os.environ, env, clear=True),
            redirect_stdout(buf),
        ):
            common_render.main(claude_host.HOST)
        return buf.getvalue()

    def test_segment_hidden_via_env(self):
        raw = {
            "workspace": {"current_dir": "/tmp"},
            "model": {"display_name": "Opus"},
            "context_window": {"used_percentage": 10},
        }
        # PATH is preserved: build_data shells out to `git` (unguarded), and
        # clear=True would otherwise strip it and crash main().
        env = {
            "HOME": "/tmp",
            "STATUSLINE_COLS": "200",
            "STATUSLINE_LINES": "50",
            "PATH": os.environ.get("PATH", ""),
            "CC_AI_KIT_SEGMENT_ALT_TIME_CLOCK": "0",
            "CC_AI_KIT_CONFIG_FILE": "/no/such.toml",
        }
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
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": "/no/such.toml", "HOME": "/h"}, claude_host.SPEC
        )
        self.assertEqual(cfg.layout, list(claude_host.LAYOUT))

    def test_line_replaces_layout(self):
        path = self._write(
            '[[line]]\nmin_rows = 0\nsegments = ["path", "model"]\n'
            '[[line]]\nmin_rows = 25\nsegments = ["context"]\n'
        )
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": path, "HOME": "/h"}, claude_host.SPEC
        )
        self.assertEqual(
            cfg.layout,
            [common_types.Line(0, ["path", "model"]), common_types.Line(25, ["context"])],
        )

    def test_line_missing_min_rows_defaults_zero(self):
        path = self._write('[[line]]\nsegments = ["path"]\n')
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": path, "HOME": "/h"}, claude_host.SPEC
        )
        self.assertEqual(cfg.layout, [common_types.Line(0, ["path"])])


class TestPaletteFromConfig(unittest.TestCase):
    def _write(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(body)
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_palette_parsed_into_config(self):
        path = self._write('[palette]\nBLUE = "1;34"\n')
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": path, "HOME": "/h"}, claude_host.SPEC
        )
        self.assertEqual(cfg.palette, {"BLUE": "1;34"})

    def test_unknown_palette_key_dropped(self):
        path = self._write('[palette]\nNOTACOLOR = "1;34"\n')
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": path, "HOME": "/h"}, claude_host.SPEC
        )
        self.assertEqual(cfg.palette, {})

    def test_main_applies_palette(self):
        from contextlib import redirect_stdout

        path = self._write('[palette]\nBLUE = "1;34"\n')
        raw = {
            "workspace": {"current_dir": "/tmp"},
            "model": {"display_name": "Opus"},
            "context_window": {"used_percentage": 10},
        }
        env = {
            "HOME": "/tmp",
            "STATUSLINE_COLS": "200",
            "STATUSLINE_LINES": "50",
            "PATH": os.environ.get("PATH", ""),  # keep PATH so git in build_data resolves
            "CC_AI_KIT_CONFIG_FILE": path,
        }
        buf = io.StringIO()
        with (
            mock.patch.object(sys, "stdin", io.StringIO(json.dumps(raw))),
            mock.patch.object(sys, "argv", ["claude-status-line.py"]),
            mock.patch.dict(os.environ, env, clear=True),
            redirect_stdout(buf),
        ):
            common_render.main(claude_host.HOST)
        # path segment is BLUE; overridden blue (1;34) must appear in the raw output.
        self.assertIn("\033[1;34m", buf.getvalue())


class TestSampleRecipe(unittest.TestCase):
    SAMPLE = os.path.join(_HERE, "..", "tools", "claude-statusline.toml.sample")

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
        self.assertEqual(parsed.get("segments"), dict(claude_host.SEGMENTS))
        want = [{"min_rows": ln.min_rows, "segments": ln.segments} for ln in claude_host.LAYOUT]
        self.assertEqual(parsed.get("line"), want)
        # The [palette] block documents every overridable color with its real
        # default; assert it so the recipe can't silently drift from the code.
        self.assertEqual(parsed.get("palette"), dict(common_types.PALETTE_DEFAULTS))
        # [ramp.*] blocks document the real default tables.
        want_ramps = {
            band: {str(thr): spec for thr, spec in pairs}
            for band, pairs in claude_host.RAMP_DEFAULTS_CLAUDE.items()
        }
        self.assertEqual(parsed.get("ramp"), want_ramps)
        # [git] knobs document their real defaults too.
        self.assertEqual(parsed.get("git"), dict(common_types.GIT_DEFAULTS))


class TestParseColor(unittest.TestCase):
    PAL = {"RED": "31", "BLUE": "38;5;39", "ORANGE": "38;5;208"}

    def test_palette_name(self):
        self.assertEqual(common_types.util_parse_color("RED", self.PAL), "\033[31m")
        self.assertEqual(common_types.util_parse_color("BLUE", self.PAL), "\033[38;5;39m")

    def test_raw_sgr_passthrough(self):
        self.assertEqual(common_types.util_parse_color("38;5;33"), "\033[38;5;33m")
        self.assertEqual(common_types.util_parse_color("1;31"), "\033[1;31m")

    def test_hex_six(self):
        self.assertEqual(common_types.util_parse_color("#3399ff"), "\033[38;2;51;153;255m")

    def test_hex_short_expands(self):
        self.assertEqual(common_types.util_parse_color("#39f"), "\033[38;2;51;153;255m")

    def test_hex_alpha_stripped(self):
        self.assertEqual(common_types.util_parse_color("#3399ffcc"), "\033[38;2;51;153;255m")

    def test_modifier_bold_on_name(self):
        self.assertEqual(common_types.util_parse_color("RED+bold", self.PAL), "\033[1;31m")

    def test_modifier_on_hex(self):
        self.assertEqual(common_types.util_parse_color("#3399ff+bold"), "\033[1;38;2;51;153;255m")

    def test_modifiers_canonical_order(self):
        # underline(4)+bold(1) -> ascending 1;4 regardless of input order
        self.assertEqual(
            common_types.util_parse_color("RED+underline+bold", self.PAL), "\033[1;4;31m"
        )

    def test_all_modifiers(self):
        self.assertEqual(
            common_types.util_parse_color("RED+bold+dim+italic+underline", self.PAL),
            "\033[1;2;3;4;31m",
        )

    def test_unknown_name_is_none(self):
        self.assertIsNone(common_types.util_parse_color("NOTACOLOR", self.PAL))

    def test_name_without_palette_is_none(self):
        self.assertIsNone(common_types.util_parse_color("RED"))

    def test_unknown_modifier_is_none(self):
        self.assertIsNone(common_types.util_parse_color("RED+blink", self.PAL))

    def test_bad_hex_is_none(self):
        self.assertIsNone(common_types.util_parse_color("#zzz"))
        self.assertIsNone(common_types.util_parse_color("#12345"))  # 5 nibbles, not 3/6/8

    def test_empty_is_none(self):
        self.assertIsNone(common_types.util_parse_color(""))
        self.assertIsNone(common_types.util_parse_color(None))


class TestParseThreshold(unittest.TestCase):
    def test_percent_int(self):
        self.assertEqual(common_types.util_parse_threshold(10), 10)
        self.assertEqual(common_types.util_parse_threshold("25"), 25)

    def test_inf(self):
        self.assertEqual(common_types.util_parse_threshold("inf"), float("inf"))
        self.assertEqual(common_types.util_parse_threshold(float("inf")), float("inf"))

    def test_byte_suffixes(self):
        self.assertEqual(common_types.util_parse_threshold("512k"), 512 * 1024)
        self.assertEqual(common_types.util_parse_threshold("5M"), 5 * 1024 * 1024)
        self.assertEqual(common_types.util_parse_threshold("1G"), 1024**3)

    def test_time_suffixes(self):
        # render_time thresholds resolve to nanoseconds
        self.assertEqual(common_types.util_parse_threshold("100ns"), 100)
        self.assertEqual(common_types.util_parse_threshold("500us"), 500_000)
        self.assertEqual(common_types.util_parse_threshold("500µs"), 500_000)
        self.assertEqual(common_types.util_parse_threshold("50ms"), 50_000_000)
        self.assertEqual(common_types.util_parse_threshold("2s"), 2_000_000_000)

    def test_bad_key_raises(self):
        with self.assertRaises(ValueError):
            common_types.util_parse_threshold("nonsense")
        with self.assertRaises(ValueError):
            common_types.util_parse_threshold("5MB")  # only single-letter k/M/G suffix


class TestTheme(unittest.TestCase):
    def test_c_resolves_and_memoizes(self):
        t = common_render.core_default_theme(claude_host.HOST)
        first = t.c("RED")
        self.assertTrue(first.startswith("\033["))
        self.assertEqual(t.c("RED"), first)  # same object/value, cached
        self.assertIn("RED", t._cache)

    def test_c_modifier(self):
        t = common_render.core_default_theme(claude_host.HOST)
        self.assertEqual(t.c("RED+bold"), common_types.util_parse_color("RED+bold", t.palette))

    def test_c_invalid_is_empty_string(self):
        t = common_render.core_default_theme(claude_host.HOST)
        self.assertEqual(t.c("NOTACOLOR"), "")  # never raises, no color


class TestBuildTheme(unittest.TestCase):
    def _cfg(self, palette=None, ramps=None):
        return common_types.Config(
            segments=dict(claude_host.SEGMENTS),
            layout=list(claude_host.LAYOUT),
            palette=palette or {},
            ramps=ramps or {},
        )

    def test_palette_merges_over_defaults(self):
        t = common_render.core_build_theme(self._cfg(palette={"BLUE": "1;34"}), claude_host.HOST)
        self.assertEqual(t.palette["BLUE"], "1;34")
        self.assertEqual(t.palette["RED"], common_types.PALETTE_DEFAULTS["RED"])  # untouched

    def test_palette_hex_override_resolved_to_params(self):
        t = common_render.core_build_theme(self._cfg(palette={"BLUE": "#3399ff"}), claude_host.HOST)
        self.assertEqual(t.palette["BLUE"], "38;2;51;153;255")

    def test_bad_palette_value_keeps_default(self):
        t = common_render.core_build_theme(self._cfg(palette={"BLUE": "#zzz"}), claude_host.HOST)
        self.assertEqual(t.palette["BLUE"], common_types.PALETTE_DEFAULTS["BLUE"])

    def test_ramp_replaced_whole(self):
        t = common_render.core_build_theme(
            self._cfg(ramps={"rate": {"50": "GREEN", "inf": "RED"}}), claude_host.HOST
        )
        self.assertEqual([c for _, c in t.ramps["rate"]], [t.c("GREEN"), t.c("RED")])
        self.assertEqual([ceil for ceil, _ in t.ramps["rate"]], [50, float("inf")])

    def test_unspecified_ramp_keeps_default(self):
        t = common_render.core_build_theme(
            self._cfg(ramps={"rate": {"inf": "RED"}}), claude_host.HOST
        )
        self.assertEqual(len(t.ramps["context"]), len(claude_host.RAMP_DEFAULTS_CLAUDE["context"]))

    def test_bad_band_color_falls_back_to_default_band(self):
        # context default band at ceil 10 is WHITE; a bad override color for that
        # band falls back to the default band's resolved color.
        bad = {"10": "NOPE", "inf": "RED"}
        t = common_render.core_build_theme(self._cfg(ramps={"context": bad}), claude_host.HOST)
        self.assertEqual(t.ramps["context"][0], (10, t.c("WHITE")))

    def test_bad_threshold_keeps_whole_default_ramp(self):
        t = common_render.core_build_theme(
            self._cfg(ramps={"context": {"oops": "RED"}}), claude_host.HOST
        )
        self.assertEqual(
            t.ramps["context"], common_render.core_default_theme(claude_host.HOST).ramps["context"]
        )

    def test_effort_derives_from_palette(self):
        t = common_render.core_default_theme(claude_host.HOST)
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
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": path, "HOME": "/h"}, claude_host.SPEC
        )
        self.assertEqual(cfg.ramps, {"rate": {"50": "GREEN", "inf": "RED+bold"}})

    def test_unknown_ramp_dropped(self):
        path = self._write('[ramp.bogus]\n10 = "RED"\n')
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": path, "HOME": "/h"}, claude_host.SPEC
        )
        self.assertEqual(cfg.ramps, {})

    def test_no_ramp_block_is_empty(self):
        cfg = common_config.cfg_load_config(
            {"CC_AI_KIT_CONFIG_FILE": "/no/such.toml", "HOME": "/h"}, claude_host.SPEC
        )
        self.assertEqual(cfg.ramps, {})


class TestRendererRobustness(unittest.TestCase):
    def test_doctor_cmd_is_concrete(self):
        cmd = common_render.core_doctor_cmd("--doctor")
        # A copy-pasteable command, not a bare flag: ends with --doctor, names a
        # python executable, and references the sibling doctor script (introspection
        # moved out of the render module in Phase 4).
        self.assertTrue(cmd.endswith("--doctor"), cmd)
        self.assertIn("statusline-doctor.py", cmd)
        self.assertRegex(cmd, r"^\S*python\S*\s")

    def test_warn_is_an_sgr_code(self):
        self.assertTrue(common_types.WARN.startswith("\033["))
        self.assertTrue(common_types.WARN.endswith("m"))

    def test_safe_build_passes_through_ok_builder(self):
        def good(data, avail, theme):
            del avail
            return "HELLO"

        ctx = _data()
        with mock.patch.dict(claude_host.BUILDERS, {"path": good}):
            out = common_render.core_safe_build("path", ctx, 40, THEME, claude_host.BUILDERS)
        self.assertEqual(out, "HELLO")
        self.assertEqual(ctx.failed, set())

    def test_safe_build_records_and_marks_on_raise(self):
        def boom(data, avail, theme):
            del avail
            raise RuntimeError("kaboom")

        ctx = _data()
        with mock.patch.dict(claude_host.BUILDERS, {"path": boom}):
            out = common_render.core_safe_build("path", ctx, 40, THEME, claude_host.BUILDERS)
        self.assertIn("path", ctx.failed)
        self.assertIn("path", strip(out))  # name shown when width allows
        self.assertLessEqual(common_types.util_visible_width(out), 40)

    def test_safe_build_bare_marker_when_no_room_for_name(self):
        def boom(data, avail, theme):
            del avail
            raise RuntimeError("x")

        ctx = _data()
        with mock.patch.dict(claude_host.BUILDERS, {"context": boom}):
            out = common_render.core_safe_build("context", ctx, 1, THEME, claude_host.BUILDERS)
        self.assertIn("context", ctx.failed)
        self.assertNotIn("context", strip(out))  # name dropped, icon kept

    def test_pack_line_survives_a_raising_pinned_builder(self):
        # "path" is PINNED — even when its builder raises, the line still renders
        # the other segments and records the failure.
        def boom(data, avail, theme):
            del avail
            raise ValueError("nope")

        cfg = common_config.cfg_default_config(claude_host.SPEC)

        def ok(data, avail, theme):
            del avail
            return "CTX"

        ctx = _data()
        with mock.patch.dict(claude_host.BUILDERS, {"path": boom, "context": ok}):
            line = _pack(["path", "context"], ctx, 80, cfg, THEME)
        self.assertIn("path", ctx.failed)
        self.assertIn("CTX", strip(line))  # the healthy segment still shows

    def test_diagnostic_line_none_when_no_failures(self):
        self.assertIsNone(
            common_render.core_diagnostic_line(set(), common_render.core_doctor_cmd("--doctor"))
        )

    def test_diagnostic_line_lists_failures_and_doctor(self):
        line = strip(
            common_render.core_diagnostic_line(
                {"git", "context"}, common_render.core_doctor_cmd("--doctor")
            )
        )
        self.assertIn("2 segments failed", line)
        self.assertIn("context, git", line)  # sorted
        self.assertIn("--doctor", line)

    def test_render_appends_diagnostic_on_builder_crash(self):
        def boom(data, avail, theme):
            del avail
            raise RuntimeError("x")

        cfg = common_config.cfg_default_config(claude_host.SPEC)
        layout = [common_types.Line(0, ["path"])]
        cfg = cfg._replace(layout=layout)
        with mock.patch.dict(claude_host.BUILDERS, {"path": boom}):
            out = common_render.core_render(_data(cols=80, lines=40), claude_host.HOST, cfg, THEME)
        self.assertTrue(any("--doctor" in strip(l) for l in out))
        self.assertTrue(any("path" in strip(l) for l in out))

    def test_render_no_diagnostic_when_healthy(self):
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        out = common_render.core_render(_data(cols=80, lines=40), claude_host.HOST, cfg, THEME)
        self.assertFalse(any("--doctor" in strip(l) for l in out))

    def test_registry_rejects_duplicate_segment_id(self):
        first = type("First", (), {"seg_x": staticmethod(lambda *_args: "a")})
        second = type("Second", (), {"seg_x": staticmethod(lambda *_args: "b")})
        with self.assertRaisesRegex(ValueError, "seg_x|duplicate segment id: x"):
            common_render.core_discover_builders(first, second)

    def test_safe_render_returns_diagnostic_on_catastrophic_failure(self):
        with mock.patch.object(
            claude_payload, "core_build_context", side_effect=RuntimeError("boom")
        ) as adapter:
            out = common_render.safe_render(claude_host.HOST, {}, os.environ, 0)
        adapter.assert_called_once()
        self.assertEqual(len(out), 1)
        self.assertIn("status-line error", strip(out[0]))
        self.assertIn("--doctor", strip(out[0]))

    def test_safe_render_normal_path(self):
        out = common_render.safe_render(claude_host.HOST, {}, os.environ, 0)
        self.assertIsInstance(out, list)
        self.assertFalse(any("status-line error" in strip(l) for l in out))

    def test_entry_bad_layout_renders_error_line(self):
        with tempfile.TemporaryDirectory(prefix="bad-layout-") as root:
            os.makedirs(os.path.join(root, "home"))
            with open(os.path.join(root, "entry.toml"), "w", encoding="utf-8") as stream:
                stream.write('[[line]]\nmin_rows = "x"\nsegments = ["path"]\n')
            output = run_entry(root, "{}")
        plain = strip(output).strip()
        self.assertTrue(plain.startswith("⚠ status-line error"), plain)
        self.assertEqual(len(output.splitlines()), 1)

    # A fresh /clear session sends context_window/cost PRESENT but with null inner
    # fields (no tokens/cost accrued yet). dict.get(k, default) returns None for a
    # present-but-null key, so int()/math on it raised inside build_data and the
    # whole bar collapsed to "status-line error". Coalesce null -> 0 instead.
    _NEW_SESSION_RAW = {
        "model": {"display_name": "Opus", "id": "claude-opus-4-8"},
        "workspace": {"current_dir": "."},
        "transcript_path": "",
        "context_window": {"used_percentage": None, "context_window_size": None},
        "cost": {
            "total_lines_added": None,
            "total_lines_removed": None,
            "total_cost_usd": None,
            "total_duration_ms": None,
            "total_api_duration_ms": None,
        },
    }

    def test_build_data_tolerates_present_but_null_fields(self):
        data, _cols, _lines = _ctx_from_env(
            dict(self._NEW_SESSION_RAW),
            os.environ,
            common_config.cfg_default_config(claude_host.SPEC),
        )
        self.assertEqual(data.context_pct, 0)
        self.assertEqual(data.context_max, 0)
        claude_data = claude_payload.core_claude_data(data)
        self.assertEqual(claude_data.added, 0)
        self.assertEqual(claude_data.removed, 0)
        self.assertEqual(claude_data.cost, 0)
        self.assertEqual(claude_data.total_ms, 0)
        self.assertEqual(claude_data.api_ms, 0)

    def test_render_new_session_no_error_no_warn(self):
        out = common_render.safe_render(
            claude_host.HOST, dict(self._NEW_SESSION_RAW), os.environ, 0
        )
        text = "\n".join(strip(l) for l in out)
        self.assertNotIn("status-line error", text)
        self.assertNotIn("⚠", text)  # no per-segment crashes either
        self.assertTrue(text.strip())  # and the bar is not blank


class TestRenderDataLazy(unittest.TestCase):
    """FR-R.2 (option A): expensive probes run inside the measured build of the
    segment that reads them, not eagerly in build_data — so the cost is captured
    by core_safe_build's timing and the shared probe still runs at most once."""

    def test_git_probe_deferred_to_render_and_runs_once(self):
        snap = common_types.GitSnapshot(True, "main", "modified", False, "")
        raw = {"workspace": {"current_dir": "/repo"}, "session_id": "s"}
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        theme = common_render.core_build_theme(cfg, claude_host.HOST)
        with mock.patch.object(common_probe, "probe_git_snapshot", return_value=snap) as gs:
            data, _cols, _lines = _ctx_from_env(raw, {"HOME": "/h"}, cfg)
            self.assertEqual(gs.call_count, 0, "git probe must NOT run during build_data")
            common_render.core_render(data, claude_host.HOST, cfg, theme)
            self.assertEqual(gs.call_count, 1, "git probe runs exactly once during render")

    def test_disabled_git_segments_skip_the_probe(self):
        raw = {"workspace": {"current_dir": "/repo"}}
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        # path is now also a git consumer (renders the project-root name), so
        # zero git probes requires disabling it too, not just the git_* segments.
        cfg.segments["path"] = False
        cfg.segments["git_branch"] = False
        cfg.segments["git_dirty"] = False
        cfg.segments["alt_git_worktree"] = False
        theme = common_render.core_build_theme(cfg, claude_host.HOST)
        with mock.patch.object(common_probe, "probe_git_snapshot") as gs:
            data, _cols, _lines = _ctx_from_env(raw, {"HOME": "/h"}, cfg)
            common_render.core_render(data, claude_host.HOST, cfg, theme)
            self.assertEqual(gs.call_count, 0, "no git-consuming segment enabled => no git probe")


class TestSlowestTruthful(unittest.TestCase):
    """FR-R.2 acceptance: `slowest` names a real contributor whose cost is the
    same order of magnitude as the render — ms-scale, not the µs of a cache hit."""

    def test_slowest_captures_probe_cost_not_microseconds(self):
        raw = {"workspace": {"current_dir": "/repo"}, "session_id": "s"}
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        theme = common_render.core_build_theme(cfg, claude_host.HOST)

        def slow_git(*_a, **_k):  # a 20ms git status
            time.sleep(0.02)
            return common_types.GitSnapshot(True, "main", "modified", False, "")

        with mock.patch.object(common_probe, "probe_git_snapshot", side_effect=slow_git):
            data, _cols, _lines = _ctx_from_env(raw, {"HOME": "/h"}, cfg)
            common_render.core_render(data, claude_host.HOST, cfg, theme)
        name, ns = data.slowest
        # path renders first in line order and is now also a git consumer, so
        # it — not git_branch — is the one that actually pays the probe cost.
        self.assertIn(name, ("path", "git_branch", "git_dirty", "alt_git_worktree"))
        self.assertGreater(ns, 1_000_000)  # >1ms, not µs


class TestTwoPassLayout(unittest.TestCase):
    """FR-R.3: a measured pass times every non-meta segment, then assembly places
    render_time/slowest at their LAYOUT positions — so slowest no longer has to be
    last on its line and sits adjacent to render_time by default."""

    def _diag_line(self):
        raw = {
            "workspace": {"current_dir": "/repo"},
            "session_id": "s",
            "cost": {"total_cost_usd": 0.5},
        }
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        theme = common_render.core_build_theme(cfg, claude_host.HOST)
        with mock.patch.object(
            common_probe,
            "probe_git_snapshot",
            return_value=common_types.GitSnapshot(True, "main", "modified", False, ""),
        ):
            data, _c, _l = _ctx_from_env(raw, {"HOME": "/h"}, cfg, t_start=time.perf_counter_ns())
            out = common_render.core_render(data, claude_host.HOST, cfg, theme)
        return next(strip(l) for l in out if "⏱" in strip(l))

    def test_slowest_adjacent_to_render_time(self):
        diag = self._diag_line()
        i, j = diag.index("⏱"), diag.index("🐌")
        self.assertGreater(j, i)  # slowest comes after render_time
        self.assertNotIn("📊", diag[i:j])  # context not wedged between them

    def test_slowest_not_forced_last_in_layout(self):
        line = next(l for l in claude_host.LAYOUT if "slowest" in l.segments)
        self.assertNotEqual(line.segments[-1], "slowest")
        self.assertEqual(line.segments.index("slowest"), line.segments.index("render_time") + 1)


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
        snap = common_types.GitSnapshot(
            in_repo=True, branch="main", dirty="modified", is_worktree=False, wt_name=""
        )
        with (
            mock.patch.object(time, "strftime", return_value="14:30"),
            mock.patch.object(time, "time", return_value=NOW),
            mock.patch.object(common_probe, "probe_git_snapshot", return_value=snap),
            mock.patch.object(claude_probes, "probe_rss_bytes", return_value=448_790_528),
            mock.patch.object(claude_probes, "probe_transcript_bytes", return_value=305_000),
            mock.patch.object(claude_probes, "probe_current_todo", return_value=(None, None)),
            mock.patch.object(claude_probes, "probe_effort_setting_is_auto", return_value=False),
        ):
            yield

    def _render_all(self):
        with open(os.path.join(self.GOLDEN, "inputs.json"), encoding="utf-8") as f:
            cases = json.load(f)
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        # The meta segments report the render itself and are inherently
        # non-deterministic (render_time / slowest durations) and are exactly what
        # the restructure changes — exclude them so the golden guards only the
        # non-meta segment output it is meant to protect.
        cfg.segments["render_time"] = False
        cfg.segments["slowest"] = False
        theme = common_render.core_build_theme(cfg, claude_host.HOST)
        blocks = []
        with self._deterministic():
            for c in cases:
                env = {
                    **self.ENV,
                    "STATUSLINE_COLS": str(c["cols"]),
                    "STATUSLINE_LINES": str(c["lines"]),
                }
                data, _cols, _lines = _ctx_from_env(c["raw"], env, cfg, t_start=None)
                out = common_render.core_render(data, claude_host.HOST, cfg, theme)
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


def entry_env(root):
    """Return the complete, isolated environment for an entry subprocess."""
    return {
        "HOME": os.path.join(root, "home"),
        "PATH": os.environ.get("PATH", ""),
        "XDG_CONFIG_HOME": os.path.join(root, "home", ".config"),
        "XDG_CACHE_HOME": os.path.join(root, "home", ".cache"),
        "TZ": "UTC",
        "LANG": "C.UTF-8",
        "GIT_CEILING_DIRECTORIES": root,
        "STATUSLINE_COLS": "120",
        "STATUSLINE_LINES": "40",
        "CC_AI_KIT_CONFIG_FILE": os.path.join(root, "entry.toml"),
    }


def run_entry(root, payload_text, extra_env=None):
    script = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "tools", "claude-status-line.py")
    )
    result = subprocess.run(
        [sys.executable, "-S", script],
        input=payload_text,
        capture_output=True,
        text=True,
        cwd=root,
        env={**entry_env(root), **(extra_env or {})},
        timeout=20,
    )
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout


def render_full_cases():
    """Render the six full-segment oracle cases with raw ANSI preserved."""
    golden = os.path.join(os.path.dirname(__file__), "fixtures", "golden")
    with open(os.path.join(golden, "inputs_full.json"), encoding="utf-8") as source:
        cases = json.load(source)
    fd, transcript = tempfile.mkstemp(prefix="statusline-oracle-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write('{"type":"user","message":{"content":"hello"}}\n')
            stream.write('{"type":"system","subtype":"compact_boundary"}\n')
        os.utime(transcript, (NOW - 300, NOW - 300))
        cfg = common_config.cfg_default_config(claude_host.SPEC)
        for key in cfg.segments:
            cfg.segments[key] = key not in {"render_time", "slowest"}
        theme = common_render.core_build_theme(cfg, claude_host.HOST)
        blocks = []
        with (
            mock.patch.object(time, "strftime", return_value="14:30"),
            mock.patch.object(time, "time", return_value=NOW),
            mock.patch.object(claude_probes, "probe_rss_bytes", return_value=448_790_528),
        ):
            for case in cases:
                oracle_root = os.path.join(tempfile.gettempdir(), "ai-kit-statusline-golden")
                home = os.path.join(oracle_root, "home")
                os.makedirs(home, exist_ok=True)
                if case["raw"]:
                    case["raw"]["workspace"]["current_dir"] = os.path.join(home, "project")
                git_values = dict(case["git"])
                git_values["root_path"] = os.path.join(home, "project")
                git = common_types.GitSnapshot(**git_values)
                todo = ("in_progress", "Write the oracle") if case["raw"] else (None, None)
                raw = json.loads(json.dumps(case["raw"]).replace("<TRANSCRIPT>", transcript))
                env = {
                    "HOME": home,
                    "TZ": "UTC",
                    "LANG": "C.UTF-8",
                    "STATUSLINE_COLS": str(case["cols"]),
                    "STATUSLINE_LINES": str(case["lines"]),
                }
                old_cwd = os.getcwd()
                cwd = (os.path.join(oracle_root, "a" * 80, "01", "oracle-cwd")
                       if not case["raw"] else os.path.join(home, "project"))
                os.makedirs(cwd, exist_ok=True)
                with (
                    mock.patch.object(common_probe, "probe_git_snapshot", return_value=git),
                    mock.patch.object(claude_probes, "probe_current_todo", return_value=todo),
                    mock.patch.object(
                        claude_probes,
                        "probe_effort_setting_is_auto",
                        return_value=case["effort_auto"],
                    ),
                ):
                    try:
                        os.chdir(cwd)
                        def hermetic_expanduser(path, _home=home):
                            if path.startswith("~/"):
                                return os.path.join(_home, path[2:])
                            if path == "~":
                                return _home
                            if path.startswith(_home + os.sep):
                                return "~" + path[len(_home):]
                            return path

                        with mock.patch.object(
                            os.path, "expanduser", side_effect=hermetic_expanduser
                        ):
                            ctx, _, _ = _ctx_from_env(raw, env, cfg, t_start=None)
                            output = common_render.core_render(ctx, claude_host.HOST, cfg, theme)
                    finally:
                        os.chdir(old_cwd)
                blocks.append(f"### {case['name']}\n" + "\n".join(output))
        return "\n\n".join(blocks) + "\n"
    finally:
        with contextlib.suppress(OSError):
            os.unlink(transcript)


class TestFullGoldenAnsi(unittest.TestCase):
    def test_matches_raw_ansi_golden_deterministically(self):
        golden = os.path.join(
            os.path.dirname(__file__), "fixtures", "golden", "expected_full_ansi.txt"
        )
        first = render_full_cases()
        self.assertEqual(first, render_full_cases())
        with open(golden, encoding="utf-8") as source:
            self.assertEqual(first, source.read())


class TestEntryRender(unittest.TestCase):
    def test_entry_output_matches_fixture(self):
        with tempfile.TemporaryDirectory(prefix="entry-render-") as root:
            home = os.path.join(root, "home")
            os.makedirs(os.path.join(home, "proj"))
            transcript = os.path.join(home, "t.jsonl")
            with open(transcript, "w", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(
                        {
                            "type": "assistant",
                            "message": {
                                "content": [
                                    {
                                        "type": "tool_use",
                                        "name": "TodoWrite",
                                        "input": {
                                            "todos": [
                                                {
                                                    "content": "Write oracle",
                                                    "activeForm": "Writing oracle",
                                                    "status": "in_progress",
                                                }
                                            ]
                                        },
                                    }
                                ]
                            },
                        }
                    )
                    + "\n"
                )
                stream.write('{"type":"system","subtype":"compact_boundary"}\n')
            config = """[segments]
path=true
git_branch=false
git_dirty=false
alt_git_worktree=false
model=true
effort=true
context=true
todo=true
lines=true
alt_cost=true
alt_time_session=true
alt_time_api=true
chat_size=true
alt_h_rate_limit=true
alt_w_rate_limit=true
alt_term_dimensions=true
render_time=false
slowest=false
alt_time_clock=false
alt_time_ago=false
alt_process_memory=false
"""
            with open(os.path.join(root, "entry.toml"), "w", encoding="utf-8") as stream:
                stream.write(config)
            with open(
                os.path.join(os.path.dirname(__file__), "fixtures", "golden", "entry_payload.json"),
                encoding="utf-8",
            ) as stream:
                payload = stream.read().replace("<ROOT>", root)
            actual = run_entry(root, payload)
            golden = os.path.join(
                os.path.dirname(__file__), "fixtures", "golden", "entry_render.txt"
            )
            with open(golden, encoding="utf-8") as stream:
                self.assertEqual(actual, stream.read())


class TestStrictProviderCapture(unittest.TestCase):
    def test_provider_input_environment_and_cache_match_fixture(self):
        with tempfile.TemporaryDirectory(prefix="provider-capture-") as root:
            home = os.path.join(root, "home")
            workspace = os.path.join(home, "proj")
            os.makedirs(workspace)
            os.makedirs(os.path.join(home, ".config", "ai-kit", "segments"))
            transcript = os.path.join(home, "t.jsonl")
            with open(transcript, "w", encoding="utf-8") as stream:
                stream.write('{"type":"system","subtype":"compact_boundary"}\n')
            config = """[segments]
path=true
git_branch=false
git_dirty=false
alt_git_worktree=false
model=true
effort=true
context=true
todo=true
lines=true
alt_cost=true
alt_time_session=true
alt_time_api=true
chat_size=true
alt_h_rate_limit=true
alt_w_rate_limit=true
alt_term_dimensions=false
render_time=false
slowest=false
alt_time_clock=false
alt_time_ago=false
alt_process_memory=false
"""
            config_path = os.path.join(root, "entry.toml")
            with open(config_path, "w", encoding="utf-8") as stream:
                stream.write(config)
            provider = os.path.join(home, ".config", "ai-kit", "segments", "strict_probe")
            script = (
                f"#!{sys.executable}\n"
                "# ai-kit-segment: line=3 after=chat_size id=strict_probe ttl=0\n"
                "import json, os, sys\n"
                "text = sys.stdin.read()\n"
                "record = {'stdin': text, 'env_keys': sorted(os.environ), "
                "'cwd_is_workspace': os.path.realpath(os.getcwd()) == "
                "os.path.realpath(json.loads(text)['workspace']['current_dir'])}\n"
                "json.dump(record, open(os.environ['STRICT_PROBE_OUT'], 'w'))\n"
                "print('probe')\n"
            )
            with open(provider, "w", encoding="utf-8") as stream:
                stream.write(script)
            os.chmod(provider, 0o755)
            payload = {
                "model": {"id": "entry-model", "display_name": "Entry Model"},
                "workspace": {"current_dir": workspace},
                "transcript_path": transcript,
                "session_id": "strict-probe",
            }
            payload_text = json.dumps(payload)
            record_path = os.path.join(root, "probe.json")
            env = {
                **entry_env(root),
                "CC_AI_KIT_CONFIG_FILE": config_path,
                "STRICT_PROBE_OUT": record_path,
            }
            script_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "tools", "claude-status-line.py")
            )
            result = subprocess.run(
                [sys.executable, "-S", script_path],
                input=payload_text,
                capture_output=True,
                text=True,
                cwd=root,
                env=env,
                timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("probe", result.stdout)
            with open(record_path, encoding="utf-8") as stream:
                record = json.load(stream)
            cache_file = os.path.join(home, ".cache", "ai-kit", "segments", "strict_probe")
            with open(cache_file, encoding="utf-8") as stream:
                cache_text = stream.read()
            capture = {
                "stdin": record["stdin"].replace(root, "<TMP>"),
                "env_keys": record["env_keys"],
                "cwd_is_workspace": record["cwd_is_workspace"],
                "cache_relpath": os.path.relpath(cache_file, os.path.join(home, ".cache")),
                "cache_text": cache_text,
            }
            expected = os.path.join(
                os.path.dirname(__file__), "fixtures", "golden", "strict_provider_capture.json"
            )
            with open(expected, encoding="utf-8") as stream:
                self.assertEqual(capture, json.load(stream))


class TestThinContext(unittest.TestCase):
    def test_root_has_claude_json_and_line_conf(self):
        ctx = _data()
        self.assertTrue(hasattr(ctx, "line_conf"))
        self.assertIsInstance(ctx.line_conf, common_types.Config)
        self.assertTrue(hasattr(ctx, "cols"))
        self.assertEqual(ctx.model_name, "Opus 4.8")

    def test_no_single_consumer_probe_fields(self):
        ctx = _data()
        for gone in (
            "ago",
            "effort_auto",
            "chat_bytes",
            "mem_bytes",
            "branch",
            "dirty",
            "is_worktree",
            "wt_name",
            "todo_state",
            "todo_text",
        ):
            self.assertNotIn(gone, type(ctx).__dict__, f"{gone} must no longer be a ctx member")


class TestGitProbeMemoized(unittest.TestCase):
    def test_probe_git_for_runs_once_per_render(self):
        calls = []

        def fake(work_dir, _conf):
            calls.append(work_dir)
            return common_types.GitSnapshot(
                in_repo=True, branch="main", dirty="clean", is_worktree=False, wt_name=""
            )

        # Use a fresh context without pre-seeded probe_cache so the probe fires.
        ctx = claude_payload.core_build_context(
            raw={"workspace": {"current_dir": "/tmp"}},
            config=common_config.cfg_default_config(claude_host.SPEC),
            theme=THEME,
            cols=200,
            lines=50,
            dim_assumed=False,
            t_start=None,
            effort="high",
            home="/home/u",
            claude_dir="/home/u/.claude",
        )
        with mock.patch.object(common_probe, "probe_git_snapshot", side_effect=fake):
            snap1 = common_probe.probe_git_for(ctx)
            snap2 = common_probe.probe_git_for(ctx)
        self.assertEqual(snap1.branch, "main")
        self.assertIs(snap1, snap2)
        self.assertEqual(len(calls), 1)


class TestEnvConvention(unittest.TestCase):
    """FR-1.6/1.7/1.8: all config env reading funnels through one structure-aware reader."""

    def test_git_cache_ttl_via_convention(self):
        cfg = common_config.cfg_load_config(
            {"HOME": "/h", "CC_AI_KIT_GIT_CACHE_TTL": "42"}, claude_host.SPEC
        )
        self.assertEqual(cfg.git["cache_ttl"], 42)

    def test_segment_toggle_via_convention(self):
        cfg = common_config.cfg_load_config(
            {"HOME": "/h", "CC_AI_KIT_SEGMENT_GIT_BRANCH": "false"}, claude_host.SPEC
        )
        self.assertFalse(cfg.segments["git_branch"])

    def test_external_dir_via_convention(self):
        cfg = common_config.cfg_load_config(
            {"HOME": "/h", "CC_AI_KIT_EXTERNAL_DIR": "/x/seg"}, claude_host.SPEC
        )
        # cfg.external is an ExternalConf; FR-1.6 routes EXTERNAL_DIR -> external.dir
        self.assertEqual(cfg.external.dir, "/x/seg")

    def test_external_cache_ttl_via_convention(self):
        cfg = common_config.cfg_load_config(
            {"HOME": "/h", "CC_AI_KIT_EXTERNAL_CACHE_TTL": "30"}, claude_host.SPEC
        )
        self.assertEqual(cfg.external.cache_ttl, 30)


class TestAltSegmentsDefaultOff(unittest.TestCase):
    def test_every_alt_segment_defaults_off(self):
        for key, val in claude_host.SEGMENTS.items():
            if key.startswith("alt_"):
                self.assertFalse(val, f"{key} must default OFF (alt_* are opt-in)")


class TestProcessMemoryRename(unittest.TestCase):
    def test_renamed_key_present_old_absent(self):
        self.assertIn("alt_process_memory", claude_host.SEGMENTS)
        self.assertNotIn("alt_system_memory", claude_host.SEGMENTS)
        self.assertTrue(hasattr(claude_segments, "seg_alt_process_memory"))
        self.assertFalse(hasattr(claude_segments, "seg_alt_system_memory"))


class TestRendererHeaderIgnoresUIKeys(unittest.TestCase):
    def test_core_parser_ignores_name_description_icon_sample(self):
        head = ["# ai-kit-segment: id=x line=1 icon=💻 name=N description=D sample=S\n"]
        fields = common_config.core_parse_segment_header(head)
        self.assertEqual(fields.get("id"), "x")
        self.assertEqual(fields.get("line"), "1")
        for ui_key in ("name", "description", "icon", "sample"):
            self.assertNotIn(ui_key, fields, f"renderer parser must ignore UI key {ui_key}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
