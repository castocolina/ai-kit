"""The code-review core: normalization, pass rule, cap, changed paths and the prompt."""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_spec import cli, code_review, review_reports


def report(*sections, status="Issues Found — fix and re-invoke"):
    """An ai-kit-shaped report with one bullet per (severity, title) section."""
    return ("## Review: code\n" + "".join(
        f"### {sev}\n- **{title}** — Location: src/app.py:3. Required: fix it. Why: it breaks.\n"
        for sev, title in sections) + f"### Status: {status}\n")


def fit_rows(*specs):
    """Fit rows for the verdict tests: one (title, severity, new_severity, fit) per row."""
    return [{"title": t, "severity": s, "location": "src/app.py:3", "new_severity": n,
             "fit": fit, "decided_by": "jev", "confidence": 0.9, "note": ""}
            for t, s, n, fit in specs]


APPROVED = "## Review: code\n### Status: Approved\n"
SUPERPOWERS = (
    "### Issues\n\n#### Critical (Must Fix)\n1. **Null deref in parser**\n"
    "   - File: src/a.py:10\n\n#### Important (Should Fix)\n"
    "- **Missing test for retry**\n\n#### Minor (Nice to Have)\n"
    "1. Rename the helper for clarity\n\n### Assessment\nReady to merge: No\n"
)
SUPERPOWERS_EXAMPLE = (
    "### Strengths\n- Clean database schema with proper migrations (db.ts:15-42)\n\n"
    "### Issues\n\n#### Important\n1. **Missing help text in CLI wrapper**\n"
    "   - File: index-conversations:1-31\n"
    "   - Issue: No --help flag, users won't discover --concurrency\n"
    "   - Fix: Add --help case with usage examples\n\n"
    "2. **Date validation missing**\n   - File: search.ts:25-27\n"
    "   - Issue: Invalid dates silently return no results\n"
    "   - Fix: Validate ISO format, throw error with example\n\n"
    "#### Minor\n1. **Progress indicators**\n   - File: indexer.ts:130\n"
    "   - Issue: No \"X of Y\" counter for long operations\n"
    "   - Impact: Users don't know how long to wait\n\n"
    "### Recommendations\n- Add progress reporting for user experience\n\n"
    "### Assessment\n\n**Ready to merge: With fixes**\n\n"
    "**Reasoning:** Core implementation is solid with good architecture and tests.\n"
)


def run_cli(argv):
    """main(argv) with captured streams: (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def write(tmp, name, data):
    """A file under tmp holding data (str as UTF-8, bytes as-is); returns its path."""
    path = os.path.join(tmp, name)
    if isinstance(data, bytes):
        with open(path, "wb") as handle:
            handle.write(data)
    else:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(data)
    return path


_IDENT = ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid"]

TABLE_BOTH = {"claude": {"skills": [
    {"name": "ponytail-review", "role": "review_lens", "path": "/example/ponytail-review"},
    {"name": "impeccable", "role": "ui_lens", "path": "/example/impeccable"},
]}}


def _git(repo, *args):
    proc = subprocess.run(["git", "-C", str(repo), *_IDENT, *args], capture_output=True,
                          text=True, check=True)
    return proc.stdout.strip()


class TestReviewVerdict(unittest.TestCase):
    def test_high_fixed_in_round_one_passes_in_round_two(self):
        findings = [{"severity": "HIGH", "title": "Open bug", "location": "src/app.py:3",
                     "required": "fix it", "why": "it breaks"}]
        self.assertEqual(code_review.review_verdict(findings, 1).state, "fix")
        self.assertEqual(code_review.review_verdict([], 2).state, "pass")

    def test_never_clearing_stops_at_round_three(self):
        states = []
        for round_no in (1, 2, 3):
            findings = [{"severity": "HIGH", "title": f"Open bug {round_no}",
                         "location": "src/app.py:3", "required": "fix it", "why": "it breaks"}]
            verdict = code_review.review_verdict(findings, round_no)
            states.append(verdict.state)
            if round_no == 3:
                self.assertEqual(verdict.blocking[0]["title"], "Open bug 3")
        self.assertEqual(states, ["fix", "fix", "cap_stop"])

    def test_clears_exactly_in_round_three(self):
        findings = [{"severity": "HIGH", "title": "Open bug", "location": "src/app.py:3",
                     "required": "fix it", "why": "it breaks"}]
        self.assertEqual(code_review.review_verdict(findings, 1).state, "fix")
        self.assertEqual(code_review.review_verdict(findings, 2).state, "fix")
        self.assertEqual(code_review.review_verdict([], 3).state, "pass")

    def test_medium_and_low_never_block(self):
        findings = [
            {"severity": "MEDIUM", "title": "Naming", "location": "src/app.py:3",
             "required": "fix it", "why": "it breaks"},
            {"severity": "LOW", "title": "Docs", "location": "src/app.py:4",
             "required": "fix it", "why": "it breaks"},
        ]
        verdict = code_review.review_verdict(findings, 1)
        self.assertEqual(verdict.state, "pass")
        self.assertEqual(len(verdict.listed), 2)
        self.assertEqual(verdict.blocking, [])

    def test_critical_blocks(self):
        findings = [{"severity": "CRITICAL", "title": "Crash", "location": "src/app.py:3",
                     "required": "fix it", "why": "it breaks"}]
        self.assertEqual(code_review.review_verdict(findings, 1).state, "fix")

    def test_empty_report_passes_round_one(self):
        self.assertEqual(code_review.review_verdict([], 1).state, "pass")


class TestNormalize(unittest.TestCase):
    def test_approved_report_normalizes_to_an_empty_approved_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", APPROVED)
            out = os.path.join(tmp, "out.md")
            code, stdout, stderr = run_cli(
                ["code-review-normalize", "--report", raw, "--out", out])
            self.assertEqual(code, 0, stderr)
            with open(out, encoding="utf-8") as handle:
                rendered = handle.read()
            self.assertEqual(review_reports.report_status(rendered), "approved")
            self.assertEqual(review_reports.parse_findings(rendered), [])
            self.assertEqual(json.loads(stdout)["findings"], 0)

    def test_medium_only_report_keeps_one_medium_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", report(("MEDIUM", "Naming")))
            out = os.path.join(tmp, "out.md")
            code, _stdout, stderr = run_cli(
                ["code-review-normalize", "--report", raw, "--out", out])
            self.assertEqual(code, 0, stderr)
            with open(out, encoding="utf-8") as handle:
                findings = review_reports.parse_findings(handle.read())
            self.assertEqual([f["severity"] for f in findings], ["MEDIUM"])

    def test_superpowers_report_normalizes_with_titles_and_locations(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "raw.md", SUPERPOWERS)
            out = os.path.join(tmp, "out.md")
            code, _stdout, stderr = run_cli(
                ["code-review-normalize", "--report", raw, "--out", out])
            self.assertEqual(code, 0, stderr)
            with open(out, encoding="utf-8") as handle:
                findings = review_reports.parse_findings(handle.read())
            self.assertEqual([f["severity"] for f in findings], ["CRITICAL", "HIGH", "LOW"])
            self.assertEqual([f["title"] for f in findings],
                             ["Null deref in parser", "Missing test for retry",
                              "Rename the helper for clarity"])
            self.assertEqual([f["location"] for f in findings],
                             ["src/a.py:10", "unstated (raw-2)", "unstated (raw-3)"])
            self.assertEqual(findings[0]["required"], "Null deref in parser")

    def test_two_lane_reports_merge_without_colliding_unlocated_findings(self):
        text = ("#### Important (Should Fix)\n- **Missing test for retry**\n\n"
                "### Assessment\nReady to merge: No\n")
        with tempfile.TemporaryDirectory() as tmp:
            out0 = os.path.join(tmp, "out0.md")
            out1 = os.path.join(tmp, "out1.md")
            for name, target in (("lane0.md", out0), ("lane1.md", out1)):
                raw = write(tmp, name, text)
                code, _stdout, stderr = run_cli(
                    ["code-review-normalize", "--report", raw, "--out", target])
                self.assertEqual(code, 0, stderr)
            with open(out0, encoding="utf-8") as handle:
                report0 = handle.read()
            with open(out1, encoding="utf-8") as handle:
                report1 = handle.read()
            merged = review_reports.merge_findings(
                [("fake/lane-a", report0), ("fake/lane-b", report1)])
            self.assertEqual(len(merged), 2)

    def test_explicit_none_markers_are_zero_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md",
                        "## Review: code\n### HIGH\nNone.\n### Status: Approved\n")
            out = os.path.join(tmp, "out.md")
            code, _stdout, stderr = run_cli(
                ["code-review-normalize", "--report", raw, "--out", out])
            self.assertEqual(code, 0, stderr)
            with open(out, encoding="utf-8") as handle:
                self.assertEqual(review_reports.parse_findings(handle.read()), [])
            sp = write(tmp, "sp.md",
                       "#### Important (Should Fix)\n- None\n\n"
                       "### Assessment\nReady to merge: No\n")
            out_sp = os.path.join(tmp, "out-sp.md")
            code, _stdout, stderr = run_cli(
                ["code-review-normalize", "--report", sp, "--out", out_sp])
            self.assertEqual(code, 0, stderr)
            with open(out_sp, encoding="utf-8") as handle:
                self.assertEqual(review_reports.parse_findings(handle.read()), [])

    def test_second_high_section_is_checked_like_the_first(self):
        wrapped = ("## Review: code\n### HIGH\n\n### HIGH\n- **Wrapped\n"
                   "  title** — Location: a.py:1. Required: x. Why: y.\n"
                   "### Status: Approved\n")
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", wrapped)
            code, _stdout, stderr = run_cli(
                ["code-review-normalize", "--report", raw, "--out",
                 os.path.join(tmp, "out.md")])
            self.assertEqual(code, 4)
            self.assertIn("### HIGH", stderr)

    def test_assessment_without_a_severity_heading_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", "### Assessment\nReady to merge: Yes\n")
            code, _stdout, stderr = run_cli(
                ["code-review-normalize", "--report", raw, "--out",
                 os.path.join(tmp, "out.md")])
            self.assertEqual(code, 4, stderr)

    def test_status_line_plus_superpowers_headings_is_incomplete(self):
        mixed = ("## Review: code\n#### Important (Should Fix)\n- **X**\n"
                "### Status: Approved\n")
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", mixed)
            code, _stdout, stderr = run_cli(
                ["code-review-normalize", "--report", raw, "--out",
                 os.path.join(tmp, "out.md")])
            self.assertEqual(code, 4)
            self.assertIn("superpowers severity headings", stderr)

    def test_unparseable_high_bullet_is_incomplete_and_names_the_heading(self):
        unparseable = ("## Review: code\n### HIGH\n- **Wrapped\n"
                       "  title** — Location: a.py:1. Required: x. Why: y.\n"
                       "### Status: Approved\n")
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", unparseable)
            code, _stdout, stderr = run_cli(
                ["code-review-normalize", "--report", raw, "--out",
                 os.path.join(tmp, "out.md")])
            self.assertEqual(code, 4)
            self.assertTrue(
                stderr.startswith("ai-kit-spec: code review report incomplete:"), stderr)
            self.assertIn("### HIGH", stderr)

    def test_no_status_and_no_assessment_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md",
                       "Some prose without any status or assessment line.\n")
            code, _stdout, stderr = run_cli(
                ["code-review-normalize", "--report", raw, "--out",
                 os.path.join(tmp, "out.md")])
            self.assertEqual(code, 4, stderr)

    def test_failure_status_is_incomplete(self):
        failure = ("## Review: code\n"
                   "### Status: Failure — not reviewed: fake/lane-a (real_error)\n")
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", failure)
            code, _stdout, stderr = run_cli(
                ["code-review-normalize", "--report", raw, "--out",
                 os.path.join(tmp, "out.md")])
            self.assertEqual(code, 4)
            self.assertIn("the report status is Failure", stderr)

    def test_invalid_utf8_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", b"### Status: Approved\n\xff\xfe")
            code, _stdout, stderr = run_cli(
                ["code-review-normalize", "--report", raw, "--out",
                 os.path.join(tmp, "out.md")])
            self.assertEqual(code, 4)
            self.assertIn("UTF-8", stderr)

    def test_missing_report_file_is_unreadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _stdout, stderr = run_cli(
                ["code-review-normalize", "--report", os.path.join(tmp, "nope.md"),
                 "--out", os.path.join(tmp, "out.md")])
            self.assertEqual(code, 2)
            self.assertIn("code-review-normalize:", stderr)

    def test_bullet_with_trailing_labels_sentence_still_parses(self):
        text = ("## Review: code\n### HIGH\n- **Bug** — Location: src/app.py:3. "
                "Required: fix it. Why: it breaks. Labels: kind=bug; tier=a.\n"
                "### Status: Issues Found — fix and re-invoke\n")
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", text)
            out = os.path.join(tmp, "out.md")
            code, stdout, stderr = run_cli(
                ["code-review-normalize", "--report", raw, "--out", out])
            self.assertEqual(code, 0, stderr)
            self.assertEqual(json.loads(stdout)["findings"], 1)
            with open(out, encoding="utf-8") as handle:
                self.assertEqual(len(review_reports.parse_findings(handle.read())), 1)


class TestSuperpowersShape(unittest.TestCase):
    def test_sub_bullets_become_why_and_required(self):
        findings = code_review.normalize_report(SUPERPOWERS_EXAMPLE)
        self.assertEqual([f["severity"] for f in findings], ["HIGH", "HIGH", "LOW"])
        self.assertEqual(findings[0]["location"], "index-conversations:1-31")
        self.assertEqual(findings[0]["why"], "No --help flag, users won't discover --concurrency")
        self.assertEqual(findings[0]["required"], "Add --help case with usage examples")
        self.assertEqual(findings[1]["required"], "Validate ISO format, throw error with example")
        self.assertEqual(findings[2]["why"], "No \"X of Y\" counter for long operations; "
                                             "Users don't know how long to wait")
        self.assertEqual(findings[2]["required"], "Progress indicators")

    def test_the_normalized_report_carries_the_fix_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "raw.md", SUPERPOWERS_EXAMPLE)
            out = os.path.join(tmp, "out.md")
            code, stdout, stderr = run_cli(
                ["code-review-normalize", "--report", raw, "--out", out])
            self.assertEqual(code, 0, stderr)
            self.assertEqual(json.loads(stdout)["findings"], 3)
            with open(out, encoding="utf-8") as handle:
                parsed = review_reports.parse_findings(handle.read())
            self.assertEqual(parsed[1]["required"], "Validate ISO format, throw error with example")
            self.assertEqual(parsed[1]["why"], "Invalid dates silently return no results")

    def test_short_no_issue_lines_read_as_empty(self):
        for marker in ("None", "None.", "none", "- None", "None found.", "No critical issues.",
                       "No issues found.", "_None_", "**None**", "* None found"):
            text = (f"#### Critical (Must Fix)\n{marker}\n\n#### Important (Should Fix)\n"
                    "1. **Retry loop never stops**\n   - File: a.py:1\n\n"
                    "### Assessment\nReady to merge: No\n")
            with self.subTest(marker=marker):
                findings = code_review.normalize_report(text)
                self.assertEqual([(f["severity"], f["title"]) for f in findings],
                                 [("HIGH", "Retry loop never stops")])

    def test_prose_that_is_not_the_closed_set_stays_incomplete(self):
        for line in ("Nothing serious, but see below",
                     "No critical issues, but the parser crashes"):
            text = (f"#### Critical (Must Fix)\n{line}\n\n### Assessment\nReady to merge: No\n")
            with self.subTest(line=line), self.assertRaises(code_review.IncompleteReport):
                code_review.normalize_report(text)


HIGH_BULLET = (
    "- **SQL built from user input** — Location: app/db.py:12. "
    "Required: bind the value. Why: injection.\n")
ISSUES = "### Status: Issues Found — fix and re-invoke\n"


class TestFailClosed(unittest.TestCase):
    """Every uncertain report shape ends not-pass: a fix verdict or an incomplete report."""

    def verdict(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", text)
            return run_cli(["code-review-verdict", "--report", raw, "--round", "1"])

    def test_loose_severity_headings_read_as_the_same_severity(self):
        for heading in ("### High", "### HIGH (1)", "## HIGH", "### high:", "## Critical (2)"):
            with self.subTest(heading=heading):
                code, stdout, stderr = self.verdict(
                    f"## Review: code\n{heading}\n{HIGH_BULLET}{ISSUES}")
                self.assertEqual(code, 1, stderr)
                self.assertIn(json.loads(stdout)["blocking"][0]["severity"],
                              ("HIGH", "CRITICAL"))

    def test_a_loose_medium_heading_still_reads_medium(self):
        code, stdout, stderr = self.verdict(f"## Review: code\n### Medium\n{HIGH_BULLET}{ISSUES}")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["listed"][0]["severity"], "MEDIUM")

    def test_a_finding_under_no_severity_heading_is_incomplete(self):
        for text in (HIGH_BULLET + ISSUES,
                     f"## Review: code\n{HIGH_BULLET}{ISSUES}",
                     f"## Review: code\n### MEDIUM\n### Blockers\n{HIGH_BULLET}{ISSUES}",
                     f"## Review: code\n### High-level notes\n{HIGH_BULLET}{ISSUES}"):
            with self.subTest(text=text):
                code, _stdout, stderr = self.verdict(text)
                self.assertEqual(code, 4, stderr)
                self.assertIn("no severity heading", stderr)

    def test_issues_found_with_no_parsed_finding_is_incomplete(self):
        for text in ("## Review: code\n### HIGH\n\n" + ISSUES,
                     "## Review: code\n### Findings\n"
                     "The query in app/db.py:12 is built from input.\n"
                     + ISSUES):
            with self.subTest(text=text):
                code, _stdout, stderr = self.verdict(text)
                self.assertEqual(code, 4, stderr)
                self.assertIn("Issues Found", stderr)

    def test_a_malformed_second_high_bullet_is_incomplete(self):
        code, _stdout, stderr = self.verdict(
            "## Review: code\n### HIGH\n" + HIGH_BULLET
            + "- **Race in the cache** at src/c.py:4, take the lock first\n" + ISSUES)
        self.assertEqual(code, 4, stderr)
        self.assertIn("### HIGH", stderr)

    def test_a_merged_report_still_normalizes(self):
        findings = [{"severity": "HIGH", "title": "Open bug", "location": "src/app.py:3",
                     "required": "fix it", "why": "it breaks", "reviewers": ["fake/lane-a"]},
                    {"severity": "CROSS-DOC", "title": "Drift", "location": "docs/a.md:1",
                     "required": "align", "why": "drift", "reviewers": ["fake/lane-b"]}]
        merged = review_reports.render_merged_report(
            findings, "docs/plan.md", judged_line="Judged by: fake/lane-a, fake/lane-b")
        self.assertEqual([f["severity"] for f in code_review.normalize_report(merged)],
                         ["HIGH", "CROSS-DOC"])

    def test_a_hash_line_that_is_no_heading_keeps_the_next_item(self):
        text = ("#### Critical (Must Fix)\n1. **First**\n#define LIMIT 3\n##### Note\n"
                "2. **Second**\n\n### Assessment\nReady to merge: No\n")
        self.assertEqual([f["title"] for f in code_review.normalize_report(text)],
                         ["First", "Second"])


class TestReviewVerdictCommand(unittest.TestCase):
    def test_high_finding_round_one_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", report(("HIGH", "Open bug")))
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1"])
            self.assertEqual(code, 1, stderr)

    def test_approved_report_round_two_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", APPROVED)
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "2"])
            self.assertEqual(code, 0, stderr)

    def test_high_finding_round_three_exits_three(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", report(("HIGH", "Open bug")))
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "3"])
            self.assertEqual(code, 3, stderr)

    def test_status_line_never_decides_the_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", report(("HIGH", "Open bug"), status="Approved"))
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1"])
            self.assertEqual(code, 1, stderr)

    def test_medium_only_report_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", report(("MEDIUM", "Naming")))
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1"])
            self.assertEqual(code, 0, stderr)

    def test_printed_json_carries_the_verdict_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", report(("HIGH", "Open bug")))
            code, stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1"])
            self.assertEqual(code, 1, stderr)
            payload = json.loads(stdout)
            self.assertEqual(sorted(payload),
                             ["blocking", "cap", "listed", "round_no", "state"])
            self.assertEqual(payload["state"], "fix")
            self.assertEqual(payload["round_no"], 1)
            self.assertEqual(payload["cap"], 3)
            self.assertEqual(payload["blocking"][0]["title"], "Open bug")
            self.assertEqual(payload["listed"], [])

    def test_empty_file_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", "")
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1"])
            self.assertEqual(code, 4, stderr)

    def test_unparseable_high_section_is_incomplete(self):
        unparseable = ("## Review: code\n### HIGH\n- **Wrapped\n"
                       "  title** — Location: a.py:1. Required: x. Why: y.\n"
                       "### Status: Issues Found — fix and re-invoke\n")
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", unparseable)
            code, _stdout, _stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1"])
            self.assertEqual(code, 4)

    def test_failure_report_is_incomplete(self):
        failure = ("## Review: code\n"
                   "### Status: Failure — not reviewed: fake/lane-a (real_error)\n")
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", failure)
            code, _stdout, _stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1"])
            self.assertEqual(code, 4)

    def test_missing_file_is_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", os.path.join(tmp, "nope.md"),
                 "--round", "1"])
            self.assertEqual(code, 2)
            self.assertIn("code-review-verdict:", stderr)

    def test_round_zero_is_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", APPROVED)
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "0"])
            self.assertEqual(code, 2)
            self.assertIn("--round and --cap must be 1 or more", stderr)

    def test_merged_report_over_one_high_finding_exits_one(self):
        findings = [{"severity": "HIGH", "title": "Open bug", "location": "src/app.py:3",
                     "required": "fix it", "why": "it breaks", "reviewers": ["fake/lane-a"]}]
        merged = review_reports.render_merged_report(
            findings, "docs/plan.md", judged_line="Judged by: fake/lane-a")
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "merged.md", merged)
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1"])
            self.assertEqual(code, 1, stderr)


class TestFindingLabels(unittest.TestCase):
    def test_all_five_valid_labels(self):
        finding = {"why": "it breaks. Labels: kind=security; tier=unit; repro=yes; "
                         "reach=user; stage=mvp"}
        self.assertEqual(code_review.finding_labels(finding),
                         {"kind": "security", "tier": "unit", "repro": "yes",
                          "reach": "user", "stage": "mvp"})

    def test_one_invalid_value_reads_unknown(self):
        finding = {"why": "it breaks. Labels: kind=bogus; tier=unit; repro=yes; "
                         "reach=user; stage=mvp"}
        self.assertEqual(code_review.finding_labels(finding),
                         {"kind": "unknown", "tier": "unit", "repro": "yes",
                          "reach": "user", "stage": "mvp"})

    def test_no_labels_tail_reads_unknown(self):
        expected = {key: "unknown" for key in code_review.LABEL_VALUES}
        self.assertEqual(code_review.finding_labels({"why": "it breaks."}), expected)
        self.assertEqual(code_review.finding_labels({}), expected)

    def test_labels_tolerate_spaces_periods_and_trailing_text(self):
        finding = {"why": "it breaks. Labels: kind = logic; tier=unit.; repro=yes; "
                         "reach=user; stage=mvp.. See a.py."}
        self.assertEqual(code_review.finding_labels(finding),
                         {"kind": "logic", "tier": "unit", "repro": "yes",
                          "reach": "user", "stage": "mvp"})

    def test_the_prompt_names_the_label_choices(self):
        self.assertIn("Labels: kind=<logic|security|performance|style|docs|other>",
                      code_review.CODE_REVIEW_PROMPT)


class TestFitJson(unittest.TestCase):
    def test_fit_severity_rule(self):
        table = (
            ("LOW", "higher", "MEDIUM", ""),
            ("MEDIUM", "higher", "HIGH", ""),
            ("HIGH", "higher", "CRITICAL", ""),
            ("CRITICAL", "higher", "CRITICAL", ""),
            ("MEDIUM", "lower", "LOW", ""),
            ("LOW", "lower", "LOW", ""),
            ("HIGH", "lower", "HIGH", "never lowered"),
            ("CRITICAL", "lower", "CRITICAL", "never lowered"),
            ("LOW", "fits", "LOW", ""),
            ("MEDIUM", None, "MEDIUM", ""),
            (None, "higher", None, ""),
            ("CROSS-DOC", "lower", "CROSS-DOC", ""),
        )
        for severity, fit, new, note in table:
            with self.subTest(severity=severity, fit=fit):
                self.assertEqual(code_review.fit_severity(severity, fit), (new, note))

    def test_check_fit(self):
        findings = [{"severity": "HIGH", "title": "Open bug", "location": "src/app.py:3"}]
        code_review.check_fit(findings, fit_rows(("Open bug", "HIGH", "HIGH", "fits")))
        # two rows covering one merged finding: same severity and location, other titles
        code_review.check_fit(findings, fit_rows(
            ("Open bug", "HIGH", "HIGH", "fits"),
            ("Second lane wording", "HIGH", "HIGH", "fits")))
        with self.subTest(case="a row breaking the rule"):
            with self.assertRaises(ValueError) as raised:
                code_review.check_fit(
                    findings, fit_rows(("Open bug", "HIGH", "LOW", "lower")))
            self.assertIn("does not follow the fit rule", str(raised.exception))
        with self.subTest(case="a blocking result the report lacks"):
            with self.assertRaises(ValueError) as raised:
                code_review.check_fit(
                    findings, fit_rows(("Other lane bug", "HIGH", "CRITICAL", "higher")))
            self.assertIn("missing from the report", str(raised.exception))
        with self.subTest(case="a non-dict row"), self.assertRaises(ValueError):
            code_review.check_fit(findings, ["nope"])
        with self.subTest(case="a non-blocking result is not checked against the report"):
            code_review.check_fit([], fit_rows(("Naming", "MEDIUM", "MEDIUM", "fits")))

    def _fit_file(self, tmp, rows):
        return write(tmp, "fit.json", json.dumps(rows))

    def test_high_report_with_the_medium_higher_high_row_exits_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", report(("HIGH", "Open bug")))
            fit = self._fit_file(tmp, fit_rows(("Open bug", "MEDIUM", "HIGH", "higher")))
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1", "--fit-json", fit])
            self.assertEqual(code, 1, stderr)

    def test_low_report_with_the_medium_lower_low_row_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", report(("LOW", "Naming")))
            fit = self._fit_file(tmp, fit_rows(("Naming", "MEDIUM", "LOW", "lower")))
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1", "--fit-json", fit])
            self.assertEqual(code, 0, stderr)

    def test_a_row_breaking_the_fit_rule_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", report(("HIGH", "Open bug")))
            fit = self._fit_file(tmp, fit_rows(("Open bug", "HIGH", "LOW", "lower")))
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1", "--fit-json", fit])
            self.assertEqual(code, 2)
            self.assertIn("does not follow the fit rule", stderr)

    def test_a_high_row_missing_from_the_report_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", report(("MEDIUM", "Naming")))
            fit = self._fit_file(tmp, fit_rows(("Open bug", "HIGH", "HIGH", "fits")))
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1", "--fit-json", fit])
            self.assertEqual(code, 2)
            self.assertIn("missing from the report", stderr)

    def test_two_rows_covering_one_merged_finding_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", report(("HIGH", "Open bug")))
            fit = self._fit_file(tmp, fit_rows(
                ("Open bug", "HIGH", "HIGH", "fits"),
                ("Second lane wording", "HIGH", "HIGH", "fits")))
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1", "--fit-json", fit])
            self.assertEqual(code, 1, stderr)

    def test_a_non_list_fit_file_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", report(("HIGH", "Open bug")))
            fit = write(tmp, "fit.json", json.dumps({"rows": []}))
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1", "--fit-json", fit])
            self.assertEqual(code, 2)
            self.assertIn("the fit file is not a list", stderr)

    def test_a_missing_fit_file_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", report(("HIGH", "Open bug")))
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1",
                 "--fit-json", os.path.join(tmp, "nope.json")])
            self.assertEqual(code, 2)
            self.assertIn("code-review-verdict:", stderr)

    def test_an_incomplete_report_still_exits_four_with_fit_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", "")
            fit = self._fit_file(tmp, fit_rows(("Open bug", "HIGH", "HIGH", "fits")))
            code, _stdout, _stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1", "--fit-json", fit])
            self.assertEqual(code, 4)

    def test_without_fit_json_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = write(tmp, "lane.md", report(("HIGH", "Open bug")))
            code, _stdout, stderr = run_cli(
                ["code-review-verdict", "--report", raw, "--round", "1"])
            self.assertEqual(code, 1, stderr)


class TestReviewPrompt(unittest.TestCase):
    def test_prompt_names_the_range_plan_and_report_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "prompt.md")
            code, stdout, stderr = run_cli(
                ["code-review-prompt", "--base", "b1", "--head", "h2",
                 "--plan", "docs/plan.md", "--description", "add retry", "--out", out])
            self.assertEqual(code, 0, stderr)
            self.assertEqual(json.loads(stdout), {"prompt": out})
            with open(out, encoding="utf-8") as handle:
                prompt = handle.read()
            self.assertIn("git diff b1..h2", prompt)
            self.assertIn("### Status: Approved", prompt)
            bullet = ("- **<title>** — Location: <path:line>. Required: <fix>. Why: <reason>. "
                      "Labels: kind=<logic|security|performance|style|docs|other>; "
                      "tier=<unit|integration|e2e|none>; repro=<yes|no>; "
                      "reach=<user|internal>; stage=<mvp|production>.")
            self.assertIn(bullet, prompt)
            self.assertIn("docs/plan.md", prompt)

    def test_description_keeps_paths_and_redacts_secrets_on_one_line(self):
        token = "ghp_" + "Zqxlmnop" * 2 + "Zqxl"
        description = ("fix `retry` in src/a.py:3\nnear \x1b" + token + " and then "
                       + "more words " * 10)
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "prompt.md")
            code, _stdout, stderr = run_cli(
                ["code-review-prompt", "--base", "b1", "--head", "h2",
                 "--plan", "docs/plan.md", "--description", description, "--out", out])
            self.assertEqual(code, 0, stderr)
            with open(out, encoding="utf-8") as handle:
                prompt = handle.read()
        line = next(row for row in prompt.splitlines() if row.startswith("Change: "))
        self.assertTrue(line.startswith("Change: fix `retry` in src/a.py:3 near [redacted] and "
                                        "then more words"), line)
        self.assertTrue(line.endswith("more words"), line)
        self.assertGreater(len(line), 120)
        self.assertNotIn(token, prompt)
        self.assertNotIn("\x1b", prompt)
        self.assertNotIn("[omitted]", line)

    def test_the_round_inputs_text_matches(self):
        path = os.path.join(os.path.dirname(__file__), "..", "skills",
                            "ai-kit-spec-execute-superpowers", "references", "code-review.md")
        with open(path, encoding="utf-8") as handle:
            flat = " ".join(handle.read().split())
        self.assertIn("`code-review-prompt` puts it on one line, drops control characters and "
                      "redacts secret shapes", flat)
        self.assertNotIn("keeps its first 80 characters", flat)


class TestReviewPaths(unittest.TestCase):
    """A real temporary git repository: the changed paths come back byte for byte."""

    def setUp(self):
        self.root = tempfile.TemporaryDirectory(prefix="ai-kit-cr-")
        self.addCleanup(self.root.cleanup)
        self.repo = os.path.join(self.root.name, "repo")
        os.mkdir(self.repo)
        _git(self.repo, "init", "-q", "-b", "main")
        for name, text in (("keep.py", "keep = 1\n"), ("gone.py", "gone = 1\n"),
                           ("old.py", "old = 1\n")):
            write(self.repo, name, text)
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "base")
        self.base = _git(self.repo, "rev-parse", "HEAD")
        write(self.repo, "keep.py", "keep = 2\n")
        os.remove(os.path.join(self.repo, "gone.py"))
        _git(self.repo, "mv", "old.py", "new.py")
        os.mkdir(os.path.join(self.repo, "src"))
        write(self.repo, "src/app.tsx", "export const app = 1\n")
        os.mkdir(os.path.join(self.repo, "SRC"))
        write(self.repo, "SRC/APP.TSX", "export const APP = 1\n")
        os.mkdir(os.path.join(self.repo, "docs"))
        write(self.repo, "docs/café.md", "café\n")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "head")
        self.head = _git(self.repo, "rev-parse", "HEAD")
        self.expected = sorted(["SRC/APP.TSX", "docs/café.md", "keep.py", "new.py",
                                "src/app.tsx"])

    def test_paths_come_back_unchanged_sorted_and_deletions_dropped(self):
        self.assertEqual(code_review.review_paths(self.base, self.head, self.repo),
                         self.expected)

    def test_an_empty_diff_gives_no_paths(self):
        self.assertEqual(code_review.review_paths(self.head, self.head, self.repo), [])

    def test_a_bad_revision_raises_before_git_runs(self):
        for bad in ("", "--output=x"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    code_review.review_paths(bad, self.head, self.repo)
                with self.assertRaises(ValueError):
                    code_review.review_paths(self.base, bad, self.repo)

    def test_the_cli_form_of_a_bad_revision_exits_two(self):
        code, _stdout, stderr = run_cli(
            ["code-review-paths", "--base=--output=x", "--head", self.head,
             "--cwd", self.repo])
        self.assertEqual(code, 2)
        self.assertIn("code-review-paths: bad revision:", stderr)

    def test_cli_prints_the_json_paths_with_no_missing_lens_note(self):
        with mock.patch.object(code_review.skill_table, "scan", return_value=TABLE_BOTH):
            code, stdout, stderr = run_cli(
                ["code-review-paths", "--base", self.base, "--head", self.head,
                 "--cwd", self.repo])
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout), self.expected)
        self.assertEqual(stderr, "")

    def test_cli_names_both_missing_lenses_and_still_exits_zero(self):
        empty_table = {"claude": {"skills": []}}
        with mock.patch.object(code_review.skill_table, "scan", return_value=empty_table):
            code, stdout, stderr = run_cli(
                ["code-review-paths", "--base", self.base, "--head", self.head,
                 "--cwd", self.repo])
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout), self.expected)
        self.assertEqual(stderr.splitlines(), [
            "ai-kit-spec: lens ponytail-review not installed; the review runs without it",
            "ai-kit-spec: lens impeccable not installed; the review runs without it",
        ])

    def test_control_character_path_is_dropped_on_the_cli(self):
        tab_name = os.path.join(self.repo, "tab\tname.py")
        with open(tab_name, "w", encoding="utf-8") as handle:
            handle.write("tabbed = 1\n")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "tab")
        later = _git(self.repo, "rev-parse", "HEAD")
        self.assertEqual(code_review.review_paths(self.head, later, self.repo),
                         ["tab\tname.py"])
        with mock.patch.object(code_review.skill_table, "scan", return_value=TABLE_BOTH):
            code, stdout, stderr = run_cli(
                ["code-review-paths", "--base", self.head, "--head", later,
                 "--cwd", self.repo])
        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout), [])
        self.assertIn("ai-kit-spec: code-review-paths: dropped a path holding a control "
                      "character: 'tab\\tname.py'", stderr)


class TestMissingLenses(unittest.TestCase):
    """Synthetic tables: no real discovery, no node."""

    def test_missing_lenses_follow_the_table_and_the_paths(self):
        ui_table = {"claude": {"skills": [{"name": "impeccable"}]}}
        empty_table = {"claude": {"skills": []}}
        only_review = {"claude": {"skills": [{"name": "ponytail-review"}]}}
        split_hosts = {"claude": {"skills": [{"name": "ponytail-review"}]},
                       "codex": {"skills": [{"name": "impeccable"}]}}
        cases = [
            (ui_table, ["src/app.py"], ["ponytail-review"]),
            (empty_table, ["SRC/APP.TSX"], ["ponytail-review", "impeccable"]),
            (TABLE_BOTH, ["SRC/APP.TSX", "src/app.tsx", "docs/x.md"], []),
            (only_review, ["src/app.py"], []),
            (empty_table, ["src/app.py"], ["ponytail-review"]),
            (split_hosts, ["src/app.tsx"], []),
        ]
        for table, paths, expected in cases:
            with self.subTest(table=table, paths=paths):
                self.assertEqual(code_review.missing_lenses(table, paths), expected)


if __name__ == "__main__":
    unittest.main()
