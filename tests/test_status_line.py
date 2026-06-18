import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
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
            (5, sl.WHITE), (9, sl.WHITE), (10, sl.CYAN), (14, sl.CYAN),
            (15, sl.BLUE), (19, sl.BLUE), (20, sl.GREEN), (24, sl.GREEN),
            (25, sl.YELLOW), (29, sl.YELLOW), (30, sl.ORANGE_BOLD), (39, sl.ORANGE_BOLD),
            (40, sl.RED), (49, sl.RED), (50, sl.MAGENTA_DARK_BOLD), (99, sl.MAGENTA_DARK_BOLD),
        ]
        for pct, want in cases:
            self.assertEqual(sl.pick_color(pct, sl.CONTEXT_RAMP), want, pct)

    def test_rate_ramp_bands(self):
        cases = [(0, sl.GREEN), (49, sl.GREEN), (50, sl.YELLOW),
                 (79, sl.YELLOW), (80, sl.RED), (100, sl.RED)]
        for pct, want in cases:
            self.assertEqual(sl.rate_color(pct), want, pct)


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
        self.assertEqual(sl.visible_width(f"{sl.RED}hi{sl.RESET}"), 2)

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
            "low": sl.CYAN, "medium": sl.BLUE,
            "high": sl.YELLOW, "xhigh": sl.ORANGE, "max": sl.RED,
        }
        for level, color in want.items():
            self.assertEqual(sl._EFFORT_BARS[level][0], color, level)

    def test_effort_fill_counts(self):
        want = {"low": 1, "medium": 2, "high": 3, "xhigh": 4, "max": 5}
        for level, n in want.items():
            filled = sl._EFFORT_BARS[level][1].split(sl.GREY)[0]
            count = sum(filled.count(c) for c in "▁▃▄▆█")
            self.assertEqual(count, n, level)


class TestCooperativeBuilders(unittest.TestCase):
    def test_branch_content_then_self_hide(self):
        self.assertIn("main", sl.seg_branch(_data(branch="main"), 50))
        self.assertIsNone(sl.seg_branch(_data(branch="main"), 5))    # no room
        self.assertIsNone(sl.seg_branch(_data(branch=""), 200))      # no data

    def test_branch_worktree_icon(self):
        self.assertIn("🌳", sl.seg_branch(_data(is_worktree=True), 100))
        self.assertIn("🌿", sl.seg_branch(_data(is_worktree=False), 100))

    def test_effort_full_then_compact_then_hide(self):
        self.assertIn("high", strip(sl.seg_effort(_data(effort="high"), 30)))
        compact = strip(sl.seg_effort(_data(effort="high"), 10))
        self.assertNotIn("high", compact)
        self.assertIn("▁▃▄", compact)
        self.assertIsNone(sl.seg_effort(_data(effort="high"), 5))
        self.assertIsNone(sl.seg_effort(_data(effort=""), 200))

    def test_effort_all_levels_full(self):
        for level in ("low", "medium", "high", "xhigh", "max"):
            out = strip(sl.seg_effort(_data(effort=level), 30))
            self.assertIn(level, out)
            self.assertTrue(out.startswith("🧠"))

    def test_context_three_tiers_never_none(self):
        self.assertIn("of 1M", strip(sl.seg_context(_data(context_pct=12), 200)))
        mid = strip(sl.seg_context(_data(context_pct=12), 18))
        self.assertNotIn("of 1M", mid)
        self.assertIn("█", mid)
        self.assertEqual(strip(sl.seg_context(_data(context_pct=12), 8)), "📊 12%")
        self.assertIsNotNone(sl.seg_context(_data(context_pct=12), 2))  # floor

    def test_context_low_pct_half_bar_and_zero_empty(self):
        self.assertIn("▌", strip(sl.seg_context(_data(context_pct=5), 200)))
        zero = strip(sl.seg_context(_data(context_pct=0), 200))
        self.assertNotIn("█", zero)
        self.assertNotIn("▌", zero)

    def test_dimensions_content_then_self_hide(self):
        self.assertEqual(strip(sl.seg_dimensions(_data(cols=120, lines=40), 200)),
                         "120×40")
        self.assertIsNone(sl.seg_dimensions(_data(cols=120, lines=40), 3))

    def test_chat_memory_self_hide_when_cramped(self):
        self.assertIsNotNone(sl.seg_chat_size(_data(), 200))
        self.assertIsNone(sl.seg_chat_size(_data(), 3))
        self.assertIsNone(sl.seg_chat_size(_data(chat_bytes=None), 200))
        self.assertIsNone(sl.seg_memory(_data(mem_bytes=None), 200))

    def test_rate_limits_shows_reset_then_drops_suffix_when_narrow(self):
        rl = {"five_hour": {"used_percentage": 42, "resets_at": NOW + 3600}}
        self.assertIn("↺", strip(sl.seg_rate_limits(_data(rate_limits=rl), 200)))
        narrow = strip(sl.seg_rate_limits(_data(rate_limits=rl), 12))
        self.assertNotIn("↺", narrow)
        self.assertIn("5h", narrow)
        self.assertIsNone(sl.seg_rate_limits(_data(rate_limits={}), 200))

    def test_model_and_clock(self):
        self.assertEqual(strip(sl.seg_model(_data(), 200)), "Opus 4.8")
        self.assertEqual(strip(sl.seg_clock(_data(), 200)), "⏰14:30")

    def test_todo_truncates_and_hides(self):
        self.assertIn("hello", strip(sl.seg_todo(
            _data(todo_state="in_progress", todo_text="hello"), 200)))
        self.assertIsNone(sl.seg_todo(
            _data(todo_state="in_progress", todo_text="hello"), 8))

    def test_rate_visibility_independent_of_clock(self):
        # Every bucket shows regardless of how its resets_at compares to the
        # clock — a past reset must NOT hide a bucket (timezone/clock changes
        # must never affect which limits are visible).
        rl = {"five_hour": {"used_percentage": 42, "resets_at": NOW + 3600},
              "seven_day": {"used_percentage": 13, "resets_at": NOW - 60}}  # past reset
        out = strip(sl.seg_rate_limits(_data(rate_limits=rl), 200))
        self.assertIn("5h: 42%", out)
        self.assertIn("7d: 13%", out)      # past-reset bucket still shown

    def test_rate_past_reset_bucket_still_shown(self):
        rl = {"five_hour": {"used_percentage": 50, "resets_at": NOW - 1}}
        out = strip(sl.seg_rate_limits(_data(rate_limits=rl), 200))
        self.assertIn("5h: 50%", out)

    def test_rate_no_resets_at_kept_without_suffix(self):
        rl = {"five_hour": {"used_percentage": 30}}  # no reset stamp -> just the %
        out = strip(sl.seg_rate_limits(_data(rate_limits=rl), 200))
        self.assertIn("5h: 30%", out)
        self.assertNotIn("↺", out)

    def test_rate_far_future_bucket_shows_long_date_when_room(self):
        rl = {"seven_day": {"used_percentage": 30, "resets_at": NOW + 7 * 86400}}
        wide = strip(sl.seg_rate_limits(_data(rate_limits=rl), 200))
        self.assertRegex(wide, r"↺ [A-Z][a-z]{2} \d\d")   # e.g. "↺ Jan 19"

    def test_path_never_none(self):
        self.assertIsNotNone(sl.seg_path(_data(), 1))

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
    def test_blue_is_256color_true_blue(self):
        # 1;34 bold-ANSI-blue reads purple on many terminals; use 256-color blue.
        self.assertEqual(sl.BLUE, "\033[38;5;33m")

    def test_lightblue_defined_for_chat_ramp(self):
        self.assertEqual(sl.LIGHTBLUE, "\033[38;5;75m")

    def test_path_emits_true_blue_not_bold_ansi(self):
        out = sl.seg_path(_data(), 80)
        self.assertIn("38;5;33", out)
        self.assertNotIn("\033[1;34m", out)


class TestChatSizeRamp(unittest.TestCase):
    KB = 1024
    MB = 1024 * 1024

    def test_ramp_bands(self):
        KB, MB = self.KB, self.MB
        cases = [
            (400 * KB, sl.WHITE), (512 * KB, sl.CYAN), (900 * KB, sl.CYAN),
            (1 * MB, sl.LIGHTBLUE), (1 * MB + 1, sl.LIGHTBLUE),
            (2 * MB, sl.GREEN), (3 * MB, sl.YELLOW), (4 * MB, sl.ORANGE),
            (5 * MB, sl.RED), (5 * MB + 1, sl.RED), (9 * MB, sl.RED),
            (10 * MB, sl.MAGENTA), (20 * MB, sl.MAGENTA),
        ]
        for n, want in cases:
            self.assertEqual(sl.pick_color(n, sl.CHAT_SIZE_RAMP), want, n)

    def test_seg_chat_size_colors_the_size(self):
        out = sl.seg_chat_size(_data(chat_bytes=6 * self.MB), 40)
        self.assertIn("💾", out)
        self.assertIn(sl.RED, out)       # 6 MB -> red band

    def test_seg_chat_size_none_when_no_bytes(self):
        self.assertIsNone(sl.seg_chat_size(_data(chat_bytes=None), 40))


class TestEffortAutoSetting(unittest.TestCase):
    def test_auto_appends_bracket_when_room(self):
        out = strip(sl.seg_effort(_data(effort="high", effort_auto=True), 40))
        self.assertIn("high", out)
        self.assertIn("[auto]", out)

    def test_resolved_level_keeps_its_color_in_auto(self):
        out = sl.seg_effort(_data(effort="high", effort_auto=True), 40)
        self.assertIn(f"{sl.YELLOW}high", out)   # level keeps its fixed color

    def test_auto_compacts_to_asterisk_when_tight(self):
        out = strip(sl.seg_effort(_data(effort="medium", effort_auto=True), 18))
        self.assertIn("medium*", out)
        self.assertNotIn("[auto]", out)

    def test_non_auto_has_no_annotation(self):
        out = strip(sl.seg_effort(_data(effort="high", effort_auto=False), 40))
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
                        layout=list(sl.LAYOUT), palette={})
        out = strip(sl.pack_line(["model", "clock"], _data(), 200, cfg))
        self.assertNotIn("⏰", out)
        self.assertIn("Opus 4.8", out)

    def test_render_honors_cfg_layout(self):
        cfg = sl.Config(segments=dict(sl.SEGMENTS),
                        layout=[sl.Line(0, ["model"])], palette={})
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
