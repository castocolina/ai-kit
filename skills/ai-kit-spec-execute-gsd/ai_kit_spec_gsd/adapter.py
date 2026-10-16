"""Top-level GSD adapter: assembles candidates from ai-kit-spec's own shared config surface, then
resolves a config-write plan (never a subprocess dispatch, Task 1 finding 3) that Task 5's SKILL.md
hands off to GSD's own /gsd-execute-phase skill. A live-quota-checked candidate with a real,
curated `tier` writes runtime + model_profile_overrides.<runtime>.<tier> directly; one without a
curated tier but with a real cross-AI command falls to cross_ai_hook (command string only -- the
write into workflow.cross_ai_command happens in Task 5, after checking the plan's own cross_ai:
true frontmatter); otherwise an honest fallback notice that makes no unenforced vendor claim."""
import sys
from collections.abc import Callable
from typing import Any, NamedTuple

from ai_kit_spec.config_io import cfg_resolve
from ai_kit_spec.execute_selection import (
    ExecuteResolveOptions,
    candidates_to_ladder,
    resolve_execute_candidates,
    screen_execute_clis,
)
from ai_kit_spec.quota import resolve_ladder_pick

from ai_kit_spec_gsd.gsd_config import (
    KNOWN_GSD_TIERS,
    TIER_TO_MODEL_PROFILE,
    ApplyResult,
    GsdWriteContext,
    apply_changes,
    is_adapter_owned,
    resolve_native_tier,
)
from ai_kit_spec_gsd.gsd_cross_ai import build_cross_ai_command


def estimate_required_context(phase_prompt: str) -> int:
    """A real, non-hardcoded estimate of the phase's own context footprint -- standard
    chars-per-token-4 heuristic. Every candidate's context_limit is None today (no curation exists
    yet), so this has no filtering effect through execute_selection.filter_by_context YET; it
    exists so a future curated context_limit is honored immediately, with no change here."""
    return len(phase_prompt) // 4


def assemble_candidates(cwd: str, env: dict, cfg_resolve_fn=cfg_resolve) -> tuple:
    resolved = cfg_resolve_fn(cwd, env)
    candidates = []
    for r in resolved.get("reviewers", []):
        if "key" not in r:
            continue
        runtime = r.get("runtime")
        command = r.get("command")
        tier = r.get("tier")
        alias_native = (runtime is None and not command) or (
            runtime == "claude" and r.get("model") in {"opus", "sonnet", "haiku", "opusplan"}
        )
        if tier is None and alias_native:
            tier = r.get("model")
        candidates.append({
            "key": r["key"], "model": r.get("model", ""),
            "runtime": None if alias_native else runtime,
            "vendor": r.get("vendor", ""), "command": command,
            "task_affinity": r.get("task_affinity"), "context_limit": r.get("context_limit"),
            "tier": tier, "purpose": r.get("purpose"),
            "effort": r.get("effort"), "service_tier": r.get("service_tier"),
        })
    top_n_keys = resolved.get("policy", {}).get("ladder", [])
    return candidates, top_n_keys


class DispatchInputs(NamedTuple):
    candidates: list
    top_n_keys: list
    gsd_config: dict
    ctx: GsdWriteContext


class DispatchContext(NamedTuple):
    target_dir: str
    current_runtime: str = "claude"
    required_context: int = 0
    quota: dict | None = None


class DispatchSeams(NamedTuple):
    apply_changes_fn: Callable[..., ApplyResult] = apply_changes
    is_adapter_owned_fn: Callable[..., bool] = is_adapter_owned
    resolve_ladder_pick_fn: Callable[..., Any] = resolve_ladder_pick


class NativeTierOutcome(NamedTuple):
    runtime: str
    tier: str
    model: str
    key: Any
    written: bool
    provenance: str


def _runtime_identity(cli) -> str:
    return cli if cli is not None else "claude"


# D-15 names claude and grok (their execute builders were deleted). Whether D-15 also covers
# GSD's own native-tier route for them is not settled, so they stay screened (fail closed).
_D15_NAMED_CLIS = frozenset({"claude", "grok"})


def _native_tier_route(candidate: dict) -> bool:
    """A curated GSD tier is written as GSD config and run by GSD's own runtime -- it never
    uses an ai-kit execute builder, so D-15's builder screen does not apply (A-WR-08)."""
    return (candidate.get("tier") in KNOWN_GSD_TIERS
            and candidate.get("runtime") not in _D15_NAMED_CLIS)


def _fallback_notice(top_choice_key, reason_code: str, reason_prose: str) -> dict:
    top_choice = top_choice_key or "no candidate resolved"
    return {
        "mode": "fallback_notice",
        "key": top_choice_key,
        "runtime": None,
        "provenance": "fallback",
        "reason": reason_code,
        "message": (
            f"ai-kit-spec-execute chose {top_choice} for this task, but {reason_prose}. No "
            f"configuration change was made to GSD's config -- GSD's own currently-active "
            f"default (unmodified by ai-kit-spec-execute) will run instead."
        ),
    }


def _write_failed(apply_result: ApplyResult, runtime, tier, key) -> dict:
    return {"mode": "write_failed", "applied": apply_result.applied,
            "failed": apply_result.failed, "reverted": apply_result.reverted,
            "revert_failed": apply_result.revert_failed, "error": apply_result.error,
            "runtime": runtime, "tier": tier, "key": key}


def _native_tier_result(outcome: NativeTierOutcome) -> dict:
    return {"mode": "native_tier", **outcome._asdict()}


def _dispatch_claude_tier(
    candidate: dict, gsd_config: dict, ctx: GsdWriteContext, seams: DispatchSeams,
) -> dict | None:
    tier = candidate.get("tier")
    if tier is None or tier not in KNOWN_GSD_TIERS:
        return None
    runtime = _runtime_identity(candidate["runtime"])
    if runtime != "claude":
        return None
    profile = TIER_TO_MODEL_PROFILE[tier]
    existing_profile = gsd_config.get("model_profile")
    if existing_profile is not None and not seams.is_adapter_owned_fn(
            gsd_config, ctx.config_path, "model_profile"):
        return _native_tier_result(NativeTierOutcome(
            runtime, tier, existing_profile, None, False, "existing_gsd_config"))
    applied = seams.apply_changes_fn(ctx, [("model_profile", profile)])
    if applied.failed:
        return _write_failed(applied, runtime, tier, candidate["key"])
    return _native_tier_result(NativeTierOutcome(
        runtime, tier, profile, candidate["key"], True, "resolved_candidate"))


def _dispatch_non_claude_tier(
    candidate: dict, gsd_config: dict, ctx: GsdWriteContext, dispatch: DispatchContext,
    seams: DispatchSeams,
) -> dict | None:
    tier = candidate.get("tier")
    if tier is None or tier not in KNOWN_GSD_TIERS:
        return None
    runtime = _runtime_identity(candidate["runtime"])
    if runtime == "claude":
        return None
    tier_dotted = f"model_profile_overrides.{runtime}.{tier}"
    existing = resolve_native_tier(gsd_config, runtime, tier)
    if existing is not None and not seams.is_adapter_owned_fn(
            gsd_config, ctx.config_path, tier_dotted):
        return _native_tier_result(NativeTierOutcome(
            runtime, tier, existing, None, False, "existing_gsd_config"))
    changes = []
    if dispatch.current_runtime != runtime:
        changes.append(("runtime", runtime))
    changes.append((tier_dotted, candidate["model"]))
    applied = seams.apply_changes_fn(ctx, changes)
    if applied.failed:
        return _write_failed(applied, runtime, tier, candidate["key"])
    return _native_tier_result(NativeTierOutcome(
        runtime, tier, candidate["model"], candidate["key"], True, "resolved_candidate"))


def _try_candidate_dispatch(
    candidate: dict, gsd_config: dict, ctx: GsdWriteContext, dispatch: DispatchContext,
    seams: DispatchSeams,
) -> dict | None:
    result = _dispatch_claude_tier(candidate, gsd_config, ctx, seams)
    if result is not None:
        return result
    result = _dispatch_non_claude_tier(candidate, gsd_config, ctx, dispatch, seams)
    if result is not None:
        return result
    cross_ai_command = build_cross_ai_command(candidate, dispatch.target_dir)
    if cross_ai_command is not None:
        cli = candidate["runtime"]
        return {"mode": "cross_ai_hook", "cross_ai_command": cross_ai_command,
                "runtime": cli,
                "key": candidate["key"], "model": candidate["model"],
                "provenance": "resolved_candidate"}
    return None


def _ladder_exhausted_notice(
    top_key: str, remaining_ladder: list, by_key: dict, target_dir: str,
) -> dict:
    has_retryable_remaining = any(
        by_key[k].get("tier") in KNOWN_GSD_TIERS
        or build_cross_ai_command(by_key[k], target_dir) is not None
        for k in remaining_ladder
    )
    reason_code = "quota_exhausted" if has_retryable_remaining else "no_usable_dispatch"
    reason_prose = (
        "every candidate in the ladder is quota-exhausted"
        if reason_code == "quota_exhausted" else
        "no quota-available candidate in the ladder has a usable native slot or cross-AI command"
    )
    return _fallback_notice(top_key, reason_code, reason_prose)


def resolve_gsd_dispatch(
    inputs: DispatchInputs,
    dispatch: DispatchContext,
    seams: DispatchSeams | None = None,
) -> dict:
    seams = seams or DispatchSeams()
    candidates = inputs.candidates
    top_n_keys = inputs.top_n_keys
    gsd_config = inputs.gsd_config
    ctx = inputs.ctx
    quota = dict(dispatch.quota or {})

    if not candidates:
        return _fallback_notice(
            None, "no_configured_candidate",
            "ai-kit-spec-execute has no configured candidate at all (review-spec.toml has no "
            "[[reviewers]] entries) -- nothing to select from")

    ranked = resolve_execute_candidates(
        candidates,
        ExecuteResolveOptions(
            None, dispatch.required_context, {}, top_n_keys,
            warn_fn=lambda msg: print(msg, file=sys.stderr),
            screen_exempt_fn=_native_tier_route),
    )
    if not ranked and not screen_execute_clis(candidates, lambda _msg: None, _native_tier_route):
        return _fallback_notice(
            candidates[0]["key"], "no_usable_dispatch",
            "no configured candidate has a usable native GSD tier or a CLI with an execute "
            "builder (each was skipped with a warning above)")
    if not ranked:
        return _fallback_notice(
            None, "all_candidates_context_rejected",
            f"every one of the {len(candidates)} configured candidate(s) was rejected on context "
            f"size -- each candidate's curated context_limit is smaller than this phase's "
            f"estimated required_context of {dispatch.required_context}")

    by_key = {c["key"]: c for c in ranked}
    remaining_ladder = candidates_to_ladder(ranked)
    top_key = ranked[0]["key"]

    while remaining_ladder:
        pick = seams.resolve_ladder_pick_fn(
            ranked, remaining_ladder, skip_vendor="", quota=quota)
        if pick is None:
            break
        candidate = by_key[pick.key]
        result = _try_candidate_dispatch(candidate, gsd_config, ctx, dispatch, seams)
        if result is not None:
            return result
        remaining_ladder = [k for k in remaining_ladder if k != pick.key]

    return _ladder_exhausted_notice(top_key, remaining_ladder, by_key, dispatch.target_dir)
