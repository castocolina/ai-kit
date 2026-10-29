"""The command line (D-02): `arm`, `disarm`, `fire`, `done` in this plan
(26-03 adds `status` and `matrix`). The host defaults to
`detect_current_runtime` on the seams env (`unknown` is refused, exit 2); the
session id defaults to the host row's session-env value."""
import argparse
import os
import sys
from collections.abc import Mapping

from ai_kit_spec.detection import detect_current_runtime

from .arm import ArmOptions, arm
from .fire import disarm, done, fire
from .hosts import HOSTS
from .state import Seams, default_seams

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
    if row is None:
        print(f"ai-kit-session-wake: unknown or unsupported host {host!r}", file=sys.stderr)
        return None
    session_id = sid_flag or env.get(row.session_env, "")
    if not session_id:
        print(
            f"ai-kit-session-wake: no session id: pass --session-id or set {row.session_env}",
            file=sys.stderr,
        )
        return None
    return host, session_id


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
    ):
        sub_parser = sub.add_parser(name, help=help_text)
        sub_parser.add_argument("--host", help="runtime label (default: detect from the env)")
        sub_parser.add_argument("--session-id", help="session id (default: the host's env var)")
    sub.choices["arm"].add_argument("--pid", type=int, help="the host process id")
    sub.choices["arm"].add_argument(
        "--permission-mode", help="the mode the resume replays (default: unknown, no bypass)"
    )
    sub.choices["arm"].add_argument(
        "--ref", action="append", default=[], help="read-only state path to record (repeatable)"
    )
    return parser


def main(argv: list[str], seams: Seams | None = None) -> int:
    """Run one subcommand; every refusal is an exit code, never an exception."""
    seams = seams if seams is not None else default_seams()
    args = _parser().parse_args(argv)
    target = _pick_target(args.host, args.session_id, seams.env)
    if target is None:
        return EXIT_REFUSED
    host, session_id = target
    if args.command == "arm":
        opts = ArmOptions(
            host=host,
            session_id=session_id,
            pid=args.pid,
            permission_mode=args.permission_mode,
            refs=tuple(args.ref),
        )
        return arm(opts, seams, default_shim_path())
    if args.command == "disarm":
        return disarm(host, session_id, seams)
    if args.command == "fire":
        return fire(host, session_id, seams)
    return done(host, session_id, seams)
