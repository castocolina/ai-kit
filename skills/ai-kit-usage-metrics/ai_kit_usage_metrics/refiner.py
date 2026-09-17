"""Cross-runtime refinement: decompose, resolve cwd, attribute tokens once per turn."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta, timezone

from ai_kit_usage_metrics.cwd_state import CwdState
from ai_kit_usage_metrics.decomposer import decompose
from ai_kit_usage_metrics.family import family_of
from ai_kit_usage_metrics.pricing import estimate_price

_SENTINEL_MIN = ""
_STATE_MACHINE_RUNTIMES = frozenset({"opencode", "codex", "cursor"})

# D-19: Codex's post-2026-07-27 tool-call shape wraps a JS-source-string
# body that awaits a `tools.*(...)` call. Only names whose JSON argument
# object represents an actual shell invocation belong here -- grounded by
# a real-store enumeration (see 15.1-02-SUMMARY.md), not guessed. A name
# such as `web__run` or `apply_patch` is a real observed `tools.*` call in
# the same wrapper shape that must NOT be treated as a command.
_CODEX_EXEC_TOOL_NAMES = frozenset({"exec_command"})
_CODEX_TOOL_CALL_RE = re.compile(
    r"tools\.(?:" + "|".join(re.escape(name) for name in _CODEX_EXEC_TOOL_NAMES) + r")\("
)
# Memoizes _codex_custom_tool_args's one JSON decode per record so its two
# independent consumers (_codex_custom_tool_cmd, _codex_custom_tool_workdir)
# each stay a simple str | None call while paying the raw_decode cost once.
# Cleared at the start of every refine_all() call -- id() can be recycled
# across GC'd payload dicts within one process, so a memo that outlives its
# batch could return another record's parsed args.
_CODEX_CUSTOM_TOOL_ARGS_MEMO: dict[int, dict | None] = {}

# Cursor's reverse-engineered transcript sometimes embeds a localised,
# human-readable stamp inside a `<timestamp>...</timestamp>` block, e.g.
# "Monday, Aug 31, 2026, 1:24 AM (UTC-4)" (D-16 date / D-19).
_CURSOR_TIMESTAMP_BLOCK_RE = re.compile(r"<timestamp>(.*?)</timestamp>", re.S)
_CURSOR_TIMESTAMP_HEAD_FORMAT = "%A, %b %d, %Y, %I:%M %p"
_CURSOR_TIMESTAMP_OFFSET_MARKER = " (UTC"


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _duration_ms(start: str | None, end: str | None) -> int | None:
    begin = _parse_ts(start)
    finish = _parse_ts(end)
    if begin is None or finish is None:
        return None
    return int((finish - begin).total_seconds() * 1000)


def _tool_result_timestamps(records: list[dict]) -> dict[str, str]:
    found: dict[str, str] = {}
    for rec in records:
        payload = rec.get("payload")
        if not isinstance(payload, dict):
            continue
        message = payload.get("message") or {}
        content = message.get("content") or []
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            tool_id = block.get("tool_use_id")
            timestamp = payload.get("timestamp")
            if tool_id and timestamp:
                found[tool_id] = timestamp
    return found


def _first_bash_tool_use(payload: dict) -> dict | None:
    if payload.get("type") != "assistant":
        return None
    message = payload.get("message") or {}
    content = message.get("content") or []
    if not isinstance(content, list):
        return None
    for block in content:
        if (
            isinstance(block, dict)
            and block.get("type") == "tool_use"
            and block.get("name") == "Bash"
        ):
            return block
    return None


def _group_key(rec: dict) -> tuple:
    session_id = rec.get("session_id")
    if session_id is None:
        payload = rec.get("payload")
        if isinstance(payload, dict):
            session_id = payload.get("sessionId")
    return (rec.get("runtime"), session_id)


def _sort_key(rec: dict) -> tuple:
    if rec.get("runtime") == "opencode":
        time_created = rec.get("time_created")
        if time_created is None:
            time_created = 0
        return (time_created, rec.get("record_id") or "")
    timestamp = rec.get("timestamp")
    if timestamp is None:
        payload = rec.get("payload")
        if isinstance(payload, dict):
            timestamp = payload.get("timestamp")
    source_line = rec.get("source_line")
    if source_line is None:
        source_line = 0
    if timestamp is not None:
        return (timestamp, source_line)
    return (_SENTINEL_MIN, source_line)


def _claude_command(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    tool_use = _first_bash_tool_use(payload)
    if tool_use is None:
        return None
    command = (tool_use.get("input") or {}).get("command")
    return command if isinstance(command, str) else None


def _opencode_command(rec: dict, payload: object) -> str | None:
    if rec.get("source_kind") != "part":
        return None
    if not isinstance(payload, dict) or payload.get("tool") != "bash":
        return None
    state = payload.get("state")
    input_obj = state.get("input") if isinstance(state, dict) else None
    command = input_obj.get("command") if isinstance(input_obj, dict) else None
    return command if isinstance(command, str) else None


def _codex_parsed_cmd(arguments: object) -> str | None:
    if not isinstance(arguments, str):
        return None
    try:
        parsed = json.loads(arguments)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    cmd = parsed.get("cmd")
    return cmd if isinstance(cmd, str) else None


def _codex_command(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    inner = payload.get("payload")
    if not isinstance(inner, dict):
        return None
    if inner.get("type") != "function_call" or inner.get("name") != "exec_command":
        return None
    return _codex_parsed_cmd(inner.get("arguments"))


def _codex_custom_tool_args(payload: object) -> dict | None:
    """Recognise and parse codex's post-2026-07-27 `custom_tool_call` shape.

    `payload` is the raw record's top-level payload (mirroring `_codex_command`'s
    convention). The inner `input` field is a JavaScript source string -- not a
    JSON document -- that awaits an allow-listed `tools.*(...)` call whose single
    argument is a JSON object literal. Locates the call site with a regex, then
    hands the stdlib decoder the exact position right after the opening
    parenthesis: `json.JSONDecoder().raw_decode` is "parse one JSON value
    starting here, tell me where it ended" -- no hand-rolled brace counting, no
    substring search for a `cmd` key (which would false-match `web__run`'s
    `search_query` object). The single decode site is memoized per-payload so
    both `_codex_custom_tool_cmd` and `_codex_custom_tool_workdir` can call this
    without re-decoding the same body.
    """
    if not isinstance(payload, dict):
        return None
    memo_key = id(payload)
    if memo_key in _CODEX_CUSTOM_TOOL_ARGS_MEMO:
        return _CODEX_CUSTOM_TOOL_ARGS_MEMO[memo_key]
    result = _parse_codex_custom_tool_args(payload)
    _CODEX_CUSTOM_TOOL_ARGS_MEMO[memo_key] = result
    return result


def _parse_codex_custom_tool_args(payload: dict) -> dict | None:
    inner = payload.get("payload")
    if not isinstance(inner, dict):
        return None
    if inner.get("type") != "custom_tool_call" or inner.get("name") != "exec":
        return None
    body = inner.get("input")
    if not isinstance(body, str):
        return None
    match = _CODEX_TOOL_CALL_RE.search(body)
    if match is None:
        return None
    try:
        parsed, _end = json.JSONDecoder().raw_decode(body, match.end())
    except (ValueError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _codex_custom_tool_cmd(payload: object) -> str | None:
    args = _codex_custom_tool_args(payload)
    if args is None:
        return None
    cmd = args.get("cmd")
    return cmd if isinstance(cmd, str) else None


def _codex_custom_tool_workdir(payload: object) -> str | None:
    args = _codex_custom_tool_args(payload)
    if args is None:
        return None
    workdir = args.get("workdir")
    return workdir or None


def _cursor_command(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    message = payload.get("message") or {}
    content = message.get("content") or []
    if not isinstance(content, list):
        return None
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use" and block.get("name") == "Shell":
            command = (block.get("input") or {}).get("command")
            return command if isinstance(command, str) else None
    return None


def _command_text(rec: dict) -> str | None:
    runtime = rec.get("runtime")
    payload = rec.get("payload")
    if runtime == "claude":
        return _claude_command(payload)
    if runtime == "opencode":
        return _opencode_command(rec, payload)
    if runtime == "codex":
        command = _codex_command(payload)
        if command is not None:
            return command
        return _codex_custom_tool_cmd(payload)
    if runtime == "cursor":
        return _cursor_command(payload)
    return None


def _opencode_workdir(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    state = payload.get("state")
    input_obj = state.get("input") if isinstance(state, dict) else None
    if not isinstance(input_obj, dict):
        return None
    workdir = input_obj.get("workdir")
    return workdir or None


def _cwd_state_resolver(rec: dict, step: dict, cwd_state: CwdState) -> str:
    del rec
    resolved = cwd_state.resolve_for(step["text"])
    cwd_state.observe(step["text"])
    return resolved


def _opencode_cwd_resolver(rec: dict, step: dict, cwd_state: CwdState) -> str:
    workdir = _opencode_workdir(rec.get("payload"))
    if workdir:
        cwd_state.current = workdir
        cwd_state.observe(step["text"])
        return workdir
    resolved = cwd_state.resolve_for(step["text"])
    cwd_state.observe(step["text"])
    return resolved


RESOLVE_CWD = {
    "claude": _cwd_state_resolver,
    "opencode": _opencode_cwd_resolver,
    "codex": _cwd_state_resolver,
    "cursor": _cwd_state_resolver,
}


def _codex_seed_cwd(rec: dict, cwd_state: CwdState) -> None:
    """Seed the record's `custom_tool_call` workdir into `cwd_state`, once.

    Called from `_rows_for_record` ABOVE the per-step loop -- never from
    inside it. `RESOLVE_CWD["codex"]` intentionally stays `_cwd_state_resolver`:
    with the record-level workdir already applied here, the generic
    `resolve_for` -> `observe` sequence is correct for every step, including a
    compound command like `cd src && pwd` under `workdir=/repo`, whose second
    step must see `/repo/src` -- not get reset back to `/repo`. This function
    only assigns `cwd_state.current`; it never calls `observe` or `resolve_for`,
    and it leaves `cwd_state` untouched when no workdir is present (a legacy
    `function_call` record, or a `custom_tool_call` with no `workdir` key), so
    the session's accumulated directory carries forward.
    """
    workdir = _codex_custom_tool_workdir(rec.get("payload"))
    if workdir:
        cwd_state.current = workdir


def _seed_opencode_cwd(recs: list[dict]) -> str:
    # Prefer the first message envelope's data.path.cwd; fall back to the
    # session envelope's directory field if the message path is absent.
    for rec in recs:
        payload = rec.get("payload")
        if rec.get("source_kind") == "message" and isinstance(payload, dict):
            path = payload.get("path")
            if isinstance(path, dict) and path.get("cwd"):
                return path["cwd"]
        if rec.get("source_kind") == "session" and isinstance(payload, dict) and payload.get(
            "directory"
        ):
            return payload["directory"]
    return "unknown"


def _seed_codex_cwd(recs: list[dict]) -> str:
    for rec in recs:
        payload = rec.get("payload")
        if not isinstance(payload, dict) or payload.get("type") != "session_meta":
            continue
        inner = payload.get("payload")
        if isinstance(inner, dict) and inner.get("cwd"):
            return inner["cwd"]
    return "unknown"


def _seed_cwd(runtime: str, recs: list[dict]) -> str:
    if runtime == "opencode":
        return _seed_opencode_cwd(recs)
    if runtime == "codex":
        return _seed_codex_cwd(recs)
    # Cursor: no session-level directory is reachable from
    # agent-transcripts/*.jsonl. Seed honestly at "unknown"; resolved_cwd
    # only changes when a later step's own text contains a literal `cd`.
    return "unknown"


def _claude_attr(rec: dict, env: dict) -> dict:
    payload = rec.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    message = payload.get("message") or {}
    usage = message.get("usage") or {}
    tokens_in = usage.get("input_tokens")
    tokens_out = usage.get("output_tokens")
    model = message.get("model")
    price, conf = estimate_price("anthropic", model, tokens_in, tokens_out, env)
    return {
        "turn_id": payload.get("uuid"),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "model": model,
        "price": price,
        "price_confidence": conf,
    }


def _opencode_messages(recs: list[dict]) -> dict:
    return {
        rec["record_id"]: rec
        for rec in recs
        if rec.get("source_kind") == "message" and rec.get("parse_status") == "ok"
    }


def _opencode_attr(rec: dict, messages: dict, env: dict) -> dict:
    message_id = rec.get("message_id")
    msg = messages.get(message_id) if message_id else None
    if msg is None:
        return {
            "turn_id": message_id,
            "tokens_in": None,
            "tokens_out": None,
            "model": None,
            "price": None,
            "price_confidence": "unknown",
        }
    payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
    tokens = payload.get("tokens") or {}
    tokens_in = tokens.get("input")
    tokens_out = tokens.get("output")
    model_id = payload.get("modelID")
    provider_id = payload.get("providerID")
    cost = payload.get("cost")
    if cost is not None:
        price, conf = cost, "high"
    else:
        price, conf = estimate_price(
            provider_id or "", model_id or "", tokens_in, tokens_out, env
        )
    model = None
    if provider_id and model_id:
        model = f"{provider_id}/{model_id}"
    elif model_id:
        model = model_id
    return {
        "turn_id": message_id,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "model": model,
        "price": price,
        "price_confidence": conf,
    }


def _codex_intervals(recs: list[dict]) -> list[tuple]:
    intervals: list[tuple] = []
    prev_in = prev_out = None
    for rec in recs:
        payload = rec.get("payload")
        if not isinstance(payload, dict) or payload.get("type") != "event_msg":
            continue
        inner = payload.get("payload")
        if not isinstance(inner, dict) or inner.get("type") != "token_count":
            continue
        usage = (inner.get("info") or {}).get("total_token_usage") or {}
        this_in = usage.get("input_tokens") or 0
        this_out = usage.get("output_tokens") or 0
        if prev_in is None or prev_out is None:
            delta_in, delta_out = this_in, this_out
        else:
            delta_in = this_in - prev_in
            delta_out = this_out - prev_out
        prev_in, prev_out = this_in, this_out
        intervals.append((rec.get("source_line"), delta_in, delta_out))
    return intervals


def _codex_attr(rec: dict, intervals: list[tuple], env: dict) -> dict:
    line = rec.get("source_line")
    chosen = None
    for source_line, delta_in, delta_out in intervals:
        if line is not None and source_line is not None and source_line <= line:
            chosen = (source_line, delta_in, delta_out)
    if chosen is None:
        return {
            "turn_id": None,
            "tokens_in": None,
            "tokens_out": None,
            "model": "unknown",
            "price": None,
            "price_confidence": "unknown",
        }
    source_line, delta_in, delta_out = chosen
    price, conf = estimate_price("openai", "unknown", delta_in, delta_out, env)
    return {
        "turn_id": source_line,
        "tokens_in": delta_in,
        "tokens_out": delta_out,
        "model": "unknown",
        "price": price,
        "price_confidence": conf,
    }


def _cursor_attr() -> dict:
    return {
        "turn_id": None,
        "tokens_in": None,
        "tokens_out": None,
        "model": None,
        "price": None,
        "price_confidence": "unknown",
    }


def _opencode_timestamp(rec: dict) -> str | None:
    # Mirrors _parse_ts's guard style: opencode's raw envelope (capture_opencode.py's
    # _base_envelope) never sets a "timestamp" key anywhere -- only "time_created", an
    # epoch-millisecond int. Only reached from _row_timestamp after both existing
    # lookups miss and runtime == "opencode" (D-16 / D-19).
    time_created = rec.get("time_created")
    if not isinstance(time_created, int):
        return None
    return datetime.fromtimestamp(time_created / 1000, tz=UTC).isoformat()


def _row_timestamp(rec: dict):
    value = rec.get("timestamp")
    if value is not None:
        return value
    payload = rec.get("payload")
    payload_ts = payload.get("timestamp") if isinstance(payload, dict) else None
    if payload_ts is not None:
        return payload_ts
    if rec.get("runtime") == "opencode":
        return _opencode_timestamp(rec)
    return None


def _cursor_timestamp_text(payload: object) -> str | None:
    """Return the inner text of the first `<timestamp>` block, or None.

    Only the first `type == "text"` content block of
    `payload["message"]["content"]` is inspected -- matching the shape observed
    in the real captured store (D-16 date / D-19). Every drill-down is
    `isinstance`-guarded, matching this module's other extractors.
    """
    if not isinstance(payload, dict):
        return None
    message = payload.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if not isinstance(content, list) or not content:
        return None
    block = content[0]
    if not isinstance(block, dict) or block.get("type") != "text":
        return None
    text = block.get("text")
    if not isinstance(text, str):
        return None
    match = _CURSOR_TIMESTAMP_BLOCK_RE.search(text)
    return match.group(1) if match else None


def _parse_cursor_offset(offset_text: str) -> timezone | None:
    if offset_text == "":
        return UTC
    sign = offset_text[0]
    if sign not in "+-":
        return None
    body = offset_text[1:]
    hour_text, _, minute_text = body.partition(":")
    if not hour_text.isdigit() or (minute_text and not minute_text.isdigit()):
        return None
    hours = int(hour_text)
    minutes = int(minute_text) if minute_text else 0
    delta = timedelta(hours=hours, minutes=minutes)
    if sign == "-":
        delta = -delta
    return timezone(delta)


def _parse_cursor_timestamp(text: str) -> str | None:
    """Parse cursor's localised stamp, e.g. `Monday, Aug 31, 2026, 1:24 AM (UTC-4)`.

    Any parse failure returns None -- never substitute `captured_at`, which
    would present a fabricated value at the same confidence as a real one.
    """
    if not isinstance(text, str):
        return None
    idx = text.find(_CURSOR_TIMESTAMP_OFFSET_MARKER)
    if idx == -1:
        return None
    head = text[:idx]
    tail = text[idx + len(_CURSOR_TIMESTAMP_OFFSET_MARKER) :]
    if not tail.endswith(")"):
        return None
    offset_text = tail[:-1]
    try:
        naive = datetime.strptime(head, _CURSOR_TIMESTAMP_HEAD_FORMAT)
    except ValueError:
        return None
    tzinfo = _parse_cursor_offset(offset_text)
    if tzinfo is None:
        return None
    return naive.replace(tzinfo=tzinfo).isoformat()


def _cursor_timestamps(recs: list[dict]) -> list[tuple]:
    """Build `(source_line, iso)` pairs, ascending, for every parsable record.

    Mirrors `_codex_intervals`'s per-group builder shape -- `_cursor_timestamp_for`
    then picks the LAST entry at or before a given record, the same selection
    idiom `_codex_attr` uses for token intervals.
    """
    entries: list[tuple] = []
    for rec in recs:
        text = _cursor_timestamp_text(rec.get("payload"))
        if text is None:
            continue
        iso = _parse_cursor_timestamp(text)
        if iso is None:
            continue
        entries.append((rec.get("source_line"), iso))
    entries.sort(key=lambda pair: pair[0] if pair[0] is not None else -1)
    return entries


def _cursor_timestamp_for(rec: dict, entries: list[tuple]) -> str | None:
    line = rec.get("source_line")
    chosen = None
    for source_line, iso in entries:
        if line is not None and source_line is not None and source_line <= line:
            chosen = iso
    return chosen


def _claude_duration(rec: dict, result_ts: dict[str, str]) -> int | None:
    payload = rec.get("payload")
    if not isinstance(payload, dict):
        return None
    tool_use = _first_bash_tool_use(payload)
    if tool_use is None:
        return None
    tool_id = tool_use.get("id")
    if tool_id and tool_id in result_ts:
        return _duration_ms(payload.get("timestamp"), result_ts[tool_id])
    return None


def _empty_rtk_fields() -> dict:
    return {
        "rtk_input_tokens": None,
        "rtk_output_tokens": None,
        "rtk_saved_tokens": None,
        "rtk_savings_pct": None,
        "rtk_rewrote": None,
        "inferred_family": None,
        "inferred_confidence": None,
    }


def _build_row(rec: dict, step: dict, ctx: dict) -> dict:
    timestamp = _row_timestamp(rec)
    if timestamp is None:
        timestamp = ctx.get("timestamp_fallback")
    date = timestamp[:10] if isinstance(timestamp, str) and len(timestamp) >= 10 else None
    operator = step["operator"]
    attr = ctx["attr"]
    # D-16 family: only a "simple" step is a real single command -- a
    # control_flow_script/unclassified step is the ENTIRE opaque blob, and
    # family_of() applied to that blob deterministically returns garbage
    # (a bare control-flow keyword, an unterminated command-substitution
    # token, a shell function-definition line). Gate on the shape rather
    # than teaching family_of() to parse inside blobs it was never meant to.
    family = family_of(step["text"]) if step["command_shape"] == "simple" else ""
    row = {
        "raw_ref": rec.get("raw_ref"),
        "runtime": ctx["runtime"],
        "session_id": ctx["session_id"],
        "turn_id": attr["turn_id"],
        "date": date,
        "timestamp": timestamp,
        "model": attr["model"],
        "command_text": step["text"],
        "family": family,
        "command_shape": step["command_shape"],
        "step_index": step["step_index"],
        "step_count": ctx["step_count"],
        "operator": operator,
        "execution_certain": operator != "&&",
        "resolved_cwd": ctx["resolved_cwd"],
        "source_confidence": rec.get("source_confidence") or "high",
        "tokens_input": attr["tokens_in"],
        "tokens_output": attr["tokens_out"],
        "price": attr["price"],
        "price_confidence": attr["price_confidence"],
        "exec_duration_ms": ctx["duration"],
    }
    row.update(_empty_rtk_fields())
    return row


def _rows_for_record(rec: dict, ctx: dict) -> list[dict]:
    if rec.get("parse_status") != "ok":
        return []
    command = _command_text(rec)
    if command is None:
        return []
    steps = decompose(command)
    if not steps:
        return []
    runtime = ctx["runtime"]
    cwd_state = ctx["cwd_state"]
    if runtime == "claude":
        payload = rec.get("payload")
        seed = payload.get("cwd") if isinstance(payload, dict) else None
        cwd_state = CwdState(seed or "unknown")
    if runtime == "codex":
        _codex_seed_cwd(rec, cwd_state)
    resolver = RESOLVE_CWD[runtime]
    built = []
    row_ctx = {
        "runtime": runtime,
        "session_id": ctx["session_id"],
        "attr": ctx["attr"],
        "duration": ctx["duration"],
        "step_count": len(steps),
        "timestamp_fallback": ctx.get("timestamp_fallback"),
    }
    for step in steps:
        row_ctx["resolved_cwd"] = resolver(rec, step, cwd_state)
        built.append(_build_row(rec, step, row_ctx))
    return built


def _attr_for(runtime: str, rec: dict, lookup: dict, env: dict) -> dict:
    if runtime == "claude":
        return _claude_attr(rec, env)
    if runtime == "opencode":
        return _opencode_attr(rec, lookup.get("messages") or {}, env)
    if runtime == "codex":
        return _codex_attr(rec, lookup.get("intervals") or [], env)
    return _cursor_attr()


def _refine_runtime_group(runtime: str, session_id, recs: list[dict], env: dict) -> list[dict]:
    cwd_state = None
    if runtime in _STATE_MACHINE_RUNTIMES:
        cwd_state = CwdState(_seed_cwd(runtime, recs))
    lookup: dict = {}
    if runtime == "opencode":
        lookup["messages"] = _opencode_messages(recs)
    elif runtime == "codex":
        lookup["intervals"] = _codex_intervals(recs)
    elif runtime == "cursor":
        lookup["cursor_timestamps"] = _cursor_timestamps(recs)
    durations = _tool_result_timestamps(recs) if runtime == "claude" else {}
    rows: list[dict] = []
    for rec in recs:
        ctx = {
            "runtime": runtime,
            "session_id": session_id,
            "cwd_state": cwd_state,
            "attr": _attr_for(runtime, rec, lookup, env),
            "duration": _claude_duration(rec, durations) if runtime == "claude" else None,
            "timestamp_fallback": (
                _cursor_timestamp_for(rec, lookup.get("cursor_timestamps") or [])
                if runtime == "cursor"
                else None
            ),
        }
        rows.extend(_rows_for_record(rec, ctx))
    return rows


def _refine_rtk_record(rec: dict) -> dict | None:
    payload = rec.get("payload")
    if not isinstance(payload, dict) or payload.get("source_type") != "history":
        return None
    command = payload.get("original_cmd")
    if not isinstance(command, str):
        return None
    timestamp = payload.get("timestamp")
    date = timestamp[:10] if isinstance(timestamp, str) and len(timestamp) >= 10 else None
    row = {
        "raw_ref": rec.get("raw_ref"),
        "runtime": "rtk",
        "session_id": rec.get("session_id"),
        "turn_id": None,
        "date": date,
        "timestamp": timestamp,
        "model": None,
        "command_text": command,
        "family": family_of(command),
        "command_shape": "simple",
        "step_index": 0,
        "step_count": 1,
        "operator": None,
        "execution_certain": True,
        "resolved_cwd": payload.get("project_path"),
        "source_confidence": rec.get("source_confidence") or "high",
        "tokens_input": None,
        "tokens_output": None,
        "price": None,
        "price_confidence": "not_applicable",
        "rtk_input_tokens": payload.get("input_tokens"),
        "rtk_output_tokens": payload.get("output_tokens"),
        "rtk_saved_tokens": payload.get("saved_tokens"),
        "rtk_savings_pct": payload.get("savings_pct"),
        "rtk_rewrote": None,
        "inferred_family": None,
        "inferred_confidence": None,
        "exec_duration_ms": payload.get("exec_time_ms"),
    }
    return row


def refine_all(raw_records: list[dict], env: dict | None = None) -> list[dict]:
    """Build `refined_commands` rows for shell commands across all 5 sources."""
    env = env or {}
    # id() can be recycled across GC'd payload dicts within one process (tests
    # call refine_all() many times), so a memo that outlives its own batch
    # could return a stale/wrong-record's parsed custom_tool_call args.
    _CODEX_CUSTOM_TOOL_ARGS_MEMO.clear()
    grouped: dict[tuple, list[dict]] = {}
    for rec in raw_records:
        grouped.setdefault(_group_key(rec), []).append(rec)
    rows: list[dict] = []
    for (runtime, session_id), recs in grouped.items():
        ordered = sorted(recs, key=_sort_key)
        if runtime == "rtk":
            for rec in ordered:
                row = _refine_rtk_record(rec)
                if row is not None:
                    rows.append(row)
            continue
        if runtime not in RESOLVE_CWD:
            continue
        rows.extend(_refine_runtime_group(runtime, session_id, ordered, env))
    return rows
