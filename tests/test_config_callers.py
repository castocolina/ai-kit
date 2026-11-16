"""Caller scans that keep the old roster name and foreign keys out of ai-kit (SPEC R6, R8; D-10,
D-17, D-18; review concern C1-19; plan 33-11 Task 2).

Static scans read the source tree only. TestNoPlanning runs the CLI inside a temporary repository
with a temporary HOME and XDG folder and checks that no `.planning/` is needed or created."""

import ast
import io
import os
import re
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
RUNNER_TEMPLATE = REPO / "skills" / "ai-kit-spec-review" / "references" / "cross-ai.mjs"
MIGRATION_SOURCE = REPO / "skills" / "ai-kit-spec-review" / "ai_kit_spec" / "config_migrate.py"
OLD_NAMES = ("review-spec.toml", "review-spec-trust")
RUNTIME_SUFFIXES = (".py", ".mjs")
WRITE_ATTRS = frozenset({
    "write_text", "write_bytes", "replace", "rename", "unlink", "remove", "rmtree", "copyfile",
    "copy", "copy2", "move", "dump", "mkstemp", "symlink_to", "touch",
})
WRITE_HELPERS = frozenset({
    "cache_write_text", "cache_write_bytes", "cache_write_json", "_atomic_write_json",
    "_atomic_copy", "write_toml_preserving", "write_toml_region_replace",
})
FN_LINE = re.compile(r"^(?:async )?function (\w+)")
GSD_LITERAL = re.compile(r"""['"]\.planning['"]""")
JS_WRITE = re.compile(
    r"\b(writeFileSync|writeFileAtomic|renameSync|unlinkSync|rmSync|copyFileSync|"
    r"appendFileSync|symlinkSync)\("
)
# Each write site is `<repo-relative path>::<function>`. Every entry is a reviewed reason.
ALLOWED_GSD_WRITES = frozenset({
    # the one-time removal of the legacy workflow.cross_ai_retry block (D-13, D-17)
    "skills/ai-kit-spec-review/references/cross-ai.mjs::migrateRetrySources",
    # self-test fixtures: a scratch repository with a synthetic GSD config
    "skills/ai-kit-spec-review/references/cross-ai.mjs::runSelfTestCase",
    "skills/ai-kit-spec-review/references/cross-ai.mjs::blackBoxSelfTest",
    # the environment matrix's scratch repository (a synthetic config with model_profile only)
    "tools/env_matrix.py::custom_tmpdir",
})

sys.path.insert(0, str(REPO / "skills" / "ai-kit-spec-review"))
from ai_kit_spec import cli
from ai_kit_spec.runner_dispatch import RunnerResult

NO_RUNTIMES = {"which_fn": lambda _name, **_kwargs: None, "run_fn": lambda *_a, **_k: None}


def old_name_problem(path, line) -> bool:
    """True when a line names the old roster outside a migration note: any mention in runtime
    code, and a mention in Markdown or JSON whose line does not also say `migrat`."""
    if not any(name in line for name in OLD_NAMES):
        return False
    if str(path).endswith(RUNTIME_SUFFIXES):
        return True
    return "migrat" not in line.lower()


def enclosing_function(lines, index) -> str:
    """The name of the top-level `function` that owns lines[index]. A comment block directly above
    a declaration documents that declaration; any other line belongs to the nearest declaration
    above it."""
    if lines[index].lstrip().startswith("//"):
        following = next((line for line in lines[index:]
                          if not line.lstrip().startswith("//")), "")
        match = FN_LINE.match(following)
        if match:
            return match.group(1)
    for position in range(index, -1, -1):
        match = FN_LINE.match(lines[position])
        if match:
            return match.group(1)
    return "<module>"


def _mode_of(call, position):
    if len(call.args) > position and isinstance(call.args[position], ast.Constant):
        return call.args[position].value
    for keyword in call.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            return keyword.value.value
    return None


def _is_write_call(call) -> bool:
    func = call.func
    if isinstance(func, ast.Name):
        if func.id == "open":
            mode = _mode_of(call, 1)
            return isinstance(mode, str) and any(ch in mode for ch in "wax+")
        return func.id in WRITE_HELPERS
    if isinstance(func, ast.Attribute):
        if func.attr == "open":
            mode = _mode_of(call, 0)
            return isinstance(mode, str) and any(ch in mode for ch in "wax+")
        return func.attr in WRITE_ATTRS or func.attr in WRITE_HELPERS
    return False


def _scope_nodes(scope, is_module):
    """Every node of a scope; a module scope stops at its function definitions."""
    stack = list(scope)
    while stack:
        node = stack.pop()
        yield node
        if is_module and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        stack.extend(ast.iter_child_nodes(node))


def py_gsd_write_sites(text) -> list:
    """Names of the scopes (functions, or <module>) that name both `.planning` and `config.json`
    in their string constants and hold a write call."""
    tree = ast.parse(text)
    scopes = [("<module>", 0, list(tree.body), True)]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scopes.append((node.name, node.lineno, [node], False))
    sites = []
    for name, _lineno, scope, is_module in sorted(scopes, key=lambda item: item[1]):
        nodes = list(_scope_nodes(scope, is_module))
        strings = [n.value for n in nodes
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        names_gsd = (any(".planning" in s for s in strings)
                     and any("config.json" in s for s in strings))
        writes = any(isinstance(n, ast.Call) and _is_write_call(n) for n in nodes)
        if names_gsd and writes:
            sites.append(name)
    return sites


def js_gsd_write_sites(text) -> list:
    """Names of the top-level functions of a JavaScript text that hold a `'.planning'` literal and
    a file-write call."""
    chunks = {"<header>": []}
    current = "<header>"
    for line in text.splitlines():
        match = FN_LINE.match(line)
        if match:
            current = match.group(1)
            chunks.setdefault(current, [])
        chunks[current].append(line)
    sites = []
    for name, body_lines in chunks.items():
        body = "\n".join(body_lines)
        if GSD_LITERAL.search(body) and JS_WRITE.search(body):
            sites.append(name)
    return sites


def _walk(patterns):
    found = set()
    for pattern in patterns:
        for path in REPO.glob(pattern):
            if path.is_file() and "__pycache__" not in path.parts and ".venv" not in path.parts:
                found.add(path)
    return sorted(found)


class TestOldNameScan(unittest.TestCase):
    def _problems(self, paths):
        problems = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for number, line in enumerate(text.splitlines(), start=1):
                if old_name_problem(path, line):
                    problems.append(f"{path.relative_to(REPO).as_posix()}:{number}: {line.strip()}")
        return problems

    def test_no_runtime_code_names_the_old_roster(self):
        runtime = [p for p in _walk(["skills/**/*.py", "tools/**/*.py", "skills/**/*.mjs"])
                   if p != MIGRATION_SOURCE]
        self.assertGreater(len(runtime), 50)
        self.assertEqual(self._problems(runtime), [])

    def test_docs_name_the_old_roster_only_as_a_migration_source(self):
        docs = _walk(["skills/**/*.md", "skills/**/*.json", "README.md", "docs/config/**/*.md"])
        self.assertGreater(len(docs), 10)
        self.assertEqual(self._problems(docs), [])
        named = [p for p in REPO.glob("skills/**/*") if p.name == "review-spec.toml"]
        self.assertEqual(named, [])

    def test_scan_is_not_vacuous(self):
        self.assertTrue(old_name_problem("SKILL.md", "see review-spec.toml"))
        self.assertFalse(old_name_problem("SKILL.md", "migrates from review-spec.toml"))
        self.assertTrue(old_name_problem("tools/x.py", '    """Reads review-spec.toml."""'))


class TestForeignKeys(unittest.TestCase):
    def test_no_python_names_cross_ai_retry(self):
        hits = [p.relative_to(REPO).as_posix()
                for p in _walk(["skills/**/*.py", "tools/**/*.py"])
                if "cross_ai_retry" in p.read_text(encoding="utf-8")]
        self.assertEqual(hits, [])

    def test_runner_names_cross_ai_retry_only_in_the_migrator(self):
        lines = RUNNER_TEMPLATE.read_text(encoding="utf-8").splitlines()
        first_import = next(i for i, line in enumerate(lines) if line.startswith("import "))
        allowed = {"migrateRetrySources", "removeRetryBlock", "blackBoxSelfTest"}
        for index, line in enumerate(lines):
            if "cross_ai_retry" not in line or index < first_import:
                continue
            self.assertIn(enclosing_function(lines, index), allowed, f"line {index + 1}")

    def test_enclosing_function_finder_is_not_vacuous(self):
        lines = ["function a() {", "  x;", "}", "// doc for b", "// more", "function b() {", "  y;",
                 "}"]
        self.assertEqual(enclosing_function(lines, 6), "b")
        self.assertEqual(enclosing_function(lines, 3), "b")
        self.assertEqual(enclosing_function(lines, 1), "a")

    def test_gsd_config_writes_only_through_allowed_paths(self):
        labels = set()
        for path in _walk(["skills/**/*.py", "tools/**/*.py"]):
            rel = path.relative_to(REPO).as_posix()
            for scope in py_gsd_write_sites(path.read_text(encoding="utf-8")):
                labels.add(f"{rel}::{scope}")
        template = RUNNER_TEMPLATE.relative_to(REPO).as_posix()
        for name in js_gsd_write_sites(RUNNER_TEMPLATE.read_text(encoding="utf-8")):
            labels.add(f"{template}::{name}")
        outside = sorted(labels - ALLOWED_GSD_WRITES)
        self.assertEqual(outside, [], "GSD config write outside the allowed paths")
        self.assertIn(f"{template}::migrateRetrySources", labels)

    def test_write_scan_is_not_vacuous(self):
        bad = ('import json\nimport os\n\ndef bad(root):\n'
               '    json.dump({"workflow": {"x": 1}}, '
               'open(os.path.join(root, ".planning", "config.json"), "w"))\n')
        reader = ('import os\n\ndef reader(root):\n'
                  '    with open(os.path.join(root, ".planning", "config.json"),'
                  ' encoding="utf-8") as handle:\n        return handle.read()\n')
        indirect = ('from pathlib import Path\n\ndef indirect(root):\n'
                    '    parts = [".planning", "config.json"]\n'
                    '    Path(root, *parts).write_text("{}")\n')
        self.assertEqual(py_gsd_write_sites(bad), ["bad"])
        self.assertEqual(py_gsd_write_sites(reader), [])
        self.assertEqual(py_gsd_write_sites(indirect), ["indirect"])
        js_bad = ("function bad(cwd) {\n"
                  "  fs.writeFileSync(path.join(cwd, '.planning', 'config.json'), '{}');\n"
                  "}\n")
        js_read = ("function reads(cwd) {\n"
                   "  return fs.readFileSync(path.join(cwd, '.planning', 'config.json'), 'utf8');\n"
                   "}\n")
        self.assertEqual(js_gsd_write_sites(js_bad), ["bad"])
        self.assertEqual(js_gsd_write_sites(js_read), [])
        self.assertEqual(js_gsd_write_sites(js_bad.replace("\n", "\r\n")), ["bad"])
        self.assertEqual(py_gsd_write_sites(bad.replace("\n", "\r\n")), ["bad"])


LOCAL_TOML = (
    '[lanes]\nstrategy = "global-merge"\n\n'
    '[[lanes.review]]\nkey = "local"\nruntime = "pi"\nmodel = "fake/m"\n'
)
USER_TOML = (
    '[lanes]\nstrategy = "global-merge"\n\n'
    '[[lanes.review]]\nkey = "global"\nruntime = "pi"\nmodel = "fake/g"\n'
)


def _tree_bytes(root):
    snapshot = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            full = os.path.join(dirpath, name)
            with open(full, "rb") as handle:
                snapshot[full] = handle.read()
    return snapshot


class TestNoPlanning(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="ai-kit-no-planning-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.repo = os.path.join(self._tmp, "repo")
        self.home = os.path.join(self._tmp, "home")
        self.xdg = os.path.join(self._tmp, "xdg")
        self.cache = os.path.join(self._tmp, "cache")
        self.quota = os.path.join(self._tmp, "quota", "quota.json")
        os.makedirs(os.path.join(self.repo, ".aikit"))
        os.makedirs(os.path.join(self.xdg, "ai-kit"))
        with open(os.path.join(self.repo, ".aikit", "config.toml"), "w", encoding="utf-8") as h:
            h.write(LOCAL_TOML)
        with open(os.path.join(self.xdg, "ai-kit", "config.toml"), "w", encoding="utf-8") as h:
            h.write(USER_TOML)
        env = {"HOME": self.home, "XDG_CONFIG_HOME": self.xdg, "XDG_CACHE_HOME": self.cache}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def _fake_runner(spec, prompt, seams):
        del spec, prompt, seams
        return RunnerResult(0, "", {"status": "ok"}, None, False, ["node", "runner"], "")

    def _run_all(self):
        runs = [
            ["resolve-reviewers", "--cwd", self.repo, "--quota-path", self.quota],
            ["probe-quota", "--cwd", self.repo, "--quota-path", self.quota,
             "--no-save-runtimes", "--no-migrate"],
            ["check-providers", "--cwd", self.repo],
        ]
        codes, text = [], []
        for argv in runs:
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                codes.append(cli.main(argv, runner_fn=self._fake_runner,
                                      custom_fn=self._fake_runner, **NO_RUNTIMES))
            text.extend([out.getvalue(), err.getvalue()])
        return codes, "\n".join(text)

    def test_three_commands_run_without_planning(self):
        codes, text = self._run_all()
        self.assertEqual(codes, [0, 0, 0])
        self.assertNotIn(".planning", text)
        self.assertNotIn("GSD", text)
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".planning")))

    def test_second_round_changes_no_repository_byte(self):
        self._run_all()
        before = _tree_bytes(self.repo)
        codes, _text = self._run_all()
        self.assertEqual(codes, [0, 0, 0])
        self.assertEqual(_tree_bytes(self.repo), before)
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".planning")))


if __name__ == "__main__":
    unittest.main()
