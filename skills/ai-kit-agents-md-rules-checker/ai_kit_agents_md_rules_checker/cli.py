"""argparse-free CLI: check, remediate, cache-update.

`check`/`remediate`: `argv[1]` (if present) is the target repo_root.
`cache-update`: positional `stack`, `json_path`, plus an explicit,
always-available `--cache-root <path>` test-only escape hatch (parsed by
hand below -- no `argparse`), never mentioned to end users in `SKILL.md`.
"""

from __future__ import annotations

import json
import os
import re
import sys

from . import stack_cache
from .makefile_checker import check_makefile_shape
from .remediation import build_remediation
from .rule_checker import check_workflow_rules
from .tool_presence import check_tool_presence

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_MAX_LINKS = 20

# At least one character that is neither whitespace nor a closing paren must
# immediately follow "(source:" (and any whitespace after it) -- rejects a
# bare substring match against "(source:)" or "(source: )" (Cycle 4 MEDIUM).
_SOURCE_CITATION_RE = re.compile(r"\(source:\s*[^\s)]")


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


def remediate(repo_root: str, agents_md_path: str | None = None) -> dict:
    """`check(...)` then `remediation.build_remediation(...)` -- no second
    lookup into `rules.py`, no competing finding shape."""
    return build_remediation(check(repo_root, agents_md_path))


def _validate_tooling_payload(data) -> str | None:
    """Return a one-line error string, or `None` if `data` is valid.

    `data` must be a JSON object; every key must be a member of
    `stack_cache.ALL_TOOLING_KEYS`; every value must be a non-empty `str`
    carrying a non-empty `(source: ...)` citation. Never merely checking for
    the bare substring `"(source:"` -- `"...(source:)"` and
    `"...(source: )"` are both rejected too (Cycle 3/Cycle 4 fixes).
    """
    if not isinstance(data, dict):
        return "tooling JSON must be an object, not a list/scalar"
    for key, value in data.items():
        if key not in stack_cache.ALL_TOOLING_KEYS:
            return f"unknown tooling key: {key!r}"
        if not isinstance(value, str) or not value:
            return f"value for {key!r} must be a non-empty string"
        if _SOURCE_CITATION_RE.search(value) is None:
            return (
                f"value for {key!r} is missing a non-empty (source: ...) "
                "citation"
            )
    return None


def _split_cache_root(args: list[str]) -> tuple[list[str], str | None]:
    """Strip a literal `--cache-root <path>` token pair from `args`.

    Returns `(remaining_positional_args, cache_root_or_None)`. Hand-scanned,
    never `argparse` -- matches the rest of this module's dispatch style.
    """
    remaining: list[str] = []
    cache_root: str | None = None
    i = 0
    while i < len(args):
        if args[i] == "--cache-root" and i + 1 < len(args):
            cache_root = args[i + 1]
            i += 2
            continue
        remaining.append(args[i])
        i += 1
    return remaining, cache_root


def cache_update(stack: str, json_path: str, cache_root: str | None = None) -> int:
    """Validate `json_path`'s JSON, then write it through `stack_cache`.

    `cache_root` is a TEST-ONLY escape hatch (default `None`, meaning
    `stack_cache.CACHE_ROOT`) -- never mentioned to an end user in
    `SKILL.md`, which always invokes `cache-update` without it.

    Never raises: a missing/unreadable `json_path`, syntactically invalid
    JSON, a structurally invalid tooling payload, or a path-traversal-shaped
    `stack` argument (caught as the `ValueError`
    `stack_cache.cache_path()` now raises before any path is joined) all
    print a one-line stderr error and return 1, writing nothing.
    """
    try:
        with open(json_path, encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as exc:
        print(f"cache-update: cannot read {json_path!r}: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"cache-update: invalid JSON in {json_path!r}: {exc}", file=sys.stderr)
        return 1

    error = _validate_tooling_payload(data)
    if error is not None:
        print(f"cache-update: {error}", file=sys.stderr)
        return 1

    try:
        stack_cache.write_stack_cache(stack, data, cache_root=cache_root)
    except ValueError as exc:
        print(f"cache-update: invalid stack identifier: {exc}", file=sys.stderr)
        return 1

    resolved_path = stack_cache.cache_path(stack, cache_root=cache_root)
    print(f"cache-update: wrote {stack!r} tooling cache to {resolved_path}")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(
            "usage: ai-kit-agents-md-rules-checker.py check|remediate [repo_root] "
            "| cache-update <stack> <json_path> [--cache-root <path>]"
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
    if cmd == "cache-update":
        positional, cache_root = _split_cache_root(argv[1:])
        if len(positional) < 2:
            print(
                "usage: cache-update <stack> <json_path> [--cache-root <path>]",
                file=sys.stderr,
            )
            return 1
        stack, json_path = positional[0], positional[1]
        return cache_update(stack, json_path, cache_root=cache_root)
    print(f"unknown subcommand: {cmd}", file=sys.stderr)
    return 2
