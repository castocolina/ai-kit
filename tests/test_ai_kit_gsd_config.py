import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-config"),
)

from ai_kit_gsd_config import cli, gsd_catalog, gsd_write


def make_fake_run(results):
    """Returns a callable matching `subprocess.run`'s signature, consuming `results` (a list
    of `(returncode, stdout, stderr)` tuples) in order -- repeating the last one once
    exhausted -- and recording every invoked argv on `.calls` so assertions can inspect
    exactly what was shelled out."""
    pending = list(results)

    def _fake_run(argv, **_kwargs):
        _fake_run.calls.append(list(argv))
        if pending:
            returncode, stdout, stderr = pending.pop(0)
        else:
            returncode, stdout, stderr = 0, "", ""
        return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr=stderr)

    _fake_run.calls = []
    return _fake_run


def fake_run(returncode, stdout="", stderr=""):
    """Single-result convenience wrapper over `make_fake_run`, matching `subprocess.run`'s
    signature for injection as `run_fn`."""
    return make_fake_run([(returncode, stdout, stderr)])


FAKE_NODE_BIN = "/usr/bin/node"


def _which_stub(path=FAKE_NODE_BIN):
    return lambda name: path if name == "node" else None


def _make_fake_install(root, include_model_catalog=True):
    """Builds a scratch fake-install tree `<root>/gsd-core/bin/gsd-tools.cjs` (and optionally
    its `lib/model-catalog.cjs` sibling) so `resolve_gsd_tools_path`/
    `resolve_model_catalog_cjs_path` resolve against REAL files on disk, never a mocked
    function -- only the eventual `node`/gsd-tools subprocess call is faked via `run_fn`."""
    bin_dir = os.path.join(root, "gsd-core", "bin")
    os.makedirs(bin_dir, exist_ok=True)
    gsd_tools_path = os.path.join(bin_dir, "gsd-tools.cjs")
    with open(gsd_tools_path, "w", encoding="utf-8") as f:
        f.write("// fake gsd-tools.cjs for hermetic tests\n")
    if include_model_catalog:
        lib_dir = os.path.join(bin_dir, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        with open(os.path.join(lib_dir, "model-catalog.cjs"), "w", encoding="utf-8") as f:
            f.write("// fake model-catalog.cjs for hermetic tests\n")
    return gsd_tools_path


class TestTracerEnsureProjectAndApplyProfile(unittest.TestCase):
    """Task 1 tracer: one model_profile answer travels from the CLI entrypoint through
    gsd-tools to a schema-validated config.json -- proven here via the exact argv shape
    shelled out, with no real subprocess/filesystem dependency."""

    def setUp(self):
        self.scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.scratch, ignore_errors=True)
        self.fake_install_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.fake_install_root, ignore_errors=True)
        self.fake_gsd_tools_path = _make_fake_install(self.fake_install_root)

    def test_ensure_project_then_apply_profile_argv_shapes(self):
        run = make_fake_run([(0, "", ""), (0, "model_profile=budget", "")])
        env_fn = lambda: {"CLAUDE_CONFIG_DIR": self.fake_install_root}

        exit1 = cli.main(
            ["ensure-project", "--project-dir", self.scratch],
            which_fn=_which_stub(),
            run_fn=run,
            env_fn=env_fn,
        )
        exit2 = cli.main(
            ["apply-profile", "--project-dir", self.scratch, "--profile", "budget"],
            which_fn=_which_stub(),
            run_fn=run,
            env_fn=env_fn,
        )

        self.assertEqual(exit1, 0)
        self.assertEqual(exit2, 0)
        self.assertEqual(
            run.calls[0],
            [
                FAKE_NODE_BIN,
                self.fake_gsd_tools_path,
                "config-new-project",
                "--cwd",
                self.scratch,
                "--raw",
            ],
        )
        self.assertEqual(
            run.calls[1],
            [
                FAKE_NODE_BIN,
                self.fake_gsd_tools_path,
                "config-set",
                "model_profile",
                "budget",
                "--project-dir",
                self.scratch,
                "--raw",
            ],
        )


class TestApplyProfileValidation(unittest.TestCase):
    def test_unknown_profile_rejected_before_any_subprocess_call(self):
        run = make_fake_run([])
        with self.assertRaises(SystemExit) as ctx:
            cli.main(
                ["apply-profile", "--project-dir", "/fake/project", "--profile", "bogus"],
                which_fn=_which_stub(),
                run_fn=run,
                env_fn=lambda: {},
            )
        self.assertNotEqual(ctx.exception.code, 0)
        self.assertEqual(run.calls, [])


class TestResolveMissing(unittest.TestCase):
    def test_missing_node_binary_exits_2(self):
        run = make_fake_run([])
        exit_code = cli.main(
            ["ensure-project", "--project-dir", "/fake/project"],
            which_fn=lambda name: None,
            run_fn=run,
            env_fn=lambda: {},
        )
        self.assertEqual(exit_code, 2)
        self.assertEqual(run.calls, [])

    def test_missing_gsd_tools_path_exits_2(self):
        # Override HOME (not just one host's own env var) to a nonexistent directory so
        # every candidate in gsd_catalog.GSD_CORE_ROOT_CANDIDATES' default-path fallback
        # also misses -- otherwise this dev machine's own real installs (e.g. ~/.claude,
        # ~/.cursor) would still resolve via the unoverridden candidates' HOME-relative
        # defaults, masking the "nothing found" path this test exists to cover.
        run = make_fake_run([])
        exit_code = cli.main(
            ["ensure-project", "--project-dir", "/fake/project"],
            which_fn=_which_stub(),
            run_fn=run,
            env_fn=lambda: {"HOME": "/definitely/nonexistent/home"},
        )
        self.assertEqual(exit_code, 2)
        self.assertEqual(run.calls, [])


class TestRealIntegration(unittest.TestCase):
    """Skips itself when no gsd-core is actually installed on the machine running the suite --
    the hermetic unit tests above never depend on this, but a dev box or CI box with gsd-core
    installed gets one real end-to-end proof."""

    _REAL_GSD_TOOLS = gsd_catalog.resolve_gsd_tools_path(dict(os.environ))

    @unittest.skipUnless(_REAL_GSD_TOOLS is not None, "no installed gsd-core found on this machine")
    def test_tracer_against_real_installed_gsd_tools(self):
        scratch = tempfile.mkdtemp()
        try:
            exit1 = cli.main(["ensure-project", "--project-dir", scratch])
            self.assertEqual(exit1, 0)
            exit2 = cli.main(["apply-profile", "--project-dir", scratch, "--profile", "budget"])
            self.assertEqual(exit2, 0)
            with open(os.path.join(scratch, ".planning", "config.json"), encoding="utf-8") as f:
                config = json.load(f)
            self.assertEqual(config.get("model_profile"), "budget")
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    @unittest.skipUnless(_REAL_GSD_TOOLS is not None, "no installed gsd-core found on this machine")
    def test_this_repos_own_config_is_never_touched(self):
        repo_config_path = os.path.join(
            os.path.dirname(__file__), "..", ".planning", "config.json"
        )
        with open(repo_config_path, "rb") as f:
            before = f.read()
        scratch = tempfile.mkdtemp()
        try:
            cli.main(["ensure-project", "--project-dir", scratch])
            cli.main(["apply-profile", "--project-dir", scratch, "--profile", "budget"])
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
        with open(repo_config_path, "rb") as f:
            after = f.read()
        self.assertEqual(before, after)


class TestGsdCatalogResolution(unittest.TestCase):
    def test_resolve_gsd_tools_path_returns_first_existing_candidate(self):
        def isfile_fn(path):
            return path == os.path.join("CURSOR_ROOT", "gsd-core", "bin", "gsd-tools.cjs")

        env = {"CLAUDE_CONFIG_DIR": "/nope", "CURSOR_CONFIG_DIR": "CURSOR_ROOT"}
        result = gsd_catalog.resolve_gsd_tools_path(env, isfile_fn)
        self.assertEqual(result, os.path.join("CURSOR_ROOT", "gsd-core", "bin", "gsd-tools.cjs"))

    def test_resolve_gsd_tools_path_returns_none_when_nothing_found(self):
        self.assertIsNone(gsd_catalog.resolve_gsd_tools_path({}, lambda path: False))

    def test_resolve_model_catalog_cjs_path_present(self):
        result = gsd_catalog.resolve_model_catalog_cjs_path(
            "/root/gsd-core/bin/gsd-tools.cjs", lambda path: True
        )
        self.assertEqual(result, "/root/gsd-core/bin/lib/model-catalog.cjs")

    def test_resolve_model_catalog_cjs_path_absent(self):
        result = gsd_catalog.resolve_model_catalog_cjs_path(
            "/root/gsd-core/bin/gsd-tools.cjs", lambda path: False
        )
        self.assertIsNone(result)

    def test_resolve_model_catalog_cjs_path_none_when_gsd_tools_path_is_none(self):
        self.assertIsNone(gsd_catalog.resolve_model_catalog_cjs_path(None))

    def test_resolve_node_binary_delegates_to_which_fn(self):
        resolved = gsd_catalog.resolve_node_binary(lambda name: "/usr/bin/node")
        self.assertEqual(resolved, "/usr/bin/node")
        self.assertIsNone(gsd_catalog.resolve_node_binary(lambda name: None))


class TestGsdWrite(unittest.TestCase):
    def test_ensure_config_exists_true_on_exit_zero(self):
        run = fake_run(0)
        self.assertTrue(
            gsd_write.ensure_config_exists(FAKE_NODE_BIN, "/fake/gsd-tools.cjs", "/fake/dir", run)
        )

    def test_ensure_config_exists_false_on_nonzero_exit(self):
        run = fake_run(1, stderr="boom")
        self.assertFalse(
            gsd_write.ensure_config_exists(FAKE_NODE_BIN, "/fake/gsd-tools.cjs", "/fake/dir", run)
        )

    def test_config_set_success_returns_stdout(self):
        run = fake_run(0, stdout="model_profile=budget")
        ok, output = gsd_write.config_set(
            FAKE_NODE_BIN, "/fake/gsd-tools.cjs", "/fake/dir", "model_profile", "budget", run
        )
        self.assertTrue(ok)
        self.assertEqual(output, "model_profile=budget")

    def test_config_set_failure_returns_stderr(self):
        run = fake_run(1, stderr="Error: bad key")
        ok, output = gsd_write.config_set(
            FAKE_NODE_BIN, "/fake/gsd-tools.cjs", "/fake/dir", "bogus.key", "x", run
        )
        self.assertFalse(ok)
        self.assertEqual(output, "Error: bad key")

    def test_config_set_coerces_python_bool_to_lowercase_string(self):
        run_true = make_fake_run([(0, "ok", "")])
        gsd_write.config_set(
            FAKE_NODE_BIN, "/fake/gsd-tools.cjs", "/fake/dir", "some.flag", True, run_true
        )
        self.assertIn("true", run_true.calls[0])
        self.assertNotIn("True", run_true.calls[0])

        run_false = make_fake_run([(0, "ok", "")])
        gsd_write.config_set(
            FAKE_NODE_BIN, "/fake/gsd-tools.cjs", "/fake/dir", "some.flag", False, run_false
        )
        self.assertIn("false", run_false.calls[0])
        self.assertNotIn("False", run_false.calls[0])


if __name__ == "__main__":
    unittest.main()
