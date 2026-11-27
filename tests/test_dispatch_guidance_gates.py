"""Caller-fed gate and commit-guard guidance: builders, composition order and the
superpowers dispatch path (fakes only)."""

import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-execute-superpowers")
)

from ai_kit_spec import (
    capability_block,
    dispatch_guidance,
    execute_dispatch,
    runner_dispatch,
    runner_facts,
)
from ai_kit_spec_superpowers import cli, dispatch_injection

LABEL = "fake-runtime, model placeholder-model-1"
MODEL = "fake/placeholder-model-1"
GATES = "make test-unit\nmake arch-test\n"
GUARD = "Commit only the task's files."
CONFIG = (".aikit/config.toml",)
FORMAT = "Reply with FORMAT-MARKER-9."
BAD_OWNER_CONFIGS = (
    "",
    ".",
    "conf/",
    "../x.toml",
    "a/../x.toml",
    "it's.toml",
    ":!x.toml",
    "*.toml",
    "a?.toml",
    "[ab].toml",
    "_x.toml",
    "@x/y.toml",
    "a\\b.toml",
    "a\nb.toml",
)


def isolated_dispatch_env(test: unittest.TestCase, root: str) -> None:
    """Scratch HOME and XDG_CACHE_HOME and no stored runner fact, so a real dispatch layer
    never reads the caller's cache."""
    env = mock.patch.dict(
        os.environ,
        {"HOME": os.path.join(root, "home"), "XDG_CACHE_HOME": os.path.join(root, "cache")},
    )
    env.start()
    test.addCleanup(env.stop)
    fact = mock.patch.object(runner_facts, "stored_fact", return_value=None)
    fact.start()
    test.addCleanup(fact.stop)


class TestGateAndGuardBuilders(unittest.TestCase):
    def test_gates_framed_once(self):
        out = dispatch_guidance.build_gates_guidance(GATES)
        self.assertEqual(
            out, dispatch_guidance.GATES_FRAME + "\n\nmake test-unit\nmake arch-test"
        )
        self.assertEqual(out.count(dispatch_guidance.GATES_FRAME), 1)

    def test_empty_gates_give_nothing(self):
        for value in (None, "", "  \n"):
            self.assertEqual(dispatch_guidance.build_gates_guidance(value), "")

    def test_guard_with_paths(self):
        out = dispatch_guidance.build_commit_guard_guidance(GUARD, CONFIG)
        self.assertTrue(out.startswith(dispatch_guidance.GUARD_FRAME))
        self.assertIn(GUARD, out)
        self.assertIn(
            "`git status --porcelain -- ':(top)' ':(top,exclude,literal).aikit/config.toml'`", out
        )

    def test_guard_without_paths_has_no_clean_tree_sentence(self):
        out = dispatch_guidance.build_commit_guard_guidance(GUARD, ())
        self.assertIn(GUARD, out)
        self.assertNotIn("git status", out)
        self.assertNotIn("clean-tree", out)

    def test_supported_path_excludes_only_that_file(self):
        out = dispatch_guidance.build_commit_guard_guidance(None, CONFIG)
        match = re.search(r"`(git status --porcelain -- [^`]+)`\.$", out)
        self.assertIsNotNone(match, out)
        assert match is not None
        git = shutil.which("git")
        if git is None:
            self.skipTest("git not found")
        with tempfile.TemporaryDirectory() as root:
            subprocess.run([git, "init", "-q", root], check=True, capture_output=True)
            for rel in ("other.txt", "sub/x.txt", ".aikit/config.toml"):
                path = os.path.join(root, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write("x\n")
            for cwd in (root, os.path.join(root, "sub")):
                with self.subTest(cwd=os.path.relpath(cwd, root)):
                    proc = subprocess.run(["bash", "-c", match.group(1)], cwd=cwd, check=False,
                                          capture_output=True, text=True)
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    lines = proc.stdout.splitlines()
                    self.assertTrue(any(line.endswith("other.txt") for line in lines), lines)
                    self.assertTrue(any("sub/" in line for line in lines), lines)
                    self.assertFalse(any("config.toml" in line for line in lines), lines)

    def test_paths_only_still_give_the_guard(self):
        out = dispatch_guidance.build_commit_guard_guidance(None, CONFIG)
        self.assertTrue(out.startswith(dispatch_guidance.GUARD_FRAME))
        self.assertIn("':(top,exclude,literal).aikit/config.toml'", out)

    def test_empty_guard_gives_nothing(self):
        self.assertEqual(dispatch_guidance.build_commit_guard_guidance(None, ()), "")
        self.assertEqual(dispatch_guidance.build_commit_guard_guidance(None), "")

    def test_builder_refuses_an_unsupported_owner_config(self):
        for value in BAD_OWNER_CONFIGS:
            with self.subTest(value=value):
                with self.assertRaises(ValueError) as ctx:
                    dispatch_guidance.build_commit_guard_guidance(GUARD, (value,))
                self.assertEqual(str(ctx.exception),
                                 f"ai-kit-spec: --owner-config: unsupported path {value}")
                with self.assertRaises(ValueError):
                    dispatch_guidance.build_dispatch_reinforcement_guidance(
                        LABEL, None, None, GUARD, (value,))

    def test_default_composition_is_unchanged(self):
        expected = "\n\n".join(
            [
                dispatch_guidance.build_model_selection_override_guidance(LABEL),
                dispatch_guidance.build_incremental_progress_guidance(),
                dispatch_guidance.build_failure_reporting_guidance(),
            ]
        )
        out = dispatch_guidance.build_dispatch_reinforcement_guidance(LABEL, None)
        self.assertEqual(out, expected)

    def test_order_is_fixed(self):
        out = dispatch_guidance.build_dispatch_reinforcement_guidance(
            LABEL, "FORMAT", GATES, GUARD, CONFIG
        )
        failure = out.index(dispatch_guidance.build_failure_reporting_guidance())
        gates = out.index(dispatch_guidance.GATES_FRAME)
        guard = out.index(dispatch_guidance.GUARD_FRAME)
        self.assertLess(failure, gates)
        self.assertLess(gates, guard)
        self.assertLess(guard, out.index("FORMAT"))
        self.assertTrue(out.endswith("FORMAT"))


class TestDispatchPath(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        isolated_dispatch_env(self, self.tmp)
        self.project = os.path.join(self.tmp, "project")
        os.makedirs(self.project)
        self.files = {}
        for name, text in (
            ("prompt.txt", "<objective>task</objective>"),
            ("format.md", FORMAT),
            ("gates.txt", GATES),
            ("guard.txt", GUARD),
        ):
            self.files[name] = os.path.join(self.tmp, name)
            with open(self.files[name], "w", encoding="utf-8") as f:
                f.write(text)
        self.compose = mock.Mock(return_value=capability_block.ComposeResult(block="BLOCK"))
        self.runner = mock.Mock(
            return_value=runner_dispatch.RunnerResult(
                0, "", {"status": "ok"}, None, False, ["node"], ""
            )
        )

    def _dispatch(self, extra):
        def wrapped(request, guidance=None):
            seams = dispatch_injection.SuperpowersDispatchSeams(
                dispatch_execute_fn=lambda spec: execute_dispatch.dispatch_execute(
                    spec,
                    execute_dispatch.ExecuteSeams(
                        compose_fn=self.compose,
                        runner_fn=self.runner,
                        print_fn=lambda _s: None,
                    ),
                ),
                env_fn=lambda: {"HOME": self.tmp},
            )
            return dispatch_injection.dispatch_superpowers_task(
                request, guidance, seams=seams
            )

        err = io.StringIO()
        with redirect_stderr(err):
            rc = cli.main(
                [
                    "dispatch-task",
                    "--injection-json",
                    json.dumps(
                        {"mode": "external_cli", "runtime": "pi", "model": MODEL, "key": "r1"}
                    ),
                    "--prompt-file",
                    self.files["prompt.txt"],
                    "--target-dir",
                    self.project,
                    "--heartbeat-interval",
                    "60",
                    "--timeout",
                    "900",
                    "--format-block-file",
                    self.files["format.md"],
                    "--report-file",
                    os.path.join(self.tmp, "report.md"),
                    *extra,
                ],
                dispatch_superpowers_task_fn=wrapped,
                detect_tool_availability_fn=lambda: {},
                resolve_agents_tooling_path_fn=lambda: None,
                cbm_registered_fn=lambda _: False,
                stdout=io.StringIO(),
            )
        return rc, err.getvalue()

    def test_dispatch_task_composes_both_blocks_once_in_order(self):
        rc, _err = self._dispatch(
            [
                "--gates-file",
                self.files["gates.txt"],
                "--guard-file",
                self.files["guard.txt"],
                "--owner-config",
                ".aikit/config.toml",
            ]
        )
        self.assertEqual(rc, 0)
        self.assertEqual(self.runner.call_count, 1)
        prompt = self.runner.call_args.args[1]
        gates_frame = dispatch_guidance.GATES_FRAME
        guard_frame = dispatch_guidance.GUARD_FRAME
        self.assertEqual(prompt.count(gates_frame), 1)
        self.assertEqual(prompt.count(guard_frame), 1)
        self.assertLess(prompt.index(gates_frame), prompt.index(guard_frame))
        self.assertLess(prompt.index(guard_frame), prompt.index(FORMAT))
        self.assertLess(prompt.index(FORMAT), prompt.index("<objective>task</objective>"))
        self.assertIn("':(top,exclude,literal).aikit/config.toml'", prompt)

    def test_dispatch_task_without_flags_has_no_block(self):
        rc, _err = self._dispatch([])
        self.assertEqual(rc, 0)
        self.assertEqual(self.runner.call_count, 1)
        prompt = self.runner.call_args.args[1]
        self.assertNotIn(dispatch_guidance.GATES_FRAME, prompt)
        self.assertNotIn(dispatch_guidance.GUARD_FRAME, prompt)

    def test_unreadable_inputs_exit_2(self):
        missing = os.path.join(self.tmp, "missing.txt")
        rc, err = self._dispatch(["--gates-file", missing])
        self.assertEqual(rc, 2)
        self.assertEqual(err, f"ai-kit-spec: --gates-file: unreadable file {missing}\n")
        bad = os.path.join(self.tmp, "bad.txt")
        with open(bad, "wb") as f:
            f.write(b"\xff\xfe")
        rc, err = self._dispatch(["--guard-file", bad])
        self.assertEqual(rc, 2)
        self.assertEqual(err, f"ai-kit-spec: --guard-file: unreadable file {bad}\n")
        self.assertEqual(self.runner.call_count, 0)

    def test_unsupported_owner_config_exits_2(self):
        absolute = os.path.join(self.tmp, "x.toml")
        for value in (*BAD_OWNER_CONFIGS, absolute):
            with self.subTest(value=value):
                rc, err = self._dispatch(["--owner-config", value])
                self.assertEqual(rc, 2)
                self.assertEqual(err, f"ai-kit-spec: --owner-config: unsupported path {value}\n")
                self.assertEqual(self.runner.call_count, 0)
        rc, _err = self._dispatch(["--owner-config", ".aikit/config.toml"])
        self.assertEqual(rc, 0)
        self.assertEqual(self.runner.call_count, 1)


class TestPrintGuidance(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.gates = os.path.join(self.tmp, "gates.txt")
        self.guard = os.path.join(self.tmp, "guard.txt")
        with open(self.gates, "w", encoding="utf-8") as f:
            f.write(GATES)
        with open(self.guard, "w", encoding="utf-8") as f:
            f.write(GUARD)

    def _run(self, extra):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stderr(err):
            rc = cli.main(["print-guidance", *extra], stdout=out)
        return rc, out.getvalue(), err.getvalue()

    def test_prints_both_blocks(self):
        rc, out, _err = self._run(
            ["--gates-file", self.gates, "--guard-file", self.guard,
             "--owner-config", ".aikit/config.toml"])
        self.assertEqual(rc, 0)
        expected = (dispatch_guidance.build_gates_guidance(GATES) + "\n\n"
                    + dispatch_guidance.build_commit_guard_guidance(GUARD, CONFIG) + "\n")
        self.assertEqual(out, expected)

    def test_paths_only_prints_the_guard(self):
        rc, out, _err = self._run(["--owner-config", ".aikit/config.toml"])
        self.assertEqual(rc, 0)
        self.assertEqual(
            out, dispatch_guidance.build_commit_guard_guidance(None, CONFIG) + "\n")

    def test_nothing_prints_nothing(self):
        rc, out, _err = self._run([])
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_input_errors_exit_2(self):
        missing = os.path.join(self.tmp, "missing.txt")
        bad = os.path.join(self.tmp, "bad.txt")
        with open(bad, "wb") as f:
            f.write(b"\xff\xfe")
        cases = [
            (["--gates-file", missing],
             f"ai-kit-spec: --gates-file: unreadable file {missing}\n"),
            (["--guard-file", missing],
             f"ai-kit-spec: --guard-file: unreadable file {missing}\n"),
            (["--guard-file", bad], f"ai-kit-spec: --guard-file: unreadable file {bad}\n"),
        ]
        for value in (*BAD_OWNER_CONFIGS, os.path.join(self.tmp, "x.toml")):
            cases.append((["--owner-config", value],
                          f"ai-kit-spec: --owner-config: unsupported path {value}\n"))
        for extra, message in cases:
            with self.subTest(extra=extra):
                rc, out, err = self._run(extra)
                self.assertEqual(rc, 2)
                self.assertEqual(err, message)
                self.assertEqual(out, "")


class TestGuidanceEdges(unittest.TestCase):
    def test_braces_and_markup_stay_verbatim(self):
        text = "run {x} and <b>{y}</b>"
        self.assertTrue(dispatch_guidance.build_gates_guidance(text).endswith(text))
        self.assertTrue(dispatch_guidance.build_commit_guard_guidance(text).endswith(text))

    def test_tail_grep_line_is_framed_not_rewritten(self):
        line = "uv run pyright | tail -n 3 | grep -q '0 errors'"
        out = dispatch_guidance.build_gates_guidance(line)
        self.assertIn(line, out)
        self.assertEqual(out.count("judge it by its exit code alone"), 1)

    def test_new_frames_name_no_framework(self):
        texts = (
            dispatch_guidance.GATES_FRAME,
            dispatch_guidance.GUARD_FRAME,
            dispatch_guidance.build_gates_guidance("x"),
            dispatch_guidance.build_commit_guard_guidance("y", (".aikit/config.toml",)),
        )
        words = ("GSD", "gsd", "superpowers", "Superpowers", "Spec Kit", "OpenSpec", "BMAD",
                 "Kiro")
        for word in words:
            for text in texts:
                self.assertNotIn(word, text)

    def test_module_source_names_no_framework(self):
        source = pathlib.Path(dispatch_guidance.__file__).read_text(encoding="utf-8")
        for word in ("GSD", "gsd-core", "superpowers", "Superpowers", "Spec Kit", "OpenSpec",
                     "BMAD", "Kiro"):
            self.assertNotIn(word, source)


SKILL_DIR = (
    pathlib.Path(__file__).resolve().parents[1] / "skills" / "ai-kit-spec-execute-superpowers"
)


class TestGuidanceDocs(unittest.TestCase):
    def setUp(self):
        self.skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.external = (SKILL_DIR / "references" / "dispatch-external-cli.md").read_text(
            encoding="utf-8"
        )

    def test_compose_holds_no_task_block(self):
        compose = self.external.split("## Compose", 1)[1].split("## Status contract", 1)[0]
        self.assertNotIn("<task", compose)

    def test_coverage_na_is_explained(self):
        for needle in ("coverage=n/a", "adds none", "would be counted"):
            self.assertIn(needle, self.external)

    def test_dispatch_passes_the_owner_config(self):
        blocks = re.findall(r"```bash\n(.*?)```", self.external, re.DOTALL)
        hits = [b for b in blocks if "dispatch-task --injection-json" in b]
        self.assertEqual(len(hits), 1)
        self.assertIn("GUIDE_ARGS=(--owner-config .aikit/config.toml)", hits[0])
        self.assertIn('"${GUIDE_ARGS[@]}"', hits[0])

    def test_one_recipe_in_skill(self):
        self.assertEqual(self.skill.count("the one input recipe"), 1)
        blocks = re.findall(r"```bash\n(.*?)```", self.skill, re.DOTALL)
        self.assertTrue(any('print-guidance "${GUIDE_ARGS[@]}"' in b for b in blocks))
        self.assertNotIn("else from the plan's verify lines", self.external)

    def test_recipe_keys_on_the_task_scalar(self):
        lines = [x for x in self.skill.splitlines() if "the one input recipe" in x]
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertIn("the loaded scalar `GUIDANCE_READY` is not `$TASK_N`", line)
        self.assertIn("launches only when that block exits 0", line)
        self.assertIn("a session-fallback dispatch included", line)
        self.assertNotIn("RESUME_FOUND=0", line)

    def test_fresh_start_clears_the_task_scalar(self):
        check = (SKILL_DIR / "references" / "config-check.md").read_text(encoding="utf-8")
        lines = [x for x in check.splitlines() if "GUIDANCE_READY=" in x]
        self.assertEqual(len(lines), 1)
        self.assertLess(check.index(lines[0]), check.index('if [ "$RESUMED" = 1 ] &&'))
        recipe = next(x for x in self.skill.splitlines() if "the one input recipe" in x)
        self.assertIn("a fresh start of the plan clears `GUIDANCE_READY`", recipe)
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("bash not found")
        with tempfile.TemporaryDirectory() as tmp:
            scalars = os.path.join(tmp, "scalars.env")
            for resumed, expected in (("0", ""), ("1", "2")):
                with self.subTest(resumed=resumed):
                    with open(scalars, "w", encoding="utf-8") as handle:
                        handle.write("TASK_N=2\nGUIDANCE_READY=2\n")
                    subprocess.run([bash, "-c", lines[0]], check=True, env={
                        "PATH": os.environ.get("PATH", ""), "RESUMED": resumed,
                        "SCALARS": scalars})
                    values = {}
                    with open(scalars, encoding="utf-8") as handle:
                        for line in handle.read().splitlines():
                            name, _sep, value = line.partition("=")
                            values[name] = value
                    self.assertEqual(values["GUIDANCE_READY"], expected)
            missing = os.path.join(tmp, "absent.env")
            subprocess.run([bash, "-c", lines[0]], check=True, env={
                "PATH": os.environ.get("PATH", ""), "RESUMED": "0", "SCALARS": missing})
            self.assertFalse(os.path.exists(missing))


REFS_DIR = SKILL_DIR / "references"
SHIM_SOURCE = """import json, os, sys
with open(os.environ["AI_KIT_FAKE_SHIM_LOG"], "a", encoding="utf-8") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
code = int(os.environ.get("AI_KIT_FAKE_SHIM_EXIT", "0"))
if code == 0:
    print("{}")
else:
    print("ai-kit-spec: fake input error", file=sys.stderr)
sys.exit(code)
"""
INJECTION = {"mode": "external_cli", "runtime": "pi", "model": MODEL, "key": "r1"}


def _doc_block(path: pathlib.Path, needle: str) -> str:
    text = path.read_text(encoding="utf-8")
    hits = [b for b in re.findall(r"```bash\n(.*?)```", text, re.DOTALL) if needle in b]
    assert len(hits) == 1, (path.name, needle, len(hits))
    return hits[0]


class TestGuidanceUniformity(unittest.TestCase):
    """The documented blocks run for real against a recording stub shim; each recorded
    dispatch call is replayed in-process through the real dispatch layers."""

    def setUp(self):
        bash_bin = shutil.which("bash")
        if bash_bin is None:
            self.skipTest("bash not found")
        self.bash_bin: str = bash_bin
        self.root = tempfile.mkdtemp(prefix="guidance-uniform-")
        self.addCleanup(shutil.rmtree, self.root, True)
        isolated_dispatch_env(self, self.root)
        self.project = os.path.join(self.root, "project")
        self.run_dir = os.path.join(self.root, "run")
        os.makedirs(self.project)
        os.makedirs(self.run_dir)
        self.log = os.path.join(self.root, "shim.log")
        self.shim = os.path.join(self.root, "shim.py")
        self.scalars = os.path.join(self.root, "scalars.env")
        self.state = os.path.join(self.root, "state.json")
        self.exit_file = os.path.join(self.root, "d", "base.exit")
        self.prompt_file = os.path.join(self.root, "prompt.txt")
        self._write(self.shim, SHIM_SOURCE)
        self._write(self.prompt_file, "<objective>task</objective>")
        self._write(os.path.join(self.root, "format.md"), FORMAT)
        self._write_injection()
        self.native = _doc_block(SKILL_DIR / "SKILL.md", 'print-guidance "${GUIDE_ARGS[@]}"')
        self.dispatch = _doc_block(
            REFS_DIR / "dispatch-external-cli.md", "dispatch-task --injection-json"
        )
        self.restore = _doc_block(REFS_DIR / "state-management.md", "state file does not match")

    @staticmethod
    def _write(path, text):
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def _write_injection(self):
        self._write(os.path.join(self.run_dir, "INJECTION_JSON.json"), json.dumps(INJECTION))

    def _gate_files(self):
        self._write(os.path.join(self.run_dir, "gates.txt"), GATES)
        self._write(os.path.join(self.run_dir, "guard.txt"), GUARD)

    def _bash(self, block, **env):
        base = {
            "RUN_DIR": self.run_dir,
            "SHIM": self.shim,
            "AI_KIT_FAKE_SHIM_LOG": self.log,
            "CWD": self.project,
            "PROMPT_FILE": self.prompt_file,
            "FORMAT_BLOCK_FILE": os.path.join(self.root, "format.md"),
            "REPORT_FILE": os.path.join(self.root, "report.md"),
            "DISPATCH_BASE": os.path.join(self.root, "d", "base"),
        }
        return subprocess.run(
            [self.bash_bin, "-c", block],
            cwd=self.root,
            capture_output=True,
            text=True,
            env={**os.environ, **base, **env},
            timeout=60,
            check=False,
        )

    def _recorded(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def _replay_dispatch(self, argv):
        compose = mock.Mock(return_value=capability_block.ComposeResult(block="BLOCK"))
        runner = mock.Mock(
            return_value=runner_dispatch.RunnerResult(
                0, "", {"status": "ok"}, None, False, ["node"], ""
            )
        )

        def wrapped(request, guidance=None):
            seams = dispatch_injection.SuperpowersDispatchSeams(
                dispatch_execute_fn=lambda spec: execute_dispatch.dispatch_execute(
                    spec,
                    execute_dispatch.ExecuteSeams(
                        compose_fn=compose, runner_fn=runner, print_fn=lambda _s: None
                    ),
                ),
                env_fn=lambda: {"HOME": self.root},
            )
            return dispatch_injection.dispatch_superpowers_task(
                request, guidance, seams=seams
            )

        with redirect_stderr(io.StringIO()):
            rc = cli.main(
                argv,
                dispatch_superpowers_task_fn=wrapped,
                detect_tool_availability_fn=lambda: {},
                resolve_agents_tooling_path_fn=lambda: None,
                cbm_registered_fn=lambda _: False,
                stdout=io.StringIO(),
            )
        self.assertEqual(rc, 0)
        self.assertEqual(runner.call_count, 1)
        return runner.call_args.args[1]

    def _replay_print(self, argv):
        out = io.StringIO()
        with redirect_stderr(io.StringIO()):
            rc = cli.main(argv, stdout=out)
        self.assertEqual(rc, 0)
        text = out.getvalue()
        self.assertTrue(text.endswith("\n"))
        return text[:-1]

    def _exit_code(self):
        with open(self.exit_file, encoding="utf-8") as f:
            return f.read().strip()

    def _dispatch_and_replay(self, mode, objective, expected):
        proc = self._bash(self.dispatch, REPORT_MODE=mode)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._exit_code(), "0")
        argv = self._recorded()[-1]
        self.assertEqual(argv[0], "dispatch-task")
        self.assertEqual(argv[argv.index("--report-mode") + 1], mode)
        prompt = self._replay_dispatch(argv)
        self.assertIn(objective, prompt)
        self.assertIn(expected, prompt)
        self.assertEqual(prompt.count(dispatch_guidance.GATES_FRAME), 1)
        self.assertEqual(prompt.count(dispatch_guidance.GUARD_FRAME), 1)
        self.assertNotIn("<task", prompt)

    def _state(self, **extra):
        state = {
            "framework": "superpowers",
            "plan_path": "p.md",
            "task_index": "2",
            "fix_round": 1,
            "excluded_keys": [],
            "reasons": {},
            "last_dispatched_key": "r1",
            "escalation_anchor_key": "",
            "injection_json": INJECTION,
        }
        state.update(extra)
        self._write(self.state, json.dumps(state))

    def _restore(self):
        return self._bash(
            self.restore,
            RESUME_STATE_PATH=self.state,
            PLAN_FILE="p.md",
            TASK_N="2",
            SCALARS=self.scalars,
        )

    def _scalar_values(self):
        values = {}
        with open(self.scalars, encoding="utf-8") as f:
            for line in f:
                name, sep, value = line.rstrip("\n").partition("=")
                if sep:
                    values[name] = value
        return values

    def test_every_path_composes_the_native_print(self):
        self._gate_files()
        before = {n: pathlib.Path(self.run_dir, n).read_bytes() for n in ("gates.txt", "guard.txt")}
        proc = self._bash(self.native)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        first = self._recorded()[0]
        self.assertEqual(first[0], "print-guidance")
        for item in ("--gates-file", "--guard-file", "--owner-config", ".aikit/config.toml"):
            self.assertIn(item, first)
        expected = self._replay_print(first)
        self._dispatch_and_replay("write", "<objective>task</objective>", expected)
        self._write(self.prompt_file, "<objective>task\nfinding 1</objective>")
        self._dispatch_and_replay("append", "finding 1", expected)
        self._state()
        os.remove(os.path.join(self.run_dir, "INJECTION_JSON.json"))
        proc = self._restore()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.run_dir, "INJECTION_JSON.json")))
        self._dispatch_and_replay("append", "finding 1", expected)
        self.assertEqual(len(self._recorded()), 4)
        for name, data in before.items():
            self.assertEqual(pathlib.Path(self.run_dir, name).read_bytes(), data)

    def test_unpinned_resume_passes_the_recorded_files_to_the_dispatch(self):
        self._write(self.scalars, "TASK_N=2\nFIX_ROUND=0\n")
        self._state(fix_round=0, last_dispatched_key="", injection_json=None)
        os.remove(os.path.join(self.run_dir, "INJECTION_JSON.json"))
        proc = self._restore()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("GUIDANCE_READY", self._scalar_values())
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "INJECTION_JSON.json")))
        self._gate_files()
        with open(self.scalars, "a", encoding="utf-8") as f:
            f.write("GUIDANCE_READY=2\n")
        self._write_injection()
        proc = self._bash(self.dispatch, REPORT_MODE="write")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._exit_code(), "0")
        argv = self._recorded()[-1]
        self.assertIn("--gates-file", argv)
        self.assertIn("--guard-file", argv)

    def test_pinned_resume_keeps_the_task_scalar(self):
        self._write(self.scalars, "TASK_N=2\nGUIDANCE_READY=2\n")
        self._state()
        proc = self._restore()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._scalar_values()["GUIDANCE_READY"], "2")

    def test_native_block_fails_when_print_fails(self):
        self._gate_files()
        proc = self._bash(self.native, AI_KIT_FAKE_SHIM_EXIT="2")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("ai-kit-spec: fake input error", proc.stderr)

    def test_without_files_only_the_owner_config_guard_appears(self):
        proc = self._bash(self.native)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = self._bash(self.dispatch, REPORT_MODE="write")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._exit_code(), "0")
        native_argv, dispatch_argv = self._recorded()
        for argv in (native_argv, dispatch_argv):
            self.assertIn("--owner-config", argv)
            self.assertIn(".aikit/config.toml", argv)
            self.assertNotIn("--gates-file", argv)
            self.assertNotIn("--guard-file", argv)
        printed = self._replay_print(native_argv)
        prompt = self._replay_dispatch(dispatch_argv)
        self.assertEqual(prompt.count(dispatch_guidance.GUARD_FRAME), 1)
        self.assertNotIn(dispatch_guidance.GATES_FRAME, prompt)
        self.assertIn(printed, prompt)


if __name__ == "__main__":
    unittest.main()
