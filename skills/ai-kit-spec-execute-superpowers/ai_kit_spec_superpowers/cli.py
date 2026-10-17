"""CLI entrypoint for ai-kit-spec-execute-superpowers -- invoked via the
ai-kit-spec-superpowers.py shim. Mirrors ai_kit_spec_gsd.cli's own subcommand pattern (Plan 2) so
Task 4's SKILL.md gives an executing agent one concrete, runnable command for every operation:
resolve-injection (live-quota candidate resolution), dispatch-task (the actual write-capable
dispatch, which preserves an implementer-authored report file rather than overwriting it with
stdout -- CRITICAL finding), classify-dispatch-failure, resume-exclusions (computes what's safe
to PERSIST as a resumable-state exclusion set without permanently excluding a merely
quota-exhausted candidate -- CRITICAL finding), write-resumable-state. There is no native
dispatch subcommand -- that mode is dispatched in-process via the Agent tool, by Task 4's
SKILL.md directly, never subprocess-invoked here (same native/cross-AI split ai_kit_spec_gsd.cli
already uses). No separate prepare-tooling subcommand either (removed a prior revision, CRITICAL
finding) -- dispatch-task already computes and passes tooling guidance inputs itself; a
standalone subcommand whose output nothing read was dead code invoking a subcommand that never
actually existed."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from typing import Any, NamedTuple, TextIO

from ai_kit_spec.cache import cache_read_json, cache_write_json
from ai_kit_spec.config_io import ConfigError
from ai_kit_spec.detection import (
    LOOPBACK_URLOPEN,
    detect_tool_availability,
    probe_codegraph,
    resolve_agents_tooling_path,
    run_codegraph_index,
)
from ai_kit_spec.dispatch import write_resumable_state as _write_resumable_state_default
from ai_kit_spec.quota import QUOTA_TTL_SECONDS, refresh_quota_cache
from ai_kit_spec.routing import (
    RuntimesSeams,
    host_context,
    probe_keys,
    route_all,
    unroutable_quota,
)

from ai_kit_spec_superpowers.dispatch_injection import (
    BuildInjectionOptions,
    BuildInjectionRequest,
    DispatchTaskRequest,
    QuotaExhaustedError,
    SuperpowersDispatchGuidance,
    assemble_candidates,
    build_dispatch_injection,
    classify_dispatch_failure,
    compute_ladder_keys,
    compute_resume_exclusions,
    derive_files_touched_sizes,
    dispatch_superpowers_task,
    reasons_summary,
)
from ai_kit_spec_superpowers.task_classification import classify_task

_REPORT_FALLBACK_MARKER = (
    "[ai-kit-spec-execute-superpowers: no report file was written by the dispatched CLI -- "
    "falling back to captured stdout]\n\n"
)


class CliDeps(NamedTuple):
    assemble_candidates_fn: Callable[..., tuple] = assemble_candidates
    build_dispatch_injection_fn: Callable[..., dict] = build_dispatch_injection
    derive_files_touched_sizes_fn: Callable[..., dict] = derive_files_touched_sizes
    compute_ladder_keys_fn: Callable[..., list] = compute_ladder_keys
    reasons_summary_fn: Callable[[dict], dict] = reasons_summary
    classify_task_fn: Callable[[str], str | None] = classify_task
    dispatch_superpowers_task_fn: Callable[..., dict] = dispatch_superpowers_task
    classify_dispatch_failure_fn: Callable[[dict], str] = classify_dispatch_failure
    compute_resume_exclusions_fn: Callable[..., list] = compute_resume_exclusions
    cache_read_json_fn: Callable[[str], Any] = cache_read_json
    cache_write_json_fn: Callable[[str, Any], None] = cache_write_json
    refresh_quota_cache_fn: Callable[..., dict] = refresh_quota_cache
    detect_tool_availability_fn: Callable[[], dict] = detect_tool_availability
    resolve_agents_tooling_path_fn: Callable[[], str | None] = resolve_agents_tooling_path
    probe_codegraph_fn: Callable[..., Any] = probe_codegraph
    run_codegraph_index_fn: Callable[[str], bool] = run_codegraph_index
    write_resumable_state_fn: Callable[..., None] = _write_resumable_state_default
    route_all_fn: Callable[..., dict] = route_all
    which_fn: Callable[..., Any] = shutil.which
    run_fn: Callable[..., Any] = subprocess.run
    popen_fn: Callable[..., Any] = subprocess.Popen
    urlopen_fn: Callable[..., Any] = LOOPBACK_URLOPEN
    env_fn: Callable[[], dict] = lambda: dict(os.environ)
    stdout: TextIO = sys.stdout


class QuotaExhaustionEmitContext(NamedTuple):
    task_type: str | None
    ladder_keys: list
    exclude: set[str]
    excluded_reasons: dict
    tried: list
    reasons: dict


class ResolveTaskLoadResult(NamedTuple):
    task_markdown: str
    sizes: dict
    ladder_keys: list
    task_type: str | None
    exclude: set[str]
    excluded_reasons: dict
    candidates: list
    top_n_keys: list
    routes: dict


class ResolveInjectionRunInputs(NamedTuple):
    args: argparse.Namespace
    loaded: ResolveTaskLoadResult


def _parse_resolve_excludes(args: argparse.Namespace) -> tuple[set[str], set[str], dict]:
    excluded_reasons = json.loads(args.excluded_reasons_json)
    exclude = set(json.loads(args.exclude_keys_json))
    escalation_exclude = set(json.loads(args.escalation_excluded_keys_json))
    return exclude, escalation_exclude, excluded_reasons


def _merged_quota_exhaustion_payload(deps: CliDeps, ctx: QuotaExhaustionEmitContext) -> dict:
    merged_reasons = dict(ctx.excluded_reasons)
    merged_reasons.update(ctx.reasons)
    for key in ctx.exclude:
        merged_reasons.setdefault(key, "no_usable_dispatch")
    merged_tried = sorted(set(ctx.tried) | ctx.exclude)
    summary = deps.reasons_summary_fn(merged_reasons)
    return {
        "mode": "quota_exhausted",
        "task_type": ctx.task_type,
        "tried": merged_tried,
        "reasons": merged_reasons,
        "all_auth_failures": summary["all_auth_failures"],
        "any_quota_recoverable": summary["any_quota_recoverable"],
        "ladder_keys": ctx.ladder_keys,
    }


def _compute_ladder_or_exit(
    deps: CliDeps, request: BuildInjectionRequest, routes: dict,
) -> list | int:
    try:
        return deps.compute_ladder_keys_fn(request, routes)
    except ValueError as exc:
        if "cannot be an execution CLI" in str(exc):
            print(f"ai-kit-spec-execute-superpowers: {exc}", file=sys.stderr)
            return 2
        raise


def _native_probe_rows(candidates: list, routes: dict) -> dict:
    """Native rows to drop from the in-memory quota. A runtime-less session default is native too,
    but it was never a subprocess, so a row a caller stored for it is real quota and stays."""
    named = {c["key"] for c in candidates if c.get("runtime") is not None}
    return {key: "native" for key, decision in routes.items()
            if decision == "native" and key in named}


def _refresh_quota_for_candidates(
    deps: CliDeps, quota_path: str, candidates: list, existing_quota: dict, routes: dict,
) -> dict:
    """Probes subprocess and unverified candidates only, then drops every native-routed row from
    the returned dict. The cache file keeps what the refresh wrote; the drop is in memory, so a
    stale subprocess failure can never block a candidate this call routes native."""
    quota = deps.refresh_quota_cache_fn(
        {"reviewers": [
            {"key": c["key"], "model": c["model"], "vendor": c["vendor"], "runtime": c["runtime"],
             "command": c.get("command")} for c in candidates
        ]},
        probe_keys([c["key"] for c in candidates], routes), existing_quota, QUOTA_TTL_SECONDS)
    deps.cache_write_json_fn(quota_path, quota)
    return unroutable_quota(quota, _native_probe_rows(candidates, routes))


def _handle_build_value_error(
    exc: ValueError, task_type: str | None, ladder_keys: list, deps: CliDeps,
) -> int:
    if str(exc).startswith("no execute candidate survived"):
        deps.stdout.write(json.dumps({
            "mode": "no_candidate", "task_type": task_type, "detail": str(exc),
            "ladder_keys": ladder_keys,
        }))
        return 0
    if "cannot be an execution CLI" in str(exc):
        print(f"ai-kit-spec-execute-superpowers: {exc}", file=sys.stderr)
        return 2
    raise exc


def _routes_for(deps: CliDeps, candidates: list) -> dict:
    """One exec-mode routing of the full roster. The host is this process; the inventory is the
    runtimes cache, refreshed once for a runtime whose listing missed."""
    env = deps.env_fn()
    seams = RuntimesSeams(deps.which_fn, deps.run_fn, deps.popen_fn, deps.urlopen_fn)
    return deps.route_all_fn(candidates, host_context("exec", env, seams))


def _resolve_task_inputs(args: argparse.Namespace, deps: CliDeps) -> ResolveTaskLoadResult | int:
    full_candidates, full_top_n_keys = deps.assemble_candidates_fn(args.cwd, deps.env_fn())
    with open(args.task_file, encoding="utf-8") as f:
        task_markdown = f.read()
    sizes = deps.derive_files_touched_sizes_fn(task_markdown, args.cwd)
    routes = _routes_for(deps, full_candidates)
    ladder_keys = _compute_ladder_or_exit(
        deps, BuildInjectionRequest(task_markdown, full_candidates, sizes, {}, full_top_n_keys),
        routes)
    if isinstance(ladder_keys, int):
        return ladder_keys
    exclude, escalation_exclude, excluded_reasons = _parse_resolve_excludes(args)
    all_exclude = exclude | escalation_exclude
    candidates = [c for c in full_candidates if c["key"] not in all_exclude]
    top_n_keys = [k for k in full_top_n_keys if k not in all_exclude]
    return ResolveTaskLoadResult(
        task_markdown, sizes, ladder_keys, deps.classify_task_fn(task_markdown),
        exclude, excluded_reasons, candidates, top_n_keys, routes)


def _emit_quota_exhausted(deps: CliDeps, ctx: QuotaExhaustionEmitContext) -> None:
    deps.stdout.write(json.dumps(_merged_quota_exhaustion_payload(deps, ctx)))


def _quota_emit_from_loaded(
    loaded: ResolveTaskLoadResult, tried: list, reasons: dict,
) -> QuotaExhaustionEmitContext:
    return QuotaExhaustionEmitContext(
        loaded.task_type, loaded.ladder_keys, loaded.exclude, loaded.excluded_reasons,
        tried, reasons)


def _run_resolve_injection_build(deps: CliDeps, inputs: ResolveInjectionRunInputs) -> int:
    loaded = inputs.loaded
    existing_quota = deps.cache_read_json_fn(inputs.args.quota_path) or {}
    quota = _refresh_quota_for_candidates(
        deps, inputs.args.quota_path, loaded.candidates, existing_quota, loaded.routes)
    request = BuildInjectionRequest(
        loaded.task_markdown, loaded.candidates, loaded.sizes, {}, loaded.top_n_keys)
    try:
        result = deps.build_dispatch_injection_fn(
            request, BuildInjectionOptions(quota=quota, routes=loaded.routes))
        result["ladder_keys"] = loaded.ladder_keys
        deps.stdout.write(json.dumps(result))
        return 0
    except QuotaExhaustedError as exc:
        _emit_quota_exhausted(
            deps, _quota_emit_from_loaded(loaded, exc.tried, exc.reasons))
        return 0
    except ValueError as exc:
        return _handle_build_value_error(
            exc, loaded.task_type, loaded.ladder_keys, deps)


def _cmd_resolve_injection(args: argparse.Namespace, deps: CliDeps) -> int:
    loaded = _resolve_task_inputs(args, deps)
    if isinstance(loaded, int):
        return loaded
    if not loaded.candidates:
        _emit_quota_exhausted(deps, _quota_emit_from_loaded(loaded, [], {}))
        return 0
    return _run_resolve_injection_build(deps, ResolveInjectionRunInputs(args, loaded))


def _read_report_snapshot(report_file: str) -> str | None:
    if not os.path.isfile(report_file):
        return None
    with open(report_file, encoding="utf-8") as f:
        return f.read()


def _write_report_fallback(args: argparse.Namespace, fallback_content: str) -> None:
    if args.report_mode == "append":
        with open(args.report_file, "a", encoding="utf-8") as f:
            f.write("\n\n---\n\nFix round dispatch (mode=external_cli):\n\n")
            f.write(fallback_content)
    else:
        with open(args.report_file, "w", encoding="utf-8") as f:
            f.write(fallback_content)


def _codegraph_registered_for_cli(cli_name: str, target_dir: str, deps: CliDeps) -> bool:
    probe = deps.probe_codegraph_fn(cli_name)
    if probe.install_command:
        print(f"ai-kit-spec-execute-superpowers: codegraph MCP is not registered or not "
              f"healthy for {cli_name}; install it with: {probe.install_command}",
              file=sys.stderr)
    # D-20 (amended RUN-34): index when codegraph is registered and not known unhealthy;
    # codex exposes no health, so it is indexed with its health reported as unknown.
    if probe.registered is not True or probe.healthy is False:
        return False
    if probe.healthy is None:
        print(f"ai-kit-spec-execute-superpowers: codegraph MCP health for {cli_name} is unknown "
              f"({probe.detail}); indexing anyway", file=sys.stderr)
    return deps.run_codegraph_index_fn(target_dir)


def _load_dispatch_task_files(args: argparse.Namespace) -> tuple[dict, str, str]:
    injection = json.loads(args.injection_json)
    if injection.get("mode") != "external_cli":
        raise ValueError(
            f"dispatch-task only handles mode='external_cli' injections, got "
            f"mode={injection.get('mode')!r}; a native injection dispatches via the "
            f"Agent tool directly, never through this CLI subprocess path")
    with open(args.prompt_file, encoding="utf-8") as f:
        prompt = f.read()
    with open(args.format_block_file, encoding="utf-8") as f:
        format_block = f.read()
    return injection, prompt, format_block


def _dispatch_guidance_for_cli(
    deps: CliDeps, args: argparse.Namespace, injection: dict, format_block: str,
) -> SuperpowersDispatchGuidance:
    return SuperpowersDispatchGuidance(
        format_block=format_block,
        tool_availability=deps.detect_tool_availability_fn(),
        agents_tooling_path=deps.resolve_agents_tooling_path_fn(),
        codegraph_registered=_codegraph_registered_for_cli(
            injection["runtime"], args.target_dir, deps),
    )


def _maybe_write_report_fallback(
    args: argparse.Namespace, result: dict, report_before: str | None,
) -> None:
    report_after = _read_report_snapshot(args.report_file)
    if report_after is not None and report_after != report_before:
        return
    _write_report_fallback(args, _REPORT_FALLBACK_MARKER + result.get("stdout", ""))


def _cmd_dispatch_task(args: argparse.Namespace, deps: CliDeps) -> int:
    injection, prompt, format_block = _load_dispatch_task_files(args)
    report_before = _read_report_snapshot(args.report_file)
    guidance = _dispatch_guidance_for_cli(deps, args, injection, format_block)
    dispatch_request = DispatchTaskRequest(
        injection, prompt, args.target_dir, args.heartbeat_interval, args.timeout)
    result = deps.dispatch_superpowers_task_fn(dispatch_request, guidance=guidance)
    _maybe_write_report_fallback(args, result, report_before)
    deps.stdout.write(json.dumps(result))
    return 0


def _cmd_classify_dispatch_failure(args: argparse.Namespace, deps: CliDeps) -> int:
    result = json.loads(args.dispatch_result_json)
    deps.stdout.write(deps.classify_dispatch_failure_fn(result))
    return 0


def _cmd_resume_exclusions(args: argparse.Namespace, deps: CliDeps) -> int:
    result = deps.compute_resume_exclusions_fn(
        json.loads(args.tried_json), json.loads(args.reasons_json),
        json.loads(args.prior_excluded_keys_json))
    deps.stdout.write(json.dumps(result))
    return 0


def _cmd_write_resumable_state(args: argparse.Namespace, deps: CliDeps) -> int:
    state = json.loads(args.state_json)
    deps.write_resumable_state_fn(args.path, state)
    deps.stdout.write(json.dumps({"written": True, "path": args.path}))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-kit-spec-execute-superpowers")
    sub = parser.add_subparsers(dest="command", required=True)

    p_resolve = sub.add_parser("resolve-injection")
    p_resolve.add_argument("--cwd", required=True)
    p_resolve.add_argument("--task-file", required=True,
                            help="path to this task's own brief file (task-N-brief.md, per "
                                 "subagent-driven-development's own scripts/task-brief) -- read "
                                 "verbatim as task_markdown; files_touched_sizes is derived from "
                                 "this SAME file's own **Files:** block, stat'd against --cwd -- "
                                 "never a caller-supplied manual map (CRITICAL finding)")
    p_resolve.add_argument("--quota-path", required=True)
    p_resolve.add_argument("--exclude-keys-json", default="[]",
                            help="candidate keys to drop before resolution -- e.g. a key already "
                                 "confirmed quota-exhausted earlier in the same wave")
    p_resolve.add_argument(
        "--excluded-reasons-json", default="{}",
        help="CRITICAL finding, recurrence guard: a {key: reason} map for every key already in "
             "--exclude-keys-json, carried forward from this wave's own accumulated "
             "$WAVE_REASONS_JSON (Task 4's SKILL.md). Without this, a re-resolution call cannot "
             "recover WHY an already-excluded candidate failed -- neither to report a real "
             "quota_exhausted outcome when every candidate is already excluded (this call's own "
             "walk never starts, so it has no reasons of its own to report) nor to fold an "
             "earlier candidate's real reason into any_quota_recoverable when THIS call's own "
             "QuotaExhaustedError only carries the (narrower) set its own walk actually visited")
    p_resolve.add_argument(
        "--escalation-excluded-keys-json", default="[]",
        help="HIGH finding, recurrence guard: candidate keys dropped from consideration for "
             "Rounds 4-5 capability-escalation reasons ONLY (Task 4's SKILL.md ESCALATION_"
             "EXCLUDE_JSON) -- ranked at-or-below a stuck candidate's own ladder position, never "
             "themselves tried or failed. Kept in a channel separate from --exclude-keys-json/"
             "--excluded-reasons-json on purpose: these keys narrow candidate selection exactly "
             "like --exclude-keys-json does, but never enter `tried`/`reasons` and never receive "
             "the 'no_usable_dispatch' permanent-reason fallback -- a healthy, never-attempted "
             "candidate excluded only to enforce a capability floor must never be reported to the "
             "user as needing a fix, and must never be carried into resume-exclusions' persisted "
             "excluded_keys set as if it had genuinely failed.")

    p_dispatch = sub.add_parser("dispatch-task")
    p_dispatch.add_argument("--injection-json", required=True)
    p_dispatch.add_argument("--prompt-file", required=True)
    p_dispatch.add_argument("--target-dir", required=True)
    p_dispatch.add_argument("--heartbeat-interval", type=int, required=True)
    p_dispatch.add_argument("--timeout", type=int, required=True)
    p_dispatch.add_argument("--format-block-file", required=True)
    p_dispatch.add_argument(
        "--report-file", required=True,
        help="the same path subagent-driven-development's own task-brief-named report file "
             "convention expects. The dispatched CLI is instructed (via the prompt) to write its "
             "OWN detailed report directly here -- if it does, this command never touches the "
             "file. Only if it provably didn't (CRITICAL finding, recurrence guard) does this "
             "command fall back to writing/appending the captured stdout, clearly labeled.")
    p_dispatch.add_argument(
        "--report-mode", choices=["write", "append"], default="write",
        help="'write' (default) for the task's FIRST dispatch -- nothing to preserve yet. "
             "'append' for every fix-loop round -- CRITICAL finding: overwriting the report file "
             "on a fix round destroys the implementer-authored report (and any earlier rounds' "
             "evidence) subagent-driven-development's own task review / re-review reads as the "
             "task's persistent memory.")

    p_classify = sub.add_parser("classify-dispatch-failure")
    p_classify.add_argument("--dispatch-result-json", required=True)

    p_resume_excl = sub.add_parser(
        "resume-exclusions",
        help="CRITICAL finding, recurrence guard: computes the exclusion set safe to PERSIST "
             "into resumable state -- a genuinely time-bound quota reason is dropped, so a later "
             "resume (after quota recovers) can retry that candidate; only permanent reasons "
             "(auth/timeout/configuration/dispatch_unavailable/no_usable_dispatch/real_error) "
             "are kept.")
    p_resume_excl.add_argument("--tried-json", required=True)
    p_resume_excl.add_argument("--reasons-json", required=True)
    p_resume_excl.add_argument("--prior-excluded-keys-json", required=True)

    p_resume = sub.add_parser("write-resumable-state")
    p_resume.add_argument("--path", required=True)
    p_resume.add_argument("--state-json", required=True)

    return parser


_COMMANDS = {
    "resolve-injection": _cmd_resolve_injection,
    "dispatch-task": _cmd_dispatch_task,
    "classify-dispatch-failure": _cmd_classify_dispatch_failure,
    "resume-exclusions": _cmd_resume_exclusions,
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
        print(f"ai-kit-spec-execute-superpowers: config error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
