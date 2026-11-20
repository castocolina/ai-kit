"""35 D-05, D-06 (Amend-1): tier, class and strengths from Artificial Analysis and Arena.

Facts are labeled by the deciding source; matching goes through model_names and jev is optional.
"""
# pylint: disable=protected-access
# catalog_bands._num is the shared numeric check (plan 35-16 names it).

from typing import NamedTuple

from ai_kit_spec import catalog_bands
from ai_kit_spec.catalog_labels import fact
from ai_kit_spec.model_names import resolve_many, split_effort


class _Cuts(NamedTuple):
    arena: object
    aa: object
    aa_edge: float | None
    aa_tps: float | None
    arena_deltas: dict
    aa_on: bool


class _Times(NamedTuple):
    aa: str
    arena: str


class _Run(NamedTuple):
    index: dict
    matches: dict
    cuts: _Cuts
    times: _Times
    inputs: object


def source_enabled(inputs, source: str) -> bool:
    return inputs.settings is None or source in getattr(inputs.settings, "sources", ())


def arena_index(arena_data) -> dict:
    index = {}
    categories = arena_data.get("categories") if isinstance(arena_data, dict) else None
    if not isinstance(categories, dict):
        return index
    for category, rows in categories.items():
        if not isinstance(rows, dict):
            continue
        for name, record in rows.items():
            if not isinstance(name, str) or not isinstance(record, dict):
                continue
            rating = record.get("rating")
            if not catalog_bands._num(rating):
                continue
            parts = split_effort("arena", name)
            slot = index.setdefault(
                parts.base, {"display": parts.base, "ratings": {}, "efforts": {}}
            )
            if parts.efforts and category == "overall":
                slot["efforts"][parts.efforts[0]] = rating
            elif not parts.efforts:
                slot["ratings"][category] = rating
    return index


def arena_matches(entry_keys: list, index: dict, name_judge) -> dict:
    names = {key: key.split("/", 1)[-1] for key in entry_keys}
    pool = {display: display for display in index}
    results = resolve_many(list(names.values()), pool, judge_batch=name_judge)
    return {
        key: (results[name].key, results[name].state, results[name].confidence)
        for key, name in names.items()
        if name in results and results[name].state in ("matched", "judged")
    }


def _aa_fields(model: dict) -> tuple:
    evaluations = model.get("evaluations", {})
    performance = model.get("performance", {})
    return (
        evaluations.get("artificial_analysis_intelligence_index"),
        evaluations.get("artificial_analysis_coding_index"),
        performance.get("median_output_tokens_per_second"),
    )


def aa_cuts(aa_models) -> tuple:
    intelligence, edges, tps_values = [], [], []
    for model in aa_models if isinstance(aa_models, list) else []:
        if not isinstance(model, dict):
            continue
        score, coding, tps = _aa_fields(model)
        if catalog_bands._num(score):
            intelligence.append(score)
        if catalog_bands._num(score) and catalog_bands._num(coding):
            edges.append(coding - score)
        if catalog_bands._num(tps):
            tps_values.append(tps)
    cuts, edge_cuts, tps_cuts = (
        catalog_bands.quartile_cuts(intelligence),
        catalog_bands.quartile_cuts(edges),
        catalog_bands.quartile_cuts(tps_values),
    )
    return cuts, edge_cuts[2] if edge_cuts else None, tps_cuts[2] if tps_cuts else None


def _arena_overall_scores(index) -> list:
    return [
        value
        for slot in index.values()
        for value in (
            (
                [slot["ratings"]["overall"]]
                if catalog_bands._num(slot["ratings"].get("overall"))
                else []
            )
            + [rating for rating in slot["efforts"].values() if catalog_bands._num(rating)]
        )
    ]


def tier_fact(entry, slot, cuts, times) -> dict | None:
    scores = entry.get("scores", {}) if cuts.aa_on else {}
    score = scores.get("intelligence_index") if isinstance(scores, dict) else None
    if catalog_bands._num(score) and cuts.aa is not None:
        result = fact(
            catalog_bands.tier_for(score, cuts.aa),
            "judged",
            "artificial-analysis",
            times.aa,
            confidence="rule",
        )
        result["note"] = "effort not distinguished"
        return result
    if not isinstance(slot, dict) or cuts.arena is None:
        return None
    ratings, efforts = slot.get("ratings", {}), slot.get("efforts", {})
    overall = ratings.get("overall") if isinstance(ratings, dict) else None
    if not catalog_bands._num(overall) and not efforts:
        return None
    effort_tiers = {
        effort: catalog_bands.tier_for(value, cuts.arena) for effort, value in efforts.items()
    }
    if catalog_bands._num(overall):
        value = catalog_bands.tier_for(overall, cuts.arena)
    elif effort_tiers:
        order = {name: pos for pos, name in enumerate(("light", "capable", "strong", "frontier"))}
        value = max(effort_tiers.values(), key=lambda tier: order.get(tier, -1))
    else:
        return None
    result = fact(value, "judged", "arena", times.arena, confidence="rule")
    if effort_tiers:
        result["by_effort"] = effort_tiers
    else:
        result["note"] = "effort not distinguished"
    return result


def class_fact(entry, tier, edges, now, tps_cut=None) -> dict:
    facts = entry.get("facts", {})
    cost = facts.get("cost_band", {})
    tps = entry.get("tokens_per_sec") if tps_cut is not None else None
    tier_value = tier.get("value") if isinstance(tier, dict) else tier
    edge, edge_cut, edge_source = edges if edges else (None, None, None)
    value = catalog_bands.class_for(
        catalog_bands.ClassInputs(
            False,
            tier_value or "unknown",
            cost.get("value", "unknown") if isinstance(cost, dict) else "unknown",
            edge,
            edge_cut,
            tps,
            tps_cut,
        )
    )
    inputs = []
    if isinstance(tier, dict) and tier.get("source"):
        inputs.append(tier["source"])
    if edge is not None and edge_source:
        inputs.append(edge_source)
    if isinstance(cost, dict) and cost.get("source"):
        inputs.append(cost["source"])
    if tps is not None:
        inputs.append("artificial-analysis")
    result = fact(value, "judged", "ai-kit class rule", now, confidence="rule")
    result["inputs"] = sorted(set(inputs))
    return result


def strengths_fact(slot, deltas, now) -> dict:
    return fact(
        catalog_bands.strengths_for(slot.get("ratings", {}), deltas),
        "judged",
        "arena",
        now,
        confidence="rule",
    )


def _aa_edge(entry) -> float | None:
    scores = entry.get("scores", {})
    coding = scores.get("coding_index") if isinstance(scores, dict) else None
    intelligence = scores.get("intelligence_index") if isinstance(scores, dict) else None
    if catalog_bands._num(coding) and catalog_bands._num(intelligence):
        assert coding is not None and intelligence is not None
        return coding - intelligence
    return None


def _edge(entry, slot, run):
    ratings = slot.get("ratings", {}) if isinstance(slot, dict) else {}
    coding, overall = ratings.get("coding"), ratings.get("overall")
    if catalog_bands._num(coding) and catalog_bands._num(overall):
        assert coding is not None and overall is not None
        return coding - overall, run.cuts.arena_deltas.get("coding"), "arena"
    edge = _aa_edge(entry) if run.cuts.aa_on else None
    if edge is not None:
        return edge, run.cuts.aa_edge, "artificial-analysis"
    return None, None, None


def _has_no_measured_fields(entry, slot, aa_on):
    facts = entry.get("facts", {})
    measured = any(
        isinstance(value, dict) and value.get("label") == "measured" for value in facts.values()
    )
    return (
        not measured
        and not entry.get("scores")
        and not (aa_on and entry.get("tokens_per_sec") is not None)
        and slot is None
    )


def _entry_facts(key, entry, run) -> tuple:
    match = run.matches.get(key)
    slot = run.index.get(match[0]) if match else None
    tier = tier_fact(entry, slot, run.cuts, run.times)
    if tier is not None and match and match[1] == "judged":
        tier.update(match="judged", match_confidence=match[2])
    edge, edge_cut, edge_source = _edge(entry, slot, run)
    class_entry = entry if run.cuts.aa_on else {**entry, "scores": None, "tokens_per_sec": None}
    edge_data = (edge, edge_cut, edge_source) if edge is not None else ()
    cls = class_fact(
        class_entry,
        tier,
        edge_data,
        run.inputs.now,
        tps_cut=run.cuts.aa_tps if run.cuts.aa_on else None,
    )
    facts = {"class": cls}
    if tier is not None:
        facts["tier"] = tier
    if slot and "overall" in slot["ratings"]:
        facts["strengths"] = strengths_fact(slot, run.cuts.arena_deltas, run.times.arena)
    judge = (
        (key, key.split("/", 1)[-1])
        if cls["value"] == "unknown" and _has_no_measured_fields(entry, slot, run.cuts.aa_on)
        else None
    )
    return facts, judge


def _judge_unknown_classes(unknown, inputs) -> dict:
    judge = inputs.class_judge
    if not unknown or judge is None:
        return {}
    answers = judge([(name, "no measured fields") for _, name in unknown])
    answers = answers if isinstance(answers, list) else []
    output = {}
    for (key, _), answer in zip(unknown, answers, strict=False):
        if (
            isinstance(answer, tuple)
            and len(answer) == 3
            and answer[0] in catalog_bands.CLASSES
            and catalog_bands._num(answer[1])
            and 0 <= answer[1] <= 1
        ):
            output[key] = fact(answer[0], "judged", "jev", inputs.now, confidence=answer[1])
    return output


def _build_run(catalog, sources, inputs) -> _Run:
    arena_on = source_enabled(inputs, "arena")
    aa_on = source_enabled(inputs, "artificial-analysis")
    index = (
        arena_index(sources.arena_data) if getattr(sources, "arena_ok", False) and arena_on else {}
    )
    keys = [key for key, entry in catalog.items() if entry.get("provider") != "router-env"]
    matches = arena_matches(keys, index, inputs.name_judge)
    aa_models = sources.aa_models if aa_on and sources.aa_ok else []
    aa_cut, aa_edge, aa_tps = aa_cuts(aa_models)
    categories = {
        name: {
            display: slot["ratings"][name]
            for display, slot in index.items()
            if name in slot["ratings"]
        }
        for name in (*catalog_bands.STRENGTH_CATEGORIES, "overall")
    }
    cuts = _Cuts(
        catalog_bands.quartile_cuts(_arena_overall_scores(index)),
        aa_cut,
        aa_edge,
        aa_tps,
        catalog_bands.delta_cuts(categories),
        aa_on,
    )
    times = _Times(
        inputs.source_at.get("artificial_analysis") or inputs.now,
        inputs.source_at.get("arena") or inputs.now,
    )
    return _Run(index, matches, cuts, times, inputs)


def _has_judged_class(entry) -> bool:
    cached = entry.get("facts", {}).get("class")
    return isinstance(cached, dict) and cached.get("source") == "jev"


def tier_facts(catalog: dict, sources, inputs) -> dict:
    run = _build_run(catalog, sources, inputs)
    output, unknown = {}, []
    for key, entry in catalog.items():
        if entry.get("provider") == "router-env":
            continue
        facts, judge = _entry_facts(key, entry, run)
        output[key] = facts
        if judge:
            unknown.append(judge)
    answers = _judge_unknown_classes(unknown, inputs)
    for key, _ in unknown:
        if key in answers:
            output[key]["class"] = answers[key]
        elif _has_judged_class(catalog[key]):
            del output[key]["class"]  # a refresh never degrades a class that jev judged earlier
    return output
