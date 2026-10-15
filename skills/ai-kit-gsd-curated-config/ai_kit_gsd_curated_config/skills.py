"""Pure skill affinity resolution (D-02, D-03, D-32, D-33).

Reference forms: ``skills/<name>`` (project), ``global:<name>`` (host global root),
``global:<plugin>:<name>`` (Claude plugin). Missing or unaddressable skills are omitted
silently and never named in output (D-03).
"""
from __future__ import annotations

from typing import Any, NamedTuple

from . import presets

_KIND_ORDER = ("project", "global", "plugin")


class _ResolveCtx(NamedTuple):
    inv: dict
    facts: dict[str, bool]
    cap: int
    agents_known: dict
    agent_skills: dict[str, list[str]]
    seen_per_agent: dict[str, set[str]]
    notes: list[dict]


def _family_shape_problem(family: Any, index: int, seen_ids: set[str]) -> str | None:
    problem: str | None = None
    if not isinstance(family, dict):
        problem = f"families[{index}] must be an object"
    fam_id = family.get("id") if isinstance(family, dict) else None
    if problem is None and (not isinstance(fam_id, str) or not fam_id):
        problem = f"families[{index}].id must be a non-empty string"
    if problem is None and fam_id in seen_ids:
        problem = f"duplicate family id {fam_id!r}"
    if problem is None and isinstance(fam_id, str):
        seen_ids.add(fam_id)
        skill_names = family.get("skills")
        if not isinstance(skill_names, list) or not all(isinstance(s, str) for s in skill_names):
            problem = f"families[{index}].skills must be a list of strings"
        agents = family.get("agents")
        if problem is None and (
            not isinstance(agents, list) or not all(isinstance(a, str) for a in agents)
        ):
            problem = f"families[{index}].agents must be a list of strings"
        when = family.get("when")
        if problem is None and when is not None and when not in presets.GATES:
            problem = f"families[{index}].when must be null or one of {presets.GATES!r}"
    return problem


def validate_affinity(doc: Any) -> str | None:
    """Returns an error string, or ``None`` when ``doc`` matches the affinity schema."""
    problem: str | None = None
    if not isinstance(doc, dict):
        problem = "top-level JSON is not an object"
    version = doc.get("schema_version") if isinstance(doc, dict) else None
    if problem is None and (
        not isinstance(version, int) or isinstance(version, bool) or version != 1
    ):
        problem = "schema_version must be exactly int 1"
    as_of = doc.get("as_of") if isinstance(doc, dict) else None
    if problem is None and not isinstance(as_of, str):
        problem = "as_of must be a string"
    families = doc.get("families") if isinstance(doc, dict) else None
    if problem is None and not isinstance(families, list):
        problem = "families must be a list"
    if problem is None and isinstance(families, list):
        seen_ids: set[str] = set()
        for index, family in enumerate(families):
            problem = _family_shape_problem(family, index, seen_ids)
            if problem:
                break
    return problem


def skill_facts(inv: dict, prior: list, existing: dict) -> dict[str, bool]:
    """Gate facts for affinity ``when`` fields (18 D-33, D-36)."""
    tdd: Any = presets.get_dotted(existing, "workflow.tdd_mode")
    for entry in prior:
        if isinstance(entry, dict) and entry.get("key") == "workflow.tdd_mode":
            tdd = entry.get("value")
            break
    project = inv.get("project") if isinstance(inv.get("project"), dict) else {}
    backend = inv.get("system_one_backend")
    detected = (
        isinstance(backend, dict)
        and isinstance(backend.get("detected"), bool)
        and backend["detected"]
    )
    return {
        "tdd_mode": bool(tdd),
        "frontend": bool(project.get("frontend", False)),
        "db": bool(project.get("db", False)),
        "system_one_backend": detected,
    }


def locate(name: str, inv: dict) -> dict | None:
    """Best installed, addressable inventory row for ``name`` (project, global, plugin)."""
    rows = inv.get("skills")
    if not isinstance(rows, list):
        return None
    matches = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("name") == name
        and row.get("addressable") is True
    ]
    if not matches:
        return None

    def _rank(row: dict) -> tuple[int, str]:
        kind = row.get("root_kind")
        order = _KIND_ORDER.index(kind) if isinstance(kind, str) and kind in _KIND_ORDER else 99
        root = row.get("root") if isinstance(row.get("root"), str) else ""
        return order, root

    return min(matches, key=_rank)


def reference_for(entry: dict) -> str:
    """gsd-core skill reference string for an inventory row (D-02, D-32)."""
    name = entry["name"]
    kind = entry.get("root_kind")
    if kind == "project":
        return f"skills/{name}"
    if kind == "global":
        return f"global:{name}"
    plugin = entry.get("plugin")
    if kind == "plugin" and isinstance(plugin, str) and plugin:
        return f"global:{plugin}:{name}"
    return f"global:{name}"


def _wire_agent(ctx: _ResolveCtx, fam_id: str, agent: str, skill_names: list) -> None:
    if agent not in ctx.agents_known:
        ctx.notes.append({
            "kind": "affinity_agent",
            "key": f"agent_skills.{agent}",
            "text": f"dropped unknown agent {agent} from family {fam_id}",
        })
        return
    bucket = ctx.seen_per_agent.setdefault(agent, set())
    names = ctx.agent_skills.setdefault(agent, [])
    for skill_name in skill_names:
        if not isinstance(skill_name, str) or skill_name in bucket:
            continue
        if locate(skill_name, ctx.inv) is None or len(names) >= ctx.cap:
            continue
        bucket.add(skill_name)
        names.append(skill_name)


def _resolve_family(family: dict, ctx: _ResolveCtx) -> None:
    when = family.get("when")
    if when is not None and not ctx.facts.get(when, False):
        return
    fam_id = family.get("id", "")
    skill_names = family.get("skills")
    agents = family.get("agents")
    if not isinstance(skill_names, list) or not isinstance(agents, list):
        return
    for agent in agents:
        if isinstance(agent, str):
            _wire_agent(ctx, fam_id, agent, skill_names)


def resolve(
    affinity: dict,
    inv: dict,
    facts: dict[str, bool],
    rigor: str,
) -> tuple[dict[str, list[str]], list[dict]]:
    """Map agents to deduped bare skill names in affinity file order, capped by rigor."""
    agents_known = inv.get("gsd_core", {}).get("agent_to_phase_type", {})
    if not isinstance(agents_known, dict):
        agents_known = {}
    ctx = _ResolveCtx(
        inv=inv,
        facts=facts,
        cap=presets.SKILL_CAPS.get(rigor, presets.SKILL_CAPS["standard"]),
        agents_known=agents_known,
        agent_skills={},
        seen_per_agent={},
        notes=[],
    )
    families = affinity.get("families")
    if not isinstance(families, list):
        return {}, ctx.notes
    for family in families:
        if isinstance(family, dict):
            _resolve_family(family, ctx)
    return {agent: names for agent, names in ctx.agent_skills.items() if names}, ctx.notes
