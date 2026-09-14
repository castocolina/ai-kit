"""Tests for `ai-kit-project-rules-arch` (REQ-rules-arch, Phase 12 plan 01).

Task 1's tracer contract: the six `<behavior>` cases below, written before
the checker existed and confirmed to fail for the right reason (ImportError
-- the package did not exist yet), then implemented against until they
passed. Task 2 fills the suite out with paired triggering/non-triggering
fixtures for every structural check, the D-A1 shape rule per-alternative,
gate registration, and the shared suite's grown `STRUCTURAL_KINDS` tuple.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-arch"),
)

from ai_kit_project_rules_arch import arch_checker, cli  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def _findings(repo_root):
    return arch_checker.check_arch_rules(repo_root)


def _issues(repo_root):
    return [f["issue"] for f in _findings(repo_root)]


class TestTracerChainingWithoutExistence(unittest.TestCase):
    """A fixture repo whose Makefile declares `arch-test:` with a recipe and
    `test: test-unit` (no arch-test prerequisite, no recipe mention) yields
    exactly one finding whose `issue` is the not-chained one, and no
    target-missing finding."""

    def test_unchained_arch_test_target_flags_chaining_only(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test: test-unit\n\ntest-unit:\n\techo t\n\narch-test:\n\techo a\n",
            )
            issues = _issues(repo)
            self.assertEqual(issues, ["arch_test_not_chained"])


class TestTracerExistenceWithoutChaining(unittest.TestCase):
    """A fixture repo whose Makefile declares `test: test-unit` and no
    arch-test-shaped target at all yields exactly one finding whose `issue`
    is the target-missing one, and no chaining finding (D-A4's gate)."""

    def test_no_arch_test_target_flags_existence_only(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test: test-unit\n\ntest-unit:\n\techo t\n",
            )
            issues = _issues(repo)
            self.assertEqual(issues, ["arch_test_target_missing"])


class TestTracerAiKitOwnRepo(unittest.TestCase):
    """ai-kit's own repository root yields neither of those two `issue`
    values (ROADMAP Phase 12 SC1)."""

    def test_own_repo_produces_no_arch_findings(self):
        issues = _issues(_REPO)
        self.assertNotIn("arch_test_target_missing", issues)
        self.assertNotIn("arch_test_not_chained", issues)


class TestTracerTransitiveChaining(unittest.TestCase):
    """A fixture repo whose `test` reaches `arch-test` only transitively
    (`test: test-all`, `test-all: unit arch-test`) yields NEITHER finding --
    D-A2 clause (ii)."""

    def test_transitive_prerequisite_is_chained(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test: test-all\n\ntest-all: unit arch-test\n\nunit:\n\techo u\n\n"
                "arch-test:\n\techo a\n",
            )
            self.assertEqual(_findings(repo), [])


class TestTracerRecipeInvocationChaining(unittest.TestCase):
    """A fixture repo whose `test` recipe runs `$(MAKE) arch-test` with no
    prerequisite list yields NEITHER finding -- D-A2 clause (iii)."""

    def test_recipe_invocation_is_chained(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test:\n\t$(MAKE) arch-test\n\narch-test:\n\techo a\n",
            )
            self.assertEqual(_findings(repo), [])


class TestTracerShapeAnchoring(unittest.TestCase):
    """A fixture repo whose only candidate target is named `archive` yields
    the target-missing finding -- D-A1's anchoring, proving the shape rule
    is not an unanchored substring match."""

    def test_archive_is_not_arch_test_shaped(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test: test-unit\n\ntest-unit:\n\techo t\n\narchive:\n\techo z\n",
            )
            issues = _issues(repo)
            self.assertEqual(issues, ["arch_test_target_missing"])


class TestCliSurface(unittest.TestCase):
    def test_check_returns_single_key_payload(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "test: test-unit\n\ntest-unit:\n\techo t\n")
            result = cli.check(repo)
            self.assertEqual(list(result), ["arch"])

    def test_remediate_returns_two_key_payload(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "test: test-unit\n\ntest-unit:\n\techo t\n")
            result = cli.remediate(repo)
            self.assertEqual(sorted(result), ["blocked", "remediate"])

    def test_unknown_subcommand_returns_2(self):
        self.assertEqual(cli.main(["bogus"]), 2)


if __name__ == "__main__":
    unittest.main()
