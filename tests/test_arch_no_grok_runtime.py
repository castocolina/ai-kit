"""Guard against restoring the removed runtime, with planted violations."""

import ast
import os
import pathlib
import re
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_ID = "gro" + "k"
WORD_RX = re.compile(rf"\b{_ID}\b", re.I)
AGENT_RX = re.compile(rf"\b{_ID.upper()}_AGENT\b")
ALLOW_RX = re.compile(
    rf"cursor-{_ID}-[\w.\-]*|opencode-go/{_ID}[\w.\-]*|x-?ai/{_ID}[\w.\-]*|"
    rf"{_ID}-\d[\w.\-]*|{_ID}-worker|{_ID}>=\d[\d.]*", re.I,
)
CLAIM_RX = re.compile(
    rf"\b{_ID}[\w.\-/]*[`*'\"]*\s+[`*]*(?:runtime|cli|binary|host)\b", re.I,
)
TABLE = "skills/ai-kit-spec-review/ai_kit_spec/detection.py"
PROFILES = "skills/ai-kit-spec-review/references/cli-profiles"
PATH_ALLOW = {
    PROFILES + "/cursor.md": re.compile(
        rf"Cursor and {_ID.capitalize()} both ship an .agent. binary"
    ),
    TABLE: re.compile(re.escape(
        'REMOVED_RUNTIMES: dict[str, tuple[str, ...]] = '
        f'{{"{_ID}": ("opencode", "pi", "cursor-agent")}}'
    )),
    "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/preference_match.py":
        re.compile(rf'_version_predicate\("{_ID}"'),
}
TEXT_ROOTS = ("skills", "tools", "cursor-agents")
TEXT_FILES = ("README.md",)
TEXT_SUFFIXES = frozenset({
    ".cjs", ".js", ".json", ".jsonc", ".jsonl", ".md", ".mjs", ".py", ".sh",
    ".toml", ".ts", ".txt", ".yaml", ".yml",
})
TEXT_NAMES = frozenset({"Makefile"})
SKIP_DIRS = {"__pycache__", "node_modules", ".git"}
ANCHORS = (TABLE, PROFILES + "/claude.md", "README.md", PROFILES + "/cursor.md")


def check_table_keys(source: str) -> tuple[list[str], list[str]]:
    keys: list[str] = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        else:
            continue
        is_table = any(isinstance(t, ast.Name) and t.id == "RUNTIMES" for t in targets)
        if is_table and isinstance(value, ast.Dict):
            keys.extend(k.value for k in value.keys if isinstance(k, ast.Constant)
                        and isinstance(k.value, str))
    return keys, [f"{TABLE}: runtime table key {key!r}" for key in keys if WORD_RX.search(key)]


def check_builders(relpath: str, tree: ast.AST) -> list[str]:
    return [
        f"{relpath}:{node.lineno}: {node.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and re.fullmatch(r"build_\w+_command", node.name)
        and _ID in node.name.lower().split("_")
    ]


def check_profiles(names: list[str]) -> list[str]:
    return [f"{PROFILES}/{name}: removed runtime profile" for name in names
            if WORD_RX.fullmatch(pathlib.Path(name).stem)]


def check_text(relpath: str, text: str) -> list[str]:
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        if relpath in PATH_ALLOW:
            line = PATH_ALLOW[relpath].sub("", line)
        remaining = ALLOW_RX.sub("", line)
        if CLAIM_RX.search(line) or WORD_RX.search(remaining) or AGENT_RX.search(remaining):
            hits.append(f"{relpath}:{n}: {line.strip()}")
    return hits


def _candidates(root: pathlib.Path) -> list[str]:
    candidates = []
    for folder in TEXT_ROOTS:
        for base, dirs, files in os.walk(root / folder):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(files):
                if os.path.splitext(name)[1] in TEXT_SUFFIXES or name in TEXT_NAMES:
                    candidates.append((pathlib.Path(base) / name).relative_to(root).as_posix())
    candidates.extend(name for name in TEXT_FILES if (root / name).is_file())
    return candidates


def _read(root: pathlib.Path, relpath: str) -> tuple[str | None, list[str]]:
    try:
        return (root / relpath).read_text(encoding="utf-8"), []
    except (OSError, UnicodeError):
        return None, [f"{relpath}: unreadable as UTF-8"]


def scan_tree(root: pathlib.Path) -> tuple[list[str], set[str]]:
    hits: list[str] = []
    scanned: set[str] = set()
    table_source = None
    for relpath in _candidates(root):
        text, errors = _read(root, relpath)
        scanned.add(relpath)
        hits.extend(errors)
        if text is None:
            continue
        hits.extend(check_text(relpath, text))
        if relpath == TABLE:
            table_source = text
        if relpath.startswith("skills/") and relpath.endswith(".py"):
            try:
                hits.extend(check_builders(relpath, ast.parse(text)))
            except SyntaxError:
                hits.append(f"{relpath}: does not parse")
    if table_source is None:
        hits.append(f"{TABLE}: missing or unreadable runtime table")
    else:
        try:
            keys, errors = check_table_keys(table_source)
            hits.extend(errors)
            if not keys or "pi" not in keys:
                hits.append(f"{TABLE}: missing runtime table keys or pi")
        except SyntaxError:
            pass  # The candidate parse above already records this failure.
    try:
        names = sorted(p.name for p in (root / PROFILES).iterdir() if p.is_file())
        scanned.add(PROFILES)
        hits.extend(check_profiles(names))
    except OSError:
        hits.append(f"{PROFILES}: missing or unreadable profile folder")
    return hits, scanned


def missing_anchors(scanned: set[str]) -> list[str]:
    return [anchor for anchor in ANCHORS if anchor not in scanned]


class TestNoGrokRuntime(unittest.TestCase):
    def test_tree_has_no_grok_runtime(self):
        hits, scanned = scan_tree(ROOT)
        self.assertEqual(hits, [], "\n".join(hits))
        self.assertEqual(missing_anchors(scanned), [])
        self.assertGreater(len(scanned), 50)


class TestNoGrokRuntimeNonVacuity(unittest.TestCase):
    def test_table_key_is_flagged(self):
        self.assertEqual(len(check_table_keys(f'RUNTIMES: dict = {{"pi": 1, "{_ID}": 2}}')[1]), 1)

    def test_builder_is_flagged(self):
        bad = ast.parse(f"def build_{_ID}_command():\n    return ''\n")
        good = ast.parse("def build_pi_command():\n    return ''\n")
        self.assertEqual(len(check_builders("skills/x.py", bad)), 1)
        self.assertEqual(len(check_builders("skills/x.py", good)), 0)

    def test_profile_is_flagged(self):
        self.assertEqual(len(check_profiles([f"{_ID}.md", "claude.md"])), 1)

    def test_text_line_is_flagged(self):
        flagged = (f"the {_ID} runtime\n", f"the {_ID.capitalize()} runtime",
                   f'"{_ID.upper()}_AGENT",')
        for text in flagged:
            self.assertEqual(len(check_text("skills/x.md", text)), 1)
        for text in (f"{_ID}king", f"{_ID.upper()}_AGENTS_HOME"):
            self.assertEqual(len(check_text("skills/x.md", text)), 0)

    def test_allowlisted_model_lines_pass(self):
        lines = (f"model: {_ID}-9.9-fakemodel", f"cursor-{_ID}-9.9-fake",
                 f"opencode-go/{_ID}-9.9-fake", f"xai/{_ID}-9.9-fake",
                 f"{_ID}-worker", f"{_ID}>=9.9")
        for line in lines:
            self.assertEqual(check_text("skills/x.md", line), [])
        alias = (f"Cursor and {_ID.capitalize()} both ship an `agent` binary, "
                 "so PATH order is ambiguous.")
        self.assertEqual(check_text(PROFILES + "/cursor.md", alias), [])
        self.assertEqual(len(check_text("skills/x.md", alias)), 1)

    def test_allowlisted_statement_with_a_claim_fails(self):
        alias = (f"Cursor and {_ID.capitalize()} both ship an `agent` binary, "
                 "so PATH order is ambiguous.")
        claim = alias + f" The {_ID.capitalize()} runtime is supported."
        self.assertEqual(len(check_text(PROFILES + "/cursor.md", claim)), 1)
        line = ('REMOVED_RUNTIMES: dict[str, tuple[str, ...]] = '
                f'{{"{_ID}": ("opencode", "pi", "cursor-agent")}}')
        self.assertEqual(check_text(TABLE, line), [])
        self.assertEqual(len(check_text(TABLE, line + f"  # the {_ID} runtime")), 1)

    def test_model_token_used_as_runtime_fails(self):
        bad = (f"the {_ID}-9.9-fakemodel runtime is supported", f"use the {_ID}-9.9-fakemodel cli",
               f"the `{_ID}-9.9-fakemodel` runtime", f"the **{_ID}** cli", f"use `{_ID}` `binary`")
        good = (f"the {_ID}-9.9-fakemodel model", f"the `{_ID}-9.9-fakemodel` model")
        for line in bad:
            self.assertEqual(len(check_text("skills/x.md", line)), 1)
        for line in good:
            self.assertEqual(check_text("skills/x.md", line), [])

    def test_unreadable_and_unparsable_files_fail(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as temp:
            root = pathlib.Path(temp)
            (root / "skills").mkdir()
            (root / "skills/bad.md").write_bytes(b"\xff\xfe\xfa")
            (root / "skills/bad.py").write_text("def (\n", encoding="utf-8")
            (root / "skills/blob.bin").write_bytes(b"\xff" + f"the {_ID} runtime".encode())
            hits, scanned = scan_tree(root)
            self.assertIn("skills/bad.md: unreadable as UTF-8", hits)
            self.assertIn("skills/bad.py: does not parse", hits)
            self.assertFalse(any("skills/blob.bin" in hit for hit in hits))
            self.assertNotIn("skills/blob.bin", scanned)

    def test_planted_tree_fails_four_times(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as temp:
            root = pathlib.Path(temp)
            files = {
                TABLE: f'RUNTIMES = {{"pi": 1, "{_ID}": 2}}\n',
                "skills/ai-kit-spec-review/ai_kit_spec/commands.py":
                    f"def build_{_ID}_command():\n    return ''\n",
                PROFILES + "/claude.md": "ok\n",
                PROFILES + f"/{_ID}.md": "ok\n",
                PROFILES + "/cursor.md": "ok\n",
                "README.md": f"the {_ID} runtime\n",
            }
            for name, text in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            hits, scanned = scan_tree(root)
            fragments = ("runtime table key", f"build_{_ID}_command", f"{_ID}.md",
                         f"{TABLE}:1:", "README.md:1:")
            for fragment in fragments:
                self.assertTrue(any(fragment in hit for hit in hits), fragment)
            self.assertTrue(any(hit.startswith("README.md:1:") for hit in hits))
            self.assertEqual(len(hits), 5)
            self.assertEqual(missing_anchors(scanned), [])

    def test_wrong_root_is_not_vacuous(self):
        hits, scanned = scan_tree(ROOT / "no-such-root")
        self.assertTrue(missing_anchors(scanned))
        self.assertTrue(hits)
