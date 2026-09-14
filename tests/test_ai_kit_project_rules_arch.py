"""Tests for `ai-kit-project-rules-arch` (REQ-rules-arch, Phase 12 plans
01-02).

Plan 12-01, Task 1's tracer contract: the six `<behavior>` cases in the
`TestTracer*` classes below, written before the checker existed and
confirmed to fail for the right reason (ImportError -- the package did not
exist yet), then implemented against until they passed. Task 2 fills the
suite out with paired triggering/non-triggering fixtures for every
structural check, the D-A1 shape rule per-alternative, all three D-A2
chaining mechanisms with their token-boundary case, cycle/breadth safety,
degradation, the CLI surface, and its own gate-registration class. The
shared suite's grown `STRUCTURAL_KINDS` tuple and
`parse_makefile_targets_ordered` coverage live in
`tests/test_ai_kit_rules_common.py` instead (Task 2 (b)).

Plan 12-02, Task 1's tracer contract: the `TestTracerAstOnly*` classes
below carry this plan's own `<behavior>` cases (D-A7/D-A8/D-A9), written
before `ast_only.py` existed. Task 3 promotes them into the permanent,
fully paired coverage classes.
"""

import os
import re
import sys
import tempfile
import tomllib
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-arch"),
)

from ai_kit_project_rules_arch import arch_checker, cli

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MAKEFILE_PATH = os.path.join(_REPO, "Makefile")
_PRECOMMIT_PATH = os.path.join(_REPO, ".pre-commit-config.yaml")
_PYPROJECT_PATH = os.path.join(_REPO, "pyproject.toml")
_CLI_PY_CANDIDATE = "skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/cli.py"


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def _findings(repo_root):
    return arch_checker.check_arch_rules(repo_root)


def _issues(repo_root):
    return [f["issue"] for f in _findings(repo_root)]


def _linear_chain_makefile(hops, target_name="arch-test"):
    """`test` reaching `target_name` through a linear chain exactly `hops`
    edges long (`test: t1`, `t1: t2`, ..., `t{hops-1}: target_name`)."""
    lines = []
    prev = "test"
    for i in range(1, hops):
        nxt = f"t{i}"
        lines.append(f"{prev}: {nxt}\n\n")
        prev = nxt
    lines.append(f"{prev}: {target_name}\n\n")
    lines.append(f"{target_name}:\n\techo a\n")
    return "".join(lines)


def _wide_fanout_makefile(width=600, target_name="arch-test"):
    """`test` with `width` distinct direct prerequisites (deliberately
    over D-A2's 512-target breadth bound), none of which lead to
    `target_name` -- `target_name` is declared separately and genuinely
    unreachable, proving the walk terminates rather than hanging on a
    bushy graph."""
    prereqs = " ".join(f"w{i}" for i in range(width))
    lines = [f"test: {prereqs}\n\n"]
    for i in range(width):
        lines.append(f"w{i}:\n\techo w{i}\n\n")
    lines.append(f"{target_name}:\n\techo a\n")
    return "".join(lines)


# Copied (not imported) from tests/test_ai_kit_project_rules_precommit.py,
# per Task 2's action: "Copy the sibling's pre-commit hook helpers rather
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


# --------------------------------------------------------------------------- #
# Plan 12-02, Task 1 fixture helpers.
# --------------------------------------------------------------------------- #

_AST_ONLY_SRC_FILES = {
    "src/target_mod.py": "X = 1\n",
    "src/helper_mod.py": "Y = 2\n",
}

# The parse side: a helper function one level below `ast.parse` (the exact
# `_parse(name)` shape `tests/test_arch.py` itself uses at line 87), called
# from a wrapping function with the literal inline -- parses `target_mod`.
_AST_ONLY_HELPER_SOURCE = (
    'import ast, os\n'
    'SRC = os.path.join(os.path.dirname(__file__), "..", "src")\n'
    "\n\n"
    "def _p(n):\n"
    "    return ast.parse(open(os.path.join(SRC, n)).read())\n"
    "\n\n"
    "def t():\n"
    '    return _p("target_mod.py")\n'
)


def _ast_only_byname_load(mod_filename, alias):
    """The `TestSegmentInventory._sl`-shaped load
    (`tests/test_arch.py:605-611`): assign the module path to a LOCAL NAME
    first, then pass the NAME to `spec_from_file_location`, under an alias
    that is not the module's own name."""
    return (
        "import importlib.util\n"
        "\n\n"
        "def load():\n"
        f'    q = os.path.join(SRC, "{mod_filename}")\n'
        f'    s = importlib.util.spec_from_file_location("{alias}", q)\n'
        "    m = importlib.util.module_from_spec(s)\n"
        "    s.loader.exec_module(m)\n"
        "    return m\n"
    )


def _direct_chain_makefile(recipe):
    """A Makefile where `arch-test` is a DIRECT prerequisite of `test`, so
    every fixture built from it is chained by construction -- isolating
    these fixtures to only the AST-only check under test."""
    return f"test: arch-test\n\narch-test:\n\t{recipe}\n"


def _ast_only_repo_raw(recipe, files):
    repo = tempfile.mkdtemp()
    _write(os.path.join(repo, "Makefile"), _direct_chain_makefile(recipe))
    for rel, body in files.items():
        _write(os.path.join(repo, rel), body)
    return repo


def _ast_only_repo(backing_file_body, recipe="python3 -m unittest tests.test_arch"):
    files = dict(_AST_ONLY_SRC_FILES, **{"tests/test_arch.py": backing_file_body})
    return _ast_only_repo_raw(recipe, files)


class TestTracerAstOnlyTargetAware(unittest.TestCase):
    """D-A8's target-aware parse-vs-execute correlation (Task 1's own
    `<behavior>` fixtures, written before `ast_only.py` existed and
    confirmed to fail for the right reason -- `ImportError` -- then
    implemented against until they passed)."""

    def test_clean_file_parsing_one_module_and_loading_unrelated_one_not_flagged(self):
        # D-01's exact real shape: parses target_mod via a helper, and
        # SEPARATELY loads an UNRELATED module (helper_mod) via the
        # variable-then-pass shape, under an alias that is not the
        # module's own name.
        body = _AST_ONLY_HELPER_SOURCE + _ast_only_byname_load(
            "helper_mod.py", "helper_alias_zz"
        )
        repo = _ast_only_repo(body)
        self.assertNotIn("backing_file_executes_checked_target", _issues(repo))

    def test_named_variable_then_pass_load_of_the_parsed_module_is_flagged_by_name(self):
        # The load-bearing pair's dirty half: same variable-then-pass shape
        # as the clean fixture, but aimed at the module that IS parsed.
        # Only a real one-level name-resolution implementation on the
        # EXECUTE side catches this -- a string-in-call-only build passes
        # every inline fixture and stays inert against the live
        # tests/test_arch.py:605-611.
        body = _AST_ONLY_HELPER_SOURCE + _ast_only_byname_load(
            "target_mod.py", "target_alias_zz"
        )
        repo = _ast_only_repo(body)
        findings = [
            f for f in _findings(repo) if f["issue"] == "backing_file_executes_checked_target"
        ]
        self.assertEqual(len(findings), 1)
        text = findings[0]["summary"].lower()
        self.assertTrue("target_mod" in text or "target-mod" in text)
        self.assertNotIn("target_alias_zz", text)
        self.assertNotIn("target-alias-zz", text)

    def test_inline_import_module_call_is_flagged(self):
        body = _AST_ONLY_HELPER_SOURCE + (
            "import importlib\n\n\ndef u():\n    return importlib.import_module(\"target_mod\")\n"
        )
        repo = _ast_only_repo(body)
        self.assertIn("backing_file_executes_checked_target", _issues(repo))

    def test_plain_import_statement_is_flagged(self):
        body = _AST_ONLY_HELPER_SOURCE + "import target_mod\n"
        repo = _ast_only_repo(body)
        self.assertIn("backing_file_executes_checked_target", _issues(repo))

    def test_dotted_execute_side_normalizes_against_path_form_parse_side(self):
        body = _AST_ONLY_HELPER_SOURCE + (
            "import importlib\n\n\ndef u():\n"
            '    return importlib.import_module("src.target_mod")\n'
        )
        repo = _ast_only_repo(body)
        self.assertIn("backing_file_executes_checked_target", _issues(repo))

    def test_two_level_parser_helper_fixed_point_is_flagged(self):
        body = (
            "import ast, os\n"
            "import target_mod\n"
            'SRC = os.path.join(os.path.dirname(__file__), "..", "src")\n'
            "\n\n"
            "def _b(n):\n"
            "    return ast.parse(open(os.path.join(SRC, n)).read())\n"
            "\n\n"
            "def _a(n):\n"
            "    return _b(n)\n"
            "\n\n"
            "def t():\n"
            '    return _a("target_mod.py")\n'
        )
        repo = _ast_only_repo(body)
        self.assertIn("backing_file_executes_checked_target", _issues(repo))


class TestTracerAstOnlyNotVerifiable(unittest.TestCase):
    """D-A9's four PINNED not-verifiable reasons -- the skill never stays
    silent about a limit it has."""

    def test_not_discoverable_when_recipe_forms_a_candidate_that_does_not_resolve(self):
        # "lint-imports --config importlinter.ini" -- a config-driven tool
        # recipe with no Python file argument.
        repo = _ast_only_repo_raw(
            "lint-imports --config importlinter.ini", dict(_AST_ONLY_SRC_FILES)
        )
        findings = [f for f in _findings(repo) if f["issue"] == "ast_only_not_verifiable"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["reason"], "not_discoverable")
        self.assertNotIn("backing_file_executes_checked_target", _issues(repo))

    def test_not_python_backing_file(self):
        repo = _ast_only_repo_raw(
            "node tests/arch.spec.ts",
            dict(_AST_ONLY_SRC_FILES, **{"tests/arch.spec.ts": "export const x = 1;\n"}),
        )
        findings = [f for f in _findings(repo) if f["issue"] == "ast_only_not_verifiable"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["reason"], "not_python")

    def test_unparseable_backing_file(self):
        repo = _ast_only_repo("def broken(:\n")
        findings = [f for f in _findings(repo) if f["issue"] == "ast_only_not_verifiable"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["reason"], "unparseable")

    def test_no_parse_call_backing_file(self):
        repo = _ast_only_repo("import os\nX = os.sep\n")
        findings = [f for f in _findings(repo) if f["issue"] == "ast_only_not_verifiable"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["reason"], "no_parse_call")


class TestTracerAstOnlyGateAndContainment(unittest.TestCase):
    """D-A4's gate re-asserted after this plan's addition, and D-A7's
    containment guard against both known escape shapes."""

    def test_gate_repo_with_no_arch_test_target_produces_exactly_one_finding(self):
        repo = tempfile.mkdtemp()
        _write(os.path.join(repo, "Makefile"), "test: unit\n\nunit:\n\techo u\n")
        findings = _findings(repo)
        self.assertEqual(len(findings), 1)
        self.assertIn("arch_test_target_missing", _issues(repo))

    def test_parent_traversal_escape_is_rejected_as_not_discoverable(self):
        outer = tempfile.mkdtemp()
        repo = os.path.join(outer, "repo")
        os.makedirs(repo)
        leak = (
            "import ast\nimport leaked_mod\n\n\ndef p():\n"
            '    return ast.parse(open("leaked_mod.py").read())\n'
        )
        _write(os.path.join(outer, "outside.py"), leak)
        _write(os.path.join(repo, "Makefile"), _direct_chain_makefile("python3 ../outside.py"))
        for rel, body in _AST_ONLY_SRC_FILES.items():
            _write(os.path.join(repo, rel), body)
        findings = [f for f in _findings(repo) if f["issue"] == "ast_only_not_verifiable"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["reason"], "not_discoverable")
        self.assertNotIn("backing_file_executes_checked_target", _issues(repo))

    def test_sibling_prefix_escape_is_rejected_as_not_discoverable(self):
        # `<tmp>/repo-evil` is a SIBLING of `<tmp>/repo` whose name merely
        # extends the root's -- the case a bare unresolved `startswith`
        # would accept.
        outer = tempfile.mkdtemp()
        repo = os.path.join(outer, "repo")
        evil = os.path.join(outer, "repo-evil")
        os.makedirs(repo)
        os.makedirs(evil)
        leak = (
            "import ast\nimport leaked_mod\n\n\ndef p():\n"
            '    return ast.parse(open("leaked_mod.py").read())\n'
        )
        _write(os.path.join(evil, "leak.py"), leak)
        _write(
            os.path.join(repo, "Makefile"),
            _direct_chain_makefile(f"python3 {os.path.join(evil, 'leak.py')}"),
        )
        for rel, body in _AST_ONLY_SRC_FILES.items():
            _write(os.path.join(repo, rel), body)
        findings = [f for f in _findings(repo) if f["issue"] == "ast_only_not_verifiable"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["reason"], "not_discoverable")
        self.assertNotIn("backing_file_executes_checked_target", _issues(repo))


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


class TestTargetExistencePaired(unittest.TestCase):
    """Target existence, paired (Task 2 (a))."""

    def test_no_shaped_target_flags_existence_exactly_once(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test: test-unit\n\ntest-unit:\n\techo t\n",
            )
            self.assertEqual(_issues(repo), ["arch_test_target_missing"])

    def test_present_and_chained_target_not_flagged_for_existence(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test: test-unit arch-test\n\ntest-unit:\n\techo t\n\n"
                "arch-test:\n\techo a\n",
            )
            self.assertEqual(_findings(repo), [])


class TestChainingPaired(unittest.TestCase):
    """Chaining, paired (Task 2 (a))."""

    def test_unreached_target_flags_chaining_exactly_once(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test: test-unit\n\ntest-unit:\n\techo t\n\narch-test:\n\techo a\n",
            )
            self.assertEqual(_issues(repo), ["arch_test_not_chained"])

    def test_prerequisite_added_not_flagged_for_chaining(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test: test-unit arch-test\n\ntest-unit:\n\techo t\n\n"
                "arch-test:\n\techo a\n",
            )
            self.assertNotIn("arch_test_not_chained", _issues(repo))


class TestEvaluationGate(unittest.TestCase):
    """D-A4's evaluation gate: the no-target repo produces EXACTLY ONE
    finding. Assert the length, not just membership -- a cascade is the
    failure this gate exists to prevent and a membership-only assertion
    passes for the cascade too."""

    def test_missing_target_repo_produces_exactly_one_finding(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test: test-unit\n\ntest-unit:\n\techo t\n",
            )
            self.assertEqual(len(_findings(repo)), 1)


class TestShapeRulePositiveAlternatives(unittest.TestCase):
    """D-A1's positive alternatives: each name below is arch-test-shaped,
    so the existence finding must NOT fire (the shape rule is satisfied)."""

    def _shaped_repo_findings(self, target_header):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                f"test: test-unit {target_header}\n\ntest-unit:\n\techo t\n\n"
                f"{target_header}:\n\techo a\n",
            )
            return _findings(repo)

    def test_arch_test_literal_shape_satisfied(self):
        self.assertEqual(self._shaped_repo_findings("arch-test"), [])

    def test_arch_test_underscore_shape_satisfied(self):
        self.assertEqual(self._shaped_repo_findings("arch_test"), [])

    def test_arch_bare_shape_satisfied(self):
        self.assertEqual(self._shaped_repo_findings("arch"), [])

    def test_arch_check_shape_satisfied(self):
        self.assertEqual(self._shaped_repo_findings("arch-check"), [])

    def test_architecture_test_shape_satisfied(self):
        self.assertEqual(self._shaped_repo_findings("architecture-test"), [])

    def test_test_arch_prefixed_shape_satisfied(self):
        self.assertEqual(self._shaped_repo_findings("test-arch"), [])


class TestShapeRuleNegativeAlternatives(unittest.TestCase):
    """D-A1's negative half -- the one that matters: an unanchored pattern
    passes every positive case and silently accepts `archive`, which is
    the false-NEGATIVE direction that hides a real gap."""

    def _unshaped_repo_issues(self, target_header):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                f"test: test-unit\n\ntest-unit:\n\techo t\n\n{target_header}:\n\techo z\n",
            )
            return _issues(repo)

    def test_archive_target_missing_flagged(self):
        self.assertEqual(self._unshaped_repo_issues("archive"), ["arch_test_target_missing"])

    def test_arch_docs_target_missing_flagged(self):
        self.assertEqual(self._unshaped_repo_issues("arch-docs"), ["arch_test_target_missing"])

    def test_architecture_diagrams_target_missing_flagged(self):
        self.assertEqual(
            self._unshaped_repo_issues("architecture-diagrams"), ["arch_test_target_missing"]
        )


class TestShapeRuleDeterminism(unittest.TestCase):
    """A repo declaring BOTH `arch` and `arch-test` names the same target
    on repeated runs, AND names the one declared FIRST -- the mechanism is
    the shared ordered reader `parse_makefile_targets_ordered`, never
    lexicographic order and never set iteration (which has no order)."""

    def test_arch_declared_first_is_chosen(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "arch:\n\techo a1\n\narch-test:\n\techo a2\n\ntest: arch\n",
            )
            from ai_kit_rules_common.makefile_parse import parse_makefile_targets_ordered

            target = arch_checker.find_arch_test_shaped_target(
                parse_makefile_targets_ordered(os.path.join(repo, "Makefile"))
            )
            self.assertEqual(target, "arch")

    def test_arch_test_declared_first_is_chosen(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "arch-test:\n\techo a2\n\narch:\n\techo a1\n\ntest: arch-test\n",
            )
            from ai_kit_rules_common.makefile_parse import parse_makefile_targets_ordered

            target = arch_checker.find_arch_test_shaped_target(
                parse_makefile_targets_ordered(os.path.join(repo, "Makefile"))
            )
            self.assertEqual(target, "arch-test")


class TestFindingSchema(unittest.TestCase):
    """D-A3's finding schema: every finding this skill emits carries
    exactly the six pinned fields and carries NO identifier key of the
    Makefile sibling's kind (`remediation.py:86`'s precedence is why: a
    `target` key would silently repoint the remediate `id`). Each
    `remediate` entry's `id` equals its finding's `category`, and the
    existence and chaining findings produce two DIFFERENT ids."""

    _SCHEMA_FIELDS = {
        "category",
        "issue",
        "criticality",
        "summary",
        "recommendation",
        "needs_research",
    }

    def test_missing_target_finding_has_exact_schema_and_no_target_key(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test: test-unit\n\ntest-unit:\n\techo t\n",
            )
            finding = _findings(repo)[0]
            self.assertEqual(set(finding), self._SCHEMA_FIELDS)
            self.assertNotIn("target", finding)

    def test_not_chained_finding_has_exact_schema_and_no_target_key(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test: test-unit\n\ntest-unit:\n\techo t\n\narch-test:\n\techo a\n",
            )
            finding = _findings(repo)[0]
            self.assertEqual(set(finding), self._SCHEMA_FIELDS)
            self.assertNotIn("target", finding)

    def test_remediate_ids_equal_categories_and_are_distinct(self):
        with (
            tempfile.TemporaryDirectory() as repo_missing,
            tempfile.TemporaryDirectory() as repo_unchained,
        ):
            _write(
                os.path.join(repo_missing, "Makefile"),
                "test: test-unit\n\ntest-unit:\n\techo t\n",
            )
            _write(
                os.path.join(repo_unchained, "Makefile"),
                "test: test-unit\n\ntest-unit:\n\techo t\n\narch-test:\n\techo a\n",
            )
            missing_result = cli.remediate(repo_missing)
            unchained_result = cli.remediate(repo_unchained)
            missing_check = cli.check(repo_missing)["arch"]
            unchained_check = cli.check(repo_unchained)["arch"]
            self.assertEqual(missing_result["remediate"][0]["id"], missing_check[0]["category"])
            self.assertEqual(
                unchained_result["remediate"][0]["id"], unchained_check[0]["category"]
            )
            ids = {missing_result["remediate"][0]["id"], unchained_result["remediate"][0]["id"]}
            self.assertEqual(len(ids), 2)


class TestChainingMechanisms(unittest.TestCase):
    """D-A2's three mechanisms, each its own method plus a non-triggering
    counterpart, plus the token-boundary boundary case."""

    def test_direct_prerequisite_is_chained(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test: arch-test\n\narch-test:\n\techo a\n",
            )
            self.assertEqual(_findings(repo), [])

    def test_no_direct_prerequisite_not_chained(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test: test-unit\n\ntest-unit:\n\techo t\n\narch-test:\n\techo a\n",
            )
            self.assertIn("arch_test_not_chained", _issues(repo))

    def test_transitive_prerequisite_through_one_aggregate_is_chained(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test: test-all\n\ntest-all: unit arch-test\n\nunit:\n\techo u\n\n"
                "arch-test:\n\techo a\n",
            )
            self.assertEqual(_findings(repo), [])

    def test_recipe_invocation_by_name_is_chained(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test:\n\t$(MAKE) arch-test\n\narch-test:\n\techo a\n",
            )
            self.assertEqual(_findings(repo), [])

    def test_recipe_mentioning_longer_hyphenated_token_not_chained(self):
        # `arch-test-integration` must NOT satisfy `arch-test` -- the
        # shared helper's both-ends token boundary is what buys this; a
        # plain substring implementation would pass every other case here.
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test:\n\t$(MAKE) arch-test-integration\n\narch-test:\n\techo a\n\n"
                "arch-test-integration:\n\techo ai\n",
            )
            self.assertIn("arch_test_not_chained", _issues(repo))


class TestGraphSafety(unittest.TestCase):
    """Cycle safety AND breadth safety: a Makefile whose prerequisite
    graph contains a cycle returns a verdict and does not hang, and a
    Makefile whose `test` has a fan-out larger than D-A2's 512-target
    breadth bound also returns a verdict rather than walking forever.
    Paired with the depth bound's honest degradation: a linear chain
    longer than 8 hops is reported not-chained (deliberate degradation
    for a graph the checker declined to finish reading, not a bug to tune
    away), paired with the same chain one hop inside the bound, which
    must come back chained."""

    def test_cyclic_prerequisites_returns_verdict(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "test: a\n\na: b\n\nb: a\n\narch-test:\n\techo a\n",
            )
            issues = _issues(repo)
            self.assertEqual(issues, ["arch_test_not_chained"])

    def test_wide_fanout_returns_verdict(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), _wide_fanout_makefile())
            issues = _issues(repo)
            self.assertEqual(issues, ["arch_test_not_chained"])

    def test_chain_within_depth_bound_is_chained(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), _linear_chain_makefile(8))
            self.assertEqual(_findings(repo), [])

    def test_chain_exceeding_depth_bound_not_chained(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), _linear_chain_makefile(9))
            self.assertIn("arch_test_not_chained", _issues(repo))


class TestDegradation(unittest.TestCase):
    """A repo with no `Makefile` at all, and a repo with an empty
    `Makefile`, each return a list and never raise."""

    def test_no_makefile_returns_list_without_raising(self):
        with tempfile.TemporaryDirectory() as repo:
            result = _findings(repo)
            self.assertIsInstance(result, list)
            self.assertEqual([f["issue"] for f in result], ["arch_test_target_missing"])

    def test_empty_makefile_returns_list_without_raising(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(os.path.join(repo, "Makefile"), "")
            result = _findings(repo)
            self.assertIsInstance(result, list)
            self.assertEqual([f["issue"] for f in result], ["arch_test_target_missing"])


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


class TestGateRegistration(unittest.TestCase):
    def test_makefile_registers_module_and_package(self):
        with open(_MAKEFILE_PATH, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("tests.test_ai_kit_project_rules_arch", text)
        self.assertIn("skills/ai-kit-project-rules-arch/", text)

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
        self.assertIn("tests.test_ai_kit_project_rules_arch", match.group(1))

    def test_pyright_include_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        include = data["tool"]["pyright"]["include"]
        self.assertIn("skills/ai-kit-project-rules-arch", include)

    def test_vulture_paths_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        paths = data["tool"]["vulture"]["paths"]
        self.assertIn("skills/ai-kit-project-rules-arch", paths)


if __name__ == "__main__":
    unittest.main()
