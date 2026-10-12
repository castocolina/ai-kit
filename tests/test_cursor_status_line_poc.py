"""Tests for tools/cursor-status-line-poc.py (Cursor Agent statusline POC)."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import types
import unittest
from pathlib import Path

PERIOD_FIXED = {
    "billingCycleStart": "1700000000000",
    "billingCycleEnd": "1702592000000",
    "planUsage": {
        "totalPercentUsed": 42.0,
        "autoPercentUsed": 10.0,
        "apiPercentUsed": 32.0,
        "includedSpend": 840,
        "limit": 2000,
    },
    "spendLimitUsage": {
        "individualUsed": 150,
        "individualLimit": 2000,
        "limitType": "user",
    },
}
HARD_FIXED = {"hardLimit": 20, "noUsageBasedAllowed": False}
HARD_UNLIMITED = {"hardLimit": 2147483647, "noUsageBasedAllowed": False}
HARD_DISABLED = {"hardLimit": 0, "noUsageBasedAllowed": True}
HARD_ZERO_ENABLED = {"hardLimit": 0, "noUsageBasedAllowed": False}
PLAN = {"planInfo": {"planName": "Pro", "billingCycleEnd": "1702592000000"}}

POC = Path(__file__).resolve().parents[1] / "tools" / "cursor-status-line-poc.py"


def load_poc():
    spec = importlib.util.spec_from_file_location("cursor_status_line_poc", POC)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class TestPayloadRender(unittest.TestCase):
    def test_model_and_path_from_payload(self):
        mod = load_poc()
        payload = {
            "session_id": "t",
            "model": {"id": "x", "display_name": "GPT POC", "param_summary": "High"},
            "workspace": {"current_dir": "/tmp/poc-proj"},
            "context_window": {
                "used_percentage": 34.5,
                "context_window_size": 200000,
            },
            "render_width_chars": 100,
        }
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            out = mod.render_for_test(payload, env)
        self.assertIn("GPT POC", out)
        self.assertIn("34", out)
        self.assertIn("poc-proj", out)
        self.assertIn("200K", out)  # fmt_tokens(200000)
        self.assertIn("High", out)  # param_summary verbatim

    def test_null_context_pct_omits_percent(self):
        mod = load_poc()
        payload = {
            "model": {"display_name": "M"},
            "workspace": {"current_dir": "/tmp/x"},
            "context_window": {"used_percentage": None, "context_window_size": 1000},
        }
        with tempfile.TemporaryDirectory() as td:
            out = mod.render_for_test(
                payload, {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            )
        self.assertIn("M", out)
        self.assertNotIn("None", out)
        self.assertNotRegex(out, r"\b0%\b")

    def test_max_mode_marker(self):
        mod = load_poc()
        payload = {
            "model": {"display_name": "M", "max_mode": True},
            "workspace": {"current_dir": "/tmp/x"},
            "context_window": {"used_percentage": 1, "context_window_size": 1000},
        }
        with tempfile.TemporaryDirectory() as td:
            out = mod.render_for_test(
                payload, {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            )
        self.assertIn("· max", out)

    def test_toml_segments_merge_and_line_replace(self):
        mod = load_poc()
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "ai-kit" / "cursor-statusline-poc.toml"
            cfg.parent.mkdir(parents=True)
            cfg.write_text(
                '[segments]\npath = false\n\n[[line]]\nmin_rows = 0\nsegments = ["model_compact"]\n',
                encoding="utf-8",
            )
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            c = mod.load_config(env)
            self.assertFalse(c.segments["path"])
            self.assertEqual(c.layout, [(0, ["model_compact"])])


class TestDumpPayload(unittest.TestCase):
    def test_dump_payload_writes_exact_raw_bytes(self):
        mod = load_poc()
        raw = b'{"model":{"display_name":"D"},"workspace":{"current_dir":"/tmp/x"},'
        raw += b'"context_window":{"used_percentage":1,"context_window_size":1000}}\n'
        with tempfile.TemporaryDirectory() as td:
            dump = Path(td) / "out" / "payload.json"
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            mod.render_from_raw(raw, env, dump_payload_path=str(dump))
            self.assertEqual(dump.read_bytes(), raw)

    def test_main_dump_payload_argv(self):
        mod = load_poc()
        raw = b'{"model":{"display_name":"D"},"workspace":{"current_dir":"/tmp/x"},'
        raw += b'"context_window":{"used_percentage":1,"context_window_size":1000}}\n'
        with tempfile.TemporaryDirectory() as td:
            dump = Path(td) / "p.json"
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            rc = mod.main(
                argv=["cursor-status-line-poc.py", "--dump-payload", str(dump)],
                stdin=io.BytesIO(raw),
                env=env,
            )
            self.assertEqual(rc, 0)
            self.assertEqual(dump.read_bytes(), raw)

    def test_main_never_raises_on_bad_stdin(self):
        mod = load_poc()
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            rc = mod.main(argv=["poc"], stdin=io.BytesIO(b"not-json"), env=env)
            self.assertEqual(rc, 0)
            rc2 = mod.main(argv=["poc"], stdin=io.BytesIO(b""), env=env)
            self.assertEqual(rc2, 0)

    def test_python_s_import(self):
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as td:
            env = {
                "HOME": td,
                "XDG_CONFIG_HOME": td,
                "XDG_CACHE_HOME": td,
                "PATH": os.environ.get("PATH", ""),
                "LANG": os.environ.get("LANG", "C.UTF-8"),
            }
            r = subprocess.run(
                [sys.executable, "-S", str(POC)],
                input=b"{}",
                capture_output=True,
                env=env,
                check=False,
            )
        self.assertNotIn(b"ImportError", r.stderr)
        self.assertNotIn(b"ModuleNotFoundError", r.stderr)


class TestLocalProbes(unittest.TestCase):
    def test_system_available_bytes_positive_on_linux(self):
        mod = load_poc()
        n = mod.probe_system_available_bytes()
        if os.path.exists("/proc/meminfo"):
            self.assertIsNotNone(n)
            self.assertGreater(n, 0)

    def test_process_rss_returns_int(self):
        if not Path("/proc").is_dir():
            self.skipTest("Linux /proc required for POC RSS probe")
        mod = load_poc()
        n = mod.probe_process_rss_bytes()
        self.assertIsInstance(n, int)
        self.assertGreater(n, 0)

    def test_git_branch_in_repo(self):
        mod = load_poc()
        root = str(Path(__file__).resolve().parents[1])
        snap = mod.probe_git_snapshot(root)
        self.assertIsInstance(snap, dict)
        self.assertTrue(snap["in_repo"])
        self.assertIn(snap["dirty"], ("clean", "modified", "untracked"))
        self.assertTrue(snap["branch"] or snap["is_worktree"])

    def test_worktree_struck_on_main_checkout(self):
        mod = load_poc()
        theme = mod.default_theme()
        ctx = types.SimpleNamespace(work_dir="/tmp/x", home="/tmp")
        mod.probe_git_snapshot = lambda _wd: {
            "in_repo": True,
            "branch": "main",
            "dirty": "clean",
            "is_worktree": False,
            "wt_name": "",
        }
        s = mod.seg_alt_git_worktree(ctx, 80, theme)
        self.assertIsNotNone(s)
        self.assertIn("⎇", s)
        self.assertIn("\033[9m", s)
        self.assertIn(theme.c("GREY"), s)

    def test_worktree_cyan_on_linked(self):
        mod = load_poc()
        theme = mod.default_theme()
        ctx = types.SimpleNamespace(work_dir="/tmp/x", home="/tmp")
        mod.probe_git_snapshot = lambda _wd: {
            "in_repo": True,
            "branch": "feat",
            "dirty": "clean",
            "is_worktree": True,
            "wt_name": "poc-wt",
        }
        s = mod.seg_alt_git_worktree(ctx, 80, theme)
        self.assertIsNotNone(s)
        self.assertIn("poc-wt", s)
        self.assertIn(theme.c("CYAN"), s)
        self.assertNotIn("\033[9m", s)

    def test_process_memory_fmt_shape(self):
        mod = load_poc()
        theme = mod.default_theme()
        ctx = types.SimpleNamespace()
        mod.probe_process_rss_bytes = lambda: 85 * 1024 * 1024
        s = mod.seg_process_memory(ctx, 80, theme)
        self.assertIsNotNone(s)
        self.assertIn("🧮", s)
        self.assertRegex(s, r"\d+(\.\d)?MB")

    def test_system_memory_long_form(self):
        mod = load_poc()
        theme = mod.default_theme()
        ctx = types.SimpleNamespace()
        mod.probe_system_available_bytes = lambda: int(5.5 * 1024**3)
        s = mod.seg_system_memory(ctx, 80, theme)
        self.assertIsNotNone(s)
        self.assertIn("GiB free", s)

    def test_slowest_skips_meta_second_pass(self):
        mod = load_poc()
        payload = {
            "model": {"display_name": "M"},
            "workspace": {"current_dir": str(Path(__file__).resolve().parents[1])},
            "context_window": {"used_percentage": 1, "context_window_size": 1000},
            "render_width_chars": 200,
        }
        with tempfile.TemporaryDirectory() as td:
            out = mod.render_for_test(
                payload, {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            )
        if "🐌" in out:
            self.assertNotRegex(out, r"🐌\s*(render_time|slowest)\b")

    def test_git_probe_once_per_render(self):
        mod = load_poc()
        n = {"calls": 0}
        real = mod.probe_git_snapshot

        def counted(wd):
            n["calls"] += 1
            return real(wd)

        mod.probe_git_snapshot = counted
        payload = {
            "model": {"display_name": "M"},
            "workspace": {"current_dir": str(Path(__file__).resolve().parents[1])},
            "context_window": {"used_percentage": 1, "context_window_size": 1000},
            "render_width_chars": 200,
        }
        with tempfile.TemporaryDirectory() as td:
            mod.render_for_test(
                payload, {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            )
        self.assertEqual(n["calls"], 1)


class TestQuotaFetch(unittest.TestCase):
    def test_normalize_fixed(self):
        mod = load_poc()
        q = mod.normalize_quota_responses(PERIOD_FIXED, HARD_FIXED, PLAN)
        self.assertEqual(q["total_pct"], 42.0)
        self.assertEqual(q["auto_pct"], 10.0)
        self.assertEqual(q["api_pct"], 32.0)
        self.assertEqual(q["on_demand"]["kind"], "fixed")
        self.assertEqual(q["on_demand"]["used_dollars"], 1.5)
        self.assertEqual(q["on_demand"]["ceiling_dollars"], 20.0)
        self.assertEqual(q["cycle_end_ms"], 1702592000000)

    def test_normalize_unlimited_and_disabled(self):
        mod = load_poc()
        u = mod.normalize_quota_responses(PERIOD_FIXED, HARD_UNLIMITED, PLAN)
        self.assertEqual(u["on_demand"]["kind"], "unlimited")
        self.assertEqual(u["on_demand"]["used_dollars"], 1.5)
        self.assertIsNone(u["on_demand"].get("ceiling_dollars"))
        d = mod.normalize_quota_responses(PERIOD_FIXED, HARD_DISABLED, PLAN)
        self.assertEqual(d["on_demand"]["kind"], "disabled")
        z = mod.normalize_quota_responses(PERIOD_FIXED, HARD_ZERO_ENABLED, PLAN)
        self.assertEqual(z["on_demand"]["kind"], "disabled")

    def test_normalize_unavailable_without_plan_usage(self):
        mod = load_poc()
        q = mod.normalize_quota_responses(
            {"billingCycleStart": "0", "billingCycleEnd": "0"}, HARD_FIXED, PLAN
        )
        self.assertEqual(q["on_demand"]["kind"], "unavailable")

    def test_cache_does_not_store_token(self):
        mod = load_poc()
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CACHE_HOME": td}
            mod.write_quota_cache(
                env,
                {"total_pct": 10, "fetched_at": 1, "on_demand": {"kind": "disabled"}},
            )
            text = Path(td, "ai-kit", "cursor-statusline-poc", "usage.json").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("accessToken", text)
            self.assertNotIn("eyJ", text)

    def test_cache_path_defaults_without_xdg_cache_home(self):
        mod = load_poc()
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td}
            p = mod.quota_cache_path(env)
            self.assertEqual(
                p,
                Path(td) / ".cache" / "ai-kit" / "cursor-statusline-poc" / "usage.json",
            )

    def test_rejects_non_https_endpoint(self):
        mod = load_poc()
        with self.assertRaises(ValueError):
            mod.quota_endpoint_url({"CURSOR_API_ENDPOINT": "http://evil.example"})

    def test_rejects_cross_host_redirect(self):
        mod = load_poc()
        self.assertFalse(
            mod.redirect_allowed("https://api2.cursor.sh/x", "https://evil.example/x")
        )
        self.assertTrue(
            mod.redirect_allowed("https://api2.cursor.sh/a", "https://api2.cursor.sh/b")
        )

    def test_default_opener_refuses_cross_host_redirect(self):
        import urllib.error
        import urllib.request

        mod = load_poc()
        self.assertTrue(
            issubclass(mod.QuotaRedirectHandler, urllib.request.HTTPRedirectHandler)
        )
        handler = mod.QuotaRedirectHandler()
        req = urllib.request.Request(
            "https://api2.cursor.sh/aiserver.v1.DashboardService/GetHardLimit",
            data=b"{}",
            headers={"Authorization": "Bearer tok"},
            method="POST",
        )
        refused = False
        try:
            out = handler.redirect_request(
                req, None, 302, "Found", {}, "https://evil.example/x"
            )
            refused = out is None
        except (urllib.error.HTTPError, ValueError, OSError):
            refused = True
        self.assertTrue(refused)

    def test_fetch_quota_posts_three_methods(self):
        mod = load_poc()
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(
                (req.full_url, req.get_header("Authorization"), req.data, timeout)
            )

            class R:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def read(self):
                    if "GetCurrentPeriodUsage" in req.full_url:
                        return json.dumps(PERIOD_FIXED).encode()
                    if "GetHardLimit" in req.full_url:
                        return json.dumps(HARD_FIXED).encode()
                    return json.dumps(PLAN).encode()

            return R()

        with tempfile.TemporaryDirectory() as td:
            auth = Path(td) / "cursor" / "auth.json"
            auth.parent.mkdir(parents=True)
            auth.write_text(
                '{"accessToken":"tok-test","refreshToken":"r"}', encoding="utf-8"
            )
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            q = mod.fetch_quota(env, urlopen=fake_urlopen, now=1_700_100_000)
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(u.startswith("https://api2.cursor.sh/") for u, *_ in calls))
        self.assertTrue(all(a == "Bearer tok-test" for _, a, *_ in calls))
        self.assertTrue(all(t == 0.8 for *_, t in calls))
        self.assertEqual(q["on_demand"]["kind"], "fixed")

    def test_total_pct_from_spend_over_limit(self):
        mod = load_poc()
        period = {
            "billingCycleStart": "1",
            "billingCycleEnd": "2",
            "planUsage": {"includedSpend": 50, "limit": 200},
        }
        q = mod.normalize_quota_responses(period, HARD_DISABLED, PLAN)
        self.assertEqual(q["total_pct"], 25.0)

    def test_total_pct_none_when_limit_zero(self):
        mod = load_poc()
        period = {
            "billingCycleStart": "1",
            "billingCycleEnd": "2",
            "planUsage": {"includedSpend": 50, "limit": 0},
        }
        q = mod.normalize_quota_responses(period, HARD_DISABLED, PLAN)
        self.assertIsNone(q["total_pct"])

    def test_cycle_end_falls_back_to_planinfo(self):
        mod = load_poc()
        period = {"billingCycleStart": "10", "planUsage": {"totalPercentUsed": 1}}
        q = mod.normalize_quota_responses(period, HARD_DISABLED, PLAN)
        self.assertEqual(q["cycle_end_ms"], 1702592000000)

    def test_missing_auth_no_network_hides_quota(self):
        mod = load_poc()
        calls = []

        def no(req, timeout=None):
            calls.append(1)
            raise AssertionError("no network without auth")

        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            q = mod.fetch_quota(env, now=1, urlopen=no)
            self.assertEqual(calls, [])
            self.assertTrue(
                q["on_demand"]["kind"] == "unavailable" or q.get("total_pct") is None
            )

    def test_missing_auth_still_serves_fresh_cache(self):
        mod = load_poc()
        calls = []

        def no(req, timeout=None):
            calls.append(1)
            raise AssertionError("no network without auth")

        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            mod.write_quota_cache(
                env,
                {
                    "total_pct": 42,
                    "fetched_at": 1000,
                    "stale": False,
                    "on_demand": {"kind": "disabled"},
                    "cycle_start_ms": 0,
                    "cycle_end_ms": 1,
                },
            )
            q = mod.fetch_quota(env, now=1030, urlopen=no)
            self.assertEqual(calls, [])
            self.assertEqual(q["total_pct"], 42)
            self.assertFalse(q.get("stale"))

    def test_malformed_auth_skips_network(self):
        mod = load_poc()
        calls = []

        def no(req, timeout=None):
            calls.append(1)
            raise AssertionError("no network on bad auth")

        with tempfile.TemporaryDirectory() as td:
            auth = Path(td) / "cursor" / "auth.json"
            auth.parent.mkdir(parents=True)
            auth.write_text("{not-json", encoding="utf-8")
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            q = mod.fetch_quota(env, now=1, urlopen=no)
            self.assertEqual(calls, [])
            self.assertTrue(
                q["on_demand"]["kind"] == "unavailable" or q.get("total_pct") is None
            )

    def test_auth_missing_token_skips_network(self):
        mod = load_poc()
        calls = []

        def no(req, timeout=None):
            calls.append(1)
            raise AssertionError("no network without token")

        with tempfile.TemporaryDirectory() as td:
            auth = Path(td) / "cursor" / "auth.json"
            auth.parent.mkdir(parents=True)
            auth.write_text('{"refreshToken":"x"}', encoding="utf-8")
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            q = mod.fetch_quota(env, now=1, urlopen=no)
            self.assertEqual(calls, [])
            self.assertTrue(
                q["on_demand"]["kind"] == "unavailable" or q.get("total_pct") is None
            )

    def test_auth_fallthrough_when_xdg_missing_file(self):
        mod = load_poc()
        with tempfile.TemporaryDirectory() as td:
            xdg = Path(td) / "xdg"
            home = Path(td) / "home"
            xdg.mkdir()
            home.mkdir()
            auth = home / ".config" / "cursor" / "auth.json"
            auth.parent.mkdir(parents=True)
            auth.write_text('{"accessToken":"t"}', encoding="utf-8")
            env = {"HOME": str(home), "XDG_CONFIG_HOME": str(xdg)}
            self.assertEqual(mod.resolve_auth_path(env), auth)

    def test_fetch_timeout_writes_negative_cache_and_stops(self):
        mod = load_poc()
        n = {"calls": 0}

        def boom(req, timeout=None):
            n["calls"] += 1
            raise TimeoutError("slow")

        with tempfile.TemporaryDirectory() as td:
            auth = Path(td) / "cursor" / "auth.json"
            auth.parent.mkdir(parents=True)
            auth.write_text('{"accessToken":"t"}', encoding="utf-8")
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            mod.write_quota_cache(
                env,
                {
                    "total_pct": 11,
                    "fetched_at": 800,
                    "stale": False,
                    "on_demand": {"kind": "disabled"},
                    "cycle_start_ms": 0,
                    "cycle_end_ms": 1,
                },
            )
            q = mod.fetch_quota(env, urlopen=boom, now=1000)
            self.assertEqual(n["calls"], 1)
            self.assertTrue(mod.quota_cache_path(env).is_file())
            self.assertTrue(q.get("error"))
            self.assertTrue(q.get("stale"))
            self.assertEqual(q["total_pct"], 11)
            n["calls"] = 0
            q2 = mod.fetch_quota(env, urlopen=boom, now=1100)
            self.assertEqual(n["calls"], 0)
            self.assertTrue(q2.get("stale"))
            self.assertEqual(q2["total_pct"], 11)

    def test_fresh_cache_skips_network(self):
        mod = load_poc()
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CACHE_HOME": td, "XDG_CONFIG_HOME": td}
            mod.write_quota_cache(
                env,
                {
                    "total_pct": 7,
                    "fetched_at": 1000,
                    "stale": False,
                    "on_demand": {"kind": "disabled"},
                    "cycle_start_ms": 0,
                    "cycle_end_ms": 1,
                },
            )
            calls = []

            def no(req, timeout=None):
                calls.append(1)
                raise AssertionError("network should not run")

            q = mod.fetch_quota(env, now=1000 + 30, urlopen=no)
            self.assertEqual(q["total_pct"], 7)
            self.assertEqual(calls, [])

    def test_error_only_negative_cache_hides(self):
        mod = load_poc()
        calls = []

        def no(req, timeout=None):
            calls.append(1)
            raise AssertionError("no network inside negative TTL")

        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CACHE_HOME": td, "XDG_CONFIG_HOME": td}
            mod.write_quota_cache(
                env,
                {"error": "timeout", "fetched_at": 1000, "stale": True},
            )
            q = mod.fetch_quota(env, now=1100, urlopen=no)
            self.assertEqual(calls, [])
            self.assertIsNone(q.get("total_pct"))
            self.assertEqual(q["on_demand"]["kind"], "unavailable")


class TestQuotaSegments(unittest.TestCase):
    def test_on_demand_fixed_shows_ceiling(self):
        mod = load_poc()
        ctx = mod.context_from_quota(
            {
                "on_demand": {
                    "kind": "fixed",
                    "used_dollars": 1.5,
                    "ceiling_dollars": 20.0,
                },
                "total_pct": 100,
                "stale": False,
                "cycle_start_ms": 0,
                "cycle_end_ms": 10,
            },
            now_ms=5,
        )
        s = mod.seg_on_demand(ctx, 80, mod.default_theme())
        self.assertIsNotNone(s)
        self.assertIn("1.5", s)
        self.assertIn("20", s)
        self.assertIn("≈", s)

    def test_on_demand_disabled_unlimited_unavailable(self):
        mod = load_poc()
        theme = mod.default_theme()
        d = mod.context_from_quota(
            {
                "on_demand": {"kind": "disabled"},
                "total_pct": 10,
                "stale": False,
                "cycle_start_ms": 0,
                "cycle_end_ms": 10,
            },
            now_ms=5,
        )
        self.assertIn("off", mod.seg_on_demand(d, 80, theme).lower())
        u = mod.context_from_quota(
            {
                "on_demand": {"kind": "unlimited", "used_dollars": 3.0},
                "total_pct": 10,
                "stale": False,
                "cycle_start_ms": 0,
                "cycle_end_ms": 10,
            },
            now_ms=5,
        )
        su = mod.seg_on_demand(u, 80, theme)
        self.assertIn("3", su)
        self.assertRegex(su.lower(), r"no cap|unlimited")
        x = mod.context_from_quota(
            {
                "on_demand": {"kind": "unavailable"},
                "total_pct": None,
                "stale": False,
                "cycle_start_ms": 0,
                "cycle_end_ms": 10,
            },
            now_ms=5,
        )
        self.assertIsNone(mod.seg_on_demand(x, 80, theme))

    def test_included_templates(self):
        mod = load_poc()
        theme = mod.default_theme()
        ctx = mod.context_from_quota(
            {
                "total_pct": 42,
                "auto_pct": 10,
                "api_pct": 32,
                "stale": False,
                "on_demand": {"kind": "disabled"},
                "cycle_start_ms": 0,
                "cycle_end_ms": 100,
            },
            now_ms=50,
        )
        self.assertIn("inc 42%", mod.seg_included_total(ctx, 80, theme))
        self.assertIn("auto 10%", mod.seg_included_auto(ctx, 80, theme))
        self.assertIn("api 32%", mod.seg_included_api(ctx, 80, theme))

    def test_auto_hidden_when_absent(self):
        mod = load_poc()
        ctx = mod.context_from_quota(
            {
                "total_pct": 10,
                "auto_pct": None,
                "on_demand": {"kind": "disabled"},
                "stale": False,
                "cycle_start_ms": 0,
                "cycle_end_ms": 10,
            },
            now_ms=5,
        )
        self.assertIsNone(mod.seg_included_auto(ctx, 80, mod.default_theme()))

    def test_stale_marker_and_reset_days(self):
        mod = load_poc()
        ctx = mod.context_from_quota(
            {
                "total_pct": 10,
                "on_demand": {"kind": "disabled"},
                "stale": True,
                "cycle_start_ms": 0,
                "cycle_end_ms": 86_400_000,
            },
            now_ms=0,
        )
        t = mod.seg_included_total(ctx, 80, mod.default_theme())
        self.assertIn("stale", t.lower())
        r = mod.seg_reset(ctx, 80, mod.default_theme())
        self.assertIsNotNone(r)
        self.assertIn("↺", r)
        self.assertIn("1d", r)

    def test_pace_gap_formula(self):
        mod = load_poc()
        self.assertEqual(
            mod.billing_pace_gap(80.0, start_ms=0, end_ms=100, now_ms=50), 30.0
        )

    def test_gap_color_bands(self):
        mod = load_poc()
        theme = mod.default_theme()
        self.assertEqual(mod.util_gap_color(5.0, theme), theme.c("GREEN"))
        self.assertEqual(mod.util_gap_color(10.0, theme), theme.c("YELLOW"))
        self.assertEqual(mod.util_gap_color(15.0, theme), theme.c("ORANGE"))
        self.assertEqual(mod.util_gap_color(16.0, theme), theme.c("RED"))

    def test_on_demand_highlight_when_included_exhausted(self):
        mod = load_poc()
        ctx = mod.context_from_quota(
            {
                "total_pct": 100,
                "on_demand": {
                    "kind": "fixed",
                    "used_dollars": 0.5,
                    "ceiling_dollars": 20,
                },
                "stale": False,
                "cycle_start_ms": 0,
                "cycle_end_ms": 10,
            },
            now_ms=5,
        )
        s = mod.seg_on_demand(ctx, 80, mod.default_theme())
        self.assertTrue(ctx.on_demand_hot)
        self.assertIn("\x1b[1;31m", s)

    def test_render_includes_quota_from_fetch(self):
        mod = load_poc()
        payload = {
            "model": {"display_name": "M"},
            "workspace": {"current_dir": "/tmp/x"},
            "context_window": {"used_percentage": 10, "context_window_size": 1000},
        }
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}
            mod.write_quota_cache(
                env,
                {
                    "total_pct": 42,
                    "auto_pct": None,
                    "api_pct": None,
                    "on_demand": {"kind": "disabled"},
                    "stale": False,
                    "fetched_at": 1,
                    "cycle_start_ms": 0,
                    "cycle_end_ms": 10_000,
                },
            )
            out = mod.render_for_test(payload, env, now=50)
        self.assertIn("M", out)
        self.assertIn("inc 42%", out)
        self.assertIn("≈", out)

    def test_render_hides_quota_when_fetch_raises(self):
        mod = load_poc()
        payload = {
            "model": {"display_name": "M"},
            "workspace": {"current_dir": "/tmp/x"},
            "context_window": {"used_percentage": 10, "context_window_size": 1000},
        }
        with tempfile.TemporaryDirectory() as td:
            env = {"HOME": td, "XDG_CONFIG_HOME": td, "XDG_CACHE_HOME": td}

            def boom(*a, **k):
                raise RuntimeError("quota down")

            mod.fetch_quota = boom
            out = mod.render_for_test(payload, env, now=50)
        self.assertIn("M", out)
        self.assertNotIn("inc ", out)
        self.assertNotIn("≈", out)


if __name__ == "__main__":
    unittest.main()
