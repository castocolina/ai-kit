"""E2E tier: APP-05's resolve-model matrix against the checkout-local gsd-core, on real node.

Skips when node or a verified gsd-core line is missing (the same guard as
`tests/test_curated_config_apply_e2e.py`); everything else is a real run: five rigor/profile
combinations x both start paths x every agent read live from gsd-core, plus the two controls that
show the oracle can actually fail (D-04, D-08, D-09, D-10).

The matrix runs once for the class (each row is a scratch project, a real apply and ~35
resolve-model calls) and every test asserts on that structured result. No test here touches this
repo's config: every project lives under `mkdtemp()`, and `test_repo_config_untouched` proves it.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import tempfile
import unittest

from tests import gsd_curated_eval as ev
from tests.test_curated_config_apply_e2e import (
    _REPO_CONFIG,
    _REPO_RUNNER,
    _gsd16_or_skip,
    _sha256,
)
from tests.test_curated_config_e2e import REPO_ROOT, _RealGsdTestCase

_TOOLS = str(REPO_ROOT / ".claude" / "gsd-core" / "bin" / "gsd-tools.cjs")
_ROW_COUNT = len(ev.COMBOS) * len(ev.PATHS)


class TestResolveModelMatrix(_RealGsdTestCase):
    """The full matrix on this machine's real gsd-core, graded against the plan-derived oracle."""

    @classmethod
    def setUpClass(cls) -> None:
        # the same guard as the apply e2e tier, called on a stand-in case: its `skipTest` raises
        # SkipTest out of setUpClass, which is how the whole class skips on a box without node or
        # a verified gsd-core line
        node_bin = _gsd16_or_skip(unittest.TestCase())
        cls.core_root = os.path.dirname(os.path.dirname(_TOOLS))
        cls.tables = ev.live_tables(node_bin, cls.core_root)
        cls.before = (_sha256(_REPO_CONFIG), _sha256(_REPO_RUNNER))
        # the same protected-set snapshot the batch rails take, taken before the run so the
        # last test can prove a real-home matrix left the strict set byte-identical
        cls.home_dir = str(pathlib.Path.home())
        cls.snap_before = ev.snapshot(REPO_ROOT, cls.home_dir)
        cls.scratch_parent = tempfile.mkdtemp(prefix="xai-matrix-e2e-")
        cls.result = ev.run_matrix(node_bin, _TOOLS, cls.home_dir)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.scratch_parent, ignore_errors=True)

    def rows(self) -> list[dict]:
        return self.result["rows"]

    def test_key_parity(self) -> None:
        """Both live tables cover exactly the same agent set, and that set is what ran."""
        profiles, phase = self.tables["profiles"], self.tables["phase"]
        self.assertEqual(set(profiles), set(phase))
        self.assertGreaterEqual(len(profiles), 35)
        self.assertEqual(self.result["agents"], len(profiles))

    def test_row_shape_and_combination_order(self) -> None:
        """10 rows: every combination on both start paths, in the plan's order, each grading
        every live agent (so a silently-narrow row cannot pass)."""
        self.assertEqual(len(self.rows()), _ROW_COUNT)
        combos = [row["combo"] for row in self.rows()]
        self.assertEqual(combos, [f"{r}/{p}" for r, p in ev.COMBOS for _ in ev.PATHS])
        self.assertEqual([row["path"] for row in self.rows()],
                         list(ev.PATHS) * len(ev.COMBOS))
        for row in self.rows():
            self.assertEqual(row["checks"], self.result["agents"])
        self.assertEqual(self.result["checks"], _ROW_COUNT * self.result["agents"]
                         + 2 * self.result["agents"])

    def test_five_combinations_two_paths(self) -> None:
        """Every agent on every combination and start path resolves to the promised model and
        tier. Nothing is asserted about `dynamic_routing` for mvp or standard (R-14)."""
        for row in self.rows():
            with self.subTest(combo=row["combo"], path=row["path"]):
                self.assertEqual(row["mismatches"], [])

    def test_control_one_fails_every_unoverridden_agent(self) -> None:
        """T-19-01: with the `resolve_model_ids` unset removed from the plan, the copied omit
        poison empties every agent that has no explicit override - the oracle must see it."""
        control = self.result["controls"]["control_1"]
        self.assertTrue(control["ok"], f"control 1 vacuous: {control}")
        self.assertGreater(control["expected_failures"], 0)
        self.assertEqual(control["observed"], control["expected_failures"])

    def test_control_two_clean_defaults_pass(self) -> None:
        """The other half of the discrimination: a clean `GSD_HOME` on P1 has no defect to
        find, so the same oracle over the same agents reports nothing."""
        control = self.result["controls"]["control_2"]
        self.assertTrue(control["ok"], f"control 2 mismatches: {control['mismatches']}")
        self.assertEqual(control["mismatches"], [])

    def test_informational_runtime_row_is_flagged(self) -> None:
        """The runtime row records a condition, it never gates: flagged informational, the key
        really present in the scratch config, and a `why` that says it is not gating."""
        row = self.result["informational"]
        self.assertIs(row["informational"], True)
        self.assertIs(row["runtime_in_config"], True)
        self.assertIn("not gating", row["why"])
        self.assertEqual((row["combo"], row["path"], row["agent"]),
                         ("standard/adaptive", "P2", "gsd-planner"))

    def test_output_carries_no_absolute_path(self) -> None:
        """D-14/jev 19-S1: the structured result is labels and names only."""
        text = json.dumps(self.result, sort_keys=True)
        for root in (self.home_dir, str(REPO_ROOT), self.scratch_parent,
                     tempfile.gettempdir(), os.environ.get("TMPDIR", "/nonexistent-tmpdir")):
            if root and root != "/":
                self.assertNotIn(root, text)
        self.assertIn(ev.GSD_CORE_LABEL, text)

    def test_repo_config_untouched(self) -> None:
        """T-19-02: the matrix wrote nothing to this repo's config or runner."""
        self.assertEqual((_sha256(_REPO_CONFIG), _sha256(_REPO_RUNNER)), self.before)

    def test_snapshot_strict_set_unchanged_across_the_run(self) -> None:
        """T-19-02: the matrix's subprocesses get the real `HOME` (D-08), so the strict
        protected set - `~/.gsd/defaults.json`, the Claude settings, `~/.cursor/cli-config.json`
        and this repo's `.planning` files - must be byte-identical after the run."""
        strict, _host = ev.snapshot_diff(self.snap_before, ev.snapshot(REPO_ROOT, self.home_dir))
        self.assertEqual(strict, [])


if __name__ == "__main__":
    unittest.main()
