"""Doc-contract tests for spec-config's question flow, skeleton and docs (36-24, 36-25, 36-28)."""

import os
import re
import shlex
import sys
import unittest
from pathlib import Path

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import cli, lane_data_use

REPO = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO / "skills" / "ai-kit-spec-config"
FLOW = SKILL_DIR / "references" / "wizard-flow.md"
FREE = SKILL_DIR / "references" / "free-lanes.md"
SELECTION = SKILL_DIR / "references" / "cli-model-selection.md"
RUN_LINE = re.compile(r"^- Run: `([^`]+)`$", re.MULTILINE)
LINK = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
FLOW_COMMANDS = ("propose-lanes", "check-reviewer", "check-code-index-alternative")
FLOW_HEADINGS = (
    "## 1. Preferred runtimes per purpose",
    "## 2. Catalog inputs",
    "## 3. Proposal per purpose",
    "## 4. Free lanes",
    "## 5. Pair and effort per chosen lane",
    "## 6. Test the pair",
    "## 7. Session default",
    "## 8. Alternative lane",
    "## 9. Order per role",
    "## 10. Escalation",
    "## 11. Mode, strategy and timeouts",
)
PROPOSE_REVIEW_RUN = "- Run: `propose-lanes --purpose review"
CHECK_RUN = "- Run: `check-reviewer"
CODE_INDEX_RUN = "- Run: `check-code-index-alternative"
UNKNOWN_FIELDS_LINE = "An alias row or a model the owner names has no price or effort fields"
PLANTED_BAD_PURPOSE = "- Run: `propose-lanes --purpose both --catalog-path c --detect`"
PLANTED_OTHER_COMMAND = "- Run: `catalog-report --catalog-path c --detect`"
NO_EFFORT_LINE = "the runner has no effort flag for <runtime> yet, so no effort is stored"
ESCALATION_LINE = "stored and informational; no run reads them yet"
ALLOWANCE_LINE = "This test call spends part of the lane's allowance."
HERDR_LINE = "never in a herdr pane or by another agent"
PROPOSAL_KEYS = ("default_view", "pool", "wider", "zero_price", "aliases", "empty", "message",
                 "ranker_reason", "efforts", "efforts_refused", "efforts_source", "price",
                 "data_use_needed")
EFFORT_PROBE_WORDS = ("effort_probe", "accepted", "rejected", "inconclusive", "ignored",
                      "label", "error", "reason")
FREE_HEADINGS = (
    "## a. Data use first",
    "## b. Pool and usage limit",
    "## c. What is written",
    "## d. Fallback rule",
    "## e. Alternative lane",
    "## f. Who asks",
)
DECLINE_LINE = ("A no or a skip writes no lane: the lane leaves the set and no further question"
                " is asked about it.")
UNKNOWN_LINE = "A missing or unreadable source is `unknown`, never a safe value."
LABEL_LINE = "`verified` only when the vendor's own documentation page was read in this run"
POOL_WARNING = ("Free models of <provider> appear to share one pool (reported by users, not"
                " confirmed by the vendor): another free model of <provider> is not a fallback"
                " for this one.")
FLAG_LINE = "Only a yes writes `usage_limited = true`"
FALLBACK_LINE = ("A usage-limited lane's fallback is the first lane of the same role, in that"
                 " role's order, that is neither usage-limited nor in the same pool")


def run_line_problems(text, allowed) -> list[str]:
    problems = []
    lines = RUN_LINE.findall(text)
    for command in lines:
        args = shlex.split(command)
        if not args or args[0] not in allowed:
            problems.append(f"unknown command: {command}")
            continue
        try:
            cli._build_parser().parse_args(args)
        except SystemExit:
            problems.append(f"invalid command: {command}")
    if not lines:
        problems.append("no documented commands")
    return problems


def section(text, heading) -> str:
    lines = text.splitlines()
    if heading not in lines:
        return ""
    result = []
    for line in lines[lines.index(heading) + 1:]:
        if line.startswith("## "):
            break
        result.append(line)
    return "\n".join(result)


def link_problems(path) -> list[str]:
    return [f"{path.name}: {target}" for target in LINK.findall(path.read_text(encoding="utf-8"))
            if not target.startswith(("http://", "https://"))
            and not (path.parent / target).exists()]


class TestWizardFlowText(unittest.TestCase):
    def setUp(self):
        self.flow = FLOW.read_text(encoding="utf-8")
        self.selection = SELECTION.read_text(encoding="utf-8")

    def test_steps_in_order(self):
        lines = self.flow.splitlines()
        indexes = [lines.index(heading) for heading in FLOW_HEADINGS]
        self.assertEqual(indexes, sorted(set(indexes)))

    def test_run_lines_parse(self):
        self.assertEqual([], run_line_problems(self.flow, FLOW_COMMANDS))
        self.assertTrue(run_line_problems(PLANTED_BAD_PURPOSE, FLOW_COMMANDS))
        self.assertTrue(run_line_problems(PLANTED_OTHER_COMMAND, FLOW_COMMANDS))

    def test_proposal_runs_before_any_effort_probe(self):
        self.assertLess(self.flow.index(PROPOSE_REVIEW_RUN), self.flow.index(CHECK_RUN))

    def test_effort_rules(self):
        text = section(self.flow, FLOW_HEADINGS[4])
        for word in (NO_EFFORT_LINE, "efforts_refused", "efforts_source", *EFFORT_PROBE_WORDS):
            self.assertIn(word, text)
        self.assertNotIn("build-command", text)
        lines = [line for line in self.flow.splitlines() if line.startswith(CHECK_RUN)]
        self.assertEqual(len(lines), 1)
        self.assertIn(" --effort ", lines[0])
        self.assertNotIn("--catalog-path", lines[0])

    def test_orders_and_escalation(self):
        order = section(self.flow, FLOW_HEADINGS[8])
        self.assertIn("[lanes.policy.review]", order)
        self.assertIn("[lanes.policy.execute]", order)
        escalation = section(self.flow, FLOW_HEADINGS[9])
        self.assertIn(ESCALATION_LINE, escalation)
        self.assertIn("two or more lanes", escalation)

    def test_proposal_keys_named(self):
        for key in PROPOSAL_KEYS:
            self.assertIn(f"`{key}`", self.flow)

    def test_allowance_line_before_every_free_lane_call(self):
        s5 = section(self.flow, FLOW_HEADINGS[4])
        self.assertLess(s5.index(ALLOWANCE_LINE), s5.index(CHECK_RUN))
        self.assertIn(ALLOWANCE_LINE, section(self.flow, FLOW_HEADINGS[5]))

    def test_unknown_fields_rule(self):
        text = section(self.flow, FLOW_HEADINGS[2])
        self.assertIn(UNKNOWN_FIELDS_LINE, text)
        self.assertIn("never zero", text)
        self.assertIn("a model the owner named", section(self.flow, FLOW_HEADINGS[4]))

    def test_code_index_check_runs_before_the_write(self):
        self.assertTrue(any(line.startswith(CODE_INDEX_RUN)
                            for line in section(self.flow, FLOW_HEADINGS[5]).splitlines()))
        self.assertLess(self.flow.index(CODE_INDEX_RUN), self.flow.index(FLOW_HEADINGS[10]))

    def test_catalog_inputs_point_to_the_proposal(self):
        for word in ("propose-lanes", "wizard-flow.md"):
            self.assertIn(word, self.selection)
        for word in ("score_candidates", "python3 -c", "no_exec"):
            self.assertNotIn(word, self.selection)

    def test_no_seed_flag_in_spec_config_text(self):
        for path in SKILL_DIR.rglob("*.md"):
            if "evals" not in path.parts:
                self.assertNotIn("review_only", path.read_text(encoding="utf-8"), str(path))

    def test_selection_links_resolve(self):
        self.assertEqual([], link_problems(SELECTION))


class TestFreeLanesText(unittest.TestCase):
    def setUp(self):
        self.free = FREE.read_text(encoding="utf-8")
        self.flow = FLOW.read_text(encoding="utf-8")

    def test_sections_in_order(self):
        lines = self.free.splitlines()
        indexes = [lines.index(heading) for heading in FREE_HEADINGS]
        self.assertEqual(indexes, sorted(set(indexes)))

    def test_data_use_comes_first_and_a_decline_writes_no_lane(self):
        text = section(self.free, FREE_HEADINGS[0])
        for phrase in ("before anything else about the lane", DECLINE_LINE, UNKNOWN_LINE,
                       LABEL_LINE):
            self.assertIn(phrase, text)
        self.assertIn("free-lanes.md", section(self.flow, FLOW_HEADINGS[3]))

    def test_data_use_record_matches_the_code(self):
        for item in (*lane_data_use.DATA_USE_KEYS, *lane_data_use.DATA_USE_VALUES,
                     *lane_data_use.DATA_USE_LABELS):
            self.assertIn(f"`{item}`", self.free)

    def test_no_data_use_command(self):
        self.assertTrue(all(line.startswith("propose-lanes ")
                            for line in RUN_LINE.findall(self.free)))
        self.assertEqual([], run_line_problems(self.free, ("propose-lanes",)))

    def test_pool_warning_and_owner_flag(self):
        text = section(self.free, FREE_HEADINGS[1])
        self.assertIn(POOL_WARNING, text)
        self.assertIn(FLAG_LINE, text)
        self.assertIn("pool_key", section(self.free, FREE_HEADINGS[2]))

    def test_fallback_and_alternative(self):
        self.assertIn(FALLBACK_LINE, section(self.free, FREE_HEADINGS[3]))
        text = section(self.free, FREE_HEADINGS[4])
        match = RUN_LINE.search(text)
        self.assertIsNotNone(match)
        assert match is not None
        self.assertIn("--avoid-pool", match.group(1))
        self.assertIn("--skip", match.group(1))
        for phrase in ("Nothing refuses the role", "that lane's own pool only",
                       "two runs, each avoiding only its own pool"):
            self.assertIn(phrase, text)

    def test_questions_stay_with_the_owner(self):
        self.assertIn(HERDR_LINE, self.free)
        self.assertIn(HERDR_LINE, self.flow)

    def test_flow_and_free_links_resolve(self):
        self.assertEqual([], link_problems(FREE) + link_problems(FLOW))


if __name__ == "__main__":
    unittest.main()
