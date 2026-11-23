"""36 D-05 / 37 D-07: validate and list lane efforts. The runner composes every effort
form; a level is a token, never a member of a set.

Pure: no file, process or network access; no config writer or CLI imports.
"""

import re
from typing import NamedTuple

from ai_kit_spec import secret_shapes
from ai_kit_spec.detection import normalize_runtime_keys
from ai_kit_spec.model_catalog import split_catalog_meta
from ai_kit_spec.routing import strip_model_suffix
from ai_kit_spec.usability import find_runtime_key

LEVEL_RX = re.compile(r"[a-z][a-z0-9_-]{0,15}")
EFFORT_SOURCE_RX = re.compile(r"accepted by a call on \d{4}-\d{2}-\d{2}")
NO_RUNTIME_IGNORED = ("ignored: effort needs a table runtime; a custom command or "
                      "session-default lane has no runner effort form")
CANONICAL_LEVEL_ORDER = ("none", "off", "minimal", "low", "medium", "high", "xhigh", "max")
# Effort-like words a host model name carries, never a level.
NAME_WORDS = frozenset({"thinking", "non-thinking", "reasoning"})


class LevelOffer(NamedTuple):
    """Offerable levels, their source, and levels refused by the runner."""
    levels: tuple[str, ...]
    source: str | None
    refused: tuple[tuple[str, str], ...]


# Redact before and after removing controls to catch both intact and split secrets.
def _shown(value) -> str:
    text = secret_shapes.redact(str(value), "[redacted]")
    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
    return secret_shapes.redact(text, "[redacted]")[:40]


def effort_source_label(today: str) -> str:
    """Label an effort accepted by a probe call."""
    return f"accepted by a call on {today}"


def _effort_shape_problem(key, effort) -> str | None:
    if not isinstance(effort, str) or not effort:
        return f"{key}: 'effort' must be a non-empty string"
    if not LEVEL_RX.fullmatch(effort):
        return f"{key}: 'effort' must match [a-z][a-z0-9_-]{{0,15}}"
    return None


def _effort_runtime_problem(key, entry) -> str | None:
    runtime = entry.get("runtime")
    if not isinstance(runtime, str) or not runtime:
        return (f"{key}: 'effort' needs a table runtime; a custom command lane passes a level "
                "through its own template field")
    return None


def _effort_source_problem(key, entry) -> str | None:
    source = entry.get("effort_source")
    if "effort_source" in entry and (
        not isinstance(source, str) or not EFFORT_SOURCE_RX.fullmatch(source)
    ):
        return f"{key}: 'effort_source' must read 'accepted by a call on YYYY-MM-DD'"
    return None


def effort_problem(entry: dict) -> str | None:
    """Validate the flat effort fields of a lane."""
    key = entry.get("key", "<unknown>")
    if "effort" not in entry:
        return f"{key}: 'effort_source' needs 'effort'" if "effort_source" in entry else None
    return (_effort_shape_problem(key, entry["effort"]) or _effort_runtime_problem(key, entry)
            or _effort_source_problem(key, entry))


def _unique_strings(items) -> list[str]:
    return (list(dict.fromkeys(item for item in items if isinstance(item, str)))
            if isinstance(items, list) else [])


def _catalog_levels(catalog, runtime, bare, model) -> list[str]:
    entries, _meta = split_catalog_meta(catalog)
    key = find_runtime_key(entries, runtime, bare)
    if key is None and model != bare:
        key = find_runtime_key(entries, runtime, model)
    return (_unique_strings(entries[key]["runtimes"][runtime].get("efforts"))
            if key is not None else [])


def _snapshot_cli(snapshot, runtime):
    clis = normalize_runtime_keys(snapshot.get("clis") if isinstance(snapshot, dict) else None)
    cli = clis.get(runtime)
    return cli if isinstance(cli, dict) else {}


def _snapshot_levels(snapshot, runtime, bare) -> list[str]:
    cli = _snapshot_cli(snapshot, runtime)
    modes = cli.get("reasoning_modes")
    levels = _unique_strings(modes.get(bare)) if isinstance(modes, dict) else []
    if levels:
        return levels
    records = cli.get("model_records")
    row = records.get(bare) if isinstance(records, dict) else None
    return _unique_strings(row.get("efforts")) if isinstance(row, dict) else []


def _display_order(levels, snapshot_levels) -> list[str]:
    if snapshot_levels and set(snapshot_levels) == set(levels):
        return list(snapshot_levels)
    return ([level for level in CANONICAL_LEVEL_ORDER if level in levels]
            + [level for level in levels if level not in CANONICAL_LEVEL_ORDER])


def _runner_refusal(level) -> str | None:
    if not LEVEL_RX.fullmatch(level):
        return f"'{level}' is not a level token [a-z][a-z0-9_-]{{0,15}}"
    if level in NAME_WORDS:
        return f"'{level}' is part of a model name, not an effort level"
    return None


def listed_ids(runtime, catalog, snapshot) -> frozenset:
    """Collect the runtime's listed ids from both sources."""
    ids = set(_unique_strings(_snapshot_cli(snapshot, runtime).get("models")))
    entries, _meta = split_catalog_meta(catalog)
    for entry in entries.values():
        runtimes = entry.get("runtimes") if isinstance(entry, dict) else None
        row = runtimes.get(runtime) if isinstance(runtimes, dict) else None
        value = row.get("model_id") if isinstance(row, dict) else None
        if isinstance(value, str):
            ids.add(value)
    return frozenset(ids)


def offered_levels(
    runtime, model, catalog, snapshot, listed: frozenset | None = None
) -> LevelOffer:
    """Offer catalog or snapshot levels; the host rejects what it cannot take."""
    if not isinstance(runtime, str) or not runtime or not isinstance(model, str) or not model:
        return LevelOffer((), None, ())
    known = listed if listed is not None else listed_ids(runtime, catalog, snapshot)
    bare = model if runtime == "pi" and model in known else strip_model_suffix(runtime, model)
    snapshot_levels = _snapshot_levels(snapshot, runtime, bare)
    raw = _catalog_levels(catalog, runtime, bare, model)
    source = "catalog" if raw else "runtimes snapshot" if snapshot_levels else None
    if source is None:
        return LevelOffer((), None, ())
    levels = []
    refused = []
    for level in _display_order(raw or snapshot_levels, snapshot_levels):
        reason = _runner_refusal(level)
        if reason is None:
            levels.append(level)
        else:
            refused.append((level, reason))
    return LevelOffer(tuple(levels), source, tuple(refused))


def write_problems(lanes, catalog, snapshot) -> list[str]:
    """Refuse an effort outside the model's own listed levels at write time."""
    problems = []
    for lane in lanes:
        if not isinstance(lane, dict) or not all(
            isinstance(lane.get(k), str) for k in ("runtime", "model", "effort")
        ):
            continue
        offer = offered_levels(lane["runtime"], lane["model"], catalog, snapshot)
        if offer.source is None:
            continue
        key, effort = lane.get("key", "<unknown>"), lane["effort"]
        reasons = dict(offer.refused)
        if effort in reasons:
            problems.append(f"{key}: effort '{_shown(effort)}' cannot be passed: {reasons[effort]}")
        elif effort not in offer.levels:
            problems.append(f"{key}: effort '{_shown(effort)}' is not in the model's list "
                            f"({', '.join(offer.levels)}) [{offer.source}]")
    return problems
