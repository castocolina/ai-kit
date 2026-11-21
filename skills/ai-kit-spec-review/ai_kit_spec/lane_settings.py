"""Flat per-lane settings: write-side checks and cleaning; readers follow in plan 36-17.

Effort is checked by lane_effort; the data-use record by lane_data_use.
"""

import re

from ai_kit_spec import lane_data_use

LANE_FLAG_KEYS = ("escalate_runtime", "escalate_model", "usage_limited")
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
    return _CONTROL_RX.sub("", text).strip()[:NOTE_MAX]


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
