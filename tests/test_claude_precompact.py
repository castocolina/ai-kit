"""Subprocess and injector tests of the Claude Code precompact route (SPEC R2, R5).

Every hook run is a real ``python3 -S tools/hooks/claude_precompact.py``
subprocess with a payload on stdin, a scratch HOME and every XDG base under a
fresh temp dir, synthetic transcripts only, and AI_KIT_PRECOMPACT_CLIENT
pointing at the stub client — no real runtime dir, client, backend or host
config is ever touched. Reader-only and injector stress cases load the modules
by path and call them in-process.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO / "tools" / "hooks" / "claude_precompact.py"
CORE_PATH = REPO / "tools" / "hooks" / "precompact_core.py"
STUB_PATH = REPO / "tests" / "fixtures" / "precompact" / "stub_client.py"
FIXTURE_PATH = REPO / "tests" / "fixtures" / "precompact" / "transcript_two_boundaries.jsonl"


def load_module(name, path):
    """A module loaded by path (status-line is unimportable by name)."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = load_module("precompact_core_under_test", CORE_PATH)


class HookCaseMixin:
    """Scratch env + subprocess runner for the Claude hook."""

    def make_env(self, tmp=None, **extra):
        base = tmp or tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        paths = {
            "HOME": os.path.join(base, "home"),
            "XDG_RUNTIME_DIR": os.path.join(base, "run"),
            "XDG_CACHE_HOME": os.path.join(base, "cache"),
            "XDG_CONFIG_HOME": os.path.join(base, "config"),
            "XDG_STATE_HOME": os.path.join(base, "state"),
        }
        for path in paths.values():
            os.makedirs(path, exist_ok=True)
        os.chmod(paths["XDG_RUNTIME_DIR"], 0o700)
        env = dict(paths)
        env["AI_KIT_PRECOMPACT_CLIENT"] = str(STUB_PATH)
        env.update(extra)
        return env

    def run_hook(self, payload, env, raw_input=None):
        """One hook run; returns the CompletedProcess."""
        data = raw_input if raw_input is not None else json.dumps(payload)
        return subprocess.run(
            [sys.executable, "-S", str(HOOK_PATH)],
            input=data, capture_output=True, check=False, env=env, timeout=60,
            text=True)

    def compact_dir(self, env):
        return os.path.join(env["XDG_RUNTIME_DIR"], "ai-kit", "compact")

    def read_stub_log(self, env):
        path = env.get("STUB_LOG")
        if not path or not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]


class TestTracerPrecompactThenInject(HookCaseMixin, unittest.TestCase):
    """Task 1 tracer: PreCompact prepares, compact SessionStart injects and deletes."""

    def test_tracer_precompact_then_inject(self):
        env = self.make_env()
        base = os.path.dirname(env["HOME"])
        env["STUB_LOG"] = os.path.join(base, "stub.log")

        transcript = os.path.join(base, "transcript.jsonl")
        shutil.copy(str(FIXTURE_PATH), transcript)
        cwd = os.path.join(base, "My Project")
        os.makedirs(cwd)
        payload = {"hook_event_name": "PreCompact", "session_id": "sess-1",
                   "transcript_path": transcript, "cwd": cwd, "trigger": "manual",
                   "custom_instructions": None}
        proc = self.run_hook(payload, env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "{}")
        self.assertNotIn("decision", proc.stdout)

        directory = self.compact_dir(env)
        names = os.listdir(directory)
        self.assertEqual(names, ["sess-1-My-Project-compact.md"], names)
        path = os.path.join(directory, names[0])
        self.assertEqual(stat_mode(path), 0o600)
        self.assertEqual(stat_mode(directory), 0o700)
        self.assertFalse(path.startswith(cwd + os.sep))
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        lines = text.splitlines()
        self.assertEqual(lines[0], core.HEADER_FIRST_LINE)
        self.assertEqual(lines[1], "session_id: sess-1")
        self.assertIn("skipped: malformed 0, unknown_type 2, boundary_unrecognized 0, "
                      "dropped_before_classify 0", lines)

        # Only the active part after boundary 2, with the deterministic pre-pass.
        for needle in ("USER-REQUEST-TEXT", "ASSISTANT-PLAN-TEXT", "IMAGE-TURN-TEXT",
                       "Read", "Bash", "RESULT-LINE-05", "RESULT-BLOCK-TEXT-A"):
            self.assertIn(needle, text)
        self.assertNotIn("RESULT-LINE-06", text)
        for banned in ("OLD-SEGMENT", "SECRET-REMINDER", "THINKING-TEXT", "IMAGEDATA",
                       "BEFORE-SEGMENT-ONE"):
            self.assertNotIn(banned, text)

        calls = self.read_stub_log(env)
        self.assertGreaterEqual(len(calls), 2, calls)
        self.assertEqual(calls[0]["argv"], ["--probe"])
        for call in calls[1:]:
            self.assertEqual(call["env"].get("JEV_BACKEND"), "laya")
        for call in calls:
            self.assertEqual(call["env"].get("GSD_PATH_JEV"), "1")
            self.assertEqual(call["env"].get("JEV_CALLER"), "ai-kit-precompact")
            self.assertNotIn("JEV_ALLOW_REMOTE", call["env"])
            self.assertTrue(call["env"].get("XDG_CONFIG_HOME", "").endswith(".no-config"))

        # The compact SessionStart injects the file text and deletes the file.
        start_payload = {"hook_event_name": "SessionStart", "source": "compact",
                         "session_id": "sess-1"}
        proc = self.run_hook(start_payload, env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(os.path.exists(path))
        envelope = json.loads(proc.stdout)
        self.assertNotIn("decision", envelope)
        output = envelope["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "SessionStart")
        self.assertEqual(output["additionalContext"], text)


def stat_mode(path):
    """The permission bits of a path."""
    return os.stat(path).st_mode & 0o777


class TestSharedStdinReader(HookCaseMixin, unittest.TestCase):
    """The read_stdin extraction: no side effects, a real limit ceiling."""

    def test_session_start_import_has_no_side_effects(self):
        env = self.make_env()
        code = (f"import sys; sys.path.insert(0, {str(HOOK_PATH.parent)!r}); "
                "import claude_session_start")
        proc = subprocess.run([sys.executable, "-S", "-c", code], capture_output=True,
                              check=False, env=env, stdin=subprocess.DEVNULL, timeout=30,
                              text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(proc.stderr, "")

    def test_read_stdin_over_one_mib(self):
        env = self.make_env()
        code = (
            f"import sys; sys.path.insert(0, {str(HOOK_PATH.parent)!r}); "
            "import claude_session_start as m\n"
            "limit = None if sys.argv[1] == 'default' else int(sys.argv[1])\n"
            "data = m.read_stdin() if limit is None else m.read_stdin(limit)\n"
            "sys.stdout.write(str(len(data)))\n")
        payload = "x" * (2 * 1024 * 1024 + 512 * 1024)
        self.assertEqual(len(payload), 2621440)
        proc = subprocess.run([sys.executable, "-S", "-c", code, str(4 * 1024 * 1024)],
                              input=payload, capture_output=True, check=False, env=env,
                              timeout=60, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "2621440")
        proc = subprocess.run([sys.executable, "-S", "-c", code, "default"],
                              input=payload, capture_output=True, check=False, env=env,
                              timeout=60, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        read = int(proc.stdout)
        self.assertGreater(read, 1024 * 1024)
        self.assertLessEqual(read, 1024 * 1024 + 65536)


if __name__ == "__main__":
    unittest.main()
