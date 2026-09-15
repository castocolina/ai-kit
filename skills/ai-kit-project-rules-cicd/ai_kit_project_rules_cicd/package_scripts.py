"""The `package.json` script reuse surface (D-C18) and its lockfile-driven
package-manager runner resolution (D-C18b), plan 14-03's first addition.

Two limits, stated here rather than discovered later:
  - ROOT file only. A workspace member's `package.json` is not read.
  - `scripts` only. Any OTHER top-level `package.json` field -- `bin`,
    `config`, and so on -- is never read as a command to reuse. A
    `scripts` entry named for an npm lifecycle hook (e.g. `prepare`) is
    read exactly like any other `scripts` entry -- through the SAME
    aggregate check and command-key machinery, no special-casing by
    name -- since it lives inside `scripts`, not outside it.

`read_package_scripts` reads the root `package.json` with the stdlib
`json` module and returns `(script_name, command)` pairs for every entry
whose value really is a string, inside a `scripts` object that really is
a dict. Every failure mode -- absent file, unreadable file, invalid JSON,
a missing or non-object `scripts` key, a non-string script value -- yields
an empty list and never raises. The wrap is exactly `(OSError,
UnicodeDecodeError, ValueError)`; `json.JSONDecodeError` subclasses
`ValueError`. A `KeyError` or `TypeError` surfacing from this module's own
logic is this module's defect, not something to swallow.

`resolve_package_manager_runner` decides the recommended runner from the
FIRST lockfile present at the repository root, in a pinned precedence --
never an arbitrary pick among several. `reuse_sources.py` computes each
script's IDENTITY (through the shared `command_text` helpers and this
skill's own `compute_command_key`); this module never computes an
identity itself, keeping the two questions ("what lockfile is present"
and "what does this script's body resolve to") separate.
"""

from __future__ import annotations

import json
import os

_LOCKFILE_RUNNERS: tuple[tuple[str, str], ...] = (
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("bun.lockb", "bun"),
    ("bun.lock", "bun"),
)
_DEFAULT_RUNNER = "npm"


def resolve_package_manager_runner(repo_root: str) -> str:
    """D-C18b: the FIRST of these lockfiles that exists at `repo_root`
    decides the runner -- `pnpm-lock.yaml` -> `pnpm`; `yarn.lock` ->
    `yarn`; `bun.lockb` or `bun.lock` -> `bun`; otherwise `npm`. A repo
    with several lockfiles gets the first in this order, deterministically.
    Never raises."""
    for filename, runner in _LOCKFILE_RUNNERS:
        if os.path.isfile(os.path.join(repo_root, filename)):
            return runner
    return _DEFAULT_RUNNER


def read_package_scripts(repo_root: str) -> list[tuple[str, str]]:
    """Read the root `package.json`'s `scripts` object and return
    `(script_name, command)` pairs for entries that really are string
    values. Absent file, unreadable file, invalid JSON, a non-dict
    top-level value, a missing or non-dict `scripts` key, and a
    non-string script value each yield an empty list. Never raises."""
    path = os.path.join(repo_root, "package.json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, UnicodeDecodeError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return []
    return [
        (name, command) for name, command in scripts.items() if isinstance(command, str)
    ]


__all__ = ["read_package_scripts", "resolve_package_manager_runner"]
