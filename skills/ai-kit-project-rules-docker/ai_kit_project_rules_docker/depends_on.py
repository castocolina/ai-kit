"""`depends_on` discipline check (ROADMAP Phase 13 SC3, D-D10).

For each dependency a service declares, via `compose_parse`'s accessors
only -- never a raw re-scan of the compose text:

  - A block sequence (`- db` lines) or a flow sequence (`[db, cache]`) is
    BARE ORDERING: `docker_depends_on_bare`, `CRITICALITY_HIGH`. The two
    spellings are the same convention failure, never treated
    differently.
  - A mapping entry with `condition: service_healthy` is conforming: no
    finding.
  - A mapping entry with `condition: service_started`, OR with NO
    `condition:` key at all, is bare ordering WRITTEN LONG:
    `docker_depends_on_weak_condition`, `CRITICALITY_HIGH`. Compose's own
    default condition IS `service_started`, so the no-condition case is
    not a neutral omission -- it is the form real repos most often
    write.
  - A mapping entry with `condition: service_completed_successfully` is
    ADVISORY (`docker_depends_on_completion_condition`,
    `CRITICALITY_ADVISORY`, `advisory: True`): the legitimate form for a
    one-shot init/migration container. Flagging it as a plain violation
    would train a reader to ignore the whole category.
  - A mapping entry with an unreadable condition (an interpolation, an
    unknown token) is ADVISORY (`docker_depends_on_unreadable`), naming
    the raw value -- same reasoning as `healthcheck.py`'s unreadable
    duration.

Evaluation is PER-ENTRY, never "does the block mention the conforming
condition anywhere": a service depending on three others where only the
first is conditioned correctly must produce two findings, not zero. This
is the same per-hook-versus-anywhere distinction
`check_precommit_prepush_split` already makes for pre-push stages.

`CRITICALITY_HIGH` rather than MEDIUM is deliberate and is the only HIGH
band in this skill: a bare `depends_on` produces a real startup race,
the concrete failure this convention exists to prevent.
"""

from __future__ import annotations

import os

from ai_kit_rules_common.criticality import CRITICALITY_ADVISORY, CRITICALITY_HIGH

from . import compose_parse

_CONFORMING_CONDITION = "service_healthy"
_WEAK_CONDITION = "service_started"
_COMPLETION_CONDITION = "service_completed_successfully"


def _bare_finding(service: str, compose_file: str, dep: str) -> dict:
    text = (
        f"Service '{service}' in {compose_file} depends on '{dep}' via bare "
        f"ordering (a sequence entry), which only waits for '{dep}' to "
        f"start, not for it to become healthy. Rewrite as a mapping entry "
        f"with 'condition: service_healthy' under '{dep}:'."
    )
    return {
        "category": "docker-depends-on",
        "issue": "docker_depends_on_bare",
        "criticality": CRITICALITY_HIGH,
        "summary": text,
        "recommendation": text,
        "needs_research": False,
        "service": service,
        "compose_file": compose_file,
        "depends_on": dep,
    }


def _weak_finding(service: str, compose_file: str, dep: str) -> dict:
    text = (
        f"Service '{service}' in {compose_file} depends on '{dep}' with a "
        f"weak or absent condition -- Compose's own default is "
        f"'service_started', which is bare ordering written long. Add "
        f"'condition: service_healthy' under '{dep}:'."
    )
    return {
        "category": "docker-depends-on",
        "issue": "docker_depends_on_weak_condition",
        "criticality": CRITICALITY_HIGH,
        "summary": text,
        "recommendation": text,
        "needs_research": False,
        "service": service,
        "compose_file": compose_file,
        "depends_on": dep,
    }


def _completion_finding(service: str, compose_file: str, dep: str) -> dict:
    text = (
        f"Service '{service}' in {compose_file} depends on '{dep}' with "
        f"'condition: service_completed_successfully' -- the legitimate "
        f"form for a one-shot init or migration container. Confirm this "
        f"is intentional rather than changing it."
    )
    return {
        "category": "docker-depends-on",
        "issue": "docker_depends_on_completion_condition",
        "criticality": CRITICALITY_ADVISORY,
        "summary": text,
        "recommendation": text,
        "needs_research": False,
        "advisory": True,
        "service": service,
        "compose_file": compose_file,
        "depends_on": dep,
    }


def _unreadable_condition_finding(
    service: str, compose_file: str, dep: str, raw_value: str
) -> dict:
    text = (
        f"Service '{service}' in {compose_file} depends on '{dep}' with a "
        f"condition this skill could not read: '{raw_value}'. Confirm its "
        f"value by hand."
    )
    return {
        "category": "docker-depends-on",
        "issue": "docker_depends_on_unreadable",
        "criticality": CRITICALITY_ADVISORY,
        "summary": text,
        "recommendation": text,
        "needs_research": False,
        "advisory": True,
        "reason": "unreadable_condition",
        "service": service,
        "compose_file": compose_file,
        "depends_on": dep,
    }


def _evaluate_service_depends_on(service: str, compose_file: str, service_block: str) -> list[dict]:
    """Evaluate one service's `depends_on`. Tries the sequence form
    first (block or flow -- both are bare ordering); if that yields no
    items, tries the mapping form and evaluates each dependency's OWN
    condition. A `depends_on` that is absent, or written as a same-line
    flow-mapping (D-D7's stated limit), yields nothing from EITHER
    branch -- neither flagged nor confirmed, per the stated limit."""
    findings: list[dict] = []

    bare_items = compose_parse.block_sequence(service_block, "depends_on")
    if bare_items:
        for dep in bare_items:
            findings.append(_bare_finding(service, compose_file, dep))
        return findings

    mapping_keys = compose_parse.block_mapping_keys(service_block, "depends_on")
    if not mapping_keys:
        return findings

    depends_on_block = compose_parse.block_subblock(service_block, "depends_on")
    for dep in mapping_keys:
        entry_block = compose_parse.block_subblock(depends_on_block, dep)
        condition = compose_parse.block_scalar(entry_block, "condition")
        if condition is None:
            findings.append(_weak_finding(service, compose_file, dep))
            continue
        cond_value = condition.strip()
        if cond_value == _CONFORMING_CONDITION:
            continue
        if cond_value == _WEAK_CONDITION:
            findings.append(_weak_finding(service, compose_file, dep))
            continue
        if cond_value == _COMPLETION_CONDITION:
            findings.append(_completion_finding(service, compose_file, dep))
            continue
        findings.append(_unreadable_condition_finding(service, compose_file, dep, condition))
    return findings


def check_depends_on(repo_root: str, compose_files: list[str]) -> list[dict]:
    """One finding per (compose file, service, dependency). `compose_files`
    is discovered ONCE by the caller (`docker_checker.py`) and passed
    down here rather than re-discovered. Never raises."""
    findings: list[dict] = []
    for path in compose_files:
        text = compose_parse.read_compose_text(path)
        rel = os.path.relpath(path, repo_root)
        for service, block in compose_parse.iter_services(text):
            findings.extend(_evaluate_service_depends_on(service, rel, block))
    return findings


__all__ = ["check_depends_on"]
