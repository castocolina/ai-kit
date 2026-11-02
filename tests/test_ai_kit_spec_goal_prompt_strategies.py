"""Tests for the strategy blocks, the shared-rails shape and the superpowers rails (GPS-01, GPS-02).

SPEC R2, R3, R4; D-08, D-09, D-13, D-27. Pure text or a temporary git repository: no model call,
no network, no real HOME. `render` writes only inside a TemporaryDirectory.
"""

import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "skills" / "ai-kit-spec-goal-prompt" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import gp_render
import gp_scope
import gp_sections
from gp_common import GuardError
from gp_render import RenderContext

from tests import goal_prompt_fixtures as fx

PATH = ".planning/goals/2026-10-31-phases-16-17.md"
FLAG_RE = re.compile(r"--[A-Za-z]")
E2E_MAKE = {
    "command": "make e2e-test",
    "source": "Makefile",
    "kind": "make",
    "confidence": "confirmed",
}
PLAN_DIR = "docs/superpowers/plans"


def strategy(strategy_id, *, rank=1, recommended=False, primitive=None, label=""):
    """A strategy entry as gp_matrix emits it (the fields render reads)."""
    return {
        "id": strategy_id,
        "rank": rank,
        "recommended": recommended,
        "reason": "test",
        "primitive": primitive,
        "label": label,
        "row": "T",
    }


def phase(number):
    return {
        "number": number,
        "name": f"Phase {number}",
        "dir": None,
        "has_spec": True,
        "has_context": True,
        "plan_count": 0,
        "has_reviews": False,
        "has_verification": False,
        "disk_status": "no_directory",
        "cross_ai_plans": 0,
    }


def make_detect(scope, strategies, *, readiness_ok=True):
    """A detect object carrying every field render reads (27-PATTERNS Contracts)."""
    return {
        "schema_version": 1,
        "scope": scope,
        "e2e": {"commands": [E2E_MAKE], "gates": ["make lint"], "none": False},
        "readiness": {
            "runner_ok": readiness_ok,
            "cli_listed": True,
            "reviewers_ok": True,
            "label": "installed, not quota- or auth-verified",
        },
        "jev": {"usable": False, "reason": "no consent on file"},
        "derived": {"must_outlive": True, "provable": True},
        "candidate_skills": ["ai-kit-spec-review"],
        "wake": {"primitive": "CronCreate recurring", "label": ""},
        "runner": {
            "command": "node .planning/scripts/cross-ai.mjs",
            "label": "installed, not quota- or auth-verified",
        },
        "strategies": strategies,
    }


def gsd_scope(identity="opengsd"):
    kind = "opengsd" if identity == "opengsd" else "gsd-unproven"
    return {
        "kind": kind,
        "identity": identity,
        "ask": None,
        "phases": [phase("16"), phase("16.1"), phase("17")],
        "plans": [],
        "order": [],
    }


def phase_answers(**overrides):
    answers = {
        "work_set": {"kind": "phases", "numbers": ["16", "16.1", "17"]},
        "target_host": "claude",
        "native_execution": False,
        "mockups": [],
        "strategy": None,
        "objective": "",
        "output_dir": None,
    }
    answers.update(overrides)
    return answers


def plan_answers(files, **overrides):
    answers = {
        "work_set": {"kind": "plans", "files": [f"{PLAN_DIR}/{name}" for name in files]},
        "target_host": "claude",
        "native_execution": False,
        "mockups": [],
        "strategy": None,
        "objective": "",
        "output_dir": None,
    }
    answers.update(overrides)
    return answers


def write_plans(root, specs):
    """specs: (filename, title, depends_on-line-or-None). Writes real plan files."""
    fx.superpowers_project(
        Path(root),
        {name: fx.plan_text(title, depends_on) for name, title, depends_on in specs},
    )


def plans_scope(root):
    """The scope object `gp_scope.detect_scope` builds from real plan files."""
    inputs = gp_scope.ScopeInputs(
        roadmap=None, phase_ops=None, identity=None, work_kind="plans", numbers=None
    )
    return gp_scope.detect_scope(str(root), inputs)


class _RepoCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = self._tmp.name
        fx.git_init(Path(self.repo))

    def ctx(self):
        return RenderContext(
            repo=self.repo,
            today="2026-10-31",
            home=fx.FAKE_HOME,
            secrets=(fx.SENTINEL_KEY,),
            out_dir=None,
        )

    def read(self, result):
        return Path(self.repo, result["path"]).read_text(encoding="utf-8")

    def problems(self, text):
        return gp_render.check_text(text, opengsd_block=True, home=fx.FAKE_HOME,
                                    secrets=[fx.SENTINEL_KEY])


class TestBlocks(_RepoCase):
    def test_goal_block_first_line_names_path_rails_and_turn_cap(self):
        (line,) = gp_sections.goal_block(PATH, "Finish phase 9.", 200)
        self.assertTrue(line.startswith("/goal "))
        for needle in (PATH, "Rails", "DONE WHEN", "exit code", "count line",
                       "stop and report after 200 turns"):
            self.assertIn(needle, line)

    def test_goal_block_collapses_newlines_in_the_objective(self):
        (line,) = gp_sections.goal_block(PATH, "Finish\nphase\n9.", 200)
        self.assertNotIn("\n", line)
        self.assertIn("Finish phase 9.", line)

    def test_goal_block_stays_within_the_budget_for_a_normal_objective(self):
        (line,) = gp_sections.goal_block(PATH, "Finish phases 16 to 17 and verify each.", 200)
        self.assertLessEqual(len(line), gp_render.GOAL_BUDGET)

    def test_goal_objective_of_5000_chars_fails_generation_naming_the_length(self):
        write_plans(self.repo, [("a.md", "Plan A", None)])
        detect = make_detect(plans_scope(self.repo), [strategy("goal", recommended=True)])
        answers = plan_answers(["a.md"], objective="y" * 5000, goal_style="inline")
        with self.assertRaisesRegex(GuardError, r"/goal condition is \d{4} code points"):
            gp_render.render(detect, answers, self.ctx())
        self.assertFalse(Path(self.repo, "docs/superpowers/goals").exists())

    def test_loop_block_uses_the_command_form_for_command_primitives(self):
        for primitive in ("/loop", "CronCreate one-shot", "CronCreate recurring",
                          "ScheduleWakeup"):
            with self.subTest(primitive=primitive):
                lines = gp_sections.loop_block(PATH, primitive, "30m")
                self.assertEqual(
                    lines,
                    [f"/loop 30m Continue the work described in {PATH} section Rails; "
                     "stop and report once DONE WHEN holds."],
                )

    def test_loop_block_is_a_plain_paragraph_for_an_os_timer_or_no_primitive(self):
        for primitive in ("systemd user timer", None):
            with self.subTest(primitive=primitive):
                (paragraph,) = gp_sections.loop_block(PATH, primitive)
                self.assertTrue(paragraph.startswith(
                    f"Continue the work described in {PATH} section Rails"))
                self.assertIn("OS-timer wake of QUOTA A re-enters this session", paragraph)

    def test_loop_and_plain_blocks_never_contain_a_double_dash(self):
        blocks = [
            gp_sections.loop_block(PATH, "/loop"),
            gp_sections.loop_block(PATH, "systemd user timer"),
            gp_sections.plain_block(PATH),
        ]
        for lines in blocks:
            for line in lines:
                self.assertNotIn("--", line)

    def test_plain_heading_is_flagged_as_plain_without_a_primitive(self):
        heading = gp_sections.strategy_heading(strategy("plain"), 3)
        self.assertIn("plain", heading)
        self.assertIn("flagged: no goal, loop or schedule primitive", heading)
        self.assertTrue(gp_sections.plain_block(PATH)[0].startswith(
            f"Continue the work described in {PATH} section Rails"))

    def test_strategy_heading_marks_the_recommended_one_and_numbers_each(self):
        self.assertEqual(
            gp_sections.strategy_heading(strategy("goal", recommended=True), 1),
            "## Strategy 1 (recommended): goal",
        )
        self.assertEqual(gp_sections.strategy_heading(strategy("loop"), 2),
                         "## Strategy 2: loop")

    def test_unverified_label_appends_the_primitive_to_the_heading(self):
        heading = gp_sections.strategy_heading(
            strategy("loop", primitive="ScheduleWakeup", label="unverified"), 2
        )
        self.assertEqual(heading, "## Strategy 2: loop [unverified: ScheduleWakeup]")

    def test_unverified_goal_loop_and_plain_blocks_say_unverified_in_the_block_itself(self):
        view = gp_render.BlockView(path=PATH, objective="Finish it.", first_line="",
                                   rails="ROLE\n- x")
        cases = [
            strategy("goal", label="unverified", primitive="goal"),
            strategy("loop", label="unverified", primitive="ScheduleWakeup"),
            strategy("plain", label="unverified", primitive="systemd user timer"),
        ]
        for case in cases:
            with self.subTest(strategy=case["id"]):
                (block,) = gp_render.build_blocks([case], view)
                body = block.text.split("\n")[1:-1]
                self.assertIn("unverified", " ".join(body))
                self.assertIn(case["primitive"], " ".join(body))
                if case["id"] == "goal":
                    self.assertIn("unverified", block.condition)
                    self.assertLessEqual(len(block.condition), gp_render.GOAL_BUDGET)

    def test_verified_blocks_carry_no_unverified_label(self):
        view = gp_render.BlockView(path=PATH, objective="Finish it.", first_line="",
                                   rails="ROLE\n- x")
        (block,) = gp_render.build_blocks([strategy("goal", primitive="goal")], view)
        self.assertNotIn("unverified", block.text)

    def test_autonomous_block_in_a_multi_block_file_is_inline_and_self_sufficient(self):
        view = gp_render.BlockView(
            path=PATH,
            objective="Finish phases 16, 16.1, 17.",
            first_line="/gsd-autonomous --from 16 --to 17 --converge",
            rails="RULES FOR EVERY PLAN\n- Every PLAN.md frontmatter carries cross_ai: true.",
        )
        blocks = gp_render.build_blocks(
            [strategy("autonomous", recommended=True), strategy("goal", rank=2)], view
        )
        inline = blocks[0]
        self.assertTrue(inline.inline)
        lines = inline.text.split("\n")
        self.assertEqual(lines[0], "````")
        self.assertEqual(lines[1], "/gsd-autonomous --from 16 --to 17 --converge")
        for line in lines[2:]:
            self.assertNotRegex(line, FLAG_RE)
        self.assertNotIn("Rails: read", inline.text)
        self.assertIn("RULES FOR EVERY PLAN", inline.text)

    def test_recommended_strategy_is_first_regardless_of_input_order(self):
        view = gp_render.BlockView(path=PATH, objective="Finish it.", first_line="",
                                   rails="ROLE\n- x")
        blocks = gp_render.build_blocks(
            [strategy("loop", rank=2), strategy("goal", rank=1, recommended=True)], view
        )
        self.assertEqual(blocks[0].heading, "## Strategy 1 (recommended): goal")
        self.assertEqual(blocks[1].heading, "## Strategy 2: loop")

    def test_superpowers_goal_and_loop_share_one_rails_section_after_the_marker(self):
        write_plans(self.repo, [("a.md", "Plan A", None), ("b.md", "Plan B", None)])
        detect = make_detect(
            plans_scope(self.repo),
            [strategy("goal", recommended=True), strategy("loop", rank=2,
                                                          primitive="CronCreate recurring")],
        )
        result = gp_render.render(detect, plan_answers(["a.md", "b.md"]), self.ctx())
        text = self.read(result)
        close = text.index(gp_render.CLOSE_MARKER)
        self.assertEqual(text.count("## Rails"), 1)
        self.assertGreater(text.index("## Rails"), close)
        self.assertLess(text.index("/goal "), text.index("/loop "))
        fences = [line for line in text.split("\n") if line == "````"]
        self.assertEqual(len(fences), 4)
        self.assertIn(f"{result['path']} section Rails", text)
        self.assertEqual(self.problems(text), [])
        self.assertEqual(result["strategies"], [
            {"id": "goal", "recommended": True, "reason": "test", "label": ""},
            {"id": "loop", "recommended": False, "reason": "test", "label": ""},
        ])
        goal_line = next(line for line in text.split("\n") if line.startswith("/goal "))
        self.assertEqual(result["conditions"], [{"strategy": "goal",
                                                 "chars": len(goal_line) - len("/goal ")}])

    def test_autonomous_alone_is_inline_with_no_shared_rails_section(self):
        detect = make_detect(gsd_scope(), [strategy("autonomous", recommended=True)])
        result = gp_render.render(detect, phase_answers(), self.ctx())
        text = self.read(result)
        self.assertNotIn("## Rails", text)
        self.assertIn("RULES FOR EVERY PLAN\n- Every PLAN.md frontmatter", text)

    def test_autonomous_with_goal_holds_rails_inline_and_shared(self):
        detect = make_detect(
            gsd_scope(),
            [strategy("autonomous", recommended=True), strategy("goal", rank=2)],
        )
        result = gp_render.render(detect, phase_answers(), self.ctx())
        text = self.read(result)
        self.assertEqual(text.count("## Rails"), 1)
        self.assertEqual(text.count("RULES FOR EVERY PLAN\n"), 2)
        self.assertGreater(text.index("## Rails"), text.index(gp_render.CLOSE_MARKER))
        self.assertEqual(self.problems(text), [])

    def test_gsd_unproven_autonomous_is_labelled_unverified_and_lands_in_goals(self):
        detect = make_detect(
            gsd_scope("unverified"),
            [strategy("autonomous", recommended=True, primitive=None, label="unverified")],
        )
        result = gp_render.render(detect, phase_answers(), self.ctx())
        self.assertTrue(result["path"].startswith(".planning/goals/"))
        self.assertIn("## Strategy 1 (recommended): autonomous [unverified: autonomous]",
                      self.read(result))

    def test_plain_strategy_renders_a_flagged_paragraph_with_the_shared_rails(self):
        write_plans(self.repo, [("a.md", "Plan A", None)])
        detect = make_detect(
            plans_scope(self.repo),
            [strategy("plain", recommended=True, primitive="systemd user timer",
                      label="unverified")],
        )
        result = gp_render.render(detect, plan_answers(["a.md"]), self.ctx())
        text = self.read(result)
        self.assertIn("## Strategy 1 (recommended): plain (flagged: no goal, loop or schedule "
                      "primitive) [unverified: systemd user timer]", text)
        self.assertIn(f"Continue the work described in {result['path']} section Rails", text)
        self.assertEqual(self.problems(text), [])

    def test_autonomous_for_superpowers_plans_is_refused(self):
        write_plans(self.repo, [("a.md", "Plan A", None)])
        detect = make_detect(plans_scope(self.repo), [strategy("autonomous", recommended=True)])
        with self.assertRaisesRegex(GuardError, "autonomous needs a GSD phases work set"):
            gp_render.render(detect, plan_answers(["a.md"]), self.ctx())

    def test_shared_rails_rule_line_over_200_characters_is_flagged(self):
        write_plans(self.repo, [("a.md", "Plan A", None)])
        detect = make_detect(plans_scope(self.repo), [strategy("goal", recommended=True)])
        result = gp_render.render(detect, plan_answers(["a.md"]), self.ctx())
        text = self.read(result)
        bloated = text.replace("## Rails\n\n", "## Rails\n\n- " + "z" * 210 + "\n", 1)
        self.assertTrue(any("200 characters" in problem for problem in self.problems(bloated)))

    def test_a_repeated_copy_marker_is_flagged(self):
        write_plans(self.repo, [("a.md", "Plan A", None)])
        detect = make_detect(plans_scope(self.repo), [strategy("goal", recommended=True)])
        text = self.read(gp_render.render(detect, plan_answers(["a.md"]), self.ctx()))
        doubled = text + "\n" + gp_render.OPEN_MARKER + "\n"
        self.assertTrue(any("marker" in problem for problem in self.problems(doubled)))


class TestSuperpowers(_RepoCase):
    def setUp(self):
        super().setUp()
        self.chain = [
            ("a.md", "Plan A", None),
            ("b.md", "Plan B", "`a.md`"),
            ("c.md", "Plan C", "`b.md`"),
            ("d.md", "Plan D", None),
        ]

    def test_superpowers_rule_lines_are_the_fixed_text(self):
        self.assertEqual(
            gp_sections.superpowers_rule_lines(["ai-kit-spec-review"]),
            [
                "Dispatch each plan's work to a subagent, one plan at a time. Reuse a subagent or "
                "start a fresh one as you judge best; no two plans share the working tree at once.",
                "You own AGENTS.md compliance and the deterministic rails; read AGENTS.md first. "
                "The subagent implements, you verify.",
                "After each plan, run its done checks yourself and print their output before "
                "starting the next plan.",
                "A failed plan stops only the plans that depend on it; every independent plan "
                "still runs.",
                "Read a skill only when the task needs it. Candidate skills: ai-kit-spec-review.",
                "Pre-commit hooks always run on every commit; fix a real failure at its root, "
                "never skip it.",
            ],
        )

    def test_order_chain_with_an_independent_plan_lists_the_order(self):
        write_plans(self.repo, self.chain)
        plans = gp_scope.load_plans(self.repo)
        order = gp_scope.execution_order(plans)
        lines = gp_sections.superpowers_order_lines(plans, order)
        self.assertEqual(lines[0], "Plans in order: a.md, b.md, c.md, d.md.")

    def test_stop_scope_lines_name_only_the_transitive_dependents(self):
        write_plans(self.repo, self.chain)
        plans = gp_scope.load_plans(self.repo)
        lines = gp_sections.superpowers_order_lines(plans, gp_scope.execution_order(plans))
        self.assertEqual(lines[1:], [
            "If a.md fails, skip its dependents: b.md, c.md.",
            "If b.md fails, skip its dependents: c.md.",
        ])
        self.assertFalse(any(line.startswith(("If c.md", "If d.md")) for line in lines))

    def test_free_text_dependency_gets_one_confirm_line_each(self):
        write_plans(self.repo, [("a.md", "Plan A", None),
                                ("b.md", "Plan B", "the schema migration")])
        plans = gp_scope.load_plans(self.repo)
        lines = gp_sections.superpowers_order_lines(plans, gp_scope.execution_order(plans))
        self.assertIn("Dependency to confirm before starting: the schema migration.", lines)

    def test_single_plan_has_no_order_lines_and_no_order_heading(self):
        write_plans(self.repo, [("a.md", "Plan A", None)])
        plans = gp_scope.load_plans(self.repo)
        self.assertEqual(gp_sections.superpowers_order_lines(plans, ["a.md"]), [])
        detect = make_detect(plans_scope(self.repo), [strategy("goal", recommended=True)])
        text = self.read(gp_render.render(detect, plan_answers(["a.md"]), self.ctx()))
        self.assertNotIn("\nORDER\n", text)

    def test_ties_keep_filename_order_with_no_dependency_lines(self):
        write_plans(self.repo, [("c.md", "Plan C", None), ("a.md", "Plan A", None),
                                ("b.md", "Plan B", None)])
        plans = gp_scope.load_plans(self.repo)
        order = gp_scope.execution_order(plans)
        self.assertEqual(order, ["a.md", "b.md", "c.md"])
        self.assertEqual(gp_sections.superpowers_order_lines(plans, order),
                         ["Plans in order: a.md, b.md, c.md."])

    def test_objective_names_every_plan_title(self):
        write_plans(self.repo, [("a.md", "A", None), ("b.md", "B", None),
                                ("c.md", "C", None), ("d.md", "D", None)])
        answers = plan_answers(["a.md", "b.md", "c.md", "d.md"])
        scope = plans_scope(self.repo)
        titles = ", ".join(p["title"] for p in scope["plans"])
        lines = gp_sections.objective_lines(answers, f"4 plans: {titles}")
        self.assertEqual(lines[0],
                         "Finish 4 plans: A, B, C, D, each verified. Then leave the repository "
                         "clean.")

    def test_full_render_writes_under_superpowers_goals_never_plans(self):
        write_plans(self.repo, self.chain)
        detect = make_detect(plans_scope(self.repo), [strategy("goal", recommended=True)])
        result = gp_render.render(detect, plan_answers(["a.md", "b.md", "c.md", "d.md"]),
                                  self.ctx())
        self.assertTrue(result["path"].startswith("docs/superpowers/goals/"))
        self.assertNotIn("/plans/", result["path"])
        self.assertTrue(Path(self.repo, result["path"]).is_file())

    def test_superpowers_rails_hold_the_sections_and_no_gsd_only_rule(self):
        write_plans(self.repo, self.chain)
        detect = make_detect(plans_scope(self.repo), [strategy("goal", recommended=True)])
        text = self.read(gp_render.render(detect, plan_answers(["a.md", "b.md", "c.md", "d.md"]),
                                          self.ctx()))
        for heading in ("OBJECTIVE", "ROLE", "RULES FOR EVERY PLAN", "ORDER", "QUOTA",
                        "DECISIONS", "SAFETY", "DONE WHEN", "CLEANUP", "STOP IF", "REPORT"):
            self.assertIn(f"\n{heading}\n", text)
        self.assertNotIn("cross_ai: true", text)
        self.assertNotIn("First step, before any execution", text)
        self.assertNotIn("cross-AI candidate", text)
        self.assertEqual(self.problems(text), [])

    def test_quota_has_separate_a_and_b_directives_and_done_when_has_the_e2e_command(self):
        write_plans(self.repo, [("a.md", "Plan A", None)])
        detect = make_detect(plans_scope(self.repo), [strategy("goal", recommended=True)])
        text = self.read(gp_render.render(detect, plan_answers(["a.md"]), self.ctx()))
        self.assertIn("\n- A. This session (its own quota)", text)
        self.assertIn("\n- B. Cross-AI children", text)
        self.assertIn("`make e2e-test` exits 0 and prints a test count above zero", text)
        self.assertIn("\nCLEANUP\n", text)

    def test_plan_work_set_renders_only_the_named_plan_files(self):
        write_plans(self.repo, self.chain)
        detect = make_detect(plans_scope(self.repo), [strategy("goal", recommended=True)])
        result = gp_render.render(detect, plan_answers(["a.md", "d.md"]), self.ctx())
        text = self.read(result)
        self.assertIn("Finish 2 plans: Plan A, Plan D, each verified.", text)
        self.assertNotIn("Plan C", text)

    def test_plan_outside_the_detected_scope_is_refused(self):
        write_plans(self.repo, [("a.md", "Plan A", None)])
        detect = make_detect(plans_scope(self.repo), [strategy("goal", recommended=True)])
        with self.assertRaisesRegex(GuardError, "not in the detected scope"):
            gp_render.render(detect, plan_answers(["z.md"]), self.ctx())
        self.assertFalse(Path(self.repo, "docs/superpowers/goals").exists())

    def test_free_text_work_set_uses_generic_rules_and_no_order_section(self):
        detect = make_detect(
            {"kind": "none", "identity": "unverified", "ask": None, "phases": [], "plans": [],
             "order": []},
            [strategy("goal", recommended=True)],
        )
        answers = {
            "work_set": {"kind": "free", "text": "tidy the release notes"},
            "target_host": "claude",
            "native_execution": False,
            "mockups": [],
            "strategy": None,
            "objective": "",
            "output_dir": "tmp/goals",
        }
        Path(self.repo, ".gitignore").write_text("tmp/\n", encoding="utf-8")
        result = gp_render.render(detect, answers, self.ctx())
        text = self.read(result)
        self.assertTrue(result["path"].startswith("tmp/goals/"))
        self.assertNotIn("\nORDER\n", text)
        self.assertIn("Finish tidy the release notes, each verified.", text)
        self.assertNotIn("cross_ai: true", text)


if __name__ == "__main__":
    unittest.main()
