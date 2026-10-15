import os
import sys

from ai_kit_spec.trust import is_trusted

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


def cfg_config_base(env: dict) -> str:
    """${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit -- the base for ai-kit's own config files
    (the global review-spec.toml and the trust store). Never relative: an unset HOME would
    otherwise resolve under the cwd -- the project -- letting a repo ship its own "global"
    config and trust store (A-WR-01). A relative XDG_CONFIG_HOME is ignored (XDG spec); no
    absolute home at all raises ConfigError (exit 2 in the CLI mains)."""
    xdg = env.get("XDG_CONFIG_HOME", "")
    if os.path.isabs(xdg):
        return os.path.join(xdg, "ai-kit")
    home = env.get("HOME") or os.path.expanduser("~")
    if not os.path.isabs(home):
        raise ConfigError("$HOME", "no absolute home directory to hold ai-kit's config")
    return os.path.join(home, ".config", "ai-kit")


def cfg_trust_store_dir(env: dict) -> str:
    """Directory holding per-content trust records for project-local review-spec.toml
    files (trust.py). Under ai-kit's own config base, never in the project."""
    return os.path.join(cfg_config_base(env), "review-spec-trust")


def cfg_global_path(env: dict) -> str:
    """${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/review-spec.toml."""
    return os.path.join(cfg_config_base(env), "review-spec.toml")


class ConfigError(ValueError):
    """A review-spec.toml exists but cannot be parsed (malformed TOML, non-UTF-8 bytes, or
    no tomllib on this interpreter). Carries the path and the parser message; the CLI mains
    catch it, print it to stderr, and exit 2 (D-11/R13) -- a broken config must stop the
    CLIs loudly, never silently disable cross-AI review."""

    def __init__(self, path: str, message: str):
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def cfg_load_toml(path: str) -> dict:
    """Parse the TOML at path. A missing file is a valid empty config -> {} (a missing
    review-spec.toml is the normal no-config state, never an error). Any OTHER problem
    raises ConfigError (D-11/R13): an existing malformed or non-UTF-8 file, an unreadable
    file, or tomllib missing on Python < 3.11. Unlike tools/status-line.py's never-raise
    loader, this module FAILS LOUDLY -- a silently-ignored broken review-spec.toml would
    switch cross-AI review off without the user ever knowing."""
    if tomllib is None:
        if os.path.exists(path):
            raise ConfigError(path, "reading TOML needs Python 3.11+")
        return {}
    try:
        with open(path, "rb") as f:
            return cfg_parse_toml_bytes(f.read(), path)
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise ConfigError(path, str(exc)) from exc


def cfg_read_bytes(path: str) -> bytes:
    """Read a config file's raw bytes once (the trust gate hashes and parses the same
    buffer); an unreadable file (permissions, a directory) is a ConfigError, exit 2."""
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError as exc:
        raise ConfigError(path, str(exc)) from exc


def cfg_parse_toml_bytes(raw: bytes, path: str) -> dict:
    """Parse already-read TOML bytes; raise ConfigError naming `path` for malformed TOML
    or non-UTF-8 bytes. Kept separate so cfg_resolve can hash and parse the SAME bytes it
    read once -- no check-then-read gap between the trust decision and the parse."""
    if tomllib is None:
        raise ConfigError(path, "reading TOML needs Python 3.11+")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ConfigError(path, f"not valid UTF-8 ({exc})") from exc
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(path, str(exc)) from exc


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


def _cfg_default_warn(msg: str) -> None:
    print(msg, file=sys.stderr)


def cfg_resolve(cwd: str, env: dict, warn_fn=None) -> dict:
    """Resolve the effective config: local (with its own `strategy`) vs
    global, per the design's local/global precedence rules.

    Trust gate (D-08, Plan 16.1-08): the local file's bytes are read ONCE, parsed, and the
    parsed dict is kept only when that exact content is trusted (trust.py). An untrusted
    local file is ignored entirely -- this resolves to global config only -- and warn_fn
    (default: stderr) explains how to review and trust it. Parsing executes nothing, so a
    malformed local file still parses the same whether trusted or not."""
    emit_warn = warn_fn if warn_fn is not None else _cfg_default_warn
    local_path = cfg_local_path(cwd)
    local = {}
    if os.path.exists(local_path):
        raw = cfg_read_bytes(local_path)
        # Parsing happens BEFORE the trust check (D-08 interpretation): a malformed file is
        # reported (R13) whether or not it is trusted -- parsing executes nothing.
        parsed = cfg_parse_toml_bytes(raw, local_path)
        if is_trusted(cfg_trust_store_dir(env), os.path.realpath(local_path), raw):
            local = parsed
        else:
            emit_warn(
                f"ai-kit-spec: ignoring untrusted project-local config {local_path}; "
                f"review its commands with `ai-kit-spec.py trust-local --cwd {cwd} --show`, "
                f"then trust it with `ai-kit-spec.py trust-local --cwd {cwd}` "
                f"(any edit needs a new trust)")
    return cfg_combine(local, env)


def cfg_combine(local: dict, env: dict) -> dict:
    """Combine an already-parsed (and already-trusted, or empty) local config with the
    global one, honoring the local `strategy`. Shared by cfg_resolve and `trust-local
    --show`, so the consent display renders the same merged entries dispatch would run."""
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
# Deliberately duplicated with model_catalog._VALID_NATIVE_RUNTIME -- the two sets must change
# together (AGENTS.md Architecture). "pi" is here because detect_current_runtime can return it
# since Phase 16.
_VALID_NATIVE_RUNTIME = {"claude", "opencode", "codex", "cursor", "pi", "unknown"}


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


def _cfg_partition_reviewers(reviewers: list) -> tuple[list, list, set]:
    rejections = []
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
    return valid_reviewers, rejections, dropped_keys


def _cfg_render_policy_lines(policy: dict, dropped_keys: set, rejections: list) -> list[str]:
    lines: list[str] = []
    raw_ladder = policy.get("ladder") or []
    ladder = [key for key in raw_ladder if key not in dropped_keys]
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
    return lines


def _cfg_render_reviewer_lines(valid_reviewers: list) -> list[str]:
    lines: list[str] = []
    for r in valid_reviewers:
        lines.append("[[reviewers]]")
        for k, v in r.items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")
    return lines


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
    lines: list[str] = []
    valid_reviewers, rejections, dropped_keys = _cfg_partition_reviewers(
        config.get("reviewers", []))

    if "strategy" in config:
        lines.append(f"strategy = {_toml_value(config['strategy'])}")
        lines.append("")
    policy = config.get("policy", {})
    if policy:
        lines.extend(_cfg_render_policy_lines(policy, dropped_keys, rejections))
    lines.extend(_cfg_render_reviewer_lines(valid_reviewers))
    if rejections:
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
