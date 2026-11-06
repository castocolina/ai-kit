"""Synthetic-fixture tests for Cursor quota normalization and state."""

import contextlib
import io
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from typing import Any, cast
from unittest import mock

from tests.cursor_fakes import FakeDashboard, load_dashboard_fixture, run_like_cursor
from tools.cursor_quota import (
    FRESH_TTL_S,
    NEGATIVE_TTL_S,
    PERIOD_ENUM,
    WEEK_MS,
    ExtraAlert,
    FetchContext,
    QuotaResult,
    core_extra_alert,
    core_needs_refresh,
    core_normalize,
    core_quota_state,
    core_synthetic_cache,
    probe_access_token,
    probe_auth_path,
    probe_build_opener,
    probe_cache_paths,
    probe_dashboard_call,
    probe_fetch_all,
    probe_fetch_quota,
    probe_read_cache,
    probe_read_quota,
    probe_refresh,
    probe_release_lock,
    probe_spawn_refresher,
    probe_try_lock,
    probe_validate_endpoint,
    probe_write_cache,
    util_number,
)


class TestCursorQuota(unittest.TestCase):
    def _auth_env(self, directory: str) -> tuple[dict[str, str], str]:
        home = pathlib.Path(directory) / "home"
        config = pathlib.Path(directory) / "config"
        auth = config / "cursor" / "auth.json"
        auth.parent.mkdir(parents=True)
        token = "synthetic-" + "cursor-" + "token"
        auth.write_text(json.dumps({"accessToken": token}), encoding="utf-8")
        return {"HOME": str(home), "XDG_CONFIG_HOME": str(config)}, token

    def test_relative_or_empty_cache_base_fails_closed_without_spawn_or_files(self):
        with tempfile.TemporaryDirectory() as directory:
            cwd = pathlib.Path(directory)
            previous = pathlib.Path.cwd()
            os.chdir(cwd)
            try:
                for base in ("", "relative-cache"):
                    with self.subTest(base=base):
                        spawned = []

                        def record_spawn(path, env, seen=spawned):
                            seen.append((path, env))
                            return True

                        result = probe_read_quota(base, {}, 1000, record_spawn)
                        self.assertEqual(result.state, "absent")
                        self.assertEqual(
                            probe_refresh(
                                base, {}, lambda: 1000, lambda _env: self.fail("must not fetch")
                            ),
                            1,
                        )
                        self.assertEqual(spawned, [])
                        self.assertEqual(list(cwd.iterdir()), [])
            finally:
                os.chdir(previous)

    def test_cache_write_refresh_and_cache_only_read(self):
        with tempfile.TemporaryDirectory() as directory:
            cache_base = str(pathlib.Path(directory) / "cache")
            cache_path, lock_path = probe_cache_paths(cache_base)
            self.assertEqual(
                stat.S_IMODE(os.stat(pathlib.Path(cache_base) / "cursor").st_mode), 0o700
            )
            token = "synthetic-cursor-token"
            data = core_synthetic_cache(1000)["data"]

            def fetch(_env):
                return cast(dict[str, object], data), None, token

            self.assertEqual(probe_refresh(cache_base, {}, lambda: 1000, fetch), 0)
            cache = cast(dict[str, object], probe_read_cache(cache_path))
            self.assertEqual(cache["data"], data)
            self.assertEqual(stat.S_IMODE(os.stat(cache_path).st_mode), 0o600)
            self.assertTrue(os.path.exists(lock_path))
            self.assertFalse(token.encode() in pathlib.Path(cache_path).read_bytes())
            spawned = []
            result = probe_read_quota(
                cache_base, {}, 1001, lambda base, env: spawned.append((base, env)) or True
            )
            self.assertEqual(result.state, "ok")
            self.assertEqual(spawned, [])

    def test_cache_atomic_failure_preserves_previous_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _lock = probe_cache_paths(directory)
            self.assertTrue(probe_write_cache(path, {"data": None}))
            prior = pathlib.Path(path).read_bytes()
            with mock.patch("tools.cursor_quota.os.replace", side_effect=OSError("blocked")):
                self.assertFalse(probe_write_cache(path, {"data": {"changed": True}}))
            self.assertEqual(pathlib.Path(path).read_bytes(), prior)
            self.assertEqual(list(pathlib.Path(path).parent.glob(".usage-*")), [])

    def test_symlink_cache_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            target = root / "target"
            target.mkdir()
            (root / "cursor").symlink_to(target, target_is_directory=True)
            self.assertFalse(probe_write_cache(str(root / "cursor" / "usage.json"), {"x": 1}))
            self.assertEqual(list(target.iterdir()), [])

    def test_cli_records_auth_missing_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory) / "home"
            config = pathlib.Path(directory) / "config"
            env = {
                "PATH": os.environ["PATH"],
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(config),
                "XDG_CACHE_HOME": str(pathlib.Path(directory) / "cache"),
            }
            proc = subprocess.run(
                [
                    sys.executable,
                    "-S",
                    str(pathlib.Path(__file__).parents[1] / "tools" / "cursor_quota.py"),
                    "--refresh",
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            cache_path = pathlib.Path(env["XDG_CACHE_HOME"]) / "ai-kit" / "cursor" / "usage.json"
            self.assertTrue(cache_path.exists())
            self.assertFalse((pathlib.Path.cwd() / "cursor").exists())
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
            self.assertEqual(cache["last_error_kind"], "auth_missing")
            self.assertIsNone(cache["data"])
            self.assertEqual(stat.S_IMODE(cache_path.stat().st_mode), 0o600)

    def test_negative_cache_retains_data_until_ttl(self):
        with tempfile.TemporaryDirectory() as directory:
            base = str(pathlib.Path(directory) / "cache")
            path, _lock = probe_cache_paths(base)
            previous = core_synthetic_cache(0)
            self.assertTrue(probe_write_cache(path, previous))
            calls = []

            def failed(_env):
                calls.append(1)
                return None, "network_error", "synthetic failure"

            self.assertEqual(probe_refresh(base, {}, lambda: 1200, failed), 0)
            saved = cast(dict[str, object], probe_read_cache(path))
            self.assertEqual(saved["data"], previous["data"])
            self.assertEqual(core_quota_state(saved, 1201).state, "stale")
            self.assertFalse(core_needs_refresh(saved, 1201))
            self.assertTrue(core_needs_refresh(saved, 1801))
            self.assertEqual(len(calls), 1)

    def test_flock_contention_and_sigkill_release(self):
        with tempfile.TemporaryDirectory() as directory:
            _path, lock_path = probe_cache_paths(directory)
            script = (
                "import fcntl, os, sys, time; fd=os.open(sys.argv[1], os.O_CREAT|os.O_RDWR, "
                "0o600); fcntl.flock(fd, fcntl.LOCK_EX); print('held', flush=True); "
                "time.sleep(30)"
            )
            holder = subprocess.Popen(
                [sys.executable, "-c", script, lock_path], stdout=subprocess.PIPE, text=True
            )
            try:
                assert holder.stdout is not None
                self.assertEqual(holder.stdout.readline().strip(), "held")
                self.assertIsNone(probe_try_lock(lock_path))
                holder.kill()  # SIGKILL releases the kernel advisory lock.
                holder.wait(timeout=5)
                descriptor = probe_try_lock(lock_path)
                self.assertIsNotNone(descriptor)
                probe_release_lock(cast(int, descriptor))
            finally:
                if holder.poll() is None:
                    holder.kill()
                    holder.wait(timeout=5)

    def test_competing_refreshers_only_one_fetches(self):
        with tempfile.TemporaryDirectory() as directory:
            base = str(pathlib.Path(directory) / "cache")
            _path, lock_path = probe_cache_paths(base)
            held = probe_try_lock(lock_path)
            self.assertIsNotNone(held)
            fetched = []
            try:

                def not_fetched(_env):
                    fetched.append(1)
                    return None, "network_error", "unexpected fetch"

                self.assertEqual(probe_refresh(base, {}, lambda: 5000, not_fetched), 0)
                self.assertEqual(fetched, [])
            finally:
                probe_release_lock(cast(int, held))
            data = core_synthetic_cache(5000)["data"]
            self.assertEqual(
                probe_refresh(
                    base, {}, lambda: 5000, lambda _env: (cast(dict[str, object], data), None, "")
                ),
                0,
            )
            saved = probe_read_cache(_path)
            assert saved is not None
            self.assertEqual(saved["data"], data)

    def test_production_read_spawns_detached_refresher(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            cache_base = root / "xdg-cache" / "ai-kit"
            home = root / "home"
            config = root / "config"
            pid_file = root / "child.pid"
            script = root / "render.py"
            tools = pathlib.Path(__file__).resolve().parents[1] / "tools"
            script.write_text(
                "import os, subprocess, sys\n"
                f"sys.path.insert(0, {str(tools)!r})\n"
                "from cursor_quota import probe_read_quota\n"
                f"base={str(cache_base)!r}; pidfile={str(pid_file)!r}\n"
                "def spawn(base, env):\n"
                "    proc = subprocess.Popen([sys.executable, '-S', "
                "os.path.join(sys.path[0], 'cursor_quota.py'), '--refresh'], "
                "env=env, stdin=subprocess.DEVNULL, "
                "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, "
                "close_fds=True, start_new_session=True)\n"
                "    open(pidfile, 'w').write(str(proc.pid))\n"
                "    return True\n"
                "probe_read_quota(base, os.environ.copy(), 1000, spawn)\n"
                "import time; time.sleep(2)\n",
                encoding="utf-8",
            )
            env = {
                "PATH": os.environ["PATH"],
                "PYTHONPATH": str(tools),
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(config),
                "XDG_CACHE_HOME": str(root / "xdg-cache"),
            }
            result = run_like_cursor(
                [sys.executable, str(script)],
                {},
                cwd=str(root),
                env=env,
                kill_after_ms=500,
                timeout_s=2,
            )
            self.assertTrue(result.killed, result)
            self.assertFalse(result.blocked)
            child_pid = int(pid_file.read_text(encoding="utf-8"))
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                cache_path = cache_base / "cursor" / "usage.json"
                if cache_path.exists():
                    break
                time.sleep(0.02)
            else:
                self.fail("detached refresher did not publish auth_missing cache")
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
            self.assertEqual(cache["last_error_kind"], "auth_missing")
            self.assertIsNone(cache["data"])
            self.assertTrue((cache_path.parent / "usage.lock").exists())
            self.assertEqual(
                probe_read_quota(str(cache_base), env, time.time()).state, "auth_missing"
            )
            self.assertNotIn("token", cache_path.read_text(encoding="utf-8"))
            self.assertGreater(child_pid, 0)

    def test_killed_refresher_releases_lock_and_replacement_publishes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory) / "cache"
            cache_path, lock_path = probe_cache_paths(str(base))
            worker = pathlib.Path(directory) / "holder.py"
            worker.write_text(
                "import fcntl, os, sys, time\n"
                f"fd=os.open({str(lock_path)!r}, os.O_CREAT|os.O_RDWR, 0o600)\n"
                "fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)\n"
                f"open({str(pathlib.Path(directory) / 'locked')!r}, 'w').close()\n"
                "time.sleep(30)\n",
                encoding="utf-8",
            )
            holder = subprocess.Popen(
                [sys.executable, "-S", str(worker)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                marker = pathlib.Path(directory) / "locked"
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline and not marker.exists():
                    time.sleep(0.02)
                self.assertTrue(marker.exists(), "worker did not acquire its flock")
                descriptor = probe_try_lock(lock_path)
                self.assertIsNone(descriptor, "worker flock was not exclusive")
                holder.kill()  # SIGKILL releases the real refresher's child-owned flock.
                holder.wait(timeout=5)
                acquired = probe_try_lock(lock_path)
                self.assertIsNotNone(acquired)
                probe_release_lock(cast(int, acquired))
                replacement_data = cast(dict[str, object], core_synthetic_cache(7000)["data"])
                calls = []

                def replacement(_env):
                    calls.append(1)
                    return replacement_data, None, ""

                self.assertEqual(probe_refresh(str(base), {}, lambda: 7000, replacement), 0)
                self.assertEqual(calls, [1])
                saved = probe_read_cache(str(cache_path))
                assert saved is not None
                self.assertEqual(saved["data"], replacement_data)
            finally:
                if holder.poll() is None:
                    holder.kill()
                    holder.wait(timeout=5)

    def test_synchronized_reader_rechecks_cache_after_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            base = str(pathlib.Path(directory) / "cache")
            cache_path, lock_path = probe_cache_paths(base)
            stale = core_synthetic_cache(0)
            self.assertTrue(probe_write_cache(cache_path, stale))
            lock = probe_try_lock(lock_path)
            self.assertIsNotNone(lock)
            entered = threading.Event()
            release = threading.Event()
            results = []

            def reader():
                observed = probe_read_cache(cache_path)
                entered.set()
                release.wait(timeout=5)
                results.append(observed)

            thread = threading.Thread(target=reader)
            thread.start()
            self.assertTrue(entered.wait(timeout=5))
            fresh = core_synthetic_cache(500)
            self.assertTrue(probe_write_cache(cache_path, fresh))
            release.set()
            thread.join(timeout=5)
            probe_release_lock(cast(int, lock))
            self.assertFalse(thread.is_alive())
            self.assertEqual(probe_read_cache(cache_path), fresh)
            self.assertEqual(results, [stale])
            fetched = []

            def not_fetched(_env):
                fetched.append(1)
                return None, "network_error", "unexpected fetch"

            self.assertEqual(probe_refresh(base, {}, lambda: 501, not_fetched), 0)
            self.assertEqual(fetched, [])

    def test_401_refresh_hides_older_quota(self):
        with tempfile.TemporaryDirectory() as directory:
            base = str(pathlib.Path(directory) / "cache")
            path, _lock = probe_cache_paths(base)
            good = core_synthetic_cache(0)
            self.assertTrue(probe_write_cache(path, good))
            ticks = iter((700, 701))
            self.assertEqual(
                probe_refresh(
                    base,
                    {},
                    lambda: next(ticks),
                    lambda _env: (None, "auth_expired", "unauthorized"),
                ),
                0,
            )
            cache = cast(dict[str, object], probe_read_cache(path))
            self.assertEqual(cache["last_error_kind"], "auth_expired")
            self.assertEqual(core_quota_state(cache, 702).state, "auth_expired")

    def test_auth_to_concurrent_transport_and_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            env, token = self._auth_env(directory)
            self.assertEqual(probe_access_token(env), (token, None))
            expected_parts = (
                load_dashboard_fixture("usage_pro"),
                load_dashboard_fixture("hard_limit_fixed"),
                load_dashboard_fixture("plan_info_monthly"),
            )
            expected = core_normalize(*expected_parts)
            with FakeDashboard() as dashboard:
                dashboard.script("GetCurrentPeriodUsage", body=expected_parts[0])
                dashboard.script("GetHardLimit", body=expected_parts[1])
                dashboard.script("GetPlanInfo", body=expected_parts[2])
                fetched = probe_fetch_all(dashboard.url, token, probe_build_opener(), 2.0)
                self.assertEqual(fetched, (*expected_parts, None))
                self.assertEqual(len(dashboard.requests), 3)
                self.assertTrue(
                    all(
                        request["method"] == "POST"
                        and request["authorization"] == "Bearer " + token
                        for request in dashboard.requests
                    )
                )
            env["CURSOR_API_ENDPOINT"] = "https://api2.cursor.sh"

            def fetch(base, fetched_token, opener, timeout_s):
                self.assertEqual(base, "https://api2.cursor.sh")
                self.assertEqual(fetched_token, token)
                return fetched

            normalized, error, _diagnostic = probe_fetch_quota(env, fetch=fetch)
            self.assertIsNone(error)
            self.assertEqual(normalized, expected)

    def test_optional_timeout_preserves_successful_usage(self):
        # An optional method exceeding the deadline degrades only its own data:
        # the successful required usage response is kept, not discarded with a
        # total network-failure classification.
        usage = load_dashboard_fixture("usage_pro")
        with FakeDashboard() as dashboard:
            dashboard.script("GetCurrentPeriodUsage", body=usage)
            dashboard.script("GetHardLimit", delay_s=2.0,
                             body=load_dashboard_fixture("hard_limit_fixed"))
            dashboard.script("GetPlanInfo", delay_s=2.0,
                             body=load_dashboard_fixture("plan_info_monthly"))
            started = time.monotonic()
            fetched = probe_fetch_all(dashboard.url, "synthetic", probe_build_opener(), 0.4)
            self.assertLessEqual(time.monotonic() - started, 2.0)
            self.assertIsNone(fetched.error_kind)
            self.assertEqual(fetched.usage, usage)
            self.assertIsNone(fetched.hard_limit)
            self.assertIsNone(fetched.plan_info)
        kept = core_normalize(fetched.usage, fetched.hard_limit, fetched.plan_info)
        self.assertEqual(kept["included_pct"],
                         core_normalize(usage, None, None)["included_pct"])
        # The required usage method staying unfinished still fails the fetch.
        with FakeDashboard() as dashboard:
            dashboard.script("GetCurrentPeriodUsage", delay_s=2.0, body=usage)
            dashboard.script("GetHardLimit", body=load_dashboard_fixture("hard_limit_fixed"))
            dashboard.script("GetPlanInfo", body=load_dashboard_fixture("plan_info_monthly"))
            fetched = probe_fetch_all(dashboard.url, "synthetic", probe_build_opener(), 0.4)
            self.assertEqual(fetched.error_kind, "network_error")
            self.assertIsNone(fetched.usage)

    def test_trickling_body_is_bounded_and_leaves_no_transport_threads(self):
        # A server sending one byte just before each read timeout keeps a
        # read(65536)-style call alive past the deadline; the production
        # refresher must still exit within the bound, with no transport worker
        # left for interpreter shutdown to join (which would hold the lock).
        scripts = (
            ("GetCurrentPeriodUsage", load_dashboard_fixture("usage_pro")),
            ("GetHardLimit", load_dashboard_fixture("hard_limit_fixed")),
            ("GetPlanInfo", load_dashboard_fixture("plan_info_monthly")),
        )
        with FakeDashboard() as dashboard:
            for method, body in scripts:
                dashboard.script(method, trickle_s=0.02, body=body)
            baseline = {thread.name for thread in threading.enumerate()}
            started = time.monotonic()
            fetched = probe_fetch_all(dashboard.url, "synthetic", probe_build_opener(), 0.5)
            elapsed = time.monotonic() - started
            self.assertEqual(fetched.error_kind, "network_error")
            self.assertLessEqual(elapsed, 0.5 + 1.0)
            leftovers = [thread.name for thread in threading.enumerate()
                         if thread.name not in baseline
                         and thread.name.startswith("ThreadPoolExecutor")]
            self.assertEqual(leftovers, [])

    def test_trickling_body_subprocess_refresher_exits_within_the_bound(self):
        # The real refresher code path (probe_fetch_all, exactly what
        # probe_refresh invokes) in its own process: it must exit well within
        # the deadline bound instead of lingering to interpreter shutdown.
        driver = (
            "import sys, time; sys.path.insert(0, sys.argv[1]);"
            "from cursor_quota import probe_fetch_all, probe_build_opener;"
            "started = time.monotonic();"
            "result = probe_fetch_all(sys.argv[2], 'synthetic',"
            " probe_build_opener(), 0.5);"
            "assert result.error_kind == 'network_error', result;"
            "assert time.monotonic() - started < 5, 'refresher outlived its deadline';"
        )
        tools_dir = str(pathlib.Path(__file__).parents[1] / "tools")
        with FakeDashboard() as dashboard:
            for method, body in (
                ("GetCurrentPeriodUsage", load_dashboard_fixture("usage_pro")),
                ("GetHardLimit", load_dashboard_fixture("hard_limit_fixed")),
                ("GetPlanInfo", load_dashboard_fixture("plan_info_monthly")),
            ):
                dashboard.script(method, trickle_s=0.02, body=body)
            proc = subprocess.run(
                [sys.executable, "-S", "-c", driver, tools_dir, dashboard.url],
                capture_output=True, text=True, timeout=20, check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_trickling_headers_subprocess_refresher_exits_within_the_bound(self):
        # T-23-30: with headers trickling one byte every 0.5 s, every blocking
        # recv succeeds and the per-socket timeout cannot end open(); the
        # absolute-deadline watchdog must close the transport so the real
        # refresher flow exits within the deadline plus a small margin.
        driver = (
            "import sys, time; sys.path.insert(0, sys.argv[1]);"
            "from cursor_quota import probe_fetch_all, probe_build_opener;"
            "started = time.monotonic();"
            "result = probe_fetch_all(sys.argv[2], 'synthetic',"
            " probe_build_opener(), 1.0);"
            "assert result.error_kind == 'network_error', result;"
            "elapsed = time.monotonic() - started;"
            "assert elapsed < 3.0, f'refresher outlived its deadline: {elapsed}';"
        )
        tools_dir = str(pathlib.Path(__file__).parents[1] / "tools")
        with FakeDashboard() as dashboard:
            for method in ("GetCurrentPeriodUsage", "GetHardLimit", "GetPlanInfo"):
                dashboard.script(method, header_trickle_s=0.5, body={})
            proc = subprocess.run(
                [sys.executable, "-S", "-c", driver, tools_dir, dashboard.url],
                capture_output=True, text=True, timeout=20, check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_trickling_headers_in_process_call_respects_absolute_deadline(self):
        # Same stall, in-process: all three calls finish (as network_error)
        # by the deadline plus a small margin instead of hanging open().
        with FakeDashboard() as dashboard:
            for method in ("GetCurrentPeriodUsage", "GetHardLimit", "GetPlanInfo"):
                dashboard.script(method, header_trickle_s=0.5, body={})
            started = time.monotonic()
            fetched = probe_fetch_all(dashboard.url, "synthetic", probe_build_opener(), 1.0)
            elapsed = time.monotonic() - started
            self.assertEqual(fetched.error_kind, "network_error")
            self.assertLess(elapsed, 1.0 + 2.0,
                            f"header trickle kept the call alive {elapsed:.2f}s")

    def test_dummy_token_never_appears_in_outputs_or_stderr(self):
        with tempfile.TemporaryDirectory() as directory:
            env, token = self._auth_env(directory)
            env["CURSOR_API_ENDPOINT"] = "http://api2.cursor.sh"
            with mock.patch(
                "tools.cursor_quota.probe_access_token", return_value=(token, None)
            ) as reader:
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    data, error, diagnostic = probe_fetch_quota(env)
            reader.assert_not_called()
            combined = repr((data, error, diagnostic, stderr.getvalue()))
            self.assertNotIn(token, combined)
            state = core_quota_state({"last_error_kind": "auth_missing"}, 10)
            self.assertEqual(state.state, "auth_missing")

    def test_endpoint_validation_and_rejection_precedes_auth(self):
        accepted = ("https://api2.cursor.sh", "https://cursor.sh", "https://API2.Cursor.sh/")
        rejected = (
            "http://api2.cursor.sh",
            "https://cursor.sh.evil.com",
            "https://xcursor.sh",
            "https://user:pw@api2.cursor.sh",
            "https://api2.cursor.sh:8443",
            "https://api2.cursor.sh/path",
            "ftp://api2.cursor.sh",
            "",
        )
        for endpoint in accepted:
            with self.subTest(endpoint=endpoint):
                self.assertIsNotNone(probe_validate_endpoint(endpoint))
        for endpoint in rejected:
            with self.subTest(endpoint=endpoint):
                self.assertIsNone(probe_validate_endpoint(endpoint))
        with mock.patch("tools.cursor_quota.probe_access_token") as reader:
            data, error, _ = probe_fetch_quota({"CURSOR_API_ENDPOINT": "http://api2.cursor.sh"})
        self.assertIsNone(data)
        self.assertEqual(error, "network_error")
        reader.assert_not_called()

    def test_auth_paths_and_token_error_kinds(self):
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory) / "home"
            xdg = pathlib.Path(directory) / "xdg"
            env = {
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(xdg),
                "CURSOR_CONFIG_DIR": str(pathlib.Path(directory) / "other"),
            }
            self.assertEqual(probe_auth_path(env, "linux"), str(xdg / "cursor" / "auth.json"))
            self.assertEqual(
                probe_auth_path({"HOME": str(home)}, "linux"),
                str(home / ".config" / "cursor" / "auth.json"),
            )
            self.assertEqual(probe_auth_path(env, "darwin"), str(home / ".cursor" / "auth.json"))
            self.assertEqual(probe_access_token(env), (None, "auth_missing"))
            auth = xdg / "cursor" / "auth.json"
            auth.parent.mkdir(parents=True)
            for content in ("{}", '{"apiKey":"ignored"}', "", "{"):
                auth.write_text(content, encoding="utf-8")
                expected = "network_error" if content in ("", "{") else "auth_unsupported"
                self.assertEqual(probe_access_token(env), (None, expected))
            auth.write_text('{"accessToken": 42}', encoding="utf-8")
            self.assertEqual(probe_access_token(env), (None, "auth_unsupported"))

    def test_redirect_refused_before_second_server_receives_request(self):
        with FakeDashboard() as destination:
            destination.script("GetCurrentPeriodUsage", body={})
            with FakeDashboard() as source:
                source.script(
                    "GetCurrentPeriodUsage",
                    status=302,
                    body={},
                    location=destination.url + "/redirected",
                )
                result = probe_dashboard_call(
                    FetchContext(
                        source.url, "synthetic", probe_build_opener(), time.monotonic() + 2, 2
                    ),
                    "GetCurrentPeriodUsage",
                )
                self.assertEqual(result[1], "network_error")
                self.assertEqual(len(source.requests), 1)
                self.assertEqual(destination.requests, [])

    def test_required_call_failures_and_optional_call_degradation(self):
        responses = (
            load_dashboard_fixture("usage_pro"),
            load_dashboard_fixture("hard_limit_fixed"),
            load_dashboard_fixture("plan_info_monthly"),
        )
        for status, expected in (
            (401, "auth_expired"),
            (403, "auth_expired"),
            (500, "network_error"),
        ):
            with self.subTest(status=status), FakeDashboard() as dashboard:
                dashboard.script("GetCurrentPeriodUsage", status=status)
                result = self._fetch_scripted(dashboard, responses)
                self.assertEqual(result.error_kind, expected)
        without_individual = load_dashboard_fixture("usage_team")
        with FakeDashboard() as dashboard:
            dashboard.script("GetCurrentPeriodUsage", body=without_individual)
            dashboard.script("GetHardLimit", status=500)
            dashboard.script("GetPlanInfo", body=responses[2])
            result = probe_fetch_all(dashboard.url, "synthetic", probe_build_opener(), 2)
            self.assertIsNone(result.error_kind)
            normalized = core_normalize(result.usage, result.hard_limit, result.plan_info)
            self.assertEqual(normalized["od_kind"], "unavailable")
        with FakeDashboard() as dashboard:
            dashboard.script("GetCurrentPeriodUsage", body=responses[0])
            dashboard.script("GetHardLimit", body=responses[1])
            dashboard.script("GetPlanInfo", status=500)
            result = probe_fetch_all(dashboard.url, "synthetic", probe_build_opener(), 2)
            normalized = core_normalize(result.usage, result.hard_limit, result.plan_info)
            self.assertEqual(
                core_quota_state({"data": normalized, "data_fetched_at": 1}, 2).included_window,
                (1791590400000, 1794268800000),
            )

    @staticmethod
    def _fetch_scripted(dashboard, responses):
        for method, response in zip(("GetHardLimit", "GetPlanInfo"), responses[1:], strict=True):
            dashboard.script(method, body=response)
        return probe_fetch_all(dashboard.url, "synthetic", probe_build_opener(), 2)

    def test_malformed_json_and_total_deadline(self):
        with FakeDashboard() as dashboard:
            dashboard.script("GetCurrentPeriodUsage", body="not an object")
            result = probe_fetch_all(dashboard.url, "synthetic", probe_build_opener(), 2)
            self.assertEqual(result.error_kind, "network_error")
        with FakeDashboard() as dashboard:
            for method in ("GetCurrentPeriodUsage", "GetHardLimit", "GetPlanInfo"):
                dashboard.script(method, body={"slow": True}, delay_s=0.4)
            started = time.monotonic()
            result = probe_fetch_all(dashboard.url, "synthetic", probe_build_opener(), 0.1)
            elapsed = time.monotonic() - started
            self.assertEqual(result.error_kind, "network_error")
            self.assertLess(elapsed, 0.3)

    def test_fixture_happy_path_normalizes_and_states(self):
        data = core_normalize(
            load_dashboard_fixture("usage_pro"),
            load_dashboard_fixture("hard_limit_fixed"),
            load_dashboard_fixture("plan_info_monthly"),
        )
        self.assertEqual(data["cycle_start_ms"], 1791590400000)
        self.assertEqual(data["cycle_end_ms"], 1794268800000)
        self.assertEqual(data["included_pct"], 50)
        self.assertEqual(data["api_pct"], 100)
        self.assertEqual(data["od_kind"], "fixed")
        self.assertEqual(data["od_used_usd"], 5.2)
        self.assertEqual(data["od_ceiling_usd"], 5.0)
        self.assertEqual(data["included_period"], "monthly")
        json.dumps(data)
        result = core_quota_state({"data": data, "data_fetched_at": 90}, 100)
        self.assertIsInstance(result, QuotaResult)
        self.assertEqual(result.state, "ok")
        self.assertEqual(result.confidence, "inferred")
        self.assertEqual(result.included_window, (1791590400000, 1794268800000))
        self.assertTrue(
            all(
                not isinstance(value, str)
                or value
                in {
                    "monthly",
                    "weekly",
                    "unspecified",
                    "fixed",
                    "unlimited",
                    "disabled",
                    "unavailable",
                }
                for value in data.values()
            )
        )

    def test_numeric_validation(self):
        for value in (True, "abc", float("nan"), float("inf"), -5, None, object()):
            with self.subTest(value=repr(value)):
                self.assertIsNone(util_number(value))

    def test_string_epoch_and_derive_else_hide(self):
        self.assertEqual(
            core_normalize(
                load_dashboard_fixture("usage_string_ms"),
                load_dashboard_fixture("hard_limit_fixed"),
                load_dashboard_fixture("plan_info_monthly"),
            ),
            core_normalize(
                load_dashboard_fixture("usage_pro"),
                load_dashboard_fixture("hard_limit_fixed"),
                load_dashboard_fixture("plan_info_monthly"),
            ),
        )
        usage = load_dashboard_fixture("usage_missing_percents")
        data = core_normalize(usage, None, None)
        self.assertEqual(data["included_pct"], 50)
        self.assertIsNone(data["api_pct"])
        usage["planUsage"]["limit"] = 0
        self.assertIsNone(core_normalize(usage, None, None)["included_pct"])
        usage["planUsage"].pop("includedSpend")
        self.assertIsNone(core_normalize(usage, None, None)["included_pct"])

    def test_invalid_dashboard_numbers_are_hidden(self):
        for invalid in (True, "abc", float("nan"), float("inf"), -5):
            with self.subTest(invalid=repr(invalid)):
                usage = load_dashboard_fixture("usage_pro")
                usage["planUsage"]["totalPercentUsed"] = invalid
                usage["planUsage"]["includedSpend"] = invalid
                usage["spendLimitUsage"]["individualUsed"] = invalid
                data = core_normalize(usage, None, None)
                self.assertIsNone(data["included_pct"])
                self.assertIsNone(data["od_used_usd"])

    def test_absent_proto_numeric_is_zero(self):
        usage = load_dashboard_fixture("usage_no_plan")
        self.assertEqual(core_normalize(usage, None, None)["od_used_usd"], 0)

    def test_hard_limit_classes_and_team_evidence(self):
        usage = load_dashboard_fixture("usage_team")
        team_without_evidence = core_normalize(usage, None, None)
        self.assertEqual(team_without_evidence["od_kind"], "unavailable")
        self.assertEqual(core_normalize(usage, {}, None)["od_kind"], "unavailable")
        for fixture, expected in (
            ("hard_limit_unlimited", "unlimited"),
            ("hard_limit_disabled", "disabled"),
        ):
            with self.subTest(fixture=fixture):
                result = core_normalize(usage, load_dashboard_fixture(fixture), None)
                self.assertEqual(result["od_kind"], expected)
        usage["spendLimitUsage"]["individualLimit"] = 1000
        individual = core_normalize(usage, None, None)
        self.assertEqual((individual["od_kind"], individual["od_ceiling_usd"]), ("fixed", 10))
        usage["spendLimitUsage"].pop("individualLimit")
        for pooled_limit, expected in ((2000, "fixed"), (0, "unavailable"), (None, "unavailable")):
            usage["spendLimitUsage"]["pooledLimit"] = pooled_limit
            with self.subTest(pooled_limit=pooled_limit):
                result = core_normalize(usage, load_dashboard_fixture("hard_limit_fixed"), None)
                self.assertEqual(result["od_kind"], expected)
                if expected == "fixed":
                    self.assertEqual(result["od_ceiling_usd"], 20)
                    self.assertEqual(result["od_used_usd"], 5.2)
        usage["spendLimitUsage"]["individualLimit"] = 0
        personal = load_dashboard_fixture("usage_pro")
        personal["spendLimitUsage"]["individualLimit"] = 0
        result = core_normalize(personal, load_dashboard_fixture("hard_limit_unlimited"), None)
        self.assertEqual(result["od_kind"], "disabled")

    def test_absent_individual_limit_uses_hard_limit_evidence(self):
        # Absence of individualLimit is not evidence of zero: only an EXPLICIT
        # zero is the disabled toggle; an absent limit falls through to the
        # hard-limit evidence (fixed / unlimited / unavailable).
        usage = load_dashboard_fixture("usage_pro")
        usage["spendLimitUsage"].pop("individualLimit")
        cases = (
            ("hard_limit_fixed", "fixed", 20.0),
            ("hard_limit_unlimited", "unlimited", None),
            (None, "unavailable", None),
        )
        for fixture, kind, ceiling in cases:
            with self.subTest(fixture=fixture):
                evidence = load_dashboard_fixture(fixture) if fixture else None
                data = core_normalize(usage, evidence, None)
                self.assertEqual(data["od_kind"], kind)
                self.assertEqual(data["od_ceiling_usd"], ceiling)
        usage["spendLimitUsage"]["individualLimit"] = 0
        for fixture in ("hard_limit_fixed", "hard_limit_unlimited", None):
            with self.subTest(explicit_zero=fixture):
                evidence = load_dashboard_fixture(fixture) if fixture else None
                self.assertEqual(core_normalize(usage, evidence, None)["od_kind"], "disabled")

    def test_windows_and_billing_cycle_fallback(self):
        usage = load_dashboard_fixture("usage_pro")
        weekly = core_normalize(usage, None, load_dashboard_fixture("plan_info_weekly"))
        reset = cast(int, weekly["included_resets_at_ms"])
        result = core_quota_state({"data": weekly, "data_fetched_at": 1}, 2)
        self.assertEqual(result.included_window, (reset - WEEK_MS, reset))
        monthly = core_normalize(usage, None, None)
        monthly_result = core_quota_state({"data": monthly, "data_fetched_at": 1}, 2)
        self.assertEqual(monthly_result.included_window, (1791590400000, 1794268800000))
        weekly_no_reset = load_dashboard_fixture("plan_info_weekly")
        weekly_no_reset["planInfo"].pop("includedUsageResetsAt")
        self.assertIsNone(
            core_quota_state(
                {"data": core_normalize(usage, None, weekly_no_reset), "data_fetched_at": 1}, 2
            ).included_window
        )
        fallback = load_dashboard_fixture("usage_pro")
        fallback.pop("billingCycleEnd")
        fallback_result = core_normalize(
            fallback, None, load_dashboard_fixture("plan_info_monthly")
        )
        self.assertEqual(fallback_result["cycle_end_ms"], 1794268800000)
        conflict = load_dashboard_fixture("usage_pro")
        conflict["billingCycleEnd"] = 123
        conflict_result = core_normalize(
            conflict, None, load_dashboard_fixture("plan_info_monthly")
        )
        self.assertEqual(conflict_result["cycle_end_ms"], 123)

    def test_normalized_strings_stay_inside_the_period_enum(self):
        # T-23-24: normalized data is numbers-and-enums only. The raw
        # server-controlled includedUsagePeriod string must be clamped to the
        # closed PERIOD_ENUM set — a hostile 5,000-character value collapses
        # to the "unknown" sentinel and never reaches the cache.
        def string_values(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for item in value.values():
                    yield from string_values(item)
            elif isinstance(value, list):
                for item in value:
                    yield from string_values(item)

        hostile = {"planInfo": {"includedUsagePeriod": "w" * 5000}}
        normalized = core_normalize(load_dashboard_fixture("usage_pro"), None, hostile)
        self.assertEqual(normalized["included_period"], "unknown")
        # The data's full closed string vocabulary: the period enum plus the
        # on-demand kind enum. Nothing else may appear, and nothing may be
        # longer than the longest member.
        allowed = PERIOD_ENUM | {"unavailable", "fixed", "disabled", "unlimited"}
        longest = max(len(word) for word in allowed)
        cache = core_synthetic_cache(10)
        cache["data"] = normalized
        for label, payload in (("normalized", normalized), ("cache", cache)):
            for word in string_values(json.loads(json.dumps(payload))):
                self.assertIn(word, allowed,
                              f"{label} carries a string outside the enum: {word!r}")
                self.assertLessEqual(len(word), longest,
                                     f"{label} carries an over-long string")
        # Recognition is case-insensitive; an absent period stays None.
        cased = {"planInfo": {"includedUsagePeriod": "WEEKLY"}}
        self.assertEqual(
            core_normalize(load_dashboard_fixture("usage_pro"), None, cased)["included_period"],
            "weekly",
        )
        self.assertIsNone(
            core_normalize(load_dashboard_fixture("usage_pro"), None, None)["included_period"]
        )

    def test_states_and_refresh_edges(self):
        data = core_normalize(load_dashboard_fixture("usage_pro"), None, None)
        for age, expected in ((FRESH_TTL_S, "ok"), (FRESH_TTL_S + 0.5, "stale")):
            with self.subTest(age=age):
                cache = {"data": data, "data_fetched_at": 100}
                self.assertEqual(core_quota_state(cache, 100 + age).state, expected)
        cycle_end = cast(float, data["cycle_end_ms"])
        self.assertEqual(
            core_quota_state({"data": data, "data_fetched_at": 100}, cycle_end / 1000).state,
            "cycle_ended",
        )
        auth = {
            "data": data,
            "data_fetched_at": 100,
            "last_attempt_at": 101,
            "last_error_kind": "auth_expired",
        }
        self.assertEqual(core_quota_state(auth, 102).state, "auth_expired")
        auth["last_error_kind"] = "auth_unsupported"
        self.assertEqual(core_quota_state(auth, 102).state, "auth_unsupported")
        network = {
            "data": data,
            "data_fetched_at": 100,
            "last_attempt_at": 101,
            "last_error_kind": "network_error",
        }
        self.assertEqual(core_quota_state(network, 102).state, "stale")
        no_data_error = {"last_error_kind": "network_error"}
        self.assertEqual(core_quota_state(no_data_error, 102).state, "network_error")
        self.assertEqual(core_quota_state({}, 102).state, "absent")
        self.assertTrue(core_needs_refresh({}, 102))
        self.assertFalse(core_needs_refresh({"data_fetched_at": 100}, 100))
        # The negative TTL is failure-only: a cache populated by a SUCCESSFUL
        # attempt is refreshable the moment its data is stale, while a failed
        # attempt is backed off for NEGATIVE_TTL_S (probe_refresh's full shape).
        data = core_normalize(load_dashboard_fixture("usage_pro"), None, None)

        def _cache(fetched: float, attempted: float, error: str | None) -> dict[str, object]:
            return {
                "data": data,
                "data_fetched_at": fetched,
                "last_attempt_at": attempted,
                "last_error": "synthetic failure" if error else None,
                "last_error_kind": error,
            }

        healthy = _cache(1000, 1000, None)
        self.assertFalse(core_needs_refresh(healthy, 1000 + FRESH_TTL_S))
        self.assertTrue(core_needs_refresh(healthy, 1000 + FRESH_TTL_S + 1))
        failed = _cache(1000, 1000, "network_error")
        self.assertFalse(core_needs_refresh(failed, 1300))
        self.assertTrue(core_needs_refresh(failed, 1000 + NEGATIVE_TTL_S + 1))
        synthetic = core_synthetic_cache(500)
        self.assertEqual(core_quota_state(synthetic, 500).state, "ok")



    def test_refresher_argv_is_module_refresh_only_and_env_passes_through(self):
        # T-23-34: the production spawn argv is exactly
        # [sys.executable, "-S", realpath(cursor_quota.py), "--refresh"],
        # running ai-kit's own module, and the env handed to the child is the
        # render's own environment unchanged.
        captured: dict[str, Any] = {}

        def fake_popen(argv, **kwargs):
            captured["argv"] = argv
            captured["kwargs"] = kwargs
            return mock.Mock()

        env = {"SYNTHETIC_VAR": "1", "PATH": os.environ["PATH"]}
        self.assertTrue(probe_spawn_refresher("/tmp/synthetic-cache", env, fake_popen))
        expected_module = os.path.realpath(
            str(pathlib.Path(__file__).parents[1] / "tools" / "cursor_quota.py")
        )
        self.assertEqual(
            captured["argv"],
            [sys.executable, "-S", expected_module, "--refresh"],
        )
        self.assertEqual(captured["kwargs"].get("env"), env)

    def test_real_fetch_flow_carries_token_only_in_authorization_header(self):
        # T-23-28: through the real fetch-and-normalize flow, the token
        # appears exactly once — in each request's Authorization header — and
        # never in the normalized data or the diagnostic.
        with tempfile.TemporaryDirectory() as directory:
            env, token = self._auth_env(directory)
            env["CURSOR_API_ENDPOINT"] = "https://api2.cursor.sh"
            parts = (
                load_dashboard_fixture("usage_pro"),
                load_dashboard_fixture("hard_limit_fixed"),
                load_dashboard_fixture("plan_info_monthly"),
            )
            def fetch(_base, fetched_token, opener, _timeout_s):
                return probe_fetch_all(dashboard.url, fetched_token, opener, 2.0)

            with FakeDashboard() as dashboard:
                for method, payload in zip(
                    ("GetCurrentPeriodUsage", "GetHardLimit", "GetPlanInfo"),
                    parts,
                    strict=True,
                ):
                    dashboard.script(method, body=payload)
                data, error, diagnostic = probe_fetch_quota(env, fetch=fetch)
            self.assertIsNone(error)
            self.assertEqual(diagnostic, "")
            self.assertEqual(len(dashboard.requests), 3)
            for request in dashboard.requests:
                self.assertEqual(request["authorization"], "Bearer " + token)
                self.assertNotIn(token, str(request["path"]))
            serialized = json.dumps(data, default=repr)
            self.assertNotIn(token, serialized)
            self.assertNotIn(token, diagnostic)

    def test_no_cache_file_under_the_cache_base_contains_the_token(self):
        # T-23-31: after a real refresh writes its cache, every file under
        # the cache base (data and lock) is free of the token.
        with tempfile.TemporaryDirectory() as directory:
            env, token = self._auth_env(directory)
            cache_base = str(pathlib.Path(directory) / "cache")
            data = core_normalize(
                load_dashboard_fixture("usage_pro"),
                load_dashboard_fixture("hard_limit_fixed"),
                load_dashboard_fixture("plan_info_monthly"),
            )

            def fetch_quota(_env):
                return data, None, ""

            self.assertEqual(probe_refresh(cache_base, env, lambda: 1000, fetch_quota), 0)
            walked = 0
            for root, _dirs, files in os.walk(cache_base):
                for name in files:
                    walked += 1
                    content = (pathlib.Path(root) / name).read_bytes()
                    self.assertNotIn(token.encode(), content, name)
            self.assertGreaterEqual(walked, 1)



class TestSyntheticCacheMidCycle(unittest.TestCase):
    """The preview cache sits 13 of 30 days into its cycle (30.2-02 D-09)."""

    NOW = 1_762_000_000

    def test_cycle_is_mid_cycle_and_included_gauge_is_green(self):
        tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools"))
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        import common_fmt

        data = cast(dict[str, Any], core_synthetic_cache(self.NOW)["data"])
        end = int((self.NOW + 17 * 86400) * 1000)
        self.assertEqual(data["cycle_end_ms"], end)
        self.assertEqual(data["cycle_start_ms"], end - 30 * 86400 * 1000)
        self.assertEqual(data["included_pct"], 42.0)
        self.assertEqual(data["api_pct"], 18.0)
        self.assertEqual(data["od_used_usd"], 2.5)
        self.assertEqual(data["od_ceiling_usd"], 20.0)
        self.assertEqual(data["included_period"], "monthly")
        start_s = cast(int, data["cycle_start_ms"]) / 1000
        end_s = cast(int, data["cycle_end_ms"]) / 1000
        gap = common_fmt.util_window_gap(42.0, start_s, end_s, self.NOW)
        self.assertIsNotNone(gap)
        self.assertLessEqual(abs(cast(float, gap)), 5.0)


class TestIncludedPeriod(unittest.TestCase):
    NOW = 1_762_000_000.0

    def _cache_with(self, period: object, *, drop: bool = False) -> dict[str, object]:
        cache = core_synthetic_cache(self.NOW)
        data = cast(dict[str, Any], cache["data"])
        if drop:
            del data["included_period"]
        else:
            data["included_period"] = period
        return cache

    def _period(self, cache: dict[str, object]) -> str | None:
        return core_quota_state(cache, self.NOW).included_period

    def test_period_is_carried_only_when_in_the_enum(self):
        self.assertEqual(self._period(self._cache_with("monthly")), "monthly")
        self.assertEqual(self._period(self._cache_with("weekly")), "weekly")
        for bad in (None, "daily"):
            self.assertIsNone(self._period(self._cache_with(bad)))
        self.assertIsNone(self._period(self._cache_with(None, drop=True)))


class TestExtraAlert(unittest.TestCase):
    """The one alert rule (30.2-02 D-12): at or above the threshold, source named."""

    def _quota(self, used, kind="fixed", ceiling: float | None = 20.0):
        return QuotaResult("ok", od_kind=kind, od_used_usd=used, od_ceiling_usd=ceiling)

    def test_cursor_limit_fires_at_or_above_and_not_below(self):
        at = core_extra_alert(None, self._quota(20.0))
        self.assertEqual(at, ExtraAlert(True, 20.0, "cursor"))
        below = core_extra_alert(None, self._quota(19.99))
        self.assertEqual(below, ExtraAlert(False, 20.0, "cursor"))
        self.assertTrue(core_extra_alert(None, self._quota(20.004)).fires)

    def test_override_wins_and_zero_is_valid(self):
        knobs: dict[str, object] = {"extra_alert": True, "extra_alert_usd": 0.0}
        self.assertEqual(core_extra_alert(knobs, self._quota(2.5)), ExtraAlert(True, 0.0, "config"))
        self.assertEqual(
            core_extra_alert({"extra_alert_usd": 5.0}, self._quota(2.5)),
            ExtraAlert(False, 5.0, "config"),
        )
        self.assertTrue(core_extra_alert({"extra_alert_usd": 2.5}, self._quota(2.5)).fires)
        self.assertFalse(core_extra_alert({"extra_alert_usd": 0.0}, self._quota(0.0)).fires)

    def test_switch_off_and_no_limit_give_no_alert(self):
        off = {"extra_alert": False, "extra_alert_usd": 5.0}
        self.assertEqual(core_extra_alert(off, self._quota(9.0)), ExtraAlert(False, None, "off"))
        for kind in ("unlimited", "disabled", "unavailable"):
            self.assertEqual(
                core_extra_alert(None, self._quota(2.5, kind=kind)), ExtraAlert(False, None, "none")
            )
        for ceiling in (None, 0.0):
            self.assertEqual(
                core_extra_alert(None, self._quota(2.5, ceiling=ceiling)),
                ExtraAlert(False, None, "none"),
            )
        unlimited = self._quota(2.5, kind="unlimited")
        self.assertTrue(core_extra_alert({"extra_alert_usd": 0.0}, unlimited).fires)

    def test_synthetic_cache_uses_the_cursor_limit_by_default(self):
        now = 1_762_000_000.0
        quota = core_quota_state(core_synthetic_cache(now), now)
        self.assertEqual(core_extra_alert(None, quota), ExtraAlert(False, 20.0, "cursor"))


if __name__ == "__main__":
    unittest.main()
