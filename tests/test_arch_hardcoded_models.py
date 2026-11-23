"""35 D-16..D-18 / HUB-09: position-based guard against hardcoded provider and model names, \
with a baseline that only shrinks; 36 R8 adds the referee rule (REFEREE_RX). Arch group."""

import collections
import json
import re
import subprocess
import tempfile
import unicodedata
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASELINE = REPO / "tests" / "fixtures" / "no_hardcoded_models_baseline.json"
SCAN_ROOTS = ("skills/", "tools/", "tests/", "docs/", "README.md", "AGENTS.md")
SUFFIXES = (
    ".py",
    ".mjs",
    ".cjs",
    ".js",
    ".sh",
    ".md",
    ".json",
    ".jsonc",
    ".toml",
    ".yaml",
    ".yml",
    ".txt",
)
DOC_SUFFIXES = (".md", ".txt")
SKIP_PARTS = (
    "tests/fixtures/archived/",
    "tests/fixtures/cli_help/",
    "graphify-out/",
    "/node_modules/",
)
SELF = "tests/test_arch_hardcoded_models.py"
CLEANED_BY = ("35", "36", "37", "38", "39", "backlog")
MARKER = "model-example:"
COMMENT_STARTS = ("#", "//", "/*", "*", "<!--")
NON_NAMES = frozenset(
    {"auto", "default", "false", "inherit", "none", "null", "session", "string", "true", "unknown"}
)
BRANCH_PREFIXES = frozenset({"feat", "fix", "hotfix", "gsd", "demo", "chore", "docs", "release"})
SYSTEM_DIRS = frozenset({"dev", "etc", "usr", "tmp", "var", "home", "bin"})
TOP_DIRS = frozenset(p.name for p in REPO.iterdir() if p.is_dir())

ALLOWED = re.compile(
    r"""^(router-env/[\w.:#-]+|placeholder-(model|alias)-\d+(-[a-z0-9]+)*|fake[/-][\w.:#\[\]=-]+)$"""
)
TEMPLATE = re.compile(r"""[{}<>$%*]|^\.\.\.|^\\|^\(|^\[|^$|\|""")
KEYVAL = re.compile(
    r"""(?i)(?:[\"']?\b(?:model|model_id|model_name|modelid|base_model|reviewer_model)[\"']?\s*[:=]\s*[\"']([^\"'\s]+)[\"'])"""
)
FLAGVAL = re.compile(r"""--model(?:[= ]+|[\"'],\s*[\"'])[\"']?([^\s\"'\x60)]+)""")
SLASH = re.compile(r"""[\"'\x60]([a-z][a-z0-9_-]{1,30}/[a-z0-9][a-z0-9._-]{3,60})[\"'\x60]""")
FILE_EXT = re.compile(r"""\.(py|md|json|jsonc|toml|yaml|yml|mjs|cjs|js|sh|txt|cfg|lock|tmpl)$""")
NAME_ASSIGN = re.compile(
    r"""^\s*([A-Z_]*(?:MODEL|ALIAS|SELECTOR)[A-Z_]*)\s*(?::[^=]+)?=\s*[\(\[{]"""
)
NAME_ASSIGN_KW = re.compile(r"""\b(native_selectors|models?|aliases)\s*=\s*[\(\[]""")
QSTR = re.compile(r"""[\"']([A-Za-z0-9][A-Za-z0-9._:/#-]*)[\"']""")
SELECTORS_ASSIGN = re.compile(r"""\bnative_selectors\s*=\s*[\(\[]""")
EXAMPLE_FIELD = re.compile(r"""^\s*[\"']?example[\"']?\s*(?::|=(?!=))""")
AA_SHAPE_RX = re.compile(r"[\"']?artificial_analysis_[a-z_]+_index[\"']?\s*[:=]\s*-?\d")
AA_MARKER = "synthetic: Artificial Analysis shapes, invented values"
# Historic plan text whose numbers' provenance is unknown; this dict only shrinks.
AA_SHAPE_KNOWN = {
    "docs/superpowers/plans/2026-09-02-ai-kit-model-discovery-config.md": "backlog",
    "docs/superpowers/plans/2026-09-05-model-catalog-effort-suffix-fallback.md": "backlog",
    "docs/superpowers/plans/2026-09-05-router-name-purpose-heuristic.md": "backlog",
}


# 36 R8: an unmarked lane alias (router-env/<x>) or referee name (referee-<x>) outside tests/ is the
# owner's config, never shipped text. tests/ is exempt wholesale: a line scan cannot tell a pi or
# opencode case apart. The model-example: marker exempts doc, comment, docstring and example lines.
REFEREE_RX = re.compile(
    r"router-env/[A-Za-z0-9](?:[\w.:#-]*\w)?"
    r"|(?<![\w-])referee-[a-z0-9](?:[\w-]*[a-z0-9])?"
)


def _modelish(value: str) -> bool:
    return bool(re.search(r"[A-Za-z]", value)) and bool(re.search(r"[-./0-9:]", value))


def _check_value(value: str, strict: bool = False) -> bool:
    if ALLOWED.match(value) or TEMPLATE.search(value) or len(value) < 3:
        return False
    if strict:
        return value.lower() not in NON_NAMES
    return _modelish(value)


def _keyval_hits(line: str) -> list[tuple[str, str]]:
    return [("keyval", v) for v in KEYVAL.findall(line) if _check_value(v, strict=True)]


def _flag_hits(line: str) -> list[tuple[str, str]]:
    return [
        ("flag", v)
        for v in FLAGVAL.findall(line)
        if not v.startswith("-") and _check_value(v, strict=True)
    ]


def _slash_hits(line: str) -> list[tuple[str, str]]:
    hits = []
    for value in SLASH.findall(line):
        first, rest = value.split("/", 1)
        if (
            ALLOWED.match(value)
            or FILE_EXT.search(value)
            or first == "router-env"
            or first in BRANCH_PREFIXES
            or first in TOP_DIRS
            or first in SYSTEM_DIRS
            or not re.search(r"[a-z]", rest)
            or not re.search(r"\d", rest)
        ):
            continue
        hits.append(("slash", value))
    return hits


def _seedrow_hits(line: str) -> list[tuple[str, str]]:
    hits = []
    if NAME_ASSIGN.match(line) or NAME_ASSIGN_KW.search(line):
        hits.extend(
            ("seedrow", v) for v in QSTR.findall(line) if not v.startswith("-") and _check_value(v)
        )
    if SELECTORS_ASSIGN.search(line):
        already = {v for _, v in hits}
        hits.extend(
            ("seedrow", v)
            for v in QSTR.findall(line)
            if len(v) >= 3 and not ALLOWED.match(v) and v not in already
        )
    return hits


def _referee_hits(path: str, line: str) -> list[tuple[str, str]]:
    if path.startswith("tests/"):
        return []
    return [("referee", value) for value in REFEREE_RX.findall(line)]


def _marker_exempt(path: str, line: str, in_docstring: bool) -> bool:
    return (
        path.endswith(DOC_SUFFIXES)
        or line.lstrip().startswith(COMMENT_STARTS)
        or in_docstring
        or bool(EXAMPLE_FIELD.search(line))
    )


def _balance(line: str) -> int:
    return sum(line.count(char) for char in "([{") - sum(line.count(char) for char in ")]}")


def _continuation_hits(line: str, kind: str) -> list[tuple[str, str]]:
    if kind == "selectors":
        values = [v for v in QSTR.findall(line) if len(v) >= 3 and not ALLOWED.match(v)]
    else:
        values = [v for v in QSTR.findall(line) if not v.startswith("-") and _check_value(v)]
    return [("seedrow", v) for v in values]


def scan_text(path: str, text: str) -> list[tuple[int, str, str]]:
    lines = unicodedata.normalize("NFKC", text).splitlines()
    result = []
    in_docstring = False
    seed_depth = 0
    seed_kind = "seed"
    for index, line in enumerate(lines):
        quotes = line.count('"""') + line.count("'''")
        if path.endswith(".py") and quotes % 2:
            in_docstring = not in_docstring
        line_in_docstring = path.endswith(".py") and (in_docstring or quotes > 0)
        hits = (
            _keyval_hits(line) + _flag_hits(line) + _slash_hits(line)
            + _seedrow_hits(line) + _referee_hits(path, line)
        )
        if seed_depth > 0:
            hits.extend(_continuation_hits(line, seed_kind))
            seed_depth += _balance(line)
            if seed_depth <= 0:
                seed_depth = 0
        else:
            seed_match = bool(NAME_ASSIGN.match(line) or NAME_ASSIGN_KW.search(line))
            selectors_match = bool(SELECTORS_ASSIGN.search(line))
            if (seed_match or selectors_match) and _balance(line) > 0:
                seed_kind = "selectors" if selectors_match else "seed"
                seed_depth = _balance(line)
        marker_near = MARKER in line or (index > 0 and MARKER in lines[index - 1])
        if marker_near and _marker_exempt(path, line, line_in_docstring):
            continue
        result.extend((index + 1, kind, value) for kind, value in hits)
    return result


def tracked_files(root: Path) -> list[str]:
    commands = (
        ["git", "ls-files", "-z"],
        ["git", "ls-files", "-z", "--others", "--exclude-standard"],
    )
    names = set()
    for command in commands:
        output = (
            subprocess.run(command, cwd=root, check=True, capture_output=True)
            .stdout.decode("utf-8")
            .split("\0")
        )
        names.update(name for name in output if name)
    return sorted(
        name
        for name in names
        if name != SELF
        and name.endswith(SUFFIXES)
        and any(name == item or name.startswith(item) for item in SCAN_ROOTS)
        and not any(part in name for part in SKIP_PARTS)
    )


def scan_tree(root: Path, files: list[str]) -> dict[str, list[tuple[int, str, str]]]:
    found = {}
    for name in files:
        try:
            text = (root / name).read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
        hits = scan_text(name, text)
        if hits:
            found[name] = hits
    return found


def load_baseline(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _hit_strings(hits: list[tuple[int, str, str]]) -> list[str]:
    return sorted(f"{kind} {value}" for _, kind, value in hits)


def baseline_problems(found: dict, baseline: dict, existing: set[str]) -> list[str]:
    problems = []
    entries = baseline.get("files", [])
    paths = [entry.get("path") for entry in entries]
    if baseline.get("schema") != 2:
        problems.append("baseline schema is not 2")
    if paths != sorted(paths):
        problems.append("baseline not sorted by path")
    by_path = {}
    for entry in entries:
        path = entry.get("path", "")
        if path in by_path:
            problems.append(f"duplicate path {path}")
        by_path[path] = entry
        if entry.get("cleaned_by") not in CLEANED_BY:
            problems.append(f"bad cleaned_by for {path}: {entry.get('cleaned_by')}")
        if entry.get("hits", []) != sorted(entry.get("hits", [])):
            problems.append(f"hits not sorted for {path}")
    for path, hits in found.items():
        if path not in by_path:
            problems.append(f"new violation: {path}:{hits[0][0]} {hits[0][1]} {hits[0][2]}")
            continue
        allowed = collections.Counter(by_path[path].get("hits", []))
        seen = collections.Counter()
        for line, kind, value in hits:
            rendered = f"{kind} {value}"
            seen[rendered] += 1
            if seen[rendered] > allowed[rendered]:
                problems.append(f"new violation: {path}:{line} {kind} {value}")
    for path, entry in by_path.items():
        if path not in existing:
            problems.append(f"gone, remove from baseline: {path}")
        elif not found.get(path):
            problems.append(f"fixed, remove from baseline: {path}")
        else:
            actual = collections.Counter(_hit_strings(found[path]))
            listed = collections.Counter(entry.get("hits", []))
            for hit, count in listed.items():
                for _ in range(max(0, count - actual[hit])):
                    problems.append(f"fixed, remove from baseline: {path} {hit}")
    return problems


def aa_text_problem(path: str, text: str) -> str | None:
    """Return the first unmarked Artificial Analysis response-shaped numeric line."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not AA_SHAPE_RX.search(line):
            continue
        if AA_MARKER in line:
            continue
        previous = index - 1
        while previous >= 0 and AA_SHAPE_RX.search(lines[previous]):
            previous -= 1
        if previous >= 0 and AA_MARKER in lines[previous]:
            continue
        return f"AA response shape without the synthetic marker: {path}:{index + 1}"
    return None


def aa_shape_problems(root: Path, files: list[str], known=AA_SHAPE_KNOWN) -> list[str]:
    problems = []
    for path in files:
        try:
            text = (root / path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        has_shape = any(AA_SHAPE_RX.search(line) for line in text.splitlines())
        if path in known:
            if not has_shape:
                problems.append(f"AA shape fixed, remove from AA_SHAPE_KNOWN: {path}")
            continue
        problem = aa_text_problem(path, text)
        if problem:
            problems.append(problem)
    return problems


def _git_binary_available() -> bool:
    return bool(__import__("shutil").which("git"))


def _inside_work_tree() -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0 and proc.stdout.strip() == "true"


GIT_WORK_TREE_AVAILABLE = _git_binary_available() and _inside_work_tree()
GIT_WORK_TREE_SKIP = "requires a git work tree; the clean-room container has no .git"


class TestAaShapes(unittest.TestCase):
    @unittest.skipUnless(GIT_WORK_TREE_AVAILABLE, GIT_WORK_TREE_SKIP)
    def test_tree_has_no_unmarked_aa_shape(self):
        self.assertEqual([], aa_shape_problems(REPO, tracked_files(REPO)))

    def test_aa_rule_non_vacuity(self):
        cases = (
            (
                "numeric shape",
                '{"artificial_analysis_intelligence_index": 68.4}',
                "AA response shape without the synthetic marker: x.json:1",
            ),
            (
                "line marker",
                AA_MARKER + '\n{"artificial_analysis_intelligence_index": 68.4}',
                None,
            ),
            (
                "marker covers matching run",
                AA_MARKER + '\n{"artificial_analysis_intelligence_index": 68.4}\n'
                '{"artificial_analysis_coding_index": 70.0}',
                None,
            ),
            (
                "marker is not file-wide",
                AA_MARKER + '\nx = 1\n{"artificial_analysis_intelligence_index": 68.4}',
                "AA response shape without the synthetic marker: x.py:3",
            ),
            (
                "key without number",
                'evaluations.get("artificial_analysis_intelligence_index")',
                None,
            ),
        )
        for name, text, expected in cases:
            path = "x.py" if name == "marker is not file-wide" else "x.json"
            with self.subTest(case=name):
                self.assertEqual(expected, aa_text_problem(path, text))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            known_path = next(iter(AA_SHAPE_KNOWN))
            target = root / known_path
            target.parent.mkdir(parents=True)
            target.write_text("no response shape\\n", encoding="utf-8")
            self.assertEqual(
                [f"AA shape fixed, remove from AA_SHAPE_KNOWN: {known_path}"],
                aa_shape_problems(root, [known_path]),
            )


class TestHardcodedModels(unittest.TestCase):
    @unittest.skipUnless(GIT_WORK_TREE_AVAILABLE, GIT_WORK_TREE_SKIP)
    def test_tree_matches_baseline(self):
        files = tracked_files(REPO)
        self.assertGreater(len(files), 0)
        found = scan_tree(REPO, files)
        self.assertEqual([], baseline_problems(found, load_baseline(BASELINE), set(files)))

    def test_baseline_is_sorted_and_unique(self):
        base = load_baseline(BASELINE)
        found = {
            item["path"]: [(1, hit.split(" ", 1)[0], hit.split(" ", 1)[1]) for hit in item["hits"]]
            for item in base["files"]
        }
        self.assertEqual(
            [], baseline_problems(found, base, {item["path"] for item in base["files"]})
        )


class TestHardcodedModelsNonVacuity(unittest.TestCase):
    def test_each_rule_catches_its_form(self):
        forms = {
            "membership": ('if model_id in ("qqvendor/qqmodel-7",):', "slash"),
            "default value": ('def pick(model="qqmodel-7"): pass', "keyval"),
            "flag": ("run --model qqmodel-7", "flag"),
            "seed row": ('native_selectors=("qqalias", "zz"),', "seedrow"),
            "bare key value": ('cfg = {"model": "qqmodel"}', "keyval"),
        }
        for name, (text, expected) in forms.items():
            with self.subTest(form=name):
                self.assertEqual([expected], [kind for _, kind, _ in scan_text("x.py", text)])

    def test_allowed_forms_pass(self):
        clean = [
            "# model-example: qqvendor/qqmodel-7",
            'model = "router-env/x"',
            'model = "placeholder-model-1-high"',
            'model = "fake/ok"',
            'model = "fake-ok-cursor[effort=high]"',
            '{"model_name": "placeholder-model-5 (thinking)"}',
            'cfg = {"model": "default"}',
            'x = "text/plain"',
        ]
        for text in clean:
            with self.subTest(text=text):
                self.assertEqual([], scan_text("tests/x.py", text))

    def test_marker_covers_two_lines_only(self):
        text = '# model-example: ok\nx = 1\nmodel = "qqmodel-7"'
        self.assertEqual([3], [line for line, _, _ in scan_text("x.py", text)])

    def test_marker_never_exempts_code(self):
        text = '# model-example: seed\nDEFAULT_MODELS = ("qqvendor/qqmodel-7",)'
        hits = scan_text("x.py", text)
        self.assertEqual([2, 2], [line for line, _, _ in hits])
        self.assertEqual(["seedrow", "slash"], sorted(kind for _, kind, _ in hits))
        inline = 'if m in ("qqvendor/qqmodel-7",):  # model-example: x'
        self.assertEqual(["slash"], [kind for _, kind, _ in scan_text("x.py", inline)])

    def test_example_field_is_not_a_comparison(self):
        comparison = 'if example == "qqvendor/qqmodel-7":  # model-example: x'
        field = 'example = "qqvendor/qqmodel-7"  # model-example: x'
        self.assertEqual(["slash"], [kind for _, kind, _ in scan_text("x.py", comparison)])
        self.assertEqual([], scan_text("x.py", field))

    def test_multiline_seed_rows(self):
        for text in (
            'DEFAULT_MODELS = (\n    "qqmodel-7",\n)',
            'native_selectors=(\n    "qqalias",\n),',
        ):
            with self.subTest(text=text):
                hits = scan_text("x.py", text)
                self.assertEqual([(2, "seedrow", hits[0][2])], hits)

    def test_marker_in_docstring_and_doc_exempt(self):
        docstring = "'''Run it like this.\nmodel-example: run --model qqmodel-7\n'''"
        self.assertEqual([], scan_text("x.py", docstring))
        self.assertEqual([], scan_text("x.md", "model-example: run --model qqmodel-7"))

    def test_nfkc_lookalike_caught(self):
        self.assertEqual(
            ["keyval"], [kind for _, kind, _ in scan_text("x.py", 'model = "ｑｑmodel-７"')]
        )

    @unittest.skipUnless(GIT_WORK_TREE_AVAILABLE, GIT_WORK_TREE_SKIP)
    def test_untracked_file_is_scanned(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "skills").mkdir()
            (root / "skills" / "a.py").write_text("pass\\n", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "add", "skills/a.py"], cwd=root, check=True)
            subprocess.run(
                ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "fixture"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            (root / "skills" / "b.py").write_text("pass\\n", encoding="utf-8")
            self.assertEqual(["skills/a.py", "skills/b.py"], tracked_files(root))

    def test_baseline_problems_each_fire(self):
        hit = (1, "slash", "qqvendor/qqmodel-7")
        entry = {"path": "skills/a.py", "cleaned_by": "35", "hits": ["slash qqvendor/qqmodel-7"]}
        baseline = {"schema": 2, "files": [entry]}
        cases = [
            ("new violation:", {"skills/b.py": [hit]}, baseline, {"skills/a.py", "skills/b.py"}),
            (
                "new violation:",
                {"skills/a.py": [hit, (2, "keyval", "qqmodel-8")]},
                baseline,
                {"skills/a.py"},
            ),
            ("fixed, remove from baseline:", {}, baseline, {"skills/a.py"}),
            ("fixed, remove from baseline:", {"skills/a.py": []}, baseline, {"skills/a.py"}),
            (
                "fixed, remove from baseline:",
                {"skills/a.py": [hit]},
                {
                    "schema": 2,
                    "files": [
                        dict(entry, hits=["keyval qqmodel-8", "slash qqvendor/qqmodel-7"])
                    ],
                },
                {"skills/a.py"},
            ),
            ("", {}, {"schema": 2, "files": []}, set()),
            (
                "baseline not sorted by path",
                {},
                {"schema": 2, "files": [dict(entry, path="z"), dict(entry, path="a")]},
                {"z", "a"},
            ),
            ("duplicate path", {}, {"schema": 2, "files": [entry, entry]}, {"skills/a.py"}),
            (
                "hits not sorted",
                {},
                {
                    "schema": 2,
                    "files": [
                        dict(entry, hits=["slash zzz/qqmodel-7", "slash qqvendor/qqmodel-7"])
                    ],
                },
                {"skills/a.py"},
            ),
            (
                "bad cleaned_by",
                {},
                {"schema": 2, "files": [dict(entry, cleaned_by="40")]},
                {"skills/a.py"},
            ),
            ("baseline schema is not 2", {}, {"schema": 1, "files": []}, set()),
            ("new violation:", {"skills/a.py": [hit, (2, *hit[1:])]}, baseline, {"skills/a.py"}),
        ]
        for prefix, found, base, existing in cases:
            with self.subTest(prefix=prefix, found=found, base=base):
                problems = baseline_problems(found, base, existing)
                if not prefix:
                    self.assertEqual([], problems)
                else:
                    self.assertTrue(
                        any(problem.startswith(prefix) for problem in problems), problems
                    )


class TestRefereeRuleNonVacuity(unittest.TestCase):
    def test_unmarked_alias_in_a_default_fails(self):
        self.assertEqual(
            [(1, "referee", "router-env/x")],
            scan_text("skills/a.py", 'DEFAULT_ALIAS = "router-env/x"'),
        )

    def test_alias_outside_tests_is_a_referee_hit(self):
        self.assertEqual(
            [(1, "referee", "router-env/x")], scan_text("skills/x.py", 'model = "router-env/x"')
        )

    def test_unmarked_alias_in_a_skill_fails(self):
        self.assertEqual(
            [(1, "referee", "router-env/x")],
            scan_text("skills/s/SKILL.md", "Use router-env/x here."),
        )

    def test_marker_covers_its_own_region_only(self):
        text = "<!-- model-example: router-env/x -->\nrouter-env/x\nrouter-env/y"
        self.assertEqual([(3, "referee", "router-env/y")], scan_text("skills/s/SKILL.md", text))

    def test_test_files_are_exempt(self):
        self.assertEqual([], scan_text("tests/test_x.py", 'model = "router-env/x"'))

    def test_new_violating_file_fails(self):
        self.assertEqual(
            ["new violation: skills/new.md:1 referee router-env/x"],
            baseline_problems(
                {"skills/new.md": [(1, "referee", "router-env/x")]},
                {"schema": 2, "files": []},
                {"skills/new.md"},
            ),
        )

    def test_cleaned_file_fails_until_its_entry_goes(self):
        baseline = {
            "schema": 2,
            "files": [
                {"path": "skills/c.md", "cleaned_by": "36", "hits": ["referee router-env/x"]}
            ],
        }
        self.assertEqual(
            ["fixed, remove from baseline: skills/c.md"],
            baseline_problems({}, baseline, {"skills/c.md"}),
        )

    def test_bare_referee_name_fails(self):
        self.assertEqual(
            [(1, "referee", "referee-one")], scan_text("skills/c.json", '{"lane": "referee-one"}')
        )

    def test_prefix_constant_and_alias_tail_forms(self):
        self.assertEqual([], scan_text("skills/a.py", 'ROUTER_PREFIX = "router-env/"'))
        self.assertEqual(
            [(1, "referee", "router-env/my-referee-one")],
            scan_text("skills/a.md", "router-env/my-referee-one."),
        )


if __name__ == "__main__":
    unittest.main()
