import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from typing import NamedTuple

from ai_kit_spec.cache import cache_base
from ai_kit_spec.commands import ResolvedReviewer, render_reviewer_command
from ai_kit_spec.config_io import _KNOWN_REVIEWER_FIELDS
from ai_kit_spec.execute_selection import purpose_matches
from ai_kit_spec.runner_dispatch import (
    CustomSpec,
    RunnerResult,
    RunnerSeams,
    RunnerSpec,
    run_custom_command,
    run_runner,
)

QUOTA_TTL_SECONDS = 3600                 # 1 hour: quota/context headroom is highly dynamic

NO_CONFIG_FALLBACK = ResolvedReviewer(key="session-default", model="", vendor="",
                                       runtime=None, command=None, extra={})

_DETAIL_MAX_CHARS = 300


def cache_quota_path(env: dict) -> str:
    return os.path.join(cache_base(env), "quota.json")


def _reviewer_by_key(reviewers: list, key: str) -> dict | None:
    for r in reviewers:
        if r.get("key") == key:
            return r
    return None


def to_resolved(entry: dict) -> ResolvedReviewer:
    """entry["key"] is always present here — every caller reaches this via
    _reviewer_by_key, which already filters by key. entry.get("model", "")
    tolerates a config entry that forgot to set model (never raises); an
    empty model is already a valid sentinel elsewhere in this module (see
    ResolvedReviewer's docstring) — "no override"."""
    return ResolvedReviewer(
        key=entry["key"], model=entry.get("model", ""), vendor=entry.get("vendor", ""),
        runtime=entry.get("runtime"), command=entry.get("command"),
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
        return to_resolved(entry)
    if not allow_same_vendor_fallback:
        return None
    for key in ladder:
        entry = _reviewer_by_key(reviewers, key)
        if entry is None or not _has_quota(quota, key):
            continue
        return to_resolved(entry)
    return None


def _filter_ladder_by_purpose(reviewers: list, ladder: list, purpose: str) -> tuple:
    """Ladder-key-list-shaped sibling of execute_selection.filter_by_purpose (candidate-dict
    shaped) -- same never-empty-on-curation-gap contract and the SAME matching predicate
    (purpose_matches, imported, never reimplemented here), just adapted to a different input
    shape (a plain ordered key list, not a list of candidate dicts) -- kept as its own small
    function because the shapes differ, not because the logic does. A key with no reviewer
    entry at all (should not happen given cfg_merge_reviewers' own invariants, but never raise
    on it) is treated as unset -- passes through, same as an entry that exists but omits
    `purpose`. Returns (resulting_ladder, fell_back) -- fell_back is True exactly when
    narrowing would have emptied the ladder and the unfiltered one was returned instead, so
    the caller (resolve_reviewers) never has to re-derive that from the result alone."""
    purpose_by_key = {r["key"]: r.get("purpose") for r in reviewers if "key" in r}
    matching = [k for k in ladder if purpose_matches(purpose_by_key.get(k), purpose)]
    if matching:
        return matching, False
    return list(ladder), bool(ladder)


def resolve_reviewers(config: dict, quota: dict, source_vendor: str, cross_ai: bool,
                       warn_fn=lambda msg: print(msg, file=sys.stderr)) -> list:
    """The full policy decision. Returns 1 or 2 ResolvedReviewer entries;
    dispatch mechanics are the caller's concern (review-spec/SKILL.md's
    Step 1), this only decides WHO.

    Narrows `ladder` to purpose in {"review", "both", None} first
    (2026-09-02 design, spec Section 7) -- falls back to the full ladder if
    that empties it, and calls `warn_fn` exactly once in that fallback case
    (spec Section 7: "falls back to the unfiltered ladder with a one-time
    warning") since an execute-only-curated config silently reviewing with
    the wrong ladder is a real misconfiguration worth surfacing. No warning
    when nothing was excluded (a ladder with no purpose-tagged entries at
    all, including today's every pre-migration review-spec.toml, behaves
    identically to before this change -- no fallback ever triggers for it,
    so nothing to warn about).

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
    ladder, fell_back = _filter_ladder_by_purpose(reviewers, ladder, "review")
    if fell_back:
        warn_fn("ai-kit-spec-review: no reviewer entry matches purpose='review' in the "
                "configured ladder -- falling back to the full, unfiltered ladder. Curate "
                "`purpose` on your review-spec.toml reviewer entries to fix this.")
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


def entry_reason(entry: dict) -> str | None:
    """The typed reason stored on a quota.json entry (D-13): the entry's own
    `reason` field when present; for legacy entries written before reasons
    existed, `real_error` when unavailable, None when available."""
    reason = entry.get("reason")
    if reason is not None:
        return reason
    if entry.get("available", True):
        return None
    return "real_error"


class ProbeSeams(NamedTuple):
    """The two spawn paths a probe can take, plus where its stderr lines are collected."""

    runner_fn: Callable[..., RunnerResult] = run_runner
    custom_fn: Callable[..., RunnerResult] = run_custom_command
    env_fn: Callable[[], dict] = lambda: dict(os.environ)
    print_fn: Callable[[str], None] | None = None


def _probe_spec(resolved: "ResolvedReviewer", cwd: str) -> RunnerSpec:
    extra = resolved.extra or {}
    runtime = resolved.runtime or ""
    return RunnerSpec(
        runtime, resolved.model, "review", 30, cwd=cwd,
        effort=extra.get("effort"), service_tier=extra.get("service_tier"),
        cursor_mode=extra.get("cursor_mode"),
    )


def _probe_entry(result: RunnerResult, detail: str) -> dict:
    """Available exactly when the runner or launcher reports no reason (D-13)."""
    if result.reason is None:
        return {"available": True, "checked_at": time.time(), "reason": None, "detail": ""}
    return {"available": False, "checked_at": time.time(), "reason": result.reason,
            "detail": detail[:_DETAIL_MAX_CHARS]}


class _ProbeRun(NamedTuple):
    result: RunnerResult
    detail: str


def _collecting_seams(seams: ProbeSeams, lines: list[str]) -> RunnerSeams:
    """Stderr lines land in `lines`; a caller's print_fn, when set, sees them too."""
    if seams.print_fn is None:
        return RunnerSeams(env_fn=seams.env_fn, print_fn=lines.append)

    emit = seams.print_fn
    assert emit is not None

    def _both(line: str) -> None:
        lines.append(line)
        emit(line)

    return RunnerSeams(env_fn=seams.env_fn, print_fn=_both)


def _probe_call(resolved, prompt, seams, runner_seams, cwd):
    """The one spawn: the runner for a table runtime, the launcher for a custom command."""
    if resolved.runtime:
        return seams.runner_fn(_probe_spec(resolved, cwd), prompt, runner_seams)
    argv = render_reviewer_command(resolved, prompt)
    return seams.custom_fn(CustomSpec(resolved.key, argv, [30], cwd=cwd), prompt, runner_seams)


def _run_probe(resolved: "ResolvedReviewer", prompt: str, seams: ProbeSeams) -> _ProbeRun:
    """One 30 s review probe. A private cwd keeps the runner off the caller's git work tree,
    so a large repo can never turn the probe into a git timeout (D-34)."""
    lines: list[str] = []
    cwd = tempfile.mkdtemp(prefix="aikit-probe-")
    try:
        result = _probe_call(resolved, prompt, seams, _collecting_seams(seams, lines), cwd)
    finally:
        shutil.rmtree(cwd, ignore_errors=True)
    return _ProbeRun(result, "\n".join(lines))


def probe_reviewer_quota(resolved: "ResolvedReviewer", run_fn=subprocess.run,
                         seams: ProbeSeams | None = None) -> dict:
    """A native entry (no runtime, no command) is never probed: nothing to run, and the
    session's own dispatch is not a quota this module can observe.

    A table-runtime entry runs one 30 s review through the runner; a custom entry (a command,
    no runtime) runs through the launcher with one 30 s tier. Available exactly when that call
    reports no reason. `detail` is the relayed stderr, truncated. `run_fn` stays accepted and
    unused so existing callers keep working."""
    del run_fn
    if not resolved.runtime and not resolved.command:
        return {"available": True, "checked_at": time.time(), "reason": None, "detail": ""}
    probe_prompt = "Only say: Hello world!"
    try:
        run = _run_probe(resolved, probe_prompt, seams or ProbeSeams())
    except ValueError as exc:
        return {"available": False, "checked_at": time.time(), "reason": "configuration",
                "detail": str(exc)}
    return _probe_entry(run.result, run.detail)


class _Refresh(NamedTuple):
    """A cache refresh: the config and ladder to probe, the cache to update, how old an entry
    may be, and the seams the probe spawns through."""

    config: dict
    ladder_keys: list
    existing: dict
    ttl_seconds: int
    seams: ProbeSeams | None = None


def refresh_quota_cache(config: dict, ladder_keys: list, existing: dict, ttl_seconds: int,
                         seams: ProbeSeams | None = None, **_unused) -> dict:
    """Returns an updated quota dict: probes only ladder_keys entries that
    are missing or whose last probe is older than ttl_seconds; entries
    still fresh are left untouched (no re-probe, no wasted quota-checking
    quota). `run_fn`, accepted through `_unused`, stays unused."""
    return _refresh(_Refresh(config, ladder_keys, existing, ttl_seconds, seams))


def _refresh(job: _Refresh) -> dict:
    reviewers = job.config.get("reviewers", [])
    updated = dict(job.existing)
    now = time.time()
    for key in job.ladder_keys:
        current = updated.get(key)
        if current is not None and now - current.get("checked_at", 0) < job.ttl_seconds:
            continue
        entry = _reviewer_by_key(reviewers, key)
        if entry is None:
            continue
        updated[key] = probe_reviewer_quota(to_resolved(entry), seams=job.seams)
    return updated
