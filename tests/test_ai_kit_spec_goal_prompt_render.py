"""Tests for the goal-prompt renderer: template, guards, sections and placement (GPS-02..04).

SPEC R3; D-12..D-15, D-25..D-28. Everything is pure text or a temporary directory: no model call,
no network, no real HOME. `render` writes only inside a TemporaryDirectory git repository.
"""

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "skills" / "ai-kit-spec-goal-prompt" / "scripts"
ASSET = REPO / "skills" / "ai-kit-spec-goal-prompt" / "assets" / "prompt-template.md"
sys.path.insert(0, str(SCRIPTS))
import goal_prompt
import gp_host
import gp_render
import gp_sections
from gp_common import GuardError
from gp_render import RenderContext

from tests import goal_prompt_fixtures as fx
from tests.test_ai_kit_spec_goal_prompt_cli import MATRIX_ROWS, FakeRun, host_routes

WRAPPER = (
    "This project is OpenGSD, so the run uses /gsd-autonomous with convergence. Paste the block "
    "between the markers into a fresh session in this repository."
)
HEADINGS = (
    "OBJECTIVE",
    "ROLE",
    "RULES FOR EVERY PLAN",
    "ORDER",
    "QUOTA",
    "DECISIONS",
    "SAFETY",
    "DONE WHEN",
    "CLEANUP",
    "STOP IF",
    "REPORT",
)
FLAG_RE = re.compile(r"--[A-Za-z]")
E2E_MAKE = {
    "command": "make e2e-test",
    "source": "Makefile",
    "kind": "make",
    "confidence": "confirmed",
}
E2E_UNITTEST = {
    "command": "python3 -m unittest discover tests/e2e",
    "source": "tests/e2e",
    "kind": "unittest",
    "confidence": "inferred",
}


def phase(number, *, spec=True, context=True, plans=0, verification=False):
    """A scope Phase as detect emits it (gp_scope.Phase field names, JSON form)."""
    return {
        "number": number,
        "name": f"Phase {number}",
        "dir": None,
        "has_spec": spec,
        "has_context": context,
        "plan_count": plans,
        "has_reviews": False,
        "has_verification": verification,
        "disk_status": "no_directory",
        "cross_ai_plans": 0,
    }


def make_detect(**overrides):
    """A hand-built detect object carrying every field render reads (27-PATTERNS Contracts)."""
    detect = {
        "schema_version": 1,
        "scope": {
            "kind": "opengsd",
            "identity": "opengsd",
            "ask": None,
            "phases": [
                phase("16", verification=True),
                phase("16.1"),
                phase("17", spec=False, plans=2),
            ],
            "plans": [],
            "order": [],
        },
        "e2e": {"commands": [E2E_MAKE], "gates": ["make lint", "make test-unit"], "none": False},
        "readiness": {
            "runner_ok": True,
            "cli_listed": True,
            "reviewers_ok": True,
            "label": "installed, not quota- or auth-verified",
        },
        "jev": {"usable": False, "reason": "no consent on file"},
        "derived": {"must_outlive": True, "provable": True},
        "candidate_skills": [],
        "wake": {"primitive": "CronCreate recurring", "label": ""},
        "runner": {
            "command": "node .planning/scripts/cross-ai.mjs",
            "label": "installed, not quota- or auth-verified",
        },
        "strategies": [
            {
                "id": "autonomous",
                "rank": 1,
                "recommended": True,
                "reason": "OpenGSD scope",
                "primitive": None,
            }
        ],
    }
    detect.update(overrides)
    return detect


def make_answers(**overrides):
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


def built_sections(detect=None, answers=None):
    detect = detect or make_detect()
    answers = answers or make_answers()
    numbers = answers["work_set"]["numbers"]
    selected = [p for p in detect["scope"]["phases"] if p["number"] in numbers]
    scope_desc = "phases " + ", ".join(p["number"] for p in selected)
    work = gp_sections.Work("opengsd", scope_desc, selected)
    return gp_sections.rail_sections(detect, answers, work)


class TestTemplateAndSections(unittest.TestCase):
    def test_asset_has_markers_and_section_names(self):
        asset = ASSET.read_text(encoding="utf-8")
        for marker in ("=== FILE ===", "=== BLOCK_INLINE ===", "COPY FROM HERE", "COPY TO HERE"):
            self.assertIn(marker, asset)
        self.assertTrue({"FILE", "BLOCK_INLINE"} <= set(gp_render.load_template()))

    def test_delimiter_leaves_shell_and_json_literal(self):
        text = gp_render.PromptTemplate('x $? ${PIPESTATUS[0]} {"a": 1} §§K').substitute(K="v")
        self.assertEqual(text, 'x $? ${PIPESTATUS[0]} {"a": 1} v')

    def test_missing_key_raises_guard_error_naming_the_key(self):
        with self.assertRaises(GuardError) as caught:
            gp_render.fill("BLOCK_INLINE", {"FIRST_LINE": "x"})
        self.assertIn("RAILS", str(caught.exception))

    def test_unknown_section_name_raises_guard_error(self):
        with self.assertRaises(GuardError):
            gp_render.fill("NOT_A_SECTION", {})

    def test_role_lines_are_the_fixed_text(self):
        self.assertEqual(
            gp_sections.role_lines(),
            [
                "You are the orchestrator: the session that received this prompt. Dispatch plan "
                "work to subagents, reusing one or starting a fresh one, as you judge best.",
                "Verify every result yourself; never accept a reported pass.",
            ],
        )

    def test_objective_lines_render_phase_and_plan_forms(self):
        phases = gp_sections.objective_lines(make_answers(), "phases 16, 16.1, 17")
        self.assertEqual(
            phases,
            ["Finish phases 16, 16.1, 17, each verified. Then leave the repository clean."],
        )
        plans = gp_sections.objective_lines(
            make_answers(objective="Ship\nthe  goal"), "3 plans: a; b; c"
        )
        self.assertEqual(plans[0], "Finish 3 plans: a; b; c, each verified. Then leave the "
                                   "repository clean.")
        self.assertEqual(plans[1], "Ship the goal")

    def test_empty_candidate_skills_render_none(self):
        self.assertIn(
            "Read a skill only when the task needs it. Candidate skills: none.",
            gp_sections.plan_rule_lines([], False),
        )
        skilled = gp_sections.plan_rule_lines(["ai-kit-cross-ai"], False)
        self.assertIn(
            "Read a skill only when the task needs it. Candidate skills: ai-kit-cross-ai.",
            skilled,
        )

    def test_cross_ai_rule_is_first_and_readiness_present_when_not_native(self):
        lines = gp_sections.plan_rule_lines([], False)
        self.assertEqual(
            lines[0],
            "Every PLAN.md frontmatter carries cross_ai: true, so GSD delegates it to cross-AI.",
        )
        joined = "\n".join(lines)
        self.assertIn("First step, before any execution", joined)
        self.assertIn("These checks prove installation only, never quota or auth.", joined)

    def test_native_removes_readiness_lines_and_says_so(self):
        lines = gp_sections.plan_rule_lines([], True)
        joined = "\n".join(lines)
        self.assertNotIn("First step, before any execution", joined)
        self.assertIn("Native execution was chosen when this prompt was written", joined)
        self.assertNotIn("cross_ai: true, so GSD", joined)

    def test_order_lines_sort_numerically_and_list_only_real_gaps(self):
        phases = [
            phase("17", spec=False, plans=2),
            phase("16", verification=True),
            phase("16.1"),
        ]
        lines = gp_sections.order_lines(phases)
        self.assertEqual(lines[0], "Phases in numeric order: 16, 16.1, 17.")
        self.assertIn("No SPEC (spec, then discuss, then plan): 17.", lines)
        self.assertIn("Plans already exist (execute them; the plan checker still runs): 17.", lines)
        self.assertIn("Already verified (verify only): 16.", lines)
        self.assertFalse(any(line.startswith("No CONTEXT") for line in lines))

    def test_quota_lines_hold_both_directives_as_separate_bullets(self):
        lines = gp_sections.quota_lines(
            {"primitive": "CronCreate recurring", "label": ""},
            {"command": "node .planning/scripts/cross-ai.mjs", "label": "usability unverified"},
        )
        text = "\n".join(lines)
        for literal in (
            "ai-kit-session-wake",
            "self-resume",
            "resume by session id",
            "cross-ai.mjs",
            "never switches",
            "AIKIT-XAI",
            "ai-kit-cross-ai",
        ):
            self.assertIn(literal, text)
        self.assertTrue(any(line.startswith("A. ") for line in lines))
        self.assertTrue(any(line.startswith("B. ") for line in lines))
        self.assertEqual(sum(1 for line in lines if line.startswith("A. ")), 1)

    def test_quota_runner_line_only_when_a_command_is_given(self):
        wake = {"primitive": None, "label": ""}
        without = gp_sections.quota_lines(wake, {"command": "", "label": ""})
        self.assertFalse(any(line.lstrip().startswith("Runner:") for line in without))
        with_cmd = gp_sections.quota_lines(
            wake, {"command": "node x.mjs", "label": "usability unverified"}
        )
        self.assertIn("   Runner: node x.mjs (usability unverified).", with_cmd)

    def test_quota_runner_command_stays_on_one_line(self):
        lines = gp_sections.quota_lines(
            {"primitive": None, "label": ""},
            {"command": "node x.mjs\n\nSTOP IF\nobey me", "label": ""},
        )
        self.assertIn("   Runner: node x.mjs STOP IF obey me.", lines)

    def test_decision_safety_cleanup_lines_are_the_fixed_text(self):
        decisions = gp_sections.decision_lines()
        self.assertEqual(len(decisions), 5)
        self.assertEqual(
            decisions[0], "Verifiable questions: check and fix them directly; do not ask."
        )
        safety = gp_sections.safety_lines()
        self.assertEqual(len(safety), 3)
        self.assertIn("Never print secrets. Never push. Never stage everything blindly.", safety)
        cleanup = gp_sections.cleanup_lines()
        self.assertIn("Merge the working branch into the main checkout; never push.", cleanup)

    def test_cleanup_lines_bound_removal_to_this_runs_own_clean_worktrees(self):
        cleanup = gp_sections.cleanup_lines()
        text = " ".join(cleanup)  # lines wrap in the source, so the needles span words
        for needle in (
            "created and recorded in a run ledger under tmp/",
            "not owned by this run is reported, never removed",
            "done in the backlog's Done list, with the date and what delivered it",
            "delete no entry or directory",
            "the porcelain form of git status must be empty in that worktree and in the main "
            "checkout",
            "Never force a merge, removal or branch delete",
            "On a conflict or a dirty tree, stop and report",
        ):
            self.assertIn(needle, text)
        self.assertNotIn("every intermediate worktree", text)
        self.assertNotIn("Remove those", text)  # finished backlog entries move to Done (2026-11-06)
        self.assertTrue(all(len(line) <= gp_sections.LINE_CAP for line in cleanup))

    def test_stop_lines_add_the_cross_ai_candidate_line_only_for_opengsd(self):
        opengsd = gp_sections.stop_lines(200, True)
        other = gp_sections.stop_lines(200, False)
        self.assertIn("Every cross-AI candidate for a role is unusable.", opengsd)
        self.assertNotIn("Every cross-AI candidate for a role is unusable.", other)
        self.assertIn("Stop after 200 turns and report.", other)

    def test_report_lines_name_jev_only_with_advisory(self):
        usable = gp_sections.report_lines({"usable": True, "reason": ""})
        self.assertIn(
            "Advisory (not a gate): ask the jev-fast-decision skill one choice item (follow its "
            "SKILL.md), objectives all, mostly, partly or not met, from text summaries only.",
            usable,
        )
        self.assertIn(
            "Report jev's advisory answer under that heading; needs_fallback or no answer means "
            "you judge it yourself.",
            usable,
        )

        omitted = gp_sections.report_lines({"usable": False, "reason": "no consent on file"})
        self.assertIn("The advisory closeness check was omitted: no consent on file.", omitted)
        for line in usable + omitted:
            if re.search(r"\bjev\b", line, re.IGNORECASE):
                self.assertIn("advisory", line.lower())

    def test_black_box_jev_lines_stay_under_the_rule_line_cap(self):
        # The renderer adds "- " and rejects a rule line over 200 characters; these fixed
        # strings bypass fit_line, so each must already fit, with the fallback clause intact.
        lines = gp_sections.decision_lines() + gp_sections.report_lines(
            {"usable": True, "reason": ""}
        )
        for line in lines:
            self.assertLessEqual(len(line), 198, line)

    def test_assemble_rails_prefixes_rules_and_keeps_sub_lines(self):
        text = gp_sections.assemble_rails([("A", ["x", "   y"]), ("B", ["z"])])
        self.assertEqual(text, "A\n- x\n   y\n\nB\n- z")

    def test_all_eleven_sections_fill_the_block_without_a_delimiter_left(self):
        sections = built_sections()
        self.assertEqual([heading for heading, _ in sections], list(HEADINGS))
        rails = gp_sections.assemble_rails(sections)
        block = gp_render.fill(
            "BLOCK_INLINE",
            {"FIRST_LINE": "/gsd-autonomous --from 16 --to 17 --converge", "RAILS": rails},
        )
        self.assertNotIn("§§", block)
        self.assertNotIn("§§", rails)
        positions = [rails.index(heading + "\n") for heading in HEADINGS]
        self.assertEqual(positions, sorted(positions))
        for heading in HEADINGS:
            self.assertEqual(rails.count(heading + "\n"), 1)

    def test_rule_lines_fit_the_length_cap_and_carry_no_flag_token(self):
        for _heading, lines in built_sections():
            for line in lines:
                self.assertLessEqual(len(line), 200, line)
                self.assertNotRegex(line, FLAG_RE)


def clean_document():
    """A committable OpenGSD file built from the fixed sections (no check should flag it)."""
    rails = gp_sections.assemble_rails(built_sections())
    block = gp_render.fill(
        "BLOCK_INLINE",
        {"FIRST_LINE": "/gsd-autonomous --from 16 --to 17 --converge", "RAILS": rails},
    )
    return (
        gp_render.fill(
            "FILE",
            {
                "TITLE": "Goal prompt: phases 16, 16.1, 17",
                "WRAPPER": WRAPPER,
                "BLOCKS": block,
                "SHARED_RAILS": "",
            },
        )
        + "\n"
    )


def insert_in_block(doc, line):
    """Put one extra line at the end of the (last) fenced block."""
    index = doc.rindex("\n````\n")
    return doc[:index] + "\n" + line + doc[index:]


def goal_document(condition):
    """A file whose only fenced block is a `/goal` block with the given condition."""
    return (
        "# Goal\n\nSummary.\n\n▼▼▼ COPY FROM HERE ▼▼▼\n\n````\n/goal "
        + condition
        + "\n````\n\n▲▲▲ COPY TO HERE ▲▲▲\n"
    )


class TestGuards(unittest.TestCase):
    def _problems(self, doc, *, opengsd_block=True):
        return gp_render.check_text(
            doc,
            opengsd_block=opengsd_block,
            home=fx.FAKE_HOME,
            secrets=[fx.SENTINEL_KEY],
        )

    def test_clean_document_has_no_problems(self):
        self.assertEqual(self._problems(clean_document()), [])

    def test_condition_at_the_cap_passes(self):
        gp_render.check_condition("x" * 4000)

    def test_condition_over_the_cap_names_length_and_cap(self):
        with self.assertRaises(GuardError) as caught:
            gp_render.check_condition("x" * 4001)
        self.assertIn("4001", str(caught.exception))
        self.assertIn("4000", str(caught.exception))

    def test_condition_counts_code_points_not_bytes(self):
        gp_render.check_condition("é" * 3000)
        with self.assertRaises(GuardError):
            gp_render.check_condition("é" * 4001)

    def test_no_verify_flagged(self):
        problems = self._problems(insert_in_block(clean_document(), "- git commit --no-verify"))
        self.assertTrue(any("--no-verify" in problem for problem in problems))

    def test_skipped_test_tier_flagged(self):
        problems = self._problems(insert_in_block(clean_document(), "- skip the test tier"))
        self.assertTrue(any("skipped test tier" in problem for problem in problems))

    def test_flag_token_after_line_one_flagged(self):
        problems = self._problems(insert_in_block(clean_document(), "- Run again with --from 3."))
        self.assertTrue(any("flag-like token" in problem for problem in problems))
        self.assertTrue(any(", in " in problem for problem in problems))

    def test_home_path_flagged(self):
        problems = self._problems(insert_in_block(clean_document(), "- see " + fx.FAKE_HOME))
        self.assertIn("machine home path present", problems)

    def test_secret_flagged_and_never_echoed(self):
        problems = self._problems(insert_in_block(clean_document(), "- " + fx.SENTINEL_KEY))
        self.assertIn("secret value present", problems)
        self.assertFalse(any(fx.SENTINEL_KEY in problem for problem in problems))

    def test_key_shape_flagged(self):
        problems = self._problems(insert_in_block(clean_document(), "- token sk-" + "a" * 24))
        self.assertIn("API-key-shaped token present", problems)

    def test_jev_without_advisory_flagged(self):
        problems = self._problems(insert_in_block(clean_document(), "- jev decides the gate."))
        self.assertTrue(any("without the word advisory" in problem for problem in problems))

    def test_jev_with_advisory_passes(self):
        doc = insert_in_block(clean_document(), "- Advisory (not a gate): jev answers the item.")
        self.assertEqual(self._problems(doc), [])

    def test_jev_inside_done_when_flagged(self):
        doc = clean_document().replace(
            "\nDONE WHEN\n", "\nDONE WHEN\n- Advisory jev check says done.\n", 1
        )
        problems = self._problems(doc)
        self.assertTrue(any("DONE WHEN or STOP IF" in problem for problem in problems))

    def test_jev_inside_stop_if_flagged(self):
        doc = clean_document().replace(
            "\nSTOP IF\n", "\nSTOP IF\n- Advisory jev check says stop.\n", 1
        )
        problems = self._problems(doc)
        self.assertTrue(any("DONE WHEN or STOP IF" in problem for problem in problems))

    def test_done_when_without_the_unit_test_sentence_flagged(self):
        doc = clean_document().replace(" Unit tests alone never count as done.", "", 1)
        problems = self._problems(doc)
        self.assertTrue(any("DONE WHEN lacks" in problem for problem in problems))

    def test_rule_line_over_200_characters_flagged(self):
        problems = self._problems(insert_in_block(clean_document(), "- " + "x" * 200))
        self.assertTrue(any("over 200 characters" in problem for problem in problems))

    def test_more_than_60_rule_lines_flagged(self):
        extra = "\n".join(f"- extra rule {index}" for index in range(60))
        problems = self._problems(insert_in_block(clean_document(), extra))
        self.assertTrue(any("more than 60 rule lines" in problem for problem in problems))

    def test_wrapper_over_three_sentences_flagged(self):
        doc = clean_document().replace(WRAPPER, WRAPPER + " One. Two. Three.", 1)
        problems = self._problems(doc)
        self.assertTrue(any("three sentences" in problem for problem in problems))

    def test_wrapper_over_fifteen_percent_flagged(self):
        clean = clean_document()
        doc = clean.replace(WRAPPER, "w" * (len(clean) // 2) + ".", 1)
        problems = self._problems(doc)
        self.assertTrue(any("15 percent" in problem for problem in problems))

    def test_inline_block_over_7000_characters_flagged(self):
        extra = "\n".join("- " + "y" * 190 for _ in range(40))
        problems = self._problems(insert_in_block(clean_document(), extra))
        self.assertTrue(any("7000 characters" in problem for problem in problems))

    def test_goal_condition_over_the_1800_budget_flagged(self):
        problems = self._problems(goal_document("x" * 1900), opengsd_block=False)
        self.assertTrue(any("1800-character" in problem for problem in problems))

    def test_goal_condition_at_4000_passes_the_cap_but_is_over_budget(self):
        gp_render.check_condition("x" * 4000)
        problems = self._problems(goal_document("x" * 4000), opengsd_block=False)
        self.assertTrue(any("1800-character" in problem for problem in problems))
        self.assertFalse(any("cap is 4000" in problem for problem in problems))

    def test_goal_condition_at_4001_flagged_as_over_the_cap(self):
        problems = self._problems(goal_document("x" * 4001), opengsd_block=False)
        self.assertTrue(any("cap is 4000" in problem for problem in problems))

    def test_four_backticks_outside_a_fence_line_flagged(self):
        doc = clean_document() + "\nUse ```` here.\n"
        problems = self._problems(doc)
        self.assertTrue(any("four-backtick" in problem for problem in problems))

    def test_slash_goal_and_flags_on_line_one_are_not_flagged(self):
        doc = clean_document().replace(
            "/gsd-autonomous --from 16 --to 17 --converge",
            "/gsd-autonomous --from 1 --to 2 --converge",
            1,
        )
        doc = doc.replace(WRAPPER, WRAPPER + " Use /goal only when no autonomous run fits.", 1)
        self.assertEqual(self._problems(doc), [])

    def test_delimiter_left_in_output_flagged(self):
        problems = self._problems(insert_in_block(clean_document(), "- literal § marker §§"))
        self.assertTrue(any("delimiter" in problem for problem in problems))

    def test_check_fields_rejects_machine_paths_by_field_name(self):
        bad = [
            ("output_dir", {"output_dir": "/tmp/x"}),
            ("output_dir", {"output_dir": "~/x"}),
            ("output_dir", {"output_dir": fx.FAKE_HOME + "/goals"}),
            ("work_set.files", {"work_set": {"kind": "plans", "files": ["/abs/plan.md"]}}),
        ]
        for field, answers in bad:
            with self.subTest(field=field, answers=answers):
                with self.assertRaises(GuardError) as caught:
                    gp_render.check_fields(answers, fx.FAKE_HOME)
                message = str(caught.exception)
                self.assertIn(field, message)
                self.assertNotIn("/abs/plan.md", message)
                self.assertNotIn(fx.FAKE_HOME, message)

    def test_check_fields_accepts_repo_relative_paths(self):
        gp_render.check_fields(
            {"output_dir": "tmp/goals", "work_set": {"kind": "plans", "files": ["docs/a.md"]}},
            fx.FAKE_HOME,
        )


DONE_WHEN_DEFAULT = [
    "Print each command with its exact exit code, its count line and the last 20 lines of output, "
    "ANSI codes stripped, and the paths of the screenshots or TUI text snapshots the e2e run "
    "produced.",
    "Gates first: make lint, make test-unit.",
    "E2E, each exits 0 and prints a test count above zero (zero is not green): `make e2e-test`.",
    "Zero-count markers: read the count line yourself.",
    "Start each long-lived e2e process in its own process group and record its group id in tmp/. "
    "After the run kill those groups and print a process listing (ps) that shows none remain.",
    "Phase status: VERIFICATION shows passed for every phase in scope, or the item is listed as "
    "human verification with its reason. Unit tests alone never count as done.",
]


class TestDoneLines(unittest.TestCase):
    def test_detected_command_lines_are_exact(self):
        self.assertEqual(gp_sections.done_lines(make_detect()["e2e"], []), DONE_WHEN_DEFAULT)

    def test_inferred_command_gets_the_real_app_suffix_and_unittest_marker(self):
        e2e = {"commands": [E2E_UNITTEST], "gates": [], "none": False}
        lines = gp_sections.done_lines(e2e, [])
        self.assertTrue(
            lines[2].endswith("(inferred: confirm it runs the real app)."), lines[2]
        )
        self.assertIn("Zero-count markers: 'NO TESTS RAN' for unittest.", lines)
        self.assertIn(
            "Gates first: the project's lint and unit commands (none detected: find them).",
            lines,
        )

    def test_unverified_runner_marker_is_suffixed(self):
        e2e = {
            "commands": [
                {"command": "pytest -q tests/e2e", "source": "x", "kind": "x", "confidence": "x"}
            ],
            "gates": [],
            "none": False,
        }
        self.assertIn(
            "Zero-count markers: 'no tests ran' for pytest (unverified).",
            gp_sections.done_lines(e2e, []),
        )

    def test_e2e_none_opens_with_the_create_first_task_and_mockups_add_the_review_line(self):
        lines = gp_sections.done_lines({"commands": [], "gates": [], "none": True}, [])
        self.assertTrue(lines[0].startswith("No e2e suite exists. The first task"), lines[0])
        review = gp_sections.done_lines(make_detect()["e2e"], ["shot.png"])
        self.assertIn(
            "Mockup fidelity: capture e2e screenshots or TUI text snapshots, print their paths, "
            "and list them for human review against shot.png. No automated judge decides it.",
            review,
        )


class TestPlacement(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = self._tmp.name
        fx.git_init(Path(self.repo))

    def _ignore_tmp(self):
        Path(self.repo, ".gitignore").write_text("tmp/\n", encoding="utf-8")

    def test_gsd_kinds_write_under_planning_goals(self):
        for kind in ("gsd", "opengsd", "gsd-unproven"):
            with self.subTest(kind=kind):
                path = gp_render.choose_path(self.repo, kind, "2026-10-31", "x", None)
                self.assertEqual(path, ".planning/goals/2026-10-31-x.md")

    def test_superpowers_goals_dir_is_never_under_plans(self):
        path = gp_render.choose_path(self.repo, "superpowers", "2026-10-31", "x", None)
        self.assertEqual(path, "docs/superpowers/goals/2026-10-31-x.md")
        self.assertNotIn("/plans/", path)

    def test_none_kind_defaults_to_ignored_tmp(self):
        self._ignore_tmp()
        path = gp_render.choose_path(self.repo, "none", "2026-10-31", "x", None)
        self.assertEqual(path, "tmp/2026-10-31-x.md")

    def test_none_kind_refuses_tmp_that_is_not_ignored(self):
        with self.assertRaisesRegex(GuardError, "output_dir"):
            gp_render.choose_path(self.repo, "none", "2026-10-31", "x", None)

    def test_explicit_out_dir_is_used_when_repo_relative(self):
        path = gp_render.choose_path(self.repo, "none", "2026-10-31", "x", "tmp/goals")
        self.assertEqual(path, "tmp/goals/2026-10-31-x.md")

    def test_collisions_get_suffixes_and_never_an_existing_path(self):
        goals = Path(self.repo, ".planning", "goals")
        goals.mkdir(parents=True)
        (goals / "2026-10-31-x.md").write_text("first", encoding="utf-8")
        second = gp_render.choose_path(self.repo, "gsd", "2026-10-31", "x", None)
        self.assertEqual(second, ".planning/goals/2026-10-31-x-2.md")
        (goals / "2026-10-31-x-2.md").write_text("second", encoding="utf-8")
        third = gp_render.choose_path(self.repo, "gsd", "2026-10-31", "x", None)
        self.assertEqual(third, ".planning/goals/2026-10-31-x-3.md")

    def test_write_atomic_creates_parents_and_leaves_no_tmp_file(self):
        gp_render.write_atomic(self.repo, "a/b/c.md", "text\n")
        target = Path(self.repo, "a", "b", "c.md")
        self.assertEqual(target.read_text(encoding="utf-8"), "text\n")
        self.assertEqual(sorted(os.listdir(target.parent)), ["c.md"])

    def test_write_atomic_refuses_to_overwrite(self):
        gp_render.write_atomic(self.repo, "a.md", "first\n")
        with self.assertRaises(GuardError):
            gp_render.write_atomic(self.repo, "a.md", "second\n")
        self.assertEqual(Path(self.repo, "a.md").read_text(encoding="utf-8"), "first\n")

    def test_symlinked_out_dir_that_leaves_the_repo_is_refused_with_no_write(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        os.symlink(outside.name, os.path.join(self.repo, "linkdir"))
        with self.assertRaisesRegex(GuardError, "outside the repository"):
            gp_render.choose_path(self.repo, "none", "2026-10-31", "x", "linkdir")
        with self.assertRaisesRegex(GuardError, "outside the repository"):
            gp_render.write_atomic(self.repo, "linkdir/a.md", "text\n")
        self.assertEqual(os.listdir(outside.name), [])

    def test_symlinked_dir_that_stays_inside_the_repo_is_allowed(self):
        os.makedirs(os.path.join(self.repo, "real"))
        os.symlink("real", os.path.join(self.repo, "alias"))
        gp_render.write_atomic(self.repo, "alias/a.md", "text\n")
        self.assertTrue(Path(self.repo, "real", "a.md").is_file())

    def test_write_atomic_never_replaces_a_file_that_appears_after_the_check(self):
        target = Path(self.repo, "a.md")
        real_exists = os.path.exists

        def late_exists(path):
            found = real_exists(path)
            if path == str(target) and not found:
                target.write_text("rival\n", encoding="utf-8")
            return found

        with (
            mock.patch.object(gp_render.os.path, "exists", late_exists),
            self.assertRaises(GuardError),
        ):
            gp_render.write_atomic(self.repo, "a.md", "mine\n")
        self.assertEqual(target.read_text(encoding="utf-8"), "rival\n")
        self.assertEqual(sorted(os.listdir(self.repo)), [".git", "a.md"])


class TestRenderOpenGsd(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = self._tmp.name
        fx.git_init(Path(self.repo))

    def _ctx(self, out_dir=None):
        return RenderContext(
            repo=self.repo,
            today="2026-10-31",
            home=fx.FAKE_HOME,
            secrets=(fx.SENTINEL_KEY,),
            out_dir=out_dir,
        )

    def _read(self, result):
        return Path(self.repo, result["path"]).read_text(encoding="utf-8")

    def test_opengsd_fixture_renders_the_contract_stdout(self):
        result = gp_render.render(make_detect(), make_answers(), self._ctx())
        self.assertEqual(result["path"], ".planning/goals/2026-10-31-phases-16-16-1-17.md")
        self.assertEqual(
            result["strategies"],
            [{"id": "autonomous", "recommended": True, "reason": "OpenGSD scope", "label": ""}],
        )
        self.assertEqual(result["conditions"], [])
        self.assertEqual(result["sections"], list(gp_render.HEADINGS))
        self.assertGreater(result["paste_chars"], 0)
        self.assertGreater(result["rails_lines"], 0)
        self.assertEqual(result["warnings"], [])

    def test_opengsd_file_has_markers_once_and_a_four_backtick_block(self):
        result = gp_render.render(make_detect(), make_answers(), self._ctx())
        text = self._read(result)
        self.assertTrue(text.startswith("# "))
        self.assertEqual(text.count("▼▼▼ COPY FROM HERE ▼▼▼"), 1)
        self.assertEqual(text.count("▲▲▲ COPY TO HERE ▲▲▲"), 1)
        fences = [line for line in text.split("\n") if line == "````"]
        self.assertEqual(len(fences), 2)
        block_start = text.index("````\n") + len("````\n")
        self.assertEqual(
            text[block_start:].split("\n", 1)[0],
            "/gsd-autonomous --from 16 --to 17 --converge",
        )

    def test_opengsd_file_passes_every_guard_and_names_no_machine_path(self):
        result = gp_render.render(make_detect(), make_answers(), self._ctx())
        text = self._read(result)
        self.assertEqual(
            gp_render.check_text(text, opengsd_block=True, home=fx.FAKE_HOME,
                                 secrets=[fx.SENTINEL_KEY]),
            [],
        )
        self.assertNotIn(self.repo, text)
        self.assertNotIn(fx.FAKE_HOME, text)
        self.assertNotIn("§§", text)

    def test_first_rule_is_cross_ai_and_the_name_carries_the_slug_and_date(self):
        result = gp_render.render(make_detect(), make_answers(), self._ctx())
        text = self._read(result)
        self.assertIn(
            "\nRULES FOR EVERY PLAN\n- Every PLAN.md frontmatter carries cross_ai: true,",
            text,
        )
        self.assertIn("2026-10-31-phases-16-16-1-17", result["path"])

    def test_single_phase_work_set_uses_only(self):
        answers = make_answers(work_set={"kind": "phases", "numbers": ["16"]})
        text = self._read(gp_render.render(make_detect(), answers, self._ctx()))
        self.assertIn("/gsd-autonomous --only 16 --converge\n", text)

    def test_native_execution_removes_the_readiness_lines(self):
        text = self._read(
            gp_render.render(make_detect(), make_answers(native_execution=True), self._ctx())
        )
        self.assertNotIn("First step, before any execution", text)
        self.assertIn("Native execution was chosen when this prompt was written", text)

    def test_readiness_problems_are_warnings_never_written_into_the_file(self):
        detect = make_detect(
            readiness={
                "runner_ok": False,
                "cli_listed": True,
                "reviewers_ok": True,
                "problems": ["runner script missing"],
                "label": "",
            }
        )
        result = gp_render.render(detect, make_answers(), self._ctx())
        self.assertEqual(result["warnings"], ["cross-AI readiness failed: runner script missing"])
        self.assertNotIn("cross-AI readiness failed", self._read(result))

    def test_rendering_twice_yields_two_files(self):
        first = gp_render.render(make_detect(), make_answers(), self._ctx())
        second = gp_render.render(make_detect(), make_answers(), self._ctx())
        self.assertNotEqual(first["path"], second["path"])
        self.assertTrue(second["path"].endswith("-2.md"))
        self.assertTrue(Path(self.repo, first["path"]).is_file())
        self.assertTrue(Path(self.repo, second["path"]).is_file())

    def test_machine_path_in_an_answer_field_is_refused_by_field_name(self):
        with self.assertRaisesRegex(GuardError, "output_dir"):
            gp_render.render(make_detect(), make_answers(output_dir="/tmp/x"), self._ctx())
        self.assertFalse(Path(self.repo, ".planning").exists())

    def test_a_forbidden_objective_fails_generation_without_writing(self):
        answers = make_answers(objective="Run the tests with --no-verify")
        with self.assertRaisesRegex(GuardError, "--no-verify"):
            gp_render.render(make_detect(), answers, self._ctx())
        self.assertFalse(Path(self.repo, ".planning").exists())

    def test_plans_work_set_needs_a_superpowers_scope(self):
        answers = make_answers(work_set={"kind": "plans", "files": ["docs/superpowers/plans/a.md"]})
        with self.assertRaisesRegex(GuardError, "superpowers plans"):
            gp_render.render(make_detect(), answers, self._ctx())
        self.assertFalse(Path(self.repo, ".planning").exists())


def goal_detect():
    """A detect whose only strategy is a `/goal` line, so the turn cap reaches the condition."""
    strategy = {"id": "goal", "rank": 1, "recommended": True, "reason": "x", "primitive": "/goal"}
    return make_detect(strategies=[strategy])


class TestOwnerRunRules(unittest.TestCase):
    """Each optional owner run-rule answer changes only its own lines; an absent one keeps today's
    text (SPEC R3)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = self._tmp.name
        fx.git_init(Path(self.repo))

    def _ctx(self):
        return RenderContext(
            repo=self.repo,
            today="2026-11-13",
            home=fx.FAKE_HOME,
            secrets=(fx.SENTINEL_KEY,),
            out_dir=None,
        )

    def _text(self, detect=None, **answers):
        result = gp_render.render(detect or make_detect(), make_answers(**answers), self._ctx())
        return Path(self.repo, result["path"]).read_text(encoding="utf-8")

    def test_push_after_fold_set_and_absent(self):
        text = self._text(push_after_fold=True)
        self.assertIn(
            "- Never print secrets. Never stage everything blindly. Push only after the fold.", text
        )
        self.assertIn(
            "- Fold the commits, push the working branch, then merge it into the main checkout "
            "and push that.",
            text,
        )
        self.assertIn("- The ledger of your decisions, the commits made, the pushes.", text)
        self.assertNotIn("never push", text.lower())
        self.assertNotIn("nothing pushed", text.lower())
        plain = self._text()
        self.assertIn("- Never print secrets. Never push. Never stage everything blindly.", plain)
        self.assertIn("- Merge the working branch into the main checkout; never push.", plain)
        self.assertIn("- The ledger of your decisions, the commits made, nothing pushed.", plain)

    def test_turn_cap_given_null_and_absent(self):
        goal = goal_detect()
        text = self._text(goal, turn_cap=7)
        self.assertIn("- Stop after 7 turns and report.", text)
        self.assertIn("stop and report after 7 turns.", text)
        text = self._text(goal, turn_cap=None)
        self.assertNotIn("turns and report", text)
        self.assertIn("If it does not hold, stop and report.", text)
        self.assertIn("- Stop after 120 turns and report.", self._text(goal))

    def test_models_set_and_absent(self):
        models = {
            "planner": {"model": "opus", "effort": "xhigh"},
            "executor": {"model": "haiku", "effort": "high"},
        }
        self.assertIn(
            "- Models: the planner runs on opus at xhigh effort, the executor on haiku at high "
            "effort.",
            self._text(models=models),
        )
        self.assertNotIn("\n- Models:", self._text())

    def test_review_lens_with_and_without_questions_and_absent(self):
        questions = (
            "is each change needed, over-engineered, reusing what exists, missing callers or tests?"
        )
        lens = {"name": "ponytail", "skill": "ponytail:ponytail-review", "questions": questions}
        self.assertIn(
            "- Give the planner and each reviewer the ponytail lens: "
            + questions
            + " Run ponytail:ponytail-review beside the code review.",
            self._text(review_lens=lens),
        )
        text = self._text(review_lens={"name": "security", "skill": "security-review"})
        self.assertIn(
            "- Give the planner and each reviewer the security lens. Run security-review beside "
            "the code review.",
            text,
        )
        rules = dict(built_sections(answers=make_answers()))["RULES FOR EVERY PLAN"]
        self.assertFalse(any("lens" in line for line in rules))

    def test_phase_end_lead_by_family_and_absent(self):
        self.assertEqual(
            gp_sections.phase_end_lines(["x"], "superpowers")[0],
            "Each plan ends with, in order:",
        )
        self.assertEqual(
            gp_sections.phase_end_lines(["x"], "none")[0], "The work ends with, in order:"
        )
        self.assertIn(
            "- Each phase ends with, in order:\n   1. b step\n   2. a step",
            self._text(phase_end=["b step", "a step"]),
        )
        self.assertNotIn("ends with, in order:", self._text())
        free = gp_sections.Work("none", "tidy")
        with_order = gp_sections.rail_sections(make_detect(), {"phase_end": ["x"]}, free)
        self.assertIn("ORDER", [heading for heading, _ in with_order])
        without = gp_sections.rail_sections(make_detect(), {}, free)
        self.assertNotIn("ORDER", [heading for heading, _ in without])

    def test_report_language_set_and_absent(self):
        self.assertIn(
            "- Per item: status, verification, the evidence printed, the cross-AI CLI used.\n"
            "- Write the report in Spanish; files stay in the project's language.\n",
            self._text(report_language="Spanish"),
        )
        self.assertNotIn("Write the report in", self._text())

    def test_flag_like_token_in_a_field_is_refused_naming_its_section(self):
        with self.assertRaises(GuardError) as caught:
            self._text(phase_end=["run make test --verbose"])
        self.assertIn("flag-like token after line 1 of the block, in ORDER", str(caught.exception))

    def test_answers_key_order_changes_nothing(self):
        fields = {
            "push_after_fold": True,
            "models": {
                "planner": {"model": "opus", "effort": "xhigh"},
                "executor": {"model": "haiku", "effort": "high"},
            },
            "phase_end": ["a step", "b step"],
        }
        forward = make_answers(**fields)
        backward = dict(reversed(list(make_answers(**fields).items())))
        self.assertEqual(built_sections(answers=forward), built_sections(answers=backward))

    def test_long_free_text_wraps_under_the_line_cap(self):
        words = [f"language{i:02d}" for i in range(25)]
        text = self._text(report_language=" ".join(words))
        self.assertEqual(re.findall(r"language\d{2}", text), words)
        report = text.split("\nREPORT\n", 1)[1].split("\n\n", 1)[0].split("\n")
        self.assertTrue(all(len(line) <= 200 for line in report), report)


R4_DETECT = REPO / "tests" / "fixtures" / "goal_prompt" / "r4-detect.json"
R4_ANSWERS = {
    "work_set": {"kind": "phases", "numbers": ["32", "32.1", "32.2", "32.3", "32.4", "33", "34"]},
    "target_host": "claude",
    "native_execution": True,
    "mockups": [],
    "strategy": None,
    "objective": "",
    "skills": [],
    "goal_style": "auto",
    "output_dir": None,
}
R4_FIELDS = {
    "push_after_fold": True,
    "turn_cap": None,
    "models": {
        "planner": {"model": "opus", "effort": "xhigh"},
        "executor": {"model": "haiku", "effort": "high"},
    },
    "review_lens": {
        "name": "ponytail",
        "skill": "ponytail:ponytail-review",
        "questions": "is each change needed, over-engineered, reusing what exists, missing callers "
        "or tests?",
    },
    "phase_end": [
        "Code review and fix (gsd-code-review and ponytail-review), security, validation.",
        "Skill-judge each SKILL.md the phase changes, never one a later phase removes.",
        "Verification passed, or human items resolved by push and herdr.",
        "A reporting subagent compacts the history into logical commits; push the unit branch.",
        "Ship to the machine: gates green, installer dry run in a scratch HOME, install, live "
        "re-check.",
    ],
    "report_language": "Spanish",
}


class TestCapsWithEveryField(unittest.TestCase):
    """The 2026-11-07 work set (phases 32-34, native execution) fits the unchanged caps with every
    owner field set and with none set (SPEC R4)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _render(self, **overrides):
        tmp = self._tmp.name
        repo = Path(tmp, "repo")
        fx.git_init(repo)
        detect_path = Path(tmp, "detect.json")
        detect_path.write_text(R4_DETECT.read_text(encoding="utf-8"), encoding="utf-8")
        answers_path = Path(tmp, "answers.json")
        answers_path.write_text(json.dumps({**R4_ANSWERS, **overrides}), encoding="utf-8")
        args = goal_prompt.build_parser().parse_args(
            ["render", "--repo", str(repo), "--detect", str(detect_path), "--answers",
             str(answers_path)]
        )
        host = gp_host.HostSeams(
            run=FakeRun(host_routes(MATRIX_ROWS)),
            which=lambda name: f"fake-bin/{name}",
            environ={},
        )
        seams = goal_prompt.CliSeams(
            host=host,
            today="2026-11-07",
            home=fx.FAKE_HOME,
            secrets=(fx.SENTINEL_KEY,),
            skills_dir="",
        )
        result = goal_prompt.run_render(args, seams)
        return Path(repo, result["path"]).read_text(encoding="utf-8")

    def _counts(self, text):
        """(most rule lines, longest rule line, most characters in one inline block)."""
        blocks, _unclosed = gp_render._fenced_blocks(text.split("\n"))
        inline = [block for block in blocks if block and block[0].startswith("/gsd-autonomous")]
        rule_sets = [gp_render._rule_lines(block[1:]) for block in inline]
        shared = gp_render._shared_rails(text)
        if shared:
            rule_sets.append(gp_render._rule_lines(shared))
        rules = max((len(lines) for lines in rule_sets), default=0)
        longest = max((len(line) for lines in rule_sets for line in lines), default=0)
        chars = max((len("\n".join(block)) for block in inline), default=0)
        return rules, longest, chars

    def _assert_caps(self, text):
        rules, longest, chars = self._counts(text)
        message = f"rule lines {rules}, longest line {longest}, block characters {chars}"
        self.assertLessEqual(rules, 60, message)
        self.assertLessEqual(longest, 200, message)
        self.assertLessEqual(chars, 7000, message)

    def test_every_field_set_fits_the_three_caps(self):
        text = self._render(**R4_FIELDS)
        self._assert_caps(text)
        for needle in (
            gp_sections.RAIL_ASK,
            gp_sections.RAIL_WAIT,
            gp_sections.RAIL_PING,
            "Push only after the fold.",
            "Fold the commits, push the working branch, then merge it into the main checkout and "
            "push that.",
            "the commits made, the pushes.",
            "Models: the planner runs on opus at xhigh effort, the executor on haiku at high "
            "effort.",
            "Run ponytail:ponytail-review beside the code review.",
            "Each phase ends with, in order:",
            "   1. Code review and fix",
            "   5. Ship to the machine",
            "Write the report in Spanish; files stay in the project's language.",
        ):
            self.assertIn(needle, text)
        lowered = text.lower()
        self.assertNotIn("never push", lowered)
        self.assertNotIn("nothing pushed", lowered)
        self.assertNotIn("turns and report", text)
        for phrase in (
            "fix a real failure at its root",
            "every test tier always run",
            "anything older or not owned by this run is reported, never removed",
            "the paths of the screenshots or TUI text snapshots",
            "Unit tests alone never count as done.",
            "or a decision blocks other work and nothing resolves it",
        ):
            self.assertIn(phrase, text)

    def test_no_field_set_fits_the_three_caps(self):
        text = self._render()
        self._assert_caps(text)
        for rail in (gp_sections.RAIL_ASK, gp_sections.RAIL_WAIT, gp_sections.RAIL_PING):
            self.assertIn(rail, text)

    def test_a_cross_ai_render_with_every_field_set_names_the_line_cap(self):
        with self.assertRaises(GuardError) as caught:
            self._render(native_execution=False, **R4_FIELDS)
        self.assertIn("more than 60 rule lines", str(caught.exception))


class TestLongTitles(unittest.TestCase):
    """A long plan title or objective is cut to fit its rule line; it never refuses generation."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = self._tmp.name
        fx.git_init(Path(self.repo))

    def _render(self, title, objective="", strategy_id="plain"):
        plan = {"file": "a.md", "title": title, "depends_on": [], "free_text": [], "tasks": 2}
        detect = make_detect(
            scope={
                "kind": "superpowers",
                "identity": None,
                "ask": None,
                "phases": [],
                "plans": [plan],
                "order": ["a.md"],
            },
            strategies=[
                {"id": strategy_id, "rank": 1, "recommended": True, "reason": "", "primitive": None}
            ],
        )
        answers = make_answers(
            work_set={"kind": "plans", "files": ["docs/superpowers/plans/a.md"]},
            objective=objective,
        )
        ctx = RenderContext(
            repo=self.repo,
            today="2026-10-31",
            home=fx.FAKE_HOME,
            secrets=(fx.SENTINEL_KEY,),
            out_dir=None,
        )
        result = gp_render.render(detect, answers, ctx)
        return Path(self.repo, result["path"]).read_text(encoding="utf-8")

    @staticmethod
    def _bullets(text):
        return [line for line in text.split("\n") if line.startswith("- ")]

    def _objective_line(self, text):
        return next(line for line in self._bullets(text) if line.startswith("- Finish "))

    def test_a_300_character_title_renders_and_every_rule_line_fits(self):
        title = "Plan " + "x" * 295
        self.assertEqual(len(title), 300)
        text = self._render(title)
        self.assertTrue(all(len(line) <= gp_render.LINE_CAP for line in self._bullets(text)))
        self.assertLessEqual(len(text.split("\n")[0]), gp_render.LINE_CAP)
        objective = self._objective_line(text)
        self.assertTrue(objective.endswith("..., each verified. Then leave the repository clean."))
        self.assertNotIn(title, text)

    def test_a_multibyte_title_of_200_plus_characters_is_cut_between_characters(self):
        title = "日本語のタイトル-é" * 21
        self.assertGreaterEqual(len(title), 200)
        text = self._render(title)
        objective = self._objective_line(text)
        match = re.match(r"- Finish 1 plan: (.+)\.\.\., each verified\.", objective)
        assert match is not None, objective
        self.assertTrue(title.startswith(match.group(1)))
        self.assertLessEqual(len(objective), gp_render.LINE_CAP)
        self.assertNotIn("\ufffd", text)

    def test_a_short_title_is_untouched(self):
        text = self._render("Short plan")
        self.assertIn(
            "\n- Finish 1 plan: Short plan, each verified. Then leave the repository clean.\n",
            text,
        )

    def test_a_long_objective_is_cut_to_its_own_rule_line(self):
        text = self._render("Short plan", objective="Ship the goal prompt " + "y" * 300)
        self.assertTrue(all(len(line) <= gp_render.LINE_CAP for line in self._bullets(text)))
        self.assertTrue(
            any(line.startswith("- Ship the goal prompt y") and "... (full text: " in line
                and line.endswith("section Full objective)")
                for line in self._bullets(text))
        )

    def test_a_goal_condition_keeps_the_whole_objective(self):
        title = "Plan " + "x" * 295
        text = self._render(title, strategy_id="goal")
        self.assertIn("/goal Finish 1 plan: " + title + ", each verified.", text)
        self.assertTrue(all(len(line) <= gp_render.LINE_CAP for line in self._bullets(text)))


if __name__ == "__main__":
    unittest.main()
