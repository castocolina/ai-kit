"""Unit tests for the install wizard view (tools/wizard_app.py).

The wizard is a faithful port of docs/wizard-redesign/prototypes/mockup-textual.py.
TestStructuralFidelity is the anti-divergence net: it encodes the locked
Global Constraints (three separate lane panels, two-list ON/OFF model, every
chip carries its icon, Choose shows components only) as machine checks.  If a
structural test fails, the PORT is wrong — fix the view, never the test.

The Textual runtime requires ``uv run``; plain ``python3`` will not have it, so
every test class is guarded by ``@skipUnless(HAVE_TEXTUAL, ...)``.

Static-content accessor in Textual 8.2.7 is ``str(widget.content)`` (not
``.render()``).
"""
import importlib.util
import threading
import unittest

HAVE_TEXTUAL = importlib.util.find_spec("textual") is not None


def _query_static(app, selector: str):
    from textual.widgets import Static as _Static

    return app.query_one(selector, _Static)

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
                str(_query_static(app, f"#lane{i}").content) for i in range(3))
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
                str(_query_static(app, f"#lane{i}").content) for i in range(3))
            for i in range(3):
                for seg in app.board.lines[i]:
                    icon = app._icon(seg)
                    if icon:
                        self.assertIn(icon, lane_text, f"{seg} missing icon")

    async def test_choose_shows_no_segments_or_externals(self):
        app = wa.WizardApp(make_ctx(with_external=True))
        async with app.run_test() as pilot:
            await pilot.pause()
            box = str(_query_static(app, "#picksbox").content)
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


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestExternal(unittest.IsolatedAsyncioTestCase):
    """External segment distinction + persistence."""

    async def test_external_starts_in_tray(self):
        app = wa.WizardApp(make_ctx(with_external=True, sl_state="ours"))
        self.assertIn("system_memory", app.board.tray)

    async def test_external_toggle_on_persists(self):
        app = wa.WizardApp(make_ctx(with_external=True, sl_state="ours"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange
            app.board.focus_zp = (3, app.board.tray.index("system_memory"))
            await pilot.press("space")
            self.assertNotIn("system_memory", app.board.tray)
            placed = any("system_memory" in ln for ln in app.board.lines)
            self.assertTrue(placed)
            self.assertIs(
                app._serialize_state()["segments"]["system_memory"], True)

    async def test_external_moved_line_wins_over_header_fallback(self):
        # The user drags system_memory's chip off its inventory "home" line
        # onto Line 1 — that explicit arrangement must be written into the
        # persisted layout's row 0, not silently dropped (which would leave
        # only the segment's own header line=/after= fallback in force).
        app = wa.WizardApp(make_ctx(with_external=True, sl_state="ours"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange
            app.board.focus_zp = (3, app.board.tray.index("system_memory"))
            await pilot.press("space")          # tray -> its home line
            home = next(i for i in range(3) if "system_memory" in app.board.lines[i])
            app.board.lines[home].remove("system_memory")
            app.board.lines[0].append("system_memory")
            app.board.focus_zp = (0, len(app.board.lines[0]) - 1)
            st = app._serialize_state()
            self.assertIn("system_memory", st["layout"][0]["segments"])
            for i in range(1, 3):
                self.assertNotIn("system_memory", st["layout"][i]["segments"])

    async def test_external_chip_has_diamond_marker(self):
        app = wa.WizardApp(make_ctx(with_external=True, sl_state="ours"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # render arrange
            await pilot.pause()
            tray_text = str(_query_static(app, "#tray").content)
            self.assertIn("◆", tray_text)
            self.assertIn("system_memory", tray_text)


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestWriteback(unittest.IsolatedAsyncioTestCase):
    """_serialize_state preserves keys; off built-ins stay listed (off-home)."""

    async def test_toggle_builtin_off_keeps_layout_listing(self):
        app = wa.WizardApp(make_ctx(sl_state="ours"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            seg = app.board.lines[0][0]               # a built-in on Line 1 (home 0)
            app.board.focus_zp = (0, 0)
            await pilot.press("space")          # → tray (off)
            st = app._serialize_state()
            self.assertIs(st["segments"][seg], False)
            # not in any row's ON portion, but still listed via off-home
            self.assertIn(seg, st["layout"][0]["segments"])
            # every original segment key survives
            self.assertEqual(set(st["segments"]), set(app.model.state["segments"]))


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestReviewDone(unittest.IsolatedAsyncioTestCase):
    """Review confirm → serialize → WizardResult → Done."""

    async def test_arrange_enter_to_review(self):
        app = wa.WizardApp(make_ctx(sl_state="ours"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange
            await pilot.press("enter")          # arrange → review
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)

    async def test_review_enter_commits_and_done(self):
        app = wa.WizardApp(make_ctx(sl_state="unset"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange
            await pilot.press("y")              # gate: adopt
            await pilot.press("enter")          # arrange → review
            await pilot.press("enter")          # review → commit
            self.assertEqual(app.flow.step, wa.STEP_DONE)
            result = app.flow.result
            self.assertIsInstance(result, wa.WizardResult)
            assert result is not None
            self.assertIs(result.state["claude"]["adopt"], True)

    async def test_q_before_confirm_leaves_no_result(self):
        app = wa.WizardApp(make_ctx(sl_state="ours"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange
            await pilot.press("q")              # abort
        self.assertIsNone(app.flow.result)

    async def test_review_enter_no_change_blocks(self):
        app = wa.WizardApp(make_ctx(sl_state="unset"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("N")              # all components off == initial
            await pilot.press("enter")          # choose → arrange (gate)
            await pilot.press("n")              # decline → jumps to Review
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            await pilot.press("enter")          # review → blocked (no net change)
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            self.assertIn("Nothing to write",
                          str(_query_static(app, "#cta").content))

    async def test_decline_omits_status_line_on_review_and_done(self):
        app = wa.WizardApp(make_ctx(sl_state="foreign"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange (gate)
            await pilot.press("n")              # decline → Review (arrange skipped)
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            # status-line preview panel is hidden; CTA & "what" omit segments
            self.assertFalse(_query_static(app, "#rev-preview").display)
            self.assertNotIn("segments", str(_query_static(app, "#cta").content))
            self.assertIn("left unchanged",
                          str(_query_static(app, "#rev-what").content))
            await pilot.press("enter")          # commit (components are a net change)
            self.assertEqual(app.flow.step, wa.STEP_DONE)
            result = app.flow.result
            assert result is not None
            self.assertIs(result.state["claude"]["adopt"], False)
            sub = str(_query_static(app, "#step-sub").content)
            self.assertNotIn("status line is ready", sub)
            self.assertNotIn("segments", sub)
            self.assertIn("left unchanged", sub)

    async def test_review_counts_components_without_hooks(self):
        ctx = make_ctx()
        ctx.selection.items.append(("hooks", "tool-advisor", True))
        ctx.state["_initial_enabled"][("hooks", "tool-advisor")] = False
        ctx.component_meta["tool-advisor"] = "Advisor description"
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.press("y")
            await pilot.press("enter")
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            self.assertIn("3[/] components", str(_query_static(app, "#rev-what").content))
            self.assertIn("3 components", str(_query_static(app, "#cta").content))

    async def test_accept_shows_status_line_on_review(self):
        app = wa.WizardApp(make_ctx(sl_state="unset"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange (gate)
            await pilot.press("y")              # accept
            await pilot.press("enter")          # arrange → review
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            self.assertTrue(_query_static(app, "#rev-preview").display)
            self.assertIn("segments", str(_query_static(app, "#cta").content))


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestInUICommit(unittest.IsolatedAsyncioTestCase):
    """Review-confirm runs the injected commit IN-UI (worker), and the Done screen
    reflects the real outcome."""

    async def _confirm(self, commit, *, accept=True, sl_state="unset"):
        """Drive Choose→gate→(board)→Review→confirm, wait for the commit worker,
        and return a snapshot dict (widgets only live inside run_test)."""
        ctx = make_ctx(sl_state=sl_state)._replace(commit=commit)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")              # choose → arrange (gate)
            await pilot.press("y" if accept else "n")
            if accept:
                await pilot.press("enter")          # arrange → review
            await pilot.press("enter")              # review → commit
            await app.workers.wait_for_complete()   # let the worker finish
            await pilot.pause()
            return {
                "step": app.flow.step,
                "committing": app.commit.committing,
                "outcome": app.commit.outcome,
                "result": app.flow.result,
                "sel": app.model.sel,
                "art": str(_query_static(app, "#done-art").content),
                "next": str(_query_static(app, "#done-next").content),
                "title": str(_query_static(app, "#step-title").content),
                "sub": str(_query_static(app, "#step-sub").content),
            }

    async def test_commit_invoked_with_host_keyed_states(self):
        """The commit payload is the host-keyed WizardResult.state: each host's
        own segments/layout/adopt, with the component-level outcome shape
        ({"ok", "adopt", "log"}) kept for the single-host caller."""
        seen = {}

        def commit(selection, states):
            seen["selection"] = selection
            seen["states"] = states
            return {"ok": True, "adopt": states["claude"]["adopt"], "log": ""}

        snap = await self._confirm(commit, accept=True)
        self.assertIs(seen["selection"], snap["sel"])
        self.assertEqual(list(seen["states"]), ["claude"])   # one host, keyed by id
        self.assertIs(seen["states"]["claude"]["adopt"], True)     # accepted at gate
        self.assertIn("segments", seen["states"]["claude"])
        self.assertIn("layout", seen["states"]["claude"])
        self.assertEqual(snap["step"], wa.STEP_DONE)
        self.assertFalse(snap["committing"])

    async def test_success_outcome_shows_success_done(self):
        snap = await self._confirm(
            lambda s, st: {"ok": True, "adopt": True, "log": "",
                           "hosts": {"claude": {"ok": True, "adopt": True,
                                                "log": ""}}}, accept=True)
        self.assertIs(snap["result"].state["claude"]["_commit_ok"], True)
        self.assertIn("─kit", snap["art"])              # success art, not "Installing…"
        self.assertIn("your status line is ready", snap["sub"])

    async def test_failure_outcome_shows_failure_done_with_reason(self):
        snap = await self._confirm(
            lambda s, st: {"ok": False, "adopt": True,
                           "log": "unknown [git] key: worktree",
                           "hosts": {"claude": {"ok": False, "adopt": True,
                                                "log": "unknown [git] key: worktree"}}},
            accept=True)
        self.assertIs(snap["result"].state["claude"]["_commit_ok"], False)
        self.assertIn("incomplete", snap["title"])
        self.assertIn("some settings could not be written", snap["next"])
        self.assertIn("worktree", snap["next"])         # the doctor reason, escaped

    async def test_hook_only_failure_done_wording(self):
        snap = await self._confirm(
            lambda s, st: {"ok": False, "adopt": False,
                           "log": "refused hooks.PreToolUse"}, accept=True)
        self.assertIn("some settings could not be written", snap["next"])
        self.assertIn("PreToolUse", snap["next"])
        self.assertNotIn("status line could not", snap["next"] + snap["sub"])

    async def test_decline_still_commits_in_ui(self):
        seen = {}

        def commit(selection, states):
            seen["adopt"] = states["claude"]["adopt"]
            return {"ok": True, "adopt": states["claude"]["adopt"], "log": ""}

        snap = await self._confirm(commit, accept=False, sl_state="foreign")
        self.assertIs(seen["adopt"], False)             # declined at the gate
        self.assertEqual(snap["step"], wa.STEP_DONE)
        self.assertIs(snap["result"].state["claude"]["_commit_ok"], True)

    async def test_no_commit_injected_falls_back_to_legacy(self):
        # make_ctx leaves commit=None → old behavior: result set, Done shown,
        # no worker / outcome.
        app = wa.WizardApp(make_ctx(sl_state="unset"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.press("y")
            await pilot.press("enter")
            await pilot.press("enter")
            await pilot.pause()
            self.assertEqual(app.flow.step, wa.STEP_DONE)
            self.assertIsInstance(app.flow.result, wa.WizardResult)
            self.assertIsNone(app.commit.outcome)
            self.assertFalse(app.commit.committing)


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestChrome(unittest.IsolatedAsyncioTestCase):
    """Header pips + footer key bar."""

    async def test_header_three_pips(self):
        app = wa.WizardApp(make_ctx())
        async with app.run_test() as pilot:
            await pilot.pause()
            right = str(_query_static(app, "#header-right").content)
            self.assertEqual(right.count("●") + right.count("○"), 3)

    async def test_done_header_all_green(self):
        app = wa.WizardApp(make_ctx())
        async with app.run_test() as pilot:
            app.flow.step = wa.STEP_DONE
            app._render()
            await pilot.pause()
            right = str(_query_static(app, "#header-right").content)
            self.assertEqual(right.count("●"), 3)
            self.assertIn(wa.GREEN, right)

    async def test_footer_matches_step(self):
        app = wa.WizardApp(make_ctx())
        async with app.run_test() as pilot:
            await pilot.pause()
            left = str(_query_static(app, "#footer-left").content)
            for _label, cap, _primary in wa.FOOTERS[wa.STEP_CHOOSE]:
                self.assertIn(cap, left)


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestHousekeepingGate(unittest.IsolatedAsyncioTestCase):
    def _ctx(self, **housekeeping):
        hk = {"stale": [], "predecessors": [], **housekeeping}
        return make_ctx()._replace(housekeeping=hk)

    async def test_no_candidates_skips_gate(self):
        app = wa.WizardApp(self._ctx())
        self.assertTrue(app.hk.done)
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertIn("of", str(_query_static(app, "#picksCount").content))

    async def test_stale_only_prune_on_yes(self):
        seen = {}
        def apply_hk(prune, repoint):
            seen["prune"], seen["repoint"] = prune, repoint
            return {"selection": None, "initial_enabled": {}}
        ctx = self._ctx(stale=["skills/gone"])._replace(apply_housekeeping=apply_hk)
        app = wa.WizardApp(ctx)
        self.assertFalse(app.hk.done)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("y")
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertTrue(app.hk.done)
        self.assertEqual(seen["prune"], True)

    async def test_stale_then_predecessors_sequenced(self):
        seen = {}
        def apply_hk(prune, repoint):
            seen["prune"], seen["repoint"] = prune, repoint
            return {"selection": None, "initial_enabled": {}}
        ctx = self._ctx(stale=["skills/gone"], predecessors=["skills/alpha"]
                        )._replace(apply_housekeeping=apply_hk)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertFalse(app.hk.done)
            await pilot.press("n")               # stale: decline prune
            self.assertFalse(app.hk.done)   # predecessors still pending
            await pilot.press("y")               # predecessors: repoint
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertTrue(app.hk.done)
        self.assertEqual(seen["prune"], False)
        self.assertEqual(seen["repoint"], True)

    async def test_replace_yes(self):
        seen = {}
        def apply_hk(prune, repoint, replace=False):
            seen["replace"] = replace
            return {"selection": None, "initial_enabled": {}}
        ctx = self._ctx(replace=["skills/alpha (claude)"])._replace(
            apply_housekeeping=apply_hk)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            gate = str(_query_static(app, "#picksbox").content)
            await pilot.press("y")
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertTrue(app.hk.done)
        self.assertIn("hold a real directory or a foreign link", gate)
        self.assertTrue(seen["replace"])

    async def test_replace_enter_defaults_no(self):
        seen = {}
        def apply_hk(prune, repoint, replace=False):
            seen["replace"] = replace
            return {"selection": None, "initial_enabled": {}}
        ctx = self._ctx(replace=["skills/alpha (claude)"])._replace(
            apply_housekeeping=apply_hk)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")        # default: leave them alone
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertTrue(app.hk.done)
        self.assertFalse(seen["replace"])

    async def test_replace_n_declines(self):
        seen = {}
        def apply_hk(prune, repoint, replace=False):
            seen["replace"] = replace
            return {"selection": None, "initial_enabled": {}}
        ctx = self._ctx(replace=["skills/alpha (claude)"])._replace(
            apply_housekeeping=apply_hk)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("n")
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertTrue(app.hk.done)
        self.assertFalse(seen["replace"])

    async def test_stale_predecessors_replace_sequenced(self):
        seen = {}
        def apply_hk(prune, repoint, replace=False):
            seen["prune"], seen["repoint"], seen["replace"] = prune, repoint, replace
            return {"selection": None, "initial_enabled": {}}
        ctx = self._ctx(stale=["skills/gone"], predecessors=["skills/alpha"],
                        replace=["skills/beta (claude)"])._replace(
            apply_housekeeping=apply_hk)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("n")               # stale: decline prune
            self.assertFalse(app.hk.done)
            await pilot.press("enter")           # predecessors: default repoint
            self.assertFalse(app.hk.done)        # replace still pending
            gate = str(_query_static(app, "#picksbox").content)
            self.assertIn("hold a real directory or a foreign link", gate)
            await pilot.press("y")               # replace: back up and link
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertTrue(app.hk.done)
        self.assertEqual(seen, {"prune": False, "repoint": True, "replace": True})

    async def test_apply_housekeeping_none_falls_back_to_legacy(self):
        # apply_housekeeping=None (unit fixtures without it) -> pressing an
        # answer still resolves the gate using the existing selection/state.
        ctx = self._ctx(stale=["skills/gone"])
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("y")
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertTrue(app.hk.done)

    async def test_apply_housekeeping_raises_resolves_gate(self):
        # apply_housekeeping raising must not leave the wizard stuck showing
        # "Applying…" forever — the gate resolves and the failure is captured,
        # not swallowed into a hang or an unhandled exception.
        def apply_hk(prune, repoint):
            raise OSError("disk exploded")

        ctx = self._ctx(stale=["skills/gone"])._replace(apply_housekeeping=apply_hk)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("y")
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertTrue(app.hk.done)   # gate resolved, no hang
        self.assertFalse(app.hk.applying)
        hk_error = app.hk.error
        assert hk_error is not None
        self.assertIn("disk exploded", hk_error)

    async def test_second_keypress_during_apply_is_noop(self):
        # A keypress that arrives while the apply worker is still in flight
        # (hk.applying=True) must not re-enter _key_housekeeping's
        # self.hk.pending[self.hk.stage] indexing — by the time the last
        # pending answer is recorded, self.hk.stage == len(self.hk.pending),
        # so an unguarded second read raises IndexError.
        release = threading.Event()
        seen = {"calls": 0}

        def apply_hk(prune, repoint):
            seen["calls"] += 1
            release.wait(timeout=2)   # held open until the test releases it
            return {"selection": None, "initial_enabled": {}}

        ctx = self._ctx(stale=["skills/gone"])._replace(apply_housekeeping=apply_hk)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("y")             # kicks off the apply worker
            self.assertTrue(app.hk.applying)  # still in flight (blocked on release)
            await pilot.press("y")             # arrives mid-flight; must be a no-op
            self.assertEqual(seen["calls"], 1)   # guard swallowed the second keypress
            release.set()
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertTrue(app.hk.done)
        self.assertEqual(seen["calls"], 1)



@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestHostTraversal(unittest.IsolatedAsyncioTestCase):
    """Task 1's seam contract: the flow walks detected hosts, one gate each,
    and serializes every host's state before any commit (plan 23-16)."""

    TWO = ("claude", "cursor")

    async def _walk(self, app, pilot, answers=("y", "y")):
        await pilot.pause()
        await pilot.press("enter")                  # choose → first host gate
        for i, ans in enumerate(answers):
            await pilot.press(ans)                  # this host's gate
            if app.flow.step == wa.STEP_ARRANGE:    # accepted → arrange the board
                await pilot.press("enter")          # board → next host / review
            del i
        return app.flow.step

    async def test_two_hosts_walk_gate_gate_review(self):
        app = wa.WizardApp(make_ctx(host_ids=self.TWO, sl_state="unset"))
        async with app.run_test() as pilot:
            step = await self._walk(app, pilot, ("y", "y"))
            self.assertEqual(step, wa.STEP_REVIEW)
            self.assertEqual([h.id for h in app.hosts], ["claude", "cursor"])
            # Both hosts answered their OWN gate.
            self.assertTrue(all(app.views[h.id].answered for h in app.hosts))

    async def test_decline_first_host_still_shows_second_gate(self):
        app = wa.WizardApp(make_ctx(host_ids=self.TWO, sl_state="unset"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")              # claude gate
            await pilot.press("n")                  # decline claude → cursor gate
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)
            self.assertFalse(app.flow.gate_done)    # the SECOND host must be asked
            self.assertEqual(app.flow.host_index, 1)
            lane0 = str(_query_static(app, "#lane0").content)
            self.assertIn("Cursor", lane0)          # cursor's wording, not Claude's

    async def test_review_serializes_both_hosts(self):
        seen = {}

        def commit(selection, states):
            seen["states"] = states
            return {"ok": True, "adopt": True, "log": "",
                    "hosts": {h: {"ok": True, "adopt": True, "log": ""}
                              for h in states}}

        ctx = make_ctx(host_ids=self.TWO, sl_state="unset")._replace(commit=commit)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._walk(app, pilot, ("y", "y"))
            await pilot.press("enter")              # review → commit
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertEqual(sorted(seen["states"]), ["claude", "cursor"])
        for host_id, st in seen["states"].items():
            self.assertIs(st["adopt"], True, host_id)
            self.assertEqual(len(st["layout"]), 3, host_id)
            self.assertTrue(st["segments"], host_id)
        result = app.flow.result
        assert result is not None            # narrowing for the typed seam below
        self.assertEqual(sorted(result.state), ["claude", "cursor"])

    async def test_review_escape_returns_to_last_adopted_host_board(self):
        app = wa.WizardApp(make_ctx(host_ids=self.TWO, sl_state="unset"))
        async with app.run_test() as pilot:
            await self._walk(app, pilot, ("y", "y"))
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            await pilot.press("escape")
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)
            self.assertEqual(app.flow.host_index, 1)              # the LAST adopted host
            self.assertTrue(app.flow.gate_done)          # its board, not its gate

    async def test_reedit_second_host_then_confirm_keeps_both(self):
        seen = {}

        def commit(selection, states):
            seen["states"] = states
            return {"ok": True, "adopt": True, "log": "",
                    "hosts": {h: {"ok": True, "adopt": True, "log": ""}
                              for h in states}}

        ctx = make_ctx(host_ids=self.TWO, sl_state="unset")._replace(commit=commit)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._walk(app, pilot, ("y", "y"))
            await pilot.press("escape")             # back to Cursor's board
            first = app.board.lines[0][0]
            app.board.focus_zp = (0, 0)
            await pilot.press("space")              # move it off → tray
            await pilot.press("enter")              # cursor board → review
            await pilot.press("enter")              # confirm
            await app.workers.wait_for_complete()
            await pilot.pause()
        claude = seen["states"]["claude"]
        self.assertIs(claude["adopt"], True)
        self.assertIs(claude["segments"][first], True)     # untouched by the re-edit
        cursor = seen["states"]["cursor"]
        self.assertIs(cursor["segments"][first], False)    # turned off here only
        # An OFF segment still rides its home row (so `<id> = false` is written),
        # which is why on/off — not placement — is what differs per host.
        self.assertIn(first, [x for row in cursor["layout"] for x in row["segments"]])

    async def test_one_host_failure_shows_its_own_text_only(self):
        def commit(selection, states):
            return {"ok": False, "adopt": True, "log": "claude broke\ncursor fine",
                    "hosts": {"claude": {"ok": False, "adopt": True,
                                         "log": "claude broke"},
                              "cursor": {"ok": True, "adopt": True, "log": ""}}}

        ctx = make_ctx(host_ids=self.TWO, sl_state="unset")._replace(commit=commit)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._walk(app, pilot, ("y", "y"))
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            await pilot.pause()
            nxt = str(_query_static(app, "#done-next").content)
            title = str(_query_static(app, "#step-title").content)
            sub = str(_query_static(app, "#step-sub").content)
        self.assertIn("incomplete", title)
        self.assertIn("claude broke", nxt)          # the failing host's own reason
        # The healthy host's outcome stays visible and its per-host ok holds.
        result = app.flow.result
        assert result is not None            # narrowing for the typed seam below
        self.assertIs(result.state["cursor"]["_commit_ok"], True)
        self.assertIs(result.state["claude"]["_commit_ok"], False)
        self.assertIn("cursor", (nxt + sub).lower())
        self.assertIn("Cursor CLI", nxt + sub)

    async def test_escape_on_later_host_board_returns_to_previous_board(self):
        """D-22: Esc on the Cursor board returns to the Claude board with its
        own arrangement intact (nothing was reset by walking forward)."""
        app = wa.WizardApp(make_ctx(host_ids=self.TWO, sl_state="unset"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")                  # choose → Claude's gate
            await pilot.press("y")                      # adopt → Claude's board
            await pilot.press("enter")                  # board → Cursor's gate
            await pilot.press("y")                      # adopt → Cursor's board
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)
            self.assertEqual(app.flow.host_index, 1)
            claude_first = app.views["claude"].board.lines[0][0]
            cursor_first = app.board.lines[0][0]
            app.board.focus_zp = (0, 0)
            await pilot.press("space")               # re-arrange Cursor only
            self.assertIn(cursor_first, app.board.tray)
            await pilot.press("escape")              # back to Claude's board
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)
            self.assertEqual(app.flow.host_index, 0)
            self.assertTrue(app.flow.gate_done)      # its board, not its gate
            self.assertIn(claude_first, app.board.lines[0])   # arrangement intact

    async def test_declining_second_host_lists_it_untouched_on_review(self):
        seen = {}

        def commit(selection, states):
            seen["states"] = states
            return {"ok": True, "adopt": True, "log": "",
                    "hosts": {h: {"ok": True, "adopt": st["adopt"], "log": ""}
                              for h, st in states.items()}}

        ctx = make_ctx(host_ids=self.TWO, sl_state="unset")._replace(commit=commit)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._walk(app, pilot, ("y", "n"))   # Claude adopts, Cursor declines
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            what = str(_query_static(app, "#rev-what").content)
            self.assertIn("Cursor CLI: left untouched", what)
            await pilot.press("enter")                 # confirm
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertIs(seen["states"]["cursor"]["adopt"], False)
        result = app.flow.result
        assert result is not None
        self.assertIs(result.state["cursor"]["adopt"], False)

    async def test_review_lists_each_adopted_hosts_config_and_wiring(self):
        app = wa.WizardApp(make_ctx(host_ids=self.TWO, sl_state="unset"))
        async with app.run_test() as pilot:
            await self._walk(app, pilot, ("y", "y"))
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            what = str(_query_static(app, "#rev-what").content)
            self.assertIn("Claude Code: write ~/.config/ai-kit/claude-statusline.toml "
                          "+ wire settings.json", what)
            self.assertIn("Cursor CLI: write ~/.config/ai-kit/cursor-statusline.toml "
                          "+ wire cli-config.json", what)

    async def test_cursor_failure_shown_on_done_while_claude_succeeds(self):
        def commit(selection, states):
            return {"ok": False, "adopt": True, "log": "",
                    "hosts": {"claude": {"ok": True, "adopt": True, "log": ""},
                              "cursor": {"ok": False, "adopt": True,
                                         "log": "cursor doctor refused"}}}

        ctx = make_ctx(host_ids=self.TWO, sl_state="unset")._replace(commit=commit)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._walk(app, pilot, ("y", "y"))
            await pilot.press("enter")                  # review → commit
            await app.workers.wait_for_complete()
            await pilot.pause()
            nxt = str(_query_static(app, "#done-next").content)
            title = str(_query_static(app, "#step-title").content)
        self.assertIn("incomplete", title)
        self.assertIn("Cursor CLI:", nxt)               # the failing host names itself
        self.assertIn("cursor doctor refused", nxt)
        self.assertIn("written OK:", nxt)               # the healthy host stays visible
        self.assertIn("Claude Code", nxt)
        result = app.flow.result
        assert result is not None
        self.assertIs(result.state["cursor"]["_commit_ok"], False)
        self.assertIs(result.state["claude"]["_commit_ok"], True)

    async def test_one_host_titles_are_host_labelled(self):
        """The formerly Claude-only strings are host-labelled (D-22): the Arrange
        title and the gate prompt name the host even in a one-host context."""
        app = wa.WizardApp(make_ctx(host_ids=("claude",), sl_state="unset"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")                  # choose → Claude's gate
            lane0 = str(_query_static(app, "#lane0").content)
            self.assertIn("Wire your Claude Code status line?", lane0)
            await pilot.press("y")                      # accept → the board
            await pilot.pause()
            title = str(_query_static(app, "#step-title").content)
            self.assertIn("Arrange your Claude Code status line", title)

    async def test_zero_hosts_skips_arrange_entirely(self):
        seen = {}

        def commit(selection, states):
            seen["states"] = states
            return {"ok": True, "adopt": False, "log": "", "hosts": {}}

        ctx = make_ctx(host_ids=())._replace(commit=commit)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")              # choose → review (no arrange)
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            self.assertFalse(_query_static(app, "#rev-preview").display)
            what = str(_query_static(app, "#rev-what").content)
            self.assertIn("No status-line host detected", what)
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertEqual(seen["states"], {})        # empty dict, no Claude fallback
        result = app.flow.result
        assert result is not None            # narrowing for the typed seam below
        self.assertEqual(result.state, {})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
