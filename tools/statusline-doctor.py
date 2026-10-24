#!/usr/bin/env python3
"""ai-kit status-line doctor — config validation + dry-render introspection.

Renders nothing on the hot path. Imports the Claude host and shared modules directly
and exercises every builder against a self-contained sample
to surface a builder that raises. CLI:
  --doctor         validate the resolved config AND dry-render every segment
  --check [FILE]   validate a config file (default: the resolved path)
  --print-config   print the resolved config as JSON

The render module (status-line.py) intentionally no longer accepts these flags:
it renders only. All introspection lives here.
"""
# pyright: strict
# pylint: disable=invalid-name  # sibling script name is hyphenated (statusline-doctor.py)

import argparse
import json
import os
import sys
import time
from collections.abc import Mapping
from typing import Any, cast

import claude_host
import common_config
import common_render
import common_types

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
_RAMP_DEFAULTS = claude_host.RAMP_DEFAULTS_CLAUDE


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


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments for the status-line doctor CLI."""
    p = argparse.ArgumentParser(
        prog="statusline-doctor.py",
        description="Claude Code status-line doctor — validate the config and "
        "dry-render every segment. Renders nothing on stdin.",
        epilog=_ENV_HELP,
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
) -> list[str]:
    """Return a list of human-readable error strings for the config at path
    (empty list = valid). Checks: parseability, unknown segment keys, unknown
    palette keys, palette color values, [[line]] segments that are not real
    builders, and [ramp.*] band names / thresholds / colors."""
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
    ext_dir, ext_ttl = common_config.cfg_resolve_external(raw, env, claude_host.SPEC.provider_dir)
    _, ext_dir, ext_ttl, _ = common_config.cfg_bind_scalars(
        raw,
        env,
        common_config.cfg_default_config(claude_host.SPEC).git or {},
        ext_dir,
        ext_ttl,
        claude_host.SPEC.env_prefix,
    )
    seg_cache = os.path.join(common_config.cfg_cache_base(env), claude_host.SPEC.provider_cache)
    ext_ids = {s.id for s in common_config.core_discover_external(ext_dir, ext_ttl, seg_cache)}
    known_segments = set(common_config.cfg_default_config(claude_host.SPEC).segments) | ext_ids
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
            if seg not in claude_host.BUILDERS and seg not in ext_ids:
                errors.append(f"line[{i}] references unknown segment: {seg}")
    resolved_palette = common_render.core_resolve_palette(
        {
            str(k): str(v)
            for k, v in cast(dict[str, Any], raw.get("palette") or {}).items()
            if k in _PALETTE_DEFAULTS
        }
    )
    for band, table in cast(dict[str, Any], raw.get("ramp") or {}).items():
        if band not in _RAMP_DEFAULTS:
            errors.append(f"unknown ramp: {band}")
            continue
        if not isinstance(table, dict):
            errors.append(f"ramp [{band}] must be a table")
            continue
        for thr, spec in cast(dict[Any, Any], table).items():
            try:
                common_types.util_parse_threshold(str(thr))
            except ValueError:
                errors.append(f"ramp [{band}] bad threshold: {thr!r}")
            if common_types.util_parse_color(str(spec), resolved_palette) is None:
                errors.append(f"ramp [{band}] bad color: {spec!r}")
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


def _dry_render_failures(cfg: Any, theme: Any, env: Env) -> set[str]:
    """Run EVERY builder once against the sample input — including segments that
    are disabled or absent from the layout — and return the set of segment keys
    whose builder raised. Dry-rendering only the enabled+reachable subset would
    let a broken disabled builder (e.g. `cost`) pass the doctor and then crash
    the moment the user enables it, which is exactly the failure class the doctor
    exists to catch. `core_safe_build` (not the packer's flag gate) does the catching,
    so we invoke it directly for each key.

    Note: this catches builders that crash on *valid* input. A builder that only
    raises on a missing/malformed key won't be surfaced by this happy-path sample."""
    ctx = claude_host.HOST.build_context(
        dict(_DOCTOR_SAMPLE), cfg, theme, env, time.perf_counter_ns()
    )
    for key in claude_host.HOST.builders:
        common_render.core_safe_build(key, ctx, 200, theme, claude_host.HOST.builders)
    return ctx.failed


def _env_problems(env: Env) -> list[str]:
    """Return env-side bind problems from the render core's verbose config load.

    Calls cfg_load_config_verbose and filters to problems that originate from
    CC_AI_KIT_* env vars (identified by the 'CC_AI_KIT_' prefix in the message).
    Each returned string is a raw problem message (no ANSI, no 'status-line: '
    prefix); pass through common_config.cfg_warn to emit it as a dim warning."""
    _, problems = common_config.cfg_load_config_verbose(env, claude_host.SPEC)
    return [p for p in problems if "CC_AI_KIT_" in p]


def cmd_doctor(env: Env) -> int:
    """Validate the resolved config AND dry-render every segment builder (not just
    the enabled ones). Prints a report; returns process exit code (0 healthy, 1 if
    any problem)."""
    path = common_config.cfg_config_path(env, claude_host.SPEC)
    errors: list[str] = []
    if os.path.exists(path):
        errors = [f"{path}: {e}" for e in validate_config_file(path, env)]
    failed: set[str] = set()
    cfg = common_config.cfg_load_config(
        env, claude_host.SPEC
    )  # never raises (degrades to defaults)
    try:
        theme = common_render.core_build_theme(cfg, claude_host.HOST)
        failed = _dry_render_failures(cfg, theme, env)
    except Exception as e:  # pylint: disable=broad-exception-caught  # diagnostic backstop reports any crash
        errors.append(f"render pipeline crashed: {e!r}")
    env_probs = _env_problems(env)
    for e in errors:
        print(e, file=sys.stderr)
    for key in sorted(failed):
        print(f"segment '{key}' raised during render", file=sys.stderr)
    for p in env_probs:
        common_config.cfg_warn(p)
    if errors or failed or env_probs:
        doctor_cmd = common_render.core_doctor_cmd(claude_host.HOST.doctor_suffix)
        print(f"after fixing, re-run: {doctor_cmd}", file=sys.stderr)
        return 1
    print(f"{path}: OK — config valid, all {len(claude_host.BUILDERS)} segments render cleanly")
    return 0


def cmd_check(path: str, env: Env) -> int:
    """Validate a config file; print result. Return process exit code (0/1)."""
    path = path or common_config.cfg_config_path(env, claude_host.SPEC)
    errors = validate_config_file(path, env)
    env_probs = _env_problems(env)
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
    if args.check is not _NO_CHECK:
        sys.exit(cmd_check(args.check, env))
    if args.doctor:
        sys.exit(cmd_doctor(env))
    if args.print_config:
        cfg = common_config.cfg_load_config(env, claude_host.SPEC)
        print(cmd_print_config(cfg, env))
        return
    parse_args(["--help"])


if __name__ == "__main__":
    main()
