"""CLI entrypoint for ai-kit-gsd-curated-config. Dependency-injected `main()` (which_fn/run_fn/
env_fn), mirroring the same convention `skills/ai-kit-spec-review/ai_kit_spec/cli.py` uses,
so every subcommand is testable without a real subprocess or real filesystem state."""
import argparse
import json
import os
import shutil
import subprocess
import sys

from . import (
    claude_md_detect,
    critical_agents,
    cross_ai_build,
    frontend_detect,
    gsd_catalog,
    gsd_write,
    model_detect,
    preference_match,
    workflow_defaults,
)

VALID_MODEL_PROFILES = ("quality", "balanced", "budget", "adaptive")

# This skill's own directory (skills/ai-kit-gsd-curated-config), used by model_detect.
# resolve_ai_kit_spec_path's sibling-of-this-skill fallback candidate. cli.py lives one level
# below the skill root (ai_kit_gsd_curated_config/cli.py), so dirname is applied twice.
_THIS_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_node_and_gsd_tools(which_fn, env_fn):
    """Resolves `node_bin`/`gsd_tools_path`; returns `(node_bin, gsd_tools_path, error)` --
    `error` is `None` on success, otherwise a one-line message naming which is missing. Never
    lets a `None` path reach `subprocess.run` as a positional argument."""
    node_bin = gsd_catalog.resolve_node_binary(which_fn)
    if node_bin is None:
        return None, None, "ai-kit-gsd-curated-config: could not resolve 'node' on PATH"
    gsd_tools_path = gsd_catalog.resolve_gsd_tools_path(env_fn())
    if gsd_tools_path is None:
        return (
            None,
            None,
            "ai-kit-gsd-curated-config: could not locate an installed gsd-core's gsd-tools.cjs",
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
                f"ai-kit-gsd-curated-config: failed to write unconditional key '{key}': {output}",
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
                        f"ai-kit-gsd-curated-config: failed to write heavy-sweep key "
                        f"'{key}': {output}",
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


def _cmd_apply_execution(args, which_fn, run_fn, env_fn):
    node_bin, gsd_tools_path, error = _resolve_node_and_gsd_tools(which_fn, env_fn)
    if error:
        print(error, file=sys.stderr)
        return 2

    ok, output = gsd_write.config_set(
        node_bin, gsd_tools_path, args.project_dir, "workflow.cross_ai_execution", True, run_fn
    )
    if not ok:
        print(f"ai-kit-gsd-curated-config: failed to write workflow.cross_ai_execution: {output}",
              file=sys.stderr)
        return 1

    cross_ai_command_written = False
    degraded_reason = None
    if not args.cli:
        degraded_reason = "no_candidate"
    elif not args.model:
        # Without --model, build_execution_command would still succeed and interpolate the
        # literal string "None" into the rendered command (str.format has no None guard) --
        # a fabricated, broken command reported as success. Fail closed instead (D-05).
        degraded_reason = "no_model"
    else:
        command = cross_ai_build.build_execution_command(args.cli, args.model, args.project_dir)
        if command is None:
            degraded_reason = "no_builder"
        else:
            ok, output = gsd_write.config_set(
                node_bin, gsd_tools_path, args.project_dir, "workflow.cross_ai_command",
                command, run_fn
            )
            if not ok:
                print(
                    f"ai-kit-gsd-curated-config: failed to write "
                    f"workflow.cross_ai_command: {output}",
                    file=sys.stderr,
                )
                return 1
            cross_ai_command_written = True

    print(json.dumps({
        "cross_ai_execution_written": True,
        "cross_ai_command_written": cross_ai_command_written,
        "degraded_reason": degraded_reason,
    }))
    return 0


def _cmd_apply_review(args, which_fn, run_fn, env_fn):
    node_bin, gsd_tools_path, error = _resolve_node_and_gsd_tools(which_fn, env_fn)
    if error:
        print(error, file=sys.stderr)
        return 2

    ok, output = gsd_write.config_set(
        node_bin, gsd_tools_path, args.project_dir, "workflow.plan_review_convergence",
        True, run_fn
    )
    if not ok:
        print(
            f"ai-kit-gsd-curated-config: failed to write "
            f"workflow.plan_review_convergence: {output}",
            file=sys.stderr,
        )
        return 1

    ok, output = gsd_write.config_set(
        node_bin, gsd_tools_path, args.project_dir, "review.effort.opencode", "high", run_fn
    )
    if not ok:
        print(f"ai-kit-gsd-curated-config: failed to write review.effort.opencode: {output}",
              file=sys.stderr)
        return 1

    slug = cross_ai_build.CLI_TO_REVIEWER_SLUG[args.cli]
    existing = gsd_write.config_get(
        node_bin, gsd_tools_path, args.project_dir, "review.default_reviewers", run_fn
    )
    reviewers = list(existing) if existing else []
    if slug not in reviewers:
        reviewers.append(slug)

    ok, output = gsd_write.config_set(
        node_bin, gsd_tools_path, args.project_dir, "review.default_reviewers",
        json.dumps(reviewers), run_fn
    )
    if not ok:
        print(f"ai-kit-gsd-curated-config: failed to write review.default_reviewers: {output}",
              file=sys.stderr)
        return 1

    ok, output = gsd_write.config_set(
        node_bin, gsd_tools_path, args.project_dir, f"review.models.{slug}", args.model, run_fn
    )
    if not ok:
        print(f"ai-kit-gsd-curated-config: failed to write review.models.{slug}: {output}",
              file=sys.stderr)
        return 1

    print(json.dumps({
        "plan_review_convergence_written": True,
        "default_reviewers": reviewers,
        "review_effort_opencode_written": True,
    }))
    return 0


def _cmd_detect_claude_md_path(args, which_fn, run_fn, env_fn):
    path = claude_md_detect.detect_claude_md_path(args.project_dir)
    print(json.dumps({"path": path}))
    return 0


def _cmd_detect_frontend(args, which_fn, run_fn, env_fn):
    frontend_present = frontend_detect.detect_frontend_present(args.project_dir)
    print(json.dumps({"frontend_present": frontend_present}))
    return 0


def _cmd_apply_claude_md_path(args, which_fn, run_fn, env_fn):
    node_bin, gsd_tools_path, error = _resolve_node_and_gsd_tools(which_fn, env_fn)
    if error:
        print(error, file=sys.stderr)
        return 2

    if not args.path:
        print(json.dumps({"applied": False, "key": "claude_md_path", "reason": "empty_path"}))
        return 0

    ok, output = gsd_write.config_set(
        node_bin, gsd_tools_path, args.project_dir, "claude_md_path", args.path, run_fn
    )
    if not ok:
        print(
            f"ai-kit-gsd-curated-config: failed to write claude_md_path: {output}",
            file=sys.stderr,
        )
        return 1
    print(json.dumps({"applied": True, "key": "claude_md_path", "value": args.path}))
    return 0


def _cmd_apply_workflow_defaults(args, which_fn, run_fn, env_fn):
    node_bin, gsd_tools_path, error = _resolve_node_and_gsd_tools(which_fn, env_fn)
    if error:
        print(error, file=sys.stderr)
        return 2

    bundle_written = 0
    for key, value in workflow_defaults.WORKFLOW_DEFAULTS.items():
        # gsd-tools' own config-set recognizes the literal string "null" as its
        # unset/clear sentinel (config.cjs) -- gsd_write._coerce_value has no special case
        # for Python None (it falls through to `str(None)` == "None", a bare string gsd-tools
        # would persist verbatim rather than clearing the key). Two WORKFLOW_DEFAULTS entries
        # (code_review_command, plan_bounce_script) are None, so this substitution happens
        # here, scoped to this plan's own cli.py, rather than widening gsd_write.py's shared
        # coercion helper (out of this plan's declared files_modified).
        coerced_value = "null" if value is None else value
        ok, output = gsd_write.config_set(
            node_bin, gsd_tools_path, args.project_dir, f"workflow.{key}", coerced_value, run_fn
        )
        if not ok:
            print(
                f"ai-kit-gsd-curated-config: failed to write workflow.{key}: {output}",
                file=sys.stderr,
            )
            return 1
        bundle_written += 1

    ui_phase = args.ui_phase == "true"
    ui_review = args.ui_review == "true"

    ok, output = gsd_write.config_set(
        node_bin, gsd_tools_path, args.project_dir, "workflow.ui_phase", ui_phase, run_fn
    )
    if not ok:
        print(
            f"ai-kit-gsd-curated-config: failed to write workflow.ui_phase: {output}",
            file=sys.stderr,
        )
        return 1

    ok, output = gsd_write.config_set(
        node_bin, gsd_tools_path, args.project_dir, "workflow.ui_review", ui_review, run_fn
    )
    if not ok:
        print(
            f"ai-kit-gsd-curated-config: failed to write workflow.ui_review: {output}",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "bundle_written": bundle_written,
                "ui_phase": ui_phase,
                "ui_review": ui_review,
            }
        )
    )
    return 0


def main(
    argv: list,
    which_fn=shutil.which,
    run_fn=subprocess.run,
    env_fn=lambda: dict(os.environ),
) -> int:
    parser = argparse.ArgumentParser(prog="ai-kit-gsd-curated-config")
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

    p_apply_execution = sub.add_parser("apply-execution")
    p_apply_execution.add_argument("--project-dir", required=True)
    p_apply_execution.add_argument("--cli", default=None)
    p_apply_execution.add_argument("--model", default=None)

    p_apply_review = sub.add_parser("apply-review")
    p_apply_review.add_argument("--project-dir", required=True)
    p_apply_review.add_argument("--cli", required=True)
    p_apply_review.add_argument("--model", required=True)

    p_detect_claude_md_path = sub.add_parser("detect-claude-md-path")
    p_detect_claude_md_path.add_argument("--project-dir", required=True)

    p_detect_frontend = sub.add_parser("detect-frontend")
    p_detect_frontend.add_argument("--project-dir", required=True)

    p_apply_claude_md_path = sub.add_parser("apply-claude-md-path")
    p_apply_claude_md_path.add_argument("--project-dir", required=True)
    p_apply_claude_md_path.add_argument("--path", required=True)

    p_apply_workflow_defaults = sub.add_parser("apply-workflow-defaults")
    p_apply_workflow_defaults.add_argument("--project-dir", required=True)
    p_apply_workflow_defaults.add_argument(
        "--ui-phase", required=True, choices=("true", "false")
    )
    p_apply_workflow_defaults.add_argument(
        "--ui-review", required=True, choices=("true", "false")
    )

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
    if args.command == "apply-execution":
        return _cmd_apply_execution(args, which_fn, run_fn, env_fn)
    if args.command == "apply-review":
        return _cmd_apply_review(args, which_fn, run_fn, env_fn)
    if args.command == "detect-claude-md-path":
        return _cmd_detect_claude_md_path(args, which_fn, run_fn, env_fn)
    if args.command == "detect-frontend":
        return _cmd_detect_frontend(args, which_fn, run_fn, env_fn)
    if args.command == "apply-claude-md-path":
        return _cmd_apply_claude_md_path(args, which_fn, run_fn, env_fn)
    if args.command == "apply-workflow-defaults":
        return _cmd_apply_workflow_defaults(args, which_fn, run_fn, env_fn)

    parser.error(f"unknown command: {args.command}")
    return 2
