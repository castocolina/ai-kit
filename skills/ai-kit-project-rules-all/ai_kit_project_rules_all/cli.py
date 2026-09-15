"""argparse-free CLI: check, remediate.

`check`/`remediate`: `argv[1]` (if present) is the target repo_root, matching
every sibling's own `main(argv)` shape exactly.

`dispatch`/`aggregate` are imported and called via qualified module-attribute
access (`from . import dispatch, aggregate` then `dispatch.dispatch_all(...)`/
`aggregate.aggregate(...)`), never imported by name (`from .dispatch import
dispatch_all`) -- mirroring `dispatch.py`'s `DOMAIN_TIMEOUT_SECONDS`
module-level-name rule, this guarantees a test's monkeypatch of
`dispatch.dispatch_all` is effective rather than silently no-opping.
"""

from __future__ import annotations

import json
import sys

from . import aggregate, dispatch


def check(repo_root: str) -> dict:
    return aggregate.aggregate(dispatch.dispatch_all(repo_root))


def remediate(repo_root: str) -> dict:
    """D-04: identical to `check`. Every per-finding classification already
    happened inside each sibling's own `remediate` subprocess call (which
    itself calls that sibling's `check` internally before running the shared
    `build_remediation()` builder) -- there is no further per-orchestrator
    classification step left for THIS command to do beyond the cross-domain
    merge `check` already performs.
    """
    return check(repo_root)


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: ai-kit-project-rules-all.py check|remediate [repo_root]")
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
