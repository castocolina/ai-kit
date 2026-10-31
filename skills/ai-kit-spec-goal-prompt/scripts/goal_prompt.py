#!/usr/bin/env python3
"""CLI for the goal-prompt skill (GPS-01..04; SPEC R1, R2; D-04, D-05).

`detect` reads a project and prints the contract object (27-PATTERNS.md, schema 1) on stdout.
`render` writes one goal file from a detect result and an answers file, then prints its contract.
Neither subcommand prompts. stdout is JSON; bad input prints a JSON error on stderr and exits 2.
Sibling skills are reached only through their CLIs (D-03); GSD only through the three read-only
`query` calls of `--gsd-cmd`, run as list argv with no shell. stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any, NamedTuple, NoReturn

import gp_host
import gp_matrix
import gp_render
import gp_scope
from gp_common import GuardError, is_machine_path, phase_key
from gp_e2e import detect_e2e
from gp_host import HostSeams
from gp_matrix import MatrixInputs
from gp_render import RenderContext

__all__ = ["CliSeams", "UsageError", "build_detect", "build_parser", "main", "parse_work_set",
           "real_seams", "run_render"]

SCHEMA_VERSION = 1
GSD_TIMEOUT = 60
SIBLING_SKILLS = (
    "ai-kit-cross-ai",
    "ai-kit-session-wake",
    "ai-kit-gsd-spec-discuss",
    "ai-kit-spec-execute-superpowers",
)
WORK_KINDS = ("phases", "plans", "free")
STRATEGIES = ("goal", "loop", "autonomous")
AUTONOMOUS_DROPPED = "/gsd-autonomous needs a GSD phases work set on this scope"
SKILL_NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")


class UsageError(ValueError):
    """Bad CLI input. The message names the flag or field and never echoes the value."""


class CliSeams(NamedTuple):
    """Injected side effects: host seams, the date, the home to refuse, the secrets to scan for,
    and the directory the sibling skill CLIs live in."""

    host: HostSeams
    today: str
    home: str
    secrets: tuple[str, ...]
    skills_dir: str


class Captures(NamedTuple):
    """What the GSD captures returned: the roadmap, the identity, the phase-op documents and the
    names of captures still missing (`identity`, `phase_op`)."""

    roadmap: Any
    identity: Any
    phase_ops: dict[str, Any]
    needs: tuple[str, ...]


NO_CAPTURES = Captures(None, None, {}, ())


def real_seams() -> CliSeams:
    """Production seams. The generator reads no credentials, so `secrets` is empty; the guard
    still scans for key shapes."""
    return CliSeams(
        host=gp_host.real_seams(),
        today=date.today().isoformat(),
        home=os.path.expanduser("~"),
        secrets=(),
        skills_dir=gp_host.SKILLS_DIR,
    )


class _Parser(argparse.ArgumentParser):
    """Argparse usage errors become UsageError, so a bad flag also prints a JSON error."""

    def error(self, message: str) -> NoReturn:
        raise UsageError(message)


EXIT_CODES_EPILOG = (
    "Exit codes: 0 ok; 2 bad input or a guard failure (a JSON error is printed on stderr). "
    "Output is JSON on stdout. The tool never prompts."
)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="goal_prompt.py", description="Goal-prompt generator: detect, render.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=EXIT_CODES_EPILOG,
    )
    commands = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    detect = commands.add_parser("detect", help="print the detect contract as JSON")
    detect.add_argument("--repo", default=".",
                        help="repository root to read (default: current directory)")
    detect.add_argument("--target-host",
                        help="host whose primitives are judged; any other host is unverified")
    detect.add_argument("--tools", default="",
                        help="comma-separated tool names seen on this machine (default: none)")
    detect.add_argument("--roadmap",
                        help="captured gsd-tools roadmap.analyze JSON file (default: none)")
    detect.add_argument("--identity",
                        help="captured runtime-identity JSON file (default: none)")
    detect.add_argument("--phase-op",
                        help="directory of captured init.phase-op files named NUMBER.json")
    detect.add_argument("--work-set",
                        help="KIND:VALUE, e.g. phases:16-18, plans:a.md,b.md or free:TEXT")
    detect.add_argument("--gsd-cmd",
                        help="read-only gsd-tools command, run as argv without a shell")
    detect.add_argument("--wake-cli", help="path of the ai-kit-session-wake CLI to probe")
    detect.add_argument("--spec-cli", help="path of the ai-kit-spec-review CLI to probe")
    detect.add_argument("--decide-cli", help="path of the decide CLI (jev, advisory only)")
    render = commands.add_parser("render", help="write one goal file, print its contract")
    render.add_argument("--repo", default=".",
                        help="repository root to write into (default: current directory)")
    render.add_argument("--detect", required=True,
                        help="JSON file written by `detect` (schema 1); required")
    render.add_argument("--answers", required=True,
                        help="JSON file with the work set, host and strategy answers; required")
    render.add_argument("--out-dir",
                        help="repo-relative directory when answers give no output_dir "
                             "(default: .planning/goals, docs/superpowers/goals or tmp)")
    return parser


# ─── small readers ───────────────────────────────────────────────────────────


def _read_json(path: str, flag: str) -> Any:
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise UsageError(f"{flag} file is missing or does not hold JSON") from exc


def _sibling(seams: CliSeams, override: str | None, name: str) -> str:
    return override or os.path.join(seams.skills_dir, name)


def _is_number(number: str) -> bool:
    try:
        phase_key(number)
    except ValueError:
        return False
    return True


def _checked(number: str) -> str:
    if not _is_number(number):
        raise UsageError("--work-set holds a phase number that is not a dotted integer")
    return number


def _names(value: str, noun: str = "plan files") -> list[str]:
    names = [part.strip() for part in value.split(",") if part.strip()]
    if not names:
        raise UsageError(f"--work-set names no {noun}")
    return names


def _tool_names(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def _roadmap_numbers(roadmap: Any) -> list[str] | None:
    """The valid phase numbers of a roadmap capture; None when there is no roadmap."""
    if roadmap is None:
        return None
    phases = roadmap.get("phases") if isinstance(roadmap, dict) else None
    if not isinstance(phases, list):
        return []
    numbers = [str(p.get("number", "")) for p in phases if isinstance(p, dict)]
    return [number for number in numbers if _is_number(number)]


# ─── --work-set ──────────────────────────────────────────────────────────────


def _phase_range(value: str, roadmap_numbers: Sequence[str] | None) -> list[str]:
    parts = value.split("-")
    if len(parts) != 2:
        raise UsageError("a phase range is FIRST-LAST, for example 16-17")
    low, high = (phase_key(_checked(part.strip())) for part in parts)
    if roadmap_numbers is None:
        raise UsageError("a phase range needs the roadmap: pass --roadmap or --gsd-cmd")
    numbers = [number for number in roadmap_numbers if low <= phase_key(number) <= high]
    if not numbers:
        raise UsageError("no roadmap phase falls in the phase range")
    return sorted(dict.fromkeys(numbers), key=phase_key)


def _phase_numbers(value: str, roadmap_numbers: Sequence[str] | None) -> list[str]:
    if "-" in value:
        return _phase_range(value, roadmap_numbers)
    numbers = [_checked(part) for part in _names(value, "phase numbers")]
    return sorted(dict.fromkeys(numbers), key=phase_key)


def parse_work_set(text: str, roadmap_numbers: Sequence[str] | None) -> dict[str, Any]:
    """`phases:16-17` (inclusive range over the roadmap), `phases:16,16.1,17`,
    `plans:a.md,b.md` or `free:<text>`. Anything else is a UsageError."""
    kind, _, value = text.partition(":")
    value = value.strip()
    if not value:
        raise UsageError("--work-set needs KIND:VALUE, for example phases:16-17")
    if kind == "phases":
        return {"kind": "phases", "numbers": _phase_numbers(value, roadmap_numbers)}
    if kind == "plans":
        return {"kind": "plans", "files": _names(value)}
    if kind == "free":
        return {"kind": "free", "text": " ".join(value.split())}
    raise UsageError("--work-set kind must be phases, plans or free")


# ─── GSD captures (read-only `query` calls, list argv) ───────────────────────


def _gsd_tokens(text: str | None) -> list[str]:
    if not text:
        return []
    try:
        tokens = shlex.split(text)
    except ValueError as exc:
        raise UsageError("--gsd-cmd does not parse as a command") from exc
    if not tokens:
        raise UsageError("--gsd-cmd names no command")
    return tokens


def _gsd_json(args: argparse.Namespace, seams: CliSeams, tokens: Sequence[str],
              query: Sequence[str]) -> Any:
    """One read-only query through the host seam; None on any failure."""
    rc, out = seams.host.run([*tokens, "query", *query], GSD_TIMEOUT, args.repo)
    if rc != 0:
        return None
    try:
        return json.loads(out)
    except ValueError:
        return None


def _gsd_work(args: argparse.Namespace) -> bool:
    """GSD phases are read only for a `.planning/` project and a phases or unspecified work set."""
    kind = args.work_set.partition(":")[0] if args.work_set else None
    has_planning = os.path.isfile(os.path.join(args.repo, ".planning", "PROJECT.md"))
    return has_planning and kind in (None, "phases")


def _roadmap(args: argparse.Namespace, seams: CliSeams, tokens: Sequence[str]) -> Any:
    if args.roadmap:
        return _read_json(args.roadmap, "--roadmap")
    if not tokens:
        if args.work_set is None:
            return None  # no work set: the roadmap is optional; only phases need it
        raise UsageError("a GSD work set needs --roadmap or --gsd-cmd")
    roadmap = _gsd_json(args, seams, tokens, ["roadmap.analyze"])
    if roadmap is None:
        raise UsageError("the --gsd-cmd roadmap query failed or did not print JSON")
    return roadmap


def _identity(args: argparse.Namespace, seams: CliSeams, tokens: Sequence[str]) -> Any:
    if args.identity:
        return _read_json(args.identity, "--identity")
    return _gsd_json(args, seams, tokens, ["runtime-identity"]) if tokens else None


def _phase_op(args: argparse.Namespace, seams: CliSeams, tokens: Sequence[str],
              number: str) -> Any:
    if args.phase_op:
        try:
            return _read_json(os.path.join(args.phase_op, f"{number}.json"), "--phase-op")
        except UsageError:
            return None
    return _gsd_json(args, seams, tokens, ["init.phase-op", number]) if tokens else None


def _op_numbers(work: Mapping[str, Any] | None, roadmap: Any) -> list[str]:
    """The phases whose phase-op document is needed: the phases work set, or every roadmap
    phase when no work set is given."""
    if work is not None:
        return list(work["numbers"]) if work["kind"] == "phases" else []
    return _roadmap_numbers(roadmap) or []


def _gsd_captures(args: argparse.Namespace, seams: CliSeams, tokens: Sequence[str], roadmap: Any,
                  work: Mapping[str, Any] | None) -> Captures:
    identity = _identity(args, seams, tokens)
    ops: dict[str, Any] = {}
    complete = True
    for number in _op_numbers(work, roadmap):
        doc = _phase_op(args, seams, tokens, number)
        if doc is None:
            complete = False
        else:
            ops[number] = doc
    needs = (["identity"] if identity is None else []) + ([] if complete else ["phase_op"])
    return Captures(roadmap, identity, ops, tuple(needs))


# ─── scope, host, strategies ─────────────────────────────────────────────────


def _restrict_plans(repo: str, scope: dict[str, Any], files: Sequence[str]) -> dict[str, Any]:
    """Keep only the named superpowers plans, in dependency order (WINDOWS #2)."""
    names = {os.path.basename(path) for path in files}
    chosen = [plan for plan in gp_scope.load_plans(repo) if plan.file in names]
    if len(chosen) != len(names):
        raise UsageError("a plan named in --work-set is not in docs/superpowers/plans")
    scope["plans"] = [plan._asdict() for plan in chosen]
    scope["order"] = gp_scope.execution_order(chosen)
    return scope


def _scope(repo: str, work: Mapping[str, Any] | None, captures: Captures) -> dict[str, Any]:
    if work is not None and work["kind"] == "free":
        return {"kind": "none", "identity": "unverified", "ask": None,
                "phases": [], "plans": [], "order": []}
    kind = work["kind"] if work is not None else None
    numbers = list(work["numbers"]) if work is not None and kind == "phases" else None
    inputs = gp_scope.ScopeInputs(
        roadmap=captures.roadmap if kind != "plans" else None,
        phase_ops=captures.phase_ops,
        identity=captures.identity,
        work_kind=kind,
        numbers=numbers,
        plan_files=(
            [os.path.basename(f) for f in work["files"]] if work and kind == "plans" else None
        ),
    )
    try:
        scope = gp_scope.detect_scope(repo, inputs)
    except ValueError as exc:
        if str(exc).startswith("dependency cycle"):
            raise UsageError(f"superpowers plans {exc}") from exc
        raise UsageError(
            "the roadmap lacks a phase named in --work-set or has a bad shape"
        ) from exc
    if work is not None and kind == "plans":
        scope = _restrict_plans(repo, scope, work["files"])
    return scope


def _target(args: argparse.Namespace, current: str | None) -> str:
    if not args.target_host:
        return current or "unknown"
    if args.target_host not in gp_host.HOST_BINARY:
        raise UsageError("--target-host names no known host")
    return args.target_host


def _host_part(seams: CliSeams, args: argparse.Namespace, tools: list[str]) -> dict[str, Any]:
    """The host object, the primitive table, the matrix source and the unrecognized tools."""
    current = gp_host.current_host(seams.host, _sibling(seams, args.spec_cli, gp_host.SPEC_CLI))
    target = _target(args, current)
    version = gp_host.host_version(seams.host, current) if current else None
    rows, reason = gp_host.read_matrix(
        seams.host, _sibling(seams, args.wake_cli, gp_host.WAKE_CLI)
    )
    seen = gp_host.Seen(frozenset(tools), gp_host.help_mentions(seams.host, target))
    if rows is None:
        primitives = gp_host.degraded_primitives(reason, target)
        source = "missing"
    else:
        primitives = gp_host.build_primitives(
            rows, target=target, current=current, version=version, seen=seen
        )
        source = "session-wake"
    return {
        "host": {"current": current, "target": target, "current_version": version},
        "primitives": primitives,
        "matrix_source": source,
        "unrecognized_tools": gp_host.unrecognized_tools(tools, rows),
    }


def _count(scope: Mapping[str, Any]) -> int:
    return len(scope["phases"]) or len(scope["plans"])


def _derived(count: int, e2e_none: bool, mockups: int) -> dict[str, bool]:
    """D-11 inputs. `unattended` is not asked, so must_outlive follows the item count alone."""
    return gp_matrix.derive(count, unattended=False, e2e_none=e2e_none, mockups=mockups)


def _strategies(scope: Mapping[str, Any], primitives: list[dict[str, Any]],
                derived: Mapping[str, bool], request: str | None) -> tuple[list, list]:
    """Ranked strategies for the scope, honouring the user's request, and the dropped requests.
    A scope with an open question (`ask`) has no strategies yet."""
    chosen = gp_matrix.select(
        MatrixInputs(scope["kind"], request, primitives,
                     derived["must_outlive"], derived["provable"])
    )
    dropped = list(chosen["dropped"])
    if request == "autonomous" and not any(s["id"] == "autonomous" for s in chosen["strategies"]):
        dropped.append({"id": "autonomous", "reason": AUTONOMOUS_DROPPED})
    strategies = [] if scope.get("ask") else chosen["strategies"]
    return strategies, dropped


def _workflow(repo: str) -> dict[str, Any]:
    try:
        with open(os.path.join(repo, ".planning", "config.json"), encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, UnicodeDecodeError, ValueError):
        return {}
    workflow = config.get("workflow") if isinstance(config, dict) else None
    return workflow if isinstance(workflow, dict) else {}


def _runner_command(repo: str, home: str) -> str:
    """workflow.cross_ai_command as written; "" when absent or when a token is a machine path."""
    command = _workflow(repo).get("cross_ai_command")
    if not isinstance(command, str) or any(is_machine_path(tok, home) for tok in command.split()):
        return ""
    return " ".join(command.split())


def _candidate_skills(skills_dir: str) -> list[str]:
    return sorted(name for name in SIBLING_SKILLS if os.path.isdir(os.path.join(skills_dir, name)))


# ─── detect ──────────────────────────────────────────────────────────────────


def _checked_repo(repo: str) -> str:
    if not os.path.isdir(repo):
        raise UsageError("--repo is not a directory")
    return repo


def build_detect(args: argparse.Namespace, seams: CliSeams) -> dict[str, Any]:
    """The contract object for `args.repo`. Read-only: nothing is written to the project."""
    repo = _checked_repo(args.repo)
    gsd = _gsd_work(args)
    tokens = _gsd_tokens(args.gsd_cmd)
    roadmap = _roadmap(args, seams, tokens) if gsd else None
    work = parse_work_set(args.work_set, _roadmap_numbers(roadmap)) if args.work_set else None
    captures = _gsd_captures(args, seams, tokens, roadmap, work) if gsd else NO_CAPTURES
    scope = _scope(repo, work, captures)
    host = _host_part(seams, args, _tool_names(args.tools))
    readiness = gp_host.cross_ai_readiness(
        seams.host, repo, native=False, spec_cli=_sibling(seams, args.spec_cli, gp_host.SPEC_CLI)
    )
    e2e = detect_e2e(repo)
    derived = _derived(_count(scope), e2e["none"], 0)
    strategies, dropped = _strategies(scope, host["primitives"], derived, None)
    return {
        "schema_version": SCHEMA_VERSION,
        **host,
        "scope": scope,
        "e2e": e2e,
        "readiness": readiness,
        "jev": gp_host.jev_status(seams.host, _sibling(seams, args.decide_cli, gp_host.DECIDE_CLI)),
        "derived": derived,
        "strategies": strategies,
        "dropped": dropped,
        "needs": list(captures.needs),
        "candidate_skills": _candidate_skills(seams.skills_dir),
        "wake": gp_matrix.wake_primitive(host["primitives"]),
        "runner": {"command": _runner_command(repo, seams.home), "label": readiness["label"]},
    }


# ─── render ──────────────────────────────────────────────────────────────────


def _require(condition: bool, field: str, expected: str) -> None:
    if not condition:
        raise UsageError(f"answers field {field} must be {expected}")


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _check_work(work: Any) -> None:
    kind = work.get("kind")
    _require(kind in WORK_KINDS, "work_set.kind", "phases, plans or free")
    if kind == "phases":
        _require(_string_list(work.get("numbers")), "work_set.numbers", "a list of strings")
    elif kind == "plans":
        _require(_string_list(work.get("files")), "work_set.files", "a list of strings")
    else:
        _require(isinstance(work.get("text"), str), "work_set.text", "a string")


def _check_output_dir(value: Any) -> None:
    if value is None:
        return
    _require(isinstance(value, str), "output_dir", "a string or null")
    parts = value.replace("\\", "/").split("/")
    if ".." in parts or os.path.isabs(value) or value.startswith("~"):
        raise UsageError("field output_dir must stay inside the repository")


def _check_answers(answers: Any) -> None:
    if not isinstance(answers, dict):
        raise UsageError("--answers must hold a JSON object")
    work = answers.get("work_set")
    _require(isinstance(work, dict), "work_set", "an object")
    _check_work(work)
    target = answers.get("target_host")
    _require(target is None or isinstance(target, str), "target_host", "a string")
    _require(isinstance(answers.get("native_execution", False), bool),
             "native_execution", "true or false")
    mockups = answers.get("mockups")
    _require(mockups is None or _string_list(mockups), "mockups", "a list of strings")
    _require(answers.get("strategy") in (None, *STRATEGIES), "strategy",
             "goal, loop, autonomous or null")
    _require(isinstance(answers.get("objective", ""), str), "objective", "a string")
    skills = answers.get("skills") or []
    _require(_string_list(skills) and all(SKILL_NAME_RE.fullmatch(s) for s in skills),
             "skills", "a list of skill names")
    _check_output_dir(answers.get("output_dir"))


def _merged_skills(detect: Mapping[str, Any], answers: Mapping[str, Any]) -> list[str]:
    extra = answers.get("skills") or []
    return sorted(set(detect.get("candidate_skills") or []) | set(extra))


def run_render(args: argparse.Namespace, seams: CliSeams) -> dict[str, Any]:
    """Write one goal file from a detect result and an answers file; return its contract.

    The strategies are re-selected with the answers' explicit request, so a request the host
    cannot run is reported in `dropped` (WINDOWS #3), never rendered.
    """
    detect = _read_json(args.detect, "--detect")
    if not isinstance(detect, dict) or detect.get("schema_version") != SCHEMA_VERSION:
        raise UsageError("--detect file is not a schema 1 detect result")
    answers = _read_json(args.answers, "--answers")
    _check_answers(answers)
    _check_output_dir(args.out_dir)
    _checked_repo(args.repo)
    derived = _derived(_count(detect["scope"]), detect["e2e"]["none"],
                       len(answers.get("mockups") or []))
    strategies, dropped = _strategies(
        detect["scope"], detect["primitives"], derived, answers.get("strategy")
    )
    detect = {**detect, "strategies": strategies,
              "candidate_skills": _merged_skills(detect, answers)}
    ctx = RenderContext(
        repo=args.repo,
        today=seams.today,
        home=seams.home,
        secrets=seams.secrets,
        out_dir=args.out_dir,
    )
    result = gp_render.render(detect, answers, ctx)
    result["dropped"] = dropped
    return result


# ─── entry point ─────────────────────────────────────────────────────────────


def main(argv: Sequence[str] | None = None, seams: CliSeams | None = None) -> int:
    """Run one subcommand; exit 0 with JSON on stdout, or 2 with a JSON error on stderr."""
    active = seams if seams is not None else real_seams()
    try:
        args = build_parser().parse_args(argv)
        if args.command == "detect":
            result = build_detect(args, active)
        else:
            result = run_render(args, active)
    except (UsageError, GuardError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    except (AttributeError, KeyError, TypeError, ValueError):
        print(json.dumps({"error": "input does not match the expected shape"}), file=sys.stderr)
        return 2
    except OSError:
        print(json.dumps({"error": "cannot read or write a file"}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
