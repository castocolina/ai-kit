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


from ai_kit_rules_common.remediation import STRUCTURAL_KINDS, build_remediation


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


from ai_kit_rules_common.makefile_parse import (
    parse_makefile_targets,
    parse_makefile_targets_ordered,
    recipe_mentions_target,
)


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


class TestParseMakefileTargetsOrdered(unittest.TestCase):
    """D-A1's declaration-order tie-break needs this reader (Phase 12 plan
    01) -- coverage placed beside the existing `parse_makefile_targets`
    coverage above, in this file's style. Every pre-existing
    `makefile_parse` assertion above and below must keep passing
    byte-for-byte; this class is purely additive."""

    def test_declaration_order_is_preserved(self):
        with tempfile.TemporaryDirectory() as repo:
            path = os.path.join(repo, "Makefile")
            _write(path, "zeta: alpha\n\techo z\n\nalpha:\n\techo a\n")
            self.assertEqual(parse_makefile_targets_ordered(path), ["zeta", "alpha"])

    def test_repeated_header_deduplicates_to_first_occurrence(self):
        with tempfile.TemporaryDirectory() as repo:
            path = os.path.join(repo, "Makefile")
            _write(
                path,
                "zeta: alpha\n\techo z\n\nalpha:\n\techo a\n\nzeta:\n\techo dup\n",
            )
            self.assertEqual(parse_makefile_targets_ordered(path), ["zeta", "alpha"])

    def test_var_assignment_and_phony_exclusions_still_apply(self):
        with tempfile.TemporaryDirectory() as repo:
            path = os.path.join(repo, "Makefile")
            _write(
                path,
                "VAR := x\n\n.PHONY: zeta alpha\n\nzeta: alpha\n\techo z\n\nalpha:\n\techo a\n",
            )
            self.assertEqual(parse_makefile_targets_ordered(path), ["zeta", "alpha"])

    def test_missing_file_returns_empty_list(self):
        self.assertEqual(parse_makefile_targets_ordered("/nonexistent/Makefile"), [])

    def test_set_reader_agrees_with_ordered_reader(self):
        # The property that proves the two readers are one parse rather
        # than two -- `parse_makefile_targets` is defined in terms of
        # `parse_makefile_targets_ordered`, so they can never disagree.
        with tempfile.TemporaryDirectory() as repo:
            path = os.path.join(repo, "Makefile")
            _write(path, "zeta: alpha\n\techo z\n\nalpha:\n\techo a\n\nbeta:\n\techo b\n")
            ordered = parse_makefile_targets_ordered(path)
            self.assertEqual(parse_makefile_targets(path), set(ordered))


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


class TestRemediationArchKind(unittest.TestCase):
    """Additive coverage for `STRUCTURAL_KINDS` growing to include `"arch"`
    (Phase 12 plan 01). Every case here must leave `TestRemediation`'s and
    `TestRemediationPrecommitKind`'s existing assertions untouched."""

    def test_structural_kinds_has_three_kinds_original_two_unchanged(self):
        self.assertEqual(STRUCTURAL_KINDS[:2], ("makefile", "precommit"))
        self.assertIn("arch", STRUCTURAL_KINDS)
        self.assertEqual(len(STRUCTURAL_KINDS), len(set(STRUCTURAL_KINDS)))

    def test_backcompat_report_carrying_only_two_pre_existing_kinds_is_byte_identical(self):
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
            "precommit": [
                {
                    "category": "p",
                    "criticality": 1,
                    "summary": "s2",
                    "recommendation": "r2",
                },
            ],
        }
        result = build_remediation(report)
        self.assertEqual(
            result["remediate"],
            [
                {
                    "kind": "precommit",
                    "id": "p",
                    "criticality": 1,
                    "summary": "s2",
                    "issue": None,
                    "auto_apply": True,
                },
                {
                    "kind": "makefile",
                    "id": "x",
                    "criticality": 3,
                    "summary": "s",
                    "issue": "i",
                    "auto_apply": True,
                },
            ],
        )
        self.assertEqual(result["blocked"], [])

    def test_all_three_kinds_order_as_one_list_disagreeing_with_insertion_order(self):
        # Insertion order is makefile-then-precommit-then-arch; criticality
        # order disagrees on purpose (arch=1, makefile=3, precommit=4) --
        # a per-kind implementation would print insertion order instead.
        report = {
            "makefile": [
                {"target": "m", "criticality": 3, "summary": "s", "recommendation": "r"}
            ],
            "precommit": [
                {"category": "p", "criticality": 4, "summary": "s", "recommendation": "r"}
            ],
            "arch": [
                {"category": "a", "criticality": 1, "summary": "s", "recommendation": "r"}
            ],
        }
        result = build_remediation(report)
        self.assertEqual(
            [e["kind"] for e in result["remediate"]], ["arch", "makefile", "precommit"]
        )

    def test_arch_kind_advisory_disables_auto_apply(self):
        report = {
            "arch": [
                {
                    "category": "arch-test-chaining",
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
        self.assertEqual(result["remediate"][0]["kind"], "arch")

    def test_arch_kind_needs_research_goes_to_blocked(self):
        report = {
            "arch": [
                {
                    "category": "arch-test-target",
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
        self.assertEqual(result["blocked"][0]["kind"], "arch")
        self.assertEqual(result["blocked"][0]["stacks"], ["python"])

    def test_identifier_precedence_category_only_yields_category_as_id(self):
        # remediation.py:86's `finding.get("target", finding.get("category"))`
        # pinned as a property, not left implicit -- this is the shared-module
        # fact the arch skill's D-A3 `target`-key prohibition depends on.
        report = {
            "arch": [
                {
                    "category": "arch-test-target",
                    "criticality": 2,
                    "summary": "s",
                    "recommendation": "r",
                }
            ]
        }
        result = build_remediation(report)
        self.assertEqual(result["remediate"][0]["id"], "arch-test-target")

    def test_identifier_precedence_target_key_wins_over_category(self):
        report = {
            "arch": [
                {
                    "target": "some-makefile-target",
                    "category": "arch-test-target",
                    "criticality": 2,
                    "summary": "s",
                    "recommendation": "r",
                }
            ]
        }
        result = build_remediation(report)
        self.assertEqual(result["remediate"][0]["id"], "some-makefile-target")


class TestRemediationDockerKind(unittest.TestCase):
    """Additive coverage for `STRUCTURAL_KINDS` growing to include
    `"docker"` (Phase 13 plan 01). Every case here must leave
    `TestRemediation`'s, `TestRemediationPrecommitKind`'s, and
    `TestRemediationArchKind`'s existing assertions untouched."""

    def test_structural_kinds_has_four_kinds_original_three_unchanged(self):
        self.assertEqual(STRUCTURAL_KINDS[:3], ("makefile", "precommit", "arch"))
        self.assertIn("docker", STRUCTURAL_KINDS)
        self.assertEqual(len(STRUCTURAL_KINDS), len(set(STRUCTURAL_KINDS)))

    def test_backcompat_report_carrying_only_three_pre_existing_kinds_is_byte_identical(self):
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
            "precommit": [
                {
                    "category": "p",
                    "criticality": 1,
                    "summary": "s2",
                    "recommendation": "r2",
                },
            ],
            "arch": [
                {
                    "category": "a",
                    "criticality": 2,
                    "summary": "s3",
                    "recommendation": "r3",
                },
            ],
        }
        result = build_remediation(report)
        self.assertEqual(
            result["remediate"],
            [
                {
                    "kind": "precommit",
                    "id": "p",
                    "criticality": 1,
                    "summary": "s2",
                    "issue": None,
                    "auto_apply": True,
                },
                {
                    "kind": "arch",
                    "id": "a",
                    "criticality": 2,
                    "summary": "s3",
                    "issue": None,
                    "auto_apply": True,
                },
                {
                    "kind": "makefile",
                    "id": "x",
                    "criticality": 3,
                    "summary": "s",
                    "issue": "i",
                    "auto_apply": True,
                },
            ],
        )
        self.assertEqual(result["blocked"], [])

    def test_all_four_kinds_order_as_one_list_disagreeing_with_insertion_order(self):
        # Insertion order is makefile-then-precommit-then-arch-then-docker;
        # criticality order disagrees on purpose (docker=1, arch=2,
        # makefile=3, precommit=4) -- a per-kind implementation would
        # print insertion order instead.
        report = {
            "makefile": [
                {"target": "m", "criticality": 3, "summary": "s", "recommendation": "r"}
            ],
            "precommit": [
                {"category": "p", "criticality": 4, "summary": "s", "recommendation": "r"}
            ],
            "arch": [{"category": "a", "criticality": 2, "summary": "s", "recommendation": "r"}],
            "docker": [
                {
                    "category": "docker-target-family",
                    "target": "docker-up",
                    "criticality": 1,
                    "summary": "s",
                    "recommendation": "r",
                }
            ],
        }
        result = build_remediation(report)
        self.assertEqual(
            [e["kind"] for e in result["remediate"]],
            ["docker", "arch", "makefile", "precommit"],
        )

    def test_docker_kind_advisory_disables_auto_apply(self):
        report = {
            "docker": [
                {
                    "category": "docker-local-runbook",
                    "criticality": 3,
                    "summary": "s",
                    "recommendation": "r",
                    "advisory": True,
                }
            ]
        }
        result = build_remediation(report)
        self.assertEqual(len(result["remediate"]), 1)
        self.assertFalse(result["remediate"][0]["auto_apply"])
        self.assertEqual(result["remediate"][0]["kind"], "docker")

    def test_docker_kind_needs_research_goes_to_blocked(self):
        report = {
            "docker": [
                {
                    "category": "docker-target-family",
                    "criticality": 3,
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
        self.assertEqual(result["blocked"][0]["kind"], "docker")
        self.assertEqual(result["blocked"][0]["stacks"], ["python"])

    def test_identifier_precedence_target_key_wins_for_docker_target_findings(self):
        # remediation.py:88's `finding.get("target", finding.get("category"))`
        # pinned as a property, not left implicit -- this is the shared-module
        # fact the docker skill's D-D3 `target`-key rule depends on for its
        # target-family findings (the one place in that skill the key is
        # correct).
        report = {
            "docker": [
                {
                    "target": "docker-up",
                    "category": "docker-target-family",
                    "criticality": 3,
                    "summary": "s",
                    "recommendation": "r",
                }
            ]
        }
        result = build_remediation(report)
        self.assertEqual(result["remediate"][0]["id"], "docker-up")

    def test_identifier_precedence_category_only_for_docker_runbook_finding(self):
        report = {
            "docker": [
                {
                    "category": "docker-local-runbook",
                    "criticality": 3,
                    "summary": "s",
                    "recommendation": "r",
                }
            ]
        }
        result = build_remediation(report)
        self.assertEqual(result["remediate"][0]["id"], "docker-local-runbook")


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


# Appended by Phase 11 plan 02: the shared catalog's baseline stacks table,
# derived tool-to-category index, D-T7 pairs reachability, ambiguous-tool
# defaults, out-of-taxonomy markers, Makefile-category alias table (+ its
# drift guard), and the redundant-vs-complementary pairs lookup.

from ai_kit_rules_common import tool_catalog as _tc


class TestBaselineStacksShape(unittest.TestCase):
    def test_all_five_stacks_present_with_all_six_category_keys(self):
        self.assertEqual(set(_tc.BASELINE_STACKS), {"python", "node", "java", "rust", "go"})
        for stack, categories in _tc.BASELINE_STACKS.items():
            self.assertEqual(
                set(categories),
                set(_tc.TAXONOMY_CATEGORIES),
                f"{stack} does not carry all six category keys",
            )

    def test_empty_category_allowed_only_for_inherent_ones(self):
        # type-checking is N/A (compiler-inherent) for java/rust/go; every
        # entry STRING within a non-empty category is a non-empty string.
        for stack, categories in _tc.BASELINE_STACKS.items():
            for category, entries in categories.items():
                for entry in entries:
                    self.assertIsInstance(entry, str)
                    self.assertTrue(entry, f"{stack}/{category} has an empty entry string")
        for stack in ("java", "rust", "go"):
            self.assertEqual(_tc.BASELINE_STACKS[stack]["type-checking"], ())


class TestToolCategoryIndexDerivation(unittest.TestCase):
    def test_every_baseline_entry_resolves_to_its_own_category(self):
        for categories in _tc.BASELINE_STACKS.values():
            for category, entries in categories.items():
                for entry in entries:
                    self.assertEqual(_tc.TOOL_CATEGORY_INDEX[entry], category)

    def test_index_contains_no_key_absent_from_both_tables(self):
        baseline_entries = {
            entry
            for categories in _tc.BASELINE_STACKS.values()
            for entries in categories.values()
            for entry in entries
        }
        allowed = baseline_entries | set(_tc._SUPPLEMENTARY_INDEX_ENTRIES)
        self.assertEqual(set(_tc.TOOL_CATEGORY_INDEX), allowed)

    def test_no_index_key_contains_a_plus_sign(self):
        # The cheapest mechanical catch for a "+"-joined cell transcribed as
        # one combined string instead of two entries.
        self.assertFalse([k for k in _tc.TOOL_CATEGORY_INDEX if "+" in k])

    def test_plus_and_slash_joined_cells_were_really_split(self):
        # Node linting cell ("eslint"+"typescript-eslint") and Java
        # formatting cell ("spotless"+"google-java-format") each resolve
        # through the index on their own.
        for entry, category in (
            ("eslint", "linting"),
            ("typescript-eslint", "linting"),
            ("spotless", "formatting"),
            ("google-java-format", "formatting"),
        ):
            self.assertEqual(_tc.TOOL_CATEGORY_INDEX[entry], category)

    def test_collision_guard_is_non_vacuous(self):
        """A constructed two-category collision must raise -- proven by a
        fixture table the real table's own silence cannot substitute for."""
        colliding = {
            "alpha-stack": {
                "formatting": ("shared-tool-name",),
                "type-checking": (),
                "linting": (),
                "security": (),
                "duplicate-code": (),
                "dead-code": (),
            },
            "beta-stack": {
                "formatting": (),
                "type-checking": ("shared-tool-name",),
                "linting": (),
                "security": (),
                "duplicate-code": (),
                "dead-code": (),
            },
        }
        with self.assertRaises(ImportError):
            _derive_from(colliding)


def _derive_from(baseline):
    """Re-implements `_derive_tool_category_index`'s collision rule against
    an arbitrary baseline mapping, so the guard is proven non-vacuous
    without needing `tool_catalog` to expose a parameterized variant of its
    own import-time-only function."""
    index = {}
    for categories in baseline.values():
        for category, entries in categories.items():
            for entry in entries:
                existing = index.get(entry)
                if existing is not None and existing != category:
                    raise ImportError(
                        f"collision: {entry!r} is both {existing!r} and {category!r}"
                    )
                index[entry] = category
    return index


class TestResolveToolCategory(unittest.TestCase):
    def test_baseline_entries_resolve(self):
        self.assertEqual(_tc.resolve_tool_category("ruff format"), "formatting")
        self.assertEqual(_tc.resolve_tool_category("mypy"), "type-checking")

    def test_case_folded(self):
        self.assertEqual(_tc.resolve_tool_category("MYPY"), "type-checking")

    def test_supplementary_entries_resolve(self):
        for tool_name in ("staticcheck", "ts-prune", "cargo-audit", "semgrep"):
            self.assertIsNotNone(_tc.resolve_tool_category(tool_name))

    def test_ambiguous_default_resolves_without_being_an_index_key(self):
        # The bare Python formatter/linter binary name resolves through the
        # defaults map chain link, NOT through index membership: indexing it
        # would collide its two suffixed entries or forge a `baseline`
        # confidence D-T3 reserves for an inference. This is the guard shape
        # the cross-AI review's cycle 2 HIGH ruled unsatisfiable if written
        # as index-membership-only.
        self.assertNotIn("ruff", _tc.TOOL_CATEGORY_INDEX)
        self.assertEqual(_tc.resolve_tool_category("ruff"), "linting")

    def test_rule_family_member_absent_from_index_and_resolves_to_none(self):
        # "ruff S rules" is a rule selector, not an invocable tool -- it is
        # not a member of the index, and resolve_tool_category must answer
        # None for it (it is not a tool at all).
        self.assertNotIn("ruff S rules", _tc.TOOL_CATEGORY_INDEX)
        self.assertIsNone(_tc.resolve_tool_category("ruff S rules"))

    def test_unknown_name_resolves_to_none(self):
        self.assertIsNone(_tc.resolve_tool_category("definitely-not-a-real-tool"))
        self.assertIsNone(_tc.resolve_tool_category(""))
        self.assertIsNone(_tc.resolve_tool_category(None))


class TestPairsReachability(unittest.TestCase):
    """D-T7: every tool-token member of every pairs row resolves through
    `resolve_tool_category` -- the index first, then the defaults map --
    never through raw index membership, which is unsatisfiable against this
    table (the bare `ruff` row's first member)."""

    def test_every_tool_token_member_resolves(self):
        for row in _tc.REDUNDANT_VS_COMPLEMENTARY_PAIRS:
            rule_family = row.get("rule_family_members", ())
            for member in row["tools"]:
                if member in rule_family:
                    continue
                self.assertIsNotNone(
                    _tc.resolve_tool_category(member),
                    f"pairs row {row['tools']!r} member {member!r} does not "
                    "resolve",
                )

    def test_redundancy_and_supersession_rows_share_one_category(self):
        for row in _tc.REDUNDANT_VS_COMPLEMENTARY_PAIRS:
            if row["relationship"] not in ("redundant", "supersession"):
                continue
            rule_family = row.get("rule_family_members", ())
            tokens = [t for t in row["tools"] if t not in rule_family]
            categories = {_tc.resolve_tool_category(t) for t in tokens}
            self.assertEqual(
                len(categories),
                1,
                f"{row['relationship']} row {row['tools']!r} spans categories "
                f"{categories!r} -- a researched 'don't run both' can never fire",
            )

    def test_named_regression_tools_resolve_to_their_partners_category(self):
        # The exact four tools the cross-AI review's cycle 1 HIGH named as
        # reachable only through the pairs table or a cell's prose.
        pairs = {
            "staticcheck": "golangci-lint",
            "ts-prune": "knip",
            "cargo-audit": "cargo-deny",
            "semgrep": "eslint-plugin-security",
        }
        for tool_name, partner in pairs.items():
            self.assertEqual(
                _tc.resolve_tool_category(tool_name),
                _tc.resolve_tool_category(partner),
            )

    def test_cross_category_rows_are_expected_and_harmless(self):
        """Exactly two of today's ten rows resolve cross-category, and both
        are complementary -- the ruff/vulture row (bare `ruff`, deliberately
        not an index key) and the Java PMD/SpotBugs row (source-analysis vs
        bytecode-analysis, genuinely different categories). Pinned here so a
        future transcription that makes a REDUNDANCY row cross-category
        fails this instead of quietly producing advice that can never
        fire."""
        cross = []
        for row in _tc.REDUNDANT_VS_COMPLEMENTARY_PAIRS:
            rule_family = row.get("rule_family_members", ())
            tokens = [t for t in row["tools"] if t not in rule_family]
            if len(tokens) != 2:
                continue
            categories = {_tc.resolve_tool_category(t) for t in tokens}
            if len(categories) > 1:
                cross.append(row)
        self.assertEqual(len(cross), 2, [r["tools"] for r in cross])
        for row in cross:
            self.assertIn(row["relationship"], ("complementary", "overlapping"))
        self.assertIn(("ruff", "vulture"), [r["tools"] for r in cross])

    def test_import_guard_raises_on_unresolvable_member(self):
        row = {
            "ecosystem": "fixture",
            "tools": ("definitely-not-a-real-tool", "vulture"),
            "rule_family_members": (),
            "relationship": "complementary",
            "reason": "fixture row for the non-vacuity guard",
        }
        with self.assertRaises(ImportError):
            _tc._validate_pairs_reachability((row,))

    def test_import_guard_raises_on_cross_category_redundancy(self):
        row = {
            "ecosystem": "fixture",
            "tools": ("mypy", "vulture"),
            "rule_family_members": (),
            "relationship": "redundant",
            "reason": "fixture row for the non-vacuity guard",
        }
        with self.assertRaises(ImportError):
            _tc._validate_pairs_reachability((row,))


class TestFindPairRelationship(unittest.TestCase):
    def test_order_insensitive_both_directions(self):
        forward = _tc.find_pair_relationship("knip", "ts-prune")
        backward = _tc.find_pair_relationship("ts-prune", "knip")
        self.assertIsNotNone(forward)
        self.assertEqual(forward, backward)
        self.assertEqual(forward["relationship"], "supersession")

    def test_unresearched_pair_returns_none(self):
        self.assertIsNone(_tc.find_pair_relationship("mypy", "jscpd"))


class TestAmbiguousToolDefaults(unittest.TestCase):
    def test_exactly_one_cited_entry(self):
        self.assertEqual(_tc.AMBIGUOUS_TOOL_DEFAULTS, {"ruff": "linting"})


class TestOutOfTaxonomyGroups(unittest.TestCase):
    def test_each_group_carries_markers_and_a_reason(self):
        for group_name, group in _tc.OUT_OF_TAXONOMY_GROUPS.items():
            self.assertTrue(group["markers"], group_name)
            self.assertTrue(group["reason"], group_name)


class TestMakefileCategoryAliasDriftGuard(unittest.TestCase):
    """Pins `MAKEFILE_CATEGORY_ALIAS`'s five mapped values against the
    sibling `ai-kit-project-rules-makefile` skill's real `RESEARCH_
    CATEGORIES` tuple, read via `ast` from `tooling_payload.py` (never
    imported)."""

    def _read_research_categories(self):
        with open(
            _MAKEFILE_SKILL_TOOLING_PAYLOAD_PATH, encoding="utf-8"
        ) as handle:
            tree = ast.parse(handle.read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name) or target.id != "RESEARCH_CATEGORIES":
                continue
            if isinstance(node.value, ast.Tuple):
                return tuple(
                    elt.value for elt in node.value.elts if isinstance(elt, ast.Constant)
                )
        raise AssertionError("RESEARCH_CATEGORIES literal not found")

    def test_alias_table_has_six_keys_one_none_five_matching_sibling(self):
        self.assertEqual(set(_tc.MAKEFILE_CATEGORY_ALIAS), set(_tc.TAXONOMY_CATEGORIES))
        self.assertIsNone(_tc.MAKEFILE_CATEGORY_ALIAS["type-checking"])
        none_count = sum(1 for v in _tc.MAKEFILE_CATEGORY_ALIAS.values() if v is None)
        self.assertEqual(none_count, 1)

    def test_mapped_values_match_sibling_research_categories(self):
        research_categories = self._read_research_categories()
        mapped = {v for v in _tc.MAKEFILE_CATEGORY_ALIAS.values() if v is not None}
        self.assertEqual(
            mapped,
            set(research_categories),
            "MAKEFILE_CATEGORY_ALIAS drifted from ai-kit-project-rules-"
            "makefile's RESEARCH_CATEGORIES -- the two skills would stop "
            "describing the same categories.",
        )

    def test_drift_guard_is_non_vacuous(self):
        """Edit one mapped value, confirm exactly this class's second test
        fails, then revert -- proving the guard actually compares rather
        than trivially passing."""
        original = _tc.MAKEFILE_CATEGORY_ALIAS["formatting"]
        _tc.MAKEFILE_CATEGORY_ALIAS["formatting"] = "not-a-real-category"
        try:
            research_categories = self._read_research_categories()
            mapped = {v for v in _tc.MAKEFILE_CATEGORY_ALIAS.values() if v is not None}
            self.assertNotEqual(mapped, set(research_categories))
        finally:
            _tc.MAKEFILE_CATEGORY_ALIAS["formatting"] = original


from ai_kit_rules_common import yaml_text
from ai_kit_rules_common.precommit_parse import _strip_yaml_quotes as _precommit_strip_yaml_quotes


class TestYamlTextStripQuotes(unittest.TestCase):
    """D-D8's `strip_yaml_quotes` -- the exact rule
    `precommit_parse._strip_yaml_quotes` already implements."""

    def test_bare_value_unchanged(self):
        self.assertEqual(yaml_text.strip_yaml_quotes("bare"), "bare")

    def test_single_quoted_value_stripped(self):
        self.assertEqual(yaml_text.strip_yaml_quotes("'quoted'"), "quoted")

    def test_double_quoted_value_stripped(self):
        self.assertEqual(yaml_text.strip_yaml_quotes('"quoted"'), "quoted")

    def test_mismatched_quotes_unchanged(self):
        self.assertEqual(yaml_text.strip_yaml_quotes("'mismatched\""), "'mismatched\"")

    def test_one_character_value_unchanged(self):
        self.assertEqual(yaml_text.strip_yaml_quotes("'"), "'")

    def test_empty_value_unchanged(self):
        self.assertEqual(yaml_text.strip_yaml_quotes(""), "")


class TestYamlTextIndentAndStructural(unittest.TestCase):
    """D-D8's `line_indent`/`is_structural_line` -- a raw whitespace-
    character count, never a tab-to-column conversion, and blank/
    comment classification at both indent 0 and depth."""

    def test_zero_indent(self):
        self.assertEqual(yaml_text.line_indent("services:"), 0)

    def test_nested_indent(self):
        self.assertEqual(yaml_text.line_indent("    image: a"), 4)

    def test_tab_led_line_counts_the_tab_as_one_character(self):
        self.assertEqual(yaml_text.line_indent("\timage: a"), 1)

    def test_blank_line_is_not_structural(self):
        self.assertFalse(yaml_text.is_structural_line("   "))

    def test_comment_at_indent_zero_is_not_structural(self):
        self.assertFalse(yaml_text.is_structural_line("# comment"))

    def test_comment_at_depth_is_not_structural(self):
        self.assertFalse(yaml_text.is_structural_line("    # nested comment"))

    def test_real_content_is_structural(self):
        self.assertTrue(yaml_text.is_structural_line("  image: a"))


class TestYamlTextQuoteStripDriftGuard(unittest.TestCase):
    """`yaml_text.strip_yaml_quotes` and `precommit_parse.
    _strip_yaml_quotes` implement the SAME rule by deliberate choice --
    Phase 11 closed `precommit_parse.py`, so it is not repointed at the
    new shared module here; `criticality.py`'s docstring already
    records this exact arrangement for `rules.py`. This guard, over a
    branch-covering input set, is what keeps the two implementations
    from silently disagreeing."""

    _INPUTS = (
        "bare",
        "'single'",
        '"double"',
        "'mismatched\"",
        "\"mismatched'",
        "'",
        '"',
        "",
        "a",
        "''",
        '""',
        "'unterminated",
    )

    def test_both_implementations_agree_on_every_input(self):
        for value in self._INPUTS:
            with self.subTest(value=value):
                self.assertEqual(
                    yaml_text.strip_yaml_quotes(value),
                    _precommit_strip_yaml_quotes(value),
                )


import subprocess

from ai_kit_rules_common.stack_detect import detect_stacks


def _stack_marker_dir(*filenames):
    """A fresh temp dir containing an empty file per name in `filenames` --
    `detect_stacks` reads a marker's mere PRESENCE, never its contents."""
    d = tempfile.mkdtemp()
    for name in filenames:
        with open(os.path.join(d, name), "w", encoding="utf-8") as handle:
            handle.write("x")
    return d


class TestHotReloadCatalogKeySet(unittest.TestCase):
    """13-CONTEXT D-05 / plan 13-03 D-D16: `HOT_RELOAD_TOOLS`'s keys must be
    exactly the stack names `detect_stacks` can return -- DERIVED here by
    running `detect_stacks` over temp dirs, never re-typed (T-13-18): a
    hand-typed set would pass forever while the two modules drift, and the
    symptom of that drift is silence, not an error."""

    def test_key_set_matches_detect_stacks_derived_markers(self):
        marker_files = ("go.mod", "pyproject.toml", "package.json", "pom.xml", "Cargo.toml")
        found: set[str] = set()
        for name in marker_files:
            found |= detect_stacks(_stack_marker_dir(name))
        self.assertEqual(set(_tc.HOT_RELOAD_TOOLS), found)

    def test_all_marker_tuples_are_lowercase_nonempty_strings(self):
        for stack, markers in _tc.HOT_RELOAD_TOOLS.items():
            self.assertIsInstance(markers, tuple, stack)
            for marker in markers:
                self.assertEqual(marker, marker.lower().strip(), marker)
                self.assertTrue(marker)


class TestResolveHotReloadStackScoping(unittest.TestCase):
    def test_recognized_command_resolves_for_its_own_stack_only(self):
        self.assertTrue(_tc.resolve_hot_reload("vite --host 0.0.0.0", {"node"}))
        self.assertIsNone(_tc.resolve_hot_reload("vite --host 0.0.0.0", {"python"}))
        self.assertTrue(_tc.resolve_hot_reload("flask run --debug", {"python"}))
        self.assertIsNone(_tc.resolve_hot_reload("flask run --debug", {"node"}))

    def test_bare_reload_flag_resolves_for_python(self):
        self.assertTrue(_tc.resolve_hot_reload("uvicorn app:app --reload", {"python"}))

    def test_token_boundary_both_directions(self):
        self.assertIsNone(_tc.resolve_hot_reload("serve invited users", {"node"}))
        self.assertIsNone(_tc.resolve_hot_reload("airflow scheduler", {"go"}))
        self.assertTrue(_tc.resolve_hot_reload("air -c .air.toml", {"go"}))

    def test_production_shaped_command_resolves_to_nothing_for_every_stack(self):
        for stack in _tc.HOT_RELOAD_TOOLS:
            with self.subTest(stack=stack):
                self.assertIsNone(_tc.resolve_hot_reload("gunicorn app:app", {stack}))

    def test_empty_stack_set_resolves_to_nothing(self):
        self.assertIsNone(_tc.resolve_hot_reload("vite", set()))


class TestResolveHotReloadSelectionOrder(unittest.TestCase):
    """D-D16's total order: (1) longest marker, (2) tie -> earliest position
    in its own stack's tuple, (3) still tied across stacks -> alphabetically
    first stack name."""

    def test_clause_one_longest_marker_wins(self):
        result = _tc.resolve_hot_reload("webpack-dev-server --watch src", {"node"})
        self.assertEqual(result, "webpack-dev-server")

    def test_clause_two_tie_on_length_earliest_position_wins(self):
        node_tuple = _tc.HOT_RELOAD_TOOLS["node"]
        self.assertIn("nodemon", node_tuple)
        self.assertIn("--watch", node_tuple)
        self.assertEqual(len("nodemon"), len("--watch"), "seeded tie assumption broke")
        self.assertLess(node_tuple.index("nodemon"), node_tuple.index("--watch"))
        result = _tc.resolve_hot_reload("nodemon --watch src index.js", {"node"})
        self.assertEqual(result, "nodemon")

    def test_clause_three_cross_process_determinism(self):
        """`stacks` arrives as a SET whose iteration order varies BETWEEN
        processes but not within one -- an in-process repeat cannot detect
        this class of non-determinism, so this drives six real subprocesses
        with differing `PYTHONHASHSEED` values."""
        script = (
            "import sys\n"
            "sys.path.insert(0, 'skills/_shared')\n"
            "from ai_kit_rules_common.tool_catalog import resolve_hot_reload as R\n"
            "print(R('nodemon --watch src index.js', {'node', 'python'}))\n"
        )
        d = tempfile.mkdtemp()
        path = os.path.join(d, "probe.py")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(script)
        outputs = set()
        for seed in range(6):
            env = dict(os.environ, PYTHONHASHSEED=str(seed))
            result = subprocess.run(
                [sys.executable, path],
                capture_output=True,
                text=True,
                check=True,
                cwd=os.getcwd(),
                env=env,
            )
            outputs.add(result.stdout.strip())
        self.assertEqual(outputs, {"nodemon"})


class TestHotReloadNotInTaxonomy(unittest.TestCase):
    """The taxonomy-corruption risk (T-13-17) stated as a test, not only as
    a comment: no hot-reload marker may be answerable by `resolve_tool_
    category`, and none may be a key of `TOOL_CATEGORY_INDEX`."""

    def test_no_marker_in_index_or_resolvable_by_resolve_tool_category(self):
        for markers in _tc.HOT_RELOAD_TOOLS.values():
            for marker in markers:
                with self.subTest(marker=marker):
                    self.assertNotIn(marker, _tc.TOOL_CATEGORY_INDEX)
                    self.assertIsNone(_tc.resolve_tool_category(marker))


class TestHotReloadCatalogAdditive(unittest.TestCase):
    """The shared catalog edit is additive (T-13-17): existing baseline
    cells, the derived index, and both import-time guards behave exactly
    as before -- proven here and by the precommit sibling's suite passing
    unchanged."""

    def test_pre_existing_catalog_facts_unchanged(self):
        self.assertEqual(_tc.BASELINE_STACKS["python"]["linting"], ("ruff check",))
        self.assertEqual(_tc.BASELINE_STACKS["node"]["duplicate-code"], ("jscpd",))
        self.assertEqual(_tc.resolve_tool_category("ruff"), "linting")
        self.assertEqual(_tc.resolve_tool_category("staticcheck"), "linting")

    def test_hot_reload_gaps_and_prefixes_are_tuples(self):
        self.assertIsInstance(_tc.HOT_RELOAD_BASELINE_GAPS, tuple)
        self.assertIsInstance(_tc.SCRIPT_INDIRECTION_PREFIXES, tuple)
        self.assertTrue(_tc.SCRIPT_INDIRECTION_PREFIXES)


class TestHotReloadPerStackMarkerPairs(unittest.TestCase):
    """Plan 13-03 Task 3(b): the marker-LEVEL pairs that belong at the
    shared catalog layer -- for each stack, one command that resolves and
    one production-shaped command that does not -- complementing
    `TestResolveHotReloadStackScoping`'s node/python-only cases with every
    stack in the mapping, driven from `HOT_RELOAD_TOOLS`'s own keys rather
    than hand-listed."""

    def test_first_baseline_marker_resolves_for_its_own_stack(self):
        for stack, markers in _tc.HOT_RELOAD_TOOLS.items():
            if not markers:
                continue
            with self.subTest(stack=stack):
                self.assertEqual(_tc.resolve_hot_reload(markers[0], {stack}), markers[0])

    def test_production_shaped_command_does_not_resolve_for_any_stack(self):
        for stack in _tc.HOT_RELOAD_TOOLS:
            with self.subTest(stack=stack):
                self.assertIsNone(_tc.resolve_hot_reload("run-the-production-build", {stack}))


if __name__ == "__main__":
    unittest.main()
