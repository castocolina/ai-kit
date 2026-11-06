"""Cursor process probes; imports host-neutral modules only."""
# pyright: strict

import os
from typing import TYPE_CHECKING

from common_probe import (
    probe_ancestor_rss_bytes,
    probe_cmdline_via_proc,
    probe_cmdline_via_ps,
    probe_exe_via_proc,
    probe_has_proc,
    probe_memo,
)

if TYPE_CHECKING:
    from common_render import Context

# ═══ 3. probe_ — side-effecting data gatherers (git / proc / fs / subprocess) ═


def probe_is_cursor(pid: int) -> bool | None:
    """True when pid is the Cursor agent, False when it is not, None when unreadable.

    The program path wins: a `node` under a `/cursor-agent/` directory matches first,
    then a command line naming `cursor-agent`. The process name (comm) is never read,
    because the live agent reports `MainThread` there."""
    if not probe_has_proc():
        cmd = probe_cmdline_via_ps(pid)
        return None if cmd is None else "cursor-agent" in cmd
    exe = probe_exe_via_proc(pid)
    if exe is not None and os.path.basename(exe) == "node" and "/cursor-agent/" in exe:
        return True
    cmd = probe_cmdline_via_proc(pid)
    if exe is None and cmd is None:
        return None
    return "cursor-agent" in (cmd or "")


def probe_cursor_rss_bytes() -> int | None:
    """VmRSS (bytes) of the nearest Cursor agent ancestor, or None (walk depth 12)."""
    return probe_ancestor_rss_bytes(probe_is_cursor, 12)


def probe_cursor_rss(ctx: "Context") -> int | None:
    """Memoized Cursor agent RSS for this render."""
    return probe_memo(ctx, "rss", probe_cursor_rss_bytes)
