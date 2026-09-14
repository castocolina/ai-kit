"""Pre-commit-hook parsing primitives shared across the ai-kit rules-checker
skill family (D-01). Moved verbatim from `ai-kit-project-rules-agents`'s
Makefile-checker at commit `9d672b9`. `check_precommit_prepush_split` gets a
HOME here and a CALLER in Phase 11 (`ai-kit-project-rules-precommit`) -- this
phase's own `ai-kit-project-rules-makefile` checker does not call it, per
the design spec's ownership split.
"""

from __future__ import annotations

import os
import re

from .criticality import CRITICALITY_MEDIUM

SLOW_HOOK_KEYWORDS = (
    "test",
    "pytest",
    "unittest",
    "mypy",
    "pyright",
    "vulture",
    "integration",
    "e2e",
    "arch",
)

_ID_LINE_RE = re.compile(r"^\s*-\s*id:\s*(.+?)\s*$", re.MULTILINE)
_ENTRY_LINE_RE = re.compile(r"^\s*entry:\s*(.+?)\s*$", re.MULTILINE)
_STAGES_LINE_RE = re.compile(r"^\s*stages:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)


def _strip_yaml_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def iter_precommit_hook_blocks(text: str):
    """Yield `(hook_id, entry_or_None, block_text)` for every `- id:` hook.

    `hook_id` is normalized to its bare string regardless of bare/single/
    double-quoted YAML form. A hook's block runs from its own `- id:` line
    up to (not including) the next `- id:` line, or end of file. Public
    (not `_`-prefixed) because Phase 11 iterates whole blocks, not just ids.
    """
    id_matches = list(_ID_LINE_RE.finditer(text))
    for pos, match in enumerate(id_matches):
        hook_id = _strip_yaml_quotes(match.group(1))
        start = match.start()
        end = id_matches[pos + 1].start() if pos + 1 < len(id_matches) else len(text)
        block = text[start:end]
        entry_match = _ENTRY_LINE_RE.search(block)
        entry = entry_match.group(1) if entry_match else None
        yield hook_id, entry, block


def parse_precommit_hooks(path: str) -> dict[str, str | None]:
    """Return `dict[hook_id, entry_command_or_None]` for every hook id.

    Matches a hook id whether declared bare, double-quoted, or single-
    quoted. `None` when that hook has no inline `entry:` line (e.g. a
    non-`local` `repo:` block whose real command lives in an external
    hook-repo manifest). Empty dict if `path` does not exist.
    """
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    return {hook_id: entry for hook_id, entry, _block in iter_precommit_hook_blocks(text)}


def check_precommit_prepush_split(repo_root: str) -> dict | None:
    """Structural check for the removed `precommit-vs-prepush-split` category.

    Classifies each present hook as "slow" via `SLOW_HOOK_KEYWORDS`
    (case-insensitive substring match against that hook's id OR its
    `entry:` command), then checks EACH slow hook's OWN YAML block for its
    own `stages:` value naming `pre-push`/`push` -- never "does ANY hook
    anywhere have a push stage". Returns `None` when there is nothing to
    verify (no slow hook at all) or every slow hook already has its own
    push stage; otherwise returns one finding naming every slow hook still
    missing its own push stage.
    """
    path = os.path.join(repo_root, ".pre-commit-config.yaml")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    missing = []
    for hook_id, entry, block in iter_precommit_hook_blocks(text):
        haystack = f"{hook_id} {entry or ''}".lower()
        if not any(keyword in haystack for keyword in SLOW_HOOK_KEYWORDS):
            continue
        stages_match = _STAGES_LINE_RE.search(block)
        value = stages_match.group(1).lower() if stages_match else ""
        if "pre-push" in value or "push" in value:
            continue
        missing.append(hook_id)
    if not missing:
        return None
    ids = sorted(missing)
    recommendation = (
        "split the slower hooks into a pre-push stage (e.g. add "
        "`stages: [pre-push]` to: " + ", ".join(ids) + ") so `pre-commit` "
        "itself stays fast"
    )
    return {
        "category": "precommit-vs-prepush-split",
        "issue": "slow_hooks_not_pushed",
        "slow_hooks_missing_push_stage": ids,
        "recommendation": recommendation,
        "needs_research": False,
        "criticality": CRITICALITY_MEDIUM,
        "summary": recommendation,
    }


__all__ = [
    "SLOW_HOOK_KEYWORDS",
    "check_precommit_prepush_split",
    "iter_precommit_hook_blocks",
    "parse_precommit_hooks",
]
