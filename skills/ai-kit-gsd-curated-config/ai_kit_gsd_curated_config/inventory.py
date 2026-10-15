"""Read-only inventory assembly: host, gsd-core tables, and probed valid keys (INV-01, REC-06).

All inventory I/O lives here; nothing in this module writes project or gsd-core config.
Read-only is not sandboxed: with project-local-first resolution (D-11) the inventory runs
the project's own gsd-core (`node .../gsd-tools.cjs config-path` and `require()` of its lib
modules), so only run it on trusted checkouts.
"""
from __future__ import annotations

import json
import os
from typing import NamedTuple

from . import catalog_adapter, gsd_catalog, host, plan_io, presets, project_facts

_PROBE_UNAVAILABLE = (
    "gsd-core at {root} (version {version}): isValidConfigKey unavailable "
    "(require failed or export missing)"
)

PROJECT_CONFIG_KEYS = (
    "model_profile",
    "models",
    "model_overrides",
    "model_profile_overrides",
    "effort",
    "dynamic_routing",
    "review",
    "agent_skills",
    "workflow",
    "granularity",
    "intel",
    "plan_review",
    "code_quality",
    "refactor",
    "runtime",
    "resolve_model_ids",
    "model_policy",
    "claude_md_path",
)

GLOBAL_CONFIG_KEYS = ("model_policy", "runtime", "resolve_model_ids")

_LATENT = "latent (copied into the project config by config-new-project)"


class InventoryOpts(NamedTuple):
    host: str | None
    refresh: bool = False


class _ResolvedHost(NamedTuple):
    host_name: str
    host_source: str
    core: host.GsdCore


class _InventorySnapshot(NamedTuple):
    host_name: str
    host_source: str
    core: host.GsdCore
    existing: dict
    global_defaults: dict
    tables: dict
    fields: dict
    project_dir: str
    ex_warn: str | None
    gl_warn: str | None


def _filter_allowlist(values: dict, allowed: tuple[str, ...]) -> dict:
    return {key: values[key] for key in allowed if key in values}


def _read_json_object(path: str) -> tuple[dict | None, str | None]:
    if not os.path.isfile(path):
        return None, None
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None, f"{path} unreadable; ignored"
    if not isinstance(data, dict):
        return None, f"{path} unreadable; ignored"
    return data, None


def _existing_config(project_dir, tools_path, node_bin, run_fn):
    gsd = gsd_catalog.load_ai_kit_spec_module("gsd_tools")
    path = os.path.join(project_dir, ".planning", "config.json")
    if gsd is not None and node_bin is not None:
        tools = gsd.GsdTools(node_bin, tools_path)
        resolved = gsd.config_path(tools, project_dir, run_fn)
        if resolved:
            path = resolved
    raw, warn = _read_json_object(path)
    exists = os.path.isfile(path)
    values = _filter_allowlist(raw, PROJECT_CONFIG_KEYS) if raw else {}
    return {"path": path, "exists": exists, "values": values}, warn


def _global_defaults(env: dict):
    home = env.get("HOME") or os.path.expanduser("~")
    base = env["GSD_HOME"] if env.get("GSD_HOME") else home
    path = os.path.join(base, ".gsd", "defaults.json")
    raw, warn = _read_json_object(path)
    exists = os.path.isfile(path)
    values = _filter_allowlist(raw, GLOBAL_CONFIG_KEYS) if raw else {}
    return {"path": path, "exists": exists, "values": values}, warn


def _probe_keys(host_name: str, existing_values: dict, global_values: dict) -> list[str]:
    keys = set(presets.closed_key_set(host_name))
    keys.update(presets.flatten_config(existing_values))
    policy = global_values.get("model_policy")
    if isinstance(policy, dict):
        keys.update(presets.flatten_config({"model_policy": policy}))
    return sorted(keys)


def _missing_lib_error(core, filename: str) -> str:
    ver = core.version or "unknown"
    return f"gsd-core at {core.root} (version {ver}): missing lib/{filename}"


def _probe_gsd_tables(core, host_name, project_dir, probe_keys, deps):
    node_bin = gsd_catalog.resolve_node_binary(deps.which_fn)
    if node_bin is None:
        return None, "could not resolve 'node' on PATH"
    model_catalog = gsd_catalog.resolve_model_catalog_cjs_path(core.tools_path)
    config_schema = gsd_catalog.resolve_config_schema_cjs_path(core.tools_path)
    if model_catalog is None or config_schema is None:
        missing = "model-catalog.cjs" if model_catalog is None else "config-schema.cjs"
        return None, _missing_lib_error(core, missing)
    paths = gsd_catalog.GsdCorePaths(node_bin, model_catalog, config_schema)
    tables = gsd_catalog.query_gsd_tables(paths, project_dir, probe_keys, deps.run_fn)
    if tables is None:
        ver = core.version or "unknown"
        return None, _PROBE_UNAVAILABLE.format(root=core.root, version=ver)
    return tables, None


def _catalog_fields(project_dir, opts, host_name, env, run_fn):
    cat, cat_err = catalog_adapter.refresh_catalog(project_dir, env, opts.refresh, run_fn)
    if cat is None:
        return None, cat_err
    try:
        candidates = catalog_adapter.build_candidates(
            cat.runtimes, cat.entries, host.host_cli(host_name), cat.weights
        )
    except ImportError as exc:
        return None, str(exc)
    return {
        "catalog": {"state": cat.state, "scored": cat.scored},
        "candidates": candidates,
        "candidate_heuristic_fields": list(catalog_adapter.CANDIDATE_HEURISTIC_FIELDS),
        "catalog_warnings": cat.warnings,
    }, None


def _item(kind: str, scope: str, key: str, value, why: str, **extra) -> dict:
    row = {"kind": kind, "scope": scope, "key": key, "value": value, "why": why}
    row.update(extra)
    return row


def _global_model_policy(existing: dict, global_values: dict, facts: dict) -> tuple[list, list]:
    if existing["exists"]:
        return [], []
    policy = global_values.get("model_policy")
    if policy is None:
        return [], []
    why = "copied into the project config by config-new-project"
    if not facts.get("planning_dir_present"):
        why += "; read at resolution while .planning/ is absent"
    return [
        _item("model_policy", "global", "model_policy", policy, why, effect=_LATENT)
    ], []


def _project_model_policy(existing: dict, global_values: dict) -> tuple[list, list]:
    conflicts, info = [], []
    policy = existing["values"].get("model_policy")
    if policy is not None:
        conflicts.append(
            _item(
                "model_policy",
                "project",
                "model_policy",
                policy,
                "project model_policy shadows model_profile_overrides (resolver step 2.5)",
            )
        )
    g_policy = global_values.get("model_policy")
    if g_policy is not None and existing["exists"]:
        info.append(
            _item(
                "model_policy",
                "global",
                "model_policy",
                g_policy,
                "inert: gsd-tools ignores ~/.gsd/defaults.json when a project config "
                "exists (#3532)",
            )
        )
    return conflicts, info


def _resolve_model_ids(host_name: str, existing: dict, global_values: dict) -> tuple[list, list]:
    if host_name != "claude":
        return [], []
    conflicts, info = [], []
    project_val = existing["values"].get("resolve_model_ids")
    if project_val == "omit":
        conflicts.append(
            _item(
                "resolve_model_ids",
                "project",
                "resolve_model_ids",
                project_val,
                "resolve_model_ids omit makes resolve-model return an empty model for "
                "every agent without a per-agent override on a claude host",
            )
        )
    global_val = global_values.get("resolve_model_ids")
    if global_val != "omit":
        return conflicts, info
    if existing["exists"]:
        info.append(
            _item(
                "resolve_model_ids",
                "global",
                "resolve_model_ids",
                global_val,
                "inert: gsd-tools ignores ~/.gsd/defaults.json when a project config "
                "exists (#3532)",
            )
        )
        return conflicts, info
    conflicts.append(
        _item(
            "resolve_model_ids",
            "global",
            "resolve_model_ids",
            global_val,
            "copied into the project config by config-new-project",
            effect=_LATENT,
        )
    )
    return conflicts, info


def _runtime_entries(host_name: str, existing: dict, global_values: dict) -> tuple[list, list]:
    conflicts, info = [], []
    project_rt = existing["values"].get("runtime")
    if isinstance(project_rt, str) and project_rt != host_name:
        conflicts.append(
            _item(
                "runtime",
                "project",
                "runtime",
                project_rt,
                f"project runtime {project_rt} differs from host {host_name}; "
                "resolve-model uses the project runtime",
            )
        )
    global_rt = global_values.get("runtime")
    if global_rt is not None:
        info.append(
            _item(
                "runtime",
                "global",
                "runtime",
                global_rt,
                "a global runtime never drives resolve-model (gsd-tools fills an absent "
                "project runtime from env or an install marker); the installer bake reads "
                "it when the project has none",
            )
        )
    return conflicts, info


def _claude_md_info(project_dir: str, existing: dict, facts: dict) -> list:
    configured = existing["values"].get("claude_md_path")
    if not isinstance(configured, str):
        return []
    rel = configured[2:] if configured.startswith("./") else configured
    if os.path.isfile(os.path.join(project_dir, rel)):
        return []
    detected = facts.get("instruction_file")
    text = f"configured claude_md_path {configured} is missing"
    if detected:
        text += f"; detected instruction file {detected}"
    return [_item("claude_md_path", "project", "claude_md_path", configured, text)]


def classify_conflicts(
    host_name: str, existing: dict, global_defaults: dict, facts: dict, project_dir: str
) -> tuple[list, list]:
    """Pure conflict/info classification (INV-03, D-10, D-21, D-31)."""
    global_values = global_defaults.get("values") or {}
    conflicts: list = []
    info: list = []
    for part in (
        _project_model_policy(existing, global_values),
        _global_model_policy(existing, global_values, facts),
        _resolve_model_ids(host_name, existing, global_values),
        _runtime_entries(host_name, existing, global_values),
    ):
        conflicts.extend(part[0])
        info.extend(part[1])
    info.extend(_claude_md_info(project_dir, existing, facts))
    return (
        sorted(conflicts, key=lambda row: (row["kind"], row["scope"])),
        sorted(info, key=lambda row: (row["kind"], row["scope"])),
    )


def _assemble_inventory(snapshot: _InventorySnapshot):
    configured = snapshot.existing["values"].get("claude_md_path")
    claude_path = configured if isinstance(configured, str) else None
    facts = project_facts.project_facts(snapshot.project_dir, claude_path)
    conflicts, info = classify_conflicts(
        snapshot.host_name,
        snapshot.existing,
        snapshot.global_defaults,
        facts,
        snapshot.project_dir,
    )
    fields = dict(snapshot.fields)
    cat_warnings = fields.pop("catalog_warnings")
    extra_warns = [w for w in (snapshot.ex_warn, snapshot.gl_warn) if w]
    core = snapshot.core
    return {
        "schema_version": plan_io.INVENTORY_SCHEMA_VERSION,
        "host": snapshot.host_name,
        "host_source": snapshot.host_source,
        "gsd_core": {
            "path": core.root,
            "scope": core.scope,
            "version": core.version,
            **snapshot.tables,
        },
        "existing_config": snapshot.existing,
        "global_defaults": snapshot.global_defaults,
        "catalog": fields["catalog"],
        "candidates": fields["candidates"],
        "candidate_heuristic_fields": fields["candidate_heuristic_fields"],
        "project": facts,
        "skills": project_facts.list_skills(snapshot.project_dir),
        "conflicts": conflicts,
        "info": info,
        "warnings": sorted(set(core.warnings) | set(cat_warnings) | set(extra_warns)),
    }


def _load_configs(project_dir, deps, resolved: _ResolvedHost):
    node_bin = gsd_catalog.resolve_node_binary(deps.which_fn)
    existing, ex_warn = _existing_config(
        project_dir, resolved.core.tools_path, node_bin, deps.run_fn
    )
    global_defaults, gl_warn = _global_defaults(deps.env_fn())
    probe = _probe_keys(
        resolved.host_name, existing["values"], global_defaults["values"]
    )
    tables, table_err = _probe_gsd_tables(
        resolved.core, resolved.host_name, project_dir, probe, deps
    )
    return existing, global_defaults, tables, table_err, ex_warn, gl_warn


def _inventory_snapshot(project_dir, opts, deps, resolved: _ResolvedHost):
    existing, global_defaults, tables, table_err, ex_warn, gl_warn = _load_configs(
        project_dir, deps, resolved
    )
    if tables is None:
        return None, table_err
    fields, cat_err = _catalog_fields(
        project_dir, opts, resolved.host_name, deps.env_fn(), deps.run_fn
    )
    if fields is None:
        return None, cat_err
    return (
        _InventorySnapshot(
            resolved.host_name,
            resolved.host_source,
            resolved.core,
            existing,
            global_defaults,
            tables,
            fields,
            project_dir,
            ex_warn,
            gl_warn,
        ),
        None,
    )


def build_inventory(project_dir, opts: InventoryOpts, deps: host.InventoryDeps):
    """Returns `(inventory_dict, None)` or `(None, error_message)`."""
    host_name, host_source = host.detect_host(deps.env_fn(), opts.host)
    if host_name is None:
        return None, host_source
    core, error = host.resolve_gsd_core(project_dir, host_name, deps)
    if core is None:
        return None, error
    snap, err = _inventory_snapshot(
        project_dir, opts, deps, _ResolvedHost(host_name, host_source, core)
    )
    if snap is None:
        return None, err
    return _assemble_inventory(snap), None
