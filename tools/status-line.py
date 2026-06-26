#!/usr/bin/env python3
"""Claude Code status line — modular Python port of statusline.sh.

Reads the status JSON on stdin and prints up to three ANSI-colored lines.
Layout is driven by SEGMENTS (on/off), LAYOUT (template), and BUILDERS
(key -> builder(ctx, avail)). The packer is the authority on show/hide;
builders auto-deprioritize to fit. See the "HOW TO CUSTOMIZE" block near the
bottom. Stdlib only. The .sh original is kept as a fallback.
"""
# pyright: strict
# ARCHITECTURE — functional core / imperative shell, one file, nine role blocks.
# This module RENDERS ONLY: read stdin JSON -> pack -> print. Config introspection
# (--doctor / --check / --print-config) lives in the sibling statusline-doctor.py,
# which imports this render core one-way (never the reverse).
# Every top-level function carries a role prefix and lives in the matching block,
# so a reader can locate (and lift out) a whole role by name. Block order
# (functional core first, imperative shell last):
#   1. DEFAULTS  data only — SEGMENTS/LAYOUT/PINNED + palette/ramp/effort tables +
#                tuning scalars + fixed colors + type decls (Config/Line/
#                GitSnapshot/ExtSpec). No logic; edit a default here.
#   2. cfg_      config loading & resolution — the ONLY block that reads config
#                env/TOML -> one immutable Config (settings + resolved cache paths).
#   3. probe_    side-effecting data gatherers (git / proc / ps / fs / subprocess);
#                each owns its caching/TTL. Memoized per render so the cost lands
#                in the measured build of the first segment that calls it (FR-R.2).
#   4. fmt_      pure formatters (number / tokens / duration / bytes / ago).
#   5. util_     pure non-format helpers (color / width / truncate / fit / parse).
#   6. core_     render machinery — Context (attribute access only, D4), Theme, the
#                builder registry, the packer, and render.
#   7. seg_      seg_x(ctx, avail, theme) -> str | None, self-sourcing; the builder
#                map is auto-discovered from seg_* names (add a seg_x, it registers).
#   8. SHELL     side effects only (env capture, stdin, print); the render entrypoint.
#   9. HOW TO CUSTOMIZE — the segment-authoring guide. Introspection itself
#                (--doctor/--check/--print-config) is extracted to the sibling
#                statusline-doctor.py; this module no longer accepts those flags.
# To add a segment: write seg_<key>(ctx, avail, theme) in the seg_ block; add <key>
# to a LAYOUT line; add <key>: True to SEGMENTS. The registry wires itself.
# pylint: disable=invalid-name  # installed script name is hyphenated (status-line.py)

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import unicodedata

try:
    import tomllib as _tomllib_impl
    tomllib = _tomllib_impl
except ModuleNotFoundError:        # Python < 3.11 — degrade to env-only config.
    tomllib = None  # type: ignore[assignment]  # stdlib boundary: optional module absent on <3.11
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, NamedTuple, Optional, cast

# Environment dict: a snapshot of os.environ captured once in main() (D6).
# Mapping[str, str] covers both plain dict and os.environ (_Environ[str]).
Env = Mapping[str, str]


# ═══ 1. DEFAULTS — data-only: segment/layout/palette/ramp tables + type decls ═


# Per-segment on/off. Set False to hide a segment entirely: its builder is never
# called, so its data is never read and the matching lazy probe (git/transcript/
# RSS/etc.) never runs — a disabled segment costs nothing. Invariant: keep "path"
# True so the identity line always emits.
SEGMENTS = {
    # identity line
    "path": True, "git_branch": True, "git_dirty": True, "alt_git_worktree": False,
    "todo": True,
    # model row
    "model": True, "alt_time_ago": False, "alt_time_clock": False, "effort": True,
    "lines": True, "alt_cost": False, "alt_time_session": False, "alt_time_api": False,
    # diagnostics row (alt_term_dimensions is a debug aid — off by default)
    "render_time": True, "slowest": True, "alt_term_dimensions": False,
    "context": True,
    "chat_size": True, "alt_process_memory": False, "alt_rate_limits": False,
}


# Identity-line tuning.
PATH_MAX_LEN = 20       # ~-collapsed path longer than this collapses to its basename


CONTEXT_BAR_CELLS = 10  # context bar width; ▌ half-cells give 5% resolution


# Packing: reserve a few cols so emoji-width miscounts don't wrap the line.
RIGHT_MARGIN = 4


SEP = " | "


# One Line per row. `segments` lists keys LEFT->RIGHT; leftmost = highest
# priority (kept first when space is tight). `min_rows` gates the whole row by
# terminal height. Reorder = move a key within a list; move between rows = cut
# and paste a key; hide = flip its SEGMENTS flag.
class Line(NamedTuple):
    """One display row: minimum terminal height to show it + ordered segment keys."""

    min_rows: int
    segments: list[str]


LAYOUT = [
    Line(0,  ["path", "git_branch", "alt_git_worktree", "git_dirty", "todo"]),
    Line(20, ["model", "alt_time_ago", "alt_time_clock", "effort", "lines",
              "alt_cost", "alt_time_session", "alt_time_api"]),
    Line(30, ["render_time", "slowest", "alt_term_dimensions", "context",
              "chat_size", "alt_process_memory", "alt_rate_limits"]),
]


PINNED = {"path", "context"}   # always rendered even if they overflow the budget


# Meta-segments: they report the whole render, not a single builder, so the
# `slowest` readout never names them as the culprit (its own output + render_time).
_SLOWEST_META = frozenset({"slowest", "render_time"})


# Resolved configuration: the result of merging internal defaults < TOML file <
# env. `segments` is a {key: bool} dict, `layout` a list[Line], `palette` a
# {NAME: "sgr;params"} dict of overrides (empty = no override), `ramps` a
# {band: {threshold: colorspec}} dict of whole-band overrides (empty = no
# override). External drop-in segments are E4c and are intentionally not part of
# this type yet.
# Scalar behaviour knobs that aren't segments/colors. The worktree feature
# migrated to the `segments.alt_git_worktree` toggle (see SEGMENTS); `[git]` now carries
# `cache_ttl` (seconds) — how long the shared probe_git_snapshot worktree probe is
# cached. Precedence: this default < TOML `[git] cache_ttl` < env CC_AI_KIT_GIT_CACHE_TTL.
_GIT_CACHE_TTL = 5                  # default seconds the worktree probe is cached


_EXTERNAL_CACHE_TTL = 10            # default seconds an external provider's output is cached


_GIT_DEFAULTS = {"cache_ttl": _GIT_CACHE_TTL}




# ── Color & effort defaults (the override baselines) ─────────────────────────
# Overridable palette: NAME -> default SGR params (no "\033[" / "m" wrapper).
# Values are pure hues — no baked-in bold. Emphasis is expressed on the ramp
# bands via "+modifiers" (e.g. "RED+bold"); see _RAMP_DEFAULTS. A [palette]
# override replaces a value here; core_build_theme resolves these into a Theme.
_PALETTE_DEFAULTS = {            # pure hues — no baked-in bold
    "GREY": "90", "WHITE": "97", "CYAN": "36", "GREEN": "32", "RED": "31",
    "YELLOW": "33", "MAGENTA": "35", "ORANGE": "38;5;208",
    "BLUE": "38;5;39",           # lightened (was 38;5;33); shade reviewed on-terminal
    "LIGHTBLUE": "38;5;75", "MAGENTA_DARK": "38;5;90",
}   # ORANGE_BOLD / MAGENTA_DARK_BOLD removed — bold now lives on the ramp band


# Ramps as data: band -> [(threshold, colorspec)]. Threshold keys go through
# util_parse_threshold (percent / byte-suffix / inf); colorspecs through util_parse_color
# against the resolved palette. [ramp.X] in config REPLACES a band wholesale.
_RAMP_DEFAULTS = {
    "context": [(10, "WHITE"), (15, "CYAN"), (20, "BLUE"), (25, "GREEN"),
                (30, "YELLOW"), (40, "ORANGE+bold"), (50, "RED+bold"),
                ("inf", "MAGENTA_DARK+bold")],
    "rate": [(50, "GREEN"), (80, "YELLOW"), ("inf", "RED+bold")],
    "chat_size": [("512k", "WHITE"), ("1M", "CYAN"), ("2M", "LIGHTBLUE"),
                  ("3M", "GREEN"), ("4M", "YELLOW"), ("5M", "ORANGE"),
                  ("10M", "RED+bold"), ("inf", "MAGENTA")],
    # render_time: the status line's own run time (SLO/SLA). Thresholds are time
    # units (ns/µs/ms/s); green under the SLO, yellow under the SLA, red beyond.
    "render_time": [("50ms", "GREEN"), ("150ms", "YELLOW"), ("inf", "RED+bold")],
    # slowest: the single per-segment SLO/SLA ramp the `slowest` segment colors by
    # (one shared band — NO per-segment override bands). Tighter than render_time
    # since it grades ONE builder, not the whole render.
    "slowest": [("15ms", "GREEN"), ("40ms", "YELLOW"), ("inf", "RED+bold")],
}


# Effort ladder: level -> (palette name, fill count 1..5). Palette-derived but
# NOT user-configurable. `auto` is a setting and `ultracode` reports as xhigh —
# neither is a level here.
_EFFORT_DEFAULTS = {
    "low": ("CYAN", 1), "medium": ("BLUE", 2), "high": ("YELLOW", 3),
    "xhigh": ("ORANGE", 4), "max": ("RED", 5),
}


_EFFORT_GLYPHS = "▁▃▄▆█"


# `git` and `external` default to None so older Config(...) call sites (which
# pass only the original fields) keep working; consumers guard with
# (cfg.git or {}) and (cfg.external.providers if cfg.external else []).
class ExternalConf(NamedTuple):
    """Resolved external-segment configuration for one render pass."""

    dir: str               # providers directory (was Config.segments_dir)
    cache_ttl: int         # default cache TTL in seconds
    providers: list[Any]   # finalized ExtSpec list (was Config.external)


class Config(NamedTuple):
    """Resolved, validated configuration for one render pass."""

    segments: dict[str, bool]
    layout: list[Line]
    palette: dict[str, str]
    ramps: dict[str, dict[str, str]]
    git: dict[str, int] | None = None
    external: "ExternalConf | None" = None
    cache_base: str = ""


_ENV_TRUE = {"1", "true", "t", "y", "yes", "on"}


_ENV_FALSE = {"0", "false", "f", "n", "no", "off"}


# Fixed (non-overridable) colors.
RESET = "\033[0m"


BG_LIGHTGRAY = "\033[47m"


_DIM = "\033[90m"             # fixed dim grey for stderr warnings (palette-independent)


_WARN = "\033[33m"            # fixed yellow for failure markers (palette-independent)


INF = float("inf")


# A builder takes (ctx, avail_cols, theme) and returns a rendered string or None.
Builder = Callable[["Context", int, "Theme"], str | None]


# The single shared git probe result. `git_branch`, `git_dirty`, and
# `alt_git_worktree` are independent segments but all read from one GitSnapshot —
# no duplicated git querying. wt_name is the active linked-worktree's directory
# basename ("" on the main checkout or outside a repo).
class GitSnapshot(NamedTuple):
    """One-shot result from the shared git probe (branch, dirty, worktree)."""

    in_repo: bool
    branch: str
    dirty: str
    is_worktree: bool
    wt_name: str


# ── External drop-in segments (E4c) ──────────────────────────────────────────


# A provider is an executable in the segments dir. Its first 10 lines may carry
#   # ai-kit-segment: line=<N> (after=<key>|before=<key>|start|end)
#                     [id=<slug>] [timeout=<s>] [ttl=<s>]
# It is modeled as a synthetic builder inserted into the resolved layout, so the
# existing packer handles placement/priority/overflow unchanged.
class ExtSpec(NamedTuple):
    """Metadata for one external segment provider discovered from the segments dir."""

    id: str
    path: str
    line: int
    position: tuple[str, str]
    timeout: float
    ttl: int
    cache_path: str


# ═══ 2. cfg_ — config loading & resolution (the only block that reads config env)


def cfg_git_key_problem(k: str, v: Any) -> str | None:
    """Classify one `[git]` key/value so cfg_load_config and the doctor's
    validate_config_file share a single validation rule (each formats its own
    message). Returns:
      'unknown' — not a recognized `[git]` key,
      'bad_ttl' — cache_ttl is not an int (bools excluded),
      None      — acceptable."""
    if k not in _GIT_DEFAULTS:
        return "unknown"
    if k == "cache_ttl" and (not isinstance(v, int) or isinstance(v, bool)):
        return "bad_ttl"
    return None


def cfg_warn(msg: str) -> None:
    """The single render-format config-warning emitter: dim grey, 'status-line:'
    prefix, stderr. Phase-3 the doctor prints bind problems through this same
    wrapper, so relocated warning text is byte-identical to what render emitted."""
    print(f"{_DIM}status-line: {msg}{RESET}", file=sys.stderr)


# kind -> (human description for messages, env-string parser).
# Open dispatch: add a kind by adding one row (no caller edits). bool/int only
# (FR scope; no float/list config field exists — YAGNI).
def _coerce_env_bool(raw: str) -> tuple[Any, bool]:
    """(value, recognized). Unrecognized -> (None, False) = tri-state no-override."""
    v = raw.strip().lower()
    if v in _ENV_TRUE:
        return True, True
    if v in _ENV_FALSE:
        return False, True
    return None, False


def cfg_coerce(raw: Any, kind: str, source: str, label: str) -> tuple[Any, str | None]:
    """Coerce a raw config value to `kind` ('bool'|'int') from `source`
    ('env'|'toml'). Returns (value, problem):
      (value, None)   -> a coerced value to apply,
      (None, None)    -> no override / skip (no real config value is None),
      (None, problem) -> present but not coercible; `problem` is the core text.
    source='env' (raw is str): bool via _ENV_TRUE/_ENV_FALSE, UNRECOGNIZED -> skip
    (preserves today's SILENT env-bad-bool); int via int(raw).
    source='toml' (raw already typed): bool must be a real bool; int must be int
    and not bool. `label` is the message subject (env var name / "segment 'x'" /
    '[git] cache_ttl')."""
    desc = "true/false" if kind == "bool" else "an integer"
    bad = f"{label} must be {desc}, got {raw!r} — ignored"
    if source == "env":
        if kind == "bool":
            value, recognized = _coerce_env_bool(cast(str, raw))
            return (value, None) if recognized else (None, None)  # unrecognized = silent skip
        try:
            return int(cast(str, raw)), None
        except (TypeError, ValueError):
            return None, bad
    # source == "toml": strict, already-typed
    if kind == "bool":
        return (raw, None) if isinstance(raw, bool) else (None, bad)
    return (raw, None) if isinstance(raw, int) and not isinstance(raw, bool) else (None, bad)


def cfg_source_get(source: str, raw_toml: dict[str, Any], env: Env,
                   path: tuple[str, ...]) -> Any | None:
    """Raw value for `path` from `source`, or None if absent. Env name is the
    mechanical projection CC_AI_KIT_<PATH> (the ('segments', KEY) path projects to
    CC_AI_KIT_SEGMENT_<KEY>); TOML is a nested-dict lookup."""
    if source == "env":
        head = "SEGMENT" if path[0] == "segments" else path[0].upper()
        name = "CC_AI_KIT_" + "_".join([head, *(p.upper() for p in path[1:])])
        return env.get(name)
    cur: dict[str, Any] = raw_toml
    for i, part in enumerate(path):
        if part not in cur:
            return None
        val: Any = cur[part]
        if i < len(path) - 1:
            if not isinstance(val, dict):
                return None
            cur = cast(dict[str, Any], val)
        else:
            return val
    return None


def _env_label(path: tuple[str, ...]) -> str:
    """Message subject for an env field = the projected env var name."""
    head = "SEGMENT" if path[0] == "segments" else path[0].upper()
    return "CC_AI_KIT_" + "_".join([head, *(p.upper() for p in path[1:])])


def _env_segment_keys(env: Env) -> list[str]:
    """Lower-cased segment keys present as CC_AI_KIT_SEGMENT_* in env."""
    pre = "CC_AI_KIT_SEGMENT_"
    return [k[len(pre):].lower() for k in env if k.startswith(pre)]


def cfg_bind_scalars(
    raw_toml: dict[str, Any], env: Env, git: dict[str, Any],
    ext_dir: str, ext_ttl: int,
) -> tuple[dict[str, Any], str, int, list[str]]:
    """Bind the scalar line_conf groups (git, external) from env on top of the
    already-resolved default<TOML values. Runs BEFORE external-provider discovery
    because CC_AI_KIT_EXTERNAL_DIR changes which directory is scanned. Phase 2
    binds ENV only (TOML stays in the git loop / cfg_resolve_external and folds
    into this walk in a later phase, when their warnings migrate to the problem
    channel). Collects problems instead of printing; the caller decides. Returns
    (git, ext_dir, ext_ttl, problems)."""
    g, d, t = dict(git), ext_dir, ext_ttl
    problems: list[str] = []

    def bind_int(path: tuple[str, ...], cur: int) -> int:
        raw = cfg_source_get("env", raw_toml, env, path)
        if raw is None:
            return cur
        value, prob = cfg_coerce(raw, "int", "env", _env_label(path))
        if prob:
            problems.append(prob)
            return cur
        return value if value is not None else cur

    g["cache_ttl"] = bind_int(("git", "cache_ttl"), g["cache_ttl"])
    t = bind_int(("external", "cache_ttl"), t)
    raw_dir = cfg_source_get("env", raw_toml, env, ("external", "dir"))
    if raw_dir:
        d = os.path.expanduser(cast(str, raw_dir))
    return g, d, t, problems


def cfg_bind_segments(
    raw_toml: dict[str, Any], env: Env, segments: dict[str, bool],
) -> tuple[dict[str, bool], list[str]]:
    """Bind the segment toggle map from env on top of the already-resolved
    default<TOML map (cfg_resolve_segments). Runs AFTER external-provider
    discovery so provider ids are known segment keys. Canonical keys only — no
    legacy forwarding. env bad-bool stays silent (tri-state). Collects problems
    instead of printing. Returns (segments, problems)."""
    seg = dict(segments)
    problems: list[str] = []
    for key in _env_segment_keys(env):
        if key not in seg:
            continue
        raw = cfg_source_get("env", raw_toml, env, ("segments", key))
        value, prob = cfg_coerce(raw, "bool", "env", _env_label(("segments", key)))
        if prob:
            problems.append(prob)
        elif value is not None:
            seg[key] = value
    return seg, problems


def cfg_default_config() -> "Config":
    """A Config snapshotting the current module-global defaults (SEGMENTS/LAYOUT,
    no palette/ramp overrides). Copies are returned so callers cannot mutate
    globals."""
    return Config(segments=dict(SEGMENTS), layout=list(LAYOUT), palette={}, ramps={},
                  git=dict(_GIT_DEFAULTS))


def cfg_config_path(env: Env) -> str:
    """Resolved TOML path: CC_AI_KIT_CONFIG_FILE, else
    ${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/statusline.toml.

    FR-1.7: this is the bootstrap exception — it reads env directly before any
    TOML is loaded (chicken-and-egg), so it is the one explicit hardcoded env read
    outside the cfg_bind_scalars/cfg_bind_segments layer."""
    explicit = env.get("CC_AI_KIT_CONFIG_FILE")
    if explicit:
        return os.path.expanduser(explicit)
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
    return os.path.join(base, "ai-kit", "statusline.toml")


def cfg_load_toml(path: str) -> dict[str, Any]:
    """Parse the TOML at path. Missing/empty/malformed/no-tomllib → {}.
    Never raises, never prints."""
    if tomllib is None:
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def cfg_resolve_segments(
    defaults: dict[str, bool], file_seg: Any
) -> tuple[dict[str, bool], list[str]]:
    """defaults < file [segments] (TOML only). Each file entry is dropped with a
    dim warning if its key is unknown OR its value is not a bool (e.g.
    `alt_cost = "true"` instead of `alt_cost = true`); only bool file values for
    known keys are honored. Env overrides are applied later by
    cfg_bind_segments (FR-3).

    Returns (resolved_segments, problems) — problems is a list of raw message
    strings (no ANSI); callers decide whether to print or discard them."""
    seg = dict(defaults)
    problems: list[str] = []
    for k, v in cast(dict[str, Any], file_seg or {}).items():
        if k not in seg:
            problems.append(f"unknown segment '{k}' in config")
        elif not isinstance(v, bool):
            problems.append(
                f"segment '{k}' must be true/false, got {v!r} — ignored"
            )
        else:
            seg[k] = v
    return seg, problems


def cfg_resolve_layout(default_layout: list[Line], raw_lines: Any) -> list[Line]:
    """If the file has ANY [[line]] block, it REPLACES the whole layout
    (all-or-nothing — a partial layout can't silently drop segments). Otherwise
    keep the default. Each block: min_rows (default 0) + segments list."""
    if not raw_lines:
        return list(default_layout)
    return [Line(int(item.get("min_rows", 0)), list(item.get("segments", [])))
            for item in raw_lines]


def cfg_resolve_external(raw: dict[str, Any], env: Env) -> tuple[str, int]:
    """Resolve (dir, default_ttl) from defaults < [external] file.
    Env overrides are applied later by cfg_bind_scalars (FR-2)."""
    file_ext: dict[str, Any] = cast(dict[str, Any], raw.get("external") or {})
    ttl = _EXTERNAL_CACHE_TTL
    fv: Any = file_ext.get("ttl")
    if isinstance(fv, int) and not isinstance(fv, bool):
        ttl = fv
    return cfg_segments_dir(file_ext, env), ttl


def cfg_place_external(
    layout: list[Line], specs: list["ExtSpec"]
) -> tuple[list[Line], list["ExtSpec"], list[str]]:
    """Insert each spec's id into the resolved layout at its row/position and
    return (new_layout, finalized_specs, problems). Resolves line=0 to the last
    row and clamps out-of-range rows. Specs are applied in their (filename, id)
    sort order so same-slot externals are deterministic.

    problems is a list of raw message strings (no ANSI); callers decide whether
    to print or discard them."""
    if not layout:
        return list(layout), [], []
    rows = [list(ln.segments) for ln in layout]
    nrows = len(rows)
    final: list[ExtSpec] = []
    problems: list[str] = []
    for spec in specs:
        want = spec.line or nrows                      # 0 => last row
        idx = want - 1
        if idx < 0 or idx >= nrows:
            problems.append(
                f"segment '{spec.id}' line={want} out of range — clamped to row {nrows}"
            )
            idx = nrows - 1
        kind, ref = spec.position
        segs = rows[idx]
        if kind == "start":
            segs.insert(0, spec.id)
        elif kind == "after" and ref in segs:
            segs.insert(segs.index(ref) + 1, spec.id)
        elif kind == "before" and ref in segs:
            segs.insert(segs.index(ref), spec.id)
        else:                                          # end, or after/before missing ref
            segs.append(spec.id)
        final.append(spec._replace(line=idx + 1))
    new_layout = [Line(layout[i].min_rows, rows[i]) for i in range(nrows)]
    return new_layout, final, problems


def cfg_load_config_verbose(  # pylint: disable=too-many-locals,too-many-branches
    env: Env,
) -> "tuple[Config, list[str]]":
    """Resolve the full Config: internal defaults < TOML file < env.

    Resolves segments, layout, palette, ramps, and the [git] knobs. Also
    discovers external drop-in providers from the [external] `dir` (default
    ~/.config/ai-kit/segments) BEFORE resolving segments — so each provider id
    is a known segment key (enabled by default, disable via `[segments] <id> =
    false`) — and places them into the layout. The resolved providers land in
    Config.external (an ExternalConf whose `.providers` holds the finalized
    ExtSpec list, `.dir` the providers directory, `.cache_ttl` the default TTL).

    All CC_AI_KIT_* config env reads funnel through cfg_bind_scalars /
    cfg_bind_segments (FR-2/FR-3 access/convert/bind layer). The bootstrap
    CC_AI_KIT_CONFIG_FILE read is the sole exception (FR-1.7).

    Returns (Config, problems) where problems is a list of raw message strings
    (no ANSI, no 'status-line: ' prefix) describing every skipped/clamped value.
    Emits NOTHING to stderr — callers decide what to do with problems."""
    base = cfg_default_config()
    raw = cfg_load_toml(cfg_config_path(env))
    problems: list[str] = []

    # External providers first: their ids must be known segment keys before
    # cfg_resolve_segments runs, so `[segments] <id> = false` is honored (not warned)
    # and they default to enabled. TOML-based dir/ttl resolved here; env overrides applied below.
    ext_dir, ext_ttl = cfg_resolve_external(raw, env)
    cache_base = cfg_cache_base(env)

    # git: resolve from TOML first, then env overrides via single reader below.
    git: dict[str, Any] = dict(_GIT_DEFAULTS)
    for k, v in cast(dict[str, Any], raw.get("git") or {}).items():
        problem = cfg_git_key_problem(k, v)
        if problem == "unknown":
            problems.append(f"unknown [git] key '{k}'")
        elif problem == "bad_ttl":
            problems.append(
                f"[git] cache_ttl must be an integer, got {v!r} — ignored"
            )
        else:
            git[k] = v

    # FR-2/FR-3: env binds via the access/convert layer. Scalars bind BEFORE
    # discovery so the env-bound external dir is the one scanned; segments bind
    # AFTER discovery so provider ids are known segment keys.
    git, ext_dir, ext_ttl, prob_scalars = cfg_bind_scalars(raw, env, git, ext_dir, ext_ttl)
    problems.extend(prob_scalars)

    # Discover external providers using the final resolved dir/ttl (env wins over TOML).
    specs = core_discover_external(ext_dir, ext_ttl, os.path.join(cache_base, "segments"))

    # segments resolved exactly once: defaults + external ids < [segments] TOML < env.
    # External provider ids are known segment keys (default enabled, disable via
    # `[segments] <id> = false`).
    seg_defaults = dict(base.segments)
    for s in specs:
        seg_defaults.setdefault(s.id, True)
    segments, prob_seg_file = cfg_resolve_segments(seg_defaults, raw.get("segments"))
    problems.extend(prob_seg_file)
    segments, prob_segs = cfg_bind_segments(raw, env, segments)          # env pass + problems
    problems.extend(prob_segs)

    layout = cfg_resolve_layout(base.layout, raw.get("line"))
    layout, external, prob_place = cfg_place_external(layout, specs)
    problems.extend(prob_place)
    palette: dict[str, str] = {}
    for k, v in cast(dict[str, Any], raw.get("palette") or {}).items():
        if k in _PALETTE_DEFAULTS:
            palette[k] = str(v)
        else:
            problems.append(f"unknown palette key '{k}'")
    ramps: dict[str, dict[str, str]] = {}
    for band, table in cast(dict[str, Any], raw.get("ramp") or {}).items():
        if band not in _RAMP_DEFAULTS:
            problems.append(f"unknown ramp '{band}'")
            continue
        if not isinstance(table, dict):
            problems.append(f"ramp '{band}' must be a table — ignored")
            continue
        ramps[band] = {str(k): str(v) for k, v in cast(dict[Any, Any], table).items()}
    cfg = Config(segments=segments, layout=layout, palette=palette, ramps=ramps,
                 git=git,
                 external=ExternalConf(dir=ext_dir, cache_ttl=ext_ttl, providers=external),
                 cache_base=cache_base)
    return cfg, problems


def cfg_load_config(env: Env) -> "Config":
    """Silent wrapper around cfg_load_config_verbose — discards all problems.

    The render path calls this so it emits nothing to stderr. Use
    cfg_load_config_verbose when you need the problem list (e.g. the doctor)."""
    cfg, _ = cfg_load_config_verbose(env)
    return cfg


def cfg_cache_base(env: Env) -> str:
    """${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit — root of every ai-kit on-disk cache."""
    base = env.get("XDG_CACHE_HOME") or os.path.join(env.get("HOME", ""), ".cache")
    return os.path.join(base, "ai-kit")


def cfg_segments_dir(file_external: Any, env: Env) -> str:
    """Resolve the providers directory from [external].dir (TOML) or the XDG default.
    Env override (CC_AI_KIT_EXTERNAL_DIR) is applied later by cfg_bind_scalars
    (FR-2); this function is TOML + XDG only."""
    ext_block: dict[str, Any] = cast(dict[str, Any], file_external or {})
    d: str | None = ext_block.get("dir")
    if d:
        return os.path.expanduser(d)
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
    return os.path.join(base, "ai-kit", "segments")


def cfg_resolve_effort(raw: dict[str, Any]) -> str:
    """The *resolved* effort level (low..max) as a normalized lowercase string, or "".

    This is the live per-turn level the API reported, read from raw["effort"]["level"]
    (JSON + settings only — FR-1.9 dropped the CLAUDE_EFFORT env source). It is never
    "auto" — auto is a *setting*, detected separately from disk by
    probe_effort_setting_is_auto. A stray "auto" in the resolved field (transition states)
    is normalized away so it can't reach the level table."""
    effort_block: dict[str, Any] = cast(dict[str, Any], raw.get("effort") or {})
    level: str = str(effort_block.get("level") or "").strip().lower()
    return "" if level == "auto" else level


# ═══ 3. probe_ — side-effecting data gatherers (git / proc / fs / subprocess) ═
# Two sub-tiers: raw gatherers on primitives (probe_git_snapshot(work_dir), …) and
# the memoized segment-facing accessors signed (ctx) (probe_git_for, probe_rss, …).
# Classified by NATURE (side-effecting), not by which segment consumes them.


def probe_terminal_size(env: Env) -> tuple[int, int, bool]:
    """Resolve (cols, lines, assumed). Fallback chain, first hit wins per dimension:
      1. STATUSLINE_COLS / STATUSLINE_LINES env
      2. COLUMNS / LINES env
      3. stty size      (via /dev/tty)
      4. tput cols/lines (via /dev/tty — macOS / setups where stty size is absent)
      5. assumed 200x40 default (assumed=True)"""
    def _int(*keys: str) -> int | None:
        for k in keys:
            v = env.get(k)
            if v and str(v).isdigit() and int(v) > 0:
                return int(v)
        return None

    cols = _int("STATUSLINE_COLS", "COLUMNS")
    lines = _int("STATUSLINE_LINES", "LINES")
    if cols is None or lines is None:
        # One controlling-tty open serves both probes: stty first, then tput as the
        # macOS/terminfo fallback (_run closes over `tty` intentionally).
        try:
            with open("/dev/tty", encoding="utf-8") as tty:
                def _run(*cmd: str) -> str:
                    return subprocess.run(list(cmd), stdin=tty, capture_output=True,
                                          text=True, timeout=1, check=False).stdout
                size = _run("stty", "size").split()
                if len(size) == 2:
                    lines = lines or int(size[0])
                    cols = cols or int(size[1])
                if cols is None or lines is None:
                    cols = cols or util_to_int(_run("tput", "cols").strip())
                    lines = lines or util_to_int(_run("tput", "lines").strip())
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    assumed = False
    if cols is None:
        cols, assumed = 200, True
    if lines is None:
        lines, assumed = 40, True
    return cols, lines, assumed


def probe_effort_setting_is_auto(work_dir: str, home: str) -> bool:
    """True when the effort *setting* is auto — i.e. `effortLevel` is absent (or
    literally "auto") across the settings chain.

    Precedence high->low: the project's .claude/settings.local.json, then
    .claude/settings.json, then ~/.claude/settings.json. The first file that defines
    `effortLevel` decides (explicit level -> not auto); if none define it, it's auto."""
    for path in (os.path.join(work_dir, ".claude", "settings.local.json"),
                 os.path.join(work_dir, ".claude", "settings.json"),
                 os.path.join(home, ".claude", "settings.json")):
        try:
            with open(path, encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(cfg, dict) and "effortLevel" in cfg:
            return str(cast(dict[str, Any], cfg)["effortLevel"]).strip().lower() == "auto"
    return True


def probe_git_worktree_info(work_dir: str) -> tuple[bool, bool, str]:
    """(in_repo, is_worktree, name) from ONE `git rev-parse`. is_worktree is True
    when work_dir sits in a linked worktree (git-dir != git-common-dir). name is
    that worktree directory's basename (from --show-toplevel), only when in a
    linked worktree; "" otherwise. Outside any repo → (False, False, "")."""
    out = subprocess.run(
        ["git", "-C", work_dir, "rev-parse",
         "--git-dir", "--git-common-dir", "--show-toplevel"],
        capture_output=True, text=True, check=False).stdout
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False, False, ""                 # not a git repo
    is_worktree = lines[0] != lines[1]          # git-dir != git-common-dir
    top = lines[2] if len(lines) >= 3 else ""
    name = os.path.basename(top.rstrip("/")) if (is_worktree and top) else ""
    return True, is_worktree, name


def probe_worktree_info_cached(work_dir: str, ttl: int, cache_base: str) -> tuple[bool, bool, str]:
    """probe_git_worktree_info wrapped in an on-disk TTL cache — the worktree rev-parse
    rarely changes, so it is cached ~ttl s keyed by work_dir. The cache is active
    only when ttl > 0 AND a cache_base is resolved: ttl <= 0 forces a fresh
    rev-parse every render, and an empty cache_base means no cache location was
    resolved (a direct/test call with no Config) so we never touch disk — this is
    what keeps such calls from writing a stray `./git/` under the cwd. In
    production cfg_load_config always supplies a real cache_base. Cache I/O is
    best-effort."""
    cached = ttl > 0 and bool(cache_base)
    path = util_git_cache_path(work_dir, cache_base) if cached else ""
    if cached:
        try:
            if time.time() - os.stat(path).st_mtime < ttl:
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
                return d["in_repo"], d["is_worktree"], d["wt_name"]
        except (OSError, ValueError, KeyError):
            pass
    info = probe_git_worktree_info(work_dir)
    if cached:                          # caching off (ttl<=0 or no cache_base) -> never write
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"in_repo": info[0], "is_worktree": info[1], "wt_name": info[2]}, f)
        except OSError:
            pass
    return info


def probe_git_snapshot(work_dir: str, config: Optional["Config"] = None) -> "GitSnapshot":
    """The single git probe behind the `git_branch`, `git_dirty`, and
    `alt_git_worktree` segments.

    `config` is the resolved Config object — the probe reads its cache TTL and
    cache_base FROM it (never from env, never as bare args). config=None (direct/
    test calls with no Config) falls back to the built-in defaults.

    Returns GitSnapshot(in_repo, branch, dirty, is_worktree, wt_name). `branch`
    and `dirty` come from one always-fresh `git status --porcelain --branch`
    (full untracked walk); the worktree rev-parse is cached ~ttl s on disk under
    cache_base/git/ (it rarely changes). The probe owns its policy and always
    does the full work — there are no per-call gating knobs: laziness is the
    compute gate (Context._git only runs when an enabled git segment reads a git
    field, so a disabled git segment never triggers the probe at all)."""
    ttl = (config.git or {}).get("cache_ttl", _GIT_CACHE_TTL) if config else _GIT_CACHE_TTL
    cache_base = config.cache_base if config else ""
    out = subprocess.run(["git", "-C", work_dir, "status", "--porcelain", "--branch"],
                         capture_output=True, text=True,
                         check=False).stdout.splitlines()
    branch = util_branch_from_porcelain(out[0] if out else "")
    changes = out[1:]   # change lines follow the `## <branch>` header
    if any(ln.startswith(("??", "A", "D")) or ln.startswith(" D") for ln in changes):
        dirty = "untracked"
    elif any(ln.strip() for ln in changes):
        dirty = "modified"
    else:
        dirty = "clean"
    in_repo, is_worktree, wt_name = probe_worktree_info_cached(work_dir, ttl, cache_base)
    return GitSnapshot(in_repo, branch, dirty, is_worktree, wt_name)


# ── Process RSS (cross-platform) ──────────────────────────────────────────────
# Platform probe: Linux → /proc readers; macOS/other → `ps` readers; any read
# failure → None (the segment hides). Three facts per pid — command name, parent
# pid, resident memory (kB) — exposed by six thin readers (_comm/_ppid/_rss_kb ×
# _via_proc/_via_ps). probe_rss_bytes picks a backend by the probe and walks the
# parent chain, returning RSS ONLY on a confirmed `claude` ancestor — otherwise
# None, so it never reports a stray process (the wezterm <10mb bug). The readers
# return comm verbatim; probe_rss_bytes is the single basename-normalization point.
def probe_comm_via_proc(pid: int) -> str | None:
    """Read process name from /proc/<pid>/comm, or None on error."""
    try:
        with open(f"/proc/{pid}/comm", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def probe_ppid_via_proc(pid: int) -> int | None:
    """Read parent PID from /proc/<pid>/stat field 4, or None on error."""
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as f:
            return int(f.read().split()[3])
    except (OSError, IndexError, ValueError):
        return None


def probe_rss_kb_via_proc(pid: int) -> int | None:
    """Read VmRSS (kB) from /proc/<pid>/status, or None on error."""
    try:
        with open(f"/proc/{pid}/status", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except (OSError, IndexError, ValueError):
        return None
    return None


def probe_ps_field(pid: int, fieldname: str) -> str | None:
    """One `ps -o <fieldname>= -p <pid>` value as a stripped string, or None."""
    try:
        out = subprocess.run(["ps", "-o", f"{fieldname}=", "-p", str(pid)],
                             capture_output=True, text=True, timeout=1,
                             check=False).stdout.strip()
        return out or None
    except (OSError, subprocess.SubprocessError):
        return None


def probe_comm_via_ps(pid: int) -> str | None:
    """Read process name via `ps -o comm=`, or None on error."""
    return probe_ps_field(pid, "comm")


def probe_ppid_via_ps(pid: int) -> int | None:
    """Read parent PID via `ps -o ppid=`, or None on error."""
    return util_to_int(probe_ps_field(pid, "ppid"))


def probe_rss_kb_via_ps(pid: int) -> int | None:
    """Read RSS (kB) via `ps -o rss=`, or None on error."""
    return util_to_int(probe_ps_field(pid, "rss"))


def probe_rss_bytes() -> int | None:
    """Resident memory (bytes) of the ancestor `claude` process, or None.

    Cross-platform via a capability probe: Linux /proc, else `ps`. Walk up the parent
    chain (bounded) and return RSS only on a `claude` match."""
    use_proc = os.path.isdir("/proc")
    comm_of = probe_comm_via_proc if use_proc else probe_comm_via_ps
    ppid_of = probe_ppid_via_proc if use_proc else probe_ppid_via_ps
    rss_kb_of = probe_rss_kb_via_proc if use_proc else probe_rss_kb_via_ps

    pid = os.getppid()
    for _ in range(8):
        name = comm_of(pid)
        if name is None:
            return None
        # `ps -o comm=` can return a full path on macOS; normalize here so both
        # backends compare the same bare name.
        if os.path.basename(name) == "claude":
            kb = rss_kb_of(pid)
            return kb * 1024 if kb is not None else None
        parent = ppid_of(pid)
        if parent is None or parent in (0, pid):
            return None
        pid = parent
    return None


def probe_transcript_bytes(path: str) -> int | None:
    """Return the transcript file size in bytes, or None if it is missing."""
    if not path or not os.path.isfile(path):
        return None
    try:
        return os.path.getsize(path)
    except OSError:
        return None


def probe_todo_from_tasks_dir(
    config_dir: str, session: Any
) -> tuple[str | None, str | None] | None:
    """Read Claude's materialized managed-Task state: one <id>.json per task under
    <config_dir>/tasks/<session>/. Returns (state, text) when task files exist
    (authoritative — may be (None, None) if all are done), else None to try the
    next source. This is O(task count) — no transcript replay."""
    if not util_safe_session(session):
        return None
    d = os.path.join(config_dir, "tasks", session)
    try:
        names = [n for n in os.listdir(d) if n.endswith(".json")]
    except OSError:
        return None
    if not names:
        return None
    # Sort by numeric id so creation order (and thus "last in_progress") is stable.
    tasks: list[dict[str, Any]] = []
    for n in sorted(names, key=lambda x: int(x[:-5]) if x[:-5].isdigit() else 0):
        try:
            with open(os.path.join(d, n), encoding="utf-8") as f:
                tasks.append(cast(dict[str, Any], json.load(f)))
        except (OSError, ValueError):
            continue
    return util_pick_from_tasks(tasks) or (None, None)


def probe_todo_from_todos_dir(
    config_dir: str, session: Any
) -> tuple[str | None, str | None] | None:
    """Read Claude's materialized TodoWrite snapshot: the most recent
    <config_dir>/todos/<session>*-agent-*.json (a single todos array). Returns
    (state, text) when such a file exists, else None to try the next source."""
    if not util_safe_session(session):
        return None
    d = os.path.join(config_dir, "todos")
    try:
        names = [n for n in os.listdir(d)
                 if n.startswith(session) and "-agent-" in n and n.endswith(".json")]
    except OSError:
        return None
    if not names:
        return None
    latest = max(names, key=lambda n: os.path.getmtime(os.path.join(d, n)))
    try:
        with open(os.path.join(d, latest), encoding="utf-8") as f:
            todos: Any = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(todos, list):
        return None
    return util_pick_from_todos(cast(list[dict[str, Any]], todos)) or (None, None)


def probe_todo_from_transcript(  # pylint: disable=too-many-branches
    path: str | None,
) -> tuple[str | None, str | None]:
    """Last-resort fallback: replay the transcript JSONL to reconstruct task /
    todo state. O(transcript size) — used only when no materialized state exists
    (e.g. running outside Claude Code, or an unrecognized on-disk layout)."""
    if not path or not os.path.isfile(path):
        return None, None

    tasks: list[dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as fh:
            todo_snapshots: list[list[dict[str, Any]]] = []
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj: Any = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(obj, dict):
                    continue
                task_names = ("TaskCreate", "TaskUpdate")
                for tu in util_iter_tool_uses(cast(dict[str, Any], obj), task_names):
                    inp: dict[str, Any] = cast(dict[str, Any], tu.get("input") or {})
                    if tu["name"] == "TaskCreate":
                        tasks.append({
                            "id": len(tasks) + 1,
                            "subject": inp.get("subject", ""),
                            "activeForm": inp.get("activeForm") or inp.get("subject", ""),
                            "status": "pending",
                        })
                    else:
                        tid = str(inp.get("taskId"))
                        for t in tasks:
                            if str(t["id"]) == tid and inp.get("status"):
                                t["status"] = inp["status"]
                for tu in util_iter_tool_uses(cast(dict[str, Any], obj), ("TodoWrite",)):
                    inp2: dict[str, Any] = cast(dict[str, Any], tu.get("input") or {})
                    todo_snapshots.append(cast(list[dict[str, Any]], inp2.get("todos") or []))
    except OSError:
        return None, None

    if tasks:
        return util_pick_from_tasks(tasks) or (None, None)
    if todo_snapshots:
        return util_pick_from_todos(todo_snapshots[-1]) or (None, None)
    return None, None


def probe_current_todo(path: str | None, session: str | None = None,
                 config_dir: str | None = None) -> tuple[str | None, str | None]:
    """Return (state, text) for the active TODO, or (None, None).

    Prefer Claude's materialized state on disk — the managed-Task files, then a
    TodoWrite snapshot — which is cheap (O(task count)) and authoritative. Only
    when neither exists do we replay the transcript (O(transcript size)). Without
    session/config_dir (direct/test calls) we go straight to the transcript."""
    if session and config_dir:
        for source in (probe_todo_from_tasks_dir, probe_todo_from_todos_dir):
            got = source(config_dir, session)
            if got is not None:
                return got
    return probe_todo_from_transcript(path)


# ── per-render memoized probe accessors (module-level; cost lands in FR-R.2) ──

def _memo(ctx: "Context", key: str, fn: "Callable[[], Any]") -> Any:
    """Run fn() once per render, caching the result on ctx.probe_cache."""
    cache = ctx.probe_cache
    if key not in cache:
        cache[key] = fn()
    return cache[key]


def probe_git_for(ctx: "Context") -> "GitSnapshot":
    """Memoized git snapshot for this render (branch/dirty/worktree/…)."""
    return _memo(ctx, "git",
                 lambda: probe_git_snapshot(ctx.work_dir, ctx.line_conf))


def probe_ago(ctx: "Context") -> str:
    """Memoized human-readable age of the transcript file, or ''."""
    def _compute() -> str:
        t = ctx.transcript
        if t and os.path.isfile(t):
            return fmt_ago(int(time.time()) - int(os.path.getmtime(t)))
        return ""
    return _memo(ctx, "ago", _compute)


def probe_effort_auto(ctx: "Context") -> bool:
    """Memoized: True when the Claude effort setting is 'auto'."""
    return _memo(ctx, "effort_auto",
                 lambda: probe_effort_setting_is_auto(ctx.work_dir, ctx.home))


def probe_todo(ctx: "Context") -> tuple[str | None, str | None]:
    """Memoized (state, text) pair for the active TODO, or (None, None)."""
    return _memo(ctx, "todo",
                 lambda: probe_current_todo(ctx.transcript, ctx.session, ctx.claude_dir))


def probe_chat_size(ctx: "Context") -> int | None:
    """Memoized transcript file size in bytes, or None."""
    return _memo(ctx, "chat_size", lambda: probe_transcript_bytes(ctx.transcript))


def probe_rss(ctx: "Context") -> int | None:
    """Memoized process RSS in bytes, or None."""
    return _memo(ctx, "rss", probe_rss_bytes)


# ═══ 4. fmt_ — pure formatters (number / tokens / duration / bytes / ago) ═════
# Formatters are pure value→display-string and consumer-independent: the same
# fmt_ produces the same text regardless of which segment calls it.


def fmt_number(n: int | float) -> str:
    """Thousands separators: 1234567 -> '1,234,567'."""
    return f"{int(n):,}"


def fmt_time_ms(ms: int | float) -> str:
    """Human-readable duration from milliseconds (matches statusline.sh)."""
    ms = int(ms)
    if ms < 1000:
        return f"{ms}ms"
    if ms < 60_000:
        return f"{ms // 1000}s"
    if ms < 3_600_000:
        return f"{ms // 60_000}m {(ms % 60_000) // 1000}s"
    return f"{ms // 3_600_000}h {(ms % 3_600_000) // 60_000}m"


def fmt_tokens(n: int | float) -> str:
    """200000 -> '200K', 1000000 -> '1M'."""
    n = int(n)
    if n >= 1_000_000:
        return f"{n // 1_000_000}M"
    if n >= 1000:
        return f"{n // 1000}K"
    return str(n)


def fmt_ago(secs: int | float) -> str:
    """Seconds since last activity as an 'ago' string."""
    secs = int(secs)
    if secs <= 0:
        return "just now"
    if secs < 60:
        return f"{secs}s ago"
    if secs < 3600:
        return f"{secs // 60}m {secs % 60}s ago"
    return f"{secs // 3600}h {(secs % 3600) // 60}m ago"


def fmt_bytes(n: int | float) -> str:
    """IEC byte size matching `numfmt --to=iec --suffix=B`: ceiling rounding,
    one decimal only when the scaled value is < 10."""
    n = int(n)
    if n < 1024:
        return f"{n}B"
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(n)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    if v < 10:
        return f"{math.ceil(v * 10) / 10:.1f}{units[i]}"
    return f"{math.ceil(v)}{units[i]}"


def fmt_duration(ns: int | float) -> str:
    """Adaptive duration from nanoseconds: ns / µs / ms / s, picking the largest
    unit that keeps the value >= 1. One decimal only when the scaled value is
    < 10 (matching fmt_bytes' style)."""
    ns = int(ns)
    if ns < 1000:
        return f"{ns}ns"
    for div, suffix in ((1_000_000_000, "s"), (1_000_000, "ms"), (1000, "µs")):
        if ns >= div:
            v = ns / div
            return f"{v:.1f}{suffix}" if v < 10 else f"{v:.0f}{suffix}"
    return f"{ns}ns"


_NUM_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "fifteen": 15,
    "twenty": 20, "thirty": 30, "sixty": 60,
}


_UNIT_ABBR = {
    "hour": "h", "hours": "h", "day": "d", "days": "d",
    "week": "w", "weeks": "w", "month": "mo", "months": "mo",
}


def fmt_rate_key_label(key: str) -> str:
    """five_hour -> '5h', thirty_day -> '30d'. Unknown words pass through."""
    num, _, unit = key.partition("_")
    num = _NUM_WORDS.get(num, num)
    unit = _UNIT_ABBR.get(unit, unit)
    return f"{num}{unit}"


# ═══ 5. util_ — pure non-format helpers (color / width / truncate / fit / parse)
# Shared by default; classify by NATURE, not caller. A helper keeps its prefix even
# if only one tier calls it today (a caller-based name rots when reuse appears).
# Extraction seam: git/proc-only helpers travel with those probes if ever
# externalized; the cross-tier ones are the irreducible shared core. The exact
# caller census is regenerable on demand via AST — not kept here.


_SGR_SEQ = re.compile(r"\x1b\[[0-9;]*m")            # an SGR color/style escape


_CSI_SEQ = re.compile(r"\x1b\[[0-9;?]*([A-Za-z])")  # any CSI; group = final byte


_OSC_SEQ = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")


_STRAY_ESC = re.compile(r"\x1b(?!\[[0-9;]*m)")      # ESC not starting an SGR


_C0_CTRL = re.compile(r"[\x00-\x09\x0b-\x1a\x1c-\x1f\x7f]")  # controls (incl. TAB) except NL/ESC


def util_truncate_visible(s: str, avail: int) -> str:
    """Cut s to at most `avail` visible cells, preserving zero-width SGR escapes,
    appending RESET if any SGR was emitted. avail <= 0 -> ''."""
    if avail <= 0:
        return ""
    out: list[str] = []
    width, i, n, saw_sgr = 0, 0, len(s), False
    while i < n:
        m = _SGR_SEQ.match(s, i)
        if m:
            out.append(m.group(0))
            saw_sgr = True
            i = m.end()
            continue
        w = util_char_width(s[i])
        if width + w > avail:
            break
        out.append(s[i])
        width += w
        i += 1
    res = "".join(out)
    if saw_sgr and not res.endswith(RESET):
        res += RESET
    return res


def util_pick_color(pct: float, ramp: list[tuple[float, str]]) -> str:
    """Return the color for the first ceil that pct is strictly below."""
    for ceil, color in ramp:
        if pct < ceil:
            return color
    return ramp[-1][1]


_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


# BMP symbols we render that terminals draw 2 cells wide (east_asian_width
# misclassifies these as narrow). Add a codepoint here if a new wide BMP glyph
# is introduced in a segment.
_WIDE_BMP = {0x23F0, 0x23F1, 0x23F8, 0x26A1}  # ⏰ ⏱ ⏸ ⚡


def util_char_width(ch: str) -> int:
    """Display cells for one char: 0 (combining/zero-width), 1, or 2 (wide)."""
    if unicodedata.combining(ch):
        return 0
    o = ord(ch)
    if 0xFE00 <= o <= 0xFE0F:                         # variation selectors render in-place
        return 0
    if o >= 0x1F300:                                  # emoji / pictographs (SMP)
        return 2
    if o in _WIDE_BMP:
        return 2
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def util_visible_width(s: str) -> int:
    """Terminal display width of s, ignoring ANSI SGR escapes."""
    return sum(util_char_width(c) for c in _ANSI_RE.sub("", s))


def util_first_fitting(variants: Sequence[str | None], avail: int) -> str | None:
    """Return the first (richest) truthy variant whose display width fits avail.

    None if none fit. Builders pass their variants rich-first so the widest
    affordable detail level wins; returning None is a builder self-hiding."""
    for v in variants:
        if v and util_visible_width(v) <= avail:
            return v
    return None


# Glyphs we model as wide (_WIDE_BMP) but that render NARROW bare on many
# terminals. Forcing VS16 (emoji presentation) makes them render wide everywhere
# so the single-space util_icon gap is always one clean column. ⏰ (U+23F0) is
# already EAW=W, so it is intentionally absent.
_ICON_VS16 = {"⏱", "⏸", "⚡"}  # ⏱ ⏸ ⚡


def util_icon(glyph: str, text: str) -> str:
    """Render `glyph` + exactly one space + `text` — the one place icon→text
    spacing is decided. Narrow-rendering glyphs get VS16 so the gap is one
    visible column regardless of terminal emoji handling."""
    g = f"{glyph}️" if glyph in _ICON_VS16 else glyph
    return f"{g} {text}"


# One parser produces every SGR escape. Base forms (by shape): palette NAME
# (letter-led, resolved against `palette`), raw SGR ("38;5;208" passthrough), or
# hex ("#rgb"/"#rrggbb"/"#rrggbbaa", alpha dropped). "+bold/+dim/+italic/
# +underline" modifiers prepend 1/2/3/4 in ascending order. Invalid -> None.
_MOD_SGR = {"bold": "1", "dim": "2", "italic": "3", "underline": "4"}


def util_hex_to_sgr(spec: str) -> str | None:
    """'#rgb' / '#rgba' / '#rrggbb' / '#rrggbbaa' -> '38;2;r;g;b' (alpha
    dropped). None if not valid hex of a supported length."""
    h = spec[1:]
    if len(h) in (3, 4):                 # short form: expand each nibble, drop alpha
        h = "".join(c * 2 for c in h[:3])
    elif len(h) == 8:                    # long form with alpha: drop the alpha byte
        h = h[:6]
    if len(h) != 6 or re.fullmatch(r"[0-9a-fA-F]{6}", h) is None:
        return None
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"38;2;{r};{g};{b}"


def util_parse_color(spec: Any, palette: dict[str, str] | None = None) -> str | None:
    """Resolve a colorspec to '\\033[...m', or None if invalid. See section
    header for the grammar. `palette` ({NAME: sgr params}) is required only for
    name lookups; raw-SGR and hex specs ignore it."""
    if not spec:
        return None
    base, *mod_names = str(spec).split("+")
    base = base.strip()
    mods: list[str] = []
    for m in mod_names:
        code = _MOD_SGR.get(m.strip().lower())
        if code is None:
            return None
        mods.append(code)
    if base.startswith("#"):
        params = util_hex_to_sgr(base)
    elif base[:1].isalpha():
        params = (palette or {}).get(base)
    elif re.fullmatch(r"[0-9;]+", base):
        params = base
    else:
        params = None
    if params is None:
        return None
    ordered = sorted(set(mods), key=int)
    return "\033[" + ";".join([*ordered, params]) + "m"


_THRESHOLD_MULT = {"k": 1024, "M": 1024 ** 2, "G": 1024 ** 3}


# Time thresholds (render_time ramp) resolve to NANOSECONDS, matching what the
# segment measures via time.perf_counter_ns(). "µs" and ASCII "us" both accepted.
_TIME_MULT_NS = {"ns": 1, "us": 1000, "µs": 1000, "ms": 1_000_000, "s": 1_000_000_000}


def util_parse_threshold(key: str | int | float) -> float:
    """Ramp threshold -> comparable number. 'inf'/inf -> INF; '512k'/'5M'/'1G'
    -> bytes (1024-based); '50ms'/'2s'/'500us'/'100ns' -> nanoseconds; bare int /
    numeric string -> that int (a percent). Raises ValueError on anything else."""
    if isinstance(key, float):
        return key
    if isinstance(key, int):
        return key
    s = str(key).strip()
    if s.lower() == "inf":
        return INF
    m = re.fullmatch(r"(\d+)([kMG])", s)
    if m:
        return int(m.group(1)) * _THRESHOLD_MULT[m.group(2)]
    m = re.fullmatch(r"(\d+)(ns|µs|us|ms|s)", s)
    if m:
        return int(m.group(1)) * _TIME_MULT_NS[m.group(2)]
    return int(s)   # ValueError on garbage


def util_rate_color(pct: float, theme: "Theme") -> str:
    """Pick the rate-limit ramp color for a usage percentage."""
    return util_pick_color(float(pct), theme.ramps["rate"])


def util_branch_from_porcelain(header: str) -> str:
    """Extract the branch from a `git status --porcelain --branch` header line
    (the `## ...` line). Returns "" for a detached HEAD, matching the old
    `git branch --show-current` behaviour. Git forbids ".." in refnames, so the
    "..." upstream separator can never collide with a branch name."""
    if not header.startswith("## "):
        return ""
    rest = header[3:]
    if rest.startswith("HEAD (no branch)"):                       # detached
        return ""
    for prefix in ("No commits yet on ", "Initial commit on "):   # unborn branch
        if rest.startswith(prefix):
            return rest[len(prefix):].strip()
    return rest.split("...", 1)[0].strip()                        # branch[...upstream]


def util_git_cache_path(work_dir: str, cache_base: str) -> str:
    """Per-work_dir cache file for the worktree probe under <cache_base>/git/."""
    key = hashlib.sha1(os.path.abspath(work_dir).encode()).hexdigest()[:16]
    return os.path.join(cache_base, "git", key)


def util_iter_tool_uses(
    line_obj: dict[str, Any], names: tuple[str, ...]
) -> Iterator[dict[str, Any]]:
    """Yield tool_use blocks whose name is in `names` from a transcript line object.
    In real transcripts message.content is a list of blocks for tool turns but
    a plain string for text turns — only iterate when it is a list of dicts."""
    msg: dict[str, Any] = cast(dict[str, Any], line_obj.get("message") or {})
    content: Any = msg.get("content")
    if not isinstance(content, list):
        return
    for item in cast(list[Any], content):
        if not isinstance(item, dict):
            continue
        block = cast(dict[str, Any], item)
        if block.get("type") == "tool_use" and block.get("name") in names:
            yield block


def util_pick_from_tasks(tasks: list[dict[str, Any]]) -> tuple[str, str] | None:
    """Choose the active task from a managed-Task list (creation order). Active =
    the last in_progress, else the first pending. Returns (state, text) or None."""
    in_prog = [t for t in tasks if t.get("status") == "in_progress"]
    if in_prog:
        return "in_progress", in_prog[-1].get("activeForm") or in_prog[-1].get("subject", "")
    pending = [t for t in tasks if t.get("status") == "pending"]
    if pending:
        return "pending", pending[0].get("subject", "")
    return None


def util_pick_from_todos(todos: list[dict[str, Any]]) -> tuple[str, str] | None:
    """Choose the active item from a TodoWrite snapshot. Active = the first
    in_progress, else the first pending. Returns (state, text) or None."""
    in_prog = [t for t in todos if t.get("status") == "in_progress"]
    if in_prog:
        return "in_progress", in_prog[0].get("activeForm", "")
    pending = [t for t in todos if t.get("status") == "pending"]
    if pending:
        return "pending", pending[0].get("content", "")
    return None


def util_safe_session(s: Any) -> bool:
    """A session id is used as a single path component under the tasks/todos dir.
    Reject anything with a path separator or parent ref so it cannot escape that
    directory (path traversal)."""
    return bool(s) and not re.search(r"[/\\]|\.\.", s)


def util_display_dir(work_dir: str, home: str) -> str:
    """Return work_dir with home replaced by '~'; truncate to basename if too long."""
    shown = work_dir
    if home and work_dir.startswith(home):
        shown = "~" + work_dir[len(home):]
    if len(shown) <= PATH_MAX_LEN:
        return shown
    return os.path.basename(work_dir.rstrip("/")) or shown


def util_dirty_mark(dirty: str, theme: "Theme") -> str:
    """Return a colored dirty-state marker string ('✗', '~', or '') for the segment."""
    if dirty == "untracked":
        return f"{theme.c('RED')}✗{RESET}"
    if dirty == "modified":
        return f"{theme.c('YELLOW')}~{RESET}"
    return ""


def util_trunc_cols(s: str, limit: int) -> str:
    """Truncate s to at most `limit` display columns, appending `…` if cut.
    Column-aware (uses util_char_width) so a wide/multibyte name can't blow the budget."""
    if sum(util_char_width(c) for c in s) <= limit:
        return s
    out: list[str] = []
    width = 0
    for c in s:
        cw = util_char_width(c)
        if width + cw > limit - 1:          # reserve one column for the ellipsis
            break
        out.append(c)
        width += cw
    return "".join(out) + "…"


def util_to_int(s: str | None) -> int | None:
    """Parse a stripped string to int, or None on empty/non-numeric input. Pure
    probe-support parser (tput/ps output) — not config; see cfg_coerce for config."""
    try:
        return int(s) if s else None
    except ValueError:
        return None


def util_reset_suffix(reset: int | None, detail: str) -> str:
    """Reset stamp at the requested detail: 'long' | 'short' | 'none'.
    Pure formatting of resets_at in local time — never compared against the
    clock, so a wrong system time or a timezone change can't change what shows."""
    if reset is None or detail == "none":
        return ""
    dt = datetime.fromtimestamp(reset)
    if detail == "long":
        return f" (↺ {dt.strftime('%b %d %H:%M')})"   # e.g. Jun 07 14:10
    return f" (↺ {dt.strftime('%m-%d %H:%M')})"        # e.g. 06-07 14:10


def util_rate_str(rate_limits: dict[str, Any], detail: str, theme: "Theme") -> str | None:
    """Format the rate-limit buckets into one icon string at the given detail
    level ('long'/'short'/'none' reset stamp), or None when no bucket reports."""
    # Show every bucket that reports a percentage. Visibility never depends on
    # the clock — the reset stamp is shown only when there's room (via detail),
    # so timezone shifts / clock skew can't make a bucket vanish.
    parts: list[str] = []
    for key in sorted(rate_limits):
        info: dict[str, Any] = cast(dict[str, Any], rate_limits[key] or {})
        pct_raw: Any = info.get("used_percentage")
        if pct_raw is None:
            continue
        pct = float(pct_raw)
        reset_raw: Any = info.get("resets_at")
        reset: int | None = int(reset_raw) if reset_raw is not None else None
        color = util_rate_color(pct, theme)
        suffix = util_reset_suffix(reset, detail)
        parts.append(f"{fmt_rate_key_label(key)}: {color}{round(pct)}%{RESET}{suffix}")
    return util_icon("⚡", " | ".join(parts)) if parts else None


def util_sanitize_external(text: str, avail: int) -> str | None:
    """First non-empty line of `text`, SGR colors kept, every other control/CSI/OSC
    sequence stripped, width-truncated to `avail`. None if nothing renderable."""
    line = next((c for c in text.splitlines() if c.strip()), "").rstrip()
    if not line:
        return None
    line = _OSC_SEQ.sub("", line)
    line = _CSI_SEQ.sub(lambda m: m.group(0) if m.group(1) == "m" else "", line)
    line = _STRAY_ESC.sub("", line)
    line = _C0_CTRL.sub("", line)
    if not line.strip():
        return None
    return util_truncate_visible(line, avail) or None


def util_position_str(position: tuple[str, str]) -> str:
    """('after','clock') -> 'after:clock'; ('end','') -> 'end'."""
    kind, ref = position
    return f"{kind}:{ref}" if ref else kind


# ═══ 6. core_ — render machinery: Context, Theme, registry, packer, render ════


def core_str_set() -> set[str]:
    """Typed factory for Context.failed — bare `set` loses the generic parameter."""
    return set()


def core_probe_cache() -> dict[str, Any]:
    """Typed factory for Context.probe_cache — bare `dict` loses the generic parameter."""
    return {}


@dataclass
class Context:  # pylint: disable=too-many-instance-attributes  # per-render bag (D1)
    """Per-render bag handed to every builder (D1). Eager inputs are resolved at
    the SHELL/CONFIG boundary; expensive probes are memoized via `probe_cache`
    so each probe runs synchronously on first access — its cost lands inside the
    *measured* build of the first segment that reads it (FR-R.2) and later reads
    are free. Render bookkeeping (`failed`, `slowest`) lives here too. Attribute
    access only — never `ctx[...]` (D4). `raw` keeps `.get()`-chain access."""
    raw: dict[str, Any]             # incoming status JSON (the ONLY dict-style member)
    line_conf: "Config"
    theme: "Theme"
    # per-render terminal geometry (resolved by the SHELL; D6 — never on Config)
    cols: int
    lines: int
    dim_assumed: bool
    t_start: int | None
    # cheap eager fields (were build_data's `base`)
    model_name: str
    model_id: str
    effort: str
    work_dir: str
    home: str
    clock: str
    added: int
    removed: int
    cost: float
    total_ms: int
    api_ms: int
    context_pct: int
    context_max: int
    rate_limits: dict[str, Any]
    # probe inputs (locate materialized todo/task state; feed the memoized probes)
    transcript: str
    session: str
    claude_dir: str
    # render bookkeeping (D1) — mutated during the render
    failed: set[str] = field(default_factory=core_str_set)
    slowest: tuple[str, int] | None = None
    # memoization cache for per-render probes (keyed by probe name)
    probe_cache: dict[str, Any] = field(default_factory=core_probe_cache)


def core_build_context(raw: dict[str, Any], config: "Config", theme: "Theme",  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
                  cols: int, lines: int, dim_assumed: bool, t_start: int | None,
                  effort: str, home: str, claude_dir: str) -> "Context":
    """Assemble the per-render Context from the parsed status JSON and the
    already-resolved per-render inputs. Segment-agnostic and env-free: every
    env read happened in the CONFIG block; the SHELL hands the resolved values
    here. Expensive probes are deferred via probe_cache memoization."""
    model: dict[str, Any] = cast(dict[str, Any], raw.get("model") or {})
    cost: dict[str, Any] = cast(dict[str, Any], raw.get("cost") or {})
    ctx_win: dict[str, Any] = cast(dict[str, Any], raw.get("context_window") or {})
    workspace: dict[str, Any] = cast(dict[str, Any], raw.get("workspace") or {})
    work_dir: str = os.path.abspath(str(workspace.get("current_dir") or "."))
    transcript: str = str(raw.get("transcript_path") or "")
    # session_id locates the materialized task/todo state probe_current_todo prefers
    # over replaying the transcript; it also equals the transcript file basename.
    session: str = str(raw.get("session_id") or (
        os.path.splitext(os.path.basename(transcript))[0] if transcript else ""))
    return Context(
        raw=raw, line_conf=config, theme=theme,
        cols=cols, lines=lines, dim_assumed=dim_assumed, t_start=t_start,
        model_name=str(model.get("display_name") or ""),
        model_id=str(model.get("id") or "unknown"),
        effort=effort, work_dir=work_dir, home=home,
        clock=time.strftime("%H:%M"),
        # `or 0` (not get's default) so a PRESENT-but-null field — what a fresh
        # /clear session sends before any tokens/cost accrue — coalesces to 0
        # instead of raising on int()/math and blanking the whole bar.
        added=int(cost.get("total_lines_added") or 0),
        removed=int(cost.get("total_lines_removed") or 0),
        cost=float(cost.get("total_cost_usd") or 0),
        total_ms=int(cost.get("total_duration_ms") or 0),
        api_ms=int(cost.get("total_api_duration_ms") or 0),
        context_pct=int(ctx_win.get("used_percentage") or 0),
        context_max=int(ctx_win.get("context_window_size") or 0),
        rate_limits=cast(dict[str, Any], raw.get("rate_limits") or {}),
        transcript=transcript, session=session, claude_dir=claude_dir,
    )


def core_doctor_cmd() -> str:
    """A concrete, copy-pasteable doctor invocation for THIS install — resolved
    from the running interpreter and the SIBLING statusline-doctor.py path
    (~-collapsed). Never a bare '--doctor', which would assume the user is sitting
    in a repo clone. Builds the string only; it does not import the doctor module,
    so it stays usable from inside a failed render."""
    py = os.path.basename(sys.executable) or "python3"
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "statusline-doctor.py")
    home = os.path.expanduser("~")
    if path == home or path.startswith(home + os.sep):
        path = "~" + path[len(home):]
    return f"{py} {path} --doctor"


class Theme:
    """Resolved colors for one render. `palette` maps NAME -> bare SGR params;
    `ramps` band -> [(ceil, escape)]; `effort` level -> (escape, bar). `c()`
    memoizes util_parse_color and never raises (invalid spec -> '')."""

    def __init__(self, palette: dict[str, str],
                 ramps: dict[str, list[tuple[float, str]]],
                 effort: dict[str, tuple[str, str]]) -> None:
        self.palette = palette
        self.ramps = ramps
        self.effort = effort
        self._cache: dict[str, str] = {}

    def c(self, spec: str) -> str:
        """Resolve a color spec to an SGR string, memoizing the lookup."""
        if spec not in self._cache:
            self._cache[spec] = util_parse_color(spec, self.palette) or ""
        return self._cache[spec]


def core_resolve_palette(overrides: Any) -> dict[str, str]:
    """Merge _PALETTE_DEFAULTS with `overrides` ({NAME: spec}); each override
    value is parsed (hex / raw SGR / +mods — no name nesting) to bare params. A
    bad value warns and keeps the default."""
    palette = dict(_PALETTE_DEFAULTS)
    for name, value in cast(dict[str, Any], overrides or {}).items():
        if name not in _PALETTE_DEFAULTS:
            continue                       # unknown keys already warned in cfg_load_config
        esc = util_parse_color(value, palette=None)
        if esc is None:
            print(f"{_DIM}status-line: bad palette {name}={value!r} — keeping "
                  f"default{RESET}", file=sys.stderr)
            continue
        palette[name] = esc[2:-1]          # strip "\033[" .. "m" -> bare params
    return palette


def core_resolve_ramp(pairs: Any, palette: dict[str, str], band: str,
                  fallback: list[tuple[float, str]] | None) -> list[tuple[float, str]]:
    """Resolve [(threshold, colorspec)] -> [(ceil, escape)] sorted ascending.
    A bad band color falls back to that ceil's color in `fallback`; a bad
    threshold abandons the override and returns `fallback` whole. `fallback` is
    None only when resolving the built-in defaults (known-good)."""
    fb: dict[float, str] = dict(fallback) if fallback else {}
    out: list[tuple[float, str]] = []
    for thr, spec in (cast(list[Any], pairs) if pairs else []):
        try:
            ceil = util_parse_threshold(thr)
        except ValueError:
            print(f"{_DIM}status-line: bad ramp [{band}] threshold {thr!r} — "
                  f"keeping default{RESET}", file=sys.stderr)
            return list(fallback) if fallback else out
        esc = util_parse_color(spec, palette)
        if esc is None:
            esc = fb.get(ceil, "")
            print(f"{_DIM}status-line: bad ramp [{band}] color {spec!r} — using "
                  f"default band{RESET}", file=sys.stderr)
        out.append((ceil, esc))
    out.sort(key=lambda ce: ce[0])
    return out


def core_build_effort(palette: dict[str, str]) -> dict[str, tuple[str, str]]:
    """level -> (color escape, bar string). Filled glyphs in the level's color,
    the rest in grey (the effort-ladder layout)."""
    grey = util_parse_color("GREY", palette) or ""
    out: dict[str, tuple[str, str]] = {}
    for level, (name, n) in _EFFORT_DEFAULTS.items():
        color = util_parse_color(name, palette) or ""
        rest = _EFFORT_GLYPHS[n:]
        bar = f"{color}{_EFFORT_GLYPHS[:n]}" + (f"{grey}{rest}" if rest else "")
        out[level] = (color, bar)
    return out


def core_build_theme(cfg: "Config") -> "Theme":
    """Resolve a Config's palette + ramps + effort into a Theme."""
    palette = core_resolve_palette(cfg.palette)
    ramps: dict[str, list[tuple[float, str]]] = {}
    for band, default_pairs in _RAMP_DEFAULTS.items():
        default_ramp = core_resolve_ramp(default_pairs, palette, band, None)
        override = (cfg.ramps or {}).get(band)
        ramps[band] = (default_ramp if override is None
                       else core_resolve_ramp(override.items(), palette, band, default_ramp))
    return Theme(palette, ramps, core_build_effort(palette))


def core_default_theme() -> "Theme":
    """Theme from cfg_default_config() (no overrides)."""
    return core_build_theme(cfg_default_config())


# Editable surface (SEGMENTS + LAYOUT) is at the top of the file; the registry
# is DERIVED by convention from the seg_* functions above — no hand-maintained
# key->fn list to drift (FR-A.3, D7).
def core_discover_builders() -> dict[str, "Builder"]:
    """The built-in builder map, derived by convention from this module's
    `seg_<key>` functions (the homologous suffix is the segment key). Replaces the
    hand-maintained BUILDERS literal (FR-A.3, D7): adding a `seg_x` auto-registers
    it. SEGMENTS/LAYOUT stay explicit defaults tables — discovery removes only the
    redundant name->fn list, never the tables that encode intent."""
    # cast: globals() returns dict[str, Any]; the comprehension filters to seg_*
    # callables matching the Builder protocol — types are erased at this stdlib boundary.
    return cast(dict[str, "Builder"], {name[len("seg_"):]: fn
                                       for name, fn in globals().items()
                                       if name.startswith("seg_") and callable(fn)})


_SEG_HEADER_RE = re.compile(r"^#\s*ai-kit-segment:\s*(.*?)\s*$")


def core_parse_segment_header(lines: list[str]) -> dict[str, Any] | None:
    """Parse the `# ai-kit-segment:` header from a file's first lines.

    Returns a dict of the raw string fields present (`line`/`id`/`timeout`/`ttl`
    as strings, `position` as a (kind, ref) tuple) — possibly empty if the header
    line exists but lists nothing. Returns None when no header line is present."""
    for ln in lines:
        m = _SEG_HEADER_RE.match(ln)
        if m is None:
            continue
        fields: dict[str, Any] = {}
        for tok in m.group(1).split():
            if tok in ("start", "end"):
                fields["position"] = (tok, "")
            elif "=" in tok:
                k, v = tok.split("=", 1)
                if k in ("after", "before"):
                    fields["position"] = (k, v)
                elif k in ("line", "id", "timeout", "ttl"):
                    fields[k] = v
        return fields
    return None


def core_discover_external(directory: str, default_ttl: int, cache_dir: str) -> list["ExtSpec"]:
    """Scan `directory` for executable providers and return a list of ExtSpec,
    sorted by (filename, id). Non-executable files are skipped with a dim warning.
    A file with no header still loads with all defaults (line=0 => last row at
    placement, position=end, id=stem, timeout=2s, ttl=default_ttl).
    `cache_dir` is the per-provider output cache directory (…/ai-kit/segments)."""
    if not directory or not os.path.isdir(directory):
        return []
    specs: list[ExtSpec] = []
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        if not os.access(path, os.X_OK):
            print(f"{_DIM}status-line: segment '{name}' not executable — skipped{RESET}",
                  file=sys.stderr)
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                head = [f.readline() for _ in range(10)]
        except OSError:
            continue
        fields = core_parse_segment_header(head) or {}
        sid = fields.get("id") or os.path.splitext(name)[0]
        try:
            timeout = float(fields.get("timeout", 2))
        except (TypeError, ValueError):
            timeout = 2.0
        try:
            ttl = int(fields.get("ttl", default_ttl))
        except (TypeError, ValueError):
            ttl = default_ttl
        try:
            line = int(fields["line"]) if "line" in fields else 0
        except (TypeError, ValueError):
            line = 0
        specs.append(ExtSpec(
            id=sid, path=path, line=line,
            position=fields.get("position", ("end", "")),
            timeout=timeout, ttl=ttl,
            cache_path=os.path.join(cache_dir, sid)))
    specs.sort(key=lambda s: (os.path.basename(s.path), s.id))
    return specs


def core_cache_read(spec: "ExtSpec") -> str | None:
    """Cached raw output line if present and younger than ttl, else None.
    ttl <= 0 always misses (forces a re-run every render)."""
    if spec.ttl <= 0:
        return None
    try:
        age = time.time() - os.stat(spec.cache_path).st_mtime
    except OSError:
        return None
    if age >= spec.ttl:
        return None
    try:
        with open(spec.cache_path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def core_cache_write(spec: "ExtSpec", text: str) -> None:
    """Best-effort: persist raw output. Unwritable cache dir -> silently skip."""
    try:
        os.makedirs(os.path.dirname(spec.cache_path), exist_ok=True)
        with open(spec.cache_path, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass


def core_run_provider(spec: "ExtSpec", ctx: "Context", avail: int) -> str | None:
    """Spawn the provider with the status JSON + segment block on stdin, the
    AI_KIT_SEGMENT_* env mirror, and cwd = workspace dir. Returns the raw first
    non-empty stdout line, or None on timeout / non-zero exit / no output."""
    pos = util_position_str(spec.position)
    payload = json.dumps({**(ctx.raw or {}),
                          "segment": {"id": spec.id, "avail_cols": avail,
                                      "line": spec.line, "position": pos}})
    env = dict(os.environ)
    env.update({"AI_KIT_SEGMENT_COLS": str(avail), "AI_KIT_SEGMENT_ID": spec.id,
                "AI_KIT_SEGMENT_LINE": str(spec.line), "AI_KIT_SEGMENT_POSITION": pos})
    try:
        proc = subprocess.run(
            [spec.path], input=payload, capture_output=True, text=True,
            timeout=spec.timeout, cwd=ctx.work_dir or ".", env=env, check=False)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        if line.strip():
            return line
    return None


def core_run_external(spec: "ExtSpec", ctx: "Context", avail: int) -> str | None:
    """TTL-cached, timeout-bounded provider invocation. Returns the sanitized,
    width-fitted segment string, or None to omit the segment."""
    raw_line = core_cache_read(spec)
    if raw_line is None:
        raw_line = core_run_provider(spec, ctx, avail)
        if raw_line is None:
            return None
        core_cache_write(spec, raw_line)
    return util_sanitize_external(raw_line, avail)


def core_make_external_builder(spec: "ExtSpec") -> "Builder":
    """Wrap an ExtSpec as a seg_x(ctx, avail, theme)-shaped builder so the packer
    treats it exactly like a built-in. theme is unused (the provider colors itself)."""
    def _builder(ctx: "Context", avail: int, theme: "Theme") -> str | None:
        return core_run_external(spec, ctx, avail)
    return _builder


def core_builders_for(cfg: "Config") -> dict[str, "Builder"]:
    """The built-in BUILDERS merged with one synthetic builder per external
    provider (keyed by id). External ids never collide with built-ins by design;
    if a user names one after a built-in, the external wins for that render."""
    builders = dict(BUILDERS)
    for spec in (cfg.external.providers if cfg.external else []):
        builders[spec.id] = core_make_external_builder(spec)
    return builders


# RENDER CONTRACT (how a line becomes text):
#   * One registry, one gate. Built-in and external segments share a single
#     name->builder map (`core_builders_for`) and a single on/off gate
#     (`cfg.segments.get(name, False)`). Every builder is `seg_x(ctx, avail,
#     theme) -> str | None` and is interchangeable to the packer.
#   * One guarded entry. `core_safe_build` is the only place a builder is called; on
#     any exception it records the key in `failed` and returns a width-bounded
#     ⚠ marker, so one bad segment can never blank the bar (never-blank).
#   * Three phases. `core_render` orchestrates Phase A (`core_measure_all` —
#     build + time EVERY non-meta segment across ALL gated-in lines, with
#     `core_crown_slowest` tracking the single GLOBAL running max into
#     `ctx.slowest`), Phase B (`core_build_meta`), and Phase C
#     (`core_assemble_line`, per line). The Phase-A timing bracket captures each
#     segment's first-read probe cost (FR-R.2), so the crowned time is the
#     segment's REAL cost.
#   * Two meta segments. `render_time` and `slowest` (`_SLOWEST_META`) report the
#     whole render, not one builder, so they are built ONCE in Phase B (after
#     every non-meta build is timed, GLOBALLY — so the readout is the same on any
#     line) and placed at their LAYOUT position in assembly — never forced last,
#     never crowned as the culprit.
def core_safe_build(
    key: str, ctx: "Context", avail: int, theme: "Theme",
    builders: dict[str, "Builder"] | None = None,
) -> str | None:
    """Invoke one segment builder in isolation. On ANY exception, record `key`
    in `ctx.failed` and return a width-bounded warning marker instead of
    propagating — so a single bad segment can never blank the whole bar. The
    marker shows the segment name when it fits `avail`, else just the icon.
    `builders` defaults to the built-in BUILDERS registry."""
    builders = builders if builders is not None else BUILDERS
    try:
        return builders[key](ctx, avail, theme)
    except Exception:  # pylint: disable=broad-exception-caught  # never-blank isolation
        ctx.failed.add(key)
        named = f"{_WARN}⚠{key}{RESET}"
        if util_visible_width(named) <= avail:
            return named
        return f"{_WARN}⚠{RESET}"


def core_crown_slowest(ctx: "Context", key: str, ns: int) -> None:
    """Record the slowest non-meta, non-crashed segment build this render — the
    single place the running max is tracked (FR-R.1). The meta segments report
    the whole render, not one builder, so they are never the culprit; a crashed
    segment (in `ctx.failed`) reports its warning marker's time, not real work."""
    if key in _SLOWEST_META or key in ctx.failed:
        return
    cur = ctx.slowest
    if cur is None or ns > cur[1]:
        ctx.slowest = (key, ns)


def core_gated_lines(ctx: "Context", cfg: "Config") -> Iterator[tuple[int, list[str]]]:
    """Yield `(line_index, enabled_keys)` for each layout line that clears the
    terminal-height gate (`ctx.lines >= min_rows`). The single place the per-line
    height gate AND the enabled-segment filter are computed — all three render
    phases (measure / meta / assemble) consume it, so a future gate-rule change
    lives in exactly one spot."""
    for line_index, ln in enumerate(cfg.layout):
        if ctx.lines < ln.min_rows:
            continue
        yield line_index, [k for k in ln.segments if cfg.segments.get(k, False)]


def core_measure_all(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    ctx: "Context", cfg: "Config", budget: int, sep_w: int,
    theme: "Theme", builders: dict[str, "Builder"],
) -> dict[tuple[int, str], str]:
    """Phase A: build + time every active non-meta segment across ALL rendered
    layout lines, crowning the single GLOBAL slowest (FR-4). Each line is walked
    left->right with its own shrinking `used_est` so `avail` (hence variant
    selection inside builders) matches the per-line fit exactly. Lines gated out
    by terminal height are skipped (via core_gated_lines), so their segments are
    never built/timed/crowned. Returns built strings keyed by `(line_index, key)`."""
    built: dict[tuple[int, str], str] = {}
    for line_index, enabled in core_gated_lines(ctx, cfg):
        used_est = 0
        for key in enabled:
            if key in _SLOWEST_META:
                continue
            sep = sep_w if used_est else 0
            avail = max(budget - used_est - sep, 0)
            t0 = time.perf_counter_ns()
            s = core_safe_build(key, ctx, avail, theme, builders)
            ns = time.perf_counter_ns() - t0
            if not s:
                continue
            if key in PINNED or util_visible_width(s) <= avail:
                built[(line_index, key)] = s
                used_est += util_visible_width(s) + sep
                core_crown_slowest(ctx, key, ns)
    return built


def core_build_meta(
    ctx: "Context", cfg: "Config", budget: int,
    theme: "Theme", builders: dict[str, "Builder"],
) -> dict[str, str]:
    """Phase B: build the meta segments (`render_time`, `slowest`) ONCE, now that
    every non-meta build is timed and `ctx.slowest`/`t_start` are settled (FR-4).
    A meta key is built when it is enabled on any height-gated-in line; the dict
    keying dedupes. Each is offered the full `budget` (it is placed per line in
    Phase C). Returns the shared meta strings reused across all lines."""
    meta_built: dict[str, str] = {}
    for _, enabled in core_gated_lines(ctx, cfg):
        for key in enabled:
            if key not in _SLOWEST_META or key in meta_built:
                continue
            s = core_safe_build(key, ctx, budget, theme, builders)
            if s:
                meta_built[key] = s
    return meta_built


def core_assemble_line(
    enabled: list[str], built: dict[str, str], budget: int, sep_w: int,
) -> str:
    """Assemble in layout order, fitting left->right with every width known."""
    kept: list[str] = []
    used = 0
    for key in enabled:
        s = built.get(key)
        if not s:
            continue
        sep = sep_w if kept else 0
        if key in PINNED or used + sep + util_visible_width(s) <= budget:
            kept.append(s)
            used += util_visible_width(s) + sep
    return SEP.join(kept)


def core_diagnostic_line(failed: set[str]) -> str | None:
    """One line naming the segments that crashed this render, pointing at the
    doctor. Returns None when nothing failed (no cost on the happy path)."""
    if not failed:
        return None
    names = ", ".join(sorted(failed))
    n = len(failed)
    noun = "segment" if n == 1 else "segments"
    return (f"{_WARN}⚠ {n} {noun} failed: {names} — "
            f"run the doctor: {core_doctor_cmd()}{RESET}")


def core_render(
    ctx: "Context", cfg: Optional["Config"] = None, theme: Optional["Theme"] = None
) -> list[str]:
    """Render up to len(cfg.layout) lines, gated by terminal height and width,
    in three phases (FR-4): Phase A measures + times every active non-meta segment
    across ALL gated-in lines and crowns the single GLOBAL slowest; Phase B builds
    the meta segments (`render_time`, `slowest`) ONCE off that settled state; Phase
    C assembles each gated-in line from its slice of Phase-A strings plus the shared
    meta. A trailing diagnostic line is appended only when a builder crashed. Reads
    geometry (cols/lines) and the shared `failed` set off `ctx`."""
    cfg = cfg or ctx.line_conf
    theme = theme or ctx.theme
    builders = core_builders_for(cfg)
    budget = ctx.cols - RIGHT_MARGIN
    sep_w = util_visible_width(SEP)
    built = core_measure_all(ctx, cfg, budget, sep_w, theme, builders)   # Phase A
    meta_built = core_build_meta(ctx, cfg, budget, theme, builders)      # Phase B
    out: list[str] = []
    for line_index, enabled in core_gated_lines(ctx, cfg):               # Phase C
        line_built = {k: v for (i, k), v in built.items() if i == line_index}
        line_built.update(meta_built)
        packed = core_assemble_line(enabled, line_built, budget, sep_w)
        if packed:
            out.append(packed)
    diag = core_diagnostic_line(ctx.failed)
    if diag:
        out.append(diag)
    return out


# ═══ 7. seg_ — segment builders seg_x(ctx, avail, theme); auto-discovered registry


# ── identity line ────────────────────────────────────────────────────────────
def seg_path(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    return f"{theme.c('BLUE')}{util_display_dir(ctx.work_dir, ctx.home)}{RESET}"  # floor


def seg_git_branch(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    branch = probe_git_for(ctx).branch
    if not branch:
        return None
    # git_branch carries its own STATIC 🌿 icon. It does NOT encode worktree state
    # (no 🌳) — that moved to the dedicated `alt_git_worktree` ⎇ segment (FR-7.2);
    # the leaf glyph here is purely "this is the branch". Falls back to the bare
    # name when too narrow for the icon, so the branch never drops just for it.
    return util_first_fitting([f"{theme.c('GREY')}[{util_icon('🌿', branch)}]{RESET}",
                           f"{theme.c('GREY')}[{branch}]{RESET}"], avail)


def seg_git_dirty(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    mark = util_dirty_mark(probe_git_for(ctx).dirty, theme)
    return util_first_fitting([mark], avail) if mark else None


def seg_alt_git_worktree(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    # alt_git_worktree names the ACTIVE linked worktree the session sits in —
    # never a list. Mirrors git_dirty's "absence is the neutral state": hidden
    # outside a repo. On the main checkout it shows a dimmed, struck `⎇ wt`
    # placeholder — GREY (not just strikethrough) so it stays distinct from the
    # cyan active form even on terminals that don't render SGR-9.
    snap = probe_git_for(ctx)
    if not snap.in_repo:
        return None
    if not snap.is_worktree:
        return util_first_fitting([f"{theme.c('GREY')}\033[9m⎇ wt{RESET}"], avail)
    name = util_trunc_cols(snap.wt_name or "", 20)
    return util_first_fitting([f"{theme.c('CYAN')}⎇ {name}{RESET}"], avail)


def seg_todo(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    state, text = probe_todo(ctx)
    if not text:
        return None
    limit = avail - 4                      # room for icon + space + ellipsis
    if limit < 6:                          # too cramped to be useful -> hide
        return None
    if len(text) > limit:
        text = text[:limit - 1] + "…"
    if state == "in_progress":
        return util_icon("📝", f"{theme.c('YELLOW')}{text}{RESET}")
    if state == "pending":
        return util_icon("⏸", f"{theme.c('GREY')}{text}{RESET}")
    return None


# ── model row ────────────────────────────────────────────────────────────────
def seg_model(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    name = ctx.model_name or ctx.model_id
    if not name:
        return None
    return util_first_fitting([f"{theme.c('CYAN')}{name}{RESET}"], avail)


def seg_alt_time_ago(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    ago = probe_ago(ctx)
    if not ago:
        return None
    return util_first_fitting([f"{theme.c('WHITE')}{ago}{RESET}"], avail)


def seg_alt_time_clock(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    return util_first_fitting([util_icon("⏰", ctx.clock)], avail)


def seg_effort(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    level = ctx.effort
    if not level:
        return None
    # Unknown level (stale/future): no color on the word, all-grey ladder — a safe
    # degraded display. cfg_resolve_effort already strips "auto", so it never lands here.
    color, bar = theme.effort.get(level.lower(), ("", f"{theme.c('GREY')}▁▃▄▆█"))
    word = f"{color}{level}{RESET}"
    bars = util_icon("🧠", f"{bar}{RESET}")
    if probe_effort_auto(ctx):
        # effortLevel is unset/auto in settings: flag the resolved level as
        # auto-chosen. The flag degrades [auto] -> * -> dropped as space tightens.
        variants = [f"{bars} {word} {theme.c('GREY')}[auto]{RESET}",
                    f"{bars} {color}{level}*{RESET}",
                    f"{bars} {word}",
                    bars]
    else:
        variants = [f"{bars} {word}", bars]
    return util_first_fitting(variants, avail)


def seg_lines(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    body = (f"{BG_LIGHTGRAY}{theme.c('GREEN')}+{fmt_number(ctx.added)}{RESET}"
            f"/{BG_LIGHTGRAY}{theme.c('RED')}-{fmt_number(ctx.removed)}{RESET}")
    return util_first_fitting([util_icon("📃", body)], avail)


def seg_alt_cost(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    return util_first_fitting([util_icon("🪙", f"${float(ctx.cost):.3f}")], avail)


def seg_alt_time_session(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    return util_first_fitting([util_icon("💬", fmt_time_ms(ctx.total_ms))], avail)


def seg_alt_time_api(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    return util_first_fitting([util_icon("📡", fmt_time_ms(ctx.api_ms))], avail)


# ── diagnostics row ──────────────────────────────────────────────────────────
# status-line's own run time, SLO/SLA-colored
def seg_render_time(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    t0 = ctx.t_start
    if t0 is None:                      # not timed (e.g. direct builder calls) -> omit
        return None
    elapsed = time.perf_counter_ns() - t0
    color = util_pick_color(elapsed, theme.ramps["render_time"])
    return util_first_fitting([util_icon("⏱", f"{color}{fmt_duration(elapsed)}{RESET}")], avail)


# slowest single segment this render, SLO/SLA-colored
def seg_slowest(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    slow = ctx.slowest
    if not slow:                            # timing off (segment disabled) -> omit
        return None
    name, ns = slow
    color = util_pick_color(ns, theme.ramps["slowest"])
    dur = f"{color}{fmt_duration(ns)}{RESET}"
    # drop name when tight
    return util_first_fitting([util_icon("🐌", f"{name} {dur}"), util_icon("🐌", dur)], avail)


def seg_alt_term_dimensions(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    mark = "?" if ctx.dim_assumed else ""
    return util_first_fitting([f"{ctx.cols}×{ctx.lines}{mark}"], avail)


def seg_context(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    pct = int(ctx.context_pct)
    color = util_pick_color(pct, theme.ramps["context"])
    pct_only = util_icon("📊", f"{color}{pct}%{RESET}")
    # Measure in half-cells (5% each) and round up, so any pct > 0 shows >= ▌.
    halves = 0 if pct <= 0 else min(2 * CONTEXT_BAR_CELLS, math.ceil(pct / 5))
    full_n, half = divmod(halves, 2)
    bar_f = "█" * full_n + ("▌" if half else "")
    bar_e = "░" * (CONTEXT_BAR_CELLS - full_n - half)
    bar = f"{color}{bar_f}{theme.c('GREY')}{bar_e}{RESET}"
    mid = util_icon("📊", f"{bar} {color}{pct}%{RESET}")
    full = util_icon("📊", f"{bar} {color}{pct}% of {fmt_tokens(ctx.context_max)}{RESET}")
    return util_first_fitting([full, mid, pct_only], avail) or pct_only  # floor


def seg_chat_size(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    n = probe_chat_size(ctx)
    if n is None:
        return None
    color = util_pick_color(n, theme.ramps["chat_size"])
    return util_first_fitting([util_icon("💾", f"{color}{fmt_bytes(n)}{RESET}")], avail)


def seg_alt_process_memory(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    n = probe_rss(ctx)
    if n is None:
        return None
    return util_first_fitting([util_icon("🧮", fmt_bytes(n))], avail)


def seg_alt_rate_limits(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    rate_limits = ctx.rate_limits
    if not rate_limits:
        return None
    return util_first_fitting([util_rate_str(rate_limits, "long", theme),
                           util_rate_str(rate_limits, "short", theme),
                           util_rate_str(rate_limits, "none", theme)], avail)


BUILDERS = core_discover_builders()   # module-level snapshot; same shape as the old literal


# Contract: every builder is seg_x(ctx, avail, theme) -> str | None.
#   avail = display cells available to this segment at its position.
#   Return None when there is no data, OR when even the smallest variant does
#   not fit avail (the builder self-deprioritizes). Otherwise return the richest
#   variant that fits, via util_first_fitting([rich, ..., minimal], avail).
# The packer (Phase A, core_measure_all) supplies avail and owns the final keep/skip decision.
# To add a segment: write seg_x(ctx, avail, theme), list its key in a LAYOUT line,
# add a SEGMENTS flag. The registry auto-discovers seg_* (no BUILDERS edit). See
# the HOW TO CUSTOMIZE block below.

# NOTE: the effort bars live on the Theme (theme.effort), resolved by
# core_build_effort from the palette so a [palette] override re-colors them too.
# `ultracode` is NOT a level (it reports as xhigh + standing multi-agent
# permission), and `auto` is a *setting*, not a resolved level — neither belongs
# in the table. The auto setting is surfaced as a "[auto]" suffix in seg_effort.


# ═══ 8. SHELL — side effects only: env capture, stdin, print, render entrypoint ═


def safe_render(raw: dict[str, Any], env: Env, cfg: "Config", theme: "Theme",
                t_start: int) -> list[str]:
    """Build context and render; on ANY unexpected failure return a single
    diagnostic line instead of a blank bar. Never raises. This is the backstop
    above core_safe_build's per-segment isolation (covers core_build_context itself)."""
    try:
        cols, lines, assumed = probe_terminal_size(env)
        home = env.get("HOME", "")
        claude_dir = env.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
        ctx = core_build_context(raw, cfg, theme, cols, lines, assumed, t_start,
                            effort=cfg_resolve_effort(raw),
                            home=home, claude_dir=claude_dir)
        return core_render(ctx)
    except Exception:  # pylint: disable=broad-exception-caught  # never-blank isolation
        return [f"{_WARN}⚠ status-line error — "
                f"run the doctor: {core_doctor_cmd()}{RESET}"]


def main() -> None:
    """CLI entrypoint: render the status line from stdin. Renders only — config
    introspection (--doctor / --check / --print-config) lives in the sibling
    statusline-doctor.py, which imports this module one-way."""
    t0 = time.perf_counter_ns()        # for the optional `render_time` self-timing segment
    env = os.environ                   # single SHELL-boundary read (FR-A.1)
    cfg = cfg_load_config(env)
    theme = core_build_theme(cfg)
    try:
        raw: dict[str, Any] = json.load(sys.stdin)
    except (ValueError, OSError):
        raw = {}
    print("\n".join(safe_render(raw, env, cfg, theme, t0)))


# ═══ 9. HOW TO CUSTOMIZE — this module renders only. Config introspection
# (--doctor / --check / --print-config) lives in the sibling statusline-doctor.py,
# which imports this render core one-way. See that script to validate config and
# dry-render every builder.


# Three knobs at the top of the file drive everything:
#
#   SEGMENTS  — on/off flag per segment. False hides it everywhere and its
#               builder is never called (saves compute). Keep "path" True.
#   LAYOUT    — the template: a list of Line(min_rows, [segment keys]). Key order
#               in each list is LEFT->RIGHT priority; leftmost survive when the
#               terminal is narrow. min_rows gates the whole row by terminal rows.
#   BUILDERS  — auto-discovered from the seg_* functions (key = the suffix after
#               "seg_"). Not hand-maintained: write a seg_x and it registers.
#
# How show/hide is decided: the packer (Phase A, core_measure_all) is the authority. It offers
# each builder the space available at its spot (avail) and keeps the result only
# if it is non-empty and fits; otherwise it skips it and tries the next. A
# builder cooperates by auto-deprioritizing itself — returning a compact variant
# for a small avail, or None when even its smallest variant will not fit.
# PINNED segments ("path", "context") are kept even if they overflow.
#
# Available segments (key -> what it shows):
#   path                 working dir (~-collapsed; basename if long)   [pinned]
#   git_branch           git branch name
#   alt_git_worktree     ⎇ active linked-worktree name (struck ⎇ wt on the main checkout)
#   git_dirty            ✗ untracked / ~ modified marker
#   todo                 active TODO / task (truncated to fit)
#   model                model display name
#   alt_time_ago         time since last transcript activity
#   alt_time_clock       ⏰ wall clock HH:MM
#   effort               🧠 effort ramp bar (+ level word when room)
#   lines                📃 +added/-removed line counts
#   alt_cost             🪙 session cost in USD (off by default)
#   alt_time_session     💬 total session duration
#   alt_time_api         📡 total API duration
#   render_time          ⏱ status-line.py's own run time, SLO/SLA-colored via the
#                        render_time ramp
#   slowest              🐌 the slowest single segment this render (name + duration),
#                        SLO/SLA-colored via the shared slowest ramp
#   alt_term_dimensions  terminal COLS×ROWS (off by default; debug)
#   context              📊 context-window usage bar + percent         [pinned]
#   chat_size            💾 transcript file size
#   alt_process_memory   🧮 agent process memory (RSS)
#   alt_rate_limits      ⚡ rate-limit buckets (+ reset times when room)
#
# Common edits:
#   * Toggle a segment:       flip its SEGMENTS[...] value.
#   * Reorder within a line:  move its key within that Line's list.
#   * Move to another line:   cut its key from one Line list, paste into another.
#   * Re-enable a removed one: ensure (a) SEGMENTS[key] is True and (b) the key is
#                             in some LAYOUT line. (The seg_* builder is discovered
#                             automatically.) Both are required for it to show.
#   * Add a NEW segment:
#       1. Write a builder:  def seg_foo(ctx, avail, theme):
#              if no_data: return None
#              return util_first_fitting([rich_form, compact_form], avail)
#          (return None to hide; read what you need from `ctx`; let the builder
#          auto-deprioritize via util_first_fitting on the avail it is offered). The
#          registry discovers seg_foo by name — no BUILDERS edit needed.
#       2. Place it:         add  "foo"  to a LAYOUT line where you want it.
#       3. Flag it:          add  "foo": True  to SEGMENTS.
#       4. Test it:          add a case in tests/test_status_line.py.

if __name__ == "__main__":
    main()
