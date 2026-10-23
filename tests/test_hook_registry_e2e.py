"""E2E: real `python3 tools/setup.py install --headless --with-hooks=precompact`
runs under a temp HOME (SPEC R10). Env holds only PATH plus the temp overrides
— nothing reaches the real ~/.claude, ~/.pi, ~/.cursor or opencode dirs. A
space in the temp root exercises the quoting edge (Round 4/5).
"""
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

SETUP = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "tools", "setup.py"))
REPO = os.path.dirname(os.path.dirname(SETUP))


class HookRegistryE2E(unittest.TestCase):
    def setUp(self):
        # A space in the root path exercises the quoting edge.
        self.root = tempfile.mkdtemp(prefix="xai-hook ")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.home = os.path.join(self.root, "home")
        self.claude = os.path.join(self.root, "claude")
        self.cursor = os.path.join(self.root, "cursor")
        self.pi = os.path.join(self.root, "pi")
        self.opencode = os.path.join(self.root, "opencode")
        self.env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": self.home,
            "AI_KIT_DIR": REPO,
            "CLAUDE_CONFIG_DIR": self.claude,
            "CURSOR_CONFIG_DIR": self.cursor,
            "PI_CODING_AGENT_DIR": self.pi,
            "OPENCODE_CONFIG_DIR": self.opencode,
            "XDG_CONFIG_HOME": os.path.join(self.root, ".config"),
            "XDG_STATE_HOME": os.path.join(self.root, "state"),
            "XDG_CACHE_HOME": os.path.join(self.root, ".cache"),
            "XDG_RUNTIME_DIR": os.path.join(self.root, ".runtime"),
        }

    def run_setup(self, *args, env=None):
        return subprocess.run(
            [sys.executable, SETUP, *args],
            env=env or self.env, capture_output=True, text=True)

    def read_settings(self):
        with open(os.path.join(self.claude, "settings.json"),
                  encoding="utf-8") as handle:
            return json.load(handle)

    def test_tracer_with_hooks_tool_advisor(self):
        link = os.path.join(self.root, "ai kit")
        os.symlink(REPO, link)
        os.makedirs(self.claude)
        env = dict(self.env, AI_KIT_DIR=link)
        proc = self.run_setup("install", "--headless",
                              "--with-hooks=tool-advisor", env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = self.read_settings()
        self.assertEqual(set(data["hooks"]), {"PreToolUse"})
        entries = data["hooks"]["PreToolUse"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["matcher"], "Bash|Read")
        command = "python3 -S " + shlex.quote(os.path.join(
            link, "tools", "hooks", "claude_tool_advisor.py"))
        self.assertEqual(entries[0]["hooks"], [{"type": "command", "command": command,
                                                  "timeout": 3}])
        for absent in (self.cursor, self.pi, self.opencode):
            self.assertFalse(os.path.exists(absent))
        bin_dir = os.path.join(self.root, "bin")
        os.makedirs(bin_dir)
        with open(os.path.join(bin_dir, "rg"), "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\\nexit 0\\n")
        os.chmod(os.path.join(bin_dir, "rg"), 0o700)
        os.symlink(sys.executable, os.path.join(bin_dir, "python3"))
        hook_env = dict(env, PATH=bin_dir)
        payload = {"hook_event_name": "PreToolUse", "session_id": "advice-unique-1",
                   "tool_name": "Bash", "tool_input": {"command": "grep -rn TODO ."},
                   "tool_use_id": "toolu_t1"}
        shell = shutil.which("sh")
        assert shell is not None
        proc = subprocess.run([shell, "-c", command], input=json.dumps(payload),
                              capture_output=True, text=True, env=hook_env, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, "")
        result = json.loads(proc.stdout)
        self.assertEqual(set(result), {"hookSpecificOutput"})
        output = result["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PreToolUse")
        self.assertIn("rg -n", output["additionalContext"])

    def test_tracer_with_hooks_precompact_wires_two_claude_entries(self):
        os.makedirs(self.claude)
        expected_command = "python3 -S " + shlex.quote(os.path.join(
            REPO, "tools", "hooks", "claude_precompact.py"))
        proc = self.run_setup("install", "--headless", "--with-hooks=precompact")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = self.read_settings()
        self.assertEqual(set(data.get("hooks", {})),
                         {"PreCompact", "SessionStart"})
        pre = data["hooks"]["PreCompact"]
        self.assertEqual(len(pre), 1)
        self.assertEqual(pre[0]["matcher"], "manual|auto")
        self.assertEqual(len(pre[0]["hooks"]), 1)
        self.assertEqual(pre[0]["hooks"][0]["command"], expected_command)
        self.assertEqual(pre[0]["hooks"][0]["timeout"], 10)
        start = data["hooks"]["SessionStart"]
        self.assertEqual(len(start), 1)
        self.assertEqual(start[0]["matcher"], "compact")
        self.assertEqual(len(start[0]["hooks"]), 1)
        self.assertEqual(start[0]["hooks"][0]["command"], expected_command)
        self.assertEqual(start[0]["hooks"][0]["timeout"], 10)
        for absent in (self.cursor, self.pi, self.opencode):
            self.assertFalse(os.path.exists(absent))

    def test_link_rows_pi_and_opencode(self):
        os.makedirs(self.claude)
        os.makedirs(self.pi)
        os.makedirs(self.opencode)
        proc = self.run_setup("install", "--headless", "--with-hooks=precompact")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        pi_link = os.path.join(self.pi, "extensions", "ai-kit-precompact.ts")
        oc_link = os.path.join(self.opencode, "plugins", "ai-kit-precompact.ts")
        self.assertTrue(os.path.islink(pi_link))
        self.assertEqual(os.readlink(pi_link), os.path.join(
            REPO, "tools", "hooks", "pi", "ai-kit-precompact.ts"))
        self.assertTrue(os.path.islink(oc_link))
        self.assertEqual(os.readlink(oc_link), os.path.join(
            REPO, "tools", "hooks", "opencode", "ai-kit-precompact.ts"))
        self.assertFalse(any(name.endswith((".json", ".jsonc"))
                             for directory in (self.pi, self.opencode)
                             for name in os.listdir(directory)))

    def test_host_qualified_pi_only(self):
        os.makedirs(self.pi)
        proc = self.run_setup("install", "--headless", "--with-hooks=precompact:pi")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.islink(os.path.join(
            self.pi, "extensions", "ai-kit-precompact.ts")))
        self.assertFalse(os.path.exists(os.path.join(self.claude, "settings.json")))

    def test_absent_hosts_skip_exit_0(self):
        proc = self.run_setup("install", "--headless", "--with-hooks=precompact")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for host in (self.claude, self.pi, self.opencode):
            self.assertFalse(os.path.exists(host))

    def test_foreign_file_at_link_path_left(self):
        os.makedirs(self.claude)
        os.makedirs(os.path.join(self.pi, "extensions"))
        path = os.path.join(self.pi, "extensions", "ai-kit-precompact.ts")
        payload = b"foreign file\\n"
        with open(path, "wb") as handle:
            handle.write(payload)
        proc = self.run_setup("install", "--headless", "--with-hooks=precompact")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(path, proc.stderr)
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), payload)
        self.assertTrue(os.path.isfile(os.path.join(self.claude, "settings.json")))

    def test_malformed_settings_refused_whole_file(self):
        os.makedirs(self.claude)
        path = os.path.join(self.claude, "settings.json")
        payload = b'{"hooks": {"SessionStart": "nope"}}\\n'
        with open(path, "wb") as handle:
            handle.write(payload)
        proc = self.run_setup("install", "--headless", "--with-hooks=precompact")
        self.assertEqual(proc.returncode, 1)
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), payload)

    def test_selector_errors_and_empty(self):
        cases = [
            (("install", "--headless", "--with-hooks=nope"), "nope"),
            (("install", "--headless", "--with-hooks=precompact:cursor"), "precompact:cursor"),
            (("install", "--headless", "--with-hooks", "install"), "install"),
            (("install", "--with-hooks=precompact"), "--with-hooks"),
            (("install", "--headless", "--hooks=precompact"), "--hooks"),
            (("uninstall", "--hooks=nope"), "nope"),
        ]
        for args, token in cases:
            with self.subTest(args=args):
                proc = self.run_setup(*args)
                self.assertEqual(proc.returncode, 2)
                self.assertIn(token, proc.stderr)
        for args in (("install", "--headless", "--with-hooks="),
                     ("uninstall", "--hooks=")):
            proc = self.run_setup(*args)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("warn:", proc.stderr)

    def test_bare_with_hooks_wires_registry_defaults(self):
        os.makedirs(self.claude)
        os.makedirs(self.cursor)
        os.makedirs(self.pi)
        proc = self.run_setup("install", "--headless", "--with-hooks")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = self.read_settings()
        self.assertTrue({"SessionStart", "PreToolUse", "PostToolUse"} <= set(data["hooks"]))
        self.assertEqual(data["hooks"]["SessionStart"][0]["matcher"], "startup|compact")
        self.assertFalse(any(entry.get("matcher") == "startup" for entry in
                             data["hooks"]["SessionStart"]))
        self.assertTrue(os.path.islink(os.path.join(
            self.pi, "extensions", "ai-kit-tool-advisor.ts")))
        self.assertTrue(os.path.islink(os.path.join(
            self.pi, "extensions", "ai-kit-tool-reminder.ts")))
        self.assertEqual(set(data["hooks"]["PreToolUse"][0]), {"matcher", "hooks"})

    def test_briefing_and_precompact_compact_entries_independent(self):
        os.makedirs(self.claude)
        self.assertEqual(self.run_setup("install", "--headless",
                                        "--with-hooks=session-briefing,precompact").returncode, 0)
        self.assertEqual(self.run_setup("uninstall", "--hooks=session-briefing").returncode, 0)
        data = self.read_settings()
        self.assertEqual([entry["matcher"] for entry in data["hooks"]["SessionStart"]],
                         ["compact"])
        self.assertEqual(self.run_setup("install", "--headless",
                                        "--with-hooks=session-briefing").returncode, 0)
        self.assertEqual(self.run_setup("uninstall", "--hooks=precompact").returncode, 0)
        data = self.read_settings()
        self.assertEqual([entry["matcher"] for entry in data["hooks"]["SessionStart"]],
                         ["startup|compact"])

    def test_with_hooks_is_additive(self):
        os.makedirs(self.claude)
        self.assertEqual(self.run_setup("install", "--headless", "--with-hooks").returncode, 0)
        before = self.read_settings()
        proc = self.run_setup("install", "--headless", "--with-hooks=decision-probe")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        after = self.read_settings()
        self.assertEqual(after["hooks"]["PreToolUse"], before["hooks"]["PreToolUse"])
        self.assertEqual(after["hooks"]["PostToolUse"], before["hooks"]["PostToolUse"])
        self.assertIn("startup", [e.get("matcher") for e in after["hooks"]["SessionStart"]])

    def test_each_id_alone_wires_only_its_entries(self):
        for hook_id in ("session-briefing", "tool-advisor", "tool-reminder",
                        "decision-probe", "precompact"):
            with self.subTest(hook_id=hook_id):
                self.setUp()
                for directory in (self.claude, self.cursor, self.pi, self.opencode):
                    os.makedirs(directory)
                settings_path = os.path.join(self.claude, "settings.json")
                foreign = {event: {"matcher": "foreign", "hooks": [{"type": "command",
                           "command": "echo foreign"}]} for event in
                           ("SessionStart", "PreToolUse", "PostToolUse", "PreCompact")}
                with open(settings_path, "w", encoding="utf-8") as handle:
                    json.dump({"theme": "dark",
                               "hooks": {k: [v] for k, v in foreign.items()}}, handle)
                os.makedirs(os.path.join(self.cursor, "hooks"), exist_ok=True)
                with open(os.path.join(self.cursor, "hooks.json"), "w", encoding="utf-8") as handle:
                    json.dump({"version": 1, "hooks": {"sessionStart": [
                        {"type": "command", "command": "echo foreign cursor"}]}}, handle)
                for folder in (os.path.join(self.pi, "extensions"),
                               os.path.join(self.opencode, "plugins")):
                    os.makedirs(folder)
                    with open(os.path.join(folder, "foreign.ts"), "w", encoding="utf-8") as handle:
                        handle.write("foreign")
                proc = self.run_setup("install", "--headless", f"--with-hooks={hook_id}")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                installed = self.read_settings()
                from tools import setup as setup_module
                marker_scripts = [row.script.replace("/", os.sep) for row in
                                  setup_module.HOOK_REGISTRY if row.id == hook_id]
                for event, entries in installed["hooks"].items():
                    ours = [entry for entry in entries if any(
                        marker in hook.get("command", "")
                        for hook in entry.get("hooks") or []
                        for marker in marker_scripts)]
                    self.assertEqual(len(ours), len([row for row in
                                     setup_module.HOOK_REGISTRY if row.id == hook_id
                                     and row.host == "claude" and row.event == event]))
                    if event in foreign:
                        self.assertEqual(entries[0], foreign[event])
                proc = self.run_setup("uninstall", f"--hooks={hook_id}")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(self.read_settings()["theme"], "dark")


    def test_uninstall_hooks_removes_exactly_precompact(self):
        os.makedirs(self.claude)
        os.makedirs(self.pi)
        os.makedirs(self.opencode)
        self.assertEqual(self.run_setup("install", "--headless", "--with-hooks").returncode, 0)
        self.assertEqual(self.run_setup("install", "--headless",
                                        "--with-hooks=precompact").returncode, 0)
        skill = os.path.join(self.claude, "skills", "foreign")
        os.makedirs(os.path.dirname(skill), exist_ok=True)
        os.symlink(os.path.join(self.root, "elsewhere"), skill)
        proc = self.run_setup("uninstall", "--hooks=precompact")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = self.read_settings()
        self.assertEqual([e["matcher"] for e in data["hooks"]["SessionStart"]],
                         ["startup|compact"])
        self.assertEqual(data["hooks"].get("PreCompact", []), [])
        self.assertFalse(os.path.lexists(os.path.join(
            self.pi, "extensions", "ai-kit-precompact.ts")))
        self.assertFalse(os.path.lexists(os.path.join(
            self.opencode, "plugins", "ai-kit-precompact.ts")))
        self.assertTrue(os.path.islink(skill))

    def test_foreign_precompact_survives_install_and_uninstall(self):
        os.makedirs(self.claude)
        path = os.path.join(self.claude, "settings.json")
        foreign = {"matcher": "manual", "hooks": [{"type": "command",
                                                       "command": "echo foreign"}]}
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"theme": "dark", "hooks": {"PreCompact": [foreign]}}, handle)
        self.assertEqual(self.run_setup("install", "--headless",
                                        "--with-hooks=precompact").returncode, 0)
        self.assertEqual(self.read_settings()["hooks"]["PreCompact"][0], foreign)
        self.assertEqual(self.run_setup("uninstall", "--hooks=precompact").returncode, 0)
        data = self.read_settings()
        self.assertEqual(data["hooks"]["PreCompact"], [foreign])
        self.assertEqual(data["theme"], "dark")

    def test_bare_uninstall_removes_all_ai_kit_hooks(self):
        os.makedirs(self.claude)
        os.makedirs(self.pi)
        os.makedirs(self.opencode)
        foreign = os.path.join(self.pi, "extensions", "foreign.ts")
        os.makedirs(os.path.dirname(foreign), exist_ok=True)
        os.symlink(os.path.join(self.root, "foreign-target"), foreign)
        self.assertEqual(self.run_setup("install", "--headless", "--with-hooks").returncode, 0)
        self.assertEqual(self.run_setup("install", "--headless",
                                        "--with-hooks=precompact").returncode, 0)
        proc = self.run_setup("uninstall")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = self.read_settings()
        self.assertEqual(data.get("hooks", {}).get("SessionStart", []), [])
        self.assertEqual(data.get("hooks", {}).get("PreCompact", []), [])
        self.assertFalse(os.path.lexists(os.path.join(
            self.pi, "extensions", "ai-kit-precompact.ts")))
        self.assertFalse(os.path.lexists(os.path.join(
            self.opencode, "plugins", "ai-kit-precompact.ts")))
        self.assertTrue(os.path.islink(foreign))

    def test_tracer_space_in_install_dir_runs_configured_command(self):
        # AI_KIT_DIR is a symlink named `ai kit` (with a space) -> the repo.
        link = os.path.join(self.root, "ai kit")
        os.symlink(REPO, link)
        os.makedirs(self.claude)
        env = dict(self.env, AI_KIT_DIR=link)
        proc = self.run_setup("install", "--headless",
                              "--with-hooks=precompact", env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = self.read_settings()
        command = data["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        self.assertIn("'", command)  # the script path is shell-quoted
        # Run the stored string exactly as a host's `sh -c` would.
        bin_dir = os.path.join(self.root, "bin")
        os.makedirs(bin_dir)
        os.symlink(sys.executable, os.path.join(bin_dir, "python3"))
        hook_env = dict(env, PATH=bin_dir)
        shell = shutil.which("sh")
        assert shell is not None
        proc = subprocess.run(
            [shell, "-c", command],
            input=json.dumps({"hook_event_name": "SessionStart",
                              "source": "compact",
                              "session_id": "s-space"}),
            capture_output=True, text=True, env=hook_env, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "{}")
        self.assertEqual(proc.stderr, "")


if __name__ == "__main__":
    unittest.main()
