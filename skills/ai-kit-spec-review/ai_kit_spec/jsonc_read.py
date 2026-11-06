"""Read-only copy of tools/config_doctor_readers.py's JSONC scanner.

Drift-tested by tests/test_ai_kit_spec_jsonc_read.py (skills cannot import tools/).
Reads only the child names of `provider` and `providers` from opencode config files. Never
writes, never returns a value, and never opens anything but the paths the caller names.
"""

import json
import os

MAX_BYTES = 1 << 20

KIND_CODE = "code"
KIND_STRING = "string"
KIND_COMMENT = "comment"


def _classify_in_string(text, kinds, i, mode):
    c = text[i]
    kinds[i] = KIND_STRING
    if mode["escaped"]:
        mode["escaped"] = False
        return i + 1
    if c == "\\":
        mode["escaped"] = True
    elif c == '"':
        mode["in_string"] = False
    return i + 1


def _classify_in_line(text, kinds, i, mode):
    kinds[i] = KIND_COMMENT
    if text[i] == "\n":
        mode["in_line"] = False
    return i + 1


def _classify_in_block(text, kinds, i, n, mode):
    kinds[i] = KIND_COMMENT
    if text[i] == "*" and i + 1 < n and text[i + 1] == "/":
        kinds[i + 1] = KIND_COMMENT
        mode["in_block"] = False
        return i + 2
    return i + 1


def _classify_in_code(text, kinds, i, n, mode):
    c = text[i]
    if c == "/" and i + 1 < n and text[i + 1] == "/":
        kinds[i] = KIND_COMMENT
        kinds[i + 1] = KIND_COMMENT
        mode["in_line"] = True
        return i + 2
    if c == "/" and i + 1 < n and text[i + 1] == "*":
        kinds[i] = KIND_COMMENT
        kinds[i + 1] = KIND_COMMENT
        mode["in_block"] = True
        return i + 2
    if c == '"':
        kinds[i] = KIND_STRING
        mode["in_string"] = True
        return i + 1
    kinds[i] = KIND_CODE
    return i + 1


def _classify_step(text, kinds, i, n, mode):
    """Single-character JSONC scanner step; mutates ``mode`` and ``kinds``."""
    if mode["in_string"] or mode["escaped"]:
        return _classify_in_string(text, kinds, i, mode)
    if mode["in_line"]:
        return _classify_in_line(text, kinds, i, mode)
    if mode["in_block"]:
        return _classify_in_block(text, kinds, i, n, mode)
    return _classify_in_code(text, kinds, i, n, mode)


def _classify(text: str) -> list[str]:
    """Classify every character from offset 0 (neutral seed)."""
    n = len(text)
    kinds = [KIND_CODE] * n
    mode = {
        "in_string": False,
        "escaped": False,
        "in_line": False,
        "in_block": False,
    }
    i = 0
    while i < n:
        i = _classify_step(text, kinds, i, n, mode)
    return kinds


def strip_jsonc_comments(text: str) -> str:
    """Replace comment characters with spaces; leave strings and code intact."""
    kinds = _classify(text)
    chars = list(text)
    for i, kind in enumerate(kinds):
        if kind == KIND_COMMENT and text[i] != "\n":
            chars[i] = " "
    return "".join(chars)


def code_indices(text: str, start: int, end: int) -> list[int]:
    """CODE-state, non-whitespace positions in ``[start, end)``."""
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
    """Replace trailing commas before ``}`` or ``]`` with a space."""
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


def read_provider_names(path: str) -> list[str] | None:
    """Child keys of `provider` and `providers` in file order, without duplicates.

    None when the file is missing, unreadable, over MAX_BYTES, not UTF-8 or not a JSON object
    (fail soft: the caller's label says which source applied).
    """
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_BYTES)
        text = raw.decode("utf-8")
        data = json.loads(strip_trailing_commas(strip_jsonc_comments(text)))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    names: list[str] = []
    for section_key in ("provider", "providers"):
        section = data.get(section_key)
        if not isinstance(section, dict):
            continue
        for name in section:
            if name not in names:
                names.append(name)
    return names


def project_config_paths(cwd: str) -> list[str]:
    """opencode config files the project itself defines."""
    return [
        os.path.join(cwd, "opencode.json"),
        os.path.join(cwd, "opencode.jsonc"),
        os.path.join(cwd, ".opencode", "opencode.json"),
        os.path.join(cwd, ".opencode", "opencode.jsonc"),
    ]


def opencode_config_paths(env: dict, cwd: str) -> list[str]:
    """User-level opencode config files, then the project's. Relative bases are dropped."""
    explicit = env.get("OPENCODE_CONFIG_DIR", "")
    if explicit:
        base = explicit
    else:
        xdg = env.get("XDG_CONFIG_HOME", "")
        if not os.path.isabs(xdg):
            home = env.get("HOME") or os.path.expanduser("~")
            xdg = os.path.join(home, ".config")
        base = os.path.join(xdg, "opencode")
    user_paths = [
        os.path.join(base, "opencode.json"),
        os.path.join(base, "opencode.jsonc"),
    ]
    return [path for path in user_paths if os.path.isabs(path)] + project_config_paths(cwd)
