"""Makefile-parsing primitives shared across the ai-kit rules-checker skill
family (D-05). Moved verbatim from `ai-kit-project-rules-agents`'s
Makefile-checker at commit `9d672b9` so Phase 10, Phase 11, and Phase 14 all
reach the same target/recipe/prerequisite parsing instead of each
re-deriving it -- a 3-skill convergence discovered while discussing Phase
14 (`ai-kit-project-rules-cicd` needs to know what `make <target>` commands
already exist; Phase 11's parity check needs the same parsing to match
Makefile targets against pre-commit hook ids).
"""

from __future__ import annotations

import os
import re

_TARGET_HEADER_RE = re.compile(r"^(?!\.)([A-Za-z0-9_.-]+)\s*:(?!=)(.*)$", re.MULTILINE)


def parse_makefile_targets_ordered(path: str) -> list[str]:
    """Return real target names defined in `path`, in Makefile declaration
    order.

    This is the single source of truth for target tokenization: `finditer`s
    the same module-private header regex `parse_makefile_targets` (the
    set-returning reader) is defined in terms of, so the two can never
    disagree about what counts as a target. `.PHONY:`/other special targets
    and recipe lines are never mistaken for targets; a `VAR := value` /
    `VAR ?= value` assignment is excluded via the `(?!=)` guard on the
    colon. A target declared twice de-duplicates to its FIRST occurrence,
    since "first in declaration order" must stay meaningful even though a
    Makefile may legally redeclare a target. Empty list if `path` does not
    exist.
    """
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    ordered: list[str] = []
    seen: set[str] = set()
    for m in _TARGET_HEADER_RE.finditer(text):
        name = m.group(1)
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def parse_makefile_targets(path: str) -> set[str]:
    """Return the set of real target names defined in `path`.

    Defined in terms of `parse_makefile_targets_ordered` (the single source
    of truth for target tokenization -- destroys declaration order, which
    D-A1's arch-test-shaped-target tie-break needs the ordered reader for
    instead) so the two readers can never disagree about what counts as a
    target. `.PHONY:`/other special targets and recipe lines are never
    mistaken for targets; a `VAR := value` / `VAR ?= value` assignment is
    excluded via the `(?!=)` guard on the colon. Empty set if `path` does
    not exist.
    """
    return set(parse_makefile_targets_ordered(path))


def parse_makefile_prerequisites_ordered(path: str, target: str) -> list[str]:
    """Return `target`'s Make prerequisite tokens, in declaration order.

    This is the single source of truth for prerequisite tokenization:
    strips an inline comment at the first `#` on the header line, then
    splits on whitespace. `parse_makefile_prerequisites` (the set-returning
    reader) is defined in terms of this function so the two can never
    disagree about what counts as a prerequisite token. Empty list if
    `target` is absent or declares no prerequisites.
    """
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    pattern = re.compile(rf"^(?!\.){re.escape(target)}\s*:(?!=)(.*)$", re.MULTILINE)
    match = pattern.search(text)
    if match is None:
        return []
    prereq_text = match.group(1).split("#", 1)[0]
    return prereq_text.split()


def parse_makefile_prerequisites(path: str, target: str) -> set[str]:
    """Return `target`'s Make prerequisite tokens (`target: dep1 dep2`).

    Distinct from `parse_makefile_recipe`: prerequisites are declared on the
    header line itself, recipe lines are the indented lines that follow.
    Defined in terms of `parse_makefile_prerequisites_ordered` (the single
    source of truth for prerequisite tokenization -- destroys declaration
    order, which plan 10-02's advisory ordering heuristic needs the ordered
    reader for instead) so the two readers can never disagree about what
    counts as a prerequisite token. Empty set if `target` is absent or
    declares no prerequisites.
    """
    return set(parse_makefile_prerequisites_ordered(path, target))


def parse_makefile_recipe(path: str, target: str) -> str:
    """Return the joined text of `target`'s indented recipe lines.

    `""` if `target` is absent. Stops at the next non-indented, non-blank
    line after the header.
    """
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()
    pattern = re.compile(rf"^(?!\.){re.escape(target)}\s*:(?!=)")
    header_idx = None
    for idx, line in enumerate(lines):
        if pattern.match(line):
            header_idx = idx
            break
    if header_idx is None:
        return ""
    recipe_lines = []
    for line in lines[header_idx + 1 :]:
        if line.strip() == "" or line[:1] in (" ", "\t"):
            recipe_lines.append(line)
            continue
        break
    return "".join(recipe_lines)


def recipe_mentions_target(recipe_text: str, name: str) -> bool:
    """Token-boundary-aware check: never a raw substring match.

    `name="lint"` does not match a recipe invoking `"pylint"`. `name=
    "test-unit"` matches the standalone token `"test-unit"` but NOT inside
    a longer hyphenated token on EITHER side, e.g. neither
    `"test-unit-integration-suite"` nor `"integration-test-unit"` --
    `\\b` alone is insufficient here because `-` is a non-word character,
    so a plain `\\btest-unit\\b` would treat the boundary between `"unit"`
    and a following `"-integration..."` (or between a preceding
    `"integration-"` and `"test"`) as already satisfied. Requires the
    character immediately before AND after the match (if any) to NOT be
    `-`/`_`/alnum, i.e. a true token boundary on both ends.
    """
    pattern = rf"(?<![-\w]){re.escape(name)}(?![-\w])"
    return re.search(pattern, recipe_text) is not None


__all__ = [
    "parse_makefile_prerequisites",
    "parse_makefile_prerequisites_ordered",
    "parse_makefile_recipe",
    "parse_makefile_targets",
    "parse_makefile_targets_ordered",
    "recipe_mentions_target",
]
