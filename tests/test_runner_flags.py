"""37-12: Python call vocabulary (SPEC R1, D-23): golden flags and builder parity."""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-gsd-curated-config"))

from ai_kit_gsd_curated_config import cross_ai_build
from ai_kit_spec import execute_dispatch, lane_settings, runner_dispatch, tooling_guidance
from ai_kit_spec.cli import main

from tests.cross_ai_selftest import _real_node_executable

RUNTIMES = ("pi", "opencode", "cursor", "codex", "claude", "copilot")


def full(runtime):
    model = "fake/placeholder-model-1" if runtime in ("pi", "opencode") else "placeholder-model-1"
    return runner_dispatch.RunnerSpec(
        runtime, model, "exec", 0, effort="high", context="1m",
        session_id="placeholder-session-1", escalate_runtime=True, escalate_model=True,
    )


class TestRunnerFlagsGolden(unittest.TestCase):
    def test_full_spec_golden_per_runtime(self):
        settings = ["--effort", "high", "--context", "1m", "--session-id",
                    "placeholder-session-1", "--escalate-runtime", "--escalate-model",
                    "--host", "auto"]
        for runtime in RUNTIMES:
            with self.subTest(runtime=runtime):
                spec = full(runtime)
                expected = ["--runtime", runtime, "--model", spec.model, "--role", "execute",
                            *settings]
                if runtime == "codex":
                    expected += ["--codex-sandbox", "workspace-write"]
                self.assertEqual(runner_dispatch.runner_flags(spec), expected)

    def test_unset_settings_emit_nothing(self):
        spec = runner_dispatch.RunnerSpec("opencode", "fake/placeholder-model-1", "review", 0)
        expected = ["--runtime", "opencode", "--model", spec.model, "--role", "review"]
        self.assertEqual(runner_dispatch.runner_flags(spec), [*expected, "--host", "auto"])
        self.assertEqual(runner_dispatch.runner_flags(spec._replace(host=None)), expected)
        self.assertEqual(runner_dispatch.runner_flags(spec._replace(context="")),
                         [*expected, "--context", "", "--host", "auto"])

    def test_role_property(self):
        for mode, role in (("exec", "execute"), ("review", "review")):
            with self.subTest(mode=mode):
                self.assertEqual(full("codex")._replace(mode=mode).role, role)

    def test_route_and_runtime_knobs_keep_their_places(self):
        for runtime, kwargs, suffix in (
            ("codex", {"service_tier": "priority"},
             ["--host", "auto", "--codex-service-tier", "priority"]),
            ("cursor", {"cursor_mode": "plan"}, ["--host", "auto", "--cursor-mode", "plan"]),
            ("pi", {"route": "router"}, ["--route-pi", "router", "--host", "auto"]),
        ):
            with self.subTest(runtime=runtime):
                spec = full(runtime)._replace(mode="review", effort=None, context=None,
                    session_id=None, escalate_runtime=False, escalate_model=False, **kwargs)
                self.assertEqual(
                    runner_dispatch.runner_flags(spec),
                    ["--runtime", runtime, "--model", spec.model, "--role", "review", *suffix],
                )


class TestTemplateAcceptsPythonFlags(unittest.TestCase):
    def test_every_python_flag_parses(self):
        # The real node, never a launcher shim that may run itself again under the scratch HOME.
        node = _real_node_executable()
        if node is None:
            self.skipTest("no real node executable on PATH")
        template = tooling_guidance.resolve_cross_ai_template_path()
        assert template is not None
        with tempfile.TemporaryDirectory() as tmp:
            env = runner_dispatch.child_env()
            env.update(HOME=tmp, AI_KIT_REFUSE_REAL_HOME="1")
            env.pop("HERDR_ENV", None)
            for runtime in RUNTIMES:
                with self.subTest(runtime=runtime):
                    argv = runner_dispatch.build_runner_argv(full(runtime)._replace(timeout_s=600),
                                                             template, node)
                    result = subprocess.run([*argv, "--print-argv"], capture_output=True,
                                            text=True, timeout=60, stdin=subprocess.DEVNULL,
                                            cwd=tmp, env=env)
                    self.assertEqual(result.returncode, 0, result.stderr[:400])
                    self.assertNotIn("unknown argument", result.stderr, result.stderr[:400])


class TestEscalationThroughLaneSettings(unittest.TestCase):
    def test_review_spec_reads_the_lane_flags(self):
        for extra, expected in ((None, False), ({}, False), ({"escalate_runtime": True}, True)):
            spec = runner_dispatch.review_spec("pi", "fake/placeholder-model-1", extra, 30)
            self.assertEqual(spec.escalate_runtime, expected)
            self.assertFalse(spec.escalate_model)
            flags = runner_dispatch.runner_flags(spec)
            self.assertEqual("--escalate-runtime" in flags, expected)
            self.assertNotIn("--escalate-model", flags)

    def test_both_flags_runtime_first(self):
        spec = runner_dispatch.review_spec("pi", "fake/placeholder-model-1",
            {"escalate_runtime": True, "escalate_model": True}, 30)
        flags = runner_dispatch.runner_flags(spec)
        self.assertTrue(spec.escalate_runtime and spec.escalate_model)
        self.assertLess(flags.index("--escalate-runtime"), flags.index("--escalate-model"))

    def test_non_boolean_flag_is_a_named_error(self):
        with self.assertRaisesRegex(lane_settings.LaneSettingError,
                                    "<unknown>: 'escalate_model' must be a boolean"):
            runner_dispatch.review_spec("pi", "fake/placeholder-model-1",
                                        {"escalate_model": "yes"}, 30)

    def test_execute_spec_reads_the_candidate_flags(self):
        candidate = {"runtime": "codex", "model": "placeholder-model-1", "escalate_model": True}
        with tempfile.TemporaryDirectory() as tmp:
            spec = execute_dispatch._runner_spec(candidate,
                execute_dispatch.ExecuteDispatchSpec(candidate, "do it", tmp, 30))
            self.assertTrue(spec.escalate_model)
            self.assertEqual((spec.cwd, spec.mode), (tmp, "exec"))
            self._check_session_flags(spec)

    def _check_session_flags(self, spec):
        self.assertIsNone(spec.context)
        self.assertIsNone(spec.session_id)
        flags = runner_dispatch.runner_flags(spec)
        self.assertNotIn("--context", flags)
        self.assertNotIn("--session-id", flags)
        flags = runner_dispatch.runner_flags(
            spec._replace(context="1m", session_id="placeholder-session-1"))
        self.assertIn("--context", flags)
        self.assertIn("--session-id", flags)

    def test_integer_effort_becomes_a_string_and_spec_has_no_ignored_field(self):
        spec = runner_dispatch.review_spec("pi", "fake/placeholder-model-1", {"effort": 3}, 30)
        self.assertEqual(spec.effort, "3")
        self.assertEqual(runner_dispatch.runner_flags(spec)[6:8], ["--effort", "3"])
        # 37-14: the runner reports an ignored setting itself; the spec no longer carries one.
        self.assertNotIn("ignored", runner_dispatch.RunnerSpec._fields)

    def test_other_knobs_unchanged(self):
        spec = runner_dispatch.review_spec("codex", "placeholder-model-1",
            {"effort": "high", "service_tier": "priority", "cursor_mode": "plan"}, 30, cwd=".")
        self.assertEqual((spec.effort, spec.service_tier, spec.cursor_mode, spec.cwd),
                         ("high", "priority", "plan", "."))
        self._check_session_flags(spec)


class TestHookTokens(unittest.TestCase):
    def test_every_flag_token_is_a_hook_token(self):
        for runtime in ("codex", "copilot", "cursor", "opencode", "pi"):
            for token in runner_dispatch.runner_flags(full(runtime)):
                with self.subTest(runtime=runtime, token=token):
                    self.assertIsNotNone(runner_dispatch.HOOK_TOKEN_RE.fullmatch(token))

    def test_hook_string_carries_role_and_host(self):
        spec = runner_dispatch.RunnerSpec("opencode", "fake/placeholder-model-1", "exec", 0)
        self.assertEqual(runner_dispatch.project_runner_command(spec),
                         "node .planning/scripts/cross-ai.mjs --runtime opencode --model "
                         "fake/placeholder-model-1 --role execute --host auto")


class TestBuilderParity(unittest.TestCase):
    def test_build_command_and_hook_builder_emit_one_flag_list(self):
        for runtime in ("codex", "copilot", "cursor", "opencode", "pi"):
            with self.subTest(runtime=runtime):
                model = full(runtime).model
                out = io.StringIO()
                with redirect_stdout(out), redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["build-command", "--runtime", runtime,
                                           "--role", "execute"]), 0)
                argv = json.loads(out.getvalue())["argv"]
                actual = [model if x == "{model}" else x for x in argv[2:argv.index("--timeout")]]
                command = cross_ai_build.build_execution_command(runtime, model)
                assert command is not None
                self.assertEqual(actual, command.split()[2:])

    def test_build_command_defaults_to_review(self):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["build-command", "--runtime", "codex"]), 0)
        argv = json.loads(out.getvalue())["argv"]
        self.assertEqual(argv[argv.index("--role") + 1], "review")
        self.assertNotIn("--codex-sandbox", argv)


if __name__ == "__main__":
    unittest.main()
