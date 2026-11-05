"""Generic shape check for every skills/*/evals/evals.json (plan 29-08, D-16, JDG-04).

Structure only: no model is called and no skill runs. A skill that ships evals gets this check
for free. The non-vacuity cases prove the check fails on a duplicate id and on a missing edge
case, so a green run means the rules were applied.
"""

import copy
import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"
MACHINE_PATH_RE = re.compile(r"/var/home|/home/[A-Za-z]|/Users/|~/")
ID_RE = re.compile(r"^(casual|precise|edge)-[a-z0-9-]+$")
PREFIXES = ("casual", "precise", "edge")
EVAL_KEYS = {"id", "prompt", "expected_output", "files", "assertions"}


def skill_dirs():
    """Every skill folder that ships an evals/evals.json, sorted."""
    return sorted(path.parent.parent for path in SKILLS.glob("*/evals/evals.json"))


def evals_problems(data, skill_dir):
    """Every rule the evals.json breaks, as readable strings (empty means clean)."""
    problems = []
    if data.get("skill_name") != skill_dir.name:
        problems.append(f"skill_name {data.get('skill_name')!r} is not {skill_dir.name!r}")
    evals = data.get("evals")
    if not isinstance(evals, list) or len(evals) < 5:
        return [*problems, "fewer than 5 evals"]
    ids = [item.get("id") for item in evals if isinstance(item, dict)]
    for duplicate in sorted({str(i) for i in ids if ids.count(i) > 1}):
        problems.append(f"duplicate id {duplicate}")
    for prefix in PREFIXES:
        if not any(isinstance(i, str) and i.startswith(prefix + "-") for i in ids):
            problems.append(f"missing {prefix} case")
    for item in evals:
        if not isinstance(item, dict):
            problems.append("eval is not an object")
            continue
        name = item.get("id")
        if set(item) != EVAL_KEYS:
            problems.append(f"eval {name}: keys are {sorted(item)}, want {sorted(EVAL_KEYS)}")
        if not (isinstance(name, str) and ID_RE.match(name)):
            problems.append(f"eval {name}: id must match {ID_RE.pattern}")
        for field in ("prompt", "expected_output"):
            if not (isinstance(item.get(field), str) and item[field].strip()):
                problems.append(f"eval {name}: {field} is empty")
        assertions = item.get("assertions")
        if not (isinstance(assertions, list) and len(assertions) >= 2 and all(
                isinstance(a, str) and len(a) >= 20 for a in assertions)):
            problems.append(f"eval {name}: needs 2+ assertions of 20+ characters")
        files = item.get("files")
        if not isinstance(files, list):
            problems.append(f"eval {name}: files is not a list")
            continue
        for path in files:
            if not (isinstance(path, str) and path.startswith("evals/files/")):
                problems.append(f"eval {name}: file {path!r} is not under evals/files/")
            elif not (skill_dir / path).is_file():
                problems.append(f"eval {name}: file {path} does not exist")
    if MACHINE_PATH_RE.search(json.dumps(data, ensure_ascii=False)):
        problems.append("machine path in evals.json")
    return problems


def listed_files(data):
    """Every evals/files/ path any eval names."""
    return {path for item in data.get("evals", []) if isinstance(item, dict)
            for path in item.get("files", []) if isinstance(path, str)}


def files_problems(skill_dir, listed):
    """Every file under evals/files/ must be named by an eval and carry no machine path."""
    problems = []
    root = skill_dir / "evals" / "files"
    if not root.is_dir():
        return problems
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(skill_dir).as_posix()
        if rel not in listed:
            problems.append(f"file {rel} is not listed by any eval")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            problems.append(f"file {rel} is not UTF-8 text")
            continue
        if MACHINE_PATH_RE.search(text):
            problems.append(f"machine path in {rel}")
    return problems


def trigger_problems(queries):
    """The trigger-query rules: 16 to 24 entries, 8 to 12 true and 8 to 12 false, unique,
    each at least 30 characters."""
    if not isinstance(queries, list):
        return ["trigger queries are not a list"]
    problems = []
    if not 16 <= len(queries) <= 24:
        problems.append(f"{len(queries)} trigger queries, want 16 to 24")
    texts = [q.get("query") for q in queries if isinstance(q, dict)]
    positives = sum(1 for q in queries if isinstance(q, dict) and q.get("should_trigger") is True)
    negatives = sum(1 for q in queries if isinstance(q, dict) and q.get("should_trigger") is False)
    if not 8 <= positives <= 12:
        problems.append(f"{positives} should_trigger true, want 8 to 12")
    if not 8 <= negatives <= 12:
        problems.append(f"{negatives} should_trigger false, want 8 to 12")
    if len(set(texts)) != len(texts):
        problems.append("duplicate trigger query")
    for text in texts:
        if not (isinstance(text, str) and len(text) >= 30):
            problems.append(f"trigger query shorter than 30 characters: {text!r}")
    return problems


def machine_path_problems(skill_dir):
    """The trigger-queries file carries no machine path."""
    text = (skill_dir / "evals" / "trigger-queries.json").read_text(encoding="utf-8")
    return ["machine path in trigger-queries.json"] if MACHINE_PATH_RE.search(text) else []


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class TestEvalsShape(unittest.TestCase):
    """Every skill with an evals/evals.json passes each rule (one subTest per skill and rule)."""

    def test_some_skill_ships_evals(self):
        self.assertTrue(skill_dirs())

    def test_every_skill_passes_every_rule(self):
        for skill in skill_dirs():
            evals_path = skill / "evals" / "evals.json"
            queries_path = skill / "evals" / "trigger-queries.json"
            data = _load(evals_path)
            with self.subTest(skill=skill.name, rule="evals.json"):
                self.assertEqual(evals_problems(data, skill), [])
            with self.subTest(skill=skill.name, rule="trigger-queries.json exists"):
                self.assertTrue(queries_path.is_file())
            with self.subTest(skill=skill.name, rule="trigger-queries.json"):
                self.assertEqual(trigger_problems(_load(queries_path)), [])
            with self.subTest(skill=skill.name, rule="evals/files"):
                self.assertEqual(files_problems(skill, listed_files(data)), [])
            with self.subTest(skill=skill.name, rule="at least one input file"):
                self.assertTrue(listed_files(data), "no eval carries an input file")
            with self.subTest(skill=skill.name, rule="machine paths"):
                self.assertEqual(machine_path_problems(skill), [])


def _synthetic():
    """A passing evals dict with a casual, a precise and an edge case; no input files."""
    def item(name):
        return {"id": name, "prompt": "A prompt that asks for one judgment.",
                "expected_output": "A short answer that names the decision.", "files": [],
                "assertions": ["The answer names the decision it made.",
                               "The answer does not present a jev answer as a verdict."]}

    return {"skill_name": "synthetic-skill",
            "evals": [item("casual-one"), item("casual-two"), item("precise-one"),
                      item("precise-two"), item("edge-one")]}


class TestEvalsShapeNonVacuity(unittest.TestCase):
    """The check fails where it claims to: a duplicate id, a missing edge case, and a bad
    trigger count. Each broken dict must produce a problem; the clean one must not."""

    SKILL = Path("synthetic-skill")

    def test_clean_synthetic_dict_passes(self):
        self.assertEqual(evals_problems(_synthetic(), self.SKILL), [])

    def test_duplicate_id_fails(self):
        data = _synthetic()
        data["evals"][1]["id"] = "casual-one"
        problems = evals_problems(data, self.SKILL)
        self.assertTrue(any("duplicate id casual-one" in p for p in problems), problems)

    def test_missing_edge_case_fails(self):
        data = copy.deepcopy(_synthetic())
        data["evals"][4]["id"] = "precise-three"
        problems = evals_problems(data, self.SKILL)
        self.assertIn("missing edge case", problems)

    def test_trigger_count_out_of_range_fails(self):
        queries = [{"query": f"A realistic user request number {n} about a judgment.",
                    "should_trigger": n < 7} for n in range(16)]
        problems = trigger_problems(queries)
        self.assertTrue(any("should_trigger true" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
