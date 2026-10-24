"""Config resolution and external discovery for the Phase 23 D-02 status-line split."""
# pyright: strict

import os
import re
import sys

try:
    import tomllib as _tomllib_impl

    tomllib = _tomllib_impl
except ModuleNotFoundError:  # Python < 3.11 — degrade to env-only config.
    tomllib = None  # type: ignore[assignment]  # stdlib boundary: optional module absent on <3.11
from typing import Any, cast

from common_fmt import cfg_coerce_env_bool, cfg_env_label, cfg_env_segment_keys
from common_types import (
    DIM,
    EXTERNAL_CACHE_TTL,
    GIT_DEFAULTS,
    PALETTE_DEFAULTS,
    RESET,
    Config,
    ConfigSpec,
    Env,
    ExternalConf,
    ExtSpec,
    Line,
)

# ═══ 2. cfg_ — config loading & resolution (the only block that reads config env)


def cfg_git_key_problem(k: str, v: Any) -> str | None:
    """Classify one `[git]` key/value so cfg_load_config and the doctor's
    validate_config_file share a single validation rule (each formats its own
    message). Returns:
      'unknown' — not a recognized `[git]` key,
      'bad_ttl' — cache_ttl is not an int (bools excluded),
      None      — acceptable."""
    if k not in GIT_DEFAULTS:
        return "unknown"
    if k == "cache_ttl" and (not isinstance(v, int) or isinstance(v, bool)):
        return "bad_ttl"
    return None


def cfg_warn(msg: str) -> None:
    """The single render-format config-warning emitter: dim grey, 'status-line:'
    prefix, stderr. Phase-3 the doctor prints bind problems through this same
    wrapper, so relocated warning text is byte-identical to what render emitted."""
    print(f"{DIM}status-line: {msg}{RESET}", file=sys.stderr)


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
            value, recognized = cfg_coerce_env_bool(cast(str, raw))
            return (value, None) if recognized else (None, None)  # unrecognized = silent skip
        try:
            return int(cast(str, raw)), None
        except (TypeError, ValueError):
            return None, bad
    # source == "toml": strict, already-typed
    if kind == "bool":
        return (raw, None) if isinstance(raw, bool) else (None, bad)
    return (raw, None) if isinstance(raw, int) and not isinstance(raw, bool) else (None, bad)


def cfg_source_get(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    source: str, raw_toml: dict[str, Any], env: Env, path: tuple[str, ...], prefix: str
) -> Any | None:
    """Get a raw source value using the supplied host prefix and path."""
    if source == "env":
        head = "SEGMENT" if path[0] == "segments" else path[0].upper()
        name = prefix + "_".join([head, *(p.upper() for p in path[1:])])
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


def cfg_bind_scalars(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    raw_toml: dict[str, Any],
    env: Env,
    git: dict[str, Any],
    ext_dir: str,
    ext_ttl: int,
    prefix: str,
) -> tuple[dict[str, Any], str, int, list[str]]:
    """Bind the scalar line_conf groups (git, external) from env on top of the
    already-resolved default<TOML values. Runs BEFORE external-provider discovery
    because the host's external directory override changes which directory is scanned. Phase 2
    binds ENV only (TOML stays in the git loop / cfg_resolve_external and folds
    into this walk in a later phase, when their warnings migrate to the problem
    channel). Collects problems instead of printing; the caller decides. Returns
    (git, ext_dir, ext_ttl, problems)."""
    g, d, t = dict(git), ext_dir, ext_ttl
    problems: list[str] = []

    def bind_int(path: tuple[str, ...], cur: int) -> int:
        raw = cfg_source_get("env", raw_toml, env, path, prefix)
        if raw is None:
            return cur
        value, prob = cfg_coerce(raw, "int", "env", cfg_env_label(path, prefix))
        if prob:
            problems.append(prob)
            return cur
        return value if value is not None else cur

    g["cache_ttl"] = bind_int(("git", "cache_ttl"), g["cache_ttl"])
    t = bind_int(("external", "cache_ttl"), t)
    raw_dir = cfg_source_get("env", raw_toml, env, ("external", "dir"), prefix)
    if raw_dir:
        d = os.path.expanduser(cast(str, raw_dir))
    return g, d, t, problems


def cfg_bind_segments(
    raw_toml: dict[str, Any],
    env: Env,
    segments: dict[str, bool],
    prefix: str,
) -> tuple[dict[str, bool], list[str]]:
    """Bind the segment toggle map from env on top of the already-resolved
    default<TOML map (cfg_resolve_segments). Runs AFTER external-provider
    discovery so provider ids are known segment keys. Canonical keys only — no
    legacy forwarding. env bad-bool stays silent (tri-state). Collects problems
    instead of printing. Returns (segments, problems)."""
    seg = dict(segments)
    problems: list[str] = []
    for key in cfg_env_segment_keys(env, prefix):
        if key not in seg:
            continue
        raw = cfg_source_get("env", raw_toml, env, ("segments", key), prefix)
        value, prob = cfg_coerce(raw, "bool", "env", cfg_env_label(("segments", key), prefix))
        if prob:
            problems.append(prob)
        elif value is not None:
            seg[key] = value
    return seg, problems


def cfg_default_config(spec: ConfigSpec) -> "Config":
    """A Config snapshotting the current module-global defaults (SEGMENTS/LAYOUT,
    no palette/ramp overrides). Copies are returned so callers cannot mutate
    globals."""
    return Config(
        segments=dict(spec.default_segments),
        layout=list(spec.default_layout),
        palette={},
        ramps={},
        git=dict(GIT_DEFAULTS),
    )


def cfg_config_path(env: Env, spec: ConfigSpec) -> str:
    """Resolved TOML path: the host's CONFIG_FILE override, else
    ${XDG_CONFIG_HOME:-$HOME/.config}/ai-kit/<host's TOML>.

    FR-1.7: this is the bootstrap exception — it reads env directly before any
    TOML is loaded (chicken-and-egg), so it is the one explicit hardcoded env read
    outside the cfg_bind_scalars/cfg_bind_segments layer."""
    explicit = env.get(spec.env_prefix + "CONFIG_FILE")
    if explicit:
        return os.path.expanduser(explicit)
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
    return os.path.join(base, "ai-kit", spec.config_filename)


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
            problems.append(f"segment '{k}' must be true/false, got {v!r} — ignored")
        else:
            seg[k] = v
    return seg, problems


def cfg_resolve_layout(default_layout: list[Line], raw_lines: Any) -> list[Line]:
    """If the file has ANY [[line]] block, it REPLACES the whole layout
    (all-or-nothing — a partial layout can't silently drop segments). Otherwise
    keep the default. Each block: min_rows (default 0) + segments list."""
    if not raw_lines:
        return list(default_layout)
    return [
        Line(int(item.get("min_rows", 0)), list(item.get("segments", []))) for item in raw_lines
    ]


def cfg_resolve_external(raw: dict[str, Any], env: Env, provider_dir: str) -> tuple[str, int]:
    """Resolve (dir, default_ttl) from defaults < [external] file.
    Env overrides are applied later by cfg_bind_scalars (FR-2)."""
    file_ext: dict[str, Any] = cast(dict[str, Any], raw.get("external") or {})
    ttl = EXTERNAL_CACHE_TTL
    fv: Any = file_ext.get("ttl")
    if isinstance(fv, int) and not isinstance(fv, bool):
        ttl = fv
    return cfg_segments_dir(file_ext, env, provider_dir), ttl


def cfg_place_external(
    layout: list[Line], specs: list["ExtSpec"]
) -> tuple[list[Line], list["ExtSpec"], list[str]]:
    """Insert each spec's id into the resolved layout at its row/position and
    return (new_layout, finalized_specs, problems). The header's `line=`/
    `after=`/`before=` is only a FALLBACK default: if the host's TOML
    already names this id in some row's `segments` list (an explicit `[[line]]`
    override), that placement wins and the header's preference is ignored —
    otherwise the spec would render twice. Resolves line=0 to the last row and
    clamps out-of-range rows. Specs are applied in their (filename, id) sort
    order so same-slot externals are deterministic.

    problems is a list of raw message strings (no ANSI); callers decide whether
    to print or discard them."""
    if not layout:
        return list(layout), [], []
    rows = [list(ln.segments) for ln in layout]
    nrows = len(rows)
    final: list[ExtSpec] = []
    problems: list[str] = []
    for spec in specs:
        placed_idx = next((i for i, segs in enumerate(rows) if spec.id in segs), None)
        if placed_idx is not None:
            final.append(spec._replace(line=placed_idx + 1))
            continue
        want = spec.line or nrows  # 0 => last row
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
        else:  # end, or after/before missing ref
            segs.append(spec.id)
        final.append(spec._replace(line=idx + 1))
    new_layout = [Line(layout[i].min_rows, rows[i]) for i in range(nrows)]
    return new_layout, final, problems


def cfg_load_config_verbose(  # pylint: disable=too-many-locals,too-many-branches
    env: Env,
    spec: ConfigSpec,
) -> "tuple[Config, list[str]]":
    """Resolve the full Config: internal defaults < TOML file < env.

    Resolves segments, layout, palette, ramps, and the [git] knobs. Also
    discovers external drop-in providers from the [external] `dir` (default
    ~/.config/ai-kit/segments) BEFORE resolving segments — so each provider id
    is a known segment key (enabled by default, disable via `[segments] <id> =
    false`) — and places them into the layout. The resolved providers land in
    Config.external (an ExternalConf whose `.providers` holds the finalized
    ExtSpec list, `.dir` the providers directory, `.cache_ttl` the default TTL).

    All host config env reads funnel through cfg_bind_scalars /
    cfg_bind_segments. The bootstrap CONFIG_FILE read is the sole exception.

    Returns (Config, problems) where problems is a list of raw message strings
    (no ANSI, no 'status-line: ' prefix) describing every skipped/clamped value.
    Emits NOTHING to stderr — callers decide what to do with problems."""
    base = cfg_default_config(spec)
    raw = cfg_load_toml(cfg_config_path(env, spec))
    problems: list[str] = []

    # External providers first: their ids must be known segment keys before
    # cfg_resolve_segments runs, so `[segments] <id> = false` is honored (not warned)
    # and they default to enabled. TOML-based dir/ttl resolved here; env overrides applied below.
    ext_dir, ext_ttl = cfg_resolve_external(raw, env, spec.provider_dir)
    cache_base = cfg_cache_base(env)

    # git: resolve from TOML first, then env overrides via single reader below.
    git: dict[str, Any] = dict(GIT_DEFAULTS)
    for k, v in cast(dict[str, Any], raw.get("git") or {}).items():
        problem = cfg_git_key_problem(k, v)
        if problem == "unknown":
            problems.append(f"unknown [git] key '{k}'")
        elif problem == "bad_ttl":
            problems.append(f"[git] cache_ttl must be an integer, got {v!r} — ignored")
        else:
            git[k] = v

    # FR-2/FR-3: env binds via the access/convert layer. Scalars bind BEFORE
    # discovery so the env-bound external dir is the one scanned; segments bind
    # AFTER discovery so provider ids are known segment keys.
    git, ext_dir, ext_ttl, prob_scalars = cfg_bind_scalars(
        raw, env, git, ext_dir, ext_ttl, spec.env_prefix
    )
    problems.extend(prob_scalars)

    # Discover external providers using the final resolved dir/ttl (env wins over TOML).
    specs = core_discover_external(ext_dir, ext_ttl, os.path.join(cache_base, spec.provider_cache))

    # segments resolved exactly once: defaults + external ids < [segments] TOML < env.
    # External provider ids are known segment keys (default enabled, disable via
    # `[segments] <id> = false`).
    seg_defaults = dict(base.segments)
    for s in specs:
        seg_defaults.setdefault(s.id, True)
    segments, prob_seg_file = cfg_resolve_segments(seg_defaults, raw.get("segments"))
    problems.extend(prob_seg_file)
    segments, prob_segs = cfg_bind_segments(
        raw, env, segments, spec.env_prefix
    )  # env pass + problems
    problems.extend(prob_segs)

    layout = cfg_resolve_layout(base.layout, raw.get("line"))
    layout, external, prob_place = cfg_place_external(layout, specs)
    problems.extend(prob_place)
    palette: dict[str, str] = {}
    for k, v in cast(dict[str, Any], raw.get("palette") or {}).items():
        if k in PALETTE_DEFAULTS:
            palette[k] = str(v)
        else:
            problems.append(f"unknown palette key '{k}'")
    ramps: dict[str, dict[str, str]] = {}
    for band, table in cast(dict[str, Any], raw.get("ramp") or {}).items():
        if band not in spec.ramp_defaults:
            problems.append(f"unknown ramp '{band}'")
            continue
        if not isinstance(table, dict):
            problems.append(f"ramp '{band}' must be a table — ignored")
            continue
        ramps[band] = {str(k): str(v) for k, v in cast(dict[Any, Any], table).items()}
    cfg = Config(
        segments=segments,
        layout=layout,
        palette=palette,
        ramps=ramps,
        git=git,
        external=ExternalConf(
            dir=ext_dir, cache_ttl=ext_ttl, providers=external, env_prefix=spec.provider_env
        ),
        cache_base=cache_base,
    )
    return cfg, problems


def cfg_load_config(env: Env, spec: ConfigSpec) -> "Config":
    """Silent wrapper around cfg_load_config_verbose — discards all problems.

    The render path calls this so it emits nothing to stderr. Use
    cfg_load_config_verbose when you need the problem list (e.g. the doctor)."""
    cfg, _ = cfg_load_config_verbose(env, spec)
    return cfg


def cfg_cache_base(env: Env) -> str:
    """${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit — root of every ai-kit on-disk cache."""
    base = env.get("XDG_CACHE_HOME") or os.path.join(env.get("HOME", ""), ".cache")
    return os.path.join(base, "ai-kit")


def cfg_segments_dir(file_external: Any, env: Env, provider_dir: str) -> str:
    """Resolve the providers directory from [external].dir (TOML) or the XDG default.
    Env override is applied later by cfg_bind_scalars
    (FR-2); this function is TOML + XDG only."""
    ext_block: dict[str, Any] = cast(dict[str, Any], file_external or {})
    d: str | None = ext_block.get("dir")
    if d:
        return os.path.expanduser(d)
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")
    return os.path.join(base, "ai-kit", provider_dir)


# ═══ 6. core_ — render machinery: Context, Theme, registry, packer, render ════


SEG_HEADER_RE = re.compile(r"^#\s*ai-kit-segment:\s*(.*?)\s*$")


def core_parse_segment_header(lines: list[str]) -> dict[str, Any] | None:
    """Parse the `# ai-kit-segment:` header from a file's first lines.

    Returns a dict of the raw string fields present (`line`/`id`/`timeout`/`ttl`
    as strings, `position` as a (kind, ref) tuple) — possibly empty if the header
    line exists but lists nothing. Returns None when no header line is present."""
    for ln in lines:
        m = SEG_HEADER_RE.match(ln)
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
            print(
                f"{DIM}status-line: segment '{name}' not executable — skipped{RESET}",
                file=sys.stderr,
            )
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
        specs.append(
            ExtSpec(
                id=sid,
                path=path,
                line=line,
                position=fields.get("position", ("end", "")),
                timeout=timeout,
                ttl=ttl,
                cache_path=os.path.join(cache_dir, sid),
            )
        )
    specs.sort(key=lambda s: (os.path.basename(s.path), s.id))
    return specs
