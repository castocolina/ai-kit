#!/usr/bin/env python3
"""Strategy matrix for the goal-prompt skill (GPS-01, SPEC R2; D-10, D-11, D-27).

stdlib only and pure: no subprocess, no file I/O, no network. `RULES` is data, one row per
strategy case (the row ids are the test names). `select` returns one to three ranked strategies
and the requested strategies it had to drop. `wake_primitive` names the loop primitive with the
best survival rank. `derive` computes the two inputs that are never asked (D-11).
"""

from __future__ import annotations

from typing import Any, NamedTuple

__all__ = ["RULES", "MatrixInputs", "derive", "select", "wake_primitive"]

OPENGSD = ("opengsd",)
NON_OPENGSD = ("superpowers", "gsd-unproven", "none")
LOOP_KINDS = ("loop", "schedule", "wake", "os-timer")
NEEDS_KINDS = {"goal": ("goal",), "loop": LOOP_KINDS}
PRIMITIVE_KINDS = {"goal": ("goal",), "loop": LOOP_KINDS, "plain": ("os-timer",)}
NO_PRIMITIVE_REASON = {
    "goal": "no goal primitive on this host, so /goal is never offered",
    "loop": "no loop, schedule or wake primitive on this host",
}
MAX_STRATEGIES = 3


class MatrixInputs(NamedTuple):
    """What the selector reads: scope kind, requested strategy, primitive table, derived flags."""

    scope_kind: str
    user_strategy: str | None
    primitives: list[dict[str, Any]]
    must_outlive: bool
    provable: bool


# A row fires when every predicate that is not None holds. `user: None` means any request.
# `needs` names a primitive kind family that must be present (not absent). `fallback` rows fire
# only when no other row fired.
RULES: tuple[dict[str, Any], ...] = (
    {
        "id": "M01",
        "scopes": OPENGSD,
        "user": (None, "autonomous"),
        "needs": None,
        "outlive": None,
        "provable": None,
        "strategy": "autonomous",
        "rank": 1,
        "reason": "OpenGSD scope: /gsd-autonomous with --from/--to/--only and --converge",
    },
    {
        "id": "M02",
        "scopes": OPENGSD,
        "user": ("goal",),
        "needs": "goal",
        "outlive": None,
        "provable": None,
        "strategy": "goal",
        "rank": 1,
        "reason": "goal requested on an OpenGSD scope",
    },
    {
        "id": "M03",
        "scopes": OPENGSD,
        "user": ("loop",),
        "needs": "loop",
        "outlive": None,
        "provable": None,
        "strategy": "loop",
        "rank": 1,
        "reason": "loop requested on an OpenGSD scope",
    },
    {
        "id": "M02b",
        "scopes": OPENGSD,
        "user": ("goal", "loop"),
        "needs": None,
        "outlive": None,
        "provable": None,
        "strategy": "autonomous",
        "rank": 2,
        "reason": "OpenGSD scope: autonomous second, behind the requested goal or loop",
    },
    {
        "id": "M04",
        "scopes": NON_OPENGSD,
        "user": None,
        "needs": "goal",
        "outlive": None,
        "provable": True,
        "strategy": "goal",
        "rank": 1,
        "reason": "goal primitive, provable by the e2e gate",
    },
    {
        "id": "M05",
        "scopes": NON_OPENGSD,
        "user": None,
        "needs": "goal",
        "outlive": None,
        "provable": False,
        "strategy": "goal",
        "rank": 2,
        "reason": "goal primitive, not provable by e2e: the condition needs a human check",
    },
    {
        "id": "M06",
        "scopes": NON_OPENGSD,
        "user": None,
        "needs": "loop",
        "outlive": True,
        "provable": False,
        "strategy": "loop",
        "rank": 1,
        "reason": "work outlives one session and is not provable: a loop keeps it going",
    },
    {
        "id": "M07",
        "scopes": NON_OPENGSD,
        "user": None,
        "needs": "loop",
        "outlive": True,
        "provable": True,
        "strategy": "loop",
        "rank": 2,
        "reason": "work outlives one session and is provable: a loop keeps it going",
    },
    {
        "id": "M08",
        "scopes": ("gsd-unproven",),
        "user": None,
        "needs": None,
        "outlive": None,
        "provable": None,
        "strategy": "autonomous",
        "rank": 3,
        "label": "unverified",
        "reason": "GSD without proven OpenGSD identity: whether the workflow exists is unverified",
    },
    {
        "id": "M09",
        "scopes": None,
        "user": None,
        "needs": None,
        "outlive": None,
        "provable": None,
        "fallback": True,
        "strategy": "plain",
        "rank": 9,
        "reason": "no strategy fits this host and work; the plain prompt relies on the "
        "OS-timer wake (flagged, unverified)",
    },
    {
        "id": "M11g",
        "scopes": NON_OPENGSD,
        "user": ("goal",),
        "needs": "goal",
        "outlive": None,
        "provable": None,
        "strategy": "goal",
        "rank": 0,
        "reason": "goal requested by the user",
    },
    {
        "id": "M11l",
        "scopes": NON_OPENGSD,
        "user": ("loop",),
        "needs": "loop",
        "outlive": None,
        "provable": None,
        "strategy": "loop",
        "rank": 0,
        "reason": "loop requested by the user",
    },
)


def _best(primitives: list[dict[str, Any]], kinds: tuple[str, ...]) -> dict[str, Any] | None:
    """The non-absent primitive of `kinds` with the highest survival rank; ties keep list order."""
    live = [p for p in primitives if p.get("kind") in kinds and p.get("availability") != "absent"]
    return max(live, key=lambda prim: prim["rank"], default=None)


def _needs_ok(needs: str | None, primitives: list[dict[str, Any]]) -> bool:
    return needs is None or _best(primitives, NEEDS_KINDS[needs]) is not None


def _row_fires(row: dict[str, Any], inputs: MatrixInputs) -> bool:
    if row.get("fallback"):
        return False
    return all(
        (
            row["scopes"] is None or inputs.scope_kind in row["scopes"],
            row["user"] is None or inputs.user_strategy in row["user"],
            _needs_ok(row["needs"], inputs.primitives),
            row["outlive"] is None or row["outlive"] == inputs.must_outlive,
            row["provable"] is None or row["provable"] == inputs.provable,
        )
    )


def _label_for(prim: dict[str, Any] | None) -> str:
    """'unverified' when the primitive row is not available; '' when available or absent."""
    if prim is None or prim["availability"] == "available":
        return ""
    return "unverified"


def _reason(row: dict[str, Any], prim: dict[str, Any] | None) -> str:
    parts = [row["reason"]]
    if prim is not None:
        parts.append(f"primitive {prim['primitive']}")
        if row["strategy"] == "loop" and prim["rank"] == 0:
            parts.append("it dies with the session")
    elif row["strategy"] == "plain":
        parts.append("no OS-timer row on this host")
    return "; ".join(parts)


def _strategy(row: dict[str, Any], inputs: MatrixInputs) -> dict[str, Any]:
    kinds = PRIMITIVE_KINDS.get(row["strategy"])
    prim = _best(inputs.primitives, kinds) if kinds else None
    label = row["label"] if "label" in row else _label_for(prim)
    return {
        "id": row["strategy"],
        "rank": row["rank"],
        "recommended": False,
        "reason": _reason(row, prim),
        "primitive": prim["primitive"] if prim else None,
        "label": label,
        "row": row["id"],
    }


def _ranked(fired: list[tuple[int, dict[str, Any]]]) -> list[dict[str, Any]]:
    """One strategy per id (lower rank wins, an equal rank keeps the earlier row), then order."""
    kept: dict[str, tuple[int, dict[str, Any]]] = {}
    for index, strategy in fired:
        held = kept.get(strategy["id"])
        if held is None or strategy["rank"] < held[1]["rank"]:
            kept[strategy["id"]] = (index, strategy)
    ordered = sorted(kept.values(), key=lambda pair: (pair[1]["rank"], pair[0]))
    return [strategy for _, strategy in ordered][:MAX_STRATEGIES]


def _dropped(inputs: MatrixInputs) -> list[dict[str, str]]:
    """A requested goal or loop whose primitive is missing is reported, never emitted."""
    wanted = inputs.user_strategy
    if wanted in NEEDS_KINDS and not _needs_ok(wanted, inputs.primitives):
        return [{"id": wanted, "reason": NO_PRIMITIVE_REASON[wanted]}]
    return []


def select(inputs: MatrixInputs) -> dict[str, Any]:
    """Ranked strategies (one to three, exactly one recommended) and the dropped requests."""
    fired = [
        (index, _strategy(row, inputs))
        for index, row in enumerate(RULES)
        if _row_fires(row, inputs)
    ]
    if not fired:
        fired = [
            (index, _strategy(row, inputs))
            for index, row in enumerate(RULES)
            if row.get("fallback")
        ]
    strategies = _ranked(fired)
    strategies[0]["recommended"] = True
    return {"strategies": strategies, "dropped": _dropped(inputs)}


def wake_primitive(primitives: list[dict[str, Any]]) -> dict[str, Any]:
    """The loop-capable primitive with the highest survival rank, labelled when not available."""
    prim = _best(primitives, LOOP_KINDS)
    if prim is None:
        return {"primitive": None, "label": ""}
    return {"primitive": prim["primitive"], "label": _label_for(prim)}


def derive(count: int, unattended: bool, e2e_none: bool, mockups: int) -> dict[str, bool]:
    """D-11: outlive for more than one phase or plan or unattended work; provable with e2e only."""
    return {
        "must_outlive": count > 1 or bool(unattended),
        "provable": (not e2e_none) and mockups == 0,
    }
