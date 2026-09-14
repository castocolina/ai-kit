"""Generic remediation payload builder.

Turns a `check()`-shaped report into an ordered, auto-apply-annotated
hand-off list. Reads only fields a rule-checking module already attaches to
each finding -- never looks anything up in a rules module itself.
"""

from __future__ import annotations

# The set of "structural" finding kinds this builder understands, beyond the
# `workflow` kind. Each is a `report` key whose findings share the same
# field shape (`criticality`, `summary`, `recommendation`/`needs_research`,
# optionally `advisory`/`issue`/`stacks`) and are folded into ONE
# criticality-ordered `remediate` list together -- Phase 15's cross-domain
# orchestrator reads that single list, so a per-kind list would make
# ordering across domains impossible. Currently the sibling
# `ai-kit-project-rules-makefile` skill's kind, `ai-kit-project-rules-precommit`'s
# (Phase 11), and `ai-kit-project-rules-arch`'s (Phase 12) -- the arch skill
# never sets the `target` identifier key its findings would otherwise be
# tempted to carry, so its `id` always derives from `category`; later phases
# append their own kind to this tuple rather than forking a second loop.
# `ai-kit-project-rules-docker`'s (Phase 13) sets `target` on its
# target-family findings only, exactly like the makefile skill's meaning
# of that key, and never on its runbook finding.
# `ai-kit-project-rules-cicd`'s (Phase 14) sets NO identifier key on any
# finding at all -- three of its four reuse surfaces are not Makefile
# targets, so a `target` key would mean a Makefile target name on some
# findings and a hook id/npm script/Gradle task on others, the exact
# per-surface meaning flip D-D3 exists to prevent. Its `id` always
# derives from `category`.
STRUCTURAL_KINDS = ("makefile", "precommit", "arch", "docker", "cicd")


def build_remediation(report: dict) -> dict:
    """Build `{"remediate": [...ordered...], "blocked": [...]}` from `report`.

    `workflow`-kind findings with `status` in `("missing", "near_miss")`
    become `remediate` entries -- `auto_apply` is `True` for `missing`,
    `False` for `near_miss`; `"present"`/`"not_applicable"` findings are
    skipped. `matched_signals` is carried forward so a near-miss
    confirmation has real evidence to name.

    Every kind in `STRUCTURAL_KINDS` (both `"target"`- and `"category"`-
    keyed findings, treated identically) branches ONLY on
    `recommendation`/`needs_research`, never on `present` or on which
    identifying key is set: any finding with a non-`None` `recommendation`
    becomes a `remediate` entry; any finding with `needs_research=True` and
    no `recommendation` goes into `blocked`, carrying its
    `criticality`/`summary`/identifier/`"stacks"` list forward verbatim.
    The iterated key is used verbatim as each entry's `kind` value, so a
    `precommit`-kind finding produces a `remediate`/`blocked` entry carrying
    `kind: "precommit"`, never re-labelled to `"makefile"`.

    `auto_apply` is `True` UNLESS the finding carries `advisory: True`, in
    which case it is `False` -- additive: a finding with no `advisory` key
    behaves exactly as it always has (`auto_apply=True`). A finding that is
    inherently a best-effort suggestion (e.g. the Makefile ordering
    heuristic) must never be presented to a caller as safe to apply
    automatically.

    Every structural-kind `remediate` entry also carries `issue`
    (`finding.get("issue")`, `None` when the finding has none) forward
    verbatim. `id` is a human-readable LABEL, not a unique key -- `remediate`
    has always been one heterogeneous list in which a `workflow` entry and a
    structural entry can share an `id`, and two DIFFERENT structural
    findings (e.g. the inherited `chain_incomplete` and an alias-family
    `alias_chain_incomplete` finding) can legitimately both identify as the
    same target. `(kind, id, issue)` is what tells two entries apart, not
    `id` alone.

    Every kind's `remediate` entries are built into ONE list, then sorted by
    `criticality` ascending, spanning every kind present in `report`
    together -- never separately-ordered lists. Returns a dict, never a
    bare list.
    """
    remediate: list[dict] = []
    blocked: list[dict] = []

    for finding in report.get("workflow", []):
        status = finding.get("status")
        if status not in ("missing", "near_miss"):
            continue
        remediate.append(
            {
                "kind": "workflow",
                "id": finding["id"],
                "status": status,
                "criticality": finding["criticality"],
                "summary": finding["summary"],
                "matched_signals": finding.get("matched_signals", []),
                "auto_apply": status == "missing",
            }
        )

    for kind in STRUCTURAL_KINDS:
        for finding in report.get(kind, []):
            identifier = finding.get("target", finding.get("category"))
            recommendation = finding.get("recommendation")
            if recommendation is not None:
                remediate.append(
                    {
                        "kind": kind,
                        "id": identifier,
                        "criticality": finding["criticality"],
                        "summary": finding["summary"],
                        "issue": finding.get("issue"),
                        "auto_apply": not finding.get("advisory", False),
                    }
                )
            elif finding.get("needs_research"):
                blocked.append(
                    {
                        "kind": kind,
                        "id": identifier,
                        "criticality": finding["criticality"],
                        "summary": finding["summary"],
                        "stacks": finding.get("stacks", []),
                    }
                )

    remediate.sort(key=lambda entry: entry["criticality"])
    return {"remediate": remediate, "blocked": blocked}


__all__ = ["STRUCTURAL_KINDS", "build_remediation"]
