"""Drift gate for the compiled error catalog."""

import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_spec import cross_ai_catalog

from tests.cross_ai_selftest import _real_node_executable, run_group, runner_env

FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fixtures", "cross_ai_errors",
)
ALLOWED_CLIS = ("claude", "codex", "copilot", "cursor", "opencode", "pi")
CAPTURED = (
    "claude-bad-model.json", "codex-bad-model.json", "copilot-bad-model.json",
    "cursor-bad-model.json", "opencode-bad-model.json", "pi-bad-model.json",
)


def _classify_entry(fixture, stem):
    entry = {
        "name": stem, "cli": fixture["cli"], "stderr": fixture["stderr"],
        "stdout": fixture["stdout"],
    }
    if "route" in fixture:
        entry["route"] = fixture["route"]
    return entry


def _template_text():
    with open(cross_ai_catalog.TEMPLATE_PATH, encoding="utf-8") as handle:
        return handle.read()


class CrossAiCatalogTest(unittest.TestCase):
    def test_rendered_block_matches_template(self):
        rows = cross_ai_catalog.load_rows(cross_ai_catalog.CATALOG_PATH)
        rendered = cross_ai_catalog.splice(
            _template_text(), cross_ai_catalog.render_block(rows),
        )
        self.assertEqual(rendered, _template_text())

    def test_changed_evidence_changes_the_block(self):
        rows = cross_ai_catalog.load_rows(cross_ai_catalog.CATALOG_PATH)
        changed = [dict(row) for row in rows]
        changed[0]["evidence"] = changed[0]["evidence"] + " (changed)"
        original = _template_text()
        spliced = cross_ai_catalog.splice(original, cross_ai_catalog.render_block(changed))
        self.assertNotEqual(spliced, original)

    def test_check_cli_reports_ok(self):
        env = dict(os.environ, PYTHONPATH=os.path.join(
            os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review",
        ))
        proc = subprocess.run(
            [sys.executable, "-m", "ai_kit_spec.cross_ai_catalog", "--check"],
            capture_output=True, text=True, env=env, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("catalog ok ", proc.stdout)

    def test_write_keeps_the_template_mode_and_leaves_no_temp_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "cross-ai.mjs")
            with open(target, "w", encoding="utf-8") as handle:
                handle.write("old")
            os.chmod(target, 0o755)
            with mock.patch.object(cross_ai_catalog, "TEMPLATE_PATH", target):
                cross_ai_catalog._write_template("new \u00e9")
            with open(target, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "new \u00e9")
            self.assertEqual(os.stat(target).st_mode & 0o777, 0o755)
            self.assertEqual(os.listdir(tmp), ["cross-ai.mjs"])


class CrossAiErrorFixturesTest(unittest.TestCase):
    def test_fixture_evidence_links(self):
        rows = cross_ai_catalog.load_rows(cross_ai_catalog.CATALOG_PATH)
        by_id = {row["id"]: row for row in rows}
        for row in rows:
            match = re.search(r"tests/fixtures/cross_ai_errors/([a-z0-9-]+\.json)", row["evidence"])
            if not match:
                continue
            path = os.path.join(FIXTURE_DIR, match.group(1))
            self.assertTrue(os.path.isfile(path), row["id"])
            with open(path, encoding="utf-8") as handle:
                fixture = json.load(handle)
            self.assertEqual(fixture["expect_rule"], row["id"], row["id"])
            self.assertEqual(row["label"], "verified", row["id"])
            for transient in ("text-cooling-down", "code-5xx"):
                self.assertLess(row["tier"], by_id[transient]["tier"], row["id"])
        for name in CAPTURED:
            path = os.path.join(FIXTURE_DIR, name)
            self.assertTrue(os.path.isfile(path), name)
            with open(path, encoding="utf-8") as handle:
                fixture = json.load(handle)
            row = by_id[fixture["expect_rule"]]
            if row["cli"] != "*":
                self.assertIn(name, row["evidence"], row["id"])

    def test_fixtures_classify(self):
        node = _real_node_executable()
        if node is None:
            self.skipTest("real node not found")
        fixtures = []
        for path in sorted(glob.glob(os.path.join(FIXTURE_DIR, "*.json"))):
            with open(path, encoding="utf-8") as handle:
                fixtures.append((os.path.splitext(os.path.basename(path))[0], json.load(handle)))
        self.assertTrue(fixtures, FIXTURE_DIR)
        with tempfile.TemporaryDirectory() as tmp:
            input_path = os.path.join(tmp, "fixtures.json")
            with open(input_path, "w", encoding="utf-8") as handle:
                json.dump([_classify_entry(fixture, stem) for stem, fixture in fixtures], handle)
            proc = run_group(
                [node, cross_ai_catalog.TEMPLATE_PATH, "--classify-only", input_path],
                60, cwd=tmp, env=runner_env(tmp),
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        results = {result["name"]: result for result in map(json.loads, proc.stdout.splitlines())}
        for stem, fixture in fixtures:
            result = results[stem]
            message = f"{fixture['host']}: {result}"
            self.assertEqual(result["status"], fixture["expect_class"], message)
            self.assertEqual(result["rule"], fixture["expect_rule"], message)

    def test_fixture_headers(self):
        paths = sorted(glob.glob(os.path.join(FIXTURE_DIR, "*.json")))
        self.assertTrue(paths, FIXTURE_DIR)
        keys = {
            "host", "version", "date", "cli", "stderr", "stdout",
            "expect_class", "expect_rule", "source",
        }
        for path in paths:
            with self.subTest(path=path):
                with open(path, encoding="utf-8", newline="") as handle:
                    text = handle.read()
                fixture = json.loads(text)
                self.assertIn(set(fixture), (keys, keys | {"route"}), path)
                if "route" in fixture:
                    self.assertIn(fixture["route"], ("router", "unknown"), path)
                for key in ("host", "version"):
                    self.assertIsInstance(fixture[key], str, path)
                    self.assertTrue(fixture[key], path)
                self.assertIn(fixture["cli"], ALLOWED_CLIS, path)
                self.assertIn(fixture["source"], ("captured", "reconstructed"), path)
                self.assertRegex(fixture["date"], r"^\d{4}-\d{2}-\d{2}$", path)
                self.assertTrue(text.endswith("\n"), path)
                for key in ("stderr", "stdout"):
                    self.assertIsInstance(fixture[key], str, path)
                    self.assertIsNone(
                        re.search(r"[\x00-\x09\x0b-\x1f\x7f-\x9f]", fixture[key]), path,
                    )
                for forbidden in ("/home/", "/var/", "/Users/", "@", "sk-", "Bearer"):
                    self.assertNotIn(forbidden, text, path)


if __name__ == "__main__":
    unittest.main()
