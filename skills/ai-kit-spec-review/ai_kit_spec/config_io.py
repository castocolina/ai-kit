import os

try:
    import tomllib as _tomllib_impl
    tomllib = _tomllib_impl
except ModuleNotFoundError:        # Python < 3.11 — degrade to env-only config.
    tomllib = None  # type: ignore[assignment]  # stdlib boundary: optional module absent on <3.11

# ── Config (TOML) ────────────────────────────────────────────────────────

DEFAULT_POLICY = {"mode": "single", "ladder": [], "timeout_tiers": [600, 1200, 1800]}

_KNOWN_REVIEWER_FIELDS = {"key", "model", "vendor", "cli", "command"}


def cfg_local_path(cwd: str) -> str:
    """./.aikit/review-spec.toml under cwd."""
    return os.path.join(cwd, ".aikit", "review-spec.toml")


def cfg_global_path(env: dict) -> str:
    """${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/review-spec.toml."""
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
    return os.path.join(base, "ai-kit", "review-spec.toml")


def cfg_load_toml(path: str) -> dict:
    """Parse the TOML at path. Missing/malformed/no-tomllib -> {}. Never
    raises (mirrors tools/status-line.py's cfg_load_toml exactly, since
    this module runs under the same bare system python3, not the .venv)."""
    if tomllib is None:
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def cfg_merge_reviewers(global_list: list, local_list: list) -> list:
    """Merge [[reviewers]] by key: local fields override/extend matching
    global entries; local-only keys are appended; global-only keys are
    preserved unchanged. Order: global order first, then new local keys.
    A malformed entry with no `key` at all is silently skipped (never
    raises) — matches cfg_load_toml's "never raises on bad input"
    contract: one hand-written mistake in review-spec.toml must not crash
    the whole orchestrator."""
    global_list = [r for r in global_list if "key" in r]
    local_list = [r for r in local_list if "key" in r]
    by_key = {r["key"]: dict(r) for r in global_list}
    for r in local_list:
        key = r["key"]
        if key in by_key:
            by_key[key].update(r)
        else:
            by_key[key] = dict(r)
    global_keys = [r["key"] for r in global_list]
    new_local_keys = [r["key"] for r in local_list if r["key"] not in global_keys]
    order = global_keys + new_local_keys
    return [by_key[k] for k in order]


def cfg_resolve(cwd: str, env: dict) -> dict:
    """Resolve the effective config: local (with its own `strategy`) vs
    global, per the design's local/global precedence rules."""
    local = cfg_load_toml(cfg_local_path(cwd))
    if not local:
        global_cfg = cfg_load_toml(cfg_global_path(env))
        return {"policy": {**DEFAULT_POLICY, **global_cfg.get("policy", {})},
                "reviewers": global_cfg.get("reviewers", [])}
    strategy = local.get("strategy", "global-merge")
    if strategy == "local-only":
        return {"policy": {**DEFAULT_POLICY, **local.get("policy", {})},
                "reviewers": local.get("reviewers", [])}
    global_cfg = cfg_load_toml(cfg_global_path(env))
    merged_policy = {**DEFAULT_POLICY, **global_cfg.get("policy", {}), **local.get("policy", {})}
    merged_reviewers = cfg_merge_reviewers(
        global_cfg.get("reviewers", []), local.get("reviewers", [])
    )
    return {"policy": merged_policy, "reviewers": merged_reviewers}


def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    escaped = str(v).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


_VALID_PURPOSE = {"review", "execute", "both"}
_VALID_NATIVE_RUNTIME = {"claude", "opencode", "codex", "cursor", "unknown"}


def validate_reviewer_fields(entry: dict) -> str | None:
    """The review-spec.toml-side sibling of model_catalog.validate_catalog_entry (design spec
    2026-09-02 Section 5: "enforced in both render-toml and the new fetch-model-catalog
    subcommand"). Only checks the THREE fields this design adds -- purpose/is_router/
    fallback_quota -- when present; every pre-existing field's validation is unchanged.
    Absent is always valid (pre-migration configs keep working exactly as before)."""
    key = entry.get("key", "<unknown>")
    # WR-03 fix: `_toml_value` (below) has no `dict` branch -- any dict-valued field falls
    # through to its final `str(v)` branch and silently corrupts into a quoted TOML STRING
    # (e.g. a hand-edited/generated `extra = { timeout_tiers = [...] }`, the exact failure
    # mode SKILL.md documents as a known constraint of this schema) rather than being
    # rejected. Reject it here, up front, for EVERY field (not just the four this design
    # specifically added below) so it surfaces through the existing rejections/WARNING
    # pathway instead of writing corrupted TOML.
    for field, value in entry.items():
        if isinstance(value, dict):
            return (f"{key}: '{field}' has a nested-object value, which this TOML schema "
                     "does not support (no dict branch in the writer)")
    # HIGH finding: `entry["purpose"] not in _VALID_PURPOSE` raises TypeError when `purpose` is
    # an unhashable value (a list/dict) rather than rejecting it as a schema-validation error --
    # the type check MUST run first, short-circuiting before the set-membership test ever sees
    # an unhashable value (spec Section 8: "schema-invalid... entry is rejected and reported",
    # never an unhandled exception).
    if "purpose" in entry and (
            not isinstance(entry["purpose"], str) or entry["purpose"] not in _VALID_PURPOSE):
        return f"{key}: 'purpose' must be one of {sorted(_VALID_PURPOSE)}"
    if "native_runtime" in entry and (
            not isinstance(entry["native_runtime"], str)
            or entry["native_runtime"] not in _VALID_NATIVE_RUNTIME):
        return f"{key}: 'native_runtime' must be one of {sorted(_VALID_NATIVE_RUNTIME)}"
    if "native_runtime" in entry and entry.get("native_runtime") is not None \
            and entry.get("cli") is not None:
        return f"{key}: 'native_runtime' must not be set on an entry with a non-null 'cli'"
    for field in ("is_router", "fallback_quota"):
        if field in entry and not isinstance(entry[field], bool):
            return f"{key}: '{field}' must be a boolean"
    return None


def cfg_render_toml(config: dict) -> str:
    """Hand-rolled TOML serializer for this schema only (an optional
    top-level `strategy` string, a flat [policy] table, and an
    array-of-tables [[reviewers]] with flat string/bool/list values) —
    tomllib is read-only in stdlib, and adding a writer dependency would
    break this repo's zero-dependency runtime.

    A reviewer entry that fails validate_reviewer_fields is dropped individually (never
    aborts the rest of the write) AND removed from policy.ladder -- a valid-looking ladder
    that references a key with no corresponding [[reviewers]] entry is unusable
    (resolve_ladder_pick can never satisfy it), so the two must never diverge."""
    lines = []
    rejections = []
    reviewers = config.get("reviewers", [])
    valid_reviewers = []
    dropped_keys = set()
    for r in reviewers:
        reason = validate_reviewer_fields(r)
        if reason:
            rejections.append(reason)
            if "key" in r:
                dropped_keys.add(r["key"])
            continue
        valid_reviewers.append(r)

    if "strategy" in config:
        lines.append(f"strategy = {_toml_value(config['strategy'])}")
        lines.append("")
    policy = config.get("policy", {})
    if policy:
        raw_ladder = policy.get("ladder") or []
        ladder = [key for key in raw_ladder if key not in dropped_keys]
        # MEDIUM finding: a rejected reviewer's key that was never actually referenced in
        # policy.ladder must never trigger this warning -- `dropped_keys` alone doesn't mean
        # the ladder had a dangling reference, only their INTERSECTION does. Computing it once
        # avoids both the false-positive-on-empty-intersection bug and a redundant second
        # `dropped_keys & set(raw_ladder)` computation on the line below.
        dangling = dropped_keys & set(raw_ladder)
        if dangling:
            rejections.append(
                f"policy.ladder: dropped dangling reference(s) to rejected reviewer key(s) "
                f"{sorted(dangling)}")
        if ladder:
            lines.append("# Priority fallback order (first available reviewer wins the")
            if policy.get("mode") == "double":
                lines.append("# primary slot; double mode also seats an independent secondary):")
            else:
                lines.append("# primary slot):")
            for i, key in enumerate(ladder, 1):
                lines.append(f"#   {i}. {key}")
        lines.append("[policy]")
        for k, v in policy.items():
            v = ladder if k == "ladder" else v
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")
    for r in valid_reviewers:
        lines.append("[[reviewers]]")
        for k, v in r.items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")
    if rejections:
        import sys
        print(f"WARNING: {len(rejections)} issue(s) found and NOT written: "
              f"{'; '.join(rejections)}", file=sys.stderr)
    return "\n".join(lines).rstrip("\n") + "\n"


def cfg_write_toml(path: str, config: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(cfg_render_toml(config))


def resolve_timeout_tiers(reviewer_entry: dict, policy: dict) -> list[int]:
    """A reviewer's own `extra.timeout_tiers` (set via review-spec.toml, e.g. a known-slow
    effort=high CLI/model combination) overrides the policy-wide default for that entry only.
    `policy` is expected to already carry a real `timeout_tiers` list (DEFAULT_POLICY guarantees
    this via cfg_resolve's own merge) -- this function never invents its own fallback constant,
    single source of truth stays DEFAULT_POLICY."""
    override = reviewer_entry.get("extra", {}).get("timeout_tiers")
    return override if override else policy["timeout_tiers"]
