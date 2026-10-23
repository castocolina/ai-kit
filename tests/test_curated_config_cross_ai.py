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

from ai_kit_gsd_curated_config import (
    cross_ai,
    gsd_catalog,
    host,
    plan_io,
    plan_schema,
    recommend,
    roles,
)

from tests.test_curated_config_recommend import (
    _fixture_review_lanes,
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
        exec_cand(f"m-{rid}", rid, execution=execution)
        for rid in cross_ai.RUNNER_IDS
    ]
    inv = make_inventory(host=host_name, candidates=cands)
    inv["installed_runtimes"] = list(cross_ai.RUNNER_IDS)
    return inv


class TestExecTargetsEndToEnd(unittest.TestCase):
    def test_pi_host_skips_itself(self):
        inv = make_inventory(
            host="pi",
            candidates=[
                exec_cand("m-cursor", "cursor"),
                exec_cand("m-opencode", "opencode"),
                exec_cand("m-pi", "pi"),
            ],
        )
        inv["installed_runtimes"] = ["cursor", "opencode", "pi"]
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
                exec_cand("m-cursor", "cursor"),
                exec_cand("m-opencode", "opencode"),
            ],
        )
        inv["installed_runtimes"] = ["cursor", "opencode"]
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
                exec_cand("m-cursor", "cursor"),
                exec_cand("m-pi", "pi"),
            ],
        )
        inv["installed_runtimes"] = ["opencode", "cursor", "pi"]
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
                exec_cand("m-cursor", "cursor"),
            ],
        )
        inv["installed_runtimes"] = ["grok", "cursor"]
        targets = cross_ai.exec_targets(inv, "standard")
        self.assertEqual([t.cli for t in targets], ["cursor"])

    def test_claude_in_prefer_skipped(self):
        inv = make_inventory(
            host="pi",
            candidates=[exec_cand("m-cursor", "cursor")],
        )
        inv["installed_runtimes"] = ["cursor"]
        targets = cross_ai.exec_targets(inv, "standard", prefer=("claude", "cursor"))
        self.assertEqual([t.cli for t in targets], ["cursor"])

    def test_host_never_a_target(self):
        for host_name in host.HOSTS:
            with self.subTest(host=host_name):
                inv = _all_runners_inv(host_name)
                targets = cross_ai.exec_targets(inv, "standard")
                for target in targets:
                    self.assertNotEqual(target.cli, host_name)

    def test_equal_execution_score_breaks_by_price(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                exec_cand("z-cursor", "cursor", execution=50.0, price=4.0),
                exec_cand("a-cursor", "cursor", execution=50.0, price=1.0),
            ],
        )
        inv["installed_runtimes"] = ["cursor"]
        target = cross_ai.exec_targets(inv, "standard")[0]
        self.assertEqual(target.model, "a-cursor")

    def test_equal_price_breaks_by_model_id(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                exec_cand("b-cursor", "cursor", execution=50.0, price=2.0),
                exec_cand("a-cursor", "cursor", execution=50.0, price=2.0),
            ],
        )
        inv["installed_runtimes"] = ["cursor"]
        target = cross_ai.exec_targets(inv, "standard")[0]
        self.assertEqual(target.model, "a-cursor")

    def test_at_ceiling_beats_above_ceiling_higher_score(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                exec_cand("cheap", "cursor", execution=70.0, price=1.0),
                exec_cand("dear", "cursor", execution=95.0, price=100.0),
            ],
        )
        inv["installed_runtimes"] = ["cursor"]
        target = cross_ai.exec_targets(inv, "mvp")[0]
        self.assertEqual(target.model, "cheap")

    def test_confirmed_router_beats_catalog(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                exec_cand("catalog-high", "cursor", execution=99.0, price=1.0),
                cand(
                    "router-env/run",
                    runtime="cursor",
                    is_host=False,
                    is_router=True,
                    router_confirmed=True,
                    name_declared_purpose="execute",
                    score_axes=0,
                    purpose_scores={},
                ),
            ],
        )
        inv["installed_runtimes"] = ["cursor"]
        target = cross_ai.exec_targets(inv, "standard")[0]
        self.assertEqual(target.model, "router-env/run")
        self.assertTrue(target.router_backed)

    def test_unconfirmed_router_not_used(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                exec_cand("catalog-pick", "cursor", execution=80.0, price=1.0),
                cand(
                    "router-env/run",
                    runtime="cursor",
                    is_host=False,
                    is_router=True,
                    router_confirmed=False,
                    name_declared_purpose="execute",
                    score_axes=0,
                    purpose_scores={},
                ),
            ],
        )
        inv["installed_runtimes"] = ["cursor"]
        target = cross_ai.exec_targets(inv, "standard")[0]
        self.assertEqual(target.model, "catalog-pick")
        self.assertFalse(target.router_backed)

    def _effort_target(self, runtime: str, modes, model: str = "m-reason"):
        inv = make_inventory(
            host="claude", candidates=[exec_cand(model, runtime, reasoning_modes=modes)]
        )
        inv["installed_runtimes"] = [runtime]
        return cross_ai.exec_targets(inv, "standard", prefer=(runtime,))[0]

    def test_catalog_pick_pins_effort_on_pi_and_codex(self):
        """WR-06: the selection's effort target reaches runners that can pin it."""
        for runtime, runner in (("pi", "pi"), ("codex", "codex")):
            with self.subTest(runtime=runtime):
                target = self._effort_target(runtime, ["low", "medium", "high"])
                self.assertEqual(target.effort, "medium")
                art = cross_ai.script_artifact([target], cross_ai.MIN_TIMEOUT_S)
                self.assertEqual(art["config"]["effort"], {runner: "medium"})
        self.assertEqual(self._effort_target("pi", ["high", "xhigh"]).effort, "high")

    def test_no_effort_without_flag_modes_or_with_variant_id(self):
        cases = (
            ("cursor", ["low", "medium"], "m-reason"),  # no effort flag in the runner
            ("pi", [], "m-reason"),  # not a reasoning model: pi clamps to off itself
            ("pi", ["low", "medium"], "m-reason-low"),  # the id already names the effort
        )
        for runtime, modes, model in cases:
            with self.subTest(runtime=runtime, modes=modes, model=model):
                target = self._effort_target(runtime, modes, model)
                self.assertIsNone(target.effort)
                art = cross_ai.script_artifact([target], cross_ai.MIN_TIMEOUT_S)
                self.assertNotIn("effort", art["config"])

    def test_no_candidates_needs_choice(self):
        inv = make_inventory(host="claude", candidates=[])
        inv["installed_runtimes"] = ["cursor"]
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



def review_cand(model: str, runtime: str, review: float = 80.0, **fields):
    scores = {"execution": 1.0, "planning": 1.0, "general": 1.0, "review": review}
    return cand(
        model,
        runtime=runtime,
        is_host=False,
        score_axes=3,
        purpose_scores=scores,
        price=fields.pop("price", 2.0),
        **fields,
    )


def _lane_row(slug: str, binary: str | None, model_key: str, effort_key: str | None = None):
    from ai_kit_spec.detection import runtime_id

    runtime = runtime_id(binary) if isinstance(binary, str) else None
    return {
        "slug": slug,
        "binary": binary,
        "runtime": runtime,
        "transport": "spawn",
        "model_key": model_key,
        "effort_key": effort_key,
        "default_effort": "high" if effort_key else None,
    }


def _review_inv(host_name: str, candidates, installed, lanes, extra_accepted=()):
    from tests.test_curated_config_recommend import _review_lane_accepted_keys

    keys = list(extra_accepted) + _review_lane_accepted_keys()
    inv = make_inventory(
        host=host_name,
        candidates=candidates,
        review_lanes=lanes,
        extra_accepted=keys,
    )
    inv["installed_runtimes"] = list(installed)
    return inv


class TestReviewLanes(unittest.TestCase):
    def test_parse_lane_runtime_from_binary(self):
        rows = gsd_catalog._parse_review_lanes([
            {"slug": "cursor", "binary": "cursor-agent"},
            {"slug": "claude", "binary": "claude"},
            {"slug": "ollama", "binary": None},
        ])
        assert rows is not None
        by_slug = {row["slug"]: row for row in rows}
        self.assertEqual(by_slug["cursor"]["binary"], "cursor-agent")
        self.assertEqual(by_slug["cursor"]["runtime"], "cursor")
        self.assertEqual(by_slug["claude"]["runtime"], "claude")
        self.assertIsNone(by_slug["ollama"]["runtime"])

    def test_cursor_binary_lane_matches_cursor_runtime(self):
        lane = {
            "slug": "cursor",
            "binary": "cursor-agent",
            "runtime": "cursor",
            "transport": "spawn",
            "model_key": "review.models.cursor",
            "effort_key": None,
            "default_effort": None,
        }
        inv = _review_inv(
            "claude",
            [review_cand("composer-2.5", "cursor", vendor="cursor")],
            ["cursor"],
            [lane],
        )
        eligible = cross_ai.eligible_lanes(inv)
        self.assertEqual([row["slug"] for row in eligible], ["cursor"])
        pool = cross_ai.lane_pool(lane, inv)
        self.assertEqual([row["model"] for row in pool], ["composer-2.5"])

    def test_r2_boundary_one_eligible_rigorous(self):
        lanes = [_lane_row("codex", "codex", "review.models.codex", "review.effort.codex")]
        inv = _review_inv(
            "claude",
            [
                cand("claude-opus-5-5", vendor="anthropic", score_axes=3,
                     purpose_scores={"planning": 9.0, "review": 1.0}),
                review_cand("gpt-5.6-sol", "codex", vendor="openai"),
            ],
            ["claude", "codex"],
            lanes,
        )
        picked, notes = cross_ai.select_lanes(inv, "rigorous", "anthropic")
        self.assertEqual(len(picked), 1)
        self.assertTrue(any("only one eligible" in n["text"] for n in notes))

    def test_r2_adjacency_skips_planner_vendor(self):
        lanes = [_lane_row("codex", "codex", "review.models.codex", "review.effort.codex")]
        inv = _review_inv(
            "claude",
            [
                cand("claude-opus-5-5", vendor="anthropic", score_axes=3,
                     purpose_scores={"planning": 9.0}),
                review_cand("openai-high", "codex", review=99.0, vendor="openai"),
                review_cand("anthropic-high", "codex", review=50.0, vendor="anthropic"),
            ],
            ["claude", "codex"],
            lanes,
        )
        lane = cross_ai.select_lanes(inv, "standard", "anthropic")[0][0]
        self.assertEqual(lane.model, "openai-high")

    def test_r2_adjacency_rigorous_second_vendor(self):
        lanes = [
            _lane_row("codex", "codex", "review.models.codex", "review.effort.codex"),
            _lane_row("opencode", "opencode", "review.models.opencode", "review.effort.opencode"),
        ]
        inv = _review_inv(
            "claude",
            [
                cand("claude-opus-5-5", vendor="anthropic", score_axes=3,
                     purpose_scores={"planning": 9.0}),
                review_cand("openai-a", "codex", review=90.0, vendor="openai", price=1.0),
                review_cand("google-codex", "codex", review=88.0, vendor="google", price=1.0),
                review_cand("openai-b", "opencode", review=99.0, vendor="openai", price=1.0),
            ],
            ["claude", "codex", "opencode"],
            lanes,
        )
        picked, _ = cross_ai.select_lanes(inv, "rigorous", "anthropic")
        self.assertEqual(len(picked), 2)
        self.assertNotEqual(picked[0].vendor, picked[1].vendor)

    def test_r2_rigorous_no_vendor_different_second_lane_notes(self):
        # SPEC R2 / PT-17: two eligible lanes, but the second only offers excluded vendors.
        lanes = [
            _lane_row("codex", "codex", "review.models.codex", "review.effort.codex"),
            _lane_row("opencode", "opencode", "review.models.opencode", "review.effort.opencode"),
        ]
        inv = _review_inv(
            "claude",
            [
                cand("claude-opus-5-5", vendor="anthropic", score_axes=3,
                     purpose_scores={"planning": 9.0}),
                review_cand("openai-a", "codex", review=90.0, vendor="openai", price=1.0),
                review_cand("openai-b", "opencode", review=99.0, vendor="openai", price=1.0),
                review_cand("anthropic-c", "opencode", review=80.0, vendor="anthropic", price=1.0),
            ],
            ["claude", "codex", "opencode"],
            lanes,
        )
        picked, notes = cross_ai.select_lanes(inv, "rigorous", "anthropic")
        self.assertEqual([lane.model for lane in picked], ["openai-b"])
        texts = [n["text"] for n in notes if n["kind"] == "review_lane"]
        self.assertEqual(len(texts), 1)
        self.assertIn("vendor", texts[0])
        self.assertIn("rigorous wanted 2", texts[0])

    def test_r2_empty_no_installed_cli(self):
        inv = _review_inv("claude", [], [], _fixture_review_lanes())
        plan = build(inv, rigor="standard", cross_ai_review="y")
        self.assertFalse(entry_map(plan)["workflow.plan_review_convergence"]["value"])
        notes = [n for n in plan["notes"] if n.get("kind") == "review_lane"]
        self.assertTrue(notes)

    def test_r2_encoding_antigravity_and_cursor_effort(self):
        lanes = [
            _lane_row("antigravity", "agy", "review.models.agy", None),
            _lane_row("cursor", "cursor-agent", "review.models.cursor", None),
        ]
        inv = _review_inv(
            "codex",
            [
                cand("gpt-5.6-sol", vendor="openai", score_axes=3,
                     purpose_scores={"planning": 9.0}),
                review_cand("agy-model", "agy", vendor="google"),
                review_cand("composer-2.5", "cursor", vendor="cursor"),
            ],
            ["codex", "agy", "cursor"],
            lanes,
        )
        picked, _ = cross_ai.select_lanes(inv, "standard", "openai")
        keys = {lane.model_key for lane in picked}
        self.assertIn("review.models.agy", keys)
        plan = build(inv, rigor="standard", cross_ai_review="y")
        em = entry_map(plan)
        self.assertNotIn("review.effort.cursor", em)

    def test_r2_ordering_scored_lanes(self):
        lanes = [
            _lane_row("codex", "codex", "review.models.codex", "review.effort.codex"),
            _lane_row("opencode", "opencode", "review.models.opencode", "review.effort.opencode"),
        ]
        inv = _review_inv(
            "claude",
            [
                cand("claude-opus-5-5", vendor="anthropic", score_axes=3,
                     purpose_scores={"planning": 9.0}),
                review_cand("z-model", "codex", review=50.0, vendor="openai", price=3.0),
                review_cand("a-model", "opencode", review=50.0, vendor="google", price=1.0),
            ],
            ["claude", "codex", "opencode"],
            lanes,
        )
        first = cross_ai.select_lanes(inv, "standard", "anthropic")[0][0]
        self.assertEqual(first.slug, "opencode")
        self.assertEqual(first.model, "a-model")

    def test_r2_ordering_equal_price_model_id(self):
        lanes = [
            _lane_row("codex", "codex", "review.models.codex", "review.effort.codex"),
            _lane_row("opencode", "opencode", "review.models.opencode", "review.effort.opencode"),
        ]
        inv = _review_inv(
            "claude",
            [
                cand("claude-opus-5-5", vendor="anthropic", score_axes=3,
                     purpose_scores={"planning": 9.0}),
                review_cand("b-model", "codex", review=50.0, vendor="openai", price=2.0),
                review_cand("a-model", "opencode", review=50.0, vendor="google", price=2.0),
            ],
            ["claude", "codex", "opencode"],
            lanes,
        )
        first = cross_ai.select_lanes(inv, "standard", "anthropic")[0][0]
        self.assertEqual(first.slug, "opencode")

    def test_r2_ordering_router_before_scored(self):
        lanes = [
            _lane_row("opencode", "opencode", "review.models.opencode", "review.effort.opencode"),
            _lane_row("codex", "codex", "review.models.codex", "review.effort.codex"),
        ]
        inv = _review_inv(
            "claude",
            [
                cand("claude-opus-5-5", vendor="anthropic", score_axes=3,
                     purpose_scores={"planning": 9.0}),
                review_cand("openai-best", "codex", review=99.0, vendor="openai"),
                cand(
                    "router-env/review",
                    runtime="opencode",
                    is_host=False,
                    is_router=True,
                    router_confirmed=True,
                    name_declared_purpose="review",
                    score_axes=0,
                    purpose_scores={},
                ),
            ],
            ["claude", "codex", "opencode"],
            lanes,
        )
        picked, _ = cross_ai.select_lanes(inv, "standard", "anthropic")
        self.assertEqual(picked[0].source, "router-declared")
        self.assertEqual(picked[0].slug, "opencode")

    def test_r2_precision_not_tied(self):
        lanes = [_lane_row("codex", "codex", "review.models.codex", "review.effort.codex")]
        inv = _review_inv(
            "claude",
            [
                cand("claude-opus-5-5", vendor="anthropic", score_axes=3,
                     purpose_scores={"planning": 9.0}),
                review_cand("exact-a", "codex", review=0.8, vendor="openai", price=1.0),
                review_cand("exact-b", "codex", review=0.8000001, vendor="google", price=1.0),
            ],
            ["claude", "codex"],
            lanes,
        )
        # Two different vendors but only one lane slug — pick the higher score within lane.
        lane = cross_ai.select_lanes(inv, "standard", "anthropic")[0][0]
        self.assertEqual(lane.model, "exact-b")

    def test_rejected_model_key_not_eligible(self):
        lanes = [_lane_row("codex", "codex", "review.models.codex", "review.effort.codex")]
        inv = _review_inv(
            "claude",
            [review_cand("gpt-5.6-sol", "codex", vendor="openai")],
            ["codex"],
            lanes,
            extra_accepted=(),
        )
        inv["gsd_core"]["valid_keys"]["rejected"] = ["review.models.codex"]
        self.assertEqual(cross_ai.eligible_lanes(inv), [])

    def test_http_lane_binary_none_not_eligible(self):
        lanes = [_lane_row("ollama", None, "review.models.ollama", None)]
        inv = _review_inv("claude", [], ["claude"], lanes)
        self.assertEqual(cross_ai.eligible_lanes(inv), [])

    def test_planner_vendor_unknown_note(self):
        inv = _review_inv(
            "codex",
            [review_cand("m1", "opencode", vendor="openai")],
            ["codex", "opencode"],
            [_lane_row("opencode", "opencode", "review.models.opencode",
                         "review.effort.opencode")],
        )
        plan = build(inv, rigor="standard", cross_ai_review="y")
        self.assertFalse(entry_map(plan)["workflow.plan_review_convergence"]["value"])
        notes = [n for n in plan["notes"] if n.get("kind") == "review_lane"]
        self.assertTrue(any("planner vendor is unknown" in n["text"] for n in notes))

    def test_confirmed_review_router_opencode(self):
        lanes = [_lane_row("opencode", "opencode", "review.models.opencode",
                         "review.effort.opencode")]
        inv = _review_inv(
            "claude",
            [
                cand("claude-opus-5-5", vendor="anthropic", score_axes=3,
                     purpose_scores={"planning": 9.0}),
                review_cand("openai-best", "opencode", review=99.0, vendor="openai"),
                cand(
                    "router-env/plan-review",
                    runtime="opencode",
                    is_host=False,
                    is_router=True,
                    router_confirmed=True,
                    name_declared_purpose="review",
                    score_axes=0,
                    purpose_scores={},
                ),
            ],
            ["claude", "opencode"],
            lanes,
        )
        lane = cross_ai.select_lanes(inv, "standard", "anthropic")[0][0]
        self.assertEqual(lane.source, "router-declared")
        self.assertEqual(lane.model, "router-env/plan-review")

    def test_unconfirmed_review_router_not_used(self):
        lanes = [_lane_row("opencode", "opencode", "review.models.opencode",
                         "review.effort.opencode")]
        inv = _review_inv(
            "claude",
            [
                cand("claude-opus-5-5", vendor="anthropic", score_axes=3,
                     purpose_scores={"planning": 9.0}),
                review_cand("picked", "opencode", review=80.0, vendor="openai"),
                cand(
                    "router-env/plan-review",
                    runtime="opencode",
                    is_host=False,
                    is_router=True,
                    router_confirmed=False,
                    name_declared_purpose="review",
                    score_axes=0,
                    purpose_scores={},
                ),
            ],
            ["claude", "opencode"],
            lanes,
        )
        lane = cross_ai.select_lanes(inv, "standard", "anthropic")[0][0]
        self.assertEqual(lane.source, "catalog-score")
        self.assertEqual(lane.model, "picked")

    def test_effort_xhigh_and_opencode_effect(self):
        lanes = [_lane_row("opencode", "opencode", "review.models.opencode",
                         "review.effort.opencode")]
        modes = ["low", "high", "xhigh"]
        inv = _review_inv(
            "claude",
            [
                cand("claude-opus-5-5", vendor="anthropic", score_axes=3,
                     purpose_scores={"planning": 9.0}),
                review_cand("m1", "opencode", vendor="openai", reasoning_modes=modes),
            ],
            ["claude", "opencode"],
            lanes,
        )
        rigorous = cross_ai.select_lanes(inv, "rigorous", "anthropic")[0][0]
        self.assertEqual(cross_ai.lane_effort(lanes[0], "rigorous", rigorous.candidate), "xhigh")
        standard = cross_ai.select_lanes(inv, "standard", "anthropic")[0][0]
        self.assertEqual(cross_ai.lane_effort(lanes[0], "standard", standard.candidate), "high")
        inv["candidates"][1]["reasoning_modes"] = ["low", "high"]
        plain = cross_ai.select_lanes(inv, "rigorous", "anthropic")[0][0]
        self.assertEqual(cross_ai.lane_effort(lanes[0], "rigorous", plain.candidate), "high")
        plan = build(inv, rigor="rigorous", cross_ai_review="y")
        self.assertEqual(
            entry_map(plan)["review.effort.opencode"].get("effect"),
            cross_ai.OPENCODE_EFFORT_EFFECT,
        )

    def test_claude_lane_alias_on_codex_host(self):
        lanes = [_lane_row("claude", "claude", "review.models.claude", "review.effort.claude")]
        inv = _review_inv(
            "codex",
            [
                cand("gpt-5.6-sol", vendor="openai", score_axes=3,
                     purpose_scores={"planning": 9.0, "review": 1.0}),
                cand(
                    "claude-opus-5-5",
                    runtime="claude",
                    is_host=False,
                    vendor="anthropic",
                    score_axes=3,
                    purpose_scores={"review": 90.0},
                    reasoning_modes=["high", "xhigh"],
                ),
                cand(
                    "claude-sonnet-5-1",
                    runtime="claude",
                    is_host=False,
                    vendor="anthropic",
                    score_axes=3,
                    purpose_scores={"review": 85.0},
                    reasoning_modes=["high"],
                ),
            ],
            ["codex", "claude"],
            lanes,
        )
        plan = build(inv, rigor="rigorous", cross_ai_review="y")
        em = entry_map(plan)
        val = em["review.models.claude"]["value"]
        self.assertIn(val, roles.CLAUDE_ALIASES)
        self.assertEqual(em["review.models.claude"].get("effect"), cross_ai.CLAUDE_ALIAS_EFFECT)
        self.assertEqual(em["review.effort.claude"]["value"], "xhigh")

    def test_mvp_default_review_off(self):
        inv = _review_inv(
            "claude",
            [review_cand("gpt-5.6-sol", "codex", vendor="openai")],
            ["claude", "codex"],
            [_lane_row("codex", "codex", "review.models.codex", "review.effort.codex")],
        )
        plan = build(inv, rigor="mvp")
        self.assertFalse(entry_map(plan)["workflow.plan_review_convergence"]["value"])
        self.assertNotIn("review.default_reviewers", entry_map(plan))

    def test_host_and_pi_never_lanes(self):
        from ai_kit_spec.detection import runtime_id

        base_lanes = []
        for lane in _fixture_review_lanes():
            row = dict(lane)
            binary = row.get("binary")
            row["runtime"] = runtime_id(binary) if isinstance(binary, str) else None
            base_lanes.append(row)
        for host_name in host.HOSTS:
            with self.subTest(host=host_name):
                inv = _review_inv(
                    host_name,
                    [review_cand("lane-model", "codex", vendor="openai")],
                    ["codex", host_name] if host_name != "codex" else ["codex"],
                    base_lanes,
                )
                if host_name == "pi":
                    inv["installed_runtimes"] = ["codex"]
                picked, _ = cross_ai.select_lanes(inv, "rigorous", "anthropic")
                for lane in picked:
                    self.assertNotIn(lane.slug, (host_name, "pi"))


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
