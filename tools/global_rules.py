"""Rewrite codegraph's "user decides" sentence in the four global instruction files.

Only text between codegraph's markers is touched, bytes in and bytes out, with a backup
written before each file. The only writer of those files in ai-kit (SPEC R11, D-11).
Stdlib only; never imports setup.py.
"""

import contextlib
import datetime
import os
import stat
import tempfile
from collections.abc import Callable
from typing import NamedTuple

from marked_block import replace_in_block

START = b"<!-- CODEGRAPH_START -->"
END = b"<!-- CODEGRAPH_END -->"
INSTALLER_SENTENCE = (
    "If there is no `.codegraph/` directory, skip CodeGraph entirely "
    "— indexing is the user's decision."
).encode()
AIKIT_SENTENCE = (
    b"If there is no `.codegraph/` directory and the `codegraph` CLI is installed, "
    b"run `codegraph init -y` to create the index; if the index exists and "
    b"`codegraph status --json` shows pending changes, run `codegraph sync` first "
    b"(`codegraph index` when it reports a reindex is recommended)."
)
HOST_ORDER = ("claude", "codex", "gemini", "opencode")


class Change(NamedTuple):
    host: str
    path: str
    status: str  # "replace", "already", or a skip reason
    before: bytes | None
    after: bytes | None
    detail: str = ""


def global_instruction_paths(env) -> list[tuple[str, str]]:
    """Return (host, path) for the four global files, using codegraph 1.6.2's resolvers."""
    home = env.get("HOME", "")
    claude_dir = env.get("CLAUDE_CONFIG_DIR", "")
    claude_base = (
        os.path.abspath(claude_dir) if claude_dir.strip() else os.path.join(home, ".claude")
    )
    codex_dir = env.get("CODEX_HOME", "")
    codex_base = codex_dir if codex_dir.strip() else os.path.join(home, ".codex")
    xdg = env.get("XDG_CONFIG_HOME", "")
    xdg_base = xdg if xdg.strip() else os.path.join(home, ".config")
    return [
        ("claude", os.path.join(claude_base, "CLAUDE.md")),
        ("codex", os.path.join(codex_base, "AGENTS.md")),
        ("gemini", os.path.join(home, ".gemini", "GEMINI.md")),
        ("opencode", os.path.join(xdg_base, "opencode", "AGENTS.md")),
    ]


def _read(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def plan_changes(env) -> list[Change]:
    """Plan one Change per host, in HOST_ORDER; never raises on a per-file I/O error."""
    changes = []
    for host, path in global_instruction_paths(env):
        if not os.path.lexists(path):
            changes.append(Change(host, path, "missing_file", None, None))
            continue
        real = os.path.realpath(path)
        if not os.path.isfile(real):
            changes.append(Change(host, path, "not_regular", None, None))
            continue
        try:
            data = _read(real)
        except OSError as exc:
            changes.append(Change(host, path, "unreadable", None, None, exc.strerror or str(exc)))
            continue
        edited, reason = replace_in_block(data, START, END, INSTALLER_SENTENCE, AIKIT_SENTENCE)
        if reason == "replaced":
            changes.append(Change(host, path, "replace", data, edited))
        else:
            changes.append(
                Change(host, path, "already" if reason == "already" else reason, data, None)
            )
    return changes


_SKIP_TEXT = {
    "missing_file": "missing file",
    "not_regular": "not a regular file",
    "no_block": "no codegraph block",
    "one_marker": "block with only one marker",
    "no_sentence": "block without codegraph's sentence",
}


def preview_lines(changes) -> list[str]:
    lines = []
    for change in changes:
        head = f"{change.host} {change.path}"
        if change.status == "replace":
            lines.append(f"{head}: replace codegraph's sentence")
            lines.append(f"  - {INSTALLER_SENTENCE.decode('utf-8')}")
            lines.append(f"  + {AIKIT_SENTENCE.decode('utf-8')}")
        elif change.status == "already":
            lines.append(f"{head}: already ai-kit's wording")
        elif change.status == "unreadable":
            lines.append(f"{head}: skipped: unreadable ({change.detail})")
        else:
            lines.append(f"{head}: skipped: {_SKIP_TEXT.get(change.status, change.status)}")
    return lines


def _backup_dir(env) -> str:
    state = env.get("XDG_STATE_HOME", "")
    base = state if state.strip() else os.path.join(env.get("HOME", ""), ".local", "state")
    return os.path.join(base, "ai-kit", "backups", "global-rules")


def _claim_backup(directory: str, name: str, data: bytes) -> str:
    """Write `data` under a name no earlier backup holds: `name`, then `name-1`, `name-2`, ..."""
    os.makedirs(directory, mode=0o700, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".claim-")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o600)
        number = 0
        while True:
            candidate = os.path.join(directory, name if number == 0 else f"{name}-{number}")
            try:
                os.link(tmp, candidate)
                return candidate
            except FileExistsError:
                number += 1
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)


def _replace_file(real: str, data: bytes) -> None:
    """Atomically replace `real` with `data`, keeping its mode; the temp file lives beside it."""
    mode = stat.S_IMODE(os.stat(real).st_mode)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(real), prefix=".ai-kit-global-")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, real)
    except OSError:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def _stamp(now: datetime.datetime) -> str:
    return now.astimezone(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def apply(
    env,
    dry: bool,
    now: datetime.datetime | None = None,
    before_replace: Callable[[str], None] | None = None,
    reviewed: list[Change] | None = None,
) -> tuple[bool, list[str]]:
    """Rewrite the replace-status files; return (every requested write succeeded, lines).

    `reviewed` is the Change list the user saw: only those files are written, and only while
    their bytes still equal the reviewed `before`. Skips are not failures; backup and write
    failures are.
    """
    changes = plan_changes(env)
    if dry:
        return True, preview_lines(changes)
    reviewed_by_path = {c.path: c for c in reviewed} if reviewed is not None else None
    when = now or datetime.datetime.now(datetime.UTC)
    directory = _backup_dir(env)
    ok, lines = True, []
    for change in changes:
        if change.status != "replace":
            lines.extend(preview_lines([change]))
            continue
        skipped = _reviewed_skip(change, reviewed_by_path)
        if skipped:
            lines.append(skipped)
            continue
        written, line = _write_change(change, directory, when, before_replace)
        ok = ok and written
        lines.append(line)
    return ok, lines


def _reviewed_skip(change: Change, reviewed_by_path) -> str | None:
    """The skip line when `change` was not reviewed or changed since review, else None."""
    head = f"{change.host} {change.path}"
    if reviewed_by_path is None:
        return None
    seen = reviewed_by_path.get(change.path)
    if seen is None:
        return f"{head}: not reviewed; not written, review again"
    if seen.before != change.before:
        return f"{head}: changed since it was reviewed; not written, review again"
    return None


def _write_change(change: Change, directory, when, before_replace) -> tuple[bool, str]:
    """Back up one file, then replace it; return (succeeded, report line)."""
    head = f"{change.host} {change.path}"
    if change.before is None or change.after is None:
        return False, f"{head}: no bytes to write; not written"
    real = os.path.realpath(change.path)
    name = f"{change.host}-{_stamp(when)}-{os.path.basename(change.path)}"
    try:
        backup = _claim_backup(directory, name, change.before)
    except OSError as exc:
        return False, f"{head}: backup failed ({exc.strerror or exc}); not written"
    if before_replace is not None:
        before_replace(change.path)
    if _read(real) != change.before:
        return True, f"{head}: changed since it was read; not written, retried on the next install"
    try:
        _replace_file(real, change.after)
    except OSError as exc:
        return False, f"{head}: write failed ({exc.strerror or exc}); not written"
    return True, f"{head}: rewrote codegraph's sentence (backup {backup})"


def summary(env) -> str:
    """The doctor row's value: which wording each file holds; never raises."""
    try:
        changes = plan_changes(env)
    except OSError as exc:
        return f"unknown ({exc.strerror or exc})"
    installer = [c.host for c in changes if c.status == "replace"]
    unreadable = [c.host for c in changes if c.status == "unreadable"]
    if installer:
        value = f"installer wording: {', '.join(installer)}"
    elif any(c.status == "already" for c in changes):
        value = "ai-kit wording"
    else:
        value = "no codegraph block"
    if unreadable:
        value += f"; unreadable: {', '.join(unreadable)}"
    return value
