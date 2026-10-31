"""The systemd user units (D-12, D-13) and their systemctl seam.

Everything here runs through `Seams`: the unit dir and the service env come
from `seams.env`, and `systemctl` resolves on the seams PATH so tests drive
fakes (D-26). `ExecStart` words are quoted with backslash, double quote, `%`
and `$` escaped; there is no shell anywhere (T-26-03).
"""

import os
import shutil
import subprocess
from collections.abc import Mapping
from typing import NamedTuple

from .state import Seams

UNIT_PREFIX = "ai-kit-session-wake"

# D-13: the service env carries PATH, HOME and the four XDG base dirs -- names
# only when set, never the rest of the arm-time environment.
_SERVICE_ENV_KEYS = (
    "PATH",
    "HOME",
    "XDG_CONFIG_HOME",
    "XDG_STATE_HOME",
    "XDG_DATA_HOME",
    "XDG_CACHE_HOME",
)


class UnitNames(NamedTuple):
    timer: str
    service: str


def unit_names(host: str, sid: str) -> UnitNames:
    """`ai-kit-session-wake-<host>-<id>.timer` and `.service` (D-12)."""
    return UnitNames(f"{UNIT_PREFIX}-{host}-{sid}.timer", f"{UNIT_PREFIX}-{host}-{sid}.service")


def unit_dir(env: Mapping[str, str]) -> str:
    """`${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user`."""
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
    return os.path.join(base, "systemd", "user")


def stamp_path(env: Mapping[str, str], timer: str) -> str:
    """The persistent timer's stamp:
    `${XDG_DATA_HOME:-$HOME/.local/share}/systemd/timers/stamp-<timer>`."""
    data = env.get("XDG_DATA_HOME") or os.path.join(env.get("HOME", ""), ".local", "share")
    return os.path.join(data, "systemd", "timers", f"stamp-{timer}")


def _escape(word: str) -> str:
    """Escape one word for a quoted systemd value: backslash and double quote
    for the quoting, a newline as `\\n`, `%` (specifiers) doubled. `Environment=`
    values take no variable expansion, so a `$` stays literal there."""
    return (
        word.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("%", "%%")
    )


def _quote(word: str) -> str:
    """One `ExecStart=` word: also `$` doubled, which is variable expansion there."""
    return f'"{_escape(word).replace("$", "$$")}"'


def render_timer(host: str, sid: str, reset_line: str | None = None) -> str:
    """The persistent calendar timer (D-12); `reset_line` adds a second
    absolute `OnCalendar=` beside `hourly` (D-28, written only by a later
    re-arm; `fire` never rewrites units). The line is the full
    `OnCalendar=...` entry (`reset_parse.calendar_line`); a bare time value is
    prefixed for convenience."""
    _timer, service = unit_names(host, sid)
    lines = [
        "[Unit]",
        f"Description=ai-kit session wake ({host} {sid})",
        "[Timer]",
        "OnCalendar=hourly",
    ]
    if reset_line:
        lines.append(
            reset_line if reset_line.startswith("OnCalendar=") else f"OnCalendar={reset_line}"
        )
    lines += [
        "Persistent=true",
        f"Unit={service}",
        "[Install]",
        "WantedBy=timers.target",
        "",
    ]
    return "\n".join(lines)


def service_environment(env: Mapping[str, str]) -> list[tuple[str, str]]:
    """The (key, value) pairs the service env carries, in D-13's order."""
    result = [(key, env[key]) for key in _SERVICE_ENV_KEYS if env.get(key)]
    for index, (key, value) in enumerate(result):
        if key == "PATH":
            filtered = os.pathsep.join(
                item for item in value.split(os.pathsep) if "fnm_multishells" not in item
            )
            result[index] = (key, filtered)
    return result


def render_service(python: str, shim: str, host: str, sid: str, env: Mapping[str, str]) -> str:
    """The oneshot service: absolute `ExecStart` (the python3 that ran arm, the
    shim, `fire --host <host> --session-id <sid>`), one Environment= pair per
    `service_environment` entry (D-13)."""
    argv = [python, shim, "fire", "--host", host, "--session-id", sid]
    env_lines = [
        f'Environment="{_escape(key)}={_escape(value)}"' for key, value in service_environment(env)
    ]
    lines = [
        "[Unit]",
        f"Description=ai-kit session wake service ({host} {sid})",
        "[Service]",
        "Type=oneshot",
        *env_lines,
        f"ExecStart={' '.join(_quote(word) for word in argv)}",
        "",
    ]
    return "\n".join(lines)


def systemctl(seams: Seams, *args: str) -> subprocess.CompletedProcess:
    """`systemctl --user <args>` with the seams env, 30 s timeout. A missing
    systemctl is returned as a 127 CompletedProcess, never raised."""
    exe = shutil.which("systemctl", path=seams.env.get("PATH", ""))
    if exe is None:
        return subprocess.CompletedProcess(
            ["systemctl", "--user", *args], 127, "", "systemctl not found on PATH"
        )
    return subprocess.run(
        [exe, "--user", *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env=dict(seams.env),
    )


def systemd_available(seams: Seams) -> bool:
    """A systemctl on the seams PATH whose `show -p Version` exits 0."""
    if shutil.which("systemctl", path=seams.env.get("PATH", "")) is None:
        return False
    return systemctl(seams, "show", "-p", "Version").returncode == 0


def linger_enabled(seams: Seams, linger_dir: str = "/var/lib/systemd/linger") -> bool | None:
    """Whether the user's linger is on: `loginctl show-user <user> -p Linger
    --value`, falling back to `/var/lib/systemd/linger/<user>`; None when
    neither answers. The user comes from the seams env's USER/LOGNAME."""
    user = seams.env.get("USER") or seams.env.get("LOGNAME") or ""
    loginctl = shutil.which("loginctl", path=seams.env.get("PATH", ""))
    if loginctl is not None and user:
        try:
            proc = subprocess.run(
                [loginctl, "show-user", user, "-p", "Linger", "--value"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                env=dict(seams.env),
            )
        except (OSError, subprocess.TimeoutExpired):
            proc = None
        if proc is not None and proc.returncode == 0:
            return proc.stdout.strip() == "yes"
    if user and os.path.exists(os.path.join(linger_dir, user)):
        return True
    return None
