#!/usr/bin/env python3
"""Host facts for the goal-prompt skill: survival matrix, versions, primitive labels, readiness.

stdlib only. Every effect runs through an injected `HostSeams` (run, which, environ), so unit
tests fake each subprocess. Probe output is parsed as data; a failed probe degrades to a labelled
"unverified", never to a guess. Results carry names, booleans and fixed reasons, never a path.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from typing import NamedTuple

HOST_BINARY = {
    "claude": "claude",
    "codex": "codex",
    "pi": "pi",
    "opencode": "opencode",
    "cursor": "agent",
}
WAKE_CLI = "ai-kit-session-wake/ai-kit-session-wake.py"
SPEC_CLI = "ai-kit-spec-review/ai-kit-spec.py"
JEV_ENTRY_REL = os.path.join("jev-fast-decision", "scripts", "jev_review.py")
PROBE_TIMEOUT = 20
# Three levels up from scripts/gp_host.py is the skills directory. abspath, not realpath: a
# symlinked skill still finds its siblings beside it.
SKILLS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Lookup copy of jev-fast-decision's SKILLS_ROOTS (scripts/jev_ladder.py), same order and values.
SKILLS_ROOTS = (
    ("CLAUDE_CONFIG_DIR", ".claude", "skills"),
    (None, ".agents", "skills"),
    ("XDG_CONFIG_HOME", ".config", "opencode/skills"),
    ("CURSOR_CONFIG_DIR", ".cursor", "skills"),
    ("PI_CODING_AGENT_DIR", ".pi/agent", "skills"),
)
VERSION_RE = re.compile(r"(?<![\d.])(\d+\.\d+\.\d+)(?![\d.])")
HELP_KEYWORD = re.compile(r"\b(goal|loop|schedule|cron)\b", re.IGNORECASE)


# The repo's own runner script runs in a probe child: variables whose name looks like a credential
# are dropped. shortcut: name-based, so an oddly named secret still passes; an allowlist needs the
# real gsd-tools environment verified first.
SECRET_NAME_RE = re.compile(r"KEY|TOKEN|SECRET|PASSW|CREDENTIAL|AUTH|COOKIE|SESSION", re.IGNORECASE)


class HostSeams(NamedTuple):
    """Injected side effects. `run(argv, timeout, cwd)` returns (rc, stdout)."""

    run: Callable[[list[str], int, str | None], tuple[int, str]]
    which: Callable[[str], str | None]
    environ: Mapping[str, str]


def _run(argv: list[str], timeout: int, cwd: str | None) -> tuple[int, str]:
    """List argv only, stdin closed; a missing program is 127 and a timeout is 124."""
    try:
        done = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
            cwd=cwd,
            env={k: v for k, v in os.environ.items() if not SECRET_NAME_RE.search(k)},
        )
    except subprocess.TimeoutExpired:
        return 124, ""
    except OSError:
        return 127, ""
    return done.returncode, done.stdout


def real_seams() -> HostSeams:
    """The production side effects."""
    return HostSeams(run=_run, which=shutil.which, environ=os.environ)


def sibling_cli(name: str, override: str | None = None) -> str:
    """A sibling skill's CLI path; `name` is relative to the skills directory."""
    return override if override else os.path.join(SKILLS_DIR, name)


def _parse_matrix(out: str) -> tuple[list | None, str]:
    """The rows of a schema-1 matrix document, or (None, short fixed reason)."""
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None, "not json"
    if not isinstance(data, dict):
        return None, "no rows"
    if data.get("schema_version") != 1:
        return None, f"schema {data.get('schema_version')}"
    rows = data.get("rows")
    if not isinstance(rows, list):
        return None, "no rows"
    return rows, "session-wake"


def read_matrix(seams: HostSeams, wake_cli: str | None = None) -> tuple[list | None, str]:
    """(rows, "session-wake") from `matrix --json`, or (None, short fixed reason)."""
    cli = sibling_cli(WAKE_CLI, wake_cli)
    if not os.path.isfile(cli):
        return None, "cli missing"
    rc, out = seams.run([sys.executable, cli, "matrix", "--json"], PROBE_TIMEOUT, None)
    if rc != 0:
        return None, f"exit {rc}"
    return _parse_matrix(out)


def host_version(seams: HostSeams, host: str) -> str | None:
    """The `x.y.z` the host binary prints for `--version`, or None when it cannot be read."""
    binary = HOST_BINARY.get(host)
    if binary is None or seams.which(binary) is None:
        return None
    rc, out = seams.run([binary, "--version"], PROBE_TIMEOUT, None)
    if rc != 0:
        return None
    match = VERSION_RE.search(out)
    return match.group(1) if match else None


def _version_parts(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version))


def version_ge(version: str | None, floor: str | None) -> bool:
    """True when `version` meets `floor`; an unknown version never meets a floor."""
    if version is None:
        return False
    if floor is None:
        return True
    return _version_parts(version) >= _version_parts(floor)


def current_host(seams: HostSeams, spec_cli: str | None = None) -> str | None:
    """The host hosting this process, from `detect-current-runtime`, or None."""
    cli = sibling_cli(SPEC_CLI, spec_cli)
    if not os.path.isfile(cli):
        return None
    rc, out = seams.run([sys.executable, cli, "detect-current-runtime"], PROBE_TIMEOUT, None)
    if rc != 0:
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None
    host = data.get("host") if isinstance(data, dict) else None
    return host if isinstance(host, str) and host else None


def help_mentions(seams: HostSeams, host: str) -> bool | None:
    """True/False for a goal, loop, schedule or cron keyword in `--help`; None when unknown."""
    binary = HOST_BINARY.get(host)
    if binary is None or seams.which(binary) is None:
        return None
    rc, out = seams.run([binary, "--help"], PROBE_TIMEOUT, None)
    if rc != 0 or not out.strip():
        return None
    return HELP_KEYWORD.search(out) is not None


# ─── primitives: two labels per row (D-07) ───────────────────────────────────

OFFICIAL_DOCS_CLAUDE = frozenset(
    {
        "/goal",
        "/loop",
        "CronCreate one-shot",
        "CronCreate recurring",
        "ScheduleWakeup",
        "cloud routine",
    }
)
KNOWN_TOOL_NAMES = frozenset(
    {
        "CronCreate",
        "CronList",
        "CronDelete",
        "ScheduleWakeup",
        "Monitor",
        "RemoteTrigger",
        "PushNotification",
    }
)
NONE_NOTE = "no native goal or loop primitive found in --help"
EXTRA_ROWS = [
    {
        "host": "codex",
        "primitive": "/goal",
        "kind": "goal",
        "surface": "slash-command",
        "survives_stall": False,
        "survives_process_death": False,
        "survives_reboot": False,
        "rank": 0,
        "source": "unverified",
        "version_floor": None,
        "usage_source": "binary strings",
        "evidence": (
            "usage /goal [<objective>|clear|edit|pause|resume] from codex binary strings; "
            "unverified"
        ),
    },
]


class Seen(NamedTuple):
    """What this session could see: agent-reported tool names and a `--help` keyword probe."""

    tools: frozenset[str]
    help_seen: bool | None


def _tool_name(row: dict) -> str:
    return row["primitive"].split()[0]


def _none_row(host: str, help_seen: bool | None) -> dict:
    """The row that says a host has no native primitive, labelled by how the probe went."""
    if help_seen is False:
        evidence = NONE_NOTE
    elif help_seen:
        evidence = "help mentions a goal, loop, schedule or cron keyword; no matrix row; unverified"
    else:
        evidence = "no matrix row and no --help probe; unverified"
    return {
        "host": host,
        "primitive": "none",
        "kind": "none",
        "surface": "cli",
        "survives_stall": False,
        "survives_process_death": False,
        "survives_reboot": False,
        "rank": 0,
        "source": "help",
        "version_floor": None,
        "usage_source": "unverified" if help_seen is None else "live",
        "evidence": evidence,
    }


def _availability(row: dict, host_match: bool, seen: Seen, version: str | None) -> str:
    if not host_match:
        return "unverified"
    if row["kind"] == "none":
        return "absent" if seen.help_seen is False else "unverified"
    if row["surface"] == "tool":
        return "available" if _tool_name(row) in seen.tools else "not seen"
    if row.get("version_floor") is None:
        return "unverified"
    return "available" if version_ge(version, row["version_floor"]) else "unverified"


def _usage_source(row: dict) -> str:
    if row.get("usage_source"):
        return row["usage_source"]
    if row["host"] == "claude" and row["primitive"] in OFFICIAL_DOCS_CLAUDE:
        return "official docs"
    return "live" if row.get("source") == "verified" else "unverified"


def _primitive(row: dict, host_match: bool, seen: Seen, version: str | None) -> dict:
    return {
        "host": row["host"],
        "primitive": row["primitive"],
        "kind": row["kind"],
        "surface": row["surface"],
        "availability": _availability(row, host_match, seen, version),
        "usage_source": _usage_source(row),
        "survives_stall": bool(row["survives_stall"]),
        "survives_process_death": bool(row["survives_process_death"]),
        "survives_reboot": bool(row["survives_reboot"]),
        "rank": row["rank"],
        "note": row["evidence"],
    }


def build_primitives(
    rows: list | None, *, target: str, current: str | None, version: str | None, seen: Seen
) -> list[dict]:
    """The target host's primitive table; every row carries availability and usage_source."""
    table = [r for r in (rows or []) if r.get("host") == target]
    table += [r for r in EXTRA_ROWS if r["host"] == target]
    kinds = {r["kind"] for r in table}
    if not kinds & {"goal", "loop", "schedule", "wake"}:
        table.append(_none_row(target, seen.help_seen))
    host_match = target == current
    return [_primitive(r, host_match, seen, version) for r in table]


def degraded_primitives(reason: str, target: str) -> list[dict]:
    """The table when the matrix cannot be read: every row unverified, with the reason kept."""
    prims = build_primitives(
        None, target=target, current=None, version=None, seen=Seen(frozenset(), None)
    )
    for prim in prims:
        prim["availability"] = "unverified"
        prim["note"] = f"matrix missing: {reason}. {prim['note']}"
    return prims


def unrecognized_tools(names: list[str], rows: list | None) -> list[str]:
    """Agent-reported tool names that match neither the known set nor a matrix tool row."""
    known = set(KNOWN_TOOL_NAMES)
    known |= {_tool_name(r) for r in (rows or []) if r.get("surface") == "tool"}
    unknown: list[str] = []
    for name in names:
        if name not in known and name not in unknown:
            unknown.append(name)
    return unknown


# ─── cross-AI readiness (D-16) and jev usability (D-21) ──────────────────────

AI_KIT_RUNNER = "cross-ai.mjs"
RUNNER_LAUNCHERS = ("node", "nodejs")
CLI_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _load_config(repo: str) -> dict:
    """The repo's .planning/config.json as a dict; a missing or invalid file is no config."""
    path = os.path.join(repo, ".planning", "config.json")
    if os.path.islink(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.loads(handle.read(1 << 20))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _section(parent: dict, key: str) -> dict:
    value = parent.get(key)
    return value if isinstance(value, dict) else {}


def _runner_problems(seams: HostSeams, repo: str, workflow: dict) -> tuple[list[str], list[str]]:
    """(problems, argv tokens) for the configured runner; tokens are [] when it cannot run."""
    problems: list[str] = []
    if workflow.get("cross_ai_execution") is not True:
        problems.append("cross_ai_execution off")
    command = workflow.get("cross_ai_command")
    if not isinstance(command, str) or not command.strip():
        return [*problems, "no cross_ai_command"], []
    try:
        tokens = shlex.split(command)
    except ValueError:
        return [*problems, "cross_ai_command unparsable"], []
    if not tokens or seams.which(tokens[0]) is None:
        problems.append("executable missing")
    if any("/" in token and not os.path.exists(os.path.join(repo, token)) for token in tokens[1:]):
        problems.append("script missing")
    return problems, tokens


def _listing(seams: HostSeams, repo: str, tokens: list[str]) -> tuple[bool | None, list[str]]:
    """(cli_listed, names) from `--print-argv`; only the exit code and CLI names are kept."""
    # Only `node <path>/cross-ai.mjs` is probed: any other leading token would run repo-chosen code.
    shaped = len(tokens) == 2 and tokens[0] in RUNNER_LAUNCHERS
    if not shaped or os.path.basename(tokens[1]) != AI_KIT_RUNNER:
        return None, []
    root = os.path.realpath(repo)
    script = os.path.realpath(os.path.join(repo, tokens[1]))
    if os.path.commonpath([root, script]) != root:  # a link or absolute path out of the repo
        return None, []
    rc, out = seams.run([*tokens, "--print-argv"], PROBE_TIMEOUT, repo)
    if rc != 0:
        return False, []
    names: list[str] = []
    for line in out.splitlines():
        fields = line.split("\t")
        is_cli_line = len(fields) == 3 and fields[2].startswith("[")
        if is_cli_line and CLI_NAME_RE.match(fields[0]) and fields[0] not in names:
            names.append(fields[0])
    return bool(names), names


def _reviewer_clis(config: dict) -> list[str]:
    """Each default reviewer's CLI: its instance's `cli` when set, else the reviewer id."""
    review = _section(config, "review")
    instances = _section(review, "reviewer_instances")
    ids = review.get("default_reviewers")
    clis: list[str] = []
    for reviewer in ids if isinstance(ids, list) else []:
        if not isinstance(reviewer, str):
            continue
        cli = _section(instances, reviewer).get("cli")
        clis.append(cli if isinstance(cli, str) and cli else reviewer)
    return clis


def _installed(seams: HostSeams, spec_cli: str | None) -> dict[str, bool] | None:
    """Each CLI `detect-runtimes` lists, as installed or not; None when the probe fails."""
    cli = sibling_cli(SPEC_CLI, spec_cli)
    if not os.path.isfile(cli):
        return None
    rc, out = seams.run([sys.executable, cli, "detect-runtimes"], PROBE_TIMEOUT, None)
    if rc != 0:
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None
    clis = data.get("clis") if isinstance(data, dict) else None
    if not isinstance(clis, dict):
        return None
    return {
        name: isinstance(info, dict) and info.get("installed") is True
        for name, info in clis.items()
    }


def _reviewer_problems(seams: HostSeams, config: dict, spec_cli: str | None) -> list[str]:
    problems: list[str] = []
    if _section(config, "workflow").get("plan_review_convergence") is not True:
        problems.append("plan_review_convergence off")
    clis = _reviewer_clis(config)
    if not clis:
        problems.append("no default reviewers")
    installed = _installed(seams, spec_cli)
    if installed is None:
        return [*problems, "detect-runtimes failed"]
    return problems + [
        f"reviewer CLI not installed: {cli}" for cli in clis if not installed.get(cli)
    ]


def _label(cli_listed: bool | None) -> str:
    if cli_listed is True:
        return "installed, not quota- or auth-verified"
    if cli_listed is False:
        return "no external CLI listed"
    return "usability unverified"


def cross_ai_readiness(
    seams: HostSeams, repo: str, *, native: bool, spec_cli: str | None = None
) -> dict:
    """D-16: the runner, a listed external CLI and the reviewers, proven without a model call."""
    config = _load_config(repo)
    runner_problems, tokens = _runner_problems(seams, repo, _section(config, "workflow"))
    runner_ok = not runner_problems
    cli_listed, clis = _listing(seams, repo, tokens if runner_ok else [])
    reviewer_problems = _reviewer_problems(seams, config, spec_cli)
    problems = runner_problems + reviewer_problems
    if cli_listed is False:
        problems.append("no external CLI listed")
    reviewers_ok = not reviewer_problems
    result = {
        "runner_ok": runner_ok,
        "cli_listed": cli_listed,
        "reviewers_ok": reviewers_ok,
        "clis": clis,
        "label": _label(cli_listed),
        "problems": problems,
        "ready_for_cross_ai": runner_ok and cli_listed is True and reviewers_ok and not native,
    }
    if native:
        result["native"] = True
    return result


def skills_roots(env: Mapping[str, str], own_root: str | None) -> list[str]:
    """Skills dirs to search in lookup order: `own_root` first when given, then SKILLS_ROOTS."""
    home = env.get("HOME", "~")
    roots = [own_root] if own_root else []
    for variable, fallback, suffix in SKILLS_ROOTS:
        base = (env.get(variable, "").strip() if variable else "") or os.path.join(home, fallback)
        roots.append(os.path.join(base, suffix))
    return [os.path.expanduser(root) for root in roots]


def find_jev(
    env: Mapping[str, str], own_root: str | None = SKILLS_DIR, override: str | None = None
) -> str | None:
    """The override when it names a file, else the first installed jev entry point."""
    if override and os.path.isfile(override):
        return override
    for root in skills_roots(env, own_root):
        path = os.path.join(root, JEV_ENTRY_REL)
        if os.path.isfile(path):
            return path
    return None


def jev_status(
    seams: HostSeams,
    jev_client: str | None = None,
    env: Mapping[str, str] | None = None,
    own_root: str | None = SKILLS_DIR,
) -> dict:
    """Whether jev-fast-decision's `detect` shows a usable backend; only detect is run."""
    entry = find_jev(os.environ if env is None else env, own_root, jev_client)
    if entry is None:
        return {"usable": False, "reason": "jev-fast-decision not installed"}
    rc, out = seams.run([sys.executable, entry, "detect"], PROBE_TIMEOUT, None)
    # Exit 2 is argparse's unknown-subcommand exit from an old client; its message is on stderr,
    # which _run never returns, so the code alone identifies it. The new detect never exits 2.
    if rc == 2:
        return {"usable": False, "reason": "jev-fast-decision too old: re-run the ai-kit installer"}
    if rc != 0:
        return {"usable": False, "reason": "detect failed"}
    return _jev_reading(out)


def _jev_reading(out: str) -> dict:
    """The usable flag and a fixed reason from jev's detect JSON; no backend detail survives."""
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"usable": False, "reason": "detect output not json"}
    backends = data.get("backends") if isinstance(data, dict) else None
    entries = [
        entry
        for entry in (backends.values() if isinstance(backends, dict) else [])
        if isinstance(entry, dict) and entry.get("usable") is True
    ]
    if any(entry.get("remote") is False for entry in entries):
        return {"usable": True, "reason": "local backend usable"}
    if any(entry.get("remote") is True for entry in entries):
        return {"usable": True, "reason": "consented remote backend"}
    return {"usable": False, "reason": "no usable backend"}
