"""Dated config backups beside the resolved GSD config and verbatim atomic restore.

The restore path is the one sanctioned config write outside gsd-tools (D-21). Backup files
are untracked artifacts in the user's repo (Pitfall 14).
"""
import os
import re
import stat
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from typing import NamedTuple

from . import gsd_catalog

BACKUP_PREFIX = "config.json.bak-"
BACKUP_RE = re.compile(r"^config\.json\.bak-(\d{8}T\d{6}Z)(?:-(\d+))?$")
KEEP = 3
MARKER_SUFFIX = ".ai-kit-apply-marker"
SNAPSHOT_SUFFIX = ".ai-kit-apply-backup"


class BackupResult(NamedTuple):
    path: str | None
    reused: bool


def backup_stamp(now: datetime) -> str:
    return now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _config_dir(config_path: str) -> str:
    return os.path.dirname(os.path.abspath(config_path))


def _backup_basename(stamp: str, n: int) -> str:
    suffix = f"-{n}" if n else ""
    return f"{BACKUP_PREFIX}{stamp}{suffix}"


def _claim_copy(data: bytes, mode: int, final: str) -> bool:
    parent = os.path.dirname(final)
    fd, tmp = tempfile.mkstemp(dir=parent, prefix=".bak-tmp-")
    os.close(fd)
    try:
        with open(tmp, "wb") as handle:
            handle.write(data)
        os.chmod(tmp, stat.S_IMODE(mode))
        os.link(tmp, final)
        return True
    except FileExistsError:
        return False
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def list_backups(config_path: str) -> list[tuple[str, str, int]]:
    directory = _config_dir(config_path)
    rows: list[tuple[str, str, int]] = []
    try:
        names = os.listdir(directory)
    except OSError:
        return []
    for name in names:
        match = BACKUP_RE.match(name)
        if not match:
            continue
        stamp = match.group(1)
        n = int(match.group(2)) if match.group(2) else 0
        rows.append((os.path.join(directory, name), stamp, n))
    rows.sort(key=lambda row: (row[1], row[2]))
    return rows


def _newest_backup(config_path: str) -> tuple[str, str, int] | None:
    backups = list_backups(config_path)
    return backups[-1] if backups else None


def _backup_matches_config(backup_path: str, config_path: str) -> bool:
    try:
        with open(backup_path, "rb") as backup:
            backup_bytes = backup.read()
        with open(config_path, "rb") as config:
            config_bytes = config.read()
        backup_mode = stat.S_IMODE(os.stat(backup_path).st_mode)
        config_mode = stat.S_IMODE(os.stat(config_path).st_mode)
    except OSError:
        return False
    return backup_bytes == config_bytes and backup_mode == config_mode


def create_backup(
    config_path: str,
    now_fn: Callable[[], datetime],
) -> BackupResult:
    if not os.path.isfile(config_path):
        return BackupResult(None, False)
    newest_row = _newest_backup(config_path)
    if newest_row is not None:
        newest_path, _stamp, _n = newest_row
        if _backup_matches_config(newest_path, config_path):
            return BackupResult(newest_path, True)
    with open(config_path, "rb") as handle:
        data = handle.read()
    mode = stat.S_IMODE(os.stat(config_path).st_mode)
    stamp = backup_stamp(now_fn())
    directory = _config_dir(config_path)
    for n in range(1000):
        final = os.path.join(directory, _backup_basename(stamp, n))
        if _claim_copy(data, mode, final):
            return BackupResult(final, False)
    raise OSError("could not claim a backup filename")


def prune_backups(config_path: str, keep: int = KEEP) -> list[str]:
    backups = list_backups(config_path)
    if len(backups) <= keep:
        return []
    remove = backups[: len(backups) - keep]
    removed: list[str] = []
    for path, _stamp, _n in remove:
        try:
            os.unlink(path)
            removed.append(path)
        except OSError:
            continue
    return removed


def restore_backup(config_path: str, backup_path: str | None) -> None:
    if backup_path is None:
        if os.path.isfile(config_path):
            os.unlink(config_path)
        return
    with open(backup_path, "rb") as handle:
        data = handle.read()
    mode = stat.S_IMODE(os.stat(backup_path).st_mode)
    cache = gsd_catalog.load_ai_kit_spec_module("cache")
    if cache is None:
        raise OSError(gsd_catalog.SIBLING_MISSING)
    cache.cache_write_bytes(os.path.abspath(config_path), data, mode=mode)
