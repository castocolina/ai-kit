"""argparse-free CLI: check, remediate.

No third subcommand (D-A6): this skill's baseline knowledge is hardcoded
and it has no research dispatch, unlike the Phase 10 and Phase 11 siblings
whose per-stack tooling genuinely goes stale.
`argv[1]` (if present) is the target repo_root for both subcommands.
"""

from __future__ import annotations

import json
import sys

from .arch_checker import check_arch_rules
from .remediation import build_remediation


def check(repo_root: str) -> dict:
    findings = check_arch_rules(repo_root)
    findings = sorted(findings, key=lambda f: f["criticality"])
    return {"arch": findings}


def remediate(repo_root: str) -> dict:
    """`check(...)` then `remediation.build_remediation(...)` -- no second
    lookup into the checker, no competing finding shape."""
    return build_remediation(check(repo_root))


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: ai-kit-project-rules-arch.py check|remediate [repo_root]")
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
