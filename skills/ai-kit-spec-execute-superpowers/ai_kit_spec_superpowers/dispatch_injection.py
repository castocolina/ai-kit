"""Live-quota-aware candidate resolution and the real dispatch wrapper for
ai-kit-spec-execute-superpowers. Never bypasses subagent-driven-development (design spec Section
8; superpowers:executing-plans is out of scope -- see Global Constraints) -- build_dispatch_
injection's output is an INPUT to that harness's own "Dispatch the implementer" step, not a
replacement for it, and dispatch_superpowers_task is the ONLY place an external_cli injection
actually runs a subprocess -- always through the existing, live-verified
ai_kit_spec.execute_dispatch.dispatch_execute path, never a second supervisor and
never a target_dir placeholder baked in ahead of the real dispatch call (HIGH finding)."""
import os
import re
import sys
from collections.abc import Callable, Mapping
from typing import Any, NamedTuple

from ai_kit_spec.config_io import cfg_resolve
from ai_kit_spec.execute_dispatch import ExecuteDispatchSpec, dispatch_execute
from ai_kit_spec.execute_selection import (
    ExecuteResolveOptions,
    candidates_to_ladder,
    resolve_execute_candidates,
    screen_execute_clis,
)
from ai_kit_spec.quota import entry_reason, resolve_ladder_pick
from ai_kit_spec.routing import (
    SKIP_ROUTES,
    Inventory,
    RouteInput,
    route,
    skip_note,
    unverified_note,
)

from ai_kit_spec_superpowers.task_classification import (
    classify_task,
    estimate_required_context,
    extract_touched_paths,
)


class BuildInjectionSeams(NamedTuple):
    resolve_ladder_pick_fn: Callable[..., Any] = resolve_ladder_pick


class BuildInjectionRequest(NamedTuple):
    task_markdown: str
    candidates: list
    files_touched_sizes: dict
    affinity_table: dict
    top_n_keys: list


class BuildInjectionOptions(NamedTuple):
    quota: dict | None = None
    seams: BuildInjectionSeams = BuildInjectionSeams()
    routes: Mapping[str, str] | None = None


class DispatchTaskRequest(NamedTuple):
    injection: dict
    prompt: str
    target_dir: str
    timeout: int


class SuperpowersDispatchGuidance(NamedTuple):
    format_block: str | None = None
    tool_availability: dict | None = None
    agents_tooling_path: str | None = None
    codegraph_registered: bool = False


class SuperpowersDispatchSeams(NamedTuple):
    dispatch_execute_fn: Callable[..., dict] = dispatch_execute


def reasons_summary(reasons: dict) -> dict:
    """Computes `all_auth_failures`/`any_quota_recoverable` over an ARBITRARY reasons dict --
    shared by QuotaExhaustedError's own properties (below, over `self.reasons`) and by cli.py's
    `resolve-injection` (CRITICAL finding, recurrence guard: a mid-dispatch re-resolution call's
    own QuotaExhaustedError only carries the tried/reasons IT visited this round; a candidate
    excluded earlier in the SAME wave -- via `--exclude-keys-json`, before this call's ladder walk
    even started -- never appears there at all, so a caller computing recoverability from `exc.
    reasons` alone silently drops every earlier wave-tried candidate's own reason. cli.py merges
    those earlier reasons in first (a new `--excluded-reasons-json` input) and recomputes the
    summary over the MERGED dict via this same function, so `any_quota_recoverable` reflects the
    whole wave, never just this call's own narrower remaining-ladder walk)."""
    return {
        "all_auth_failures": bool(reasons) and all(r == "auth" for r in reasons.values()),
        "any_quota_recoverable": any(r == "quota" for r in reasons.values()),
    }


class QuotaExhaustedError(RuntimeError):
    """Every candidate in the resolved ladder was quota-exhausted or had no usable dispatch
    mechanism for this task. `tried` carries every candidate key the walk actually visited, in
    ladder order, so a caller can persist the complete excluded set verbatim into resumable state
    (design spec Section 10, HIGH finding) -- never a bare string a caller has to re-parse.
    `reasons` maps each tried key to why it was skipped -- a typed reason from
    ai_kit_spec.error_classifier.REASONS (quota/auth/timeout/configuration/dispatch_unavailable/
    real_error -- the one shared, stderr-and-exit-status-only classifier, D-13; HIGH finding:
    a real probe/dispatch failure has more shapes than "quota" vs "auth", and only one of them is
    ever worth an hourly wait), PLUS one superpowers-local reason:
      - "quota": a genuine, time-bound rate/usage-limit signal -- worth the hourly wake.
      - "auth": an authentication/entitlement/setup problem -- never fixed by waiting.
      - "timeout": the probe itself hung/timed out -- a broken invocation, not a rate limit.
      - "configuration": a missing/malformed command template -- a config problem.
      - "dispatch_unavailable": the CLI binary itself could not be invoked (OSError).
      - a route name (bad_model, review_only, not_installed, no_inventory, unknown_runtime,
        no_model): the per-call route walk skipped this candidate. Permanent, like every reason
        below except "quota" -- waiting never changes which host this process runs on or which
        model a runtime lists.
      - "real_error": anything else -- a real, non-time-bound failure (a bad model id, an
        unrelated nonzero exit) that must never be mistaken for a recoverable quota wait.
    `all_auth_failures` is True only when every entry in `reasons` is "auth" (kept for the
    original stop-and-ask-about-setup signal). `any_quota_recoverable` is the general HIGH-finding
    gate a caller now uses instead: True only when at least one entry in `reasons` is "quota" --
    the ONLY case where scheduling an hourly CronCreate wake accomplishes anything. If it's False,
    EVERY tried candidate failed for a reason waiting never fixes, and the caller must stop and
    report the real problem(s) instead of scheduling a futile wake."""

    def __init__(self, task_type, tried: list, reasons: dict | None = None):
        self.task_type = task_type
        self.tried = tried
        self.reasons = reasons or {}
        super().__init__(
            f"every resolved candidate for task_type={task_type!r} is unusable "
            f"(tried: {tried!r}, reasons: {self.reasons!r}) -- caller must persist resumable "
            f"state and, only if any_quota_recoverable, schedule a CronCreate quota re-check "
            f"rather than retry immediately"
        )

    @property
    def all_auth_failures(self) -> bool:
        return reasons_summary(self.reasons)["all_auth_failures"]

    @property
    def any_quota_recoverable(self) -> bool:
        """HIGH finding: the real gate for scheduling an hourly CronCreate wake. True only if at
        least one tried candidate's reason is "quota" -- a genuine, time-bound rate/usage limit.
        Every other reason (auth/timeout/configuration/dispatch_unavailable/real_error, and
        every route name the walk records) never improves by waiting; if NONE of `reasons` is
        "quota", waiting an hour
        fixes nothing for any candidate, and the caller must stop and report the real problem(s)
        instead. Delegates to the shared reasons_summary (above) -- see its own docstring for why
        a caller merging reasons across more than one resolve-injection call must recompute this
        SAME summary over the merged dict rather than trust one call's own `.reasons` alone."""
        return reasons_summary(self.reasons)["any_quota_recoverable"]


def compute_resume_exclusions(tried: list, reasons: dict, prior_excluded_keys: list) -> list:
    """CRITICAL finding (recurrence guard): a persisted resumable-state `excluded_keys` set must
    NEVER permanently exclude a candidate whose only failure reason was "quota" -- once
    permanently excluded, a candidate can NEVER be retried again, even after quota genuinely
    recovers, which defeats the entire purpose of the hourly CronCreate wake this same exhaustion
    event schedules. This function is the single place that decides what belongs in a PERSISTED
    exclusion set: `prior_excluded_keys` (already permanent, carried forward unchanged) plus every
    key in `tried` whose reason is NOT "quota" (auth/timeout/configuration/dispatch_unavailable/
    real_error, or a route name -- genuinely permanent, by construction of QuotaExhaustedError's
    own typed reasons above). A "quota" reason is deliberately DROPPED from the returned set, so
    the next resolve-injection call -- which always refreshes quota fresh -- gets a real chance to
    see that candidate recovered. Returns a sorted list (deterministic for a caller diffing/
    persisting it)."""
    permanent_new = {k for k in tried if reasons.get(k) != "quota"}
    return sorted(set(prior_excluded_keys) | permanent_new)


def assemble_candidates(cwd: str, env: dict, cfg_resolve_fn=cfg_resolve) -> tuple:
    """Reads the SAME shared candidate roster ai_kit_spec_gsd.adapter.assemble_candidates reads
    (review-spec.toml's [[reviewers]], design spec Section 4) -- the "superpowers has no config
    surface" constraint (Global Constraints) is about a superpowers-specific config file like
    GSD's .planning/config.json, which genuinely doesn't exist; it is not about this shared
    roster, which every ai-kit-spec-execute-* adapter reads identically. Duplicated here (not
    imported from ai_kit_spec_gsd.adapter) to keep the two sibling adapters independent -- neither
    should import the other's package. `task_affinity`/`context_limit`/`purpose` come back `None`
    for a pre-2026-09-02 ai-kit-spec-config output (Global Constraints) -- `.get()`, never
    `KeyError`."""
    resolved = cfg_resolve_fn(cwd, env)
    candidates = []
    for r in resolved.get("reviewers", []):
        if "key" not in r:
            continue
        candidates.append({
            "key": r["key"], "model": r.get("model", ""),
            "runtime": r.get("runtime"),
            "vendor": r.get("vendor", ""), "command": r.get("command"),
            "task_affinity": r.get("task_affinity"), "context_limit": r.get("context_limit"),
            "purpose": r.get("purpose"),
            "effort": r.get("effort"), "service_tier": r.get("service_tier"),
        })
    top_n_keys = resolved.get("policy", {}).get("ladder", [])
    return candidates, top_n_keys


_LINE_QUALIFIER = re.compile(r":\d+(?:-\d+)?$")


def _strip_line_qualifier(path: str) -> str:
    """CRITICAL finding: writing-plans' own standard task template (this plan's own Task
    Structure, `Modify: existing.py:123-145`) qualifies a Modify: path with a trailing line
    range -- that suffix is never part of a real filesystem path. Strips a trailing `:N` or
    `:N-M` ONLY for the purpose of resolving a real file on disk; the caller (derive_files_
    touched_sizes) keeps using the RAW, unstripped string as its own dict key, since
    estimate_required_context looks sizes up by extract_touched_paths' own raw output."""
    return _LINE_QUALIFIER.sub("", path)


def derive_files_touched_sizes(task_markdown: str, cwd: str, isfile_fn=os.path.isfile,
                                getsize_fn=os.path.getsize) -> dict:
    """The real {path: byte_size} map estimate_required_context needs (CRITICAL finding: context-
    size input was never populated end-to-end). Every path task_classification.extract_touched_
    paths finds is normalized via _strip_line_qualifier (CRITICAL finding: a writing-plans-style
    `existing.py:123-145` Modify: target never resolves to a real file without this -- isfile()
    on the raw, colon-suffixed string is always False, so every real Modify: target silently
    contributed 0 bytes and context-size filtering was inert for the framework's own standard
    task shape) before being joined against cwd and stat'd; a path that doesn't exist yet (a
    Create: target, which is never line-qualified in the first place) contributes 0 -- matches
    estimate_required_context's own "missing size counts as zero, never an error" contract
    exactly. The dict KEY returned is always the RAW (un-normalized) path, matching extract_
    touched_paths' own output verbatim -- only the on-disk lookup is normalized."""
    sizes = {}
    for path in extract_touched_paths(task_markdown):
        full_path = os.path.join(cwd, _strip_line_qualifier(path))
        sizes[path] = getsize_fn(full_path) if isfile_fn(full_path) else 0
    return sizes


def _unavailability_reason(quota: dict, key: str) -> str:
    """Why a quota-unavailable candidate is unavailable: the TYPED `reason` the shared
    classifier (ai_kit_spec.error_classifier, D-13) already stored on the quota.json entry
    at probe time -- never a re-parse of the human-readable `detail` text. A legacy entry
    written before reasons existed reads "real_error" (never "quota" -- a false "quota"
    here would wrongly schedule an hourly CronCreate wake for a failure that will never
    improve by waiting, exactly the bug the HIGH finding closed)."""
    return entry_reason(quota.get(key) or {}) or "real_error"


def _route_of(candidate: dict, routes: Mapping[str, str]) -> str:
    """The candidate's route. A missing mapping fails closed: an unknown host and an empty
    inventory, so only the session default (no runtime, no model) is dispatchable. A runtime-less
    candidate that still names a model is the pre-routing native shape; it stays the session
    default rather than becoming an unknown runtime."""
    key = candidate["key"]
    if key in routes:
        return routes[key]
    runtime = candidate.get("runtime")
    model = "" if runtime is None and not candidate.get("command") else candidate.get("model", "")
    return route(RouteInput(runtime, model, candidate.get("command")),
                 "unknown", "exec", Inventory(frozenset(), {}))


def _screen_exempt(routes: Mapping[str, str]):
    """D-15 screen order: only an explicit purpose="execute" choice is screened before the walk.
    A native route needs no execute builder, and every other candidate's skip is the walk's."""
    return lambda candidate: (
        candidate.get("purpose") != "execute" or _route_of(candidate, routes) == "native"
    )


def _narrow_and_rank(request: BuildInjectionRequest, routes: Mapping[str, str]) -> tuple:
    """Shared by build_dispatch_injection and compute_ladder_keys (CRITICAL finding: the two
    must never compute the narrowed/ranked candidate order via two independently-drifting code
    paths) -- classifies the task, estimates required context, and narrows+ranks via
    resolve_execute_candidates. Returns (task_type, required_context, ranked)."""
    task_type = classify_task(request.task_markdown)
    required_context = estimate_required_context(
        request.task_markdown, request.files_touched_sizes)
    ranked = resolve_execute_candidates(
        request.candidates,
        ExecuteResolveOptions(
            task_type, required_context, request.affinity_table, request.top_n_keys,
            warn_fn=lambda msg: print(msg, file=sys.stderr),
            screen_exempt_fn=_screen_exempt(routes),
        ),
    )
    return task_type, required_context, ranked


def compute_ladder_keys(request: BuildInjectionRequest, routes=None) -> list:
    """CRITICAL finding (Rounds 4-5 capability escalation): the FULL ordered candidate-key list
    -- via the SAME narrowing/ranking build_dispatch_injection itself walks (_narrow_and_rank,
    above) -- turned into keys via candidates_to_ladder. Deliberately NOT `list(top_n_keys)`: a
    candidate ranked here but absent from `top_n_keys` (policy.ladder's own configured keys)
    still gets a real, ordered (last-ranked) position, so a caller computing "every candidate
    ranked strictly above the stuck one" (Task 4's SKILL.md escalation rule) never silently misses
    an out-of-ladder candidate the live walk could actually have picked.

    Bundled into a request so the routes mapping fits the argument limit. The pre-screen stays
    silent: resolve-injection runs build_dispatch_injection right after, which emits the same
    D-15 skip warnings once (A-IN-06). A purpose="execute" error still raises."""
    screened = screen_execute_clis(
        request.candidates, lambda _msg: None, _screen_exempt(routes or {}))
    _, _, ranked = _narrow_and_rank(request._replace(candidates=screened), routes or {})
    return candidates_to_ladder(ranked)


def _injection_for(candidate: dict, decision: str) -> dict:
    """The host-agnostic payload. `unverified` still dispatches: the model list was unavailable,
    so neither side could check the model before it runs."""
    if decision == "unverified":
        print(unverified_note(candidate["key"], candidate.get("runtime"),
                              candidate.get("model", "")), file=sys.stderr)
    if decision == "native":
        return {"mode": "native", "key": candidate["key"], "runtime": candidate.get("runtime"),
                "model": candidate["model"]}
    return {
        "mode": "external_cli", "key": candidate["key"], "runtime": candidate.get("runtime"),
        "model": candidate["model"], "effort": candidate.get("effort"),
        "service_tier": candidate.get("service_tier"),
    }


def _record_remaining(remaining: list, quota: dict, tried: list, reasons: dict) -> None:
    for key in remaining:
        tried.append(key)
        reasons[key] = _unavailability_reason(quota, key)


def _skip_route(candidate: dict, decision: str, tried: list, reasons: dict) -> None:
    """A skip route is permanent: recorded under the route name, never picked, one stderr line."""
    tried.append(candidate["key"])
    reasons[candidate["key"]] = decision
    print(skip_note(f"{candidate['key']} for execution", decision), file=sys.stderr)


def _walk_ladder_for_injection(
    task_type, ranked: list, quota: dict, seams: BuildInjectionSeams, routes: Mapping[str, str],
) -> dict:
    """Route first, then quota. Skip routes are recorded before the pick, so a cached row can
    never hide one. Native rows are NOT dropped here: the CLI refresh already removed them, and a
    library caller that passes a quota dict means that dict to be honored."""
    by_key = {c["key"]: c for c in ranked}
    remaining = candidates_to_ladder(ranked)
    tried: list = []
    reasons: dict = {}
    for candidate in list(ranked):
        decision = _route_of(candidate, routes)
        if decision in SKIP_ROUTES:
            _skip_route(candidate, decision, tried, reasons)
            remaining = [k for k in remaining if k != candidate["key"]]
    visible = quota
    while remaining:
        pick = seams.resolve_ladder_pick_fn(ranked, remaining, skip_vendor="", quota=visible)
        if pick is None:
            break
        candidate = by_key[pick.key]
        return _injection_for(candidate, _route_of(candidate, routes))
    _record_remaining(remaining, visible, tried, reasons)
    raise QuotaExhaustedError(task_type, tried, reasons)


def build_dispatch_injection(request: BuildInjectionRequest,
                              options: BuildInjectionOptions | None = None) -> dict:
    opts = options or BuildInjectionOptions()
    routes = opts.routes or {}
    task_type, required_context, ranked = _narrow_and_rank(request, routes)
    if not ranked:
        raise ValueError(
            f"no execute candidate survived affinity/context narrowing for "
            f"task_type={task_type!r}, required_context={required_context} -- cannot build a "
            f"dispatch injection"
        )
    return _walk_ladder_for_injection(
        task_type, ranked, dict(opts.quota or {}), opts.seams, routes)


def dispatch_superpowers_task(request: DispatchTaskRequest,
                               guidance: SuperpowersDispatchGuidance | None = None,
                               seams: SuperpowersDispatchSeams | None = None) -> dict:
    """The ONLY place a mode="external_cli" injection actually runs a subprocess. `target_dir` is
    a real, caller-supplied path at the moment of dispatch -- never resolved ahead of time and
    never a placeholder string (HIGH finding). Always routes through
    ai_kit_spec.execute_dispatch.dispatch_execute, which builds the real execute-mode command,
    composes the reinforcement/tooling/soft-confinement prose, and runs it through the one
    supervision core -- this function adds no dispatch mechanics of its own."""
    if request.injection.get("mode") != "external_cli":
        raise ValueError(
            f"dispatch_superpowers_task is for mode='external_cli' injections only -- got "
            f"mode={request.injection.get('mode')!r}; a native injection dispatches via the "
            f"Agent tool directly, in-process, and never reaches this function"
        )
    guide = guidance or SuperpowersDispatchGuidance()
    seam = seams or SuperpowersDispatchSeams()
    injection = request.injection
    candidate = {"runtime": injection["runtime"], "model": injection["model"],
                 "effort": injection.get("effort"), "service_tier": injection.get("service_tier")}
    return seam.dispatch_execute_fn(
        ExecuteDispatchSpec(
            candidate,
            request.prompt,
            request.target_dir,
            request.timeout,
            format_block=guide.format_block,
            tool_availability=guide.tool_availability,
            agents_tooling_path=guide.agents_tooling_path,
            codegraph_registered=guide.codegraph_registered,
        )
    )


def classify_dispatch_failure(dispatch_result: dict) -> str:
    """Classifies a completed dispatch_superpowers_task result from the runner's own reason:
    "ok" (returncode 0), "quota" when the runner reported reason `quota` (retry with the next
    ladder candidate, never this same one), or "real_error" for anything else, including a
    timeout and every auth/entitlement/setup signal -- HIGH finding: those never get better by
    waiting, so they must never come back "quota" and trigger the caller's hourly CronCreate
    wake loop -- surfaced honestly to the harness's own BLOCKED/fix-loop path instead, design
    spec Section 12's explicit "never silently retry disguised as quota-wait" rule."""
    if dispatch_result.get("returncode", 0) == 0:
        return "ok"
    if dispatch_result.get("reason") == "quota":
        return "quota"
    return "real_error"
