"""Pre-round ping: probe every chosen lane at once, replace a blocked one from the owner's order,
record each lane in the round log."""

import argparse
import concurrent.futures
import json
import subprocess
import sys
import time
from collections.abc import Callable
from typing import NamedTuple

from ai_kit_spec import config_io, lane_switch, quota, review_log, reviewer_dispatch
from ai_kit_spec.cache import cache_read_json, cache_write_json
from ai_kit_spec.error_classifier import NO_LANE_LEFT, PING_TIMEOUT, REASONS, REPLACED

PING_TIMEOUT_S = 30
PING_GRACE_S = 5
PING_EXIT_NO_LANE = 3


class PingSeams(NamedTuple):
    probe_fn: Callable[..., dict] = quota.probe_reviewer_quota
    now_fn: Callable[[], float] = time.time
    route_fn: Callable[[str], str | None] = lambda _key: None
    clock_fn: Callable[[], float] = time.monotonic
    read_fn: Callable[[str], object] = lambda _pool: None
    decisions: dict | None = None


class PingRun(NamedTuple):
    config: dict
    reviewers: list
    round_no: int
    events: list
    cache: dict
    probe_seams: quota.ProbeSeams


class PingOutcome(NamedTuple):
    reviewers: list
    lines: list
    events: list
    cache: dict
    stop: str


def _reason(entry) -> str:
    reason = quota.entry_reason(entry) or "real_error"
    if reason == "timeout":
        return PING_TIMEOUT
    return reason if reason in REASONS else "real_error"


def _skip_status(run, row, now) -> str | None:
    if reviewer_dispatch.row_is_native(row):
        return "ok"
    event = review_log.round_states(run.events, run.round_no - 1).get(row["key"], {})
    at = event.get("at")
    if (run.round_no > 1 and event.get("state") == "judged"
            and isinstance(at, (int, float)) and not isinstance(at, bool)
            and now - at < quota.QUOTA_TTL_SECONDS):
        return "fresh"
    return None


def _lane(run, row) -> dict:
    return (lane_switch.review_lane(run.config, row["key"])
            or {**(row.get("extra") or {}), "key": row["key"]})


def _bounded(fn, calls: dict, timeout_s: float) -> dict:
    """Run fn(*args) for every key at once, one worker each, and wait at most timeout_s plus the
    grace; key -> future. Threads are never stopped: an unfinished future is just not done."""
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(calls))
    try:
        futures = {key: executor.submit(fn, *args) for key, args in calls.items()}
        concurrent.futures.wait(list(futures.values()), timeout=timeout_s + PING_GRACE_S)
        return futures
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _read_pools(pools, seams, timeout_s) -> dict:
    """Read each pool once, concurrently. Each read is a runner child killed at `timeout_s`;
    the wait only classifies. An unfinished or raising read is absent (no record)."""
    if not pools:
        return {}
    futures = _bounded(seams.read_fn, {pool: (pool,) for pool in sorted(pools)}, timeout_s)
    return {pool: future.result() for pool, future in futures.items()
            if future.done() and future.exception() is None}


def _ping_one(row, run, seams) -> dict:
    """One bounded worker. The probe gets the whole per-ping timeout from its own start (a pool
    read before it has its own bound); a lane ends within that timeout handed to the runner plus
    the runner's own kill grace; the thread waits only classify."""
    begin = seams.clock_fn()
    try:
        # A blocked pool is never probed; an expired pool is retried by one lane only.
        decision, detail = (seams.decisions or {}).get(row["key"], ("none", ""))
        if decision in ("blocked", "expired-wait"):
            return lane_switch.quota_entry(seams.now_fn(), detail)
        entry = seams.probe_fn(reviewer_dispatch.row_resolved(row), run.probe_seams)
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return lane_switch.unavailable_entry(seams.now_fn(), "real_error", type(exc).__name__)
    if seams.clock_fn() - begin >= run.probe_seams.timeout_s:
        return lane_switch.unavailable_entry(seams.now_fn(), PING_TIMEOUT,
                                             "ping deadline reached")
    return entry


def _probe_all(rows: dict, run, seams) -> dict:
    """Classify within the deadline, without stopping threads; runner kill grace bounds probes.

    The process exits once its last probe has ended.
    """
    if not rows:
        return {}
    futures = _bounded(_ping_one, {key: (row, run, seams) for key, row in rows.items()},
                       run.probe_seams.timeout_s)
    entries = {}
    for key, future in futures.items():
        try:
            entry = (future.result() if future.done() else
                     lane_switch.unavailable_entry(seams.now_fn(), PING_TIMEOUT,
                                                   "ping deadline reached"))
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            entry = lane_switch.unavailable_entry(seams.now_fn(), "real_error",
                                                  type(exc).__name__)
        entries[key] = {**entry, "checked_at": seams.now_fn()}
    return entries


def _statuses(run, seams, now) -> tuple[dict, dict]:
    rows = {row["key"]: row for row in reversed(run.reviewers)}
    keys = list(dict.fromkeys(row["key"] for row in run.reviewers))
    lanes = [_lane(run, rows[key]) for key in keys
             if not reviewer_dispatch.row_is_native(rows[key])]
    pool_of = lane_switch.pool_keys(lanes)
    decisions: dict = {}
    if pool_of:
        reads = _read_pools(set(pool_of.values()), seams, run.probe_seams.timeout_s)
        decisions = lane_switch.pool_decisions(lanes, [lane["key"] for lane in lanes], now,
                                               reads.get)
        seams = seams._replace(decisions=decisions)
    statuses = {key: (None if decisions.get(key, ("none",))[0] != "none"
                      else _skip_status(run, row, now)) for key, row in rows.items()}
    waiting = {key for key, (decision, _detail) in decisions.items() if decision == "expired-wait"}
    entries = _probe_all({key: rows[key] for key, status in statuses.items()
                          if status is None and key not in waiting}, run, seams)
    entries.update(_after_retry(run, seams, pool_of, entries, rows))
    for key, entry in entries.items():
        statuses[key] = "ok" if entry.get("available") else _reason(entry)
    return statuses, entries


def _after_retry(run, seams, pool_of, entries, rows) -> dict:
    """A lane waiting on an expired pool is probed once that pool's retrying lane came back
    available, and gets an unavailable `quota` entry otherwise."""
    decisions = seams.decisions or {}
    waiting = [key for key, (decision, _detail) in decisions.items() if decision == "expired-wait"]
    cleared = {pool_of[key] for key, (decision, _detail) in decisions.items()
               if decision == "expired-retry" and entries.get(key, {}).get("available")}
    probed = _probe_all({key: rows[key] for key in waiting if pool_of[key] in cleared},
                        run, seams._replace(decisions={}))
    return {key: probed.get(key) or lane_switch.quota_entry(seams.now_fn(), decisions[key][1])
            for key in waiting}


def _replace(run, seams, key, reason, state) -> str | None:
    for _ in range(len(run.config.get("review", []))):
        candidate = lane_switch.next_lane(run.config, key, state["exclude"], seams.route_fn)
        if candidate is None:
            return None
        state["exclude"].add(candidate)
        row = lane_switch.replacement_row(run.config, candidate, seams.route_fn)
        entry = ({"available": True} if reviewer_dispatch.row_is_native(row) else
                 _probe_all({candidate: row}, run, seams)[candidate])
        if not reviewer_dispatch.row_is_native(row):
            state["cache"][candidate] = entry
        if entry.get("available"):
            state["events"].append(review_log.lane_event(
                run.round_no, key, "replaced", state["now"], REPLACED, cause=reason,
                by=candidate))
            state["events"].append(
                review_log.lane_event(run.round_no, candidate, "chosen", state["now"]))
            return candidate
        state["events"].append(review_log.lane_event(
            run.round_no, candidate, "failed", state["now"], _reason(entry)))
    return None


def _stop_text(failed) -> str:
    return ", ".join(f"{key} ({reason})" for key, reason in failed) or "(empty reviewers file)"


def ping_lanes(run: PingRun, seams: PingSeams | None = None) -> PingOutcome:
    seams = seams or PingSeams()
    now = seams.now_fn()
    statuses, entries = _statuses(run, seams, now)
    exclude = {row["key"] for row in run.reviewers}
    exclude.update(key for key, event in review_log.round_states(run.events, run.round_no).items()
                   if event["state"] in ("failed", "replaced"))
    state = {"exclude": exclude, "events": [], "cache": {**run.cache, **entries}, "now": now}
    rows, lines, failed, seen = [], [], [], {}
    for row in run.reviewers:
        key = row["key"]
        if key in seen:
            if seen[key] is not None:
                rows.append(seen[key])
            continue
        status = statuses[key]
        if status in ("ok", "fresh"):
            rows.append(row)
            seen[key] = row
            state["events"].append(review_log.lane_event(run.round_no, key, "chosen", now))
            lines.append(f"ping {key}: {status}")
            continue
        replacement = _replace(run, seams, key, status, state)
        if replacement is not None:
            seen[key] = lane_switch.replacement_row(run.config, replacement, seams.route_fn)
            rows.append(seen[key])
            lines.append(f"ping {key}: replaced by {replacement} ({status})")
        else:
            seen[key] = None
            failed.append((key, status))
            state["events"].append(
                review_log.lane_event(run.round_no, key, "failed", now, status))
            lines.append(f"ping {key}: failed ({status})")
    return PingOutcome(rows if rows else run.reviewers, lines, state["events"],
                       state["cache"], _stop_text(failed) if not rows else "")


def cmd_ping_lanes(args, deps) -> int:
    config = config_io.cfg_resolve(args.cwd, deps.env_fn(), migrate=False)
    try:
        return _ping_command(args, deps, config)
    except config_io.ConfigError:
        raise  # cli.main turns a config error into its own exit 2 message
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ping-lanes: {error!r}", file=sys.stderr)
        return 2


def _ping_command(args, deps, config) -> int:
    with open(args.reviewers_json, encoding="utf-8") as stream:
        reviewers = json.load(stream)
    run = PingRun(config, reviewers, args.round, review_log.read_events(args.lane_log),
                  cache_read_json(args.quota_path) or {},
                  deps.probe_seams()._replace(timeout_s=args.timeout, role="review"))
    outcome = ping_lanes(run, PingSeams(route_fn=lane_switch.lazy_routes(config, deps),
                                        read_fn=lane_switch.blocked_reader(
                                            deps, timeout_s=args.timeout)))
    for event in outcome.events:
        review_log.append_event(args.lane_log, event)
    cache_write_json(args.quota_path, outcome.cache)
    for line in outcome.lines:
        print(line)
    if outcome.stop:
        review_log.append_event(args.lane_log, {"round": args.round, "stop": NO_LANE_LEFT,
                                                "at": time.time()})
        print(f"ai-kit-spec: no lane left: {outcome.stop}", file=sys.stderr)
        return PING_EXIT_NO_LANE
    if outcome.reviewers != reviewers:
        lane_switch.write_rows(args.reviewers_json, outcome.reviewers)
    return 0


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{text} is not a positive integer") from exc
    if value < 1:
        raise argparse.ArgumentTypeError(f"{text} is not a positive integer")
    return value


def register_parsers(sub) -> None:
    parser = sub.add_parser(
        "ping-lanes", help="ping every chosen lane before a round and replace a blocked one "
        "from the review order")
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--reviewers-json", required=True)
    parser.add_argument("--lane-log", required=True)
    parser.add_argument("--round", required=True, type=_positive_int)
    parser.add_argument("--quota-path", required=True)
    parser.add_argument("--timeout", type=_positive_int, default=PING_TIMEOUT_S,
                        help="seconds handed to each probe's runner (default 30); a probe ends "
                        "within that plus the runner's kill grace")


COMMANDS = {"ping-lanes": cmd_ping_lanes}
