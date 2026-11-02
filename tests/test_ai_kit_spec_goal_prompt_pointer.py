"""Tests for the pointer form of the `/goal` block (a long condition moves to `## Full goal`).

The inline form keeps the whole condition on the `/goal` line; the pointer form puts a short
pointer there and the condition in a `## Full goal` section at the bottom of the file. Everything
is pure text or a temporary git repository: no model call, no network, no real HOME.
"""

import contextlib
import io
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "skills" / "ai-kit-spec-goal-prompt" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import goal_prompt
import gp_render
import gp_sections
from gp_common import GuardError

from tests import goal_prompt_fixtures as fx
from tests.test_ai_kit_spec_goal_prompt_cli import (
    DECIDE_REL,
    PHASES,
    SPEC_REL,
    WAKE_REL,
    FakeRun,
    cli_seams,
    host_routes,
)
from tests.test_ai_kit_spec_goal_prompt_cli import answers as cli_answers
from tests.test_ai_kit_spec_goal_prompt_strategies import (
    PATH,
    _RepoCase,
    make_detect,
    plan_answers,
    plans_scope,
    strategy,
    write_plans,
)

FULL = "## Full goal"
LONG = "Ship every phase with the full checks and keep the notes tidy. " * 24  # about 1,500 chars


def pointer_line(path):
    return (
        f"/goal read document `{path}` at section `Full goal` and finish only when that "
        "section's DONE WHEN conditions hold"
    )


def full_goal_body(text):
    """The whitespace-normalised body of the `## Full goal` section ("" when absent)."""
    _, found, rest = text.partition(f"\n{FULL}\n")
    return " ".join(rest.split()) if found else ""


def goal_line_of(text):
    return next(line for line in text.split("\n") if line.startswith("/goal "))


def inline_condition(path, objective, cap=gp_sections.TURN_FLOOR):
    return gp_sections.goal_block(path, objective, cap)[0][len(gp_render.GOAL_PREFIX):]


def goal_view(objective, goal_style="auto"):
    return gp_render.BlockView(path=PATH, objective=objective, first_line="", rails="ROLE\n- x",
                               goal_style=goal_style)


class TestConstants(unittest.TestCase):
    def test_threshold_sits_below_the_budget(self):
        self.assertEqual(gp_render.GOAL_POINTER_THRESHOLD, 1000)
        self.assertLess(gp_render.GOAL_POINTER_THRESHOLD, gp_render.GOAL_BUDGET)
        self.assertEqual(gp_render.GOAL_STYLES, ("auto", "inline", "pointer"))
        self.assertEqual(gp_render.FULL_GOAL_HEADING, FULL)


class TestBuildBlocks(unittest.TestCase):
    def _objective_for(self, total):
        return "x" * (total - len(inline_condition(PATH, "")) - 1)

    def test_a_condition_of_exactly_the_threshold_stays_inline(self):
        objective = self._objective_for(gp_render.GOAL_POINTER_THRESHOLD)
        (block,) = gp_render.build_blocks([strategy("goal", recommended=True)],
                                          goal_view(objective))
        self.assertEqual(len(block.condition), gp_render.GOAL_POINTER_THRESHOLD)
        self.assertEqual(block.full_goal, "")
        self.assertIn(block.condition, block.text)

    def test_one_character_over_the_threshold_uses_the_pointer(self):
        objective = self._objective_for(gp_render.GOAL_POINTER_THRESHOLD + 1)
        (block,) = gp_render.build_blocks([strategy("goal", recommended=True)],
                                          goal_view(objective))
        self.assertEqual(len(block.full_goal), gp_render.GOAL_POINTER_THRESHOLD + 1)
        self.assertEqual(block.full_goal, inline_condition(PATH, objective))
        self.assertEqual(block.text.split("\n")[1], pointer_line(PATH))
        self.assertEqual(block.condition, pointer_line(PATH)[len("/goal "):])

    def test_forced_styles_override_the_length(self):
        short, long_ = "Finish it.", "y" * 1500
        goal = [strategy("goal", recommended=True)]
        self.assertTrue(gp_render.build_blocks(goal, goal_view(short, "pointer"))[0].full_goal)
        self.assertEqual(gp_render.build_blocks(goal, goal_view(long_, "inline"))[0].full_goal, "")
        self.assertEqual(gp_render.build_blocks(goal, goal_view(short, "auto"))[0].full_goal, "")

    def test_unverified_goal_says_so_on_the_pointer_line_and_in_the_full_goal(self):
        goal = [strategy("goal", recommended=True, label="unverified", primitive="goal")]
        (block,) = gp_render.build_blocks(goal, goal_view("Finish it.", "pointer"))
        self.assertIn("unverified", block.text.split("\n")[1])
        self.assertIn("unverified", block.full_goal)

    def test_loop_and_plain_blocks_ignore_the_goal_style(self):
        for kind, primitive in (("loop", "/loop"), ("plain", "systemd user timer")):
            with self.subTest(kind=kind):
                case = [strategy(kind, primitive=primitive)]
                self.assertEqual(gp_render.build_blocks(case, goal_view("z" * 1500, "pointer")),
                                 gp_render.build_blocks(case, goal_view("z" * 1500, "inline")))

    def test_autonomous_block_ignores_the_goal_style(self):
        view = gp_render.BlockView(path=PATH, objective="z" * 1500,
                                   first_line="/gsd-autonomous --from 16 --to 17 --converge",
                                   rails="ROLE\n- x", goal_style="pointer")
        (block,) = gp_render.build_blocks([strategy("autonomous", recommended=True)], view)
        self.assertEqual(block.full_goal, "")
        self.assertTrue(block.inline)


class TestRenderPointer(_RepoCase):
    def _render(self, objective, goal_style=None, files=("a.md", "b.md")):
        write_plans(self.repo, [(name, f"Plan {name}", None) for name in files])
        detect = make_detect(plans_scope(self.repo), [strategy("goal", recommended=True)])
        extra = {} if goal_style is None else {"goal_style": goal_style}
        answers = plan_answers(list(files), objective=objective, **extra)
        result = gp_render.render(detect, answers, self.ctx())
        return result, self.read(result)

    def test_a_short_goal_keeps_the_inline_form(self):
        result, text = self._render("Finish it.")
        self.assertIn("Done when every DONE WHEN item", goal_line_of(text))
        self.assertNotIn(FULL, text)
        self.assertEqual(result["goal_form"], "inline")
        self.assertEqual(self.problems(text), [])

    def test_a_long_goal_gets_the_pointer_and_a_full_goal_section_at_the_bottom(self):
        result, text = self._render(LONG)
        lines = text.split("\n")
        self.assertEqual(goal_line_of(text), pointer_line(result["path"]))
        self.assertEqual(result["goal_form"], "pointer")
        self.assertEqual(lines.count(FULL), 1)
        self.assertGreater(lines.index(FULL), lines.index("## Rails"))
        self.assertEqual([l for l in lines if l.startswith("## ")][-1], FULL)
        self.assertEqual(self.problems(text), [])

    def test_the_full_goal_equals_what_the_inline_form_would_have_carried(self):
        objective = "y" * 1200  # over the threshold, under the budget: both forms render
        inline_result, inline_text = self._render(objective, "inline")
        pointer_result, pointer_text = self._render(objective, "pointer")
        expected = goal_line_of(inline_text)[len("/goal "):].replace(
            inline_result["path"], pointer_result["path"])
        self.assertEqual(full_goal_body(pointer_text), expected)

    def test_the_full_goal_body_wraps_at_about_100_columns_with_no_line_cap(self):
        _, text = self._render(LONG)
        body = text.partition(f"\n{FULL}\n")[2].strip("\n").split("\n")
        self.assertGreater(len(body), 10)
        self.assertTrue(all(len(line) <= 100 for line in body))
        self.assertGreater(len(" ".join(body)), gp_sections.LINE_CAP)

    def test_the_pointer_uses_the_final_unique_path(self):
        first, first_text = self._render(LONG)
        second, second_text = self._render(LONG)
        self.assertTrue(second["path"].endswith("-2.md"), second["path"])
        self.assertIn(f"`{first['path']}`", first_text)
        self.assertIn(f"`{second['path']}`", second_text)
        self.assertNotIn(f"`{first['path']}`", second_text)
        self.assertIn(f"{second['path']} section Rails", full_goal_body(second_text))

    def test_the_4000_code_point_refusal_no_longer_applies_to_the_pointer_form(self):
        result, text = self._render("y" * 5000)
        self.assertEqual(result["goal_form"], "pointer")
        self.assertIn("y" * 5000, full_goal_body(text))
        self.assertEqual(self.problems(text), [])

    def test_forced_inline_keeps_the_refusals(self):
        write_plans(self.repo, [("a.md", "Plan A", None)])
        detect = make_detect(plans_scope(self.repo), [strategy("goal", recommended=True)])
        answers = plan_answers(["a.md"], objective="y" * 5000, goal_style="inline")
        with self.assertRaisesRegex(GuardError, r"/goal condition is \d{4} code points"):
            gp_render.render(detect, answers, self.ctx())
        self.assertFalse(Path(self.repo, "docs/superpowers/goals").exists())

    def test_forced_inline_between_the_threshold_and_the_budget_is_inline(self):
        result, text = self._render("y" * 1200, goal_style="inline")
        self.assertEqual(result["goal_form"], "inline")
        self.assertNotIn(FULL, text)

    def test_forced_pointer_on_a_short_goal(self):
        result, text = self._render("Finish it.", goal_style="pointer")
        self.assertEqual(result["goal_form"], "pointer")
        self.assertIn(pointer_line(result["path"]), text)
        self.assertIn("Finish it.", full_goal_body(text))

    def test_an_unknown_goal_style_is_refused_and_writes_nothing(self):
        write_plans(self.repo, [("a.md", "Plan A", None)])
        detect = make_detect(plans_scope(self.repo), [strategy("goal", recommended=True)])
        with self.assertRaisesRegex(GuardError, "goal_style"):
            gp_render.render(detect, plan_answers(["a.md"], goal_style="wide"), self.ctx())
        self.assertFalse(Path(self.repo, "docs/superpowers/goals").exists())

    def test_no_goal_block_reports_no_goal_form(self):
        write_plans(self.repo, [("a.md", "Plan A", None)])
        detect = make_detect(plans_scope(self.repo), [strategy("plain", recommended=True)])
        result = gp_render.render(detect, plan_answers(["a.md"]), self.ctx())
        self.assertIsNone(result["goal_form"])
        self.assertNotIn(FULL, self.read(result))

    def test_the_pointer_form_warns_that_the_host_behaviour_is_unverified(self):
        result, text = self._render(LONG)
        self.assertTrue(any("unverified" in w and "Full goal" in w for w in result["warnings"]))
        self.assertFalse(any(w in text for w in result["warnings"]))
        short, _ = self._render("Finish it.")
        self.assertFalse(any("Full goal" in w for w in short["warnings"]))

    def test_conditions_report_the_pointer_and_the_full_length(self):
        result, text = self._render(LONG)
        (entry,) = result["conditions"]
        self.assertEqual(entry["chars"], len(goal_line_of(text)) - len("/goal "))
        self.assertEqual(entry["full_chars"], len(full_goal_body(text)))

    def test_a_goal_with_loop_keeps_the_loop_line_and_one_shared_rails_section(self):
        write_plans(self.repo, [("a.md", "Plan A", None)])
        detect = make_detect(plans_scope(self.repo), [
            strategy("goal", recommended=True),
            strategy("loop", rank=2, primitive="CronCreate recurring")])
        result = gp_render.render(detect, plan_answers(["a.md"], objective=LONG), self.ctx())
        text = self.read(result)
        self.assertEqual(text.count("## Rails"), 1)
        self.assertIn(f"/loop 30m Continue the work described in {result['path']} section Rails",
                      text)
        self.assertEqual(self.problems(text), [])


class TestCheckText(unittest.TestCase):
    def _document(self, full_body, rail_line="- short rule"):
        return (
            "# Goal\n\nSummary.\n\n▼▼▼ COPY FROM HERE ▼▼▼\n\n## Strategy 1: goal\n\n````\n"
            f"{pointer_line('g.md')}\n````\n\n▲▲▲ COPY TO HERE ▲▲▲\n\n## Rails\n\n"
            f"ROLE\n{rail_line}\n\n{FULL}\n\n{full_body}\n"
        )

    def _problems(self, text):
        return gp_render.check_text(text, opengsd_block=False, home=fx.FAKE_HOME,
                                    secrets=[fx.SENTINEL_KEY])

    def test_a_pointer_document_with_a_long_full_goal_is_clean(self):
        self.assertEqual(self._problems(self._document("x" * 5000)), [])

    def test_the_rule_line_cap_still_applies_above_the_full_goal(self):
        problems = self._problems(self._document("ok", rail_line="- " + "r" * 250))
        self.assertTrue(any("rule line over 200" in p for p in problems))

    def test_a_pointer_without_a_full_goal_section_is_flagged(self):
        text = self._document("ok").replace(f"\n{FULL}\n\nok\n", "\n")
        self.assertTrue(any("Full goal" in p for p in self._problems(text)))

    def test_a_skipped_test_tier_split_across_wrapped_lines_is_still_flagged(self):
        body = "Please skip the\nslow test tier today."
        self.assertIn("skipped test tier", self._problems(self._document(body)))

    def test_a_secret_in_the_full_goal_is_flagged(self):
        self.assertTrue(self._problems(self._document(f"use {fx.SENTINEL_KEY} here")))


class TestCliGoalStyle(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        fx.git_init(self.repo)
        skills = self.root / "skills"
        for rel in (WAKE_REL, SPEC_REL, DECIDE_REL):
            fx.write(skills, rel, "# stand-in sibling CLI; never executed\n")
        self.seams = cli_seams(FakeRun(host_routes()), str(skills))
        prompt = mock.patch("builtins.input", side_effect=AssertionError("must never prompt"))
        prompt.start()
        self.addCleanup(prompt.stop)
        fx.opengsd_project(self.repo, PHASES)
        fx.makefile(self.repo, {"e2e-test": "python3 -m unittest discover -s tests/e2e"})
        self.detect_doc = self._detect()

    def _call(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = goal_prompt.main(list(argv), self.seams)
        return code, out.getvalue(), err.getvalue()

    def _detect(self):
        base = self.root / "captures"
        fx.write(base, "roadmap.json", json.dumps(fx.roadmap_json(PHASES)))
        fx.write(base, "identity.json", json.dumps(fx.identity_json(True)))
        for number, doc in fx.phase_op_json(self.repo, PHASES).items():
            fx.write(base / "ops", f"{number}.json", json.dumps(doc))
        code, out, err = self._call(
            "detect", "--repo", str(self.repo), "--roadmap", str(base / "roadmap.json"),
            "--identity", str(base / "identity.json"), "--phase-op", str(base / "ops"))
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def _render(self, **overrides):
        detect_path = self.root / "detect.json"
        answers_path = self.root / "answers.json"
        detect_path.write_text(json.dumps(self.detect_doc), encoding="utf-8")
        answers_path.write_text(json.dumps(cli_answers(strategy="goal", **overrides)),
                                encoding="utf-8")
        return self._call("render", "--repo", str(self.repo), "--detect", str(detect_path),
                          "--answers", str(answers_path))

    def test_default_style_is_auto_and_a_short_goal_reports_inline(self):
        code, out, err = self._render()
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["goal_form"], "inline")

    def test_a_long_objective_reports_pointer_and_writes_the_section(self):
        code, out, err = self._render(objective=LONG)
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(payload["goal_form"], "pointer")
        text = (self.repo / payload["path"]).read_text(encoding="utf-8")
        self.assertIn(pointer_line(payload["path"]), text)
        self.assertEqual(text.count(f"\n{FULL}\n"), 1)
        self.assertTrue(any("Full goal" in warning for warning in payload["warnings"]))

    def test_forced_pointer_and_forced_inline(self):
        code, out, err = self._render(goal_style="pointer")
        self.assertEqual((code, json.loads(out)["goal_form"]), (0, "pointer"), err)
        code, out, err = self._render(goal_style="inline", objective="y" * 1100)
        self.assertEqual((code, json.loads(out)["goal_form"]), (0, "inline"), err)

    def test_an_invalid_goal_style_exits_two_naming_the_field(self):
        code, _out, err = self._render(goal_style="huge")
        self.assertEqual(code, 2)
        self.assertIn("goal_style", json.loads(err)["error"])

    def test_a_null_goal_style_means_auto(self):
        code, out, err = self._render(goal_style=None)
        self.assertEqual((code, json.loads(out)["goal_form"]), (0, "inline"), err)

    def test_the_body_is_wrapped_like_textwrap_at_100_columns(self):
        code, out, err = self._render(objective=LONG)
        self.assertEqual(code, 0, err)
        text = (self.repo / json.loads(out)["path"]).read_text(encoding="utf-8")
        body = text.partition(f"\n{FULL}\n")[2].strip("\n")
        self.assertEqual(body, textwrap.fill(" ".join(body.split()), width=100,
                                             break_long_words=False, break_on_hyphens=False))


if __name__ == "__main__":
    unittest.main()
