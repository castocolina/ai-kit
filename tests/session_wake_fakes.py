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
_PRELUDE = '''import json, os, sys
_log = os.environ.get("AI_KIT_FAKE_LOG")
if _log:
    with open(_log, "a", encoding="utf-8") as _handle:
        _handle.write(json.dumps({
            "name": __FAKE_NAME__,
            "argv": sys.argv[1:],
            "cwd": os.getcwd(),
            "env_names": sorted(os.environ),
            "stdin_null": os.readlink("/proc/self/fd/0") == "/dev/null",
        }) + "\\n")
'''


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


def write_fake(bin_dir: str, name: str, body: str) -> str:
    """Write an executable fake named `name` (shebang = this interpreter)."""
    os.makedirs(bin_dir, exist_ok=True)
    path = os.path.join(bin_dir, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(f"#!{sys.executable}\n")
        handle.write(_PRELUDE.replace("__FAKE_NAME__", repr(name)))
        handle.write(body)
    os.chmod(path, 0o755)
    return path


_SYSTEMCTL_BODY = """
_argv = sys.argv[1:]
if _argv[1:3] == ["show", "-p"]:
    if os.environ.get("FAKE_SYSTEMCTL_DOWN"):
        sys.exit(1)
    print("Version=259")
    sys.exit(0)
if _argv[:1] == ["is-active"]:
    print("active")
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
"""


def fake_systemctl(bin_dir: str) -> str:
    """A fake systemctl: `show -p Version` prints Version=259 unless
    FAKE_SYSTEMCTL_DOWN is set (then exit 1); `is-active` prints active;
    everything else exits 0."""
    return write_fake(bin_dir, "systemctl", "import os, sys\n" + _SYSTEMCTL_BODY)


def fake_loginctl(bin_dir: str) -> str:
    """A fake loginctl printing $FAKE_LINGER (default yes)."""
    return write_fake(bin_dir, "loginctl", "import os, sys\n" + _LOGINCTL_BODY)


def fake_host(bin_dir: str, name: str) -> str:
    """A fake host CLI; with FAKE_WAKE_DONE set it runs the shim's `done` for
    the session named by AI_KIT_SESSION_WAKE_FIRE."""
    return write_fake(bin_dir, name, "import os, subprocess, sys\n" + _HOST_BODY)


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
