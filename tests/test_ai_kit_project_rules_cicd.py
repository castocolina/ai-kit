"""Tests for `ai-kit-project-rules-cicd` (REQ-rules-cicd, Phase 14 plan 01).

Plan 14-01, Task 1's tracer contract: the `TestTracer*` classes below
carry the `<behavior>` cases written before the checker existed and
confirmed to fail for the right reason (ImportError -- the package did
not exist yet), then implemented against until they passed. Task 2 fills
the suite out with paired triggering/non-triggering fixtures for every
structural check, D-C3's identity clauses, D-C4's gate and its Route 3
qualifier, D-C5's match rule, D-C6's segmentation and reuse table,
D-C13's determinism, the degradation paths, D-C7's identifier discipline,
the CLI surface, and its own gate-registration class. The shared suite's
grown `STRUCTURAL_KINDS` tuple, the new `yaml_text` primitives,
`command_text`, and both drift guards live in
`tests/test_ai_kit_rules_common.py` instead.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-cicd"),
)

from ai_kit_project_rules_cicd import ci_parse, cicd_checker, cli, reuse_sources

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MAKEFILE_PATH = os.path.join(_REPO, "Makefile")
_PRECOMMIT_PATH = os.path.join(_REPO, ".pre-commit-config.yaml")
_PYPROJECT_PATH = os.path.join(_REPO, "pyproject.toml")
_CLI_PY_CANDIDATE = "skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/cli.py"
_ENTRYPOINT = [
    sys.executable,
    os.path.join(_REPO, "skills", "ai-kit-project-rules-cicd", "ai-kit-project-rules-cicd.py"),
]


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def _fixture(files: dict) -> str:
    """A fresh temp-dir repo containing `files` (relative path -> text)."""
    repo = tempfile.mkdtemp()
    for relpath, content in files.items():
        _write(os.path.join(repo, relpath), content)
    return repo


def _findings(repo_root):
    return cicd_checker.check_cicd_rules(repo_root)


_MK_RUFF_MYPY = (
    "ruff:\n\tuv run ruff check .\n\n"
    "mypy:\n\tuv run mypy .\n\n"
    "clean:\n\trm -rf dist\n\n"
    "greet:\n\techo hello\n"
)


class TestTracerDirectInvocationFlagged(unittest.TestCase):
    """<behavior> case 1: a GitLab CI job running `ruff check .` directly
    beside a matching single-tool `ruff` Makefile target yields exactly
    ONE finding naming BOTH the duplicated invocation and the replacement
    command (ROADMAP SC1)."""

    def test_direct_invocation_produces_one_finding_naming_both_sides(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": (
                    "lint-job:\n  stage: test\n  script:\n  - ruff check .\n"
                ),
            }
        )
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding["category"], "cicd-command-reuse")
        self.assertEqual(finding["issue"], "ci_duplicates_existing_command")
        self.assertNotIn("target", finding)
        self.assertEqual(finding["reuse_surface"], "makefile")
        self.assertEqual(finding["reuse_command"], "make ruff")
        self.assertIn("ruff check .", finding["recommendation"])
        self.assertIn("make ruff", finding["recommendation"])


class TestTracerReuseInvocationSilent(unittest.TestCase):
    """<behavior> case 2: the same fixture whose `script:` calls the
    target instead yields ZERO findings (ROADMAP SC2)."""

    def test_calling_the_target_produces_zero_findings(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": "lint-job:\n  script:\n  - make ruff\n",
            }
        )
        self.assertEqual(_findings(repo), [])


class TestTracerMixedDirectAndReuse(unittest.TestCase):
    """<behavior> case 3: a `script:` mixing a direct invocation and a
    reuse invocation yields exactly one finding, for the direct one
    only."""

    def test_mixed_script_flags_only_the_direct_line(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": (
                    "lint-job:\n  script:\n  - ruff check .\n  - make mypy\n"
                ),
            }
        )
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["tool"], "ruff check")


class TestTracerNoCiConfig(unittest.TestCase):
    """<behavior> case 4: a repo with a Makefile and no CI config of any
    kind yields zero findings (D-C1)."""

    def test_no_ci_config_is_zero_findings(self):
        repo = _fixture({"Makefile": _MK_RUFF_MYPY})
        self.assertEqual(_findings(repo), [])


class TestTracerAiKitOwnRoot(unittest.TestCase):
    """<behavior> case 5: ai-kit's own repository root yields zero
    findings -- the live case. Its `.gitlab-ci.yml` satisfies D-C1's gate
    (it exists) and declares no `script:` anywhere (an `include:` and a
    `secret_detection:` job with no `script:` key), so this exercises the
    reader and the matcher, not just the gate. If this repo's own CI ever
    gains a direct tool invocation, this method failing is the correct
    signal, not a nuisance."""

    def test_ai_kit_own_root_is_zero_findings(self):
        self.assertEqual(_findings(_REPO), [])


class TestTracerIdentityGateShellNoise(unittest.TestCase):
    """<behavior> case 6: CI lines running `rm -rf dist`/`echo hello`
    beside SYNTHETIC `clean:`/`greet:` targets that run exactly those
    never enter the reuse inventory (D-C4). Neither target exists in
    ai-kit's own Makefile."""

    def test_shell_noise_targets_never_produce_findings(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": (
                    "j:\n  script:\n  - rm -rf dist\n  - echo hello\n"
                ),
            }
        )
        self.assertEqual(_findings(repo), [])


class TestTracerRuffWideningBoundary(unittest.TestCase):
    """<behavior> case 7: `ruff format .` against a `ruff` (linter)
    target yields zero findings, while the same repo's `ruff check .`
    line yields one (D-C5's widening and its boundary, in one paired
    fixture)."""

    def test_formatting_does_not_match_linting_target(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": "j:\n  script:\n  - ruff format .\n",
            }
        )
        self.assertEqual(_findings(repo), [])

    def test_linting_matches_linting_target(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": "j:\n  script:\n  - ruff check .\n",
            }
        )
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["reuse_command"], "make ruff")


class TestTracerTwoLineTargetIdentity(unittest.TestCase):
    """<behavior> case 8: a two-real-line `ruff:` target whose lines
    compute DIFFERENT keys (`ruff check .` / `ruff format .`) is an
    aggregate with no identity, so a matching CI `ruff check .` line
    yields ZERO findings; the paired two-real-line target whose lines
    compute the SAME key (`ruff check .` / `ruff check --fix .`) DOES
    cover a CI `ruff check .` line (D-C3 clause (b2))."""

    def test_different_key_two_line_target_has_no_identity(self):
        mk = "ruff:\n\truff check .\n\truff format .\n"
        repo = _fixture(
            {"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - ruff check .\n"}
        )
        self.assertEqual(_findings(repo), [])

    def test_same_key_two_line_target_covers_ci_line(self):
        mk = "ruff:\n\truff check .\n\truff check --fix .\n"
        repo = _fixture(
            {"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - ruff check .\n"}
        )
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["reuse_command"], "make ruff")


class TestTracerIncludeNeverFollowed(unittest.TestCase):
    """<behavior> case 9 (D-C28): a root `.gitlab-ci.yml` that only
    `include:`s a local file, whose included file declares a job running
    `ruff check .` beside a matching `ruff` Makefile target, yields ZERO
    findings -- and the included file is never opened."""

    def test_include_local_is_never_followed(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": "include:\n- local: ci/lint.yml\nj:\n  stage: test\n",
                "ci/lint.yml": "lint:\n  script:\n  - ruff check .\n",
            }
        )
        self.assertEqual(_findings(repo), [])

        opened: list[str] = []
        original_read = cicd_checker.ci_parse.read_ci_text

        def _tracking_read(path):
            opened.append(path)
            return original_read(path)

        cicd_checker.ci_parse.read_ci_text = _tracking_read
        try:
            _findings(repo)
        finally:
            cicd_checker.ci_parse.read_ci_text = original_read
        self.assertTrue(all("ci/lint.yml" not in p for p in opened), opened)


class TestTracerUnreadableMakefile(unittest.TestCase):
    """<behavior> case 10 (D-C10): a repo whose `Makefile` is unreadable
    binary content yields a LIST and no traceback."""

    def test_binary_makefile_degrades_to_empty_list(self):
        repo = tempfile.mkdtemp()
        _write(os.path.join(repo, ".gitlab-ci.yml"), "j:\n  script:\n  - ruff check .\n")
        with open(os.path.join(repo, "Makefile"), "wb") as handle:
            handle.write(b"\xff\xfe\x00 binary, not utf-8\n")
        findings = _findings(repo)
        self.assertEqual(findings, [])


# --------------------------------------------------------------------------- #
# Task 2: paired triggering/non-triggering fixtures for every structural
# check, D-C3's identity clauses, D-C4's gate and its Route 3 qualifier,
# D-C5's match rule, D-C6's segmentation and reuse table, D-C13's
# determinism, degradation, D-C7's identifier discipline, the CLI surface,
# and gate registration.
# --------------------------------------------------------------------------- #


class TestApplicabilityGatePositive(unittest.TestCase):
    """D-C1, each clause on its own."""

    def test_gitlab_ci_yml_satisfies_the_gate(self):
        repo = _fixture({".gitlab-ci.yml": "j:\n  script:\n  - x\n"})
        self.assertTrue(ci_parse.repo_has_ci_config(repo))

    def test_gitlab_ci_yaml_satisfies_the_gate(self):
        repo = _fixture({".gitlab-ci.yaml": "j:\n  script:\n  - x\n"})
        self.assertTrue(ci_parse.repo_has_ci_config(repo))

    def test_github_workflows_yml_satisfies_the_gate(self):
        repo = _fixture({".github/workflows/ci.yml": "name: CI\n"})
        self.assertTrue(ci_parse.repo_has_ci_config(repo))

    def test_github_workflows_yaml_satisfies_the_gate(self):
        repo = _fixture({".github/workflows/ci.yaml": "name: CI\n"})
        self.assertTrue(ci_parse.repo_has_ci_config(repo))


class TestApplicabilityGateNegative(unittest.TestCase):
    """D-C1's negative edges -- each must NOT satisfy the gate."""

    def test_repo_with_no_ci_config_does_not_satisfy_the_gate(self):
        repo = _fixture({"Makefile": _MK_RUFF_MYPY})
        self.assertFalse(ci_parse.repo_has_ci_config(repo))

    def test_empty_workflows_directory_does_not_satisfy_the_gate(self):
        repo = tempfile.mkdtemp()
        os.makedirs(os.path.join(repo, ".github", "workflows"))
        self.assertFalse(ci_parse.repo_has_ci_config(repo))

    def test_workflows_directory_with_no_yaml_does_not_satisfy_the_gate(self):
        repo = _fixture({".github/workflows/README.md": "not yaml\n"})
        self.assertFalse(ci_parse.repo_has_ci_config(repo))

    def test_nested_gitlab_ci_file_does_not_satisfy_the_gate(self):
        repo = _fixture({"sub/.gitlab-ci.yml": "j:\n  script:\n  - x\n"})
        self.assertFalse(ci_parse.repo_has_ci_config(repo))


class TestReaderShapes(unittest.TestCase):
    """The GitLab reader, paired per shape it claims to read."""

    def test_script_items_are_read(self):
        sites = list(ci_parse.iter_command_sites("j:\n  script:\n  - a\n  - b\n"))
        self.assertEqual(sites, [("j", ["a", "b"])])

    def test_before_and_after_script_ordering_is_fixed_regardless_of_declaration_order(self):
        text = "j:\n  after_script:\n  - c\n  script:\n  - b\n  before_script:\n  - a\n"
        sites = list(ci_parse.iter_command_sites(text))
        self.assertEqual(sites, [("j", ["a", "b", "c"])])

    def test_block_scalar_item_contributes_each_continuation_line(self):
        text = "j:\n  script:\n  - |\n    line one\n    line two\n"
        sites = list(ci_parse.iter_command_sites(text))
        self.assertEqual(sites, [("j", ["line one", "line two"])])

    def test_default_block_scripts_are_read(self):
        text = "default:\n  script:\n  - a\n"
        sites = list(ci_parse.iter_command_sites(text))
        self.assertEqual(sites, [("default", ["a"])])

    def test_dot_prefixed_template_scripts_are_read(self):
        text = ".template:\n  script:\n  - a\n"
        sites = list(ci_parse.iter_command_sites(text))
        self.assertEqual(sites, [(".template", ["a"])])

    def test_top_level_sequence_valued_before_script_is_its_own_pseudo_site(self):
        text = "before_script:\n- a\n- b\n"
        sites = list(ci_parse.iter_command_sites(text))
        self.assertEqual(sites, [("before_script", ["a", "b"])])


class TestReaderReservedKeysContributeNoCommandLines(unittest.TestCase):
    """`stages:`, `variables:`, `include:`, and a job with no script key
    at all -- ai-kit's own live shape -- must NOT contribute command
    lines."""

    def test_stages_is_ignored(self):
        sites = list(ci_parse.iter_command_sites("stages:\n- test\n"))
        self.assertEqual(sites, [])

    def test_variables_is_ignored(self):
        sites = list(ci_parse.iter_command_sites('variables:\n  X: "1"\n'))
        self.assertEqual(sites, [])

    def test_include_is_ignored(self):
        sites = list(ci_parse.iter_command_sites("include:\n- local: x.yml\n"))
        self.assertEqual(sites, [])

    def test_job_with_no_script_key_is_ignored(self):
        text = "secret_detection:\n  stage: secret-detection\n"
        sites = list(ci_parse.iter_command_sites(text))
        self.assertEqual(sites, [])


class TestReaderStatedLimits(unittest.TestCase):
    """The reader's stated limits, as recorded behavior: each returns a
    LIST (possibly empty) and never raises."""

    def test_tab_indented_file_does_not_raise(self):
        text = "j:\n\tscript:\n\t- ruff check .\n"
        result = list(ci_parse.iter_command_sites(text))
        self.assertIsInstance(result, list)

    def test_anchor_alias_merge_key_file_does_not_raise(self):
        text = "defaults: &defaults\n  image: x\nj:\n  <<: *defaults\n  script:\n  - a\n"
        result = list(ci_parse.iter_command_sites(text))
        self.assertIsInstance(result, list)

    def test_reference_tag_file_does_not_raise(self):
        text = "j:\n  script:\n  - !reference [.setup, script]\n"
        result = list(ci_parse.iter_command_sites(text))
        self.assertIsInstance(result, list)

    def test_heredoc_line_is_skipped_not_misparsed(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": (
                    "j:\n  script:\n  - python3 - <<EOF\n  - ruff check .\n"
                ),
            }
        )
        findings = _findings(repo)
        # Only the real "ruff check ." line is evaluated; the heredoc line
        # is skipped entirely rather than mis-parsed into a finding.
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["command"], "ruff check .")

    def test_include_local_is_a_disclosed_limit_and_produces_no_findings(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": "include:\n- local: ci/lint.yml\nj:\n  stage: test\n",
                "ci/lint.yml": "lint:\n  script:\n  - ruff check .\n",
            }
        )
        self.assertEqual(_findings(repo), [])

        opened: list[str] = []
        original_read = cicd_checker.ci_parse.read_ci_text

        def _tracking_read(path):
            opened.append(path)
            return original_read(path)

        cicd_checker.ci_parse.read_ci_text = _tracking_read
        try:
            _findings(repo)
        finally:
            cicd_checker.ci_parse.read_ci_text = original_read
        self.assertTrue(all("ci/lint.yml" not in p for p in opened), opened)

    def test_include_template_over_ai_kits_own_shape_is_a_disclosed_limit(self):
        # ai-kit's own real .gitlab-ci.yml shape: `include: - template: ...`.
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": (
                    "include:\n- template: Security/Secret-Detection.gitlab-ci.yml\n"
                    "secret_detection:\n  stage: secret-detection\n"
                ),
            }
        )
        self.assertEqual(_findings(repo), [])


class TestIdentityExtractionClauses(unittest.TestCase):
    """D-C3's identity-extraction clauses, each proven through whether a
    matching CI line is flagged -- never the internal shape alone."""

    def test_clause_b_single_line_target_is_flagged(self):
        mk = "ruff:\n\tuv run ruff check .\n"
        repo = _fixture({"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - ruff check .\n"})
        self.assertEqual(len(_findings(repo)), 1)

    def test_clause_a_delegate_target_is_flagged(self):
        mk = "validate-lint:\n\tuv run pre-commit run ruff --all-files\n"
        repo = _fixture({"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - ruff check .\n"})
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["reuse_command"], "make validate-lint")

    def test_clause_b2_same_key_pair_is_flagged(self):
        mk = "ruff:\n\truff check .\n\truff check --fix .\n"
        repo = _fixture({"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - ruff check .\n"})
        self.assertEqual(len(_findings(repo)), 1)

    def test_clause_b2_different_key_pair_yields_no_findings(self):
        mk = "ruff:\n\truff check .\n\truff format .\n"
        repo = _fixture({"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - ruff check .\n"})
        self.assertEqual(_findings(repo), [])

    def test_clause_c_catalog_bare_name_is_flagged(self):
        # A bare `ruff:` target with no recipe and no prerequisites --
        # admitted by D-C4 Route 1 via AMBIGUOUS_TOOL_DEFAULTS.
        mk = "ruff:\n"
        repo = _fixture({"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - ruff check .\n"})
        self.assertEqual(len(_findings(repo)), 1)

    def test_clause_c_non_catalog_bare_name_yields_no_findings(self):
        mk = "my-house-style:\n"
        repo = _fixture(
            {"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - my-house-style x\n"}
        )
        self.assertEqual(_findings(repo), [])

    def test_three_real_line_target_is_capped_out_and_yields_no_findings(self):
        mk = "ruff:\n\techo a\n\techo b\n\truff check .\n"
        repo = _fixture({"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - ruff check .\n"})
        self.assertEqual(_findings(repo), [])

    def test_prerequisites_with_empty_recipe_aggregate_yields_no_findings(self):
        # ai-kit's own real shape: `validate:` is prerequisites-only with
        # an empty recipe.
        mk = "ruff:\n\truff check .\n\nvalidate: ruff\n"
        repo = _fixture({"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - validate\n"})
        self.assertEqual(_findings(repo), [])


class TestIdentityGateNegatives(unittest.TestCase):
    """D-C4's negatives first: shell-noise commands never enter the reuse
    inventory even when a SYNTHETIC target runs exactly that command."""

    def _assert_shell_noise_target_is_never_a_reuse_source(self, target_name, command):
        mk = f"{target_name}:\n\t{command}\n"
        repo = _fixture(
            {"Makefile": mk, ".gitlab-ci.yml": f"j:\n  script:\n  - {command}\n"}
        )
        self.assertEqual(_findings(repo), [], f"{target_name} wrongly entered the inventory")

    def test_rm_target_is_never_a_reuse_source(self):
        self._assert_shell_noise_target_is_never_a_reuse_source("clean", "rm -rf dist")

    def test_echo_target_is_never_a_reuse_source(self):
        self._assert_shell_noise_target_is_never_a_reuse_source("greet", "echo hello")

    def test_cd_target_is_never_a_reuse_source(self):
        self._assert_shell_noise_target_is_never_a_reuse_source("enter", "cd sub")

    def test_git_target_is_never_a_reuse_source(self):
        self._assert_shell_noise_target_is_never_a_reuse_source("tag", "git tag v1")

    def test_bash_target_is_never_a_reuse_source(self):
        self._assert_shell_noise_target_is_never_a_reuse_source("run-script", "bash script.sh")

    def test_pytest_target_is_flagged_via_out_of_taxonomy_route(self):
        # The case a catalog-gated design would silently miss (D-C2).
        mk = "test:\n\tuv run pytest\n"
        repo = _fixture({"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - pytest\n"})
        self.assertEqual(len(_findings(repo)), 1)

    def test_route3_admits_identity_derived_from_a_real_command_body(self):
        mk = "myformatter:\n\tmyformatter --fix\n"
        repo = _fixture(
            {"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - myformatter --fix\n"}
        )
        self.assertEqual(len(_findings(repo)), 1)

    def test_route3_rejects_the_same_name_with_no_command_body(self):
        mk = "myformatter:\n"
        repo = _fixture(
            {"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - myformatter --fix\n"}
        )
        self.assertEqual(_findings(repo), [])


class TestMatchRuleRuffTriad(unittest.TestCase):
    """D-C5's match rule, the `ruff` triad at its centre."""

    _MK_RUFF_ONLY = "ruff:\n\truff check .\n"

    def test_bare_ruff_identity_matches_ci_ruff_check(self):
        mk = "ruff:\n"
        repo = _fixture({"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - ruff check .\n"})
        self.assertEqual(len(_findings(repo)), 1)

    def test_ruff_format_matches_neither_ruff_nor_ruff_check(self):
        repo = _fixture(
            {"Makefile": self._MK_RUFF_ONLY, ".gitlab-ci.yml": "j:\n  script:\n  - ruff format .\n"}
        )
        self.assertEqual(_findings(repo), [])

    def test_ruff_check_identity_matches_ruff_check_with_fix(self):
        repo = _fixture(
            {
                "Makefile": self._MK_RUFF_ONLY,
                ".gitlab-ci.yml": "j:\n  script:\n  - ruff check --fix .\n",
            }
        )
        self.assertEqual(len(_findings(repo)), 1)

    def test_two_token_form_go_test_matches_via_out_of_taxonomy(self):
        mk = "test:\n\tgo test ./...\n"
        repo = _fixture({"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - go test ./...\n"})
        self.assertEqual(len(_findings(repo)), 1)

    def test_two_token_form_tsc_no_emit_matches(self):
        mk = "types:\n\tuv run tsc --noEmit\n"
        repo = _fixture(
            {"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - tsc --noEmit\n"}
        )
        self.assertEqual(len(_findings(repo)), 1)

    def test_unknown_key_with_no_reuse_source_yields_no_findings(self):
        repo = _fixture(
            {
                "Makefile": self._MK_RUFF_ONLY,
                ".gitlab-ci.yml": "j:\n  script:\n  - somemysterytool x\n",
            }
        )
        self.assertEqual(_findings(repo), [])


class TestSegmentationAndReuseTable(unittest.TestCase):
    """D-C6's segmentation and the reuse-invocation table."""

    def test_and_joined_line_flags_only_the_direct_segment(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": "j:\n  script:\n  - make ruff && ruff check .\n",
            }
        )
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["command"], "ruff check .")

    def test_semicolon_joined_line_flags_only_the_direct_segment(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": "j:\n  script:\n  - make ruff; ruff check .\n",
            }
        )
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)

    def test_quoted_and_operator_inside_argument_is_not_split(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": "j:\n  script:\n  - echo 'a && b'\n",
            }
        )
        self.assertEqual(_findings(repo), [])

    def test_pipeline_first_stage_is_the_classified_one(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": "j:\n  script:\n  - ruff check . | tee out.log\n",
            }
        )
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)

    def test_var_assignment_prefix_is_classified_as_ruff_check(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": "j:\n  script:\n  - VAR=1 ruff check .\n",
            }
        )
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["tool"], "ruff check")

    def test_uv_run_direct_invocation_is_flagged(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": "j:\n  script:\n  - uv run ruff check .\n",
            }
        )
        self.assertEqual(len(_findings(repo)), 1)

    def test_npx_direct_invocation_is_flagged(self):
        mk = "lint:\n\tnpx eslint .\n"
        repo = _fixture(
            {"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - npx eslint .\n"}
        )
        self.assertEqual(len(_findings(repo)), 1)

    def test_pnpm_exec_direct_invocation_is_flagged_not_reuse(self):
        # The ordering proof: `pnpm exec` is stripped before the reuse
        # table is checked, so this reads as a DIRECT `eslint` call.
        mk = "lint:\n\tnpx eslint .\n"
        repo = _fixture(
            {"Makefile": mk, ".gitlab-ci.yml": "j:\n  script:\n  - pnpm exec eslint .\n"}
        )
        self.assertEqual(len(_findings(repo)), 1)

    def test_make_row_is_reuse_and_never_a_finding(self):
        repo = _fixture(
            {"Makefile": _MK_RUFF_MYPY, ".gitlab-ci.yml": "j:\n  script:\n  - make ruff\n"}
        )
        self.assertEqual(_findings(repo), [])

    def test_pre_commit_run_row_is_reuse_and_never_a_finding(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY,
                ".gitlab-ci.yml": "j:\n  script:\n  - pre-commit run ruff --all-files\n",
            }
        )
        self.assertEqual(_findings(repo), [])

    def test_npm_run_row_is_reuse_and_never_a_finding(self):
        repo = _fixture(
            {"Makefile": _MK_RUFF_MYPY, ".gitlab-ci.yml": "j:\n  script:\n  - npm run lint\n"}
        )
        self.assertEqual(_findings(repo), [])

    def test_bare_yarn_script_row_is_reuse_and_never_a_finding(self):
        repo = _fixture(
            {"Makefile": _MK_RUFF_MYPY, ".gitlab-ci.yml": "j:\n  script:\n  - yarn lint\n"}
        )
        self.assertEqual(_findings(repo), [])

    def test_gradlew_row_is_reuse_and_never_a_finding(self):
        repo = _fixture(
            {"Makefile": _MK_RUFF_MYPY, ".gitlab-ci.yml": "j:\n  script:\n  - ./gradlew check\n"}
        )
        self.assertEqual(_findings(repo), [])

    def test_classify_reuse_invocation_matches_each_table_row_directly(self):
        for segment, surface in (
            ("make", "makefile"),
            ("make ruff", "makefile"),
            ("pre-commit run ruff", "precommit"),
            ("npm run lint", "package-json"),
            ("npm test", "package-json"),
            ("pnpm run lint", "package-json"),
            ("yarn run lint", "package-json"),
            ("yarn lint", "package-json"),
            ("pnpm lint", "package-json"),
            ("gradle check", "gradle"),
            ("gradlew check", "gradle"),
            ("./gradlew check", "gradle"),
        ):
            with self.subTest(segment=segment):
                self.assertEqual(reuse_sources.classify_reuse_invocation(segment), surface)

    def test_direct_invocation_is_not_classified_as_reuse(self):
        self.assertIsNone(reuse_sources.classify_reuse_invocation("ruff check ."))


class TestDeterminism(unittest.TestCase):
    """D-C13: CI files in discovery order, then command sites in
    file-declaration order, then segments in line order. Order and
    alphabetical order DISAGREE on purpose."""

    _MK = (
        "zzz:\n\tuv run tsc --noEmit\n\n"
        "aaa:\n\tuv run ruff check .\n"
    )
    _CI = (
        "b-job:\n  script:\n  - tsc --noEmit\n"
        "a-job:\n  script:\n  - ruff check .\n"
    )

    def test_findings_follow_declaration_order_not_alphabetical(self):
        repo = _fixture({"Makefile": self._MK, ".gitlab-ci.yml": self._CI})
        findings = _findings(repo)
        self.assertEqual([f["job"] for f in findings], ["b-job", "a-job"])

    def test_two_runs_produce_byte_identical_json(self):
        repo = _fixture({"Makefile": self._MK, ".gitlab-ci.yml": self._CI})
        first = json.dumps(cli.check(repo), sort_keys=False)
        second = json.dumps(cli.check(repo), sort_keys=False)
        self.assertEqual(first, second)


class TestDegradation(unittest.TestCase):
    """Each degradation path returns a list and never raises."""

    def test_gate_satisfying_repo_with_no_makefile_yields_no_findings(self):
        repo = _fixture({".gitlab-ci.yml": "j:\n  script:\n  - ruff check .\n"})
        self.assertEqual(_findings(repo), [])

    def test_empty_makefile_yields_no_findings(self):
        repo = _fixture(
            {"Makefile": "", ".gitlab-ci.yml": "j:\n  script:\n  - ruff check .\n"}
        )
        self.assertEqual(_findings(repo), [])

    def test_unreadable_binary_makefile_yields_no_findings(self):
        repo = tempfile.mkdtemp()
        _write(os.path.join(repo, ".gitlab-ci.yml"), "j:\n  script:\n  - ruff check .\n")
        with open(os.path.join(repo, "Makefile"), "wb") as handle:
            handle.write(b"\xff\xfe\x00 binary, not utf-8\n")
        self.assertEqual(_findings(repo), [])

    def test_unreadable_binary_ci_file_yields_no_findings(self):
        repo = tempfile.mkdtemp()
        _write(os.path.join(repo, "Makefile"), _MK_RUFF_MYPY)
        with open(os.path.join(repo, ".gitlab-ci.yml"), "wb") as handle:
            handle.write(b"\xff\xfe\x00 binary, not utf-8\n")
        self.assertEqual(_findings(repo), [])

    @unittest.skipIf(os.geteuid() == 0, "root ignores file permission bits -- skip: not enforced")
    def test_chmod_000_makefile_yields_no_findings(self):
        repo = tempfile.mkdtemp()
        _write(os.path.join(repo, ".gitlab-ci.yml"), "j:\n  script:\n  - ruff check .\n")
        mk_path = os.path.join(repo, "Makefile")
        _write(mk_path, _MK_RUFF_MYPY)
        os.chmod(mk_path, 0o000)
        try:
            self.assertEqual(_findings(repo), [])
        finally:
            os.chmod(mk_path, 0o644)

    def test_shared_parser_really_raises_on_the_binary_fixture(self):
        # Pairs with `test_unreadable_binary_makefile_yields_no_findings`
        # above: this is what makes D-C10's wrap non-vacuous.
        sys.path.insert(0, os.path.join(_REPO, "skills", "_shared"))
        from ai_kit_rules_common.makefile_parse import parse_makefile_targets

        repo = tempfile.mkdtemp()
        mk_path = os.path.join(repo, "Makefile")
        with open(mk_path, "wb") as handle:
            handle.write(b"\xff\xfe\x00 binary, not utf-8\n")
        with self.assertRaises((OSError, UnicodeDecodeError)):
            parse_makefile_targets(mk_path)


class TestIdentifierDiscipline(unittest.TestCase):
    """D-C7: no finding carries `target`; every remediate id is the
    category."""

    def test_no_finding_carries_the_prohibited_target_key(self):
        repo = _fixture(
            {"Makefile": _MK_RUFF_MYPY, ".gitlab-ci.yml": "j:\n  script:\n  - ruff check .\n"}
        )
        for finding in _findings(repo):
            self.assertNotIn("target", finding)

    def test_remediate_id_is_always_the_category(self):
        repo = _fixture(
            {"Makefile": _MK_RUFF_MYPY, ".gitlab-ci.yml": "j:\n  script:\n  - ruff check .\n"}
        )
        payload = cli.remediate(repo)
        self.assertEqual(payload["remediate"][0]["id"], "cicd-command-reuse")


class TestCliSurface(unittest.TestCase):
    """`check` and `remediate`'s own binding -- the shared builder's
    behavior is covered by the shared suite, not duplicated here."""

    def test_check_returns_single_key_payload(self):
        repo = _fixture({"Makefile": _MK_RUFF_MYPY})
        self.assertEqual(set(cli.check(repo)), {"cicd"})

    def test_remediate_returns_two_key_payload(self):
        repo = _fixture({"Makefile": _MK_RUFF_MYPY})
        self.assertEqual(set(cli.remediate(repo)), {"remediate", "blocked"})

    def test_unknown_subcommand_returns_2(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            code = cli.main(["bogus"])
        self.assertEqual(code, 2)
        self.assertIn("unknown subcommand", buf.getvalue())

    def test_check_with_no_path_argument_defaults_to_current_directory(self):
        cwd = os.getcwd()
        repo = _fixture({"Makefile": _MK_RUFF_MYPY})
        os.chdir(repo)
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = cli.main(["check"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(buf.getvalue()), {"cicd": []})
        finally:
            os.chdir(cwd)

    def test_entrypoint_subprocess_unknown_subcommand_is_clean_exit_2(self):
        result = subprocess.run(
            [*_ENTRYPOINT, "bogus"], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)


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


class TestGateRegistration(unittest.TestCase):
    """The sibling docker/precommit suites' gate-registration checks,
    retargeted at this skill."""

    def test_makefile_registers_module_and_package(self):
        with open(_MAKEFILE_PATH, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("tests.test_ai_kit_project_rules_cicd", text)
        self.assertIn("skills/ai-kit-project-rules-cicd/", text)

    def test_ruff_and_py_compile_match_package_path(self):
        for hook_id in ("ruff", "py-compile"):
            regex = _precommit_hook_files_regex(hook_id)
            self.assertIsNotNone(
                re.match(regex, _CLI_PY_CANDIDATE),
                f"{_CLI_PY_CANDIDATE} did not match {hook_id} files: {regex}",
            )
        entry_block = _precommit_hook_block("unittest")
        match = re.search(r"^\s*entry:\s*(.+)$", entry_block, re.MULTILINE)
        self.assertIsNotNone(match, "no entry: value for hook unittest")
        self.assertIn("tests.test_ai_kit_project_rules_cicd", match.group(1))

    def test_pyright_include_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        include = data["tool"]["pyright"]["include"]
        self.assertIn("skills/ai-kit-project-rules-cicd", include)

    def test_vulture_paths_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        paths = data["tool"]["vulture"]["paths"]
        self.assertIn("skills/ai-kit-project-rules-cicd", paths)


_MK_RUFF_MYPY_TASK1 = (
    "ruff:\n\tuv run ruff check .\n\n"
    "mypy:\n\tuv run mypy .\n"
)

_WF_LINT_AND_TYPES = (
    "name: ci\n"
    "on:\n"
    "  push:\n"
    "jobs:\n"
    "  lint:\n"
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "    - uses: actions/checkout@v4\n"
    "      with:\n"
    "        path: ruff check .\n"
    "    - name: Lint\n"
    "      run: ruff check .\n"
    "    - name: Types\n"
    "      run: |\n"
    "        mypy .\n"
    "        make mypy\n"
)


class TestGitHubReaderShapes(unittest.TestCase):
    """Plan 14-02 Task 1's <behavior> cases: the GitHub Actions
    sequence-of-mappings reader, its `run:` scalar/block-scalar forms, and
    the `uses:` exclusion (D-C14, D-C17, T-14-13, T-14-14, T-14-16, T-14-17)."""

    def test_run_scalar_step_is_flagged_against_a_matching_makefile_target(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY_TASK1,
                ".github/workflows/ci.yml": (
                    "jobs:\n  lint:\n    steps:\n    - run: ruff check .\n"
                ),
            }
        )
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding["ci_file"], ".github/workflows/ci.yml")
        self.assertEqual(finding["job"], "lint")
        self.assertEqual(finding["reuse_command"], "make ruff")
        self.assertNotIn("target", finding)

    def test_run_step_calling_make_target_yields_no_findings(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY_TASK1,
                ".github/workflows/ci.yml": (
                    "jobs:\n  lint:\n    steps:\n    - run: make ruff\n"
                ),
            }
        )
        self.assertEqual(_findings(repo), [])

    def test_block_scalar_run_two_direct_one_reuse_yields_two_findings_in_line_order(
        self,
    ):
        wf = (
            "jobs:\n"
            "  j:\n"
            "    steps:\n"
            "    - run: |\n"
            "        ruff check .\n"
            "        make ruff\n"
            "        mypy .\n"
        )
        repo = _fixture({"Makefile": _MK_RUFF_MYPY_TASK1, ".github/workflows/ci.yml": wf})
        findings = _findings(repo)
        self.assertEqual([f["command"] for f in findings], ["ruff check .", "mypy ."])

    def test_uses_step_with_and_without_with_block_contributes_no_commands(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY_TASK1,
                ".github/workflows/ci.yml": (
                    "jobs:\n"
                    "  j:\n"
                    "    steps:\n"
                    "    - uses: actions/checkout@v4\n"
                    "    - uses: actions/setup-python@v5\n"
                    "      with:\n"
                    "        path: ruff check .\n"
                ),
            }
        )
        self.assertEqual(_findings(repo), [])

    def test_two_jobs_yield_findings_in_job_then_step_order(self):
        wf = (
            "jobs:\n"
            "  b-job:\n"
            "    steps:\n"
            "    - run: ruff check .\n"
            "  a-job:\n"
            "    steps:\n"
            "    - run: mypy .\n"
        )
        repo = _fixture({"Makefile": _MK_RUFF_MYPY_TASK1, ".github/workflows/ci.yml": wf})
        findings = _findings(repo)
        self.assertEqual([f["job"] for f in findings], ["b-job", "a-job"])

    def test_job_and_step_name_produce_the_d_c17_job_field(self):
        repo = _fixture(
            {"Makefile": _MK_RUFF_MYPY_TASK1, ".github/workflows/ci.yml": _WF_LINT_AND_TYPES}
        )
        findings = _findings(repo)
        self.assertEqual([f["job"] for f in findings], ["lint / Lint", "lint / Types"])

    def test_step_with_no_name_key_uses_bare_job_key(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY_TASK1,
                ".github/workflows/ci.yml": (
                    "jobs:\n  j:\n    steps:\n    - run: ruff check .\n"
                ),
            }
        )
        findings = _findings(repo)
        self.assertEqual(findings[0]["job"], "j")


class TestGitHubDiscoveryAndGate(unittest.TestCase):
    """Discovery agrees with D-C1's already-shipped gate on every extension
    and depth (D-C1's key-links entry)."""

    def test_yml_extension_is_discovered(self):
        repo = _fixture(
            {".github/workflows/ci.yml": "jobs:\n  j:\n    steps:\n    - run: a\n"}
        )
        self.assertEqual(ci_parse.discover_ci_files(repo), [".github/workflows/ci.yml"])

    def test_yaml_extension_is_discovered(self):
        repo = _fixture(
            {".github/workflows/ci.yaml": "jobs:\n  j:\n    steps:\n    - run: a\n"}
        )
        self.assertEqual(ci_parse.discover_ci_files(repo), [".github/workflows/ci.yaml"])

    def test_non_yaml_workflow_entry_is_not_discovered(self):
        repo = _fixture({".github/workflows/README.md": "# not yaml\n"})
        self.assertEqual(ci_parse.discover_ci_files(repo), [])

    def test_nested_workflow_file_is_not_discovered(self):
        repo = _fixture(
            {".github/workflows/sub/deep.yml": "jobs:\n  j:\n    steps:\n    - run: a\n"}
        )
        self.assertEqual(ci_parse.discover_ci_files(repo), [])
        self.assertFalse(ci_parse.repo_has_ci_config(repo))

    def test_gitlab_files_precede_workflow_files_sorted_by_name(self):
        repo = _fixture(
            {
                ".gitlab-ci.yml": "j:\n  script:\n  - x\n",
                ".github/workflows/b.yml": "jobs:\n  j:\n    steps:\n    - run: a\n",
                ".github/workflows/a.yml": "jobs:\n  j:\n    steps:\n    - run: a\n",
            }
        )
        self.assertEqual(
            ci_parse.discover_ci_files(repo),
            [".gitlab-ci.yml", ".github/workflows/a.yml", ".github/workflows/b.yml"],
        )


class TestCrossPlatformDeterminism(unittest.TestCase):
    """D-C13's ordering and determinism, now across both platforms."""

    def test_gitlab_then_workflow_files_and_two_runs_agree(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY_TASK1,
                ".gitlab-ci.yml": "gl-job:\n  script:\n  - ruff check .\n",
                ".github/workflows/b.yml": "jobs:\n  j:\n    steps:\n    - run: mypy .\n",
                ".github/workflows/a.yml": "jobs:\n  j:\n    steps:\n    - run: mypy .\n",
            }
        )
        findings = _findings(repo)
        self.assertEqual(
            [f["ci_file"] for f in findings],
            [".gitlab-ci.yml", ".github/workflows/a.yml", ".github/workflows/b.yml"],
        )
        first = json.dumps(cli.check(repo), sort_keys=False)
        second = json.dumps(cli.check(repo), sort_keys=False)
        self.assertEqual(first, second)

    def test_no_workflow_file_is_scanned_twice(self):
        repo = _fixture(
            {
                "Makefile": _MK_RUFF_MYPY_TASK1,
                ".github/workflows/ci.yml": (
                    "jobs:\n  j:\n    steps:\n    - run: ruff check .\n"
                ),
            }
        )
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)


class TestGitHubDegradation(unittest.TestCase):
    """Every malformed workflow shape yields a list and never raises."""

    def test_empty_workflow_does_not_raise(self):
        result = list(ci_parse.iter_workflow_command_sites(""))
        self.assertEqual(result, [])

    def test_no_jobs_key_does_not_raise(self):
        result = list(ci_parse.iter_workflow_command_sites("name: ci\non:\n  push:\n"))
        self.assertEqual(result, [])

    def test_jobs_with_no_steps_does_not_raise(self):
        result = list(
            ci_parse.iter_workflow_command_sites("jobs:\n  j:\n    runs-on: ubuntu-latest\n")
        )
        self.assertEqual(result, [])

    def test_tab_indented_workflow_does_not_raise(self):
        text = "jobs:\n\tj:\n\t\tsteps:\n\t\t- run: ruff check .\n"
        result = list(ci_parse.iter_workflow_command_sites(text))
        self.assertIsInstance(result, list)

    def test_unreadable_binary_workflow_yields_no_findings(self):
        repo = tempfile.mkdtemp()
        _write(os.path.join(repo, "Makefile"), _MK_RUFF_MYPY_TASK1)
        os.makedirs(os.path.join(repo, ".github", "workflows"))
        with open(
            os.path.join(repo, ".github", "workflows", "ci.yml"), "wb"
        ) as handle:
            handle.write(b"\xff\xfe\x00 binary, not utf-8\n")
        self.assertEqual(_findings(repo), [])


_CI_RUFF_STEP = "jobs:\n  j:\n    steps:\n    - run: ruff check .\n"


class TestPrecommitReuseSurface(unittest.TestCase):
    """Plan 14-02 Task 2's <behavior> cases: the pre-commit-hook reuse
    surface (D-C15), its D-C4 gate reuse, and D-C16's precedence."""

    def test_local_hook_with_entry_is_flagged_with_pre_commit_run_recommendation(self):
        pc = (
            "repos:\n- repo: local\n  hooks:\n  - id: ruff\n"
            "    entry: ruff check\n    language: system\n"
        )
        repo = _fixture({".pre-commit-config.yaml": pc, ".github/workflows/ci.yml": _CI_RUFF_STEP})
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding["reuse_surface"], "precommit")
        self.assertEqual(finding["reuse_command"], "pre-commit run ruff --all-files")
        self.assertIn("ruff check .", finding["recommendation"])
        self.assertIn("pre-commit run ruff", finding["recommendation"])
        self.assertNotIn("target", finding)

    def test_ci_calling_pre_commit_run_directly_yields_no_findings(self):
        pc = (
            "repos:\n- repo: local\n  hooks:\n  - id: ruff\n"
            "    entry: ruff check\n    language: system\n"
        )
        repo = _fixture(
            {
                ".pre-commit-config.yaml": pc,
                ".github/workflows/ci.yml": (
                    "jobs:\n  j:\n    steps:\n    - run: pre-commit run ruff --all-files\n"
                ),
            }
        )
        self.assertEqual(_findings(repo), [])

    def test_entry_less_upstream_ruff_hook_covers_ci_ruff_check(self):
        pc = (
            "repos:\n- repo: https://github.com/astral-sh/ruff-pre-commit\n"
            "  hooks:\n  - id: ruff\n"
        )
        repo = _fixture({".pre-commit-config.yaml": pc, ".github/workflows/ci.yml": _CI_RUFF_STEP})
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["reuse_command"], "pre-commit run ruff --all-files")

    def test_entry_less_hygiene_hook_covers_its_own_direct_invocation(self):
        pc = "repos:\n- repo: local\n  hooks:\n  - id: trailing-whitespace\n"
        repo = _fixture(
            {
                ".pre-commit-config.yaml": pc,
                ".github/workflows/ci.yml": (
                    "jobs:\n  j:\n    steps:\n    - run: trailing-whitespace .\n"
                ),
            }
        )
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["reuse_command"], "pre-commit run trailing-whitespace --all-files"
        )

    def test_entry_less_unknown_hook_id_admits_nothing(self):
        pc = "repos:\n- repo: local\n  hooks:\n  - id: my-house-style\n"
        repo = _fixture(
            {
                ".pre-commit-config.yaml": pc,
                ".github/workflows/ci.yml": (
                    "jobs:\n  j:\n    steps:\n    - run: my-house-style .\n"
                ),
            }
        )
        self.assertEqual(_findings(repo), [])

    def test_entry_carrying_unknown_tool_is_admitted_via_route_3(self):
        pc = (
            "repos:\n- repo: local\n  hooks:\n  - id: myformatter\n"
            "    entry: myformatter --fix\n    language: system\n"
        )
        repo = _fixture(
            {
                ".pre-commit-config.yaml": pc,
                ".github/workflows/ci.yml": (
                    "jobs:\n  j:\n    steps:\n    - run: myformatter --fix now\n"
                ),
            }
        )
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["reuse_command"], "pre-commit run myformatter --all-files")

    def test_quoted_entry_matches_a_direct_ci_invocation_identically_to_bare(self):
        pc_quoted = (
            'repos:\n- repo: local\n  hooks:\n  - id: ruff\n'
            '    entry: "ruff check"\n    language: system\n'
        )
        pc_bare = pc_quoted.replace('entry: "ruff check"', "entry: ruff check")
        quoted = _fixture(
            {".pre-commit-config.yaml": pc_quoted, ".github/workflows/ci.yml": _CI_RUFF_STEP}
        )
        bare = _fixture(
            {".pre-commit-config.yaml": pc_bare, ".github/workflows/ci.yml": _CI_RUFF_STEP}
        )
        self.assertEqual(_findings(quoted), _findings(bare))
        self.assertEqual(len(_findings(quoted)), 1)

    def test_single_quoted_entry_resolves_to_the_same_identity_as_bare(self):
        pc_single = (
            "repos:\n- repo: local\n  hooks:\n  - id: black\n"
            "    entry: 'black .'\n    language: system\n"
        )
        pc_bare = pc_single.replace("entry: 'black .'", "entry: black .")
        repo_single = _fixture(
            {
                ".pre-commit-config.yaml": pc_single,
                ".github/workflows/ci.yml": (
                    "jobs:\n  j:\n    steps:\n    - run: black .\n"
                ),
            }
        )
        repo_bare = _fixture(
            {
                ".pre-commit-config.yaml": pc_bare,
                ".github/workflows/ci.yml": (
                    "jobs:\n  j:\n    steps:\n    - run: black .\n"
                ),
            }
        )
        self.assertEqual(_findings(repo_single), _findings(repo_bare))

    def test_multi_segment_bare_entry_has_no_identity(self):
        pc = (
            "repos:\n- repo: local\n  hooks:\n  - id: fmt\n"
            "    entry: black . && isort .\n    language: system\n"
        )
        repo = _fixture(
            {
                ".pre-commit-config.yaml": pc,
                ".github/workflows/ci.yml": (
                    "jobs:\n  j:\n    steps:\n    - run: black .\n"
                ),
            }
        )
        self.assertEqual(_findings(repo), [])

    def test_multi_segment_quoted_entry_has_no_identity(self):
        pc = (
            'repos:\n- repo: local\n  hooks:\n  - id: fmt\n'
            '    entry: "black . && isort ."\n    language: system\n'
        )
        repo = _fixture(
            {
                ".pre-commit-config.yaml": pc,
                ".github/workflows/ci.yml": (
                    "jobs:\n  j:\n    steps:\n    - run: black .\n"
                ),
            }
        )
        self.assertEqual(_findings(repo), [])

    def test_shell_one_liner_over_non_tool_command_covers_nothing(self):
        pc = (
            "repos:\n- repo: local\n  hooks:\n  - id: shellish\n"
            '    entry: bash -c "exit 0"\n    language: system\n'
        )
        repo = _fixture(
            {
                ".pre-commit-config.yaml": pc,
                ".github/workflows/ci.yml": (
                    "jobs:\n  j:\n    steps:\n    - run: bash -c \"exit 0\"\n"
                ),
            }
        )
        self.assertEqual(_findings(repo), [])

    def test_makefile_and_hook_collision_recommends_only_the_makefile_target(self):
        mk = "ruff:\n\tuv run ruff check .\n"
        pc = (
            "repos:\n- repo: local\n  hooks:\n  - id: ruff\n"
            "    entry: ruff check\n    language: system\n"
        )
        repo = _fixture(
            {
                "Makefile": mk,
                ".pre-commit-config.yaml": pc,
                ".github/workflows/ci.yml": _CI_RUFF_STEP,
            }
        )
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["reuse_surface"], "makefile")
        self.assertEqual(findings[0]["reuse_command"], "make ruff")
        self.assertNotIn("pre-commit", findings[0]["recommendation"])

    def test_makefile_mypy_and_hook_ruff_each_produce_their_own_finding(self):
        mk = "mypy:\n\tuv run mypy .\n"
        pc = (
            "repos:\n- repo: local\n  hooks:\n  - id: ruff\n"
            "    entry: ruff check\n    language: system\n"
        )
        wf = "jobs:\n  j:\n    steps:\n    - run: ruff check .\n    - run: mypy .\n"
        repo = _fixture(
            {"Makefile": mk, ".pre-commit-config.yaml": pc, ".github/workflows/ci.yml": wf}
        )
        findings = _findings(repo)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["reuse_surface"], "precommit")
        self.assertEqual(findings[1]["reuse_surface"], "makefile")

    def test_absent_precommit_config_leaves_makefile_surface_usable(self):
        repo = _fixture(
            {
                "Makefile": "ruff:\n\tuv run ruff check .\n",
                ".github/workflows/ci.yml": _CI_RUFF_STEP,
            }
        )
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["reuse_surface"], "makefile")

    def test_empty_precommit_config_yields_no_precommit_findings(self):
        repo = _fixture(
            {".pre-commit-config.yaml": "", ".github/workflows/ci.yml": _CI_RUFF_STEP}
        )
        self.assertEqual(_findings(repo), [])

    def test_unreadable_binary_precommit_config_does_not_raise(self):
        repo = tempfile.mkdtemp()
        _write(os.path.join(repo, ".github/workflows/ci.yml"), _CI_RUFF_STEP)
        with open(os.path.join(repo, ".pre-commit-config.yaml"), "wb") as handle:
            handle.write(b"\xff\xfe\x00 binary, not utf-8\n")
        self.assertEqual(_findings(repo), [])


_INTEGRATION_MK = "ruff:\n\tuv run ruff check .\n\nmypy:\n\tuv run mypy .\n"
_INTEGRATION_PC = (
    "repos:\n- repo: local\n  hooks:\n  - id: black\n"
    "    entry: black .\n    language: system\n"
)
_INTEGRATION_GL = "gl-job:\n  script:\n  - ruff check .\n  - black .\n"
_INTEGRATION_WF_A = "jobs:\n  j:\n    steps:\n    - run: mypy .\n"
_INTEGRATION_WF_B = "jobs:\n  j:\n    steps:\n    - run: black .\n"

_INTEGRATION_EXPECTED = [
    {
        "ci_file": ".gitlab-ci.yml",
        "job": "gl-job",
        "command": "ruff check .",
        "tool": "ruff check",
        "reuse_surface": "makefile",
        "reuse_command": "make ruff",
    },
    {
        "ci_file": ".gitlab-ci.yml",
        "job": "gl-job",
        "command": "black .",
        "tool": "black",
        "reuse_surface": "precommit",
        "reuse_command": "pre-commit run black --all-files",
    },
    {
        "ci_file": ".github/workflows/a.yml",
        "job": "j",
        "command": "mypy .",
        "tool": "mypy",
        "reuse_surface": "makefile",
        "reuse_command": "make mypy",
    },
    {
        "ci_file": ".github/workflows/b.yml",
        "job": "j",
        "command": "black .",
        "tool": "black",
        "reuse_surface": "precommit",
        "reuse_command": "pre-commit run black --all-files",
    },
]


def _integration_fixture(reverse_workflow_creation=False):
    repo = tempfile.mkdtemp()
    _write(os.path.join(repo, "Makefile"), _INTEGRATION_MK)
    _write(os.path.join(repo, ".pre-commit-config.yaml"), _INTEGRATION_PC)
    _write(os.path.join(repo, ".gitlab-ci.yml"), _INTEGRATION_GL)
    if reverse_workflow_creation:
        _write(os.path.join(repo, ".github/workflows/b.yml"), _INTEGRATION_WF_B)
        _write(os.path.join(repo, ".github/workflows/a.yml"), _INTEGRATION_WF_A)
    else:
        _write(os.path.join(repo, ".github/workflows/a.yml"), _INTEGRATION_WF_A)
        _write(os.path.join(repo, ".github/workflows/b.yml"), _INTEGRATION_WF_B)
    return repo


class TestIntegrationBothPlatformsBothSurfaces(unittest.TestCase):
    """Task 3(c): the phase's first integration fixture -- every
    combination of platform (GitLab, GitHub Actions) and surface
    (makefile, precommit) fires at least once, asserted field by field in
    D-C13's order. Plan 14-03 extends this fixture with its own two
    surfaces."""

    def test_complete_finding_list_in_declaration_order(self):
        repo = _integration_fixture()
        findings = _findings(repo)
        self.assertEqual(len(findings), len(_INTEGRATION_EXPECTED))
        for finding, expected in zip(findings, _INTEGRATION_EXPECTED, strict=True):
            for key, value in expected.items():
                self.assertEqual(finding[key], value, (key, finding))
            self.assertNotIn("target", finding)

    def test_two_runs_are_byte_identical(self):
        repo = _integration_fixture()
        first = json.dumps(cli.check(repo), sort_keys=False)
        second = json.dumps(cli.check(repo), sort_keys=False)
        self.assertEqual(first, second)

    def test_reverse_filesystem_creation_order_does_not_change_output(self):
        forward = _findings(_integration_fixture(reverse_workflow_creation=False))
        reversed_ = _findings(_integration_fixture(reverse_workflow_creation=True))
        self.assertEqual(forward, reversed_)

    def test_remediate_over_the_integration_fixture(self):
        repo = _integration_fixture()
        payload = cli.remediate(repo)
        self.assertEqual(len(payload["remediate"]), len(_INTEGRATION_EXPECTED))
        for entry in payload["remediate"]:
            self.assertEqual(entry["kind"], "cicd")
            self.assertEqual(entry["id"], "cicd-command-reuse")
            self.assertTrue(entry["auto_apply"])
        self.assertEqual(payload["blocked"], [])


class TestStatedLimitsGitHub(unittest.TestCase):
    """Task 3(c): one method per limit this plan's GitHub Actions reader
    states in its module docstring -- each pins CURRENT behavior with the
    limit named as scope, so plan 14-04's `SKILL.md` can quote a claim
    that is still true."""

    _MK = "ruff:\n\tuv run ruff check .\n"

    def test_uses_step_action_is_never_fetched_or_analyzed(self):
        # Limit: "a `uses:` step's action is never fetched, downloaded,
        # read or analyzed."
        repo = _fixture(
            {
                "Makefile": self._MK,
                ".github/workflows/ci.yml": (
                    "jobs:\n  j:\n    steps:\n    - uses: some-org/some-action@v1\n"
                ),
            }
        )
        self.assertEqual(_findings(repo), [])

    def test_reusable_workflow_reference_is_never_followed(self):
        # Limit: "a `jobs.<id>.uses` reusable workflow reference is
        # likewise never followed."
        repo = _fixture(
            {
                "Makefile": self._MK,
                ".github/workflows/ci.yml": (
                    "jobs:\n  j:\n    uses: org/repo/.github/workflows/reusable.yml@main\n"
                ),
            }
        )
        self.assertEqual(_findings(repo), [])

    def test_if_condition_is_not_evaluated_command_still_read(self):
        # Limit: "`if:` conditions ... are not evaluated, so a command
        # that would never actually run on this platform is still read."
        repo = _fixture(
            {
                "Makefile": self._MK,
                ".github/workflows/ci.yml": (
                    "jobs:\n  j:\n    steps:\n    - if: false\n      run: ruff check .\n"
                ),
            }
        )
        self.assertEqual(len(_findings(repo)), 1)

    def test_matrix_strategy_is_not_expanded(self):
        # Limit: "matrix expansion ... [is] not evaluated" -- a matrixed
        # job's step is read exactly ONCE, never multiplied per matrix
        # cell.
        repo = _fixture(
            {
                "Makefile": self._MK,
                ".github/workflows/ci.yml": (
                    "jobs:\n  j:\n    strategy:\n      matrix:\n        py: [1, 2, 3]\n"
                    "    steps:\n    - run: ruff check .\n"
                ),
            }
        )
        self.assertEqual(len(_findings(repo)), 1)

    def test_defaults_run_at_workflow_and_job_level_contributes_nothing(self):
        # Limit: "`defaults.run` is not evaluated either, at workflow OR
        # job level" -- the finding's command is the literal `run:` text,
        # with no working-directory/shell prefix contribution.
        repo = _fixture(
            {
                "Makefile": self._MK,
                ".github/workflows/ci.yml": (
                    "defaults:\n  run:\n    working-directory: sub\n    shell: bash\n"
                    "jobs:\n  j:\n    defaults:\n      run:\n"
                    "        working-directory: sub2\n        shell: bash\n"
                    "    steps:\n    - run: ruff check .\n"
                ),
            }
        )
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["command"], "ruff check .")

    def test_expression_only_run_has_no_classifiable_tool_token(self):
        # Limit: "`${{ }}` expressions are never resolved, so a step
        # whose command is entirely an expression has no classifiable
        # tool token."
        repo = _fixture(
            {
                "Makefile": self._MK,
                ".github/workflows/ci.yml": (
                    "jobs:\n  j:\n    steps:\n    - run: ${{ steps.x.outputs.cmd }}\n"
                ),
            }
        )
        self.assertEqual(_findings(repo), [])

    def test_sequence_of_mappings_reader_stays_skill_local(self):
        # D-C14: the mapping-item reader has exactly one consumer and is
        # not IMPORTED from -- or delegated to -- the sibling docker
        # skill's compose_parse.py. (`compose_parse` appears only in
        # prose, naming the capability boundary this reader crosses.)
        import ast

        with open(
            os.path.join(
                _REPO,
                "skills",
                "ai-kit-project-rules-cicd",
                "ai_kit_project_rules_cicd",
                "ci_parse.py",
            ),
            encoding="utf-8",
        ) as handle:
            src = handle.read()
        tree = ast.parse(src)
        imported_modules = {
            n.module or ""
            for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom)
        } | {
            alias.name
            for n in ast.walk(tree)
            if isinstance(n, ast.Import)
            for alias in n.names
        }
        self.assertTrue(
            all(
                "compose_parse" not in m and "ai_kit_project_rules_docker" not in m
                for m in imported_modules
            ),
            imported_modules,
        )


if __name__ == "__main__":
    unittest.main()
