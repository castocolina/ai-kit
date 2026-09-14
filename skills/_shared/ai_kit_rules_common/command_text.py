"""Shell-command-line GRAMMAR primitives shared across the ai-kit
rules-checker skill family (D-C9, Phase 14 plan 01).

This module owns three purely-syntactic questions any single command
line poses: what are its top-level segments (split on `&&`/`||`/`;`,
never inside a quoted region, with a pipeline's first stage separated
from its consumption at the first unquoted `|`); which leading tokens
are noise -- `VAR=value` assignments, a leading `env` plus its own
assignments, or a direct-runner prefix (`uv run`, `npx`, `pnpm exec`,
...) -- rather than the invoked command itself; and what a token's
normalized form is (path basename, casefolded, `_` folded to `-`).

It knows NOTHING about `make`, `pre-commit`, `npm`, or Gradle. Which
invocations count as calling an existing command is `ai-kit-project-
rules-cicd`'s own reuse POLICY (its reuse-invocation table and its
tool-shaped identity gate), and stays inside that skill so a future
checker asking a different question can reuse this grammar without
inheriting that policy.

`ai-kit-project-rules-precommit`'s `parity_checker._RUNNER_PREFIX_RE`
(Phase 11) is the nearest prior answer to the runner-prefix question,
written for Makefile recipe lines. It is NOT repointed at this module --
Phase 11 closed that file, the same closed-file reason `yaml_text.py`'s
own docstring records for its own first duplication. This module's
`RUNNER_PREFIX_RE` constant is BYTE-IDENTICAL to `_RUNNER_PREFIX_RE`'s
pattern literal -- that constant, and ONLY that constant, is what a
drift guard in `tests/test_ai_kit_rules_common.py` pins against
`parity_checker`'s. Verified live on 2026-09-14, `_RUNNER_PREFIX_RE` is
`r"^(?<![-\\w])[A-Za-z0-9_.-]+(?![-\\w])[ \\t]+(?<![-\\w])run(?![-\\w])[ \\t]+"`
-- it recognizes the generic `<runner> run <rest>` SHAPE only (covering
`uv run`, `poetry run`, `pdm run`, `hatch run`, `pipenv run`), and cannot
express `npx`, `bunx`, `pnpm exec`, `pnpm dlx`, `yarn dlx`, or `bun x`
(none of which contain the token `run`), nor does it strip `VAR=value`
assignments. Those forms live in SEPARATELY-named constants below,
deliberately outside the guard's subject: the guard asserts equality on
`RUNNER_PREFIX_RE` alone, never a behavioral-equivalence check on this
whole module against `parity_checker`'s stripping behavior as a whole --
that reading would force this module to shrink to the one shape and
break the `npx`/`pnpm exec` handling this phase's CI-reuse policy
requires.

Every function degrades: no string input raises.
"""

from __future__ import annotations

import os
import re

# The ONE pinned constant (see module docstring). Byte-identical to
# `ai_kit_project_rules_precommit.parity_checker._RUNNER_PREFIX_RE`'s
# pattern literal, verified live 2026-09-14.
RUNNER_PREFIX_RE = re.compile(
    r"^(?<![-\w])[A-Za-z0-9_.-]+(?![-\w])[ \t]+(?<![-\w])run(?![-\w])[ \t]+"
)

# Two-token direct-runner forms NOT covered by RUNNER_PREFIX_RE's generic
# "<name> run" shape -- literal tool+subcommand pairs D-C6 names.
# Deliberately outside the drift guard's subject.
_PNPM_EXEC_RE = re.compile(r"^(?<![-\w])pnpm(?![-\w])[ \t]+(?<![-\w])exec(?![-\w])[ \t]+")
_PNPM_DLX_RE = re.compile(r"^(?<![-\w])pnpm(?![-\w])[ \t]+(?<![-\w])dlx(?![-\w])[ \t]+")
_YARN_DLX_RE = re.compile(r"^(?<![-\w])yarn(?![-\w])[ \t]+(?<![-\w])dlx(?![-\w])[ \t]+")
_BUN_X_RE = re.compile(r"^(?<![-\w])bun(?![-\w])[ \t]+(?<![-\w])x(?![-\w])[ \t]+")

_TWO_TOKEN_RUNNER_RES = (RUNNER_PREFIX_RE, _PNPM_EXEC_RE, _PNPM_DLX_RE, _YARN_DLX_RE, _BUN_X_RE)

# One-token direct-runner forms (`npx eslint .`, `bunx eslint .`).
_ONE_TOKEN_RUNNER_RE = re.compile(r"^(?<![-\w])(npx|bunx)(?![-\w])[ \t]+")

# A leading `VAR=value` assignment token.
_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*[ \t]+")

# A leading `env` token (its own assignments are consumed separately,
# immediately after this matches).
_ENV_RE = re.compile(r"^(?<![-\w])env(?![-\w])[ \t]+")


def split_top_level_segments(line: str) -> list[str]:
    """Split `line` on top-level (unquoted) `&&`, `||`, and `;`, never
    splitting inside a single- or double-quoted region. Each segment is
    stripped of surrounding whitespace; empty segments (e.g. a trailing
    `;`) are dropped. Never raises for any string input."""
    segments: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch == "'" and not in_double:
            in_single = not in_single
            current.append(ch)
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            current.append(ch)
            i += 1
            continue
        if not in_single and not in_double:
            if line[i : i + 2] in ("&&", "||"):
                segments.append("".join(current))
                current = []
                i += 2
                continue
            if ch == ";":
                segments.append("".join(current))
                current = []
                i += 1
                continue
        current.append(ch)
        i += 1
    segments.append("".join(current))
    return [s.strip() for s in segments if s.strip()]


def truncate_at_unquoted_pipe(segment: str) -> str:
    """Return `segment` truncated at the first UNQUOTED `|` -- a
    pipeline's first stage is the invoked tool, the rest is consumption.
    Never splits inside a quoted region. Never raises."""
    in_single = False
    in_double = False
    for i, ch in enumerate(segment):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "|" and not in_single and not in_double:
            return segment[:i]
    return segment


def has_heredoc(line: str) -> bool:
    """`True` if `line` contains an unquoted `<<` (a heredoc/here-string
    marker) -- D-C6: a line containing one is skipped entirely by
    whatever consumes this primitive, rather than mis-parsed. Never
    raises."""
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif (
            ch == "<"
            and not in_single
            and not in_double
            and line[i : i + 2] == "<<"
        ):
            return True
    return False


def _strip_one_round(line: str) -> str:
    """Try D-C6's stripping rules once, in order, and apply the FIRST one
    that matches: a leading `VAR=value` token; a leading `env` plus its
    own assignments; a two-token direct-runner form; a one-token
    direct-runner form. Returns `line` unchanged if none matches."""
    match = _ASSIGNMENT_RE.match(line)
    if match is not None:
        return line[match.end() :]

    match = _ENV_RE.match(line)
    if match is not None:
        rest = line[match.end() :]
        while True:
            assignment = _ASSIGNMENT_RE.match(rest)
            if assignment is None:
                break
            rest = rest[assignment.end() :]
        return rest

    for pattern in _TWO_TOKEN_RUNNER_RES:
        match = pattern.match(line)
        if match is not None:
            return line[match.end() :]

    match = _ONE_TOKEN_RUNNER_RE.match(line)
    if match is not None:
        return line[match.end() :]

    return line


def strip_leading_noise(line: str, stop_check=None) -> str:
    """Strip up to 3 ROUNDS of D-C6's leading noise, trying each rule (in
    `_strip_one_round`'s order) every round and applying the first match.
    A line with more than 3 stacked prefixes stops after the third round
    rather than looping -- a stated bound, not a bug.

    `stop_check`, if given, is an opaque predicate this module never
    interprets: called with the current text BEFORE any stripping and
    again after every round that changes it; the moment it returns
    `True`, stripping stops and that text is returned as-is. This lets a
    caller recognize a shape it cares about (a reuse-invocation prefix
    like `pre-commit run <id>`, which the generic runner-prefix rule
    below would otherwise consume as if it were a `<runner> run <rest>`
    wrapper) without this module needing any policy knowledge of what
    that shape means -- D-C9 keeps that knowledge in the caller. Never
    raises for any string input."""
    result = line
    if stop_check is not None and stop_check(result):
        return result
    for _ in range(3):
        stripped = _strip_one_round(result)
        if stripped == result:
            break
        result = stripped
        if stop_check is not None and stop_check(result):
            break
    return result


def normalize_token(token: str) -> str:
    """Basename, then casefold, then `_`-to-`-` fold -- Phase 11's
    `normalize_name` rule plus the basename step a shell command token
    needs (`./bin/ruff` and `.venv/bin/ruff` both become `ruff`). Never
    raises for any string input."""
    base = os.path.basename(token.strip())
    return base.casefold().replace("_", "-")


__all__ = [
    "RUNNER_PREFIX_RE",
    "has_heredoc",
    "normalize_token",
    "split_top_level_segments",
    "strip_leading_noise",
    "truncate_at_unquoted_pipe",
]
