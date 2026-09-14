import json
import os
import re
import sys
import tempfile
import tomllib
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-precommit"),
)

from ai_kit_project_rules_precommit import (
    cli,
    config_read,
    parity_checker,
    precommit_checker,
    stack_cache,
    taxonomy_checker,
)

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MAKEFILE_PATH = os.path.join(_REPO, "Makefile")
_PRECOMMIT_PATH = os.path.join(_REPO, ".pre-commit-config.yaml")
_PYPROJECT_PATH = os.path.join(_REPO, "pyproject.toml")
_CLI_PY_CANDIDATE = (
    "skills/ai-kit-project-rules-precommit/ai_kit_project_rules_precommit/cli.py"
)


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


# Copied (not imported) from tests/test_ai_kit_project_rules_makefile.py, per
# Task 3's action: "Copy the sibling's two pre-commit hook helpers rather
# than importing them across test modules."
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


def _precommit_yaml(*hook_blocks):
    return "repos:\n  - repo: local\n    hooks:\n" + "".join(hook_blocks)


def _hook(hook_id, entry=None, extra=""):
    block = f"      - id: {hook_id}\n"
    if entry is not None:
        block += f"        entry: {entry}\n"
    block += extra
    return block


class TestDirectionAHookWithoutTarget(unittest.TestCase):
    """Direction A (hook -> target), paired."""

    def test_hook_without_matching_target_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "noop:\n\techo hi\n")
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(_hook("mypy", entry="mypy .")),
            )
            findings = parity_checker.check_parity(repo)
            hits = [f for f in findings if f.get("issue") == "hook_without_target"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["hook_id"], "mypy")

    def test_hook_with_matching_target_not_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "noop:\n\techo hi\n\nmypy:\n\techo type-check\n",
            )
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(_hook("mypy", entry="mypy .")),
            )
            findings = parity_checker.check_parity(repo)
            hits = [f for f in findings if f.get("issue") == "hook_without_target"]
            self.assertEqual(hits, [])


class TestDirectionBTargetWithoutHook(unittest.TestCase):
    """Direction B (tool-shaped target -> hook), paired."""

    _MAKEFILE = (
        "ruff:\n\tuv run pre-commit run ruff --all-files\n\n"
        "shellcheck:\n\tuv run pre-commit run shellcheck --all-files\n"
    )

    def test_tool_shaped_target_without_hook_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), self._MAKEFILE)
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(_hook("ruff", entry="ruff check .")),
            )
            findings = parity_checker.check_parity(repo)
            hits = [f for f in findings if f.get("issue") == "target_without_hook"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["target"], "shellcheck")

    def test_tool_shaped_target_with_hook_not_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), self._MAKEFILE)
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(
                    _hook("ruff", entry="ruff check ."),
                    _hook("shellcheck", entry="shellcheck"),
                ),
            )
            findings = parity_checker.check_parity(repo)
            hits = [f for f in findings if f.get("issue") == "target_without_hook"]
            self.assertEqual(hits, [])


class TestNormalization(unittest.TestCase):
    """D-P1 normalized name matching, paired."""

    def test_underscore_and_case_variants_matched(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "py-compile:\n\techo pc\n\nruff:\n\techo r\n",
            )
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(
                    _hook("py_compile", entry="python3 -m py_compile"),
                    _hook("Ruff", entry="ruff check ."),
                ),
            )
            findings = parity_checker.check_parity(repo)
            hits = [f for f in findings if f.get("issue") == "hook_without_target"]
            self.assertEqual(hits, [], "underscore/hyphen and case folding must match")

    def test_prefix_sharing_pair_not_matched(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "ruff-format:\n\techo rf\n")
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(_hook("ruff", entry="ruff check .")),
            )
            findings = parity_checker.check_parity(repo)
            hits = [f for f in findings if f.get("issue") == "hook_without_target"]
            self.assertEqual(
                len(hits),
                1,
                "'ruff' hook must not be satisfied by a 'ruff-format' target -- "
                "two different tools in two different taxonomy categories",
            )
            self.assertEqual(hits[0]["hook_id"], "ruff")


class TestShapePredicatePaired(unittest.TestCase):
    """D-P2 tool-shape predicate, paired -- asserted through the public
    `check_parity` function, not `classify_target_shape` alone, so the
    wiring is covered too."""

    def test_aggregate_target_not_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "validate: ruff-check\n\nruff-check:\n\tuv run pre-commit run ruff --all-files\n",
            )
            _write(os.path.join(repo, ".pre-commit-config.yaml"), _precommit_yaml())
            findings = parity_checker.check_parity(repo)
            names = {f.get("target") for f in findings if f.get("issue") == "target_without_hook"}
            self.assertNotIn(
                "validate",
                names,
                "a target with prerequisites and an empty recipe is an "
                "AGGREGATE and must never be tool-shaped",
            )

    def test_multiline_non_tool_recipe_not_flagged(self):
        """`sync-deps` is a deliberately generic project-verb name -- NOT a
        tool/analyzer name in the shared catalog -- so this stays a
        non-triggering case for the right reason (the >=2-real-line cap
        alone excludes it) even after plan 11-02 adds clause (iii) over
        real catalog tool names. Do not "improve" this into a realistic
        tool name; that would defeat the point of this fixture."""
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "sync-deps:\n\techo step-one\n\techo step-two\n\techo step-three\n",
            )
            _write(os.path.join(repo, ".pre-commit-config.yaml"), _precommit_yaml())
            findings = parity_checker.check_parity(repo)
            names = {f.get("target") for f in findings if f.get("issue") == "target_without_hook"}
            self.assertNotIn("sync-deps", names)

    def test_two_line_delegate_flagged_when_unmatched(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "mypy-check:\n\techo checking\n\tuv run pre-commit run mypy --all-files\n",
            )
            _write(os.path.join(repo, ".pre-commit-config.yaml"), _precommit_yaml())
            findings = parity_checker.check_parity(repo)
            hits = [f for f in findings if f.get("issue") == "target_without_hook"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["target"], "mypy-check")
            self.assertEqual(hits[0]["identity"], "mypy")
            self.assertEqual(hits[0]["clause"], "i")

    def test_two_line_delegate_not_flagged_when_matched(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "mypy-check:\n\techo checking\n\tuv run pre-commit run mypy --all-files\n",
            )
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(_hook("mypy", entry="mypy .")),
            )
            findings = parity_checker.check_parity(repo)
            hits = [f for f in findings if f.get("issue") == "target_without_hook"]
            self.assertEqual(hits, [])

    def test_runner_prefixed_delegate_flagged_when_unmatched(self):
        """Regression guard: a first-token or line-anchored matcher would
        silently drop this case -- the delegation token is preceded by a
        `poetry run` runner prefix, exactly the shape every one of this
        repository's own eight delegating recipes has."""
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "lint-py:\n\tpoetry run pre-commit run pylint --all-files\n",
            )
            _write(os.path.join(repo, ".pre-commit-config.yaml"), _precommit_yaml())
            findings = parity_checker.check_parity(repo)
            hits = [f for f in findings if f.get("issue") == "target_without_hook"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["target"], "lint-py")
            self.assertEqual(hits[0]["identity"], "pylint")

    def test_runner_prefixed_delegate_not_flagged_when_matched(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "lint-py:\n\tpoetry run pre-commit run pylint --all-files\n",
            )
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(_hook("pylint", entry="pylint .")),
            )
            findings = parity_checker.check_parity(repo)
            hits = [f for f in findings if f.get("issue") == "target_without_hook"]
            self.assertEqual(hits, [])

    def test_env_var_prefixed_delegate_considered(self):
        """A leading `env VAR=x` prefix is ignored generically too -- the
        clause never enumerates a fixed prefix list."""
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "sec-scan:\n\tenv FOO=bar pre-commit run bandit --all-files\n",
            )
            _write(os.path.join(repo, ".pre-commit-config.yaml"), _precommit_yaml())
            findings = parity_checker.check_parity(repo)
            hits = [f for f in findings if f.get("issue") == "target_without_hook"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["identity"], "bandit")

    def test_target_without_hook_recommendation_states_both_options(self):
        """D-P2b: every direction-B finding's recommendation is MANDATORY
        dual text -- add a hook, OR record the target as deliberately
        non-gating."""
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "mypy-check:\n\tuv run pre-commit run mypy --all-files\n",
            )
            _write(os.path.join(repo, ".pre-commit-config.yaml"), _precommit_yaml())
            findings = parity_checker.check_parity(repo)
            hits = [f for f in findings if f.get("issue") == "target_without_hook"]
            self.assertEqual(len(hits), 1)
            recommendation = hits[0]["recommendation"].lower()
            self.assertIn("add", recommendation)
            self.assertIn("deliberately non-gating", recommendation)


class TestStageSplitWired(unittest.TestCase):
    """Regression guard on Phase 10's ROADMAP SC1 amendment:
    `check_precommit_prepush_split` now has its caller here. Deleting the
    call in `precommit_checker.py` must make exactly this class's
    triggering test fail and nothing else in this module silently pass."""

    def test_slow_hook_missing_push_stage_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                "repos:\n"
                "  - repo: local\n"
                "    hooks:\n"
                "      - id: unittest\n"
                "        entry: python3 -m unittest tests.test_x\n",
            )
            findings = precommit_checker.check_precommit_rules(repo)
            hits = [f for f in findings if f.get("category") == "precommit-vs-prepush-split"]
            self.assertEqual(len(hits), 1)
            self.assertIn("unittest", hits[0]["slow_hooks_missing_push_stage"])

    def test_slow_hook_with_push_stage_produces_no_finding(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                "repos:\n"
                "  - repo: local\n"
                "    hooks:\n"
                "      - id: unittest\n"
                "        entry: python3 -m unittest tests.test_x\n"
                "        stages: [pre-push]\n",
            )
            findings = precommit_checker.check_precommit_rules(repo)
            hits = [f for f in findings if f.get("category") == "precommit-vs-prepush-split"]
            self.assertEqual(hits, [])


class TestClassifyPrecommitTools(unittest.TestCase):
    """Plan 11-02 Task 2: classification (ROADMAP SC2), each fixture its
    own class per the plan's paired-fixture instruction."""

    def test_sc2_fixture_four_tools_each_in_exactly_one_category(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "pyproject.toml"), '[project]\nname="x"\n')
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(
                    _hook("ruff", entry="ruff check ."),
                    _hook("mypy", entry="mypy ."),
                    _hook("bandit", entry="bandit -r ."),
                    _hook("eslint", entry="eslint ."),
                ),
            )
            result = taxonomy_checker.classify_precommit_tools(repo)
            self.assertEqual(result["unclassified"], [])
            placed = {}
            for category, hooks in result["taxonomy"].items():
                for hook in hooks:
                    placed.setdefault(hook["hook_id"], []).append(category)
            self.assertEqual(sorted(placed), ["bandit", "eslint", "mypy", "ruff"])
            self.assertTrue(all(len(v) == 1 for v in placed.values()))
            used_categories = {c for c, hs in result["taxonomy"].items() if hs}
            self.assertEqual(used_categories, {"linting", "type-checking", "security"})


class TestDisambiguationPair(unittest.TestCase):
    def test_formatter_subcommand_classifies_formatting(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(_hook("fmt-or-lint", entry="ruff format .")),
            )
            result = taxonomy_checker.classify_precommit_tools(repo)
            self.assertEqual(result["taxonomy"]["formatting"][0]["hook_id"], "fmt-or-lint")

    def test_lint_subcommand_classifies_linting(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(_hook("fmt-or-lint", entry="ruff check .")),
            )
            result = taxonomy_checker.classify_precommit_tools(repo)
            self.assertEqual(result["taxonomy"]["linting"][0]["hook_id"], "fmt-or-lint")


class TestTokenBoundaryPair(unittest.TestCase):
    def test_plugin_name_containing_shorter_tool_name_classifies_as_plugin(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(
                    _hook("eslint-security", entry="eslint-plugin-security .")
                ),
            )
            result = taxonomy_checker.classify_precommit_tools(repo)
            self.assertEqual(len(result["taxonomy"]["security"]), 1)
            self.assertEqual(result["taxonomy"]["linting"], [])
            self.assertEqual(
                result["taxonomy"]["security"][0]["matched"], "eslint-plugin-security"
            )


class TestInferredConfidencePair(unittest.TestCase):
    def test_bare_ambiguous_hook_id_is_inferred(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(_hook("ruff")),
            )
            result = taxonomy_checker.classify_precommit_tools(repo)
            hooks = result["taxonomy"]["linting"]
            self.assertEqual(len(hooks), 1)
            self.assertEqual(hooks[0]["confidence"], "inferred")

    def test_disambiguated_entry_is_baseline(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(_hook("ruff", entry="ruff check .")),
            )
            result = taxonomy_checker.classify_precommit_tools(repo)
            hooks = result["taxonomy"]["linting"]
            self.assertEqual(len(hooks), 1)
            self.assertEqual(hooks[0]["confidence"], "baseline")


class TestCacheConfidencePath(unittest.TestCase):
    # Invented, implausible name -- MUST be absent from the catalog index,
    # asserted below, so this fixture cannot silently rot into vacuity when
    # a later phase grows the catalog. Resolution order puts the index
    # first, so a real/already-indexed tool name would classify at
    # `baseline` before the cache is ever consulted.
    _CACHE_ONLY_TOOL = "zzz-imaginary-deadcode-detector"

    def test_invented_tool_name_is_absent_from_catalog_index(self):
        from ai_kit_rules_common.tool_catalog import TOOL_CATEGORY_INDEX

        self.assertNotIn(self._CACHE_ONLY_TOOL, TOOL_CATEGORY_INDEX)

    def test_warm_cache_classifies_at_cache_confidence_naming_the_stack(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "pyproject.toml"), '[project]\nname="x"\n')
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(
                    _hook(self._CACHE_ONLY_TOOL, entry=f"{self._CACHE_ONLY_TOOL} .")
                ),
            )
            cache_root = os.path.join(repo, "_cache")
            stack_cache.write_stack_cache(
                "python",
                {
                    "dead-code": (
                        f"{self._CACHE_ONLY_TOOL} "
                        "(source: https://example.com/imaginary-tool)"
                    )
                },
                cache_root=cache_root,
            )
            result = taxonomy_checker.classify_precommit_tools(repo, cache_root=cache_root)
            hooks = result["taxonomy"]["dead-code"]
            self.assertEqual(len(hooks), 1)
            self.assertEqual(hooks[0]["confidence"], "cache")
            self.assertEqual(hooks[0]["stack"], "python")
            self.assertFalse(hooks[0]["stale"])

    def test_cold_cache_is_unclassified(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "pyproject.toml"), '[project]\nname="x"\n')
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(
                    _hook(self._CACHE_ONLY_TOOL, entry=f"{self._CACHE_ONLY_TOOL} .")
                ),
            )
            cache_root = os.path.join(repo, "_cache")
            result = taxonomy_checker.classify_precommit_tools(repo, cache_root=cache_root)
            self.assertEqual(len(result["unclassified"]), 1)
            self.assertEqual(result["unclassified"][0]["hook_id"], self._CACHE_ONLY_TOOL)


class TestCacheStalenessFlag(unittest.TestCase):
    _CACHE_ONLY_TOOL = "zzz-imaginary-deadcode-detector"

    def test_stale_hit_is_still_cache_confidence_with_stale_flag_true(self):
        import json as _json
        from datetime import UTC, datetime, timedelta

        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "pyproject.toml"), '[project]\nname="x"\n')
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(
                    _hook(self._CACHE_ONLY_TOOL, entry=f"{self._CACHE_ONLY_TOOL} .")
                ),
            )
            cache_root = os.path.join(repo, "_cache")
            stack_cache.write_stack_cache(
                "python",
                {
                    "dead-code": (
                        f"{self._CACHE_ONLY_TOOL} "
                        "(source: https://example.com/imaginary-tool)"
                    )
                },
                cache_root=cache_root,
            )
            path = stack_cache.cache_path("python", cache_root=cache_root)
            with open(path, encoding="utf-8") as handle:
                payload = _json.load(handle)
            backdated = datetime.now(UTC) - timedelta(days=stack_cache.STALE_AFTER_DAYS + 1)
            payload["cached_at"] = backdated.isoformat()
            with open(path, "w", encoding="utf-8") as handle:
                _json.dump(payload, handle)

            result = taxonomy_checker.classify_precommit_tools(repo, cache_root=cache_root)
            hooks = result["taxonomy"]["dead-code"]
            self.assertEqual(len(hooks), 1)
            self.assertEqual(hooks[0]["confidence"], "cache")
            self.assertTrue(hooks[0]["stale"])


class TestOutOfTaxonomy(unittest.TestCase):
    def test_hygiene_and_test_runner_hooks_produce_no_finding(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(
                    _hook("trailing-whitespace"),
                    _hook("run-pytest", entry="pytest tests/"),
                ),
            )
            result = taxonomy_checker.classify_precommit_tools(repo)
            self.assertEqual(len(result["out_of_taxonomy"]), 2)
            self.assertEqual(result["unclassified"], [])
            findings = taxonomy_checker.build_unclassified_findings(result)
            self.assertEqual(findings, [])

    def test_genuinely_unknown_analysis_tool_is_unclassified_and_produces_a_finding(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(_hook("some-brand-new-analyzer")),
            )
            result = taxonomy_checker.classify_precommit_tools(repo)
            self.assertEqual(len(result["unclassified"]), 1)
            findings = taxonomy_checker.build_unclassified_findings(result)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["category"], "tool-taxonomy")
            self.assertEqual(findings[0]["issue"], "unclassified_tool")
            self.assertIsNone(findings[0]["recommendation"])
            self.assertTrue(findings[0]["needs_research"])


class TestOneOutcomeInvariant(unittest.TestCase):
    def test_every_hook_id_appears_exactly_once_across_all_outcomes(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(
                    _hook("ruff", entry="ruff check ."),
                    _hook("trailing-whitespace"),
                    _hook("some-brand-new-analyzer"),
                    _hook("mypy", entry="mypy ."),
                    _hook("run-pytest", entry="pytest tests/"),
                ),
            )
            result = taxonomy_checker.classify_precommit_tools(repo)
            seen = []
            for hooks in result["taxonomy"].values():
                seen.extend(h["hook_id"] for h in hooks)
            seen.extend(h["hook_id"] for h in result["out_of_taxonomy"])
            seen.extend(h["hook_id"] for h in result["unclassified"])
            self.assertEqual(
                sorted(seen),
                sorted(
                    [
                        "mypy",
                        "run-pytest",
                        "ruff",
                        "some-brand-new-analyzer",
                        "trailing-whitespace",
                    ]
                ),
            )
            self.assertEqual(len(seen), len(set(seen)))


class TestUnclassifiedReachesBlocked(unittest.TestCase):
    def test_unclassified_tool_is_a_blocked_remediation_entry(self):
        with tempfile.TemporaryDirectory() as repo:
            # A matching Makefile target keeps the parity check (Direction
            # A) silent, so this fixture isolates the taxonomy-unclassified
            # path rather than also exercising precommit-parity.
            _write(
                os.path.join(repo, "Makefile"),
                "some-brand-new-analyzer:\n\techo noop\n",
            )
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(_hook("some-brand-new-analyzer")),
            )
            result = cli.remediate(repo)
            self.assertEqual(result["remediate"], [])
            # Task 3's category-absence findings also route to `blocked`
            # for this no-stack-marker fixture -- filter to the
            # taxonomy-specific entry this test is actually about.
            hits = [b for b in result["blocked"] if b["id"] == "some-brand-new-analyzer"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["kind"], "precommit")
            self.assertIsNone(hits[0].get("recommendation"))


class TestPredicateExtensionClauseIII(unittest.TestCase):
    def test_makefile_target_named_after_catalog_tool_with_no_hook_is_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "security-scanner:\n\tuv run bandit -r tools skills\n",
            )
            _write(os.path.join(repo, ".pre-commit-config.yaml"), _precommit_yaml())
            findings = parity_checker.check_parity(repo)
            hits = [f for f in findings if f.get("issue") == "target_without_hook"]
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["target"], "security-scanner")
            self.assertEqual(hits[0]["clause"], "iii")

    def test_bare_general_purpose_linter_name_does_not_become_tool_shaped(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "duplicate-code:\n"
                "\tuv run pylint --disable=all --enable=duplicate-code tools skills\n",
            )
            _write(os.path.join(repo, ".pre-commit-config.yaml"), _precommit_yaml())
            findings = parity_checker.check_parity(repo)
            hits = [f for f in findings if f.get("issue") == "target_without_hook"]
            self.assertEqual(hits, [])

    def test_real_repo_security_scanner_newly_flagged_duplicate_code_not(self):
        f = cli.check(".")["precommit"]
        targets = {x["target"] for x in f if x.get("issue") == "target_without_hook"}
        self.assertIn("security-scanner", targets)
        self.assertNotIn("duplicate-code", targets)


_PYTHON_EVERYTHING_HOOKS = (
    _hook("ruff-fmt", entry="ruff format ."),
    _hook("mypy", entry="mypy ."),
    _hook("ruff", entry="ruff check ."),
    _hook("bandit", entry="bandit -r ."),
)


class TestCategoryAbsenceThreeRealCases(unittest.TestCase):
    """ROADMAP Phase 11 SC4: three real fixture repos, not two plus an
    argument."""

    def _repo_with(self, *extra_hooks):
        repo = tempfile.mkdtemp()
        _write(os.path.join(repo, "pyproject.toml"), '[project]\nname="x"\n')
        _write(
            os.path.join(repo, ".pre-commit-config.yaml"),
            _precommit_yaml(*_PYTHON_EVERYTHING_HOOKS, *extra_hooks),
        )
        return repo

    def test_zero_duplicate_code_tooling_flags_exactly_that_category(self):
        repo = self._repo_with(_hook("vulture", entry="vulture ."))
        findings = precommit_checker.check_precommit_rules(repo)
        issues = {f.get("issue") for f in findings if f.get("category") == "category-absence"}
        self.assertEqual(issues, {"duplicate_code_absent"})

    def test_zero_dead_code_tooling_flags_exactly_that_category(self):
        repo = self._repo_with(_hook("jscpd", entry="jscpd ."))
        findings = precommit_checker.check_precommit_rules(repo)
        issues = {f.get("issue") for f in findings if f.get("category") == "category-absence"}
        self.assertEqual(issues, {"dead_code_absent"})

    def test_both_categories_covered_triggers_neither_finding(self):
        repo = self._repo_with(
            _hook("jscpd", entry="jscpd ."), _hook("vulture", entry="vulture .")
        )
        findings = precommit_checker.check_precommit_rules(repo)
        issues = {f.get("issue") for f in findings if f.get("category") == "category-absence"}
        self.assertEqual(issues, set())


class TestCategoryAbsenceRecommendation(unittest.TestCase):
    def test_recommendation_names_concrete_tool_for_detected_stack(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "pyproject.toml"), '[project]\nname="x"\n')
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(_hook("jscpd", entry="jscpd .")),
            )
            findings = precommit_checker.check_precommit_rules(repo)
            hits = [f for f in findings if f.get("issue") == "dead_code_absent"]
            self.assertEqual(len(hits), 1)
            self.assertIn("vulture", hits[0]["recommendation"])

    def test_unrecognized_stack_and_cold_cache_is_blocked_no_recommendation(self):
        from ai_kit_project_rules_precommit.taxonomy_checker import (
            build_category_absence_findings,
            classify_precommit_tools,
        )

        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, ".pre-commit-config.yaml"), _precommit_yaml())
            cache_root = os.path.join(repo, "_cache")
            classification = classify_precommit_tools(
                repo, cache_root=cache_root, detected_stacks={"zig"}
            )
            findings = build_category_absence_findings(
                classification, repo, detected_stacks={"zig"}, cache_root=cache_root
            )
            self.assertEqual(len(findings), 2)
            for finding in findings:
                self.assertIsNone(finding["recommendation"])
                self.assertTrue(finding["needs_research"])
                self.assertEqual(finding["stacks"], ["zig"])

    def test_no_stack_marker_at_all_produces_a_finding_that_says_so(self):
        from ai_kit_project_rules_precommit.taxonomy_checker import (
            build_category_absence_findings,
            classify_precommit_tools,
        )

        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, ".pre-commit-config.yaml"), _precommit_yaml())
            classification = classify_precommit_tools(repo, detected_stacks=set())
            findings = build_category_absence_findings(
                classification, repo, detected_stacks=set()
            )
            self.assertEqual(len(findings), 2)
            for finding in findings:
                self.assertIn("no detected language stack", finding["summary"])
                self.assertEqual(finding["stacks"], [])
                self.assertIsNone(finding["recommendation"])


class TestCategoryAbsenceD_T5ConsistencyGuard(unittest.TestCase):
    """A dead-code tool known ONLY through a cache entry still counts as
    present -- the case a second keyword scan would get wrong while the
    classification-driven check gets right."""

    def test_cache_only_dead_code_tool_suppresses_the_absence_finding(self):
        from ai_kit_project_rules_precommit.taxonomy_checker import (
            build_category_absence_findings,
            classify_precommit_tools,
        )

        cache_only_tool = "zzz-imaginary-deadcode-detector"
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "pyproject.toml"), '[project]\nname="x"\n')
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(_hook(cache_only_tool, entry=f"{cache_only_tool} .")),
            )
            cache_root = os.path.join(repo, "_cache")
            stack_cache.write_stack_cache(
                "python",
                {
                    "dead-code": (
                        f"{cache_only_tool} (source: https://example.com/imaginary-tool)"
                    )
                },
                cache_root=cache_root,
            )
            classification = classify_precommit_tools(repo, cache_root=cache_root)
            self.assertEqual(len(classification["taxonomy"]["dead-code"]), 1)
            findings = build_category_absence_findings(
                classification, repo, cache_root=cache_root
            )
            issues = {f["issue"] for f in findings}
            self.assertNotIn("dead_code_absent", issues)


class TestDegradation(unittest.TestCase):
    def test_missing_makefile_returns_list_without_raising(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(_hook("ruff", entry="ruff check .")),
            )
            findings = precommit_checker.check_precommit_rules(repo)
            self.assertIsInstance(findings, list)

    def test_missing_precommit_config_returns_list_without_raising(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "noop:\n\techo hi\n")
            findings = precommit_checker.check_precommit_rules(repo)
            self.assertIsInstance(findings, list)

    def test_missing_both_returns_list_without_raising(self):
        with tempfile.TemporaryDirectory() as repo:
            findings = precommit_checker.check_precommit_rules(repo)
            self.assertIsInstance(findings, list)


class TestCliSurface(unittest.TestCase):
    """Only THIS skill's binding is covered here -- the generic cache/
    validator engine's own behavior is already covered in
    tests/test_ai_kit_rules_common.py; duplicating it here is as much a
    defect as dropping it."""

    def test_check_returns_single_key_payload(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "noop:\n\techo hi\n")
            _write(os.path.join(repo, ".pre-commit-config.yaml"), _precommit_yaml())
            result = cli.check(repo)
            self.assertEqual(sorted(result), ["precommit"])

    def test_remediate_returns_two_key_payload(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "noop:\n\techo hi\n")
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                _precommit_yaml(_hook("mypy", entry="mypy .")),
            )
            result = cli.remediate(repo)
            self.assertEqual(sorted(result), ["blocked", "remediate"])
            self.assertTrue(all(e["kind"] == "precommit" for e in result["remediate"]))

    def test_unknown_subcommand_returns_2(self):
        self.assertEqual(cli.main(["bogus"]), 2)

    def test_cache_update_round_trips_through_this_skills_namespace(self):
        with tempfile.TemporaryDirectory() as scratch:
            cache_root = os.path.join(scratch, "_cache")
            json_path = os.path.join(scratch, "tooling.json")
            payload = {
                "dead-code": "vulture (source: https://pypi.org/project/vulture/)",
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
            self.assertIn("dead-code", tooling)

    def test_cache_update_rejects_unknown_key_without_traceback(self):
        with tempfile.TemporaryDirectory() as scratch:
            cache_root = os.path.join(scratch, "_cache")
            json_path = os.path.join(scratch, "tooling.json")
            payload = {"not-a-real-key": "x (source: https://example.com)"}
            _write(json_path, json.dumps(payload))
            rc = cli.main(
                ["cache-update", "python", json_path, "--cache-root", cache_root]
            )
            self.assertEqual(rc, 1)
            self.assertFalse(
                os.path.isfile(stack_cache.cache_path("python", cache_root=cache_root))
            )


class TestGateRegistration(unittest.TestCase):
    def test_makefile_registers_module_and_package(self):
        with open(_MAKEFILE_PATH, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("tests.test_ai_kit_project_rules_precommit", text)
        self.assertIn("skills/ai-kit-project-rules-precommit/", text)

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
        self.assertIn("tests.test_ai_kit_project_rules_precommit", match.group(1))

    def test_pyright_include_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        include = data["tool"]["pyright"]["include"]
        self.assertIn("skills/ai-kit-project-rules-precommit", include)

    def test_vulture_paths_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        paths = data["tool"]["vulture"]["paths"]
        self.assertIn("skills/ai-kit-project-rules-precommit", paths)


def _enable_everything(repo_root):
    return [
        x
        for x in precommit_checker.check_precommit_rules(repo_root)
        if x.get("category") == "enable-everything"
    ]


def _check_limitations(repo_root):
    return [
        x
        for x in precommit_checker.check_precommit_rules(repo_root)
        if x.get("category") == "check-limitation"
    ]


class TestEnableEverythingRuff(unittest.TestCase):
    def test_select_all_is_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "pyproject.toml"),
                '[tool.ruff.lint]\nselect = ["ALL"]\n',
            )
            findings = _enable_everything(repo)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["config_path"], "pyproject.toml")
            self.assertEqual(findings[0]["issue"], "uncurated_ruleset")

    def test_curated_extend_select_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "pyproject.toml"),
                '[tool.ruff.lint]\nextend-select = ["E", "F", "I"]\n',
            )
            self.assertEqual(_enable_everything(repo), [])


class TestEnableEverythingGo(unittest.TestCase):
    def test_enable_all_true_is_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".golangci.yml"),
                "linters:\n  enable-all: true\n",
            )
            findings = _enable_everything(repo)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["config_path"], ".golangci.yml")

    def test_explicit_curated_enable_list_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".golangci.yml"),
                "linters:\n  enable:\n    - errcheck\n    - govet\n",
            )
            self.assertEqual(_enable_everything(repo), [])


class TestEnableEverythingNode(unittest.TestCase):
    def test_extends_everything_preset_is_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".eslintrc.json"),
                json.dumps({"extends": "eslint:all"}),
            )
            findings = _enable_everything(repo)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["config_path"], ".eslintrc.json")

    def test_extends_named_preset_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, ".eslintrc.json"),
                json.dumps({"extends": ["eslint:recommended"]}),
            )
            self.assertEqual(_enable_everything(repo), [])


class TestEnableEverythingJava(unittest.TestCase):
    def test_whole_category_ref_is_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "pmd.xml"),
                '<ruleset><rule ref="category/java/bestpractices.xml"/></ruleset>\n',
            )
            findings = _enable_everything(repo)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["config_path"], "pmd.xml")

    def test_named_rules_ref_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "pmd.xml"),
                (
                    '<ruleset><rule ref='
                    '"category/java/bestpractices.xml/UnusedLocalVariable"/>'
                    "</ruleset>\n"
                ),
            )
            self.assertEqual(_enable_everything(repo), [])

    def test_rulesets_dir_one_level_deep_is_discovered(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "rulesets", "team.xml"),
                '<ruleset><rule ref="category/java/security.xml"/></ruleset>\n',
            )
            findings = _enable_everything(repo)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["config_path"], os.path.join("rulesets", "team.xml"))


class TestEnableEverythingLimitation(unittest.TestCase):
    def test_js_module_only_produces_limitation_not_enable_everything(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "eslint.config.js"), "export default [];\n")
            self.assertEqual(_enable_everything(repo), [])
            limitations = _check_limitations(repo)
            self.assertEqual(len(limitations), 1)
            self.assertEqual(limitations[0]["config_path"], "eslint.config.js")
            self.assertIn("statically", limitations[0]["summary"])

    def test_json_form_alongside_js_module_suppresses_limitation(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "eslint.config.js"), "export default [];\n")
            _write(
                os.path.join(repo, ".eslintrc.json"),
                json.dumps({"extends": ["eslint:recommended"]}),
            )
            self.assertEqual(_check_limitations(repo), [])
            # The normal check result still applies to the JSON form.
            self.assertEqual(_enable_everything(repo), [])

    def test_limitation_finding_reaches_remediate_with_auto_apply_off(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "eslint.config.js"), "export default [];\n")
            result = cli.remediate(repo)
            entries = [
                e for e in result["remediate"] if e.get("issue") == "config_not_statically_readable"
            ]
            self.assertEqual(len(entries), 1)
            self.assertFalse(entries[0]["auto_apply"])


class TestConfigReadDegradation(unittest.TestCase):
    """Every reader in config_read.py degrades to no-finding on malformed,
    wrong-typed, absent, and empty input, proven through the real
    entrypoint per the plan's instruction to assert absence of an
    exception explicitly rather than catching one in the test."""

    def test_truncated_toml_produces_no_finding_and_no_exception(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "pyproject.toml"), '[tool.ruff.lint]\nselect = ["E"\n')
            findings = precommit_checker.check_precommit_rules(repo)
            self.assertIsInstance(findings, list)
            self.assertEqual(_enable_everything(repo), [])

    def test_json_top_level_list_produces_no_finding_and_no_exception(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, ".eslintrc.json"), json.dumps(["not", "a", "mapping"]))
            findings = precommit_checker.check_precommit_rules(repo)
            self.assertIsInstance(findings, list)
            self.assertEqual(_enable_everything(repo), [])

    def test_directory_instead_of_file_produces_no_finding_and_no_exception(self):
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, ".golangci.yml"))
            findings = precommit_checker.check_precommit_rules(repo)
            self.assertIsInstance(findings, list)
            self.assertEqual(_enable_everything(repo), [])

    def test_empty_file_produces_no_finding_and_no_exception(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "pmd.xml"), "")
            findings = precommit_checker.check_precommit_rules(repo)
            self.assertIsInstance(findings, list)
            self.assertEqual(_enable_everything(repo), [])

    def test_read_yaml_value_never_raises_on_malformed_input(self):
        with tempfile.TemporaryDirectory() as repo:
            path = os.path.join(repo, ".golangci.yml")
            _write(path, "linters: [this, is, not, a, mapping\n")
            value = config_read.read_yaml_value(path, ("linters", "enable-all"))
            self.assertIs(value, config_read.NOT_READABLE)

    def test_read_toml_never_raises_on_absent_file(self):
        with tempfile.TemporaryDirectory() as repo:
            path = os.path.join(repo, "does-not-exist.toml")
            self.assertIs(config_read.read_toml(path), config_read.NOT_READABLE)


class TestEnableEverythingPathsAreRepoRelative(unittest.TestCase):
    def test_ruff_and_go_finding_paths_never_start_with_a_separator(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "pyproject.toml"),
                '[tool.ruff.lint]\nselect = ["ALL"]\n',
            )
            _write(os.path.join(repo, ".golangci.yml"), "linters:\n  enable-all: true\n")
            findings = _enable_everything(repo)
            self.assertEqual(len(findings), 2)
            for finding in findings:
                self.assertFalse(finding["config_path"].startswith(os.sep))


class TestReadYamlValueBlockSequenceContract(unittest.TestCase):
    """Direct, positive proof (not a non-triggering assertion) that the
    YAML subset reader reads all three required value shapes at a known
    key path -- see this plan's YAML-BLOCK-SEQ-OK acceptance criterion."""

    def test_scalar_inline_list_and_block_sequence_all_read(self):
        with tempfile.TemporaryDirectory() as repo:
            path = os.path.join(repo, ".golangci.yml")
            _write(
                path,
                (
                    "run:\n  timeout: 5m\n"
                    "linters:\n"
                    "  enable-all: false\n"
                    "  disable:\n"
                    "    - staticcheck\n"
                    "    - errcheck\n"
                    "  enable: [govet, ineffassign]\n"
                ),
            )
            disable = config_read.read_yaml_value(path, ("linters", "disable"))
            enable = config_read.read_yaml_value(path, ("linters", "enable"))
            enable_all = config_read.read_yaml_value(path, ("linters", "enable-all"))
            self.assertEqual(list(disable), ["staticcheck", "errcheck"])
            self.assertEqual(list(enable), ["govet", "ineffassign"])
            self.assertEqual(str(enable_all).lower(), "false")


if __name__ == "__main__":
    unittest.main()
