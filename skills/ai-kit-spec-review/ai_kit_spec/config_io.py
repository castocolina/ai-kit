import contextlib
import fcntl
import os
import shlex
import sys

from ai_kit_spec import config_migrate, lane_effort, lane_settings, role_orders, toml_splice, trust
from ai_kit_spec.detection import REMOVED_RUNTIMES, RUNTIMES, removed_runtime_message, runtime_id

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
    if row is None:
        if "command" in result:
            return [f"{key}: cli={cli} is not in the runtime table; kept as a custom command entry"]
        result["runtime"] = rid
        return [f"{key}: cli={cli} is not in the runtime table and has no command; "
                "store a custom `command` lane for it"]
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


def _quiet_warn(_line) -> None:
    """Drop preview notes without recording their dedupe keys."""


def _note_once(label, line, warn_fn) -> None:
    """Emit one line per label in this process (the legacy-note dedupe)."""
    if warn_fn is _quiet_warn:
        return
    if label in _LEGACY_NOTED:
        return
    _LEGACY_NOTED.add(label)
    warn_fn(line)


def _emit_legacy_note(label, notes, warn_fn) -> None:
    """Emit one privacy-safe migration note per label in this process."""
    if notes:
        _note_once(label,
                   f"ai-kit-spec: {label}: legacy reviewer fields loaded in memory "
                   f"({'; '.join(notes)}); the file is unchanged -- re-save it with the "
                   "ai-kit-spec-config wizard or render-toml --out <file> --replace", warn_fn)


def cfg_local_path(cwd: str) -> str:
    """The project layer of ai-kit's config: ./.aikit/config.toml under cwd."""
    return os.path.join(cwd, ".aikit", "config.toml")


def cfg_config_base(env: dict) -> str:
    """${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit -- the base for ai-kit's own config files
    (the user config.toml and the trust store). HOME comes from env only, never from
    an ambient lookup, so an unset or empty HOME is an error rather than a guess: a repo could
    otherwise ship its own "global" config and trust store under the cwd (A-WR-01, C1-3). A
    whitespace-only XDG_CONFIG_HOME counts as unset (D-27); a relative one is ignored (XDG
    spec); no absolute home at all raises ConfigError (exit 2 in the CLI mains). The same rule
    as local_secrets, jev_review, tools/common_config and the runner
    (tests/test_config_dir_parity.py)."""
    xdg = env.get("XDG_CONFIG_HOME", "").strip()
    if os.path.isabs(xdg):
        return os.path.join(xdg, "ai-kit")
    home = env.get("HOME", "")
    if not os.path.isabs(home):
        raise ConfigError("$HOME", "no absolute home directory to hold ai-kit's config")
    return os.path.join(home, ".config", "ai-kit")


def cfg_trust_store_dir(env: dict) -> str:
    """Directory holding the trust records for project config.toml files whose command-bearing
    lanes were trusted (D-11, trust.py). Under ai-kit's own config base, never in the project."""
    return os.path.join(cfg_config_base(env), "config-trust")


def cfg_global_path(env: dict) -> str:
    """The user layer of ai-kit's config: ${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/config.toml."""
    return os.path.join(cfg_config_base(env), "config.toml")


class ConfigError(ValueError):
    """A config.toml exists but cannot be parsed (malformed TOML, non-UTF-8 bytes, a non-table
    [lanes], a failed roster migration, or no tomllib on this interpreter). Carries the path and the
    parser message; the CLI mains
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
    config.toml is the normal no-config state, never an error). Any OTHER problem
    raises ConfigError (D-11/R13): an existing malformed or non-UTF-8 file, an unreadable
    file, or tomllib missing on Python < 3.11. Unlike the renderer's never-raise
    loader, this module FAILS LOUDLY -- a silently-ignored broken config.toml would
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


def _drop_model_bound(base: dict, local: dict) -> None:
    """Drop settings for the old pair when a local entry changes or restates its variant."""
    moved = (any(local.get(field) is not None for field in _VARIANT_FIELDS)
             or ("model" in local and local["model"] != base.get("model")))
    if moved:
        for name in lane_settings.MODEL_BOUND:
            if name not in local:
                base.pop(name, None)


def cfg_merge_reviewers(global_list: list, local_list: list) -> list:
    """Merge [[reviewers]] by key: local fields override/extend matching
    global entries; local-only keys are appended; global-only keys are
    preserved unchanged. Order: global order first, then new local keys.
    A malformed entry with no `key` at all is silently skipped (never
    raises) — matches cfg_load_toml's "never raises on bad input"
    contract: one hand-written mistake in the roster must not crash
    the whole orchestrator. Model-bound settings are dropped first when the pair changes."""
    global_list = [r for r in global_list if "key" in r]
    local_list = [r for r in local_list if "key" in r]
    by_key = {r["key"]: dict(r) for r in global_list}
    for r in local_list:
        key = r["key"]
        if key in by_key:
            _drop_model_bound(by_key[key], r)
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


def cfg_lanes_table(doc: dict, path: str) -> dict:
    """The `[lanes]` table of a parsed config.toml; a missing one is {} (an empty roster)."""
    lanes = doc.get("lanes", {})
    if not isinstance(lanes, dict):
        raise ConfigError(path, "[lanes] must be a table")
    return lanes


def cfg_lanes_view(lanes: dict) -> dict:
    """The role lists of a [lanes] table plus the flat view callers still read (D-24): `reviewers`
    is the review lanes, then each execute lane whose key no review lane has. A lane is never
    merged across roles, so a key in both roles stays two entries in `review` and `execute`."""
    review = lanes["review"] if isinstance(lanes.get("review"), list) else []
    execute = lanes["execute"] if isinstance(lanes.get("execute"), list) else []
    review_keys = {entry["key"] for entry in review
                   if isinstance(entry, dict) and isinstance(entry.get("key"), str)}
    flat = review + [
        entry for entry in execute
        if not (isinstance(entry, dict) and isinstance(entry.get("key"), str)
                and entry["key"] in review_keys)
    ]
    view = {
        "policy": lanes["policy"] if isinstance(lanes.get("policy"), dict) else {},
        "reviewers": flat,
        "review": review,
        "execute": execute,
    }
    if "strategy" in lanes:
        view["strategy"] = lanes["strategy"]
    return view


def cfg_user_command_keys(lanes: dict) -> frozenset:
    """The `key` of every command-bearing lane entry in the user's roster (D-11). A project
    entry with the same key would override a command the user runs, so it joins the digest."""
    keys = set()
    for items in lanes.values():
        if not isinstance(items, list):
            continue
        for entry in items:
            if isinstance(entry, dict) and "command" in entry and isinstance(entry.get("key"), str):
                keys.add(entry["key"])
    return frozenset(keys)


def _read_legacy_lanes(new_path: str):
    """(lanes, raw bytes) of the pending old roster beside new_path; None when there is none."""
    try:
        return config_migrate.read_legacy(new_path)
    except config_migrate.LegacyRosterError as exc:
        raise ConfigError(exc.path, exc.message) from exc


def _user_lanes_readonly(env: dict) -> dict:
    """The user layer's lanes with nothing migrated or written: its config.toml [lanes], else a
    pending old roster's lanes."""
    path = cfg_global_path(env)
    lanes = cfg_lanes_table(cfg_load_toml(path), path)
    if lanes:
        return lanes
    found = _read_legacy_lanes(path)
    return found[0] if found is not None else {}


def cfg_project_trust_bytes(lanes: dict, env: dict) -> bytes | None:
    """The canonical bytes a project trust record pins (D-11): its command-bearing lane
    entries, plus the user's command keys unless the project is local-only (no user read)."""
    if lanes.get("strategy") == "local-only":
        keys = frozenset()
    else:
        keys = cfg_user_command_keys(_user_lanes_readonly(env))
    return trust.command_lanes_bytes(lanes, keys)


def cfg_confine_project_file(path: str, env: dict) -> None:
    """Refuse to read-modify-write a project layer file that leaves its `.aikit/` folder (CR-01).

    A cloned repo can ship `.aikit/config.toml` as a link to the user config.toml (or link its
    old roster file); a publish through it would plant lanes in the trust-free user layer. The
    user layer itself may be a link (dotfiles), so only project-layer callers use this guard."""
    folder = os.path.realpath(os.path.dirname(path))
    for name in (path, config_migrate.legacy_path(path)):
        if os.path.islink(name):
            raise ConfigError(name, "is a link; the project config is not migrated or written "
                                    "through a link (replace the link with a regular file)")
    real = os.path.realpath(path)
    if os.path.dirname(real) != folder or real == os.path.realpath(cfg_global_path(env)):
        raise ConfigError(path, "resolves outside the project's .aikit/ folder or onto the user "
                                "config; it is not migrated or written")


def _migrate(path: str, env: dict, warn_fn, project: bool) -> str:
    """Run config_migrate.migrate_layer on one layer; a failed migration is a ConfigError."""
    if project:
        cfg_confine_project_file(path, env)
    trust_dir = cfg_trust_store_dir(env) if project else None
    trust_bytes_fn = (lambda lanes: cfg_project_trust_bytes(lanes, env)) if project else None
    try:
        return config_migrate.migrate_layer(path, warn_fn=warn_fn, trust_dir=trust_dir,
                                            trust_bytes_fn=trust_bytes_fn,
                                            keep_backup=config_migrate.keep_backup_from_env(env))
    except config_migrate.LegacyRosterError as exc:
        raise ConfigError(exc.path, exc.message) from exc


def cfg_migrate_project(cwd: str, env: dict, warn_fn=None) -> str:
    """Move the project's old roster into config.toml (D-10); "none" when nothing is pending."""
    path = cfg_local_path(cwd)
    if config_migrate.pending(path) is None:
        return "none"
    return _migrate(path, env, warn_fn or _cfg_default_warn, project=True)


def cfg_migrate_user(env: dict, warn_fn=None) -> str:
    """Move the user layer's old roster into config.toml (D-10); user rosters carry no trust."""
    path = cfg_global_path(env)
    if config_migrate.pending(path) is None:
        return "none"
    return _migrate(path, env, warn_fn or _cfg_default_warn, project=False)


def cfg_migrate_target(path: str, env: dict, warn_fn=None) -> str:
    """Migrate the old roster beside the config.toml a write targets (D-10): as the user layer when
    that file sits in the user config folder, else as the project layer, with its trust carried."""
    emit = warn_fn or _cfg_default_warn
    in_user_dir = os.path.realpath(os.path.dirname(path)) == os.path.realpath(cfg_config_base(env))
    # A `.aikit/config.toml` path is a project layer even when `.aikit` links to the user config
    # folder (WR-102): the project guard then refuses it instead of writing the user file.
    named_project = os.path.basename(os.path.dirname(os.path.abspath(path))) == ".aikit"
    return _migrate(path, env, emit, project=named_project or not in_user_dir)


def cfg_trust_project(cwd: str, env: dict, warn_fn=None) -> tuple[str, str | None]:
    """Record trust for the project config.toml's command-bearing lanes (D-11), migrating it first.

    Returns (realpath, sha256 of the trusted bytes), or (realpath, None) with no trust needed."""
    cfg_migrate_project(cwd, env, warn_fn=warn_fn)
    path = cfg_local_path(cwd)
    if not os.path.exists(path):
        raise ConfigError(path, "no project config.toml")
    real = os.path.realpath(path)
    lanes = cfg_lanes_table(cfg_parse_toml_bytes(cfg_read_bytes(path), path), path)
    canonical = cfg_project_trust_bytes(lanes, env)
    if canonical is None:
        return real, None
    trust.record_trust(cfg_trust_store_dir(env), real, canonical)
    return real, trust.content_sha256(canonical)


def cfg_load_layers(cwd: str, env: dict) -> tuple[dict, dict]:
    """(project config.toml, user config.toml) parsed; no migration and no trust."""
    return cfg_load_toml(cfg_local_path(cwd)), cfg_load_toml(cfg_global_path(env))


def _table_at(doc: dict, table_path: tuple) -> dict:
    node = doc
    for part in table_path:
        node = node.get(part) if isinstance(node, dict) else None
        if not isinstance(node, dict):
            return {}
    return node


def cfg_layered_table(cwd: str, env: dict, *table_path: str) -> dict:
    """One ordinary table merged per key, project over user (for `[models]`, `[jev]`, `[hooks]`,
    `[runner]`). The trust-gated lanes go through cfg_resolve instead."""
    project, user = cfg_load_layers(cwd, env)
    return {**_table_at(user, table_path), **_table_at(project, table_path)}


def _untrusted_warning(local_path: str, cwd: str) -> str:
    return (
        f"ai-kit-spec: ignoring untrusted project-local config {local_path}; review its commands "
        f"with `ai-kit-spec.py trust-local --cwd {cwd} --show`, then trust it with "
        f"`ai-kit-spec.py trust-local --cwd {cwd}` (an edit to a command-bearing lane needs "
        "a new trust)"
    )


def _trusted_lanes(lanes: dict, local_path: str, cwd: str, env: dict, emit_warn) -> dict:
    """The project lanes when they need no trust or their canonical bytes are trusted, else {}."""
    canonical = cfg_project_trust_bytes(lanes, env)
    if canonical is None or trust.is_trusted(cfg_trust_store_dir(env),
                                             os.path.realpath(local_path), canonical):
        return lanes
    emit_warn(_untrusted_warning(local_path, cwd))
    return {}


def _pending_note(new_path: str, lanes: dict, emit_warn) -> None:
    """Report a pending old roster: it moves on the next read, or it is held because it names a
    removed runtime (39.1 D-03: no read migrates it), noted once per file."""
    legacy = config_migrate.legacy_path(new_path)
    if not cfg_names_removed_runtime(lanes):
        emit_warn(f"ai-kit-spec: migration pending: {legacy} moves to {new_path} on the next "
                  "command that reads the roster")
        return
    _note_once(f"migration held {legacy}",
               f"ai-kit-spec: migration held: {legacy} names a removed runtime, so no read moves "
               f"it to {new_path}; re-save its lanes with the ai-kit-spec-config wizard or "
               f"render-toml --out {new_path} --replace", emit_warn)


def cfg_legacy_project_trusted(local_path: str, lanes: dict, raw: bytes, env: dict) -> bool:
    """True when the pending old project roster beside local_path may be used: it needs no trust
    (D-11) or the old file is trusted under the old raw-byte rule."""
    canonical = cfg_project_trust_bytes(lanes, env)
    return canonical is None or trust.is_trusted(
        config_migrate.legacy_trust_dir(cfg_trust_store_dir(env)),
        os.path.realpath(config_migrate.legacy_path(local_path)), raw)


def _pending_project_lanes(cwd: str, local_path: str, env: dict, emit_warn) -> dict:
    """migrate=False: a pending old roster is read in memory and reported, never written. It is used
    when cfg_legacy_project_trusted allows it."""
    found = _read_legacy_lanes(local_path)
    if found is None:
        return {}
    lanes, raw = found
    _pending_note(local_path, lanes, emit_warn)
    if cfg_legacy_project_trusted(local_path, lanes, raw, env):
        return lanes
    emit_warn(_untrusted_warning(local_path, cwd))
    return {}


def _project_lanes(cwd: str, env: dict, emit_warn, migrate: bool) -> tuple[dict, str]:
    """The project layer's lanes as cfg_resolve may use them (empty when none, or untrusted), and
    the file they came from: its config.toml, or the pending old roster read in memory."""
    local_path = cfg_local_path(cwd)
    if os.path.exists(local_path):
        # Parsing happens BEFORE the trust check: a malformed file is reported (R13) whether or
        # not it is trusted -- parsing executes nothing.
        lanes = cfg_lanes_table(cfg_parse_toml_bytes(cfg_read_bytes(local_path), local_path),
                                local_path)
        if lanes:
            return _trusted_lanes(lanes, local_path, cwd, env, emit_warn), local_path
    if migrate:
        return {}, local_path
    lanes = _pending_project_lanes(cwd, local_path, env, emit_warn)
    return lanes, (config_migrate.legacy_path(local_path) if lanes else local_path)


def cfg_names_removed_runtime(lanes: dict) -> bool:
    """True when a [lanes] table holds a lane that names a removed runtime (39.1 D-03)."""
    return any(cfg_removed_runtime(entry) is not None for role in ("review", "execute")
               if isinstance(lanes.get(role), list) for entry in lanes[role])


def _legacy_names_removed(new_path: str) -> bool:
    """True when the pending old roster names a removed runtime; skip migration (39.1 D-03)."""
    found = _read_legacy_lanes(new_path)
    return found is not None and cfg_names_removed_runtime(found[0])


def cfg_resolve(cwd: str, env: dict, warn_fn=None, migrate: bool = True) -> dict:
    """Resolve the effective roster (D-10, D-11, D-24): the project config.toml's [lanes], migrated
    from an old roster file first unless migrate=False, merged over the user layer per role.

    The project [lanes] is used only when it has no command-bearing lane entry or its canonical
    bytes are trusted (trust.py); an untrusted one is ignored with a warning to warn_fn (default
    stderr). Parsing executes nothing, so a malformed file fails the same whether trusted or not.
    migrate=False reads a pending old roster in memory and writes nothing (--no-migrate).
    A pending old roster holding a lane that names a removed runtime is never migrated; it is read
    in memory like migrate=False (39.1 D-03)."""
    emit_warn = warn_fn if warn_fn is not None else _cfg_default_warn
    project_migrate = migrate and not _legacy_names_removed(cfg_local_path(cwd))
    if project_migrate:
        cfg_migrate_project(cwd, env, warn_fn=emit_warn)
    local, local_source = _project_lanes(cwd, env, emit_warn, project_migrate)
    return cfg_combine(local, env, warn_fn=emit_warn, local_path=local_source, migrate=migrate)


def cfg_resolve_quiet(cwd: str, env: dict) -> dict:
    """Resolve without migration or consuming another load's deduplicated notes."""
    return cfg_resolve(cwd, env, warn_fn=_quiet_warn, migrate=False)


def _combine_layers(local, global_cfg):
    """(reviewers, policy, (project notes, user notes, merge notes)) after strategy, legacy
    normalization and the route drop."""
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
    return merged, policy, (local_notes, global_notes, inferred_notes + route_notes)


def _pending_user_lanes(global_path: str, emit_warn) -> dict:
    """migrate=False: the user layer's pending old roster, read in memory and reported."""
    found = _read_legacy_lanes(global_path)
    if found is None:
        return {}
    _pending_note(global_path, found[0], emit_warn)
    return found[0]


def _user_lanes(env: dict, emit_warn, migrate: bool) -> tuple[dict, str]:
    """The user layer's [lanes] table, migrated first when migrate is true, else read as it is, and
    the file it came from: its config.toml, or the pending old roster read in memory."""
    global_path = cfg_global_path(env)
    migrate = migrate and not _legacy_names_removed(global_path)
    if migrate:
        cfg_migrate_user(env, warn_fn=emit_warn)
    lanes = cfg_lanes_table(cfg_load_toml(global_path), global_path)
    if lanes or migrate:
        return lanes, global_path
    lanes = _pending_user_lanes(global_path, emit_warn)
    return lanes, (config_migrate.legacy_path(global_path) if lanes else global_path)


def cfg_removed_runtime(entry: object) -> str | None:
    """The removed runtime named by a raw lane's runtime, cli or native_runtime (39.1 D-03)."""
    if not isinstance(entry, dict):
        return None
    for field in ("runtime", "cli"):
        rid = entry.get(field)
        if isinstance(rid, str) and rid in REMOVED_RUNTIMES:
            return rid
    rid = entry.get("native_runtime")
    if (isinstance(rid, str) and rid in REMOVED_RUNTIMES
            and entry.get("runtime") is None and entry.get("cli") is None):
        return rid
    return None


def _pin_removed(lanes: dict) -> dict:
    """Pin removed variants before merging, without legacy fields or stored routes (39.1 A2)."""
    pinned = dict(lanes)
    for role in ("review", "execute"):
        if isinstance(lanes.get(role), list):
            entries = []
            for entry in lanes[role]:
                rid = cfg_removed_runtime(entry)
                if rid is not None:
                    entry = {**{k: v for k, v in entry.items()
                                if k not in ("cli", "command", "native_runtime", "route")},
                             "runtime": rid}
                entries.append(entry)
            pinned[role] = entries
    return pinned


def _drop_removed_lanes(roles: dict, project_view: dict, paths: tuple,
                        emit_warn) -> tuple[dict, dict]:
    """Drop removed lanes after merging and note each role and key once (39.1 D-03), labelled with
    the file that holds the lane: paths is (project file, user file), and the project file is named
    when its own entry names the removed runtime (it wins the merge), else the user file."""
    kept, removed = {}, {}
    for role in ("review", "execute"):
        project_keys = {entry.get("key") for entry in project_view.get(role, [])
                        if cfg_removed_runtime(entry) is not None}
        kept[role], keys = [], set()
        for entry in roles[role]:
            rid = cfg_removed_runtime(entry)
            if rid is None:
                kept[role].append(entry)
                continue
            key = entry.get("key")
            if isinstance(key, str):
                keys.add(key)
            note_label = f"{paths[0] if key in project_keys else paths[1]} [{role} {key}]"
            _note_once(note_label, f"ai-kit-spec: {note_label}: {removed_runtime_message(rid)}; "
                       "this lane is skipped and the file is unchanged", emit_warn)
        removed[role] = frozenset(keys)
    return kept, removed


def _combine_role(local_view: dict, global_view: dict, role: str, local_only: bool) -> list:
    """One role's merged lanes (D-24): the same layering as the flat view, per role, so a lane under
    `review` never merges with a lane under `execute`."""
    global_list, _ = normalize_legacy_reviewers(global_view.get(role, []))
    if not local_view:
        merged = global_list
    else:
        local_list, _ = normalize_legacy_reviewers(local_view.get(role, []))
        merged = local_list if local_only else cfg_merge_reviewers(global_list, local_list)
    merged, _ = infer_legacy_native(merged)
    merged, _ = _drop_stored_routes(merged)
    return merged


def _combine_roles(roles: dict, policy: dict, project_view: dict, paths: tuple,
                   emit_warn) -> dict:
    """Each role's merged lanes and order (36 D-04).

    Lanes naming a removed runtime are dropped first (39.1 D-03).
    It prints one warning per role whose usage_limited lanes have no selectable lane to fall
    back to (36 D-17).
    """
    roles, removed = _drop_removed_lanes(roles, project_view, paths, emit_warn)
    result = {**roles, "orders": role_orders.role_orders(policy, roles, emit_warn, removed)}
    for line in lane_settings.fallback_warnings(roles, result["orders"]):
        emit_warn(line)
    return result


def cfg_combine(local: dict, env: dict, warn_fn=None, local_path=None,
                migrate: bool = True) -> dict:
    """Combine an already-trusted (or empty) project [lanes] table with the user layer, honoring
    the local `strategy`. Shared by cfg_resolve and `trust-local --show`, so the consent display
    renders the same merged entries dispatch would run. Returns the flat `reviewers` view plus the
    `review` and `execute` lists (D-24), and `orders`, each role's priority order (36 D-04).
    local_path names the file the project lanes came from (a note label)."""
    emit_warn = warn_fn if warn_fn is not None else _cfg_default_warn
    # A local-only project never consults the user file, so it is never read (B-WR-01).
    local_only = bool(local) and local.get("strategy") == "local-only"
    user_lanes, user_path = (({}, cfg_global_path(env)) if local_only
                             else _user_lanes(env, emit_warn, migrate))
    local_view = cfg_lanes_view(_pin_removed(local)) if local else {}
    global_view = cfg_lanes_view(_pin_removed(user_lanes))
    merged, policy, notes = _combine_layers(local_view, global_view)
    if local:
        _emit_legacy_note(local_path or "project config.toml", notes[0], emit_warn)
    _emit_legacy_note(cfg_global_path(env), notes[1], emit_warn)
    _emit_legacy_note(f"merged lanes ({local_path or 'local'}, {cfg_global_path(env)})",
                      notes[2], emit_warn)
    roles = {role: _combine_role(local_view, global_view, role, local_only)
             for role in ("review", "execute")}
    return {"policy": policy,
            "reviewers": [entry for entry in merged if cfg_removed_runtime(entry) is None],
            **_combine_roles(roles, policy, local_view,
                             (local_path or "project config.toml", user_path), emit_warn)}


_VALID_PURPOSE = {"review", "execute", "both"}
_LEGACY_WRITE_FIELDS = ("cli", "native_runtime")


def _validate_pair_fields(entry: dict, key) -> str | None:
    """Save is strict: a runtime must be a table row and carry a model, a command only exists
    on a custom entry, and a pinned model needs a runtime. Load stays lenient."""
    runtime = entry.get("runtime")
    if "runtime" in entry and runtime is not None:
        removed = removed_runtime_message(runtime)
        if removed is not None or not isinstance(runtime, str) or runtime not in RUNTIMES:
            message = removed if removed is not None else (
                f"runtime {runtime!r} is not in the runtime table; "
                "store a custom `command` lane instead (no 'runtime')")
            return f"{key}: {message}"
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
    """The roster-side sibling of model_catalog.validate_catalog_entry (design spec
    2026-09-02 Section 5: "enforced in both render-toml and the new fetch-model-catalog
    subcommand"). Checks purpose/is_router/fallback_quota, then effort, lane settings and pair
    rules: a table runtime needs a model, a command is custom-only, and a pinned model needs a
    runtime."""
    key = entry.get("key", "<unknown>")
    # WR-03 fix: a dict-valued field must not reach the writer as a quoted TOML string (e.g. a
    # hand-edited `extra = { timeout_tiers = [...] }`, a known constraint of this schema), so
    # reject it here, up front, for EVERY field. It then surfaces through the rejections/WARNING
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
    return (lane_effort.effort_problem(entry)
            or lane_settings.validate_lane_settings(entry, key)
            or _validate_pair_fields(entry, key))


def _cfg_partition_reviewers(reviewers: list) -> tuple[list, list, set]:
    rejections = []
    valid_reviewers = []
    dropped_keys = set()
    for r in reviewers:
        reason = validate_reviewer_fields(r) or lane_settings.write_problem(r)
        if reason:
            rejections.append(reason)
            if "key" in r:
                dropped_keys.add(r["key"])
            continue
        valid_reviewers.append(r)
    return valid_reviewers, rejections, dropped_keys


def _cfg_render_reviewers(entries: list) -> tuple[list, list[str]]:
    """The two load steps, in the same order, so a write holds only the new form.

    A stored route is NOT dropped here: save rejects it, so the entry stays intact for
    validate_reviewer_fields to refuse. Load drops it instead. The lane settings' display lines
    are cleaned before validation (36 D-16, D-23)."""
    reviewers, notes = normalize_legacy_reviewers(entries)
    reviewers, inferred = infer_legacy_native(reviewers)
    reviewers = [lane_settings.normalise_lane_settings(entry) if isinstance(entry, dict) else entry
                 for entry in reviewers]
    return reviewers, notes + inferred


_RENAMED_REVIEWERS = (
    "render-toml: the JSON key 'reviewers' is now 'lanes' "
    "(each entry's purpose picks its role: review, execute or both)"
)
_LADDER_COMMENT_HEAD = "# Priority fallback order"
_FLAT_LADDER_NOTE = ("ai-kit-spec: render-toml: the flat policy ladder is written as one order "
                     "per role ([lanes.policy.review], [lanes.policy.execute])")


def _ladder_comment_lines(role: str, ladder: list, double: bool) -> list[str]:
    """The generated comment above a role table naming its fallback order."""
    if not ladder:
        return []
    tail = ("# primary slot; double mode also seats an independent secondary):"
            if double and role == "review" else "# primary slot):")
    return [f"{_LADDER_COMMENT_HEAD}, {role} lanes (first available wins the", tail,
            *(f"#   {number}. {lane_settings.clean_note(str(key))}"
              for number, key in enumerate(ladder, 1))]


def _refresh_ladder_comment(text: str, path: tuple, generated_lines: list) -> str:
    """Keep the generated fallback-order comment above the table at `path` in step with its ladder.

    The contiguous comment lines directly above the header are the generated block when the first
    one starts with _LADDER_COMMENT_HEAD: the block is replaced by the lines for the ladder now
    written (none when the ladder is empty). With no comment above, the block is inserted. A user's
    own comment there is left alone. Comments never change a parsed value."""
    blocks = toml_splice.split_blocks(text)
    index = next((number for number, block in enumerate(blocks)
                  if not block.array and block.path == path), None)
    if index is None:
        return text
    block = blocks[index]
    lead = block.lines[: block.lead]
    if lead and not lead[0].startswith(_LADDER_COMMENT_HEAD):
        return text
    newline = "\r\n" if "\r\n" in text else "\n"
    generated = [line + newline for line in generated_lines]
    if generated == lead:
        return text
    rewritten = [*generated, *block.lines[block.lead:]]
    lines: list[str] = []
    for number, item in enumerate(blocks):
        lines.extend(rewritten if number == index else item.lines)
    return "".join(lines)


def _refresh_ladder_comments(text: str, policy: dict) -> str:
    """Refresh generated comments for the policy and its role tables."""
    text = _refresh_ladder_comment(text, ("lanes", "policy"), [])
    for role in role_orders.ROLES:
        table = policy.get(role)
        if not isinstance(table, dict):
            table = {}
        text = _refresh_ladder_comment(text, ("lanes", "policy", role),
                                       _ladder_comment_lines(role, table.get("ladder") or [],
                                                             policy.get("mode") == "double"))
    return text


def _ladder_drops(source: list, keep: set, dropped: set) -> tuple[list, list]:
    rejected = sorted({key for key in source if isinstance(key, str) and key in dropped})
    unknown = sorted({key if isinstance(key, str) else repr(key) for key in source
                      if not (isinstance(key, str) and (key in keep or key in dropped))})
    return rejected, unknown


def _report_drops(label: str, noun: str, drops: tuple, rejections: list) -> None:
    rejected, unknown = drops
    if rejected:
        rejections.append(
            f"{label}: dropped dangling reference(s) to rejected lane key(s) {rejected}")
    if unknown:
        rejections.append(f"{label}: dropped key(s) naming no {noun} {unknown}")


def _role_source(role: str, raw, legacy: list, rejections: list) -> tuple[dict, list]:
    """Return the role table's other keys and source order, or the legacy order."""
    if raw is None:
        return {}, legacy
    if not isinstance(raw, dict) or not isinstance(raw.get("ladder"), list):
        rejections.append(f"policy.{role}: needs a table with a 'ladder' list; not written")
        return {}, []
    return {k: v for k, v in raw.items() if k != "ladder"}, raw["ladder"]


def _cfg_lanes_policy(policy, dropped_keys: set, rejections: list, role_keys: dict) -> dict | None:
    """Write flat keys and nonempty per-role orders, filtering rejected and unknown lanes."""
    if not policy:
        return None
    legacy = policy.get("ladder", [])
    if not isinstance(legacy, list):
        rejections.append("policy.ladder: not a list; not written")
        legacy = []
    if legacy:
        print(_FLAT_LADDER_NOTE, file=sys.stderr)
        _report_drops("policy.ladder", "lane", _ladder_drops(
            legacy, role_keys["review"] | role_keys["execute"], dropped_keys), rejections)
    written = {k: v for k, v in policy.items() if k != "ladder" and k not in role_orders.ROLES}
    for role in role_orders.ROLES:
        extra, source = _role_source(role, policy.get(role), legacy, rejections)
        if policy.get(role) is not None:
            _report_drops(f"policy.{role}.ladder", f"{role} lane",
                          _ladder_drops(source, role_keys[role], dropped_keys), rejections)
        ladder = list(dict.fromkeys(key for key in source
                                    if isinstance(key, str) and key in role_keys[role]))
        if ladder:
            written[role] = {**extra, "ladder": ladder}
    return written or None


def _current_lanes(text: str) -> dict:
    """The [lanes] table the text holds ({} for no text); broken TOML is a ConfigError."""
    if not text:
        return {}
    return cfg_lanes_table(cfg_parse_toml_bytes(text.encode("utf-8"), "render-toml target"),
                           "render-toml target")


def _splice_policy(text: str, old, policy: dict) -> str:
    """Splice flat policy keys and role tables, removing obsolete or inline roles."""
    old = old if isinstance(old, dict) else {}
    flat, roles = role_orders.split_policy(policy)
    headed = {block.path[2] for block in toml_splice.split_blocks(text)
              if not block.array and len(block.path) == 3 and block.path[:2] == ("lanes", "policy")}
    gone = tuple(name for name in old if name not in flat
                 and not (name in role_orders.ROLES and name in headed))
    if flat or gone:
        text = toml_splice.set_table(text, ("lanes", "policy"), flat, remove=gone)
    for role in role_orders.ROLES:
        path = ("lanes", "policy", role)
        if role in roles:
            own = old.get(role) if role in headed else {}
            if not isinstance(own, dict):
                own = {}
            text = toml_splice.set_table(
                text, path, roles[role],
                remove=tuple(name for name in own if name not in roles[role]))
        elif role in headed:
            text = toml_splice.remove_table(text, path)
    return text


def _splice_roster(text: str, current: dict, parts: dict) -> str:
    """The roster parts spliced into the text one table or array at a time (D-08)."""
    strategy, policy = parts["strategy"], parts["policy"]
    if strategy is not None:
        text = toml_splice.set_table(text, ("lanes",), {"strategy": strategy})
    elif "strategy" in current:
        text = toml_splice.set_table(text, ("lanes",), {}, remove=("strategy",))
    if policy is not None:
        text = _splice_policy(text, current.get("policy"), policy)
    elif "policy" in current:
        text = toml_splice.remove_table(text, ("lanes", "policy"))
    text = toml_splice.set_array(text, ("lanes", "review"), parts["review"] or [])
    text = toml_splice.set_array(text, ("lanes", "execute"), parts["execute"] or [])
    return _refresh_ladder_comments(text, policy or {})


def _expected_lanes(current: dict, parts: dict) -> dict:
    """The [lanes] table a write must hold: current, with each part set (dropped when None)."""
    lanes = dict(current)
    for name, value in parts.items():
        if value is None:
            lanes.pop(name, None)
        else:
            lanes[name] = value
    return lanes


def _written_fallback_warnings(policy, review: list, execute: list) -> list[str]:
    """The reader's no-fallback lines for the roster as written, in its written order."""
    tables = policy or {}
    orders = {role: tables[role]["ladder"] if isinstance(tables.get(role), dict) else []
              for role in role_orders.ROLES}
    return lane_settings.fallback_warnings({"review": review, "execute": execute}, orders)


def cfg_render_lanes(config: dict, existing_text: str = "") -> str:
    """Set the [lanes] roster to `config` in config.toml text; every other byte is kept (D-08).

    `config` is {"strategy"?, "policy"?, "lanes": [entry, ...]}. Each entry's `purpose` picks its
    role (D-24). Entries are normalised and validated as before: a rejected one is dropped with a
    WARNING line on stderr. Only the roster parts are spliced: `strategy`, [lanes.policy] flat
    keys, [lanes.policy.review] and [lanes.policy.execute] orders, and the role arrays.
    Usage-limited lanes without a fallback are written and get the reader's warning (36 D-17).
    Raises ValueError for a JSON still keyed 'reviewers', and ConfigError for invalid TOML."""
    if "reviewers" in config:
        raise ValueError(_RENAMED_REVIEWERS)
    entries, notes = _cfg_render_reviewers(config.get("lanes", []))
    if notes:
        print("ai-kit-spec: render-toml: migrated legacy fields before writing "
              f"({'; '.join(notes)})", file=sys.stderr)
    valid, rejections, dropped = _cfg_partition_reviewers(entries)
    review, execute = config_migrate.split_by_purpose(valid)
    parts = {
        "strategy": config.get("strategy"),
        "policy": _cfg_lanes_policy(config.get("policy"), dropped, rejections,
                                    {"review": {entry.get("key") for entry in review},
                                     "execute": {entry.get("key") for entry in execute}}),
        "review": review or None,
        "execute": execute or None,
    }
    current = _current_lanes(existing_text)
    text = _splice_roster(existing_text, current, parts)
    if _current_lanes(text) != _expected_lanes(current, parts):
        raise ConfigError("render-toml target", "the written roster does not match")
    if rejections:
        print(f"WARNING: {len(rejections)} issue(s) found and NOT written: {'; '.join(rejections)}",
              file=sys.stderr)
    for line in _written_fallback_warnings(parts["policy"], review, execute):
        print(line, file=sys.stderr)
    return text


@contextlib.contextmanager
def cfg_folder_lock(path: str):
    """Exclusive folder lock for a config read-modify-write, shared by both writers.

    No lock file is created; a folder made only for the lock is removed again while it is empty
    (a refused or failed write leaves nothing behind).
    """
    folder = os.path.dirname(os.path.abspath(path))
    created = not os.path.isdir(folder)
    os.makedirs(folder, exist_ok=True)
    fd = os.open(folder, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        if created:
            with contextlib.suppress(OSError):
                os.rmdir(folder)  # fails, and keeps the folder, once a write put a file in it


def cfg_write_toml(path: str, config: dict) -> None:
    """Write the roster into the config.toml at path through the splicer (D-08). A broken target is
    a ConfigError before anything is written; the publish is atomic."""
    with cfg_folder_lock(path):
        existing = ""
        if os.path.exists(path):
            raw = cfg_read_bytes(path)
            cfg_parse_toml_bytes(raw, path)
            existing = raw.decode("utf-8")
        toml_splice.publish(path, cfg_render_lanes(config, existing))


def resolve_timeout_tiers(reviewer_entry: dict, policy: dict) -> list[int]:
    """A reviewer's own `extra.timeout_tiers` (set in the config.toml lanes, e.g. a known-slow
    effort=high CLI/model combination) overrides the policy-wide default for that entry only.
    `policy` is expected to already carry a real `timeout_tiers` list (DEFAULT_POLICY guarantees
    this via cfg_resolve's own merge) -- this function never invents its own fallback constant,
    single source of truth stays DEFAULT_POLICY."""
    override = reviewer_entry.get("extra", {}).get("timeout_tiers")
    return override if override else policy["timeout_tiers"]
