"""SPEC R1 (39 D-07, D-09, D-21): the closed skill and MCP server roles, the seed rows of
references/skill-roles.json and the [skills.roles] sorts. A seed row is an example with a source
label and no decision power: presence comes from the scan (scan lives beside it, 39-04), never
from a row.
"""

import json
import os
import re
import stat
from collections.abc import Callable

from ai_kit_spec import config_io, secret_shapes
from ai_kit_spec.detection import CBM_REGISTRATION_KEYS, _cbm_config_paths, _cbm_read_config

ROLES = (
    "review_lens",
    "edit_lens",
    "ui_lens",
    "code_index",
    "decision_helper",
    "host_control",
    "skill_judge",
    "unsorted",
)
KINDS = ("skill", "mcp")
BUILT_IN_HOSTS = ("claude", "codex", "opencode", "cursor", "copilot", "pi")
_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_PATH = os.path.join(_SKILL_DIR, "references", "skill-roles.json")


def load_seed(path: str | None = None) -> list[dict]:
    """The seed rows of skill-roles.json (SEED_PATH by default)."""
    with open(path or SEED_PATH, encoding="utf-8") as handle:
        doc = json.load(handle)
    rows = doc.get("rows") if isinstance(doc, dict) else None
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{path or SEED_PATH}: rows is not a list of objects")
    return rows


def _launch_problem(row: dict) -> str | None:
    if "launch" not in row:
        return None
    if row.get("kind") == "skill":
        return "launch on a skill row"
    launch = row["launch"] if isinstance(row["launch"], dict) else {}
    command, args, source = launch.get("command"), launch.get("args"), launch.get("source")
    good_command = isinstance(command, str) and bool(command)
    good_args = isinstance(args, list) and all(isinstance(arg, str) for arg in args)
    good_source = isinstance(source, str) and bool(source.strip())
    return (
        None if good_command and good_args and good_source
        else "launch needs command, args and source"
    )


def _row_problems(row: dict) -> list[str]:
    problems = []
    if not isinstance(row.get("name"), str) or not row["name"]:
        problems.append("name is not a non-empty string")
    if row.get("kind") not in KINDS:
        problems.append(f"kind {row.get('kind')!r} is not skill or mcp")
    if row.get("role") == "unsorted":
        problems.append("role unsorted is not a seed role")
    elif row.get("role") not in ROLES:
        problems.append(f"role {row.get('role')!r} is not in ROLES")
    if not isinstance(row.get("source"), str) or not row["source"].strip():
        problems.append("no source label")
    launch_problem = _launch_problem(row)
    if launch_problem is not None:
        problems.append(launch_problem)
    if "built_in" in row:
        if row.get("kind") != "skill":
            problems.append("built_in on a non-skill row")
        elif row["built_in"] not in BUILT_IN_HOSTS:
            problems.append(f"built_in {row['built_in']!r} is not a host")
    return problems


def seed_problems(rows: list, literal_hits: Callable[[str], list] | None = None) -> list[str]:
    """Every problem of the seed rows, as "row <i> (<name>): <problem>".

    literal_hits is the repo's hardcoding guard helper (tests inject scan_text);
    without it no literal check runs.
    """
    problems = []
    seen = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            problems.append(f"row {index}: not an object")
            continue
        label = f"row {index} ({row.get('name') or '?'})"
        problems.extend(f"{label}: {text}" for text in _row_problems(row))
        if isinstance(row.get("name"), str) and isinstance(row.get("kind"), str):
            key = (row["name"], row["kind"])
            if key in seen:
                problems.append(f"{label}: duplicate name and kind")
            else:
                seen.add(key)
        if literal_hits is not None:
            for hit in literal_hits(json.dumps(row, sort_keys=True)):
                problems.append(f"{label}: model or provider literal {hit[-1]}")
    return problems


def user_roles(cwd: str, env: dict) -> dict[str, str]:
    """Read confirmed sorts from [skills.roles], project over user per key.

    Invalid roles and malformed files raise ConfigError. Scan callers may catch it and
    show a note; sorter and confirm commands let it propagate.
    """
    for layer in config_io.cfg_load_layers(cwd, env):
        skills = layer.get("skills")
        roles = skills.get("roles") if isinstance(skills, dict) else skills
        if roles is not None and not isinstance(roles, dict):
            raise config_io.ConfigError("[skills.roles]", "must be a table")
    table = config_io.cfg_layered_table(cwd, env, "skills", "roles")
    stated = [role for role in ROLES if role != "unsorted"]
    for name, role in table.items():
        if role not in stated:
            raise config_io.ConfigError(
                "[skills.roles]", f"entry {name!r} needs a role from: {', '.join(stated)}"
            )
    return dict(table)


def table_inputs(
    cwd: str, env: dict, seed_path: str | None = None
) -> tuple[list[dict], dict[str, str], list[str]]:
    """Return seed rows, stated roles and notes; broken inputs become empty with a note.

    Config-time commands call load_seed and user_roles directly and fail loudly.
    """
    notes = []
    try:
        seed = load_seed(seed_path)
    except (OSError, ValueError) as error:
        seed = []
        notes.append(f"skill seed ignored: {error}")
    try:
        user = user_roles(cwd, env)
    except config_io.ConfigError as error:
        user = {}
        notes.append(f"skills.roles ignored: {error}")
    return seed, user, notes


def resolve_role(name: str, kind: str, seed: list, user: dict) -> tuple[str, str]:
    """(role, role_source): a user-stated sort, else the seed row of this name and kind,
    else ("unsorted", "none"). Names match exactly.
    """
    if name in user:
        return user[name], "user-stated"
    for row in seed:
        if (
            isinstance(row, dict)
            and row.get("name") == name
            and row.get("kind") == kind
            and row.get("role") in ROLES
            and row.get("role") != "unsorted"
        ):
            return row["role"], "seed"
    return "unsorted", "none"


# Scan (SPEC R1, D-08): presence is read from disk on every call; nothing is cached.
# Always fullmatch; the GSD config skill's addressable rule
# (the runner's own name rule is narrower).
SKILL_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")
# (host, config-dir variable, fallback under HOME, suffix). The sixth copy of the host-root list
# (D-08); codex and copilot loading these folders is unverified.
HOST_SKILL_ROOTS = (
    ("claude", "CLAUDE_CONFIG_DIR", ".claude", "skills"),
    ("codex", "CODEX_HOME", ".codex", "skills"),
    ("opencode", "XDG_CONFIG_HOME", ".config", "opencode/skills"),
    ("cursor", "CURSOR_CONFIG_DIR", ".cursor", "skills"),
    ("copilot", "COPILOT_HOME", ".copilot", "skills"),
    ("pi", "PI_CODING_AGENT_DIR", ".pi/agent", "skills"),
    ("agents", None, ".agents", "skills"),
)
_KIND_ORDER = {"global": 0, "plugin": 1}


def host_root(row: tuple, env) -> str | None:
    """Resolve an absolute host skill root without falling back to the current directory."""
    _host, variable, fallback, suffix = row
    base = (env.get(variable, "").strip() if variable else "") or os.path.join(
        env.get("HOME", ""), fallback
    )
    root = os.path.join(base, suffix)
    return root if os.path.isabs(root) else None


def root_rows(
    root: str, root_kind: str, seed: list, user: dict, plugin: str | None = None
) -> list[dict]:
    """One row per child with SKILL.md; a missing or unreadable root gives []."""
    if not root or not os.path.isdir(root):
        return []
    try:
        names = os.listdir(root)
    except OSError:
        return []
    rows = []
    for name in names:
        path = os.path.join(root, name)
        if not os.path.isfile(os.path.join(path, "SKILL.md")):
            continue
        addressable = bool(SKILL_NAME_RE.fullmatch(name)) and (
            plugin is None or bool(SKILL_NAME_RE.fullmatch(plugin))
        )
        role, role_source = (
            resolve_role(name, "skill", seed, user) if addressable else ("unsorted", "none")
        )
        rows.append({
            "name": name, "role": role, "role_source": role_source, "path": path,
            "root_kind": root_kind, "addressable": addressable,
        })
    return rows


def _row_key(row: dict) -> tuple:
    return (_KIND_ORDER.get(row["root_kind"], 9), os.path.dirname(row["path"]), row["name"])


def _host_entry(row: tuple, env, ctx: tuple) -> dict:
    seed, user, notes, plugin_skills, plugin_roots = ctx
    host = row[0]
    root = host_root(row, env)
    skills = root_rows(root, "global", seed, user) if root else []
    if host == "claude":
        skills.extend(plugin_skills)
    skills.sort(key=_row_key)
    roots = [os.path.realpath(root)] if root and os.path.isdir(root) else []
    if host == "claude":
        roots.extend(plugin_roots)
    names, note = mcp_names(host, env)
    mcp = names if isinstance(names, str) else [
        {"name": name, "role": resolve_role(name, "mcp", seed, user)[0]} for name in names
    ]
    return {"skills": skills, "roots": roots, "mcp": mcp, "mcp_note": note, "notes": list(notes)}


def scan(env, cwd) -> dict:
    """Per host: skills, real roots, MCP names or unknown, MCP note, and scan-wide notes.

    Read-only, no cache, never raises for a broken seed or roles config (SPEC R1).
    """
    seed, user, notes = table_inputs(cwd, env)
    claude_dir = env.get("CLAUDE_CONFIG_DIR", "").strip() or os.path.join(
        env.get("HOME", ""), ".claude"
    )
    plugin_skills, plugin_roots = (
        plugin_rows(claude_dir, cwd, seed, user) if os.path.isabs(claude_dir) else ([], [])
    )
    ctx = (seed, user, notes, plugin_skills, plugin_roots)
    return {row[0]: _host_entry(row, env, ctx) for row in HOST_SKILL_ROOTS}


def cmd_skill_table(args, deps) -> int:
    """Print the scan as JSON (read only)."""
    print(json.dumps(scan(deps.env_fn(), args.cwd or os.getcwd()), indent=2))
    return 0


def register_parsers(sub) -> None:
    """Register the read-only skill-table command."""
    parser = sub.add_parser(
        "skill-table",
        help="list the skills and MCP server names present per host with their roles (read only)",
    )
    parser.add_argument(
        "--cwd", default=None,
        help="project directory whose .aikit/config.toml roles apply; "
        "default: the current directory",
    )


COMMANDS = {"skill-table": cmd_skill_table}

DESCRIPTION_MAX = 300
DESCRIPTION_READ_MAX = 65536
_BLOCK_INDICATOR = re.compile(r"[>|](?:[-+]?[1-9]?|[1-9][-+])")


def _read_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError, RecursionError):
        return {}
    return raw if isinstance(raw, dict) else {}


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


def read_description(skill_dir: str) -> str:
    """The SKILL.md frontmatter description, cut at DESCRIPTION_MAX characters;
    "" when unreadable (SPEC R1, R2).
    """
    try:
        with open(os.path.join(skill_dir, "SKILL.md"), encoding="utf-8") as handle:
            return _parse_description(handle.read(DESCRIPTION_READ_MAX))
    except (OSError, ValueError, UnicodeDecodeError):
        return ""


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


def _install_path(records: list, project_dir: str) -> str | None:
    for record in records:
        if not isinstance(record, dict):
            continue
        if not _record_matches(record, project_dir):
            continue
        path = record.get("installPath")
        if isinstance(path, str) and path:
            return path
    return None


def plugin_rows(
    claude_dir: str, project_dir: str, seed: list, user: dict
) -> tuple[list[dict], list[str]]:
    """Enabled Claude plugin skills under <installPath>/skills.

    Uses installed_plugins.json plus layered enabledPlugins; per-key layering unverified.
    """
    manifest_path = os.path.join(claude_dir, "plugins", "installed_plugins.json")
    data = _read_json(manifest_path)
    plugins = data.get("plugins")
    if not isinstance(plugins, dict):
        return [], []
    enabled = _merged_enabled(claude_dir, project_dir)
    out: list[dict] = []
    roots: list[str] = []
    for plugin_id, records in plugins.items():
        if not isinstance(records, list):
            continue
        install_path = _install_path(records, project_dir)
        if install_path is None or not enabled.get(plugin_id):
            continue
        if not os.path.isdir(install_path):
            continue
        display = _plugin_display_name(install_path, plugin_id)
        skills_root = os.path.join(install_path, "skills")
        # shortcut: custom plugin.json skill paths and a root SKILL.md are not scanned
        if os.path.isdir(skills_root):
            roots.append(os.path.realpath(skills_root))
        out.extend(root_rows(skills_root, "plugin", seed, user, plugin=display))
    return out, roots


PI_MCP_NOTE = "pi has no MCP config key (its servers come from extension files); not read"
AGENTS_MCP_NOTE = "the shared agents root is a skills folder, not a host: no MCP config"
# Names reach prompt text (39-10): only plain names are shown; the rest are counted.
MCP_NAME_RE = re.compile(r"[A-Za-z0-9_.@-]{1,64}")
MCP_CONFIG_MAX = 1048576


def mcp_names(host: str, env) -> tuple:
    """Return sorted server names or unknown and a note, reading keys only.

    An unreadable, malformed, or non-table servers key makes the whole host unknown.
    """
    if host not in CBM_REGISTRATION_KEYS:
        return [], AGENTS_MCP_NOTE
    key = CBM_REGISTRATION_KEYS[host]
    if key is None:
        return "unknown", PI_MCP_NOTE
    names = set()
    for path in _cbm_config_paths(host, env):
        try:
            info = os.stat(path)
        except FileNotFoundError:
            continue
        except OSError:
            return "unknown", f"unreadable or malformed: {path}"
        if not stat.S_ISREG(info.st_mode) or info.st_size > MCP_CONFIG_MAX:
            return "unknown", f"not a regular file or over {MCP_CONFIG_MAX} bytes: {path}"
        data = _cbm_read_config(path)
        if isinstance(data, dict) and key not in data:
            continue
        servers = data.get(key) if isinstance(data, dict) else None
        if not isinstance(servers, dict):
            return "unknown", f"unreadable or malformed: {path}"
        names.update(name for name in servers if isinstance(name, str))
    shown = sorted(name for name in names if MCP_NAME_RE.fullmatch(name)
                   and secret_shapes.redact(name, "") == name)
    hidden = len(names) - len(shown)
    return shown, (
        f"{hidden} server name(s) not shown: outside [A-Za-z0-9_.@-] or secret-shaped"
        if hidden else ""
    )


def skill_roots(result: dict) -> list[str]:
    """The real paths of the scanned roots and of each skill directory found in them (SPEC R8).

    A skill directory linked into a host root (the installer's symlink shape) is a skill root
    itself; a SKILL.md linked out of a real in-root directory still resolves outside.
    """
    roots = {root for entry in result.values() for root in entry["roots"]}
    roots.update(os.path.realpath(row["path"]) for entry in result.values()
                 for row in entry.get("skills", []) if row.get("path"))
    return sorted(roots)
