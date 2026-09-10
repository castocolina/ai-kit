"""Wave-1 refiner: simple (non-compound) Claude Code Bash commands only."""

from __future__ import annotations

from datetime import datetime

from ai_kit_usage_metrics.family import family_of
from ai_kit_usage_metrics.pricing import estimate_price

_COMPOUND_CHARS = frozenset("&;|")


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


def _row_from_record(rec: dict, result_ts: dict[str, str], env: dict) -> dict | None:
    if rec.get("parse_status") != "ok":
        return None
    payload = rec.get("payload")
    if not isinstance(payload, dict):
        return None
    tool_use = _first_bash_tool_use(payload)
    if tool_use is None:
        return None
    command = (tool_use.get("input") or {}).get("command")
    if not isinstance(command, str):
        return None
    if any(ch in command for ch in _COMPOUND_CHARS):
        return None
    message = payload.get("message") or {}
    usage = message.get("usage") or {}
    tokens_in = usage.get("input_tokens")
    tokens_out = usage.get("output_tokens")
    timestamp = payload.get("timestamp")
    model = message.get("model")
    price, price_confidence = estimate_price(
        "anthropic", model, tokens_in, tokens_out, env
    )
    tool_id = tool_use.get("id")
    duration = None
    if tool_id and tool_id in result_ts:
        duration = _duration_ms(timestamp, result_ts[tool_id])
    date = timestamp[:10] if isinstance(timestamp, str) and len(timestamp) >= 10 else None
    return {
        "raw_ref": rec.get("raw_ref"),
        "runtime": "claude",
        "session_id": payload.get("sessionId"),
        "turn_id": payload.get("uuid"),
        "date": date,
        "timestamp": timestamp,
        "model": model,
        "command_text": command,
        "family": family_of(command),
        "command_shape": "simple",
        "step_index": 0,
        "step_count": 1,
        "operator": None,
        "execution_certain": True,
        "resolved_cwd": payload.get("cwd"),
        "source_confidence": "high",
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
        "price": price,
        "price_confidence": price_confidence,
        "rtk_input_tokens": None,
        "rtk_output_tokens": None,
        "rtk_saved_tokens": None,
        "rtk_savings_pct": None,
        "rtk_rewrote": None,
        "inferred_family": None,
        "inferred_confidence": None,
        "exec_duration_ms": duration,
    }


def refine_simple_commands(raw_records: list[dict], env: dict | None = None) -> list[dict]:
    """Build `refined_commands` rows for simple Bash tool_use envelopes.

    Operates on already-captured raw envelopes. A missing `input.command`, a
    non-ok parse_status, or any of `&` / `;` / `|` in the command produces no
    row (the raw envelope is left untouched).
    """
    env = env or {}
    by_session: dict = {}
    for rec in raw_records:
        payload = rec.get("payload")
        session_id = payload.get("sessionId") if isinstance(payload, dict) else None
        by_session.setdefault(session_id, []).append(rec)
    rows: list[dict] = []
    for recs in by_session.values():
        result_ts = _tool_result_timestamps(recs)
        for rec in recs:
            row = _row_from_record(rec, result_ts, env)
            if row is not None:
                rows.append(row)
    return rows
