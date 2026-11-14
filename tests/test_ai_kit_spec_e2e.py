"""Real gsd-core runs for ai-kit-spec-review: the e2e tier
(C-IN-06). Each class spawns real `node` against this checkout's own `.claude/gsd-core` on a
scratch project with a temp HOME, and skips when node or that gsd-core is missing."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import gsd_tools


def _scratch_project(parent=None):
    """A temp project that owns its `.planning/`: gsd-tools' project-root lookup stops at the
    first `.planning/` it meets, so without one a temp dir inside a checkout (TMPDIR in the repo)
    resolves to that checkout's real `.planning/config.json`."""
    project = tempfile.mkdtemp(dir=parent)
    os.mkdir(os.path.join(project, ".planning"))
    return project


def _assert_inside(test, path, root):
    """Fails before any write when gsd-tools resolved a config outside the test's temp root."""
    real, top = os.path.realpath(path), os.path.realpath(root)
    test.assertTrue(real.startswith(top + os.sep), f"config resolved outside {top}: {real}")


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
        self.project = _scratch_project()
        self.addCleanup(shutil.rmtree, self.project, ignore_errors=True)
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        node = shutil.which("node")
        assert node is not None
        self.tools = gsd_tools.GsdTools(node, self._REAL_GSD_TOOLS)

    def _run(self, argv, **kwargs):
        env = dict(os.environ)
        env["HOME"] = self.home
        kwargs["env"] = env
        return subprocess.run(argv, **kwargs)

    def test_previous_value_contract_on_real_gsd_core(self):
        self.assertTrue(gsd_tools.ensure_config_exists(self.tools, self.project, run_fn=self._run))
        resolved = gsd_tools.config_path(self.tools, self.project, run_fn=self._run)
        assert resolved is not None
        _assert_inside(self, resolved, self.project)
        self.assertTrue(resolved.endswith(os.path.join(".planning", "config.json")))

        ok, output = gsd_tools.config_set(
            self.tools, self.project, "workflow.cross_ai_timeout", 900, run_fn=self._run
        )
        self.assertTrue(ok)

        ok, output = gsd_tools.config_set(
            self.tools, self.project, "workflow.cross_ai_timeout", 600, run_fn=self._run
        )
        self.assertTrue(ok)

        ok, output = gsd_tools.config_set(
            self.tools, self.project, "workflow.cross_ai_timeout", None, run_fn=self._run
        )
        self.assertTrue(ok)
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

    def test_a_folder_nested_in_another_project_becomes_its_own_project(self):
        """An empty folder inside another GSD project becomes its own project; the outer project
        is never written. The outer folder is its own git repository, so gsd-core stops there
        wherever the temp dir lives."""
        outer = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outer, ignore_errors=True)
        self._run(["git", "init", "-q", outer], check=True, capture_output=True, timeout=60)
        os.mkdir(os.path.join(outer, ".planning"))
        outer_cfg = os.path.join(outer, ".planning", "config.json")
        with open(outer_cfg, "w", encoding="utf-8") as f:
            json.dump({"model_profile": "quality"}, f)
        with open(outer_cfg, "rb") as f:
            outer_bytes = f.read()
        outer_listing = sorted(os.listdir(os.path.join(outer, ".planning")))
        inner = os.path.join(outer, "inner")
        os.mkdir(inner)
        # Stops before any write when gsd-core walks past the synthetic outer project.
        probe = gsd_tools.config_path(self.tools, inner, run_fn=self._run)
        assert probe is not None
        _assert_inside(self, probe, outer)
        self.assertTrue(gsd_tools.ensure_config_exists(self.tools, inner, run_fn=self._run))
        self.assertTrue(os.path.isfile(os.path.join(inner, ".planning", "config.json")))
        resolved = gsd_tools.config_path(self.tools, inner, run_fn=self._run)
        assert resolved is not None
        _assert_inside(self, resolved, inner)
        with open(outer_cfg, "rb") as f:
            self.assertEqual(f.read(), outer_bytes)
        self.assertEqual(sorted(os.listdir(os.path.join(outer, ".planning"))), outer_listing)

class TestRealGsdConfigSet(unittest.TestCase):
    """The one real gsd-tools run: against this checkout's own .claude/gsd-core on a scratch
    project, HOME pointed at a temp dir. Skipped when gsd-core or node is missing."""

    _TOOLS = os.path.join(os.path.dirname(__file__), "..", ".claude", "gsd-core", "bin",
                          "gsd-tools.cjs")

    @unittest.skipUnless(os.path.exists(_TOOLS), "checkout has no .claude/gsd-core install")
    @unittest.skipUnless(shutil.which("node"), "node not on PATH")
    def test_write_workflow_keys_round_trip_through_real_gsd_core(self):
        import json
        import subprocess
        import tempfile

        from ai_kit_spec import gsd_tools as gt
        node = shutil.which("node")
        assert node is not None
        tools = gt.GsdTools(node_bin=node, gsd_tools_path=os.path.abspath(self._TOOLS))
        scratch = _scratch_project()
        self.addCleanup(shutil.rmtree, scratch, ignore_errors=True)
        with (tempfile.TemporaryDirectory() as home,
              mock.patch.dict(os.environ, {"HOME": home})):
                self.assertTrue(gt.ensure_config_exists(tools, scratch, run_fn=subprocess.run))
                resolved = gt.config_path(tools, scratch, run_fn=subprocess.run)
                assert resolved is not None
                _assert_inside(self, resolved, scratch)
                config_json = os.path.join(scratch, ".planning", "config.json")
                ok, _output = gt.config_set(tools, scratch, "workflow.cross_ai_execution", True,
                                            run_fn=subprocess.run)
                self.assertTrue(ok)
                got = gt.config_get(tools, scratch, "workflow.cross_ai_execution",
                                    run_fn=subprocess.run)
                self.assertTrue(got.found)
                self.assertIs(got.value, True)
                # The config.json on disk was written by gsd-tools' config-set.
                self.assertTrue(os.path.exists(config_json))
                with open(config_json, encoding="utf-8") as f:
                    on_disk = json.load(f)
                self.assertIs(on_disk["workflow"]["cross_ai_execution"], True)


class TestRealGsdRunsStayInTheirTempRoot(unittest.TestCase):
    """Guard: reruns every real gsd-tools case above with TMPDIR inside this checkout, the setup
    that once let a scratch run write the repo's own `.planning/config.json` plus a `.bak`."""

    _CASES = ("tests.test_ai_kit_spec_e2e.TestRealGsdTools",
              "tests.test_ai_kit_spec_e2e.TestRealGsdConfigSet")

    # Each case's _assert_inside fails before its first write, so a pass here means no case
    # resolved a config outside its temp root (tests never read the real .planning/ itself).
    @unittest.skipUnless(os.path.isfile(TestRealGsdTools._REAL_GSD_TOOLS), "no checkout gsd-core")
    @unittest.skipUnless(shutil.which("node"), "node not on PATH")
    def test_real_gsd_cases_pass_with_tmpdir_inside_the_checkout(self):
        parent = os.path.join(_REPO_ROOT, "tmp")
        os.makedirs(parent, exist_ok=True)
        inner_tmp = tempfile.mkdtemp(prefix="hermetic-guard-", dir=parent)
        self.addCleanup(shutil.rmtree, inner_tmp, ignore_errors=True)
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", *self._CASES],
            cwd=_REPO_ROOT, env={**os.environ, "TMPDIR": inner_tmp},
            capture_output=True, text=True, timeout=120, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        self.assertNotIn("skipped=", proc.stderr)


if __name__ == "__main__":
    unittest.main()
