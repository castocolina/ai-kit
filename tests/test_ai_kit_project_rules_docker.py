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

Task 2's family-tuple coverage is driven from `docker_checker`'s own
`DOCKER_TARGET_FAMILY` tuple rather than eight hand-written methods, so
the suite cannot fall out of step with the checker's own literal list.
"""

import contextlib
import io
import json
import os
import re
import sys
import tempfile
import tomllib
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-docker"),
)

from ai_kit_project_rules_docker import cli, docker_checker

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MAKEFILE_PATH = os.path.join(_REPO, "Makefile")
_PRECOMMIT_PATH = os.path.join(_REPO, ".pre-commit-config.yaml")
_PYPROJECT_PATH = os.path.join(_REPO, "pyproject.toml")
_CLI_PY_CANDIDATE = "skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/cli.py"


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


# --------------------------------------------------------------------------- #
# Task 2 -- paired triggering/non-triggering coverage for every structural
# check, D-D1's normalization negatives, D-D2's ordering, D-D3's identifier
# discipline, degradation, the CLI surface, and gate registration.
# --------------------------------------------------------------------------- #


class TestApplicabilityGateEvidenceClauses(unittest.TestCase):
    """D-D4's four evidence clauses, each proven satisfied on its own, and
    the nested/suffixed shapes that must NOT satisfy the gate -- ai-kit's
    own repo shape is the reason the last two negatives exist."""

    def test_gate_satisfied_by_root_compose_file(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            self.assertNotEqual(_findings(repo), [])

    def test_gate_satisfied_by_root_dockerfile(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Dockerfile"), "FROM scratch\n")
            self.assertNotEqual(_findings(repo), [])

    def test_gate_satisfied_by_root_dockerfile_dev(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Dockerfile.dev"), "FROM scratch\n")
            self.assertNotEqual(_findings(repo), [])

    def test_gate_satisfied_by_root_docker_directory(self):
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, "docker"), exist_ok=True)
            self.assertNotEqual(_findings(repo), [])

    def test_gate_satisfied_by_docker_up_target(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            self.assertNotEqual(_findings(repo), [])

    def test_gate_not_satisfied_by_nested_compose_file(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "sub", "docker-compose.yml"), _COMPOSE_MINIMAL)
            self.assertEqual(_findings(repo), [])

    def test_gate_not_satisfied_by_nested_dockerfile(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "tests", "e2e", "docker", "Dockerfile"), "FROM scratch\n")
            self.assertEqual(_findings(repo), [])

    def test_gate_not_satisfied_by_nested_docker_directory(self):
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, "sub", "docker"), exist_ok=True)
            self.assertEqual(_findings(repo), [])

    def test_gate_not_satisfied_by_e2e_docker_suffixed_target(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "e2e-docker:\n\techo e\n")
            self.assertEqual(_findings(repo), [])


class TestTargetFamilyDrivenFromTuple(unittest.TestCase):
    """Coverage driven from `docker_checker.DOCKER_TARGET_FAMILY` itself,
    never eight hand-written methods, so the suite cannot fall out of
    step with the checker's own literal list."""

    def test_missing_one_target_at_a_time_produces_one_finding_naming_it(self):
        family = docker_checker.DOCKER_TARGET_FAMILY
        for missing in family:
            with self.subTest(missing=missing):
                present = [name for name in family if name != missing]
                with tempfile.TemporaryDirectory() as repo:
                    _write(os.path.join(repo, "Makefile"), _makefile_with_targets(present))
                    _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
                    _write(os.path.join(repo, "docker", "local", "README.md"), "# runbook\n")
                    findings = _findings(repo)
                    target_findings = [
                        f for f in findings if f["issue"] == "docker_target_missing"
                    ]
                    self.assertEqual(len(target_findings), 1)
                    self.assertEqual(target_findings[0]["target"], missing)

    def test_all_eight_targets_present_yields_no_findings(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                _makefile_with_targets(docker_checker.DOCKER_TARGET_FAMILY),
            )
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            _write(os.path.join(repo, "docker", "local", "README.md"), "# runbook\n")
            self.assertEqual(_findings(repo), [])


class TestNormalizationRule(unittest.TestCase):
    """D-D1: equality after normalization (casefold, `_` to `-`) -- the
    negative half is the one that matters, since a prefix or substring
    implementation would accept a renamed target as conforming."""

    def test_underscore_and_uppercase_variant_satisfies_docker_up_slot(self):
        family = docker_checker.DOCKER_TARGET_FAMILY
        rest = [name for name in family if name != "docker-up"]
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"), _makefile_with_targets(["DOCKER_UP", *rest])
            )
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            _write(os.path.join(repo, "docker", "local", "README.md"), "# runbook\n")
            self.assertEqual(_findings(repo), [])

    def test_docker_upload_and_docker_start_are_not_flagged_as_docker_up(self):
        family = docker_checker.DOCKER_TARGET_FAMILY
        rest = [name for name in family if name != "docker-up"]
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                _makefile_with_targets(["docker-upload", "docker-start", "up", *rest]),
            )
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            _write(os.path.join(repo, "docker", "local", "README.md"), "# runbook\n")
            findings = _findings(repo)
            target_findings = [f for f in findings if f["issue"] == "docker_target_missing"]
            self.assertEqual([f["target"] for f in target_findings], ["docker-up"])


class TestOrderingByFamilyTuple(unittest.TestCase):
    """D-D2: the per-target findings come back in the family tuple's own
    declaration order, which disagrees with alphabetical order, and two
    runs over the same fixture produce identical output."""

    def test_missing_targets_ordered_by_family_tuple_not_alphabetically(self):
        family = docker_checker.DOCKER_TARGET_FAMILY
        self.assertNotEqual(list(family), sorted(family))
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "test:\n\techo t\n")
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            _write(os.path.join(repo, "docker", "local", "README.md"), "# runbook\n")
            findings = _findings(repo)
            target_findings = [f for f in findings if f["issue"] == "docker_target_missing"]
            self.assertEqual([f["target"] for f in target_findings], list(family))

    def test_repeated_runs_produce_identical_order(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "test:\n\techo t\n")
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            first = _findings(repo)
            second = _findings(repo)
            self.assertEqual(first, second)


class TestRunbookPaired(unittest.TestCase):
    """D-D5's runbook check, both halves, plus the content-naming
    recommendation the design spec requires."""

    def test_runbook_missing_produces_one_finding(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                _makefile_with_targets(docker_checker.DOCKER_TARGET_FAMILY),
            )
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            findings = _findings(repo)
            runbook_findings = [f for f in findings if f["issue"] == "docker_runbook_missing"]
            self.assertEqual(len(runbook_findings), 1)

    def test_runbook_present_produces_no_finding(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                _makefile_with_targets(docker_checker.DOCKER_TARGET_FAMILY),
            )
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            _write(os.path.join(repo, "docker", "local", "README.md"), "# runbook\n")
            findings = _findings(repo)
            runbook_findings = [f for f in findings if f["issue"] == "docker_runbook_missing"]
            self.assertEqual(runbook_findings, [])

    def test_runbook_recommendation_names_required_content(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                _makefile_with_targets(docker_checker.DOCKER_TARGET_FAMILY),
            )
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            findings = _findings(repo)
            runbook_finding = next(f for f in findings if f["issue"] == "docker_runbook_missing")
            recommendation = runbook_finding["recommendation"]
            lowered = recommendation.lower()
            self.assertIn("network", lowered)
            self.assertIn("secret", lowered)
            self.assertIn(".env", recommendation)
            self.assertIn("worktree", lowered)


class TestIdentifierDiscipline(unittest.TestCase):
    """D-D3, from both sides: `remediation.py:88`'s
    `finding.get("target", finding.get("category"))` precedence is why the
    target findings must carry `target` and the runbook finding must not."""

    def test_target_findings_carry_target_key_with_missing_name(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "test:\n\techo t\n")
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            _write(os.path.join(repo, "docker", "local", "README.md"), "# runbook\n")
            findings = _findings(repo)
            target_findings = [f for f in findings if f["issue"] == "docker_target_missing"]
            for finding in target_findings:
                self.assertIn("target", finding)
            self.assertEqual(
                {f["target"] for f in target_findings}, set(docker_checker.DOCKER_TARGET_FAMILY)
            )

    def test_runbook_finding_lacks_target_key(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                _makefile_with_targets(docker_checker.DOCKER_TARGET_FAMILY),
            )
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            findings = _findings(repo)
            runbook_finding = next(f for f in findings if f["issue"] == "docker_runbook_missing")
            self.assertNotIn("target", runbook_finding)

    def test_remediate_payload_target_ids_are_distinct(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "test:\n\techo t\n")
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            result = cli.remediate(repo)
            target_entries = [
                e for e in result["remediate"] if e["issue"] == "docker_target_missing"
            ]
            ids = [e["id"] for e in target_entries]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(len(ids), len(docker_checker.DOCKER_TARGET_FAMILY))

    def test_remediate_payload_runbook_id_equals_category(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                _makefile_with_targets(docker_checker.DOCKER_TARGET_FAMILY),
            )
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            result = cli.remediate(repo)
            runbook_entries = [
                e for e in result["remediate"] if e["issue"] == "docker_runbook_missing"
            ]
            self.assertEqual(len(runbook_entries), 1)
            self.assertEqual(runbook_entries[0]["id"], "docker-local-runbook")


class TestDegradation(unittest.TestCase):
    """A repo with no `Makefile`, an empty one, an unreadable binary one,
    and (platform permitting) a chmod-000 one all return a list and never
    raise. D-D23's wrap is proven non-vacuous by the paired direct-call
    method, which pins that the SHARED parser still raises on the same
    binary fixture."""

    def test_gate_satisfied_no_makefile_returns_full_family_and_runbook(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            findings = _findings(repo)
            self.assertIsInstance(findings, list)
            self.assertEqual(len(findings), len(docker_checker.DOCKER_TARGET_FAMILY) + 1)

    def test_gate_satisfied_empty_makefile_returns_full_family_and_runbook(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "")
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            findings = _findings(repo)
            self.assertIsInstance(findings, list)
            self.assertEqual(len(findings), len(docker_checker.DOCKER_TARGET_FAMILY) + 1)

    def test_unreadable_binary_makefile_returns_list_without_raising(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            makefile_path = os.path.join(repo, "Makefile")
            with open(makefile_path, "wb") as handle:
                handle.write(b"\xff\xfe\x00 binary, not utf-8\n")
            findings = _findings(repo)
            self.assertIsInstance(findings, list)
            self.assertEqual(len(findings), len(docker_checker.DOCKER_TARGET_FAMILY) + 1)

    def test_shared_parser_raises_directly_on_binary_makefile_fixture(self):
        from ai_kit_rules_common.makefile_parse import parse_makefile_targets

        with tempfile.TemporaryDirectory() as repo:
            makefile_path = os.path.join(repo, "Makefile")
            with open(makefile_path, "wb") as handle:
                handle.write(b"\xff\xfe\x00 binary, not utf-8\n")
            with self.assertRaises((OSError, UnicodeDecodeError)):
                parse_makefile_targets(makefile_path)

    def test_chmod_000_makefile_returns_list_without_raising_or_is_skipped(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest(
                "running as root: chmod 000 does not block root's own reads, "
                "so this fixture cannot exercise the permission-denied path"
            )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "docker-compose.yml"), _COMPOSE_MINIMAL)
            makefile_path = os.path.join(repo, "Makefile")
            _write(makefile_path, "docker-up:\n\techo x\n")
            os.chmod(makefile_path, 0o000)
            try:
                findings = _findings(repo)
                self.assertIsInstance(findings, list)
            finally:
                os.chmod(makefile_path, 0o644)


class TestCliSurface(unittest.TestCase):
    """THIS skill's own CLI binding only -- the shared builder's own
    behavior is covered in the shared suite."""

    def test_check_returns_single_key_payload(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "test:\n\techo t\n")
            result = cli.check(repo)
            self.assertEqual(list(result), ["docker"])

    def test_remediate_returns_two_key_payload(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "test:\n\techo t\n")
            result = cli.remediate(repo)
            self.assertEqual(sorted(result), ["blocked", "remediate"])

    def test_unknown_subcommand_returns_2(self):
        self.assertEqual(cli.main(["bogus"]), 2)

    def test_check_with_no_path_argument_defaults_to_current_directory(self):
        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as repo:
            os.chdir(repo)
            try:
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    returncode = cli.main(["check"])
                self.assertEqual(returncode, 0)
                payload = json.loads(buf.getvalue())
                self.assertEqual(payload, {"docker": []})
            finally:
                os.chdir(old_cwd)


class TestGateRegistration(unittest.TestCase):
    """The sibling class's checks, retargeted at this skill."""

    def test_makefile_registers_module_and_package(self):
        with open(_MAKEFILE_PATH, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("tests.test_ai_kit_project_rules_docker", text)
        self.assertIn("skills/ai-kit-project-rules-docker/", text)

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
        self.assertIn("tests.test_ai_kit_project_rules_docker", match.group(1))

    def test_pyright_include_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        include = data["tool"]["pyright"]["include"]
        self.assertIn("skills/ai-kit-project-rules-docker", include)

    def test_vulture_paths_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        paths = data["tool"]["vulture"]["paths"]
        self.assertIn("skills/ai-kit-project-rules-docker", paths)


if __name__ == "__main__":
    unittest.main()
