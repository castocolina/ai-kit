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

from ai_kit_project_rules_docker import cli, compose_parse, docker_checker, healthcheck, hot_reload
from ai_kit_rules_common.tool_catalog import HOT_RELOAD_BASELINE_GAPS, HOT_RELOAD_TOOLS

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


# --------------------------------------------------------------------------- #
# Plan 13-02, Task 1 -- the shared YAML-text primitives (D-D8), the
# indentation-aware compose parser (D-D7), and the healthcheck bounds
# check (SC2, D-D9), written before either module existed and confirmed
# to fail for the right reason (ImportError) before being implemented
# against.
# --------------------------------------------------------------------------- #


def _healthcheck_block(interval="5s", timeout="2s", start_period="10s"):
    return (
        "    healthcheck:\n"
        "      test: [CMD, true]\n"
        f"      interval: {interval}\n"
        f"      timeout: {timeout}\n"
        f"      start_period: {start_period}\n"
    )


class TestHealthcheckBoundsNestingAttribution(unittest.TestCase):
    """Two services with DIFFERENT healthcheck values in the same file --
    the fixture shape that catches a parser attributing a nested block
    to the wrong owner. A single-service fixture would pass for that
    bug."""

    def _fixture(self, second_healthcheck):
        return (
            "services:\n"
            "  first:\n"
            "    image: demo\n" + _healthcheck_block() + "  second:\n"
            "    image: demo\n" + second_healthcheck
        )

    def test_second_services_bad_values_produce_three_findings_naming_only_it(self):
        compose = self._fixture(_healthcheck_block("30s", "10s", "40s"))
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = _findings(repo)
            hc_findings = [f for f in findings if f["category"] == "docker-healthcheck-bounds"]
            self.assertEqual(len(hc_findings), 3)
            self.assertTrue(all(f["service"] == "second" for f in hc_findings))
            self.assertEqual(
                sorted(f["key"] for f in hc_findings), ["interval", "start_period", "timeout"]
            )

    def test_second_service_at_exact_boundary_produces_no_finding(self):
        compose = self._fixture(_healthcheck_block("5s", "2s", "10s"))
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = _findings(repo)
            hc_findings = [f for f in findings if f["category"] == "docker-healthcheck-bounds"]
            self.assertEqual(hc_findings, [])


class TestHealthcheckDurationReading(unittest.TestCase):
    """Compound and sub-second duration forms, read against the real
    checker rather than `parse_duration` alone."""

    def test_1m30s_flagged_against_interval_bound(self):
        compose = (
            "services:\n  svc:\n    image: demo\n" + _healthcheck_block(interval="1m30s")
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = [
                f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"
            ]
            self.assertEqual([f["key"] for f in findings], ["interval"])

    def test_1500ms_not_flagged_against_timeout_bound(self):
        compose = (
            "services:\n  svc:\n    image: demo\n" + _healthcheck_block(timeout="1500ms")
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = [
                f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"
            ]
            self.assertEqual(findings, [])


class TestHealthcheckFractionalExclusiveBound(unittest.TestCase):
    """The exclusive bound proven on a FRACTIONAL discriminator: an
    integer-only duration reader fails this method by producing the
    right key with the WRONG issue (unreadable, not out-of-bounds)."""

    def test_interval_5_001s_is_out_of_bounds_not_unreadable(self):
        compose = "services:\n  svc:\n    image: demo\n" + _healthcheck_block(
            interval="5.001s"
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = [
                f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"
            ]
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["issue"], "docker_healthcheck_out_of_bounds")
            self.assertEqual(findings[0]["key"], "interval")
            self.assertEqual(findings[0]["declared"], "5.001s")


class TestHealthcheckUnreadableValue(unittest.TestCase):
    def test_timeout_forever_yields_one_advisory_not_out_of_bounds(self):
        compose = (
            "services:\n  svc:\n    image: demo\n"
            "    healthcheck:\n"
            "      test: [CMD, true]\n"
            "      timeout: forever\n"
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = [
                f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"
            ]
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["issue"], "docker_healthcheck_unreadable")
            self.assertTrue(findings[0]["advisory"])
            self.assertEqual(findings[0]["declared"], "forever")


class TestHealthcheckAbsenceScope(unittest.TestCase):
    """A service with no `healthcheck:` block, and one declaring only
    `test:`, each yield no healthcheck finding."""

    def test_no_healthcheck_block_yields_nothing(self):
        compose = "services:\n  svc:\n    image: demo\n"
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = [
                f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"
            ]
            self.assertEqual(findings, [])

    def test_healthcheck_with_only_test_key_yields_nothing(self):
        compose = (
            "services:\n  svc:\n    image: demo\n"
            "    healthcheck:\n      test: [CMD, true]\n"
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = [
                f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"
            ]
            self.assertEqual(findings, [])

    def test_only_timeout_declared_yields_nothing_declared_values_only(self):
        """D-D9's declared-values-only prohibition, written as a
        regression test: Compose's implicit 30s `interval` exceeds the
        5s bound, so a later 'fix' to flag absent keys makes this fail
        -- the signal to report rather than to proceed."""
        compose = (
            "services:\n  svc:\n    image: demo\n"
            "    healthcheck:\n      test: [CMD, true]\n      timeout: 1s\n"
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = [
                f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"
            ]
            self.assertEqual(findings, [])


class TestHealthcheckFlowMappingStatedLimit(unittest.TestCase):
    """D-D7's flow-mapping limit: a same-line `healthcheck: {...}` body
    yields no finding, does not raise, and -- the half that matters --
    does NOT disturb the NEXT service, which must still be flagged by
    its own name."""

    def test_flow_mapping_healthcheck_unread_and_does_not_swallow_next_service(self):
        compose = (
            "services:\n"
            "  flowy:\n"
            "    image: demo\n"
            "    healthcheck: {interval: 30s, timeout: 10s}\n"
            "  after:\n"
            "    image: demo\n"
            + _healthcheck_block(interval="30s", timeout="10s", start_period="10s")
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = [
                f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"
            ]
            self.assertTrue(all(f["service"] == "after" for f in findings))
            self.assertGreaterEqual(len(findings), 1)


class TestHealthcheckParserDegradation(unittest.TestCase):
    """A truncated compose file, an empty file, and a file of binary
    noise each yield zero services and no finding, and none raises."""

    def test_truncated_services_key_yields_nothing(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), "services:\n")
            findings = [
                f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"
            ]
            self.assertEqual(findings, [])

    def test_empty_compose_file_yields_nothing(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), "")
            findings = [
                f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"
            ]
            self.assertEqual(findings, [])

    def test_binary_noise_compose_file_does_not_raise(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            compose_path = os.path.join(repo, "docker-compose.yml")
            with open(compose_path, "wb") as handle:
                handle.write(b"\xff\xfe\x00 not yaml \xff\n")
            findings = _findings(repo)
            self.assertIsInstance(findings, list)
            hc_findings = [f for f in findings if f["category"] == "docker-healthcheck-bounds"]
            self.assertEqual(hc_findings, [])


class TestComposeParserNestingFixture(unittest.TestCase):
    """`PARSER-NESTING-OK`'s fixture: a top-level `version:`, a top-level
    `volumes:` mapping, an interior comment, and an interior blank line,
    none of which may end a block or become mistaken for a service."""

    _FIXTURE = (
        "version: '3'\n\n"
        "services:\n\n"
        "  # a comment that must not end a block\n"
        "  alpha:\n"
        "    image: a\n"
        "    healthcheck:\n"
        "      interval: 9s\n\n"
        "  beta:\n"
        "    image: b\n"
        "    depends_on:\n"
        "      - alpha\n\n"
        "volumes:\n"
        "  data:\n"
    )

    def test_only_alpha_and_beta_are_services(self):
        svc = dict(compose_parse.iter_services(self._FIXTURE))
        self.assertEqual(sorted(svc), ["alpha", "beta"])

    def test_alpha_healthcheck_interval_read_correctly(self):
        svc = dict(compose_parse.iter_services(self._FIXTURE))
        healthcheck = compose_parse.block_subblock(svc["alpha"], "healthcheck")
        self.assertEqual(compose_parse.block_scalar(healthcheck, "interval"), "9s")

    def test_beta_does_not_inherit_alpha_healthcheck(self):
        svc = dict(compose_parse.iter_services(self._FIXTURE))
        self.assertIsNone(compose_parse.block_subblock(svc["beta"], "healthcheck"))

    def test_beta_depends_on_reads_as_bare_sequence(self):
        svc = dict(compose_parse.iter_services(self._FIXTURE))
        self.assertEqual(compose_parse.block_sequence(svc["beta"], "depends_on"), ["alpha"])


class TestParseDurationExactness(unittest.TestCase):
    def test_readable_forms(self):
        cases = {
            "2s": 2.0,
            "1m30s": 90.0,
            "1500ms": 1.5,
            "1h": 3600.0,
            "0": 0.0,
            "30": 30.0,
            "5.001s": 5.001,
            "0.5": 0.5,
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(healthcheck.parse_duration(raw), expected)

    def test_unreadable_forms_return_none(self):
        for raw in ("", "forever", "2 s", "abc", "5y", None, "10sx"):
            with self.subTest(raw=raw):
                self.assertIsNone(healthcheck.parse_duration(raw))


class TestComposeFilenameListRepointed(unittest.TestCase):
    """D-D6: the applicability gate and discovery read ONE list."""

    def test_gate_and_discovery_share_the_same_tuples(self):
        pool = set(compose_parse.BASE_COMPOSE_FILENAMES) | set(
            compose_parse.LOCAL_DEV_COMPOSE_FILENAMES
        )
        self.assertEqual(len(pool), 8)

    def test_local_dev_only_repo_is_gated_in_and_parsed(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                _makefile_with_targets(docker_checker.DOCKER_TARGET_FAMILY),
            )
            _write(
                os.path.join(repo, "docker-compose.local.yml"),
                "services:\n  api:\n    image: demo\n" + _healthcheck_block(interval="60s"),
            )
            _write(os.path.join(repo, "docker", "local", "README.md"), "# runbook\n")
            findings = [
                f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"
            ]
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["service"], "api")


# --------------------------------------------------------------------------- #
# Plan 13-02, Task 2 -- `depends_on` discipline (SC3, D-D10): all three
# bare-ordering forms, the conforming form, the advisory completion
# condition, the unreadable-condition advisory, and per-entry evaluation.
# --------------------------------------------------------------------------- #


def _depends_on_findings(repo):
    return [f for f in _findings(repo) if f["category"] == "docker-depends-on"]


class TestDependsOnBareOrdering(unittest.TestCase):
    def test_block_sequence_of_two_names_yields_two_bare_findings(self):
        compose = (
            "services:\n  api:\n    image: a\n    depends_on:\n      - db\n      - cache\n"
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = _depends_on_findings(repo)
            self.assertEqual(len(findings), 2)
            self.assertTrue(all(f["issue"] == "docker_depends_on_bare" for f in findings))
            self.assertEqual(sorted(f["depends_on"] for f in findings), ["cache", "db"])

    def test_flow_sequence_yields_the_same_two_findings(self):
        compose = "services:\n  api:\n    image: a\n    depends_on: [db, cache]\n"
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = _depends_on_findings(repo)
            self.assertEqual(len(findings), 2)
            self.assertTrue(all(f["issue"] == "docker_depends_on_bare" for f in findings))
            self.assertEqual(sorted(f["depends_on"] for f in findings), ["cache", "db"])


class TestDependsOnMappingForm(unittest.TestCase):
    def test_service_healthy_on_every_entry_yields_no_finding(self):
        compose = (
            "services:\n  api:\n    image: a\n    depends_on:\n"
            "      db:\n        condition: service_healthy\n"
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            self.assertEqual(_depends_on_findings(repo), [])

    def test_service_started_yields_one_weak_finding(self):
        compose = (
            "services:\n  api:\n    image: a\n    depends_on:\n"
            "      db:\n        condition: service_started\n"
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = _depends_on_findings(repo)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["issue"], "docker_depends_on_weak_condition")

    def test_no_condition_at_all_yields_the_same_weak_issue(self):
        compose = "services:\n  api:\n    image: a\n    depends_on:\n      db:\n"
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = _depends_on_findings(repo)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["issue"], "docker_depends_on_weak_condition")

    def test_completed_successfully_yields_one_advisory_with_auto_apply_false(self):
        compose = (
            "services:\n  api:\n    image: a\n    depends_on:\n"
            "      seed:\n        condition: service_completed_successfully\n"
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = _depends_on_findings(repo)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["issue"], "docker_depends_on_completion_condition")
            self.assertTrue(findings[0]["advisory"])
            rem = cli.remediate(repo)
            entries = [
                e
                for e in rem["remediate"]
                if e["issue"] == "docker_depends_on_completion_condition"
            ]
            self.assertEqual([e["auto_apply"] for e in entries], [False])

    def test_unreadable_condition_token_yields_one_advisory_naming_it(self):
        compose = (
            "services:\n  api:\n    image: a\n    depends_on:\n"
            "      db:\n        condition: ${SOME_CONDITION}\n"
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = _depends_on_findings(repo)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["issue"], "docker_depends_on_unreadable")
            self.assertTrue(findings[0]["advisory"])
            self.assertEqual(findings[0]["depends_on"], "db")

    def test_no_depends_on_at_all_yields_nothing(self):
        compose = "services:\n  api:\n    image: a\n"
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            self.assertEqual(_depends_on_findings(repo), [])

    def test_mixed_conforming_and_bare_across_two_services_flags_only_the_bare_one(self):
        compose = (
            "services:\n"
            "  api:\n    image: a\n    depends_on:\n"
            "      db:\n        condition: service_healthy\n"
            "  worker:\n    image: b\n    depends_on:\n      - db\n"
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = _depends_on_findings(repo)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["service"], "worker")
            self.assertEqual(findings[0]["depends_on"], "db")


class TestDependsOnPerEntryEvaluation(unittest.TestCase):
    """A whole-block search for the conforming condition would pass this
    fixture at zero findings; per-entry evaluation must not."""

    def test_one_correct_entry_does_not_clear_the_other_two(self):
        compose = (
            "services:\n  api:\n    image: a\n    depends_on:\n"
            "      db:\n        condition: service_healthy\n"
            "      cache:\n        condition: service_started\n"
            "      queue:\n"
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = _depends_on_findings(repo)
            self.assertEqual(sorted(f["depends_on"] for f in findings), ["cache", "queue"])


class TestDependsOnSequenceReaderForms(unittest.TestCase):
    """`block_sequence` reads block, flow, and quoted-flow forms
    identically, and does not fire on an absent key."""

    def test_block_flow_and_quoted_flow_forms_read_identically(self):
        block = "image: x\ndepends_on:\n  - db\n  - cache\n"
        flow = "image: x\ndepends_on: [db, cache]\n"
        quoted_flow = "image: x\ndepends_on: [\"db\", 'cache']\n"
        self.assertEqual(compose_parse.block_sequence(block, "depends_on"), ["db", "cache"])
        self.assertEqual(compose_parse.block_sequence(flow, "depends_on"), ["db", "cache"])
        self.assertEqual(
            compose_parse.block_sequence(quoted_flow, "depends_on"), ["db", "cache"]
        )
        self.assertEqual(compose_parse.block_sequence(block, "volumes"), [])


# --------------------------------------------------------------------------- #
# Plan 13-02, Task 3 -- fills out the suite for both checks and the
# parser, proves both checks non-vacuous (mutations applied, observed
# failing, and reverted -- see the plan's SUMMARY for the recorded
# results), and adds multi-file / same-named-service coverage.
# --------------------------------------------------------------------------- #


class TestParserStructuralEdges(unittest.TestCase):
    """Top-level `version:`, a top-level `volumes:` mapping, blank
    lines, comments at several indents, a `---` separator, trailing
    whitespace, and a file with no `services:` key at all -- none of
    which may become a service or end a block early."""

    def test_top_level_version_key_is_not_a_service(self):
        text = "version: '3.8'\nservices:\n  api:\n    image: a\n"
        svc = dict(compose_parse.iter_services(text))
        self.assertNotIn("version", svc)
        self.assertEqual(sorted(svc), ["api"])

    def test_top_level_volumes_mapping_is_not_a_service(self):
        text = "services:\n  api:\n    image: a\nvolumes:\n  data:\n"
        svc = dict(compose_parse.iter_services(text))
        self.assertNotIn("volumes", svc)
        self.assertNotIn("data", svc)

    def test_document_separator_is_skipped_as_noise(self):
        text = "---\nservices:\n  api:\n    image: a\n"
        svc = dict(compose_parse.iter_services(text))
        self.assertEqual(sorted(svc), ["api"])

    def test_comment_lines_at_several_indents_do_not_end_a_block(self):
        text = (
            "services:\n"
            "  # top comment\n"
            "  api:\n"
            "    # nested comment\n"
            "    image: a\n"
            "    healthcheck:\n"
            "      # deeper comment\n"
            "      interval: 9s\n"
        )
        svc = dict(compose_parse.iter_services(text))
        self.assertEqual(sorted(svc), ["api"])
        healthcheck_block = compose_parse.block_subblock(svc["api"], "healthcheck")
        self.assertEqual(compose_parse.block_scalar(healthcheck_block, "interval"), "9s")

    def test_blank_lines_do_not_end_a_block(self):
        text = "services:\n\n  api:\n\n    image: a\n\n"
        svc = dict(compose_parse.iter_services(text))
        self.assertEqual(compose_parse.block_scalar(svc["api"], "image"), "a")

    def test_trailing_whitespace_on_lines_does_not_break_parsing(self):
        text = "services:  \n  api:  \n    image: a  \n"
        svc = dict(compose_parse.iter_services(text))
        self.assertEqual(compose_parse.block_scalar(svc["api"], "image"), "a")

    def test_no_services_key_yields_no_services(self):
        text = "version: '3'\nvolumes:\n  data:\n"
        svc = dict(compose_parse.iter_services(text))
        self.assertEqual(svc, {})


class TestParserNestingThreeServicesMiddleOnly(unittest.TestCase):
    """Three services where only the MIDDLE one declares a nested
    healthcheck block -- catches both an over-greedy and an
    under-greedy block boundary at once."""

    def test_only_middle_service_has_a_healthcheck_block(self):
        text = (
            "services:\n"
            "  first:\n    image: a\n"
            "  middle:\n    image: b\n    healthcheck:\n      interval: 9s\n"
            "  last:\n    image: c\n"
        )
        svc = dict(compose_parse.iter_services(text))
        self.assertEqual(sorted(svc), ["first", "last", "middle"])
        self.assertIsNone(compose_parse.block_subblock(svc["first"], "healthcheck"))
        self.assertIsNone(compose_parse.block_subblock(svc["last"], "healthcheck"))
        middle_hc = compose_parse.block_subblock(svc["middle"], "healthcheck")
        self.assertEqual(compose_parse.block_scalar(middle_hc, "interval"), "9s")
        self.assertEqual(compose_parse.block_scalar(svc["last"], "image"), "c")


class TestBlockAccessorsPairedCoverage(unittest.TestCase):
    """Each accessor's own paired coverage: a present key and an absent
    one, quoted and bare scalars, and a mapping whose keys come back in
    file order."""

    def test_block_scalar_present_and_absent_key(self):
        block = "image: a\n"
        self.assertEqual(compose_parse.block_scalar(block, "image"), "a")
        self.assertIsNone(compose_parse.block_scalar(block, "missing"))

    def test_block_scalar_quoted_and_bare_forms(self):
        block = "a: 'quoted'\nb: bare\n"
        self.assertEqual(compose_parse.block_scalar(block, "a"), "quoted")
        self.assertEqual(compose_parse.block_scalar(block, "b"), "bare")

    def test_block_subblock_present_and_absent_key(self):
        block = "healthcheck:\n  interval: 9s\n"
        self.assertIsNotNone(compose_parse.block_subblock(block, "healthcheck"))
        self.assertIsNone(compose_parse.block_subblock(block, "missing"))

    def test_block_mapping_keys_returned_in_file_order(self):
        block = (
            "depends_on:\n"
            "  zeta:\n    condition: service_healthy\n"
            "  alpha:\n    condition: service_healthy\n"
        )
        self.assertEqual(
            compose_parse.block_mapping_keys(block, "depends_on"), ["zeta", "alpha"]
        )


class TestBlockSequenceScalarItemContract(unittest.TestCase):
    """D-D7: `block_sequence` returns SCALAR items only. A long-form
    volume entry (`- type: bind` / `source:` / `target:`) arrives as
    the single fragment of its own `- ` line, with its continuation
    lines DROPPED -- never merged, never returned as items of their
    own. Plan 13-03's volume classifier is required to treat that
    fragment as UNREADABLE rather than as an absent bind mount; this
    method pins the observed contract that requirement rests on."""

    def test_sequence_of_mappings_entry_yields_one_fragment_and_drops_continuations(self):
        block = "volumes:\n  - type: bind\n    source: ./src\n    target: /app/src\n"
        items = compose_parse.block_sequence(block, "volumes")
        self.assertEqual(items, ["type: bind"])


class TestParserDegradationFull(unittest.TestCase):
    """Empty, whitespace-only, truncated `services:`, binary noise, a
    tab-indented file, and a directory in place of a compose file all
    degrade to a list and never raise."""

    def test_whitespace_only_compose_file_yields_nothing(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), "   \n\t\n  \n")
            self.assertEqual(_depends_on_findings(repo), [])
            self.assertEqual(
                [f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"],
                [],
            )

    def test_tab_indented_file_does_not_raise(self):
        """D-D7 states tab handling as a mis-attribution LIMIT, not a
        guarantee -- assert only that nothing raises, never that a
        tab-indented file parses correctly or produces a specific
        service/finding set (cycle-1 review finding 11). If the
        implementation happens to parse it correctly, that is luck, not
        contract."""
        text = "services:\n\tapi:\n\t\timage: a\n"
        try:
            services = list(compose_parse.iter_services(text))
        except Exception as exc:  # the assertion IS does-not-raise; catch broadly on purpose
            self.fail(f"iter_services raised on tab-indented input: {exc!r}")
        self.assertIsInstance(services, list)
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), text)
            findings = _findings(repo)
            self.assertIsInstance(findings, list)

    def test_directory_in_place_of_compose_file_does_not_raise(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            os.makedirs(os.path.join(repo, "docker-compose.yml"), exist_ok=True)
            findings = _findings(repo)
            self.assertIsInstance(findings, list)
            self.assertEqual(
                [f for f in findings if f["category"] == "docker-healthcheck-bounds"], []
            )

    def test_read_compose_text_on_a_directory_returns_empty_string(self):
        with tempfile.TemporaryDirectory() as repo:
            dir_path = os.path.join(repo, "adir")
            os.makedirs(dir_path, exist_ok=True)
            self.assertEqual(compose_parse.read_compose_text(dir_path), "")


class TestFlowMappingStatedLimitPairedFamily(unittest.TestCase):
    """D-D7's flow-mapping limit, both bodies (`healthcheck: {...}`,
    `depends_on: {...}`), each paired with the containment case that
    proves this is a stated gap and not a parser bug: a SECOND service
    immediately below, written in block form with a real violation,
    must still be flagged with its own name. Plus the accessor-level
    `None`/`[]` contract."""

    def test_depends_on_flow_mapping_body_unread_and_does_not_raise(self):
        compose = (
            "services:\n"
            "  flowy:\n    image: c\n    depends_on: {db: {condition: service_healthy}}\n"
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            self.assertEqual(_depends_on_findings(repo), [])

    def test_depends_on_flow_mapping_does_not_swallow_the_next_service(self):
        compose = (
            "services:\n"
            "  flowy:\n    image: c\n    depends_on: {db: {condition: service_healthy}}\n"
            "  after:\n    image: d\n    depends_on:\n      - db\n"
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            findings = _depends_on_findings(repo)
            self.assertTrue(all(f["service"] == "after" for f in findings))
            self.assertGreaterEqual(len(findings), 1)

    def test_block_subblock_returns_none_for_flow_mapping_healthcheck_key(self):
        block = "healthcheck: {interval: 30s}\n"
        self.assertIsNone(compose_parse.block_subblock(block, "healthcheck"))

    def test_block_mapping_keys_returns_empty_for_flow_mapping_depends_on_key(self):
        block = "depends_on: {db: {condition: service_healthy}}\n"
        self.assertEqual(compose_parse.block_mapping_keys(block, "depends_on"), [])


class TestHealthcheckBoundsPerKeyPaired(unittest.TestCase):
    """Driven from `healthcheck._BOUNDS` itself so the test cannot fall
    out of step with the table: for EACH bound key, one service just
    over its bound and one exactly at it."""

    def test_each_bound_key_over_and_at_boundary(self):
        defaults = {"interval": "5s", "timeout": "2s", "start_period": "10s"}
        for key, bound in healthcheck._BOUNDS:
            with self.subTest(key=key):
                over = dict(defaults)
                over[key] = f"{bound + 1}s"
                at = dict(defaults)
                at[key] = f"{bound}s"

                compose_over = (
                    "services:\n  svc:\n    image: demo\n" + _healthcheck_block(**over)
                )
                with tempfile.TemporaryDirectory() as repo:
                    _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
                    _write(os.path.join(repo, "docker-compose.yml"), compose_over)
                    findings = [
                        f
                        for f in _findings(repo)
                        if f["category"] == "docker-healthcheck-bounds"
                    ]
                    self.assertEqual([f["key"] for f in findings], [key])

                compose_at = (
                    "services:\n  svc:\n    image: demo\n" + _healthcheck_block(**at)
                )
                with tempfile.TemporaryDirectory() as repo:
                    _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
                    _write(os.path.join(repo, "docker-compose.yml"), compose_at)
                    findings = [
                        f
                        for f in _findings(repo)
                        if f["category"] == "docker-healthcheck-bounds"
                    ]
                    self.assertEqual(findings, [])


class TestHealthcheckDeclaredValuesOnlyScopeRegression(unittest.TestCase):
    """D-D9's declared-values-only prohibition is a deliberate scope
    limit -- Compose's own 30s `interval` default exceeds the 5s bound,
    so tightening this check to flag ABSENT keys is a reportable
    proposal, not an executor's fix. Each case here must continue to
    produce nothing; a later 'improvement' failing one of these is the
    correct signal to report rather than to proceed."""

    def test_only_test_key_declared_yields_nothing(self):
        compose = (
            "services:\n  svc:\n    image: demo\n    healthcheck:\n      test: [CMD, true]\n"
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            self.assertEqual(
                [f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"],
                [],
            )

    def test_only_timeout_declared_yields_nothing(self):
        compose = (
            "services:\n  svc:\n    image: demo\n"
            "    healthcheck:\n      test: [CMD, true]\n      timeout: 1s\n"
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            self.assertEqual(
                [f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"],
                [],
            )

    def test_disable_true_yields_nothing_even_with_out_of_bounds_values(self):
        compose = (
            "services:\n  svc:\n    image: demo\n"
            "    healthcheck:\n      disable: true\n      interval: 999s\n"
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            self.assertEqual(
                [f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"],
                [],
            )

    def test_no_healthcheck_block_at_all_yields_nothing(self):
        compose = "services:\n  svc:\n    image: demo\n"
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), compose)
            self.assertEqual(
                [f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"],
                [],
            )


class TestHealthcheckUnreadableReasonField(unittest.TestCase):
    """The unreadable-value advisory, paired with a readable one, plus
    an assertion that its `reason` field distinguishes the case."""

    def test_unreadable_value_finding_carries_reason_readable_pair_does_not_fire(self):
        readable = "services:\n  svc:\n    image: demo\n" + _healthcheck_block(timeout="2s")
        unreadable = (
            "services:\n  svc:\n    image: demo\n" + _healthcheck_block(timeout="banana")
        )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), readable)
            self.assertEqual(
                [f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"],
                [],
            )
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), unreadable)
            findings = [
                f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"
            ]
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["issue"], "docker_healthcheck_unreadable")
            self.assertIn("reason", findings[0])
            self.assertEqual(findings[0]["reason"], "unreadable_duration")


class TestMultiComposeFileCoverage(unittest.TestCase):
    """A repo with BOTH `docker-compose.yml` and
    `docker-compose.override.yml` where each declares a differently-
    named offending service produces findings for both, each naming
    its own file. A one-file implementation passes every other test in
    this plan."""

    def test_base_and_override_files_both_contribute_findings(self):
        base = "services:\n  svc_a:\n    image: a\n" + _healthcheck_block(interval="30s")
        override = "services:\n  svc_b:\n    image: b\n" + _healthcheck_block(interval="30s")
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), base)
            _write(os.path.join(repo, "docker-compose.override.yml"), override)
            findings = [
                f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"
            ]
            self.assertEqual(sorted(f["service"] for f in findings), ["svc_a", "svc_b"])
            by_service = {f["service"]: f["compose_file"] for f in findings}
            self.assertEqual(by_service["svc_a"], "docker-compose.yml")
            self.assertEqual(by_service["svc_b"], "docker-compose.override.yml")

    def test_same_named_service_in_two_files_both_findings_differ_by_file(self):
        text_a = "services:\n  svc:\n    image: a\n" + _healthcheck_block(interval="30s")
        text_b = "services:\n  svc:\n    image: b\n" + _healthcheck_block(timeout="30s")
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), text_a)
            _write(os.path.join(repo, "docker-compose.override.yml"), text_b)
            findings = [
                f for f in _findings(repo) if f["category"] == "docker-healthcheck-bounds"
            ]
            self.assertEqual(len(findings), 2)
            compose_files = sorted(f["compose_file"] for f in findings)
            self.assertEqual(
                compose_files, ["docker-compose.override.yml", "docker-compose.yml"]
            )


class TestDependsOnMultiFileCoverage(unittest.TestCase):
    def test_depends_on_findings_from_two_files_each_name_their_own_file(self):
        text_a = "services:\n  svc:\n    image: a\n    depends_on:\n      - db\n"
        text_b = "services:\n  svc:\n    image: b\n    depends_on:\n      - cache\n"
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "docker-up:\n\techo u\n")
            _write(os.path.join(repo, "docker-compose.yml"), text_a)
            _write(os.path.join(repo, "docker-compose.override.yml"), text_b)
            findings = _depends_on_findings(repo)
            self.assertEqual(len(findings), 2)
            compose_files = sorted(f["compose_file"] for f in findings)
            self.assertEqual(
                compose_files, ["docker-compose.override.yml", "docker-compose.yml"]
            )


class TestDependsOnConditionAccessorContract(unittest.TestCase):
    """Per-dependency condition reading composes `block_subblock` TWICE
    -- once for `depends_on:` itself, once for the dependency name --
    exactly as `depends_on.py` does."""

    def test_condition_scalar_reads_through_nested_subblock_calls(self):
        service_block = "image: a\ndepends_on:\n  db:\n    condition: service_healthy\n"
        depends_on_block = compose_parse.block_subblock(service_block, "depends_on")
        entry_block = compose_parse.block_subblock(depends_on_block, "db")
        self.assertEqual(
            compose_parse.block_scalar(entry_block, "condition"), "service_healthy"
        )

    def test_absent_condition_key_yields_empty_subblock_and_none_scalar(self):
        service_block = "image: a\ndepends_on:\n  db:\n"
        depends_on_block = compose_parse.block_subblock(service_block, "depends_on")
        entry_block = compose_parse.block_subblock(depends_on_block, "db")
        self.assertEqual(entry_block, "")
        self.assertIsNone(compose_parse.block_scalar(entry_block, "condition"))


# ---------------------------------------------------------------------------
# Plan 13-03: hot-reload convention check (ROADMAP Phase 13 SC4, D-D13
# through D-D18). Every fixture below carries a stack marker (`package.
# json`/`pyproject.toml`) at repo root so `detect_stacks` finds `node`/
# `python` and the seeded catalog's `vite`/`node ...` markers actually
# resolve or fail to resolve as intended.
# ---------------------------------------------------------------------------


def _hot_reload_findings(repo_root):
    return [f for f in _findings(repo_root) if f["category"] == "docker-hot-reload"]


def _hot_reload_repo(
    override_text,
    *,
    override_filename="docker-compose.override.yml",
    base_text="services:\n  prod:\n    image: demo\n",
    stack_markers=("package.json", "pyproject.toml"),
):
    repo = tempfile.mkdtemp()
    _write(os.path.join(repo, "docker-compose.yml"), base_text)
    _write(os.path.join(repo, override_filename), override_text)
    for marker in stack_markers:
        content = "{}\n" if marker.endswith(".json") else "[project]\nname = 'x'\n"
        _write(os.path.join(repo, marker), content)
    return repo


class TestHotReloadConformingBindPlusRecognizedCommand(unittest.TestCase):
    def test_bind_mount_and_recognized_command_yields_no_finding(self):
        override = (
            "services:\n"
            "  okvite:\n"
            "    image: demo\n"
            "    volumes:\n"
            "      - ./src:/app/src\n"
            "    command: vite --host 0.0.0.0\n"
        )
        repo = _hot_reload_repo(override)
        self.assertEqual(_hot_reload_findings(repo), [])


class TestHotReloadProductionEntrypointAdvisory(unittest.TestCase):
    """The user's own reported case (13-CONTEXT D-04): a bind mount plus an
    override that is just the production entrypoint, with no watch/reload
    flag, must NOT be reported conforming."""

    def test_bind_mount_plus_production_command_is_advisory_command_not_matched(self):
        override = (
            "services:\n"
            "  prodcmd:\n"
            "    image: demo\n"
            "    volumes:\n"
            "      - ./src:/app/src\n"
            "    command: node dist/server.js\n"
        )
        repo = _hot_reload_repo(override)
        findings = _hot_reload_findings(repo)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f["issue"], "docker_hot_reload_tool_unrecognized")
        self.assertEqual(f.get("reason"), "command_not_matched")
        self.assertIs(f.get("advisory"), True)


class TestHotReloadScriptIndirectionAdvisory(unittest.TestCase):
    def test_script_runner_override_is_advisory_script_indirection(self):
        override = (
            "services:\n"
            "  scripted:\n"
            "    image: demo\n"
            "    volumes:\n"
            "      - ./src:/app/src\n"
            "    command: npm run dev\n"
        )
        repo = _hot_reload_repo(override)
        findings = _hot_reload_findings(repo)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f.get("reason"), "script_indirection")
        self.assertIs(f.get("advisory"), True)
        text = f["recommendation"].lower()
        self.assertTrue("package.json" in text or "makefile" in text, text)


class TestHotReloadMissingBothHalves(unittest.TestCase):
    def test_no_volumes_no_override_names_both_halves(self):
        override = "services:\n  baked:\n    image: demo\n"
        repo = _hot_reload_repo(override)
        findings = _hot_reload_findings(repo)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f["issue"], "docker_hot_reload_convention_missing")
        self.assertNotIn("advisory", f)
        text = f["summary"].lower()
        self.assertIn("no bind mount", text)
        self.assertIn("no command or entrypoint override", text)


class TestHotReloadMissingOverrideHalfOnly(unittest.TestCase):
    def test_bind_mount_present_no_override_names_override_half_only(self):
        override = (
            "services:\n"
            "  mounted:\n"
            "    image: demo\n"
            "    volumes:\n"
            "      - ./src:/app/src\n"
        )
        repo = _hot_reload_repo(override)
        findings = _hot_reload_findings(repo)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f["issue"], "docker_hot_reload_convention_missing")
        text = f["summary"].lower()
        self.assertNotIn("no bind mount", text)
        self.assertIn("no command or entrypoint override", text)


class TestHotReloadNamedVolumeIsMissingNotUnreadable(unittest.TestCase):
    def test_named_volume_only_is_convention_missing(self):
        override = (
            "services:\n"
            "  namedonly:\n"
            "    image: demo\n"
            "    volumes:\n"
            "      - appdata:/app/data\n"
            "    command: node dist/server.js\n"
        )
        repo = _hot_reload_repo(override)
        findings = _hot_reload_findings(repo)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "docker_hot_reload_convention_missing")


class TestHotReloadInterpolatedVolumeIsAdvisory(unittest.TestCase):
    def test_interpolated_volume_source_is_advisory_unreadable(self):
        var = chr(36) + "{SRC_DIR}"
        override = (
            "services:\n"
            "  murky:\n"
            "    image: demo\n"
            "    volumes:\n"
            f"      - {var}:/app/src\n"
        )
        repo = _hot_reload_repo(override)
        findings = _hot_reload_findings(repo)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f["issue"], "docker_hot_reload_tool_unrecognized")
        self.assertEqual(f.get("reason"), "volumes_unreadable")
        self.assertIs(f.get("advisory"), True)


class TestHotReloadAnonymousVolumeIsMissingNotBind(unittest.TestCase):
    """D-D17 rule 1: a bare path with NO colon is an anonymous volume --
    READABLE, never a bind mount -- even though it begins with `/`."""

    def test_bare_path_anonymous_volume_is_convention_missing(self):
        override = (
            "services:\n"
            "  anonvol:\n"
            "    image: demo\n"
            "    volumes:\n"
            "      - /app/data\n"
            "    command: node dist/server.js\n"
        )
        repo = _hot_reload_repo(override)
        findings = _hot_reload_findings(repo)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "docker_hot_reload_convention_missing")

    def test_same_leading_characters_with_separator_is_a_bind_mount(self):
        override = (
            "services:\n"
            "  realbind:\n"
            "    image: demo\n"
            "    volumes:\n"
            "      - /app/data:/app/data\n"
            "    command: vite --host 0.0.0.0\n"
        )
        repo = _hot_reload_repo(override)
        self.assertEqual(_hot_reload_findings(repo), [])


class TestHotReloadLongFormVolumeIsAdvisory(unittest.TestCase):
    """D-D17's descope (cycle-2 review finding 1): a long-form
    (mapping-style) entry is UNREADABLE, never a confident finding in
    either direction."""

    def test_long_form_mapping_style_entry_is_advisory_not_missing_not_conforming(self):
        override = (
            "services:\n"
            "  longform:\n"
            "    image: demo\n"
            "    volumes:\n"
            "      - type: bind\n"
            "        source: ./src\n"
            "        target: /app/src\n"
            "    command: vite --host 0.0.0.0\n"
        )
        repo = _hot_reload_repo(override)
        findings = _hot_reload_findings(repo)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f["issue"], "docker_hot_reload_tool_unrecognized")
        self.assertEqual(f.get("reason"), "volumes_unreadable")


class TestHotReloadMixedStateUnreadableAndMissingOverride(unittest.TestCase):
    """D-D17's mixed-state precedence: `volumes_unreadable` outranks the
    missing-override half even though both are true here."""

    def test_interpolated_volume_and_no_override_is_one_advisory_never_missing(self):
        var = chr(36) + "{SRC_DIR}"
        override = (
            "services:\n"
            "  murky:\n"
            "    image: demo\n"
            "    volumes:\n"
            f"      - {var}:/app/src\n"
        )
        repo = _hot_reload_repo(override)
        findings = _hot_reload_findings(repo)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f["issue"], "docker_hot_reload_tool_unrecognized")
        self.assertEqual(f.get("reason"), "volumes_unreadable")
        self.assertIs(f.get("advisory"), True)
        text = (f["summary"] + " " + f["recommendation"]).lower()
        self.assertNotIn("no bind mount", text)
        self.assertIn("no 'command:' or 'entrypoint:' override", text)


class TestHotReloadReadableBindBesideUnreadableStaysConforming(unittest.TestCase):
    """The mixed state's paired counterpart: one READABLE bind mount
    settles the answer, so an unreadable neighbour must not drag a
    genuinely conforming service into the advisory outcome."""

    def test_one_readable_bind_mount_settles_answer_despite_interpolated_neighbor(self):
        var = chr(36) + "{SRC_DIR}"
        override = (
            "services:\n"
            "  mixed:\n"
            "    image: demo\n"
            "    volumes:\n"
            f"      - {var}:/cache\n"
            "      - ./src:/app/src\n"
            "    command: vite --host 0.0.0.0\n"
        )
        repo = _hot_reload_repo(override)
        self.assertEqual(_hot_reload_findings(repo), [])


class TestHotReloadBaseFileOnlyServiceNeverEvaluated(unittest.TestCase):
    def test_service_defined_only_in_base_compose_file_is_not_evaluated(self):
        repo = tempfile.mkdtemp()
        _write(os.path.join(repo, "docker-compose.yml"), "services:\n  prod:\n    image: demo\n")
        self.assertEqual(_hot_reload_findings(repo), [])


class TestHotReloadStacklessRepoReasonPrecedence(unittest.TestCase):
    """D-D15's fixed reason order end-to-end: `script_indirection` is
    evaluated BEFORE `no_stack_detected`, so a script-runner override in a
    stackless repo keeps `script_indirection` rather than moving to
    `no_stack_detected` -- only the two non-script services move."""

    def test_no_detected_stack_moves_non_script_services_to_no_stack_detected(self):
        override = (
            "services:\n"
            "  okvite:\n"
            "    image: demo\n"
            "    volumes:\n"
            "      - ./src:/app/src\n"
            "    command: vite --host 0.0.0.0\n"
            "  prodcmd:\n"
            "    image: demo\n"
            "    volumes:\n"
            "      - ./src:/app/src\n"
            "    command: node dist/server.js\n"
            "  scripted:\n"
            "    image: demo\n"
            "    volumes:\n"
            "      - ./src:/app/src\n"
            "    command: npm run dev\n"
        )
        repo = _hot_reload_repo(override, stack_markers=())
        findings = _hot_reload_findings(repo)
        reasons = sorted(f.get("reason") for f in findings)
        self.assertEqual(reasons, ["no_stack_detected", "no_stack_detected", "script_indirection"])


# ---------------------------------------------------------------------------
# Plan 13-03 Task 3: fill out coverage for every outcome and every advisory
# reason with paired fixtures, driven from the shared mapping rather than
# hand-listed where possible.
# ---------------------------------------------------------------------------

_STACK_MARKER_FILES = {
    "python": "pyproject.toml",
    "node": "package.json",
    "java": "pom.xml",
    "rust": "Cargo.toml",
    "go": "go.mod",
}


class TestHotReloadOutcomeOneEveryStackWithBaseline(unittest.TestCase):
    """Outcome 1 (conforming), one subtest per stack carrying a baseline --
    driven from `HOT_RELOAD_TOOLS`'s own keys rather than hand-listed, so a
    stack added later is covered automatically."""

    def test_bind_mount_and_first_baseline_marker_conforms_per_stack(self):
        for stack, markers in HOT_RELOAD_TOOLS.items():
            if not markers:
                continue
            with self.subTest(stack=stack):
                command = markers[0]
                override = (
                    "services:\n"
                    "  svc:\n"
                    "    image: demo\n"
                    "    volumes:\n"
                    "      - ./src:/app/src\n"
                    f"    command: '{command}'\n"
                )
                repo = _hot_reload_repo(override, stack_markers=(_STACK_MARKER_FILES[stack],))
                self.assertEqual(_hot_reload_findings(repo), [], (stack, command))


class TestHotReloadMissingBindHalfOnly(unittest.TestCase):
    def test_no_volumes_key_but_override_present_names_bind_half_only(self):
        override = "services:\n  nobind:\n    image: demo\n    command: node dist/server.js\n"
        repo = _hot_reload_repo(override)
        findings = _hot_reload_findings(repo)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f["issue"], "docker_hot_reload_convention_missing")
        text = f["summary"].lower()
        self.assertIn("no bind mount", text)
        self.assertNotIn("no command or entrypoint override", text)

    def test_adding_bind_mount_and_recognized_marker_makes_it_conform(self):
        override = (
            "services:\n"
            "  nobind:\n"
            "    image: demo\n"
            "    volumes:\n"
            "      - ./src:/app/src\n"
            "    command: node dist/server.js --watch\n"
        )
        repo = _hot_reload_repo(override)
        self.assertEqual(_hot_reload_findings(repo), [])


class TestHotReloadOutcomeThreeReasonsPaired(unittest.TestCase):
    """Outcome 3 (not confirmable), one method per reason with its own
    conforming counterpart in the SAME method -- proving each reason's
    fixture discriminates rather than always firing."""

    def test_command_not_matched_reason_paired_with_conforming_counterpart(self):
        missing = (
            "services:\n  svc:\n    image: demo\n    volumes:\n      - ./src:/app/src\n"
            "    command: node dist/server.js\n"
        )
        conforming = missing.replace("node dist/server.js", "vite --host 0.0.0.0")
        bad = _hot_reload_findings(_hot_reload_repo(missing))
        good = _hot_reload_findings(_hot_reload_repo(conforming))
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0].get("reason"), "command_not_matched")
        self.assertEqual(good, [])

    def test_script_indirection_reason_paired_with_conforming_counterpart(self):
        scripted = (
            "services:\n  svc:\n    image: demo\n    volumes:\n      - ./src:/app/src\n"
            "    command: npm run dev\n"
        )
        conforming = scripted.replace("npm run dev", "vite --host 0.0.0.0")
        bad = _hot_reload_findings(_hot_reload_repo(scripted))
        good = _hot_reload_findings(_hot_reload_repo(conforming))
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0].get("reason"), "script_indirection")
        self.assertEqual(good, [])

    def test_interpolated_volume_reason_paired_with_readable_counterpart(self):
        var = chr(36) + "{SRC_DIR}"
        unreadable = (
            "services:\n  svc:\n    image: demo\n    volumes:\n"
            f"      - {var}:/app/src\n    command: vite --host 0.0.0.0\n"
        )
        readable = unreadable.replace(f"{var}:/app/src", "./src:/app/src")
        bad = _hot_reload_findings(_hot_reload_repo(unreadable))
        good = _hot_reload_findings(_hot_reload_repo(readable))
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0].get("reason"), "volumes_unreadable")
        self.assertEqual(good, [])

    def test_stackless_reason_paired_with_stack_detected_counterpart(self):
        override = (
            "services:\n  svc:\n    image: demo\n    volumes:\n      - ./src:/app/src\n"
            "    command: vite --host 0.0.0.0\n"
        )
        stackless = _hot_reload_findings(_hot_reload_repo(override, stack_markers=()))
        stacked = _hot_reload_findings(_hot_reload_repo(override))
        self.assertEqual(len(stackless), 1)
        self.assertEqual(stackless[0].get("reason"), "no_stack_detected")
        self.assertEqual(stacked, [])

    def test_stack_without_baseline_reason_skipped_when_gaps_tuple_empty(self):
        """`HOT_RELOAD_BASELINE_GAPS` is empty today (D-D16), so no
        detectable stack carries an empty marker tuple and this reason is
        unreachable via a real fixture. A skipped, EXPLAINED method is
        honest; silently passing on an empty tuple would be a check that
        does not exist. Kept so a future non-empty gaps tuple gets
        immediate paired coverage rather than a silent blank."""
        if not HOT_RELOAD_BASELINE_GAPS:
            self.skipTest(
                "HOT_RELOAD_BASELINE_GAPS is empty -- no stack has a "
                "deliberately-empty marker tuple today, so "
                "'stack_without_baseline' cannot be reached via a real "
                "detected stack yet."
            )
        gap_stack = HOT_RELOAD_BASELINE_GAPS[0]
        marker_file = _STACK_MARKER_FILES[gap_stack]
        override = (
            "services:\n  svc:\n    image: demo\n    volumes:\n      - ./src:/app/src\n"
            "    command: anything\n"
        )
        repo = _hot_reload_repo(override, stack_markers=(marker_file,))
        findings = _hot_reload_findings(repo)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].get("reason"), "stack_without_baseline")


class TestHotReloadUnreadableVolumePrecedenceFiveCombos(unittest.TestCase):
    """D-D17's mixed-state precedence, all four combinations plus the
    long-form's own mixed-state landing -- a rule about PRECEDENCE, which
    no single method can show."""

    def test_interpolated_source_no_override_is_mixed_state_advisory(self):
        var = chr(36) + "{SRC_DIR}"
        override = f"services:\n  svc:\n    image: demo\n    volumes:\n      - {var}:/app/src\n"
        findings = _hot_reload_findings(_hot_reload_repo(override))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "docker_hot_reload_tool_unrecognized")
        self.assertEqual(findings[0].get("reason"), "volumes_unreadable")

    def test_interpolated_source_with_override_is_the_same_reason(self):
        var = chr(36) + "{SRC_DIR}"
        override = (
            f"services:\n  svc:\n    image: demo\n    volumes:\n      - {var}:/app/src\n"
            "    command: vite --host 0.0.0.0\n"
        )
        findings = _hot_reload_findings(_hot_reload_repo(override))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].get("reason"), "volumes_unreadable")

    def test_long_form_entry_no_override_lands_on_same_mixed_state_result(self):
        override = (
            "services:\n  svc:\n    image: demo\n    volumes:\n"
            "      - type: bind\n        source: ./src\n        target: /app/src\n"
        )
        findings = _hot_reload_findings(_hot_reload_repo(override))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "docker_hot_reload_tool_unrecognized")
        self.assertEqual(findings[0].get("reason"), "volumes_unreadable")

    def test_readable_bind_beside_interpolated_with_recognized_command_conforms(self):
        var = chr(36) + "{SRC_DIR}"
        override = (
            f"services:\n  svc:\n    image: demo\n    volumes:\n      - {var}:/cache\n"
            "      - ./src:/app/src\n    command: vite --host 0.0.0.0\n"
        )
        self.assertEqual(_hot_reload_findings(_hot_reload_repo(override)), [])

    def test_readable_bind_beside_interpolated_with_production_command_is_command_not_matched(self):
        var = chr(36) + "{SRC_DIR}"
        override = (
            f"services:\n  svc:\n    image: demo\n    volumes:\n      - {var}:/cache\n"
            "      - ./src:/app/src\n    command: node dist/server.js\n"
        )
        findings = _hot_reload_findings(_hot_reload_repo(override))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "docker_hot_reload_tool_unrecognized")
        self.assertEqual(findings[0].get("reason"), "command_not_matched")


class TestHotReloadReasonDeterminism(unittest.TestCase):
    def test_mixed_state_reason_is_stable_across_runs(self):
        var = chr(36) + "{SRC_DIR}"
        override = f"services:\n  svc:\n    image: demo\n    volumes:\n      - {var}:/app/src\n"
        repo = _hot_reload_repo(override)
        first = _hot_reload_findings(repo)[0].get("reason")
        second = _hot_reload_findings(repo)[0].get("reason")
        self.assertEqual(first, "volumes_unreadable")
        self.assertEqual(first, second)

    def test_script_indirection_in_stackless_repo_is_stable_and_not_no_stack_detected(self):
        override = (
            "services:\n  svc:\n    image: demo\n    volumes:\n      - ./src:/app/src\n"
            "    command: npm run dev\n"
        )
        repo = _hot_reload_repo(override, stack_markers=())
        first = _hot_reload_findings(repo)[0].get("reason")
        second = _hot_reload_findings(repo)[0].get("reason")
        self.assertEqual(first, "script_indirection")
        self.assertEqual(first, second)


class TestHotReloadRecommendationMarkerBuiltAtRuntime(unittest.TestCase):
    """D-D16's fourth prohibition: a recommendation naming markers must
    JOIN them at runtime from the shared catalog, not from a hand-typed
    example -- so the expected marker is read FROM the live tuple here,
    never typed into the test."""

    def test_command_not_matched_recommendation_names_a_marker_from_the_live_tuple(self):
        override = (
            "services:\n  svc:\n    image: demo\n    volumes:\n      - ./src:/app/src\n"
            "    command: node dist/server.js\n"
        )
        repo = _hot_reload_repo(override)
        findings = _hot_reload_findings(repo)
        text = findings[0]["recommendation"]
        node_markers = HOT_RELOAD_TOOLS["node"]
        self.assertTrue(any(marker in text for marker in node_markers), text)


class TestHotReloadVolumeEntryGrammarFullFamily(unittest.TestCase):
    """D-D17's five ordered rules, each against the private classifier
    directly so every rule has its own neighbor-distinguishing fixture."""

    def test_named_volume_is_readable_non_bind(self):
        self.assertEqual(hot_reload._classify_volume_entry("appdata:/app/data"), "named")

    def test_short_form_with_ro_option_is_bind(self):
        self.assertEqual(hot_reload._classify_volume_entry("./src:/app/src:ro"), "bind")

    def test_interpolated_source_is_unreadable(self):
        var = chr(36) + "{SRC_DIR}"
        self.assertEqual(hot_reload._classify_volume_entry(f"{var}:/app/src"), "interpolated")

    def test_anonymous_no_colon_is_readable_non_bind(self):
        self.assertEqual(hot_reload._classify_volume_entry("/app/data"), "anonymous")

    def test_anonymous_with_relative_dot_path_is_also_readable_non_bind(self):
        self.assertEqual(hot_reload._classify_volume_entry("./cache"), "anonymous")

    def test_long_form_fragment_is_unreadable(self):
        self.assertEqual(hot_reload._classify_volume_entry("type: bind"), "not_short_form")


class TestHotReloadEntrypointCountsAsOverride(unittest.TestCase):
    """`entrypoint:` counts as an override exactly as `command:` does, in
    both scalar and sequence form."""

    def test_entrypoint_scalar_counts_as_override(self):
        override = (
            "services:\n  svc:\n    image: demo\n    volumes:\n      - ./src:/app/src\n"
            "    entrypoint: vite --host 0.0.0.0\n"
        )
        self.assertEqual(_hot_reload_findings(_hot_reload_repo(override)), [])

    def test_entrypoint_sequence_form_counts_as_override(self):
        override = (
            "services:\n  svc:\n    image: demo\n    volumes:\n      - ./src:/app/src\n"
            "    entrypoint:\n      - vite\n      - --host\n      - 0.0.0.0\n"
        )
        self.assertEqual(_hot_reload_findings(_hot_reload_repo(override)), [])

    def test_command_sequence_form_counts_as_override(self):
        override = (
            "services:\n  svc:\n    image: demo\n    volumes:\n      - ./src:/app/src\n"
            "    command:\n      - vite\n      - --host\n      - 0.0.0.0\n"
        )
        self.assertEqual(_hot_reload_findings(_hot_reload_repo(override)), [])


class TestHotReloadScopeDefinedInBothFilesEvaluatedOnceFromLocalDev(unittest.TestCase):
    def test_service_in_both_base_and_override_is_evaluated_once_from_local_dev(self):
        base = "services:\n  svc:\n    image: demo\n"
        override = (
            "services:\n  svc:\n    image: demo\n    volumes:\n      - ./src:/app/src\n"
            "    command: vite --host 0.0.0.0\n"
        )
        repo = _hot_reload_repo(override, base_text=base)
        self.assertEqual(_hot_reload_findings(repo), [])

    def test_service_in_both_files_missing_convention_produces_exactly_one_finding(self):
        base = "services:\n  svc:\n    image: demo\n"
        override = "services:\n  svc:\n    image: demo\n"
        repo = _hot_reload_repo(override, base_text=base)
        findings = _hot_reload_findings(repo)
        self.assertEqual(len(findings), 1)


class TestHotReloadDegradation(unittest.TestCase):
    def test_empty_local_dev_compose_file_yields_nothing_and_does_not_raise(self):
        repo = tempfile.mkdtemp()
        _write(os.path.join(repo, "docker-compose.yml"), "services:\n  prod:\n    image: demo\n")
        _write(os.path.join(repo, "docker-compose.override.yml"), "")
        self.assertEqual(_hot_reload_findings(repo), [])

    def test_truncated_local_dev_compose_file_yields_nothing_and_does_not_raise(self):
        """Truncated mid the `services:` key header itself -- never
        reaching a real `name:` header -- yields no services at all
        (never a partial one), so no hot-reload finding either."""
        repo = tempfile.mkdtemp()
        _write(os.path.join(repo, "docker-compose.yml"), "services:\n  prod:\n    image: demo\n")
        _write(os.path.join(repo, "docker-compose.override.yml"), "serv")
        self.assertEqual(_hot_reload_findings(repo), [])

    def test_binary_local_dev_compose_file_yields_nothing_and_does_not_raise(self):
        repo = tempfile.mkdtemp()
        _write(os.path.join(repo, "docker-compose.yml"), "services:\n  prod:\n    image: demo\n")
        with open(os.path.join(repo, "docker-compose.override.yml"), "wb") as handle:
            handle.write(b"\x00\x01 not yaml \xff\n")
        self.assertEqual(_hot_reload_findings(repo), [])


class TestHotReloadMutualExclusivityAcrossEveryCase(unittest.TestCase):
    def test_no_service_ever_produces_two_hot_reload_findings(self):
        var = chr(36) + "{SRC_DIR}"
        override = (
            "services:\n"
            "  okvite:\n    image: demo\n    volumes:\n      - ./src:/app/src\n"
            "    command: vite --host 0.0.0.0\n"
            "  prodcmd:\n    image: demo\n    volumes:\n      - ./src:/app/src\n"
            "    command: node dist/server.js\n"
            "  scripted:\n    image: demo\n    volumes:\n      - ./src:/app/src\n"
            "    command: npm run dev\n"
            "  baked:\n    image: demo\n"
            "  mounted:\n    image: demo\n    volumes:\n      - ./src:/app/src\n"
            "  namedonly:\n    image: demo\n    volumes:\n      - appdata:/app/data\n"
            "    command: node dist/server.js\n"
            "  anonvol:\n    image: demo\n    volumes:\n      - /app/data\n"
            "    command: node dist/server.js\n"
            f"  murky:\n    image: demo\n    volumes:\n      - {var}:/app/src\n"
            "  longform:\n    image: demo\n    volumes:\n      - type: bind\n"
            "        source: ./src\n        target: /app/src\n"
            "    command: vite --host 0.0.0.0\n"
        )
        repo = _hot_reload_repo(override)
        findings = _hot_reload_findings(repo)
        service_names = {f["service"] for f in findings}
        self.assertEqual(len(findings), len(service_names))


if __name__ == "__main__":
    unittest.main()
