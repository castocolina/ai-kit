"""The pure recommendation engine (REC-01): inventory + profile + rigor + the two
cross-AI answers -> one canonical, sorted, explainable plan dict. No subprocess, no
network, no clock, no environment, no filesystem: everything arrives through the
inventory. Imports only `typing` names, `.cross_ai`, `.presets`, `.roles` and
`.plan_schema` (guarded by the tests' AST import check).
"""
from typing import Any, NamedTuple

from . import cross_ai, plan_schema, presets, roles, skills


class RecommendOpts(NamedTuple):
    profile: str
    rigor: str
    cross_ai_review: str | None = None
    cross_ai_exec: str | None = None
    affinity: dict | None = None


class PlanCtx(NamedTuple):
    inv: dict
    opts: RecommendOpts
    host: str
    existing: dict
    preset: dict
    # Computed once in build_plan so every layer reads the same answer (PT-14).
    targets: tuple = ()
    answers: Any = None


class _SlotMeta(NamedTuple):
    key: str
    purpose: str
    target: str
    extra: dict


class _PickRequest(NamedTuple):
    ctx: PlanCtx
    key: str
    reason: str
    purpose: str
    target: str
    ceiling: roles.Ceiling
    extra: dict


class _SpecialistRun(NamedTuple):
    ctx: PlanCtx
    prior: list
    cands: list
    ceiling: roles.Ceiling


class _SpecialistOut(NamedTuple):
    entries: list
    notes: list


class _CounterpartReq(NamedTuple):
    run: _SpecialistRun
    agent: str
    ref_model: str | None
    ref_label: str


class _CounterpartPick(NamedTuple):
    req: _CounterpartReq
    pick: roles.Pick
    ref_vendor: str
    target: str
    slot_model: str | None


class _VisionPick(NamedTuple):
    run: _SpecialistRun
    agent: str
    pick: roles.Pick
    target: str
    slot_model: str | None


def make_entry(ctx: PlanCtx, key: str, value: Any, source: str, why: str, **extra) -> dict:
    """One plan entry with the mandatory base fields (REC-01, D-08); `op` defaults
    to `set` and further fields (`status`, `candidates`, `effect`) ride in via
    `extra`. (Bundled into `**extra` rather than named parameters to honor the
    repo-wide pylint max-args=5.)"""
    entry = {
        "key": key,
        "op": extra.pop("op", "set"),
        "value": value,
        "source": source,
        "why": why,
        "existing": presets.get_dotted(ctx.existing, key),
    }
    entry.update(extra)
    return entry


def cross_ai_answers(ctx: PlanCtx) -> dict:
    """Resolves the two cross-AI answers (17 D-19, 18 D-39). An explicit flag wins with
    `defaulted: False`; an omitted flag defaults from rigor and host and is recorded
    as `defaulted: True`."""
    other_cli = any(not c.get("is_host", False) for c in ctx.inv["candidates"])
    claude_or_codex = ctx.host in ("claude", "codex")

    def _resolve(flag: str | None, default: str) -> dict:
        return {"answer": flag if flag is not None else default, "defaulted": flag is None}

    review_default = "n"
    standard_qualified = ctx.opts.rigor == "standard" and claude_or_codex and other_cli
    if ctx.opts.rigor == "rigorous" or standard_qualified:
        review_default = "y"
    exec_default, _ = cross_ai.exec_default(ctx.host, list(ctx.targets))
    return {
        "review": _resolve(ctx.opts.cross_ai_review, review_default),
        "exec": _resolve(ctx.opts.cross_ai_exec, exec_default),
    }


_ENUMERATION_TAIL = {"failed": " (listing failed)", "empty": " (listing empty)"}


def _exec_targets(inv: dict, rigor: str) -> list[cross_ai.Target]:
    """cross_ai's targets; an empty runtime pool states its enumeration cause, never a
    ceiling outcome (C-W12)."""
    status = inv.get("runtime_enumeration") or {}
    out = []
    for target in cross_ai.exec_targets(inv, rigor):
        runtime = cross_ai.RUNNER_CLI[target.cli]
        pool = [c for c in inv["candidates"] if c.get("runtime") == runtime]
        if target.model is None and not pool:
            tail = _ENUMERATION_TAIL.get(status.get(runtime), "")
            target = target._replace(why=f"no {runtime} models enumerated{tail}")
        out.append(target)
    return out


def _preset_layer(ctx: PlanCtx, _prior_entries: list) -> tuple[list, list]:
    """Layer 1: every §5 preset key for the chosen rigor plus its conditional keys."""
    entries = []
    notes = []
    for key in sorted(ctx.preset):
        why = f"rigor {ctx.opts.rigor} preset (spec §5)"
        extra: dict = {}
        if key.startswith("dynamic_routing."):
            extra["effect"] = presets.DYNAMIC_ROUTING_EFFECT
        entries.append(make_entry(ctx, key, ctx.preset[key], "preset", why, **extra))
    if ctx.opts.rigor == "rigorous" and ctx.inv["project"].get("frontend", False):
        notes.append({
            "kind": "live_dom_uat",
            "key": "workflow.live_dom_uat",
            "text": "enable workflow.live_dom_uat via plan-set if a browser MCP is available",
        })
    return entries, notes


def _tier_layer(ctx: PlanCtx, _prior_entries: list) -> tuple[list, list]:
    """Layer 2 (tier level): `model_profile` plus one `models.<phase>` entry per
    rigor phase shift. Later plans append the slot layer after this one."""
    entries = [
        make_entry(
            ctx,
            "model_profile",
            ctx.opts.profile,
            "preset",
            f"profile {ctx.opts.profile}"
            + (" (adaptive recommended)" if ctx.opts.profile == "adaptive" else ""),
            **({"effect": presets.PI_EFFECT} if ctx.host == "pi" else {}),
        )
    ]
    for phase in sorted(presets.PHASE_SHIFTS[ctx.opts.rigor]):
        tier = presets.PHASE_SHIFTS[ctx.opts.rigor][phase]
        extra = {"effect": presets.PI_EFFECT} if ctx.host == "pi" else {}
        entries.append(
            make_entry(
                ctx,
                f"models.{phase}",
                tier,
                "preset",
                f"rigor {ctx.opts.rigor} shifts the whole {phase} phase to {tier}",
                **extra,
            )
        )
    return entries, []


def _native_model(ctx: PlanCtx, tier: str) -> str | None:
    host_map = ctx.inv["gsd_core"]["runtime_profile_map"].get(ctx.host)
    if not isinstance(host_map, dict):
        return None
    slot = host_map.get(tier)
    if not isinstance(slot, dict):
        return None
    model = slot.get("model")
    return model if isinstance(model, str) else None


def _native_value(ctx: PlanCtx, tier: str) -> Any:
    """The gsd default slot verbatim (codex keeps its own reasoning_effort): a `keep`
    writes nothing, so the displayed value must be the one that takes effect."""
    slot = ctx.inv["gsd_core"]["runtime_profile_map"][ctx.host][tier]
    return dict(slot) if ctx.host == "codex" else slot["model"]


def _slot_value(host: str, candidate: dict, target: str) -> Any:
    if host == "codex":
        modes = candidate.get("reasoning_modes") or []
        return {
            "model": candidate["model"],
            "reasoning_effort": roles.clamp_effort(target, modes),
        }
    return candidate["model"]


_KEEP_WHY = "kept gsd default: present on host, within ceiling"
_CODEX_EMPTY_WHY = "kept gsd default: codex enumerated no models; presence and ceiling unchecked"


def _keep_why(existing: Any, why: str = _KEEP_WHY) -> tuple[str, str]:
    """`keep` shows the gsd default as `value`; an `unset` (existing override removed so
    the default applies) carries `value: None` like every other unset."""
    if existing is None:
        return "keep", why
    return "unset", why + "; removes the existing override"


def _slot_meta(ctx: PlanCtx, tier: str) -> _SlotMeta:
    band = roles.TIER_EFFORT_BAND[tier]
    extra: dict = {}
    if ctx.host == "codex":
        extra["effect"] = presets.CODEX_EFFECT
    key = f"model_profile_overrides.{ctx.host}.{tier}"
    target = ctx.preset[f"effort.routing_tier_defaults.{band}"]
    return _SlotMeta(key, roles.TIER_PURPOSE[tier], target, extra)


def _catalog_pick_entry(req: _PickRequest, cands: list):
    pick = roles.best_pick(cands, req.purpose, req.target, req.ceiling.value)
    if pick is None:
        return None
    why = f"{req.reason}; {roles.pick_why(pick, req.purpose, req.target, req.ceiling)}"
    value = _slot_value(req.ctx.host, pick.candidate, req.target)
    if isinstance(value, dict) and value["reasoning_effort"] not in pick.candidate.get(
        "reasoning_modes", []
    ):
        # clamp_effort keeps the raw target when the model lists no usable level.
        why += (
            f"; effort {value['reasoning_effort']} unverified "
            "(not among the model's reasoning modes)"
        )
    return make_entry(req.ctx, req.key, value, "catalog-score", why, **req.extra)


def _override_reason(ctx: PlanCtx, native_id: str | None, native_c: dict | None, ceiling) -> str:
    if native_id is None:
        return f"no gsd default for {ctx.host}"
    if native_c is None:
        return f"gsd default {native_id} not on host"
    return f"gsd default {native_id} above ceiling ({roles.ceiling_text(ceiling)})"


def _tier_slot(ctx: PlanCtx, tier: str, cands: list, ceiling: roles.Ceiling) -> dict:
    meta = _slot_meta(ctx, tier)
    native_id = _native_model(ctx, tier)
    native_c = next((c for c in cands if c["model"] == native_id), None) if native_id else None
    if native_c is not None and roles.within_ceiling(native_c, ceiling.value):
        op, why = _keep_why(presets.get_dotted(ctx.existing, meta.key))
        return make_entry(
            ctx,
            meta.key,
            _native_value(ctx, tier) if op == "keep" else None,
            "native",
            why,
            op=op,
            **meta.extra,
        )
    reason = _override_reason(ctx, native_id, native_c, ceiling)
    req = _PickRequest(ctx, meta.key, reason, meta.purpose, meta.target, ceiling, meta.extra)
    if (picked := _catalog_pick_entry(req, cands)) is not None:
        return picked
    if not cands:
        tail = f"no {ctx.host} models enumerated; choose with plan-set"
    elif not any(c["score_axes"] > 0 for c in cands):
        tail = f"no scores: no {ctx.host} candidate has a catalog score; choose with plan-set"
    else:
        tail = f"no eligible {meta.purpose} candidate on {ctx.host}; choose with plan-set"
    return make_entry(
        ctx,
        meta.key,
        None,
        "preset",
        f"{reason}; {tail}",
        status="needs_choice",
        candidates=roles.choice_candidates(cands, meta.purpose, ceiling.value),
        **meta.extra,
    )


def _codex_empty_slots(ctx: PlanCtx, tiers: tuple[str, ...]) -> tuple[list, list]:
    entries = []
    effect = presets.CODEX_EFFECT + "; effect unverified: enumeration failed"
    for tier in tiers:
        key = _slot_meta(ctx, tier).key
        op, why = _keep_why(presets.get_dotted(ctx.existing, key), _CODEX_EMPTY_WHY)
        known = op == "keep" and _native_model(ctx, tier) is not None
        value = _native_value(ctx, tier) if known else None
        entries.append(make_entry(ctx, key, value, "native", why, op=op, effect=effect))
    return entries, []


_PI_NOTE = {
    "kind": "pi",
    "key": None,
    "text": (
        "pi: only an opt-in model_profile_overrides.pi.sonnet is offered; "
        "no per-agent model_overrides (effect unverified on pi, gsd-core registry: "
        "namedDispatch false)"
    ),
}


def _pi_slot(ctx: PlanCtx, tiers: tuple[str, ...]) -> tuple[list, list]:
    if "sonnet" not in tiers:
        return [], [dict(_PI_NOTE)]
    key = "model_profile_overrides.pi.sonnet"
    why = (
        "opt-in session steer (D-22): choose a bare model id of the session provider "
        "with plan-set (the session provider is unknown before Phase 22), or drop this "
        "entry with plan-unset"
    )
    entry = make_entry(
        ctx,
        key,
        None,
        "preset",
        why,
        status="needs_choice",
        candidates=[],
        effect=presets.PI_EFFECT,
    )
    return [entry], [dict(_PI_NOTE)]


def _slot_layer(ctx: PlanCtx, _prior_entries: list) -> tuple[list, list]:
    """Layer 2b: per-tier model_profile_overrides for the host (D-01..D-06)."""
    if ctx.host == "claude":
        return [], []
    shifts = presets.PHASE_SHIFTS[ctx.opts.rigor]
    tiers = roles.used_tiers(ctx.inv["gsd_core"], ctx.opts.profile, shifts)
    if ctx.host == "pi":
        return _pi_slot(ctx, tiers)
    cands = _host_cands(ctx)
    if ctx.host == "codex" and not cands:
        return _codex_empty_slots(ctx, tiers)
    ceiling = roles.host_ceiling(cands, presets.PRICE_PERCENTILE[ctx.opts.rigor])
    entries = [_tier_slot(ctx, tier, cands, ceiling) for tier in tiers]
    return entries, []


def _slot_models(ctx: PlanCtx, prior: list) -> dict[str, str | None]:
    shifts = presets.PHASE_SHIFTS[ctx.opts.rigor]
    tiers = roles.used_tiers(ctx.inv["gsd_core"], ctx.opts.profile, shifts)
    prefix = f"model_profile_overrides.{ctx.host}."
    by_key = {e["key"]: e for e in prior if e["key"].startswith(prefix)}
    out: dict[str, str | None] = {}
    for tier in tiers:
        if ctx.host == "claude":
            out[tier] = tier
            continue
        entry = by_key.get(prefix + tier)
        if entry is None or entry["op"] in ("keep", "unset"):
            out[tier] = _native_model(ctx, tier)
        elif entry.get("status") == "needs_choice":
            out[tier] = None
        else:
            val = entry["value"]
            out[tier] = val["model"] if isinstance(val, dict) else val
    return out


def _facts(ctx: PlanCtx, cands: list, model: str | None) -> tuple[str | None, bool | None]:
    if model is None:
        return None, None
    if ctx.host == "claude" and model in presets.TIERS:
        matched = [c for c in cands if roles.claude_alias_for(c["model"]) == model]
        if not matched:
            return None, None
        vendors = {c["vendor"] for c in matched if c.get("vendor")}
        vendor = next(iter(vendors)) if len(vendors) == 1 else None
        flags = [c.get("image_input") for c in matched]
        if all(f is True for f in flags):
            image = True
        elif all(f is False for f in flags):
            image = False
        else:
            image = None
        return vendor, image
    for cand in cands:
        if cand["model"] == model:
            return cand.get("vendor"), cand.get("image_input")
    return None, None


def _agent_target(ctx: PlanCtx, agent: str, tier: str) -> str:
    key = f"effort.agent_overrides.{agent}"
    if key in ctx.preset:
        return ctx.preset[key]
    band = roles.TIER_EFFORT_BAND[tier]
    return ctx.preset[f"effort.routing_tier_defaults.{band}"]


def _value_for(ctx: PlanCtx, candidate: dict) -> str:
    if ctx.host == "claude":
        alias = roles.claude_alias_for(candidate["model"])
        if alias is not None:
            return alias
    return candidate["model"]


def _agent_slot_model(ctx: PlanCtx, prior: list, agent: str) -> str | None:
    shifts = presets.PHASE_SHIFTS[ctx.opts.rigor]
    tier = roles.agent_tier(agent, ctx.inv["gsd_core"], ctx.opts.profile, shifts)
    if tier is None:
        return None
    return _slot_models(ctx, prior).get(tier)


def _host_cands(ctx: PlanCtx) -> list:
    return [c for c in ctx.inv["candidates"] if c.get("is_host", False)]


_ALIAS_EFFECT = "alias mapping inferred: Claude Code runs the alias's current model"


def _alias_why(ctx: PlanCtx, candidate: dict) -> str:
    alias = roles.claude_alias_for(candidate["model"]) if ctx.host == "claude" else None
    if alias is None:
        return ""
    return f"; alias {alias} scored as {candidate['model']} (highest-version id for the alias)"


def _alias_extra(ctx: PlanCtx, value: str) -> dict:
    alias = ctx.host == "claude" and value in roles.CLAUDE_ALIASES
    return {"effect": _ALIAS_EFFECT} if alias else {}


def _claude_keep(c: dict) -> bool:
    return roles.claude_alias_for(c["model"]) is not None


def _router_unconfirmed_notes(ctx: PlanCtx, cands: list) -> list:
    notes = []
    for cand in sorted(cands, key=lambda c: c["model"]):
        if not cand.get("is_router"):
            continue
        purpose = cand.get("name_declared_purpose")
        if purpose and not cand.get("router_confirmed"):
            # Only execute routers can win a Phase 17 slot; review routers wait for Phase 18.
            effect = (
                "to let it win its slot"
                if purpose == "execute"
                else "for Phase 18 cross-AI review selection"
            )
            notes.append({
                "kind": "router_unconfirmed",
                "key": cand["model"],
                "text": (
                    f"router {cand['model']} declares purpose {purpose} but is not "
                    f"user-confirmed; confirm it via ai-kit-spec-config {effect}"
                ),
            })
    return notes


def _single_provider(ctx: PlanCtx, cands: list) -> bool:
    if ctx.host in ("claude", "codex"):
        return True
    vendors = {c["vendor"] for c in cands if c.get("vendor")}
    return len(vendors) == 1


def _counterpart_note(ctx: PlanCtx) -> dict:
    return {
        "kind": "counterpart",
        "key": None,
        "text": (
            f"no in-runtime counterpart for gsd-plan-checker and gsd-code-reviewer on "
            f"{ctx.host} (single provider): use cross-AI review"
        ),
    }


def _write_exec_overrides(
    run: _SpecialistRun, out: _SpecialistOut, pick_val: str, source: str, why: str,
) -> None:
    ctx, prior = run.ctx, run.prior
    for agent in ("gsd-executor", "gsd-code-fixer"):
        slot = _agent_slot_model(ctx, prior, agent)
        key = f"model_overrides.{agent}"
        if pick_val != slot:
            extra = _alias_extra(ctx, pick_val)
            out.entries.append(make_entry(ctx, key, pick_val, source, why, **extra))


def _exec_no_model_note(ctx: PlanCtx, out: _SpecialistOut) -> None:
    out.notes.append({
        "kind": "specialist",
        "key": "model_overrides.gsd-executor",
        "text": (
            f"no eligible execution model on {ctx.host}; gsd-executor and "
            "gsd-code-fixer keep their tier"
        ),
    })


def _exec_from_router(run: _SpecialistRun, out: _SpecialistOut, router: dict) -> str:
    pick_val = _value_for(run.ctx, router)
    router_why = "user-curated router (declared purpose: execute)"
    _write_exec_overrides(run, out, pick_val, "router-declared", router_why)
    return pick_val


def _exec_from_catalog(
    run: _SpecialistRun, out: _SpecialistOut, exec_slot: str | None,
) -> str | None:
    ctx, cands, ceiling = run.ctx, run.cands, run.ceiling
    shifts = presets.PHASE_SHIFTS[ctx.opts.rigor]
    tier = roles.agent_tier("gsd-executor", ctx.inv["gsd_core"], ctx.opts.profile, shifts)
    if tier is None:
        _unknown_agent_note(ctx, out, "gsd-executor")
        return exec_slot
    target = _agent_target(ctx, "gsd-executor", tier)
    keep = _claude_keep if ctx.host == "claude" else None
    pick = roles.best_pick(cands, "execution", target, ceiling.value, keep=keep)
    if pick is None:
        _exec_no_model_note(ctx, out)
        return exec_slot
    pick_val = _value_for(ctx, pick.candidate)
    exec_why = roles.pick_why(pick, "execution", target, ceiling) + _alias_why(ctx, pick.candidate)
    _write_exec_overrides(run, out, pick_val, "catalog-score", exec_why)
    return pick_val


def _execution_specialists(run: _SpecialistRun, out: _SpecialistOut) -> str | None:
    ctx, cands = run.ctx, run.cands
    out.notes.extend(_router_unconfirmed_notes(ctx, cands))
    exec_slot = _agent_slot_model(run.ctx, run.prior, "gsd-executor")
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
        return _exec_from_router(run, out, routers[0])
    return _exec_from_catalog(run, out, exec_slot)


def _counterpart_keep(ctx: PlanCtx, ref_vendor: str):
    def keep(c: dict) -> bool:
        vendor = c.get("vendor")
        if vendor is None or vendor == ref_vendor:
            return False
        return _claude_keep(c) if ctx.host == "claude" else True

    return keep


def _specialist_note(out: _SpecialistOut, key: str, text: str) -> None:
    out.notes.append({"kind": "specialist", "key": key, "text": text})


def _unknown_agent_note(ctx: PlanCtx, out: _SpecialistOut, agent: str) -> None:
    version = ctx.inv["gsd_core"].get("version") or "unknown"
    _specialist_note(
        out,
        f"model_overrides.{agent}",
        f"{agent} unknown to gsd-core {version} (no tier); no override proposed",
    )


def _append_counterpart_override(bundle: _CounterpartPick, out: _SpecialistOut) -> None:
    req, pick, ref_vendor, target, slot_model = bundle
    ctx = req.run.ctx
    pick_val = _value_for(ctx, pick.candidate)
    slot_vendor, _ = _facts(ctx, req.run.cands, slot_model)
    if slot_vendor is not None and slot_vendor != ref_vendor:
        return
    if pick_val == slot_model:
        return
    key = f"model_overrides.{req.agent}"
    tail = roles.pick_why(pick, "review", target, req.run.ceiling)
    why = (
        f"counterpart: inferred vendor {pick.candidate.get('vendor')} differs from the inferred "
        f"{req.ref_label} vendor {ref_vendor} (D-14); {tail}{_alias_why(ctx, pick.candidate)}"
    )
    extra = _alias_extra(ctx, pick_val)
    out.entries.append(make_entry(ctx, key, pick_val, "catalog-score", why, **extra))


def _counterpart_one(req: _CounterpartReq, out: _SpecialistOut) -> None:
    ctx, prior, cands, ceiling = req.run
    key = f"model_overrides.{req.agent}"
    shifts = presets.PHASE_SHIFTS[ctx.opts.rigor]
    tier = roles.agent_tier(req.agent, ctx.inv["gsd_core"], ctx.opts.profile, shifts)
    if tier is None:
        _unknown_agent_note(ctx, out, req.agent)
        return
    slot_model = _agent_slot_model(ctx, prior, req.agent)
    ref_vendor, _ = _facts(ctx, cands, req.ref_model)
    if req.ref_model is None or ref_vendor is None:
        _specialist_note(
            out,
            key,
            f"no inferred vendor for {req.ref_label} reference model; {req.agent} keeps its tier",
        )
        return
    target = _agent_target(ctx, req.agent, tier)
    pick = roles.best_pick(
        cands, "review", target, ceiling.value, keep=_counterpart_keep(ctx, ref_vendor)
    )
    if pick is None:
        _specialist_note(
            out,
            key,
            f"no eligible review model with vendor other than {ref_vendor} on "
            f"{ctx.host}; {req.agent} keeps its tier",
        )
        return
    bundle = _CounterpartPick(req, pick, ref_vendor, target, slot_model)
    _append_counterpart_override(bundle, out)


def _counterpart_specialists(
    run: _SpecialistRun, exec_model: str | None, out: _SpecialistOut,
) -> None:
    ctx, prior, cands, _ = run
    if _single_provider(ctx, cands):
        out.notes.append(_counterpart_note(ctx))
        return
    shifts = presets.PHASE_SHIFTS[ctx.opts.rigor]
    planner_tier = roles.agent_tier("gsd-planner", ctx.inv["gsd_core"], ctx.opts.profile, shifts)
    slots = _slot_models(ctx, prior)
    planner_model = slots.get(planner_tier) if planner_tier else None
    _counterpart_one(
        _CounterpartReq(run, "gsd-plan-checker", planner_model, "gsd-planner"), out
    )
    _counterpart_one(
        _CounterpartReq(run, "gsd-code-reviewer", exec_model, "execution"), out
    )


def _vision_fallback_note(run: _SpecialistRun, out: _SpecialistOut, key: str, agent: str) -> None:
    host = run.ctx.host
    if any(c.get("image_input") is True for c in run.cands):
        text = (
            f"image_input models on {host} have no general score (unscored, router or -fast "
            f"twin); {agent} falls back to its tier; choose with plan-set"
        )
    else:
        text = f"no image_input model on {host}; {agent} falls back to its tier"
    out.notes.append({"kind": "vision", "key": key, "text": text})


def _vision_keep(ctx: PlanCtx):
    def keep(c: dict) -> bool:
        if c.get("image_input") is not True:
            return False
        return _claude_keep(c) if ctx.host == "claude" else True

    return keep


def _append_vision_override(bundle: _VisionPick, out: _SpecialistOut) -> None:
    run, agent, pick, target, slot_model = bundle
    ctx, ceiling = run.ctx, run.ceiling
    pick_val = _value_for(ctx, pick.candidate)
    if pick_val == slot_model:
        return
    head = (
        "frontend-capable = image_input (D-28)"
        if agent == "gsd-ui-researcher"
        else "needs image_input"
    )
    key = f"model_overrides.{agent}"
    tail = roles.pick_why(pick, "general", target, ceiling) + _alias_why(ctx, pick.candidate)
    extra = _alias_extra(ctx, pick_val)
    out.entries.append(make_entry(ctx, key, pick_val, "catalog-score", f"{head}; {tail}", **extra))


def _vision_one(run: _SpecialistRun, agent: str, out: _SpecialistOut) -> None:
    ctx, prior, cands, ceiling = run
    key = f"model_overrides.{agent}"
    tier = roles.agent_tier(
        agent, ctx.inv["gsd_core"], ctx.opts.profile, presets.PHASE_SHIFTS[ctx.opts.rigor]
    )
    if tier is None:
        _unknown_agent_note(ctx, out, agent)
        return
    slot_model = _agent_slot_model(ctx, prior, agent)
    _, slot_image = _facts(ctx, cands, slot_model)
    if slot_image is True:
        return
    if not any(c.get("image_input") is True for c in cands):
        _vision_fallback_note(run, out, key, agent)
        return
    target = _agent_target(ctx, agent, tier)
    pick = roles.best_pick(cands, "general", target, ceiling.value, keep=_vision_keep(ctx))
    if pick is None:
        _vision_fallback_note(run, out, key, agent)
        return
    _append_vision_override(_VisionPick(run, agent, pick, target, slot_model), out)


def _vision_specialists(run: _SpecialistRun, out: _SpecialistOut) -> None:
    for agent in ("gsd-ui-auditor", "gsd-dom-verifier"):
        _vision_one(run, agent, out)
    if run.ctx.inv["project"].get("frontend", False):
        _vision_one(run, "gsd-ui-researcher", out)


def _specialist_layer(ctx: PlanCtx, prior_entries: list) -> tuple[list, list]:
    """Layer 2c: at most seven `model_overrides.*` entries when slots fail specialist rules."""
    if ctx.host == "pi":
        return [], []
    cands = _host_cands(ctx)
    if ctx.host == "claude":
        cands = roles.claude_alias_rows(cands)
    ceiling = roles.host_ceiling(cands, presets.PRICE_PERCENTILE[ctx.opts.rigor])
    run = _SpecialistRun(ctx, prior_entries, cands, ceiling)
    out = _SpecialistOut([], [])
    exec_model = _execution_specialists(run, out)
    _counterpart_specialists(run, exec_model, out)
    _vision_specialists(run, out)
    return out.entries, out.notes


def _cross_ai_why(ctx: PlanCtx, answers_key: str, answer: dict) -> str:
    defaulted = " (defaulted)" if answer["defaulted"] else ""
    base = f"cross-AI {answers_key} answer: {answer['answer']}{defaulted}"
    if answers_key != "exec" or not answer["defaulted"]:
        return base
    _, def_why = cross_ai.exec_default(ctx.host, list(ctx.targets))
    return f"{base}; {def_why}"


def _exec_command_why(targets: list[cross_ai.Target]) -> str:
    missing = [t for t in targets if t.model is None]
    if missing:
        return (
            "set each missing target model with plan-set script:cross-ai.model.<cli> <model>"
        )
    names = ", ".join(t.cli for t in targets)
    return f"cross-AI execution runner (18 D-09); targets: {names}"


def _review_lane_note(key: str, text: str) -> dict:
    return {"kind": "review_lane", "key": key, "text": text}


def _review_off_entry(ctx: PlanCtx, why: str) -> dict:
    return make_entry(ctx, "workflow.plan_review_convergence", False, "preset", why)


def _no_lane_reason(inv: dict, planner_vendor: str | None) -> str:
    eligible = cross_ai.eligible_lanes(inv)
    installed = set(inv.get("installed_runtimes") or [])
    lane_bins = {
        lane.get("binary")
        for lane in inv["gsd_core"].get("review_lanes") or []
        if isinstance(lane, dict) and lane.get("slug") not in (inv["host"], "pi")
    }
    if not lane_bins & installed:
        missing = "no installed non-host lane CLI"
    elif not eligible:
        missing = "no enumerated models on an installed non-host lane"
    elif planner_vendor is None:
        missing = "planner vendor is unknown"
    else:
        missing = f"no lane whose vendor differs from {planner_vendor}"
    return f"no eligible review lane: {missing}; re-enable with plan-set"


def _append_lane_entries(ctx: PlanCtx, entries: list, lane: cross_ai.Lane) -> None:
    accepted = set(ctx.inv["gsd_core"]["valid_keys"]["accepted"])
    extra: dict = {}
    if lane.slug == "claude":
        extra["effect"] = cross_ai.CLAUDE_ALIAS_EFFECT
    entries.append(
        make_entry(
            ctx,
            lane.model_key,
            lane.model,
            lane.source,
            lane.why,
            **extra,
        )
    )
    effort = lane.effort
    effort_key = lane.effort_key
    if effort is None or effort_key is None or effort_key not in accepted:
        return
    eff_extra: dict = {}
    if lane.slug == "opencode":
        eff_extra["effect"] = cross_ai.OPENCODE_EFFORT_EFFECT
    entries.append(
        make_entry(ctx, effort_key, effort, lane.source, lane.why, **eff_extra)
    )


def _cross_ai_review_entries(
    ctx: PlanCtx, prior_entries: list, answer: dict,
) -> tuple[list, list]:
    entries: list = []
    notes: list = []
    if answer["answer"] != "y":
        return entries, notes
    planner_model = _agent_slot_model(ctx, prior_entries, "gsd-planner")
    planner_vendor, _ = _facts(ctx, _host_cands(ctx), planner_model)
    lanes, lane_notes = (
        cross_ai.select_lanes(ctx.inv, ctx.opts.rigor, planner_vendor)
        if planner_vendor is not None
        else ([], [])
    )
    notes.extend(lane_notes)
    if not lanes:
        why = _no_lane_reason(ctx.inv, planner_vendor)
        entries.append(_review_off_entry(ctx, why))
        notes.append(_review_lane_note("workflow.plan_review_convergence", why))
        return entries, notes
    entries.append(
        make_entry(
            ctx,
            "workflow.plan_review_convergence",
            True,
            "preset" if answer["defaulted"] else "user",
            _cross_ai_why(ctx, "review", answer),
        )
    )
    slugs = [lane.slug for lane in lanes]
    entries.append(
        make_entry(
            ctx,
            "review.default_reviewers",
            slugs,
            "preset",
            f"cross-AI review lanes ({', '.join(slugs)}) from gsd-core registry (D-24)",
        )
    )
    for lane in lanes:
        _append_lane_entries(ctx, entries, lane)
    return entries, notes


def _cross_ai_exec_entries(ctx: PlanCtx, answer: dict, targets: list) -> tuple[list, list]:
    entries: list = []
    notes: list = []
    flag_key = "workflow.cross_ai_execution"
    command_key = "workflow.cross_ai_command"
    yes = answer["answer"] == "y"
    entries.append(
        make_entry(
            ctx,
            flag_key,
            yes,
            "preset" if answer["defaulted"] else "user",
            _cross_ai_why(ctx, "exec", answer),
        )
    )
    if not yes:
        return entries, notes
    if not targets:
        entries.append(
            make_entry(
                ctx,
                command_key,
                None,
                "preset",
                cross_ai.NO_TARGET_TEXT,
                status="needs_choice",
                candidates=[],
            )
        )
        return entries, notes
    cmd_extra: dict = {}
    if any(t.model is None for t in targets):
        cmd_extra = {"status": "needs_choice", "candidates": []}
    entries.append(
        make_entry(
            ctx,
            command_key,
            cross_ai.CROSS_AI_COMMAND,
            "preset",
            _exec_command_why(targets),
            **cmd_extra,
        )
    )
    timeout_key = "workflow.cross_ai_timeout"
    entries.append(
        make_entry(
            ctx,
            timeout_key,
            cross_ai.timeout_value(presets.get_dotted(ctx.existing, timeout_key)),
            "preset",
            f"cross-AI outer timeout (18 D-12); minimum {cross_ai.MIN_TIMEOUT_S}s",
        )
    )
    mgr_key = "manager.flags.execute"
    entries.append(
        make_entry(
            ctx,
            mgr_key,
            cross_ai.manager_flags_value(presets.get_dotted(ctx.existing, mgr_key)),
            "preset",
            "append --cross-ai for cross-AI execution (18 D-09)",
        )
    )
    notes.append({
        "kind": "cross_ai_run",
        "key": mgr_key,
        "text": "cross-AI execution is on: run phases with --cross-ai",
    })
    return entries, notes


def _cross_ai_layer(ctx: PlanCtx, prior_entries: list) -> tuple[list, list]:
    """Layer 3: cross-AI booleans mirror the answers; exec yes wires runner keys (18 D-09)."""
    answers = ctx.answers
    entries = []
    notes = []
    targets = list(ctx.targets)
    review_answer = answers["review"]
    if review_answer["answer"] == "n":
        entries.append(
            make_entry(
                ctx,
                "workflow.plan_review_convergence",
                False,
                "preset" if review_answer["defaulted"] else "user",
                _cross_ai_why(ctx, "review", review_answer),
            )
        )
    else:
        review_entries, review_notes = _cross_ai_review_entries(
            ctx, prior_entries, review_answer,
        )
        entries.extend(review_entries)
        notes.extend(review_notes)

    exec_entries, exec_notes = _cross_ai_exec_entries(ctx, answers["exec"], targets)
    entries.extend(exec_entries)
    notes.extend(exec_notes)
    exec_ans = answers["exec"]
    if exec_ans["answer"] == "n" and exec_ans["defaulted"]:
        _, def_why = cross_ai.exec_default(ctx.host, targets)
        if def_why == cross_ai.NO_TARGET_TEXT:
            notes.append({
                "kind": "cross_ai_exec",
                "key": "workflow.cross_ai_execution",
                "text": f"{cross_ai.NO_TARGET_TEXT}; execution stays on the host",
            })
    return entries, notes


_LEFTOVER_WHY = "managed by the curated plan (D-08); not set by this plan"
_MODEL_POLICY_UNSET_TAIL = (
    "unset per leaf: gsd-core 1.16 rejects config-set model_policy null on the whole object (D-08)"
)
_RUNTIME_WHY = (
    "the gsd-core installer bakes agent models from the project runtime, else "
    "~/.gsd/defaults.json's, and ignores GSD_RUNTIME (D-23)"
)


def _conflict_extra(item: dict) -> dict:
    return {"effect": item["effect"]} if "effect" in item else {}


def _model_policy_unsets(ctx: PlanCtx, item: dict) -> list:
    flat = presets.flatten_config({"model_policy": item["value"]})
    base = item["why"]
    why = f"{base}; {_MODEL_POLICY_UNSET_TAIL}"
    extra = _conflict_extra(item)
    return [
        make_entry(ctx, key, None, "preset", why, op="unset", **extra)
        for key in sorted(flat)
    ]


def _conflicts_by_kind(ctx: PlanCtx) -> list:
    """One conflict per kind; a project-scope conflict wins over a global one."""
    by_kind: dict = {}
    for item in ctx.inv["conflicts"]:
        held = by_kind.get(item["kind"])
        if held is None or (item["scope"] == "project" and held["scope"] != "project"):
            by_kind[item["kind"]] = item
    return [by_kind[kind] for kind in sorted(by_kind)]


def _conflict_unsets(ctx: PlanCtx) -> list:
    entries: list = []
    for item in _conflicts_by_kind(ctx):
        kind = item["kind"]
        if kind == "model_policy":
            entries.extend(_model_policy_unsets(ctx, item))
        elif kind == "resolve_model_ids":
            entries.append(
                make_entry(
                    ctx,
                    "resolve_model_ids",
                    None,
                    "preset",
                    item["why"],
                    op="unset",
                    **_conflict_extra(item),
                )
            )
    return entries


def _leftover_unsets(ctx: PlanCtx, planned: set[str]) -> list:
    entries: list = []
    for key in sorted(presets.flatten_config(ctx.existing)):
        if key in planned or not presets.is_managed(key, ctx.host):
            continue
        entries.append(make_entry(ctx, key, None, "preset", _LEFTOVER_WHY, op="unset"))
    return entries


def _runtime_mismatch_note(ctx: PlanCtx, runtime: str, source: str) -> dict:
    text = (
        f"runtime {runtime} from {source} differs from host {ctx.host}; "
        f"the plan writes no runtime entry on {ctx.host} (D-30); "
        f"change it with plan-set runtime {ctx.host}"
    )
    return {"kind": "runtime_mismatch", "key": "runtime", "text": text}


def _observed_runtime(ctx: PlanCtx) -> tuple[str | None, str]:
    proj = ctx.existing.get("runtime")
    if isinstance(proj, str):
        return proj, "the project config"
    global_vals = ctx.inv["global_defaults"].get("values") or {}
    global_rt = global_vals.get("runtime")
    if isinstance(global_rt, str):
        path = ctx.inv["global_defaults"].get("path")
        label = path if isinstance(path, str) else "global defaults"
        return global_rt, label
    return None, ""


def _runtime_entries(ctx: PlanCtx) -> tuple[list, list]:
    if ctx.host in presets.RUNTIME_MANAGED_HOSTS:
        entry = make_entry(ctx, "runtime", ctx.host, "preset", _RUNTIME_WHY)
        return [entry], []
    runtime, source = _observed_runtime(ctx)
    if runtime is None or runtime == ctx.host:
        return [], []
    return [], [_runtime_mismatch_note(ctx, runtime, source)]


def _skills_agent_why(
    agent: str,
    names: list[str],
    families: list,
    facts: dict[str, bool],
) -> str:
    why_parts: list[str] = []
    for family in families:
        if not isinstance(family, dict):
            continue
        when = family.get("when")
        if when is not None and not facts.get(when, False):
            continue
        fam_skills = family.get("skills")
        fam_agents = family.get("agents")
        if not isinstance(fam_skills, list) or not isinstance(fam_agents, list):
            continue
        if agent not in fam_agents:
            continue
        picked = [n for n in names if n in fam_skills]
        if picked:
            fam_id = family.get("id", "")
            why_parts.append(f"family {fam_id}: {', '.join(picked)}")
    return "; ".join(why_parts) if why_parts else "skill affinity"


_PI_AGENT_SKILLS_EFFECT = "no effect on pi (no GSD agent files installed)"
_JEV_SESSION_NOTE = (
    "jev-fast-decision is inert unless the agent session sets GSD_PATH_JEV=1 and "
    "GSD_PATH_JEV_TIMEOUT_SECONDS"
)


def _agent_skill_entries(
    ctx: PlanCtx, resolved: dict[str, list[str]], affinity: dict, facts: dict[str, bool],
) -> list:
    families = affinity.get("families")
    fam_list = families if isinstance(families, list) else []
    pi_effect = [_PI_AGENT_SKILLS_EFFECT] if ctx.host == "pi" else []
    entries = []
    for agent, names in sorted(resolved.items()):
        effects = pi_effect + skills.entry_caveats(names, ctx.inv)
        entries.append(make_entry(
            ctx,
            f"agent_skills.{agent}",
            names,
            "affinity",
            _skills_agent_why(agent, names, fam_list, facts),
            **({"effect": "; ".join(effects)} if effects else {}),
        ))
    return entries


def _skills_layer(ctx: PlanCtx, prior_entries: list) -> tuple[list, list]:
    """Wire installed skills to agents from curated affinity (18 D-02, D-04, D-33)."""
    affinity = ctx.opts.affinity
    if affinity is None:
        return [], []
    facts = skills.skill_facts(ctx.inv, prior_entries, ctx.existing)
    resolved, notes = skills.resolve(affinity, ctx.inv, facts, ctx.opts.rigor)
    entries = _agent_skill_entries(ctx, resolved, affinity, facts)
    wired = skills.wired_skills(resolved, ctx.inv)
    candidates = skills.trusted_roots(wired, ctx.inv)
    if candidates:
        entries.append(
            make_entry(
                ctx,
                "agent_skills_security.trusted_global_roots",
                None,
                "affinity",
                skills.merged_trusted_roots_why(candidates, ctx.inv),
                status="needs_choice",
                candidates=[skills.trusted_roots_candidate(candidates, ctx.inv)],
            )
        )
    notes.extend(skills.proposals(affinity, ctx.inv))
    if skills.jev_is_wired(resolved):
        notes.append({
            "kind": "jev_session_gate",
            "key": "jev-fast-decision",
            "text": _JEV_SESSION_NOTE,
        })
    return entries, notes


def _reconcile_layer(ctx: PlanCtx, prior_entries: list) -> tuple[list, list]:
    """Last layer: runtime, conflict-driven unsets, then managed leftovers (D-08)."""
    planned = {entry["key"] for entry in prior_entries}
    # A rejected key cannot be unset either; an earlier layer already noted its drop.
    planned.update(ctx.inv["gsd_core"]["valid_keys"]["rejected"])
    runtime_entries, notes = _runtime_entries(ctx)
    conflict_entries = _conflict_unsets(ctx)
    planned.update(entry["key"] for entry in conflict_entries)
    planned.update(entry["key"] for entry in runtime_entries)
    leftover_entries = _leftover_unsets(ctx, planned)
    entries = runtime_entries + conflict_entries + leftover_entries
    return entries, notes


_LAYERS = (
    _preset_layer,
    _tier_layer,
    _slot_layer,
    _specialist_layer,
    _cross_ai_layer,
    _skills_layer,
    _reconcile_layer,
)


def _drop_rejected(ctx: PlanCtx, entries: list) -> tuple[list, list]:
    """D-26/R12: an entry whose key is in `valid_keys.rejected` is dropped and gets its
    own `dropped_key` note naming the key and the host gsd-core version; a key in
    neither list was never probed and raises (the CLI maps it to exit 2)."""
    valid_keys = ctx.inv["gsd_core"]["valid_keys"]
    accepted = set(valid_keys["accepted"])
    probed = accepted | set(valid_keys["rejected"])
    unprobed = sorted(e["key"] for e in entries if e["key"] not in probed)
    if unprobed:
        # Never claim gsd-core rejected a key it was never asked about (fail closed).
        raise ValueError(f"keys not probed by this inventory: {', '.join(unprobed)}")
    version = ctx.inv["gsd_core"].get("version") or "unknown"
    kept, notes = [], []
    for entry in entries:
        if entry["key"] in accepted:
            kept.append(entry)
            continue
        notes.append({
            "kind": "dropped_key",
            "key": entry["key"],
            "text": f"dropped {entry['key']}: not accepted by the host gsd-core "
                    f"{version} isValidConfigKey",
        })
    return kept, notes


def _merge_layers(ctx: PlanCtx) -> tuple[list, list]:
    """Runs the layers in fixed order; a duplicate key (within or across layers) raises instead
    of overwriting (R11 ordering backstop: preset keys can never be silently
    replaced by catalog-driven keys)."""
    all_entries: list = []
    all_notes: list = []
    seen: set[str] = set()
    for layer in _LAYERS:
        entries, notes = layer(ctx, all_entries)
        for entry in entries:
            if entry["key"] in seen:
                raise ValueError(f"duplicate plan key {entry['key']}")
            seen.add(entry["key"])
        # Filter per layer so later layers only see entries that will be written.
        entries, drop_notes = _drop_rejected(ctx, entries)
        all_entries.extend(entries)
        all_notes.extend(notes + drop_notes)
    return all_entries, all_notes


def build_plan(inventory: dict, opts: RecommendOpts) -> dict:
    """The pure entrypoint: returns the canonical plan dict for `inventory` under
    `opts` (same inputs, same dict, byte-identical `plan_schema.canonical_json`)."""
    ctx = PlanCtx(
        inv=inventory,
        opts=opts,
        host=inventory["host"],
        existing=inventory["existing_config"]["values"],
        preset=presets.preset_values(opts.rigor, inventory["project"]),
        targets=tuple(_exec_targets(inventory, opts.rigor)),
    )
    ctx = ctx._replace(answers=cross_ai_answers(ctx))
    entries, notes = _merge_layers(ctx)
    answers = ctx.answers
    exec_yes = answers["exec"]["answer"] == "y"
    targets = list(ctx.targets) if exec_yes else []
    artifacts: list = []
    if exec_yes and targets:
        timeout_key = "workflow.cross_ai_timeout"
        timeout = cross_ai.timeout_value(presets.get_dotted(ctx.existing, timeout_key))
        artifacts = [cross_ai.script_artifact(targets, timeout)]
    skill_affinity = None
    if opts.affinity is not None:
        skill_affinity = {
            "schema_version": opts.affinity.get("schema_version"),
            "as_of": opts.affinity.get("as_of"),
        }
    return {
        "schema_version": plan_schema.PLAN_SCHEMA_VERSION,
        "inventory_digest": plan_schema.inventory_digest(inventory),
        "host": ctx.host,
        "profile": opts.profile,
        "rigor": opts.rigor,
        "cross_ai": answers,
        "skill_affinity": skill_affinity,
        "artifacts": artifacts,
        "entries": sorted(entries, key=lambda entry: entry["key"]),
        "notes": sorted(
            notes, key=lambda note: (note["kind"], note.get("key") or "", note["text"])
        ),
    }
