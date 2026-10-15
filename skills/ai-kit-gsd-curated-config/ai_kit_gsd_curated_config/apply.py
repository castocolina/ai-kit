"""Read-only apply pre-flight and dry-run diff (18 D-18/D-42). Writes land in 18-18."""
from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, NamedTuple

from . import cross_ai_script, gsd_catalog, host, plan_io, plan_schema, presets, skills

_PROBE_UNAVAILABLE = (
    "gsd-core at {root} (version {version}): isValidConfigKey unavailable "
    "(require failed or export missing)"
)
_FORCED_CMD_WARNING = (
    "workflow.cross_ai_command overrides the runner; "
    "gsd-core runs it with full permissions"
)


class ApplyDeps(NamedTuple):
    which_fn: Callable[..., str | None]
    run_fn: Callable[..., Any]
    env_fn: Callable[[], dict]
    now_fn: Callable[[], datetime] = lambda: datetime.now(UTC)


class Inputs(NamedTuple):
    plan: dict
    plan_path: str
    inv: dict
    inv_path: str
    project_dir: str


class Target(NamedTuple):
    tools: Any
    paths: gsd_catalog.GsdCorePaths
    config_path: str
    env: dict
    version: str | None
    core_root: str


def load_inputs(
    plan_path: str, inv_path: str, project_dir: str
) -> tuple[Inputs | None, str | None]:
    project_dir = os.path.abspath(project_dir)
    if not os.path.isdir(project_dir):
        return None, f"--project-dir {project_dir} is not a directory"
    plan, error = plan_io.load_plan(plan_path)
    if plan is None:
        return None, error
    inv, inv_err = plan_io.load_inventory(inv_path)
    if inv is None:
        return None, inv_err
    digest = plan_schema.inventory_digest(inv)
    if plan.get("inventory_digest") != digest:
        return None, (
            "inventory digest does not match the plan's inventory_digest "
            f"(plan {plan['inventory_digest']!r}, inventory {digest!r})"
        )
    inv_problem = plan_io.check_plan_inventory(plan, inv)
    if inv_problem:
        return None, inv_problem
    return Inputs(plan, plan_path, inv, inv_path, project_dir), None


def needs_choice_keys(plan: dict) -> list[str]:
    keys: list[str] = []
    for entry in plan.get("entries") or []:
        if entry.get("status") == "needs_choice":
            key = entry.get("key")
            if isinstance(key, str):
                keys.append(key)
    for artifact in plan.get("artifacts") or []:
        if artifact.get("status") == "needs_choice":
            path = artifact.get("path")
            if isinstance(path, str):
                keys.append(f"artifact:{path}")
    return sorted(keys)


def write_keys(plan: dict) -> list[str]:
    keys = [
        entry["key"]
        for entry in plan.get("entries") or []
        if entry.get("op") in ("set", "unset") and isinstance(entry.get("key"), str)
    ]
    return sorted(keys)


def read_live_config(config_path: str) -> dict:
    data, warn = plan_io.read_json_object(config_path)
    if warn:
        raise ValueError(warn)
    return data or {}


def skill_value(inv: dict, names: list) -> list[str]:
    refs: list[str] = []
    for name in names:
        row = skills.locate(name, inv)
        if row is None:
            raise ValueError(
                f"skill {name} is not installed or not addressable on this host"
            )
        refs.append(skills.reference_for(row))
    return refs


def _planned_to(entry: dict, inv: dict) -> Any:
    op = entry.get("op")
    key = entry.get("key", "")
    if op == "unset":
        return None
    if op == "keep":
        return entry.get("existing")
    value = entry.get("value")
    if op == "set" and isinstance(key, str) and key.startswith("agent_skills."):
        if not isinstance(value, list):
            return value
        return skill_value(inv, value)
    return value


def _diff_kind(op: str, live: Any, planned: Any) -> str:
    if op == "keep":
        return "keep"
    if op == "unset":
        return "keep" if live is None else "remove"
    if op == "set":
        if live is None:
            return "add"
        if live == planned:
            return "keep"
        return "change"
    return "keep"


def diff_entries(plan: dict, live: dict, inv: dict) -> list[dict]:
    rows: list[dict] = []
    for entry in plan.get("entries") or []:
        key = entry.get("key")
        op = entry.get("op")
        if not isinstance(key, str) or not isinstance(op, str):
            continue
        from_val = presets.get_dotted(live, key)
        to_val = _planned_to(entry, inv)
        rows.append(
            {
                "key": key,
                "kind": _diff_kind(op, from_val, to_val),
                "from": from_val,
                "to": to_val,
            }
        )
    return sorted(rows, key=lambda row: row["key"])


def _scrub_env() -> list[str]:
    detection = gsd_catalog.load_ai_kit_spec_module("detection")
    if detection is None:
        return []
    return sorted(detection.HOST_SIGNAL_ENV_VARS)


def script_preview(inputs: Inputs, template: bytes) -> list[dict]:
    scrub = _scrub_env()
    rows: list[dict] = []
    for artifact in inputs.plan.get("artifacts") or []:
        if not isinstance(artifact, dict):
            continue
        plan = cross_ai_script.plan_script(
            inputs.project_dir, artifact, template, scrub
        )
        path = artifact.get("path")
        if not isinstance(path, str):
            path = plan.path
        rows.append({"path": path, "kind": plan.kind, "note": plan.note})
    return rows


def _inventory_deps(deps: ApplyDeps) -> host.InventoryDeps:
    return host.InventoryDeps(deps.which_fn, deps.run_fn, deps.env_fn)


def _config_binding_error(config_path: str, recorded: object) -> str | None:
    if not isinstance(recorded, str) or not os.path.isabs(recorded):
        return f"{recorded!r} is not an absolute config path; rerun inventory"
    if os.path.realpath(config_path) != os.path.realpath(recorded):
        return (
            f"{config_path} is not the config this inventory was taken for ({recorded}); "
            "rerun inventory for this project and workstream"
        )
    return None


def _target_for_core(inputs: Inputs, deps: ApplyDeps, core: host.GsdCore) -> Target | str:
    gsd_tools = gsd_catalog.load_ai_kit_spec_module("gsd_tools")
    if gsd_tools is None:
        return gsd_catalog.SIBLING_MISSING
    node_bin = gsd_catalog.resolve_node_binary(deps.which_fn)
    if node_bin is None:
        return "could not resolve 'node' on PATH"
    tools = gsd_tools.GsdTools(node_bin, core.tools_path)
    env = deps.env_fn()
    config_path = gsd_tools.config_path(tools, inputs.project_dir, deps.run_fn, env)
    if not config_path:
        ver = core.version or "unknown"
        return f"gsd-core at {core.root} (version {ver}): config-path failed"
    bind_err = _config_binding_error(config_path, inputs.inv["existing_config"]["path"])
    if bind_err:
        return bind_err
    model_catalog = gsd_catalog.resolve_model_catalog_cjs_path(core.tools_path)
    config_schema = gsd_catalog.resolve_config_schema_cjs_path(core.tools_path)
    if model_catalog is None or config_schema is None:
        missing = "model-catalog.cjs" if model_catalog is None else "config-schema.cjs"
        ver = core.version or "unknown"
        return f"gsd-core at {core.root} (version {ver}): missing lib/{missing}"
    paths = gsd_catalog.GsdCorePaths(node_bin, model_catalog, config_schema)
    return Target(tools, paths, config_path, env, core.version, core.root)


def resolve_target(inputs: Inputs, deps: ApplyDeps) -> tuple[Target | None, str | None]:
    core, error = host.resolve_gsd_core(
        inputs.project_dir, inputs.plan["host"], _inventory_deps(deps)
    )
    if core is None:
        return None, error
    built = _target_for_core(inputs, deps, core)
    if isinstance(built, str):
        return None, built
    return built, None


def _encode_entry(entry: dict, inv: dict, encode: Callable[[str, object], str]) -> str | None:
    if entry.get("op") != "set":
        return None
    key = entry.get("key")
    if not isinstance(key, str):
        return None
    try:
        value = _planned_to(entry, inv)
        encode(key, value)
    except ValueError as exc:
        return str(exc)
    return None


def preflight(
    inputs: Inputs,
    target: Target,
    deps: ApplyDeps,
    encode: Callable[[str, object], str],
) -> list[str]:
    problems: list[str] = []
    for entry in inputs.plan.get("entries") or []:
        msg = _encode_entry(entry, inputs.inv, encode)
        if msg:
            problems.append(msg)
    keys = write_keys(inputs.plan)
    ver = target.version or "unknown"
    try:
        tables = gsd_catalog.query_gsd_tables(
            target.paths,
            inputs.project_dir,
            keys,
            deps.run_fn,
            target.env,
        )
    except gsd_catalog.NodeQueryError as exc:
        return [f"gsd-core at {target.core_root} (version {ver}): {exc}"]
    if tables is None:
        return [_PROBE_UNAVAILABLE.format(root=target.core_root, version=ver)]
    rejected = set(tables["valid_keys"]["rejected"])
    for key in keys:
        if key in rejected:
            problems.append(
                f"key {key} was rejected by the host gsd-core {ver} isValidConfigKey"
            )
    return problems


def _apply_warnings(plan: dict) -> list[str]:
    warnings: list[str] = []
    for entry in plan.get("entries") or []:
        if entry.get("key") == "workflow.cross_ai_command" and entry.get("forced"):
            warnings.append(_FORCED_CMD_WARNING)
    return warnings


def dry_run_report(
    inputs: Inputs,
    target: Target,
    live: dict,
    template: bytes,
) -> dict:
    return {
        "dry_run": True,
        "plan": inputs.plan_path,
        "config_path": target.config_path,
        "gsd_core_version": target.version,
        "diff": diff_entries(inputs.plan, live, inputs.inv),
        "artifacts": script_preview(inputs, template),
        "warnings": _apply_warnings(inputs.plan),
    }
