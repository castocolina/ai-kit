"""ping-lanes: the pre-round ping, replacement from the owner's order, cadence and the stop
(fake lanes only)."""

import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from unittest import mock

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import cli, config_io, lane_ping, lane_switch, quota, review_log
from ai_kit_spec.commands import ResolvedReviewer
from ai_kit_spec.runner_dispatch import RunnerResult

ROSTER = '''[[lanes.review]]
key = "lane-a"
model = "placeholder-model-1"
command = "placeholder-cli-1 {model}"
[[lanes.review]]
key = "lane-b"
model = "placeholder-model-2"
command = "placeholder-cli-1 {model}"
[[lanes.review]]
key = "lane-c"
model = "placeholder-model-3"
command = "placeholder-cli-1 {model}"
[lanes.policy.review]
ladder = ["lane-a", "lane-b", "lane-c"]
'''


CONFIG = {"review": [{"key": f"lane-{letter}", "model": f"placeholder-model-{index}",
                      "command": "placeholder-cli-1 {model}"}
                     for index, letter in enumerate("abc", 1)],
          "orders": {"review": ["lane-a", "lane-b", "lane-c"]}}
OK = {"available": True, "checked_at": 0.0, "reason": None, "detail": "", "answered": True}


def row(key):
    return {**next(item for item in CONFIG["review"] if item["key"] == key),
            "vendor": "", "runtime": None, "extra": {}, "route": "custom"}


def run(rows, round_no=1, events=(), cache=None, timeout_s=30):
    return lane_ping.PingRun(CONFIG, rows, round_no, list(events), dict(cache or {}),
                             quota.ProbeSeams(timeout_s=timeout_s))


def blocked(reason):
    return {"available": False, "checked_at": 0.0, "reason": reason, "detail": "",
            "answered": False}


class TestPingTimeout(unittest.TestCase):
    def test_probe_seams_timeout_reaches_both_spawn_paths(self):
        seen = {}

        def runner(spec, prompt, seams):
            seen["runner"] = spec.timeout_s
            return RunnerResult(0, "ok", {}, None, False, ["fake"], "")

        def custom(spec, prompt, seams):
            seen["custom"] = spec.timeout_tiers
            return RunnerResult(0, "ok", {}, None, False, ["fake"], "")

        seams = quota.ProbeSeams(runner_fn=runner, custom_fn=custom, timeout_s=7)
        quota.probe_reviewer_quota(ResolvedReviewer("a", "fake/placeholder-model-1", "",
                                                    "codex", None, {}), seams)
        quota.probe_reviewer_quota(ResolvedReviewer("b", "placeholder-model-1", "", None,
                                                    "placeholder-cli-1 {model}", {}), seams)
        self.assertEqual(seen, {"runner": 7, "custom": [7]})

    def test_two_lanes_ping_concurrently(self):
        def probe(resolved, seams):
            time.sleep(2)
            return OK

        start = time.monotonic()
        outcome = lane_ping.ping_lanes(run([row("lane-a"), row("lane-b")]),
                                       lane_ping.PingSeams(probe_fn=probe, now_fn=lambda: 1000.0))
        self.assertLess(time.monotonic() - start, 3.5)
        self.assertEqual(outcome.lines, ["ping lane-a: ok", "ping lane-b: ok"])

    def test_a_ping_at_its_deadline_is_ping_timeout(self):
        release = threading.Event()
        self.addCleanup(release.set)

        def probe(resolved, seams):
            if resolved.key == "lane-a":
                release.wait(30)
            return OK

        with mock.patch.object(lane_ping, "PING_GRACE_S", 0):
            outcome = lane_ping.ping_lanes(run([row("lane-a"), row("lane-b")], timeout_s=1),
                                           lane_ping.PingSeams(probe_fn=probe))
        self.assertEqual(outcome.lines[0], "ping lane-a: replaced by lane-c (ping_timeout)")
        self.assertEqual(outcome.events[0]["cause"], "ping_timeout")

    def test_probe_timeout_reason_reads_ping_timeout(self):
        def probe(resolved, seams):
            return blocked("timeout") if resolved.key == "lane-a" else OK

        outcome = lane_ping.ping_lanes(run([row("lane-a"), row("lane-b")]),
                                       lane_ping.PingSeams(probe_fn=probe))
        self.assertEqual(outcome.lines[0], "ping lane-a: replaced by lane-c (ping_timeout)")

    def test_result_finished_at_the_deadline_is_ping_timeout(self):
        state = {"t": 0.0}

        def probe(resolved, seams):
            if resolved.key == "lane-a":
                state["t"] += 5.0
            return OK

        outcome = lane_ping.ping_lanes(run([row("lane-a")], timeout_s=5),
                                       lane_ping.PingSeams(probe_fn=probe,
                                                           clock_fn=lambda: state["t"]))
        self.assertEqual(outcome.lines[0], "ping lane-a: replaced by lane-b (ping_timeout)")
        self.assertEqual(outcome.reviewers[0]["key"], "lane-b")

    def test_one_raising_probe_fails_only_its_lane(self):
        def probe(resolved, seams):
            if resolved.key == "lane-a":
                raise OSError("boom")
            return OK

        outcome = lane_ping.ping_lanes(run([row("lane-a"), row("lane-b")]),
                                       lane_ping.PingSeams(probe_fn=probe))
        self.assertEqual(outcome.lines, ["ping lane-a: replaced by lane-c (real_error)",
                                         "ping lane-b: ok"])

    def test_rejected_candidate_gets_its_own_failed_event(self):
        config = {"review": [*CONFIG["review"], {"key": "lane-d", "model": "placeholder-model-4",
                                                 "command": "placeholder-cli-1 {model}"}],
                  "orders": {"review": [*CONFIG["orders"]["review"], "lane-d"]}}

        def probe(resolved, seams):
            return {"lane-b": blocked("quota"), "lane-c": blocked("auth")}.get(resolved.key, OK)

        outcome = lane_ping.ping_lanes(run([row("lane-a"), row("lane-b")])._replace(config=config),
                                       lane_ping.PingSeams(probe_fn=probe))
        self.assertEqual(outcome.lines[1], "ping lane-b: replaced by lane-d (quota)")
        self.assertTrue(any(event["key"] == "lane-c" and event["state"] == "failed"
                            and event["reason"] == "auth" and event["round"] == 1
                            for event in outcome.events))

    def test_timeout_must_be_positive(self):
        base = ["ping-lanes", "--cwd", "unused", "--reviewers-json", "unused",
                "--lane-log", "unused", "--quota-path", "unused"]
        for args in (["--round", "1", "--timeout", "0"],
                     ["--round", "1", "--timeout", "-3"],
                     ["--round", "0", "--timeout", "1"]):
            with self.subTest(args=args), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    cli.main(base + args)
                self.assertEqual(caught.exception.code, 2)


class TestPingLanes(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.cwd = os.path.join(tmp.name, "project")
        os.makedirs(self.cwd)
        self.env = {"HOME": os.path.join(tmp.name, "home"),
                    "XDG_CONFIG_HOME": os.path.join(tmp.name, "xdg"),
                    "XDG_CACHE_HOME": os.path.join(tmp.name, "cache")}
        path = config_io.cfg_global_path(self.env)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(ROSTER)
        self.reviewers = os.path.join(tmp.name, "reviewers.json")
        self.log = os.path.join(tmp.name, "lanes.jsonl")
        self.quota = os.path.join(tmp.name, "quota.json")

    def _rows(self, keys):
        rows = [{"key": key, "model": f"placeholder-model-{ord(key[-1]) - 96}",
                 "vendor": "", "runtime": None, "command": "placeholder-cli-1 {model}",
                 "extra": {}, "route": "custom"} for key in keys]
        with open(self.reviewers, "w", encoding="utf-8") as stream:
            json.dump(rows, stream)

    def _read(self, path):
        with open(path, encoding="utf-8") as stream:
            return json.load(stream)

    def _ping(self, blocked):
        def fake(spec, prompt, seams):
            if spec.key in blocked:
                return RunnerResult(1, "", {"status": "quota"}, "quota", False, ["fake"], "quota")
            return RunnerResult(0, "Hello world!", {"status": "ok"}, None, False, ["fake"], "")

        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["ping-lanes", "--cwd", self.cwd, "--reviewers-json", self.reviewers,
                             "--lane-log", self.log, "--round", "1", "--quota-path", self.quota],
                            custom_fn=fake, runner_fn=fake, env_fn=lambda: dict(self.env),
                            which_fn=lambda *_a, **_k: None, run_fn=lambda *_a, **_k: None)
        return code, out.getvalue(), err.getvalue()

    def test_one_blocked_lane_of_two_is_replaced_and_both_slots_fill(self):
        self._rows(["lane-a", "lane-b"])
        code, out, _ = self._ping({"lane-b"})
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), ["ping lane-a: ok",
                                          "ping lane-b: replaced by lane-c (quota)"])
        self.assertEqual([row["key"] for row in self._read(self.reviewers)], ["lane-a", "lane-c"])
        states = review_log.round_states(review_log.read_events(self.log), 1)
        self.assertEqual(states["lane-a"]["state"], "chosen")
        self.assertEqual(states["lane-b"]["state"], "replaced")
        self.assertEqual(states["lane-b"]["cause"], "quota")
        self.assertEqual(states["lane-b"]["by"], "lane-c")
        self.assertEqual(states["lane-c"]["state"], "chosen")
        self.assertEqual(set(self._read(self.quota)), {"lane-a", "lane-b", "lane-c"})

    def test_both_blocked_with_no_fallback_stops_without_change(self):
        self._rows(["lane-a", "lane-b"])
        with open(self.reviewers, "rb") as stream:
            before = stream.read()
        code, _, err = self._ping({"lane-a", "lane-b", "lane-c"})
        self.assertEqual(code, 3)
        self.assertIn("ai-kit-spec: no lane left: lane-a (quota), lane-b (quota)", err)
        with open(self.reviewers, "rb") as stream:
            self.assertEqual(stream.read(), before)
        event = review_log.read_events(self.log)[-1]
        self.assertEqual(event["round"], 1)
        self.assertEqual(event["stop"], "no_lane_left")

    def test_empty_reviewers_file_exits_3(self):
        self._rows([])
        code, _, err = self._ping(set())
        self.assertEqual(code, 3)
        self.assertIn("ai-kit-spec: no lane left: (empty reviewers file)", err)
        self.assertEqual(self._read(self.reviewers), [])

    def test_unreadable_input_exits_2(self):
        for text in ("{not json", '[{"model": "placeholder-model-1"}]'):
            with self.subTest(text=text):
                with open(self.reviewers, "w", encoding="utf-8") as stream:
                    stream.write(text)
                code, out, err = self._ping(set())
                self.assertEqual((code, out), (2, ""))
                self.assertTrue(err.startswith("ping-lanes: "), err)


class TestPingCadence(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.entries = {}

    def probe(self, resolved, seams):
        self.calls.append(resolved.key)
        return self.entries.get(resolved.key, OK)

    def ping(self, ping_run):
        return lane_ping.ping_lanes(ping_run, lane_ping.PingSeams(
            probe_fn=self.probe, now_fn=lambda: 10000.0))

    def test_lane_judged_last_round_is_fresh_and_a_failed_lane_is_pinged(self):
        events = [{"round": 1, "key": "lane-a", "state": "judged", "at": 9990.0},
                  {"round": 1, "key": "lane-b", "state": "failed", "reason": "quota",
                   "at": 9990.0}]
        outcome = self.ping(run([row("lane-a"), row("lane-b")], 2, events))
        self.assertEqual(self.calls, ["lane-b"])
        self.assertEqual(outcome.lines, ["ping lane-a: fresh", "ping lane-b: ok"])

    def test_ttl_edges(self):
        for at, expected in ((10000.0 - (quota.QUOTA_TTL_SECONDS - 1), []),
                             (10000.0 - (quota.QUOTA_TTL_SECONDS + 1), ["lane-a"]),
                             ("x", ["lane-a"]), (None, ["lane-a"])):
            with self.subTest(at=at):
                self.calls.clear()
                event = {"round": 1, "key": "lane-a", "state": "judged"}
                if at is not None:
                    event["at"] = at
                outcome = self.ping(run([row("lane-a")], 2, [event]))
                self.assertEqual(self.calls, expected)
                self.assertEqual(outcome.lines, ["ping lane-a: ok" if expected
                                                 else "ping lane-a: fresh"])

    def test_round_one_probes_despite_a_fresh_cache_success(self):
        events = [{"round": 0, "sizing": {"lanes": 2, "keys": ["lane-a", "lane-b"],
                                          "reason": "signal security"}, "at": 9000.0}]
        cache = {"lane-a": {**OK, "checked_at": 9999.0},
                 "lane-z": {**OK, "checked_at": 5.0}}
        outcome = self.ping(run([row("lane-a"), row("lane-b")], 1, events, cache))
        self.assertEqual(sorted(self.calls), ["lane-a", "lane-b"])
        self.assertEqual(outcome.cache["lane-a"]["checked_at"], 10000.0)
        self.assertEqual(outcome.cache["lane-z"]["checked_at"], 5.0)

    def test_identical_keys_are_pinged_once(self):
        self.ping(run([row("lane-a"), row("lane-a")]))
        self.assertEqual(self.calls, ["lane-a"])

    def test_results_match_by_key_and_replacements_keep_the_order(self):
        config = {"review": [*CONFIG["review"], {"key": "lane-d", "model": "placeholder-model-4",
                                                "command": "placeholder-cli-1 {model}"}],
                  "orders": {"review": [*CONFIG["orders"]["review"], "lane-d"]}}

        def probe(resolved, seams):
            if resolved.key == "lane-a":
                time.sleep(0.3)
                return blocked("quota")
            return blocked("auth") if resolved.key == "lane-b" else OK

        outcome = lane_ping.ping_lanes(run([row("lane-a"), row("lane-b")])._replace(config=config),
                                       lane_ping.PingSeams(probe_fn=probe))
        self.assertEqual([item["key"] for item in outcome.reviewers], ["lane-c", "lane-d"])
        self.assertEqual(outcome.lines, ["ping lane-a: replaced by lane-c (quota)",
                                         "ping lane-b: replaced by lane-d (auth)"])

    def test_judge_style_file_is_pinged_and_never_replaced(self):
        rows = [{**row("lane-a"), "key": "judge-a", "model": "placeholder-model-8"},
                {**row("lane-b"), "key": "judge-b", "model": "placeholder-model-9"}]
        self.entries["judge-a"] = blocked("quota")
        outcome = self.ping(run(rows))
        self.assertEqual(sorted(self.calls), ["judge-a", "judge-b"])
        self.assertEqual(outcome.lines, ["ping judge-a: failed (quota)", "ping judge-b: ok"])
        self.assertEqual([item["key"] for item in outcome.reviewers], ["judge-b"])
        self.assertEqual(outcome.stop, "")
        self.assertTrue(any(e["key"] == "judge-a" and e["state"] == "failed"
                            for e in outcome.events))
        self.assertFalse(any(e["state"] == "replaced" for e in outcome.events))

    def test_judge_file_through_the_cli_runs_no_route_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.path.join(tmp, "project")
            os.makedirs(cwd)
            env = {"HOME": os.path.join(tmp, "home"), "XDG_CONFIG_HOME": os.path.join(tmp, "xdg"),
                   "XDG_CACHE_HOME": os.path.join(tmp, "cache")}
            config = config_io.cfg_global_path(env)
            os.makedirs(os.path.dirname(config), exist_ok=True)
            with open(config, "w", encoding="utf-8") as stream:
                stream.write(ROSTER)
            with open(config, "rb") as stream:
                before = stream.read()
            reviewers = os.path.join(tmp, "reviewers.json")
            rows = [{**row("lane-a"), "key": "judge-a", "model": "placeholder-model-8"},
                    {**row("lane-b"), "key": "judge-b", "model": "placeholder-model-9"}]
            with open(reviewers, "w", encoding="utf-8") as stream:
                json.dump(rows, stream)
            which_calls, run_calls = [], []

            def fake(spec, prompt, seams):
                return RunnerResult(0, "Hello world!", {"status": "ok"}, None, False, ["fake"], "")

            def which(*args, **kwargs):
                which_calls.append(args)
                return None

            def run_cmd(*args, **kwargs):
                run_calls.append(args)
                return None

            out = io.StringIO()
            with redirect_stdout(out):
                code = cli.main(["ping-lanes", "--cwd", cwd, "--reviewers-json", reviewers,
                                 "--lane-log", os.path.join(tmp, "lanes.jsonl"), "--round", "1",
                                 "--quota-path", os.path.join(tmp, "quota.json")],
                                custom_fn=fake, runner_fn=fake, env_fn=lambda: dict(env),
                                which_fn=which, run_fn=run_cmd)
            self.assertEqual(code, 0)
            self.assertEqual(out.getvalue().splitlines(), ["ping judge-a: ok", "ping judge-b: ok"])
            self.assertEqual(which_calls, [])
            self.assertEqual(run_calls, [])
            with open(config, "rb") as stream:
                self.assertEqual(stream.read(), before)
            self.assertFalse(os.path.exists(config_io.cfg_local_path(cwd)))

    def test_native_row_is_never_probed(self):
        native = {"key": "lane-n", "model": "", "vendor": "", "runtime": None,
                  "command": None, "extra": {}, "route": "native"}
        outcome = self.ping(run([native, row("lane-a")]))
        self.assertEqual(self.calls, ["lane-a"])
        self.assertEqual(outcome.lines[0], "ping lane-n: ok")

    def test_every_failure_reason_is_a_listed_key(self):
        from ai_kit_spec.error_classifier import REASONS

        for reason in ("quota", "timeout"):
            with self.subTest(reason=reason):
                self.entries["lane-a"] = blocked(reason)
                outcome = self.ping(run([row("lane-a"), row("lane-b")]))
                for event in outcome.events:
                    for field in ("reason", "cause"):
                        if event.get(field) is not None:
                            self.assertIn(event[field], set(REASONS))


POOL_NOW = datetime(2099, 1, 1, tzinfo=UTC).timestamp()
PAST = datetime(2098, 12, 31, tzinfo=UTC)
FUTURE = datetime(2099, 1, 2, tzinfo=UTC)
POOL_NAME = "fake-provider:free"


def pooled_config(*keys):
    config = copy.deepcopy(CONFIG)
    for lane in config["review"]:
        if lane["key"] in keys:
            lane.update({"usage_limited": True, "pool": POOL_NAME})
    return config


class TestPingBlockedPool(unittest.TestCase):
    def setUp(self):
        self.log = []
        self.calls = []

    def probe(self, resolved, seams):
        self.log.append(("probe", resolved.key))
        self.calls.append(resolved.key)
        return OK

    def ping(self, ping_run, record, probe=None, **extra):
        def read(pool):
            self.log.append(("read", pool))
            return record(pool) if callable(record) else record

        return lane_ping.ping_lanes(ping_run, lane_ping.PingSeams(
            probe_fn=probe or self.probe, now_fn=lambda: POOL_NOW, read_fn=read, **extra))

    def test_blocked_flagged_lane_is_replaced_without_a_probe(self):
        ping_run = run([row("lane-a"), row("lane-b")])._replace(config=pooled_config("lane-a"))
        self.assertEqual(lane_switch.pool_keys(ping_run.config["review"]),
                         {"lane-a": POOL_NAME})
        outcome = self.ping(ping_run, FUTURE)
        self.assertNotIn("lane-a", self.calls)
        self.assertIn("ping lane-a: replaced by lane-c (quota)", outcome.lines)
        self.assertEqual(outcome.events[0]["cause"], "quota")

    def test_cleared_record_is_pinged_once(self):
        ping_run = run([row("lane-a"), row("lane-b")])._replace(config=pooled_config("lane-a"))
        outcome = self.ping(ping_run, None)
        self.assertEqual(sorted(self.calls), ["lane-a", "lane-b"])
        self.assertIn("ping lane-a: ok", outcome.lines)

    def test_expired_pool_retries_one_lane_and_reads_once(self):
        for label, after, result, expected, probed in (
                ("renewal", FUTURE, blocked("quota"),
                 ["ping lane-a: replaced by lane-c (quota)", "ping lane-b: failed (quota)"],
                 ["lane-a", "lane-c"]),
                ("clearing", None, OK, ["ping lane-a: ok", "ping lane-b: ok"],
                 ["lane-a", "lane-b"])):
            with self.subTest(label=label):
                self.log.clear()
                self.calls.clear()
                state = {"until": PAST}

                def probe(resolved, seams, state=state, after=after, result=result):
                    self.log.append(("probe", resolved.key))
                    self.calls.append(resolved.key)
                    if resolved.key == "lane-a":
                        state["until"] = after
                        return result
                    return OK

                ping_run = run([row("lane-a"), row("lane-b")])._replace(
                    config=pooled_config("lane-a", "lane-b"))
                outcome = self.ping(ping_run, lambda _pool, state=state: state["until"], probe)
                self.assertEqual(sorted(self.calls), probed)
                self.assertEqual(self.calls[0], "lane-a")
                for line in expected:
                    self.assertIn(line, outcome.lines)
                self.assertEqual([item for item in self.log if item[0] == "read"],
                                 [("read", POOL_NAME)])
                self.assertEqual(self.log[0][0], "read")

    def test_two_pools_are_read_once_each_before_any_probe(self):
        config = pooled_config("lane-a")
        config["review"][1].update({"usage_limited": True, "pool": "other-provider:free"})
        barrier = threading.Barrier(2, timeout=5)

        def record(_pool):
            barrier.wait()

        outcome = self.ping(run([row("lane-a"), row("lane-b")])._replace(config=config), record)
        self.assertFalse(barrier.broken)
        reads = [item for item in self.log if item[0] == "read"]
        self.assertEqual(sorted(pool for _, pool in reads), ["fake-provider:free",
                                                              "other-provider:free"])
        first_probe = next(i for i, item in enumerate(self.log) if item[0] == "probe")
        self.assertTrue(all(self.log.index(item) < first_probe for item in reads))
        self.assertEqual(sorted(self.calls), ["lane-a", "lane-b"])
        self.assertEqual(outcome.lines, ["ping lane-a: ok", "ping lane-b: ok"])

    def test_pooled_lane_keeps_the_round_2_cadence(self):
        events = [{"round": 1, "key": "lane-a", "state": "judged", "reason": None,
                   "cause": None, "by": None, "at": POOL_NOW - 10}]
        ping_run = run([row("lane-a"), row("lane-b")], 2, events)._replace(
            config=pooled_config("lane-a"))
        outcome = self.ping(ping_run, None)
        self.assertIn("ping lane-a: fresh", outcome.lines)
        self.assertEqual(sorted(self.calls), ["lane-b"])

    def test_status_read_time_never_comes_off_a_probe_budget(self):
        for seconds in (2, 5, 60):
            with self.subTest(seconds=seconds):
                clock = {"t": 0.0}
                seen = []

                def record(_pool, clock=clock, seconds=seconds):
                    clock["t"] += seconds

                def probe(resolved, seams, seen=seen):
                    seen.append((resolved.key, seams.timeout_s))
                    return OK

                ping_run = run([row("lane-a"), row("lane-b")], timeout_s=5)._replace(
                    config=pooled_config("lane-a"))
                outcome = self.ping(ping_run, record, probe,
                                    clock_fn=lambda clock=clock: clock["t"])
                self.assertEqual(outcome.lines, ["ping lane-a: ok", "ping lane-b: ok"])
                self.assertEqual(sorted(seen), [("lane-a", 5), ("lane-b", 5)])
                self.assertEqual([key for key, entry in outcome.cache.items()
                                  if entry.get("reason") == "ping_timeout"], [])

    def test_a_stalled_status_read_blocks_no_lane(self):
        release = threading.Event()
        self.addCleanup(release.set)
        seen = []

        def probe(resolved, seams):
            seen.append((resolved.key, seams.timeout_s))
            return OK

        ping_run = run([row("lane-a"), row("lane-b")], timeout_s=1)._replace(
            config=pooled_config("lane-a"))
        with mock.patch.object(lane_ping, "PING_GRACE_S", 0):
            outcome = self.ping(ping_run, lambda _pool: release.wait(10), probe)
        self.assertEqual(outcome.lines, ["ping lane-a: ok", "ping lane-b: ok"])
        self.assertEqual(sorted(seen), [("lane-a", 1), ("lane-b", 1)])
        self.assertEqual([key for key, entry in outcome.cache.items()
                          if entry.get("reason") == "ping_timeout"], [])


class TestPingBlockedPoolCli(TestPingLanes):
    def test_ping_probes_are_review_role(self):
        self._rows(["lane-a", "lane-b"])
        with mock.patch.object(lane_ping, "ping_lanes", wraps=lane_ping.ping_lanes) as wrapped:
            self._ping(set())
        seams = wrapped.call_args.args[0].probe_seams
        self.assertEqual(seams.role, "review")
        self.assertEqual(seams.timeout_s, 30)

    def test_cli_reads_the_runner_line(self):
        path = config_io.cfg_global_path(self.env)
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(ROSTER.replace(
                'key = "lane-a"\n',
                'key = "lane-a"\nusage_limited = true\npool = "fake-provider:free"\n', 1))
        self._rows(["lane-a", "lane-b"])
        unexpected, status_calls, seen = [], [], []

        def fake(spec, prompt, seams):
            seen.append(spec.key)
            return RunnerResult(0, "Hello world!", {"status": "ok"}, None, False, ["fake"], "")

        def fake_run(argv, *_a, **_k):
            if argv[0] == "/fake/bin/node" and argv[2:] == ["--describe"]:
                return subprocess.CompletedProcess(argv, 0, json.dumps({"runtimes": {}}), "")
            if argv[0] == "/fake/bin/node" and argv[2:] == ["--blocked-status", POOL_NAME]:
                status_calls.append(argv)
                return subprocess.CompletedProcess(
                    argv, 0, "blocked_until=2099-01-01T00:00:00Z failures=1\n", "")
            unexpected.append(argv)
            raise AssertionError(f"unexpected call {argv}")

        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = cli.main(["ping-lanes", "--cwd", self.cwd, "--reviewers-json", self.reviewers,
                             "--lane-log", self.log, "--round", "1", "--quota-path", self.quota],
                            custom_fn=fake, runner_fn=fake, env_fn=lambda: dict(self.env),
                            which_fn=lambda name, *_a, **_k: ("/fake/bin/node" if name == "node"
                                                              else None),
                            run_fn=fake_run)
        self.assertEqual(code, 0)
        self.assertEqual(unexpected, [])
        self.assertEqual(len(status_calls), 1)
        self.assertIn("ping lane-a: replaced by lane-c (quota)", out.getvalue())
        self.assertNotIn("lane-a", seen)


if __name__ == "__main__":
    unittest.main()
