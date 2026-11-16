"""Flow documentation tests: the unit contract and adapter guide, the commit-fold skill text, the
superpowers and spec-discuss adapter steps, and AGENTS.md's ship rule.

Each class pins one document against the code or the other document it must agree with, with a
non-vacuity case where the check could otherwise pass on empty text.
"""

import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

_REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-commit-fold" / "scripts"))


class TestFlowScriptsImport(unittest.TestCase):
    def test_flow_scripts_import(self):
        import flow_git  # noqa: F401
        import flow_pr  # noqa: F401
        import flow_record  # noqa: F401
        import flow_stack  # noqa: F401
        import flow_unit  # noqa: F401
        import fold

        args = fold.build_parser().parse_args(["checkpoint", "--unit", "-"])
        self.assertEqual(args.command, "checkpoint")
        self.assertEqual(args.unit_file, "-")


_REFS = _REPO / "skills" / "ai-kit-commit-fold" / "references"
_SYSTEM_WORDS = ("gsd", "superpowers", "grill-me", "spec-kit")


def _read(path):
    return path.read_text(encoding="utf-8")


def _missing(text, names):
    return [name for name in names if name not in text]


def _system_hits(text):
    lowered = text.lower()
    return [word for word in _SYSTEM_WORDS if word in lowered]


class TestUnitContractDoc(unittest.TestCase):
    def test_contract_names_every_field(self):
        import flow_record

        names = flow_record.CONTRACT_REQUIRED + flow_record.CONTRACT_OPTIONAL
        text = _read(_REFS / "unit-contract.md")
        self.assertEqual(_missing(text, names), [])

    def test_contract_check_catches_a_field_the_doc_lacks(self):
        # Non-vacuity: a field added to the tuple without a doc line is reported.
        import flow_record

        names = flow_record.CONTRACT_REQUIRED + flow_record.CONTRACT_OPTIONAL
        text = _read(_REFS / "unit-contract.md")
        self.assertEqual(_missing(text, (*names, "fake_drift_field")), ["fake_drift_field"])

    def test_neutral_docs_name_no_system(self):
        for name in ("unit-contract.md", "folding-policy.md"):
            text = _read(_REFS / name)
            self.assertEqual(_system_hits(text), [], name)
            self.assertEqual(_system_hits(text + "\nRun the GSD adapter\n"), ["gsd"], name)

    def test_adapter_guide_names_hooks_commands_and_third_system(self):
        text = _read(_REFS / "adapter-guide.md")
        required = (
            "discuss:pre",
            "execute:wave:post",
            "ship:pre",
            "ai-kit-fold start",
            "ai-kit-fold guard",
            "ai-kit-fold ready",
            "Adding a third system",
            "--unit",
            "--checkpoint",
        )
        self.assertEqual(_missing(text, required), [])
        self.assertEqual(_missing(text.replace("ship:pre", ""), ["ship:pre"]), ["ship:pre"])

    def test_adapter_guide_superpowers_steps_in_order(self):
        text = _read(_REFS / "adapter-guide.md")
        steps = (
            "fold.py start --plan",
            "fold.py checkpoint --plan",
            "--final",
            "fold.py ready --plan",
        )
        positions = [text.find(step) for step in steps]
        self.assertTrue(all(pos >= 0 for pos in positions), positions)
        self.assertEqual(positions, sorted(positions))
        self.assertIn("plan_not_carried", text)


_SKILL = _REPO / "skills" / "ai-kit-commit-fold" / "SKILL.md"
_RETIRED_LINES = (
    "Never push, force-push or open a PR",
    "pushing or opening PRs",
    "GSD runs `ai-kit-fold run`",
    "verify:post",
)


def _present(text, phrases):
    return [phrase for phrase in phrases if phrase in text]


class TestCommitFoldSkillText(unittest.TestCase):
    def setUp(self):
        self.skill = _read(_SKILL)

    def test_names_every_flow_command(self):
        import fold

        commands = [f"fold.py {command}" for command in fold._FLOW_HANDLERS]
        self.assertEqual(_missing(self.skill, commands), [])
        # Non-vacuity: a text without one command's line fails the check.
        without_show = self.skill.replace("fold.py show", "fold.py view")
        self.assertEqual(_missing(without_show, commands), ["fold.py show"])

    def test_points_to_both_new_references(self):
        required = ("references/unit-contract.md", "references/adapter-guide.md")
        self.assertEqual(_missing(self.skill, required), [])
        self.assertEqual(
            _missing(self.skill.replace("references/unit-contract.md", "the contract"), required),
            ["references/unit-contract.md"],
        )

    def test_names_gsd_hook_points_and_orchestrator_commands(self):
        required = (
            "discuss:pre",
            "plan:pre",
            "execute:wave:pre",
            "execute:wave:post",
            "ship:pre",
            "ai-kit-fold guard --phase",
            "ai-kit-fold ready --phase",
            "ai-kit-fold boundary-plan --phase",
            "ai-kit-fold boundary-wave",
            "GSD delegates before any wave hook runs",
        )
        self.assertEqual(_missing(self.skill, required), [])
        self.assertEqual(
            _missing(self.skill.replace("ship:pre", "ship"), ("ship:pre",)), ["ship:pre"]
        )
        # Non-vacuity: the cross-AI sentence is the one the orchestrator step relies on.
        without_reason = self.skill.replace("GSD delegates before any wave hook runs", "")
        self.assertEqual(
            _missing(without_reason, ("GSD delegates before any wave hook runs",)),
            ["GSD delegates before any wave hook runs"],
        )

    def test_names_restack_resolution_and_no_gates(self):
        required = ("restack --continue", "restack --abort", "no_gates")
        self.assertEqual(_missing(self.skill, required), [])
        self.assertEqual(
            _missing(self.skill.replace("no_gates", "gate refusal"), ("no_gates",)), ["no_gates"]
        )

    def test_pins_the_consent_and_merge_rules(self):
        # T-29.1-16: the agent asks the owner, never self-grants, never pushes or merges alone.
        required = (
            "ask the owner once",
            "Never grant push consent yourself",
            "Never push without push consent.",
            "Never merge a PR outside the owner-started merge chain",
        )
        self.assertEqual(_missing(self.skill, required), [])
        weakened = self.skill.replace("Never grant push consent yourself", "Grant push consent")
        self.assertEqual(_missing(weakened, required), ["Never grant push consent yourself"])

    def test_retired_fold_only_lines_stay_gone(self):
        # Each retired line, appended back, is found: the check is not vacuous.
        self.assertEqual(_present(self.skill, _RETIRED_LINES), [])
        for line in _RETIRED_LINES:
            with self.subTest(line=line):
                self.assertEqual(_present(self.skill + "\n" + line + "\n", _RETIRED_LINES), [line])


_AGENTS = _REPO / "AGENTS.md"
_SHIP_STEPS = (
    "gates green on the unit branch",
    "an installer dry run and the new hooks against a scratch HOME",
    "main checkout on the unit branch's tip",
    "install and a live re-check",
    "local `main` moves only when the stacked PRs merge",
)
_SHIP_ORDERED = _SHIP_STEPS[:4]


def _workflow(agents_text):
    start = agents_text.find("## Workflow")
    if start < 0:
        return ""
    end = agents_text.find("\n## ", start + 1)
    return agents_text[start:] if end < 0 else agents_text[start:end]


def _ship_rule(agents_text):
    """The Workflow bullet that starts '- Ship a finished unit', with whitespace flattened."""
    for bullet in re.split(r"\n(?=- )", _workflow(agents_text)):
        flat = " ".join(bullet.split())
        if flat.startswith("- Ship a finished unit"):
            return flat
    return ""


def _missing_steps(rule):
    return [step for step in _SHIP_STEPS if step not in rule]


class TestShipRule(unittest.TestCase):
    def setUp(self):
        self.agents = _read(_AGENTS)
        self.rule = _ship_rule(self.agents)

    def test_ship_rule_names_every_step(self):
        self.assertTrue(self.rule, "no Workflow bullet starts '- Ship a finished unit'")
        self.assertEqual(_missing_steps(self.rule), [])

    def test_steps_run_in_order(self):
        self.assertTrue(_in_order(self.rule, _SHIP_ORDERED))
        # Non-vacuity: the same steps in reverse order fail the check.
        self.assertFalse(_in_order(self.rule, tuple(reversed(_SHIP_ORDERED))))

    def test_removing_any_one_step_fails(self):
        for step in _SHIP_STEPS:
            with self.subTest(step=step):
                self.assertEqual(_missing_steps(self.rule.replace(step, "")), [step])

    def test_missing_bullet_fails(self):
        without = self.agents.replace("- Ship a finished unit", "- Ship later")
        self.assertEqual(_ship_rule(without), "")
        self.assertEqual(_missing_steps(_ship_rule(without)), list(_SHIP_STEPS))

    def test_old_merge_every_phase_wording_is_gone(self):
        old = "merge every phase into local main"
        self.assertNotIn(old, self.agents.lower())
        # Non-vacuity: the wording, appended back, is found.
        self.assertIn(old, (self.agents + "\n- " + old + ".\n").lower())


_SP_DIR = _REPO / "skills" / "ai-kit-spec-execute-superpowers"
_SPEC_DISCUSS = _REPO / "skills" / "ai-kit-gsd-spec-discuss" / "SKILL.md"
_SP_SEQUENCE = (
    "fold.py start --plan",
    "fold.py checkpoint --plan",
    '--base "$FOLD_BASE"',
    "--final",
    "fold.py ready --plan",
)


def _in_order(text, phrases):
    positions = [text.find(phrase) for phrase in phrases]
    return all(pos >= 0 for pos in positions) and positions == sorted(positions)


def _spec_section(text):
    start = text.find("## 1. Per phase: spec")
    end = text.find("## 2. Per phase: discuss")
    return text[start:end] if start >= 0 and end > start else ""


class TestAdapterSkillText(unittest.TestCase):
    def setUp(self):
        skill = _read(_SP_DIR / "SKILL.md")
        self.sp = skill + "\n" + _read(_SP_DIR / "references" / "fold-step.md")
        self.spec = _read(_SPEC_DISCUSS)

    def test_superpowers_runs_the_unit_commands_in_order(self):
        self.assertTrue(_in_order(self.sp, _SP_SEQUENCE))
        # Non-vacuity: the reversed sequence is out of order.
        self.assertFalse(_in_order(self.sp, tuple(reversed(_SP_SEQUENCE))))

    def test_superpowers_finishing_step_is_not_used(self):
        phrase = "finishing step does not merge, push or open a PR for this unit"
        flat = " ".join(self.sp.split())
        self.assertIn(phrase, flat)
        # Non-vacuity: the text without the phrase no longer carries it.
        self.assertNotIn(phrase, flat.replace(phrase, ""))

    def test_superpowers_states_that_start_carries_the_planning_commits(self):
        phrase = "carries those local-only commits onto the unit branch"
        flat = " ".join(self.sp.split())
        self.assertIn(phrase, flat)
        self.assertIn("the spec on the plan's `**Spec:**` line", flat)  # the carry rule
        # Non-vacuity: the text without the gap sentence no longer carries it.
        self.assertNotIn(phrase, flat.replace(phrase, ""))

    def test_spec_discuss_starts_the_unit_before_the_spec_commit(self):
        section = _spec_section(self.spec)
        start = section.find("fold.py start --phase")
        self.assertGreaterEqual(start, 0)
        self.assertLess(start, section.find("The workflow commits the SPEC itself"))
        self.assertIn("show the report and stop before any write", section)
        # Non-vacuity: without the start line the section has no start.
        self.assertEqual(
            _spec_section(self.spec.replace("fold.py start --phase", "fold start")).find(
                "fold.py start --phase"),
            -1,
        )

    def test_spec_discuss_goes_on_after_a_non_blocking_refusal(self):
        flat = " ".join(_spec_section(self.spec).split())
        self.assertIn("Still `refused no_trunk`, or `refused no_remote`: blocks nothing", flat)
        self.assertIn("stop the whole run", flat)
        self.assertNotIn("$CWD", self.spec)
        self.assertNotIn("fold-step.md", self.spec)

    def test_spec_discuss_fetches_once_then_ledgers_a_no_trunk_refusal(self):
        flat = " ".join(_spec_section(self.spec).split())
        needles = ("`refused no_trunk`: run `git -C <REPO> fetch` once, then re-run `start`",
                   "Append one ledger line `unit flow off for phase <N>: <reason>`",
                   "show it again in the end report")
        for needle in needles:
            self.assertIn(needle, flat)
        self.assertTrue(_in_order(flat, needles))
        # Non-vacuity: the old silent wording carries none of them.
        self.assertNotIn(needles[0], flat.replace(needles[0], ""))

    def test_spec_discuss_handles_a_proposed_phase_without_a_directory(self):
        flat = " ".join(_spec_section(self.spec).split())
        self.assertIn("`bad_checkpoint: phase dir not found`", flat)
        self.assertIn("then run `start` again; this does not stop the run", flat)
        self.assertLess(flat.index("phase dir not found"), flat.index("Any other refusal"))

    def test_spec_discuss_setup_block_prints_fold_py_and_repo(self):
        text = self.spec[self.spec.index("Resolve this skill's scripts dir"):]
        match = re.search(r"```bash\n(.*?)```", text, re.DOTALL)
        assert match is not None, "no setup block"
        block = "\n".join(line[3:] for line in match.group(1).splitlines()).replace(
            "<absolute path of THIS SKILL.md>", str(_SPEC_DISCUSS))
        # REPO is the git toplevel of the cwd; run in a scratch repo so the check holds where the
        # checkout has no .git (the Docker e2e image copies the tree without it).
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as proj:
            env = {"PATH": os.environ.get("PATH", ""), "HOME": home}
            subprocess.run(["git", "init", "-q", proj], env=env, check=True, timeout=60)
            proc = subprocess.run(["bash", "-c", block], cwd=proj, env=env, text=True,
                                  capture_output=True, check=False, timeout=60)
            want_repo = os.path.realpath(proj)
        lines = dict(line.split("=", 1) for line in proc.stdout.splitlines())
        self.assertEqual(lines["S"], str(_SPEC_DISCUSS.parent / "scripts"), proc.stderr)
        self.assertEqual(lines["FOLD_PY"],
                         str(_REPO / "skills" / "ai-kit-commit-fold" / "scripts" / "fold.py"))
        self.assertEqual(lines["GOAL_MD"],
                         str(_REPO / "skills" / "ai-kit-spec-goal-prompt" / "SKILL.md"))
        self.assertEqual(os.path.realpath(lines["REPO"]), want_repo)


if __name__ == "__main__":
    unittest.main()
