"""Naming heuristics for fields no external source provides (design spec 2026-09-02, Section
3): is_router, batch_mode, and fallback_quota. All three are best-effort signals only -- the
wizard (ai-kit-spec-config Step 2.2, Task 8 of this plan) always surfaces them to the user for
confirm/correct, and a correction is written back to the catalog cache
(model_catalog.apply_heuristic_corrections); nothing here writes anything itself."""

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
