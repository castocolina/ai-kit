"""The command line (D-02): `arm`, `disarm`, `fire`, `done` in this plan
(26-03 adds `status` and `matrix`). The host defaults to
`detect_current_runtime` on the seams env (`unknown` is refused, exit 2); the
session id defaults to the host row's session-env value."""

import argparse
import os
import sys
from collections.abc import Mapping

from ai_kit_spec.detection import detect_current_runtime

from .arm import ArmOptions, ResetArg, arm
from .fire import disarm, done, fire
from .hosts import HOSTS
from .liveness import is_alive
from .matrix import matrix_json, render_matrix
from .reset_parse import iso_z
from .state import Seams, default_seams, read_state, session_paths, state_dir
from .units import linger_enabled, systemctl, unit_names

EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_NO_PRIMITIVE = 3

_SHIM_NAME = "ai-kit-session-wake.py"


def default_shim_path() -> str:
    """The shim beside this package: the absolute ExecStart argument (D-13)."""
    skill_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    return os.path.join(skill_dir, _SHIM_NAME)


def _pick_target(host_flag: str | None, sid_flag: str | None, env: Mapping[str, str]):
    """Resolve (host, session id) from the flags or the host defaults; print
    the refusal and return None when there is nothing to operate on."""
    host = host_flag or detect_current_runtime(env)
    row = HOSTS.get(host)
    if host == "cursor":
        session_id = sid_flag or "cursor-session"
    elif row is None:
        print(f"ai-kit-session-wake: unknown or unsupported host {host!r}", file=sys.stderr)
        return None
    else:
        session_id = sid_flag or (env.get(row.session_env, "") if row.session_env else "")
        if not session_id:
            print(
                f"ai-kit-session-wake: no session id: pass --session-id or set {row.session_env}",
                file=sys.stderr,
            )
            return None
    return (host, session_id) if _id_accepted(env, host, session_id) else None


def _id_accepted(env: Mapping[str, str], host: str, session_id: str) -> bool:
    """False, after printing the refusal, when the id fails the safe charset: it
    never reaches a path or a unit name (an exit 2 instead of a traceback)."""
    try:
        session_paths(env, host, session_id)
    except ValueError as exc:
        print(f"ai-kit-session-wake: {exc}", file=sys.stderr)
        return False
    return True


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-kit-session-wake",
        description="Arm, fire and retire a session wake that survives its host process.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("arm", "record this session and enable its persistent wake timer"),
        ("disarm", "remove a session's wake completely"),
        ("fire", "one timer wake: resume the recorded session id once"),
        ("done", "write the done marker so the next wake disarms"),
        ("status", "show recorded wake state"),
        ("matrix", "show wake survival by host"),
    ):
        sub_parser = sub.add_parser(name, help=help_text)
        sub_parser.add_argument("--host", help="runtime label (default: detect from the env)")
        sub_parser.add_argument("--session-id", help="session id (default: the host's env var)")
    sub.choices["matrix"].add_argument("--json", action="store_true")
    sub.choices["arm"].add_argument("--pid", type=int, help="the host process id")
    sub.choices["arm"].add_argument(
        "--only-if-armed",
        action="store_true",
        help="refresh an existing wake only; exit 0 without arming when none exists",
    )
    sub.choices["arm"].add_argument(
        "--permission-mode", help="the mode the resume replays (default: unknown, no bypass)"
    )
    sub.choices["arm"].add_argument(
        "--ref", action="append", default=[], help="read-only state path to record (repeatable)"
    )
    reset = sub.choices["arm"].add_mutually_exclusive_group()
    reset.add_argument(
        "--reset-text",
        help="the host's limit text; its reset time sets the wake (inferred; D-30)",
    )
    reset.add_argument(
        "--reset-at",
        help="the reset time as epoch seconds or ISO 8601 with Z or an explicit offset",
    )
    return parser


def _reset_arg(args: argparse.Namespace) -> ResetArg | None:
    if args.reset_text is not None:
        return ResetArg("text", args.reset_text)
    if args.reset_at is not None:
        return ResetArg("at", args.reset_at)
    return None


def _dispatch(
    command: str, host: str, session_id: str, args: argparse.Namespace, seams: Seams
) -> int:
    if command == "arm":
        opts = ArmOptions(
            host, session_id, args.pid, args.permission_mode, tuple(args.ref), _reset_arg(args),
            only_if_armed=args.only_if_armed,
        )
        return arm(opts, seams, default_shim_path())
    if command == "disarm":
        return disarm(host, session_id, seams)
    if command == "fire":
        return fire(host, session_id, seams)
    return done(host, session_id, seams)


def main(argv: list[str], seams: Seams | None = None) -> int:
    """Run one subcommand; every refusal is an exit code, never an exception."""
    seams = seams if seams is not None else default_seams()
    args = _parser().parse_args(argv)
    if args.command == "matrix":
        print(matrix_json() if args.json else render_matrix())
        return EXIT_OK
    if args.command == "status":
        return _status(args, seams)
    if args.command == "arm" and args.host == "cursor":
        print("no surviving primitive for cursor")
        return EXIT_NO_PRIMITIVE
    target = _pick_target(args.host, args.session_id, seams.env)
    if target is None:
        return EXIT_REFUSED
    host, session_id = target
    return _dispatch(args.command, host, session_id, args, seams)


def _status_entry(path: str, seams: Seams) -> None:
    name = os.path.basename(path)[:-5]
    host, _, sid = name.partition("-")
    state, reason = read_state(path, host, sid)
    print(path)
    if state is None:
        print(f"invalid state: {reason}")
        return
    cwd_note = "" if state.get("launch_cwd_verified", True) else " (unverified)"
    print(f"launch_cwd: {state['launch_cwd']}{cwd_note}")
    status = "alive" if is_alive(state, seams) else "gone"
    print(f"host process: {status} ({state.get('liveness_source', 'proc')})")
    print(f"wakes: {state['wake_count']}/{state['cap']}")
    if state.get("wake_source") == "reset_inferred":
        print(
            f"next wake: {iso_z(state['not_before'])} UTC (inferred: host-reported reset + 60 s; "
            "the host did not state this wake time), then hourly"
        )
    else:
        print("next wake: hourly")
    print(
        f"permission_mode: {state['permission_mode']} ({state.get('permission_source', 'unknown')})"
    )
    print(f"linger: {linger_enabled(seams)}")
    active = systemctl(seams, "is-active", unit_names(host, sid).timer)
    print(active.stdout.strip() or active.stderr.strip() or "unknown")
    for created in state["created"]:
        print(f"created: {created}")


def _status(args: argparse.Namespace, seams: Seams) -> int:
    directory = state_dir(seams.env)
    if bool(args.host) != bool(args.session_id):
        print("status requires both --host and --session-id", file=sys.stderr)
        return EXIT_REFUSED
    if args.host and args.host not in (*HOSTS, "cursor"):
        print(f"ai-kit-session-wake: unknown or unsupported host {args.host!r}", file=sys.stderr)
        return EXIT_REFUSED
    if args.host and not _id_accepted(seams.env, args.host, args.session_id):
        return EXIT_REFUSED
    files = []
    if args.host and args.session_id:
        files = [os.path.join(directory, f"{args.host}-{args.session_id}.json")]
    elif os.path.isdir(directory):
        files = [
            os.path.join(directory, name)
            for name in sorted(os.listdir(directory))
            if name.endswith(".json")
        ]
    if not files:
        print("nothing armed")
        return EXIT_OK
    for path in files:
        _status_entry(path, seams)
    return EXIT_OK
