"""Install wizard view tests (tools/wizard_app.py), part 1 of 3.

Covers structural fidelity, Choose, the adoption gate and Arrange moves.

The wizard is a faithful port of docs/wizard-redesign/prototypes/mockup-textual.py. The three
parts run in parallel; the Textual guard and the Static helper live in
tests/wizard_app_common.py.

TestStructuralFidelity is the anti-divergence net: it encodes the locked
Global Constraints (three separate lane panels, two-list ON/OFF model, every
chip carries its icon, Choose shows components only) as machine checks.  If a
structural test fails, the PORT is wrong — fix the view, never the test.
"""
import unittest

from tests.wizard_app_common import HAVE_TEXTUAL, query_static
from tools import wizard_app as wa

if HAVE_TEXTUAL:
    from tests.wizard_fixtures import make_ctx


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestStructuralFidelity(unittest.IsolatedAsyncioTestCase):
    """Anti-divergence net — the locked Global Constraints as machine checks."""

    async def test_arrange_has_three_separate_lane_panels(self):
        app = wa.WizardApp(make_ctx())
        async with app.run_test() as pilot:
            app.flow.step = wa.STEP_ARRANGE
            app.flow.gate_done = True
            app._render()
            await pilot.pause()
            for wid in ("#lane0", "#lane1", "#lane2", "#focchip", "#tray", "#preview"):
                self.assertEqual(len(app.query(wid)), 1, f"missing {wid}")

    async def test_off_segment_never_appears_in_a_lane(self):
        app = wa.WizardApp(make_ctx())
        async with app.run_test() as pilot:
            app.flow.step = wa.STEP_ARRANGE
            app.flow.gate_done = True
            app._render()
            await pilot.pause()
            lane_text = " ".join(
                str(query_static(app, f"#lane{i}").content) for i in range(3))
            for seg in app.board.tray:
                self.assertNotIn(seg, lane_text,
                                 f"OFF segment {seg!r} leaked into a lane")

    async def test_every_lane_chip_carries_its_icon(self):
        ctx = make_ctx()
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            app.flow.step = wa.STEP_ARRANGE
            app.flow.gate_done = True
            app._render()
            await pilot.pause()
            lane_text = " ".join(
                str(query_static(app, f"#lane{i}").content) for i in range(3))
            for i in range(3):
                for seg in app.board.lines[i]:
                    icon = app._icon(seg)
                    if icon:
                        self.assertIn(icon, lane_text, f"{seg} missing icon")

    async def test_choose_shows_no_segments_or_externals(self):
        app = wa.WizardApp(make_ctx(with_external=True))
        async with app.run_test() as pilot:
            await pilot.pause()
            box = str(query_static(app, "#picksbox").content)
            for seg in app.model.state["segments"]:
                self.assertNotIn(seg, box, f"segment {seg!r} leaked onto Choose")


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestChoose(unittest.IsolatedAsyncioTestCase):
    """Choose (step 0) drives ctx.selection only."""

    async def test_down_up_wrap_cursor(self):
        app = wa.WizardApp(make_ctx())
        n = len(app.model.sel.items)
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertEqual(app.model.sel.cursor, 0)
            await pilot.press("up")            # wrap to last
            self.assertEqual(app.model.sel.cursor, n - 1)
            await pilot.press("down")          # wrap back to first
            self.assertEqual(app.model.sel.cursor, 0)

    async def test_space_toggles_cursor_item(self):
        app = wa.WizardApp(make_ctx())
        before = app.model.sel.items[0][2]
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("space")
        self.assertEqual(app.model.sel.items[0][2], not before)

    async def test_a_n_set_cursor_category(self):
        app = wa.WizardApp(make_ctx())  # cursor 0 → category "agents" (2 items)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("n")
            agents = [it for it in app.model.sel.items if it[0] == "agents"]
            self.assertTrue(all(not it[2] for it in agents))
            # other categories untouched
            self.assertTrue(app.model.sel.items[2][2])  # commands/code-review still on
            await pilot.press("a")
            self.assertTrue(all(it[2] for it in agents))

    async def test_upper_a_n_set_all(self):
        app = wa.WizardApp(make_ctx())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("N")
            self.assertTrue(all(not it[2] for it in app.model.sel.items))
            await pilot.press("A")
            self.assertTrue(all(it[2] for it in app.model.sel.items))

    async def test_tab_is_noop(self):
        app = wa.WizardApp(make_ctx())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("tab")
            self.assertEqual(app.flow.step, wa.STEP_CHOOSE)

    async def test_enter_advances_to_arrange(self):
        app = wa.WizardApp(make_ctx())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestAdoptionGate(unittest.IsolatedAsyncioTestCase):
    """The adoption gate shown on Arrange entry."""

    async def test_unset_enter_adopts(self):
        app = wa.WizardApp(make_ctx(sl_state="unset"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange
            self.assertFalse(app.flow.gate_done)
            await pilot.press("enter")          # answer gate (default Yes)
            self.assertTrue(app.flow.gate_done)
            self.assertIs(app.model.state["adopt"], True)
            # Accepted → stays on the Arrange board (segments to arrange).
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)

    async def test_foreign_enter_declines_and_skips_arrange(self):
        app = wa.WizardApp(make_ctx(sl_state="foreign"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange (gate)
            await pilot.press("enter")          # answer gate (default No for foreign)
            self.assertTrue(app.flow.gate_done)
            self.assertIs(app.model.state["adopt"], False)
            # Declined → segment arrangement is skipped; jump straight to Review.
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)

    async def test_unset_n_declines_and_skips_arrange(self):
        app = wa.WizardApp(make_ctx(sl_state="unset"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange (gate)
            await pilot.press("n")              # decline
            self.assertIs(app.model.state["adopt"], False)
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)

    async def test_y_n_force(self):
        app = wa.WizardApp(make_ctx(sl_state="foreign"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.press("y")
            self.assertIs(app.model.state["adopt"], True)
            self.assertTrue(app.flow.gate_done)
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)   # accepted → board

    async def test_gate_escape_returns_to_choose(self):
        app = wa.WizardApp(make_ctx(sl_state="foreign"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange (gate)
            await pilot.press("escape")         # back out of the gate
            self.assertEqual(app.flow.step, wa.STEP_CHOOSE)
            self.assertFalse(app.flow.gate_done)     # gate re-asks on next entry

    async def test_review_escape_after_decline_returns_to_choose(self):
        app = wa.WizardApp(make_ctx(sl_state="foreign"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange (gate)
            await pilot.press("n")              # decline → Review (arrange skipped)
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            await pilot.press("escape")         # back from Review
            # Arrange was skipped, so Esc returns to Choose, not Arrange.
            self.assertEqual(app.flow.step, wa.STEP_CHOOSE)

    async def test_ours_skips_gate_at_init(self):
        app = wa.WizardApp(make_ctx(sl_state="ours"))
        self.assertTrue(app.flow.gate_done)
        self.assertIs(app.model.state["adopt"], True)

    async def test_ours_at_open_pins_the_shown_command_for_adoption(self):
        # U1: a host already ai-kit's when the wizard opens is adopted without
        # a gate; the exact wiring value the pane shows must be pinned so the
        # commit refuses a foreign command written while the session is open.
        ctx = make_ctx(sl_state="ours")
        host = ctx.hosts[0]._replace(
            status_line=lambda: {"state": "ours",
                                 "current_command": "/usr/bin/mybar-a"})
        ctx = ctx._replace(hosts=(host,))
        app = wa.WizardApp(ctx)
        self.assertIs(app.model.state["adopt"], True)
        self.assertEqual(app.model.state["adopt_command"], "/usr/bin/mybar-a")


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestArrangeMoves(unittest.IsolatedAsyncioTestCase):
    """Chip movement on the board (gate already done via sl_state='ours')."""

    async def _arrange_app(self, **kw):
        app = wa.WizardApp(make_ctx(sl_state="ours", **kw))
        return app

    async def test_space_lane_chip_moves_to_tray(self):
        app = await self._arrange_app()
        seg = app.board.lines[0][0]
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange (gate done)
            app.board.focus_zp = (0, 0)
            await pilot.press("space")
            self.assertIn(seg, app.board.tray)
            self.assertNotIn(seg, app.board.lines[0])
            self.assertIs(app._serialize_state()["segments"][seg], False)

    async def test_space_tray_chip_reactivates_home(self):
        app = await self._arrange_app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            seg = app.board.tray[0]
            home = app.model.home_line.get(seg, 2)
            app.board.focus_zp = (3, 0)
            await pilot.press("space")
            self.assertIn(seg, app.board.lines[home])
            self.assertNotIn(seg, app.board.tray)

    async def test_left_right_reorder(self):
        app = await self._arrange_app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            first, second = app.board.lines[0][0], app.board.lines[0][1]
            app.board.focus_zp = (0, 0)
            await pilot.press("right")
            self.assertEqual(app.board.lines[0][0], second)
            self.assertEqual(app.board.lines[0][1], first)
            await pilot.press("left")
            self.assertEqual(app.board.lines[0][0], first)

    async def test_up_from_line1_to_tray(self):
        app = await self._arrange_app()
        seg = None
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            seg = app.board.lines[0][0]
            app.board.focus_zp = (0, 0)
            await pilot.press("up")             # Line 1 → tray
            self.assertIn(seg, app.board.tray)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
