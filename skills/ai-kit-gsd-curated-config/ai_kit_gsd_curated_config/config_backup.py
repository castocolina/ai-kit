"""Dated config backups beside the resolved GSD config and verbatim atomic restore.

The restore path is the one sanctioned config write outside gsd-tools (D-21). Backup files
are untracked artifacts in the user's repo (Pitfall 14).
"""
import json
import os
import re
import stat
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, NamedTuple

from . import gsd_catalog, plan_io

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


def _cache() -> Any:
    cache = gsd_catalog.load_ai_kit_spec_module("cache")
    if cache is None:
        raise OSError(gsd_catalog.SIBLING_MISSING)
    return cache


def _atomic_copy(src: str, dst: str) -> None:
    """Bytes and mode of ``src`` onto ``dst`` through the shared atomic writer."""
    with open(src, "rb") as handle:
        data = handle.read()
    mode = stat.S_IMODE(os.stat(src).st_mode)
    _cache().cache_write_bytes(os.path.abspath(dst), data, mode=mode)


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
    _atomic_copy(backup_path, config_path)


def snapshot_file(path: str) -> str | None:
    if not os.path.isfile(path):
        return None
    target = os.path.abspath(path) + SNAPSHOT_SUFFIX
    _atomic_copy(path, target)
    return target


def discard_snapshot(snapshot_path: str) -> None:
    if snapshot_path and os.path.isfile(snapshot_path):
        os.unlink(snapshot_path)


def marker_path(config_path: str) -> str:
    return os.path.abspath(config_path) + MARKER_SUFFIX


def acquire_marker(config_path: str, config_existed: bool, now_fn: Callable[[], datetime]) -> bool:
    target = os.path.abspath(config_path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    started = now_fn().astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "backup": None,
        "config_existed": config_existed,
        "started": started,
        "runner": None,
        "committed": False,
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return _claim_copy(body, _cache().umask_file_mode(), marker_path(target))


def read_marker(config_path: str) -> dict[str, Any] | None:
    path = marker_path(config_path)
    if not os.path.isfile(path):
        return None
    data, warn = plan_io.read_json_object(path)
    if warn is not None or data is None:
        return {"corrupt": True}
    return data


def update_marker(config_path: str, **fields: Any) -> None:
    current = read_marker(config_path)
    if current is None or current.get("corrupt"):
        raise OSError("apply marker missing or corrupt")
    merged = {**current, **fields}
    text = json.dumps(merged, indent=2, sort_keys=True) + "\n"
    _cache().cache_write_text(marker_path(config_path), text)


def clear_marker(config_path: str) -> None:
    path = marker_path(config_path)
    if os.path.isfile(path):
        os.unlink(path)


def _leftovers_phrase(marker: dict[str, Any]) -> str:
    runner = marker.get("runner")
    if isinstance(runner, dict) and runner.get("snapshot"):
        snap = runner["snapshot"]
        return f"{snap} if it exists, then the marker"
    return "the marker"


def _recovery_config_step(marker: dict[str, Any], config_path: str) -> str:
    backup = marker.get("backup")
    if backup:
        # The marker keeps the basename (relocatable); the text needs a path usable from any cwd.
        return f"put {os.path.join(os.path.dirname(config_path), backup)} back over {config_path}"
    if not marker.get("config_existed", True):
        return f"delete {config_path} if it exists (that apply created it)"
    return (
        f"{config_path} needs no restore (no backup was taken yet, "
        "so that apply wrote nothing to it)"
    )


def _recovery_runner_step(marker: dict[str, Any]) -> str:
    runner = marker.get("runner")
    if not isinstance(runner, dict):
        return "the runner needs no restore"
    kind = runner.get("kind")
    path = runner.get("path")
    snapshot = runner.get("snapshot")
    if kind == "change" and snapshot and path:
        return f"put {snapshot} back over {path}"
    if kind == "add" and path:
        return (
            f"delete {path} if it exists, unless you created it since (that apply added it)"
        )
    return "the runner needs no restore"


def _recovery_dry_run_prefix(marker: dict[str, Any], config_path: str) -> str:
    backup = marker.get("backup")
    config_existed = marker.get("config_existed", True)
    if not backup and config_existed:
        return ""
    phrase = _leftovers_phrase(marker)
    return (
        " first run apply --dry-run with that apply's plan and inventory "
        "(a dry run takes no lock and ignores the marker, 18-17); "
        "if its diff holds only keep rows, that apply finished its writes and "
        f"only its commit record is missing: delete {phrase} and restore nothing; otherwise"
    )


def recovery_text(marker: dict[str, Any] | None, config_path: str) -> str:
    config_path = os.path.abspath(config_path)
    head = f"an apply is running or did not finish ({marker_path(config_path)})"
    if marker is None:
        return f"{head}; it has finished since; run apply again"
    if marker.get("corrupt"):
        return (
            f"{head}; the marker is unreadable: if no apply is running, check "
            f"{config_path} and the runner by hand, then delete the marker"
        )
    if marker.get("committed"):
        phrase = _leftovers_phrase(marker)
        return (
            f"{head}; that apply committed: {config_path} and its runner hold the "
            f"applied state; if no apply is running, delete {phrase}; "
            "do not restore the backup"
        )
    dry = _recovery_dry_run_prefix(marker, config_path)
    config_step = _recovery_config_step(marker, config_path)
    runner_step = _recovery_runner_step(marker)
    marker_file = marker_path(config_path)
    return (
        f"{head}; if no apply is running:{dry} {config_step}; {runner_step}, "
        f"then delete {marker_file}"
    )
