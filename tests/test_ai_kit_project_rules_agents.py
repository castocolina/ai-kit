import os
import re
import sys
import tempfile
import tomllib
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-agents"),
)

from ai_kit_project_rules_agents import (
    cli,
    remediation,
    rule_checker,
    rules,
    tool_presence,
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

    @classmethod
    def _require_find(cls, findings, rule_id):
        finding = cls._find(findings, rule_id)
        assert finding is not None
        return finding

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

    def test_tool_presence_condition_not_applicable(self):
        presence = {"rtk": False}
        findings = rule_checker.check_workflow_rules(
            "no rtk mention here", presence, include_present=True
        )
        self.assertEqual(self._require_find(findings, "R05")["status"], "not_applicable")

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
        self.assertEqual(set(result.keys()), {"remediate", "blocked"})


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


if __name__ == "__main__":
    unittest.main()
