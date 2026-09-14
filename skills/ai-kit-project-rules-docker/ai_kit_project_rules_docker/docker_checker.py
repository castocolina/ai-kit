"""This skill's aggregator (REQ-rules-docker), plan 13-01's tracer subject.

Scope boundary: this skill checks the FORM of a repo's local-dev Docker
workflow conventions and never runs, builds or inspects a container, and it
evaluates root-level assets only.

`check_docker_rules(repo_root)` is a flat-list aggregator plans 13-02 and
13-03 extend by appending calls inside the APPLICABLE branch below (never
by adding a check ahead of the gate): the applicability gate (D-D4) is
evaluated FIRST and short-circuits with an empty list when it does not
hold; the checks this plan and plan 13-02 own then extend the findings
list. Plan 13-02 REPOINTED clause (i) at `compose_parse`'s
`BASE_COMPOSE_FILENAMES`/`LOCAL_DEV_COMPOSE_FILENAMES` tuples (D-D6) --
the gate and compose-file discovery read ONE list now, never two --
and this module discovers the repo's compose files ONCE, passing that
same list down to every check plan 13-02/13-03 append.

Every finding this module returns carries EXACTLY D-D5's field set:
`category`, `issue`, `criticality`, `summary`, `recommendation`,
`needs_research`. D-D3's identifier discipline is pinned in BOTH
directions here: the target-family findings carry `target` (a real
Makefile target name, exactly the sibling `ai-kit-project-rules-makefile`
skill's meaning of that key -- the one place in this skill it is right),
and the runbook finding does NOT carry it (it is about a file, not a
target). `remediation.py`'s `build_remediation` reads
`finding.get("target", finding.get("category"))`, so dropping `target`
from the family findings collapses N missing targets onto one remediate
id, and adding it to the runbook finding points that id at an unrelated
Makefile target name. Plan 13-02's compose-derived findings (healthcheck
bounds, `depends_on` discipline) sit on the PROHIBITED side of D-D3:
none of them carries `target` either -- they are about a compose service
and key/dependency, not a Makefile target, and carry `service`/
`compose_file`/non-identifying data fields instead.
"""

from __future__ import annotations

import os

from ai_kit_rules_common.criticality import CRITICALITY_MEDIUM
from ai_kit_rules_common.makefile_parse import parse_makefile_targets_ordered

from . import compose_parse, healthcheck

# D-D1 -- the eight-target family is a FIXED NAME LIST, matched exactly
# after normalization -- never a shape rule, never the Makefile sibling's
# `_DOCKER_UP_SHAPE_RE` (that answers a different question: is any
# docker-up-shaped target preceded by a build step). Declaration order is
# what the finding text, the tests, and plan 13-04's `SKILL.md` all read.
DOCKER_TARGET_FAMILY = (
    "docker-up",
    "docker-health",
    "docker-stop",
    "docker-clean",
    "docker-prune",
    "docker-events-up",
    "docker-events-monitor",
    "docker-events-test",
)

# D-06 / design spec: the runbook's required path, relative to repo_root.
RUNBOOK_RELATIVE_PATH = os.path.join("docker", "local", "README.md")

_RUNBOOK_RECOMMENDATION = (
    "Add docker/local/README.md documenting this repo's local-dev Docker "
    "runbook: how an agent interacts with the containers, which networks "
    "and secrets the local-dev stack requires, how to copy .env files into "
    "a new worktree, and whether a new worktree needs fresh containers or "
    "can reuse a sibling worktree's already-running ones."
)


def normalize_target_name(name: str) -> str:
    """D-D1's normalization: casefold, then fold `_` to `-`."""
    return name.casefold().replace("_", "-")


def _normalized_targets_present(makefile_path: str) -> set[str]:
    """D-D23 -- the unreadable-file wrap lives HERE, not in the shared
    parser. `parse_makefile_targets_ordered` guards only ABSENCE
    (`if not os.path.isfile(path): return []`) and then reads with
    `open(path, encoding="utf-8")` inside no `try`, so a binary or
    non-UTF-8 Makefile raises `UnicodeDecodeError` and an
    unreadable-permission one raises `OSError` straight out of the shared
    module. Catch exactly those two types -- never a bare `except:`, never
    `except Exception` -- and treat a failed read as "no targets
    declared", the same answer an absent or empty Makefile yields."""
    try:
        targets = parse_makefile_targets_ordered(makefile_path)
    except (OSError, UnicodeDecodeError):
        return set()
    return {normalize_target_name(name) for name in targets}


def repo_uses_docker(repo_root: str, makefile_path: str) -> bool:
    """D-D4's applicability gate, evaluated FIRST and short-circuiting.

    Root-level evidence only -- a bounded, constant number of stats
    against explicitly-joined root paths (plus one non-recursive listing
    of the root directory itself to catch `Dockerfile.*` variants), never
    a directory walk and never a glob that descends. This is the gate
    that keeps ai-kit's own `tests/e2e/docker/Dockerfile` (nested) and its
    `e2e-docker` Makefile target (docker-SUFFIXED) from tripping a false
    positive, and it is the load-bearing decision of this plan: without
    it, every non-Docker repo -- including this one -- would be handed
    nine findings on its first run.
    """
    for name in compose_parse.BASE_COMPOSE_FILENAMES + compose_parse.LOCAL_DEV_COMPOSE_FILENAMES:
        if os.path.isfile(os.path.join(repo_root, name)):
            return True

    try:
        root_entries = os.listdir(repo_root)
    except OSError:
        root_entries = []
    for entry in root_entries:
        if (entry == "Dockerfile" or entry.startswith("Dockerfile.")) and os.path.isfile(
            os.path.join(repo_root, entry)
        ):
            return True

    if os.path.isdir(os.path.join(repo_root, "docker")):
        return True

    # Clause (iv): a PREFIX rule over the D-D1-normalized name, never a
    # substring test -- a substring rule would match a docker-suffixed
    # target like `e2e-docker` and make ai-kit's own repo a false
    # positive.
    for name in _normalized_targets_present(makefile_path):
        if name == "docker" or name.startswith("docker-"):
            return True

    return False


def _target_family_findings(makefile_path: str) -> list[dict]:
    """D-D2: one finding PER missing family member, in the family tuple's
    own declaration order -- never alphabetically, never an aggregate
    finding carrying a list -- so two runs over the same repo produce
    byte-identical output."""
    present = _normalized_targets_present(makefile_path)
    findings: list[dict] = []
    for name in DOCKER_TARGET_FAMILY:
        if name in present:
            continue
        recommendation = (
            f"Add a Makefile target named '{name}' -- one of the eight "
            f"members of this repo's house docker-* local-dev target "
            f"family (docker-up, docker-health, docker-stop, docker-clean, "
            f"docker-prune, docker-events-up, docker-events-monitor, "
            f"docker-events-test). '{name}' is currently missing."
        )
        findings.append(
            {
                "category": "docker-target-family",
                "issue": "docker_target_missing",
                "criticality": CRITICALITY_MEDIUM,
                "target": name,
                "summary": recommendation,
                "recommendation": recommendation,
                "needs_research": False,
            }
        )
    return findings


def _runbook_finding(repo_root: str) -> dict | None:
    """D-D5's runbook check. No `target` key (D-D3): this finding is about
    a file, not a Makefile target."""
    runbook_path = os.path.join(repo_root, RUNBOOK_RELATIVE_PATH)
    if os.path.isfile(runbook_path):
        return None
    return {
        "category": "docker-local-runbook",
        "issue": "docker_runbook_missing",
        "criticality": CRITICALITY_MEDIUM,
        "summary": _RUNBOOK_RECOMMENDATION,
        "recommendation": _RUNBOOK_RECOMMENDATION,
        "needs_research": False,
    }


def check_docker_rules(repo_root: str) -> list[dict]:
    """Return a flat list of findings for `repo_root`.

    Evaluates D-D4's applicability gate first and returns an empty list
    immediately when it does not hold. Otherwise resolves the Makefile
    path ONCE and passes it down to each check, so a later plan cannot
    accidentally re-run the gate with a different answer. Degradation,
    not crashes: an absent Makefile yields all eight target-missing
    findings because the shared parsers already return an empty result
    for an absent file; an unreadable one yields the same answer via the
    D-D23 wrap above.

    Discovers this repo's compose files ONCE via `compose_parse.
    discover_compose_files` (D-D6's one filename list) and passes that
    same list down to every compose-derived check plan 13-02 appends --
    plan 13-03 appends a third consumer of that same list rather than
    re-discovering it.
    """
    makefile_path = os.path.join(repo_root, "Makefile")
    if not repo_uses_docker(repo_root, makefile_path):
        return []

    findings: list[dict] = []
    findings.extend(_target_family_findings(makefile_path))
    runbook = _runbook_finding(repo_root)
    if runbook is not None:
        findings.append(runbook)

    compose_files = compose_parse.discover_compose_files(repo_root)
    findings.extend(healthcheck.check_healthcheck_bounds(repo_root, compose_files))
    return findings


__all__ = [
    "DOCKER_TARGET_FAMILY",
    "RUNBOOK_RELATIVE_PATH",
    "check_docker_rules",
    "normalize_target_name",
    "repo_uses_docker",
]
