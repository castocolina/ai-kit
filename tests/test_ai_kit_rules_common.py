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


if __name__ == "__main__":
    unittest.main()
