"""jev's executor pick: fake jev only, never a real client."""

import io
import json
import os
import re
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-execute-superpowers"))

from ai_kit_spec import executor_pick, jev_names
from ai_kit_spec_superpowers import cli as superpowers_cli
from ai_kit_spec_superpowers import dispatch_injection

KEYS = ["a/one", "b/two", "c/three"]
CANDIDATES = [{"key": k, "model": f"placeholder-model-{i + 1}", "runtime": "codex",
               "vendor": "v", "task_affinity": None, "context_limit": None}
              for i, k in enumerate(KEYS)]


def answers_run(table, calls):
    def run(argv, input="", **kwargs):
        calls.append({"payload": json.loads(input), "cwd": kwargs.get("cwd")})
        items = {
            item["id"]: {"decided_by": "fake", "fake": table[item["id"]]}
            for item in json.loads(input)["items"] if item["id"] in table
        }
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"items": items}), stderr="")
    return run


def jev_root(case) -> tuple:
    """(skills root holding a jev client, env with a scratch HOME)."""
    tmp = tempfile.TemporaryDirectory()
    case.addCleanup(tmp.cleanup)
    entry_dir = os.path.join(tmp.name, "skills", "jev-fast-decision", "scripts")
    os.makedirs(entry_dir)
    with open(os.path.join(entry_dir, "jev_review.py"), "w", encoding="utf-8"):
        pass
    return os.path.join(tmp.name, "skills"), {"HOME": os.path.join(tmp.name, "home")}


def never_run(*_argv, **_kwargs):
    raise AssertionError("jev must not be called")


class TestResolveInjectionPick(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.task = os.path.join(self.root, "task-1-brief.md")
        with open(self.task, "w", encoding="utf-8") as handle:
            handle.write("### Task 1\n**Files:**\n- Create: `README.md`\n")

    def resolve(self, run, *, exclude="[]", escalation="[]", extra=()):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stderr(err):
            rc = superpowers_cli.main(
                ["resolve-injection", "--cwd", self.root, "--task-file", self.task,
                 "--quota-path", os.path.join(self.root, "quota.json"),
                 "--exclude-keys-json", exclude, "--excluded-reasons-json", "{}",
                 "--escalation-excluded-keys-json", escalation, *extra],
                assemble_candidates_fn=lambda cwd, env: (CANDIDATES, KEYS),
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, ks, existing, _ttl: {},
                route_all_fn=lambda entries, _ctx: {e["key"]: "subprocess" for e in entries},
                run_fn=run, stdout=out)
        return rc, json.loads(out.getvalue()), err.getvalue()

    def test_confident_pick_goes_first_and_is_logged(self):
        calls = []
        with mock.patch.object(jev_names, "find_jev", return_value="fake-entry"):
            runner = answers_run({"x0": {"choice": "c2", "top": 0.95}}, calls)
            rc, result, err = self.resolve(runner)
        self.assertEqual(rc, 0)
        self.assertEqual(result["key"], "b/two")
        self.assertEqual(result["ladder_keys"], KEYS)
        self.assertEqual(result["pick"],
                         {"decided_by": "jev", "confidence": 0.95, "note": ""})
        self.assertIn("ai-kit-spec: executor pick: b/two (jev, 0.95)", err)
        # labels only: the one offered item carries the locked question over opaque tokens,
        # never a roster key or model name
        item = calls[0]["payload"]["items"][0]
        self.assertEqual(item["instructions"], executor_pick.PICK_QUESTION)
        self.assertEqual(item["criteria"],
                         {"c1": "candidate 1", "c2": "candidate 2", "c3": "candidate 3"})
        self.assertEqual(len(calls), 1)

    def test_no_jev_keeps_todays_order(self):
        def run(*_argv, **_kwargs):
            raise AssertionError("jev must not be called")
        with mock.patch.object(jev_names, "find_jev", return_value=None):
            rc, result, err = self.resolve(run)
        self.assertEqual(rc, 0)
        self.assertEqual(result["key"], "a/one")
        self.assertEqual(result["pick"],
                         {"decided_by": "default", "confidence": None, "note": "jev absent"})
        self.assertIn("ai-kit-spec: executor pick: a/one (default: jev absent)", err)

    def test_fix_round_and_escalation_skip_the_pick(self):
        with mock.patch.object(jev_names, "find_jev", return_value="fake-entry"):
            rc, result, err = self.resolve(never_run, extra=("--fix-round", "1"))
        self.assertEqual(rc, 0)
        self.assertNotIn("pick", result)
        self.assertNotIn("executor pick:", err)
        with mock.patch.object(jev_names, "find_jev", return_value="fake-entry"):
            rc, result, err = self.resolve(never_run, escalation='["c/three"]')
        self.assertEqual(rc, 0)
        self.assertNotIn("pick", result)
        self.assertNotIn("executor pick:", err)

    def test_excluded_key_is_never_offered(self):
        calls = []
        run = answers_run({"x0": {"choice": "c2", "top": 0.95}}, calls)
        with mock.patch.object(jev_names, "find_jev", return_value="fake-entry"):
            rc, _result, _err = self.resolve(run, exclude='["a/one"]')
        self.assertEqual(rc, 0)
        self.assertEqual(len(calls[0]["payload"]["items"][0]["criteria"]), 2)

    def test_one_survivor_asks_nothing(self):
        rc, result, err = self.resolve(never_run, exclude='["a/one", "b/two"]')
        self.assertEqual(rc, 0)
        self.assertEqual(result["key"], "c/three")
        self.assertIn("ai-kit-spec: executor pick: c/three (default: one candidate)", err)

    def test_undecodable_jev_reply_keeps_todays_order(self):
        def run(*_argv, **_kwargs):
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        with mock.patch.object(jev_names, "find_jev", return_value="fake-entry"):
            rc, result, err = self.resolve(run)
        self.assertEqual(rc, 0)
        self.assertEqual(result["key"], "a/one")
        self.assertEqual(result["pick"],
                         {"decided_by": "default", "confidence": None, "note": "jev low"})
        self.assertIn("ai-kit-spec: executor pick: a/one (default: jev low)", err)


class TestPickExecutor(unittest.TestCase):
    labels = executor_pick.candidate_labels(CANDIDATES, {}, "backend", {})

    def test_jev_absent_keeps_todays_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"HOME": os.path.join(tmp, "home")}
            pick = executor_pick.pick_executor(CANDIDATES, self.labels, env, never_run,
                                              own_root=tmp)
        self.assertEqual(pick, executor_pick.Pick(None, "default", None, "jev absent"))

    def test_one_or_zero_candidates_ask_nothing(self):
        root, env = jev_root(self)
        one = executor_pick.pick_executor([CANDIDATES[0]], self.labels[:1], env, never_run,
                                          own_root=root)
        zero = executor_pick.pick_executor([], [], env, never_run, own_root=root)
        self.assertEqual(one, executor_pick.Pick(None, "default", None, "one candidate"))
        self.assertEqual(zero, executor_pick.Pick(None, "default", None, "one candidate"))

    def test_too_many_candidates_ask_nothing(self):
        root, env = jev_root(self)
        twelve = [{"key": f"k/{n}", "model": f"placeholder-model-{n}", "runtime": "codex",
                   "vendor": "v", "task_affinity": None, "context_limit": None}
                  for n in range(1, 13)]
        labels = executor_pick.candidate_labels(twelve, {}, "backend", {})
        pick = executor_pick.pick_executor(twelve, labels, env, never_run, own_root=root)
        self.assertEqual(pick, executor_pick.Pick(None, "default", None, "too many candidates"))

    def test_confident_pick_names_the_key(self):
        root, env = jev_root(self)
        calls = []
        pick = executor_pick.pick_executor(
            CANDIDATES, self.labels, env, answers_run({"x0": {"choice": "c2", "top": 0.95}},
                                                      calls), own_root=root)
        self.assertEqual(pick, executor_pick.Pick("b/two", "jev", 0.95, ""))
        self.assertEqual(len(calls), 1)

    def test_low_top_stays_default(self):
        root, env = jev_root(self)
        pick = executor_pick.pick_executor(
            CANDIDATES, self.labels, env, answers_run({"x0": {"choice": "c2", "top": 0.5}}, []),
            own_root=root)
        self.assertEqual(pick, executor_pick.Pick(None, "default", 0.5, "jev low"))

    def test_needs_fallback_stays_default(self):
        root, env = jev_root(self)
        pick = executor_pick.pick_executor(
            CANDIDATES, self.labels, env,
            answers_run({"x0": {"choice": "c2", "top": 0.9, "needs_fallback": True}}, []),
            own_root=root)
        self.assertEqual(pick, executor_pick.Pick(None, "default", 0.9, "jev low"))

    def test_failed_run_stays_default(self):
        root, env = jev_root(self)

        def run(argv, input="", **_kwargs):
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom")
        pick = executor_pick.pick_executor(CANDIDATES, self.labels, env, run, own_root=root)
        self.assertEqual(pick, executor_pick.Pick(None, "default", None, "jev low"))

    def test_undecodable_run_stays_default(self):
        root, env = jev_root(self)

        def run(*_argv, **_kwargs):
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        pick = executor_pick.pick_executor(CANDIDATES, self.labels, env, run, own_root=root)
        self.assertEqual(pick, executor_pick.Pick(None, "default", None, "jev low"))

    def test_answer_outside_the_criteria_is_low(self):
        root, env = jev_root(self)
        pick = executor_pick.pick_executor(
            CANDIDATES, self.labels, env, answers_run({"x0": {"choice": "c9", "top": 0.95}}, []),
            own_root=root)
        self.assertEqual(pick, executor_pick.Pick(None, "default", None, "jev low"))

    def test_pick_outside_the_roster_is_discarded(self):
        root, env = jev_root(self)
        with mock.patch.object(jev_names, "ask_items", return_value={"x0": ("c9", 0.95, "")}):
            pick = executor_pick.pick_executor(CANDIDATES, self.labels, env, never_run,
                                              own_root=root)
        self.assertEqual(pick, executor_pick.Pick(None, "default", 0.95,
                                                  "pick outside the roster discarded"))

    def test_dispatch_record_names_the_deciding_side(self):
        self.assertEqual(executor_pick.dispatch_record(
            executor_pick.Pick("b/two", "jev", 0.95, ""), "b/two"),
            {"decided_by": "jev", "confidence": 0.95, "note": ""})
        self.assertEqual(executor_pick.dispatch_record(
            executor_pick.Pick("c/three", "jev", 0.95, ""), "a/one"),
            {"decided_by": "default", "confidence": 0.95, "note": "jev pick unavailable"})
        self.assertEqual(executor_pick.dispatch_record(
            executor_pick.Pick(None, "default", None, "jev low"), "a/one"),
            {"decided_by": "default", "confidence": None, "note": "jev low"})

    def test_payload_holds_labels_only(self):
        root, env = jev_root(self)
        calls = []
        pick = executor_pick.pick_executor(
            CANDIDATES, self.labels, env, answers_run({"x0": {"choice": "c2", "top": 0.95}},
                                                      calls), own_root=root)
        self.assertEqual(pick, executor_pick.Pick("b/two", "jev", 0.95, ""))
        payload = calls[0]["payload"]
        self.assertEqual(len(payload["items"]), 1)
        item = payload["items"][0]
        self.assertEqual(item["id"], "x0")
        self.assertIsNotNone(re.fullmatch(
            r"Task type: [a-z]+\.( c[0-9]+: route [a-z_]+, effort [a-z]+, class [a-z]+, "
            r"affinity [a-z]+\.)+", item["context"]), item["context"])
        for value in item["criteria"].values():
            self.assertIsNotNone(re.fullmatch(r"candidate [0-9]+", value), value)
        text = json.dumps(payload)
        for needle in ("a/one", "b/two", "c/three", "placeholder-model-1", "placeholder-model-2",
                       "placeholder-model-3", "codex", "placeholder-model", "router-env"):
            self.assertNotIn(needle, text)


class TestLabels(unittest.TestCase):
    entries = {"fake/placeholder-model-1": {
        "runtimes": {"codex": {"model_id": "placeholder-model-1"}},
        "facts": {"class": {"value": "small"}}}}

    def test_catalog_class_reads_the_entry_facts(self):
        self.assertEqual(executor_pick.catalog_class(self.entries, CANDIDATES[0]), "small")

    def test_catalog_class_reads_unknown_shapes_as_unknown(self):
        no_facts = {"fake/placeholder-model-1":
                    {"runtimes": {"codex": {"model_id": "placeholder-model-1"}}}}
        weird = {"fake/placeholder-model-1": {
            "runtimes": {"codex": {"model_id": "placeholder-model-1"}},
            "facts": {"class": {"value": "weird"}}}}
        self.assertEqual(executor_pick.catalog_class(no_facts, CANDIDATES[0]), "unknown")
        self.assertEqual(executor_pick.catalog_class(weird, CANDIDATES[0]), "unknown")
        self.assertEqual(
            executor_pick.catalog_class(self.entries, {"key": "x", "runtime": None, "model": "m"}),
            "unknown")

    def test_candidate_labels_pin_route_effort_and_task(self):
        candidates = [
            {"key": "a/one", "model": "placeholder-model-1", "runtime": "codex",
             "effort": "high"},
            {"key": "b/two", "model": "placeholder-model-2", "runtime": "codex"},
            {"key": "c/three", "model": "placeholder-model-3", "runtime": "codex",
             "effort": "turbo"},
            {"key": "s/one", "model": "", "runtime": None},
        ]
        labels = executor_pick.candidate_labels(candidates, {"a/one": "native"}, None, {})
        self.assertEqual([lab["route"] for lab in labels],
                         ["native", "external_cli", "external_cli", "session"])
        self.assertEqual([lab["effort"] for lab in labels], ["high", "none", "other", "none"])
        self.assertEqual(labels[0]["task"], "none")

    def test_pick_line_formats_both_sides(self):
        self.assertEqual(
            executor_pick.pick_line("b/two", {"decided_by": "jev", "confidence": 0.951,
                                             "note": ""}),
            "ai-kit-spec: executor pick: b/two (jev, 0.95)")
        self.assertEqual(
            executor_pick.pick_line("a/one", {"decided_by": "default", "confidence": None,
                                             "note": "jev low"}),
            "ai-kit-spec: executor pick: a/one (default: jev low)")


class TestWalkOrder(unittest.TestCase):
    task = "### Task 1\n**Files:**\n- Create: `README.md`\n"

    def setUp(self):
        self.offered = []

    def opts(self, seam, pick_fn, routes=None):
        return dispatch_injection.BuildInjectionOptions(
            quota={}, seams=dispatch_injection.BuildInjectionSeams(resolve_ladder_pick_fn=seam),
            routes=routes or {k: "subprocess" for k in KEYS}, pick_fn=pick_fn)

    def request(self, candidates=None, top_n_keys=None):
        return dispatch_injection.BuildInjectionRequest(
            self.task, candidates or CANDIDATES, {}, {}, top_n_keys or KEYS)

    def jev(self, key):
        def pick_fn(candidates):
            self.offered.extend(c["key"] for c in candidates)
            return executor_pick.Pick(key, "jev", 0.95, "")
        return pick_fn

    def test_picked_key_goes_first_and_absent_leaves_todays_order(self):
        seen = []

        def record(ranked, remaining, skip_vendor, quota):
            seen.append(list(remaining))
            return None

        cases = ((self.jev("c/three"), ["c/three", "a/one", "b/two"]),
                 (self.jev("z/none"), KEYS),
                 (None, KEYS))
        for pick_fn, expected in cases:
            with self.subTest(expected=expected):
                seen.clear()
                err = io.StringIO()
                with redirect_stderr(err), self.assertRaises(
                        dispatch_injection.QuotaExhaustedError):
                    dispatch_injection.build_dispatch_injection(
                        self.request(), options=self.opts(record, pick_fn))
                self.assertEqual(seen, [expected])
                self.assertNotIn("executor pick:", err.getvalue())

    def test_offered_set_equals_the_walk_set(self):
        routes = {"a/one": "subprocess", "b/two": "not_installed", "c/three": "subprocess"}

        def seam(ranked, remaining, skip_vendor, quota):
            return types.SimpleNamespace(key=remaining[0])

        err = io.StringIO()
        with redirect_stderr(err):
            result = dispatch_injection.build_dispatch_injection(
                self.request(), options=self.opts(seam, self.jev("c/three"), routes=routes))
        ranked = dispatch_injection._narrow_and_rank(self.request(), routes)[2]
        self.assertEqual(self.offered, [c["key"] for c in ranked
                                        if routes[c["key"]] != "not_installed"])
        self.assertEqual(self.offered, ["a/one", "c/three"])
        self.assertEqual(result["key"], "c/three")

    def test_blocked_pick_logs_the_dispatched_key(self):
        def seam(ranked, remaining, skip_vendor, quota):
            return types.SimpleNamespace(key=next(k for k in remaining if k != "c/three"))

        err = io.StringIO()
        with redirect_stderr(err):
            result = dispatch_injection.build_dispatch_injection(
                self.request(), options=self.opts(seam, self.jev("c/three")))
        self.assertEqual(result["key"], "a/one")
        self.assertEqual(result["pick"], {"decided_by": "default", "confidence": 0.95,
                                          "note": "jev pick unavailable"})
        self.assertIn("ai-kit-spec: executor pick: a/one (default: jev pick unavailable)",
                      err.getvalue())

    def test_native_injection_carries_effort(self):
        candidates = [{**CANDIDATES[0], "effort": "high"}, {**CANDIDATES[1], "effort": None}]
        routes = {k: "native" for k in ("a/one", "b/two")}

        def seam(ranked, remaining, skip_vendor, quota):
            return types.SimpleNamespace(key=remaining[0])

        for top_n_keys, effort in ((["a/one", "b/two"], "high"), (["b/two", "a/one"], "")):
            with self.subTest(top_n_keys=top_n_keys):
                err = io.StringIO()
                with redirect_stderr(err):
                    result = dispatch_injection.build_dispatch_injection(
                        self.request(candidates, top_n_keys),
                        options=self.opts(seam, None, routes=routes))
                self.assertEqual(result["mode"], "native")
                self.assertEqual(result["effort"], effort)

    def test_skill_passes_native_effort(self):
        skill = (Path(__file__).resolve().parents[1] / "skills"
                 / "ai-kit-spec-execute-superpowers" / "SKILL.md")
        text = " ".join(skill.read_text(encoding="utf-8").split())
        self.assertIn("pass `model` and `effort` as the `Agent` tool's `model` and `effort` "
                      "parameters (omit each when empty)", text)


if __name__ == "__main__":
    unittest.main()
