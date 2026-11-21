"""36 SPEC R7 / 37 R9: no refusal path reads a runtime-table seed flag or a mirror of the
runner's formulas, and every refusal names a fact.
This module scans Python sources; plan 36-28 adds the Markdown scan."""

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import detection, routing, runner_facts
from ai_kit_spec.config_io import validate_reviewer_fields
from ai_kit_spec.execute_selection import screen_execute_clis
from ai_kit_spec.tooling_guidance import resolve_cross_ai_template_path

REPO = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = ("skills", "tools")
OLD_FLAG_RX = re.compile(r"\breview_only\b")
# 37 R9: Python reads the runner's --describe fact; no Python copy of its formulas or execute set.
MIRROR_RX = re.compile(
    r"\b(?:exec_formula|ExecFormula|has_exec_formula|exec_formula_source|"
    r"NO_RUNNER_ENTRY|SUPPORTED_EXECUTE_CLIS)\b"
)
# 37 D-06: the runner keeps the only model id floor; Python names no per-runtime grammar.
GRAMMAR_MIRROR_RX = re.compile(
    r"\b(?:\w*MODEL_ID_SRC|model_id_ok|model_id_src|runner_model_problem|"
    r"PI_MODEL_ID|OPENCODE_MODEL_ID|CURSOR_MODEL_ID)\b"
)
_MD_SCAN_ROOT = Path(__file__).resolve().parents[1]
SEED_FLAG_TOKEN = "review_only"
MD_EXTRA = ("AGENTS.md", "README.md", "docs/config/design.md")


def python_sources(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for base in SOURCE_ROOTS
                  for path in (root / base).rglob("*.py")
                  if not {"__pycache__", "node_modules"}.intersection(path.parts))


def flag_lines(text: str) -> list[int]:
    return [n for n, line in enumerate(text.splitlines(), 1) if OLD_FLAG_RX.search(line)]


def mirror_lines(text: str) -> list[int]:
    return [n for n, line in enumerate(text.splitlines(), 1) if MIRROR_RX.search(line)]


class TestNoRunnerFormulaMirror(unittest.TestCase):
    def test_no_python_source_mirrors_a_runner_formula(self):
        self.assertEqual([], [f"{path}:{n}" for path in python_sources(REPO)
                              for n in mirror_lines((REPO / path).read_text(
                                  encoding="utf-8", errors="replace"))])

    def test_scan_catches_a_planted_mirror(self):
        self.assertEqual(mirror_lines('row.exec_formula.head\nx = 1\n'), [1])
        self.assertEqual(mirror_lines('from ai_kit_spec.commands import SUPPORTED_EXECUTE_CLIS\n'
                                      'NO_RUNNER_ENTRY = "x"\nhas_exec_formula(row)\n'), [1, 2, 3])
        self.assertEqual(mirror_lines('runner_facts.runner_has_exec(fact, rid)\n'), [])


def grammar_lines(text: str) -> list[int]:
    return [n for n, line in enumerate(text.splitlines(), 1) if GRAMMAR_MIRROR_RX.search(line)]


class TestNoGrammarMirror(unittest.TestCase):
    def test_no_python_source_names_a_runtime_grammar(self):
        self.assertEqual([], [f"{path}:{n}" for path in python_sources(REPO)
                              for n in grammar_lines((REPO / path).read_text(
                                  encoding="utf-8", errors="replace"))])

    def test_scan_catches_a_planted_grammar(self):
        self.assertEqual(grammar_lines('x = 1\nok = model_id_ok("pi", m)\n'), [2])
        self.assertEqual(grammar_lines('PI_MODEL_ID_SRC = "/x/"\nrunner_model_problem(a, b, c)\n'),
                         [1, 2])
        self.assertEqual(grammar_lines('model_id_problem(label, value)\n'), [])


def seed_flag_markdown_hits(root: Path) -> list[str]:
    paths = sorted(p for p in (root / "skills").rglob("*.md") if "__pycache__" not in p.parts)
    paths.extend(root / name for name in MD_EXTRA if (root / name).is_file())
    return [f"{path.relative_to(root).as_posix()}:{number}"
            for path in paths
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
            if SEED_FLAG_TOKEN in line]


class TestNoSeedFlagInMarkdown(unittest.TestCase):
    def test_no_markdown_names_the_seed_flag(self):
        self.assertEqual(seed_flag_markdown_hits(_MD_SCAN_ROOT), [])

    def test_markdown_scan_is_not_vacuous(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "skills" / "x"
            (skill / "references").mkdir(parents=True)
            (skill / "SKILL.md").write_text("skip route review_only here\n", encoding="utf-8")
            (skill / "references" / "a.md").write_text("a review-only note\n", encoding="utf-8")
            (root / "AGENTS.md").write_text("clean\n", encoding="utf-8")
            self.assertEqual(seed_flag_markdown_hits(root), ["skills/x/SKILL.md:1"])


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
    def test_accepted_by_config_and_selection_then_routed_by_the_fact(self):
        lane = {"key": "c1", "runtime": "claude", "model": "placeholder-model-1",
                "purpose": "execute"}
        self.assertIsNone(validate_reviewer_fields(dict(lane)))
        self.assertEqual(screen_execute_clis([dict(lane)], warn_fn=self.fail), [lane])
        request = routing.RouteInput("claude", "placeholder-model-1")
        inventory = routing.Inventory(frozenset({"claude"}),
                                      {"claude": ("placeholder-model-1",)})
        for _ in range(2):
            self.assertEqual(routing.route(request, "codex", "exec", inventory), "subprocess")
        fact = {"template_sha256": runner_facts.template_sha256(resolve_cross_ai_template_path()),
                "describe": {"runtimes": {"claude": {"formulas": {"exec": False}}}}}
        inventory = inventory._replace(runner=fact)
        for _ in range(2):
            self.assertEqual(routing.route(request, "codex", "exec", inventory), "no_formula")
        self.assertEqual(routing.skip_note("c1 for execution", "no_formula", "claude"),
                         "ai-kit-spec: skipping c1 for execution: route no_formula: "
                         "the runner has no exec formula for claude "
                         "(cross-ai.mjs --describe, recorded in the runtimes snapshot)")


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
