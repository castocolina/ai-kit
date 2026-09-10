"""Chronological cwd-resolution state machine.

Callers MUST call `resolve_for` first, THEN `observe`, per step. That
ordering is an explicit two-call contract so future readers cannot
accidentally invert it: `resolve_for` returns the cwd THIS step itself
runs in, before any `cd` inside this same step takes effect for the NEXT
step. One `CwdState` instance is constructed per session and threaded
across every tool-call in timestamp order — the instance itself carries
cross-call memory.
"""

from __future__ import annotations

import os


class CwdState:
    """Track the running cwd from detected `cd` steps. Never touches the disk."""

    def __init__(self, initial_dir: str) -> None:
        self.current = initial_dir

    def resolve_for(self, step_text: str) -> str:
        """Return `.current` as of this call (cwd THIS step runs in)."""
        del step_text
        return self.current

    def observe(self, step_text: str) -> None:
        """Update `.current` when `step_text` is a `cd <path>` invocation.

        Bare `cd` with no argument is a documented no-op: resolving `$HOME`
        is out of this module's scope (not a case the PRD's own worked
        examples exercise).
        """
        tokens = step_text.strip().split(None, 1)
        if not tokens or tokens[0] != "cd":
            return
        if len(tokens) < 2:
            return
        path = _strip_wrapping_quotes(tokens[1])
        if os.path.isabs(path):
            self.current = os.path.normpath(path)
        else:
            self.current = os.path.normpath(os.path.join(self.current, path))


def _strip_wrapping_quotes(argument: str) -> str:
    if len(argument) >= 2 and argument[0] == argument[-1] and argument[0] in "\"'":
        return argument[1:-1]
    return argument
