"""SPEC R3/R4 tests for D-06..D-08 advisor parsing, output safety and read reports."""
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HOOKS = os.path.join(_ROOT, "tools", "hooks")
_STUB = os.path.join(_ROOT, "tests", "fixtures", "precompact", "stub_client.py")
sys.path.insert(0, _HOOKS)


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HOOKS, filename))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = _load("advisor_core_test", "advisor_core.py")
session = _load("session_start_test", "claude_session_start.py")
TOOLS = {"rg", "bat", "fd", "sd"}

COMMANDS = [
    ("grep -rn TODO .", ["grep"]), ("cat f | grep x", ["cat", "grep"]),
    ('echo "cat"', []), ("git grep x", []), ("rg x", []),
    ("find . -name '*.py'", ["find"]), ("sed -n '5,9p' f", ["sed-range"]),
    ("sed -i 's/a/b/' f", ["sed-edit"]), ("sed 's/a/b/g' f", ["sed-edit"]),
    ("sed '/^#/d' f", []), ("ls && grep -l x f", ["grep"]),
    ("make || grep err log", ["grep"]), ("echo a; cat f", ["cat"]),
    ("echo a\ngrep b f", ["grep"]), ("man grep", []),
    ("./bin/grep x f", ["grep"]), ("sudo grep x f", ["grep"]),
    ("FOO=1 grep x f", ["grep"]),
    ("if grep -q x f; then cat f; fi", ["grep", "cat"]),
    ("(cd d && find . -type f)", ["find"]), ("echo $(grep x f)", ["grep"]),
    ("grep x <<EOF\ncat\nEOF", ["grep"]), ("xargs -0 grep x", ["grep"]),
    ("time find .", ["find"]), ("cat a | cat b", ["cat"]),
    ("grep x f 2>&1 | head", ["grep"]), ("fd -e py | xargs bat", []),
    ("echo \"it's", []), ('""', []), ('"   "', []), ('echo "|" grep x', []),
    ("echo a # note | grep y\ncat f", ["cat"]), ("echo a#b ; grep x f", ["grep"]),
    ("'grep' x f", ["grep"]), ("echo '# x' && cat f", ["cat"]),
    ("sudo -u root grep x f", []), (r"echo \| grep x", []),
    ("sed '/x/d' f | echo 's/a/b/'", []),
    ("sed '/x/d' f; echo -n '5,9p'", []),
    ("env FOO=1 grep x f", ["grep"]),
    ("sudo env FOO=1 grep x f", ["grep"]),
    ("FOO='x y' grep x f", ["grep"]),
    ("sed s" + "/" * 16000 + "! f", ["sed-edit"]),
    ("grep x \\ncat f", ["grep"]), ('echo x" | grep "y', []),
    ("echo '\\'; grep x f", ["grep"]),
]


class AdvisorCoreTests(unittest.TestCase):
    def test_bash_advice_table(self):
        self.assertGreaterEqual(len(COMMANDS), 20)
        for command, expected in COMMANDS:
            with self.subTest(command=command):
                actual = [identity for identity, _line in core.bash_advice(command, TOOLS)]
                self.assertEqual(actual, expected)

    def test_bash_advice_lines_carry_flags(self):
        lines = dict(core.bash_advice("grep x f; cat f.py; sed -n '5,9p' f; "
                                      "sed -i 's/a/b/' f; find .", TOOLS))
        self.assertIn("rg -n", lines["grep"])
        self.assertIn("rg -l", lines["grep"])
        self.assertIn("--glob", lines["grep"])
        cat_line = dict(core.bash_advice("cat f.py", TOOLS))["cat"]
        self.assertIn("bat --plain --paging=never -l py", cat_line)
        for command in ("cat notes.backup2024", "cat Makefile"):
            self.assertNotIn("-l", dict(core.bash_advice(command, TOOLS))["cat"])
        self.assertIn("-r 5:9", lines["sed-range"])
        self.assertIn("offset", lines["sed-range"])
        self.assertIn("sd -p", lines["sed-edit"])
        self.assertIn("fd --type f --glob", lines["find"])
        self.assertTrue(all(line.startswith("ai-kit advice: ") for line in lines.values()))
        self.assertNotIn("f.py", " ".join(lines.values()))

    def test_bash_advice_uninstalled_tools_silent(self):
        detect = _load("detect_uninstalled_test", "detect.py")
        _load("reminder_uninstalled_test", "claude_tool_reminder.py")
        subsets = ((set(), set()), ({"fd"}, {"fd"}), ({"bat", "sd"}, {"bat", "sd"}))
        command = "grep x f | cat f; sed -n '1,2p' f; sed -i 's/a/b/' f; find ."
        for installed, _expected in subsets:
            with self.subTest(installed=installed):
                self.assertEqual([item[0] for item in core.bash_advice(
                    "cat f | grep x", installed)],
                    [name for name in ("cat", "grep") if
                     (name == "cat" and "bat" in installed) or
                     (name == "grep" and "rg" in installed)])
                bin_path = self._bin_with(installed)
                path_env = {"PATH": bin_path}
                for _identity, line in core.bash_advice(command, installed):
                    for modern in {"rg", "bat", "fd", "sd", "eza"} - installed:
                        self.assertNotRegex(line, rf"\\b{modern}\\b")
                found = detect.detect_substitutions(bin_path)
                briefing = detect.compose_message(found)
                for text in briefing:
                    for modern in {"rg", "bat", "fd", "sd", "eza"} - installed:
                        self.assertNotRegex(text, rf"\\b{modern}\\b")
                event = {"hook_event_name": "PostToolUse", "session_id": uuid.uuid4().hex,
                         "tool_name": "Bash", "tool_input": {"command": command},
                         "tool_response": {"stdout": "\\n".join(["x"] * 500)}}
                message = core.run_claude(json.dumps(event).encode("utf-8"), "reminder", path_env)
                if installed:
                    self.assertIsNotNone(message)
                    for modern in {"rg", "bat", "fd", "sd", "eza"} - installed:
                        self.assertNotRegex(message, rf"\\b{modern}\\b")
                else:
                    self.assertIsNone(message)

    def _bin_with(self, installed):
        path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, path, ignore_errors=True)
        for tool in installed:
            executable = os.path.join(path, tool)
            with open(executable, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\\nexit 0\\n")
            os.chmod(executable, 0o700)
        return path

    def test_emit_allows_only_context_keys(self):
        for message in (None, "", "m"):
            for system_message in (None, "", "s"):
                for event in ("SessionStart", "PreToolUse", "PostToolUse"):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        session.emit(message, system_message, event)
                    payload = json.loads(output.getvalue())
                    self.assertLessEqual(set(payload), {"systemMessage", "hookSpecificOutput"})
                    if payload.get("hookSpecificOutput"):
                        self.assertEqual(set(payload["hookSpecificOutput"]),
                                         {"hookEventName", "additionalContext"})
                    if not message and not system_message:
                        self.assertEqual(payload, {})

    def _sandbox(self):
        root = tempfile.mkdtemp(prefix="advisor-test-")
        runtime = os.path.join(root, "runtime")
        os.mkdir(runtime, 0o700)
        env = {"HOME": os.path.join(root, "home"),
               "XDG_CONFIG_HOME": os.path.join(root, "config"),
               "XDG_CACHE_HOME": os.path.join(root, "cache"),
               "XDG_STATE_HOME": os.path.join(root, "state"),
               "XDG_RUNTIME_DIR": runtime, "PATH": os.environ.get("PATH", "")}
        os.makedirs(env["HOME"])
        return root, env

    def _read_event(self, path, offset=None, limit=None):
        event = {"tool": "read", "path": path, "offset": offset, "limit": limit}
        return core.advise(event, {"PATH": ""})

    def test_read_report_thresholds(self):
        root = tempfile.mkdtemp(prefix="read-threshold-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        exact_lines = (b"x" * 19 + b"\n") * 2000
        below_lines = b"x\n" * 1999 + b"x" * (39000 - 3998)
        cases = (("three-thousand", b"x\n" * 3000, True),
                 ("below", below_lines, False),
                 ("two-thousand", exact_lines, False),
                 ("over-lines", b"x\n" * 2001, True),
                 ("over-bytes", b"x" * 40001, True), ("empty", b"", False))
        for name, content, expected in cases:
            with self.subTest(name=name):
                path = os.path.join(root, name)
                with open(path, "wb") as handle:
                    handle.write(content)
                report = self._read_event(path)
                self.assertEqual(report is not None, expected)
                if name == "three-thousand":
                    self.assertIn("3000 lines", report)

    def test_read_report_ranged_silent(self):
        root = tempfile.mkdtemp(prefix="read-ranged-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        path = os.path.join(root, "large.txt")
        with open(path, "wb") as handle:
            handle.write(b"x\n" * 3000)
        for offset, limit in ((1, None), (None, 20), (1, 20)):
            with self.subTest(offset=offset, limit=limit):
                self.assertIsNone(self._read_event(path, offset, limit))

    def test_read_report_bad_paths_give_nothing(self):
        root = tempfile.mkdtemp(prefix="read-bad-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        directory = os.path.join(root, "directory")
        os.mkdir(directory)
        fifo = os.path.join(root, "pipe")
        os.mkfifo(fifo)
        started = __import__("time").monotonic()
        for path in (os.path.join(root, "missing"), directory, fifo, "relative.txt", None):
            with self.subTest(path=path):
                self.assertIsNone(self._read_event(path))
        self.assertLess(__import__("time").monotonic() - started, 1.0)

    def test_read_report_sparse_file_bounded(self):
        root = tempfile.mkdtemp(prefix="read-sparse-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        path = os.path.join(root, "sparse.bin")
        with open(path, "wb"):
            os.truncate(path, 100 * 1024 * 1024)
        started = __import__("time").monotonic()
        report = self._read_event(path)
        self.assertLess(__import__("time").monotonic() - started, 1.0)
        self.assertIn("≥", report)

    def test_read_report_text_shape(self):
        root = tempfile.mkdtemp(prefix="read-shape-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        path = os.path.join(root, "private-name.txt")
        content = b"secret content " + b"z" * 41000
        with open(path, "wb") as handle:
            handle.write(content)
        report = self._read_event(path)
        self.assertIn(str(len(content)), report)
        self.assertIn("≈", report)
        self.assertIn(str((len(content) + 3) // 4), report)
        self.assertIn("next", report)
        self.assertIn("offset", report)
        self.assertNotIn("private-name", report)
        self.assertNotIn("secret content", report)
        binary = os.path.join(root, "binary")
        with open(binary, "wb") as handle:
            handle.write(bytes(range(256)) * 200)
        self.assertIsNotNone(self._read_event(binary))

    def test_advisor_hook_budgets(self):
        scripts = (
            ("claude_session_start.py", {"hook_event_name": "SessionStart", "source": "startup"}),
            ("claude_tool_advisor.py", {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                                         "tool_input": {"command": "grep x f"}}),
            ("claude_tool_reminder.py", {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                                          "tool_input": {"command": "grep x f"},
                                          "tool_response": {"stdout": "\\n".join(["x"] * 300)}}),
        )
        root, env = self._sandbox()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        bin_dir = os.path.join(root, "bin")
        os.mkdir(bin_dir)
        for tool in TOOLS:
            path = os.path.join(bin_dir, tool)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\\nexit 0\\n")
            os.chmod(path, 0o700)
        env["PATH"] = bin_dir
        for script, payload in scripts:
            elapsed = []
            with self.subTest(script=script):
                for _ in range(20):
                    event = dict(payload, session_id=uuid.uuid4().hex)
                    started = time.monotonic()
                    proc = subprocess.run([sys.executable, "-S", os.path.join(_HOOKS, script)],
                                          input=json.dumps(event), text=True, capture_output=True,
                                          env=env, timeout=3, check=False)
                    elapsed.append(time.monotonic() - started)
                    self.assertEqual((proc.returncode, proc.stderr), (0, ""))
                median, maximum = statistics.median(elapsed), max(elapsed)
                self.assertLess(median, 0.3, f"median={median:.3f}s max={maximum:.3f}s")
                self.assertLess(maximum, 1.0, f"median={median:.3f}s max={maximum:.3f}s")

    def test_forced_exception_gives_empty(self):
        for entry, core_name, script_name in (
                ("claude_tool_advisor.py", "advisor_core.py", "claude_tool_advisor.py"),
                ("claude_tool_reminder.py", "advisor_core.py", "claude_tool_reminder.py"),
                ("claude_decision_probe.py", "precompact_core.py", "claude_decision_probe.py"),
                ("cursor_session_start.py", "detect.py", "cursor_session_start.py")):
            with self.subTest(entry=entry):
                root, env = self._sandbox()
                self.addCleanup(shutil.rmtree, root, ignore_errors=True)
                install = os.path.join(root, "install", "tools", "hooks")
                os.makedirs(install)
                for source in os.listdir(_HOOKS):
                    if source.endswith(".py"):
                        shutil.copy(os.path.join(_HOOKS, source), install)
                if core_name == "claude_session_start.py":
                    os.unlink(os.path.join(install, core_name))
                else:
                    with open(os.path.join(install, core_name), "w", encoding="utf-8") as handle:
                        handle.write('raise RuntimeError("x")\\n')
                env["AI_KIT_PRECOMPACT_CLIENT"] = _STUB
                payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                           "tool_input": {"command": "grep x f"}, "session_id": uuid.uuid4().hex}
                proc = subprocess.run([sys.executable, "-S", os.path.join(install, script_name)],
                                      input=json.dumps(payload), text=True, capture_output=True,
                                      env=env, timeout=5, check=False)
                self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, "{}", ""))

    def test_advisor_script_outputs_only_context(self):
        root, env = self._sandbox()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        install = os.path.join(root, "install with space", "tools", "hooks")
        os.makedirs(install)
        filenames = ("claude_tool_advisor.py", "claude_session_start.py",
                     "advisor_core.py", "detect.py")
        for filename in filenames:
            shutil.copy(os.path.join(_HOOKS, filename), install)
        bin_dir = os.path.join(root, "bin")
        os.mkdir(bin_dir)
        for tool in TOOLS:
            toolpath = os.path.join(bin_dir, tool)
            with open(toolpath, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\nexit 0\n")
            os.chmod(toolpath, 0o700)
        os.symlink(sys.executable, os.path.join(bin_dir, "python3"))
        env["PATH"] = bin_dir
        script = os.path.join(install, "claude_tool_advisor.py")
        for command, _expected in COMMANDS:
            payload = {"hook_event_name": "PreToolUse", "session_id": uuid.uuid4().hex,
                       "tool_name": "Bash", "tool_input": {"command": command},
                       "tool_use_id": uuid.uuid4().hex}
            proc = subprocess.run([sys.executable, "-S", script], input=json.dumps(payload),
                                  text=True, capture_output=True, env=env, timeout=10)
            self.assertEqual((proc.returncode, proc.stderr), (0, ""))
            result = json.loads(proc.stdout)
            self.assertLessEqual(set(result), {"hookSpecificOutput"})
            if result:
                self.assertEqual(set(result["hookSpecificOutput"]),
                                 {"hookEventName", "additionalContext"})
                self.assertEqual(result["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        proc = subprocess.run([sys.executable, "-S", script], input="", text=True,
                              capture_output=True, env=env, timeout=10)
        self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, "{}", ""))


_LIVE_DIR = os.path.join(_ROOT, ".planning", "phases",
                         "21.3-visible-tool-advisory-hooks-as-setup-knobs")
_LIVE_MD = os.path.join(_LIVE_DIR, "21.3-LIVE.md")


def _load_live_checker():
    spec = importlib.util.spec_from_file_location(
        "check_live_test", os.path.join(_LIVE_DIR, "live", "check_live.py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LiveEvidenceCheckerTests(unittest.TestCase):
    """Phase 21.3 live gate: check_live.py must reject unobserved evidence (SPEC R10)."""

    @classmethod
    def setUpClass(cls):
        cls.checker = _load_live_checker()
        with open(_LIVE_MD, encoding="utf-8") as handle:
            cls.template = handle.read()

    def _write(self, text):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        path = os.path.join(root, "21.3-LIVE.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def _all_pass(self, sign_off="pass", launch="opencode --standalone"):
        out = []
        for line in self.template.splitlines():
            if line.startswith("| L-"):
                line = re.sub(r"not run \([^|]*\) \|$", "pass |", line)
            elif line.startswith("Result:"):
                line = f"Result: {sign_off}"
            elif line.startswith("Launched with:"):
                line = f"Launched with: {launch}"
            out.append(line)
        return "\n".join(out) + "\n"

    def test_checked_in_live_evidence_is_rejected(self):
        failures = self.checker.check(_LIVE_MD)
        self.assertIn("L-C1: Result is 'not run (needs an interactive host login "
                      "in the scratch HOME; owner)', expected 'pass'", failures)
        self.assertTrue(any(f.startswith("S-OC: unresolved Result 'not run") for f in failures))
        self.assertIn("S-OC: Launched with must contain --standalone", failures)
        self.assertEqual(len(failures), 12 + 2)

    def test_all_rows_pass_clears_matrix_failures(self):
        failures = self.checker.check(self._write(self._all_pass(sign_off="fail (no append)")))
        self.assertEqual(failures, [])

    def test_pass_on_s_oc_needs_adapter_plan(self):
        failures = self.checker.check(self._write(self._all_pass()))
        self.assertEqual(len(failures), 1)
        self.assertIn("pass requires a later adapter plan", failures[0])

    def test_missing_row_and_missing_standalone_are_rejected(self):
        text = self._all_pass(sign_off="fail (no append)", launch="opencode")
        text = "\n".join(l for l in text.splitlines() if not l.startswith("| L-P4 ")) + "\n"
        failures = self.checker.check(self._write(text))
        self.assertIn("L-P4: expected exactly one row, found 0", failures)
        self.assertIn("S-OC: Launched with must contain --standalone", failures)

    def test_usage_error_exits_2(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.checker.main(["a", "b"]), 2)


if __name__ == "__main__":
    unittest.main()
