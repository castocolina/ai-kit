"""36 R6, R12 a and c, D-07, D-18: the propose-lanes command.

It writes no config, catalog, lane or usability record. cli.py registers it; this module never
imports cli.
"""

import json
import sys

from ai_kit_spec import detection, lane_effort, lane_order, lane_pool, lane_price, model_ranker
from ai_kit_spec.cache import cache_read_json
from ai_kit_spec.model_catalog import split_catalog_meta

DEFAULT_VIEW = 5
ZERO_GROUP_MAX = 5
EMPTY_CATALOG = ("model catalog is empty: run fetch-model-catalog first "
                 "(the spec-config catalog step)")
EMPTY_POOL = "no candidates for this purpose"
WIDER_REASON = "scorer: wider pool, scores not comparable with the main list"


def _snapshot(args, deps) -> tuple:
    # the same snapshot input as catalog_cmds.cmd_catalog_report
    if args.detect:
        return detection.build_runtimes_snapshot(
            which_fn=deps.which_fn, run_fn=deps.run_fn,
            catalog_fn=lambda: cache_read_json(args.catalog_path),
            opencode=detection.OpencodeSeams(deps.popen_fn, deps.urlopen_fn, deps.env_fn()),
        ), True
    snapshot = cache_read_json(args.runtimes_json)
    if not isinstance(snapshot, dict):
        return None, False
    return {**snapshot, "clis": detection.normalize_runtime_keys(snapshot.get("clis"))}, False


def _load(args, deps) -> tuple:
    raw = split_catalog_meta(cache_read_json(args.catalog_path) or {})[0]
    entries = {k: v for k, v in raw.items() if isinstance(v, dict)}
    if not entries:
        return entries, None, False, EMPTY_CATALOG
    snapshot, fresh = _snapshot(args, deps)
    problem = (None if snapshot is not None else
               f"runtimes snapshot unreadable: {args.runtimes_json}")
    return entries, snapshot, fresh, problem


def _filters(args) -> tuple:
    avoid, skip = set(), set()
    for value in args.avoid_pool:
        if not lane_price.POOL_KEY_RX.fullmatch(value):
            return avoid, skip, f"bad --avoid-pool value: {value} (expected <provider>:free)"
        avoid.add(value)
    for value in args.skip:
        runtime, sep, key = value.partition(":")
        if not runtime or not sep or not key:
            return avoid, skip, f"bad --skip value: {value} (expected RUNTIME:KEY)"
        skip.add((runtime, key))
    return avoid, skip, None


def _offers(rows, entries, snapshot, listed) -> tuple:
    result, offers = [], {}
    for row in rows:
        offer = lane_effort.offered_levels(row.runtime, row.model_id, entries, snapshot,
                                           listed=listed[row.runtime])
        offers[(row.key, row.runtime)] = offer
        result.append(row._replace(efforts=offer.levels))
    return result, offers


def _ranked(args, judge, split, entries, snapshot) -> tuple:
    all_rows = split.pool + split.unknown + split.wider
    listed = {rid: lane_effort.listed_ids(rid, entries, snapshot)
              for rid in {row.runtime for row in all_rows}}
    candidates, offers = _offers(split.pool + split.unknown, entries, snapshot, listed)
    wider, wider_offers = _offers(split.wider, entries, snapshot, listed)
    offers.update(wider_offers)
    prices = {(row.key, row.runtime): lane_price.price_of(
        row.key, row.entry, row.model_id, lane_pool.snapshot_cli(snapshot, row.runtime),
        row.runtime)
        for row in candidates + wider}
    weights = model_ranker.load_ranking_weights()
    zero = {key for key, price in prices.items() if price.state == "zero"}
    return (lane_order.rank(candidates, args.purpose, weights, judge, zero),
            lane_order.deterministic_order(wider, args.purpose, weights), prices, offers)


def _row_json(rank: int, item, price, offer) -> dict:
    row = item.row
    return {"rank": rank, "key": row.key, "runtime": row.runtime, "model_id": row.model_id,
            "tier": row.tier, "class": row.klass, "class_label": row.klass,
            "cost_band": row.cost_band, "strengths": list(row.strengths),
            "efforts": list(offer.levels), "efforts_refused": [list(x) for x in offer.refused],
            "efforts_source": offer.source, "usability": row.usability,
            "score": round(item.score, 1), "ranked_by": item.ranked_by,
            "ranker_reason": item.reason,
            "price": {**price._asdict(), "sources": list(price.sources)},
            "pool_key": lane_price.pool_key(row.model_id, row.entry.get("provider"))
            if price.state == "zero" else None, "data_use_needed": price.state == "zero"}


def _alias_json(row, note) -> dict:
    return {"key": row.key, "runtime": row.runtime, "model_id": row.model_id,
            "label": lane_pool.ALIAS_LABEL, "purpose_note": note}


def _render(items, prices, offers) -> list:
    return [_row_json(i, item, prices[(item.row.key, item.row.runtime)],
                      offers[(item.row.key, item.row.runtime)]) for i, item in enumerate(items, 1)]


def _alternative(pool, filters):
    avoid, skip = filters
    return next((row for row in pool if row["pool_key"] not in avoid
                 and (row["runtime"], row["key"]) not in skip), None)


def _proposal(args, judge, inputs, filters) -> dict:
    entries, snapshot, fresh = inputs
    # A catalog written before a runtime was removed still holds its rows (39.1 D-03).
    rows = [row for row in lane_pool.build_rows(
        entries, snapshot, tuple(args.runtime) if args.runtime else None)
        if row.runtime not in detection.REMOVED_RUNTIMES]
    split = lane_pool.split_pools(rows, args.purpose, snapshot, entries, fresh)
    ranked, wider_pairs, prices, offers = _ranked(args, judge, split, entries, snapshot)
    pool = _render(ranked, prices, offers)
    wider = _render([lane_order.Ranked(row, score, None, None, "scorer", WIDER_REASON, False)
                     for row, score in wider_pairs], prices, offers)
    return {"purpose": args.purpose, "default_view": DEFAULT_VIEW,
            "ranking": "jev" if any(x.ranked_by == "jev" for x in ranked) else "scorer",
            "jev": {"requested": args.jev, "found": judge is not None,
                    "asked": sum(x.asked for x in ranked),
                    "answered": sum(x.ranked_by == "jev" for x in ranked),
                    "window": lane_order.JEV_WINDOW, "stable_top": lane_order.STABLE_TOP},
            "stale_checked": fresh, "pool": pool,
            "zero_price": [{**row, "group_rank": i} for i, row in enumerate(
                [row for row in pool if row["price"]["state"] == "zero"][:ZERO_GROUP_MAX], 1)],
            "aliases": [_alias_json(row, note) for row, note in split.aliases], "wider": wider,
            "alternative": _alternative(pool, filters), "empty": not pool,
            "message": EMPTY_POOL if not pool else ""}


def cmd_propose_lanes(args, deps) -> int:
    avoid, skip, problem = _filters(args)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    entries, snapshot, fresh, problem = _load(args, deps)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    judge = deps.score_judge_fn(deps.env_fn()) if args.jev else None
    print(json.dumps(_proposal(args, judge, (entries, snapshot, fresh), (avoid, skip))))
    return 0


def register_parsers(sub) -> None:
    parser = sub.add_parser("propose-lanes")
    parser.add_argument("--purpose", choices=("review", "execute"), required=True)
    parser.add_argument("--catalog-path", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--detect", action="store_true")
    group.add_argument("--runtimes-json")
    parser.add_argument("--runtime", action="append", default=None)
    parser.add_argument("--jev", action="store_true")
    parser.add_argument("--avoid-pool", action="append", default=[])
    parser.add_argument("--skip", action="append", default=[])


COMMANDS = {"propose-lanes": cmd_propose_lanes}
