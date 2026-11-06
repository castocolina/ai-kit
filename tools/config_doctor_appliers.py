"""Atomic/surgical writers for Config Doctor apply.

Stdlib-only. Imports nothing from setup.py and nothing from any skills/*
package — every primitive is ported into this file with a source citation.
A tools/ module importing a skills/ package would be a layering violation
(tools/setup.py:1383-1394's own documented rule, applied here to a THIRD
writer this project did not have before; 04-RESEARCH.md Common Pitfall 1).
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import stat
import tempfile
import tomllib
from datetime import UTC, datetime

import global_rules

BACKUP_KEEP = 10

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
    """Validate new_text via tomllib.loads BEFORE ever touching the target.

    Adapted from tools/setup.py::write_toml_preserving (lines 451-508) rather
    than imported. DIVERGES at the self-validation step: instead of shelling
    out to statusline-doctor.py --doctor (Config Doctor has no per-format
    external validator of its own), call tomllib.loads(new_text) directly.

    Validating first — not after writing — closes a crash window a
    validate-after-write ordering would otherwise leave open: a process
    killed between "write" and "restore-on-failure" would leave the real
    target holding invalid TOML permanently, contradicting the byte-identical
    refusal-on-malformed-input contract this writer must uphold. With
    validate-first, invalid text is never written to the target at all, so
    no restore step is needed. On OSError during the write, unlink the temp
    file and return False rather than raising.
    """
    try:
        tomllib.loads(new_text)
    except tomllib.TOMLDecodeError:
        return False
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    dirname = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(new_text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except OSError:
        if os.path.exists(tmp):
            os.unlink(tmp)
        return False
    try:
        dir_fd = os.open(dirname, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass
    return True


def atomic_write_text(path, text):
    """Atomically write arbitrary text via sibling temp-file + os.replace.

    Mirrors write_toml_region_replace's temp-file+replace mechanics but for
    already-serialized text that is not TOML (JSONC surgical output). No
    parse-check of its own — the caller validates before committing. Fsyncs
    the containing directory after replace, matching atomic_write_json's and
    write_toml_region_replace's crash-durability guarantee.
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
    try:
        dir_fd = os.open(dirname, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass


# JSONC surgical helpers, ported VERBATIM from the jsonc_edit module in the
# ai-kit-opencode-providers skill (_classify lines 30-88, _skip_insignificant
# 91-94, _string_end 97-101, _skip_value 104-134, find_object_span 137-152,
# significant_indices 251-272). Format-mechanics only — no "provider"-
# specific logic. Cited rather than imported (a tools/ module importing a
# skills/ package would be a layering violation; tools/setup.py:1383-1394,
# 04-RESEARCH.md Common Pitfall 1).


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
                    while value < n and (kinds[value] == KIND_COMMENT or text[value].isspace()):
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


def _jsonc_insert_key(text, key_name, dumped, open_i, close_i):
    """Insert a new top-level key into an existing JSONC object span."""
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
    return _jsonc_insert_key(text, key_name, dumped, open_i, close_i)


def apply_codegraph_global_sentence(ctx, _target, dry):
    """Re-apply ai-kit wording where codegraph's installer wrote its sentence back (D-11).

    Keeps its own backup under backups/global-rules/ (Phase 30 R11): it is the one
    applier exempt from the shared apply_guarded path (D-14).
    """
    ok, lines = global_rules.apply(ctx.env, dry)
    if not ok:
        reason = next((line for line in lines if "failed" in line), "write failed")
        return {"ok": False, "reason": reason, "lines": lines}
    return {"ok": True, "current_display": global_rules.summary(ctx.env), "lines": lines}


# Guarded apply (D-14, D-08, D-09): every doctor applier except the Phase 30
# codegraph sentence goes through apply_guarded. Backups are uniform per
# runtime under backups_root(env)/<runtime>/ (plan ruling 4).


def backups_root(env):
    """Backup root under XDG state (D-08); same formula as setup.resolve_paths."""
    state_home = env.get("XDG_STATE_HOME") or os.path.join(env.get("HOME", ""), ".local", "state")
    return os.path.join(state_home, "ai-kit", "backups")


def prune_backups(folder, basename, keep, exclude):
    """Delete this file's backups beyond the newest `keep` (D-09); return deleted paths.

    Only names matching `<basename>.<stamp>[-n].bak` are candidates. `exclude` is
    counted first and never deleted, so the backup just taken survives by path,
    not by sort order.
    """
    if not os.path.isdir(folder):
        return []
    pattern = re.compile(rf"^{re.escape(basename)}\.\d{{8}}T\d{{12}}Z(-\d+)?\.bak$")
    paths = [os.path.join(folder, name) for name in os.listdir(folder) if pattern.match(name)]
    paths.sort(key=lambda p: (os.stat(p).st_mtime_ns, os.path.basename(p)), reverse=True)
    ordered = [p for p in paths if p == exclude] + [p for p in paths if p != exclude]
    kept = 0
    deleted = []
    for path in ordered:
        if path == exclude or kept < keep:
            kept += 1
            continue
        os.remove(path)
        deleted.append(path)
    return deleted


def _claim_backup_name(tmp, folder, basename, stamp):
    """Hard-link the temp copy to a fresh name; numbered suffix on collision."""
    suffix = 0
    while True:
        tail = "" if suffix == 0 else f"-{suffix}"
        candidate = os.path.join(folder, f"{basename}.{stamp}{tail}.bak")
        try:
            os.link(tmp, candidate)
            return candidate
        except FileExistsError:
            suffix += 1


def backup_before_write(path, backups_dir, label, keep=BACKUP_KEEP, now=None):
    """Copy `path` to `<backups_dir>/<label>/<name>.<UTC stamp>.bak`; return the new path.

    A missing `path` needs no backup and returns "". Raises OSError on any failure,
    so a failed backup aborts the write (D-08).
    """
    if not os.path.isfile(path):
        return ""
    if not os.path.isabs(backups_dir):
        raise OSError(f"backups dir is not absolute: {backups_dir}")
    folder = os.path.join(backups_dir, label)
    os.makedirs(folder, mode=0o700, exist_ok=True)
    basename = os.path.basename(path)
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    stamp = moment.strftime("%Y%m%dT%H%M%S%fZ")
    with open(path, "rb") as src:
        payload = src.read()
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        new_path = _claim_backup_name(tmp, folder, basename, stamp)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    os.chmod(new_path, 0o600)
    # Best effort: the new backup is already on disk, so a prune error must not read as
    # "backup failed" and block every later write.
    with contextlib.suppress(OSError):
        prune_backups(folder, basename, keep, exclude=new_path)
    return new_path


def _read_bytes_or_none(path):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as handle:
        return handle.read()


def _refuse_unparseable(path, kind):
    return {
        "ok": False,
        "reason": (
            f"refused: {path} was not changed: it cannot be parsed as {kind}. "
            "Nothing was written; fix the file by hand, then run the check again"
        ),
    }


def apply_guarded(  # pylint: disable=too-many-arguments
    path,
    compute,
    dry,
    *,
    parse,
    kind,
    write,
    backups_dir,
    label,
    before_replace=None,
):
    """Parse check, backup, re-read and compare, atomic write (D-14, R6).

    `compute(text_or_None, parsed_or_None)` returns `(payload, result)` or a
    refusal dict. A dry run returns `result` without a backup or a write.
    `before_replace` is a test hook that runs between the backup and the re-read.
    """
    raw = _read_bytes_or_none(path)
    text = None
    parsed = None
    if raw is not None:
        try:
            text = raw.decode("utf-8")
            parsed = parse(text)
            if not isinstance(parsed, dict):
                raise TypeError("not an object")
        except (ValueError, TypeError):
            return _refuse_unparseable(path, kind)
    outcome = compute(text, parsed)
    if isinstance(outcome, dict):
        return outcome
    payload, result = outcome
    if dry:
        return result
    return _commit_guarded(
        path,
        raw,
        payload,
        result,
        backups_dir=backups_dir,
        label=label,
        before_replace=before_replace,
        write=write,
    )


def _commit_guarded(  # pylint: disable=too-many-arguments
    path, raw, payload, result, *, backups_dir, label, before_replace, write
):
    """Backup, test hook, re-read compare, then the write; refusals keep the target."""
    try:
        backup = backup_before_write(path, backups_dir, label)
    except OSError as exc:
        return {"ok": False, "reason": f"refused: backup failed ({exc}); nothing was written"}
    if before_replace is not None:
        before_replace()
    if _read_bytes_or_none(path) != raw:
        return {
            "ok": False,
            "reason": (
                f"refused: {path} changed since it was read; nothing was written "
                f"(backup kept at {backup})"
            ),
        }
    try:
        write(path, payload)
    except OSError as exc:
        return {"ok": False, "reason": f"refused: write failed ({exc}); backup kept at {backup}"}
    return {**result, "backup": backup}
