"""Per-host resume table (D-04, D-15) and the resume child's env (T-26-04).

Hosts are keyed by the runtime labels of `ai_kit_spec.detection`. Rows carry
their evidence; only `claude` is in this plan (26-04 adds pi, opencode and
codex). The scrub set is derived from the RUNTIMES single source of truth plus
the host-session markers, so a resumed agent never looks like the host that
stalled.
"""
import glob
import os
from typing import NamedTuple

from ai_kit_spec.detection import HOST_SIGNAL_ENV_VARS

FIRE_MARKER_ENV = "AI_KIT_SESSION_WAKE_FIRE"


class Host(NamedTuple):
    """One host's wake facts, each row labelled with its evidence."""

    label: str
    session_env: str
    pid_env: str
    resume: tuple[str, ...]
    store: tuple[str, ...]
    verified: bool
    evidence: str


# Resume tokens take `{id}`; `store` globs take `{id}` (layout reverse-engineered
# for claude -- the reason strings say so; AGENTS.md certainty labelling).
HOSTS: dict[str, Host] = {
    "claude": Host(
        label="claude",
        session_env="CLAUDE_CODE_SESSION_ID",
        pid_env="CLAUDE_PID",
        resume=("--resume", "{id}", "--permission-prompts", "none"),
        store=(".claude", "projects", "*", "{id}.jsonl"),
        verified=True,
        evidence="spike 001, claude 2.1.310",
    ),
}

WAKE_SCRUB = frozenset(HOST_SIGNAL_ENV_VARS) | {
    "CLAUDE_PID",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_CODE_CHILD_SESSION",
    "CLAUDE_JOB_DIR",
    "AI_KIT_CROSS_AI_CHILD",
}


def resume_argv(state: dict, prompt: str) -> list[str]:
    """The single resume of the recorded id (D-03, D-15): the recorded
    cli_path first, then the row's tokens, the mode flags (empty for
    `default` and `unknown`), then `-p <prompt>` last."""
    row = HOSTS[state["host"]]
    tokens = [token.replace("{id}", state["session_id"]) for token in row.resume]
    argv = [state["cli_path"], *tokens]
    mode = state.get("permission_mode", "unknown")
    if mode not in ("default", "unknown"):
        argv += ["--permission-mode", mode]
    return [*argv, "-p", prompt]


def child_env(env, host: str, session_id: str) -> dict[str, str]:
    """The resume child's environment: `env` minus every `WAKE_SCRUB` name,
    plus `AI_KIT_SESSION_WAKE_FIRE=<host>-<id>`."""
    scrubbed = {key: value for key, value in env.items() if key not in WAKE_SCRUB}
    scrubbed[FIRE_MARKER_ENV] = f"{host}-{session_id}"
    return scrubbed


def session_exists(host: str, session_id: str, launch_cwd: str, seams) -> tuple[str, str]:
    """`(status, reason)` with status `exists | missing | unknown`.

    `launch_cwd` is part of the signature because pi and opencode key their
    stores by directory (26-04); claude 2.1.310 selects the transcript by id
    alone (spike 001). The claude layout is reverse-engineered, so the reason
    names it `layout unverified`.
    """
    if host not in HOSTS:
        return "unknown", f"no verified transcript layout for {host}"
    row = HOSTS[host]
    home = seams.env.get("HOME", "")
    parts = [part.replace("{id}", session_id) for part in row.store]
    pattern = os.path.join(home, *parts)
    matches = sorted(glob.glob(pattern))
    if matches:
        return "exists", matches[0]
    return "missing", "layout unverified: no <HOME>/.claude/projects/*/<id>.jsonl transcript"
