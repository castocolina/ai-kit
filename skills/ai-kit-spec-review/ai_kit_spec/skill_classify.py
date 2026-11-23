"""SPEC R2, D-09: the optional sorter.

classify-skills (read only) asks jev, when present, one choice per unsorted skill
from its name and description only; confirm-skill-role writes one owner-confirmed
[skills.roles] entry. Configuration time only: never called by a review or an
execute run. cli.py registers both; this module never imports cli.
"""

import functools
import os
import subprocess
import sys
from typing import NamedTuple

from ai_kit_spec import config_io, jev_names, secret_shapes, skill_table, toml_splice

PROPOSABLE = tuple(role for role in skill_table.ROLES if role != "unsorted")
NONE_KEY = "none_of_these"
ROLE_QUESTION = (
    "Which role fits this agent skill best, judged only from its name and description? "
    "Pick none_of_these when no role fits."
)
ROLE_HINTS = {
    "review_lens": "gives read-only review advice on plans or code",
    "edit_lens": "changes files to improve them",
    "ui_lens": "reviews or designs user interfaces",
    "code_index": "indexes or searches code and documents",
    "decision_helper": "gives fast typed judgments or decisions",
    "host_control": "drives terminals, panes or other agents",
    "skill_judge": "scores or reviews agent skills",
}


class Proposal(NamedTuple):
    """An advisory role and confidence for a skill."""

    name: str
    role: str
    confidence: float


def unsorted_skills(result: dict) -> list:
    """(name, path, hosts) per addressable unsorted skill, first seen in scan order."""
    found = {}
    for host, entry in result.items():
        for row in entry["skills"]:
            name = row["name"]
            if (row["role"] != "unsorted" or not row["addressable"]
                    or secret_shapes.redact(name, "") != name):
                continue
            if name not in found:
                found[name] = (row["path"], [])
            if host not in found[name][1]:
                found[name][1].append(host)
    return [(name, path, hosts) for name, (path, hosts) in found.items()]


def not_addressable(result: dict) -> list:
    """(shown name, hosts, reason) per unsorted row listed but never offered."""
    found = {}
    for host, entry in result.items():
        for row in entry["skills"]:
            name = row["name"]
            if row["role"] != "unsorted":
                continue
            secret = secret_shapes.redact(name, "") != name
            if row["addressable"] and not secret:
                continue
            shown = secret_shapes.redact(name, "[redacted]")
            reason = "name_secret_shaped" if secret else "name_not_addressable"
            key = (shown, reason)
            if key not in found:
                found[key] = []
            if host not in found[key]:
                found[key].append(host)
    return [(shown, hosts, reason) for (shown, reason), hosts in found.items()]


def _inside_roots(real: str, roots: list) -> bool:
    try:
        return any(os.path.commonpath([real, root]) == root for root in roots)
    except ValueError:
        return False


def role_item(index: int, name: str, path: str, roots: list) -> dict:
    """Build an item containing only the skill name and safe description."""
    real = os.path.realpath(os.path.join(path, "SKILL.md"))
    raw = skill_table.read_description(path) if _inside_roots(real, roots) else ""
    raw = secret_shapes.redact(raw, "[redacted]")
    text = secret_shapes.redact(
        "".join(ch for ch in raw if ch.isprintable())[:skill_table.DESCRIPTION_MAX], "[redacted]"
    )
    context = f"Skill name: {name}." + (f" Description: {text}" if text else "")
    return {
        "id": f"s{index}", "type": "choice", "instructions": ROLE_QUESTION,
        "context": context,
        "criteria": {**{role: ROLE_HINTS[role] for role in PROPOSABLE},
                     NONE_KEY: "none of these roles fits this skill"},
    }


def _proposals(items: list, pending: list, answers: dict) -> list:
    proposals = []
    for item, (name, _, _) in zip(items, pending, strict=True):
        choice, top, reason = answers.get(item["id"], (None, None, "no answer"))
        if reason == "" and choice in PROPOSABLE and isinstance(top, (int, float)):
            proposals.append(Proposal(name, choice, float(top)))
    return proposals


def classify(env, cwd, run=subprocess.run, own_root=None) -> dict:
    """Return unsorted, not_offered, jev status and advisory proposals; writes nothing."""
    skill_table.user_roles(cwd, env)
    result = skill_table.scan(env, cwd)
    pending = unsorted_skills(result)
    out = {"unsorted": [(name, hosts) for name, _, hosts in pending],
           "not_offered": not_addressable(result), "jev": "not needed", "proposals": []}
    if not pending:
        return out
    entry = jev_names.find_jev(env, own_root)
    if entry is None:
        out["jev"] = "absent"
        return out
    roots = skill_table.skill_roots(result)
    items = [role_item(index, name, path, roots)
             for index, (name, path, _) in enumerate(pending)]
    answers = jev_names.ask_items(entry, items, env, functools.partial(run, cwd=cwd), strict=True)
    out["jev"] = "asked"
    out["proposals"] = _proposals(items, pending, answers)
    return out


def cmd_classify_skills(args, deps) -> int:
    """Print the unsorted skills and the advisory proposals (read only)."""
    result = classify(deps.env_fn(), args.cwd or os.getcwd(), deps.run_fn)
    for name, hosts in result["unsorted"]:
        print(f"unsorted {name} hosts={','.join(hosts)}")
    for name, hosts, reason in result["not_offered"]:
        print(f"not offered {name!a} hosts={','.join(hosts)} reason={reason}")
    if not result["unsorted"] and not result["not_offered"]:
        print("no unsorted skills")
    if result["jev"] == "absent":
        print("jev absent: nothing proposed")
    for proposal in result["proposals"]:
        print(f"proposal {proposal.name} role={proposal.role} "
              f"confidence={proposal.confidence:.2f} advisory")
    return 0


def confirm_role(path: str, name: str, role: str, project_env: dict | None = None) -> None:
    """Atomically write one owner-confirmed role, preserving other bytes; reject broken files."""
    folder = os.path.dirname(os.path.abspath(path))
    # The read-splice-publish holds the folder lock shared with render-toml.
    with config_io.cfg_folder_lock(path):
        if project_env is not None:
            if os.path.islink(folder):
                raise config_io.ConfigError(
                    folder, "is a link; the project config is not written through a linked "
                            ".aikit folder"
                )
            config_io.cfg_confine_project_file(path, project_env)
        existing = ""
        if os.path.exists(path):
            raw = config_io.cfg_read_bytes(path)
            config_io.cfg_parse_toml_bytes(raw, path)
            existing = raw.decode("utf-8")
        text = toml_splice.set_table(existing, ("skills", "roles"), {name: role})
        toml_splice.publish(path, text)


def cmd_confirm_skill_role(args, deps) -> int:
    """Write the one sort the owner confirmed, labeled user-stated on read."""
    if (not (skill_table.SKILL_NAME_RE.fullmatch(args.name)
             or skill_table.MCP_NAME_RE.fullmatch(args.name))
            or secret_shapes.redact(args.name, "") != args.name):
        print(f"confirm-skill-role: invalid skill name {args.name!r}", file=sys.stderr)
        return 2
    env = deps.env_fn()
    path = (config_io.cfg_global_path(env) if args.use_global
            else config_io.cfg_local_path(args.cwd or os.getcwd()))
    try:
        confirm_role(path, args.name, args.role, None if args.use_global else env)
    except (toml_splice.SpliceError, OSError) as exc:
        print(f"confirm-skill-role: {exc}", file=sys.stderr)
        return 1
    print(f"confirmed {args.name} role={args.role} user-stated in {path}")
    return 0


def register_parsers(sub) -> None:
    """Register skill classification and confirmation commands."""
    parser = sub.add_parser(
        "classify-skills",
        help="list unsorted skills and ask jev, when present, for an advisory role (read only)",
    )
    parser.add_argument(
        "--cwd", default=None,
        help="project directory whose .aikit/config.toml roles apply; "
        "default: the current directory",
    )
    confirm = sub.add_parser(
        "confirm-skill-role",
        help="write one owner-confirmed skill role into [skills.roles] "
             "(project layer unless --global)",
    )
    confirm.add_argument("--name", required=True)
    confirm.add_argument("--role", required=True, choices=PROPOSABLE)
    confirm.add_argument("--global", dest="use_global", action="store_true",
                         help="write the user layer instead of ./.aikit/config.toml")
    confirm.add_argument("--cwd", default=None)


COMMANDS = {"classify-skills": cmd_classify_skills, "confirm-skill-role": cmd_confirm_skill_role}
