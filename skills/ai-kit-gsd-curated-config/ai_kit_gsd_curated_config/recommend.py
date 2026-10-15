"""The pure recommendation engine (REC-01): inventory + profile + rigor -> one
canonical, sorted, explainable plan dict. No subprocess, no network, no clock, no
environment, no filesystem: everything arrives through the inventory. Imports only
`typing` names, `.presets` and `.plan_io` (guarded by the tests' AST import check).
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


def _preset_layer(ctx: PlanCtx, prior_entries: list) -> tuple[list, list]:
    """Layer 1: every §5 preset key for the chosen rigor plus its conditional keys."""
    del prior_entries
    entries = [
        make_entry(ctx, key, ctx.preset[key], "preset", f"rigor {ctx.opts.rigor} preset (spec §5)")
        for key in sorted(ctx.preset)
    ]
    return entries, []


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
        )
    ]
    for phase in sorted(presets.PHASE_SHIFTS[ctx.opts.rigor]):
        tier = presets.PHASE_SHIFTS[ctx.opts.rigor][phase]
        entries.append(
            make_entry(
                ctx,
                f"models.{phase}",
                tier,
                "preset",
                f"rigor {ctx.opts.rigor} shifts the whole {phase} phase to {tier}",
            )
        )
    return entries, []


_LAYERS = (_preset_layer, _tier_layer)


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
    return {
        "schema_version": plan_io.PLAN_SCHEMA_VERSION,
        "inventory_digest": plan_io.inventory_digest(inventory),
        "host": ctx.host,
        "profile": opts.profile,
        "rigor": opts.rigor,
        "entries": sorted(entries, key=lambda entry: entry["key"]),
        "notes": sorted(
            notes, key=lambda note: (note["kind"], note.get("key") or "", note["text"])
        ),
    }
