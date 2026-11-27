"""Flat per-lane settings: write-side checks and cleaning; readers follow in plan 36-17.

Effort is checked by lane_effort; the data-use record by lane_data_use.
"""

import re
from typing import NamedTuple

from ai_kit_spec import lane_data_use

LANE_FLAG_KEYS = ("escalate_runtime", "escalate_model", "usage_limited", "interactive")
# role-table flag of [lanes.policy.execute]; kept out of LANE_FLAG_KEYS, which are lane-entry flags
SESSION_FALLBACK_KEY = "session_fallback"
# Settings for one pair are dropped on a pair change unless restated.
MODEL_BOUND = ("effort", "effort_source", "usage_limited", "usage_limit_note", "pool",
               "escalate_runtime", "escalate_model", *lane_data_use.DATA_USE_KEYS)
NOTE_MAX = 200
POOL_RX = re.compile(r"[A-Za-z0-9._-]{1,64}:[a-z]{1,16}")
_CONTROL_RX = re.compile(r"[\x00-\x1f\x7f-\x9f]")
FREE_LANE_REFUSAL = ("{key}: a free lane (pool set) needs the data-use record and its "
                     "confirmation; a declined or skipped lane is not written")
_REQUIRED_DATA_USE = tuple(name for name in lane_data_use.DATA_USE_KEYS if name != "data_use_label")


def clean_note(text: str) -> str:
    """One display line as typed: control characters removed, capped; never parsed."""
    return " ".join(_CONTROL_RX.sub(" ", text).split())[:NOTE_MAX].strip()


def normalise_lane_settings(entry: dict) -> dict:
    """Copy without false flags, with both display lines cleaned; nothing else changes."""
    result = dict(entry)
    for name in LANE_FLAG_KEYS:
        if result.get(name) is False:
            result.pop(name)
    if isinstance(result.get("usage_limit_note"), str):
        result["usage_limit_note"] = clean_note(result["usage_limit_note"])
        if not result["usage_limit_note"]:
            result.pop("usage_limit_note")
    if isinstance(result.get("data_use_line"), str):
        result["data_use_line"] = lane_data_use.clean_line(result["data_use_line"])
    return result


def _problems(entry: dict, key):
    for name in LANE_FLAG_KEYS:
        if name in entry and not isinstance(entry[name], bool):
            yield f"{key}: '{name}' must be a boolean"
    if "usage_limit_note" in entry:
        if not isinstance(entry["usage_limit_note"], str):
            yield f"{key}: 'usage_limit_note' must be a string"
        elif entry.get("usage_limited") is not True:
            yield f"{key}: 'usage_limit_note' needs 'usage_limited = true'"
    if "pool" in entry and not (isinstance(entry["pool"], str)
                                and POOL_RX.fullmatch(entry["pool"])):
        yield f"{key}: 'pool' must look like '<provider>:free'"
    if any(name in entry for name in lane_data_use.DATA_USE_KEYS):
        problem = lane_data_use.validate_note(entry)
        if problem:
            yield f"{key}: {problem}"


def validate_lane_settings(entry: dict, key) -> str | None:
    """The first problem with the lane's own settings, or None."""
    return next(_problems(entry, key), None)


def write_problem(entry: dict) -> str | None:
    """Refuse unconfirmed pool lanes on write only; hand-written lanes still load."""
    if "pool" not in entry:
        return None
    complete = (all(name in entry for name in _REQUIRED_DATA_USE)
                and entry.get("data_use_confirmed") is True
                and (entry.get("data_use") == "unknown" or "data_use_label" in entry))
    return None if complete else FREE_LANE_REFUSAL.format(key=entry.get("key", "<unknown>"))


# ── Readers (consumers: Phases 37, 40, 41; no run reads them in this phase) ──

class LaneSettingError(ValueError):
    """A lane setting a reader cannot use; the message names its lane and setting."""


class UsageLimit(NamedTuple):
    limited: bool
    note: str


class Escalation(NamedTuple):
    runtime: bool
    model: bool


FALLBACK_WARNING = ("ai-kit-spec: usage_limited {role} lane(s) {keys} have no lane to fall back "
                    "to: every other {role} lane is usage_limited or in the same pool")


def _bool_setting(entry: dict, name: str) -> bool:
    value = entry.get(name, False)
    if not isinstance(value, bool):
        raise LaneSettingError(f"{entry.get('key', '<unknown>')}: '{name}' must be a boolean")
    return value


def lane_usage_limit(entry: dict) -> UsageLimit:
    """36 D-16 / SPEC R12 d: the one reader for the owner's usage-limit flag and note."""
    note = entry.get("usage_limit_note", "")
    return UsageLimit(_bool_setting(entry, "usage_limited"),
                      clean_note(note) if isinstance(note, str) else "")


def lane_session_fallback(config: dict) -> bool:
    """The owner's opt-in to run a task on the session model when no execute lane is available."""
    policy = config.get("policy")
    table = policy.get("execute") if isinstance(policy, dict) else None
    if not isinstance(table, dict):
        return False
    return _bool_setting({**table, "key": "policy.execute"}, SESSION_FALLBACK_KEY)


def lane_escalation(entry: dict) -> Escalation:
    """36 D-06 / SPEC R5: read escalation flags; non-booleans raise a named error."""
    return Escalation(_bool_setting(entry, "escalate_runtime"),
                      _bool_setting(entry, "escalate_model"))


def lane_interactive(entry: dict) -> bool:
    """The owner's interactive marker: the lane may use a verified herdr pane; a non-boolean
    raises a named error."""
    return _bool_setting(entry, "interactive")


def lane_free_pool(entry: dict) -> str | None:
    """The entry's free-pool name when the owner flagged it usage_limited and the pool is
    well formed; None otherwise, including for a non-boolean flag."""
    try:
        limited = lane_usage_limit(entry).limited
    except LaneSettingError:
        return None
    pool = entry.get("pool")
    if limited and isinstance(pool, str) and POOL_RX.fullmatch(pool):
        return pool
    return None


def _keyed(role_lanes) -> list:
    """Return keyed lane dicts in order, keeping first occurrences and skipping malformed items."""
    if not isinstance(role_lanes, list):
        return []
    seen = set()
    result = []
    for lane in role_lanes:
        if isinstance(lane, dict) and isinstance(lane.get("key"), str) and lane["key"] not in seen:
            seen.add(lane["key"])
            result.append(lane)
    return result


def _flagged(lane: dict) -> bool:
    return lane.get("usage_limited") is True


def _fallback_from(base: dict, candidates: list) -> str | None:
    return next((lane["key"] for lane in candidates if lane["key"] != base["key"]
                 and not _flagged(lane)
                 and not (base.get("pool") and lane.get("pool") == base.get("pool"))), None)


def selectable_lanes(role: str, role_lanes, order) -> list:
    """Review picks ordered lanes only; execute also picks remaining lanes in roster order."""
    lanes = _keyed(role_lanes)
    by_key = {lane["key"]: lane for lane in lanes}
    keys = (list(dict.fromkeys(k for k in order if isinstance(k, str) and k in by_key))
            if isinstance(order, list) else [])
    ordered = [by_key[k] for k in keys]
    return ordered if role == "review" else ordered + [lane for lane in lanes
                                                      if lane["key"] not in keys]


def lane_fallback(role_lanes: list, key: str) -> str | None:
    """36 D-16, D-20 / SPEC R12 d: first different, unflagged, different-pool lane in order."""
    lanes = _keyed(role_lanes)
    base = next((lane for lane in lanes if lane["key"] == key), None)
    return _fallback_from(base, lanes) if base is not None else None


def _kind_matches(base: dict, lane: dict, kind: str) -> bool:
    """True when `lane` is a step of `kind` from `base`: another runtime, or the same runtime
    with another model."""
    same = lane.get("runtime") == base.get("runtime")
    return (kind == "runtime" and not same) or (kind == "model" and same
                                                and lane.get("model") != base.get("model"))


def escalation_target(role_lanes: list, key: str, kind: str) -> str | None:
    """36 D-06 / SPEC R5: find the next configured lane matching the escalation kind."""
    if kind not in ("runtime", "model"):
        raise ValueError(f"escalation kind must be 'runtime' or 'model', not {kind!r}")
    lanes = _keyed(role_lanes)
    index = next((number for number, lane in enumerate(lanes) if lane["key"] == key), None)
    if index is None:
        return None
    base = lanes[index]
    return next((lane["key"] for lane in lanes[index + 1:] if _kind_matches(base, lane, kind)),
                None)


def escalation_candidates(role_lanes: list, anchor_key: str, above_keys: list) -> list[str] | None:
    """Keys above the anchor that the anchor lane's escalation flags allow, in the given order;
    None when both flags are off."""
    lanes = _keyed(role_lanes)
    by_key = {lane["key"]: lane for lane in lanes}
    anchor = by_key.get(anchor_key)
    if anchor is None:
        raise LaneSettingError(f"{anchor_key}: not an execute lane")
    flags = lane_escalation(anchor)
    if not flags.runtime and not flags.model:
        return None
    if flags.runtime and flags.model:
        return list(above_keys)
    kind = "runtime" if flags.runtime else "model"
    return [k for k in above_keys if k in by_key and _kind_matches(anchor, by_key[k], kind)]


def fallback_warnings(roles: dict, orders: dict) -> list[str]:
    """36 D-17 / SPEC R12 c: warn per role about flagged lanes without selectable fallbacks."""
    orders = orders if isinstance(orders, dict) else {}
    result = []
    for role, lanes in roles.items():
        pick = selectable_lanes(role, lanes, orders.get(role, []))
        stranded = [lane["key"] for lane in _keyed(lanes)
                    if _flagged(lane) and _fallback_from(lane, pick) is None]
        if stranded:
            result.append(FALLBACK_WARNING.format(role=role, keys=", ".join(stranded)))
    return result
