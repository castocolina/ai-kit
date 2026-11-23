"""Tracer coverage for lane composition and its CLI."""
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
from ai_kit_spec import capability_block as cb
from ai_kit_spec import cli, execute_dispatch, reviewer_dispatch, runner_dispatch
from ai_kit_spec.runner_dispatch import child_env, review_spec

PI_LINES = [
    'pi\tpi\t["--tools","read,grep,find,ls"]',
    ('cross-ai: capabilities {"write":{"value":"none","label":{"state":"verified",'
     '"source":"from argv"}},"shell":{"value":"no","label":{"state":"verified",'
     '"source":"from argv"}},"skills":{"value":"none","label":{"state":"verified",'
     '"source":"from argv"}},"mcp":{"value":"none","label":{"state":"verified",'
     '"source":"from argv"}},"prompt":{"channel":"stdin","max_bytes":null}}'),
    "cross-ai: setting model=fake/placeholder-model-1 applied",
]
EMPTY_SCAN = {key: {"skills": [], "roots": [], "mcp": [], "mcp_note": None, "notes": []}
              for key in ("pi", "agents")}
UNKNOWN_WINDOW = {"value": None, "label": "unknown", "source": None, "note": None}
MODEL = "fake/placeholder-model-1"


class TestComposeForLane(unittest.TestCase):
    def setUp(self):
        root = tempfile.mkdtemp(dir=os.environ.get("TMPDIR"))
        self.addCleanup(shutil.rmtree, root)
        self.cwd = os.path.join(root, "project")
        home = os.path.join(root, "home")
        binary = os.path.join(root, "bin")
        for path in (self.cwd, home, binary):
            os.makedirs(path)
        self.env = {"PATH": binary, "HOME": home}
        self.spec = review_spec("pi", MODEL, None, 30, cwd=self.cwd)
        self.fake = mock.Mock(return_value=PI_LINES)
        self.seams = cb.ComposeSeams(self.fake, lambda _env, _cwd: EMPTY_SCAN,
                                     lambda *_a: UNKNOWN_WINDOW)
        patcher = mock.patch.object(cb, "guidance_paths", return_value=(None, None, ()))
        patcher.start()
        self.addCleanup(patcher.stop)

    def compose(self, files=()):
        return cb.compose_for_lane(cb.LaneRequest("pi", MODEL, "review", self.cwd, self.spec),
                                   "PROMPT", files, self.env, self.seams)

    def expected(self, lines):
        host = {**EMPTY_SCAN["pi"], "skills": [], "mcp": []}
        return cb.build_block(cb.BlockInput(cb.lane_facts(lines), child_env(env=self.env), host,
                                            [], "review", "pi", MODEL, cwd=self.cwd))

    def test_refusal_spawns_nothing_execute(self):
        record = {"reason": "path_unresolvable", "detail": {}}
        prompt = os.path.join(self.cwd, "prompt")
        with open(prompt, "w", encoding="utf-8") as handle:
            handle.write("TASK")
        for stdout_only in (False, True):
            out, err = io.StringIO(), io.StringIO()
            seams = execute_dispatch.ExecuteSeams(
                compose_fn=lambda *_a: cb.ComposeResult(refusal=record),
                runner_fn=mock.Mock(side_effect=AssertionError("spawned")))
            args = ["dispatch-execute", "--runtime", "pi", "--model", MODEL,
                    "--target-dir", self.cwd, "--prompt-file", prompt, "--timeout", "600",
                    "--files"]
            if stdout_only:
                args.append("--stdout-only")
            with redirect_stdout(out), redirect_stderr(err):
                code = cli.main(args, dispatch_execute_fn=lambda spec, active=seams: (
                    execute_dispatch.dispatch_execute(spec, active)))
            self.assertEqual(code, 65)
            self.assertEqual(out.getvalue(), "")
            self.assertEqual(json.loads(err.getvalue().splitlines()[-1]), record)
            seams.runner_fn.assert_not_called()

    def test_execute_prompt_is_block_then_reinforcement_then_prompt(self):
        compose = mock.Mock(return_value=cb.ComposeResult(block="BLOCK"))
        runner = mock.Mock(return_value=runner_dispatch.RunnerResult(
            0, "", {"status": "ok"}, None, False, ["node"], ""))
        spec = execute_dispatch.ExecuteDispatchSpec(
            {"runtime": "pi", "model": MODEL}, "TASK", self.cwd, 600)
        execute_dispatch.dispatch_execute(spec, execute_dispatch.ExecuteSeams(
            compose_fn=compose, runner_fn=runner,
            build_reinforcement_fn=lambda *_a: "REINFORCE", print_fn=lambda _s: None))
        self.assertEqual(runner.call_args.args[1], "BLOCK\n\nREINFORCE\n\nTASK")
        request, text = compose.call_args.args[:2]
        self.assertEqual(text, "REINFORCE\n\nTASK")
        self.assertEqual(request.role, "execute")
        self.assertEqual(request.runner_spec.mode, "exec")
        self.assertEqual(request.soft_confinement,
                         execute_dispatch.build_soft_confinement_guidance(self.cwd))

    def test_execute_without_files_keeps_the_confinement_sentence(self):
        compose = mock.Mock(side_effect=AssertionError("composed without --files"))
        runner = mock.Mock(return_value=runner_dispatch.RunnerResult(
            0, "", {"status": "ok"}, None, False, ["node"], ""))
        spec = execute_dispatch.ExecuteDispatchSpec(
            {"runtime": "pi", "model": MODEL}, "TASK", self.cwd, 600, files=None)
        execute_dispatch.dispatch_execute(spec, execute_dispatch.ExecuteSeams(
            compose_fn=compose, runner_fn=runner, build_reinforcement_fn=lambda *_a: "REINFORCE",
            build_soft_confinement_fn=lambda target: f"SOFT {target}", print_fn=lambda _s: None))
        self.assertEqual(runner.call_args.args[1], f"REINFORCE\n\nSOFT {self.cwd}\n\nTASK")
        compose.assert_not_called()

    def test_execute_spawn_carries_the_lens_flags(self):
        runner = mock.Mock(return_value=runner_dispatch.RunnerResult(
            0, "", {"status": "ok"}, None, False, ["node"], ""))
        spec = execute_dispatch.ExecuteDispatchSpec(
            {"runtime": "pi", "model": MODEL}, "TASK", self.cwd, 600)
        execute_dispatch.dispatch_execute(spec, execute_dispatch.ExecuteSeams(
            compose_fn=lambda *_a: cb.ComposeResult(skill_names=("lens-a",),
                                                     skill_paths=("/x/lens-a",)),
            runner_fn=runner, print_fn=lambda _s: None))
        self.assertEqual(runner.call_args.args[0].skill_names, ("lens-a",))
        self.assertEqual(runner.call_args.args[0].skill_paths, ("/x/lens-a",))

    def test_pi_review_block_from_fake_argv(self):
        result = self.compose()
        self.assertIsNone(result.refusal)
        self.assertIsNone(result.run_dir)
        self.assertEqual(result.skill_names, ())
        self.assertEqual(result.block, self.expected(PI_LINES))
        self.fake.assert_called_once()

    def test_failed_preview_is_all_unknown_with_reason(self):
        self.fake.return_value = None
        result = self.compose()
        self.assertIsNone(result.refusal)
        self.assertEqual(result.block, self.expected(None))

    def test_capability_block_cli_prints_the_compose_block(self):
        out = io.StringIO()
        with mock.patch.object(cb, "DEFAULT_SEAMS", self.seams), redirect_stdout(out):
            code = cli.main(["capability-block", "--runtime", "pi", "--model", MODEL,
                             "--role", "review", "--cwd", self.cwd], env_fn=lambda: self.env)
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(), self.expected(PI_LINES) + "\n")

    def test_custom_lane_composes_without_print_argv(self):
        self.fake.side_effect = AssertionError("unexpected preview")
        result = cb.compose_for_lane(cb.LaneRequest(None, "fake-custom", "review", self.cwd, None),
                                     "", (), self.env, self.seams)
        expected = cb.build_block(cb.BlockInput(cb.lane_facts([]), child_env(env=self.env),
                                                {"skills": [], "mcp": "unknown"}, [], "review",
                                                "custom", "fake-custom", cwd=self.cwd))
        self.assertEqual(result.block, expected)
        self.assertIsNone(result.refusal)
        self.fake.assert_not_called()

    def test_empty_value_is_rejected_not_joined(self):
        result = self.compose(("", "   "))
        self.assertIsNotNone(result.refusal)
        assert result.refusal is not None
        self.assertEqual(result.refusal["reason"], "path_unresolvable")
        self.assertEqual(len(result.refusal["detail"]["rejections"]), 2)

    def test_missing_files_skips_preview(self):
        self.assertEqual(self.compose(None), cb.ComposeResult())
        self.fake.assert_not_called()

    def test_window_over_and_unknown(self):
        self.seams = self.seams._replace(window_fn=lambda *_: {
            "value": 10, "label": "user-stated", "source": "test", "note": None})
        result = self.compose()
        assert result.refusal is not None
        self.assertEqual(result.refusal["reason"], "prompt_over_window")
        self.assertEqual(result.refusal["detail"]["window"], 10)
        self.seams = self.seams._replace(window_fn=lambda *_: UNKNOWN_WINDOW)
        req = cb.LaneRequest("pi", MODEL, "review", self.cwd, self.spec)
        result = cb.compose_for_lane(req, "x" * 1_000_000, (), self.env, self.seams)
        self.assertIsNone(result.refusal)
        assert result.window is not None
        self.assertIsNone(result.window["value"])

    def test_window_equal_passes(self):
        import math
        first = self.compose()
        size = math.ceil(len(cb.with_block(first.block, "PROMPT").encode()) / 4)
        self.seams = self.seams._replace(window_fn=lambda *_: {**UNKNOWN_WINDOW, "value": size})
        self.assertIsNone(self.compose().refusal)
        self.seams = self.seams._replace(window_fn=lambda *_: {**UNKNOWN_WINDOW, "value": size - 1})
        self.assertIsNotNone(self.compose().refusal)

    def test_control_char_file_refused_with_all_rejections(self):
        result = self.compose(("a" + chr(10) + "b", "c" + chr(0x202E) + "d"))
        assert result.refusal is not None
        self.assertEqual(result.refusal["reason"], "value_control_char")
        self.assertEqual(len(result.refusal["detail"]["rejections"]), 2)
        # In a git checkout (the worktree lookup runs) a NUL is a refusal, never a ValueError.
        subprocess.run(["git", "init", "-q", self.cwd], check=True, capture_output=True)
        result = self.compose(("../outside" + chr(0) + "x",))
        assert result.refusal is not None
        self.assertEqual(result.refusal["reason"], "value_control_char")

    def test_context_form_applied_makes_window_unknown(self):
        seen = []
        self.seams = self.seams._replace(window_fn=lambda *a: seen.append(a[4]) or UNKNOWN_WINDOW)
        for line in ("cross-ai: setting context=fake-ctx applied",
                     "cross-ai: setting context=fake-ctx ignored reason=id_carries",
                     "cross-ai: setting context=fake-ctx ignored reason=no_form", ""):
            self.fake.return_value = [*PI_LINES, line]
            self.compose()
        self.assertEqual(seen, [True, True, False, False])

    def lens_scan(self):
        root = os.path.join(self.cwd, "skills")
        path = os.path.join(root, "lens-a")
        os.makedirs(path)
        with open(os.path.join(path, "SKILL.md"), "w", encoding="utf-8") as handle:
            handle.write("---\nname: lens-a\n---\n" + "x" * 2000)
        host = {**EMPTY_SCAN["pi"], "roots": [root],
                "skills": [{"name": "lens-a", "path": path, "role": "review_lens"}]}
        self.seams = self.seams._replace(scan_fn=lambda *_: {**EMPTY_SCAN, "pi": host})
        return path

    def test_lens_delivered_and_skipped(self):
        path = self.lens_scan()
        self.fake.return_value = [*PI_LINES, "cross-ai: setting skill=lens-a applied form=path"]
        result = self.compose()
        self.assertEqual(result.skill_names, ("lens-a",))
        self.assertEqual(result.skill_paths, (os.path.realpath(path),))
        self.assertEqual(self.fake.call_args.args[0].skill_names, ("lens-a",))
        self.seams = self.seams._replace(window_fn=lambda *_: {**UNKNOWN_WINDOW, "value": 250})
        result = self.compose()
        self.assertIsNone(result.refusal)
        self.assertEqual(result.skill_names, ())
        self.assertIn("lens-a: skipped (over_window)", result.block)

    def test_native_lane_gets_lens_lines_only(self):
        self.lens_scan()
        request = cb.LaneRequest("pi", MODEL, "review", self.cwd, None, native=True)
        result = cb.compose_for_lane(request, "p", (), self.env, self.seams)
        # Lens lines only: no tool claims, no LANE, ACCESS, TOOLS or SETTINGS section.
        self.assertEqual(result.block, "SKILLS\nlens-a: load the skill lens-a by name if your "
                                       "host provides it (unverified)")
        self.assertIsNone(result.refusal)
        self.fake.assert_not_called()

    def test_mcp_file_written_and_cleaned(self):
        binary = os.path.join(self.env["PATH"], "codebase-memory-mcp")
        with open(binary, "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\nexit 0\n")
        os.chmod(binary, 0o755)
        result = self.compose()
        assert result.mcp_config is not None
        assert result.run_dir is not None
        self.assertEqual(os.stat(result.mcp_config).st_mode & 0o777, 0o600)
        self.assertEqual(self.fake.call_args.args[0].mcp_config, result.mcp_config)
        self.assertNotIn(result.run_dir, result.block)
        cb.cleanup(result)
        self.assertFalse(os.path.exists(result.run_dir))

    def test_lens_fits_draft_not_final(self):
        path = self.lens_scan()
        self.fake.return_value = [*PI_LINES, "cross-ai: setting skill=lens-a applied form=path"]
        host = {**EMPTY_SCAN["pi"], "roots": [os.path.dirname(path)],
                "skills": [{"name": "lens-a", "path": path, "role": "review_lens"}]}
        draft = cb.build_block(cb.BlockInput(cb.lane_facts(self.fake.return_value),
                                            child_env(env=self.env), host, [], "review", "pi",
                                            MODEL, cwd=self.cwd))
        # The planner's own count (the runner's prose block): the draft admits the lens, and
        # only the final block, longer by its SKILLS line, pushes it over the window.
        lens_bytes = cb.lens_delivery.check_lens(
            {"name": "lens-a", "path": path, "role": "review_lens"},
            os.path.realpath(self.cwd), [os.path.dirname(path)])["bytes"]
        window = math.ceil((len(cb.with_block(draft, "PROMPT").encode("utf-8")) + lens_bytes) / 4)
        self.seams = self.seams._replace(window_fn=lambda *_: {**UNKNOWN_WINDOW, "value": window})
        result = self.compose()
        self.assertIsNone(result.refusal)
        self.assertEqual(result.skill_names, ())
        self.assertIn("lens-a: skipped (over_window)", result.block)
        self.assertEqual([call.args[0].skill_names for call in self.fake.call_args_list],
                         [(), ("lens-a",)])

    def test_argv_cap_skips_lens(self):
        self.lens_scan()
        base = len(cb.with_block(self.compose().block, "PROMPT").encode("utf-8"))
        lines = list(PI_LINES)
        lines[1] = lines[1].replace('"channel":"stdin","max_bytes":null',
                                    f'"channel":"argv","max_bytes":{base + 100}')
        self.fake.return_value = [*lines, "cross-ai: setting skill=lens-a applied form=path"]
        result = self.compose()
        self.assertIsNone(result.refusal)
        self.assertEqual(result.skill_names, ())
        self.assertIn("lens-a: skipped (over_window)", result.block)

    def test_two_lanes_compose_independently(self):
        self.seams = self.seams._replace(
            print_argv_fn=lambda spec, _env: PI_LINES if spec.runtime == "pi" else ["codex"],
            window_fn=lambda runtime, *_: {**UNKNOWN_WINDOW, "value": 10} if runtime == "pi"
            else UNKNOWN_WINDOW)
        pi = self.compose()
        spec = review_spec("codex", MODEL, None, 30, cwd=self.cwd)
        codex = cb.compose_for_lane(cb.LaneRequest("codex", MODEL, "review", self.cwd, spec),
                                    "PROMPT", (), self.env, self.seams)
        self.assertIsNotNone(pi.refusal)
        self.assertIsNone(codex.refusal)
        self.assertIn("runtime: pi", pi.block)
        self.assertIn("runtime: codex", codex.block)

    def test_other_worktree_document_runs_with_note(self):
        def git(*args):
            subprocess.run(["git", "-c", "gc.auto=0", "-c", "maintenance.auto=false",
                            "-c", "user.name=t", "-c", "user.email=t@e", *args],
                           check=True, capture_output=True)

        git("init", self.cwd)
        git("-C", self.cwd, "commit", "--allow-empty", "-m", "initial")
        second = os.path.join(os.path.dirname(self.cwd), "second")
        git("-C", self.cwd, "worktree", "add", "-b", "second", second)
        doc = os.path.join(second, "doc")
        with open(doc, "w", encoding="utf-8") as handle:
            handle.write("document")
        result = self.compose((doc,))
        self.assertIsNone(result.refusal)
        self.assertIn(f"note: documents from other worktrees: 1 ({os.path.realpath(second)})",
                      result.block)
        # The allowance is for review documents: an execute lane's file there is still outside.
        execute = cb.LaneRequest("pi", MODEL, "execute", self.cwd, self.spec)
        result = cb.compose_for_lane(execute, "PROMPT", (doc,), self.env, self.seams)
        assert result.refusal is not None
        self.assertEqual(result.refusal["reason"], "path_outside_roots")
        other = os.path.join(os.path.dirname(self.cwd), "other")
        git("init", other)
        result = self.compose((os.path.join(other, "doc"),))
        assert result.refusal is not None
        self.assertEqual(result.refusal["reason"], "path_outside_roots")

    def test_learned_framework_profile_is_an_allowed_root(self):
        subprocess.run(["git", "init", "-q", self.cwd], check=True)
        cache = os.path.join(self.env["HOME"], ".claude", "cache")
        profiles = os.path.join(cache, "framework-profiles")
        sibling = os.path.join(cache, "framework-profiles-x")
        outside = os.path.join(os.path.dirname(self.cwd), "outside.md")
        for folder in (profiles, sibling):
            os.makedirs(folder)
        for path in (os.path.join(profiles, "gsd.md"), os.path.join(sibling, "gsd.md"), outside):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("profile")
        link = os.path.join(profiles, "link.md")
        os.symlink(outside, link)
        execute = cb.LaneRequest("pi", MODEL, "execute", self.cwd, self.spec)
        for request in (cb.LaneRequest("pi", MODEL, "review", self.cwd, self.spec), execute):
            result = cb.compose_for_lane(request, "PROMPT", (os.path.join(profiles, "gsd.md"),),
                                         self.env, self.seams)
            self.assertIsNone(result.refusal)
        for refused in (os.path.join(sibling, "gsd.md"), link):
            result = self.compose((refused,))
            assert result.refusal is not None
            self.assertEqual(result.refusal["reason"], "path_outside_roots")
        # A relative HOME gives no cache root, never one under the current directory.
        self.env["HOME"] = "home"
        self.assertIsNone(cb.profile_cache_root(self.env))
        result = self.compose((os.path.join(profiles, "gsd.md"),))
        assert result.refusal is not None
        self.assertEqual(result.refusal["reason"], "path_outside_roots")

    def dispatch_args(self, prompt="PROMPT"):
        reviewers = os.path.join(self.cwd, "reviewers.json")
        prompt_file = os.path.join(self.cwd, "prompt")
        with open(reviewers, "w", encoding="utf-8") as handle:
            json.dump([{"key": "r1", "runtime": "pi", "model": MODEL,
                        "route": "subprocess"}], handle)
        with open(prompt_file, "w", encoding="utf-8") as handle:
            handle.write(prompt)
        return ["dispatch-reviewer", "--reviewers-json", reviewers, "--index", "0",
                "--prompt-file", prompt_file, "--timeout-tiers", "600", "--cwd", self.cwd]

    def dispatch_cli(self, args, **overrides):
        out, err = io.StringIO(), io.StringIO()
        def dispatch(spec, seams):
            return reviewer_dispatch.dispatch_reviewer(spec, seams._replace(**overrides))
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(args, dispatch_reviewer_fn=dispatch, env_fn=lambda: self.env)
        return code, out.getvalue(), err.getvalue()

    def test_missing_file_list_builds_no_block(self):
        self.assertTrue(self.compose(()).block)
        runner = mock.Mock(return_value=runner_dispatch.RunnerResult(
            0, "### Status: approved", {"status": "ok"}, None, False, [], ""))
        self.fake.reset_mock()
        code, out, err = self.dispatch_cli(self.dispatch_args(), compose_seams=self.seams,
                                           runner_tiers_fn=runner)
        self.assertEqual(code, 0)
        self.assertEqual(runner.call_args.args[2], "PROMPT")
        self.fake.assert_not_called()
        self.assertEqual(err.strip(), "ai-kit-spec: no capability block built: no --files given "
                         "(pass --files to get the lane's capability block)")
        self.assertIn("approved", out)

    def test_refusal_spawns_nothing_reviewer(self):
        boom = mock.Mock(side_effect=AssertionError("runner spawned"))
        refusal = cb.ComposeResult(block="B", refusal={"status": "refused",
                                    "reason": "prompt_over_window", "detail": {}})
        for flags in ([], ["--stdout-only"]):
            code, out, err = self.dispatch_cli(self.dispatch_args() + flags + ["--files"],
                                              compose_fn=lambda *_: refusal,
                                              runner_tiers_fn=boom)
            self.assertEqual(code, 65)
            self.assertEqual(out, "")
            self.assertEqual(json.loads(err.splitlines()[-1])["reason"], "prompt_over_window")
        boom.assert_not_called()

    def test_rejected_file_never_spawns(self):
        boom = mock.Mock(side_effect=AssertionError("runner spawned"))
        code, out, err = self.dispatch_cli([*self.dispatch_args(), "--files", "a\nb"],
                                          compose_seams=self.seams, runner_tiers_fn=boom)
        self.assertEqual(code, 65)
        self.assertEqual(out, "")
        rejection = json.loads(err.splitlines()[-1])["detail"]["rejections"][0]
        self.assertEqual(rejection["position"], "files[0]")
        self.assertEqual(rejection["reason"], "value_control_char")
        boom.assert_not_called()

    def test_blank_prompt_is_not_composed(self):
        compose = mock.Mock(side_effect=AssertionError("composed blank prompt"))
        runner = mock.Mock(return_value=runner_dispatch.RunnerResult(
            0, "### Status: approved", {"status": "ok"}, None, False, [], ""))
        code, _, _ = self.dispatch_cli([*self.dispatch_args("\n"), "--files"],
                                       compose_fn=compose, runner_tiers_fn=runner)
        self.assertEqual(code, 0)
        compose.assert_not_called()
        self.assertEqual(runner.call_args.args[2], "\n")

    def test_tool_availability_flag_is_ignored_with_a_note(self):
        runner = mock.Mock(return_value=runner_dispatch.RunnerResult(
            0, "### Status: approved", {"status": "ok"}, None, False, [], ""))
        args = [*self.dispatch_args(), "--tool-availability-json", "not json", "--files"]
        code, _, err = self.dispatch_cli(args, compose_fn=lambda *_: cb.ComposeResult(),
                                         runner_tiers_fn=runner)
        self.assertEqual(code, 0)
        self.assertIn("ai-kit-spec: --tool-availability-json is ignored: the capability block "
                      "resolves tools on the lane's own PATH", err)

    def test_mcp_dir_removed_when_publication_fails(self):
        with (mock.patch.object(cb.lens_delivery, "mcp_pick", return_value=[{"name": "fake"}]),
              mock.patch.object(cb.lens_delivery, "write_mcp_file", side_effect=OSError),
              self.assertRaises(OSError)):
            self.compose()
        self.assertFalse(any(name.startswith("aikit-mcp-") for name in
                             os.listdir(os.environ["TMPDIR"])))
