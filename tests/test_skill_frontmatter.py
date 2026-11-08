"""Strict frontmatter for every installable entry (32 SPEC R8, D-17).

The gate parses the frontmatter of each skill and agent the installer lists with a strict
subset of YAML, rejecting every shape a host's YAML parser could reject, then checks the
name and description fields. tests/test_skill_frontmatter_pyyaml.py cross-checks it with
PyYAML on the same fixtures.
"""
import importlib.util
import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_setup():
    path = REPO_ROOT / "tools" / "setup.py"
    spec = importlib.util.spec_from_file_location("ai_kit_setup_for_frontmatter", str(path))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_setup = _load_setup()

INDICATORS = frozenset("-?:,[]{}#&*!|>'\"%@`")
NON_STRING_RE = re.compile(
    r"^(?:[-+]?\d[\d_]*(?:\.\d*)?(?:[eE][-+]?\d+)?|0x[0-9a-fA-F]+|0o[0-7]+|~|null|Null|NULL"
    r"|true|True|TRUE|false|False|FALSE|yes|Yes|YES|no|No|NO|on|On|ON|off|Off|OFF)$"
)
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
KEY_LINE_RE = re.compile(r"^([A-Za-z0-9_-]+):(?: (.*))?$")
MAX_DESCRIPTION = 1024
MAX_NAME = 64


class FrontmatterError(ValueError):
    """A frontmatter shape outside the strict subset; the message names the problem."""


def _fold(lines):
    """Fold a `>` block: one space between consecutive text lines, one newline per blank line."""
    out, started, blanks = [], False, 0
    for line in lines:
        if not line:
            blanks += 1
            continue
        if started:
            out.append("\n" * blanks if blanks else " ")
        else:
            out.append("\n" * blanks)
        out.append(line)
        started, blanks = True, 0
    return "".join(out)


def _block_scalar(key, header, inner, start):
    """Read a `>` or `|` block from inner[start:]; return (value, index after the block)."""
    if not re.fullmatch(r"[>|][-+]?", header):
        raise FrontmatterError(f"{key}: unsupported block scalar header")
    end = start
    while end < len(inner) and (not inner[end].strip() or inner[end].startswith(" ")):
        end += 1
    taken = inner[start:end]
    indents = [len(line) - len(line.lstrip(" ")) for line in taken if line.strip()]
    if not indents:
        return "", end
    indent = indents[0]
    lines = []
    for line in taken:
        if not line.strip():
            lines.append("")
            continue
        spaces = len(line) - len(line.lstrip(" "))
        if spaces < indent:
            raise FrontmatterError(f"{key}: under-indented line in a block scalar")
        if header[0] == ">" and spaces > indent:
            raise FrontmatterError(f"{key}: more-indented line in a folded block")
        lines.append(line[indent:])
    trailing = 0
    while lines and lines[-1] == "":
        lines.pop()
        trailing += 1
    body = _fold(lines) if header[0] == ">" else "\n".join(lines)
    chomp = header[1:]
    if chomp == "-":
        suffix = ""
    elif chomp == "+":
        suffix = "\n" * (1 + trailing)
    else:
        suffix = "\n"
    return body + suffix, end


def _quoted_scalar(key, value):
    if value[0] == '"':
        if len(value) < 2 or not value.endswith('"'):
            raise FrontmatterError(f"{key}: unterminated double-quoted scalar")
        try:
            return json.loads(value)
        except ValueError:
            raise FrontmatterError(f"{key}: bad double-quoted scalar") from None
    if len(value) < 2 or not value.endswith("'"):
        raise FrontmatterError(f"{key}: unterminated single-quoted scalar")
    inner = value[1:-1]
    if "'" in inner.replace("''", ""):
        raise FrontmatterError(f"{key}: bad single-quoted scalar")
    return inner.replace("''", "'")


def _flow_scalar(key, value):
    """A single-line value: quoted, or plain with the strict subset's rules."""
    if value == "":
        raise FrontmatterError(f"{key}: empty value")
    if value[0] in '"\'':
        return _quoted_scalar(key, value)
    if value[0] in INDICATORS:
        raise FrontmatterError(f"{key}: plain scalar starts with an indicator")
    if ": " in value or " #" in value or value.endswith(":"):
        raise FrontmatterError(f"{key}: plain scalar holds ': ', ' #' or a trailing ':'")
    if NON_STRING_RE.match(value):
        return None
    return value


def parse_strict(text):
    """Return the frontmatter as {key: str | None}; None marks a value YAML reads as non-string.

    Raise FrontmatterError on any shape the strict subset does not accept.
    """
    if not text.startswith("---\n"):
        raise FrontmatterError("no frontmatter")
    lines = text.split("\n")
    end = next((i for i in range(1, len(lines)) if lines[i] == "---"), None)
    if end is None:
        raise FrontmatterError("unterminated frontmatter")
    inner = lines[1:end]
    if not any(line.strip() for line in inner):
        raise FrontmatterError("empty frontmatter")
    if any("\t" in line for line in inner):
        raise FrontmatterError("tab in frontmatter")
    data = {}
    i = 0
    while i < len(inner):
        line = inner[i]
        if not line.strip():
            i += 1
            continue
        lineno = i + 2
        if line.startswith(" "):
            raise FrontmatterError(f"line {lineno}: indented line outside a block scalar")
        match = KEY_LINE_RE.match(line)
        if match is None:
            raise FrontmatterError(f"line {lineno}: not a key: value line")
        key, value = match.group(1), (match.group(2) or "").rstrip()
        if key in data:
            raise FrontmatterError(f"duplicate key {key}")
        i += 1
        if value[:1] in (">", "|"):
            data[key], i = _block_scalar(key, value, inner, i)
        else:
            data[key] = _flow_scalar(key, value)
    return data


def field_problems(data, folder):
    """Problems with name and description. folder None checks presence and type only (agents)."""
    problems = []
    if "name" not in data:
        problems.append("no name")
    elif not isinstance(data["name"], str):
        problems.append("name is not a string")
    elif not data["name"].strip():
        problems.append("empty name")
    elif folder is not None:
        name = data["name"]
        if not NAME_RE.match(name) or len(name) > MAX_NAME:
            problems.append(f"name {name} is not 1-64 lowercase letters, digits and single hyphens")
        if name != folder:
            problems.append(f"name {name} differs from its folder {folder}")
    if "description" not in data:
        problems.append("no description")
    elif not isinstance(data["description"], str):
        problems.append("description is not a string")
    elif not data["description"].strip():
        problems.append("empty description")
    elif len(data["description"]) > MAX_DESCRIPTION:
        problems.append(
            f"description has {len(data['description'])} characters (max {MAX_DESCRIPTION})"
        )
    return problems


def skill_problems(text, folder):
    try:
        data = parse_strict(text)
    except FrontmatterError as exc:
        return [str(exc)]
    return field_problems(data, folder)


def entry_files(install_dir):
    """(category, name, markdown path) for every entry the installer lists, skills first."""
    entries = _setup.enumerate_entries(str(install_dir))
    found = []
    for cat in ("skills", "agents", "commands"):
        for name, path in entries.get(cat, []):
            md = Path(path) / "SKILL.md" if cat == "skills" else Path(path)
            found.append((cat, name, md))
    return found


def entry_problems(install_dir):
    base = Path(install_dir)
    problems = []
    for cat, name, md in entry_files(base):
        rel = md.relative_to(base).as_posix()
        text = md.read_text(encoding="utf-8")
        found = skill_problems(text, name if cat == "skills" else None)
        problems.extend(f"{rel}: {problem}" for problem in found)
    return problems


def _doc(front):
    """A whole SKILL.md-style document: the frontmatter block and an empty body."""
    return f"---\n{front}---\n"


DEMO = "demo-skill"
# (label, document text, folder, accepted by the gate). The two DESIGNED_STRICTER rows are
# valid YAML that the gate rejects on purpose (see the module docstring of the PyYAML check).
FIXTURES = (
    ("valid plain", _doc(f"name: {DEMO}\ndescription: Use when testing.\n"), DEMO, True),
    ("colon on first line", _doc(f"name: {DEMO}\ndescription: Use when: testing.\n"), DEMO, False),
    (
        "colon on continuation line",
        _doc(f"name: {DEMO}\ndescription: Use when\n  testing: yes\n"),
        DEMO,
        False,
    ),
    ("tab-indented line", _doc(f"name: {DEMO}\ndescription: Use when\n\ttesting.\n"), DEMO, False),
    (
        "unterminated quote",
        _doc(f'name: {DEMO}\ndescription: "Use when testing.\n'),
        DEMO,
        False,
    ),
    ("duplicate key", _doc(f"name: {DEMO}\nname: {DEMO}\ndescription: d\n"), DEMO, False),
    ("non-string name", _doc("name: 123\ndescription: d\n"), DEMO, False),
    (
        "1025-character description",
        _doc(f"name: {DEMO}\ndescription: {'a' * 1025}\n"),
        DEMO,
        False,
    ),
    ("uppercase name", _doc("name: Demo-Skill\ndescription: d\n"), "Demo-Skill", False),
    ("name differs from folder", _doc("name: other-name\ndescription: d\n"), DEMO, False),
    ("65-character name", _doc(f"name: {'a' * 65}\ndescription: d\n"), "a" * 65, False),
    ("double hyphen", _doc("name: demo--skill\ndescription: d\n"), "demo--skill", False),
    ("leading hyphen", _doc('name: "-demo"\ndescription: d\n'), "-demo", False),
    ("trailing hyphen", _doc("name: demo-\ndescription: d\n"), "demo-", False),
    ("empty description", _doc(f'name: {DEMO}\ndescription: ""\n'), DEMO, False),
    ("empty frontmatter", "---\n---\n", DEMO, False),
    ("no frontmatter", "# Title\n", DEMO, False),
    (
        "plain continuation without colon",
        _doc(f"name: {DEMO}\ndescription: Use when\n  testing.\n"),
        DEMO,
        False,
    ),
    ("inline comment", _doc(f"name: {DEMO}\ndescription: Use when testing #note\n"), DEMO, False),
    (
        "1024-character description",
        _doc(f"name: {DEMO}\ndescription: {'a' * 1024}\n"),
        DEMO,
        True,
    ),
    ("64-character name", _doc(f"name: {'a' * 64}\ndescription: d\n"), "a" * 64, True),
    (
        "folded description",
        _doc(f"name: {DEMO}\ndescription: >\n  Use when\n  testing.\n"),
        DEMO,
        True,
    ),
    (
        "literal description",
        _doc(f"name: {DEMO}\ndescription: |\n  Use when\n  testing.\n"),
        DEMO,
        True,
    ),
    (
        "double-quoted description",
        _doc(f'name: {DEMO}\ndescription: "Use when: testing."\n'),
        DEMO,
        True,
    ),
    (
        "single-quoted description with a doubled quote",
        _doc(f"name: {DEMO}\ndescription: 'It''s testing.'\n"),
        DEMO,
        True,
    ),
    (
        "non-ASCII description of 1024 characters",
        _doc(f"name: {DEMO}\ndescription: {'a' * 1023}é\n"),
        DEMO,
        True,
    ),
    (
        "description before name",
        _doc(f"description: Use when testing.\nname: {DEMO}\n"),
        DEMO,
        True,
    ),
)
DESIGNED_STRICTER = frozenset({"plain continuation without colon", "inline comment"})


class TestTreeFrontmatter(unittest.TestCase):
    """Every installable entry in this checkout parses strictly and names itself."""

    def test_every_entry_parses_strictly(self):
        self.assertEqual([], entry_problems(REPO_ROOT))

    def test_the_tree_entries_are_covered(self):
        files = entry_files(REPO_ROOT)
        skills = [item for item in files if item[0] == "skills"]
        self.assertGreater(len(skills), 10)
        self.assertTrue(
            any(cat == "agents" and path.name == "ai-kit-judge.md" for cat, _, path in files)
        )


class TestStrictFixtures(unittest.TestCase):
    """Small documents in temp dirs: the parser's values and the report order."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _write_skill(self, folder, text):
        skill_dir = os.path.join(self.tmp, "skills", folder)
        os.makedirs(skill_dir, exist_ok=True)
        with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_block_scalars_fold_and_chomp(self):
        head = "---\nname: demo\ndescription: "
        self.assertEqual(
            parse_strict(head + ">\n  Use when\n  testing.\n---\n")["description"],
            "Use when testing.\n",
        )
        self.assertEqual(
            parse_strict(head + ">-\n  Use when\n  testing.\n---\n")["description"],
            "Use when testing.",
        )
        self.assertEqual(
            parse_strict(head + "|\n  Use when\n  testing.\n---\n")["description"],
            "Use when\ntesting.\n",
        )

    def test_a_non_string_value_maps_to_none(self):
        text = "---\nname: 123\ndescription: d\n---\n"
        self.assertIsNone(parse_strict(text)["name"])
        self.assertEqual(skill_problems(text, "demo"), ["name is not a string"])

    def test_every_failing_entry_is_reported_in_order(self):
        self._write_skill(
            "bad-one", "---\nname: bad-one\nname: bad-one\ndescription: d\n---\n# body\n"
        )
        self._write_skill("bad-two", "---\nname: other\ndescription: d\n---\n# body\n")
        self.assertEqual(
            entry_problems(Path(self.tmp)),
            [
                "skills/bad-one/SKILL.md: duplicate key name",
                "skills/bad-two/SKILL.md: name other differs from its folder bad-two",
            ],
        )

    def test_each_fixture_result(self):
        for label, text, folder, accepted in FIXTURES:
            with self.subTest(label=label):
                self.assertEqual(bool(skill_problems(text, folder)), not accepted)

    def test_designed_stricter_labels_name_rejected_fixtures(self):
        # a misspelled label would silently drop a row from the PyYAML cross-check
        self.assertLessEqual(DESIGNED_STRICTER, {row[0] for row in FIXTURES if not row[3]})
