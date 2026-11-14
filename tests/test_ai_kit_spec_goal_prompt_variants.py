"""Content variants of the goal-prompt rails: create-first, mockup human review and the advisory
jev step (GPS-03, GPS-04; SPEC R6, R7; D-21). Pure text and temporary repositories: no model call,
no network, no real HOME. Each render writes only inside a TemporaryDirectory git repository.
"""

import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "skills" / "ai-kit-spec-goal-prompt" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import gp_e2e
import gp_render
import gp_scope
import gp_sections
from gp_common import GuardError
from gp_render import RenderContext

from tests import goal_prompt_fixtures as fx

NO_E2E = {"commands": [], "gates": [], "none": True}
MAKE_E2E = {
    "command": "make e2e-test",
    "source": "Makefile",
    "kind": "make",
    "confidence": "confirmed",
}
CREATE_FIRST = (
    "No e2e suite exists. The first task, before any feature plan, creates one that launches the "
    "real app (a PTY drive for a terminal UI, a browser for a web UI) and make it pass."
)
EVIDENCE = (
    "Print each command with its exact exit code, its count line and the last 20 lines of "
    "output, ANSI codes stripped, and the paths of the screenshots or TUI text snapshots the e2e "
    "run produced."
)
MOCKUP_TEXT = (
    "Mockup fidelity: capture e2e screenshots or TUI text snapshots, print their paths, and list "
    "them for human review against {mockups}. No automated judge decides it."
)
ADVISORY = "Advisory (not a gate):"
# The DECISIONS gray-area line names the jev-fast-decision skill (black-box instruction); no other
# non-report line may mention jev.
GRAY_AREA_LINE = "- Gray areas:"
JEV_RE = re.compile(r"\bjev", re.IGNORECASE)
MOCKUP_OR_UI_RE = re.compile(r"mockup|screenshot|\bUI\b", re.IGNORECASE)
PATH_HEADINGS = gp_render.HEADINGS


def phase(number, *, plans=0, cross_ai=0):
    """A scope Phase as detect emits it (gp_scope.Phase field names, JSON form)."""
    return {
        "number": number,
        "name": f"Phase {number}",
        "dir": None,
        "has_spec": True,
        "has_context": True,
        "plan_count": plans,
        "has_reviews": False,
        "has_verification": False,
        "disk_status": "no_directory",
        "cross_ai_plans": cross_ai,
    }


def make_detect(**overrides):
    """A hand-built detect object carrying every field render reads (27-PATTERNS Contracts)."""
    detect = {
        "schema_version": 1,
        "scope": {
            "kind": "opengsd",
            "identity": "opengsd",
            "ask": None,
            "phases": [phase("16")],
            "plans": [],
            "order": [],
        },
        "e2e": {"commands": [MAKE_E2E], "gates": ["make lint"], "none": False},
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
        "runner": {"command": "node .planning/scripts/cross-ai.mjs", "label": ""},
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
        "work_set": {"kind": "phases", "numbers": ["16"]},
        "target_host": "claude",
        "native_execution": False,
        "mockups": [],
        "strategy": None,
        "objective": "",
        "output_dir": None,
    }
    answers.update(overrides)
    return answers


def section_map(text):
    """Lines under each labeled heading of a rendered file, keyed by heading."""
    sections, current = {}, None
    for line in text.split("\n"):
        if line in PATH_HEADINGS:
            current = line
            sections[line] = []
        elif current is not None:
            sections[current].append(line)
    return sections


class TestDoneVariants(unittest.TestCase):
    def test_no_e2e_opens_with_the_create_first_task(self):
        lines = gp_sections.done_lines(NO_E2E, [])
        self.assertEqual(lines[0], CREATE_FIRST)

    def test_no_e2e_keeps_the_generic_evidence_process_group_and_unit_clause(self):
        lines = gp_sections.done_lines(NO_E2E, [])
        self.assertIn(EVIDENCE, lines)
        self.assertTrue(any(line.startswith("Start each long-lived e2e process") for line in lines))
        self.assertTrue(
            any(line.endswith("Unit tests alone never count as done.") for line in lines)
        )

    def test_no_e2e_has_no_command_line_even_with_gates_detected(self):
        lines = gp_sections.done_lines({"commands": [], "gates": ["make lint"], "none": True}, [])
        self.assertFalse(any(line.startswith("E2E") for line in lines))
        self.assertIn("Gates first: make lint.", lines)

    def test_detected_commands_name_every_command_and_the_grep_targets(self):
        lines = gp_sections.done_lines(
            {"commands": [MAKE_E2E], "gates": ["make lint"], "none": False}, []
        )
        self.assertNotIn(CREATE_FIRST, lines)
        self.assertIn(
            "E2E, each exits 0 and prints a test count above zero (zero is not green): "
            "`make e2e-test`.",
            lines,
        )
        joined = "\n".join(lines)
        for needle in ("exit code", "count", "process group", "ps"):
            self.assertIn(needle, joined)

    def test_no_e2e_with_mockups_keeps_create_first_first_and_the_review_line(self):
        lines = gp_sections.done_lines(NO_E2E, ["docs/mockup.png"])
        self.assertEqual(lines[0], CREATE_FIRST)
        self.assertIn(MOCKUP_TEXT.format(mockups="docs/mockup.png"), lines)

    def test_mockup_adds_the_human_review_line_and_no_automated_judge(self):
        lines = gp_sections.done_lines(
            {"commands": [MAKE_E2E], "gates": [], "none": False}, ["docs/mockup.png"]
        )
        self.assertIn(MOCKUP_TEXT.format(mockups="docs/mockup.png"), lines)
        self.assertIn("No automated judge decides it.", "\n".join(lines))

    def test_mockup_descriptions_collapse_to_one_line(self):
        lines = gp_sections.done_lines(NO_E2E, ["login\n  screen,   v2.png"])
        self.assertFalse(any("\n" in line for line in lines))
        self.assertIn(MOCKUP_TEXT.format(mockups="login screen, v2.png"), lines)

    def test_no_line_mentions_jev_together_with_a_mockup_screenshot_or_ui(self):
        for e2e in (NO_E2E, {"commands": [MAKE_E2E], "gates": [], "none": False}):
            for line in gp_sections.done_lines(e2e, ["docs/mockup.png"]):
                if MOCKUP_OR_UI_RE.search(line):
                    self.assertIsNone(JEV_RE.search(line), line)

    def test_e2e_fixtures_name_the_commands_they_detect(self):
        cases = {
            "makefile": lambda root: fx.makefile(root, {"e2e-test": "x"}),
            "package-script": lambda root: fx.package_json(
                root, {"e2e": "playwright test"}, lockfile="pnpm-lock.yaml"
            ),
            "playwright": lambda root: (
                fx.package_json(root, {"ui": "playwright test"}),
                fx.playwright_config(root),
            ),
        }
        for name, build in cases.items():
            with self.subTest(fixture=name), tempfile.TemporaryDirectory() as tmp:
                fx.git_init(Path(tmp))
                build(Path(tmp))
                e2e = gp_e2e.detect_e2e(tmp)
                self.assertFalse(e2e["none"])
                lines = gp_sections.done_lines(e2e, [])
                self.assertIn(
                    "E2E, each exits 0 and prints a test count above zero (zero is not green): "
                    f"`{e2e['commands'][0]['command']}`.",
                    lines,
                )
        with tempfile.TemporaryDirectory() as tmp:
            fx.git_init(Path(tmp))
            fx.empty_project(Path(tmp))
            e2e = gp_e2e.detect_e2e(tmp)
            self.assertTrue(e2e["none"])
            self.assertEqual(gp_sections.done_lines(e2e, [])[0], CREATE_FIRST)


class TestWrapItems(unittest.TestCase):
    def test_exactly_200_characters_stays_one_line_and_201_wraps(self):
        one = gp_sections.wrap_items("H: ", ["a" * 100, "b" * 92], ".", ", ", "ORDER")
        self.assertEqual(one, ["H: " + "a" * 100 + ", " + "b" * 92 + "."])
        two = gp_sections.wrap_items("H: ", ["a" * 100, "b" * 93], ".", ", ", "ORDER")
        self.assertEqual(two, ["H: " + "a" * 100 + ",", "   " + "b" * 93 + "."])

    def test_length_counts_code_points(self):
        lines = gp_sections.wrap_items("H: ", ["é" * 100, "b" * 92], ".", ", ", "ORDER")
        self.assertEqual(lines, ["H: " + "é" * 100 + ", " + "b" * 92 + "."])

    def test_continuation_never_starts_with_the_separator_and_keeps_order(self):
        items = [f"item-{i:03d}" for i in range(60)]
        lines = gp_sections.wrap_items("L: ", items, ".", ", ", "ORDER")
        self.assertGreater(len(lines), 1)
        for line in lines[1:]:
            self.assertTrue(line.startswith("   item-"), line)
        for line in lines[:-1]:
            self.assertTrue(line.endswith(","), line)
        self.assertEqual(re.findall(r"item-\d{3}", "".join(lines)), items)
        self.assertLessEqual(len("- " + lines[0]), 200)
        for line in lines[1:]:
            self.assertLessEqual(len(line), 200)

    def test_head_with_three_spaces_is_a_sub_line(self):
        lines = gp_sections.wrap_items("   Runner: ", ["node", "x.mjs"], ".", " ", "QUOTA")
        self.assertEqual(lines, ["   Runner: node x.mjs."])

    def test_a_single_item_keeps_the_head_and_tail(self):
        lines = gp_sections.wrap_items("Candidate skills: ", ["none"], ".")
        self.assertEqual(lines, ["Candidate skills: none."])

    def test_an_item_longer_than_a_line_is_refused_naming_the_section(self):
        with self.assertRaises(GuardError) as caught:
            gp_sections.wrap_items("H: ", ["x" * 199], ".", ", ", "ORDER")
        self.assertTrue(str(caught.exception).startswith("rule line over 200 characters in ORDER"))

    def test_superpowers_order_gates_and_mockups_wrap_in_order(self):
        plans = [
            gp_scope.Plan(
                file=f"plan-{i:02d}-a-fairly-long-plan-name.md",
                title="",
                depends_on=(),
                free_text=(),
                tasks=0,
            )
            for i in range(12)
        ]
        files = [plan.file for plan in plans]
        lines = gp_sections.superpowers_order_lines(plans, files)
        self.assertTrue(lines[0].startswith("Plans in order: "))
        self.assertGreaterEqual(len(lines), 2)
        for line in lines[1:]:
            self.assertTrue(line.startswith("   "), line)
        self.assertEqual(
            re.findall(r"plan-\d{2}-a-fairly-long-plan-name\.md", "".join(lines)), files
        )
        gates = [f"make gate-{i:02d}-check" for i in range(20)]
        mockups = [f"docs/mockups/screen-{i:02d}.png" for i in range(12)]
        done = gp_sections.done_lines({"commands": [], "gates": gates, "none": True}, mockups)
        joined = "".join(done)
        self.assertEqual(re.findall(r"make gate-\d{2}-check", joined), gates)
        self.assertEqual(re.findall(r"docs/mockups/screen-\d{2}\.png", joined), mockups)
        self.assertIn("No automated judge decides it.", joined)
        for line in done:
            limit = 200 if line.startswith("   ") else 198
            self.assertLessEqual(len(line), limit, line)

    def test_a_too_long_skill_or_runner_word_is_refused_naming_its_section(self):
        with self.assertRaises(GuardError) as skill:
            gp_sections.plan_rule_lines(["a" * 199], True)
        self.assertIn("in RULES FOR EVERY PLAN", str(skill.exception))
        with self.assertRaises(GuardError) as runner:
            gp_sections.quota_lines(
                {"primitive": None, "label": ""}, {"command": "x" * 199, "label": ""}
            )
        self.assertIn("in QUOTA", str(runner.exception))


class TestJevVariants(unittest.TestCase):
    def test_usable_jev_gives_one_advisory_report_line_naming_the_skill(self):
        lines = gp_sections.report_lines({"usable": True, "reason": "local backend usable"})
        advisory = [line for line in lines if line.startswith(ADVISORY)]
        self.assertEqual(len(advisory), 1)
        self.assertIn("jev-fast-decision skill", advisory[0])
        self.assertIn("from text summaries only", advisory[0])

    def test_unusable_jev_names_the_reason_and_adds_no_advisory_line(self):
        lines = gp_sections.report_lines({"usable": False, "reason": "detect failed"})
        self.assertIn("The advisory closeness check was omitted: detect failed.", lines)
        self.assertFalse(any(line.startswith(ADVISORY) for line in lines))

    def test_rendered_advisory_jev_line_sits_in_report_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx.git_init(Path(tmp))
            ctx = RenderContext(tmp, "2026-10-31", fx.FAKE_HOME, (fx.SENTINEL_KEY,), None)
            detect = make_detect(jev={"usable": True, "reason": "local backend usable"})
            text = Path(tmp, gp_render.render(detect, make_answers(), ctx)["path"]).read_text(
                encoding="utf-8"
            )
        sections = section_map(text)
        advisory = [line for line in sections["REPORT"] if line.startswith(f"- {ADVISORY}")]
        self.assertEqual(len(advisory), 1)
        for name, lines in sections.items():
            if name != "REPORT":
                outside = [line for line in lines if not line.startswith(GRAY_AREA_LINE)]
                self.assertFalse(any(JEV_RE.search(line) for line in outside), name)

    def test_rendered_file_with_advisory_jev_passes_the_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx.git_init(Path(tmp))
            ctx = RenderContext(tmp, "2026-10-31", fx.FAKE_HOME, (fx.SENTINEL_KEY,), None)
            detect = make_detect(jev={"usable": True, "reason": "local backend usable"})
            text = Path(tmp, gp_render.render(detect, make_answers(), ctx)["path"]).read_text(
                encoding="utf-8"
            )
        self.assertEqual(
            gp_render.check_text(text, opengsd_block=True, home=fx.FAKE_HOME,
                                 secrets=[fx.SENTINEL_KEY]),
            [],
        )

    def test_unusable_jev_leaves_no_jev_line_in_the_rendered_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx.git_init(Path(tmp))
            ctx = RenderContext(tmp, "2026-10-31", fx.FAKE_HOME, (fx.SENTINEL_KEY,), None)
            detect = make_detect(jev={"usable": False, "reason": "detect failed"})
            text = Path(tmp, gp_render.render(detect, make_answers(), ctx)["path"]).read_text(
                encoding="utf-8"
            )
        self.assertIn("The advisory closeness check was omitted: detect failed.", text)
        lines = [line for line in text.split("\n") if not line.startswith(GRAY_AREA_LINE)]
        self.assertFalse(any(JEV_RE.search(line) for line in lines))

    def test_sweep_usable_jev_and_mockup_never_share_a_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx.git_init(Path(tmp))
            ctx = RenderContext(tmp, "2026-10-31", fx.FAKE_HOME, (fx.SENTINEL_KEY,), None)
            detect = make_detect(jev={"usable": True, "reason": "local backend usable"})
            answers = make_answers(mockups=["docs/mockup.png"])
            text = Path(tmp, gp_render.render(detect, answers, ctx)["path"]).read_text(
                encoding="utf-8"
            )
        self.assertIn(MOCKUP_TEXT.format(mockups="docs/mockup.png"), text)
        for line in text.split("\n"):
            if JEV_RE.search(line):
                self.assertIsNone(MOCKUP_OR_UI_RE.search(line), line)


def opengsd_scope(*phases):
    return {
        "kind": "opengsd",
        "identity": "opengsd",
        "ask": None,
        "phases": list(phases),
        "plans": [],
        "order": [],
    }


class _RenderCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = self._tmp.name
        fx.git_init(Path(self.repo))

    def _ctx(self):
        return RenderContext(self.repo, "2026-10-31", fx.FAKE_HOME, (fx.SENTINEL_KEY,), None)

    def _render(self, detect, answers=None):
        result = gp_render.render(detect, answers or make_answers(), self._ctx())
        return result, Path(self.repo, result["path"]).read_text(encoding="utf-8")


class TestCrossAiVariants(_RenderCase):
    def test_gap_line_lists_only_phases_whose_plans_lack_the_declaration(self):
        lines = gp_sections.order_lines(
            [
                phase("16", plans=2, cross_ai=2),
                phase("17", plans=2, cross_ai=1),
                phase("18"),
                phase("19", plans=1),
            ]
        )
        gap = [line for line in lines if line.startswith("Existing plans missing cross_ai")]
        self.assertEqual(
            gap, ["Existing plans missing cross_ai: true (add it, then execute): 17, 19."]
        )

    def test_gap_line_is_absent_when_every_plan_already_declares_it(self):
        lines = gp_sections.order_lines([phase("16", plans=2, cross_ai=2)])
        self.assertFalse(any("Existing plans missing" in line for line in lines))

    def test_gap_line_is_absent_for_native_execution(self):
        lines = gp_sections.order_lines([phase("17", plans=2)], native=True)
        self.assertFalse(any("Existing plans missing" in line for line in lines))

    def test_turn_cap_is_forty_per_item_and_never_below_sixty(self):
        self.assertEqual(gp_sections.turn_cap(1), 60)
        self.assertEqual(gp_sections.turn_cap(3), 120)
        self.assertEqual(gp_sections.turn_cap(12), 480)
        self.assertEqual(gp_sections.turn_cap(0), 60)

    def test_derived_cap_reaches_stop_if_and_the_goal_condition(self):
        detect = make_detect(
            scope=opengsd_scope(phase("16"), phase("16.1"), phase("17")),
            strategies=[{"id": "goal", "rank": 1, "recommended": True, "primitive": "goal"}],
        )
        answers = make_answers(work_set={"kind": "phases", "numbers": ["16", "16.1", "17"]})
        _, text = self._render(detect, answers)
        self.assertIn("Stop after 120 turns and report.", text)
        self.assertNotIn("after 200 turns", text)
        view = gp_render.BlockView(
            path=".planning/goals/x.md", objective="Finish it.", first_line="",
            rails="ROLE\n- x", turn_cap=120,
        )
        (block,) = gp_render.build_blocks([detect["strategies"][0]], view)
        self.assertIn("stop and report after 120 turns", block.condition)

    def test_native_file_says_so_plainly_and_carries_no_readiness_or_cross_ai_rule(self):
        detect = make_detect(scope=opengsd_scope(phase("17", plans=2)))
        answers = make_answers(
            work_set={"kind": "phases", "numbers": ["17"]}, native_execution=True
        )
        _, text = self._render(detect, answers)
        self.assertIn(
            "Native execution was chosen when this prompt was written: plans omit cross_ai: true "
            "and run in this session.",
            text,
        )
        self.assertNotIn("First step, before any execution", text)
        self.assertNotIn("- Every PLAN.md frontmatter carries cross_ai: true", text)
        self.assertNotIn("Existing plans missing cross_ai", text)
        self.assertNotIn("adapter", text.lower())
        self.assertNotIn("not installed", text.lower())

    def test_readiness_failure_is_a_stdout_warning_and_never_enters_the_file(self):
        readiness = {
            "runner_ok": False,
            "cli_listed": True,
            "reviewers_ok": True,
            "problems": ["runner script missing"],
            "label": "",
        }
        result, text = self._render(make_detect(readiness=readiness))
        self.assertEqual(result["warnings"], ["cross-AI readiness failed: runner script missing"])
        self.assertIn("First step, before any execution", text)
        self.assertNotIn("cross-AI readiness failed", text)

    def test_ready_readiness_gives_an_empty_warning_list(self):
        readiness = {"runner_ok": True, "cli_listed": True, "reviewers_ok": True,
                     "problems": [], "label": ""}
        result, _ = self._render(make_detect(readiness=readiness))
        self.assertEqual(result["warnings"], [])

    def test_native_execution_gives_no_readiness_warnings(self):
        readiness = {"runner_ok": False, "cli_listed": False, "reviewers_ok": False,
                     "problems": ["runner script missing"], "label": ""}
        result, _ = self._render(
            make_detect(readiness=readiness), make_answers(native_execution=True)
        )
        self.assertEqual(result["warnings"], [])

    def test_one_phase_renders_only_and_a_range_renders_from_to(self):
        detect = make_detect(scope=opengsd_scope(phase("16"), phase("16.1"), phase("17")))
        _, one = self._render(
            detect, make_answers(work_set={"kind": "phases", "numbers": ["16"]})
        )
        self.assertIn("/gsd-autonomous --only 16 --converge\n", one)
        _, several = self._render(
            detect, make_answers(work_set={"kind": "phases", "numbers": ["16", "16.1", "17"]})
        )
        self.assertIn("/gsd-autonomous --from 16 --to 17 --converge\n", several)

    def test_non_numeric_phase_number_is_a_guard_error_and_writes_nothing(self):
        detect = make_detect(scope=opengsd_scope(phase("16"), phase("17")))
        answers = make_answers(work_set={"kind": "phases", "numbers": ["16", "sixteen"]})
        with self.assertRaisesRegex(GuardError, "phase number"):
            gp_render.render(detect, answers, self._ctx())
        self.assertFalse(Path(self.repo, ".planning").exists())


class TestLongLists(_RenderCase):
    def test_forty_phases_render_with_every_phase_in_order(self):
        numbers = [f"30.{i}" for i in range(1, 41)]
        detect = make_detect(scope=opengsd_scope(*[phase(n, plans=1) for n in numbers]))
        answers = make_answers(
            work_set={"kind": "phases", "numbers": numbers}, native_execution=True
        )
        _, text = self._render(detect, answers)
        order = section_map(text)["ORDER"]

        def block(prefix):
            start = next(i for i, line in enumerate(order) if line.startswith(prefix))
            end = next(
                (i for i in range(start + 1, len(order)) if not order[i].startswith("   ")),
                len(order),
            )
            return order[start:end]

        for prefix in ("- Phases in numeric order:", "- Plans already exist"):
            with self.subTest(list=prefix):
                lines = block(prefix)
                self.assertGreaterEqual(len(lines), 2)
                self.assertEqual(re.findall(r"30\.\d+", "".join(lines)), numbers)
        fenced = [line for fence in gp_render._fenced_blocks(text.split("\n"))[0] for line in fence]
        self.assertTrue(all(len(line) <= 200 for line in fenced))
        for line in order:
            if line.strip():
                self.assertTrue(line.startswith("- ") or re.match(r"   \d", line), line)

    def test_thirty_candidate_skills_render_in_order(self):
        skills = [f"example-skill-{i:02d}" for i in range(30)]
        _, text = self._render(make_detect(candidate_skills=skills), make_answers())
        rules = section_map(text)["RULES FOR EVERY PLAN"]
        self.assertEqual(re.findall(r"example-skill-\d{2}", "".join(rules)), skills)
        fenced = [line for fence in gp_render._fenced_blocks(text.split("\n"))[0] for line in fence]
        self.assertTrue(all(len(line) <= 200 for line in fenced))

    def test_a_runner_command_over_300_characters_renders_in_order(self):
        words = [f"word{i:03d}" for i in range(40)]
        command = "node .planning/scripts/cross-ai.mjs " + " ".join(words)
        self.assertGreater(len(command), 300)
        _, text = self._render(make_detect(runner={"command": command, "label": ""}))
        quota = section_map(text)["QUOTA"]
        self.assertEqual(re.findall(r"word\d{3}", "".join(quota)), words)
        runner_lines = [
            line for line in quota if line.startswith("   Runner:") or re.match(r"   word", line)
        ]
        self.assertGreaterEqual(len(runner_lines), 2)
        fenced = [line for fence in gp_render._fenced_blocks(text.split("\n"))[0] for line in fence]
        self.assertTrue(all(len(line) <= 200 for line in fenced))

    def test_wrapped_lists_past_sixty_lines_are_still_refused(self):
        numbers = [f"30.{i}" for i in range(1, 121)]
        phases = []
        for number in numbers:
            row = phase(number, plans=1)
            row.update(has_spec=False, has_context=False, has_verification=True)
            phases.append(row)
        answers = make_answers(work_set={"kind": "phases", "numbers": numbers})
        with self.assertRaises(GuardError) as caught:
            self._render(make_detect(scope=opengsd_scope(*phases)), answers)
        self.assertIn("more than 60 rule lines", str(caught.exception))

    def test_a_300_character_e2e_command_renders_in_code_span_pieces(self):
        command = "python3 -m unittest " + " ".join(
            f"tests.test_e2e_module_{i:02d}" for i in range(12)
        )
        self.assertGreaterEqual(len(command), 300)
        e2e = {
            "commands": [
                {"command": command, "source": "x", "kind": "unittest", "confidence": "detected"}
            ],
            "gates": ["make lint"],
            "none": False,
        }
        _, text = self._render(make_detect(e2e=e2e))
        done = section_map(text)["DONE WHEN"]
        e2e_lines = [line for line in done if line.startswith(("- E2E", "   `"))]
        self.assertGreaterEqual(len(e2e_lines), 2)
        spans = re.findall(r"`([^`]*)`", "\n".join(e2e_lines))
        self.assertEqual(" ".join(spans), command)
        self.assertTrue(all(len(line) <= 200 for line in e2e_lines))


class TestRenderGuards(_RenderCase):
    def test_absolute_mockup_path_is_refused_by_field_name(self):
        answers = make_answers(mockups=["/abs/mockup.png"])
        with self.assertRaisesRegex(GuardError, "mockups"):
            gp_render.render(make_detect(), answers, self._ctx())
        self.assertFalse(Path(self.repo, ".planning").exists())

    def test_repo_relative_mockup_path_renders(self):
        result, _ = self._render(make_detect(), make_answers(mockups=["docs/mockup.png"]))
        self.assertTrue(result["path"].endswith(".md"))
