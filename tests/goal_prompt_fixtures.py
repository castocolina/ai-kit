"""Fixture project builders for the goal-prompt skill's tests (not a test module).

Every builder takes a `root` the caller owns (a TemporaryDirectory) and writes only under it.
FAKE_HOME is a literal string used to exercise the home guard; nothing creates it on disk.
stdlib only.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

FAKE_HOME = "/var/home/fakeuser"
SENTINEL_KEY = "SENTINEL-KEY-0123456789abcdef"

Phase = dict


def write(root: Path, relpath: str, text: str) -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def git_init(root: Path) -> None:
    """A repo with one empty commit; identity and signing are set locally for the fixture."""
    git = ["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid",
           "-c", "commit.gpgsign=false", "-C", str(root)]
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "fixture"], check=True)


def phase_spec(number: str, name: str, *, spec: bool = True, context: bool = True,
               plans: int = 0, reviews: bool = False, verification: bool = False,
               cross_ai: int = 0, disk_status: str = "no_directory") -> Phase:
    return {"number": number, "name": name, "spec": spec, "context": context, "plans": plans,
            "reviews": reviews, "verification": verification, "cross_ai": cross_ai,
            "disk_status": disk_status}


def _prefix(number: str) -> str:
    head, dot, tail = number.partition(".")
    return head.zfill(2) + (dot + tail if dot else "")


def _dirname(phase: Phase) -> str:
    return f"{_prefix(phase['number'])}-{phase['name'].lower().replace(' ', '-')}"


def plan_text(title: str, depends_on: str | None = None, tasks: int = 2) -> str:
    lines = [f"# {title}", ""]
    if depends_on is not None:
        lines += [f"**Depends on:** {depends_on}", ""]
    for index in range(1, tasks + 1):
        lines += [f"### Task {index}: step {index}", "", f"Do step {index}.", ""]
    return "\n".join(lines)


def opengsd_project(root: Path, phases: list[Phase]) -> None:
    write(root, ".planning/PROJECT.md", "# Fixture project\n")
    config = {
        "workflow": {"cross_ai_execution": True,
                     "cross_ai_command": "node .planning/scripts/cross-ai.mjs"},
        "plan_review_convergence": True,
        "review": {"default_reviewers": ["referee-one"]},
    }
    write(root, ".planning/config.json", json.dumps(config, indent=2) + "\n")
    for phase in phases:
        prefix = _prefix(phase["number"])
        base = f".planning/phases/{_dirname(phase)}"
        if phase["spec"]:
            write(root, f"{base}/{prefix}-SPEC.md", "# Spec\n")
        if phase["context"]:
            write(root, f"{base}/{prefix}-CONTEXT.md", "# Context\n")
        for index in range(1, phase["plans"] + 1):
            plan = f"{prefix}-{index:02d}"
            if index <= phase["cross_ai"]:
                front = f"---\nphase: {prefix}\nplan: {index:02d}\ncross_ai: true\n---\n"
            else:
                front = f"---\nphase: {prefix}\nplan: {index:02d}\n---\n"
            write(root, f"{base}/{plan}-PLAN.md", front + plan_text(f"Plan {plan}"))
        if phase["reviews"]:
            write(root, f"{base}/{prefix}-REVIEWS.md", "# Reviews\n")
        if phase["verification"]:
            write(root, f"{base}/{prefix}-VERIFICATION.md", "# Verification\n")


def roadmap_json(phases: list[Phase]) -> dict[str, Any]:
    """Shape of `gsd-tools query roadmap.analyze` (the fields the skill reads)."""
    return {
        "milestones": [{"version": "v1.3", "name": "fixture milestone"}],
        "phases": [
            {"number": p["number"], "name": p["name"], "goal": f"goal of {p['name']}",
             "depends_on": "", "plan_count": p["plans"], "summary_count": 0,
             "has_context": p["context"], "disk_status": p["disk_status"],
             "roadmap_complete": False}
            for p in phases
        ],
    }


def phase_op_json(root: Path, phases: list[Phase]) -> dict[str, dict[str, Any]]:
    """Number -> `init phase-op` document. Paths are ABSOLUTE on purpose (tests relativize)."""
    state = str(root / ".planning" / "STATE.md")
    docs: dict[str, dict[str, Any]] = {}
    for p in phases:
        docs[p["number"]] = {
            "phase_found": True,
            "phase_dir": str(root / ".planning" / "phases" / _dirname(p)),
            "phase_number": p["number"],
            "has_context": p["context"],
            "has_plans": p["plans"] > 0,
            "has_reviews": p["reviews"],
            "has_verification": p["verification"],
            "plan_count": p["plans"],
            "state_path": state,
        }
    return docs


def identity_json(opengsd: bool) -> dict[str, str]:
    if opengsd:
        return {"packageName": "@opengsd/gsd-core", "version": "1.17.0"}
    return {"packageName": "get-shit-done-cc", "version": "1.0.0"}


def superpowers_project(root: Path, plans: dict[str, str]) -> None:
    plans_dir = root / "docs" / "superpowers" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    for name, text in plans.items():
        write(root, f"docs/superpowers/plans/{name}", text)


def makefile(root: Path, targets: dict[str, str]) -> Path:
    body = "".join(f"{name}:\n\t{recipe}\n\n" for name, recipe in targets.items())
    return write(root, "Makefile", body)


def package_json(root: Path, scripts: dict[str, str], lockfile: str | None = None) -> Path:
    path = write(root, "package.json", json.dumps({"scripts": scripts}, indent=2) + "\n")
    if lockfile:
        write(root, lockfile, "")
    return path


def playwright_config(root: Path) -> Path:
    return write(root, "playwright.config.ts", "export default {};\n")


def cypress_config(root: Path) -> Path:
    return write(root, "cypress.config.js", "module.exports = {};\n")


def pty_driver(root: Path, relpath: str, module: str = "pty") -> Path:
    return write(root, relpath, f"import {module}\n\n\ndef test_driver():\n    pass\n")


def empty_project(root: Path) -> Path:
    return write(root, "README.md", "# Empty fixture\n")
