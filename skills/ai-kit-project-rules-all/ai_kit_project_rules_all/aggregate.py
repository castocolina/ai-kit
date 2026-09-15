"""Pure cross-domain criticality merge (SC4).

Imports `DOMAIN_ORDER` from `.dispatch` (the single source of truth for
iteration/tie-break order) but imports nothing else from `dispatch.py` and
never imports `subprocess` -- this is the pure function SC4's stub test
suite targets directly, with 6 hand-built fixture dicts and zero subprocess
calls.
"""

from __future__ import annotations

from .dispatch import DOMAIN_ORDER


def aggregate(domain_results: dict) -> dict:
    """Merge `domain_results` (one entry per `DOMAIN_ORDER` key, each
    either a real `{"remediate": [...], "blocked": [...]}` payload or a
    D-05 failure-entry marker) into `{"remediate": ..., "blocked": ...,
    "failed": ...}`.

    For each domain in `DOMAIN_ORDER`, a real payload's `remediate` and
    `blocked` entries are folded into two running lists spanning ALL 6
    domains together; a D-05 failure marker (no `"remediate"` key) is
    appended to a running `failed` list instead -- never folded into
    `remediate`/`blocked` (D-02, D-05). After the loop, both `remediate`
    and `blocked` are stable-sorted by `criticality` ascending over the
    WHOLE concatenated list, never per-domain (SC2). Every sorted
    `remediate` entry whose `kind == "workflow"` (the AGENTS.md domain)
    then gets `hand_off = "agent-md-refactor"` set on it -- no other entry
    gets this key (SC3).
    """
    remediate: list[dict] = []
    blocked: list[dict] = []
    failed: list[dict] = []

    for domain in DOMAIN_ORDER:
        result = domain_results[domain]
        if "remediate" in result:
            remediate.extend(result["remediate"])
            blocked.extend(result.get("blocked", []))
        else:
            failed.append(result)

    remediate.sort(key=lambda entry: entry["criticality"])
    blocked.sort(key=lambda entry: entry["criticality"])

    for entry in remediate:
        if entry.get("kind") == "workflow":
            entry["hand_off"] = "agent-md-refactor"

    return {"remediate": remediate, "blocked": blocked, "failed": failed}
