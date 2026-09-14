"""Healthcheck timing-bounds check (ROADMAP Phase 13 SC2, D-D9).

`parse_duration` reads a Go-style Compose duration (`5s`, `1m30s`,
`1500ms`, a bare number as seconds, and a DECIMAL FRACTION on any
`<number>` component) or a bare unitless number, and returns `None` --
never a guess, never `0` -- for anything it cannot read, including an
interpolated `${VAR}`, an empty value, or an unknown unit.

`_BOUNDS` is ONE module-level table -- `timeout` 2.0s, `start_period`
10.0s, `interval` 5.0s, in that declaration order -- and every finding's
text reads its numbers from this table rather than repeating them in a
format string, so a bound and its message cannot drift.

A key DECLARED with a value STRICTLY GREATER than its bound is a
finding; equal to the bound is conforming (SC2 says "exceeding"). A key
DECLARED with an unparseable value is an ADVISORY finding naming the raw
value -- silence there is the wrong answer, since an unreadable
`timeout` is precisely where a real violation hides. A key that is
ABSENT gets nothing, and that is a PROHIBITION on the stricter check
(D-D9), not an unfinished edge: Compose's own 30s `interval`/`timeout`
defaults would exceed two of these bounds, so "flag the absent key too"
is the obvious-looking improvement that is forbidden here -- it would
silently expand what ROADMAP SC2 promises and fire on the majority of
real compose files. A service with no `healthcheck:` block, or one
declaring `disable: true`, gets nothing, for the same reason: no source
artifact for this phase says every service must have a healthcheck.
"""

from __future__ import annotations

import os
import re

from ai_kit_rules_common.criticality import CRITICALITY_ADVISORY, CRITICALITY_MEDIUM

from . import compose_parse

_DURATION_TOKEN_RE = re.compile(r"(\d+(?:\.\d+)?)(ns|us|ms|s|m|h)")
_BARE_NUMBER_RE = re.compile(r"^\d+(?:\.\d+)?$")

_UNIT_SECONDS = {
    "ns": 1e-9,
    "us": 1e-6,
    "ms": 1e-3,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
}

# D-D9's ONE bounds table, in this declaration order (timeout,
# start_period, interval) so output is deterministic.
_BOUNDS = (
    ("timeout", 2.0),
    ("start_period", 10.0),
    ("interval", 5.0),
)


def parse_duration(value) -> float | None:
    """A Go-style duration of one or more `<number><unit>` pairs (units
    `ns`, `us`, `ms`, `s`, `m`, `h`; `1m30s` is 90.0), or a bare number
    as seconds. Each `<number>` may carry a decimal fraction (`1.5s`,
    `5.001s`, a bare `0.5`). `None` -- never a guess, never `0` -- for
    anything else: not a string, empty, an interpolated `${VAR}`, an
    unknown unit, or trailing garbage after an otherwise-valid duration.
    Never raises."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if _BARE_NUMBER_RE.fullmatch(text):
        return float(text)
    pos = 0
    total = 0.0
    matched_any = False
    length = len(text)
    while pos < length:
        match = _DURATION_TOKEN_RE.match(text, pos)
        if match is None:
            return None
        total += float(match.group(1)) * _UNIT_SECONDS[match.group(2)]
        matched_any = True
        pos = match.end()
    if not matched_any:
        return None
    return total


def _out_of_bounds_finding(
    service: str, compose_file: str, key: str, declared: str, bound: float
) -> dict:
    text = (
        f"Service '{service}' in {compose_file} declares healthcheck "
        f"'{key}: {declared}', exceeding the {bound}s bound. Lower "
        f"'{key}' to {bound}s or less."
    )
    return {
        "category": "docker-healthcheck-bounds",
        "issue": "docker_healthcheck_out_of_bounds",
        "criticality": CRITICALITY_MEDIUM,
        "summary": text,
        "recommendation": text,
        "needs_research": False,
        "service": service,
        "compose_file": compose_file,
        "key": key,
        "declared": declared,
        "bound": bound,
    }


def _unreadable_finding(service: str, compose_file: str, key: str, declared: str) -> dict:
    text = (
        f"Service '{service}' in {compose_file} declares healthcheck "
        f"'{key}: {declared}', which this skill could not read as a "
        f"duration. An unreadable timing is exactly where a real "
        f"violation can hide -- confirm '{key}' by hand."
    )
    return {
        "category": "docker-healthcheck-bounds",
        "issue": "docker_healthcheck_unreadable",
        "criticality": CRITICALITY_ADVISORY,
        "summary": text,
        "recommendation": text,
        "needs_research": False,
        "advisory": True,
        "reason": "unreadable_duration",
        "service": service,
        "compose_file": compose_file,
        "key": key,
        "declared": declared,
    }


def check_healthcheck_bounds(repo_root: str, compose_files: list[str]) -> list[dict]:
    """One finding per (compose file, service, offending key), in
    `_BOUNDS`'s declaration order per service. `compose_files` is
    discovered ONCE by the caller (`docker_checker.py`) and passed down
    here rather than re-discovered. Never raises."""
    findings: list[dict] = []
    for path in compose_files:
        text = compose_parse.read_compose_text(path)
        rel = os.path.relpath(path, repo_root)
        for service, block in compose_parse.iter_services(text):
            healthcheck_block = compose_parse.block_subblock(block, "healthcheck")
            if healthcheck_block is None:
                continue
            disable_value = compose_parse.block_scalar(healthcheck_block, "disable")
            if disable_value is not None and disable_value.strip().lower() == "true":
                continue
            for key, bound in _BOUNDS:
                declared = compose_parse.block_scalar(healthcheck_block, key)
                if declared is None:
                    continue
                seconds = parse_duration(declared)
                if seconds is None:
                    findings.append(_unreadable_finding(service, rel, key, declared))
                    continue
                if seconds > bound:
                    findings.append(_out_of_bounds_finding(service, rel, key, declared, bound))
    return findings


__all__ = ["check_healthcheck_bounds", "parse_duration"]
