import json
import os
import shutil
import subprocess
import sys

from ai_kit_spec.cache import cache_is_stale, cache_read_json, cache_write_json
from ai_kit_spec.commands import (
    ResolvedReviewer, build_reviewer_command, build_reviewer_model_id,
    render_reviewer_command,
)
from ai_kit_spec.config_io import cfg_render_toml, cfg_resolve, cfg_write_toml
from ai_kit_spec.detection import (
    RUNTIMES_TTL_SECONDS, build_runtimes_snapshot, cache_runtimes_path,
    detect_tool_availability, group_models_by_family,
)
from ai_kit_spec.quota import (
    QUOTA_TTL_SECONDS, cache_quota_path, probe_reviewer_quota,
    refresh_quota_cache, resolve_reviewers,
)
from ai_kit_spec.review_reports import (
    merge_findings, render_merged_report, report_declares_issues,
    report_has_status,
)
from ai_kit_spec.vendor import infer_vendor_from_model


def main(argv: list, which_fn=shutil.which, run_fn=subprocess.run) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="review-spec")
    sub = parser.add_subparsers(dest="command", required=True)

    p_cache_path = sub.add_parser("cache-path")
    p_cache_path.add_argument("--kind", choices=["runtimes", "quota"], required=True)

    sub.add_parser("detect-tools")

    p_detect = sub.add_parser("detect-runtimes")
    p_detect.add_argument(
        "--save", default=None, help="write the snapshot to this path via cache_write_json"
    )
    p_detect.add_argument(
        "--if-stale", default=None, metavar="PATH",
        help=(
            "skip detection entirely (print {} and exit 0) when PATH exists "
            "and is fresher than RUNTIMES_TTL_SECONDS; else detect and --save to PATH"
        ),
    )

    p_quota = sub.add_parser("probe-quota")
    p_quota.add_argument("--cwd", required=True)
    p_quota.add_argument("--quota-path", required=True)

    p_resolve = sub.add_parser("resolve-reviewers")
    p_resolve.add_argument("--cwd", required=True)
    p_resolve.add_argument("--quota-path", required=True)
    p_resolve.add_argument("--source-vendor", default="")  # "" = no same-vendor skip
    p_resolve.add_argument("--cross-ai", action="store_true")

    p_merge = sub.add_parser("merge-reports")
    p_merge.add_argument("--doc-paths", required=True)
    p_merge.add_argument("reports", nargs="+", help="key=path/to/report.md")

    p_toml = sub.add_parser("render-toml")
    p_toml.add_argument(
        "--json-config", required=True, help="path to a JSON file shaped like the TOML config"
    )
    p_toml.add_argument(
        "--out", default=None,
        help=(
            "write the rendered TOML to this path via cfg_write_toml (creating parent dirs) "
            "instead of only printing it"
        ),
    )

    p_render = sub.add_parser("render-command")
    p_render.add_argument("--reviewers-json", required=True,
                           help="path to resolve-reviewers' saved JSON array output")
    p_render.add_argument("--index", type=int, required=True,
                           help="0 for the primary/only reviewer, 1 for the secondary")
    p_render.add_argument("--prompt-file", required=True)

    p_vendor = sub.add_parser("infer-vendor")
    p_vendor.add_argument("--model", required=True)

    p_build_cmd = sub.add_parser("build-command")
    p_build_cmd.add_argument("--cli", required=True)
    p_build_cmd.add_argument("--effort", default=None)
    p_build_cmd.add_argument("--service-tier", default=None)
    p_build_cmd.add_argument("--mode", default="plan",
                              help="cursor-agent only: 'plan' or 'ask' (both read-only)")

    p_build_model = sub.add_parser("build-model-id")
    p_build_model.add_argument("--cli", required=True)
    p_build_model.add_argument("--base-model", required=True)
    p_build_model.add_argument("--effort", default=None)
    p_build_model.add_argument("--fast", choices=["true", "false"], default=None)
    p_build_model.add_argument("--context", default=None)

    p_group = sub.add_parser("group-models")
    p_group.add_argument(
        "--runtimes-json", required=True,
        help="path to a detect-runtimes snapshot (as saved via --save/--if-stale)"
    )
    p_group.add_argument("--cli", required=True,
                          help="which CLI's models array to group, e.g. opencode, cursor-agent")

    p_check = sub.add_parser("check-reviewer")
    p_check.add_argument("--key", default="candidate")
    p_check.add_argument("--model", default="")
    p_check.add_argument("--vendor", default="")
    p_check.add_argument("--cli", default=None,
                          help="omit for a native (no-CLI) candidate — always available")
    p_check.add_argument("--command", dest="reviewer_command", default=None,
                          help="required when --cli is set; the command template to test")
    p_check.add_argument("--extra-json", default=None,
                          help="JSON object of extra {placeholder} fields the template needs")

    args = parser.parse_args(argv)

    if args.command == "cache-path":
        env = dict(os.environ)
        print(cache_runtimes_path(env) if args.kind == "runtimes" else cache_quota_path(env))
        return 0

    if args.command == "detect-tools":
        print(json.dumps(detect_tool_availability(which_fn=which_fn)))
        return 0

    if args.command == "detect-runtimes":
        if args.if_stale and not cache_is_stale(args.if_stale, RUNTIMES_TTL_SECONDS):
            print(json.dumps({}))  # fresh — caller should treat this as "nothing to do"
            return 0
        snapshot = build_runtimes_snapshot(which_fn=which_fn, run_fn=run_fn)
        save_path = args.if_stale or args.save
        if save_path:
            cache_write_json(save_path, snapshot)
        print(json.dumps(snapshot))
        return 0

    if args.command == "probe-quota":
        config = cfg_resolve(args.cwd, dict(os.environ))
        ladder = config.get("policy", {}).get("ladder", [])
        existing = cache_read_json(args.quota_path) or {}
        updated = refresh_quota_cache(config, ladder, existing, QUOTA_TTL_SECONDS, run_fn=run_fn)
        cache_write_json(args.quota_path, updated)
        print(json.dumps(updated))
        return 0

    if args.command == "resolve-reviewers":
        config = cfg_resolve(args.cwd, dict(os.environ))
        quota = cache_read_json(args.quota_path) or {}
        reviewers = resolve_reviewers(config, quota, args.source_vendor, args.cross_ai)
        print(json.dumps([r._asdict() for r in reviewers]))
        return 0

    if args.command == "merge-reports":
        reports = []
        unreadable = []
        for item in args.reports:
            key, _, path = item.partition("=")
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
            except OSError:
                unreadable.append(key)
                continue
            if not report_has_status(text):
                unreadable.append(key)
                continue
            reports.append((key, text))
        if unreadable:
            # Deliberately prints NO "### Status:" line — review-spec/SKILL.md's
            # existing Step 2 already treats "No Status line" as a failure to
            # surface (its own long-standing rule), so a failed/unreadable
            # external reviewer can never silently merge into a false
            # "### Status: Approved". No new orchestrator special-case needed.
            print(f"merge-reports: reviewer(s) {', '.join(unreadable)} produced "
                  f"no readable report with a Status line — cannot merge.")
            return 0
        merged = merge_findings(reports)
        any_source_issues = any(report_declares_issues(text) for _, text in reports)
        print(render_merged_report(merged, args.doc_paths, any_source_issues))
        return 0

    if args.command == "render-toml":
        with open(args.json_config, encoding="utf-8") as f:
            config = json.load(f)
        rendered = cfg_render_toml(config)
        if args.out:
            cfg_write_toml(args.out, config)
        print(rendered)
        return 0

    if args.command == "render-command":
        with open(args.reviewers_json, encoding="utf-8") as f:
            reviewers = json.load(f)
        r = reviewers[args.index]
        resolved = ResolvedReviewer(key=r["key"], model=r["model"], vendor=r["vendor"],
                                     cli=r["cli"], command=r["command"], extra=r["extra"])
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
        try:
            print(render_reviewer_command(resolved, prompt))
        except ValueError as exc:
            # Deliberately no "### Status:" substring — same fail-closed
            # convention as merge-reports: review-spec/SKILL.md's existing
            # "No Status line -> Surface failure" rule catches this
            # without any new special-casing at the dispatch step.
            print(f"render-command: {exc}", file=sys.stderr)
            return 1
        return 0

    if args.command == "infer-vendor":
        print(json.dumps({"vendor": infer_vendor_from_model(args.model)}))
        return 0

    if args.command == "build-command":
        params = {}
        if args.effort:
            params["effort"] = args.effort
        if args.service_tier:
            params["service_tier"] = args.service_tier
        if args.cli == "cursor-agent":
            params["mode"] = args.mode
        try:
            print(build_reviewer_command(args.cli, **params))
        except ValueError as exc:
            print(f"build-command: {exc}", file=sys.stderr)
            return 1
        return 0

    if args.command == "build-model-id":
        fast = {"true": True, "false": False, None: None}[args.fast]
        print(build_reviewer_model_id(args.cli, args.base_model, effort=args.effort,
                                       fast=fast, context=args.context))
        return 0

    if args.command == "group-models":
        snapshot = cache_read_json(args.runtimes_json) or {}
        models = snapshot.get("clis", {}).get(args.cli, {}).get("models", [])
        print(json.dumps(group_models_by_family(models)))
        return 0

    if args.command == "check-reviewer":
        extra = json.loads(args.extra_json) if args.extra_json else {}
        resolved = ResolvedReviewer(key=args.key, model=args.model, vendor=args.vendor,
                                     cli=args.cli, command=args.reviewer_command, extra=extra)
        result = probe_reviewer_quota(resolved, run_fn=run_fn)
        print(json.dumps(result))
        return 0

    return 1
