"""Read-only inventory assembly: host, gsd-core tables, and probed valid keys (INV-01, REC-06).

All inventory I/O lives here; nothing in this module writes project or gsd-core config.
"""
from __future__ import annotations

from typing import NamedTuple

from . import catalog_adapter, gsd_catalog, host, plan_io, presets

_PROBE_UNAVAILABLE = (
    "gsd-core at {root} (version {version}): isValidConfigKey unavailable "
    "(require failed or export missing)"
)


class InventoryOpts(NamedTuple):
    host: str | None
    refresh: bool = False


def _probe_keys(host_name: str) -> list[str]:
    return presets.closed_key_set(host_name)


def _missing_lib_error(core, filename: str) -> str:
    ver = core.version or "unknown"
    return f"gsd-core at {core.root} (version {ver}): missing lib/{filename}"


def _probe_gsd_tables(core, host_name, project_dir, deps):
    node_bin = gsd_catalog.resolve_node_binary(deps.which_fn)
    if node_bin is None:
        return None, "could not resolve 'node' on PATH"
    model_catalog = gsd_catalog.resolve_model_catalog_cjs_path(core.tools_path)
    config_schema = gsd_catalog.resolve_config_schema_cjs_path(core.tools_path)
    if model_catalog is None or config_schema is None:
        missing = "model-catalog.cjs" if model_catalog is None else "config-schema.cjs"
        return None, _missing_lib_error(core, missing)
    paths = gsd_catalog.GsdCorePaths(node_bin, model_catalog, config_schema)
    tables = gsd_catalog.query_gsd_tables(
        paths, project_dir, _probe_keys(host_name), deps.run_fn
    )
    if tables is None:
        ver = core.version or "unknown"
        return None, _PROBE_UNAVAILABLE.format(root=core.root, version=ver)
    return tables, None


def _catalog_fields(project_dir, opts, host_name, env, run_fn):
    cat, cat_err = catalog_adapter.refresh_catalog(project_dir, env, opts.refresh, run_fn)
    if cat is None:
        return None, cat_err
    candidates = catalog_adapter.build_candidates(
        cat.runtimes, cat.entries, host.host_cli(host_name), cat.weights
    )
    return {
        "catalog": {"state": cat.state, "scored": cat.scored},
        "candidates": candidates,
        "candidate_heuristic_fields": list(catalog_adapter.CANDIDATE_HEURISTIC_FIELDS),
        "catalog_warnings": cat.warnings,
    }, None


def build_inventory(project_dir, opts: InventoryOpts, deps: host.InventoryDeps):
    """Returns `(inventory_dict, None)` or `(None, error_message)`."""
    host_name, host_source = host.detect_host(deps.env_fn(), opts.host)
    if host_name is None:
        return None, host_source
    core, error = host.resolve_gsd_core(project_dir, host_name, deps)
    if core is None:
        return None, error
    tables, table_err = _probe_gsd_tables(core, host_name, project_dir, deps)
    if tables is None:
        return None, table_err
    fields, cat_err = _catalog_fields(
        project_dir, opts, host_name, deps.env_fn(), deps.run_fn
    )
    if fields is None:
        return None, cat_err
    cat_warnings = fields.pop("catalog_warnings")
    inv = {
        "schema_version": plan_io.INVENTORY_SCHEMA_VERSION,
        "host": host_name,
        "host_source": host_source,
        "gsd_core": {"path": core.root, "scope": core.scope, "version": core.version, **tables},
        **fields,
        "warnings": sorted(set(core.warnings) | set(cat_warnings)),
    }
    return inv, None
