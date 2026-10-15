"""The pure recommendation engine (REC-01): inventory + profile + rigor + the two
cross-AI answers -> one canonical, sorted, explainable plan dict. No subprocess, no
network, no clock, no environment, no filesystem: everything arrives through the
inventory. Imports only `typing` names, `.presets`, `.roles` and `.plan_io` (guarded
by the tests' AST import check).
"""
from typing import Any, NamedTuple

from . import plan_io, presets, roles


class RecommendOpts(NamedTuple):
    profile: str
    rigor: str
    cross_ai_review: str | None = None
    cross_ai_exec: str | None = None


class PlanCtx(NamedTuple):
    inv: dict
    opts: RecommendOpts
    host: str
    existing: dict
    preset: dict


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


def _cheap_exec_default(ctx: PlanCtx) -> str:
    if ctx.opts.rigor != "mvp" or ctx.host not in ("claude", "codex"):
        return "n"
    q = presets.PRICE_PERCENTILE["mvp"]
    cheap = roles.cheap_other_cli(ctx.inv["candidates"], q)
    return "y" if cheap is not None else "n"


def cross_ai_answers(ctx: PlanCtx) -> dict:
    """Resolves the two cross-AI answers (17 D-19). An explicit flag wins with
    `defaulted: False`; an omitted flag defaults from rigor and host and is recorded
    as `defaulted: True`. MVP exec defaults to yes only when a cheap other-CLI
    candidate exists (spec §5)."""
    other_cli = any(not c.get("is_host", False) for c in ctx.inv["candidates"])
    claude_or_codex = ctx.host in ("claude", "codex")

    def _resolve(flag: str | None, default: str) -> dict:
        return {"answer": flag if flag is not None else default, "defaulted": flag is None}

    review_default = "n"
    standard_qualified = ctx.opts.rigor == "standard" and claude_or_codex and other_cli
    if ctx.opts.rigor == "rigorous" or standard_qualified:
        review_default = "y"
    exec_default = _cheap_exec_default(ctx)
    return {
        "review": _resolve(ctx.opts.cross_ai_review, review_default),
        "exec": _resolve(ctx.opts.cross_ai_exec, exec_default),
    }


def _preset_layer(ctx: PlanCtx, prior_entries: list) -> tuple[list, list]:
    """Layer 1: every §5 preset key for the chosen rigor plus its conditional keys."""
    del prior_entries
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


def _tier_layer(ctx: PlanCtx, prior_entries: list) -> tuple[list, list]:
    """Layer 2 (tier level): `model_profile` plus one `models.<phase>` entry per
    rigor phase shift. Later plans append the slot layer after this one."""
    del prior_entries
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


def _slot_value(host: str, candidate: dict, target: str) -> Any:
    if host == "codex":
        modes = candidate.get("reasoning_modes") or []
        return {
            "model": candidate["model"],
            "reasoning_effort": roles.clamp_effort(target, modes),
        }
    return candidate["model"]


def _keep_why(existing: Any) -> tuple[str, str]:
    why = "kept gsd default: present on host, within ceiling"
    op = "keep"
    if existing is not None:
        op = "unset"
        why += "; removes the existing override"
    return op, why


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
    return make_entry(
        req.ctx,
        req.key,
        _slot_value(req.ctx.host, pick.candidate, req.target),
        "catalog-score",
        why,
        **req.extra,
    )


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
            _slot_value(ctx.host, native_c, meta.target),
            "native",
            why,
            op=op,
            **meta.extra,
        )
    reason = _override_reason(ctx, native_id, native_c, ceiling)
    req = _PickRequest(ctx, meta.key, reason, meta.purpose, meta.target, ceiling, meta.extra)
    if (picked := _catalog_pick_entry(req, cands)) is not None:
        return picked
    no_scores = not any(c["score_axes"] > 0 for c in cands)
    tail = (
        f"no scores: no {ctx.host} candidate has a catalog score; choose with plan-set"
        if no_scores
        else f"no eligible {meta.purpose} candidate on {ctx.host}; choose with plan-set"
    )
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
        key = f"model_profile_overrides.codex.{tier}"
        native_id = _native_model(ctx, tier)
        band = roles.TIER_EFFORT_BAND[tier]
        target = ctx.preset[f"effort.routing_tier_defaults.{band}"]
        existing = presets.get_dotted(ctx.existing, key)
        op, _ = _keep_why(existing)
        why = (
            "kept gsd default: codex enumerated no models; presence and ceiling unchecked"
            + ("; removes the existing override" if existing is not None else "")
        )
        value = None
        if native_id is not None:
            slot = ctx.inv["gsd_core"]["runtime_profile_map"]["codex"][tier]
            modes = slot.get("reasoning_modes") or []
            value = _slot_value(
                "codex",
                {"model": native_id, "reasoning_modes": modes},
                target,
            )
        entries.append(
            make_entry(ctx, key, value, "native", why, op=op, effect=effect),
        )
    return entries, []


def _pi_slot(ctx: PlanCtx, tiers: tuple[str, ...]) -> tuple[list, list]:
    if "sonnet" not in tiers:
        note = {
            "kind": "pi",
            "key": None,
            "text": (
                "pi: only an opt-in model_profile_overrides.pi.sonnet is offered; "
                "no per-agent model_overrides (effect unverified on pi, gsd-core registry: "
                "namedDispatch false)"
            ),
        }
        return [], [note]
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
    note = {
        "kind": "pi",
        "key": None,
        "text": (
            "pi: only an opt-in model_profile_overrides.pi.sonnet is offered; "
            "no per-agent model_overrides (effect unverified on pi, gsd-core registry: "
            "namedDispatch false)"
        ),
    }
    return [entry], [note]


def _slot_layer(ctx: PlanCtx, prior_entries: list) -> tuple[list, list]:
    """Layer 2b: per-tier model_profile_overrides for the host (D-01..D-06)."""
    del prior_entries
    if ctx.host == "claude":
        return [], []
    shifts = presets.PHASE_SHIFTS[ctx.opts.rigor]
    tiers = roles.used_tiers(ctx.inv["gsd_core"], ctx.opts.profile, shifts)
    if ctx.host == "pi":
        return _pi_slot(ctx, tiers)
    cands = [c for c in ctx.inv["candidates"] if c.get("is_host", False)]
    if ctx.host == "codex" and not cands:
        return _codex_empty_slots(ctx, tiers)
    ceiling = roles.host_ceiling(cands, presets.PRICE_PERCENTILE[ctx.opts.rigor])
    entries = [_tier_slot(ctx, tier, cands, ceiling) for tier in tiers]
    return entries, []


def _cross_ai_why(ctx: PlanCtx, answers_key: str, answer: dict) -> str:
    defaulted = " (defaulted)" if answer["defaulted"] else ""
    base = f"cross-AI {answers_key} answer: {answer['answer']}{defaulted}"
    if answers_key != "exec" or answer["answer"] != "y" or not answer["defaulted"]:
        return base
    cheap = roles.cheap_other_cli(ctx.inv["candidates"], presets.PRICE_PERCENTILE["mvp"])
    if cheap is None:
        return base + "; no cheap other-CLI candidate within the MVP ceiling"
    return (
        f"{base}; cheap candidate {cheap['runtime']} {cheap['model']} at "
        f"{cheap['price']:g}/1M within the MVP ceiling"
    )


def _cross_ai_layer(ctx: PlanCtx, prior_entries: list) -> tuple[list, list]:
    """Layer 3: the cross-AI boolean keys mirror the answers; each yes reserves a
    needs_choice slot for the Phase 18 selection key (17 D-19)."""
    del prior_entries
    answers = cross_ai_answers(ctx)
    entries = []
    for answers_key, flag_key, command_key in (
        ("review", "workflow.plan_review_convergence", "review.default_reviewers"),
        ("exec", "workflow.cross_ai_execution", "workflow.cross_ai_command"),
    ):
        answer = answers[answers_key]
        yes = answer["answer"] == "y"
        entries.append(
            make_entry(
                ctx,
                flag_key,
                yes,
                "preset",
                _cross_ai_why(ctx, answers_key, answer),
            )
        )
        if yes:
            entries.append(
                make_entry(
                    ctx,
                    command_key,
                    None,
                    "preset",
                    "reserved for Phase 18 cross-AI selection (D-19)",
                    status="needs_choice",
                    candidates=[],
                )
            )
    return entries, []


_LAYERS = (_preset_layer, _tier_layer, _slot_layer, _cross_ai_layer)


def _drop_rejected(ctx: PlanCtx, entries: list) -> tuple[list, list]:
    """D-26/R12: an entry whose key is not in `valid_keys.accepted` is dropped and
    gets its own `dropped_key` note naming the key and the host gsd-core version."""
    accepted = set(ctx.inv["gsd_core"]["valid_keys"]["accepted"])
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
    """Runs the layers in fixed order; a duplicate key across layers raises instead
    of overwriting (R11 ordering backstop: preset keys can never be silently
    replaced by catalog-driven keys)."""
    all_entries: list = []
    all_notes: list = []
    for layer in _LAYERS:
        entries, notes = layer(ctx, all_entries)
        for entry in entries:
            if any(existing["key"] == entry["key"] for existing in all_entries):
                raise ValueError(f"duplicate plan key {entry['key']}")
        all_entries.extend(entries)
        all_notes.extend(notes)
    return all_entries, all_notes


def _digest_inventory(inventory: dict) -> dict:
    """Candidate order is not significant for the plan fingerprint (R7)."""
    stable = dict(inventory)
    stable["candidates"] = sorted(
        inventory["candidates"],
        key=lambda c: (c.get("runtime") or "", c.get("model") or ""),
    )
    return stable


def build_plan(inventory: dict, opts: RecommendOpts) -> dict:
    """The pure entrypoint: returns the canonical plan dict for `inventory` under
    `opts` (same inputs, same dict, byte-identical `plan_io.canonical_json`)."""
    ctx = PlanCtx(
        inv=inventory,
        opts=opts,
        host=inventory["host"],
        existing=inventory["existing_config"]["values"],
        preset=presets.preset_values(opts.rigor, inventory["project"]),
    )
    entries, notes = _merge_layers(ctx)
    entries, drop_notes = _drop_rejected(ctx, entries)
    notes.extend(drop_notes)
    return {
        "schema_version": plan_io.PLAN_SCHEMA_VERSION,
        "inventory_digest": plan_io.inventory_digest(_digest_inventory(inventory)),
        "host": ctx.host,
        "profile": opts.profile,
        "rigor": opts.rigor,
        "cross_ai": cross_ai_answers(ctx),
        "entries": sorted(entries, key=lambda entry: entry["key"]),
        "notes": sorted(
            notes, key=lambda note: (note["kind"], note.get("key") or "", note["text"])
        ),
    }
