"""Synthetic payload and cache tests for the Cursor status-line host."""

import contextlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from datetime import datetime
from typing import Any, cast
from unittest import mock

from tests.cursor_fakes import run_like_cursor
from tools.cursor_quota import (
    QuotaResult,
    core_quota_state,
    core_synthetic_cache,
    probe_cache_paths,
    probe_write_cache,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENTRY = ROOT / "tools" / "cursor-status-line.py"
SYNTHETIC = json.loads((ROOT / "tests/fixtures/cursor/payload_synthetic.json").read_text())
POC = json.loads((ROOT / "tests/fixtures/cursor/payload_poc_redacted.json").read_text())
sys.path.insert(0, str(ROOT / "tools"))
import claude_host
import common_config
import common_fmt
import common_probe
import common_segments
import common_types
import cursor_host
import cursor_payload
import cursor_probes
import cursor_segments
from common_config import cfg_default_config, cfg_load_config
from common_render import Context, core_build_theme, core_render


class TestCursorStatusLine(unittest.TestCase):
    def _environment(self, root: pathlib.Path, extras: dict[str, str] | None = None):
        home = root / "home"
        xdg = root / "xdg"
        cache = root / "cache"
        for directory in (home, xdg, cache):
            directory.mkdir(parents=True, exist_ok=True)
        cache_base = str(cache / "ai-kit")
        path, _lock = probe_cache_paths(cache_base)
        self.assertTrue(probe_write_cache(path, core_synthetic_cache(time.time())))
        env = {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(xdg),
            "XDG_CACHE_HOME": str(cache),
            "PATH": os.defpath,
        }
        if extras:
            env.update(extras)
        return env

    def _run_entry(self, payload: dict[str, Any], env: dict[str, str]):
        return subprocess.run(
            [sys.executable, "-S", str(ENTRY)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=10,
        )

    def _context(self, quota: QuotaResult, cols: int = 120, raw: dict[str, Any] | None = None):
        config = cfg_default_config(cursor_host.SPEC)
        theme = core_build_theme(config, cursor_host.HOST)
        data = cursor_payload.CursorData(quota)
        return Context(
            raw or {},
            config,
            theme,
            cols,
            40,
            False,
            None,
            "Model",
            "model",
            "/work/project",
            "/tmp/home",
            "12:00",
            42,
            200000,
            data,
        ), theme

    @staticmethod
    def _quota(**overrides):
        values = {
            "state": "ok",
            "confidence": "inferred",
            "diagnostic": "",
            "fetched_at": 1000,
            "cycle_start_ms": 0,
            "cycle_end_ms": 100_000_000,
            "included_pct": 47.0,
            "api_pct": 35.0,
            "included_window": (0, 100_000_000),
            "od_kind": "fixed",
            "od_used_usd": 5.2,
            "od_ceiling_usd": 20.0,
        }
        values.update(overrides)
        return QuotaResult(**values)

    def test_render_with_unresolved_or_relative_cache_base_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            cwd = pathlib.Path(temporary)
            previous = pathlib.Path.cwd()
            os.chdir(cwd)
            try:
                for env in ({}, {"XDG_CACHE_HOME": "relative-cache"}):
                    with self.subTest(env=env):
                        config = cfg_default_config(cursor_host.SPEC)
                        theme = core_build_theme(config, cursor_host.HOST)
                        context = cursor_payload.core_cursor_context(
                            SYNTHETIC, config, theme, env, None
                        )
                        self.assertEqual(
                            cursor_payload.core_cursor_data(context).quota.state, "absent"
                        )
                        self.assertEqual(list(cwd.iterdir()), [])
            finally:
                os.chdir(previous)

    def test_entry_cache_is_resolved_under_xdg_cache_home(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            env = {
                "HOME": str(root / "home"),
                "XDG_CONFIG_HOME": str(root / "xdg-config"),
                "XDG_CACHE_HOME": str(root / "xdg-cache"),
                "PATH": os.defpath,
            }
            cwd = root / "workspace"
            cwd.mkdir()
            result = run_like_cursor(
                [sys.executable, "-S", str(ENTRY)], SYNTHETIC, cwd=str(cwd), env=env
            )
            self.assertEqual(result.returncode, 0, result.text)
            cache_root = pathlib.Path(env["XDG_CACHE_HOME"]) / "ai-kit" / "cursor"
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not (cache_root / "usage.json").exists():
                time.sleep(0.02)
            self.assertEqual(
                sorted(path.name for path in cache_root.iterdir()), ["usage.json", "usage.lock"]
            )
            self.assertFalse((cwd / "cursor").exists())
            self.assertFalse((root / "cursor").exists())

    def test_entry_renders_path_model_and_nullable_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = self._environment(pathlib.Path(temporary))
            result = self._run_entry(SYNTHETIC, env)
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = result.stdout.splitlines()
            self.assertIn("/work/project", lines[0])
            self.assertIn("Synthetic Model · high", lines[1])
            self.assertIn("42%", lines[1])

            without_summary = json.loads(json.dumps(SYNTHETIC))
            without_summary["model"].pop("param_summary")
            bare = self._run_entry(without_summary, env)
            self.assertIn("Synthetic Model", bare.stdout)
            self.assertNotIn("Synthetic Model ·", bare.stdout)

            without_context = json.loads(json.dumps(SYNTHETIC))
            without_context["context_window"]["used_percentage"] = None
            hidden = self._run_entry(without_context, env)
            self.assertEqual(hidden.returncode, 0, hidden.stderr)
            self.assertNotIn("📊", hidden.stdout)

    def test_entry_width_precedence_and_poc_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = self._environment(pathlib.Path(temporary), {"STATUSLINE_COLS": "200"})
            for value, expected in (
                (60, 60),
                (0, 200),
                (-1, 200),
                (True, 200),
                ("80", 200),
                (None, 200),
            ):
                payload = json.loads(json.dumps(SYNTHETIC))
                if value is None:
                    payload.pop("render_width_chars")
                else:
                    payload["render_width_chars"] = value
                result = self._run_entry(payload, env)
                self.assertEqual(result.returncode, 0, result.stderr)
                config = cfg_default_config(cursor_host.SPEC)
                theme = core_build_theme(config, cursor_host.HOST)
                context = cursor_payload.core_cursor_context(payload, config, theme, env, None)
                self.assertEqual(context.cols, expected)
            poc = self._run_entry(POC, env)
            self.assertEqual(poc.returncode, 0, poc.stderr)

    def test_cursor_runner_simulator_uses_real_entry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            env = self._environment(root)
            result = run_like_cursor(
                [sys.executable, "-S", str(ENTRY)], SYNTHETIC, cwd=str(ROOT), env=env
            )
            self.assertEqual(result.returncode, 0, result.text)
            self.assertIn("Synthetic Model · high", result.text)

    def test_shared_gauge_identity_and_included_variants(self):
        self.assertIs(cursor_segments.util_window_gap, common_fmt.util_window_gap)
        self.assertIs(cursor_segments.util_gap_color, common_types.util_gap_color)
        self.assertIs(cursor_segments.util_gap_sign, common_types.util_gap_sign)
        context, theme = self._context(self._quota(included_window=(0, 100_000)))
        with mock.patch("cursor_segments.time.time", return_value=40):
            wide = cursor_segments.seg_cursor_included(context, 40, theme)
            narrow = cursor_segments._colored(
                cursor_segments.Gauge("47%", 47, (0, 100_000), 40, "ok", False), theme
            )
        self.assertIn("inc: ", cast(str, wide))
        self.assertIn("-47%", cast(str, wide))
        self.assertIn(theme.c("YELLOW"), cast(str, wide))
        self.assertIn(" ≈", cast(str, wide))
        self.assertNotIn("-47%", narrow)
        self.assertIn("47%", narrow)
        neutral_ctx, neutral_theme = self._context(self._quota(included_window=None))
        neutral = cursor_segments.seg_cursor_included(neutral_ctx, 40, neutral_theme)
        self.assertIn(neutral_theme.c("WHITE"), cast(str, neutral))

    def test_api_renders_whatever_the_toggle_packer_gates(self):
        # WR-04: the builder no longer re-checks its own enablement — the
        # packer already filters disabled keys, and double-gating kept the
        # doctor's every-builder dry render from exercising the default-off
        # cursor_api gauge. The builder renders whenever it has quota data;
        # enablement is the layout's concern.
        self.assertFalse(cursor_host.SEGMENTS["cursor_api"])
        context, theme = self._context(self._quota())
        api = cursor_segments.seg_cursor_api(context, 100, theme)
        self.assertIn("api: ", cast(str, api))
        fixed = cursor_segments.seg_cursor_extra(context, 100, theme)
        self.assertIn("$5.20/$20.00", cast(str, fixed))
        self.assertIn("≈", cast(str, fixed))
        unlimited_ctx, unlimited_theme = self._context(
            self._quota(od_kind="unlimited", od_ceiling_usd=None)
        )
        unlimited = cursor_segments.seg_cursor_extra(unlimited_ctx, 100, unlimited_theme)
        self.assertIn("$5.20", cast(str, unlimited))
        self.assertIn("≈", cast(str, unlimited))
        disabled_ctx, disabled_theme = self._context(
            self._quota(od_kind="disabled", od_ceiling_usd=None)
        )
        self.assertIn(
            "extra off",
            cast(str, cursor_segments.seg_cursor_extra(disabled_ctx, 100, disabled_theme)),
        )
        hidden_ctx, hidden_theme = self._context(
            self._quota(od_kind="unavailable", od_ceiling_usd=None)
        )
        self.assertIsNone(cursor_segments.seg_cursor_extra(hidden_ctx, 100, hidden_theme))

    def test_stale_hidden_states_and_segment_adjacency(self):
        stale_ctx, stale_theme = self._context(self._quota(state="stale"))
        wide = cursor_segments.seg_cursor_included(stale_ctx, 100, stale_theme)
        narrow = cursor_segments._colored(
            cursor_segments.Gauge("47%", 47, (0, 100_000), 40, "stale", False), stale_theme
        ) + cursor_segments._marker("stale", False)
        self.assertIn("≈ stale", cast(str, wide))
        self.assertIn("≈*", cast(str, narrow))
        for state in (
            "absent",
            "auth_expired",
            "auth_unsupported",
            "auth_missing",
            "network_error",
            "cycle_ended",
        ):
            ctx, theme = self._context(self._quota(state=state))
            for builder in (
                cursor_segments.seg_cursor_included,
                cursor_segments.seg_cursor_api,
                cursor_segments.seg_cursor_extra,
                cursor_segments.seg_cursor_reset,
            ):
                self.assertIsNone(builder(ctx, 200, theme), state)
        included, theme = self._context(self._quota(od_kind="unavailable"))
        extra_quota = self._quota(included_pct=None)
        extra, extra_theme = self._context(extra_quota)
        self.assertIsNotNone(cursor_segments.seg_cursor_included(included, 100, theme))
        self.assertIsNone(cursor_segments.seg_cursor_extra(included, 100, theme))
        self.assertIsNone(cursor_segments.seg_cursor_included(extra, 100, extra_theme))
        self.assertIsNotNone(cursor_segments.seg_cursor_extra(extra, 100, extra_theme))

    def test_reset_is_local_date_without_time_of_day(self):
        # D-04: the reset shows the local date and no clock time, in any zone.
        weekly = self._quota(included_window=(93_600_000, 698_400_000))
        window = cast(tuple[int, int], weekly.included_window)
        self.assertEqual(window[0], window[1] - 7 * 86400 * 1000)
        ctx, theme = self._context(weekly)
        end_ms = cast(int, cursor_segments._cycle_end(weekly))
        for zone in ("UTC", "Asia/Tokyo"):
            with mock.patch.dict(os.environ, {"TZ": zone}):
                time.tzset()
                text = cast(str, cursor_segments.seg_cursor_reset(ctx, 100, theme))
                expected = datetime.fromtimestamp(end_ms / 1000).strftime("%b %d")
            self.assertIn(f"↺ {expected} (", text)
            self.assertNotIn(":", text)
            self.assertIn("≈", text)
        time.tzset()

    def test_config_namespace_provider_namespace_and_no_network_render(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            env = self._environment(root)
            path = root / "provider" / "extra"
            path.parent.mkdir()
            capture = root / "provider-env.json"
            path.write_text(
                f"#!{sys.executable} -S\n"
                "import json, os, sys\n"
                f"open({str(capture)!r}, 'w').write(json.dumps(dict(os.environ)))\n"
                "print('provider-value')\n",
                encoding="utf-8",
            )
            path.chmod(0o755)
            config_file = root / "cursor.toml"
            config_file.write_text(
                "[segments]\npath=false\nmodel=true\n"
                f"[external]\ndir='{path.parent}'\n"
                "[[line]]\nmin_rows=0\nsegments=['extra']\n",
                encoding="utf-8",
            )
            env["AI_KIT_CURSOR_CONFIG_FILE"] = str(config_file)
            env["CC_AI_KIT_CONFIG_FILE"] = str(root / "wrong-claude.toml")
            env["CC_AI_KIT_SEGMENT_MODEL"] = "0"
            cache = root / "cache" / "ai-kit" / "segments-cursor"
            cache.mkdir(parents=True)
            env["XDG_CACHE_HOME"] = str(root / "cache")
            cfg = cfg_load_config(env, cursor_host.SPEC)
            self.assertTrue(cfg.segments["model"])
            self.assertFalse(cfg.segments["path"])
            external = cast(common_types.ExternalConf, cfg.external)
            self.assertEqual([provider.id for provider in external.providers], ["extra"])
            self.assertIn("extra", cfg.layout[0].segments)
            context = cursor_payload.core_cursor_context(
                SYNTHETIC, cfg, core_build_theme(cfg, cursor_host.HOST), env, None
            )
            with mock.patch(
                "cursor_payload.probe_read_quota", wraps=cursor_payload.probe_read_quota
            ) as reader:
                # The fresh cache suppresses its spawn callback and all network imports.
                with mock.patch("cursor_quota.probe_spawn_refresher", side_effect=AssertionError):
                    cursor_host.HOST.build_context(SYNTHETIC, cfg, context.theme, env, None)
                reader.assert_called()
            context.work_dir = str(root)
            rendered = core_render(context, cursor_host.HOST, cfg)
            self.assertIn("provider-value", "\n".join(rendered))
            provider_env = json.loads(capture.read_text(encoding="utf-8"))
            for key in (
                "AI_KIT_CURSOR_PROVIDER_COLS",
                "AI_KIT_CURSOR_PROVIDER_ID",
                "AI_KIT_CURSOR_PROVIDER_LINE",
                "AI_KIT_CURSOR_PROVIDER_POSITION",
            ):
                self.assertIn(key, provider_env)
            self.assertFalse(any(key.startswith("AI_KIT_SEGMENT_") for key in provider_env))
            self.assertTrue(list(cache.iterdir()))

    def test_claude_config_does_not_scan_cursor_provider_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            env = self._environment(root)
            xdg = pathlib.Path(env["XDG_CONFIG_HOME"])
            cursor_dir = xdg / "ai-kit" / "segments-cursor"
            cursor_dir.mkdir(parents=True)
            provider = cursor_dir / "cursor-only"
            provider.write_text(f"#!{sys.executable} -S\nprint('cursor-only')\n", encoding="utf-8")
            provider.chmod(0o755)
            with mock.patch(
                "common_config.core_discover_external", wraps=common_config.core_discover_external
            ) as discover:
                claude_cfg = cfg_load_config(env, claude_host.HOST.config)
            self.assertEqual(cast(common_types.ExternalConf, claude_cfg.external).providers, [])
            self.assertNotIn(str(cursor_dir), str(discover.call_args))

    def test_config_env_isolation_and_cursor_toggle(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            env = self._environment(
                root,
                {
                    "CC_AI_KIT_CONFIG_FILE": str(root / "claude.toml"),
                    "CC_AI_KIT_SEGMENT_MODEL": "0",
                },
            )
            cfg = cfg_load_config(env, cursor_host.SPEC)
            self.assertTrue(cfg.segments["model"])
            env["AI_KIT_CURSOR_SEGMENT_MODEL"] = "0"
            cfg = cfg_load_config(env, cursor_host.SPEC)
            self.assertFalse(cfg.segments["model"])
            context = cursor_payload.core_cursor_context(
                SYNTHETIC, cfg, core_build_theme(cfg, cursor_host.HOST), env, None
            )
            self.assertNotIn("Synthetic Model", core_render(context, cursor_host.HOST)[1])

    def test_layout_config_places_extra_first(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            env = self._environment(root)
            config_path = root / "cursor.toml"
            config_path.write_text(
                "[[line]]\nmin_rows=0\nsegments=['cursor_extra','path','model']\n", encoding="utf-8"
            )
            env["AI_KIT_CURSOR_CONFIG_FILE"] = str(config_path)
            result = self._run_entry(SYNTHETIC, env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.splitlines()[0].startswith("🪙 extra: "))


NOW = 1_762_000_000.0
# A bold SGR span (parameter list holding 1) up to the next reset.
_BOLD_SPAN = re.compile(r"\x1b\[(?:[0-9]+;)*1(?:;[0-9]+)*m(.*?)\x1b\[0m")


class TestCursorQuotaShape(unittest.TestCase):
    """Claude's quota shape on Cursor: folded reset, days left, extra-spend alert (30.2-03)."""

    _context = TestCursorStatusLine._context
    _quota = staticmethod(TestCursorStatusLine._quota)

    @staticmethod
    def _plain(text: str) -> str:
        return re.sub(r"\x1b\[[0-9;]*m", "", text)

    @staticmethod
    def _end(seconds: float) -> int:
        return int((NOW + seconds) * 1000)

    @staticmethod
    def _bold_spans(ctx: Context, theme: Any) -> list[str]:
        with mock.patch("cursor_segments.time.time", return_value=NOW):
            return _BOLD_SPAN.findall(cast(str, cursor_segments.seg_cursor_extra(ctx, 400, theme)))

    def _reset(self, end_ms: int) -> str:
        ctx, theme = self._context(QuotaResult(state="ok", cycle_end_ms=end_ms))
        with mock.patch("cursor_segments.time.time", return_value=NOW):
            return self._plain(cast(str, cursor_segments.seg_cursor_reset(ctx, 400, theme)))

    def test_wide_target_and_narrow_tiers_on_the_synthetic_cache(self):
        quota = core_quota_state(core_synthetic_cache(NOW), NOW)
        ctx, theme = self._context(quota)
        end_ms = cast(tuple[int, int], quota.included_window)[1]
        date = datetime.fromtimestamp(end_ms / 1000).strftime("%b %d")
        with mock.patch("cursor_segments.time.time", return_value=NOW):
            parts = [
                cursor_segments.seg_cursor_included(ctx, 400, theme),
                cursor_segments.seg_cursor_api(ctx, 400, theme),
                cursor_segments.seg_cursor_extra(ctx, 400, theme),
            ]
            joined = " | ".join(self._plain(cast(str, part)) for part in parts)
            self.assertEqual(
                joined,
                f"⚡️ inc: +42% (↺ {date}, 17d) ≈ | ⚡️ api: +18% ≈ | 🪙 extra: +$2.50/$20.00 ≈",
            )
            narrow_width = common_types.util_visible_width("⚡️ inc: +42% ≈")
            narrow = cursor_segments.seg_cursor_included(ctx, narrow_width, theme)
            unsigned = cursor_segments.seg_cursor_included(ctx, narrow_width - 1, theme)
        self.assertEqual(self._plain(cast(str, narrow)), "⚡️ inc: +42% ≈")
        self.assertEqual(self._plain(cast(str, unsigned)), "⚡️ inc: 42% ≈")

    def test_days_left_adjacency(self):
        cases = {23 * 3600: "1d", 25 * 3600: "2d", 24 * 3600: "1d", 24 * 3600 + 60: "2d", 0: "0d"}
        for seconds, expected in cases.items():
            self.assertIn(f"({expected})", self._reset(self._end(seconds)), seconds)

    def test_passed_reset_on_a_stale_result_shows_zero_days(self):
        end = self._end(-3600)
        quota = QuotaResult(
            state="stale",
            cycle_start_ms=0,
            cycle_end_ms=end,
            included_pct=42.0,
            included_window=(0, end),
            od_kind="fixed",
            od_used_usd=2.5,
            od_ceiling_usd=20.0,
        )
        ctx, theme = self._context(quota)
        with mock.patch("cursor_segments.time.time", return_value=NOW):
            reset = self._plain(cast(str, cursor_segments.seg_cursor_reset(ctx, 400, theme)))
            included = self._plain(cast(str, cursor_segments.seg_cursor_included(ctx, 400, theme)))
        self.assertIn("(0d) ≈ stale", reset)
        self.assertIn(", 0d) ≈ stale", included)
        self.assertNotIn("-", reset)

    def test_weekly_plan_folds_the_weekly_end_and_the_reset_keeps_the_monthly_end(self):
        weekly_end = self._end(3 * 86400)
        monthly_end = self._end(17 * 86400)
        quota = QuotaResult(
            state="ok",
            cycle_start_ms=self._end(-13 * 86400),
            cycle_end_ms=monthly_end,
            included_pct=42.0,
            included_window=(self._end(-4 * 86400), weekly_end),
            included_period="weekly",
            od_kind="unavailable",
        )
        ctx, theme = self._context(quota)
        with mock.patch("cursor_segments.time.time", return_value=NOW):
            included = self._plain(cast(str, cursor_segments.seg_cursor_included(ctx, 400, theme)))
            reset = self._plain(cast(str, cursor_segments.seg_cursor_reset(ctx, 400, theme)))
        weekly_date = datetime.fromtimestamp(weekly_end / 1000).strftime("%b %d")
        monthly_date = datetime.fromtimestamp(monthly_end / 1000).strftime("%b %d")
        self.assertIn(f"(↺ {weekly_date}, 3d)", included)
        self.assertIn(f"↺ {monthly_date} (17d)", reset)

    def test_render_is_idempotent_for_the_same_payload_and_clock(self):
        ctx, theme = self._context(core_quota_state(core_synthetic_cache(NOW), NOW))
        with mock.patch("cursor_segments.time.time", return_value=NOW):
            first = cursor_segments.seg_cursor_included(ctx, 400, theme)
            second = cursor_segments.seg_cursor_included(ctx, 400, theme)
        self.assertEqual(first, second)

    def test_alert_colours_only_the_amount(self):
        ctx, theme = self._context(core_quota_state(core_synthetic_cache(NOW), NOW))
        with mock.patch("cursor_segments.time.time", return_value=NOW):
            ctx.line_conf = ctx.line_conf._replace(
                host_knobs={"cursor": {"extra_alert": True, "extra_alert_usd": 0.0}}
            )
            raw = cast(str, cursor_segments.seg_cursor_extra(ctx, 400, theme))
            spans = _BOLD_SPAN.findall(raw)
            self.assertEqual(len(spans), 1)
            self.assertEqual(self._plain(spans[0]), "$2.50")
            self.assertEqual(self._plain(raw), "🪙 extra: +$2.50/$20.00 ≈")
            ctx.line_conf = ctx.line_conf._replace(
                host_knobs={"cursor": {"extra_alert": True, "extra_alert_usd": 5.0}}
            )
            self.assertEqual(self._bold_spans(ctx, theme), [])
            ctx.line_conf = ctx.line_conf._replace(host_knobs=None)
            self.assertEqual(self._bold_spans(ctx, theme), [])

    def test_unlimited_extra_bolds_the_amount_on_an_override(self):
        quota = QuotaResult(state="ok", od_kind="unlimited", od_used_usd=2.5, fetched_at=1000)
        ctx, theme = self._context(quota)
        with mock.patch("cursor_segments.time.time", return_value=NOW):
            ctx.line_conf = ctx.line_conf._replace(
                host_knobs={"cursor": {"extra_alert": True, "extra_alert_usd": 0.0}}
            )
            raw = cast(str, cursor_segments.seg_cursor_extra(ctx, 400, theme))
            spans = _BOLD_SPAN.findall(raw)
            self.assertEqual([self._plain(span) for span in spans], ["$2.50"])


class TestCursorModelMaxAndDims(unittest.TestCase):
    """D-05/R6/R8 on Cursor: the max marker follows param_summary; zero rows drop the `×0`."""

    _context = TestCursorStatusLine._context
    _quota = staticmethod(TestCursorStatusLine._quota)

    def _ctx(self):
        ctx, theme = self._context(self._quota())
        ctx.model_name = "Synthetic Model · high"
        return ctx, theme

    def test_max_mode_appends_the_marker_after_param_summary(self):
        ctx, theme = self._ctx()
        ctx.model_max = True
        text = common_segments.seg_model(ctx, 200, theme)
        self.assertEqual(
            re.sub(r"\x1b\[[0-9;]*m", "", cast(str, text)),
            "🤖 Synthetic Model · high · max",
        )

    def test_max_mode_false_adds_nothing(self):
        ctx, theme = self._ctx()
        ctx.model_max = False
        text = common_segments.seg_model(ctx, 200, theme)
        self.assertEqual(
            re.sub(r"\x1b\[[0-9;]*m", "", cast(str, text)), "🤖 Synthetic Model · high"
        )

    def test_param_summary_suffix_is_not_duplicated(self):
        def shown(display_name, summary):
            raw = {"model": {"display_name": display_name, "param_summary": summary}}
            return cursor_payload.core_payload_fields(raw).model_name

        # Live Cursor 2026.10.22 name already ends with the context and effort.
        self.assertEqual(shown("GPT-5.6 Sol 272K High", "272K High"), "GPT-5.6 Sol 272K High")
        self.assertEqual(shown("GPT-5.6 Sol 272K High", " 272k  high "), "GPT-5.6 Sol 272K High")
        self.assertEqual(shown("Synthetic Model High", "high"), "Synthetic Model High")
        self.assertEqual(shown("Synthetic Model", "high"), "Synthetic Model · high")
        self.assertEqual(shown("", "high"), "high")

    def test_cursor_zero_rows_render_the_width_alone(self):
        ctx, theme = self._ctx()
        ctx.cols = 116
        ctx.lines = 0
        text = re.sub(r"\x1b\[[0-9;]*m", "", cast(str, common_segments.seg_alt_term_dimensions(
            ctx, 200, theme)))
        self.assertEqual(text, "📐 116")
        self.assertNotIn("×0", text)


def _quota_ending(days, included=42.0, used=2.5):
    """A fresh Cursor quota whose cycle (and included window) ends `days` after NOW."""
    end = int((NOW + days * 86400) * 1000)
    start = int((NOW - 13 * 86400) * 1000)
    return QuotaResult(
        state="ok",
        cycle_start_ms=start,
        cycle_end_ms=end,
        included_pct=included,
        api_pct=18.0,
        included_window=(start, end),
        od_kind="fixed",
        od_used_usd=used,
        od_ceiling_usd=20.0,
    )


def _cursor_render_context(home, raw, quota):
    """Build a Cursor render context the way the entry does, with one quota read."""
    config = cfg_default_config(cursor_host.SPEC)
    theme = core_build_theme(config, cursor_host.HOST)
    with mock.patch("cursor_payload.probe_read_quota", return_value=quota):
        ctx = cursor_payload.core_cursor_context(raw, config, theme, {"HOME": home}, None)
    return ctx, theme


def _cursor_raw(home, max_mode):
    return {
        "model": {"display_name": "Synthetic Model", "id": "m1", "param_summary": "high",
                  "max_mode": max_mode},
        "workspace": {"current_dir": home},
        "render_width_chars": 120,
        "transcript_path": "",
    }


class TestCursorSingleCacheRead(unittest.TestCase):
    """R5 (30.2-03): the render reads the quota cache once; segments never re-read it, so a
    cache refresh between two reads cannot mix values inside one render."""

    def test_segments_render_from_the_one_read_and_never_reread_the_cache(self):
        with tempfile.TemporaryDirectory(prefix="ai-kit-p302-") as home:
            first_read = _quota_ending(17, included=42.0, used=2.5)
            refreshed = _quota_ending(17, included=10.0, used=9.0)
            config = cfg_default_config(cursor_host.SPEC)
            theme = core_build_theme(config, cursor_host.HOST)
            # Each call to the cache-only reader would return the refreshed value.
            with mock.patch(
                "cursor_payload.probe_read_quota", side_effect=[first_read, refreshed]
            ) as reader:
                ctx = cursor_payload.core_cursor_context(
                    _cursor_raw(home, False), config, theme, {"HOME": home}, None
                )
                with mock.patch("cursor_segments.time.time", return_value=NOW):
                    first = [
                        cursor_segments.seg_cursor_included(ctx, 400, theme),
                        cursor_segments.seg_cursor_api(ctx, 400, theme),
                        cursor_segments.seg_cursor_extra(ctx, 400, theme),
                        cursor_segments.seg_cursor_reset(ctx, 400, theme),
                    ]
                    second = [
                        cursor_segments.seg_cursor_included(ctx, 400, theme),
                        cursor_segments.seg_cursor_api(ctx, 400, theme),
                        cursor_segments.seg_cursor_extra(ctx, 400, theme),
                        cursor_segments.seg_cursor_reset(ctx, 400, theme),
                    ]
            self.assertEqual(reader.call_count, 1)
        plain = " | ".join(
            re.sub(r"\x1b\[[0-9;]*m", "", cast(str, part)) for part in first if part
        )
        self.assertIn("42%", plain)
        self.assertIn("$2.50", plain)
        self.assertNotIn("10%", plain)
        self.assertNotIn("$9.00", plain)
        self.assertEqual(first, second)


class TestCursorDaysAndMaxPerRender(unittest.TestCase):
    """R6 (30.2-03): days left and the max marker come from one render's payload and cache;
    two renders with different inputs share no state."""

    @staticmethod
    def _render(ctx, theme):
        return {
            "model": _plain(common_segments.seg_model(ctx, 200, theme)),
            "reset": _plain(cursor_segments.seg_cursor_reset(ctx, 200, theme)),
        }

    def test_days_and_max_come_from_each_renders_own_payload_and_cache(self):
        with tempfile.TemporaryDirectory(prefix="ai-kit-p302-") as home:
            ctx_a, theme = _cursor_render_context(
                home, _cursor_raw(home, True), _quota_ending(17)
            )
            ctx_b, _theme_b = _cursor_render_context(
                home, _cursor_raw(home, False), _quota_ending(3)
            )
            with mock.patch("cursor_segments.time.time", return_value=NOW):
                first_a = self._render(ctx_a, theme)
                only_b = self._render(ctx_b, theme)
                second_a = self._render(ctx_a, theme)
        self.assertEqual(first_a["model"], "🤖 Synthetic Model · high · max")
        self.assertIn("(17d)", first_a["reset"])
        self.assertEqual(only_b["model"], "🤖 Synthetic Model · high")
        self.assertIn("(3d)", only_b["reset"])
        self.assertNotIn("17d", only_b["reset"])
        self.assertEqual(first_a, second_a)
        self.assertIsNot(ctx_a.probe_cache, ctx_b.probe_cache)


class TestCursorTranscriptAge(unittest.TestCase):
    """D-06/R3: the Cursor host renders the same shared transcript-age segment (30.2-03)."""

    NOW = 1_700_000_000
    _context = TestCursorStatusLine._context
    _quota = staticmethod(TestCursorStatusLine._quota)

    def test_cursor_renders_the_shared_age_of_its_transcript(self):
        plain = mock.Mock(c=lambda spec: "")
        with tempfile.TemporaryDirectory(prefix="ai-kit-p302-") as tmp:
            path = os.path.join(tmp, "t.jsonl")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{}\n")
            os.utime(path, (self.NOW - 300, self.NOW - 300))
            ctx, _theme = self._context(self._quota())
            ctx.transcript_path = path
            with mock.patch("common_probe.time.time", return_value=self.NOW):
                text = common_segments.seg_alt_time_ago(ctx, 200, plain)
        self.assertEqual(text, "⌛ " + common_types.fmt_ago(300) + common_types.RESET)

    def test_absent_transcript_hides_the_segment(self):
        plain = mock.Mock(c=lambda spec: "")
        ctx, _theme = self._context(self._quota())
        ctx.transcript_path = os.path.join(tempfile.gettempdir(), "ai-kit-p302-missing.jsonl")
        self.assertIsNone(common_segments.seg_alt_time_ago(ctx, 200, plain))


AGENT_EXE = "/scratch/.local/share/cursor-agent/versions/2026.10.22/node"


def _plain(text: str | None) -> str:
    return re.sub(r"\033\[[0-9;]*m", "", text or "")


class TestCursorContextFields(unittest.TestCase):
    """Neutral transcript_path and model_max carried by Cursor's context (D-05, D-06)."""

    def _context(self, payload: dict[str, Any]):
        config = cfg_default_config(cursor_host.SPEC)
        theme = core_build_theme(config, cursor_host.HOST)
        with tempfile.TemporaryDirectory(prefix="ai-kit-p302-") as tmp:
            env = {
                "HOME": tmp,
                "XDG_CACHE_HOME": os.path.join(tmp, "cache"),
                "XDG_CONFIG_HOME": os.path.join(tmp, "config"),
            }
            return cursor_payload.core_cursor_context(payload, config, theme, env, None)

    def test_transcript_path_is_carried(self):
        payload = json.loads(json.dumps(SYNTHETIC))
        payload["transcript_path"] = "/scratch/trans cript é/t.jsonl"
        ctx = self._context(payload)
        self.assertEqual(ctx.transcript_path, "/scratch/trans cript é/t.jsonl")
        self.assertIs(ctx.model_max, False)

    def test_only_a_true_boolean_max_mode_sets_model_max(self):
        for value, expected in ((True, True), (False, False), ("true", False), (None, False)):
            with self.subTest(value=value):
                payload = json.loads(json.dumps(SYNTHETIC))
                model = dict(payload.get("model") or {})
                if value is None:
                    model.pop("max_mode", None)  # None stands for an absent key
                else:
                    model["max_mode"] = value
                payload["model"] = model
                self.assertIs(self._context(payload).model_max, expected)

    def test_absent_transcript_path_gives_empty_string(self):
        payload = json.loads(json.dumps(SYNTHETIC))
        payload.pop("transcript_path", None)
        self.assertEqual(self._context(payload).transcript_path, "")


class TestCursorProcessMemory(unittest.TestCase):
    """Cursor's 🧮 segment through the shared ancestor walk; /proc and ps are faked."""

    _context = TestCursorStatusLine._context
    _quota = staticmethod(TestCursorStatusLine._quota)

    @contextlib.contextmanager
    def _fake_proc(
        self,
        table: dict[int, dict[str, Any]],
        parent: int,
        reads: list[int],
        *,
        ps: bool = False,
    ):
        """Serve /proc (or ps) readers and os.getppid from a pid table; log every pid read."""

        def reader(field: str):
            def read(pid: int):
                reads.append(pid)
                return table.get(pid, {}).get(field)

            return read

        if ps:
            targets = [
                (common_probe, "probe_ppid_via_ps", reader("ppid")),
                (common_probe, "probe_rss_kb_via_ps", reader("rss")),
                (cursor_probes, "probe_cmdline_via_ps", reader("cmd")),
            ]
        else:
            targets = [
                (common_probe, "probe_ppid_via_proc", reader("ppid")),
                (common_probe, "probe_rss_kb_via_proc", reader("rss")),
                (cursor_probes, "probe_cmdline_via_proc", reader("cmd")),
                (cursor_probes, "probe_exe_via_proc", reader("exe")),
            ]
        with contextlib.ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(common_probe, "probe_has_proc", return_value=not ps)
            )
            stack.enter_context(
                mock.patch.object(cursor_probes, "probe_has_proc", return_value=not ps)
            )
            stack.enter_context(mock.patch.object(os, "getppid", return_value=parent))
            for module, name, side_effect in targets:
                stack.enter_context(mock.patch.object(module, name, side_effect=side_effect))
            yield

    def _chain(self, agent: dict[str, Any], *, wrapper: dict[str, Any] | None = None):
        """Parent 200 is a plain shell whose parent 201 is the agent (or the wrapper pair)."""
        table: dict[int, dict[str, Any]] = {
            200: {"cmd": "/bin/sh -c x", "exe": "/usr/bin/sh", "ppid": 201},
            201: agent,
        }
        if wrapper is not None:
            table = {200: agent, 201: wrapper}
        return table

    def test_linux_chain_renders_agent_memory(self):
        table = self._chain(
            {"cmd": "node /opt/x/index.js", "exe": AGENT_EXE, "ppid": 1, "rss": 45056}
        )
        reads: list[int] = []
        ctx, theme = self._context(self._quota())
        with self._fake_proc(table, 200, reads):
            self.assertEqual(cursor_probes.probe_cursor_rss_bytes(), 46137344)
            shown = _plain(cursor_segments.seg_alt_process_memory(ctx, 200, theme))
        self.assertEqual(shown, "🧮 " + common_types.fmt_bytes(46137344))

    def test_command_line_match_without_agent_path(self):
        table = self._chain(
            {
                "cmd": "/scratch/.local/bin/cursor-agent --use-system-ca /x/index.js",
                "exe": "/usr/bin/node",
                "ppid": 1,
                "rss": 45056,
            }
        )
        with self._fake_proc(table, 200, []):
            self.assertEqual(cursor_probes.probe_cursor_rss_bytes(), 46137344)

    def test_node_outside_agent_directory_is_no_match(self):
        table = self._chain(
            {"cmd": "node /x/index.js", "exe": "/usr/bin/node", "ppid": 1, "rss": 45056}
        )
        ctx, theme = self._context(self._quota())
        with self._fake_proc(table, 200, []):
            self.assertIs(cursor_probes.probe_is_cursor(201), False)
            self.assertIsNone(cursor_probes.probe_cursor_rss_bytes())
            self.assertIsNone(cursor_segments.seg_alt_process_memory(ctx, 200, theme))

    def test_unreadable_first_parent_stops_the_walk(self):
        table: dict[int, dict[str, Any]] = {
            200: {"cmd": None, "exe": None, "ppid": 201},
            201: {"cmd": "node /x/index.js", "exe": AGENT_EXE, "ppid": 1, "rss": 45056},
        }
        reads: list[int] = []
        with self._fake_proc(table, 200, reads):
            self.assertIsNone(cursor_probes.probe_cursor_rss_bytes())
        self.assertNotIn(201, reads)

    def test_own_process_is_never_matched(self):
        own = os.getpid()
        table: dict[int, dict[str, Any]] = {
            own: {"cmd": "cursor-agent", "exe": AGENT_EXE, "ppid": 200, "rss": 45056},
            200: {"cmd": "/bin/sh", "exe": "/usr/bin/sh", "ppid": 1},
            1: {"cmd": "init", "exe": "/sbin/init", "ppid": 0},
        }
        reads: list[int] = []
        with self._fake_proc(table, 200, reads):
            self.assertIsNone(cursor_probes.probe_cursor_rss_bytes())
        self.assertNotIn(own, reads)

    def test_non_utf8_command_line_still_matches(self):
        raw = b"/x/cursor-agent\x00--flag\x00\xff\xfe\x00index.js\x00"
        with (
            mock.patch("builtins.open", mock.mock_open(read_data=raw)),
            mock.patch.object(cursor_probes, "probe_has_proc", return_value=True),
            mock.patch.object(cursor_probes, "probe_exe_via_proc", return_value=None),
        ):
            text = common_probe.probe_cmdline_via_proc(201)
            matched = cursor_probes.probe_is_cursor(201)
        self.assertIn("cursor-agent", text or "")
        self.assertIn("�", text or "")
        self.assertIs(matched, True)

    def test_no_proc_uses_the_ps_readers(self):
        table = self._chain(
            {"cmd": "cursor-agent --x", "ppid": 1, "rss": 45056},
        )
        reads: list[int] = []
        with self._fake_proc(table, 200, reads, ps=True):
            self.assertEqual(cursor_probes.probe_cursor_rss_bytes(), 46137344)
        self.assertIn(201, reads)

    def test_memory_is_read_once_per_render(self):
        ctx, theme = self._context(self._quota())
        with mock.patch.object(
            cursor_probes, "probe_cursor_rss_bytes", return_value=46137344
        ) as walk:
            cursor_segments.seg_alt_process_memory(ctx, 200, theme)
            cursor_segments.seg_alt_process_memory(ctx, 200, theme)
        walk.assert_called_once_with()

    def test_nearest_agent_wins_over_a_wrapper_further_up(self):
        table = self._chain(
            {"cmd": "node /x/index.js", "exe": AGENT_EXE, "rss": 45056},
            wrapper={"cmd": "/bin/sh /scratch/.local/bin/cursor-agent", "exe": "/usr/bin/sh",
                     "ppid": 1, "rss": 2048},
        )
        reads: list[int] = []
        with self._fake_proc(table, 200, reads):
            self.assertEqual(cursor_probes.probe_cursor_rss_bytes(), 46137344)
        self.assertNotIn(201, reads)

    def test_either_signal_alone_matches(self):
        cases = [
            {"cmd": "node /x/index.js", "exe": AGENT_EXE, "rss": 45056},
            {"cmd": "/scratch/.local/bin/cursor-agent --x", "exe": None, "rss": 45056},
        ]
        for agent in cases:
            with self.subTest(agent=agent), self._fake_proc(self._chain(agent), 200, []):
                self.assertEqual(cursor_probes.probe_cursor_rss_bytes(), 46137344)

    def test_depth_bound_stops_after_twelve_ancestors(self):
        table: dict[int, dict[str, Any]] = {
            200 + i: {"cmd": "/bin/sh", "exe": "/usr/bin/sh", "ppid": 201 + i} for i in range(13)
        }
        reads: list[int] = []
        with self._fake_proc(table, 200, reads):
            self.assertIsNone(cursor_probes.probe_cursor_rss_bytes())
        self.assertLessEqual(len(set(reads)), 12)


ANSI_SGR = re.compile(r"\x1b\[[0-9;]*m")
INVENTORY_PATH = ROOT / "tools" / "segments_inventory.toml"
SAMPLE_PAYLOAD_PATH = ROOT / "tests" / "fixtures" / "sample-input-cursor.json"
SAMPLE_TOML_PATH = ROOT / "tools" / "cursor-statusline.toml.sample"
SAMPLE_PAYLOAD = json.loads(SAMPLE_PAYLOAD_PATH.read_text(encoding="utf-8"))
REAL_CAPTURES = (
    ROOT / "tests/fixtures/cursor/payload_synthetic.json",
    ROOT / "tests/fixtures/cursor/payload_poc_redacted.json",
)


def _key_paths(node, prefix=""):
    """Dotted key paths of a JSON object, top level and nested."""
    paths: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else key
            paths.add(path)
            paths |= _key_paths(value, path)
    return paths


def _inventory():
    return tomllib.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def _strip_icon(text, icon):
    """ANSI-free text without the leading icon, its optional VS16 and one space."""
    text = ANSI_SGR.sub("", text)
    if text.startswith(icon):
        text = text[len(icon) :]
        if text.startswith("️"):
            text = text[1:]
        if text.startswith(" "):
            text = text[1:]
    return text


def _mask_parts(text):
    """Mask the parts that depend on the clock: reset dates, day counts and clock times."""
    text = re.sub(r"[A-Z][a-z]{2} \d{2}", "<date>", text)
    text = re.sub(r"\d+d\)", "<N>d)", text)
    return re.sub(r"\d{2}:\d{2}", "<clock>", text)


class TestCursorSampleFixture(unittest.TestCase):
    """30.2 D-09 / R10: the sample payload carries only Cursor payload fields."""

    def test_sample_keys_are_real_cursor_capture_keys(self):
        fields: set[str] = set()
        for capture in REAL_CAPTURES:
            fields |= _key_paths(json.loads(capture.read_text(encoding="utf-8")))
        self.assertFalse(_key_paths(SAMPLE_PAYLOAD) - fields)

    def test_claude_only_keys_are_absent(self):
        # design §5.1 excludes these two Claude-only keys from the Cursor payload
        self.assertNotIn("cost", SAMPLE_PAYLOAD)
        self.assertNotIn("rate_limits", SAMPLE_PAYLOAD)


class TestCursorSampleParity(unittest.TestCase):
    """30.2 D-09 / R10: each compared Cursor entry renders the sample the inventory ships.

    Compared: the Cursor-only entries (hosts == ["cursor"]) and every shared entry that
    carries cursor_sample. A shared entry without cursor_sample keeps its host-neutral sample.
    """

    _environment = TestCursorStatusLine._environment

    def _cursor_context(self, root):
        env = self._environment(root)
        config = cfg_default_config(cursor_host.SPEC)
        theme = core_build_theme(config, cursor_host.HOST)
        ctx = cursor_host.HOST.build_context(SAMPLE_PAYLOAD, config, theme, env, None)
        return ctx, theme

    def test_compared_entries_render_their_sample(self):
        compared = {
            key: entry
            for key, entry in _inventory().items()
            if "cursor" in entry["hosts"]
            and (entry["hosts"] == ["cursor"] or "cursor_sample" in entry)
        }
        self.assertTrue(compared)
        with tempfile.TemporaryDirectory() as temporary, mock.patch("time.time", return_value=NOW):
            ctx, theme = self._cursor_context(pathlib.Path(temporary))
            for key, entry in compared.items():
                with self.subTest(key=key):
                    rendered = cursor_host.BUILDERS[key](ctx, 400, theme)
                    self.assertTrue(rendered, f"{key} renders nothing on the sample payload")
                    sample = entry.get("cursor_sample", entry["sample"])
                    self.assertEqual(
                        _mask_parts(_strip_icon(rendered or "", entry["icon"])),
                        _mask_parts(_strip_icon(sample, entry["icon"])),
                    )


class TestSegmentIconParity(unittest.TestCase):
    """30.2 D-07 / R2: every inventory entry renders with the icon the inventory lists."""

    _environment = TestCursorStatusLine._environment

    @staticmethod
    def _expected_prefix(key, entry):
        # git_branch keeps its existing leading "[" before the icon
        return ("[" if key == "git_branch" else "") + entry["icon"]

    @staticmethod
    def _seed_probes(ctx, transcript):
        """Seed the per-render probes so no segment touches git, /proc or the real transcript."""
        ctx.probe_cache["git"] = common_types.GitSnapshot(
            in_repo=True, branch="main", dirty="modified", is_worktree=True,
            wt_name="wt", root_name="", root_path="",
        )
        ctx.probe_cache["ago"] = "5m 0s ago"
        ctx.probe_cache["rss"] = 1048576
        ctx.transcript_path = str(transcript)
        ctx.t_start = time.perf_counter()
        ctx.slowest = ("path", 1000)

    def test_cursor_entries_start_with_their_icon(self):
        inventory = _inventory()
        with tempfile.TemporaryDirectory() as temporary, mock.patch("time.time", return_value=NOW):
            root = pathlib.Path(temporary)
            env = self._environment(root)
            transcript = root / "transcript.jsonl"
            transcript.write_text("{}\n", encoding="utf-8")
            config = cfg_default_config(cursor_host.SPEC)
            theme = core_build_theme(config, cursor_host.HOST)
            ctx = cursor_host.HOST.build_context(SAMPLE_PAYLOAD, config, theme, env, None)
            self._seed_probes(ctx, transcript)
            for key, entry in inventory.items():
                if "cursor" not in entry["hosts"]:
                    continue
                with self.subTest(key=key):
                    rendered = cursor_host.BUILDERS[key](ctx, 400, theme)
                    self.assertTrue(rendered, f"{key} renders nothing on the sample payload")
                    plain = ANSI_SGR.sub("", rendered or "")
                    self.assertTrue(plain.startswith(self._expected_prefix(key, entry)), plain)

    def test_claude_entries_start_with_their_icon(self):
        from tests import test_status_line  # the Claude context helper, reused not copied

        inventory = _inventory()
        golden = json.loads((ROOT / "tests/fixtures/golden/inputs_full.json").read_text("utf-8"))
        case = golden[0]
        self.assertEqual(case["name"], "full-wide-200x50")
        raw = case["raw"]
        with tempfile.TemporaryDirectory() as temporary:
            transcript = pathlib.Path(temporary) / "transcript.jsonl"
            transcript.write_text("{}\n", encoding="utf-8")
            # _data hard-codes raw={}, so the golden raw fields go through its keyword overrides
            ctx = test_status_line._data(
                cols=case["cols"], lines=case["lines"],
                model_name=raw["model"]["display_name"], model_id=raw["model"]["id"],
                work_dir=raw["workspace"]["current_dir"],
                context_pct=raw["context_window"]["used_percentage"],
                context_max=raw["context_window"]["context_window_size"],
                effort=raw["effort"]["level"],
                added=raw["cost"]["total_lines_added"],
                removed=raw["cost"]["total_lines_removed"],
                cost=raw["cost"]["total_cost_usd"],
                total_ms=raw["cost"]["total_duration_ms"],
                api_ms=raw["cost"]["total_api_duration_ms"],
                rate_limits=raw["rate_limits"],
                in_repo=True, is_worktree=True, wt_name="wt", dirty="modified",
                ago="5m 0s ago", mem_bytes=1048576, t_start=time.perf_counter(),
                slowest=("path", 1000), todo_state="in_progress", todo_text="write tests",
            )
            ctx.transcript_path = str(transcript)
            for key, entry in inventory.items():
                if "claude" not in entry["hosts"]:
                    continue
                with self.subTest(key=key):
                    rendered = claude_host.BUILDERS[key](ctx, 400, ctx.theme)
                    self.assertTrue(rendered, f"{key} renders nothing on the default payload")
                    plain = ANSI_SGR.sub("", rendered or "")
                    self.assertTrue(plain.startswith(self._expected_prefix(key, entry)), plain)

    def test_shared_keys_have_the_same_icon_on_both_hosts(self):
        inventory = _inventory()
        for key, entry in inventory.items():
            if entry["hosts"] == ["claude", "cursor"]:
                with self.subTest(key=key):
                    self.assertEqual(entry["icon"], inventory[key]["icon"])
                    self.assertTrue(entry["icon"], f"{key} has no icon")


class TestCursorNoInventedValues(unittest.TestCase):
    """30.2 D-07 / R7: no Cursor render shows a Claude window, a 0 row count or a default."""

    _environment = TestCursorStatusLine._environment
    _context = TestCursorStatusLine._context
    _quota = staticmethod(TestCursorStatusLine._quota)
    _chain = TestCursorProcessMemory._chain

    def _fake_proc(self, table, parent, reads, **kwargs):
        """The process-memory fake, reused by import (pyright needs the explicit self cast)."""
        return TestCursorProcessMemory._fake_proc(cast(Any, self), table, parent, reads, **kwargs)

    @staticmethod
    def _memory_render(ctx, theme):
        """A full Cursor render with only alt_process_memory enabled, as plain text."""
        config = cfg_default_config(cursor_host.SPEC)
        cfg = config._replace(
            layout=[common_types.Line(min_rows=0, segments=["alt_process_memory"])],
            segments={key: key == "alt_process_memory" for key in config.segments},
        )
        return ANSI_SGR.sub("", "".join(core_render(ctx, cursor_host.HOST, cfg=cfg)))

    def test_no_cursor_ancestor_shows_no_memory(self):
        table = self._chain(
            {"cmd": "/usr/bin/bash", "exe": "/usr/bin/bash", "ppid": 1, "rss": 45056}
        )
        ctx, theme = self._context(self._quota())
        with self._fake_proc(table, 200, []):
            self.assertIsNone(cursor_segments.seg_alt_process_memory(ctx, 400, theme))
            ctx, _theme = self._context(self._quota())
            self.assertNotIn("🧮", self._memory_render(ctx, theme))

    def test_cursor_agent_ancestor_shows_its_memory_once(self):
        table = self._chain(
            {"cmd": "node /opt/x/index.js", "exe": AGENT_EXE, "ppid": 1, "rss": 45056}
        )
        ctx, theme = self._context(self._quota())
        with self._fake_proc(table, 200, []):
            rss = cursor_probes.probe_cursor_rss_bytes()
            assert rss is not None, "the fake agent chain must match"
            expected = common_types.fmt_bytes(rss)
            text = self._memory_render(ctx, theme)
        self.assertEqual(text.count("🧮"), 1)
        self.assertIn(f"🧮 {expected}", text)

    def _run_all_segments(self, payload_path, env):
        for key in cursor_host.SEGMENTS:
            env[f"AI_KIT_CURSOR_SEGMENT_{key.upper()}"] = "true"
        return subprocess.run(
            [sys.executable, "-S", str(ENTRY)],
            input=payload_path.read_text(encoding="utf-8"),
            capture_output=True,
            text=True,
            env=env,
            check=False,
            timeout=10,
        )

    def test_fixtures_never_render_claude_windows_or_zero_counts(self):
        payloads = (*REAL_CAPTURES, SAMPLE_PAYLOAD_PATH)
        with tempfile.TemporaryDirectory() as temporary:
            for payload in payloads:
                with self.subTest(payload=payload.name):
                    env = self._environment(pathlib.Path(temporary))
                    result = self._run_all_segments(payload, env)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for banned in ("5h:", "7d:", "×0"):
                        self.assertNotIn(banned, result.stdout)

    def test_empty_cache_shows_no_quota_and_no_percent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            home = root / "home"
            empty_cache = root / "empty-cache"
            home.mkdir()
            empty_cache.mkdir()
            env = {
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(root / "xdg"),
                "XDG_CACHE_HOME": str(empty_cache),
                "PATH": os.defpath,
            }
            result = self._run_all_segments(SAMPLE_PAYLOAD_PATH, env)
        self.assertEqual(result.returncode, 0, result.stderr)
        for banned in ("inc:", "api:", "extra", "5h:", "7d:"):
            self.assertNotIn(banned, result.stdout)


class TestCursorTomlSample(unittest.TestCase):
    """30.2 D-09 / D-12: the TOML sample lists the defaults and the commented [cursor] block."""

    def test_segment_block_lists_every_default_in_order(self):
        text = SAMPLE_TOML_PATH.read_text(encoding="utf-8")
        block = text.split("# [segments]", 1)[1].split("## Uncomment", 1)[0]
        pairs = re.findall(r"^# (\w+) = (true|false)$", block, re.MULTILINE)
        self.assertEqual(
            pairs, [(key, str(value).lower()) for key, value in cursor_host.SEGMENTS.items()]
        )

    def test_header_names_the_alert_overrides_and_the_cursor_block_is_commented(self):
        text = SAMPLE_TOML_PATH.read_text(encoding="utf-8")
        header = text.split("# [segments]", 1)[0]
        self.assertIn("AI_KIT_CURSOR_EXTRA_ALERT", header)
        self.assertIn("AI_KIT_CURSOR_EXTRA_ALERT_USD", header)
        for line in ("# [cursor]", "# extra_alert = true", "# extra_alert_usd = 20.0"):
            self.assertIn(line, text.splitlines())
        tomllib.loads(text)  # the all-comment sample parses

    def test_uncommenting_the_switch_alone_sets_extra_alert_without_an_override(self):
        lines = SAMPLE_TOML_PATH.read_text(encoding="utf-8").splitlines()
        uncommented = [
            line[2:] if line in ("# [cursor]", "# extra_alert = true") else line for line in lines
        ]
        parsed = tomllib.loads("\n".join(uncommented))
        self.assertEqual(parsed["cursor"], {"extra_alert": True})


class TestCursorDefaults(unittest.TestCase):
    """30.2 D-09 / R9: Cursor's defaults equal Claude's on every shared key."""

    _environment = TestCursorStatusLine._environment

    def test_shared_keys_have_equal_defaults(self):
        shared = set(claude_host.SEGMENTS) & set(cursor_host.SEGMENTS)
        self.assertTrue(shared)
        for key in sorted(shared):
            with self.subTest(key=key):
                self.assertEqual(cursor_host.SEGMENTS[key], claude_host.SEGMENTS[key])

    def test_cursor_only_defaults(self):
        segments = cursor_host.SEGMENTS
        self.assertTrue(segments["cursor_included"])
        self.assertFalse(segments["cursor_api"])
        self.assertTrue(segments["cursor_extra"])
        self.assertFalse(segments["cursor_reset"])

    def test_new_keys_are_off_on_both_hosts(self):
        for host in (claude_host.SEGMENTS, cursor_host.SEGMENTS):
            for key in ("alt_process_memory", "alt_time_ago", "alt_term_dimensions"):
                with self.subTest(key=key):
                    self.assertFalse(host[key])

    def test_layout_appends_the_two_new_keys_to_the_diagnostics_row(self):
        row = cursor_host.LAYOUT[2].segments
        self.assertEqual(row[-2:], ["alt_time_ago", "alt_process_memory"])

    def test_no_config_loads_exactly_the_defaults(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = self._environment(pathlib.Path(temporary))
            cfg = cfg_load_config(env, cursor_host.SPEC)
        self.assertEqual(cfg.segments, cursor_host.SEGMENTS)

    def test_explicit_switch_wins_over_the_default(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = self._environment(pathlib.Path(temporary))
            config_dir = pathlib.Path(env["XDG_CONFIG_HOME"]) / "ai-kit"
            config_dir.mkdir(parents=True, exist_ok=True)
            (config_dir / "cursor-statusline.toml").write_text(
                "[segments]\ncursor_reset = true\n", encoding="utf-8"
            )
            cfg = cfg_load_config(env, cursor_host.SPEC)
        self.assertTrue(cfg.segments["cursor_reset"])


if __name__ == "__main__":
    unittest.main()
