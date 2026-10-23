"""Real gsd-core runs for ai-kit-spec-review and ai-kit-spec-execute-gsd: the e2e tier
(C-IN-06). Each class spawns real `node` against this checkout's own `.claude/gsd-core` on a
scratch project with a temp HOME, and skips when node or that gsd-core is missing."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-execute-gsd"))

from ai_kit_spec import gsd_tools
from ai_kit_spec_gsd import cli


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
        self.project = tempfile.mkdtemp()
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

class TestRealGsdConfigSet(unittest.TestCase):
    """The one real gsd-tools run: against this checkout's own .claude/gsd-core on a scratch
    project, HOME pointed at a temp dir. Skipped when gsd-core or node is missing."""

    _TOOLS = os.path.join(os.path.dirname(__file__), "..", ".claude", "gsd-core", "bin",
                          "gsd-tools.cjs")

    @unittest.skipUnless(os.path.exists(_TOOLS), "checkout has no .claude/gsd-core install")
    @unittest.skipUnless(shutil.which("node"), "node not on PATH")
    def test_write_workflow_keys_round_trip_through_real_gsd_core(self):
        import io
        import json
        import subprocess
        import tempfile

        from ai_kit_spec import gsd_tools as gt
        node = shutil.which("node")
        assert node is not None
        tools = gt.GsdTools(node_bin=node, gsd_tools_path=os.path.abspath(self._TOOLS))
        with (tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as scratch,
              mock.patch.dict(os.environ, {"HOME": home})):
                self.assertTrue(gt.ensure_config_exists(tools, scratch, run_fn=subprocess.run))
                config_json = os.path.join(scratch, ".planning", "config.json")
                stdout = io.StringIO()
                code = cli.main(["write-workflow-keys", "--cwd", scratch, "--run-id", "r1",
                                 "--set", "cross_ai_execution=true"],
                                resolve_gsd_tools_fn=lambda start: tools.gsd_tools_path,
                                stdout=stdout)
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(stdout.getvalue())["applied"],
                                 ["workflow.cross_ai_execution"])
                got = gt.config_get(tools, scratch, "workflow.cross_ai_execution",
                                    run_fn=subprocess.run)
                self.assertTrue(got.found)
                self.assertIs(got.value, True)
                # The config.json on disk was written by gsd-tools, not by ai-kit: gsd-tools'
                # config-new-project created it, and ai-kit only ever opened it read-only.
                self.assertTrue(os.path.exists(config_json))
                with open(config_json, encoding="utf-8") as f:
                    on_disk = json.load(f)
                self.assertIs(on_disk["workflow"]["cross_ai_execution"], True)

if __name__ == "__main__":
    unittest.main()
