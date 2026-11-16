# tests/test_jev_fast_decision_guard.py
"""D-13 / SPEC R9 guard over `skills/jev-fast-decision`.

The skill has no Zen or other removed backend, `opencode` appears only as a host folder, and no
step hands Laya's or the official typesafe-ai skill's install or upgrade to tools-installer or
another repository. The Laya server's lifecycle is the owner's.

Bounded rule: a prohibition such as "this skill never upgrades Laya" passes because its negation
sits right before the verb. Any other phrasing that names an install or upgrade of Laya or the
official skill together with a hand-off word fails on purpose and gets reworded.

stdlib `unittest` only. The guard reads the skill tree and this module's own fixtures; it never
reads `.planning/`, the network or a real host.
"""

import ast
import importlib.util
import io
import re
import tempfile
import tokenize
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO / "skills" / "jev-fast-decision"
SCANNED_SUFFIXES = (".py", ".md", ".json", ".jsonl")

ZEN = re.compile(r"\bzen\b", re.I)
OPENCODE = re.compile(r"opencode", re.I)
# Host-folder lines that may name opencode (skills folder, hosts list, a near-miss query).
OPENCODE_ALLOWED = (
    "opencode/skills",
    "Claude Code and opencode",
    "opencode, pi and Cursor",
    "codex and opencode both review",
)
INSTALLER = re.compile(r"tools-installer", re.I)
# `(?<![-.\w])` keeps `--check-updates` and `dict.update` out of the install-verb family.
STEP = re.compile(r"(?<![-.\w])(?:re)?(?:install|upgrad|updat)\w*", re.I)
SUBJECT = re.compile(r"\b(?:laya|typesafe-ai|official skill)\b", re.I)
HANDOFF = re.compile(
    r"\brepo(?:s|sitory|sitories)?\b|\bllm-env\b|tools-installer"
    r"|\bdelegat\w*|\bhand(?:s|ed|ing)?\s+(?:\w+\s+)?(?:off|over)\b"
    r"|\b(?:another|other|separate)\s+(?:tool|project|team|package)s?\b",
    re.I,
)
# A negation exempts only the verbs its match covers (at most two words before the verb).
# `not` followed by `only` or `just` is not a negation: "not only install" still delegates.
NEGATED_STEP = re.compile(
    r"\b(?:never|not(?!\W+(?:only|just)\b)|no|nor|cannot|don't|doesn't|won't)\b"
    r"(?:\W+\w+){0,2}\W+(?:re)?(?:install|upgrad|updat)\w*",
    re.I,
)
TOOL_ARGV = frozenset({
    "pip", "pip3", "pipx", "uv", "npm", "pnpm", "npx", "docker", "podman",
    "systemctl", "brew", "apt", "apt-get", "dnf",
})
TOOL_TEXT = re.compile(
    r"\b(pip3?|pipx|uv) install\b|\bdocker (run|pull|compose)\b|\bpodman (run|pull)\b|\bsystemctl\b"
)
NUMBERED = re.compile(r"\d+\.\s")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def skill_files(root):
    """Every scanned file under `root`, sorted, outside any `__pycache__` folder."""
    return sorted(
        path for path in root.rglob("*")
        if path.is_file() and path.suffix in SCANNED_SUFFIXES and "__pycache__" not in path.parts
    )


def _sentences(line, block):
    return [(line, part) for part in SENTENCE_END.split(block) if part.strip()]


def _markup_units(text):
    """Sentences of Markdown, JSON or docstring text; wrapped lines are joined into one block."""
    units = []
    block = []
    first = 0
    for number, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not stripped:
            if block:
                units.extend(_sentences(first, " ".join(block)))
                block = []
            continue
        starts_block = (
            not block
            or stripped.startswith(("- ", "* ", "#", "|"))
            or NUMBERED.match(stripped) is not None
        )
        if block and starts_block:
            units.extend(_sentences(first, " ".join(block)))
            block = []
        if not block:
            first = number
        block.append(stripped)
    if block:
        units.extend(_sentences(first, " ".join(block)))
    return units


def _python_units(text):
    """Sentences of every docstring and every comment; code lines are left to the code rule."""
    units = []
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node)
            if doc:
                units.extend((getattr(node, "lineno", 1), s) for _, s in _markup_units(doc))
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            units.extend(_sentences(token.start[0], token.string.lstrip("#").strip()))
    return units


def prose_units(suffix, text):
    """(line number, sentence) pairs for the prose of one file."""
    if suffix == ".py":
        return _python_units(text)
    return _markup_units(text)


def delegation_problem(sentence):
    """True when one sentence names Laya or the official skill, an install or upgrade,
    and a hand-off word."""
    rest = NEGATED_STEP.sub(" ", sentence)
    return all(pattern.search(rest) for pattern in (STEP, SUBJECT, HANDOFF))


def text_problems(relpath, text):
    """Problems in one file's text: Zen, opencode outside a host-folder line,
    tools-installer, and delegation."""
    problems = []
    for number, line in enumerate(text.splitlines(), 1):
        if ZEN.search(line):
            problems.append(f"{relpath}:{number}: names Zen")
        if OPENCODE.search(line) and not any(allowed in line for allowed in OPENCODE_ALLOWED):
            problems.append(f"{relpath}:{number}: names opencode outside a host-folder line")
        if INSTALLER.search(line):
            problems.append(f"{relpath}:{number}: names tools-installer")
    for number, sentence in prose_units(Path(relpath).suffix, text):
        if delegation_problem(sentence):
            problems.append(
                f"{relpath}:{number}: hands an install or upgrade to another repository")
    return problems


def code_problems(relpath, source):
    """Problems in Python code: a string constant that runs a package, container or service tool."""
    problems = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if value in TOOL_ARGV or TOOL_TEXT.search(value):
                problems.append(
                    f"{relpath}:{node.lineno}: runs a package, container or service tool: "
                    f"{value[:40]}"
                )
    return problems


def table_problems(names):
    """Problems in backend table names: any name containing zen or opencode."""
    return [
        f"backend table names a removed backend: {name}"
        for name in names if re.search(r"zen|opencode", name, re.I)
    ]


def tree_problems(root):
    """Every guard problem in the skill tree under `root`."""
    problems = []
    for path in skill_files(root):
        relpath = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        problems.extend(text_problems(relpath, text))
        if path.suffix == ".py":
            problems.extend(code_problems(relpath, text))
    return problems


def _load_table_names():
    spec = importlib.util.spec_from_file_location(
        "jev_review_guard_under_test", str(SKILL_DIR / "scripts" / "jev_review.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [row["name"] for row in module.TABLE]


class TestJevGuard(unittest.TestCase):
    def test_skill_tree_passes_the_guard(self):
        self.assertTrue(skill_files(SKILL_DIR))
        self.assertEqual(tree_problems(SKILL_DIR), [])

    def test_backend_table_names_no_removed_backend(self):
        names = _load_table_names()
        self.assertEqual(names, ["laya", "typesafe"])
        self.assertEqual(table_problems(names), [])

    def test_guard_flags_each_violation(self):
        self.assertTrue(text_problems("x.md", "Fall back to OpenCode Zen when Laya is down."))
        self.assertTrue(text_problems("x.md", "Use the opencode backend for long items."))
        self.assertTrue(text_problems("x.md", "Ask tools-installer to set it up."))
        self.assertTrue(text_problems("x.md", "Run the Laya upgrade from the llm-env repo."))
        self.assertTrue(code_problems(
            "x.py", 'import subprocess\nsubprocess.run(["pip", "install", "laya"])\n'))
        self.assertTrue(table_problems(["opencode"]))

    def test_delegation_rule_reads_sentences(self):
        cases = [
            ("x.md", "Ask the infrastructure repository to upgrade Laya.\n"),
            ("x.md", "Before calibrating, run the Laya\nupgrade from the llm-env repo.\n"),
            ("x.md", "Do not skip this step: ask the ops repo to install the official skill.\n"),
            ("x.md", "Delegate the typesafe-ai install to another team.\n"),
            ("x.md", "Do not only install Laya from another repository.\n"),
            ("x.py", '"""Have the platform repo\nreinstall Laya before a run."""\n'),
        ]
        for relpath, text in cases:
            with self.subTest(text=text):
                problems = text_problems(relpath, text)
                self.assertTrue(
                    any("hands an install or upgrade to another repository" in p for p in problems),
                    problems)

    def test_allowed_lines_pass(self):
        for line in (
            "| 4 | `${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills` |",
            "This skill never installs, upgrades or restarts Laya.",
            "This skill never installs or upgrades Laya from another repository.",
            "Laya is never upgraded from another repository by this skill.",
            "`make start` in the llm-env repo with `system_one.enabled: true`",
            "`--check-updates` re-fetches the Laya record from the project repo README.",
        ):
            with self.subTest(line=line):
                self.assertEqual(text_problems("x.md", line + "\n"), [])
        self.assertEqual(text_problems("x.py", "fields.update(row)  # laya repo note\n"), [])

    def test_empty_tree_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "SKILL.md").write_text("", encoding="utf-8")
            (root / "scripts").mkdir()
            (root / "scripts" / "x.py").write_text("", encoding="utf-8")
            self.assertEqual(tree_problems(root), [])


if __name__ == "__main__":
    unittest.main()
