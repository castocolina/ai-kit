import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "_shared"),
)

from ai_kit_rules_common.classification import check_rules, evaluate_condition

_RULES = (
    {
        "id": "X01",
        "category": "demo",
        "criticality": 1,
        "condition": "always",
        "signals": ("alpha", "beta", "gamma"),
        "summary": "demo flat rule",
    },
    {
        "id": "X02",
        "category": "demo",
        "criticality": 2,
        "condition": "tool-presence:widget",
        "signals": (("one", "uno"), ("two", "dos")),
        "summary": "demo grouped rule",
    },
    {
        "id": "X03",
        "category": "demo",
        "criticality": 3,
        "condition": "always",
        "signals": (("rg", ("rg", "ripgrep")), ("bat", ("bat", "batcat"))),
        "summary": "demo tool-scoped rule",
    },
)


class TestEvaluateCondition(unittest.TestCase):
    def test_always_is_true(self):
        self.assertTrue(evaluate_condition("always", {}))

    def test_tool_presence_looks_up_dict(self):
        self.assertTrue(evaluate_condition("tool-presence:widget", {"widget": True}))
        self.assertFalse(evaluate_condition("tool-presence:widget", {"widget": False}))
        self.assertFalse(evaluate_condition("tool-presence:widget", {}))

    def test_unknown_condition_shape_is_false(self):
        self.assertFalse(evaluate_condition("bogus", {}))


class TestCheckRulesFlat(unittest.TestCase):
    def test_no_signals_matched_is_missing(self):
        findings = check_rules("nothing relevant here", {}, _RULES, include_present=True)
        x01 = next(f for f in findings if f["id"] == "X01")
        self.assertEqual(x01["status"], "missing")
        self.assertEqual(x01["matched_signals"], [])

    def test_majority_of_three_signals_is_present(self):
        findings = check_rules("alpha and beta both appear", {}, _RULES, include_present=True)
        x01 = next(f for f in findings if f["id"] == "X01")
        self.assertEqual(x01["status"], "present")
        self.assertEqual(x01["matched_signals"], ["alpha", "beta"])

    def test_one_of_three_signals_is_near_miss(self):
        findings = check_rules("only alpha appears", {}, _RULES, include_present=True)
        x01 = next(f for f in findings if f["id"] == "X01")
        self.assertEqual(x01["status"], "near_miss")


class TestCheckRulesGroups(unittest.TestCase):
    def test_condition_not_met_is_not_applicable(self):
        findings = check_rules("one appears", {"widget": False}, _RULES, include_present=True)
        x02 = next(f for f in findings if f["id"] == "X02")
        self.assertEqual(x02["status"], "not_applicable")

    def test_one_group_satisfied_is_near_miss(self):
        findings = check_rules(
            "one appears but the second item does not",
            {"widget": True},
            _RULES,
            include_present=True,
        )
        x02 = next(f for f in findings if f["id"] == "X02")
        self.assertEqual(x02["status"], "near_miss")

    def test_all_groups_satisfied_is_present(self):
        findings = check_rules(
            "one and two both appear", {"widget": True}, _RULES, include_present=True
        )
        x02 = next(f for f in findings if f["id"] == "X02")
        self.assertEqual(x02["status"], "present")


class TestCheckRulesToolScoped(unittest.TestCase):
    def test_no_scoped_tool_present_is_not_applicable(self):
        findings = check_rules(
            "rg and bat both mentioned",
            {"modern-cli:rg": False, "modern-cli:bat": False},
            _RULES,
            include_present=True,
        )
        x03 = next(f for f in findings if f["id"] == "X03")
        self.assertEqual(x03["status"], "not_applicable")

    def test_only_present_tools_are_required(self):
        findings = check_rules(
            "rg is mentioned but not the other one",
            {"modern-cli:rg": True, "modern-cli:bat": False},
            _RULES,
            include_present=True,
        )
        x03 = next(f for f in findings if f["id"] == "X03")
        self.assertEqual(x03["status"], "present")
        self.assertEqual(x03["missing_tools"], [])


class TestCheckRulesIncludePresent(unittest.TestCase):
    def test_default_excludes_present_findings(self):
        findings = check_rules("alpha and beta both appear", {}, _RULES)
        ids = {f["id"] for f in findings}
        self.assertNotIn("X01", ids)

    def test_include_present_keeps_everything(self):
        findings = check_rules("alpha and beta both appear", {}, _RULES, include_present=True)
        ids = {f["id"] for f in findings}
        self.assertIn("X01", ids)


import tempfile

from ai_kit_rules_common.tool_presence import MODERN_CLI_TOOLS, check_tool_presence


class TestToolPresence(unittest.TestCase):
    def test_empty_path_and_repo_all_false(self):
        with tempfile.TemporaryDirectory() as repo:
            result = check_tool_presence(search_path="", repo_root=repo)
        self.assertFalse(result["rtk"])
        self.assertFalse(result["modern-cli"])
        self.assertFalse(result["codegraph"])
        self.assertFalse(result["graphify"])
        self.assertFalse(result["gsd"])
        for tool in MODERN_CLI_TOOLS:
            self.assertFalse(result[f"modern-cli:{tool}"])

    def test_codegraph_and_gsd_dirs_detected(self):
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, ".codegraph"))
            os.makedirs(os.path.join(repo, ".planning"))
            result = check_tool_presence(search_path="", repo_root=repo)
        self.assertTrue(result["codegraph"])
        self.assertTrue(result["gsd"])


import json
from datetime import UTC, datetime, timedelta

from ai_kit_rules_common.stack_cache import (
    STALE_AFTER_DAYS,
    cache_path,
    default_cache_root,
    get_stack_tooling,
    read_stack_cache,
    write_stack_cache,
)


class TestStackCache(unittest.TestCase):
    def test_default_cache_root_includes_namespace(self):
        root = default_cache_root("demo-skill")
        self.assertIn("demo-skill", root)
        self.assertTrue(root.endswith(os.path.join("demo-skill", "stack-refs")))

    def test_absent_fresh_stale(self):
        with tempfile.TemporaryDirectory() as scratch:
            cache_root = os.path.join(scratch, "_cache")
            self.assertEqual(
                read_stack_cache("python", cache_root=cache_root)["state"], "absent"
            )

            write_stack_cache(
                "python", {"setup-env": "uv sync"}, cache_root=cache_root
            )
            self.assertEqual(
                read_stack_cache("python", cache_root=cache_root)["state"], "fresh"
            )

            path = cache_path("python", cache_root=cache_root)
            with open(path, encoding="utf-8") as handle:
                payload = json.load(handle)
            stale_dt = datetime.now(UTC) - timedelta(days=STALE_AFTER_DAYS + 1)
            payload["cached_at"] = stale_dt.isoformat()
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            self.assertEqual(
                read_stack_cache("python", cache_root=cache_root)["state"], "stale"
            )

    def test_invalid_stack_identifier_raises(self):
        with self.assertRaises(ValueError):
            cache_path("../escape", cache_root="/tmp/whatever")

    def test_get_stack_tooling_needs_research_when_absent_or_stale(self):
        with tempfile.TemporaryDirectory() as scratch:
            cache_root = os.path.join(scratch, "_cache")
            tooling, needs_research = get_stack_tooling("python", cache_root=cache_root)
            self.assertIsNone(tooling)
            self.assertTrue(needs_research)

            write_stack_cache("python", {"setup-env": "uv sync"}, cache_root=cache_root)
            tooling, needs_research = get_stack_tooling("python", cache_root=cache_root)
            self.assertEqual(tooling, {"setup-env": "uv sync"})
            self.assertFalse(needs_research)

    def test_corrupted_json_is_absent(self):
        with tempfile.TemporaryDirectory() as scratch:
            cache_root = os.path.join(scratch, "_cache")
            path = cache_path("python", cache_root=cache_root)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{not valid json")
            self.assertEqual(
                read_stack_cache("python", cache_root=cache_root),
                {"state": "absent", "data": None},
            )

    def test_non_dict_payload_is_absent(self):
        with tempfile.TemporaryDirectory() as scratch:
            cache_root = os.path.join(scratch, "_cache")
            path = cache_path("python", cache_root=cache_root)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump([1, 2, 3], handle)
            self.assertEqual(
                read_stack_cache("python", cache_root=cache_root),
                {"state": "absent", "data": None},
            )

    def test_missing_or_malformed_cached_at_is_stale(self):
        with tempfile.TemporaryDirectory() as scratch:
            cache_root = os.path.join(scratch, "_cache")
            path = cache_path("python", cache_root=cache_root)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tooling = {"setup-env": "uv sync"}
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"tooling": tooling}, handle)
            missing = read_stack_cache("python", cache_root=cache_root)
            self.assertEqual(missing["state"], "stale")
            self.assertEqual(missing["data"], tooling)

            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"cached_at": "not-a-datetime", "tooling": tooling}, handle)
            malformed = read_stack_cache("python", cache_root=cache_root)
            self.assertEqual(malformed["state"], "stale")
            self.assertEqual(malformed["data"], tooling)

    def test_naive_cached_at_normalized_to_utc_and_stale(self):
        with tempfile.TemporaryDirectory() as scratch:
            cache_root = os.path.join(scratch, "_cache")
            path = cache_path("python", cache_root=cache_root)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            naive_old = (
                datetime.now(UTC) - timedelta(days=STALE_AFTER_DAYS + 1)
            ).replace(tzinfo=None)
            cached_at = naive_old.isoformat()
            self.assertNotIn("+", cached_at)
            self.assertFalse(cached_at.endswith("Z"))
            tooling = {"setup-env": "uv sync"}
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"cached_at": cached_at, "tooling": tooling}, handle)
            result = read_stack_cache("python", cache_root=cache_root)
            self.assertEqual(result["state"], "stale")
            self.assertEqual(result["data"], tooling)


from ai_kit_rules_common.remediation import build_remediation


class TestRemediation(unittest.TestCase):
    def test_missing_and_near_miss_auto_apply(self):
        report = {
            "workflow": [
                {"id": "X01", "status": "missing", "criticality": 1, "summary": "s1"},
                {"id": "X02", "status": "near_miss", "criticality": 2, "summary": "s2"},
                {"id": "X03", "status": "present", "criticality": 3, "summary": "s3"},
            ]
        }
        result = build_remediation(report)
        ids = {e["id"]: e["auto_apply"] for e in result["remediate"]}
        self.assertEqual(ids, {"X01": True, "X02": False})
        self.assertEqual(result["blocked"], [])

    def test_returns_dict_never_bare_list(self):
        result = build_remediation({"workflow": []})
        self.assertIsInstance(result, dict)
        self.assertEqual(result, {"remediate": [], "blocked": []})

    def test_unknown_kind_keys_ignored_safely(self):
        # A report carrying a kind key this module doesn't branch on (e.g.
        # a future precommit-checker's findings, see this task's Interfaces
        # "Known scope limit" note) must not crash build_remediation -- the
        # unknown kind's findings are silently dropped, not validated
        # against a fixed kind list, and findings under known kinds are
        # still processed normally alongside it.
        result = build_remediation(
            {
                "workflow": [
                    {
                        "id": "X01",
                        "status": "missing",
                        "criticality": 1,
                        "summary": "s1",
                    }
                ],
                "precommit": [{"id": "Y01", "status": "missing", "criticality": 1}],
            }
        )
        self.assertEqual(len(result["remediate"]), 1)
        self.assertEqual(result["remediate"][0]["id"], "X01")
        self.assertEqual(result["blocked"], [])


if __name__ == "__main__":
    unittest.main()
