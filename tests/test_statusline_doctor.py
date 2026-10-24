"""Tests for tools/statusline-doctor.py — the extracted introspection CLI.

The doctor script imports the host modules one-way via its own importlib shim;
this test module loads the doctor script the same way and exercises
parse_args / cmd_print_config / cmd_check / cmd_doctor / validate_config_file
for both hosts, plus env_help and the Cursor quota report.
"""

import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from typing import cast
from unittest import mock

_HERE = os.path.dirname(__file__)
_TOOLS_DIR = os.path.abspath(os.path.join(_HERE, "..", "tools"))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)
import claude_host
import common_config
import common_types
import cursor_host
import cursor_quota

_DOCTOR_PATH = os.path.join(_HERE, "..", "tools", "statusline-doctor.py")


def load_module():
    spec = importlib.util.spec_from_file_location("statusline_doctor", _DOCTOR_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


doctor = load_module()
sl = claude_host  # direct split-module access


class TestCLI(unittest.TestCase):
    def _write(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(body)
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_parse_args_defaults(self):
        ns = doctor.parse_args([])
        self.assertFalse(ns.print_config)
        self.assertIs(ns.check, doctor._NO_CHECK)

    def test_print_config_emits_resolved_json(self):
        import json

        cfg = common_types.Config(
            segments={"path": True},
            layout=[common_types.Line(0, ["path"])],
            palette={"BLUE": "1;34"},
            ramps={},
        )
        out = doctor.cmd_print_config(cfg, {})
        parsed = json.loads(out)
        self.assertEqual(parsed["segments"], {"path": True})
        self.assertEqual(parsed["layout"], [{"min_rows": 0, "segments": ["path"]}])
        self.assertEqual(parsed["palette"], {"BLUE": "1;34"})

    def test_check_valid_returns_zero(self):
        path = self._write("[segments]\nalt_cost = true\n")
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 0)

    def test_check_unknown_segment_returns_one(self):
        path = self._write("[segments]\nbogus = true\n")
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_bad_layout_ref_returns_one(self):
        path = self._write('[[line]]\nsegments = ["nope"]\n')
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_malformed_returns_one(self):
        path = self._write("= = not toml")
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_bad_palette_hex_returns_one(self):
        path = self._write('[palette]\nBLUE = "#zzz"\n')
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_unknown_modifier_returns_one(self):
        path = self._write('[palette]\nRED = "31+blink"\n')
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_bad_ramp_color_returns_one(self):
        path = self._write('[ramp.context]\n10 = "NOTACOLOR"\n')
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_bad_ramp_threshold_returns_one(self):
        path = self._write('[ramp.context]\noops = "RED"\n')
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 1)

    def test_check_valid_palette_and_ramp_returns_zero(self):
        path = self._write(
            '[palette]\nBLUE = "#3399ff"\n[ramp.context]\n50 = "GREEN"\ninf = "RED+bold"\n'
        )
        self.assertEqual(doctor.cmd_check(path, {"HOME": "/h"}), 0)

    def test_doctor_reports_env_problems_byte_identical(self):
        """cmd_check surfaces env-side bind errors byte-identical to cfg_warn output."""
        import io
        from contextlib import redirect_stderr

        env = {"CC_AI_KIT_GIT_CACHE_TTL": "not-an-int"}
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = doctor.cmd_check("", env)
        self.assertEqual(rc, 1)
        self.assertIn(
            f"{common_types.DIM}status-line: CC_AI_KIT_GIT_CACHE_TTL must be an integer, "
            f"got 'not-an-int' — ignored{common_types.RESET}",
            buf.getvalue(),
        )


class TestValidateConfigFile(unittest.TestCase):
    def _write(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as f:
            f.write(body)
        self.addCleanup(os.unlink, f.name)
        return f.name


class TestDoctor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Resolve config to a path that does NOT exist → defaults, which are valid.
        self.env = {
            "HOME": self.tmp,
            "CC_AI_KIT_CONFIG_FILE": os.path.join(self.tmp, "absent.toml"),
        }

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_doctor_ok_on_defaults(self):
        rc = doctor.cmd_doctor(self.env)
        self.assertEqual(rc, 0)

    def test_doctor_flags_a_raising_builder(self):
        def boom(data, avail, theme):
            del avail
            raise RuntimeError("x")

        with mock.patch.dict(claude_host.BUILDERS, {"path": boom}):
            rc = doctor.cmd_doctor(self.env)
        self.assertEqual(rc, 1)

    def test_doctor_flags_a_raising_disabled_builder(self):
        # A builder that is DISABLED by default (`alt_cost`) must still be
        # dry-rendered: the doctor catches a builder that would crash once enabled.
        self.assertFalse(
            common_config.cfg_default_config(claude_host.SPEC).segments.get("alt_cost")
        )

        def boom(data, avail, theme):
            del avail
            raise RuntimeError("x")

        with mock.patch.dict(claude_host.BUILDERS, {"alt_cost": boom}):
            rc = doctor.cmd_doctor(self.env)
        self.assertEqual(rc, 1)

    def test_doctor_flags_invalid_config_file(self):
        bad = os.path.join(self.tmp, "bad.toml")
        with open(bad, "w") as f:
            f.write("[segments]\nthis_is_not_a_segment = true\n")
        env = dict(self.env, CC_AI_KIT_CONFIG_FILE=bad)
        rc = doctor.cmd_doctor(env)
        self.assertEqual(rc, 1)

    def test_check_flag_still_works(self):
        # Back-compat: --check path is untouched.
        rc = doctor.cmd_check(os.path.join(self.tmp, "absent.toml"), self.env)
        self.assertEqual(rc, 1)  # absent file → cmd_check reports it (existing behavior)

    def test_bad_toml_value_is_diagnosed_not_a_traceback_both_hosts(self):
        # D-17 exact input: [[line]] with min_rows = "x" parses as TOML and
        # passes naive structural checks, but raises inside the render
        # pipeline's layout resolution — the renderer exits 0 pointing at this
        # doctor, so --check and --doctor ARE the recovery path and must
        # return an actionable nonzero diagnostic for BOTH hosts, never a
        # traceback.
        body = '[[line]]\nmin_rows = "x"\nsegments = ["path"]\n'
        for host_name in ("claude", "cursor"):
            host = doctor.HOSTS[host_name]
            with self.subTest(host=host_name):
                bad = os.path.join(self.tmp, f"bad-{host_name}.toml")
                with open(bad, "w", encoding="utf-8") as handle:
                    handle.write(body)
                env = {"HOME": self.tmp,
                       "PATH": os.environ.get("PATH", ""),
                       "CC_AI_KIT_CONFIG_FILE": bad,
                       "AI_KIT_CURSOR_CONFIG_FILE": bad}
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    rc = doctor.cmd_check(bad, env, host=host)
                self.assertEqual(rc, 1)
                self.assertIn("min_rows", err.getvalue())
                out, err = io.StringIO(), io.StringIO()
                fetch = lambda _env: (None, "auth_missing", "")
                with redirect_stdout(out), redirect_stderr(err):
                    rc = doctor.cmd_doctor(env, host, fetch_quota=fetch)
                self.assertEqual(rc, 1)
                self.assertIn("min_rows", err.getvalue())


class TestHostSwitch(unittest.TestCase):
    """--host claude|cursor: default claude, per-host --help epilog, argparse boundary."""

    def _tmp(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        return d

    def _run_help(self, extra):
        env = {"HOME": self._tmp(), "PATH": os.environ.get("PATH", "")}
        proc = subprocess.run(
            [sys.executable, "-S", _DOCTOR_PATH, *extra, "--help"],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout

    def test_parse_args_defaults_to_claude(self):
        ns = doctor.parse_args([])
        self.assertEqual(ns.host, "claude")
        self.assertFalse(ns.print_config)
        self.assertIs(ns.check, doctor._NO_CHECK)

    def test_parse_args_cursor(self):
        ns = doctor.parse_args(["--host", "cursor", "--doctor"])
        self.assertEqual(ns.host, "cursor")
        self.assertTrue(ns.doctor)

    def test_host_bogus_exits_two(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            doctor.parse_args(["--host", "bogus"])
        self.assertEqual(cm.exception.code, 2)

    def test_env_help_claude_matches_legacy_text(self):
        self.assertEqual(doctor.env_help(claude_host.SPEC), doctor._ENV_HELP)

    def test_env_help_cursor_lists_cursor_names(self):
        text = doctor.env_help(cursor_host.SPEC)
        self.assertIn("AI_KIT_CURSOR_CONFIG_FILE", text)
        self.assertIn("AI_KIT_CURSOR_SEGMENT_<KEY>", text)
        self.assertIn("AI_KIT_CURSOR_PROVIDER_", text)
        self.assertNotIn("CC_AI_KIT_", text)

    def test_help_default_host_lists_host_flag_and_claude_env(self):
        out = self._run_help([])
        self.assertIn("--host", out)
        self.assertIn("CC_AI_KIT_CONFIG_FILE", out)

    def test_help_cursor_host_lists_cursor_env(self):
        out = self._run_help(["--host", "cursor"])
        self.assertIn("--host", out)
        self.assertIn("AI_KIT_CURSOR_CONFIG_FILE", out)
        self.assertNotIn("CC_AI_KIT_CONFIG_FILE", out)


class TestCursorDoctor(unittest.TestCase):
    """--host cursor --doctor: offline validation + dry render, plus ONE explicit
    foreground quota refresh. Tests inject the fetch explicitly and deny the real
    fetch seam and any detached spawn as a network backstop — nothing here may
    reach the network, and a stale-free run spawns no detached refresher."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.env = {
            "HOME": self.tmp,
            "PATH": os.environ.get("PATH", ""),
            "XDG_CONFIG_HOME": os.path.join(self.tmp, "cfg"),
            "XDG_CACHE_HOME": os.path.join(self.tmp, "cache"),
            "AI_KIT_CURSOR_CONFIG_FILE": os.path.join(self.tmp, "cursor-statusline.toml"),
        }
        os.makedirs(self.env["XDG_CONFIG_HOME"])
        os.makedirs(self.env["XDG_CACHE_HOME"])
        with open(self.env["AI_KIT_CURSOR_CONFIG_FILE"], "w") as f:
            f.write("[segments]\nrender_time = false\n")
        self.now = 1_800_000_000.0
        self.fetches = []
        self.spawns = []
        patches = [
            mock.patch.object(
                cursor_quota,
                "probe_fetch_quota",
                side_effect=AssertionError("network denied by test backstop"),
            ),
            mock.patch.object(
                cursor_quota,
                "probe_spawn_detached",
                side_effect=lambda *a, **k: self.spawns.append((a, k)) or True,
            ),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _seed_cache(self, cache):
        cache_base = common_config.cfg_cache_base(dict(self.env))
        path, _lock = cursor_quota.probe_cache_paths(cache_base)
        self.assertTrue(cursor_quota.probe_write_cache(path, cache))

    def _seed_fresh_synthetic(self):
        self._seed_cache(cursor_quota.core_synthetic_cache(self.now))

    def _stale_positive_cache(self):
        cache = cursor_quota.core_synthetic_cache(self.now - 3600.0)
        return cache

    def _fetch(self, result):
        def fake(env):
            self.fetches.append(dict(env))
            return result

        return fake

    def _run(self, fetch):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = doctor.cmd_doctor(self.env, cursor_host.HOST, fetch_quota=fetch, now=self.now)
        return out.getvalue(), err.getvalue(), rc

    def test_doctor_ok_reports_config_builders_and_quota(self):
        self._seed_fresh_synthetic()
        out, err, rc = self._run(self._fetch((None, None, "")))
        self.assertEqual(rc, 0, err)
        self.assertIn(f"{self.env['AI_KIT_CURSOR_CONFIG_FILE']}: OK", out)
        self.assertIn(f"all {len(cursor_host.BUILDERS)} segments render cleanly", out)
        self.assertIn("quota: ok (inferred — undocumented Cursor API)", out)
        # Fresh cache: no fetch needed, no detached refresher spawned.
        self.assertEqual(self.fetches, [])
        self.assertEqual(self.spawns, [])

    def test_doctor_auth_expired_points_at_login(self):
        out, err, rc = self._run(
            self._fetch((None, "auth_expired", "Cursor authentication unavailable"))
        )
        self.assertEqual(rc, 0, err)
        self.assertEqual(len(self.fetches), 1)
        self.assertIn("quota: auth_expired (inferred — undocumented Cursor API)", out)
        self.assertIn("cursor-agent login", out)

    def test_doctor_lock_held_skips_refresh(self):
        cache_base = common_config.cfg_cache_base(dict(self.env))
        _path, lock_path = cursor_quota.probe_cache_paths(cache_base)
        fd = cursor_quota.probe_try_lock(lock_path)
        self.assertIsNotNone(fd)
        self.addCleanup(cursor_quota.probe_release_lock, cast(int, fd))
        out, err, rc = self._run(self._fetch((None, None, "")))
        self.assertEqual(rc, 0, err)
        self.assertIn("refresh is in progress", out)
        self.assertEqual(self.fetches, [])
        self.assertEqual(self.spawns, [])

    def test_token_absent_from_stdout_and_stderr(self):
        auth_dir = os.path.join(self.env["XDG_CONFIG_HOME"], "cursor")
        os.makedirs(auth_dir)
        with open(os.path.join(auth_dir, "auth.json"), "w") as f:
            f.write('{"accessToken": "dummytok-doctor-absence-check"}')
        self._seed_cache(self._stale_positive_cache())
        data = cursor_quota.core_synthetic_cache(self.now)["data"]
        out, err, rc = self._run(self._fetch((data, None, "")))
        self.assertEqual(rc, 0, err)
        self.assertEqual(len(self.fetches), 1)  # the foreground refresh ran
        self.assertNotIn("dummytok-doctor-absence-check", out)
        self.assertNotIn("dummytok-doctor-absence-check", err)
        self.assertIn("quota: ok (inferred — undocumented Cursor API)", out)

    def test_check_cursor_flags_claude_only_segment(self):
        path = os.path.join(self.tmp, "claude-only.toml")
        with open(path, "w") as f:
            f.write("[segments]\neffort = true\n")
        err = io.StringIO()
        with redirect_stderr(err):
            rc_cursor = doctor.cmd_check(path, self.env, cursor_host.HOST)
            rc_claude = doctor.cmd_check(path, self.env)
        self.assertEqual(rc_cursor, 1)
        self.assertIn("unknown segment key: effort", err.getvalue())
        self.assertEqual(rc_claude, 0)

    def test_print_config_cursor_lists_cursor_segments_dir(self):
        import json

        env = {k: v for k, v in self.env.items() if k != "AI_KIT_CURSOR_CONFIG_FILE"}
        cfg = common_config.cfg_load_config(env, cursor_host.SPEC)
        blob = json.loads(doctor.cmd_print_config(cfg, env))
        self.assertIn("cursor_included", blob["segments"])
        self.assertTrue(blob["external"]["dir"].endswith("segments-cursor"))


if __name__ == "__main__":
    unittest.main()
