"""Per-host resume table (D-04, D-15) and the resume child's env (T-26-04).

Hosts are keyed by the runtime labels of `ai_kit_spec.detection`. Rows carry
their evidence; only `claude` is in this plan (26-04 adds pi, opencode and
codex). The scrub set is derived from the RUNTIMES single source of truth plus
the host-session markers, so a resumed agent never looks like the host that
stalled.
"""

import glob
import json
import os
import re
import shutil
import subprocess
from typing import NamedTuple

from ai_kit_spec.detection import HOST_SIGNAL_ENV_VARS

from .state import SESSION_ID_RE
from .units import service_environment

FIRE_MARKER_ENV = "AI_KIT_SESSION_WAKE_FIRE"


class Host(NamedTuple):
    """One host's wake facts, each row labelled with its evidence."""

    label: str
    session_env: str | None
    pid_env: str | None
    resume: tuple[str, ...]
    store: tuple[str, str, str] | None
    verified: bool
    evidence: str


# Resume tokens take `{id}`; stores use an exact stem regex with a literal <ID>
# replaced only after validating the id.
HOSTS: dict[str, Host] = {
    "claude": Host(
        label="claude",
        session_env="CLAUDE_CODE_SESSION_ID",
        pid_env="CLAUDE_PID",
        resume=("--resume", "{id}", "--permission-prompts", "none"),
        store=(".claude", "projects/*/<ID>.jsonl", "<ID>"),
        verified=True,
        evidence="spike 001, claude 2.1.310",
    ),
    "pi": Host(
        "pi",
        None,
        None,
        ("-p", "--session-id", "{id}"),
        (".pi/agent", "sessions/*/*.jsonl", "(?:[^_]*_)?<ID>"),
        True,
        "spike 003, pi 1.3.0",
    ),
    "opencode": Host(
        "opencode",
        None,
        None,
        ("run", "--session", "{id}"),
        None,
        True,
        "spike 003, opencode 2.0.31; JSON listing shape unverified",
    ),
    "codex": Host(
        "codex",
        "CODEX_THREAD_ID",
        None,
        ("exec", "resume", "{id}"),
        (
            ".codex",
            "sessions/**/rollout-*.jsonl",
            "rollout-[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}-[0-9]{2}-[0-9]{2}-<ID>",
        ),
        False,
        "help only, codex-cli 0.162.1",
    ),
}

OPENCODE_LIST_MAX = 10000

WAKE_SCRUB = frozenset(HOST_SIGNAL_ENV_VARS) | {
    "CLAUDE_PID",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_CODE_CHILD_SESSION",
    "CLAUDE_JOB_DIR",
    "AI_KIT_CROSS_AI_CHILD",
}


def permission_from_cmdline(host: str, argv: list[str] | None) -> str:
    if host != "claude" or not argv or "bg-spare" in argv:
        return "unknown"
    if "--dangerously-skip-permissions" in argv:
        return "bypassPermissions"
    for index, token in enumerate(argv):
        if token == "--permission-mode" and index + 1 < len(argv):
            return argv[index + 1]
        if token.startswith("--permission-mode="):
            return token.split("=", 1)[1]
    return "default"


def resume_argv(state: dict, prompt: str) -> list[str]:
    """The single resume of the recorded id (D-03, D-15): the recorded
    cli_path first, then the row's tokens, the mode flags (claude only;
    empty for `default` and `unknown`), then the prompt. Claude takes it after `-p`;
    pi, opencode and codex take it as the final positional (D-15, spike 003)."""
    row = HOSTS[state["host"]]
    tokens = [token.replace("{id}", state["session_id"]) for token in row.resume]
    argv = [state["cli_path"], *tokens]
    mode = state.get("permission_mode", "unknown")
    # only claude has a verified permission flag; arm says "not applied" for the rest
    if state["host"] == "claude" and mode not in ("default", "unknown"):
        argv += ["--permission-mode", mode]
    if state["host"] == "claude":
        return [*argv, "-p", prompt]
    return [*argv, prompt]


def child_env(env, host: str, session_id: str) -> dict[str, str]:
    """The resume child's environment: `env` minus every `WAKE_SCRUB` name,
    plus `AI_KIT_SESSION_WAKE_FIRE=<host>-<id>`."""
    scrubbed = {key: value for key, value in env.items() if key not in WAKE_SCRUB}
    scrubbed[FIRE_MARKER_ENV] = f"{host}-{session_id}"
    return scrubbed


def session_exists(  # pylint: disable=too-many-return-statements,too-many-locals
    host: str, session_id: str, launch_cwd: str, seams
) -> tuple[str, str]:
    """`(status, reason)` with status `exists | missing | unknown`.

    `launch_cwd` is part of the signature because pi and opencode key their
    stores by directory (26-04); claude 2.1.310 selects the transcript by id
    alone (spike 001). The claude layout is reverse-engineered, so the reason
    names it `layout unverified`.
    """
    if host not in HOSTS:
        return "unknown", f"no verified transcript layout for {host}"
    row = HOSTS[host]
    if session_id is None or re.fullmatch(SESSION_ID_RE, session_id) is None:
        return "missing", "invalid session id"
    service_env = dict(service_environment(seams.env))
    home = service_env.get("HOME", "")
    if host == "opencode":
        cli = shutil.which("opencode", path=service_env.get("PATH", ""))
        if not cli:
            return "unknown", "opencode listing unavailable; JSON shape and completeness unverified"
        try:
            result = subprocess.run(
                [
                    cli,
                    "session",
                    "list",
                    "--format",
                    "json",
                    "--standalone",
                    "--max-count",
                    str(OPENCODE_LIST_MAX),
                ],
                cwd=launch_cwd,
                env=service_env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            data = json.loads(result.stdout) if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            data = None
        if not isinstance(data, list) or not any(
            isinstance(item, dict) and isinstance(item.get("id"), str) for item in data
        ):
            return (
                "unknown",
                "opencode listing failed or has invalid JSON/ids; listing shape unverified",
            )
        if any(isinstance(item, dict) and item.get("id") == session_id for item in data):
            return "exists", "opencode id listed (JSON shape unverified)"
        if len(data) >= OPENCODE_LIST_MAX:
            return "unknown", "opencode listing may be truncated; completeness unverified"
        return "missing", "opencode id not listed (JSON shape unverified)"
    if row.store is None:
        return "unknown", "no session store configured"
    root, pattern, stem_pattern = row.store
    glob_pattern = os.path.join(home, root, pattern.replace("<ID>", session_id))
    stem_re = re.compile(stem_pattern.replace("<ID>", re.escape(session_id)))
    for candidate in glob.glob(glob_pattern, recursive=True):
        if re.fullmatch(stem_re, os.path.splitext(os.path.basename(candidate))[0]):
            return "exists", candidate + " (layout unverified)"
    return "missing", f"layout unverified: searched {glob_pattern}"
