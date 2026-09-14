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


class TestValidateOrderAndPrecommitPrepushSplit(unittest.TestCase):
    # THREE-WAY split of 9d672b9's TestValidateOrderAndPrecommitPrepushSplit:
    #   1. splitter cases -> tests/test_ai_kit_rules_common.py's
    #      TestPrecommitPrepushSplit (the splitter moved to
    #      skills/_shared/ai_kit_rules_common/precommit_parse.py)
    #   2. the ordering-stub case below -> HERE. This is the checker's
    #      actual post-Task-1 behavior (a permanent no-op); plan 10-02
    #      rewrites this coverage in place once the stub becomes the
    #      advisory heuristic.
    #   3. the schema-shape case below -> HERE too (cycle-3 review finding:
    #      this method is neither a splitter case nor an ordering-stub
    #      case, it's an independent schema-shape assertion the original
    #      two-way split left unassigned).
    def test_check_validate_order_never_adds_a_finding(self):
        self.assertIsNone(makefile_checker.check_validate_order("ignored", True))
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
        self.assertIn("skills/ai-kit-project-rules-makefile/", text)

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
        self.assertIn("tests.test_ai_kit_project_rules_makefile", match.group(1))

    def test_pyright_include_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        include = data["tool"]["pyright"]["include"]
        self.assertIn("skills/ai-kit-project-rules-makefile", include)

    def test_vulture_paths_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        paths = data["tool"]["vulture"]["paths"]
        self.assertIn("skills/ai-kit-project-rules-makefile", paths)


if __name__ == "__main__":
    unittest.main()
