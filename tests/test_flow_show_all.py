"""fold.py show --all: the read-only all-units view (SPEC R7)."""

import contextlib
import io
import os
import pathlib
import sys
from unittest import mock

_REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-commit-fold" / "scripts"))
sys.path.insert(0, str(_REPO))

import flow_record
import flow_stack
import flow_unit
import fold

from tests import fold_fixtures as f
from tests.test_flow_stack import BR_A, BR_B, BR_C, _StackCase


class TestShowAll(_StackCase):
    def _record_bytes(self):
        path = self.repo / ".git" / "ai-kit-stack.json"
        return path.read_bytes() if path.exists() else None

    def _refs_and_head(self):
        return (
            f.run_git(self.repo, self.env, "for-each-ref", "--format=%(refname) %(objectname)"),
            f.run_git(self.repo, self.env, "branch", "--show-current"),
        )

    def test_three_units_with_a_deleted_branch_print_in_stack_order(self):
        self.build_stack()
        f.run_git(self.repo, self.env, "switch", BR_B)
        f.run_git(self.repo, self.env, "branch", "-D", BR_C)
        before = self._record_bytes()
        remote = {b: self.remote_tip(b) for b in (BR_A, BR_B, BR_C)}
        code, text = self.fold("show", "--all")
        self.assertEqual(code, 0, text)
        tip_a = self.rev(BR_A)[:12]
        tip_b = self.rev(BR_B)[:12]
        self.assertEqual(text.splitlines(), [
            f"unit unit-a branch {BR_A} parent main state open exists yes tip {tip_a}",
            f"unit unit-b branch {BR_B} parent {BR_A} state open exists yes tip {tip_b}",
            f"unit unit-c branch {BR_C} parent {BR_B} state open exists no tip none",
        ])
        self.assertEqual(self._record_bytes(), before)
        self.assertEqual({b: self.remote_tip(b) for b in (BR_A, BR_B, BR_C)}, remote)

    def test_no_recorded_unit_prints_units_none(self):
        before = self._record_bytes()
        code, text = self.fold("show", "--all")
        self.assertEqual(code, 0, text)
        self.assertEqual(text.strip(), "units: none")
        self.assertEqual(self._record_bytes(), before)

    def test_decimal_id_and_same_tip_units_print_verbatim(self):
        self.start_unit("phase-02.1", "demo/phase-02.1-x.y")
        self.start_unit("unit-b", BR_B)
        code, text = self.fold("show", "--all")
        self.assertEqual(code, 0, text)
        tip = self.rev("refs/heads/demo/phase-02.1-x.y")[:12]
        first = (
            "unit phase-02.1 branch demo/phase-02.1-x.y parent main "
            f"state open exists yes tip {tip}"
        )
        second = (
            f"unit unit-b branch {BR_B} parent demo/phase-02.1-x.y "
            f"state open exists yes tip {tip}"
        )
        self.assertEqual(text.splitlines(), [first, second])

    def test_reads_no_settings_and_runs_no_sync(self):
        self.build_stack()
        before = self._record_bytes()
        refs = self._refs_and_head()
        remote = {b: self.remote_tip(b) for b in (BR_A, BR_B, BR_C)}
        with (
            mock.patch.dict(os.environ, self.env),
            mock.patch.object(
                flow_unit, "read_settings", side_effect=AssertionError("read_settings called")
            ),
            mock.patch.object(
                flow_record, "read_settings", side_effect=AssertionError("read_settings called")
            ),
            mock.patch.object(
                flow_stack, "sync", side_effect=AssertionError("sync called")
            ),
            contextlib.redirect_stdout(io.StringIO()) as out,
        ):
            code = fold.main(["show", "--all", "--repo", str(self.repo)])
        self.assertEqual(code, 0)
        self.assertEqual(len(out.getvalue().splitlines()), 3)
        self.assertEqual(self._record_bytes(), before)
        self.assertEqual(self._refs_and_head(), refs)
        self.assertEqual({b: self.remote_tip(b) for b in (BR_A, BR_B, BR_C)}, remote)

    def test_all_is_offered_by_show_only_and_is_exclusive(self):
        code, _text = self.fold("guard", "--all")
        self.assertEqual(code, 2)
        code, _text = self.fold("show", "--all", "--unit-id", "unit-a")
        self.assertEqual(code, 2)
