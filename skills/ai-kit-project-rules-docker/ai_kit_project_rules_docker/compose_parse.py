"""Indentation-aware, stdlib-only `docker-compose.yml` reader (D-01/D-02,
D-D6/D-D7).

This is a narrow reader of one well-known document shape -- a Compose
file's `services:` mapping and the `healthcheck:`/`depends_on:` blocks
nested under each service -- built on an indentation-aware text scan
rather than a flat line-scan, because a flat scan cannot attribute a
nested block to its OWNING service (13-CONTEXT D-01): `healthcheck:` and
`depends_on:` sit deeper than a service name and must never be mistaken
for one, and two services in the same file can declare the same nested
key with different values. It is NOT a YAML implementation, and two
limits follow from that on purpose, stated here in the same voice so a
later reader sees them as scope rather than as bugs to fix:

  - YAML forbids tab indentation. A tab-indented file may therefore be
    MIS-ATTRIBUTED (a block owned by the wrong service, or missed
    entirely) rather than rejected outright -- this parser measures
    indentation as a raw whitespace-CHARACTER count (`yaml_text.
    line_indent`), never a tab-to-column conversion, and never raises on
    a tab-indented input.
  - A same-line FLOW-MAPPING body (`healthcheck: {interval: 30s}`,
    `depends_on: {db: {condition: service_healthy}}`) is OUT OF SCOPE
    and is NOT read at all: `block_subblock` and `block_mapping_keys`
    return `None`/`[]` for such a key, so the owning service is neither
    flagged nor confirmed conforming. This parser never lets a
    flow-mapping value swallow the block boundary of the service defined
    after it -- that is the difference between this stated gap and a
    parser bug.

Every public function degrades: no input raises, and an unreadable or
malformed file yields an empty/`None` result rather than a crash.

`block_sequence`'s own docstring states a THIRD, related limit (D-D7):
it returns SCALAR items only. A YAML sequence-of-mappings entry (a
long-form `volumes:` bind mount, `- type: bind` / `source:` / `target:`)
arrives as the partial fragment of its own `- ` line, with its
continuation lines dropped rather than merged -- a stated reader
contract, not a parser bug, and plan 13-03's volume classifier is
required to treat that fragment as UNREADABLE rather than as an absent
bind mount.
"""

from __future__ import annotations

import os
import re

from ai_kit_rules_common.yaml_text import is_structural_line, line_indent, strip_yaml_quotes

# D-D6 -- ONE pair of filename tuples. `docker_checker.py`'s D-D4
# applicability-gate clause (i) and this module's own discovery functions
# both read these, never a second hand-written copy.
BASE_COMPOSE_FILENAMES = (
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
)

# 13-CONTEXT D-03's dedicated local-dev filename convention, defined here
# so plan 13-03 consumes it rather than re-deriving it.
LOCAL_DEV_COMPOSE_FILENAMES = (
    "docker-compose.override.yml",
    "docker-compose.override.yaml",
    "docker-compose.local.yml",
    "docker-compose.local.yaml",
)

_KEY_HEADER_RE = re.compile(r"^([^\s:#][^:]*):(.*)$")


def _lines(text: str) -> list[str]:
    return text.split("\n")


def _is_document_separator(line: str) -> bool:
    """A `---` document separator, skipped as structural noise rather
    than treated as a key (D-D7)."""
    return line.strip() == "---"


def _effective_structural(line: str) -> bool:
    """`is_structural_line` plus the `---` separator carve-out."""
    if not is_structural_line(line):
        return False
    return not _is_document_separator(line)


def _strip_inline_comment(text: str) -> str:
    """Truncate `text` at the first UNQUOTED `#`. Never raises."""
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


def _match_key_header(content: str):
    """`content` is an already-stripped line. Returns `(key, rest)` or
    `None` if `content` is not a `key:` header line."""
    match = _KEY_HEADER_RE.match(content)
    if match is None:
        return None
    return match.group(1).strip(), match.group(2)


def _find_block_end(lines: list[str], start: int, ref_indent: int) -> int:
    """Index of the first effectively-structural line at index >= `start`
    whose indent is <= `ref_indent` -- the block-end rule: a block owned
    by a key at indent `ref_indent` runs from `start` until that line, or
    to `len(lines)` if none exists."""
    n = len(lines)
    i = start
    while i < n:
        line = lines[i]
        if _effective_structural(line) and line_indent(line) <= ref_indent:
            return i
        i += 1
    return n


def _own_level_lines(lines: list[str], start: int, end: int):
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
        if not _effective_structural(line):
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


def _find_own_key(lines: list[str], start: int, end: int, key: str):
    """Search the own-level lines of `lines[start:end]` for a `key:`
    header matching `key` by exact (quote-stripped) name. Returns
    `(line_index, indent, rest)` or `None`."""
    for idx, content in _own_level_lines(lines, start, end):
        parsed = _match_key_header(content)
        if parsed is None:
            continue
        name, rest = parsed
        if strip_yaml_quotes(name.strip()) == key:
            return idx, line_indent(lines[idx]), rest
    return None


def _parse_flow_sequence(value: str) -> list[str]:
    """`[a, b, "c"]` -> `['a', 'b', 'c']`. No nested-bracket support --
    that is the YAML implementation D-01 exists to avoid; this handles
    exactly the flat scalar-item flow sequences Compose's `depends_on`/
    `volumes` shorthand actually uses."""
    inner = value.strip()
    if inner.startswith("["):
        inner = inner[1:]
    close = inner.rfind("]")
    if close != -1:
        inner = inner[:close]
    parts = [p.strip() for p in inner.split(",")]
    return [strip_yaml_quotes(p) for p in parts if p.strip()]


def discover_compose_files(repo_root: str) -> list[str]:
    """Existing ROOT-level files from BOTH `BASE_COMPOSE_FILENAMES` and
    `LOCAL_DEV_COMPOSE_FILENAMES`, base first, in tuple order. Absolute
    paths. Root-scoped, matching D-D4: no walk, no descending glob. Never
    raises."""
    found: list[str] = []
    for name in BASE_COMPOSE_FILENAMES + LOCAL_DEV_COMPOSE_FILENAMES:
        path = os.path.join(repo_root, name)
        if os.path.isfile(path):
            found.append(os.path.abspath(path))
    return found


def discover_local_dev_compose_files(repo_root: str) -> list[str]:
    """Existing ROOT-level files from `LOCAL_DEV_COMPOSE_FILENAMES` only
    -- plan 13-03's entry point. Absolute paths. Never raises."""
    found: list[str] = []
    for name in LOCAL_DEV_COMPOSE_FILENAMES:
        path = os.path.join(repo_root, name)
        if os.path.isfile(path):
            found.append(os.path.abspath(path))
    return found


def read_compose_text(path: str) -> str:
    """Read `path` as UTF-8 text; `""` on ANY read failure (missing file,
    permission error, invalid UTF-8) rather than raising. Both of this
    plan's checks route their file reads through this one function so a
    truncated, unreadable, or binary compose file degrades identically
    for each."""
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return ""


def iter_services(text: str):
    """Yield `(service_name, service_block_text)` for every key directly
    under a top-level `services:` mapping. `services:` is a top-level key
    at indent 0; the SERVICE indentation level is the indent of the
    first structural line inside the `services:` block, and only lines
    at exactly that indent matching a `name:` header are service names.
    Yields nothing for any input with no `services:` key. Never raises."""
    if not text:
        return
    lines = _lines(text)
    services_idx = None
    for i, line in enumerate(lines):
        if not _effective_structural(line):
            continue
        if line_indent(line) != 0:
            continue
        parsed = _match_key_header(line.strip())
        if parsed is None:
            continue
        name, rest = parsed
        if name.strip() != "services":
            continue
        if _strip_inline_comment(rest).strip():
            # `services: {...}` or similar inline value -- not the block
            # form this reader supports; keep scanning rather than
            # treating this as the real `services:` key.
            continue
        services_idx = i
        break
    if services_idx is None:
        return

    services_end = _find_block_end(lines, services_idx + 1, 0)
    headers = list(_own_level_lines(lines, services_idx + 1, services_end))
    for pos, (idx, content) in enumerate(headers):
        parsed = _match_key_header(content)
        if parsed is None:
            continue
        name, _rest = parsed
        service_name = strip_yaml_quotes(name.strip())
        next_idx = headers[pos + 1][0] if pos + 1 < len(headers) else services_end
        block_text = "\n".join(lines[idx + 1 : next_idx])
        yield service_name, block_text


def block_scalar(block_text: str | None, key: str) -> str | None:
    """The scalar value of `key:` at `block_text`'s own first nesting
    level, quotes stripped, or `None` when `key` is absent, has no
    same-line value, or that value is a flow form (`{...}`/`[...]`) --
    the case this reader hands to `block_subblock`/`block_sequence`
    instead. Never raises."""
    if not block_text:
        return None
    lines = _lines(block_text)
    found = _find_own_key(lines, 0, len(lines), key)
    if found is None:
        return None
    _, _, rest = found
    value = _strip_inline_comment(rest).strip()
    if not value:
        return None
    if value[0] in "{[":
        return None
    return strip_yaml_quotes(value)


def block_subblock(block_text: str | None, key: str) -> str | None:
    """The nested block text under `key:`, or `None` when `key` is
    absent OR carries a same-line value (a scalar or a flow-mapping body
    -- D-D7's stated flow-mapping limit lives here: `healthcheck:
    {interval: 30s}` returns `None`, never the `{...}` text mistaken for
    a block). `""` (not `None`) when `key:` is present with a bare colon
    and no nested lines follow -- a real, empty mapping is a different
    answer from "not found". Never raises."""
    if not block_text:
        return None
    lines = _lines(block_text)
    found = _find_own_key(lines, 0, len(lines), key)
    if found is None:
        return None
    idx, indent, rest = found
    if _strip_inline_comment(rest).strip():
        return None
    end = _find_block_end(lines, idx + 1, indent)
    return "\n".join(lines[idx + 1 : end])


def block_sequence(block_text: str | None, key: str) -> list[str]:
    """The items of a `key:` sequence in EITHER block form (`- item`
    lines) or flow form (`[a, b]`), quotes stripped, or `[]` when `key`
    is absent, has a non-sequence same-line value, or has no block-form
    items.

    SCALAR ITEMS ONLY (D-D7). An item is the text of a `- `-prefixed
    line at the sequence's own indent; a DEEPER continuation line
    beneath it is a child of the preceding item and is skipped -- never
    merged into that item, never returned as an item of its own. A YAML
    sequence-of-mappings entry -- `- type: bind` / `source: ./src` /
    `target: /app/src` -- therefore arrives as the single fragment
    `type: bind`, with its two continuation lines dropped. That is a
    stated limit of this reader: a consumer must treat a fragment it
    cannot parse under its OWN grammar as UNREADABLE rather than as a
    value, never as evidence that the sequence item is absent. Never
    raises."""
    if not block_text:
        return []
    lines = _lines(block_text)
    found = _find_own_key(lines, 0, len(lines), key)
    if found is None:
        return []
    idx, indent, rest = found
    value = _strip_inline_comment(rest).strip()
    if value:
        if value.startswith("["):
            return _parse_flow_sequence(value)
        return []
    end = _find_block_end(lines, idx + 1, indent)
    items: list[str] = []
    for _item_idx, content in _own_level_lines(lines, idx + 1, end):
        if not content.startswith("-"):
            continue
        item_text = content[1:].strip()
        items.append(strip_yaml_quotes(item_text))
    return items


def block_mapping_keys(block_text: str | None, key: str) -> list[str]:
    """The key names of a `key:` mapping, in file order, or `[]` when
    `key` is absent, has a same-line value (including a flow-mapping
    body), or has an empty body. Never raises."""
    sub = block_subblock(block_text, key)
    if not sub:
        return []
    lines = _lines(sub)
    names: list[str] = []
    for _idx, content in _own_level_lines(lines, 0, len(lines)):
        parsed = _match_key_header(content)
        if parsed is None:
            continue
        name, _rest = parsed
        names.append(strip_yaml_quotes(name.strip()))
    return names


__all__ = [
    "BASE_COMPOSE_FILENAMES",
    "LOCAL_DEV_COMPOSE_FILENAMES",
    "block_mapping_keys",
    "block_scalar",
    "block_sequence",
    "block_subblock",
    "discover_compose_files",
    "discover_local_dev_compose_files",
    "iter_services",
    "read_compose_text",
]
