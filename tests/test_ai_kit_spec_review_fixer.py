"""Doc-contract tests for the ai-kit-spec-review-fixer SKILL.md (SPEC R4; plan 32.1-07).

ai-kit-spec-review parses three Status spellings from the fixer's output. These tests pin those
spellings against the orchestrator's own SKILL.md, and pin the fixer's disagreement rule, its
cross-document rule and the Fix Summary order against the fixer's SKILL.md. A failing test is
fixed in the prose, never by weakening the test.
"""

import itertools
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skills" / "ai-kit-spec-review-fixer"
SKILL_MD = SKILL / "SKILL.md"
ORCHESTRATOR_MD = REPO / "skills" / "ai-kit-spec-review" / "SKILL.md"
PARSED = ("Edits Applied", "Escalation Required", "No Edits")
FENCE = re.compile(r"^```")


def _section(text: str, heading: str) -> list[str]:
    """Lines under `## heading` up to the next level-2 heading."""
    lines = text.split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith(f"## {heading}"))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start + 1 : end]


def _fenced_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in text.split("\n"):
        if FENCE.match(line):
            if current is None:
                current = []
            else:
                blocks.append(current)
                current = None
        elif current is not None:
            current.append(line)
    return blocks


def _fix_summary_blocks(text: str) -> list[list[str]]:
    """The fenced Fix Summary template: the one block whose first line is `## Fix Summary:`."""
    return [block for block in _fenced_blocks(text)
            if block and block[0].startswith("## Fix Summary:")]


class TestStatusContract(unittest.TestCase):
    def setUp(self):
        self.text = SKILL_MD.read_text(encoding="utf-8")
        self.orchestrator = ORCHESTRATOR_MD.read_text(encoding="utf-8")

    def test_parsed_values_keep_their_spelling(self):
        for value in PARSED:
            with self.subTest(value=value):
                self.assertIn(f"### Status: {value}", self.orchestrator)
        blocks = _fix_summary_blocks(self.text)
        self.assertEqual(len(blocks), 1)
        status_lines = [line for line in blocks[0] if line.startswith("### Status:")]
        self.assertEqual(len(status_lines), 1)
        for value in (*PARSED, "Failure"):
            self.assertIn(value, status_lines[0])

    def test_failure_is_emitted_with_no_edits(self):
        self.assertIn("### Status: Failure — document not on disk", self.text)
        self.assertIn("with no edits", self.text)

    def test_mixed_run_reports_escalation_required(self):
        self.assertIn(
            "`Escalation Required` when any finding was escalated, even when others were edited",
            self.text,
        )


class TestRules(unittest.TestCase):
    def setUp(self):
        self.text = SKILL_MD.read_text(encoding="utf-8")

    def test_one_disagreement_rule(self):
        rules = _section(self.text, "Editing rules")
        self.assertTrue(any(
            line.startswith("| If you disagree with a CRITICAL or HIGH finding, address it anyway")
            for line in rules
        ))
        self.assertIn(
            "A MEDIUM or LOW finding is a task if trivial; otherwise defer it under",
            "\n".join(_section(self.text, "Before editing")),
        )

    def test_cross_document_rule_is_an_editing_rule(self):
        self.assertTrue(any(
            line.startswith("| A finding whose `Location:` spans several documents:")
            for line in _section(self.text, "Editing rules")
        ))
        escalation = "\n".join(_section(self.text, "Escalation conditions"))
        self.assertNotIn("more than one document", escalation)
        self.assertIn("names a document you were not given or that is not on disk", escalation)

    def test_fix_summary_section_order(self):
        blocks = _fix_summary_blocks(self.text)
        self.assertEqual(len(blocks), 1)
        block = blocks[0]
        headings = [
            "### Findings addressed",
            "### Findings escalated",
            "### Findings skipped (MEDIUM or LOW only, with disagreement noted)",
            "### Findings not yet addressed",
            "### Status:",
        ]
        indices = [next((i for i, line in enumerate(block) if line.startswith(h)), -1)
                   for h in headings]
        self.assertTrue(all(i >= 0 for i in indices), indices)
        self.assertTrue(all(a < b for a, b in itertools.pairwise(indices)), indices)

    def test_skipped_list_is_medium_or_low_only(self):
        block = _fix_summary_blocks(self.text)[0]
        self.assertTrue(any("Severity: <MEDIUM|LOW>. Reason:" in line for line in block))

    def test_no_contradicting_wording(self):
        for phrase in ("Address it AND note", "Address it OR document",
                       "otherwise they are escalation candidates"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.text)
        self.assertTrue(any(
            line.startswith("| Silently dropping a finding you disagree with | "
                            "Address a CRITICAL or HIGH finding anyway")
            for line in _section(self.text, "Common Mistakes")
        ))

    def test_escalations_go_in_the_fix_summary(self):
        escalation = "\n".join(_section(self.text, "Escalation conditions"))
        self.assertIn("under `### Findings escalated` in the Fix Summary", escalation)


if __name__ == "__main__":
    unittest.main()
