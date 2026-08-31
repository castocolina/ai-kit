"""Top-level GSD adapter: assembles candidates from ai-kit-spec's own shared config surface, then
resolves a config-write plan (never a subprocess dispatch, Task 1 finding 3) that Task 5's SKILL.md
hands off to GSD's own /gsd-execute-phase skill. A live-quota-checked candidate with a real,
curated `tier` writes runtime + model_profile_overrides.<runtime>.<tier> directly; one without a
curated tier but with a real cross-AI command falls to cross_ai_hook (command string only -- the
write into workflow.cross_ai_command happens in Task 5, after checking the plan's own cross_ai:
true frontmatter); otherwise an honest fallback notice that makes no unenforced vendor claim."""
from ai_kit_spec.config_io import cfg_resolve
from ai_kit_spec.execute_selection import candidates_to_ladder, resolve_execute_candidates
from ai_kit_spec.quota import resolve_ladder_pick

from ai_kit_spec_gsd.gsd_config import (
    KNOWN_GSD_TIERS,
    TIER_TO_MODEL_PROFILE,
    model_profile_is_adapter_owned,
    override_is_adapter_owned,
    write_active_runtime,
    write_model_profile,
    write_native_tier_override,
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
        cli = r.get("cli")
        # tier: curated field wins; a native (cli is None) entry's own `model` is already a
        # Claude-tier-alias by this repo's existing convention (e.g. "opus-native" -> model:
        # "opus"); a cli-set entry with no curated tier cannot be expressed natively at all.
        tier = r.get("tier")
        if tier is None and cli is None:
            tier = r.get("model")
        candidates.append({
            "key": r["key"], "model": r.get("model", ""), "cli": cli,
            "vendor": r.get("vendor", ""), "command": r.get("command"),
            "task_affinity": r.get("task_affinity"), "context_limit": r.get("context_limit"),
            "tier": tier,
        })
    top_n_keys = resolved.get("policy", {}).get("ladder", [])
    return candidates, top_n_keys


def _runtime_identity(cli) -> str:
    return cli if cli is not None else "claude"


def _fallback_notice(top_choice_key, reason_code: str, reason_prose: str) -> dict:
    top_choice = top_choice_key or "no candidate resolved"
    return {
        "mode": "fallback_notice",
        "key": top_choice_key,
        "cli": None,
        "provenance": "fallback",
        "reason": reason_code,
        "message": (
            f"ai-kit-spec-execute chose {top_choice} for this task, but {reason_prose}. No "
            f"configuration change was made to GSD's config -- GSD's own currently-active "
            f"default (unmodified by ai-kit-spec-execute) will run instead."
        ),
    }


def resolve_gsd_dispatch(candidates: list, top_n_keys: list, gsd_config: dict,
                          gsd_config_path: str, target_dir: str, current_runtime: str = "claude",
                          required_context: int = 0, quota: dict | None = None,
                          run_id: str | None = None, write_tier_fn=write_native_tier_override,
                          write_runtime_fn=write_active_runtime,
                          write_model_profile_fn=write_model_profile,
                          resolve_ladder_pick_fn=resolve_ladder_pick) -> dict:
    quota = dict(quota or {})

    if not candidates:
        return _fallback_notice(
            None, "no_configured_candidate",
            "ai-kit-spec-execute has no configured candidate at all (review-spec.toml has no "
            "[[reviewers]] entries) -- nothing to select from")

    # task_type is execute_selection's own frontend/backend/mixed "task_affinity" axis -- no
    # curated data exists yet, so this is always None (see Global Constraints).
    ranked = resolve_execute_candidates(candidates, None, required_context, {}, top_n_keys)
    if not ranked:
        return _fallback_notice(
            None, "all_candidates_context_rejected",
            f"every one of the {len(candidates)} configured candidate(s) was rejected on context "
            f"size -- each candidate's curated context_limit is smaller than this phase's "
            f"estimated required_context of {required_context}")

    by_key = {c["key"]: c for c in ranked}
    remaining_ladder = candidates_to_ladder(ranked)
    top_key = ranked[0]["key"]

    while remaining_ladder:
        pick = resolve_ladder_pick_fn(ranked, remaining_ladder, skip_vendor="", quota=quota)
        if pick is None:
            break  # nothing left in remaining_ladder currently has quota
        candidate = by_key[pick.key]
        cli = candidate["cli"]
        tier = candidate.get("tier")
        # Task 7 smoke-test finding: GSD's own model resolution (gsd-core/bin/lib/core.cjs's
        # RUNTIME_OVERRIDE_TIERS) ONLY ever consults opus/sonnet/haiku -- a tier outside that set
        # (e.g. the Agent-tool's own 4th alias "fable") would write a real key GSD's own resolution
        # never reads back, so it must never be treated as native-tier-eligible here.
        if tier is not None and tier in KNOWN_GSD_TIERS:
            runtime = _runtime_identity(cli)
            # Task 7 smoke-test finding: model_profile_overrides.<runtime>.<tier> is only ever
            # consulted by GSD's own resolution when runtime is set AND != "claude" -- for the
            # claude runtime (the overwhelmingly common case), the real, live-read lever is the
            # top-level model_profile scalar instead. See gsd_config.py's own TIER_TO_MODEL_PROFILE
            # docstring for the full citation.
            if runtime == "claude":
                profile = TIER_TO_MODEL_PROFILE[tier]
                existing_profile = gsd_config.get("model_profile")
                # Known, accepted trade-off (live-verified 2026-08-31 against a real project
                # scaffolded by GSD's own `gsd-tools.cjs config-new-project`): GSD itself seeds
                # every fresh project's model_profile to "balanced" -- not a deliberate user
                # choice, just GSD's own default. This check can't distinguish that default from
                # a genuine hand-set "balanced" pin, so it treats both the same way (never
                # overwrite) -- meaning in practice this branch rarely ever reaches the write
                # below in a real, freshly-scaffolded project. Confirmed the write mechanism
                # itself works correctly when model_profile is genuinely unset (write_model_profile
                # writes "quality"/"balanced"/"budget" and GSD's own tooling reads it back
                # correctly) -- the gap is only in this condition, and it's being kept as-is:
                # never risking a genuine user pin is worth more than this adapter's own tier
                # decision reliably taking effect.
                if existing_profile is not None and not model_profile_is_adapter_owned(gsd_config):
                    return {"mode": "native_tier", "runtime": runtime, "tier": tier,
                            "model": existing_profile, "written": False, "cli": cli, "key": None,
                            "provenance": "existing_gsd_config"}
                gsd_config = write_model_profile_fn(gsd_config_path, gsd_config, profile,
                                                      run_id=run_id)
                return {"mode": "native_tier", "runtime": runtime, "tier": tier,
                        "model": profile, "written": True, "cli": cli,
                        "key": candidate["key"], "provenance": "resolved_candidate"}
            existing = gsd_config.get("model_profile_overrides", {}).get(runtime, {}).get(tier)
            if existing is not None and not override_is_adapter_owned(gsd_config, runtime, tier):
                return {"mode": "native_tier", "runtime": runtime, "tier": tier,
                        "model": existing, "written": False, "cli": cli, "key": None,
                        "provenance": "existing_gsd_config"}
            if current_runtime != runtime:
                gsd_config = write_runtime_fn(gsd_config_path, gsd_config, runtime, run_id=run_id)
            gsd_config = write_tier_fn(gsd_config_path, gsd_config, runtime, tier,
                                        candidate["model"], run_id=run_id)
            return {"mode": "native_tier", "runtime": runtime, "tier": tier,
                    "model": candidate["model"], "written": True, "cli": cli,
                    "key": candidate["key"], "provenance": "resolved_candidate"}
        cross_ai_command = build_cross_ai_command(candidate, target_dir)
        if cross_ai_command is not None:
            return {"mode": "cross_ai_hook", "cross_ai_command": cross_ai_command, "cli": cli,
                    "key": candidate["key"], "model": candidate["model"],
                    "provenance": "resolved_candidate"}
        # No usable dispatch mechanism for this candidate at all -- drop it and keep walking.
        remaining_ladder = [k for k in remaining_ladder if k != pick.key]

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
