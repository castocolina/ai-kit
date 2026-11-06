"""Claude probes and tool-use pickers for the Phase 23 D-02 status-line split."""
# pyright: strict

import json
import os
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, cast

from claude_payload import core_claude_data
from common_probe import (
    probe_ancestor_rss_bytes,
    probe_comm_via_proc,
    probe_comm_via_ps,
    probe_has_proc,
    probe_memo,
)
from common_types import util_safe_session

if TYPE_CHECKING:
    from common_render import Context

# ═══ 3. probe_ — side-effecting data gatherers (git / proc / fs / subprocess) ═


def probe_effort_setting_is_auto(work_dir: str, home: str) -> bool:
    """True when the effort *setting* is auto — i.e. `effortLevel` is absent (or
    literally "auto") across the settings chain.

    Precedence high->low: the project's .claude/settings.local.json, then
    .claude/settings.json, then ~/.claude/settings.json. The first file that defines
    `effortLevel` decides (explicit level -> not auto); if none define it, it's auto."""
    for path in (os.path.join(work_dir, ".claude", "settings.local.json"),
                 os.path.join(work_dir, ".claude", "settings.json"),
                 os.path.join(home, ".claude", "settings.json")):
        try:
            with open(path, encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(cfg, dict) and "effortLevel" in cfg:
            return str(cast(dict[str, Any], cfg)["effortLevel"]).strip().lower() == "auto"
    return True


def probe_is_claude(pid: int) -> bool | None:
    """True when pid's comm is `claude`, False otherwise, None when unreadable.

    Read through /proc, else `ps -o comm=`. `ps` can return a full path on macOS, so
    compare the basename."""
    name = probe_comm_via_proc(pid) if probe_has_proc() else probe_comm_via_ps(pid)
    if name is None:
        return None
    return os.path.basename(name) == "claude"


def probe_rss_bytes() -> int | None:
    """Resident memory (bytes) of the ancestor `claude` process, or None.

    The shared ancestor walk (common_probe) with Claude's `claude` matcher, 8 deep."""
    return probe_ancestor_rss_bytes(probe_is_claude, 8)


def probe_transcript_bytes(path: str) -> int | None:
    """Return the transcript file size in bytes, or None if it is missing."""
    if not path or not os.path.isfile(path):
        return None
    try:
        return os.path.getsize(path)
    except OSError:
        return None


_COMPACT_BOUNDARY_MARKER = b'"compact_boundary"'


def probe_transcript_compaction(path: str, total_bytes: int) -> tuple[int, int]:
    """Scan the transcript for compact_boundary markers. Returns
    (since_bytes, compact_count): since_bytes is the byte count from the start
    of the LAST compact_boundary record's line to EOF (== total_bytes when none
    found); compact_count is how many valid compact_boundary records were
    found. The compaction-marker JSON shape is Claude Code's internal, version-
    dependent format — a malformed/renamed shape (doesn't parse, or parses but
    isn't {"type":"system","subtype":"compact_boundary"}) is silently skipped,
    never raised; a missing/unreadable file degrades to (total_bytes, 0)."""
    last_offset: int | None = None
    count = 0
    try:
        with open(path, "rb") as f:
            offset = 0
            for raw_line in f:
                if _COMPACT_BOUNDARY_MARKER in raw_line:
                    try:
                        obj = json.loads(raw_line)
                    except json.JSONDecodeError:
                        obj = None
                    if isinstance(obj, dict):
                        rec = cast(dict[str, Any], obj)
                        if (rec.get("type") == "system"
                                and rec.get("subtype") == "compact_boundary"):
                            last_offset = offset
                            count += 1
                offset += len(raw_line)
    except OSError:
        return total_bytes, 0
    since = max(0, total_bytes - last_offset) if last_offset is not None else total_bytes
    return since, count


def probe_todo_from_tasks_dir(
    config_dir: str, session: Any
) -> tuple[str | None, str | None] | None:
    """Read Claude's materialized managed-Task state: one <id>.json per task under
    <config_dir>/tasks/<session>/. Returns (state, text) when task files exist
    (authoritative — may be (None, None) if all are done), else None to try the
    next source. This is O(task count) — no transcript replay."""
    if not util_safe_session(session):
        return None
    d = os.path.join(config_dir, "tasks", session)
    try:
        names = [n for n in os.listdir(d) if n.endswith(".json")]
    except OSError:
        return None
    if not names:
        return None
    # Sort by numeric id so creation order (and thus "last in_progress") is stable.
    tasks: list[dict[str, Any]] = []
    for n in sorted(names, key=lambda x: int(x[:-5]) if x[:-5].isdigit() else 0):
        try:
            with open(os.path.join(d, n), encoding="utf-8") as f:
                tasks.append(cast(dict[str, Any], json.load(f)))
        except (OSError, ValueError):
            continue
    return util_pick_from_tasks(tasks) or (None, None)


def probe_todo_from_todos_dir(
    config_dir: str, session: Any
) -> tuple[str | None, str | None] | None:
    """Read Claude's materialized TodoWrite snapshot: the most recent
    <config_dir>/todos/<session>*-agent-*.json (a single todos array). Returns
    (state, text) when such a file exists, else None to try the next source."""
    if not util_safe_session(session):
        return None
    d = os.path.join(config_dir, "todos")
    try:
        names = [n for n in os.listdir(d)
                 if n.startswith(session) and "-agent-" in n and n.endswith(".json")]
    except OSError:
        return None
    if not names:
        return None
    latest = max(names, key=lambda n: os.path.getmtime(os.path.join(d, n)))
    try:
        with open(os.path.join(d, latest), encoding="utf-8") as f:
            todos: Any = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(todos, list):
        return None
    return util_pick_from_todos(cast(list[dict[str, Any]], todos)) or (None, None)


def probe_todo_from_transcript(  # pylint: disable=too-many-branches
    path: str | None,
) -> tuple[str | None, str | None]:
    """Last-resort fallback: replay the transcript JSONL to reconstruct task /
    todo state. O(transcript size) — used only when no materialized state exists
    (e.g. running outside Claude Code, or an unrecognized on-disk layout)."""
    if not path or not os.path.isfile(path):
        return None, None

    tasks: list[dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as fh:
            todo_snapshots: list[list[dict[str, Any]]] = []
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj: Any = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(obj, dict):
                    continue
                task_names = ("TaskCreate", "TaskUpdate")
                for tu in util_iter_tool_uses(cast(dict[str, Any], obj), task_names):
                    inp: dict[str, Any] = cast(dict[str, Any], tu.get("input") or {})
                    if tu["name"] == "TaskCreate":
                        tasks.append({
                            "id": len(tasks) + 1,
                            "subject": inp.get("subject", ""),
                            "activeForm": inp.get("activeForm") or inp.get("subject", ""),
                            "status": "pending",
                        })
                    else:
                        tid = str(inp.get("taskId"))
                        for t in tasks:
                            if str(t["id"]) == tid and inp.get("status"):
                                t["status"] = inp["status"]
                for tu in util_iter_tool_uses(cast(dict[str, Any], obj), ("TodoWrite",)):
                    inp2: dict[str, Any] = cast(dict[str, Any], tu.get("input") or {})
                    todo_snapshots.append(cast(list[dict[str, Any]], inp2.get("todos") or []))
    except OSError:
        return None, None

    if tasks:
        return util_pick_from_tasks(tasks) or (None, None)
    if todo_snapshots:
        return util_pick_from_todos(todo_snapshots[-1]) or (None, None)
    return None, None


def probe_current_todo(path: str | None, session: str | None = None,
                 config_dir: str | None = None) -> tuple[str | None, str | None]:
    """Return (state, text) for the active TODO, or (None, None).

    Prefer Claude's materialized state on disk — the managed-Task files, then a
    TodoWrite snapshot — which is cheap (O(task count)) and authoritative. Only
    when neither exists do we replay the transcript (O(transcript size)). Without
    session/config_dir (direct/test calls) we go straight to the transcript."""
    if session and config_dir:
        for source in (probe_todo_from_tasks_dir, probe_todo_from_todos_dir):
            got = source(config_dir, session)
            if got is not None:
                return got
    return probe_todo_from_transcript(path)


def probe_effort_auto(ctx: "Context") -> bool:
    """Memoized: True when the Claude effort setting is 'auto'."""
    return probe_memo(ctx, "effort_auto",
                 lambda: probe_effort_setting_is_auto(ctx.work_dir, ctx.home))


def probe_todo(ctx: "Context") -> tuple[str | None, str | None]:
    """Memoized (state, text) pair for the active TODO, or (None, None)."""
    data = core_claude_data(ctx)
    return probe_memo(ctx, "todo",
                 lambda: probe_current_todo(data.transcript, data.session, data.claude_dir))


def probe_chat_size(ctx: "Context") -> int | None:
    """Memoized transcript file size in bytes, or None."""
    return probe_memo(
        ctx, "chat_size", lambda: probe_transcript_bytes(core_claude_data(ctx).transcript)
    )


def probe_chat_compaction(ctx: "Context") -> tuple[int, int] | None:
    """Memoized (since_bytes, compact_count) for the transcript — None exactly
    when probe_chat_size(ctx) is None (mirrors its 'no transcript' contract)."""
    total = probe_chat_size(ctx)
    if total is None:
        return None
    transcript = core_claude_data(ctx).transcript
    return probe_memo(ctx, "chat_compaction",
                 lambda: probe_transcript_compaction(transcript, total))


def probe_rss(ctx: "Context") -> int | None:
    """Memoized process RSS in bytes, or None."""
    return probe_memo(ctx, "rss", probe_rss_bytes)

# ═══ 5. util_ — pure non-format helpers (color / width / truncate / fit / parse)


def util_iter_tool_uses(
    line_obj: dict[str, Any], names: tuple[str, ...]
) -> Iterator[dict[str, Any]]:
    """Yield tool_use blocks whose name is in `names` from a transcript line object.
    In real transcripts message.content is a list of blocks for tool turns but
    a plain string for text turns — only iterate when it is a list of dicts."""
    msg: dict[str, Any] = cast(dict[str, Any], line_obj.get("message") or {})
    content: Any = msg.get("content")
    if not isinstance(content, list):
        return
    for item in cast(list[Any], content):
        if not isinstance(item, dict):
            continue
        block = cast(dict[str, Any], item)
        if block.get("type") == "tool_use" and block.get("name") in names:
            yield block


def util_pick_from_tasks(tasks: list[dict[str, Any]]) -> tuple[str, str] | None:
    """Choose the active task from a managed-Task list (creation order). Active =
    the last in_progress, else the first pending. Returns (state, text) or None."""
    in_prog = [t for t in tasks if t.get("status") == "in_progress"]
    if in_prog:
        return "in_progress", in_prog[-1].get("activeForm") or in_prog[-1].get("subject", "")
    pending = [t for t in tasks if t.get("status") == "pending"]
    if pending:
        return "pending", pending[0].get("subject", "")
    return None


def util_pick_from_todos(todos: list[dict[str, Any]]) -> tuple[str, str] | None:
    """Choose the active item from a TodoWrite snapshot. Active = the first
    in_progress, else the first pending. Returns (state, text) or None."""
    in_prog = [t for t in todos if t.get("status") == "in_progress"]
    if in_prog:
        return "in_progress", in_prog[0].get("activeForm", "")
    pending = [t for t in todos if t.get("status") == "pending"]
    if pending:
        return "pending", pending[0].get("content", "")
    return None
