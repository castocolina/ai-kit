"""Role selection helpers for spec §4 (D-03, D-06, D-16, D-25, D-27).

Pure functions only: no I/O, clock, or environment. `EFFORT_LADDER` mirrors the
module-internal ladder in gsd-core `model-catalog.cjs` (not exported from node).
"""
from __future__ import annotations

import math
from typing import NamedTuple

from . import presets

TIER_PURPOSE = {"opus": "planning", "sonnet": "general", "haiku": "mechanical"}
TIER_EFFORT_BAND = {"opus": "heavy", "sonnet": "standard", "haiku": "light"}
EFFORT_LADDER = ("minimal", "low", "medium", "high", "xhigh", "max", "ultra")
CLAUDE_ALIASES = ("fable", "opus", "sonnet", "haiku")


def claude_alias_for(model: str) -> str | None:
    for alias in CLAUDE_ALIASES:
        if model.startswith(f"claude-{alias}-"):
            return alias
    return None


def _version_key(model: str) -> tuple:
    return tuple(int(p) for p in model.split("-") if p.isdigit()), model


def claude_alias_rows(cands: list) -> list:
    """Claude Code lists several ids per alias but runs the alias's current model, so
    rank one row per alias: its highest-version non-fast id (inferred representative,
    not a verified alias -> id map). Ids without an alias are dropped."""
    best: dict[str, dict] = {}
    for c in cands:
        alias = claude_alias_for(c["model"])
        if alias is None or c["fast_twin_of"] is not None:
            continue
        held = best.get(alias)
        if held is None or _version_key(c["model"]) > _version_key(held["model"]):
            best[alias] = c
    return [best[alias] for alias in sorted(best)]


def _ladder_index(token: str) -> int:
    for idx, step in enumerate(EFFORT_LADDER):
        if step == token:
            return idx
    return -1


class Ceiling(NamedTuple):
    """Rigor price cap over eligible host families."""

    value: float | None
    q: float | None
    families: int


class Pick(NamedTuple):
    """One scored family variant chosen for a slot."""

    candidate: dict
    rule: str
    capped: bool


def effort_token(model: str) -> str | None:
    parts = model.split("-")
    if parts and parts[-1] == "fast":
        parts = parts[:-1]
    if parts and parts[-1] in EFFORT_LADDER:
        return parts[-1]
    return None


def clamp_effort(target: str, modes: list) -> str:
    if not modes or target in modes:
        return target
    if _ladder_index(target) < 0:
        return target
    t_idx = _ladder_index(target)
    lower = [m for m in modes if 0 <= _ladder_index(m) < t_idx]
    if lower:
        return max(lower, key=_ladder_index)
    higher = [m for m in modes if _ladder_index(m) > t_idx]
    if higher:
        return min(higher, key=_ladder_index)
    return target


def tie_key(c: dict, purpose: str) -> tuple:
    score = c["purpose_scores"][purpose]
    price = c["price"]
    price_key = math.inf if price is None else price
    return (-score, price_key, c["model"])


def price_ceiling(prices: list, q: float | None) -> float | None:
    if q is None or not prices:
        return None
    ordered = sorted(prices)
    n = len(ordered)
    return ordered[max(0, math.ceil(q * n) - 1)]


def host_ceiling(cands: list, q: float | None) -> Ceiling:
    family_prices: dict[str, float] = {}
    for c in cands:
        if c["score_axes"] <= 0 or c["fast_twin_of"] is not None or c["is_router"]:
            continue
        if c["price"] is None:
            continue
        fam = c["family"]
        price = c["price"]
        if fam not in family_prices or price < family_prices[fam]:
            family_prices[fam] = price
    val = price_ceiling(list(family_prices.values()), q)
    return Ceiling(val, q, len(family_prices))


def ceiling_text(c: Ceiling) -> str:
    if c.q is None:
        return "no ceiling"
    if c.value is None:
        return "no priced family"
    pct = int(c.q * 100)
    return f"<= {c.value:g}/1M, {pct}th pct of {c.families} families"


def _variant_groups(members: list) -> dict[str | None, list]:
    groups: dict[str | None, list] = {}
    for m in members:
        token = effort_token(m["model"])
        groups.setdefault(token, []).append(m)
    return groups


def pick_variant(members: list, purpose: str, target: str) -> tuple[dict, str]:
    # shortcut: the family grouping (vendor._MODEL_TIER_SUFFIXES) does not strip
    # minimal/ultra, so such ids form their own family; upgrade when a host lists them.
    groups = _variant_groups(members)
    if target in groups:
        chosen = min(groups[target], key=lambda c: tie_key(c, purpose))
        return chosen, "exact"
    t_idx = _ladder_index(target)
    if t_idx >= 0:
        lower_tokens = [
            t for t in groups if t is not None and 0 <= _ladder_index(t) < t_idx
        ]
        if lower_tokens:
            best_t = max(lower_tokens, key=_ladder_index)
            chosen = min(groups[best_t], key=lambda c: tie_key(c, purpose))
            return chosen, "nearest lower"
        higher_tokens = [t for t in groups if t is not None and _ladder_index(t) > t_idx]
        if higher_tokens:
            best_t = min(higher_tokens, key=_ladder_index)
            chosen = min(groups[best_t], key=lambda c: tie_key(c, purpose))
            return chosen, "nearest higher"
    if None in groups:
        chosen = min(groups[None], key=lambda c: tie_key(c, purpose))
        return chosen, "bare"
    token = next(iter(groups))
    chosen = min(groups[token], key=lambda c: tie_key(c, purpose))
    return chosen, "bare"


def _eligible_pool(cands: list, purpose: str, keep) -> list:
    pool = [
        c
        for c in cands
        if purpose in c["purpose_scores"]
        and c["fast_twin_of"] is None
        and not c["is_router"]
    ]
    if keep is not None:
        pool = [c for c in pool if keep(c)]
    return pool


def _family_variants(pool: list, purpose: str, target: str) -> list[tuple[dict, str]]:
    by_family: dict[str, list] = {}
    for c in pool:
        by_family.setdefault(c["family"], []).append(c)
    return [pick_variant(members, purpose, target) for members in by_family.values()]


def within_ceiling(c: dict, ceiling_value: float | None) -> bool:
    if ceiling_value is None:
        return True
    if c["price"] is None:
        return True
    return c["price"] <= ceiling_value


def best_pick(
    cands: list,
    purpose: str,
    target: str,
    ceiling_value: float | None,
    keep=None,
) -> Pick | None:
    pool = _eligible_pool(cands, purpose, keep)
    if not pool:
        return None
    chosen = _family_variants(pool, purpose, target)
    variants = [c for c, _rule in chosen]
    in_cap = [c for c in variants if within_ceiling(c, ceiling_value)]
    if in_cap:
        best = min(in_cap, key=lambda c: tie_key(c, purpose))
        rule = next(r for c, r in chosen if c is best)
        return Pick(best, rule, False)
    def _cap_key(item: tuple[dict, str]) -> tuple:
        c, _rule = item
        price = c["price"]
        assert price is not None
        return (price, tie_key(c, purpose))

    best_c, best_rule = min(chosen, key=_cap_key)
    return Pick(best_c, best_rule, True)


def pick_why(pick: Pick, purpose: str, target: str, ceiling: Ceiling) -> str:
    c = pick.candidate
    ct = ceiling_text(ceiling)
    if pick.capped:
        head = f"no family within ceiling ({ct}); cheapest eligible used"
    else:
        head = f"best {purpose} score within ceiling ({ct})"
    token = effort_token(c["model"])
    token_label = token if token is not None else "bare"
    tail = (
        f"; effort variant {token_label} of inferred family {c['family']} "
        f"for target {target} ({pick.rule})"
    )
    if c["price"] is None:
        tail += "; price unknown"
    return head + tail


def choice_candidates(
    cands: list, purpose: str, ceiling_value: float | None, limit: int = 3
) -> list[dict]:
    pool = [c for c in cands if c["fast_twin_of"] is None and not c["is_router"]]
    scored = [c for c in pool if purpose in c["purpose_scores"]]
    if scored:
        ordered = sorted(scored, key=lambda c: tie_key(c, purpose))
        out = []
        for c in ordered[:limit]:
            out.append({
                "model": c["model"],
                "runtime": c["runtime"],
                "score": round(c["purpose_scores"][purpose], 1),
                "price": c["price"],
                "why": f"{purpose} score",
            })
        return out
    def _price_order(c: dict) -> tuple:
        p = c["price"]
        return (p is None, p if p is not None else 0, c["model"])

    within = [c for c in pool if within_ceiling(c, ceiling_value)]
    rest = [c for c in pool if c not in within]
    ordered = sorted(within, key=_price_order) + sorted(rest, key=_price_order)
    out = []
    for c in ordered[:limit]:
        if c["score_axes"] <= 0:
            why = "no scores; ordered by price, not quality"
        else:
            why = f"no {purpose} score; ordered by price, not quality"
        out.append({
            "model": c["model"],
            "runtime": c["runtime"],
            "score": None,
            "price": c["price"],
            "why": why,
        })
    return out


def agent_tier(agent: str, gsd_core: dict, profile: str, shifts: dict) -> str | None:
    """`model_profiles` is profile -> {agent: tier} (normalized by the inventory). A
    missing profile cell reads the balanced one, like gsd-core's computeProfileTier."""
    phase = gsd_core["agent_to_phase_type"].get(agent)
    if phase is not None and phase in shifts:
        tier = shifts[phase]
    else:
        profiles = gsd_core["model_profiles"]
        tier = profiles.get(profile, {}).get(agent) or profiles.get("balanced", {}).get(agent)
    if tier not in presets.TIERS:
        return None
    return tier


def used_tiers(gsd_core: dict, profile: str, shifts: dict) -> tuple[str, ...]:
    agents = {a for column in gsd_core["model_profiles"].values() for a in column}
    seen = {agent_tier(a, gsd_core, profile, shifts) for a in agents}
    return tuple(t for t in presets.TIERS if t in seen)


def cheap_other_cli(cands: list, q: float | None) -> dict | None:
    host = [c for c in cands if c["is_host"]]
    ceiling = host_ceiling(host, q).value
    if ceiling is None:
        return None
    pool = [
        c
        for c in cands
        if not c["is_host"]
        and c["score_axes"] > 0
        and c["fast_twin_of"] is None
        and not c["is_router"]
        and c["price"] is not None
        and c["price"] <= ceiling
    ]
    if not pool:
        return None
    return min(pool, key=lambda c: (c["price"], c["model"], c["runtime"]))
