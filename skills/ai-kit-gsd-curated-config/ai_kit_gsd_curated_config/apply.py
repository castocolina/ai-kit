"""Apply pre-flight, dry-run diff (18 D-18/D-42) and the D-22 write path (18-18)."""
from __future__ import annotations

import contextlib
import json
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, NamedTuple

from . import (
    config_backup,
    cross_ai_script,
    followups,
    gsd_catalog,
    host,
    plan_io,
    plan_schema,
    presets,
    skills,
)

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
    bind_err = _config_binding_error(config_path, inputs.inv["existing_config"].get("path"))
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


_PREDICTED_WARNING = (
    "remove rows marked predicted are the managed keys config-new-project is expected to copy "
    "from the inventory's global defaults; the copy itself is unverified until apply runs"
)


def _predicted_reconcile(inputs: Inputs) -> list[dict]:
    """R12 on a fresh project: the reconcile apply runs after config-new-project."""
    copied = (inputs.inv.get("global_defaults") or {}).get("values") or {}
    return [
        {
            "key": key,
            "kind": "remove",
            "from": presets.get_dotted(copied, key),
            "to": None,
            "predicted": True,
        }
        for key, _ in reconcile_writes(inputs.plan, copied, inputs.plan["host"])
    ]


def dry_run_report(
    inputs: Inputs,
    target: Target,
    live: dict,
    template: bytes,
) -> dict:
    diff = diff_entries(inputs.plan, live, inputs.inv)
    warnings = _apply_warnings(inputs.plan)
    if not os.path.isfile(target.config_path):
        predicted = _predicted_reconcile(inputs)
        if predicted:
            diff = sorted(diff + predicted, key=lambda row: row["key"])
            warnings.append(_PREDICTED_WARNING)
    return {
        "dry_run": True,
        "plan": inputs.plan_path,
        "config_path": target.config_path,
        "gsd_core_version": target.version,
        "diff": diff,
        "artifacts": script_preview(inputs, template),
        "warnings": warnings,
    }


_PI_SKILL_SKIP = (
    "GSD_RUNTIME=pi is not canonicalized by gsd-core 1.16.0; "
    "agent skills have no effect on pi"
)


@dataclass
class Progress:
    backup_done: bool = False
    backup: str | None = None
    runner: cross_ai_script.ScriptPlan | None = None
    snapshot: str | None = None
    created_dirs: list[str] = field(default_factory=list)
    new_render: str | None = None  # a .new this apply created (removed on rollback)


class CleanupCtx(NamedTuple):
    progress: Progress
    config_path: str
    project_dir: str
    target: Target
    inputs: Inputs
    deps: ApplyDeps
    report: dict


class ScriptStepCtx(NamedTuple):
    inputs: Inputs
    target: Target
    template: bytes
    config_path: str
    progress: Progress
    report: dict


class ConfigWriteCtx(NamedTuple):
    call: Any
    gsd_mod: Any
    writes: list[tuple[str, object]]
    progress: Progress
    config_path: str
    report: dict


class PrepareCtx(NamedTuple):
    inputs: Inputs
    target: Target
    deps: ApplyDeps
    config_path: str
    config_existed: bool
    progress: Progress
    report: dict


class ExecuteCtx(NamedTuple):
    inputs: Inputs
    deps: ApplyDeps
    target: Target
    template: bytes
    gsd_mod: Any
    report: dict


def write_order(key: str, op: str) -> tuple:
    return (key.split(".")[0], 0 if op == "unset" else 1, key)


def _rel_path(project_dir: str, path: str) -> str:
    root = os.path.abspath(project_dir)
    absolute = os.path.abspath(path)
    try:
        return os.path.relpath(absolute, root)
    except ValueError:
        return absolute


def _missing_dir_chain(path: str) -> list[str]:
    parent = os.path.dirname(os.path.abspath(path))
    missing: list[str] = []
    cursor = parent
    while cursor and cursor != os.path.dirname(cursor):
        if os.path.isdir(cursor):
            break
        missing.append(cursor)
        cursor = os.path.dirname(cursor)
    missing.reverse()
    return missing


def _rmdir_chain(dirs: list[str]) -> None:
    for directory in sorted(dirs, key=len, reverse=True):
        try:
            os.rmdir(directory)
        except OSError:
            continue


def _reconcile_candidate(key: str, host_name: str) -> bool:
    if presets.is_managed(key, host_name):
        return True
    if key.startswith("model_policy."):
        return True
    return key == "resolve_model_ids" and host_name == "claude"


def reconcile_writes(plan: dict, live: dict, host_name: str) -> list[tuple[str, None]]:
    planned = {
        entry["key"]
        for entry in plan.get("entries") or []
        if isinstance(entry.get("key"), str)
    }
    rows: list[tuple[str, None]] = []
    for key in sorted(presets.flatten_config(live)):
        if key in planned or not _reconcile_candidate(key, host_name):
            continue
        rows.append((key, None))
    return rows


def pending_writes(
    plan: dict, inv: dict, live: dict, host_name: str
) -> list[tuple[str, object]]:
    del host_name  # reserved for symmetry with reconcile_writes
    rows: list[tuple[str, object]] = []
    for entry in plan.get("entries") or []:
        op = entry.get("op")
        key = entry.get("key")
        if not isinstance(key, str) or op == "keep":
            continue
        if op == "unset":
            if presets.get_dotted(live, key) is None:
                continue
            rows.append((key, None))
            continue
        if op != "set":
            continue
        value = _planned_to(entry, inv)
        if presets.get_dotted(live, key) == value:
            continue
        rows.append((key, value))
    rows.sort(
        key=lambda row: write_order(row[0], "unset" if row[1] is None else "set")
    )
    return rows


def _wired_agents(plan: dict) -> list[str]:
    seen: set[str] = set()
    agents: list[str] = []
    for entry in plan.get("entries") or []:
        key = entry.get("key")
        op = entry.get("op")
        if not isinstance(key, str) or not key.startswith("agent_skills."):
            continue
        if op not in ("set", "unset"):
            continue
        agent = key.split(".", 1)[1]
        if agent not in seen:
            seen.add(agent)
            agents.append(agent)
    return sorted(agents)


def verify_skills(
    target: Target,
    inputs: Inputs,
    deps: ApplyDeps,
    agents: list[str],
) -> dict:
    host_name = inputs.plan["host"]
    if host_name == "pi":
        return {"skipped": _PI_SKILL_SKIP}
    gsd = gsd_catalog.load_ai_kit_spec_module("gsd_tools")
    if gsd is None:
        return {"error": gsd_catalog.SIBLING_MISSING}
    out: dict = {}
    env = {**target.env, "GSD_RUNTIME": host_name}
    for agent in agents:
        try:
            proc = deps.run_fn(
                [
                    target.tools.node_bin,
                    target.tools.gsd_tools_path,
                    "query",
                    "agent-skills",
                    agent,
                    "--json",
                    "--project-dir",
                    inputs.project_dir,
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
                env=env,
            )
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            out[agent] = {"error": str(exc)}
            continue
        if proc.returncode != 0:
            out[agent] = {"error": (proc.stderr or proc.stdout or "").strip()}
            continue
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            out[agent] = {"error": f"unparseable agent-skills JSON: {exc}"}
            continue
        if not isinstance(data, dict):
            out[agent] = {"error": "agent-skills JSON is not an object"}
            continue
        warnings = data.get("warnings")
        out[agent] = {"warnings": warnings if isinstance(warnings, list) else []}
    return out


def _config_call(target: Target, inputs: Inputs, deps: ApplyDeps) -> Any:
    gsd = gsd_catalog.load_ai_kit_spec_module("gsd_tools")
    if gsd is None:
        raise OSError(gsd_catalog.SIBLING_MISSING)
    return gsd.ConfigCall(target.tools, inputs.project_dir, deps.run_fn, target.env)


def _new_project(call: Any) -> bool:
    proc = call.run_fn(
        [
            call.tools.node_bin,
            call.tools.gsd_tools_path,
            "config-new-project",
            "--cwd",
            call.project_dir,
            "--raw",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
        env=None if call.env is None else dict(call.env),
    )
    return proc.returncode == 0


def _count_skipped(plan: dict, inv: dict, live: dict) -> int:
    skipped = 0
    for entry in plan.get("entries") or []:
        op = entry.get("op")
        key = entry.get("key")
        if not isinstance(key, str):
            continue
        if op == "keep" or (
            op == "unset" and presets.get_dotted(live, key) is None
        ):
            skipped += 1
        elif op == "set":
            try:
                planned = _planned_to(entry, inv)
            except ValueError:
                continue
            if presets.get_dotted(live, key) == planned:
                skipped += 1
    return skipped


def _script_warning(path: str) -> str:
    return (
        f"{path}.new is not active; the runner at {path} still runs its old CONFIG; "
        "merge the new render by hand"
    )


def _script_report(
    performed: cross_ai_script.ScriptPlan, project_dir: str, warnings: list[str]
) -> dict:
    rel = _rel_path(project_dir, performed.path)
    active = performed.kind != "new-as-.new"
    if not active:
        warnings.append(_script_warning(rel))
    return {
        "path": rel,
        "kind": performed.kind,
        "note": performed.note,
        "active": active,
    }


def _record_runner_marker(
    config_path: str, plan: cross_ai_script.ScriptPlan, snapshot: str | None
) -> None:
    payload = {"path": plan.path, "snapshot": snapshot, "kind": plan.kind}
    config_backup.update_marker(config_path, runner=payload)


def _clear_runner_marker(config_path: str, snapshot: str | None) -> None:
    # Marker first: a held marker must never name a snapshot that is already gone.
    config_backup.update_marker(config_path, runner=None)
    if snapshot:
        config_backup.discard_snapshot(snapshot)


def _rollback(progress: Progress, config_path: str) -> str | None:
    restore_error: str | None = None
    if progress.backup_done:
        try:
            config_backup.restore_backup(config_path, progress.backup)
        except OSError as exc:
            restore_error = str(exc)
    runner = progress.runner
    if runner is not None:
        try:
            if runner.kind == "change" and progress.snapshot:
                config_backup.restore_backup(runner.path, progress.snapshot)
            elif runner.kind == "add":
                config_backup.restore_backup(runner.path, None)
            elif progress.new_render:
                config_backup.restore_backup(progress.new_render, None)
        except OSError as exc:
            restore_error = restore_error or str(exc)
    if restore_error:
        return restore_error
    with contextlib.suppress(OSError):
        if progress.snapshot:
            config_backup.discard_snapshot(progress.snapshot)
    with contextlib.suppress(OSError):
        config_backup.clear_marker(config_path)
    _rmdir_chain(progress.created_dirs)
    return None


def _marker_committed_or_gone(config_path: str) -> bool:
    marker = config_backup.read_marker(config_path)
    return marker is None or bool(marker.get("committed"))


def _cleanup_committed(ctx: CleanupCtx) -> None:
    progress = ctx.progress
    config_path = ctx.config_path
    project_dir = ctx.project_dir
    report = ctx.report
    committed_recorded = False
    marker_clear_attempted = False
    try:
        config_backup.update_marker(config_path, committed=True)
        committed_recorded = True
    except (OSError, ValueError) as exc:
        report["warnings"].append(f"could not record committed in marker: {exc}")
        marker_clear_attempted = True
        try:
            config_backup.clear_marker(config_path)
        except OSError:
            marker = config_backup.marker_path(config_path)
            snap = progress.snapshot
            tail = (
                f"delete {snap} if it exists, then {marker}"
                if snap
                else f"delete {marker}"
            )
            report["warnings"].append(
                "the apply committed but could not record it in or delete "
                f"{marker}; {config_path} and the runner hold the applied state: "
                f"{tail}; do not restore the backup"
            )

    try:
        report["skill_check"] = verify_skills(
            ctx.target, ctx.inputs, ctx.deps, _wired_agents(ctx.inputs.plan)
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught  # post-commit: warn only
        report["warnings"].append(f"skill check failed after commit: {exc}")

    if _marker_committed_or_gone(config_path) and progress.snapshot:
        try:
            config_backup.discard_snapshot(progress.snapshot)
        except OSError as exc:
            rel = _rel_path(project_dir, progress.snapshot)
            report["warnings"].append(
                f"committed apply left snapshot {rel}: delete it by hand ({exc})"
            )

    if _marker_committed_or_gone(config_path):
        try:
            report["pruned"] = config_backup.prune_backups(config_path)
        except OSError as exc:
            report["warnings"].append(
                f"committed apply left old backups beside the config: prune by hand ({exc})"
            )

    if not marker_clear_attempted and committed_recorded:
        marker_clear_attempted = True
        try:
            config_backup.clear_marker(config_path)
        except OSError as exc:
            rel = _rel_path(project_dir, config_backup.marker_path(config_path))
            report["warnings"].append(
                f"committed apply left marker {rel}: delete it by hand ({exc})"
            )


def _fail_report(project_dir: str, config_path: str, plan: dict) -> dict:
    return {
        "applied": False,
        "config_path": _rel_path(project_dir, config_path),
        "created_config": False,
        "backup": {"path": None, "reused": False},
        "reconciled": [],
        "writes": [],
        "skipped": 0,
        "script": None,
        "skill_check": {},
        "pruned": [],
        "warnings": _apply_warnings(plan),
        "failed_key": None,
        "error": None,
        "restore_error": None,
    }


def _abort_marker(
    config_path: str, progress: Progress, report: dict, message: str
) -> tuple[int, dict]:
    with contextlib.suppress(OSError):
        config_backup.clear_marker(config_path)
    _rmdir_chain(progress.created_dirs)
    report["error"] = message
    return 1, report


def _apply_script_step(ctx: ScriptStepCtx) -> cross_ai_script.ScriptPlan | None:
    inputs = ctx.inputs
    config_path = ctx.config_path
    progress = ctx.progress
    report = ctx.report
    scrub = _scrub_env()
    artifacts = inputs.plan.get("artifacts") or []
    if not artifacts:
        return None
    artifact = artifacts[0]
    if not isinstance(artifact, dict):
        return None
    try:
        plan = cross_ai_script.plan_script(
            inputs.project_dir, artifact, ctx.template, scrub
        )
    except ValueError as exc:
        report["error"] = str(exc)
        report["restore_error"] = _rollback(progress, config_path)
        return None
    runner_dir = os.path.dirname(plan.path)
    if not os.path.isdir(runner_dir):
        progress.created_dirs.extend(_missing_dir_chain(plan.path))
    snapshot: str | None = None
    if plan.kind == "change":
        snapshot = config_backup.snapshot_file(plan.path)
        progress.snapshot = snapshot
        _record_runner_marker(config_path, plan, snapshot)
    elif plan.kind == "add":
        _record_runner_marker(config_path, plan, None)
    new_existed = os.path.lexists(plan.path + ".new")
    try:
        performed = cross_ai_script.write_script(plan)
    except OSError as exc:
        report["error"] = str(exc)
        report["restore_error"] = _rollback(progress, config_path)
        return None
    progress.runner = performed
    if performed.kind == "new-as-.new":
        if not new_existed:
            progress.new_render = performed.write_path
        snap = progress.snapshot
        progress.snapshot = None
        with contextlib.suppress(OSError):
            _clear_runner_marker(config_path, snap)
    report["script"] = _script_report(performed, inputs.project_dir, report["warnings"])
    return performed


def _apply_config_writes(ctx: ConfigWriteCtx) -> bool:
    for key, value in ctx.writes:
        ok, output = ctx.gsd_mod.config_set_strict(ctx.call, key, value)
        if ok:
            op = "unset" if value is None else "set"
            ctx.report["writes"].append({"key": key, "op": op})
            continue
        ctx.report["failed_key"] = key
        ctx.report["error"] = output
        ctx.report["restore_error"] = _rollback(ctx.progress, ctx.config_path)
        return False
    return True


def _rollback_report(
    progress: Progress, config_path: str, report: dict, message: str
) -> tuple[int, dict]:
    report["error"] = message
    report["restore_error"] = _rollback(progress, config_path)
    return 1, report


def _open_marker(
    config_path: str, config_existed: bool, progress: Progress, deps: ApplyDeps, report: dict
) -> tuple[int, dict] | None:
    try:
        if not config_backup.acquire_marker(config_path, config_existed, deps.now_fn):
            report["error"] = config_backup.recovery_text(
                config_backup.read_marker(config_path), config_path
            )
            return 2, report
    except OSError as exc:
        _rmdir_chain(progress.created_dirs)
        report["error"] = str(exc)
        return 1, report
    return None


def _take_backup(
    config_path: str,
    project_dir: str,
    progress: Progress,
    deps: ApplyDeps,
    report: dict,
) -> tuple[int, dict] | None:
    try:
        backup = config_backup.create_backup(config_path, deps.now_fn)
    except OSError as exc:
        return _abort_marker(config_path, progress, report, str(exc))
    progress.backup_done = True
    progress.backup = backup.path
    report["backup"] = {
        "path": _rel_path(project_dir, backup.path) if backup.path else None,
        "reused": backup.reused,
    }
    try:
        backup_name = os.path.basename(backup.path) if backup.path else None
        config_backup.update_marker(config_path, backup=backup_name)
    except OSError as exc:
        return _abort_marker(config_path, progress, report, str(exc))
    return None


def _prepare_writes(
    ctx: PrepareCtx,
) -> tuple[int, dict] | list[tuple[str, object]]:
    plan = ctx.inputs.plan
    config_path = ctx.config_path
    try:
        live = read_live_config(config_path)
    except ValueError as exc:
        return _rollback_report(ctx.progress, config_path, ctx.report, str(exc))
    created_config = False
    if not ctx.config_existed:
        call = _config_call(ctx.target, ctx.inputs, ctx.deps)
        if not _new_project(call):
            return _rollback_report(
                ctx.progress, config_path, ctx.report, "config-new-project failed"
            )
        created_config = True
        ctx.report["created_config"] = True
        try:
            live = read_live_config(config_path)
        except ValueError as exc:
            return _rollback_report(ctx.progress, config_path, ctx.report, str(exc))
    host_name = plan["host"]
    reconcile = reconcile_writes(plan, live, host_name) if created_config else []
    ctx.report["reconciled"] = [key for key, _ in reconcile]
    live = read_live_config(config_path)
    plan_writes = pending_writes(plan, ctx.inputs.inv, live, host_name)
    writes = reconcile + plan_writes
    writes.sort(key=lambda row: write_order(row[0], "unset" if row[1] is None else "set"))
    ctx.report["skipped"] = _count_skipped(plan, ctx.inputs.inv, live)
    return writes


def _pre_commit(
    ctx: ExecuteCtx, config_path: str, config_existed: bool, progress: Progress
) -> tuple[int, dict] | None:
    """D-22 steps 4-6 (new project, runner, config-set); a failure has already rolled back."""
    prep = PrepareCtx(
        ctx.inputs, ctx.target, ctx.deps, config_path, config_existed, progress, ctx.report
    )
    prepared = _prepare_writes(prep)
    if isinstance(prepared, tuple):
        return prepared
    script_ctx = ScriptStepCtx(
        ctx.inputs, ctx.target, ctx.template, config_path, progress, ctx.report
    )
    performed = _apply_script_step(script_ctx)
    if performed is None and ctx.report.get("error"):
        return 1, ctx.report
    write_ctx = ConfigWriteCtx(
        _config_call(ctx.target, ctx.inputs, ctx.deps),
        ctx.gsd_mod,
        prepared,
        progress,
        config_path,
        ctx.report,
    )
    if not _apply_config_writes(write_ctx):
        return 1, ctx.report
    return None


def _execute_apply(ctx: ExecuteCtx) -> tuple[int, dict]:
    project_dir = ctx.inputs.project_dir
    config_path = ctx.target.config_path
    config_existed = os.path.isfile(config_path)
    progress = Progress()
    progress.created_dirs.extend(_missing_dir_chain(config_path))
    blocked = _open_marker(config_path, config_existed, progress, ctx.deps, ctx.report)
    if blocked is not None:
        return blocked
    blocked = _take_backup(config_path, project_dir, progress, ctx.deps, ctx.report)
    if blocked is not None:
        return blocked
    try:
        failed = _pre_commit(ctx, config_path, config_existed, progress)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        # A raised failure before the commit point restores exactly like a returned one (D-22).
        message = str(exc) or type(exc).__name__
        return _rollback_report(progress, config_path, ctx.report, message)
    if failed is not None:
        return failed
    ctx.report["applied"] = True
    _cleanup_committed(
        CleanupCtx(progress, config_path, project_dir, ctx.target, ctx.inputs, ctx.deps, ctx.report)
    )
    try:
        _attach_followups(ctx.report, ctx.inputs, ctx.deps)
    except Exception as exc:  # pylint: disable=broad-exception-caught  # post-commit: warn only
        ctx.report["warnings"].append(f"follow-ups could not be listed after commit: {exc}")
    return 0, ctx.report


def _attach_followups(report: dict, inputs: Inputs, deps: ApplyDeps) -> None:
    host_name = inputs.plan["host"]
    written = [row["key"] for row in report["writes"]] + list(report["reconciled"])
    fctx = followups.FollowupCtx(
        inputs.plan_path,
        inputs.inv_path,
        inputs.project_dir,
        _inventory_deps(deps),
    )
    force = sorted(followups.followup_ids(written, host_name))
    report["followups"] = followups.build_followups(
        inputs.plan, inputs.inv, fctx, force_ids=force
    )


def run_apply(
    inputs: Inputs, deps: ApplyDeps, encode: Callable[[str, object], str]
) -> tuple[int, dict]:
    plan = inputs.plan
    open_choices = needs_choice_keys(plan)
    if open_choices:
        msg = "apply refused while needs_choice remains: " + ", ".join(open_choices)
        return 2, {"error": msg, "applied": False}
    target, error = resolve_target(inputs, deps)
    if target is None:
        return 2, {"error": error, "applied": False}
    report = _fail_report(inputs.project_dir, target.config_path, plan)
    problems = preflight(inputs, target, deps, encode)
    if problems:
        report["error"] = problems[0]
        return 2, report
    template, tmpl_err = cross_ai_script.load_template()
    if template is None:
        report["error"] = tmpl_err
        return 2, report
    gsd_mod = gsd_catalog.load_ai_kit_spec_module("gsd_tools")
    if gsd_mod is None:
        report["error"] = gsd_catalog.SIBLING_MISSING
        return 2, report
    body = ExecuteCtx(inputs, deps, target, template, gsd_mod, report)
    return _execute_apply(body)
