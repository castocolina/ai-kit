"""Fakes and scratch-env helpers for the session-wake tests (D-26).

Everything runs on a scratch root: PATH holds only `<root>/bin`, the HOME and
XDG dirs sit under `<root>/home`, and every fake appends one JSON log line to
`$AI_KIT_FAKE_LOG`. No real systemd, no real host CLI, no real home.
"""

import json
import os
import shutil
import subprocess
import sys

from ai_kit_session_wake.state import Seams

# The shared fake prelude: append one JSON line describing this call. When
# AI_KIT_FAKE_LOG is absent the line is skipped (26-04 gives the prelude a
# log-path fallback beside the fake's bin dir; this plan's prelude is
# unchanged by that review disposition).
_PRELUDE = """import json, os, sys
_log = os.environ.get("AI_KIT_FAKE_LOG") or os.path.join(
    os.path.dirname(os.path.dirname(sys.argv[0])), "fake.log"
)
if _log:
    with open(_log, "a", encoding="utf-8") as _handle:
        _handle.write(json.dumps({
            "name": __FAKE_NAME__,
            "argv": sys.argv[1:],
            "cwd": os.getcwd(),
            "env_names": sorted(os.environ),
            "stdin_null": os.readlink("/proc/self/fd/0") == "/dev/null",
        }) + "\\n")
"""


def scoped_env(root: str) -> dict[str, str]:
    """A scratch env whose PATH is `<root>/bin` only and whose HOME and XDG
    dirs live under `<root>/home`; never a copy of os.environ."""
    home = os.path.join(root, "home")
    return {
        "PATH": os.path.join(root, "bin"),
        "HOME": home,
        "XDG_CONFIG_HOME": os.path.join(home, ".config"),
        "XDG_STATE_HOME": os.path.join(home, ".local", "state"),
        "XDG_DATA_HOME": os.path.join(home, ".local", "share"),
        "XDG_CACHE_HOME": os.path.join(home, ".cache"),
        "USER": "wake-test",
        "AI_KIT_FAKE_LOG": os.path.join(root, "fake.log"),
    }


def doc_block_env(root: str, commands: list[str]) -> dict[str, str]:
    """The env for running a SKILL.md bash block (26-10, plan-checker blocker).

    PATH is `<root>/bin` first (the fake systemctl, loginctl and notify-send, plus a
    `python3` wrapper that execs this interpreter), then `<root>/tools`, which holds one
    symlink per name in `commands` and nothing else: never a system directory, so the
    real `systemctl --user` is unreachable. HOME and XDG dirs are the scratch ones."""
    env = scoped_env(root)
    bin_dir = os.path.join(root, "bin")
    tools_dir = os.path.join(root, "tools")
    os.makedirs(tools_dir, exist_ok=True)
    fake_systemctl(bin_dir)
    fake_loginctl(bin_dir)
    fake_notify_send(bin_dir)
    wrapper = os.path.join(bin_dir, "python3")
    with open(wrapper, "w", encoding="utf-8") as handle:
        handle.write(
            f"#!{sys.executable}\n"
            "import os, sys\n"
            f"os.execv({sys.executable!r}, [{sys.executable!r}] + sys.argv[1:])\n"
        )
    os.chmod(wrapper, 0o755)
    for name in commands:
        target = shutil.which(name)
        if target is None:
            raise RuntimeError(f"doc block needs {name!r}, which does not resolve")
        link = os.path.join(tools_dir, name)
        if not os.path.lexists(link):
            os.symlink(target, link)
    env["PATH"] = os.pathsep.join([bin_dir, tools_dir])
    for name in ("systemctl", "loginctl", "notify-send"):
        resolved = shutil.which(name, path=env["PATH"])
        if resolved is None or not resolved.startswith(bin_dir + os.sep):
            raise RuntimeError(f"{name} must resolve under the scratch bin dir, got {resolved!r}")
    return env


def write_fake(bin_dir: str, name: str, body: str, shebang: str | None = None) -> str:
    """Write an executable fake named `name` (shebang = this interpreter by default)."""
    os.makedirs(bin_dir, exist_ok=True)
    path = os.path.join(bin_dir, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(f"{shebang or f'#!{sys.executable}'}\n")
        handle.write(_PRELUDE.replace("__FAKE_NAME__", repr(name)))
        handle.write(body)
    os.chmod(path, 0o755)
    return path


_SYSTEMCTL_BODY = """
_argv = sys.argv[2:]
if _argv[:2] == ["show", "-p"]:
    if os.environ.get("FAKE_SYSTEMCTL_DOWN"):
        sys.exit(1)
    print("Version=259")
    sys.exit(0)
if _argv[:1] == ["is-active"]:
    print("active")
_fail = os.environ.get("FAKE_SYSTEMCTL_FAIL", "")
if _fail and _argv[0] == _fail:
    print("fake systemctl: failed " + " ".join(_argv), file=sys.stderr)
    sys.exit(1)
if os.environ.get("FAKE_SYSTEMCTL_PARTIAL") == "enable" and _argv[0] == "enable":
    _unit = _argv[-1]
    _base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.environ["HOME"], ".config")
    _user_dir = os.path.join(_base, "systemd", "user")
    _wants = os.path.join(_user_dir, "timers.target.wants")
    os.makedirs(_wants, exist_ok=True)
    os.symlink(os.path.join(_user_dir, _unit), os.path.join(_wants, _unit))
    print("fake systemctl: failed " + " ".join(_argv), file=sys.stderr)
    sys.exit(1)
sys.exit(0)
"""

_LOGINCTL_BODY = """
print(os.environ.get("FAKE_LINGER", "yes"))
"""

_HOST_BODY = """
_fire = os.environ.get("AI_KIT_SESSION_WAKE_FIRE", "")
_shim = os.environ.get("FAKE_WAKE_SHIM", "")
if os.environ.get("FAKE_WAKE_DONE") and _fire and _shim:
    _host, _, _sid = _fire.partition("-")
    subprocess.run(
        [sys.executable, _shim, "done", "--host", _host, "--session-id", _sid],
        check=False, stdout=subprocess.DEVNULL,
    )
if os.environ.get("FAKE_HOST_MODE") == "arm":
    _proc = subprocess.run(
        [sys.executable, os.environ["FAKE_WAKE_SHIM"], "arm", "--host",
         os.environ["FAKE_WAKE_HOST"], "--session-id", os.environ["FAKE_WAKE_SID"]],
        capture_output=True, text=True, env=dict(os.environ),
    )
    with open(os.environ["AI_KIT_FAKE_LOG"], "a", encoding="utf-8") as _handle:
        _handle.write(json.dumps({
            "name": "arm-child", "returncode": _proc.returncode,
            "stdout": _proc.stdout, "stderr": _proc.stderr,
        }) + "\\n")
    sys.exit(_proc.returncode)
if os.environ.get("FAKE_HOST_SLEEP"):
    time.sleep(float(os.environ["FAKE_HOST_SLEEP"]))
sys.exit(int(os.environ.get("FAKE_HOST_EXIT", "0")))
"""


def fake_systemctl(bin_dir: str) -> str:
    """A fake systemctl: `show -p Version` prints Version=259 unless
    FAKE_SYSTEMCTL_DOWN is set (then exit 1); `is-active` prints active;
    everything else exits 0. FAKE_SYSTEMCTL_FAIL=<verb> makes the verb exit 1
    with a stderr line (the rollback tests); FAKE_SYSTEMCTL_PARTIAL=enable
    first creates the wants symlink for the unit, then exits 1 (a partial
    `enable --now` the rollback must undo)."""
    return write_fake(bin_dir, "systemctl", "import os, sys\n" + _SYSTEMCTL_BODY)


def fake_loginctl(bin_dir: str) -> str:
    """A fake loginctl printing $FAKE_LINGER (default yes)."""
    return write_fake(bin_dir, "loginctl", "import os, sys\n" + _LOGINCTL_BODY)


def fake_host(bin_dir: str, name: str) -> str:
    """A fake host CLI. With FAKE_HOST_MODE=arm it runs the shim's `arm` as its
    own child (so it is the arm process's ancestor), logs the child's exit code
    and output, and exits with it. FAKE_HOST_SLEEP=<seconds> sleeps that long
    before exiting (so a resumed fake host keeps its fire's lock held for a
    known span); FAKE_HOST_EXIT=<code> sets the exit code."""
    return write_fake(bin_dir, name, "import json, os, subprocess, sys, time\n" + _HOST_BODY)


_NOTIFY_BODY = """
if os.environ.get("FAKE_NOTIFY_SLEEP"):
    time.sleep(float(os.environ["FAKE_NOTIFY_SLEEP"]))
if os.environ.get("FAKE_NOTIFY_FAIL"):
    sys.exit(1)
sys.exit(0)
"""


def fake_notify_send(bin_dir: str) -> str:
    """A fake notify-send that logs its call; FAKE_NOTIFY_FAIL makes it exit 1,
    FAKE_NOTIFY_SLEEP=<s> sleeps that long before anything else."""
    return write_fake(bin_dir, "notify-send", "import os, sys, time\n" + _NOTIFY_BODY)


def hold_lock(path: str, seconds: float) -> subprocess.Popen:
    """A helper process that takes the flock on `path`, prints `locked` once
    it holds it (the caller waits for that line before acting), and exits
    after `seconds`. The caller owns the process and kills it in cleanup."""
    script = (
        "import fcntl, os, sys, time\n"
        "fd = os.open(sys.argv[1], os.O_RDONLY)\n"
        "fcntl.flock(fd, fcntl.LOCK_EX)\n"
        "print('locked', flush=True)\n"
        "time.sleep(float(sys.argv[2]))\n"
    )
    return subprocess.Popen(
        [sys.executable, "-c", script, path, str(seconds)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def codex_session(home: str, sid: str) -> str:
    """A codex rollout file for `sid` in the unverified help-derived layout."""
    directory = os.path.join(home, ".codex", "sessions", "2026", "10", "25")
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"rollout-2026-10-25T10-00-00-{sid}.jsonl")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("{}\n")
    return path


def fake_opencode(bin_dir: str) -> str:
    """A fake opencode whose fixtures sit beside it (the service env the probe
    runs under drops env variables): `<bin>/opencode-sessions.json` is printed
    cut to the given --max-count, `<bin>/opencode-list-fail` makes it exit 1."""
    body = """
_here = os.path.dirname(os.path.realpath(__file__))
if os.path.exists(os.path.join(_here, "opencode-list-fail")):
    sys.exit(1)
_count = 10000
if "--max-count" in sys.argv:
    _count = int(sys.argv[sys.argv.index("--max-count") + 1])
try:
    with open(os.path.join(_here, "opencode-sessions.json"), encoding="utf-8") as _h:
        _data = json.load(_h)
    print(json.dumps(_data[:_count]))
except Exception:
    with open(os.path.join(_here, "opencode-sessions.json"), encoding="utf-8") as _h:
        sys.stdout.write(_h.read())
"""
    return write_fake(bin_dir, "opencode", "import json, os, sys\n" + body)


def pi_session(home: str, sid: str) -> str:
    directory = os.path.join(home, ".pi", "agent", "sessions", "--scratch--")
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"2026-10-25_{sid}.jsonl")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("{}\\n")
    return path


# A stub shim for the executor blocks (26-10): logs its argv, then mirrors the real `arm`
# contract. STUB_HOST is the host it arms for; pi and opencode refuse without --session-id
# (exit 2, the real refusal text). STUB_ARM_OUTPUT overrides the printed line (for example
# `refreshed`); STUB_ARM_RC overrides the exit code. `done` and `disarm` log and exit 0.
_STUB_SHIM_BODY = """
import json, os, sys
_argv = sys.argv[1:]
_log = os.environ["AI_KIT_FAKE_LOG"]
with open(_log, "a", encoding="utf-8") as _handle:
    _handle.write(json.dumps({"name": "shim", "argv": _argv}) + "\\n")
if not _argv or _argv[0] != "arm":
    sys.exit(0)
_host = os.environ.get("STUB_HOST", "claude")
_sid = ""
if "--session-id" in _argv:
    _sid = _argv[_argv.index("--session-id") + 1]
if _host in ("pi", "opencode") and not _sid:
    print("ai-kit-session-wake: no session id: pass --session-id", file=sys.stderr)
    sys.exit(2)
_sid = _sid or os.environ.get("STUB_SID", "stub-session")
_out = os.environ.get("STUB_ARM_OUTPUT") or f"armed {_host}-{_sid}"
print(_out.replace("{id}", _sid))
sys.exit(int(os.environ.get("STUB_ARM_RC", "0")))
"""


def stub_shim(path: str) -> str:
    """Write the stub shim at `path` (creating its directory) and return the path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(f"#!{sys.executable}\n" + _STUB_SHIM_BODY)
    os.chmod(path, 0o755)
    return path


def read_log(path: str) -> list[dict]:
    """Parse the fake log's JSON lines."""
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def start_host_process(cwd: str):
    """A real `sleep 120` stand-in for the host process, started in `cwd`.
    The caller kills it via addCleanup."""
    sleep = shutil.which("sleep")
    if sleep is None:
        raise RuntimeError("no sleep binary for the host stand-in")
    return subprocess.Popen(
        [sleep, "120"],
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def fixed_seams(env: dict[str, str], now: float) -> Seams:
    """Seams whose clock always reads `now`."""
    return Seams(env=env, now=lambda: now)


def claude_session(home: str, sid: str) -> str:
    """A claude transcript for `sid` in the reverse-engineered layout."""
    project = os.path.join(home, ".claude", "projects", "-scratch")
    os.makedirs(project, exist_ok=True)
    path = os.path.join(project, f"{sid}.jsonl")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write('{"fake": true}\n')
    return path
