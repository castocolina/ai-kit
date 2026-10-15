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

# Purpose names (16 D-10) and aliases: execute is an alias of execution, review is an alias
# of itself.
CANONICAL_PURPOSES = ("planning", "general", "mechanical", "execution", "review")
PURPOSE_ALIASES = {"execute": "execution", "review": "review"}

# Mirrors ranking-weights.toml exactly -- used only when the file is missing/unreadable/
# malformed, so ranking never blocks on a corrupted or absent weights file.
DEFAULT_WEIGHTS = {
    "review": {"intelligence_index": 0.30, "coding_index": 0.10, "agentic_index": 0.15,
               "context_window": 0.15, "tool_calling": 0.05, "price": 0.15, "speed": 0.05},
    "execution": {"intelligence_index": 0.10, "coding_index": 0.25, "agentic_index": 0.20,
                  "context_window": 0.05, "tool_calling": 0.10, "price": 0.25, "speed": 0.05},
    "planning": {"intelligence_index": 0.40, "coding_index": 0.10, "agentic_index": 0.25,
                 "context_window": 0.10, "tool_calling": 0.05, "price": 0.05, "speed": 0.05},
    "general": {"intelligence_index": 0.25, "coding_index": 0.15, "agentic_index": 0.15,
                "context_window": 0.10, "tool_calling": 0.05, "price": 0.20, "speed": 0.10},
    "mechanical": {"intelligence_index": 0.05, "coding_index": 0.15, "agentic_index": 0.05,
                   "context_window": 0.05, "tool_calling": 0.05, "price": 0.55, "speed": 0.10,
                   "floor": {"coding_index": 35}},
    "bonuses": {"batch_mode": 8, "fallback_quota": 5, "bonus_cap": 15},
}

# A missing axis no longer excludes itself from the weighted average -- it defaults to
# just below the midpoint of the 0-100 scale (max/2 - 1 = 49.0), so a candidate present on
# only a few axes -- even if every one of those few axes normalizes favorably (e.g. a $0
# price) -- can no longer trivially outrank a candidate with real, comparatively weaker
# data spread across many axes. User-directed design change, 2026-09-04 -- supersedes the
# design spec's original "missing axis excluded from the weighted sum, never zeroed"
# contract (docs/superpowers/specs/2026-09-02-model-discovery-curation-design.md,
# Section 6), after live verification against a real catalog showed that contract let
# data-free candidates dominate the top ranks over real flagships. The 49.0 default applies
# only when scoring survivors (after optional per-purpose floors); a purpose floor is checked
# on raw scores values before normalization, so the default can never satisfy a floor (16 D-11).
_MISSING_AXIS_DEFAULT = 49.0

_REQUIRED_AXES = {"intelligence_index", "coding_index", "agentic_index", "context_window",
                   "tool_calling", "price", "speed"}
_REQUIRED_BONUS_FIELDS = {"batch_mode", "fallback_quota", "bonus_cap"}
_FLOOR_KEY = "floor"
_FLOORABLE_AXES = {"intelligence_index", "coding_index", "agentic_index"}


def resolve_purpose(purpose: str) -> str:
    """Map a purpose name or alias to its canonical name (16 D-10)."""
    return PURPOSE_ALIASES.get(purpose, purpose)


def _is_finite_number(value) -> bool:
    """True only for an int or float that is NOT a bool and that math.isfinite accepts.
    Rejects bool (isinstance(True, int) is true in Python) and non-finite values (NaN, inf).
    Used to validate every axis weight, every bonus field and every floor value (review cycle 1)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _normalize_purpose_aliases(weights: dict) -> dict:
    """Return a NEW dict with purpose aliases resolved (16 D-10). Only aliases whose
    canonical name DIFFERS from the alias are processed (today only execute -> execution):
    such a section is moved to the canonical key when the canonical key is absent and dropped
    when both are present (the canonical section wins). Every other key -- including review,
    whose alias entry maps to itself -- is copied unchanged as an ordinary section."""
    result = {}
    for key, value in weights.items():
        canonical = resolve_purpose(key)
        if canonical != key:  # This is an alias (e.g., "execute" -> "execution")
            if canonical not in weights:  # Only move if canonical is absent
                result[canonical] = value
            # else: canonical is present, so skip this alias section
        else:  # Not an alias (e.g., "review" stays "review")
            result[key] = value
    return result


def _is_valid_purpose_section(section) -> bool:
    """Validate a single purpose section dict: every _REQUIRED_AXES key must be present with
    every value passing _is_finite_number. An optional floor table is allowed but must be
    a dict whose keys are all in _FLOORABLE_AXES and whose values all pass _is_finite_number."""
    if not isinstance(section, dict):
        return False
    # Check required axes
    if _REQUIRED_AXES - section.keys():
        return False
    # Validate axes values (excluding the optional floor key)
    for key in _REQUIRED_AXES:
        if not _is_finite_number(section[key]):
            return False
    # Validate optional floor
    if _FLOOR_KEY in section:
        floor = section[_FLOOR_KEY]
        if not isinstance(floor, dict):
            return False
        for axis, minimum in floor.items():
            if axis not in _FLOORABLE_AXES or not _is_finite_number(minimum):
                return False
    return True


def _passes_floor(entry: dict, floor: dict) -> bool:
    """Check if a candidate passes the floor constraints (16 D-11). For each (axis, minimum),
    the candidate's raw entry["scores"][axis] must exist (scores must be a dict), pass
    _is_finite_number, and be >= minimum; otherwise False. If floor is empty, returns True."""
    if not floor:
        return True
    scores = entry.get("scores")
    if not isinstance(scores, dict):
        return False
    for axis, minimum in floor.items():
        value = scores.get(axis)
        if not _is_finite_number(value) or value < minimum:
            return False
    return True


def _is_valid_weights_structure(weights) -> bool:
    """HIGH finding: syntactically-valid TOML that doesn't match the shape score_candidates
    actually needs (a present-but-malformed purpose section/axis, a non-numeric axis value
    including a bool, or a missing bonus field) must not reach score_candidates -- it would
    raise a KeyError/TypeError deep inside ranking instead of degrading to defaults up front,
    breaking the "malformed configuration never blocks ranking" promise this module makes.
    A missing purpose is NOT a reason to reject the file (load_ranking_weights fills it from
    DEFAULT_WEIGHTS). Checked eagerly, once, at load time -- score_candidates itself trusts
    its `weights` argument completely."""
    if not isinstance(weights, dict):
        return False
    # Validate each purpose present in CANONICAL_PURPOSES
    for purpose in CANONICAL_PURPOSES:
        if purpose in weights and not _is_valid_purpose_section(weights[purpose]):
            return False
    # Validate bonuses
    bonuses = weights.get("bonuses")
    if not isinstance(bonuses, dict) or _REQUIRED_BONUS_FIELDS - bonuses.keys():
        return False
    return all(_is_finite_number(bonuses[f]) for f in _REQUIRED_BONUS_FIELDS)


def load_ranking_weights(path: str = DEFAULT_RANKING_WEIGHTS_PATH) -> dict:
    """Never raises: missing file, unreadable file, malformed TOML, invalid UTF-8 bytes,
    no tomllib (<3.11), or syntactically-valid-but-structurally-wrong TOML (missing section/
    axis/bonus field, a non-numeric axis value, or a bool value) all fall back to an
    INDEPENDENT COPY of DEFAULT_WEIGHTS -- a `copy.deepcopy`, never the shared module-level
    dict, so one caller mutating its result (e.g. a test) can never corrupt what the next
    call returns. A file with only the old [review]/[execute] purposes still loads: missing
    new purposes are filled from DEFAULT_WEIGHTS."""
    if tomllib is None:
        return copy.deepcopy(DEFAULT_WEIGHTS)
    try:
        with open(path, "rb") as f:
            weights = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return copy.deepcopy(DEFAULT_WEIGHTS)
    # Normalize purpose aliases (e.g., execute -> execution)
    weights = _normalize_purpose_aliases(weights)
    if not _is_valid_weights_structure(weights):
        return copy.deepcopy(DEFAULT_WEIGHTS)
    # Fill in missing purposes from DEFAULT_WEIGHTS
    result = copy.deepcopy(weights)
    for purpose in CANONICAL_PURPOSES:
        if purpose not in result:
            result[purpose] = copy.deepcopy(DEFAULT_WEIGHTS[purpose])
    return result


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


def _axis_norm_maps(survivors: list) -> dict[str, dict]:
    price_norm = _normalize_minmax(
        {e["key"]: e.get("pricing", {}).get("input_per_1m") for e in survivors}, invert=True)
    speed_norm = _normalize_minmax({e["key"]: e.get("tokens_per_sec") for e in survivors})
    ctx_norm = _normalize_minmax({
        e["key"]: (math.log10(w) if (w := _max_context_window(e)) else None) for e in survivors
    })
    intelligence_norm = _normalize_minmax(
        {e["key"]: e.get("scores", {}).get("intelligence_index") for e in survivors})
    coding_norm = _normalize_minmax(
        {e["key"]: e.get("scores", {}).get("coding_index") for e in survivors})
    agentic_norm = _normalize_minmax(
        {e["key"]: e.get("scores", {}).get("agentic_index") for e in survivors})
    return {
        "intelligence_index": intelligence_norm,
        "coding_index": coding_norm,
        "agentic_index": agentic_norm,
        "context_window": ctx_norm,
        "price": price_norm,
        "speed": speed_norm,
    }


def _score_one_entry(entry: dict, axis_weights: dict, norm_maps: dict, bonuses: dict) -> dict:
    tool_call = entry.get("tool_calling")
    key = entry["key"]
    axis_values = {
        "intelligence_index": norm_maps["intelligence_index"][key],
        "coding_index": norm_maps["coding_index"][key],
        "agentic_index": norm_maps["agentic_index"][key],
        "tool_calling": 100.0 if tool_call is True else (0.0 if tool_call is False else None),
        "context_window": norm_maps["context_window"][key],
        "price": norm_maps["price"][key],
        "speed": norm_maps["speed"][key],
    }
    present = {a: (v if v is not None else _MISSING_AXIS_DEFAULT) for a, v in axis_values.items()}
    weight_sum = sum(axis_weights[a] for a in present)
    base = (sum(axis_weights[a] * v for a, v in present.items()) / weight_sum
            if weight_sum else 0.0)
    bonus = 0.0
    if entry.get("batch_mode"):
        bonus += bonuses["batch_mode"]
    if entry.get("fallback_quota"):
        bonus += bonuses["fallback_quota"]
    bonus = min(bonus, bonuses["bonus_cap"])
    score = min(100.0, base + bonus)
    return {**entry, "score": round(score, 1)}


def score_candidates(entries: list, purpose: str, weights: dict) -> list:
    """purpose: "planning", "general", "mechanical", "execution", "review", or aliases
    "execute" (-> execution) / "review" (-> itself). Every axis always contributes; an axis
    with no data for this candidate is scored at _MISSING_AXIS_DEFAULT (49.0, on the 0-100
    normalized scale); the weighted sum is divided by the sum of ALL the purpose's axis
    weights; and a purpose floor (if present) is checked on the candidate's RAW scores values
    before any normalization, so the 49.0 default can never satisfy a floor.
    price and context_window/speed are normalized RELATIVE TO THIS CALL'S entries (never a
    fixed global ceiling) -- price inverted (cheaper scores higher). Returns shallow copies of
    `entries`, each with an added "score" (0-100, rounded to 1 decimal), sorted descending;
    never mutates the input list/dicts. No task_affinity bonus -- see ranking-weights.toml's
    own note on why that spec-named bonus is deliberately absent from this implementation."""
    # Resolve purpose alias (e.g., "execute" -> "execution")
    canonical = resolve_purpose(purpose)
    # A hand-built legacy dict keyed "execute" keeps working via the fallback.
    axis_weights = weights[canonical] if canonical in weights else weights[purpose]

    # Apply floor filter BEFORE normalization so excluded candidates don't affect scoring
    floor = axis_weights.get(_FLOOR_KEY) or {}
    survivors = [e for e in entries if _passes_floor(e, floor)]

    norm_maps = _axis_norm_maps(survivors)
    bonuses = weights["bonuses"]
    scored = [_score_one_entry(e, axis_weights, norm_maps, bonuses) for e in survivors]
    return sorted(scored, key=lambda e: e["score"], reverse=True)
