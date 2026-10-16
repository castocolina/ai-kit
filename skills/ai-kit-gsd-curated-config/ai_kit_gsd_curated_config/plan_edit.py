"""Pure plan.json editing for the v2 plan-set / plan-unset CLI (18 D-15/D-16/D-41/D-44)."""
from __future__ import annotations

import copy
import json
import shlex
from collections.abc import Callable
from typing import Any, NamedTuple

from . import cross_ai, plan_io, presets, roles, skills

_LIST_KEYS_PREFIXES = ("agent_skills.",)
LIST_KEYS = (
    "review.default_reviewers",
    "agent_skills_security.trusted_global_roots",
)
LIST_KEYS_PREFIXES = _LIST_KEYS_PREFIXES
_USER_WHY = "set by the user (plan-set)"
_UNSET_WHY = "kept at the current config value by the user (plan-unset)"
_EXEC_STRIP_KEYS = (
    "workflow.cross_ai_command",
    "workflow.cross_ai_timeout",
    "manager.flags.execute",
)
SCRIPT_MODEL_PREFIX = "script:cross-ai.model."
SCRIPT_PREFER_KEY = "script:cross-ai.prefer"
_EMPTY_PREFER_MSG = (
    "removing every target would leave no execution target; plan-set "
    "workflow.cross_ai_execution false instead"
)


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


def _load_json(key: str, raw: str, label: str) -> object:
    try:
        return json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise PlanEditError(f"{key}: expected a JSON {label} (got {raw!r})") from exc


def _parse_string_list(key: str, raw: str) -> list[str]:
    label = 'list of strings, e.g. \'["name"]\''
    parsed = _load_json(key, raw, label)
    if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
        raise PlanEditError(f"{key}: expected a JSON {label}")
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
    parsed = _load_json(key, raw, label)
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


def runtime_candidates(inv: dict, runner_id: str, rigor: str) -> list[dict]:
    """The ``needs_choice`` rows recommend lists for ``runner_id`` (PT-09): routers and
    fast twins excluded, within the rigor's price ceiling first."""
    runtime = cross_ai.RUNNER_CLI[runner_id]
    cands = [c for c in inv.get("candidates") or [] if c.get("runtime") == runtime]
    # .get: a hand-edited rigor reads as no ceiling, like rigorous.
    ceiling = roles.host_ceiling(cands, presets.PRICE_PERCENTILE.get(rigor))
    return roles.choice_candidates(cands, "execution", ceiling.value)


def plan_unset(call: EditCall, key: str) -> tuple[dict, list[str]]:
    if key.startswith(SCRIPT_MODEL_PREFIX):
        return _plan_unset_script_model(call, key)
    entry = _find_entry(call.plan, key)
    if entry is None:
        raise PlanEditError(f"{key} is not in the plan; nothing to unset")
    _unset_refusal(call.plan, key, entry)
    plan = copy.deepcopy(call.plan)
    entry = _find_entry(plan, key)
    assert entry is not None
    existing = entry.get("existing")
    entry["op"] = "keep"
    entry["value"] = existing
    entry["source"] = "user"
    entry["why"] = _UNSET_WHY
    entry.pop("status", None)
    entry.pop("candidates", None)
    entry.pop("forced", None)
    plan["entries"] = sorted(plan.get("entries") or [], key=lambda row: row["key"])
    return plan, []


def plan_set(call: EditCall, key: str, raw: str) -> tuple[dict, list[str]]:
    """Return a new plan dict and stderr warnings; raise PlanEditError to refuse."""
    if _is_script_pseudo_key(key):
        return _plan_set_script(call, key, raw)
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
    if key == "workflow.cross_ai_execution" and parsed is True:
        _require_script_artifact(call.plan)
    parsed, forced = _special_keys(call, key, entry, parsed, warnings)
    _candidate_refusal(call, key, entry, parsed, forced)
    warnings.extend(_fast_twin_warnings(call.inv, parsed))
    try:
        call.encode(key, parsed)
    except ValueError as exc:
        raise PlanEditError(str(exc)) from exc
    _apply_entry(entry, parsed, forced)
    if key == "workflow.cross_ai_execution" and parsed is False:
        _strip_execution_deps(plan)
    if key == "workflow.cross_ai_timeout":
        _sync_artifact_timeout(plan, parsed)
    plan["entries"] = sorted(plan["entries"], key=lambda row: row["key"])
    return plan, warnings


def _is_script_pseudo_key(key: str) -> bool:
    return key == SCRIPT_PREFER_KEY or key.startswith(SCRIPT_MODEL_PREFIX)


def _plan_set_script(call: EditCall, key: str, raw: str) -> tuple[dict, list[str]]:
    if key == SCRIPT_PREFER_KEY:
        return _plan_set_script_prefer(call, raw)
    runner_id = key[len(SCRIPT_MODEL_PREFIX) :]
    if not runner_id:
        raise PlanEditError(f"{key}: missing runner id")
    return _plan_set_script_model(call, runner_id, raw)


def _plan_set_script_model(
    call: EditCall, runner_id: str, raw: str,
) -> tuple[dict, list[str]]:
    _assert_runner_target(call, runner_id)
    model = raw
    plan = copy.deepcopy(call.plan)
    artifact = _script_artifact(plan)
    config = artifact.setdefault("config", {})
    prefer = config.get("prefer") or []
    if runner_id not in prefer:
        raise PlanEditError(f"script target {runner_id} is not in config.prefer")
    row = _find_inventory_model(call.inv, runner_id, model)
    if row is None and not call.force:
        runtime = cross_ai.RUNNER_CLI[runner_id]
        raise PlanEditError(
            f"{model!r} is not listed for {runtime} in the inventory; "
            "pass --force to pin it anyway"
        )
    router = bool(row.get("is_router")) if row else False
    models = config.setdefault("models", {})
    router_map = config.setdefault("router_backed", {})
    models[runner_id] = model
    router_map[runner_id] = router
    artifact.setdefault("choices", {}).pop(runner_id, None)
    _finish_script_artifact(artifact)
    _sync_artifact_command(plan, artifact)
    plan["entries"] = sorted(plan.get("entries") or [], key=lambda row: row["key"])
    return plan, []


def _plan_set_script_prefer(call: EditCall, raw: str) -> tuple[dict, list[str]]:
    ids = _parse_string_list(SCRIPT_PREFER_KEY, raw)
    if not ids:
        raise PlanEditError(_EMPTY_PREFER_MSG)
    for runner_id in ids:
        _assert_runner_target(call, runner_id)
    if len(set(ids)) != len(ids):
        raise PlanEditError(f"{SCRIPT_PREFER_KEY}: ids must be unique")
    plan = copy.deepcopy(call.plan)
    artifact = _script_artifact(plan)
    config = artifact.setdefault("config", {})
    old_prefer = list(config.get("prefer") or [])
    config["prefer"] = ids
    models = config.setdefault("models", {})
    router_map = config.setdefault("router_backed", {})
    choices = artifact.setdefault("choices", {})
    for dropped in set(old_prefer) - set(ids):
        models.pop(dropped, None)
        router_map.pop(dropped, None)
        choices.pop(dropped, None)
    for runner_id in ids:
        if runner_id in models:
            continue
        if runner_id not in choices:
            choices[runner_id] = {
                "candidates": runtime_candidates(call.inv, runner_id, call.plan["rigor"]),
            }
    _finish_script_artifact(artifact)
    _sync_artifact_command(plan, artifact)
    plan["entries"] = sorted(plan.get("entries") or [], key=lambda row: row["key"])
    return plan, []


def _plan_unset_script_model(call: EditCall, key: str) -> tuple[dict, list[str]]:
    runner_id = key[len(SCRIPT_MODEL_PREFIX) :]
    if not runner_id:
        raise PlanEditError(f"{key}: missing runner id")
    plan = copy.deepcopy(call.plan)
    artifact = _script_artifact(plan)
    config = artifact.setdefault("config", {})
    prefer = config.get("prefer") or []
    if runner_id not in prefer:
        raise PlanEditError(f"script target {runner_id} is not in config.prefer")
    config.setdefault("models", {}).pop(runner_id, None)
    config.setdefault("router_backed", {}).pop(runner_id, None)
    artifact.setdefault("choices", {})[runner_id] = {
        "candidates": runtime_candidates(call.inv, runner_id, call.plan["rigor"]),
    }
    _finish_script_artifact(artifact)
    _sync_artifact_command(plan, artifact)
    plan["entries"] = sorted(plan.get("entries") or [], key=lambda row: row["key"])
    return plan, []


def _script_artifact(plan: dict) -> dict:
    artifacts = plan.get("artifacts") or []
    if not artifacts or not isinstance(artifacts[0], dict):
        raise PlanEditError(
            "no cross-AI script artifact; rerun recommend with --cross-ai-exec y"
        )
    return artifacts[0]


def _require_script_artifact(plan: dict) -> None:
    artifacts = plan.get("artifacts") or []
    if not artifacts:
        raise PlanEditError(
            "no cross-AI script artifact; rerun recommend with --cross-ai-exec y"
        )


def _strip_execution_deps(plan: dict) -> None:
    plan["artifacts"] = []
    drop = set(_EXEC_STRIP_KEYS)
    plan["entries"] = [row for row in plan.get("entries") or [] if row.get("key") not in drop]
    plan["notes"] = [
        note
        for note in plan.get("notes") or []
        if not (isinstance(note, dict) and note.get("kind") == "cross_ai_run")
    ]


def _unset_refusal(plan: dict, key: str, entry: dict) -> None:
    if key == "workflow.cross_ai_timeout" and plan_io.execution_effective_on(plan):
        raise PlanEditError(
            "workflow.cross_ai_timeout is required while workflow.cross_ai_execution is on"
        )
    if key == "workflow.cross_ai_command" and plan_io.execution_effective_on(plan):
        existing = entry.get("existing")
        if existing != cross_ai.CROSS_AI_COMMAND:
            raise PlanEditError(
                "workflow.cross_ai_command is required while "
                "workflow.cross_ai_execution is on"
            )
    if key == "workflow.cross_ai_execution":
        artifacts = plan.get("artifacts") or []
        existing = entry.get("existing")
        if artifacts and existing is False:
            raise PlanEditError(
                "a cross-AI script artifact needs workflow.cross_ai_execution on"
            )


def _assert_runner_target(call: EditCall, runner_id: str) -> None:
    host_name = call.plan.get("host")
    installed = set(call.inv.get("installed_runtimes") or [])
    runtime = cross_ai.RUNNER_CLI.get(runner_id)
    bad = (
        runtime is None
        or runner_id == host_name
        or runtime not in installed
    )
    if bad:
        raise PlanEditError(
            f"script target {runner_id} is not one of pi, cursor, opencode, codex, "
            "is the host, or is not installed"
        )


def _find_inventory_model(inv: dict, runner_id: str, model: str) -> dict | None:
    runtime = cross_ai.RUNNER_CLI[runner_id]
    for row in inv.get("candidates") or []:
        if not isinstance(row, dict):
            continue
        if row.get("runtime") == runtime and row.get("model") == model:
            return row
    return None


def _finish_script_artifact(artifact: dict) -> None:
    choices = artifact.get("choices") or {}
    artifact["source"] = "user"
    artifact["status"] = "needs_choice" if choices else "ok"


def _sync_artifact_command(plan: dict, artifact: dict) -> None:
    command = _find_entry(plan, "workflow.cross_ai_command")
    if command is None:
        return
    choices = artifact.get("choices") or {}
    if choices:
        command["status"] = "needs_choice"
        command["candidates"] = []
    else:
        command.pop("status", None)
        command.pop("candidates", None)


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
            if isinstance(val, list):  # a list candidate (trusted roots) admits its elements
                out.update(item for item in val if isinstance(item, str))
            elif val is not None:
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
    host_name = call.inv["host"]
    if host_name in value:
        # Force-immune, like the execution side (_assert_runner_target): SPEC R2 must-not.
        raise PlanEditError(f"{host_name!r} is the host CLI and cannot be a review lane")
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
        return _check_trusted_roots(call, entry, value, warnings)
    return value, False


def _check_timeout(value: Any) -> int:
    problem = plan_io.timeout_problem("workflow.cross_ai_timeout", value)
    if problem:
        raise PlanEditError(problem)
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
        # The same rule recommend wires by (PT-08), so plan-set never admits a skipped skill.
        reason = skills.unwired_reason(name, inv) if isinstance(name, str) else ""
        if reason is not None:
            raise PlanEditError(
                reason or f"skill {name} is not installed or not addressable on this host"
            )
    return value


def _check_trusted_roots(
    call: EditCall, entry: dict, value: Any, warnings: list[str],
) -> tuple[list[str], bool]:
    """Refuse a list that silently drops configured roots (C-W8); the ``~/`` shape of each
    root is ``validate_plan``'s job (it also covers hand edits)."""
    key = "agent_skills_security.trusted_global_roots"
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise PlanEditError(f"{key}: expected a list of root paths")
    existing = entry.get("existing")
    existing_list = existing if isinstance(existing, list) else []
    dropped = [root for root in existing_list if root not in value]
    if not dropped:
        return value, False
    shown = ", ".join(dropped)
    if not call.force:
        merged = existing_list + [root for root in value if root not in existing_list]
        payload = shlex.quote(json.dumps(merged, separators=(",", ":")))
        raise PlanEditError(
            f"{key}: the list drops already-configured root(s) {shown}; keep them with "
            f"plan-set {key} {payload}, or pass --force to drop them"
        )
    warnings.append(f"{key}: --force drops already-configured root(s) {shown}")
    return value, True


def _apply_entry(entry: dict, value: Any, forced: bool) -> None:
    existing = entry.get("existing")
    entry["value"] = value
    entry["source"] = "user"
    entry["why"] = _USER_WHY
    entry.pop("status", None)
    entry.pop("candidates", None)
    if forced:
        entry["forced"] = True
    else:
        entry.pop("forced", None)
    if existing is not None and plan_io.same_value(value, existing):
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
