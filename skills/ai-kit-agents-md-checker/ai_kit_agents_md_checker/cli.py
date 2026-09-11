"""argparse-free CLI: check. `argv[1]` (if present) is the target repo_root."""

from __future__ import annotations

import json
import os
import re
import sys

from .makefile_checker import check_makefile_shape
from .rule_checker import check_workflow_rules
from .tool_presence import check_tool_presence

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_MAX_LINKS = 20


def resolve_instruction_text(repo_root: str, agents_md_path: str | None = None) -> str:
    """Resolve AGENTS.md (falling back to CLAUDE.md) and follow one hop
    of same-repo relative Markdown links out of the root file.

    Containment of a linked file under `repo_root` is checked via
    `os.path.realpath` on both sides, never lexical path comparison -- a
    link that looks like it resolves inside the repo but, via a symlink
    anywhere in its path, actually resolves outside `repo_root`'s real
    path is rejected and never read.
    """
    if agents_md_path:
        root_path = agents_md_path
    else:
        agents_candidate = os.path.join(repo_root, "AGENTS.md")
        claude_candidate = os.path.join(repo_root, "CLAUDE.md")
        if os.path.isfile(agents_candidate):
            root_path = agents_candidate
        elif os.path.isfile(claude_candidate):
            root_path = claude_candidate
        else:
            root_path = agents_candidate

    if os.path.isfile(root_path):
        with open(root_path, encoding="utf-8") as handle:
            text = handle.read()
    else:
        text = ""

    real_repo_root = os.path.realpath(repo_root)
    root_dir = os.path.dirname(root_path)
    seen: set[str] = set()
    appended: list[str] = []

    for match in _LINK_RE.finditer(text):
        if len(seen) >= _MAX_LINKS:
            break
        target = match.group(1).strip()
        if not target or target.startswith("/") or "://" in target:
            continue
        candidate_path = os.path.join(root_dir, target)
        real_link = os.path.realpath(candidate_path)
        if real_link in seen:
            continue
        seen.add(real_link)
        if not (
            real_link == real_repo_root
            or real_link.startswith(real_repo_root + os.sep)
        ):
            continue
        if not os.path.isfile(candidate_path):
            continue
        with open(candidate_path, encoding="utf-8") as handle:
            appended.append(handle.read())

    if not appended:
        return text
    return text + "\n\n" + "\n\n".join(appended)


def check(repo_root: str, agents_md_path: str | None = None) -> dict:
    makefile_findings = check_makefile_shape(repo_root)
    text = resolve_instruction_text(repo_root, agents_md_path)
    presence = check_tool_presence(repo_root=repo_root)
    workflow_findings = check_workflow_rules(text, presence)
    workflow_findings = sorted(workflow_findings, key=lambda f: f["criticality"])
    return {"makefile": makefile_findings, "workflow": workflow_findings}


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: ai-kit-agents-md-checker.py check [repo_root]")
        return 0
    cmd = argv[0]
    if cmd == "check":
        repo_root = argv[1] if len(argv) > 1 else "."
        print(json.dumps(check(repo_root), indent=2))
        return 0
    print(f"unknown subcommand: {cmd}", file=sys.stderr)
    return 2
