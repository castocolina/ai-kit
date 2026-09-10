"""Atomic/surgical writers for Config Doctor apply.

Stdlib-only. Imports nothing from setup.py and nothing from any skills/*
package — every primitive is ported into this file with a source citation.
A tools/ module importing a skills/ package would be a layering violation
(tools/setup.py:1383-1394's own documented rule, applied here to a THIRD
writer this project did not have before; 04-RESEARCH.md Common Pitfall 1).
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
import tomllib

KIND_CODE = "code"
KIND_STRING = "string"
KIND_COMMENT = "comment"


def atomic_write_json(path, data):
    """Atomically write JSON with indent=2 + trailing newline.

    Adapted from tools/setup.py::_atomic_write_json (lines 1383-1423) rather
    than imported. That function itself was adapted from the atomic_write
    module in the ai-kit-opencode-providers skill rather than imported (a
    tools/ module importing a skills/ package would be a layering
    violation). Fresh files get mode 0o600 — the mode both
    hosts' own config files were measured to carry — rather than a
    umask-derived mode. An existing target's real mode is copied, never
    overwritten. Unlink-then-re-raise on OSError is the durability contract
    the failure-injection test executes against.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    target = os.path.realpath(path)
    dirname = os.path.dirname(target) or "."
    existed = os.path.isfile(target)
    mode = stat.S_IMODE(os.stat(target).st_mode) if existed else 0o600
    fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, target)
    except OSError:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    try:
        dir_fd = os.open(dirname, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass


def write_toml_region_replace(path, new_text):
    """Atomically write TOML text, then self-validate via tomllib.loads.

    Adapted from tools/setup.py::write_toml_preserving (lines 451-508) rather
    than imported. DIVERGES at the self-validation step: instead of shelling
    out to statusline-doctor.py --doctor (Config Doctor has no per-format
    external validator of its own), call tomllib.loads(new_text) directly.
    On TOMLDecodeError, restore the previous content the same atomic way
    (a second temp-file + os.replace) and return False; when there was no
    previous content (prev is None) and validation fails, os.unlink the
    just-written file instead of restoring. On OSError during the write,
    unlink the temp file and return False rather than raising.
    """
    prev = None
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            prev = handle.read()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(new_text)
        os.replace(tmp, path)
    except OSError:
        if os.path.exists(tmp):
            os.unlink(tmp)
        return False
    try:
        tomllib.loads(new_text)
    except tomllib.TOMLDecodeError:
        if prev is None:
            os.unlink(path)
        else:
            rfd, rtmp = tempfile.mkstemp(
                dir=os.path.dirname(path) or ".", suffix=".tmp"
            )
            try:
                with os.fdopen(rfd, "w", encoding="utf-8") as handle:
                    handle.write(prev)
                os.replace(rtmp, path)
            except OSError:
                if os.path.exists(rtmp):
                    os.unlink(rtmp)
        return False
    return True


def _atomic_write_text(path, text):
    """Atomically write arbitrary text via sibling temp-file + os.replace.

    Mirrors write_toml_region_replace's temp-file+replace mechanics but for
    already-serialized text that is not TOML (JSONC surgical output). No
    parse-check of its own — the caller validates before committing.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    target = os.path.realpath(path)
    dirname = os.path.dirname(target) or "."
    existed = os.path.isfile(target)
    mode = stat.S_IMODE(os.stat(target).st_mode) if existed else 0o600
    fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, target)
    except OSError:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# JSONC surgical helpers, ported VERBATIM from the jsonc_edit module in the
# ai-kit-opencode-providers skill (_classify lines 30-88, _skip_insignificant
# 91-94, _string_end 97-101, _skip_value 104-134, find_object_span 137-152,
# significant_indices 251-272). Format-mechanics only — no "provider"-
# specific logic. Cited rather than imported (a tools/ module importing a
# skills/ package would be a layering violation; tools/setup.py:1383-1394,
# 04-RESEARCH.md Common Pitfall 1).


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


def significant_indices(text: str, start: int, end: int) -> list[int]:
    """Non-whitespace, non-comment positions in `[start, end)`."""
    kinds = _classify(text)
    out: list[int] = []
    for i in range(start, min(end, len(text))):
        if kinds[i] == KIND_COMMENT:
            continue
        if text[i].isspace():
            continue
        out.append(i)
    return out


def _find_top_level_key_span(text, key_name):
    """Span of a top-level key of any JSON type, or None if absent.

    Generalizes jsonc_edit.find_provider_object's depth-1 key-match walk
    (lines 155-186), replacing the hardcoded ``"provider"`` literal with
    ``key_name`` and using ``_skip_value`` (not ``find_object_span``) to
    bound the value — a top-level value can be any JSON type (``share`` is
    a plain string, not an object). Returns ``(key_start, value_start,
    value_end)`` or None.
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
                if colon < n and text[colon] == ":" and key == key_name:
                    value = colon + 1
                    while value < n and (
                        kinds[value] == KIND_COMMENT or text[value].isspace()
                    ):
                        value += 1
                    if value < n and kinds[value] == KIND_STRING:
                        value_end = _string_end(kinds, value, n)
                    else:
                        value_end = _skip_value(text, kinds, value, n)
                    return (i, value, value_end)
            i = str_end
            continue
        i += 1
    return None


def _first_code_brace(text):
    kinds = _classify(text)
    for i, kind in enumerate(kinds):
        if kind == KIND_CODE and text[i] == "{":
            return i
    return None


def set_jsonc_value(text, key_path, new_value):
    """Surgically set a top-level JSONC key, preserving every other byte.

    Requires ``len(key_path) == 1`` in this wave. Nested key paths raise
    ``NotImplementedError`` — no currently apply-eligible row needs a deeper
    path, and extending this to recursive nested-object creation is
    deliberately out of this wave's scope (04-RESEARCH.md: deferred CLI
    front-end / future-row work is additive, not architecture-changing).

    Performs NO self-validation of its own output — it is a pure text
    transform. A caller writing the returned text to disk is responsible
    for validating the spliced result before committing it (the
    opencode-share-mode applier does this via the same strip+parse path
    config_doctor_readers.read_jsonc_checked uses internally, refusing to
    write when that validation fails).
    """
    if len(key_path) != 1:
        raise NotImplementedError(
            f"set_jsonc_value: nested key paths are not supported yet "
            f"({key_path!r} has depth {len(key_path)})"
        )
    key_name = key_path[0]
    dumped = json.dumps(new_value)
    found = _find_top_level_key_span(text, key_name)
    if found is not None:
        _key_start, value_start, value_end = found
        return text[:value_start] + dumped + text[value_end:]
    brace = _first_code_brace(text)
    if brace is None:
        return '{\n  "' + key_name + '": ' + dumped + "\n}\n"
    open_i, close_i = find_object_span(text, brace)
    sig = significant_indices(text, open_i, close_i)
    last_before_close = None
    for idx in reversed(sig):
        if idx < close_i - 1:
            last_before_close = idx
            break
    if last_before_close is None or text[last_before_close] == "{":
        insert = f'\n  "{key_name}": {dumped}\n'
        return text[: open_i + 1] + insert + text[close_i - 1 :]
    insert = f',\n  "{key_name}": {dumped}'
    return text[: last_before_close + 1] + insert + text[last_before_close + 1 :]
