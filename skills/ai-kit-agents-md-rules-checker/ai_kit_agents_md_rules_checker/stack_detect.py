"""Detect which language stack(s) a repo matches from marker files.

D-04: stack tooling is NOT hardcoded to go/python/node/java alone -- this
module only answers "which stack(s)", never what tooling to use for them.
"""

from __future__ import annotations

import os

_MARKERS: tuple[tuple[str, str], ...] = (
    ("go.mod", "go"),
    ("requirements.txt", "python"),
    ("pyproject.toml", "python"),
    ("setup.py", "python"),
    ("Pipfile", "python"),
    ("package.json", "node"),
    ("pom.xml", "java"),
    ("build.gradle", "java"),
    ("build.gradle.kts", "java"),
    ("Cargo.toml", "rust"),
)


def detect_stacks(repo_root: str) -> set[str]:
    """Return the set of stacks whose marker file(s) exist under `repo_root`.

    A repo can match more than one stack.
    """
    stacks: set[str] = set()
    for marker, stack in _MARKERS:
        if os.path.isfile(os.path.join(repo_root, marker)):
            stacks.add(stack)
    return stacks
