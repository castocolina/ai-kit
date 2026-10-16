"""Tracer + engine tests for the pure recommend engine (plan 17-02): CLI end-to-end,
§5 preset tables per rigor, phase shifts, cross-AI reservations (D-19), unknown-key
drops (D-26/R12), effect labels (D-22), fail-closed inventory loading (D-31) and the
purity guarantee (REC-01). All fixtures live in temp dirs; no real HOME is touched.
"""
import ast
import contextlib
import io
import json
import os
import random
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"),
)

from ai_kit_gsd_curated_config import (
    cli,
    cross_ai,
    gsd_catalog,
    plan_io,
    plan_schema,
    presets,
    recommend,
    roles,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Synthetic gsd-core 1.16 tables (17-02-PLAN <interfaces>; copied from the live dump).
TABLES = {
    "runtime_profile_map": {
        "claude": {
            "opus": {"model": "claude-opus-4-8"},
            "sonnet": {"model": "claude-sonnet-5"},
            "haiku": {"model": "claude-haiku-4-5"},
        },
        "codex": {
            "opus": {"model": "gpt-5.6-sol", "reasoning_effort": "xhigh"},
            "sonnet": {"model": "gpt-5.6-terra", "reasoning_effort": "medium"},
            "haiku": {"model": "gpt-5.6-luna", "reasoning_effort": "medium"},
        },
        "opencode": {
            "opus": {"model": "anthropic/claude-opus-4-8"},
            "sonnet": {"model": "anthropic/claude-sonnet-5"},
            "haiku": {"model": "anthropic/claude-haiku-4-5"},
        },
        "pi": {
            "opus": {"model": "claude-opus-4-8"},
            "sonnet": {"model": "claude-sonnet-5"},
            "haiku": {"model": "claude-haiku-4-5"},
        },
        "cursor": {},
    },
    "model_profiles": {
        "quality": {
            "gsd-planner": "opus",
            "gsd-executor": "opus",
            "gsd-verifier": "sonnet",
            "gsd-plan-checker": "sonnet",
            "gsd-code-reviewer": "opus",
            "gsd-ui-auditor": "sonnet",
            "gsd-dom-verifier": "sonnet",
            "gsd-ui-researcher": "opus",
            "gsd-code-fixer": "opus",
        },
        "balanced": {
            "gsd-planner": "opus",
            "gsd-executor": "sonnet",
            "gsd-verifier": "sonnet",
            "gsd-plan-checker": "sonnet",
            "gsd-code-reviewer": "sonnet",
            "gsd-ui-auditor": "sonnet",
            "gsd-dom-verifier": "sonnet",
            "gsd-ui-researcher": "sonnet",
            "gsd-code-fixer": "sonnet",
        },
        "budget": {
            "gsd-planner": "sonnet",
            "gsd-executor": "sonnet",
            "gsd-verifier": "haiku",
            "gsd-plan-checker": "haiku",
            "gsd-code-reviewer": "sonnet",
            "gsd-ui-auditor": "haiku",
            "gsd-dom-verifier": "haiku",
            "gsd-ui-researcher": "haiku",
            "gsd-code-fixer": "sonnet",
        },
        "adaptive": {
            "gsd-planner": "opus",
            "gsd-executor": "sonnet",
            "gsd-verifier": "sonnet",
            "gsd-plan-checker": "haiku",
            "gsd-code-reviewer": "sonnet",
            "gsd-ui-auditor": "haiku",
            "gsd-dom-verifier": "haiku",
            "gsd-ui-researcher": "sonnet",
            "gsd-code-fixer": "sonnet",
        },
    },
    "agent_to_phase_type": {
        "gsd-planner": "planning",
        "gsd-executor": "execution",
        "gsd-phase-researcher": "research",
        "gsd-verifier": "verification",
        "gsd-plan-checker": "verification",
        "gsd-code-reviewer": "verification",
        "gsd-code-fixer": "execution",
        "gsd-ui-researcher": "research",
        "gsd-ui-auditor": "verification",
        "gsd-dom-verifier": "verification",
        "gsd-codebase-mapper": "research",
    },
}

ENTRY_BASE_KEYS = {"key", "op", "value", "source", "why", "existing"}
ENTRY_OPTIONAL_KEYS = {"status", "candidates", "effect"}

def cand(model, runtime="codex", **fields):
    """A full inventory candidate dict with contract defaults."""
    out = {
        "runtime": runtime,
        "model": model,
        "is_host": True,
        "catalog_key": None,
        "provider": None,
        "vendor": None,
        "family": model,
        "fast_twin_of": None,
        "is_router": False,
        "router_confirmed": False,
        "name_declared_purpose": None,
        "price": None,
        "score_axes": 0,
        "scores": {},
        "image_input": None,
        "image_input_source": None,
        "reasoning_modes": [],
        "purpose_scores": {},
    }
    out.update(fields)
    return out


_SCORES = {"planning": 8.0, "general": 7.0, "mechanical": 6.0}
_CODEX_MODES = ["low", "medium", "high", "xhigh", "max", "ultra"]

CODEX = [
    cand(
        "gpt-6-astra", price=10, score_axes=3, family="gpt-6-astra",
        purpose_scores={**_SCORES, "planning": 6.0},
        reasoning_modes=_CODEX_MODES,
    ),
    cand(
        "gpt-5.6-sol", price=4, score_axes=3, family="gpt-5.6-sol",
        purpose_scores={**_SCORES, "planning": 9.0},
        reasoning_modes=["low", "medium", "high", "xhigh", "max"],
    ),
    cand(
        "gpt-5.6-terra", price=2, score_axes=3, family="gpt-5.6-sol-terra",
        purpose_scores={**_SCORES, "general": 9.0, "planning": 7.0},
        reasoning_modes=["low", "medium", "high", "xhigh"],
    ),
    cand(
        "gpt-6.1-sol", price=2, score_axes=3, family="gpt-6.1-sol",
        purpose_scores={"planning": 8.0, "general": 6.0},
        reasoning_modes=["high", "xhigh"],
    ),
    cand(
        "gpt-5.6-luna", price=0.2, score_axes=3, family="gpt-5.6-luna",
        purpose_scores={**_SCORES, "mechanical": 9.0, "planning": 4.0},
        reasoning_modes=["low", "medium", "high"],
    ),
]

_SCORES5 = {**_SCORES, "execution": 6.0, "review": 6.0}

OPENCODE = [
    cand(
        "openai/gpt-5.6-sol", runtime="opencode", price=4, score_axes=3,
        family="gpt-5.6-sol",
        purpose_scores={**_SCORES5, "planning": 9.0},
    ),
    cand(
        "xai/grok-4.6", runtime="opencode", price=2, score_axes=3, family="grok-4.6",
        purpose_scores={**_SCORES5, "planning": 8.0},
    ),
    cand(
        "zai-coding-plan/glm-5.3", runtime="opencode", price=0, score_axes=3,
        family="glm-5.3",
        purpose_scores={**_SCORES5, "general": 9.0, "mechanical": 8.0},
    ),
]

_ALL90 = {
    "planning": 90.0,
    "general": 90.0,
    "mechanical": 90.0,
    "execution": 90.0,
    "review": 90.0,
}

SPECIALIST_OPENCODE = [
    cand(
        "zai-coding-plan/glm-5.3",
        runtime="opencode",
        vendor="zhipu",
        image_input=False,
        price=0,
        score_axes=3,
        family="glm-5.3",
        purpose_scores=dict(_ALL90),
    ),
    cand(
        "openai/gpt-5.6-sol",
        runtime="opencode",
        vendor="openai",
        image_input=True,
        price=4,
        score_axes=3,
        family="gpt-5.6-sol",
        purpose_scores={**_ALL90, "review": 85.0, "execution": 50.0},
    ),
    cand(
        "xai/grok-4.6",
        runtime="opencode",
        vendor="xai",
        image_input=True,
        price=2,
        score_axes=3,
        family="grok-4.6",
        purpose_scores={**_ALL90, "review": 80.0, "general": 85.0},
    ),
    cand(
        "router-env/my-coding",
        runtime="opencode",
        is_router=True,
        router_confirmed=True,
        name_declared_purpose="execute",
        vendor=None,
        score_axes=0,
        purpose_scores={},
    ),
]


def make_inventory(
    host="codex", candidates=(), project=None, existing=None, conflicts=(), rejected=(),
    global_values=None, global_path=None, extra_accepted=(), review_lanes=(),
):
    """A full current-schema inventory with token paths."""
    from ai_kit_gsd_curated_config import host as host_mod
    if project is None:
        project = {"frontend": False, "intel_index_present": False}
    if existing is None:
        existing = {"exists": False, "values": {}}
    if global_values is None:
        global_values = {}
    accepted = set(presets.closed_key_set(host)) | set(
        presets.flatten_config(existing["values"])
    )
    policy = global_values.get("model_policy")
    if isinstance(policy, dict):
        accepted |= set(presets.flatten_config({"model_policy": policy}))
    agent_skill_keys = [
        f"agent_skills.{agent}" for agent in TABLES["agent_to_phase_type"]
    ]
    accepted = sorted(
        (set(accepted) | set(extra_accepted) | set(agent_skill_keys)) - set(rejected)
    )
    gpath = global_path if global_path is not None else "<global>/.gsd/defaults.json"
    return {
        "schema_version": plan_io.INVENTORY_SCHEMA_VERSION,
        "host": host,
        "gsd_core": {
            "runtime_profile_map": TABLES["runtime_profile_map"],
            "model_profiles": TABLES["model_profiles"],
            # A copy: tests add agents to their own inventory, never to the shared TABLES.
            "agent_to_phase_type": dict(TABLES["agent_to_phase_type"]),
            "valid_keys": {"accepted": accepted, "rejected": list(rejected)},
            "review_lanes": list(review_lanes),
            "skills_roots": {},
            "path": "<project>/.claude/gsd-core",
            "scope": "local",
            "version": "1.16.0",
        },
        "candidates": list(candidates),
        "project": dict(project),
        "existing_config": existing,
        "global_defaults": {"path": gpath, "values": dict(global_values)},
        "conflicts": list(conflicts),
        "installed_runtimes": [],
        "skills": [],
        "ponytail_visibility": {h: [] for h in host_mod.HOSTS},
        "system_one_backend": {"detected": False, "via": [], "note": ""},
    }


def run_recommend(inv, *flags):
    """Writes `inv` (dict or raw JSON text) to a temp dir, runs the CLI recommend
    subcommand, and returns (exit code, parsed plan dict or None, plan bytes, stderr)."""
    with tempfile.TemporaryDirectory() as tmp:
        inv_path = os.path.join(tmp, "inventory.json")
        out_path = os.path.join(tmp, "plan.json")
        with open(inv_path, "w", encoding="utf-8") as handle:
            handle.write(inv if isinstance(inv, str) else json.dumps(inv))
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            code = cli.main(["recommend", "--inventory", inv_path, *flags, "--out", out_path])
        plan_bytes = None
        if os.path.exists(out_path):
            with open(out_path, "rb") as handle:
                plan_bytes = handle.read()
        plan = json.loads(plan_bytes.decode("utf-8")) if plan_bytes is not None else None
        return code, plan, plan_bytes, buf_err.getvalue()


def entry_map(plan):
    return {e["key"]: e for e in plan["entries"]}


def build(inv, rigor="standard", profile="adaptive", **kw):
    return recommend.build_plan(inv, recommend.RecommendOpts(profile, rigor, **kw))


class TestRecommendTracer(unittest.TestCase):
    """Task 1: an inventory file becomes a canonical plan.json through the CLI."""

    def test_cli_recommend_writes_canonical_plan(self):
        inv = make_inventory(host="codex")
        code, plan, _, err = run_recommend(
            inv, "--profile", "adaptive", "--rigor", "standard"
        )
        self.assertEqual((code, err), (0, ""))
        assert plan is not None
        data = json.loads(self._stdout_of(inv))
        for key in ("out", "entries", "needs_choice", "notes"):
            self.assertIn(key, data)
        self.assertEqual(plan["schema_version"], plan_schema.PLAN_SCHEMA_VERSION)
        self.assertTrue(plan["inventory_digest"].startswith("sha256:"))
        self.assertEqual(plan["inventory_digest"], plan_schema.inventory_digest(inv))
        # A-IN-08: the public digest itself ignores candidate order.
        shuffled = make_inventory(host="codex", candidates=CODEX)
        reordered = dict(shuffled, candidates=shuffled["candidates"][::-1])
        self.assertEqual(
            plan_schema.inventory_digest(shuffled), plan_schema.inventory_digest(reordered)
        )
        self.assertEqual(plan["host"], "codex")
        self.assertEqual(plan["profile"], "adaptive")
        self.assertEqual(plan["rigor"], "standard")
        keys = [e["key"] for e in plan["entries"]]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(
            entry_map(plan)["model_profile"],
            {"key": "model_profile", "op": "set", "value": "adaptive", "source": "preset",
             "why": "profile adaptive (adaptive recommended)", "existing": None},
        )
        self.assertEqual(entry_map(plan)["granularity"]["value"], "standard")
        self.assertFalse(any(k.startswith("models.") for k in keys))
        for entry in plan["entries"]:
            self.assertTrue(set(entry) >= ENTRY_BASE_KEYS)
            self.assertTrue(set(entry) <= ENTRY_BASE_KEYS | ENTRY_OPTIONAL_KEYS)

    def _stdout_of(self, inv):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = os.path.join(tmp, "inventory.json")
            out_path = os.path.join(tmp, "plan.json")
            with open(inv_path, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(inv))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = cli.main([
                    "recommend", "--inventory", inv_path,
                    "--profile", "adaptive", "--rigor", "standard", "--out", out_path,
                ])
            self.assertEqual(code, 0)
            return buf.getvalue()

    def test_two_runs_byte_identical_and_trailing_newline(self):
        inv = make_inventory(host="codex")
        _, _, first, _ = run_recommend(inv, "--profile", "adaptive", "--rigor", "standard")
        _, _, second, _ = run_recommend(inv, "--profile", "adaptive", "--rigor", "standard")
        self.assertEqual(first, second)
        assert first is not None
        self.assertTrue(first.endswith(b"\n"))

    def test_existing_value_recorded(self):
        inv = make_inventory(
            host="codex", existing={"exists": True, "values": {"granularity": "coarse"}}
        )
        code, plan, _, _ = run_recommend(inv, "--profile", "adaptive", "--rigor", "standard")
        self.assertEqual(code, 0)
        assert plan is not None
        self.assertEqual(entry_map(plan)["granularity"]["existing"], "coarse")

    def test_get_dotted(self):
        self.assertEqual(presets.get_dotted({"a": {"b": 1}}, "a.b"), 1)
        self.assertIsNone(presets.get_dotted({"a": {"b": 1}}, "a.c"))
        self.assertIsNone(presets.get_dotted({"a": {"b": 1}}, "a.b.c"))
        self.assertIsNone(presets.get_dotted({}, "a.b"))

    def test_flatten_config_stops_at_value_objects(self):
        self.assertEqual(
            presets.flatten_config({
                "model_overrides": {"gsd-planner": "opus"},
                "model_profile_overrides": {
                    "codex": {"opus": {"model": "m", "reasoning_effort": "high"}}
                },
                "x": {},
            }),
            {
                "model_overrides.gsd-planner": "opus",
                "model_profile_overrides.codex.opus": {"model": "m", "reasoning_effort": "high"},
            },
        )
        self.assertEqual(
            presets.flatten_config({
                "model_policy": {
                    "provider": "generic",
                    "runtime_tiers": {
                        "codex": {"opus": {"model": "m", "reasoning_effort": "high"}, "haiku": "h"}
                    },
                }
            }),
            {
                "model_policy.provider": "generic",
                "model_policy.runtime_tiers.codex.opus": {"model": "m", "reasoning_effort": "high"},
                "model_policy.runtime_tiers.codex.haiku": "h",
            },
        )
        self.assertFalse(
            any(k.endswith((".model", ".reasoning_effort")) for k in presets.flatten_config({
                "model_policy": {"runtime_tiers": {"codex": {"opus": {"model": "m"}}}}
            }))
        )


# Literal spec §5 expected tables (per rigor); `frontend`/`intel` substituted in.
_EXPECTED_PRESETS = {
    "mvp": lambda frontend: {
        "granularity": "coarse",
        "workflow.mvp_mode": True,
        "effort.routing_tier_defaults.heavy": "high",
        "effort.routing_tier_defaults.standard": "medium",
        "effort.routing_tier_defaults.light": "minimal",
        "effort.agent_overrides.gsd-executor": "medium",
        "effort.agent_overrides.gsd-code-fixer": "medium",
        "workflow.research": True,
        "workflow.plan_check": True,
        "workflow.verifier": True,
        "workflow.pattern_mapper": True,
        "workflow.nyquist_validation": False,
        "workflow.tdd_mode": False,
        "workflow.code_review_depth": "quick",
        "workflow.security_asvs_level": 1,
        "workflow.security_block_on": "critical",
        "workflow.ui_phase": frontend,
        "workflow.ui_review": False,
        "intel.enabled": False,
    },
    "standard": lambda frontend: {
        "granularity": "standard",
        "effort.routing_tier_defaults.heavy": "xhigh",
        "effort.routing_tier_defaults.standard": "high",
        "effort.routing_tier_defaults.light": "low",
        "effort.agent_overrides.gsd-executor": "medium",
        "effort.agent_overrides.gsd-code-fixer": "medium",
        "workflow.research": True,
        "workflow.plan_check": True,
        "workflow.verifier": True,
        "workflow.pattern_mapper": True,
        "workflow.nyquist_validation": True,
        "workflow.tdd_mode": False,
        "workflow.code_review_depth": "standard",
        "workflow.security_asvs_level": 1,
        "workflow.security_block_on": "high",
        "workflow.ui_phase": frontend,
        "workflow.ui_review": frontend,
        "intel.enabled": True,
    },
    "rigorous": lambda frontend: {
        "granularity": "fine",
        "effort.routing_tier_defaults.heavy": "xhigh",
        "effort.routing_tier_defaults.standard": "high",
        "effort.routing_tier_defaults.light": "low",
        "effort.agent_overrides.gsd-executor": "medium",
        "effort.agent_overrides.gsd-code-fixer": "medium",
        "effort.agent_overrides.gsd-code-reviewer": "xhigh",
        "workflow.research": True,
        "workflow.plan_check": True,
        "workflow.verifier": True,
        "workflow.pattern_mapper": True,
        "workflow.nyquist_validation": True,
        "workflow.tdd_mode": True,
        "workflow.code_review_depth": "deep",
        "workflow.security_asvs_level": 2,
        "workflow.security_block_on": "medium",
        "workflow.ui_phase": frontend,
        "workflow.ui_review": True,
        "intel.enabled": True,
        "code_quality.fallow.enabled": True,
        "code_quality.fallow.profile": "standard",
        "refactor.trigger_enabled": True,
        "dynamic_routing.enabled": True,
        "dynamic_routing.escalate_on_failure": True,
        "dynamic_routing.max_escalations": 1,
    },
}


class TestPresets(unittest.TestCase):
    """Task 2: the §5 preset table, pinned literally per rigor and project facts."""

    def test_table_per_rigor_and_facts(self):
        for rigor in presets.RIGORS:
            for frontend in (False, True):
                for intel in (False, True):
                    project = {"frontend": frontend, "intel_index_present": intel}
                    inv = make_inventory(host="codex", project=project)
                    plan = build(inv, rigor=rigor)
                    got = {
                        e["key"]: e["value"]
                        for e in plan["entries"]
                        if e["source"] == "preset"
                        and e["key"] != "runtime"
                        and not e["key"].startswith(
                            ("models.", "workflow.plan_review_convergence",
                             "workflow.cross_ai", "review.", "model_profile")
                        )
                    }
                    expected = _EXPECTED_PRESETS[rigor](frontend)
                    if rigor == "rigorous" and intel:
                        expected["plan_review.source_grounding_authority"] = "intel"
                    self.assertEqual(got, expected, f"{rigor} frontend={frontend} intel={intel}")


class TestPhaseShifts(unittest.TestCase):
    """`models.<phase>` appears only where the rigor shifts a whole phase (R8)."""

    def test_mvp(self):
        plan = build(make_inventory(), rigor="mvp")
        self.assertEqual(
            {e["key"]: e["value"] for e in plan["entries"] if e["key"].startswith("models.")},
            {"models.research": "haiku", "models.verification": "haiku"},
        )

    def test_standard_sets_no_models_key(self):
        plan = build(make_inventory(), rigor="standard")
        self.assertFalse(any(e["key"].startswith("models.") for e in plan["entries"]))

    def test_rigorous(self):
        plan = build(make_inventory(), rigor="rigorous")
        self.assertEqual(
            {e["key"]: e["value"] for e in plan["entries"] if e["key"].startswith("models.")},
            {"models.planning": "opus", "models.verification": "sonnet"},
        )


class TestRolesHelpers(unittest.TestCase):
    """Unit tests for roles.py pure helpers."""

    def test_price_ceiling(self):
        prices = [0.2, 2, 2, 4, 10]
        self.assertEqual(roles.price_ceiling(prices, 0.75), 4)
        self.assertEqual(roles.price_ceiling(prices, 0.40), 2)
        self.assertIsNone(roles.price_ceiling(prices, None))
        self.assertIsNone(roles.price_ceiling([], 0.4))

    def test_effort_token(self):
        self.assertEqual(roles.effort_token("gpt-5.6-sol-high-fast"), "high")
        self.assertIsNone(roles.effort_token("composer-2.5"))
        self.assertIsNone(roles.effort_token("gpt-5.6-sol-none"))

    def test_clamp_effort(self):
        modes = ["low", "medium", "high", "xhigh", "max"]
        self.assertEqual(roles.clamp_effort("ultra", modes), "max")
        self.assertEqual(roles.clamp_effort("high", modes), "high")

    def test_tie_key_price_zero_and_none(self):
        c0 = {"purpose_scores": {"p": 1.0}, "price": 0, "model": "b"}
        c1 = dict(c0, price=1, model="a")
        self.assertLess(roles.tie_key(c0, "p"), roles.tie_key(c1, "p"))

    def test_pick_variant_rules(self):
        purpose = "general"
        members = [
            cand("claude-opus-5-5-low", family="claude-opus-5-5", purpose_scores={purpose: 1}),
            cand("claude-opus-5-5-high", family="claude-opus-5-5", purpose_scores={purpose: 2}),
            cand("claude-opus-5-5-xhigh", family="claude-opus-5-5", purpose_scores={purpose: 3}),
            cand("claude-opus-5-5-max", family="claude-opus-5-5", purpose_scores={purpose: 4}),
        ]
        chosen, rule = roles.pick_variant(members, purpose, "high")
        self.assertEqual(chosen["model"], "claude-opus-5-5-high")
        self.assertEqual(rule, "exact")
        chosen, rule = roles.pick_variant(members, purpose, "medium")
        self.assertEqual(chosen["model"], "claude-opus-5-5-low")
        self.assertEqual(rule, "nearest lower")
        hi_only = [m for m in members if m["model"].endswith(("-xhigh", "-max"))]
        chosen, rule = roles.pick_variant(hi_only, purpose, "high")
        self.assertEqual(chosen["model"], "claude-opus-5-5-xhigh")
        self.assertEqual(rule, "nearest higher")
        bare = [cand("composer-2.5", family="composer-2.5", purpose_scores={purpose: 1})]
        chosen, rule = roles.pick_variant(bare, purpose, "medium")
        self.assertEqual(chosen["model"], "composer-2.5")
        self.assertEqual(rule, "bare")

    def test_pick_variant_off_ladder_target_is_order_independent(self):
        """A-IN-02: an off-ladder target with no bare id picks the lowest ladder step,
        whatever the member order, and never labels a suffixed id "bare"."""
        purpose = "general"
        members = [
            cand("m-xhigh", family="m", purpose_scores={purpose: 3}),
            cand("m-low", family="m", purpose_scores={purpose: 1}),
        ]
        for order in (members, members[::-1]):
            chosen, rule = roles.pick_variant(order, purpose, "turbo")
            self.assertEqual((chosen["model"], rule), ("m-low", "lowest available"))

    def test_lone_max_suffix_is_a_product_name(self):
        """A-IN-10: gpt-5.1-codex-max next to a bare gpt-5.1-codex is a distinct model,
        so a medium target ranks both by score instead of taking -max as an effort step."""
        purpose = "general"
        members = [
            cand("gpt-5.1-codex", family="gpt-5.1-codex", purpose_scores={purpose: 5}),
            cand("gpt-5.1-codex-max", family="gpt-5.1-codex", purpose_scores={purpose: 4}),
        ]
        chosen, rule = roles.pick_variant(members, purpose, "medium")
        self.assertEqual((chosen["model"], rule), ("gpt-5.1-codex", "bare"))
        with_sibling = [*members, cand("gpt-5.1-codex-low", family="gpt-5.1-codex",
                                       purpose_scores={purpose: 1})]
        chosen, rule = roles.pick_variant(with_sibling, purpose, "max")
        self.assertEqual((chosen["model"], rule), ("gpt-5.1-codex-max", "exact"))


class TestUnknownSpecialist(unittest.TestCase):
    """A-IN-03: a specialist missing from gsd-core's tables gets a note, not silence."""

    def test_each_specialist_path_notes_an_unknown_agent(self):
        for agent in ("gsd-executor", "gsd-plan-checker", "gsd-ui-auditor"):
            inv = make_inventory(host="opencode", candidates=OPENCODE)
            core = inv["gsd_core"]
            core["model_profiles"] = {
                profile: {a: t for a, t in column.items() if a != agent}
                for profile, column in core["model_profiles"].items()
            }
            core["agent_to_phase_type"] = {
                a: p for a, p in core["agent_to_phase_type"].items() if a != agent
            }
            notes = [
                n for n in build(inv)["notes"]
                if n["kind"] == "specialist" and n["key"] == f"model_overrides.{agent}"
            ]
            self.assertTrue(
                any(f"{agent} unknown to gsd-core 1.16.0" in n["text"] for n in notes),
                (agent, notes),
            )


class TestSlotTracer(unittest.TestCase):
    """Task 1: codex keep/override and opencode catalog-score overrides."""

    def test_codex_standard_keeps_native_slots(self):
        inv = make_inventory(host="codex", candidates=CODEX)
        code, plan, _, err = run_recommend(inv, "--profile", "adaptive", "--rigor", "standard")
        self.assertEqual((code, err), (0, ""))
        assert plan is not None
        em = entry_map(plan)
        for tier in ("opus", "sonnet"):
            key = f"model_profile_overrides.codex.{tier}"
            entry = em[key]
            self.assertEqual(entry["op"], "keep")
            self.assertEqual(entry["source"], "native")
            self.assertEqual(entry["effect"], presets.CODEX_EFFECT)
            # A-WR-03: a keep shows the gsd default verbatim, not the rigor's effort target.
            self.assertEqual(entry["value"], TABLES["runtime_profile_map"]["codex"][tier])

    def test_codex_mvp_overrides_opus_above_ceiling(self):
        inv = make_inventory(host="codex", candidates=CODEX)
        plan = build(inv, rigor="mvp")
        em = entry_map(plan)
        opus = em["model_profile_overrides.codex.opus"]
        self.assertEqual(opus["op"], "set")
        self.assertEqual(opus["source"], "catalog-score")
        self.assertIsInstance(opus["value"], dict)
        self.assertLessEqual(
            next(c["price"] for c in CODEX if c["model"] == opus["value"]["model"]), 2
        )
        self.assertEqual(opus["value"]["reasoning_effort"], "high")
        self.assertTrue(opus["why"].startswith("gsd default gpt-5.6-sol above ceiling"))
        self.assertEqual(em["model_profile_overrides.codex.sonnet"]["op"], "keep")

    def test_codex_effort_without_listed_modes_is_marked_unverified(self):
        """A-IN-11: an effort the picked model does not list is flagged in `why`."""
        no_modes = [dict(c, reasoning_modes=[]) for c in CODEX]
        opus = entry_map(build(make_inventory(host="codex", candidates=no_modes), rigor="mvp"))[
            "model_profile_overrides.codex.opus"
        ]
        self.assertEqual(opus["value"]["reasoning_effort"], "high")
        self.assertIn("; effort high unverified (not among the model's reasoning modes)",
                      opus["why"])
        listed = entry_map(build(make_inventory(host="codex", candidates=CODEX), rigor="mvp"))
        self.assertNotIn("unverified", listed["model_profile_overrides.codex.opus"]["why"])

    def test_opencode_standard_overrides_all_used_tiers(self):
        inv = make_inventory(host="opencode", candidates=OPENCODE)
        plan = build(inv, rigor="standard")
        em = entry_map(plan)
        for tier in ("opus", "sonnet", "haiku"):
            key = f"model_profile_overrides.opencode.{tier}"
            entry = em[key]
            self.assertEqual(entry["op"], "set")
            self.assertEqual(entry["source"], "catalog-score")
            val = entry["value"]
            self.assertIsInstance(val, str)
            self.assertFalse(val.startswith("anthropic/"))
            self.assertTrue(entry["why"].startswith("gsd default anthropic/"))

    def test_claude_host_skips_slot_layer(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                cand(
                    "claude-sonnet-5",
                    runtime="claude",
                    purpose_scores=_SCORES,
                    score_axes=3,
                )
            ],
        )
        plan = build(inv, rigor="standard")
        self.assertFalse(
            any(e["key"].startswith("model_profile_overrides.") for e in plan["entries"])
        )


class TestSlotEdges(unittest.TestCase):
    """Task 2: needs_choice, unscored, pi, codex empty, cap fallback, -fast twins."""

    def test_opencode_zero_candidates_needs_choice(self):
        inv = make_inventory(host="opencode", candidates=[])
        code, plan, _, _ = run_recommend(inv, "--profile", "adaptive", "--rigor", "standard")
        self.assertEqual(code, 0)
        assert plan is not None
        for tier in ("opus", "sonnet"):
            entry = entry_map(plan)[f"model_profile_overrides.opencode.{tier}"]
            self.assertEqual(entry["status"], "needs_choice")
            self.assertIsNone(entry["value"])
            self.assertEqual(entry["candidates"], [])
            # A-IN-07: empty enumeration, not missing scores, is the reason.
            self.assertIn("no opencode models enumerated; choose with plan-set", entry["why"])
            self.assertNotIn("no scores", entry["why"])

    def test_opencode_unscored_price_order(self):
        cands = [
            cand("m/a", runtime="opencode", price=3, score_axes=0, purpose_scores={}),
            cand("m/b", runtime="opencode", price=1, score_axes=0, purpose_scores={}),
            cand("m/c", runtime="opencode", price=None, score_axes=0, purpose_scores={}),
            cand("m/d", runtime="opencode", price=0.5, score_axes=0, purpose_scores={}),
            cand("m/e", runtime="opencode", price=2, score_axes=0, purpose_scores={}),
        ]
        inv = make_inventory(host="opencode", candidates=cands)
        plan = build(inv, rigor="standard")
        em = entry_map(plan)
        self.assertFalse(any(e["source"] == "catalog-score" for e in plan["entries"]))
        for tier in ("opus", "sonnet"):
            entry = em[f"model_profile_overrides.opencode.{tier}"]
            models = [c["model"] for c in entry["candidates"]]
            self.assertEqual(models, ["m/d", "m/b", "m/e"])
            for cand_row in entry["candidates"]:
                self.assertIsNone(cand_row["score"])
                self.assertEqual(cand_row["why"], "no scores; ordered by price, not quality")

    def test_codex_unscored_keeps_native(self):
        unscored = [dict(c, score_axes=0, purpose_scores={}) for c in CODEX]
        inv = make_inventory(host="codex", candidates=unscored)
        plan = build(inv, rigor="standard")
        em = entry_map(plan)
        for tier in ("opus", "sonnet"):
            entry = em[f"model_profile_overrides.codex.{tier}"]
            self.assertEqual(entry["op"], "keep")
            self.assertEqual(entry["source"], "native")
        slot_sets = [
            e for e in plan["entries"]
            if e["op"] == "set" and e["key"].startswith("model_profile_overrides.")
        ]
        self.assertFalse(slot_sets)

    def test_cursor_no_catalog_needs_choice(self):
        cands = [
            cand("claude-opus-5-5-high", runtime="cursor", score_axes=0, purpose_scores={}),
            cand("composer-2.5", runtime="cursor", score_axes=0, purpose_scores={}),
            cand("gemini-3.8-flash-low", runtime="cursor", score_axes=0, purpose_scores={}),
            cand("gpt-5.6-luna-low", runtime="cursor", score_axes=0, purpose_scores={}),
            cand("gpt-5.6-sol-medium", runtime="cursor", score_axes=0, purpose_scores={}),
        ]
        inv = make_inventory(host="cursor", candidates=cands)
        plan = build(inv, rigor="standard")
        em = entry_map(plan)
        self.assertFalse(any(e["source"] == "catalog-score" for e in plan["entries"]))
        for tier in ("opus", "sonnet"):
            entry = em[f"model_profile_overrides.cursor.{tier}"]
            self.assertEqual(entry["status"], "needs_choice")
            self.assertIn("no gsd default for cursor", entry["why"])
            self.assertIn("no scores", entry["why"])
            models = [c["model"] for c in entry["candidates"]]
            self.assertEqual(
                models,
                ["claude-opus-5-5-high", "composer-2.5", "gemini-3.8-flash-low"],
            )

    def test_fast_twin_never_chosen(self):
        base = dict(OPENCODE[0])
        fast = dict(
            base,
            model="openai/gpt-5.6-sol-fast",
            fast_twin_of="openai/gpt-5.6-sol",
            purpose_scores={k: v + 5 for k, v in base["purpose_scores"].items()},
        )
        inv = make_inventory(host="opencode", candidates=[*OPENCODE, fast])
        plan = build(inv, rigor="standard")
        for entry in plan["entries"]:
            if entry["key"].startswith("model_profile_overrides.") and entry.get("value"):
                val = entry["value"]
                model = val["model"] if isinstance(val, dict) else val
                self.assertNotEqual(model, "openai/gpt-5.6-sol-fast")

    def test_cap_fallback_haiku(self):
        cands = [
            cand("a", price=1, score_axes=3, purpose_scores={"planning": 9}),
            cand("b", price=1, score_axes=3, purpose_scores={"planning": 8}),
            cand("c", price=10, score_axes=3, purpose_scores={"mechanical": 9}),
        ]
        inv = make_inventory(host="codex", candidates=cands)
        plan = build(inv, profile="budget", rigor="mvp")
        entry = entry_map(plan)["model_profile_overrides.codex.haiku"]
        self.assertEqual(entry["value"]["model"], "c")
        self.assertIn("no family within ceiling", entry["why"])
        self.assertIn("cheapest eligible used", entry["why"])

    def test_mechanical_floor_needs_choice(self):
        cands = [
            cand("a", price=1, score_axes=3, purpose_scores={"planning": 9, "general": 8}),
        ]
        inv = make_inventory(host="codex", candidates=cands)
        plan = build(inv, profile="budget", rigor="standard")
        entry = entry_map(plan)["model_profile_overrides.codex.haiku"]
        self.assertEqual(entry["status"], "needs_choice")
        self.assertIn("no eligible mechanical candidate", entry["why"])

    def test_unpriced_scored_why(self):
        cands = [
            cand(
                "priced",
                runtime="opencode",
                price=5,
                score_axes=3,
                purpose_scores={"planning": 5},
            ),
            cand(
                "free",
                runtime="opencode",
                price=None,
                score_axes=3,
                purpose_scores={"planning": 9},
            ),
        ]
        inv = make_inventory(host="opencode", candidates=cands)
        plan = build(inv, rigor="rigorous")
        entry = entry_map(plan)["model_profile_overrides.opencode.opus"]
        self.assertTrue(entry["why"].endswith("; price unknown"))

    def test_keep_with_existing_override_unset(self):
        inv = make_inventory(
            host="codex",
            candidates=CODEX,
            existing={
                "exists": True,
                "values": {"model_profile_overrides": {"codex": {"sonnet": "x"}}},
            },
        )
        plan = build(inv, rigor="standard")
        entry = entry_map(plan)["model_profile_overrides.codex.sonnet"]
        self.assertEqual(entry["op"], "unset")
        self.assertEqual(entry["source"], "native")
        self.assertEqual(entry["existing"], "x")
        # A-IN-06: every unset carries value null, like the reconcile-layer unsets.
        self.assertIsNone(entry["value"])
        empty = build(dict(inv, candidates=[]), rigor="standard")
        empty_entry = entry_map(empty)["model_profile_overrides.codex.sonnet"]
        self.assertEqual((empty_entry["op"], empty_entry["value"]), ("unset", None))

    def test_pi_sonnet_needs_choice(self):
        inv = make_inventory(
            host="pi",
            candidates=[cand("x/y", runtime="pi", score_axes=3, purpose_scores=_SCORES)],
        )
        plan = build(inv, rigor="standard")
        slot_keys = [
            e["key"] for e in plan["entries"] if e["key"].startswith("model_profile_overrides.")
        ]
        self.assertEqual(slot_keys, ["model_profile_overrides.pi.sonnet"])
        entry = entry_map(plan)["model_profile_overrides.pi.sonnet"]
        self.assertEqual(entry["status"], "needs_choice")
        self.assertEqual(entry["candidates"], [])
        self.assertEqual(entry["effect"], presets.PI_EFFECT)
        self.assertEqual(len([n for n in plan["notes"] if n["kind"] == "pi"]), 1)

    def test_codex_zero_candidates_keeps_native(self):
        inv = make_inventory(host="codex", candidates=[])
        plan = build(inv, rigor="standard")
        for tier in ("opus", "sonnet"):
            entry = entry_map(plan)[f"model_profile_overrides.codex.{tier}"]
            self.assertEqual(entry["op"], "keep")
            self.assertEqual(entry["value"], TABLES["runtime_profile_map"]["codex"][tier])
            self.assertIn("codex enumerated no models", entry["why"])
            self.assertIn("effect unverified: enumeration failed", entry["effect"])
        bad = [
            e for e in plan["entries"]
            if e.get("status") == "needs_choice" and "model_profile_overrides." in e["key"]
        ]
        self.assertFalse(bad)

    def test_needs_choice_candidate_limit(self):
        many = [
            cand(f"m{i}", runtime="opencode", price=i, score_axes=0, purpose_scores={})
            for i in range(5)
        ]
        inv = make_inventory(host="opencode", candidates=many)
        plan = build(inv, rigor="standard")
        entry = entry_map(plan)["model_profile_overrides.opencode.opus"]
        self.assertEqual(len(entry["candidates"]), 3)
        inv2 = make_inventory(host="opencode", candidates=many[:2])
        plan2 = build(inv2, rigor="standard")
        entry2 = entry_map(plan2)["model_profile_overrides.opencode.opus"]
        self.assertEqual(len(entry2["candidates"]), 2)

    def test_cursor_haiku_effort_variant_low(self):
        cands = [
            cand(
                "gpt-5.6-luna-low",
                runtime="cursor",
                family="gpt-5.6-luna",
                price=1,
                score_axes=3,
                purpose_scores={"mechanical": 5},
            ),
            cand(
                "gpt-5.6-luna-high",
                runtime="cursor",
                family="gpt-5.6-luna",
                price=1,
                score_axes=3,
                purpose_scores={"mechanical": 6},
            ),
            cand(
                "gpt-5.6-luna-max",
                runtime="cursor",
                family="gpt-5.6-luna",
                price=1,
                score_axes=3,
                purpose_scores={"mechanical": 7},
            ),
            cand(
                "opus-plan",
                runtime="cursor",
                price=2,
                score_axes=3,
                purpose_scores={"planning": 9, "general": 8, "mechanical": 4},
            ),
        ]
        inv = make_inventory(host="cursor", candidates=cands)
        plan = build(inv, profile="budget", rigor="standard")
        entry = entry_map(plan)["model_profile_overrides.cursor.haiku"]
        self.assertTrue(str(entry["value"]).endswith("-low"))


class TestSpecialistTracer(unittest.TestCase):
    """Task 1: execution, counterpart and vision overrides only where slots fail."""

    def test_specialist_opencode_end_to_end(self):
        inv = make_inventory(
            host="opencode",
            candidates=SPECIALIST_OPENCODE,
            project={"frontend": True, "intel_index_present": False},
        )
        code, plan, _, err = run_recommend(inv, "--profile", "adaptive", "--rigor", "standard")
        self.assertEqual((code, err), (0, ""))
        assert plan is not None
        em = entry_map(plan)
        self.assertEqual(
            em["model_overrides.gsd-executor"]["value"],
            "router-env/my-coding",
        )
        self.assertEqual(em["model_overrides.gsd-executor"]["source"], "router-declared")
        self.assertEqual(
            em["model_overrides.gsd-code-fixer"]["value"],
            "router-env/my-coding",
        )
        pc = em.get("model_overrides.gsd-plan-checker")
        self.assertIsNotNone(pc)
        assert pc is not None
        self.assertEqual(pc["value"], "openai/gpt-5.6-sol")
        self.assertTrue(pc["why"].startswith("counterpart: inferred vendor"))
        self.assertNotIn("model_overrides.gsd-code-reviewer", em)
        reviewer_notes = [
            n for n in plan["notes"]
            if n["kind"] == "specialist" and n["key"] == "model_overrides.gsd-code-reviewer"
        ]
        self.assertEqual(len(reviewer_notes), 1)
        for agent in ("gsd-ui-auditor", "gsd-dom-verifier", "gsd-ui-researcher"):
            entry = em[f"model_overrides.{agent}"]
            self.assertTrue(entry["value"] in ("openai/gpt-5.6-sol", "xai/grok-4.6"))
            self.assertEqual(entry["source"], "catalog-score")
        override_keys = [
            e["key"] for e in plan["entries"]
            if e["key"].startswith("model_overrides.") and e["op"] == "set"
        ]
        self.assertLessEqual(len(override_keys), 7)
        self.assertTrue(all(k.split(".", 1)[1] in presets.SPECIALISTS for k in override_keys))

    def test_claude_alias_for(self):
        self.assertEqual(roles.claude_alias_for("claude-haiku-4-5-20251001"), "haiku")
        self.assertEqual(roles.claude_alias_for("claude-opus-5-5-high"), "opus")
        self.assertIsNone(roles.claude_alias_for("gpt-5.6-sol"))

    def test_claude_aliases_drift_guard(self):
        detection = gsd_catalog.load_ai_kit_spec_module("detection")
        assert detection is not None
        self.assertEqual(set(roles.CLAUDE_ALIASES), set(detection.CLAUDE_MODEL_ALIASES))


class TestSpecialistRules(unittest.TestCase):
    """Task 2: single-provider, vision, frontend, router, claude alias rules."""

    _COUNTERPART_TEXT = (
        "no in-runtime counterpart for gsd-plan-checker and gsd-code-reviewer on "
        "{host} (single provider): use cross-AI review"
    )

    def _counterpart_notes(self, plan):
        return [n for n in plan["notes"] if n["kind"] == "counterpart"]

    def test_codex_single_provider_counterpart_note(self):
        inv = make_inventory(host="codex", candidates=CODEX)
        plan = build(inv, rigor="standard")
        notes = self._counterpart_notes(plan)
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["text"], self._COUNTERPART_TEXT.format(host="codex"))
        em = entry_map(plan)
        self.assertNotIn("model_overrides.gsd-plan-checker", em)
        self.assertNotIn("model_overrides.gsd-code-reviewer", em)

    def test_claude_single_provider_and_alias_values(self):
        cands = [
            cand("claude-opus-5-5", runtime="claude", vendor="anthropic", score_axes=3,
                 purpose_scores=_SCORES5),
            cand("claude-sonnet-5", runtime="claude", vendor="anthropic", score_axes=3,
                 purpose_scores=_SCORES5),
            cand("claude-haiku-4-5", runtime="claude", vendor="anthropic", score_axes=3,
                 purpose_scores=_SCORES5),
        ]
        inv = make_inventory(host="claude", candidates=cands)
        plan = build(inv, profile="adaptive", rigor="standard")
        notes = self._counterpart_notes(plan)
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["text"], self._COUNTERPART_TEXT.format(host="claude"))
        for entry in plan["entries"]:
            if entry["key"].startswith("model_overrides.") and entry["op"] == "set":
                self.assertIn(entry["value"], roles.CLAUDE_ALIASES)

    def test_claude_alias_scored_by_highest_version_id(self):
        """A-WR-04: a stale id's score never justifies the alias Claude Code maps elsewhere."""
        def scored(model, execution):
            return cand(model, runtime="claude", vendor="anthropic", score_axes=3, price=1,
                        purpose_scores={**_SCORES5, "execution": execution})

        cands = [
            scored("claude-opus-4-8", 9.5),
            scored("claude-opus-5-5", 4.0),
            scored("claude-sonnet-5", 6.0),
            scored("claude-haiku-4-5", 3.0),
            scored("claude-haiku-5-5", 8.0),
        ]
        plan = build(make_inventory(host="claude", candidates=cands), rigor="standard")
        executor = entry_map(plan)["model_overrides.gsd-executor"]
        self.assertEqual(executor["value"], "haiku")
        self.assertIn("alias haiku scored as claude-haiku-5-5", executor["why"])
        self.assertNotIn("claude-opus-4-8", executor["why"])
        self.assertIn("alias mapping inferred", executor["effect"])
        rows = roles.claude_alias_rows([*cands, cand("gpt-x", runtime="claude")])
        self.assertEqual(
            [c["model"] for c in rows],
            ["claude-haiku-5-5", "claude-opus-5-5", "claude-sonnet-5"],
        )

    def test_opencode_all_openai_single_provider(self):
        cands = [
            cand("openai/a", runtime="opencode", vendor="openai", score_axes=3,
                 purpose_scores=_SCORES5),
            cand("openai/b", runtime="opencode", vendor="openai", score_axes=3,
                 purpose_scores=_SCORES5),
        ]
        inv = make_inventory(host="opencode", candidates=cands)
        plan = build(inv, rigor="standard")
        self.assertEqual(len(self._counterpart_notes(plan)), 1)

    def test_vision_note_when_image_models_are_unscored(self):
        """A-WR-06: an unscored image_input model is not reported as absent."""
        cands = [
            cand("m/a", runtime="opencode", vendor="openai", image_input=False, score_axes=3,
                 purpose_scores=_SCORES5),
            cand("b/y", runtime="opencode", vendor="xai", image_input=True),
        ]
        plan = build(make_inventory(host="opencode", candidates=cands))
        texts = [n["text"] for n in plan["notes"] if n["kind"] == "vision"]
        self.assertTrue(texts)
        for text in texts:
            self.assertNotIn("no image_input model", text)
            self.assertIn("have no general score", text)

    def test_vision_notes_when_no_image_input(self):
        cands = [
            cand("m/a", runtime="opencode", vendor="openai", image_input=False, score_axes=3,
                 purpose_scores=_SCORES5),
        ]
        inv = make_inventory(
            host="opencode",
            candidates=cands,
            project={"frontend": True, "intel_index_present": False},
        )
        plan = build(inv, rigor="standard")
        em = entry_map(plan)
        vision = [n for n in plan["notes"] if n["kind"] == "vision"]
        agents = {n["key"].split(".", 1)[1] for n in vision}
        self.assertIn("gsd-ui-auditor", agents)
        self.assertIn("gsd-dom-verifier", agents)
        self.assertIn("gsd-ui-researcher", agents)
        self.assertFalse(any(k.startswith("model_overrides.gsd-ui") for k in em))

    def test_frontend_false_skips_ui_researcher(self):
        inv = make_inventory(host="opencode", candidates=OPENCODE, project={"frontend": False})
        plan = build(inv, rigor="standard")
        em = entry_map(plan)
        self.assertNotIn("model_overrides.gsd-ui-researcher", em)
        self.assertFalse(
            any("gsd-ui-researcher" in n.get("text", "") for n in plan["notes"])
        )

    def test_router_unconfirmed_no_router_declared_override(self):
        cands = list(SPECIALIST_OPENCODE)
        cands[-1] = dict(
            cands[-1],
            router_confirmed=False,
        )
        inv = make_inventory(
            host="opencode",
            candidates=cands,
            project={"frontend": True, "intel_index_present": False},
        )
        plan = build(inv, profile="adaptive", rigor="standard")
        em = entry_map(plan)
        self.assertNotIn("model_overrides.gsd-executor", em)
        unconfirmed = [n for n in plan["notes"] if n["kind"] == "router_unconfirmed"]
        self.assertEqual(len(unconfirmed), 1)
        self.assertEqual(unconfirmed[0]["key"], "router-env/my-coding")
        self.assertIn("to let it win its slot", unconfirmed[0]["text"])

    def test_unconfirmed_review_router_promises_no_slot(self):
        """A-WR-05: no Phase 17 path lets a review router win a slot."""
        review = cand("router-env/my-plan-review", runtime="opencode", is_router=True,
                      name_declared_purpose="review")
        inv = make_inventory(host="opencode", candidates=[*SPECIALIST_OPENCODE[:-1], review])
        notes = [n for n in build(inv)["notes"] if n["kind"] == "router_unconfirmed"]
        self.assertEqual(len(notes), 1)
        self.assertNotIn("win its slot", notes[0]["text"])
        self.assertIn("Phase 18 cross-AI review selection", notes[0]["text"])

    def test_claude_executor_same_sonnet_slot_no_override(self):
        cands = [
            cand("claude-sonnet-5", runtime="claude", vendor="anthropic", score_axes=3,
                 purpose_scores={**_SCORES5, "execution": 9.0}),
        ]
        inv = make_inventory(host="claude", candidates=cands)
        plan = build(inv, profile="adaptive", rigor="standard")
        em = entry_map(plan)
        self.assertNotIn("model_overrides.gsd-executor", em)

    def test_pi_no_model_overrides(self):
        inv = make_inventory(
            host="pi",
            candidates=[cand("x/y", runtime="pi", score_axes=3, purpose_scores=_SCORES5)],
        )
        plan = build(inv, rigor="standard")
        self.assertFalse(any(e["key"].startswith("model_overrides.") for e in plan["entries"]))

    def test_purpose_pin_review_vs_general(self):
        cands = [
            cand(
                "zai-coding-plan/glm-5.3",
                runtime="opencode",
                vendor="zhipu",
                image_input=False,
                price=0,
                score_axes=3,
                family="glm-5.3",
                purpose_scores={
                    "planning": 90,
                    "general": 90,
                    "mechanical": 90,
                    "execution": 90,
                    "review": 10,
                },
            ),
            cand(
                "openai/gpt-5.6-sol",
                runtime="opencode",
                vendor="openai",
                image_input=True,
                price=4,
                score_axes=3,
                family="gpt-5.6-sol",
                purpose_scores={
                    "planning": 50,
                    "general": 40,
                    "mechanical": 50,
                    "execution": 50,
                    "review": 90,
                },
            ),
            cand(
                "xai/grok-4.6",
                runtime="opencode",
                vendor="xai",
                image_input=True,
                price=2,
                score_axes=3,
                family="grok-4.6",
                purpose_scores={
                    "planning": 50,
                    "general": 80,
                    "mechanical": 50,
                    "execution": 50,
                    "review": 30,
                },
            ),
        ]
        inv = make_inventory(
            host="opencode",
            candidates=cands,
            project={"frontend": True, "intel_index_present": False},
        )
        plan = build(inv, profile="adaptive", rigor="standard")
        em = entry_map(plan)
        self.assertNotIn("model_overrides.gsd-executor", em)
        self.assertNotIn("model_overrides.gsd-code-fixer", em)
        self.assertEqual(em["model_overrides.gsd-plan-checker"]["value"], "openai/gpt-5.6-sol")
        self.assertEqual(em["model_overrides.gsd-code-reviewer"]["value"], "openai/gpt-5.6-sol")
        for agent in ("gsd-ui-auditor", "gsd-dom-verifier", "gsd-ui-researcher"):
            self.assertEqual(em[f"model_overrides.{agent}"]["value"], "xai/grok-4.6")

    def test_budget_planner_sonnet_counterpart_reference(self):
        cands = [
            cand(
                "openai/gpt-5.6-terra",
                runtime="opencode",
                vendor="openai",
                price=2,
                score_axes=3,
                family="gpt-5.6-terra",
                purpose_scores={
                    "planning": 50,
                    "general": 90,
                    "mechanical": 50,
                    "execution": 50,
                    "review": 40,
                },
            ),
            cand(
                "openai/gpt-5.6-luna",
                runtime="opencode",
                vendor="openai",
                price=0.2,
                score_axes=3,
                family="gpt-5.6-luna",
                purpose_scores={
                    "planning": 50,
                    "general": 50,
                    "mechanical": 90,
                    "execution": 50,
                    "review": 30,
                },
            ),
            cand(
                "xai/grok-4.6",
                runtime="opencode",
                vendor="xai",
                price=2,
                score_axes=3,
                family="grok-4.6",
                purpose_scores={"review": 50},
            ),
        ]
        inv = make_inventory(host="opencode", candidates=cands)
        plan = build(inv, profile="budget", rigor="standard")
        em = entry_map(plan)
        self.assertNotIn("model_profile_overrides.opencode.opus", em)
        self.assertEqual(em["model_overrides.gsd-plan-checker"]["value"], "xai/grok-4.6")
        self.assertIn("openai", em["model_overrides.gsd-plan-checker"]["why"])


class TestSpecialistProperties(unittest.TestCase):
    """Task 3: cap, order independence, strict vendor eligibility."""

    def _rich_mix(self, host="opencode", runtime="opencode"):
        return [
            cand(
                f"{runtime}/glm",
                runtime=runtime,
                vendor="zhipu",
                image_input=False,
                price=0,
                score_axes=3,
                purpose_scores=_ALL90,
            ),
            cand(
                f"{runtime}/sol",
                runtime=runtime,
                vendor="openai",
                image_input=True,
                price=4,
                score_axes=3,
                purpose_scores={**_ALL90, "review": 85},
            ),
            cand(
                f"{runtime}/grok",
                runtime=runtime,
                vendor="xai",
                image_input=True,
                price=2,
                score_axes=3,
                purpose_scores={**_ALL90, "general": 85},
            ),
            cand(
                f"{runtime}/router",
                runtime=runtime,
                is_router=True,
                router_confirmed=False,
                name_declared_purpose="execute",
                vendor=None,
                score_axes=0,
                purpose_scores={},
            ),
            cand(
                f"{runtime}/fast",
                runtime=runtime,
                vendor="openai",
                fast_twin_of=f"{runtime}/sol",
                score_axes=3,
                purpose_scores={**_ALL90, "execution": 99},
            ),
            cand(
                f"{runtime}/null-v",
                runtime=runtime,
                vendor=None,
                score_axes=3,
                purpose_scores={**_ALL90, "review": 99},
            ),
        ]

    def test_at_most_seven_overrides_matrix(self):
        hosts = (
            ("codex", "codex"),
            ("opencode", "opencode"),
            ("cursor", "cursor"),
            ("claude", "claude"),
            ("pi", "pi"),
        )
        for host, runtime in hosts:
            for rigor in presets.RIGORS:
                for profile in ("quality", "balanced", "budget", "adaptive"):
                    inv = make_inventory(
                        host=host,
                        candidates=self._rich_mix(host, runtime),
                        project={"frontend": True, "intel_index_present": False},
                    )
                    plan = build(inv, profile=profile, rigor=rigor)
                    sets = [
                        e for e in plan["entries"]
                        if e["key"].startswith("model_overrides.") and e["op"] == "set"
                    ]
                    self.assertLessEqual(len(sets), 7, f"{host} {rigor} {profile}")
                    for entry in sets:
                        agent = entry["key"].split(".", 1)[1]
                        self.assertIn(agent, presets.SPECIALISTS)

    def test_shuffle_stable_with_specialists(self):
        inv0 = make_inventory(
            host="opencode",
            candidates=list(SPECIALIST_OPENCODE),
            project={"frontend": True, "intel_index_present": False},
        )
        ref = plan_io.canonical_json(
            build(inv0, profile="adaptive", rigor="standard")
        )
        for seed in (7, 8, 9):
            shuffled = list(SPECIALIST_OPENCODE)
            random.Random(seed).shuffle(shuffled)
            inv = make_inventory(
                host="opencode",
                candidates=shuffled,
                project={"frontend": True, "intel_index_present": False},
            )
            self.assertEqual(
                plan_io.canonical_json(build(inv, profile="adaptive", rigor="standard")),
                ref,
            )



    def test_null_vendor_never_counterpart_override(self):
        inv = make_inventory(host="opencode", candidates=self._rich_mix())
        plan = build(inv, profile="adaptive", rigor="standard")
        em = entry_map(plan)
        for key in ("model_overrides.gsd-plan-checker", "model_overrides.gsd-code-reviewer"):
            if key in em:
                self.assertNotEqual(em[key]["value"], "opencode/null-v")

    def test_planner_needs_choice_blocks_plan_checker_override(self):
        cands = [
            cand("m/a", runtime="opencode", score_axes=3, purpose_scores={"general": 9}),
        ]
        inv = make_inventory(host="opencode", candidates=cands)
        plan = build(inv, profile="adaptive", rigor="standard")
        em = entry_map(plan)
        self.assertNotIn("model_overrides.gsd-plan-checker", em)
        notes = [
            n for n in plan["notes"]
            if n["kind"] == "specialist" and n["key"] == "model_overrides.gsd-plan-checker"
        ]
        self.assertEqual(len(notes), 1)

    def test_fast_twin_never_executor(self):
        inv = make_inventory(host="opencode", candidates=self._rich_mix())
        plan = build(inv, profile="adaptive", rigor="standard")
        em = entry_map(plan)
        if "model_overrides.gsd-executor" in em:
            self.assertNotEqual(em["model_overrides.gsd-executor"]["value"], "opencode/fast")


class TestDeterminism(unittest.TestCase):
    """Task 3: tie order, shuffle stability, used tiers, ladder drift."""

    def test_tie_breakers(self):
        purpose = "general"
        eq = [
            cand("b", price=2, score_axes=3, purpose_scores={purpose: 5.0}),
            cand("a", price=2, score_axes=3, purpose_scores={purpose: 5.0}),
        ]
        pick = roles.best_pick(eq, purpose, "medium", None)
        assert pick is not None
        self.assertEqual(pick.candidate["model"], "a")
        price_cases = [
            (
                cand("a", price=2, score_axes=3, purpose_scores={purpose: 5.0}),
                cand("b", price=1, score_axes=3, purpose_scores={purpose: 5.0}),
                "b",
            ),
            (
                cand("a", price=1, score_axes=3, purpose_scores={purpose: 5.0}),
                cand("b", price=0, score_axes=3, purpose_scores={purpose: 5.0}),
                "b",
            ),
            (
                cand("a", price=None, score_axes=3, purpose_scores={purpose: 5.0}),
                cand("b", price=0, score_axes=3, purpose_scores={purpose: 5.0}),
                "b",
            ),
            (
                cand("a", price=None, score_axes=3, purpose_scores={purpose: 5.0}),
                cand("b", price=1, score_axes=3, purpose_scores={purpose: 5.0}),
                "b",
            ),
        ]
        for c0, c1, want in price_cases:
            pick = roles.best_pick([c0, c1], purpose, "medium", None)
            assert pick is not None
            self.assertEqual(pick.candidate["model"], want)
        tiny = [
            cand("a", price=1, score_axes=3, purpose_scores={purpose: 5.0}),
            cand("b", price=1, score_axes=3, purpose_scores={purpose: 5.0 + 1e-9}),
        ]
        pick = roles.best_pick(tiny, purpose, "medium", None)
        assert pick is not None
        self.assertEqual(pick.candidate["model"], "b")

    def test_shuffle_stable_plan(self):
        for rigor in ("mvp", "standard"):
            for host, base in (("opencode", OPENCODE), ("codex", CODEX)):
                inv0 = make_inventory(host=host, candidates=list(base))
                ref = plan_io.canonical_json(build(inv0, rigor=rigor))
                for seed in (7, 8, 9):
                    shuffled = list(base)
                    random.Random(seed).shuffle(shuffled)
                    inv = make_inventory(host=host, candidates=shuffled)
                    self.assertEqual(plan_io.canonical_json(build(inv, rigor=rigor)), ref)

    def test_used_tiers_profile_and_shifts(self):
        gsd = {
            "model_profiles": TABLES["model_profiles"],
            "agent_to_phase_type": TABLES["agent_to_phase_type"],
        }
        self.assertEqual(roles.used_tiers(gsd, "budget", {}), ("sonnet", "haiku"))
        self.assertEqual(roles.used_tiers(gsd, "quality", {}), ("opus", "sonnet"))
        self.assertIn(
            "opus",
            roles.used_tiers(gsd, "budget", presets.PHASE_SHIFTS["rigorous"]),
        )

    @unittest.skipUnless(
        os.path.exists(
            os.path.join(REPO_ROOT, ".claude", "gsd-core", "bin", "lib", "model-catalog.cjs")
        ),
        "gsd-core not installed locally",
    )
    def test_effort_ladder_matches_gsd_core(self):
        path = os.path.join(
            REPO_ROOT, ".claude", "gsd-core", "bin", "lib", "model-catalog.cjs"
        )
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        rendered = ", ".join(f"'{step}'" for step in roles.EFFORT_LADDER)
        needle = f"const EFFORT_LADDER = [{rendered}];"
        self.assertIn(needle, text)




def _fixture_review_lanes():
    from ai_kit_spec.detection import runtime_id

    path = os.path.join(
        REPO_ROOT, "tests", "fixtures", "curated_config_v2", "gsd_tables_1_16.json"
    )
    with open(path, encoding="utf-8") as handle:
        lanes = json.load(handle)["review_lanes"]
    stamped = []
    for lane in lanes:
        row = dict(lane)
        binary = row.get("binary")
        row["runtime"] = runtime_id(binary) if isinstance(binary, str) else None
        stamped.append(row)
    return stamped



def _review_lane_accepted_keys():
    keys = ["review.default_reviewers"]
    for lane in _fixture_review_lanes():
        for field in ("model_key", "effort_key"):
            val = lane.get(field)
            if isinstance(val, str) and val:
                keys.append(val)
    return keys

class TestCrossAi(unittest.TestCase):
    """D-19/XAI-01: review yes wires registry lanes; without lanes convergence stays off."""

    def test_review_yes(self):
        inv = make_inventory(
            host="claude",
            candidates=[
                cand(
                    "claude-opus-5-5",
                    runtime="claude",
                    vendor="anthropic",
                    score_axes=3,
                    purpose_scores={"planning": 90.0, "review": 1.0},
                ),
                cand(
                    "gpt-5.6-sol",
                    runtime="codex",
                    is_host=False,
                    vendor="openai",
                    price=2,
                    score_axes=3,
                    purpose_scores={"review": 90.0, "planning": 1.0},
                ),
            ],
            review_lanes=_fixture_review_lanes(),
            extra_accepted=_review_lane_accepted_keys(),
        )
        inv["installed_runtimes"] = ["claude", "codex"]
        plan = build(inv, rigor="standard", cross_ai_review="y")
        em = entry_map(plan)
        self.assertTrue(em["workflow.plan_review_convergence"]["value"])
        self.assertEqual(em["review.default_reviewers"]["value"], ["codex"])
        self.assertEqual(em["review.models.codex"]["value"], "gpt-5.6-sol")

    def test_review_yes_no_lanes_turns_convergence_off(self):
        plan = build(make_inventory(), rigor="standard", cross_ai_review="y")
        self.assertFalse(entry_map(plan)["workflow.plan_review_convergence"]["value"])
        self.assertNotIn("review.default_reviewers", entry_map(plan))

    def test_explicit_answer_source_user_default_preset(self):
        """A-WR-09: R7 `source: user` marks an explicit answer, `preset` a rigor default."""
        plan = build(make_inventory(), rigor="standard", cross_ai_review="n")
        em = entry_map(plan)
        self.assertEqual(em["workflow.plan_review_convergence"]["source"], "user")
        self.assertEqual(em["workflow.cross_ai_execution"]["source"], "preset")

    def test_review_no(self):
        plan = build(make_inventory(), rigor="standard", cross_ai_review="n")
        self.assertFalse(entry_map(plan)["workflow.plan_review_convergence"]["value"])
        self.assertNotIn("review.default_reviewers", entry_map(plan))

    def test_exec_yes(self):
        plan = build(make_inventory(), rigor="standard", cross_ai_exec="y")
        self.assertTrue(entry_map(plan)["workflow.cross_ai_execution"]["value"])
        reserved = entry_map(plan)["workflow.cross_ai_command"]
        self.assertEqual(reserved["status"], "needs_choice")
        self.assertEqual(reserved["value"], None)
        self.assertEqual(reserved["candidates"], [])
        self.assertEqual(reserved["why"], cross_ai.NO_TARGET_TEXT)

    def test_exec_no(self):
        plan = build(make_inventory(), rigor="standard", cross_ai_exec="n")
        self.assertFalse(entry_map(plan)["workflow.cross_ai_execution"]["value"])
        self.assertNotIn("workflow.cross_ai_command", entry_map(plan))

    def test_defaults(self):
        pi_router = cand(
            "router-env/my-coding",
            runtime="pi",
            is_host=False,
            is_router=True,
            router_confirmed=True,
            name_declared_purpose="execute",
        )
        cursor_cand = cand(
            "composer-2.5",
            runtime="cursor",
            is_host=False,
            price=1,
            score_axes=3,
            purpose_scores={**_SCORES, "execution": 8.0},
        )
        other = [cand("some/other-model", runtime="codex", is_host=False)]
        cases = [
            # (host, candidates, installed, rigor, review, exec)
            ("codex", (), [], "rigorous", "y", "n"),
            ("codex", other, [], "standard", "y", "n"),
            ("opencode", other, ["opencode"], "standard", "n", "n"),
            ("claude", (pi_router,), ["pi"], "mvp", "n", "y"),
            ("claude", (pi_router,), ["pi"], "standard", "y", "y"),
            ("claude", (pi_router,), ["pi"], "rigorous", "y", "y"),
            ("claude", (), [], "mvp", "n", "n"),
            ("codex", (cursor_cand,), ["cursor"], "standard", "y", "y"),
        ]
        for host, candidates, installed, rigor, want_review, want_exec in cases:
            inv = make_inventory(host=host, candidates=candidates)
            inv["installed_runtimes"] = list(installed)
            plan = build(inv, rigor=rigor)
            self.assertEqual(
                plan["cross_ai"]["review"], {"answer": want_review, "defaulted": True}, host
            )
            self.assertEqual(
                plan["cross_ai"]["exec"], {"answer": want_exec, "defaulted": True}, host
            )
            convergence = entry_map(plan)["workflow.plan_review_convergence"]["value"]
            if want_review == "y":
                has_lanes = bool(cross_ai.eligible_lanes(inv)) and host != "pi"
                self.assertEqual(convergence, has_lanes, host)
            else:
                self.assertFalse(convergence, host)
        inv = make_inventory(host="claude", candidates=())
        inv["installed_runtimes"] = []
        plan = build(inv, rigor="standard")
        notes = [n for n in plan["notes"] if n["kind"] == "cross_ai_exec"]
        self.assertEqual(len(notes), 1)
        self.assertIn("pi, cursor, opencode", notes[0]["text"])

    def test_empty_runner_pool_names_the_enumeration_cause(self):
        """C-W12: a failed or empty model listing is not a price-ceiling outcome."""
        for state, tail in (("failed", " (listing failed)"), ("empty", " (listing empty)"),
                            (None, "")):
            inv = make_inventory(host="claude")
            inv["installed_runtimes"] = ["pi"]
            if state is not None:
                inv["runtime_enumeration"] = {"pi": state}
            plan = build(inv, rigor="standard", cross_ai_exec="y")
            why = plan["artifacts"][0]["why"]
            with self.subTest(state=state):
                self.assertIn(f"pi: no pi models enumerated{tail}", why)
                self.assertNotIn("within ceiling", why)

    def test_no_lane_reason_without_a_non_host_lane_binary(self):
        """C-W12: only the host CLI installed is 'no installed non-host lane CLI'."""
        inv = make_inventory(
            host="claude",
            candidates=[cand("claude-opus-5-5", runtime="claude", vendor="anthropic",
                             score_axes=3, purpose_scores={"planning": 90.0})],
            review_lanes=_fixture_review_lanes(),
            extra_accepted=_review_lane_accepted_keys(),
        )
        inv["installed_runtimes"] = ["claude"]
        plan = build(inv, rigor="standard", cross_ai_review="y")
        why = entry_map(plan)["workflow.plan_review_convergence"]["why"]
        self.assertIn("no installed non-host lane CLI", why)

    def test_no_lane_reason_follows_runtime_when_binary_differs(self):
        lane = {
            "slug": "cursor",
            "binary": "cursor-agent",
            "runtime": "cursor",
            "transport": "spawn",
            "model_key": "review.models.cursor",
            "effort_key": None,
            "default_effort": None,
        }
        inv = make_inventory(
            host="claude",
            candidates=[],
            review_lanes=[lane],
            extra_accepted=["review.models.cursor"],
        )
        inv["installed_runtimes"] = ["cursor"]
        why = recommend._no_lane_reason(inv, "anthropic")
        self.assertNotIn("no installed non-host lane CLI", why)
        self.assertIn("no enumerated models on an installed non-host lane", why)

    def test_explicit_flag_not_defaulted(self):
        plan = build(make_inventory(), rigor="mvp", cross_ai_review="y")
        self.assertEqual(plan["cross_ai"]["review"], {"answer": "y", "defaulted": False})


class TestKeyDrop(unittest.TestCase):
    """REC-06/D-26/R12: unknown keys dropped, one note each, idempotent."""

    REJECTED = (
        "dynamic_routing.enabled",
        "dynamic_routing.escalate_on_failure",
        "dynamic_routing.max_escalations",
    )

    def _plan(self):
        return build(make_inventory(host="codex", rejected=self.REJECTED), rigor="rigorous")

    def test_rigorous_drops_dynamic_routing_with_three_notes(self):
        plan = self._plan()
        keys = {e["key"] for e in plan["entries"]}
        for key in self.REJECTED:
            self.assertNotIn(key, keys)
        notes = [n for n in plan["notes"] if n["kind"] == "dropped_key"]
        self.assertEqual(len(notes), 3)
        self.assertEqual({n["key"] for n in notes}, set(self.REJECTED))
        for note in notes:
            self.assertIn(note["key"], note["text"])
            self.assertIn("1.16.0", note["text"])

    def test_rerun_drops_the_same_keys_with_the_same_notes(self):
        first, second = self._plan(), self._plan()
        self.assertEqual(
            [n for n in first["notes"] if n["kind"] == "dropped_key"],
            [n for n in second["notes"] if n["kind"] == "dropped_key"],
        )


class TestPerLayerDrop(unittest.TestCase):
    def test_specialists_see_only_written_slots(self):
        """A-WR-08: a rejected slot is not treated as the executor's effective model."""
        rejected = ("model_profile_overrides.opencode.sonnet",)
        inv = make_inventory(
            host="opencode", candidates=SPECIALIST_OPENCODE[:-1], rejected=rejected
        )
        em = entry_map(build(inv))
        self.assertNotIn(rejected[0], em)
        self.assertEqual(em["model_overrides.gsd-executor"]["value"], "zai-coding-plan/glm-5.3")


class TestUnprobedKeys(unittest.TestCase):
    def test_unprobed_key_fails_closed_not_dropped(self):
        """A-WR-07: a key in neither valid_keys list exits 2 instead of a false drop note."""
        inv = make_inventory(host="codex", candidates=CODEX)
        inv["gsd_core"]["valid_keys"]["accepted"].remove("workflow.ui_phase")
        with self.assertRaisesRegex(ValueError, "not probed.*workflow.ui_phase"):
            build(inv)
        code, plan, _, err = run_recommend(inv, "--profile", "adaptive", "--rigor", "standard")
        self.assertEqual((code, plan), (2, None))
        self.assertIn("rerun inventory", err)


class TestEffectLabels(unittest.TestCase):
    """D-22/D-29 effect labels and the live_dom_uat note."""

    def test_dynamic_routing_effect(self):
        plan = build(make_inventory(host="codex"), rigor="rigorous")
        for entry in plan["entries"]:
            if entry["key"].startswith("dynamic_routing."):
                self.assertEqual(entry["effect"], presets.DYNAMIC_ROUTING_EFFECT)

    def test_pi_effect_on_model_layer(self):
        inv = make_inventory(host="pi")
        plan = build(inv, rigor="rigorous")
        for entry in plan["entries"]:
            if entry["key"] == "model_profile" or entry["key"].startswith("models."):
                self.assertEqual(entry["effect"], presets.PI_EFFECT)

    def test_rigorous_frontend_gets_live_dom_uat_note_only(self):
        inv = make_inventory(host="codex", project={"frontend": True, "intel_index_present": True})
        plan = build(inv, rigor="rigorous")
        notes = [n for n in plan["notes"] if n["kind"] == "live_dom_uat"]
        self.assertEqual(len(notes), 1)
        self.assertEqual(
            notes[0]["text"],
            "enable workflow.live_dom_uat via plan-set if a browser MCP is available",
        )

    def test_live_dom_uat_never_set_in_any_rigor(self):
        for rigor in presets.RIGORS:
            for frontend in (False, True):
                inv = make_inventory(
                    host="codex", project={"frontend": frontend, "intel_index_present": True}
                )
                plan = build(inv, rigor=rigor)
                self.assertNotIn("workflow.live_dom_uat", entry_map(plan))


FORBIDDEN_IMPORT_ROOTS = frozenset((
    "subprocess", "socket", "time", "datetime", "os", "urllib", "http", "shutil",
    "tempfile", "random", "pathlib", "glob", "io", "ai_kit_spec",
))
ALLOWED_RELATIVE_IMPORTS = frozenset(("cross_ai", "presets", "roles", "plan_schema", "skills"))


def forbidden_imports(source):
    """AST guard: every import root in `source` that breaks the recommend purity
    boundary (REC-01). Relative `from . import X` may only name the pure sibling
    modules."""
    flagged = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                    flagged.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                names = [alias.name for alias in node.names]
                if node.module:
                    names.append(node.module)
                for name in names:
                    if name.split(".")[0] not in ALLOWED_RELATIVE_IMPORTS:
                        flagged.append(f".{name}")
            elif node.module is not None and node.module.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                flagged.append(node.module)
    return flagged


class TestPurity(unittest.TestCase):
    """REC-01/R7: build_plan is I/O-free and deterministic."""

    def test_build_plan_pure_and_deterministic(self):
        inv = make_inventory(host="codex", rejected=("dynamic_routing.enabled",))
        inv["skills"] = [{
            "name": "ponytail", "root_kind": "global", "root": "r", "plugin": None,
            "real_dir": "<r>/ponytail", "real_dir_home": None, "escapes_root": False,
            "addressable": True, "description": "d",
        }]
        # C-IN-02: the skills layer runs under the raisers too (loaded before patching open).
        affinity, err = plan_io.load_affinity(plan_io.AFFINITY_PATH)
        self.assertIsNone(err)
        opts = recommend.RecommendOpts("adaptive", "rigorous", "y", "y", affinity)
        raiser = mock.MagicMock(side_effect=AssertionError("purity violation"))
        with mock.patch.object(subprocess, "run", raiser), \
             mock.patch.object(subprocess, "Popen", raiser), \
             mock.patch.object(socket, "socket", raiser), \
             mock.patch.object(time, "time", raiser), \
             mock.patch.object(time, "monotonic", raiser), \
             mock.patch("builtins.open", raiser):
            first = recommend.build_plan(inv, opts)
            second = recommend.build_plan(inv, opts)
        self.assertEqual(plan_io.canonical_json(first), plan_io.canonical_json(second))
        self.assertIn("agent_skills.gsd-planner", {e["key"] for e in first["entries"]})

    def test_recommend_and_presets_import_nothing_forbidden(self):
        for module in ("recommend", "presets", "roles", "plan_schema", "cross_ai", "skills"):
            with open(
                os.path.join(
                    REPO_ROOT, "skills", "ai-kit-gsd-curated-config", "ai_kit_gsd_curated_config",
                    f"{module}.py",
                ),
                encoding="utf-8",
            ) as handle:
                self.assertEqual(forbidden_imports(handle.read()), [], module)

    def test_forbidden_imports_is_not_vacuous(self):
        self.assertIn("subprocess", forbidden_imports("import subprocess\n"))
        self.assertIn("ai_kit_spec", forbidden_imports("from ai_kit_spec import cache\n"))
        self.assertIn(".cli", forbidden_imports("from . import cli\n"))
        self.assertIn(".plan_io", forbidden_imports("from . import plan_io\n"))
        self.assertIn(".inventory", forbidden_imports("from . import inventory\n"))
        self.assertIn("socket", forbidden_imports("import socket\n# cross_ai-like\n"))
        self.assertEqual(forbidden_imports("from . import plan_schema, presets\n"), [])
        self.assertEqual(forbidden_imports("from typing import Any\n"), [])


class TestCliRecommendIo(unittest.TestCase):
    """MUST NOT (R7): recommend reads inventory, shipped skill_affinity.json, and --out only."""

    def test_cli_recommend_touches_only_inventory_and_out(self):
        inv = make_inventory(host="codex", rejected=("dynamic_routing.enabled",))
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = os.path.join(tmp, "inventory.json")
            out_path = os.path.join(tmp, "plan.json")
            with open(inv_path, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(inv))
            opened = []
            active = [True]

            def hook(event, args):
                if active[0] and event == "open" and isinstance(args[0], (str, bytes)):
                    opened.append(os.path.realpath(os.fsdecode(args[0])))

            sys.addaudithook(hook)  # hooks cannot be removed; `active` disarms it
            raiser = mock.MagicMock(side_effect=AssertionError("I/O violation"))
            try:
                with mock.patch.object(subprocess, "run", raiser), \
                     mock.patch.object(subprocess, "Popen", raiser), \
                     mock.patch.object(socket, "socket", raiser), \
                     contextlib.redirect_stdout(io.StringIO()):
                    code = cli.main([
                        "recommend", "--inventory", inv_path, "--profile", "adaptive",
                        "--rigor", "rigorous", "--out", out_path,
                    ])
            finally:
                active[0] = False
            self.assertEqual(code, 0)
            real_tmp = os.path.realpath(tmp)
            affinity_real = os.path.realpath(plan_io.AFFINITY_PATH)
            # The plan write reads its own umask from /proc (IN-11): process state, not data.
            own_status = os.path.realpath("/proc/self/status")
            # Lazy imports may write a writable stdlib's __pycache__ (root in the docker clean
            # room), including its atomic `x.pyc.<id>` temp: bytecode, not recommend's data I/O.
            touched = {
                p for p in opened
                if not p.endswith((".py", ".pyc"))
                and "__pycache__" not in p.split(os.sep)
                and p != own_status
            }
            self.assertIn(os.path.realpath(inv_path), touched)
            self.assertIn(affinity_real, touched)
            for path in touched:
                if path == affinity_real:
                    continue
                self.assertEqual(os.path.dirname(path), real_tmp, path)
            self.assertEqual(sorted(os.listdir(tmp)), ["inventory.json", "plan.json"])


class TestWritePlan(unittest.TestCase):
    """T-17-06: the atomic plan write leaves exactly one file with exact content."""

    def test_write_plan_atomic_and_exact(self):
        plan = {"schema_version": 1, "entries": [], "notes": []}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "plan.json")
            plan_io.write_plan(path, plan)
            plan_io.write_plan(path, plan)
            self.assertEqual(os.listdir(tmp), ["plan.json"])
            with open(path, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), plan_io.canonical_json(plan))


    @unittest.skipIf(os.name == "nt", "POSIX permission bits")
    def test_write_plan_mode_follows_umask(self):
        """B-IN-08: plan.json gets the umask-derived mode, not mkstemp's 0600."""
        plan = {"schema_version": 1, "entries": [], "notes": []}
        for umask, expected in ((0o022, 0o644), (0o077, 0o600)):
            old = os.umask(umask)
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    path = os.path.join(tmp, "plan.json")
                    plan_io.write_plan(path, plan)
                    self.assertEqual(os.stat(path).st_mode & 0o777, expected, oct(umask))
            finally:
                os.umask(old)

    def test_out_into_missing_dir_exits_2(self):
        """B-IN-08: `--out` never creates a missing parent directory."""
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = os.path.join(tmp, "inventory.json")
            with open(inv_path, "w", encoding="utf-8") as handle:
                json.dump(make_inventory(), handle)
            missing = os.path.join(tmp, "missing")
            err = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                code = cli.main([
                    "recommend", "--inventory", inv_path, "--profile", "adaptive",
                    "--rigor", "standard", "--out", os.path.join(missing, "plan.json"),
                ])
            self.assertEqual(code, 2)
            self.assertTrue(err.getvalue().startswith("ai-kit-gsd-curated-config: "))
            self.assertIn("does not exist", err.getvalue())
            self.assertFalse(os.path.exists(missing))


class TestRelativeOut(unittest.TestCase):
    def test_bare_relative_out_is_written(self):
        """B-CR-02: SPEC R7's literal `--out plan.json` works from any cwd."""
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = os.path.join(tmp, "inventory.json")
            with open(inv_path, "w", encoding="utf-8") as handle:
                json.dump(make_inventory(), handle)
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    code = cli.main([
                        "recommend", "--inventory", inv_path, "--profile", "adaptive",
                        "--rigor", "standard", "--out", "plan.json",
                    ])
            finally:
                os.chdir(cwd)
            self.assertEqual(code, 0)
            self.assertTrue(os.path.isfile(os.path.join(tmp, "plan.json")))


class TestOutGuard(unittest.TestCase):
    def test_out_never_overwrites_inputs_or_planning(self):
        """B-WR-09: --out cannot target the inventory, a GSD config or .planning/."""
        with tempfile.TemporaryDirectory() as tmp:
            planning = os.path.join(tmp, "project", ".planning")
            os.makedirs(planning)
            config = os.path.join(planning, "config.json")
            with open(config, "w", encoding="utf-8") as handle:
                handle.write('{"model_profile": "balanced"}')
            inv = make_inventory(
                existing={"exists": True, "path": config, "values": {}},
                global_path=os.path.join(tmp, "defaults.json"),
            )
            inv_path = os.path.join(tmp, "inventory.json")
            with open(inv_path, "w", encoding="utf-8") as handle:
                json.dump(inv, handle)
            for out in (config, os.path.join(planning, "plan.json"), inv_path,
                        os.path.join(tmp, "defaults.json")):
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    code = cli.main([
                        "recommend", "--inventory", inv_path, "--profile", "adaptive",
                        "--rigor", "standard", "--out", out,
                    ])
                self.assertEqual(code, 2, out)
                self.assertIn("--out", err.getvalue())
            with open(config, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), '{"model_profile": "balanced"}')
            self.assertFalse(os.path.exists(os.path.join(planning, "plan.json")))

    def test_workstream_config_still_guards_the_whole_planning_dir(self):
        """SPEC must-not: a workstream config (.planning/workstreams/<ws>/config.json)
        still protects all of .planning/, not only the workstream dir; a sibling of
        .planning/ in the project stays writable."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        project = os.path.join(tmp, "project")
        planning = os.path.join(project, ".planning")
        config = os.path.join(planning, "workstreams", "ws1", "config.json")
        os.makedirs(os.path.dirname(config))
        inv = make_inventory(existing={"exists": True, "path": config, "values": {}})
        self.assertIsNotNone(plan_io.out_path_problem(
            os.path.join(planning, "STATE.md"), os.path.join(tmp, "inv.json"), inv))
        self.assertIsNone(plan_io.out_path_problem(
            os.path.join(project, "plan.json"), os.path.join(tmp, "inv.json"), inv))


class TestInventoryValidation(unittest.TestCase):
    """D-31/R7 boundary: bad inventories exit 2 with `rerun inventory`, write nothing."""

    def _run(self, inv, **kw):
        return run_recommend(inv, "--profile", kw.get("profile", "adaptive"),
                             "--rigor", kw.get("rigor", "standard"))

    def test_bad_schema_versions_fail_closed(self):
        ver = plan_io.INVENTORY_SCHEMA_VERSION
        for bad in (0, ver - 1, ver + 1, str(ver), True, float(ver)):
            inv = make_inventory()
            inv["schema_version"] = bad
            code, plan, plan_bytes, err = self._run(inv)
            self.assertEqual((code, plan, plan_bytes), (2, None, None), repr(bad))
            self.assertIn("rerun inventory", err)

    def test_schema_version_schema_message(self):
        ver = plan_io.INVENTORY_SCHEMA_VERSION
        inv = make_inventory()
        inv["schema_version"] = ver + 1
        _, _, _, err = self._run(inv)
        self.assertIn(f"schema_version {ver + 1} unsupported (expected {ver})", err)
        # B-IN-08: the same prefix as every other CLI error path.
        self.assertTrue(err.startswith("ai-kit-gsd-curated-config: inventory "), err)

    def test_schema_2_inventory_refused(self):
        inv = make_inventory()
        inv["schema_version"] = 2
        code, plan, plan_bytes, err = self._run(inv)
        self.assertEqual((code, plan, plan_bytes), (2, None, None))
        self.assertIn("schema_version 2 unsupported (expected 3)", err)

    def test_lane_missing_runtime_refused(self):
        lane = {
            "slug": "codex",
            "transport": "spawn",
            "binary": "codex",
            "model_key": "review.models.codex",
            "effort_key": None,
            "default_effort": None,
        }
        inv = make_inventory(review_lanes=[lane])
        code, plan, plan_bytes, err = self._run(inv)
        self.assertEqual((code, plan, plan_bytes), (2, None, None))
        self.assertIn("missing runtime", err)

    def test_missing_schema_version_fails_closed(self):
        inv = make_inventory()
        del inv["schema_version"]
        code, plan, plan_bytes, err = self._run(inv)
        self.assertEqual((code, plan, plan_bytes), (2, None, None))
        self.assertIn("rerun inventory", err)

    def test_each_removed_required_key_named(self):
        removed = {
            "host": lambda inv: inv.pop("host"),
            "gsd_core": lambda inv: inv.pop("gsd_core"),
            "gsd_core.valid_keys": lambda inv: inv["gsd_core"].pop("valid_keys"),
            "candidates": lambda inv: inv.pop("candidates"),
            "project": lambda inv: inv.pop("project"),
            "existing_config": lambda inv: inv.pop("existing_config"),
            "global_defaults": lambda inv: inv.pop("global_defaults"),
            "conflicts": lambda inv: inv.pop("conflicts"),
        }
        for name, remove in removed.items():
            inv = make_inventory()
            remove(inv)
            code, plan, plan_bytes, err = self._run(inv)
            self.assertEqual((code, plan, plan_bytes), (2, None, None), name)
            self.assertIn(name, err, name)
            self.assertIn("rerun inventory", err, name)

    def test_skill_row_fields_validated(self):
        """C-W10: every skills[] field recommend and apply consume is checked at load."""
        good = {
            "name": "ok", "root_kind": "plugin", "root": "p@m", "plugin": "p",
            "real_dir": "<home>/p/ok", "real_dir_home": "~/p/ok", "escapes_root": False,
            "addressable": True, "description": "",
        }
        inv = make_inventory()
        inv["skills"] = [dict(good)]
        self.assertEqual(self._run(inv)[0], 0)
        unaddressable = dict(good, name="bad name", plugin="bad.plugin", addressable=False)
        inv["skills"] = [unaddressable]
        self.assertEqual(self._run(inv)[0], 0)
        bad_rows = {
            "name": {"name": "foo\n"},
            "plugin": {"plugin": "bad.plugin"},
            "real_dir_home": {"real_dir_home": "/abs/ok"},
            "real_dir": {"real_dir": None},
            "root": {"root": 3},
            "description": {"description": None},
            "root_kind": {"root_kind": "vendor"},
        }
        for field, change in bad_rows.items():
            inv = make_inventory()
            inv["skills"] = [dict(good, **change)]
            self._assert_fail_closed(inv, f"skills[0].{field}")

    def _assert_fail_closed(self, inv, needle):
        code, plan, plan_bytes, err = self._run(inv)
        self.assertEqual((code, plan, plan_bytes), (2, None, None), needle)
        self.assertIn(needle, err)
        self.assertIn("rerun inventory", err)
        self.assertNotIn("Traceback", err)

    def test_malformed_candidate_fields_fail_closed(self):
        """A-WR-01/B-WR-01: every field recommend reads is validated (exit 2, no traceback)."""
        cases = (
            ("score_axes", lambda c: c.pop("score_axes")),
            ("price", lambda c: c.update(price="4")),
            ("purpose_scores", lambda c: c.update(purpose_scores={"general": "high"})),
            ("is_router", lambda c: c.update(is_router=None)),
            ("score_axes", lambda c: c.update(score_axes=True)),
            ("image_input", lambda c: c.update(image_input="yes")),
        )
        for field, mutate in cases:
            candidate = cand("gpt-5.6-sol", price=1, score_axes=1)
            mutate(candidate)
            self._assert_fail_closed(make_inventory(candidates=[candidate]), field)

    def test_malformed_conflicts_fail_closed(self):
        no_why = {"kind": "resolve_model_ids", "key": "resolve_model_ids", "scope": "project"}
        bad_policy = {
            "kind": "model_policy", "key": "model_policy", "scope": "project",
            "why": "w", "value": "generic",
        }
        for item in (no_why, bad_policy):
            self._assert_fail_closed(make_inventory(conflicts=[item]), "conflicts[0] malformed")

    def test_non_utf8_inventory_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path = os.path.join(tmp, "inventory.json")
            with open(inv_path, "wb") as handle:
                handle.write(b"\xff\xfe{")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = cli.main([
                    "recommend", "--inventory", inv_path, "--profile", "adaptive",
                    "--rigor", "standard", "--out", os.path.join(tmp, "plan.json"),
                ])
        self.assertEqual(code, 2)
        self.assertIn("rerun inventory", err.getvalue())

    def test_engine_error_is_exit_2_backstop(self):
        with mock.patch.object(recommend, "build_plan", side_effect=KeyError("x")):
            self._assert_fail_closed(make_inventory(), "malformed")

    def test_agent_first_model_profiles_fail_closed(self):
        """A pre-normalization (agent-first) table exits 2, never a KeyError traceback."""
        inv = make_inventory()
        inv["gsd_core"]["model_profiles"] = gsd_catalog.profile_first(
            inv["gsd_core"]["model_profiles"]
        )
        code, plan, plan_bytes, err = self._run(inv)
        self.assertEqual((code, plan, plan_bytes), (2, None, None))
        self.assertIn("gsd_core.model_profiles", err)
        self.assertIn("rerun inventory", err)

    def test_missing_profile_column_falls_back_to_balanced(self):
        """gsd-core's computeProfileTier reads balanced when a profile column is absent."""
        inv = make_inventory()
        profiles = dict(inv["gsd_core"]["model_profiles"])
        del profiles["adaptive"]
        inv["gsd_core"]["model_profiles"] = profiles
        code, _plan, _, err = self._run(inv)
        self.assertEqual(code, 0, err)
        self.assertEqual(
            roles.agent_tier("gsd-executor", inv["gsd_core"], "adaptive", {}),
            profiles["balanced"]["gsd-executor"],
        )

    def test_missing_path_and_invalid_json_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_path = os.path.join(tmp, "broken.json")
            with open(bad_path, "w", encoding="utf-8") as handle:
                handle.write("{not json")
            buf_err = io.StringIO()
            with contextlib.redirect_stderr(buf_err):
                code = cli.main([
                    "recommend", "--inventory", bad_path, "--profile", "adaptive",
                    "--rigor", "standard", "--out", os.path.join(tmp, "plan.json"),
                ])
            self.assertEqual(code, 2)
            self.assertIn("rerun inventory", buf_err.getvalue())
            buf_err = io.StringIO()
            with contextlib.redirect_stderr(buf_err):
                code = cli.main([
                    "recommend", "--inventory", os.path.join(tmp, "absent.json"),
                    "--profile", "adaptive", "--rigor", "standard",
                    "--out", os.path.join(tmp, "plan.json"),
                ])
            self.assertEqual(code, 2)
            self.assertIn("rerun inventory", buf_err.getvalue())

    def test_unknown_profile_and_rigor_rejected_before_files(self):
        inv = make_inventory()
        for flag, value in (("--profile", "turbo"), ("--rigor", "extreme")):
            with tempfile.TemporaryDirectory() as tmp:
                inv_path = os.path.join(tmp, "inventory.json")
                with open(inv_path, "w", encoding="utf-8") as handle:
                    handle.write(json.dumps(inv))
                with self.assertRaises(SystemExit) as caught:
                    cli.main([
                        "recommend", "--inventory", inv_path, flag, value,
                        "--out", os.path.join(tmp, "plan.json"),
                    ])
                self.assertEqual(caught.exception.code, 2)
                self.assertFalse(os.path.exists(os.path.join(tmp, "plan.json")))


class TestReconcileTracer(unittest.TestCase):
    """Task 17-08-1: managed leftovers and policy conflicts on a claude host."""

    _LEFTOVER_WHY = "managed by the curated plan (D-08); not set by this plan"

    def _v1_inv(self):
        return make_inventory(
            host="claude",
            existing={
                "exists": True,
                "values": {
                    "model_overrides": {"gsd-planner": "opus"},
                    "model_policy": {"provider": "generic", "high": "x"},
                    "resolve_model_ids": "omit",
                    "workflow": {"live_dom_uat": True, "auto_advance": True},
                    "model_profile_overrides": {
                        "codex": {"opus": {"model": "m", "reasoning_effort": "high"}},
                    },
                    "brave_search": True,
                },
            },
            conflicts=[
                {
                    "kind": "model_policy",
                    "scope": "project",
                    "key": "model_policy",
                    "value": {"provider": "generic", "high": "x"},
                    "why": "legacy v1 model_policy",
                },
                {
                    "kind": "resolve_model_ids",
                    "scope": "project",
                    "key": "resolve_model_ids",
                    "value": "omit",
                    "why": "claude resolve_model_ids conflict",
                },
            ],
        )

    def test_v1_claude_managed_unsets(self):
        code, plan, _, err = run_recommend(
            self._v1_inv(), "--profile", "adaptive", "--rigor", "standard"
        )
        self.assertEqual((code, err), (0, ""))
        assert plan is not None
        em = entry_map(plan)
        mo = em["model_overrides.gsd-planner"]
        self.assertEqual(mo["op"], "unset")
        self.assertEqual(mo["source"], "preset")
        self.assertEqual(mo["existing"], "opus")
        self.assertEqual(mo["why"], self._LEFTOVER_WHY)
        for key in ("model_policy.high", "model_policy.provider"):
            self.assertEqual(em[key]["op"], "unset")
        rid = em["resolve_model_ids"]
        self.assertEqual(rid["op"], "unset")
        self.assertEqual(rid["existing"], "omit")
        for bad in (
            "workflow.live_dom_uat",
            "workflow.auto_advance",
            "model_profile_overrides.codex.opus",
            "brave_search",
        ):
            self.assertNotIn(bad, em)

    def test_is_managed_matrix(self):
        yes = (
            ("model_overrides.gsd-planner", "claude"),
            ("models.planning", "claude"),
            ("effort.routing_tier_defaults.heavy", "claude"),
            ("effort.agent_overrides.gsd-planner", "claude"),
            ("review.default_reviewers", "claude"),
            ("review.models.codex", "claude"),
            ("review.effort.codex", "claude"),
            ("workflow.tdd_mode", "claude"),
            ("model_profile_overrides.claude.opus", "claude"),
        )
        no = (
            ("workflow.live_dom_uat", "claude"),
            ("model_profile_overrides.codex.opus", "claude"),
            ("runtime", "claude"),
            ("model_policy.provider", "claude"),
            ("claude_md_path", "claude"),
            # A-IN-09: user tuning knobs the plan never writes survive.
            ("effort.default", "claude"),
            ("review.max_prompt_tokens", "claude"),
            ("review.parallel_lanes", "claude"),
            ("review.reviewer_instances.x.model", "claude"),
        )
        for key, host in yes:
            self.assertTrue(presets.is_managed(key, host), key)
        for key, host in no:
            self.assertFalse(presets.is_managed(key, host), key)


class TestReconcileConflicts(unittest.TestCase):
    """Task 17-08-2: runtime, latent globals, malformed conflicts."""

    def test_opencode_runtime_set(self):
        inv = make_inventory(host="opencode", candidates=OPENCODE)
        entry = entry_map(build(inv))["runtime"]
        self.assertEqual(entry["op"], "set")
        self.assertEqual(entry["value"], "opencode")
        self.assertEqual(entry["source"], "preset")
        self.assertIsNone(entry["existing"])

    def test_codex_runtime_existing(self):
        inv = make_inventory(
            host="codex",
            candidates=CODEX,
            existing={"exists": True, "values": {"runtime": "codex"}},
        )
        entry = entry_map(build(inv))["runtime"]
        self.assertEqual(entry["value"], "codex")
        self.assertEqual(entry["existing"], "codex")

    def test_claude_runtime_mismatch_project(self):
        inv = make_inventory(
            host="claude",
            existing={"exists": True, "values": {"runtime": "codex"}},
        )
        plan = build(inv)
        self.assertNotIn("runtime", entry_map(plan))
        notes = [n for n in plan["notes"] if n["kind"] == "runtime_mismatch"]
        self.assertEqual(len(notes), 1)
        self.assertIn("the project config", notes[0]["text"])

    def test_cursor_runtime_mismatch_global_path(self):
        inv = make_inventory(
            host="cursor",
            global_values={"runtime": "codex"},
            global_path="gsd-home/.gsd/defaults.json",
        )
        plan = build(inv)
        notes = [n for n in plan["notes"] if n["kind"] == "runtime_mismatch"]
        self.assertEqual(len(notes), 1)
        self.assertIn("gsd-home/.gsd/defaults.json", notes[0]["text"])
        self.assertNotIn("~/.gsd", notes[0]["text"])

    def test_pi_runtime_match_no_note(self):
        inv = make_inventory(
            host="pi",
            existing={"exists": True, "values": {"runtime": "pi"}},
        )
        plan = build(inv)
        self.assertFalse(any(n["kind"] == "runtime_mismatch" for n in plan["notes"]))

    def test_latent_global_resolve_model_ids(self):
        inv = make_inventory(
            host="claude",
            conflicts=[
                {
                    "kind": "resolve_model_ids",
                    "scope": "global",
                    "key": "resolve_model_ids",
                    "value": "omit",
                    "why": "w",
                    "effect": "latent (copied into the project config by config-new-project)",
                },
            ],
        )
        entry = entry_map(build(inv))["resolve_model_ids"]
        self.assertEqual(entry["op"], "unset")
        self.assertIsNone(entry["existing"])
        self.assertEqual(
            entry["effect"], "latent (copied into the project config by config-new-project)"
        )

    def test_same_kind_conflicts_project_wins_no_duplicate_keys(self):
        """A-WR-02: project + global model_policy yield one unset per leaf, order-free."""
        def item(scope, policy):
            return {
                "kind": "model_policy", "scope": scope, "key": "model_policy",
                "value": policy, "why": f"{scope} policy",
            }

        project = item("project", {"provider": "generic", "high": "h"})
        glob = item("global", {"provider": "generic", "budget": "b"})
        plans = []
        for conflicts in ([project, glob], [glob, project]):
            inv = make_inventory(
                host="claude", conflicts=conflicts,
                existing={"exists": True, "values": {"model_policy": project["value"]}},
                global_values={"model_policy": glob["value"]},
            )
            plan = build(inv)
            keys = [e["key"] for e in plan["entries"]]
            self.assertEqual(len(keys), len(set(keys)))
            self.assertIn("project policy", entry_map(plan)["model_policy.provider"]["why"])
            plans.append(plan["entries"])
        self.assertEqual(plans[0], plans[1])

    def test_duplicate_key_within_one_layer_raises(self):
        dup = recommend.make_entry
        inv = make_inventory(host="claude")

        def layer(ctx, _prior):
            return [dup(ctx, "k", 1, "preset", "w"), dup(ctx, "k", 2, "preset", "w")], []

        ctx = recommend.PlanCtx(inv, recommend.RecommendOpts("adaptive", "standard"),
                                "claude", {}, {})
        with mock.patch.object(recommend, "_LAYERS", (layer,)), \
                self.assertRaisesRegex(ValueError, "duplicate plan key k"):
            recommend._merge_layers(ctx)

    def test_latent_global_model_policy_leaves(self):
        policy = {"provider": "generic", "budget": "b"}
        inv = make_inventory(
            host="claude",
            global_values={"model_policy": policy},
            conflicts=[
                {
                    "kind": "model_policy",
                    "scope": "global",
                    "key": "model_policy",
                    "value": policy,
                    "why": "global policy",
                    "effect": "latent (copied into the project config by config-new-project)",
                },
            ],
        )
        em = entry_map(build(inv))
        for key in ("model_policy.budget", "model_policy.provider"):
            self.assertEqual(em[key]["op"], "unset")
            self.assertEqual(
                em[key]["effect"], "latent (copied into the project config by config-new-project)"
            )

    def test_codex_resolve_model_ids_not_managed(self):
        inv = make_inventory(
            host="codex",
            candidates=CODEX,
            existing={"exists": True, "values": {"resolve_model_ids": "omit"}},
        )
        self.assertNotIn("resolve_model_ids", entry_map(build(inv)))

    def test_runtime_tiers_object_leaves(self):
        existing = {
            "model_policy": {
                "provider": "generic",
                "runtime_tiers": {
                    "codex": {"opus": {"model": "m", "reasoning_effort": "high"}},
                },
            },
        }
        inv = make_inventory(
            host="claude",
            existing={"exists": True, "values": existing},
            conflicts=[
                {
                    "kind": "model_policy",
                    "scope": "project",
                    "key": "model_policy",
                    "value": existing["model_policy"],
                    "why": "policy",
                },
            ],
        )
        em = entry_map(build(inv))
        mp_keys = [k for k in em if k.startswith("model_policy.")]
        self.assertEqual(
            sorted(mp_keys),
            ["model_policy.provider", "model_policy.runtime_tiers.codex.opus"],
        )
        tier = em["model_policy.runtime_tiers.codex.opus"]
        self.assertEqual(tier["op"], "unset")
        self.assertEqual(tier["existing"], {"model": "m", "reasoning_effort": "high"})
        self.assertFalse(any(k.endswith(".model") or k.endswith(".reasoning_effort") for k in em))

    def test_r13_empty_no_unsets(self):
        for host in ("claude", "codex", "opencode", "cursor", "pi"):
            cands = CODEX if host == "codex" else (OPENCODE if host == "opencode" else ())
            plan = build(make_inventory(host=host, candidates=cands))
            self.assertFalse(any(e["op"] == "unset" for e in plan["entries"]), host)

    def test_cross_ai_review_y_no_duplicate_unset(self):
        inv = make_inventory(
            existing={
                "exists": True,
                "values": {"review": {"default_reviewers": ["x"]}},
            },
        )
        plan = build(inv, cross_ai_review="y")
        unsets = [
            e for e in plan["entries"]
            if e["key"] == "review.default_reviewers" and e["op"] == "unset"
        ]
        self.assertEqual(len(unsets), 1)
        self.assertFalse(entry_map(plan)["workflow.plan_review_convergence"]["value"])

    def test_cross_ai_review_n_unsets_reviewers(self):
        inv = make_inventory(
            existing={
                "exists": True,
                "values": {"review": {"default_reviewers": ["x"]}},
            },
        )
        entry = entry_map(build(inv, cross_ai_review="n"))["review.default_reviewers"]
        self.assertEqual(entry["op"], "unset")

    def test_malformed_conflicts_exit_2(self):
        cases = (
            '["x"]',
            '[{"kind": "model_policy", "scope": "local", "key": "model_policy"}]',
            '[{"kind": "model_policy", "scope": "project"}]',
        )
        for raw in cases:
            inv = make_inventory()
            inv["conflicts"] = json.loads(raw)
            code, _, _, err = run_recommend(
                json.dumps(inv), "--profile", "adaptive", "--rigor", "standard"
            )
            self.assertEqual(code, 2, raw)
            self.assertIn("conflicts[0]", err)
            self.assertIn("rerun inventory", err)


class TestReconcileComposition(unittest.TestCase):
    """Task 17-08-3: reconcile composes with slot, specialist and cross-AI layers."""

    def test_codex_slot_not_leftover(self):
        inv = make_inventory(
            host="codex",
            candidates=CODEX,
            existing={
                "exists": True,
                "values": {
                    "model_profile_overrides": {
                        "codex": {"opus": {"model": "old", "reasoning_effort": "low"}},
                    },
                },
            },
        )
        entry = entry_map(build(inv))["model_profile_overrides.codex.opus"]
        leftover = "managed by the curated plan (D-08); not set by this plan"
        self.assertNotEqual(entry["why"], leftover)

    def test_rigorous_research_unset_planning_set(self):
        inv = make_inventory(
            existing={
                "exists": True,
                "values": {"models": {"research": "haiku", "planning": "sonnet"}},
            },
        )
        em = entry_map(build(inv, rigor="rigorous"))
        self.assertEqual(em["models.research"]["op"], "unset")
        self.assertEqual(em["models.planning"]["op"], "set")
        self.assertEqual(em["models.planning"]["existing"], "sonnet")

    def test_dynamic_routing_standard_unset_rigorous_set(self):
        base = {"exists": True, "values": {"dynamic_routing": {"enabled": True}}}
        std = entry_map(build(make_inventory(existing=base), rigor="standard"))
        self.assertEqual(std["dynamic_routing.enabled"]["op"], "unset")
        rig = entry_map(build(make_inventory(existing=base), rigor="rigorous"))
        self.assertEqual(rig["dynamic_routing.enabled"]["op"], "set")

    def test_pi_stale_override_and_sonnet_needs_choice(self):
        inv = make_inventory(
            host="pi",
            existing={"exists": True, "values": {"model_overrides": {"gsd-executor": "opus"}}},
        )
        em = entry_map(build(inv))
        self.assertEqual(em["model_overrides.gsd-executor"]["op"], "unset")
        self.assertEqual(em["model_profile_overrides.pi.sonnet"]["status"], "needs_choice")

    def test_agent_skills_leftover(self):
        inv = make_inventory(
            existing={"exists": True, "values": {"agent_skills": {"gsd-executor": True}}},
        )
        self.assertEqual(entry_map(build(inv))["agent_skills.gsd-executor"]["op"], "unset")

    def test_rejected_managed_key_dropped(self):
        key = "dynamic_routing.enabled"
        inv = make_inventory(rejected=(key,), existing={"exists": True, "values": {key: True}})
        plan = build(inv, rigor="rigorous")
        self.assertNotIn(key, entry_map(plan))
        notes = [n for n in plan["notes"] if n["kind"] == "dropped_key"]
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0]["key"], key)

    def test_reordered_existing_byte_identical_plan(self):
        values = {
            "model_overrides": {"gsd-planner": "opus", "gsd-executor": "sonnet"},
            "effort": {"routing_tier_defaults": {"heavy": "max"}},
            "dynamic_routing": {"enabled": True},
        }
        inv_a = make_inventory(host="claude", existing={"exists": True, "values": values})
        nested = json.loads(json.dumps(values))
        inv_b = make_inventory(host="claude", existing={"exists": True, "values": nested})
        _, _, bytes_a, _ = run_recommend(
            inv_a, "--profile", "adaptive", "--rigor", "standard"
        )
        _, _, bytes_b, _ = run_recommend(
            inv_b, "--profile", "adaptive", "--rigor", "standard"
        )
        self.assertEqual(bytes_a, bytes_b)


if __name__ == "__main__":
    unittest.main()

