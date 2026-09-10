"""Read-only 3-state config readers for Config Doctor.

Stdlib-only. Imports nothing from setup.py, wizard_app.py, or any skills/*
package. Absent / ok-dict / unreadable are never conflated into {}.
"""

from __future__ import annotations

import json
import os
import subprocess
import tomllib

UNKNOWN = object()

RTK_PROBE_TIMEOUT_SECONDS = 2.0
RTK_SIGNAL_CONFIRMED = "registered"
RTK_SIGNAL_NOT_REGISTERED = "not-registered"
RTK_SIGNAL_UNREADABLE = "unreadable"

KIND_CODE = "code"
KIND_STRING = "string"
KIND_COMMENT = "comment"


def _classify(text: str) -> list[str]:
    """Classify every character from offset 0 (neutral seed).

    Ported from the jsonc_edit module in the ai-kit-opencode-providers skill
    (read-only helpers only; no surgical-edit machinery).
    """
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


def strip_jsonc_comments(text: str) -> str:
    """Replace comment characters with spaces; leave strings and code intact.

    Ported from the jsonc_edit module in the ai-kit-opencode-providers skill
    (``strip_jsonc_comments``; read-only, not imported).
    """
    kinds = _classify(text)
    chars = list(text)
    for i, kind in enumerate(kinds):
        if kind == KIND_COMMENT and text[i] != "\n":
            chars[i] = " "
    return "".join(chars)


def code_indices(text: str, start: int, end: int) -> list[int]:
    """CODE-state, non-whitespace positions in ``[start, end)``.

    Ported from the jsonc_edit module in the ai-kit-opencode-providers skill
    (``code_indices`` — required internally by ``strip_trailing_commas``).
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
    """Replace trailing commas before ``}`` or ``]`` with a space.

    Ported from the jsonc_edit module in the ai-kit-opencode-providers skill
    (``strip_trailing_commas``; read-only, not imported).
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


def _classify_parsed(path, loader):
    """Run ``loader(path) -> data`` through the 3-state contract."""
    if not os.path.isfile(path):
        return "absent", {}
    try:
        data = loader(path)
    except (ValueError, OSError):
        return "unreadable", None
    if not isinstance(data, dict):
        return "unreadable", None
    return "ok", data


def read_json_checked(path):
    """Three-state JSON reader: absent / ok-dict / unreadable."""

    def _load(p):
        with open(p, encoding="utf-8") as handle:
            return json.load(handle)

    return _classify_parsed(path, _load)


def read_jsonc_checked(path):
    """Three-state JSONC reader: strip comments + trailing commas, then JSON."""

    def _load(p):
        with open(p, encoding="utf-8") as handle:
            text = handle.read()
        stripped = strip_trailing_commas(strip_jsonc_comments(text))
        return json.loads(stripped)

    return _classify_parsed(path, _load)


def read_toml_checked(path):
    """Three-state TOML reader using stdlib tomllib. Distinct from setup.read_toml."""

    def _load(p):
        with open(p, "rb") as handle:
            return tomllib.load(handle)

    return _classify_parsed(path, _load)


def get_nested(data, *keys, default=UNKNOWN):
    """Walk ``data`` through successive string keys; return ``default`` on miss."""
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _probe_rtk_cursor_hook(rtk_path, runner):
    """Classify rtk's Cursor hook from ``rtk init --show`` stdout. Never raises.

    Line text sourced from 03-RESEARCH.md:527-540's verbatim output block:
    ``[ok] Cursor hook: registered in hooks.json`` (lowercase ``hook``),
    distinct from ``[ok] Hook: rtk hook claude (native binary command)``.
    Matcher requires ``"Cursor"`` and lowercase ``"hook"``, never a
    case-sensitive ``"Hook"``. 04-RESEARCH.md row 12: point-in-time —
    re-probe at build/verify time, not fixed by this research session. A
    future rtk release could reword this line; classification degrades to
    unreadable on no match rather than raise or assume.
    """
    if runner is None:
        runner = subprocess.run
    try:
        proc = runner(
            [rtk_path, "init", "--show"],
            capture_output=True,
            text=True,
            timeout=RTK_PROBE_TIMEOUT_SECONDS,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except Exception:
        return RTK_SIGNAL_UNREADABLE
    stdout = proc.stdout or ""
    for line in stdout.splitlines():
        if "Cursor" not in line or "hook" not in line:
            continue
        stripped = line.lstrip()
        if stripped.startswith("[ok]"):
            return RTK_SIGNAL_CONFIRMED
        if stripped.startswith("[--]"):
            return RTK_SIGNAL_NOT_REGISTERED
        return RTK_SIGNAL_UNREADABLE
    return RTK_SIGNAL_UNREADABLE
