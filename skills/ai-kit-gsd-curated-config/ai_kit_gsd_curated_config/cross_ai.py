"""Pure cross-AI execution target selection (18 D-09/D-10/D-15/D-28/D-39).

Imports only ``.presets`` and ``.roles``. Target ids are runner ids; ``RUNNER_CLI`` maps
them to inventory runtimes. The script artifact ``config`` is the sole copy of runner
settings (no parallel ``targets[]`` list).
"""
from typing import NamedTuple

from . import presets, roles

CROSS_AI_COMMAND = "node .planning/scripts/cross-ai.mjs"
SCRIPT_PATH = ".planning/scripts/cross-ai.mjs"
TEMPLATE_NAME = "cross-ai.mjs"
TEMPLATE_VERSION = 2
MIN_TIMEOUT_S = 1800
DEFAULT_PREFER = ("pi", "cursor", "opencode")
RUNNER_CLI = {
    "pi": "pi",
    "cursor": "cursor-agent",
    "opencode": "opencode",
    "codex": "codex",
}
EXEC_DEFAULT_HOSTS = ("claude", "codex")
EXEC_EFFORT_TARGET = "medium"
CROSS_AI_FLAG = "--cross-ai"
NO_TARGET_TEXT = "no installed cross-AI target (pi, cursor-agent, opencode)"
_ROUTER_WHY = "user-curated router (declared purpose: execute)"


class Target(NamedTuple):
    cli: str
    model: str | None
    source: str | None
    why: str
    router_backed: bool
    candidates: list


def _runtime_cands(inv: dict, runner_id: str) -> list:
    runtime = RUNNER_CLI[runner_id]
    return [c for c in inv["candidates"] if c.get("runtime") == runtime]


def _pick_for_runner(runner_id: str, cands: list, rigor: str) -> Target:
    ceiling = roles.host_ceiling(cands, presets.PRICE_PERCENTILE[rigor])
    routers = sorted(
        [
            c
            for c in cands
            if c.get("is_router")
            and c.get("router_confirmed")
            and c.get("name_declared_purpose") == "execute"
        ],
        key=lambda c: c["model"],
    )
    if routers:
        model = routers[0]["model"]
        return Target(runner_id, model, "router-declared", _ROUTER_WHY, True, [])
    pick = roles.best_pick(cands, "execution", EXEC_EFFORT_TARGET, ceiling.value)
    if pick is not None:
        why = roles.pick_why(pick, "execution", EXEC_EFFORT_TARGET, ceiling)
        return Target(runner_id, pick.candidate["model"], "catalog-score", why, False, [])
    fallback = roles.choice_candidates(cands, "execution", ceiling.value)
    return Target(
        runner_id,
        None,
        None,
        "no execution model within ceiling",
        False,
        fallback,
    )


def exec_targets(inv: dict, rigor: str, prefer=DEFAULT_PREFER) -> list[Target]:
    """Preference-ordered execution targets on installed non-host runtimes (18 D-10)."""
    host = inv["host"]
    installed = inv["installed_runtimes"]
    out: list[Target] = []
    for runner_id in prefer:
        if runner_id not in RUNNER_CLI:
            continue
        if runner_id == host:
            continue
        runtime = RUNNER_CLI[runner_id]
        if runtime not in installed:
            continue
        cands = _runtime_cands(inv, runner_id)
        out.append(_pick_for_runner(runner_id, cands, rigor))
    return out


def exec_default(host: str, targets: list) -> tuple[str, str]:
    """D-39 default for ``workflow.cross_ai_execution`` when the flag is omitted."""
    if host in EXEC_DEFAULT_HOSTS:
        if targets:
            names = ", ".join(t.cli for t in targets)
            return ("y", f"D-39: cross-AI execution defaults on {host} with target(s) {names}")
        return ("n", NO_TARGET_TEXT)
    return ("n", f"execution stays on the host for {host} (spec §6)")


def timeout_value(existing) -> int:
    if isinstance(existing, int) and not isinstance(existing, bool) and existing >= MIN_TIMEOUT_S:
        return existing
    return MIN_TIMEOUT_S


def manager_flags_value(existing) -> str:
    if isinstance(existing, str) and existing.strip():
        tokens = existing.split()
        if CROSS_AI_FLAG in tokens:
            return existing
        return existing.strip() + f" {CROSS_AI_FLAG}"
    return CROSS_AI_FLAG


REVIEW_COUNT = {"mvp": 1, "standard": 1, "rigorous": 2}
REVIEW_EFFORT_TARGET = "high"
OPENCODE_EFFORT_EFFECT = (
    "unverified: opencode 2.x run has no --variant flag (Phase 20 risk)"
)
CLAUDE_ALIAS_EFFECT = (
    "alias mapping inferred: Claude Code runs the alias's current model"
)
_REVIEW_ROUTER_WHY = "user-curated router (declared purpose: review)"


class Lane(NamedTuple):
    slug: str
    model_key: str
    effort_key: str | None
    effort: str | None
    model: str
    candidate: dict
    vendor: str | None
    source: str
    why: str


def eligible_lanes(inv: dict) -> list[dict]:
    """Registry lanes (gsd-core review_lanes, D-24) that can host a non-host reviewer."""
    host = inv["host"]
    installed = set(inv.get("installed_runtimes") or [])
    valid = inv["gsd_core"]["valid_keys"]
    accepted = set(valid.get("accepted") or [])
    rejected = set(valid.get("rejected") or [])
    lanes = inv["gsd_core"].get("review_lanes") or []
    out: list[dict] = []
    for lane in lanes:
        if not isinstance(lane, dict):
            continue
        slug = lane.get("slug")
        binary = lane.get("binary")
        model_key = lane.get("model_key")
        if not isinstance(slug, str) or slug in (host, "pi"):
            continue
        if not isinstance(binary, str) or binary not in installed:
            continue
        if not isinstance(model_key, str) or not model_key:
            continue
        if model_key not in accepted or model_key in rejected:
            continue
        if not any(
            c.get("runtime") == binary and not c.get("is_host", False)
            for c in inv.get("candidates") or []
        ):
            continue
        out.append(lane)
    return out


def lane_pool(lane: dict, inv: dict) -> list[dict]:
    binary = lane["binary"]
    pool = [
        c
        for c in inv.get("candidates") or []
        if c.get("runtime") == binary and not c.get("is_host", False)
    ]
    if lane.get("slug") == "claude":
        return roles.claude_alias_rows(pool)
    return pool


def lane_value(lane: dict, candidate: dict) -> str:
    if lane.get("slug") == "claude":
        alias = roles.claude_alias_for(candidate["model"])
        if alias is not None:
            return alias
    return candidate["model"]


def lane_effort(lane: dict, rigor: str, candidate: dict) -> str | None:
    effort_key = lane.get("effort_key")
    if effort_key is None:
        return None
    modes = candidate.get("reasoning_modes") or []
    if rigor == "rigorous" and "xhigh" in modes:
        return "xhigh"
    return lane.get("default_effort")


def _vendor_keep(excluded: set[str | None]):
    def keep(c: dict) -> bool:
        vendor = c.get("vendor")
        return vendor is not None and vendor not in excluded

    return keep


def _review_routers(pool: list[dict]) -> list[dict]:
    return sorted(
        [
            c
            for c in pool
            if c.get("is_router")
            and c.get("router_confirmed")
            and c.get("name_declared_purpose") == "review"
        ],
        key=lambda c: c["model"],
    )


def _lane_rank_key(lane: Lane) -> tuple:
    if lane.source == "router-declared":
        return (0, lane.slug)
    return (1, roles.tie_key(lane.candidate, "review"), lane.slug)


def _lane_row(lane: dict, cand: dict, rigor: str, source: str, why: str) -> Lane:
    return Lane(
        lane["slug"],
        lane["model_key"],
        lane.get("effort_key"),
        lane_effort(lane, rigor, cand),
        lane_value(lane, cand),
        cand,
        cand.get("vendor"),
        source,
        why,
    )


def _pick_lane(lane: dict, inv: dict, rigor: str, excluded: set[str | None]) -> Lane | None:
    pool = lane_pool(lane, inv)
    if not pool:
        return None
    routers = _review_routers(pool)
    if routers:
        why = f"{_REVIEW_ROUTER_WHY}; exempt from vendor-different rule (D-04)"
        return _lane_row(lane, routers[0], rigor, "router-declared", why)
    ceiling = roles.host_ceiling(pool, presets.PRICE_PERCENTILE[rigor])
    pick = roles.best_pick(
        pool,
        "review",
        REVIEW_EFFORT_TARGET,
        ceiling.value,
        keep=_vendor_keep(excluded),
    )
    if pick is None:
        return None
    cand = pick.candidate
    slug = lane["slug"]
    vendor = cand.get("vendor")
    tail = roles.pick_why(pick, "review", REVIEW_EFFORT_TARGET, ceiling)
    excl = sorted(v for v in excluded if v)
    why = (
        f"review lane {slug}: inferred vendor {vendor} differs from excluded "
        f"{excl} (SPEC R2); {tail}"
    )
    return _lane_row(lane, cand, rigor, "catalog-score", why)


def _ranked_lanes(
    eligible: list[dict], inv: dict, rigor: str, excluded: set[str | None],
) -> list[Lane]:
    picked = [_pick_lane(lane, inv, rigor, excluded) for lane in eligible]
    lanes = [lane for lane in picked if lane is not None]
    return sorted(lanes, key=_lane_rank_key)


def select_lanes(
    inv: dict, rigor: str, planner_vendor: str | None,
) -> tuple[list[Lane], list[dict]]:
    """Pick review lanes in registry order rules (D-01, SPEC R2). Routers rank first."""
    notes: list[dict] = []
    eligible = eligible_lanes(inv)
    want = REVIEW_COUNT.get(rigor, 1)
    excluded: set[str | None] = {planner_vendor} if planner_vendor else {None}
    ranked = _ranked_lanes(eligible, inv, rigor, excluded)
    if not ranked:
        return [], notes
    chosen = [ranked[0]]
    if want < 2:
        return chosen, notes
    reason = "only one eligible review lane"
    if len(eligible) > 1:
        first = chosen[0]
        excl = set(excluded)
        if first.vendor is not None:
            excl.add(first.vendor)
        rest = [lane for lane in eligible if lane["slug"] != first.slug]
        second_ranked = _ranked_lanes(rest, inv, rigor, excl)
        if second_ranked:
            chosen.append(second_ranked[0])
        reason = (
            "no other review lane has a candidate within the ceiling whose vendor differs "
            "from the planner's and the first reviewer's"
        )
    if len(chosen) < want:
        # SPEC R2: Rigorous otherwise gets 1 lane plus a note.
        notes.append({
            "kind": "review_lane",
            "key": "review.default_reviewers",
            "text": f"{reason}; {rigor} wanted {want}",
        })
    return chosen, notes


def script_artifact(targets: list[Target], timeout: int) -> dict:
    models = {t.cli: t.model for t in targets if t.model is not None}
    choices = {t.cli: {"candidates": t.candidates} for t in targets if t.model is None}
    status = "needs_choice" if choices else "ok"
    why_tail = "; ".join(f"{t.cli}: {t.why}" for t in targets)
    return {
        "kind": "cross-ai-script",
        "path": SCRIPT_PATH,
        "template": TEMPLATE_NAME,
        "version": TEMPLATE_VERSION,
        "config": {
            "prefer": [t.cli for t in targets],
            "models": models,
            "outer_timeout_s": timeout,
            "router_backed": {t.cli: t.router_backed for t in targets if t.model is not None},
        },
        "choices": choices,
        "status": status,
        "source": "preset",
        "why": f"cross-AI execution runner (18 D-09); {why_tail}",
    }
