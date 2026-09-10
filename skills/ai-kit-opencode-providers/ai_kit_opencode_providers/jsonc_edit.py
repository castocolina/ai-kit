"""Comment/string-aware JSONC surgical scanner.

Four mutually suppressing states: in-string, after-backslash-escape,
in-line-comment (`//` until newline), in-block-comment (`/*` until `*/`).
Brace depth changes only in none of those states. While in-string, `//` and
`/*` are ordinary string content and never open comment state; while in either
comment state, `"` is ordinary comment text and never opens string state; the
escape state applies only inside a string.

No recursive-descent parser. No regular expression for brace matching.
"""

from __future__ import annotations

import json
from typing import NamedTuple

KIND_CODE = "code"
KIND_STRING = "string"
KIND_COMMENT = "comment"


class ProviderEntry(NamedTuple):
    provider_id: str
    key_start: int
    value_start: int
    value_end: int


def _classify(text: str) -> list[str]:
    """Classify every character from offset 0 (neutral seed)."""
    n = len(text)
    kinds = [KIND_CODE] * n
    i = 0
    in_string = False
    escaped = False
    in_line = False
    in_block = False
    while i < n:
        c = text[i]
        if escaped:
            kinds[i] = KIND_STRING
            escaped = False
            i += 1
            continue
        if in_string:
            kinds[i] = KIND_STRING
            if c == "\\":
                escaped = True
            elif c == '"':
                in_string = False
            i += 1
            continue
        if in_line:
            kinds[i] = KIND_COMMENT
            if c == "\n":
                in_line = False
            i += 1
            continue
        if in_block:
            kinds[i] = KIND_COMMENT
            if c == "*" and i + 1 < n and text[i + 1] == "/":
                kinds[i + 1] = KIND_COMMENT
                in_block = False
                i += 2
                continue
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            kinds[i] = KIND_COMMENT
            kinds[i + 1] = KIND_COMMENT
            in_line = True
            i += 2
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            kinds[i] = KIND_COMMENT
            kinds[i + 1] = KIND_COMMENT
            in_block = True
            i += 2
            continue
        if c == '"':
            kinds[i] = KIND_STRING
            in_string = True
            i += 1
            continue
        kinds[i] = KIND_CODE
        i += 1
    return kinds


def _skip_insignificant(text: str, kinds: list[str], i: int, end: int) -> int:
    while i < end and (kinds[i] != KIND_CODE or text[i].isspace()):
        i += 1
    return i


def _string_end(kinds: list[str], start: int, end: int) -> int:
    i = start + 1
    while i < end and kinds[i] == KIND_STRING:
        i += 1
    return i


def _skip_value(text: str, kinds: list[str], start: int, end: int) -> int:
    """Advance past a JSONC value starting at `start`. Returns end_exclusive."""
    start = _skip_insignificant(text, kinds, start, end)
    if start >= end:
        return end
    kind = kinds[start]
    if kind == KIND_STRING:
        return _string_end(kinds, start, end)
    if kind != KIND_CODE:
        return start + 1
    c = text[start]
    if c in "{[":
        opener, closer = ("{", "}") if c == "{" else ("[", "]")
        depth = 0
        i = start
        while i < end:
            if kinds[i] == KIND_CODE:
                if text[i] == opener:
                    depth += 1
                elif text[i] == closer:
                    depth -= 1
                    if depth == 0:
                        return i + 1
            i += 1
        return end
    i = start
    while i < end:
        if kinds[i] != KIND_CODE or text[i].isspace() or text[i] in ",}]":
            break
        i += 1
    return i


def find_object_span(text: str, open_index: int) -> tuple[int, int]:
    """Return (start, end_exclusive) of the balanced object at open_index."""
    kinds = _classify(text)
    depth = 0
    n = len(text)
    for i in range(open_index, n):
        if kinds[i] != KIND_CODE:
            continue
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return (open_index, i + 1)
    return (open_index, n)


def find_provider_object(text: str) -> tuple[int, int] | None:
    """Span of the top-level `"provider"` value object, or None.

    The key is matched only while brace depth is exactly 1 relative to the
    document's outermost `{`. A nested `"provider"` key is never matched.
    """
    kinds = _classify(text)
    n = len(text)
    depth = 0
    i = 0
    while i < n:
        kind = kinds[i]
        if kind == KIND_CODE:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
            continue
        if kind == KIND_STRING and (i == 0 or kinds[i - 1] != KIND_STRING):
            str_end = _string_end(kinds, i, n)
            if depth == 1:
                key = text[i + 1 : str_end - 1]
                colon = _skip_insignificant(text, kinds, str_end, n)
                if colon < n and text[colon] == ":" and key == "provider":
                    value = _skip_insignificant(text, kinds, colon + 1, n)
                    if value < n and text[value] == "{":
                        return find_object_span(text, value)
            i = str_end
            continue
        i += 1
    return None


def _walk_provider_children(
    text: str,
) -> tuple[list[ProviderEntry], list[str]]:
    span = find_provider_object(text)
    if span is None:
        return [], []
    open_i, close_i = span
    kinds = _classify(text)
    entries: list[ProviderEntry] = []
    non_objects: list[str] = []
    depth = 0
    i = open_i
    while i < close_i:
        kind = kinds[i]
        if kind == KIND_CODE:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
            continue
        if kind == KIND_STRING and (i == 0 or kinds[i - 1] != KIND_STRING):
            str_end = _string_end(kinds, i, close_i)
            if depth == 1:
                key = text[i + 1 : str_end - 1]
                colon = _skip_insignificant(text, kinds, str_end, close_i)
                if colon < close_i and text[colon] == ":":
                    value = _skip_insignificant(text, kinds, colon + 1, close_i)
                    if value < close_i and text[value] == "{":
                        _vs, value_end = find_object_span(text, value)
                        entries.append(
                            ProviderEntry(key, i, value, value_end),
                        )
                        i = value_end
                        continue
                    if value < close_i:
                        non_objects.append(key)
                        i = _skip_value(text, kinds, value, close_i)
                        continue
            i = str_end
            continue
        i += 1
    return entries, non_objects


def iter_provider_entries(text: str) -> list[ProviderEntry]:
    """Immediate object-valued children of the top-level `"provider"` object.

    Depth 1 relative to the `"provider"` opening brace. A depth-1 child whose
    first significant character after `:` is not `{` is skipped, not yielded,
    and never a raise.
    """
    entries, _non = _walk_provider_children(text)
    return entries


def non_object_provider_keys(text: str) -> list[str]:
    """Depth-1 `"provider"` keys whose values are not objects, in file order."""
    _entries, non_objects = _walk_provider_children(text)
    return non_objects


def significant_indices(text: str, start: int, end: int) -> list[int]:
    """Non-whitespace, non-comment positions in `[start, end)`.

    Seed `start` at a position whose walker state is provably neutral — not
    in a string, not in a comment, not after an escape. The only seed this
    codebase uses is the `"provider"` object's opening brace, reached by
    walking from offset 0. Calling with an arbitrary mid-file `start` is
    out of contract.

    A non-whitespace character inside a quoted string IS significant: those
    bytes are real file content. This list answers "is this position comment
    or whitespace?", never "is this position in code state?".
    """
    kinds = _classify(text)
    out: list[int] = []
    for i in range(start, min(end, len(text))):
        if kinds[i] == KIND_COMMENT:
            continue
        if text[i].isspace():
            continue
        out.append(i)
    return out


def strip_jsonc_comments(text: str) -> str:
    """Replace comment characters with spaces; leave strings and code intact."""
    kinds = _classify(text)
    chars = list(text)
    for i, kind in enumerate(kinds):
        if kind == KIND_COMMENT and text[i] != "\n":
            chars[i] = " "
    return "".join(chars)


def code_indices(text: str, start: int, end: int) -> list[int]:
    """CODE-state, non-whitespace positions in `[start, end)`.

    Strict subset of `significant_indices`: excludes string interiors.
    Same neutral-seed precondition as `significant_indices`.
    """
    kinds = _classify(text)
    out: list[int] = []
    for i in range(start, min(end, len(text))):
        if kinds[i] != KIND_CODE:
            continue
        if text[i].isspace():
            continue
        out.append(i)
    return out


def strip_trailing_commas(text: str) -> str:
    """Replace trailing commas before `}` or `]` with a space.

    Both sides of the test use `code_indices` (walker CODE state), never
    membership in `significant_indices`. An in-string `,}` is left intact.
    Seeded at offset 0 of `text`, which callers pass as a balanced slice
    whose first character is the entry value's own `{`.
    """
    indices = code_indices(text, 0, len(text))
    chars = list(text)
    for pos, i in enumerate(indices):
        if text[i] != ",":
            continue
        if pos + 1 >= len(indices):
            continue
        nxt = text[indices[pos + 1]]
        if nxt in "}]":
            chars[i] = " "
    return "".join(chars)


def provider_summary(text: str, entry: ProviderEntry) -> dict:
    """Allowlisted fields for `list`: id, npm, options.baseURL."""
    slice_text = text[entry.value_start : entry.value_end]
    cleaned = strip_trailing_commas(strip_jsonc_comments(slice_text))
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = None
    npm = None
    base_url = None
    if isinstance(parsed, dict):
        raw_npm = parsed.get("npm")
        if isinstance(raw_npm, str):
            npm = raw_npm
        options = parsed.get("options")
        if isinstance(options, dict):
            raw_url = options.get("baseURL")
            if isinstance(raw_url, str):
                base_url = raw_url
    return {
        "id": entry.provider_id,
        "npm": npm,
        "baseURL": base_url,
    }


def _parse_pairs(text: str):
    """Parse `text` (JSONC) via `object_pairs_hook=list`.

    Every JSON object in the document — top-level and nested — decodes to a
    `list[tuple[key, value]]` instead of a `dict`, preserving both key order
    and duplicate keys exactly as written. A plain `dict` would silently
    collapse duplicate provider ids to their last occurrence, which would
    make `validate_removal` reject the legitimate "remove the first of two
    duplicate ids, the second survives" case `remove_provider` itself
    supports (see `TestDuplicateProviderId`). Raises `json.JSONDecodeError`
    on invalid input — callers decide what "invalid" means for them.
    """
    cleaned = strip_trailing_commas(strip_jsonc_comments(text))
    return json.loads(cleaned, object_pairs_hook=list)


def validate_removal(before_text: str, after_text: str, provider_id: str) -> bool:
    """Structural safety check for a `remove_provider` edit before it is written.

    `find_object_span`/`find_provider_object` locate spans by pure brace-depth
    counting with no awareness of whether those braces actually belong to the
    entry being scanned. On unbalanced-brace input elsewhere in the document,
    that counting can walk straight through the target entry's intended end
    and consume a `}` that belongs to the enclosing `"provider"` object or the
    document root — `remove_provider` would then delete the wrong span and
    return text that looks plausible but is no longer valid JSON, or is valid
    JSON with damage far outside the target entry. Trusting the same
    brace-depth bookkeeping to also validate itself (e.g. checking the target
    entry's computed end against the enclosing object's computed end) does not
    catch this: both ends are wrong in lockstep, produced by the same flawed
    scan.

    This performs a full, independent JSON round-trip instead: both
    `before_text` and `after_text` must parse as valid JSON once comments and
    trailing commas are stripped, and `after_text` must equal `before_text`
    with exactly the first depth-1 `provider_id` entry removed from the
    `"provider"` object — nothing else may differ. Returns `False` (refuse to
    write) on any parse failure or any other mismatch, including when
    `before_text` was already malformed — this tool must never write on top
    of a config it cannot fully verify.
    """
    try:
        before_pairs = _parse_pairs(before_text)
        after_pairs = _parse_pairs(after_text)
    except json.JSONDecodeError:
        return False
    if not isinstance(before_pairs, list):
        return False
    try:
        expected_pairs = []
        removed = False
        for key, value in before_pairs:
            if not removed and key == "provider" and isinstance(value, list):
                new_value = list(value)
                for i, (child_key, _child_value) in enumerate(new_value):
                    if child_key == provider_id:
                        del new_value[i]
                        break
                expected_pairs.append((key, new_value))
                removed = True
            else:
                expected_pairs.append((key, value))
    except (TypeError, ValueError):
        return False
    return after_pairs == expected_pairs


def remove_provider(text: str, provider_id: str) -> str | None:
    """Return text with the first depth-1 `provider_id` entry removed, or None.

    Two disjoint deletions: the entry's key_start..value_end span, and at most
    one comma (after the entry if a sibling follows, else before it). Bytes
    between those deletions are preserved. Duplicate depth-1 ids: the first
    in file order is removed.

    `significant_indices` is computed exactly once, seeded at the provider
    object's opening brace.
    """
    entries = iter_provider_entries(text)
    target = None
    for entry in entries:
        if entry.provider_id == provider_id:
            target = entry
            break
    if target is None:
        return None
    span = find_provider_object(text)
    if span is None:
        return None
    open_i, close_i = span
    sig = significant_indices(text, open_i, close_i)
    comma: int | None = None
    after = [i for i in sig if i >= target.value_end]
    if after and text[after[0]] == ",":
        comma = after[0]
    else:
        before = [i for i in sig if i < target.key_start]
        if before and text[before[-1]] == ",":
            comma = before[-1]
    if comma is None:
        return text[: target.key_start] + text[target.value_end :]
    if comma < target.key_start:
        return (
            text[:comma]
            + text[comma + 1 : target.key_start]
            + text[target.value_end :]
        )
    return (
        text[: target.key_start]
        + text[target.value_end : comma]
        + text[comma + 1 :]
    )
