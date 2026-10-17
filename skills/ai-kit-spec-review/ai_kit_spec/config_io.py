import os
import shlex
import sys

from ai_kit_spec.cache import cache_write_text
from ai_kit_spec.detection import RUNTIMES, runtime_id
from ai_kit_spec.trust import is_trusted

try:
    import tomllib as _tomllib_impl

    tomllib = _tomllib_impl
except ModuleNotFoundError:  # Python < 3.11 — degrade to env-only config.
    tomllib = None  # type: ignore[assignment]  # stdlib boundary: optional module absent on <3.11

# ── Config (TOML) ────────────────────────────────────────────────────────

DEFAULT_POLICY = {"mode": "single", "ladder": [], "timeout_tiers": [600, 1200, 1800]}

_KNOWN_REVIEWER_FIELDS = {"key", "model", "vendor", "runtime", "command"}

_MODE_SLOT = "{mode}"
# The pre-18.1 factory templates, frozen here so a stored legacy `command` can be recognised
# and dropped (D-32); cursor's binary is sourced from the runtime table.
_FACTORY_ARGV: dict[str, tuple[str, ...]] = {
    "codex": ("codex", "exec", "--sandbox", "read-only", "--skip-git-repo-check", "-m", "{model}"),
    "claude": ("claude", "-p", "--model", "{model}", "--output-format", "text"),
    "opencode": ("opencode", "run", "-m", "{model}"),
    "cursor": (
        RUNTIMES["cursor"].binaries[0],
        "-p",
        "--output-format",
        "text",
        "--mode",
        _MODE_SLOT,
        "--trust",
        "--model",
        "{model}",
    ),
}
_CODEX_KNOB_ORDER = ("model_reasoning_effort", "service_tier")
_LEGACY_NOTED: set[str] = set()


def _codex_command_knobs(remainder) -> dict | None:
    if len(remainder) % 2 or len(remainder) > 4:
        return None
    knobs = {}
    previous = -1
    for flag, assignment in zip(remainder[::2], remainder[1::2], strict=True):
        if flag != "-c" or "=" not in assignment:
            return None
        key, value = assignment.split("=", 1)
        if key not in _CODEX_KNOB_ORDER:
            return None
        order = _CODEX_KNOB_ORDER.index(key)
        if order <= previous:
            return None
        previous = order
        value = value.strip("'\\\"")
        knobs["effort" if key == "model_reasoning_effort" else "service_tier"] = value
    return knobs


def _legacy_command_knobs(rid, command) -> dict | None:
    """Return factory knobs only when command exactly matches a known argv shape."""
    if not isinstance(command, str):
        return None
    try:
        argv = shlex.split(command)
    except ValueError:
        return None
    head = _FACTORY_ARGV.get(rid)
    if head is None or len(argv) < len(head):
        return None
    knobs = _factory_head_knobs(head, argv)
    if knobs is None:
        return None
    remainder = argv[len(head) :]
    if rid == "codex":
        codex_knobs = _codex_command_knobs(remainder)
        return {**knobs, **codex_knobs} if codex_knobs is not None else None
    return knobs if not remainder else None


def _factory_head_knobs(head, argv) -> dict | None:
    knobs = {}
    for index, expected in enumerate(head):
        token = argv[index]
        if expected == _MODE_SLOT:
            if token not in ("plan", "ask"):
                return None
            knobs["cursor_mode"] = token
        elif token != expected:
            return None
    return knobs


def _normalize_legacy_cli(result: dict, key) -> list[str]:
    cli = result["cli"]
    rid = runtime_id(cli)
    command = result.get("command")
    result.pop("cli", None)
    result.pop("native_runtime", None)
    row = RUNTIMES.get(rid)
    if row is None or not row.runner:
        if "command" in result:
            return [f"{key}: cli={cli} has no runner formula; kept as a custom command entry"]
        result["runtime"] = rid
        return [f"{key}: cli={cli} has no runner formula and no command; this entry is skipped "
                f"(build-command --runtime {rid} generates a custom command entry)"]
    if "command" not in result:
        result["runtime"] = rid
        return [f"{key}: cli={cli} -> runtime={rid}"]
    knobs = _legacy_command_knobs(rid, command)
    if knobs is None:
        return [
            f"{key}: cli={cli}: command has flags the runner formula does not reproduce; "
            "kept as a custom command entry"
        ]
    result["runtime"] = rid
    result.pop("command", None)
    kept = []
    for knob, value in knobs.items():
        if knob not in result:
            result[knob] = value
            kept.append(knob)
    suffix = f"; kept {', '.join(kept)}" if kept else ""
    return [
        f"{key}: cli={cli} -> runtime={rid}; command dropped (the runner builds the argv){suffix}"
    ]


def _normalize_legacy_native(result: dict, key) -> list[str]:
    value = result.pop("native_runtime")
    if value == "unknown" or value is None:
        if isinstance(result.get("runtime"), str):
            return [f"{key}: native_runtime={value} ignored; runtime={result['runtime']} kept"]
        model = result.pop("model", None)
        result.pop("runtime", None)
        return (
            [f"{key}: native_runtime=unknown: model '{model}' dropped, now the session default"]
            if model
            else []
        )
    rid = runtime_id(value)
    if "runtime" not in result:
        result["runtime"] = rid
    return [f"{key}: native_runtime={value} -> runtime={result['runtime']}"]


def normalize_legacy_entry(entry) -> tuple[dict, list[str]]:
    """Copy and normalize one legacy reviewer entry without raising or mutating it."""
    if not isinstance(entry, dict):
        return entry, []
    result = dict(entry)
    key = result.get("key", "<unknown>")
    notes = []
    for field in ("cli", "runtime", "native_runtime"):
        value = result.get(field)
        if field in result and value is not None and not isinstance(value, str):
            return result, [
                f"{key}: '{field}' is not a string; left unchanged "
                "(save rejects it, dispatch skips it as unknown_runtime)"
            ]

    if "command" in result and not isinstance(result["command"], str):
        return result, [f"{key}: 'command' is not a string; left unchanged"]
    if result.get("cli") is not None:
        notes.extend(_normalize_legacy_cli(result, key))
    elif "native_runtime" in result:
        notes.extend(_normalize_legacy_native(result, key))
    if isinstance(result.get("runtime"), str):
        old = result["runtime"]
        rid = runtime_id(old)
        if rid != old:
            result["runtime"] = rid
            notes.append(f"{key}: runtime={old} -> {rid}")
    return result, notes


def _drop_stored_routes(reviewers) -> tuple[list, list[str]]:
    """Drop a stored route from every entry. Load-only: save rejects one instead."""
    cleaned = []
    notes = []
    for entry in reviewers:
        result, note = _drop_stored_route(entry)
        cleaned.append(result)
        if note:
            notes.append(note)
    return cleaned, notes


def _drop_stored_route(entry) -> tuple[dict, str | None]:
    """A stored route is a decision, never config. Load drops it; save rejects it."""
    if not isinstance(entry, dict) or "route" not in entry:
        return entry, None
    result = dict(entry)
    value = result.pop("route")
    return result, f"{entry.get('key', '<unknown>')}: route={value} ignored (decided per run)"


def normalize_legacy_reviewers(reviewers) -> tuple[list, list[str]]:
    """Normalize reviewer entries while preserving order and malformed non-dicts."""
    normalized = []
    notes = []
    if not isinstance(reviewers, list):
        return normalized, notes
    for entry in reviewers:
        mapped, entry_notes = normalize_legacy_entry(entry)
        normalized.append(mapped)
        notes.extend(entry_notes)
    return normalized, notes


def infer_legacy_native(reviewers) -> tuple[list, list[str]]:
    """Apply the separate legacy alias inference after reviewer merging."""
    normalized = []
    notes = []
    for entry in reviewers:
        if not isinstance(entry, dict):
            normalized.append(entry)
            continue
        mapped = dict(entry)
        model = mapped.get("model")
        # A non-string legacy field was left as-is by normalize_legacy_entry (B-WR-03).
        legacy = any(mapped.get(field) is not None for field in ("cli", "native_runtime"))
        if (
            mapped.get("runtime") in (None, "")
            and not legacy
            and "command" not in mapped
            and isinstance(model, str)
            and model
        ):
            key = mapped.get("key", "<unknown>")
            if model in RUNTIMES["claude"].native_selectors:
                mapped["runtime"] = "claude"
                notes.append(
                    f"{key}: model '{model}' had no runtime; inferred runtime=claude "
                    "(pre-1.2 native meaning)"
                )
            else:
                mapped["model"] = ""
                notes.append(
                    f"{key}: model '{model}' had no runtime; dropped, now the session default"
                )
        normalized.append(mapped)
    return normalized, notes


def _emit_legacy_note(label, notes, warn_fn) -> None:
    """Emit one privacy-safe migration note per label in this process."""
    if not notes or label in _LEGACY_NOTED:
        return
    _LEGACY_NOTED.add(label)
    warn_fn(
        f"ai-kit-spec: {label}: legacy reviewer fields loaded in memory "
        f"({'; '.join(notes)}); the file is unchanged -- re-save it with the "
        "ai-kit-spec-config wizard or render-toml --out <file> --replace"
    )


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


_VARIANT_FIELDS = ("runtime", "command")


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
            if any(r.get(field) is not None for field in _VARIANT_FIELDS):
                for field in _VARIANT_FIELDS:
                    if field not in r:
                        by_key[key].pop(field, None)
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
                f"(any edit needs a new trust)"
            )
    return cfg_combine(local, env, warn_fn=emit_warn, local_path=local_path)


def _combine_layers(local, global_cfg):
    """(reviewers, policy) after strategy, legacy normalization and the route drop."""
    local_reviewers, local_notes = normalize_legacy_reviewers(local.get("reviewers", []))
    global_reviewers, global_notes = normalize_legacy_reviewers(global_cfg.get("reviewers", []))
    strategy = local.get("strategy", "global-merge") if local else "global-merge"
    if not local:
        merged, policy = global_reviewers, {**DEFAULT_POLICY, **global_cfg.get("policy", {})}
    elif strategy == "local-only":
        merged, policy = local_reviewers, {**DEFAULT_POLICY, **local.get("policy", {})}
    else:
        merged = cfg_merge_reviewers(global_reviewers, local_reviewers)
        policy = {**DEFAULT_POLICY, **global_cfg.get("policy", {}), **local.get("policy", {})}
    merged, inferred_notes = infer_legacy_native(merged)
    merged, route_notes = _drop_stored_routes(merged)
    return merged, policy, local_notes, global_notes, inferred_notes + route_notes


def cfg_combine(local: dict, env: dict, warn_fn=None, local_path=None) -> dict:
    """Combine an already-parsed (and already-trusted, or empty) local config with the
    global one, honoring the local `strategy`. Shared by cfg_resolve and `trust-local
    --show`, so the consent display renders the same merged entries dispatch would run."""
    emit_warn = warn_fn if warn_fn is not None else _cfg_default_warn
    global_path = cfg_global_path(env)
    # A local-only project never consults the global file, so it is never read (B-WR-01).
    local_only = bool(local) and local.get("strategy") == "local-only"
    merged, policy, local_notes, global_notes, notes = _combine_layers(
        local, {} if local_only else cfg_load_toml(global_path))
    if local:
        _emit_legacy_note(local_path or "project-local review-spec.toml", local_notes, emit_warn)
    _emit_legacy_note(global_path, global_notes, emit_warn)
    _emit_legacy_note(f"merged review-spec.toml ({local_path or 'local'}, {global_path})",
                      notes, emit_warn)
    return {"policy": policy, "reviewers": merged}


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
_LEGACY_WRITE_FIELDS = ("cli", "native_runtime")


# A runner-less row (grok) runs only as a custom command entry (D-29), never as a pair.
_RUNNER_RUNTIMES = sorted(rid for rid, row in RUNTIMES.items() if row.runner)


def _validate_pair_fields(entry: dict, key) -> str | None:
    """Save is strict: a runtime must be a runner row and carry a model, a command only exists
    on a custom entry, and a pinned model needs a runtime. Load stays lenient."""
    runtime = entry.get("runtime")
    if "runtime" in entry and runtime is not None:
        if not isinstance(runtime, str) or runtime not in _RUNNER_RUNTIMES:
            return f"{key}: 'runtime' must be one of {_RUNNER_RUNTIMES}"
        model = entry.get("model")
        if "model" not in entry or not isinstance(model, str) or model == "":
            return f"{key}: an entry with a 'runtime' needs a non-empty 'model'"
    if "command" in entry and (
        not isinstance(entry["command"], str)
        or entry["command"] == ""
        or entry.get("runtime") is not None
    ):
        return f"{key}: 'command' is only for a custom entry with no 'runtime'"
    model = entry.get("model")
    if (
        entry.get("runtime") is None
        and "command" not in entry
        and isinstance(model, str)
        and model
    ):
        return (
            f"{key}: a pinned 'model' needs a 'runtime' "
            "(or leave both unset for the session default)"
        )
    for name in _LEGACY_WRITE_FIELDS:
        if name in entry and entry[name] is not None:
            return f"{key}: legacy field '{name}' is not written"
    return None


def validate_reviewer_fields(entry: dict) -> str | None:
    """The review-spec.toml-side sibling of model_catalog.validate_catalog_entry (design spec
    2026-09-02 Section 5: "enforced in both render-toml and the new fetch-model-catalog
    subcommand"). Checks purpose/is_router/fallback_quota when present, then the pair rules:
    a table runtime needs a model, a command is custom-only, a pinned model needs a runtime."""
    key = entry.get("key", "<unknown>")
    # WR-03 fix: `_toml_value` (below) has no `dict` branch -- any dict-valued field falls
    # through to its final `str(v)` branch and silently corrupts into a quoted TOML STRING
    # (e.g. a hand-edited/generated `extra = { timeout_tiers = [...] }`, the exact failure
    # mode SKILL.md documents as a known constraint of this schema) rather than being
    # rejected. Reject it here, up front, for EVERY field (not just the four this design
    # specifically added below) so it surfaces through the existing rejections/WARNING
    # pathway instead of writing corrupted TOML.
    for field, value in entry.items():
        if field == "route":
            return f"{key}: 'route' is decided per run and is never stored"
        if isinstance(value, dict):
            return (
                f"{key}: '{field}' has a nested-object value, which this TOML schema "
                "does not support (no dict branch in the writer)"
            )
    # HIGH finding: `entry["purpose"] not in _VALID_PURPOSE` raises TypeError when `purpose` is
    # an unhashable value (a list/dict) rather than rejecting it as a schema-validation error --
    # the type check MUST run first, short-circuiting before the set-membership test ever sees
    # an unhashable value (spec Section 8: "schema-invalid... entry is rejected and reported",
    # never an unhandled exception).
    if "purpose" in entry and (
        not isinstance(entry["purpose"], str) or entry["purpose"] not in _VALID_PURPOSE
    ):
        return f"{key}: 'purpose' must be one of {sorted(_VALID_PURPOSE)}"
    for field in ("is_router", "fallback_quota"):
        if field in entry and not isinstance(entry[field], bool):
            return f"{key}: '{field}' must be a boolean"
    return _validate_pair_fields(entry, key)


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
            f"{sorted(dangling)}"
        )
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


def _cfg_render_reviewers(config: dict) -> tuple[list, list[str]]:
    """The two load steps, in the same order, so a write holds only the new form.

    A stored route is NOT dropped here: save rejects it, so the entry stays intact for
    validate_reviewer_fields to refuse. Load drops it instead."""
    reviewers, notes = normalize_legacy_reviewers(config.get("reviewers", []))
    reviewers, inferred = infer_legacy_native(reviewers)
    return reviewers, notes + inferred


def cfg_render_toml(config: dict) -> str:
    """Hand-rolled TOML serializer for this schema only (an optional
    top-level `strategy` string, a flat [policy] table, and an
    array-of-tables [[reviewers]] with flat string/bool/list values) —
    tomllib is read-only in stdlib, and adding a writer dependency would
    break this repo's zero-dependency runtime.

    Reviewers are normalized first (the same two steps load runs), then validated strictly:
    an entry that fails validate_reviewer_fields is dropped individually (never aborts the
    rest of the write) AND removed from policy.ladder -- a valid-looking ladder that
    references a key with no corresponding [[reviewers]] entry is unusable
    (resolve_ladder_pick can never satisfy it), so the two must never diverge."""
    lines: list[str] = []
    reviewers, notes = _cfg_render_reviewers(config)
    if notes:
        print(
            "ai-kit-spec: render-toml: migrated legacy fields before writing "
            f"({'; '.join(notes)})",
            file=sys.stderr,
        )
    valid_reviewers, rejections, dropped_keys = _cfg_partition_reviewers(reviewers)

    if "strategy" in config:
        lines.append(f"strategy = {_toml_value(config['strategy'])}")
        lines.append("")
    policy = config.get("policy", {})
    if policy:
        lines.extend(_cfg_render_policy_lines(policy, dropped_keys, rejections))
    lines.extend(_cfg_render_reviewer_lines(valid_reviewers))
    if rejections:
        print(
            f"WARNING: {len(rejections)} issue(s) found and NOT written: {'; '.join(rejections)}",
            file=sys.stderr,
        )
    return "\n".join(lines).rstrip("\n") + "\n"


def cfg_write_toml(path: str, config: dict) -> None:
    cache_write_text(path, cfg_render_toml(config))


def resolve_timeout_tiers(reviewer_entry: dict, policy: dict) -> list[int]:
    """A reviewer's own `extra.timeout_tiers` (set via review-spec.toml, e.g. a known-slow
    effort=high CLI/model combination) overrides the policy-wide default for that entry only.
    `policy` is expected to already carry a real `timeout_tiers` list (DEFAULT_POLICY guarantees
    this via cfg_resolve's own merge) -- this function never invents its own fallback constant,
    single source of truth stays DEFAULT_POLICY."""
    override = reviewer_entry.get("extra", {}).get("timeout_tiers")
    return override if override else policy["timeout_tiers"]
