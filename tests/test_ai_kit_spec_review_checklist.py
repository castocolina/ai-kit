"""Doc-contract tests for the ai-kit-spec-review-checklist SKILL.md (SPEC R2, R3).

ai-kit-spec-review parses the checklist's three Status lines and merges its reports by heading.
These tests pin those spellings against the orchestrator's own SKILL.md, run the templates through
the orchestrator's own parser, compare the fallback marker table with each profile's
detection_signals, and pin the fallback, no-ask and LOW rules. A failing test is fixed in the
prose, never by weakening the test.
"""

import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
from ai_kit_spec.review_reports import parse_findings, report_status

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skills" / "ai-kit-spec-review-checklist"
SKILL_MD = SKILL / "SKILL.md"
PROFILES = SKILL / "references" / "frameworks"
ORCHESTRATOR_MD = REPO / "skills" / "ai-kit-spec-review" / "SKILL.md"
FENCE = re.compile(r"^```")
ORCHESTRATOR_ROWS = (
    "| `### Status: Approved` |",
    "| `### Status: Issues Found — fix and re-invoke` |",
    "| `### Status: Failure — <reason>` |",
)
ISSUES_HEADINGS = [
    "### Document Type",
    "### Files Read",
    "### CRITICAL",
    "### HIGH",
    "### MEDIUM",
    "### LOW",
    "### Cross-Document Consistency",
    "### Status: Issues Found — fix and re-invoke",
]
BULLET = "- **T{n}** — Location: s{n}. Required: r{n}. Why: w{n}."
PLAIN_NOTE = "- Step 3 uses a raw string where the module already has a constant."
TEMPLATE_RULES = (
    "Write each note as a plain `- <text>` bullet, never the finding shape",
    "Every heading line is bare, with nothing after the heading text",
    "`### LOW` holds Plan-checklist tooling-catchable findings and appears only beside a "
    "CRITICAL, HIGH, MEDIUM or Cross-Document Consistency finding.",
    "A review whose only findings are LOW keeps the Approved shape and lists them under "
    "`### Non-blocking notes`.",
    "With more than three, keep the three most useful.",
)
TABLE_ORDER = ("superpowers", "openspec", "spec-kit", "kiro", "bmad", "gsd")
MARKER_ROW = re.compile(r"^\| `([a-z-]+)` \| (.+) \|$")
CODE_SPAN = re.compile(r"`([^`]+)`")
SIGNAL_ITEM = re.compile(r'^\s+- "(.+)"$')
FALLBACK_RULES = (
    "A marker that matches the document's own path beats a repository-level marker",
    "when two profiles still tie, the first row of the table wins",
    "Look for repository-level markers in the codebase root the caller gave you; with none, in "
    "the current working directory.",
    "Name the profile you used on the `### Document Type` line.",
    "With `FRAMEWORK_PROFILE_PATH = none`, or no matching marker, review with the generic "
    "archetype checklists and record `generic` as the framework on the `### Document Type` line.",
    "Never stop to ask a question, in any mode",
    "every run ends with one of the three Status lines",
    "end with `### Status: Failure — archetype not settled: <path>`, never Approved and never "
    "Issues Found",
    "Audit only — never edit the document under review.",
)
ASK_SENTENCE = "ask the user"


def _fenced_blocks(text):
    blocks = []
    current = None
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


def _review_blocks(text):
    """The fenced report templates: the blocks whose first line starts `## Review:`."""
    return [block for block in _fenced_blocks(text) if block and block[0].startswith("## Review:")]


def _section_lines(text, heading):
    """Lines under the heading line starting with `heading`, up to the next `### ` heading.

    Returns None when the heading is absent, so a missing section fails the test.
    """
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.startswith(heading)), None)
    if start is None:
        return None
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("### ")), len(lines)
    )
    return lines[start + 1 : end]


def _flat(text):
    return " ".join(text.split())


def _filled(block):
    """The template with each `- ...` placeholder replaced by a finding bullet, in order."""
    filled = []
    count = 0
    for line in block:
        if line == "- ...":
            count += 1
            filled.append(BULLET.format(n=count))
        else:
            filled.append(line)
    return "\n".join(filled) + "\n"


def _with_note(block, note):
    """The Approved template with one note line inserted before its Status line."""
    return "\n".join([*block[:-1], "### Non-blocking notes", note, block[-1]]) + "\n"


def _detection_signals(path):
    """The profile's frontmatter `detection_signals` list, or [] when it has none."""
    lines = path.read_text(encoding="utf-8").split("\n")
    if not lines or lines[0] != "---":
        return []
    end = next((i for i in range(1, len(lines)) if lines[i] == "---"), len(lines))
    frontmatter = lines[1:end]
    if "detection_signals:" not in frontmatter:
        return []
    signals = []
    for line in frontmatter[frontmatter.index("detection_signals:") + 1 :]:
        match = SIGNAL_ITEM.match(line)
        if match is None:
            break
        signals.append(match.group(1))
    return signals


def _marker_rows(text):
    """(profile id, line index, backticked markers) for each fallback marker-table row."""
    rows = []
    for index, line in enumerate(text.split("\n")):
        match = MARKER_ROW.match(line.strip())
        if match and match.group(1) in TABLE_ORDER:
            rows.append((match.group(1), index, CODE_SPAN.findall(match.group(2))))
    return rows


class TestStatusContract(unittest.TestCase):
    def setUp(self):
        self.text = SKILL_MD.read_text(encoding="utf-8")
        self.orchestrator = ORCHESTRATOR_MD.read_text(encoding="utf-8")

    def test_orchestrator_step_2_parses_the_three_spellings(self):
        heading = "### Step 2 — Parse reviewer Status"
        lines = _section_lines(self.orchestrator, heading)
        if lines is None:
            self.fail(f"section {heading!r} is absent from ai-kit-spec-review")
        for row in ORCHESTRATOR_ROWS:
            with self.subTest(statement=row):
                self.assertTrue(any(line.startswith(row) for line in lines))

    def test_checklist_emits_each_spelling(self):
        blocks = _review_blocks(self.text)
        self.assertEqual(len(blocks), 2, "expected the Approved and the Issues Found templates")
        approved, issues = blocks
        with self.subTest(statement="Approved template ends with its Status line"):
            self.assertEqual(approved[-1], "### Status: Approved")
        with self.subTest(statement="Issues Found template ends with its Status line"):
            self.assertEqual(issues[-1], "### Status: Issues Found — fix and re-invoke")
        with self.subTest(statement="Failure spelling for an input not on disk"):
            self.assertIn("### Status: Failure — input not on disk.", _flat(self.text))


class TestTemplates(unittest.TestCase):
    def setUp(self):
        self.text = SKILL_MD.read_text(encoding="utf-8")
        blocks = _review_blocks(self.text)
        self.assertEqual(len(blocks), 2, "expected the Approved and the Issues Found templates")
        self.approved, self.issues = blocks

    def test_approved_headings_are_unchanged(self):
        self.assertEqual(
            [line for line in self.approved if line.startswith("### ")],
            ["### Document Type", "### Files Read", "### Status: Approved"],
        )

    def test_issues_found_heading_order(self):
        self.assertEqual(
            [line for line in self.issues if line.startswith("### ")],
            ISSUES_HEADINGS,
        )

    def test_issues_found_template_parses_every_tier(self):
        report = _filled(self.issues)
        self.assertEqual(
            [finding["severity"] for finding in parse_findings(report)],
            ["CRITICAL", "HIGH", "MEDIUM", "LOW", "CROSS-DOC"],
        )
        self.assertEqual(report_status(report), "issues")

    def test_plain_note_keeps_an_approved_report_approved(self):
        report = _with_note(self.approved, PLAIN_NOTE)
        self.assertEqual(parse_findings(report), [])
        self.assertEqual(report_status(report), "approved")

    def test_finding_shaped_note_is_parsed_as_an_issue(self):
        report = _with_note(self.approved, BULLET.format(n=9))
        self.assertEqual(len(parse_findings(report)), 1)

    def test_low_and_notes_rules_are_stated(self):
        flat = _flat(self.text)
        for rule in TEMPLATE_RULES:
            with self.subTest(statement=rule):
                self.assertIn(rule, flat)


class TestMarkerTable(unittest.TestCase):
    def setUp(self):
        self.text = SKILL_MD.read_text(encoding="utf-8")

    def test_profiles_are_the_six_rows(self):
        ids = sorted(p.stem for p in PROFILES.glob("*.md") if p.name != "SCHEMA.md")
        self.assertEqual(ids, sorted(TABLE_ORDER))

    def test_rows_equal_detection_signals(self):
        rows = _marker_rows(self.text)
        for profile_id in TABLE_ORDER:
            with self.subTest(profile=profile_id):
                signals = _detection_signals(PROFILES / f"{profile_id}.md")
                self.assertTrue(signals, f"{profile_id} profile lists no detection_signals")
                matches = [markers for row_id, _index, markers in rows if row_id == profile_id]
                self.assertEqual(len(matches), 1, f"expected one marker row for {profile_id}")
                self.assertEqual(matches[0], signals)

    def test_rows_follow_table_order(self):
        self.assertEqual([row_id for row_id, _index, _markers in _marker_rows(self.text)],
                         list(TABLE_ORDER))


class TestFallbackRules(unittest.TestCase):
    def setUp(self):
        self.text = SKILL_MD.read_text(encoding="utf-8")

    def test_fallback_rules_are_stated(self):
        flat = _flat(self.text)
        for rule in FALLBACK_RULES:
            with self.subTest(statement=rule):
                self.assertIn(rule, flat)

    def test_no_question_to_the_user(self):
        self.assertNotIn(ASK_SENTENCE, _flat(self.text))


if __name__ == "__main__":
    unittest.main()
