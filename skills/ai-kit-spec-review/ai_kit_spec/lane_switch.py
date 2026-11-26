"""Lane selection shared by the pre-round ping and the flagged-lane switch: always inside the
owner's review roster and order."""

import functools
import json
import re
import subprocess
import sys
import time
from datetime import UTC, datetime

from ai_kit_spec import (
    cache,
    config_io,
    detection,
    lane_settings,
    quota,
    review_log,
    role_orders,
    routing,
    runner_dispatch,
)
from ai_kit_spec.error_classifier import REPLACED

BLOCKED_STATUS_FLAG = "--blocked-status"
_STATUS_RE = re.compile(
    r"^blocked_until=(-|\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) failures=\d+$")


def review_lane(config: dict, key) -> dict | None:
    """The roster's review lane with this key, or None."""
    return next((item for item in config.get("review", [])
                 if isinstance(item, dict) and item.get("key") == key), None)


def _route(config: dict, key: str, route_fn) -> str | None:
    route = route_fn(key)
    if route is not None:
        return route
    lane = review_lane(config, key) or {}
    command = lane.get("command")
    return ("custom" if isinstance(command, str) and command and lane.get("runtime") is None
            else None)


def next_lane(config: dict, base_key: str, exclude, route_fn) -> str | None:
    ordered = lane_settings.selectable_lanes("review", config.get("review"),
                                             role_orders.role_order(config, "review"))
    if base_key not in {lane["key"] for lane in ordered}:
        return None
    excluded = set(exclude) - {base_key}
    for _ in ordered:
        pick = lane_settings.lane_fallback([lane for lane in ordered
                                            if lane["key"] not in excluded], base_key)
        if pick is None:
            return None
        route = _route(config, pick, route_fn)
        if route is not None and route not in routing.SKIP_ROUTES:
            return pick
        excluded.add(pick)
    return None


def _parse_status(text: str) -> datetime | None:
    """The blocked-until time of the runner's one status line; None for no record or any
    other shape (the runner's own status trailer goes to stderr)."""
    lines = (text or "").strip().splitlines()
    match = _STATUS_RE.match(lines[0]) if len(lines) == 1 else None
    if match is None or match.group(1) == "-":
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def blocked_until(pool: str, seams=None, run_fn=detection.run_in_own_group,
                  timeout_s: int = runner_dispatch.PREVIEW_TIMEOUT_S) -> datetime | None:
    """Read a pool's blocked-until time only through `cross-ai.mjs --blocked-status <pool>`.
    A missing node or runner, a failed call or a bad record gives None and never blocks."""
    if not lane_settings.POOL_RX.fullmatch(pool):
        return None
    run = detection.bounded_run(run_fn)
    active = seams or runner_dispatch.RunnerSeams()
    node = active.which_fn("node")
    template = active.runner_path_fn()
    if not node or not template:
        return None
    try:
        proc = run([node, template, BLOCKED_STATUS_FLAG, pool],
                   stdin=subprocess.DEVNULL, capture_output=True, text=True,
                   timeout=timeout_s,
                   env=runner_dispatch.child_env(env=active.env_fn()), check=False)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if proc.returncode != 0:
        return None
    return _parse_status(proc.stdout)


def unavailable_entry(now_s: float, reason: str, detail: str) -> dict:
    """An unavailable probe entry."""
    return {"available": False, "checked_at": now_s, "reason": reason, "detail": detail,
            "answered": False}


def quota_entry(now_s: float, detail: str) -> dict:
    """The unavailable `quota` probe entry."""
    return unavailable_entry(now_s, "quota", detail)


def pool_status(lane: dict, now_s: float, reader) -> tuple[str, str]:
    """(state, detail) of a flagged lane's pool: none, blocked or expired; a time equal to
    now counts as passed. The reader is never called for a lane without a flagged pool."""
    pool = lane_settings.lane_free_pool(lane)
    if pool is None:
        return ("none", "")
    until = reader(pool)
    if until is None:
        return ("none", "")
    if until.timestamp() > now_s:
        stamp = until.strftime("%Y-%m-%dT%H:%M:%SZ")
        return ("blocked", f"pool {pool} blocked until {stamp}")
    return ("expired", f"pool {pool} retried by another lane")


def pool_keys(lanes: list) -> dict:
    """key -> pool for each lane with a flagged pool, in input order (config only)."""
    return {lane["key"]: pool for lane in lanes
            if isinstance(lane, dict) and "key" in lane
            and (pool := lane_settings.lane_free_pool(lane)) is not None}


def pool_decisions(lanes: list, order: list, now_s: float, reader) -> dict:
    """key -> (decision, detail) for each flagged pooled key of `order`: one read per pool; an
    expired pool is retried by its first key (expired-retry), later keys wait (expired-wait)."""
    by_key = {lane["key"]: lane for lane in lanes if isinstance(lane, dict) and "key" in lane}
    read = functools.cache(reader)
    retried: set = set()
    decisions: dict = {}
    for key in order:
        lane = by_key.get(key)
        if key in decisions or lane is None or lane_settings.lane_free_pool(lane) is None:
            continue
        state, detail = pool_status(lane, now_s, read)
        if state == "expired":
            pool = lane_settings.lane_free_pool(lane)
            state = "expired-wait" if pool in retried else "expired-retry"
            retried.add(pool)
        decisions[key] = (state, detail)
    return decisions


def blocked_reader(deps, timeout_s: int = runner_dispatch.PREVIEW_TIMEOUT_S):
    """A pool reader over the dependency seams: pool name -> blocked-until time or None."""
    return functools.partial(
        blocked_until,
        seams=runner_dispatch.RunnerSeams(which_fn=deps.which_fn, env_fn=deps.env_fn),
        run_fn=deps.run_fn, timeout_s=timeout_s)


def blocked_cache_entries(lanes: list, ladder: list, existing: dict, now_s: float,
                          reader) -> dict:
    """The Step 0.7 rule for blocked pools: a flagged pooled lane on the ladder whose pool is
    still blocked gets an unavailable `quota` entry stamped now; an expired pool is tried once by
    its first lane (any cached entry dropped) while its other lanes wait; a cleared record drops a
    cached `quota` failure so the lane is probed once. Other lanes and reasons stay untouched."""
    updated = dict(existing)
    for key, (decision, detail) in pool_decisions(lanes, ladder, now_s, reader).items():
        if decision in ("blocked", "expired-wait"):
            updated[key] = quota_entry(now_s, detail)
        elif decision == "expired-retry":
            updated.pop(key, None)
        else:
            cached = updated.get(key)
            if (isinstance(cached, dict) and cached.get("available") is False
                    and cached.get("reason") == "quota"):
                del updated[key]
    return updated


def flagged_replacement(config: dict, key: str, reason, exclude, route_fn) -> str | None:
    """The owner's flag alone permits a switch after quota; other lanes or reasons do not."""
    if reason != "quota":
        return None
    lane = review_lane(config, key)
    if lane is None:
        return None
    try:
        limited = lane_settings.lane_usage_limit(lane).limited
    except lane_settings.LaneSettingError:
        return None
    return next_lane(config, key, exclude, route_fn) if limited else None


def _refusal(row: dict, states: dict, config: dict) -> str | None:
    last = states.get(row.get("key"))
    if last is None:
        return "no record"
    if last["state"] != "failed":
        return last["state"]
    lane = review_lane(config, row.get("key"))
    if lane is None:
        return "lane changed"
    resolved = quota.to_resolved(lane)
    if any(getattr(resolved, field) != row.get(field) for field in ("runtime", "model", "command")):
        return "lane changed"
    return None


def replacement_row(config: dict, key: str, route_fn) -> dict:
    lane = review_lane(config, key)
    if lane is None:
        raise KeyError(key)
    row = dict(quota.to_resolved(lane)._asdict())
    row["route"] = _route(config, key, route_fn)
    return row


def write_rows(path: str, rows: list) -> None:
    cache.cache_write_bytes(path, json.dumps(rows).encode("utf-8"), mode=0o600)


def review_routes(config: dict, deps) -> dict:
    seams = routing.RuntimesSeams(deps.which_fn, deps.run_fn, deps.popen_fn, deps.urlopen_fn)
    return routing.route_all([lane for lane in config.get("review", []) if isinstance(lane, dict)],
                             routing.host_context("review", deps.env_fn(), seams, False))


def lazy_routes(config: dict, deps):
    """A route lookup that runs route discovery only on its first call."""
    routes = None

    def route(key):
        nonlocal routes
        if routes is None:
            routes = review_routes(config, deps)
        return routes.get(key)
    return route


def cmd_switch_lane(args, deps) -> int:
    """One writer at a time: callers serialize switches and re-read rows after each call."""
    if args.round < 1 or args.index < 0:
        print("switch-lane: --round must be >= 1 and --index >= 0", file=sys.stderr)
        return 2
    try:
        return _switch_lane(args, deps)
    except config_io.ConfigError:
        raise  # cli.main turns a config error into its own exit 2 message
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"switch-lane: {error!r}", file=sys.stderr)
        return 2


def _switch_lane(args, deps) -> int:
    with open(args.reviewers_json, encoding="utf-8") as stream:
        reviewers = json.load(stream)
    if args.index >= len(reviewers):
        print(f"switch-lane: no reviewer at index {args.index}", file=sys.stderr)
        return 1
    old = reviewers[args.index]["key"]
    states = review_log.round_states(review_log.read_events(args.lane_log), args.round)
    config = config_io.cfg_resolve(args.cwd, deps.env_fn(), migrate=False)
    refusal = _refusal(reviewers[args.index], states, config)
    if refusal is not None:
        print(f"not switched {old}: {refusal}")
        return 1
    last = states[old]
    route = lazy_routes(config, deps)
    exclude = {row["key"] for row in reviewers} | {
        key for key, event in states.items() if event["state"] in ("failed", "replaced")}
    new = flagged_replacement(config, old, last.get("reason"), exclude, route)
    if new is None:
        print(f"not switched {old}: {last.get('reason')}")
        return 1
    reviewers[args.index] = replacement_row(config, new, route)
    now = time.time()
    # Log first, in one write: a failed append leaves reviewers.json and the round log as they were.
    review_log.append_event(
        args.lane_log,
        review_log.lane_event(args.round, old, "replaced", now, REPLACED, cause="quota", by=new),
        review_log.lane_event(args.round, new, "chosen", now))
    write_rows(args.reviewers_json, reviewers)
    print(f"switched {old} -> {new}")
    return 0


def register_parsers(sub) -> None:
    parser = sub.add_parser(
        "switch-lane", help="switch a usage_limited lane that failed with quota "
        "to its fallback in the review order")
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--reviewers-json", required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--lane-log", required=True)
    parser.add_argument("--round", type=int, required=True)


COMMANDS = {"switch-lane": cmd_switch_lane}
