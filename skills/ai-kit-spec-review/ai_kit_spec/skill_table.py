"""SPEC R1 (39 D-07, D-09, D-21): the closed skill and MCP server roles, the seed rows of
references/skill-roles.json and the [skills.roles] sorts. A seed row is an example with a source
label and no decision power: presence comes from the scan (scan lives beside it, 39-04), never
from a row.
"""

import json
import os
from collections.abc import Callable

from ai_kit_spec import config_io

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
