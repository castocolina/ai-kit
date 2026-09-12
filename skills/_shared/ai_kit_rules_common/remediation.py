"""Generic remediation payload builder.

Turns a `check()`-shaped report into an ordered, auto-apply-annotated
hand-off list. Reads only fields a rule-checking module already attaches to
each finding -- never looks anything up in a rules module itself.
"""

from __future__ import annotations


def build_remediation(report: dict) -> dict:
    """Build `{"remediate": [...ordered...], "blocked": [...]}` from `report`.

    `workflow`-kind findings with `status` in `("missing", "near_miss")`
    become `remediate` entries -- `auto_apply` is `True` for `missing`,
    `False` for `near_miss`; `"present"`/`"not_applicable"` findings are
    skipped. `matched_signals` is carried forward so a near-miss
    confirmation has real evidence to name.

    `makefile`-kind findings (both `"target"`- and `"category"`-keyed,
    treated identically) branch ONLY on `recommendation`/`needs_research`,
    never on `present` or on which identifying key is set: any finding with
    a non-`None` `recommendation` becomes a `remediate` entry with
    `auto_apply=True`; any finding with `needs_research=True` and no
    `recommendation` goes into `blocked`, carrying its `criticality`/
    `summary`/identifier/`"stacks"` list forward verbatim.

    Both kinds' `remediate` entries are built into ONE list, then sorted by
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

    for finding in report.get("makefile", []):
        identifier = finding.get("target", finding.get("category"))
        recommendation = finding.get("recommendation")
        if recommendation is not None:
            remediate.append(
                {
                    "kind": "makefile",
                    "id": identifier,
                    "criticality": finding["criticality"],
                    "summary": finding["summary"],
                    "auto_apply": True,
                }
            )
        elif finding.get("needs_research"):
            blocked.append(
                {
                    "kind": "makefile",
                    "id": identifier,
                    "criticality": finding["criticality"],
                    "summary": finding["summary"],
                    "stacks": finding.get("stacks", []),
                }
            )

    remediate.sort(key=lambda entry: entry["criticality"])
    return {"remediate": remediate, "blocked": blocked}


__all__ = ["build_remediation"]
