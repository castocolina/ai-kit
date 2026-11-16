"""Kept skills carry behaviour, not history (32 SPEC R9, D-18).

Each kept skill's SKILL.md main flow (everything above its trailing `## Evidence`
section) holds no ISO date, no "as of" phrase, no run log and no tool version outside a
conditional or constraint. The seven `ai-kit-project-rules-*` skills are exempt by name.
It also guards shipped skill Python: no string literal or comment in a tracked skills/**/*.py
names a phase file or a phase folder (the Markdown check's own patterns).
"""

import ast
import io
import re
import subprocess
import tempfile
import tokenize
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS = REPO_ROOT / "skills"
RULES_PREFIX = "ai-kit-project-rules-"
EXEMPT = frozenset(
    {
        "ai-kit-project-rules-agents",
        "ai-kit-project-rules-all",
        "ai-kit-project-rules-arch",
        "ai-kit-project-rules-cicd",
        "ai-kit-project-rules-docker",
        "ai-kit-project-rules-makefile",
        "ai-kit-project-rules-precommit",
    }
)
EXEMPT_REASON = "replaced in Phases 45-47 (owner decision, 2026-11-07)"
EVIDENCE_HEADING = "## Evidence"
DATE_RE = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)")
AS_OF_RE = re.compile(r"\bas of\b", re.IGNORECASE)
FENCE_RE = re.compile(r"^\s*(```|~~~)")
RUNLOG_RES = (
    re.compile(r"\bone real run\b", re.IGNORECASE),
    re.compile(r"\bconfirmed live\s*(?::|\d{4}-\d{2}-\d{2})", re.IGNORECASE),
    re.compile(r"\brecorded\s+\d{4}-\d{2}-\d{2}", re.IGNORECASE),
)
VERSION_TOOLS = (
    "cursor-agent",
    "gsd-core",
    "opencode",
    "copilot",
    "claude",
    "cursor",
    "codex",
    "grok",
    "pi",
    "node",
    "Node",
    "python",
    "jev",
    "Jev",
    "laya",
    "Laya",
    "uv",
)
VERSION_RE = re.compile(
    r"(?<![\w.-])(?:"
    + "|".join(re.escape(tool) for tool in sorted(VERSION_TOOLS, key=len, reverse=True))
    + r")\s+v?\d+(?:\.\d+)+"
)
CONSTRAINT_RE = re.compile(
    r"\bor later\b|\bor newer\b|\bat least\b|\bneeds\b|>=|\bolder\b|\bbefore\b|\bif\b|\bwhen\b",
    re.IGNORECASE,
)
CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
DOTTED_NUMBER_RE = re.compile(r"\d+(?:\.\d+)+")
LINK_TARGET_RE = re.compile(r"\]\([^)]*\)")
URL_RE = re.compile(r"https?://\S+")
PHASE_DIR_RE = re.compile(r"(?<![\w.-])\d{1,2}(?:\.\d+)?-[a-z][a-z0-9]*(?:-[a-z0-9]+)*/")
PHASE_FILE_RE = re.compile(
    r"(?<![\w.-])\d{1,2}(?:\.\d+)?(?:-\d{2})?-[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*\.md\b"
)
BACKLOG_RE = re.compile(r"(?<![\w.])999\.\d+(?!\d)")
DECISION_RE = re.compile(r"(?<![A-Za-z0-9-])D-\d+(?!\w)")
REFEREE_RE = re.compile(r"router-env/|\breferee-[a-z0-9]")
POINTER_RULES = (
    (PHASE_DIR_RE, "phase folder"),
    (PHASE_FILE_RE, "phase file"),
    (BACKLOG_RE, "backlog id"),
    (REFEREE_RE, "referee"),
)


def main_flow(lines):
    """The lines above the trailing `## Evidence` section, or all lines when there is none."""
    fenced = False
    headings = []
    for index, line in enumerate(lines):
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if not fenced and line.startswith("## "):
            headings.append(index)
    if headings and lines[headings[-1]].rstrip() == EVIDENCE_HEADING:
        return lines[: headings[-1]]
    return list(lines)


def history_hits(skill_dir, base):
    """History hits in one skill's main flow, as `path:line: kind match` strings."""
    rel = (skill_dir / "SKILL.md").relative_to(base).as_posix()
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    flow = main_flow(text.splitlines())
    hits = []
    for number, line in enumerate(flow, start=1):
        for match in DATE_RE.finditer(line):
            hits.append(f"{rel}:{number}: date {match.group(0)}")
        if AS_OF_RE.search(line):
            hits.append(f"{rel}:{number}: as of")
        for pattern in RUNLOG_RES:
            for match in pattern.finditer(line):
                hits.append(f"{rel}:{number}: run log {match.group(0)}")
    for path in shipped_markdown(skill_dir):
        path_rel = path.relative_to(base).as_posix()
        hits.extend(pointer_hits(path.read_text(encoding="utf-8"), path_rel))
    return hits + version_hits(flow, rel)


def shipped_markdown(skill_dir):
    """Every .md a skill ships: under its folder, outside evals/ and __pycache__."""
    found = []
    for path in sorted(skill_dir.rglob("*.md")):
        parts = path.relative_to(skill_dir).parts
        if parts[0] == "evals" or "__pycache__" in parts:
            continue
        found.append(path)
    return found


def _bold_example(line, match):
    """A decision id written as a bold format example, such as `**D-14: ...**`."""
    before = line[max(0, match.start() - 2) : match.start()]
    return before == "**" and line[match.end() : match.end() + 1] == ":"


def pointer_hits(text, rel):
    """Planning pointers (phase folders and files, backlog ids, decision ids, referee names).

    Code spans stay in the line, so a pointer in one still points; URLs are removed first.
    """
    hits = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = URL_RE.sub(" ", raw)
        for pattern, kind in POINTER_RULES:
            for match in pattern.finditer(line):
                hits.append(f"{rel}:{number}: {kind} {match.group(0)}")
        for match in DECISION_RE.finditer(line):
            if not _bold_example(line, match):
                hits.append(f"{rel}:{number}: decision id {match.group(0)}")
    return hits


def _file_name_matches(text):
    """(kind, name, offset) for each phase-folder or phase-file name in one string."""
    return [
        (kind, match.group(0), match.start())
        for pattern, kind in POINTER_RULES[:2]
        for match in pattern.finditer(text)
    ]


def python_pointer_hits(source, rel):
    """Phase-folder and phase-file names in one Python source's string literals (docstrings
    and f-string constant parts included, bytes skipped) and comments, as sorted
    "path:line: kind name" strings; a source that does not parse is itself a hit.
    """
    try:
        tree = ast.parse(source)
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (SyntaxError, tokenize.TokenError) as exc:
        return [f"{rel}:1: unparsable source {type(exc).__name__}"]
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            # shortcut: escaped newlines or line continuations shift the reported line.
            for kind, name, offset in _file_name_matches(node.value):
                line = node.lineno + node.value[:offset].count("\n")
                found.append((line, kind, name))
    for token in tokens:
        if token.type == tokenize.COMMENT:
            for kind, name, _offset in _file_name_matches(token.string):
                found.append((token.start[0], kind, name))
    return [f"{rel}:{line}: {kind} {name}" for line, kind, name in sorted(found)]


def tracked_skill_python(repo):
    """Every tracked .py under skills/, from git ls-files.

    Untracked scratch and __pycache__ are never listed.
    """
    proc = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z", "--", "skills"],
        capture_output=True,
        check=True,
    )
    names = proc.stdout.decode("utf-8").split("\0")
    return sorted(name for name in names if name.endswith(".py"))


def _in_work_tree():
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def _units(lines):
    """Prose units for the version rule: a run of prose lines, or one table row."""
    units = []
    run = []
    first = 0
    fenced = False

    def flush():
        if run:
            units.append((first, " ".join(run)))
            run.clear()

    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if FENCE_RE.match(raw):
            flush()
            fenced = not fenced
        elif fenced:
            continue
        elif line.startswith("|"):
            flush()
            units.append((number, line))
        elif not line:
            flush()
        else:
            if not run:
                first = number
            run.append(line)
    flush()
    return units


def _code_span(match):
    """A code span holding a version stays opaque; one holding only a name keeps its text."""
    inner = match.group(0)[1:-1]
    return " CODE " if DOTTED_NUMBER_RE.search(inner) else inner


def version_hits(lines, rel):
    """Tool versions in prose that carry no constraint word, code spans and URLs excluded."""
    hits = []
    for number, text in _units(lines):
        flat = CODE_SPAN_RE.sub(_code_span, text)
        flat = LINK_TARGET_RE.sub("]", flat)
        flat = URL_RE.sub(" ", flat)
        for sentence in re.split(r"(?<=[.!?])\s+", flat):
            match = VERSION_RE.search(sentence)
            if match and not CONSTRAINT_RE.search(sentence):
                hits.append(f"{rel}:{number}: version {match.group(0)}")
    return hits


def kept_skills(skills_root):
    """Every skill folder with a SKILL.md that is not exempt, in name order."""
    return [
        folder
        for folder in sorted(skills_root.iterdir())
        if (folder / "SKILL.md").is_file() and folder.name not in EXEMPT
    ]


class TestKeptSkillsCarryNoHistory(unittest.TestCase):
    def test_every_kept_skill_passes(self):
        hits = []
        for folder in kept_skills(SKILLS):
            hits.extend(history_hits(folder, REPO_ROOT))
        self.assertEqual([], hits)

    def test_rules_skills_are_exempt_by_name(self):
        folders = {
            folder.name
            for folder in SKILLS.iterdir()
            if folder.name.startswith(RULES_PREFIX) and (folder / "SKILL.md").is_file()
        }
        self.assertEqual(set(EXEMPT), folders)
        self.assertTrue(EXEMPT_REASON)


class TestHistoryRulesNonVacuity(unittest.TestCase):
    def _hits(self, body):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            skill = base / "demo-skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text(body, encoding="utf-8")
            return history_hits(skill, base)

    def test_iso_date_in_main_flow_fails(self):
        self.assertEqual(
            self._hits("Ran on 2026-08-29.\n"), ["demo-skill/SKILL.md:1: date 2026-08-29"]
        )

    def test_date_in_code_span_fails(self):
        self.assertEqual(
            self._hits("see `2026-08-29`\n"), ["demo-skill/SKILL.md:1: date 2026-08-29"]
        )

    def test_date_in_fenced_line_fails(self):
        self.assertEqual(
            self._hits("```\n2026-10-25T17:26:29Z\n```\n"),
            ["demo-skill/SKILL.md:2: date 2026-10-25"],
        )

    def test_date_under_evidence_heading_passes(self):
        self.assertEqual(
            self._hits("# Title\n\nBody.\n\n## Evidence\n\n- Ran on 2026-08-29.\n"), []
        )

    def test_empty_evidence_section_passes(self):
        self.assertEqual(self._hits("# Title\n\n## Evidence\n"), [])

    def test_file_without_evidence_heading_is_checked_in_full(self):
        self.assertEqual(
            self._hits("# Title\n\n2026-08-29\n"), ["demo-skill/SKILL.md:3: date 2026-08-29"]
        )

    def test_evidence_heading_that_is_not_last_is_checked_as_main_flow(self):
        body = "## Evidence\n\n- x\n\n## Notes\n\nRan 2026-08-29.\n"
        self.assertEqual(self._hits(body), ["demo-skill/SKILL.md:7: date 2026-08-29"])

    def test_evidence_heading_inside_a_fence_is_not_a_section(self):
        body = "```\n## Evidence\n```\n\nRan 2026-08-29.\n"
        self.assertEqual(self._hits(body), ["demo-skill/SKILL.md:5: date 2026-08-29"])

    def test_as_of_phrase_fails(self):
        self.assertEqual(self._hits("## Limits (as of now)\n"), ["demo-skill/SKILL.md:1: as of"])

    def test_non_ascii_line_is_read_as_utf8(self):
        self.assertEqual(
            self._hits("Café 2026-01-02\n"), ["demo-skill/SKILL.md:1: date 2026-01-02"]
        )

    def test_tool_version_outside_a_conditional_fails(self):
        self.assertEqual(
            self._hits("Uses gsd-core 1.17.0 today.\n"),
            ["demo-skill/SKILL.md:1: version gsd-core 1.17.0"],
        )

    def test_version_with_a_constraint_word_passes(self):
        self.assertEqual(self._hits("Needs gsd-core 1.20 or later.\n"), [])
        self.assertEqual(self._hits("Install gsd-core 1.20 when the hook is missing.\n"), [])

    def test_version_in_a_code_span_passes(self):
        self.assertEqual(self._hits("Pin `gsd-core 1.17.0` here.\n"), [])

    def test_prose_version_after_a_code_span_tool_name_fails(self):
        self.assertEqual(
            self._hits("Built on `@opengsd/gsd-core` 1.17.0 today.\n"),
            ["demo-skill/SKILL.md:1: version gsd-core 1.17.0"],
        )

    def test_version_in_a_link_target_or_url_passes(self):
        self.assertEqual(self._hits("[notes](https://example.com/jev-1-14)\n"), [])

    def test_version_in_link_text_fails(self):
        self.assertEqual(
            self._hits("[Jev 1.14 notes](https://example.com/x)\n"),
            ["demo-skill/SKILL.md:1: version Jev 1.14"],
        )

    def test_version_inside_a_fence_passes(self):
        self.assertEqual(self._hits("```\nnode 24.1.0\n```\n"), [])

    def test_laya_version_fails(self):
        self.assertEqual(
            self._hits("Laya 0.4.27 answers fast.\n"),
            ["demo-skill/SKILL.md:1: version Laya 0.4.27"],
        )

    def test_one_real_run_fails(self):
        self.assertEqual(
            self._hits("(one real run: the same item scored 0.74, then 0.67)\n"),
            ["demo-skill/SKILL.md:1: run log one real run"],
        )

    def test_confirmed_live_needs_a_colon_or_date(self):
        self.assertEqual(
            self._hits("Confirmed live: x\n"), ["demo-skill/SKILL.md:1: run log Confirmed live:"]
        )
        self.assertIn(
            "demo-skill/SKILL.md:1: run log Confirmed live 2026-08-29",
            self._hits("Confirmed live 2026-08-29: x\n"),
        )
        self.assertEqual(
            self._hits("covers every model family confirmed live in the CLI profiles\n"), []
        )

    def test_recorded_date_is_a_run_log(self):
        self.assertIn(
            "demo-skill/SKILL.md:1: run log recorded 2026-08-29",
            self._hits("recorded 2026-08-29 in the walk\n"),
        )

    def test_table_row_is_its_own_unit(self):
        row = "| cursor host | validated from a cursor-agent 2026.10.14-941492e session |\n"
        self.assertEqual(
            self._hits(row), ["demo-skill/SKILL.md:1: version cursor-agent 2026.10.14"]
        )

    def test_phase_folder_and_file_pointer_fails(self):
        body = "Evidence: `.planning/phases/18.1-one-runtime-model/18.1-RESEARCH.md:231`.\n"
        self.assertEqual(
            self._hits(body),
            [
                "demo-skill/SKILL.md:1: phase folder 18.1-one-runtime-model/",
                "demo-skill/SKILL.md:1: phase file 18.1-RESEARCH.md",
            ],
        )

    def test_phase_file_name_fails(self):
        self.assertEqual(
            self._hits("Smoke result: see 21-SMOKE-CURSOR.md.\n"),
            ["demo-skill/SKILL.md:1: phase file 21-SMOKE-CURSOR.md"],
        )

    def test_plan_and_summary_file_names_fail(self):
        self.assertEqual(
            self._hits("Done in 04-01-PLAN.md and 15.1-02-SUMMARY.md.\n"),
            [
                "demo-skill/SKILL.md:1: phase file 04-01-PLAN.md",
                "demo-skill/SKILL.md:1: phase file 15.1-02-SUMMARY.md",
            ],
        )

    def test_backlog_id_fails(self):
        self.assertEqual(
            self._hits("Filed under Backlog 999.2.\n"),
            ["demo-skill/SKILL.md:1: backlog id 999.2"],
        )

    def test_referee_name_fails(self):
        hits = self._hits("Judged by router-env/my-referee-two.\n")
        self.assertEqual(len(hits), 2)
        self.assertTrue(all(hit.startswith("demo-skill/SKILL.md:1: referee ") for hit in hits))

    def test_decision_ids_fail(self):
        self.assertEqual(
            self._hits("Kept by (D-07), 20 D-11 and D-14.\n"),
            [
                "demo-skill/SKILL.md:1: decision id D-07",
                "demo-skill/SKILL.md:1: decision id D-11",
                "demo-skill/SKILL.md:1: decision id D-14",
            ],
        )

    def test_generic_pointers_pass(self):
        body = "\n".join(
            [
                "Read `.planning/config.json` and `.planning/scripts/cross-ai.mjs`.",
                "Phase files live in `.planning/phases/<phase>/`.",
                "Find `.planning/phases/**/*-CONTEXT.md` and write `NN-SPEC.md`.",
                "Cite `D-<n>` or `NN D-xx`.",
                "- **D-14: The spike captures the payload** (SPEC R5)",
                "Ids `JDG-04` and `ID-07` are not decisions.",
                "See https://example.com/999.2/21-SMOKE-CURSOR.md for the page.",
            ]
        )
        self.assertEqual(self._hits(body + "\n"), [])

    def _tree_hits(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            skill = base / "demo-skill"
            for rel, body in {"SKILL.md": "# Demo\n", **files}.items():
                (skill / rel).parent.mkdir(parents=True, exist_ok=True)
                (skill / rel).write_text(body, encoding="utf-8")
            return history_hits(skill, base)

    def test_pointer_in_a_reference_file_fails(self):
        self.assertEqual(
            self._tree_hits({"references/notes.md": "Kept by (D-07).\n"}),
            ["demo-skill/references/notes.md:1: decision id D-07"],
        )

    def test_pointer_in_a_root_readme_fails(self):
        self.assertEqual(
            self._tree_hits({"README.md": "See 21-SMOKE-CURSOR.md.\n"}),
            ["demo-skill/README.md:1: phase file 21-SMOKE-CURSOR.md"],
        )

    def test_evals_markdown_is_never_read(self):
        files = {
            "evals/cases.md": "Backlog 999.2 and (D-07).\n",
            "evals/files/deep/x.md": "router-env/my-referee-two\n",
        }
        self.assertEqual(self._tree_hits(files), [])


class TestShippedPythonNamesNoPlanningFile(unittest.TestCase):
    def setUp(self):
        if not _in_work_tree():
            self.skipTest("not inside a git work tree")

    def test_tracked_skill_python_names_no_planning_file(self):
        hits = []
        for name in tracked_skill_python(REPO_ROOT):
            if not (REPO_ROOT / name).is_file():
                continue
            text = (REPO_ROOT / name).read_text(encoding="utf-8")
            hits.extend(python_pointer_hits(text, name))
        self.assertEqual([], hits)


class TestPythonGuardNonVacuity(unittest.TestCase):
    def test_docstring_hit_fails(self):
        self.assertEqual(
            python_pointer_hits('"""Detection (07-CONTEXT.md D-06)."""\n', "demo.py"),
            ["demo.py:1: phase file 07-CONTEXT.md"],
        )

    def test_label_hit_fails(self):
        source = 'LABEL = (\n    "live-verified (names only; 21-SMOKE-CURSOR.md)."\n)\n'
        self.assertEqual(
            python_pointer_hits(source, "demo.py"),
            ["demo.py:2: phase file 21-SMOKE-CURSOR.md"],
        )

    def test_comment_hit_fails(self):
        self.assertEqual(
            python_pointer_hits("# evidence: 16.1-RESEARCH.md\nX = 1\n", "demo.py"),
            ["demo.py:1: phase file 16.1-RESEARCH.md"],
        )

    def test_phase_folder_hit_fails(self):
        source = 'PATH = ".planning/phases/18.1-one-runtime-model/notes"\n'
        self.assertEqual(
            python_pointer_hits(source, "demo.py"),
            ["demo.py:1: phase folder 18.1-one-runtime-model/"],
        )

    def test_f_string_constant_part_fails(self):
        source = 'name = "x"\nMSG = f"see 20-SMOKE-CODEX.md for {name}"\n'
        self.assertEqual(
            python_pointer_hits(source, "demo.py"),
            ["demo.py:2: phase file 20-SMOKE-CODEX.md"],
        )

    def test_bytes_literal_is_skipped(self):
        self.assertEqual(python_pointer_hits('DATA = b"21-SMOKE-CURSOR.md"\n', "demo.py"), [])

    def test_unparsable_source_is_a_hit(self):
        self.assertEqual(
            python_pointer_hits("def broken(:\n", "demo.py"),
            ["demo.py:1: unparsable source SyntaxError"],
        )

    def test_generic_pointers_pass(self):
        source = (
            '"""Read `.planning/config.json`, `.planning/phases/<phase>/` and write `NN-SPEC.md`'
            ' (16 D-11)."""\n# see .planning/ROADMAP.md\n'
        )
        self.assertEqual(python_pointer_hits(source, "demo.py"), [])

    def test_hits_sort_by_line(self):
        self.assertEqual(
            python_pointer_hits('# 20-SMOKE-CODEX.md\n"""21-SMOKE-CURSOR.md"""\n', "demo.py"),
            ["demo.py:1: phase file 20-SMOKE-CODEX.md", "demo.py:2: phase file 21-SMOKE-CURSOR.md"],
        )

    def test_empty_source_has_no_hit(self):
        self.assertEqual(python_pointer_hits("", "demo.py"), [])


if __name__ == "__main__":
    unittest.main()
