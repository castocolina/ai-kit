"""37-14: the runner preview replaces the Python effort composers (D-01, SPEC R3)."""

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import cli
from ai_kit_spec.runner_dispatch import (
    PREVIEW_TIMEOUT_S,
    RunnerSeams,
    RunnerSpec,
    preview_model_id,
    preview_setting,
    print_argv_lines,
    runner_flags,
)

REPO = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = ("skills", "tools")
# D-01: the runner owns every effort form; these are the Python composers it replaced.
COMPOSER_PATTERNS = (re.compile(r"\[[^\]\n]*effort=\{"),
                     re.compile(r"\}[:#]\{effort\}"), re.compile(r'f"effort=\{'))


def composer_lines(text) -> list[int]:
    return [n for n, line in enumerate(text.splitlines(), 1)
            if any(pattern.search(line) for pattern in COMPOSER_PATTERNS)]


def composer_hits(root) -> list[str]:
    paths = sorted(path for base in SOURCE_ROOTS for path in (root / base).rglob("*.py")
                   if not {"__pycache__", "node_modules"}.intersection(path.parts))
    return [f"{path.relative_to(root).as_posix()}:{n}" for path in paths
            for n in composer_lines(path.read_text(encoding="utf-8", errors="replace"))]


class TestNoPythonEffortComposer(unittest.TestCase):
    def test_no_module_composes_an_effort_into_a_model_id(self):
        self.assertEqual(composer_hits(REPO), [])

    def test_the_scan_catches_a_planted_composer(self):
        self.assertEqual(composer_lines('return f"{model}[{prefix}effort={effort}]"\nx = 1\n'), [1])
        self.assertEqual(composer_lines('f"{model}:{effort}"\nf"{model}#{effort}"\n'
                                        'overrides.append(f"effort={effort}")\n'), [1, 2, 3])
        self.assertEqual(composer_lines('return f"model={model}, effort={effort_display}"\n'), [])


class TestPreviewReaders(unittest.TestCase):
    def test_model_id_line(self):
        self.assertEqual(preview_model_id(["x",
                                           "cross-ai: model-id placeholder-model-1[effort=high]",
                                           "cross-ai: model-id other"]),
                         "placeholder-model-1[effort=high]")
        self.assertIsNone(preview_model_id([]))

    def test_setting_line(self):
        self.assertEqual(preview_setting(["cross-ai: setting effort=high applied"], "effort"),
                         ("applied", None))
        self.assertEqual(preview_setting(
            ["cross-ai: setting effort=high ignored reason=no_form"], "effort"),
            ("ignored", "no_form"))
        self.assertIsNone(preview_setting(
            ["cross-ai: setting provider=- unknown reason=no_provider_form"], "effort"))
        self.assertIsNone(preview_setting(["cross-ai: setting effortx=high applied"], "effort"))

    def test_print_argv_lines_seams(self):
        spec = RunnerSpec("cursor", "placeholder-model-1", "review", 30, cwd=".")
        seams = RunnerSeams(which_fn=lambda _: "node", runner_path_fn=lambda: "template",
                            env_fn=lambda: {"HOME": "fake-home"})
        run = Mock(return_value=subprocess.CompletedProcess(
            [], 0, "a\n", "b\ncross-ai: model-id m\n"))
        self.assertEqual(print_argv_lines(spec, seams, run), ["a", "b", "cross-ai: model-id m"])
        run.assert_called_once_with(["node", "template", *runner_flags(spec), "--print-argv"],
                                    stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                    timeout=PREVIEW_TIMEOUT_S, cwd=".", env={"HOME": "fake-home"},
                                    check=False)
        for missing in (seams._replace(which_fn=lambda _: None),
                        seams._replace(runner_path_fn=lambda: None)):
            run.reset_mock()
            self.assertIsNone(print_argv_lines(spec, missing, run))
            run.assert_not_called()
        for error in (OSError(), subprocess.TimeoutExpired("node", 30)):
            self.assertIsNone(print_argv_lines(spec, seams, Mock(side_effect=error)))
        for code in (1, 2):
            for output in ("", "cross-ai: setting effort=high applied\ncross-ai: model-id m\n"):
                run = Mock(return_value=subprocess.CompletedProcess([], code, output, ""))
                self.assertIsNone(print_argv_lines(spec, seams, run))


class TestBuildModelIdReadsTheRunner(unittest.TestCase):
    def invoke(self, args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["build-model-id", *args])
        return code, out.getvalue(), err.getvalue()

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_cursor_bracket_from_the_runner(self):
        with tempfile.TemporaryDirectory() as home, patch.dict(os.environ, {
            "HOME": home, "AI_KIT_REFUSE_REAL_HOME": "1"
        }):
            code, out, _ = self.invoke(["--runtime", "cursor", "--base-model",
                                        "placeholder-model-1", "--effort", "high", "--context",
                                        "1m", "--fast", "true"])
            self.assertEqual(code, 0)
            self.assertTrue(out.startswith("placeholder-model-1[fast=true,"))
            self.assertEqual(len(out.splitlines()), 1)
            self.assertIn("effort=high", out)
            self.assertIn("context=1m", out)
            self.assertEqual(out.count("["), 1)
            self.assertEqual(out.count("]"), 1)
            code, out, _ = self.invoke(["--runtime", "cursor", "--base-model",
                                        "placeholder-model-1"])
            self.assertEqual((code, out), (0, "placeholder-model-1\n"))

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_codex_effort_is_a_flag(self):
        with tempfile.TemporaryDirectory() as home, patch.dict(os.environ, {
            "HOME": home, "AI_KIT_REFUSE_REAL_HOME": "1"
        }):
            code, out, err = self.invoke(["--runtime", "codex", "--base-model",
                                          "placeholder-model-1", "--effort", "high"])
        self.assertEqual((code, out), (0, "placeholder-model-1\n"))
        self.assertIn("build-model-id: cross-ai: setting effort=high applied", err)

    def test_preview_failures_are_named(self):
        cases = ((None, "the runner preview did not run (node or the runner template is missing)"),
                 (["cross-ai: setting model=x applied"], "the runner printed no model-id line"))
        for lines, message in cases:
            with patch("ai_kit_spec.cli.print_argv_lines", return_value=lines):
                code, out, err = self.invoke(["--runtime", "cursor", "--base-model",
                                              "placeholder-model-1"])
            self.assertEqual((code, out), (1, ""))
            self.assertIn(f"build-model-id: {message}", err)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_fast_is_cursor_only(self):
        with tempfile.TemporaryDirectory() as home, patch.dict(os.environ, {
            "HOME": home, "AI_KIT_REFUSE_REAL_HOME": "1"
        }):
            code, out, err = self.invoke(["--runtime", "codex", "--base-model",
                                          "placeholder-model-1", "--fast", "true"])
        self.assertEqual((code, out), (0, "placeholder-model-1\n"))
        self.assertIn("build-model-id: --fast applies to cursor only; ignored", err)


if __name__ == "__main__":
    unittest.main()
