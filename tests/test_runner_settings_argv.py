"""37-04: runner settings planner via --print-argv (SPEC R2, R3; D-01, D-07, D-11, D-14).

Unit group: real node, no model call.
"""

import json
import os
import subprocess
import tempfile
import unittest

from tests.cross_ai_selftest import TEMPLATE, _real_node_executable, runner_env

NODE = _real_node_executable()
SETTING_PREFIX = "cross-ai: setting "
MODEL_ID_PREFIX = "cross-ai: model-id "


def print_argv(args, template=TEMPLATE):
    assert NODE is not None
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            [NODE, template, "--print-argv", *args], cwd=tmp,
            env={**runner_env(tmp), "AI_KIT_REFUSE_REAL_HOME": "1"},
            capture_output=True, text=True, timeout=60, check=False,
        )
        argv = None
        for line in result.stdout.splitlines():
            fields = line.split("\t")
            if len(fields) >= 3 and fields[2].startswith("["):
                argv = json.loads(fields[2])
                break
        lines = result.stderr.splitlines()
        settings = [line for line in lines if line.startswith(SETTING_PREFIX)]
        model_id = next((line[len(MODEL_ID_PREFIX):] for line in lines
                         if line.startswith(MODEL_ID_PREFIX)), None)
        return result.returncode, argv, settings, model_id, os.path.realpath(tmp), result.stderr


def contains_run(argv, run):
    return any(argv[i:i + len(run)] == run for i in range(len(argv) - len(run) + 1))


NO_SETTING_ARGV = {
    ("pi", "exec"): ["-p", "--model", "fake/ok", "--session-id", "<sid>", "--no-skills",
                     "--no-extensions", "--no-approve", "--offline"],
    ("pi", "review"): ["-p", "--model", "fake/ok", "--session-id", "<sid>", "--no-skills",
                       "--no-extensions", "--no-approve", "--offline", "--tools",
                       "read,grep,find,ls", "--no-mcp", "--no-context-files"],
    ("opencode", "exec"): ["run", "--model", "fake/ok", "--auto", "--format", "json",
                           "--standalone"],
    ("opencode", "review"): ["run", "--model", "fake/ok", "--agent", "plan", "--format", "json",
                             "--standalone"],
    ("cursor", "exec"): ["-p", "--output-format", "json", "--model", "fake-ok-cursor", "--trust",
                         "--force", "--sandbox", "disabled", "--approve-mcps", "--workspace",
                         "{cwd}"],
    ("cursor", "review"): ["-p", "--output-format", "json", "--model", "fake-ok-cursor", "--mode",
                           "ask", "--trust", "--workspace", "{cwd}"],
    ("codex", "exec"): ["exec", "--dangerously-bypass-approvals-and-sandbox",
                        "--skip-git-repo-check", "-C", "{cwd}", "-m", "fake-ok-codex", "--json",
                        "-o", "<tmp>/last-message.md", "-"],
    ("codex", "review"): ["exec", "--sandbox", "read-only", "--skip-git-repo-check", "-C", "{cwd}",
                          "-m", "fake-ok-codex", "--json", "-o", "<tmp>/last-message.md", "-"],
    ("claude", "review"): ["-p", "--model", "fake-ok", "--output-format", "json",
                           "--permission-mode", "plan"],
    ("copilot", "exec"): ["-p", "<prompt>", "-s", "--no-ask-user", "--model", "fake-ok",
                          "--session-id", "<sid>", "--allow-all-tools"],
    ("copilot", "review"): ["-p", "<prompt>", "-s", "--no-ask-user", "--model", "fake-ok",
                            "--session-id", "<sid>", "--allow-all-tools",
                            "--available-tools=view,grep,glob",
                            "--excluded-tools=bash,create,edit,apply_patch", "--deny-tool=shell",
                            "--deny-tool=write", "--disable-builtin-mcps"],
}

EFFORT_ROWS = (
    ("pi", "exec", "fake/ok", "high", ["--model", "fake/ok", "--thinking", "high", "--session-id"],
     "fake/ok"),
    ("opencode", "exec", "fake/ok", "high", ["--model", "fake/ok#high", "--auto"], "fake/ok#high"),
    ("cursor", "review", "fake-ok-cursor", "high",
     ["--model", "fake-ok-cursor[effort=high]", "--mode"],
     "fake-ok-cursor[effort=high]"),
    ("codex", "exec", "fake-ok-codex", "ultra",
     ["<tmp>/last-message.md", "-", "-c", "model_reasoning_effort=ultra"], "fake-ok-codex"),
    ("codex", "review", "fake-ok-codex", "max",
     ["<tmp>/last-message.md", "-", "-c", "model_reasoning_effort=max"], "fake-ok-codex"),
    ("claude", "review", "fake-ok", "max", ["-p", "--model", "fake-ok", "--output-format", "json",
     "--permission-mode", "plan", "--effort", "max"], "fake-ok"),
    ("copilot", "exec", "fake-ok", "xhigh", ["--model", "fake-ok", "--reasoning-effort", "xhigh"],
     "fake-ok"),
)


class TestNoSettingArgv(unittest.TestCase):
    def setUp(self):
        if NODE is None:
            self.skipTest("no real node executable: cross-ai.mjs --print-argv needs node")

    def test_no_setting_argv_and_lines(self):
        for (runtime, mode), expected in NO_SETTING_ARGV.items():
            with self.subTest(runtime=runtime, mode=mode):
                model = "fake/ok" if runtime in ("pi", "opencode") else (
                    "fake-ok-" + runtime if runtime in ("codex", "cursor") else "fake-ok"
                )
                rc, argv, lines, model_id, cwd, stderr = print_argv(
                    ["--runtime", runtime, "--mode", mode, "--model", model]
                )
                self.assertEqual(rc, 0, stderr)
                self.assertEqual(argv, [cwd if x == "{cwd}" else x for x in expected])
                wanted = [f"cross-ai: setting model={model} applied"]
                if runtime in ("pi", "opencode"):
                    wanted.append("cross-ai: setting provider=fake applied")
                role = 'execute' if mode == 'exec' else 'review'
                wanted.append(f"cross-ai: setting role={role} applied")
                self.assertEqual(lines, wanted)
                self.assertEqual(model_id, model)


class TestEffortForms(unittest.TestCase):
    def setUp(self):
        if NODE is None:
            self.skipTest("no real node executable: cross-ai.mjs --print-argv needs node")

    def test_effort_form_per_runtime(self):
        for runtime, mode, model, level, run, expected_id in EFFORT_ROWS:
            with self.subTest(runtime=runtime, mode=mode):
                rc, argv, lines, model_id, _, stderr = print_argv(
                    ["--runtime", runtime, "--mode", mode, "--model", model, "--effort", level]
                )
                self.assertEqual(rc, 0, stderr)
                self.assertTrue(contains_run(argv, run))
                if runtime == "claude":
                    self.assertEqual(argv, run)
                self.assertEqual(model_id, expected_id)
                self.assertEqual(lines[-1], f"cross-ai: setting effort={level} applied")

    def test_id_carried_effort_wins(self):
        for runtime, model in (("pi", "fake/ok:low"), ("pi", "fake/ok:high"),
                               ("opencode", "fake/ok#xhigh"),
                               ("cursor", "fake-ok-cursor[effort=low]")):
            with self.subTest(runtime=runtime, model=model):
                rc, argv, lines, model_id, _, stderr = print_argv(
                    ["--runtime", runtime, "--model", model, "--effort", "high"]
                )
                self.assertEqual(rc, 0, stderr)
                assert argv is not None
                self.assertNotIn("--thinking", argv)
                self.assertEqual(model_id, model)
                self.assertIn("cross-ai: setting effort=high ignored reason=id_carries", lines)

    def test_cursor_bracket_keeps_keys(self):
        rc, argv, _, model_id, _, stderr = print_argv(
            ["--runtime", "cursor", "--mode", "review", "--model",
             "fake-ok-cursor[context=1m]", "--effort", "high"]
        )
        self.assertEqual(rc, 0, stderr)
        self.assertEqual(model_id, "fake-ok-cursor[context=1m,effort=high]")
        assert argv is not None
        self.assertEqual(argv[argv.index("--model") + 1], model_id)

    def test_levels_are_opaque_tokens(self):
        rc, argv, lines, _, _, stderr = print_argv(
            ["--runtime", "codex", "--model", "fake-ok-codex", "--effort", "x-1_2"]
        )
        self.assertEqual(rc, 0, stderr)
        self.assertTrue(contains_run(argv, ["-c", "model_reasoning_effort=x-1_2"]))
        self.assertIn("cross-ai: setting effort=x-1_2 applied", lines)

    def test_codex_effort_alias_behaves_as_before(self):
        rc, argv, lines, _, _, stderr = print_argv(
            ["--runtime", "codex", "--model", "fake-ok-codex", "--codex-effort", "high"]
        )
        self.assertEqual(rc, 0, stderr)
        assert argv is not None
        self.assertEqual(argv.count("model_reasoning_effort=high"), 1)
        self.assertTrue(contains_run(argv, ["-c", "model_reasoning_effort=high"]))
        self.assertIn("cross-ai: setting effort=high applied", lines)


class TestSettingsReport(unittest.TestCase):
    def setUp(self):
        if NODE is None:
            self.skipTest("no real node executable: cross-ai.mjs --print-argv needs node")

    def test_provider_lines(self):
        for runtime, model, expected in (
            ("codex", "fake/ok", "cross-ai: setting provider=fake unknown reason=no_provider_form"),
            ("pi", "fake/ok", "cross-ai: setting provider=fake applied"),
            ("codex", "fake-ok-codex", None),
        ):
            with self.subTest(runtime=runtime, model=model):
                rc, _, lines, _, _, stderr = print_argv(["--runtime", runtime, "--model", model])
                self.assertEqual(rc, 0, stderr)
                providers = [line for line in lines
                             if line.startswith("cross-ai: setting provider=")]
                self.assertEqual(providers, [expected] if expected else [])

    def test_model_id_line_redacted(self):
        key = "sk-" + "a" * 16
        rc, _, lines, model_id, _, stderr = print_argv(
            ["--runtime", "codex", "--model", key]
        )
        self.assertEqual(rc, 0, stderr)
        self.assertEqual(model_id, "<redacted>")
        self.assertIn("cross-ai: setting model=<redacted> applied", lines)
        self.assertNotIn(key, "\n".join(lines))

    def test_escalation_lines_fixed_order(self):
        base = ["--runtime", "pi", "--model", "fake/ok", "--effort", "low"]
        rc, argv, lines, _, _, stderr = print_argv(
            ["--runtime", "pi", "--model", "fake/ok", "--escalate-model",
             "--escalate-runtime", "--effort", "low"]
        )
        self.assertEqual(rc, 0, stderr)
        self.assertEqual(argv, print_argv(base)[1])
        self.assertEqual(lines, [
            "cross-ai: setting model=fake/ok applied",
            "cross-ai: setting provider=fake applied",
            "cross-ai: setting role=execute applied",
            "cross-ai: setting effort=low applied",
            "cross-ai: setting escalate_runtime=true ignored reason=recorded_only",
            "cross-ai: setting escalate_model=true ignored reason=recorded_only",
        ])


class TestConfigEffort(unittest.TestCase):
    def setUp(self):
        if NODE is None:
            self.skipTest("no real node executable: cross-ai.mjs --print-argv needs node")
        self.copy_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.copy_dir.cleanup)
        self.key = "sk-" + "a" * 16
        with open(TEMPLATE, encoding="utf-8") as source:
            text = source.read()
        original = '  "effort": {},\n'
        self.assertEqual(text.count(original), 1)
        default = json.dumps({"codex": "low", "pi": "\x07" + self.key})
        self.copy = os.path.join(self.copy_dir.name, "cross-ai.mjs")
        with open(self.copy, "w", encoding="utf-8") as target:
            target.write(text.replace(original, f'  "effort": {default},\n'))

    def test_config_effort_fed_and_call_wins(self):
        base = ["--runtime", "codex", "--model", "fake-ok-codex"]
        rc, argv, lines, _, _, stderr = print_argv(base, template=self.copy)
        self.assertEqual(rc, 0, stderr)
        self.assertTrue(contains_run(argv, ["-c", "model_reasoning_effort=low"]))
        self.assertIn("cross-ai: setting effort=low applied", lines)
        rc, argv, lines, _, _, stderr = print_argv([*base, "--effort", "high"], template=self.copy)
        self.assertEqual(rc, 0, stderr)
        assert argv is not None
        self.assertIn("model_reasoning_effort=high", argv)
        self.assertNotIn("model_reasoning_effort=low", argv)
        self.assertIn("cross-ai: setting effort=high applied", lines)
        rc, _, lines, _, _, stderr = print_argv(
            ["--runtime", "opencode", "--model", "fake/ok"], template=self.copy
        )
        self.assertEqual(rc, 0, stderr)
        self.assertFalse(any(line.startswith("cross-ai: setting effort=") for line in lines))

    def test_bad_config_level_ignored_redacted(self):
        rc, argv, lines, _, _, stderr = print_argv(
            ["--runtime", "pi", "--model", "fake/ok"], template=self.copy
        )
        self.assertEqual(rc, 0, stderr)
        assert argv is not None
        self.assertNotIn("--thinking", argv)
        self.assertIn("cross-ai: setting effort=<redacted> ignored reason=bad_value", lines)
        self.assertNotIn("\x07", stderr)
        self.assertNotIn(self.key, stderr)


class TestContextForms(unittest.TestCase):
    def setUp(self):
        if NODE is None:
            self.skipTest("no real node executable")

    def test_context_applied_per_kind(self):
        for runtime, model, label, run in (
            ("cursor", "fake-ok-cursor", "1m", ["fake-ok-cursor[context=1m]"]),
            ("copilot", "fake-ok", "long_context",
             ["--model", "fake-ok", "--context", "long_context"]),
            ("codex", "fake-ok-codex", "200k", ["-", "-c", "model_context_window=200000"]),
            ("codex", "fake-ok-codex", "1m", ["-", "-c", "model_context_window=1000000"]),
            ("codex", "fake-ok-codex", "4096", ["-", "-c", "model_context_window=4096"]),
        ):
            with self.subTest(runtime=runtime, label=label):
                mode = "review" if runtime == "cursor" else "exec"
                rc, argv, lines, _, _, err = print_argv(
                    ["--runtime", runtime, "--mode", mode, "--model", model, "--context", label])
                self.assertEqual(rc, 0, err)
                assert argv is not None
                self.assertTrue(contains_run(argv, run))
                self.assertIn(f"cross-ai: setting context={label} applied", lines)

    def test_context_bad_value(self):
        for runtime, model, label in (("copilot", "fake-ok", "1m"),
                                      ("codex", "fake-ok-codex", "abc"),
                                      ("codex", "fake-ok-codex", "0"),
                                      ("codex", "fake-ok-codex", "2000m")):
            rc, argv, lines, _, _, err = print_argv(
                ["--runtime", runtime, "--model", model, "--context", label])
            self.assertEqual(rc, 0, err)
            assert argv is not None
            self.assertNotIn("--context", argv)
            self.assertFalse(any(x.startswith("model_context_window=") for x in argv))
            self.assertIn(f"cross-ai: setting context={label} ignored reason=bad_value", lines)

    def test_context_no_form_and_unverified(self):
        for runtime, mode, model, reason in (("pi", "exec", "fake/ok", "no_form"),
                                              ("opencode", "exec", "fake/ok", "no_form"),
                                              ("claude", "review", "fake-ok", "unverified_form")):
            rc, argv, lines, _, _, err = print_argv(
                ["--runtime", runtime, "--mode", mode, "--model", model, "--context", "1m"])
            self.assertEqual(rc, 0, err)
            self.assertEqual(argv, NO_SETTING_ARGV[runtime, mode])
            self.assertIn(f"cross-ai: setting context=1m ignored reason={reason}", lines)

    def test_context_id_carries(self):
        model = "fake-ok-cursor[context=272k]"
        rc, _, lines, actual, _, err = print_argv(
            ["--runtime", "cursor", "--mode", "review", "--model", model, "--context", "1m"])
        self.assertEqual(rc, 0, err)
        self.assertEqual(actual, model)
        self.assertIn("cross-ai: setting context=1m ignored reason=id_carries", lines)

    def test_effort_and_context_together(self):
        rc, _, lines, model, _, err = print_argv(
            ["--runtime", "cursor", "--mode", "review", "--model", "fake-ok-cursor",
             "--effort", "high", "--context", "1m"])
        self.assertEqual(rc, 0, err)
        self.assertEqual(model, "fake-ok-cursor[effort=high,context=1m]")
        self.assertLess(lines.index("cross-ai: setting effort=high applied"),
                        lines.index("cross-ai: setting context=1m applied"))
        rc, argv, _, _, _, err = print_argv(
            ["--runtime", "codex", "--model", "fake-ok-codex", "--effort", "high",
             "--context", "1m"])
        self.assertEqual(rc, 0, err)
        assert argv is not None
        self.assertTrue(contains_run(argv, ["-c", "model_reasoning_effort=high", "-c",
                                            "model_context_window=1000000"]))


class TestSessionForms(unittest.TestCase):
    def setUp(self):
        if NODE is None:
            self.skipTest("no real node executable")

    def test_chosen_session_ids(self):
        for runtime, model in (("pi", "fake/ok"), ("copilot", "fake-ok")):
            for sid in (None, "s-1"):
                args = ["--runtime", runtime, "--model", model]
                if sid:
                    args += ["--session-id", sid]
                rc, argv, lines, _, _, err = print_argv(args)
                self.assertEqual(rc, 0, err)
                self.assertEqual(argv, [sid if x == "<sid>" and sid else x
                                        for x in NO_SETTING_ARGV[runtime, "exec"]])
                sessions = [x for x in lines if x.startswith("cross-ai: setting session=")]
                self.assertEqual(sessions,
                                 [f"cross-ai: setting session={sid} applied"] if sid else [])

    def test_minted_session_resume_argv(self):
        for runtime, model, flag in (("cursor", "fake-ok-cursor", "--resume"),
                                     ("opencode", "fake/ok", "--session"),
                                     ("codex", "fake-ok-codex", None)):
            rc, argv, lines, _, cwd, err = print_argv(
                ["--runtime", runtime, "--model", model, "--session-id", "s-1"])
            self.assertEqual(rc, 0, err)
            expected = [x if x != "{cwd}" else cwd for x in NO_SETTING_ARGV[runtime, "exec"]]
            if flag:
                expected += [flag, "s-1"]
            else:
                expected = ["exec", "resume", "--dangerously-bypass-approvals-and-sandbox",
                            "--skip-git-repo-check", "-m", model, "--json", "-o",
                            "<tmp>/last-message.md", "s-1", "-"]
            self.assertEqual(argv, expected)
            self.assertIn("cross-ai: setting session=s-1 applied", lines)

    def test_session_mode_forbids(self):
        for mode, extra in (("review", []), ("exec", ["--codex-sandbox", "workspace-write"])):
            rc, argv, lines, _, cwd, err = print_argv(
                ["--runtime", "codex", "--mode", mode, "--model", "fake-ok-codex",
                 "--session-id", "s-1", *extra])
            self.assertEqual(rc, 0, err)
            assert argv is not None
            self.assertIn("cross-ai: setting session=s-1 ignored reason=mode_forbids", lines)
            if mode == "review":
                self.assertEqual(argv, [cwd if x == "{cwd}" else x
                                        for x in NO_SETTING_ARGV["codex", mode]])
            else:
                self.assertTrue(contains_run(argv, ["--sandbox", "workspace-write"]))
                self.assertNotIn("resume", argv)

    def test_claude_review_resumes(self):
        rc, argv, lines, _, _, err = print_argv(
            ["--runtime", "claude", "--mode", "review", "--model", "fake-ok",
             "--session-id", "s-1"])
        self.assertEqual(rc, 0, err)
        self.assertEqual(argv, NO_SETTING_ARGV["claude", "review"] + ["--resume", "s-1"])
        self.assertIn("cross-ai: setting session=s-1 applied", lines)

    def test_uuid_session_line_not_redacted(self):
        sid = "00000000-0000-4000-8000-000000000001"
        rc, _, lines, _, _, err = print_argv(
            ["--runtime", "pi", "--model", "fake/ok", "--session-id", sid])
        self.assertEqual(rc, 0, err)
        self.assertIn(f"cross-ai: setting session={sid} applied", lines)


if __name__ == "__main__":
    unittest.main()
