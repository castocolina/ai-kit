"""Live-quota-aware candidate resolution and the real dispatch wrapper for
ai-kit-spec-execute-superpowers. Never bypasses subagent-driven-development (design spec Section
8; superpowers:executing-plans is out of scope -- see Global Constraints) -- build_dispatch_
injection's output is an INPUT to that harness's own "Dispatch the implementer" step, not a
replacement for it, and dispatch_superpowers_task is the ONLY place an external_cli injection
actually runs a subprocess -- always through the existing, live-verified
ai_kit_spec.execute_dispatch.dispatch_execute path, never a raw dispatch_with_heartbeat call and
never a target_dir placeholder baked in ahead of the real dispatch call (HIGH finding)."""
import os
import re

from ai_kit_spec.commands import build_execute_command
from ai_kit_spec.config_io import cfg_resolve
from ai_kit_spec.execute_dispatch import dispatch_execute
from ai_kit_spec.execute_selection import candidates_to_ladder, resolve_execute_candidates
from ai_kit_spec.quota import resolve_ladder_pick

from ai_kit_spec_superpowers.task_classification import (
    classify_task,
    estimate_required_context,
    extract_touched_paths,
)

# Rate/usage-limit signals only -- genuinely time-bound, worth an hourly quota-wake retry.
_DISPATCH_QUOTA_SIGNALS = ("usage limit", "quota", "rate limit", "rate_limit")
# Auth/entitlement/setup signals -- HIGH finding: these never get better by waiting, so they must
# classify as real_error (never "quota"), or an unauthenticated CLI triggers a futile hourly
# CronCreate wake loop forever. Mirrors ai_kit_spec.quota's own private _UNAVAILABLE_SIGNALS
# auth-flavored entries (duplicated, not imported -- that name is a private implementation detail
# of quota.py's probe_reviewer_quota, not a shared public constant). Keep in sync by hand.
_AUTH_SIGNALS = ("actionrequirederror", "not authenticated", "not logged in")
# A probe timeout -- quota.py's own probe_reviewer_quota literally returns this exact detail text
# ("timed out after 30s") on subprocess.TimeoutExpired. Never quota-recoverable: a hung/broken CLI
# invocation does not get better by waiting for quota to refill (HIGH finding).
_TIMEOUT_SIGNAL = "timed out"
# A malformed/missing command template -- ai_kit_spec.commands.render_reviewer_command's own
# ValueError text ("... has cli=... set but no command template" / "... has a malformed command
# template: ..."), confirmed by reading commands.py. A config problem, not a quota problem --
# waiting an hour never fixes a bad template (HIGH finding).
_CONFIGURATION_SIGNALS = ("command template", "no command builder registered",
                           "no execute-mode")
# The CLI binary itself could not be invoked at all -- quota.py's probe_reviewer_quota returns the
# raw OSError text verbatim on a failed subprocess launch (e.g. the binary isn't on PATH). Also
# never quota-recoverable (HIGH finding).
_DISPATCH_UNAVAILABLE_SIGNALS = ("no such file or directory", "command not found", "errno 2")


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
    `reasons` maps each tried key to why it was skipped -- one of SIX typed reasons (HIGH finding:
    a real probe/dispatch failure has more shapes than "quota" vs "auth", and only one of them is
    ever worth an hourly wait):
      - "quota": a genuine, time-bound rate/usage-limit signal -- worth the hourly wake.
      - "auth": an authentication/entitlement/setup problem -- never fixed by waiting.
      - "timeout": the probe itself hung/timed out -- a broken invocation, not a rate limit.
      - "configuration": a missing/malformed command template -- a config problem.
      - "dispatch_unavailable": the CLI binary itself could not be invoked (OSError) --
        no registered execute-mode builder falls under this same umbrella via "no_usable_dispatch"
        below, which is set directly by build_dispatch_injection's own dispatchability check, not
        by _unavailability_reason.
      - "no_usable_dispatch": had quota, but build_execute_command_fn has no registered
        execute-mode builder for this candidate's cli (set directly by build_dispatch_injection,
        never by _unavailability_reason -- see the drop-and-continue branch below).
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
        Every other reason (auth/timeout/configuration/dispatch_unavailable/no_usable_dispatch/
        real_error) never improves by waiting; if NONE of `reasons` is "quota", waiting an hour
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
    no_usable_dispatch/real_error -- genuinely permanent, by construction of QuotaExhaustedError's
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
    should import the other's package. `task_affinity`/`context_limit` come back `None` for
    today's real ai-kit-spec-config output (Global Constraints) -- `.get()`, never `KeyError`."""
    resolved = cfg_resolve_fn(cwd, env)
    candidates = []
    for r in resolved.get("reviewers", []):
        if "key" not in r:
            continue
        candidates.append({
            "key": r["key"], "model": r.get("model", ""), "cli": r.get("cli"),
            "vendor": r.get("vendor", ""), "command": r.get("command"),
            "task_affinity": r.get("task_affinity"), "context_limit": r.get("context_limit"),
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


def _has_quota(quota: dict, key: str) -> bool:
    """Mirrors ai_kit_spec.quota's own private _has_quota (no entry -> never probed -> assume
    available, never block resolution on the ABSENCE of quota data)."""
    entry = quota.get(key)
    if entry is None:
        return True
    return entry.get("available", True)


def _unavailability_reason(quota: dict, key: str) -> str:
    """Classifies why a quota-unavailable candidate is unavailable, from the SAME `detail` text
    quota.py's probe_reviewer_quota already records. HIGH finding (fixed this revision): the
    probe's own generic heuristic marks a candidate unavailable on ANY nonzero exit, a timeout, an
    OSError, or a malformed command template -- NOT only on a genuine rate/usage-limit signal --
    so this function must positively MATCH each typed reason from the real `detail` text rather
    than defaulting everything non-auth to "quota". Only a signal in _DISPATCH_QUOTA_SIGNALS ever
    returns "quota"; every other case returns its own typed reason, and an unmatched/ambiguous/
    empty detail returns "real_error" (never "quota") -- a false "quota" here would wrongly
    schedule an hourly CronCreate wake for a failure that will never improve by waiting, exactly
    the bug this finding closes."""
    detail = (quota.get(key) or {}).get("detail", "").lower()
    if any(signal in detail for signal in _AUTH_SIGNALS):
        return "auth"
    if any(signal in detail for signal in _DISPATCH_QUOTA_SIGNALS):
        return "quota"
    if _TIMEOUT_SIGNAL in detail:
        return "timeout"
    if any(signal in detail for signal in _CONFIGURATION_SIGNALS):
        return "configuration"
    if any(signal in detail for signal in _DISPATCH_UNAVAILABLE_SIGNALS):
        return "dispatch_unavailable"
    return "real_error"


# A non-empty sentinel ONLY for _is_dispatchable's own probe call below -- build_execute_command's
# real builders raise ValueError on an EMPTY target_dir (their own _require_target_dir guard, a
# separate, correct check that a write-capable dispatch never silently lands in the orchestrator's
# own cwd) unrelated to whether the cli has a registered builder at all. This sentinel exists only
# to get past that guard during registration-probing; the resulting command string is discarded
# immediately and NEVER reaches an actual dispatch -- the real target_dir is supplied later, at
# the moment of real dispatch, by dispatch_superpowers_task -> dispatch_execute (Global
# Constraints' "never a literal placeholder baked in ahead of time" rule governs THAT call, not
# this internal capability probe).
_PROBE_TARGET_DIR = "/__ai_kit_spec_execute_superpowers_dispatch_probe__"


def _is_dispatchable(candidate: dict, build_execute_command_fn) -> bool:
    """True for a native candidate (cli is None -- always executes in-process via the Agent
    tool). For ANY CLI-set candidate, including cli == "claude" (CRITICAL finding: only cli is
    None is a native Agent-tool alias -- "claude" is a real, subprocess-invoked entry with its
    own registered execute-mode builder, ai_kit_spec.commands._build_claude_execute_command, and
    must be probed/dispatched exactly like any other CLI), True only if build_execute_command_fn
    actually has a registered execute-mode builder for its cli (raises ValueError otherwise,
    design spec Section 12's "execute-mode builder not yet live-verified for a CLI: refuse ...
    never attempt an unverified invocation" rule) -- CRITICAL finding: this is what makes
    "usable-dispatch filtering" real instead of assumed."""
    cli = candidate.get("cli")
    if cli is None:
        return True
    try:
        build_execute_command_fn(cli, target_dir=_PROBE_TARGET_DIR, effort=candidate.get("effort"),
                                  service_tier=candidate.get("service_tier"))
        return True
    except ValueError:
        return False


def _narrow_and_rank(task_markdown: str, candidates: list, files_touched_sizes: dict,
                      affinity_table: dict, top_n_keys: list) -> tuple:
    """Shared by build_dispatch_injection and compute_ladder_keys (CRITICAL finding: the two
    must never compute the narrowed/ranked candidate order via two independently-drifting code
    paths) -- classifies the task, estimates required context, and narrows+ranks via
    resolve_execute_candidates. Returns (task_type, required_context, ranked)."""
    task_type = classify_task(task_markdown)
    required_context = estimate_required_context(task_markdown, files_touched_sizes)
    ranked = resolve_execute_candidates(
        candidates, task_type, required_context, affinity_table, top_n_keys)
    return task_type, required_context, ranked


def compute_ladder_keys(task_markdown: str, candidates: list, files_touched_sizes: dict,
                         affinity_table: dict, top_n_keys: list) -> list:
    """CRITICAL finding (Rounds 4-5 capability escalation): the FULL ordered candidate-key list
    -- via the SAME narrowing/ranking build_dispatch_injection itself walks (_narrow_and_rank,
    above) -- turned into keys via candidates_to_ladder. Deliberately NOT `list(top_n_keys)`: a
    candidate ranked here but absent from `top_n_keys` (policy.ladder's own configured keys)
    still gets a real, ordered (last-ranked) position, so a caller computing "every candidate
    ranked strictly above the stuck one" (Task 4's SKILL.md escalation rule) never silently misses
    an out-of-ladder candidate the live walk could actually have picked."""
    _, _, ranked = _narrow_and_rank(task_markdown, candidates, files_touched_sizes,
                                     affinity_table, top_n_keys)
    return candidates_to_ladder(ranked)


def build_dispatch_injection(task_markdown: str, candidates: list, files_touched_sizes: dict,
                              affinity_table: dict, top_n_keys: list, quota: dict | None = None,
                              resolve_ladder_pick_fn=resolve_ladder_pick,
                              build_execute_command_fn=build_execute_command) -> dict:
    task_type, required_context, ranked = _narrow_and_rank(
        task_markdown, candidates, files_touched_sizes, affinity_table, top_n_keys)
    if not ranked:
        raise ValueError(
            f"no execute candidate survived affinity/context narrowing for "
            f"task_type={task_type!r}, required_context={required_context} -- cannot build a "
            f"dispatch injection"
        )
    by_key = {c["key"]: c for c in ranked}
    remaining_ladder = candidates_to_ladder(ranked)
    quota = dict(quota or {})
    tried = []
    reasons = {}
    while remaining_ladder:
        pick = resolve_ladder_pick_fn(ranked, remaining_ladder, skip_vendor="", quota=quota)
        if pick is None:
            break  # nothing left in remaining_ladder currently has quota
        candidate = by_key[pick.key]
        if not _is_dispatchable(candidate, build_execute_command_fn):
            # Has quota, but no usable dispatch mechanism -- drop it and keep walking (CRITICAL
            # finding), same drop-and-continue shape ai_kit_spec_gsd.adapter.resolve_gsd_dispatch
            # already uses for its own equivalent case.
            tried.append(pick.key)
            reasons[pick.key] = "no_usable_dispatch"
            remaining_ladder = [k for k in remaining_ladder if k != pick.key]
            continue
        cli = candidate["cli"]
        # CRITICAL finding: only cli is None is a native Agent-tool alias. cli == "claude" is a
        # real, subprocess-invoked entry (ai_kit_spec.commands.py registers a real
        # (_EXECUTE, "claude") builder for it) -- it falls through to the external_cli branch
        # below like any other CLI-set entry, never silently treated as native.
        if cli is None:
            return {"mode": "native_claude", "model": candidate["model"], "key": candidate["key"]}
        return {
            "mode": "external_cli", "key": candidate["key"], "cli": cli,
            "model": candidate["model"], "effort": candidate.get("effort"),
            "service_tier": candidate.get("service_tier"),
        }
    # Nothing left in remaining_ladder currently has quota -- classify each one's own reason
    # (HIGH finding: distinguishes a real, time-bound quota wait from a futile auth retry) and
    # fold it into `tried` so the complete excluded set is what QuotaExhaustedError carries.
    for key in remaining_ladder:
        tried.append(key)
        reasons[key] = _unavailability_reason(quota, key)
    raise QuotaExhaustedError(task_type, tried, reasons)


def dispatch_superpowers_task(injection: dict, prompt: str, target_dir: str,
                               heartbeat_interval: int, timeout: int,
                               format_block: str | None = None,
                               tool_availability: dict | None = None, agents_tooling_path=None,
                               codegraph_registered: bool = False,
                               dispatch_execute_fn=dispatch_execute) -> dict:
    """The ONLY place a mode="external_cli" injection actually runs a subprocess. `target_dir` is
    a real, caller-supplied path at the moment of dispatch -- never resolved ahead of time and
    never a placeholder string (HIGH finding). Always routes through
    ai_kit_spec.execute_dispatch.dispatch_execute, which builds the real execute-mode command,
    composes the reinforcement/tooling/soft-confinement prose, and performs the real dispatch via
    dispatch_with_heartbeat -- this function adds no dispatch mechanics of its own."""
    if injection.get("mode") != "external_cli":
        raise ValueError(
            f"dispatch_superpowers_task is for mode='external_cli' injections only -- got "
            f"mode={injection.get('mode')!r}; a native_claude injection dispatches via the "
            f"Agent tool directly, in-process, and never reaches this function"
        )
    candidate = {"cli": injection["cli"], "model": injection["model"],
                 "effort": injection.get("effort"), "service_tier": injection.get("service_tier")}
    return dispatch_execute_fn(
        candidate, prompt, target_dir, heartbeat_interval, timeout, format_block=format_block,
        tool_availability=tool_availability, agents_tooling_path=agents_tooling_path,
        codegraph_registered=codegraph_registered,
    )


def classify_dispatch_failure(dispatch_result: dict) -> str:
    """Classifies a completed dispatch_superpowers_task result: "ok" (returncode 0), "quota"
    (nonzero returncode + a genuine rate/usage-limit signal in combined stdout+stderr -- retry
    with the next ladder candidate, never this same one), or "real_error" (anything else,
    including a timeout regardless of its own text, AND an auth/entitlement/setup signal --
    HIGH finding: those never get better by waiting, so they must never come back "quota" and
    trigger the caller's hourly CronCreate wake loop -- surfaced honestly to the harness's own
    BLOCKED/fix-loop path instead, design spec Section 12's explicit "never silently retry
    disguised as quota-wait" rule)."""
    if dispatch_result.get("timed_out"):
        return "real_error"
    returncode = dispatch_result.get("returncode", 0)
    if returncode == 0:
        return "ok"
    combined = (dispatch_result.get("stdout", "") + dispatch_result.get("stderr", "")).lower()
    if any(signal in combined for signal in _AUTH_SIGNALS):
        return "real_error"
    if any(signal in combined for signal in _DISPATCH_QUOTA_SIGNALS):
        return "quota"
    return "real_error"
