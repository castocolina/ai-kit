import os
import subprocess
import time

from ai_kit_spec.cache import cache_base
from ai_kit_spec.commands import ResolvedReviewer, render_reviewer_command
from ai_kit_spec.config_io import _KNOWN_REVIEWER_FIELDS

QUOTA_TTL_SECONDS = 3600                 # 1 hour: quota/context headroom is highly dynamic

NO_CONFIG_FALLBACK = ResolvedReviewer(key="session-default", model="", vendor="",
                                       cli=None, command=None, extra={})

_UNAVAILABLE_SIGNALS = (
    "usage limit", "quota", "rate limit", "rate_limit",
    # confirmed live against cursor-agent on a free plan: exit code is
    # already nonzero for this case, so these are belt-and-suspenders,
    # not load-bearing — kept in case a future CLI reports the same
    # class of failure (plan/entitlement gate, not a temporary limit) on
    # a zero exit code.
    "actionrequirederror", "not authenticated", "not logged in",
)
_DETAIL_MAX_CHARS = 300


def cache_quota_path(env: dict) -> str:
    return os.path.join(cache_base(env), "quota.json")


def _reviewer_by_key(reviewers: list, key: str) -> dict | None:
    for r in reviewers:
        if r.get("key") == key:
            return r
    return None


def _to_resolved(entry: dict) -> ResolvedReviewer:
    """entry["key"] is always present here — every caller reaches this via
    _reviewer_by_key, which already filters by key. entry.get("model", "")
    tolerates a config entry that forgot to set model (never raises); an
    empty model is already a valid sentinel elsewhere in this module (see
    ResolvedReviewer's docstring) — "no override"."""
    return ResolvedReviewer(
        key=entry["key"], model=entry.get("model", ""), vendor=entry.get("vendor", ""),
        cli=entry.get("cli"), command=entry.get("command"),
        extra={k: v for k, v in entry.items() if k not in _KNOWN_REVIEWER_FIELDS},
    )


def _has_quota(quota: dict, key: str) -> bool:
    """No entry -> never probed / no probe support for this CLI yet ->
    assume available (never block a review on the ABSENCE of quota data)."""
    entry = quota.get(key)
    if entry is None:
        return True
    return entry.get("available", True)


def resolve_ladder_pick(reviewers: list, ladder: list, skip_vendor: str, quota: dict,
                         allow_same_vendor_fallback: bool = True) -> ResolvedReviewer | None:
    """First ladder entry that (a) exists in `reviewers`, (b) has a
    different vendor than skip_vendor (empty skip_vendor disables this
    filter — used for "best overall, any vendor"), and (c) has quota. If
    nothing survives both filters and `allow_same_vendor_fallback` is True
    (the default), retry ignoring the vendor filter (same-vendor coverage
    beats no reviewer at all) — this is `single` mode's behavior, and
    `double` mode's PRIMARY slot (whose `skip_vendor` is always `""`
    anyway, so the fallback never actually triggers there). None only if
    every candidate lacks quota or doesn't exist.

    Pass `allow_same_vendor_fallback=False` for `double` mode's SECONDARY
    slot specifically: the design's guarantee for that slot is "a
    cross-vendor alternate, dropped (not substituted) if none survives" —
    silently degrading to a same-vendor pick there would run two
    same-vendor reviewers under a "double review" banner while billing a
    second CLI call for zero independent perspective.

    This is where tier-awareness comes from: a caller passing an ordered
    ladder like ["claude-opus", "claude-sonnet", ...] gets the flagship
    tier whenever it has quota, and falls through to the next configured
    tier automatically otherwise — no separate "tier" concept needed."""
    for key in ladder:
        entry = _reviewer_by_key(reviewers, key)
        if entry is None or not _has_quota(quota, key):
            continue
        if skip_vendor and entry.get("vendor") == skip_vendor:
            continue
        return _to_resolved(entry)
    if not allow_same_vendor_fallback:
        return None
    for key in ladder:
        entry = _reviewer_by_key(reviewers, key)
        if entry is None or not _has_quota(quota, key):
            continue
        return _to_resolved(entry)
    return None


def resolve_reviewers(config: dict, quota: dict, source_vendor: str, cross_ai: bool) -> list:
    """The full policy decision. Returns 1 or 2 ResolvedReviewer entries;
    dispatch mechanics are the caller's concern (review-spec/SKILL.md's
    Step 1), this only decides WHO.

    single: one reviewer, preferring a vendor different from source_vendor
    (independent perspective on the document), quota-aware, tier-aware via
    ladder order.

    double: `primary` walks the FULL ladder in order, any vendor, native or
    external alike — the user's configured ladder position is the sole
    priority signal, never overridden by a native-precedence rule. Falls
    back to NO_CONFIG_FALLBACK only when nothing in the ladder has quota
    (or the ladder is empty). CHANGED 2026-08-29 (explicit user request,
    superseding docs/superpowers/specs/2026-08-27-review-spec-cross-ai-
    design.md §3's "native reviewer runs unconditionally as the guaranteed
    baseline" rule): a native entry (e.g. the current session's own tier)
    is no longer forced to primary regardless of its ladder position —
    live-observed real-world case that prompted this change: a ladder
    ordered [external-A, external-B, native] with mode="double" was
    silently reordered to seat native as primary and external-A as
    secondary, permanently starving external-B, when the user's actual
    intent was "try A, then B, fall back to native only if both lack
    quota." `secondary` is the best entry anywhere in the FULL ladder with
    a vendor DIFFERENT from primary's — or, when primary is
    NO_CONFIG_FALLBACK (whose vendor is unknown, `""`), different from
    `source_vendor` instead, since an unknown-vendor filter is no filter
    at all and would defeat the cross-vendor guarantee exactly when
    nothing in the ladder has quota — dropped (not substituted) if none
    survives (an all-same-vendor ladder degrades to a single reviewer,
    not an error).

    Either mode falls back to NO_CONFIG_FALLBACK when --no-cross-ai was
    passed, the ladder is empty, or nothing in it has quota."""
    if not cross_ai:
        return [NO_CONFIG_FALLBACK]
    policy = config.get("policy", {})
    mode = policy.get("mode", "single")
    ladder = policy.get("ladder", [])
    reviewers = config.get("reviewers", [])
    if mode == "double":
        primary = resolve_ladder_pick(reviewers, ladder, skip_vendor="", quota=quota)
        if primary is None:
            primary = NO_CONFIG_FALLBACK
        secondary_skip_vendor = primary.vendor or source_vendor
        secondary = resolve_ladder_pick(
            reviewers, ladder, skip_vendor=secondary_skip_vendor, quota=quota,
            allow_same_vendor_fallback=False,
        )
        if secondary is None or secondary.key == primary.key:
            return [primary]
        return [primary, secondary]
    pick = resolve_ladder_pick(reviewers, ladder, skip_vendor=source_vendor, quota=quota)
    return [pick] if pick else [NO_CONFIG_FALLBACK]


def probe_reviewer_quota(resolved: "ResolvedReviewer", run_fn=subprocess.run) -> dict:
    """Native (cli-less) entries are never probed — there is nothing to
    shell out to, and dispatch mechanics there are the current session's
    own concern, not a quota this module can observe. For CLI entries: run
    a trivial prompt through the reviewer's own command and classify
    availability generically — a nonzero exit code, or stdout/stderr
    containing a case-insensitive usage/quota/rate-limit phrase, means
    unavailable; anything else (including plain success) means available.
    This generic heuristic is what makes the confirmed codex usage-limit
    error (see skills/review-spec/references/cli-profiles/codex.md) detectable
    without a CLI-specific parser. A `cli`-set entry with a missing or
    malformed `command` template is deliberately classified `available:
    False` here rather than skipped/True — it can never actually be
    dispatched, so reporting it as available would let a broken config
    entry win the ladder walk and fail later, in real dispatch, instead
    of here where the failure is cheap and diagnosable.

    `detail` (always present) carries the reviewer's own combined
    stdout+stderr, truncated to `_DETAIL_MAX_CHARS`, when unavailable —
    e.g. "ActionRequiredError: Named models unavailable. Free plans can
    only use Auto." (confirmed live against cursor-agent). Empty string
    when available or native (nothing to report). This is diagnostic
    only — `available` is still the sole signal callers act on; `detail`
    exists so a human (review-spec-config's setup wizard, or anyone
    reading quota.json) can see *why* without re-running the probe by
    hand.

    The probe prompt is always piped via stdin (`input=`), never inlined
    as a shell argument — confirmed live against every known-CLI builder
    (codex/claude/opencode/cursor-agent all read a missing prompt from
    stdin; see each `_build_*_command`'s docstring). This is
    unconditional, not gated on whether `resolved.command` happens to
    still contain a literal `{prompt}` (grok's builder, and any
    hand-written open-hatch command, still can) — an unread stdin pipe is
    harmless to a CLI that takes its prompt inline instead, so one code
    path serves both without the caller needing to introspect the
    template first."""
    if not resolved.cli:
        return {"available": True, "checked_at": time.time(), "detail": ""}
    probe_prompt = "Only say: Hello world!"
    try:
        filled = render_reviewer_command(resolved, probe_prompt)
    except ValueError as exc:
        return {"available": False, "checked_at": time.time(), "detail": str(exc)}
    try:
        result = run_fn(filled, shell=True, input=probe_prompt, capture_output=True,
                         text=True, check=False, timeout=30)
    except subprocess.TimeoutExpired:
        return {"available": False, "checked_at": time.time(),
                "detail": "timed out after 30s"}
    except OSError as exc:
        return {"available": False, "checked_at": time.time(), "detail": str(exc)}
    combined = (result.stdout + result.stderr).strip()
    if result.returncode != 0 or any(s in combined.lower() for s in _UNAVAILABLE_SIGNALS):
        return {"available": False, "checked_at": time.time(),
                "detail": combined[:_DETAIL_MAX_CHARS]}
    return {"available": True, "checked_at": time.time(), "detail": ""}


def refresh_quota_cache(config: dict, ladder_keys: list, existing: dict, ttl_seconds: int,
                         run_fn=subprocess.run) -> dict:
    """Returns an updated quota dict: probes only ladder_keys entries that
    are missing or whose last probe is older than ttl_seconds; entries
    still fresh are left untouched (no re-probe, no wasted quota-checking
    quota)."""
    reviewers = config.get("reviewers", [])
    updated = dict(existing)
    now = time.time()
    for key in ladder_keys:
        current = updated.get(key)
        if current is not None and now - current.get("checked_at", 0) < ttl_seconds:
            continue
        entry = _reviewer_by_key(reviewers, key)
        if entry is None:
            continue
        updated[key] = probe_reviewer_quota(_to_resolved(entry), run_fn=run_fn)
    return updated
