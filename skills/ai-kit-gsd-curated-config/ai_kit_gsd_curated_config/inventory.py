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

from . import catalog_adapter, gsd_catalog, host, plan_io, presets, project_facts, skill_scan

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
    "manager",
    "agent_skills_security",
)

GLOBAL_CONFIG_KEYS = ("model_policy", "runtime", "resolve_model_ids")

# gsd-core configuration.cjs DEPTH_TO_GRANULARITY; an unmapped depth passes through as-is.
_DEPTH_TO_GRANULARITY = {"quick": "coarse", "standard": "standard", "comprehensive": "fine"}

_LATENT = "latent (copied into the project config by config-new-project)"
_COPIED_WHY = "copied into the project config by config-new-project"
_INERT_WHY = "inert: gsd-tools ignores ~/.gsd/defaults.json when a project config exists (#3532)"


def _copied_why(facts: dict) -> str:
    # gsd-core reads ~/.gsd/defaults.json at resolution while .planning/ is absent.
    if facts.get("planning_dir_present"):
        return _COPIED_WHY
    return _COPIED_WHY + "; read at resolution while .planning/ is absent"


class InventoryOpts(NamedTuple):
    host: str | None
    refresh: bool = False


def _filter_allowlist(values: dict, allowed: tuple[str, ...]) -> dict:
    return {key: values[key] for key in allowed if key in values}


def _read_json_object(path: str) -> tuple[dict | None, str | None]:
    if not os.path.isfile(path):
        return None, None
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError, RecursionError):  # ValueError covers JSON + UTF-8 decode
        return None, f"{path} unreadable; ignored"
    if not isinstance(data, dict):
        return None, f"{path} unreadable; ignored"
    return data, None


def _hoist_legacy_depth(raw: dict) -> tuple[dict, bool]:
    """Mirrors gsd-core's normalization 4 (configuration.cjs): a top-level `depth` with no
    `granularity` is read as granularity. Returns `(config, hoisted)`."""
    if "depth" not in raw or "granularity" in raw:
        return raw, False
    depth = raw["depth"]
    mapped = _DEPTH_TO_GRANULARITY.get(depth, depth) if isinstance(depth, str) else depth
    return {**raw, "granularity": mapped}, True


def _existing_config(project_dir, tools_path, node_bin, deps):
    gsd = gsd_catalog.load_ai_kit_spec_module("gsd_tools")
    path = os.path.join(project_dir, ".planning", "config.json")
    if gsd is not None and node_bin is not None:
        tools = gsd.GsdTools(node_bin, tools_path)
        resolved = gsd.config_path(tools, project_dir, deps.run_fn, deps.env_fn())
        if resolved:
            path = resolved
    raw, warn = _read_json_object(path)
    exists = os.path.isfile(path)
    raw, hoisted = _hoist_legacy_depth(raw or {})
    values = _filter_allowlist(raw, PROJECT_CONFIG_KEYS)
    section = {"path": path, "exists": exists, "values": values}
    if hoisted:
        section["legacy_depth"] = raw["depth"]
    return section, warn


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


def _probe_gsd_tables(core, node_bin, project_dir, probe_keys, deps):
    if node_bin is None:
        return None, "could not resolve 'node' on PATH"
    model_catalog = gsd_catalog.resolve_model_catalog_cjs_path(core.tools_path)
    config_schema = gsd_catalog.resolve_config_schema_cjs_path(core.tools_path)
    if model_catalog is None or config_schema is None:
        missing = "model-catalog.cjs" if model_catalog is None else "config-schema.cjs"
        return None, _missing_lib_error(core, missing)
    paths = gsd_catalog.GsdCorePaths(node_bin, model_catalog, config_schema)
    ver = core.version or "unknown"
    try:
        tables = gsd_catalog.query_gsd_tables(
            paths, project_dir, probe_keys, deps.run_fn, deps.env_fn()
        )
    except gsd_catalog.NodeQueryError as exc:
        return None, f"gsd-core at {core.root} (version {ver}): {exc}"
    if tables is None:
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
    clis = cat.runtimes.get("clis", {}) if isinstance(cat.runtimes, dict) else {}
    installed = sorted(
        name
        for name, row in clis.items()
        if isinstance(name, str) and isinstance(row, dict) and row.get("installed") is True
    )
    return {
        "catalog": {"state": cat.state, "scored": cat.scored},
        "candidates": candidates,
        "candidate_heuristic_fields": list(catalog_adapter.CANDIDATE_HEURISTIC_FIELDS),
        "catalog_warnings": cat.warnings,
        "installed_runtimes": installed,
    }, None


def _item(kind: str, scope: str, value, why: str, **extra) -> dict:
    """A conflict/info row; its `key` is always the top-level config key `kind`."""
    row = {"kind": kind, "scope": scope, "key": kind, "value": value, "why": why}
    row.update(extra)
    return row


def _global_model_policy(existing: dict, global_values: dict, facts: dict) -> tuple[list, list]:
    if existing["exists"]:
        return [], []
    policy = global_values.get("model_policy")
    if policy is None:
        return [], []
    return [
        _item("model_policy", "global", policy, _copied_why(facts),
              effect=_LATENT)
    ], []


def _project_model_policy(existing: dict, global_values: dict) -> tuple[list, list]:
    conflicts, info = [], []
    policy = existing["values"].get("model_policy")
    if policy is not None:
        conflicts.append(
            _item(
                "model_policy",
                "project",
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
                g_policy,
                _INERT_WHY,
            )
        )
    return conflicts, info


def _resolve_model_ids(
    host_name: str, existing: dict, global_values: dict, facts: dict
) -> tuple[list, list]:
    if host_name != "claude":
        return [], []
    conflicts, info = [], []
    project_val = existing["values"].get("resolve_model_ids")
    if project_val == "omit":
        conflicts.append(
            _item(
                "resolve_model_ids",
                "project",
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
                global_val,
                _INERT_WHY,
            )
        )
        return conflicts, info
    conflicts.append(
        _item(
            "resolve_model_ids",
            "global",
            global_val,
            _copied_why(facts),
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
    return [_item("claude_md_path", "project", configured, text)]


def _legacy_depth_info(existing: dict) -> list:
    if "legacy_depth" not in existing:
        return []
    depth = existing["legacy_depth"]
    granularity = existing["values"].get("granularity")
    return [
        _item(
            "depth",
            "project",
            depth,
            f"legacy top-level depth {json.dumps(depth)} is read as granularity "
            f"{json.dumps(granularity)} by gsd-core (configuration.cjs normalization 4); "
            "a written granularity takes precedence and leaves depth unused",
        )
    ]


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
        _resolve_model_ids(host_name, existing, global_values, facts),
        _runtime_entries(host_name, existing, global_values),
    ):
        conflicts.extend(part[0])
        info.extend(part[1])
    info.extend(_claude_md_info(project_dir, existing, facts))
    info.extend(_legacy_depth_info(existing))
    return (
        sorted(conflicts, key=lambda row: (row["kind"], row["scope"])),
        sorted(info, key=lambda row: (row["kind"], row["scope"])),
    )


_LANE_REGISTRY_WARN = (
    "gsd-core review-lane registry unavailable; review lanes need plan-set"
)
_SKILLS_ROOTS_WARN = (
    "gsd-core skills roots unavailable; global and plugin skills are not inventoried"
)


def _normalize_lane_tables(tables: dict) -> tuple[dict, list[str]]:
    """Ensure lane/root fields exist for schema 2; warn when gsd-core reported null."""
    out = dict(tables)
    warnings: list[str] = []
    if "review_lanes" not in out:
        out["review_lanes"] = []
    elif out["review_lanes"] is None:
        out["review_lanes"] = []
        warnings.append(_LANE_REGISTRY_WARN)
    if "skills_roots" not in out:
        out["skills_roots"] = {}
    elif out["skills_roots"] is None:
        out["skills_roots"] = {}
        warnings.append(_SKILLS_ROOTS_WARN)
    return out, warnings


def _assemble_inventory(project_dir, host_name, host_source, core: host.GsdCore, parts: dict):
    existing = parts["existing_config"]
    configured = existing["values"].get("claude_md_path")
    facts = project_facts.project_facts(
        project_dir, configured if isinstance(configured, str) else None
    )
    conflicts, info = classify_conflicts(
        host_name, existing, parts["global_defaults"], facts, project_dir
    )
    home = parts["home"]
    skills_roots = parts["tables"].get("skills_roots") or {}
    skills = skill_scan.scan_skills(project_dir, host_name, skills_roots, home)
    ponytail = skill_scan.ponytail_visibility(skills_roots)
    if any(row.get("root_kind") == "plugin" for row in skills):
        info.append(
            _item(
                "plugin_skills",
                "project",
                None,
                "enabledPlugins layering assumed per key (unverified)",
            )
        )
        info = sorted(info, key=lambda row: (row["kind"], row["scope"]))
    warnings = set(core.warnings) | set(parts["catalog_warnings"]) | set(parts["config_warnings"])
    return {
        "schema_version": plan_io.INVENTORY_SCHEMA_VERSION,
        "host": host_name,
        "host_source": host_source,
        "gsd_core": {
            "path": core.root,
            "scope": core.scope,
            "version": core.version,
            **parts["tables"],
        },
        "existing_config": existing,
        "global_defaults": parts["global_defaults"],
        "catalog": parts["catalog"],
        "candidates": parts["candidates"],
        "candidate_heuristic_fields": parts["candidate_heuristic_fields"],
        "project": facts,
        "skills": skills,
        "ponytail_visibility": ponytail,
        "system_one_backend": parts["system_one_backend"],
        "installed_runtimes": parts["installed_runtimes"],
        "conflicts": conflicts,
        "info": info,
        "warnings": sorted(warnings),
    }


def _load_configs(project_dir, deps, host_name, core: host.GsdCore):
    """Project and global config plus the probed gsd-core tables, as inventory parts:
    `(parts, None)` or `(None, error_message)`."""
    node_bin = gsd_catalog.resolve_node_binary(deps.which_fn)
    env = deps.env_fn()
    existing, ex_warn = _existing_config(project_dir, core.tools_path, node_bin, deps)
    global_defaults, gl_warn = _global_defaults(env)
    probe = _probe_keys(host_name, existing["values"], global_defaults["values"])
    tables, table_err = _probe_gsd_tables(core, node_bin, project_dir, probe, deps)
    if tables is None:
        return None, table_err
    lane_tables, lane_warns = _normalize_lane_tables(tables)
    return {
        "existing_config": existing,
        "global_defaults": global_defaults,
        "tables": lane_tables,
        "config_warnings": [w for w in (ex_warn, gl_warn, *lane_warns) if w],
        "home": env.get("HOME") or os.path.expanduser("~"),
    }, None


def build_inventory(project_dir, opts: InventoryOpts, deps: host.InventoryDeps):
    """Returns `(inventory_dict, None)` or `(None, error_message)`."""
    host_name, host_source = host.detect_host(deps.env_fn(), opts.host)
    if host_name is None:
        return None, host_source
    core, error = host.resolve_gsd_core(project_dir, host_name, deps)
    if core is None:
        return None, error
    configs, error = _load_configs(project_dir, deps, host_name, core)
    if configs is None:
        return None, error
    fields, error = _catalog_fields(project_dir, opts, host_name, deps.env_fn(), deps.run_fn)
    if fields is None:
        return None, error
    parts = {**configs, **fields}
    parts["system_one_backend"] = skill_scan.system_one_backend(
        deps.env_fn(), deps.connect_fn
    )
    return _assemble_inventory(project_dir, host_name, host_source, core, parts), None
