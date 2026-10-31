"""Tests for `ai-kit-project-rules-all` (REQ-rules-all, Phase 15 plan 01).

Unit tier: fixture-driven `TestFailureIsolation` (D-02/D-05 degradation paths via small
scripts), `TestAggregate` (SC4 pure-function stubs, zero subprocess calls) and `TestCLI`
(D-04 check==remediate with `dispatch_all` mocked, plus the entry script's usage branches).
The real dispatch against this repo's six checkers lives in
`tests/test_ai_kit_project_rules_all_e2e.py` (e2e tier, 26-08: the agents domain runs the
project-local gsd-core through node).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-all"),
)

from ai_kit_project_rules_all import aggregate, cli, dispatch

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENTRYPOINT = [
    sys.executable,
    os.path.join(_REPO, "skills", "ai-kit-project-rules-all", "ai-kit-project-rules-all.py"),
]


def _skill_resolve_block(skill_name):
    """The fenced bash block of `SKILL.md` that resolves the entrypoint."""
    path = os.path.join(_REPO, "skills", skill_name, "SKILL.md")
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    for block in re.findall(r"```bash\n(.*?)```", text, re.DOTALL):
        if "SKILL_DIR=" in block and "for d in" in block:
            return block
    raise AssertionError(f"{skill_name}/SKILL.md has no entrypoint resolve block")


def _run_block(block, root, skill_dir=None):
    """Run a resolve block under a scratch HOME; `skill_dir` fills its placeholder."""
    if skill_dir is not None:
        block = block.replace("<directory containing this SKILL.md>", skill_dir)
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.path.join(root, "home"),
        "XDG_CONFIG_HOME": os.path.join(root, "xdg"),
    }
    return subprocess.run(
        ["bash", "-c", block], capture_output=True, text=True, env=env, check=False, timeout=30
    )


def _ok(remediate: list[dict] | None = None, blocked: list[dict] | None = None) -> dict:
    """A real sibling `remediate` payload shape: `{"remediate": [...],
    "blocked": [...]}`."""
    return {"remediate": remediate or [], "blocked": blocked or []}


def _failed(domain: str, error: str = "boom", returncode: int | None = 1) -> dict:
    """A D-05 failure-entry marker -- no `"remediate"` key."""
    return {"domain": domain, "status": "failed", "error": error, "returncode": returncode}


def _entry(kind: str, id_: str, criticality: int) -> dict:
    return {"kind": kind, "id": id_, "criticality": criticality}


def _blocked_entry(kind: str, id_: str, criticality: int) -> dict:
    return {"kind": kind, "id": id_, "criticality": criticality, "stacks": []}


def _write_fixture_script(content: str) -> str:
    """A standalone `.py` file under a fresh temp dir, subprocess-invoked
    by `run_domain` exactly like a real sibling entry script -- the
    `resolve_entrypoint`/`SKILL_NAMES` machinery is left untouched; only
    `dispatch.resolve_entrypoint`'s return value is monkeypatched to point
    at this fixture, so `run_domain` still exercises the real subprocess
    path (`subprocess.run` is never mocked)."""
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, "fixture.py")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


class TestFailureIsolation(unittest.TestCase):
    """Task 2's `<behavior>` cases -- D-02/D-05's degradation paths, each
    driven through the real subprocess path against a small fixture
    script rather than a mocked `subprocess` call."""

    def test_nonzero_exit_degrades_to_d05_shape(self):
        fixture = _write_fixture_script("import sys\nsys.exit(1)\n")
        with mock.patch.object(dispatch, "resolve_entrypoint", return_value=fixture):
            result = dispatch.run_domain("cicd", ".")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["domain"], "cicd")
        self.assertEqual(result["returncode"], 1)
        self.assertTrue(result["error"])

    def test_malformed_json_stdout_degrades_to_d05_shape(self):
        fixture = _write_fixture_script("print('not json')\n")
        with mock.patch.object(dispatch, "resolve_entrypoint", return_value=fixture):
            result = dispatch.run_domain("cicd", ".")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["domain"], "cicd")
        self.assertEqual(result["returncode"], 0)
        self.assertIn("json", result["error"].lower())

    def test_timeout_degrades_to_d05_shape(self):
        fixture = _write_fixture_script("import time\ntime.sleep(5)\nprint('{}')\n")
        with (
            mock.patch.object(dispatch, "resolve_entrypoint", return_value=fixture),
            mock.patch.object(dispatch, "DOMAIN_TIMEOUT_SECONDS", 1),
        ):
            result = dispatch.run_domain("cicd", ".")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["domain"], "cicd")
        self.assertIsNone(result["returncode"])
        self.assertIn("timed out", result["error"].lower())

    def test_undecodable_output_degrades_to_d05_shape(self):
        fixture = _write_fixture_script(
            "import sys\nsys.stdout.buffer.write(b'\\xff\\xfe not utf-8')\n"
        )
        with mock.patch.object(dispatch, "resolve_entrypoint", return_value=fixture):
            result = dispatch.run_domain("cicd", ".")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["domain"], "cicd")

    def test_launch_failure_degrades_and_other_domains_still_run(self):
        real_run = subprocess.run
        fixture = _write_fixture_script('print(\'{"remediate": [], "blocked": []}\')\n')

        def run(argv, **kwargs):
            if argv[-2:] == ["remediate", "launch-fails"]:
                raise OSError("exec format error")
            return real_run(argv, **kwargs)

        with (
            mock.patch.object(dispatch, "resolve_entrypoint", return_value=fixture),
            mock.patch.object(dispatch.subprocess, "run", side_effect=run),
        ):
            failed = dispatch.run_domain("cicd", "launch-fails")
            results = dispatch.dispatch_all(".")
        self.assertEqual(failed["status"], "failed")
        self.assertIn("exec format error", failed["error"])
        self.assertEqual(len(results), 6)

    def test_non_object_json_degrades_to_d05_shape(self):
        fixture = _write_fixture_script("print('[]')\n")
        with mock.patch.object(dispatch, "resolve_entrypoint", return_value=fixture):
            result = dispatch.run_domain("cicd", ".")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["domain"], "cicd")


class TestResolveEntrypointAgentsShared(unittest.TestCase):
    """The agents sibling needs `_shared/ai_kit_rules_common` beside its real dir."""

    @staticmethod
    def _install(root: str, name: str, with_shared: bool) -> None:
        os.makedirs(os.path.join(root, "skills", name))
        open(os.path.join(root, "skills", name, f"{name}.py"), "w").close()
        if with_shared:
            os.makedirs(os.path.join(root, "skills", "_shared", "ai_kit_rules_common"))

    def test_candidate_without_shared_skipped_later_good_wins(self):
        name = dispatch.SKILL_NAMES["agents"]
        with (
            tempfile.TemporaryDirectory() as bad,
            tempfile.TemporaryDirectory() as good,
            tempfile.TemporaryDirectory() as home,
        ):
            self._install(bad, name, with_shared=False)
            self._install(good, name, with_shared=True)
            # The checkout-sibling candidate is `bad` (plain copy); the plugin root is `good`.
            fake_file = os.path.join(
                bad, "skills", "ai-kit-project-rules-all", "pkg", "dispatch.py"
            )
            env = {"CLAUDE_PLUGIN_ROOT": good, "HOME": home, "XDG_CONFIG_HOME": home}
            with (
                mock.patch.dict(os.environ, env),
                mock.patch.object(dispatch, "__file__", fake_file),
            ):
                found = dispatch.resolve_entrypoint(name)
                self.assertEqual(found, os.path.join(good, "skills", name, f"{name}.py"))
                # Same plain copy is still bound for a domain that needs no _shared.
                other = dispatch.SKILL_NAMES["makefile"]
                self._install(bad, other, with_shared=False)
                bound = dispatch.resolve_entrypoint(other)
                assert bound is not None
                self.assertTrue(bound.startswith(bad))
            with (
                mock.patch.dict(
                    os.environ, {"CLAUDE_PLUGIN_ROOT": "", "HOME": home, "XDG_CONFIG_HOME": home}
                ),
                mock.patch.object(dispatch, "__file__", fake_file),
            ):
                self.assertIsNone(dispatch.resolve_entrypoint(name))


class TestAggregate(unittest.TestCase):
    """Task 3's `<behavior>` cases (SC4): `aggregate.aggregate()` called
    directly with 6 hand-built fixture dicts -- never `subprocess`, never
    `dispatch_all`."""

    def test_cross_domain_ordering_is_one_global_sort(self):
        domains = {
            "agents": _ok(),
            "makefile": _ok(
                remediate=[_entry("makefile", "mk-a", 1), _entry("makefile", "mk-b", 4)]
            ),
            "precommit": _ok(remediate=[_entry("precommit", "pc-a", 2)]),
            "arch": _ok(remediate=[_entry("arch", "arch-a", 3)]),
            "docker": _ok(),
            "cicd": _ok(),
        }
        report = aggregate.aggregate(domains)
        crits = [entry["criticality"] for entry in report["remediate"]]
        self.assertEqual(crits, [1, 2, 3, 4])

    def test_workflow_kind_alone_gets_hand_off_tag(self):
        domains = {
            "agents": _ok(remediate=[_entry("workflow", "R01", 1)]),
            "makefile": _ok(remediate=[_entry("makefile", "mk-a", 2)]),
            "precommit": _ok(),
            "arch": _ok(),
            "docker": _ok(),
            "cicd": _ok(),
        }
        report = aggregate.aggregate(domains)
        workflow_entries = [e for e in report["remediate"] if e["kind"] == "workflow"]
        other_entries = [e for e in report["remediate"] if e["kind"] != "workflow"]
        self.assertEqual(len(workflow_entries), 1)
        self.assertEqual(workflow_entries[0]["hand_off"], "agent-md-refactor")
        self.assertTrue(other_entries)
        for entry in other_entries:
            self.assertNotIn("hand_off", entry)

    def test_failed_domain_isolated_from_remediate_and_blocked(self):
        domains = {
            "agents": _ok(remediate=[_entry("workflow", "R01", 1)]),
            "makefile": _ok(remediate=[_entry("makefile", "mk-a", 2)]),
            "precommit": _ok(remediate=[_entry("precommit", "pc-a", 3)]),
            "arch": _failed("arch"),
            "docker": _ok(remediate=[_entry("docker", "dk-a", 4)]),
            "cicd": _ok(remediate=[_entry("cicd", "ci-a", 5)]),
        }
        report = aggregate.aggregate(domains)
        self.assertEqual(len(report["failed"]), 1)
        self.assertEqual(report["failed"][0]["domain"], "arch")
        self.assertEqual(report["failed"][0]["status"], "failed")
        self.assertEqual(len(report["remediate"]), 5)
        remediate_kinds = {entry["kind"] for entry in report["remediate"]}
        self.assertNotIn("arch", remediate_kinds)

    def test_payload_without_remediate_key_is_failed_with_its_domain(self):
        domains = {name: _ok() for name in dispatch.DOMAIN_ORDER}
        domains["docker"] = {"blocked": []}
        report = aggregate.aggregate(domains)
        self.assertEqual(report["failed"], [{"blocked": [], "domain": "docker"}])

    def test_blocked_list_combined_and_sorted(self):
        domains = {
            "agents": _ok(),
            "makefile": _ok(blocked=[_blocked_entry("makefile", "mk-b", 5)]),
            "precommit": _ok(),
            "arch": _ok(blocked=[_blocked_entry("arch", "arch-b", 2)]),
            "docker": _ok(),
            "cicd": _ok(),
        }
        report = aggregate.aggregate(domains)
        crits = [entry["criticality"] for entry in report["blocked"]]
        self.assertEqual(crits, [2, 5])


class TestCLI(unittest.TestCase):
    """Task 3's `<behavior>` cases: D-04's check==remediate proof, and the
    entry script's usage/unknown-subcommand branches."""

    def test_check_and_remediate_are_byte_identical_d04(self):
        fixed_domains = {
            "agents": _ok(),
            "makefile": _ok(
                remediate=[_entry("makefile", "mk-a", 1), _entry("makefile", "mk-b", 4)]
            ),
            "precommit": _ok(remediate=[_entry("precommit", "pc-a", 2)]),
            "arch": _ok(remediate=[_entry("arch", "arch-a", 3)]),
            "docker": _ok(),
            "cicd": _ok(),
        }
        with mock.patch.object(dispatch, "dispatch_all", return_value=fixed_domains):
            check_result = cli.check(".")
            remediate_result = cli.remediate(".")
        self.assertEqual(check_result, remediate_result)

    def test_entry_script_unknown_subcommand_and_no_args(self):
        unknown = subprocess.run(
            [*_ENTRYPOINT, "bogus"], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(unknown.returncode, 2)
        self.assertIn("unknown subcommand", unknown.stderr)

        no_args = subprocess.run(_ENTRYPOINT, capture_output=True, text=True, timeout=30)
        self.assertEqual(no_args.returncode, 0)
        self.assertIn("check|remediate", no_args.stdout)


class TestSkillMdActions(unittest.TestCase):
    """The SKILL.md entrypoint block and the AGENTS.md links step run as written."""

    _SKILL = "ai-kit-project-rules-all"
    _DIR = os.path.join(_REPO, "skills", _SKILL)

    def test_block_with_skill_dir_prints_that_entrypoint(self):
        with tempfile.TemporaryDirectory() as root:
            result = _run_block(_skill_resolve_block(self._SKILL), root, self._DIR)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), self._DIR + "/" + self._SKILL + ".py")

    def test_unedited_block_fails_loudly_and_prints_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            result = _run_block(_skill_resolve_block(self._SKILL), root)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("SKILL_DIR", result.stderr)

    def _skill_text(self):
        with open(os.path.join(self._DIR, "SKILL.md"), encoding="utf-8") as handle:
            return handle.read()

    def _agents_block(self):
        for block in re.findall(r"```bash\n(.*?)```", self._skill_text(), re.DOTALL):
            if "for d in" in block and "ai-kit-project-rules-agents.py" in block:
                return block
        self.fail("no agents-sibling resolve block in SKILL.md")

    def test_agents_sibling_block_prefers_the_checkout_sibling(self):
        with tempfile.TemporaryDirectory() as root:
            result = _run_block(self._agents_block(), root, self._DIR)
        agents = "ai-kit-project-rules-agents"
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(
            os.path.realpath(result.stdout.strip()),
            os.path.realpath(os.path.join(_REPO, "skills", agents, agents + ".py")),
        )

    def test_agents_sibling_block_walks_installed_locations(self):
        agents = "ai-kit-project-rules-agents"
        with tempfile.TemporaryDirectory() as root:
            lone = os.path.join(root, "lone", "ai-kit-project-rules-all")
            os.makedirs(lone)
            open(os.path.join(lone, "SKILL.md"), "w", encoding="utf-8").close()
            installed = os.path.join(root, "home", ".claude", "skills", agents)
            os.makedirs(installed)
            open(os.path.join(installed, agents + ".py"), "w", encoding="utf-8").close()
            # A plain copy without a sibling `_shared` cannot import: it is skipped.
            result = _run_block(self._agents_block(), root, lone)
            self.assertEqual(result.stdout, "")
            os.makedirs(
                os.path.join(root, "home", ".claude", "skills", "_shared", "ai_kit_rules_common")
            )
            result = _run_block(self._agents_block(), root, lone)
        self.assertEqual(result.stdout.strip(), os.path.join(installed, agents + ".py"))

    def test_agents_sibling_block_prints_nothing_when_not_installed(self):
        with tempfile.TemporaryDirectory() as root:
            lone = os.path.join(root, "lone", "ai-kit-project-rules-all")
            os.makedirs(lone)
            open(os.path.join(lone, "SKILL.md"), "w", encoding="utf-8").close()
            result = _run_block(self._agents_block(), root, lone)
        self.assertEqual(result.stdout, "")

    def test_steps_2_and_3_use_the_recorded_agents_path_only(self):
        text = self._skill_text()
        self.assertNotIn("<SKILL_DIR>/../ai-kit-project-rules-agents", text)
        self.assertIn("<AGENTS_ENTRYPOINT>", text)

    def test_links_step_command_reports_a_broken_link(self):
        match = re.search(
            r"^ +(AI_KIT_SKIP_GSD_PROBE=1 python3 .*)$", self._skill_text(), re.MULTILINE
        )
        if match is None:
            self.fail("no links-step command in SKILL.md")
        agents = "ai-kit-project-rules-agents"
        entry = os.path.join(_REPO, "skills", agents, agents + ".py")
        with tempfile.TemporaryDirectory() as root:
            repo = os.path.join(root, "repo")
            os.makedirs(repo)
            with open(os.path.join(repo, "AGENTS.md"), "w", encoding="utf-8") as handle:
                handle.write("See [missing](docs/nope.md).\n")
            command = match.group(1).replace("<AGENTS_ENTRYPOINT>", entry)
            command = command.replace("<repo_root>", repo)
            env = {"PATH": os.environ.get("PATH", ""), "HOME": os.path.join(root, "home")}
            result = subprocess.run(
                ["bash", "-c", command], capture_output=True, text=True, env=env, check=False
            )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(len(json.loads(result.stdout)["links"]), 1)


if __name__ == "__main__":
    unittest.main()
