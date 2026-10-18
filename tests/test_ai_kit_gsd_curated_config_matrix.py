"""Real-node resolve-model matrices for Claude, Codex and OpenCode hosts."""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest

from tests import gsd_curated_eval as ev
from tests.test_curated_config_apply_e2e import _REPO_CONFIG, _REPO_RUNNER, _gsd16_or_skip, _sha256
from tests.test_curated_config_e2e import REPO_ROOT, _RealGsdTestCase

_TOOLS = str(REPO_ROOT / ".claude" / "gsd-core" / "bin" / "gsd-tools.cjs")
_ROW_COUNT = len(ev.COMBOS) * len(ev.PATHS)


class _ResolveModelMatrixMixin(unittest.TestCase):
    HOST = "claude"

    @classmethod
    def setUpClass(cls) -> None:
        node_bin = _gsd16_or_skip(unittest.TestCase())
        cls.core_root = os.path.dirname(os.path.dirname(_TOOLS))
        cls.tables = ev.live_tables(node_bin, cls.core_root)
        cls.before = (_sha256(_REPO_CONFIG), _sha256(_REPO_RUNNER))
        cls.home_dir = str(pathlib.Path.home())
        cls.snap_before = ev.snapshot(REPO_ROOT, cls.home_dir)
        cls.result = ev.run_matrix(node_bin, _TOOLS, cls.home_dir, host=cls.HOST)

    def rows(self) -> list[dict]:
        return self.result["rows"]

    def test_key_parity(self) -> None:
        profiles, phase = self.tables["profiles"], self.tables["phase"]
        self.assertEqual(set(profiles), set(phase))
        self.assertGreaterEqual(len(profiles), 35)
        self.assertEqual(self.result["agents"], len(profiles))

    def test_row_shape_and_combination_order(self) -> None:
        self.assertEqual(len(self.rows()), _ROW_COUNT)
        self.assertEqual(
            [row["combo"] for row in self.rows()],
            [f"{r}/{p}" for r, p in ev.COMBOS for _ in ev.PATHS],
        )
        self.assertEqual([row["path"] for row in self.rows()], list(ev.PATHS) * len(ev.COMBOS))
        for row in self.rows():
            self.assertEqual(row["checks"], self.result["agents"])
        self.assertEqual(
            self.result["checks"], _ROW_COUNT * self.result["agents"] + 2 * self.result["agents"]
        )

    def test_five_combinations_two_paths(self) -> None:
        for row in self.rows():
            with self.subTest(combo=row["combo"], path=row["path"]):
                self.assertEqual(row["mismatches"], [])

    def test_control_one_discriminates(self) -> None:
        control = self.result["controls"]["control_1"]
        self.assertTrue(control["ok"], f"control 1 vacuous: {control}")
        self.assertGreater(control["expected_failures"], 0)
        self.assertEqual(control["observed"], control["expected_failures"])

    def test_control_two_clean_defaults_pass(self) -> None:
        self.assertTrue(self.result["controls"]["control_2"]["ok"])

    def test_informational_row_is_host_appropriate(self) -> None:
        info = self.result["informational"]
        if self.HOST == "claude":
            self.assertIs(info["informational"], True)
            self.assertIs(info["runtime_in_config"], True)
            self.assertIn("not gating", info["why"])
        else:
            self.assertIsNone(info)

    def test_output_carries_no_absolute_path(self) -> None:
        text = json.dumps(self.result, sort_keys=True)
        for root in (
            self.home_dir,
            str(REPO_ROOT),
            tempfile.gettempdir(),
            os.environ.get("TMPDIR", ""),
        ):
            if root and root != "/":
                self.assertNotIn(root, text)
        self.assertIn(ev.GSD_CORE_LABEL, text)

    def test_repo_config_untouched(self) -> None:
        self.assertEqual((_sha256(_REPO_CONFIG), _sha256(_REPO_RUNNER)), self.before)

    def test_snapshot_strict_set_unchanged_across_the_run(self) -> None:
        strict, _host = ev.snapshot_diff(self.snap_before, ev.snapshot(REPO_ROOT, self.home_dir))
        self.assertEqual(strict, [])


class TestResolveModelMatrix(_ResolveModelMatrixMixin, _RealGsdTestCase):
    """Claude matrix regression baseline."""


class TestResolveModelMatrixCodex(_ResolveModelMatrixMixin, _RealGsdTestCase):
    HOST = "codex"


class TestResolveModelMatrixOpencode(_ResolveModelMatrixMixin, _RealGsdTestCase):
    HOST = "opencode"


if __name__ == "__main__":
    unittest.main()
