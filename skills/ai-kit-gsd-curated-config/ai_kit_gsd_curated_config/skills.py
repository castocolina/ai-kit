"""Pure skill affinity resolution (D-02, D-03, D-32, D-33).

Reference forms: ``skills/<name>`` (project), ``global:<name>`` (host global root),
``global:<plugin>:<name>`` (Claude plugin). Missing or unaddressable skills are omitted
silently and never named in output (D-03).
"""
from __future__ import annotations

import json
import shlex
from typing import Any, NamedTuple

from . import presets

_KIND_ORDER = ("project", "global", "plugin")
PROPOSAL_CAP = 10

_TRUSTED_ROOTS_WHY_TAIL = (
    "or keep the current value with plan-unset; a declined root leaves the skill wired "
    "and gsd-core skips it (apply reports the warning)"
)


class _ResolveCtx(NamedTuple):
    inv: dict
    facts: dict[str, bool]
    cap: int
    agents_known: dict
    agent_skills: dict[str, list[str]]
    seen_per_agent: dict[str, set[str]]
    notes: list[dict]
    unwired_noted: set[str]


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
    raw_project = inv.get("project")
    project = raw_project if isinstance(raw_project, dict) else {}
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


def _addressable_rows(name: str, inv: dict) -> list[dict]:
    rows = inv.get("skills")
    if not isinstance(rows, list):
        return []
    return [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("name") == name
        and row.get("addressable") is True
    ]


def _has_usable_project_copy(name: str, inv: dict) -> bool:
    return any(
        row.get("root_kind") == "project" and not row.get("escapes_root")
        for row in _addressable_rows(name, inv)
    )


def _escaping_project_only(name: str, inv: dict) -> bool:
    rows = _addressable_rows(name, inv)
    if not rows:
        return False
    has_escaping = any(
        row.get("root_kind") == "project" and row.get("escapes_root") for row in rows
    )
    if not has_escaping:
        return False
    has_other = any(
        row.get("root_kind") in ("global", "plugin")
        or (row.get("root_kind") == "project" and not row.get("escapes_root"))
        for row in rows
    )
    return not has_other


def locate(name: str, inv: dict) -> dict | None:
    """Best installed, addressable inventory row for ``name`` (project, global, plugin)."""
    matches = _addressable_rows(name, inv)
    matches = [
        row
        for row in matches
        if not (row.get("root_kind") == "project" and row.get("escapes_root"))
    ]
    if not matches:
        return None

    def _rank(row: dict) -> tuple[int, str]:
        kind = row.get("root_kind")
        order = _KIND_ORDER.index(kind) if isinstance(kind, str) and kind in _KIND_ORDER else 99
        root = row.get("root")
        return order, root if isinstance(root, str) else ""

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


def existing_roots(inv: dict) -> list[str]:
    """Recorded ``agent_skills_security.trusted_global_roots`` from the inventory."""
    existing = inv.get("existing_config")
    if not isinstance(existing, dict):
        return []
    values = existing.get("values")
    if not isinstance(values, dict):
        return []
    sec = values.get("agent_skills_security")
    if not isinstance(sec, dict):
        return []
    roots = sec.get("trusted_global_roots")
    if not isinstance(roots, list):
        return []
    return [item for item in roots if isinstance(item, str)]


def covered(value: str, real_dir: str, roots: list[str]) -> bool:
    """True when an existing trusted root already covers ``value`` (lexical shortcut)."""
    # shortcut: lexical comparison; a root reached only through a symlink is proposed again
    # (harmless duplicate approval); gsd-core canonicalizes roots at use
    for root in roots:
        trimmed = root.rstrip("/")
        if trimmed.startswith("~/"):
            if value == trimmed or value.startswith(trimmed + "/"):
                return True
        elif real_dir == trimmed or real_dir.startswith(trimmed + "/"):
            return True
    return False


def _record_unwired(ctx: _ResolveCtx, skill: str, text: str) -> None:
    if skill in ctx.unwired_noted:
        return
    ctx.unwired_noted.add(skill)
    ctx.notes.append({"kind": "skill_unwired", "key": skill, "text": text})


def unwired_reason(name: str, inv: dict) -> str | None:
    """``None`` when ``name`` can be wired; else the note text (``""``: not installed, silent)."""
    row = locate(name, inv)
    if row is None:
        if _escaping_project_only(name, inv):
            return f"not wired: {name} (its project copy resolves outside the project)"
        return ""
    if (
        row.get("root_kind") == "global"
        and row.get("escapes_root")
        and not _has_usable_project_copy(name, inv)
        and not row.get("real_dir_home")
        and not covered("", row.get("real_dir") or "", existing_roots(inv))
    ):
        return f"not wired: {name} resolves outside the home directory"
    return None


def _can_wire(name: str, ctx: _ResolveCtx) -> bool:
    reason = unwired_reason(name, ctx.inv)
    if reason:
        _record_unwired(ctx, name, reason)
    return reason is None


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
        if len(names) >= ctx.cap or not _can_wire(skill_name, ctx):
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
        unwired_noted=set(),
    )
    families = affinity.get("families")
    if not isinstance(families, list):
        return {}, ctx.notes
    for family in families:
        if isinstance(family, dict):
            _resolve_family(family, ctx)
    return {agent: names for agent, names in ctx.agent_skills.items() if names}, ctx.notes


def wired_skills(resolved: dict[str, list[str]], inv: dict) -> dict[str, dict]:
    """Installed inventory row per wired bare skill name."""
    wired: dict[str, dict] = {}
    for names in resolved.values():
        for name in names:
            if name in wired:
                continue
            row = locate(name, inv)
            if row is not None:
                wired[name] = row
    return wired


def trusted_roots(wired: dict, inv: dict) -> tuple[list[dict], list[dict]]:
    """``needs_choice`` candidates for escaping global skills (18 D-34, D-41)."""
    roots = existing_roots(inv)
    raw: list[dict] = []
    notes: list[dict] = []
    for skill, row in sorted(wired.items()):
        if row.get("root_kind") != "global" or not row.get("escapes_root"):
            continue
        if _has_usable_project_copy(skill, inv):
            continue
        home_rel = row.get("real_dir_home")
        if not isinstance(home_rel, str) or not home_rel:
            continue
        real_dir = row.get("real_dir") if isinstance(row.get("real_dir"), str) else ""
        if covered(home_rel, real_dir, roots):
            continue
        raw.append({
            "value": home_rel,
            "skill": skill,
            "why": f"global skill {skill} resolves outside the configured root",
        })
    seen: set[str] = set()
    candidates: list[dict] = []
    for item in sorted(raw, key=lambda entry: entry["value"]):
        if item["value"] in seen:
            continue
        seen.add(item["value"])
        candidates.append(item)
    return candidates, notes


def merged_trusted_roots_why(candidates: list[dict], inv: dict) -> str:
    merged = existing_roots(inv) + [item["value"] for item in candidates]
    payload = json.dumps(merged, separators=(",", ":"))
    return (
        f"approve with plan-set agent_skills_security.trusted_global_roots {shlex.quote(payload)} "
        f"{_TRUSTED_ROOTS_WHY_TAIL}"
    )


def _family_skill_names(affinity: dict) -> set[str]:
    names: set[str] = set()
    families = affinity.get("families")
    if not isinstance(families, list):
        return names
    for family in families:
        if not isinstance(family, dict):
            continue
        skills_list = family.get("skills")
        if isinstance(skills_list, list):
            for skill in skills_list:
                if isinstance(skill, str):
                    names.add(skill)
    return names


def proposals(affinity: dict, inv: dict) -> list[dict]:
    """Capped notes for unknown installed skills (18 D-03)."""
    family = _family_skill_names(affinity)
    rows = inv.get("skills")
    if not isinstance(rows, list):
        return []
    eligible: list[dict] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("addressable") is not True:
            continue
        name = row.get("name")
        if not isinstance(name, str) or name in family or name.startswith("gsd-"):
            continue
        desc = row.get("description")
        if not isinstance(desc, str) or not desc.strip():
            continue
        eligible.append(row)
    eligible.sort(key=lambda item: item["name"])
    notes: list[dict] = []
    for row in eligible[:PROPOSAL_CAP]:
        name = row["name"]
        kind = row.get("root_kind", "")
        desc = row["description"]
        notes.append({
            "kind": "skill_proposal",
            "key": name,
            "text": (
                f"unknown skill {name} ({kind}): {desc}; "
                "wire with plan-set agent_skills.<agent>"
            ),
        })
    extra = len(eligible) - PROPOSAL_CAP
    if extra > 0:
        notes.append({
            "kind": "skill_proposal_more",
            "key": "skills",
            "text": (
                f"{extra} more unknown skills not listed; see the inventory's skills list"
            ),
        })
    return notes


def jev_is_wired(resolved: dict[str, list[str]]) -> bool:
    return any("jev-fast-decision" in names for names in resolved.values())
