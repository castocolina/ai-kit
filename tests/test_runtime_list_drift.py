"""One drift test ties every hand-copied runtime list to the RUNTIMES table (phase 31 R13).

Each copy is compared as a set with the table's ids (or the table's runner rows). A difference
passes only when it is listed in DELIBERATE with its reason. The JS template's RUNTIMES block is
parsed by brace matching, and its keys must equal the runner rows exactly.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
for rel in (
    ("skills", "ai-kit-gsd-curated-config"),
    ("skills", "ai-kit-spec-review"),
    ("skills", "ai-kit-spec-goal-prompt", "scripts"),
):
    sys.path.insert(0, str(REPO_ROOT.joinpath(*rel)))

import gp_host
from ai_kit_gsd_curated_config import cross_ai, cross_ai_build, host, preference_match
from ai_kit_spec.detection import RUNTIMES

TEMPLATE = REPO_ROOT / "skills" / "ai-kit-spec-review" / "references" / "cross-ai.mjs"
_JS_KEY = re.compile(r"^  ([\w-]+): \{")
_SUBSET = "deliberate subset: {module}.{name} lists only the runtimes it serves"

# (copy name, id) -> the reason the copy legitimately differs from the table.
DELIBERATE = {
    ("RUNNER_IDS", "claude"): "review-only: claude is a reviewer, not a curated runner choice",
    ("RUNNER_IDS", "copilot"): "not a curated runner choice: its runner rows are unverified",
    ("HOSTS", "copilot"): "no host support: the host list has no copilot entry",
    ("HOSTS", "grok"): "no host support: the host list has no grok entry",
    ("HOST_BINARY", "copilot"): "no host support: the goal-prompt host map has no copilot entry",
    ("HOST_BINARY", "grok"): "no host support: the goal-prompt host map has no grok entry",
    ("REVIEWER_SLUGS", "codex"): _SUBSET.format(module="cross_ai_build", name="REVIEWER_SLUGS"),
    ("REVIEWER_SLUGS", "pi"): _SUBSET.format(module="cross_ai_build", name="REVIEWER_SLUGS"),
    ("REVIEWER_SLUGS", "copilot"): _SUBSET.format(module="cross_ai_build", name="REVIEWER_SLUGS"),
    ("REVIEWER_SLUGS", "grok"): _SUBSET.format(module="cross_ai_build", name="REVIEWER_SLUGS"),
    ("_RUNTIME_ORDER", "claude"): _SUBSET.format(module="preference_match",
                                                 name="_RUNTIME_ORDER"),
    ("_RUNTIME_ORDER", "codex"): _SUBSET.format(module="preference_match", name="_RUNTIME_ORDER"),
    ("_RUNTIME_ORDER", "pi"): _SUBSET.format(module="preference_match", name="_RUNTIME_ORDER"),
    ("_RUNTIME_ORDER", "copilot"): _SUBSET.format(module="preference_match",
                                                  name="_RUNTIME_ORDER"),
    ("_RUNTIME_ORDER", "grok"): _SUBSET.format(module="preference_match", name="_RUNTIME_ORDER"),
}
# Copies that are deliberately empty (an empty copy fails unless its name is listed here).
DELIBERATE_EMPTY: set[str] = set()


def runtime_list_differences(name, copy, expected):
    """One readable line per id where `copy` and `expected` differ and no DELIBERATE entry
    covers it; [] exactly when every difference is listed."""
    copy_ids, expected_ids = set(copy), set(expected)
    if not copy_ids:
        if name in DELIBERATE_EMPTY:
            return []
        return [f"{name} is empty and is not listed as deliberately empty"]
    lines = []
    for rid in sorted(copy_ids - expected_ids):
        if (name, rid) not in DELIBERATE:
            lines.append(f"{name} lists {rid}, which RUNTIMES does not define")
    for rid in sorted(expected_ids - copy_ids):
        if (name, rid) not in DELIBERATE:
            lines.append(f"{name} lacks {rid}, which RUNTIMES defines")
    return lines


def template_runtime_ids(source: str) -> set[str]:
    """The keys of the JS template's `const RUNTIMES = {` block at depth 1 (brace matched)."""
    lines = source[source.index("const RUNTIMES = {"):].splitlines()
    ids: set[str] = set()
    depth = 0
    for line in lines:
        if depth == 1:
            match = _JS_KEY.match(line)
            if match:
                ids.add(match.group(1))
        depth += line.count("{") - line.count("}")
        if depth == 0:
            break
    return ids


def _runner_ids() -> set[str]:
    return {rid for rid, row in RUNTIMES.items() if row.runner}


class TestRuntimeListDrift(unittest.TestCase):
    def test_runner_ids_match_the_table_runner_rows(self):
        self.assertEqual(
            runtime_list_differences("RUNNER_IDS", cross_ai.RUNNER_IDS, _runner_ids()), [])

    def test_hosts_match_every_table_id(self):
        self.assertEqual(
            runtime_list_differences("HOSTS", host.HOSTS, RUNTIMES), [])

    def test_host_binary_ids_match_and_each_binary_is_the_runtimes_own(self):
        self.assertEqual(
            runtime_list_differences("HOST_BINARY", gp_host.HOST_BINARY, RUNTIMES), [])
        for rid, binary in gp_host.HOST_BINARY.items():
            if rid in RUNTIMES:
                self.assertIn(binary, RUNTIMES[rid].binaries, rid)

    def test_reviewer_slugs_match_every_table_id(self):
        self.assertEqual(
            runtime_list_differences("REVIEWER_SLUGS", cross_ai_build.REVIEWER_SLUGS, RUNTIMES),
            [])

    def test_runtime_order_matches_every_table_id(self):
        self.assertEqual(
            runtime_list_differences("_RUNTIME_ORDER", preference_match._RUNTIME_ORDER, RUNTIMES),
            [])

    def test_js_template_keys_equal_the_runner_rows_exactly(self):
        source = TEMPLATE.read_text(encoding="utf-8")
        self.assertEqual(
            runtime_list_differences("cross-ai.mjs RUNTIMES",
                                     template_runtime_ids(source), _runner_ids()),
            [])


class TestHelperIsNonVacuous(unittest.TestCase):
    def test_a_copy_only_runtime_in_a_python_copy_is_reported(self):
        lines = runtime_list_differences(
            "RUNNER_IDS", (*cross_ai.RUNNER_IDS, "zz-new"), _runner_ids())
        self.assertTrue(any("zz-new" in line for line in lines), lines)

    def test_a_copy_only_runtime_in_the_js_key_set_is_reported(self):
        keys = template_runtime_ids(TEMPLATE.read_text(encoding="utf-8")) | {"zz-new"}
        lines = runtime_list_differences("cross-ai.mjs RUNTIMES", keys, _runner_ids())
        self.assertTrue(any("zz-new" in line for line in lines), lines)

    def test_an_empty_copy_fails_unless_listed_as_deliberately_empty(self):
        self.assertNotEqual(runtime_list_differences("zz-empty", (), _runner_ids()), [])
        with mock.patch.object(sys.modules[__name__], "DELIBERATE_EMPTY", {"zz-empty"}):
            self.assertEqual(runtime_list_differences("zz-empty", (), _runner_ids()), [])

    def test_a_listed_difference_passes_and_an_unlisted_one_fails(self):
        listed = runtime_list_differences("HOSTS", host.HOSTS, RUNTIMES)
        self.assertEqual(listed, [])
        unlisted = runtime_list_differences("HOSTS", (*host.HOSTS, "zz-new"), RUNTIMES)
        self.assertEqual(len(unlisted), 1)


if __name__ == "__main__":
    unittest.main()
