"""XAI-01/XAI-02 selection tests: execution targets, D-39 defaults, value helpers."""
from __future__ import annotations

import copy
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"),
)

from ai_kit_gsd_curated_config import cross_ai, gsd_catalog, host, plan_io, plan_schema, recommend

from tests.test_curated_config_recommend import (
    build,
    cand,
    entry_map,
    make_inventory,
    run_recommend,
)


def exec_cand(model: str, runtime: str, execution: float = 80.0, price: float = 2.0, **fields):
    scores = {"execution": execution, "planning": 1.0, "general": 1.0, "review": 1.0}
    return cand(
        model,
        runtime=runtime,
        is_host=False,
        score_axes=1,
        purpose_scores=scores,
        price=price,
        **fields,
    )


def _all_runners_inv(host_name: str, execution: float = 90.0):
    cands = [
        exec_cand(f"m-{rid}", cross_ai.RUNNER_CLI[rid], execution=execution)
        for rid in cross_ai.RUNNER_CLI
    ]
    inv = make_inventory(host=host_name, candidates=cands)
    inv["installed_runtimes"] = sorted(set(cross_ai.RUNNER_CLI.values()))
    return inv


class TestExecTargetsEndToEnd(unittest.TestCase):
    def test_pi_host_skips_itself(self):
        inv = make_inventory(
            host="pi",
            candidates=[
                exec_cand("m-cursor", "cursor-agent"),
                exec_cand("m-opencode", "opencode"),
                exec_cand("m-pi", "pi"),
            ],
        )
        inv["installed_runtimes"] = ["cursor-agent", "opencode", "pi"]
        code, plan, _, err = run_recommend(
            inv, "--profile", "adaptive", "--rigor", "standard", "--cross-ai-exec", "y"
        )
        self.assertEqual((code, err), (0, ""))
        assert plan is not None
        self.assertEqual(plan["artifacts"][0]["config"]["prefer"], ["cursor", "opencode"])

    def test_claude_without_pi_falls_to_cursor(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                exec_cand("m-cursor", "cursor-agent"),
                exec_cand("m-opencode", "opencode"),
            ],
        )
        inv["installed_runtimes"] = ["cursor-agent", "opencode"]
        code, plan, _, err = run_recommend(inv, "--profile", "adaptive", "--rigor", "standard")
        self.assertEqual((code, err), (0, ""))
        assert plan is not None
        self.assertEqual(plan["artifacts"][0]["config"]["prefer"][0], "cursor")
        entry = entry_map(plan)["workflow.cross_ai_execution"]
        self.assertTrue(entry["value"])
        self.assertTrue(plan["cross_ai"]["exec"]["defaulted"])


class TestExecTargets(unittest.TestCase):
    def test_preference_order_not_install_order(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                exec_cand("m-opencode", "opencode"),
                exec_cand("m-cursor", "cursor-agent"),
                exec_cand("m-pi", "pi"),
            ],
        )
        inv["installed_runtimes"] = ["opencode", "cursor-agent", "pi"]
        targets = cross_ai.exec_targets(inv, "standard")
        self.assertEqual([t.cli for t in targets], ["pi", "cursor", "opencode"])

    def test_custom_prefer_tuple(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                exec_cand("m-opencode", "opencode"),
                exec_cand("m-pi", "pi"),
            ],
        )
        inv["installed_runtimes"] = ["opencode", "pi"]
        targets = cross_ai.exec_targets(inv, "standard", prefer=("opencode", "pi"))
        self.assertEqual([t.cli for t in targets], ["opencode", "pi"])

    def test_grok_installed_never_target(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                exec_cand("m-grok", "grok"),
                exec_cand("m-cursor", "cursor-agent"),
            ],
        )
        inv["installed_runtimes"] = ["grok", "cursor-agent"]
        targets = cross_ai.exec_targets(inv, "standard")
        self.assertEqual([t.cli for t in targets], ["cursor"])

    def test_claude_in_prefer_skipped(self):
        inv = make_inventory(
            host="pi",
            candidates=[exec_cand("m-cursor", "cursor-agent")],
        )
        inv["installed_runtimes"] = ["cursor-agent"]
        targets = cross_ai.exec_targets(inv, "standard", prefer=("claude", "cursor"))
        self.assertEqual([t.cli for t in targets], ["cursor"])

    def test_host_never_a_target(self):
        for host_name in host.HOSTS:
            with self.subTest(host=host_name):
                inv = _all_runners_inv(host_name)
                targets = cross_ai.exec_targets(inv, "standard")
                for target in targets:
                    mapped = cross_ai.RUNNER_CLI.get(target.cli)
                    self.assertNotEqual(mapped, host_name)

    def test_equal_execution_score_breaks_by_price(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                exec_cand("z-cursor", "cursor-agent", execution=50.0, price=4.0),
                exec_cand("a-cursor", "cursor-agent", execution=50.0, price=1.0),
            ],
        )
        inv["installed_runtimes"] = ["cursor-agent"]
        target = cross_ai.exec_targets(inv, "standard")[0]
        self.assertEqual(target.model, "a-cursor")

    def test_equal_price_breaks_by_model_id(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                exec_cand("b-cursor", "cursor-agent", execution=50.0, price=2.0),
                exec_cand("a-cursor", "cursor-agent", execution=50.0, price=2.0),
            ],
        )
        inv["installed_runtimes"] = ["cursor-agent"]
        target = cross_ai.exec_targets(inv, "standard")[0]
        self.assertEqual(target.model, "a-cursor")

    def test_at_ceiling_beats_above_ceiling_higher_score(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                exec_cand("cheap", "cursor-agent", execution=70.0, price=1.0),
                exec_cand("dear", "cursor-agent", execution=95.0, price=100.0),
            ],
        )
        inv["installed_runtimes"] = ["cursor-agent"]
        target = cross_ai.exec_targets(inv, "mvp")[0]
        self.assertEqual(target.model, "cheap")

    def test_confirmed_router_beats_catalog(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                exec_cand("catalog-high", "cursor-agent", execution=99.0, price=1.0),
                cand(
                    "router-env/run",
                    runtime="cursor-agent",
                    is_host=False,
                    is_router=True,
                    router_confirmed=True,
                    name_declared_purpose="execute",
                    score_axes=0,
                    purpose_scores={},
                ),
            ],
        )
        inv["installed_runtimes"] = ["cursor-agent"]
        target = cross_ai.exec_targets(inv, "standard")[0]
        self.assertEqual(target.model, "router-env/run")
        self.assertTrue(target.router_backed)

    def test_unconfirmed_router_not_used(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                exec_cand("catalog-pick", "cursor-agent", execution=80.0, price=1.0),
                cand(
                    "router-env/run",
                    runtime="cursor-agent",
                    is_host=False,
                    is_router=True,
                    router_confirmed=False,
                    name_declared_purpose="execute",
                    score_axes=0,
                    purpose_scores={},
                ),
            ],
        )
        inv["installed_runtimes"] = ["cursor-agent"]
        target = cross_ai.exec_targets(inv, "standard")[0]
        self.assertEqual(target.model, "catalog-pick")
        self.assertFalse(target.router_backed)

    def test_no_candidates_needs_choice(self):
        inv = make_inventory(host="claude", candidates=[])
        inv["installed_runtimes"] = ["cursor-agent"]
        targets = cross_ai.exec_targets(inv, "standard")
        self.assertEqual(len(targets), 1)
        self.assertIsNone(targets[0].model)
        artifact = cross_ai.script_artifact(targets, cross_ai.MIN_TIMEOUT_S)
        self.assertEqual(artifact["status"], "needs_choice")
        self.assertEqual(artifact["choices"]["cursor"]["candidates"], [])


class TestExecDefault(unittest.TestCase):
    def test_claude_defaults_exec_y_with_targets(self):
        for rigor in ("mvp", "standard", "rigorous"):
            with self.subTest(rigor=rigor):
                inv = _all_runners_inv("claude")
                plan = build(inv, rigor=rigor)
                entry = entry_map(plan)["workflow.cross_ai_execution"]
                self.assertTrue(entry["value"])
                self.assertIn("defaulted", entry["why"])

    def test_claude_no_target_defaults_n_with_note(self):
        inv = make_inventory(host="claude", candidates=[])
        inv["installed_runtimes"] = []
        plan = build(inv, rigor="standard")
        entry = entry_map(plan)["workflow.cross_ai_execution"]
        self.assertFalse(entry["value"])
        kinds = {n["kind"] for n in plan["notes"]}
        self.assertIn("cross_ai_exec", kinds)

    def test_codex_no_target_note(self):
        inv = make_inventory(host="codex", candidates=[])
        inv["installed_runtimes"] = []
        plan = build(inv, rigor="standard")
        entry = entry_map(plan)["workflow.cross_ai_execution"]
        self.assertFalse(entry["value"])

    def test_non_delegate_hosts_default_n(self):
        for host_name in ("opencode", "cursor", "pi"):
            with self.subTest(host=host_name):
                inv = _all_runners_inv(host_name)
                plan = build(inv, rigor="standard")
                entry = entry_map(plan)["workflow.cross_ai_execution"]
                self.assertFalse(entry["value"])

    def test_explicit_y_no_target_needs_choice(self):
        inv = make_inventory(host="claude", candidates=[])
        inv["installed_runtimes"] = []
        plan = build(inv, rigor="standard", cross_ai_exec="y")
        cmd = entry_map(plan)["workflow.cross_ai_command"]
        self.assertEqual(cmd.get("status"), "needs_choice")
        self.assertIsNone(cmd["value"])
        self.assertEqual(plan["artifacts"], [])

    def test_build_plan_is_pure(self):
        inv = _all_runners_inv("claude")
        before = copy.deepcopy(inv)
        opts = recommend.RecommendOpts("adaptive", "standard")
        plan_a = recommend.build_plan(inv, opts)
        plan_b = recommend.build_plan(inv, opts)
        self.assertEqual(inv, before)
        self.assertEqual(
            plan_schema.canonical_json(plan_a),
            plan_schema.canonical_json(plan_b),
        )

    def test_write_plan_replace_failure_keeps_old_bytes(self):
        cache = gsd_catalog.load_ai_kit_spec_module("cache")
        assert cache is not None
        plan_a = {"schema_version": 1, "entries": []}
        plan_b = {"schema_version": 1, "entries": [{"key": "x"}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(path, plan_a)
            with open(path, "rb") as handle:
                old_bytes = handle.read()
            with (
                mock.patch.object(cache.os, "replace", side_effect=OSError("injected")),
                self.assertRaises(OSError),
            ):
                plan_io.write_plan(path, plan_b)
            with open(path, "rb") as handle:
                self.assertEqual(handle.read(), old_bytes)
            self.assertEqual(os.listdir(tmp), ["plan.json"])


class TestValues(unittest.TestCase):
    def test_timeout_value(self):
        cases = [
            (None, 1800),
            (1799, 1800),
            (1800, 1800),
            (3600, 3600),
            (True, 1800),
            ("3600", 1800),
        ]
        for existing, want in cases:
            with self.subTest(existing=existing):
                self.assertEqual(cross_ai.timeout_value(existing), want)

    def test_manager_flags_value(self):
        self.assertEqual(cross_ai.manager_flags_value(None), "--cross-ai")
        self.assertEqual(cross_ai.manager_flags_value("--auto"), "--auto --cross-ai")
        self.assertEqual(
            cross_ai.manager_flags_value("--cross-ai --auto"),
            "--cross-ai --auto",
        )
        self.assertEqual(
            cross_ai.manager_flags_value("--cross-ai-x"),
            "--cross-ai-x --cross-ai",
        )


if __name__ == "__main__":
    unittest.main()
