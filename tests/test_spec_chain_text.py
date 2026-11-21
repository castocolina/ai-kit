"""Doc-contract tests for the no-config chain (36 SPEC R2).

Pin the shared block in the review skill and adapter, and a config-status fixture.
"""

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import cli

REPO = Path(_REPO_ROOT).resolve()
TOOLS_PY = REPO / "skills/ai-kit-spec-review/ai-kit-spec.py"
REVIEW_SKILL = REPO / "skills/ai-kit-spec-review/SKILL.md"
DISPATCH_REF = REPO / "skills/ai-kit-spec-review/references/cross-ai-dispatch.md"
CLAUDE_PROFILE = REPO / "skills/ai-kit-spec-review/references/cli-profiles/claude.md"
BLOCK_LINES = (
    '**No-config check** (skipped with `--no-cross-ai`). Run `python3 '
    '"$TOOLS_PY" config-status --role review --cwd <CODEBASE_ROOT>` and read its first line.',
    '1. `active`: continue and ask nothing.',
    '2. `pending`: continue; the trust and migration steps handle it, never setup.',
    "3. `none`: ask once, with the host's question tool or numbered plain text, "
    'and never answer for the user:',
    '   (1) run ai-kit-spec-config now, (2) run once on the session model, (3) '
    'stop. An empty or unrecognised answer is (3).',
    '   (1): follow the sibling ai-kit-spec-config skill to its end, run '
    'config-status again (it must print `active`), then continue the task.',
    '   (2): continue on the session default and put the line `no cross-AI '
    'config: ran on the session model` in the surface message.',
    '   (3): stop.',
    '4. `none` and the host has no way to ask: print `no cross-AI config: run '
    'ai-kit-spec-config; continuing on the session model, no config written`,',
    '   continue on the session default and repeat that line in the surface message.',
    '5. `none`, the answer is (1) and no ../ai-kit-spec-config/SKILL.md exists '
    'beside this skill: stop with',
    '   `ai-kit-spec-config is not installed. Install ai-kit, then run ai-kit-spec-config.`',
    '6. Exit code 2: show the named error line and stop; any other nonzero '
    'exit: show the first stderr line and stop.',
)
TOOLS_PY_NOTICE = (
    "ai-kit-spec-review: ai-kit-spec.py is missing; install ai-kit. "
    "Continuing on the session model, nothing checked."
)
BLOCK = "\n".join(BLOCK_LINES)
POINT_SIX = BLOCK_LINES[-1]
ACTIVE_LANE = ('[[lanes.review]]\nkey = "fake-review"\nruntime = "opencode"\n'
               'model = "fake/placeholder-model-1"\n')


def has_block(text: str, block: str) -> bool:
    return block in text


def _read(path) -> str:
    return path.read_text(encoding="utf-8")


def _config_status(project: str, home: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": home, "XDG_CONFIG_HOME": os.path.join(home, ".config"),
           "XDG_CACHE_HOME": os.path.join(home, ".cache"), "AI_KIT_REFUSE_REAL_HOME": "1"}
    return subprocess.run([sys.executable, str(TOOLS_PY), "config-status", "--role", "review",
                           "--cwd", project], env=env, capture_output=True, text=True,
                          timeout=60, check=False)


class TestReviewChainBlock(unittest.TestCase):
    def test_block_has_thirteen_ascii_lines(self):
        self.assertEqual(len(BLOCK_LINES), 13)
        self.assertTrue(BLOCK.isascii())

    def test_block_sits_in_step_0_7(self):
        text = _read(REVIEW_SKILL)
        section = text[text.index("## Step 0.7"):text.index("## Constants")]
        self.assertTrue(has_block(section, BLOCK))

    def test_block_command_parses(self):
        args = cli._build_parser().parse_args(
            ["config-status", "--role", "review", "--cwd", "/tmp/x"])
        self.assertEqual((args.role, args.cwd), ("review", "/tmp/x"))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli._build_parser().parse_args(["config-statuz", "--cwd", "/tmp/x"])

    def test_block_check_catches_a_missing_point(self):
        text = _read(REVIEW_SKILL)
        self.assertTrue(has_block(text, BLOCK))
        self.assertFalse(has_block(text.replace(POINT_SIX, ""), BLOCK))


class TestConfigStatusFixture(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="spec-chain-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.home = os.path.join(self.root, "home")
        self.project = os.path.join(self.root, "project")
        os.makedirs(self.home)
        os.makedirs(self.project)

    def write_config(self, text):
        directory = Path(self.project) / ".aikit"
        directory.mkdir()
        (directory / "config.toml").write_text(text, encoding="utf-8")

    def test_no_config_reaches_the_chain(self):
        result = _config_status(self.project, self.home)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines()[0], "none")

    def test_active_roster_never_reaches_the_chain(self):
        self.write_config(ACTIVE_LANE)
        result = _config_status(self.project, self.home)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines()[0], "active")

    def test_malformed_config_is_point_six(self):
        self.write_config("[lanes\n")
        result = _config_status(self.project, self.home)
        self.assertEqual(result.returncode, 2)
        self.assertIn("ai-kit-spec: config error:", result.stderr)

    def test_execute_only_roster_still_reaches_the_chain(self):
        self.write_config('[[lanes.execute]]\nkey = "fake-execute"\n'
                          'runtime = "opencode"\nmodel = "fake/placeholder-model-2"\n')
        result = _config_status(self.project, self.home)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines()[0], "none")


class TestDispatchPointThree(unittest.TestCase):
    def test_point_three_checks_config_before_the_refresh(self):
        text = _read(DISPATCH_REF)
        positions = [text.index(marker) for marker in (
            "2. **If `--no-cross-ai` was requested",
            "3. **No-config check, then the snapshot refresh.**",
            'detect-runtimes --if-stale "$RUNTIMES_JSON"',
            "4. Refresh quota",
        )]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("points 3–5 below are entirely skipped", text)

    def test_old_snapshot_hint_is_gone(self):
        text = _read(DISPATCH_REF)
        self.assertNotIn("no-runtimes-snapshot-yet", text)
        self.assertNotIn("No cross-AI config saved yet", text)

    def test_session_default_answers_reuse_point_two(self):
        self.assertIn("set `REVIEWER_LIST` exactly as point 2 does", _read(DISPATCH_REF))

    def test_missing_tools_py_is_not_a_missing_wizard(self):
        self.assertIn("a missing `ai-kit-spec-config` skill is a different fact",
                      " ".join(_read(DISPATCH_REF).split()))

    def test_missing_tools_py_prints_a_notice(self):
        text = _read(DISPATCH_REF)
        point = text[text.index("2. **If `--no-cross-ai` was requested"):
                     text.index("3. **No-config check")]
        self.assertIn(TOOLS_PY_NOTICE, point)
        self.assertIn("never for `--no-cross-ai`, which prints nothing", point)


class TestReviewNoFormulaWording(unittest.TestCase):
    def test_review_texts_name_no_formula_not_the_seed_flag(self):
        for path in (REVIEW_SKILL, DISPATCH_REF, CLAUDE_PROFILE):
            with self.subTest(path=path):
                text = _read(path)
                self.assertIn("no_formula", text)
                self.assertNotIn("review_only", text)

    def test_probe_quota_sentence_names_the_review_order(self):
        text = _read(REVIEW_SKILL)
        self.assertIn("`probe-quota` probes each lane of the review order in order", text)
        self.assertNotIn("probes each ladder entry", text)


if __name__ == "__main__":
    unittest.main()
