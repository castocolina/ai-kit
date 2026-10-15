"""Pure plan.json editing for the v2 plan-set / plan-unset CLI (18 D-15/D-16/D-41/D-44)."""
from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable
from typing import Any, NamedTuple

from . import cross_ai, presets

_SKILL_NAME = re.compile(r"^[A-Za-z0-9_-]+$")
_LIST_KEYS_PREFIXES = ("agent_skills.",)
LIST_KEYS = (
    "review.default_reviewers",
    "agent_skills_security.trusted_global_roots",
)
LIST_KEYS_PREFIXES = _LIST_KEYS_PREFIXES
_USER_WHY = "set by the user (plan-set)"


class PlanEditError(ValueError):
    """Refusal before any plan write."""


class EditCall(NamedTuple):
    plan: dict
    inv: dict
    force: bool
    encode: Callable[[str, object], str]


def parse_value(key: str, raw: str, current: Any) -> object:
    """Shell text -> typed value using the entry's current value or key family."""
    if key in LIST_KEYS or key.startswith(LIST_KEYS_PREFIXES):
        return _parse_string_list(key, raw)
    if isinstance(current, bool):
        return _parse_bool(key, raw)
    if isinstance(current, int) and not isinstance(current, bool):
        return _parse_int(key, raw)
    if isinstance(current, (dict, list)):
        kind = type(current)
        label = "object" if kind is dict else "list"
        return _parse_json_type(key, raw, kind, label)
    if isinstance(current, str):
        return raw
    return _parse_fallback(raw)


def _parse_string_list(key: str, raw: str) -> list[str]:
    parsed = json.loads(raw)
    if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
        raise PlanEditError(f"{key}: expected a JSON list of strings")
    return parsed


def _parse_bool(key: str, raw: str) -> bool:
    low = raw.strip().lower()
    if low == "true":
        return True
    if low == "false":
        return False
    raise PlanEditError(f"{key}: expected true or false (got {raw!r})")


def _parse_int(key: str, raw: str) -> int:
    try:
        return int(raw)
    except ValueError as exc:
        raise PlanEditError(f"{key}: expected an integer (got {raw!r})") from exc


def _parse_json_type(key: str, raw: str, expected: type, label: str):
    parsed = json.loads(raw)
    if not isinstance(parsed, expected):
        raise PlanEditError(f"{key}: expected a JSON {label}")
    return parsed


def _parse_fallback(raw: str):
    try:
        parsed = json.loads(raw)
    except ValueError:
        return raw
    if isinstance(parsed, str):
        return raw
    return parsed


def plan_unset(_call: EditCall, _key: str) -> tuple[dict, list[str]]:
    raise PlanEditError("plan-unset is not available in this build")


def plan_set(call: EditCall, key: str, raw: str) -> tuple[dict, list[str]]:
    """Return a new plan dict and stderr warnings; raise PlanEditError to refuse."""
    warnings: list[str] = []
    _key_probe_refusal(call, key)
    warnings.extend(_unprobed_warning(call, key))
    plan = copy.deepcopy(call.plan)
    entry = _find_entry(plan, key)
    current = entry.get("value") if entry else None
    if entry is None:
        current = _default_current(key, call.inv)
        entry = {
            "key": key,
            "op": "set",
            "value": None,
            "source": "user",
            "why": _USER_WHY,
            "existing": presets.get_dotted(call.inv["existing_config"]["values"], key),
        }
        plan.setdefault("entries", []).append(entry)
    parsed = parse_value(key, raw, current)
    parsed, forced = _special_keys(call, key, entry, parsed, warnings)
    _candidate_refusal(call, key, entry, parsed, forced)
    warnings.extend(_fast_twin_warnings(call.inv, parsed))
    try:
        call.encode(key, parsed)
    except ValueError as exc:
        raise PlanEditError(str(exc)) from exc
    _apply_entry(entry, parsed, forced)
    if key == "workflow.cross_ai_timeout":
        _sync_artifact_timeout(plan, parsed)
    plan["entries"] = sorted(plan["entries"], key=lambda row: row["key"])
    return plan, warnings


def _default_current(key: str, inv: dict) -> Any:
    existing = presets.get_dotted(inv["existing_config"]["values"], key)
    if existing is not None:
        return existing
    if key in LIST_KEYS or key.startswith(LIST_KEYS_PREFIXES):
        return []
    if key == "workflow.cross_ai_timeout":
        return cross_ai.MIN_TIMEOUT_S
    return None


def _find_entry(plan: dict, key: str) -> dict | None:
    for entry in plan.get("entries") or []:
        if entry.get("key") == key:
            return entry
    return None


def _valid_keys(inv: dict) -> tuple[set[str], set[str]]:
    vk = inv["gsd_core"]["valid_keys"]
    return set(vk.get("accepted") or []), set(vk.get("rejected") or [])


def _key_probe_refusal(call: EditCall, key: str) -> None:
    _accepted, rejected = _valid_keys(call.inv)
    if key in rejected:
        version = call.inv["gsd_core"].get("version") or "unknown"
        raise PlanEditError(
            f"key {key} was rejected by the host gsd-core {version} isValidConfigKey"
        )


def _unprobed_warning(call: EditCall, key: str) -> list[str]:
    accepted, rejected = _valid_keys(call.inv)
    if key in accepted or key in rejected:
        return []
    return [f"key {key} was not probed by this inventory"]


def _candidate_values(entry: dict) -> set[Any]:
    out: set[Any] = set()
    for row in entry.get("candidates") or []:
        if not isinstance(row, dict):
            continue
        for field in ("model", "value"):
            val = row.get(field)
            if val is not None:
                out.add(val)
    return out


def _candidate_refusal(
    call: EditCall, key: str, entry: dict, value: Any, forced: bool,
) -> None:
    if entry.get("status") != "needs_choice" or not _candidate_values(entry):
        if key == "review.default_reviewers":
            _reviewers_refusal(call, value, forced)
        return
    pool = _candidate_values(entry)
    items = value if isinstance(value, list) else [value]
    existing = entry.get("existing")
    existing_list = existing if isinstance(existing, list) else []
    bad = [item for item in items if item not in pool and item not in existing_list]
    if bad and not call.force:
        shown = ", ".join(repr(x) for x in sorted(pool, key=str))
        raise PlanEditError(
            f"{bad[0]!r} is not a candidate for {key} (candidates: {shown}); "
            "pass --force to pin it anyway"
        )


def _reviewers_refusal(call: EditCall, value: Any, forced: bool) -> None:
    if not isinstance(value, list):
        return
    lanes = {lane["slug"] for lane in cross_ai.eligible_lanes(call.inv)}
    bad = [slug for slug in value if slug not in lanes]
    if bad and not call.force:
        raise PlanEditError(
            f"{bad[0]!r} is not a candidate for review.default_reviewers "
            f"(candidates: {', '.join(sorted(lanes))}); pass --force to pin it anyway"
        )


def _fast_twin_warnings(inv: dict, value: Any) -> list[str]:
    models = value if isinstance(value, list) else [value]
    by_model = {c["model"]: c for c in inv.get("candidates") or [] if isinstance(c, dict)}
    out: list[str] = []
    for model in models:
        if not isinstance(model, str):
            continue
        row = by_model.get(model)
        twin = row.get("fast_twin_of") if row else None
        if isinstance(twin, str) and twin:
            out.append(
                f"model {model} has fast twin {twin}; prefer the -fast id when speed matters"
            )
    return out


def _skill_installed(name: str, inv: dict) -> bool:
    if not _SKILL_NAME.fullmatch(name):
        return False
    rows = inv.get("skills") or []
    return any(
        isinstance(row, dict)
        and row.get("name") == name
        and row.get("addressable") is True
        and not (row.get("root_kind") == "project" and row.get("escapes_root"))
        for row in rows
    )


def _trusted_root_ok(element: str, entry: dict, pool: set[Any]) -> bool:
    existing = entry.get("existing")
    if isinstance(existing, list) and element in existing:
        return True
    if element in pool:
        return True
    return element.startswith("~/")


def _special_keys(
    call: EditCall, key: str, entry: dict, value: Any, warnings: list[str],
) -> tuple[Any, bool]:
    if key == "workflow.cross_ai_timeout":
        return _check_timeout(value), False
    if key == "workflow.cross_ai_command":
        return _check_cross_ai_command(call, value, warnings)
    if key.startswith("agent_skills."):
        return _check_agent_skills(call.inv, key, value), False
    if key == "agent_skills_security.trusted_global_roots":
        return _check_trusted_roots(key, entry, value), False
    return value, False


def _check_timeout(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise PlanEditError(
            f"workflow.cross_ai_timeout must be an integer >= {cross_ai.MIN_TIMEOUT_S} "
            f"(got {value!r})"
        )
    if value < cross_ai.MIN_TIMEOUT_S:
        raise PlanEditError(
            f"workflow.cross_ai_timeout must be an integer >= {cross_ai.MIN_TIMEOUT_S} "
            f"(got {value})"
        )
    return value


def _check_cross_ai_command(call: EditCall, value: Any, warnings: list[str]) -> tuple[Any, bool]:
    if value == cross_ai.CROSS_AI_COMMAND:
        return value, False
    if not call.force:
        raise PlanEditError(
            "workflow.cross_ai_command must be node .planning/scripts/cross-ai.mjs; "
            "gsd-core runs this command with full permissions; pass --force to override"
        )
    warnings.append(
        "workflow.cross_ai_command overrides the runner; gsd-core runs it with full permissions"
    )
    return value, True


def _check_agent_skills(inv: dict, key: str, value: Any) -> list:
    if not isinstance(value, list):
        raise PlanEditError(f"{key}: expected a list of skill names")
    for name in value:
        if not _skill_installed(name, inv):
            raise PlanEditError(f"skill {name} is not installed or not addressable on this host")
    return value


def _check_trusted_roots(key: str, entry: dict, value: Any) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise PlanEditError(f"{key}: expected a list of root paths")
    pool = _candidate_values(entry)
    for element in value:
        if not _trusted_root_ok(element, entry, pool):
            raise PlanEditError(
                f"trusted root {element!r} must be ~/-relative (only an already-configured "
                "root keeps another form)"
            )
    return value


def _apply_entry(entry: dict, value: Any, forced: bool) -> None:
    existing = entry.get("existing")
    entry["value"] = value
    entry["source"] = "user"
    entry["why"] = _USER_WHY
    entry.pop("status", None)
    entry.pop("candidates", None)
    if forced:
        entry["forced"] = True
    elif "forced" in entry and entry.get("key") != "workflow.cross_ai_command":
        entry.pop("forced", None)
    if existing is not None and value == existing:
        entry["op"] = "keep"
    else:
        entry["op"] = "set"


def _sync_artifact_timeout(plan: dict, timeout: int) -> None:
    artifacts = plan.get("artifacts") or []
    if not artifacts:
        return
    art = artifacts[0]
    if isinstance(art, dict) and isinstance(art.get("config"), dict):
        art["config"]["outer_timeout_s"] = timeout
