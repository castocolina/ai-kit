"""Tests of tools/check_dogfood.py on temporary roots only (never the repo's `.planning/`)."""
from __future__ import annotations

import ast
import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "skills" / "ai-kit-gsd-curated-config"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import cross_ai_script
from ai_kit_spec.detection import HOST_SIGNAL_ENV_VARS

_SPEC = importlib.util.spec_from_file_location(
    "check_dogfood", REPO_ROOT / "tools" / "check_dogfood.py")
assert _SPEC is not None and _SPEC.loader is not None
check_dogfood = importlib.util.module_from_spec(_SPEC)
sys.modules["check_dogfood"] = check_dogfood
_SPEC.loader.exec_module(check_dogfood)

TEMPLATE = REPO_ROOT / "skills" / "ai-kit-spec-review" / "references" / "cross-ai.mjs"
RUNNER_REL = ".planning/scripts/cross-ai.mjs"


def _artifact() -> dict:
    return {
        "kind": "cross-ai-script",
        "path": RUNNER_REL,
        "template": "cross-ai.mjs",
        "version": 3,
        "config": {
            "runtime": "pi",
            "models": {"pi": "router-env/my-coding"},
            "outer_timeout_s": 1800,
            "router_backed": {"pi": True},
        },
        "choices": {},
        "status": "ok",
        "source": "preset",
        "why": "check-dogfood test",
    }


def _render_copy(root: Path) -> Path:
    """A pristine rendered runner copy in `root`, as ensure-runner writes it."""
    plan = cross_ai_script.plan_script(
        str(root), _artifact(), TEMPLATE.read_bytes(), HOST_SIGNAL_ENV_VARS)
    cross_ai_script.write_script(plan)
    return root / RUNNER_REL


def _write_config(root: Path, command: str | None) -> None:
    (root / ".planning").mkdir(parents=True, exist_ok=True)
    workflow = {} if command is None else {"cross_ai_command": command}
    (root / ".planning" / "config.json").write_text(
        json.dumps({"workflow": workflow}), encoding="utf-8")


def _run_main(argv: list[str]) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = check_dogfood.main(argv)
    return code, out.getvalue()


class TestRunnerCopy(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def skip_args(self) -> list[str]:
        return ["--root", str(self.root), "--template", str(TEMPLATE), "--skip-no-write"]

    def test_pristine_copy_has_no_problem(self):
        _render_copy(self.root)
        problems, _notes = check_dogfood.check_runner_copy(self.root, TEMPLATE)
        self.assertEqual(problems, [])

    def test_one_byte_outside_the_config_block_is_a_problem(self):
        path = _render_copy(self.root)
        data = path.read_bytes()
        parts = cross_ai_script.split_header(data)
        assert parts is not None
        shebang, header, body = parts
        start = body.find(b"// </config>") + len(b"// </config>")
        flipped = body[: start + 5] + bytes([body[start + 5] ^ 1]) + body[start + 6 :]
        path.write_bytes(shebang + b"\n" + header + b"\n" + flipped)
        problems, _notes = check_dogfood.check_runner_copy(self.root, TEMPLATE)
        self.assertTrue(problems)
        code, out = _run_main(self.skip_args())
        self.assertEqual(code, 1)
        self.assertNotIn("check-dogfood: ok", out)

    def test_absent_copy_named_by_config_is_a_problem(self):
        _write_config(self.root, f"node {RUNNER_REL}")
        problems, notes = check_dogfood.check_runner_copy(self.root, TEMPLATE)
        self.assertEqual(notes, ["runner copy absent"])
        self.assertEqual(len(problems), 1)

    def test_absent_copy_without_config_is_only_a_note(self):
        problems, notes = check_dogfood.check_runner_copy(self.root, TEMPLATE)
        self.assertEqual((problems, notes), ([], ["runner copy absent"]))
        code, out = _run_main(self.skip_args())
        self.assertEqual(code, 0)
        self.assertIn("check-dogfood: runner copy absent", out)


_ID_A, _ID_B, _ID_APPLY = check_dogfood.GUARD_TESTS
_SKIP_REASON = "checkout-local gsd-core is 1.18.0; need one of 1.16., 1.17."


def _line(test_id: str, status: str = "ok") -> str:
    return f"{test_id.rsplit('.', 1)[1]} ({test_id}) ... {status}\n"


def _output(**overrides: str) -> str:
    """Verbose child output: every guard test ok unless overridden by id suffix."""
    return "".join(
        _line(test_id, overrides.get(test_id.rsplit(".", 1)[1], "ok"))
        for test_id in check_dogfood.GUARD_TESTS
    )


class TestParseVerbose(unittest.TestCase):
    def test_ok_fail_error_and_both_skip_quote_forms(self):
        text = (
            _line("tests.m.C.test_a") + _line("tests.m.C.test_b", "FAIL")
            + _line("tests.m.C.test_c", "ERROR")
            + _line("tests.m.C.test_d", "skipped 'single quoted'")
            + _line("tests.m.C.test_e", 'skipped "it\'s double quoted"')
        )
        self.assertEqual(check_dogfood.parse_verbose(text), {
            "tests.m.C.test_a": ("ok", ""),
            "tests.m.C.test_b": ("FAIL", ""),
            "tests.m.C.test_c": ("ERROR", ""),
            "tests.m.C.test_d": ("skipped", "single quoted"),
            "tests.m.C.test_e": ("skipped", "it's double quoted"),
        })

    def test_result_after_a_docstring_line(self):
        text = "test_a (tests.m.C.test_a)\nFirst docstring line. ... ok\n"
        self.assertEqual(check_dogfood.parse_verbose(text), {"tests.m.C.test_a": ("ok", "")})

    def test_summary_lines_are_not_results(self):
        text = "FAIL: test_a (tests.m.C.test_a)\n----\nRan 1 test in 0.1s\n\nFAILED (failures=1)\n"
        self.assertEqual(check_dogfood.parse_verbose(text), {})


class TestNoWrite(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        _write_config(self.root, f"node {RUNNER_REL}")
        _render_copy(self.root)

    def check(self, rc: int | None = 0, output=None, calls=(), act=None):
        def run():
            if act:
                act(self.root)
            return rc, _output() if output is None else output, list(calls)

        return check_dogfood.check_no_write(self.root, run)

    def test_clean_run_reports_counts_and_no_problem(self):
        problems, notes = self.check()
        self.assertEqual(problems, [])
        self.assertEqual(notes, ["no-write guard: 3 attempted, 3 executed, 0 skipped"])

    def test_changed_config_is_named_with_the_concurrent_edit_tail(self):
        def act(root):
            with open(root / ".planning" / "config.json", "a", encoding="utf-8") as f:
                f.write(" ")

        problems, _notes = self.check(act=act)
        self.assertEqual(problems, [
            ".planning/config.json changed during a curated-config run "
            "(or was edited meanwhile; re-run make check-dogfood)"])

    def test_added_backup_file_is_reported(self):
        def act(root):
            (root / ".planning" / "config.json.bak-x").write_text("{}", encoding="utf-8")

        problems, _notes = self.check(act=act)
        self.assertEqual(len(problems), 1)
        self.assertIn(".planning/config.json.bak-x added during", problems[0])

    def test_removed_runner_is_reported(self):
        problems, _notes = self.check(act=lambda root: (root / RUNNER_REL).unlink())
        self.assertEqual(len(problems), 1)
        self.assertIn(f"{RUNNER_REL} removed during", problems[0])

    def test_fail_and_error_lines_are_problems(self):
        problems, _notes = self.check(rc=1, output=_output(
            test_tracer_against_real_installed_gsd_tools="FAIL",
            test_apply_golden_plan="ERROR"))
        self.assertIn(f"no-write guard failed: {_ID_A}", problems)
        self.assertIn(f"no-write guard failed: {_ID_APPLY}", problems)

    def test_child_rc_and_timeout_are_problems(self):
        problems, _notes = self.check(rc=3)
        self.assertEqual(problems, ["no-write guard child exited 3"])
        problems, _notes = self.check(rc=None, output="")
        self.assertIn("no-write guard timed out after 600s", problems)

    def test_missing_id_is_a_problem(self):
        problems, notes = self.check(output=_line(_ID_A) + _line(_ID_B))
        self.assertEqual(problems, [f"no-write guard missing result: {_ID_APPLY}"])
        self.assertIn("no-write guard: 3 attempted, 2 executed, 0 skipped", notes)

    def test_tripwire_calls_are_a_problem(self):
        problems, _notes = self.check(calls=["codex --version"])
        self.assertEqual(problems, ["no-write guard host CLI calls: codex --version"])

    def test_skipped_apply_is_counted_apart_and_warned_about(self):
        problems, notes = self.check(
            output=_output(test_apply_golden_plan=f"skipped '{_SKIP_REASON}'"))
        self.assertEqual(problems, [])
        self.assertEqual(notes, [
            f"no-write guard skipped: {_ID_APPLY}: {_SKIP_REASON}",
            "no-write guard: 3 attempted, 2 executed, 1 skipped",
            f"warning: the apply no-write guard did not run ({_SKIP_REASON}); apply writes to "
            "the live project are unguarded until it runs",
        ])

    def test_every_guard_skipped_is_a_problem_for_each_non_apply_guard(self):
        output = "".join(_line(i, f"skipped '{_SKIP_REASON}'") for i in (_ID_A, _ID_B, _ID_APPLY))
        problems, notes = self.check(output=output)
        self.assertEqual(problems, [
            f"no-write guard skipped: {_ID_A}; the live project is unguarded",
            f"no-write guard skipped: {_ID_B}; the live project is unguarded",
        ])
        self.assertIn("no-write guard: 3 attempted, 0 executed, 3 skipped", notes)

    def test_class_level_skip_covers_the_class_tests(self):
        cls_id = _ID_APPLY.rsplit(".", 1)[0]
        output = _line(_ID_A) + _line(_ID_B) + f"setUpClass ({cls_id}) ... skipped 'no node'\n"
        problems, notes = self.check(output=output)
        self.assertEqual(problems, [])
        self.assertIn("no-write guard: 3 attempted, 2 executed, 1 skipped", notes)

    def test_root_other_than_the_checkout_needs_skip_no_write(self):
        with unittest.mock.patch.object(
            check_dogfood, "_run_guard_tests", side_effect=AssertionError("guard child started")
        ):
            code, out = _run_main(["--root", str(self.root), "--template", str(TEMPLATE)])
        self.assertEqual(code, 2)
        self.assertEqual(
            out, "check-dogfood: --root applies to the runner-copy check only; "
            "add --skip-no-write\n")


def _step(command: str) -> dict:
    return {"capId": "ai-kit-commit-fold", "kind": "step", "ref": {"command": command},
            "onError": "skip"}


def _gate(blocking: bool = True, command: str = "node .claude/gsd-core/bin/gsd-tools.cjs "
          "ai-kit-fold ship --phase ${PHASE_NUMBER}") -> dict:
    return {"capId": "ai-kit-commit-fold", "kind": "gate", "blocking": blocking,
            "onError": "halt",
            "check": {"predicate": {"kind": "command-exit-zero", "command": command}}}


def _healthy_hooks() -> dict:
    return {"discuss:pre": [_step("ai-kit-fold start")],
            "execute:wave:post": [_step("ai-kit-fold checkpoint")],
            "ship:pre": [_gate()], "plan:pre": [], "execute:wave:pre": [], "verify:post": []}


class _FakeGsd:
    """Answers the gsd-tools calls check_flow_config makes; records each argv tail."""

    def __init__(self, branching="phase", health=None, caps=None, hooks=None):
        self.branching = branching
        healthy = {"status": "healthy", "errors": [], "warnings": []}
        self.health = healthy if health is None else health
        self.caps = [{"id": "ai-kit-commit-fold"}] if caps is None else caps
        self.hooks = _healthy_hooks() if hooks is None else hooks
        self.calls = []

    def __call__(self, root, *args):
        self.calls.append(args)
        if args[:2] == ("config-get", "git.branching_strategy"):
            out = self.branching
        elif args[:2] == ("validate", "health"):
            out = json.dumps(self.health)
        elif args[:2] == ("capability", "list"):
            out = json.dumps(self.caps)
        else:
            out = json.dumps({"activeHooks": self.hooks.get(args[2], [])})
        return subprocess.CompletedProcess(args=list(args), returncode=0, stdout=out)


class TestFlowConfig(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / ".claude" / "gsd-core" / "bin").mkdir(parents=True)
        (self.root / check_dogfood.GSD_TOOLS_REL).write_text("", encoding="utf-8")

    def check(self, fake):
        return check_dogfood.check_flow_config(self.root, fake)

    def test_healthy_flow_has_no_problem(self):
        self.assertEqual(self.check(_FakeGsd()), ([], []))

    def test_each_drift_form_is_one_named_problem(self):
        hooks = _healthy_hooks()
        cases = {
            "branching": (_FakeGsd(branching="none"), "git.branching_strategy is none"),
            "health": (_FakeGsd(health={"status": "degraded", "errors": [],
                                        "warnings": [{"code": "W019"}]}),
                       "validate health is degraded with warnings W019"),
            "capability": (_FakeGsd(caps=[]), "capability ai-kit-commit-fold is not installed"),
            "capId": (_FakeGsd(hooks={**hooks, "discuss:pre": [
                {**_step("ai-kit-fold start"), "capId": "ai-kit-commit-fold-old"}]}),
                "entry capId ai-kit-commit-fold-old is not ai-kit-commit-fold"),
            "kind": (_FakeGsd(hooks={**hooks, "discuss:pre": [
                {**_step("ai-kit-fold start"), "kind": "gate"}]}),
                "entry kind gate is not step"),
            "command": (_FakeGsd(hooks={**hooks, "execute:wave:post": [
                _step("ai-kit-fold run")]}),
                "step command 'ai-kit-fold run' is not 'ai-kit-fold checkpoint'"),
            "non-blocking ship gate": (_FakeGsd(hooks={**hooks, "ship:pre": [_gate(False)]}),
                                       "ship:pre: gate is not blocking"),
            "entry at plan:pre": (
                _FakeGsd(hooks={**hooks, "plan:pre": [_step("ai-kit-fold start")]}),
                "plan:pre lists a ai-kit-commit-fold entry"),
        }
        for label, (fake, fragment) in cases.items():
            with self.subTest(drift=label):
                problems, _notes = self.check(fake)
                self.assertEqual(len(problems), 1, problems)
                self.assertIn(fragment, problems[0])

    def test_absent_gsd_core_is_only_a_note(self):
        def boom(root, *args):
            raise AssertionError("gsd-tools must not run without a project-local gsd-core")

        empty = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, empty, True)
        self.assertEqual(check_dogfood.check_flow_config(empty, boom),
                         ([], ["flow config not checked: no project-local gsd-core"]))


def missing_guard_tests(test_ids) -> list[str]:
    """The ids that name no `class.method` in their module file (AST only, no import)."""
    missing = []
    for test_id in test_ids:
        *module, cls, method = test_id.split(".")
        path = REPO_ROOT.joinpath(*module).with_suffix(".py")
        found = False
        if path.is_file():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            found = any(
                isinstance(node, ast.ClassDef) and node.name == cls and any(
                    isinstance(item, ast.FunctionDef) and item.name == method for item in node.body)
                for node in tree.body
            )
        if not found:
            missing.append(test_id)
    return missing


class TestGuardTestsExist(unittest.TestCase):
    def test_guard_tests_exist(self):
        self.assertEqual(missing_guard_tests(check_dogfood.GUARD_TESTS), [])

    def test_a_bogus_id_is_flagged(self):
        bogus = (_ID_A.replace("test_tracer", "test_nope"),
                 "tests.test_nope_module.C.test_x")
        self.assertEqual(missing_guard_tests(bogus), list(bogus))


if __name__ == "__main__":
    unittest.main()
