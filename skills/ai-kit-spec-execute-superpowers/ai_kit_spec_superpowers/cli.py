"""CLI entrypoint for ai-kit-spec-execute-superpowers -- invoked via the ai-kit-spec-superpowers.py
shim. Mirrors the GSD flow's own CLI subcommand pattern (Plan 2) so Task 4's SKILL.md gives an
executing agent one concrete, runnable command for every operation: resolve-injection (live-quota
candidate resolution), dispatch-task (the actual write-capable dispatch, which preserves an
implementer-authored report file rather than overwriting it with stdout -- CRITICAL finding),
classify-dispatch-failure, implementer-status (the status the reply declares on a line of its own),
runner-facts (the runner's status, findings and coverage from a dispatch result),
resume-exclusions (computes what's safe to PERSIST as a resumable-state exclusion set without
permanently excluding a merely quota-exhausted candidate -- CRITICAL finding),
write-resumable-state. There is no native dispatch subcommand -- that mode is dispatched in-process
via the Agent tool, by Task 4's SKILL.md directly, never subprocess-invoked here (same
native/cross-AI split the GSD flow's CLI already uses). No separate prepare-tooling subcommand
either (removed a prior revision, CRITICAL finding) -- dispatch-task already computes and passes
tooling guidance inputs itself; a standalone subcommand whose output nothing read was dead code
invoking a subcommand that never actually existed."""
import argparse
import contextlib
import functools
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple, TextIO

from ai_kit_spec import (
    capability_block,
    executor_pick,
    herdr_pane,
    host_config,
    lane_switch,
    lane_transport,
    prompt_guard,
    routing,
    runner_dispatch,
)
from ai_kit_spec.cache import cache_read_json, cache_write_json, cache_write_text
from ai_kit_spec.config_io import ConfigError, cfg_resolve_quiet
from ai_kit_spec.detection import (
    CBM_NAME,
    LOOPBACK_URLOPEN,
    cache_runtimes_path,
    check_cbm_registered,
    detect_current_runtime,
    detect_tool_availability,
    resolve_agents_tooling_path,
    run_cbm_index,
    runtime_id,
)
from ai_kit_spec.dispatch_guidance import (
    build_commit_guard_guidance,
    build_gates_guidance,
    checked_owner_config_paths,
)
from ai_kit_spec.execute_dispatch import ExecuteSeams, dispatch_execute
from ai_kit_spec.execute_selection import ExecuteSelectionError
from ai_kit_spec.lane_settings import LaneSettingError
from ai_kit_spec.model_catalog import cache_catalog_path, split_catalog_meta
from ai_kit_spec.quota import QUOTA_TTL_SECONDS, refresh_quota_cache
from ai_kit_spec.routing import (
    RuntimesSeams,
    host_context,
    probe_keys,
    route_all,
    unroutable_quota,
)

from ai_kit_spec_superpowers.dispatch_injection import (
    NO_CANDIDATE_PREFIX,
    BuildInjectionOptions,
    BuildInjectionRequest,
    DispatchTaskRequest,
    QuotaExhaustedError,
    SuperpowersDispatchGuidance,
    SuperpowersDispatchSeams,
    assemble_candidates,
    build_dispatch_injection,
    compute_ladder_keys,
    compute_resume_exclusions,
    derive_files_touched_sizes,
    dispatch_classification,
    dispatch_superpowers_task,
    escalation_gate,
    implementer_status,
    quota_evidence,
    reasons_summary,
    session_fallback_injection,
)
from ai_kit_spec_superpowers.task_classification import classify_task

_REPORT_FALLBACK_MARKER = (
    "[ai-kit-spec-execute-superpowers: no report file was written by the dispatched CLI -- "
    "falling back to captured stdout]\n\n"
)


_GATE_STOP = ("ai-kit-spec: STOP: empty or unknown ESCALATION_ANCHOR_KEY; "
              "ask the owner, do not resolve")
_FALLBACK_ON = ("ai-kit-spec: no execute lane is available; this task runs on the session model "
                "({note})")
_FALLBACK_OFF = ("ai-kit-spec: no execute lane is available; run ai-kit-spec-config to add one "
                 "or to turn on the session-model fallback")
_GATE_NOTES = {
    "off": "escalation is off for this lane",
    "no-target": "no lane above it matches the lane's escalation flags",
}

_LITE_REL = os.path.join(".aikit", "brief", "lite-executor.md")
_LITE_REF = Path(__file__).resolve().parents[1] / "references" / "lite-block.md"
_LITE_START = "<!-- lite-block:start -->"
_LITE_END = "<!-- lite-block:end -->"


class CliDeps(NamedTuple):
    assemble_candidates_fn: Callable[..., tuple] = assemble_candidates
    build_dispatch_injection_fn: Callable[..., dict] = build_dispatch_injection
    derive_files_touched_sizes_fn: Callable[..., dict] = derive_files_touched_sizes
    compute_ladder_keys_fn: Callable[..., list] = compute_ladder_keys
    reasons_summary_fn: Callable[[dict], dict] = reasons_summary
    classify_task_fn: Callable[[str], str | None] = classify_task
    dispatch_superpowers_task_fn: Callable[..., dict] = dispatch_superpowers_task
    classify_dispatch_failure_fn: Callable[[dict], dict] = dispatch_classification
    compute_resume_exclusions_fn: Callable[..., list] = compute_resume_exclusions
    cache_read_json_fn: Callable[[str], Any] = cache_read_json
    cache_write_json_fn: Callable[[str, Any], None] = cache_write_json
    refresh_quota_cache_fn: Callable[..., dict] = refresh_quota_cache
    detect_tool_availability_fn: Callable[[], dict] = detect_tool_availability
    resolve_agents_tooling_path_fn: Callable[[], str | None] = resolve_agents_tooling_path
    cbm_registered_fn: Callable[[str], bool] = check_cbm_registered
    run_cbm_index_fn: Callable[[str], bool] = run_cbm_index
    write_resumable_state_fn: Callable[..., None] = cache_write_json
    route_all_fn: Callable[..., dict] = route_all
    which_fn: Callable[..., Any] = shutil.which
    run_fn: Callable[..., Any] = subprocess.run
    popen_fn: Callable[..., Any] = subprocess.Popen
    urlopen_fn: Callable[..., Any] = LOOPBACK_URLOPEN
    env_fn: Callable[[], dict] = lambda: dict(os.environ)
    stdout: TextIO = sys.stdout
    pick_executor_fn: Callable[..., Any] = executor_pick.pick_executor
    clock_fn: Callable[[], float] = time.time
    close_pane_fn: Callable[..., Any] = herdr_pane.close_pane
    run_sweep_fn: Callable[..., Any] = runner_dispatch.run_sweep


class QuotaExhaustionEmitContext(NamedTuple):
    task_type: str | None
    ladder_keys: list
    exclude: set[str]
    excluded_reasons: dict
    tried: list
    reasons: dict
    escalation_exclude: frozenset[str] = frozenset()


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
    escalation_exclude: frozenset[str] = frozenset()


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
    # Recoverability counts only keys this call could still pick: a stale reason for a key outside
    # the walk, or a key below the Rounds 4-5 floor, must never schedule a wake.
    eligible = set(merged_tried) - ctx.escalation_exclude
    summary = deps.reasons_summary_fn(
        {k: r for k, r in merged_reasons.items() if k in eligible})
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
        if isinstance(exc, ExecuteSelectionError):
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
    if str(exc).startswith(NO_CANDIDATE_PREFIX):
        deps.stdout.write(json.dumps({
            "mode": "no_candidate", "task_type": task_type, "detail": str(exc),
            "ladder_keys": ladder_keys,
        }))
        return 0
    if isinstance(exc, ExecuteSelectionError):
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
        exclude, excluded_reasons, candidates, top_n_keys, routes, frozenset(escalation_exclude))


def _emit_quota_exhausted(deps: CliDeps, ctx: QuotaExhaustionEmitContext) -> None:
    deps.stdout.write(json.dumps(_merged_quota_exhaustion_payload(deps, ctx)))


def _quota_emit_from_loaded(
    loaded: ResolveTaskLoadResult, tried: list, reasons: dict,
) -> QuotaExhaustionEmitContext:
    return QuotaExhaustionEmitContext(
        loaded.task_type, loaded.ladder_keys, loaded.exclude, loaded.excluded_reasons,
        tried, reasons, loaded.escalation_exclude)


def _emit_or_fallback(
    deps: CliDeps, args: argparse.Namespace, loaded: ResolveTaskLoadResult,
    emit: Callable[[], object],
) -> int:
    """Print today's no-lane output, or the session-model injection when the owner turned the
    fallback on. Only a plain resolution may fall back: a fix round of 4 or more, escalation keys
    or --no-fallback print today's output with no config read and no jev call."""
    if args.no_fallback or args.fix_round >= 4 or loaded.escalation_exclude:
        emit()
        return 0
    summary = (f"Task type: {loaded.task_type or 'unknown'}. Files named: {len(loaded.sizes)}. "
               f"Fix round: {args.fix_round}.")
    try:
        injection = session_fallback_injection(
            cfg_resolve_quiet(args.cwd, deps.env_fn()), loaded.ladder_keys, summary,
            deps.env_fn(), functools.partial(deps.run_fn, cwd=args.cwd))
    except LaneSettingError as exc:
        print(f"ai-kit-spec: {exc}", file=sys.stderr)
        return 2
    if injection is not None:
        deps.stdout.write(json.dumps(injection))
        print(_FALLBACK_ON.format(note=injection["fallback_note"]), file=sys.stderr)
        return 0
    emit()
    print(_FALLBACK_OFF, file=sys.stderr)
    return 0


def _blocked_pool_quota(
    deps: CliDeps, loaded: ResolveTaskLoadResult, request: BuildInjectionRequest,
    existing_quota: dict,
) -> dict:
    """Stamp a ranked, eligible, spawned flagged lane whose pool is still blocked; an expired pool
    is retried by its first such lane. The keys come from the same narrowing the final pick uses,
    run on the remaining candidates; excluded and native lanes never take part."""
    try:
        keys = deps.compute_ladder_keys_fn(request, loaded.routes)
    except ValueError:
        return existing_quota
    by_key = {c["key"]: c for c in loaded.candidates}
    ranked = probe_keys([k for k in keys if k in by_key], loaded.routes)
    lanes = [by_key[k]["roster_entry"] for k in ranked
             if isinstance(by_key[k].get("roster_entry"), dict)]
    return lane_switch.blocked_cache_entries(
        lanes, ranked, existing_quota, deps.clock_fn(), lane_switch.blocked_reader(deps))


def _catalog_entries(deps: CliDeps) -> dict:
    """The model catalog's entries; an unreadable cache reads as none."""
    return split_catalog_meta(deps.cache_read_json_fn(cache_catalog_path(deps.env_fn())))[0]


def _pick_fn_for(
    deps: CliDeps, args: argparse.Namespace, loaded: ResolveTaskLoadResult,
) -> Callable[[list], executor_pick.Pick] | None:
    """jev's executor pick, built only for a plain first resolution."""
    if args.fix_round != 0 or loaded.escalation_exclude:
        return None

    def pick(eligible: list) -> executor_pick.Pick:
        labels = executor_pick.candidate_labels(
            eligible, loaded.routes, loaded.task_type, _catalog_entries(deps))
        return deps.pick_executor_fn(
            eligible, labels, deps.env_fn(), functools.partial(deps.run_fn, cwd=args.cwd))
    return pick


def _lite_text() -> str:
    """The block between the markers of references/lite-block.md."""
    text = _LITE_REF.read_text(encoding="utf-8")
    block = text.split(_LITE_START, 1)[1].split(_LITE_END, 1)[0]
    return block.strip("\n") + "\n"


def _cached_routes(deps: CliDeps, candidates: list) -> dict:
    """Exec routes from the cached runtimes snapshot only: no host probe and no cache write."""
    env = deps.env_fn()
    inventory = routing.inventory_from_snapshot(
        deps.cache_read_json_fn(cache_runtimes_path(env)))
    host = detect_current_runtime(env)
    return {c["key"]: routing.route(routing.RouteInput.of(c), host, "exec", inventory)
            for c in candidates}


def _brief_inside(cwd: str) -> bool:
    """True when <cwd>/.aikit/brief resolves inside the resolved cwd (symlinks followed)."""
    root = os.path.realpath(cwd)
    return os.path.commonpath(
        [root, os.path.realpath(os.path.join(cwd, ".aikit", "brief"))]) == root


def _cmd_lite_block(args: argparse.Namespace, deps: CliDeps) -> int:
    """Write the lite block beside the plan-writer brief when the executor that will run is lite."""
    if not _brief_inside(args.cwd):
        print("ai-kit-spec: lite-block: brief folder outside the project", file=sys.stderr)
        return 2
    candidates, top_n_keys = deps.assemble_candidates_fn(
        args.cwd, deps.env_fn(), cfg_resolve_fn=cfg_resolve_quiet)
    order = {k: i for i, k in enumerate(top_n_keys)}
    routes = _cached_routes(deps, candidates)
    ranked = sorted((c for c in candidates if routes[c["key"]] not in routing.SKIP_ROUTES),
                    key=lambda c: order.get(c["key"], len(order)))
    entries = _catalog_entries(deps)
    labels = executor_pick.candidate_labels(ranked, routes, "plan", entries)
    pick = deps.pick_executor_fn(ranked, labels, deps.env_fn(),
                                 functools.partial(deps.run_fn, cwd=args.cwd))
    # no jev pick: the default order decides, so its first lane is the executor that will run
    picked = next((c for c in ranked if c["key"] == pick.key), ranked[0] if ranked else None)
    lite = picked is not None and executor_pick.is_lite(entries, picked)
    path = os.path.join(args.cwd, _LITE_REL)
    removed = False
    try:
        if lite:
            cache_write_text(path, _lite_text())
        elif os.path.exists(path):
            os.remove(path)
            removed = True
    except OSError:
        print(f"ai-kit-spec: lite-block: cannot write {path}", file=sys.stderr)
        return 2
    deps.stdout.write(json.dumps({
        "lite": lite, "key": picked["key"] if picked else None, "decided_by": pick.decided_by,
        "path": path if lite else None, "removed_stale": removed}))
    return 0


def _run_resolve_injection_build(deps: CliDeps, inputs: ResolveInjectionRunInputs) -> int:
    loaded = inputs.loaded
    request = BuildInjectionRequest(
        loaded.task_markdown, loaded.candidates, loaded.sizes, {}, loaded.top_n_keys)
    existing_quota = _blocked_pool_quota(
        deps, loaded, request, deps.cache_read_json_fn(inputs.args.quota_path) or {})
    quota = _refresh_quota_for_candidates(
        deps, inputs.args.quota_path, loaded.candidates, existing_quota, loaded.routes)
    try:
        result = deps.build_dispatch_injection_fn(
            request, BuildInjectionOptions(quota=quota, routes=loaded.routes,
                                           pick_fn=_pick_fn_for(deps, inputs.args, loaded)))
        result["ladder_keys"] = loaded.ladder_keys
        deps.stdout.write(json.dumps(result))
        return 0
    except QuotaExhaustedError as exc:
        return _emit_or_fallback(
            deps, inputs.args, loaded,
            functools.partial(
                _emit_quota_exhausted, deps,
                _quota_emit_from_loaded(loaded, exc.tried, exc.reasons)))
    except ValueError as exc:
        # narrowing left no lane (no_candidate): the owner's curation stop, never the fallback
        return _handle_build_value_error(
            exc, loaded.task_type, loaded.ladder_keys, deps)


def _cmd_resolve_injection(args: argparse.Namespace, deps: CliDeps) -> int:
    loaded = _resolve_task_inputs(args, deps)
    if isinstance(loaded, int):
        return loaded
    if not loaded.candidates:
        return _emit_or_fallback(
            deps, args, loaded,
            lambda: _emit_quota_exhausted(deps, _quota_emit_from_loaded(loaded, [], {})))
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


def _code_index_registered_for_cli(cli_name: str, target_dir: str, deps: CliDeps) -> bool:
    """D-20 (amended RUN-34, Phase 32.5): when the lane's host config registers
    codebase-memory-mcp, index the target with one index_repository call; return the
    registration. A failed index is reported on stderr and never reads as missing registration;
    with no binary on PATH there is nothing to run, so no index and no stderr line."""
    if not deps.cbm_registered_fn(cli_name):
        return False
    if deps.which_fn(CBM_NAME) is None:
        return True
    if not deps.run_cbm_index_fn(target_dir):
        print(f"codebase-memory-mcp: pre-dispatch index_repository failed in {target_dir}; "
              "the lane may find a missing or stale index", file=sys.stderr)
    return True


def _load_dispatch_task_files(args: argparse.Namespace) -> tuple[dict, str, str]:
    injection = json.loads(args.injection_json)
    if injection.get("mode") != "external_cli":
        raise ValueError(
            f"dispatch-task only handles mode='external_cli' injections, got "
            f"mode={injection.get('mode')!r}; a native injection dispatches via the "
            f"Agent tool directly, never through this CLI subprocess path")
    if "runtime" not in injection and "cli" in injection:  # a pre-18.1 injection (B-IN-05)
        injection["runtime"] = runtime_id(injection.pop("cli"))
    with open(args.prompt_file, encoding="utf-8") as f:
        prompt = f.read()
    with open(args.format_block_file, encoding="utf-8") as f:
        format_block = f.read()
    return injection, prompt, format_block


def _read_optional(flag: str, path: str | None) -> str | None:
    """The text of an optional guidance file; an explicit file that cannot be read is an error,
    never an empty block."""
    if path is None:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"ai-kit-spec: {flag}: unreadable file {path}") from exc


def _guidance_inputs(args: argparse.Namespace) -> tuple:
    return (
        _read_optional("--gates-file", args.gates_file),
        _read_optional("--guard-file", args.guard_file),
        checked_owner_config_paths(args.owner_config),
    )


def _dispatch_guidance_for_cli(
    deps: CliDeps, args: argparse.Namespace, injection: dict, format_block: str,
    inputs: tuple,
) -> SuperpowersDispatchGuidance:
    return SuperpowersDispatchGuidance(
        format_block=format_block,
        tool_availability=deps.detect_tool_availability_fn(),
        agents_tooling_path=deps.resolve_agents_tooling_path_fn(),
        code_index_registered=_code_index_registered_for_cli(
            injection["runtime"], args.target_dir, deps),
        gates_text=inputs[0],
        guard_text=inputs[1],
        owner_config_paths=inputs[2],
    )


def _maybe_write_report_fallback(
    args: argparse.Namespace, result: dict, report_before: str | None,
) -> None:
    report_after = _read_report_snapshot(args.report_file)
    if report_after is not None and report_after != report_before:
        return
    _write_report_fallback(args, _REPORT_FALLBACK_MARKER + result.get("stdout", ""))


def _task_round_start(args: argparse.Namespace, deps: CliDeps, injection: dict) -> tuple | None:
    """The lane's transport round for a --transport-record dispatch: the roster row whose key,
    runtime and model match the injection exactly, chosen under the record's lock. None (and no
    roster read) when no record path was given; None too when the roster holds no exact row, so
    the call runs today's fresh-subprocess path with no record write. A record file that
    cannot be used prints one stderr line and returns None."""
    if args.transport_record is None:
        return None
    try:
        lanes, _ = deps.assemble_candidates_fn(
            args.target_dir, deps.env_fn(), cfg_resolve_fn=cfg_resolve_quiet)
    except ConfigError:
        lanes = []
    for index, candidate in enumerate(lanes):
        row = candidate["roster_entry"]
        if candidate["key"] != injection.get("key") \
                or row.get("runtime") != injection.get("runtime") \
                or row.get("model") != injection.get("model"):
            continue
        entry = {**row, "runtime": injection.get("runtime"), "model": injection.get("model")}
        start = lane_transport.RoundStart(
            args.transport_record,
            lane_transport.lane_request("execute", index, entry, deps.env_fn(),
                                        deps.which_fn),
            os.getpid())
        choice = lane_transport.try_begin_round(start)
        return None if choice is None else (start, choice)
    return None


def _task_pane_runner(start, target_dir: str):
    """The pane runner for one execute round: one tier, the request's own timeout."""
    def fallback(spec, tiers, prompt, seams=None):
        return runner_dispatch.run_runner(
            spec._replace(timeout_s=tiers[-1]), prompt, seams)

    return lane_transport.pane_runner(start, target_dir, "execute", fallback)


def _task_pane_kwargs(args: argparse.Namespace, round_start) -> dict:
    """seams only for a pane round, so a fake of shape (request, guidance=None) stays valid."""
    if round_start is None or round_start[1].transport != "pane":
        return {}
    runner = _task_pane_runner(round_start[0], args.target_dir)
    seams = ExecuteSeams(
        runner_fn=lambda spec, prompt, seams=None: runner(spec, [spec.timeout_s], prompt, seams))
    return {"seams": SuperpowersDispatchSeams(
        dispatch_execute_fn=functools.partial(dispatch_execute, seams=seams))}


def _cmd_dispatch_task(args: argparse.Namespace, deps: CliDeps) -> int:
    injection, prompt, format_block = _load_dispatch_task_files(args)
    try:
        inputs = _guidance_inputs(args)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    report_before = _read_report_snapshot(args.report_file)
    guidance = _dispatch_guidance_for_cli(deps, args, injection, format_block, inputs)
    round_start = _task_round_start(args, deps, injection)
    session_id = (round_start[1].session_id
                  if round_start is not None and round_start[1].transport == "resume"
                  else None)
    dispatch_request = DispatchTaskRequest(
        injection, prompt, args.target_dir, args.timeout, session_id=session_id)
    try:
        result = deps.dispatch_superpowers_task_fn(
            dispatch_request, guidance=guidance,
            **_task_pane_kwargs(args, round_start))
    except capability_block.LaneRefused as exc:
        deps.stdout.write(json.dumps({"runtime": injection.get("runtime"),
                                      "model": injection.get("model"), "command": "", "stdout": "",
                                      "returncode": prompt_guard.REFUSED_EXIT, "timed_out": False,
                                      "reason": exc.record["reason"], "status": exc.record}))
        return prompt_guard.REFUSED_EXIT
    if round_start is not None:
        lane_transport.try_end_round(round_start[0], round_start[1], result.get("status"))
    _maybe_write_report_fallback(args, result, report_before)
    deps.stdout.write(json.dumps(result))
    return 0


def _cmd_close_transports(args: argparse.Namespace, deps: CliDeps) -> int:
    """Close the plan's recorded panes and run the runner sweep once."""
    try:
        outcome = lane_transport.close_record(
            args.transport_record, deps.close_pane_fn, deps.run_sweep_fn)
    except ValueError:
        print(f"close-transports: unreadable transport record {args.transport_record}",
              file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"close-transports: cannot read transport record {args.transport_record}: {exc}",
              file=sys.stderr)
        return 2
    deps.stdout.write(json.dumps(outcome) + "\n")
    return 1 if outcome["failed"] else 0


def _cmd_print_guidance(args: argparse.Namespace, deps: CliDeps) -> int:
    """The gates and guard blocks a native dispatch puts in its brief, identical to an external
    dispatch."""
    try:
        gates_text, guard_text, paths = _guidance_inputs(args)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    blocks = [build_gates_guidance(gates_text), build_commit_guard_guidance(guard_text, paths)]
    text = "\n\n".join(b for b in blocks if b)
    if text:
        deps.stdout.write(text + "\n")
    return 0


def _cmd_classify_dispatch_failure(args: argparse.Namespace, deps: CliDeps) -> int:
    result = json.loads(args.dispatch_result_json)
    deps.stdout.write(json.dumps(deps.classify_dispatch_failure_fn(result)))
    return 0


def _cmd_implementer_status(args: argparse.Namespace, deps: CliDeps) -> int:
    result = json.loads(args.dispatch_result_json)
    deps.stdout.write(implementer_status(result.get("stdout") or ""))
    return 0


def _cmd_runner_facts(args: argparse.Namespace, deps: CliDeps) -> int:
    """The runner's status, finding codes and coverage from a dispatch result's status line,
    one word each on one line; `-` for a missing value."""
    result = json.loads(args.dispatch_result_json)
    line = result.get("status") if isinstance(result, dict) else None
    facts = line if isinstance(line, dict) else {}
    words = ["".join(str(facts.get(key) or "").split()) or "-"
             for key in ("status", "findings", "coverage")]
    deps.stdout.write(" ".join(words) + "\n")
    return 0


def _cmd_resume_exclusions(args: argparse.Namespace, deps: CliDeps) -> int:
    result = deps.compute_resume_exclusions_fn(
        json.loads(args.tried_json), json.loads(args.reasons_json),
        json.loads(args.prior_excluded_keys_json))
    deps.stdout.write(json.dumps(result))
    return 0


_AUDIT_UNAVAILABLE = "ai-kit-spec: observation: host-config audit unavailable: {reason}"


def _is_audit_value(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return value is None or isinstance(value, int) or value == host_config.UNAVAILABLE


def _is_audit_snapshot(data: Any) -> bool:
    """True for a dict of exactly the listed paths holding an int, None or UNAVAILABLE."""
    if not isinstance(data, dict) or set(data) != set(host_config.HOST_CONFIG_FILES):
        return False
    return all(_is_audit_value(v) for v in data.values())


def _cmd_host_config_audit(args: argparse.Namespace, deps: CliDeps) -> int:
    """An observation only: always exit 0, never read a host config file."""
    env = deps.env_fn()
    if args.snapshot:
        try:
            deps.cache_write_json_fn(os.path.abspath(args.snapshot), host_config.snapshot(env))
        except OSError as exc:
            reason = f"cannot write {args.snapshot}: {exc.strerror or exc}"
            deps.stdout.write(_AUDIT_UNAVAILABLE.format(reason=reason) + "\n")
        return 0
    before = deps.cache_read_json_fn(args.compare)
    if before is None:
        reason = f"cannot read {args.compare}"
    elif not _is_audit_snapshot(before):
        reason = f"{args.compare} is not a host-config snapshot"
    else:
        after = host_config.snapshot(env)
        for line in host_config.observation_lines(
            env, host_config.changed(before, after), host_config.unavailable(before, after)
        ):
            deps.stdout.write(line + "\n")
        return 0
    deps.stdout.write(_AUDIT_UNAVAILABLE.format(reason=reason) + "\n")
    return 0


def _cmd_write_resumable_state(args: argparse.Namespace, deps: CliDeps) -> int:
    state = json.loads(args.state_json)
    deps.write_resumable_state_fn(args.path, state)
    deps.stdout.write(json.dumps({"written": True, "path": args.path}))
    return 0


def _read_json_input(deps: CliDeps, command: str, flag: str, path: str, valid) -> Any:
    """The file's JSON when `valid` accepts it; else None after one stderr line naming the
    command, the flag and the file."""
    data = deps.cache_read_json_fn(path)
    if data is None or not valid(data):
        print(f"ai-kit-spec: {command}: unreadable {flag} {path}", file=sys.stderr)
        return None
    return data


def _is_str_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(k, str) for k in value)


def _is_injection(value: Any) -> bool:
    return isinstance(value, dict) and _is_str_list(value.get("ladder_keys"))


def _write_gate_files(out_dir: str, gate: dict) -> str | None:
    """Write both gate files under temporary names, then rename them; on a failure remove both
    temporary names and both gate files, so no mixed or stale pair is left. The path that
    failed, or None."""
    pairs = [(os.path.join(out_dir, "ESCALATION_EXCLUDE_JSON.json"), gate["exclude"]),
             (os.path.join(out_dir, "ESCALATION_ALLOWED_JSON.json"), gate["allowed"])]
    current = out_dir
    try:
        for path, value in pairs:
            current = path + ".tmp"
            with open(current, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(value))
        for path, _value in pairs:
            current = path
            os.replace(path + ".tmp", path)
    except OSError:
        for path, _value in pairs:
            for leftover in (path + ".tmp", path):
                with contextlib.suppress(OSError):
                    os.remove(leftover)
        return current
    return None


def _cmd_escalation_gate(args: argparse.Namespace, deps: CliDeps) -> int:
    injection = _read_json_input(deps, "escalation-gate", "--injection-file",
                                 args.injection_file, _is_injection)
    if injection is None:
        return 2
    ladder_keys = injection["ladder_keys"]
    lanes = cfg_resolve_quiet(args.cwd, deps.env_fn()).get("execute", [])
    try:
        gate = escalation_gate(lanes, args.anchor_key, ladder_keys)
    except LaneSettingError as exc:
        print(f"ai-kit-spec: {exc}", file=sys.stderr)
        return 2
    except ValueError:
        print(_GATE_STOP, file=sys.stderr)
        return 3
    failed = _write_gate_files(args.out_dir, gate)
    if failed is not None:
        print(f"ai-kit-spec: escalation-gate: cannot write {failed}", file=sys.stderr)
        return 2
    deps.stdout.write(json.dumps(gate))
    if not gate["escalate"]:
        print(f"ai-kit-spec: fix round stays on {args.anchor_key}: "
              f"{_GATE_NOTES[gate['reason']]}", file=sys.stderr)
    return 0


def _load_fallback_inputs(args: argparse.Namespace, deps: CliDeps) -> list | None:
    """(dispatch result, excluded keys, injection), or None after the stderr text."""
    reads = [(args.dispatch_result, "--dispatch-result", lambda v: isinstance(v, dict))]
    reads += [(path, "--exclude-keys-file", _is_str_list) for path in args.exclude_keys_file]
    reads.append((args.injection_file, "--injection-file", _is_injection))
    loaded = []
    for path, flag, valid in reads:
        data = _read_json_input(deps, "executor-fallback", flag, path, valid)
        if data is None:
            return None
        loaded.append(data)
    return [loaded[0], [key for keys in loaded[1:-1] for key in keys], loaded[-1]]


def _execute_roster(config: dict) -> list:
    return [lane for lane in config.get("execute", []) if isinstance(lane, dict)]


def _cmd_executor_fallback(args: argparse.Namespace, deps: CliDeps) -> int:
    loaded = _load_fallback_inputs(args, deps)
    if loaded is None:
        return 2
    result, exclude_keys, injection = loaded
    config = cfg_resolve_quiet(args.cwd, deps.env_fn())
    held = set(injection["ladder_keys"])
    exclude = set(exclude_keys) | {
        lane.get("key") for lane in _execute_roster(config) if lane.get("key") not in held}
    route = lane_switch.lazy_routes(
        config, deps, routes_fn=lambda cfg, d: _routes_for(d, _execute_roster(cfg)))
    new, why = lane_switch.fallback_outcome(config, args.key, quota_evidence(result), exclude,
                                            route)
    if new:
        deps.stdout.write(json.dumps({"switched": True, "key": new,
                                      "exclude": sorted(held - {new})}))
        return 0
    deps.stdout.write(json.dumps({"switched": False, "reason": why}))
    return 1


def _add_guidance_args(parser) -> None:
    parser.add_argument(
        "--gates-file", default=None,
        help="file of gate commands the implementer must run; framed once in the guidance")
    parser.add_argument(
        "--guard-file", default=None,
        help="file of commit-guard rules; framed once in the guidance")
    parser.add_argument(
        "--owner-config", action="append", default=None,
        help="an owner config path the implementer is told never to stage and to leave out of "
             "clean-tree checks; repeatable")


def _add_fallback_parser(sub) -> None:
    p_fallback = sub.add_parser(
        "executor-fallback",
        help="after a quota stop proven by the runner result, move a lane the owner flagged "
             "usage_limited to its configured fallback; other lanes and transient failures are "
             "not switched")
    p_fallback.add_argument("--cwd", required=True)
    p_fallback.add_argument("--key", required=True)
    p_fallback.add_argument("--dispatch-result", required=True,
                            help="the saved dispatch result JSON file")
    p_fallback.add_argument("--exclude-keys-file", required=True, action="append",
                            help="repeatable: the task's EXCLUDED_KEYS_JSON.json and, at fix "
                                 "rounds 4-5, the escalation gate's ESCALATION_EXCLUDE_JSON.json; "
                                 "every listed key is excluded")
    p_fallback.add_argument("--injection-file", required=True,
                            help="the task's saved INJECTION_JSON.json; its ladder_keys are the "
                                 "task-narrowed candidates")


def _add_result_parsers(sub) -> None:
    p_status = sub.add_parser(
        "implementer-status",
        help="the status the dispatch result's stdout declares on a line of its own, else BLOCKED")
    p_status.add_argument("--dispatch-result-json", required=True)

    p_facts = sub.add_parser(
        "runner-facts",
        help="the runner's status, finding codes and coverage from a dispatch result, one line")
    p_facts.add_argument("--dispatch-result-json", required=True)


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

    p_resolve.add_argument(
        "--fix-round", type=int, default=0,
        help="the task's fix round; at 4 or more the session-model fallback is never used")
    p_resolve.add_argument(
        "--no-fallback", action="store_true",
        help="never use the owner's session-model fallback in this call; the escalation re-run "
             "block passes it")

    p_dispatch = sub.add_parser("dispatch-task")
    p_dispatch.add_argument("--injection-json", required=True)
    p_dispatch.add_argument("--prompt-file", required=True)
    p_dispatch.add_argument("--target-dir", required=True)
    p_dispatch.add_argument("--heartbeat-interval", type=int, required=True)
    p_dispatch.add_argument("--timeout", type=int, required=True)
    p_dispatch.add_argument("--format-block-file", required=True)
    _add_guidance_args(p_dispatch)
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
    p_dispatch.add_argument(
        "--transport-record", default=None,
        help="the plan's lane-transport record; absent means one fresh subprocess call")

    p_close = sub.add_parser(
        "close-transports",
        help="close the plan's recorded panes and run the runner sweep once")
    p_close.add_argument("--transport-record", required=True)

    p_guidance = sub.add_parser(
        "print-guidance",
        help="print the gates and commit-guard blocks for a native dispatch")
    _add_guidance_args(p_guidance)

    p_classify = sub.add_parser("classify-dispatch-failure")
    p_classify.add_argument("--dispatch-result-json", required=True)

    _add_result_parsers(sub)

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

    p_audit = sub.add_parser(
        "host-config-audit",
        help="snapshot or compare the modification times of the listed host-config files "
             "(an observation, never a stop)")
    audit_mode = p_audit.add_mutually_exclusive_group(required=True)
    audit_mode.add_argument("--snapshot", help="write the snapshot to this file")
    audit_mode.add_argument("--compare", help="compare against the snapshot in this file")

    p_gate = sub.add_parser(
        "escalation-gate",
        help="which keys a rounds 4-5 fix round may move to, from the stuck lane's escalation "
             "flags")
    p_gate.add_argument("--cwd", required=True)
    p_gate.add_argument("--anchor-key", required=True,
                        help="the stuck lane's key; an empty value stops with exit 3")
    p_gate.add_argument("--injection-file", required=True,
                        help="the saved INJECTION_JSON.json, never JSON text on argv")
    p_gate.add_argument("--out-dir", required=True, help="the task's run folder")

    p_lite = sub.add_parser(
        "lite-block",
        help="write the lite executor block beside the plan-writer brief when the executor pick "
             "is a lite model")
    p_lite.add_argument("--cwd", required=True)

    _add_fallback_parser(sub)

    return parser


_COMMANDS = {
    "resolve-injection": _cmd_resolve_injection,
    "dispatch-task": _cmd_dispatch_task,
    "close-transports": _cmd_close_transports,
    "print-guidance": _cmd_print_guidance,
    "classify-dispatch-failure": _cmd_classify_dispatch_failure,
    "implementer-status": _cmd_implementer_status,
    "runner-facts": _cmd_runner_facts,
    "resume-exclusions": _cmd_resume_exclusions,
    "write-resumable-state": _cmd_write_resumable_state,
    "escalation-gate": _cmd_escalation_gate,
    "executor-fallback": _cmd_executor_fallback,
    "host-config-audit": _cmd_host_config_audit,
    "lite-block": _cmd_lite_block,
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
