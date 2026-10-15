"""GSD config changes for ai-kit-spec-execute-gsd -- every write goes through
`gsd-tools config-set` (one call per key, D-17, R11), never a direct config.json write, so
GSD's own validation, locking and workstream-aware config path are honored. Ownership of
ai-kit-written values lives in a sidecar `<config dir>/ai-kit-gsd-owned.json` (dotted key ->
value), NOT in config.json: gsd-core 1.16 `config-set` rejects unknown keys (D-16). A lost or
edited sidecar only ever makes existing values read as user-owned (fail-safe), and a legacy
`_ai_kit_spec_execute_gsd` key left in an old config.json is simply ignored -- nothing reads it.
Runtime is a scalar vendor-runtime identity, model_profile_overrides is keyed (runtime, tier),
workflow.cross_ai_* carries the cross-AI hook config."""
import json
import os
import shutil
import time
from typing import NamedTuple

from ai_kit_spec import gsd_tools
from ai_kit_spec.cache import cache_read_json, cache_write_json

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


class GsdWriteContext(NamedTuple):
    """Everything one config-writing run needs, threaded as one value (D-17): the resolved
    gsd-tools handle, the project dir its CLI is invoked with, the config path gsd-tools' own
    `config-path` returned (workstream-aware), the per-run id backing up the config, and the
    subprocess runner (injected in tests)."""

    tools: gsd_tools.GsdTools
    project_dir: str
    config_path: str
    run_id: str
    run_fn: object


class ApplyResult(NamedTuple):
    """Outcome of one `apply_changes` run: the keys whose `config-set` succeeded, the one key
    that failed (None on full success), its error text, and the earlier keys reverted in
    reverse order."""

    applied: list
    failed: str | None
    error: str | None
    reverted: list


OWNERSHIP_SIDECAR = "ai-kit-gsd-owned.json"


def _ownership_path(config_path: str) -> str:
    return os.path.join(os.path.dirname(config_path), OWNERSHIP_SIDECAR)


def read_ownership(config_path: str) -> dict:
    """The sidecar ownership map (dotted key -> value ai-kit wrote), {} when missing -- a lost
    or edited sidecar only ever makes values user-owned (fail-safe, D-16)."""
    return cache_read_json(_ownership_path(config_path)) or {}


def write_ownership(config_path: str, owned: dict) -> None:
    cache_write_json(_ownership_path(config_path), owned)


def _dotted_get(gsd_config: dict, dotted_key: str):
    current = gsd_config
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def is_adapter_owned(gsd_config: dict, config_path: str, dotted_key: str) -> bool:
    """True only when the config's current value is not None and exactly equals the sidecar's
    record for that dotted key -- a missing sidecar means every value reads as user-owned."""
    current = _dotted_get(gsd_config, dotted_key)
    return current is not None and current == read_ownership(config_path).get(dotted_key)


def apply_changes(ctx: GsdWriteContext, changes: list) -> ApplyResult:
    """Applies (dotted_key, value) changes through `gsd-tools config-set`, one call per key, in
    plan order (D-17, R11). Each undo entry is that key's own config-set `previousValue`
    (RUN-11: never a separate config-get). On any failure the earlier applied keys are reverted
    in reverse order and the failed key keeps its new value. gsd-tools owns locking and
    validation; this module never writes config.json itself."""
    if not changes:
        return ApplyResult([], None, None, [])
    _backup_once(ctx.config_path, shutil.copy2, os.path.isfile, ctx.run_id)
    applied, reverts, reverted = [], [], []
    failed, error = None, None
    for key, value in changes:
        ok, output = gsd_tools.config_set(ctx.tools, ctx.project_dir, key, value,
                                           run_fn=ctx.run_fn)
        if not ok:
            failed, error = key, f"config-set failed for {key}: {output}"
            break
        undo = gsd_tools.prior_value(output)
        if undo is None:
            failed = key
            error = (f"config-set gave no parseable result for {key}; its prior value is "
                     f"unknown, so it keeps the new value")
            break
        reverts.append((key, undo[1]))
        applied.append(key)
    if failed is not None:
        for key, prior in reversed(reverts):
            gsd_tools.config_set(ctx.tools, ctx.project_dir, key, prior, run_fn=ctx.run_fn)
            reverted.append(key)
    else:
        owned = read_ownership(ctx.config_path)
        for key, value in changes:
            if value is None:
                owned.pop(key, None)
            else:
                owned[key] = value
        write_ownership(ctx.config_path, owned)
    return ApplyResult(applied, failed, error, reverted)


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


def resolve_native_tier(gsd_config: dict, runtime: str, tier: str):
    """Reads model_profile_overrides.<runtime>.<tier> (Task 1 finding 2's confirmed real shape --
    three levels deep). Never crashes on a missing intermediate level."""
    return gsd_config.get("model_profile_overrides", {}).get(runtime, {}).get(tier)


def resolve_model_profile(gsd_config: dict) -> str:
    """GSD's own confirmed default: model_profile unset reads as "balanced" (core.cjs's own
    `String(config['model_profile'] || 'balanced')`)."""
    return gsd_config.get("model_profile") or "balanced"


def generate_run_id(time_fn=time.time) -> str:
    """A caller performing more than one write per logical run MUST call this exactly once and
    thread the SAME string through the run's GsdWriteContext -- leaving run_id=None on two
    separate calls does NOT give them the same id."""
    return str(int(time_fn() * 1000))


def _backup_once(path: str, backup_copy_fn, isfile_fn, run_id: str) -> None:
    if not isfile_fn(path):
        return
    backup_path = f"{path}{_BACKUP_INFIX}{run_id}.bak"
    if not isfile_fn(backup_path):
        backup_copy_fn(path, backup_path)  # real on-disk bytes, never an in-memory dict
