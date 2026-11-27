"""jev_review: advisory classification of reviewer-fixer disagreements and review sizing
(fake jev only)."""

import copy
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import (
    cache,
    cli,
    code_review,
    config_io,
    jev_names,
    jev_review,
    quota,
    review_log,
    review_reports,
    review_signals,
    secret_shapes,
)

REPORT_A = """## Review: docs/x.md
### Document Type
spec
### HIGH
- **Missing rollback** — Location: §3. Required: add a rollback step. \
Why: a failed deploy stays broken.
### MEDIUM
- **Loose wording** — Location: §2. Required: name the limit. Why: readers guess.
### Status: Issues Found — fix and re-invoke
"""

REPORT_B = """## Review: docs/x.md
### Document Type
spec
### MEDIUM
- **Loose wording** — Location: §2. Required: name the limit. Why: readers guess.
### Status: Issues Found — fix and re-invoke
"""

SUMMARY = """## Fix Summary
### Findings addressed
### Findings escalated
### Findings skipped (MEDIUM or LOW only, with disagreement noted)
- **Loose wording** — Severity: MEDIUM. Reason: the limit is named in section one. \
NOT addressed in this pass.
### Status: Edits Applied
"""


def merged(*reports):
    found = review_reports.merge_findings([(f"lane-{i}", r) for i, r in enumerate(reports)])
    return review_reports.render_merged_report(found, "docs/x.md")


def answers_run(table, calls):
    def run(argv, input="", **kwargs):
        calls.append({"payload": json.loads(input), "cwd": kwargs.get("cwd")})
        items = {
            item["id"]: {"decided_by": "fake", "fake": table[item["id"]]}
            for item in json.loads(input)["items"] if item["id"] in table
        }
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"items": items}), stderr="")
    return run


def jev_root(case) -> tuple:
    """(skills root holding a jev client, env with a scratch HOME)."""
    tmp = tempfile.TemporaryDirectory()
    case.addCleanup(tmp.cleanup)
    entry_dir = os.path.join(tmp.name, "skills", "jev-fast-decision", "scripts")
    os.makedirs(entry_dir)
    with open(os.path.join(entry_dir, "jev_review.py"), "w", encoding="utf-8"):
        pass
    return os.path.join(tmp.name, "skills"), {"HOME": os.path.join(tmp.name, "home")}


def f(title, severity, source="skipped", reason="the limit is named", matched=True):
    return jev_review.Finding(title, severity, source, reason, matched)


def routes(result):
    return [r.route for r in result.routes]


def raising_run(*_args, **_kwargs):
    raise AssertionError("jev must not be called")


def undecodable_run(*_args, **_kwargs):
    raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")


ESCALATED_HIGH = (
    "### Findings escalated\n"
    "- **Missing rollback** — Severity: HIGH. Reason for escalation: needs the author. "
    "Caller decision needed.\n"
)
SKIPPED_LOOSE = (
    "### Findings skipped (MEDIUM or LOW only, with disagreement noted)\n"
    "- **Loose wording** — Severity: MEDIUM. Reason: the limit is named in section one. "
    "NOT addressed in this pass.\n"
)


def report_of(*bullets):
    return "## Review: docs/x.md\n### MEDIUM\n" + "".join(bullets) + (
        "### Status: Issues Found — fix and re-invoke\n")


def bullet(title, location, required="name the limit", why="readers guess"):
    return f"- **{title}** — Location: {location}. Required: {required}. Why: {why}.\n"


CODE_REPORT = ("## Review: code\n### HIGH\n" + bullet("Retry loop never stops", "src/retry.py:12")
              + "### MEDIUM\n" + bullet("Rename the helper", "src/retry.py:30")
              + "### Status: Issues Found — fix and re-invoke\n")
CODE_DISCUSS = (
    "### Findings escalated\n"
    "- **Retry loop never stops** — Severity: HIGH. Reason for escalation: needs a design call. "
    "Caller decision needed.\n"
    "- **Rename the helper** — Severity: MEDIUM. Reason for escalation: a style choice. "
    "Caller decision needed.\n"
)


class TestMergedReportBullets(unittest.TestCase):
    def test_merged_report_round_trips_through_the_parser(self):
        text = merged(REPORT_A, REPORT_B)
        self.assertIn("(Reviewers: lane-0, lane-1)", text)
        keys = ("severity", "title", "location", "required", "why")
        parsed = [{k: f[k] for k in keys} for f in review_reports.parse_findings(text)]
        expected = [
            {k: f[k] for k in keys}
            for f in review_reports.merge_findings([("lane-0", REPORT_A), ("lane-1", REPORT_B)])
        ]
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed, expected)


class TestClassifyDisagreements(unittest.TestCase):
    def test_skipped_medium_on_edits_applied_goes_to_the_fixer(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = os.path.join(tmp, "report.md")
            summary = os.path.join(tmp, "summary.md")
            cwd = os.path.join(tmp, "reviewed")
            os.mkdir(cwd)
            with open(report, "w", encoding="utf-8") as handle:
                handle.write(merged(REPORT_A, REPORT_B))
            with open(summary, "w", encoding="utf-8") as handle:
                handle.write(SUMMARY)
            calls = []
            out = io.StringIO()
            argv = ["classify-disagreements", "--cwd", cwd, "--report", report,
                    "--fix-summary", summary, "--iteration", "1", "--cap", "3"]
            run = answers_run({"d0": {"choice": "mechanical", "top": 0.9}}, calls)
            with mock.patch.object(jev_names, "find_jev", return_value="fake-entry"), \
                    redirect_stdout(out):
                code = cli.main(argv, run_fn=run)
            self.assertEqual(code, 0)
            printed = json.loads(out.getvalue())
            self.assertEqual(printed["jev"], "asked")
            self.assertEqual(printed["fixer"], [{
                "title": "Loose wording", "severity": "MEDIUM", "source": "skipped",
                "class": "mechanical", "confidence": 0.9}])
            self.assertEqual(printed["owner"], [])
            self.assertEqual(printed["skipped"], [])
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["cwd"], cwd)
            self.assertTrue(hasattr(jev_review, "classify_disagreements"))

    def test_each_class_routes_as_written(self):
        root, env = jev_root(self)
        items = [f("a", "MEDIUM"), f("b", "MEDIUM"), f("c", "MEDIUM"),
                 f("d", "CROSS-DOC"), f("e", "none"), f("g", "CROSS-DOC"), f("h", "none")]
        table = {
            "d0": {"choice": "owner_decision", "top": 0.9},
            "d1": {"choice": "mechanical", "top": 0.9},
            "d2": {"choice": "reviewer_wrong", "top": 0.91},
            "d3": {"choice": "reviewer_wrong", "top": 0.95},
            "d4": {"choice": "reviewer_wrong", "top": 0.95},
            "d5": {"choice": "mechanical", "top": 0.95},
            "d6": {"choice": "mechanical", "top": 0.95},
        }
        result = jev_review.classify_disagreements(
            items, env, answers_run(table, []),
            jev_review.ClassifyOptions(own_root=root, limits=(1, 3)))
        self.assertEqual(result.jev, "asked")
        self.assertEqual(routes(result), ["owner", "fixer", "skipped"] + ["owner"] * 4)
        self.assertEqual(result.routes[2].note, "jev: reviewer_wrong (0.91)")

    def test_owner_items_are_appended_to_the_owner_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = os.path.join(tmp, "report.md")
            summary = os.path.join(tmp, "summary.md")
            owner_out = os.path.join(tmp, "owner-items.json")
            cwd = os.path.join(tmp, "reviewed")
            os.mkdir(cwd)
            with open(report, "w", encoding="utf-8") as handle:
                handle.write(merged(REPORT_A, REPORT_B))
            with open(summary, "w", encoding="utf-8") as handle:
                handle.write("## Fix Summary\n" + ESCALATED_HIGH + SKIPPED_LOOSE
                             + "### Status: Edits Applied\n")
            table = {"d0": {"choice": "mechanical", "top": 0.9},
                     "d1": {"choice": "mechanical", "top": 0.9}}
            argv = ["classify-disagreements", "--cwd", cwd, "--report", report,
                    "--fix-summary", summary, "--iteration", "1", "--cap", "3",
                    "--owner-out", owner_out]
            expected = {"title": "Missing rollback", "severity": "HIGH", "source": "escalated",
                        "class": "mechanical", "confidence": 0.9}
            with mock.patch.object(jev_names, "find_jev", return_value="fake-entry"):
                for count in (1, 2):
                    with redirect_stdout(io.StringIO()):
                        code = cli.main(argv, run_fn=answers_run(table, []))
                    self.assertEqual(code, 0)
                    with open(owner_out, encoding="utf-8") as handle:
                        lines = handle.read().splitlines()
                    self.assertEqual([json.loads(line) for line in lines], [expected] * count)
                bad = [*argv[:-1], tmp]
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    code = cli.main(bad, run_fn=answers_run(table, []))
            self.assertEqual(code, 2)
            self.assertTrue(err.getvalue().startswith("classify-disagreements:"))
            self.assertEqual(out.getvalue(), "")

    def test_mechanical_at_the_cap_goes_to_the_owner(self):
        root, env = jev_root(self)
        for limits in ((3, 3), (None, None)):
            with self.subTest(limits=limits):
                run = answers_run({"d0": {"choice": "mechanical", "top": 0.9}}, [])
                result = jev_review.classify_disagreements(
                    [f("a", "MEDIUM")], env, run,
                    jev_review.ClassifyOptions(own_root=root, limits=limits))
                self.assertEqual(routes(result), ["owner"])

    def test_serious_findings_always_reach_the_owner(self):
        root, env = jev_root(self)
        table = {"d0": {"choice": "reviewer_wrong", "top": 0.99},
                 "d1": {"choice": "mechanical", "top": 0.99}}
        result = jev_review.classify_disagreements(
            [f("a", "CRITICAL"), f("b", "HIGH")], env, answers_run(table, []),
            jev_review.ClassifyOptions(own_root=root, limits=(1, 3)))
        self.assertEqual(routes(result), ["owner", "owner"])
        self.assertEqual([r.klass for r in result.routes], ["reviewer_wrong", "mechanical"])

    def test_severity_comes_from_the_report(self):
        root, env = jev_root(self)
        summary = (
            "### Findings skipped (MEDIUM or LOW only, with disagreement noted)\n"
            "- **Missing rollback** — Severity: MEDIUM. Reason: not needed. "
            "NOT addressed in this pass.\n"
        )
        items = jev_review.disagreement_items(merged(REPORT_A), summary, False)
        self.assertEqual(items[0].severity, "HIGH")
        calls = []
        run = answers_run({"d0": {"choice": "reviewer_wrong", "top": 0.95}}, calls)
        result = jev_review.classify_disagreements(
            items, env, run, jev_review.ClassifyOptions(own_root=root, limits=(1, 3)))
        self.assertEqual(routes(result), ["owner"])
        context = calls[0]["payload"]["items"][0]["context"]
        self.assertTrue(context.startswith("Severity: HIGH."))

    def test_duplicate_or_unknown_titles_go_to_the_owner(self):
        root, env = jev_root(self)
        text = merged(report_of(bullet("Loose wording", "§2"), bullet("Loose wording", "§5")))
        items = jev_review.disagreement_items(text, SKIPPED_LOOSE, False)
        self.assertEqual(len(items), 1)
        self.assertFalse(items[0].matched)
        with mock.patch.object(jev_names, "find_jev", side_effect=AssertionError):
            result = jev_review.classify_disagreements(
                items, env, raising_run,
                jev_review.ClassifyOptions(own_root=root, limits=(1, 3)))
        self.assertEqual(result, jev_review.Classified("not needed", [jev_review.Route(
            "Loose wording", "MEDIUM", "skipped", None, None, "owner",
            "no unique report match")]))
        located = SKIPPED_LOOSE.replace("in section one.", "in §5.")
        items = jev_review.disagreement_items(text, located, False)
        self.assertTrue(items[0].matched)
        unknown = SKIPPED_LOOSE.replace("Loose wording", "Unknown title")
        items = jev_review.disagreement_items(text, unknown, False)
        self.assertFalse(items[0].matched)
        items = jev_review.disagreement_items(text, SKIPPED_LOOSE, True)
        self.assertEqual([i.source for i in items], ["skipped", "cap-open", "cap-open"])
        self.assertEqual([i.matched for i in items], [False, True, True])

    def test_low_or_unusable_answers_go_to_the_owner(self):
        root, env = jev_root(self)
        cases = (
            {"choice": "mechanical", "top": 0.79},
            {"choice": "mechanical", "top": 0.95, "needs_fallback": True},
            {"choice": "not_a_class", "top": 0.95},
        )
        for column in cases:
            with self.subTest(column=column):
                result = jev_review.classify_disagreements(
                    [f("a", "MEDIUM")], env, answers_run({"d0": column}, []),
                    jev_review.ClassifyOptions(own_root=root, limits=(1, 3)))
                self.assertEqual(routes(result), ["owner"])

        def failing(argv, input="", **_kwargs):
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom")

        with self.subTest(column="exit 1"):
            result = jev_review.classify_disagreements(
                [f("a", "MEDIUM")], env, failing,
                jev_review.ClassifyOptions(own_root=root, limits=(1, 3)))
            self.assertEqual(routes(result), ["owner"])

    def test_absent_jev_sends_everything_to_the_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"HOME": os.path.join(tmp, "home")}
            result = jev_review.classify_disagreements(
                [f("a", "MEDIUM"), f("b", "LOW")], env, raising_run,
                jev_review.ClassifyOptions(own_root=tmp, limits=(1, 3)))
            self.assertEqual(result.jev, "absent")
            self.assertEqual(routes(result), ["owner", "owner"])
            self.assertEqual({r.note for r in result.routes}, {"jev absent"})
            report = os.path.join(tmp, "report.md")
            summary = os.path.join(tmp, "summary.md")
            with open(report, "w", encoding="utf-8") as handle:
                handle.write(merged(REPORT_A, REPORT_B))
            with open(summary, "w", encoding="utf-8") as handle:
                handle.write(SUMMARY)
            argv = ["classify-disagreements", "--cwd", tmp, "--report", report,
                    "--fix-summary", summary, "--iteration", "1", "--cap", "3"]
            out = io.StringIO()
            with mock.patch.object(jev_names, "find_jev", return_value=None), \
                    redirect_stdout(out):
                code = cli.main(argv, run_fn=raising_run)
        self.assertEqual(code, 0)
        printed = json.loads(out.getvalue())
        self.assertEqual(printed["jev"], "absent")
        self.assertEqual([e["title"] for e in printed["owner"]], ["Loose wording"])
        self.assertEqual(printed["fixer"] + printed["skipped"], [])

    def test_no_items_means_no_jev_call(self):
        _root, env = jev_root(self)
        with mock.patch.object(jev_names, "find_jev", side_effect=AssertionError):
            result = jev_review.classify_disagreements([], env, raising_run)
        self.assertEqual(result, jev_review.Classified("not needed", []))
        self.assertEqual(jev_review.disagreement_items(merged(REPORT_A), "", False), [])
        items = jev_review.disagreement_items(merged(REPORT_A, REPORT_B), SUMMARY, True)
        self.assertEqual(
            [(i.title, i.source, i.severity) for i in items],
            [("Loose wording", "skipped", "MEDIUM"), ("Missing rollback", "cap-open", "HIGH")])

    def test_payload_holds_summaries_only(self):
        root, env = jev_root(self)
        title = ('Fix "hunter2 value" in docs/plan.md near api_key=abc123 and '
                 "0123456789abcdef0123 via host:8080")
        reason = ("the value `secret_cfg` and 'quoted' path C:\\temp\\x and "
                  "token=feedface0011 break it")
        while len(reason) < 300:
            reason += " plain words"
        text = merged(report_of(bullet(
            title, "§9 of docs/plan.md", "rewrite the loop", "the old loop leaks")))
        summary = (f"### Findings escalated\n- **{title}** — Severity: MEDIUM. "
                   f"Reason for escalation: {reason} Caller decision needed.\n")
        shape = (r"Severity: [A-Z-]+\. Finding: .{1,80}\. Fixer: .{1,160}\. "
                 r"Source: (escalated|skipped|cap-open)\.")
        calls = []
        run = answers_run({"d0": {"choice": "mechanical", "top": 0.95}}, calls)
        jev_review.classify_disagreements(
            jev_review.disagreement_items(text, summary, False), env, run,
            jev_review.ClassifyOptions(own_root=root, limits=(1, 3)))
        self.assertEqual(len(calls), 1)
        sent = json.dumps(calls[0]["payload"], ensure_ascii=False)
        for item in calls[0]["payload"]["items"]:
            self.assertIsNotNone(re.fullmatch(shape, item["context"]), item["context"])
            self.assertNotIn("\\temp", item["context"])
        banned = ("hunter2", "docs/plan.md", "plan.md", "api_key", "abc123", "0123456789abcdef",
                  "host:8080", "secret_cfg", "quoted", "C:\\temp", "C:\\\\temp", "feedface",
                  "§9", "rewrite the loop", "the old loop leaks")
        for needle in banned:
            self.assertNotIn(needle, sent)
        self.assertIn("[omitted]", sent)

        token = "ghp_" + "Zqxlmnop" * 2 + "Zqxl"
        self.assertNotEqual(secret_shapes.redact(token, "[redacted]"), token)
        self.assertIsNone(code_review._UNSAFE_TOKEN_RE.search(token))
        long_title = "wordy " * 11 + "xyz" + " " + token
        self.assertEqual(long_title.index(token), 70)
        text = merged(report_of(bullet(long_title, "§1")))
        summary = (f"### Findings escalated\n- **{long_title}** — Severity: MEDIUM. "
                   "Reason for escalation: plain words. Caller decision needed.\n")
        calls = []
        run = answers_run({"d0": {"choice": "mechanical", "top": 0.95}}, calls)
        result = jev_review.classify_disagreements(
            jev_review.disagreement_items(text, summary, False), env, run,
            jev_review.ClassifyOptions(own_root=root, limits=(1, 3)))
        self.assertEqual(result.jev, "asked")
        self.assertEqual(len(calls), 1)
        self.assertNotIn(token[:12], json.dumps(calls[0]["payload"], ensure_ascii=False))


class TestClassifyCodeKind(unittest.TestCase):
    def run_classify(self, run_or_table, jev_entry: str | None = "fake-entry",
                     discuss=CODE_DISCUSS, kind: str | None = "code"):
        """The classify CLI call shape of the fixer test, kind `None` omitting `--kind`."""
        with tempfile.TemporaryDirectory() as tmp:
            report = os.path.join(tmp, "report.md")
            summary = os.path.join(tmp, "summary.md")
            cwd = os.path.join(tmp, "reviewed")
            os.mkdir(cwd)
            with open(report, "w", encoding="utf-8") as handle:
                handle.write(CODE_REPORT)
            with open(summary, "w", encoding="utf-8") as handle:
                handle.write(discuss)
            calls = []
            run = (answers_run(run_or_table, calls) if isinstance(run_or_table, dict)
                   else run_or_table)
            argv = ["classify-disagreements"]
            if kind is not None:
                argv += ["--kind", kind]
            argv += ["--cwd", cwd, "--report", report, "--fix-summary", summary,
                     "--iteration", "1", "--cap", "3"]
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(jev_names, "find_jev", return_value=jev_entry), \
                    redirect_stdout(out), redirect_stderr(err):
                code = cli.main(argv, run_fn=run)
        return code, out.getvalue(), err.getvalue(), calls

    def test_default_kind_item_is_unchanged(self):
        self.assertEqual(jev_review.finding_item(0, f("Loose wording", "MEDIUM")), {
            "id": "d0", "type": "choice", "instructions": jev_review.CLASSIFY_QUESTION,
            "context": "Severity: MEDIUM. Finding: Loose wording. "
                       "Fixer: the limit is named. Source: skipped.",
            "criteria": dict(jev_review.CLASSES)})

    def test_code_item_holds_severity_title_and_source_only(self):
        self.assertEqual(
            jev_review.finding_item(
                0, f("load(path=x) leaks", "MEDIUM", reason="see src/a.py:3"), "code"),
            {"id": "d0", "type": "choice", "instructions": jev_review.CODE_CLASSIFY_QUESTION,
             "context": "Severity: MEDIUM. Finding: [omitted] leaks. Source: skipped.",
             "criteria": dict(jev_review.CODE_CLASSES)})

    def test_no_jev_sends_both_to_the_owner(self):
        code, out, _err, calls = self.run_classify(raising_run, jev_entry=None)
        self.assertEqual(code, 0)
        printed = json.loads(out)
        self.assertEqual(printed["jev"], "absent")
        self.assertEqual([e["title"] for e in printed["owner"]],
                         ["Retry loop never stops", "Rename the helper"])
        self.assertEqual([e["reason"] for e in printed["owner"]], ["jev absent"] * 2)
        self.assertEqual(printed["fixer"] + printed["skipped"], [])
        self.assertEqual(calls, [])

    def test_a_failed_call_sends_both_to_the_owner(self):
        def failing(argv, input="", **_kwargs):
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom")

        code, out, _err, _calls = self.run_classify(failing)
        self.assertEqual(code, 0)
        printed = json.loads(out)
        self.assertEqual([e["title"] for e in printed["owner"]],
                         ["Retry loop never stops", "Rename the helper"])
        self.assertEqual(printed["fixer"] + printed["skipped"], [])

    def test_low_answers_send_both_to_the_owner(self):
        table = {"d0": {"choice": "mechanical", "top": 0.5},
                 "d1": {"choice": "mechanical", "top": 0.5}}
        code, out, _err, _calls = self.run_classify(table)
        self.assertEqual(code, 0)
        printed = json.loads(out)
        self.assertEqual([e["title"] for e in printed["owner"]],
                         ["Retry loop never stops", "Rename the helper"])
        self.assertEqual(printed["fixer"] + printed["skipped"], [])

    def test_needs_fallback_answers_send_both_to_the_owner(self):
        table = {"d0": {"choice": "mechanical", "top": 0.95, "needs_fallback": True},
                 "d1": {"choice": "mechanical", "top": 0.95, "needs_fallback": True}}
        code, out, _err, _calls = self.run_classify(table)
        self.assertEqual(code, 0)
        printed = json.loads(out)
        self.assertEqual([e["title"] for e in printed["owner"]],
                         ["Retry loop never stops", "Rename the helper"])
        self.assertEqual(printed["fixer"] + printed["skipped"], [])

    def test_confident_reviewer_wrong_skips_only_the_medium(self):
        table = {"d0": {"choice": "reviewer_wrong", "top": 0.95},
                 "d1": {"choice": "reviewer_wrong", "top": 0.95}}
        code, out, _err, calls = self.run_classify(table)
        self.assertEqual(code, 0)
        printed = json.loads(out)
        self.assertEqual([e["title"] for e in printed["owner"]], ["Retry loop never stops"])
        self.assertEqual([e["title"] for e in printed["skipped"]], ["Rename the helper"])
        self.assertEqual(printed["skipped"][0]["reason"], "jev: reviewer_wrong (0.95)")
        items = calls[0]["payload"]["items"]
        self.assertEqual([item["instructions"] for item in items],
                         [jev_review.CODE_CLASSIFY_QUESTION] * 2)
        for item in items:
            self.assertNotIn("src/", item["context"])
            self.assertNotIn("needs a design call", item["context"])
            self.assertNotIn("a style choice", item["context"])

    def test_confident_mechanical_on_the_medium_goes_to_the_fixer(self):
        table = {"d0": {"choice": "mechanical", "top": 0.95},
                 "d1": {"choice": "mechanical", "top": 0.95}}
        code, out, _err, _calls = self.run_classify(table)
        self.assertEqual(code, 0)
        printed = json.loads(out)
        self.assertEqual([e["title"] for e in printed["owner"]], ["Retry loop never stops"])
        self.assertEqual([e["title"] for e in printed["fixer"]], ["Rename the helper"])
        self.assertEqual(printed["skipped"], [])

    def test_document_kind_by_default_on_the_cli(self):
        code, out, _err, calls = self.run_classify(
            {"d0": {"choice": "mechanical", "top": 0.9}}, kind=None)
        self.assertEqual(code, 0)
        printed = json.loads(out)
        self.assertEqual(printed["jev"], "asked")
        for item in calls[0]["payload"]["items"]:
            self.assertEqual(item["instructions"], jev_review.CLASSIFY_QUESTION)
            self.assertEqual(item["criteria"], dict(jev_review.CLASSES))

    def test_malformed_escalation_exits_3_for_code(self):
        malformed = CODE_DISCUSS.replace("Severity: MEDIUM. Reason", "Severity: MEDIUM Reason")
        code, out, err, calls = self.run_classify(raising_run, discuss=malformed)
        self.assertEqual(code, 3)
        self.assertEqual(err.strip(), jev_review.NO_MATCH)
        self.assertEqual(out, "")
        self.assertEqual(calls, [])
        code, out, _err, _calls = self.run_classify(
            {"d0": {"choice": "mechanical", "top": 0.9}}, discuss=malformed, kind=None)
        self.assertEqual(code, 0)
        printed = json.loads(out)
        self.assertEqual([e["title"] for e in printed["owner"]], ["Retry loop never stops"])
        self.assertEqual(printed["fixer"] + printed["skipped"], [])


ROSTER = "".join(
    f'''[[lanes.review]]
key = "lane-{letter}"
model = "placeholder-model-{index}"
vendor = "vendor-{index}"
command = "placeholder-cli-1 {{model}}"
'''
    for index, letter in enumerate("abc", 1)
) + '''[lanes.policy.review]
ladder = ["lane-a", "lane-b", "lane-c"]
'''


class TestSizeReviewCommand(unittest.TestCase):
    FIXTURES = os.path.join(_REPO_ROOT, "tests", "fixtures", "review_signals")

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.cwd = os.path.join(tmp.name, "project")
        os.makedirs(self.cwd)
        self.env = {"HOME": os.path.join(tmp.name, "home"),
                    "XDG_CONFIG_HOME": os.path.join(tmp.name, "xdg"),
                    "XDG_CACHE_HOME": os.path.join(tmp.name, "cache")}
        path = config_io.cfg_global_path(self.env)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(ROSTER)
        self.reviewers = os.path.join(tmp.name, "reviewers.json")
        self.log = os.path.join(tmp.name, "lanes.jsonl")
        self.quota = os.path.join(tmp.name, "quota.json")
        self.write_rows(["lane-a"])

    def write_rows(self, keys):
        rows = [{"key": key, "model": f"placeholder-model-{ord(key[-1]) - 96}",
                 "vendor": f"vendor-{ord(key[-1]) - 96}", "runtime": None,
                 "command": "placeholder-cli-1 {model}", "extra": {}, "route": "custom"}
                for key in keys]
        with open(self.reviewers, "w", encoding="utf-8") as stream:
            json.dump(rows, stream)

    def read_rows(self):
        with open(self.reviewers, encoding="utf-8") as stream:
            return json.load(stream)

    def keys(self):
        return [row["key"] for row in self.read_rows()]

    def events(self):
        with open(self.log, encoding="utf-8") as stream:
            return [json.loads(line) for line in stream if line.strip()]

    def cli(self, argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(argv, env_fn=lambda: dict(self.env),
                            which_fn=lambda *_a, **_k: None, run_fn=raising_run)
        return code, out.getvalue()

    def size(self, doc):
        return self.cli([
            "size-review", "--cwd", self.cwd, "--reviewers-json", self.reviewers,
            "--doc", os.path.join(self.FIXTURES, doc), "--archetype", "plan",
            "--framework", "superpowers", "--lane-log", self.log,
            "--quota-path", self.quota, "--cross-ai"])

    def mark_unavailable(self, *keys):
        row = {"available": False, "checked_at": 1.0, "reason": "quota", "detail": "fake",
               "answered": True}
        cache.cache_write_json(self.quota, {key: dict(row) for key in keys})

    def test_security_plan_gets_two_lanes_without_asking_jev(self):
        with mock.patch.object(jev_names, "find_jev", side_effect=AssertionError("jev asked")):
            code, out = self.size("security_plan.md")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "sizing: 2 lane(s): signal security")
        self.assertEqual(self.keys(), ["lane-a", "lane-b"])
        events = self.events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["round"], 0)
        self.assertEqual(events[0]["sizing"]["lanes"], 2)
        self.assertEqual(events[0]["sizing"]["keys"], ["lane-a", "lane-b"])

    def test_plain_plan_without_jev_keeps_the_count(self):
        with open(self.reviewers, "rb") as stream:
            before = stream.read()
        with mock.patch.object(jev_names, "find_jev", return_value=None):
            code, out = self.size("plain_plan.md")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "sizing: 1 lane(s): jev absent: configured count kept")
        with open(self.reviewers, "rb") as stream:
            self.assertEqual(stream.read(), before)
        self.assertEqual(len(self.events()), 1)

    def test_failed_log_write_leaves_reviewers_unchanged(self):
        with open(self.reviewers, "rb") as stream:
            before = stream.read()
        err = io.StringIO()
        with mock.patch.object(jev_names, "find_jev", side_effect=AssertionError("jev asked")), \
                mock.patch.object(review_log, "append_event", side_effect=OSError("disk full")), \
                redirect_stderr(err):
            code, out = self.size("security_plan.md")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("size-review: disk full", err.getvalue())
        with open(self.reviewers, "rb") as stream:
            self.assertEqual(stream.read(), before)

    def test_quota_excluded_lane_is_never_re_added(self):
        self.mark_unavailable("lane-a")
        code, out = self.cli(["resolve-reviewers", "--cwd", self.cwd,
                              "--quota-path", self.quota, "--cross-ai"])
        self.assertEqual(code, 0)
        with open(self.reviewers, "w", encoding="utf-8") as stream:
            stream.write(out)
        self.assertEqual(self.keys(), ["lane-b"])
        with mock.patch.object(jev_names, "find_jev", side_effect=AssertionError("jev asked")):
            self.size("security_plan.md")
        self.assertEqual(self.keys(), ["lane-b", "lane-c"])
        for event in self.events():
            self.assertNotIn("lane-a", event["sizing"]["keys"])
        self.mark_unavailable("lane-a", "lane-c")
        self.write_rows(["lane-b"])
        with mock.patch.object(jev_names, "find_jev", side_effect=AssertionError("jev asked")):
            _code, out = self.size("security_plan.md")
        self.assertEqual(self.keys(), ["lane-b"])
        self.assertEqual(
            out.strip(),
            "sizing: 1 lane(s): signal security wants two lanes; "
            "the roster has no second eligible lane")

    def test_security_plan_with_the_author_vendor_first_gets_two_lanes(self):
        code, out = self.cli(["resolve-reviewers", "--cwd", self.cwd, "--quota-path", self.quota,
                              "--source-vendor", "vendor-1", "--cross-ai"])
        self.assertEqual(code, 0)
        with open(self.reviewers, "w", encoding="utf-8") as stream:
            stream.write(out)
        self.assertEqual(self.keys(), ["lane-b"])
        with mock.patch.object(jev_names, "find_jev", side_effect=AssertionError("jev asked")):
            code, out = self.cli([
                "size-review", "--cwd", self.cwd, "--reviewers-json", self.reviewers,
                "--doc", os.path.join(self.FIXTURES, "security_plan.md"), "--archetype", "plan",
                "--framework", "superpowers", "--lane-log", self.log,
                "--quota-path", self.quota, "--source-vendor", "vendor-1", "--cross-ai"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "sizing: 2 lane(s): signal security")
        self.assertEqual(self.keys(), ["lane-b", "lane-a"])


SIZE_CONFIG = {
    "review": [
        {"key": f"lane-{letter}", "model": f"placeholder-model-{index}",
         "vendor": f"vendor-{index}", "command": "placeholder-cli-1 {model}"}
        for index, letter in enumerate("abc", 1)
    ],
    "orders": {"review": ["lane-a", "lane-b", "lane-c"]},
}
ROUTES = {"lane-a": "custom", "lane-b": "custom", "lane-c": "custom"}
FIXTURE_DIR = os.path.join(_REPO_ROOT, "tests", "fixtures", "review_signals")


def fixture_text(name):
    with open(os.path.join(FIXTURE_DIR, name), encoding="utf-8") as stream:
        return stream.read()


PLAIN = fixture_text("plain_plan.md")
SECURITY = fixture_text("security_plan.md")


def rows_for(keys):
    return [dict(quota.to_resolved(lane)._asdict(), route="custom")
            for key in keys for lane in SIZE_CONFIG["review"] if lane["key"] == key]


def size_input(rows, text, **over):
    return jev_review.SizeInput(**{
        "config": SIZE_CONFIG, "reviewers": rows, "text": text,
        "paths": review_signals.plan_paths(text), "archetype": "plan",
        "framework": "superpowers", "quota": {}, "routes": dict(ROUTES),
        "source_vendor": "", "cross_ai": True, **over})


def strict_run(table, calls):
    inner = answers_run(table, calls)

    def run(argv, input="", **kwargs):
        for item in json.loads(input)["items"]:
            if item["type"] == "choice":
                assert len(item["criteria"]) >= 2, item["id"]
        return inner(argv, input=input, **kwargs)
    return run


def both(lanes, reviewer):
    return {"lanes": lanes, "reviewer": reviewer}


def keys_of(sizing):
    return [row["key"] for row in sizing.reviewers]


class TestSizeReview(unittest.TestCase):
    def setUp(self):
        self.root, self.env = jev_root(self)

    def size(self, rows, text, run, **over):
        return jev_review.size_review(
            size_input(rows, text, **over), self.env, run, own_root=self.root)

    def test_signal_forces_two_whatever_jev_says(self):
        result = self.size(rows_for(["lane-a"]), SECURITY, raising_run)
        self.assertEqual(keys_of(result), ["lane-a", "lane-b"])
        self.assertEqual(result.reason, "signal security")

    def test_same_vendor_first_lane_joins_when_the_pick_is_the_secondary(self):
        result = self.size(rows_for(["lane-b"]), SECURITY, raising_run, source_vendor="vendor-1")
        self.assertEqual((keys_of(result), result.reason),
                         (["lane-b", "lane-a"], "signal security"))
        table = both({"choice": "two", "top": 0.9}, {"choice": "p1", "top": 0.9})
        result = self.size(rows_for(["lane-b"]), PLAIN, strict_run(table, []),
                           source_vendor="vendor-1")
        self.assertEqual((keys_of(result), result.reason), (["lane-b", "lane-a"], "jev two (0.90)"))

    def test_confident_one_gives_one_lane(self):
        table = both({"choice": "one", "top": 0.86}, {"choice": "p1", "top": 0.9})
        result = self.size(rows_for(["lane-a", "lane-b"]), PLAIN, strict_run(table, []))
        self.assertEqual(keys_of(result), ["lane-a"])
        self.assertEqual(result.reason, "jev one (0.86)")

    def test_confident_two_adds_the_next_eligible_lane_and_moves_the_pick(self):
        table = both({"choice": "two", "top": 0.9}, {"choice": "p2", "top": 0.9})
        result = self.size(rows_for(["lane-a"]), PLAIN, strict_run(table, []))
        self.assertEqual(keys_of(result), ["lane-b", "lane-a"])
        self.assertEqual(result.reason, "jev two (0.90)")
        result = self.size(rows_for(["lane-a"]), PLAIN, strict_run(table, []),
                           quota={"lane-b": {"available": False}})
        self.assertEqual(keys_of(result), ["lane-c", "lane-a"])

    def test_low_or_failed_answers_keep_the_rows(self):
        rows = rows_for(["lane-a", "lane-b"])
        low = "jev low: configured count kept"

        def failing(argv, input="", **_kwargs):
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom")

        cases = {
            "low lanes": strict_run(both({"choice": "one", "top": 0.5},
                                         {"choice": "p2", "top": 0.95}), []),
            "needs fallback": strict_run(both(
                {"choice": "one", "top": 0.95, "needs_fallback": True},
                {"choice": "p2", "top": 0.95}), []),
            "exit 1": failing,
        }
        for name, run in cases.items():
            with self.subTest(name):
                result = self.size(rows, PLAIN, run)
                self.assertEqual(result.reviewers, rows)
                self.assertEqual(result.reason, low)
        table = both({"choice": "two", "top": 0.9}, {"choice": "p2", "top": 0.5})
        result = self.size(rows, PLAIN, strict_run(table, []))
        self.assertEqual(keys_of(result), ["lane-a", "lane-b"])
        with tempfile.TemporaryDirectory() as empty:
            result = jev_review.size_review(
                size_input(rows, PLAIN), {"HOME": os.path.join(empty, "home")},
                raising_run, own_root=empty)
        self.assertEqual(result.reviewers, rows)
        self.assertEqual(result.reason, "jev absent: configured count kept")

    def test_unusable_pick_with_a_count_changing_answer(self):
        table = both({"choice": "two", "top": 0.9}, {"choice": "p9", "top": 0.95})
        result = self.size(rows_for(["lane-a"]), PLAIN, strict_run(table, []))
        self.assertEqual(keys_of(result), ["lane-a", "lane-b"])
        table = both({"choice": "one", "top": 0.9}, {"choice": "p9", "top": 0.95})
        result = self.size(rows_for(["lane-a"]), PLAIN, strict_run(table, []))
        self.assertEqual(keys_of(result), ["lane-a"])

    def test_confident_one_keeps_the_picked_reviewer(self):
        table = both({"choice": "one", "top": 0.9}, {"choice": "p2", "top": 0.95})
        for configured in (["lane-a"], ["lane-a", "lane-b"]):
            with self.subTest(configured=configured):
                result = self.size(rows_for(configured), PLAIN, strict_run(table, []))
                self.assertEqual((keys_of(result), result.reason), (["lane-b"], "jev one (0.90)"))
        low_pick = both({"choice": "one", "top": 0.9}, {"choice": "p2", "top": 0.5})
        result = self.size(rows_for(["lane-a", "lane-b"]), PLAIN, strict_run(low_pick, []))
        self.assertEqual(keys_of(result), ["lane-a"])

    def test_reviewer_tokens_name_candidate_lanes(self):
        calls = []
        table = both({"choice": "two", "top": 0.9}, {"choice": "p1", "top": 0.9})
        self.size(rows_for(["lane-a", "lane-b"]), PLAIN, strict_run(table, calls))
        reviewer = next(item for item in calls[0]["payload"]["items"] if item["id"] == "reviewer")
        self.assertEqual(reviewer["criteria"], {"p1": "candidate lane 1", "p2": "candidate lane 2"})
        self.assertIn("candidate lane", reviewer["instructions"])
        self.assertNotIn("review order", reviewer["instructions"])

    def test_no_eligible_second_lane_says_so(self):
        reason = "signal security wants two lanes; the roster has no second eligible lane"
        only_a = {"review": SIZE_CONFIG["review"][:1], "orders": {"review": ["lane-a"]}}
        result = self.size(rows_for(["lane-a"]), SECURITY, raising_run, config=only_a)
        self.assertEqual((keys_of(result), result.reason), (["lane-a"], reason))
        result = self.size(
            rows_for(["lane-a"]), SECURITY, raising_run,
            quota={"lane-b": {"available": False}},
            routes=dict(ROUTES, **{"lane-c": "not_installed"}))
        self.assertEqual((keys_of(result), result.reason), (["lane-a"], reason))

    def test_execute_purpose_lane_is_never_added(self):
        config = copy.deepcopy(SIZE_CONFIG)
        config["review"][1]["purpose"] = "execute"
        result = self.size(rows_for(["lane-a"]), SECURITY, raising_run, config=config)
        self.assertEqual(keys_of(result), ["lane-a", "lane-c"])

    def test_native_lane_with_a_stale_cache_failure_is_added(self):
        stale = {"lane-b": {"available": False, "reason": "auth"}}
        result = self.size(rows_for(["lane-a"]), SECURITY, raising_run, quota=stale,
                           routes=dict(ROUTES, **{"lane-b": "native"}))
        self.assertEqual(keys_of(result), ["lane-a", "lane-b"])
        self.assertEqual(result.reviewers[1]["route"], "native")
        result = self.size(rows_for(["lane-a"]), SECURITY, raising_run, quota=stale)
        self.assertEqual(keys_of(result), ["lane-a", "lane-c"])

    def test_reviewer_item_omitted_below_two_eligible_lanes(self):
        calls = []
        down = {"lane-b": {"available": False}, "lane-c": {"available": False}}
        table = {"lanes": {"choice": "two", "top": 0.9}}
        result = self.size(rows_for(["lane-a"]), PLAIN, strict_run(table, calls), quota=down)
        self.assertEqual([item["id"] for item in calls[0]["payload"]["items"]], ["lanes"])
        self.assertEqual(keys_of(result), ["lane-a"])
        self.assertEqual(result.reason, "jev two (0.90); the roster has no second eligible lane")

    def test_sizing_payload_holds_numbers_tokens_and_labels_only(self):
        calls = []
        table = both({"choice": "one", "top": 0.9}, {"choice": "p1", "top": 0.9})
        self.size(rows_for(["lane-a"]), PLAIN, strict_run(table, calls))
        self.size(rows_for(["lane-a"]), PLAIN, strict_run(table, calls),
                  archetype="docs/secret=1", framework="my-custom-fw")
        shape = re.compile(
            r"Plan facts: tasks \d+, files \d+, steps \d+, complexity (small|medium|large), "
            r"archetype plan, framework superpowers\. Signals: none\.")
        first = calls[0]["payload"]["items"]
        for item in first:
            self.assertIsNotNone(shape.fullmatch(item["context"]), item["context"])
        reviewer = next(item for item in first if item["id"] == "reviewer")
        self.assertEqual(list(reviewer["criteria"]), ["p1", "p2"])
        sent = json.dumps([call["payload"] for call in calls], ensure_ascii=False)
        for needle in ("lane-a", "lane-b", "lane-c", "vendor-", "placeholder-model",
                       "placeholder-cli", "src/docs/contents.py", "Rename the table"):
            self.assertNotIn(needle, sent)
        context = calls[1]["payload"]["items"][0]["context"]
        self.assertIn("archetype other, framework other", context)

    def test_inputs_are_never_mutated(self):
        config_before = copy.deepcopy(SIZE_CONFIG)
        confident = {
            "lanes": {"choice": "two", "top": 0.9}, "reviewer": {"choice": "p2", "top": 0.9}}
        cases = {
            "signal": (SECURITY, raising_run),
            "two with a pick": (PLAIN, strict_run(confident, [])),
            "one": (PLAIN, strict_run(
                both({"choice": "one", "top": 0.9}, {"choice": "p1", "top": 0.9}), [])),
        }
        for name, (text, run) in cases.items():
            with self.subTest(name):
                rows = rows_for(["lane-a"])
                before = copy.deepcopy(rows)
                result = self.size(rows, text, run)
                self.assertEqual(rows, before)
                self.assertEqual(SIZE_CONFIG, config_before)
                self.assertIsNot(result.reviewers, rows)


class TestClassifyExecuteResult(unittest.TestCase):
    def test_execute_default_reads_the_status_token(self):
        direct = {"DONE": "done", "DONE_WITH_CONCERNS": "partial"}
        for status in (*jev_review.IMPLEMENTER_STATUSES, "SOMETHING_ELSE"):
            with self.subTest(status=status):
                self.assertEqual(jev_review.execute_default(status),
                                 direct.get(status, "another_round"))

    def test_confident_answers_decide(self):
        root, env = jev_root(self)
        for klass in jev_review.EXECUTE_CLASSES:
            with self.subTest(klass=klass):
                calls = []
                result = jev_review.classify_execute_result(
                    jev_review.ExecuteFacts("DONE", "ok", ("no_commit",), "2/3"), env,
                    answers_run({"e0": {"choice": klass, "top": 0.9}}, calls), own_root=root)
                self.assertEqual(result, jev_review.LaneClass(klass, "jev", 0.9, ""))

    def test_absent_jev_uses_the_status_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = jev_review.classify_execute_result(
                jev_review.ExecuteFacts("DONE", "ok", ("no_commit",), "2/3"),
                {"HOME": os.path.join(tmp, "home")}, raising_run, own_root=tmp)
        self.assertEqual(result, jev_review.LaneClass("done", "default", None, "jev absent"))

    def test_low_answers_use_the_status_default(self):
        root, env = jev_root(self)
        facts = jev_review.ExecuteFacts("DONE", "ok", (), "1/1")
        cases = (("low top", {"e0": {"choice": "partial", "top": 0.5}}, 0.5),
                 ("needs fallback", {"e0": {"choice": "partial", "top": 0.95,
                                          "needs_fallback": True}}, 0.95))
        for name, table, top in cases:
            with self.subTest(name=name):
                calls = []
                result = jev_review.classify_execute_result(
                    facts, env, answers_run(table, calls), own_root=root)
                self.assertEqual(result, jev_review.LaneClass("done", "default", top, "jev low"))

    def test_empty_status_never_calls_jev(self):
        with mock.patch.object(jev_names, "find_jev", side_effect=AssertionError):
            result = jev_review.classify_execute_result(
                jev_review.ExecuteFacts("", "ok", (), ""), {}, raising_run)
        self.assertEqual(
            result, jev_review.LaneClass("another_round", "default", None, "no lane result"))

    def test_a_report_that_is_not_done_never_calls_jev(self):
        for status in ("DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED"):
            with self.subTest(status=status), \
                    mock.patch.object(jev_names, "find_jev", side_effect=AssertionError):
                result = jev_review.classify_execute_result(
                    jev_review.ExecuteFacts(status, "ok", ("no_commit",), "1/4"), {}, raising_run)
                self.assertEqual(result, jev_review.LaneClass(
                    jev_review.execute_default(status), "default", None, "not a DONE report"))

    def test_the_payload_holds_allowlisted_values_only(self):
        root, env = jev_root(self)
        calls = []
        hostile = jev_review.ExecuteFacts(
            "DONE", "ok; rm -rf /",
            ("no_commit", "../etc/passwd", "task_uncovered", "made_up_code"), "2/3 secret")
        jev_review.classify_execute_result(
            hostile, env, answers_run({"e0": {"choice": "done", "top": 0.9}}, calls),
            own_root=root)
        self.assertEqual(
            calls[0]["payload"]["items"][0]["context"],
            "Implementer status: DONE. Runner status: none. "
            "Runner findings: no_commit, task_uncovered. Coverage: none.")
        sent = json.dumps(calls[0]["payload"])
        for needle in ("rm -rf", "passwd", "made_up_code", "secret"):
            self.assertNotIn(needle, sent)
        jev_review.classify_execute_result(
            jev_review.ExecuteFacts("DONE", "secretword", (), "2/3"), env,
            answers_run({"e0": {"choice": "done", "top": 0.9}}, calls), own_root=root)
        self.assertEqual(
            calls[1]["payload"]["items"][0]["context"],
            "Implementer status: DONE. Runner status: none. "
            "Runner findings: none. Coverage: 2/3.")
        jev_review.classify_execute_result(
            jev_review.ExecuteFacts("DONE", "partial", (), ""), env,
            answers_run({"e0": {"choice": "done", "top": 0.9}}, calls), own_root=root)
        self.assertIn("Runner status: partial.", calls[2]["payload"]["items"][0]["context"])

    def test_handover_status(self):
        classes = jev_review.EXECUTE_CLASSES
        table = [("DONE", "done", "DONE"),
                 ("DONE", "partial", "DONE_WITH_CONCERNS"),
                 ("DONE", "another_round", "DONE_WITH_CONCERNS")]
        table += [(status, klass, status)
                  for status in ("DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED")
                  for klass in classes]
        for status, klass, expected in table:
            with self.subTest(status=status, klass=klass):
                self.assertEqual(jev_review.handover_status(status, klass), expected)

    def test_runner_constants_match_the_template(self):
        text = (pathlib.Path(__file__).resolve().parent.parent / "skills"
                / "ai-kit-spec-review" / "references" / "cross-ai.mjs").read_text(
                    encoding="utf-8")
        line = next(l for l in text.splitlines()
                    if l.startswith("const FINDING_CODES = Object.freeze(["))
        body = line[line.index("[") + 1:line.rindex("]")]
        self.assertEqual(tuple(re.findall(r"'([a-z_]+)'", body)),
                         jev_review.RUNNER_FINDING_CODES)
        for word in jev_review.RUNNER_STATUSES:
            with self.subTest(word=word):
                self.assertIn(f"reportAndFinish('{word}'", text)

    def test_the_cli_prints_json_and_the_log_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv = ["classify-execute-result", "--cwd", tmp, "--status", "DONE",
                    "--runner-status", "ok", "--findings", "no_commit", "--coverage", "n/a"]
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(jev_names, "find_jev", return_value=None), \
                    redirect_stdout(out), redirect_stderr(err):
                code = cli.main(argv, run_fn=raising_run)
        self.assertEqual(code, 0)
        self.assertEqual(
            out.getvalue(),
            '{"class": "done", "decided_by": "default", "confidence": null, '
            '"note": "jev absent", "handover": "DONE"}\n')
        self.assertEqual(err.getvalue(), "ai-kit-spec: lane result: done (default)\n")

    def test_an_undecodable_jev_reply_uses_the_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv = ["classify-execute-result", "--cwd", tmp, "--status", "DONE"]
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(jev_names, "find_jev", return_value="fake-entry"), \
                    redirect_stdout(out), redirect_stderr(err):
                code = cli.main(argv, run_fn=undecodable_run)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["decided_by"], "default")
        self.assertEqual(err.getvalue(), "ai-kit-spec: lane result: done (default)\n")


class TestClassifyFindings(unittest.TestCase):
    LABELED = ("### HIGH\n- **Leak** — Location: src/a.py:2. Required: close it. "
               "Why: it leaks. Labels: kind=security; tier=unit; repro=yes; "
               "reach=user; stage=mvp.\n### MEDIUM\n- **Loose** — Location: src/b.py:3. "
               "Required: tighten it. Why: it drifts. Labels: kind=bogus.\n"
               "### Status: Issues Found — fix and re-invoke\n")

    def cr(self, severity, title="Leak"):
        return {"severity": severity, "title": title, "location": "src/a.py:1",
                "required": "rewrite the loop",
                "why": ("the old loop leaks. Labels: kind=logic; tier=unit; "
                         "repro=yes; reach=user; stage=mvp")}

    def test_an_undecodable_jev_reply_keeps_the_reviewer_severity(self):
        labeled = {**self.cr("MEDIUM"), "why": "it leaks. Labels: kind=security; tier=unit; "
                                               "repro=yes; reach=user; stage=mvp"}
        with mock.patch.object(jev_names, "find_jev", return_value="fake-entry"):
            status, rows = jev_review.classify_findings([labeled], {}, undecodable_run)
        self.assertEqual(status, "asked")
        self.assertEqual([(r["new_severity"], r["decided_by"]) for r in rows],
                         [("MEDIUM", "default")])

    def test_confident_answers_move_the_severity(self):
        root, env = jev_root(self)
        cases = (("LOW", "higher", "MEDIUM", ""),
                 ("MEDIUM", "lower", "LOW", ""),
                 ("HIGH", "higher", "CRITICAL", ""),
                 ("CRITICAL", "higher", "CRITICAL", ""),
                 ("MEDIUM", "fits", "MEDIUM", ""),
                 ("HIGH", "lower", "HIGH", "never lowered"))
        for severity, fit, new, note in cases:
            with self.subTest(severity=severity, fit=fit):
                status, rows = jev_review.classify_findings(
                    [self.cr(severity)], env,
                    answers_run({"f0": {"choice": fit, "top": 0.9}}, []), own_root=root)
                self.assertEqual(status, "asked")
                self.assertEqual(rows, [{
                    "title": "Leak", "severity": severity, "location": "src/a.py:1",
                    "new_severity": new, "fit": fit, "decided_by": "jev",
                    "confidence": 0.9, "note": note}])

    def test_absent_jev_keeps_every_reviewer_severity(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, rows = jev_review.classify_findings(
                [self.cr("LOW"), self.cr("HIGH", "Crash")],
                {"HOME": os.path.join(tmp, "home")}, raising_run, own_root=tmp)
        self.assertEqual(status, "absent")
        self.assertEqual([r["decided_by"] for r in rows], ["default", "default"])
        self.assertEqual([r["new_severity"] for r in rows], ["LOW", "HIGH"])
        self.assertEqual({r["note"] for r in rows}, {"jev absent"})

    def test_low_or_unusable_answers_use_the_default_row(self):
        root, env = jev_root(self)
        cases = (("low top", {"f0": {"choice": "higher", "top": 0.5}}, 0.5),
                 ("needs fallback", {"f0": {"choice": "higher", "top": 0.95,
                                           "needs_fallback": True}}, 0.95))
        for name, table, top in cases:
            with self.subTest(name=name):
                status, rows = jev_review.classify_findings(
                    [self.cr("MEDIUM")], env, answers_run(table, []), own_root=root)
                self.assertEqual(status, "asked")
                self.assertEqual(rows, [{
                    "title": "Leak", "severity": "MEDIUM", "location": "src/a.py:1",
                    "new_severity": "MEDIUM", "fit": None, "decided_by": "default",
                    "confidence": top, "note": "jev low"}])

    def test_no_findings_never_calls_jev(self):
        _root, env = jev_root(self)
        with mock.patch.object(jev_names, "find_jev", side_effect=AssertionError):
            self.assertEqual(jev_review.classify_findings([], env, raising_run),
                             ("not needed", []))

    def test_severities_outside_the_order_stay_default_rows(self):
        _root, env = jev_root(self)
        with mock.patch.object(jev_names, "find_jev", side_effect=AssertionError):
            status, rows = jev_review.classify_findings(
                [self.cr(None, "Unset"), self.cr("CROSS-DOC", "Cross")], env, raising_run)
        self.assertEqual(status, "not needed")
        self.assertEqual([r["new_severity"] for r in rows], [None, "CROSS-DOC"])
        self.assertEqual([r["decided_by"] for r in rows], ["default", "default"])
        self.assertEqual({r["note"] for r in rows}, {""})

    def test_a_finding_with_no_labels_is_not_sent(self):
        root, env = jev_root(self)
        calls = []
        bare = {**self.cr("MEDIUM", "Bare"), "why": "it drifts"}
        status, rows = jev_review.classify_findings(
            [self.cr("MEDIUM"), bare], env,
            answers_run({"f0": {"choice": "higher", "top": 0.9},
                         "f1": {"choice": "higher", "top": 0.9}}, calls), own_root=root)
        self.assertEqual(status, "asked")
        self.assertEqual([item["id"] for item in calls[0]["payload"]["items"]], ["f0"])
        self.assertEqual(rows[0]["new_severity"], "HIGH")
        self.assertEqual(rows[1], {
            "title": "Bare", "severity": "MEDIUM", "location": "src/a.py:1",
            "new_severity": "MEDIUM", "fit": None, "decided_by": "default",
            "confidence": None, "note": "no labels"})

    def test_only_unlabeled_findings_never_call_jev(self):
        _root, env = jev_root(self)
        bare = {**self.cr("HIGH", "Bare"), "why": "it drifts"}
        with mock.patch.object(jev_names, "find_jev", side_effect=AssertionError("jev asked")):
            status, rows = jev_review.classify_findings([bare], env, raising_run)
        self.assertEqual(status, "not needed")
        self.assertEqual([(r["decided_by"], r["note"]) for r in rows], [("default", "no labels")])

    def test_payload_holds_labels_only(self):
        root, env = jev_root(self)
        title = 'Fix "hunter2" in src/app.py near api_key=abc123'
        calls = []
        jev_review.classify_findings(
            [self.cr("MEDIUM", title)], env,
            answers_run({"f0": {"choice": "fits", "top": 0.9}}, calls), own_root=root)
        self.assertEqual(len(calls), 1)
        shape = (r"Severity: [A-Z]+\. Kind: [a-z]+\. Test tier: [a-z0-9]+\. "
                 r"Reproducible: [a-z]+\. End-user reach: [a-z]+\. Stage: [a-z]+\.")
        for item in calls[0]["payload"]["items"]:
            self.assertIsNotNone(re.fullmatch(shape, item["context"]), item["context"])
        sent = json.dumps(calls[0]["payload"])
        for needle in ("hunter2", "src/app.py", "src/a.py", "api_key", "abc123",
                       "Fix", "rewrite the loop", "the old loop leaks"):
            self.assertNotIn(needle, sent)

    def test_labels_reach_jev_through_the_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = os.path.join(tmp, "report.md")
            out = os.path.join(tmp, "rows.json")
            adj = os.path.join(tmp, "adjusted.md")
            with open(report, "w", encoding="utf-8") as handle:
                handle.write(self.LABELED)
            root, env = jev_root(self)
            calls = []
            run = answers_run({"f0": {"choice": "fits", "top": 0.9},
                               "f1": {"choice": "higher", "top": 0.9}}, calls)
            out_s, err_s = io.StringIO(), io.StringIO()
            with mock.patch.object(
                    jev_names, "find_jev",
                    return_value=jev_names.find_jev(env, root)), \
                    redirect_stdout(out_s), redirect_stderr(err_s):
                code = cli.main(["classify-findings", "--cwd", tmp, "--report", report,
                                 "--out", out, "--out-report", adj], run_fn=run)
            self.assertEqual(code, 0, err_s.getvalue())
            items = {item["id"]: item for item in calls[0]["payload"]["items"]}
            self.assertEqual(list(items), ["f0"])
            self.assertIn("Kind: security. Test tier: unit. Reproducible: yes. "
                          "End-user reach: user. Stage: mvp.", items["f0"]["context"])
            self.assertIn("ai-kit-spec: finding fit: jev 1, default 1", err_s.getvalue())
            with open(out, encoding="utf-8") as handle:
                rows = json.load(handle)
            with open(adj, encoding="utf-8") as handle:
                adjusted = handle.read()
        self.assertEqual(rows[1]["note"], "no labels")
        self.assertEqual(rows[1]["decided_by"], "default")
        self.assertIn("### HIGH", adjusted)
        self.assertIn("### MEDIUM", adjusted)
        self.assertEqual([f["severity"] for f in code_review.normalize_report(adjusted)],
                         ["HIGH", "MEDIUM"])

    def test_out_report_may_be_the_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = os.path.join(tmp, "report.md")
            out = os.path.join(tmp, "rows.json")
            with open(report, "w", encoding="utf-8") as handle:
                handle.write(self.LABELED)
            root, env = jev_root(self)
            run = answers_run({"f0": {"choice": "fits", "top": 0.9},
                               "f1": {"choice": "higher", "top": 0.9}}, [])
            out_s, err_s = io.StringIO(), io.StringIO()
            with mock.patch.object(
                    jev_names, "find_jev",
                    return_value=jev_names.find_jev(env, root)), \
                    redirect_stdout(out_s), redirect_stderr(err_s):
                code = cli.main(["classify-findings", "--cwd", tmp, "--report", report,
                                 "--out", out, "--out-report", report], run_fn=run)
            self.assertEqual(code, 0, err_s.getvalue())
            with open(report, encoding="utf-8") as handle:
                adjusted = handle.read()
        self.assertEqual([f["severity"] for f in code_review.normalize_report(adjusted)],
                         ["HIGH", "MEDIUM"])

    def test_cli_writes_the_rows(self):
        text = ("### HIGH\n- **Leak** — Location: src/a.py:2. Required: close it. "
                "Why: it leaks.\n### Status: Issues Found — fix and re-invoke\n")
        with tempfile.TemporaryDirectory() as tmp:
            report = os.path.join(tmp, "report.md")
            out = os.path.join(tmp, "rows.json")
            adj = os.path.join(tmp, "adjusted.md")
            with open(report, "w", encoding="utf-8") as handle:
                handle.write(text)
            out_s, err_s = io.StringIO(), io.StringIO()
            with mock.patch.object(jev_names, "find_jev", return_value=None), \
                    redirect_stdout(out_s), redirect_stderr(err_s):
                code = cli.main(["classify-findings", "--cwd", tmp, "--report", report,
                                 "--out", out, "--out-report", adj], run_fn=raising_run)
            self.assertEqual(code, 0, err_s.getvalue())
            self.assertEqual(json.loads(out_s.getvalue()), {"out": out, "jev": "not needed"})
            with open(out, encoding="utf-8") as handle:
                rows = json.load(handle)
            with open(adj, encoding="utf-8") as handle:
                adjusted = handle.read()
            self.assertIn("ai-kit-spec: finding fit: jev 0, default 1", err_s.getvalue())
        self.assertEqual(rows, [{"title": "Leak", "severity": "HIGH",
                                 "location": "src/a.py:2", "new_severity": "HIGH",
                                 "fit": None, "decided_by": "default", "confidence": None,
                                 "note": "no labels"}])
        self.assertEqual(code_review.normalize_report(adjusted),
                         code_review.normalize_report(text))


if __name__ == "__main__":

    unittest.main()
