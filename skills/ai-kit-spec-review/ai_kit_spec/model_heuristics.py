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


# 35 D-15: the source label of the router-env alias assumption (catalog_facts writes it).
ROUTER_ALIAS_SOURCE = "router-env alias naming"


def router_statement(entry) -> bool | None:
    """38 D-17: the one confirmed-router rule.

    True for a confirmed router lane (the owner's word, or the router-env alias
    assumption), False when the owner said it is not one, None when only a heuristic
    or nothing speaks (a judged name hint stays advisory).
    """
    if not isinstance(entry, dict):
        return None
    confirmed = entry.get("heuristic_confirmed")
    owner = {f for f in confirmed if f in ("is_router", "fallback_quota")} if isinstance(
        confirmed, list
    ) else set()
    facts = entry.get("facts")
    klass = facts.get("class") if isinstance(facts, dict) else None
    klass = klass if isinstance(klass, dict) else {}
    quota, router = entry.get("fallback_quota"), entry.get("is_router")
    stated = klass.get("label") == "user-stated"
    # an explicit owner false wins over every assumption
    owner_false = ("fallback_quota" in owner and quota is False) or (
        "is_router" in owner and router is False
    )
    if owner_false or (stated and klass.get("value") != "router"):
        return False
    # unknown or disagreeing heuristic fields never confirm
    if quota is not True or router is not True:
        return None
    if owner or stated:
        return True
    if (entry.get("provider") == "router-env" and klass.get("label") == "assumed"
            and klass.get("source") == ROUTER_ALIAS_SOURCE and klass.get("value") == "router"):
        return True
    return None


def is_confirmed_router(entry) -> bool:
    """True only for a confirmed router lane (router_statement is True)."""
    return router_statement(entry) is True


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
