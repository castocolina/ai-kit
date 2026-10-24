#!/usr/bin/env python3
"""ai-kit status-line doctor — per-host config validation + dry-render introspection.

Renders nothing on the hot path. Imports the host assembly modules directly
and exercises every builder of the selected host (`--host claude|cursor`,
default claude, backward compatible) against a self-contained sample to
surface a builder that raises. CLI:
  --doctor         validate the resolved config AND dry-render every segment
  --check [FILE]   validate a config file (default: the resolved path)
  --print-config   print the resolved config as JSON

The render modules intentionally no longer accept these flags: they render
only. All introspection lives here. The Cursor doctor additionally reports
the quota fetch status; only this explicit manual `--doctor --host cursor`
invocation may run the (foreground) quota refresh — save validation, tests
and previews stay offline and never fetch or spawn a refresher.
"""
# pyright: strict
# pylint: disable=invalid-name  # sibling script name is hyphenated (statusline-doctor.py)

import argparse
import json
import os
import sys
import time
from collections.abc import Callable, Mapping
from typing import Any, cast

import claude_host
import common_config
import common_render
import common_types
import cursor_host
import cursor_quota

try:
    import tomllib as _tomllib_impl

    tomllib = _tomllib_impl
except ModuleNotFoundError:  # Python < 3.11 — config validation degrades.
    tomllib = None  # type: ignore[assignment]  # stdlib boundary: optional module absent on <3.11

# Environment dict: a snapshot of os.environ. Mapping[str, str] covers both a
# plain dict and os.environ (_Environ[str]).
Env = Mapping[str, str]

# Public default tables are read directly from common_types.
_EXTERNAL_CACHE_TTL = common_types.EXTERNAL_CACHE_TTL
_PALETTE_DEFAULTS = common_types.PALETTE_DEFAULTS

# The fetch seam injected by tests; the real default (cursor_quota.probe_fetch_quota)
# resolves at call time inside cursor_quota.probe_refresh, never here.
FetchQuota = Callable[[dict[str, str]], tuple[dict[str, object] | None, str | None, str]]

# The selectable hosts: every command takes the selected host's ConfigSpec (paths,
# env names, defaults, ramps), builders and build_context. Default is Claude, so
# pre-Phase-23 invocations behave byte-identically.
HOSTS: dict[str, common_render.Host] = {
    "claude": claude_host.HOST,
    "cursor": cursor_host.HOST,
}


_NO_CHECK = object()  # sentinel: --check flag absent (vs. present with no FILE)


_ENV_HELP = """\
Environment variables:
  CC_AI_KIT_CONFIG_FILE      path to the TOML config file
  CC_AI_KIT_SEGMENT_<KEY>    per-segment bool toggle; KEY is the upper-cased
                             segment name (PATH, MODEL, COST, CONTEXT, ...).
                             true:  1 true t y yes on    false: 0 false f n no off
  CC_AI_KIT_GIT_CACHE_TTL    int; seconds the git worktree probe is cached. Wins
                             over [git] cache_ttl (default 5).
  CC_AI_KIT_EXTERNAL_DIR     external drop-in segments directory (default
                             ${XDG_CONFIG_HOME:-~/.config}/ai-kit/segments)
  CC_AI_KIT_EXTERNAL_CACHE_TTL  default cache TTL (seconds) for external segments

Config precedence (low -> high): built-in defaults < TOML file < env."""


def env_help(spec: common_types.ConfigSpec) -> str:
    """Env-var help for one host's ConfigSpec (the --help epilog).

    Claude's text is the stable, hand-tuned _ENV_HELP verbatim; every other host
    gets the same layout generated from its spec (env prefix, providers dir,
    provider env prefix), per D-20."""
    if spec.env_prefix == claude_host.SPEC.env_prefix:
        return _ENV_HELP
    pre = spec.env_prefix
    return (
        "Environment variables:\n"
        f"  {pre}CONFIG_FILE      path to the TOML config file\n"
        f"  {pre}SEGMENT_<KEY>    per-segment bool toggle; KEY is the upper-cased\n"
        "                             segment name (PATH, MODEL, CONTEXT, ...).\n"
        "                             true:  1 true t y yes on    false: 0 false f n no off\n"
        f"  {pre}GIT_CACHE_TTL    int; seconds the git worktree probe is cached. Wins\n"
        "                             over [git] cache_ttl (default 5).\n"
        f"  {pre}EXTERNAL_DIR     external drop-in segments directory (default\n"
        "                             "
        f"${{XDG_CONFIG_HOME:-~/.config}}/ai-kit/{spec.provider_dir})\n"
        f"  {pre}EXTERNAL_CACHE_TTL  default cache TTL (seconds) for external segments\n"
        f"  {pre}PROVIDER_<VAR>  env vars handed to external provider scripts\n"
        "                             (ID, COLS, LINE, POSITION)\n"
        "\n"
        "Config precedence (low -> high): built-in defaults < TOML file < env."
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments for the status-line doctor CLI.

    --host is read first (parse_known_args) so the --help epilog shows the
    selected host's env-var help."""
    host_pre = argparse.ArgumentParser(add_help=False)
    host_pre.add_argument(
        "--host",
        choices=sorted(HOSTS),
        default="claude",
        help="select the status line to diagnose (default: claude)",
    )
    known, _unknown = host_pre.parse_known_args(argv)
    host = HOSTS[cast(str, known.host)]
    title = "Claude Code" if host.name == "claude" else "Cursor CLI"
    p = argparse.ArgumentParser(
        prog="statusline-doctor.py",
        parents=[host_pre],
        description=f"{title} status-line doctor — validate the config and "
        "dry-render every segment. Renders nothing on stdin.",
        epilog=env_help(host.config),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--print-config",
        action="store_true",
        help="resolve config (defaults < file < env), print it as JSON, and exit",
    )
    p.add_argument(
        "--check",
        nargs="?",
        const=None,
        default=_NO_CHECK,
        metavar="FILE",
        help="validate a config file (default: the resolved path) and exit non-zero if invalid",
    )
    p.add_argument(
        "--doctor",
        action="store_true",
        help="validate the config AND dry-render every segment to "
        "surface a builder that raises; exit non-zero if unhealthy",
    )
    return p.parse_args(argv)


def cmd_print_config(cfg: Any, env: Env) -> str:
    """Resolved config as pretty JSON (no rendering)."""
    # The top-level external `ttl`/`dir` are the GLOBAL resolved defaults
    # (defaults < [external] file < env) — resolved the same way cfg_load_config
    # does, so they're meaningful even when zero providers are discovered and
    # are never confused with a single provider's per-header `ttl=` override
    # (those appear per-entry in the "providers" array below). `dir` is the
    # PROVIDERS directory (where scripts live), NOT the XDG cache dir.
    _ = env
    ext_providers: Any = cfg.external.providers if cfg.external else []
    ext_dir: Any = cfg.external.dir if cfg.external else ""
    ext_ttl: Any = cfg.external.cache_ttl if cfg.external else _EXTERNAL_CACHE_TTL
    providers: list[dict[str, Any]] = [
        {
            "id": s.id,
            "path": s.path,
            "line": s.line,
            "position": common_types.util_position_str(s.position),
            "timeout": s.timeout,
            "ttl": s.ttl,
        }
        for s in cast("list[Any]", ext_providers)
    ]
    return json.dumps(
        {
            "segments": cfg.segments,
            "layout": [{"min_rows": ln.min_rows, "segments": ln.segments} for ln in cfg.layout],
            "palette": cfg.palette,
            "ramps": cfg.ramps,
            "git": cfg.git or {},
            "external": {
                "ttl": ext_ttl,
                "dir": ext_dir,
                "providers": providers,
            },
        },
        indent=2,
    )


def validate_config_file(  # pylint: disable=too-many-locals,too-many-statements,too-many-branches
    path: str,
    env: Env,
    host: common_render.Host = claude_host.HOST,
) -> list[str]:
    """Return a list of human-readable error strings for the config at path
    (empty list = valid), checked against the selected host's spec and builders.
    Checks: parseability, unknown segment keys, unknown palette keys, palette
    color values, [[line]] segments that are not real builders, and [ramp.*]
    band names / thresholds / colors. Fully offline — never fetches quota."""
    spec = host.config
    if tomllib is None:
        return ["tomllib unavailable (Python < 3.11): cannot validate"]
    try:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
    except FileNotFoundError:
        return [f"{path}: no such file"]
    except (OSError, tomllib.TOMLDecodeError) as e:
        return [f"{path}: {e}"]
    errors: list[str] = []
    ext_dir, ext_ttl = common_config.cfg_resolve_external(raw, env, spec.provider_dir)
    _, ext_dir, ext_ttl, _ = common_config.cfg_bind_scalars(
        raw,
        env,
        common_config.cfg_default_config(spec).git or {},
        ext_dir,
        ext_ttl,
        spec.env_prefix,
    )
    seg_cache = os.path.join(common_config.cfg_cache_base(env), spec.provider_cache)
    ext_ids = {s.id for s in common_config.core_discover_external(ext_dir, ext_ttl, seg_cache)}
    known_segments = set(common_config.cfg_default_config(spec).segments) | ext_ids
    for k in cast(dict[str, Any], raw.get("segments") or {}):
        if k not in known_segments:
            errors.append(f"unknown segment key: {k}")
    for k in cast(dict[str, Any], raw.get("palette") or {}):
        if k not in _PALETTE_DEFAULTS:
            errors.append(f"unknown palette key: {k}")
    for name, value in cast(dict[str, Any], raw.get("palette") or {}).items():
        if (
            name in _PALETTE_DEFAULTS
            and common_types.util_parse_color(str(value), palette=None) is None
        ):
            errors.append(f"bad palette color: {name} = {value!r}")
    for i, line in enumerate(cast(list[Any], raw.get("line") or [])):
        line_dict = cast(dict[str, Any], line) if isinstance(line, dict) else {}
        for seg in cast(list[Any], line_dict.get("segments") or []):
            if seg not in host.builders and seg not in ext_ids:
                errors.append(f"line[{i}] references unknown segment: {seg}")
    resolved_palette = common_render.core_resolve_palette(
        {
            str(k): str(v)
            for k, v in cast(dict[str, Any], raw.get("palette") or {}).items()
            if k in _PALETTE_DEFAULTS
        }
    )
    for band, table in cast(dict[str, Any], raw.get("ramp") or {}).items():
        if band not in spec.ramp_defaults:
            errors.append(f"unknown ramp: {band}")
            continue
        if not isinstance(table, dict):
            errors.append(f"ramp [{band}] must be a table")
            continue
        for thr, spec_color in cast(dict[Any, Any], table).items():
            try:
                common_types.util_parse_threshold(str(thr))
            except ValueError:
                errors.append(f"ramp [{band}] bad threshold: {thr!r}")
            if common_types.util_parse_color(str(spec_color), resolved_palette) is None:
                errors.append(f"ramp [{band}] bad color: {spec_color!r}")
    for k, v in cast(dict[str, Any], raw.get("git") or {}).items():
        problem = common_config.cfg_git_key_problem(k, v)
        if problem == "unknown":
            errors.append(f"unknown [git] key: {k}")
        elif problem == "bad_ttl":
            errors.append(f"[git] cache_ttl must be an integer, got {v!r}")
    ext: Any = raw.get("external")
    if ext is not None:
        if not isinstance(ext, dict):
            errors.append("[external] must be a table")
        else:
            ext_dict: dict[str, Any] = cast(dict[str, Any], ext)
            for k in ext_dict:
                if k not in ("ttl", "dir"):
                    errors.append(f"unknown [external] key: {k}")
            ttl_val = ext_dict.get("ttl")
            if "ttl" in ext_dict and (not isinstance(ttl_val, int) or isinstance(ttl_val, bool)):
                errors.append(f"[external] ttl must be an integer, got {ttl_val!r}")
            if "dir" in ext_dict and not isinstance(ext_dict["dir"], str):
                errors.append(f"[external] dir must be a string, got {ext_dict['dir']!r}")
    return errors


# A representative status JSON for the doctor's dry render. Self-contained (no
# fixture file): exercises every default builder so one that raises is surfaced.
_DOCTOR_SAMPLE = {
    "model": {"display_name": "Opus 4.8", "id": "claude-opus-4-8"},
    "cost": {
        "total_lines_added": 12,
        "total_lines_removed": 3,
        "total_cost_usd": 0.0123,
        "total_duration_ms": 45000,
        "total_api_duration_ms": 12000,
    },
    "context_window": {"used_percentage": 42, "context_window_size": 200000},
    "workspace": {"current_dir": "."},
    "transcript_path": "",
    "session_id": "doctor-sample",
    "rate_limits": {},
    "effort": {"level": "high"},
}

# The Cursor sample mirrors the synthetic payload shape (tests/fixtures/cursor/
# payload_synthetic.json): model block with param_summary, cwd/workspace, an
# explicit render width (keeps the dry render off the terminal probe) and a
# context window. Quota comes from the on-disk cache, never the network.
_DOCTOR_SAMPLE_CURSOR: dict[str, Any] = {
    "session_id": "doctor-sample",
    "transcript_path": "",
    "render_width_chars": 116,
    "cwd": ".",
    "autorun": False,
    "model": {
        "id": "synthetic-model",
        "display_name": "Synthetic Model",
        "param_summary": "high",
        "max_mode": False,
    },
    "workspace": {"current_dir": ".", "project_dir": ".", "added_dirs": []},
    "version": "synthetic-cli-version",
    "output_style": {"name": "default"},
    "context_window": {"context_window_size": 200000, "used_percentage": 42.5},
    "session_name": "doctor session",
    "vim": {"mode": "normal"},
    "worktree": {"name": "synthetic", "path": "."},
}

_DOCTOR_SAMPLES: dict[str, dict[str, Any]] = {
    "claude": _DOCTOR_SAMPLE,
    "cursor": _DOCTOR_SAMPLE_CURSOR,
}


def _dry_render_failures(
    cfg: Any,
    theme: Any,
    env: Env,
    host: common_render.Host = claude_host.HOST,
) -> set[str]:
    """Run EVERY builder once against the host's sample input — including
    segments that are disabled or absent from the layout — and return the set
    of segment keys whose builder raised. Dry-rendering only the
    enabled+reachable subset would let a broken disabled builder (e.g. `cost`)
    pass the doctor and then crash the moment the user enables it, which is
    exactly the failure class the doctor exists to catch. `core_safe_build`
    (not the packer's flag gate) does the catching, so we invoke it directly
    for each key.

    Note: this catches builders that crash on *valid* input. A builder that only
    raises on a missing/malformed key won't be surfaced by this happy-path sample.
    For the Cursor host this reads quota from the on-disk cache (offline); the
    caller refreshes it beforehand so no detached refresher is spawned here."""
    ctx = host.build_context(
        dict(_DOCTOR_SAMPLES[host.name]), cfg, theme, env, time.perf_counter_ns()
    )
    for key in host.builders:
        common_render.core_safe_build(key, ctx, 200, theme, host.builders)
    return ctx.failed


def _env_problems(env: Env, host: common_render.Host = claude_host.HOST) -> list[str]:
    """Return env-side bind problems from the render core's verbose config load.

    Calls cfg_load_config_verbose and filters to problems that originate from
    the selected host's env vars (identified by the host's env prefix in the
    message). Each returned string is a raw problem message (no ANSI, no
    'status-line: ' prefix); pass through common_config.cfg_warn to emit it as
    a dim warning."""
    _, problems = common_config.cfg_load_config_verbose(env, host.config)
    prefix = host.config.env_prefix
    return [p for p in problems if prefix in p]


_QUOTA_LABEL = " (inferred — undocumented Cursor API)"

# State-specific, token-free guidance for the Cursor quota report.
_QUOTA_HINTS = {
    "auth_expired": "quota auth: expired — run `cursor-agent login` to sign in again",
    "auth_unsupported": "quota auth: the Cursor login type is not supported",
    "auth_missing": "quota auth: no Cursor login was found — run `cursor-agent login`",
}


def quota_report(env: Env, now: float, fetch_quota: FetchQuota | None = None) -> str:
    """One explicit foreground quota refresh + cache state, as report lines.

    Only a manual `--doctor --host cursor` calls this. When the single-flight
    lock is free it attempts ONE foreground refresh (the real fetch seam is
    cursor_quota.probe_refresh's own default, resolved at call time; tests
    inject fakes and deny the network as a backstop); when the lock is held it
    reads the cache and reports that a refresh is in progress. Token-free:
    only QuotaResult fields and diagnostics ever appear (SPEC R8)."""
    try:
        cache_base = common_config.cfg_cache_base(dict(env))
        cache_path, lock_path = cursor_quota.probe_cache_paths(cache_base)
    except OSError as exc:
        return f"quota: absent{_QUOTA_LABEL}\nquota cache: unavailable ({exc})"
    descriptor = cursor_quota.probe_try_lock(lock_path)
    if descriptor is None:
        note = "refresh: none started — a refresh is in progress (single-flight lock held)"
    else:
        cursor_quota.probe_release_lock(descriptor)
        cursor_quota.probe_refresh(
            cache_base, dict(env), now_fn=lambda: now, fetch_quota=fetch_quota
        )
        note = "refresh: one foreground refresh attempted (single-flight lock acquired)"
    result = cursor_quota.core_quota_state(cursor_quota.probe_read_cache(cache_path) or {}, now)
    lines = [f"quota: {result.state}{_QUOTA_LABEL}"]
    if result.fetched_at is not None:
        lines.append(f"quota data age: {max(0, int(now - result.fetched_at))}s")
    if result.diagnostic:
        lines.append(f"quota diagnostic: {result.diagnostic}")
    hint = _QUOTA_HINTS.get(result.state)
    if hint is not None:
        lines.append(hint)
    lines.append(note)
    return "\n".join(lines)


def _report_health(
    path: str, errors: list[str], failed: set[str], env_probs: list[str], host: Any
) -> int:
    """Print the config/render/env problem report; return the doctor exit code."""
    for e in errors:
        print(e, file=sys.stderr)
    for key in sorted(failed):
        print(f"segment '{key}' raised during render", file=sys.stderr)
    for p in env_probs:
        common_config.cfg_warn(p)
    if errors or failed or env_probs:
        doctor_cmd = common_render.core_doctor_cmd(host.doctor_suffix)
        print(f"after fixing, re-run: {doctor_cmd}", file=sys.stderr)
        return 1
    print(f"{path}: OK — config valid, all {len(host.builders)} segments render cleanly")
    return 0


def cmd_doctor(
    env: Env,
    host: common_render.Host = claude_host.HOST,
    fetch_quota: FetchQuota | None = None,
    now: float | None = None,
) -> int:
    """Validate the resolved config AND dry-render every segment builder (not just
    the enabled ones). Prints a report; returns process exit code (0 healthy,
    1 if any problem). Quota fetch status is reported for the Cursor host only,
    and only here — save validation and previews stay offline (synthetic quota).
    The quota refresh runs BEFORE the dry render so the render reads the
    just-refreshed cache and spawns no detached refresher."""
    spec = host.config
    quota_lines = ""
    if host.name == "cursor":
        stamp = time.time() if now is None else now
        quota_lines = quota_report(env, stamp, fetch_quota)
    path = common_config.cfg_config_path(env, spec)
    errors: list[str] = []
    if os.path.exists(path):
        errors = [f"{path}: {e}" for e in validate_config_file(path, env, host)]
    failed: set[str] = set()
    cfg = common_config.cfg_load_config(env, spec)  # never raises (degrades to defaults)
    try:
        theme = common_render.core_build_theme(cfg, host)
        failed = _dry_render_failures(cfg, theme, env, host)
    except Exception as e:  # pylint: disable=broad-exception-caught  # diagnostic backstop reports any crash
        errors.append(f"render pipeline crashed: {e!r}")
    code = _report_health(path, errors, failed, _env_problems(env, host), host)
    if quota_lines:
        print(quota_lines)
    return code


def cmd_check(
    path: str,
    env: Env,
    host: common_render.Host = claude_host.HOST,
) -> int:
    """Validate a config file; print result. Return process exit code (0/1)."""
    path = path or common_config.cfg_config_path(env, host.config)
    errors = validate_config_file(path, env, host)
    env_probs = _env_problems(env, host)
    if errors:
        for e in errors:
            print(f"{path}: {e}", file=sys.stderr)
        for p in env_probs:
            common_config.cfg_warn(p)
        return 1
    if env_probs:
        for p in env_probs:
            common_config.cfg_warn(p)
        return 1
    print(f"{path}: OK")
    return 0


def main() -> None:
    """CLI entrypoint: validate config and/or dry-render every segment."""
    env = os.environ
    args = parse_args(sys.argv[1:])
    host = HOSTS[cast(str, args.host)]
    if args.check is not _NO_CHECK:
        sys.exit(cmd_check(args.check, env, host))
    if args.doctor:
        sys.exit(cmd_doctor(env, host))
    if args.print_config:
        cfg = common_config.cfg_load_config(env, host.config)
        print(cmd_print_config(cfg, env))
        return
    parse_args(["--help"])


if __name__ == "__main__":
    main()
