import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

_HERE = os.path.dirname(__file__)
_MODULE_PATH = os.path.join(_HERE, "..", "tools", "status-line.py")


def load_module():
    spec = importlib.util.spec_from_file_location("status_line", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sl = load_module()

THEME = sl.default_theme()

ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def strip(s):
    return ANSI_RE.sub("", s)


NOW = 1_000_000  # fixed epoch for deterministic rate-limit tests


def _data(**over):
    base = {
        "model_name": "Opus 4.8", "model_id": "claude-opus-4-8",
        "effort": "high", "effort_auto": False, "work_dir": "/home/u/proj", "home": "/home/u",
        "branch": "main", "dirty": "modified", "is_worktree": False,
        "clock": "14:30", "ago": "5m 0s ago",
        "added": 12, "removed": 3, "cost": 0.5,
        "total_ms": 65000, "api_ms": 4200,
        "context_pct": 12, "context_max": 1_000_000,
        "chat_bytes": 305000, "mem_bytes": 448_790_528,
        "rate_limits": {}, "todo_state": None, "todo_text": None,
        "dim_assumed": False, "cols": 200, "lines": 50,
    }
    base.update(over)
    return base


class TestPickColor(unittest.TestCase):
    def test_context_ramp_bands(self):
        cases = [
            (5, THEME.c("WHITE")), (9, THEME.c("WHITE")), (10, THEME.c("CYAN")), (14, THEME.c("CYAN")),
            (15, THEME.c("BLUE")), (19, THEME.c("BLUE")), (20, THEME.c("GREEN")), (24, THEME.c("GREEN")),
            (25, THEME.c("YELLOW")), (29, THEME.c("YELLOW")), (30, THEME.c("ORANGE+bold")), (39, THEME.c("ORANGE+bold")),
            (40, THEME.c("RED+bold")), (49, THEME.c("RED+bold")), (50, THEME.c("MAGENTA_DARK+bold")), (99, THEME.c("MAGENTA_DARK+bold")),
        ]
        for pct, want in cases:
            self.assertEqual(sl.pick_color(pct, THEME.ramps["context"]), want, pct)

    def test_rate_ramp_bands(self):
        cases = [(0, THEME.c("GREEN")), (49, THEME.c("GREEN")), (50, THEME.c("YELLOW")),
                 (79, THEME.c("YELLOW")), (80, THEME.c("RED+bold")), (100, THEME.c("RED+bold"))]
        for pct, want in cases:
            self.assertEqual(sl.rate_color(pct, THEME), want, pct)


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


class TestVisibleWidth(unittest.TestCase):
    def test_plain_ascii(self):
        self.assertEqual(sl.visible_width("hello"), 5)

    def test_ansi_is_zero_width(self):
        self.assertEqual(sl.visible_width(f'{THEME.c("RED")}hi{sl.RESET}'), 2)

    def test_smp_emoji_is_two_cells(self):
        for ch in "📊📝🧠💬📡💾🧮🌿🌳📃":
            self.assertEqual(sl.char_width(ch), 2, ch)

    def test_wide_bmp_symbols_are_two_cells(self):
        for ch in "⏰⏸⚡":
            self.assertEqual(sl.char_width(ch), 2, ch)

    def test_box_drawing_is_one_cell(self):
        for ch in "▁▃▄▆█▌░":
            self.assertEqual(sl.char_width(ch), 1, ch)

    def test_narrow_symbols_are_one_cell(self):
        for ch in "✗~↺":
            self.assertEqual(sl.char_width(ch), 1, ch)

    def test_combining_mark_is_zero(self):
        self.assertEqual(sl.visible_width("é"), 1)  # e + combining acute

    def test_mixed_segment(self):
        self.assertEqual(sl.visible_width("📊 12%"), 6)


class TestFirstFitting(unittest.TestCase):
    def test_returns_richest_that_fits(self):
        self.assertEqual(sl._first_fitting(["abcdef", "abc", "a"], 4), "abc")

    def test_returns_first_when_all_fit(self):
        self.assertEqual(sl._first_fitting(["ab", "a"], 10), "ab")

    def test_none_when_nothing_fits(self):
        self.assertIsNone(sl._first_fitting(["abcdef", "abcd"], 3))

    def test_ignores_falsy_variants(self):
        self.assertEqual(sl._first_fitting([None, "", "ok"], 5), "ok")


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

    def test_branch_worktree_icon(self):
        self.assertIn("🌳", sl.seg_branch(_data(is_worktree=True), 100, THEME))
        self.assertIn("🌿", sl.seg_branch(_data(is_worktree=False), 100, THEME))

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
        self.assertEqual(strip(sl.seg_clock(_data(), 200, THEME)), "⏰14:30")

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
                    "dimensions", "context", "chat_size", "memory", "rate_limits"):
            self.assertIn(key, sl.BUILDERS, key)
            self.assertTrue(callable(sl.BUILDERS[key]))


class TestDisplayDir(unittest.TestCase):
    def test_short_path_kept_whole(self):
        self.assertEqual(sl._display_dir("/home/u/proj", "/home/u"), "~/proj")

    def test_long_path_collapses_to_basename(self):
        long = "/home/u/very/long/path/exceeding/twenty/chars"
        self.assertEqual(sl._display_dir(long, "/home/u"), "chars")

    def test_no_ellipsis_prefix(self):
        long = "/home/u/very/long/path/exceeding/twenty/chars"
        self.assertNotIn("/", sl._display_dir(long, "/home/u"))


class TestPackLine(unittest.TestCase):
    def test_keeps_segments_that_fit(self):
        out = sl.pack_line(["model", "clock"], _data(), 200)
        self.assertIn("Opus 4.8", strip(out))
        self.assertIn("⏰14:30", strip(out))
        self.assertIn(" | ", out)

    def test_best_fit_skips_overflow_keeps_smaller(self):
        out = strip(sl.pack_line(["model", "clock"], _data(model_name="X" * 60), 30))
        self.assertIn("⏰14:30", out)
        self.assertNotIn("XXXX", out)

    def test_flag_off_segment_not_built(self):
        sl.SEGMENTS["clock"] = False
        try:
            out = strip(sl.pack_line(["model", "clock"], _data(), 200))
            self.assertNotIn("⏰", out)
        finally:
            sl.SEGMENTS["clock"] = True

    def test_pinned_path_present_even_when_too_narrow(self):
        out = strip(sl.pack_line(["path", "branch"],
                                 _data(work_dir="/home/u/proj", home="/home/u"), 5))
        self.assertIn("proj", out)

    def test_pinned_context_present_even_when_too_narrow(self):
        out = strip(sl.pack_line(["dimensions", "context"],
                                 _data(cols=300, lines=80, context_pct=12), 8))
        self.assertIn("12%", out)

    def test_respects_right_margin(self):
        out = sl.pack_line(["model", "clock", "effort", "lines"], _data(), 60)
        self.assertLessEqual(sl.visible_width(out), 60 - sl.RIGHT_MARGIN)


class TestRenderLayout(unittest.TestCase):
    def test_three_lines_when_tall_and_wide(self):
        self.assertEqual(len(sl.render(_data(), 200, 50)), 3)

    def test_line_gating_by_rows(self):
        self.assertEqual(len(sl.render(_data(), 200, 10)), 1)   # identity only
        self.assertEqual(len(sl.render(_data(), 200, 25)), 2)   # + model row

    def test_identity_line_never_empty(self):
        out = sl.render(_data(branch="", dirty="clean", todo_text=None), 200, 50)
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
                    "dimensions", "context", "chat_size", "memory", "rate_limits"):
            self.assertIn(key, src, key)

    def test_has_customization_guide(self):
        src = self._src()
        for phrase in ("HOW TO CUSTOMIZE", "Add a NEW segment",
                       "Reorder", "Re-enable", "auto-deprioritize"):
            self.assertIn(phrase, src, phrase)


class TestProcAndGit(unittest.TestCase):
    def test_proc_rss_and_git_smoke(self):
        rss = sl.proc_rss_bytes()
        self.assertTrue(rss is None or isinstance(rss, int))
        branch, dirty, is_wt = sl.git_info(".")
        self.assertIn(dirty, ("clean", "untracked", "modified"))
        self.assertIsInstance(is_wt, bool)


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
        data, cols, lines = sl.build_data(raw, env)
        out = sl.render(data, cols, lines)
        self.assertEqual(len(out), 3)
        self.assertIn("Opus 4.8", strip(out[1]))
        self.assertIn("47%", strip(out[2]))


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
            (400 * KB, THEME.c("WHITE")), (512 * KB, THEME.c("CYAN")), (900 * KB, THEME.c("CYAN")),
            (1 * MB, THEME.c("LIGHTBLUE")), (1 * MB + 1, THEME.c("LIGHTBLUE")),
            (2 * MB, THEME.c("GREEN")), (3 * MB, THEME.c("YELLOW")), (4 * MB, THEME.c("ORANGE")),
            (5 * MB, THEME.c("RED+bold")), (5 * MB + 1, THEME.c("RED+bold")), (9 * MB, THEME.c("RED+bold")),
            (10 * MB, THEME.c("MAGENTA")), (20 * MB, THEME.c("MAGENTA")),
        ]
        for n, want in cases:
            self.assertEqual(sl.pick_color(n, THEME.ramps["chat_size"]), want, n)

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
        self.assertTrue(sl.effort_setting_is_auto(proj, home))

    def test_explicit_user_level_is_not_auto(self):
        proj, home = self._dirs()
        self._write(home, "settings.json", {"effortLevel": "high"})
        self.assertFalse(sl.effort_setting_is_auto(proj, home))

    def test_literal_auto_value_is_auto(self):
        proj, home = self._dirs()
        self._write(home, "settings.json", {"effortLevel": "auto"})
        self.assertTrue(sl.effort_setting_is_auto(proj, home))

    def test_project_setting_wins_over_user(self):
        proj, home = self._dirs()
        self._write(home, "settings.json", {"effortLevel": "auto"})
        self._write(proj, "settings.json", {"effortLevel": "high"})
        self.assertFalse(sl.effort_setting_is_auto(proj, home))

    def test_keyless_file_falls_through_to_next(self):
        proj, home = self._dirs()
        self._write(proj, "settings.local.json", {"model": "opus"})  # present, no effortLevel
        self._write(home, "settings.json", {"effortLevel": "max"})
        self.assertFalse(sl.effort_setting_is_auto(proj, home))

    def test_local_json_wins_over_project_and_user(self):
        proj, home = self._dirs()
        self._write(proj, "settings.local.json", {"effortLevel": "high"})
        self._write(proj, "settings.json", {"effortLevel": "auto"})
        self._write(home, "settings.json", {"effortLevel": "auto"})
        self.assertFalse(sl.effort_setting_is_auto(proj, home))


class TestResolveEffort(unittest.TestCase):
    def test_level_auto_normalized_away(self):
        # "auto" is a *setting*, never a resolved level — it must not survive here.
        self.assertEqual(sl.resolve_effort({"effort": {"level": "auto"}}, {}), "")

    def test_env_auto_normalized_away(self):
        self.assertEqual(sl.resolve_effort({}, {"CLAUDE_EFFORT": "auto"}), "")

    def test_case_normalized(self):
        self.assertEqual(sl.resolve_effort({"effort": {"level": "HIGH"}}, {}), "high")

    def test_level_wins_over_env(self):
        self.assertEqual(
            sl.resolve_effort({"effort": {"level": "high"}}, {"CLAUDE_EFFORT": "auto"}),
            "high")

    def test_missing_is_empty(self):
        self.assertEqual(sl.resolve_effort({}, {}), "")


class TestProcRssLinux(unittest.TestCase):
    def test_returns_none_when_no_claude_ancestor(self):
        # the wezterm bug: walk finds no `claude`, must return None (not a stray RSS)
        comm = {10: "zsh", 11: "wezterm-gui", 1: "systemd"}
        ppid = {10: 11, 11: 1, 1: 0}
        with mock.patch.object(sl.os.path, "isdir", return_value=True), \
             mock.patch.object(sl.os, "getppid", return_value=10), \
             mock.patch.object(sl, "_comm_via_proc", side_effect=comm.get), \
             mock.patch.object(sl, "_ppid_via_proc", side_effect=ppid.get), \
             mock.patch.object(sl, "_rss_kb_via_proc", side_effect=lambda p: 5000):
            self.assertIsNone(sl.proc_rss_bytes())

    def test_returns_rss_when_claude_found(self):
        comm = {10: "zsh", 11: "claude", 1: "systemd"}
        ppid = {10: 11, 11: 1, 1: 0}
        with mock.patch.object(sl.os.path, "isdir", return_value=True), \
             mock.patch.object(sl.os, "getppid", return_value=10), \
             mock.patch.object(sl, "_comm_via_proc", side_effect=comm.get), \
             mock.patch.object(sl, "_ppid_via_proc", side_effect=ppid.get), \
             mock.patch.object(sl, "_rss_kb_via_proc",
                               side_effect=lambda p: 204800 if p == 11 else 5000):
            self.assertEqual(sl.proc_rss_bytes(), 204800 * 1024)


class TestProcRssMacOS(unittest.TestCase):
    def test_ps_fallback_when_no_proc(self):
        comm = {10: "login", 11: "claude", 1: "launchd"}
        ppid = {10: 11, 11: 1, 1: 0}
        rss = {11: 307200, 10: 100}
        with mock.patch.object(sl.os.path, "isdir", return_value=False), \
             mock.patch.object(sl.os, "getppid", return_value=10), \
             mock.patch.object(sl, "_comm_via_ps", side_effect=comm.get), \
             mock.patch.object(sl, "_ppid_via_ps", side_effect=ppid.get), \
             mock.patch.object(sl, "_rss_kb_via_ps", side_effect=rss.get):
            self.assertEqual(sl.proc_rss_bytes(), 307200 * 1024)

    def test_ps_field_parses_one_value(self):
        class R:
            stdout = "  12345\n"
        with mock.patch.object(sl.subprocess, "run", return_value=R()):
            self.assertEqual(sl._ps_field(99, "rss"), "12345")


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
        with mock.patch.object(sl.subprocess, "run", side_effect=fake_run), \
             mock.patch("builtins.open", mock.mock_open(read_data="")):
            cols, lines, assumed = sl.terminal_size({})
        self.assertEqual((cols, lines), (123, 44))
        self.assertFalse(assumed)


class TestConfigScaffold(unittest.TestCase):
    def test_default_config_matches_globals(self):
        cfg = sl.default_config()
        self.assertEqual(cfg.segments, dict(sl.SEGMENTS))
        self.assertEqual(cfg.layout, list(sl.LAYOUT))
        self.assertEqual(cfg.palette, {})

    def test_default_config_is_a_snapshot(self):
        cfg = sl.default_config()
        cfg.segments["clock"] = not cfg.segments["clock"]
        self.assertNotEqual(cfg.segments["clock"], sl.SEGMENTS["clock"])  # snapshot, not alias


class TestEnvBool(unittest.TestCase):
    def test_true_tokens(self):
        for v in ("1", "true", "T", "y", "Yes", "on", "ON"):
            self.assertIs(sl.env_bool({"X": v}, "X"), True, v)

    def test_false_tokens(self):
        for v in ("0", "false", "F", "n", "No", "off", "OFF"):
            self.assertIs(sl.env_bool({"X": v}, "X"), False, v)

    def test_unset_is_none(self):
        self.assertIsNone(sl.env_bool({}, "X"))

    def test_unrecognized_is_none(self):
        self.assertIsNone(sl.env_bool({"X": "maybe"}, "X"))
        self.assertIsNone(sl.env_bool({"X": ""}, "X"))


class TestConfigPathAndLoad(unittest.TestCase):
    def test_explicit_path_wins(self):
        env = {"CC_AI_KIT_CONFIG": "/tmp/x.toml", "HOME": "/home/u"}
        self.assertEqual(sl.config_path(env), "/tmp/x.toml")

    def test_xdg_path(self):
        env = {"XDG_CONFIG_HOME": "/cfg", "HOME": "/home/u"}
        self.assertEqual(sl.config_path(env), "/cfg/ai-kit/statusline.toml")

    def test_home_default_path(self):
        env = {"HOME": "/home/u"}
        self.assertEqual(sl.config_path(env), "/home/u/.config/ai-kit/statusline.toml")

    def test_missing_file_is_empty(self):
        self.assertEqual(sl._load_toml("/no/such/file.toml"), {})

    def test_malformed_file_is_empty_no_crash(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("this is = = not toml")
            path = f.name
        try:
            self.assertEqual(sl._load_toml(path), {})
        finally:
            os.unlink(path)

    def test_valid_file_parses(self):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write("[segments]\ncost = true\n")
            path = f.name
        try:
            self.assertEqual(sl._load_toml(path), {"segments": {"cost": True}})
        finally:
            os.unlink(path)


class TestResolveSegments(unittest.TestCase):
    def _write(self, body):
        f = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False)
        f.write(body)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_defaults_when_no_file_no_env(self):
        env = {"CC_AI_KIT_CONFIG": "/no/such.toml", "HOME": "/h"}
        cfg = sl.load_config(env)
        self.assertEqual(cfg.segments, dict(sl.SEGMENTS))
        self.assertEqual(cfg.layout, list(sl.LAYOUT))
        self.assertEqual(cfg.palette, {})

    def test_file_overrides_default(self):
        path = self._write("[segments]\ncost = true\nmemory = false\n")
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertTrue(cfg.segments["cost"])      # default False -> True
        self.assertFalse(cfg.segments["memory"])   # default True  -> False
        self.assertTrue(cfg.segments["clock"])     # untouched default

    def test_env_overrides_file(self):
        path = self._write("[segments]\ncost = true\n")
        env = {"CC_AI_KIT_CONFIG": path, "HOME": "/h", "CC_AI_KIT_SEGMENT_COST": "0"}
        cfg = sl.load_config(env)
        self.assertFalse(cfg.segments["cost"])     # env beats file

    def test_unknown_segment_key_ignored(self):
        path = self._write("[segments]\nbogus = true\n")
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertNotIn("bogus", cfg.segments)

    def test_wrong_type_value_ignored(self):
        # `cost = "true"` (string, not bool) is a known key but a bad value:
        # it must be dropped (keeping the default), not silently coerced.
        path = self._write('[segments]\ncost = "true"\n')
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.segments["cost"], sl.SEGMENTS["cost"])  # default kept


class TestRenderWithConfig(unittest.TestCase):
    def test_pack_line_honors_cfg_segments(self):
        cfg = sl.Config(segments={**sl.SEGMENTS, "clock": False},
                        layout=list(sl.LAYOUT), palette={}, ramps={})
        out = strip(sl.pack_line(["model", "clock"], _data(), 200, cfg))
        self.assertNotIn("⏰", out)
        self.assertIn("Opus 4.8", out)

    def test_render_honors_cfg_layout(self):
        cfg = sl.Config(segments=dict(sl.SEGMENTS),
                        layout=[sl.Line(0, ["model"])], palette={}, ramps={})
        lines = sl.render(_data(), 200, 50, cfg)
        self.assertEqual(len(lines), 1)
        self.assertIn("Opus 4.8", strip(lines[0]))

    def test_render_default_cfg_unchanged(self):
        # No cfg arg -> same as today (three rows when tall+wide).
        self.assertEqual(len(sl.render(_data(), 200, 50)), 3)


class TestMainUsesConfig(unittest.TestCase):
    def _run_main(self, raw, env):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(raw))), \
             mock.patch.object(sys, "argv", ["status-line.py"]), \
             mock.patch.dict(os.environ, env, clear=True), \
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
        f = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False)
        f.write(body)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_no_line_keeps_default_layout(self):
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": "/no/such.toml", "HOME": "/h"})
        self.assertEqual(cfg.layout, list(sl.LAYOUT))

    def test_line_replaces_layout(self):
        path = self._write(
            '[[line]]\nmin_rows = 0\nsegments = ["path", "model"]\n'
            '[[line]]\nmin_rows = 25\nsegments = ["context"]\n')
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.layout,
                         [sl.Line(0, ["path", "model"]), sl.Line(25, ["context"])])

    def test_line_missing_min_rows_defaults_zero(self):
        path = self._write('[[line]]\nsegments = ["path"]\n')
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.layout, [sl.Line(0, ["path"])])


class TestPaletteFromConfig(unittest.TestCase):
    def _write(self, body):
        f = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False)
        f.write(body)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_palette_parsed_into_config(self):
        path = self._write('[palette]\nBLUE = "1;34"\n')
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.palette, {"BLUE": "1;34"})

    def test_unknown_palette_key_dropped(self):
        path = self._write('[palette]\nNOTACOLOR = "1;34"\n')
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
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
        with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(raw))), \
             mock.patch.object(sys, "argv", ["status-line.py"]), \
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


class TestCLI(unittest.TestCase):
    def _write(self, body):
        f = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False)
        f.write(body)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_parse_args_defaults(self):
        ns = sl.parse_args([])
        self.assertFalse(ns.print_config)
        self.assertIs(ns.check, sl._NO_CHECK)

    def test_print_config_emits_resolved_json(self):
        cfg = sl.Config(segments={"path": True}, layout=[sl.Line(0, ["path"])],
                        palette={"BLUE": "1;34"}, ramps={})
        out = sl.cmd_print_config(cfg)
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


class TestParseColor(unittest.TestCase):
    PAL = {"RED": "31", "BLUE": "38;5;39", "ORANGE": "38;5;208"}

    def test_palette_name(self):
        self.assertEqual(sl.parse_color("RED", self.PAL), "\033[31m")
        self.assertEqual(sl.parse_color("BLUE", self.PAL), "\033[38;5;39m")

    def test_raw_sgr_passthrough(self):
        self.assertEqual(sl.parse_color("38;5;33"), "\033[38;5;33m")
        self.assertEqual(sl.parse_color("1;31"), "\033[1;31m")

    def test_hex_six(self):
        self.assertEqual(sl.parse_color("#3399ff"), "\033[38;2;51;153;255m")

    def test_hex_short_expands(self):
        self.assertEqual(sl.parse_color("#39f"), "\033[38;2;51;153;255m")

    def test_hex_alpha_stripped(self):
        self.assertEqual(sl.parse_color("#3399ffcc"), "\033[38;2;51;153;255m")

    def test_modifier_bold_on_name(self):
        self.assertEqual(sl.parse_color("RED+bold", self.PAL), "\033[1;31m")

    def test_modifier_on_hex(self):
        self.assertEqual(sl.parse_color("#3399ff+bold"), "\033[1;38;2;51;153;255m")

    def test_modifiers_canonical_order(self):
        # underline(4)+bold(1) -> ascending 1;4 regardless of input order
        self.assertEqual(sl.parse_color("RED+underline+bold", self.PAL), "\033[1;4;31m")

    def test_all_modifiers(self):
        self.assertEqual(sl.parse_color("RED+bold+dim+italic+underline", self.PAL),
                         "\033[1;2;3;4;31m")

    def test_unknown_name_is_none(self):
        self.assertIsNone(sl.parse_color("NOTACOLOR", self.PAL))

    def test_name_without_palette_is_none(self):
        self.assertIsNone(sl.parse_color("RED"))

    def test_unknown_modifier_is_none(self):
        self.assertIsNone(sl.parse_color("RED+blink", self.PAL))

    def test_bad_hex_is_none(self):
        self.assertIsNone(sl.parse_color("#zzz"))
        self.assertIsNone(sl.parse_color("#12345"))   # 5 nibbles, not 3/6/8

    def test_empty_is_none(self):
        self.assertIsNone(sl.parse_color(""))
        self.assertIsNone(sl.parse_color(None))


class TestParseThreshold(unittest.TestCase):
    def test_percent_int(self):
        self.assertEqual(sl._parse_threshold(10), 10)
        self.assertEqual(sl._parse_threshold("25"), 25)

    def test_inf(self):
        self.assertEqual(sl._parse_threshold("inf"), float("inf"))
        self.assertEqual(sl._parse_threshold(float("inf")), float("inf"))

    def test_byte_suffixes(self):
        self.assertEqual(sl._parse_threshold("512k"), 512 * 1024)
        self.assertEqual(sl._parse_threshold("5M"), 5 * 1024 * 1024)
        self.assertEqual(sl._parse_threshold("1G"), 1024 ** 3)

    def test_bad_key_raises(self):
        with self.assertRaises(ValueError):
            sl._parse_threshold("nonsense")
        with self.assertRaises(ValueError):
            sl._parse_threshold("5MB")   # only single-letter k/M/G suffix


class TestTheme(unittest.TestCase):
    def test_c_resolves_and_memoizes(self):
        t = sl.default_theme()
        first = t.c("RED")
        self.assertTrue(first.startswith("\033["))
        self.assertEqual(t.c("RED"), first)          # same object/value, cached
        self.assertIn("RED", t._cache)

    def test_c_modifier(self):
        t = sl.default_theme()
        self.assertEqual(t.c("RED+bold"), sl.parse_color("RED+bold", t.palette))

    def test_c_invalid_is_empty_string(self):
        t = sl.default_theme()
        self.assertEqual(t.c("NOTACOLOR"), "")        # never raises, no color


class TestBuildTheme(unittest.TestCase):
    def _cfg(self, palette=None, ramps=None):
        return sl.Config(segments=dict(sl.SEGMENTS), layout=list(sl.LAYOUT),
                         palette=palette or {}, ramps=ramps or {})

    def test_palette_merges_over_defaults(self):
        t = sl.build_theme(self._cfg(palette={"BLUE": "1;34"}))
        self.assertEqual(t.palette["BLUE"], "1;34")
        self.assertEqual(t.palette["RED"], sl._PALETTE_DEFAULTS["RED"])  # untouched

    def test_palette_hex_override_resolved_to_params(self):
        t = sl.build_theme(self._cfg(palette={"BLUE": "#3399ff"}))
        self.assertEqual(t.palette["BLUE"], "38;2;51;153;255")

    def test_bad_palette_value_keeps_default(self):
        t = sl.build_theme(self._cfg(palette={"BLUE": "#zzz"}))
        self.assertEqual(t.palette["BLUE"], sl._PALETTE_DEFAULTS["BLUE"])

    def test_ramp_replaced_whole(self):
        t = sl.build_theme(self._cfg(ramps={"rate": {"50": "GREEN", "inf": "RED"}}))
        self.assertEqual([c for _, c in t.ramps["rate"]],
                         [t.c("GREEN"), t.c("RED")])
        self.assertEqual([ceil for ceil, _ in t.ramps["rate"]], [50, float("inf")])

    def test_unspecified_ramp_keeps_default(self):
        t = sl.build_theme(self._cfg(ramps={"rate": {"inf": "RED"}}))
        self.assertEqual(len(t.ramps["context"]), len(sl._RAMP_DEFAULTS["context"]))

    def test_bad_band_color_falls_back_to_default_band(self):
        # context default band at ceil 10 is WHITE; a bad override color for that
        # band falls back to the default band's resolved color.
        bad = {"10": "NOPE", "inf": "RED"}
        t = sl.build_theme(self._cfg(ramps={"context": bad}))
        self.assertEqual(t.ramps["context"][0], (10, t.c("WHITE")))

    def test_bad_threshold_keeps_whole_default_ramp(self):
        t = sl.build_theme(self._cfg(ramps={"context": {"oops": "RED"}}))
        self.assertEqual(t.ramps["context"], sl.default_theme().ramps["context"])

    def test_effort_derives_from_palette(self):
        t = sl.default_theme()
        self.assertEqual(t.effort["low"][0], t.c("CYAN"))
        self.assertEqual(t.effort["max"][0], t.c("RED"))
        self.assertEqual(t.effort["low"][1].count("▁"), 1)
        # full ladder: every glyph present, no trailing grey segment for max
        self.assertTrue(t.effort["max"][1].startswith(t.c("RED")))


class TestRampFromConfig(unittest.TestCase):
    def _write(self, body):
        f = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False)
        f.write(body); f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_ramp_parsed_into_config(self):
        path = self._write('[ramp.rate]\n50 = "GREEN"\ninf = "RED+bold"\n')
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.ramps, {"rate": {"50": "GREEN", "inf": "RED+bold"}})

    def test_unknown_ramp_dropped(self):
        path = self._write('[ramp.bogus]\n10 = "RED"\n')
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": path, "HOME": "/h"})
        self.assertEqual(cfg.ramps, {})

    def test_no_ramp_block_is_empty(self):
        cfg = sl.load_config({"CC_AI_KIT_CONFIG": "/no/such.toml", "HOME": "/h"})
        self.assertEqual(cfg.ramps, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
