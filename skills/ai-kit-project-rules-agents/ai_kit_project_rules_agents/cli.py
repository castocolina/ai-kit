"""argparse-free CLI: check, remediate.

`check`/`remediate`: `argv[1]` (if present) is the target repo_root.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse

from .remediation import build_remediation
from .rule_checker import check_workflow_rules
from .tool_presence import check_tool_presence

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_MAX_LINKS = 20
_BINARY_SNIFF = 8192


def _parse_link_target(raw: str) -> str | None:
    """Return the path to check, or None when the link is not a file link.

    Strips a CommonMark `<...>` wrapper or a trailing title, then cuts at
    the first `#` and the first `?` and percent-decodes the rest. Empty
    (anchor-only), absolute and any URL-scheme targets are skipped.
    """
    target = raw.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        # shortcut: an unwrapped target with a space ([x](my file.md))
        # checks only its first word; CommonMark needs <...> for such
        # paths, upgrade if one is reported.
        target = target.split()[0] if target.split() else ""
    target = target.split("#", 1)[0].split("?", 1)[0]
    if not target or target.startswith("/") or _SCHEME_RE.match(target):
        return None
    return urllib.parse.unquote(target)


def _without_fenced_code(text: str) -> str:
    """Drop fenced code blocks: a link-shaped example inside one is not a link."""
    kept: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        found = _FENCE_RE.match(line)
        if fence is None:
            if found:
                fence = found.group(1)
            else:
                kept.append(line)
        elif found and found.group(1)[0] == fence[0] and len(found.group(1)) >= len(fence):
            fence = None
    return "\n".join(kept)


def _read_text_target(path: str) -> str | None:
    """Read a linked file as UTF-8 text, or None when it is binary.

    A NUL in the first 8192 bytes, or any byte sequence that is not valid
    UTF-8, marks the file binary. Binary targets are never decoded.
    """
    with open(path, "rb") as handle:
        raw = handle.read()
    if b"\0" in raw[:_BINARY_SNIFF]:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _follow_links(
    text: str, root_dir: str, real_repo_root: str, source: str
) -> tuple[list[str], list[dict]]:
    """One hop of same-repo relative links: appended texts, broken findings.

    Containment is `os.path.realpath` on both sides, never lexical: a link
    that looks inside the repo but resolves outside it through a symlink
    is skipped and never read. Missing contained targets become broken-link
    findings; existing directories and binary targets are skipped.
    """
    seen: set[str] = set()
    appended: list[str] = []
    broken: list[dict] = []
    for match in _LINK_RE.finditer(_without_fenced_code(text)):
        if len(seen) >= _MAX_LINKS:
            break
        target = _parse_link_target(match.group(1))
        if target is None:
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
        if not os.path.exists(candidate_path):
            broken.append(
                {
                    "kind": "link",
                    "status": "broken",
                    "target": target,
                    "source": source,
                }
            )
            continue
        if not os.path.isfile(candidate_path):
            continue
        linked = _read_text_target(candidate_path)
        if linked is not None:
            appended.append(linked)
    broken.sort(key=lambda finding: finding["target"])
    return appended, broken


def _resolve(
    repo_root: str, agents_md_path: str | None
) -> tuple[str, list[dict]]:
    """Root instruction text plus one hop of followed links and findings."""
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

    source = os.path.relpath(root_path, repo_root)
    appended, broken = _follow_links(
        text, os.path.dirname(root_path), os.path.realpath(repo_root), source
    )
    if not appended:
        return text, broken
    return text + "\n\n" + "\n\n".join(appended), broken


def check(repo_root: str, agents_md_path: str | None = None) -> dict:
    text, broken = _resolve(repo_root, agents_md_path)
    presence = check_tool_presence(repo_root=repo_root)
    workflow_findings = check_workflow_rules(text, presence)
    workflow_findings = sorted(workflow_findings, key=lambda f: f["criticality"])
    return {"workflow": workflow_findings, "links": broken}


def remediate(repo_root: str, agents_md_path: str | None = None) -> dict:
    """`check(...)` then `remediation.build_remediation(...)` -- no second
    lookup into `rules.py`, no competing finding shape."""
    return build_remediation(check(repo_root, agents_md_path))


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(
            "usage: ai-kit-project-rules-agents.py check|remediate [repo_root]"
        )
        return 0
    cmd = argv[0]
    if cmd == "check":
        repo_root = argv[1] if len(argv) > 1 else "."
        print(json.dumps(check(repo_root), indent=2))
        return 0
    if cmd == "remediate":
        repo_root = argv[1] if len(argv) > 1 else "."
        print(json.dumps(remediate(repo_root), indent=2))
        return 0
    print(f"unknown subcommand: {cmd}", file=sys.stderr)
    return 2
