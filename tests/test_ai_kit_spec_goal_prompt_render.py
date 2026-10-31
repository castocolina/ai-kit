"""Tests for the goal-prompt renderer: template, guards, sections and placement (GPS-02..04).

SPEC R3; D-12..D-15, D-25..D-28. Everything is pure text or a temporary directory: no model call,
no network, no real HOME. `render` writes only inside a TemporaryDirectory git repository.
"""

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "skills" / "ai-kit-spec-goal-prompt" / "scripts"
ASSET = REPO / "skills" / "ai-kit-spec-goal-prompt" / "assets" / "prompt-template.md"
sys.path.insert(0, str(SCRIPTS))
import gp_render
import gp_sections
from gp_common import GuardError
from gp_render import RenderContext

from tests import goal_prompt_fixtures as fx

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
    return gp_sections.rail_sections(detect, answers, scope_desc, selected)


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

    def test_decision_safety_cleanup_lines_are_the_fixed_text(self):
        decisions = gp_sections.decision_lines()
        self.assertEqual(len(decisions), 4)
        self.assertEqual(
            decisions[0], "Verifiable questions: check and fix them directly; do not ask."
        )
        safety = gp_sections.safety_lines()
        self.assertEqual(len(safety), 3)
        self.assertIn("Never print secrets. Never push. Never stage everything blindly.", safety)
        cleanup = gp_sections.cleanup_lines()
        self.assertEqual(len(cleanup), 4)
        self.assertEqual(cleanup[2], "Merge the working branch into the main checkout; never push.")

    def test_stop_lines_add_the_cross_ai_candidate_line_only_for_opengsd(self):
        opengsd = gp_sections.stop_lines(200, True)
        other = gp_sections.stop_lines(200, False)
        self.assertIn("Every cross-AI candidate for a role is unusable.", opengsd)
        self.assertNotIn("Every cross-AI candidate for a role is unusable.", other)
        self.assertIn("Stop after 200 turns and report.", other)

    def test_report_lines_name_jev_only_with_advisory(self):
        usable = gp_sections.report_lines({"usable": True, "reason": ""})
        self.assertIn(
            "Advisory (not a gate): run one decide.py choice item, objectives all, mostly, "
            "partly or not met, from text summaries only; report the answer under that heading.",
            usable,
        )
        omitted = gp_sections.report_lines({"usable": False, "reason": "no consent on file"})
        self.assertIn("The advisory closeness check was omitted: no consent on file.", omitted)
        for line in usable + omitted:
            if re.search(r"\bjev\b", line, re.IGNORECASE):
                self.assertIn("advisory", line.lower())

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
        doc = clean_document().replace(
            "- Unit tests alone never count as done.", "- Tests pass.", 1
        )
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
    "ANSI codes stripped.",
    "Gates first: make lint, make test-unit.",
    "E2E: `make e2e-test` exits 0 and prints a test count above zero. Exit 0 with a zero count is "
    "not green.",
    "Zero-count markers: read the count line yourself.",
    "Print the paths of the screenshots or TUI text snapshots the e2e run produced.",
    "Start each long-lived e2e process in its own process group and record its group id in tmp/. "
    "After the run kill those groups and print a process listing (ps) that shows none remain.",
    "Phase status: VERIFICATION shows passed for every phase in scope, or the item is listed as "
    "human verification with its reason.",
    "Unit tests alone never count as done.",
]


class TestDoneLines(unittest.TestCase):
    def test_detected_command_lines_are_exact(self):
        self.assertEqual(gp_sections.done_lines(make_detect()["e2e"], []), DONE_WHEN_DEFAULT)

    def test_inferred_command_gets_the_real_app_suffix_and_unittest_marker(self):
        e2e = {"commands": [E2E_UNITTEST], "gates": [], "none": False}
        lines = gp_sections.done_lines(e2e, [])
        self.assertTrue(
            lines[2].endswith("(inferred: confirm it runs the real app)"), lines[2]
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

    def test_e2e_none_and_mockups_point_to_plan_27_08(self):
        with self.assertRaisesRegex(NotImplementedError, "27-08"):
            gp_sections.done_lines({"commands": [], "gates": [], "none": True}, [])
        with self.assertRaisesRegex(NotImplementedError, "27-08"):
            gp_sections.done_lines(make_detect()["e2e"], ["shot.png"])


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
        self.assertEqual(result["strategies"], [{"id": "autonomous", "recommended": True}])
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
            readiness={"runner_ok": False, "cli_listed": True, "reviewers_ok": True, "label": ""}
        )
        result = gp_render.render(detect, make_answers(), self._ctx())
        self.assertEqual(result["warnings"], ["cross-AI runner not ready"])
        self.assertNotIn("cross-AI runner not ready", self._read(result))

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

    def test_scopes_other_than_opengsd_wait_for_plan_27_07(self):
        detect = make_detect()
        detect["scope"]["kind"] = "superpowers"
        with self.assertRaisesRegex(NotImplementedError, "27-07"):
            gp_render.render(detect, make_answers(), self._ctx())


if __name__ == "__main__":
    unittest.main()
