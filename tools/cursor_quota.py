"""Pure Cursor quota normalization and state logic.

Networking and credential imports are intentionally lazy so rendering stays cheap.
"""
# pyright: strict

import importlib
import math
from collections.abc import Callable
from typing import Any, NamedTuple, cast

# ═══ 1. DEFAULTS — cache and Dashboard constants ═══
FRESH_TTL_S = 120
NEGATIVE_TTL_S = 600
UNLIMITED_HARD_LIMIT = 2147483647
WEEK_MS = 7 * 86400 * 1000
DEFAULT_CALL_TIMEOUT_S = 8.0


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


class FetchResult(NamedTuple):
    usage: dict[str, object] | None
    hard_limit: dict[str, object] | None
    plan_info: dict[str, object] | None
    error_kind: str | None


class FetchContext(NamedTuple):
    base: str
    token: str
    opener: Any
    deadline: float
    timeout_s: float


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
        hidden_errors = {"auth_expired", "auth_unsupported", "auth_missing"}
        state = str(error_kind) if error_kind in hidden_errors else (
            "network_error" if error_kind == "network_error" else "absent")
        return QuotaResult(state, "inferred", str(value.get("last_error") or ""), None,
                           None, None, None, None, None, "unavailable", None, None)
    start = data.get("cycle_start_ms")
    end = data.get("cycle_end_ms")
    if isinstance(end, int) and now * 1000 >= end:
        state = "cycle_ended"
    elif error_kind in {"auth_expired", "auth_unsupported", "auth_missing"} and (
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


# ═══ 4. PROBE — credentials and Dashboard transport ═══
def util_validate_endpoint(url: str) -> str | None:
    """Return a canonical approved Dashboard base URL, or None."""
    urlsplit = importlib.import_module("urllib.parse").urlsplit
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        valid_scheme = parsed.scheme.lower() == "https"
        valid_host = bool(host) and (host.lower() == "cursor.sh" or
                                     host.lower().endswith(".cursor.sh"))
        valid_credentials = parsed.username is None and parsed.password is None
        valid_port = parsed.port in (None, 443)
        valid_suffix = parsed.path in ("", "/") and not parsed.query and not parsed.fragment
        if not (valid_scheme and valid_host and valid_credentials and valid_port and valid_suffix):
            return None
        return f"https://{host.lower()}"
    except ValueError:
        return None


def probe_auth_path(env: dict[str, str], platform: str = "") -> str:
    """Resolve the CLI's read-only auth path without consulting CURSOR_CONFIG_DIR."""
    os = importlib.import_module("os")
    sys = importlib.import_module("sys")
    system = platform or sys.platform
    if system == "darwin":
        return os.path.join(env.get("HOME", os.path.expanduser("~")), ".cursor", "auth.json")
    config = env.get("XDG_CONFIG_HOME") or os.path.join(
        env.get("HOME", os.path.expanduser("~")), ".config")
    return os.path.join(config, "cursor", "auth.json")


def probe_access_token(env: dict[str, str]) -> tuple[str | None, str | None]:
    """Read only accessToken from auth.json; never expose parse or OS errors."""
    json = importlib.import_module("json")
    try:
        with open(probe_auth_path(env), encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError:
        return None, "auth_missing"
    except (OSError, ValueError):
        return None, "network_error"
    token = cast(dict[str, object], value).get("accessToken") if isinstance(value, dict) else None
    if not isinstance(token, str) or not token:
        return None, "auth_unsupported"
    return token, None


def probe_build_opener() -> Any:
    """Build a default-TLS opener which refuses every redirect."""
    request_module = importlib.import_module("urllib.request")

    class NoRedirect(request_module.HTTPRedirectHandler):
        def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    return request_module.build_opener(NoRedirect)


def probe_fetch_all(base: str, token: str, opener: Any, timeout_s: float) -> FetchResult:
    """Fetch three Dashboard methods concurrently within one body-inclusive deadline."""
    runtime = importlib.import_module
    futures_module = runtime("concurrent.futures")
    context = FetchContext(base, token, opener, runtime("time").monotonic() + timeout_s,
                          timeout_s)

    def call(method: str) -> tuple[dict[str, object] | None, str | None]:
        return probe_dashboard_call(context, method)

    methods = ("GetCurrentPeriodUsage", "GetHardLimit", "GetPlanInfo")
    by_method = probe_submit_calls(futures_module, call, methods, context.deadline)
    if by_method is None:
        return FetchResult(None, None, None, "network_error")
    usage, usage_error = by_method[methods[0]]
    hard, _ = by_method[methods[1]]
    plan, _ = by_method[methods[2]]
    if usage_error:
        return FetchResult(None, None, None, usage_error)
    return FetchResult(usage, hard, plan, None)

def probe_submit_calls(
    futures_module: Any,
    call: Callable[[str], tuple[dict[str, object] | None, str | None]],
    methods: tuple[str, ...], deadline: float
) -> dict[str, tuple[dict[str, object] | None, str | None]] | None:
    """Run method calls concurrently and bound executor wait by the shared deadline."""
    executor = futures_module.ThreadPoolExecutor(max_workers=len(methods))
    futures = {method: executor.submit(call, method) for method in methods}
    _, pending = futures_module.wait(
        futures.values(), timeout=max(0.0, deadline - importlib.import_module("time").monotonic()),
        return_when=futures_module.ALL_COMPLETED)
    if pending:
        for future in pending:
            future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        return None
    results = {method: future.result() for method, future in futures.items()}
    executor.shutdown(wait=True)
    return results


def probe_dashboard_call(
    context: FetchContext, method: str
) -> tuple[dict[str, object] | None, str | None]:
    """Issue one Dashboard POST and parse a JSON-object body before the deadline."""
    runtime = importlib.import_module
    json = runtime("json")
    time = runtime("time")
    http_error = runtime("urllib.error").HTTPError
    request_module = runtime("urllib.request")
    remaining = context.deadline - time.monotonic()
    if remaining <= 0:
        return None, "network_error"
    request = request_module.Request(
        f"{context.base}/aiserver.v1.DashboardService/{method}", data=b"{}", method="POST",
        headers={"Authorization": f"Bearer {context.token}", "Content-Type": "application/json",
                 "Connect-Protocol-Version": "1"})
    try:
        with context.opener.open(request, timeout=min(context.timeout_s, remaining)) as response:
            sock = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
            chunks: list[bytes] = []
            while True:
                remaining = context.deadline - time.monotonic()
                if remaining <= 0:
                    return None, "network_error"
                if sock is not None and sock.fileno() >= 0:
                    sock.settimeout(remaining)
                chunk = response.read(65536)
                if not chunk:
                    break
                chunks.append(chunk)
            value = json.loads(b"".join(chunks))
            return (cast(dict[str, object], value), None) if isinstance(value, dict) else (
                None, "network_error")
    except http_error as exc:
        return None, "auth_expired" if exc.code in (401, 403) else "network_error"
    except (OSError, ValueError, json.JSONDecodeError, TimeoutError):
        return None, "network_error"


def probe_fetch_quota(
    env: dict[str, str], opener: Any = None,
    fetch: Callable[[str, str, Any, float], FetchResult] = probe_fetch_all
) -> tuple[dict[str, object] | None, str | None, str]:
    """Validate before reading the token, fetch, and return only normalized data."""
    endpoint = util_validate_endpoint(env.get("CURSOR_API_ENDPOINT", "https://api2.cursor.sh"))
    if endpoint is None:
        return None, "network_error", "Dashboard endpoint rejected"
    token, error = probe_access_token(env)
    if error:
        return None, error, "Cursor authentication unavailable"
    result = fetch(endpoint, cast(str, token), opener or probe_build_opener(),
                   DEFAULT_CALL_TIMEOUT_S)
    if result.error_kind:
        return None, result.error_kind, "Cursor Dashboard request failed"
    return core_normalize(result.usage, result.hard_limit, result.plan_info), None, ""
