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
from ai_kit_spec import (
    effort_probe,
    execute_dispatch,
    lane_settings,
    quota,
    reviewer_dispatch,
    runner_dispatch,
    tooling_guidance,
)
from ai_kit_spec.cli import main
from ai_kit_spec.commands import ResolvedReviewer

from tests.cross_ai_selftest import _real_node_executable

RUNTIMES = ("pi", "opencode", "cursor", "codex", "claude", "copilot")


def full(runtime):
    model = "fake/placeholder-model-1" if runtime in ("pi", "opencode") else "placeholder-model-1"
    return runner_dispatch.RunnerSpec(
        runtime, model, "exec", 0, effort="high", context="1m",
        session_id="placeholder-session-1", escalate_runtime=True, escalate_model=True,
    )


def golden(runtime):
    settings = ["--effort", "high", "--context", "1m", "--session-id",
                "placeholder-session-1", "--escalate-runtime", "--escalate-model",
                "--host", "auto"]
    expected = ["--runtime", runtime, "--model", full(runtime).model, "--role", "execute",
                *settings]
    if runtime == "codex":
        expected += ["--codex-sandbox", "workspace-write"]
    return expected


class TestRunnerFlagsGolden(unittest.TestCase):
    def test_full_spec_golden_per_runtime(self):
        for runtime in RUNTIMES:
            with self.subTest(runtime=runtime):
                self.assertEqual(runner_dispatch.runner_flags(full(runtime)), golden(runtime))

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


class TestSkillFlags(unittest.TestCase):
    def test_skill_flags_follow_every_existing_flag(self):
        for base in (full("codex")._replace(service_tier="priority"),
                     full("cursor")._replace(mode="review", cursor_mode="plan")):
            with self.subTest(runtime=base.runtime):
                spec = base._replace(skill_names=("lens-a", "lens-b"),
                    skill_paths=("/fake/skills/lens-a", "/fake/skills/lens-b"),
                    mcp_config="/fake/run/mcp.json")
                self.assertEqual(runner_dispatch.runner_flags(spec),
                    [*runner_dispatch.runner_flags(base),
                        "--skill-name", "lens-a", "--skill-path", "/fake/skills/lens-a",
                        "--skill-name", "lens-b", "--skill-path", "/fake/skills/lens-b",
                        "--mcp-config", "/fake/run/mcp.json"])

    def test_no_skill_fields_is_byte_equal(self):
        for runtime in RUNTIMES:
            with self.subTest(runtime=runtime):
                self.assertEqual(runner_dispatch.runner_flags(full(runtime)), golden(runtime))
        self.assertEqual(runner_dispatch.project_runner_command(full("pi")),
            "node .planning/scripts/cross-ai.mjs --runtime pi --model fake/placeholder-model-1 "
            "--role execute --effort high --context 1m --session-id placeholder-session-1 "
            "--escalate-runtime --escalate-model --host auto")

    def test_unequal_skill_tuples_raise(self):
        spec = full("pi")._replace(skill_names=("lens-a",), skill_paths=())
        with self.assertRaises(ValueError):
            runner_dispatch.runner_flags(spec)

    def test_hook_string_refuses_a_path_with_a_space(self):
        spec = full("pi")._replace(skill_names=("lens-a",),
                                   skill_paths=("/fake/my skills/lens-a",))
        self.assertIsNone(runner_dispatch.project_runner_command(spec))
        command = runner_dispatch.project_runner_command(
            spec._replace(skill_paths=("/fake/skills/lens-a",)))
        assert command is not None
        self.assertTrue(command.endswith(" --skill-name lens-a --skill-path /fake/skills/lens-a"))


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


POOLED = {"usage_limited": True, "pool": "fake-provider:free"}


def _recording_runner():
    specs = []

    def fake(spec, prompt, seams):
        del prompt, seams
        specs.append(spec)
        return runner_dispatch.RunnerResult(0, "Hello world!", None, None, False, ["node"], "")

    return fake, specs


def _resolved(extra):
    return ResolvedReviewer("lane-a", "fake/placeholder-model-1", "", "pi", None, extra)


class TestPoolFlag(unittest.TestCase):
    def test_review_dispatch_argv_carries_the_pool_after_every_flag(self):
        specs = []

        def fake_tiers(spec, tiers, prompt, seams):
            del tiers, prompt, seams
            specs.append(spec)
            return runner_dispatch.RunnerResult(0, "ok", None, None, False, [], "")

        entry = {"key": "lane-a", "model": "fake/placeholder-model-1", "vendor": "",
                 "runtime": "pi", "command": None, "extra": dict(POOLED), "route": "runner"}
        reviewer_dispatch.dispatch_reviewer(
            reviewer_dispatch.ReviewerDispatchSpec(
                reviewer_entry=entry, prompt="Review this.", timeout_tiers=[30],
                tool_availability={}, agents_tooling_path=None),
            seams=reviewer_dispatch.ReviewerSeams(
                runner_tiers_fn=fake_tiers,
                compose_fn=lambda *_a, **_k: reviewer_dispatch.ComposeResult(block="")),
        )
        self.assertEqual(len(specs), 1)
        self.assertEqual(runner_dispatch.runner_flags(specs[0])[-2:],
                         ["--pool", "fake-provider:free"])

    def test_review_probe_argv_carries_the_pool_and_others_do_not(self):
        fake, specs = _recording_runner()
        quota.probe_reviewer_quota(
            _resolved(dict(POOLED)), seams=quota.ProbeSeams(runner_fn=fake, role="review"))
        self.assertEqual(runner_dispatch.runner_flags(specs[0])[-2:],
                         ["--pool", "fake-provider:free"])
        for role in ("execute", ""):
            with self.subTest(role=role):
                other, seen = _recording_runner()
                seams = quota.ProbeSeams(runner_fn=other, role=role)
                quota.probe_reviewer_quota(_resolved(dict(POOLED)), seams=seams)
                self.assertIsNone(seen[0].pool)
                self.assertNotIn("--pool", runner_dispatch.runner_flags(seen[0]))

    def test_check_reviewer_never_passes_the_pool(self):
        fake, specs = _recording_runner()
        with redirect_stdout(io.StringIO()):
            code = main(["check-reviewer", "--key", "lane-a", "--model",
                         "fake/placeholder-model-1", "--runtime", "pi", "--extra-json",
                         json.dumps(POOLED)], runner_fn=fake)
        self.assertEqual(code, 0)
        self.assertEqual(len(specs), 1)
        self.assertIsNone(specs[0].pool)
        self.assertNotIn("--pool", runner_dispatch.runner_flags(specs[0]))
        fake, specs = _recording_runner()
        effort_probe.probe_effort(
            _resolved(dict(POOLED)), "high", "2026-11-20", quota.ProbeSeams(runner_fn=fake),
            preview_fn=lambda spec: [f"cross-ai: setting effort={spec.effort} applied",
                                     f"cross-ai: model-id {spec.model}"])
        self.assertEqual(len(specs), 1)
        self.assertIsNone(specs[0].pool)

    def test_no_pool_flag_otherwise(self):
        for extra in ({"pool": "fake-provider:free"}, {"usage_limited": True},
                      {"usage_limited": True, "pool": "not a pool"}):
            with self.subTest(extra=extra):
                fake, specs = _recording_runner()
                quota.probe_reviewer_quota(
                    _resolved(extra), seams=quota.ProbeSeams(runner_fn=fake, role="review"))
                self.assertIsNone(specs[0].pool)
                self.assertNotIn("--pool", runner_dispatch.runner_flags(specs[0]))
        spec = runner_dispatch.spec_with_effort(
            "pi", "fake/placeholder-model-1", "exec", 30, dict(POOLED))
        self.assertIsNone(spec.pool)

    def test_spec_without_pool_is_byte_equal(self):
        spec = runner_dispatch.review_spec("pi", "fake/placeholder-model-1", {}, 30)
        self.assertEqual(
            runner_dispatch.runner_flags(spec),
            ["--runtime", "pi", "--model", "fake/placeholder-model-1", "--role", "review",
             "--host", "auto"])
        pooled = runner_dispatch.review_spec("pi", "fake/placeholder-model-1", dict(POOLED), 30)
        self.assertIsNone(pooled.pool)


if __name__ == "__main__":
    unittest.main()
