"""37-14: the runner preview replaces the Python effort composers (D-01, SPEC R3)."""

import hashlib
import io
import json
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
from ai_kit_spec.capability_block import (
    BAD_LINE_REASON,
    NO_LINE_REASON,
    NO_PREVIEW_REASON,
    context_form_applied,
    lane_facts,
)
from ai_kit_spec.runner_dispatch import (
    PREVIEW_TIMEOUT_S,
    RunnerSeams,
    RunnerSpec,
    child_env,
    preview_model_id,
    preview_setting,
    print_argv_lines,
    runner_flags,
)

from tests.cross_ai_selftest import _real_node_executable

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


def lab(source, state="verified"):
    return {"state": state, "source": source}


CAPS = {
    "write": {"value": "none", "label": lab("from argv --tools")},
    "shell": {"value": "no", "label": lab("from argv --tools")},
    "skills": {"value": "none", "label": lab("from argv --no-skills")},
    "mcp": {"value": "none", "label": lab("from argv --no-mcp")},
    "prompt": {"channel": "stdin", "max_bytes": None},
}


def caps_line(obj):
    return "cross-ai: capabilities " + json.dumps(obj)


class TestLaneFacts(unittest.TestCase):
    def test_no_preview_is_all_unknown(self):
        facts = lane_facts(None)
        self.assertEqual(facts.reason, NO_PREVIEW_REASON)
        fields = [facts.write, facts.shell, facts.skills, facts.mcp]
        for field in fields:
            self.assertEqual(field, {"value": "unknown", "label": {
                "state": "unknown", "source": NO_PREVIEW_REASON}})
        self.assertEqual(len({id(field) for field in fields}), 4)
        self.assertEqual(facts.prompt, {"channel": "unknown", "max_bytes": None})
        self.assertEqual((facts.skill_settings, facts.mcp_settings, facts.skill_blocks,
                          facts.settings), ((), (), (), ()))

    def test_missing_line_is_all_unknown(self):
        facts = lane_facts(["pi\tpi\t[]", "cross-ai: setting skill=lens-a applied form=path"])
        self.assertEqual(facts.reason, NO_LINE_REASON)
        self.assertEqual(facts.write["value"], "unknown")
        self.assertEqual(facts.skill_settings, ({"name": "lens-a", "state": "applied",
                                                "reason": None, "form": "path"},))

    def test_malformed_line_is_all_unknown(self):
        cases = [
            "cross-ai: capabilities {", "cross-ai: capabilities []",
            caps_line({**CAPS, "write": {"value": "maybe", "label": "x"}}),
            caps_line({k: v for k, v in CAPS.items() if k != "mcp"}),
            caps_line({**CAPS, "shell": {"value": "no"}}),
            caps_line({**CAPS, "shell": {"value": "no", "label": "from argv"}}),
            caps_line({**CAPS, "shell": {"value": "no", "label": {"state": "verified"}}}),
            [caps_line(CAPS), caps_line(CAPS)],
            caps_line({**CAPS, "prompt": {"channel": "pipe", "max_bytes": None}}),
            caps_line({**CAPS, "prompt": {"channel": "argv", "max_bytes": -1}}),
            caps_line({**CAPS, "prompt": {"channel": "argv", "max_bytes": True}}),
            caps_line({**CAPS, "prompt": {"channel": "argv", "max_bytes": None}}),
            caps_line({**CAPS, "prompt": {"channel": "stdin", "max_bytes": 100}}),
            caps_line({**CAPS, "shell": {"value": "no", "label": lab("from argv", "probably")}}),
            caps_line({**CAPS, "shell": {"value": "no", "label": lab("")}}),
        ]
        for case in cases:
            with self.subTest(case=case):
                facts = lane_facts(case if isinstance(case, list) else [case])
                self.assertEqual(facts.reason, BAD_LINE_REASON)
                for field in (facts.write, facts.shell, facts.skills, facts.mcp):
                    self.assertEqual(field["value"], "unknown")

    def test_well_formed_line(self):
        facts = lane_facts([caps_line({**CAPS,
            "shell": {"value": "no", "label": {**lab("from argv --tools"), "extra": 1}},
            "prompt": {"channel": "argv", "max_bytes": 102000}, "extra": 1})])
        self.assertIsNone(facts.reason)
        self.assertEqual(facts.shell, {"value": "no", "label": lab("from argv --tools")})
        self.assertEqual(facts.prompt, {"channel": "argv", "max_bytes": 102000})

    def test_setting_and_block_lines(self):
        lines = [
            "cross-ai: setting model=placeholder-model-1 applied",
            "cross-ai: setting effort=high ignored reason=no_form",
            "cross-ai: setting context=1m applied",
            "cross-ai: setting skill=lens-a applied form=prose",
            "cross-ai: setting skill=lens-b ignored reason=no_form",
            "cross-ai: setting mcp=fake-server ignored reason=mode_forbids",
            "cross-ai: skill-block lens-a bytes=120 sha256=" + "a" * 64,
            "cross-ai: skill-block lens-a bytes=12x sha256=" + "a" * 64,
            "cross-ai: setting skill=other-a applied form=bogus",
            "cross-ai: setting skill=ui-a applied form=path trailing", caps_line(CAPS),
        ]
        facts = lane_facts(lines)
        self.assertEqual(facts.settings, ({"name": "model", "value": "placeholder-model-1"},
                                          {"name": "context", "value": "1m"}))
        self.assertEqual(facts.context_setting, {"value": "1m", "state": "applied", "reason": None})
        self.assertTrue(context_form_applied(facts))
        for reason, expected in (("id_carries", True), ("no_form", False)):
            with self.subTest(reason=reason):
                self.assertEqual(context_form_applied(lane_facts([
                    f"cross-ai: setting context=1m ignored reason={reason}"])), expected)
        self.assertFalse(context_form_applied(lane_facts([])))
        self.assertEqual(facts.skill_settings, (
            {"name": "lens-a", "state": "applied", "reason": None, "form": "prose"},
            {"name": "lens-b", "state": "ignored", "reason": "no_form", "form": None}))
        self.assertEqual(facts.mcp_settings, (
            {"name": "fake-server", "state": "ignored", "reason": "mode_forbids"},))
        self.assertEqual(facts.skill_blocks, (
            {"name": "lens-a", "bytes": 120, "sha256": "a" * 64},))


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
        self.assertEqual(preview_setting(["cross-ai: setting skill=lens-a applied form=path"],
                                         "skill"), ("applied", None))
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


class TestLaneFactsFromTheRunner(unittest.TestCase):
    def setUp(self):
        self.node = _real_node_executable()
        self.assertIsNotNone(self.node, "no real node executable on PATH")

    def _run(self, tmp, spec):
        node = self.node
        assert node is not None
        env = child_env()
        env.update(HOME=tmp, XDG_STATE_HOME=os.path.join(tmp, "state"),
                   AI_KIT_REFUSE_REAL_HOME="1")
        env.pop("HERDR_ENV", None)
        return lane_facts(print_argv_lines(
            spec, RunnerSeams(which_fn=lambda _: node, env_fn=lambda: env)))

    def _skill(self, tmp):
        directory = os.path.join(tmp, "skills", "lens-a")
        os.makedirs(directory)
        content = b"---\nname: lens-a\n---\nLens body.\n"
        with open(os.path.join(directory, "SKILL.md"), "wb") as skill:
            skill.write(content)
        return directory, content

    def test_pi_path_form_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, _ = self._skill(tmp)
            spec = RunnerSpec("pi", "fake/placeholder-model-1", "review", 30, cwd=tmp,
                              skill_names=("lens-a",), skill_paths=(directory,))
            facts = self._run(tmp, spec)
            self.assertIsNone(facts.reason, msg=str(facts))
            self.assertEqual(facts.skill_settings, ({"name": "lens-a", "state": "applied",
                                                     "reason": None, "form": "path"},))
            self.assertEqual(facts.skills["value"], "path")
            self.assertEqual(facts.shell["value"], "no")
            self.assertIn(facts.prompt["channel"], ("argv", "stdin"))
            self.assertEqual(facts.skill_blocks, ())

    def test_copilot_prose_and_mcp_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, content = self._skill(tmp)
            mcp = os.path.join(tmp, "mcp.json")
            with open(mcp, "w", encoding="utf-8") as output:
                json.dump({"mcpServers": {"fake-server": {"command": "fake-cmd"}}}, output)
            os.chmod(mcp, 0o600)
            spec = RunnerSpec("copilot", "placeholder-model-1", "review", 30, cwd=tmp,
                              skill_names=("lens-a",), skill_paths=(directory,), mcp_config=mcp)
            facts = self._run(tmp, spec)
            self.assertIsNone(facts.reason, msg=str(facts))
            self.assertEqual(facts.skill_settings[0]["form"], "prose")
            self.assertEqual(len(facts.skill_blocks), 1)
            self.assertEqual(facts.skill_blocks[0]["name"], "lens-a")
            self.assertEqual(facts.skill_blocks[0]["sha256"], hashlib.sha256(content).hexdigest())
            self.assertGreater(facts.skill_blocks[0]["bytes"], 0)
            self.assertEqual(facts.mcp_settings, ({"name": "fake-server", "state": "applied",
                                                   "reason": None},))
            self.assertEqual(facts.mcp["value"], "call_file")
            self.assertEqual(facts.settings[0], {"name": "model", "value": "placeholder-model-1"})


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
