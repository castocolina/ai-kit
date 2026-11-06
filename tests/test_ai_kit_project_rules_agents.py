import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-agents"),
)
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-all"),
)

from ai_kit_project_rules_agents import (
    cli,
    remediation,
    rule_checker,
    rules,
    tool_presence,
)
from ai_kit_project_rules_all import aggregate as rules_all_aggregate
from ai_kit_rules_common.tool_catalog import (
    PARALLEL_TEST_COUNT_FLAGS,
    PARALLEL_TEST_GENERIC,
    PARALLEL_TEST_SIGNAL_GROUPS,
)

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MAKEFILE_PATH = os.path.join(_REPO, "Makefile")
_PRECOMMIT_PATH = os.path.join(_REPO, ".pre-commit-config.yaml")
_PYPROJECT_PATH = os.path.join(_REPO, "pyproject.toml")
_CLI_PY_CANDIDATE = "skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py"


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def _skill_resolve_block(skill_name):
    """The fenced bash block of `SKILL.md` that resolves the entrypoint."""
    path = os.path.join(_REPO, "skills", skill_name, "SKILL.md")
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    for block in re.findall(r"```bash\n(.*?)```", text, re.DOTALL):
        if "SKILL_DIR=" in block and "for d in" in block:
            return block
    raise AssertionError(f"{skill_name}/SKILL.md has no entrypoint resolve block")


def _run_block(block, root, skill_dir=None, cwd=None):
    """Run a resolve block under a scratch HOME; `skill_dir` fills its placeholder."""
    if skill_dir is not None:
        block = block.replace("<directory containing this SKILL.md>", skill_dir)
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.path.join(root, "home"),
        "XDG_CONFIG_HOME": os.path.join(root, "xdg"),
    }
    return subprocess.run(
        ["bash", "-c", block], capture_output=True, text=True, env=env, check=False, timeout=30,
        cwd=cwd,
    )


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


def _tool_roots_cover(rel_dir: str, roots: list[str]) -> bool:
    sample = f"{rel_dir.rstrip('/')}/module.py"
    return any(sample == root or sample.startswith(f"{root}/") for root in roots)



class TestToolPresence(unittest.TestCase):
    def test_empty_path_and_repo_all_false(self):
        with tempfile.TemporaryDirectory() as bin_dir, tempfile.TemporaryDirectory() as repo:
            env = scoped_env(bin_dir, repo)
            result = tool_presence.check_tool_presence(
                search_path=env["PATH"], repo_root=repo
            )
            expected = {
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

    @classmethod
    def _require_find(cls, findings, rule_id):
        finding = cls._find(findings, rule_id)
        assert finding is not None
        return finding

    def _always_false_presence(self):
        presence = {"modern-cli": False, "codegraph": False,
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
        self.assertEqual(self._require_find(missing, "R01")["status"], "missing")

        present = rule_checker.check_workflow_rules(
            "All docs are english-only and this is non-negotiable.",
            presence,
            include_present=True,
        )
        self.assertEqual(self._require_find(present, "R01")["status"], "present")

        near = rule_checker.check_workflow_rules(
            "We write docs in english only.", presence, include_present=True
        )
        self.assertEqual(self._require_find(near, "R01")["status"], "near_miss")

    def test_retired_r05_is_absent_and_r06_still_reported(self):
        presence = self._always_false_presence()
        findings = rule_checker.check_workflow_rules(
            "nothing relevant here", presence, include_present=True
        )
        self.assertIsNone(self._find(findings, "R05"))
        self.assertIsNotNone(self._find(findings, "R06"))

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
        self.assertEqual(self._require_find(review_only, "R04")["status"], "near_miss")

        all_groups = rule_checker.check_workflow_rules(
            "we run cross-ai review, cheap-model execution, and "
            "path-agnostic command generation",
            presence,
            include_present=True,
        )
        self.assertEqual(self._require_find(all_groups, "R04")["status"], "present")

        none_present = rule_checker.check_workflow_rules(
            "no relevant text here", presence, include_present=True
        )
        self.assertEqual(self._require_find(none_present, "R04")["status"], "missing")

    def test_r06_tool_scoped_groups_only_require_installed_tools(self):
        presence = self._always_false_presence()
        presence.update(
            {"modern-cli": True, "modern-cli:rg": True, "modern-cli:bat": True}
        )

        rg_only = rule_checker.check_workflow_rules(
            "use ripgrep instead of grep", presence, include_present=True
        )
        r06 = self._require_find(rg_only, "R06")
        self.assertEqual(r06["status"], "near_miss")
        self.assertEqual(r06["missing_tools"], ["bat"])

        both = rule_checker.check_workflow_rules(
            "use ripgrep and bat instead of grep/cat", presence, include_present=True
        )
        r06 = self._require_find(both, "R06")
        self.assertEqual(r06["status"], "present")
        self.assertEqual(r06["missing_tools"], [])

        no_tools = self._always_false_presence()
        findings = rule_checker.check_workflow_rules(
            "use ripgrep and bat instead of grep/cat", no_tools, include_present=True
        )
        self.assertEqual(self._require_find(findings, "R06")["status"], "not_applicable")

    def test_matched_signals_field(self):
        presence = self._always_false_presence()
        findings = rule_checker.check_workflow_rules(
            "we write docs in english only", presence, include_present=True
        )
        r01 = self._require_find(findings, "R01")
        self.assertEqual(r01["status"], "near_miss")
        self.assertTrue(r01["matched_signals"])
        self.assertTrue(set(r01["matched_signals"]) <= set(rules.RULES[0]["signals"]))


class TestCliCheck(unittest.TestCase):
    def test_check_returns_workflow_and_links_keys(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "AGENTS.md"),
                "Some filler text with no relevant rule content elsewhere.",
            )
            result = cli.check(repo)
            # ROADMAP Success Criterion 1's machine-checkable form: `check`
            # stays workflow-only for rule findings. `links` is the separate
            # broken-link key (RUN-11); it is not a second rule kind.
            self.assertEqual(set(result.keys()), {"workflow", "links"})
            self.assertEqual(result["links"], [])
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


def _listing(root):
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            found.append(os.path.relpath(os.path.join(dirpath, name), root))
    return found


class TestLinkHandling(unittest.TestCase):
    def test_image_link_to_binary_png_is_not_decoded(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "AGENTS.md"),
                "![logo](img/logo.png)\n",
            )
            png = os.path.join(repo, "img", "logo.png")
            os.makedirs(os.path.dirname(png))
            with open(png, "wb") as handle:
                handle.write(b"\x89PNG\r\n\x1a\n\x00\x01")
            result = cli.check(repo)
            self.assertEqual(result["links"], [])

    def test_anchored_link_appends_target_text(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "AGENTS.md"),
                "[guide](docs/guide.md#setup)\n",
            )
            _write(
                os.path.join(repo, "docs", "guide.md"),
                "Every commit is one coherent logical commit, after a "
                "compaction pass.",
            )
            result = cli.check(repo)
            self.assertEqual(result["links"], [])
            ids = [f["id"] for f in result["workflow"]]
            self.assertNotIn("R03", ids)

    def test_query_and_title_are_stripped_before_the_path_check(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "AGENTS.md"),
                '[x](docs/guide.md?plain=1 "Title")\n',
            )
            _write(
                os.path.join(repo, "docs", "guide.md"),
                "Every commit is one coherent logical commit, after a "
                "compaction pass.",
            )
            result = cli.check(repo)
            self.assertEqual(result["links"], [])
            ids = [f["id"] for f in result["workflow"]]
            self.assertNotIn("R03", ids)

    def test_anchor_only_link_is_skipped(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "AGENTS.md"), "[top](#section)\n")
            result = cli.check(repo)
            self.assertEqual(result["links"], [])

    def test_missing_markdown_target_is_a_broken_link(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "AGENTS.md"),
                "[gone](docs/missing.md)\n",
            )
            result = cli.check(repo)
            self.assertEqual(
                result["links"],
                [
                    {
                        "kind": "link",
                        "status": "broken",
                        "target": "docs/missing.md",
                        "source": "AGENTS.md",
                    }
                ],
            )

    def test_missing_image_target_is_a_broken_link(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "AGENTS.md"),
                "![gone](img/missing.png)\n",
            )
            result = cli.check(repo)
            self.assertEqual(
                [finding["target"] for finding in result["links"]],
                ["img/missing.png"],
            )
            self.assertEqual(result["links"][0]["kind"], "link")
            self.assertEqual(result["links"][0]["status"], "broken")

    def test_directory_encoded_and_fenced_links_are_not_broken(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "AGENTS.md"),
                "[docs](docs/) [root](./) [sub](sub) [enc](sub/My%20File.md)\n"
                "```\n[example](path/to/file.md)\n```\n"
                "~~~~\n[tilde](also/missing.md)\n```\n~~~~\n"
                "[gone](after/fence.md)\n",
            )
            _write(os.path.join(repo, "docs", "a.md"), "x")
            _write(os.path.join(repo, "sub", "My File.md"), "x")
            result = cli.check(repo)
            self.assertEqual(
                [finding["target"] for finding in result["links"]], ["after/fence.md"]
            )

    def test_url_scheme_and_absolute_links_are_skipped(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "AGENTS.md"),
                "[web](https://example.com/a.md) "
                "[mail](mailto:a@b.example) "
                "[abs](/etc/passwd)\n",
            )
            result = cli.check(repo)
            self.assertEqual(result["links"], [])

    def test_check_is_read_only_and_repeatable(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "AGENTS.md"),
                "![logo](img/logo.png) [gone](docs/missing.md)\n",
            )
            png = os.path.join(repo, "img", "logo.png")
            os.makedirs(os.path.dirname(png))
            with open(png, "wb") as handle:
                handle.write(bytes(range(256)))
            before = _listing(repo)
            first = cli.check(repo)
            second = cli.check(repo)
            self.assertEqual(first, second)
            self.assertEqual(_listing(repo), before)
            self.assertEqual(
                [finding["target"] for finding in first["links"]],
                ["docs/missing.md"],
            )


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
        }
        result = remediation.build_remediation(report)
        self.assertIsInstance(result, dict)
        ids = [entry["id"] for entry in result["remediate"]]
        self.assertEqual(ids, ["R01", "R17"])
        by_id = {entry["id"]: entry for entry in result["remediate"]}
        self.assertIs(by_id["R01"]["auto_apply"], True)
        self.assertIs(by_id["R17"]["auto_apply"], False)
        self.assertEqual(result["blocked"], [])

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
        }
        result = remediation.build_remediation(report)
        self.assertEqual(
            result["remediate"][0]["matched_signals"], ["concise", "narrative"]
        )

    def test_returns_dict_never_bare_list(self):
        result = remediation.build_remediation({"workflow": []})
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result.keys()), {"remediate", "blocked", "notices"})
        self.assertEqual(result["notices"], [])

    def test_entry_signals_are_what_a_clause_must_contain_to_classify_present(self):
        # The SKILL.md hand-off writes each clause around its entry's `signals`; the bare
        # summary alone classifies near_miss/missing for several rules (R01, R12, ...).
        presence = {"gsd": True, "modern-cli": True, "codegraph": True,
                    "graphify": True, "opengsd": "ok"}
        presence.update({f"modern-cli:{t}": True for t in tool_presence.MODERN_CLI_TOOLS})
        entries = remediation.build_remediation(
            {"workflow": rule_checker.check_workflow_rules("", presence)}
        )["remediate"]
        self.assertTrue(entries)

        def phrases(signals):
            for item in signals:
                if isinstance(item, str):
                    yield item
                else:
                    yield from phrases(item)

        for entry in entries:
            text = entry["summary"] + "\n" + "; ".join(phrases(entry["signals"]))
            found = rule_checker.check_workflow_rules(text, presence, include_present=True)
            by_id = {finding["id"]: finding["status"] for finding in found}
            self.assertEqual(by_id[entry["id"]], "present", msg=entry["id"])


class TestGateRegistration(unittest.TestCase):
    def test_makefile_lists_module(self):
        with open(_MAKEFILE_PATH, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("tests.test_ai_kit_project_rules_agents", text)
        self.assertIn("tests.test_ai_kit_rules_common", text)

    def test_precommit_ruff_and_py_compile_match_package_path(self):
        for hook_id in ("ruff", "py-compile"):
            regex = _precommit_hook_files_regex(hook_id)
            self.assertIsNotNone(
                re.match(regex, _CLI_PY_CANDIDATE),
                f"{_CLI_PY_CANDIDATE} did not match {hook_id} files: {regex}",
            )
            self.assertIsNotNone(
                re.match(regex, "skills/_shared/ai_kit_rules_common/classification.py"),
                f"shared package did not match {hook_id} files: {regex}",
            )
        entry_block = _precommit_hook_block("unittest")
        match = re.search(r"^\s*entry:\s*(.+)$", entry_block, re.MULTILINE)
        self.assertIsNotNone(match, "no entry: value for hook unittest")
        assert match is not None
        self.assertIn("tests.test_ai_kit_project_rules_agents", match.group(1))
        self.assertIn("tests.test_ai_kit_rules_common", match.group(1))

    def test_pyright_include_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        include = data["tool"]["pyright"]["include"]
        self.assertTrue(_tool_roots_cover("skills/ai-kit-project-rules-agents", include), include)
        self.assertTrue(_tool_roots_cover("skills/_shared/ai_kit_rules_common", include), include)

    def test_vulture_paths_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        paths = data["tool"]["vulture"]["paths"]
        self.assertTrue(_tool_roots_cover("skills/ai-kit-project-rules-agents", paths), paths)
        self.assertTrue(_tool_roots_cover("skills/_shared/ai_kit_rules_common", paths), paths)

    def test_validate_covers_every_precommit_hook(self):
        with open(_PRECOMMIT_PATH, encoding="utf-8") as handle:
            precommit = handle.read()
        hook_ids = []
        for match in re.finditer(r"^\s*-\s*id:\s*(.+?)\s*$", precommit, re.MULTILINE):
            value = match.group(1).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            hook_ids.append(value)
        self.assertTrue(hook_ids, "no - id: entries parsed from .pre-commit-config.yaml")

        with open(_MAKEFILE_PATH, encoding="utf-8") as handle:
            makefile = handle.read()
        match = re.search(r"^validate:\s*(.*)$", makefile, re.MULTILINE)
        self.assertIsNotNone(match, "no validate: target in Makefile")
        assert match is not None
        prerequisites = match.group(1).split()
        makefile_targets = set(
            re.findall(r"^(?!\.)([A-Za-z0-9_.-]+)\s*:(?!=)", makefile, re.MULTILINE)
        )

        covered = [hook_id for hook_id in hook_ids if hook_id in makefile_targets]
        self.assertTrue(
            covered,
            "no pre-commit hook id has a same-named Makefile target",
        )
        for hook_id in covered:
            self.assertIn(
                hook_id,
                prerequisites,
                f"hook {hook_id!r} has a same-named Makefile target "
                f"but is missing from validate: prerequisites {prerequisites}",
            )


class TestOpenGsdRules(unittest.TestCase):
    """R18 and R19 are gated on a proven `@opengsd/gsd-core` identity (26 D-19, SPEC R7)."""

    IDENTITY = '{"packageName":"@opengsd/gsd-core","version":"1.17.0"}'
    SENTINEL = "sk-" + "test-" + "not-a-real-secret-0426"

    def _project(self, root, agents_text=None):
        repo = os.path.join(root, "repo")
        _write(os.path.join(repo, ".planning", "STATE.md"), "state\n")
        _write(os.path.join(repo, ".claude", "gsd-core", "bin", "gsd-tools.cjs"), "")
        if agents_text is not None:
            _write(os.path.join(repo, "AGENTS.md"), agents_text)
        bin_dir = os.path.join(root, "bin")
        fake_bin(bin_dir, ["node"], "#!/bin/sh\nexit 0\n")
        return repo, bin_dir

    def _run(self, identity_stdout=None, exit_code=0, record=None):
        def run_fn(argv, **kwargs):
            if record is not None:
                record.append((argv, kwargs))
            if "runtime-identity" in argv:
                return subprocess.CompletedProcess(
                    argv, exit_code, stdout=identity_stdout or "", stderr=""
                )
            return subprocess.CompletedProcess(argv, 128, stdout="", stderr="")

        return run_fn

    def _env(self, root, bin_dir):
        env = scoped_env(bin_dir, os.path.join(root, "home"))
        return env

    @staticmethod
    def _ids(result):
        return {finding["id"] for finding in result["workflow"]}

    def _finding(self, result, rule_id):
        for finding in result["workflow"]:
            if finding["id"] == rule_id:
                return finding
        self.fail(f"{rule_id} is absent from the findings")

    def test_no_agents_md_both_rules_missing(self):
        with tempfile.TemporaryDirectory() as root:
            repo, bin_dir = self._project(root)
            result = cli.check(
                repo, env=self._env(root, bin_dir), run_fn=self._run(self.IDENTITY)
            )
            for rule_id in ("R18", "R19"):
                self.assertEqual(self._finding(result, rule_id)["status"], "missing")

    def test_pointer_and_summary_satisfy_rules_and_cli_filters_present(self):
        text = (
            "The main agent arms the session wake and a self-resume by session id.\n"
            + rules.R19_POINTER
            + "\n"
        )
        with tempfile.TemporaryDirectory() as root:
            repo, bin_dir = self._project(root, text)
            env = self._env(root, bin_dir)
            filtered = cli.check(repo, env=env, run_fn=self._run(self.IDENTITY))
            self.assertEqual(self._ids(filtered) & {"R18", "R19"}, set())
            full = cli.check(
                repo, env=env, run_fn=self._run(self.IDENTITY), include_present=True
            )
            self.assertEqual(self._finding(full, "R18")["status"], "present")
            self.assertEqual(self._finding(full, "R19")["status"], "present")

    def test_one_directive_yields_one_present_one_missing(self):
        with tempfile.TemporaryDirectory() as root:
            repo, bin_dir = self._project(root, rules.R19_POINTER + "\n")
            full = cli.check(
                repo,
                env=self._env(root, bin_dir),
                run_fn=self._run(self.IDENTITY),
                include_present=True,
            )
            self.assertEqual(self._finding(full, "R19")["status"], "present")
            self.assertEqual(self._finding(full, "R18")["status"], "missing")

    def test_unverified_identity_is_notice_in_remediate(self):
        with tempfile.TemporaryDirectory() as root:
            repo, bin_dir = self._project(root)
            report = cli.remediate(
                repo, env=self._env(root, bin_dir), run_fn=self._run(exit_code=1)
            )
            notice_ids = [n["id"] for n in report["notices"]]
            self.assertEqual(notice_ids, ["R18", "R19"])
            for notice in report["notices"]:
                self.assertTrue(notice["unverified"])
                self.assertIn("reason", notice)
                self.assertEqual(notice["kind"], "workflow")
            remediated = {entry["id"] for entry in report["remediate"]}
            self.assertFalse(remediated & {"R18", "R19"})
            for rule_id in ("R18", "R19"):
                finding = self._finding(
                    cli.check(
                        repo, env=self._env(root, bin_dir), run_fn=self._run(exit_code=1)
                    ),
                    rule_id,
                )
                self.assertEqual(finding["status"], "not_applicable")
                self.assertTrue(finding["unverified"])

    def test_unverified_notice_reaches_rules_all_aggregate(self):
        with tempfile.TemporaryDirectory() as root:
            repo, bin_dir = self._project(root)
            agents_report = cli.remediate(
                repo, env=self._env(root, bin_dir), run_fn=self._run(exit_code=1)
            )
        domains = {
            "agents": agents_report,
            "makefile": {"remediate": [], "blocked": [], "notices": []},
            "precommit": {"remediate": [], "blocked": []},
            "arch": {"remediate": [], "blocked": []},
            "docker": {"remediate": [], "blocked": []},
            "cicd": {"remediate": [], "blocked": []},
        }
        report = rules_all_aggregate.aggregate(domains)
        self.assertEqual([n["id"] for n in report["notices"]], ["R18", "R19"])

    def test_valid_identity_naming_another_package_is_plain_not_applicable(self):
        other = '{"packageName":"@opengsd/gsd-core-fork","version":"9"}'
        with tempfile.TemporaryDirectory() as root:
            repo, bin_dir = self._project(root)
            result = cli.check(
                repo, env=self._env(root, bin_dir), run_fn=self._run(other)
            )
            for rule_id in ("R18", "R19"):
                finding = self._finding(result, rule_id)
                self.assertEqual(finding["status"], "not_applicable")
                self.assertNotIn("unverified", finding)
            report = cli.remediate(
                repo, env=self._env(root, bin_dir), run_fn=self._run(other)
            )
            self.assertEqual(report["notices"], [])

    def test_no_planning_dir_skips_probe_and_rules(self):
        with tempfile.TemporaryDirectory() as root:
            repo = os.path.join(root, "repo")
            os.makedirs(repo)
            calls = []
            result = cli.check(
                repo,
                env=self._env(root, root),
                run_fn=self._run(self.IDENTITY, record=calls),
            )
            self.assertEqual(calls, [])
            self.assertEqual(self._finding(result, "R18")["status"], "not_applicable")
            self.assertNotIn("unverified", self._finding(result, "R18"))
            report = cli.remediate(
                repo, env=self._env(root, root), run_fn=self._run(self.IDENTITY)
            )
            self.assertEqual(report["notices"], [])

    def test_skip_env_runs_no_target_code_and_reports_notices(self):
        with tempfile.TemporaryDirectory() as root:
            repo, bin_dir = self._project(root)
            env = self._env(root, bin_dir)
            env["AI_KIT_SKIP_GSD_PROBE"] = "1"
            calls = []
            report = cli.remediate(
                repo, env=env, run_fn=self._run(self.IDENTITY, record=calls)
            )
            self.assertEqual(
                [argv for argv, _kw in calls if "runtime-identity" in argv], []
            )
            self.assertEqual([n["id"] for n in report["notices"]], ["R18", "R19"])
            self.assertIn("AI_KIT_SKIP_GSD_PROBE", report["notices"][0]["reason"])

    def test_skip_env_executes_nothing_at_all(self):
        # SKILL.md claims "nothing from the repo runs": tool presence only stats paths
        with tempfile.TemporaryDirectory() as root:
            repo, bin_dir = self._project(root)
            env = self._env(root, bin_dir)
            env["AI_KIT_SKIP_GSD_PROBE"] = "1"
            calls = []
            boom = mock.Mock(side_effect=AssertionError("subprocess executed"))
            with mock.patch("subprocess.run", boom), mock.patch("subprocess.Popen", boom):
                cli.check(repo, env=env, run_fn=self._run(self.IDENTITY, record=calls))
            self.assertEqual(calls, [])
            boom.assert_not_called()

    def test_probe_env_and_findings_carry_no_caller_secret(self):
        with tempfile.TemporaryDirectory() as root:
            repo, bin_dir = self._project(root)
            env = self._env(root, bin_dir)
            env["SECRET_SENTINEL"] = self.SENTINEL
            calls = []
            result = cli.check(
                repo, env=env, run_fn=self._run(self.IDENTITY, record=calls),
                include_present=True,
            )
            probe_calls = [kw for argv, kw in calls if "runtime-identity" in argv]
            self.assertEqual(len(probe_calls), 1)
            self.assertEqual(set(probe_calls[0]["env"]), {"PATH", "HOME"})
            self.assertNotIn(self.SENTINEL, json.dumps(result))

    def test_check_tool_presence_stays_hermetic(self):
        with tempfile.TemporaryDirectory() as root:
            repo, bin_dir = self._project(root)
            presence = tool_presence.check_tool_presence(
                search_path=bin_dir, repo_root=repo
            )
            self.assertNotIn("opengsd", presence)
            self.assertIs(presence["gsd"], True)


class TestOpenGsdRuleText(unittest.TestCase):
    def test_r18_r19_r20_follow_r17_in_catalog_order(self):
        ids = [rule["id"] for rule in rules.RULES]
        self.assertEqual(ids[-4:], ["R17", "R18", "R19", "R20"])

    def test_signal_sets_are_disjoint_and_avoid_the_banned_phrases(self):
        by_id = {rule["id"]: rule for rule in rules.RULES}
        flat_r18 = set(by_id["R18"]["signals"])
        r19_phrases = {p for group in by_id["R19"]["signals"] for p in group}
        self.assertEqual(flat_r18 & r19_phrases, set())
        for banned in ("unfinished work", "quota", "hourly"):
            self.assertNotIn(banned, flat_r18)
            self.assertNotIn(banned, r19_phrases)

    def test_r19_summary_is_the_policy_pointer_verbatim(self):
        from tests.test_quota_policy_text import REFERENCE, pointer_lines

        text = REFERENCE.read_text(encoding="utf-8")
        pointer = "\n".join(pointer_lines(text))
        self.assertEqual(rules.R19_POINTER, pointer)
        by_id = {rule["id"]: rule for rule in rules.RULES}
        self.assertEqual(by_id["R19"]["summary"], pointer)
        self.assertTrue(by_id["R19"]["verbatim"])
        self.assertTrue(by_id["R18"]["verbatim"])

    def test_pointer_satisfies_every_r19_group(self):
        from tests.test_quota_policy_text import REFERENCE, pointer_lines

        pointer = "\n".join(pointer_lines(REFERENCE.read_text(encoding="utf-8")))
        by_id = {rule["id"]: rule for rule in rules.RULES}
        for group in by_id["R19"]["signals"]:
            self.assertTrue(any(p in pointer.lower() for p in group), msg=group)

    def test_r18_summary_satisfies_its_signals(self):
        by_id = {rule["id"]: rule for rule in rules.RULES}
        summary = by_id["R18"]["summary"].lower()
        self.assertTrue(any(p in summary for p in by_id["R18"]["signals"]))
        self.assertIn("host-reported reset + 60 s", by_id["R18"]["summary"])

    def test_non_vacuity_partial_pointer_is_near_miss(self):
        presence = {"opengsd": "ok", "opengsd_reason": "test"}
        text = rules.R19_POINTER.replace("cross-ai.mjs", "runner.mjs")
        findings = rule_checker.check_workflow_rules(text, presence, include_present=True)
        self.assertEqual(self._status(findings, "R19"), "near_miss")

    def test_non_vacuity_partial_summary_is_near_miss(self):
        presence = {"opengsd": "ok", "opengsd_reason": "test"}
        # flat rule: 0 matches is missing, 1 of 3 is near_miss, 2 of 3 reaches ceil(3/2) = present
        findings = rule_checker.check_workflow_rules(
            "a session wake only", presence, include_present=True
        )
        self.assertEqual(self._status(findings, "R18"), "near_miss")
        findings = rule_checker.check_workflow_rules(
            "nothing relevant here", presence, include_present=True
        )
        self.assertEqual(self._status(findings, "R18"), "missing")
        findings = rule_checker.check_workflow_rules(
            "session wake and self-resume", presence, include_present=True
        )
        self.assertEqual(self._status(findings, "R18"), "present")

    def test_unverified_condition_is_not_applicable_not_met(self):
        from ai_kit_rules_common.classification import condition_state, evaluate_condition

        self.assertEqual(condition_state("opengsd", {"opengsd": "unverified"}), "unverified")
        self.assertFalse(evaluate_condition("opengsd", {"opengsd": "unverified"}))
        self.assertEqual(condition_state("opengsd", {"opengsd": "absent"}), "unmet")
        self.assertEqual(condition_state("opengsd", {"opengsd": "ok"}), "met")

    @staticmethod
    def _status(findings, rule_id):
        for finding in findings:
            if finding["id"] == rule_id:
                return finding["status"]
        return None


class TestEntrypointResolveBlock(unittest.TestCase):
    """The SKILL.md entrypoint block is robust to a missing or unusable skill directory."""

    _SKILL = "ai-kit-project-rules-agents"

    def _skill_dir(self):
        return os.path.join(_REPO, "skills", self._SKILL)

    def test_block_with_skill_dir_prints_that_entrypoint(self):
        with tempfile.TemporaryDirectory() as root:
            result = _run_block(_skill_resolve_block(self._SKILL), root, self._skill_dir())
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            os.path.realpath(self._skill_dir()) + "/" + self._SKILL + ".py",
        )

    def test_relative_skill_dir_prints_an_absolute_entrypoint(self):
        with tempfile.TemporaryDirectory() as root:
            result = _run_block(
                _skill_resolve_block(self._SKILL), root, self._SKILL,
                cwd=os.path.join(_REPO, "skills"),
            )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        printed = result.stdout.strip()
        self.assertTrue(os.path.isabs(printed), printed)
        self.assertEqual(printed, os.path.realpath(self._skill_dir()) + "/" + self._SKILL + ".py")

    def test_unedited_block_fails_loudly_and_prints_nothing(self):
        with tempfile.TemporaryDirectory() as root:
            result = _run_block(_skill_resolve_block(self._SKILL), root)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("SKILL_DIR", result.stderr)

    def test_plain_copy_without_shared_is_skipped(self):
        with tempfile.TemporaryDirectory() as root:
            copy = os.path.join(root, "copy", self._SKILL)
            shutil.copytree(self._skill_dir(), copy, ignore=shutil.ignore_patterns("__pycache__"))
            result = _run_block(_skill_resolve_block(self._SKILL), root, copy)
        self.assertEqual(result.stdout, "")

    def test_skill_md_paths_to_rules_and_classification_exist(self):
        with open(os.path.join(self._skill_dir(), "SKILL.md"), encoding="utf-8") as handle:
            text = handle.read()
        for rel in (
            "ai_kit_project_rules_agents/rules.py",
            "../_shared/ai_kit_rules_common/classification.py",
        ):
            self.assertIn(rel, text)
            self.assertTrue(os.path.isfile(os.path.join(self._skill_dir(), rel)), rel)


class TestRefactorSafetyPreflight(unittest.TestCase):
    """Step C's pre-flight block runs as written; a missing refactor skill does not block."""

    _SKILL = "ai-kit-project-rules-agents"

    def _text(self):
        path = os.path.join(_REPO, "skills", self._SKILL, "SKILL.md")
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def _run(self, repo, files=("AGENTS.md",)):
        blocks = [b for b in re.findall(r"```bash\n(.*?)```", self._text(), re.DOTALL)
                  if "mktemp -d" in b]
        self.assertEqual(len(blocks), 1)
        listed = " ".join(f"'{f}'" for f in files)
        block = blocks[0].replace("<repo_root>", repo).replace(
            "'<target file>' '<linked file>'", listed
        )
        env = {"PATH": os.environ.get("PATH", ""), "HOME": os.path.join(repo, "..", "home"),
               "TMPDIR": os.path.join(repo, "..")}
        return subprocess.run(
            ["bash", "-c", block], capture_output=True, text=True, env=env, check=False, timeout=30
        )

    def _git(self, repo, *args):
        subprocess.run(
            ["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            check=True, capture_output=True,
        )

    def test_clean_tracked_file_needs_no_backup(self):
        with tempfile.TemporaryDirectory() as root:
            repo = os.path.join(root, "repo")
            _write(os.path.join(repo, "AGENTS.md"), "a\n")
            self._git(repo, "init", "-q")
            self._git(repo, "add", "AGENTS.md")
            self._git(repo, "commit", "-q", "-m", "x")
            result = self._run(repo)
        self.assertEqual(result.stdout.strip(), "clean: AGENTS.md", msg=result.stderr)

    def test_dirty_file_is_backed_up(self):
        with tempfile.TemporaryDirectory() as root:
            repo = os.path.join(root, "repo")
            _write(os.path.join(repo, "AGENTS.md"), "a\n")
            self._git(repo, "init", "-q")
            self._git(repo, "add", "AGENTS.md")
            self._git(repo, "commit", "-q", "-m", "x")
            _write(os.path.join(repo, "AGENTS.md"), "a\nedited\n")
            result = self._run(repo)
            self.assertTrue(result.stdout.startswith("backup: "), msg=result.stderr)
            backup = result.stdout.strip().removeprefix("backup: ")
            with open(backup, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "a\nedited\n")

    def test_ignored_file_is_backed_up(self):
        # An ignored file has an empty `git status`, so tracked state must decide.
        with tempfile.TemporaryDirectory() as root:
            repo = os.path.join(root, "repo")
            _write(os.path.join(repo, ".gitignore"), "AGENTS.md\n")
            _write(os.path.join(repo, "AGENTS.md"), "a\n")
            self._git(repo, "init", "-q")
            self._git(repo, "add", ".gitignore")
            self._git(repo, "commit", "-q", "-m", "x")
            result = self._run(repo)
        self.assertTrue(result.stdout.startswith("backup: "), msg=result.stderr)

    def test_linked_files_are_backed_up_individually(self):
        with tempfile.TemporaryDirectory() as root:
            repo = os.path.join(root, "repo")
            for name in ("AGENTS.md", "docs/a.md"):
                _write(os.path.join(repo, name), "a\n")
            self._git(repo, "init", "-q")
            self._git(repo, "add", "AGENTS.md")
            self._git(repo, "commit", "-q", "-m", "x")
            result = self._run(repo, files=("AGENTS.md", "docs/a.md"))
            lines = result.stdout.strip().splitlines()
            self.assertEqual(lines[0], "clean: AGENTS.md", msg=result.stderr)
            self.assertTrue(lines[1].startswith("backup: "), msg=result.stderr)
            self.assertTrue(lines[1].endswith("/docs/a.md"))
            self.assertTrue(os.path.isfile(lines[1].removeprefix("backup: ")))

    def test_non_git_repo_is_backed_up(self):
        with tempfile.TemporaryDirectory() as root:
            repo = os.path.join(root, "repo")
            _write(os.path.join(repo, "AGENTS.md"), "a\n")
            result = self._run(repo)
        self.assertTrue(result.stdout.startswith("backup: "), msg=result.stderr)

    def test_step_c_and_d_text(self):
        text = self._text()
        self.assertNotIn("stop and report that `agent-md-refactor` is not installed", text)
        self.assertIn("offer the Step B clauses by direct edit", text)
        self.assertIn("Confirm that nothing outside the Step B clauses", text)
        self.assertIn("**Mechanism available:**", text)
        self.assertIn("**Skill not found:**", text)
        self.assertIn("**No dispatch mechanism:**", text)
        self.assertIn("pre-flight backup is still required on this direct-edit path", text)
        self.assertIn("EVERY file of the pre-flight `FILES` set", text)
        self.assertIn('diff -u "$BACKUP/<file>"', text)
        self.assertIn("Near-misses the user declined in Step A stay declined", text)

    def test_preflight_runs_before_any_edit_and_step_d_is_a_checklist(self):
        text = self._text()
        pre_match = re.search(r"\*\*Pre-flight backup \(own step: before ANY edit", text)
        assert pre_match
        step_b = text.index("**Step B (assemble one ordered list)")
        step_c = text.index("**Step C (one invocation")
        self.assertLess(step_b, pre_match.start())
        self.assertLess(pre_match.start(), step_c)
        # the pre-flight section owns the backup block; Step C does not
        self.assertLess(pre_match.start(), text.index("mktemp -d"))
        self.assertLess(text.index("mktemp -d"), step_c)
        empty_match = re.search(r"- \*\*List empty:\*\*(.*)", text)
        assert empty_match
        self.assertIn("run the pre-flight backup FIRST", empty_match.group(1))
        step_d = text[text.index("**Step D (re-check"):text.index("## Anti-patterns")]
        for n in range(1, 6):
            self.assertIn(f"\n{n}. **", step_d)
        self.assertIn("List the files the run created", step_d)
        self.assertIn("never delete them", step_d)

    def test_status_vocabulary_and_step_a_bullets(self):
        text = self._text()
        self.assertIn("`not_applicable` finding is a flag, not a status", text)
        self.assertIn("the CLI omits `present` findings", text)
        self.assertIn("Every accepted Step B id must now be absent from `workflow`", text)
        leads = ("**Confirmation:**", "**Unattended:**", "**R20 rewrite",
                 "**`unverified_stacks`:**", "**Why not its contradiction phase:**")
        for lead in leads:
            self.assertIn(lead, text)
        self.assertIn("R20 stays `near_miss` while any such line is left", text)
        self.assertIn("that printed path is the one to carry", text)

    def test_trust_gate_and_external_refactor_text(self):
        text = self._text()
        self.assertIn("the probe is the only step that executes anything from the repo", text)
        self.assertIn("without running a binary", text)
        self.assertIn("is an external, optional skill", text)
        self.assertIn("name a phase only after reading that file", text)
        self.assertNotIn("Phase 2", text)
        self.assertNotIn("Phase 3", text)
        self.assertIn("do not insert the R20 block again", text)

    def test_description_and_unattended_branch(self):
        text = self._text()
        desc_match = re.search(r"^description: (.*)$", text, re.MULTILINE)
        assert desc_match
        desc = desc_match.group(1)
        self.assertLessEqual(len(desc), 1024)
        for phrase in ("or to fix it", "insert missing house rules", "repair broken links",
                       "/agent-md-refactor"):
            self.assertIn(phrase, desc)
        self.assertIn("apply only the Step B clauses by direct edit", text)
        self.assertIn("Unattended, if the diff shows any change outside the Step B clauses", text)
        self.assertNotIn("plus any linked file containing a `hardcoded_counts` line", text)
        for phrase in ("house rules", "agent instructions", "workflow-rule audit"):
            self.assertIn(phrase, desc)
        self.assertNotIn("general rules engine", desc)
        self.assertNotIn("files named in any R20", text)
        self.assertLessEqual(text.count("\n"), 170)

    def test_output_shapes_and_disjoint_dispatch_cases(self):
        text = self._text()
        for key in ("`check.workflow`", "`check.links`", "`remediate.remediate`",
                    "`remediate.notices`", "`remediate.blocked`"):
            self.assertIn(key, text)
        mech_match = re.search(r"\*\*Mechanism available:\*\*(.*)", text)
        assert mech_match
        mechanism = mech_match.group(1)
        self.assertNotIn("into context", mechanism)


_COUNT_FILES = (
    "skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py",
    "skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rule_checker.py",
    "skills/ai-kit-project-rules-agents/SKILL.md",
    "README.md",
    "skills/ai-kit-project-rules-makefile/SKILL.md",
)
_COUNT_RE = re.compile(r"\b(\d+)(-rule| house rules| rules\b)")


class TestRuleCountStrings(unittest.TestCase):
    """Every `<n>-rule`, `<n> rules` and `<n> house rules` tracks `len(RULES)` (D-22, D-27)."""

    def test_every_count_string_equals_rule_count(self):
        expected = len(rules.RULES)
        seen = []
        for rel in _COUNT_FILES:
            with open(os.path.join(_REPO, rel), encoding="utf-8") as handle:
                for match in _COUNT_RE.finditer(handle.read()):
                    seen.append((rel, int(match.group(1))))
        self.assertGreaterEqual(len(seen), 8, msg=f"non-vacuity: found only {seen}")
        stale = [item for item in seen if item[1] != expected]
        self.assertEqual(stale, [], msg=f"count strings disagree with {expected} rules")


class TestParallelTestRule(unittest.TestCase):
    """R20: the parallel-test CPU share, composed per detected stack (26 D-27, SPEC R9)."""

    def _repo(self, root, markers=(), agents_text=None):
        repo = os.path.join(root, "repo")
        os.makedirs(repo, exist_ok=True)
        for marker in markers:
            _write(os.path.join(repo, marker), "")
        if agents_text is not None:
            _write(os.path.join(repo, "AGENTS.md"), agents_text)
        return repo

    @staticmethod
    def _env(root):
        return scoped_env(os.path.join(root, "bin"), os.path.join(root, "home"))

    def _check(self, repo, root, include_present=False):
        return cli.check(repo, env=self._env(root), include_present=include_present)

    @staticmethod
    def _r20(result):
        """The R20 finding, or None when the CLI filtered it out (present, by default)."""
        for finding in result["workflow"]:
            if finding["id"] == "R20":
                return finding
        return None

    def _present_r20(self, repo, root):
        """R20 with `include_present=True`; fails the test explicitly if it is absent."""
        finding = self._r20(self._check(repo, root, include_present=True))
        if finding is None:
            self.fail("R20 is absent even with include_present=True")
        return finding

    def test_python_repo_without_rule_is_missing_with_python_clause(self):
        with tempfile.TemporaryDirectory() as root:
            repo = self._repo(root, ["pyproject.toml"], "# Agents\n")
            finding = self._present_r20(repo, root)
            self.assertEqual(finding["status"], "missing")
            self.assertIn("floor(40% of the available CPUs)", finding["summary"])
            self.assertIn("python: pytest-xdist `pytest -n N`", finding["summary"])
            self.assertEqual(finding["stacks"], ["python"])
            self.assertEqual(finding["unverified_stacks"], [])

    def test_remediation_text_written_back_is_present_and_filtered_by_cli(self):
        with tempfile.TemporaryDirectory() as root:
            repo = self._repo(root, ["pyproject.toml"], "# Agents\n")
            remediated = [
                entry
                for entry in cli.remediate(repo, env=self._env(root))["remediate"]
                if entry["id"] == "R20"
            ]
            self.assertEqual(len(remediated), 1)
            self.assertTrue(remediated[0]["verbatim"])
            _write(
                os.path.join(repo, "AGENTS.md"),
                "# Agents\n\n" + remediated[0]["summary"] + "\n",
            )
            self.assertIsNone(self._r20(self._check(repo, root)))
            self.assertEqual(self._present_r20(repo, root)["status"], "present")

    def test_no_stack_marker_makes_rule_not_applicable(self):
        with tempfile.TemporaryDirectory() as root:
            repo = self._repo(root, [], "# Agents\n")
            self.assertEqual(self._present_r20(repo, root)["status"], "not_applicable")

    # --- Task 2: per-stack forms, multi-stack order, the 40% boundary, literal counts ---

    _STACK_FIXTURES = {
        "go": ("go.mod",),
        "node": ("package.json",),
        "rust": ("Cargo.toml",),
        "maven": ("pom.xml",),
        "gradle": ("build.gradle",),
        "gradle-kts": ("build.gradle.kts",),
    }

    def _composed(self, root, markers):
        """Compose R20 for a repo with `markers`, write it back, and return its summary."""
        repo = self._repo(root, markers, "# Agents\n")
        finding = self._present_r20(repo, root)
        _write(os.path.join(repo, "AGENTS.md"), "# Agents\n\n" + finding["summary"] + "\n")
        return finding, repo

    def test_each_stack_gets_its_own_clause_and_round_trips_present(self):
        from ai_kit_rules_common import tool_catalog

        clause_by_marker = {}
        for row in tool_catalog.PARALLEL_TEST_FORMS:
            for marker in row["markers"]:
                clause_by_marker[marker] = row["clause"]
        for marker, expected_markers in self._STACK_FIXTURES.items():
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as root:
                markers = expected_markers
                finding, repo = self._composed(root, markers)
                clause = clause_by_marker[markers[0]]
                self.assertIn(clause, finding["summary"])
                self.assertEqual(finding["status"], "missing")
                self.assertIsNone(self._r20(self._check(repo, root)))
                self.assertEqual(self._present_r20(repo, root)["status"], "present")

    def test_gradle_groovy_and_kotlin_clauses_are_each_their_own_syntax(self):
        with tempfile.TemporaryDirectory() as root:
            groovy, _ = self._composed(root, ("build.gradle",))
            self.assertIn(
                "Math.max(1, (int) (Runtime.runtime.availableProcessors() * 0.4))",
                groovy["summary"],
            )
            self.assertNotIn("coerceAtLeast", groovy["summary"])
        with tempfile.TemporaryDirectory() as root:
            kotlin, _ = self._composed(root, ("build.gradle.kts",))
            self.assertIn("coerceAtLeast(1)", kotlin["summary"])
            self.assertNotIn("Math.max", kotlin["summary"])

    def test_three_java_markers_give_maven_groovy_kotlin_in_that_order(self):
        with tempfile.TemporaryDirectory() as root:
            repo = self._repo(root, ["pom.xml", "build.gradle", "build.gradle.kts"], "# A\n")
            finding = self._present_r20(repo, root)
            clauses = [line for line in finding["summary"].split("\n") if line.startswith("java")]
            self.assertEqual(len(clauses), 3)
            self.assertTrue(clauses[0].startswith("java (Maven)"))
            self.assertIn("Groovy DSL", clauses[1])
            self.assertIn("Kotlin DSL", clauses[2])

    def test_gradle_literal_fork_count_is_flagged_not_the_clause(self):
        with tempfile.TemporaryDirectory() as root:
            repo = self._repo(root, ["build.gradle"], "# A\n")
            _write(
                os.path.join(repo, "AGENTS.md"),
                "maxParallelForks = 8\n",
            )
            finding = self._present_r20(repo, root)
            self.assertEqual(finding["hardcoded_counts"], ["maxParallelForks = 8"])
            self.assertEqual(finding["status"], "near_miss")

    def test_multi_stack_order_and_stable_across_runs(self):
        with tempfile.TemporaryDirectory() as root:
            repo = self._repo(root, ["pyproject.toml", "go.mod", "package.json"], "# A\n")
            first = self._present_r20(repo, root)
            second = self._present_r20(repo, root)
            self.assertEqual(first["stacks"], ["go", "python", "node"])
            self.assertEqual(first, second)
            lines = first["summary"].split("\n")
            go_at = next(i for i, line in enumerate(lines) if line.startswith("go:"))
            py_at = next(i for i, line in enumerate(lines) if line.startswith("python:"))
            node_at = next(i for i, line in enumerate(lines) if line.startswith("node:"))
            self.assertLess(go_at, py_at)
            self.assertLess(py_at, node_at)

    def test_two_stacks_with_identical_clause_write_it_once(self):
        from ai_kit_rules_common import classification

        shared = "shared: one clause for two stacks."
        forms = (
            {"form": "a", "stack": "go", "markers": ("go.mod",), "runners": (), "clause": shared,
             "signals": ("shared",), "count_flags": ("-p",), "source": "s"},
            {"form": "b", "stack": "rust", "markers": ("Cargo.toml",), "runners": (),
             "clause": shared, "signals": ("shared",), "count_flags": ("-p",), "source": "s"},
        )
        rule = {
            "id": "R20",
            "criticality": 3,
            "condition": "stack-detected",
            "signals": PARALLEL_TEST_SIGNAL_GROUPS,
            "summary": PARALLEL_TEST_GENERIC,
            "stack_forms": forms,
            "count_flags": PARALLEL_TEST_COUNT_FLAGS,
        }
        presence = {"stacks": ["go", "rust"], "stack_markers": ["go.mod", "Cargo.toml"]}
        finding = classification.check_rules("# A\n", presence, (rule,), include_present=True)[0]
        self.assertEqual(finding["summary"].count(shared), 1)
        self.assertEqual(finding["stacks"], ["go", "rust"])

    def test_share_of_exactly_forty_percent_passes(self):
        with tempfile.TemporaryDirectory() as root:
            text = (
                "Unit tests run in parallel with a worker count of floor(40% of the available "
                "CPUs), at least 1. node: jest --maxWorkers=40%.\n"
            )
            repo = self._repo(root, ["package.json"], text)
            finding = self._present_r20(repo, root)
            self.assertEqual(finding["hardcoded_counts"], [])
            self.assertEqual(finding["status"], "present")

    def test_share_above_forty_percent_is_flagged_in_each_form(self):
        cases = {
            "percent flag": "jest --maxWorkers=41% for unit tests",
            "per-core multiplier": "mvn -T 0.41C test runs unit tests",
            "prose share": "use 41% of the available CPUs for the test suite",
        }
        for label, line in cases.items():
            with self.subTest(form=label), tempfile.TemporaryDirectory() as root:
                repo = self._repo(root, ["package.json", "pom.xml"], line + "\n")
                finding = self._present_r20(repo, root)
                self.assertEqual(finding["hardcoded_counts"], [line], msg=label)
                self.assertEqual(finding["status"], "near_miss")

    def test_maven_zero_point_four_cores_passes_and_zero_point_four_one_fails(self):
        with tempfile.TemporaryDirectory() as root:
            repo = self._repo(root, ["pom.xml"], "Maven: mvn -T 0.4C test (unit tests)\n")
            self.assertEqual(self._present_r20(repo, root)["hardcoded_counts"], [])
        with tempfile.TemporaryDirectory() as root:
            repo = self._repo(root, ["pom.xml"], "Maven: mvn -T 0.41C test (unit tests)\n")
            self.assertEqual(
                self._present_r20(repo, root)["hardcoded_counts"],
                ["Maven: mvn -T 0.41C test (unit tests)"],
            )

    def test_literal_counts_next_to_a_test_command_are_flagged(self):
        cases = [
            ("pytest -n 12 unit tests", ["python"]),
            ("make -j 8 test", ["python"]),
            ("jest --maxWorkers=4 unit tests", ["node"]),
        ]
        for line, markers in cases:
            with self.subTest(line=line), tempfile.TemporaryDirectory() as root:
                marker_files = {"python": "pyproject.toml", "node": "package.json"}
                repo = self._repo(root, [marker_files[m] for m in markers], line + "\n")
                finding = self._present_r20(repo, root)
                self.assertEqual(finding["hardcoded_counts"], [line])
                self.assertEqual(finding["status"], "near_miss")

    def test_rust_test_threads_is_flagged_once_not_as_a_short_flag(self):
        with tempfile.TemporaryDirectory() as root:
            repo = self._repo(root, ["Cargo.toml"], "cargo test -- --test-threads=4\n")
            finding = self._present_r20(repo, root)
            self.assertEqual(finding["hardcoded_counts"], ["cargo test -- --test-threads=4"])

    def test_non_vacuity_non_test_lines_are_not_flagged(self):
        text = "tail -n 50 build.log\nmake -j 8 build\n"
        with tempfile.TemporaryDirectory() as root:
            repo = self._repo(root, ["pyproject.toml"], text)
            finding = self._present_r20(repo, root)
            self.assertEqual(finding["hardcoded_counts"], [])

    def test_unverified_stack_clause_says_so_and_is_listed(self):
        from ai_kit_rules_common import classification

        forms = ({"stack": "go", "markers": ("go.mod",), "runners": (), "clause": "go: x",
                  "signals": ("go x",), "count_flags": ("-p",), "source": "s", "form": "go"},)
        rule = {
            "id": "R20",
            "criticality": 3,
            "condition": "stack-detected",
            "signals": PARALLEL_TEST_SIGNAL_GROUPS,
            "summary": PARALLEL_TEST_GENERIC,
            "stack_forms": forms,
            "count_flags": PARALLEL_TEST_COUNT_FLAGS,
        }
        presence = {"stacks": ["go", "cobol"], "stack_markers": ["go.mod"]}
        finding = classification.check_rules("# A\n", presence, (rule,), include_present=True)[0]
        self.assertEqual(finding["unverified_stacks"], ["cobol"])
        self.assertIn("cobol: no verified form exists", finding["summary"])
        self.assertIn("go: x", finding["summary"])

    def test_generic_sentence_is_case_insensitive(self):
        with tempfile.TemporaryDirectory() as root:
            text = (
                "Unit tests run in PARALLEL with a worker count of FLOOR(40% OF THE AVAILABLE "
                "CPUS), AT LEAST 1.\n"
            )
            repo = self._repo(root, ["pyproject.toml"], text)
            finding = self._present_r20(repo, root)
            self.assertEqual(finding["status"], "near_miss")
            self.assertEqual(finding["hardcoded_counts"], [])




if __name__ == "__main__":
    unittest.main()
