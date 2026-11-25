"""switch-lane and dispatch-reviewer --lane-log: only a usage_limited lane that failed
with quota switches (fake lanes only)."""

import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime, timedelta
from unittest import mock

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import cli, config_io, lane_switch, review_log
from ai_kit_spec.capability_block import LaneRefused
from ai_kit_spec.error_classifier import REASONS
from ai_kit_spec.runner_dispatch import RunnerSeams

ROSTER = '''[[lanes.review]]
key = "lane-a"
model = "placeholder-model-1"
command = "placeholder-cli-1 {model}"
usage_limited = true
pool = "fake-provider:free"
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


def config(*lanes, order=None):
    return {"review": list(lanes),
            "orders": {"review": order or [item["key"] for item in lanes]}}


def lane(key, **settings):
    return {"key": key, "model": "placeholder-model-1",
            "command": "placeholder-cli-1 {model}", **settings}


def no_route(_key):
    return None


POOL = "fake-provider:free"


class TestBlockedUntil(unittest.TestCase):
    def _read(self, stdout, returncode=0, node: str | None = "/fake/bin/node",
              template: str | None = "/fake/cross-ai.mjs", raise_exc=None):
        calls = []

        def run_fn(argv, **_kwargs):
            calls.append(argv)
            if raise_exc is not None:
                raise raise_exc
            return subprocess.CompletedProcess(argv, returncode, stdout, "AIKIT-XAI status=ok\n")

        seams = RunnerSeams(which_fn=lambda _name: node, runner_path_fn=lambda: template,
                            env_fn=lambda: {})
        return lane_switch.blocked_until(POOL, seams, run_fn), calls

    def test_blocked_line_reads_a_time_and_blocks_a_flagged_pooled_lane(self):
        value, calls = self._read("blocked_until=2099-01-02T03:04:05Z failures=2\n")
        until = datetime(2099, 1, 2, 3, 4, 5, tzinfo=UTC)
        self.assertEqual(value, until)
        self.assertEqual(calls, [["/fake/bin/node", "/fake/cross-ai.mjs", "--blocked-status",
                                  POOL]])
        flagged = {"key": "lane-a", "usage_limited": True, "pool": POOL}
        before = datetime(2099, 1, 1, tzinfo=UTC).timestamp()
        self.assertEqual(lane_switch.pool_status(flagged, before, lambda _pool: until)[0],
                         "blocked")

        def never(*_a, **_k):
            raise AssertionError("run_fn called")

        reader = lane_switch.blocked_reader(types.SimpleNamespace(
            which_fn=lambda _name: None, env_fn=lambda: {}, run_fn=never))
        self.assertIsNone(reader(POOL))

    def test_unusable_answers_read_none(self):
        valid = "blocked_until=2099-01-02T03:04:05Z failures=2\n"
        for label, stdout, code in (
                ("none", "blocked_until=- failures=0\n", 0),
                ("malformed", "blocked_until=soon failures=1\n", 0),
                ("two lines", valid + valid, 0),
                ("impossible date", "blocked_until=2099-13-40T00:00:00Z failures=1\n", 0),
                ("exit 2", valid, 2)):
            with self.subTest(label=label):
                self.assertIsNone(self._read(stdout, returncode=code)[0])
        self.assertEqual(self._read(valid, node=None), (None, []))
        self.assertEqual(self._read(valid, template=None), (None, []))
        self.assertIsNone(self._read(valid, raise_exc=OSError("boom"))[0])
        self.assertIsNone(self._read(valid, raise_exc=UnicodeDecodeError(
            "utf-8", b"\xff", 0, 1, "invalid start byte"))[0])
        calls = []
        seams = RunnerSeams(which_fn=lambda _name: "/fake/bin/node",
                            runner_path_fn=lambda: "/fake/cross-ai.mjs", env_fn=lambda: {})
        self.assertIsNone(lane_switch.blocked_until(
            "not a pool", seams, lambda argv, **_k: calls.append(argv)))
        self.assertEqual(calls, [])

    def test_equal_time_counts_as_passed(self):
        now = datetime(2099, 1, 1, tzinfo=UTC)
        flagged = {"key": "lane-a", "usage_limited": True, "pool": POOL}
        self.assertEqual(lane_switch.pool_status(flagged, now.timestamp(), lambda _pool: now)[0],
                         "expired")
        later = now + timedelta(seconds=1)
        self.assertEqual(lane_switch.pool_status(flagged, now.timestamp(), lambda _pool: later)[0],
                         "blocked")

    def test_unflagged_or_poolless_lane_is_never_read(self):
        def never(_pool):
            raise AssertionError("reader called")

        now = datetime(2099, 1, 1, tzinfo=UTC)
        for item in ({"key": "lane-a", "pool": POOL},
                     {"key": "lane-a", "usage_limited": True},
                     {"key": "lane-a", "usage_limited": "yes", "pool": POOL}):
            with self.subTest(item=item):
                self.assertEqual(lane_switch.pool_status(item, now.timestamp(), never),
                                 ("none", ""))

    def test_cache_rule_blocks_or_retries_once(self):
        lanes = [{"key": "lane-a", "usage_limited": True, "pool": POOL},
                 {"key": "lane-b", "usage_limited": True, "pool": "other-provider:free"},
                 {"key": "lane-c"},
                 {"key": "lane-d", "usage_limited": True, "pool": POOL}]
        failed = {"available": False, "checked_at": 1.0, "reason": "quota", "detail": "",
                  "answered": False}
        existing = {"lane-b": dict(failed), "lane-c": dict(failed), "lane-d": dict(failed)}
        snapshot = json.loads(json.dumps(existing))
        until = datetime(2099, 1, 1, tzinfo=UTC)
        now_s = datetime(2098, 1, 1, tzinfo=UTC).timestamp()
        result = lane_switch.blocked_cache_entries(
            lanes, ["lane-a", "lane-b", "lane-c"], existing, now_s,
            lambda pool: until if pool == POOL else None)
        self.assertEqual(result["lane-a"], {
            "available": False, "checked_at": now_s, "reason": "quota",
            "detail": f"pool {POOL} blocked until 2099-01-01T00:00:00Z", "answered": False})
        self.assertNotIn("lane-b", result)
        self.assertEqual(result["lane-c"], failed)
        self.assertEqual(result["lane-d"], failed)
        self.assertEqual(existing, snapshot)

    def test_pool_status_tells_blocked_expired_and_none(self):
        flagged = {"key": "lane-a", "usage_limited": True, "pool": POOL}
        now_s = datetime(2099, 1, 1, tzinfo=UTC).timestamp()
        self.assertEqual(
            lane_switch.pool_status(flagged, now_s,
                                    lambda _pool: datetime(2099, 1, 2, tzinfo=UTC)),
            ("blocked", f"pool {POOL} blocked until 2099-01-02T00:00:00Z"))
        self.assertEqual(
            lane_switch.pool_status(flagged, now_s,
                                    lambda _pool: datetime(2099, 1, 1, tzinfo=UTC))[0],
            "expired")
        self.assertEqual(lane_switch.pool_status(flagged, now_s, lambda _pool: None),
                         ("none", ""))

        def never(_pool):
            raise AssertionError("reader called")

        self.assertEqual(lane_switch.pool_status({"key": "lane-b"}, now_s, never), ("none", ""))
        self.assertEqual(
            lane_switch.pool_keys([flagged, {"key": "lane-b"},
                                   {"key": "lane-c", "usage_limited": True, "pool": POOL}]),
            {"lane-a": POOL, "lane-c": POOL})

    def test_pool_decisions_retry_one_lane_per_expired_pool(self):
        lanes = [{"key": "lane-a", "usage_limited": True, "pool": POOL},
                 {"key": "lane-b"},
                 {"key": "lane-c", "usage_limited": True, "pool": POOL},
                 {"key": "lane-d", "usage_limited": True, "pool": "other-provider:free"}]
        reads = []

        def reader(pool):
            reads.append(pool)
            if pool == POOL:
                return datetime(2098, 12, 31, tzinfo=UTC)
            return datetime(2099, 1, 2, tzinfo=UTC)

        now_s = datetime(2099, 1, 1, tzinfo=UTC).timestamp()
        decisions = lane_switch.pool_decisions(
            lanes, ["lane-c", "lane-a", "lane-b", "lane-d"], now_s, reader)
        self.assertEqual(decisions["lane-c"][0], "expired-retry")
        self.assertEqual(decisions["lane-a"][0], "expired-wait")
        self.assertEqual(decisions["lane-d"][0], "blocked")
        self.assertNotIn("lane-b", decisions)
        self.assertEqual(sorted(reads), [POOL, "other-provider:free"])


class TestFlaggedReplacement(unittest.TestCase):
    def _pick(self, cfg, key="lane-a", reason="quota", exclude=(), route_fn=no_route):
        return lane_switch.flagged_replacement(cfg, key, reason, set(exclude), route_fn)

    def test_only_quota_switches_a_flagged_lane(self):
        cfg = config(lane("lane-a", usage_limited=True, pool=POOL), lane("lane-b"))
        self.assertEqual(self._pick(cfg), "lane-b")
        for reason in ("billing_or_access", "auth", "configuration", "capacity",
                       "real_error", "timeout"):
            with self.subTest(reason=reason):
                self.assertIsNone(self._pick(cfg, reason=reason))

    def test_unflagged_lane_never_switches(self):
        self.assertIsNone(self._pick(config(lane("lane-a"), lane("lane-b"))))

    def test_same_pool_lane_is_skipped(self):
        cfg = config(lane("lane-a", usage_limited=True, pool=POOL), lane("lane-b", pool=POOL),
                     lane("lane-c"))
        self.assertEqual(self._pick(cfg), "lane-c")

    def test_earlier_fallback_wins(self):
        lanes = (lane("lane-a", usage_limited=True), lane("lane-b"), lane("lane-c"))
        self.assertEqual(self._pick(config(*lanes)), "lane-b")
        self.assertEqual(self._pick(config(*lanes, order=["lane-a", "lane-c", "lane-b"])),
                         "lane-c")

    def test_no_eligible_fallback_gives_none(self):
        cfg = config(lane("lane-a", usage_limited=True, pool=POOL),
                     lane("lane-b", usage_limited=True), lane("lane-c", pool=POOL))
        self.assertIsNone(self._pick(cfg))

    def test_malformed_flag_and_unknown_or_unordered_key_give_none(self):
        self.assertIsNone(self._pick(config(lane("lane-a", usage_limited="yes"), lane("lane-b"))))
        self.assertIsNone(self._pick(config(lane("lane-a", usage_limited=True), lane("lane-b")),
                                     key="lane-x"))
        lanes = (lane("lane-a", usage_limited=True), lane("lane-b"))
        self.assertIsNone(self._pick(config(*lanes, order=["lane-b"])))
        three = (lane("lane-a", usage_limited=True), lane("lane-b"), lane("lane-c"))
        self.assertEqual(self._pick(config(*three, order=["lane-a", "lane-c"])), "lane-c")

    def test_excluded_and_skip_routed_lanes_are_passed_over(self):
        cfg = config(lane("lane-a", usage_limited=True), lane("lane-b"), lane("lane-c"))
        self.assertEqual(self._pick(cfg, exclude={"lane-b"}), "lane-c")
        routes = {"lane-b": "not_installed"}
        self.assertEqual(self._pick(cfg, route_fn=routes.get), "lane-c")


class TestFlaggedSwitch(unittest.TestCase):
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
        self.prompt = os.path.join(tmp.name, "prompt")
        with open(self.prompt, "w", encoding="utf-8") as stream:
            stream.write("review this")
        self.dispatched = []

    def _rows(self, keys):
        rows = [{"key": key, "model": f"placeholder-model-{ord(key[-1]) - 96}",
                 "vendor": "", "runtime": None, "command": "placeholder-cli-1 {model}",
                 "extra": {}, "route": "custom"} for key in keys]
        with open(self.reviewers, "w", encoding="utf-8") as stream:
            json.dump(rows, stream)

    def _seed(self, keys):
        for key in keys:
            review_log.append_event(self.log, {"round": 1, "key": key, "state": "chosen",
                                              "reason": None, "cause": None, "by": None, "at": 0})

    def _main(self, argv, **overrides):
        out, err = io.StringIO(), io.StringIO()
        deps = {"env_fn": lambda: dict(self.env), "which_fn": lambda *_a, **_k: None,
                "run_fn": lambda *_a, **_k: None, **overrides}
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv, **deps)
        return code, out.getvalue(), err.getvalue()

    def fake_dispatch(self, reason, returncode, stdout=""):
        def dispatch(spec, seams=None):
            self.dispatched.append(spec.reviewer_entry["key"])
            return {"stdout": stdout, "returncode": returncode, "timed_out": False,
                    "reason": reason, "status": None, "argv": []}
        return dispatch

    def _dispatch(self, index, fake):
        return self._main(["dispatch-reviewer", "--reviewers-json", self.reviewers,
                           "--index", str(index), "--prompt-file", self.prompt,
                           "--timeout-tiers", "60", "--stdout-only", "--lane-log", self.log,
                           "--round", "1"], dispatch_reviewer_fn=fake)

    def _switch(self, index):
        return self._main(["switch-lane", "--cwd", self.cwd, "--reviewers-json", self.reviewers,
                           "--index", str(index), "--lane-log", self.log, "--round", "1"])

    def _report(self, key, text):
        path = os.path.join(self.cwd, key + ".md")
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(text)
        return path

    def _merge(self, *reports):
        return self._main(["merge-reports", "--doc-paths", "spec.md", "--cwd", self.cwd,
                           "--lane-log", self.log, "--round", "1", *reports])

    def test_flagged_lane_with_quota_switches_and_the_review_finishes(self):
        self._rows(["lane-a", "lane-b"])
        self._seed(["lane-a", "lane-b"])
        self.assertEqual(self._dispatch(0, self.fake_dispatch("quota", 75))[0], 75)
        state = review_log.round_states(review_log.read_events(self.log), 1)["lane-a"]
        self.assertEqual((state["state"], state["reason"]), ("failed", "quota"))
        code, out, _ = self._switch(0)
        self.assertEqual(code, 0)
        self.assertIn("switched lane-a -> lane-c", out)
        with open(self.reviewers, encoding="utf-8") as stream:
            self.assertEqual([r["key"] for r in json.load(stream)], ["lane-c", "lane-b"])
        code, out, _ = self._dispatch(0, self.fake_dispatch(None, 0, "### Status: Approved\n"))
        self.assertEqual(code, 0)
        c = self._report("lane-c", out)
        self.assertEqual(self.dispatched, ["lane-a", "lane-c"])
        b = self._report("lane-b", "### Status: Approved\n")
        code, out, _ = self._merge(f"lane-c={c}", f"lane-b={b}")
        self.assertEqual(code, 0)
        self.assertIn("Judged by: lane-b, lane-c; not judged: lane-a (replaced, by lane-c)",
                      out.splitlines())
        self.assertIn("### Status: Approved (partial)", out.splitlines())

    def test_failed_log_write_leaves_the_file_and_log_matching(self):
        real_append = review_log.append_event
        for fail_on in (1, 2):
            with self.subTest(fail_on=fail_on):
                if os.path.exists(self.log):
                    os.remove(self.log)
                self._rows(["lane-a", "lane-b"])
                self._seed(["lane-a", "lane-b"])
                self.assertEqual(self._dispatch(0, self.fake_dispatch("quota", 75))[0], 75)
                before = self._bytes()
                calls = []

                def append(path, *events, _fail_on=fail_on, _calls=calls):
                    _calls.append(path)
                    if len(_calls) == _fail_on:
                        raise OSError("disk full")
                    real_append(path, *events)

                with mock.patch.object(review_log, "append_event", side_effect=append):
                    code, out, err = self._switch(0)
                states = review_log.round_states(review_log.read_events(self.log), 1)
                if code == 0:
                    self.assertEqual(self._keys(), ["lane-c", "lane-b"])
                    self.assertEqual((states["lane-a"]["state"], states["lane-c"]["state"]),
                                     ("replaced", "chosen"))
                else:
                    self.assertEqual(code, 2)
                    self.assertIn("disk full", err)
                    self.assertNotIn("switched", out)
                    self.assertEqual(self._bytes(), before)
                    self.assertEqual((states["lane-a"]["state"], states["lane-a"]["reason"]),
                                     ("failed", "quota"))
                    self.assertNotIn("lane-c", states)

    def test_unflagged_exit_69_keeps_the_sibling_report(self):
        self._rows(["lane-b", "lane-c"])
        self._seed(["lane-b", "lane-c"])
        with open(self.reviewers, "rb") as stream:
            before = stream.read()
        self.assertEqual(self._dispatch(0, self.fake_dispatch("billing_or_access", 69))[0], 69)
        code, out, _ = self._switch(0)
        self.assertEqual(code, 1)
        self.assertIn("not switched lane-b: billing_or_access", out)
        with open(self.reviewers, "rb") as stream:
            self.assertEqual(stream.read(), before)
        c = self._report("lane-c", "### Status: Approved\n")
        b = os.path.join(self.cwd, "missing.md")
        code, out, _ = self._merge(f"lane-b={b}", f"lane-c={c}")
        self.assertEqual(code, 0)
        self.assertIn("Judged by: lane-c; not judged: lane-b (billing_or_access)", out.splitlines())
        self.assertIn("### Status: Approved (partial)", out.splitlines())

    def _roster(self, text):
        with open(config_io.cfg_global_path(self.env), "w", encoding="utf-8") as stream:
            stream.write(text)

    def _bytes(self):
        with open(self.reviewers, "rb") as stream:
            return stream.read()

    def _keys(self):
        with open(self.reviewers, encoding="utf-8") as stream:
            return [row["key"] for row in json.load(stream)]

    def _state(self, key):
        return review_log.round_states(review_log.read_events(self.log), 1)[key]

    @staticmethod
    def _refuse(spec, seams=None):
        raise LaneRefused({"reason": "prompt_over_window"})

    def test_unflagged_lane_failure_is_reported_not_replaced(self):
        for reason in ("quota", "capacity", "real_error"):
            with self.subTest(reason=reason):
                if os.path.exists(self.log):
                    os.remove(self.log)
                self._rows(["lane-b", "lane-c"])
                self._seed(["lane-b", "lane-c"])
                before = self._bytes()
                self.assertEqual(self._dispatch(0, self.fake_dispatch(reason, 1))[0], 1)
                code, out, _ = self._switch(0)
                self.assertEqual(code, 1)
                self.assertIn(f"not switched lane-b: {reason}", out)
                self.assertEqual(self._bytes(), before)
                c = self._report("lane-c", "### Status: Approved\n")
                b = os.path.join(self.cwd, "missing.md")
                code, out, _ = self._merge(f"lane-b={b}", f"lane-c={c}")
                self.assertEqual(code, 0)
                self.assertIn(f"Judged by: lane-c; not judged: lane-b ({reason})",
                              out.splitlines())

    def test_flagged_lane_without_fallback_stays_failed(self):
        self._roster(ROSTER.replace(
            'command = "placeholder-cli-1 {model}"\n[[lanes.review]]\nkey = "lane-c"',
            'command = "placeholder-cli-1 {model}"\nusage_limited = true\n'
            '[[lanes.review]]\nkey = "lane-c"').replace(
            'model = "placeholder-model-3"\ncommand = "placeholder-cli-1 {model}"',
            'model = "placeholder-model-3"\ncommand = "placeholder-cli-1 {model}"\n'
            'usage_limited = true'))
        self._rows(["lane-a", "lane-b"])
        self._seed(["lane-a", "lane-b"])
        before = self._bytes()
        self.assertEqual(self._dispatch(0, self.fake_dispatch("quota", 75))[0], 75)
        code, out, _ = self._switch(0)
        self.assertEqual(code, 1)
        self.assertIn("not switched lane-a: quota", out)
        self.assertEqual(self._bytes(), before)

    def test_refused_lane_records_configuration_and_never_switches(self):
        self._rows(["lane-a", "lane-b"])
        self._seed(["lane-a", "lane-b"])
        self.assertEqual(self._dispatch(0, self._refuse)[0], 65)
        state = self._state("lane-a")
        self.assertEqual((state["state"], state["reason"]), ("failed", "configuration"))
        code, out, _ = self._switch(0)
        self.assertEqual(code, 1)
        self.assertIn("not switched lane-a: configuration", out)

    def test_lane_without_a_failure_is_not_switched(self):
        self._rows(["lane-a", "lane-b"])
        self._seed(["lane-a"])
        code, out, _ = self._switch(0)
        self.assertEqual(code, 1)
        self.assertIn("not switched lane-a: chosen", out)
        os.remove(self.log)
        code, out, _ = self._switch(0)
        self.assertEqual(code, 1)
        self.assertIn("not switched lane-a: no record", out)

    def test_round_and_index_must_be_valid(self):
        self._rows(["lane-a", "lane-b"])
        before = self._bytes()
        base = ["dispatch-reviewer", "--reviewers-json", self.reviewers, "--index", "0",
                "--prompt-file", self.prompt, "--timeout-tiers", "60", "--stdout-only",
                "--lane-log", self.log]
        fake = self.fake_dispatch(None, 0)
        self.assertEqual(self._main(base, dispatch_reviewer_fn=fake)[0], 2)
        self.assertEqual(self._main([*base, "--round", "0"], dispatch_reviewer_fn=fake)[0], 2)
        self.assertFalse(os.path.exists(self.log))
        common = ["switch-lane", "--cwd", self.cwd, "--reviewers-json", self.reviewers,
                  "--lane-log", self.log]
        self.assertEqual(self._main([*common, "--index", "0", "--round", "0"])[0], 2)
        self.assertEqual(self._main([*common, "--index", "-1", "--round", "1"])[0], 2)
        self.assertEqual(self._bytes(), before)

    def test_refusals_run_no_route_discovery(self):
        for keys, reason in ((["lane-b", "lane-c"], "quota"), (["lane-a", "lane-b"], "capacity")):
            with self.subTest(keys=keys, reason=reason):
                if os.path.exists(self.log):
                    os.remove(self.log)
                self._rows(keys)
                self._seed(keys)
                self.assertEqual(self._dispatch(0, self.fake_dispatch(reason, 1))[0], 1)
                with mock.patch.object(lane_switch, "review_routes",
                                       side_effect=AssertionError("route discovery")):
                    code, out, _ = self._switch(0)
                self.assertEqual(code, 1)
                self.assertIn(f"not switched {keys[0]}: {reason}", out)

    def test_bad_prompt_or_tiers_record_configuration(self):
        self._rows(["lane-a", "lane-b"])
        fake = self.fake_dispatch(None, 0)
        cases = (("--prompt-file", os.path.join(self.cwd, "missing-prompt")),
                 ("--timeout-tiers", "sixty"))
        for flag, value in cases:
            with self.subTest(flag=flag):
                if os.path.exists(self.log):
                    os.remove(self.log)
                argv = ["dispatch-reviewer", "--reviewers-json", self.reviewers, "--index", "0",
                        "--prompt-file", self.prompt, "--timeout-tiers", "60", "--stdout-only",
                        "--lane-log", self.log, "--round", "1"]
                argv[argv.index(flag) + 1] = value
                code, _, err = self._main(argv, dispatch_reviewer_fn=fake)
                self.assertEqual(code, 1)
                self.assertIn("dispatch-reviewer: ", err)
                state = self._state("lane-a")
                self.assertEqual((state["state"], state["reason"]), ("failed", "configuration"))
        self.assertEqual(self.dispatched, [])

    def test_unreadable_input_exits_2(self):
        self._seed(["lane-a"])
        for text in ("{not json", '[{"model": "placeholder-model-1"}]'):
            with self.subTest(text=text):
                with open(self.reviewers, "w", encoding="utf-8") as stream:
                    stream.write(text)
                code, out, err = self._switch(0)
                self.assertEqual((code, out), (2, ""))
                self.assertTrue(err.startswith("switch-lane: "), err)

    def test_changed_lane_identity_is_not_switched(self):
        self._rows(["lane-a", "lane-b"])
        self._seed(["lane-a", "lane-b"])
        self.assertEqual(self._dispatch(0, self.fake_dispatch("quota", 75))[0], 75)
        with open(self.reviewers, encoding="utf-8") as stream:
            rows = json.load(stream)
        rows[0]["model"] = "placeholder-model-9"
        with open(self.reviewers, "w", encoding="utf-8") as stream:
            json.dump(rows, stream)
        code, out, _ = self._switch(0)
        self.assertEqual(code, 1)
        self.assertIn("not switched lane-a: lane changed", out)
        events = review_log.read_events(self.log)
        self.assertEqual([e for e in events if e["state"] == "replaced"], [])

    def test_two_failed_slots_switch_one_at_a_time(self):
        self._roster(ROSTER.replace(
            'model = "placeholder-model-2"\ncommand = "placeholder-cli-1 {model}"',
            'model = "placeholder-model-2"\ncommand = "placeholder-cli-1 {model}"\n'
            'usage_limited = true\npool = "other-provider:free"'))
        self._rows(["lane-a", "lane-b"])
        self._seed(["lane-a", "lane-b"])
        self.assertEqual(self._dispatch(0, self.fake_dispatch("quota", 75))[0], 75)
        self.assertEqual(self._dispatch(1, self.fake_dispatch("quota", 75))[0], 75)
        code, out, _ = self._switch(0)
        self.assertEqual(code, 0)
        self.assertIn("switched lane-a -> lane-c", out)
        code, out, _ = self._switch(1)
        self.assertEqual(code, 1)
        self.assertIn("not switched lane-b: quota", out)
        self.assertEqual(self._keys(), ["lane-c", "lane-b"])
        events = review_log.read_events(self.log)
        self.assertEqual(len([e for e in events if e["state"] == "replaced"]), 1)

    def test_every_recorded_reason_is_listed(self):
        self._rows(["lane-a", "lane-b"])
        self._seed(["lane-a", "lane-b"])
        self.assertEqual(self._dispatch(0, self.fake_dispatch("quota", 75))[0], 75)
        self.assertEqual(self._switch(0)[0], 0)
        self.assertEqual(self._dispatch(1, self.fake_dispatch("capacity", 1))[0], 1)
        self.assertEqual(self._dispatch(1, self._refuse)[0], 65)
        for event in review_log.read_events(self.log):
            for field in ("reason", "cause"):
                self.assertTrue(event[field] is None or event[field] in set(REASONS), event)

    def test_resumed_flagged_lane_failing_with_quota_switches(self):
        self._rows(["lane-a", "lane-b"])
        self._seed(["lane-a", "lane-b"])
        self.assertEqual(self._dispatch(0, self.fake_dispatch("capacity", 75))[0], 75)
        code, out, _ = self._switch(0)
        self.assertEqual(code, 1)
        self.assertIn("not switched lane-a: capacity", out)
        self.assertEqual(self._dispatch(0, self.fake_dispatch("quota", 75))[0], 75)
        state = self._state("lane-a")
        self.assertEqual((state["state"], state["reason"]), ("failed", "quota"))
        code, out, _ = self._switch(0)
        self.assertEqual(code, 0)
        self.assertIn("switched lane-a -> lane-c", out)
        self.assertEqual(self._keys(), ["lane-c", "lane-b"])

    def test_resumed_lane_after_a_failed_attempt_is_judged(self):
        self._rows(["lane-b", "lane-c"])
        self._seed(["lane-b", "lane-c"])
        self.assertEqual(self._dispatch(0, self.fake_dispatch("quota", 75))[0], 75)
        code, out, _ = self._dispatch(0, self.fake_dispatch(None, 0, "### Status: Approved\n"))
        self.assertEqual(code, 0)
        self.assertEqual(self._state("lane-b")["state"], "chosen")
        b = self._report("lane-b", "### Status: Approved\n")
        c = self._report("lane-c", "### Status: Approved\n")
        code, out, _ = self._merge(f"lane-b={b}", f"lane-c={c}")
        self.assertEqual(code, 0)
        self.assertIn("Judged by: lane-b, lane-c", out.splitlines())
        self.assertIn("### Status: Approved", out.splitlines())


if __name__ == "__main__":
    unittest.main()
