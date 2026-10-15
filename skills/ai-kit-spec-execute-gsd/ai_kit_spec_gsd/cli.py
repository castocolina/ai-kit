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


def _resolve_gsd_tooling(cwd: str, which_fn, resolve_gsd_tools_fn) -> tuple:
    """Resolves (node, gsd-tools path), printing which piece is missing to stderr -- returns
    (None, None) so the caller can exit 2."""
    node = which_fn("node")
    if not node:
        print("ai-kit-spec-execute-gsd: node not found on PATH -- required to run gsd-tools",
              file=sys.stderr)
        return None, None
    tools_path = resolve_gsd_tools_fn(start=cwd)
    if not tools_path:
        print(f"ai-kit-spec-execute-gsd: no gsd-tools.cjs found for {cwd} -- GSD must be "
              f"installed (project-local gsd-core first)", file=sys.stderr)
        return None, None
    return node, tools_path


def _default_resolve_gsd_tools(start: str):
    return gsd_tools.resolve_gsd_tools(start=start)


def _build_write_context(cwd: str, run_id: str, which_fn=shutil.which,
                          resolve_gsd_tools_fn=_default_resolve_gsd_tools,
                          run_fn=subprocess.run) -> GsdWriteContext | None:
    """The one helper that builds a GsdWriteContext: resolves node + gsd-tools, asks gsd-tools
    for the workstream-aware config path, and prints the `ai-kit: gsd-core <version> at <path>`
    banner to stderr so a previousValue contract drift on a non-1.16 gsd-core is diagnosable
    from every config-writing run. Returns None (after naming the miss) when node or gsd-tools
    cannot be resolved."""
    node, tools_path = _resolve_gsd_tooling(cwd, which_fn, resolve_gsd_tools_fn)
    if node is None:
        return None
    tools = gsd_tools.GsdTools(node_bin=node, gsd_tools_path=tools_path)
    config_path = gsd_tools.config_path(tools, cwd, run_fn=run_fn)
    if not config_path:
        config_path = os.path.join(cwd, ".planning", "config.json")
    version = gsd_tools.gsd_core_version(tools_path)
    print(f"ai-kit: gsd-core {version or 'unknown'} at {tools_path}", file=sys.stderr)
    return GsdWriteContext(tools=tools, project_dir=cwd, config_path=config_path,
                            run_id=run_id, run_fn=run_fn)


def main(argv: list, **kwargs) -> int:
    """Wrapper around _main that turns a ConfigError (D-11/R13) into a loud failure: print
    the path + parser message to stderr and exit 2 -- a broken review-spec.toml must stop
    the CLI, never silently disable cross-AI review."""
    try:
        return _main(argv, **kwargs)
    except ConfigError as exc:
        print(f"ai-kit-spec-execute-gsd: config error: {exc}", file=sys.stderr)
        return 2


def _main(argv: list, assemble_candidates_fn=assemble_candidates,
         read_gsd_config_fn=read_gsd_config, refresh_quota_cache_fn=refresh_quota_cache,
         cache_read_json_fn=cache_read_json, cache_write_json_fn=cache_write_json,
         which_fn=shutil.which, resolve_gsd_tools_fn=_default_resolve_gsd_tools,
         detect_tool_availability_fn=detect_tool_availability,
         resolve_agents_tooling_path_fn=resolve_agents_tooling_path,
         probe_codegraph_fn=probe_codegraph,
         run_codegraph_index_fn=run_codegraph_index,
         build_gsd_cross_ai_guidance_fn=build_gsd_cross_ai_guidance,
         run_fn=subprocess.run, write_resumable_state_fn=_write_resumable_state_default,
         stdout=sys.stdout) -> int:
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
    p_prepare.add_argument("--cli", default=None,
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

    args = parser.parse_args(argv)

    if args.command == "resolve-dispatch":
        run_id = args.run_id if args.run_id else generate_run_id()
        # cfg_resolve (inside assemble) runs FIRST: a malformed local review-spec.toml is a
        # loud ConfigError/exit 2 (D-11/R13) before any gsd-tools run or config write (D-15).
        candidates, top_n_keys = assemble_candidates_fn(args.cwd, dict(os.environ))
        # D-17: the config path comes from gsd-tools config-path (workstream-aware); the
        # gsd-core version banner prints here too, before any config-set this run may make.
        ctx = _build_write_context(args.cwd, run_id, which_fn=which_fn,
                                    resolve_gsd_tools_fn=resolve_gsd_tools_fn, run_fn=run_fn)
        if ctx is None:
            return 2
        gsd_config, status = read_gsd_config_fn(
            ctx.config_path, warn_fn=lambda msg: print(msg, file=sys.stderr))
        if status == "malformed":
            result = {"mode": "fallback_notice", "key": None, "cli": None,
                      "provenance": "fallback", "reason": "malformed_config",
                      "message": f"{ctx.config_path} is malformed/unreadable -- refusing to "
                                 f"write over it. Fix or remove it by hand, then re-run.",
                      "run_id": run_id}
            stdout.write(json.dumps(result))
            return 0
        existing_quota = cache_read_json_fn(args.quota_path) or {}
        quota = refresh_quota_cache_fn(
            {"reviewers": [
                {"key": c["key"], "model": c["model"], "vendor": c["vendor"], "cli": c["cli"],
                 "command": c.get("command")}
                for c in candidates
            ]},
            [c["key"] for c in candidates], existing_quota, QUOTA_TTL_SECONDS)
        cache_write_json_fn(args.quota_path, quota)
        required_context = 0
        if args.phase_prompt_file:
            try:
                with open(args.phase_prompt_file, encoding="utf-8") as f:
                    required_context = estimate_required_context(f.read())
            except OSError as exc:
                print(f"ai-kit-spec-execute-gsd: could not read --phase-prompt-file "
                      f"{args.phase_prompt_file!r} ({exc}) -- falling back to "
                      f"required_context=0", file=sys.stderr)
        try:
            result = resolve_gsd_dispatch(
                candidates, top_n_keys, gsd_config, ctx, args.target_dir,
                current_runtime=resolve_active_runtime(gsd_config),
                required_context=required_context, quota=quota)
        except ValueError as exc:
            # D-15 (Phase 16.1): an explicit purpose = "execute" entry naming an unsupported CLI
            # (claude/grok) is a hard config error -- fail before any config write, never fall
            # back to another CLI.
            print(f"ai-kit-spec-execute-gsd: {exc}", file=sys.stderr)
            return 2
        result["run_id"] = run_id
        stdout.write(json.dumps(result))
        return 1 if result.get("mode") == "write_failed" else 0

    if args.command == "config-path":
        node, tools_path = _resolve_gsd_tooling(args.cwd, which_fn, resolve_gsd_tools_fn)
        if node is None:
            return 2
        tools = gsd_tools.GsdTools(node_bin=node, gsd_tools_path=tools_path)
        resolved = gsd_tools.config_path(tools, args.cwd, run_fn=run_fn)
        if not resolved:
            print(f"ai-kit-spec-execute-gsd: gsd-tools could not resolve a config path for "
                  f"{args.cwd}", file=sys.stderr)
            return 2
        stdout.write(resolved + "\n")
        return 0

    if args.command == "write-workflow-keys":
        ctx = _build_write_context(args.cwd, args.run_id, which_fn=which_fn,
                                    resolve_gsd_tools_fn=resolve_gsd_tools_fn, run_fn=run_fn)
        if ctx is None:
            return 2
        changes = []
        for spec in args.set:
            key, _, raw = spec.partition("=")
            changes.append(("workflow." + key, json.loads(raw)))
        result = apply_changes(ctx, changes)
        stdout.write(json.dumps(result._asdict()))
        return 1 if result.failed else 0

    if args.command == "clear-workflow-keys":
        ctx = _build_write_context(args.cwd, args.run_id, which_fn=which_fn,
                                    resolve_gsd_tools_fn=resolve_gsd_tools_fn, run_fn=run_fn)
        if ctx is None:
            return 2
        gsd_config, status = read_gsd_config(ctx.config_path,
                                              warn_fn=lambda msg: print(msg, file=sys.stderr))
        if status == "malformed":
            print(f"ai-kit-spec-execute-gsd: {ctx.config_path} is malformed -- refusing to "
                  f"clear workflow keys over it", file=sys.stderr)
            return 2
        changes = [("workflow." + key, None) for key in args.key
                   if is_adapter_owned(gsd_config, ctx.config_path, "workflow." + key)]
        result = apply_changes(ctx, changes)
        stdout.write(json.dumps(result._asdict()))
        return 1 if result.failed else 0

    if args.command == "prepare-tooling":
        tool_availability = detect_tool_availability_fn()
        agents_tooling_path = resolve_agents_tooling_path_fn()
        codegraph_registered = False
        if args.cli is not None:
            probe = probe_codegraph_fn(args.cli)
            if probe.install_command:
                print(f"ai-kit-spec-execute-gsd: codegraph MCP is not registered or not healthy "
                      f"for {args.cli}; install it with: {probe.install_command}",
                      file=sys.stderr)
            if probe.healthy is True:
                codegraph_registered = run_codegraph_index_fn(args.target_dir)
        guidance = build_tooling_guidance(
            args.cli, tool_availability, agents_tooling_path, codegraph_registered,
            shared_reference_path=resolve_shared_tooling_reference_path())
        stdout.write(guidance)
        return 0

    if args.command == "prepare-cross-ai-guidance":
        stdout.write(build_gsd_cross_ai_guidance_fn(args.resolved_label))
        return 0

    if args.command == "print-summary-format-block":
        # Just the raw SUMMARY.md shape (no resolved_label wrapper) -- for writing to a stable
        # file passed as ai_kit_spec's own `dispatch-execute --format-block-file`, which builds
        # the REST of the reinforcement prose (model-override/incremental-progress/failure-
        # reporting) itself at dispatch time. prepare-cross-ai-guidance (above) is for the OLDER
        # phase-prompt-file-append path; this is for the newer direct-dispatch-wrapper path.
        stdout.write(GSD_SUMMARY_FORMAT_BLOCK)
        return 0

    if args.command == "write-resumable-state":
        state = json.loads(args.state_json)
        write_resumable_state_fn(args.path, state)
        stdout.write(json.dumps({"written": True, "path": args.path}))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
