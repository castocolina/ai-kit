"""CLI entrypoint for ai-kit-spec-execute-superpowers -- invoked via the
ai-kit-spec-superpowers.py shim. Mirrors ai_kit_spec_gsd.cli's own subcommand pattern (Plan 2) so
Task 4's SKILL.md gives an executing agent one concrete, runnable command for every operation:
resolve-injection (live-quota candidate resolution), dispatch-task (the actual write-capable
dispatch, which preserves an implementer-authored report file rather than overwriting it with
stdout -- CRITICAL finding), classify-dispatch-failure, resume-exclusions (computes what's safe
to PERSIST as a resumable-state exclusion set without permanently excluding a merely
quota-exhausted candidate -- CRITICAL finding), write-resumable-state. There is no native_claude
dispatch subcommand -- that mode is dispatched in-process via the Agent tool, by Task 4's
SKILL.md directly, never subprocess-invoked here (same native/cross-AI split ai_kit_spec_gsd.cli
already uses). No separate prepare-tooling subcommand either (removed a prior revision, CRITICAL
finding) -- dispatch-task already computes and passes tooling guidance inputs itself; a
standalone subcommand whose output nothing read was dead code invoking a subcommand that never
actually existed."""
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

from ai_kit_spec_superpowers.dispatch_injection import (
    QuotaExhaustedError,
    assemble_candidates,
    build_dispatch_injection,
    classify_dispatch_failure,
    classify_task,
    compute_ladder_keys,
    compute_resume_exclusions,
    derive_files_touched_sizes,
    dispatch_superpowers_task,
    reasons_summary,
)

# Prefixes a fallback report so it is never mistaken for a genuine implementer-authored one
# (CRITICAL finding, recurrence guard).
_REPORT_FALLBACK_MARKER = (
    "[ai-kit-spec-execute-superpowers: no report file was written by the dispatched CLI -- "
    "falling back to captured stdout]\n\n"
)


def main(argv: list, assemble_candidates_fn=assemble_candidates,
         build_dispatch_injection_fn=build_dispatch_injection,
         derive_files_touched_sizes_fn=derive_files_touched_sizes,
         compute_ladder_keys_fn=compute_ladder_keys, reasons_summary_fn=reasons_summary,
         classify_task_fn=classify_task,
         dispatch_superpowers_task_fn=dispatch_superpowers_task,
         classify_dispatch_failure_fn=classify_dispatch_failure,
         compute_resume_exclusions_fn=compute_resume_exclusions,
         cache_read_json_fn=cache_read_json, cache_write_json_fn=cache_write_json,
         refresh_quota_cache_fn=refresh_quota_cache,
         detect_tool_availability_fn=detect_tool_availability,
         resolve_agents_tooling_path_fn=resolve_agents_tooling_path,
         ensure_codegraph_registered_fn=ensure_codegraph_registered,
         build_codegraph_index_command_fn=build_codegraph_index_command,
         run_fn=subprocess.run, write_resumable_state_fn=_write_resumable_state_default,
         stdout=sys.stdout) -> int:
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

    args = parser.parse_args(argv)

    if args.command == "resolve-injection":
        full_candidates, full_top_n_keys = assemble_candidates_fn(args.cwd, dict(os.environ))
        with open(args.task_file, encoding="utf-8") as f:
            task_markdown = f.read()
        sizes = derive_files_touched_sizes_fn(task_markdown, args.cwd)
        # CRITICAL finding (Rounds 4-5 capability escalation, incomplete ladder): ladder_keys is
        # the FULL ordered candidate-key list -- via compute_ladder_keys_fn's own narrowing/
        # ranking, never list(top_n_keys), which silently omits any candidate outside
        # policy.ladder -- computed over the FULL, pre-exclusion candidate set (never narrowed by
        # whichever keys happen to be excluded on THIS call), so Task 4's SKILL.md can compute
        # "every candidate ranked strictly above the stuck one" for a genuine capability bump,
        # including one that never appeared in policy.ladder at all.
        ladder_keys = compute_ladder_keys_fn(task_markdown, full_candidates, sizes, {},
                                              full_top_n_keys)
        task_type = classify_task_fn(task_markdown)
        excluded_reasons = json.loads(args.excluded_reasons_json)
        exclude = set(json.loads(args.exclude_keys_json))
        # HIGH finding, recurrence guard: escalation_exclude is a SEPARATE set from exclude --
        # candidates dropped purely to enforce Rounds 4-5's capability-bump floor (Task 4's
        # SKILL.md ESCALATION_EXCLUDE_JSON), never themselves tried or failed. It narrows
        # candidate selection exactly like exclude does, but -- unlike exclude -- it is never
        # merged into `tried`/`reasons` below: a healthy, never-attempted candidate excluded only
        # for ranking reasons must never be tagged "no_usable_dispatch" (a permanent-shaped
        # reason), reported to the user as needing a fix, or carried into resume-exclusions'
        # persisted excluded_keys set as if it had genuinely failed.
        escalation_exclude = set(json.loads(args.escalation_excluded_keys_json))
        all_exclude = exclude | escalation_exclude
        candidates = [c for c in full_candidates if c["key"] not in all_exclude]
        top_n_keys = [k for k in full_top_n_keys if k not in all_exclude]

        def _emit_quota_exhausted(tried, reasons):
            # CRITICAL finding, recurrence guard: merge THIS call's own findings with every
            # already-known excluded reason (excluded_reasons -- the wave's own accumulated
            # reasons for keys excluded BEFORE this call even started walking) so any_quota_
            # recoverable/all_auth_failures reflect the WHOLE wave, never just this call's own
            # narrower remaining-ladder walk (which never visits a candidate exclude already
            # dropped). Any excluded key still missing a reason after this merge (this caller
            # never supplied --excluded-reasons-json, or omitted one) falls back to
            # "no_usable_dispatch" -- a permanent-shaped reason, deliberately never "quota", so a
            # gap in the caller's own bookkeeping can never falsely look quota-recoverable.
            # HIGH finding: this loop and the `tried` union below iterate `exclude` ONLY, never
            # `escalation_exclude` -- an escalation-only key must never receive a reason (fallback
            # or otherwise) or appear in `tried` at all, since it was never actually attempted.
            merged_reasons = dict(excluded_reasons)
            merged_reasons.update(reasons)
            for key in exclude:
                merged_reasons.setdefault(key, "no_usable_dispatch")
            merged_tried = sorted(set(tried) | exclude)
            summary = reasons_summary_fn(merged_reasons)
            stdout.write(json.dumps({
                "mode": "quota_exhausted", "task_type": task_type, "tried": merged_tried,
                "reasons": merged_reasons, "all_auth_failures": summary["all_auth_failures"],
                "any_quota_recoverable": summary["any_quota_recoverable"],
                "ladder_keys": ladder_keys,
            }))

        if not candidates:
            # CRITICAL finding: every configured candidate for this task is already excluded
            # BEFORE this call's own walk even starts (a single-candidate ladder tried once, or
            # several waves' accumulated exclusions covering the whole roster -- exclude and/or
            # escalation_exclude together). Calling
            # build_dispatch_injection_fn here would raise its OWN ValueError ("no candidate
            # survived narrowing") -- the wrong exception: that one means a genuine curation gap
            # (nothing configured for this task type at all), not "we already tried everything",
            # and it is never caught below, so it would crash this whole command instead of
            # reporting the controlled quota_exhausted result the SKILL.md's own branch-on-mode
            # logic already handles.
            _emit_quota_exhausted([], {})
            return 0

        existing_quota = cache_read_json_fn(args.quota_path) or {}
        quota = refresh_quota_cache_fn(
            {"reviewers": [
                {"key": c["key"], "model": c["model"], "vendor": c["vendor"], "cli": c["cli"],
                 "command": c.get("command")} for c in candidates
            ]},
            [c["key"] for c in candidates], existing_quota, QUOTA_TTL_SECONDS)
        cache_write_json_fn(args.quota_path, quota)
        try:
            result = build_dispatch_injection_fn(task_markdown, candidates, sizes, {},
                                                   top_n_keys, quota=quota)
            result["ladder_keys"] = ladder_keys
            stdout.write(json.dumps(result))
            return 0
        except QuotaExhaustedError as exc:
            _emit_quota_exhausted(exc.tried, exc.reasons)
            return 0
        except ValueError as exc:
            # HIGH finding: `candidates` can be non-empty here (the `if not candidates` guard
            # above only catches every candidate already EXCLUDED) and build_dispatch_injection_fn
            # can still raise its own ValueError -- e.g. execute_selection.filter_by_context drops
            # every remaining candidate because this task's required_context exceeds every one of
            # their context_limit values, leaving `ranked` empty from a non-empty `candidates`.
            # That is a genuine curation gap (a config/authoring problem: nothing configured can
            # actually run this task), never a quota-availability problem -- an hourly CronCreate
            # wake would never fix it. Report it as its own, distinctly-tagged, controlled JSON
            # result instead of letting the exception propagate uncaught and crash this command
            # (which would also leave $INJECTION_JSON empty, failing Step 2's very next
            # `json.loads` call with an unrelated decode error).
            # MEDIUM finding: build_dispatch_injection_fn raises ValueError from exactly one call
            # site -- "no execute candidate survived affinity/context narrowing for ..." (its own
            # `if not ranked` guard). Every OTHER ValueError build_execute_command_fn can raise
            # ("no execute-mode builder registered for cli=...") is already caught INSIDE
            # build_dispatch_injection_fn's own _is_dispatchable check and turned into a
            # drop-and-continue, never propagated here -- so any ValueError reaching this branch
            # whose message does NOT start with the documented narrowing-failure text is a genuine
            # code defect, not a curation gap, and must not be silently reported to the SKILL.md
            # as a "nothing configured can run this task" no_candidate result. Re-raise it instead
            # so it surfaces as an uncaught crash the agent can actually diagnose.
            if not str(exc).startswith("no execute candidate survived"):
                raise
            stdout.write(json.dumps({
                "mode": "no_candidate", "task_type": task_type, "detail": str(exc),
                "ladder_keys": ladder_keys,
            }))
            return 0

    if args.command == "dispatch-task":
        injection = json.loads(args.injection_json)
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
        with open(args.format_block_file, encoding="utf-8") as f:
            format_block = f.read()
        tool_availability = detect_tool_availability_fn()
        agents_tooling_path = resolve_agents_tooling_path_fn()
        codegraph_registered = ensure_codegraph_registered_fn(injection["cli"])
        if codegraph_registered:
            index_cmd = build_codegraph_index_command_fn(args.target_dir)
            try:
                probe = run_fn(index_cmd, shell=True, capture_output=True, text=True,
                                check=False, timeout=CODEGRAPH_INDEX_TIMEOUT_SECONDS)
                if probe.returncode != 0:
                    codegraph_registered = False
            except (subprocess.TimeoutExpired, OSError):
                codegraph_registered = False
        # CRITICAL finding (recurrence guard): never blindly overwrite --report-file with
        # captured subprocess stdout. The real superpowers implementer contract has the
        # dispatched CLI write its OWN detailed report directly to this path (it has write
        # access to target_dir -- an execute-mode dispatch -- per the prompt's report-file-path
        # instruction) and return only a short status separately. Snapshot the file's content
        # BEFORE dispatching and compare AFTER: if it changed (the CLI wrote to it, appended or
        # created it), that on-disk content IS the implementer's real report -- leave it
        # completely untouched. Only fall back to stdout when the file is provably unchanged.
        report_before = None
        if os.path.isfile(args.report_file):
            with open(args.report_file, encoding="utf-8") as f:
                report_before = f.read()
        result = dispatch_superpowers_task_fn(
            injection, prompt, args.target_dir, args.heartbeat_interval, args.timeout,
            format_block=format_block, tool_availability=tool_availability,
            agents_tooling_path=agents_tooling_path, codegraph_registered=codegraph_registered)
        report_after = None
        if os.path.isfile(args.report_file):
            with open(args.report_file, encoding="utf-8") as f:
                report_after = f.read()
        implementer_wrote_report = report_after is not None and report_after != report_before
        if not implementer_wrote_report:
            fallback_content = _REPORT_FALLBACK_MARKER + result.get("stdout", "")
            if args.report_mode == "append":
                with open(args.report_file, "a", encoding="utf-8") as f:
                    f.write("\n\n---\n\nFix round dispatch (mode=external_cli):\n\n")
                    f.write(fallback_content)
            else:
                with open(args.report_file, "w", encoding="utf-8") as f:
                    f.write(fallback_content)
        stdout.write(json.dumps(result))
        return 0

    if args.command == "classify-dispatch-failure":
        result = json.loads(args.dispatch_result_json)
        stdout.write(classify_dispatch_failure_fn(result))
        return 0

    if args.command == "resume-exclusions":
        result = compute_resume_exclusions_fn(
            json.loads(args.tried_json), json.loads(args.reasons_json),
            json.loads(args.prior_excluded_keys_json))
        stdout.write(json.dumps(result))
        return 0

    if args.command == "write-resumable-state":
        state = json.loads(args.state_json)
        write_resumable_state_fn(args.path, state)
        stdout.write(json.dumps({"written": True, "path": args.path}))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
