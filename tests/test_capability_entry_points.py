"""Read-only capability summaries at the config-status entry point."""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_spec import capability_block, cli, config_io, execute_dispatch, prompt_guard
from ai_kit_spec.runner_dispatch import RunnerResult

from tests.test_compose_for_lane import EMPTY_SCAN, PI_LINES, UNKNOWN_WINDOW


class TestCapabilityEntryPoints(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.cwd = self.root / "project"
        self.cwd.mkdir()
        self.env = {"HOME": str(self.root / "home"), "XDG_CONFIG_HOME": str(self.root / "xdg")}
        self.path = Path(config_io.cfg_global_path(self.env))
        self.specs = []
        patch = mock.patch.object(capability_block, "resolve_shared_tooling_reference_path",
                                  return_value=None)
        patch.start()
        self.addCleanup(patch.stop)

    def write_config(self, text):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(text, encoding="utf-8")

    def status(self, *args):
        def preview(spec, _env):
            self.specs.append(spec)
            return PI_LINES
        seams = capability_block.ComposeSeams(print_argv_fn=preview)
        out, err = io.StringIO(), io.StringIO()
        with (mock.patch.object(capability_block, "DEFAULT_SEAMS", seams),
              redirect_stdout(out), redirect_stderr(err)):
            code = cli.main(["config-status", "--cwd", str(self.cwd), *args],
                            env_fn=lambda: dict(self.env))
        self.assertEqual(code, 0, err.getvalue())
        return out.getvalue().splitlines()

    def test_check_reviewer_has_capability_key(self):
        def preview(spec, _env):
            self.specs.append(spec)
            return PI_LINES
        seams = capability_block.ComposeSeams(print_argv_fn=preview)
        out = io.StringIO()
        with (mock.patch.object(capability_block, "DEFAULT_SEAMS", seams),
              mock.patch.object(cli.effort_probe, "probe_effort",
                                return_value={"probe": {"available": True}}),
              redirect_stdout(out)):
            code = cli.main(["check-reviewer", "--key", "r1", "--runtime", "pi",
                             "--model", "fake/placeholder-model-1", "--effort", "high"],
                            env_fn=lambda: dict(self.env))
        self.assertEqual(code, 0)
        expected = capability_block.summary_line(capability_block.lane_facts(PI_LINES),
                                                "pi", "fake/placeholder-model-1", "review")
        self.assertEqual(json.loads(out.getvalue())["capability"],
                         "capability pi/fake/placeholder-model-1 review: " + expected)
        self.assertEqual(self.specs[0].effort, "high")

    def test_check_reviewer_native_capability(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(["check-reviewer", "--key", "r1"], env_fn=lambda: dict(self.env))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["capability"],
                         "capability native/r1 review: native lane, no tool claims")

    def check_equal_entry_points(self, role):
        model = "fake/placeholder-model-1"
        prompt = self.cwd / "prompt"
        prompt.write_text("PROMPT", encoding="utf-8")
        reviewers = self.cwd / "reviewers.json"
        reviewers.write_text(json.dumps([{"key": "r1", "runtime": "pi", "model": model,
                                          "route": "subprocess"}]), encoding="utf-8")
        specs = []
        def preview(spec, _env):
            specs.append(spec)
            lines = list(PI_LINES)
            if role == "execute":
                lines[1] = lines[1].replace('"value":"none"', '"value":"unknown"', 1)
            lines[-1] = f"cross-ai: setting model={spec.model} applied"
            return lines
        seams = capability_block.ComposeSeams(preview, lambda *_: EMPTY_SCAN,
                                               lambda *_: UNKNOWN_WINDOW)
        runner = mock.Mock(return_value=RunnerResult(0, "ok", None, None, False, [], ""))
        out = io.StringIO()
        with (mock.patch.object(capability_block, "DEFAULT_SEAMS", seams),
              mock.patch.object(capability_block, "guidance_paths", return_value=(None, None, ())),
              mock.patch.object(capability_block.lens_delivery, "mcp_pick", return_value=[]),
              redirect_stdout(out), redirect_stderr(io.StringIO())):
            code = cli.main(["capability-block", "--runtime", "pi", "--model", model,
                             "--role", role, "--cwd", str(self.cwd), "--files"])
            self.assertEqual(code, 0)
            block = out.getvalue().removesuffix("\n")
            first = specs[-1]
            if role == "review":
                args = ["dispatch-reviewer", "--reviewers-json", str(reviewers), "--index", "0",
                        "--prompt-file", str(prompt), "--timeout-tiers", "600",
                        "--cwd", str(self.cwd), "--files"]
                code = cli.main(args, runner_tiers_fn=runner)
                actual = runner.call_args.args[2]
                expected = "PROMPT"
            else:
                args = ["dispatch-execute", "--runtime", "pi", "--model", model,
                        "--target-dir", str(self.cwd), "--prompt-file", str(prompt),
                        "--timeout", "600", "--files"]
                active = execute_dispatch.ExecuteSeams(
                    runner_fn=runner, compose_seams=seams,
                    build_reinforcement_fn=lambda *_: "R")
                code = cli.main(args, dispatch_execute_fn=lambda spec:
                                execute_dispatch.dispatch_execute(spec, active))
                actual = runner.call_args.args[1]
                expected = "R\n\nPROMPT"
                self.assertIn("NO operating-system-level write confinement", block)
            self.assertEqual(code, 0)
        self.assertEqual(actual, capability_block.with_block(block, expected))
        self.assertEqual(first._replace(timeout_s=0), specs[-1]._replace(timeout_s=0))

    def test_three_entry_points_byte_equal_review(self):
        self.check_equal_entry_points("review")

    def test_three_entry_points_byte_equal_execute(self):
        self.check_equal_entry_points("execute")

    def test_lines_follow_config_order(self):
        self.write_config('[[lanes.review]]\nkey="r1"\nruntime="pi"\n'
                          'model="fake/placeholder-model-1"\neffort="high"\n'
                          '[[lanes.review]]\nkey="r2"\ncommand="placeholder-cli-1 {prompt}"\n'
                          'model="fake-custom"\n[[lanes.execute]]\nkey="e1"\n'
                          'runtime="pi"\nmodel="fake/placeholder-model-2"\n')
        facts = capability_block.lane_facts(PI_LINES)
        custom = capability_block.lane_facts([])
        expected = [
            "capability pi/fake/placeholder-model-1 review: " +
            capability_block.summary_line(facts, "pi", "fake/placeholder-model-1", "review"),
            "capability custom/fake-custom review: " +
            capability_block.summary_line(custom, "custom", "fake-custom", "review"),
            "capability pi/fake/placeholder-model-2 execute: " +
            capability_block.summary_line(facts, "pi", "fake/placeholder-model-2", "execute"),
        ]
        self.assertEqual(self.status()[3:], expected)
        self.assertEqual(self.specs[0].effort, "high")
        self.assertEqual(self.status("--role", "execute")[3:], expected[2:])

    def test_native_lane_line(self):
        self.write_config('[[lanes.review]]\nkey="host-a"\n')
        self.assertEqual(config_io.cfg_resolve(str(self.cwd), self.env, migrate=False)["review"],
                         [{"key": "host-a"}])
        self.assertEqual(self.status()[3:], [
            "capability native/host-a review: native lane, no tool claims"])
        self.write_config('[[lanes.review]]\nkey="bad"\nruntime=7\n')
        self.assertEqual(self.status()[3:], [
            "capability 7/bad review: invalid lane entry: runtime must be a string "
            "and extra a table"])

    def test_control_chars_escaped(self):
        model = "fake/placeholder-model-1"
        self.write_config('[[lanes.review]]\nkey="r1"\nruntime="pi"\n'
                          f'model="{model}\\u001b"\n')
        lines = self.status()
        self.assertEqual(len(lines), 4)
        self.assertIn(prompt_guard.escape_value("fake/placeholder-model-1\x1b"), lines[3])
        self.assertNotIn("\x1b", lines[3])

    def test_no_lanes_no_capability_line(self):
        self.assertEqual(len(self.status()), 3)

    def test_pending_state_prints_no_capability_line(self):
        self.write_config('[[lanes.review]]\nkey="r1"\nruntime="pi"\nmodel="fake-model"\n')
        project = self.cwd / ".aikit" / "config.toml"
        project.parent.mkdir()
        project.write_text('[[lanes.review]]\nkey="local"\ncommand="placeholder-cli-1"\n',
                           encoding="utf-8")
        lines = self.status()
        self.assertEqual(lines[0], "pending")
        self.assertEqual(len(lines), 3)

    def test_config_status_writes_nothing(self):
        self.write_config('[[lanes.review]]\nkey="r1"\nruntime="pi"\nmodel="fake-model"\n')
        before = (self.path.read_bytes(), self.path.stat().st_mtime_ns)
        self.status()
        self.assertEqual(before, (self.path.read_bytes(), self.path.stat().st_mtime_ns))
