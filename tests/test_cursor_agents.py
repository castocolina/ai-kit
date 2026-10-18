"""AGT-01 Cursor subagents: port the bundle parser and pin D-06, D-07 and D-08."""

import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENTS_DIR = os.path.join(REPO_ROOT, "cursor-agents")
FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "cursor_models.txt")
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import detection

_FM = re.compile(r"^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)$", re.M)
BUNDLE_FIELDS = frozenset({
    "name", "description", "model", "force-default-model", "readonly", "background",
    "is_background", "tools",
})


def parse_agent(text: str) -> dict | None:
    """Port the Cursor bundle line parser; None means the loader drops this file."""
    match = _FM.search(text)
    if not match or not match.group(2).strip():
        return None
    fields = {}
    for raw in match.group(1).split("\n"):
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        if key.strip():
            fields[key.strip().lower()] = value.strip()
    fields["__body__"] = match.group(2)
    return fields


def _agent_files() -> list[Path]:
    return sorted(Path(AGENTS_DIR).glob("*.md"))


def _parsed_agents() -> list[tuple[Path, dict]]:
    parsed = []
    for path in _agent_files():
        fields = parse_agent(path.read_text(encoding="utf-8"))
        if fields is not None:
            parsed.append((path, fields))
    return parsed


class TestCursorAgents(unittest.TestCase):
    def test_exactly_the_two_shipped_files_exist(self):
        self.assertEqual([path.name for path in _agent_files()], [
            "composer-worker.md", "grok-worker.md",
        ])

    def test_files_parse_with_the_bundle_rules(self):
        for path, fields in _parsed_agents():
            with self.subTest(path=path.name):
                self.assertTrue(fields["__body__"].strip())

    def test_only_bundle_fields_are_used(self):
        for path, fields in _parsed_agents():
            with self.subTest(path=path.name):
                self.assertLessEqual(set(fields) - {"__body__"}, BUNDLE_FIELDS)
        invalid = parse_agent("---\nname: sample\ntools-extra: shell\n---\nbody")
        self.assertIsNotNone(invalid)
        assert invalid is not None
        fields = set(invalid) - {"__body__"}
        self.assertFalse(fields <= BUNDLE_FIELDS)

    def test_values_are_unquoted_single_line_scalars(self):
        for path, fields in _parsed_agents():
            for key, value in fields.items():
                if key != "__body__":
                    with self.subTest(path=path.name, key=key):
                        self.assertFalse(value.startswith(("'", '"', "|", ">")))

    def test_names_match_stems_and_never_gsd_prefix(self):
        for path, fields in _parsed_agents():
            name = fields["name"]
            with self.subTest(path=path.name):
                self.assertEqual(name, path.stem)
                self.assertFalse(name.startswith("gsd-"))

    def test_pins_are_non_fast_ids_from_the_captured_listing(self):
        parsed_ids = detection.parse_cursor_models(Path(FIXTURE).read_text(encoding="utf-8"))
        self.assertIsNotNone(parsed_ids)
        assert parsed_ids is not None
        ids = set(parsed_ids)
        pins = set()
        for path, fields in _parsed_agents():
            model = fields["model"]
            pins.add(model)
            with self.subTest(path=path.name):
                self.assertIn(model, ids)
                self.assertFalse(model.endswith("-fast"))
                self.assertIn(model + "-fast", ids)
        self.assertEqual(pins, {"composer-2.5", "grok-4.7-medium"})

    @unittest.skipUnless(shutil.which("node"), "node not on PATH")
    def test_bundle_regex_parity_with_node(self):
        """Check regex dialects on two shipped files and selected fields, not full equivalence."""
        javascript = r"""const fs=require('fs');
const text=fs.readFileSync(process.argv[1],'utf8');
const m=text.match(/^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)$/m);
if(!m||!m[2].trim()){process.stdout.write('null');process.exit(0)}
const fields={};
for(const raw of m[1].split('\n')){const line=raw.trim();if(!line||line.startsWith('#'))continue;
const i=line.indexOf(':');if(i<0)continue;const key=line.slice(0,i).trim().toLowerCase();
const value=line.slice(i+1).trim();if(key)fields[key]=value;}
process.stdout.write(JSON.stringify({name:fields.name,description:fields.description,model:fields.model,body_empty:m[2].trim().length===0}));"""
        node = shutil.which("node")
        assert node is not None
        for path, fields in _parsed_agents():
            result = subprocess.run(
                [node, "-e", javascript, "--", str(path)],
                capture_output=True, text=True, check=False, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            oracle = json.loads(result.stdout)
            expected = {key: fields[key] for key in ("name", "description", "model")}
            expected["body_empty"] = not fields["__body__"].strip()
            self.assertEqual(oracle, expected, path.name)

    def test_parser_drops_a_file_with_an_empty_body(self):
        self.assertIsNone(parse_agent("---\nname: sample\n---\n \n"))

    def test_parser_requires_a_frontmatter_block(self):
        self.assertIsNone(parse_agent("name: sample\n\nbody\n"))

    def test_leading_text_before_the_block_still_matches(self):
        parsed = parse_agent("preface\n---\nname: sample\n---\nbody\n")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed["name"], "sample")


if __name__ == "__main__":
    unittest.main()
