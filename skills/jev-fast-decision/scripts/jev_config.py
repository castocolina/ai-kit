"""jev-fast-decision's own copy of ai-kit's layered config.toml reader and comment-keeping
splicer, plus the [jev] settings (Phase 34 D-01..D-03). The copied definitions are AST-identical
to Phase 33's ai_kit_spec modules (tests/test_jev_config_parity.py); edit them only by
re-copying. Stdlib only.
"""

import contextlib
import copy
import math
import os
import re
import stat
import tempfile
import urllib.parse
from types import ModuleType
from typing import NamedTuple

# The copied guard below binds tomllib; its None branch is the Python < 3.11 degrade path.
tomllib: ModuleType

try:
    import tomllib as _tomllib_impl

    tomllib = _tomllib_impl
except ModuleNotFoundError:  # Python < 3.11 — degrade to env-only config.
    tomllib = None  # type: ignore[assignment]  # stdlib boundary: optional module absent on <3.11


# BEGIN COPIED DEFINITIONS
# --- copied verbatim from ai_kit_spec/config_io.py ---
# tests/test_jev_config_parity.py pins each definition; re-copy on drift, never edit.
def cfg_local_path(cwd: str) -> str:
    """The project layer of ai-kit's config: ./.aikit/config.toml under cwd."""
    return os.path.join(cwd, ".aikit", "config.toml")


def cfg_config_base(env: dict) -> str:
    """${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit -- the base for ai-kit's own config files
    (the user config.toml and the trust store). HOME comes from env only, never from
    an ambient lookup, so an unset or empty HOME is an error rather than a guess: a repo could
    otherwise ship its own "global" config and trust store under the cwd (A-WR-01, C1-3). A
    whitespace-only XDG_CONFIG_HOME counts as unset (D-27); a relative one is ignored (XDG
    spec); no absolute home at all raises ConfigError (exit 2 in the CLI mains). The same rule
    as local_secrets, jev_review, tools/common_config and the runner
    (tests/test_config_dir_parity.py)."""
    xdg = env.get("XDG_CONFIG_HOME", "").strip()
    if os.path.isabs(xdg):
        return os.path.join(xdg, "ai-kit")
    home = env.get("HOME", "")
    if not os.path.isabs(home):
        raise ConfigError("$HOME", "no absolute home directory to hold ai-kit's config")
    return os.path.join(home, ".config", "ai-kit")


def cfg_global_path(env: dict) -> str:
    """The user layer of ai-kit's config: ${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/config.toml."""
    return os.path.join(cfg_config_base(env), "config.toml")


class ConfigError(ValueError):
    """A config.toml exists but cannot be parsed (malformed TOML, non-UTF-8 bytes, a non-table
    [lanes], a failed roster migration, or no tomllib on this interpreter). Carries the path and the
    parser message; the CLI mains
    catch it, print it to stderr, and exit 2 (D-11/R13) -- a broken config must stop the
    CLIs loudly, never silently disable cross-AI review."""

    def __init__(self, path: str, message: str):
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def cfg_load_toml(path: str) -> dict:
    """Parse the TOML at path. A missing file is a valid empty config -> {} (a missing
    config.toml is the normal no-config state, never an error). Any OTHER problem
    raises ConfigError (D-11/R13): an existing malformed or non-UTF-8 file, an unreadable
    file, or tomllib missing on Python < 3.11. Unlike the renderer's never-raise
    loader, this module FAILS LOUDLY -- a silently-ignored broken config.toml would
    switch cross-AI review off without the user ever knowing."""
    if tomllib is None:
        if os.path.exists(path):
            raise ConfigError(path, "reading TOML needs Python 3.11+")
        return {}
    try:
        with open(path, "rb") as f:
            return cfg_parse_toml_bytes(f.read(), path)
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise ConfigError(path, str(exc)) from exc


def cfg_read_bytes(path: str) -> bytes:
    """Read a config file's raw bytes once (the trust gate hashes and parses the same
    buffer); an unreadable file (permissions, a directory) is a ConfigError, exit 2."""
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError as exc:
        raise ConfigError(path, str(exc)) from exc


def cfg_parse_toml_bytes(raw: bytes, path: str) -> dict:
    """Parse already-read TOML bytes; raise ConfigError naming `path` for malformed TOML
    or non-UTF-8 bytes. Kept separate so cfg_resolve can hash and parse the SAME bytes it
    read once -- no check-then-read gap between the trust decision and the parse."""
    if tomllib is None:
        raise ConfigError(path, "reading TOML needs Python 3.11+")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ConfigError(path, f"not valid UTF-8 ({exc})") from exc
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(path, str(exc)) from exc


def cfg_load_layers(cwd: str, env: dict) -> tuple[dict, dict]:
    """(project config.toml, user config.toml) parsed; no migration and no trust."""
    return cfg_load_toml(cfg_local_path(cwd)), cfg_load_toml(cfg_global_path(env))


def _table_at(doc: dict, table_path: tuple) -> dict:
    node = doc
    for part in table_path:
        node = node.get(part) if isinstance(node, dict) else None
        if not isinstance(node, dict):
            return {}
    return node


def cfg_layered_table(cwd: str, env: dict, *table_path: str) -> dict:
    """One ordinary table merged per key, project over user (for `[models]`, `[jev]`, `[hooks]`,
    `[runner]`). The trust-gated lanes go through cfg_resolve instead."""
    project, user = cfg_load_layers(cwd, env)
    return {**_table_at(user, table_path), **_table_at(project, table_path)}


# --- copied verbatim from ai_kit_spec/toml_splice.py ---
# tests/test_jev_config_parity.py pins each definition; re-copy on drift, never edit.
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


# --- copied verbatim from ai_kit_spec/cache.py ---
# tests/test_jev_config_parity.py pins each definition; re-copy on drift, never edit.
def cache_write_bytes(path: str, data: bytes, mode: int | None = None) -> None:
    """Crash-safe atomic binary write: mkstemp in the target dir, optional chmod, fsync of the
    file, os.replace, then fsync of the folder (a folder fsync failure is not a write failure)."""
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=parent, suffix=".tmp")
    try:
        if mode is not None:
            os.chmod(tmp, mode)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            with contextlib.suppress(OSError):
                os.unlink(tmp)
        raise
    _fsync_folder(parent)


def _fsync_folder(folder: str) -> None:
    """Best effort: the rename already happened, so a folder fsync error is ignored."""
    try:
        fd = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass
# END COPIED DEFINITIONS


# --- jev settings: this skill's own code (not a copy) ---
JEV_KEYS = ("laya_url", "laya_version", "enabled")
URL_ENV = ("JEV_LAYA_URL", "AI_KIT_LAYA_URL")
KNOB_ENV = "GSD_PATH_JEV"
_VERSION_RE = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+-]{0,63}")


def jev_table(cwd: str, env) -> dict:
    """The [jev] table, project over user per key (ConfigError for an unreadable file)."""
    return cfg_layered_table(cwd, env, "jev")


def valid_url(raw: str) -> bool:
    """http or https with a host, no user name or password, no query or fragment, a valid port.
    A query or fragment could carry a credential, and the client drops both before use."""
    try:
        parts = urllib.parse.urlsplit(raw)
        _ = parts.port
    except ValueError:
        return False
    return (
        parts.scheme in ("http", "https")
        and bool(parts.hostname)
        and re.fullmatch(r"\S+", parts.netloc) is not None
        and parts.username is None
        and parts.password is None
        and not parts.query
        and not parts.fragment
    )


def valid_version(raw: str) -> bool:
    return _VERSION_RE.fullmatch(raw) is not None


def parse_value(key: str, raw: str) -> bool | str:
    """The typed value of one [jev] key. Raises ValueError: unknown_key or invalid_value:<key>."""
    if key not in JEV_KEYS:
        raise ValueError("unknown_key")
    text = raw.strip()
    if key == "enabled" and text.lower() in ("true", "false"):
        return text.lower() == "true"
    if key == "laya_url" and (text == "" or valid_url(text)):
        return text
    if key == "laya_version" and valid_version(text):
        return text
    raise ValueError(f"invalid_value:{key}")


def config_set(key: str, raw: str, env, cwd: str | None = None) -> dict:
    """Save one [jev] key to the user config.toml (D-03). Other bytes of the file stay as they are;
    a broken or unwritable file is refused with nothing written. With a `cwd`, a project
    ./.aikit/config.toml that overrides the saved key is reported (`overridden_by`, `notice`)."""
    try:
        value = parse_value(key, raw)
    except ValueError as error:
        return {"ok": False, "reason": str(error)}
    try:
        path = cfg_global_path(env)
    except ConfigError:
        return {"ok": False, "reason": "no_user_config_dir"}
    try:
        text = ""
        if os.path.exists(path):
            data = cfg_read_bytes(path)
            cfg_parse_toml_bytes(data, path)
            text = data.decode("utf-8")
        new_text = set_table(text, ("jev",), {key: value})
        if new_text != text:
            publish(path, new_text)
    except (ConfigError, SpliceError, OSError, UnicodeError) as error:
        return {"ok": False, "reason": "config_unwritable", "detail": str(error)}
    result = {"ok": True, "key": key, "value": value, "file": path}
    if cwd is not None:
        shadow = _shadow(key, value, env, cwd)
        if shadow:
            result["overridden_by"], result["notice"] = shadow
    return result


def _shadow(key: str, value, env, cwd: str):
    """(overridden_by, notice) when something beats the user value just saved, else None: a session
    variable first, then a project file that cannot be read or that sets the key itself."""
    names = {"enabled": (KNOB_ENV,), "laya_url": URL_ENV}.get(key, ())
    name = next((name for name in names if (env.get(name) or "").strip()), None)
    if name:
        return f"env:{name}", f"saved, but {name} is set in this session and wins over the " \
                              "files until it is unset"
    project = cfg_local_path(cwd)
    try:
        effective = cfg_layered_table(cwd, env, "jev").get(key)
    except ConfigError:
        return project, (f"saved, but {project} cannot be read, so the saved {key} is not "
                         "used there until it is fixed")
    if effective != value and os.path.exists(project):
        return project, (f"saved, but {project} sets {key} and wins over the user file "
                         "until that line is removed")
    return None


def knob(cwd: str, env) -> dict:
    """Whether jev runs (D-01): GSD_PATH_JEV wins both ways, then [jev] enabled (project over user),
    then on by default with needs_answer. A broken file or a bad value fails closed (off)."""
    raw = env.get(KNOB_ENV)
    if isinstance(raw, str) and raw.strip():
        value = raw.strip()
        return {"on": value == "1", "source": f"env:{KNOB_ENV}", "needs_answer": False,
                "problem": None if value in ("0", "1") else f"invalid_value:{KNOB_ENV}"}
    try:
        table = jev_table(cwd, env)
    except ConfigError as error:
        return {"on": False, "source": "config", "needs_answer": False,
                "problem": f"config_error: {error}"}
    value = table.get("enabled")
    if isinstance(value, bool):
        return {"on": value, "source": "config", "needs_answer": False, "problem": None}
    if value is None:
        return {"on": True, "source": "default", "needs_answer": True, "problem": None}
    return {"on": False, "source": "config", "needs_answer": False,
            "problem": "invalid_value:enabled"}


def laya_url_setting(cwd: str, env) -> tuple:
    """(value, source) of the Laya URL: session env, then project [jev], then user [jev], then none.
    An empty string is the declined answer, not a missing one."""
    for name in URL_ENV:
        raw = (env.get(name) or "").strip()
        if raw:
            return raw, f"env:{name}"
    try:
        table = jev_table(cwd, env)
    except ConfigError:
        return None, "config_error"
    value = table.get("laya_url")
    if isinstance(value, str):
        return value.strip(), "config"
    if value is None:
        return None, "default"
    return None, "invalid_value:laya_url"
