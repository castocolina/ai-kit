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
    remediation,
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


class TestRemediation(unittest.TestCase):
    def test_missing_and_near_miss_auto_apply(self):
        report = {
            "workflow": [
                {
                    "id": "R01",
                    "status": "missing",
                    "criticality": 1,
                    "summary": "R01 summary",
                    "matched_signals": [],
                },
                {
                    "id": "R17",
                    "status": "near_miss",
                    "criticality": 3,
                    "summary": "R17 summary",
                    "matched_signals": ["concise"],
                },
            ],
            "makefile": [],
        }
        result = remediation.build_remediation(report)
        self.assertIsInstance(result, dict)
        ids = [entry["id"] for entry in result["remediate"]]
        self.assertEqual(ids, ["R01", "R17"])
        by_id = {entry["id"]: entry for entry in result["remediate"]}
        self.assertIs(by_id["R01"]["auto_apply"], True)
        self.assertIs(by_id["R17"]["auto_apply"], False)
        self.assertEqual(result["blocked"], [])

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
        result = remediation.build_remediation(report)
        ids_in_order = [entry["id"] for entry in result["remediate"]]
        self.assertEqual(ids_in_order, ["setup-env", "R09"])

    def test_matched_signals_carried_forward(self):
        report = {
            "workflow": [
                {
                    "id": "R17",
                    "status": "near_miss",
                    "criticality": 3,
                    "summary": "R17 summary",
                    "matched_signals": ["concise", "narrative"],
                },
            ],
            "makefile": [],
        }
        result = remediation.build_remediation(report)
        self.assertEqual(
            result["remediate"][0]["matched_signals"], ["concise", "narrative"]
        )

    def test_present_but_recommended_structural_finding_in_remediate(self):
        report = {
            "workflow": [],
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
        result = remediation.build_remediation(report)
        self.assertEqual(len(result["remediate"]), 1)
        self.assertEqual(result["remediate"][0]["id"], "validate")
        self.assertTrue(result["remediate"][0]["auto_apply"])
        self.assertEqual(result["blocked"], [])

    def test_blocked_preserves_stacks(self):
        report = {
            "workflow": [],
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
        result = remediation.build_remediation(report)
        self.assertEqual(result["remediate"], [])
        self.assertEqual(len(result["blocked"]), 1)
        self.assertEqual(result["blocked"][0]["id"], "formatter")
        self.assertEqual(result["blocked"][0]["stacks"], ["go", "python"])

    def test_returns_dict_never_bare_list(self):
        result = remediation.build_remediation({"workflow": [], "makefile": []})
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result.keys()), {"remediate", "blocked"})


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
