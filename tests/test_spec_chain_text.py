"""Doc-contract tests for the no-config chain (36 SPEC R2).

Pin the shared block in the review skill and adapter, and a config-status fixture.
"""

import contextlib
import io
import json
import os
import re
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


ADAPTER_SKILL = REPO / "skills/ai-kit-spec-execute-superpowers/SKILL.md"
CONFIG_CHECK_MD = REPO / "skills/ai-kit-spec-execute-superpowers/references/config-check.md"
ADAPTER_BLOCK_LINES = (
    '**No-config check** (a resumed run of this plan whose scalar file records '
    '`CONFIG_CHECK=` skips it; a fresh start asks again). Run block 1 below and read '
    'the `CONFIG_STATE=` line it prints.',
    *BLOCK_LINES[1:6],
    '   (2): continue on the session default and print the line `no cross-AI config: '
    'ran on the session model` now and again after the final review.',
    *BLOCK_LINES[7:9],
    '   continue on the session default and print that line again after the final review.',
    *BLOCK_LINES[10:],
)
ADAPTER_BLOCK = "\n".join(ADAPTER_BLOCK_LINES)
VARIANT_INDEXES = (0, 6, 9)


class TestAdapterChainBlock(unittest.TestCase):
    def test_adapter_block_has_thirteen_ascii_lines_without_the_flag(self):
        self.assertEqual(len(ADAPTER_BLOCK_LINES), 13)
        self.assertTrue(ADAPTER_BLOCK.isascii())
        self.assertNotIn("--no-cross-ai", ADAPTER_BLOCK)

    def test_adapter_block_shares_every_other_line(self):
        pairs = zip(BLOCK_LINES, ADAPTER_BLOCK_LINES, strict=True)
        for index, (review, adapter) in enumerate(pairs):
            with self.subTest(index=index):
                self.assertEqual(review != adapter, index in VARIANT_INDEXES)

    def test_adapter_block_in_config_check(self):
        text = _read(CONFIG_CHECK_MD)
        self.assertIn(ADAPTER_BLOCK, text)
        self.assertIn("MANDATORY", text.split("\n## ")[0])
        self.assertIn("Do NOT load", text)

    def test_step_one_points_to_config_check_before_the_start_step(self):
        text = _read(ADAPTER_SKILL)
        section = text[text.index("## Step 1:"):text.index("## Task paths")]
        self.assertLess(section.index("references/config-check.md"),
                        section.index("references/start-step.md"))
        self.assertTrue(any("MANDATORY" in line and "references/config-check.md" in line
                            for line in section.splitlines()))

    def test_adapter_skill_stays_short_and_fence_free(self):
        text = _read(ADAPTER_SKILL)
        self.assertLessEqual(len(text.splitlines()), 300)
        for block in re.findall(r"```bash\n(.*?)```", text, re.DOTALL):
            self.assertNotIn("config-status", block)


STUB_TOOLS = '''\
import json, os, sys
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
if sys.argv[1:3] == ["cache-path", "--kind"]:
    print(os.environ["STUB_QUOTA"])
    sys.exit(0)
if sys.argv[1] == "config-status":
    rc = int(os.environ.get("STUB_RC", "0"))
    if rc:
        print("ai-kit-spec: config error: /nowhere/config.toml: bad", file=sys.stderr)
        sys.exit(rc)
    print(os.environ.get("STUB_STATE", "none"))
    print("checked user /nowhere/config.toml missing")
    sys.exit(0)
sys.exit(9)
'''


class TestAdapterConfigCheckBlock(unittest.TestCase):
    def setUp(self):
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("bash not found")
        assert bash is not None
        self.bash = bash
        self.root = Path(tempfile.mkdtemp(prefix="spec-chain-adapter-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.skill = self.root / "skills/ai-kit-spec-execute-superpowers"
        self.skill.mkdir(parents=True)
        self.tools = self.root / "stub_tools.py"
        self.tools.write_text(STUB_TOOLS, encoding="utf-8")
        self.project = self.root / "project"
        self.project.mkdir()
        self.plan = self.project / "plan.md"
        self.plan.write_text("# Plan\n", encoding="utf-8")
        self.quota = self.root / "cache/quota.json"
        self.log = self.root / "stub.log"
        self.blocks = re.findall(r"```bash\n(.*?)```", _read(CONFIG_CHECK_MD), re.DOTALL)
        self.assertEqual(len(self.blocks), 3)

    def _fill(self, block, **values):
        replacements = {"<Step 0 SKILL_DIR>": str(self.skill),
                        "<Step 0 TOOLS_PY>": str(self.tools),
                        "<Step 1 CWD>": str(self.project),
                        "<Step 1 PLAN_FILE>": str(self.plan),
                        "<the SCALARS path block 1 printed>": values.get("scalars", ""),
                        "<active|pending|once|notice|chained>": values.get("outcome", "")}
        for placeholder, value in replacements.items():
            block = block.replace(placeholder, value)
        return block

    def _run(self, block, state="none", rc="0", **extra):
        env = {**os.environ, "STUB_LOG": str(self.log), "STUB_STATE": state,
               "STUB_RC": rc, "STUB_QUOTA": str(self.quota), **extra}
        return subprocess.run([self.bash, "-c", block], env=env, capture_output=True,
                              text=True, timeout=60, check=False)

    def _scalars(self, stdout):
        return Path(next(line.split("=", 1)[1] for line in stdout.splitlines()
                         if line.startswith("SCALARS=")))

    def _record_once(self):
        result = self._run(self._fill(self.blocks[0]))
        scalars = self._scalars(result.stdout)
        record = self._run(self._fill(self.blocks[1], scalars=str(scalars), outcome="once"))
        self.assertEqual(record.returncode, 0, record.stderr)
        return scalars

    def _resume(self, scalars, plan):
        key = scalars.name.removeprefix("superpowers-run-").removesuffix("-scalars.env")
        state = {"framework": "superpowers", "plan_path": str(plan), "task_index": 1}
        (self.quota.parent / f"superpowers-resume-{key}-task-1.json").write_text(
            json.dumps(state), encoding="utf-8")
        self.log.write_text("", encoding="utf-8")

    def test_none_prints_the_state_and_a_missing_wizard(self):
        result = self._run(self._fill(self.blocks[0]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CONFIG_STATE=none", result.stdout)
        self.assertIn("SPEC_CONFIG=missing", result.stdout)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertIn(["config-status", "--role", "execute", "--cwd", str(self.project)], calls)

    def test_a_sibling_wizard_is_found(self):
        wizard = self.skill.parent / "ai-kit-spec-config/SKILL.md"
        wizard.parent.mkdir()
        wizard.write_text("# Skill\n", encoding="utf-8")
        self.assertIn("SPEC_CONFIG=present", self._run(self._fill(self.blocks[0])).stdout)

    def test_a_resumed_run_asks_nothing_again(self):
        scalars = self._record_once()
        self._resume(scalars, self.plan)
        result = self._run(self._fill(self.blocks[0]))
        self.assertEqual(result.returncode, 0)
        self.assertIn("CONFIG_CHECK=once", result.stdout)
        self.assertIn("ask nothing", result.stdout)
        self.assertNotIn("config-status", self.log.read_text())

    def test_a_fresh_rerun_checks_again(self):
        scalars = self._record_once()
        self.log.write_text("", encoding="utf-8")
        result = self._run(self._fill(self.blocks[0]), state="active")
        self.assertEqual(result.returncode, 0)
        self.assertIn("old CONFIG_CHECK is cleared", result.stdout)
        self.assertIn("CONFIG_STATE=active", result.stdout)
        self.assertEqual(self.log.read_text().count("config-status"), 1)
        self.assertEqual(scalars.read_text().splitlines()[-1], "CONFIG_CHECK=")

    def test_a_wrong_plan_state_file_is_a_fresh_start(self):
        scalars = self._record_once()
        self._resume(scalars, "/elsewhere/plan.md")
        result = self._run(self._fill(self.blocks[0]))
        self.assertEqual(result.returncode, 0)
        self.assertIn("old CONFIG_CHECK is cleared", result.stdout)
        self.assertIn("config-status", self.log.read_text())

    def test_session_model_block_writes_the_native_injection(self):
        run = self.root / "run"
        run.mkdir()
        scalars = self.root / "scalars"
        result = self._run(self.blocks[2], CONFIG_CHECK="once", RUN_DIR=str(run),
                           SCALARS=str(scalars))
        self.assertEqual(result.returncode, 0, result.stderr)
        injection = run / "INJECTION_JSON.json"
        self.assertEqual(json.loads(injection.read_text()),
                         {"mode": "native", "key": "", "runtime": "", "model": "",
                          "ladder_keys": []})
        self.assertTrue(scalars.read_text().endswith("INJECTION_MODE=native\n"))
        injection.unlink()
        result = self._run(self.blocks[2], CONFIG_CHECK="active", RUN_DIR=str(run),
                           SCALARS=str(scalars))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(injection.exists())

    def test_exit_two_stops_with_the_code(self):
        result = self._run(self._fill(self.blocks[0]), rc="2")
        self.assertEqual(result.returncode, 2)
        self.assertIn("CONFIG_STATUS_EXIT=2", result.stdout)

    def test_record_refuses_an_unknown_value(self):
        scalars = self.root / "scalars"
        result = self._run(self._fill(self.blocks[1], scalars=str(scalars), outcome="maybe"))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(scalars.exists())

    def test_blocks_parse_with_bash_n(self):
        for block in self.blocks:
            result = subprocess.run([self.bash, "-n", "-c", block], capture_output=True,
                                    text=True, timeout=60, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_scalar_path_matches_the_task_paths_block(self):
        skill_lines = _read(ADAPTER_SKILL).splitlines()
        for name in ("QUOTA_PATH=", "PROJECT_KEY=", "SCALARS="):
            line = next(line.strip() for line in self.blocks[0].splitlines()
                        if line.startswith(name))
            self.assertIn(line, skill_lines)
        self.assertIn("superpowers-resume-${PROJECT_KEY}-task-", _read(ADAPTER_SKILL))


SESSION_MODE_SENTENCE = (
    "**Session-model mode:** when the scalar `CONFIG_CHECK` is `once` or `notice`, run block 3 "
    "of `references/config-check.md` in place of the `resolve-injection` block for every task "
    "(it writes `$RUN_DIR/INJECTION_JSON.json` with mode `native` and an empty key, runtime "
    "and model, and records `INJECTION_MODE=native`); the rest of Step 2 and Step 3 run "
    "unchanged, so the task dispatches natively with `model` omitted (the session model)."
)
NO_LADDER_SENTENCE = (
    "In session-model mode rounds 4–5 run on the session model with no ladder escalation and "
    "no model bump; the escalation rule above applies to every other mode."
)


class TestAdapterNoFormulaWording(unittest.TestCase):
    def test_adapter_texts_name_no_formula_not_the_seed_flag(self):
        refs = ADAPTER_SKILL.parent / "references"
        paths = [ADAPTER_SKILL, refs / "escalation.md", refs / "design-notes.md",
                 refs / "resolution-stops.md"]
        for path in [*paths, CONFIG_CHECK_MD]:
            with self.subTest(path=path):
                self.assertNotIn("review_only", _read(path))
                if path != CONFIG_CHECK_MD:
                    self.assertIn("no_formula", _read(path))
        for path in (ADAPTER_SKILL, refs / "design-notes.md"):
            self.assertNotIn("review-only", _read(path))

    def test_step_five_prints_the_notice_again(self):
        text = _read(ADAPTER_SKILL)
        section = text[text.index("## Step 5:"):text.index("## Close the session wake")]
        self.assertIn("`CONFIG_CHECK` is `once` or `notice`", section)

    def test_session_model_mode_skips_resolution(self):
        text = _read(ADAPTER_SKILL)
        step2 = text[text.index("## Step 2:"):text.index("## Step 3:")]
        step3 = text[text.index("## Step 3:"):text.index("## Step 4:")]
        self.assertIn(SESSION_MODE_SENTENCE, " ".join(step2.split()))
        self.assertIn(NO_LADDER_SENTENCE, " ".join(step3.split()))
        self.assertIn("Rounds 4–5 in this mode run on the session model with no ladder "
                      "escalation and no model bump", " ".join(_read(CONFIG_CHECK_MD).split()))


if __name__ == "__main__":
    unittest.main()
