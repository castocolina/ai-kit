"""Real-CLI run for the goal-prompt skill: the e2e tier (GPS-01..04; D-22).

Spawns the real `goal_prompt.py` as a subprocess on a temporary git repository. A fake `node` on
PATH answers only the three read-only gsd-tools queries and the runner's `--print-argv`; host CLI
probes reach the `tests/host_fakes.py` fakes, never a real host. HOME is a temporary directory and
AI_KIT_REFUSE_REAL_HOME=1 is exported. The dogfood run detects this repository read-only. Every
subprocess has a timeout, and none outlives its test.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests import goal_prompt_fixtures as fx
from tests import host_fakes

REPO = Path(__file__).resolve().parent.parent
CLI = REPO / "skills" / "ai-kit-spec-goal-prompt" / "scripts" / "goal_prompt.py"
TIMEOUT = 120
PHASES = [
    fx.phase_spec("16", "Foundation", plans=2, cross_ai=2, verification=True),
    fx.phase_spec("16.1", "Hotfix", plans=1),
    fx.phase_spec("17", "Surfaces", spec=False, plans=2),
]
FAKE_NODE = """#!/bin/sh
# Stand-in for node: answers only the read-only queries the goal-prompt CLI makes.
case "$*" in
  *--print-argv*) printf 'pi\\t/bin/pi\\t[]\\n'; exit 0 ;;
  *"query roadmap.analyze"*) cat "$GOAL_FIXTURE/roadmap.json"; exit 0 ;;
  *"query runtime-identity"*) cat "$GOAL_FIXTURE/identity.json"; exit 0 ;;
  *"query init.phase-op "*)
    number=$(printf '%s' "$*" | sed 's/.*init\\.phase-op //')
    cat "$GOAL_FIXTURE/ops/$number.json"; exit 0 ;;
esac
exit 127
"""
ANSWERS = {
    "work_set": {"kind": "phases", "numbers": ["16", "16.1", "17"]},
    "target_host": "claude",
    "native_execution": False,
    "mockups": [],
    "strategy": None,
    "objective": "Finish phases 16 to 17, each verified.",
    "output_dir": None,
}


# Directories a walk over a checkout skips (the same set for the status snapshot and the copy).
WALK_SKIP = frozenset({".git", ".venv", "tmp", "__pycache__"})


def _clean_env() -> dict[str, str]:
    """The environment without GIT_* variables: a commit hook exports GIT_INDEX_FILE, which
    would point these git calls at the outer repository's index instead of the one they name."""
    return {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}


def git_status(repo: Path) -> set[str]:
    """Every porcelain line of `repo`, untracked files listed one by one. A checkout without
    `.git` (the clean-room image copies the tree without it) gets a file snapshot instead."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True, text=True, check=False, timeout=TIMEOUT, env=_clean_env(),
    )
    if proc.returncode == 0:
        return set(proc.stdout.splitlines())
    lines = set()
    for base, dirs, names in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in WALK_SKIP]
        for name in names:
            path = Path(base, name)
            stat = path.stat()
            lines.add(f"{path.relative_to(repo)} {stat.st_size} {stat.st_mtime_ns}")
    return lines


def source_files(repo: Path) -> list[Path]:
    """The checkout's files a copy takes, relative to `repo`, never anything under `.planning/`
    (SPEC R9). Tracked files from `git ls-files` when the checkout has git; otherwise a walk
    that skips the git_status set plus `.planning` (the clean-room image has no `.git`)."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z"],
        capture_output=True, check=False, timeout=TIMEOUT, env=_clean_env(),
    )
    if proc.returncode == 0:
        names = [name for name in proc.stdout.decode("utf-8").split("\0") if name]
    else:
        skip = WALK_SKIP | {".planning"}
        names = []
        for base, dirs, files in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in skip]
            names += [os.path.relpath(os.path.join(base, name), repo) for name in files]
    return [Path(name) for name in names
            if name != ".planning" and not name.startswith(".planning/")]


def copy_checkout(dest: Path) -> None:
    """Copy this checkout minus `.planning/` into `dest` and make it a git repo with one commit,
    so the dogfood detect reads the copy and the copy's status can be compared before and after."""
    for rel in source_files(REPO):
        src, out = REPO / rel, dest / rel
        if not os.path.lexists(src):  # tracked but deleted in the work tree
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            os.symlink(os.readlink(src), out)
        elif src.is_file():
            shutil.copy2(src, out)
    commands = (
        ["init", "-q"],
        ["add", "--all"],
        ["-c", "user.name=ai-kit-test", "-c", "user.email=test@example.invalid",
         "commit", "-q", "-m", "copy of the checkout without .planning"],
    )
    for args in commands:
        subprocess.run(["git", "-C", str(dest), *args], check=True, capture_output=True,
                       timeout=TIMEOUT, env=_clean_env())


class TestRealCli(unittest.TestCase):
    """The real CLI on a temporary git repository with a fake `node` on PATH."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        fx.git_init(self.repo)
        fx.opengsd_project(self.repo, PHASES)
        self.fixture = self.root / "fixture"
        fx.write(self.fixture, "roadmap.json", json.dumps(fx.roadmap_json(PHASES)))
        fx.write(self.fixture, "identity.json", json.dumps(fx.identity_json(True)))
        for number, doc in fx.phase_op_json(self.repo, PHASES).items():
            fx.write(self.fixture / "ops", f"{number}.json", json.dumps(doc))
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        node = bin_dir / "node"
        node.write_text(FAKE_NODE, encoding="utf-8")
        node.chmod(0o755)
        home = self.root / "home"
        home.mkdir()
        self.env = {
            "PATH": os.pathsep.join([
                str(bin_dir), host_fakes.write_host_fakes(self.root / "host-bin"),
                os.environ.get("PATH", ""),
            ]),
            "HOME": str(home),
            "AI_KIT_REFUSE_REAL_HOME": "1",
            "GOAL_FIXTURE": str(self.fixture),
        }

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            capture_output=True, text=True, env=self.env, cwd=str(self.root),
            timeout=TIMEOUT, check=False,
        )

    def test_detect_and_render_on_a_temp_git_repo(self):
        before = git_status(self.repo)
        detect_run = self.run_cli(
            "detect", "--repo", str(self.repo),
            "--gsd-cmd", "node .claude/gsd-core/bin/gsd-tools.cjs",
            "--work-set", "phases:16-17", "--tools", "CronCreate",
        )
        self.assertEqual(detect_run.returncode, 0, detect_run.stderr)
        detect_doc = json.loads(detect_run.stdout)
        self.assertEqual(detect_doc["scope"]["kind"], "opengsd")
        self.assertEqual(git_status(self.repo), before, "detect must not write")

        detect_path = self.root / "detect.json"
        detect_path.write_text(detect_run.stdout, encoding="utf-8")
        answers_path = self.root / "answers.json"
        answers_path.write_text(json.dumps(ANSWERS), encoding="utf-8")
        render_run = self.run_cli(
            "render", "--repo", str(self.repo),
            "--detect", str(detect_path), "--answers", str(answers_path),
        )
        self.assertEqual(render_run.returncode, 0, render_run.stderr)
        payload = json.loads(render_run.stdout)
        self.assertTrue(payload["path"].startswith(".planning/goals/"), payload["path"])
        text = (self.repo / payload["path"]).read_text(encoding="utf-8")
        first_fence_line = text.split("````\n", 1)[1].split("\n", 1)[0]
        self.assertTrue(first_fence_line.startswith("/gsd-autonomous --from 16 --to 17 --converge"),
                        first_fence_line)
        new_lines = git_status(self.repo) - before
        self.assertEqual(new_lines, {f"?? {payload['path']}"})

    def test_bad_input_exits_two_with_a_json_error(self):
        detect_path = self.root / "detect.json"
        detect_path.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
        answers_path = self.root / "answers.json"
        answers_path.write_text(json.dumps({"strategy": "bogus"}), encoding="utf-8")
        run = self.run_cli(
            "render", "--repo", str(self.repo),
            "--detect", str(detect_path), "--answers", str(answers_path),
        )
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, "")
        self.assertIn("error", json.loads(run.stderr))


class TestStatusSnapshot(unittest.TestCase):
    def test_checkout_without_git_still_detects_a_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "a.txt").write_text("a", encoding="utf-8")
            before = git_status(repo)
            self.assertTrue(before)
            (repo / "b.txt").write_text("b", encoding="utf-8")
            self.assertNotEqual(git_status(repo), before)


class TestDogfood(unittest.TestCase):
    def test_detect_on_a_copy_of_this_repo(self):
        # The live .planning/ is never read: detect runs on a copy without it (SPEC R9).
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as work:
            env = {
                "PATH": host_fakes.host_path(host_fakes.write_host_fakes(Path(home) / "host-bin")),
                "HOME": home,
                "AI_KIT_REFUSE_REAL_HOME": "1",
            }
            copy = Path(work) / "checkout"
            copy.mkdir()
            copy_checkout(copy)
            before = git_status(copy)
            run = subprocess.run(
                [sys.executable, str(CLI), "detect", "--repo", str(copy),
                 "--tools", "", "--work-set", "free:dogfood"],
                capture_output=True, text=True, env=env, timeout=TIMEOUT, check=False,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(git_status(copy), before, "dogfood detect must not write")
        commands = [c["command"] for c in json.loads(run.stdout)["e2e"]["commands"]]
        self.assertIn("make e2e-test", commands)
        self.assertIn("make e2e-docker", commands)

    def test_source_files_without_git(self):
        # The clean-room image has no .git: the walk fallback lists files, minus .planning.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in ("a.py", "pkg/b.py", ".planning/STATE.md", "tmp/scratch.txt",
                        "__pycache__/c.pyc"):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text("x", encoding="utf-8")
            self.assertEqual(
                sorted(source_files(root)), [Path("a.py"), Path("pkg/b.py")]
            )


if __name__ == "__main__":
    unittest.main()
