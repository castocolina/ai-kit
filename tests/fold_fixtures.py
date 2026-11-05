"""Helpers for the ai-kit-commit-fold tests: temp git repos, pinned identity, no host config."""

import json
import os
import pathlib
import shutil
import subprocess

from tests.test_jev_fast_decision import closed_port_url

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "ai-kit-commit-fold"
_SCRUBBED = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
# Host config roots and the jev client override: a fold run must never reach a real install.
HOST_CONFIG_VARS = ("CLAUDE_CONFIG_DIR", "XDG_CONFIG_HOME", "CURSOR_CONFIG_DIR",
                    "PI_CODING_AGENT_DIR", "AI_KIT_JEV_CLIENT")


def git_env(home):
    """A copy of os.environ for fixture git calls: no global or system config, fixed identity."""
    dropped = _SCRUBBED + HOST_CONFIG_VARS
    env = {key: value for key, value in os.environ.items() if key not in dropped}
    env.update({
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "HOME": str(home),
        "GIT_AUTHOR_NAME": "Fixture Author",
        "GIT_AUTHOR_EMAIL": "author@example.com",
        "GIT_COMMITTER_NAME": "Fixture Committer",
        "GIT_COMMITTER_EMAIL": "committer@example.com",
        "GIT_AUTHOR_DATE": "1700000000 +0000",
        "GIT_COMMITTER_DATE": "1700000000 +0000",
        "JEV_LAYA_URL": closed_port_url(),
    })
    return env


def run_git(repo, env, *args, data=None):
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        input=data, capture_output=True, env=env, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.decode().strip()}")
    return proc.stdout.decode("utf-8")


def make_repo(root, env):
    """A repository on `main` with one base commit (base.txt)."""
    repo = pathlib.Path(root) / "repo"
    repo.mkdir(parents=True)
    run_git(repo, env, "init", "-q", "-b", "main")
    commit(repo, env, {"base.txt": b"base\n"}, "chore: base")
    return repo


def commit(repo, env, files, message, author=None):
    """Write or delete each path (None deletes), stage those paths, commit, return the sha."""
    paths = []
    for name, content in files.items():
        target = pathlib.Path(repo) / name
        if content is None:
            target.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        paths.append(name)
    run_git(repo, env, "add", "-A", "--", *paths)
    commit_env = dict(env)
    if author is not None:
        commit_env.update(GIT_AUTHOR_NAME=author[0], GIT_AUTHOR_EMAIL=author[1])
    run_git(repo, commit_env, "commit", "-q", "-F", "-", data=message.encode("utf-8"))
    return run_git(repo, env, "rev-parse", "HEAD").strip()


def merge_no_ff(repo, env, branch, message):
    """Merge `branch` into the checked-out branch with a merge commit; return the merge sha."""
    run_git(repo, env, "merge", "--no-ff", "--no-edit", "-m", message, branch)
    return run_git(repo, env, "rev-parse", "HEAD").strip()


def set_ref(repo, env, ref, sha):
    """Point `ref` at `sha` (a fixture ref move; the working tree is not touched)."""
    run_git(repo, env, "update-ref", ref, sha)


def write_checkpoint(path, **fields):
    path = pathlib.Path(path)
    path.write_text(json.dumps(fields), encoding="utf-8")
    return path


def isolated_fold(root):
    """Copy the skill into `root` and return the copied fold.py, so CLI runs see no other skill."""
    dest = pathlib.Path(root) / "skills" / "ai-kit-commit-fold"
    shutil.copytree(SKILL, dest)
    return dest / "scripts" / "fold.py"


PHASE_BRANCH = "gsd/phase-07-demo"
PHASE_DIR = ".planning/phases/07-demo"
SP_PLAN = "docs/superpowers/plans/2026-11-04-demo.md"
SP_BRANCH = "feature/demo"


def gsd_plan_text(plan, stems):
    """A PLAN.md with one task element per stem: `Task N: Feature X` and its two files."""
    tasks = [
        f'<task type="auto">\n  <name>Task {number}: Feature {stem.upper()}</name>\n'
        f"  <files>{stem}.py, tests/test_{stem}.py</files>\n</task>"
        for number, stem in enumerate(stems, start=1)
    ]
    return f"# Phase 07 Plan {plan}\n\n<tasks>\n" + "\n".join(tasks) + "\n</tasks>\n"


def gsd_plan_commits(plan, stems, summary=True, state=True):
    """The commits of one plan: feat and test per stem, then `docs(07-NN): complete plan`."""
    unit = f"07-{plan}"
    specs = []
    for stem in stems:
        specs.append(({f"{stem}.py": f"{stem}\n".encode()}, f"feat({unit}): add {stem}", None))
        specs.append(({f"tests/test_{stem}.py": f"test {stem}\n".encode()},
                      f"test({unit}): test {stem}", None))
    if summary:
        files = {f"{PHASE_DIR}/{unit}-SUMMARY.md": f"summary {unit}\n".encode()}
        if state:
            files[".planning/STATE.md"] = f"state after {unit}\n".encode()
        specs.append((files, f"docs({unit}): complete plan", None))
    return specs


def _plan_files(plans):
    return {f"{PHASE_DIR}/07-{p['plan']}-PLAN.md": gsd_plan_text(p["plan"], p["stems"]).encode()
            for p in plans}


def gsd_project(root, env, mode, plans, stray=None):
    """A repo with a phase branch holding one PLAN.md per plan spec and its plan commits.

    plans: dicts with `plan` (NN), `stems` (two feature stems) and `summary` (default True).
    mode `sequential` commits each plan on the phase branch; `worktree` gives each plan its own
    branch, merges them back with GSD's merge subject, then adds one tracking commit.
    stray: (index, files, message) inserted into the sequential commit list.
    """
    repo = make_repo(root, env)
    run_git(repo, env, "checkout", "-q", "-b", PHASE_BRANCH)
    commit(repo, env, _plan_files(plans), "docs(07): create phase plan")
    if mode == "sequential":
        specs = [spec for p in plans
                 for spec in gsd_plan_commits(p["plan"], p["stems"], p.get("summary", True))]
        if stray is not None:
            specs.insert(stray[0], (stray[1], stray[2], None))
        for files, message, author in specs:
            commit(repo, env, files, message, author)
        return repo
    branches = []
    for p in plans:
        branch = f"worktree-agent-{p['plan']}"
        run_git(repo, env, "checkout", "-q", "-b", branch, PHASE_BRANCH)
        for files, message, author in gsd_plan_commits(p["plan"], p["stems"],
                                                       p.get("summary", True), state=False):
            commit(repo, env, files, message, author)
        run_git(repo, env, "checkout", "-q", PHASE_BRANCH)
        branches.append(branch)
    for branch in branches:
        merge_no_ff(repo, env, branch, f"chore: merge executor worktree ({branch})")
    commit(repo, env, {".planning/STATE.md": b"tracking\n", ".planning/ROADMAP.md": b"road\n"},
           "docs(phase-07): update tracking after wave 1")
    return repo


SP_PLAN_TEXT = """# Demo Plan

### Task 1: Feature A

**Files:**
- Create: `a.py`
- Test: `tests/test_a.py`

- [ ] **Step 1: write a**

### Task 2: Feature B

**Files:**
- Modify: `b.py:12-30`
- Test: `tests/test_b.py`
"""

SP_SPECS = [
    ({"a.py": b"a\n"}, "feat: add a", None),
    ({"tests/test_a.py": b"test a\n"}, "test: cover a", None),
    ({"b.py": b"b\n"}, "feat: add b", None),
    ({"tests/test_b.py": b"test b\n"}, "test: cover b", None),
]


def superpowers_project(root, env, specs=SP_SPECS):
    """A repo on main with the plan file, and a feature branch: a pre-plan commit, then specs.

    Returns (repo, pre-plan sha, branch shas).
    """
    repo = make_repo(root, env)
    commit(repo, env, {SP_PLAN: SP_PLAN_TEXT.encode()}, "docs: add plan")
    run_git(repo, env, "checkout", "-q", "-b", SP_BRANCH)
    pre_plan = commit(repo, env, {"design.md": b"design\n"}, "docs: add design")
    shas = [commit(repo, env, files, message, author) for files, message, author in specs]
    return repo, pre_plan, shas
