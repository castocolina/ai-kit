"""Pure Cursor quota normalization and state logic.

This module is the only module that will touch the network or a credential (in later
increments); networking imports belong inside functions only.
"""
# pyright: strict

import math
from typing import NamedTuple, cast

# ═══ 1. DEFAULTS — cache and Dashboard constants ═══
FRESH_TTL_S = 120
NEGATIVE_TTL_S = 600
UNLIMITED_HARD_LIMIT = 2147483647
WEEK_MS = 7 * 86400 * 1000


class QuotaResult(NamedTuple):
    state: str
    confidence: str
    diagnostic: str
    fetched_at: float | None
    cycle_start_ms: int | None
    cycle_end_ms: int | None
    included_pct: float | None
    api_pct: float | None
    included_window: tuple[int, int] | None
    od_kind: str
    od_used_usd: float | None
    od_ceiling_usd: float | None


# ═══ 2. UTIL — pure parsing helpers ═══
def util_pick(obj: object, camel: str, snake: str) -> object:
    """Pick the camelCase Dashboard key, falling back to snake_case."""
    if not isinstance(obj, dict):
        return None
    mapping = cast(dict[str, object], obj)
    return mapping.get(camel, mapping.get(snake))


def util_number(value: object) -> float | None:
    """Return a finite, nonnegative number without treating bool as numeric."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    if number < 0 or not math.isfinite(number):
        return None
    return number


def util_epoch_ms(value: object) -> int | None:
    number = util_number(value)
    return int(number) if number is not None else None


def util_object(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def util_spend(value: object) -> float | None:
    number = util_number(value)
    return number / 100 if number is not None else None


def util_percent(value: object) -> float | None:
    number = util_number(value)
    return number if number is not None and number <= 100 else None


# ═══ 3. CORE — normalization and cache state ═══
def util_spend_fields(
    spend: dict[str, object]
) -> tuple[float, float | None, float, float, bool]:
    raw_used = util_pick(spend, "individualUsed", "individual_used")
    used = util_spend(raw_used) if raw_used is not None else 0.0
    raw_limit = util_pick(spend, "individualLimit", "individual_limit")
    individual = util_spend(raw_limit)
    if raw_limit is None:
        individual = 0.0
    pooled_raw = util_pick(spend, "pooledUsed", "pooled_used")
    pooled = util_spend(pooled_raw) if pooled_raw is not None else 0.0
    pooled_raw_limit = util_pick(spend, "pooledLimit", "pooled_limit")
    pooled_limit = util_spend(pooled_raw_limit) if pooled_raw_limit is not None else 0.0
    team = util_pick(spend, "limitType", "limit_type") == "team"
    return cast(float, used), individual, cast(float, pooled), cast(float, pooled_limit), team


def util_on_demand(
    spend: dict[str, object], evidence: object
) -> tuple[str, float | None, float | None]:
    """Classify personal/team spend using available hard-limit evidence."""
    used, individual, pooled, pooled_limit, team = util_spend_fields(spend)
    hard = util_object(evidence)
    hard_value = util_number(util_pick(hard, "hardLimit", "hard_limit"))
    disabled = util_pick(hard, "noUsageBasedAllowed", "no_usage_based_allowed") is True
    kind, ceiling, selected_used = "unavailable", None, None
    if individual is not None and individual > 0:
        kind, ceiling, selected_used = "fixed", individual, used
    elif not team and individual == 0:
        kind, selected_used = "disabled", used
    elif evidence is not None and disabled:
        kind, selected_used = "disabled", pooled if team else used
    elif evidence is not None and hard_value is not None and hard_value >= UNLIMITED_HARD_LIMIT:
        kind, selected_used = "unlimited", pooled if team else used
    elif team and evidence is not None and hard_value is not None and hard_value > 0:
        if pooled_limit > 0:
            kind, ceiling, selected_used = "fixed", pooled_limit, pooled
    elif evidence is not None and hard_value is not None and hard_value > 0:
        kind, ceiling, selected_used = "fixed", hard_value, used
    return kind, selected_used, ceiling


def util_cycle(usage: dict[str, object], plan: dict[str, object]) -> tuple[int | None, int | None]:
    start = util_epoch_ms(util_pick(usage, "billingCycleStart", "billing_cycle_start"))
    end = util_epoch_ms(util_pick(usage, "billingCycleEnd", "billing_cycle_end"))
    if end is None:
        end = util_epoch_ms(util_pick(plan, "billingCycleEnd", "billing_cycle_end"))
    return start, end


def util_included(plan_usage: dict[str, object]) -> tuple[float | None, float | None]:
    limit = util_spend(util_pick(plan_usage, "limit", "limit"))
    included = util_spend(util_pick(plan_usage, "includedSpend", "included_spend"))
    included_pct = util_percent(util_pick(plan_usage, "totalPercentUsed", "total_percent_used"))
    if included_pct is None and included is not None and limit is not None and limit > 0:
        included_pct = included / limit * 100
    api_pct = util_percent(util_pick(plan_usage, "apiPercentUsed", "api_percent_used"))
    return included_pct, api_pct


def util_plan_window(plan: dict[str, object]) -> tuple[str | None, int | None]:
    period = util_pick(plan, "includedUsagePeriod", "included_usage_period")
    resets = util_epoch_ms(util_pick(plan, "includedUsageResetsAt", "included_usage_resets_at"))
    return (period.lower() if isinstance(period, str) else None), resets


def core_normalize(usage: object, hard_limit: object, plan_info: object) -> dict[str, object]:
    """Normalize Dashboard responses into token-free, derived quota data."""
    usage_obj = util_object(usage)
    plan_obj = util_object(util_pick(plan_info, "planInfo", "plan_info"))
    plan_usage = util_object(util_pick(usage_obj, "planUsage", "plan_usage"))
    spend_usage = util_object(util_pick(usage_obj, "spendLimitUsage", "spend_limit_usage"))
    start, end = util_cycle(usage_obj, plan_obj)
    included_pct, api_pct = util_included(plan_usage)
    od_kind, od_used, od_ceiling = util_on_demand(spend_usage, hard_limit)
    window = util_plan_window(plan_obj)
    return {
        "cycle_start_ms": start, "cycle_end_ms": end, "included_pct": included_pct,
        "api_pct": api_pct, "included_period": window[0],
        "included_resets_at_ms": window[1], "od_kind": od_kind,
        "od_used_usd": od_used, "od_ceiling_usd": od_ceiling,
        "plan_usage": bool(plan_usage),
    }


def core_included_window(data: dict[str, object]) -> tuple[int, int] | None:
    start, end = data.get("cycle_start_ms"), data.get("cycle_end_ms")
    if data.get("included_period") == "weekly":
        resets = data.get("included_resets_at_ms")
        return (resets - WEEK_MS, resets) if isinstance(resets, int) else None
    if isinstance(start, (int, float)) and isinstance(end, (int, float)):
        return (int(start), int(end))
    return None


def core_quota_state(cache: object, now: float) -> QuotaResult:
    """Derive visibility and freshness from a cache snapshot and clock."""
    value = util_object(cache)
    data = util_object(value.get("data")) if isinstance(value.get("data"), dict) else None
    fetched = util_number(value.get("data_fetched_at"))
    last_attempt = util_number(value.get("last_attempt_at"))
    error_kind = value.get("last_error_kind")
    if data is None:
        state = str(error_kind) if error_kind in {"auth_expired", "auth_unsupported"} else (
            "network_error" if error_kind == "network_error" else "absent")
        return QuotaResult(state, "inferred", str(value.get("last_error") or ""), None,
                           None, None, None, None, None, "unavailable", None, None)
    start = data.get("cycle_start_ms")
    end = data.get("cycle_end_ms")
    if isinstance(end, int) and now * 1000 >= end:
        state = "cycle_ended"
    elif error_kind in {"auth_expired", "auth_unsupported"} and (
            last_attempt is not None and (fetched is None or last_attempt > fetched)):
        state = str(error_kind)
    elif error_kind == "network_error":
        state = "stale"
    elif fetched is not None and now - fetched <= FRESH_TTL_S:
        state = "ok"
    else:
        state = "stale"
    return QuotaResult(
        state, "inferred", str(value.get("last_error") or ""), fetched,
        int(start) if isinstance(start, (int, float)) else None,
        int(end) if isinstance(end, (int, float)) else None,
        cast(float, data["included_pct"])
        if isinstance(data.get("included_pct"), (int, float)) else None,
        cast(float, data["api_pct"])
        if isinstance(data.get("api_pct"), (int, float)) else None,
        core_included_window(data), str(data.get("od_kind", "unavailable")),
        cast(float, data["od_used_usd"])
        if isinstance(data.get("od_used_usd"), (int, float)) else None,
        cast(float, data["od_ceiling_usd"])
        if isinstance(data.get("od_ceiling_usd"), (int, float)) else None,
    )


def core_needs_refresh(cache: object, now: float) -> bool:
    value = util_object(cache)
    fetched = util_number(value.get("data_fetched_at"))
    if fetched is not None and now - fetched <= FRESH_TTL_S:
        return False
    attempted = util_number(value.get("last_attempt_at"))
    return attempted is None or now - attempted >= NEGATIVE_TTL_S


def core_synthetic_cache(now: float) -> dict[str, object]:
    """Return fresh, token-free mid-cycle cache data for previews."""
    end = int((now + 86400) * 1000)
    data: dict[str, object] = {
        "cycle_start_ms": end - 30 * 86400 * 1000, "cycle_end_ms": end,
        "included_pct": 42.0, "api_pct": 18.0, "included_period": "monthly",
        "included_resets_at_ms": None, "od_kind": "fixed", "od_used_usd": 2.5,
        "od_ceiling_usd": 20.0, "plan_usage": True,
    }
    return {"data": data, "data_fetched_at": now, "last_attempt_at": now,
            "last_error": None, "last_error_kind": None}
