"""Drift guard: skills/ai-kit-spec-review jsonc_read vs tools/config_doctor_readers (D-03).

jsonc_read is a read-only copy of the doctor's JSONC scanner. On shared synthetic fixtures both
must yield the same provider names; a non-vacuity case proves the comparison can fail.
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

_REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO, "skills", "ai-kit-spec-review"))

from ai_kit_spec import jsonc_read

_READERS_PATH = os.path.join(_REPO, "tools", "config_doctor_readers.py")
_spec = importlib.util.spec_from_file_location("config_doctor_readers", _READERS_PATH)
assert _spec is not None and _spec.loader is not None
config_doctor_readers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(config_doctor_readers)

FIXTURES = {
    "comments": '// top\n{"provider": {"a": {}}, /* x */ "providers": {"b": {}}}\n',
    "trailing_commas": '{"provider": {"a": {},}, "providers": {"b": {},},}\n',
    "escaped_strings": (
        '{"provider": {"a": {"name": "x \\"//\\" y"}}, "other": "/* not a comment */"}\n'
    ),
    "v1_provider_only": '{"provider": {"mine": {}}}\n',
    "v2_providers_only": '{"providers": {"mine2": {}}}\n',
}


def _doctor_names(path):
    state, data = config_doctor_readers.read_jsonc_checked(path)
    if state != "ok":
        return None
    names = []
    for key in ("provider", "providers"):
        section = config_doctor_readers.get_nested(data, key, default={})
        if isinstance(section, dict):
            names.extend(name for name in section if name not in names)
    return names


def _reader_without_comma_strip(path):
    """A deliberately weaker copy: comments stripped, trailing commas left in place."""
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    try:
        data = json.loads(jsonc_read.strip_jsonc_comments(text))
    except ValueError:
        return None
    section = data.get("provider", {}) if isinstance(data, dict) else {}
    return list(section) if isinstance(section, dict) else None


class TestJsoncReadDrift(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="ai-kit-p31-")
        cls.paths = {}
        for name, text in FIXTURES.items():
            path = os.path.join(cls.tmp, f"{name}.jsonc")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
            cls.paths[name] = path

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_each_fixture_matches_the_doctor_reader(self):
        for name, path in self.paths.items():
            with self.subTest(fixture=name):
                self.assertEqual(
                    sorted(jsonc_read.read_provider_names(path) or []),
                    sorted(_doctor_names(path) or []),
                )

    def test_drift_guard_is_non_vacuous(self):
        path = self.paths["trailing_commas"]
        self.assertIsNone(_reader_without_comma_strip(path))
        self.assertEqual(sorted(_doctor_names(path) or []), ["a", "b"])
        self.assertNotEqual(_reader_without_comma_strip(path), _doctor_names(path))

    def test_invalid_file_returns_none(self):
        path = os.path.join(self.tmp, "broken.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        self.assertIsNone(jsonc_read.read_provider_names(path))
        self.assertIsNone(jsonc_read.read_provider_names(os.path.join(self.tmp, "missing.json")))

    def test_deeply_nested_file_returns_none(self):
        path = os.path.join(self.tmp, "deep.json")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("[" * 200000)
        self.assertIsNone(jsonc_read.read_provider_names(path))


if __name__ == "__main__":
    unittest.main()
