"""Read-only skill location scan for inventory (D-31, D-32, D-35, D-36).

Reads plugin skills only under ``<installPath>/skills/``; never reads secret values into
output. ``enabledPlugins`` layering (user, project, local; last wins) is assumed per key
(unverified).
"""
from __future__ import annotations

import json
import os
import re
import threading
from typing import Any
from urllib.parse import urlsplit

from . import gsd_catalog, host

# Always fullmatch: re.match with "$" also accepts a trailing newline (C-IN-01).
SKILL_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")
PONYTAIL_SKILLS = (
    "ponytail",
    "ponytail-audit",
    "ponytail-debt",
    "ponytail-gain",
    "ponytail-help",
    "ponytail-review",
)
DESCRIPTION_MAX = 300
CONNECT_TIMEOUT_S = 1.5
URL_NOTE = "reachable, not verified as System One"

# YAML block scalar header: style, then optional chomping and indent indicators in either order.
_BLOCK_INDICATOR = re.compile(r"[>|](?:[-+]?[1-9]?|[1-9][-+])")
_ROOT_KIND_ORDER = {"global": 0, "plugin": 1, "project": 2}


def _read_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _real(path: str) -> str | None:
    try:
        return os.path.realpath(path)
    except OSError:
        return None


def _inside(inner: str, outer: str) -> bool:
    try:
        return os.path.commonpath([inner, outer]) == outer
    except ValueError:
        return False


def _home_rel(real_dir: str, home: str) -> str | None:
    home_real = _real(home)
    if home_real is None or not _inside(real_dir, home_real):
        return None
    rel = os.path.relpath(real_dir, home_real)
    return "~/" + rel.replace(os.sep, "/")


def _parse_description(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    end = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end = idx
            break
    if end is None:
        return ""
    body = lines[1:end]
    desc_lines: list[str] = []
    in_desc = False
    for line in body:
        if not in_desc:
            if line.startswith("description:"):
                rest = line[len("description:") :].strip()
                if _BLOCK_INDICATOR.fullmatch(rest):
                    in_desc = True
                    continue
                if rest.startswith(('"', "'")) and rest.endswith(rest[0]) and len(rest) >= 2:
                    rest = rest[1:-1]
                desc_lines.append(rest)
                break
            continue
        if line and not line[0].isspace():
            break
        desc_lines.append(line.strip())
    joined = " ".join(part for part in desc_lines if part)
    return joined[:DESCRIPTION_MAX]


def _read_description(skill_md: str) -> str:
    try:
        with open(skill_md, encoding="utf-8") as handle:
            return _parse_description(handle.read())
    except (OSError, ValueError, UnicodeDecodeError):
        return ""


def _escapes_root(skill_dir: str, root_dir: str) -> bool:
    root_real = _real(root_dir)
    if root_real is None:
        return False
    dir_real = _real(skill_dir)
    md_real = _real(os.path.join(skill_dir, "SKILL.md"))
    dir_out = dir_real is not None and not _inside(dir_real, root_real)
    md_out = md_real is not None and not _inside(md_real, root_real)
    return dir_out or md_out


def _escapes_project(skill_dir: str, project_dir: str) -> bool:
    """gsd-core's project rule (``tryWithinRoot(skillPath, projectRoot)``): the skill
    directory's realpath must stay inside the project's; ``SKILL.md`` is not resolved."""
    proj_real, dir_real = _real(project_dir), _real(skill_dir)
    return proj_real is None or dir_real is None or not _inside(dir_real, proj_real)


def _real_dir(skill_dir: str) -> str | None:
    md_real = _real(os.path.join(skill_dir, "SKILL.md"))
    if md_real is None:
        return _real(skill_dir)
    return os.path.dirname(md_real)


def scan_root(
    root: str,
    root_kind: str,
    label: str,
    home: str,
    plugin: str | None = None,
) -> list[dict]:
    """One entry per child dir holding SKILL.md; missing root -> []."""
    if not root or not os.path.isdir(root):
        return []
    out: list[dict] = []
    try:
        names = os.listdir(root)
    except OSError:
        return []
    for name in names:
        skill_dir = os.path.join(root, name)
        skill_md = os.path.join(skill_dir, "SKILL.md")
        if not os.path.isfile(skill_md):  # follows links: a dangling SKILL.md is skipped
            continue
        resolved = _real_dir(skill_dir)
        if resolved is None:
            continue
        addr_name = bool(SKILL_NAME_RE.fullmatch(name))
        addr_plugin = plugin is None or bool(SKILL_NAME_RE.fullmatch(plugin))
        out.append(
            {
                "name": name,
                "root_kind": root_kind,
                "root": label,
                "plugin": plugin,
                "real_dir": resolved,
                "real_dir_home": _home_rel(resolved, home),
                "escapes_root": _escapes_root(skill_dir, root),
                "addressable": addr_name and addr_plugin,
                "description": _read_description(skill_md),
            }
        )
    return out


def _merged_enabled(claude_dir: str, project_dir: str) -> dict[str, bool]:
    paths = (
        os.path.join(claude_dir, "settings.json"),
        os.path.join(project_dir, ".claude", "settings.json"),
        os.path.join(project_dir, ".claude", "settings.local.json"),
    )
    merged: dict[str, bool] = {}
    for path in paths:
        data = _read_json(path)
        layer = data.get("enabledPlugins")
        if isinstance(layer, dict):
            merged.update(layer)
    return merged


def _plugin_display_name(install_path: str, plugin_id: str) -> str:
    manifest = _read_json(os.path.join(install_path, ".claude-plugin", "plugin.json"))
    name = manifest.get("name")
    if isinstance(name, str) and name:
        return name
    return plugin_id.split("@", 1)[0]


def _record_matches(record: dict, project_dir: str) -> bool:
    scope = record.get("scope")
    if scope == "user":
        return True
    if scope in ("project", "local"):
        proj = record.get("projectPath")
        if isinstance(proj, str):
            try:
                return os.path.samefile(proj, project_dir)
            except OSError:
                return os.path.normpath(proj) == os.path.normpath(project_dir)
    return False


def plugin_skills(claude_dir: str, project_dir: str, home: str) -> list[dict]:
    """Claude plugin skills from installed_plugins.json and layered enabledPlugins."""
    manifest_path = os.path.join(claude_dir, "plugins", "installed_plugins.json")
    data = _read_json(manifest_path)
    plugins = data.get("plugins")
    if not isinstance(plugins, dict):
        return []
    enabled = _merged_enabled(claude_dir, project_dir)
    out: list[dict] = []
    for plugin_id, records in plugins.items():
        if not isinstance(records, list):
            continue
        install_path = None
        for record in records:
            if not isinstance(record, dict):
                continue
            if not _record_matches(record, project_dir):
                continue
            path = record.get("installPath")
            if isinstance(path, str) and path:
                install_path = path
                break
        if install_path is None or not enabled.get(plugin_id):
            continue
        if not os.path.isdir(install_path):
            continue
        display = _plugin_display_name(install_path, plugin_id)
        skills_root = os.path.join(install_path, "skills")
        # shortcut: custom plugin.json skill paths and a root SKILL.md are not scanned
        out.extend(scan_root(skills_root, "plugin", plugin_id, home, plugin=display))
    return out


def scan_skills(
    project_dir: str,
    host_name: str,
    skills_roots: dict,
    home: str,
) -> list[dict]:
    """Sorted by (root_kind, root, name)."""
    entries: list[dict] = []
    proj_root = os.path.join(project_dir, "skills")
    for row in scan_root(proj_root, "project", "skills", home):
        row["escapes_root"] = _escapes_project(os.path.join(proj_root, row["name"]), project_dir)
        entries.append(row)
    global_root = skills_roots.get(host_name) if isinstance(skills_roots, dict) else None
    if isinstance(global_root, str) and global_root:
        entries.extend(scan_root(global_root, "global", global_root, home))
    if host_name == "claude":
        claude_skills = skills_roots.get("claude") if isinstance(skills_roots, dict) else None
        if isinstance(claude_skills, str) and claude_skills:
            claude_dir = os.path.dirname(claude_skills)
            entries.extend(plugin_skills(claude_dir, project_dir, home))
    def _sort_key(row: dict) -> tuple:
        kind = _ROOT_KIND_ORDER.get(row["root_kind"], 9)
        return kind, row["root"], row["name"]

    entries.sort(key=_sort_key)
    return entries


def ponytail_visibility(skills_roots: dict, home: str) -> dict[str, list[str]]:
    """Per-host ponytail skill names under each host's global skills root only: Claude
    plugin skills are not counted here (they are ``skills`` rows with ``root_kind: plugin``)."""
    out: dict[str, list[str]] = {h: [] for h in host.HOSTS}
    if not isinstance(skills_roots, dict):
        return out
    pony_set = set(PONYTAIL_SKILLS)
    for host_name in host.HOSTS:
        root = skills_roots.get(host_name)
        if not isinstance(root, str) or not root:
            continue
        found = {e["name"] for e in scan_root(root, "global", root, home) if e["name"] in pony_set}
        out[host_name] = sorted(found)
    return out


def _url_endpoint(raw_url: str) -> tuple[str, int] | None:
    parts = urlsplit(raw_url.strip())
    if not parts.hostname:
        return None
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        return None
    try:
        port = parts.port
    except ValueError:
        return None
    if port is None:
        port = 443 if scheme == "https" else 80
    return parts.hostname, port


def _tcp_reachable(endpoint: tuple[str, int], connect_fn) -> bool:
    holder: list[Any] = []
    err: list[BaseException] = []

    def _worker() -> None:
        try:
            sock = connect_fn(endpoint, timeout=CONNECT_TIMEOUT_S)
            holder.append(sock)
            sock.close()
        except (OSError, ValueError) as exc:  # ValueError: UnicodeError on an IDNA-invalid host
            err.append(exc)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(CONNECT_TIMEOUT_S)
    if thread.is_alive():
        return False
    return bool(holder) and not err


def _key_present(env: dict) -> bool:
    secrets = gsd_catalog.load_ai_kit_spec_module("local_secrets")
    if secrets is not None:
        return bool(secrets.secret_is_set(env, "JEV_API_KEY"))
    return bool(str(env.get("JEV_API_KEY", "")).strip())


def system_one_backend(env: dict, connect_fn) -> dict:
    """Reachability-only URL probe plus presence-only key check; never stores URL or key."""
    via: list[str] = []
    note = ""
    raw = str(env.get("JEV_API_URL", "")).strip()
    if raw:
        endpoint = _url_endpoint(raw)
        if endpoint is not None and _tcp_reachable(endpoint, connect_fn):
            via.append("url_reachable")
            note = URL_NOTE
    if _key_present(env):
        via.append("key_present")
    return {"detected": bool(via), "via": via, "note": note}
