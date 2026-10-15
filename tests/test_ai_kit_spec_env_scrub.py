"""HARD-04 (D-14/R9) end-to-end pin: a REAL child process spawned through every cross-AI
dispatcher (dispatch_with_heartbeat, dispatch_with_polling, quota.probe_reviewer_quota,
execute_dispatch.dispatch_execute, reviewer_dispatch.dispatch_reviewer) with all eleven
host-signal variables set in the parent environment sees none of them, while PATH and HOME
pass through; with no host signal set, the child sees the same names the parent had.

Real children run sys.executable on a temp env-dump script -- never a real AI CLI. The
sys.path setup below is relative to this test file's own __file__, never an absolute path."""
import json
import os
import shlex
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_spec import dispatch, execute_dispatch, quota, reviewer_dispatch

HOST_SIGNALS = [
    "AI_AGENT", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SSE_PORT", "OPENCODE",
    "CURSOR_AGENT", "PI_CODING_AGENT", "CODEX_THREAD_ID", "CODEX_SANDBOX", "GROK_AGENT",
    "CODEX_VERSION",
]


def _write_env_dump_script(directory: str) -> str:
    """Writes the env-dump child script into `directory` and returns its path. The script
    writes the sorted names of its own environment as JSON to its argv[1]."""
    script = os.path.join(directory, "dump_env.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write("import json, os, sys\n"
                "with open(sys.argv[1], 'w', encoding='utf-8') as f:\n"
                "    f.write(json.dumps(sorted(os.environ)))\n")
    return script


def _command_template(script: str, outfile: str) -> str:
    return f"{shlex.quote(sys.executable)} {shlex.quote(script)} {shlex.quote(outfile)}"


def _read_child_env_names(outfile: str) -> set:
    with open(outfile, encoding="utf-8") as f:
        return set(json.load(f))


def _run_all_dispatchers(script: str, tmp: str, timeout: int = 60) -> dict:
    """Runs one real child through EACH of the five dispatchers, each writing its own
    environment-name dump to its own temp file, and returns {dispatcher: name-set}."""
    results = {}
    signals = {s: "1" for s in HOST_SIGNALS}
    with unittest.mock.patch.dict(os.environ, signals):
        # 1. dispatch_with_heartbeat
        out = os.path.join(tmp, "heartbeat.json")
        result = dispatch.dispatch_with_heartbeat(
            shlex.split(_command_template(script, out)), "p", heartbeat_interval=1,
            timeout=timeout, print_fn=lambda *_a: None)
        assert result["returncode"] == 0, result
        results["dispatch_with_heartbeat"] = _read_child_env_names(out)
        # 2. dispatch_with_polling
        out = os.path.join(tmp, "polling.json")
        result = dispatch.dispatch_with_polling(
            [sys.executable, script, out], "p", timeout_tiers=[timeout],
            print_fn=lambda *_a: None)
        assert result["returncode"] == 0, result
        results["dispatch_with_polling"] = _read_child_env_names(out)
        # 3. probe_reviewer_quota (real subprocess.run via its default run_fn)
        out = os.path.join(tmp, "probe.json")
        resolved = quota.ResolvedReviewer(key="k", model="m", vendor="v", cli="codex",
                                          command=_command_template(script, out), extra={})
        probe = quota.probe_reviewer_quota(resolved)
        assert probe["available"], probe
        results["probe_reviewer_quota"] = _read_child_env_names(out)
        # 4. dispatch_execute (real child via its default dispatch_fn)
        out = os.path.join(tmp, "execute.json")
        execute_dispatch.dispatch_execute(
            {"cli": "codex", "model": "m", "key": "codex/m"}, "p", tmp, 1, timeout,
            build_execute_command_fn=lambda _cli, **_kw: _command_template(script, out),
            build_tooling_guidance_fn=lambda *_a, **_kw: "",
            build_reinforcement_fn=lambda *_a, **_kw: "",
            build_soft_confinement_fn=lambda *_a, **_kw: "")
        results["dispatch_execute"] = _read_child_env_names(out)
        # 5. dispatch_reviewer (cli None: no codegraph health probe, command template is ours)
        out = os.path.join(tmp, "reviewer.json")
        result = reviewer_dispatch.dispatch_reviewer(
            {"key": "k", "model": "m", "vendor": "v", "cli": None,
             "command": _command_template(script, out), "extra": {}},
            "p", timeout_tiers=[timeout], tool_availability={},
            dispatch_fn=dispatch.dispatch_with_polling,
            build_tooling_guidance_fn=lambda *_a, **_kw: "",
            resolve_shared_reference_fn=lambda: None,
            codegraph_health_fn=lambda _cli: False)
        assert result["returncode"] == 0, result
        results["dispatch_reviewer"] = _read_child_env_names(out)
    return results


class TestHostSignalScrubAllDispatchers(unittest.TestCase):
    """R9/HARD-04 tracer: real children through all five dispatchers never see a host signal."""

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
