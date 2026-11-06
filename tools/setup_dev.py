#!/usr/bin/env python3
"""`make setup-dev`: uv sync, the flow's missing tools, then the git hooks, each guarded.

Installs only what is missing from PATH (never upgrades, never runs sudo, never pipes a
download into a shell). A step that fails, times out or cannot start is reported with its
manual command, and the script always exits 0 so the calling target never stops early.
Run under the git common dir lock so two worktrees do not install at once.
"""

import collections
import fcntl
import os
import shutil
import subprocess
import sys
from typing import NamedTuple

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TIMEOUT_SECONDS = 600
LOCK_NAME = "ai-kit-setup-dev.lock"


class Tool(NamedTuple):
    """One flow tool: how to probe it, what installs it, and the manual fallback."""

    name: str
    needs: str | None
    installer: str
    install: tuple[str, ...]
    manual: str
    verified: bool


TOOLS = (
    Tool("pre-commit", None, "uv", ("uv", "tool", "install", "pre-commit"),
         "uv tool install pre-commit", True),
    Tool("gh", None, "brew", ("brew", "install", "gh"),
         "install the GitHub CLI from https://cli.github.com (release tarball or a "
         "package manager)", False),
    Tool("gh-stack", "gh", "gh", ("gh", "extension", "install", "github/gh-stack"),
         "gh extension install github/gh-stack", True),
    Tool("codegraph", None, "pnpm", ("pnpm", "add", "-g", "@colbymchenry/codegraph"),
         "install codegraph (@colbymchenry/codegraph, github.com/colbymchenry/codegraph) "
         "with its own installer", False),
    Tool("graphify", None, "uv", ("uv", "tool", "install", "graphifyy"),
         "uv tool install graphifyy", True),
)


def _step(argv, env, runner, root):
    """Run one external command; return (rc or None, stdout, error text). Never raises."""
    try:
        done = runner(list(argv), cwd=root, env=env, capture_output=True, text=True,
                      check=False, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return None, "", f"timed out after {TIMEOUT_SECONDS} s"
    except OSError as error:
        return None, "", error.strerror or str(error)
    return done.returncode, done.stdout or "", ""


def _why(rc, err):
    return err if rc is None else f"exit {rc}"


def _on_path(name, env):
    return shutil.which(name, path=env.get("PATH", "")) is not None


def _present(tool, env, runner, root):
    if tool.name == "gh-stack":
        if not _on_path("gh", env):
            return False
        rc, out, _err = _step(["gh", "extension", "list"], env, runner, root)
        return rc == 0 and "gh-stack" in out
    return _on_path(tool.name, env)


def _lock(root, env, out):
    """Hold a blocking lock under the git common dir; None (with a note) when unavailable."""
    try:
        done = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=root, env=env, capture_output=True, text=True, check=False)
    except OSError as error:
        out(f"note: setup-dev lock unavailable ({error.strerror}); running without it")
        return None
    if done.returncode != 0:
        out("note: setup-dev lock unavailable (not a git checkout); running without it")
        return None
    fd = None
    try:
        fd = os.open(os.path.join(done.stdout.strip(), LOCK_NAME), os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
    except OSError as error:
        if fd is not None:
            os.close(fd)
        out(f"note: setup-dev lock unavailable ({error.strerror}); running without it")
        return None
    return fd


def _env_step(env, runner, root, out):
    if not _on_path("uv", env):
        out("env: not run: no uv; manual: install uv, then make setup-env")
        return
    rc, _out, err = _step(["uv", "sync"], env, runner, root)
    if rc == 0:
        out("env: synced (uv sync)")
    else:
        out(f"env: uv sync failed ({_why(rc, err)}); manual: make setup-env")


def _tool_step(tool, env, runner, root, out):
    """Report one tool and return its outcome: present, installed, manual or failed."""
    if _present(tool, env, runner, root):
        out(f"{tool.name}: present (left alone)")
        return "present"
    if tool.needs and not _on_path(tool.needs, env):
        out(f"{tool.name}: skipped: {tool.needs} is not available; manual: {tool.manual}")
        return "manual"
    if not _on_path(tool.installer, env):
        out(f"{tool.name}: not installed: no {tool.installer}; manual: {tool.manual}")
        return "manual"
    rc, _out, err = _step(tool.install, env, runner, root)
    command = " ".join(tool.install)
    if rc == 0 and _present(tool, env, runner, root):
        label = "" if tool.verified else " [unverified command]"
        out(f"{tool.name}: installed ({command}){label}")
        return "installed"
    if rc is None and err.startswith("timed out"):
        out(f"{tool.name}: install {err}; manual: {tool.manual}")
    elif rc == 0:
        out(f"{tool.name}: install ran but {tool.name} is not on PATH; manual: {tool.manual}")
    else:
        out(f"{tool.name}: install failed ({_why(rc, err)}); manual: {tool.manual}")
    return "failed"


def _hooks_step(env, runner, root, out):
    if not _on_path("uv", env):
        out("hooks: not run: no uv; manual: make dev")
        return
    rc, _out, err = _step(["uv", "run", "pre-commit", "install"], env, runner, root)
    if rc == 0:
        out("hooks: installed (uv run pre-commit install)")
    else:
        out(f"hooks: install failed ({_why(rc, err)}); manual: make dev")


def run(env, runner=subprocess.run, out=print, root=ROOT):
    """Run every guarded step in order and return 0 (the target never fails here)."""
    fd = _lock(root, env, out)
    try:
        _env_step(env, runner, root, out)
        counts = collections.Counter(
            _tool_step(tool, env, runner, root, out) for tool in TOOLS)
        _hooks_step(env, runner, root, out)
    finally:
        if fd is not None:
            os.close(fd)
    manual = counts["manual"] + counts["failed"]
    out(f"setup-dev: {counts['installed']} installed, {counts['present']} present, "
        f"{manual} need a manual step")
    return 0


def main():
    """Run with the caller's environment; any unexpected error is reported, exit still 0."""
    try:
        return run(dict(os.environ))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        # Every step already reports its own failure; this keeps a stray error from failing make.
        print(f"setup-dev: unexpected error: {error}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
