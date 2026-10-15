"""CLI entrypoint for ai-kit-gsd-curated-config. Dependency-injected `main()` (which_fn/run_fn/
env_fn), mirroring the same convention `skills/ai-kit-spec-review/ai_kit_spec/cli.py` uses,
so every subcommand is testable without a real subprocess or real filesystem state."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Any, NamedTuple

from . import (
    claude_md_detect,
    critical_agents,
    cross_ai_build,
    frontend_detect,
    gsd_catalog,
    host,
    inventory,
    model_detect,
    plan_io,
    preference_match,
    presets,
    recommend,
    workflow_defaults,
)

VALID_MODEL_PROFILES = ("quality", "balanced", "budget", "adaptive")

# This skill's own directory (skills/ai-kit-gsd-curated-config), used by model_detect.
# resolve_ai_kit_spec_path's sibling-of-this-skill fallback candidate. cli.py lives one level
# below the skill root (ai_kit_gsd_curated_config/cli.py), so dirname is applied twice.
_THIS_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _GsdCtx(NamedTuple):
    gsd: Any
    tools: Any
    project_dir: str
    run_fn: Any


def _resolve_node_and_gsd_tools(which_fn, env_fn, project_dir=None):
    """Returns `(gsd, tools, error)`: the shared `ai_kit_spec.gsd_tools` module, a populated
    `GsdTools(node_bin, gsd_tools_path)`, and `error` -- `None` on success, otherwise a
    one-line message naming what is missing (the ai-kit-spec-review sibling, `node`, or an
    installed gsd-core). Never lets a `None` path reach `subprocess.run`. `project_dir`
    seeds the shared resolver's project-local candidates (D-18: a project-local gsd-core
    wins over any global one)."""
    gsd = gsd_catalog.load_gsd_tools()
    if gsd is None:
        return (
            None,
            None,
            "ai-kit-gsd-curated-config: the ai-kit-spec-review sibling skill (ai_kit_spec) "
            "is not installed next to this skill",
        )
    node_bin = gsd_catalog.resolve_node_binary(which_fn)
    if node_bin is None:
        return None, None, "ai-kit-gsd-curated-config: could not resolve 'node' on PATH"
    gsd_tools_path = gsd_catalog.resolve_gsd_tools_path(env_fn(), start=project_dir)
    if gsd_tools_path is None:
        return (
            None,
            None,
            "ai-kit-gsd-curated-config: could not locate an installed gsd-core's gsd-tools.cjs",
        )
    return gsd, gsd.GsdTools(node_bin, gsd_tools_path), None


def _cmd_ensure_project(args, which_fn, run_fn, env_fn):
    gsd, tools, error = _resolve_node_and_gsd_tools(
        which_fn, env_fn, project_dir=args.project_dir
    )
    if error or gsd is None or tools is None:
        print(error, file=sys.stderr)
        return 2
    ensured = gsd.ensure_config_exists(tools, args.project_dir, run_fn=run_fn)
    print(json.dumps({"ensured": ensured}))
    return 0 if ensured else 1


def _cmd_apply_profile(args, which_fn, run_fn, env_fn):
    gsd, tools, error = _resolve_node_and_gsd_tools(
        which_fn, env_fn, project_dir=args.project_dir
    )
    if error or gsd is None or tools is None:
        print(error, file=sys.stderr)
        return 2
    applied, _output = gsd.config_set(
        tools, args.project_dir, "model_profile", args.profile, run_fn=run_fn
    )
    print(json.dumps({"applied": applied, "key": "model_profile", "value": args.profile}))
    return 0 if applied else 1


def _write_config_pairs(ctx: _GsdCtx, pairs, failure_label):
    """Return `None` on success, else an exit code."""
    for key, value in pairs.items():
        ok, output = ctx.gsd.config_set(
            ctx.tools, ctx.project_dir, key, value, run_fn=ctx.run_fn
        )
        if not ok:
            print(
                f"ai-kit-gsd-curated-config: failed to write {failure_label} key "
                f"'{key}': {output}",
                file=sys.stderr,
            )
            return 1
    return None


def _heavy_sweep_result(ctx: _GsdCtx, unconditional_pairs):
    """Apply tier-dependent overrides when the live catalog query succeeds."""
    model_catalog_path = gsd_catalog.resolve_model_catalog_cjs_path(ctx.tools.gsd_tools_path)
    if model_catalog_path is None:
        return False, 0, "model_catalog_not_found"
    catalog = gsd_catalog.query_agent_catalog(
        ctx.tools.node_bin, model_catalog_path, ctx.run_fn
    )
    if catalog is None:
        return False, 0, "live_query_failed"
    full_overrides = critical_agents.compute_overrides(catalog["tiers"])
    remaining_keys = set(full_overrides) - set(unconditional_pairs)
    heavy_agents_written = 0
    for key in remaining_keys:
        ok, output = ctx.gsd.config_set(
            ctx.tools, ctx.project_dir, key, full_overrides[key], run_fn=ctx.run_fn
        )
        if ok:
            heavy_agents_written += 1
        else:
            print(
                f"ai-kit-gsd-curated-config: failed to write heavy-sweep key "
                f"'{key}': {output}",
                file=sys.stderr,
            )
    return True, heavy_agents_written, None


def _cmd_apply_critical_agents(args, which_fn, run_fn, env_fn):
    gsd, tools, error = _resolve_node_and_gsd_tools(
        which_fn, env_fn, project_dir=args.project_dir
    )
    if error or gsd is None or tools is None:
        print(error, file=sys.stderr)
        return 2

    ctx = _GsdCtx(gsd, tools, args.project_dir, run_fn)
    unconditional_pairs = critical_agents.compute_overrides(None)
    fail = _write_config_pairs(ctx, unconditional_pairs, "unconditional")
    if fail is not None:
        return fail

    heavy_sweep_applied, heavy_agents_written, degraded_reason = _heavy_sweep_result(
        ctx, unconditional_pairs
    )

    print(
        json.dumps(
            {
                "unconditional_written": len(unconditional_pairs),
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
    # D-15 (Phase 16.1): validate `--cli` BEFORE the first config-set, workflow.cross_ai_execution
    # included -- a rejected executor (claude/grok, or any unsupported name) must leave the GSD
    # config completely untouched, on every run.
    if args.cli:
        rejection = cross_ai_build.reject_execute_cli(args.cli)
        if rejection:
            print(f"ai-kit-gsd-curated-config: {rejection}", file=sys.stderr)
            return 2

    gsd, tools, error = _resolve_node_and_gsd_tools(
        which_fn, env_fn, project_dir=args.project_dir
    )
    if error or gsd is None or tools is None:
        print(error, file=sys.stderr)
        return 2

    ok, output = gsd.config_set(
        tools, args.project_dir, "workflow.cross_ai_execution", True, run_fn=run_fn
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
            ok, output = gsd.config_set(
                tools, args.project_dir, "workflow.cross_ai_command", command, run_fn=run_fn
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


def _config_set_exit(ctx: _GsdCtx, key, value, label):
    """Return an exit code on failure, else `None`."""
    ok, output = ctx.gsd.config_set(
        ctx.tools, ctx.project_dir, key, value, run_fn=ctx.run_fn
    )
    if not ok:
        print(
            f"ai-kit-gsd-curated-config: failed to write {label}: {output}",
            file=sys.stderr,
        )
        return 1
    return None


def _apply_review_writes(ctx: _GsdCtx, args):
    """Return reviewer list on success, else an exit code."""
    slug = cross_ai_build.CLI_TO_REVIEWER_SLUG.get(args.cli)
    if slug is None:
        print(
            f"ai-kit-gsd-curated-config: unrecognized --cli {args.cli!r} "
            f"(expected one of {sorted(cross_ai_build.CLI_TO_REVIEWER_SLUG)})",
            file=sys.stderr,
        )
        return 2
    # Read before any write: a failed read must not overwrite the user's list (B-IN-10).
    got = ctx.gsd.config_get(
        ctx.tools, ctx.project_dir, "review.default_reviewers", run_fn=ctx.run_fn
    )
    if got.error is not None:
        print(
            f"ai-kit-gsd-curated-config: failed to read review.default_reviewers: {got.error}",
            file=sys.stderr,
        )
        return 1
    steps = (
        ("workflow.plan_review_convergence", True, "workflow.plan_review_convergence"),
        ("review.effort.opencode", "high", "review.effort.opencode"),
    )
    for key, value, label in steps:
        code = _config_set_exit(ctx, key, value, label)
        if code is not None:
            return code
    existing = got.value if got.found else None
    reviewers = list(existing) if isinstance(existing, list) else []
    if slug not in reviewers:
        reviewers.append(slug)
    for key, value, label in (
        ("review.default_reviewers", reviewers, "review.default_reviewers"),
        (f"review.models.{slug}", args.model, f"review.models.{slug}"),
    ):
        code = _config_set_exit(ctx, key, value, label)
        if code is not None:
            return code
    return reviewers


def _cmd_apply_review(args, which_fn, run_fn, env_fn):
    gsd, tools, error = _resolve_node_and_gsd_tools(
        which_fn, env_fn, project_dir=args.project_dir
    )
    if error or gsd is None or tools is None:
        print(error, file=sys.stderr)
        return 2

    result = _apply_review_writes(_GsdCtx(gsd, tools, args.project_dir, run_fn), args)
    if not isinstance(result, list):
        return result

    print(
        json.dumps(
            {
                "plan_review_convergence_written": True,
                "default_reviewers": result,
                "review_effort_opencode_written": True,
            }
        )
    )
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
    gsd, tools, error = _resolve_node_and_gsd_tools(
        which_fn, env_fn, project_dir=args.project_dir
    )
    if error or gsd is None or tools is None:
        print(error, file=sys.stderr)
        return 2

    if not args.path:
        print(json.dumps({"applied": False, "key": "claude_md_path", "reason": "empty_path"}))
        return 0

    ok, output = gsd.config_set(
        tools, args.project_dir, "claude_md_path", args.path, run_fn=run_fn
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
    gsd, tools, error = _resolve_node_and_gsd_tools(
        which_fn, env_fn, project_dir=args.project_dir
    )
    if error or gsd is None or tools is None:
        print(error, file=sys.stderr)
        return 2

    bundle_written = 0
    for key, value in workflow_defaults.WORKFLOW_DEFAULTS.items():
        # the shared _coerce_value maps Python None to gsd-tools' "null" unset sentinel
        ok, output = gsd.config_set(
            tools, args.project_dir, f"workflow.{key}", value, run_fn=run_fn
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

    ok, output = gsd.config_set(
        tools, args.project_dir, "workflow.ui_phase", ui_phase, run_fn=run_fn
    )
    if not ok:
        print(
            f"ai-kit-gsd-curated-config: failed to write workflow.ui_phase: {output}",
            file=sys.stderr,
        )
        return 1

    ok, output = gsd.config_set(
        tools, args.project_dir, "workflow.ui_review", ui_review, run_fn=run_fn
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


def _cmd_inventory(args, which_fn, run_fn, env_fn) -> int:
    deps = host.InventoryDeps(which_fn, run_fn, env_fn)
    inv, error = inventory.build_inventory(
        os.path.abspath(args.project_dir),
        inventory.InventoryOpts(args.host, refresh=args.refresh),
        deps,
    )
    if inv is None:
        print(f"ai-kit-gsd-curated-config: {error}", file=sys.stderr)
        return 2
    sys.stdout.write(plan_io.canonical_json(inv))
    return 0


def _cmd_recommend(args, which_fn, run_fn, env_fn) -> int:
    """Pure recommend: load + validate the inventory, build the plan, write `--out`
    atomically. Any load or write failure is a one-line stderr message and exit 2;
    success prints the entry/needs_choice/note counts as JSON."""
    del which_fn, run_fn, env_fn  # recommend performs no subprocess and no env read
    loaded, error = plan_io.load_inventory(args.inventory)
    if loaded is None:
        print(error, file=sys.stderr)
        return 2
    opts = recommend.RecommendOpts(
        profile=args.profile,
        rigor=args.rigor,
        cross_ai_review=args.cross_ai_review,
        cross_ai_exec=args.cross_ai_exec,
    )
    try:
        plan = recommend.build_plan(loaded, opts)
    except (KeyError, TypeError, ValueError) as exc:
        # Backstop for a shape the validator does not cover: one line, never a traceback.
        print(
            f"ai-kit-gsd-curated-config: inventory {args.inventory}: malformed ({exc}); "
            "rerun inventory",
            file=sys.stderr,
        )
        return 2
    try:
        plan_io.write_plan(args.out, plan)
    except OSError as exc:
        print(f"ai-kit-gsd-curated-config: cannot write {args.out}: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "out": args.out,
                "entries": len(plan["entries"]),
                "needs_choice": sum(
                    1 for e in plan["entries"] if e.get("status") == "needs_choice"
                ),
                "notes": len(plan["notes"]),
            }
        )
    )
    return 0


def _build_parser():
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

    p_inventory = sub.add_parser("inventory")
    p_inventory.add_argument("--project-dir", required=True)
    p_inventory.add_argument("--host", choices=host.HOSTS, default=None)
    p_inventory.add_argument(
        "--refresh",
        action="store_true",
        help="force detect-runtimes and a full catalog fetch",
    )

    p_recommend = sub.add_parser("recommend")
    p_recommend.add_argument("--inventory", required=True)
    p_recommend.add_argument(
        "--profile", required=True, choices=VALID_MODEL_PROFILES, help="adaptive recommended"
    )
    p_recommend.add_argument("--rigor", required=True, choices=presets.RIGORS)
    p_recommend.add_argument("--cross-ai-review", choices=("y", "n"), default=None)
    p_recommend.add_argument("--cross-ai-exec", choices=("y", "n"), default=None)
    p_recommend.add_argument(
        "--out",
        required=True,
        help="written atomically; keep it outside the project's .planning/",
    )

    p_apply_workflow_defaults = sub.add_parser("apply-workflow-defaults")
    p_apply_workflow_defaults.add_argument("--project-dir", required=True)
    p_apply_workflow_defaults.add_argument(
        "--ui-phase", required=True, choices=("true", "false")
    )
    p_apply_workflow_defaults.add_argument(
        "--ui-review", required=True, choices=("true", "false")
    )
    return parser


_COMMAND_HANDLERS = {
    "ensure-project": _cmd_ensure_project,
    "apply-profile": _cmd_apply_profile,
    "apply-critical-agents": _cmd_apply_critical_agents,
    "detect-execution-candidate": _cmd_detect_execution_candidate,
    "detect-review-candidate": _cmd_detect_review_candidate,
    "apply-execution": _cmd_apply_execution,
    "apply-review": _cmd_apply_review,
    "detect-claude-md-path": _cmd_detect_claude_md_path,
    "detect-frontend": _cmd_detect_frontend,
    "apply-claude-md-path": _cmd_apply_claude_md_path,
    "apply-workflow-defaults": _cmd_apply_workflow_defaults,
    "inventory": _cmd_inventory,
    "recommend": _cmd_recommend,
}


def main(
    argv: list,
    which_fn=shutil.which,
    run_fn=subprocess.run,
    env_fn=lambda: dict(os.environ),
) -> int:
    args = _build_parser().parse_args(argv)
    handler = _COMMAND_HANDLERS.get(args.command)
    if handler is None:
        _build_parser().error(f"unknown command: {args.command}")
    return handler(args, which_fn, run_fn, env_fn)
