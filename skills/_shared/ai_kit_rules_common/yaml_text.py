"""Shared stdlib YAML-text primitives (D-D8, Phase 13 plan 02).

Three small, dependency-free building blocks -- quote stripping,
indentation measurement, and structural-line classification -- factored
out of `ai-kit-project-rules-docker`'s indentation-aware compose parser
because Phase 14's `ai-kit-project-rules-cicd` parses CI YAML with the
exact same stdlib-text approach (no YAML library, per 13-CONTEXT D-01/
D-02) and will reach for the same three primitives. This module lives in
`skills/_shared/` rather than inside the docker skill for that reason --
the same convergence argument `makefile_parse.py` records for its own
move here in Phase 10.

`strip_yaml_quotes` implements the EXACT rule
`precommit_parse._strip_yaml_quotes` (line 33) already implements: a
matched leading and trailing `'` or `"` pair removed, otherwise the value
unchanged. That private function is deliberately NOT repointed at this
module -- Phase 11 closed `precommit_parse.py`, and repointing a closed
file is a separate, reversible follow-up rather than this plan's
business. This is not a silent duplication: `criticality.py`'s docstring
already records exactly this arrangement for `rules.py` (a closed
sibling file left un-repointed while its literals are pinned equal), and
the same mitigation applies here -- a drift guard in
`tests/test_ai_kit_rules_common.py` pins `strip_yaml_quotes` and
`precommit_parse._strip_yaml_quotes` against each other over a shared
input set, so the two implementations cannot silently disagree.
"""

from __future__ import annotations


def strip_yaml_quotes(value: str) -> str:
    """A matched leading and trailing `'` or `"` pair removed, otherwise
    `value` unchanged. Never raises for any string input, including an
    empty or single-character one."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def line_indent(line: str) -> int:
    """A count of leading whitespace CHARACTERS -- `len(line) -
    len(line.lstrip())` -- never a tab-to-space-width conversion. YAML
    forbids tab indentation, so a tab-indented line's "indent" under this
    count is a raw character count, not a column position; a consumer
    reading a tab-indented file may therefore mis-attribute a block. That
    is a stated limit of whatever consumes this primitive (see
    `compose_parse.py`'s module docstring), not a defect in this
    function, which does exactly what its name says for any string."""
    return len(line) - len(line.lstrip())


def is_structural_line(line: str) -> bool:
    """`True` unless `line` is blank or a comment (first non-whitespace
    character `#`). Blank and comment lines never end a block and never
    set an indentation level for whatever consumes this primitive."""
    stripped = line.strip()
    if not stripped:
        return False
    return stripped[0] != "#"


__all__ = ["is_structural_line", "line_indent", "strip_yaml_quotes"]
