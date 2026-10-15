"""Inventory tracer, gsd-core resolution, probe fail-closed paths, and real-gsd smoke (17-03)."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import cli, gsd_catalog, host, plan_io, presets
from ai_kit_spec import gsd_tools

from tests.test_ai_kit_gsd_curated_config import _RealGsdTestCase

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def make_gsd_install(install_root, version="1.16.0", *, include_config_schema=True):
    """Minimal fake gsd-core tree under `install_root` (the install root, not project root)."""
    bin_dir = os.path.join(install_root, "bin")
    lib_dir = os.path.join(bin_dir, "lib")
    os.makedirs(lib_dir, exist_ok=True)
    with open(os.path.join(install_root, "VERSION"), "w", encoding="utf-8") as fh:
        fh.write(version + "\n")
    with open(os.path.join(bin_dir, "gsd-tools.cjs"), "w", encoding="utf-8") as fh:
        fh.write("// fake\n")
    with open(os.path.join(lib_dir, "model-catalog.cjs"), "w", encoding="utf-8") as fh:
        fh.write("// fake\n")
    if include_config_schema:
        with open(os.path.join(lib_dir, "config-schema.cjs"), "w", encoding="utf-8") as fh:
            fh.write("// fake\n")
    return os.path.join(bin_dir, "gsd-tools.cjs")


def _default_tables_from_argv(argv):
    keys = json.loads(argv[6])
    return json.dumps(
        {
            "runtime_profile_map": {"codex": {"opus": {"model": "gpt-5.6-sol"}}},
            "model_profiles": {"gsd-planner": {"adaptive": "opus"}},
            "agent_to_phase_type": {"gsd-planner": "planning"},
            "valid_keys": {"accepted": keys, "rejected": []},
        }
    )


class FakeRun:
    """Records subprocess argv; answers git and node `-e` calls from configurable maps."""

    def __init__(self, git_answers=None, node_stdout=None):
        self.argv_log: list[list] = []
        self.kw_log: list[dict] = []
        self.git_answers = git_answers or {}
        self.node_stdout = node_stdout

    def __call__(self, cmd, **kw):
        self.argv_log.append(list(cmd))
        self.kw_log.append(dict(kw))
        if cmd and cmd[0] == "git":
            key = cmd[-1]
            if key in self.git_answers:
                rc, out = self.git_answers[key]
                return subprocess.CompletedProcess(cmd, rc, out, "")
            return subprocess.CompletedProcess(cmd, 128, "", "")
        if len(cmd) >= 3 and cmd[0] == "node" and cmd[1] == "-e":
            out = self.node_stdout
            if callable(out):
                out = out(cmd)
            elif out is None:
                out = _default_tables_from_argv(cmd)
            return subprocess.CompletedProcess(cmd, 0, out, "")
        return subprocess.CompletedProcess(cmd, 1, "", "")


def run_inventory(project, env, fake, *extra):
    stdout = io.StringIO()
    stderr = io.StringIO()
    argv = ["inventory", "--project-dir", project, *extra]
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = cli.main(
            argv,
            which_fn=lambda name: "node" if name == "node" else None,
            env_fn=lambda: dict(env),
            run_fn=fake,
        )
    err = stderr.getvalue()
    raw = stdout.getvalue()
    parsed = json.loads(raw) if code == 0 and raw.strip() else None
    return code, parsed, err


def real_gsd_run(child_env, node_bin, fallback=None):
    """Allow only real node/git subprocesses in real-gsd tests."""

    def _run(cmd, **kw):
        if cmd and (cmd[0] == node_bin or cmd[0] == "git"):
            merged = {**kw, "env": child_env}
            return subprocess.run(cmd, **merged)
        if fallback is not None:
            return fallback(cmd, **kw)
        raise AssertionError(f"real-gsd test reached a non-node/git subprocess: {cmd[:3]}")

    return _run


class TestInventoryTracer(unittest.TestCase):
    def test_end_to_end_fake_claude_gsd_core(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        install = os.path.join(project, ".claude", "gsd-core")
        make_gsd_install(install)
        env = {"HOME": home, "PATH": ""}
        fake = FakeRun()
        code, parsed, _err = run_inventory(project, env, fake, "--host", "opencode")
        self.assertEqual(code, 0)
        assert parsed is not None
        self.assertEqual(parsed["schema_version"], 1)
        self.assertEqual(parsed["host"], "opencode")
        self.assertEqual(parsed["host_source"], "flag")
        self.assertEqual(parsed["gsd_core"]["path"], install)
        self.assertEqual(parsed["gsd_core"]["scope"], "local")
        self.assertEqual(parsed["gsd_core"]["version"], "1.16.0")
        node_calls = [a for a in fake.argv_log if a and a[0] == "node"]
        self.assertEqual(len(node_calls), 1)
        argv = node_calls[0]
        self.assertEqual(argv[1], "-e")
        self.assertEqual(argv[3], os.path.join(install, "bin", "lib", "model-catalog.cjs"))
        self.assertEqual(argv[4], os.path.join(install, "bin", "lib", "config-schema.cjs"))
        self.assertEqual(argv[5], project)
        self.assertEqual(json.loads(argv[6]), presets.closed_key_set("opencode"))
        script = argv[2]
        for key in presets.closed_key_set("opencode"):
            if "." not in key:
                continue  # undotted keys can appear as substrings of export names in the script
            self.assertNotIn(key, script)
        out_buf = io.StringIO()
        with contextlib.redirect_stdout(out_buf):
            cli.main(
                ["inventory", "--project-dir", project, "--host", "opencode"],
                which_fn=lambda name: "node" if name == "node" else None,
                env_fn=lambda: dict(env),
                run_fn=fake,
            )
        self.assertEqual(out_buf.getvalue(), plan_io.canonical_json(parsed))

    def test_local_gsd_core_roots_matches_gsd_core_roots_prefix(self):
        root = "/tmp/proj"
        env = {"HOME": "/tmp/h"}
        self.assertEqual(
            gsd_tools.local_gsd_core_roots(root),
            gsd_tools.gsd_core_roots(env, root)[:3],
        )

    def test_real_gsd_run_allows_node_and_git_only(self):
        child_env = {"HOME": "/tmp/x", "PATH": ""}
        node = "/usr/bin/node"
        run = real_gsd_run(child_env, node)
        with mock.patch("subprocess.run") as mocked:
            mocked.return_value = subprocess.CompletedProcess(["git"], 0, "", "")
            run(["git", "-C", "p", "rev-parse", "--show-toplevel"], capture_output=True)
            _, kwargs = mocked.call_args
            self.assertIs(kwargs["env"], child_env)
        with self.assertRaisesRegex(AssertionError, "non-node/git"):
            run([sys.executable, "x/ai-kit-spec.py", "detect-runtimes"])
        seen = []

        def fake(cmd, **kw):
            seen.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        run2 = real_gsd_run(child_env, node, fallback=fake)
        run2([sys.executable, "x/ai-kit-spec.py", "detect-runtimes"])
        self.assertEqual(len(seen), 1)


class TestRealGsdInventory(_RealGsdTestCase):
    def test_inventory_each_host_against_checkout_gsd_core(self):
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        self.require_real_gsd(project)
        version_path = os.path.join(_REPO_ROOT, ".claude", "gsd-core", "VERSION")
        with open(version_path, encoding="utf-8") as fh:
            expected_version = fh.read().strip()
        for host_name in host.HOSTS:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = cli.main(
                    ["inventory", "--project-dir", project, "--host", host_name],
                    which_fn=lambda name: self.node_bin if name == "node" else None,
                    env_fn=lambda: dict(self.resolve_env),
                    run_fn=real_gsd_run(self.child_env, self.node_bin),
                )
            self.assertEqual(code, 0, host_name)
            parsed = json.loads(stdout.getvalue())
            self.assertEqual(parsed["gsd_core"]["version"], expected_version)
            self.assertEqual(parsed["gsd_core"]["scope"], "local")
            self.assertIn("gsd-planner", parsed["gsd_core"]["model_profiles"])
            self.assertEqual(parsed["gsd_core"]["valid_keys"]["rejected"], [])


class TestGsdCoreResolution(unittest.TestCase):
    def _home_env(self):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        return home, {"HOME": home, "PATH": ""}

    def test_local_claude_wins_over_global(self):
        home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"), version="1.16.0")
        make_gsd_install(os.path.join(home, ".claude", "gsd-core"), version="9.9.9")
        fake = FakeRun()
        code, parsed, _ = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 0)
        assert parsed
        self.assertEqual(parsed["gsd_core"]["scope"], "local")
        self.assertEqual(parsed["gsd_core"]["version"], "1.16.0")
        self.assertEqual(
            parsed["gsd_core"]["path"], os.path.join(project, ".claude", "gsd-core")
        )

    def test_global_only_is_labelled_global(self):
        home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        global_root = os.path.join(home, ".claude", "gsd-core")
        make_gsd_install(global_root, version="1.16.0")
        fake = FakeRun()
        code, parsed, _ = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 0)
        assert parsed
        self.assertEqual(parsed["gsd_core"]["scope"], "global")
        self.assertEqual(parsed["gsd_core"]["path"], global_root)

    def test_pi_prefers_dot_pi_over_dot_claude(self):
        _home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        make_gsd_install(os.path.join(project, ".pi", "gsd-core"), version="1.16.0")
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"), version="9.9.9")
        fake = FakeRun()
        code, parsed, _ = run_inventory(project, env, fake, "--host", "pi")
        self.assertEqual(code, 0)
        assert parsed
        self.assertEqual(parsed["gsd_core"]["path"], os.path.join(project, ".pi", "gsd-core"))

    def test_claude_host_ignores_dot_pi(self):
        _home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        make_gsd_install(os.path.join(project, ".pi", "gsd-core"), version="9.9.9")
        claude_root = os.path.join(project, ".claude", "gsd-core")
        make_gsd_install(claude_root, version="1.16.0")
        fake = FakeRun()
        code, parsed, _ = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 0)
        assert parsed
        self.assertEqual(parsed["gsd_core"]["path"], claude_root)

    def test_pi_global_from_pi_agent_home(self):
        home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        pi_global = os.path.join(home, ".pi", "agent", "gsd-core")
        make_gsd_install(pi_global, version="1.16.0")
        fake = FakeRun()
        code, parsed, _ = run_inventory(project, env, fake, "--host", "pi")
        self.assertEqual(code, 0)
        assert parsed
        self.assertEqual(parsed["gsd_core"]["scope"], "global")
        self.assertEqual(parsed["gsd_core"]["path"], pi_global)

    def test_pi_missing_install_lists_dot_pi_first(self):
        _home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        fake = FakeRun()
        code, _parsed, err = run_inventory(project, env, fake, "--host", "pi")
        self.assertEqual(code, 2)
        first = os.path.join(project, ".pi", "gsd-core", "bin", "gsd-tools.cjs")
        self.assertIn(first, err)

    def test_worktree_global_warns_when_main_has_local(self):
        home, env = self._home_env()
        project = tempfile.mkdtemp()
        main = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        self.addCleanup(shutil.rmtree, main, ignore_errors=True)
        make_gsd_install(os.path.join(home, ".claude", "gsd-core"))
        make_gsd_install(os.path.join(main, ".claude", "gsd-core"))
        git_answers = {
            "--show-toplevel": (0, project + "\n"),
            "--git-common-dir": (0, os.path.join(main, ".git") + "\n"),
        }
        fake = FakeRun(git_answers=git_answers)
        code, parsed, _ = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 0)
        assert parsed
        self.assertEqual(len(parsed["warnings"]), 1)
        self.assertIn(main, parsed["warnings"][0])
        self.assertIn("versions can differ", parsed["warnings"][0])

    def test_worktree_no_warning_without_main_local(self):
        home, env = self._home_env()
        project = tempfile.mkdtemp()
        main = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        self.addCleanup(shutil.rmtree, main, ignore_errors=True)
        make_gsd_install(os.path.join(home, ".claude", "gsd-core"))
        git_answers = {
            "--show-toplevel": (0, project + "\n"),
            "--git-common-dir": (0, os.path.join(main, ".git") + "\n"),
        }
        fake = FakeRun(git_answers=git_answers)
        code, parsed, _ = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 0)
        assert parsed
        self.assertEqual(parsed["warnings"], [])

    def test_local_install_skips_git_common_dir(self):
        _home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        fake = FakeRun()
        run_inventory(project, env, fake, "--host", "claude")
        common_calls = [
            a for a in fake.argv_log if a[:3] == ["git", "-C", project] and "--git-common-dir" in a
        ]
        self.assertEqual(common_calls, [])

    def test_no_install_lists_searched_paths(self):
        home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        fake = FakeRun()
        code, _parsed, err = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 2)
        self.assertIn("searched:", err)
        self.assertIn(os.path.join(project, "gsd-core", "bin", "gsd-tools.cjs"), err)
        self.assertIn(os.path.join(home, ".claude", "gsd-core", "bin", "gsd-tools.cjs"), err)

    def test_missing_host_flag_exits_two(self):
        _home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        fake = FakeRun()
        code, _parsed, err = run_inventory(project, env, fake)
        self.assertEqual(code, 2)
        self.assertIn("pass --host", err)

    def test_opencode_detected_without_flag(self):
        _home, env = self._home_env()
        env["OPENCODE"] = "1"
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        fake = FakeRun()
        code, parsed, _ = run_inventory(project, env, fake)
        self.assertEqual(code, 0)
        assert parsed
        self.assertEqual(parsed["host"], "opencode")
        self.assertEqual(parsed["host_source"], "detected")

    def test_missing_sibling_exits_two_no_node(self):
        _home, env = self._home_env()
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        make_gsd_install(os.path.join(project, ".claude", "gsd-core"))
        fake = FakeRun()
        with mock.patch.object(gsd_catalog, "load_ai_kit_spec_module", return_value=None):
            code, _parsed, err = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 2)
        self.assertIn("ai-kit-spec-review", err)
        node_calls = [a for a in fake.argv_log if a and a[0] == "node"]
        self.assertEqual(node_calls, [])


class TestProbeFailures(unittest.TestCase):
    def _project_with_install(self, *, include_config_schema=True):
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        root = os.path.join(project, ".claude", "gsd-core")
        make_gsd_install(root, include_config_schema=include_config_schema)
        env = {"HOME": home, "PATH": ""}
        return project, env, root

    def test_node_null_stdout_fails_closed(self):
        project, env, root = self._project_with_install()
        fake = FakeRun(node_stdout="null")
        code, _parsed, err = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 2)
        self.assertIn("isValidConfigKey unavailable", err)
        self.assertIn(root, err)
        self.assertIn("1.16.0", err)

    def test_node_nonzero_exit_fails_closed(self):
        project, env, root = self._project_with_install()

        def bad_node(cmd, **kw):
            if cmd[0] == "node":
                return subprocess.CompletedProcess(cmd, 1, "null", "")
            return FakeRun()(cmd, **kw)

        code, _parsed, err = run_inventory(project, env, bad_node, "--host", "claude")
        self.assertEqual(code, 2)
        self.assertIn("isValidConfigKey unavailable", err)
        self.assertIn(root, err)

    def test_node_timeout_fails_closed(self):
        project, env, root = self._project_with_install()

        def timeout_node(cmd, **kw):
            if cmd[0] == "node":
                raise subprocess.TimeoutExpired(cmd, 30)
            return FakeRun()(cmd, **kw)

        code, _parsed, err = run_inventory(project, env, timeout_node, "--host", "claude")
        self.assertEqual(code, 2)
        self.assertIn("isValidConfigKey unavailable", err)
        self.assertIn(root, err)

    def test_missing_node_skips_probe(self):
        project, env, _root = self._project_with_install()
        fake = FakeRun()
        with mock.patch.object(gsd_catalog, "resolve_node_binary", return_value=None):
            code, _parsed, err = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 2)
        self.assertIn("node", err.lower())
        node_calls = [a for a in fake.argv_log if a and a[0] == "node"]
        self.assertEqual(node_calls, [])

    def test_missing_config_schema_cjs(self):
        project, env, root = self._project_with_install(include_config_schema=False)
        fake = FakeRun()
        code, _parsed, err = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 2)
        self.assertIn(root, err)
        self.assertIn("config-schema.cjs", err)

    def test_parse_tables_output_rejects_malformed(self):
        from ai_kit_gsd_curated_config.gsd_catalog import _parse_tables_output

        good_keys = ["a"]
        good = json.dumps(
            {
                "runtime_profile_map": {"x": {"y": {}}},
                "model_profiles": {"p": {}},
                "agent_to_phase_type": {"a": "b"},
                "valid_keys": {"accepted": good_keys, "rejected": []},
            }
        )
        self.assertIsNotNone(_parse_tables_output(good))
        for bad in ("x", "[]", "{}", json.dumps({"model_profiles": {"p": {}}})):
            self.assertIsNone(_parse_tables_output(bad))
        empty_profiles = json.dumps(
            {
                "runtime_profile_map": {"x": {"y": {}}},
                "model_profiles": {},
                "agent_to_phase_type": {"a": "b"},
                "valid_keys": {"accepted": [], "rejected": []},
            }
        )
        self.assertIsNone(_parse_tables_output(empty_profiles))
        bad_accepted = json.dumps(
            {
                "runtime_profile_map": {"x": {"y": {}}},
                "model_profiles": {"p": {}},
                "agent_to_phase_type": {"a": "b"},
                "valid_keys": {"accepted": "nope", "rejected": []},
            }
        )
        self.assertIsNone(_parse_tables_output(bad_accepted))
        bad_rejected = json.dumps(
            {
                "runtime_profile_map": {"x": {"y": {}}},
                "model_profiles": {"p": {}},
                "agent_to_phase_type": {"a": "b"},
                "valid_keys": {"accepted": [], "rejected": [1]},
            }
        )
        self.assertIsNone(_parse_tables_output(bad_rejected))

    def test_inventory_does_not_mutate_project_tree(self):
        project, env, _root = self._project_with_install()
        before = {}
        for dirpath, _dirnames, filenames in os.walk(project):
            for name in filenames:
                path = os.path.join(dirpath, name)
                with open(path, "rb") as fh:
                    before[path] = fh.read()
        fake = FakeRun()
        code, _parsed, _err = run_inventory(project, env, fake, "--host", "claude")
        self.assertEqual(code, 0)
        after = {}
        for dirpath, _dirnames, filenames in os.walk(project):
            for name in filenames:
                path = os.path.join(dirpath, name)
                with open(path, "rb") as fh:
                    after[path] = fh.read()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
