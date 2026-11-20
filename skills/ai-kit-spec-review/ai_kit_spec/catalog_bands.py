"""35 D-05, D-06 (Amend-1), D-07: pure banding rules.

Every cut is a quartile of this refresh's rows; a value on a cut goes to the higher band. No I/O.
"""

import math
import statistics
from typing import NamedTuple

TIERS = ("frontier", "strong", "capable", "light", "unknown")
COST_BANDS = ("low", "medium", "high", "premium", "free_or_local", "unknown")
CLASSES = ("flagship", "coding", "general", "fast", "small", "router", "unknown")
STRENGTH_CATEGORIES = (
    "coding",
    "math",
    "hard_prompts",
    "instruction_following",
    "creative_writing",
    "multi_turn",
)


def _num(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def quartile_cuts(values) -> tuple | None:
    """Return refresh-local quartile cut points, or None with too few values."""
    ordered = sorted(value for value in values if _num(value))
    if len(ordered) < 4:
        return None
    return tuple(ordered[int(len(ordered) * point)] for point in (0.25, 0.5, 0.75))


def _band(value, cuts, names) -> str:
    if value >= cuts[2]:
        return names[0]
    if value >= cuts[1]:
        return names[1]
    if value >= cuts[0]:
        return names[2]
    return names[3]


def tier_for(score, cuts) -> str:
    if not _num(score) or cuts is None:
        return "unknown"
    return _band(score, cuts, ("frontier", "strong", "capable", "light"))


def price_per_million(cost) -> tuple:
    if not isinstance(cost, dict):
        return None, False
    input_price = cost.get("input")
    output_price = cost.get("output")
    if not _num(input_price) or not _num(output_price):
        return None, False
    assert input_price is not None and output_price is not None
    if input_price < 0 or output_price < 0:
        return None, False
    if input_price == 0 and output_price == 0:
        return 0.0, True
    return float(input_price + output_price), False


def _bare_id(model_key: str) -> str:
    return model_key.rsplit("/", 1)[-1]


def cost_cuts(models_dev_data) -> tuple | None:
    groups = {}
    if not isinstance(models_dev_data, dict):
        return None
    for provider in models_dev_data.values():
        if not isinstance(provider, dict):
            continue
        rows = provider.get("models")
        if not isinstance(rows, dict):
            continue
        for model_key, row in rows.items():
            if not isinstance(row, dict):
                continue
            price, free = price_per_million(row.get("cost"))
            if price is None or free:
                continue
            canonical_id = row.get("canonical_model_id")
            group_id = (
                canonical_id
                if isinstance(canonical_id, str) and canonical_id
                else _bare_id(model_key)
            )
            groups.setdefault(group_id, []).append(price)
    medians = [statistics.median(prices) for prices in groups.values()]
    return quartile_cuts(medians)


def cost_band(price, free: bool, cuts) -> str:
    if free:
        return "free_or_local"
    if not _num(price) or cuts is None:
        return "unknown"
    return _band(price, cuts, ("premium", "high", "medium", "low"))


class ClassInputs(NamedTuple):
    router_alias: bool
    tier: str
    cost_band: str
    coding_edge: float | None
    edge_cut: float | None
    tps: float | None
    tps_cut: float | None


def _is_router(inputs: ClassInputs) -> bool:
    return inputs.router_alias


def _is_unknown(inputs: ClassInputs) -> bool:
    return (
        inputs.tier == "unknown"
        and inputs.cost_band == "unknown"
        and inputs.coding_edge is None
        and inputs.tps is None
    )


def _is_flagship(inputs: ClassInputs) -> bool:
    return inputs.tier == "frontier"


def _is_coding(inputs: ClassInputs) -> bool:
    return (
        inputs.tier in ("strong", "capable")
        and inputs.coding_edge is not None
        and inputs.edge_cut is not None
        and inputs.coding_edge >= inputs.edge_cut
    )


def _is_fast(inputs: ClassInputs) -> bool:
    return (
        inputs.tier in ("strong", "capable", "light")
        and inputs.tps is not None
        and inputs.tps_cut is not None
        and inputs.tps >= inputs.tps_cut
    )


def _is_small(inputs: ClassInputs) -> bool:
    return inputs.tier == "light" and inputs.cost_band in ("low", "free_or_local")


_CLASS_RULES = (
    ("router", _is_router),
    ("unknown", _is_unknown),
    ("flagship", _is_flagship),
    ("coding", _is_coding),
    ("fast", _is_fast),
    ("small", _is_small),
)


def class_for(inputs: ClassInputs) -> str:
    for name, predicate in _CLASS_RULES:
        if predicate(inputs):
            return name
    return "general"


def delta_cuts(categories: dict) -> dict:
    if not isinstance(categories, dict) or not isinstance(categories.get("overall"), dict):
        return {}
    overall = categories["overall"]
    result = {}
    for category in STRENGTH_CATEGORIES:
        ratings = categories.get(category)
        if not isinstance(ratings, dict):
            continue
        deltas = [
            rating - overall[name]
            for name, rating in ratings.items()
            if name in overall and _num(rating) and _num(overall[name])
        ]
        cuts = quartile_cuts(deltas)
        if cuts is not None:
            result[category] = cuts[2]
    return result


def strengths_for(ratings: dict, cuts: dict) -> list:
    if not isinstance(ratings, dict) or not isinstance(cuts, dict):
        return []
    overall = ratings.get("overall")
    if not _num(overall):
        return []
    return sorted(
        category
        for category in STRENGTH_CATEGORIES
        if _num(ratings.get(category))
        and _num(cuts.get(category))
        and ratings[category] - overall >= cuts[category]
    )
