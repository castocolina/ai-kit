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
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-agents-md-checker"),
)

from ai_kit_agents_md_checker import (
    cli,
    makefile_checker,
    rule_checker,
    rules,
    stack_cache,
    tool_presence,
)

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MAKEFILE_PATH = os.path.join(_REPO, "Makefile")
_PRECOMMIT_PATH = os.path.join(_REPO, ".pre-commit-config.yaml")
_PYPROJECT_PATH = os.path.join(_REPO, "pyproject.toml")
_CLI_PY_CANDIDATE = "skills/ai-kit-agents-md-checker/ai_kit_agents_md_checker/cli.py"


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def fake_bin(root, names, body):
    """Write executable sh stubs named `names` under `root`."""
    os.makedirs(root, exist_ok=True)
    for name in names:
        path = os.path.join(root, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
        os.chmod(path, 0o755)
    return root


def scoped_env(bin_dir, home):
    """Env whose PATH is exactly `bin_dir` and whose XDG dirs sit under `home`."""
    return {
        "PATH": bin_dir,
        "HOME": home,
        "XDG_CONFIG_HOME": os.path.join(home, ".config"),
        "XDG_DATA_HOME": os.path.join(home, ".local", "share"),
        "XDG_CACHE_HOME": os.path.join(home, ".cache"),
    }


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


class TestParseMakefileTargets(unittest.TestCase):
    def test_ignores_phony_and_recipe_lines(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                ".PHONY: test\ntest:\n\techo hi\n",
            )
            targets = makefile_checker.parse_makefile_targets(
                os.path.join(repo, "Makefile")
            )
            self.assertEqual(targets, {"test"})

    def test_missing_file_returns_empty_set(self):
        self.assertEqual(
            makefile_checker.parse_makefile_targets("/nonexistent/Makefile"), set()
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
            hooks = makefile_checker.parse_precommit_hooks(path)
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
            makefile_checker.parse_precommit_hooks("/nonexistent/.pre-commit-config.yaml"),
            {},
        )


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
    def test_absent_fresh_stale(self):
        with tempfile.TemporaryDirectory() as cache_root:
            self.assertEqual(
                stack_cache.read_stack_cache("python", cache_root=cache_root)["state"],
                "absent",
            )
            stack_cache.write_stack_cache(
                "python", {"setup-env": "uv venv"}, cache_root=cache_root
            )
            self.assertEqual(
                stack_cache.read_stack_cache("python", cache_root=cache_root)["state"],
                "fresh",
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
            self.assertEqual(
                stack_cache.read_stack_cache("python", cache_root=cache_root)["state"],
                "stale",
            )


class TestCachePathValidation(unittest.TestCase):
    def test_valid_identifiers_succeed(self):
        stack_cache.cache_path("python")
        stack_cache.cache_path("node-lts")

    def test_invalid_identifiers_raise(self):
        for bad in ("../../etc/passwd", "/etc/passwd", "a/b", ""):
            with self.assertRaises(ValueError):
                stack_cache.cache_path(bad)


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


_MAKEFILE_RUFF_HOOK_TEXT = """\
repos:
  - repo: local
    hooks:
      - id: ruff
        entry: uv run ruff check
        language: system
"""


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
    def test_check_validate_order_never_adds_a_finding(self):
        self.assertIsNone(makefile_checker.check_validate_order("ignored", True))
        self.assertIsNone(makefile_checker.check_validate_order("ignored", False))

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
            finding = makefile_checker.check_precommit_prepush_split(repo)
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
            finding = makefile_checker.check_precommit_prepush_split(repo)
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
            finding = makefile_checker.check_precommit_prepush_split(repo)
            self.assertIsNone(finding)

    def test_categories_never_contain_removed_entries(self):
        self.assertNotIn("validate-order", stack_cache.RESEARCH_CATEGORIES)
        self.assertNotIn("precommit-vs-prepush-split", stack_cache.RESEARCH_CATEGORIES)


class TestToolPresence(unittest.TestCase):
    def test_empty_path_and_repo_all_false(self):
        with tempfile.TemporaryDirectory() as bin_dir, tempfile.TemporaryDirectory() as repo:
            env = scoped_env(bin_dir, repo)
            result = tool_presence.check_tool_presence(
                search_path=env["PATH"], repo_root=repo
            )
            expected = {
                "rtk": False,
                "modern-cli": False,
                "modern-cli:rg": False,
                "modern-cli:bat": False,
                "modern-cli:sd": False,
                "modern-cli:fd": False,
                "modern-cli:eza": False,
                "codegraph": False,
                "graphify": False,
                "gsd": False,
            }
            for key, value in expected.items():
                self.assertEqual(result[key], value, key)

    def test_partial_tools_and_codegraph_dir(self):
        with tempfile.TemporaryDirectory() as bin_dir, tempfile.TemporaryDirectory() as repo:
            fake_bin(bin_dir, ["rg", "bat"], "#!/bin/sh\nexit 0\n")
            os.makedirs(os.path.join(repo, ".codegraph"))
            env = scoped_env(bin_dir, repo)
            result = tool_presence.check_tool_presence(
                search_path=env["PATH"], repo_root=repo
            )
            self.assertTrue(result["modern-cli"])
            self.assertTrue(result["modern-cli:rg"])
            self.assertTrue(result["modern-cli:bat"])
            self.assertFalse(result["modern-cli:sd"])
            self.assertFalse(result["modern-cli:fd"])
            self.assertFalse(result["modern-cli:eza"])
            self.assertTrue(result["codegraph"])


class TestRuleChecker(unittest.TestCase):
    @staticmethod
    def _find(findings, rule_id):
        for finding in findings:
            if finding["id"] == rule_id:
                return finding
        return None

    def _always_false_presence(self):
        presence = {"rtk": False, "modern-cli": False, "codegraph": False,
                    "graphify": False, "gsd": False}
        presence.update(
            {f"modern-cli:{t}": False for t in tool_presence.MODERN_CLI_TOOLS}
        )
        return presence

    def test_r01_flat_classification(self):
        presence = self._always_false_presence()

        missing = rule_checker.check_workflow_rules(
            "nothing related here", presence, include_present=True
        )
        self.assertEqual(self._find(missing, "R01")["status"], "missing")

        present = rule_checker.check_workflow_rules(
            "All docs are english-only and this is non-negotiable.",
            presence,
            include_present=True,
        )
        self.assertEqual(self._find(present, "R01")["status"], "present")

        near = rule_checker.check_workflow_rules(
            "We write docs in english only.", presence, include_present=True
        )
        self.assertEqual(self._find(near, "R01")["status"], "near_miss")

    def test_tool_presence_condition_not_applicable(self):
        presence = {"rtk": False}
        findings = rule_checker.check_workflow_rules(
            "no rtk mention here", presence, include_present=True
        )
        self.assertEqual(self._find(findings, "R05")["status"], "not_applicable")

    def test_r02_included_by_signals_not_category(self):
        presence = self._always_false_presence()
        findings = rule_checker.check_workflow_rules(
            "no relevant text", presence, include_present=True
        )
        self.assertIsNotNone(self._find(findings, "R02"))

    def test_r04_grouped_signals_require_every_group(self):
        presence = self._always_false_presence()
        presence["gsd"] = True

        review_only = rule_checker.check_workflow_rules(
            "we run cross-ai review on every plan", presence, include_present=True
        )
        self.assertEqual(self._find(review_only, "R04")["status"], "near_miss")

        all_groups = rule_checker.check_workflow_rules(
            "we run cross-ai review, cheap-model execution, and "
            "path-agnostic command generation",
            presence,
            include_present=True,
        )
        self.assertEqual(self._find(all_groups, "R04")["status"], "present")

        none_present = rule_checker.check_workflow_rules(
            "no relevant text here", presence, include_present=True
        )
        self.assertEqual(self._find(none_present, "R04")["status"], "missing")

    def test_r06_tool_scoped_groups_only_require_installed_tools(self):
        presence = self._always_false_presence()
        presence.update(
            {"modern-cli": True, "modern-cli:rg": True, "modern-cli:bat": True}
        )

        rg_only = rule_checker.check_workflow_rules(
            "use ripgrep instead of grep", presence, include_present=True
        )
        r06 = self._find(rg_only, "R06")
        self.assertEqual(r06["status"], "near_miss")
        self.assertEqual(r06["missing_tools"], ["bat"])

        both = rule_checker.check_workflow_rules(
            "use ripgrep and bat instead of grep/cat", presence, include_present=True
        )
        r06 = self._find(both, "R06")
        self.assertEqual(r06["status"], "present")
        self.assertEqual(r06["missing_tools"], [])

        no_tools = self._always_false_presence()
        findings = rule_checker.check_workflow_rules(
            "use ripgrep and bat instead of grep/cat", no_tools, include_present=True
        )
        self.assertEqual(self._find(findings, "R06")["status"], "not_applicable")

    def test_matched_signals_field(self):
        presence = self._always_false_presence()
        findings = rule_checker.check_workflow_rules(
            "we write docs in english only", presence, include_present=True
        )
        r01 = self._find(findings, "R01")
        self.assertEqual(r01["status"], "near_miss")
        self.assertTrue(r01["matched_signals"])
        self.assertTrue(set(r01["matched_signals"]) <= set(rules.RULES[0]["signals"]))


class TestCliCheck(unittest.TestCase):
    def test_check_combines_and_orders_by_criticality(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "AGENTS.md"),
                "Some filler text with no relevant rule content elsewhere.",
            )
            result = cli.check(repo)
            ids = [f["id"] for f in result["workflow"]]
            self.assertIn("R01", ids)
            self.assertIn("R17", ids)
            self.assertLess(ids.index("R01"), ids.index("R17"))

    def test_resolve_instruction_text_falls_back_to_claude_md(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "CLAUDE.md"),
                "All docs are english-only; this is non-negotiable.",
            )
            result = cli.check(repo)
            ids = [f["id"] for f in result["workflow"]]
            self.assertNotIn("R01", ids)

    def test_resolve_instruction_text_follows_one_hop_links(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "AGENTS.md"),
                "See [testing](docs/testing.md) for conventions.",
            )
            _write(
                os.path.join(repo, "docs", "testing.md"),
                "Every commit is one coherent logical commit, after a "
                "compaction pass.",
            )
            result = cli.check(repo)
            ids = [f["id"] for f in result["workflow"]]
            self.assertNotIn("R03", ids)

    def test_resolve_instruction_text_dangling_link_no_crash(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "AGENTS.md"),
                "See [testing](docs/missing.md) for conventions.",
            )
            result = cli.check(repo)
            ids = [f["id"] for f in result["workflow"]]
            self.assertIn("R03", ids)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unsupported")
    def test_resolve_instruction_text_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as repo, tempfile.TemporaryDirectory() as outside:
            _write(
                os.path.join(outside, "secret.md"),
                "Every commit is one coherent logical commit, after a "
                "compaction pass.",
            )
            _write(
                os.path.join(repo, "AGENTS.md"),
                "See [testing](docs/escape.md) for conventions.",
            )
            docs_dir = os.path.join(repo, "docs")
            os.makedirs(docs_dir, exist_ok=True)
            try:
                os.symlink(
                    os.path.join(outside, "secret.md"),
                    os.path.join(docs_dir, "escape.md"),
                )
            except (OSError, NotImplementedError):
                self.skipTest("symlinks not supported on this platform")
            result = cli.check(repo)
            ids = [f["id"] for f in result["workflow"]]
            self.assertIn("R03", ids)


class TestGateRegistration(unittest.TestCase):
    def test_makefile_registers_module_and_package(self):
        with open(_MAKEFILE_PATH, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("tests.test_ai_kit_agents_md_checker", text)
        self.assertIn("skills/ai-kit-agents-md-checker/", text)

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
        self.assertIn("tests.test_ai_kit_agents_md_checker", match.group(1))

    def test_pyright_include_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        include = data["tool"]["pyright"]["include"]
        self.assertIn("skills/ai-kit-agents-md-checker", include)

    def test_vulture_paths_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        paths = data["tool"]["vulture"]["paths"]
        self.assertIn("skills/ai-kit-agents-md-checker", paths)


if __name__ == "__main__":
    unittest.main()
