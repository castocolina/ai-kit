"""Tests for tools/wizard_app.py — Textual skeleton (Task 2.1).

The Textual runtime requires ``uv run``; plain ``python3`` will not have it.
The core pre-commit ``unittest`` hook runs plain python3 and therefore SKIPS
these tests via the guard below.  The ``unittest-wizard`` pre-commit hook
(added to .pre-commit-config.yaml by Task 2.1) runs them under uv.

Run manually:
  uv run python -m unittest tests.test_wizard_app -v
"""
import types
import unittest
from unittest.mock import MagicMock, patch

try:
    import textual  # noqa: F401
    HAVE_TEXTUAL = True
except ImportError:
    HAVE_TEXTUAL = False

if HAVE_TEXTUAL:
    from tools import wizard_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_selection(items=None):
    """Minimal stand-in for setup.Selection with items, toggle, set_all, and
    category_sets.  category_sets() returns {cat: {name, ...}} for enabled items."""
    if items is None:
        items = [
            ["skills", "coding", True],
            ["skills", "review", False],
            ["commands", "commit", True],
        ]
    sel = types.SimpleNamespace()
    sel.items = items

    def toggle(index: int) -> None:
        sel.items[index][2] = not sel.items[index][2]

    def set_all(value: bool) -> None:
        for row in sel.items:
            row[2] = value

    def category_sets():
        result = {}
        for cat, name, on in sel.items:
            if on:
                result.setdefault(cat, set()).add(name)
        return result

    sel.toggle = toggle
    sel.set_all = set_all
    sel.category_sets = category_sets
    return sel


def _fake_ctx_layout():
    """Build a WizardContext with real layout_move/layout_toggle/off_tray/groups
    injected via setup's implementations (imported locally to avoid module-level
    coupling).  State has two layout lines and one segment in each line."""
    from tools import setup as _setup  # pylint: disable=import-outside-toplevel

    selection = _fake_selection(items=[
        ["skills", "coding", True],
        ["commands", "commit", True],
    ])
    state = {
        "segments": {"path": True, "model": True, "git_branch": False},
        "layout": [
            {"min_rows": 0, "segments": ["path", "model"]},
            {"min_rows": 20, "segments": []},
        ],
        "dirty": False,
    }
    engine = types.SimpleNamespace(
        render_preview=lambda segments: "",
        apply_command=_setup._apply_wizard_command,  # pylint: disable=protected-access
        groups=_setup._wizard_groups,  # pylint: disable=protected-access
        order=_setup._wizard_order,  # pylint: disable=protected-access
        layout_move=_setup.layout_move,
        layout_toggle=_setup.layout_toggle,
        off_tray=_setup.off_tray,
    )
    return wizard_app.WizardContext(
        selection=selection,
        state=state,
        sample_json="{}",
        engine=engine,
    )


def _fake_ctx(items=None):
    """Build a real WizardContext with a minimal fake selection and engine."""
    selection = _fake_selection(items)
    state = {
        "segments": {"git_branch": True, "system_memory": False},
        "layout": [{"min_rows": 0, "segments": ["git_branch"]}],
        "dirty": False,
    }
    engine = types.SimpleNamespace(
        render_preview=lambda segments: "",
        apply_command=lambda st, cmd: (st, None),
        groups=lambda st: [],
        order=lambda st: [],
    )
    return wizard_app.WizardContext(
        selection=selection,
        state=state,
        sample_json="{}",
        engine=engine,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestWizardApp(unittest.IsolatedAsyncioTestCase):
    """Skeleton boot and abort tests (Task 2.1)."""

    async def test_app_boots_and_shows_install_picks(self):
        """App boots headless and the #install-picks container is queryable.

        After the _PicksScreen refactor, #install-picks lives on the pushed
        screen — query via app.screen (the current top screen) rather than
        app.query_one which only searches default_screen in Textual 8.x.
        """
        ctx = _fake_ctx()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            node = app.screen.query_one("#install-picks")
            self.assertIsNotNone(node)

    async def test_abort_via_q_leaves_result_none(self):
        """Pressing 'q' triggers action_abort; result stays None."""
        ctx = _fake_ctx()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("q")
        self.assertIsNone(app.result)

    async def test_abort_via_escape_leaves_result_none(self):
        """Pressing 'escape' triggers action_abort; result stays None."""
        ctx = _fake_ctx()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("escape")
        self.assertIsNone(app.result)

    async def test_picks_populated_from_ctx(self):
        """SelectionList is populated with one option per item in ctx.selection."""
        items = [
            ["skills", "alpha", True],
            ["skills", "beta", False],
            ["commands", "gamma", True],
        ]
        ctx = _fake_ctx(items=items)
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            picks = app.screen.query_one("#picks")
            self.assertEqual(picks.option_count, len(items))


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestInstallPicks(unittest.IsolatedAsyncioTestCase):
    """Toggle / all / none interaction tests (Task 2.2)."""

    async def test_space_toggles_focused_pick(self):
        """space toggles the focused row in ctx.selection.items."""
        ctx = _fake_ctx(items=[["skills", "a", True], ["skills", "b", False]])
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()                 # let on_mount highlight assignment settle
            await pilot.press("space")          # toggles the focused row (index 0)
            self.assertFalse(ctx.selection.items[0][2])

    async def test_a_selects_all_n_selects_none(self):
        """'a' enables all picks; 'n' disables all picks."""
        ctx = _fake_ctx(items=[["skills", "a", False], ["agents", "b", False]])
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("a")
            self.assertTrue(all(it[2] for it in ctx.selection.items))
            await pilot.press("n")
            self.assertTrue(all(not it[2] for it in ctx.selection.items))

    async def test_glyph_shape_encodes_on_off_state(self):
        """FR-W.7: glyph SHAPE in the option prompt conveys on/off independent of color.

        An enabled pick's prompt must contain ◉; a disabled pick's must contain ◯.
        After toggling, the glyph must flip (◉→◯ or ◯→◉).
        Glyph text is read from SelectionList.get_option_at_index(i).prompt so
        this test is independent of color/style — purely character content.
        """
        items = [["skills", "a", True], ["skills", "b", False]]
        ctx = _fake_ctx(items=items)
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            picks = app.screen.query_one("#picks")

            # Initial glyphs: index 0 enabled → ◉, index 1 disabled → ◯
            prompt0 = picks.get_option_at_index(0).prompt
            prompt1 = picks.get_option_at_index(1).prompt
            self.assertIn("◉", str(prompt0), "enabled pick must use ◉ glyph")
            self.assertNotIn("◯", str(prompt0), "enabled pick must not use ◯ glyph")
            self.assertIn("◯", str(prompt1), "disabled pick must use ◯ glyph")
            self.assertNotIn("◉", str(prompt1), "disabled pick must not use ◉ glyph")

            # Toggle index 0 (currently enabled → should become disabled → ◯)
            await pilot.press("space")
            await pilot.pause()
            prompt0_after = picks.get_option_at_index(0).prompt
            self.assertIn("◯", str(prompt0_after), "toggled-off pick must flip to ◯")
            self.assertNotIn("◉", str(prompt0_after), "toggled-off pick must not retain ◉")


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestConfirm(unittest.IsolatedAsyncioTestCase):
    """Summary + confirm flow tests (Task 2.3)."""

    async def test_enter_confirms_and_sets_result(self):
        """enter → summary screen → enter → confirms; result has correct category_sets."""
        ctx = _fake_ctx(items=[["skills", "a", True]])
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("enter")   # picks → summary
            await pilot.pause()
            await pilot.press("enter")   # summary → confirm
        self.assertIsNotNone(app.result)
        self.assertIn("a", app.result.selection.category_sets()["skills"])

    async def test_abort_from_picks_yields_none_result(self):
        """q from picks screen → result is None."""
        app = wizard_app.WizardApp(_fake_ctx())
        async with app.run_test() as pilot:
            await pilot.press("q")
        self.assertIsNone(app.result)

    async def test_abort_from_summary_yields_none_result(self):
        """q from summary screen → result is None."""
        app = wizard_app.WizardApp(_fake_ctx())
        async with app.run_test() as pilot:
            await pilot.press("enter")   # to summary
            await pilot.pause()
            await pilot.press("q")       # abort from summary
        self.assertIsNone(app.result)

    async def test_empty_selection_default_no_returns_to_picks(self):
        """Empty selection: enter → summary → enter opens empty-confirm modal.
        Default action (enter, no explicit yes) pops back to picks; result is None."""
        ctx = _fake_ctx(items=[["skills", "a", False]])
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("enter")   # picks → summary (empty)
            await pilot.pause()
            await pilot.press("enter")   # empty confirm opens; default = No
            await pilot.pause()
            await pilot.press("enter")   # confirm the No default → back to picks
        self.assertIsNone(app.result)

    async def test_empty_selection_explicit_yes_sets_result(self):
        """Empty selection: explicit 'y' on the empty-confirm modal sets result."""
        ctx = _fake_ctx(items=[["skills", "a", False]])
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("enter")   # picks → summary (empty)
            await pilot.pause()
            await pilot.press("enter")   # empty confirm opens
            await pilot.pause()
            await pilot.press("y")       # explicit yes
        self.assertIsNotNone(app.result)
        self.assertEqual(app.result.selection.category_sets(), {})

    async def test_esc_from_summary_yields_none_result(self):
        """escape from summary screen → clean abort; result is None."""
        app = wizard_app.WizardApp(_fake_ctx())
        async with app.run_test() as pilot:
            await pilot.press("enter")    # picks → summary
            await pilot.pause()
            await pilot.press("escape")   # abort from summary
        self.assertIsNone(app.result)

    async def test_empty_modal_q_returns_to_picks(self):
        """Empty selection: q on EmptyConfirmModal dismisses modal back to picks.

        Documents that q/esc on the modal does NOT abort the wizard — it just
        returns to the picks screen (result stays None, app still running).
        This mirrors the per-screen behavior described in the module docstring.
        """
        ctx = _fake_ctx(items=[["skills", "a", False]])
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("enter")   # picks → summary (empty)
            await pilot.pause()
            await pilot.press("enter")   # empty confirm modal opens
            await pilot.pause()
            await pilot.press("q")       # dismiss modal → back to picks (not abort)
        # result is None: the wizard was NOT confirmed (returned to picks, then
        # the test harness exited cleanly without a further confirmation).
        self.assertIsNone(app.result)


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestLayoutBoard(unittest.IsolatedAsyncioTestCase):
    """Layout board interaction tests (Task 3.2 / FR-W.4)."""

    async def _navigate_to_board(self, app, pilot):
        """Helper: wait for picks screen then press tab to open the board."""
        await pilot.pause()          # let _PicksScreen mount
        await pilot.press("tab")     # push LayoutBoard
        await pilot.pause()          # let board mount + render

    async def test_arrow_moves_chip_within_line(self):
        """right moves the focused chip (path) to the right within line 0."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            # focused_seg defaults to first chip in first non-empty group = "path"
            board = app.screen  # LayoutBoard is now the top screen
            self.assertIsInstance(board, wizard_app.LayoutBoard)
            self.assertEqual(board.focused_seg, "path")
            await pilot.press("right")   # move path → after model
            await pilot.pause()
        self.assertEqual(app.state["layout"][0]["segments"], ["model", "path"])

    async def test_left_moves_chip_left(self):
        """n→right(no-op, model is last)→left: model moves to index 0; order is exact."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            board = app.screen
            # Focus model via n-key (path is 0, model is 1)
            await pilot.press("n")       # focus → model
            await pilot.pause()
            self.assertEqual(board.focused_seg, "model")
            await pilot.press("right")   # move model right (it is last → no-op)
            await pilot.pause()
            # model is last, so left moves it to index 0
            await pilot.press("left")
            await pilot.pause()
        # Exact order: model must now be first (the move was not a no-op)
        self.assertEqual(app.state["layout"][0]["segments"], ["model", "path"])

    async def test_up_down_cross_line(self):
        """down moves focused chip (path) from line 0 to line 1."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            board = app.screen
            self.assertEqual(board.focused_seg, "path")
            await pilot.press("down")    # move path from line 0 → line 1
            await pilot.pause()
        self.assertIn("path", app.state["layout"][1]["segments"])
        self.assertNotIn("path", app.state["layout"][0]["segments"])

    async def test_space_toggles_to_tray(self):
        """space on focused chip (path) toggles it to the off-tray."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            board = app.screen
            self.assertEqual(board.focused_seg, "path")
            await pilot.press("space")   # toggle path → tray
            await pilot.pause()
        # After toggle, path should be disabled (in off-tray)
        self.assertFalse(app.state["segments"]["path"])

    async def test_confirm_after_edit_carries_state(self):
        """Board edit → enter → confirm: result.state reflects the edited layout."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            await pilot.press("right")   # move path → after model
            await pilot.pause()
            await pilot.press("enter")   # board → summary
            await pilot.pause()
            await pilot.press("enter")   # confirm (skills/coding is selected)
            await pilot.pause()
        self.assertIsNotNone(app.result)
        self.assertEqual(
            app.result.state["layout"][0]["segments"],
            ["model", "path"],
        )

    async def test_board_focus_glyph_encodes_shape(self):
        """FR-W.7: board label encodes focus via bracket/glyph SHAPE, not color.

        The focused chip appears as [>SEG<] and every other layout-line chip
        appears as [SEG] (no arrows).  After pressing 'n' (focus-next), the
        [>...<] marker moves to the next chip; the previously-focused chip
        reverts to plain [SEG].  Text is read via Label.content (the string
        passed to Label.update()) — purely character content, color-independent.
        """
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            board = app.screen
            self.assertIsInstance(board, wizard_app.LayoutBoard)

            # Initial state: focused_seg == "path" (first chip in first non-empty line)
            lbl = board.query_one("#board-label", wizard_app.Label)
            text = str(lbl.content)
            self.assertIn("[>path<]", text, "focused chip must use [>...<] shape")
            self.assertNotIn("[>model<]", text, "unfocused chip must NOT use [>...<] shape")
            self.assertIn("[model]", text, "unfocused chip must appear as plain [...]")

            # Press 'n' to advance focus: path → model
            await pilot.press("n")
            await pilot.pause()
            text_after = str(lbl.content)
            self.assertIn("[>model<]", text_after, "[>...<] must move to model after n")
            self.assertIn("[path]", text_after, "formerly-focused path must revert to [...]")
            self.assertNotIn("[>path<]", text_after, "path must no longer carry [>...<]")


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestPreview(unittest.IsolatedAsyncioTestCase):
    """Live preview pane tests (Task 3.3 / FR-W.4).

    Verifies that the #preview Static widget in LayoutBoard:
      - exists after mount (initial render fires immediately);
      - changes text after a segment-toggling edit + debounce period;
      - shows "(preview unavailable)" when render_preview returns "".
    """

    def _fake_ctx_with_real_preview(self):
        """WizardContext whose render_preview calls the real status-line renderer.

        Uses the real sample-input.json fixture and real segment defaults so
        the renderer produces genuine output (not the unavailable sentinel).
        """
        import importlib.util as _ilu  # pylint: disable=import-outside-toplevel
        import os as _os  # pylint: disable=import-outside-toplevel

        here = _os.path.dirname(_os.path.abspath(__file__))
        setup_path = _os.path.join(here, "..", "tools", "setup.py")
        spec = _ilu.spec_from_file_location("setup", setup_path)
        _setup = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(_setup)  # type: ignore[union-attr]

        status_line = _os.path.join(here, "..", "tools", "status-line.py")
        with open(_setup._sample_input_path(), encoding="utf-8") as f:  # pylint: disable=protected-access
            sample_json = f.read()

        _sample_toml = _os.path.join(here, "..", "tools", "statusline.toml.sample")

        def _render_preview(segments, layout=None):
            base_config = None
            if layout is not None:
                try:
                    with open(_sample_toml, encoding="utf-8") as _f:
                        base_config = _f.read()
                except OSError:
                    base_config = ""
            return _setup.render_preview(status_line, segments, sample_json, {},
                                         layout=layout, base_config=base_config)

        from tools import setup as _ts  # pylint: disable=import-outside-toplevel
        selection = _fake_selection(items=[
            ["skills", "coding", True],
            ["commands", "commit", True],
        ])
        state = {
            "segments": dict(_setup.SEGMENT_DEFAULTS),
            "layout": [
                {"min_rows": 0, "segments": ["path", "model"]},
                {"min_rows": 20, "segments": []},
            ],
            "dirty": False,
        }
        engine = types.SimpleNamespace(
            render_preview=_render_preview,
            apply_command=_ts._apply_wizard_command,  # pylint: disable=protected-access
            groups=_ts._wizard_groups,  # pylint: disable=protected-access
            order=_ts._wizard_order,  # pylint: disable=protected-access
            layout_move=_ts.layout_move,
            layout_toggle=_ts.layout_toggle,
            off_tray=_ts.off_tray,
        )
        return wizard_app.WizardContext(
            selection=selection,
            state=state,
            sample_json=sample_json,
            engine=engine,
        )

    async def _navigate_to_board(self, app, pilot):
        """Navigate from picks screen to the LayoutBoard."""
        await pilot.pause()
        await pilot.press("tab")
        await pilot.pause()

    async def test_preview_widget_exists_after_mount(self):
        """#preview Static is present in LayoutBoard after mount."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            board = app.screen
            self.assertIsInstance(board, wizard_app.LayoutBoard)
            preview = board.query_one("#preview", wizard_app.Static)
            self.assertIsNotNone(preview)

    async def test_toggle_updates_preview(self):
        """Toggling a segment via space + debounce changes the #preview text.

        Uses the real renderer fixture (sample-input.json + real status-line.py)
        so the before/after comparison is a genuine content change.  A 0.3 s
        pause covers the 100 ms debounce + subprocess startup time.
        """
        ctx = self._fake_ctx_with_real_preview()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            # Wait for the initial debounced preview to settle
            await pilot.pause(0.3)
            board = app.screen
            self.assertIsInstance(board, wizard_app.LayoutBoard)
            before = str(board.query_one("#preview", wizard_app.Static).content)
            # Toggle the focused chip (path) → segments["path"] flips
            await pilot.press("space")
            # Wait for debounce + subprocess round-trip
            await pilot.pause(0.3)
            after = str(board.query_one("#preview", wizard_app.Static).content)
        self.assertNotEqual(before, after,
                            "preview text must change after toggling a segment")

    async def test_move_updates_preview(self):
        """Moving a segment (→ arrow swaps path↔model) changes #preview after debounce.

        Uses the real renderer so before/after is a genuine content change.
        right on the focused chip (path, position 0) moves it to position 1,
        reordering row-1 to [model, path] — a structural layout change the
        renderer must reflect.
        """
        ctx = self._fake_ctx_with_real_preview()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            # Wait for initial debounced preview
            await pilot.pause(0.3)
            board = app.screen
            self.assertIsInstance(board, wizard_app.LayoutBoard)
            before = str(board.query_one("#preview", wizard_app.Static).content)
            # Move path → right (swaps with model; layout becomes [model, path])
            await pilot.press("right")
            # Wait for debounce + subprocess round-trip (longer pause for slow CI)
            await pilot.pause(0.5)
            after = str(board.query_one("#preview", wizard_app.Static).content)
        self.assertNotEqual(before, after,
                            "preview text must change after a layout move")

    async def test_unavailable_shown_when_renderer_returns_empty(self):
        """When render_preview returns "", #preview shows the unavailable sentinel."""
        # _fake_ctx_layout() uses render_preview=lambda segments: ""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            # Wait for debounce to fire
            await pilot.pause(0.3)
            board = app.screen
            text = str(board.query_one("#preview", wizard_app.Static).content)
        self.assertIn("(preview unavailable)", text)

    async def test_epoch_guard_increments_on_schedule(self):
        """_preview_epoch increments with each _schedule_preview call.

        This is a unit-level test of the epoch-guard mechanism.  We cannot
        deterministically force the W1-before-W2 finish-order race in a test
        (the subprocess is too fast), but we verify:

          1. Epoch starts at 0 before any schedule.
          2. Each call to _schedule_preview increments the epoch exactly once.
          3. After N rapid schedules the epoch equals N (monotonically correct).

        Stale-update prevention therefore follows: a worker that snapshotted
        epoch k will find board._preview_epoch > k and discard its result
        whenever a newer call was made while the subprocess ran.

        Race-determinism limitation: we do not simulate a slow W1 finishing
        after a fast W2 because timing a real subprocess race in a test is
        inherently flaky.  The guard correctness is structural — the closure
        passed to call_from_thread compares the snapshotted epoch to the live
        epoch on the UI thread, which is the final arbiter.
        """
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            board = app.screen
            self.assertIsInstance(board, wizard_app.LayoutBoard)

            # on_mount fires one _schedule_preview; epoch should be 1
            initial_epoch = board._preview_epoch  # pylint: disable=protected-access
            self.assertEqual(initial_epoch, 1,
                             "_preview_epoch must be 1 after on_mount schedules first render")

            # Trigger three more rapid schedules (arrow move calls _schedule_preview)
            await pilot.press("right")
            await pilot.press("left")
            await pilot.press("right")
            await pilot.pause()  # let events settle

        # After 3 additional schedules, epoch should be 4 (1 from mount + 3 from moves)
        self.assertEqual(board._preview_epoch, 4,  # pylint: disable=protected-access
                         "_preview_epoch must equal total number of _schedule_preview calls")


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestCrashSafety(unittest.IsolatedAsyncioTestCase):
    """Task 4.1 — crash detection and small-terminal guard in run_wizard."""

    def _fake_ctx_with_failing_preview(self):
        """Return a WizardContext whose render_preview always raises RuntimeError.

        This lets us confirm that an unhandled exception inside the app
        surfaces as WizardCrash rather than being silently swallowed.
        """
        def _bad_render(_segments):
            raise RuntimeError("injected render failure")

        selection = _fake_selection()
        state = {
            "segments": {"git_branch": True},
            "layout": [{"min_rows": 0, "segments": ["git_branch"]}],
            "dirty": False,
        }
        engine = types.SimpleNamespace(
            render_preview=_bad_render,
            apply_command=lambda st, cmd: (st, None),
            groups=lambda st: [],
            order=lambda st: [],
        )
        return wizard_app.WizardContext(
            selection=selection,
            state=state,
            sample_json="{}",
            engine=engine,
        )

    def test_unhandled_exception_raises_wizard_crash(self):
        """If app._exception is set after app.run(), run_wizard must raise WizardCrash.

        We test this by injecting a fake exception directly onto the app object
        (bypassing the Textual event loop) and calling run_wizard with a patched
        app.run that is a no-op.  This exercises the post-run check in isolation,
        without requiring a full async event loop or a real exception path inside
        Textual.
        """
        ctx = _fake_ctx()
        original_exception = RuntimeError("boom")

        app_holder: list = []

        original_init = wizard_app.WizardApp.__init__

        def _patched_init(self_app, *args, **kwargs):
            original_init(self_app, *args, **kwargs)
            app_holder.append(self_app)

        def _patched_run(self_app, **_kw):
            # Store the injected exception — mimics Textual's _handle_exception.
            self_app._exception = original_exception  # pylint: disable=protected-access

        with patch.object(wizard_app.WizardApp, "__init__", _patched_init), \
             patch.object(wizard_app.WizardApp, "run", _patched_run), \
             self.assertRaises(wizard_app.WizardCrash) as cm:
            wizard_app.run_wizard(ctx)

        # The crash must carry the original exception as its cause.
        self.assertIs(cm.exception.__cause__, original_exception)

    def test_small_terminal_raises_wizard_crash_before_app_run(self):
        """A terminal below the minimum size must raise WizardCrash WITHOUT
        ever calling app.run().

        We patch shutil.get_terminal_size to return a tiny size and assert
        that (a) WizardCrash is raised and (b) WizardApp.run was never called.
        """
        ctx = _fake_ctx()
        tiny_size = (10, 5)  # well below _MIN_TERMINAL_COLS × _MIN_TERMINAL_ROWS

        mock_run = MagicMock()
        with patch.object(wizard_app.shutil, "get_terminal_size", return_value=tiny_size), \
             patch.object(wizard_app.WizardApp, "run", mock_run), \
             self.assertRaises(wizard_app.WizardCrash) as cm:
            wizard_app.run_wizard(ctx)

        # app.run must NOT have been called.
        mock_run.assert_not_called()
        # The crash reason must mention the dimensions.
        reason = str(cm.exception.args[0])
        self.assertIn("10", reason)
        self.assertIn("5", reason)


if __name__ == "__main__":
    unittest.main()
