"""cst-refactor's contract: SKILL.md and the codemod template agree.

LibCST is never imported here.
"""

import ast
import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skills" / "cst-refactor"
TEMPLATE = SKILL / "codemod_template.py.txt"
SKILL_MD = SKILL / "SKILL.md"
FENCE = re.compile(r"^```")
COMMAND_RE = re.compile(r"tools/codemod_template\.py\s+([a-z][a-z-]*)(.*)")


def _section(text: str, heading: str) -> list[str]:
    """Lines under `## heading` up to the next level-2 heading."""
    lines = text.split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith(f"## {heading}"))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start + 1 : end]


def _fenced_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in text.split("\n"):
        if FENCE.match(line):
            if current is None:
                current = []
            else:
                blocks.append(current)
                current = None
        elif current is not None:
            current.append(line)
    return blocks


def _first_string(call: ast.Call) -> str | None:
    if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
        return call.args[0].value
    return None


def _attr_name(node: ast.expr) -> str | None:
    return node.attr if isinstance(node, ast.Attribute) else None


def template_flags() -> dict[str, set[str]]:
    """Subcommand -> its `--` flags, read from the template's argparse calls with `ast`."""
    tree = ast.parse(TEMPLATE.read_text(encoding="utf-8"))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    common = {
        flag
        for node in ast.walk(functions["_add_common_args"])
        if isinstance(node, ast.Call) and _attr_name(node.func) == "add_argument"
        for flag in [_first_string(node)]
        if flag and flag.startswith("--")
    }
    parse_args = functions["parse_args"]
    mapping: dict[str, str] = {}
    flags: dict[str, set[str]] = {}
    for node in ast.walk(parse_args):
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and _attr_name(node.value.func) == "add_parser"
            and isinstance(node.targets[0], ast.Name)
        ):
            name = _first_string(node.value)
            if name is not None:
                mapping[node.targets[0].id] = name
                flags[name] = set()
    for node in ast.walk(parse_args):
        if not isinstance(node, ast.Call):
            continue
        if (
            _attr_name(node.func) == "add_argument"
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in mapping
        ):
            flag = _first_string(node)
            if flag and flag.startswith("--"):
                flags[mapping[node.func.value.id]].add(flag)
        elif (
            isinstance(node.func, ast.Name)
            and node.func.id == "_add_common_args"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id in mapping
        ):
            flags[mapping[node.args[0].id]] |= common
    return flags


def command_flags(line: str) -> tuple[str, set[str]] | None:
    """Subcommand and `--` flags of a `tools/codemod_template.py <sub> ...` line, or None."""
    match = COMMAND_RE.search(line)
    if match is None:
        return None
    return match.group(1), {token for token in match.group(2).split() if token.startswith("--")}


def documented_flags() -> dict[str, set[str]]:
    """Subcommand -> its `--` flags, unioned over every SKILL.md code-block command line."""
    documented: dict[str, set[str]] = {}
    for block in _fenced_blocks(SKILL_MD.read_text(encoding="utf-8")):
        for line in block:
            parsed = command_flags(line)
            if parsed is None:
                continue
            name, flags = parsed
            documented.setdefault(name, set()).update(flags)
    return documented


class TestTemplateContract(unittest.TestCase):
    def test_command_line_parser(self):
        rows = [
            (
                'cp "<this skill\'s directory>/codemod_template.py.txt" tools/codemod_template.py',
                None,
            ),
            ("mkdir -p tools", None),
            (
                "uv run python tools/codemod_template.py add-parameter --function f "
                "--param p --default 1 --paths src",
                ("add-parameter", {"--function", "--param", "--default", "--paths"}),
            ),
        ]
        for line, expected in rows:
            with self.subTest(line=line):
                self.assertEqual(command_flags(line), expected)

    def test_subcommands_match(self):
        self.assertEqual(sorted(documented_flags()), sorted(template_flags()))

    def test_flags_match_per_subcommand(self):
        documented = documented_flags()
        for name, flags in sorted(template_flags().items()):
            with self.subTest(subcommand=name):
                self.assertEqual(documented.get(name, set()), flags)

    def test_template_has_the_five_subcommands(self):
        self.assertEqual(
            set(template_flags()),
            {
                "rename-symbol",
                "rename-parameter",
                "add-parameter",
                "remove-parameter",
                "rewrite-docstring",
            },
        )


def libcst_imports(tree: ast.AST) -> list[str]:
    """Module names of every `libcst` import in the tree (`import` and `from ... import`)."""
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        else:
            continue
        hits.extend(name for name in names if name.split(".")[0] == "libcst")
    return hits


class TestSkillText(unittest.TestCase):
    """SKILL.md states what the template does, the validation loop and the recovery step."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text(encoding="utf-8")

    def _bullet(self, name: str) -> str:
        prefix = f"- `{name}`:"
        hits = [
            line
            for line in _section(self.text, "What each subcommand changes")
            if line.startswith(prefix)
        ]
        self.assertEqual(len(hits), 1, f"expected one bullet for {name}")
        return hits[0]

    def test_validation_loop_order(self):
        steps = [line for line in _section(self.text, "Validation loop") if line.strip()]
        markers = ["--paths", "git diff", "tests", "git restore", "Repeat", "rg -n"]
        self.assertEqual(len(steps), len(markers))
        for number, (step, marker) in enumerate(zip(steps, markers, strict=True), start=1):
            with self.subTest(step=number):
                self.assertTrue(step.startswith(f"{number}. "))
                self.assertIn(marker, step)

    def test_parse_failure_recovery(self):
        bullets = [line for line in self.text.split("\n") if "fails to parse" in line]
        self.assertTrue(any("git restore <paths>" in line for line in bullets))

    def test_subcommand_outcomes_stated(self):
        add = self._bullet("add-parameter")
        self.assertIn("without `--call-value`", add)
        self.assertIn("call sites", add)
        remove = self._bullet("remove-parameter")
        for word in ("*args", "**kwargs", "positional"):
            self.assertIn(word, remove)
        self.assertIn("f-string", self._bullet("rewrite-docstring"))
        rename = self._bullet("rename-symbol")
        self.assertIn("comments", rename)
        self.assertIn("string", rename)

    def test_idempotency_stated(self):
        self.assertIn("a second run of the same rename changes nothing", self.text)

    def test_no_tighten_matchers_instruction(self):
        self.assertNotIn("Tighten matchers", self.text)


class TestNoRuntimeLibcst(unittest.TestCase):
    """LibCST is dev-only: no tracked runtime `.py` under skills/ or tools/ imports it."""

    def test_no_runtime_file_imports_libcst(self):
        listed = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "-z", "--", "skills", "tools"],
            capture_output=True,
            check=True,
        ).stdout.decode("utf-8")
        hits: list[str] = []
        for name in listed.split("\0"):
            if name.endswith(".py"):
                tree = ast.parse((REPO / name).read_text(encoding="utf-8"))
                hits.extend(f"{name}: {module}" for module in libcst_imports(tree))
        self.assertEqual(hits, [])

    def test_libcst_import_check_catches_an_import(self):
        tree = ast.parse("import libcst\nfrom libcst import matchers\n")
        self.assertEqual(len(libcst_imports(tree)), 2)
