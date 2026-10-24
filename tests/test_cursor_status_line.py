"""Synthetic payload and cache tests for the Cursor status-line host."""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest
from typing import Any, cast
from unittest import mock

from tests.cursor_fakes import run_like_cursor
from tools.cursor_quota import (
    QuotaResult,
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
import common_types
import cursor_host
import cursor_payload
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
        self.assertIn("inc ", cast(str, wide))
        self.assertIn("-47%", cast(str, wide))
        self.assertIn(theme.c("YELLOW"), cast(str, wide))
        self.assertIn(" ≈", cast(str, wide))
        self.assertNotIn("-47%", narrow)
        self.assertIn("47%", narrow)
        neutral_ctx, neutral_theme = self._context(self._quota(included_window=None))
        neutral = cursor_segments.seg_cursor_included(neutral_ctx, 40, neutral_theme)
        self.assertIn(neutral_theme.c("WHITE"), cast(str, neutral))

    def test_api_default_toggle_and_all_extra_kinds(self):
        self.assertFalse(cursor_host.SEGMENTS["cursor_api"])
        context, theme = self._context(self._quota())
        context.line_conf = context.line_conf._replace(
            segments={**context.line_conf.segments, "cursor_api": False}
        )
        self.assertIsNone(cursor_segments.seg_cursor_api(context, 100, theme))
        enabled_config = context.line_conf._replace(
            segments={**context.line_conf.segments, "cursor_api": True}
        )
        context.line_conf = enabled_config
        enabled_context = context
        api = cursor_segments.seg_cursor_api(enabled_context, 100, theme)
        self.assertIn("api ", cast(str, api))
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
        )
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

    def test_reset_is_local_time_and_weekly_window(self):
        weekly = self._quota(included_window=(93_600_000, 698_400_000))
        window = cast(tuple[int, int], weekly.included_window)
        self.assertEqual(window[0], window[1] - 7 * 86400 * 1000)
        ctx, theme = self._context(weekly)
        with mock.patch.dict(os.environ, {"TZ": "UTC"}):
            time.tzset()
            utc = cursor_segments.seg_cursor_reset(ctx, 100, theme)
        with mock.patch.dict(os.environ, {"TZ": "Asia/Tokyo"}):
            time.tzset()
            tokyo = cursor_segments.seg_cursor_reset(ctx, 100, theme)
        time.tzset()
        self.assertNotEqual(utc, tokyo)
        self.assertIn("≈", cast(str, utc))

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
            self.assertTrue(result.stdout.splitlines()[0].startswith("extra "))


if __name__ == "__main__":
    unittest.main()
