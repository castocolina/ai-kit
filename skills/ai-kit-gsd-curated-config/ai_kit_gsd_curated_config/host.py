"""Host detection and gsd-core resolution for the read-only inventory (D-11 scope labelling).

Resolution delegates to the shared `ai_kit_spec.gsd_tools` candidate list — never a second
hand-copied launcher order. On pi and opencode hosts the project-local gsd-core under
`<root>/.pi/gsd-core` or `<root>/.opencode/gsd-core` is tried before GSD's shared order
(17 D-11 amended, 18-02); every other candidate comes from `gsd_tools_candidates`.
"""
from __future__ import annotations

import os
import socket
import subprocess
from collections.abc import Callable
from typing import Any, NamedTuple

from . import gsd_catalog

HOSTS = ("claude", "codex", "opencode", "cursor", "pi")

# Project-local gsd-core roots tried before GSD's shared launcher order (pi, opencode).
_HOST_FIRST_ROOT = {
    "pi": ".pi",
    # Verified by the Phase 20 opencode smoke (20-SMOKE-OPENCODE.md): the installer's local
    # root is <project>/.opencode/gsd-core.
    "opencode": ".opencode",
}

_UNKNOWN_HOST_MSG = (
    "could not detect the host CLI; pass --host claude|codex|opencode|cursor|pi"
)


class InventoryDeps(NamedTuple):
    which_fn: Callable[..., str | None]
    run_fn: Callable[..., subprocess.CompletedProcess]
    env_fn: Callable[[], dict]
    connect_fn: Callable[..., Any] = socket.create_connection


class GsdCore(NamedTuple):
    tools_path: str
    root: str
    scope: str
    version: str | None
    warnings: tuple[str, ...]


def detect_host(env: dict, override: str | None) -> tuple[str | None, str]:
    """Returns `(host, host_source)` or `(None, error_message)`."""
    if override is not None:
        return override, "flag"
    detection = gsd_catalog.load_ai_kit_spec_module("detection")
    if detection is None:
        return None, gsd_catalog.SIBLING_MISSING
    label = detection.detect_current_runtime(env)
    if label == "unknown":
        return None, _UNKNOWN_HOST_MSG
    return label, "detected"


def _local_roots(gsd_tools, root: str, host: str) -> list[str]:
    locals_ = list(gsd_tools.local_gsd_core_roots(root))
    sub = _HOST_FIRST_ROOT.get(host)
    if sub is not None:
        locals_.insert(0, os.path.join(root, sub, "gsd-core"))
    return locals_


def _gsd_tools_candidates(gsd_tools, env: dict, root: str, host: str, which_fn) -> list[str]:
    paths: list[str] = []
    sub = _HOST_FIRST_ROOT.get(host)
    if sub is not None:
        local_tools = os.path.join(root, sub, "gsd-core", gsd_tools.GSD_TOOLS_REL)
        paths.append(os.path.expanduser(local_tools))
    paths.extend(gsd_tools.gsd_tools_candidates(env, root, which_fn))
    return paths


def _main_checkout(project_dir: str, run_fn: Callable[..., subprocess.CompletedProcess]):
    """Main git checkout dir when `project_dir` is a linked worktree, else `None`."""
    try:
        out = run_fn(
            ["git", "-C", project_dir, "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    common = (out.stdout or "").strip()
    if not common or os.path.basename(common) != ".git":
        return None
    return os.path.dirname(common)


def _worktree_warning(gsd_tools, main: str, host: str, install_root: str) -> str | None:
    for local_root in _local_roots(gsd_tools, main, host):
        tools = os.path.join(local_root, gsd_tools.GSD_TOOLS_REL)
        if os.path.isfile(tools):
            # One f-string, never str.format: a "{" in a path must not become a field.
            return (
                f"gsd-core resolved globally at {install_root}, but the main checkout {main} "
                "has a project-local install; versions can differ (D-11)"
            )
    return None


def _linked_main_checkout(project_dir: str, root: str, run_fn) -> str | None:
    """The main checkout when `project_dir` sits in a linked worktree of another dir."""
    main = _main_checkout(project_dir, run_fn)
    if not main or os.path.normpath(main) == os.path.normpath(root):
        return None
    return main


def resolve_gsd_core(
    project_dir: str, host: str, deps: InventoryDeps
) -> tuple[GsdCore | None, str | None]:
    """First existing gsd-tools.cjs in launcher order; labels project-local vs global scope."""
    gsd_tools = gsd_catalog.load_ai_kit_spec_module("gsd_tools")
    if gsd_tools is None:
        return None, gsd_catalog.SIBLING_MISSING
    env = deps.env_fn()
    root = gsd_tools.project_root(env, project_dir, deps.run_fn)
    candidates = _gsd_tools_candidates(gsd_tools, env, root, host, deps.which_fn)
    tools_path = next((p for p in candidates if os.path.isfile(p)), None)
    if tools_path is None:
        lines = "\n".join(f"  {p}" for p in candidates)
        return None, f"no gsd-core found for {project_dir}; searched:\n{lines}"
    install_root = os.path.normpath(os.path.dirname(os.path.dirname(tools_path)))
    local_set = {os.path.normpath(r) for r in _local_roots(gsd_tools, root, host)}
    scope = "local" if install_root in local_set else "global"
    version = gsd_tools.gsd_core_version(tools_path)
    main = _linked_main_checkout(project_dir, root, deps.run_fn) if scope == "global" else None
    warning = _worktree_warning(gsd_tools, main, host, install_root) if main else None
    return GsdCore(tools_path, install_root, scope, version, (warning,) if warning else ()), None
