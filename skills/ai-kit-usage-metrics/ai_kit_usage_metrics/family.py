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
# `export` is a shell keyword wrapping an assignment the same way (`export
# FOO=bar` / `export FOO=bar rg x`), not a real binary -- without it, a bare
# `export FOO=bar` line has its OWN assignment token skipped but "export"
# itself never gets a skip rule, so it wrongly becomes the family.
_WRAPPERS = frozenset({"sudo", "env", "time", "nice", "ionice", "export"})
_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*$")

# A command substitution glued directly onto an assignment's value with no
# separating space (`FOO="$(jq ...)"`, `FOO=$(jq ...)`) is naive-whitespace-
# tokenized as ONE token together with the substituted command's own name
# (e.g. `FOO="$(jq` from `FOO="$(jq -cSn ...)"`), so the plain assignment
# skip above consumes it as a unit and the substituted command's own FLAG
# (`-cSn`) becomes the next token and is wrongly read as the family. This
# pattern recognizes that shape and captures the substitution's real command
# name directly, ahead of the plain assignment check.
_SUBST_ASSIGNMENT_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*=[\"']?\$\(([A-Za-z0-9_./-]+)"
)

# A family value that reaches this point without matching a curated pair is
# shown as-is (D-16: "never a generic 'unclassified' string") -- but only
# when it plausibly LOOKS like a command/binary name. The decomposer's
# quote-aware scanner cannot always structurally close every shell
# construct (documented `unclassified`/`control_flow_script` limitation in
# SKILL.md); a mis-split fragment of one of those constructs -- a trailing
# `sort)` from an unclosed `<(...)` process substitution, a bare `-cSn`
# flag, a quoted string fragment -- is not a command name and must not
# populate the family filter/chart as if it were one.
_FAMILY_CANDIDATE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")

# D-11 / SD-1: option-arity table for subfamily_of()'s value-flag skip. A flag
# belongs here when its following SEPARATE argument is a configuration value
# rather than the command's subcommand (e.g. `git -C /path commit` -> `-C`
# consumes `/path`, so the subcommand is `commit`, not `/path`). A flag whose
# argument IS the meaningful second token -- `python3 -m <module>` -- is
# deliberately absent, so the skip loop steps over `-m` and lands on the
# module name instead of treating it as a value to discard.
_VALUE_FLAGS: dict[str, frozenset[str]] = {
    "git": frozenset(
        {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
    ),
    "make": frozenset({"-C", "--directory", "-f", "--file", "-j", "--jobs", "-o", "-W"}),
    "docker": frozenset({"-H", "--host", "--context", "--config", "--log-level"}),
    "kubectl": frozenset(
        {"-n", "--namespace", "--context", "--cluster", "--user", "--kubeconfig"}
    ),
    "npm": frozenset({"--prefix", "-w", "--workspace", "--registry"}),
    "cargo": frozenset({"--manifest-path", "--config", "-Z"}),
    "go": frozenset({"-C"}),
    "pip": frozenset(
        {"-r", "--requirement", "--index-url", "--extra-index-url", "-t", "--target"}
    ),
    "pip3": frozenset(
        {"-r", "--requirement", "--index-url", "--extra-index-url", "-t", "--target"}
    ),
    "systemctl": frozenset({"-H", "--host", "-M", "--machine"}),
    "apt": frozenset({"-o", "-c", "-t"}),
    "apt-get": frozenset({"-o", "-c", "-t"}),
    "tar": frozenset({"-f", "--file", "-C", "--directory"}),
    "rsync": frozenset({"-e", "--exclude-from", "--files-from"}),
}

# The subfamily candidate plausibility filter (SD-1 step 5). A path, a quoted
# fragment, a variable expansion, a redirect or a numeric literal is not a
# subcommand -- rejecting those here keeps the subfamily axis from
# accumulating the same noise D-16 removed from the family axis.
_SUBFAMILY_CANDIDATE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")


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
        subst = _SUBST_ASSIGNMENT_RE.match(tok)
        if subst:
            token = subst.group(1)
            return _TOKEN_TO_FAMILY.get(token, token)
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
    if token and not _FAMILY_CANDIDATE_RE.match(token):
        return ""
    return _TOKEN_TO_FAMILY.get(token, token)


def subfamily_of(command_text: str) -> str:
    """Return the command's meaningful second token (D-11 / SD-1).

    Reuses `family_of`'s exact wrapper/assignment/leading-flag skip loop to
    land on the family-determining token, then applies an option-arity table
    (`_VALUE_FLAGS`) one token deeper: a flag whose following SEPARATE
    argument is a configuration value (not the subcommand itself) is skipped
    along with its value, so `git -C /path commit` returns `commit` rather
    than `/path` -- the naive "skip every flag-shaped token" approach cannot
    tell `-C`'s value apart from a real subcommand, because the value is not
    itself flag-shaped. No `os.path.basename` reduction and no
    `_TOKEN_TO_FAMILY` substitution is applied to the result: a subcommand is
    not a binary path, and family_of's curated pairs don't apply one token
    deeper. A candidate that fails the plausibility filter (a path, a quoted
    fragment, a redirect, a numeric literal) returns "" rather than
    presenting noise on this axis the way an ungated family_of() did on its
    own (D-16).
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
    if i >= len(tokens):
        return ""
    family_token = os.path.basename(tokens[i])
    value_flags = _VALUE_FLAGS.get(family_token, frozenset())
    i += 1
    while i < len(tokens) and tokens[i].startswith("-"):
        if tokens[i] == "--":
            i += 1
            break
        flag = tokens[i]
        i += 1
        if "=" not in flag and flag in value_flags and i < len(tokens):
            i += 1
    if i >= len(tokens):
        return ""
    candidate = tokens[i]
    if not _SUBFAMILY_CANDIDATE_RE.match(candidate):
        return ""
    return candidate
