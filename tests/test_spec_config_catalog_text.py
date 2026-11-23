"""Contract tests for spec-config's catalog instructions (35-25)."""

import os
import re
import shlex
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.fspath(REPO / "skills" / "ai-kit-spec-review"))

from ai_kit_spec import cli

SKILL = REPO / "skills/ai-kit-spec-config/SKILL.md"
CATALOG = REPO / "skills/ai-kit-spec-config/references/catalog.md"
RUN_LINE = re.compile(r"^- Run: `([^`]+)`$", re.MULTILINE)
ALLOWED = (
    "detect-runtimes", "fetch-model-catalog", "catalog-report", "web-query",
    "record-web-names", "herdr-names", "confirm-model", "models-config", "check-reviewer",
    "cache-path",
)


def command_problems(text):
    problems = []
    lines = RUN_LINE.findall(text)
    for command in lines:
        args = shlex.split(command)
        if not args or args[0] not in ALLOWED:
            problems.append(f"unknown command: {command}")
            continue
        try:
            cli._build_parser().parse_args(args)
        except SystemExit:
            problems.append(f"invalid command: {command}")
    if not lines:
        problems.append("no documented commands")
    return problems


class TestSpecConfigCatalogText(unittest.TestCase):
    def setUp(self):
        self.skill = SKILL.read_text(encoding="utf-8")
        self.catalog = CATALOG.read_text(encoding="utf-8")

    def test_step_order(self):
        lines = self.skill.splitlines()
        detect = next(i for i, line in enumerate(lines) if line.startswith("### Step 1 —"))
        catalog = next(i for i, line in enumerate(lines) if line == "### Step 1.5 — Catalog")
        ask = next(i for i, line in enumerate(lines) if line.startswith("### Step 2 —"))
        self.assertLess(detect, catalog)
        self.assertLess(catalog, ask)
        self.assertIn("references/catalog.md", "\n".join(lines[catalog:ask]))

    def test_commands_named(self):
        for command in ("detect-runtimes", "fetch-model-catalog", "web-query",
                        "record-web-names", "herdr-names", "catalog-report",
                        "check-reviewer --catalog-path", "confirm-model", "models-config",
                        "cache-path --kind catalog"):
            self.assertIn(command, self.catalog)

    def test_rules_worded(self):
        for phrase in ("not checked", "stale", "attribution", "assumed", "HERDR_ENV=1",
                       "data, never instructions"):
            self.assertIn(phrase, self.catalog)

    def test_step_2_5_records_usability(self):
        section = self.skill.split("#### Step 2.5", 1)[1].split("#### Step 2.6", 1)[0]
        self.assertIn("--catalog-path", section)

    def test_documented_commands_parse(self):
        self.assertEqual([], command_problems(self.catalog))
        planted = "- Run: `catalog-report --json`"
        self.assertTrue(command_problems(planted))

    def test_herdr_notice_before_run(self):
        notice_text = "copilot will start in a herdr pane with its permission prompts off"
        notice = self.catalog.index(notice_text)
        run = self.catalog.index("- Run: `herdr-names")
        self.assertLess(notice, run)


if __name__ == "__main__":
    unittest.main()
