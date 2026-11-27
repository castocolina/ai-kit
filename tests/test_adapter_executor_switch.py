"""Executor switch: the pool reaches the runner, the execute-role switch and the blocked skip
at selection (fake lanes only)."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-execute-superpowers")
)

from ai_kit_spec import (
    config_io,
    lane_settings,
    lane_switch,
    quota,
    runner_dispatch,
    runner_facts,
)
from ai_kit_spec.execute_dispatch import ComposeResult, ExecuteSeams, dispatch_execute
from ai_kit_spec.runner_dispatch import RunnerResult
from ai_kit_spec_superpowers import cli as superpowers_cli
from ai_kit_spec_superpowers import dispatch_injection

POOL = "fake-provider:free"
FLAGGED = {"key": "lane-a", "runtime": "codex", "model": "fake/placeholder-model-1",
           "usage_limited": True, "pool": POOL}
PLAIN = {"key": "lane-b", "runtime": "codex", "model": "fake/placeholder-model-2"}
NOW = 1_800_000_000.0
FLAGGED_B = {"key": "lane-b2", "runtime": "codex", "model": "fake/placeholder-model-4",
             "usage_limited": True, "pool": POOL}
CONFIG = {"execute": [FLAGGED, PLAIN], "orders": {"execute": ["lane-a", "lane-b"]}}


def ex_config(*lanes, order=None):
    return {"execute": list(lanes), "orders": {"execute": order or [lane["key"] for lane in lanes]}}


def stamp(offset_s):
    return datetime.fromtimestamp(NOW + offset_s, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def route(_key):
    return "subprocess"


def execute_switch(cfg, key, reason, exclude=()):
    if lane_switch.flagged_lane(cfg, key, reason, role="execute") is None:
        return None
    return lane_switch.next_lane(cfg, key, set(exclude), route, role="execute")


def _dispatched_flags(candidate):
    with tempfile.TemporaryDirectory() as target, mock.patch.dict(
        os.environ, {"HOME": os.path.join(target, "home"),
                     "XDG_CACHE_HOME": os.path.join(target, "cache")}
    ), mock.patch.object(runner_facts, "stored_fact", return_value=None):
        injection = {**dispatch_injection._injection_for(candidate, "subprocess"),
                     "ladder_keys": ["lane-a", "lane-b"]}
        seen = []

        def fake_runner(spec, prompt, seams):
            del prompt, seams
            seen.append(spec)
            return RunnerResult(0, "DONE", {"status": "ok"}, None, False, ["node", "runner"], "")

        dispatch_injection.dispatch_superpowers_task(
            dispatch_injection.DispatchTaskRequest(injection, "do the task", target, 900),
            seams=dispatch_injection.SuperpowersDispatchSeams(
                dispatch_execute_fn=lambda spec: dispatch_execute(
                    spec, seams=ExecuteSeams(
                        runner_fn=fake_runner,
                        compose_fn=lambda *_a, **_k: ComposeResult())),
                env_fn=lambda: {"HOME": target}))
        return injection, seen[0], runner_dispatch.runner_flags(seen[0])


class TestExecutorPool(unittest.TestCase):
    def test_flagged_pooled_lane_carries_its_pool_to_the_runner(self):
        candidates, _ = dispatch_injection.assemble_candidates(
            "unused", {}, cfg_resolve_fn=lambda _cwd, _env: CONFIG)
        self.assertEqual(candidates[0]["pool"], POOL)
        self.assertIsNone(candidates[1]["pool"])
        injection, spec, flags = _dispatched_flags(candidates[0])
        self.assertEqual(injection["pool"], POOL)
        self.assertEqual(spec.pool, POOL)
        self.assertIn("--pool", flags)
        self.assertEqual(flags[flags.index("--pool") + 1], POOL)

    def test_unflagged_lane_passes_no_pool(self):
        candidates, _ = dispatch_injection.assemble_candidates(
            "unused", {}, cfg_resolve_fn=lambda _cwd, _env: CONFIG)
        _, spec, flags = _dispatched_flags(candidates[1])
        self.assertIsNone(spec.pool)
        self.assertNotIn("--pool", flags)


class TestExecuteRoleSwitch(unittest.TestCase):
    def test_flagged_lane_moves_to_the_first_unflagged_lane_of_another_pool(self):
        same_pool = {"key": "lane-b", "runtime": "codex", "model": "fake/placeholder-model-2",
                     "pool": POOL}
        other = {"key": "lane-c", "runtime": "codex", "model": "fake/placeholder-model-3"}
        cfg = ex_config(FLAGGED, same_pool, other)
        self.assertEqual(execute_switch(cfg, "lane-a", "quota"), "lane-c")

    def test_two_eligible_fallbacks_take_the_earlier_in_order(self):
        lane_b = {"key": "lane-b", "runtime": "codex", "model": "fake/placeholder-model-2"}
        lane_c = {"key": "lane-c", "runtime": "codex", "model": "fake/placeholder-model-3"}
        cfg = ex_config(FLAGGED, lane_b, lane_c, order=["lane-a", "lane-c", "lane-b"])
        self.assertEqual(execute_switch(cfg, "lane-a", "quota"), "lane-c")

    def test_unflagged_or_non_quota_or_no_fallback_gives_none(self):
        cfg = ex_config(FLAGGED, PLAIN)
        self.assertIsNone(lane_switch.flagged_lane(cfg, "lane-b", "quota", role="execute"))
        self.assertIsNone(lane_switch.flagged_lane(cfg, "lane-a", "auth", role="execute"))
        other_flagged = {**PLAIN, "usage_limited": True, "pool": "fake-provider:other"}
        alone = ex_config(FLAGGED, other_flagged)
        self.assertIs(lane_switch.flagged_lane(alone, "lane-a", "quota", role="execute"), FLAGGED)
        self.assertIsNone(execute_switch(alone, "lane-a", "quota"))

    def test_review_default_is_unchanged(self):
        cfg = ex_config(FLAGGED, PLAIN)
        self.assertIsNone(lane_switch.flagged_replacement(cfg, "lane-a", "quota", set(), route))
        self.assertIs(lane_switch.review_lane(ex_config(FLAGGED), "lane-a", role="execute"),
                      FLAGGED)

    def test_replacement_row_reads_the_execute_roster(self):
        row = lane_switch.replacement_row(ex_config(FLAGGED, PLAIN), "lane-b", route,
                                          role="execute")
        self.assertEqual(row["route"], "subprocess")


class TestQuotaEvidence(unittest.TestCase):
    def test_only_runner_quota_is_evidence(self):
        cycle = {"retry_after_s": "600", "cycle": "2"}
        rows = [
            ({"returncode": 69, "status": {"status": "transient"}}, False, "quota"),
            ({"returncode": 75, "status": {"status": "transient", **cycle}}, False,
             "quota_cycle"),
            ({"returncode": 69, "status": {"status": "quota"}}, True, "quota"),
            ({"returncode": 75, "status": {"status": "quota", **cycle}}, True, "quota_cycle"),
            ({"returncode": 1, "reason": "quota", "status": None}, True, "quota"),
            ({"returncode": 0, "status": {"status": "ok"}}, False, "ok"),
        ]
        for result, expected, klass in rows:
            with self.subTest(result=result):
                self.assertIs(dispatch_injection.quota_evidence(result), expected)
                self.assertEqual(dispatch_injection.dispatch_classification(result)["class"],
                                 klass)


class TestBlockedAtSelection(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.task = os.path.join(self.tmp, "task-1-brief.md")
        self.brief = "### Task 1\n**Files:**\n- Create: `one.py`\n"
        with open(self.task, "w", encoding="utf-8") as handle:
            handle.write(self.brief)

    def _resolve(self, resolved, status_stdout, *, node: str | None = "/fake/bin/node",
                 exclude=(),
                 cached=None, routes=None, env=None, refresh_fn=None):
        argvs = []
        refreshed = []

        def run(argv, **_kwargs):
            argvs.append(argv)
            if "--blocked-status" in argv:
                return subprocess.CompletedProcess(argv, 0, status_stdout, "")
            return subprocess.CompletedProcess(argv, 1, "", "")

        def refresh(_cfg, _keys, existing, _ttl):
            refreshed.append(dict(existing))
            return dict(existing)

        out = io.StringIO()
        rc = superpowers_cli.main(
            ["resolve-injection", "--cwd", self.tmp, "--task-file", self.task,
             "--quota-path", os.path.join(self.tmp, "quota.json"),
             "--exclude-keys-json", json.dumps(list(exclude))],
            assemble_candidates_fn=lambda cwd, env_: dispatch_injection.assemble_candidates(
                cwd, env_, cfg_resolve_fn=lambda _c, _e: resolved),
            cache_read_json_fn=lambda _p: dict(cached or {}),
            cache_write_json_fn=lambda _p, _d: None,
            refresh_quota_cache_fn=refresh_fn or refresh,
            route_all_fn=lambda cands, _ctx: {
                c["key"]: (routes or {}).get(c["key"], "subprocess") for c in cands},
            which_fn=lambda name: node if name == "node" else None,
            run_fn=run,
            env_fn=lambda: dict(env or {"HOME": self.tmp}),
            clock_fn=lambda: NOW,
            stdout=out)
        blocked = [a for a in argvs if "--blocked-status" in a]
        return rc, json.loads(out.getvalue()), blocked, (refreshed[0] if refreshed else None)

    def test_blocked_pool_lane_is_skipped(self):
        rc, result, blocked, _ = self._resolve(
            ex_config(FLAGGED, PLAIN), f"blocked_until={stamp(3600)} failures=1\n")
        self.assertEqual(rc, 0)
        self.assertEqual(result["key"], "lane-b")
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0][-1], POOL)

    def test_expired_pool_is_tried_once_by_the_first_eligible_lane(self):
        stale = {"available": False, "checked_at": NOW - 60, "reason": "quota",
                 "detail": "stale", "answered": False}
        _, result, blocked, refreshed = self._resolve(
            ex_config(FLAGGED, FLAGGED_B, PLAIN), f"blocked_until={stamp(-3600)} failures=1\n",
            exclude=["lane-a"], cached={"lane-b2": stale})
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0][-1], POOL)
        assert refreshed is not None
        self.assertNotIn("lane-b2", refreshed)
        self.assertNotIn("lane-a", refreshed)
        self.assertEqual(result["key"], "lane-b2")

    def test_affinity_reentry_lane_is_still_checked(self):
        lane_a = {"key": "lane-a", "runtime": "codex", "model": "fake/placeholder-model-1"}
        lane_b = {"key": "lane-b", "runtime": "codex", "model": "fake/placeholder-model-2",
                  "usage_limited": True, "pool": POOL, "task_affinity": "frontend"}
        self.assertNotEqual(dispatch_injection.classify_task(self.brief), "frontend")
        _, result, blocked, _ = self._resolve(
            ex_config(lane_a, lane_b), f"blocked_until={stamp(3600)} failures=1\n",
            exclude=["lane-a"])
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0][-1], POOL)
        self.assertEqual(result["mode"], "quota_exhausted")

    def test_expired_pool_probes_only_its_first_eligible_lane(self):
        probed = []

        def probe(spec, prompt, seams):
            del prompt, seams
            probed.append(spec.model)
            return RunnerResult(0, "Hello world!", {"status": "ok"}, None, False,
                                ["node", "runner"], "")

        def refresh(cfg, keys, existing, ttl):
            return quota.refresh_quota_cache(
                cfg, keys, existing, ttl,
                seams=quota.ProbeSeams(runner_fn=probe, env_fn=lambda: {"HOME": self.tmp}))

        with mock.patch.object(quota.time, "time", return_value=NOW):
            _, result, blocked, _ = self._resolve(
                ex_config(FLAGGED, FLAGGED_B), f"blocked_until={stamp(-3600)} failures=1\n",
                refresh_fn=refresh)
        self.assertEqual(len(blocked), 1)
        self.assertEqual(probed, ["fake/placeholder-model-1"])
        self.assertEqual(result["key"], "lane-a")

    def test_missing_node_or_bad_record_blocks_nothing(self):
        cfg = ex_config(FLAGGED, PLAIN)
        _, result, _, _ = self._resolve(
            cfg, f"blocked_until={stamp(3600)} failures=1\n", node=None)
        self.assertEqual(result["key"], "lane-a")
        _, result, _, _ = self._resolve(cfg, "garbage\n")
        self.assertEqual(result["key"], "lane-a")

    def test_unflagged_lane_reads_no_record(self):
        lane_c = {"key": "lane-c", "runtime": "codex", "model": "fake/placeholder-model-3"}
        _, result, blocked, _ = self._resolve(
            ex_config(PLAIN, lane_c), f"blocked_until={stamp(3600)} failures=1\n")
        self.assertEqual(result["key"], "lane-b")
        self.assertEqual(blocked, [])

    def test_native_routed_flagged_lane_reads_no_record(self):
        _, result, blocked, _ = self._resolve(
            ex_config(FLAGGED, PLAIN), f"blocked_until={stamp(3600)} failures=1\n",
            routes={"lane-a": "native"})
        self.assertEqual(blocked, [])
        self.assertEqual(result["mode"], "native")
        self.assertEqual(result["key"], "lane-a")

    def test_sole_blocked_pool_with_session_fallback_runs_native(self):
        env = {"HOME": self.tmp, "XDG_CONFIG_HOME": os.path.join(self.tmp, ".config")}
        text = config_io.cfg_render_lanes({
            "policy": {"execute": {"ladder": ["lane-a"], lane_settings.SESSION_FALLBACK_KEY: True}},
            "lanes": [{"key": "lane-a", "runtime": "codex",
                        "model": "fake/placeholder-model-1", "purpose": "execute"}],
        })
        os.makedirs(os.path.dirname(config_io.cfg_global_path(env)), exist_ok=True)
        with open(config_io.cfg_global_path(env), "w", encoding="utf-8") as handle:
            handle.write(text)
        rc, result, blocked, _ = self._resolve(
            ex_config(FLAGGED), f"blocked_until={stamp(3600)} failures=1\n", env=env)
        self.assertEqual(rc, 0)
        self.assertEqual(result["mode"], "native")
        self.assertEqual(result["fallback"], "session")
        self.assertEqual(len(blocked), 1)


ROSTER = """
[[lanes.execute]]
key = "lane-a"
runtime = "codex"
model = "fake/placeholder-model-1"
purpose = "execute"
usage_limited = true

[[lanes.execute]]
key = "lane-b"
runtime = "codex"
model = "fake/placeholder-model-2"
purpose = "execute"

[lanes.policy.execute]
ladder = ["lane-a", "lane-b"]
"""
ROSTER_ABC = """
[[lanes.execute]]
key = "lane-a"
runtime = "codex"
model = "fake/placeholder-model-1"
purpose = "execute"
usage_limited = true

[[lanes.execute]]
key = "lane-b"
runtime = "codex"
model = "fake/placeholder-model-2"
purpose = "execute"

[[lanes.execute]]
key = "lane-c"
runtime = "codex"
model = "fake/placeholder-model-3"
purpose = "execute"

[lanes.policy.execute]
ladder = ["lane-a", "lane-b", "lane-c"]
"""
ROSTER_GATE = """
[[lanes.execute]]
key = "lane-top"
runtime = "opencode"
model = "fake/placeholder-model-3"
purpose = "execute"
usage_limited = true

[[lanes.execute]]
key = "lane-mid"
runtime = "opencode"
model = "fake/placeholder-model-5"
purpose = "execute"

[[lanes.execute]]
key = "lane-anchor"
runtime = "codex"
model = "fake/placeholder-model-1"
purpose = "execute"
escalate_runtime = true

[lanes.policy.execute]
ladder = ["lane-top", "lane-mid", "lane-anchor"]
"""
ROSTER_OFF = """
[[lanes.execute]]
key = "lane-other"
runtime = "opencode"
model = "fake/placeholder-model-5"
purpose = "execute"

[[lanes.execute]]
key = "lane-anchor"
runtime = "codex"
model = "fake/placeholder-model-1"
purpose = "execute"
usage_limited = true

[lanes.policy.execute]
ladder = ["lane-other", "lane-anchor"]
"""
QUOTA_69 = {"returncode": 69, "status": {"status": "quota"}, "reason": "quota"}
QUOTA_75 = {"returncode": 75, "status": {"status": "quota", "retry_after_s": 60, "cycle": 1}}
TRANSIENT_69 = {"returncode": 69, "status": {"status": "transient"}, "reason": "capacity"}
TRANSIENT_75 = {"returncode": 75,
                "status": {"status": "transient", "retry_after_s": 60, "cycle": 1},
                "reason": "capacity"}


class TestExecutorFallback(unittest.TestCase):
    def setUp(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        self.root = root
        self.cwd = os.path.join(root, "project")
        os.makedirs(self.cwd)
        self.env = {"HOME": os.path.join(root, "home"),
                    "XDG_CONFIG_HOME": os.path.join(root, "xdg"),
                    "XDG_CACHE_HOME": os.path.join(root, "cache")}
        self.route_calls = []
        self._n = 0
        self._write(ROSTER)

    def _write(self, toml_text):
        path = config_io.cfg_local_path(self.cwd)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(toml_text)

    def _raw(self, text):
        self._n += 1
        path = os.path.join(self.root, f"input-{self._n}.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def _result(self, obj):
        return self._raw(json.dumps(obj))

    def _exclude(self, keys):
        return self._raw(json.dumps(list(keys)))

    def _injection(self, ladder):
        return self._raw(json.dumps({"mode": "external_cli", "key": ladder[0],
                                     "runtime": "codex", "ladder_keys": list(ladder)}))

    def _route_all(self, cands, _ctx):
        self.route_calls.append([c["key"] for c in cands])
        return {c["key"]: "subprocess" for c in cands}

    def _main(self, key, files, out):
        dispatch, exclude, injection = files
        return superpowers_cli.main(
            ["executor-fallback", "--cwd", self.cwd, "--key", key,
             "--dispatch-result", dispatch, "--exclude-keys-file", exclude,
             "--injection-file", injection],
            env_fn=lambda: dict(self.env), route_all_fn=self._route_all, stdout=out)

    def _run(self, key, result, exclude=(), ladder=("lane-a", "lane-b")):
        out = io.StringIO()
        files = (self._result(result), self._exclude(exclude), self._injection(ladder))
        rc = self._main(key, files, out)
        return rc, json.loads(out.getvalue())

    def _gate_file(self, anchor, ladder):
        out_dir = os.path.join(self.root, "gate-" + anchor)
        os.makedirs(out_dir, exist_ok=True)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = superpowers_cli.main(
                ["escalation-gate", "--cwd", self.cwd, "--anchor-key", anchor,
                 "--injection-file", self._injection(ladder), "--out-dir", out_dir],
                env_fn=lambda: dict(self.env), stdout=io.StringIO())
        self.assertEqual(rc, 0, err.getvalue())
        return os.path.join(out_dir, "ESCALATION_EXCLUDE_JSON.json")

    def _run_files(self, key, result, exclude_files, ladder):
        argv = ["executor-fallback", "--cwd", self.cwd, "--key", key,
                "--dispatch-result", self._result(result)]
        for path in exclude_files:
            argv += ["--exclude-keys-file", path]
        argv += ["--injection-file", self._injection(ladder)]
        out = io.StringIO()
        rc = superpowers_cli.main(argv, env_fn=lambda: dict(self.env),
                                  route_all_fn=self._route_all, stdout=out)
        return rc, json.loads(out.getvalue())

    def test_real_quota_69_and_75_move_a_flagged_lane(self):
        for result in (QUOTA_69, QUOTA_75):
            with self.subTest(result=result):
                self.assertEqual(self._run("lane-a", result),
                                 (0, {"switched": True, "key": "lane-b", "exclude": ["lane-a"]}))

    def test_transient_69_and_75_never_switch(self):
        for result in (TRANSIENT_69, TRANSIENT_75):
            with self.subTest(result=result):
                self.assertEqual(self._run("lane-a", result),
                                 (1, {"switched": False, "reason": "not quota"}))
        self.assertEqual(self.route_calls, [])
        self.assertEqual(dispatch_injection.dispatch_classification(TRANSIENT_69)["class"],
                         "quota")
        self.assertEqual(dispatch_injection.dispatch_classification(TRANSIENT_75)["class"],
                         "quota_cycle")

    def test_unflagged_lane_on_quota_stops_and_reports(self):
        self.assertEqual(self._run("lane-b", QUOTA_69),
                         (1, {"switched": False, "reason": "unflagged"}))
        self.assertEqual(self.route_calls, [])
        self.assertEqual(self._run("lane-z", QUOTA_69),
                         (1, {"switched": False, "reason": "unknown lane"}))
        self.assertEqual(self.route_calls, [])

    def test_no_eligible_fallback_reports_without_dispatch(self):
        no_fallback = (1, {"switched": False, "reason": "no fallback"})
        self._write(ROSTER.replace('model = "fake/placeholder-model-2"\npurpose = "execute"',
                                   'model = "fake/placeholder-model-2"\npurpose = "execute"\n'
                                   'usage_limited = true'))
        self.assertEqual(self._run("lane-a", QUOTA_69), no_fallback)
        self._write(ROSTER)
        self.assertEqual(self._run("lane-a", QUOTA_69, exclude=["lane-b"]), no_fallback)
        self.assertEqual(self._run("lane-a", QUOTA_69, ladder=("lane-a",)), no_fallback)

    def test_first_eligible_fallback_skips_a_lane_outside_the_task(self):
        self._write(ROSTER_ABC)
        self.assertEqual(self._run("lane-a", QUOTA_69, ladder=("lane-a", "lane-c")),
                         (0, {"switched": True, "key": "lane-c", "exclude": ["lane-a"]}))
        self.assertEqual(self._run("lane-a", QUOTA_69, ladder=("lane-a", "lane-b", "lane-c")),
                         (0, {"switched": True, "key": "lane-b",
                              "exclude": ["lane-a", "lane-c"]}))

    def test_rounds_four_five_switch_stays_inside_the_gate(self):
        self._write(ROSTER_GATE)
        ladder = ("lane-top", "lane-mid", "lane-anchor")
        gate = self._gate_file("lane-anchor", ladder)
        with open(gate, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), ["lane-anchor"])
        self.assertEqual(
            self._run_files("lane-top", QUOTA_69, [self._exclude(["lane-top"]), gate], ladder),
            (0, {"switched": True, "key": "lane-mid", "exclude": ["lane-anchor", "lane-top"]}))
        tried = self._exclude(["lane-top", "lane-mid"])
        for files in ([tried, gate], [gate, tried]):
            with self.subTest(gate_first=files[0] == gate):
                self.assertEqual(self._run_files("lane-top", QUOTA_69, files, ladder),
                                 (1, {"switched": False, "reason": "no fallback"}))

    def test_both_flags_off_switch_never_moves_the_stuck_lane(self):
        self._write(ROSTER_OFF)
        ladder = ("lane-other", "lane-anchor")
        gate = self._gate_file("lane-anchor", ladder)
        tried = self._exclude(["lane-anchor"])
        for files in ([tried, gate], [gate, tried]):
            with self.subTest(gate_first=files[0] == gate):
                self.assertEqual(self._run_files("lane-anchor", QUOTA_69, files, ladder),
                                 (1, {"switched": False, "reason": "no fallback"}))
        self.assertEqual(self._run_files("lane-anchor", QUOTA_69, [tried], ladder),
                         (0, {"switched": True, "key": "lane-other", "exclude": ["lane-anchor"]}))

    def test_unreadable_inputs_exit_two(self):
        good = [self._result(QUOTA_69), self._exclude([]), self._injection(("lane-a", "lane-b"))]
        flags = ("--dispatch-result", "--exclude-keys-file", "--injection-file")
        bad = ((0, "not json"), (0, "[]"), (1, "not json"), (1, "{}"), (2, "not json"),
               (2, '{"ladder_keys": "lane-a"}'), (2, '{"mode": "external_cli"}'))
        for index, text in bad:
            with self.subTest(flag=flags[index], text=text):
                files = list(good)
                files[index] = self._raw(text)
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stderr(err):
                    rc = self._main("lane-a", files, out)
                self.assertEqual(rc, 2)
                self.assertEqual(out.getvalue(), "")
                self.assertEqual(
                    err.getvalue(),
                    f"ai-kit-spec: executor-fallback: unreadable {flags[index]} "
                    f"{files[index]}\n")
                self.assertEqual(self.route_calls, [])


if __name__ == "__main__":
    unittest.main()
