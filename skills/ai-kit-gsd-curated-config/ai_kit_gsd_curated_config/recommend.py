"""The pure recommendation engine (REC-01): inventory + profile + rigor + the two
cross-AI answers -> one canonical, sorted, explainable plan dict. No subprocess, no
network, no clock, no environment, no filesystem: everything arrives through the
inventory. Imports only `typing` names, `.presets` and `.plan_io` (guarded by the
tests' AST import check).
"""
from typing import Any, NamedTuple

from . import plan_io, presets


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
    """Resolves the two cross-AI answers (17 D-19). An explicit flag wins with
    `defaulted: False`; an omitted flag defaults from rigor and host and is recorded
    as `defaulted: True`. 17-04 narrows the MVP exec default to a cheap other-CLI
    candidate once `roles.cheap_other_cli` exists (spec §5)."""
    other_cli = any(not c.get("is_host", False) for c in ctx.inv["candidates"])
    claude_or_codex = ctx.host in ("claude", "codex")

    def _resolve(flag: str | None, default: str) -> dict:
        return {"answer": flag if flag is not None else default, "defaulted": flag is None}

    review_default = "n"
    standard_qualified = ctx.opts.rigor == "standard" and claude_or_codex and other_cli
    if ctx.opts.rigor == "rigorous" or standard_qualified:
        review_default = "y"
    exec_default = "y" if (ctx.opts.rigor == "mvp" and claude_or_codex and other_cli) else "n"
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
    rigor phase shift. Later plans (17-04/17-06) append the slot and specialist
    layers after this one."""
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
        defaulted = " (defaulted)" if answer["defaulted"] else ""
        entries.append(
            make_entry(
                ctx,
                flag_key,
                yes,
                "preset",
                f"cross-AI {answers_key} answer: {answer['answer']}{defaulted}",
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


_LAYERS = (_preset_layer, _tier_layer, _cross_ai_layer)


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
        "inventory_digest": plan_io.inventory_digest(inventory),
        "host": ctx.host,
        "profile": opts.profile,
        "rigor": opts.rigor,
        "cross_ai": cross_ai_answers(ctx),
        "entries": sorted(entries, key=lambda entry: entry["key"]),
        "notes": sorted(
            notes, key=lambda note: (note["kind"], note.get("key") or "", note["text"])
        ),
    }
