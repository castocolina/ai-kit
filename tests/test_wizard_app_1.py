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
    from tests.wizard_fixtures import make_ctx, make_ctx_kinds


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestStructuralFidelity(unittest.IsolatedAsyncioTestCase):
    """Anti-divergence net — the locked Global Constraints as machine checks."""

    async def test_arrange_has_three_separate_lane_panels(self):
        app = wa.WizardApp(make_ctx())
        async with app.run_test() as pilot:
            app.flow.step = wa.STEP_ARRANGE
            app._render()
            await pilot.pause()
            for wid in ("#lane0", "#lane1", "#lane2", "#focchip", "#tray", "#preview"):
                self.assertEqual(len(app.query(wid)), 1, f"missing {wid}")

    async def test_off_segment_never_appears_in_a_lane(self):
        app = wa.WizardApp(make_ctx())
        async with app.run_test() as pilot:
            app.flow.step = wa.STEP_ARRANGE
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
class TestChooseTabs(unittest.IsolatedAsyncioTestCase):
    """Choose (step 0): one tab per kind that has items, one card on screen (D-01, D-02)."""

    def _tabs(self, app):
        return str(query_static(app, "#kind-tabs").content)

    async def test_tab_row_counts_and_no_commands_tab(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test() as pilot:
            await pilot.pause()
            tabs = self._tabs(app)
            self.assertIn("skills 3/3", tabs)
            self.assertIn("agents 1/1", tabs)
            self.assertIn("hooks 1/2", tabs)
            self.assertNotIn("commands", tabs)
            self.assertIn("skills 3/3", str(query_static(app, "#picksbox").border_title))

    async def test_right_wraps_and_left_goes_back(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertEqual(app.flow.kind, "skills")
            await pilot.press("right")
            self.assertEqual(app.flow.kind, "agents")
            await pilot.press("right")
            self.assertEqual(app.flow.kind, "hooks")
            await pilot.press("right")          # past the last tab wraps to the first
            self.assertEqual(app.flow.kind, "skills")
            await pilot.press("left")           # past the first wraps to the last
            self.assertEqual(app.flow.kind, "hooks")

    async def test_down_wraps_inside_card_and_each_tab_keeps_its_cursor(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("down")
            self.assertEqual(app.model.sel.cursor, 1)
            await pilot.press("down")
            await pilot.press("down")           # three skills: wraps to the first
            self.assertEqual(app.model.sel.cursor, 0)
            await pilot.press("down")
            await pilot.press("right")          # agents: its own cursor
            self.assertEqual(app.model.sel.items[app.model.sel.cursor][0], "agents")
            await pilot.press("left")           # back to skills: cursor 1 remembered
            self.assertEqual(app.model.sel.cursor, 1)

    async def test_space_changes_only_its_card_and_review_counts(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("right")
            await pilot.press("right")          # hooks; cursor on tool-advisor
            await pilot.press("down")           # rtk-hint (off)
            await pilot.press("space")
            tabs = self._tabs(app)
            self.assertIn("hooks 2/2", tabs)
            self.assertIn("skills 3/3", tabs)
            self.assertIn("agents 1/1", tabs)
            rows, _ncomp = app._review_component_rows()
            self.assertTrue(any("2/2: tool-advisor, rtk-hint" in row for row in rows), rows)

    async def test_n_and_upper_n_and_upper_a(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("right")          # agents, one item
            await pilot.press("n")
            self.assertEqual(app.model.sel.items[3][2], False)
            self.assertIn("skills 3/3", self._tabs(app))
            self.assertIn("hooks 1/2", self._tabs(app))
            await pilot.press("N")
            self.assertTrue(all(not on for _c, _n, on in app.model.sel.items))
            await pilot.press("A")
            self.assertTrue(all(on for _c, _n, on in app.model.sel.items))

    async def test_one_kind_catalog_has_one_tab_and_arrows_do_nothing(self):
        app = wa.WizardApp(make_ctx_kinds(items=[("skills", "brainstorming", True)]))
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertIn("skills 1/1", self._tabs(app))
            await pilot.press("right")
            await pilot.press("left")
            self.assertEqual(app.flow.kind, "skills")

    async def test_empty_catalog_shows_nothing_to_install_and_enter_leaves(self):
        app = wa.WizardApp(make_ctx_kinds(items=[]))
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertIn("nothing to install", str(query_static(app, "#picksbox").content))
            await pilot.press("enter")
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)

    async def test_tab_is_noop(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("tab")
            self.assertEqual(app.flow.step, wa.STEP_CHOOSE)

    async def test_enter_advances_to_arrange(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)

    async def test_twenty_five_skills_scroll_to_the_last_item(self):
        items = [("skills", f"skill-{i:02d}", True) for i in range(25)]
        app = wa.WizardApp(make_ctx_kinds(items=items))
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            scroll = app.query_one("#step-choose")
            self.assertGreater(scroll.max_scroll_y, 0)
            await pilot.press("up")             # wraps to the last skill
            await pilot.pause()
            self.assertGreater(scroll.scroll_y, 0)

    async def test_wide_descriptions_keep_one_row_each(self):
        items = [("skills", f"skill-{i:02d}", True) for i in range(25)]
        wide = "説明😀" * 20                     # East Asian and emoji cells, far past 80 columns
        ctx = make_ctx_kinds(items=items)._replace(
            component_meta={f"skill-{i:02d}": wide for i in range(25)})
        app = wa.WizardApp(ctx)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            self.assertEqual(query_static(app, "#picksbox").content_size.height, 25)


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestToggleStart(unittest.IsolatedAsyncioTestCase):
    """The band toggle's start state on Arrange entry (plan 30.1-05: no yes/no gate)."""

    async def test_unset_starts_off_and_o_turns_it_on(self):
        app = wa.WizardApp(make_ctx(sl_state="unset"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange (no gate)
            self.assertIs(app.model.state["adopt"], False)
            await pilot.press("o")
            self.assertIs(app.model.state["adopt"], True)
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)

    async def test_foreign_starts_at_keep_and_enter_goes_on(self):
        app = wa.WizardApp(make_ctx(sl_state="foreign"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange
            self.assertIs(app.model.state["adopt"], False)
            self.assertEqual(app.model.state["foreign_choice"], "keep")
            await pilot.press("enter")          # every pane is visited: one host, so Review
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)

    async def test_o_cycles_foreign_keep_remove_custom(self):
        app = wa.WizardApp(make_ctx(sl_state="foreign"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange
            await pilot.press("o")
            self.assertEqual(app.model.state["foreign_choice"], "remove")
            self.assertIs(app.model.state["adopt"], False)
            await pilot.press("o")
            self.assertEqual(app.model.state["foreign_choice"], "custom")
            self.assertIs(app.model.state["adopt"], True)
            await pilot.press("o")
            self.assertEqual(app.model.state["foreign_choice"], "keep")
            self.assertIs(app.model.state["adopt"], False)

    async def test_arrange_escape_returns_to_choose(self):
        app = wa.WizardApp(make_ctx(sl_state="foreign"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange
            await pilot.press("escape")         # first host's pane backs out to Choose
            self.assertEqual(app.flow.step, wa.STEP_CHOOSE)

    async def test_review_escape_returns_to_last_host_pane(self):
        app = wa.WizardApp(make_ctx(sl_state="foreign"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange
            await pilot.press("enter")          # → Review
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            await pilot.press("escape")         # back from Review to the host's pane
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)

    async def test_ours_starts_on(self):
        app = wa.WizardApp(make_ctx(sl_state="ours"))
        self.assertIs(app.model.state["adopt"], True)
        self.assertEqual(app.model.state["start_state"], "ours")

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
