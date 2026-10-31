#!/usr/bin/env python3
"""Scope detection for the goal-prompt skill: GSD phases, OpenGSD identity, superpowers plans.

stdlib only, pure over injected JSON plus read-only repo reads. Nothing here runs a subprocess
or touches the network. Phase state comes from three sources (D-24): the `roadmap analyze`
JSON (order, disk_status, has_context, plan_count), a `*-SPEC.md` glob (no has_spec field
exists), and the `init phase-op` JSON (has_reviews, has_verification). Directories are
repo-relative; phase_dir and state_path from phase-op are never read.
"""

from __future__ import annotations

import glob
import os
import re
from collections.abc import Sequence
from typing import Any, NamedTuple

from gp_common import phase_key

OPENGSD_PACKAGE = "@opengsd/gsd-core"


class Phase(NamedTuple):
    number: str
    name: str
    dir: str | None
    has_spec: bool
    has_context: bool
    plan_count: int
    has_reviews: bool
    has_verification: bool
    disk_status: str
    cross_ai_plans: int


def _read_text(path: str) -> str:
    """File text as UTF-8, or "" when it cannot be read or decoded."""
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return ""


def _files(directory: str, pattern: str) -> list[str]:
    return sorted(glob.glob(os.path.join(glob.escape(directory), pattern)))


def _same_number(prefix: str, number: str) -> bool:
    try:
        return phase_key(prefix) == phase_key(number)
    except ValueError:
        return False


def _phase_dir(repo: str, number: str) -> str | None:
    """The phase directory whose numeric prefix equals `number`, or None when absent."""
    root = os.path.join(glob.escape(repo), ".planning", "phases")
    for path in sorted(glob.glob(os.path.join(root, "*-*"))):
        prefix = os.path.basename(path).split("-", 1)[0]
        if os.path.isdir(path) and _same_number(prefix, number):
            return path
    return None


def _has_cross_ai(path: str) -> bool:
    """True when the first frontmatter block holds a line exactly `cross_ai: true`."""
    lines = _read_text(path).splitlines()
    if not lines or lines[0].rstrip() != "---":
        return False
    for line in lines[1:]:
        if line.rstrip() == "---":
            return False
        if line.rstrip() == "cross_ai: true":
            return True
    return False


def _roadmap_entries(roadmap: Any) -> list[dict[str, Any]]:
    """The roadmap phase objects; ValueError for anything that is not a roadmap."""
    phases = roadmap.get("phases") if isinstance(roadmap, dict) else None
    if not isinstance(phases, list) or not all(isinstance(p, dict) for p in phases):
        raise ValueError("roadmap JSON must be an object with a phases list")
    for phase in phases:
        phase_key(str(phase.get("number", "")))
    return phases


def _phase(repo: str, entry: dict[str, Any], ops: dict[str, Any]) -> Phase:
    number = str(entry.get("number", ""))
    doc = ops.get(number)
    doc = doc if isinstance(doc, dict) else {}
    directory = _phase_dir(repo, number)
    count = entry.get("plan_count")
    cross_ai = 0
    if directory is not None:
        cross_ai = sum(1 for path in _files(directory, "*-PLAN.md") if _has_cross_ai(path))
    relpath = None
    if directory is not None:
        relpath = os.path.relpath(directory, repo).replace(os.sep, "/")
    return Phase(
        number=number,
        name=str(entry.get("name", "")),
        dir=relpath,
        has_spec=directory is not None and bool(_files(directory, "*-SPEC.md")),
        has_context=entry.get("has_context") is True,
        plan_count=count if isinstance(count, int) else 0,
        has_reviews=doc.get("has_reviews") is True,
        has_verification=doc.get("has_verification") is True,
        disk_status=str(entry.get("disk_status", "")),
        cross_ai_plans=cross_ai,
    )


def load_phases(
    repo: str, roadmap: Any, phase_ops: Any, numbers: Sequence[str] | None
) -> list[Phase]:
    """Phases in numeric order (16 < 16.1 < 17), restricted to `numbers` when given.

    A requested number missing from the roadmap raises ValueError; it is never dropped silently.
    """
    by_key = {phase_key(str(e.get("number", ""))): e for e in _roadmap_entries(roadmap)}
    if numbers is None:
        keys = sorted(by_key)
    else:
        for number in numbers:
            if phase_key(number) not in by_key:
                raise ValueError(f"requested phase {number} is not in the roadmap")
        keys = sorted({phase_key(number) for number in numbers})
    ops = phase_ops if isinstance(phase_ops, dict) else {}
    return [_phase(repo, by_key[key], ops) for key in keys]


def opengsd_identity(identity: Any) -> str:
    """"opengsd" only for the exact package name; anything else is "unverified" (26 D-18/D-19)."""
    if isinstance(identity, dict) and identity.get("packageName") == OPENGSD_PACKAGE:
        return "opengsd"
    return "unverified"


class Plan(NamedTuple):
    file: str
    title: str
    depends_on: tuple[str, ...]
    free_text: tuple[str, ...]
    tasks: int


_TITLE_RE = re.compile(r"^# (.+)$", re.MULTILINE)
_TASK_RE = re.compile(r"^### Task\b", re.MULTILINE)
_DEPENDS_RE = re.compile(r"^\*\*Depends on:\*\*[ \t]*(.*)$", re.MULTILINE)
_TICK_RE = re.compile(r"`([^`\n]+)`")


def _parse_depends(text: str, known: frozenset[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(linked filenames, free text) from the first `**Depends on:**` line. Exact names only.

    The free text is the rest of the line as ONE entry (linked names removed, other backticks
    unwrapped), so the work-set question shows a sentence, not split fragments.
    """
    match = _DEPENDS_RE.search(text)
    if match is None or match.group(1).strip().lower().rstrip(".") in ("", "none"):
        return (), ()
    line = match.group(1)
    links = tuple(dict.fromkeys(name for name in _TICK_RE.findall(line) if name in known))
    rest = _TICK_RE.sub(lambda m: "" if m.group(1) in known else m.group(1), line)
    rest = rest.strip(" \t,;")
    return links, ((rest,) if rest else ())


def load_plans(repo: str) -> list[Plan]:
    """Superpowers plans under docs/superpowers/plans, sorted by filename. Read-only."""
    pattern = os.path.join(glob.escape(repo), "docs", "superpowers", "plans", "*.md")
    paths = sorted((p for p in glob.glob(pattern) if os.path.isfile(p)), key=os.path.basename)
    texts = {os.path.basename(path): _read_text(path) for path in paths}
    known = frozenset(texts)
    loaded = []
    for name, text in texts.items():
        title = _TITLE_RE.search(text)
        links, free = _parse_depends(text, known)
        loaded.append(Plan(file=name, title=title.group(1).strip() if title else "",
                           depends_on=links, free_text=free,
                           tasks=len(_TASK_RE.findall(text))))
    return loaded


def execution_order(plans: Sequence[Plan]) -> list[str]:
    """Stable topological order (Kahn): always the smallest ready filename. A cycle raises."""
    names = {plan.file for plan in plans}
    pending = {plan.file: {dep for dep in plan.depends_on if dep in names} for plan in plans}
    order: list[str] = []
    while pending:
        ready = [name for name, deps in pending.items() if not deps]
        if not ready:
            raise ValueError("dependency cycle among: " + ", ".join(sorted(pending)))
        name = min(ready)
        order.append(name)
        del pending[name]
        for deps in pending.values():
            deps.discard(name)
    return order


def dependents(plans: Sequence[Plan], file: str) -> list[str]:
    """Plans that transitively depend on `file`, in execution order; independent ones are absent."""
    children: dict[str, list[str]] = {}
    for plan in plans:
        for dep in plan.depends_on:
            children.setdefault(dep, []).append(plan.file)
    found: set[str] = set()
    stack = [file]
    while stack:
        for child in children.get(stack.pop(), []):
            if child not in found:
                found.add(child)
                stack.append(child)
    return [name for name in execution_order(plans) if name in found]


class ScopeInputs(NamedTuple):
    roadmap: Any
    phase_ops: Any
    identity: Any
    work_kind: str | None
    numbers: Sequence[str] | None


_ASK = {
    "both": "which work set is meant: GSD phases or superpowers plans?",
    "none": "No GSD phases or superpowers plans were found; name the work set as free text.",
}


def scope_kind(*, has_planning: bool, identity: str, plans_count: int,
               work_kind: str | None) -> str:
    """opengsd | gsd-unproven | superpowers | both | none, from what exists and the work set."""
    if work_kind not in (None, "phases", "plans"):
        raise ValueError("work_kind must be phases or plans")
    gsd = has_planning and work_kind != "plans"
    superpowers = plans_count > 0 and work_kind != "phases"
    if gsd and superpowers:
        return "both"
    if gsd:
        return "opengsd" if identity == "opengsd" else "gsd-unproven"
    return "superpowers" if superpowers else "none"


def detect_scope(repo: str, inputs: ScopeInputs) -> dict[str, Any]:
    """The contract `scope` object for `repo`. Read-only: nothing is written to the project."""
    has_planning = os.path.isfile(os.path.join(repo, ".planning", "PROJECT.md"))
    identity = opengsd_identity(inputs.identity)
    plans = load_plans(repo)
    kind = scope_kind(has_planning=has_planning, identity=identity, plans_count=len(plans),
                      work_kind=inputs.work_kind)
    phases: list[Phase] = []
    if has_planning and inputs.work_kind != "plans" and inputs.roadmap is not None:
        phases = load_phases(repo, inputs.roadmap, inputs.phase_ops, inputs.numbers)
    shown_plans = plans if inputs.work_kind != "phases" else []
    if kind in ("opengsd", "gsd-unproven"):
        order = [phase.number for phase in phases]
    elif kind == "superpowers":
        order = execution_order(plans)
    else:
        order = []
    return {
        "kind": kind,
        "identity": identity,
        "ask": _ASK.get(kind),
        "phases": [phase._asdict() for phase in phases],
        "plans": [plan._asdict() for plan in shown_plans],
        "order": order,
    }


__all__ = [
    "OPENGSD_PACKAGE",
    "Phase",
    "Plan",
    "ScopeInputs",
    "dependents",
    "detect_scope",
    "execution_order",
    "load_phases",
    "load_plans",
    "opengsd_identity",
    "scope_kind",
]
