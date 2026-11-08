"""Doc-contract tests: AGENTS.md and house rules R07/R08 carry one tool-use rule text."""

import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-agents"),
)

from ai_kit_project_rules_agents import rules
from ai_kit_rules_common import code_exploration

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AGENTS_PATH = os.path.join(_REPO, "AGENTS.md")
_CODE_EXPLORATION = "## Code Exploration"
_CLAUSES = code_exploration.RULE_CLAUSES


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _section(text, heading):
    """Return the heading line through the next `## ` heading ("" when absent)."""
    padded = "\n" + text
    start = padded.find("\n" + heading + "\n")
    if start < 0:
        return ""
    end = padded.find("\n## ", start + 1)
    return padded[start + 1 : end if end >= 0 else len(padded)]


def _flat(text):
    return " ".join(text.split())


def _missing_clauses(section_text, clauses):
    flat = _flat(section_text)
    return [clause for clause in clauses if _flat(clause) not in flat]


class TestToolUseRule(unittest.TestCase):
    def setUp(self):
        self.section = _section(_read(_AGENTS_PATH), _CODE_EXPLORATION)

    def test_every_clause_is_in_agents_code_exploration(self):
        self.assertEqual(_missing_clauses(self.section, _CLAUSES), [])

    def test_removing_one_clause_reports_exactly_that_clause(self):
        # non-vacuity: each clause's removal must be caught and named, not just any clause
        for clause in _CLAUSES:
            with self.subTest(clause=clause[:40]):
                damaged = self.section.replace(f"- {clause}\n", "", 1)
                self.assertNotEqual(damaged, self.section)
                self.assertEqual(_missing_clauses(damaged, _CLAUSES), [clause])

    def test_missing_heading_reports_all_clauses(self):
        section = _section("# title\n\nno exploration heading here\n", _CODE_EXPLORATION)
        self.assertEqual(section, "")
        self.assertEqual(len(_missing_clauses(section, _CLAUSES)), len(_CLAUSES))
        self.assertEqual(len(_CLAUSES), 13)

    def test_summaries_join_the_clauses_at_the_stated_indexes(self):
        self.assertEqual(
            code_exploration.R07_SUMMARY,
            " ".join(_CLAUSES[i] for i in code_exploration.R07_CLAUSES),
        )
        self.assertEqual(
            code_exploration.R08_SUMMARY,
            " ".join(_CLAUSES[i] for i in code_exploration.R08_CLAUSES),
        )

    def test_summaries_name_their_signals(self):
        for token in ("codegraph", "codegraph_explore", ".codegraph"):
            self.assertIn(token, code_exploration.R07_SUMMARY)
        for token in ("graphify", "graph.json", "graphify-out"):
            self.assertIn(token, code_exploration.R08_SUMMARY)


class TestHouseRulesCarryTheSharedSummaries(unittest.TestCase):
    def _entry(self, rule_id):
        return next(rule for rule in rules.RULES if rule["id"] == rule_id)

    def test_r07_and_r08_summaries_are_the_shared_constants(self):
        self.assertEqual(self._entry("R07")["summary"], code_exploration.R07_SUMMARY)
        self.assertEqual(self._entry("R08")["summary"], code_exploration.R08_SUMMARY)

    def test_r07_and_r08_keep_their_signals_and_criticality(self):
        self.assertEqual(
            self._entry("R07")["signals"], ("codegraph", "codegraph_explore", ".codegraph")
        )
        self.assertEqual(
            self._entry("R08")["signals"], ("graphify", "graph.json", "graphify-out")
        )
        for rule_id in ("R07", "R08"):
            self.assertEqual(self._entry(rule_id)["criticality"], rules.CRITICALITY_MEDIUM)
            self.assertEqual(self._entry(rule_id)["category"], "workflow")


_DESIGN_MARKER = "- **Design rule**:"
_DESIGN_CLAUSES = (
    "Simple is not the same as easy.",
    "Prefer the simple design over the complex one",
    "never recommend the easier option when it gives the user less value only to skip a "
    "few steps that are not hard",
    "never ship a half-done feature or mediocre value to keep a change small",
    "Ponytail decides how the code is built (reuse existing components, helpers and "
    "well-known design patterns before writing from scratch, with no speculative "
    "abstraction), not how much of the feature ships.",
    "MVP mode only shifts the weight toward simplicity and never allows a half-done feature.",
    "When jev is present it classifies the options against these criteria",
    "without jev the rule still applies, decided by the agent's own reasoning",
    "Where ponytail's smallest-change wording meets this rule, ponytail yields.",
)
_RUNBOOK_PATH = os.path.join(_REPO, "docs", "run-book", "graphify.md")
_RUNBOOK_HEADINGS = ["## Build", "## Refresh", "## Check freshness", "## Query"]
_RUNBOOK_PHRASES = (
    "measured on 2026-11-03",
    "gsd-core 1.20.0",
    "24 h",
    "commits behind",
    "unknown update option",
    ".rebuild.lock",
    "ai-kit-index.lock",
    "without GSD",
    "same graph",
    "update-ref",
    "graphify.enabled",
    "graphify.graph_path",
    "default location",
)


def _design_bullet(text):
    padded = "\n" + text
    start = padded.find("\n" + _DESIGN_MARKER)
    if start < 0:
        return ""
    ends = [e for e in (padded.find("\n- ", start + 1), padded.find("\n## ", start + 1)) if e >= 0]
    return _flat(padded[start : min(ends) if ends else len(padded)])


def _above_generated_block(text):
    """True when the design bullet sits above the first generated-block marker."""
    bullet = text.find(_DESIGN_MARKER)
    marker = text.find("<!-- BEGIN")
    if marker < 0:
        return bullet >= 0
    return 0 <= bullet < marker


def _headings(text):
    return [line for line in text.splitlines() if line.startswith("## ")]


class TestDesignRule(unittest.TestCase):
    def setUp(self):
        self.bullet = _design_bullet(_read(_AGENTS_PATH))

    def test_every_design_clause_is_in_the_bullet(self):
        self.assertTrue(self.bullet, "Design rule bullet missing from AGENTS.md")
        self.assertEqual(_missing_clauses(self.bullet, _DESIGN_CLAUSES), [])

    def test_removing_one_design_clause_reports_exactly_that_clause(self):
        # non-vacuity: a removed clause must be the one reported
        for clause in _DESIGN_CLAUSES:
            with self.subTest(clause=clause[:40]):
                damaged = self.bullet.replace(_flat(clause), "", 1)
                self.assertEqual(_missing_clauses(damaged, _DESIGN_CLAUSES), [clause])

    def test_design_bullet_sits_above_the_generated_block(self):
        # bullet first, then marker: passes; marker first, then bullet: fails
        ok = "## Non-Negotiable Rules\n\n" + _DESIGN_MARKER + " x\n<!-- BEGIN gen -->\n"
        bad = "## Non-Negotiable Rules\n\n<!-- BEGIN gen -->\n" + _DESIGN_MARKER + " x\n"
        self.assertTrue(_above_generated_block(ok))
        self.assertFalse(_above_generated_block(bad))
        self.assertTrue(_above_generated_block(_read(_AGENTS_PATH)))


_JUDGE_MARKER = "- Any new or materially updated `SKILL.md` passes the `skill-judge` review"
_JUDGE_CLAUSES = (
    "A judge loop stops after three rounds per skill: its result is recorded as it stands, "
    "and an unmet bar goes to the owner.",
    "A disputed finding counts as refuted only through a recorded run (the finding id, "
    "`path:line`, the command and its observed output), never through another judge round.",
    "SKILL.md describes behaviour; provenance and version history live in a trailing section "
    "or a reference, and version-specific text appears only as a conditional.",
)


def _judge_bullet(text):
    padded = "\n" + text
    start = padded.find("\n" + _JUDGE_MARKER)
    if start < 0:
        return ""
    ends = [e for e in (padded.find("\n- ", start + 1), padded.find("\n## ", start + 1)) if e >= 0]
    return _flat(padded[start : min(ends) if ends else len(padded)])


class TestSkillJudgeRule(unittest.TestCase):
    def setUp(self):
        self.bullet = _judge_bullet(_read(_AGENTS_PATH))

    def test_every_judge_clause_is_in_the_bullet(self):
        self.assertTrue(self.bullet, "skill-judge bullet missing from AGENTS.md")
        self.assertEqual(_missing_clauses(self.bullet, _JUDGE_CLAUSES), [])

    def test_removing_one_judge_clause_reports_exactly_that_clause(self):
        # non-vacuity: a removed clause must be the one reported
        for clause in _JUDGE_CLAUSES:
            with self.subTest(clause=clause[:40]):
                damaged = self.bullet.replace(_flat(clause), "", 1)
                self.assertNotEqual(damaged, self.bullet)
                self.assertEqual(_missing_clauses(damaged, _JUDGE_CLAUSES), [clause])

    def test_missing_marker_reports_all_clauses(self):
        bullet = _judge_bullet("# title\n\nno judge bullet here\n")
        self.assertEqual(bullet, "")
        self.assertEqual(len(_missing_clauses(bullet, _JUDGE_CLAUSES)), len(_JUDGE_CLAUSES))


class TestRunbook(unittest.TestCase):
    def setUp(self):
        self.text = _read(_RUNBOOK_PATH)

    def test_four_sections_in_order(self):
        self.assertEqual(_headings(self.text), _RUNBOOK_HEADINGS)

    def test_swapped_sections_fail(self):
        # non-vacuity: a reordered runbook must not match the pinned order
        swapped = (
            self.text.replace("## Build\n", "## TMP\n", 1)
            .replace("## Refresh\n", "## Build\n", 1)
            .replace("## TMP\n", "## Refresh\n", 1)
        )
        self.assertNotEqual(_headings(swapped), _RUNBOOK_HEADINGS)

    def test_agents_links_to_the_runbook_and_it_exists(self):
        self.assertIn("](docs/run-book/graphify.md)", _read(_AGENTS_PATH))
        self.assertTrue(os.path.isfile(_RUNBOOK_PATH))

    def test_runbook_holds_each_pinned_phrase(self):
        flat = _flat(self.text)
        self.assertEqual([p for p in _RUNBOOK_PHRASES if p not in flat], [])

    def test_removing_a_pinned_phrase_is_reported(self):
        # non-vacuity: each phrase's removal is caught
        flat = _flat(self.text)
        for phrase in _RUNBOOK_PHRASES:
            with self.subTest(phrase=phrase):
                damaged = flat.replace(phrase, "")
                self.assertEqual([p for p in _RUNBOOK_PHRASES if p not in damaged], [phrase])


class TestCommands(unittest.TestCase):
    def test_commands_list_setup_dev_setup_env_and_dev(self):
        section = _section(_read(_AGENTS_PATH), "## Commands")
        lines = [line for line in section.splitlines() if line.startswith("- ")]
        for prefix in ("- `make setup-dev`", "- `make setup-env`", "- `make dev`"):
            with self.subTest(prefix=prefix):
                self.assertTrue(any(line.startswith(prefix) for line in lines))


if __name__ == "__main__":
    unittest.main()
