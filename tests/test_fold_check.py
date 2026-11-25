"""The superpowers fold-step check and merge-reports --extra-findings."""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skills" / "ai-kit-spec-review"))

from ai_kit_spec import fold_check, review_reports
from ai_kit_spec.cli import main

FIXTURES = REPO / "tests" / "fixtures" / "fold_step"


def _run(argv) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _fold_block(doc: str) -> str:
    code, block = _run(["check-fold-step", "--doc", doc,
                        "--framework", "superpowers", "--archetype", "plan"])
    assert code == 0
    return block


FOLD_REQUIRED = "### Task 3: Fold the plan's commits (ai-kit-commit-fold)"
APPROVED = "## Review: plan.md\n### Status: Approved\n"


class TestFoldFinding(unittest.TestCase):
    def test_fixture_pair(self):
        self.assertIsNone(fold_check.fold_finding(_read("with_fold.md"), "plan.md"))
        result = fold_check.fold_finding(_read("without_fold.md"), "plan.md")
        self.assertIsNotNone(result)
        assert result is not None
        found = review_reports.parse_findings(result)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["severity"], "HIGH")
        self.assertEqual(found[0]["title"], "Plan has no fold step")
        self.assertEqual(found[0]["location"], "plan.md, last ### Task")
        self.assertIn(FOLD_REQUIRED, found[0]["required"])

    def test_fold_in_a_fence_or_under_self_review_does_not_count(self):
        for name in ("fold_in_fence.md", "fold_under_self_review.md", "fold_in_long_fence.md"):
            with self.subTest(name=name):
                result = fold_check.fold_finding(_read(name), "plan.md")
                self.assertIsNotNone(result)
                self.assertIn("### Task 3:", result or "")
        text = ("### Task 1: A\n- [ ] a\n```\n~~~\n"
                "### Task 2: Fold the plan's commits (ai-kit-commit-fold)\n```\n")
        result = fold_check.fold_finding(text, "plan.md")
        self.assertIsNotNone(result)
        self.assertIn("### Task 2:", result or "")

    def test_empty_plan_gets_no_finding(self):
        self.assertIsNone(fold_check.fold_finding("# Plan\n\n**Goal:** nothing yet.\n", "plan.md"))
        self.assertIsNone(fold_check.fold_finding("", "plan.md"))

    def test_mark_is_case_insensitive_on_a_heading_or_checkbox(self):
        self.assertIsNone(fold_check.fold_finding(
            "### Task 1: A\n- [ ] a\n### Task 2: Finish\n- [x] FOLD THE PLAN'S COMMITS now\n",
            "plan.md"))
        self.assertIsNone(fold_check.fold_finding(
            "### Task 1: A\n### Task 2: Use AI-KIT-COMMIT-FOLD\n", "plan.md"))
        result = fold_check.fold_finding(
            "### Task 1: A\n### Task 2: B\nThe ai-kit-commit-fold step comes later.\n",
            "plan.md")
        self.assertIsNotNone(result)
        self.assertIn("### Task 3:", result or "")

    def test_only_the_last_task_counts(self):
        result = fold_check.fold_finding(
            "### Task 1: Fold the plan's commits (ai-kit-commit-fold)\n"
            "### Task 2: B\n- [ ] b\n", "plan.md")
        self.assertIsNotNone(result)
        self.assertIn("### Task 3:", result or "")

    def test_wants_check_scope(self):
        self.assertTrue(fold_check.wants_check("superpowers", "plan"))
        self.assertTrue(fold_check.wants_check("superpowers", "design+plan"))
        self.assertFalse(fold_check.wants_check("gsd", "plan"))
        self.assertFalse(fold_check.wants_check("none", "plan"))
        self.assertFalse(fold_check.wants_check("superpowers", "intent+requirements+design"))


class TestFoldTracer(unittest.TestCase):
    def test_missing_fold_step_reaches_the_merged_report(self):
        doc = str(FIXTURES / "without_fold.md")
        with tempfile.TemporaryDirectory() as d:
            code, block = _run(["check-fold-step", "--doc", doc,
                                "--framework", "superpowers", "--archetype", "plan"])
            self.assertEqual(code, 0)
            self.assertEqual(block.splitlines()[0], "### HIGH")
            self.assertIn("- **Plan has no fold step** — Location: " + doc + ", last ### Task.",
                          block)
            self.assertIn("### Task 3: Fold the plan's commits (ai-kit-commit-fold)", block)
            fold_path = os.path.join(d, "fold.md")
            report_path = os.path.join(d, "a.md")
            Path(fold_path).write_text(block, encoding="utf-8")
            Path(report_path).write_text("## Review: plan.md\n### Status: Approved\n",
                                         encoding="utf-8")
            code, out = _run(["merge-reports", "--doc-paths", "plan.md",
                              "--extra-findings", fold_path, "a=" + report_path])
        self.assertEqual(code, 0)
        self.assertIn("### HIGH", out)
        self.assertIn("(Reviewers: fold-check)", out)
        self.assertTrue(out.rstrip().endswith("### Status: Issues Found — fix and re-invoke"))

    def test_non_superpowers_plan_is_never_flagged(self):
        doc = str(FIXTURES / "without_fold.md")
        for framework, archetype in (("gsd", "plan"), ("none", "plan"),
                                     ("superpowers", "intent+requirements+design")):
            with self.subTest(framework=framework, archetype=archetype):
                self.assertEqual(_run(["check-fold-step", "--doc", doc, "--framework",
                                       framework, "--archetype", archetype]), (0, ""))

    def test_with_fold_prints_nothing(self):
        doc = str(FIXTURES / "with_fold.md")
        self.assertEqual(_run(["check-fold-step", "--doc", doc, "--framework", "superpowers",
                               "--archetype", "plan"]), (0, ""))

    def test_unreadable_doc_exits_2(self):
        with tempfile.TemporaryDirectory() as d, redirect_stderr(io.StringIO()):
            code, out = _run(["check-fold-step", "--doc", os.path.join(d, "missing.md"),
                              "--framework", "superpowers", "--archetype", "plan"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")

    def test_two_plans_keep_two_findings(self):
        without = _read("without_fold.md")
        with tempfile.TemporaryDirectory() as d:
            paths = {}
            for name, text in (("p1.md", without), ("p2.md", _read("with_fold.md")),
                               ("p3.md", without)):
                paths[name] = os.path.join(d, name)
                Path(paths[name]).write_text(text, encoding="utf-8")
            fold = "".join(_fold_block(paths[n]) for n in ("p1.md", "p2.md", "p3.md"))
            fold_path = os.path.join(d, "fold.md")
            Path(fold_path).write_text(fold, encoding="utf-8")
            report_path = os.path.join(d, "r.md")
            Path(report_path).write_text(
                "## Review: p1.md\n### HIGH\n- **Goal is vague** — Location: Goal line. "
                "Required: name the outcome. Why: the reader cannot test it.\n"
                "### Status: Issues Found — fix and re-invoke\n", encoding="utf-8")
            code, out = _run(["merge-reports", "--doc-paths", "p1.md p2.md p3.md",
                              "--extra-findings", fold_path, "r=" + report_path])
            found = review_reports.parse_findings(out)
            self.assertEqual(code, 0)
            self.assertEqual(len(found), 3)
            self.assertTrue(all(f["severity"] == "HIGH" for f in found))
            folds = [f for f in found if f["title"] == "Plan has no fold step"]
            self.assertEqual(sorted(f["location"] for f in folds),
                             [paths["p1.md"] + ", last ### Task",
                              paths["p3.md"] + ", last ### Task"])
            for f in folds:
                self.assertIn(FOLD_REQUIRED, f["required"])
            self.assertEqual([f["title"] for f in found if f not in folds], ["Goal is vague"])
            self.assertNotIn("p2.md", "".join(f["location"] for f in found))

    def test_logged_two_lane_merge_keeps_the_fold_finding(self):
        with tempfile.TemporaryDirectory() as d:
            lane = ('{"round": 1, "key": "%s", "state": "chosen", "reason": null, '
                    '"cause": null, "by": null, "at": 1.0}\n')
            log = os.path.join(d, "lanes.jsonl")
            Path(log).write_text(lane % "a" + lane % "b", encoding="utf-8")
            a = os.path.join(d, "a.md")
            b = os.path.join(d, "b.md")
            Path(a).write_text(APPROVED, encoding="utf-8")
            Path(b).write_text(APPROVED, encoding="utf-8")
            fold_path = os.path.join(d, "fold.md")
            Path(fold_path).write_text(_fold_block(str(FIXTURES / "without_fold.md")),
                                       encoding="utf-8")
            code, out = _run(["merge-reports", "--cwd", d, "--doc-paths", "plan.md",
                              "--lane-log", log, "--round", "1",
                              "--extra-findings", fold_path, "a=" + a, "b=" + b])
        self.assertEqual(code, 0)
        self.assertIn("Plan has no fold step", out)
        self.assertIn("(Reviewers: fold-check)", out)
        self.assertTrue(any(line.startswith("Judged by: a, b") for line in out.splitlines()))
        self.assertTrue(out.rstrip().endswith("### Status: Issues Found — fix and re-invoke"))

    def test_same_location_reviewer_high_keeps_the_fold_edit(self):
        with tempfile.TemporaryDirectory() as d:
            p1 = os.path.join(d, "p1.md")
            Path(p1).write_text(_read("without_fold.md"), encoding="utf-8")
            fold_path = os.path.join(d, "fold.md")
            Path(fold_path).write_text(_fold_block(p1), encoding="utf-8")
            report_path = os.path.join(d, "r.md")
            Path(report_path).write_text(
                "## Review: p1.md\n### HIGH\n- **Last task has no test step** — Location: "
                + p1 + ", last ### Task. Required: add a test step. Why: the change is "
                "untested.\n### Status: Issues Found — fix and re-invoke\n", encoding="utf-8")
            code, out = _run(["merge-reports", "--doc-paths", "p1.md",
                              "--extra-findings", fold_path, "r=" + report_path])
            found = review_reports.parse_findings(out)
            self.assertEqual(code, 0)
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["severity"], "HIGH")
            self.assertEqual(found[0]["title"], "Plan has no fold step")
            self.assertEqual(found[0]["location"], p1 + ", last ### Task")
            self.assertIn(FOLD_REQUIRED, found[0]["required"])
            self.assertIn("(Reviewers: fold-check, r)", out)

    def test_empty_extra_file_keeps_approved(self):
        with tempfile.TemporaryDirectory() as d:
            fold_path = os.path.join(d, "fold.md")
            Path(fold_path).write_text("", encoding="utf-8")
            a = os.path.join(d, "a.md")
            Path(a).write_text(APPROVED, encoding="utf-8")
            code, out = _run(["merge-reports", "--doc-paths", "plan.md",
                              "--extra-findings", fold_path, "a=" + a])
        self.assertEqual(code, 0)
        self.assertTrue(out.rstrip().endswith("### Status: Approved"))

    def test_unreadable_extra_file_exits_2(self):
        with tempfile.TemporaryDirectory() as d:
            a = os.path.join(d, "a.md")
            Path(a).write_text(APPROVED, encoding="utf-8")
            junk = os.path.join(d, "fold.md")
            Path(junk).write_text("not a finding\n", encoding="utf-8")
            for extra in (os.path.join(d, "missing.md"), junk):
                with self.subTest(extra=os.path.basename(extra)):
                    with self.assertRaises(SystemExit) as ctx, redirect_stderr(io.StringIO()):
                        _run(["merge-reports", "--doc-paths", "plan.md",
                              "--extra-findings", extra, "a=" + a])
                    self.assertEqual(ctx.exception.code, 2)

    def test_extra_file_is_never_a_lane(self):
        with tempfile.TemporaryDirectory() as d:
            a = os.path.join(d, "a.md")
            b = os.path.join(d, "b.md")
            Path(a).write_text("### Status: Failure — input missing\n", encoding="utf-8")
            Path(b).write_text(APPROVED, encoding="utf-8")
            fold_path = os.path.join(d, "fold.md")
            Path(fold_path).write_text(_fold_block(str(FIXTURES / "without_fold.md")),
                                       encoding="utf-8")
            code, out = _run(["merge-reports", "--doc-paths", "plan.md",
                              "--extra-findings", fold_path, "a=" + a, "b=" + b])
        self.assertEqual(code, 1)
        self.assertIn("### Status: Failure — a", out)
        self.assertNotIn("fold-check", out)


class TestFoldWording(unittest.TestCase):
    def test_adapter_skill_documents_the_wording(self):
        text = (REPO / "skills" / "ai-kit-spec-execute-superpowers" / "SKILL.md").read_text(
            encoding="utf-8")
        self.assertIn(fold_check.FOLD_SKILL, text)
        self.assertIn(fold_check.FOLD_TODO, text)

    def test_review_eval_plans_carry_the_fold_step(self):
        for rel in ("active", "no-config"):
            with self.subTest(fixture=rel):
                text = (REPO / "skills" / "ai-kit-spec-review" / "evals" / "files" / rel
                        / "project" / "docs" / "superpowers" / "plans"
                        / "demo.md").read_text(encoding="utf-8")
                tasks = [line for line in text.splitlines() if line.startswith("### Task ")]
                self.assertEqual(tasks[-1], FOLD_REQUIRED)
                self.assertIsNone(fold_check.fold_finding(text, "demo.md"))


if __name__ == "__main__":
    unittest.main()
