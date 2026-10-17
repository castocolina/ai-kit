"""HARD-04 (D-14/R9) end-to-end pin: a REAL child process spawned through every cross-AI
dispatcher (the runner, the custom launcher, quota.probe_reviewer_quota,
execute_dispatch.dispatch_execute, reviewer_dispatch.dispatch_reviewer) with all eleven
host-signal variables set in the parent environment sees none of them, while PATH and HOME
pass through; with no host signal set, the child sees the same names the parent had.

Real children run sys.executable on a temp env-dump script -- never a real AI CLI. The
sys.path setup below is relative to this test file's own __file__, never an absolute path."""

import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_spec import execute_dispatch, quota, reviewer_dispatch
from ai_kit_spec.detection import HOST_SIGNAL_ENV_VARS
from ai_kit_spec.runner_dispatch import (
    CustomSpec,
    RunnerSeams,
    RunnerSpec,
    run_custom_command,
    run_runner,
)

HOST_SIGNALS = sorted(HOST_SIGNAL_ENV_VARS)


def _write_env_dump_script(directory: str) -> str:
    """Writes the env-dump child script into `directory` and returns its path. The script
    writes the sorted names of its own environment as JSON to its argv[1]."""
    script = os.path.join(directory, "dump_env.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(
            "import json, os, sys\n"
            "with open(sys.argv[1], 'w', encoding='utf-8') as f:\n"
            "    f.write(json.dumps(sorted(os.environ)))\n"
        )
    return script


def _command_template(script: str, outfile: str) -> str:
    return f"{shlex.quote(sys.executable)} {shlex.quote(script)} {shlex.quote(outfile)}"


def _read_child_env_names(outfile: str) -> set:
    with open(outfile, encoding="utf-8") as f:
        return set(json.load(f))


def _dump_popen(outfile: str):
    """A Popen seam that runs the env-dump script instead of the runner's argv.

    The runner builds `node <template> ...` and feeds the prompt on stdin; this seam keeps
    every other spawn detail (the env, the session) and points the child at the dump."""
    script = os.path.join(os.path.dirname(outfile), "dump_env.py")

    def spawn(argv, **kwargs):
        del argv
        return subprocess.Popen([sys.executable, script, outfile], **kwargs)

    return spawn


def _run_all_dispatchers(script: str, tmp: str, timeout: int = 60) -> dict:
    """Runs one real child through EACH of the five dispatchers, each writing its own
    environment-name dump to its own temp file, and returns {dispatcher: name-set}."""
    results = {}
    signals = {s: "1" for s in HOST_SIGNALS}
    with unittest.mock.patch.dict(os.environ, signals):
        # 1. the runner: the one supervision core for a table runtime
        out = os.path.join(tmp, "runner.json")
        result = run_runner(
            RunnerSpec("opencode", "m", "review", timeout),
            "p",
            seams=RunnerSeams(
                which_fn=lambda _name: sys.executable,
                runner_path_fn=lambda: script,
                popen_fn=_dump_popen(out),
                print_fn=lambda *_a: None,
            ),
        )
        assert result.returncode == 0, result
        results["run_runner"] = _read_child_env_names(out)
        # 2. the custom launcher
        out = os.path.join(tmp, "custom.json")
        result = run_custom_command(
            CustomSpec("k", [sys.executable, script, out], [timeout]),
            "p",
            seams=RunnerSeams(print_fn=lambda *_a: None),
        )
        assert result.returncode == 0, result
        results["run_custom_command"] = _read_child_env_names(out)
        # 3. probe_reviewer_quota: a custom entry runs through the launcher for real
        out = os.path.join(tmp, "probe.json")
        resolved = quota.ResolvedReviewer(
            key="k", model="m", vendor="v", runtime=None,
            command=_command_template(script, out), extra={},
        )
        probe = quota.probe_reviewer_quota(resolved)
        assert probe["available"], probe
        results["probe_reviewer_quota"] = _read_child_env_names(out)
        # 4. dispatch_execute: the runner seam's Popen is what the child would get
        captured_exec = {}

        def fake_popen(argv, **kwargs):
            captured_exec["argv"] = argv
            captured_exec["kwargs"] = kwargs
            raise OSError("spawn stopped after env capture")

        result = execute_dispatch.dispatch_execute(
            execute_dispatch.ExecuteDispatchSpec(
                candidate={"runtime": "codex", "model": "m", "key": "codex/m"},
                prompt="p",
                target_dir=tmp,
                heartbeat_interval=1,
                timeout=timeout,
            ),
            seams=execute_dispatch.ExecuteSeams(
                build_tooling_guidance_fn=lambda *_a, **_kw: "",
                build_reinforcement_fn=lambda *_a, **_kw: "",
                build_soft_confinement_fn=lambda *_a, **_kw: "",
                # which_fn: the image without node must still reach the spawn.
                runner_seams=RunnerSeams(popen_fn=fake_popen, which_fn=lambda _name: "node"),
            ),
        )
        assert result["reason"] == "dispatch_unavailable", result
        assert isinstance(captured_exec["argv"], list), captured_exec["argv"]
        assert "shell" not in captured_exec["kwargs"], captured_exec["kwargs"]
        assert captured_exec["kwargs"]["start_new_session"] is True
        assert "--child-pgid-file" in captured_exec["argv"]
        assert "--child-pgid-file" not in result["command"]
        results["dispatch_execute"] = set(captured_exec["kwargs"]["env"])
        # 5. dispatch_reviewer: the same custom entry through the default launcher
        out = os.path.join(tmp, "reviewer.json")
        result = reviewer_dispatch.dispatch_reviewer(
            reviewer_dispatch.ReviewerDispatchSpec(
                reviewer_entry={
                    "key": "k", "model": "m", "vendor": "v",
                    "command": _command_template(script, out), "extra": {},
                },
                prompt="p", timeout_tiers=[timeout], tool_availability={},
            ),
            seams=reviewer_dispatch.ReviewerSeams(
                build_tooling_guidance_fn=lambda *_a, **_kw: "",
                resolve_shared_reference_fn=lambda: None,
                codegraph_health_fn=lambda _cli: False,
            ),
        )
        assert result["returncode"] == 0, result
        results["dispatch_reviewer"] = _read_child_env_names(out)
    return results


class TestHostSignalScrubAllDispatchers(unittest.TestCase):
    """R9/HARD-04 tracer: real children through all five dispatchers never see a host signal."""

    def test_signal_set_is_the_table_set(self):
        self.assertEqual(len(HOST_SIGNALS), 11)

    def test_child_sees_none_of_the_eleven_host_signals(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = _write_env_dump_script(tmp)
            results = _run_all_dispatchers(script, tmp)
        for name, child_names in results.items():
            with self.subTest(dispatcher=name):
                self.assertEqual(child_names & set(HOST_SIGNALS), set())
                self.assertIn("PATH", child_names)
                self.assertIn("HOME", child_names)

    def test_without_host_signals_child_names_match_parent(self):
        parent_names = {n for n in os.environ if n not in HOST_SIGNALS}
        with tempfile.TemporaryDirectory() as tmp:
            script = _write_env_dump_script(tmp)
            with unittest.mock.patch.dict(os.environ):
                for signal in HOST_SIGNALS:
                    os.environ.pop(signal, None)
                results = _run_all_dispatchers(script, tmp)
        for name, child_names in results.items():
            with self.subTest(dispatcher=name):
                self.assertEqual(set(), parent_names - child_names)


if __name__ == "__main__":
    unittest.main()
