"""Command-family tagging from the Phase 3 curated substitution set."""

from __future__ import annotations

import os

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


def family_of(command_text: str) -> str:
    """Return the family of the first token of `command_text`.

    Both sides of a curated pair resolve to the LEGACY member (e.g. `rg` and
    `grep` both yield `"grep"`). Unmatched commands are their own singleton
    family — never a generic `"unclassified"` string (that token is reserved
    for the `command_shape` axis).
    """
    token = (command_text or "").split(None, 1)[0] if command_text else ""
    token = os.path.basename(token)
    return _TOKEN_TO_FAMILY.get(token, token)
