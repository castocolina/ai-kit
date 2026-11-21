"""36 R6, D-07: the propose-lanes order. The purpose-weighted scorer orders every row;
a jev judge, when passed, re-orders the rows of one bounded window it answers confidently.
Each row names who ranked it."""

import subprocess
from typing import NamedTuple

from ai_kit_spec import jev_names, lane_pool, model_ranker
from ai_kit_spec.catalog_bands import is_num

JEV_WINDOW = 12
POOL_WINDOW = 7
ZERO_WINDOW = 5
STABLE_TOP = 0.80
NEUTRAL_LEVEL = 2
JEV_NOT_USED = "scorer: jev not used"
OUTSIDE_WINDOW = "scorer: outside the jev window"
UNKNOWN_FACTS = "scorer: tier or class unknown"
_ANSWER_REASONS = {"low": "scorer: jev gave a low answer",
                   "no answer": "scorer: jev gave no answer",
                   "timeout": "scorer: jev timed out", "old": "scorer: jev too old",
                   "error": "scorer: jev error"}
JEV_ERROR = "scorer: jev error"
EFFORT_FACT_LEVELS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")
# A judge failure falls back to the scorer; Rule 9 forbids a broad catch-all.
_JUDGE_ERRORS = (ArithmeticError, AttributeError, LookupError, OSError, RuntimeError, TypeError,
                 ValueError, subprocess.SubprocessError)


class Ranked(NamedTuple):
    row: lane_pool.Row
    score: float
    level: str | None
    top: float | None
    ranked_by: str
    reason: str
    asked: bool


def _finite(value) -> bool:
    try:
        return is_num(value)
    except (OverflowError, ValueError):
        return False


def _score_entry(row, index: int) -> dict:
    window = row.row.get("ctx_window")
    pricing = row.entry.get("pricing")
    price = pricing.get("input_per_1m") if isinstance(pricing, dict) else None
    scores = row.entry.get("scores")
    speed = row.entry.get("tokens_per_sec")
    return {**row.entry, "key": str(index),
            "runtimes": {row.runtime: {**row.row, "ctx_window": (
                window if _finite(window) and window > 0 else None)}},
            "pricing": {"input_per_1m": price} if _finite(price) else {},
            "scores": ({k: v for k, v in scores.items() if _finite(v)}
                       if isinstance(scores, dict) else {}),
            "tokens_per_sec": speed if _finite(speed) else None}


def deterministic_order(rows: list, purpose: str, weights: dict) -> list:
    ordered = sorted(rows, key=lambda r: (r.key, r.runtime))
    entries = [_score_entry(row, i) for i, row in enumerate(ordered)]
    results = model_ranker.score_candidates(entries, purpose, weights)
    pairs = [(ordered[int(result["key"])], result["score_exact"]) for result in results]
    return sorted(pairs, key=lambda pair: (-pair[1], pair[0].key, pair[0].runtime))


def facts_summary(row) -> str:
    strengths = ", ".join(row.strengths) or "none"
    efforts = ", ".join(e for e in row.efforts if e in EFFORT_FACT_LEVELS) or "none"
    return (f"Facts: tier {row.tier}; class {row.klass}; cost band {row.cost_band}; "
            f"strengths {strengths}; effort levels {efforts}.")


def _window(known: list, zero_keys: set) -> list:
    chosen = known[:POOL_WINDOW]
    seen = {(row.key, row.runtime) for row, _ in chosen}
    zero = [(row, score) for row, score in known if (row.key, row.runtime) in zero_keys]
    for pair in zero[:ZERO_WINDOW]:
        if (pair[0].key, pair[0].runtime) not in seen:
            chosen.append(pair)
            seen.add((pair[0].key, pair[0].runtime))
    return chosen[:JEV_WINDOW]


def _judged(answer) -> tuple:
    if (not isinstance(answer, tuple) or len(answer) != 3 or not isinstance(answer[2], str)
            or not (answer[0] is None or isinstance(answer[0], str))):
        return NEUTRAL_LEVEL, None, None, "scorer", JEV_ERROR
    choice, top, why = answer
    if (choice in jev_names.SCORE_LEVELS and why == "" and isinstance(top, (int, float))
            and not isinstance(top, bool)):
        if top >= STABLE_TOP:
            return (jev_names.SCORE_LEVELS.index(choice), choice, top, "jev",
                    f"jev: {choice} (top {top:.2f})")
        return NEUTRAL_LEVEL, None, None, "scorer", _ANSWER_REASONS["low"]
    return (NEUTRAL_LEVEL, None, None, "scorer",
            _ANSWER_REASONS.get(why, _ANSWER_REASONS["no answer"]))


def _ranked_known(known, window, answers, judge_used):
    mapped = {(row.key, row.runtime): answer
              for (row, _), answer in zip(window, answers, strict=False)}
    asked = {(row.key, row.runtime) for row, _ in window}
    ranked = []
    for row, score in known:
        key = (row.key, row.runtime)
        if key in asked:
            level_index, level, top, source, reason = _judged(
                mapped.get(key, (None, None, "no answer")))
        else:
            level_index, level, top, source = NEUTRAL_LEVEL, None, None, "scorer"
            reason = OUTSIDE_WINDOW if judge_used else JEV_NOT_USED
        ranked.append((level_index, Ranked(row, score, level, top, source, reason, key in asked)))
    ranked.sort(key=lambda item: (-item[0], -item[1].score, item[1].row.key, item[1].row.runtime))
    return [item[1] for item in ranked]


def rank(rows: list, purpose: str, weights: dict, judge, zero_keys: set) -> list:
    scored = deterministic_order(rows, purpose, weights)
    known = [pair for pair in scored if not lane_pool.is_unknown(pair[0])]
    unknown = [pair for pair in scored if lane_pool.is_unknown(pair[0])]
    window = _window(known, zero_keys) if judge is not None else []
    answers = []
    if window:
        assert judge is not None
        try:
            answers = list(judge([(purpose, facts_summary(row)) for row, _ in window]))
        except _JUDGE_ERRORS:
            answers = [(None, None, "error")] * len(window)
    result = _ranked_known(known, window, answers, judge is not None)
    result.extend(Ranked(row, score, None, None, "scorer", UNKNOWN_FACTS, False)
                  for row, score in unknown)
    return result
