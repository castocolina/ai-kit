"""Tests for skills/ai-kit-spec-goal-prompt/scripts/gp_scope.py (GPS-01, GPS-02).

Detection is pure over injected JSON plus read-only repo reads. Every project is a temporary
tree built by tests/goal_prompt_fixtures.py; nothing runs a subprocess and no real home,
credential or network is touched.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "skills" / "ai-kit-spec-goal-prompt" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import gp_scope

from tests import goal_prompt_fixtures as fx


class TestPhases(unittest.TestCase):
    def _mixed(self, root):
        phases = [
            fx.phase_spec("16", "Alpha", spec=True, context=True, plans=2, reviews=True,
                          verification=True, cross_ai=1, disk_status="partial"),
            fx.phase_spec("16.1", "Beta", spec=True, context=False),
            fx.phase_spec("17", "Gamma", spec=False, context=False),
        ]
        fx.opengsd_project(root, phases)
        return phases, fx.roadmap_json(phases), fx.phase_op_json(root, phases)

    def test_mixed_states_match_their_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, roadmap, ops = self._mixed(Path(tmp))
            result = {p.number: p for p in gp_scope.load_phases(tmp, roadmap, ops, None)}
        p16 = result["16"]
        self.assertTrue(p16.has_spec)
        self.assertTrue(p16.has_context)
        self.assertEqual(p16.plan_count, 2)
        self.assertEqual(p16.cross_ai_plans, 1)
        self.assertTrue(p16.has_reviews)
        self.assertTrue(p16.has_verification)
        self.assertEqual(p16.disk_status, "partial")
        p161 = result["16.1"]
        self.assertTrue(p161.has_spec)
        self.assertFalse(p161.has_context)
        self.assertEqual(p161.plan_count, 0)
        self.assertFalse(p161.has_reviews)
        self.assertFalse(p161.has_verification)

    def test_order_is_numeric_not_roadmap_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            phases = [fx.phase_spec("16", "Alpha"), fx.phase_spec("16.1", "Beta"),
                      fx.phase_spec("17", "Gamma")]
            fx.opengsd_project(root, phases)
            roadmap = fx.roadmap_json(list(reversed(phases)))
            result = gp_scope.load_phases(tmp, roadmap, fx.phase_op_json(root, phases), None)
        self.assertEqual([p.number for p in result], ["16", "16.1", "17"])

    def test_numbers_select_a_subset_in_numeric_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, roadmap, ops = self._mixed(Path(tmp))
            result = gp_scope.load_phases(tmp, roadmap, ops, ["17", "16.1"])
        self.assertEqual([p.number for p in result], ["16.1", "17"])

    def test_requested_phase_missing_from_roadmap_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            phases, _, ops = self._mixed(Path(tmp))
            roadmap = fx.roadmap_json(phases[:2])
            with self.assertRaises(ValueError):
                gp_scope.load_phases(tmp, roadmap, ops, ["17"])

    def test_invalid_requested_number_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, roadmap, ops = self._mixed(Path(tmp))
            for number in ["x", "1..2", ""]:
                with self.subTest(number=number), self.assertRaises(ValueError):
                    gp_scope.load_phases(tmp, roadmap, ops, [number])

    def test_dir_is_repo_relative_and_serialized_result_has_no_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, roadmap, ops = self._mixed(Path(tmp))
            result = gp_scope.load_phases(tmp, roadmap, ops, None)
        self.assertEqual(result[0].dir, ".planning/phases/16-alpha")
        for phase in result:
            if phase.dir is not None:
                self.assertFalse(os.path.isabs(phase.dir))
        dumped = json.dumps([p._asdict() for p in result])
        self.assertNotIn(tmp, dumped)
        self.assertNotIn("state_path", dumped)

    def test_phase_without_directory_has_no_dir_and_no_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, roadmap, ops = self._mixed(Path(tmp))
            result = gp_scope.load_phases(tmp, roadmap, ops, ["17"])
        self.assertIsNone(result[0].dir)
        self.assertFalse(result[0].has_spec)
        self.assertEqual(result[0].cross_ai_plans, 0)

    def test_cross_ai_counts_frontmatter_lines_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, roadmap, ops = self._mixed(root)
            fx.write(root, ".planning/phases/16-alpha/16-03-PLAN.md",
                     "---\nphase: 16\n---\n\ncross_ai: true\n")
            result = gp_scope.load_phases(tmp, roadmap, ops, ["16"])
        self.assertEqual(result[0].cross_ai_plans, 1)

    def test_malformed_roadmap_raises_without_a_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            for roadmap in ({"phases": "nope"}, ["not", "an", "object"], {"phases": [1]}):
                with self.subTest(roadmap=roadmap), self.assertRaises(ValueError) as ctx:
                    gp_scope.load_phases(tmp, roadmap, {}, None)
                self.assertNotIn(tmp, str(ctx.exception))

    def test_absent_phase_ops_means_no_reviews_or_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, roadmap, _ = self._mixed(Path(tmp))
            result = gp_scope.load_phases(tmp, roadmap, {}, ["16"])
        self.assertFalse(result[0].has_reviews)
        self.assertFalse(result[0].has_verification)


class TestIdentity(unittest.TestCase):
    def test_exact_opengsd_package_name_is_opengsd(self):
        self.assertEqual(gp_scope.opengsd_identity(fx.identity_json(True)), "opengsd")

    def test_original_gsd_identity_is_unverified(self):
        self.assertEqual(gp_scope.opengsd_identity(fx.identity_json(False)), "unverified")

    def test_missing_or_empty_identity_is_unverified(self):
        for document in (None, {}, [], "@opengsd/gsd-core"):
            with self.subTest(document=document):
                self.assertEqual(gp_scope.opengsd_identity(document), "unverified")

    def test_near_miss_names_are_unverified(self):
        for name in ("@opengsd/gsd-core-evil", "@opengsd/gsd-core ", "@OpenGSD/gsd-core",
                     "opengsd/gsd-core"):
            with self.subTest(name=name):
                self.assertEqual(
                    gp_scope.opengsd_identity({"packageName": name}), "unverified")


def _load(plans):
    """Build a superpowers project from {filename: text}, load it, and return the Plan list."""
    with tempfile.TemporaryDirectory() as tmp:
        fx.superpowers_project(Path(tmp), plans)
        return gp_scope.load_plans(tmp)


class TestPlans(unittest.TestCase):
    def test_loads_sorted_by_filename_with_title_and_task_count(self):
        loaded = _load({
            "2026-01-02-b.md": fx.plan_text("Bravo", tasks=3),
            "2026-01-01-a.md": fx.plan_text("Alpha", tasks=2),
        })
        self.assertEqual([p.file for p in loaded], ["2026-01-01-a.md", "2026-01-02-b.md"])
        self.assertEqual([p.title for p in loaded], ["Alpha", "Bravo"])
        self.assertEqual([p.tasks for p in loaded], [2, 3])

    def test_backticked_filename_links_an_existing_plan(self):
        loaded = _load({
            "2026-01-01-a.md": fx.plan_text("A"),
            "2026-01-02-b.md": fx.plan_text("B", depends_on="`2026-01-01-a.md`"),
        })
        self.assertEqual(loaded[1].depends_on, ("2026-01-01-a.md",))
        self.assertEqual(loaded[1].free_text, ())

    def test_several_backticked_filenames_link_all(self):
        loaded = _load({
            "2026-01-01-a.md": fx.plan_text("A"),
            "2026-01-02-b.md": fx.plan_text("B"),
            "2026-01-03-c.md": fx.plan_text(
                "C", depends_on="`2026-01-01-a.md`, `2026-01-02-b.md`"),
        })
        self.assertEqual(loaded[2].depends_on, ("2026-01-01-a.md", "2026-01-02-b.md"))

    def test_free_text_is_data_not_an_edge(self):
        loaded = _load({
            "2026-01-01-a.md": fx.plan_text("A"),
            "2026-01-02-b.md": fx.plan_text("B", depends_on="the API plan"),
        })
        self.assertEqual(loaded[1].depends_on, ())
        self.assertEqual(loaded[1].free_text, ("the API plan",))

    def test_free_text_stays_one_entry_for_a_mixed_line(self):
        # Shaped like the repo's own plans: a linked filename followed by prose with snippets.
        loaded = _load({
            "2026-01-01-a.md": fx.plan_text("A"),
            "2026-01-02-b.md": fx.plan_text(
                "B", depends_on="`2026-01-01-a.md` (the renderer, the `sample`). Do it first."),
        })
        self.assertEqual(loaded[1].depends_on, ("2026-01-01-a.md",))
        self.assertEqual(loaded[1].free_text, ("(the renderer, the sample). Do it first.",))

    def test_backticked_name_that_is_not_a_loaded_plan_is_free_text(self):
        loaded = _load({"2026-01-01-a.md": fx.plan_text("A", depends_on="`nope.md`")})
        self.assertEqual(loaded[0].depends_on, ())
        self.assertEqual(loaded[0].free_text, ("nope.md",))

    def test_none_and_missing_line_are_independent(self):
        loaded = _load({
            "a.md": fx.plan_text("A", depends_on="none"),
            "b.md": fx.plan_text("B"),
        })
        for plan in loaded:
            with self.subTest(plan=plan.file):
                self.assertEqual(plan.depends_on, ())
                self.assertEqual(plan.free_text, ())

    def test_path_with_a_directory_does_not_link(self):
        loaded = _load({
            "2026-01-01-a.md": fx.plan_text("A"),
            "2026-01-02-b.md": fx.plan_text(
                "B", depends_on="`docs/superpowers/plans/2026-01-01-a.md`"),
        })
        self.assertEqual(loaded[1].depends_on, ())
        self.assertEqual(loaded[1].free_text, ("docs/superpowers/plans/2026-01-01-a.md",))

    def test_execution_order_chain_plus_independent(self):
        loaded = _load({
            "2026-01-01-a.md": fx.plan_text("A"),
            "2026-01-02-b.md": fx.plan_text("B", depends_on="`2026-01-01-a.md`"),
            "2026-01-03-c.md": fx.plan_text("C", depends_on="`2026-01-02-b.md`"),
            "2026-01-04-d.md": fx.plan_text("D"),
        })
        self.assertEqual(
            gp_scope.execution_order(loaded),
            ["2026-01-01-a.md", "2026-01-02-b.md", "2026-01-03-c.md", "2026-01-04-d.md"],
        )

    def test_independent_plan_that_sorts_first_runs_first(self):
        loaded = _load({
            "0-d.md": fx.plan_text("D"),
            "a.md": fx.plan_text("A"),
            "b.md": fx.plan_text("B", depends_on="`a.md`"),
            "c.md": fx.plan_text("C", depends_on="`b.md`"),
        })
        self.assertEqual(gp_scope.execution_order(loaded), ["0-d.md", "a.md", "b.md", "c.md"])

    def test_ties_keep_filename_order(self):
        loaded = _load({"z.md": fx.plan_text("Z"), "x.md": fx.plan_text("X"),
                        "y.md": fx.plan_text("Y")})
        self.assertEqual(gp_scope.execution_order(loaded), ["x.md", "y.md", "z.md"])

    def test_single_plan_gives_one_element_order(self):
        loaded = _load({"only.md": fx.plan_text("Only")})
        self.assertEqual(gp_scope.execution_order(loaded), ["only.md"])

    def test_cycle_raises_dependency_cycle(self):
        loaded = _load({
            "a.md": fx.plan_text("A", depends_on="`b.md`"),
            "b.md": fx.plan_text("B", depends_on="`a.md`"),
        })
        with self.assertRaises(ValueError) as ctx:
            gp_scope.execution_order(loaded)
        self.assertTrue(str(ctx.exception).startswith("dependency cycle"))

    def test_dependents_are_transitive_and_in_order(self):
        loaded = _load({
            "a.md": fx.plan_text("A"),
            "b.md": fx.plan_text("B", depends_on="`a.md`"),
            "c.md": fx.plan_text("C", depends_on="`b.md`"),
            "d.md": fx.plan_text("D"),
        })
        self.assertEqual(gp_scope.dependents(loaded, "a.md"), ["b.md", "c.md"])
        self.assertNotIn("d.md", gp_scope.dependents(loaded, "a.md"))

    def test_leaf_has_no_dependents(self):
        loaded = _load({
            "a.md": fx.plan_text("A"),
            "b.md": fx.plan_text("B", depends_on="`a.md`"),
        })
        self.assertEqual(gp_scope.dependents(loaded, "b.md"), [])

    def test_undecodable_plan_reads_as_empty_without_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx.superpowers_project(Path(tmp), {"good.md": fx.plan_text("Good")})
            bad = Path(tmp) / "docs" / "superpowers" / "plans" / "bad.md"
            bad.write_bytes(b"\xff\xfe# not utf-8\n")
            loaded = gp_scope.load_plans(tmp)
        by_name = {p.file: p for p in loaded}
        self.assertEqual(by_name["bad.md"].title, "")
        self.assertEqual(by_name["bad.md"].tasks, 0)
        self.assertEqual(by_name["good.md"].title, "Good")

    def test_symlinked_plan_is_not_loaded(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            fx.superpowers_project(Path(tmp), {"good.md": fx.plan_text("Good")})
            secret = Path(outside, "secret.md")
            secret.write_text("# TOPSECRET\n", encoding="utf-8")
            plans = Path(tmp) / "docs" / "superpowers" / "plans"
            os.symlink(secret, plans / "linked.md")
            loaded = gp_scope.load_plans(tmp)
        self.assertEqual([p.file for p in loaded], ["good.md"])

    def test_a_plan_is_read_only_up_to_the_cap(self):
        text = "# Cap\n### Task 1\n" + "x" * 64 + "\n### Task 2\n"
        with tempfile.TemporaryDirectory() as tmp:
            fx.superpowers_project(Path(tmp), {"a.md": text})
            with mock.patch.object(gp_scope, "READ_CAP", 32):
                loaded = gp_scope.load_plans(tmp)
        self.assertEqual((loaded[0].title, loaded[0].tasks), ("Cap", 1))


def _inputs(roadmap=None, phase_ops=None, identity=None, work_kind=None, numbers=None):
    return gp_scope.ScopeInputs(roadmap=roadmap, phase_ops=phase_ops, identity=identity,
                                work_kind=work_kind, numbers=numbers)


def _tree_state(root):
    """Every directory and file under root with its mtime (ns), for the read-only check."""
    state = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            path = os.path.join(dirpath, name)
            state[path] = os.stat(path).st_mtime_ns
    return state


class TestScopeKind(unittest.TestCase):
    def test_opengsd_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            phases = [fx.phase_spec("16", "Alpha", plans=1)]
            fx.opengsd_project(root, phases)
            scope = gp_scope.detect_scope(tmp, _inputs(
                roadmap=fx.roadmap_json(phases), phase_ops=fx.phase_op_json(root, phases),
                identity=fx.identity_json(True)))
        self.assertEqual(scope["kind"], "opengsd")
        self.assertEqual(scope["identity"], "opengsd")
        self.assertIsNone(scope["ask"])
        self.assertEqual([p["number"] for p in scope["phases"]], ["16"])
        self.assertEqual(scope["order"], ["16"])
        self.assertEqual(scope["roadmap_order"], ["16"])

    def test_original_gsd_fixture_is_gsd_unproven(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            phases = [fx.phase_spec("16", "Alpha")]
            fx.opengsd_project(root, phases)
            scope = gp_scope.detect_scope(tmp, _inputs(
                roadmap=fx.roadmap_json(phases), phase_ops=fx.phase_op_json(root, phases),
                identity=fx.identity_json(False)))
        self.assertEqual(scope["kind"], "gsd-unproven")
        self.assertEqual(scope["identity"], "unverified")
        self.assertEqual(len(scope["phases"]), 1)

    def test_superpowers_plans_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx.superpowers_project(Path(tmp), {
                "2026-01-01-a.md": fx.plan_text("A"),
                "2026-01-02-b.md": fx.plan_text("B", depends_on="`2026-01-01-a.md`"),
            })
            scope = gp_scope.detect_scope(tmp, _inputs())
        self.assertEqual(scope["kind"], "superpowers")
        self.assertEqual([p["file"] for p in scope["plans"]],
                         ["2026-01-01-a.md", "2026-01-02-b.md"])
        self.assertEqual(scope["order"], ["2026-01-01-a.md", "2026-01-02-b.md"])
        self.assertEqual(scope["phases"], [])
        self.assertIsNone(scope["ask"])

    def test_neither_asks_for_free_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx.empty_project(Path(tmp))
            scope = gp_scope.detect_scope(tmp, _inputs())
        self.assertEqual(scope["kind"], "none")
        self.assertIn("free text", scope["ask"])
        self.assertEqual(scope["order"], [])

    def test_both_asks_which_work_set_and_lists_both(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            phases = [fx.phase_spec("16", "Alpha")]
            fx.opengsd_project(root, phases)
            fx.superpowers_project(root, {"2026-01-01-a.md": fx.plan_text("A")})
            scope = gp_scope.detect_scope(tmp, _inputs(
                roadmap=fx.roadmap_json(phases), phase_ops=fx.phase_op_json(root, phases),
                identity=fx.identity_json(True)))
        self.assertEqual(scope["kind"], "both")
        self.assertIn("which work set", scope["ask"])
        self.assertEqual(len(scope["phases"]), 1)
        self.assertEqual(len(scope["plans"]), 1)
        self.assertEqual(scope["order"], [])

    def test_work_kind_phases_resolves_to_gsd(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            phases = [fx.phase_spec("16", "Alpha")]
            fx.opengsd_project(root, phases)
            fx.superpowers_project(root, {"2026-01-01-a.md": fx.plan_text("A")})
            scope = gp_scope.detect_scope(tmp, _inputs(
                roadmap=fx.roadmap_json(phases), phase_ops=fx.phase_op_json(root, phases),
                identity=fx.identity_json(True), work_kind="phases"))
        self.assertEqual(scope["kind"], "opengsd")
        self.assertIsNone(scope["ask"])
        self.assertEqual(scope["plans"], [])
        self.assertEqual(scope["order"], ["16"])

    def test_work_kind_plans_resolves_to_superpowers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            phases = [fx.phase_spec("16", "Alpha")]
            fx.opengsd_project(root, phases)
            fx.superpowers_project(root, {"2026-01-01-a.md": fx.plan_text("A")})
            scope = gp_scope.detect_scope(tmp, _inputs(
                roadmap=fx.roadmap_json(phases), phase_ops=fx.phase_op_json(root, phases),
                identity=fx.identity_json(True), work_kind="plans"))
        self.assertEqual(scope["kind"], "superpowers")
        self.assertIsNone(scope["ask"])
        self.assertEqual(scope["phases"], [])
        self.assertEqual(scope["order"], ["2026-01-01-a.md"])

    def test_scope_kind_truth_table_and_bad_work_kind(self):
        self.assertEqual(gp_scope.scope_kind(has_planning=True, identity="opengsd",
                                             plans_count=0, work_kind=None), "opengsd")
        self.assertEqual(gp_scope.scope_kind(has_planning=True, identity="unverified",
                                             plans_count=0, work_kind=None), "gsd-unproven")
        self.assertEqual(gp_scope.scope_kind(has_planning=False, identity="unverified",
                                             plans_count=2, work_kind=None), "superpowers")
        with self.assertRaises(ValueError):
            gp_scope.scope_kind(has_planning=False, identity="unverified",
                                plans_count=0, work_kind="both")

    def test_detection_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            phases = [fx.phase_spec("16", "Alpha", plans=1)]
            fx.opengsd_project(root, phases)
            fx.superpowers_project(root, {"2026-01-01-a.md": fx.plan_text("A")})
            inputs = _inputs(roadmap=fx.roadmap_json(phases),
                             phase_ops=fx.phase_op_json(root, phases),
                             identity=fx.identity_json(True))
            before = _tree_state(tmp)
            gp_scope.detect_scope(tmp, inputs)
            self.assertEqual(_tree_state(tmp), before)


if __name__ == "__main__":
    unittest.main()
