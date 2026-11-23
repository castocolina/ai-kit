"""35 D-01, D-13: catalog commands (confirm-model, models-config, catalog-report and
optional-source commands). cli.py registers them; this module never imports cli. Handlers
take (args, deps) and print JSON or text."""

import difflib
import json
import os
import sys

from ai_kit_spec import (
    catalog_bands,
    catalog_report,
    config_io,
    detection,
    herdr_source,
    models_config,
    optional_sources,
)
from ai_kit_spec.cache import cache_read_json
from ai_kit_spec.catalog_attribution import attribution_lines, catalog_sources
from ai_kit_spec.catalog_labels import fact, now_iso
from ai_kit_spec.model_catalog import (
    apply_heuristic_corrections,
    join_catalog_meta,
    locked_catalog_update,
    merge_catalog_entry,
    split_catalog_meta,
)

CONFIRMABLE = ("is_router", "batch_mode", "fallback_quota", "class")
_BOOL_FIELDS = ("is_router", "batch_mode", "fallback_quota")


class Refused(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _parse_value(field: str, raw: str):
    if field in _BOOL_FIELDS:
        lowered = raw.lower()
        if lowered not in ("true", "false"):
            raise ValueError(f"{field} needs true or false")
        return lowered == "true"
    if field == "class" and raw in catalog_bands.CLASSES and raw != "unknown":
        return raw
    allowed = ", ".join(value for value in catalog_bands.CLASSES if value != "unknown")
    raise ValueError(f"class must be one of: {allowed}")


def cmd_confirm_model(args, deps) -> int:
    if args.field not in CONFIRMABLE:
        print(f"unknown confirm-model field: {args.field}", file=sys.stderr)
        return 2
    try:
        value = _parse_value(args.field, args.value)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    now = now_iso()

    def update(current):
        entries, meta = split_catalog_meta(current)
        key = args.model_id
        if key not in entries:
            nearest = difflib.get_close_matches(key, list(entries), n=5, cutoff=0.4)
            raise Refused(1, f"unknown catalog key: {key}; nearest: {', '.join(nearest)}")
        entry = entries[key]
        if args.field in _BOOL_FIELDS:
            entries, reason = apply_heuristic_corrections(entries, key, {args.field: value})
        else:
            entries, reason = merge_catalog_entry(
                entries,
                key,
                {
                    **entry,
                    "facts": {
                        **entry.get("facts", {}),
                        "class": fact(value, "user-stated", "confirm-model", now),
                    },
                },
            )
        if reason:
            raise Refused(1, reason)
        entry = entries[key]
        confirmed = {
            **entry.get("confirmed_fields", {}),
            args.field: {"by": "confirm-model", "at": now, "note": args.note or ""},
        }
        entries, reason = merge_catalog_entry(
            entries, key, {**entry, "confirmed_fields": confirmed}
        )
        if reason:
            raise Refused(1, reason)
        return join_catalog_meta(entries, meta)

    try:
        locked_catalog_update(args.catalog_path, update)
    except Refused as error:
        print(error.message, file=sys.stderr)
        return error.code
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps({"model_id": args.model_id, "field": args.field, "value": value,
                      "confirmed": True}))
    return 0


def _settings_json(settings) -> dict:
    return {
        "sources": list(settings.sources),
        "cache_days": settings.cache_days,
        "context": [item._asdict() for item in settings.context],
    }


def _parse_cache_days(pairs: list[str]) -> dict:
    result = {}
    for pair in pairs:
        key, separator, raw = pair.partition("=")
        if not separator or not key:
            raise ValueError(f"bad --cache-days value: {pair}")
        try:
            result[key] = int(raw)
        except ValueError as error:
            raise ValueError(f"bad --cache-days value: {pair}") from error
    return result


def cmd_models_config(args, deps) -> int:
    env = deps.env_fn()
    cwd = args.cwd or os.getcwd()
    if args.show:
        print(json.dumps(_settings_json(models_config.read_models_settings(cwd, env))))
        return 0
    try:
        cache_days = _parse_cache_days(args.cache_days)
        context = []
        for runtime, model, raw_tokens in args.context:
            try:
                tokens = int(raw_tokens)
            except ValueError as error:
                raise ValueError(f"bad --context tokens: {raw_tokens}") from error
            context.append(models_config.ContextOverride(runtime, model, tokens))
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    sources = args.sources.split(",") if args.sources is not None else None
    if sources is None and not cache_days and not context:
        print("nothing to write", file=sys.stderr)
        return 2
    path = (config_io.cfg_global_path(env) if args.global_scope
            else config_io.cfg_local_path(cwd))
    models_config.write_models_settings(
        path,
        sources=sources,
        cache_days=cache_days or None,
        context=context if args.context else None,
    )
    print(json.dumps({"written": path}))
    return 0


def _optional_rows_input(env) -> dict:
    store = cache_read_json(optional_sources.store_path(env)) or {}
    if not isinstance(store, dict):
        return {}
    return {
        runtime: optional_sources.optional_candidates(store, runtime)
        for runtime in store
        if isinstance(runtime, str)
    }


def cmd_catalog_report(args, deps) -> int:
    entries = split_catalog_meta(cache_read_json(args.catalog_path) or {})[0]
    if args.detect:
        snapshot = detection.build_runtimes_snapshot(
            which_fn=deps.which_fn,
            run_fn=deps.run_fn,
            catalog_fn=lambda: cache_read_json(args.catalog_path),
            opencode=detection.OpencodeSeams(
                deps.popen_fn, deps.urlopen_fn, deps.env_fn()
            ),
        )
        fresh = True
    else:
        snapshot = cache_read_json(args.runtimes_json) or {}
        fresh = False
    rows = catalog_report.report_rows(
        entries, snapshot, _optional_rows_input(deps.env_fn()), fresh=fresh
    )
    lines = attribution_lines(catalog_sources(entries))
    if args.json:
        print(json.dumps({
            "rows": [row._asdict() for row in rows],
            "attribution": lines,
        }))
    else:
        output = catalog_report.render_lines(rows)
        if lines:
            output.extend(("", "Attribution:", *lines))
        print("\n".join(output))
    return 0


def cmd_web_query(args, deps) -> int:
    try:
        print(optional_sources.web_query(args.runtime))
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


def cmd_record_web_names(args, deps) -> int:
    try:
        runtime, records = optional_sources.ingest_web_file(args.file)
        optional_sources.record_names(
            optional_sources.store_path(deps.env_fn()), runtime, records
        )
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps({"runtime": runtime, "recorded": len(records),
                      "label": "web, unverified"}))
    return 0


def cmd_herdr_names(args, deps) -> int:
    records, status = herdr_source.read_interactive_names(
        args.runtime, deps.env_fn(), deps.run_fn, deps.which_fn, args.cwd or os.getcwd()
    )
    if records:
        optional_sources.record_names(
            optional_sources.store_path(deps.env_fn()), args.runtime, records
        )
    print(json.dumps({"status": status, "recorded": len(records)}))
    return 0


def optional_fetch_candidates(snapshot: dict, store: dict, sources) -> list:
    """Candidates from stored optional names and seed rows for installed no-list runtimes."""
    result = []
    for runtime, row in snapshot.get("clis", {}).items():
        if not isinstance(row, dict) or not row.get("installed") or row.get("listing") != "none":
            continue
        seed = []
        if sources.models_dev_ok and runtime != "claude":
            seed = optional_sources.seed_candidates(runtime, sources.models_dev_data)
        for candidate in optional_sources.optional_candidates(store, runtime, seed=seed):
            result.append({
                "runtime": runtime,
                "model_id": candidate["name"],
                "listed_from": candidate["sources"],
                "label": candidate["label"],
            })
    return sorted(
        {(item["runtime"], item["model_id"]): item for item in result}.values(),
        key=lambda item: (item["runtime"], item["model_id"]),
    )


def builder_candidates(optional: list, taken: set) -> list:
    """Project optional candidates to builder shape, omitting already discovered pairs."""
    return [
        {"runtime": item["runtime"], "model_id": item["model_id"]}
        for item in optional
        if (item["runtime"], item["model_id"]) not in taken
    ]


def attach_listed_from(catalog: dict, candidates: list) -> tuple:
    """Attach optional-source records to matching runtime rows, retaining full provenance."""
    reasons = []
    for candidate in candidates:
        runtime = candidate.get("runtime")
        model_id = candidate.get("model_id")
        if not isinstance(runtime, str) or not isinstance(model_id, str):
            continue
        key = next((entry_key for entry_key, entry in catalog.items()
                    if isinstance(entry, dict)
                    and isinstance(entry.get("runtimes"), dict)
                    and isinstance(entry["runtimes"].get(runtime), dict)
                    and entry["runtimes"][runtime].get("model_id") == model_id), None)
        if key is None:
            continue
        entry = catalog[key]
        updated, reason = merge_catalog_entry(
            catalog, key, {**entry, "runtimes": {runtime: {
                "model_id": model_id, "listed_from": candidate.get("listed_from", [])
            }}}
        )
        catalog = updated
        if reason:
            reasons.append(reason)
    return catalog, reasons


def register_parsers(sub) -> None:
    web_query = sub.add_parser("web-query")
    web_query.add_argument("--runtime", required=True)
    record_web = sub.add_parser("record-web-names")
    record_web.add_argument("--file", required=True)
    herdr = sub.add_parser("herdr-names")
    herdr.add_argument("--runtime", required=True)
    herdr.add_argument("--cwd", default=None)

    confirm = sub.add_parser("confirm-model")
    confirm.add_argument("--catalog-path", required=True)
    confirm.add_argument("--model-id", required=True)
    confirm.add_argument("--field", choices=CONFIRMABLE, required=True)
    confirm.add_argument("--value", required=True)
    confirm.add_argument("--note", default="")

    settings = sub.add_parser("models-config")
    settings.add_argument("--cwd", default=None)
    settings.add_argument("--global", dest="global_scope", action="store_true")
    settings.add_argument("--sources", default=None)
    settings.add_argument("--cache-days", action="append", default=[])
    settings.add_argument("--context", nargs=3, action="append", default=[],
                          metavar=("RUNTIME", "MODEL", "TOKENS"))
    settings.add_argument("--show", action="store_true")

    report = sub.add_parser("catalog-report")
    report.add_argument("--catalog-path", required=True)
    proof = report.add_mutually_exclusive_group(required=True)
    proof.add_argument("--detect", action="store_true")
    proof.add_argument("--runtimes-json", required=False)
    report.add_argument("--json", action="store_true")


COMMANDS = {
    "web-query": cmd_web_query,
    "record-web-names": cmd_record_web_names,
    "herdr-names": cmd_herdr_names,
    "confirm-model": cmd_confirm_model,
    "models-config": cmd_models_config,
    "catalog-report": cmd_catalog_report,
}
