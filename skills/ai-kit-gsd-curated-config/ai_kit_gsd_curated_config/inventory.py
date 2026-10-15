"""Read-only inventory assembly: host, gsd-core tables, and probed valid keys (INV-01, REC-06).

All inventory I/O lives here; nothing in this module writes project or gsd-core config.
"""
from __future__ import annotations

from typing import NamedTuple

from . import gsd_catalog, host, plan_io, presets

_PROBE_UNAVAILABLE = (
    "gsd-core at {root} (version {version}): isValidConfigKey unavailable "
    "(require failed or export missing)"
)


class InventoryOpts(NamedTuple):
    host: str | None


def _probe_keys(host_name: str) -> list[str]:
    return presets.closed_key_set(host_name)


def _missing_lib_error(core, filename: str) -> str:
    ver = core.version or "unknown"
    return f"gsd-core at {core.root} (version {ver}): missing lib/{filename}"


def build_inventory(project_dir, opts: InventoryOpts, deps: host.InventoryDeps):
    """Returns `(inventory_dict, None)` or `(None, error_message)`."""
    host_name, host_source = host.detect_host(deps.env_fn(), opts.host)
    if host_name is None:
        return None, host_source
    core, error = host.resolve_gsd_core(project_dir, host_name, deps)
    if core is None:
        return None, error
    node_bin = gsd_catalog.resolve_node_binary(deps.which_fn)
    if node_bin is None:
        return None, "could not resolve 'node' on PATH"
    model_catalog = gsd_catalog.resolve_model_catalog_cjs_path(core.tools_path)
    config_schema = gsd_catalog.resolve_config_schema_cjs_path(core.tools_path)
    if model_catalog is None or config_schema is None:
        missing = "model-catalog.cjs" if model_catalog is None else "config-schema.cjs"
        return None, _missing_lib_error(core, missing)
    paths = gsd_catalog.GsdCorePaths(node_bin, model_catalog, config_schema)
    tables = gsd_catalog.query_gsd_tables(paths, project_dir, _probe_keys(host_name), deps.run_fn)
    if tables is None:
        ver = core.version or "unknown"
        return None, _PROBE_UNAVAILABLE.format(root=core.root, version=ver)
    inv = {
        "schema_version": plan_io.INVENTORY_SCHEMA_VERSION,
        "host": host_name,
        "host_source": host_source,
        "gsd_core": {"path": core.root, "scope": core.scope, "version": core.version, **tables},
        "warnings": list(core.warnings),
    }
    return inv, None
