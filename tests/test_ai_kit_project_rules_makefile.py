import functools
import json
import os
import re
import sys
import tempfile
import tomllib
import unittest
from datetime import UTC, datetime, timedelta
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-makefile"),
)

from ai_kit_project_rules_makefile import cli, makefile_checker, stack_cache

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MAKEFILE_PATH = os.path.join(_REPO, "Makefile")
_PRECOMMIT_PATH = os.path.join(_REPO, ".pre-commit-config.yaml")
_PYPROJECT_PATH = os.path.join(_REPO, "pyproject.toml")
_CLI_PY_CANDIDATE = (
    "skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/cli.py"
)


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def _precommit_hook_block(hook_id):
    with open(_PRECOMMIT_PATH, encoding="utf-8") as handle:
        text = handle.read()
    needle = f"- id: {hook_id}"
    start = text.find(needle)
    if start < 0:
        raise AssertionError(f"hook id {hook_id!r} not found")
    rest = text[start:]
    nxt = rest.find("\n      - id:", len(needle))
    return rest if nxt < 0 else rest[:nxt]


def _precommit_hook_files_regex(hook_id):
    block = _precommit_hook_block(hook_id)
    match = re.search(r"^\s*files:\s*(\S+)\s*$", block, re.MULTILINE)
    if match is None:
        raise AssertionError(f"no files: value for hook {hook_id!r}")
    return match.group(1).strip().strip("'\"")


def _tool_roots_cover(rel_dir: str, roots: list[str]) -> bool:
    sample = f"{rel_dir.rstrip('/')}/module.py"
    return any(sample == root or sample.startswith(f"{root}/") for root in roots)



_FIXTURE_MAKEFILE_BASIC = """\
INSTALL_SH := tools/install.sh

.PHONY: install reconfigure uninstall doctor check test lint dev validate

install:
\tbash $(INSTALL_SH)

dev:
\tuv sync
\tuv run pre-commit install

reconfigure:
\tbash $(INSTALL_SH) reconfigure

uninstall:
\tbash $(INSTALL_SH) uninstall

doctor:
\tbash $(INSTALL_SH) --doctor

check:
\tbash $(INSTALL_SH) --check

test:
\tpython3 -m unittest tests.test_setup
\tbash tests/test_install.sh

lint:
\tshellcheck $(INSTALL_SH) tests/test_install.sh

validate:
\tuv run pre-commit run --all-files
"""

_FIXTURE_PRECOMMIT_BASIC = """\
default_install_hook_types: [pre-commit]
repos:
  - repo: local
    hooks:
      - id: "vulture"
        name: vulture
        entry: uv run vulture
        language: system
        pass_filenames: false
      - id: external-hook
        name: external hook (no inline entry)
        language: system
"""

_MAKEFILE_RUFF_HOOK_TEXT = """\
repos:
  - repo: local
    hooks:
      - id: ruff
        entry: uv run ruff check
        language: system
"""


class TestCheckMakefileShapeTracer(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.repo = self._tmpdir.name
        self.cache_root = os.path.join(self.repo, "_cache")
        _write(os.path.join(self.repo, "requirements.txt"), "")
        _write(os.path.join(self.repo, "Makefile"), _FIXTURE_MAKEFILE_BASIC)
        _write(
            os.path.join(self.repo, ".pre-commit-config.yaml"), _FIXTURE_PRECOMMIT_BASIC
        )

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_arch_test_and_hook_gaps_named_individually(self):
        with mock.patch.object(stack_cache, "CACHE_ROOT", self.cache_root):
            findings = makefile_checker.check_makefile_shape(self.repo)
        by_target = {f["target"]: f for f in findings if "target" in f}

        self.assertIn("arch-test", by_target)
        self.assertTrue(by_target["arch-test"]["needs_research"])
        self.assertIsNotNone(by_target["arch-test"]["criticality"])
        self.assertIsNotNone(by_target["arch-test"]["summary"])

        self.assertIn("vulture", by_target)
        self.assertFalse(by_target["vulture"]["needs_research"])
        self.assertIn("uv run vulture", by_target["vulture"]["recommendation"])

        self.assertIn("external-hook", by_target)
        self.assertIn("pre-commit run", by_target["external-hook"]["recommendation"])
        self.assertIn("external-hook", by_target["external-hook"]["recommendation"])

    def test_fresh_cache_resolves_static_target(self):
        stack_cache.write_stack_cache(
            "python", {"setup-env": "uv venv && uv sync"}, cache_root=self.cache_root
        )
        findings = makefile_checker.check_makefile_shape(
            self.repo,
            get_tooling=functools.partial(
                stack_cache.get_stack_tooling, cache_root=self.cache_root
            ),
        )
        by_target = {f["target"]: f for f in findings if "target" in f}
        self.assertIn("setup-env", by_target)
        self.assertFalse(by_target["setup-env"]["needs_research"])
        self.assertIsNotNone(by_target["setup-env"]["recommendation"])


class TestStackCacheStates(unittest.TestCase):
    # Re-homed from 9d672b9's TestStackCacheStates. The generic
    # absent/fresh/stale transitions and the corrupted-JSON /
    # non-object-payload degrade-not-crash behavior are already covered by
    # tests/test_ai_kit_rules_common.py's TestStackCache (calling the
    # shared engine directly) -- dropped here as already-covered rather
    # than duplicated. What's kept is genuinely about THIS skill's own
    # binding: its default cache root resolves under its own namespace,
    # and its wrappers thread that default root through when `cache_root`
    # is omitted.
    def test_default_cache_root_uses_own_namespace(self):
        self.assertIn("project-rules-makefile", stack_cache.CACHE_ROOT)

    def test_wrappers_thread_default_root_when_cache_root_omitted(self):
        with (
            tempfile.TemporaryDirectory() as cache_root,
            mock.patch.object(stack_cache, "CACHE_ROOT", cache_root),
        ):
            stack_cache.write_stack_cache("python", {"setup-env": "uv venv"})
            result = stack_cache.read_stack_cache("python")
        self.assertEqual(result["state"], "fresh")


class TestCachePathValidation(unittest.TestCase):
    # Re-homed from 9d672b9's TestCachePathValidation. The
    # invalid-identifier-raises behavior is already covered by
    # tests/test_ai_kit_rules_common.py's
    # TestStackCache.test_invalid_stack_identifier_raises (calling the
    # shared `cache_path` directly) -- dropped here as already-covered.
    # Kept: that THIS skill's wrapper resolves a valid identifier under its
    # own default namespace without error.
    def test_valid_identifiers_succeed_via_default_namespace(self):
        stack_cache.cache_path("python")
        stack_cache.cache_path("node-lts")


class TestStaleCacheNotTrusted(unittest.TestCase):
    def test_stale_entry_never_trusted(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "requirements.txt"), "")
            _write(os.path.join(repo, "Makefile"), _FIXTURE_MAKEFILE_BASIC)
            cache_root = os.path.join(repo, "_cache")
            stack_cache.write_stack_cache(
                "python", {"setup-env": "uv venv && uv sync"}, cache_root=cache_root
            )
            path = stack_cache.cache_path("python", cache_root=cache_root)
            with open(path, encoding="utf-8") as handle:
                payload = json.load(handle)
            backdated = datetime.now(UTC) - timedelta(
                days=stack_cache.STALE_AFTER_DAYS + 1
            )
            payload["cached_at"] = backdated.isoformat()
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)

            findings = makefile_checker.check_makefile_shape(
                repo,
                get_tooling=functools.partial(
                    stack_cache.get_stack_tooling, cache_root=cache_root
                ),
            )
            by_target = {f["target"]: f for f in findings if "target" in f}
            self.assertTrue(by_target["setup-env"]["needs_research"])
            self.assertIsNone(by_target["setup-env"]["recommendation"])


class TestMultiStackResolution(unittest.TestCase):
    def _setup_repo(self, repo):
        _write(os.path.join(repo, "requirements.txt"), "")
        _write(os.path.join(repo, "package.json"), "{}")
        _write(os.path.join(repo, "Makefile"), _FIXTURE_MAKEFILE_BASIC)

    def test_one_stack_fresh_other_missing(self):
        with tempfile.TemporaryDirectory() as repo:
            self._setup_repo(repo)
            cache_root = os.path.join(repo, "_cache")
            stack_cache.write_stack_cache(
                "python", {"setup-env": "uv venv && uv sync"}, cache_root=cache_root
            )
            findings = makefile_checker.check_makefile_shape(
                repo,
                get_tooling=functools.partial(
                    stack_cache.get_stack_tooling, cache_root=cache_root
                ),
            )
            by_target = {f["target"]: f for f in findings if "target" in f}
            finding = by_target["setup-env"]
            self.assertTrue(finding["needs_research"])
            self.assertEqual(finding["stacks"], ["node"])

    def test_all_stacks_fresh(self):
        with tempfile.TemporaryDirectory() as repo:
            self._setup_repo(repo)
            cache_root = os.path.join(repo, "_cache")
            stack_cache.write_stack_cache(
                "python", {"setup-env": "uv venv && uv sync"}, cache_root=cache_root
            )
            stack_cache.write_stack_cache(
                "node", {"setup-env": "npm ci"}, cache_root=cache_root
            )
            findings = makefile_checker.check_makefile_shape(
                repo,
                get_tooling=functools.partial(
                    stack_cache.get_stack_tooling, cache_root=cache_root
                ),
            )
            by_target = {f["target"]: f for f in findings if "target" in f}
            finding = by_target["setup-env"]
            self.assertFalse(finding["needs_research"])
            self.assertIn("node", finding["recommendation"])
            self.assertIn("python", finding["recommendation"])

    def test_neither_stack_fresh(self):
        with tempfile.TemporaryDirectory() as repo:
            self._setup_repo(repo)
            cache_root = os.path.join(repo, "_cache")
            findings = makefile_checker.check_makefile_shape(
                repo,
                get_tooling=functools.partial(
                    stack_cache.get_stack_tooling, cache_root=cache_root
                ),
            )
            by_target = {f["target"]: f for f in findings if "target" in f}
            finding = by_target["setup-env"]
            self.assertTrue(finding["needs_research"])
            self.assertEqual(finding["stacks"], ["node", "python"])


class TestToolingCategoryGaps(unittest.TestCase):
    def test_category_gap_reported_when_uncovered(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "requirements.txt"), "")
            _write(os.path.join(repo, "Makefile"), _FIXTURE_MAKEFILE_BASIC)
            cache_root = os.path.join(repo, "_cache")
            stack_cache.write_stack_cache(
                "python", {"security-scanner": "bandit -r ."}, cache_root=cache_root
            )
            findings = makefile_checker.check_makefile_shape(
                repo,
                get_tooling=functools.partial(
                    stack_cache.get_stack_tooling, cache_root=cache_root
                ),
            )
            by_category = {f["category"]: f for f in findings if "category" in f}
            self.assertIn("security-scanner", by_category)
            self.assertFalse(by_category["security-scanner"]["needs_research"])

    def test_category_gap_skipped_when_already_covered(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "requirements.txt"), "")
            _write(os.path.join(repo, "Makefile"), _FIXTURE_MAKEFILE_BASIC)
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                "repos:\n"
                "  - repo: local\n"
                "    hooks:\n"
                "      - id: bandit\n"
                "        entry: uv run bandit -r .\n"
                "        language: system\n",
            )
            cache_root = os.path.join(repo, "_cache")
            findings = makefile_checker.check_makefile_shape(
                repo,
                get_tooling=functools.partial(
                    stack_cache.get_stack_tooling, cache_root=cache_root
                ),
            )
            categories = {f["category"] for f in findings if "category" in f}
            self.assertNotIn("security-scanner", categories)


class TestValidateChainAndAlias(unittest.TestCase):
    def test_incomplete_chain_and_alias_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                ".PHONY: validate test test-unit ruff\n\n"
                "validate:\n\techo validating\n\n"
                "test:\n\techo testing\n\n"
                "test-unit:\n\techo unit\n\n"
                "ruff:\n\tuv run ruff check\n",
            )
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"), _MAKEFILE_RUFF_HOOK_TEXT
            )
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {
                f.get("issue"): f for f in findings if f.get("present") is True
            }
            self.assertIn("chain_incomplete", issues)
            self.assertEqual(issues["chain_incomplete"]["missing_chain_members"], ["ruff"])
            self.assertIsNotNone(issues["chain_incomplete"]["recommendation"])
            self.assertFalse(issues["chain_incomplete"]["needs_research"])

            self.assertIn("not_aliased", issues)
            self.assertIsNotNone(issues["not_aliased"]["recommendation"])
            self.assertFalse(issues["not_aliased"]["needs_research"])

    def test_complete_chain_and_alias_via_recipe_reference(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                ".PHONY: validate test test-unit ruff\n\n"
                "validate:\n\t$(MAKE) ruff\n\techo validating\n\n"
                "test:\n\t$(MAKE) test-unit\n\techo testing\n\n"
                "test-unit:\n\techo unit\n\n"
                "ruff:\n\tuv run ruff check\n",
            )
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"), _MAKEFILE_RUFF_HOOK_TEXT
            )
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings if f.get("present") is True}
            self.assertNotIn("chain_incomplete", issues)
            self.assertNotIn("not_aliased", issues)


class TestValidateAliasFamily(unittest.TestCase):
    # ROADMAP Phase 10 Success Criterion 2: for every tooling category with a
    # concrete Makefile target present, the checker requires the matching
    # `validate-<short-name>` alias target, and separately flags `validate`
    # when an alias that DOES exist is not chained into it.

    def test_no_concrete_target_requires_no_alias(self):
        # Negative fixture: a category with no concrete target present
        # requires nothing, even though every alias is absent.
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "validate:\n\techo v\n")
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings}
            self.assertNotIn("alias_missing", issues)
            self.assertNotIn("alias_chain_incomplete", issues)

    def test_alias_missing_when_concrete_target_present(self):
        # Triggering fixture: a security-category concrete target with no
        # `validate-security` target -> one finding naming the category and
        # the concrete target(s) that made it required.
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "validate:\n\techo v\n\nsecurity-scan:\n\techo s\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            missing = [f for f in findings if f.get("issue") == "alias_missing"]
            self.assertEqual(len(missing), 1)
            finding = missing[0]
            self.assertEqual(finding["target"], "validate-security")
            self.assertFalse(finding["present"])
            self.assertEqual(finding["alias_category"], "security-scanner")
            self.assertIn("security-scan", finding["triggering_targets"])
            self.assertFalse(finding["needs_research"])
            self.assertIsNotNone(finding["recommendation"])
            self.assertIsNotNone(finding["summary"])
            self.assertIsNotNone(finding["criticality"])

    def test_alias_present_but_unchained_flags_validate(self):
        # Triggering fixture: `validate-security` present but `validate`
        # neither lists it as a prerequisite nor references it in its
        # recipe -> one finding against `validate` naming it among the
        # alias members it fails to chain.
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "validate:\n\techo v\n\nsecurity-scan:\n\techo s\n\n"
                "validate-security:\n\techo vs\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            agg = [f for f in findings if f.get("issue") == "alias_chain_incomplete"]
            self.assertEqual(len(agg), 1)
            finding = agg[0]
            self.assertEqual(finding["target"], "validate")
            self.assertTrue(finding["present"])
            self.assertIn("validate-security", finding["missing_alias_members"])
            self.assertFalse(finding["needs_research"])
            self.assertIsNotNone(finding["recommendation"])
            # The alias-missing finding must NOT also fire for the same gap.
            self.assertNotIn(
                "alias_missing", {f.get("issue") for f in findings}
            )

    def test_fully_satisfied_produces_no_finding(self):
        # Negative fixture: concrete target, alias, AND the alias chained
        # into `validate` -> no finding from this check at all.
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "validate: validate-security\n\techo v\n\nsecurity-scan:\n\techo s\n\n"
                "validate-security:\n\techo vs\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings}
            self.assertNotIn("alias_missing", issues)
            self.assertNotIn("alias_chain_incomplete", issues)

    def test_validate_prefixed_target_never_counts_as_concrete_trigger(self):
        # A target whose name begins with `validate` never counts as the
        # concrete target that triggers a category's requirement --
        # otherwise `validate-security` would make itself required, and
        # `validate` would trigger every category.
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "validate:\n\techo v\n\nvalidate-security:\n\techo vs\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings}
            self.assertNotIn("alias_missing", issues)
            self.assertNotIn("alias_chain_incomplete", issues)

    def test_validate_absent_flags_missing_alias_but_not_chain(self):
        # `validate` absent entirely -> no alias-chain finding (the
        # inherited static-target check already reports the bigger gap);
        # the per-category missing-alias findings still apply.
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "security-scan:\n\techo s\n")
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings}
            self.assertIn("alias_missing", issues)
            self.assertNotIn("alias_chain_incomplete", issues)

    def test_aggregate_and_inherited_chain_incomplete_coexist_with_distinct_issues(
        self,
    ):
        # Two different gaps about `validate` -- the inherited
        # `chain_incomplete` (a hook-derived member not chained) and this
        # check's `alias_chain_incomplete` (an existing alias not chained)
        # -- can legitimately co-occur, distinguishable by `issue`.
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "validate:\n\techo v\n\nruff:\n\techo r\n\n"
                "security-scan:\n\techo s\n\nvalidate-security:\n\techo vs\n",
            )
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"), _MAKEFILE_RUFF_HOOK_TEXT
            )
            findings = makefile_checker.check_makefile_shape(repo)
            validate_findings = [f for f in findings if f.get("target") == "validate"]
            self.assertEqual(len(validate_findings), 2)
            issues = {f["issue"] for f in validate_findings}
            self.assertEqual(issues, {"chain_incomplete", "alias_chain_incomplete"})

    def test_alias_map_pinned_roadmap_names(self):
        # ROADMAP SC2 pins these three names literally; not the executor's
        # to rename.
        self.assertEqual(
            makefile_checker.CATEGORY_ALIAS_MAP["security-scanner"], "validate-security"
        )
        self.assertEqual(
            makefile_checker.CATEGORY_ALIAS_MAP["duplicate-code-detector"],
            "validate-duplicate",
        )
        self.assertEqual(
            makefile_checker.CATEGORY_ALIAS_MAP["dead-code-detector"], "validate-dead"
        )


class TestHelpReachability(unittest.TestCase):
    # ROADMAP Phase 10 Success Criterion 3.

    def test_default_goal_naming_existing_target_not_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                ".DEFAULT_GOAL := build\n\nbuild:\n\techo b\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings}
            self.assertNotIn("no_reachable_help_path", issues)

    def test_stemless_catchall_not_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"), "%:\n\techo unknown\n\nbuild:\n\techo b\n"
            )
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings}
            self.assertNotIn("no_reachable_help_path", issues)

    def test_stemmed_suffix_rule_is_not_a_catchall_and_is_flagged(self):
        # Discriminating negative case: a suffix rule tells Make how to
        # build one file class from another and does nothing for an
        # unknown-target invocation.
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "%.o: %.c\n\techo compile\n\nbuild:\n\techo b\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            reach = [f for f in findings if f.get("issue") == "no_reachable_help_path"]
            self.assertEqual(len(reach), 1)

    def test_neither_mechanism_is_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "build:\n\techo b\n")
            findings = makefile_checker.check_makefile_shape(repo)
            reach = [f for f in findings if f.get("issue") == "no_reachable_help_path"]
            self.assertEqual(len(reach), 1)
            self.assertEqual(reach[0]["target"], "help")

    def test_default_goal_naming_undefined_target_is_flagged_with_distinct_summary(
        self,
    ):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                ".DEFAULT_GOAL := nonexistent\n\nbuild:\n\techo b\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            reach = [f for f in findings if f.get("issue") == "no_reachable_help_path"]
            self.assertEqual(len(reach), 1)
            self.assertIn("nonexistent", reach[0]["summary"])

            with tempfile.TemporaryDirectory() as repo2:
                _write(os.path.join(repo2, "Makefile"), "build:\n\techo b\n")
                findings2 = makefile_checker.check_makefile_shape(repo2)
                reach2 = next(
                    f for f in findings2 if f.get("issue") == "no_reachable_help_path"
                )
            # Same issue id, different summary sentence.
            self.assertEqual(reach[0]["issue"], reach2["issue"])
            self.assertNotEqual(reach[0]["summary"], reach2["summary"])


class TestRecipeLengthCap(unittest.TestCase):
    # ROADMAP Phase 10 Success Criterion 4.

    def test_four_line_recipe_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "build:\n\techo 1\n\techo 2\n\techo 3\n\techo 4\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            over = [f for f in findings if f.get("issue") == "recipe_too_long"]
            self.assertEqual(len(over), 1)
            self.assertEqual(over[0]["target"], "build")
            self.assertEqual(over[0]["line_count"], 4)
            self.assertIsNotNone(over[0]["recommendation"])
            self.assertIn("script", over[0]["recommendation"])

    def test_exactly_three_lines_not_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"), "build:\n\techo 1\n\techo 2\n\techo 3\n"
            )
            findings = makefile_checker.check_makefile_shape(repo)
            over = [f for f in findings if f.get("issue") == "recipe_too_long"]
            self.assertEqual(over, [])

    def test_blank_and_comment_padded_three_commands_not_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "build:\n\techo 1\n\n\t# a comment\n\techo 2\n\n\t# another\n\techo 3\n\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            over = [f for f in findings if f.get("issue") == "recipe_too_long"]
            self.assertEqual(over, [])

    def test_help_target_exempt_from_cap(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "help:\n\techo 1\n\techo 2\n\techo 3\n\techo 4\n\techo 5\n\techo 6\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            over = [f for f in findings if f.get("issue") == "recipe_too_long"]
            self.assertEqual(over, [])

    def test_default_goal_named_target_exempt_from_cap(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                ".DEFAULT_GOAL := usage\n\n"
                "usage:\n\techo 1\n\techo 2\n\techo 3\n\techo 4\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            over = [f for f in findings if f.get("issue") == "recipe_too_long"]
            self.assertEqual(over, [])

    def test_one_finding_per_over_long_target(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "build:\n\techo 1\n\techo 2\n\techo 3\n\techo 4\n\n"
                "deploy:\n\techo 1\n\techo 2\n\techo 3\n\techo 4\n\techo 5\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            over = {f["target"]: f for f in findings if f.get("issue") == "recipe_too_long"}
            self.assertEqual(set(over), {"build", "deploy"})
            self.assertEqual(over["build"]["line_count"], 4)
            self.assertEqual(over["deploy"]["line_count"], 5)


class TestWiringViaPrerequisites(unittest.TestCase):
    def test_validate_chain_via_prerequisites(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                ".PHONY: validate test test-unit ruff\n\n"
                "validate: ruff\n\techo validating\n\n"
                "test:\n\techo testing\n\n"
                "test-unit:\n\techo unit\n\n"
                "ruff:\n\tuv run ruff check\n",
            )
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"), _MAKEFILE_RUFF_HOOK_TEXT
            )
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings if f.get("present") is True}
            self.assertNotIn("chain_incomplete", issues)

    def test_alias_via_prerequisite(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                ".PHONY: validate test test-unit ruff\n\n"
                "validate:\n\t$(MAKE) ruff\n\techo validating\n\n"
                "test: test-unit\n\techo testing\n\n"
                "test-unit:\n\techo unit\n\n"
                "ruff:\n\tuv run ruff check\n",
            )
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"), _MAKEFILE_RUFF_HOOK_TEXT
            )
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings if f.get("present") is True}
            self.assertNotIn("not_aliased", issues)


class TestWiredCheckWordBoundary(unittest.TestCase):
    # Re-homed from 9d672b9's TestWiredCheckWordBoundary -- ONLY the two
    # cases that assert through check_makefile_shape. The case that
    # exercises the recipe-reference helper's token semantics directly
    # lives in tests/test_ai_kit_rules_common.py's
    # TestRecipeMentionsTargetWordBoundary (this class's two-way split).
    def test_raw_substring_never_satisfies_membership(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                ".PHONY: validate lint\n\n"
                "validate:\n\tuv run pylint src/\n\techo validating\n\n"
                "lint:\n\tuv run pylint src/\n",
            )
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                "repos:\n"
                "  - repo: local\n"
                "    hooks:\n"
                "      - id: lint\n"
                "        entry: uv run pylint src/\n"
                "        language: system\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            chain = next(
                f for f in findings if f.get("issue") == "chain_incomplete"
            )
            self.assertIn("lint", chain["missing_chain_members"])

    def test_standalone_token_satisfies_membership(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                ".PHONY: validate lint\n\n"
                "validate:\n\t$(MAKE) lint\n\techo validating\n\n"
                "lint:\n\tuv run pylint src/\n",
            )
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                "repos:\n"
                "  - repo: local\n"
                "    hooks:\n"
                "      - id: lint\n"
                "        entry: uv run pylint src/\n"
                "        language: system\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings if f.get("present") is True}
            self.assertNotIn("chain_incomplete", issues)


class TestNoCrashAndNoStack(unittest.TestCase):
    def test_check_missing_makefile_and_precommit_no_crash(self):
        with tempfile.TemporaryDirectory() as repo:
            result = cli.check(repo)
            names = {f["target"] for f in result["makefile"] if "target" in f}
            for target in stack_cache.REQUIRED_STATIC_TARGETS:
                self.assertIn(target, names)

    def test_no_detected_stack_stays_needs_research(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), _FIXTURE_MAKEFILE_BASIC)
            findings = makefile_checker.check_makefile_shape(repo)
            by_target = {f["target"]: f for f in findings if "target" in f}
            for target in (
                "setup-env",
                "test-unit",
                "test-integration",
                "e2e-test",
                "arch-test",
            ):
                self.assertTrue(by_target[target]["needs_research"])
                self.assertEqual(by_target[target]["stacks"], [])
                self.assertIn("no stack", by_target[target]["summary"].lower())


def _make_scripts(repo, count, subdir="scripts"):
    for i in range(count):
        _write(os.path.join(repo, subdir, f"s{i}.sh"), "#!/bin/sh\n")


class TestDockerBuildBeforeUp(unittest.TestCase):
    # ROADMAP Phase 10 Success Criterion 5 (first clause).

    def test_no_build_wiring_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\tdocker compose up\n")
            findings = makefile_checker.check_makefile_shape(repo)
            flagged = [f for f in findings if f.get("issue") == "docker_build_not_wired"]
            self.assertEqual(len(flagged), 1)
            self.assertEqual(flagged[0]["target"], "docker-up")
            self.assertEqual(flagged[0]["criticality"], 2)

    def test_build_shaped_prerequisite_not_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "docker-build:\n\tdocker build .\n\n"
                "docker-up: docker-build\n\tdocker compose up\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings}
            self.assertNotIn("docker_build_not_wired", issues)

    def test_recipe_invocation_of_existing_build_target_not_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "docker-build:\n\tdocker build .\n\n"
                "docker-up:\n\t$(MAKE) docker-build\n\tdocker compose up\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings}
            self.assertNotIn("docker_build_not_wired", issues)

    def test_recipe_mentioning_undefined_build_target_is_not_satisfaction(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "docker-up:\n\t$(MAKE) docker-build\n\tdocker compose up\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            flagged = [f for f in findings if f.get("issue") == "docker_build_not_wired"]
            self.assertEqual(len(flagged), 1)

    def test_inline_compose_flag_only_is_flagged_pinned_behavior(self):
        # This is the case the rule is written down to settle: NO
        # "standalone build token" clause. The finding's summary must name
        # what was checked, never claim the recipe performs no build.
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"), "docker-up:\n\tdocker compose up --build\n"
            )
            findings = makefile_checker.check_makefile_shape(repo)
            flagged = [f for f in findings if f.get("issue") == "docker_build_not_wired"]
            self.assertEqual(len(flagged), 1)
            summary = flagged[0]["summary"].lower()
            self.assertIn("prerequisite", summary)
            # Must name what was checked, never claim the recipe itself
            # performs no build -- on this fixture that stronger claim
            # would be false (it DOES build, via the inline --build flag).
            self.assertNotIn("never build", summary)
            self.assertNotIn("performs no build", summary)
            self.assertNotIn("does not build", summary)

    def test_no_up_shaped_target_no_finding(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "build:\n\techo b\n")
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings}
            self.assertNotIn("docker_build_not_wired", issues)

    def test_multi_segment_up_shaped_satisfied_by_multi_segment_build_prereq(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "docker-events-build:\n\tdocker build .\n\n"
                "docker-events-up: docker-events-build\n\tdocker compose up\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings}
            self.assertNotIn("docker_build_not_wired", issues)

    def test_shape_membership_up_and_build(self):
        up_re = makefile_checker._DOCKER_UP_SHAPE_RE
        build_re = makefile_checker._DOCKER_BUILD_SHAPE_RE
        for name in ("docker-up", "docker-events-up"):
            self.assertIsNotNone(up_re.match(name), name)
        for name in ("docker-build", "docker-events-build"):
            self.assertIsNotNone(build_re.match(name), name)
        for name in ("events-up", "up", "docker-up-legacy", "docker_up"):
            self.assertIsNone(up_re.match(name), name)
        for name in ("events-build", "build", "docker-build-legacy"):
            self.assertIsNone(build_re.match(name), name)


class TestShellcheckThreshold(unittest.TestCase):
    # ROADMAP Phase 10 Success Criterion 5 (second clause).

    def test_five_scripts_no_target_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _make_scripts(repo, 5)
            _write(os.path.join(repo, "Makefile"), "build:\n\techo b\n")
            findings = makefile_checker.check_makefile_shape(repo)
            missing = [
                f for f in findings if f.get("issue") == "shellcheck_target_missing"
            ]
            self.assertEqual(len(missing), 1)
            self.assertFalse(missing[0]["present"])
            self.assertIn("ai-kit-project-rules-cicd", missing[0]["summary"])

    def test_four_scripts_no_finding(self):
        with tempfile.TemporaryDirectory() as repo:
            _make_scripts(repo, 4)
            _write(os.path.join(repo, "Makefile"), "build:\n\techo b\n")
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings}
            self.assertNotIn("shellcheck_target_missing", issues)
            self.assertNotIn("shellcheck_target_not_wired", issues)

    def test_five_scripts_target_present_but_not_wired_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _make_scripts(repo, 5)
            _write(
                os.path.join(repo, "Makefile"),
                "shellcheck:\n\tshellcheck scripts/*.sh\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            not_wired = [
                f for f in findings if f.get("issue") == "shellcheck_target_not_wired"
            ]
            self.assertEqual(len(not_wired), 1)
            self.assertTrue(not_wired[0]["present"])
            self.assertIn("ai-kit-project-rules-cicd", not_wired[0]["summary"])
            missing = [
                f for f in findings if f.get("issue") == "shellcheck_target_missing"
            ]
            self.assertEqual(missing, [])

    def test_five_scripts_target_and_hook_present_no_finding(self):
        with tempfile.TemporaryDirectory() as repo:
            _make_scripts(repo, 5)
            _write(
                os.path.join(repo, "Makefile"),
                "shellcheck:\n\tshellcheck scripts/*.sh\n",
            )
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                "repos:\n  - repo: local\n    hooks:\n"
                "      - id: shellcheck\n        entry: shellcheck scripts/*.sh\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings}
            self.assertNotIn("shellcheck_target_missing", issues)
            self.assertNotIn("shellcheck_target_not_wired", issues)

    def test_pruned_directories_do_not_count_toward_threshold(self):
        # Below-threshold pair proving pruning actually happens: 4 visible
        # scripts plus 20 under pruned directories must stay silent, while
        # the identical tree with 5 visible scripts fires.
        with tempfile.TemporaryDirectory() as repo:
            _make_scripts(repo, 4, subdir="scripts")
            _make_scripts(repo, 10, subdir=".git")
            _make_scripts(repo, 10, subdir="node_modules")
            _write(os.path.join(repo, "Makefile"), "build:\n\techo b\n")
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings}
            self.assertNotIn("shellcheck_target_missing", issues)

        with tempfile.TemporaryDirectory() as repo2:
            _make_scripts(repo2, 5, subdir="scripts")
            _make_scripts(repo2, 10, subdir=".git")
            _make_scripts(repo2, 10, subdir="node_modules")
            _write(os.path.join(repo2, "Makefile"), "build:\n\techo b\n")
            findings2 = makefile_checker.check_makefile_shape(repo2)
            issues2 = {f.get("issue") for f in findings2}
            self.assertIn("shellcheck_target_missing", issues2)


class TestAdvisoryOrdering(unittest.TestCase):
    # ROADMAP Phase 10 Success Criterion 5 (third clause).

    def _repo_with_validate(self, repo, prereqs):
        target_blocks = "\n\n".join(f"{name}:\n\techo {name}\n" for name in prereqs)
        _write(
            os.path.join(repo, "Makefile"),
            ".DEFAULT_GOAL := help\n\nhelp:\n\techo h\n\n"
            + target_blocks
            + f"\n\nvalidate: {' '.join(prereqs)}\n\techo v\n",
        )
        hook_lines = "".join(
            f"      - id: {name}\n        entry: run {name}\n" for name in prereqs
        )
        _write(
            os.path.join(repo, ".pre-commit-config.yaml"),
            f"repos:\n  - repo: local\n    hooks:\n{hook_lines}",
        )

    def test_inverted_prereqs_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            self._repo_with_validate(repo, ["unittest", "ruff"])
            findings = makefile_checker.check_makefile_shape(repo)
            adv = [f for f in findings if f.get("issue") == "validate_order_advisory"]
            self.assertEqual(len(adv), 1)
            self.assertTrue(adv[0]["advisory"])
            self.assertEqual(adv[0]["criticality"], 4)
            self.assertIn(("unittest", "ruff"), adv[0]["inverted_pairs"])

    def test_correct_order_not_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            self._repo_with_validate(repo, ["ruff", "unittest"])
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings}
            self.assertNotIn("validate_order_advisory", issues)

    def test_unrecognized_name_skipped_never_forms_inversion(self):
        with tempfile.TemporaryDirectory() as repo:
            self._repo_with_validate(repo, ["zzz-unknown", "unittest"])
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings}
            self.assertNotIn("validate_order_advisory", issues)

    def test_one_finding_lists_all_inversions(self):
        with tempfile.TemporaryDirectory() as repo:
            self._repo_with_validate(repo, ["unittest", "mypy", "ruff"])
            findings = makefile_checker.check_makefile_shape(repo)
            adv = [f for f in findings if f.get("issue") == "validate_order_advisory"]
            self.assertEqual(len(adv), 1)
            self.assertGreaterEqual(len(adv[0]["inverted_pairs"]), 2)

    def test_speed_tier_pinned(self):
        self.assertIsNotNone(makefile_checker.speed_tier("unittest"))
        self.assertIsNotNone(makefile_checker.speed_tier("ruff"))
        unittest_tier = makefile_checker.speed_tier("unittest")
        ruff_tier = makefile_checker.speed_tier("ruff")
        assert unittest_tier is not None
        assert ruff_tier is not None
        self.assertGreater(unittest_tier, ruff_tier)
        self.assertEqual(
            makefile_checker.speed_tier("pytest"), makefile_checker.speed_tier("unittest")
        )
        self.assertEqual(
            makefile_checker.speed_tier("test"), makefile_checker.speed_tier("unittest")
        )
        self.assertIsNone(makefile_checker.speed_tier("zzz-not-a-real-tool"))

    def test_suppressed_when_chain_incomplete(self):
        # `validate`'s prerequisites ARE inverted (unittest before ruff),
        # but a third hook-derived member (`extra`) is not chained at all
        # -- the actionable chain finding is the one to act on, so the
        # advisory must stay silent.
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                ".DEFAULT_GOAL := help\n\nhelp:\n\techo h\n\n"
                "unittest:\n\techo u\n\nruff:\n\techo r\n\nextra:\n\techo e\n\n"
                "validate: unittest ruff\n\techo v\n",
            )
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                "repos:\n  - repo: local\n    hooks:\n"
                "      - id: unittest\n        entry: run unittest\n"
                "      - id: ruff\n        entry: run ruff\n"
                "      - id: extra\n        entry: run extra\n",
            )
            findings = makefile_checker.check_makefile_shape(repo)
            issues = {f.get("issue") for f in findings}
            self.assertIn("chain_incomplete", issues)
            self.assertNotIn("validate_order_advisory", issues)


class TestValidateOrderAndPrecommitPrepushSplit(unittest.TestCase):
    # THREE-WAY split of 9d672b9's TestValidateOrderAndPrecommitPrepushSplit:
    #   1. splitter cases -> tests/test_ai_kit_rules_common.py's
    #      TestPrecommitPrepushSplit (the splitter moved to
    #      skills/_shared/ai_kit_rules_common/precommit_parse.py)
    #   2. the ordering-stub case below -> HERE, REWRITTEN IN PLACE by plan
    #      10-02 Task 3 now that the stub is the real advisory heuristic.
    #      Detailed coverage of the heuristic itself lives in
    #      TestAdvisoryOrdering above; what's kept here is the narrow
    #      contract this class originally asserted -- the
    #      `chain_incomplete_found` flag stays load-bearing.
    #   3. the schema-shape case below -> HERE too (cycle-3 review finding:
    #      this method is neither a splitter case nor an ordering-stub
    #      case, it's an independent schema-shape assertion the original
    #      two-way split left unassigned).
    def test_check_validate_order_suppressed_by_chain_incomplete_flag(self):
        self.assertIsNone(makefile_checker.check_validate_order("ignored", True))

    def test_check_validate_order_returns_none_for_a_repo_with_no_inversion(self):
        self.assertIsNone(makefile_checker.check_validate_order("ignored", False))

    def test_categories_never_contain_removed_entries(self):
        self.assertNotIn("validate-order", stack_cache.RESEARCH_CATEGORIES)
        self.assertNotIn("precommit-vs-prepush-split", stack_cache.RESEARCH_CATEGORIES)


class TestCacheUpdateCLI(unittest.TestCase):
    def test_cache_update_round_trips_through_get_stack_tooling(self):
        with tempfile.TemporaryDirectory() as scratch:
            cache_root = os.path.join(scratch, "_cache")
            json_path = os.path.join(scratch, "tooling.json")
            payload = {
                "setup-env": (
                    "uv venv && uv sync (source: https://docs.astral.sh/uv/)"
                ),
                "formatter": (
                    "ruff format (source: https://docs.astral.sh/ruff/formatter/)"
                ),
            }
            _write(json_path, json.dumps(payload))
            rc = cli.main(
                ["cache-update", "python", json_path, "--cache-root", cache_root]
            )
            self.assertEqual(rc, 0)
            tooling, needs_research = stack_cache.get_stack_tooling(
                "python", cache_root=cache_root
            )
            self.assertFalse(needs_research)
            assert tooling is not None
            self.assertIn("setup-env", tooling)
            self.assertIn("formatter", tooling)


class TestCacheUpdateValidation(unittest.TestCase):
    def _run(self, scratch, stack, payload_text):
        cache_root = os.path.join(scratch, "_cache")
        json_path = os.path.join(scratch, "tooling.json")
        _write(json_path, payload_text)
        rc = cli.main(["cache-update", stack, json_path, "--cache-root", cache_root])
        return rc, cache_root

    def test_json_array_instead_of_object(self):
        with tempfile.TemporaryDirectory() as scratch:
            rc, cache_root = self._run(
                scratch, "python", json.dumps(["not", "an", "object"])
            )
            self.assertEqual(rc, 1)
            self.assertFalse(
                os.path.isfile(stack_cache.cache_path("python", cache_root=cache_root))
            )

    def test_unknown_key(self):
        with tempfile.TemporaryDirectory() as scratch:
            payload = {"not-a-real-key": "something (source: https://example.com)"}
            rc, cache_root = self._run(scratch, "python", json.dumps(payload))
            self.assertEqual(rc, 1)
            self.assertFalse(
                os.path.isfile(stack_cache.cache_path("python", cache_root=cache_root))
            )

    def test_non_string_value(self):
        with tempfile.TemporaryDirectory() as scratch:
            payload = {"setup-env": 123}
            rc, cache_root = self._run(scratch, "python", json.dumps(payload))
            self.assertEqual(rc, 1)
            self.assertFalse(
                os.path.isfile(stack_cache.cache_path("python", cache_root=cache_root))
            )

    def test_value_missing_source_substring_entirely(self):
        with tempfile.TemporaryDirectory() as scratch:
            payload = {"setup-env": "uv venv && uv sync"}
            rc, cache_root = self._run(scratch, "python", json.dumps(payload))
            self.assertEqual(rc, 1)
            self.assertFalse(
                os.path.isfile(stack_cache.cache_path("python", cache_root=cache_root))
            )

    def test_value_empty_citation(self):
        with tempfile.TemporaryDirectory() as scratch:
            payload = {"setup-env": "uv venv (source:)"}
            rc, cache_root = self._run(scratch, "python", json.dumps(payload))
            self.assertEqual(rc, 1)
            self.assertFalse(
                os.path.isfile(stack_cache.cache_path("python", cache_root=cache_root))
            )

    def test_value_whitespace_only_citation(self):
        with tempfile.TemporaryDirectory() as scratch:
            payload = {"setup-env": "uv venv (source: )"}
            rc, cache_root = self._run(scratch, "python", json.dumps(payload))
            self.assertEqual(rc, 1)
            self.assertFalse(
                os.path.isfile(stack_cache.cache_path("python", cache_root=cache_root))
            )

    def test_path_traversal_stack_rejected(self):
        with tempfile.TemporaryDirectory() as scratch:
            payload = {"setup-env": "uv venv (source: https://example.com)"}
            json_path = os.path.join(scratch, "tooling.json")
            _write(json_path, json.dumps(payload))
            cache_root = os.path.join(scratch, "_cache")

            def _snapshot():
                found = set()
                for root, _dirs, files in os.walk(scratch):
                    for name in files:
                        found.add(os.path.relpath(os.path.join(root, name), scratch))
                return found

            before = _snapshot()
            rc = cli.main(
                [
                    "cache-update",
                    "../../etc/passwd",
                    json_path,
                    "--cache-root",
                    cache_root,
                ]
            )
            self.assertEqual(rc, 1)
            self.assertFalse(os.path.isdir(cache_root))
            self.assertEqual(before, _snapshot())


class TestGateRegistration(unittest.TestCase):
    def test_makefile_registers_module_and_package(self):
        with open(_MAKEFILE_PATH, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("tests.test_ai_kit_project_rules_makefile", text)
        self.assertIsNotNone(re.search(r"^lint: shellcheck py-compile$", text, re.MULTILINE))

    def test_precommit_ruff_and_py_compile_match_package_path(self):
        for hook_id in ("ruff", "py-compile"):
            regex = _precommit_hook_files_regex(hook_id)
            self.assertIsNotNone(
                re.match(regex, _CLI_PY_CANDIDATE),
                f"{_CLI_PY_CANDIDATE} did not match {hook_id} files: {regex}",
            )
        entry_block = _precommit_hook_block("unittest")
        match = re.search(r"^\s*entry:\s*(.+)$", entry_block, re.MULTILINE)
        self.assertIsNotNone(match, "no entry: value for hook unittest")
        assert match is not None
        self.assertIn("tests.test_ai_kit_project_rules_makefile", match.group(1))

    def test_pyright_include_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        include = data["tool"]["pyright"]["include"]
        self.assertTrue(_tool_roots_cover("skills/ai-kit-project-rules-makefile", include), include)

    def test_vulture_paths_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        paths = data["tool"]["vulture"]["paths"]
        self.assertTrue(_tool_roots_cover("skills/ai-kit-project-rules-makefile", paths), paths)


if __name__ == "__main__":
    unittest.main()
