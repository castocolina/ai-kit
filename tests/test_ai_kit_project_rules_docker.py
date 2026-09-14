"""Tests for `ai-kit-project-rules-docker` (REQ-rules-docker, Phase 13
plan 01).

Plan 13-01, Task 1's tracer contract: the six `<behavior>` cases in the
`TestTracer*` classes below, written before the checker existed and
confirmed to fail for the right reason (ImportError -- the package did
not exist yet), then implemented against until they passed. Task 2 fills
the suite out with paired triggering/non-triggering fixtures for every
structural check, D-D1's normalization with its prefix/substring
negatives, D-D2's ordering, D-D3's identifier discipline from both sides,
the degradation paths, the CLI surface, and its own gate-registration
class. The shared suite's grown `STRUCTURAL_KINDS` tuple and cross-kind
ordering live in `tests/test_ai_kit_rules_common.py` instead.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-docker"),
)

from ai_kit_project_rules_docker import cli, docker_checker

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def _findings(repo_root):
    return docker_checker.check_docker_rules(repo_root)


def _issues(repo_root):
    return [f["issue"] for f in _findings(repo_root)]


def _makefile_with_targets(names):
    return "".join(f"{name}:\n\techo x\n\n" for name in names)


_COMPOSE_MINIMAL = "services:\n  api:\n    image: demo\n"


class TestTracerFullFamilyConforms(unittest.TestCase):
    """A fixture repo carrying a compose file, all eight family targets,
    and docker/local/README.md yields zero findings."""

    def test_conforming_repo_yields_no_findings(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                _makefile_with_targets(docker_checker.DOCKER_TARGET_FAMILY),
            )
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            _write(os.path.join(repo, "docker", "local", "README.md"), "# runbook\n")
            self.assertEqual(_findings(repo), [])


class TestTracerPartialFamilyAndMissingRunbook(unittest.TestCase):
    """A fixture repo carrying a compose file and only two of the eight
    targets, with no runbook, yields exactly six target-missing findings
    -- one per absent name, each carrying that name -- plus exactly one
    runbook finding."""

    def test_partial_family_yields_six_target_findings_and_one_runbook(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                _makefile_with_targets(["docker-up", "docker-stop"]),
            )
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            findings = _findings(repo)
            target_findings = [f for f in findings if f["issue"] == "docker_target_missing"]
            runbook_findings = [f for f in findings if f["issue"] == "docker_runbook_missing"]
            expected_missing = [
                name
                for name in docker_checker.DOCKER_TARGET_FAMILY
                if name not in ("docker-up", "docker-stop")
            ]
            self.assertEqual([f["target"] for f in target_findings], expected_missing)
            self.assertEqual(len(runbook_findings), 1)
            self.assertNotIn("target", runbook_findings[0])
            self.assertEqual(len(findings), 7)


class TestTracerNoRootDockerEvidence(unittest.TestCase):
    """A fixture repo with a Makefile but no root-level Docker evidence
    of any kind yields zero findings (D-D4's gate)."""

    def test_no_docker_evidence_yields_no_findings(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "test:\n\techo t\n")
            self.assertEqual(_findings(repo), [])


class TestTracerAiKitOwnRepo(unittest.TestCase):
    """ai-kit's own repository root yields zero findings -- the live case
    of the applicability gate."""

    def test_ai_kit_own_repo_yields_no_findings(self):
        self.assertEqual(_findings(_REPO), [])


class TestTracerApplicabilityEdges(unittest.TestCase):
    """A fixture repo whose only Docker evidence is a NESTED
    tests/e2e/docker/Dockerfile, plus a docker-SUFFIXED e2e-docker target,
    yields zero findings; the same fixture with a ROOT Dockerfile added
    yields findings. This pair is D-D4's two edges, and ai-kit's own repo
    is the reason both exist."""

    def test_nested_dockerfile_and_suffixed_target_yield_no_findings(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test:\n\techo t\n\ne2e-docker:\n\techo e\n",
            )
            _write(os.path.join(repo, "tests", "e2e", "docker", "Dockerfile"), "FROM scratch\n")
            self.assertEqual(_findings(repo), [])

    def test_same_fixture_with_root_dockerfile_yields_findings(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test:\n\techo t\n\ne2e-docker:\n\techo e\n",
            )
            _write(os.path.join(repo, "tests", "e2e", "docker", "Dockerfile"), "FROM scratch\n")
            _write(os.path.join(repo, "Dockerfile"), "FROM scratch\n")
            findings = _findings(repo)
            self.assertEqual(len(findings), 9)


class TestTracerDockerDirWithoutMakefile(unittest.TestCase):
    """A fixture repo with a root docker/ directory but no Makefile at
    all yields the full eight target-missing findings plus the runbook
    one -- the gate is satisfied by evidence other than a Makefile, and
    the shared parsers' absent-file behavior carries the rest."""

    def test_docker_dir_without_makefile_yields_nine_findings(self):
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, "docker"), exist_ok=True)
            findings = _findings(repo)
            target_findings = [f for f in findings if f["issue"] == "docker_target_missing"]
            runbook_findings = [f for f in findings if f["issue"] == "docker_runbook_missing"]
            self.assertEqual(len(target_findings), 8)
            self.assertEqual(len(runbook_findings), 1)
            self.assertEqual(len(findings), 9)


if __name__ == "__main__":
    unittest.main()
