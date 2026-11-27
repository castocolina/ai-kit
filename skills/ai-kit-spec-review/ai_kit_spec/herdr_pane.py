"""Runs an interactive lane in a reused herdr pane on the runner's hosted-lane protocol,
reading verdicts from the round's files only.

Limits: the pane hosts the lane's headless runner command in a visible, reused pane for an
owner-marked interactive lane; an interactive agent TUI is not driven (it takes no model flag
and gives no structured result). Spec-review lanes never get a pane: their run folder is
removed by spec review's own cleanup, so they use a subprocess or a resumed session.
"""

import contextlib
import json
import os
import re
import secrets
import shlex
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from stat import S_ISDIR, S_ISREG
from typing import Any, NamedTuple

from ai_kit_spec import runner_dispatch
from ai_kit_spec.cache import cache_write_text
from ai_kit_spec.herdr_source import herdr_available
from ai_kit_spec.runner_dispatch import child_env, parse_status_line

HOST_FILES = {
    "run": "run.json",
    "launcher": "launch.sh",
    "env": "env",
    "prompt": "prompt",
    "out": "out",
    "err": "err",
    "pid": "pid",
    "rc": "rc",
}
LABEL_PREFIX = "aikit"
LABEL_MAX = 63
LABEL_RE = re.compile(r"^aikit:(review|execute):[A-Za-z0-9][A-Za-z0-9-]{0,31}:[0-9a-f]{12}$")
TOKEN_RE = re.compile(r"^[0-9a-f]{12}$")
RC_RE = re.compile(r"^(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9]|SIG[A-Z0-9]{2,8})$")
HOST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
PATH_SAFE_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PANE_TOOLS = ("/bin/sh", "/usr/bin/env", "/usr/bin/setsid", "/bin/rm", "/bin/mv", "/bin/sleep")
PANE_VERBS = ("tab create", "pane run", "tab close", "tab list")
RUN_RECORD_VERSION = 1
RUN_RECORD_MAX_BYTES = 65536
DIR_MODE = 0o700
FILE_MODE = 0o600
ROUND_FILE = "round.sh"
ROUND_RUN = "round.run"
PANE_IDLE_S = 1800
PANE_PID_GRACE_S = 5
POLL_S = 0.25
HERDR_TIMEOUT_S = 5
KILL_GRACE_S = 2
STDERR_TAIL_CHARS = 2048
ROUND_ENDS = ("rc", "launcher gone", "timeout")


def state_home(env: dict) -> str:
    """The XDG state home, or ~/.local/state when it is unset (the runner's stateHome)."""
    named = (env.get("XDG_STATE_HOME") or "").strip()
    home = env.get("HOME") or os.path.expanduser("~")
    return os.path.abspath(named or os.path.join(home, ".local", "state"))


def run_dir_for(env: dict, token: str) -> str:
    """<state home>/ai-kit/spec/host/<token>, the run folder the sweep also reads."""
    return os.path.join(state_home(env), "ai-kit", "spec", "host", token)


def pane_label(role: str, runtime: str, token: str) -> str:
    """aikit:<role>:<runtime>:<token>, the tab label the owner sees in the pane."""
    return f"{LABEL_PREFIX}:{role}:{runtime}:{token}"


def typed_line(launcher_path: str) -> str:
    """The line typed into the pane: sh <launcher path>, never an executable path."""
    return "sh " + launcher_path


def new_token() -> str:
    """12 hex chars, unique per pane lane (the runner's hostToken)."""
    return secrets.token_hex(6)


def proc_start_time(pid: int) -> str:
    """Field 22 of /proc/<pid>/stat parsed after the last ')', or '-' when unreadable."""
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as handle:
            stat = handle.read()
        fields = stat[stat.rfind(")") + 1:].split()
        start = fields[19]
    except (OSError, IndexError):
        return "-"
    return start if start.isdigit() else "-"


def pid_alive(pid: int) -> bool:
    """True while the pid answers a signal-0 probe and is not a zombie."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as handle:
            stat = handle.read()
    except OSError:
        return True
    return re.match(r"^\d+ \(.*\) Z", stat) is None


def pane_problem(run_dir: str, access_fn=os.access) -> str | None:
    """The reason the pane transport cannot start on this host, or None when it can."""
    if PATH_SAFE_RE.fullmatch(run_dir) is None:
        return "state home path holds a character outside [A-Za-z0-9._/-]"
    for path in PANE_TOOLS:
        if not access_fn(path, os.X_OK):
            return f"{path} is not executable"
    return None


class PaneSeams(NamedTuple):
    """Call seams: herdr runs, the clock, and pid checks stay fake-able per test."""

    run_fn: Callable[..., Any] = subprocess.run
    which_fn: Callable[..., str | None] = shutil.which
    time_fn: Callable[[], float] = time.monotonic
    sleep_fn: Callable[[float], None] = time.sleep
    token_fn: Callable[[], str] = new_token
    alive_fn: Callable[[int], bool] = pid_alive
    killpg_fn: Callable[[int, int], None] = os.killpg
    start_fn: Callable[[int], str] = proc_start_time


DEFAULT_SEAMS = PaneSeams()


class PaneRound(NamedTuple):
    """One round's job: the runner command, its prompt and its whole-wait timeout."""

    argv: list[str]
    prompt: str
    cwd: str
    timeout_s: int
    env: dict | None = None


def _refuse(reason: str) -> None:
    """One stderr refusal line, always paired with a None return."""
    print(f"ai-kit-spec: pane: {reason}", file=sys.stderr)


def _herdr_call(binary: str, verb: str, args: list, env: dict, run_fn: Callable[..., Any]) -> Any:
    """One herdr verb call (the runner's herdrCall), or None when it fails to answer."""
    if verb not in PANE_VERBS:
        raise ValueError(
            f"herdr verb {verb} is not one of tab create, pane run, tab close, tab list")
    try:
        return run_fn([binary, *verb.split(" "), *args], capture_output=True, text=True,
                      env=env, timeout=HERDR_TIMEOUT_S, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _herdr_code(result) -> str | None:
    """The error.code string of a herdr JSON stderr line, or None when there is none."""
    if result is None or not isinstance(result.stderr, str):
        return None
    try:
        parsed = json.loads(result.stderr)
    except ValueError:
        return None
    if not isinstance(parsed, dict) or not isinstance(parsed.get("error"), dict):
        return None
    code = parsed["error"].get("code")
    return code if isinstance(code, str) else None


def launcher_text(run_dir: str, token: str) -> str:
    """The pane's launcher loop: one clean-environment re-exec, then the reused round pipe.

    The loop ends when the launcher file is removed (close, or keep-record-only) or after
    PANE_IDLE_S idle seconds, so the runner's sweep always reads a live launcher or nothing.
    """
    q = shlex.quote

    def f(name: str) -> str:
        return q(os.path.join(run_dir, name))

    lines = [
        "#!/bin/sh",
        f'[ "${{AIKIT_HOST_CLEAN:-}}" = {q(token)} ] || exec /usr/bin/env -i '
        f'AIKIT_HOST_CLEAN={q(token)} /usr/bin/setsid /bin/sh "$0"',
        "unset AIKIT_HOST_CLEAN",
        f"printf '%s\\n' \"$$\" > {f('pid.tmp')} && /bin/mv {f('pid.tmp')} {f('pid')}",
        "idle=0",
        f'while [ "$idle" -lt {PANE_IDLE_S} ] && [ -f {f(HOST_FILES["launcher"])} ]; do',
        f'  if [ -f {f(ROUND_FILE)} ] && /bin/mv {f(ROUND_FILE)} {f(ROUND_RUN)}; then',
        f'    /bin/sh {f(ROUND_RUN)} > {f(HOST_FILES["out"])} 2> {f(HOST_FILES["err"])}',
        "    rc=$?",
        '    if [ "$rc" -gt 128 ] && sig=$(kill -l "$rc" 2>/dev/null); then rc="SIG$sig"; fi',
        f"    /bin/rm -f {f(ROUND_RUN)}",
        f"    printf '%s\\n' \"$rc\" > {f('rc.tmp')} && /bin/mv {f('rc.tmp')} "
        f"{f(HOST_FILES['rc'])}",
        f'    printf \'AIKIT-HOST-DONE %s rc=%s\\n\' {q(token)} "$rc"',
        "    idle=0",
        "  else",
        "    /bin/sleep 1",
        "    idle=$((idle + 1))",
        "  fi",
        "done",
    ]
    return "\n".join(lines) + "\n"


def _round_text(run_dir: str, job: PaneRound) -> str:
    q = shlex.quote

    def f(name: str) -> str:
        return q(os.path.join(run_dir, name))

    if "\0" in job.cwd or any("\0" in element for element in job.argv):
        raise ValueError("argv element holds a NUL byte")
    lines = [
        ". " + f(HOST_FILES["env"]),
        "exec 3< " + f(HOST_FILES["prompt"]),
        "/bin/rm -f " + f(HOST_FILES["env"]) + " " + f(HOST_FILES["prompt"]),
        f"cd {q(job.cwd)} && {' '.join(q(element) for element in job.argv)} <&3 3<&-",
    ]
    return "\n".join(lines) + "\n"


def _env_text(env: dict) -> str:
    lines = []
    for name, value in env.items():
        if ENV_NAME_RE.fullmatch(name) is not None:
            lines.append(f"export {name}={shlex.quote(str(value))}")
    return "\n".join(lines) + "\n"


def _read_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _remove_files(run_dir: str, names: tuple) -> None:
    for name in names:
        try:
            path = os.path.join(run_dir, name)
            os.unlink(path)
        except OSError:
            pass


def _write_record(run_dir: str, record: dict) -> None:
    """run.json written atomically with the private file mode; the sweep's only file."""
    cache_write_text(os.path.join(run_dir, HOST_FILES["run"]), json.dumps(record),
                     mode=FILE_MODE)


def _read_run_record(run_dir: str) -> dict | None:
    """run.json read the way the runner's readRunRecord reads it: no symlink, a regular
    file of at most RUN_RECORD_MAX_BYTES, a JSON object."""
    try:
        fd = os.open(os.path.join(run_dir, HOST_FILES["run"]), os.O_RDONLY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if not S_ISREG(info.st_mode) or info.st_size > RUN_RECORD_MAX_BYTES:
                return None
            data = os.read(fd, RUN_RECORD_MAX_BYTES + 1)
            if len(data) > RUN_RECORD_MAX_BYTES:
                return None
            record = json.loads(data.decode("utf-8"))
        finally:
            os.close(fd)
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) else None


def live_launcher_pid(pane: dict, alive_fn: Callable[[int], bool] = pid_alive) -> int | None:
    """The pane launcher's pid from run.json while it is alive, else None: no run dir, no
    record, no pid, or a launcher that ended (it exits after PANE_IDLE_S without a round)."""
    run_dir = pane.get("run_dir")
    if not isinstance(run_dir, str) or not run_dir:
        return None
    record = _read_run_record(run_dir)
    pid = record.get("launcher_pid") if isinstance(record, dict) else None
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0 or not alive_fn(pid):
        return None
    return pid


def _make_run_dir(run_dir: str, token: str) -> str | None:
    """Create the private run directory, or the refusal reason when it cannot."""
    try:
        os.makedirs(os.path.dirname(run_dir), mode=DIR_MODE, exist_ok=True)
        os.mkdir(run_dir, DIR_MODE)
    except FileExistsError:
        return f"run directory exists: {token}"
    except OSError as exc:
        return f"state home cannot be created: {exc.strerror}"
    os.chmod(run_dir, DIR_MODE)
    return None


def _keep_record_only(run_dir: str) -> None:
    """Remove every file but run.json: the launcher loop ends, the sweep can still close."""
    try:
        names = os.listdir(run_dir)
    except OSError:
        return
    for name in names:
        if name != HOST_FILES["run"]:
            _remove_files(run_dir, (name,))


def _drop_round(run_dir: str) -> None:
    """Drop the round's files so a late launcher starts nothing and no secret stays behind."""
    _remove_files(run_dir, (ROUND_FILE, HOST_FILES["env"], HOST_FILES["prompt"]))


def _create_tab(binary: str, label: str, cwd: str, env: dict, active: PaneSeams) -> tuple:
    """(exit code, tab id, pane id) of a tab create; ids only when they match HOST_ID_RE."""
    created = _herdr_call(binary, "tab create",
                          ["--label", label, "--no-focus", "--cwd", cwd], env, active.run_fn)
    if created is None:
        return None, None, None
    try:
        parsed = json.loads(created.stdout)
        tab_id = parsed["result"]["tab"]["tab_id"]
        pane_id = parsed["result"]["root_pane"]["pane_id"]
    except (ValueError, KeyError, TypeError):
        return created.returncode, None, None
    if not isinstance(tab_id, str) or HOST_ID_RE.fullmatch(tab_id) is None:
        tab_id = None
    if not isinstance(pane_id, str) or HOST_ID_RE.fullmatch(pane_id) is None:
        pane_id = None
    return created.returncode, tab_id, pane_id


def _host_tab(binary: str, cwd: str, env: dict, record: dict, active: PaneSeams) -> tuple:
    """(pane, reason): the pane dict with its tab ids, or None and the refusal reason."""
    run_dir = run_dir_for(env, record["token"])
    code, tab_id, pane_id = _create_tab(binary, record["label"], cwd, env, active)
    if code is not None and code != 0:
        shutil.rmtree(run_dir, ignore_errors=True)
        return None, f"tab create failed (exit {code})"
    if tab_id is None:
        _keep_record_only(run_dir)
        return None, "tab create answer lost; kept the run record for the sweep"
    pane = {"token": record["token"], "tab_id": tab_id, "pane_id": pane_id, "run_dir": run_dir}
    if pane_id is None:
        close_pane(pane, env, active)
        return None, "tab create failed (no pane id in its answer)"
    record["tab_id"] = tab_id
    record["pane_id"] = pane_id
    _write_record(run_dir, record)
    return pane, None


def _await_pid(run_dir: str, active: PaneSeams) -> tuple:
    """(pid, pgid) once the launcher's pid file lands, (None, None) after the grace window."""
    deadline = active.time_fn() + PANE_PID_GRACE_S
    pid_path = os.path.join(run_dir, HOST_FILES["pid"])
    pid = None
    while active.time_fn() < deadline:
        text = _read_file(pid_path)
        if re.fullmatch(r"\d+\n?", text) is not None:
            pid = int(text)
            break
        active.sleep_fn(POLL_S)
    if pid is None:
        return None, None
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return None, None
    return pid, pgid


def _host_launcher(binary: str, pane: dict, env: dict, record: dict,
                   active: PaneSeams) -> str | None:
    """Type the launcher into the pane and record its pid, pgid and start, or the reason."""
    run_dir = pane["run_dir"]
    _herdr_call(binary, "pane run",
                [pane["pane_id"], typed_line(os.path.join(run_dir, HOST_FILES["launcher"]))],
                env, active.run_fn)
    pid, pgid = _await_pid(run_dir, active)
    if pid is None:
        close_pane(pane, env, active)
        return "the launcher wrote no pid within 5 s"
    record["launcher_pid"] = pid
    record["launcher_pgid"] = pgid
    record["launcher_start"] = proc_start_time(pid)
    _write_record(run_dir, record)
    return None


def open_pane(role: str, runtime: str, cwd: str, env: dict | None = None,
              seams: PaneSeams | None = None) -> dict | None:
    """Open the lane's reused pane on the hosted-lane protocol, or refuse with one line."""
    active = seams or DEFAULT_SEAMS
    env = dict(os.environ) if env is None else env
    binary, why = herdr_available(env, active.which_fn)
    if binary is None:
        return _refuse(why)
    token = active.token_fn()
    label = pane_label(role, runtime, token)
    if (TOKEN_RE.fullmatch(token) is None or LABEL_RE.fullmatch(label) is None
            or len(label) > LABEL_MAX):
        return _refuse(f"label outside the protocol: {label}")
    run_dir = run_dir_for(env, token)
    problem = pane_problem(run_dir)
    if problem is not None:
        return _refuse(problem)
    reason = _make_run_dir(run_dir, token)
    if reason is not None:
        return _refuse(reason)
    record = {
        "version": RUN_RECORD_VERSION,
        "token": token,
        "runner_pid": os.getpid(),
        "runner_start": proc_start_time(os.getpid()),
        "host_name": os.uname().nodename,
        "checkout_root": os.path.realpath(cwd),
        "role": role,
        "runtime": runtime,
        "label": label,
        "tab_id": None,
        "pane_id": None,
        "launcher_pid": None,
        "launcher_pgid": None,
        "launcher_start": None,
        "created_ms": int(time.time() * 1000),
    }
    _write_record(run_dir, record)
    cache_write_text(os.path.join(run_dir, HOST_FILES["launcher"]),
                     launcher_text(run_dir, token), mode=FILE_MODE)
    pane, reason = _host_tab(binary, cwd, env, record, active)
    if reason is None:
        reason = _host_launcher(binary, pane, env, record, active)
    if reason is not None:
        return _refuse(reason)
    return pane


def _retire(run_dir: str, active: PaneSeams) -> None:
    """Signal the verified launcher group (the runner's finalize rule): SIGTERM, then
    SIGKILL when it outlives KILL_GRACE_S."""
    record = _read_run_record(run_dir) or {}
    pid = record.get("launcher_pid")
    pgid = record.get("launcher_pgid")
    start = record.get("launcher_start")
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 1:
        return
    if not isinstance(pgid, int) or pgid != pid or pgid == os.getpgid(0):
        return
    if not isinstance(start, str) or start == "-" or start != active.start_fn(pid):
        return
    try:
        active.killpg_fn(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = active.time_fn() + KILL_GRACE_S
    while active.alive_fn(pid) and active.time_fn() < deadline:
        active.sleep_fn(POLL_S)
    if active.alive_fn(pid):
        with contextlib.suppress(ProcessLookupError):
            active.killpg_fn(pgid, signal.SIGKILL)


def _abandon(pane: dict, run_dir: str, active: PaneSeams, end: str) -> str:
    """Drop the round files, retire the launcher group and mark the pane closed; returns end."""
    _drop_round(run_dir)
    _retire(run_dir, active)
    pane["closed"] = True
    return end


def run_round(pane: dict, job: PaneRound, seams: PaneSeams | None = None) -> str:
    """Run one round through the pane's launcher loop and wait for its rc file."""
    active = seams or DEFAULT_SEAMS
    run_dir = pane["run_dir"]
    if pane.get("closed"):
        return "launcher gone"
    pid = live_launcher_pid(pane, active.alive_fn)
    if pid is None:
        return _abandon(pane, run_dir, active, "launcher gone")
    _remove_files(run_dir, (HOST_FILES["out"], HOST_FILES["err"], HOST_FILES["rc"]))
    cache_write_text(os.path.join(run_dir, HOST_FILES["env"]),
                     _env_text(job.env if job.env is not None else child_env()),
                     mode=FILE_MODE)
    cache_write_text(os.path.join(run_dir, HOST_FILES["prompt"]), job.prompt, mode=FILE_MODE)
    cache_write_text(os.path.join(run_dir, ROUND_FILE), _round_text(run_dir, job),
                     mode=FILE_MODE)
    return _await_round(pane, pid, active.time_fn() + job.timeout_s, active)


def _round_done(run_dir: str) -> bool:
    """True when the round's launcher finished: round.sh is gone and an rc file landed."""
    return (not os.path.exists(os.path.join(run_dir, ROUND_FILE))
            and bool(_read_file(os.path.join(run_dir, HOST_FILES["rc"]))))


def _await_round(pane: dict, pid: int, deadline: float, active: PaneSeams) -> str:
    """Poll the rc file until the round ends; the round files are dropped on an abandon."""
    run_dir = pane["run_dir"]
    while True:
        if _round_done(run_dir):
            return "rc"
        if not active.alive_fn(pid):
            if _round_done(run_dir):
                return "rc"
            return _abandon(pane, run_dir, active, "launcher gone")
        if active.time_fn() >= deadline:
            return _abandon(pane, run_dir, active, "timeout")
        active.sleep_fn(POLL_S)


def read_verdict(run_dir: str) -> dict | None:
    """The round's verdict from its rc, out and err files only; herdr is never read."""
    text = _read_file(os.path.join(run_dir, HOST_FILES["rc"]))
    body = text[:-1] if text.endswith("\n") else text
    if body == "":
        return None
    verdict: dict[str, Any] = {"code": None, "signal": None, "bad": None}
    if RC_RE.fullmatch(body) is None:
        verdict["bad"] = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", body.split("\n")[0])[:80]
    elif body.isdigit():
        verdict["code"] = int(body)
    else:
        verdict["signal"] = body
    verdict["out"] = _read_file(os.path.join(run_dir, HOST_FILES["out"]))
    verdict["status"] = _last_status(os.path.join(run_dir, HOST_FILES["err"]))
    verdict["err_tail"] = _read_file(
        os.path.join(run_dir, HOST_FILES["err"]))[-STDERR_TAIL_CHARS:]
    return verdict


def _last_status(err_path: str) -> dict | None:
    """parse_status_line of the last err line that starts with the status prefix."""
    for line in reversed(_read_file(err_path).splitlines()):
        if line.startswith("AIKIT-XAI "):
            return parse_status_line(line)
    return None


def pane_spawn(pane: dict, seams: PaneSeams | None = None) -> Callable[..., Any]:
    """The spawn seam run_runner calls for a pane round; the runner argv, deadline, env,
    trailer check and reason stay run_runner's."""

    def spawn(request: runner_dispatch.SpawnRequest,
              runner_seams: runner_dispatch.RunnerSeams) -> runner_dispatch.RunnerResult:
        try:
            job = PaneRound(
                list(request.argv), request.prompt, request.cwd or os.getcwd(),
                int(request.deadline_s),
                runner_dispatch.child_env(env=runner_seams.env_fn()),
            )
            end = run_round(pane, job, seams)
            if end == "launcher gone":
                raise OSError("pane launcher gone")
            verdict = (read_verdict(pane["run_dir"]) or {}) if end == "rc" else {}
            err_tail = verdict.get("err_tail")
            if not err_tail:
                err_tail = _read_file(
                    os.path.join(pane["run_dir"], HOST_FILES["err"]))[-STDERR_TAIL_CHARS:]
            for line in err_tail.splitlines():
                runner_seams.print_fn(line)
            if end == "timeout":
                return runner_dispatch.RunnerResult(
                    None, "", None, None, True, list(request.argv), err_tail)
            return runner_dispatch.RunnerResult(
                verdict.get("code"), verdict.get("out", ""), verdict.get("status"),
                None, False, list(request.argv), err_tail)
        finally:
            runner_dispatch.reap_recorded_groups(request.pgid_file, runner_seams)

    return spawn


def _owned_record(pane: dict, run_dir: str, env: dict) -> dict | None:
    """run.json when the run dir and record prove this pane owns them, else None."""
    token = pane.get("token")
    if (not isinstance(token, str) or TOKEN_RE.fullmatch(token) is None
            or run_dir != run_dir_for(env, token)):
        return None
    try:
        info = os.lstat(run_dir)
    except OSError:
        return None
    if not S_ISDIR(info.st_mode):
        return None
    record = _read_run_record(run_dir)
    if record is None or record.get("token") != token:
        return None
    label = record.get("label")
    if (not isinstance(label, str) or LABEL_RE.fullmatch(label) is None
            or not label.endswith(":" + token)
            or record.get("host_name") != os.uname().nodename):
        return None
    return record


def _tab_listed(binary: str, tab_id: str, label: str, env: dict, active: PaneSeams) -> bool:
    """True only when herdr's tab list shows this tab id under this label (the sweep match)."""
    result = _herdr_call(binary, "tab list", [], env, active.run_fn)
    if result is None or result.returncode != 0:
        return False
    try:
        tabs = json.loads(result.stdout)["result"]["tabs"]
    except (ValueError, KeyError, TypeError):
        return False
    if not isinstance(tabs, list):
        return False
    for tab in tabs:
        if isinstance(tab, dict) and tab.get("tab_id") == tab_id and tab.get("label") == label:
            return True
    return False


def close_pane(pane: dict, env: dict | None = None, seams: PaneSeams | None = None) -> bool:
    """Close the pane's tab and remove the run dir, keeping run.json when unconfirmed."""
    active = seams or DEFAULT_SEAMS
    run_dir = pane.get("run_dir") or ""
    live_env = env or dict(os.environ)
    record = _owned_record(pane, run_dir, live_env)
    if record is None:
        return False
    tab_id = pane.get("tab_id")
    if not isinstance(tab_id, str) or HOST_ID_RE.fullmatch(tab_id) is None:
        _retire(run_dir, active)
        shutil.rmtree(run_dir, ignore_errors=True)
        return True
    binary, _ = herdr_available(live_env, active.which_fn)
    if binary is None:
        _keep_record_only(run_dir)
        return False
    if not _tab_listed(binary, tab_id, record["label"], live_env, active):
        _keep_record_only(run_dir)
        return False
    _retire(run_dir, active)
    result = _herdr_call(binary, "tab close", [tab_id], live_env, active.run_fn)
    if result is not None and (result.returncode == 0 or _herdr_code(result) == "tab_not_found"):
        shutil.rmtree(run_dir, ignore_errors=True)
        return True
    _keep_record_only(run_dir)
    return False
