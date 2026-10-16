"""CLI entrypoint for ai-kit-spec-execute-gsd -- invoked via the ai-kit-spec-gsd.py shim. Mirrors
ai_kit_spec/cli.py's own subcommand pattern (Plan 1) so Task 5's SKILL.md gives an executing agent
one concrete, runnable command for every operation it performs -- resolve-dispatch, config-path,
write-workflow-keys, clear-workflow-keys, prepare-tooling, prepare-cross-ai-guidance,
write-resumable-state. There is no dispatch-phase/classify-failure subcommand: GSD's own
/gsd-execute-phase skill performs the actual dispatch in-session, invoked directly via the Skill
tool by Task 5's SKILL.md, never subprocess-invoked here (Task 1 finding 3)."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from typing import Any, NamedTuple, TextIO

from ai_kit_spec import gsd_tools
from ai_kit_spec.cache import cache_read_json, cache_write_json
from ai_kit_spec.config_io import ConfigError
from ai_kit_spec.detection import (
    detect_tool_availability,
    probe_codegraph,
    resolve_agents_tooling_path,
    run_codegraph_index,
)
from ai_kit_spec.dispatch import write_resumable_state as _write_resumable_state_default
from ai_kit_spec.quota import QUOTA_TTL_SECONDS, refresh_quota_cache
from ai_kit_spec.tooling_guidance import (
    build_tooling_guidance,
    resolve_shared_tooling_reference_path,
)

from ai_kit_spec_gsd.adapter import (
    DispatchContext,
    DispatchInputs,
    assemble_candidates,
    estimate_required_context,
    resolve_gsd_dispatch,
)
from ai_kit_spec_gsd.cross_ai_guidance import GSD_SUMMARY_FORMAT_BLOCK, build_gsd_cross_ai_guidance
from ai_kit_spec_gsd.gsd_config import (
    GsdWriteContext,
    apply_changes,
    generate_run_id,
    is_adapter_owned,
    read_gsd_config,
    resolve_active_runtime,
)


def _default_resolve_gsd_tools(start: str):
    return gsd_tools.resolve_gsd_tools(start=start)


class CliDeps(NamedTuple):
    assemble_candidates_fn: Callable[..., tuple] = assemble_candidates
    read_gsd_config_fn: Callable[..., tuple] = read_gsd_config
    refresh_quota_cache_fn: Callable[..., dict] = refresh_quota_cache
    cache_read_json_fn: Callable[[str], Any] = cache_read_json
    cache_write_json_fn: Callable[[str, Any], None] = cache_write_json
    which_fn: Callable[[str], str | None] = shutil.which
    resolve_gsd_tools_fn: Callable[..., str | None] = _default_resolve_gsd_tools
    detect_tool_availability_fn: Callable[[], dict] = detect_tool_availability
    resolve_agents_tooling_path_fn: Callable[[], str | None] = resolve_agents_tooling_path
    probe_codegraph_fn: Callable[..., Any] = probe_codegraph
    run_codegraph_index_fn: Callable[[str], bool] = run_codegraph_index
    build_gsd_cross_ai_guidance_fn: Callable[[str], str] = build_gsd_cross_ai_guidance
    run_fn: Callable[..., subprocess.CompletedProcess] = subprocess.run
    write_resumable_state_fn: Callable[..., None] = _write_resumable_state_default
    stdout: TextIO = sys.stdout


def _resolve_gsd_tooling(cwd: str, deps: CliDeps) -> tuple[str | None, str | None]:
    """Resolves (node, gsd-tools path), printing which piece is missing to stderr -- returns
    (None, None) so the caller can exit 2."""
    node = deps.which_fn("node")
    if not node:
        print("ai-kit-spec-execute-gsd: node not found on PATH -- required to run gsd-tools",
              file=sys.stderr)
        return None, None
    tools_path = deps.resolve_gsd_tools_fn(cwd)
    if not tools_path:
        print(f"ai-kit-spec-execute-gsd: no gsd-tools.cjs found for {cwd} -- GSD must be "
              f"installed (project-local gsd-core first)", file=sys.stderr)
        return None, None
    return node, tools_path


def _build_write_context(cwd: str, run_id: str, deps: CliDeps) -> GsdWriteContext | None:
    """The one helper that builds a GsdWriteContext: resolves node + gsd-tools, asks gsd-tools
    for the workstream-aware config path, and prints the `ai-kit: gsd-core <version> at <path>`
    banner to stderr so a previousValue contract drift on a non-1.16 gsd-core is diagnosable
    from every config-writing run. Returns None (after naming the miss) when node or gsd-tools
    cannot be resolved, or gsd-tools cannot resolve the config path -- never a guessed
    `<cwd>/.planning/config.json`, which in a workstream project is the wrong file (A-WR-04)."""
    node, tools_path = _resolve_gsd_tooling(cwd, deps)
    if node is None or tools_path is None:
        return None
    tools = gsd_tools.GsdTools(node_bin=node, gsd_tools_path=tools_path)
    config_path = gsd_tools.config_path(tools, cwd, run_fn=deps.run_fn)
    if not config_path:
        print(f"ai-kit-spec-execute-gsd: gsd-tools could not resolve a config path for {cwd}",
              file=sys.stderr)
        return None
    version = gsd_tools.gsd_core_version(tools_path)
    print(f"ai-kit: gsd-core {version or 'unknown'} at {tools_path}", file=sys.stderr)
    return GsdWriteContext(tools=tools, project_dir=cwd, config_path=config_path,
                            run_id=run_id, run_fn=deps.run_fn)


def _malformed_resolve_result(config_path: str, run_id: str) -> dict:
    return {
        "mode": "fallback_notice",
        "key": None,
        "runtime": None,
        "provenance": "fallback",
        "reason": "malformed_config",
        "message": (
            f"{config_path} is malformed/unreadable -- refusing to write over it. "
            f"Fix or remove it by hand, then re-run."
        ),
        "run_id": run_id,
    }


def _refresh_quota_for_candidates(
    deps: CliDeps, quota_path: str, candidates: list, existing_quota: dict,
) -> dict:
    quota = deps.refresh_quota_cache_fn(
        {"reviewers": [
            {"key": c["key"], "model": c["model"], "vendor": c["vendor"], "cli": c["runtime"],
             "command": c.get("command")}
            for c in candidates
        ]},
        [c["key"] for c in candidates], existing_quota, QUOTA_TTL_SECONDS)
    deps.cache_write_json_fn(quota_path, quota)
    return quota


def _required_context_from_prompt_file(path: str | None) -> int:
    if not path:
        return 0
    try:
        with open(path, encoding="utf-8") as f:
            return estimate_required_context(f.read())
    except OSError as exc:
        print(f"ai-kit-spec-execute-gsd: could not read --phase-prompt-file "
              f"{path!r} ({exc}) -- falling back to required_context=0", file=sys.stderr)
        return 0


def _cmd_resolve_dispatch(args: argparse.Namespace, deps: CliDeps) -> int:
    run_id = args.run_id if args.run_id else generate_run_id()
    candidates, top_n_keys = deps.assemble_candidates_fn(args.cwd, dict(os.environ))
    ctx = _build_write_context(args.cwd, run_id, deps)
    if ctx is None:
        return 2
    gsd_config, status = deps.read_gsd_config_fn(
        ctx.config_path, warn_fn=lambda msg: print(msg, file=sys.stderr))
    if status == "malformed":
        deps.stdout.write(json.dumps(_malformed_resolve_result(ctx.config_path, run_id)))
        return 0
    existing_quota = deps.cache_read_json_fn(args.quota_path) or {}
    quota = _refresh_quota_for_candidates(deps, args.quota_path, candidates, existing_quota)
    required_context = _required_context_from_prompt_file(args.phase_prompt_file)
    dispatch = DispatchContext(
        target_dir=args.target_dir,
        current_runtime=resolve_active_runtime(gsd_config),
        required_context=required_context,
        quota=quota,
    )
    try:
        result = resolve_gsd_dispatch(
            DispatchInputs(candidates, top_n_keys, gsd_config, ctx), dispatch)
    except ValueError as exc:
        print(f"ai-kit-spec-execute-gsd: {exc}", file=sys.stderr)
        return 2
    result["run_id"] = run_id
    deps.stdout.write(json.dumps(result))
    return 1 if result.get("mode") == "write_failed" else 0


def _cmd_config_path(args: argparse.Namespace, deps: CliDeps) -> int:
    node, tools_path = _resolve_gsd_tooling(args.cwd, deps)
    if node is None or tools_path is None:
        return 2
    tools = gsd_tools.GsdTools(node_bin=node, gsd_tools_path=tools_path)
    resolved = gsd_tools.config_path(tools, args.cwd, run_fn=deps.run_fn)
    if not resolved:
        print(f"ai-kit-spec-execute-gsd: gsd-tools could not resolve a config path for "
              f"{args.cwd}", file=sys.stderr)
        return 2
    deps.stdout.write(resolved + "\n")
    return 0


def _parse_workflow_set_specs(specs: list[str]) -> list:
    changes = []
    for spec in specs:
        key, _, raw = spec.partition("=")
        changes.append(("workflow." + key, json.loads(raw)))
    return changes


def _cmd_write_workflow_keys(args: argparse.Namespace, deps: CliDeps) -> int:
    try:
        changes = _parse_workflow_set_specs(args.set)
    except ValueError as exc:
        print(f"ai-kit-spec-execute-gsd: --set needs KEY=JSON ({exc})", file=sys.stderr)
        return 2
    ctx = _build_write_context(args.cwd, args.run_id, deps)
    if ctx is None:
        return 2
    result = apply_changes(ctx, changes)
    deps.stdout.write(json.dumps(result._asdict()))
    return 1 if result.failed else 0


def _cmd_clear_workflow_keys(args: argparse.Namespace, deps: CliDeps) -> int:
    ctx = _build_write_context(args.cwd, args.run_id, deps)
    if ctx is None:
        return 2
    gsd_config, status = deps.read_gsd_config_fn(
        ctx.config_path, warn_fn=lambda msg: print(msg, file=sys.stderr))
    if status == "malformed":
        print(f"ai-kit-spec-execute-gsd: {ctx.config_path} is malformed -- refusing to "
              f"clear workflow keys over it", file=sys.stderr)
        return 2
    changes = [
        ("workflow." + key, None) for key in args.key
        if is_adapter_owned(gsd_config, ctx.config_path, "workflow." + key)
    ]
    result = apply_changes(ctx, changes)
    deps.stdout.write(json.dumps(result._asdict()))
    return 1 if result.failed else 0


def _codegraph_registered_for_cli(cli_name: str | None, target_dir: str, deps: CliDeps) -> bool:
    if cli_name is None:
        return False
    probe = deps.probe_codegraph_fn(cli_name)
    if probe.install_command:
        print(f"ai-kit-spec-execute-gsd: codegraph MCP is not registered or not healthy "
              f"for {cli_name}; install it with: {probe.install_command}",
              file=sys.stderr)
    # D-20 (amended RUN-34): index when codegraph is registered and not known unhealthy;
    # codex exposes no health, so it is indexed with its health reported as unknown.
    if probe.registered is not True or probe.healthy is False:
        return False
    if probe.healthy is None:
        print(f"ai-kit-spec-execute-gsd: codegraph MCP health for {cli_name} is unknown "
              f"({probe.detail}); indexing anyway", file=sys.stderr)
    return deps.run_codegraph_index_fn(target_dir)


def _cmd_prepare_tooling(args: argparse.Namespace, deps: CliDeps) -> int:
    tool_availability = deps.detect_tool_availability_fn()
    agents_tooling_path = deps.resolve_agents_tooling_path_fn()
    codegraph_registered = _codegraph_registered_for_cli(args.runtime, args.target_dir, deps)
    guidance_cli = args.runtime if args.runtime is not None else "claude"
    guidance = build_tooling_guidance(
        guidance_cli, tool_availability, agents_tooling_path, codegraph_registered,
        shared_reference_path=resolve_shared_tooling_reference_path())
    deps.stdout.write(guidance)
    return 0


def _cmd_prepare_cross_ai_guidance(args: argparse.Namespace, deps: CliDeps) -> int:
    deps.stdout.write(deps.build_gsd_cross_ai_guidance_fn(args.resolved_label))
    return 0


def _cmd_print_summary_format_block(args: argparse.Namespace, deps: CliDeps) -> int:
    deps.stdout.write(GSD_SUMMARY_FORMAT_BLOCK)
    return 0


def _cmd_write_resumable_state(args: argparse.Namespace, deps: CliDeps) -> int:
    state = json.loads(args.state_json)
    deps.write_resumable_state_fn(args.path, state)
    deps.stdout.write(json.dumps({"written": True, "path": args.path}))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-kit-spec-execute-gsd")
    sub = parser.add_subparsers(dest="command", required=True)

    p_resolve = sub.add_parser("resolve-dispatch")
    p_resolve.add_argument("--cwd", required=True)
    p_resolve.add_argument("--target-dir", required=True)
    p_resolve.add_argument("--quota-path", required=True)
    p_resolve.add_argument("--phase-prompt-file", default=None,
                            help="used to compute a real required_context estimate; omit for 0")
    p_resolve.add_argument("--run-id", default=None,
                            help="omit to generate one -- this call's resolved run_id is ALSO "
                                 "printed in the JSON result (result['run_id']) so the caller can "
                                 "thread the SAME id into any later write-workflow-keys/"
                                 "clear-workflow-keys calls in the same wave")

    p_config_path = sub.add_parser("config-path")
    p_config_path.add_argument("--cwd", required=True)

    p_write_workflows = sub.add_parser("write-workflow-keys")
    p_write_workflows.add_argument("--cwd", required=True)
    p_write_workflows.add_argument("--run-id", required=True,
                                    help="the SAME run_id captured from this wave's "
                                         "resolve-dispatch call (result['run_id'])")
    p_write_workflows.add_argument("--set", action="append", required=True, metavar="KEY=JSON",
                                    help="workflow key (without the 'workflow.' prefix) and its "
                                         "JSON value -- e.g. '--set cross_ai_execution=true'")

    p_clear_workflows = sub.add_parser("clear-workflow-keys")
    p_clear_workflows.add_argument("--cwd", required=True)
    p_clear_workflows.add_argument("--run-id", required=True)
    p_clear_workflows.add_argument("--key", action="append", required=True,
                                    metavar="KEY",
                                    help="workflow key (without the 'workflow.' prefix) to "
                                         "unset -- only keys the sidecar marks adapter-owned")

    p_prepare = sub.add_parser("prepare-tooling")
    p_prepare.add_argument("--runtime", "--cli", dest="runtime", default=None,
                            help="omit (or pass 'claude') for native/current-runtime dispatch")
    p_prepare.add_argument("--target-dir", required=True)

    p_guidance = sub.add_parser("prepare-cross-ai-guidance")
    p_guidance.add_argument("--resolved-label", required=True,
                             help="human-readable description of the resolved dispatch, e.g. "
                                  "'codex, model gpt-5.6-sol' -- included verbatim in the "
                                  "model-selection-override sentence")

    sub.add_parser("print-summary-format-block")

    p_resume = sub.add_parser("write-resumable-state")
    p_resume.add_argument("--path", required=True)
    p_resume.add_argument("--state-json", required=True)

    return parser


_COMMANDS = {
    "resolve-dispatch": _cmd_resolve_dispatch,
    "config-path": _cmd_config_path,
    "write-workflow-keys": _cmd_write_workflow_keys,
    "clear-workflow-keys": _cmd_clear_workflow_keys,
    "prepare-tooling": _cmd_prepare_tooling,
    "prepare-cross-ai-guidance": _cmd_prepare_cross_ai_guidance,
    "print-summary-format-block": _cmd_print_summary_format_block,
    "write-resumable-state": _cmd_write_resumable_state,
}


def _dispatch(argv: list, deps: CliDeps) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = _COMMANDS.get(args.command)
    if handler is None:
        return 1
    return handler(args, deps)


def main(argv: list, deps: CliDeps | None = None, **overrides) -> int:
    """Wrapper around dispatch that turns a ConfigError (D-11/R13) into exit 2."""
    merged = (deps or CliDeps())._replace(**overrides)
    try:
        return _dispatch(argv, merged)
    except ConfigError as exc:
        print(f"ai-kit-spec-execute-gsd: config error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
