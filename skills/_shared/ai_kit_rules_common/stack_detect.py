"""Detect which language stack(s) a repo matches from marker files (D-02).
Moved verbatim from `ai-kit-project-rules-agents`'s Makefile-checker at
commit `9d672b9`, alongside the already-shared, generic `stack_cache.py` it
is paired with -- Phase 11's tooling-taxonomy research and Phase 13's
(`ai-kit-project-rules-docker`) checks both reach it from here.

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


__all__ = ["detect_stacks"]
