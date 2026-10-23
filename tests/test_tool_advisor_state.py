"""Locked state and PostToolUse reminder tests for the shared advisor core."""
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "tools" / "hooks"
sys.path.insert(0, str(HOOKS))


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HOOKS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = _load("advisor_state_core", "advisor_core.py")
precompact = _load("advisor_state_precompact", "precompact_core.py")
TOOLS = {"rg", "bat", "fd", "sd"}


class AdvisorStateTests(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="advisor-state-")
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
        self.env = {"HOME": os.path.join(self.base, "home"),
                    "XDG_RUNTIME_DIR": os.path.join(self.base, "runtime"),
                    "XDG_CACHE_HOME": os.path.join(self.base, "cache"),
                    "PATH": os.environ.get("PATH", "")}
        for path in (self.env["HOME"], self.env["XDG_RUNTIME_DIR"], self.env["XDG_CACHE_HOME"]):
            os.makedirs(path, mode=0o700)
            os.chmod(path, 0o700)
        self.tools = dict(self.env)
        self._installed_patch = mock.patch.object(
            core, "installed_tools", side_effect=lambda env: TOOLS if env.get("PATH") else set())
        self._installed_patch.start()
        self.addCleanup(self._installed_patch.stop)

    def event(self, kind="advisor", session="s-a", call_id: str | None = "c1", output_lines=0,
              output_chars=0, command="grep -rn x .", single_block=False):
        return {"kind": kind, "tool": "bash", "command": command, "session_id": session,
                "call_id": call_id, "output_lines": output_lines,
                "output_chars": output_chars, "single_block": single_block}

    def advise(self, event):
        return core.advise(event, self.tools)

    def state(self, session="s-a"):
        path = Path(self.env["XDG_RUNTIME_DIR"]) / "ai-kit" / "advisor" / f"{session}.json"
        return json.loads(path.read_text())

    def test_frequency_first_then_every_tenth(self):
        shown = [i for i in range(1, 26)
                 if self.advise(self.event(session="s-a", call_id=f"t{i}"))]
        self.assertEqual(shown, [1, 11, 21])
        shown_b = [i for i in range(1, 12)
                   if self.advise(self.event(session="s-b", call_id=f"b{i}"))]
        self.assertEqual(shown_b, [1, 11])
        shown_c = [i for i in range(1, 26)
                   if self.advise(self.event(session="s-c", call_id=None))]
        self.assertEqual(shown_c, [1, 11, 21])
        self.assertNotIn("SECRET-TOKEN", (Path(self.env["XDG_RUNTIME_DIR"])
                                           / "ai-kit/advisor/s-a.json").read_text())

    def test_corrupt_state_is_first(self):
        directory = Path(precompact.private_dir(self.env, name="advisor"))
        seeds = ["{not json", json.dumps({"session": "s-a", "counts": {"grep": "bad"},
                                           "calls": {"k": 3}})]
        for seed in seeds:
            with self.subTest(seed=seed):
                (directory / "s-a.json").write_text(seed)
                self.assertIsNotNone(self.advise(self.event(call_id="fresh")))
                state = json.loads((directory / "s-a.json").read_text())
                self.assertEqual(state["session"], "s-a")
                self.assertEqual(state["counts"]["grep"], 1)

    def test_state_params_and_mode(self):
        self.assertTrue(precompact.private_dir(self.env).endswith("ai-kit/compact"))
        directory = precompact.private_dir(self.env, name="advisor")
        self.advise(self.event())
        state_path = os.path.join(directory, "s-a.json")
        self.assertEqual(os.stat(directory).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(state_path).st_mode & 0o777, 0o600)
        old, new = os.path.join(directory, "old.json"), os.path.join(directory, "new.json")
        for path in (old, new, os.path.join(directory, "notes.txt"),
                     os.path.join(directory, ".advisor.lock")):
            Path(path).touch()
        old_time = time_now() - 25 * 3600
        new_time = time_now() - 23 * 3600
        os.utime(old, (old_time, old_time))
        os.utime(new, (new_time, new_time))
        precompact.sweep(directory, patterns=core.STATE_PATTERNS)
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.exists(new))
        self.assertTrue(os.path.exists(os.path.join(directory, ".advisor.lock")))
        self.assertTrue(os.path.exists(os.path.join(directory, "notes.txt")))

    def test_state_concurrent_processes(self):
        source = f'''import os, sys
sys.path.insert(0, {str(HOOKS)!r})
import advisor_core
advisor_core.installed_tools = lambda _env: {{"rg"}}
env = {{key: os.environ[key] for key in ("HOME", "XDG_RUNTIME_DIR", "XDG_CACHE_HOME")}}
for index in range(50):
    event = {{"kind": "advisor", "tool": "bash", "command": "grep x .",
             "session_id": "parallel", "call_id": sys.argv[1] + str(index)}}
    print(int(bool(advisor_core.advise(event, env))))
'''
        env = dict(os.environ, **self.env)
        children = [subprocess.Popen([sys.executable, "-S", "-c", source, f"p{n}-"],
                                     env=env, stdout=subprocess.PIPE, text=True)
                    for n in range(2)]
        results = []
        for child in children:
            output, _ = child.communicate(timeout=30)
            self.assertEqual(child.returncode, 0)
            results.extend(int(line) for line in output.splitlines())
        self.assertEqual(sum(results), 10)
        self.assertEqual(self.state("parallel")["counts"]["grep"], 100)

    def test_reminder_after_advised_small_output_silent(self):
        self.assertIsNotNone(self.advise(self.event(call_id="same")))
        self.assertIsNone(self.advise(self.event("reminder", call_id="same", output_lines=20,
                                                output_chars=100)))

    def test_reminder_big_output_reminds(self):
        self.advise(self.event(call_id="same"))
        line = self.advise(self.event("reminder", call_id="same", output_lines=500,
                                     output_chars=2000))
        self.assertTrue(line.startswith("ai-kit reminder: "))
        self.assertIn("printed 500 lines, about", line)
        self.assertIn("rg", line)
        self.assertIn("grep", line)

    def test_reminder_silent_cases(self):
        cases = [(self.event("reminder", command="rg x", output_lines=500, call_id="a"),
                  self.tools),
                 (self.event("reminder", output_lines=500, call_id="b"), {"PATH": ""}),
                 (self.event("reminder", output_lines=0, call_id="c"), self.tools),
                 ({**self.event("reminder", call_id="d"), "tool": "read"}, self.tools)]
        for event, tools in cases:
            with self.subTest(event=event):
                self.assertIsNone(core.advise(event, tools))

    def test_single_block_event_never_doubles(self):
        for order in ("advisor-first", "reminder-first"):
            with self.subTest(order=order):
                session = "single-" + order
                advisor = self.event(session=session, call_id="single", single_block=True)
                reminder = self.event("reminder", session=session, call_id="single",
                                      output_lines=500, output_chars=2000, single_block=True)
                results = [self.advise(item) for item in
                           ((advisor, reminder) if order == "advisor-first" else
                            (reminder, advisor))]
                self.assertEqual(sum(bool(item) for item in results), 1)
        advisor = self.event(session="claude", call_id="claude")
        reminder = self.event("reminder", session="claude", call_id="claude", output_lines=500,
                              output_chars=2000)
        self.assertTrue(self.advise(advisor))
        self.assertTrue(self.advise(reminder))

    def test_single_block_cadence_both_orders(self):
        for order in ("advisor-first", "reminder-first"):
            with self.subTest(order=order):
                session = "cadence-" + order
                for i in range(1, 26):
                    advisor = self.event(session=session, call_id=f"{order}{i}", single_block=True)
                    reminder = self.event("reminder", session=session, call_id=f"{order}{i}",
                                          output_lines=500, output_chars=2000,
                                          single_block=True)
                    pair = (advisor, reminder) if order == "advisor-first" else (reminder, advisor)
                    results = [self.advise(item) for item in pair]
                    self.assertEqual(any(results), i in (1, 11, 21))
                    self.assertFalse(all(results))
                state = self.state(session)
                self.assertEqual(state["counts"]["grep"], 25)
                self.assertEqual(state["counts"]["big:grep"], 25)

    def test_reminder_after_throttled_call_silent(self):
        self.advise(self.event(call_id="one"))
        self.assertIsNone(self.advise(self.event(call_id="two")))
        self.assertIsNone(self.advise(self.event("reminder", call_id="two", output_lines=20,
                                                output_chars=80)))

    def test_reminder_alone_follows_frequency(self):
        shown = [i for i in range(1, 26)
                 if self.advise(self.event("reminder", call_id=f"alone{i}",
                                          output_lines=20, output_chars=80))]
        self.assertEqual(shown, [1, 11, 21])

    def test_output_size_counting(self):
        for text, expected in (("a\nb\n", 2), ("a\nb", 2), ("a\r\nb\r\n", 2), ("", 0)):
            with self.subTest(text=text):
                self.assertEqual(core.output_size((text,))[0], expected)
        lines, chars = core.output_size(("a\n", "bc"))
        self.assertEqual(lines, 2)
        self.assertEqual(math.ceil(chars / 4), 1)

    def test_reminder_script_envelope(self):
        install = Path(self.base) / "install" / "tools" / "hooks"
        install.mkdir(parents=True)
        for filename in ("claude_tool_reminder.py", "claude_session_start.py",
                         "advisor_core.py", "detect.py", "precompact_core.py"):
            shutil.copy(HOOKS / filename, install / filename)
        bin_dir = Path(self.base) / "bin"
        bin_dir.mkdir()
        for tool in TOOLS:
            path = bin_dir / tool
            path.write_text("#!/bin/sh\nexit 0\n")
            path.chmod(0o700)
        env = dict(self.env, PATH=str(bin_dir))
        payload = {"tool_name": "Bash", "tool_input": {"command": "grep x ."},
                   "tool_response": {"stdout": "x\n" * 499 + "x", "stderr": ""},
                   "tool_use_id": "reminder-id", "session_id": "script-session"}
        proc = subprocess.run([sys.executable, "-S", str(install / "claude_tool_reminder.py")],
                              input=json.dumps(payload), text=True, capture_output=True,
                              env=env, timeout=10)
        self.assertEqual((proc.returncode, proc.stderr), (0, ""))
        result = json.loads(proc.stdout)
        self.assertEqual(set(result), {"hookSpecificOutput"})
        self.assertEqual(set(result["hookSpecificOutput"]),
                         {"hookEventName", "additionalContext"})
        self.assertEqual(result["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertIn("printed 500 lines", result["hookSpecificOutput"]["additionalContext"])
        empty = subprocess.run([sys.executable, "-S", str(install / "claude_tool_reminder.py")],
                               input="", text=True, capture_output=True, env=env, timeout=10)
        self.assertEqual((empty.returncode, empty.stdout, empty.stderr), (0, "{}", ""))


def time_now():
    import time
    return time.time()


if __name__ == "__main__":
    unittest.main()
