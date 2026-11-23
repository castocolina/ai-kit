"""36 D-19 / SPEC R12 f, executable part: the write-path commands print and write the same
bytes with and without a herdr signal and never call herdr. The question flow is skill text,
pinned elsewhere.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import capability_block, cli, herdr_source
from ai_kit_spec.detection import RUNTIMES_SCHEMA_VERSION
from ai_kit_spec.model_catalog import CATALOG_SCHEMA_VERSION
from ai_kit_spec.runner_dispatch import RunnerResult

from tests.herdr_fakes import herdr_calls, write_herdr_fake

# herdr-names is left out on purpose: it is the catalog step that opens a herdr pane
# after telling the owner.
WRITE_PATH_COMMANDS = ("config-status", "render-toml", "propose-lanes", "check-reviewer")
CONFIG = {
    "policy": {"mode": "single", "review": {"ladder": ["review-a"]},
               "execute": {"ladder": ["exec-free", "exec-b"]}},
    "lanes": [
        {"key": "review-a", "runtime": "codex", "model": "placeholder-model-1",
         "purpose": "review"},
        {"key": "exec-free", "runtime": "opencode", "model": "fake/placeholder-model-3",
         "purpose": "execute", "usage_limited": True, "usage_limit_note": "a daily cap",
         "pool": "fake:free", "data_use": "may_be_kept_or_trained",
         "data_use_line": "The provider's page says prompts may be kept.",
         "data_use_source": "https://example.com/data-use", "data_use_read": "2000-01-02",
         "data_use_label": "reported", "data_use_confirmed": True},
        {"key": "exec-b", "runtime": "codex", "model": "placeholder-model-4",
         "purpose": "execute"},
    ],
}
CATALOG = {"_meta": {"schema_version": CATALOG_SCHEMA_VERSION},
           "fake/placeholder-model-1": {"provider": "fake", "runtimes": {
               "codex": {"model_id": "placeholder-model-1"}}, "source": {},
               "confidence": "low", "last_verified": "2000-01-01"}}
SNAPSHOT = {"schema_version": RUNTIMES_SCHEMA_VERSION, "clis": {
    "codex": {"installed": True, "listing": "ok", "models": ["placeholder-model-1"]}}}


def _fake_runner(_spec, _prompt, _seams):
    return RunnerResult(0, "Hello world!", {"status": "ok"}, None, False, [], "")


def _fake_preview(_spec, *_args, **_kwargs):
    """The effort probe's --print-argv step, stubbed: under this test's scratch HOME the Volta
    `node` shim on PATH cannot find its toolchain and re-runs `node` from PATH (itself) without
    end."""
    return ["cross-ai: setting effort=high applied"]


class TestHerdrIdentity(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.bin_dir = self.root / "bin"
        self.log = self.root / "herdr.log"
        self.fake = write_herdr_fake(self.bin_dir, {}, self.log)
        self.base_path = os.environ.get("PATH", "")
        self.work = self.root / "work"

    def _env(self, herdr: bool) -> dict:
        env = {"PATH": str(self.bin_dir) + os.pathsep + self.base_path,
               "HOME": str(self.work / "home"), "XDG_CONFIG_HOME": str(self.work / "xdg"),
               "XDG_CACHE_HOME": str(self.work / "cache"), "AI_KIT_REFUSE_REAL_HOME": "1"}
        if herdr:
            env["HERDR_ENV"] = "1"
        if "TMPDIR" in os.environ:
            env["TMPDIR"] = os.environ["TMPDIR"]
        return env

    def _session(self, env) -> tuple:
        project = self.work / "project"
        project.mkdir(parents=True)
        for name, value in (("lanes", CONFIG), ("catalog", CATALOG), ("runtimes", SNAPSHOT)):
            (self.work / f"{name}.json").write_text(json.dumps(value), encoding="utf-8")
        target = project / ".aikit" / "config.toml"
        calls = [
            ["config-status", "--cwd", str(project)],
            ["render-toml", "--json-config", str(self.work / "lanes.json"), "--out", str(target)],
            ["config-status", "--cwd", str(project)],
            ["propose-lanes", "--purpose", "review", "--catalog-path",
             str(self.work / "catalog.json"), "--runtimes-json", str(self.work / "runtimes.json")],
            ["check-reviewer", "--key", "review-a", "--runtime", "codex", "--model",
             "placeholder-model-1"],
            ["check-reviewer", "--key", "review-a", "--runtime", "codex", "--model",
             "placeholder-model-1", "--effort", "high"],
        ]
        runs = []
        for argv in calls:
            out, err = io.StringIO(), io.StringIO()
            with (mock.patch.dict(os.environ, env, clear=True),
                  mock.patch("time.time", return_value=1000.0),
                  mock.patch("ai_kit_spec.effort_probe.print_argv_lines", _fake_preview),
                  mock.patch.object(capability_block, "DEFAULT_SEAMS",
                                    capability_block.ComposeSeams(print_argv_fn=lambda *_a: None)),
                  redirect_stdout(out), redirect_stderr(err)):
                code = cli.main(argv, env_fn=lambda: dict(env), runner_fn=_fake_runner)
            runs.append((argv[0], code, out.getvalue(), err.getvalue()))
        config_bytes = target.read_bytes()
        shutil.rmtree(self.work)
        return runs, config_bytes

    def test_write_path_is_identical_with_and_without_herdr(self):
        plain = self._session(self._env(False))
        hosted = self._session(self._env(True))
        self.assertEqual(plain, hosted)
        self.assertTrue(herdr_calls(self.log) == [])
        runs, config_bytes = plain
        for run in runs:
            self.assertEqual(run[1], 0, run)
        self.assertEqual(runs[0][2].splitlines()[0], "none")
        self.assertEqual(runs[2][2].splitlines()[0], "active")
        self.assertIn(b"[lanes.policy.execute]", config_bytes)
        self.assertIn(b"usage_limited = true", config_bytes)

    def test_herdr_signal_is_real(self):
        self.assertEqual(herdr_source.herdr_available(self._env(True))[0], str(self.fake))
        self.assertIsNone(herdr_source.herdr_available(self._env(False))[0])

    def test_fake_herdr_logs_every_call(self):
        result = subprocess.run([str(self.fake), "pane", "list"], capture_output=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(herdr_calls(self.log), [["pane", "list"]])

    def test_herdr_names_is_the_named_exception(self):
        self.assertNotIn("herdr-names", WRITE_PATH_COMMANDS)
        runs, _ = self._session(self._env(False))
        self.assertEqual({run[0] for run in runs}, set(WRITE_PATH_COMMANDS))


if __name__ == "__main__":
    unittest.main()
