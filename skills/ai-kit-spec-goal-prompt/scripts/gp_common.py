#!/usr/bin/env python3
"""Shared helpers for the goal-prompt skill. stdlib only.

Three helpers are COPIES (D-03), not imports, so this skill has no cross-skill dependency.
Each copy is parity-tested against its original in tests/test_ai_kit_spec_goal_prompt_common.py:
  - phase_key:            skills/ai-kit-gsd-spec-discuss/scripts/phase_range.py lines 28-37
  - make_targets:         skills/_shared/ai_kit_rules_common/makefile_parse.py line 16 (regex)
                          and parse_makefile_targets_ordered (lines 19-44)
  - read_package_scripts / package_runner: skills/ai-kit-project-rules-cicd/
                          ai_kit_project_rules_cicd/package_scripts.py, read_package_scripts
                          (line 58) and resolve_package_manager_runner (line 46)

Guards (is_machine_path, scan_text) and the file helpers (slugify, unique_path, strip_ansi) are
new here. scan_text takes its key shapes from the sibling secret_shapes.py, a byte-identical copy
of the shared scanner, and never flags a leading slash, so slash commands such as /goal pass.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Sequence

import secret_shapes

_TARGET_HEADER_RE = re.compile(r"^(?!\.)([A-Za-z0-9_.-]+)\s*:(?!=)(.*)$", re.MULTILINE)
_LOCKFILE_RUNNERS: tuple[tuple[str, str], ...] = (
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("bun.lockb", "bun"),
    ("bun.lock", "bun"),
)
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:\\")
# One problem message per shared shape name; the two older names keep their wording.
_SHAPE_MESSAGES = {
    "sk_rk_key": "API-key-shaped token present",
    "github_token": "GitHub-token-shaped token present",
}
_SLUG_MAX = 40


class GuardError(ValueError):
    """A goal-prompt guard refused an input."""


def phase_key(number: str) -> tuple[int, ...]:
    """Numeric sort key for a dotted phase number (16 < 16.1 < 17). ValueError otherwise."""
    text = str(number)
    if not re.fullmatch(r"\d+(?:\.\d+)*", text):
        raise ValueError("invalid phase number")
    return tuple(int(part) for part in text.split("."))


def make_targets(text: str) -> list[str]:
    """Real target names in declaration order; a repeated target keeps its first position."""
    ordered: list[str] = []
    for match in _TARGET_HEADER_RE.finditer(text):
        name = match.group(1)
        if name not in ordered:
            ordered.append(name)
    return ordered


def read_package_scripts(repo: str) -> list[tuple[str, str]]:
    """(name, command) pairs from the root package.json `scripts`. Never raises; [] on any fault."""
    try:
        with open(os.path.join(repo, "package.json"), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, UnicodeDecodeError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return []
    return [(name, cmd) for name, cmd in scripts.items() if isinstance(cmd, str)]


def package_runner(repo: str) -> str:
    """The first lockfile in the pinned order decides the runner; npm when none exists."""
    for filename, runner in _LOCKFILE_RUNNERS:
        if os.path.isfile(os.path.join(repo, filename)):
            return runner
    return "npm"


def is_machine_path(value: str, home: str) -> bool:
    """True for an absolute, home-relative or Windows-drive path, or any value naming the home."""
    if value.startswith(("/", "~/")) or _WINDOWS_DRIVE_RE.match(value):
        return True
    return len(home) >= 2 and home in value


def scan_text(text: str, *, home: str, secrets: Sequence[str]) -> list[str]:
    """Problem kinds found in `text`. Messages name the kind only, never the matched text."""
    problems: list[str] = []
    if len(home) >= 2 and home in text:
        problems.append("machine home path present")
    for secret in secrets:
        if secret and secret in text:
            problems.append("secret value present")
    for name in secret_shapes.detect(text):
        problems.append(_SHAPE_MESSAGES.get(name, f"{name}-shaped token present"))
    return problems


def slugify(text: str) -> str:
    """Lowercase ASCII slug, at most 40 characters; "goal" when nothing is left."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:_SLUG_MAX].rstrip("-")
    return slug or "goal"


def unique_path(directory: str, name: str) -> str:
    """`directory/name`, or `name-2`, `name-3`, ... when that path is taken. Never overwrites."""
    base, ext = os.path.splitext(name)
    candidate = os.path.join(directory, name)
    counter = 2
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base}-{counter}{ext}")
        counter += 1
    return candidate


def strip_ansi(text: str) -> str:
    """Remove ANSI CSI colour and cursor sequences."""
    return _ANSI_RE.sub("", text)


__all__ = [
    "GuardError",
    "is_machine_path",
    "make_targets",
    "package_runner",
    "phase_key",
    "read_package_scripts",
    "scan_text",
    "slugify",
    "strip_ansi",
    "unique_path",
]
