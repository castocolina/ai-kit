"""plan-set / plan-unset and validate_plan (18-14)."""
from __future__ import annotations

import copy
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-gsd-curated-config"),
)

from ai_kit_gsd_curated_config import cli, gsd_catalog, plan_edit, plan_io, plan_schema

from tests.test_curated_config_golden import build_golden_inventory
from tests.test_curated_config_recommend import run_recommend


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as handle:
        return handle.read()


def _run_plan_set(plan_path, inv_path, key, value, *, force=False):
    flags = ["plan-set", key, value, "--plan", plan_path, "--inventory", inv_path]
    if force:
        flags.append("--force")
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(flags)
    return code, out.getvalue(), err.getvalue()


def _run_plan_unset(plan_path, inv_path, key):
    flags = ["plan-unset", key, "--plan", plan_path, "--inventory", inv_path]
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(flags)
    return code, out.getvalue(), err.getvalue()


def _write_pair(tmp, host="claude", rigor="standard"):
    inv = build_golden_inventory(host)
    inv_path = os.path.join(tmp, "inventory.json")
    plan_path = os.path.join(tmp, "plan.json")
    with open(inv_path, "w", encoding="utf-8") as handle:
        handle.write(plan_io.canonical_json(inv))
    code, plan, raw, err = run_recommend(
        inv, "--profile", "adaptive", "--rigor", rigor
    )
    if code != 0 or plan is None or raw is None:
        raise AssertionError(f"recommend failed: {err}")
    with open(plan_path, "wb") as handle:
        handle.write(raw)
    return inv_path, plan_path, inv, plan


def _strict_encode():
    gsd_tools = gsd_catalog.load_ai_kit_spec_module("gsd_tools")
    assert gsd_tools is not None
    return gsd_tools.encode_value_strict


def _partial_runner_plan(inv, plan):
    """Artifact with pi model set and cursor still in choices."""
    plan = copy.deepcopy(plan)
    art = plan["artifacts"][0]
    config = art["config"]
    pi_model = config["models"].get("pi")
    if not pi_model:
        pi_model = next(iter(config["models"].values()))
    config["prefer"] = ["pi", "cursor"]
    config["models"] = {"pi": pi_model}
    config["router_backed"] = {"pi": config["router_backed"].get("pi", False)}
    art["choices"] = {
        "cursor": {"candidates": plan_edit.runtime_candidates(inv, "cursor")},
    }
    art["status"] = "needs_choice"
    cmd = next(e for e in plan["entries"] if e["key"] == "workflow.cross_ai_command")
    cmd["status"] = "needs_choice"
    cmd["candidates"] = []
    return plan


def _save_plan(plan_path, inv, plan):
    plan = copy.deepcopy(plan)
    plan["inventory_digest"] = plan_schema.inventory_digest(inv)
    with open(plan_path, "w", encoding="utf-8") as handle:
        handle.write(plan_io.canonical_json(plan))


class TestPlanSetTracer(unittest.TestCase):
    def test_plan_set_rewrites_with_source_user(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, _plan = _write_pair(tmp)
            before = _read_bytes(plan_path)
            code, stdout, stderr = _run_plan_set(
                plan_path, inv_path, "workflow.plan_review_convergence", "false"
            )
            self.assertEqual(code, 0, stderr)
            self.assertEqual(stderr, "")
            payload = json.loads(stdout)
            self.assertEqual(payload["op"], "set")
            reloaded, err = plan_io.load_plan(plan_path)
            self.assertIsNone(err)
            assert reloaded is not None
            entry = next(
                e for e in reloaded["entries"] if e["key"] == "workflow.plan_review_convergence"
            )
            self.assertEqual(entry["value"], False)
            self.assertEqual(entry["source"], "user")
            self.assertEqual(entry["why"], "set by the user (plan-set)")
            self.assertNotIn("status", entry)
            keys = [e["key"] for e in reloaded["entries"]]
            self.assertEqual(keys, sorted(keys))
            after = _read_bytes(plan_path)
            self.assertEqual(after, plan_io.canonical_json(reloaded).encode("utf-8"))
            self.assertNotEqual(before, after)

    def test_digest_mismatch_leaves_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, plan = _write_pair(tmp)
            plan["inventory_digest"] = "sha256:dead"
            with open(plan_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(plan))
            raw = _read_bytes(plan_path)
            code, _, err = _run_plan_set(
                plan_path, inv_path, "workflow.plan_review_convergence", "false"
            )
            self.assertEqual(code, 2)
            self.assertIn("digest", err)
            self.assertEqual(_read_bytes(plan_path), raw)

    def test_plan_inside_planning_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, inv, plan = _write_pair(tmp)
            config_path = os.path.join(tmp, "project", ".planning", "config.json")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as handle:
                handle.write("{}")
            inv["existing_config"]["path"] = config_path
            inv["existing_config"]["exists"] = True
            with open(inv_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(inv))
            plan["inventory_digest"] = plan_schema.inventory_digest(inv)
            with open(plan_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(plan))
            inside = os.path.join(tmp, "project", ".planning", "plan.json")
            with open(plan_path, encoding="utf-8") as src:
                body = src.read()
            with open(inside, "w", encoding="utf-8") as handle:
                handle.write(body)
            with open(inside, "rb") as handle:
                raw = handle.read()
            code, _, err = _run_plan_set(
                inside, inv_path, "workflow.plan_review_convergence", "false"
            )
            self.assertEqual(code, 2)
            self.assertIn(".planning", err)
            with open(inside, "rb") as handle:
                self.assertEqual(handle.read(), raw)

    def test_schema_one_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, plan = _write_pair(tmp)
            plan["schema_version"] = 1
            with open(plan_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(plan))
            raw = _read_bytes(plan_path)
            code, _, err = _run_plan_set(
                plan_path, inv_path, "workflow.plan_review_convergence", "false"
            )
            self.assertEqual(code, 2)
            self.assertTrue(err.rstrip().endswith("; rerun recommend"))
            self.assertEqual(_read_bytes(plan_path), raw)

    def test_duplicate_key_refused_at_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, plan = _write_pair(tmp)
            dup = copy.deepcopy(plan["entries"][0])
            plan["entries"].append(dup)
            with open(plan_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(plan))
            raw = _read_bytes(plan_path)
            code, _, err = _run_plan_set(
                plan_path, inv_path, "workflow.plan_review_convergence", "false"
            )
            self.assertEqual(code, 2)
            self.assertIn("duplicate", err)
            self.assertEqual(_read_bytes(plan_path), raw)


class TestPlanSetRefusals(unittest.TestCase):
    def _assert_refusal(self, tmp, argv_extra, needle):
        inv_path, plan_path, _inv, _plan = _write_pair(tmp)
        raw = _read_bytes(plan_path)
        code, _, err = _run_plan_set(plan_path, inv_path, *argv_extra)
        self.assertEqual(code, 2, err)
        self.assertIn(needle, err)
        self.assertEqual(_read_bytes(plan_path), raw)

    def test_rejected_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, inv, plan = _write_pair(tmp)
            inv["gsd_core"]["valid_keys"]["rejected"].append("workflow.plan_review_convergence")
            inv["gsd_core"]["valid_keys"]["accepted"] = [
                k
                for k in inv["gsd_core"]["valid_keys"]["accepted"]
                if k != "workflow.plan_review_convergence"
            ]
            with open(inv_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(inv))
            plan["inventory_digest"] = plan_schema.inventory_digest(inv)
            with open(plan_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(plan))
            with open(plan_path, "rb") as handle:
                raw = handle.read()
            for force in (False, True):
                code, _, err = _run_plan_set(
                    plan_path,
                    inv_path,
                    "workflow.plan_review_convergence",
                    "false",
                    force=force,
                )
                self.assertEqual(code, 2)
                self.assertIn("rejected", err)
            self.assertEqual(_read_bytes(plan_path), raw)

    def test_bare_value_for_json_keys_is_a_refusal(self):
        """B WR-02 / C-W7: a bare word for a JSON-typed key is exit 2, never a traceback."""
        for key in (
            "review.default_reviewers",
            "agent_skills.gsd-planner",
            "agent_skills_security.trusted_global_roots",
            "script:cross-ai.prefer",
        ):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tmp:
                self._assert_refusal(tmp, (key, "codex"), "expected a JSON list of strings")
        self.assertRaisesRegex(
            plan_edit.PlanEditError,
            "expected a JSON object",
            plan_edit.parse_value,
            "models",
            "{oops",
            {"a": 1},
        )

    def test_timeout_floor(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._assert_refusal(tmp, ("workflow.cross_ai_timeout", "1799"), "1800")
            self._assert_refusal(tmp, ("workflow.cross_ai_timeout", "1799",), "1800")
            inv_path, plan_path, _inv, _plan = _write_pair(tmp)
            raw = _read_bytes(plan_path)
            code, _, err = _run_plan_set(
                plan_path, inv_path, "workflow.cross_ai_timeout", "1799", force=True
            )
            self.assertEqual(code, 2)
            self.assertIn("1800", err)
            self.assertEqual(_read_bytes(plan_path), raw)
            code, _, err = _run_plan_set(
                plan_path, inv_path, "workflow.cross_ai_timeout", "abc", force=True
            )
            self.assertEqual(code, 2)
            self.assertEqual(_read_bytes(plan_path), raw)

    def test_cross_ai_command_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._assert_refusal(
                tmp,
                ("workflow.cross_ai_command", "node other.mjs"),
                "full permissions",
            )
            inv_path, plan_path, _inv, _plan = _write_pair(tmp)
            code, _stdout, err = _run_plan_set(
                plan_path,
                inv_path,
                "workflow.cross_ai_command",
                "node other.mjs",
                force=True,
            )
            self.assertEqual(code, 0, err)
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            entry = next(e for e in plan["entries"] if e["key"] == "workflow.cross_ai_command")
            self.assertTrue(entry.get("forced"))
            self.assertIn("full permissions", err)

    def test_skill_not_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._assert_refusal(
                tmp,
                ("agent_skills.gsd-executor", '["not-installed"]'),
                "not installed",
            )
            inv_path, plan_path, _inv, _plan = _write_pair(tmp)
            code, _, err = _run_plan_set(
                plan_path,
                inv_path,
                "agent_skills.gsd-executor",
                '["not-installed"]',
                force=True,
            )
            self.assertEqual(code, 2)
            self.assertIn("not installed", err)

    def test_reviewers_outside_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._assert_refusal(
                tmp,
                ("review.default_reviewers", '["nolane"]'),
                "not a candidate",
            )
            inv_path, plan_path, _inv, _plan = _write_pair(tmp)
            code, _, err = _run_plan_set(
                plan_path,
                inv_path,
                "review.default_reviewers",
                '["nolane"]',
                force=True,
            )
            self.assertEqual(code, 0, err)

    def test_trusted_root_absolute_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._assert_refusal(
                tmp,
                (
                    "agent_skills_security.trusted_global_roots",
                    '["/abs/path"]',
                ),
                "~/-relative",
            )

    def test_forged_existing_trusted_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, inv, plan = _write_pair(tmp)
            good_plan = copy.deepcopy(plan)
            vault = os.path.join(tmp, "vault")
            for entry in plan["entries"]:
                if entry["key"] == "agent_skills_security.trusted_global_roots":
                    entry["existing"] = [vault]
            with open(plan_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(plan))
            raw = _read_bytes(plan_path)
            payload = json.dumps([vault])
            for force in (False, True):
                code, _, err = _run_plan_set(
                    plan_path,
                    inv_path,
                    "agent_skills_security.trusted_global_roots",
                    payload,
                    force=force,
                )
                self.assertEqual(code, 2)
                self.assertIn("trusted_global_roots", err)
            with open(plan_path, "rb") as handle:
                self.assertEqual(handle.read(), raw)
            self.assertIsNone(plan_io.check_plan_inventory(good_plan, inv))


class TestPlanSetWarnings(unittest.TestCase):
    def test_unprobed_key_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, _plan = _write_pair(tmp)
            code, _, err = _run_plan_set(
                plan_path, inv_path, "workflow.live_dom_uat", "true"
            )
            self.assertEqual(code, 0, err)
            self.assertIn("not probed", err)

    def test_timeout_syncs_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, _plan = _write_pair(tmp)
            code, _, err = _run_plan_set(
                plan_path, inv_path, "workflow.cross_ai_timeout", "3600"
            )
            self.assertEqual(code, 0, err)
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            entry = next(e for e in plan["entries"] if e["key"] == "workflow.cross_ai_timeout")
            self.assertEqual(entry["value"], 3600)
            self.assertEqual(plan["artifacts"][0]["config"]["outer_timeout_s"], 3600)

    def test_timeout_1800_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, _plan = _write_pair(tmp)
            code, _, err = _run_plan_set(
                plan_path, inv_path, "workflow.cross_ai_timeout", "1800"
            )
            self.assertEqual(code, 0, err)


class TestPlanValidator(unittest.TestCase):
    def _golden_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            _inv_path, _plan_path, _inv, plan = _write_pair(tmp)
            return copy.deepcopy(plan)

    def test_valid_plan_ok(self):
        plan = self._golden_plan()
        self.assertIsNone(plan_io.validate_plan(plan))

    def test_duplicate_key(self):
        plan = self._golden_plan()
        plan["entries"].append(copy.deepcopy(plan["entries"][0]))
        problem = plan_io.validate_plan(plan)
        self.assertIsNotNone(problem)
        assert problem is not None
        self.assertIn("duplicate", problem)

    def test_set_missing_value(self):
        plan = self._golden_plan()
        plan["entries"][0]["value"] = None
        plan["entries"][0].pop("status", None)
        problem = plan_io.validate_plan(plan)
        self.assertIsNotNone(problem)
        assert problem is not None
        self.assertIn(plan["entries"][0]["key"], problem)

    def test_bad_host(self):
        plan = self._golden_plan()
        plan["host"] = "windows"
        problem = plan_io.validate_plan(plan)
        self.assertIsNotNone(problem)
        assert problem is not None
        self.assertIn("host", problem)

    def test_timeout_1799(self):
        plan = self._golden_plan()
        for entry in plan["entries"]:
            if entry["key"] == "workflow.cross_ai_timeout":
                entry["value"] = 1799
        problem = plan_io.validate_plan(plan)
        self.assertIsNotNone(problem)
        assert problem is not None
        self.assertIn("1800", problem)

    def test_forced_command_ok(self):
        plan = self._golden_plan()
        for entry in plan["entries"]:
            if entry["key"] == "workflow.cross_ai_command":
                entry["value"] = "node other.mjs"
                entry["forced"] = True
        self.assertIsNone(plan_io.validate_plan(plan))

    def test_needs_choice_none_ok(self):
        plan = self._golden_plan()
        for entry in plan["entries"]:
            if entry["key"] == "agent_skills_security.trusted_global_roots":
                entry["value"] = None
                entry["status"] = "needs_choice"
        self.assertIsNone(plan_io.validate_plan(plan))

    def test_artifact_bad_path(self):
        plan = self._golden_plan()
        plan["artifacts"][0]["path"] = "../x.mjs"
        problem = plan_io.validate_plan(plan)
        self.assertIsNotNone(problem)
        assert problem is not None
        self.assertIn("path", problem)

    def test_prefer_host_id(self):
        plan = self._golden_plan()
        plan["artifacts"][0]["config"]["prefer"] = ["claude"]
        problem = plan_io.validate_plan(plan)
        self.assertIsNotNone(problem)
        assert problem is not None
        self.assertIn("prefer", problem)

    def test_trusted_root_abs_without_existing(self):
        plan = self._golden_plan()
        for entry in plan["entries"]:
            if entry["key"] == "agent_skills_security.trusted_global_roots":
                entry["value"] = ["/abs/path"]
                entry.pop("status", None)
        problem = plan_io.validate_plan(plan)
        self.assertIsNotNone(problem)
        assert problem is not None
        self.assertIn("trusted_global_roots", problem)

    def test_agent_skill_invalid_name(self):
        plan = self._golden_plan()
        for entry in plan["entries"]:
            if entry["key"] == "agent_skills.gsd-executor":
                entry["value"] = ["../evil"]
        problem = plan_io.validate_plan(plan)
        self.assertIsNotNone(problem)
        assert problem is not None
        self.assertIn("gsd-executor", problem)

    def test_keep_native_slot_ok(self):
        plan = self._golden_plan()
        plan["entries"].append({
            "key": "models.native_slot",
            "op": "keep",
            "value": "opus",
            "existing": None,
            "source": "preset",
            "why": "native slot",
        })
        self.assertIsNone(plan_io.validate_plan(plan))

    def test_artifact_empty_target_coverage(self):
        plan = self._golden_plan()
        art = plan["artifacts"][0]
        art["config"]["prefer"] = ["pi"]
        art["config"]["models"] = {}
        art["config"]["router_backed"] = {}
        art["choices"] = {}
        art["status"] = "ok"
        problem = plan_io.validate_plan(plan)
        self.assertIsNotNone(problem)
        assert problem is not None
        self.assertIn("pi", problem)


class TestScriptPseudoKeys(unittest.TestCase):
    CURSOR_MODEL = "gemini-3.8-flash-low"

    def _setup_partial(self, tmp):
        inv_path, plan_path, inv, plan = _write_pair(tmp)
        partial = _partial_runner_plan(inv, plan)
        _save_plan(plan_path, inv, partial)
        return inv_path, plan_path, inv, partial

    def test_fill_last_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, _plan = self._setup_partial(tmp)
            code, _, err = _run_plan_set(
                plan_path,
                inv_path,
                "script:cross-ai.model.cursor",
                self.CURSOR_MODEL,
            )
            self.assertEqual(code, 0, err)
            reloaded, _ = plan_io.load_plan(plan_path)
            assert reloaded is not None
            art = reloaded["artifacts"][0]
            self.assertEqual(art["config"]["models"]["cursor"], self.CURSOR_MODEL)
            self.assertEqual(art["choices"], {})
            self.assertEqual(art["status"], "ok")
            self.assertEqual(art["source"], "user")
            cmd = next(
                e for e in reloaded["entries"] if e["key"] == "workflow.cross_ai_command"
            )
            self.assertNotIn("status", cmd)
            self.assertNotIn("candidates", cmd)
            self.assertFalse(any(e["key"].startswith("script:") for e in reloaded["entries"]))

    def test_model_not_in_inventory_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, _plan = self._setup_partial(tmp)
            raw = _read_bytes(plan_path)
            code, _, err = _run_plan_set(
                plan_path,
                inv_path,
                "script:cross-ai.model.cursor",
                "not-a-cursor-model",
            )
            self.assertEqual(code, 2)
            self.assertIn("not listed", err)
            self.assertEqual(_read_bytes(plan_path), raw)
            code, _, err = _run_plan_set(
                plan_path,
                inv_path,
                "script:cross-ai.model.cursor",
                "not-a-cursor-model",
                force=True,
            )
            self.assertEqual(code, 0, err)

    def test_invalid_targets_refused(self):
        cases = [
            ("script:cross-ai.model.claude", "some-model"),
            ("script:cross-ai.model.claude", "other"),
            ("script:cross-ai.prefer", '["grok"]'),
            ("script:cross-ai.prefer", "[]"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, _plan = self._setup_partial(tmp)
            for key, value in cases:
                raw = _read_bytes(plan_path)
                for force in (False, True):
                    code, _, _err = _run_plan_set(
                        plan_path, inv_path, key, value, force=force
                    )
                    self.assertEqual(code, 2, (key, value, force))
                    self.assertEqual(_read_bytes(plan_path), raw)

    def test_prefer_reorder_and_add(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, inv, plan = self._setup_partial(tmp)
            code, _, err = _run_plan_set(
                plan_path, inv_path, "script:cross-ai.prefer", '["cursor", "pi"]'
            )
            self.assertEqual(code, 0, err)
            reloaded, _ = plan_io.load_plan(plan_path)
            assert reloaded is not None
            self.assertEqual(reloaded["artifacts"][0]["config"]["prefer"], ["cursor", "pi"])

            partial = _partial_runner_plan(inv, plan)
            _save_plan(plan_path, inv, partial)
            code, _, err = _run_plan_set(
                plan_path, inv_path, "script:cross-ai.prefer", '["pi", "opencode"]'
            )
            self.assertEqual(code, 0, err)
            reloaded, _ = plan_io.load_plan(plan_path)
            assert reloaded is not None
            art = reloaded["artifacts"][0]
            self.assertEqual(art["config"]["prefer"], ["pi", "opencode"])
            self.assertNotIn("cursor", art["config"]["models"])
            self.assertIn("opencode", art["choices"])
            self.assertEqual(art["status"], "needs_choice")
            cmd = next(
                e for e in reloaded["entries"] if e["key"] == "workflow.cross_ai_command"
            )
            self.assertEqual(cmd.get("status"), "needs_choice")

    def test_plan_unset_script_model_direct(self):
        with tempfile.TemporaryDirectory() as tmp:
            _inv_path, _plan_path, inv, plan = self._setup_partial(tmp)
            encode = _strict_encode()
            call = plan_edit.EditCall(plan, inv, False, encode)
            edited, _warnings = plan_edit.plan_unset(call, "script:cross-ai.model.pi")
            art = edited["artifacts"][0]
            self.assertIn("pi", art["config"]["prefer"])
            self.assertNotIn("pi", art["config"]["models"])
            self.assertIn("pi", art["choices"])
            self.assertEqual(art["status"], "needs_choice")


class TestPlanUnset(unittest.TestCase):
    def test_set_same_as_existing_is_keep(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, plan = _write_pair(tmp)
            key = "workflow.plan_review_convergence"
            entry = next(e for e in plan["entries"] if e["key"] == key)
            existing = entry.get("existing")
            if existing is None:
                self.skipTest("no existing snapshot for convergence")
            code, _, err = _run_plan_set(
                plan_path, inv_path, key, "true" if existing else "false"
            )
            self.assertEqual(code, 0, err)
            reloaded, _ = plan_io.load_plan(plan_path)
            assert reloaded is not None
            row = next(e for e in reloaded["entries"] if e["key"] == key)
            self.assertEqual(row["op"], "keep")
            self.assertEqual(row["source"], "user")

    def test_unset_absent_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, _plan = _write_pair(tmp)
            raw = _read_bytes(plan_path)
            code, _, err = _run_plan_unset(plan_path, inv_path, "nonexistent.key")
            self.assertEqual(code, 2)
            self.assertIn("nonexistent.key", err)
            self.assertEqual(_read_bytes(plan_path), raw)

    def test_unset_script_model_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, inv, plan = _write_pair(tmp)
            partial = _partial_runner_plan(inv, plan)
            _save_plan(plan_path, inv, partial)
            encode = _strict_encode()
            direct, _ = plan_edit.plan_unset(
                plan_edit.EditCall(copy.deepcopy(partial), inv, False, encode),
                "script:cross-ai.model.pi",
            )
            code, _, err = _run_plan_unset(
                plan_path, inv_path, "script:cross-ai.model.pi"
            )
            self.assertEqual(code, 0, err)
            reloaded, _ = plan_io.load_plan(plan_path)
            assert reloaded is not None
            self.assertEqual(
                reloaded["artifacts"][0]["choices"],
                direct["artifacts"][0]["choices"],
            )

    def test_unset_sorts_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, _plan = _write_pair(tmp)
            code, _, err = _run_plan_set(
                plan_path, inv_path, "workflow.live_dom_uat", "true"
            )
            self.assertEqual(code, 0, err)
            code, _, err = _run_plan_unset(
                plan_path, inv_path, "workflow.plan_review_convergence"
            )
            self.assertEqual(code, 0, err)
            reloaded, _ = plan_io.load_plan(plan_path)
            assert reloaded is not None
            keys = [e["key"] for e in reloaded["entries"]]
            self.assertEqual(keys, sorted(keys))

    def test_decline_trusted_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, plan = _write_pair(tmp)
            entry = next(
                e
                for e in plan["entries"]
                if e["key"] == "agent_skills_security.trusted_global_roots"
            )
            existing = entry.get("existing")
            code, _, err = _run_plan_unset(
                plan_path,
                inv_path,
                "agent_skills_security.trusted_global_roots",
            )
            self.assertEqual(code, 0, err)
            reloaded, _ = plan_io.load_plan(plan_path)
            assert reloaded is not None
            row = next(
                e
                for e in reloaded["entries"]
                if e["key"] == "agent_skills_security.trusted_global_roots"
            )
            self.assertEqual(row["op"], "keep")
            self.assertEqual(row["value"], existing)
            self.assertEqual(row["source"], "user")
            self.assertNotIn("status", row)

    def test_unset_timeout_while_execution_on(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, _plan = _write_pair(tmp)
            raw = _read_bytes(plan_path)
            code, _, err = _run_plan_unset(
                plan_path, inv_path, "workflow.cross_ai_timeout"
            )
            self.assertEqual(code, 2)
            self.assertIn("workflow.cross_ai_timeout", err)
            self.assertEqual(_read_bytes(plan_path), raw)

    def test_unset_command_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, inv, plan = _write_pair(tmp)
            for entry in plan["entries"]:
                if entry["key"] == "workflow.cross_ai_command":
                    entry["existing"] = None
            _save_plan(plan_path, inv, plan)
            raw = _read_bytes(plan_path)
            code, _, err = _run_plan_unset(
                plan_path, inv_path, "workflow.cross_ai_command"
            )
            self.assertEqual(code, 2)
            self.assertIn("workflow.cross_ai_command", err)
            self.assertEqual(_read_bytes(plan_path), raw)

    def test_unset_command_keeps_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, inv, plan = _write_pair(tmp)
            for entry in plan["entries"]:
                if entry["key"] == "workflow.cross_ai_command":
                    entry["existing"] = "node .planning/scripts/cross-ai.mjs"
            _save_plan(plan_path, inv, plan)
            code, _, err = _run_plan_unset(
                plan_path, inv_path, "workflow.cross_ai_command"
            )
            self.assertEqual(code, 0, err)
            reloaded, _ = plan_io.load_plan(plan_path)
            assert reloaded is not None
            row = next(
                e for e in reloaded["entries"] if e["key"] == "workflow.cross_ai_command"
            )
            self.assertEqual(row["op"], "keep")

    def test_unset_execution_with_artifact_existing_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, inv, plan = _write_pair(tmp)
            for entry in plan["entries"]:
                if entry["key"] == "workflow.cross_ai_execution":
                    entry["existing"] = False
            _save_plan(plan_path, inv, plan)
            raw = _read_bytes(plan_path)
            code, _, err = _run_plan_unset(
                plan_path, inv_path, "workflow.cross_ai_execution"
            )
            self.assertEqual(code, 2)
            self.assertIn("artifact", err)
            self.assertEqual(_read_bytes(plan_path), raw)

    def test_unset_execution_existing_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, inv, plan = _write_pair(tmp)
            for entry in plan["entries"]:
                if entry["key"] == "workflow.cross_ai_execution":
                    entry["existing"] = True
            _save_plan(plan_path, inv, plan)
            code, _, err = _run_plan_unset(
                plan_path, inv_path, "workflow.cross_ai_execution"
            )
            self.assertEqual(code, 0, err)


class TestExecutionToggle(unittest.TestCase):
    def test_execution_off_strips_deps(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, _plan = _write_pair(tmp)
            code, _, err = _run_plan_set(
                plan_path, inv_path, "workflow.cross_ai_execution", "false"
            )
            self.assertEqual(code, 0, err)
            reloaded, _ = plan_io.load_plan(plan_path)
            assert reloaded is not None
            self.assertEqual(reloaded["artifacts"], [])
            keys = {e["key"] for e in reloaded["entries"]}
            self.assertNotIn("workflow.cross_ai_command", keys)
            self.assertNotIn("workflow.cross_ai_timeout", keys)
            self.assertNotIn("manager.flags.execute", keys)
            kinds = {n.get("kind") for n in reloaded["notes"]}
            self.assertNotIn("cross_ai_run", kinds)

    def test_execution_on_without_artifact_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, _plan = _write_pair(tmp)
            _run_plan_set(plan_path, inv_path, "workflow.cross_ai_execution", "false")
            raw = _read_bytes(plan_path)
            code, _, err = _run_plan_set(
                plan_path, inv_path, "workflow.cross_ai_execution", "true"
            )
            self.assertEqual(code, 2)
            self.assertIn("artifact", err)
            self.assertEqual(_read_bytes(plan_path), raw)

    def test_invalid_plan_blocks_plan_set_at_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, inv, plan = _write_pair(tmp)
            plan["artifacts"] = []
            _save_plan(plan_path, inv, plan)
            raw = _read_bytes(plan_path)
            code, _, err = _run_plan_set(
                plan_path, inv_path, "workflow.plan_review_convergence", "false"
            )
            self.assertEqual(code, 2)
            self.assertIn("artifact", err)
            self.assertEqual(_read_bytes(plan_path), raw)


class TestPlanSetExtra(unittest.TestCase):
    def test_trusted_roots_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, _plan = _write_pair(tmp)
            code, _, err = _run_plan_set(
                plan_path,
                inv_path,
                "agent_skills_security.trusted_global_roots",
                '["~/.agents/skills/react-dev"]',
            )
            self.assertEqual(code, 0, err)
            plan, _ = plan_io.load_plan(plan_path)
            assert plan is not None
            entry = next(
                e for e in plan["entries"]
                if e["key"] == "agent_skills_security.trusted_global_roots"
            )
            self.assertEqual(entry["source"], "user")
            self.assertNotIn("status", entry)

    def test_ponytail_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, _plan = _write_pair(tmp)
            code, _, err = _run_plan_set(
                plan_path, inv_path, "agent_skills.gsd-executor", '["ponytail"]'
            )
            self.assertEqual(code, 0, err)

    def test_strict_encoder_refuses_retype(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, _inv, plan = _write_pair(tmp)
            key = "review.models.opencode"
            if not any(e["key"] == key for e in plan["entries"]):
                self.skipTest("golden plan has no opencode review model entry")
            raw = _read_bytes(plan_path)
            for value in ("12", "true", "[x"):
                code, _, err = _run_plan_set(plan_path, inv_path, key, value, force=True)
                self.assertEqual(code, 2, err)
                self.assertEqual(_read_bytes(plan_path), raw)

    def test_configured_absolute_root_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            inv_path, plan_path, inv, plan = _write_pair(tmp)
            vault = os.path.join(tmp, "vault")
            for entry in plan["entries"]:
                if entry["key"] == "agent_skills_security.trusted_global_roots":
                    entry["existing"] = [vault]
            inv_values = inv["existing_config"]["values"]
            inv_values.setdefault("agent_skills_security", {})["trusted_global_roots"] = [vault]
            with open(inv_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(inv))
            plan["inventory_digest"] = plan_schema.inventory_digest(inv)
            with open(plan_path, "w", encoding="utf-8") as handle:
                handle.write(plan_io.canonical_json(plan))
            payload = json.dumps([vault, "~/.agents/skills/react-dev"])
            code, _, err = _run_plan_set(
                plan_path,
                inv_path,
                "agent_skills_security.trusted_global_roots",
                payload,
            )
            self.assertEqual(code, 0, err)
            saved, _ = plan_io.load_plan(plan_path)
            assert saved is not None
            entry = next(
                e for e in saved["entries"]
                if e["key"] == "agent_skills_security.trusted_global_roots"
            )
            self.assertIn(vault, entry["value"])


if __name__ == "__main__":
    unittest.main()
