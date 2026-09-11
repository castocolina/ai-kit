"""Remediation payload builder (D-01/D-02/D-03/D-08).

Turns a `cli.check()` report (`{"makefile": [...], "workflow": [...]}`)
into an ordered, auto-apply-annotated hand-off for `/agent-md-refactor`.
Adds no new lookup into `rules.py` -- it only reads fields `rule_checker.py`
and `makefile_checker.py` already attach to every finding.
"""

from __future__ import annotations


def build_remediation(report: dict) -> dict:
    """Build `{"remediate": [...ordered...], "blocked": [...]}` from `report`.

    `workflow` findings with `status` in `("missing", "near_miss")` become
    `remediate` entries -- `auto_apply` is `True` for `missing`, `False` for
    `near_miss` (D-08); `"present"`/`"not_applicable"` findings are skipped.
    `matched_signals` is carried forward so a near-miss confirmation has real
    evidence to name.

    `makefile`-kind findings (both `"target"`- and `"category"`-keyed,
    treated identically) branch ONLY on `recommendation`/`needs_research`,
    never on `present` or on which identifying key is set: any finding with
    a non-`None` `recommendation` becomes a `remediate` entry with
    `auto_apply=True`; any finding with `needs_research=True` and no
    `recommendation` goes into `blocked`, carrying its `criticality`/
    `summary`/identifier/`"stacks"` list forward verbatim -- these are never
    handed to `/agent-md-refactor` as if they were actionable.

    Both kinds' `remediate` entries are built into ONE list, then sorted by
    `criticality` ascending (D-02), spanning workflow AND makefile findings
    together -- never two separately-ordered lists. Returns a dict, never a
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
