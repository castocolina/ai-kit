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
import threading
import time
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
    sys.modules[spec.name] = module  # register so @dataclass can resolve cls.__module__
    spec.loader.exec_module(module)
    return module


core = load_module("precompact_core_under_test", CORE_PATH)
hook = load_module("claude_precompact_under_test", HOOK_PATH)


class HookCaseMixin(unittest.TestCase):
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
            text=not isinstance(data, bytes))

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


class TestTranscriptMatrix(HookCaseMixin, unittest.TestCase):
    """The defensive transcript read through the real hook (SPEC R2)."""

    def _precompact(self, env, transcript, session_id="sess-m"):
        base = os.path.dirname(env["HOME"])
        cwd = os.path.join(base, "proj")
        os.makedirs(cwd, exist_ok=True)
        payload = {"hook_event_name": "PreCompact", "session_id": session_id,
                   "transcript_path": transcript, "cwd": cwd, "trigger": "manual",
                   "custom_instructions": None}
        proc = self.run_hook(payload, env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "{}")
        directory = self.compact_dir(env)
        return [name for name in os.listdir(directory)
                if name.startswith(f"{session_id}-")] if os.path.isdir(directory) else []

    def test_transcript_acceptance_matrix(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        well = os.path.join(base, "well.jsonl")
        shutil.copy(str(FIXTURE_PATH), well)
        truncated = os.path.join(base, "truncated.jsonl")
        with open(truncated, "w", encoding="utf-8") as handle:
            handle.write('{"type": "user", "message": {"role": "user", "cont')
        unknown = os.path.join(base, "unknown.jsonl")
        with open(unknown, "w", encoding="utf-8") as handle:
            handle.write('{"type": "file-history-snapshot", "snapshot_id": "s"}\n')
            handle.write('{"type": "summary", "summary": "old"}\n')
        empty = os.path.join(base, "empty.jsonl")
        open(empty, "w", encoding="utf-8").close()
        missing = os.path.join(base, "missing.jsonl")
        cases = (("well", well, 1), ("truncated", truncated, 0),
                 ("unknown", unknown, 0), ("empty", empty, 0), ("missing", missing, 0))
        for name, path, files in cases:
            with self.subTest(case=name):
                env = self.make_env()
                self.assertEqual(self._precompact(env, path),
                                 ["sess-m-proj-compact.md"] if files else [])

    def _write_lines(self, base, name, lines):
        path = os.path.join(base, name)
        with open(path, "wb") as handle:
            for line in lines:
                handle.write(line)
        return path

    @staticmethod
    def _user_line(text):
        record = {"type": "user", "timestamp": "t", "session_id": "s",
                  "message": {"role": "user", "content": text}}
        return (json.dumps(record) + "\n").encode("utf-8")

    def test_transcript_boundary_on_last_line_no_file(self):
        env = self.make_env()
        base = os.path.dirname(env["HOME"])
        boundary = json.dumps({"type": "system", "subtype": "compact_boundary",
                               "timestamp": "t"}) + "\n"
        path = self._write_lines(base, "t.jsonl",
                                 [self._user_line("kept text"), boundary.encode()])
        self.assertEqual(self._precompact(env, path), [])

    def test_transcript_truncated_after_valid_uses_valid(self):
        env = self.make_env()
        base = os.path.dirname(env["HOME"])
        path = self._write_lines(base, "t.jsonl",
                                 [self._user_line("VALID-TURN-TEXT"),
                                  b'{"type": "user", "mess'])
        names = self._precompact(env, path)
        self.assertEqual(names, ["sess-m-proj-compact.md"])
        with open(os.path.join(self.compact_dir(env), names[0]),
                  encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("VALID-TURN-TEXT", text)
        self.assertIn("malformed 1", text)

    def test_transcript_invalid_utf8_line_skipped(self):
        env = self.make_env()
        base = os.path.dirname(env["HOME"])
        path = self._write_lines(base, "t.jsonl",
                                 [self._user_line("before"), b"\xff\xfe\n",
                                  self._user_line("after")])
        names = self._precompact(env, path)
        self.assertEqual(names, ["sess-m-proj-compact.md"])
        with open(os.path.join(self.compact_dir(env), names[0]),
                  encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("malformed 1", text)
        self.assertIn("after", text)

    def test_transcript_file_order_kept(self):
        env = self.make_env()
        base = os.path.dirname(env["HOME"])
        lines = []
        for index in range(4):
            record = {"type": "user", "timestamp": f"t{3 - index}",
                      "message": {"role": "user", "content": f"ORDER-{index}"}}
            lines.append((json.dumps(record) + "\n").encode("utf-8"))
        path = self._write_lines(base, "t.jsonl", lines)
        names = self._precompact(env, path)
        with open(os.path.join(self.compact_dir(env), names[0]),
                  encoding="utf-8") as handle:
            text = handle.read()
        positions = [text.index(f"ORDER-{index}") for index in range(4)]
        self.assertEqual(positions, sorted(positions))

    def test_transcript_skip_counters_match_fixture(self):
        env = self.make_env()
        base = os.path.dirname(env["HOME"])
        path = self._write_lines(
            base, "t.jsonl",
            [b"not json\n", b"not json\n", b"not json\n",
             b'{"type": "file-history-snapshot", "snapshot_id": "s"}\n',
             b'{"type": "summary", "summary": "old"}\n',
             self._user_line("the one usable turn")])
        names = self._precompact(env, path)
        with open(os.path.join(self.compact_dir(env), names[0]),
                  encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("malformed 3", text)
        self.assertIn("unknown_type 2", text)

    def test_transcript_growing_file_reads(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        path = os.path.join(base, "t.jsonl")
        with open(path, "wb") as handle:
            for index in range(3):
                handle.write(self._user_line(f"OPEN-{index}"))
        failures = []

        def grow():
            try:
                with open(path, "ab") as handle:
                    for index in range(200):
                        handle.write(self._user_line(f"APPENDED-{index}"))
                        handle.flush()
                        time.sleep(0.001)
            except (OSError, ValueError) as error:  # pragma: no cover
                failures.append(error)

        thread = threading.Thread(target=grow)
        thread.start()
        try:
            messages, _skipped = core.read_claude_transcript(path)
        finally:
            thread.join(timeout=30)
        self.assertEqual(failures, [])
        texts = "\n".join(message["text"] for message in messages)
        self.assertIn("OPEN-0", texts)
        self.assertNotIn("APPENDED-", texts)

    def test_transcript_no_boundary_whole_file_flagged(self):
        env = self.make_env()
        base = os.path.dirname(env["HOME"])
        path = self._write_lines(
            base, "t.jsonl",
            [self._user_line("first"), self._user_line("second")])
        names = self._precompact(env, path)
        with open(os.path.join(self.compact_dir(env), names[0]),
                  encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("boundary_unrecognized 1", text)
        self.assertIn("first", text)
        self.assertIn("second", text)


class TestBoundaryParity(unittest.TestCase):
    """last_boundary is a pinned copy of status-line's boundary rule (D-05)."""

    def _fixtures(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        boundary = json.dumps({"type": "system", "subtype": "compact_boundary",
                               "timestamp": "t"}) + "\n"
        user = json.dumps({"type": "user", "message": {"role": "user",
                                                       "content": "turn"}}) + "\n"
        paths = {}
        for name, count in (("two", 2), ("one", 1), ("none", 0)):
            path = os.path.join(base, f"{name}.jsonl")
            with open(path, "wb") as handle:
                for _index in range(count):
                    handle.write(user.encode("utf-8"))
                    handle.write(boundary.encode("utf-8"))
                handle.write(user.encode("utf-8"))
            paths[name] = path
        return paths

    def test_boundary_parity_with_status_line(self):
        status_line = load_module("status_line_under_test",
                                  REPO / "tools" / "status-line.py")
        for name, path in self._fixtures().items():
            with self.subTest(fixture=name):
                size = os.path.getsize(path)
                offset, count = core.last_boundary(path, size)
                since, compact_count = status_line.probe_transcript_compaction(path, size)
                self.assertEqual(count, compact_count, name)
                expected = size - offset if offset is not None else size
                self.assertEqual(expected, since, name)


class TestInjector(HookCaseMixin, unittest.TestCase):
    """The compact-SessionStart injector edges (SPEC R5)."""

    def _inject_hook(self, payload, env):
        return self.run_hook(payload, env)

    def test_inject_other_session_file_untouched(self):
        env = self.make_env()
        directory = core.private_dir(env)
        core.write_presummary(
            core.HEADER_FIRST_LINE + "\nsession_id: s-b\n---\ns-b body\n",
            "s-b", "proj", directory)
        path = os.path.join(directory, "s-b-proj-compact.md")
        proc = self._inject_hook({"hook_event_name": "SessionStart",
                                  "source": "compact", "session_id": "s-a"}, env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "{}")
        self.assertTrue(os.path.exists(path))

    def test_inject_prefix_collision(self):
        env = self.make_env()
        directory = core.private_dir(env)
        core.write_presummary(
            core.HEADER_FIRST_LINE + "\nsession_id: abc-def\n---\nbody\n",
            "abc-def", "proj", directory)
        path = os.path.join(directory, "abc-def-proj-compact.md")
        proc = self._inject_hook({"hook_event_name": "SessionStart",
                                  "source": "compact", "session_id": "abc"}, env)
        self.assertEqual(proc.stdout, "{}")
        self.assertTrue(os.path.exists(path))

    def test_inject_order(self):
        env = self.make_env()
        base = os.path.dirname(env["HOME"])
        transcript = os.path.join(base, "t.jsonl")
        shutil.copy(str(FIXTURE_PATH), transcript)
        cwd = os.path.join(base, "proj")
        os.makedirs(cwd)
        compact = {"hook_event_name": "SessionStart", "source": "compact",
                   "session_id": "sess-o"}
        proc = self.run_hook(compact, env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "{}")
        payload = {"hook_event_name": "PreCompact", "session_id": "sess-o",
                   "transcript_path": transcript, "cwd": cwd, "trigger": "manual",
                   "custom_instructions": None}
        self.run_hook(payload, env)
        proc = self.run_hook(compact, env)
        envelope = json.loads(proc.stdout)
        self.assertIn("hookSpecificOutput", envelope)
        proc = self.run_hook(compact, env)
        self.assertEqual(proc.stdout, "{}")

    def test_inject_never_partial(self):
        env = self.make_env()
        directory = core.private_dir(env)
        stop = threading.Event()

        def rewrite():
            index = 0
            while not stop.is_set():
                core.write_presummary(
                    core.HEADER_FIRST_LINE + f"\nsession_id: sess-p\n---\nbody {index}\n",
                    "sess-p", "proj", directory)
                index += 1

        thread = threading.Thread(target=rewrite)
        thread.start()
        payload = {"hook_event_name": "SessionStart", "source": "compact",
                   "session_id": "sess-p"}
        try:
            for _round in range(200):
                text = hook.inject(payload, env)
                if text is not None:
                    self.assertTrue(text.startswith(core.HEADER_FIRST_LINE))
                    self.assertIn("session_id: sess-p", text)
        finally:
            stop.set()
            thread.join(timeout=30)

    def test_inject_overcap_file_not_injected(self):
        env = self.make_env()
        directory = core.private_dir(env)
        body = "x" * (core.CAP_CHARS + 1)
        core.write_presummary(
            core.HEADER_FIRST_LINE + f"\nsession_id: sess-c\n---\n{body}\n",
            "sess-c", "proj", directory)
        proc = self.run_hook({"hook_event_name": "SessionStart", "source": "compact",
                              "session_id": "sess-c"}, env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "{}")
        names = [name for name in os.listdir(directory) if name.endswith("-compact.md")]
        self.assertEqual(names, [])


class TestHookSafety(HookCaseMixin, unittest.TestCase):
    """Session-id validation and the never-block sweep (SPEC R5, prohibitions)."""

    UNSAFE_IDS = ("../x", "a*b", "a[b", "", "x" * 129)

    def test_session_id_rejects_unsafe(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        transcript = os.path.join(base, "t.jsonl")
        shutil.copy(str(FIXTURE_PATH), transcript)
        cwd = os.path.join(base, "proj")
        os.makedirs(cwd)
        for session_id in self.UNSAFE_IDS:
            with self.subTest(session_id=session_id[:12]):
                env = self.make_env()
                payload = {"hook_event_name": "PreCompact", "session_id": session_id,
                           "transcript_path": transcript, "cwd": cwd,
                           "trigger": "manual", "custom_instructions": None}
                proc = self.run_hook(payload, env)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(proc.stdout, "{}")
                directory = self.compact_dir(env)
                self.assertFalse(os.path.isdir(directory)
                                 and os.listdir(directory),
                                 os.listdir(directory) if os.path.isdir(directory) else None)
                proc = self.run_hook({"hook_event_name": "SessionStart",
                                      "source": "compact", "session_id": session_id}, env)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(proc.stdout, "{}")

    def test_no_decision_on_any_path(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        transcript = os.path.join(base, "t.jsonl")
        shutil.copy(str(FIXTURE_PATH), transcript)
        cwd = os.path.join(base, "proj")
        os.makedirs(cwd)
        cases = [
            ("invalid_json", None, b"{not json"),
            ("empty_stdin", None, b""),
            ("stop_event", {"hook_event_name": "Stop", "session_id": "sess-n"}, None),
            ("missing_transcript", {"hook_event_name": "PreCompact",
                                    "session_id": "sess-n", "cwd": cwd,
                                    "trigger": "manual"}, None),
            ("directory_transcript", {"hook_event_name": "PreCompact",
                                      "session_id": "sess-n",
                                      "transcript_path": cwd, "cwd": cwd,
                                      "trigger": "manual"}, None),
            ("startup_source", {"hook_event_name": "SessionStart",
                                "source": "startup", "session_id": "sess-n"}, None),
            ("unsafe_session", {"hook_event_name": "SessionStart",
                                "source": "compact", "session_id": "../x"}, None),
        ]
        for name, payload, raw in cases:
            with self.subTest(case=name):
                env = self.make_env()
                proc = self.run_hook(payload, env, raw_input=raw)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                parsed = json.loads(proc.stdout)
                self.assertIsInstance(parsed, dict)
                self.assertNotIn("decision", parsed)


if __name__ == "__main__":
    unittest.main()
