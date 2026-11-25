"""jev_review: advisory classification of reviewer-fixer disagreements and review sizing
(fake jev only)."""

import copy
import io
import json
import os
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
            items, env, answers_run(table, []), own_root=root, limits=(1, 3))
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
                    [f("a", "MEDIUM")], env, run, own_root=root, limits=limits)
                self.assertEqual(routes(result), ["owner"])

    def test_serious_findings_always_reach_the_owner(self):
        root, env = jev_root(self)
        table = {"d0": {"choice": "reviewer_wrong", "top": 0.99},
                 "d1": {"choice": "mechanical", "top": 0.99}}
        result = jev_review.classify_disagreements(
            [f("a", "CRITICAL"), f("b", "HIGH")], env, answers_run(table, []),
            own_root=root, limits=(1, 3))
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
            items, env, run, own_root=root, limits=(1, 3))
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
                items, env, raising_run, own_root=root, limits=(1, 3))
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
                    own_root=root, limits=(1, 3))
                self.assertEqual(routes(result), ["owner"])

        def failing(argv, input="", **_kwargs):
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom")

        with self.subTest(column="exit 1"):
            result = jev_review.classify_disagreements(
                [f("a", "MEDIUM")], env, failing, own_root=root, limits=(1, 3))
            self.assertEqual(routes(result), ["owner"])

    def test_absent_jev_sends_everything_to_the_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"HOME": os.path.join(tmp, "home")}
            result = jev_review.classify_disagreements(
                [f("a", "MEDIUM"), f("b", "LOW")], env, raising_run, own_root=tmp,
                limits=(1, 3))
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
            own_root=root, limits=(1, 3))
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
        self.assertIsNone(jev_review._UNSAFE_TOKEN_RE.search(token))
        long_title = "wordy " * 11 + "xyz" + " " + token
        self.assertEqual(long_title.index(token), 70)
        text = merged(report_of(bullet(long_title, "§1")))
        summary = (f"### Findings escalated\n- **{long_title}** — Severity: MEDIUM. "
                   "Reason for escalation: plain words. Caller decision needed.\n")
        calls = []
        run = answers_run({"d0": {"choice": "mechanical", "top": 0.95}}, calls)
        result = jev_review.classify_disagreements(
            jev_review.disagreement_items(text, summary, False), env, run,
            own_root=root, limits=(1, 3))
        self.assertEqual(result.jev, "asked")
        self.assertEqual(len(calls), 1)
        self.assertNotIn(token[:12], json.dumps(calls[0]["payload"], ensure_ascii=False))


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


if __name__ == "__main__":
    unittest.main()
