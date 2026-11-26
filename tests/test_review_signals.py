"""review_signals: security, data and irreversible triggers and plan facts (held-out fixtures)."""

import os
import sys
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import review_signals

FIXTURES = os.path.join(_REPO_ROOT, "tests", "fixtures", "review_signals")

SECURITY_SAMPLES = (
    "auth",
    "authn",
    "authz",
    "OAuth",
    "OAuth2",
    "authentication",
    "authorization",
    "authorize",
    "jwt",
    "csrf",
    "xss",
    "crypto",
    "cryptography",
    "encrypted",
    "decrypting",
    "secret",
    "secrets",
    "credentials",
    "passwords",
    "permissions",
    "sandboxed",
    "vulnerability",
    "injection",
    "security",
)
DATA_SAMPLES = (
    "database",
    "schema",
    "migrations",
    "sql",
    "backfill",
    "pii",
    "gdpr",
    "retention",
    "datastore",
    "data loss",
)
IRREVERSIBLE_SAMPLES = (
    "drop table",
    "truncate",
    "rm -rf",
    "force push",
    "force-push",
    "git push --force",
    "git reset --hard",
    "purge",
    "wipe",
    "destroy",
    "irreversibly",
    "rotate key",
    "delete all",
)

TRIGGERS = (
    *((sample, ["security"]) for sample in SECURITY_SAMPLES),
    *((sample, ["data"]) for sample in DATA_SAMPLES),
    *((sample, ["irreversible"]) for sample in IRREVERSIBLE_SAMPLES),
    ("drop database", ["data", "irreversible"]),
    ("SQL injection risk", ["security", "data"]),
)


def read(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as handle:
        return handle.read()


def build_plan(tasks: int, files: int) -> str:
    lines = [f"### Task {n}: Step {n}" for n in range(1, tasks + 1)]
    lines.extend(f"- Create: `src/file_{n}.py`" for n in range(files))
    return "\n".join(lines) + "\n"


class TestPlanSignals(unittest.TestCase):
    def test_fixtures_hit_exactly_their_signal(self) -> None:
        cases = (
            ("security_plan.md", ["security"]),
            ("data_plan.md", ["data"]),
            ("irreversible_plan.md", ["irreversible"]),
            ("plain_plan.md", []),
            ("auth_plan.md", ["security"]),
            ("rules_boilerplate_plan.md", []),
            ("secret_handling_plan.md", ["security"]),
        )
        for name, expected in cases:
            with self.subTest(fixture=name):
                text = read(name)
                found = review_signals.plan_signals(text, review_signals.plan_paths(text))
                self.assertEqual(found, expected)

    def test_each_trigger_expression(self) -> None:
        for sample, expected in TRIGGERS:
            with self.subTest(sample=sample):
                self.assertEqual(review_signals.plan_signals(sample, []), expected)

    def test_paths_trigger_data(self) -> None:
        self.assertEqual(review_signals.plan_signals("", ["db/migrations/0001.py"]), ["data"])
        self.assertEqual(review_signals.plan_signals("", ["reports/q1.SQL"]), ["data"])
        self.assertEqual(review_signals.plan_signals("", ["src/docs/outline.py"]), [])

    def test_rule_lines_and_temp_cleanup_are_not_irreversible(self) -> None:
        samples = (
            "- Never delete outside `tmp/`, and never use `rm -rf` on a variable path.",
            "Never `git reset --hard` without the owner.",
            "Do not force push.",
            "No `rm -rf` on a variable path.",
            "trap 'rm -rf \"$WORK\"' EXIT",
            'rm -rf "$TMPDIR/run"',
            "rm -rf tmp/p40-scratch",
            'rm -rf "$(mktemp -d)"',
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertEqual(review_signals.plan_signals(sample, []), [])

    def test_irreversible_work_beside_a_rule_still_triggers(self) -> None:
        samples = (
            "rm -rf templates/",
            "Without a backup, drop table users.",
            "This step does not roll back: purge the queue.",
            "rm -rf tmp/scratch && git push --force",
            "rm -rf build/",
            "Run `rm -rf dist` before the release.",
            "Never use `rm -rf` on a variable path.\nRun `git reset --hard` on the clone.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertEqual(review_signals.plan_signals(sample, []), ["irreversible"])

    def test_rule_lines_are_not_security(self) -> None:
        samples = (
            "- English only. Never print or write a secret, never print a process environment.",
            "Never print secrets or email addresses.",
            "Do not copy real credentials into a test.",
            "You must not change file permissions here.",
            "No secrets, no machine paths in the fixtures.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertEqual(review_signals.plan_signals(sample, []), [])

    def test_security_work_beside_a_rule_still_triggers(self) -> None:
        samples = (
            "Never print secrets.\nStore the credentials file with permissions 0600.",
            "Add OAuth login; never log the access token.",
            "Check the user's permission before the delete.",
            "Without a password the request is refused.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertEqual(review_signals.plan_signals(sample, []), ["security"])

    def test_common_words_never_trigger(self) -> None:
        words = (
            "table",
            "index",
            "session",
            "token",
            "release",
            "publish",
            "author",
            "authority",
            "authored",
        )
        for word in words:
            with self.subTest(word=word):
                self.assertEqual(review_signals.plan_signals(word, []), [])


class TestPlanFacts(unittest.TestCase):
    def test_superpowers_plan_counts(self) -> None:
        self.assertEqual(
            review_signals.plan_facts(read("security_plan.md")),
            {"tasks": 2, "files": 3, "steps": 3, "complexity": "small"},
        )

    def test_gsd_tags_count(self) -> None:
        text = (
            '<task type="auto">\n<files>a.py, b.py</files>\n</task>\n'
            '<task type="auto">\n<files>b.py, c.py</files>\n</task>\n'
        )
        facts = review_signals.plan_facts(text)
        self.assertEqual(facts["tasks"], 2)
        self.assertEqual(facts["files"], 3)

    def test_complexity_edges(self) -> None:
        cases = (
            (2, 3, "small"),
            (2, 4, "medium"),
            (6, 0, "large"),
            (1, 10, "large"),
        )
        for tasks, files, expected in cases:
            with self.subTest(tasks=tasks, files=files):
                facts = review_signals.plan_facts(build_plan(tasks, files))
                self.assertEqual(facts["complexity"], expected)


if __name__ == "__main__":
    unittest.main()
