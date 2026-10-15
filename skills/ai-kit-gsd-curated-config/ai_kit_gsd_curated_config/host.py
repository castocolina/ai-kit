"""Host detection and gsd-core resolution for the read-only inventory (D-11 scope labelling).

Resolution delegates to the shared `ai_kit_spec.gsd_tools` candidate list — never a second
hand-copied launcher order. On pi hosts `<root>/.pi/gsd-core` is tried before GSD's shared
order (17 D-11 amended, 22 D-08); every other candidate comes from `gsd_tools_candidates`.
"""
from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from typing import NamedTuple

from . import gsd_catalog

HOSTS = ("claude", "codex", "opencode", "cursor", "pi")

_SIBLING_MSG = (
    "the ai-kit-spec-review sibling skill (ai_kit_spec) is not installed next to this skill"
)
_UNKNOWN_HOST_MSG = (
    "could not detect the host CLI; pass --host claude|codex|opencode|cursor|pi"
)


class InventoryDeps(NamedTuple):
    which_fn: Callable[..., str | None]
    run_fn: Callable[..., subprocess.CompletedProcess]
    env_fn: Callable[[], dict]


class GsdCore(NamedTuple):
    tools_path: str
    root: str
    scope: str
    version: str | None
    warnings: tuple[str, ...]


def host_cli(host: str) -> str:
    """Maps inventory host labels to KNOWN_CLIS binary names."""
    return "cursor-agent" if host == "cursor" else host


def detect_host(env: dict, override: str | None) -> tuple[str | None, str]:
    """Returns `(host, host_source)` or `(None, error_message)`."""
    if override is not None:
        return override, "flag"
    detection = gsd_catalog.load_ai_kit_spec_module("detection")
    if detection is None:
        return None, _SIBLING_MSG
    label = detection.detect_current_runtime(env)
    if label == "unknown":
        return None, _UNKNOWN_HOST_MSG
    return label, "detected"


def _local_roots(root: str, host: str) -> list[str]:
    gsd_tools = gsd_catalog.load_ai_kit_spec_module("gsd_tools")
    if gsd_tools is None:
        return []
    locals_ = list(gsd_tools.local_gsd_core_roots(root))
    if host == "pi":
        locals_.insert(0, os.path.join(root, ".pi", "gsd-core"))
    return locals_


def _gsd_tools_candidates(env: dict, root: str, host: str) -> list[str]:
    gsd_tools = gsd_catalog.load_ai_kit_spec_module("gsd_tools")
    if gsd_tools is None:
        return []
    paths: list[str] = []
    if host == "pi":
        pi_tools = os.path.join(root, ".pi", "gsd-core", gsd_tools.GSD_TOOLS_REL)
        paths.append(os.path.expanduser(pi_tools))
    paths.extend(gsd_tools.gsd_tools_candidates(env, root))
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


def _worktree_warning(main: str, host: str) -> str | None:
    gsd_tools = gsd_catalog.load_ai_kit_spec_module("gsd_tools")
    if gsd_tools is None:
        return None
    for local_root in _local_roots(main, host):
        tools = os.path.join(local_root, gsd_tools.GSD_TOOLS_REL)
        if os.path.isfile(tools):
            return (
                f"gsd-core resolved globally at {{root}}, but the main checkout {main} has a "
                "project-local install; versions can differ (D-11)"
            )
    return None


def _global_worktree_warnings(install_root: str, project_dir: str, host: str, root: str, run_fn):
    main = _main_checkout(project_dir, run_fn)
    if not main or os.path.normpath(main) == os.path.normpath(root):
        return ()
    template = _worktree_warning(main, host)
    if not template:
        return ()
    return (template.format(root=install_root),)


def resolve_gsd_core(
    project_dir: str, host: str, deps: InventoryDeps
) -> tuple[GsdCore | None, str | None]:
    """First existing gsd-tools.cjs in launcher order; labels project-local vs global scope."""
    gsd_tools = gsd_catalog.load_ai_kit_spec_module("gsd_tools")
    if gsd_tools is None:
        return None, _SIBLING_MSG
    env = deps.env_fn()
    root = gsd_tools.project_root(env, project_dir, deps.run_fn)
    candidates = _gsd_tools_candidates(env, root, host)
    tools_path = next((p for p in candidates if os.path.isfile(p)), None)
    if tools_path is None:
        lines = "\n".join(f"  {p}" for p in candidates)
        return None, f"no gsd-core found for {project_dir}; searched:\n{lines}"
    install_root = os.path.normpath(os.path.dirname(os.path.dirname(tools_path)))
    local_set = {os.path.normpath(r) for r in _local_roots(root, host)}
    scope = "local" if install_root in local_set else "global"
    version = gsd_tools.gsd_core_version(tools_path)
    extra = (
        _global_worktree_warnings(install_root, project_dir, host, root, deps.run_fn)
        if scope == "global"
        else ()
    )
    return GsdCore(tools_path, install_root, scope, version, tuple(sorted(extra))), None
