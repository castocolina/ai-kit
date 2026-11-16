"""PyYAML cross-check of the strict frontmatter gate (32 SPEC R8, D-17).

Parses the same fixtures and the installable tree with PyYAML's safe loader, extended to
reject duplicate keys, and checks that the gate and PyYAML agree on every fixture except the
designed-stricter cases. Runs under uv: PyYAML is a locked dev dependency, listed in
UNIT_UV_MODULES of tools/run_unittest_parallel.py.
"""
import unittest

import yaml

from tests.test_skill_frontmatter import (
    DESIGNED_STRICTER,
    FIXTURES,
    REPO_ROOT,
    entry_files,
    field_problems,
)


class UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects a duplicate mapping key instead of keeping the last value."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, f"found duplicate key {key!r}", key_node.start_mark
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def frontmatter_body(text):
    """The YAML between the opening and closing `---` lines, or None without a block."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 3)
    if end < 0:
        return None
    return text[4:end + 1]


def yaml_accepts(text, folder):
    """True when PyYAML (with UniqueKeyLoader) reads the block and the field rules hold."""
    body = frontmatter_body(text)
    if body is None:
        return False
    try:
        data = yaml.load(body, Loader=UniqueKeyLoader)
    except yaml.YAMLError:
        return False
    if not isinstance(data, dict):
        return False
    return not field_problems(data, folder)


def _must_body(text):
    """frontmatter_body for a text that must have a frontmatter block."""
    body = frontmatter_body(text)
    assert body is not None, "no frontmatter block"
    return body


class TestPyYamlCrossCheck(unittest.TestCase):
    def test_fixture_results_match_the_gate(self):
        for label, text, folder, accepted in FIXTURES:
            with self.subTest(label=label):
                expected = True if label in DESIGNED_STRICTER else accepted
                self.assertEqual(yaml_accepts(text, folder), expected)

    def test_duplicate_keys_need_the_unique_loader(self):
        body = _must_body("---\nname: first\nname: demo\ndescription: d\n---\n")
        self.assertEqual(yaml.safe_load(body)["name"], "demo")
        with self.assertRaises(yaml.constructor.ConstructorError):
            yaml.load(body, Loader=UniqueKeyLoader)

    def test_tree_frontmatter_loads(self):
        for cat, name, md in entry_files(REPO_ROOT):
            with self.subTest(entry=f"{cat}/{name}"):
                body = _must_body(md.read_text(encoding="utf-8"))
                data = yaml.load(body, Loader=UniqueKeyLoader)
                self.assertIsInstance(data, dict)
                self.assertIsInstance(data.get("name"), str)
                self.assertIsInstance(data.get("description"), str)
                if cat == "skills":
                    self.assertEqual(field_problems(data, name), [])
