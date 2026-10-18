"""Post-apply follow-ups (installer, effort sync): listed in one block; nothing runs without
`followups --approve`. Machine-level installs are never run. The installer argv pins
`@opengsd/gsd-core` to the inventory-resolved version (never an npm dist-tag name) and to the
public registry, so the target project's `.npmrc` cannot redirect the download (U-2)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from typing import Any, NamedTuple

from . import gsd_catalog, host

HOST_DIRS = {"claude": ".claude", "codex": ".codex", "opencode": ".opencode"}
EFFORT_SYNC_HOSTS = ("claude", "codex", "opencode")
PACKAGE = "@opengsd/gsd-core"
NPM_REGISTRY = "https://registry.npmjs.org/"
# An exact release (with optional prerelease); the VERSION file may sit in an untrusted checkout.
_SEMVER = re.compile(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?")
REQUIRE_IDS = ("installer", "effort_sync")

_INSTALLER_PURPOSE = "install a project-local gsd-core for this host"
_INSTALLER_ALT = (
    "pnpm dlx @opengsd/gsd-core@<version> --<host> --local (unverified under pnpm)"
)
_EFFORT_PURPOSE = "sync effort settings into agent frontmatter for this host"


class FollowUp(NamedTuple):
    id: str
    argv: list[str]
    cwd: str
    purpose: str
    alternative: str
    detail: str


class FollowupCtx(NamedTuple):
    plan_path: str
    inv_path: str
    project_dir: str
    deps: host.InventoryDeps


def installer_argv(version: str, host_name: str) -> list[str]:
    # Both flags: a scoped `@opengsd:registry` in .npmrc outranks a plain --registry.
    return [
        "npx",
        "-y",
        f"--registry={NPM_REGISTRY}",
        f"--@opengsd:registry={NPM_REGISTRY}",
        f"{PACKAGE}@{version}",
        f"--{host_name}",
        "--local",
    ]


def local_gsd_tools(project_dir: str, host_name: str, deps: host.InventoryDeps) -> str | None:
    core, _err = host.resolve_gsd_core(project_dir, host_name, deps)
    if core is not None and core.scope == "local":
        return core.tools_path
    return None


def changed_keys(plan: dict) -> list[str]:
    keys: list[str] = []
    for entry in plan.get("entries") or []:
        op = entry.get("op")
        key = entry.get("key")
        if not isinstance(key, str):
            continue
        if op == "set":
            if entry.get("value") != entry.get("existing"):
                keys.append(key)
        elif op == "unset" and entry.get("existing") is not None:
            keys.append(key)
    return sorted(keys)


def followup_ids(keys: list[str] | set[str], host_name: str) -> set[str]:
    ids: set[str] = set()
    for key in keys:
        if key.startswith("effort."):
            ids.add("effort_sync")
        if host_name == "codex" and key.startswith("model_overrides."):
            ids.add("installer")
    if host_name == "opencode":
        ids.add("installer")
    return ids


def workstream_config(inv: dict, project_dir: str, env: dict) -> str | None:
    recorded = inv.get("existing_config") or {}
    path = recorded.get("path")
    if isinstance(path, str) and path:
        root_cfg = os.path.join(project_dir, ".planning", "config.json")
        try:
            if os.path.realpath(path) != os.path.realpath(root_cfg):
                return path
        except OSError:
            return path
    ws = env.get("GSD_WORKSTREAM")
    if ws:
        return str(ws)
    return None


def effort_sync_argv(
    node: str,
    tools: str,
    host_name: str,
    project_dir: str,
    *,
    apply: bool,
) -> list[str]:
    flag = "--apply" if apply else "--dry-run"
    host_dir = HOST_DIRS[host_name]
    return [
        node,
        tools,
        "effort",
        "sync",
        flag,
        "--runtime",
        host_name,
        "--config-dir",
        os.path.join(project_dir, host_dir),
        "--project-dir",
        project_dir,
    ]


def effort_dry_run_count(argv: list[str], run_fn: Any, env: dict) -> int | None:
    try:
        proc = run_fn(
            argv,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
            env=env,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        body = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return None
    if not isinstance(body, dict):
        return None
    changes = body.get("changes")
    if not isinstance(changes, list):
        return None
    return len(changes)


def _followup_dict(row: FollowUp) -> dict:
    return {
        "id": row.id,
        "argv": row.argv,
        "cwd": row.cwd,
        "purpose": row.purpose,
        "alternative": row.alternative,
        "detail": row.detail,
    }


def _inventory_version(inv: dict) -> str | None:
    version = (inv.get("gsd_core") or {}).get("version")
    if not isinstance(version, str) or not _SEMVER.fullmatch(version):
        return None
    return version


def _disclosures() -> list[str]:
    return [
        "npx -y downloads and runs an npm package from the registry",
        f"the argv pins the registry to {NPM_REGISTRY} so the project's .npmrc cannot "
        "redirect it; its other settings (proxy, auth, scripts) still apply",
        "pnpm dlx is the equivalent of npx -y (unverified under the pnpm shim)",
        "a non-Claude --local install rewrites ~/.gsd/defaults.json and scans home "
        "host dirs unless --no-legacy-cleanup is passed; the locked argv above omits it",
    ]


def _intel_recommended(plan: dict, inv: dict) -> list[dict]:
    enabled = False
    for entry in plan.get("entries") or []:
        if entry.get("key") == "intel.enabled" and entry.get("op") == "set":
            enabled = entry.get("value") is True
    project = inv.get("project") or {}
    if enabled and not project.get("intel_index_present", False):
        return [{"id": "map_codebase", "text": "Run /gsd-map-codebase to build the intel index"}]
    return []


def _no_effort_host_note(host_name: str) -> str:
    return f"effort sync not offered on {host_name}: no effort: frontmatter"


def _missing_local_note(host_name: str, project_dir: str) -> str:
    return (
        f"effort sync not offered: no project-local gsd-core for {host_name} in "
        f"{project_dir}; effort keys take effect only after a local gsd-core install "
        "runs its effort sync"
    )


def _workstream_note(ws: str) -> str:
    return (
        f"effort sync not offered for workstream config {ws}: gsd-core's effort sync reads "
        "only the root .planning/config.json and ~/.gsd/defaults.json, so it would sync "
        "the root's effort settings, not the ones apply wrote"
    )


def _config_dir_note() -> str:
    return "effort sync --config-dir value is inferred from the host layout (unverified)"


def _smoke_scope(host_name: str) -> str:
    """What the ai-kit Phase 20 smoke actually ran, and what it did not."""
    return (
        f"observed in the ai-kit Phase 20 smoke, which ran gsd-core 1.17.0's cached installer "
        f"as --{host_name} --local --no-legacy-cleanup under a throwaway HOME; this follow-up's "
        "argv (no --no-legacy-cleanup, the real HOME, the inventory's version), the shipped "
        "npx launcher and its registry fetch were not exercised"
    )


def _opencode_root_note(project_dir: str) -> str:
    root = os.path.join(project_dir, ".opencode", "gsd-core")
    return f"the local install root {root} follows the layout {_smoke_scope('opencode')}"


_GITIGNORE_KEEP_DIR = {
    # bin/install.js installCodexConfig merges GSD's block into this file (gsd-core 1.17.0)
    "codex": "gsd-core 1.17.0's installer merges its block into .codex/config.toml "
    "(source-inspected), which may hold your own codex settings",
    "opencode": "opencode keeps its own files in .opencode/ (D-12; an opencode-written "
    ".opencode/.gitignore was not observed in the Phase 20 smoke)",
}


def _gitignore_prefix_note(host_name: str) -> str | None:
    if host_name not in _GITIGNORE_KEEP_DIR:
        return None
    host_dir = HOST_DIRS[host_name]
    return (
        f"GSD-generated paths to gitignore by prefix in this project: {host_dir}/gsd-core/, "
        f"{host_dir}/agents/gsd-*, {host_dir}/commands/gsd-*, {host_dir}/skills/gsd-*, "
        f"{host_dir}/plugins/gsd-core.js, {host_dir}/gsd-*.json; never ignore the whole "
        f"{host_dir} directory: {_GITIGNORE_KEEP_DIR[host_name]}; curated-config reports "
        "this and never edits .gitignore"
    )


def _unknown_version_note() -> str:
    return (
        "local gsd-core installer not offered: inventory gsd_core.version is unknown or "
        "not an exact release version; pin a version by hand before installing"
    )


def _codex_installer_note() -> str:
    layout = "codex installer follow-up: the <project>/.codex/gsd-core layout was"
    return f"{layout} {_smoke_scope('codex')}"


def _maybe_installer(
    host_name: str,
    inv: dict,
    ctx: FollowupCtx,
    candidates: set[str],
    notes: list[str],
) -> FollowUp | None:
    if "installer" not in candidates:
        return None
    if host_name not in ("opencode", "codex"):
        return None
    version = _inventory_version(inv)
    if version is None:
        notes.append(_unknown_version_note())
        return None
    if host_name == "codex":
        notes.append(_codex_installer_note())
    return FollowUp(
        "installer",
        installer_argv(version, host_name),
        ctx.project_dir,
        _INSTALLER_PURPOSE,
        _INSTALLER_ALT,
        f"pinned to gsd-core {version} from inventory",
    )


def _effort_blocked(
    host_name: str,
    ctx: FollowupCtx,
    inv: dict,
    has_installer: bool,
    notes: list[str],
) -> bool:
    if host_name not in EFFORT_SYNC_HOSTS:
        notes.append(_no_effort_host_note(host_name))
        return True
    if host_name in ("claude", "opencode"):
        ws = workstream_config(inv, ctx.project_dir, ctx.deps.env_fn())
        if ws is not None:
            notes.append(_workstream_note(ws))
            return True
    tools = local_gsd_tools(ctx.project_dir, host_name, ctx.deps)
    if tools is None and not has_installer:
        notes.append(_missing_local_note(host_name, ctx.project_dir))
        return True
    return False


def _effort_detail(
    tools: str | None,
    node: str | None,
    host_name: str,
    ctx: FollowupCtx,
    has_installer: bool,
) -> str:
    if tools is None and has_installer:
        return "change count unavailable until the local install exists"
    if tools is None or node is None:
        return "change count unavailable"
    dry_argv = effort_sync_argv(node, tools, host_name, ctx.project_dir, apply=False)
    count = effort_dry_run_count(dry_argv, ctx.deps.run_fn, ctx.deps.env_fn())
    if count is None:
        return "change count unavailable (dry-run failed)"
    return f"effort sync --dry-run reports {count} change(s)"


def _build_effort_row(
    host_name: str,
    ctx: FollowupCtx,
    has_installer: bool,
    notes: list[str],
) -> FollowUp | None:
    node = gsd_catalog.resolve_node_binary(ctx.deps.which_fn)
    if node is None:
        notes.append("effort sync not offered: node was not found on PATH")
        return None
    tools = local_gsd_tools(ctx.project_dir, host_name, ctx.deps)
    detail = _effort_detail(tools, node, host_name, ctx, has_installer)
    notes.append(_config_dir_note())
    if tools is not None:
        argv = effort_sync_argv(node, tools, host_name, ctx.project_dir, apply=True)
    else:
        argv = effort_sync_argv(
            node, "<local-gsd-tools>", host_name, ctx.project_dir, apply=True
        )
    return FollowUp("effort_sync", argv, ctx.project_dir, _EFFORT_PURPOSE, "", detail)


def block_fingerprint(required: list[dict]) -> str:
    """Binds an approval to the exact rows the user saw (id, argv, cwd)."""
    rows = [{"id": r["id"], "argv": r["argv"], "cwd": r["cwd"]} for r in required]
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _approve_with(ctx: FollowupCtx, required: list[dict]) -> str:
    if not required:
        return ""
    ids = {row["id"] for row in required}
    ordered = [i for i in REQUIRE_IDS if i in ids]
    argv = [
        "followups",
        "--plan",
        ctx.plan_path,
        "--inventory",
        ctx.inv_path,
        "--project-dir",
        ctx.project_dir,
        "--approve",
        "--require",
        ",".join(ordered),
        "--fingerprint",
        block_fingerprint(required),
    ]
    return shlex.join(argv)


def build_followups(
    plan: dict,
    inv: dict,
    ctx: FollowupCtx,
    force_ids: tuple[str, ...] | list[str] = (),
) -> dict:
    host_name = plan.get("host")
    if not isinstance(host_name, str):
        host_name = str(inv.get("host") or "")
    candidates = followup_ids(changed_keys(plan), host_name) | set(force_ids)
    notes: list[str] = []
    installer = _maybe_installer(host_name, inv, ctx, candidates, notes)
    has_installer = installer is not None
    if host_name == "opencode" and has_installer:
        notes.append(_opencode_root_note(ctx.project_dir))
    gitignore_note = _gitignore_prefix_note(host_name)
    if has_installer and gitignore_note is not None:
        notes.append(gitignore_note)
    effort: FollowUp | None = None
    if "effort_sync" in candidates and not _effort_blocked(
        host_name, ctx, inv, has_installer, notes
    ):
        effort = _build_effort_row(host_name, ctx, has_installer, notes)
    required = [_followup_dict(row) for row in (installer, effort) if row is not None]
    return {
        "required": required,
        "recommended": _intel_recommended(plan, inv),
        "notes": notes,
        "disclosures": _disclosures() if has_installer else [],
        "approve_with": _approve_with(ctx, required),
    }


def _tail(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def _run_one(row: FollowUp, run_fn: Any, env: dict) -> dict:
    try:
        proc = run_fn(
            row.argv,
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
            cwd=row.cwd,
            env=env,
        )
        rc = proc.returncode
        out = proc.stdout or ""
        err = proc.stderr or ""
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        rc = 1
        out = ""
        err = str(exc)
    return {
        "id": row.id,
        "argv": row.argv,
        "cwd": row.cwd,
        "returncode": rc,
        "stdout_tail": _tail(out),
        "stderr_tail": _tail(err),
    }


def _resolve_effort_argv(
    row: FollowUp,
    host_name: str,
    ctx: FollowupCtx,
) -> tuple[FollowUp | None, str | None]:
    if row.id != "effort_sync":
        return row, None
    if row.argv and "<local-gsd-tools>" not in row.argv[1]:
        return row, None
    tools = local_gsd_tools(ctx.project_dir, host_name, ctx.deps)
    node = gsd_catalog.resolve_node_binary(ctx.deps.which_fn)
    if tools is None or node is None:
        return None, "no project-local gsd-core after the installer"
    resolved = FollowUp(
        row.id,
        effort_sync_argv(node, tools, host_name, ctx.project_dir, apply=True),
        row.cwd,
        row.purpose,
        row.alternative,
        row.detail,
    )
    return resolved, None


def run_followups(
    block: dict,
    host_name: str,
    ctx: FollowupCtx,
) -> tuple[int, list[dict]]:
    env = ctx.deps.env_fn()
    results: list[dict] = []
    for raw in block.get("required") or []:
        row = FollowUp(
            raw["id"],
            list(raw["argv"]),
            raw["cwd"],
            raw.get("purpose", ""),
            raw.get("alternative", ""),
            raw.get("detail", ""),
        )
        row, err = _resolve_effort_argv(row, host_name, ctx)
        if err is not None:
            print(
                f"ai-kit-gsd-curated-config: effort_sync failed; {err}",
                file=sys.stderr,
            )
            return 1, results
        assert row is not None
        result = _run_one(row, ctx.deps.run_fn, env)
        results.append(result)
        if result["returncode"] != 0:
            cmd = shlex.join(row.argv)
            print(
                f"ai-kit-gsd-curated-config: {row.id} failed; run it yourself: {cmd} "
                f"(cwd {row.cwd})",
                file=sys.stderr,
            )
            return 1, results
    return 0, results
