"""36 SPEC R1, D-02: config-status says whether lanes are configured (active, pending or none)
and which two files it checked. Read only: nothing is migrated, trusted or written; each lane's
capability line comes from the runner's --print-argv dry run (39 R11), never a spawn of the lane.
cli.py registers it; this module never imports cli.
"""

import os

from ai_kit_spec import capability_block, config_io, config_migrate, trust

_ROLES = ("review", "execute")
_PENDING = frozenset({"untrusted", "pending-migration"})


def _has_lane(lanes: dict, roles: tuple) -> bool:
    return any(isinstance(entries, list) and any(
        isinstance(entry, dict) and isinstance(entry.get("key"), str) for entry in entries
    ) for entries in (lanes.get(role) for role in roles))


def _read_lanes(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    doc = config_io.cfg_parse_toml_bytes(config_io.cfg_read_bytes(path), path)
    return config_io.cfg_lanes_table(doc, path) if "lanes" in doc else None


def _old_roster_status(path: str) -> str | None:
    if config_migrate.pending(path) is None:
        return None
    try:
        config_migrate.read_legacy(path)
    except config_migrate.LegacyRosterError as exc:
        raise config_io.ConfigError(exc.path, exc.message) from exc
    return "pending-migration"


def _lane_less_status(path: str, lanes: dict | None, legacy: str | None) -> str:
    if lanes is not None:
        return "empty"
    return legacy or ("missing" if not os.path.exists(path) else "empty")


def _project_status(path: str, env: dict, roles: tuple) -> tuple[str, dict]:
    legacy = _old_roster_status(path)
    lanes = _read_lanes(path)
    if lanes is not None and _has_lane(lanes, roles):
        canonical = config_io.cfg_project_trust_bytes(lanes, env)
        trusted = canonical is None or trust.is_trusted(
            config_io.cfg_trust_store_dir(env), os.path.realpath(path), canonical
        )
        return ("lanes" if trusted else "untrusted", lanes)
    return _lane_less_status(path, lanes, legacy), lanes or {}


def _user_status(path: str, roles: tuple) -> str:
    legacy = _old_roster_status(path)
    lanes = _read_lanes(path)
    if lanes is not None and _has_lane(lanes, roles):
        return "lanes"
    return _lane_less_status(path, lanes, legacy)


def config_status(
    cwd: str, env: dict, role: str | None = None
) -> tuple[str, list[tuple[str, str, str]]]:
    """Report active, pending or none, optionally filtering lanes by role."""
    roles = (role,) if role else _ROLES
    user_path = config_io.cfg_global_path(env)
    project_path = os.path.abspath(config_io.cfg_local_path(cwd))
    project, lanes = _project_status(project_path, env, roles)
    user = (
        "skipped-local-only" if lanes.get("strategy") == "local-only"
        else _user_status(user_path, roles)
    )
    statuses = {project, user}
    state = "pending" if statuses & _PENDING else "active" if "lanes" in statuses else "none"
    return state, [("project", project_path, project), ("user", user_path, user)]


def capability_lines(cwd: str, env: dict, role: str | None) -> list[str]:
    """Return previews for the effective lanes in configuration order."""
    resolved = config_io.cfg_resolve(cwd, env, warn_fn=lambda _line: None, migrate=False)
    lines = []
    for each_role in ((role,) if role else _ROLES):
        for entry in resolved.get(each_role) or []:
            if isinstance(entry, dict):
                rt, model, text = capability_block.lane_summary(
                    entry, each_role, cwd, env, capability_block.DEFAULT_SEAMS)
                lines.append(f"capability {rt}/{model} {each_role}: {text}")
    return lines


def cmd_config_status(args, deps) -> int:
    """Print the state, checked paths and effective lane previews."""
    env = deps.env_fn()
    state, checked = config_status(args.cwd, env, args.role)
    lines = capability_lines(args.cwd, env, args.role) if state == "active" else []
    print(state)
    for layer, path, status in checked:
        print(f"checked {layer} {path} {status}")
    for line in lines:
        print(line)
    return 0


def register_parsers(sub) -> None:
    """Register the read-only status command."""
    parser = sub.add_parser(
        "config-status",
        help="report whether lanes are configured: active, pending or none (read only)",
    )
    parser.add_argument("--cwd", required=True)
    parser.add_argument(
        "--role", choices=["review", "execute"], default=None,
        help="count only lanes of this role (default: either role)",
    )


COMMANDS = {"config-status": cmd_config_status}
