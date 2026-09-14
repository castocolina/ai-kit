"""The single place this skill reads a target repo's tool-configuration
files (11-CONTEXT, Phase 11 Plan 03). One function per format, and NONE of
them raise for any input -- every reader in this module degrades to
`NOT_READABLE` on a decode error, an OS error, a non-mapping top level, or
any shape it does not understand (T-11-13).

Every configuration file this module reads comes from an untrusted target
repo. TOML and JSON are parsed with the standard library. The YAML subset
is scanned with anchored per-line regexes (this repository carries no YAML
parser and is not adding one -- AGENTS.md's hand-rolled-scanner precedent).
The one XML-shaped configuration this skill's checks read (a PMD ruleset)
is scanned with a LINE REGEX by its own caller in `enable_everything.py`,
never here and never with an XML parser: the standard library's XML
parsers expand entities from the document by default, which is a
denial-of-service surface on untrusted input, and nothing this skill
detects is worth opening it (T-11-14).

`read_yaml_value`'s documented contract (a CONTRACT, not an illustration):
it reads a scalar (`key: value`), an inline list (`key: [a, b]`), and a
BLOCK SEQUENCE (the key on its own line followed by more-indented `- item`
lines, terminated by the first line at or below the key's own indentation)
at a known, nested key path. It does NOT understand anchors and aliases,
multi-document files, block scalar folding (`>` / `|`), nested mappings
inside a sequence item, or flow mappings -- any of those shapes, or a key
path it cannot locate at all, returns `NOT_READABLE` rather than a partial
guess, so a caller can tell "absent" from "present but beyond this
reader". Concretely, the golangci configuration this phase reads carries
`linters.enable-all` as a scalar but `linters.enable` and `linters.disable`
as block sequences in idiomatic use -- all three key paths are this
reader's contract.
"""

from __future__ import annotations

import json
import os
import re
import tomllib


class _NotReadable:
    """Sentinel type for 'this reader could not statically read this
    input' -- distinct from any real parsed value (including an empty
    string or an empty list), so a caller can tell absent/malformed apart
    from a legitimately empty result."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "<config not statically readable>"

    def __bool__(self) -> bool:
        return False


NOT_READABLE = _NotReadable()


def read_toml(path: str):
    """Parse `path` as TOML. Returns the parsed mapping, or `NOT_READABLE`
    for a missing file, an OS error, a decode error, or a non-mapping top
    level (T-11-13). Never raises."""
    if not os.path.isfile(path):
        return NOT_READABLE
    try:
        with open(path, "rb") as handle:
            data = tomllib.load(handle)
    except (OSError, ValueError):
        return NOT_READABLE
    if not isinstance(data, dict):
        return NOT_READABLE
    return data


def read_json(path: str):
    """Parse `path` as JSON. Same contract as `read_toml`: `NOT_READABLE`
    for a missing file, an OS error, a decode error, or a non-mapping top
    level. Never raises."""
    if not os.path.isfile(path):
        return NOT_READABLE
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return NOT_READABLE
    if not isinstance(data, dict):
        return NOT_READABLE
    return data


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _extract_scoped_value(lines: list[str], key_idx: int, key_indent: int, trailing: str):
    """`trailing` is the text (if any) already found on the key's own
    line. Non-empty trailing -> scalar or inline list (this function
    decides which). Empty trailing -> look for a block sequence on the
    following more-indented lines."""
    if trailing:
        if trailing.startswith("["):
            if not trailing.endswith("]"):
                return NOT_READABLE
            inner = trailing[1:-1]
            items = [_strip_quotes(part.strip()) for part in inner.split(",") if part.strip()]
            return items
        return _strip_quotes(trailing)

    items: list[str] = []
    idx = key_idx + 1
    while idx < len(lines):
        raw = lines[idx]
        if raw.strip() == "":
            idx += 1
            continue
        if _indent_of(raw) <= key_indent:
            break
        stripped = raw.strip()
        item_match = re.match(r"^-\s*(.*)$", stripped)
        if item_match is None:
            # A shape this reader does not understand (e.g. a nested
            # mapping under the key) -- degrade rather than guess.
            return NOT_READABLE
        item = item_match.group(1).strip()
        if not item:
            return NOT_READABLE
        items.append(_strip_quotes(item))
        idx += 1
    if not items:
        return NOT_READABLE
    return items


def _scope_for_key(lines: list[str], start: int, end: int, base_indent: int, key: str):
    """Search `lines[start:end]` (all at indent strictly greater than
    `base_indent`) for a line whose stripped text is `key:` plus optional
    trailing content. Returns `(index, indent, trailing)` or `None`."""
    pattern = re.compile(rf"^{re.escape(key)}:\s*(.*)$")
    for idx in range(start, end):
        raw = lines[idx]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = _indent_of(raw)
        if indent <= base_indent:
            continue
        match = pattern.match(stripped)
        if match is None:
            continue
        return idx, indent, match.group(1).strip()
    return None


def read_yaml_value(path: str, key_path: tuple[str, ...]):
    """Read the value at `key_path` (a tuple of nested keys, outermost
    first) from the YAML subset at `path`. Returns a scalar string, a list
    of strings (inline list or block sequence), or `NOT_READABLE` -- see
    this module's docstring for the exact three shapes understood and the
    shapes deliberately not. Never raises."""
    if not key_path:
        return NOT_READABLE
    if not os.path.isfile(path):
        return NOT_READABLE
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeError):
        return NOT_READABLE

    lines = text.splitlines()
    start, end, base_indent = 0, len(lines), -1

    for depth, key in enumerate(key_path):
        located = _scope_for_key(lines, start, end, base_indent, key)
        if located is None:
            return NOT_READABLE
        key_idx, key_indent, trailing = located
        if depth == len(key_path) - 1:
            return _extract_scoped_value(lines, key_idx, key_indent, trailing)
        new_start = key_idx + 1
        new_end = new_start
        while new_end < end:
            raw = lines[new_end]
            if raw.strip() == "":
                new_end += 1
                continue
            if _indent_of(raw) <= key_indent:
                break
            new_end += 1
        start, end, base_indent = new_start, new_end, key_indent

    return NOT_READABLE


def read_config_value(path: str, key_path: tuple[str, ...]):
    """Format-dispatching sibling of `read_yaml_value`: picks the reader
    by `path`'s extension (`.yml`/`.yaml` -> `read_yaml_value`,
    `.toml`/`.json` -> the whole-document reader followed by a plain
    mapping descent), then returns the value at `key_path` or
    `NOT_READABLE`. Used where a single ecosystem's candidate configs span
    more than one format (e.g. golangci's four conventional extensions),
    so a caller needs one call regardless of which candidate matched."""
    if path.endswith((".yml", ".yaml")):
        return read_yaml_value(path, key_path)
    if path.endswith(".toml"):
        parsed = read_toml(path)
    elif path.endswith(".json"):
        parsed = read_json(path)
    else:
        return NOT_READABLE
    if parsed is NOT_READABLE:
        return NOT_READABLE
    current = parsed
    for key in key_path:
        if not isinstance(current, dict) or key not in current:
            return NOT_READABLE
        current = current[key]
    return current


def first_existing_candidate(repo_root: str, candidates: tuple[str, ...], reader):
    """D-C1's shared discovery helper: try `candidates` (repo-relative
    paths) IN ORDER, and return `(repo_relative_path, reader(absolute_path))`
    for the first one that exists as a file. Returns `(None, NOT_READABLE)`
    if none exist. `reader` is a function of one absolute path -- one of
    this module's whole-document readers for a single-format ecosystem, or
    a small per-caller dispatcher (see `enable_everything.py`'s Go row,
    whose candidates span more than one format and whose marker predicate
    re-reads a specific key path via `read_config_value` rather than a
    generic whole-document parse a YAML candidate cannot support here).

    Existence-only: this function does not judge whether the matched file
    actually configures the thing being searched for. 'First file found
    per ecosystem wins' (D-C1) -- absence of every candidate is what means
    the ecosystem's checks do not apply, never a look-past-content probe
    that would need its own degrade-not-crash contract."""
    for rel in candidates:
        abs_path = os.path.join(repo_root, rel)
        if os.path.isfile(abs_path):
            return rel, reader(abs_path)
    return None, NOT_READABLE


__all__ = [
    "NOT_READABLE",
    "first_existing_candidate",
    "read_config_value",
    "read_json",
    "read_toml",
    "read_yaml_value",
]
