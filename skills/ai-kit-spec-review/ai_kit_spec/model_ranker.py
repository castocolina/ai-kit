"""Purpose-weighted ranking of model-catalog entries (design spec 2026-09-02, Section 6).
Pure functions -- no network, no file writes. score_candidates never mutates its inputs."""
import copy
import math
import os

try:
    import tomllib as _tomllib_impl
    tomllib = _tomllib_impl
except ModuleNotFoundError:          # Python < 3.11 -- degrade to the hardcoded defaults.
    tomllib = None  # type: ignore[assignment]

DEFAULT_RANKING_WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "references", "ranking-weights.toml")

# Mirrors ranking-weights.toml exactly -- used only when the file is missing/unreadable/
# malformed, so ranking never blocks on a corrupted or absent weights file.
DEFAULT_WEIGHTS = {
    "review": {"intelligence_index": 0.30, "coding_index": 0.10, "agentic_index": 0.15,
               "context_window": 0.15, "tool_calling": 0.05, "price": 0.15, "speed": 0.05},
    "execute": {"intelligence_index": 0.15, "coding_index": 0.30, "agentic_index": 0.25,
                "context_window": 0.10, "tool_calling": 0.15, "price": 0.15, "speed": 0.10},
    "bonuses": {"batch_mode": 8, "fallback_quota": 5, "bonus_cap": 15},
}

_REQUIRED_AXES = {"intelligence_index", "coding_index", "agentic_index", "context_window",
                   "tool_calling", "price", "speed"}
_REQUIRED_BONUS_FIELDS = {"batch_mode", "fallback_quota", "bonus_cap"}


def _is_valid_weights_structure(weights) -> bool:
    """HIGH finding: syntactically-valid TOML that doesn't match the shape score_candidates
    actually needs (a missing purpose section/axis, a non-numeric axis value, or a missing
    bonus field) must not reach score_candidates -- it would raise a KeyError/TypeError deep
    inside ranking instead of degrading to defaults up front, breaking the "malformed
    configuration never blocks ranking" promise this module makes. Checked eagerly, once, at
    load time -- score_candidates itself trusts its `weights` argument completely."""
    if not isinstance(weights, dict):
        return False
    for purpose in ("review", "execute"):
        axes = weights.get(purpose)
        if not isinstance(axes, dict) or _REQUIRED_AXES - axes.keys():
            return False
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in axes.values()):
            return False
    bonuses = weights.get("bonuses")
    if not isinstance(bonuses, dict) or _REQUIRED_BONUS_FIELDS - bonuses.keys():
        return False
    return all(isinstance(bonuses[f], (int, float)) and math.isfinite(bonuses[f])
               for f in _REQUIRED_BONUS_FIELDS)


def load_ranking_weights(path: str = DEFAULT_RANKING_WEIGHTS_PATH) -> dict:
    """Never raises: missing file, unreadable file, malformed TOML, no tomllib (<3.11), or
    syntactically-valid-but-structurally-wrong TOML (missing section/axis/bonus field, or a
    non-numeric axis value) all fall back to an INDEPENDENT COPY of DEFAULT_WEIGHTS -- a
    `copy.deepcopy`, never the shared module-level dict, so one caller mutating its result
    (e.g. a test) can never corrupt what the next call returns."""
    if tomllib is None:
        return copy.deepcopy(DEFAULT_WEIGHTS)
    try:
        with open(path, "rb") as f:
            weights = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return copy.deepcopy(DEFAULT_WEIGHTS)
    if not _is_valid_weights_structure(weights):
        return copy.deepcopy(DEFAULT_WEIGHTS)
    return weights


def _max_context_window(entry: dict) -> float | None:
    windows = [rt.get("ctx_window") for rt in entry.get("runtimes", {}).values()
               if rt.get("ctx_window") is not None]
    return max(windows) if windows else None


def _normalize_minmax(raw: dict, invert: bool = False) -> dict:
    """raw: {key: float|None}. None stays None (excluded from scoring downstream, never
    treated as 0). A set with no present values, or where every present value is identical,
    normalizes every present value to 100 -- there is no meaningful spread to rank by, and a
    single-candidate set must never divide by zero."""
    present = {k: v for k, v in raw.items() if v is not None}
    if not present:
        return dict.fromkeys(raw)
    lo, hi = min(present.values()), max(present.values())
    if hi == lo:
        return {k: (100.0 if v is not None else None) for k, v in raw.items()}

    def scale(v):
        if v is None:
            return None
        pct = (v - lo) / (hi - lo) * 100.0
        return 100.0 - pct if invert else pct

    return {k: scale(v) for k, v in raw.items()}


def score_candidates(entries: list, purpose: str, weights: dict) -> list:
    """purpose: "review" or "execute". Absent axes are excluded from the weighted sum and the
    remaining weights renormalize proportionally (spec Section 6) -- missing data never
    penalizes, it just contributes no signal. price and context_window/speed are normalized
    RELATIVE TO THIS CALL'S entries (never a fixed global ceiling) -- price inverted (cheaper
    scores higher). Returns shallow copies of `entries`, each with an added "score" (0-100,
    rounded to 1 decimal), sorted descending; never mutates the input list/dicts. No
    task_affinity bonus -- see ranking-weights.toml's own note on why that spec-named bonus is
    deliberately absent from this implementation."""
    axis_weights = weights[purpose]
    price_raw = {e["key"]: e.get("pricing", {}).get("input_per_1m") for e in entries}
    price_norm = _normalize_minmax(price_raw, invert=True)
    speed_norm = _normalize_minmax({e["key"]: e.get("tokens_per_sec") for e in entries})
    ctx_raw = {e["key"]: (math.log10(w) if (w := _max_context_window(e)) else None)
               for e in entries}
    ctx_norm = _normalize_minmax(ctx_raw)

    scored = []
    for e in entries:
        tool_call = e.get("tool_calling")
        axis_values = {
            "intelligence_index": e.get("scores", {}).get("intelligence_index"),
            "coding_index": e.get("scores", {}).get("coding_index"),
            "agentic_index": e.get("scores", {}).get("agentic_index"),
            "tool_calling": 100.0 if tool_call is True else (0.0 if tool_call is False else None),
            "context_window": ctx_norm[e["key"]],
            "price": price_norm[e["key"]],
            "speed": speed_norm[e["key"]],
        }
        present = {a: v for a, v in axis_values.items() if v is not None}
        weight_sum = sum(axis_weights[a] for a in present)
        base = (sum(axis_weights[a] * v for a, v in present.items()) / weight_sum
                if weight_sum else 0.0)
        bonus = 0.0
        if e.get("batch_mode"):
            bonus += weights["bonuses"]["batch_mode"]
        if e.get("fallback_quota"):
            bonus += weights["bonuses"]["fallback_quota"]
        bonus = min(bonus, weights["bonuses"]["bonus_cap"])
        score = min(100.0, base + bonus)
        scored.append({**e, "score": round(score, 1)})
    return sorted(scored, key=lambda e: e["score"], reverse=True)
