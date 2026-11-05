"""Tests for the `## Full objective` section: a user objective too long for one rule line keeps
its full text in the file, and the shortened rule line ends with a pointer to it.

Pure text or a temporary git repository: no model call, no network, no real HOME.
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "skills" / "ai-kit-spec-goal-prompt" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import goal_prompt
import gp_render
import gp_sections

from tests import goal_prompt_fixtures as fx
from tests.test_ai_kit_spec_goal_prompt_cli import (
    JEV_REL,
    PHASES,
    SPEC_REL,
    WAKE_REL,
    FakeRun,
    cli_seams,
    host_routes,
)
from tests.test_ai_kit_spec_goal_prompt_cli import answers as cli_answers
from tests.test_ai_kit_spec_goal_prompt_strategies import (
    _RepoCase,
    gsd_scope,
    make_detect,
    phase_answers,
    plan_answers,
    plans_scope,
    strategy,
    write_plans,
)

FULL_OBJ = "## Full objective"
FULL_GOAL = "## Full goal"
LONG = "Keep every migration reversible and leave a short note per phase on what changed. " * 6
PATH = ".planning/goals/2026-10-31-phases-16-17.md"


def pointer(path=PATH):
    return f"(full text: {path} section Full objective)"


def objective_rule(text):
    """The line after `OBJECTIVE`'s scope line, as a rule line with its bullet."""
    lines = text.split("\n")
    start = lines.index("OBJECTIVE")
    return lines[start + 2]


def full_objective_body(text):
    _, found, rest = text.partition(f"\n{FULL_OBJ}\n")
    if not found:
        return ""
    return " ".join(rest.split(f"\n{FULL_GOAL}\n")[0].split())


class TestObjectiveLines(unittest.TestCase):
    def _answers(self, objective):
        return {"objective": objective}

    def test_an_objective_that_fits_is_unchanged(self):
        fits = "x" * (gp_sections.LINE_CAP - len(gp_sections.RULE_BULLET))
        lines = gp_sections.objective_lines(self._answers(fits), "phases 16", PATH)
        self.assertEqual(lines[1], fits)
        self.assertFalse(gp_sections.objective_cut(self._answers(fits)))

    def test_one_character_over_is_cut_and_ends_with_the_pointer(self):
        over = "x" * (gp_sections.LINE_CAP - len(gp_sections.RULE_BULLET) + 1)
        self.assertTrue(gp_sections.objective_cut(self._answers(over)))
        line = gp_sections.objective_lines(self._answers(over), "phases 16", PATH)[1]
        self.assertTrue(line.endswith(pointer()), line)
        self.assertLessEqual(len(gp_sections.RULE_BULLET + line), gp_sections.LINE_CAP)
        self.assertIn("...", line)

    def test_no_objective_means_no_cut(self):
        self.assertFalse(gp_sections.objective_cut({"objective": ""}))
        self.assertFalse(gp_sections.objective_cut({}))

    def test_the_pointer_fits_even_for_a_long_path(self):
        path = ".planning/goals/" + "a" * 90 + ".md"
        line = gp_sections.objective_lines(self._answers(LONG), "phases 16", path)[1]
        self.assertTrue(line.endswith(pointer(path)))
        self.assertLessEqual(len(gp_sections.RULE_BULLET + line), gp_sections.LINE_CAP)


class TestRenderFullObjective(_RepoCase):
    def _autonomous(self, objective, extra=()):
        detect = make_detect(gsd_scope(), [strategy("autonomous", recommended=True), *extra])
        result = gp_render.render(detect, phase_answers(objective=objective), self.ctx())
        return result, self.read(result)

    def test_a_short_objective_adds_no_section(self):
        result, text = self._autonomous("Ship it.")
        self.assertNotIn(FULL_OBJ, text)
        self.assertFalse(result["full_objective"])

    def test_a_long_objective_adds_the_section_after_the_marker(self):
        result, text = self._autonomous(LONG.strip())
        lines = text.split("\n")
        self.assertTrue(result["full_objective"])
        self.assertEqual(lines.count(FULL_OBJ), 1)
        self.assertGreater(lines.index(FULL_OBJ), lines.index(gp_render.CLOSE_MARKER))
        self.assertEqual(full_objective_body(text), " ".join(LONG.split()))
        self.assertTrue(objective_rule(text).endswith(pointer(result["path"])))
        self.assertEqual(self.problems(text), [])

    def test_the_section_wraps_at_100_columns_with_no_line_cap(self):
        _, text = self._autonomous(LONG.strip() * 3)
        body = text.partition(f"\n{FULL_OBJ}\n")[2].strip("\n").split("\n")
        self.assertGreater(len(body), 5)
        self.assertTrue(all(len(line) <= 100 for line in body))
        self.assertGreater(len(" ".join(body)), gp_sections.LINE_CAP)

    def test_the_pointer_uses_the_final_unique_path(self):
        first, _ = self._autonomous(LONG.strip())
        second, second_text = self._autonomous(LONG.strip())
        self.assertTrue(second["path"].endswith("-2.md"))
        self.assertTrue(objective_rule(second_text).endswith(pointer(second["path"])))
        self.assertNotIn(first["path"], objective_rule(second_text))

    def test_full_objective_comes_before_full_goal_and_both_stay_intact(self):
        write_plans(self.repo, [("a.md", "Plan A", None)])
        detect = make_detect(plans_scope(self.repo), [strategy("goal", recommended=True)])
        result = gp_render.render(detect, plan_answers(["a.md"], objective=LONG.strip() * 2),
                                  self.ctx())
        text = self.read(result)
        headings = [line for line in text.split("\n") if line.startswith("## ")]
        self.assertEqual(headings[-3:], ["## Rails", FULL_OBJ, FULL_GOAL])
        self.assertEqual(result["goal_form"], "pointer")
        self.assertEqual(self.problems(text), [])
        self.assertIn(" ".join((LONG.strip() * 2).split()), full_objective_body(text))

    def test_loop_and_plain_blocks_share_the_rails_pointer(self):
        write_plans(self.repo, [("a.md", "Plan A", None)])
        detect = make_detect(plans_scope(self.repo), [
            strategy("loop", recommended=True, primitive="/loop"),
            strategy("plain", rank=2, primitive="systemd user timer")])
        result = gp_render.render(detect, plan_answers(["a.md"], objective=LONG.strip()),
                                  self.ctx())
        text = self.read(result)
        self.assertEqual(text.count(FULL_OBJ), 1)
        self.assertTrue(result["full_objective"])
        self.assertEqual(self.problems(text), [])

    def test_a_scope_cut_alone_adds_no_section(self):
        write_plans(self.repo, [(f"p{i}.md", "T " * 80, None) for i in range(6)])
        detect = make_detect(plans_scope(self.repo), [strategy("plain", recommended=True)])
        names = [f"p{i}.md" for i in range(6)]
        result = gp_render.render(detect, plan_answers(names), self.ctx())
        self.assertFalse(result["full_objective"])


class TestCheckText(unittest.TestCase):
    def _document(self, full_body, rail_line="- short rule", objective_line=None):
        rule = objective_line or "- Finish phases 16 to 17."
        return (
            "# Goal\n\nSummary.\n\n▼▼▼ COPY FROM HERE ▼▼▼\n\n## Strategy 1: plain\n\n````\n"
            "Continue the work described in g.md section Rails\n````\n\n▲▲▲ COPY TO HERE ▲▲▲\n\n"
            f"## Rails\n\nOBJECTIVE\n{rule}\n{rail_line}\n\n{FULL_OBJ}\n\n{full_body}\n"
        )

    def _problems(self, text):
        return gp_render.check_text(text, opengsd_block=False, home=fx.FAKE_HOME,
                                    secrets=[fx.SENTINEL_KEY])

    def test_a_long_full_objective_is_clean(self):
        line = f"- Ship it ... {pointer('g.md')}"
        self.assertEqual(self._problems(self._document("x" * 5000, objective_line=line)), [])

    def test_the_rule_line_cap_still_applies_above_the_section(self):
        problems = self._problems(self._document("ok", rail_line="- " + "r" * 250))
        self.assertTrue(any("rule line over 200" in p for p in problems))

    def test_a_pointer_without_a_section_is_flagged(self):
        line = f"- Ship it ... {pointer('g.md')}"
        text = self._document("ok", objective_line=line).replace(f"\n{FULL_OBJ}\n\nok\n", "\n")
        self.assertTrue(any("Full objective" in p for p in self._problems(text)))

    def test_a_skipped_test_tier_split_across_wrapped_lines_is_flagged(self):
        body = "Please skip the\nslow test tier today."
        self.assertIn("skipped test tier", self._problems(self._document(body)))


class TestCliFullObjective(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        fx.git_init(self.repo)
        skills = self.root / "skills"
        for rel in (WAKE_REL, SPEC_REL, JEV_REL):
            fx.write(skills, rel, "# stand-in sibling CLI; never executed\n")
        self.seams = cli_seams(FakeRun(host_routes()), str(skills))
        prompt = mock.patch("builtins.input", side_effect=AssertionError("must never prompt"))
        prompt.start()
        self.addCleanup(prompt.stop)
        fx.opengsd_project(self.repo, PHASES)
        fx.makefile(self.repo, {"e2e-test": "python3 -m unittest discover -s tests/e2e"})

    def _call(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = goal_prompt.main(list(argv), self.seams)
        return code, out.getvalue(), err.getvalue()

    def _render(self, objective):
        base = self.root / "captures"
        fx.write(base, "roadmap.json", json.dumps(fx.roadmap_json(PHASES)))
        fx.write(base, "identity.json", json.dumps(fx.identity_json(True)))
        for number, doc in fx.phase_op_json(self.repo, PHASES).items():
            fx.write(base / "ops", f"{number}.json", json.dumps(doc))
        code, out, err = self._call(
            "detect", "--repo", str(self.repo), "--roadmap", str(base / "roadmap.json"),
            "--identity", str(base / "identity.json"), "--phase-op", str(base / "ops"))
        self.assertEqual(code, 0, err)
        (self.root / "detect.json").write_text(out, encoding="utf-8")
        (self.root / "answers.json").write_text(
            json.dumps(cli_answers(objective=objective)), encoding="utf-8")
        return self._call("render", "--repo", str(self.repo), "--detect",
                          str(self.root / "detect.json"), "--answers",
                          str(self.root / "answers.json"))

    def test_render_reports_full_objective_false_for_a_short_objective(self):
        code, out, err = self._render("Finish the foundation phases")
        self.assertEqual(code, 0, err)
        self.assertFalse(json.loads(out)["full_objective"])

    def test_render_reports_full_objective_true_and_writes_the_section(self):
        code, out, err = self._render(LONG.strip())
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertTrue(payload["full_objective"])
        text = (self.repo / payload["path"]).read_text(encoding="utf-8")
        self.assertEqual(text.count(f"\n{FULL_OBJ}\n"), 1)
        self.assertIn(pointer(payload["path"]), text)


if __name__ == "__main__":
    unittest.main()
