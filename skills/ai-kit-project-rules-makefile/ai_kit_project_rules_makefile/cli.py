"""argparse-free CLI: check, remediate, cache-update.

`check`/`remediate`: `argv[1]` (if present) is the target repo_root.
`cache-update`: positional `stack`, `json_path`, plus an explicit,
always-available `--cache-root <path>` test-only escape hatch (parsed by
hand below -- no `argparse`), never mentioned to end users in `SKILL.md`.
"""

from __future__ import annotations

import json
import sys

from . import stack_cache
from .makefile_checker import check_makefile_shape
from .remediation import build_remediation
from .tooling_payload import validate_tooling_payload


def check(repo_root: str) -> dict:
    findings = check_makefile_shape(repo_root)
    findings = sorted(findings, key=lambda f: f["criticality"])
    return {"makefile": findings}


def remediate(repo_root: str) -> dict:
    """`check(...)` then `remediation.build_remediation(...)` -- no second
    lookup into the checker, no competing finding shape."""
    return build_remediation(check(repo_root))


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
    `stack` argument (caught as the `ValueError` `stack_cache.cache_path()`
    now raises before any path is joined) all print a one-line stderr error
    and return 1, writing nothing.
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

    error = validate_tooling_payload(data)
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
            "usage: ai-kit-project-rules-makefile.py check|remediate [repo_root] "
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
