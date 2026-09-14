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

    # The next three cases were re-homed here from
    # tests/test_ai_kit_project_rules_agents.py by Phase 9's prune commit
    # (09-CONTEXT.md D-04 / ROADMAP Phase 9) -- they are the only coverage
    # of build_remediation's second ("makefile"-kind) per-kind branch, which
    # Phase 10 depends on. Their second-kind payloads are non-empty and ARE
    # the branch under test; copied verbatim from the pre-prune suite.
    def test_combined_cross_kind_criticality_ordering(self):
        report = {
            "workflow": [
                {
                    "id": "R09",
                    "status": "missing",
                    "criticality": 2,
                    "summary": "workflow high",
                    "matched_signals": [],
                },
            ],
            "makefile": [
                {
                    "target": "setup-env",
                    "present": False,
                    "criticality": 1,
                    "summary": "makefile critical",
                    "recommendation": "uv venv",
                    "needs_research": False,
                },
            ],
        }
        result = build_remediation(report)
        ids_in_order = [entry["id"] for entry in result["remediate"]]
        self.assertEqual(ids_in_order, ["setup-env", "R09"])

    def test_present_but_recommended_structural_finding_in_remediate(self):
        report = {
            "makefile": [
                {
                    "target": "validate",
                    "present": True,
                    "issue": "chain_incomplete",
                    "recommendation": "restructure validate to invoke vulture",
                    "needs_research": False,
                    "criticality": 1,
                    "summary": "restructure validate to invoke vulture",
                },
            ],
        }
        result = build_remediation(report)
        self.assertEqual(len(result["remediate"]), 1)
        self.assertEqual(result["remediate"][0]["id"], "validate")
        self.assertTrue(result["remediate"][0]["auto_apply"])
        self.assertEqual(result["blocked"], [])

    def test_blocked_preserves_stacks(self):
        report = {
            "makefile": [
                {
                    "category": "formatter",
                    "recommendation": None,
                    "needs_research": True,
                    "stacks": ["go", "python"],
                    "criticality": 1,
                    "summary": "Tooling category 'formatter' needs research",
                },
            ],
        }
        result = build_remediation(report)
        self.assertEqual(result["remediate"], [])
        self.assertEqual(len(result["blocked"]), 1)
        self.assertEqual(result["blocked"][0]["id"], "formatter")
        self.assertEqual(result["blocked"][0]["stacks"], ["go", "python"])

    # Plan 10-02 Task 3: two additive edits to the makefile branch -- the
    # advisory flag drives auto-apply, and `issue` is carried forward onto
    # the remediate entry. Both are ADDITIVE: every case above (with no
    # `advisory`/`issue` key) must keep producing exactly what it produces
    # today.
    def test_advisory_finding_disables_auto_apply(self):
        report = {
            "makefile": [
                {
                    "target": "validate",
                    "present": True,
                    "issue": "validate_order_advisory",
                    "advisory": True,
                    "recommendation": "reorder",
                    "needs_research": False,
                    "criticality": 4,
                    "summary": "reorder",
                },
            ],
        }
        result = build_remediation(report)
        self.assertEqual(len(result["remediate"]), 1)
        self.assertFalse(result["remediate"][0]["auto_apply"])

    def test_non_advisory_finding_still_auto_applies(self):
        report = {
            "makefile": [
                {
                    "target": "setup-env",
                    "present": False,
                    "criticality": 1,
                    "summary": "add it",
                    "recommendation": "uv venv",
                    "needs_research": False,
                },
            ],
        }
        result = build_remediation(report)
        self.assertEqual(len(result["remediate"]), 1)
        self.assertTrue(result["remediate"][0]["auto_apply"])

    def test_issue_carried_forward_and_none_when_absent(self):
        with_issue = {
            "makefile": [
                {
                    "target": "validate",
                    "criticality": 1,
                    "summary": "s",
                    "recommendation": "r",
                    "needs_research": False,
                    "issue": "chain_incomplete",
                },
            ],
        }
        without_issue = {
            "makefile": [
                {
                    "target": "setup-env",
                    "criticality": 1,
                    "summary": "s",
                    "recommendation": "r",
                    "needs_research": False,
                },
            ],
        }
        result_with = build_remediation(with_issue)
        result_without = build_remediation(without_issue)
        self.assertEqual(result_with["remediate"][0]["issue"], "chain_incomplete")
        self.assertIsNone(result_without["remediate"][0]["issue"])


# The classes below are re-homed here from
# tests/test_ai_kit_project_rules_agents.py by Phase 10 plan 01 (recovered
# verbatim from commit 9d672b9, Phase 9's rename commit) -- they exercise
# the Makefile-parsing and pre-commit-hook-parsing primitives D-01/D-05
# moved into ai_kit_rules_common.makefile_parse / .precommit_parse.


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


from ai_kit_rules_common.makefile_parse import parse_makefile_targets, recipe_mentions_target


class TestParseMakefileTargets(unittest.TestCase):
    def test_ignores_phony_and_recipe_lines(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                ".PHONY: test\ntest:\n\techo hi\n",
            )
            targets = parse_makefile_targets(os.path.join(repo, "Makefile"))
            self.assertEqual(targets, {"test"})

    def test_missing_file_returns_empty_set(self):
        self.assertEqual(parse_makefile_targets("/nonexistent/Makefile"), set())


class TestRecipeMentionsTargetWordBoundary(unittest.TestCase):
    # Re-homed from TestWiredCheckWordBoundary (9d672b9) -- ONLY the case
    # that exercises the recipe-reference helper's token semantics
    # directly. The two cases that assert through check_makefile_shape
    # stay TestWiredCheckWordBoundary in
    # tests/test_ai_kit_project_rules_makefile.py (this is that class's
    # two-way split).
    def test_hyphenated_name_never_matches_inside_a_longer_hyphenated_token(self):
        # Regression: `\btest-unit\b` alone treats the boundary between
        # "unit" and a following "-integration..." (or a preceding
        # "integration-") as already satisfied, since "-" is a non-word
        # character -- reopening the substring false-positive class this
        # word-boundary check exists to close, just for hyphenated names
        # instead of single-word ones (06-REVIEW.md Critical #2).
        self.assertFalse(
            recipe_mentions_target(
                "\t$(MAKE) test-unit-integration-suite\n", "test-unit"
            )
        )
        self.assertFalse(
            recipe_mentions_target(
                "\t$(MAKE) integration-test-unit\n", "test-unit"
            )
        )
        self.assertTrue(
            recipe_mentions_target("\t$(MAKE) test-unit\n", "test-unit")
        )


from ai_kit_rules_common.precommit_parse import (
    check_precommit_prepush_split,
    parse_precommit_hooks,
)


class TestParsePrecommitHooks(unittest.TestCase):
    def test_parse_precommit_hooks_handles_quoted_ids(self):
        with tempfile.TemporaryDirectory() as repo:
            path = os.path.join(repo, ".pre-commit-config.yaml")
            _write(
                path,
                "repos:\n"
                "  - repo: local\n"
                "    hooks:\n"
                "      - id: ruff\n"
                "        entry: uv run ruff check\n"
                '      - id: "vulture"\n'
                "        entry: uv run vulture\n"
                "      - id: 'pylint'\n"
                "        entry: uv run pylint\n",
            )
            hooks = parse_precommit_hooks(path)
            self.assertEqual(
                hooks,
                {
                    "ruff": "uv run ruff check",
                    "vulture": "uv run vulture",
                    "pylint": "uv run pylint",
                },
            )

    def test_missing_file_returns_empty_dict(self):
        self.assertEqual(
            parse_precommit_hooks("/nonexistent/.pre-commit-config.yaml"), {}
        )


class TestPrecommitPrepushSplit(unittest.TestCase):
    # Re-homed from TestValidateOrderAndPrecommitPrepushSplit (9d672b9) --
    # ONLY the pre-commit-stage-splitter half. The splitter moved to
    # skills/_shared/ai_kit_rules_common/precommit_parse.py (D-01) and has
    # no caller in this phase (Phase 11 owns the check). The class's other
    # two slices -- the ordering-stub half and the
    # test_categories_never_contain_removed_entries schema-shape case --
    # stay under the class's original name,
    # TestValidateOrderAndPrecommitPrepushSplit, in
    # tests/test_ai_kit_project_rules_makefile.py (this is that class's
    # three-way split).
    def test_slow_hook_missing_own_push_stage_is_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                "repos:\n"
                "  - repo: local\n"
                "    hooks:\n"
                "      - id: unittest\n"
                "        entry: python3 -m unittest tests.test_x\n"
                "        language: system\n"
                "      - id: ruff\n"
                "        entry: uv run ruff check\n"
                "        language: system\n"
                "        stages: [push]\n",
            )
            finding = check_precommit_prepush_split(repo)
            self.assertIsNotNone(finding)
            self.assertIn("unittest", finding["slow_hooks_missing_push_stage"])

    def test_slow_hook_with_own_push_stage_not_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                "repos:\n"
                "  - repo: local\n"
                "    hooks:\n"
                "      - id: unittest\n"
                "        entry: python3 -m unittest tests.test_x\n"
                "        language: system\n"
                "        stages: [pre-push]\n",
            )
            finding = check_precommit_prepush_split(repo)
            self.assertIsNone(finding)

    def test_no_slow_hook_nothing_to_verify(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                "repos:\n"
                "  - repo: local\n"
                "    hooks:\n"
                "      - id: ruff\n"
                "        entry: uv run ruff check\n"
                "        language: system\n",
            )
            finding = check_precommit_prepush_split(repo)
            self.assertIsNone(finding)


import ast

from ai_kit_rules_common import criticality as _shared_criticality

_AGENTS_RULES_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "skills",
    "ai-kit-project-rules-agents",
    "ai_kit_project_rules_agents",
    "rules.py",
)


class TestCriticalityDriftGuard(unittest.TestCase):
    """Pins the shared criticality bands against
    ai-kit-project-rules-agents's rules.py literals (a file read via `ast`,
    never a runtime import of another skill's package). Phase 15 orders
    findings across six domains by this number, so two domains silently
    disagreeing about what "critical" means would mis-sort the aggregated
    report -- this is the guard that makes
    ai_kit_rules_common.criticality's docstring claim checkable."""

    def test_shared_bands_match_agents_skill_literals(self):
        with open(_AGENTS_RULES_PATH, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        literals = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if target.id not in (
                "CRITICALITY_CRITICAL",
                "CRITICALITY_HIGH",
                "CRITICALITY_MEDIUM",
            ):
                continue
            if isinstance(node.value, ast.Constant):
                literals[target.id] = node.value.value
        self.assertEqual(
            len(literals),
            3,
            f"expected exactly 3 criticality literals in {_AGENTS_RULES_PATH}, "
            f"found {literals}",
        )
        self.assertEqual(
            (
                literals["CRITICALITY_CRITICAL"],
                literals["CRITICALITY_HIGH"],
                literals["CRITICALITY_MEDIUM"],
            ),
            (
                _shared_criticality.CRITICALITY_CRITICAL,
                _shared_criticality.CRITICALITY_HIGH,
                _shared_criticality.CRITICALITY_MEDIUM,
            ),
            "ai_kit_rules_common.criticality's bands drifted from "
            "ai-kit-project-rules-agents's rules.py literals -- Phase 15 "
            "orders findings across six domains by this number, so two "
            "domains silently disagreeing about what 'critical' means "
            "mis-sorts the aggregated report.",
        )


# Appended by Phase 11 plan 01: the generalized remediation's `precommit`
# kind, the generic cache-payload validator, the taxonomy vocabulary, and
# the provenance-citation drift guard between the shared generic validator
# and ai-kit-project-rules-makefile's own tooling_payload.py validator.


class TestRemediationPrecommitKind(unittest.TestCase):
    """Additive coverage for `STRUCTURAL_KINDS` growing to include
    `"precommit"` (Phase 11 plan 01). Every case here must leave
    `TestRemediation`'s existing makefile-only assertions untouched."""

    def test_backcompat_report_carrying_only_sibling_kind_is_byte_identical(self):
        report = {
            "makefile": [
                {
                    "target": "x",
                    "criticality": 3,
                    "summary": "s",
                    "recommendation": "r",
                    "issue": "i",
                },
            ],
        }
        result = build_remediation(report)
        self.assertEqual(
            result["remediate"],
            [
                {
                    "kind": "makefile",
                    "id": "x",
                    "criticality": 3,
                    "summary": "s",
                    "issue": "i",
                    "auto_apply": True,
                }
            ],
        )
        self.assertEqual(result["blocked"], [])

    def test_cross_kind_ordering_discriminates_from_insertion_order(self):
        # Insertion order is makefile-then-precommit; criticality order is
        # the OPPOSITE (precommit=1 before makefile=3) -- the two disagree
        # on purpose, so a per-kind (rather than one merged, sorted) list
        # implementation would fail this the same way it would fail
        # `test_combined_cross_kind_criticality_ordering` above.
        report = {
            "makefile": [
                {"target": "m", "criticality": 3, "summary": "s", "recommendation": "r"}
            ],
            "precommit": [
                {"category": "p", "criticality": 1, "summary": "s", "recommendation": "r"}
            ],
        }
        result = build_remediation(report)
        self.assertEqual([e["kind"] for e in result["remediate"]], ["precommit", "makefile"])

    def test_precommit_kind_advisory_disables_auto_apply(self):
        report = {
            "precommit": [
                {
                    "category": "precommit-parity",
                    "criticality": 2,
                    "summary": "s",
                    "recommendation": "r",
                    "advisory": True,
                }
            ]
        }
        result = build_remediation(report)
        self.assertEqual(len(result["remediate"]), 1)
        self.assertFalse(result["remediate"][0]["auto_apply"])
        self.assertEqual(result["remediate"][0]["kind"], "precommit")

    def test_precommit_kind_needs_research_goes_to_blocked(self):
        report = {
            "precommit": [
                {
                    "category": "precommit-parity",
                    "criticality": 2,
                    "summary": "s",
                    "recommendation": None,
                    "needs_research": True,
                    "stacks": ["python"],
                }
            ]
        }
        result = build_remediation(report)
        self.assertEqual(result["remediate"], [])
        self.assertEqual(len(result["blocked"]), 1)
        self.assertEqual(result["blocked"][0]["kind"], "precommit")
        self.assertEqual(result["blocked"][0]["stacks"], ["python"])


from ai_kit_rules_common import stack_cache as _shared_stack_cache
from ai_kit_rules_common.stack_cache import validate_stack_payload


class TestValidateStackPayloadGeneric(unittest.TestCase):
    def test_valid_payload_for_arbitrary_key_set(self):
        self.assertIsNone(
            validate_stack_payload({"alpha": "tool (source: https://x)"}, ("alpha", "beta"))
        )

    def test_rejects_unknown_key(self):
        self.assertIsNotNone(
            validate_stack_payload({"gamma": "tool (source: https://x)"}, ("alpha", "beta"))
        )

    def test_rejects_non_string_or_empty_value(self):
        self.assertIsNotNone(validate_stack_payload({"alpha": 123}, ("alpha",)))
        self.assertIsNotNone(validate_stack_payload({"alpha": ""}, ("alpha",)))

    def test_rejects_absent_citation(self):
        self.assertIsNotNone(
            validate_stack_payload({"alpha": "tool, no citation here"}, ("alpha",))
        )

    def test_rejects_empty_or_whitespace_only_citation(self):
        self.assertIsNotNone(validate_stack_payload({"alpha": "tool (source:)"}, ("alpha",)))
        self.assertIsNotNone(validate_stack_payload({"alpha": "tool (source: )"}, ("alpha",)))

    def test_rejects_non_dict_payload(self):
        self.assertIsNotNone(validate_stack_payload(["not", "a", "dict"], ("alpha",)))


from ai_kit_rules_common.tool_catalog import TAXONOMY_CATEGORIES


class TestTaxonomyVocabulary(unittest.TestCase):
    def test_exactly_six_names_in_pinned_order(self):
        self.assertEqual(
            list(TAXONOMY_CATEGORIES),
            [
                "formatting",
                "type-checking",
                "linting",
                "security",
                "duplicate-code",
                "dead-code",
            ],
        )

    def test_no_duplicates(self):
        self.assertEqual(len(TAXONOMY_CATEGORIES), len(set(TAXONOMY_CATEGORIES)))


_MAKEFILE_SKILL_TOOLING_PAYLOAD_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "skills",
    "ai-kit-project-rules-makefile",
    "ai_kit_project_rules_makefile",
    "tooling_payload.py",
)


class TestProvenanceCitationRegexDriftGuard(unittest.TestCase):
    """Pins `ai_kit_rules_common.stack_cache`'s generic validator's citation
    regex against `ai-kit-project-rules-makefile`'s own `tooling_payload.py`
    literal (a file read via `ast`, never a runtime import of another
    skill's package). Two skills disagreeing about what counts as a cited
    recommendation means one of them admits an uncited tool name into a
    cache it later reports as researched fact."""

    def test_shared_citation_regex_matches_sibling_skill_literal(self):
        with open(_MAKEFILE_SKILL_TOOLING_PAYLOAD_PATH, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        literal = None
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name) or target.id != "_SOURCE_CITATION_RE":
                continue
            if isinstance(node.value, ast.Call) and node.value.args:
                arg = node.value.args[0]
                if isinstance(arg, ast.Constant):
                    literal = arg.value
        self.assertIsNotNone(
            literal,
            f"no _SOURCE_CITATION_RE string literal found in "
            f"{_MAKEFILE_SKILL_TOOLING_PAYLOAD_PATH}",
        )
        self.assertEqual(
            literal,
            _shared_stack_cache._SOURCE_CITATION_RE.pattern,
            "ai_kit_rules_common.stack_cache's citation regex drifted from "
            "ai-kit-project-rules-makefile's tooling_payload.py literal -- "
            "two skills disagreeing about what counts as a cited "
            "recommendation means one of them admits an uncited tool name "
            "into a cache it later reports as researched fact.",
        )


if __name__ == "__main__":
    unittest.main()
