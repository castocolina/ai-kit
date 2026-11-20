"""35 D-04 / R4: one parser for host model names.

Effort is parsed by runtime style, known identity is kept whole, and batches resolve
with an injected judge. Pure; never calls jev itself.
"""

import difflib
import re
from typing import NamedTuple

from ai_kit_spec.model_matcher import _FUZZY_MARGIN, _FUZZY_THRESHOLD, _normalize

EFFORT_WORDS = frozenset(
    {
        "none",
        "minimal",
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
        "thinking",
        "non-thinking",
        "reasoning",
        "off",
    }
)
JUDGE_FLOOR = 0.5
# A judge choice below this confidence stays unmatched, SPEC R4. The jev adapter of plan 06
# already drops answers jev marks as not decided.
JUDGE_MIN_CONFIDENCE = 0.5

_PI_RX = re.compile(r":(off|minimal|low|medium|high|xhigh|max)$")
_OPENCODE_RX = re.compile(r"#([^#/]+)$")
_BRACKET_RX = re.compile(r"\[([^\]]*)\]$")
_DASH_RX = re.compile(r"-(non-thinking|[a-z]+)$")
_ARENA_RX = re.compile(r"\s*\(([^()]*)\)$")


class BlankNameError(ValueError):
    """Raised when a host or source supplies a blank model name."""


class NameParts(NamedTuple):
    host_id: str
    base: str
    efforts: tuple


class Resolution(NamedTuple):
    state: str
    key: str | None
    candidates: tuple
    confidence: float | None


def known_ids_from_models_dev(payload) -> frozenset:
    """Return bare and provider-qualified ids from a models.dev-shaped payload."""
    known = set()
    if not isinstance(payload, dict):
        return frozenset()
    for provider, value in payload.items():
        if (
            not isinstance(provider, str)
            or not isinstance(value, dict)
            or not isinstance(value.get("models"), dict)
        ):
            continue
        for model_id in value["models"]:
            if isinstance(model_id, str):
                known.add(model_id)
                known.add(f"{provider}/{model_id}")
    return frozenset(known)


def _suffix_parts(host_id: str, pattern: re.Pattern) -> tuple[str, tuple]:
    match = pattern.search(host_id)
    if match is None:
        return host_id, ()
    return host_id[: match.start()], (match.group(1),)


def _pi_parts(host_id: str) -> tuple[str, tuple]:
    return _suffix_parts(host_id, _PI_RX)


def _opencode_parts(host_id: str) -> tuple[str, tuple]:
    return _suffix_parts(host_id, _OPENCODE_RX)


def _cursor_parts(host_id: str) -> tuple[str, tuple]:
    base = host_id
    efforts = []
    bracket = _BRACKET_RX.search(base)
    if bracket:
        base = base[: bracket.start()]
        for item in bracket.group(1).split(","):
            key, separator, value = item.partition("=")
            value = value.strip()
            if separator and key.strip() in {"effort", "reasoning"} and value in EFFORT_WORDS:
                efforts.append(value)
    dash = _DASH_RX.search(base)
    if dash and dash.group(1) in EFFORT_WORDS:
        base = base[: dash.start()]
        efforts.append(dash.group(1))
    return base, tuple(efforts)


def _arena_parts(host_id: str) -> tuple[str, tuple]:
    match = _ARENA_RX.search(host_id)
    if match is None or match.group(1).strip().lower() not in EFFORT_WORDS:
        return host_id, ()
    return host_id[: match.start()].rstrip(), (match.group(1).strip().lower(),)


def split_effort(runtime: str, host_id: str, known_ids: frozenset = frozenset()) -> NameParts:
    """Split a recognized runtime effort marker without changing the original host id."""
    if not host_id.strip():
        raise BlankNameError("blank model name")
    bare = host_id.rsplit("/", 1)[-1]
    if host_id in known_ids or bare in known_ids:
        return NameParts(host_id, host_id, ())
    parser = {
        "pi": _pi_parts,
        "opencode": _opencode_parts,
        "cursor": _cursor_parts,
        "arena": _arena_parts,
    }.get(runtime)
    base, efforts = parser(host_id) if parser else (host_id, ())
    return NameParts(host_id, base, efforts)


def _score_candidates(name: str, pool_names, floor: float) -> list:
    normalized = _normalize(name)
    exact = sorted(candidate for candidate in pool_names if _normalize(candidate) == normalized)
    if exact:
        return exact
    scored = [
        (difflib.SequenceMatcher(None, normalized, _normalize(candidate)).ratio(), candidate)
        for candidate in pool_names
    ]
    return [
        candidate
        for ratio, candidate in sorted(scored, key=lambda row: (-row[0], row[1]))
        if ratio >= floor
    ]


def candidates(
    name: str, pool_names, limit: int | None = 5, floor: float = _FUZZY_THRESHOLD
) -> list:
    """List normalized exact matches or ranked fuzzy candidates, optionally limited."""
    found = _score_candidates(name, pool_names, floor)
    return found if limit is None else found[:limit]


def _ranked_score(name: str, candidate: str) -> float:
    return difflib.SequenceMatcher(None, _normalize(name), _normalize(candidate)).ratio()


def _deterministic_match(name: str, found: list, pool: dict) -> Resolution | None:
    exact = [candidate for candidate in found if _normalize(candidate) == _normalize(name)]
    if len(exact) == 1:
        return Resolution("matched", pool[exact[0]], tuple(found), None)
    if not exact and found:
        best = _ranked_score(name, found[0])
        runner_up = _ranked_score(name, found[1]) if len(found) > 1 else 0.0
        if len(found) == 1 or (best - runner_up >= _FUZZY_MARGIN and best != runner_up):
            return Resolution("matched", pool[found[0]], tuple(found), None)
    return None


def _judge_answer(answer, found: list, pool: dict) -> Resolution | None:
    if not isinstance(answer, tuple) or len(answer) != 3:
        return None
    choice, confidence, _reason = answer
    valid_confidence = (
        isinstance(confidence, (int, float))
        and not isinstance(confidence, bool)
        and JUDGE_MIN_CONFIDENCE <= confidence <= 1
    )
    if choice not in found[:5] or not valid_confidence:
        return None
    return Resolution("judged", pool[choice], tuple(found), float(confidence))


def resolve_many(names: list, pool: dict, judge_batch=None) -> dict:
    """Resolve names deterministically, batching only ambiguous names for an injected judge."""
    results = {}
    pending = []
    for name in names:
        found = candidates(name, pool, limit=None)
        match = _deterministic_match(name, found, pool)
        if match is not None:
            results[name] = match
            continue
        if not found:
            found = candidates(name, pool, limit=None, floor=JUDGE_FLOOR)
        results[name] = Resolution("unmatched", None, tuple(found), None)
        if found and judge_batch is not None:
            pending.append((name, found))
    if pending and judge_batch is not None:
        answers = judge_batch([(name, found[:5]) for name, found in pending])
        answers = answers if isinstance(answers, list) else []
        for index, (name, found) in enumerate(pending):
            answer = answers[index] if index < len(answers) else None
            judged = _judge_answer(answer, found, pool)
            if judged is not None:
                results[name] = judged
    return results
