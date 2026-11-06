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
import common_probe
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
        self.assertIn("inc ", cast(str, wide))
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


if __name__ == "__main__":
    unittest.main()
