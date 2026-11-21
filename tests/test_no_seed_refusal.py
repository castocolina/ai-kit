"""36 SPEC R7: no refusal path reads a runtime-table seed flag, and every refusal names a fact.
This module scans Python sources; plan 36-28 adds the Markdown scan."""

import os
import re
import sys
import unittest
from pathlib import Path

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import detection, routing
from ai_kit_spec.config_io import validate_reviewer_fields
from ai_kit_spec.execute_selection import screen_execute_clis

REPO = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = ("skills", "tools")
OLD_FLAG_RX = re.compile(r"\breview_only\b")


def python_sources(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for base in SOURCE_ROOTS
                  for path in (root / base).rglob("*.py")
                  if not {"__pycache__", "node_modules"}.intersection(path.parts))


def flag_lines(text: str) -> list[int]:
    return [n for n, line in enumerate(text.splitlines(), 1) if OLD_FLAG_RX.search(line)]


class TestNoSeedFlagReader(unittest.TestCase):
    def test_no_python_source_names_the_old_flag(self):
        sources = python_sources(REPO)
        self.assertIn("skills/ai-kit-spec-review/ai_kit_spec/routing.py", sources)
        self.assertEqual([], [f"{path}:{n}" for path in sources
                              for n in flag_lines((REPO / path).read_text(
                                  encoding="utf-8", errors="replace"))])

    def test_scan_catches_a_planted_reader(self):
        self.assertEqual(flag_lines("x = 1\nif row.review_only:\n"), [2])
        self.assertEqual(flag_lines('SKIP = {"review_only"}\n'), [1])
        self.assertEqual(flag_lines("claude is review-only\nreview_only_x = 1\n"), [])

    def test_routes_and_table_drop_the_old_flag(self):
        self.assertIn("no_formula", routing.SKIP_ROUTES)
        self.assertNotIn("review_only", routing.SKIP_ROUTES)
        self.assertNotIn("review_only", detection.Runtime._fields)


class TestClaudeExecuteLane(unittest.TestCase):
    def test_accepted_by_config_and_selection_then_routed_no_formula(self):
        lane = {"key": "c1", "runtime": "claude", "model": "placeholder-model-1",
                "purpose": "execute"}
        self.assertIsNone(validate_reviewer_fields(dict(lane)))
        self.assertEqual(screen_execute_clis([dict(lane)], warn_fn=self.fail), [lane])
        request = routing.RouteInput("claude", "placeholder-model-1")
        inventory = routing.Inventory(frozenset({"claude"}),
                                      {"claude": ("placeholder-model-1",)})
        for _ in range(2):
            self.assertEqual(routing.route(request, "codex", "exec", inventory), "no_formula")
        self.assertEqual(routing.skip_note("c1 for execution", "no_formula", "claude"),
                         "ai-kit-spec: skipping c1 for execution: route no_formula: "
                         "the runner has no exec formula for claude "
                         "(cross-ai.mjs RUNTIMES.claude.exec is null, read 2026-11-20)")


class TestOutOfTableRuntime(unittest.TestCase):
    def test_save_error_names_the_custom_lane(self):
        for key, runtime in (("p1", "placeholder-cli-1"), ("c2", "Claude")):
            with self.subTest(runtime=runtime):
                self.assertEqual(validate_reviewer_fields(
                    {"key": key, "runtime": runtime, "model": "placeholder-model-1"}),
                    f"{key}: runtime {runtime!r} is not in the runtime table; "
                    "store a custom `command` lane instead (no 'runtime')")

    def test_custom_command_lane_is_accepted(self):
        self.assertIsNone(validate_reviewer_fields(
            {"key": "p1", "command": "placeholder-cli-1 -p {prompt} -m {model}",
             "model": "placeholder-model-1"}))


if __name__ == "__main__":
    unittest.main()
