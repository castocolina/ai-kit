"""Comment-keeping TOML edits for ai-kit's config files (D-08).

Each operation changes only the lines it owns and re-parses its result with tomllib; it raises
SpliceError rather than return text whose parsed value differs from the intended document.
"""

import copy
import itertools
import math
import os
import re
import stat
import tomllib
from typing import NamedTuple

from ai_kit_spec.cache import cache_write_bytes

_MAX_SPAN_LINES = 400
_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")
_ESCAPES = {
    "\\": "\\\\", '"': '\\"', "\b": "\\b", "\t": "\\t", "\n": "\\n", "\f": "\\f", "\r": "\\r",
}


class SpliceError(ValueError):
    """A write that cannot be made to parse back to the intended document."""


class Span(NamedTuple):
    """One `key = value` statement of a block; start and end are line indexes, end exclusive."""

    key: tuple
    start: int
    end: int
    value: object


class Block(NamedTuple):
    """A table or array-of-tables entry: its leading comments, header and body lines."""

    path: tuple
    array: bool
    lines: list
    lead: int
    spans: list


# ── Values ───────────────────────────────────────────────────────────────


def toml_key(name: str) -> str:
    """A bare key when the name allows one, otherwise a quoted key."""
    return name if _NAME_RE.fullmatch(name) else toml_value(name)


def toml_value(value) -> str:
    """The TOML text of a Python value. bool is tested before int; NaN and infinity are refused."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _float_text(value)
    if isinstance(value, str):
        return _basic_string(value)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return _inline_table(value)
    raise SpliceError(f"unsupported TOML value type: {type(value).__name__}")


def _float_text(value: float) -> str:
    if math.isnan(value) or math.isinf(value):
        raise SpliceError("nan and infinity have no TOML form in this writer")
    return repr(value)


def _inline_table(table: dict) -> str:
    if not table:
        return "{}"
    pairs = ", ".join(f"{toml_key(key)} = {toml_value(item)}" for key, item in table.items())
    return "{ " + pairs + " }"


def _basic_string(text: str) -> str:
    out = []
    for char in text:
        if char in _ESCAPES:
            out.append(_ESCAPES[char])
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            out.append(f"\\u{ord(char):04X}")
        else:
            out.append(char)
    return '"' + "".join(out) + '"'


def _key_line(name: str, value, indent: str, nl: str) -> str:
    return indent + toml_key(name) + " = " + toml_value(value) + nl


# ── Text helpers ─────────────────────────────────────────────────────────


def _split_lines(text: str) -> list:
    return [part for part in re.split(r"(?<=\n)", text) if part]


def _newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _with_eol(text: str) -> str:
    if text and not text.endswith("\n"):
        return text + _newline(text)
    return text


def _parse(text: str) -> dict:
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise SpliceError(f"not valid TOML: {exc}") from exc


def _verify(result: str, expected: dict) -> None:
    try:
        parsed = tomllib.loads(result)
    except tomllib.TOMLDecodeError as exc:
        raise SpliceError("splice result does not match the intended document") from exc
    if parsed != expected:
        raise SpliceError("splice result does not match the intended document")


def _indent(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


# ── Scanning: spans (key = value statements) and table headers ───────────


def _key_text(line: str):
    """The text before the first `=` that is outside quotes, or None."""
    quote = None
    index = 0
    while index < len(line):
        char = line[index]
        if quote == '"':
            if char == "\\":
                index += 1
            elif char == '"':
                quote = None
        elif quote == "'":
            if char == "'":
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "=":
            return line[:index]
        index += 1
    return None


def _leaf_path(parsed: dict) -> tuple:
    """Walk a one-key-per-level document (`a.b = 0` gives ('a', 'b'))."""
    path = []
    node = parsed
    while isinstance(node, dict) and len(node) == 1:
        key, node = next(iter(node.items()))
        path.append(key)
    return tuple(path)


def _value_at(parsed: dict, key: tuple):
    node = parsed
    for name in key:
        node = node[name]
    return node


def _find_close(text: str, start: int):
    """Index of the first `]` outside a double-quoted string, or None."""
    in_string = False
    index = start
    while index < len(text):
        char = text[index]
        if in_string:
            if char == "\\":
                index += 1
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "]":
            return index
        index += 1
    return None


def _header_path(line: str, number: int) -> tuple:
    stripped = line.strip()
    inner_start = 2 if stripped.startswith("[[") else 1
    close = _find_close(stripped, inner_start)
    message = f"line {number}: cannot parse this table header"
    if close is None:
        raise SpliceError(message)
    try:
        parsed = tomllib.loads(stripped[inner_start:close] + " = 0")
    except tomllib.TOMLDecodeError as exc:
        raise SpliceError(message) from exc
    return _leaf_path(parsed)


def _read_span(lines: list, index: int):
    """The statement starting at lines[index]: (end, key, value), grown until it parses."""
    message = f"line {index + 1}: cannot parse the value of this key"
    key_text = _key_text(lines[index])
    if key_text is None:
        raise SpliceError(message)
    try:
        key = _leaf_path(tomllib.loads(key_text + " = 0"))
    except tomllib.TOMLDecodeError as exc:
        raise SpliceError(message) from exc
    for end in range(index + 1, min(len(lines), index + _MAX_SPAN_LINES) + 1):
        try:
            parsed = tomllib.loads("".join(lines[index:end]))
        except tomllib.TOMLDecodeError:
            continue
        try:
            return end, key, _value_at(parsed, key)
        except (KeyError, TypeError) as exc:
            raise SpliceError(message) from exc
    raise SpliceError(message)


def _scan(lines: list):
    """Statement spans as (start, end, key, value) and headers as (index, path, array)."""
    spans = []
    headers = []
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped or stripped.startswith("#"):
            index += 1
        elif stripped.startswith("["):
            array = stripped.startswith("[[")
            headers.append((index, _header_path(lines[index], index + 1), array))
            index += 1
        else:
            end, key, value = _read_span(lines, index)
            spans.append((index, end, key, value))
            index = end
    return spans, headers


def _lead_start(lines: list, spans: list, headers: list, number: int) -> int:
    """First line of a header's block: the contiguous comment lines directly above it."""
    head = headers[number][0]
    floor = 0
    for _start, end, _key, _value in spans:
        if end <= head:
            floor = max(floor, end)
    if number:
        floor = max(floor, headers[number - 1][0] + 1)
    first = head
    while first > floor and lines[first - 1].strip().startswith("#"):
        first -= 1
    return first


def _trailer_start(lines: list):
    """Index of the first line of a section comment that closes `lines`: a comment group that
    follows a blank line after the last statement and is not directly above the next header
    (WR-02). It belongs to the next table, so a removal keeps it and a new entry goes before it.
    None when there is no such group."""
    end = len(lines)
    while end and (not lines[end - 1].strip() or lines[end - 1].strip().startswith("#")):
        end -= 1
    at = end
    while at < len(lines) and lines[at].strip().startswith("#"):
        at += 1  # comments right under the last statement stay with it
    blank = at
    while at < len(lines) and not lines[at].strip():
        at += 1
    return at if blank < at < len(lines) else None


def _trailer(lines: list) -> list:
    at = _trailer_start(lines)
    return [] if at is None else lines[at:]


def _block_spans(spans: list, start: int, stop: int) -> list:
    """The spans that start inside [start, stop), with indexes relative to start."""
    inside = [(s, e, key, value) for s, e, key, value in spans if start <= s < stop]
    return [Span(key, s - start, e - start, value) for s, e, key, value in inside]


def split_blocks(text: str) -> list:
    """The root block (always first, possibly empty) and one block per table header.

    The blocks cover the text in order: joining their lines gives the text back.
    """
    lines = _split_lines(text)
    spans, headers = _scan(lines)
    heads = [_lead_start(lines, spans, headers, number) for number in range(len(headers))]
    limits = [*heads, len(lines)]
    blocks = [Block((), False, lines[: limits[0]], 0, _block_spans(spans, 0, limits[0]))]
    for number, (head, path, array) in enumerate(headers):
        start, stop = heads[number], limits[number + 1]
        body = lines[start:stop]
        blocks.append(Block(path, array, body, head - start, _block_spans(spans, start, stop)))
    return blocks


# ── Editing one block ────────────────────────────────────────────────────


def _insert_at(block: Block) -> int:
    """Where a new key line goes: after the last span, else after the header, else after the
    last non-blank root line."""
    if block.spans:
        return block.spans[-1].end
    if block.path:
        return block.lead + 1
    last = 0
    for index, line in enumerate(block.lines):
        if line.strip():
            last = index + 1
    return last


def _span_edits(block: Block, old: dict, new: dict, nl: str):
    """Lines to drop, and lines to emit before a line index, for the spans the block owns."""
    drop = set()
    before = {}
    replaced = set()
    for span in block.spans:
        name = span.key[0]
        if name not in old and name not in new:
            continue
        if name in old and name in new and old[name] == new[name]:
            continue
        drop.update(range(span.start, span.end))
        if name in new and name not in replaced:
            replaced.add(name)
            indent = _indent(block.lines[span.start])
            before.setdefault(span.start, []).append(_key_line(name, new[name], indent, nl))
    return drop, before


def _apply_edits(lines: list, drop: set, before: dict) -> list:
    out = []
    for index, line in enumerate(lines):
        out.extend(before.get(index, []))
        if index not in drop:
            out.append(line)
    out.extend(before.get(len(lines), []))
    return out


def _edit_block(block: Block, old: dict, new: dict, nl: str) -> list:
    """The block's lines with its own keys changed from `old` to `new` (both hold the keys the
    block writes itself; child tables are left out by the caller).

    A key whose value changed is rewritten on its own line; a key gone from `new` loses its
    lines; a key new to the block is added after its last key line. Spans of keys in neither
    dict belong to a child block and are kept as they are.
    """
    drop, before = _span_edits(block, old, new, nl)
    owned = {span.key[0] for span in block.spans}
    extra = [_key_line(name, value, "", nl) for name, value in new.items() if name not in owned]
    if extra:
        before.setdefault(_insert_at(block), []).extend(extra)
    return _apply_edits(block.lines, drop, before)


def _walk_dict(root: dict, names: tuple):
    node = root
    for name in names:
        if not isinstance(node, dict) or name not in node:
            return None
        node = node[name]
    return node if isinstance(node, dict) else None


def _child_keys(paths: list, prefix: tuple) -> set:
    return {p[len(prefix)] for p in paths if len(p) > len(prefix) and p[: len(prefix)] == prefix}


def _ensure_table(tree: dict, path: tuple) -> dict:
    node = tree
    for name in path:
        child = node.get(name)
        if not isinstance(child, dict):
            child = {}
            node[name] = child
        node = child
    return node


def _table_index(blocks: list, path: tuple):
    for index, block in enumerate(blocks):
        if not block.array and block.path == path:
            return index
    return None


def _join(blocks: list, replaced: dict) -> str:
    out = []
    for index, block in enumerate(blocks):
        out.extend(replaced.get(index, block.lines))
    return "".join(out)


def _refuse_table_arrays(values: dict) -> None:
    for name, value in values.items():
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            raise SpliceError(
                f"{name}: set_table writes inline values only; use set_array for arrays of tables")


def _new_table_text(text: str, path: tuple, values: dict, nl: str) -> str:
    head = "[" + ".".join(toml_key(name) for name in path) + "]" + nl
    body = [_key_line(name, value, "", nl) for name, value in values.items()]
    return (nl if text else "") + head + "".join(body)


def set_table(text: str, path: tuple, values: dict, remove: tuple = ()) -> str:
    """Set keys of the table at `path`; keys in `remove` go. Other tables keep their text.

    Returns `text` itself when the values already hold. A table with no header is appended at the
    end of the file.
    """
    _refuse_table_arrays(values)
    original = text
    text = _with_eol(text)
    current = _parse(text)
    expected = copy.deepcopy(current)
    table = _ensure_table(expected, path)
    table.update(copy.deepcopy(values))
    for name in remove:
        table.pop(name, None)
    if expected == current:
        return original
    result = _splice_table(text, path, values, current, table)
    _verify(result, expected)
    return result


def _splice_table(text: str, path: tuple, values: dict, current: dict, table: dict) -> str:
    blocks = split_blocks(text)
    nl = _newline(text)
    index = _table_index(blocks, path)
    if index is None:
        return text + _new_table_text(text, path, values, nl)
    child = _child_keys([block.path for block in blocks], path)
    old = {k: v for k, v in (_walk_dict(current, path) or {}).items() if k not in child}
    # A child key (a sub-table or an array of tables, e.g. [[lanes.review]] under [lanes]) lives in
    # its own blocks, so the parent block never writes it, whatever its value.
    new = {k: v for k, v in table.items() if k not in child}
    return _join(blocks, {index: _edit_block(blocks[index], old, new, nl)})


# ── Arrays of tables and table removal ───────────────────────────────────


class _ArrayPlan(NamedTuple):
    path: tuple
    old: list
    entries: list
    pairs: list
    groups: list
    nl: str


def _array_entries(tree: dict, path: tuple) -> list:
    node = tree
    for name in path:
        if not isinstance(node, dict) or name not in node:
            return []
        node = node[name]
    return node if isinstance(node, list) else []


def _is_under(child: tuple, parent: tuple) -> bool:
    return len(child) > len(parent) and child[: len(parent)] == parent


def _array_groups(blocks: list, path: tuple) -> list:
    """Each entry of the array at `path` as the block indexes it spans: its own [[path]] block,
    then the blocks right after it that sit under `path` (sub-tables, nested arrays)."""
    groups = []
    index = 0
    while index < len(blocks):
        if not (blocks[index].array and blocks[index].path == path):
            index += 1
            continue
        members = [index]
        index += 1
        while index < len(blocks) and _is_under(blocks[index].path, path):
            members.append(index)
            index += 1
        groups.append(members)
    return groups


def _match_value(entry, match: str):
    value = entry.get(match) if isinstance(entry, dict) else None
    return value if isinstance(value, str) else None


def _unique_strings(keys: list) -> bool:
    return all(isinstance(key, str) for key in keys) and len(set(keys)) == len(keys)


def _pair_entries(old: list, new: list, match: str) -> list:
    """For each new entry, the index of the old entry it stands for, or None when it is new.

    Entries pair by their unique string `match` value; without that, by position.
    """
    old_keys = [_match_value(entry, match) for entry in old]
    new_keys = [_match_value(entry, match) for entry in new]
    if _unique_strings(old_keys) and _unique_strings(new_keys):
        position = {key: index for index, key in enumerate(old_keys)}
        return [position.get(key) for key in new_keys]
    return [index if index < len(old) else None for index in range(len(new))]


def _render_entry(path: tuple, entry: dict, nl: str) -> list:
    head = "[[" + ".".join(toml_key(name) for name in path) + "]]" + nl
    return [head] + [_key_line(name, value, "", nl) for name, value in entry.items()]


def _put_value(tree: dict, path: tuple, value) -> None:
    _ensure_table(tree, path[:-1])[path[-1]] = value


def _remove_path(tree: dict, path: tuple, blocks: list) -> None:
    """Pop the value at `path`. An ancestor table left empty goes too, unless a header names it."""
    chain = [tree]
    for name in path[:-1]:
        node = chain[-1].get(name)
        if not isinstance(node, dict):
            return
        chain.append(node)
    if path[-1] not in chain[-1]:
        return
    del chain[-1][path[-1]]
    for depth in range(len(path) - 1, 0, -1):
        if chain[depth] or any(block.path == path[:depth] for block in blocks):
            break
        del chain[depth - 1][path[depth - 1]]


def _old_own(node: dict, child: set) -> dict:
    return {key: value for key, value in node.items() if key not in child}


def _new_own(node: dict, child: set) -> dict:
    """The keys a block writes itself: a child key whose new value is a table lives in its own
    block, so it is left out here."""
    return {key: value for key, value in node.items()
            if not (key in child and isinstance(value, dict))}


def _edit_kept_block(group: list, rels: list, index: int, entries: tuple, nl: str) -> list:
    old_entry, new_entry = entries
    rel = rels[index]
    child = _child_keys(rels, rel)
    old_node = _walk_dict(old_entry, rel) or {}
    new_node = _walk_dict(new_entry, rel) or {}
    return _edit_block(group[index], _old_own(old_node, child), _new_own(new_node, child), nl)


def _implicit_prefixes(kept_rels: list, rels: list) -> list:
    """Proper prefixes of kept block paths that have no block of their own (`extra` when only
    `extra.tuning` has a block), shortest first."""
    found = set()
    for rel in kept_rels:
        for size in range(1, len(rel)):
            if rel[:size] not in rels:
                found.add(rel[:size])
    return sorted(found, key=lambda prefix: (len(prefix), prefix))


def _implicit_inserts(path: tuple, rels: list, kept: list, entries: tuple, nl: str) -> dict:
    """Header-and-key lines for implicit tables that gained keys, keyed by the kept block that
    they go directly before."""
    old_entry, new_entry = entries
    inserts = {}
    for prefix in _implicit_prefixes([rels[index] for index in kept], rels):
        child = _child_keys(rels, prefix)
        old_direct = _old_own(_walk_dict(old_entry, prefix) or {}, child)
        new_direct = _new_own(_walk_dict(new_entry, prefix) or {}, child)
        if old_direct == new_direct:
            continue
        if old_direct:
            raise SpliceError(
                f"{'.'.join(path + prefix)}: keys of an implicit table set through dotted keys "
                "are not edited; edit it by hand")
        anchor = next(index for index in kept if rels[index][: len(prefix)] == prefix)
        head = "[" + ".".join(toml_key(name) for name in path + prefix) + "]" + nl
        lines = [head] + [_key_line(key, value, "", nl) for key, value in new_direct.items()]
        inserts.setdefault(anchor, []).extend(lines)
    return inserts


def _edit_group(group: list, path: tuple, old_entry: dict, new_entry: dict, nl: str) -> list:
    """The lines of one changed entry, edited block by block so its comments survive (C1-1)."""
    if any(block.array and len(block.path) > len(path) for block in group):
        raise SpliceError(
            f"{'.'.join(path)}: an entry holding a nested array of tables is not edited; "
            "edit it by hand")
    rels = [block.path[len(path):] for block in group]
    kept = [index for index, rel in enumerate(rels)
            if not rel or _walk_dict(new_entry, rel) is not None]
    entries = (old_entry, new_entry)
    edited = {index: _edit_kept_block(group, rels, index, entries, nl) for index in kept}
    inserts = _implicit_inserts(path, rels, kept, entries, nl)
    out = []
    for index in kept:
        out.extend(inserts.get(index, []))
        out.extend(edited[index])
    return out


def _group_results(blocks: list, plan: _ArrayPlan) -> tuple:
    """(the lines each old group keeps, the section comments of removed groups): a group's text
    when unchanged, edited lines when changed, none when its entry is gone from the list; a gone
    entry's closing section comment stays (WR-02)."""
    new_of_old = {old: new for new, old in enumerate(plan.pairs) if old is not None}
    results = {}
    kept = {}
    for old_index, members in enumerate(plan.groups):
        if old_index not in new_of_old:
            results[old_index] = []
            kept[old_index] = _trailer(blocks[members[-1]].lines)
            continue
        group = [blocks[index] for index in members]
        old_entry = plan.old[old_index]
        new_entry = plan.entries[new_of_old[old_index]]
        if old_entry == new_entry:
            results[old_index] = [line for block in group for line in block.lines]
        else:
            results[old_index] = _edit_group(group, plan.path, old_entry, new_entry, plan.nl)
    return results, kept


def _append_pieces(lines: list, pieces: list, nl: str) -> list:
    """Append each piece, with a blank line between it and what precedes it."""
    for piece in pieces:
        if lines and lines[-1].strip():
            lines.append(nl)
        lines.extend(piece)
    return lines


def _keeps_order(pairs: list) -> bool:
    matched = [old for old in pairs if old is not None]
    return all(before < after for before, after in itertools.pairwise(matched))


def _place_new_entries(plan: _ArrayPlan, rendered: list) -> tuple:
    """Order kept: a new entry goes directly before the group of the next kept entry, or after the
    last old group when no kept entry follows it. Returns (lines before group, trailing entries)."""
    before = {}
    tails = []
    for new, old in enumerate(plan.pairs):
        if old is not None:
            continue
        following = [plan.pairs[later] for later in range(new + 1, len(plan.pairs))
                     if plan.pairs[later] is not None]
        if following:
            before.setdefault(following[0], []).extend(rendered[new] + [plan.nl])
        else:
            tails.append(rendered[new])
    return before, tails


def _reorder(plan: _ArrayPlan, results: dict, rendered: list) -> dict:
    """Order changed: every entry is written contiguously in the new order, at the position of the
    first old group; the other old groups are emptied."""
    pieces = [results[old] if old is not None else rendered[new]
              for new, old in enumerate(plan.pairs)]
    emptied = {index: [] for index in results}
    emptied[0] = _append_pieces([], pieces, plan.nl)
    return emptied


def _assemble(blocks: list, groups: list, results: dict, before: dict, kept: dict) -> list:
    first = {members[0]: group for group, members in enumerate(groups)}
    inside = {index for members in groups for index in members}
    out = []
    for index, block in enumerate(blocks):
        if index in first:
            out.extend(before.get(first[index], []))
            out.extend(results[first[index]])
            out.extend(kept.get(first[index], []))
        elif index not in inside:
            out.extend(block.lines)
    return out


def _array_lines(blocks: list, plan: _ArrayPlan) -> list:
    rendered = [_render_entry(plan.path, entry, plan.nl) for entry in plan.entries]
    results, kept = _group_results(blocks, plan)
    if not _keeps_order(plan.pairs):
        return _assemble(blocks, plan.groups, _reorder(plan, results, rendered), {}, {})
    before, tails = _place_new_entries(plan, rendered)
    if plan.groups:
        last = len(plan.groups) - 1
        results[last] = _append_before_trailer(results[last], tails, plan.nl)
        tails = []
    out = _assemble(blocks, plan.groups, results, before, kept)
    return _append_pieces(out, tails, plan.nl)


def _append_before_trailer(lines: list, pieces: list, nl: str) -> list:
    """`_append_pieces`, but ahead of a closing section comment, with a blank line before it."""
    at = _trailer_start(lines)
    if at is None or not pieces:
        return _append_pieces(lines, pieces, nl)
    return [*_append_pieces(lines[:at], pieces, nl), nl, *lines[at:]]


def set_array(text: str, path: tuple, entries: list, match: str = "key") -> str:
    """Replace the array of tables at `path` with `entries`, entry by entry.

    An unchanged entry keeps its text; a changed one is edited block by block; a new entry lands
    where it belongs in the order; an entry gone takes its header, body and comments with it.
    Empty `entries` removes the array. Returns `text` itself when nothing changes.
    """
    original = text
    text = _with_eol(text)
    current = _parse(text)
    expected = copy.deepcopy(current)
    blocks = split_blocks(text)
    if entries:
        _put_value(expected, path, copy.deepcopy(entries))
    else:
        _remove_path(expected, path, blocks)
    if expected == current:
        return original
    old = _array_entries(current, path)
    groups = _array_groups(blocks, path)
    if len(groups) != len(old):
        raise SpliceError(f"{'.'.join(path)}: the array does not match its table blocks")
    pairs = _pair_entries(old, entries, match)
    plan = _ArrayPlan(path, old, entries, pairs, groups, _newline(text))
    result = "".join(_array_lines(blocks, plan))
    _verify(result, expected)
    return result


def remove_table(text: str, path: tuple) -> str:
    """Drop the table at `path` with every block under it; other tables keep their text."""
    original = text
    text = _with_eol(text)
    current = _parse(text)
    expected = copy.deepcopy(current)
    blocks = split_blocks(text)
    _remove_path(expected, path, blocks)
    if expected == current:
        return original
    def under(index: int) -> bool:
        return index < len(blocks) and blocks[index].path[: len(path)] == path

    # The last dropped block of a run keeps its closing section comment (WR-02).
    dropped = {index: [] if under(index + 1) else _trailer(blocks[index].lines)
               for index in range(len(blocks)) if under(index)}
    result = _join(blocks, dropped)
    _verify(result, expected)
    return result


# ── Publishing ───────────────────────────────────────────────────────────


def publish(path: str, text: str) -> None:
    """Write `text` to `path` atomically, after checking that it parses as TOML.

    The temp file lives in the target folder; a symlink stays a link (its target is written);
    an existing file keeps its mode, a new one gets 0600.
    """
    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise SpliceError(f"refusing to publish invalid TOML: {exc}") from exc
    real = os.path.realpath(path)
    mode = stat.S_IMODE(os.stat(real).st_mode) if os.path.isfile(real) else 0o600
    cache_write_bytes(real, text.encode("utf-8"), mode=mode)
