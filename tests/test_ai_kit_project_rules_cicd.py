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

import os
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-cicd"),
)

from ai_kit_project_rules_cicd import cicd_checker

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


if __name__ == "__main__":
    unittest.main()
