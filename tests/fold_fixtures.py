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


def git_env(home):
    """A copy of os.environ for fixture git calls: no global or system config, fixed identity."""
    env = {key: value for key, value in os.environ.items() if key not in _SCRUBBED}
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


def write_checkpoint(path, **fields):
    path = pathlib.Path(path)
    path.write_text(json.dumps(fields), encoding="utf-8")
    return path


def isolated_fold(root):
    """Copy the skill into `root` and return the copied fold.py, so CLI runs see no other skill."""
    dest = pathlib.Path(root) / "skills" / "ai-kit-commit-fold"
    shutil.copytree(SKILL, dest)
    return dest / "scripts" / "fold.py"
