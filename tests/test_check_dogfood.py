"""Tests of tools/check_dogfood.py on temporary roots only (never the repo's `.planning/`)."""
from __future__ import annotations

import ast
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

_EDGE_SPEC = importlib.util.spec_from_file_location(
    "edge_floor", REPO_ROOT / "skills" / "ai-kit-gsd-spec-discuss" / "scripts" / "edge_floor.py")
assert _EDGE_SPEC is not None and _EDGE_SPEC.loader is not None
edge_floor = importlib.util.module_from_spec(_EDGE_SPEC)
_EDGE_SPEC.loader.exec_module(edge_floor)

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
_SKIP_REASON = "checkout-local gsd-core is 1.15.0; need 1.16.0 or newer"


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


_BOUNDARY_TEXT = ("ai-kit unit flow (boundary before planning): run node "
                  ".claude/gsd-core/bin/gsd-tools.cjs ai-kit-fold boundary-plan --phase <N>.")


def _contribution(into: str = "planner", text: str = _BOUNDARY_TEXT) -> dict:
    return {"capId": "ai-kit-commit-fold", "kind": "contribution", "into": into,
            "fragment": {"inline": text}, "onError": "skip"}


def _healthy_hooks() -> dict:
    return {"discuss:pre": [_step("ai-kit-fold start")],
            "execute:wave:pre": [_step("ai-kit-fold boundary-wave")],
            "execute:wave:post": [_step("ai-kit-fold checkpoint")],
            "ship:pre": [_gate()], "plan:pre": [_contribution()], "verify:post": []}


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
            "step at plan:pre": (
                _FakeGsd(hooks={**hooks, "plan:pre": [_step("ai-kit-fold boundary-plan")]}),
                "entry kind step is not contribution"),
            "contribution into checker": (
                _FakeGsd(hooks={**hooks, "plan:pre": [_contribution(into="checker")]}),
                "contribution is not into planner"),
            "contribution without boundary-plan": (
                _FakeGsd(hooks={**hooks, "plan:pre": [_contribution(text="ai-kit unit flow")]}),
                "contribution does not run ai-kit-fold boundary-plan"),
            "missing execute:wave:pre step": (
                _FakeGsd(hooks={**hooks, "execute:wave:pre": []}),
                "execute:wave:pre: expected one ai-kit-commit-fold step, found 0"),
            "entry at verify:post": (
                _FakeGsd(hooks={**hooks, "verify:post": [_step("ai-kit-fold start")]}),
                "verify:post lists a ai-kit-commit-fold entry"),
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


_LENS_BRIEF = """# ai-kit lens brief (synthetic)

## Expected lenses

- gsd-ui-researcher: global:impeccable
- gsd-ui-checker: global:impeccable
- gsd-ui-auditor: global:impeccable
- gsd-planner: global:ponytail:ponytail
- gsd-plan-checker: global:ponytail:ponytail
- gsd-code-reviewer: global:ponytail:ponytail-review

## If a lens did not load

Continue without it and name it.

## Unit brief

Synthetic text for the three unit-brief agents.
"""
_LENS = ".planning/lens-brief"
_JEV = "skills/jev-fast-decision"
_BRIEF = ".aikit/brief"
_LENS_SKILLS = {
    "gsd-ui-researcher": ["global:impeccable", _LENS, _JEV],
    "gsd-ui-checker": ["global:impeccable", _LENS, _JEV],
    "gsd-ui-auditor": ["global:impeccable", _LENS, _JEV],
    "gsd-planner": ["global:ponytail:ponytail", _LENS, _JEV, _BRIEF],
    "gsd-plan-checker": ["global:ponytail:ponytail", _LENS, _JEV],
    "gsd-code-reviewer": ["global:ponytail:ponytail-review", _LENS, _JEV],
    "gsd-phase-researcher": [_JEV, _LENS, _BRIEF],
    "gsd-executor": [_JEV, _LENS, _BRIEF],
}


class _LensFake:
    """Answers the three config-get calls check_lens_wiring makes; anything else fails the test."""

    def __init__(self, skills=None, roots=None, review="true"):
        self.skills = dict(_LENS_SKILLS) if skills is None else skills
        self.roots = ["~/.agents/skills"] if roots is None else roots
        self.review = review

    def __call__(self, root, *args):
        if args == ("config-get", "agent_skills"):
            out = json.dumps(self.skills)
        elif args == ("config-get", "agent_skills_security.trusted_global_roots"):
            out = json.dumps(self.roots)
        elif args == ("config-get", "workflow.ui_review", "--raw"):
            out = self.review
        else:
            raise AssertionError(f"unexpected gsd-tools call {args}")
        return subprocess.CompletedProcess(args=list(args), returncode=0, stdout=out)


class TestLensWiring(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        tools = self.root / check_dogfood.GSD_TOOLS_REL
        tools.parent.mkdir(parents=True)
        tools.write_text("", encoding="utf-8")
        brief = self.root / check_dogfood.LENS_BRIEF_REL
        brief.parent.mkdir(parents=True)
        brief.write_text(_LENS_BRIEF, encoding="utf-8")

    def check(self, fake):
        return check_dogfood.check_lens_wiring(self.root, fake)

    def test_healthy_wiring_has_no_problem(self):
        self.assertEqual(self.check(_LensFake()), ([], []))

    def test_missing_lens_brief_is_only_a_note(self):
        (self.root / check_dogfood.LENS_BRIEF_REL).unlink()

        def boom(root, *args):
            raise AssertionError("gsd-tools must not run without the lens brief")

        self.assertEqual(self.check(boom), ([], [
            "lens wiring not checked: no .planning/lens-brief/SKILL.md"]))

    def test_each_drift_form_is_one_named_problem(self):
        cases = {
            "lens missing": (_LensFake({**_LENS_SKILLS, "gsd-ui-checker": [_LENS, _JEV]}),
                             "gsd-ui-checker: lens global:impeccable is not in its list"),
            "lens not first": (_LensFake({**_LENS_SKILLS, "gsd-planner": [
                _JEV, "global:ponytail:ponytail", _LENS, _BRIEF]}),
                "gsd-planner: lens global:ponytail:ponytail is not first"),
            "lens brief not after lens": (_LensFake({**_LENS_SKILLS, "gsd-ui-auditor": [
                "global:impeccable", _JEV, _LENS]}),
                "gsd-ui-auditor: .planning/lens-brief is not right after the lens"),
            "jev missing": (_LensFake({**_LENS_SKILLS, "gsd-plan-checker": [
                "global:ponytail:ponytail", _LENS]}),
                "gsd-plan-checker: skills/jev-fast-decision is missing"),
            "absolute entry": (_LensFake({**_LENS_SKILLS, "gsd-code-reviewer": [
                "global:ponytail:ponytail-review", _LENS, _JEV, "/home/x/skill"]}),
                "entry /home/x/skill is an absolute path"),
            "brief missing": (_LensFake({**_LENS_SKILLS, "gsd-executor": [_JEV, _LENS]}),
                              "gsd-executor: .aikit/brief is missing"),
            "lens brief after brief": (_LensFake({**_LENS_SKILLS, "gsd-phase-researcher": [
                _JEV, _BRIEF, _LENS]}),
                "gsd-phase-researcher: .planning/lens-brief is not before .aikit/brief"),
            "unlisted global entry": (_LensFake({**_LENS_SKILLS, "gsd-debugger": [
                "global:x", _JEV]}),
                "gsd-debugger: global entry global:x is not in the lens brief"),
            "trusted roots": (_LensFake(roots=["/home/u/.agents/skills"]),
                              "trusted_global_roots is ['/home/u/.agents/skills']"),
            "ui_review off": (_LensFake(review="false"),
                              "workflow.ui_review is false, not true"),
        }
        for label, (fake, fragment) in cases.items():
            with self.subTest(drift=label):
                problems, _notes = self.check(fake)
                self.assertEqual(len(problems), 1, problems)
                self.assertIn(fragment, problems[0])


def _fixture_spec(requirements: list[str], rows: list[tuple[str, str, str]]) -> str:
    """A phase SPEC: numbered **bold** requirements, then an Edge Coverage table of `rows`."""
    numbered = "\n".join(f"{n}. **{title}** body text" for n, title in enumerate(requirements, 1))
    table = "\n".join(f"| {cat} | {req} | ✅ covered | {reason} |" for cat, req, reason in rows)
    return (f"# Fixture SPEC\n\n## Requirements\n\n{numbered}\n\n## Edge Coverage\n\n"
            "| Category | Requirement | Status | Resolution / Reason |\n"
            "|----------|-------------|--------|---------------------|\n"
            f"{table}\n")


_EDGE_ONLY_SPEC = "## Edge Coverage\n\n| Category | Requirement |\n"


class TestEdgeFloors(unittest.TestCase):
    def _root(self, specs: dict[str, str], engine: bool = True) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for rel, text in specs.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        if engine:
            engine_path = root / check_dogfood.EDGE_ENGINE_REL
            engine_path.parent.mkdir(parents=True, exist_ok=True)
            engine_path.write_text("// fake engine\n", encoding="utf-8")
        return root

    @staticmethod
    def _fake_run(results: dict[str, tuple[int, str]]):
        calls: list[str] = []

        def run(root: Path, spec_rel: str) -> subprocess.CompletedProcess[str]:
            calls.append(spec_rel)
            code, out = results[spec_rel]
            return subprocess.CompletedProcess(args=[], returncode=code, stdout=out, stderr="")

        return run, calls

    def test_drift_is_named_and_order_is_sorted(self):
        one = ".planning/phases/01-a/01-SPEC.md"
        two = ".planning/phases/02-b/02-SPEC.md"
        root = self._root({
            one: _EDGE_ONLY_SPEC,
            two: _EDGE_ONLY_SPEC,
            ".planning/phases/02-b/02-UI-SPEC.md": _EDGE_ONLY_SPEC,
            ".planning/phases/03-c/.keep": "",
        })
        run, calls = self._fake_run({
            one: (0, '{"ok": true}'),
            two: (1, '{"ok": false, "missing": [["encoding", "R2"]]}'),
        })
        problems, notes = check_dogfood.check_edge_floors(root, run=run,
                                                          which=lambda _name: "/usr/bin/node")
        self.assertEqual(problems,
                         [f"edge floor drift: {two} missing encoding R2"])
        self.assertEqual(notes, [])
        self.assertEqual(calls, [one, two])

    def test_spec_without_edge_section_is_a_note_and_never_runs(self):
        rel = ".planning/phases/01-a/01-SPEC.md"
        root = self._root({rel: "# In progress\n\n## Requirements\n\n1. **x** y\n"})
        run, calls = self._fake_run({})
        problems, notes = check_dogfood.check_edge_floors(root, run=run,
                                                          which=lambda _name: "/usr/bin/node")
        self.assertEqual(problems, [])
        self.assertEqual(notes,
                         [f"edge floor for {rel} not checked: no Edge Coverage section"])
        self.assertEqual(calls, [])

    def test_engine_failure_is_a_named_skip_not_ok(self):
        rel = ".planning/phases/01-a/01-SPEC.md"
        root = self._root({rel: _EDGE_ONLY_SPEC})
        run, _calls = self._fake_run({rel: (2, "")})
        problems, notes = check_dogfood.check_edge_floors(root, run=run,
                                                          which=lambda _name: "/usr/bin/node")
        self.assertEqual(problems, [])
        self.assertEqual(notes, [f"edge floor for {rel} not checked: engine failed closed"])

    def test_missing_prerequisites_are_named_notes(self):
        rel = ".planning/phases/01-a/01-SPEC.md"
        cases = {
            "node not found": (self._root({rel: _EDGE_ONLY_SPEC}), lambda _name: None,
                               "edge floors not checked: node not found"),
            "no engine": (self._root({rel: _EDGE_ONLY_SPEC}, engine=False),
                          lambda _name: "/usr/bin/node",
                          "edge floors not checked: no project-local gsd-core engine"),
            "no phases": (self._root({}), lambda _name: "/usr/bin/node",
                          "edge floors not checked: no .planning/phases"),
        }
        for label, (root, which, note) in cases.items():
            with self.subTest(label):
                run, calls = self._fake_run({})
                problems, notes = check_dogfood.check_edge_floors(root, run=run, which=which)
                self.assertEqual((problems, notes, calls), ([], [note], []))

    def test_real_engine_passes_full_table_and_names_a_removed_row(self):
        engine = _real_edge_engine()
        if engine is None or shutil.which("node") is None:
            self.skipTest("node or the gsd-core edge-probe.cjs engine not installed")
        titles = ["alpha rule", "beta rule"]
        bare = _fixture_spec(titles, [])
        floor = edge_floor.run_engine(engine, edge_floor.requirements(bare))
        rows = [(item["category"], item["requirement_id"], "covered by fixture")
                for item in floor["items"]]
        full = _fixture_spec(titles, rows)
        root = self._root({".planning/phases/01-a/01-SPEC.md": full}, engine=False)
        link = root / ".claude" / "gsd-core" / "bin"
        link.mkdir(parents=True)
        os.symlink(os.path.dirname(engine), link / "lib")
        rel = ".planning/phases/01-a/01-SPEC.md"
        self.assertEqual(check_dogfood.check_edge_floors(root)[0], [])
        removed = rows[0]
        partial = _fixture_spec(titles, rows[1:])
        (root / rel).write_text(partial, encoding="utf-8")
        problems, _notes = check_dogfood.check_edge_floors(root)
        self.assertEqual(len(problems), 1)
        self.assertIn(f"{removed[0]} {removed[1]}", problems[0])


_JDG04_PROBLEM = "Phase {} names a SKILL.md but no success criterion cites JDG-04"


def _phase(number: str, names_skill: bool = True, criteria: str | None = "Plain criterion.",
           requirements: str = "JDG-01") -> str:
    """One ROADMAP `### Phase N:` block; criteria None omits the success-criteria marker."""
    goal = "Edit `skills/x/SKILL.md`." if names_skill else "Edit the tools."
    text = (f"### Phase {number}: Title {number}\n\n**Goal:** {goal}\n\n"
            f"**Requirements**: {requirements}\n\n")
    if criteria is not None:
        text += f"**Success Criteria** (what must be TRUE):\n\n1. {criteria}\n\n"
    return text + "**Plans**: 1 plan\n\n"


def _roadmap(*blocks: str) -> str:
    """A roadmap with a Progress section, the Phase Details blocks and a Backlog entry that
    names a SKILL.md and no JDG-04, which the scan must never read."""
    return ("# Roadmap\n\n## Progress\n\nnone\n\n## Phase Details\n\n" + "".join(blocks)
            + "## Backlog\n\n### Phase 999.9: B\n\n**Goal:** Edit `skills/x/SKILL.md`.\n\n"
            "**Success Criteria** (what must be TRUE):\n\n1. Nothing.\n")


class TestJdg04Citations(unittest.TestCase):
    def _root(self, roadmap: str | None) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        if roadmap is not None:
            (root / ".planning").mkdir()
            (root / ".planning" / "ROADMAP.md").write_text(roadmap, encoding="utf-8")
        return root

    def test_skill_phase_without_citation_is_flagged_and_backlog_is_skipped(self):
        root = self._root(_roadmap(_phase("33", criteria="Plain criterion.")))
        self.assertEqual(check_dogfood.check_jdg04_citations(root),
                         ([_JDG04_PROBLEM.format("33")], []))

    def test_adding_the_citation_clears_the_problem(self):
        root = self._root(_roadmap(_phase("33", criteria="Plain criterion.")))
        self.assertEqual(len(check_dogfood.check_jdg04_citations(root)[0]), 1)
        (root / ".planning" / "ROADMAP.md").write_text(
            _roadmap(_phase("33", criteria="Meets the bar (JDG-04).")), encoding="utf-8")
        self.assertEqual(check_dogfood.check_jdg04_citations(root), ([], []))

    def test_phases_up_to_32_are_not_checked_but_32_1_is(self):
        root = self._root(_roadmap(_phase("32"), _phase("31.1"), _phase("32.1")))
        self.assertEqual(check_dogfood.check_jdg04_citations(root),
                         ([_JDG04_PROBLEM.format("32.1")], []))

    def test_look_alike_ids_and_requirements_line_do_not_count(self):
        root = self._root(_roadmap(
            _phase("33", criteria="Cites JDG-040 and jdg-04."),
            _phase("34", criteria="Plain criterion.", requirements="JDG-04"),
        ))
        self.assertEqual(check_dogfood.check_jdg04_citations(root),
                         ([_JDG04_PROBLEM.format("33"), _JDG04_PROBLEM.format("34")], []))

    def test_skill_phase_without_criteria_marker_is_flagged_and_non_skill_is_not(self):
        root = self._root(_roadmap(
            _phase("35", criteria=None),
            _phase("36", names_skill=False, criteria=None),
        ))
        self.assertEqual(check_dogfood.check_jdg04_citations(root),
                         ([_JDG04_PROBLEM.format("35")], []))

    def test_every_offender_is_reported_in_roadmap_order(self):
        root = self._root(_roadmap(_phase("33"), _phase("33.1"), _phase("35")))
        self.assertEqual(check_dogfood.check_jdg04_citations(root), ([
            _JDG04_PROBLEM.format("33"),
            _JDG04_PROBLEM.format("33.1"),
            _JDG04_PROBLEM.format("35"),
        ], []))

    def test_missing_roadmap_and_missing_section_are_named_notes(self):
        self.assertEqual(check_dogfood.check_jdg04_citations(self._root(None)), ([], [
            "JDG-04 citations not checked: no .planning/ROADMAP.md"]))
        root = self._root("# Roadmap\n\n## Progress\n\nnone\n")
        self.assertEqual(check_dogfood.check_jdg04_citations(root), ([], [
            "JDG-04 citations not checked: no ## Phase Details section"]))


class TestJudgeRecords(unittest.TestCase):
    """check_judge_records (32 D-07) with a fake check; no real .planning/judge is read."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="check-dogfood-judge-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.real = check_dogfood._judge_loop()

    def _fake(self, result=None, error=None):
        calls = []

        def fake_check(root, records, opts):
            calls.append((root, records, opts))
            if error is not None:
                raise error
            return result

        module = unittest.mock.Mock(check=fake_check, CheckOptions=self.real.CheckOptions,
                                    JudgeLoopError=self.real.JudgeLoopError)
        return module, calls

    def test_a_missing_folder_is_a_note_and_nothing_is_loaded(self):
        def never_loaded():
            raise AssertionError("the judge tool was loaded without .planning/judge")

        self.assertEqual(check_dogfood.check_judge_records(self.root, load=never_loaded),
                         ([], ["judge records not checked: no .planning/judge"]))

    def test_problems_and_notes_are_prefixed_and_the_checker_gets_the_folder(self):
        (self.root / ".planning" / "judge").mkdir(parents=True)
        module, calls = self._fake(result=(["line"], ["p1"], ["n1"]))
        found = check_dogfood.check_judge_records(self.root, load=lambda: module)
        self.assertEqual(found, (["judge records: p1"], ["judge records: n1"]))
        self.assertEqual(calls, [(self.root, self.root / ".planning" / "judge",
                                  self.real.CheckOptions())])

    def test_a_refused_input_is_a_problem_not_a_traceback(self):
        (self.root / ".planning" / "judge").mkdir(parents=True)
        module, _calls = self._fake(error=self.real.JudgeLoopError("bad inputs"))
        self.assertEqual(check_dogfood.check_judge_records(self.root, load=lambda: module),
                         (["judge records: bad inputs"], []))

    def test_an_unexpected_record_error_is_a_problem_not_a_traceback(self):
        (self.root / ".planning" / "judge").mkdir(parents=True)
        module, _calls = self._fake(error=KeyError("findings"))
        self.assertEqual(check_dogfood.check_judge_records(self.root, load=lambda: module),
                         (["judge records: KeyError: 'findings'"], []))


def _real_edge_engine() -> str | None:
    """The edge-probe.cjs engine that edge_floor.find_engine resolves for this checkout, or None."""
    return edge_floor.find_engine(os.environ, str(REPO_ROOT), None)


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
