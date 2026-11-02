"""Evals, trigger queries, README and script smoke for skills/ai-kit-spec-goal-prompt (27-14).
Structure and behavior only: no model is called, no real home is touched.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skills" / "ai-kit-spec-goal-prompt"
SCRIPT = SKILL / "scripts" / "goal_prompt.py"
EVALS = SKILL / "evals"
sys.path.insert(0, str(SKILL / "scripts"))
sys.path.insert(0, str(REPO / "skills" / "ai-kit-spec-review"))
import goal_prompt
import gp_common
from ai_kit_spec.detection import HOST_SIGNAL_ENV_VARS

from tests import goal_prompt_fixtures as fx

MACHINE_PATH_RE = re.compile(r"/var/home|/home/[A-Za-z]|/Users/|~/")
LINK_RE = re.compile(r"\]\(([^)#\s]+)\)")


def text_files() -> list[Path]:
    """README plus every file under evals/ (utf-8 text only)."""
    files = [SKILL / "README.md"]
    files += [p for p in sorted(EVALS.rglob("*")) if p.is_file()] if EVALS.is_dir() else []
    return [p for p in files if p.is_file()]


class TestReadme(unittest.TestCase):
    README = SKILL / "README.md"

    def _text(self) -> str:
        return self.README.read_text(encoding="utf-8")

    def test_readme_exists_and_is_short(self):
        self.assertTrue(self.README.is_file())
        lines = self._text().splitlines()
        self.assertGreaterEqual(len(lines), 15)
        self.assertLessEqual(len(lines), 80)
        self.assertEqual(lines[0], "# ai-kit-spec-goal-prompt")

    def test_readme_has_the_five_sections(self):
        lines = self._text().splitlines()
        for heading in ("What it is", "When to use", "Install", "Usage", "Links"):
            self.assertIn(f"## {heading}", lines)

    def test_readme_links_resolve(self):
        targets = [t for t in LINK_RE.findall(self._text()) if not t.startswith("http")]
        for target in targets:
            self.assertTrue((self.README.parent / target).exists(), target)
        for required in ("SKILL.md", "references/", "evals/evals.json",
                         "evals/trigger-queries.json",
                         "tests/test_ai_kit_spec_goal_prompt_evals.py"):
            self.assertTrue(any(required in t for t in targets), required)

    def test_readme_content_pins(self):
        text = self._text()
        install = "python3 tools/setup.py install --headless --skills ai-kit-spec-goal-prompt"
        for fragment in ("goal_prompt.py detect", "goal_prompt.py render", install,
                         "unverified", "never runs"):
            self.assertIn(fragment, text)
        self.assertIsNone(MACHINE_PATH_RE.search(text))


TRIGGER_FILE = EVALS / "trigger-queries.json"
NEAR_MISS_WORDS = re.compile(
    r"\b(phase|phases|plan|plans|loop|goal|prompt|run|schedule)\b", re.IGNORECASE)
POSITIVE_LITERALS = ("/goal", "/loop", "goal prompt", "loop prompt", "one-shot")


class TestTriggerQueries(unittest.TestCase):
    def _items(self) -> list:
        return json.loads(TRIGGER_FILE.read_text(encoding="utf-8"))

    def test_shape(self):
        items = self._items()
        self.assertIsInstance(items, list)
        for item in items:
            self.assertIsInstance(item, dict)
            self.assertEqual(set(item), {"query", "should_trigger"})
            self.assertIsInstance(item["query"], str)
            self.assertTrue(item["query"].strip())
            self.assertIsInstance(item["should_trigger"], bool)

    def test_counts(self):
        items = self._items()
        self.assertEqual(len(items), 20)
        self.assertEqual(sum(1 for item in items if item["should_trigger"]), 10)
        self.assertEqual(sum(1 for item in items if not item["should_trigger"]), 10)

    def test_unique_and_substantial(self):
        items = self._items()
        lowered = [item["query"].lower() for item in items]
        self.assertEqual(len(set(lowered)), len(lowered))
        for item in items:
            self.assertGreaterEqual(len(item["query"].split()), 6, item["query"])

    def test_negatives_are_near_misses(self):
        negatives = [item["query"] for item in self._items() if not item["should_trigger"]]
        near = [q for q in negatives if NEAR_MISS_WORDS.search(q)]
        self.assertGreaterEqual(len(near), 8)

    def test_realistic_variety(self):
        items = self._items()
        queries = [item["query"] for item in items]
        with_digit_or_slash = [q for q in queries if re.search(r"[0-9/]", q)]
        self.assertGreaterEqual(len(with_digit_or_slash), 5)
        long_ones = [q for q in queries if len(q.split()) >= 12]
        self.assertGreaterEqual(len(long_ones), 5)
        positives = [item["query"] for item in items if item["should_trigger"]]
        unnamed = [q for q in positives if not any(lit in q.lower() for lit in POSITIVE_LITERALS)]
        self.assertGreaterEqual(len(unnamed), 3)

    def test_hygiene(self):
        text = TRIGGER_FILE.read_text(encoding="utf-8")
        self.assertIsNone(MACHINE_PATH_RE.search(text))
        self.assertEqual(
            gp_common.scan_text(text, home=fx.FAKE_HOME, secrets=(fx.SENTINEL_KEY,)), [])


VAGUE_RE = re.compile(
    r"\b(?:works|correct|correctly|properly|good|nice|well|appropriate|appropriately"
    r"|todo|tbd|placeholder|etc)\b|\bas expected\b",
    re.IGNORECASE,
)
BACKTICK_RE = re.compile(r"`[^`]+`")
PROMPT_PATH_RE = re.compile(r"evals/files/[A-Za-z0-9_./-]+")
EVAL_ID_RE = re.compile(r"^(casual|precise|edge)-[a-z0-9-]+$")
EVAL_KEYS = {"id", "prompt", "expected_output", "files", "assertions"}
EVALS_FILE = EVALS / "evals.json"
FILES_ROOT = EVALS / "files"


def assertion_problems(text: str) -> list[str]:
    """Reasons an assertion is not concrete enough to check (empty when it is)."""
    problems: list[str] = []
    if len(text) < 40:
        problems.append("shorter than 40 characters")
    if VAGUE_RE.search(text):
        problems.append("vague word")
    return problems


def _evals() -> dict:
    return json.loads(EVALS_FILE.read_text(encoding="utf-8"))


def eval_env(home: str) -> dict[str, str]:
    """The CLI's env: a fake HOME and XDG dir, and Claude Code as the current host.

    The evals say "target host is the current one" and expect Claude's primitives, so the
    caller's host signals are replaced: a plain-terminal `git push` would otherwise detect no
    host and drop the goal strategy.
    """
    env = {k: v for k, v in os.environ.items() if k not in HOST_SIGNAL_ENV_VARS}
    env["CLAUDECODE"] = "1"
    env["HOME"] = home
    env["XDG_CONFIG_HOME"] = home + "/.config"
    env["AI_KIT_REFUSE_REAL_HOME"] = "1"
    return env


def run_cli(*args: str, home: str) -> subprocess.CompletedProcess:
    """Run the real CLI under `eval_env`; never the owner's home."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL,
        check=False, env=eval_env(home),
    )


def stage_project(name: str, dest: Path) -> Path:
    """Copy a fixture project to `dest`; its `planning/` folder becomes `.planning/`."""
    shutil.copytree(FILES_ROOT / name / "project", dest)
    planning = dest / "planning"
    if planning.is_dir():
        planning.rename(dest / ".planning")
    return dest


def stage_captures(dest_dir: Path, repo: Path) -> Path:
    """Copy the captured gsd-tools JSON and put the real repository root in place of @REPO@."""
    shutil.copytree(FILES_ROOT / "opengsd-mixed" / "captures", dest_dir)
    for path in dest_dir.rglob("*.json"):
        text = path.read_text(encoding="utf-8").replace("@REPO@", str(repo))
        path.write_text(text, encoding="utf-8")
    return dest_dir


class TestEvals(unittest.TestCase):
    def test_top_level_shape(self):
        doc = _evals()
        self.assertIsInstance(doc, dict)
        self.assertEqual(doc["skill_name"], "ai-kit-spec-goal-prompt")
        self.assertIsInstance(doc["evals"], list)

    def test_count_and_unique_ids(self):
        evals = _evals()["evals"]
        self.assertGreaterEqual(len(evals), 6)
        ids = [e["id"] for e in evals]
        self.assertEqual(len(set(ids)), len(ids))
        for eval_id in ids:
            self.assertRegex(eval_id, EVAL_ID_RE)

    def test_required_fields(self):
        for item in _evals()["evals"]:
            self.assertEqual(set(item), EVAL_KEYS, item.get("id"))
            self.assertIsInstance(item["prompt"], str)
            self.assertTrue(item["prompt"])
            self.assertIsInstance(item["expected_output"], str)
            self.assertTrue(item["expected_output"])
            self.assertIsInstance(item["files"], list)
            self.assertTrue(item["files"])
            self.assertTrue(all(isinstance(f, str) for f in item["files"]))
            self.assertIsInstance(item["assertions"], list)
            self.assertGreaterEqual(len(item["assertions"]), 4)
            self.assertTrue(all(isinstance(a, str) for a in item["assertions"]))

    def test_phrasing_and_edge_mix(self):
        ids = [e["id"] for e in _evals()["evals"]]
        self.assertTrue(any(i.startswith("casual-") for i in ids))
        self.assertTrue(any(i.startswith("precise-") for i in ids))
        self.assertGreaterEqual(sum(1 for i in ids if i.startswith("edge-")), 2)

    def test_input_files_exist(self):
        for item in _evals()["evals"]:
            for rel in item["files"]:
                self.assertTrue(rel.startswith("evals/files/"), rel)
                self.assertNotIn("..", rel)
                self.assertFalse(os.path.isabs(rel), rel)
                self.assertTrue((SKILL / rel).is_file(), rel)

    def test_no_orphan_fixture_files(self):
        listed = {rel for item in _evals()["evals"] for rel in item["files"]}
        on_disk = {p.relative_to(SKILL).as_posix()
                   for p in FILES_ROOT.rglob("*") if p.is_file()}
        self.assertEqual(on_disk - listed, set())

    def test_prompt_fixture_paths_exist(self):
        for item in _evals()["evals"]:
            for match in PROMPT_PATH_RE.findall(item["prompt"]):
                rel = match.rstrip(".,)")
                self.assertTrue((SKILL / rel).exists(), rel)

    def test_assertions_are_concrete(self):
        seen: set[str] = set()
        for item in _evals()["evals"]:
            for text in item["assertions"]:
                self.assertEqual(assertion_problems(text), [], text)
                self.assertNotIn(text, seen, text)
                seen.add(text)
            with_literal = [a for a in item["assertions"] if BACKTICK_RE.search(a)]
            self.assertGreaterEqual(len(with_literal), 3, item["id"])

    def test_assertion_checker_is_not_vacuous(self):
        self.assertNotEqual(assertion_problems("It works correctly."), [])
        self.assertNotEqual(assertion_problems("ok"), [])
        real = _evals()["evals"][0]["assertions"][0]
        self.assertEqual(assertion_problems(real), [])

    def test_no_machine_paths_or_secrets(self):
        for path in text_files():
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(MACHINE_PATH_RE.search(text), path.name)
            self.assertEqual(
                gp_common.scan_text(text, home=fx.FAKE_HOME, secrets=(fx.SENTINEL_KEY,)),
                [], path.name)

    def test_fixtures_hold_no_live_planning_dir(self):
        paths = list(FILES_ROOT.rglob("*"))
        for path in paths:
            self.assertFalse({".planning", "__pycache__"} & set(path.parts), path)
        if shutil.which("git") is None:
            self.skipTest("git is not installed")
        files = [p.relative_to(REPO).as_posix() for p in paths if p.is_file()]
        proc = subprocess.run(
            ["git", "check-ignore", "--no-index", *files],
            cwd=REPO, capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.stdout.strip(), "")


class TestFixtureDetect(unittest.TestCase):
    """Each fixture kind through the real `detect` CLI; no render, no model."""

    def _json(self, proc: subprocess.CompletedProcess) -> dict:
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_current_host_does_not_follow_the_caller(self):
        """A plain-terminal caller (no host signal) still detects Claude Code as current."""
        plain = {k: v for k, v in os.environ.items() if k not in HOST_SIGNAL_ENV_VARS}
        with tempfile.TemporaryDirectory() as tmp, unittest.mock.patch.dict(
            os.environ, plain, clear=True
        ):
            home = Path(tmp) / "home"
            home.mkdir()
            repo = stage_project("opengsd-mixed", Path(tmp) / "repo")
            result = self._json(run_cli("detect", "--repo", str(repo), "--tools", "",
                                        home=str(home)))
        self.assertEqual(result["host"]["current"], "claude")
        self.assertIn("goal", [s["id"] for s in result["strategies"]])

    def test_opengsd_mixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            repo = stage_project("opengsd-mixed", root / "repo")
            caps = stage_captures(root / "caps", repo)
            proc = run_cli(
                "detect", "--repo", str(repo), "--work-set", "phases:16-18",
                "--roadmap", str(caps / "roadmap.json"),
                "--identity", str(caps / "identity.json"),
                "--phase-op", str(caps / "phase-op"), "--tools", "",
                home=str(home),
            )
            result = self._json(proc)
            self.assertEqual(result["schema_version"], 1)
            self.assertEqual(result["scope"]["kind"], "opengsd")
            self.assertEqual(result["scope"]["identity"], "opengsd")
            phases = result["scope"]["phases"]
            self.assertEqual([p["number"] for p in phases], ["16", "17", "18"])
            self.assertEqual([p["plan_count"] for p in phases], [2, 2, 0])
            self.assertEqual([c["command"] for c in result["e2e"]["commands"]],
                             ["make e2e-test"])
            self.assertNotIn(str(repo), proc.stdout)

    def test_long_goal_eval_renders_the_pointer_form(self):
        """The assertions of `precise-long-goal-pointer` hold on the real CLI output."""
        item = next(e for e in _evals()["evals"] if e["id"] == "precise-long-goal-pointer")
        objective = item["prompt"].split("as the objective: ")[1].split(" Native execution")[0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            repo = stage_project("opengsd-mixed", root / "repo")
            caps = stage_captures(root / "caps", repo)
            detect = run_cli(
                "detect", "--repo", str(repo), "--work-set", "phases:16-18",
                "--roadmap", str(caps / "roadmap.json"),
                "--identity", str(caps / "identity.json"),
                "--phase-op", str(caps / "phase-op"), "--tools", "", home=str(home),
            )
            self._json(detect)
            (root / "detect.json").write_text(detect.stdout, encoding="utf-8")
            answers = {"work_set": {"kind": "phases", "numbers": ["16", "17", "18"]},
                       "target_host": "claude", "native_execution": False, "mockups": [],
                       "strategy": "goal", "objective": objective, "output_dir": None}
            (root / "answers.json").write_text(json.dumps(answers), encoding="utf-8")
            proc = run_cli("render", "--repo", str(repo), "--detect", str(root / "detect.json"),
                           "--answers", str(root / "answers.json"), home=str(home))
            result = self._json(proc)
            text = (repo / result["path"]).read_text(encoding="utf-8")
        self.assertEqual(result["goal_form"], "pointer")
        (entry,) = result["conditions"]
        self.assertGreater(entry["full_chars"], 1000)
        self.assertLess(entry["chars"], 200)
        goal_lines = [line for line in text.split("\n") if line.startswith("/goal ")]
        self.assertEqual(len(goal_lines), 1)
        self.assertTrue(goal_lines[0].startswith("/goal read document"))
        self.assertIn(f"`{result['path']}`", goal_lines[0])
        self.assertTrue(goal_lines[0].endswith("DONE WHEN conditions hold"))
        tail = text.partition("\n## Full goal\n")[2]
        self.assertIn("Unit tests alone never count as done.", " ".join(tail.split()))
        self.assertIn("never touch my real configuration files", " ".join(tail.split()))
        self.assertTrue(all(len(line) <= 100 for line in tail.split("\n")))
        self.assertTrue(any("unverified" in warning for warning in result["warnings"]))
        self.assertTrue(result["full_objective"])
        self.assertIn("section Full objective)", text)
        self.assertLess(text.index("\n## Full objective\n"), text.index("\n## Full goal\n"))
        full_objective = text.partition("\n## Full objective\n")[2].partition("\n## Full goal\n")[0]
        self.assertIn(objective, " ".join(full_objective.split()))

    def test_opengsd_without_captures_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            repo = stage_project("opengsd-mixed", root / "repo")
            proc = run_cli("detect", "--repo", str(repo), "--work-set", "phases:16-18",
                           "--tools", "", home=str(home))
            self.assertEqual(proc.returncode, 2)
            error = json.loads(proc.stderr)["error"]
            self.assertTrue("--roadmap" in error or "--gsd-cmd" in error, error)

    def test_superpowers_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            repo = stage_project("superpowers-chain", root / "repo")
            proc = run_cli("detect", "--repo", str(repo),
                           "--work-set", "plans:alpha.md,beta.md,gamma.md", "--tools", "",
                           home=str(home))
            result = self._json(proc)
            self.assertEqual(result["scope"]["kind"], "superpowers")
            order = result["scope"]["order"]
            self.assertLess(order.index("alpha.md"), order.index("beta.md"))
            commands = [c["command"] for c in result["e2e"]["commands"]]
            self.assertIn("make e2e-test", commands)

    def test_superpowers_chain_for_codex(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            repo = stage_project("superpowers-chain", root / "repo")
            proc = run_cli("detect", "--repo", str(repo),
                           "--work-set", "plans:alpha.md,beta.md,gamma.md", "--tools", "",
                           "--target-host", "codex", home=str(home))
            result = self._json(proc)
            primitives = result["primitives"]
            items = list(primitives.values()) if isinstance(primitives, dict) else primitives
            self.assertTrue(items)
            for item in items:
                self.assertEqual(item["availability"], "unverified")

    def test_no_e2e_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            repo = stage_project("no-e2e", root / "repo")
            proc = run_cli("detect", "--repo", str(repo), "--work-set", "plans:solo.md",
                           "--tools", "", home=str(home))
            self.assertEqual(self._json(proc)["e2e"]["commands"], [])

    def test_empty_project_asks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            repo = stage_project("empty-project", root / "repo")
            proc = run_cli("detect", "--repo", str(repo), "--tools", "", home=str(home))
            scope = self._json(proc)["scope"]
            self.assertEqual(scope["kind"], "none")
            self.assertIsNotNone(scope["ask"])

    def test_both_frameworks_asks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            repo = stage_project("both-frameworks", root / "repo")
            proc = run_cli("detect", "--repo", str(repo), "--tools", "", home=str(home))
            result = self._json(proc)
            self.assertEqual(result["scope"]["kind"], "both")
            self.assertIsNotNone(result["scope"]["ask"])
            self.assertEqual(result["strategies"], [])


class TestScriptCli(unittest.TestCase):
    """The entry script's non-interactive contract: help, one JSON object, exit codes."""

    def _help(self, *argv: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as home:
            return run_cli(*argv, home=home)

    def test_help_exits_zero_and_prints_usage(self):
        for argv in (["--help"], ["detect", "--help"], ["render", "--help"]):
            proc = self._help(*argv)
            self.assertEqual(proc.returncode, 0, argv)
            self.assertTrue(proc.stdout.startswith("usage:"), argv)
            self.assertEqual(proc.stderr, "", argv)

    def test_help_lists_the_documented_flags(self):
        detect = self._help("detect", "--help").stdout
        for flag in ("--repo", "--target-host", "--tools", "--work-set", "--gsd-cmd",
                     "--roadmap", "--identity", "--phase-op"):
            self.assertIn(flag, detect)
        render = self._help("render", "--help").stdout
        for flag in ("--repo", "--detect", "--answers", "--out-dir"):
            self.assertIn(flag, render)
        root = self._help("--help").stdout
        self.assertIn("detect", root)
        self.assertIn("render", root)

    def test_help_documents_exit_codes(self):
        lines = self._help("--help").stdout.splitlines()
        index = next(i for i, line in enumerate(lines) if "Exit codes" in line)
        window = " ".join(lines[index:index + 3])
        self.assertRegex(window, r"\b0\b")
        self.assertRegex(window, r"\b2\b")

    def test_every_option_has_help_text(self):
        parser = goal_prompt.build_parser()
        subparsers = next(a for a in parser._actions
                          if isinstance(a, argparse._SubParsersAction))
        for name in ("detect", "render"):
            for action in subparsers.choices[name]._actions:
                if isinstance(action, argparse._HelpAction):
                    continue
                self.assertIsInstance(action.help, str, f"{name} {action.dest}")
                self.assertTrue(action.help.strip(), f"{name} {action.dest}")

    def test_detect_prints_one_json_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            repo = stage_project("superpowers-chain", root / "repo")
            proc = run_cli("detect", "--repo", str(repo), "--work-set", "plans:alpha.md",
                           "--tools", "", home=str(home))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stderr, "")
            result = json.loads(proc.stdout)
            self.assertEqual(result["schema_version"], 1)
            for key in ("host", "primitives", "scope", "e2e", "derived", "strategies"):
                self.assertIn(key, result)
            self.assertGreaterEqual(len(result["strategies"]), 1)
            self.assertLessEqual(len(result["strategies"]), 3)

    def test_render_bad_input_exits_two_with_json_stderr(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            home.mkdir()
            repo = stage_project("superpowers-chain", root / "repo")
            detect_file = root / "detect.json"
            detect = run_cli("detect", "--repo", str(repo), "--work-set", "plans:alpha.md",
                             "--tools", "", home=str(home))
            detect_file.write_text(detect.stdout, encoding="utf-8")
            answers_file = root / "answers.json"
            answers_file.write_text("{}", encoding="utf-8")
            before = sorted(p.relative_to(repo) for p in repo.rglob("*"))
            proc = run_cli("render", "--repo", str(repo), "--detect", str(detect_file),
                           "--answers", str(answers_file), home=str(home))
            self.assertEqual(proc.returncode, 2)
            self.assertEqual(proc.stdout, "")
            self.assertIn("error", json.loads(proc.stderr))
            self.assertEqual(sorted(p.relative_to(repo) for p in repo.rglob("*")), before)


if __name__ == "__main__":
    unittest.main()
