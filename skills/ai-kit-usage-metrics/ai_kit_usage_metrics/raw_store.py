"""Raw JSONL store, cursor I/O, and the CaptureResult contract."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from dataclasses import dataclass

from ai_kit_usage_metrics import paths


@dataclass
class CaptureResult:
    """One concrete return shape for every source's `capture(env, cursor)`."""

    records: list[dict]
    cursor: dict
    stats: dict


def _ensure_private_dir(directory: str) -> None:
    if not directory:
        directory = "."
    os.makedirs(directory, mode=0o700, exist_ok=True)
    os.chmod(directory, 0o700)


def _atomic_write_text(path: str, text: str) -> None:
    """Atomically write `text` to `path`.

    Skeleton ported from the sibling skill
    `skills/ai-kit-opencode-providers` `atomic_write.py`
    (`write_preserving_mode`: temp file, fsync, chmod, os.replace, dir fsync).
    Mode-preservation pre-check ported from
    `tools/config_doctor_appliers.py::_atomic_write_text` (lines 109-134):
    `existed = os.path.isfile(target)`; `os.stat` only when the target already
    exists; new files get mode 0o600 with no exception-driven control flow.
    """
    directory = os.path.dirname(path) or "."
    _ensure_private_dir(directory)
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


def append_records(path: str, new_records: list[dict]) -> None:
    """Append envelopes whose `raw_ref` is not already in `path`.

    Reads the target file's own existing lines first and filters on `raw_ref`
    so a crash between append and cursor-write cannot duplicate lines. A true
    O_APPEND-based writer is a drop-in future optimization that does not
    change the JSONL format itself; rewrite-the-file is MVP-appropriate at
    personal-scale volume.
    """
    existing_lines: list[str] = []
    seen: set[str] = set()
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                stripped = line.rstrip("\r\n")
                if not stripped:
                    continue
                existing_lines.append(stripped)
                try:
                    rec = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                raw_ref = rec.get("raw_ref")
                if raw_ref is not None:
                    seen.add(raw_ref)
    survivors = [rec for rec in new_records if rec.get("raw_ref") not in seen]
    if not survivors and os.path.isfile(path):
        return
    out_lines = existing_lines + [json.dumps(rec, ensure_ascii=False) for rec in survivors]
    _atomic_write_text(path, "".join(line + "\n" for line in out_lines))


def read_cursor(env: dict, source_name: str) -> dict:
    path = os.path.join(paths.cursors_dir(env), f"{source_name}.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_cursor(env: dict, source_name: str, cursor: dict) -> None:
    path = os.path.join(paths.cursors_dir(env), f"{source_name}.json")
    _atomic_write_text(path, json.dumps(cursor, indent=2) + "\n")
