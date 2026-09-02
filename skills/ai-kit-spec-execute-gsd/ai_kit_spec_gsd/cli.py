"""CLI entrypoint for ai-kit-spec-execute-gsd -- invoked via the ai-kit-spec-gsd.py shim. Mirrors
ai_kit_spec/cli.py's own subcommand pattern (Plan 1) so Task 5's SKILL.md gives an executing agent
one concrete, runnable command for every operation it performs -- resolve-dispatch, config-path,
write-workflow-key, clear-workflow-key, prepare-tooling, prepare-cross-ai-guidance,
write-resumable-state. There is no dispatch-phase/classify-failure subcommand: GSD's own
/gsd-execute-phase skill performs the actual dispatch in-session, invoked directly via the Skill
tool by Task 5's SKILL.md, never subprocess-invoked here (Task 1 finding 3)."""
import argparse
import json
import os
import subprocess
import sys

from ai_kit_spec.cache import cache_read_json, cache_write_json
from ai_kit_spec.detection import (
    CODEGRAPH_INDEX_TIMEOUT_SECONDS,
    build_codegraph_index_command,
    detect_tool_availability,
    ensure_codegraph_registered,
    resolve_agents_tooling_path,
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
    clear_workflow_key_if_adapter_owned,
    generate_run_id,
    read_gsd_config,
    resolve_active_runtime,
    resolve_gsd_config_path,
    write_active_runtime,
    write_model_profile,
    write_native_tier_override,
    write_workflow_key,
)


def main(argv: list, assemble_candidates_fn=assemble_candidates,
         read_gsd_config_fn=read_gsd_config, refresh_quota_cache_fn=refresh_quota_cache,
         cache_read_json_fn=cache_read_json, cache_write_json_fn=cache_write_json,
         write_tier_fn=write_native_tier_override, write_runtime_fn=write_active_runtime,
         write_model_profile_fn=write_model_profile,
         write_workflow_key_fn=write_workflow_key,
         clear_workflow_key_if_adapter_owned_fn=clear_workflow_key_if_adapter_owned,
         detect_tool_availability_fn=detect_tool_availability,
         resolve_agents_tooling_path_fn=resolve_agents_tooling_path,
         ensure_codegraph_registered_fn=ensure_codegraph_registered,
         build_codegraph_index_command_fn=build_codegraph_index_command,
         build_gsd_cross_ai_guidance_fn=build_gsd_cross_ai_guidance,
         run_fn=subprocess.run, write_resumable_state_fn=_write_resumable_state_default,
         stdout=sys.stdout) -> int:
    parser = argparse.ArgumentParser(prog="ai-kit-spec-execute-gsd")
    sub = parser.add_subparsers(dest="command", required=True)

    p_resolve = sub.add_parser("resolve-dispatch")
    p_resolve.add_argument("--cwd", required=True)
    p_resolve.add_argument("--config-path", required=True)
    p_resolve.add_argument("--target-dir", required=True)
    p_resolve.add_argument("--quota-path", required=True)
    p_resolve.add_argument("--phase-prompt-file", default=None,
                            help="used to compute a real required_context estimate; omit for 0")
    p_resolve.add_argument("--run-id", default=None,
                            help="omit to generate one -- this call's resolved run_id is ALSO "
                                 "printed in the JSON result (result['run_id']) so the caller can "
                                 "thread the SAME id into any later write-workflow-key/"
                                 "clear-workflow-key calls in the same wave")

    p_config_path = sub.add_parser("config-path")
    p_config_path.add_argument("--cwd", required=True)

    p_write_workflow = sub.add_parser("write-workflow-key")
    p_write_workflow.add_argument("--config-path", required=True)
    p_write_workflow.add_argument("--config-json", required=True,
                                   help="the current gsd_config dict as a JSON string -- thread "
                                        "the PREVIOUS write's own stdout into this on a second "
                                        "call in the same run")
    p_write_workflow.add_argument("--key", required=True)
    p_write_workflow.add_argument("--value-json", required=True,
                                   help="the value to write, as a JSON literal -- e.g. "
                                        "'\"codex exec ...\"' for a string, 'true' for a JSON "
                                        "boolean")
    p_write_workflow.add_argument("--run-id", required=True,
                                   help="the SAME run_id captured from this wave's "
                                        "resolve-dispatch call (result['run_id'])")

    p_clear_workflow = sub.add_parser("clear-workflow-key")
    p_clear_workflow.add_argument("--config-path", required=True)
    p_clear_workflow.add_argument("--config-json", required=True)
    p_clear_workflow.add_argument("--key", required=True)
    p_clear_workflow.add_argument("--run-id", required=True)

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
        gsd_config, status = read_gsd_config_fn(
            args.config_path, warn_fn=lambda msg: print(msg, file=sys.stderr))
        if status == "malformed":
            result = {"mode": "fallback_notice", "key": None, "cli": None,
                      "provenance": "fallback", "reason": "malformed_config",
                      "message": f"{args.config_path} is malformed/unreadable -- refusing to "
                                 f"write over it. Fix or remove it by hand, then re-run.",
                      "run_id": args.run_id if args.run_id else generate_run_id()}
            stdout.write(json.dumps(result))
            return 0
        run_id = args.run_id if args.run_id else generate_run_id()
        candidates, top_n_keys = assemble_candidates_fn(args.cwd, dict(os.environ))
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
        result = resolve_gsd_dispatch(
            candidates, top_n_keys, gsd_config, args.config_path, args.target_dir,
            current_runtime=resolve_active_runtime(gsd_config), required_context=required_context,
            quota=quota, run_id=run_id, write_tier_fn=write_tier_fn,
            write_runtime_fn=write_runtime_fn, write_model_profile_fn=write_model_profile_fn)
        result["run_id"] = run_id
        stdout.write(json.dumps(result))
        return 0

    if args.command == "config-path":
        stdout.write(resolve_gsd_config_path(args.cwd) + "\n")
        return 0

    if args.command == "write-workflow-key":
        gsd_config = json.loads(args.config_json)
        value = json.loads(args.value_json)
        result = write_workflow_key_fn(args.config_path, gsd_config, args.key, value,
                                        run_id=args.run_id)
        stdout.write(json.dumps(result))
        return 0

    if args.command == "clear-workflow-key":
        gsd_config = json.loads(args.config_json)
        result = clear_workflow_key_if_adapter_owned_fn(args.config_path, gsd_config, args.key,
                                                          run_id=args.run_id)
        stdout.write(json.dumps(result))
        return 0

    if args.command == "prepare-tooling":
        tool_availability = detect_tool_availability_fn()
        agents_tooling_path = resolve_agents_tooling_path_fn()
        codegraph_registered = False
        if args.cli is not None:
            codegraph_registered = ensure_codegraph_registered_fn(args.cli)
            if codegraph_registered:
                index_cmd = build_codegraph_index_command_fn(args.target_dir)
                try:
                    result = run_fn(index_cmd, shell=True, capture_output=True, text=True,
                                     check=False, timeout=CODEGRAPH_INDEX_TIMEOUT_SECONDS)
                    if result.returncode != 0:
                        codegraph_registered = False
                except (subprocess.TimeoutExpired, OSError):
                    codegraph_registered = False
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
