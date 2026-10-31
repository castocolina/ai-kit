"""Tests for skills/ai-kit-spec-goal-prompt/scripts/gp_matrix.py (GPS-01, SPEC R2, D-10/11/27).

The selector is pure: no subprocess, no file I/O, no network. Primitive tables are hand-built with
the keys gp_host.build_primitives emits, so no test needs a real host binary.
"""

import copy
import itertools
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "skills" / "ai-kit-spec-goal-prompt" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import gp_matrix
from gp_matrix import MatrixInputs


def prim(primitive, kind, availability="available", rank=0, surface="slash-command"):
    return {
        "host": "claude",
        "primitive": primitive,
        "kind": kind,
        "surface": surface,
        "availability": availability,
        "usage_source": "official docs",
        "survives_stall": rank > 0,
        "survives_process_death": rank > 1,
        "survives_reboot": rank > 2,
        "rank": rank,
        "note": "",
    }


# Four host tables for the property sweep (Task 2) and the row tests.
CLAUDE_LIKE = [
    prim("/goal", "goal", rank=0),
    prim("/loop", "loop", rank=0),
    prim("CronCreate recurring", "schedule", rank=1, surface="tool"),
    prim("systemd user timer", "os-timer", rank=3, surface="cli"),
]
CODEX_LIKE = [
    prim("/goal", "goal", "unverified", rank=0),
    prim("systemd user timer", "os-timer", rank=3, surface="cli"),
]
OPENCODE_LIKE = [
    prim("systemd user timer", "os-timer", rank=3, surface="cli"),
    prim("none", "none", "absent", rank=0, surface="cli"),
]
EMPTY: list[dict] = []


def select_for(scope, user=None, primitives=CLAUDE_LIKE, outlive=False, provable=False):
    return gp_matrix.select(MatrixInputs(scope, user, primitives, outlive, provable))


def ids(result):
    return [s["id"] for s in result["strategies"]]


def rows(result):
    return [s["row"] for s in result["strategies"]]


def recommended(result):
    return [s["recommended"] for s in result["strategies"]]


class TestRows(unittest.TestCase):
    """One test per matrix row id (SPEC R2 acceptance: one table test per row)."""

    def test_M01_opengsd_autonomous_alone(self):
        for user in (None, "autonomous"):
            with self.subTest(user=user):
                result = select_for("opengsd", user)
                self.assertEqual(rows(result), ["M01"])
                strategy = result["strategies"][0]
                self.assertEqual(
                    (strategy["id"], strategy["rank"], strategy["recommended"]),
                    ("autonomous", 1, True),
                )
                self.assertEqual((strategy["label"], strategy["primitive"]), ("", None))
                self.assertEqual(result["dropped"], [])

    def test_M02_opengsd_requested_goal_comes_first(self):
        result = select_for("opengsd", "goal", CLAUDE_LIKE)
        self.assertEqual(ids(result), ["goal", "autonomous"])
        self.assertEqual(rows(result), ["M02", "M02b"])
        self.assertEqual(recommended(result), [True, False])
        self.assertEqual(result["strategies"][0]["rank"], 1)
        self.assertEqual(result["strategies"][0]["primitive"], "/goal")
        self.assertEqual(result["dropped"], [])

    def test_M02b_opengsd_requested_goal_without_goal_is_dropped(self):
        result = select_for("opengsd", "goal", EMPTY)
        self.assertEqual(ids(result), ["autonomous"])
        self.assertEqual(rows(result), ["M02b"])
        self.assertEqual(result["strategies"][0]["rank"], 2)
        self.assertEqual(recommended(result), [True])
        self.assertEqual([d["id"] for d in result["dropped"]], ["goal"])
        self.assertTrue(result["dropped"][0]["reason"])

    def test_M03_opengsd_requested_loop_comes_first(self):
        result = select_for("opengsd", "loop", CLAUDE_LIKE)
        self.assertEqual(ids(result), ["loop", "autonomous"])
        self.assertEqual(rows(result), ["M03", "M02b"])
        self.assertEqual(recommended(result), [True, False])
        self.assertEqual(result["strategies"][0]["primitive"], "systemd user timer")
        self.assertEqual(result["dropped"], [])

    def test_M04_goal_when_provable(self):
        result = select_for("superpowers", None, CLAUDE_LIKE, outlive=False, provable=True)
        self.assertEqual(ids(result), ["goal"])
        self.assertEqual(rows(result), ["M04"])
        strategy = result["strategies"][0]
        self.assertEqual(
            (strategy["rank"], strategy["primitive"], strategy["label"]), (1, "/goal", "")
        )
        self.assertEqual(recommended(result), [True])

    def test_M05_goal_when_not_provable(self):
        result = select_for("none", None, CLAUDE_LIKE, outlive=False, provable=False)
        self.assertEqual(ids(result), ["goal"])
        self.assertEqual(rows(result), ["M05"])
        self.assertEqual(result["strategies"][0]["rank"], 2)
        self.assertEqual(recommended(result), [True])

    def test_M06_loop_when_outliving_and_not_provable(self):
        result = select_for("superpowers", None, OPENCODE_LIKE, outlive=True, provable=False)
        self.assertEqual(ids(result), ["loop"])
        self.assertEqual(rows(result), ["M06"])
        self.assertEqual(result["strategies"][0]["rank"], 1)
        self.assertEqual(result["strategies"][0]["primitive"], "systemd user timer")
        self.assertEqual(recommended(result), [True])

    def test_M07_loop_when_outliving_and_provable(self):
        result = select_for("gsd-unproven", None, OPENCODE_LIKE, outlive=True, provable=True)
        self.assertEqual(ids(result), ["loop", "autonomous"])
        self.assertEqual(rows(result), ["M07", "M08"])
        self.assertEqual(result["strategies"][0]["rank"], 2)
        self.assertEqual(recommended(result), [True, False])

    def test_M08_gsd_unproven_autonomous_is_unverified(self):
        result = select_for("gsd-unproven", None, EMPTY)
        self.assertEqual(ids(result), ["autonomous"])
        self.assertEqual(rows(result), ["M08"])
        strategy = result["strategies"][0]
        self.assertEqual((strategy["rank"], strategy["label"]), (3, "unverified"))
        self.assertIn("unverified", strategy["reason"])
        self.assertEqual(recommended(result), [True])

    def test_M09_plain_fallback_flags_the_os_timer_wake(self):
        result = select_for("superpowers", None, OPENCODE_LIKE, outlive=False, provable=False)
        self.assertEqual(ids(result), ["plain"])
        self.assertEqual(rows(result), ["M09"])
        strategy = result["strategies"][0]
        self.assertEqual((strategy["rank"], strategy["primitive"]), (9, "systemd user timer"))
        self.assertIn("OS-timer", strategy["reason"])
        self.assertIn("flagged", strategy["reason"])
        self.assertEqual(recommended(result), [True])

    def test_M09_plain_without_os_timer_names_no_wake(self):
        result = select_for("superpowers", None, EMPTY)
        strategy = result["strategies"][0]
        self.assertEqual((strategy["id"], strategy["row"]), ("plain", "M09"))
        self.assertIsNone(strategy["primitive"])
        self.assertIn("no OS-timer row", strategy["reason"])

    def test_M11g_requested_goal_has_rank_zero(self):
        result = select_for("superpowers", "goal", CLAUDE_LIKE, outlive=False, provable=False)
        self.assertEqual(ids(result), ["goal"])
        self.assertEqual(rows(result), ["M11g"])
        self.assertEqual(result["strategies"][0]["rank"], 0)
        self.assertEqual(recommended(result), [True])
        self.assertEqual(result["dropped"], [])

    def test_M11l_requested_loop_has_rank_zero_and_dies_with_session(self):
        session_loop = [prim("/loop", "loop", rank=0)]
        result = select_for("superpowers", "loop", session_loop, outlive=False)
        self.assertEqual(ids(result), ["loop"])
        self.assertEqual(rows(result), ["M11l"])
        strategy = result["strategies"][0]
        self.assertEqual(strategy["rank"], 0)
        self.assertIn("dies with the session", strategy["reason"])
        self.assertEqual(recommended(result), [True])


class TestWake(unittest.TestCase):
    """wake_primitive: the loop-capable row with the highest survival rank (D-07, SPEC R2)."""

    def test_highest_survival_rank_wins(self):
        table = [
            prim("CronCreate recurring", "schedule", rank=1, surface="tool"),
            prim("systemd user timer", "os-timer", rank=3, surface="cli"),
        ]
        self.assertEqual(
            gp_matrix.wake_primitive(table),
            {"primitive": "systemd user timer", "label": ""},
        )

    def test_label_unverified_when_row_not_available(self):
        for availability in ("unverified", "not seen"):
            with self.subTest(availability=availability):
                table = [prim("CronCreate recurring", "schedule", availability, rank=1)]
                self.assertEqual(
                    gp_matrix.wake_primitive(table),
                    {"primitive": "CronCreate recurring", "label": "unverified"},
                )

    def test_no_loop_capable_row_gives_none(self):
        for table in (EMPTY, [prim("/goal", "goal")], [prim("none", "none", "absent")]):
            with self.subTest(table=[row["primitive"] for row in table]):
                self.assertEqual(gp_matrix.wake_primitive(table), {"primitive": None, "label": ""})


class TestDerive(unittest.TestCase):
    """D-11: must_outlive and provable are derived, never asked."""

    def test_two_phases_outlive(self):
        self.assertTrue(gp_matrix.derive(2, False, False, 0)["must_outlive"])

    def test_one_phase_attended_does_not_outlive(self):
        self.assertFalse(gp_matrix.derive(1, False, False, 0)["must_outlive"])

    def test_unattended_outlives(self):
        self.assertTrue(gp_matrix.derive(1, True, False, 0)["must_outlive"])

    def test_e2e_detected_and_no_mockup_is_provable(self):
        self.assertTrue(gp_matrix.derive(1, False, False, 0)["provable"])

    def test_e2e_none_is_not_provable(self):
        self.assertFalse(gp_matrix.derive(1, False, True, 0)["provable"])

    def test_one_mockup_is_not_provable(self):
        self.assertFalse(gp_matrix.derive(1, False, False, 1)["provable"])


SCOPES = ("opengsd", "gsd-unproven", "superpowers", "none")
USERS = (None, "goal", "loop", "autonomous")
TABLES = {"claude": CLAUDE_LIKE, "codex": CODEX_LIKE, "opencode": OPENCODE_LIKE, "empty": EMPTY}


def sweep():
    """Every (scope, request, host table, must_outlive, provable) combination."""
    for scope, user, (name, table), outlive, provable in itertools.product(
        SCOPES, USERS, TABLES.items(), (False, True), (False, True)
    ):
        case = (scope, user, name, outlive, provable)
        yield case, select_for(scope, user, table, outlive, provable)


class TestProperties(unittest.TestCase):
    """Invariants over the whole input space (SPEC R2 edges: adjacency, empty, ordering)."""

    def test_one_to_three_strategies_exactly_one_recommended_first(self):
        for case, result in sweep():
            with self.subTest(case=case):
                strategies = result["strategies"]
                self.assertTrue(1 <= len(strategies) <= 3)
                self.assertEqual(recommended(result).count(True), 1)
                self.assertTrue(strategies[0]["recommended"])

    def test_ids_unique_and_ranks_non_decreasing(self):
        for case, result in sweep():
            with self.subTest(case=case):
                self.assertEqual(len(set(ids(result))), len(ids(result)))
                ranks = [s["rank"] for s in result["strategies"]]
                self.assertEqual(ranks, sorted(ranks))

    def test_no_goal_without_a_goal_primitive(self):
        for case, result in sweep():
            _scope, user, name, _outlive, _provable = case
            if name not in ("opencode", "empty"):
                continue
            with self.subTest(case=case):
                self.assertNotIn("goal", ids(result))
                if user == "goal":
                    self.assertIn("goal", [d["id"] for d in result["dropped"]])

    def test_opengsd_always_offers_autonomous(self):
        for case, result in sweep():
            scope, user, _name, _outlive, _provable = case
            if scope != "opengsd":
                continue
            with self.subTest(case=case):
                self.assertIn("autonomous", ids(result))
                if user is None:
                    self.assertEqual(ids(result), ["autonomous"])

    def test_gsd_unproven_autonomous_is_labelled_unverified(self):
        for case, result in sweep():
            if case[0] != "gsd-unproven":
                continue
            with self.subTest(case=case):
                autonomous = [s for s in result["strategies"] if s["id"] == "autonomous"]
                self.assertTrue(autonomous)
                self.assertTrue(all(s["label"] == "unverified" for s in autonomous))

    def test_reasons_are_plain_text_without_paths_or_jev(self):
        for case, result in sweep():
            with self.subTest(case=case):
                texts = [s["reason"] for s in result["strategies"]]
                texts += [d["reason"] for d in result["dropped"]]
                for text in texts:
                    self.assertTrue(text)
                    for banned in ("FAKE_HOME", "/home/", "/var/home/"):
                        self.assertNotIn(banned, text)
                    self.assertNotIn("jev", text.lower())

    def test_select_is_pure(self):
        for scope, user, name, outlive, provable in itertools.product(
            SCOPES, USERS, TABLES, (False, True), (False, True)
        ):
            table = TABLES[name]
            before = copy.deepcopy(table)
            inputs = gp_matrix.MatrixInputs(scope, user, table, outlive, provable)
            with self.subTest(case=(scope, user, name, outlive, provable)):
                self.assertEqual(gp_matrix.select(inputs), gp_matrix.select(copy.deepcopy(inputs)))
                self.assertEqual(table, before)

    def test_ties_keep_matrix_order(self):
        # No live row pair shares a rank with both firing, so the tie rule is pinned on a
        # synthetic RULES tuple: three rows, all rank 1, all firing for the same input.
        base = {
            "scopes": None,
            "user": None,
            "needs": None,
            "outlive": None,
            "provable": None,
            "rank": 1,
            "reason": "tie",
        }
        rows_in_order = (
            dict(base, id="T1", strategy="goal"),
            dict(base, id="T2", strategy="loop"),
            dict(base, id="T3", strategy="autonomous"),
        )
        for ordered, expected in (
            (rows_in_order, ["goal", "loop", "autonomous"]),
            (tuple(reversed(rows_in_order)), ["autonomous", "loop", "goal"]),
        ):
            with self.subTest(expected=expected), mock.patch.object(gp_matrix, "RULES", ordered):
                result = select_for("none", None, CLAUDE_LIKE)
                self.assertEqual(ids(result), expected)
                self.assertEqual(recommended(result), [True, False, False])

    def test_loop_primitive_follows_survival_rank(self):
        timer_and_cron = [
            prim("CronCreate recurring", "schedule", rank=1, surface="tool"),
            prim("systemd user timer", "os-timer", rank=3, surface="cli"),
        ]
        loop = select_for("superpowers", None, timer_and_cron, outlive=True)["strategies"][0]
        self.assertEqual((loop["id"], loop["primitive"]), ("loop", "systemd user timer"))
        session_only = [prim("/loop", "loop", rank=0)]
        loop = select_for("superpowers", None, session_only, outlive=True)["strategies"][0]
        self.assertIn("dies with the session", loop["reason"])


if __name__ == "__main__":
    unittest.main()
