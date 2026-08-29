#!/usr/bin/env python3
"""review-spec cross-AI reviewer support: config (TOML), cache (JSON),
runtime/CLI detection, policy resolution, and cross-reviewer findings
merge. Stdlib-only, no external dependencies (see pyproject.toml)."""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time

try:
    import tomllib as _tomllib_impl
    tomllib = _tomllib_impl
except ModuleNotFoundError:        # Python < 3.11 — degrade to env-only config.
    tomllib = None  # type: ignore[assignment]  # stdlib boundary: optional module absent on <3.11

from typing import NamedTuple

# ── Config (TOML) ────────────────────────────────────────────────────────

DEFAULT_POLICY = {"mode": "single", "ladder": []}


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


def cfg_render_toml(config: dict) -> str:
    """Hand-rolled TOML serializer for this schema only (an optional
    top-level `strategy` string, a flat [policy] table, and an
    array-of-tables [[reviewers]] with flat string/bool/list values) —
    tomllib is read-only in stdlib, and adding a writer dependency would
    break this repo's zero-dependency runtime."""
    lines = []
    if "strategy" in config:
        lines.append(f"strategy = {_toml_value(config['strategy'])}")
        lines.append("")
    policy = config.get("policy", {})
    if policy:
        ladder = policy.get("ladder") or []
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
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")
    for r in config.get("reviewers", []):
        lines.append("[[reviewers]]")
        for k, v in r.items():
            lines.append(f"{k} = {_toml_value(v)}")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def cfg_write_toml(path: str, config: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(cfg_render_toml(config))


# ── Cache (JSON) ─────────────────────────────────────────────────────────

RUNTIMES_TTL_SECONDS = 30 * 24 * 3600   # ~30 days: CLI/model presence is near-static
QUOTA_TTL_SECONDS = 3600                 # 1 hour: quota/context headroom is highly dynamic


def cache_base(env: dict) -> str:
    """${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit/review-spec."""
    base = env.get("XDG_CACHE_HOME") or os.path.join(env.get("HOME", ""), ".cache")
    return os.path.join(base, "ai-kit", "review-spec")


def cache_runtimes_path(env: dict) -> str:
    return os.path.join(cache_base(env), "runtimes.json")


def cache_quota_path(env: dict) -> str:
    return os.path.join(cache_base(env), "quota.json")


def cache_read_json(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def cache_write_json(path: str, data: dict) -> None:
    """Atomic write (tmp file + os.replace) so a crash mid-write never
    leaves a half-written cache file for the next reader."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def cache_is_stale(path: str, ttl_seconds: int) -> bool:
    try:
        return time.time() - os.stat(path).st_mtime >= ttl_seconds
    except OSError:
        return True


# ── Runtime/CLI detection ───────────────────────────────────────────────

KNOWN_CLIS = ("claude", "codex", "opencode", "grok", "cursor-agent", "gemini")


def detect_installed_clis(which_fn=shutil.which) -> dict:
    """{cli_name: absolute_path_or_None} for each KNOWN_CLIS entry."""
    return {cli: which_fn(cli) for cli in KNOWN_CLIS}


def detect_opencode_models(binary: str, run_fn=subprocess.run) -> list:
    """Runs `<binary> models`; one model id per non-blank line. opencode is
    the only known-installed multi-provider CLI today (confirmed live:
    lists opencode-go/kimi-k3, opencode-go/qwen3.8-max, opencode-go/grok-4.6,
    etc. under its own routing) — other CLIs name their model directly on
    invocation with no separate list subcommand to parse."""
    try:
        result = run_fn([binary, "models"], capture_output=True, text=True,
                         check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]


def detect_cursor_agent_models(binary: str, run_fn=subprocess.run) -> list:
    """Runs `<binary> models`; each line is `<id> - <display name>` after
    a header ("Available models") and a blank line — confirmed live
    against a real authenticated install (2026.08.25-3e8eec8). Returns
    just the ids (before ` - `), skipping the header/blank lines and any
    line with no ` - ` separator (defensive — a format change should
    degrade to an empty/partial list here, never crash detection)."""
    try:
        result = run_fn([binary, "models"], capture_output=True, text=True,
                         check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return []
    models = []
    for ln in result.stdout.splitlines():
        ln = ln.strip()
        if " - " not in ln:
            continue
        models.append(ln.split(" - ", 1)[0].strip())
    return models


# Tier/quality/mode tokens known to appear as trailing, hyphen-joined
# suffixes on a model id across the CLIs this design has seen so far
# (confirmed live, cursor-agent's ~204-id catalog: e.g.
# "claude-opus-5-thinking-high-fast" is the "claude-opus-5" family with
# thinking+high+fast suffixes). This list is a snapshot, not a closed
# set — new CLIs/providers will invent new tier vocabulary this can't
# recognize, so group_models_by_family degrades gracefully (an
# unrecognized-suffix id just becomes its own single-member "family")
# rather than raising. It is a grouping AID for a human/wizard to skim a
# long catalog faster, never a substitute for actually reading the ids.
_MODEL_TIER_SUFFIXES = (
    "thinking", "low", "medium", "high", "xhigh", "max", "none", "fast",
)


def group_models_by_family(models: list) -> dict:
    """Collapses tier/effort/mode variants of the same base model into one
    group, e.g. ["claude-opus-5-high", "claude-opus-5-high-fast",
    "claude-opus-5-low"] -> {"claude-opus-5": [...three ids...]}. Strips
    only a TRAILING run of tokens from `_MODEL_TIER_SUFFIXES` (hyphen-
    joined) off the end of each id — an id with no such trailing run
    becomes its own family unchanged (e.g. "auto", "composer-2.5"). This
    is a best-effort heuristic over a live-fetched, presumably-current
    catalog — it does not know which family is "newest" or "best" for
    any purpose; that judgment belongs to whoever (or whatever, e.g. a
    wizard doing live research on an unfamiliar name) is choosing among
    the returned families, not to this function. Preserves each model's
    original relative order within its group and preserves the order
    families are first seen in `models`."""
    groups = {}
    for model in models:
        parts = model.split("-")
        cut = len(parts)
        while cut > 1 and parts[cut - 1] in _MODEL_TIER_SUFFIXES:
            cut -= 1
        family = "-".join(parts[:cut]) or model
        groups.setdefault(family, []).append(model)
    return groups


def build_runtimes_snapshot(which_fn=shutil.which, run_fn=subprocess.run) -> dict:
    """{"clis": {name: {"installed": bool, "path"?: str, "models"?: [str]}}}.
    Pure function — the caller (this module's CLI entrypoint) decides
    whether/where to persist this via cache_write_json."""
    installed = detect_installed_clis(which_fn=which_fn)
    snapshot = {"clis": {}}
    for cli, binpath in installed.items():
        if not binpath:
            snapshot["clis"][cli] = {"installed": False}
            continue
        entry = {"installed": True, "path": binpath}
        if cli == "opencode":
            entry["models"] = detect_opencode_models(binpath, run_fn=run_fn)
        elif cli == "cursor-agent":
            entry["models"] = detect_cursor_agent_models(binpath, run_fn=run_fn)
        snapshot["clis"][cli] = entry
    return snapshot


# ── Vendor inference ─────────────────────────────────────────────────────

# Longest/most-specific prefix first within each group — "cursor-grok-"
# must be checked before any bare "grok-" entry would be (there isn't one
# here: the standalone `grok` CLI is single-vendor by construction, so it
# never needs this table). opencode's ids are namespaced "<provider>/...";
# cursor-agent's are bare, vendor-prefixed strings with no separator.
_MODEL_VENDOR_PREFIXES = (
    ("opencode-go/kimi", "moonshot"),
    ("opencode-go/qwen", "alibaba"),
    ("opencode-go/grok", "xai"),
    ("opencode-go/gpt", "openai"),
    ("cursor-grok-", "xai"),
    ("claude-", "anthropic"),
    ("gpt-", "openai"),
    ("glm-", "zhipu"),
    ("kimi-", "moonshot"),
    ("gemini-", "google"),
    ("composer-", "cursor"),
)


def infer_vendor_from_model(model: str) -> str | None:
    """Deterministic best-effort vendor lookup from a model id's known
    prefix. Returns None when no prefix matches (e.g. `ollama-cloud/*`,
    `auto`, or an id this table hasn't seen yet) — the caller
    (review-spec-config) must ask the user to confirm/supply the vendor
    explicitly in that case, never guess further or fall back to a
    default vendor."""
    for prefix, vendor in _MODEL_VENDOR_PREFIXES:
        if model.startswith(prefix):
            return vendor
    return None


# ── Policy resolution ────────────────────────────────────────────────────

class ResolvedReviewer(NamedTuple):
    """A reviewer chosen for this run. cli/command are None for native
    (current-runtime) dispatch. model == "" means "no override — inherit
    the current session's own default model" (never a hardcoded name).
    extra holds any reviewer-entry fields beyond key/model/vendor/cli/
    command (e.g. effort, service_tier) for the caller to interpolate into
    `command`."""

    key: str
    model: str
    vendor: str
    cli: str | None
    command: str | None
    extra: dict


NO_CONFIG_FALLBACK = ResolvedReviewer(key="session-default", model="", vendor="",
                                       cli=None, command=None, extra={})

_KNOWN_REVIEWER_FIELDS = {"key", "model", "vendor", "cli", "command"}


def _reviewer_by_key(reviewers: list, key: str) -> dict | None:
    for r in reviewers:
        if r.get("key") == key:
            return r
    return None


def _to_resolved(entry: dict) -> ResolvedReviewer:
    """entry["key"] is always present here — every caller reaches this via
    _reviewer_by_key, which already filters by key. entry.get("model", "")
    tolerates a config entry that forgot to set model (never raises); an
    empty model is already a valid sentinel elsewhere in this module (see
    ResolvedReviewer's docstring) — "no override"."""
    return ResolvedReviewer(
        key=entry["key"], model=entry.get("model", ""), vendor=entry.get("vendor", ""),
        cli=entry.get("cli"), command=entry.get("command"),
        extra={k: v for k, v in entry.items() if k not in _KNOWN_REVIEWER_FIELDS},
    )


def _has_quota(quota: dict, key: str) -> bool:
    """No entry -> never probed / no probe support for this CLI yet ->
    assume available (never block a review on the ABSENCE of quota data)."""
    entry = quota.get(key)
    if entry is None:
        return True
    return entry.get("available", True)


def resolve_ladder_pick(reviewers: list, ladder: list, skip_vendor: str, quota: dict,
                         allow_same_vendor_fallback: bool = True) -> ResolvedReviewer | None:
    """First ladder entry that (a) exists in `reviewers`, (b) has a
    different vendor than skip_vendor (empty skip_vendor disables this
    filter — used for "best overall, any vendor"), and (c) has quota. If
    nothing survives both filters and `allow_same_vendor_fallback` is True
    (the default), retry ignoring the vendor filter (same-vendor coverage
    beats no reviewer at all) — this is `single` mode's behavior, and
    `double` mode's PRIMARY slot (whose `skip_vendor` is always `""`
    anyway, so the fallback never actually triggers there). None only if
    every candidate lacks quota or doesn't exist.

    Pass `allow_same_vendor_fallback=False` for `double` mode's SECONDARY
    slot specifically: the design's guarantee for that slot is "a
    cross-vendor alternate, dropped (not substituted) if none survives" —
    silently degrading to a same-vendor pick there would run two
    same-vendor reviewers under a "double review" banner while billing a
    second CLI call for zero independent perspective.

    This is where tier-awareness comes from: a caller passing an ordered
    ladder like ["claude-opus", "claude-sonnet", ...] gets the flagship
    tier whenever it has quota, and falls through to the next configured
    tier automatically otherwise — no separate "tier" concept needed."""
    for key in ladder:
        entry = _reviewer_by_key(reviewers, key)
        if entry is None or not _has_quota(quota, key):
            continue
        if skip_vendor and entry.get("vendor") == skip_vendor:
            continue
        return _to_resolved(entry)
    if not allow_same_vendor_fallback:
        return None
    for key in ladder:
        entry = _reviewer_by_key(reviewers, key)
        if entry is None or not _has_quota(quota, key):
            continue
        return _to_resolved(entry)
    return None


def _native_ladder(reviewers: list, ladder: list) -> list:
    """The sub-list of `ladder` whose keys resolve to a cli-less
    (native/current-runtime) reviewer entry, order preserved. Used to keep
    double mode's baseline guaranteed-native (see resolve_reviewers)."""
    result = []
    for key in ladder:
        entry = _reviewer_by_key(reviewers, key)
        if entry is not None and not entry.get("cli"):
            result.append(key)
    return result


def resolve_reviewers(config: dict, quota: dict, source_vendor: str, cross_ai: bool) -> list:
    """The full policy decision, including double mode's
    native-baseline guarantee. Returns 1 or 2 ResolvedReviewer entries;
    dispatch mechanics are the caller's concern (review-spec/SKILL.md's
    Step 1), this only decides WHO.

    single: one reviewer, preferring a vendor different from source_vendor
    (independent perspective on the document), quota-aware, tier-aware via
    ladder order.

    double: `primary` walks ONLY the ladder's native (cli-less) entries —
    tier-aware within that restricted set, guaranteed to never be an
    external entry, falling back to NO_CONFIG_FALLBACK if no native entry
    is configured or none has quota (never zero reviewers, and never a
    promoted external entry standing in for the baseline). `secondary` is
    the best entry anywhere in the FULL ladder with a vendor DIFFERENT
    from primary's — or, when primary is NO_CONFIG_FALLBACK (whose vendor
    is unknown, `""`), different from `source_vendor` instead, since an
    unknown-vendor filter is no filter at all and would defeat the
    cross-vendor guarantee exactly when there's no configured native
    entry to compare against — dropped (not substituted) if none
    survives (a native-only, or all-same-vendor, ladder degrades to a
    single reviewer, not an error).

    Either mode falls back to NO_CONFIG_FALLBACK when --no-cross-ai was
    passed, the ladder is empty, or nothing in it has quota."""
    if not cross_ai:
        return [NO_CONFIG_FALLBACK]
    policy = config.get("policy", {})
    mode = policy.get("mode", "single")
    ladder = policy.get("ladder", [])
    reviewers = config.get("reviewers", [])
    if mode == "double":
        primary = resolve_ladder_pick(reviewers, _native_ladder(reviewers, ladder),
                                       skip_vendor="", quota=quota)
        if primary is None:
            primary = NO_CONFIG_FALLBACK
        secondary_skip_vendor = primary.vendor or source_vendor
        secondary = resolve_ladder_pick(
            reviewers, ladder, skip_vendor=secondary_skip_vendor, quota=quota,
            allow_same_vendor_fallback=False,
        )
        if secondary is None or secondary.key == primary.key:
            return [primary]
        return [primary, secondary]
    pick = resolve_ladder_pick(reviewers, ladder, skip_vendor=source_vendor, quota=quota)
    return [pick] if pick else [NO_CONFIG_FALLBACK]


# ── Command building (Strategy/Factory, one builder per CLI) ────────────

# Every CLI has its own real syntax for reasoning-effort/service-tier/
# execution-mode knobs — codex wants two separate `-c key='"val"'` flags,
# cursor-agent encodes effort/fast/context as bracket-parameter overrides
# on the --model argument itself, others take no such knob at all today.
# Hand-writing that per-CLI quoting into a review-spec.toml `command`
# string (the old approach) pushed CLI-specific knowledge onto whoever
# configures a reviewer; centralizing it here means review-spec-config's
# setup wizard (and `build-command`/`build-model-id`, its CLI entrypoints
# below) only ever has to pass structured params, never hand-transcribe
# a quoting idiom. Each builder returns a `command`-template STRING with
# {model}/{prompt} left as literal placeholders — render_reviewer_command
# (below) fills those at dispatch time from the reviewer entry's own
# stored `model` and the real prompt text, exactly as before; builders
# here only ever see structural params (effort, service_tier, mode), not
# prompt/model text, and must never be called with either.

def _build_codex_command(effort=None, service_tier=None, **_params):
    """No {prompt} in this template — confirmed live (codex --help): the
    positional PROMPT arg, when omitted, reads instructions from stdin.
    Prompt delivery is stdin-only for every builder below except gemini's
    (unverified, no installed CLI to confirm against) — see
    probe_reviewer_quota's unconditional `input=` and review-spec/
    SKILL.md's Step 1 external-CLI dispatch, which both redirect the
    already-on-disk prompt file as stdin regardless of whether a given
    template still inlines a literal {prompt} placeholder (the open
    hand-written-command escape hatch, and gemini today, still can)."""
    parts = ["codex exec --sandbox read-only --skip-git-repo-check", "-m {model}"]
    if effort:
        parts.append(f"-c model_reasoning_effort='\"{effort}\"'")
    if service_tier:
        parts.append(f"-c service_tier='\"{service_tier}\"'")
    return " ".join(parts)


def _build_claude_command(**_params):
    """No {prompt} — confirmed live: `claude -p` with no positional
    prompt argument reads it from stdin."""
    return "claude -p --model {model} --output-format text"


def _build_grok_command(**_params):
    """`-p -` (dash-as-value), not bare `-p` — confirmed live: grok's
    `-p`/`--single <PROMPT>` requires a value; only literal `-` makes it
    read that value from stdin instead of a positional arg. No {prompt}
    placeholder — see _build_codex_command's docstring."""
    return "grok -p - -m {model} --output-format plain"


def _build_gemini_command(**_params):
    return "gemini -m {model} --sandbox --approval-mode yolo {prompt}"


def _build_opencode_command(**_params):
    """No {prompt} — confirmed live: `opencode run -m {model}` with no
    positional message reads the prompt from stdin."""
    return "opencode run -m {model}"


def _build_cursor_agent_command(mode="plan", **_params):
    """--mode plan|ask are cursor-agent's own confirmed read-only modes
    (--help: "plan: read-only/planning (analyze, propose plans, no
    edits). ask: Q&A style ... (read-only)") — any other mode would allow
    edits, so this refuses rather than silently building a write-capable
    command for a reviewer.

    No {prompt} placeholder — confirmed live: cursor-agent's `-p`/
    `--print` is a boolean flag (no value), and with it set the process
    reads the prompt from stdin rather than a positional argument."""
    if mode not in ("plan", "ask"):
        raise ValueError(
            f"cursor-agent reviewer dispatch must use a read-only --mode "
            f"('plan' or 'ask'), got {mode!r}"
        )
    return f"cursor-agent -p --output-format text --mode {mode} --model {{model}}"


_COMMAND_BUILDERS = {
    "codex": _build_codex_command,
    "claude": _build_claude_command,
    "grok": _build_grok_command,
    "gemini": _build_gemini_command,
    "opencode": _build_opencode_command,
    "cursor-agent": _build_cursor_agent_command,
}


def build_reviewer_command(cli: str, **params) -> str:
    """Factory entry point: dispatch to `cli`'s own builder. Unrecognized
    kwargs are silently ignored by each builder's `**_params` (so a
    caller can pass one params dict without filtering it per CLI first —
    e.g. `effort`/`service_tier` for codex are simply unused by grok's
    builder rather than raising). Raises ValueError for an unregistered
    `cli` — never falls back to a guessed shape — and for structural
    params a specific builder rejects as unsafe (e.g. cursor-agent's
    write-capable modes, above)."""
    builder = _COMMAND_BUILDERS.get(cli)
    if builder is None:
        raise ValueError(
            f"no command builder registered for cli={cli!r} (known: "
            f"{', '.join(sorted(_COMMAND_BUILDERS))})"
        )
    return builder(**params)


def build_cursor_agent_model_id(base_model: str, effort=None, fast=None, context=None) -> str:
    """cursor-agent's own per-call effort/fast/context tuning lives in
    the --model argument itself via bracket-parameter overrides
    (confirmed live, --help: "Parameterized models accept quoted bracket
    overrides, e.g. 'claude-opus-4-8[context=1m,effort=high,
    fast=false]'"), not a separate CLI flag the command builder above
    could set — this builds that string for the reviewer entry's own
    `model` field instead. Returns `base_model` unchanged when no
    overrides are given, so calling this is always safe even with
    nothing to override."""
    overrides = []
    if effort:
        overrides.append(f"effort={effort}")
    if fast is not None:
        overrides.append(f"fast={'true' if fast else 'false'}")
    if context:
        overrides.append(f"context={context}")
    if not overrides:
        return base_model
    return f"{base_model}[{','.join(overrides)}]"


def build_reviewer_model_id(cli: str, base_model: str, effort=None, fast=None,
                             context=None) -> str:
    """Like build_reviewer_command, but for the `model` field itself —
    only cursor-agent encodes structural params there today; every other
    known CLI takes effort/service_tier as command-line flags instead
    (see build_reviewer_command), so this returns base_model unchanged
    for them rather than raising (no params to lose, unlike an
    unrecognized cli in build_reviewer_command)."""
    if cli == "cursor-agent":
        return build_cursor_agent_model_id(base_model, effort=effort, fast=fast, context=context)
    return base_model


# ── Quota probing ─────────────────────────────────────────────────────────

_UNAVAILABLE_SIGNALS = (
    "usage limit", "quota", "rate limit", "rate_limit",
    # confirmed live against cursor-agent on a free plan: exit code is
    # already nonzero for this case, so these are belt-and-suspenders,
    # not load-bearing — kept in case a future CLI reports the same
    # class of failure (plan/entitlement gate, not a temporary limit) on
    # a zero exit code.
    "actionrequirederror", "not authenticated", "not logged in",
)
_DETAIL_MAX_CHARS = 300


def render_reviewer_command(resolved: "ResolvedReviewer", prompt: str) -> str:
    """Fill a resolved reviewer's `command` template. {model} and {prompt}
    are always available; any of the entry's extra fields (effort,
    service_tier, ...) fill their own {placeholder} when the command
    references it. Shared by probe_reviewer_quota (below) and
    review-spec/SKILL.md's real dispatch step (via the `render-command`
    CLI subcommand), so probing and dispatching can never drift apart.

    Only {prompt} is shell-escaped (via shlex.quote) before substitution —
    it is free text built from document paths/content signals and MUST
    survive as exactly one shell argument no matter what it contains (this
    fixes a real command-injection risk: an unescaped {prompt} spliced into
    a `shell=True` command string via a document path containing `"`, `$`,
    or `` ` `` would corrupt or inject into the command). {model} and any
    `extra` field are deliberately left unescaped — they're short,
    human-typed config values, and some CLIs need their own literal
    quoting idiom in the template around them (e.g. codex's `-c
    key='"{effort}"'`), which auto-quoting would break. Command templates
    must therefore write a bare `{prompt}` (never `"{prompt}"` or
    `'{prompt}'` — the quoting is already applied here).

    Raises `ValueError` — never a raw `KeyError`/`AttributeError`/
    `IndexError`/`TypeError` — when `resolved.command` is missing (a
    `cli`-set entry with no `command` is a malformed config, per the
    schema's "required iff `cli` present"), the template references a
    placeholder that isn't `{model}`/`{prompt}`/one of `extra`'s keys,
    contains a literal unescaped brace, or `extra` itself defines a
    `model`/`prompt` key (a hand-written config collision with the two
    reserved placeholder names — `str.format`'s duplicate-keyword-argument
    `TypeError` in that case is exactly as much a malformed-config problem
    as a bad placeholder, and gets the same treatment). A malformed
    `review-spec.toml` entry must surface as a reportable config error,
    never crash the caller."""
    if not resolved.command:
        raise ValueError(
            f"reviewer {resolved.key!r} has cli={resolved.cli!r} set but no command template"
        )
    try:
        return resolved.command.format(
            model=resolved.model, prompt=shlex.quote(prompt), **resolved.extra
        )
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise ValueError(
            f"reviewer {resolved.key!r} has a malformed command template: {exc}"
        ) from exc


def probe_reviewer_quota(resolved: "ResolvedReviewer", run_fn=subprocess.run) -> dict:
    """Native (cli-less) entries are never probed — there is nothing to
    shell out to, and dispatch mechanics there are the current session's
    own concern, not a quota this module can observe. For CLI entries: run
    a trivial prompt through the reviewer's own command and classify
    availability generically — a nonzero exit code, or stdout/stderr
    containing a case-insensitive usage/quota/rate-limit phrase, means
    unavailable; anything else (including plain success) means available.
    This generic heuristic is what makes the confirmed codex usage-limit
    error (see skills/review-spec/references/cli-profiles/codex.md) detectable
    without a CLI-specific parser. A `cli`-set entry with a missing or
    malformed `command` template is deliberately classified `available:
    False` here rather than skipped/True — it can never actually be
    dispatched, so reporting it as available would let a broken config
    entry win the ladder walk and fail later, in real dispatch, instead
    of here where the failure is cheap and diagnosable.

    `detail` (always present) carries the reviewer's own combined
    stdout+stderr, truncated to `_DETAIL_MAX_CHARS`, when unavailable —
    e.g. "ActionRequiredError: Named models unavailable. Free plans can
    only use Auto." (confirmed live against cursor-agent). Empty string
    when available or native (nothing to report). This is diagnostic
    only — `available` is still the sole signal callers act on; `detail`
    exists so a human (review-spec-config's setup wizard, or anyone
    reading quota.json) can see *why* without re-running the probe by
    hand.

    The probe prompt is always piped via stdin (`input=`), never inlined
    as a shell argument — confirmed live against every known-CLI builder
    (codex/claude/grok/opencode/cursor-agent all read a missing/`-`-value
    prompt from stdin; see each `_build_*_command`'s docstring). This is
    unconditional, not gated on whether `resolved.command` happens to
    still contain a literal `{prompt}` (gemini's builder, and any
    hand-written open-hatch command, still can) — an unread stdin pipe is
    harmless to a CLI that takes its prompt inline instead, so one code
    path serves both without the caller needing to introspect the
    template first."""
    if not resolved.cli:
        return {"available": True, "checked_at": time.time(), "detail": ""}
    probe_prompt = "Only say: Hello world!"
    try:
        filled = render_reviewer_command(resolved, probe_prompt)
    except ValueError as exc:
        return {"available": False, "checked_at": time.time(), "detail": str(exc)}
    try:
        result = run_fn(filled, shell=True, input=probe_prompt, capture_output=True,
                         text=True, check=False, timeout=30)
    except subprocess.TimeoutExpired:
        return {"available": False, "checked_at": time.time(),
                "detail": "timed out after 30s"}
    except OSError as exc:
        return {"available": False, "checked_at": time.time(), "detail": str(exc)}
    combined = (result.stdout + result.stderr).strip()
    if result.returncode != 0 or any(s in combined.lower() for s in _UNAVAILABLE_SIGNALS):
        return {"available": False, "checked_at": time.time(),
                "detail": combined[:_DETAIL_MAX_CHARS]}
    return {"available": True, "checked_at": time.time(), "detail": ""}


def refresh_quota_cache(config: dict, ladder_keys: list, existing: dict, ttl_seconds: int,
                         run_fn=subprocess.run) -> dict:
    """Returns an updated quota dict: probes only ladder_keys entries that
    are missing or whose last probe is older than ttl_seconds; entries
    still fresh are left untouched (no re-probe, no wasted quota-checking
    quota)."""
    reviewers = config.get("reviewers", [])
    updated = dict(existing)
    now = time.time()
    for key in ladder_keys:
        current = updated.get(key)
        if current is not None and now - current.get("checked_at", 0) < ttl_seconds:
            continue
        entry = _reviewer_by_key(reviewers, key)
        if entry is None:
            continue
        updated[key] = probe_reviewer_quota(_to_resolved(entry), run_fn=run_fn)
    return updated


# ── Findings merge (review-spec/SKILL.md's Step 1.5 double-review reconciliation) ──

_SEVERITY_HEADINGS = {
    "CRITICAL": "CRITICAL", "HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW",
    "Cross-Document Consistency": "CROSS-DOC",
}
_SEVERITY_RE = re.compile(
    r"^### (CRITICAL|HIGH|MEDIUM|LOW|Cross-Document Consistency)\s*$", re.MULTILINE)
_BULLET_RE = re.compile(
    r"^- \*\*(.+?)\*\* — Location: (.+?)\. Required: (.+?)\. Why: (.+?)\.\s*$",
    re.MULTILINE)


def report_has_status(report_text: str) -> bool:
    """True iff report_text contains a `### Status:` line — the one thing
    every conforming reviewer report guarantees (per review-spec-checklist's
    output template). Used by the merge-reports CLI subcommand to
    detect a failed/non-conforming/empty reviewer report BEFORE merging, so
    a broken external CLI call can never silently read as a clean Approved
    merge (it never produces findings, so an unguarded merge would treat it
    as "zero issues")."""
    return "### Status:" in report_text


def report_declares_issues(report_text: str) -> bool:
    """True iff report_text's own Status line says Issues Found. A plain
    substring check, deliberately independent of `_BULLET_RE`'s strict
    per-bullet shape — `parse_findings` can miss a bullet that wraps across
    lines or uses slightly different punctuation, but the report's own
    Status line is a single fixed string every conforming report ends
    with. Used as a second, structurally-independent signal alongside
    parsed findings so a report that says "Issues Found" can never merge
    into a false "Approved" just because none of its bullets happened to
    match the strict bullet regex."""
    return "### Status: Issues Found" in report_text


def parse_findings(report_text: str) -> list:
    """[{severity, title, location, required, why}] in document order, per
    the review-spec-checklist output template (`### SEVERITY` headings —
    `CRITICAL`/`HIGH`/`MEDIUM`/`LOW`, plus `### Cross-Document Consistency`
    normalized to the `"CROSS-DOC"` severity tag — followed by
    `- **title** — Location: .... Required: .... Why: ....` bullets).
    `LOW` is recognized because a plan-archetype review may legitimately
    emit it (review-spec-checklist's Plan checklist defines a LOW/Tooling-
    Catchable tier); without recognizing it, its bullets would fall
    through to severity None and get silently re-labeled MEDIUM by
    `render_merged_report`, escalating severity that was never intended.
    A bullet appearing before any recognized heading (malformed input)
    still gets severity None."""
    sev_matches = list(_SEVERITY_RE.finditer(report_text))
    findings = []
    for m in _BULLET_RE.finditer(report_text):
        pos = m.start()
        severity = None
        for i, sm in enumerate(sev_matches):
            nxt = sev_matches[i + 1].start() if i + 1 < len(sev_matches) else len(report_text)
            if sm.start() <= pos < nxt:
                severity = _SEVERITY_HEADINGS[sm.group(1)]
                break
        findings.append({"severity": severity, "title": m.group(1), "location": m.group(2),
                          "required": m.group(3), "why": m.group(4)})
    return findings


def merge_findings(reports: list) -> list:
    """reports: [(reviewer_key, report_text), ...]. Union of every finding,
    each tagged with which reviewer(s) surfaced it. Findings sharing the
    exact same (severity, location) ACROSS DIFFERENT reports are combined
    into one entry with both reviewers tagged — deliberately NOT fuzzy
    title-text matching (two models rarely word the same finding
    identically), so this only merges the case where they flag literally
    the same passage. Within a single report, two distinct findings that
    happen to share a (severity, location) — e.g. two separate HIGH issues
    both in "§3" — are never collapsed into each other: only the first
    occurrence per report claims the bare (severity, location) key; any
    later same-report finding at that same key is disambiguated by adding
    its own title into the key, so it always survives as its own entry."""
    merged = {}
    order = []
    for key, text in reports:
        seen_this_report = set()
        for f in parse_findings(text):
            dedup_key = (f["severity"], f["location"])
            if dedup_key in seen_this_report:
                dedup_key = (f["severity"], f["location"], f["title"])
            seen_this_report.add((f["severity"], f["location"]))
            if dedup_key in merged:
                merged[dedup_key]["reviewers"].append(key)
            else:
                entry = dict(f)
                entry["reviewers"] = [key]
                merged[dedup_key] = entry
                order.append(dedup_key)
    return [merged[k] for k in order]


def render_merged_report(findings: list, doc_paths: str, any_source_issues: bool = False) -> str:
    """Renders CRITICAL/HIGH/MEDIUM/LOW under their own headings and
    CROSS-DOC findings under the same `### Cross-Document Consistency`
    heading the source reports use (never a raw `### CROSS-DOC`, which
    isn't part of the output template). A finding whose severity didn't
    match any recognized heading (malformed input — e.g. a bullet before
    any `### SEVERITY` heading) falls back to MEDIUM, tagged exactly as
    parsed — this can only happen on non-conforming input, since
    the merge-reports CLI subcommand already filters those out (via
    report_has_status) before this function ever runs. Deliberately
    drops each source report's own
    `### Document Type`/`### Files Read` lines — those describe a single
    reviewer's run, not a property of the merge — in favor of a fixed
    `cross-ai merged` marker.

    `any_source_issues` (from `report_declares_issues` on each raw source
    report, computed by the caller) is OR'd into the parsed-findings-based
    status: a report can legitimately say "Issues Found" while containing
    a bullet `_BULLET_RE` fails to parse (wrapped line, off-template
    punctuation), and without this the merge would silently downgrade that
    to "Approved" purely because no *parsed* finding survived."""
    by_sev = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": [], "CROSS-DOC": []}
    for f in findings:
        sev = f["severity"] if f["severity"] in by_sev else "MEDIUM"
        by_sev[sev].append(f)
    lines = [f"## Review: {doc_paths}", "### Document Type", "cross-ai merged"]
    any_issues = any(by_sev.values()) or any_source_issues
    heading_for = {"CRITICAL": "### CRITICAL", "HIGH": "### HIGH", "MEDIUM": "### MEDIUM",
                   "LOW": "### LOW", "CROSS-DOC": "### Cross-Document Consistency"}
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "CROSS-DOC"):
        items = by_sev.get(sev, [])
        if not items:
            continue
        lines.append(heading_for[sev])
        for f in items:
            tag = ", ".join(f["reviewers"])
            lines.append(f"- **{f['title']}** — Location: {f['location']}. "
                          f"Required: {f['required']}. Why: {f['why']}. (Reviewers: {tag})")
    lines.append(
        "### Status: Issues Found — fix and re-invoke" if any_issues else "### Status: Approved"
    )
    return "\n".join(lines) + "\n"


# ── CLI entrypoint ────────────────────────────────────────────────────────

def main(argv: list, which_fn=shutil.which, run_fn=subprocess.run) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="review-spec")
    sub = parser.add_subparsers(dest="command", required=True)

    p_cache_path = sub.add_parser("cache-path")
    p_cache_path.add_argument("--kind", choices=["runtimes", "quota"], required=True)

    p_detect = sub.add_parser("detect-runtimes")
    p_detect.add_argument(
        "--save", default=None, help="write the snapshot to this path via cache_write_json"
    )
    p_detect.add_argument(
        "--if-stale", default=None, metavar="PATH",
        help=(
            "skip detection entirely (print {} and exit 0) when PATH exists "
            "and is fresher than RUNTIMES_TTL_SECONDS; else detect and --save to PATH"
        ),
    )

    p_quota = sub.add_parser("probe-quota")
    p_quota.add_argument("--cwd", required=True)
    p_quota.add_argument("--quota-path", required=True)

    p_resolve = sub.add_parser("resolve-reviewers")
    p_resolve.add_argument("--cwd", required=True)
    p_resolve.add_argument("--quota-path", required=True)
    p_resolve.add_argument("--source-vendor", default="")  # "" = no same-vendor skip
    p_resolve.add_argument("--cross-ai", action="store_true")

    p_merge = sub.add_parser("merge-reports")
    p_merge.add_argument("--doc-paths", required=True)
    p_merge.add_argument("reports", nargs="+", help="key=path/to/report.md")

    p_toml = sub.add_parser("render-toml")
    p_toml.add_argument(
        "--json-config", required=True, help="path to a JSON file shaped like the TOML config"
    )
    p_toml.add_argument(
        "--out", default=None,
        help=(
            "write the rendered TOML to this path via cfg_write_toml (creating parent dirs) "
            "instead of only printing it"
        ),
    )

    p_render = sub.add_parser("render-command")
    p_render.add_argument("--reviewers-json", required=True,
                           help="path to resolve-reviewers' saved JSON array output")
    p_render.add_argument("--index", type=int, required=True,
                           help="0 for the primary/only reviewer, 1 for the secondary")
    p_render.add_argument("--prompt-file", required=True)

    p_vendor = sub.add_parser("infer-vendor")
    p_vendor.add_argument("--model", required=True)

    p_build_cmd = sub.add_parser("build-command")
    p_build_cmd.add_argument("--cli", required=True)
    p_build_cmd.add_argument("--effort", default=None)
    p_build_cmd.add_argument("--service-tier", default=None)
    p_build_cmd.add_argument("--mode", default="plan",
                              help="cursor-agent only: 'plan' or 'ask' (both read-only)")

    p_build_model = sub.add_parser("build-model-id")
    p_build_model.add_argument("--cli", required=True)
    p_build_model.add_argument("--base-model", required=True)
    p_build_model.add_argument("--effort", default=None)
    p_build_model.add_argument("--fast", choices=["true", "false"], default=None)
    p_build_model.add_argument("--context", default=None)

    p_group = sub.add_parser("group-models")
    p_group.add_argument(
        "--runtimes-json", required=True,
        help="path to a detect-runtimes snapshot (as saved via --save/--if-stale)"
    )
    p_group.add_argument("--cli", required=True,
                          help="which CLI's models array to group, e.g. opencode, cursor-agent")

    p_check = sub.add_parser("check-reviewer")
    p_check.add_argument("--key", default="candidate")
    p_check.add_argument("--model", default="")
    p_check.add_argument("--vendor", default="")
    p_check.add_argument("--cli", default=None,
                          help="omit for a native (no-CLI) candidate — always available")
    p_check.add_argument("--command", dest="reviewer_command", default=None,
                          help="required when --cli is set; the command template to test")
    p_check.add_argument("--extra-json", default=None,
                          help="JSON object of extra {placeholder} fields the template needs")

    args = parser.parse_args(argv)

    if args.command == "cache-path":
        env = dict(os.environ)
        print(cache_runtimes_path(env) if args.kind == "runtimes" else cache_quota_path(env))
        return 0

    if args.command == "detect-runtimes":
        if args.if_stale and not cache_is_stale(args.if_stale, RUNTIMES_TTL_SECONDS):
            print(json.dumps({}))  # fresh — caller should treat this as "nothing to do"
            return 0
        snapshot = build_runtimes_snapshot(which_fn=which_fn, run_fn=run_fn)
        save_path = args.if_stale or args.save
        if save_path:
            cache_write_json(save_path, snapshot)
        print(json.dumps(snapshot))
        return 0

    if args.command == "probe-quota":
        config = cfg_resolve(args.cwd, dict(os.environ))
        ladder = config.get("policy", {}).get("ladder", [])
        existing = cache_read_json(args.quota_path) or {}
        updated = refresh_quota_cache(config, ladder, existing, QUOTA_TTL_SECONDS, run_fn=run_fn)
        cache_write_json(args.quota_path, updated)
        print(json.dumps(updated))
        return 0

    if args.command == "resolve-reviewers":
        config = cfg_resolve(args.cwd, dict(os.environ))
        quota = cache_read_json(args.quota_path) or {}
        reviewers = resolve_reviewers(config, quota, args.source_vendor, args.cross_ai)
        print(json.dumps([r._asdict() for r in reviewers]))
        return 0

    if args.command == "merge-reports":
        reports = []
        unreadable = []
        for item in args.reports:
            key, _, path = item.partition("=")
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
            except OSError:
                unreadable.append(key)
                continue
            if not report_has_status(text):
                unreadable.append(key)
                continue
            reports.append((key, text))
        if unreadable:
            # Deliberately prints NO "### Status:" line — review-spec/SKILL.md's
            # existing Step 2 already treats "No Status line" as a failure to
            # surface (its own long-standing rule), so a failed/unreadable
            # external reviewer can never silently merge into a false
            # "### Status: Approved". No new orchestrator special-case needed.
            print(f"merge-reports: reviewer(s) {', '.join(unreadable)} produced "
                  f"no readable report with a Status line — cannot merge.")
            return 0
        merged = merge_findings(reports)
        any_source_issues = any(report_declares_issues(text) for _, text in reports)
        print(render_merged_report(merged, args.doc_paths, any_source_issues))
        return 0

    if args.command == "render-toml":
        with open(args.json_config, encoding="utf-8") as f:
            config = json.load(f)
        rendered = cfg_render_toml(config)
        if args.out:
            cfg_write_toml(args.out, config)
        print(rendered)
        return 0

    if args.command == "render-command":
        with open(args.reviewers_json, encoding="utf-8") as f:
            reviewers = json.load(f)
        r = reviewers[args.index]
        resolved = ResolvedReviewer(key=r["key"], model=r["model"], vendor=r["vendor"],
                                     cli=r["cli"], command=r["command"], extra=r["extra"])
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
        try:
            print(render_reviewer_command(resolved, prompt))
        except ValueError as exc:
            # Deliberately no "### Status:" substring — same fail-closed
            # convention as merge-reports: review-spec/SKILL.md's existing
            # "No Status line -> Surface failure" rule catches this
            # without any new special-casing at the dispatch step.
            print(f"render-command: {exc}", file=sys.stderr)
            return 1
        return 0

    if args.command == "infer-vendor":
        print(json.dumps({"vendor": infer_vendor_from_model(args.model)}))
        return 0

    if args.command == "build-command":
        params = {}
        if args.effort:
            params["effort"] = args.effort
        if args.service_tier:
            params["service_tier"] = args.service_tier
        if args.cli == "cursor-agent":
            params["mode"] = args.mode
        try:
            print(build_reviewer_command(args.cli, **params))
        except ValueError as exc:
            print(f"build-command: {exc}", file=sys.stderr)
            return 1
        return 0

    if args.command == "build-model-id":
        fast = {"true": True, "false": False, None: None}[args.fast]
        print(build_reviewer_model_id(args.cli, args.base_model, effort=args.effort,
                                       fast=fast, context=args.context))
        return 0

    if args.command == "group-models":
        snapshot = cache_read_json(args.runtimes_json) or {}
        models = snapshot.get("clis", {}).get(args.cli, {}).get("models", [])
        print(json.dumps(group_models_by_family(models)))
        return 0

    if args.command == "check-reviewer":
        extra = json.loads(args.extra_json) if args.extra_json else {}
        resolved = ResolvedReviewer(key=args.key, model=args.model, vendor=args.vendor,
                                     cli=args.cli, command=args.reviewer_command, extra=extra)
        result = probe_reviewer_quota(resolved, run_fn=run_fn)
        print(json.dumps(result))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
