"""37-18: the runner's --describe fact in the snapshot and in routing (SPEC R9, D-10)."""
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import cli, routing, runner_facts
from ai_kit_spec.cache import cache_read_json, cache_write_json
from ai_kit_spec.detection import cache_runtimes_path
from ai_kit_spec.tooling_guidance import resolve_cross_ai_template_path

DESCRIBE = {"schema": 1, "classes": ["x"], "runtimes": {
    "pi": {"formulas": {"exec": True, "review": True, "resume": True}},
    "placeholder-cli-1": {"formulas": {"exec": False, "review": True, "resume": False}},
    "claude": {"formulas": {"exec": False}},
}}


def fact():
    return {"template_sha256": runner_facts.template_sha256(resolve_cross_ai_template_path()),
            "describe": DESCRIBE}


def fake_run(argv, **kwargs):
    return subprocess.CompletedProcess(argv, 0, json.dumps(DESCRIBE), "AIKIT-XAI status=ok")


def seams():
    return routing.RuntimesSeams(lambda name: "node-bin" if name == "node" else None,
                                 fake_run, None, None)


class TestFactReader(unittest.TestCase):
    def test_runner_has_exec(self):
        current = fact()
        self.assertIs(runner_facts.runner_has_exec(current, "pi"), True)
        self.assertIs(runner_facts.runner_has_exec(current, "placeholder-cli-1"), False)
        self.assertIsNone(runner_facts.runner_has_exec(current, "codex"))
        for bad in (None, "garbage", {**current, "template_sha256": "0" * 64},
                    {**current, "describe": None},
                    {**current, "describe": {"runtimes": {"pi": {"formulas": {"exec": "yes"}}}}}):
            self.assertIsNone(runner_facts.runner_has_exec(bad, "pi"))

    def test_read_runner_describe(self):
        calls = []
        def run(argv, **kwargs):
            calls.append(argv)
            return fake_run(argv, **kwargs)
        template = resolve_cross_ai_template_path()
        self.assertEqual(runner_facts.read_runner_describe("node-bin", template, run), fact())
        self.assertEqual(calls, [["node-bin", template, "--describe"]])
        self.assertIsNone(runner_facts.read_runner_describe(None, template, run)["describe"])
        self.assertEqual(len(calls), 1)
        for output, code in (("not json", 0), ("[]", 0), ("{}", 0),
                             (json.dumps(DESCRIBE), 1)):
            def bad(argv, output=output, code=code, **kwargs):
                return subprocess.CompletedProcess(argv, code, output, "")
            self.assertIsNone(
                runner_facts.read_runner_describe("node-bin", template, bad)["describe"])
        for error in (OSError(), subprocess.TimeoutExpired("node-bin", 1)):
            def raises(argv, error=error, **kwargs):
                raise error
            self.assertIsNone(
                runner_facts.read_runner_describe("node-bin", template, raises)["describe"])

    def test_template_sha256(self):
        self.assertIsNone(runner_facts.template_sha256(None))
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "template"
            path.write_bytes(b"example")
            self.assertEqual(runner_facts.template_sha256(str(path)),
                             hashlib.sha256(b"example").hexdigest())
            self.assertIsNone(runner_facts.template_sha256(str(path / "missing")))


class TestFactRefresh(unittest.TestCase):
    def test_fact_is_current_and_refresh(self):
        template = resolve_cross_ai_template_path()
        current = fact()
        self.assertTrue(runner_facts.fact_is_current(current, template))
        for bad in (None, {}, {**current, "describe": None},
                    {**current, "template_sha256": "0" * 64}):
            self.assertFalse(runner_facts.fact_is_current(bad, template))
        self.assertFalse(runner_facts.fact_is_current(
            {"template_sha256": None, "describe": {}}, None))
        with patch.object(runner_facts, "read_runner_describe",
                          wraps=runner_facts.read_runner_describe) as read:
            snapshot = {"runner": current}
            self.assertFalse(runner_facts.refresh_fact(snapshot, seams().which_fn, fake_run))
            read.assert_not_called()
            for old in (None, {**current, "describe": None},
                        {**current, "template_sha256": "0" * 64}):
                snapshot = {} if old is None else {"runner": old}
                self.assertTrue(runner_facts.refresh_fact(snapshot, seams().which_fn, fake_run))
                self.assertEqual(snapshot["runner"], current)

    def test_load_refreshes_a_stale_fact_atomically(self):
        with tempfile.TemporaryDirectory() as root:
            env = {"HOME": root, "XDG_CACHE_HOME": root}
            path = cache_runtimes_path(env)
            stale = {"runner": {**fact(), "template_sha256": "0" * 64}}
            cache_write_json(path, stale)
            with patch.object(routing, "runtimes_cache_is_fresh", return_value=True):
                before = Path(path).read_bytes()
                snapshot, built = routing.load_runtimes_snapshot(env, seams(), persist=False)
                self.assertFalse(built)
                self.assertEqual(snapshot["runner"], fact())
                self.assertEqual(Path(path).read_bytes(), before)
                snapshot, built = routing.load_runtimes_snapshot(env, seams())
                self.assertFalse(built)
                self.assertEqual(cache_read_json(path), snapshot)
                self.assertEqual(os.listdir(os.path.dirname(path)), ["runtimes.json"])

    def test_detect_runtimes_if_stale_refreshes_the_fact(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "runtimes.json")
            cache_write_json(path, {"runner": {**fact(), "template_sha256": "0" * 64}})
            with patch.object(routing, "runtimes_cache_is_fresh", return_value=True):
                for _ in range(2):
                    out = io.StringIO()
                    before = Path(path).read_bytes()
                    with redirect_stdout(out):
                        self.assertEqual(cli.main(["detect-runtimes", "--if-stale", path],
                                                  which_fn=seams().which_fn, run_fn=fake_run,
                                                  env_fn=lambda: {"HOME": root}), 0)
                    self.assertEqual(json.loads(out.getvalue()), {})
                    saved = cache_read_json(path)
                    assert saved is not None
                    self.assertEqual(saved["runner"], fact())
                    if _:
                        self.assertEqual(Path(path).read_bytes(), before)


class TestRoutesReadTheFact(unittest.TestCase):
    def test_fact_decides_no_formula(self):
        inv = routing.Inventory(frozenset({"pi"}), {"pi": ("fake/placeholder-model-1",)}, fact())
        self.assertEqual(routing.route(routing.RouteInput("pi", "fake/placeholder-model-1"),
                                       "codex", "exec", inv), "subprocess")
        entry = routing.RouteInput("placeholder-cli-1", "placeholder-model-1")
        self.assertEqual(routing.route(entry, "codex", "exec", inv), "no_formula")
        stale = inv._replace(runner={**fact(), "template_sha256": "0" * 64})
        self.assertEqual(routing.route(entry, "codex", "exec", stale), "unverified")
        self.assertEqual(routing.route(entry, "codex", "review", inv), "unverified")

    def test_runtime_outside_the_table_is_served(self):
        inv = routing.Inventory(frozenset(), {})
        entry = routing.RouteInput("placeholder-cli-1", "placeholder-model-1",
                                   "placeholder-cli-1 -p {prompt}")
        for mode in ("review", "exec"):
            self.assertEqual(routing.route(entry, "codex", mode, inv), "unverified")
        self.assertEqual(routing.route(entry._replace(model=""), "codex", "exec", inv), "no_model")

    def test_absent_or_unreadable_fact_never_refuses(self):
        values: list[Any] = [None, "garbage", {"describe": None}]
        for value in values:
            inv = routing.Inventory(frozenset({"claude"}),
                                    {"claude": ("placeholder-model-1",)}, value)
            self.assertEqual(routing.route(routing.RouteInput("claude", "placeholder-model-1"),
                                           "codex", "exec", inv), "subprocess")

    def test_skip_routes_and_detail(self):
        self.assertNotIn("no_inventory", routing.SKIP_ROUTES)
        self.assertIn("unknown_runtime", routing.SKIP_ROUTES)
        self.assertEqual(routing.no_formula_detail("claude"),
                         "the runner has no exec formula for claude "
                         "(cross-ai.mjs --describe, recorded in the runtimes snapshot)")
        self.assertEqual(routing.no_formula_detail(None),
                         "a custom command lane runs in review mode only")
