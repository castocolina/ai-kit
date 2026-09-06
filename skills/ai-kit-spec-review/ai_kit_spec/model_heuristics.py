"""Naming heuristics for fields no external source provides (design spec 2026-09-02, Section
3): is_router, batch_mode, and fallback_quota. All three are best-effort signals only -- the
wizard (ai-kit-spec-config Step 2.2, Task 8 of this plan) always surfaces them to the user for
confirm/correct, and a correction is written back to the catalog cache
(model_catalog.apply_heuristic_corrections); nothing here writes anything itself."""

import re

_ROUTER_NAME_HINTS = ("router", "-env", "local-llm")
_BATCH_NAME_HINTS = ("batch", "flash", "mini", "-lite")


def infer_is_router(provider_or_key: str) -> bool:
    """E.g. a provider/key named 'router-env' self-identifies as a router."""
    lowered = provider_or_key.lower()
    return any(hint in lowered for hint in _ROUTER_NAME_HINTS)


def infer_batch_mode(model_id: str) -> bool:
    """Suffixes like -flash/-batch/-mini/-lite correlate with non-interactive/batch-suitable
    variants across vendors (observed pattern, not a guarantee)."""
    lowered = model_id.lower()
    return any(hint in lowered for hint in _BATCH_NAME_HINTS)


def infer_fallback_quota(provider_or_key: str) -> bool:
    """spec Section 3: "same inference source as is_router" -- a router entry, by definition,
    has internal multi-backend fallback. Delegates to infer_is_router rather than duplicating
    _ROUTER_NAME_HINTS, so the two heuristics can never silently drift apart."""
    return infer_is_router(provider_or_key)


_PURPOSE_NAME_HINTS = {
    "review": ("review", "plan-review"),
    "execute": ("coding", "execute"),
}


def _hint_matches(hint: str, lowered: str) -> bool:
    """Delimiter-bounded match: `hint` must not be embedded inside a larger
    alphanumeric run. Plain substring matching would let "review" fire on
    "preview" or "coding" fire on "encoding" -- both real router/gateway
    naming collisions, not purpose declarations."""
    return re.search(rf"\b{re.escape(hint)}\b", lowered) is not None


def infer_purpose_from_name(model_id: str) -> str | None:
    """Only meaningful for a candidate ALREADY confirmed as a router/gateway via
    infer_is_router -- this function does not check is_router itself (keeps the two
    heuristics independently testable/composable; every caller gates on infer_is_router
    first). Checks for an explicit, unambiguous purpose word in the id, as a
    delimiter-bounded token (never a raw substring): "review"/"plan-review" -> "review";
    "coding"/"execute" -> "execute". Returns None when neither group matches, OR when both
    do (a genuine naming contradiction must never be silently resolved by picking one) --
    callers that get None fall through to the ordinary external-matching path, exactly as
    if this heuristic didn't exist."""
    lowered = model_id.lower()
    is_review = any(_hint_matches(h, lowered) for h in _PURPOSE_NAME_HINTS["review"])
    is_execute = any(_hint_matches(h, lowered) for h in _PURPOSE_NAME_HINTS["execute"])
    if is_review == is_execute:   # neither matched, or both did (contradiction) -> None
        return None
    return "review" if is_review else "execute"
