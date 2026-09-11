"""CLI entrypoint for ai-kit-gsd-config. Dependency-injected `main()` (which_fn/run_fn/
env_fn), mirroring the same convention `skills/ai-kit-spec-review/ai_kit_spec/cli.py` uses,
so every subcommand is testable without a real subprocess or real filesystem state."""
import argparse
import json
import os
import shutil
import subprocess
import sys

from . import critical_agents, gsd_catalog, gsd_write, model_detect, preference_match

VALID_MODEL_PROFILES = ("quality", "balanced", "budget", "adaptive")

# This skill's own directory (skills/ai-kit-gsd-config), used by model_detect.
# resolve_ai_kit_spec_path's sibling-of-this-skill fallback candidate. cli.py lives one level
# below the skill root (ai_kit_gsd_config/cli.py), so dirname is applied twice.
_THIS_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_node_and_gsd_tools(which_fn, env_fn):
    """Resolves `node_bin`/`gsd_tools_path`; returns `(node_bin, gsd_tools_path, error)` --
    `error` is `None` on success, otherwise a one-line message naming which is missing. Never
    lets a `None` path reach `subprocess.run` as a positional argument."""
    node_bin = gsd_catalog.resolve_node_binary(which_fn)
    if node_bin is None:
        return None, None, "ai-kit-gsd-config: could not resolve 'node' on PATH"
    gsd_tools_path = gsd_catalog.resolve_gsd_tools_path(env_fn())
    if gsd_tools_path is None:
        return (
            None,
            None,
            "ai-kit-gsd-config: could not locate an installed gsd-core's gsd-tools.cjs",
        )
    return node_bin, gsd_tools_path, None


def _cmd_ensure_project(args, which_fn, run_fn, env_fn):
    node_bin, gsd_tools_path, error = _resolve_node_and_gsd_tools(which_fn, env_fn)
    if error:
        print(error, file=sys.stderr)
        return 2
    ensured = gsd_write.ensure_config_exists(node_bin, gsd_tools_path, args.project_dir, run_fn)
    print(json.dumps({"ensured": ensured}))
    return 0 if ensured else 1


def _cmd_apply_profile(args, which_fn, run_fn, env_fn):
    node_bin, gsd_tools_path, error = _resolve_node_and_gsd_tools(which_fn, env_fn)
    if error:
        print(error, file=sys.stderr)
        return 2
    applied, _output = gsd_write.config_set(
        node_bin, gsd_tools_path, args.project_dir, "model_profile", args.profile, run_fn
    )
    print(json.dumps({"applied": applied, "key": "model_profile", "value": args.profile}))
    return 0 if applied else 1


def _cmd_apply_critical_agents(args, which_fn, run_fn, env_fn):
    node_bin, gsd_tools_path, error = _resolve_node_and_gsd_tools(which_fn, env_fn)
    if error:
        print(error, file=sys.stderr)
        return 2

    unconditional_pairs = critical_agents.compute_overrides(None)
    unconditional_written = 0
    for key, value in unconditional_pairs.items():
        ok, output = gsd_write.config_set(
            node_bin, gsd_tools_path, args.project_dir, key, value, run_fn
        )
        if not ok:
            print(
                f"ai-kit-gsd-config: failed to write unconditional key '{key}': {output}",
                file=sys.stderr,
            )
            return 1
        unconditional_written += 1

    heavy_sweep_applied = False
    heavy_agents_written = 0
    degraded_reason = None

    model_catalog_path = gsd_catalog.resolve_model_catalog_cjs_path(gsd_tools_path)
    if model_catalog_path is None:
        degraded_reason = "model_catalog_not_found"
    else:
        catalog = gsd_catalog.query_agent_catalog(node_bin, model_catalog_path, run_fn)
        if catalog is None:
            degraded_reason = "live_query_failed"
        else:
            full_overrides = critical_agents.compute_overrides(catalog["tiers"])
            remaining_keys = set(full_overrides) - set(unconditional_pairs)
            for key in remaining_keys:
                ok, output = gsd_write.config_set(
                    node_bin, gsd_tools_path, args.project_dir, key, full_overrides[key], run_fn
                )
                if ok:
                    heavy_agents_written += 1
                else:
                    print(
                        f"ai-kit-gsd-config: failed to write heavy-sweep key '{key}': {output}",
                        file=sys.stderr,
                    )
            heavy_sweep_applied = True

    print(
        json.dumps(
            {
                "unconditional_written": unconditional_written,
                "heavy_sweep_applied": heavy_sweep_applied,
                "heavy_agents_written": heavy_agents_written,
                "degraded_reason": degraded_reason,
            }
        )
    )
    return 0


def _detect_candidate_pool(run_fn, env_fn):
    """Shared by both detect-*-candidate subcommands: resolves ai_kit_spec's shim, runs
    detect-runtimes (or degrades to an empty snapshot when the shim can't be found), and
    returns the built candidate pool. Never raises -- a missing sibling skill or a failed
    detection subprocess both degrade to an empty pool, which each matcher already handles
    (best_execution_candidate returns None, best_review_candidate returns the native
    last-resort)."""
    ai_kit_spec_path = model_detect.resolve_ai_kit_spec_path(_THIS_SKILL_DIR, env_fn())
    snapshot = None
    if ai_kit_spec_path is not None:
        snapshot = model_detect.detect_runtimes_snapshot(sys.executable, ai_kit_spec_path, run_fn)
    return model_detect.build_candidate_pool(snapshot)


def _cmd_detect_execution_candidate(args, which_fn, run_fn, env_fn):
    pool = _detect_candidate_pool(run_fn, env_fn)
    result = preference_match.best_execution_candidate(pool)
    if result is None:
        print(json.dumps({"cli": None, "model": None, "rule": None}))
        return 0
    cli_name, model, rule = result
    print(json.dumps({"cli": cli_name, "model": model, "rule": rule}))
    return 0


def _cmd_detect_review_candidate(args, which_fn, run_fn, env_fn):
    pool = _detect_candidate_pool(run_fn, env_fn)
    cli_name, model, rule = preference_match.best_review_candidate(pool)
    print(json.dumps({"cli": cli_name, "model": model, "rule": rule}))
    return 0


def main(
    argv: list,
    which_fn=shutil.which,
    run_fn=subprocess.run,
    env_fn=lambda: dict(os.environ),
) -> int:
    parser = argparse.ArgumentParser(prog="ai-kit-gsd-config")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ensure = sub.add_parser("ensure-project")
    p_ensure.add_argument("--project-dir", required=True)

    p_profile = sub.add_parser("apply-profile")
    p_profile.add_argument("--project-dir", required=True)
    p_profile.add_argument("--profile", required=True, choices=VALID_MODEL_PROFILES)

    p_critical = sub.add_parser("apply-critical-agents")
    p_critical.add_argument("--project-dir", required=True)

    sub.add_parser("detect-execution-candidate")
    sub.add_parser("detect-review-candidate")

    args = parser.parse_args(argv)

    if args.command == "ensure-project":
        return _cmd_ensure_project(args, which_fn, run_fn, env_fn)
    if args.command == "apply-profile":
        return _cmd_apply_profile(args, which_fn, run_fn, env_fn)
    if args.command == "apply-critical-agents":
        return _cmd_apply_critical_agents(args, which_fn, run_fn, env_fn)
    if args.command == "detect-execution-candidate":
        return _cmd_detect_execution_candidate(args, which_fn, run_fn, env_fn)
    if args.command == "detect-review-candidate":
        return _cmd_detect_review_candidate(args, which_fn, run_fn, env_fn)

    parser.error(f"unknown command: {args.command}")
    return 2
