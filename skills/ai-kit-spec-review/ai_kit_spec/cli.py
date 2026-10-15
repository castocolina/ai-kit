import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from typing import NamedTuple

from ai_kit_spec import trust
from ai_kit_spec.cache import cache_is_stale, cache_read_json, cache_write_json
from ai_kit_spec.catalog_build import (
    CatalogSources,
    _anthropic_model_ids,
    _runtime_meta_from_snapshot,
    build_model_catalog,
)
from ai_kit_spec.commands import (
    ResolvedReviewer,
    build_reviewer_command,
    build_reviewer_model_id,
    execute_cli_error,
    render_reviewer_command,
    split_command_template,
)
from ai_kit_spec.config_io import (
    ConfigError,
    cfg_local_path,
    cfg_parse_toml_bytes,
    cfg_render_toml,
    cfg_resolve,
    cfg_trust_store_dir,
    cfg_write_toml,
    resolve_timeout_tiers,
)
from ai_kit_spec.detection import (
    RUNTIMES_TTL_SECONDS,
    build_runtimes_snapshot,
    cache_runtimes_path,
    claude_runtime_is_current,
    detect_current_runtime,
    detect_tool_availability,
    find_codegraph_alternative,
    group_models_by_family,
    runtimes_schema_is_current,
)
from ai_kit_spec.execute_dispatch import dispatch_execute
from ai_kit_spec.local_secrets import load_secret
from ai_kit_spec.model_catalog import (
    CATALOG_SCHEMA_VERSION,
    CATALOG_TTL_SECONDS,
    apply_heuristic_corrections,
    cache_catalog_path,
    canonical_key,
    catalog_schema_is_current,
    join_catalog_meta,
    merge_catalog_entry,
    split_catalog_meta,
)
from ai_kit_spec.model_sources import fetch_artificial_analysis, fetch_models_dev
from ai_kit_spec.quota import (
    QUOTA_TTL_SECONDS,
    cache_quota_path,
    probe_reviewer_quota,
    refresh_quota_cache,
    resolve_reviewers,
)
from ai_kit_spec.review_reports import (
    merge_findings,
    render_merged_report,
    report_status,
)
from ai_kit_spec.reviewer_dispatch import dispatch_reviewer
from ai_kit_spec.vendor import infer_vendor_from_model


def _default_env_fn():
    return dict(os.environ)


class FetchBuildInputs(NamedTuple):
    discovered: list
    existing_catalog: dict
    catalog_meta: dict
    sources: CatalogSources
    skip_fetch: bool
    runtime_meta: dict


class FetchCatalogOutput(NamedTuple):
    catalog: dict
    catalog_meta: dict
    rejections: list
    unmatched: list
    inputs: FetchBuildInputs


class CliDeps(NamedTuple):
    which_fn: object = shutil.which
    run_fn: object = subprocess.run
    dispatch_execute_fn: object = dispatch_execute
    dispatch_reviewer_fn: object = dispatch_reviewer
    env_fn: object = _default_env_fn
    load_secret_fn: object = load_secret
    fetch_models_dev_fn: object = fetch_models_dev
    fetch_artificial_analysis_fn: object = fetch_artificial_analysis


def _register_cache_detect_parsers(sub: argparse._SubParsersAction) -> None:

    p_cache_path = sub.add_parser("cache-path")
    p_cache_path.add_argument("--kind", choices=["runtimes", "quota", "catalog"], required=True)

    sub.add_parser("detect-tools")
    sub.add_parser("detect-current-runtime")

    p_detect = sub.add_parser("detect-runtimes")
    p_detect.add_argument(
        "--save", default=None, help="write the snapshot to this path via cache_write_json"
    )
    p_detect.add_argument(
        "--if-stale", default=None, metavar="PATH",
        help=(
            "skip detection entirely (print {} and exit 0) when PATH exists, "
            "is fresher than RUNTIMES_TTL_SECONDS, and carries the current "
            "schema_version (a missing or older version always re-detects); "
            "when claude is installed the skip additionally requires the cached "
            "claude model list (aliases/full ids/source) to match what the current "
            "model-catalog.json _meta yields, since those ids are derived from the "
            "catalog; else detect and --save to PATH"
        ),
    )



def _register_catalog_parsers(sub: argparse._SubParsersAction) -> None:
    p_catalog = sub.add_parser("fetch-model-catalog")
    p_catalog.add_argument(
        "--runtimes-json", required=True,
        help="path to a detect-runtimes snapshot (as saved via --save/--if-stale)")
    p_catalog.add_argument("--catalog-path", required=True)
    p_catalog.add_argument("--cwd", default=None,
                            help="for resolving review-spec.toml's already-registered "
                                 "single-provider-CLI models; defaults to the process cwd")
    p_catalog.add_argument(
        "--extra-candidate", action="append", default=[], metavar="CLI:MODEL_ID",
        help="repeatable; a wizard-typed single-provider-CLI candidate not yet in "
             "review-spec.toml (e.g. a first-time codex/grok setup with nothing registered "
             "yet) -- still goes through the same matching/enrichment path as anything else.")
    p_catalog.add_argument(
        "--if-stale", action="store_true",
        help="gate NETWORK CALLS ONLY: when --catalog-path exists, is fresher than "
             "CATALOG_TTL_SECONDS, and its _meta.schema_version is current (a missing or "
             "older version is always re-fetched), skip fetching models.dev/Artificial "
             "Analysis and reuse "
             "cached fields for every already-known candidate -- candidate DISCOVERY/"
             "RECONCILIATION (runtimes snapshot + registered single-provider-CLI models + "
             "--extra-candidate) always runs regardless of this flag, every invocation, so a "
             "brand-new candidate is never silently missed just because the catalog is fresh "
             "(CRITICAL finding: an earlier draft exited before even building the candidate "
             "list when fresh, which is wrong -- freshness should only ever skip re-fetching, "
             "never skip reconciling what's newly installed).")
    # MEDIUM finding: spec Section 8 names a `fetch-model-catalog --force` flag for manual
    # refresh. This plan deliberately does NOT add a separate `--force` flag: the command's
    # default behavior (no flag at all) already re-fetches both external sources unconditionally
    # -- `skip_fetch` below is only ever true when `--if-stale` is explicitly passed AND the
    # cache is fresh. So "run without `--if-stale`" IS the manual-refresh/force path the spec
    # names; a dedicated `--force` flag would be a same-effect alias, not new behavior, and is
    # intentionally omitted here rather than left as a silent, unrecorded gap.

    p_confirm = sub.add_parser("confirm-catalog-entry")
    p_confirm.add_argument("--catalog-path", required=True)
    p_confirm.add_argument("--entry-json", required=True,
                            help="path to a temp JSON file: {\"model_id\": ..., \"entry\": {...}} "
                                 "-- same JSON-temp-file convention as render-toml's --json-config")

    p_apply_correction = sub.add_parser("apply-heuristic-correction")
    p_apply_correction.add_argument("--catalog-path", required=True)
    p_apply_correction.add_argument("--model-id", required=True)
    p_apply_correction.add_argument(
        "--corrections-json", required=True,
        help="path to a temp JSON file: a flat object of any subset of "
             "is_router/batch_mode/fallback_quota, e.g. {\"is_router\": false}")

    p_quota = sub.add_parser("probe-quota")
    p_quota.add_argument("--cwd", required=True)
    p_quota.add_argument("--quota-path", required=True)

    p_resolve = sub.add_parser("resolve-reviewers")
    p_resolve.add_argument("--cwd", required=True)
    p_resolve.add_argument("--quota-path", required=True)
    p_resolve.add_argument("--source-vendor", default="")  # "" = no same-vendor skip
    p_resolve.add_argument("--cross-ai", action="store_true")



def _register_report_parsers(sub: argparse._SubParsersAction) -> None:
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

    p_tiers = sub.add_parser("resolve-timeout-tiers")
    p_tiers.add_argument("--cwd", required=True)
    p_tiers.add_argument("--reviewers-json", required=True,
                          help="path to resolve-reviewers' saved JSON array output")
    p_tiers.add_argument("--index", type=int, required=True)

    p_trust = sub.add_parser("trust-local")
    p_trust.add_argument("--cwd", required=True)
    trust_mode = p_trust.add_mutually_exclusive_group()
    trust_mode.add_argument("--show", action="store_true",
                             help="print each reviewer's exact argv (or its refusal) plus "
                                  "trust status; writes nothing")
    trust_mode.add_argument("--revoke", action="store_true",
                             help="delete this file's trust records (all content hashes)")

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

    p_alt = sub.add_parser("check-codegraph-alternative")
    p_alt.add_argument("--cli", required=True)
    p_alt.add_argument("--model", required=True)
    p_alt.add_argument("--runtimes-json", required=True)



def _register_dispatch_parsers(sub: argparse._SubParsersAction) -> None:
    p_dispatch = sub.add_parser("dispatch-execute")
    p_dispatch.add_argument("--cli", required=True,
                             help="never 'native'/None here -- a native candidate executes "
                                  "in-process and never reaches this subcommand at all")
    p_dispatch.add_argument("--model", required=True)
    p_dispatch.add_argument("--effort", default=None,
                             help="structural param a builder may or may not use, same as "
                                  "build-command's own --effort -- codex's execute builder "
                                  "honors it, others silently ignore it")
    p_dispatch.add_argument("--service-tier", default=None)
    p_dispatch.add_argument("--target-dir", required=True)
    p_dispatch.add_argument("--prompt-file", required=True,
                             help="the phase task prompt -- kept as a file (like render-command's "
                                  "own --prompt-file) since a real prompt can be large; pass '-' "
                                  "to read the prompt from this process's own stdin instead -- "
                                  "the shape needed to drop this subcommand straight into a "
                                  "target framework's own stdin-piping hook (e.g. GSD's "
                                  "workflow.cross_ai_command, which always pipes its task prompt "
                                  "via stdin into whatever command that key names)")
    p_dispatch.add_argument("--heartbeat-interval", type=int, default=30)
    p_dispatch.add_argument("--timeout", type=int, required=True)
    p_dispatch.add_argument("--format-block-file", default=None,
                             help="e.g. GSD's own real SUMMARY.md shape -- omit for a dispatch "
                                  "mode whose caller already knows its own output convention")
    p_dispatch.add_argument("--tool-availability-json", default=None)
    p_dispatch.add_argument("--agents-tooling-path", default=None)
    p_dispatch.add_argument("--codegraph-registered", action="store_true")
    p_dispatch.add_argument(
        "--stdout-only", action="store_true",
        help="print ONLY the dispatched CLI's own stdout (result['stdout'], verbatim, no JSON "
             "envelope) and exit with its own returncode, instead of printing the full JSON "
             "result and always exiting 0/1 -- the exact contract a caller capturing this "
             "subcommand's stdout as a real artifact needs (e.g. GSD's own cross_ai_delegation "
             "step, which redirects workflow.cross_ai_command's raw stdout straight into a "
             "SUMMARY.md candidate file and inspects the real exit code, never a JSON wrapper)")

    p_dispatch_reviewer = sub.add_parser("dispatch-reviewer")
    p_dispatch_reviewer.add_argument(
        "--reviewers-json", required=True,
        help="path to resolve-reviewers' saved JSON array output -- this subcommand renders "
             "the entry's own command template itself (never take a pre-rendered --command "
             "string: the render must happen AFTER the tooling-guidance prefix is composed, "
             "or a CLI that inlines {prompt} into its command line never receives it)")
    p_dispatch_reviewer.add_argument(
        "--index", type=int, required=True,
        help="0 for the primary/only reviewer, 1 for the secondary")
    p_dispatch_reviewer.add_argument("--prompt-file", required=True,
                                      help="pass '-' to read the prompt from this process's "
                                           "own stdin")
    p_dispatch_reviewer.add_argument(
        "--timeout-tiers", required=True,
        help="comma-separated seconds, e.g. '600,1200,1800' -- escalation order")
    p_dispatch_reviewer.add_argument("--tool-availability-json", default=None)
    p_dispatch_reviewer.add_argument("--agents-tooling-path", default=None)
    p_dispatch_reviewer.add_argument(
        "--stdout-only", action="store_true",
        help="print ONLY the dispatched reviewer's own stdout and exit with its real "
             "returncode, same contract as dispatch-execute's own --stdout-only")

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



def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="review-spec")
    sub = parser.add_subparsers(dest="command", required=True)
    _register_cache_detect_parsers(sub)
    _register_catalog_parsers(sub)
    _register_report_parsers(sub)
    _register_dispatch_parsers(sub)
    return parser

def _cmd_cache_path(args: argparse.Namespace, deps: CliDeps) -> int:
    env = dict(os.environ)
    if args.kind == "runtimes":
        print(cache_runtimes_path(env))
    elif args.kind == "catalog":
        print(cache_catalog_path(env))
    else:
        print(cache_quota_path(env))
    return 0

def _cmd_detect_tools(args: argparse.Namespace, deps: CliDeps) -> int:
    print(json.dumps(detect_tool_availability(which_fn=deps.which_fn)))
    return 0

def _cmd_detect_current_runtime(args: argparse.Namespace, deps: CliDeps) -> int:
    print(json.dumps({"native_runtime": detect_current_runtime(deps.env_fn())}))
    return 0

def _cmd_detect_runtimes(args: argparse.Namespace, deps: CliDeps) -> int:
    def _read_default_catalog():
        # 16 D-04: detect-runtimes has no catalog-path flag -- it reads the standard
        # cache location derived from deps.env_fn(). A nested def, not an assigned lambda,
        # so ruff's lambda-assignment rule never fires.
        return cache_read_json(cache_catalog_path(deps.env_fn()))

    # 16 D-12: the skip requires BOTH a fresh mtime AND the current schema_version --
    # a missing or older version forces re-detection whatever the TTL says (Pitfall 3:
    # the refresh condition is "stale OR version not current", never chained ANDs).
    # Plan 16-04 adds a third AND-ed condition (the claude entry matches the current
    # catalog) to this same expression; the catalog is only read when the cache would
    # otherwise be skipped, and only its claude portion is compared.
    cached_runtimes = cache_read_json(args.if_stale) if args.if_stale else None
    if args.if_stale and not cache_is_stale(args.if_stale, RUNTIMES_TTL_SECONDS) \
            and runtimes_schema_is_current(cached_runtimes) \
            and claude_runtime_is_current(cached_runtimes,
                                          catalog_fn=_read_default_catalog):
        print(json.dumps({}))  # fresh — caller should treat this as "nothing to do"
        return 0
    snapshot = build_runtimes_snapshot(which_fn=deps.which_fn, run_fn=deps.run_fn,
                                        catalog_fn=_read_default_catalog)
    save_path = args.if_stale or args.save
    if save_path:
        cache_write_json(save_path, snapshot)
    print(json.dumps(snapshot))
    return 0



def _discovered_catalog_candidates(
    runtimes: dict, args: argparse.Namespace, deps: CliDeps
) -> list:
    discovered = [
        {"cli": cli_name, "model_id": model_id}
        for cli_name, cli_data in runtimes.get("clis", {}).items()
        for model_id in cli_data.get("models", [])
    ]
    single_provider_clis = {
        name
        for name, data in runtimes.get("clis", {}).items()
        if data.get("installed") and "models" not in data
    }
    if single_provider_clis:
        cwd = args.cwd or os.getcwd()
        resolved = cfg_resolve(cwd, deps.env_fn())
        for reviewer in resolved.get("reviewers", []):
            if reviewer.get("cli") in single_provider_clis and reviewer.get("model"):
                discovered.append({"cli": reviewer["cli"], "model_id": reviewer["model"]})
    for raw in args.extra_candidate:
        cli_name, _, model_id = raw.partition(":")
        if cli_name and model_id:
            discovered.append({"cli": cli_name, "model_id": model_id})
    return discovered


def _fetch_catalog_external_sources(
    deps: CliDeps, args: argparse.Namespace, catalog_meta: dict
) -> tuple[CatalogSources, dict, bool]:
    fetch_meta_path = args.catalog_path + ".fetch-meta.json"
    skip_fetch = (
        args.if_stale
        and not cache_is_stale(fetch_meta_path, CATALOG_TTL_SECONDS)
        and catalog_schema_is_current(catalog_meta)
    )
    if skip_fetch:
        return CatalogSources({}, False, [], False), catalog_meta, skip_fetch
    api_key = deps.load_secret_fn(deps.env_fn(), "ARTIFICIAL_ANALYSIS_API_KEY")
    models_dev_data, models_dev_ok = deps.fetch_models_dev_fn()
    aa_models, aa_fetch_ok = deps.fetch_artificial_analysis_fn(api_key)
    aa_ok = aa_fetch_ok and bool(api_key)
    if models_dev_ok or aa_ok:
        cache_write_json(fetch_meta_path, {"last_fetched": time.time()})
    if models_dev_ok:
        catalog_meta = {**catalog_meta, "schema_version": CATALOG_SCHEMA_VERSION}
    return (
        CatalogSources(models_dev_data, models_dev_ok, aa_models, aa_ok),
        catalog_meta,
        skip_fetch,
    )


def _finalize_fetch_catalog_meta(
    catalog: dict,
    catalog_meta: dict,
    anthropic_ids: list,
    materialized: bool,
) -> dict:
    if materialized:
        anthropic_ids = [
            i
            for i in anthropic_ids
            if canonical_key("anthropic", i) in catalog
            and "claude" in catalog[canonical_key("anthropic", i)].get("runtimes", {})
        ]
    if anthropic_ids:
        catalog_meta["anthropic_model_ids"] = anthropic_ids
        catalog_meta["anthropic_model_ids_as_of"] = time.strftime("%Y-%m-%d")
    return catalog_meta


def _write_fetch_catalog_result(args, out: FetchCatalogOutput) -> None:
    cache_write_json(args.catalog_path, join_catalog_meta(out.catalog, out.catalog_meta))
    print(json.dumps({
        "catalog_path": args.catalog_path,
        "entry_count": len(out.catalog),
        "rejections": out.rejections,
        "unmatched": out.unmatched,
        "discovered": out.inputs.discovered,
        "models_dev_ok": out.inputs.sources.models_dev_ok,
        "artificial_analysis_ok": out.inputs.sources.aa_ok,
        "fetch_skipped": out.inputs.skip_fetch,
    }))


def _claude_catalog_candidates(
    discovered: list, anthropic_ids: list, which_fn
) -> tuple[list, bool]:
    if not anthropic_ids or not which_fn("claude"):
        return [], False
    listed = {(c["cli"], c["model_id"]) for c in discovered}
    claude_candidates = [
        {"cli": "claude", "model_id": model_id}
        for model_id in anthropic_ids
        if ("claude", model_id) not in listed
    ]
    return claude_candidates, True

def _run_fetch_catalog_build(
    inputs: FetchBuildInputs, deps: CliDeps
) -> FetchCatalogOutput:
    anthropic_ids = (
        _anthropic_model_ids(inputs.sources.models_dev_data)
        if (not inputs.skip_fetch and inputs.sources.models_dev_ok)
        else []
    )
    claude_candidates, materialized = _claude_catalog_candidates(
        inputs.discovered, anthropic_ids, deps.which_fn
    )
    catalog, rejections, unmatched = build_model_catalog(
        inputs.discovered + claude_candidates,
        inputs.sources,
        inputs.existing_catalog,
        runtime_meta=inputs.runtime_meta,
    )
    extra = {("claude", c["model_id"]) for c in claude_candidates}
    filtered = [
        record
        for record in unmatched
        if (record.get("cli"), record.get("model_id")) not in extra
    ]
    meta = _finalize_fetch_catalog_meta(
        catalog, inputs.catalog_meta, anthropic_ids, materialized
    )
    return FetchCatalogOutput(catalog, meta, rejections, filtered, inputs)


def _cmd_fetch_model_catalog(args: argparse.Namespace, deps: CliDeps) -> int:
    # MEDIUM finding: cache_is_stale is already imported at module level (`from
    # ai_kit_spec.cache import cache_is_stale, cache_read_json, cache_write_json` --
    # confirmed live in the current cli.py) -- no local re-import needed here.
    # load_secret/fetch_models_dev/fetch_artificial_analysis are now imported at module
    # level too (Important finding, coordinator review: this subcommand's real-I/O calls
    # had no injection hook, so the "no API key" branch below was never actually exercised
    # by the test suite -- every existing test dodged it via `--if-stale`). They're threaded
    # through load_secret_fn/fetch_models_dev_fn/fetch_artificial_analysis_fn on CliDeps,
    # same deps.which_fn/deps.run_fn/deps.env_fn convention this repo
    # already uses everywhere else.
    runtimes = cache_read_json(args.runtimes_json) or {}
    runtime_meta = _runtime_meta_from_snapshot(runtimes)
    discovered = _discovered_catalog_candidates(runtimes, args, deps)

    # 16 D-12: split the reserved `_meta` metadata object off so build_model_catalog and
    # _find_existing_key_for_runtime only ever see real `provider/model` entries (every
    # other top-level key of a catalog file is a model entry; `_meta` never is).
    existing_catalog, catalog_meta = split_catalog_meta(
        cache_read_json(args.catalog_path))
    # Important finding (coordinator review): `cache_is_stale(args.catalog_path, ...)` is
    # mtime-based, but `cache_write_json(args.catalog_path, catalog)` below runs on EVERY
    # invocation -- including a skip_fetch run where nothing external was ever queried.
    # That resets the catalog file's own mtime every run regardless of whether a real fetch
    # happened, so once `--if-stale` is invoked more often than every CATALOG_TTL_SECONDS,
    # the external-source data looks perpetually fresh and never actually re-fetches.
    # Freshness for THIS purpose (should we re-fetch from models.dev/Artificial Analysis?)
    # is tracked via a dedicated sidecar file instead, written ONLY when a fetch actually
    # ran this invocation AND at least one source came back genuinely ok -- never touched
    # on a skipped-fetch run, so its own mtime reflects the last REAL fetch, not the last
    # catalog write.
    sources, catalog_meta, skip_fetch = _fetch_catalog_external_sources(
        deps, args, catalog_meta
    )
    out = _run_fetch_catalog_build(
        FetchBuildInputs(
            discovered, existing_catalog, catalog_meta, sources, skip_fetch, runtime_meta
        ),
        deps,
    )
    _write_fetch_catalog_result(args, out)
    return 0

def _cmd_confirm_catalog_entry(args: argparse.Namespace, deps: CliDeps) -> int:
    payload = cache_read_json(args.entry_json) or {}
    # Important finding (coordinator review): every other failure mode across these three
    # subcommands returns structured JSON + exit 1 -- a malformed/empty --entry-json used to
    # raise a bare KeyError traceback here instead, via unguarded payload["model_id"]/
    # payload["entry"] access. Validate the payload's shape before ever touching those keys.
    if (not isinstance(payload, dict) or not isinstance(payload.get("model_id"), str)
            or not isinstance(payload.get("entry"), dict)):
        print(json.dumps({
            "confirmed": False,
            "reason": "--entry-json must be an object with a string 'model_id' and an "
                      "object 'entry'"}))
        return 1
    # 16 D-12: split `_meta` off before merging so merge_catalog_entry only ever sees
    # real entries, then write it back verbatim -- confirm never disturbs cache metadata.
    entries, meta = split_catalog_meta(cache_read_json(args.catalog_path))
    merged, reason = merge_catalog_entry(entries, payload["model_id"], payload["entry"])
    if reason:
        print(json.dumps({"confirmed": False, "reason": reason}))
        return 1
    cache_write_json(args.catalog_path, join_catalog_meta(merged, meta))
    print(json.dumps({"confirmed": True, "model_id": payload["model_id"]}))
    return 0

def _cmd_apply_heuristic_correction(args: argparse.Namespace, deps: CliDeps) -> int:
    # HIGH finding: a raw json.dump(..., open(path, "w")) bypasses this repo's atomic,
    # validated cache-write path -- a crash mid-write can corrupt the catalog file, and
    # nothing here would ever re-validate the result. cache_write_json (already imported,
    # used by every other catalog-writing subcommand) is the ONE write path for
    # model-catalog.json; this subcommand is the ONLY way a heuristic correction is
    # ever persisted, matching confirm-catalog-entry's contract for unmatched candidates.
    # CRITICAL finding: apply_heuristic_corrections now returns (catalog, reason) -- a
    # correction that would produce a schema-invalid entry is rejected here exactly like
    # confirm-catalog-entry rejects an invalid new entry, never silently written.
    corrections = cache_read_json(args.corrections_json) or {}
    # 16 D-12: split `_meta` off before correcting, write it back verbatim -- a
    # correction never disturbs the catalog's cache metadata.
    entries, meta = split_catalog_meta(cache_read_json(args.catalog_path))
    catalog, reason = apply_heuristic_corrections(entries, args.model_id, corrections)
    if reason:
        print(json.dumps({"applied": False, "reason": reason}))
        return 1
    cache_write_json(args.catalog_path, join_catalog_meta(catalog, meta))
    print(json.dumps({"applied": True, "model_id": args.model_id}))
    return 0

def _cmd_probe_quota(args: argparse.Namespace, deps: CliDeps) -> int:
    config = cfg_resolve(args.cwd, dict(os.environ))
    ladder = config.get("policy", {}).get("ladder", [])
    existing = cache_read_json(args.quota_path) or {}
    updated = refresh_quota_cache(config, ladder, existing, QUOTA_TTL_SECONDS, run_fn=deps.run_fn)
    cache_write_json(args.quota_path, updated)
    print(json.dumps(updated))
    return 0

def _cmd_resolve_reviewers(args: argparse.Namespace, deps: CliDeps) -> int:
    config = cfg_resolve(args.cwd, dict(os.environ))
    quota = cache_read_json(args.quota_path) or {}
    reviewers = resolve_reviewers(config, quota, args.source_vendor, args.cross_ai)
    print(json.dumps([r._asdict() for r in reviewers]))
    return 0

def _cmd_merge_reports(args: argparse.Namespace, deps: CliDeps) -> int:
    reports = []
    failing = []
    for item in args.reports:
        key, _, path = item.partition("=")
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            failing.append(key)
            continue
        status = report_status(text)
        if status is None or status == "failure":
            failing.append(key)
            continue
        reports.append((key, text))
    if failing:
        # D-12/R7: any failing or missing lane fails the merge — the Status line is
        # printed so SKILL.md Step 2's fail-closed rule sees a Failure verdict, and
        # the non-zero exit keeps the merge out of any `&&`-chained pipeline.
        print(f"### Status: Failure — {', '.join(failing)}")
        return 1
    merged = merge_findings(reports)
    any_source_issues = any(report_status(text) == "issues" for _, text in reports)
    print(render_merged_report(merged, args.doc_paths, any_source_issues))
    return 0

def _cmd_render_toml(args: argparse.Namespace, deps: CliDeps) -> int:
    with open(args.json_config, encoding="utf-8") as f:
        config = json.load(f)
    rendered = cfg_render_toml(config)
    if args.out:
        cfg_write_toml(args.out, config)
    print(rendered)
    return 0

def _cmd_render_command(args: argparse.Namespace, deps: CliDeps) -> int:
    with open(args.reviewers_json, encoding="utf-8") as f:
        reviewers = json.load(f)
    r = reviewers[args.index]
    resolved = ResolvedReviewer(key=r["key"], model=r["model"], vendor=r["vendor"],
                                 cli=r["cli"], command=r["command"], extra=r["extra"])
    with open(args.prompt_file, encoding="utf-8") as f:
        prompt = f.read()
    try:
        # argv dispatch (D-10): print the rendered argv as a JSON array, not a string
        print(json.dumps(render_reviewer_command(resolved, prompt)))
    except ValueError as exc:
        # Deliberately no "### Status:" substring — same fail-closed
        # convention as merge-reports: review-spec/SKILL.md's existing
        # "No Status line -> Surface failure" rule catches this
        # without any new special-casing at the dispatch step.
        print(f"render-command: {exc}", file=sys.stderr)
        return 1
    return 0

def _cmd_resolve_timeout_tiers(args: argparse.Namespace, deps: CliDeps) -> int:
    with open(args.reviewers_json, encoding="utf-8") as f:
        reviewers = json.load(f)
    r = reviewers[args.index]
    config = cfg_resolve(args.cwd, dict(os.environ))
    tiers = resolve_timeout_tiers(r, config.get("policy", {}))
    print(",".join(str(t) for t in tiers))
    return 0

def _cmd_trust_local(args: argparse.Namespace, deps: CliDeps) -> int:
    local_path = cfg_local_path(args.cwd)
    if not os.path.exists(local_path):
        print(f"no project-local config at {local_path}", file=sys.stderr)
        return 1
    real = os.path.realpath(local_path)
    env = dict(os.environ)
    store = cfg_trust_store_dir(env)
    with open(local_path, "rb") as f:
        raw = f.read()
    config = cfg_parse_toml_bytes(raw, local_path)
    for r in config.get("reviewers", []):
        if "command" not in r:
            continue
        key = r.get("key")
        line = {"key": key}
        try:
            line["argv"] = split_command_template(key, r["command"])
            if args.show:
                line["trusted"] = trust.is_trusted(store, real, raw)
                line["path"] = real
        except ValueError as exc:
            line = {"key": key, "error": str(exc)}
        print(json.dumps(line))
    if args.show:
        return 0
    if args.revoke:
        n = trust.revoke_trust(store, real)
        print(f"revoked {n} trust record(s) for {real}")
        return 0
    sha = trust.content_sha256(raw)
    trust.record_trust(store, real, raw)
    print(f"trusted {real} sha256={sha}")
    return 0

def _cmd_infer_vendor(args: argparse.Namespace, deps: CliDeps) -> int:
    print(json.dumps({"vendor": infer_vendor_from_model(args.model)}))
    return 0

def _cmd_build_command(args: argparse.Namespace, deps: CliDeps) -> int:
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

def _cmd_build_model_id(args: argparse.Namespace, deps: CliDeps) -> int:
    fast = {"true": True, "false": False, None: None}[args.fast]
    print(build_reviewer_model_id(args.cli, args.base_model, effort=args.effort,
                                   fast=fast, context=args.context))
    return 0

def _cmd_group_models(args: argparse.Namespace, deps: CliDeps) -> int:
    snapshot = cache_read_json(args.runtimes_json) or {}
    models = snapshot.get("clis", {}).get(args.cli, {}).get("models", [])
    print(json.dumps(group_models_by_family(models)))
    return 0

def _cmd_check_codegraph_alternative(args: argparse.Namespace, deps: CliDeps) -> int:
    snapshot = cache_read_json(args.runtimes_json) or {}
    alternative = find_codegraph_alternative(args.cli, args.model, snapshot)
    print(json.dumps({"alternative_cli": alternative}))
    return 0

def _cmd_dispatch_execute(args: argparse.Namespace, deps: CliDeps) -> int:
    # D-15 hardening: an explicit claude/grok executor choice is rejected before the prompt
    # is read or any dispatch function is called -- nothing is spawned, ever.
    rejection = execute_cli_error(args.cli)
    if rejection:
        print(f"ai-kit-spec: {rejection}", file=sys.stderr)
        return 2
    if args.prompt_file == "-":
        prompt = sys.stdin.read()
    else:
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
    format_block = None
    if args.format_block_file:
        with open(args.format_block_file, encoding="utf-8") as f:
            format_block = f.read()
    tool_availability = (json.loads(args.tool_availability_json)
                          if args.tool_availability_json else {})
    candidate = {"cli": args.cli, "model": args.model, "effort": args.effort,
                 "service_tier": args.service_tier}
    try:
        result = deps.dispatch_execute_fn(
            candidate, prompt, args.target_dir, args.heartbeat_interval, args.timeout,
            format_block=format_block, tool_availability=tool_availability,
            agents_tooling_path=args.agents_tooling_path,
            codegraph_registered=args.codegraph_registered)
    except ValueError as exc:
        print(f"dispatch-execute: {exc}", file=sys.stderr)
        return 1
    if args.stdout_only:
        sys.stdout.write(result["stdout"])
        # Propagate the dispatched CLI's own real returncode (not a collapsed 0/1) -- GSD's
        # own cross_ai_delegation step only ever checks nonzero-vs-zero, but the real code is
        # more diagnosable than a flattened one when things go wrong. A timeout kill can leave
        # returncode negative (signal) or None depending on the platform; 1 covers both, since
        # any nonzero reads as failure either way.
        return result["returncode"] if result["returncode"] is not None else 1
    print(json.dumps(result))
    return 0

def _cmd_dispatch_reviewer(args: argparse.Namespace, deps: CliDeps) -> int:
    with open(args.reviewers_json, encoding="utf-8") as f:
        reviewers = json.load(f)
    if not -len(reviewers) <= args.index < len(reviewers):
        print(f"dispatch-reviewer: no reviewer at index {args.index} "
              f"({len(reviewers)} entries)", file=sys.stderr)
        return 1
    if args.prompt_file == "-":
        prompt = sys.stdin.read()
    else:
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
    timeout_tiers = [int(t) for t in args.timeout_tiers.split(",") if t.strip()]
    tool_availability = (json.loads(args.tool_availability_json)
                          if args.tool_availability_json else {})
    try:
        result = deps.dispatch_reviewer_fn(
            reviewers[args.index], prompt, timeout_tiers, tool_availability,
            args.agents_tooling_path)
    except ValueError as exc:
        # Deliberately no "### Status:" substring -- same fail-closed convention
        # render-command uses: a malformed reviewer entry (bad/missing command template,
        # empty timeout tiers) leaves this reviewer's report file absent/statusless, which
        # ai-kit-spec-review/SKILL.md's existing "No Status line -> Surface failure" rule
        # already handles with no new special-casing.
        print(f"dispatch-reviewer: {exc}", file=sys.stderr)
        return 1
    if args.stdout_only:
        sys.stdout.write(result["stdout"])
        return result["returncode"] if result["returncode"] is not None else 1
    print(json.dumps(result))
    return 0

def _cmd_check_reviewer(args: argparse.Namespace, deps: CliDeps) -> int:
    extra = json.loads(args.extra_json) if args.extra_json else {}
    resolved = ResolvedReviewer(key=args.key, model=args.model, vendor=args.vendor,
                                 cli=args.cli, command=args.reviewer_command, extra=extra)
    result = probe_reviewer_quota(resolved, run_fn=deps.run_fn)
    print(json.dumps(result))
    return 0
_COMMANDS = {
    "cache-path": _cmd_cache_path,
    "detect-tools": _cmd_detect_tools,
    "detect-current-runtime": _cmd_detect_current_runtime,
    "detect-runtimes": _cmd_detect_runtimes,
    "fetch-model-catalog": _cmd_fetch_model_catalog,
    "confirm-catalog-entry": _cmd_confirm_catalog_entry,
    "apply-heuristic-correction": _cmd_apply_heuristic_correction,
    "probe-quota": _cmd_probe_quota,
    "resolve-reviewers": _cmd_resolve_reviewers,
    "merge-reports": _cmd_merge_reports,
    "render-toml": _cmd_render_toml,
    "render-command": _cmd_render_command,
    "resolve-timeout-tiers": _cmd_resolve_timeout_tiers,
    "trust-local": _cmd_trust_local,
    "infer-vendor": _cmd_infer_vendor,
    "build-command": _cmd_build_command,
    "build-model-id": _cmd_build_model_id,
    "group-models": _cmd_group_models,
    "check-codegraph-alternative": _cmd_check_codegraph_alternative,
    "dispatch-execute": _cmd_dispatch_execute,
    "dispatch-reviewer": _cmd_dispatch_reviewer,
    "check-reviewer": _cmd_check_reviewer,
}

def _dispatch(argv: list, deps: CliDeps) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = _COMMANDS.get(args.command)
    if handler is None:
        return 1
    return handler(args, deps)


def main(argv: list, deps: CliDeps | None = None, **overrides) -> int:
    """Wrapper around dispatch that turns ConfigError (D-11/R13) into exit 2."""
    merged = (deps or CliDeps())._replace(**overrides)
    try:
        return _dispatch(argv, merged)
    except ConfigError as exc:
        print(f"ai-kit-spec: config error: {exc}", file=sys.stderr)
        return 2
