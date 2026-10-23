"""SPEC R3/R4 tests for D-06..D-08 advisor parsing, output safety and read reports."""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HOOKS = os.path.join(_ROOT, "tools", "hooks")
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
    ("grep x \\\ncat f", ["grep"]), ('echo x" | grep "y', []),
    ("echo '\\'; grep x f", ["grep"]),
]


class AdvisorCoreTests(unittest.TestCase):
    def test_bash_advice_table(self):
        acceptance_rows = (
            ("grep -rn TODO .", ["grep"]), ("cat f | grep x", ["cat", "grep"]),
            ('echo "cat"', []), ("git grep x", []), ("rg x", []),
            ("find . -name '*.py'", ["find"]), ("sed -n '5,9p' f", ["sed-range"]),
            ("sed -i 's/a/b/' f", ["sed-edit"]), ("sed 's/a/b/g' f", ["sed-edit"]),
            ("sed '/^#/d' f", []), ("ls && grep -l x f", ["grep"]),
            ("make || grep err log", ["grep"]), ("echo a; cat f", ["cat"]),
            ("echo a\\ngrep b f", ["grep"]), ("man grep", []),
            ("./bin/grep x f", ["grep"]), ("sudo grep x f", ["grep"]),
            ("FOO=1 grep x f", ["grep"]),
            ("if grep -q x f; then cat f; fi", ["grep", "cat"]),
            ("(cd d && find . -type f)", ["find"]), ("echo $(grep x f)", ["grep"]),
        )
        self.assertGreaterEqual(len(acceptance_rows), 20)
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
        for installed, expected in (({"rg"}, ["grep"]), (set(), []), ({"fd"}, [])):
            with self.subTest(installed=installed):
                self.assertEqual([item[0] for item in core.bash_advice(
                    "cat f | grep x", installed)], expected)
                find_advice = core.bash_advice("find .", installed)
                self.assertEqual([item[0] for item in find_advice],
                                 ["find"] if "fd" in installed else [])
                joined = " ".join(line for _identity, line in find_advice)
                for unavailable in {"rg", "bat", "sd"} - installed:
                    self.assertNotRegex(joined, rf"\\b{unavailable}\\b")

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
                handle.write("#!/bin/sh\\nexit 0\\n")
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


if __name__ == "__main__":
    unittest.main()
