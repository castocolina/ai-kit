"""GSD's real .planning/config.json read/write surface -- confirmed live against a real GSD
install and a real GSD-managed project's own config (Task 1 finding, this plan's dated finding
subsection): runtime is a scalar vendor-runtime identity, model_profile_overrides is keyed
(runtime, tier), workflow.cross_ai_* carries the cross-AI hook config."""
import json
import os
import shutil
import time

from ai_kit_spec.cache import cache_write_json

KNOWN_GSD_RUNTIMES = {
    "claude", "codex", "gemini", "opencode", "qwen", "kilo", "copilot", "grok", "cursor",
    "windsurf", "augment", "trae", "codebuddy", "cline", "antigravity",
}  # Task 1 finding 2 -- confirmed live, documented non-exhaustive (GSD's own runtime concept is
   # open-ended). cli is None is ALWAYS native, independent of this set (current-session identity).

KNOWN_GSD_TIERS = {"opus", "sonnet", "haiku"}  # Task 7 smoke-test finding -- confirmed live against
# gsd-core/bin/lib/core.cjs's own RUNTIME_OVERRIDE_TIERS constant: model_profile_overrides.<runtime>
# .<tier> ONLY ever consults these three tier names for real model resolution. A fourth Agent-tool
# alias this plan's own Global Constraints named ("fable") is NOT one of them -- writing
# model_profile_overrides.<runtime>.fable produces a real "unknown tier" warning on GSD's own
# stderr and is silently never read back by GSD's resolution logic. Exhaustive, not a floor: GSD's
# own source is the single source of truth for this set, unlike KNOWN_GSD_RUNTIMES above.

_BACKUP_INFIX = ".ai-kit-spec-execute-gsd."  # per-run suffix: f"{path}{_BACKUP_INFIX}{run_id}.bak"
_OWNERSHIP_KEY = "_ai_kit_spec_execute_gsd"

TIER_TO_MODEL_PROFILE = {"opus": "quality", "sonnet": "balanced", "haiku": "budget"}
# Task 7 smoke-test finding: model_profile_overrides.<runtime>.<tier> is confirmed DEAD for the
# claude runtime -- gsd-core/bin/lib/core.cjs's resolveModelInternal only ever reaches
# _resolveRuntimeTier (the function that consults model_profile_overrides) when config['runtime']
# is BOTH set and != "claude"; runtime defaults to null/"claude" for the overwhelming majority of
# real projects (confirmed live: wezterm-setup's own config.json has no "runtime" key at all), so
# that branch never fires for native dispatch. GSD's real, live-confirmed lever for native Claude
# tier choice is the model_profile top-level scalar (quality/balanced/budget/adaptive/inherit --
# gsd-core/bin/shared/model-catalog.json's own `profiles` list), read via its own per-agent-role
# MODEL_PROFILES table. This 3-tier mapping mirrors GSD's own core.cjs fallback intent (quality->
# opus, budget->haiku, else sonnet) -- coarser than a per-tier override (applies project-wide to
# every agent role GSD spawns, not just one dispatch), but it is the mechanism GSD actually reads.


def read_gsd_config(path: str, read_fn=open, warn_fn=print) -> tuple:
    """Returns (config, status) -- status is one of "missing"/"malformed"/"ok". A missing file is
    a valid, unconfigured-project state (no warning, safe to proceed); a malformed/unreadable file
    is a real problem (warned, and callers MUST treat it as a hard abort for any config-mutating
    write)."""
    try:
        with read_fn(path, encoding="utf-8") as f:
            return json.load(f), "ok"
    except FileNotFoundError:
        return {}, "missing"
    except (json.JSONDecodeError, OSError) as exc:
        warn_fn(f"ai-kit-spec-execute-gsd: could not read {path} ({exc}) -- "
                 f"config is MALFORMED, not merely unconfigured -- refusing to write over it")
        return {}, "malformed"


def resolve_active_runtime(gsd_config: dict) -> str:
    """Task 1 finding 2: GSD's own confirmed default -- runtime: null reads as "claude". Never
    returns None; an unset key is a real, meaningful default, not an unknown sentinel."""
    return gsd_config.get("runtime") or "claude"


def write_active_runtime(path: str, gsd_config: dict, runtime: str,
                          write_fn=cache_write_json, backup_copy_fn=shutil.copy2,
                          isfile_fn=os.path.isfile, run_id: str | None = None) -> dict:
    run_id = run_id if run_id is not None else generate_run_id()
    _backup_once(path, backup_copy_fn, isfile_fn, run_id)
    updated = dict(gsd_config)
    updated["runtime"] = runtime
    updated[_OWNERSHIP_KEY] = dict(updated.get(_OWNERSHIP_KEY, {}))
    updated[_OWNERSHIP_KEY]["runtime"] = runtime
    write_fn(path, updated)
    return updated


def resolve_native_tier(gsd_config: dict, runtime: str, tier: str):
    """Reads model_profile_overrides.<runtime>.<tier> (Task 1 finding 2's confirmed real shape --
    three levels deep). Never crashes on a missing intermediate level."""
    return gsd_config.get("model_profile_overrides", {}).get(runtime, {}).get(tier)


def write_native_tier_override(path: str, gsd_config: dict, runtime: str, tier: str, model: str,
                                write_fn=cache_write_json, backup_copy_fn=shutil.copy2,
                                isfile_fn=os.path.isfile, run_id: str | None = None) -> dict:
    run_id = run_id if run_id is not None else generate_run_id()
    _backup_once(path, backup_copy_fn, isfile_fn, run_id)
    updated = dict(gsd_config)
    overrides = {k: dict(v) for k, v in updated.get("model_profile_overrides", {}).items()}
    overrides[runtime] = dict(overrides.get(runtime, {}))
    overrides[runtime][tier] = model
    updated["model_profile_overrides"] = overrides
    updated[_OWNERSHIP_KEY] = dict(updated.get(_OWNERSHIP_KEY, {}))
    marker_overrides = {k: dict(v) for k, v in updated[_OWNERSHIP_KEY].get("overrides", {}).items()}
    marker_overrides[runtime] = dict(marker_overrides.get(runtime, {}))
    marker_overrides[runtime][tier] = model
    updated[_OWNERSHIP_KEY]["overrides"] = marker_overrides
    write_fn(path, updated)
    return updated


def override_is_adapter_owned(gsd_config: dict, runtime: str, tier: str) -> bool:
    current = gsd_config.get("model_profile_overrides", {}).get(runtime, {}).get(tier)
    marker = gsd_config.get(_OWNERSHIP_KEY, {}).get("overrides", {}).get(runtime, {}).get(tier)
    return current is not None and current == marker


def resolve_model_profile(gsd_config: dict) -> str:
    """GSD's own confirmed default: model_profile unset reads as "balanced" (core.cjs's own
    `String(config['model_profile'] || 'balanced')`)."""
    return gsd_config.get("model_profile") or "balanced"


def write_model_profile(path: str, gsd_config: dict, profile: str,
                         write_fn=cache_write_json, backup_copy_fn=shutil.copy2,
                         isfile_fn=os.path.isfile, run_id: str | None = None) -> dict:
    run_id = run_id if run_id is not None else generate_run_id()
    _backup_once(path, backup_copy_fn, isfile_fn, run_id)
    updated = dict(gsd_config)
    updated["model_profile"] = profile
    updated[_OWNERSHIP_KEY] = dict(updated.get(_OWNERSHIP_KEY, {}))
    updated[_OWNERSHIP_KEY]["model_profile"] = profile
    write_fn(path, updated)
    return updated


def model_profile_is_adapter_owned(gsd_config: dict) -> bool:
    current = gsd_config.get("model_profile")
    marker = gsd_config.get(_OWNERSHIP_KEY, {}).get("model_profile")
    return current is not None and current == marker


def resolve_gsd_config_path(cwd: str) -> str:
    """Task 1's spike found no workstream-scoped config path convention in real GSD -- this
    matches the real, confirmed project-root layout exactly (no speculative override params)."""
    return os.path.join(cwd, ".planning", "config.json")


def generate_run_id(time_fn=time.time) -> str:
    """A caller performing more than one write per logical run MUST call this exactly once and
    thread the SAME string through every write call's own run_id argument -- leaving run_id=None
    on two separate calls does NOT give them the same id."""
    return str(int(time_fn() * 1000))


def _backup_once(path: str, backup_copy_fn, isfile_fn, run_id: str) -> None:
    if not isfile_fn(path):
        return
    backup_path = f"{path}{_BACKUP_INFIX}{run_id}.bak"
    if not isfile_fn(backup_path):
        backup_copy_fn(path, backup_path)  # real on-disk bytes, never the in-memory dict


def write_workflow_key(path: str, gsd_config: dict, key: str, value,
                        write_fn=cache_write_json, backup_copy_fn=shutil.copy2,
                        isfile_fn=os.path.isfile, run_id: str | None = None) -> dict:
    run_id = run_id if run_id is not None else generate_run_id()
    _backup_once(path, backup_copy_fn, isfile_fn, run_id)
    updated = dict(gsd_config)
    updated["workflow"] = dict(updated.get("workflow", {}))
    updated["workflow"][key] = value
    updated[_OWNERSHIP_KEY] = dict(updated.get(_OWNERSHIP_KEY, {}))
    updated[_OWNERSHIP_KEY]["workflow"] = dict(updated[_OWNERSHIP_KEY].get("workflow", {}))
    updated[_OWNERSHIP_KEY]["workflow"][key] = value
    write_fn(path, updated)
    return updated


def workflow_key_is_adapter_owned(gsd_config: dict, key: str) -> bool:
    current = gsd_config.get("workflow", {}).get(key)
    marker = gsd_config.get(_OWNERSHIP_KEY, {}).get("workflow", {}).get(key)
    return current is not None and current == marker


def clear_workflow_key_if_adapter_owned(path: str, gsd_config: dict, key: str,
                                         write_fn=cache_write_json, backup_copy_fn=shutil.copy2,
                                         isfile_fn=os.path.isfile,
                                         run_id: str | None = None) -> dict:
    """A LATER run that resolves a DIFFERENT dispatch mode must not leave a PRIOR run's own
    cross_ai_command/cross_ai_execution write active -- GSD would keep routing through a stale
    hook this plan no longer intends active. Only ever clears a key THIS ADAPTER itself set; a
    genuine user-set value is never touched, and an absent key is a no-op."""
    if not workflow_key_is_adapter_owned(gsd_config, key):
        return gsd_config
    run_id = run_id if run_id is not None else generate_run_id()
    _backup_once(path, backup_copy_fn, isfile_fn, run_id)
    updated = dict(gsd_config)
    updated["workflow"] = dict(updated.get("workflow", {}))
    del updated["workflow"][key]
    updated[_OWNERSHIP_KEY] = dict(updated.get(_OWNERSHIP_KEY, {}))
    updated[_OWNERSHIP_KEY]["workflow"] = dict(updated[_OWNERSHIP_KEY].get("workflow", {}))
    del updated[_OWNERSHIP_KEY]["workflow"][key]
    write_fn(path, updated)
    return updated
