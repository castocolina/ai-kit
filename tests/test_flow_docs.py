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


_BRANCHES = _REPO / "skills" / "ai-kit-gsd-spec-discuss" / "references" / "branches.md"
_HAND_MOVES = (
    "git switch",
    "git checkout",
    "branch -f",
    "git reset",
    "update-ref",
    "git branch -D",
)
# Action cells copied from plan 39.2-05 Task 1, keyed by the start of the symptom cell.
_EXPECTED_ACTIONS = {
    "paused restack": (
        "Follow the fold skill's cascade-conflict steps: resolve only the listed files, then "
        "`restack --continue --note <path>=<how>`; when the paused command was a `start`, "
        "re-run that `start` with its `guard` and branch check after the continue succeeds, "
        "before any write. Or `restack --abort` (it returns every branch to its tip at "
        "command entry) and stop."
    ),
    "`stale_lease`": (
        "A push inside `start`'s catch-up failed or was not allowed. Show the report to the "
        "owner and stop; never force or push by hand."
    ),
    "inserted phase": (
        "Ask the owner. Number it after the top open unit; there is no insert-below command."
    ),
    "a phase's documents": (
        "Run `start --phase <N>` and `guard --phase <N>` for the owning unit and read them "
        "there; never copy files between branches by hand."
    ),
    "`gsd_branch_mismatch`": (
        "From `branch_preflight.py`: GSD's phase branch differs from the unit branch. Stop "
        "before the first `start`; change nothing and write no config. Show both names; the "
        "owner aligns `git.phase_branch_template` or the branching strategy."
    ),
    "`stale_parent`": (
        "The newest unmerged unit's branch is gone. Show the report to the owner and stop "
        "the run. Never append a `unit flow off` line for it and never recreate the branch."
    ),
    "`unrecorded_head`": (
        "HEAD is an unrecorded branch with commits the trunk lacks. Show the listed commits "
        "to the owner and stop; the owner moves them or switches branch, then re-run."
    ),
    "`restack_pending`": (
        "A restack is paused. Resolve it with the fold skill's cascade-conflict steps "
        "(`restack --continue --note <path>=<how>`), or `restack --abort`, then re-run the "
        "refused command once (a `start` again with its `guard` and branch check). When a "
        "later restack pass was refused without a conflict, `restack --continue` refuses "
        "`restack_not_paused`: run `restack --abort` (it restores every branch and the record "
        "to the command-entry state), fix the cause the refusal named, then re-run the "
        "refused command once."
    ),
    "`detached_head`": (
        "HEAD is detached. Show the report to the owner and wait; after the owner checks out "
        "a branch, retry `start --phase <N>` once. A second `detached_head`: stop."
    ),
    "`no_trunk`": (
        "From `start`: run `git -C <REPO> fetch` once, then re-run `start`; still refused: "
        "append the ledger line `unit flow off for phase <N>: no_trunk` and continue on the "
        "current branch (SKILL.md §1). From `restack`: run `git -C <REPO> fetch` once and "
        "retry `restack` once; still refused: show the report and stop (the commits stay on "
        "their owner unit)."
    ),
    "`no_remote`": (
        "From `start`: append the ledger line `unit flow off for phase <N>: no_remote` and "
        "continue on the current branch. From `restack`: show the report and stop."
    ),
    "`dirty_tree`": (
        "From `start` or `restack`: run the branch check first. Only when "
        "`git -C <REPO> branch --show-current` prints the owner unit's branch of every "
        "modified file this step wrote, commit those files and retry the refused command "
        "once. A modified file whose owner unit is not checked out, or any file this step "
        "did not write: show it to the owner and stop; never commit, stash or discard it."
    ),
    "`branch_in_worktree`": (
        "Another worktree holds the branch. Ask the owner to switch it away and wait. Then, "
        "from `start`: retry it once; from `restack`: run `restack --abort` (it returns "
        "every branch to its tip at command entry), then retry plain `restack` once."
    ),
}


def _contract_reasons():
    text = _read(_REFS / "unit-contract.md")
    start = text.find("## Reason codes (refused)")
    end = text.find("and every fold", start)
    return re.findall(r"`([a-z_]+)`", text[start:end])


def _recipe_section(text):
    start = text.find("## Recipe")
    end = text.find("\n## ", start + 1) if start >= 0 else -1
    return text[start:end] if start >= 0 and end > start else ""


def _recipe_rows(text):
    rows = {}
    for line in _recipe_section(text).splitlines():
        if not line.startswith("| ") or line.startswith("| Refusal") or line.startswith("|---"):
            continue
        cells = line.split("|")
        action = cells[2].strip()
        for name in re.findall(r"`([a-z_]+)`", cells[1]):
            rows[name] = action
    return rows


def _never_list(text):
    start = text.find("## Reasons that never reach spec-discuss")
    end = text.find("\n## ", start + 1) if start >= 0 else -1
    part = text[start:end] if start >= 0 and end > start else ""
    return re.findall(r"`([a-z_]+)`", part)


def _uncovered(text, reasons):
    rows = _recipe_rows(text)
    never = set(_never_list(text))
    return [reason for reason in reasons if not rows.get(reason) and reason not in never]


def _symptom_cells(text):
    return {
        line.split("|")[1].strip(): line.split("|")[2].strip()
        for line in _recipe_section(text).splitlines()
        if line.startswith("| ") and not line.startswith("| Refusal")
    }


def _row_mismatches(text):
    cells = _symptom_cells(text)
    bad = []
    for key, want in _EXPECTED_ACTIONS.items():
        got = [action for symptom, action in cells.items() if symptom.startswith(key)]
        if got != [want]:
            bad.append(key)
    return bad


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


class TestSpecDiscussBranchRules(unittest.TestCase):
    def setUp(self):
        self.spec = _read(_SPEC_DISCUSS)
        self.flat = " ".join(self.spec.split())

    def test_branch_checks_run_before_the_first_start(self):
        needles = (
            "Branch checks, right after the range is known and before the first `fold.py start`",
            "show --all --repo <REPO>",
            "branch_preflight.py",
            "adding ` --ws <name>` when the run is workstream-scoped",
            "move no branch, edit no stack record, write no config",
        )
        self.assertTrue(_in_order(self.flat, needles))
        self.assertLess(
            self.flat.index("branch_preflight.py"), self.flat.index("query phase.mvp-mode <N>"))
        self.assertLess(
            self.flat.index("confirm or trim the proposed range"),
            self.flat.index("Branch checks, right after the range is known"))
        self.assertNotIn("write no config", self.flat.replace("write no config", ""))

    def test_where_am_i_runs_before_each_phase_read_only(self):
        flat = " ".join(_spec_section(self.spec).split())
        self.assertIn("run the where-am-I step again", flat)
        self.assertIn(
            "it is read-only and never edits the stack record or moves a branch", flat)
        self.assertLess(
            flat.index("it is read-only and never edits the stack record or moves a branch"),
            flat.index("fold.py start --phase"))

    def test_stale_parent_is_shown_to_the_owner_not_ledgered(self):
        flat = " ".join(_spec_section(self.spec).split())
        row = (
            "`refused stale_parent`: the newest unmerged unit's branch is gone. "
            "Show the report to the owner and stop the whole run; never append a "
            "`unit flow off` ledger line for it"
        )
        self.assertIn(row, flat)
        self.assertLess(flat.index(row), flat.index("Any other refusal"))
        self.assertIn("`refused unrecorded_head`", flat)
        weakened = flat.replace(
            "never append a `unit flow off` ledger line for it",
            "append a `unit flow off` ledger line")
        self.assertNotIn(row, weakened)

    def test_first_refusal_points_to_the_recipe(self):
        flat = " ".join(_spec_section(self.spec).split())
        pointer = "At the first refusal of any fold command, read `references/branches.md`"
        self.assertIn(pointer, flat)
        self.assertLess(flat.index(pointer), flat.index("`refused no_trunk`: run"))

    def test_start_guard_and_branch_check_before_phase_files(self):
        flat = " ".join(_spec_section(self.spec).split())
        self.assertTrue(_in_order(flat, (
            "run the where-am-I step again",
            "Before the workflow's first read or write of phase N's files, "
            "run `fold.py start --phase <N>`",
            "guard --phase <N> --repo <REPO>",
            "branch --show-current",
            "Only then does the workflow read or write phase N's files",
        )))
        self.assertNotIn("Before the phase's first commit, run", flat)
        self.assertLess(
            self.flat.index("branch_preflight.py"),
            self.flat.index("Before the workflow's first read or write"))

    def test_deferred_order_directory_then_recheck_then_start(self):
        needles = (
            "create only the directory, `mkdir <REPO>/.planning/phases/<P>-<slug>`",
            "write nothing in it",
            "then the where-am-I step again, the script again for phase N",
            "`start`, `guard` and the branch check of §1, then the first write",
        )
        self.assertTrue(_in_order(self.flat, needles))
        self.assertFalse(_in_order(self.flat, tuple(reversed(needles))))
        self.assertIn("A second `deferred`, exit 1 or exit 2 stops the run", self.flat)
        self.assertNotIn("$S/branch_preflight.py", self.spec)
        self.assertNotIn("let the spec workflow create only the directory", self.flat)

    def test_ownership_rule_replaces_the_old_amendment_wording(self):
        self.assertIn(
            "Each file is committed on the branch of the lowest open unit that owns it, "
            "then the units above are restacked",
            self.flat,
        )
        self.assertNotIn("in K's commit", self.spec)
        self.assertNotIn("<every cross-phase amended", self.flat)
        self.assertIn(
            "in K's commit",
            self.spec + " amends them **in K's commit**",
        )

    def test_one_switch_and_one_restack_per_step_in_order(self):
        needles = (
            "start --phase <J> --repo <REPO>",
            "guard --phase <J> --repo <REPO>",
            "must print J's unit branch",
            "query commit",
            "restack --repo <REPO>",
            "pushes nothing in that run, its trunk cascade included",
            "start --phase <K> --repo <REPO>",
            "guard --phase <K> --repo <REPO>",
            "the same check for K's unit branch",
        )
        part = self.flat[self.flat.index("One switch per owner unit"):]
        self.assertTrue(_in_order(part, needles))
        self.assertFalse(_in_order(part, tuple(reversed(needles))))
        self.assertNotIn("(local, nothing pushed)", self.flat)

    def test_going_back_uses_start_then_guard_only(self):
        part = self.flat[self.flat.index("Going to an earlier phase J"):]
        self.assertTrue(_in_order(part, (
            "start --phase <J> --repo <REPO>",
            "guard --phase <J> --repo <REPO>",
            "These two commands are the only way to switch",
            "never move a branch",
        )))

    def test_end_report_names_five_fields_in_order(self):
        part = self.flat[self.flat.index("**End report.**"):]
        needles = (
            "`checkout:`",
            "`stack:`",
            "`docs <N>:`",
            "`goal file: <path> on <branch>`",
            "`unit flow off:`",
        )
        self.assertTrue(_in_order(part, needles))
        self.assertIn("`goal file: none`", part)
        self.assertIn("`unit flow off: none`", part)
        self.assertFalse(_in_order(part, tuple(reversed(needles))))

    def test_shared_files_go_on_the_lowest_open_unit(self):
        self.assertIn(
            "Both `docs(state)` commits, after the range and at an early stop, "
            "go on the lowest open unit (§6).",
            self.flat,
        )
        self.assertIn(
            "committed with STATE in step (4) of that order, on the lowest open unit",
            self.flat,
        )
        self.assertNotIn("lowest open unit of the range", self.flat)
        self.assertIn(
            "whose unit id starts with `phase-` and whose state is `open`",
            self.flat,
        )
        self.assertNotIn("whose state is not `merged`", self.flat)

    def test_branches_reference_exists_and_is_listed(self):
        self.assertIn("- `references/branches.md` —", self.spec)
        self.assertTrue((_SPEC_DISCUSS.parent / "references" / "branches.md").is_file())

    def test_end_of_range_switches_before_the_shared_writes(self):
        steps = (
            "End of range, in this one order:",
            "for the top phase of the range, then render the goal file there without committing it",
            "(2) `start`, `guard` and the branch check for the lowest open unit",
            "(3) `state.record-session`",
            "(4) one `docs(state)` commit of the `state_path` file and the goal file",
            "(5) `restack`",
            "(6) `start --phase <lowest>`, `guard` and the branch check",
            "(7) a fresh where-am-I and the end report",
        )
        self.assertTrue(_in_order(self.flat, steps))
        self.assertFalse(_in_order(self.flat, tuple(reversed(steps))))
        self.assertEqual(self.flat.count("End of range, in this one order:"), 1)
        self.assertIn("`checkout: <current branch> (unit flow off)`", self.flat)
        self.assertNotIn("After the range's `docs(state)` commit, prepare", self.flat)
        self.assertIn("`goal file: none` and the report is still printed", self.flat)
        self.assertIn("`unit flow off: fold not installed`", self.flat)


class TestSpecDiscussBranchesDoc(unittest.TestCase):
    def setUp(self):
        self.text = _read(_BRANCHES)
        self.flat = " ".join(self.text.split())

    def test_every_contract_reason_has_an_action_or_never_reaches(self):
        reasons = _contract_reasons()
        self.assertIn("stale_parent", reasons)
        self.assertIn("unrecorded_head", reasons)
        self.assertEqual(_uncovered(self.text, reasons), [])

    def test_a_dropped_reason_is_reported(self):
        dropped = self.text.replace("`wrong_parent`", "`gone_reason`")
        self.assertEqual(_uncovered(dropped, _contract_reasons()), ["wrong_parent"])

    def test_symptom_rows_have_actions(self):
        self.assertEqual(_row_mismatches(self.text), [])
        # Non-vacuity: an emptied inserted-phase cell fails for exactly that row.
        emptied = self.text.replace(
            "| inserted phase that must sit below open units | " + _EXPECTED_ACTIONS[
                "inserted phase"] + " |",
            "| inserted phase that must sit below open units |  |",
        )
        self.assertNotEqual(emptied, self.text)
        self.assertEqual(_row_mismatches(emptied), ["inserted phase"])

    def test_unknown_failure_stops(self):
        self.assertIn("A refusal or failure not in this table: show the report and stop.",
                      self.flat)
        self.assertIn("retry once after the stated change, wait for the owner, or stop",
                      self.flat)

    def test_no_action_edits_the_record_or_moves_a_branch(self):
        def _violations(text):
            found = []
            for action in _recipe_rows(text).values():
                if "ai-kit-stack.json" in action:
                    found.append(action)
            for move in _HAND_MOVES:
                if move in text:
                    found.append(move)
            for line in text.splitlines():
                if "ai-kit-stack.json" in line and "Never edit" not in line:
                    found.append(line)
            return found

        self.assertEqual(_violations(self.text), [])
        marker = "## Reasons that never reach spec-discuss"
        record_row = "| `x_reason` | edit .git/ai-kit-stack.json by hand |\n"
        planted_record = self.text.replace(marker, record_row + marker, 1)
        self.assertTrue(any("ai-kit-stack.json" in hit for hit in _violations(planted_record)))
        self.assertTrue(any("ai-kit-stack.json" in action
                            for action in _recipe_rows(planted_record).values()))
        switch_row = "| `y_reason` | run git switch to the unit branch |\n"
        planted_switch = self.text.replace(marker, switch_row + marker, 1)
        self.assertIn("git switch", _violations(planted_switch))

    def test_where_am_i_shape(self):
        shape = (
            "current: <branch, or (detached)>",
            "stack:",
            "unit <id> branch <branch> parent <parent> state <state> exists <yes|no> tip "
            "<sha12|none>",
            "phase <N> unit <id|none> docs <branch|none|split>",
        )
        self.assertTrue(_in_order(self.text, shape))
        self.assertIn("show --all --repo <REPO>", self.text)
        self.assertIn("moves no branch", self.flat)
        self.assertIn("ls-tree --name-only refs/heads/<unit branch> .planning/phases/", self.flat)
        self.assertNotIn("query find-phase", self.text)
        self.assertIn("<P>-SPEC.md", self.text)
        self.assertIn("<P>-CONTEXT.md", self.text)
        self.assertIn("<D>/CONTEXT.md", self.text)
        self.assertIn("`docs split`: exactly one of them is", self.flat)
        self.assertIn("(SPEC on <branch>, CONTEXT none)", self.flat)

    def test_write_steps_in_order(self):
        needles = (
            "start --phase <J> --repo <REPO>",
            "guard --phase <J> --repo <REPO>",
            "must print J's unit branch",
            "query commit",
            "restack --repo <REPO>",
            "start --phase <K> --repo <REPO>",
            "guard --phase <K> --repo <REPO>",
            "must print K's unit branch",
        )
        self.assertTrue(_in_order(self.text, needles))
        self.assertFalse(_in_order(self.text, tuple(reversed(needles))))
        self.assertIn("it pushes nothing in that run, its trunk cascade included", self.flat)
        self.assertNotIn("(local; it pushes nothing)", self.flat)
        self.assertIn("on the branch of the lowest open unit that owns it", self.flat)
        self.assertIn("whose unit id starts with `phase-` and whose state is `open`", self.flat)
        self.assertIn("a `finished` or `ready` unit never receives them", self.flat)
        self.assertNotIn("whose state is not `merged`", self.flat)

    def test_end_report_has_five_fields_in_order(self):
        fields = (
            "checkout: <branch>",
            "stack:",
            "docs <N>: <branch>",
            "goal file: <path> on <branch>",
            "unit flow off: <ledger line>",
        )
        part = self.text[self.text.index("## End report"):]
        self.assertTrue(_in_order(part, fields))
        self.assertFalse(_in_order(part, tuple(reversed(fields))))
        self.assertIn("goal file: none", part)
        self.assertIn("unit flow off: none", part)


if __name__ == "__main__":
    unittest.main()
