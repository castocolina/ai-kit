"""Migrate a leftover codegraph installer block to ai-kit's codebase-memory-mcp block.

Applies to the four global instruction files. A file that already holds a
codebase-memory-mcp block keeps it and every other byte; a complete codegraph block
beside it is removed (`_plan_remove` states the line rule). Bytes in and bytes out, with a
backup written before each file. The only writer of those files in ai-kit (SPEC R11, D-11).
Stdlib only; never imports setup.py.
"""

import contextlib
import datetime
import os
import re
import stat
import tempfile
from collections.abc import Callable
from typing import NamedTuple

from marked_block import find_block

LEGACY_START = b"<!-- CODEGRAPH_START -->"  # codegraph's block, migrated to codebase-memory-mcp
LEGACY_END = b"<!-- CODEGRAPH_END -->"  # codegraph's block, migrated to codebase-memory-mcp
CBM_START = b"<!-- codebase-memory-mcp:start -->"
CBM_END = b"<!-- codebase-memory-mcp:end -->"
_BLOCK_BODY = (
    b"## codebase-memory-mcp (code and doc exploration)\n"
    b"\n"
    b"Before grep, find or broad file reads, query the codebase-memory-mcp graph: "
    b"`search_graph` (symbols and doc sections), `trace_path` (callers and callees), "
    b"`get_code_snippet` (source), `query_graph` (Cypher), `get_architecture` "
    b"(overview). Call `check_index_coverage` with every path you cite. When "
    b"`list_projects` has no project whose root contains the working directory, run "
    b"`index_repository` on the repository root. Without the MCP tools, run "
    b"`codebase-memory-mcp cli <tool> --flag value`. Use `rg` for literals and config "
    b"values."
)
AIKIT_BLOCK = CBM_START + b"\n" + _BLOCK_BODY + b"\n" + CBM_END
WRITE_STATUSES = ("replace", "remove")  # the statuses `apply` writes
HOST_ORDER = ("claude", "codex", "gemini", "opencode")
_MARKERS = (CBM_START, CBM_END, LEGACY_START, LEGACY_END)


class Change(NamedTuple):
    host: str
    path: str
    status: str  # "replace", "remove", "already", "ambiguous", or a skip reason
    before: bytes | None
    after: bytes | None
    detail: str = ""


def global_instruction_paths(env) -> list[tuple[str, str]]:
    """Return (host, path) for the four global files.

    codebase-memory-mcp replaced codegraph 1.6.2, whose installer wrote these files.
    A leftover codegraph block can remain there; codebase-memory-mcp migrates it.
    """
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


def _plan_remove(host: str, path: str, data: bytes, cbm, legacy) -> Change:
    """A file with both blocks: drop the legacy block's lines, every other byte equal.

    The block's own line ending goes with it; a blank line left on both sides collapses to one
    (or to none at the start of the file); a block that ended the file leaves the file ending the
    way it ended before (one line ending, or none). A legacy block that overlaps the
    codebase-memory-mcp block is skipped whole (ambiguous), never cut."""
    cbm_from, cbm_to = cbm[0] - len(CBM_START), cbm[1] + len(CBM_END)
    begin, end = legacy[0] - len(LEGACY_START), legacy[1] + len(LEGACY_END)
    if not (end <= cbm_from or begin >= cbm_to):
        return Change(host, path, "ambiguous", data, None)
    head, rest = data[:begin], data[end:]
    ending = re.match(rb"\r?\n", rest)
    if ending:
        rest = rest[ending.end() :]
    blank = re.match(rb"\r?\n", rest)
    if not rest:
        head = head.rstrip(b"\r\n") + (ending.group(0) if ending and head.strip() else b"")
    elif blank and (not head or re.search(rb"\r?\n\r?\n$", head)):
        rest = rest[blank.end() :]
    return Change(host, path, "remove", data, head + rest)


def _plan_one(host: str, path: str, data: bytes) -> Change:
    """Decide one file's Change from its bytes; a repeated marker is never migrated."""
    if any(data.count(marker) > 1 for marker in _MARKERS):
        # find_block takes the first start and the next end; with repeated or nested markers
        # that span could swallow text between blocks, so the file is skipped whole.
        return Change(host, path, "ambiguous", data, None)
    cbm = find_block(data, CBM_START, CBM_END)
    if cbm != "no_block":
        if not isinstance(cbm, tuple):
            return Change(host, path, "one_marker", data, None)
        legacy = find_block(data, LEGACY_START, LEGACY_END)
        if not isinstance(legacy, tuple):
            return Change(host, path, "already", data, None)
        return _plan_remove(host, path, data, cbm, legacy)
    legacy = find_block(data, LEGACY_START, LEGACY_END)
    if isinstance(legacy, str):
        return Change(host, path, legacy, data, None)
    begin, finish = legacy
    after = (
        data[: begin - len(LEGACY_START)] + AIKIT_BLOCK + data[finish + len(LEGACY_END) :]
    )
    return Change(host, path, "replace", data, after)


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
        changes.append(_plan_one(host, path, data))
    return changes


_SKIP_TEXT = {
    "missing_file": "missing file",
    "not_regular": "not a regular file",
    "no_block": "no codegraph or codebase-memory-mcp block",
    "one_marker": "block with only one marker",
    "ambiguous": "repeated or nested block markers",
}


def _old_block_lines(data: bytes) -> list[str]:
    """The whole legacy block, markers included, as `  - ` preview lines."""
    span = find_block(data, LEGACY_START, LEGACY_END)
    if isinstance(span, str):
        return []
    begin, finish = span
    old = data[begin - len(LEGACY_START) : finish + len(LEGACY_END)]
    return [f"  - {line}" for line in old.decode("utf-8", errors="replace").splitlines()]


def preview_lines(changes) -> list[str]:
    lines = []
    for change in changes:
        head = f"{change.host} {change.path}"
        if change.status == "replace":
            lines.append(f"{head}: replace the codegraph block with the codebase-memory-mcp block")
            lines.extend(_old_block_lines(change.before))
            lines.extend(f"  + {line}" for line in AIKIT_BLOCK.decode("utf-8").splitlines())
        elif change.status == "remove":
            lines.append(f"{head}: remove the leftover codegraph block (the codebase-memory-mcp "
                         "block stays)")
            lines.extend(_old_block_lines(change.before))
        elif change.status == "already":
            lines.append(f"{head}: already holds the codebase-memory-mcp block")
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
        if change.status not in WRITE_STATUSES:
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
    done = ("removed the leftover codegraph block beside the codebase-memory-mcp block"
            if change.status == "remove"
            else "replaced the codegraph block with the codebase-memory-mcp block")
    return True, f"{head}: {done} (backup {backup})"


def summary(env) -> str:
    """The doctor row's value: which block each file holds; never raises."""
    try:
        changes = plan_changes(env)
    except OSError as exc:
        return f"unknown ({exc.strerror or exc})"
    installer = [c.host for c in changes if c.status == "replace"]
    beside = [c.host for c in changes if c.status == "remove"]
    ambiguous = [c.host for c in changes if c.status == "ambiguous"]
    unreadable = [c.host for c in changes if c.status == "unreadable"]
    parts = []
    if installer:
        parts.append(
            f"leftover codegraph block (codebase-memory-mcp replaces it): {', '.join(installer)}"
        )
    if beside:
        parts.append(
            f"leftover codegraph block beside the codebase-memory-mcp block: {', '.join(beside)}"
        )
    if parts:
        value = "; ".join(parts)
    elif any(c.status == "already" for c in changes):
        value = "codebase-memory-mcp block"
    else:
        value = "no block"
    if unreadable:
        value += f"; unreadable: {', '.join(unreadable)}"
    if ambiguous:
        value += f"; ambiguous markers: {', '.join(ambiguous)}"
    return value
