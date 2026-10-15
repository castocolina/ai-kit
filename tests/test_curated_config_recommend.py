"""Tracer + engine tests for the pure recommend engine (plan 17-02): CLI end-to-end,
§5 preset tables per rigor, phase shifts, cross-AI reservations (D-19), unknown-key
drops (D-26/R12), effect labels (D-22), fail-closed inventory loading (D-31) and the
purity guarantee (REC-01). All fixtures live in temp dirs; no real HOME is touched.
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"),
)

from ai_kit_gsd_curated_config import cli, plan_io, presets, recommend

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
    },
    "model_profiles": {
        "quality": {"gsd-planner": "opus", "gsd-executor": "opus", "gsd-verifier": "sonnet"},
        "balanced": {"gsd-planner": "opus", "gsd-executor": "sonnet", "gsd-verifier": "sonnet"},
        "budget": {"gsd-planner": "sonnet", "gsd-executor": "sonnet", "gsd-verifier": "haiku"},
        "adaptive": {"gsd-planner": "opus", "gsd-executor": "sonnet", "gsd-verifier": "sonnet"},
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


def make_inventory(
    host="codex", candidates=(), project=None, existing=None, conflicts=(), rejected=(),
    global_values=None,
):
    """A full schema-version-1 inventory (17-02-PLAN <interfaces>) with token paths."""
    if project is None:
        project = {"frontend": False, "intel_index_present": False}
    if existing is None:
        existing = {"exists": False, "values": {}}
    if global_values is None:
        global_values = {}
    accepted = sorted(
        (set(presets.closed_key_set(host)) | set(presets.flatten_config(existing["values"])))
        - set(rejected)
    )
    return {
        "schema_version": 1,
        "host": host,
        "gsd_core": {
            "runtime_profile_map": TABLES["runtime_profile_map"],
            "model_profiles": TABLES["model_profiles"],
            "agent_to_phase_type": TABLES["agent_to_phase_type"],
            "valid_keys": {"accepted": accepted, "rejected": list(rejected)},
            "path": "<project>/.claude/gsd-core",
            "scope": "local",
            "version": "1.16.0",
        },
        "candidates": list(candidates),
        "project": dict(project),
        "existing_config": existing,
        "global_defaults": {"values": dict(global_values)},
        "conflicts": list(conflicts),
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
        data = json.loads(self._stdout_of(inv))
        for key in ("out", "entries", "needs_choice", "notes"):
            self.assertIn(key, data)
        self.assertEqual(plan["schema_version"], 1)
        self.assertTrue(plan["inventory_digest"].startswith("sha256:"))
        self.assertEqual(plan["inventory_digest"], plan_io.inventory_digest(inv))
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
        self.assertTrue(first.endswith(b"\n"))

    def test_existing_value_recorded(self):
        inv = make_inventory(
            host="codex", existing={"exists": True, "values": {"granularity": "coarse"}}
        )
        code, plan, _, _ = run_recommend(inv, "--profile", "adaptive", "--rigor", "standard")
        self.assertEqual(code, 0)
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


if __name__ == "__main__":
    unittest.main()
