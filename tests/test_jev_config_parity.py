"""D-02 parity of the copy in skills/jev-fast-decision/scripts/jev_config.py against
skills/ai-kit-spec-review/ai_kit_spec/config_io.py, toml_splice.py and cache.py (plan 34-01).

The files are parsed as text and ai_kit_spec is never imported, so a drifted copy fails here by
name. Each copied definition must dump (ast.dump) equal to its source definition."""

import ast
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPEC_DIR = REPO / "skills" / "ai-kit-spec-review" / "ai_kit_spec"
COPY = REPO / "skills" / "jev-fast-decision" / "scripts" / "jev_config.py"

CONFIG_NAMES = (
    "cfg_local_path",
    "cfg_config_base",
    "cfg_global_path",
    "ConfigError",
    "cfg_load_toml",
    "cfg_read_bytes",
    "cfg_parse_toml_bytes",
    "cfg_load_layers",
    "_table_at",
    "cfg_layered_table",
)
SPLICE_NAMES = (
    "Block",
    "Span",
    "SpliceError",
    "_ESCAPES",
    "_MAX_SPAN_LINES",
    "_NAME_RE",
    "_apply_edits",
    "_basic_string",
    "_block_spans",
    "_child_keys",
    "_edit_block",
    "_ensure_table",
    "_find_close",
    "_float_text",
    "_header_path",
    "_indent",
    "_inline_table",
    "_insert_at",
    "_join",
    "_key_line",
    "_key_text",
    "_lead_start",
    "_leaf_path",
    "_new_table_text",
    "_newline",
    "_parse",
    "_read_span",
    "_refuse_table_arrays",
    "_scan",
    "_span_edits",
    "_splice_table",
    "_split_lines",
    "_table_index",
    "_value_at",
    "_verify",
    "_walk_dict",
    "_with_eol",
    "publish",
    "set_table",
    "split_blocks",
    "toml_key",
    "toml_value",
)
CACHE_NAMES = ("cache_write_bytes", "_fsync_folder")
COPIES = {
    "config_io.py": CONFIG_NAMES,
    "toml_splice.py": SPLICE_NAMES,
    "cache.py": CACHE_NAMES,
}


def _tree(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _defs(tree):
    found = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            found[node.name] = node
        elif (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            found[node.targets[0].id] = node
    return found


def copy_problems(copy_tree, source_tree, names, label):
    copy_defs = _defs(copy_tree)
    source_defs = _defs(source_tree)
    problems = []
    for name in names:
        if name not in copy_defs:
            problems.append(f"{name} missing from the copy")
        elif name not in source_defs:
            problems.append(f"{name} missing from {label}")
        elif ast.dump(copy_defs[name]) != ast.dump(source_defs[name]):
            problems.append(f"{name} differs from {label}; re-copy it")
    return problems


class TestCopyParity(unittest.TestCase):
    def test_every_copied_definition_matches_its_source(self):
        copy_tree = _tree(COPY)
        for file_name, names in COPIES.items():
            with self.subTest(source=file_name):
                problems = copy_problems(copy_tree, _tree(SPEC_DIR / file_name), names, file_name)
                self.assertEqual(problems, [])

    def test_tomllib_guard_matches(self):
        # Only config_io.py opens with the tomllib guard; toml_splice.py and cache.py have none.
        guard = next(node for node in _tree(COPY).body if isinstance(node, ast.Try))
        source_guard = next(
            node for node in _tree(SPEC_DIR / "config_io.py").body if isinstance(node, ast.Try)
        )
        self.assertEqual(ast.dump(guard), ast.dump(source_guard))

    def test_parity_check_is_not_vacuous(self):
        problems = copy_problems(
            ast.parse("def f():\n    return 2\n"),
            ast.parse("def f():\n    return 1\n"),
            ("f",),
            "x.py",
        )
        self.assertEqual(problems, ["f differs from x.py; re-copy it"])

    def test_copy_count_is_54(self):
        total = sum(len(names) for names in COPIES.values())
        self.assertEqual(total, 54)


if __name__ == "__main__":
    unittest.main()
