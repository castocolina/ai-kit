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

Phase 14 plan 01 (D-C8) appends six more primitives -- `is_document_
separator`, `is_effective_structural`, `strip_inline_comment`,
`match_key_header`, `find_block_end`, `own_level_lines` -- generalizing
`ai-kit-project-rules-docker`'s `compose_parse.py` six module-private
helpers of the same shape (`_is_document_separator`,
`_effective_structural`, `_strip_inline_comment`, `_match_key_header`,
`_find_block_end`, `_own_level_lines`) so `ai-kit-project-rules-cicd`'s
indentation-aware CI-YAML reader can reuse them rather than re-deriving
its own copy. `compose_parse.py` is deliberately NOT repointed at these
six -- Phase 13 closed that file, the same closed-file reason this
docstring already records for `strip_yaml_quotes` above -- and the same
mitigation applies: a drift guard in `tests/test_ai_kit_rules_common.py`
pins each new primitive against its `compose_parse.py` private
counterpart over a shared input table, loading that file by path rather
than importing the docker skill's package.
"""

from __future__ import annotations

import re


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


_KEY_HEADER_RE = re.compile(r"^([^\s:#][^:]*):(.*)$")


def is_document_separator(line: str) -> bool:
    """`True` for a `---` YAML document separator, skipped as structural
    noise rather than treated as a key by whatever consumes this
    primitive. Never raises for any string input."""
    return line.strip() == "---"


def is_effective_structural(line: str) -> bool:
    """`is_structural_line` plus the `---` document-separator carve-out:
    `True` unless `line` is blank, a comment, or a bare document
    separator. Never raises."""
    if not is_structural_line(line):
        return False
    return not is_document_separator(line)


def strip_inline_comment(text: str) -> str:
    """Truncate `text` at the first UNQUOTED `#`, honouring single- and
    double-quoted regions. Never raises for any string input."""
    in_single = False
    in_double = False
    for i, ch in enumerate(text):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return text[:i]
    return text


def match_key_header(content: str) -> tuple[str, str] | None:
    """`content` is an already-stripped line. Returns `(key, rest)` when
    `content` is a `key:` header line, or `None` otherwise. Never
    raises."""
    match = _KEY_HEADER_RE.match(content)
    if match is None:
        return None
    return match.group(1).strip(), match.group(2)


def find_block_end(lines: list[str], start: int, ref_indent: int) -> int:
    """Index of the first effectively-structural line at index >= `start`
    whose indent is <= `ref_indent` -- the block-end rule: a block owned
    by a key at indent `ref_indent` runs from `start` until that line, or
    to `len(lines)` if none exists. Never raises for any well-formed
    `lines`/`start`/`ref_indent` input."""
    n = len(lines)
    i = start
    while i < n:
        line = lines[i]
        if is_effective_structural(line) and line_indent(line) <= ref_indent:
            return i
        i += 1
    return n


def own_level_lines(lines: list[str], start: int, end: int):
    """Yield `(line_index, stripped_content)` for every effectively-
    structural line in `lines[start:end]` at the block's OWN first
    nesting level -- the level established by the FIRST such line. A
    line at a DEEPER indent is a child of the preceding header and is
    skipped: never merged into it, never returned as an item of its own.
    A line at a SHALLOWER indent than the established level ends the
    scan (malformed input; degrade rather than raise)."""
    level = None
    i = start
    while i < end:
        line = lines[i]
        if not is_effective_structural(line):
            i += 1
            continue
        indent = line_indent(line)
        if level is None:
            level = indent
        if indent < level:
            break
        if indent == level:
            yield i, line.strip()
        i += 1


__all__ = [
    "find_block_end",
    "is_document_separator",
    "is_effective_structural",
    "is_structural_line",
    "line_indent",
    "match_key_header",
    "own_level_lines",
    "strip_inline_comment",
    "strip_yaml_quotes",
]
