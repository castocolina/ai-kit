"""Command-family tagging from the Phase 3 curated substitution set."""

from __future__ import annotations

import os
import re

# Ported from tools/hooks/detect.py::CURATED_SUBSTITUTIONS (not imported).
CURATED_SUBSTITUTIONS = (
    ("cat", "bat"),
    ("grep", "rg"),
    ("find", "fd"),
    ("sed", "sd"),
    ("ls", "eza"),
)

_TOKEN_TO_FAMILY = {}
for _legacy, _modern in CURATED_SUBSTITUTIONS:
    _TOKEN_TO_FAMILY[_legacy] = _legacy
    _TOKEN_TO_FAMILY[_modern] = _legacy

# Common wrapper binaries and a leading env-var-assignment run that should be
# skipped before taking the family-determining token, so `sudo grep x` and
# `FOO=bar rg x` resolve to "grep" rather than "sudo"/"FOO=bar" (WR-04).
_WRAPPERS = frozenset({"sudo", "env", "time", "nice", "ionice"})
_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*$")


def family_of(command_text: str) -> str:
    """Return the family of the first non-wrapper/non-assignment token.

    Both sides of a curated pair resolve to the LEGACY member (e.g. `rg` and
    `grep` both yield `"grep"`). Unmatched commands are their own singleton
    family — never a generic `"unclassified"` string (that token is reserved
    for the `command_shape` axis).

    A leading run of env-var assignments (`FOO=bar`, in any order/repetition
    with wrappers) and common wrapper binaries (`sudo`, `env`, `time`,
    `nice`, `ionice`) is skipped before the family-determining token is
    taken, along with each wrapper's own leading flags (e.g. `nice -n10`,
    `ionice -c2`), so `sudo grep x`, `FOO=bar rg x`, and `nice -n10 rg x`
    all resolve to `"grep"` instead of the wrapper/assignment/flag token.
    """
    tokens = (command_text or "").split()
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if _ASSIGNMENT_RE.match(tok):
            i += 1
            continue
        if tok in _WRAPPERS:
            i += 1
            while i < len(tokens) and tokens[i].startswith("-"):
                i += 1
            continue
        break
    token = os.path.basename(tokens[i]) if i < len(tokens) else ""
    return _TOKEN_TO_FAMILY.get(token, token)
