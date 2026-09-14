"""Local-dev hot-reload convention check (ROADMAP Phase 13 SC4, 13-CONTEXT
D-04/D-05, plan 13-03 D-D13 through D-D18).

A local-dev service (D-D13: one defined in a file `compose_parse.
discover_local_dev_compose_files` returns, never a base-file-only service)
CONFORMS when it declares a bind mount, declares a `command:`/`entrypoint:`
override, and that override resolves to a recognized stack-appropriate
hot-reload marker via the shared catalog's `resolve_hot_reload`
(13-CONTEXT D-04's expansion beyond a plain bind-mount-plus-override
heuristic). Evaluation has THREE outcomes, never two (D-D15): conforming
(no finding); the convention is MISSING one or both halves (a real,
`CRITICALITY_MEDIUM` finding naming which half); or the third clause
cannot be CONFIRMED (an ADVISORY finding carrying one of five named
`reason`s). Collapsing the third outcome into the second would assert
"this service has no hot reload" on evidence this skill never had;
collapsing it into the first would silently withdraw the check.

Every service is evaluated once into exactly one outcome -- one finding
per (local-dev compose file, service), D-D18 -- by first resolving the
bind-mount answer (three-valued: present / absent / unreadable, D-D17) and
the override answer (two-valued: declared / not), and only then branching.

This module carries THREE stated limits, not silent gaps:

  - Stack attribution is REPO-WIDE, not per-service: the override command
    is resolved against the union of every stack detected in the repo,
    because a compose service definition carries no per-service language
    signal. A polyglot repo can therefore accept one stack's dev server on
    a different stack's service command line.
  - The per-stack marker baseline (the shared catalog's hot-reload
    mapping) is hardcoded knowledge that goes stale. This is exactly why
    an unrecognized override is advisory rather than a defect -- a
    checker that asserted certainty from an admittedly incomplete table
    would be a checker a user learns to distrust.
  - LONG-FORM (mapping-style) volume entries are not read by this check
    (D-D17's descope, cycle-2 review finding 1): the shared parser's
    scalar-item sequence reader delivers such an entry as an unparseable
    fragment, and this check reports that fragment as UNREADABLE --
    advisory, never a confident "no bind mount" and never a false
    conforming result.

No text in this module names a specific hot-reload marker or
script-runner prefix as a literal (D-D16's fourth prohibition): every
recommendation string that lists "the markers/prefixes this skill knows"
builds that list at RUNTIME by joining from the shared catalog's
`HOT_RELOAD_TOOLS`/`SCRIPT_INDIRECTION_PREFIXES` for the stacks actually
in play. A hardcoded example here would be a second, staleable copy of
knowledge 13-CONTEXT D-05 gave one home.
"""

from __future__ import annotations

import os
import re

from ai_kit_rules_common.criticality import CRITICALITY_ADVISORY, CRITICALITY_MEDIUM
from ai_kit_rules_common.stack_detect import detect_stacks
from ai_kit_rules_common.tool_catalog import (
    HOT_RELOAD_BASELINE_GAPS,
    HOT_RELOAD_TOOLS,
    SCRIPT_INDIRECTION_PREFIXES,
    resolve_hot_reload,
)

from . import compose_parse

_ISSUE_MISSING = "docker_hot_reload_convention_missing"
_ISSUE_UNRECOGNIZED = "docker_hot_reload_tool_unrecognized"

# D-D17's three-valued bind-mount answer.
_BIND_PRESENT = "present"
_BIND_ABSENT = "absent"
_BIND_UNREADABLE = "unreadable"

# The two entry SHAPES that classify as unreadable (D-D17 rules 2 and 3),
# kept distinct only so the finding text can name which one applied.
_UNREADABLE_NOT_SHORT_FORM = "not_short_form"
_UNREADABLE_INTERPOLATED = "interpolated"


def _classify_volume_entry(entry: str) -> str:
    """D-D17's FIVE rules, evaluated IN THIS ORDER, stopping at the first
    that applies. Returns one of: `"anonymous"` (rule 1 -- no colon
    anywhere; READABLE and never a bind mount, even though the entry may
    begin with a bind-mount-shaped leading character); `"not_short_form"`
    (rule 2 -- not `src:dst[:opts]` with an absolute `dst`; UNREADABLE,
    which is where a descoped long-form/mapping-style fragment lands);
    `"interpolated"` (rule 3 -- `src` carries an interpolation;
    UNREADABLE); `"bind"` (rule 4 -- `src` begins with `.`, `..`, `/` or
    `~`); or `"named"` (rule 5 -- otherwise, a named volume, READABLE and
    never a bind mount).

    The separator test (rule 1) runs BEFORE the leading-character test
    (rule 4) on purpose: a bare path entry begins with `/` or `.` exactly
    like a real bind-mount source does, and an implementation reaching the
    leading-character test first would read it as a bind mount and report
    a service CONFORMING on a mount that does not exist.
    """
    stripped = entry.strip()
    if ":" not in stripped:
        return "anonymous"
    src, _, remainder = stripped.partition(":")
    dst, _, _opts = remainder.partition(":")
    src = src.strip()
    dst = dst.strip()
    if not dst.startswith("/"):
        return _UNREADABLE_NOT_SHORT_FORM
    if "$" in src:
        return _UNREADABLE_INTERPOLATED
    if src.startswith((".", "/", "~")):
        return "bind"
    return "named"


def _bind_mount_answer(service_block: str) -> tuple[str, str | None]:
    """The three-valued bind-mount answer (D-D17), plus the FIRST
    unreadable entry's shape (for the finding text) when the answer is
    `unreadable`. Resolution order of authority: one readable bind mount
    makes the answer `present` no matter how many unreadable entries sit
    beside it; with no readable bind mount, ANY unreadable entry makes the
    answer `unreadable`; only an all-readable, all-non-bind-mount list --
    named volumes, anonymous volumes, or both -- or no `volumes:` key at
    all, makes it `absent`. `unreadable` is NEVER collapsed into `absent`
    at any point in this computation.
    """
    entries = compose_parse.block_sequence(service_block, "volumes")
    if not entries:
        return _BIND_ABSENT, None
    unreadable_kinds = (_UNREADABLE_NOT_SHORT_FORM, _UNREADABLE_INTERPOLATED)
    any_bind = False
    unreadable_shape: str | None = None
    for entry in entries:
        kind = _classify_volume_entry(entry)
        if kind == "bind":
            any_bind = True
        elif kind in unreadable_kinds and unreadable_shape is None:
            unreadable_shape = kind
    if any_bind:
        return _BIND_PRESENT, None
    if unreadable_shape is not None:
        return _BIND_UNREADABLE, unreadable_shape
    return _BIND_ABSENT, None


def _override_text(service_block: str) -> str | None:
    """The joined text of the service's `command:`/`entrypoint:` override,
    scalar or sequence form, or `None` when neither key is declared
    (D-D17's override answer, two-valued: a key is declared or it is
    not)."""
    parts: list[str] = []
    declared = False
    for key in ("command", "entrypoint"):
        scalar = compose_parse.block_scalar(service_block, key)
        if scalar is not None:
            declared = True
            parts.append(scalar)
            continue
        sequence = compose_parse.block_sequence(service_block, key)
        if sequence:
            declared = True
            parts.append(" ".join(sequence))
    if not declared:
        return None
    return " ".join(parts)


def _is_script_indirection(command_text: str) -> bool:
    """Whether `command_text` STARTS WITH one of the shared catalog's
    script-runner prefixes (`SCRIPT_INDIRECTION_PREFIXES`), token-boundary
    aware at the prefix's own end so a prefix cannot match as part of a
    longer, unrelated first token."""
    normalized = " ".join(command_text.split()).casefold()
    for prefix in SCRIPT_INDIRECTION_PREFIXES:
        pattern = rf"^{re.escape(prefix)}(?![-\w])"
        if re.match(pattern, normalized) is not None:
            return True
    return False


def _classify_unrecognized_reason(override_text: str, stacks: set[str]) -> str:
    """D-D15's fixed evaluation order for the four reasons reachable once
    the bind-mount answer is confirmed `present` (the fifth, `volumes_
    unreadable`, is decided earlier and never reaches this function):
    `script_indirection` -> `no_stack_detected` -> `stack_without_baseline`
    -> `command_not_matched`. An empty stack set, and a detected stack
    whose tuple is empty, are NOT folded into `command_not_matched` --
    those three say different things to the reader, and the last one
    implies a marker table was actually consulted."""
    if _is_script_indirection(override_text):
        return "script_indirection"
    if not stacks:
        return "no_stack_detected"
    if all(stack in HOT_RELOAD_BASELINE_GAPS for stack in stacks):
        return "stack_without_baseline"
    return "command_not_matched"


def _markers_text(stacks: set[str]) -> str:
    """The markers this skill knows for `stacks`, joined at RUNTIME from
    the shared catalog -- never a literal list (D-D16's fourth
    prohibition)."""
    markers = sorted(
        {marker for stack in sorted(stacks) for marker in HOT_RELOAD_TOOLS.get(stack, ())}
    )
    if not markers:
        return "no markers for the detected stack(s)"
    return "the markers this skill knows for the detected stack(s) (" + ", ".join(markers) + ")"


def _script_prefixes_text() -> str:
    """The script-runner prefixes this skill knows, joined at RUNTIME from
    the shared catalog -- never a literal list."""
    return ", ".join(SCRIPT_INDIRECTION_PREFIXES)


def _missing_finding(
    service: str, compose_file: str, *, bind_present: bool, override_present: bool
) -> dict:
    missing_halves = []
    if not bind_present:
        missing_halves.append("no bind mount")
    if not override_present:
        missing_halves.append("no command or entrypoint override")
    halves_text = " and ".join(missing_halves)
    text = (
        f"Service '{service}' in {compose_file} is missing the local-dev "
        f"hot-reload convention: {halves_text}. This looks like the "
        f"production image/entrypoint baked at build time rather than a "
        f"reloading local-dev workflow."
    )
    if not bind_present:
        text += (
            " Add a bind mount of the source tree under 'volumes:' (a "
            "short-form entry, e.g. './src:/app/src')."
        )
    if not override_present:
        text += (
            " Add a 'command:' or 'entrypoint:' override that runs a "
            "stack-appropriate dev server with hot reload."
        )
    return {
        "category": "docker-hot-reload",
        "issue": _ISSUE_MISSING,
        "criticality": CRITICALITY_MEDIUM,
        "summary": text,
        "recommendation": text,
        "needs_research": False,
        "service": service,
        "compose_file": compose_file,
    }


def _unrecognized_finding(
    service: str,
    compose_file: str,
    reason: str,
    *,
    override_present: bool,
    override_text: str | None,
    unreadable_shape: str | None,
    stacks: set[str],
) -> dict:
    if reason == "volumes_unreadable":
        if override_present:
            override_fact = (
                f"declares a 'command:'/'entrypoint:' override ('{override_text}')"
            )
        else:
            override_fact = "declares no 'command:' or 'entrypoint:' override"
        shape_phrase = (
            "an interpolated volume source this skill does not resolve"
            if unreadable_shape == _UNREADABLE_INTERPOLATED
            else "a long-form (mapping-style) volume entry this skill does not read"
        )
        text = (
            f"Service '{service}' in {compose_file} {override_fact}. "
            f"Whether it has a bind mount is UNKNOWN: its only candidate "
            f"volume entry is {shape_phrase}, so this skill could not "
            f"confirm a bind mount is present. This is advisory, not a "
            f"defect claim -- confirm the volume entry by hand."
        )
    elif reason == "script_indirection":
        text = (
            f"Service '{service}' in {compose_file} declares a bind mount "
            f"and a command override ('{override_text}'), but the override "
            f"runs through a script indirection (one of the script-runner "
            f"prefixes this skill knows: {_script_prefixes_text()}) whose "
            f"real command this skill does not follow into a 'package.json' "
            f"scripts entry or a Makefile recipe. This is advisory, not a "
            f"defect claim -- check the script's real command by hand."
        )
    elif reason == "no_stack_detected":
        text = (
            f"Service '{service}' in {compose_file} declares a bind mount "
            f"and a command override ('{override_text}'), but no known "
            f"stack was detected anywhere in this repo, so no stack's "
            f"hot-reload convention applies. This is advisory, not a "
            f"defect claim."
        )
    elif reason == "stack_without_baseline":
        text = (
            f"Service '{service}' in {compose_file} declares a bind mount "
            f"and a command override ('{override_text}'), but the "
            f"detected stack(s) carry no hot-reload baseline in this "
            f"skill's catalog yet. This is advisory, not a defect claim."
        )
    else:
        text = (
            f"Service '{service}' in {compose_file} declares a bind mount "
            f"and a command override ('{override_text}'), but this skill "
            f"could not confirm it reloads on change -- it matched none of "
            f"{_markers_text(stacks)}. This is advisory, not a defect "
            f"claim -- confirm by hand."
        )
    return {
        "category": "docker-hot-reload",
        "issue": _ISSUE_UNRECOGNIZED,
        "criticality": CRITICALITY_ADVISORY,
        "summary": text,
        "recommendation": text,
        "needs_research": False,
        "advisory": True,
        "reason": reason,
        "service": service,
        "compose_file": compose_file,
    }


def _evaluate_service(
    service: str, compose_file: str, service_block: str, stacks: set[str]
) -> dict | None:
    """Evaluate one service into exactly one of D-D15's three outcomes.
    The bind-mount answer and the override answer are both resolved BEFORE
    any branching, so the three outcomes stay visibly mutually exclusive.

    An `unreadable` bind answer OUTRANKS the missing-override half and
    ALWAYS produces the advisory `volumes_unreadable` outcome, even when
    the override is also missing (D-D17's mixed-state rule) -- it must
    NEVER produce the non-advisory convention-missing finding, because
    that finding would be built on a value this skill could not read.
    """
    bind_answer, unreadable_shape = _bind_mount_answer(service_block)
    override_text = _override_text(service_block)
    override_present = override_text is not None

    if bind_answer == _BIND_UNREADABLE:
        return _unrecognized_finding(
            service,
            compose_file,
            "volumes_unreadable",
            override_present=override_present,
            override_text=override_text,
            unreadable_shape=unreadable_shape,
            stacks=stacks,
        )

    bind_present = bind_answer == _BIND_PRESENT
    if bind_present and override_present:
        marker = resolve_hot_reload(override_text, stacks)
        if marker is not None:
            return None
        reason = _classify_unrecognized_reason(override_text, stacks)
        return _unrecognized_finding(
            service,
            compose_file,
            reason,
            override_present=True,
            override_text=override_text,
            unreadable_shape=None,
            stacks=stacks,
        )

    return _missing_finding(
        service, compose_file, bind_present=bind_present, override_present=override_present
    )


def check_hot_reload(repo_root: str, compose_files: list[str]) -> list[dict]:
    """One finding per (local-dev compose file, service) -- D-D18.
    `compose_files` MUST be the LOCAL-DEV list only
    (`compose_parse.discover_local_dev_compose_files`), discovered once by
    the caller (`docker_checker.py`) and passed down here: this is the ONE
    check in this skill scoped to local-dev files only (D-03), and a call
    given the full discovery list would flag production service
    definitions for not hot-reloading, inverting the convention.

    `detect_stacks(repo_root)` is called EXACTLY ONCE per invocation, here
    -- not per service -- because the answer cannot differ between
    services in one repo. Never raises."""
    findings: list[dict] = []
    stacks = detect_stacks(repo_root)
    for path in compose_files:
        text = compose_parse.read_compose_text(path)
        rel = os.path.relpath(path, repo_root)
        for service, block in compose_parse.iter_services(text):
            finding = _evaluate_service(service, rel, block, stacks)
            if finding is not None:
                findings.append(finding)
    return findings


__all__ = ["check_hot_reload"]
