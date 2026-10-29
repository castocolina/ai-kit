"""Host-process liveness (D-08 as amended by spike 001, item 7).

A process counts as alive only when the pid exists, its start time matches,
and the boot id matches. `comm`, `exe` and `cmdline` are never compared: the
host's `comm` is its version string (`2.1.299`), which changes on auto-update.
"""
import os
import shutil
import subprocess
from typing import NamedTuple

from .state import Seams


class ProcIdentity(NamedTuple):
    """What could be observed about one pid, and where it came from."""

    pid: int
    start: str
    boot_id: str | None
    source: str


def _read_boot_id(proc_root: str) -> str | None:
    try:
        boot = os.path.join(proc_root, "sys", "kernel", "random", "boot_id")
        with open(boot, encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return None


def _stat_start(proc_root: str, pid: int) -> str | None:
    """Field 22 (`starttime`): the 20th field after the last `)`."""
    try:
        stat_file = os.path.join(proc_root, str(pid), "stat")
        with open(stat_file, encoding="utf-8", errors="replace") as handle:
            stat = handle.read()
    except OSError:
        return None
    try:
        return stat[stat.rindex(")") + 2 :].split()[19]
    except (ValueError, IndexError):
        return None


def _ps_identity(pid: int, seams: Seams) -> ProcIdentity | None:
    """Fallback when no proc tree exists: `ps -o lstart=`, unverified (D-08)."""
    ps = shutil.which("ps", path=seams.env.get("PATH", ""))
    if ps is None:
        return None
    try:
        proc = subprocess.run(
            [ps, "-o", "lstart=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=dict(seams.env),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    line = proc.stdout.strip()
    if proc.returncode != 0 or not line:
        return None
    return ProcIdentity(pid, line, None, "ps-unverified")


def identify(pid: int, seams: Seams) -> ProcIdentity | None:
    """Identity of `pid`, or None when it does not exist.

    `<proc_root>/<pid>/stat` start time plus `<proc_root>` boot id, source
    `proc`; when the proc tree is absent, the `ps` fallback with boot_id None
    and source `ps-unverified`.
    """
    start = _stat_start(seams.proc_root, pid)
    if start is not None:
        return ProcIdentity(pid, start, _read_boot_id(seams.proc_root), "proc")
    if os.path.isdir(seams.proc_root):
        return None
    return _ps_identity(pid, seams)


def is_alive(state: dict, seams: Seams) -> bool:
    """True only when the recorded pid exists with the recorded start time and
    boot id (D-08; no `comm` check)."""
    identity = identify(int(state["pid"]), seams)
    if identity is None:
        return False
    return identity.start == str(state["pid_start"]) and identity.boot_id == state["boot_id"]


def launch_cwd(pid: int, seams: Seams) -> tuple[str, bool]:
    """The process's working directory and whether it could be verified.

    A `(deleted)` suffix or an unreadable link degrades to this process's cwd,
    unverified (D-09).
    """
    try:
        target = os.readlink(os.path.join(seams.proc_root, str(pid), "cwd"))
    except OSError:
        return os.getcwd(), False
    if target.endswith(" (deleted)"):
        return os.getcwd(), False
    return target, True


def read_cmdline(pid: int, seams: Seams) -> list[str] | None:
    """The process's argv, or None when it cannot be read (the permission-mode
    copy at arm reads this; 26-04 consumes it)."""
    try:
        with open(os.path.join(seams.proc_root, str(pid), "cmdline"), "rb") as handle:
            raw = handle.read()
    except OSError:
        return None
    if not raw:
        return None
    return [part.decode("utf-8", "replace") for part in raw.split(b"\0") if part]
