"""Tests for the one shared gsd-tools resolver and config write wrappers
(`ai_kit_spec.gsd_tools`, D-18): launcher-order candidates pinned to `edge_floor.py`'s
`engine_candidates`, project-local-first resolution (R17), the wrapper argv shapes, and --
via a `skipUnless` class -- the real gsd-core `previousValue` contract the plan 16.1-10
undo log relies on. All filesystem fixtures live in tempfile dirs; the only real
gsd-tools run is `TestRealGsdTools` against the checkout's own `.claude/gsd-core` on a
scratch project."""
import importlib
import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

gsd_tools = importlib.import_module("ai_kit_spec.gsd_tools")


def _load_edge_floor():
    spec = importlib.util.spec_from_file_location(
        "edge_floor_under_test",
        os.path.join(_REPO_ROOT, "skills", "ai-kit-gsd-spec-discuss", "scripts", "edge_floor.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EDGE_FLOOR = _load_edge_floor()


def _mkdtemp():
    d = tempfile.mkdtemp()
    return d


def _write(path, content=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def recording_run(results):
    """run_fn returning `subprocess.CompletedProcess` per `(rc, stdout, stderr)`, repeating
    the last once exhausted, and recording every argv on `.calls`."""
    pending = list(results)

    def _run(argv, **_kwargs):
        _run.calls.append(list(argv))
        rc, stdout, stderr = pending.pop(0) if pending else (0, "", "")
        return subprocess.CompletedProcess(argv, rc, stdout=stdout, stderr=stderr)

    _run.calls = []
    return _run


GSD_TOOLS_SUFFIX = gsd_tools.GSD_TOOLS_REL
EDGE_SUFFIX = EDGE_FLOOR.ENGINE_REL


class TestResolverOrder(unittest.TestCase):
    """D-18/R17: candidate order is GSD's own launcher order, pinned to edge_floor."""

    def test_gsd_core_roots_project_local_first_then_host_homes(self):
        env = {"HOME": "H"}
        roots = gsd_tools.gsd_core_roots(env, "R")
        self.assertEqual(roots[:3], ["R/gsd-core", "R/.claude/gsd-core", "R/.codex/gsd-core"])
        self.assertEqual(roots[3:], [os.path.join(h, "gsd-core") for h in
                                     gsd_tools._host_homes(env)])

    def test_non_launcher_candidates_match_edge_floor_engine_candidates(self):
        env = {
            "HOME": _mkdtemp(),
            "XDG_CONFIG_HOME": _mkdtemp(),
            "CODEX_HOME": _mkdtemp(),
            "CLAUDE_CONFIG_DIR": _mkdtemp(),
        }
        self.addCleanup(shutil.rmtree, env["HOME"], ignore_errors=True)
        self.addCleanup(shutil.rmtree, env["XDG_CONFIG_HOME"], ignore_errors=True)
        self.addCleanup(shutil.rmtree, env["CODEX_HOME"], ignore_errors=True)
        self.addCleanup(shutil.rmtree, env["CLAUDE_CONFIG_DIR"], ignore_errors=True)
        root = _mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        ours = gsd_tools.gsd_tools_candidates(env, root)
        theirs = EDGE_FLOOR.engine_candidates(env, root)
        ours_stripped = [p[: -len(GSD_TOOLS_SUFFIX)] for p in ours]
        theirs_stripped = [p[: -len(EDGE_SUFFIX)] for p in theirs]
        self.assertEqual(ours_stripped, theirs_stripped)

    def test_launcher_candidate_from_path_and_absent_without_path(self):
        tree = _mkdtemp()
        self.addCleanup(shutil.rmtree, tree, ignore_errors=True)
        home = _mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        start = _mkdtemp()  # empty: the checkout's own .claude/gsd-core is never a candidate
        self.addCleanup(shutil.rmtree, start, ignore_errors=True)
        bin_dir = os.path.join(tree, "gsd-core", "bin")
        launcher = _write(os.path.join(bin_dir, "gsd_run"), "#!/bin/sh\n")
        os.chmod(launcher, os.stat(launcher).st_mode | stat.S_IXUSR | stat.S_IXGRP
                 | stat.S_IXOTH)
        gsd_tools_path = _write(os.path.join(bin_dir, "gsd-tools.cjs"), "// fake\n")
        env = {"HOME": home, "PATH": bin_dir}
        candidates = gsd_tools.gsd_tools_candidates(env, start)
        self.assertEqual(candidates[-1], gsd_tools_path)
        self.assertEqual(gsd_tools.resolve_gsd_tools(env, start=start), gsd_tools_path)
        no_path_env = {"HOME": home}
        self.assertEqual(gsd_tools.gsd_tools_candidates(no_path_env, start),
                         candidates[:-1])
        self.assertIsNone(gsd_tools.resolve_gsd_tools(no_path_env, start=start))


class TestLocalFirst(unittest.TestCase):
    """R17 adjacency: with both a project-local and a global fake gsd-core, the local one
    wins; each alone is found; neither returns None."""

    def test_project_local_wins_over_home_install(self):
        project = _mkdtemp()
        self.addCleanup(shutil.rmtree, project, ignore_errors=True)
        home = _mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        local = _write(os.path.join(project, ".claude", "gsd-core", "bin", "gsd-tools.cjs"))
        _write(os.path.join(home, ".claude", "gsd-core", "bin", "gsd-tools.cjs"))
        env = {"HOME": home, "RUNTIME_DIR": project}
        self.assertEqual(gsd_tools.resolve_gsd_tools(env, start=project), local)

    def test_global_only_found(self):
        home = _mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        start = _mkdtemp()
        self.addCleanup(shutil.rmtree, start, ignore_errors=True)
        expected = _write(os.path.join(home, ".codex", "gsd-core", "bin", "gsd-tools.cjs"))
        env = {"HOME": home}
        self.assertEqual(gsd_tools.resolve_gsd_tools(env, start=start), expected)

    def test_none_when_nothing_found(self):
        home = _mkdtemp()
        self.addCleanup(shutil.rmtree, home, ignore_errors=True)
        start = _mkdtemp()
        self.addCleanup(shutil.rmtree, start, ignore_errors=True)
        self.assertIsNone(gsd_tools.resolve_gsd_tools({"HOME": home}, start=start))


class TestWrappers(unittest.TestCase):
    """The config-* wrapper argv shapes and the `previousValue` contract (D-17/RUN-11)."""

    TOOLS = gsd_tools.GsdTools("node", "/g/gsd-tools.cjs")

    def test_config_set_argv_and_none_unset(self):
        run = recording_run([(0, '{"updated": true}', "")])
        ok, output = gsd_tools.config_set(self.TOOLS, "/p", "a.b", None, run_fn=run)
        self.assertTrue(ok)
        self.assertEqual(output, '{"updated": true}')
        self.assertEqual(
            run.calls[0],
            ["node", "/g/gsd-tools.cjs", "config-set", "a.b", "null",
             "--project-dir", "/p"],
        )
        self.assertNotIn("--raw", run.calls[0])

    def test_config_set_coercion(self):
        for value, expected in [(True, "true"), (False, "false"), (["x", "y"], '["x", "y"]'),
                                ({"k": 1}, '{"k": 1}'), ("s", "s")]:
            run = recording_run([(0, "ok", "")])
            gsd_tools.config_set(self.TOOLS, "/p", "k", value, run_fn=run)
            self.assertEqual(run.calls[0][4], expected)

    def test_config_set_failure_returns_stderr(self):
        ok, output = gsd_tools.config_set(
            self.TOOLS, "/p", "k", 1, run_fn=recording_run([(1, "", "Error: bad")])
        )
        self.assertFalse(ok)
        self.assertEqual(output, "Error: bad")

    def test_prior_value_shapes(self):
        self.assertEqual(
            gsd_tools.prior_value('{"updated": true, "key": "k", "value": 2, "previousValue": 1}'),
            (True, 1),
        )
        self.assertEqual(
            gsd_tools.prior_value('{"updated": true, "key": "k", "value": 2}'), (False, None)
        )
        self.assertIsNone(gsd_tools.prior_value("k=2"))
        self.assertIsNone(gsd_tools.prior_value("[1]"))

    def test_config_get_found(self):
        got = gsd_tools.config_get(
            self.TOOLS, "/p", "x", run_fn=recording_run([(0, '["a"]', "")])
        )
        self.assertEqual(got.found, True)
        self.assertEqual(got.value, ["a"])
        self.assertIsNone(got.error)

    def test_config_get_clean_miss_has_no_error(self):
        got = gsd_tools.config_get(
            self.TOOLS, "/p", "x",
            run_fn=recording_run([(1, "", "Error: Key not found: x")]),
        )
        self.assertEqual(got, (False, None, None))

    def test_config_get_other_failure_carries_stderr(self):
        got = gsd_tools.config_get(
            self.TOOLS, "/p", "x", run_fn=recording_run([(1, "", "boom")])
        )
        self.assertEqual(got, (False, None, "boom"))

    def test_config_get_non_json_output_names_it(self):
        got = gsd_tools.config_get(
            self.TOOLS, "/p", "x", run_fn=recording_run([(0, "not json", "")])
        )
        self.assertFalse(got.found)
        self.assertIn("not json", got.error)

    def test_config_path(self):
        run = recording_run([(0, "/p/.planning/config.json\n", "")])
        self.assertEqual(
            gsd_tools.config_path(self.TOOLS, "/p", run_fn=run), "/p/.planning/config.json"
        )
        self.assertEqual(
            run.calls[0], ["node", "/g/gsd-tools.cjs", "config-path", "--cwd", "/p"]
        )
        self.assertIsNone(
            gsd_tools.config_path(self.TOOLS, "/p", run_fn=recording_run([(1, "", "err")]))
        )

    def test_ensure_config_exists(self):
        run = recording_run([(0, "ok", "")])
        self.assertTrue(gsd_tools.ensure_config_exists(self.TOOLS, "/p", run_fn=run))
        self.assertEqual(
            run.calls[0],
            ["node", "/g/gsd-tools.cjs", "config-new-project", "--cwd", "/p", "--raw"],
        )
        self.assertFalse(
            gsd_tools.ensure_config_exists(self.TOOLS, "/p", run_fn=recording_run([(1, "", "")]))
        )


class TestRealGsdTools(unittest.TestCase):
    """Pins the real gsd-core 1.16 contract the undo log assumes, against the checkout's own
    `.claude/gsd-core` on a scratch project. gsd-tools never reads the real ~/.gsd: HOME is
    pointed at a temp dir for every subprocess."""

    _REAL_GSD_TOOLS = os.path.join(_REPO_ROOT, ".claude", "gsd-core", "bin", "gsd-tools.cjs")
    _SKIPPED_BECAUSE = (
        f"checkout-local gsd-tools.cjs not found at {_REAL_GSD_TOOLS}"
        if not os.path.isfile(_REAL_GSD_TOOLS)
        else "node not found on PATH"
        if shutil.which("node") is None
        else None
    )

    def setUp(self):
        if self._SKIPPED_BECAUSE:
            self.skipTest(self._SKIPPED_BECAUSE)
        self.project = _mkdtemp()
        self.addCleanup(shutil.rmtree, self.project, ignore_errors=True)
        self.home = _mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.tools = gsd_tools.GsdTools(shutil.which("node"), self._REAL_GSD_TOOLS)

    def _run(self, argv, **kwargs):
        env = dict(os.environ)
        env["HOME"] = self.home
        kwargs["env"] = env
        return subprocess.run(argv, **kwargs)

    def test_previous_value_contract_on_real_gsd_core(self):
        self.assertTrue(gsd_tools.ensure_config_exists(self.tools, self.project, run_fn=self._run))
        resolved = gsd_tools.config_path(self.tools, self.project, run_fn=self._run)
        self.assertIsNotNone(resolved)
        self.assertTrue(resolved.endswith(os.path.join(".planning", "config.json")))

        ok, output = gsd_tools.config_set(
            self.tools, self.project, "workflow.cross_ai_timeout", 900, run_fn=self._run
        )
        self.assertTrue(ok)
        self.assertEqual(gsd_tools.prior_value(output), (False, None))

        ok, output = gsd_tools.config_set(
            self.tools, self.project, "workflow.cross_ai_timeout", 600, run_fn=self._run
        )
        self.assertTrue(ok)
        self.assertEqual(gsd_tools.prior_value(output), (True, 900))

        ok, output = gsd_tools.config_set(
            self.tools, self.project, "workflow.cross_ai_timeout", None, run_fn=self._run
        )
        self.assertTrue(ok)
        self.assertEqual(gsd_tools.prior_value(output), (True, 600))
        got = gsd_tools.config_get(
            self.tools, self.project, "workflow.cross_ai_timeout", run_fn=self._run
        )
        self.assertEqual(got.found, False)
        self.assertIsNone(got.error)

        ok, output = gsd_tools.config_set(
            self.tools, self.project, "_ai_kit_unknown", 1, run_fn=self._run
        )
        self.assertFalse(ok)
        self.assertIn("unknown", output.lower())


if __name__ == "__main__":
    unittest.main()
