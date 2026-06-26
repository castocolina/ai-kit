"""Tests for tools/wizard_app.py — Textual skeleton (Task 2.1).

The Textual runtime requires ``uv run``; plain ``python3`` will not have it.
The core pre-commit ``unittest`` hook runs plain python3 and therefore SKIPS
these tests via the guard below.  The ``unittest-wizard`` pre-commit hook
(added to .pre-commit-config.yaml by Task 2.1) runs them under uv.

Run manually:
  uv run python -m unittest tests.test_wizard_app -v
"""
import copy
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
    sel.cursor = 0

    def toggle(index: int) -> None:
        sel.items[index][2] = not sel.items[index][2]

    def toggle_cursor() -> None:
        if sel.items:
            toggle(sel.cursor)

    def set_all(value: bool) -> None:
        for row in sel.items:
            row[2] = bool(value)

    def set_category(cat: str, value: bool) -> None:
        for row in sel.items:
            if row[0] == cat:
                row[2] = bool(value)

    def move_cursor(delta: int) -> None:
        if sel.items:
            sel.cursor = max(0, min(len(sel.items) - 1, sel.cursor + delta))

    def enabled_map():
        return {name: on for _cat, name, on in sel.items}

    def category_sets():
        result = {}
        for cat, name, on in sel.items:
            if on:
                result.setdefault(cat, set()).add(name)
        return result

    sel.toggle = toggle
    sel.toggle_cursor = toggle_cursor
    sel.set_all = set_all
    sel.set_category = set_category
    sel.move_cursor = move_cursor
    sel.enabled_map = enabled_map
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
        "adopt": False,
    }
    engine = types.SimpleNamespace(
        render_preview=lambda segments, layout=None: "",
        apply_command=_setup._apply_wizard_command,  # pylint: disable=protected-access
        groups=_setup._wizard_groups,  # pylint: disable=protected-access
        order=_setup._wizard_order,  # pylint: disable=protected-access
        layout_move=_setup.layout_move,
        layout_toggle=_setup.layout_toggle,
        off_tray=_setup.off_tray,
        layout_defaults=lambda: copy.deepcopy(_setup.LAYOUT_DEFAULTS),
    )
    return wizard_app.WizardContext(
        selection=selection,
        state=state,
        sample_json="{}",
        engine=engine,
        status_line={"state": "unset", "current_command": None},
        segment_meta={},
        external_segments=[],
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
        render_preview=lambda segments, layout=None: "",
        apply_command=lambda st, cmd: (st, None),
        groups=lambda st: [],
        order=lambda st: [],
    )
    return wizard_app.WizardContext(
        selection=selection,
        state=state,
        sample_json="{}",
        engine=engine,
        status_line={"state": "unset", "current_command": None},
        segment_meta={},
        external_segments=[],
    )


def _fake_ctx_picks():
    """WizardContext for TestInstallPicks: 3 skills + 2 commands, cursor at 0."""
    items = [
        ["skills", "coding",  True],   # 0
        ["skills", "review",  False],  # 1
        ["skills", "agents",  False],  # 2
        ["commands", "commit", True],  # 3
        ["commands", "push",   False], # 4
    ]
    selection = _fake_selection(items=items)
    state = {
        "segments": {n: v for _, n, v in items},
        "layout": [{"min_rows": 0, "segments": ["commit"]}],
        "dirty": False,
    }
    engine = types.SimpleNamespace(
        render_preview=lambda segments, layout=None: "",
        apply_command=lambda st, cmd: (st, None),
        groups=lambda st: [
            ("skills",   ["coding", "review", "agents"]),
            ("commands", ["commit", "push"]),
        ],
        order=lambda st: ["coding", "review", "agents", "commit", "push"],
    )
    return wizard_app.WizardContext(
        selection=selection,
        state=state,
        sample_json="{}",
        engine=engine,
        status_line={"state": "unset", "current_command": None},
        segment_meta={
            "coding":  {"icon": "🤖", "description": "AI coding"},
            "review":  {"icon": "🔍", "description": "Code review"},
            "agents":  {"icon": "👥", "description": "Agents"},
            "commit":  {"icon": "📝", "description": "Git commit"},
            "push":    {"icon": "🚀", "description": "Git push"},
        },
        external_segments=[],
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

    async def test_esc_from_arrange_goes_to_choose(self):
        """The Esc KEY from STEP_ARRANGE (gate answered) goes back to Choose (Task 8).

        Exercises the real key path: pressing 'y' answers the adoption gate
        (_gate_done=True), after which LayoutBoard.key_escape no longer consumes
        Esc, so it bubbles to WizardApp's ('escape','back') binding → action_back
        → STEP_ARRANGE branch → _PicksScreen remounted.  Uses _fake_ctx_layout()
        because answering the gate with 'y' opens the board (needs engine.off_tray).
        """
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()              # let _PicksScreen mount
            await pilot.press("tab")         # AdvanceStep(STEP_ARRANGE) → board + gate
            await pilot.pause()
            await pilot.press("y")           # answer gate (adopt) → _gate_done=True
            await pilot.pause()              # _open_board + call_after_refresh settle
            await pilot.pause()
            await pilot.press("escape")      # real Esc key → bubbles → action_back
            await pilot.pause()
            # _PicksScreen should be remounted; LayoutBoard should be gone
            picks = list(app.query(wizard_app._PicksScreen))
            self.assertTrue(
                len(picks) > 0,
                "_PicksScreen not remounted after Esc key from STEP_ARRANGE",
            )

    async def test_help_modal_appears(self):
        """Pressing '?' pushes HelpModal onto the screen stack (Task 8)."""
        ctx = _fake_ctx()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("question_mark")
            await pilot.pause()
            self.assertIsInstance(app.screen, wizard_app.HelpModal,
                                  "Expected HelpModal to be the current screen after '?'")

    async def test_help_modal_renders_help_dict(self):
        """HelpModal(STEP_CHOOSE) renders HELP content, not FOOTERS (Task 8).

        HELP[STEP_CHOOSE] carries 'A / N' (global all/none) which is absent
        from FOOTERS[STEP_CHOOSE] — its presence proves the modal reads HELP.
        """
        ctx = _fake_ctx()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("question_mark")
            await pilot.pause()
            body = app.screen.query_one("#help-body")
            self.assertIn("A / N", str(body.render()),
                          "Expected 'A / N' from HELP[STEP_CHOOSE] in HelpModal body")

    async def test_picks_populated_from_ctx(self):
        """Count label reflects the total from ctx.selection.items."""
        items = [
            ["skills", "alpha", True],
            ["skills", "beta", False],
            ["commands", "gamma", True],
        ]
        ctx = _fake_ctx(items=items)
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            count_widget = app.screen.query_one("#picks-count")
            self.assertIn(f"of {len(items)} components selected", str(count_widget.content))

    async def test_boot(self):
        """App mounts without crashing (Task 1 scaffold)."""
        ctx = _fake_ctx()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
        # passes if no exception raised


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestInstallPicks(unittest.IsolatedAsyncioTestCase):
    """Toggle / all / none interaction tests (Task 3)."""

    async def test_space_toggle_changes_glyph(self):
        """space toggles the focused row (index 0) in ctx.selection.items."""
        ctx = _fake_ctx_picks()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("space")
            await pilot.pause()
        self.assertFalse(ctx.selection.items[0][2])

    async def test_a_selects_category_only(self):
        """'a' enables all picks in the focused category only (per-category)."""
        ctx = _fake_ctx_picks()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
        skills = [it for it in ctx.selection.items if it[0] == "skills"]
        self.assertTrue(all(it[2] for it in skills))
        self.assertTrue(ctx.selection.items[3][2])   # commit=True unchanged
        self.assertFalse(ctx.selection.items[4][2])  # push=False unchanged

    async def test_n_deselects_category_only(self):
        """'n' disables all picks in the focused category only (per-category)."""
        ctx = _fake_ctx_picks()
        for it in ctx.selection.items:
            it[2] = True  # all on before test
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("n")
            await pilot.pause()
        skills = [it for it in ctx.selection.items if it[0] == "skills"]
        self.assertTrue(all(not it[2] for it in skills))
        commands = [it for it in ctx.selection.items if it[0] == "commands"]
        self.assertTrue(all(it[2] for it in commands))

    async def test_A_selects_all_global(self):
        """'A' enables ALL picks across every category."""
        ctx = _fake_ctx_picks()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("A")
            await pilot.pause()
        self.assertTrue(all(it[2] for it in ctx.selection.items))

    async def test_N_deselects_all_global(self):
        """'N' disables ALL picks across every category."""
        ctx = _fake_ctx_picks()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("N")
            await pilot.pause()
        self.assertTrue(all(not it[2] for it in ctx.selection.items))

    async def test_per_category_count_renders(self):
        """Category header line contains '{on}/{total} on' text."""
        ctx = _fake_ctx_picks()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            body = app.screen.query_one("#picks-body", wizard_app.Static)
            self.assertIn("/3 on", str(body.content))

    async def test_total_count_renders(self):
        """#picks-count widget contains 'of {total_n} components selected'."""
        ctx = _fake_ctx_picks()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            count = app.screen.query_one("#picks-count", wizard_app.Static)
            self.assertIn("of 5 components selected", str(count.content))

    async def test_glyph_shape(self):
        """FR-W.7: body renders ◉ for enabled and ◯ for disabled segments."""
        ctx = _fake_ctx_picks()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            body = app.screen.query_one("#picks-body", wizard_app.Static)
            text = str(body.content)
        self.assertIn("◉", text, "enabled segment must render ◉ glyph")
        self.assertIn("◯", text, "disabled segment must render ◯ glyph")

    async def test_cursor_row_has_pink_gutter(self):
        """Cursor row renders with PINK ▌ gutter; regression check vs gray highlight."""
        ctx = _fake_ctx_picks()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            body = app.screen.query_one("#picks-body", wizard_app.Static)
            text = str(body.content)
        self.assertIn(wizard_app.PINK, text, "cursor row must carry PINK color marker")
        self.assertEqual(text.count("▌"), 1, "exactly one row should have the ▌ gutter")

    async def test_cursor_pink_moves_on_down(self):
        """Pressing ↓ moves the PINK ▌ gutter to the next row."""
        ctx = _fake_ctx_picks()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            body_before = str(app.screen.query_one("#picks-body", wizard_app.Static).content)
            await pilot.press("down")
            await pilot.pause()
            body_after = str(app.screen.query_one("#picks-body", wizard_app.Static).content)
        pink_before = next((ln for ln in body_before.split("\n") if wizard_app.PINK in ln), "")
        pink_after = next((ln for ln in body_after.split("\n") if wizard_app.PINK in ln), "")
        self.assertNotEqual(
            pink_before, pink_after, "pink cursor row should shift after pressing ↓"
        )

    async def test_empty_category_not_rendered(self):
        """Category absent from selection items does NOT appear in #picks-body."""
        ctx = _fake_ctx(items=[
            ["skills", "coding", True],
            ["skills", "review", False],
        ])
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            body = app.screen.query_one("#picks-body", wizard_app.Static)
            text = str(body.content)
        self.assertIn("skills", text.lower())
        self.assertNotIn("commands", text.lower())


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestConfirm(unittest.IsolatedAsyncioTestCase):
    """Summary + confirm flow tests (Task 2.3)."""

    async def test_enter_confirms_and_sets_result(self):
        """enter → arrange gate → n (skip) → enter → summary → enter → confirms."""
        ctx = _fake_ctx(items=[["skills", "a", True]])
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("enter")   # picks → arrange (gate)
            await pilot.pause()
            await pilot.press("n")       # gate: skip → one-liner (adopt=False)
            await pilot.pause()
            await pilot.press("enter")   # one-liner → summary (STEP_REVIEW)
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
            await pilot.press("enter")   # picks → arrange (gate)
            await pilot.pause()
            await pilot.press("n")       # gate: skip → one-liner
            await pilot.pause()
            await pilot.press("enter")   # one-liner → summary
            await pilot.pause()
            await pilot.press("q")       # abort from summary
        self.assertIsNone(app.result)

    async def test_empty_selection_default_no_returns_to_picks(self):
        """Empty selection: enter → arrange gate → n → summary → enter opens empty-confirm modal.
        Default action (enter, no explicit yes) pops back to picks; result is None."""
        ctx = _fake_ctx(items=[["skills", "a", False]])
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("enter")   # picks → arrange (gate)
            await pilot.pause()
            await pilot.press("n")       # gate: skip → one-liner
            await pilot.pause()
            await pilot.press("enter")   # one-liner → summary (empty)
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
            await pilot.press("enter")   # picks → arrange (gate)
            await pilot.pause()
            await pilot.press("n")       # gate: skip → one-liner
            await pilot.pause()
            await pilot.press("enter")   # one-liner → summary (empty)
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
            await pilot.press("enter")    # picks → arrange (gate)
            await pilot.pause()
            await pilot.press("n")        # gate: skip → one-liner
            await pilot.pause()
            await pilot.press("enter")    # one-liner → summary
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
            await pilot.press("enter")   # picks → arrange (gate)
            await pilot.pause()
            await pilot.press("n")       # gate: skip → one-liner
            await pilot.pause()
            await pilot.press("enter")   # one-liner → summary (empty)
            await pilot.pause()
            await pilot.press("enter")   # empty confirm modal opens
            await pilot.pause()
            await pilot.press("q")       # dismiss modal → back to picks (not abort)
        # result is None: the wizard was NOT confirmed (returned to picks, then
        # the test harness exited cleanly without a further confirmation).
        self.assertIsNone(app.result)

    # ------------------------------------------------------------------
    # Task 5 — SummaryScreen: review-only, _has_net_change guard
    # ------------------------------------------------------------------

    async def test_enter_shows_summary(self):
        """Navigate to SummaryScreen; 'Install Summary' renders in #summary-text."""
        app = wizard_app.WizardApp(_fake_ctx())
        async with app.run_test() as pilot:
            await pilot.press("enter")   # picks → arrange (gate)
            await pilot.pause()
            await pilot.press("n")       # gate: skip (adopt=False)
            await pilot.pause()
            await pilot.press("enter")   # board → SummaryScreen (STEP_REVIEW)
            await pilot.pause()
            await pilot.pause()          # extra pause for screen push to settle
            # app.screen is the active screen (top of stack = SummaryScreen)
            self.assertIsInstance(app.screen, wizard_app.SummaryScreen)
            # Textual 8.2.7: Label/Static exposes no public .renderable; read mangled content
            text = str(app.screen.query_one("#summary-text")._Static__content)
            self.assertIn("Install Summary", text)

    async def test_enter_commits_result(self):
        """SummaryScreen with non-empty selection → enter commits result (guard bypassed)."""
        # Use absent _initial_enabled so component_changed=True → guard bypasses
        ctx = _fake_ctx(items=[["skills", "a", True]])
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("enter")   # picks → arrange (gate)
            await pilot.pause()
            await pilot.press("n")       # gate: skip (adopt=False)
            await pilot.pause()
            await pilot.press("enter")   # board → SummaryScreen
            await pilot.pause()
            await pilot.press("enter")   # summary → guard passes → commit
        self.assertIsNotNone(app.result)
        self.assertIsInstance(app.result, wizard_app.WizardResult)

    async def test_escape_pops_to_arrange(self):
        """Escape from SummaryScreen pops back to STEP_ARRANGE (LayoutBoard visible)."""
        app = wizard_app.WizardApp(_fake_ctx())
        async with app.run_test() as pilot:
            await pilot.press("enter")   # picks → arrange (gate)
            await pilot.pause()
            await pilot.press("n")       # gate: skip
            await pilot.pause()
            await pilot.press("enter")   # board → SummaryScreen
            await pilot.pause()
            await pilot.pause()          # extra pause for screen push to settle
            await pilot.press("escape")  # pop back to board
            await pilot.pause()
            # After pop, app.screen is the default screen; LayoutBoard is in it
            boards = app.screen.query(wizard_app.LayoutBoard)
            self.assertTrue(len(boards) > 0)

    async def test_empty_selection_shows_modal(self):
        """Empty selection: enter on SummaryScreen opens EmptyConfirmModal."""
        ctx = _fake_ctx(items=[["skills", "a", False]])
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("enter")   # picks → arrange (gate)
            await pilot.pause()
            await pilot.press("n")       # gate: skip
            await pilot.pause()
            await pilot.press("enter")   # board → SummaryScreen
            await pilot.pause()
            await pilot.pause()          # extra pause for screen push to settle
            await pilot.press("enter")   # action_confirm → EmptyConfirmModal pushed
            await pilot.pause()
            # EmptyConfirmModal is pushed on top; app.screen is the modal
            self.assertIsInstance(app.screen, wizard_app.EmptyConfirmModal)

    async def test_no_net_change_shows_modal(self):
        """_initial_enabled matches current + adopt=False → no net change → modal."""
        items = [["skills", "a", True]]
        ctx = _fake_ctx(items=items)
        # Seed initial_enabled to match current selection exactly (no changes)
        ctx.state["_initial_enabled"] = {
            (cat, name): on for cat, name, on in ctx.selection.items
        }
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("enter")   # picks → arrange
            await pilot.pause()
            await pilot.press("n")       # gate: skip (adopt=False in app.state)
            await pilot.pause()
            await pilot.press("enter")   # board → SummaryScreen
            await pilot.pause()
            await pilot.pause()          # extra pause for screen push to settle
            await pilot.press("enter")   # action_confirm → no net change → modal
            await pilot.pause()
            # EmptyConfirmModal is pushed on top; app.screen is the modal
            self.assertIsInstance(app.screen, wizard_app.EmptyConfirmModal)

    async def test_component_change_bypasses_guard(self):
        """_initial_enabled seeded; flip one item → component_changed=True → commits."""
        items = [["skills", "a", False]]
        ctx = _fake_ctx(items=items)
        # Seed initial to match original state
        ctx.state["_initial_enabled"] = {
            (cat, name): on for cat, name, on in ctx.selection.items
        }
        # Flip the item so current != initial
        ctx.selection.items[0][2] = True
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("enter")   # picks → arrange
            await pilot.pause()
            await pilot.press("n")       # gate: skip (adopt=False)
            await pilot.pause()
            await pilot.press("enter")   # board → SummaryScreen
            await pilot.pause()
            await pilot.press("enter")   # action_confirm → guard passes → commit
        self.assertIsNotNone(app.result)
        self.assertIsInstance(app.result, wizard_app.WizardResult)

    async def test_adopt_true_bypasses_guard_and_summary_shows_write_plan(self):
        """adopt=True + no component change: guard passes + summary shows write-plan.

        Critical path for FIX 1 (_has_net_change reads LIVE app.state["adopt"],
        not frozen ctx.state) and FIX 2 (_build_summary_text receives live state).

        Uses _fake_ctx_layout() because pressing 'y' at the gate calls _open_board()
        which needs engine.off_tray — absent in _fake_ctx's minimal engine stub.
        """
        ctx = _fake_ctx_layout()
        # Seed _initial_enabled to match current selection exactly → component_changed=False.
        # The only reason _has_net_change returns True must be adopt=True (FIX 1 verified).
        ctx.state["_initial_enabled"] = {
            (cat, name): on for cat, name, on in ctx.selection.items
        }
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()              # let _PicksScreen mount
            await pilot.press("tab")         # AdvanceStep(STEP_ARRANGE) → _swap_body
            await pilot.pause()              # let LayoutBoard mount + gate render
            await pilot.press("y")           # gate: adopt=True → app.state["adopt"]=True
            await pilot.pause()              # _open_board() + call_after_refresh(_init_board)
            await pilot.pause()              # extra settle (mirrors _navigate_to_board pattern)
            await pilot.press("enter")       # board → SummaryScreen (STEP_REVIEW)
            await pilot.pause()
            await pilot.pause()              # extra settle for screen push
            # (a) SummaryScreen is still active — not blocked by EmptyConfirmModal
            self.assertIsInstance(app.screen, wizard_app.SummaryScreen)
            # (b) Summary reflects adopt=True: write-plan shown, not "unchanged"
            # Textual 8.2.7: Label/Static exposes no public .renderable; read mangled content
            text = str(app.screen.query_one("#summary-text")._Static__content)
            self.assertIn(
                "Will configure", text,
                "adopt=True summary must show write-config plan",
            )
            self.assertNotIn(
                "unchanged", text,
                "adopt=True summary must NOT show 'unchanged'",
            )
            # Commit: guard passes (adopt=True even with no component change)
            await pilot.press("enter")
        # Guard passed → WizardResult committed, not swallowed by nothing-to-do modal
        self.assertIsNotNone(
            app.result,
            "adopt=True must produce a result even when no component changed",
        )
        self.assertIsInstance(app.result, wizard_app.WizardResult)

    async def test_double_escape_from_summary_no_crash(self):
        """Repro I-1: escape from SummaryScreen then escape again must not crash.

        Before fix: second escape called pop_screen() on an empty stack because
        _step remained STEP_REVIEW after the first escape → ScreenStackError → crash.
        After fix: _step is restored to STEP_ARRANGE before pop, so second escape
        calls _swap_body(STEP_CHOOSE) instead → _PicksScreen shown, no crash.
        """
        ctx = _fake_ctx(items=[["skills", "a", True]])
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("enter")   # picks → arrange (gate)
            await pilot.pause()
            await pilot.press("n")       # gate: skip (adopt=False)
            await pilot.pause()
            await pilot.press("enter")   # board → SummaryScreen (STEP_REVIEW)
            await pilot.pause()
            await pilot.pause()          # extra settle for screen push
            await pilot.press("escape")  # pop SummaryScreen → board (STEP_ARRANGE)
            await pilot.pause()
            await pilot.press("escape")  # board → _PicksScreen (STEP_CHOOSE)
            await pilot.pause()
            # No crash: _exception must be unset
            self.assertIsNone(app._exception)
            # After second escape, step is STEP_CHOOSE and _PicksScreen is in the body
            self.assertEqual(app._step, wizard_app.STEP_CHOOSE)
            picks = app.screen.query(wizard_app._PicksScreen)
            self.assertTrue(len(picks) > 0, "_PicksScreen must be present after double-escape")

    async def test_external_all_off_triggers_nothing_selected_modal(self):
        """I-2: external segment present but toggled OFF → Trigger 2 guard fires.

        Before fix: has_external used static default_on (always True) → guard never fired.
        After fix: has_external reads live app.state["segments"] → False when toggled off.
        """
        base_ctx = _fake_ctx(items=[["skills", "a", False]])
        # Add external segment with id "ext1"; seed it OFF in state (user toggled off)
        base_ctx.state["segments"]["ext1"] = False
        ctx = base_ctx._replace(
            external_segments=[{"id": "ext1", "default_on": True, "name": "ext1"}]
        )
        # No _initial_enabled seeded → component_changed=True → Trigger 1 bypassed
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("enter")   # picks → arrange (gate)
            await pilot.pause()
            await pilot.press("n")       # gate: skip (adopt=False)
            await pilot.pause()
            await pilot.press("enter")   # board → SummaryScreen
            await pilot.pause()
            await pilot.pause()          # extra settle for screen push
            await pilot.press("enter")   # action_confirm → Trigger 2 → EmptyConfirmModal
            await pilot.pause()
            # Trigger 2 guard must have fired → modal on top
            self.assertIsInstance(app.screen, wizard_app.EmptyConfirmModal)

    async def test_external_on_bypasses_trigger2_guard(self):
        """I-2: external segment toggled ON → Trigger 2 guard does not fire → result committed."""
        base_ctx = _fake_ctx(items=[["skills", "a", False]])
        # Add external segment with id "ext1"; seed it ON in state
        base_ctx.state["segments"]["ext1"] = True
        ctx = base_ctx._replace(
            external_segments=[{"id": "ext1", "default_on": True, "name": "ext1"}]
        )
        # No _initial_enabled seeded → component_changed=True → Trigger 1 bypassed
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("enter")   # picks → arrange (gate)
            await pilot.pause()
            await pilot.press("n")       # gate: skip (adopt=False)
            await pilot.pause()
            await pilot.press("enter")   # board → SummaryScreen
            await pilot.pause()
            await pilot.press("enter")   # action_confirm → guard passes → exit
        # Guard did not fire → WizardResult committed
        self.assertIsNotNone(app.result)
        self.assertIsInstance(app.result, wizard_app.WizardResult)


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestLayoutBoard(unittest.IsolatedAsyncioTestCase):
    """Layout board interaction tests (Task 3.2 / FR-W.4)."""

    async def _navigate_to_board(self, app, pilot):
        """Helper: wait for picks screen then tab to board, answer adoption gate."""
        await pilot.pause()          # let _PicksScreen mount
        await pilot.press("tab")     # AdvanceStep(STEP_ARRANGE) → _swap_body
        await pilot.pause()          # let LayoutBoard mount + gate render
        await pilot.press("y")       # answer adoption gate Yes
        await pilot.pause()          # let board panels mount + initial render

    async def test_arrow_moves_chip_within_line(self):
        """right moves the focused chip (path) to the right within line 0."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            # focused_seg defaults to first chip in first non-empty group = "path"
            board = app.query_one(wizard_app.LayoutBoard)
            self.assertEqual(board._focused_seg, "path")
            await pilot.press("right")   # move path → after model
            await pilot.pause()
        self.assertEqual(app.state["layout"][0]["segments"], ["model", "path"])

    async def test_left_moves_chip_left(self):
        """n→right(no-op, model is last)→left: model moves to index 0; order is exact."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            board = app.query_one(wizard_app.LayoutBoard)
            # Focus model via n-key (path is 0, model is 1)
            await pilot.press("n")       # focus → model
            await pilot.pause()
            self.assertEqual(board._focused_seg, "model")
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
            board = app.query_one(wizard_app.LayoutBoard)
            self.assertEqual(board._focused_seg, "path")
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
            board = app.query_one(wizard_app.LayoutBoard)
            self.assertEqual(board._focused_seg, "path")
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
            board = app.query_one(wizard_app.LayoutBoard)

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

    async def test_arrow_moves_focused_chip(self):
        """right arrow moves focused chip (path) one position right in lane 0."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            board = app.query_one(wizard_app.LayoutBoard)
            self.assertEqual(board._focused_seg, "path")
            await pilot.press("right")
            await pilot.pause()
        self.assertEqual(app.state["layout"][0]["segments"], ["model", "path"])

    async def test_up_cross_line(self):
        """down then up: chip returns to its original lane."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            await pilot.press("down")
            await pilot.pause()
            self.assertIn("path", app.state["layout"][1]["segments"])
            await pilot.press("up")
            await pilot.pause()
        self.assertIn("path", app.state["layout"][0]["segments"])
        self.assertNotIn("path", app.state["layout"][1]["segments"])

    async def test_space_to_tray(self):
        """space on focused chip moves it to the off-tray."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            await pilot.press("space")
            await pilot.pause()
        from tools import setup as _setup  # pylint: disable=import-outside-toplevel
        tray = _setup.off_tray(app.state)
        self.assertIn("path", tray)

    async def test_focus_glyph(self):
        """#board-label contains [>path<] for focused and [model] for unfocused."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            board = app.query_one(wizard_app.LayoutBoard)
            lbl = board.query_one("#board-label", wizard_app.Label)
            text = str(lbl.content)
        self.assertIn("[>path<]", text)
        self.assertIn("[model]", text)
        self.assertNotIn("[>model<]", text)

    async def test_r_resets_layout(self):
        """r key resets layout to LAYOUT_DEFAULTS after a move."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            await pilot.press("right")
            await pilot.pause()
            await pilot.press("r")
            await pilot.pause()
        from tools import setup as _setup  # pylint: disable=import-outside-toplevel
        self.assertEqual(app.state["layout"], _setup.LAYOUT_DEFAULTS)

    async def test_shift_tab_reverses_panel_cycle(self):
        """tab then shift+tab returns _focus_panel to its original value."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            board = app.query_one(wizard_app.LayoutBoard)
            original = board._focus_panel
            await pilot.press("tab")
            await pilot.pause()
            await pilot.press("shift+tab")
            await pilot.pause()
        self.assertEqual(board._focus_panel, original)

    async def test_left_right_noop_in_tray(self):
        """left arrow is a no-op when focused chip is in the off-tray."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            await pilot.press("space")
            await pilot.pause()
            layout_before = [dict(row) for row in app.state["layout"]]
            await pilot.press("left")
            await pilot.pause()
        self.assertEqual(
            [row["segments"] for row in app.state["layout"]],
            [row["segments"] for row in layout_before],
        )


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestLayoutBoardGateStates(unittest.IsolatedAsyncioTestCase):
    """Adoption gate state tests (Task 4 review — I3).

    Verifies that the three status_line states (foreign / ours / unset-skip)
    produce the correct LayoutBoard behaviour:
      - foreign  → Enter defaults to No; board panels absent, gate-confirm present
      - ours     → gate skipped on mount; board panels present, adopt=True
      - unset+n  → key_n skips board; board panels absent, gate-confirm present
      - unset+esc→ esc treated as No; board panels absent (m1)
      - short term → ours board lanes show 'needs ≥ N rows' subtitle (I2)
    """

    async def _to_arrange(self, app, pilot):
        """Advance from picks to STEP_ARRANGE without answering the gate."""
        await pilot.pause()          # let _PicksScreen mount
        await pilot.press("tab")     # AdvanceStep(STEP_ARRANGE) → _swap_body
        await pilot.pause()          # let LayoutBoard mount + gate render

    async def test_foreign_gate_shows_warning_and_default_no(self):
        """foreign state: Enter defaults to No — no board panels, adopt=False."""
        ctx = _fake_ctx_layout()._replace(
            status_line={"state": "foreign", "current_command": "fancybash --color"},
        )
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._to_arrange(app, pilot)
            await pilot.press("enter")   # Enter → default No (foreign)
            await pilot.pause()
            board = app.query_one(wizard_app.LayoutBoard)
            self.assertFalse(app.state["adopt"])
            self.assertEqual(len(board.query("#board-lanes")), 0)

    async def test_ours_gate_skipped_board_preloaded(self):
        """ours state: gate is skipped on mount; board panels present, adopt=True."""
        ctx = _fake_ctx_layout()._replace(
            status_line={"state": "ours", "current_command": None},
        )
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._to_arrange(app, pilot)
            await pilot.pause()          # let _init_board fire after_refresh
            board = app.query_one(wizard_app.LayoutBoard)
            self.assertTrue(board._gate_done)
            self.assertTrue(app.state["adopt"])
            self.assertEqual(len(board.query("#board-lanes")), 1)

    async def test_skip_no_editor_board_absent(self):
        """unset state + n: no board panels, gate-confirm one-liner present."""
        ctx = _fake_ctx_layout()  # status_line state = "unset" by default
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._to_arrange(app, pilot)
            await pilot.press("n")       # skip → one-liner
            await pilot.pause()
            board = app.query_one(wizard_app.LayoutBoard)
            self.assertEqual(len(board.query("#board-lanes")), 0)
            self.assertEqual(len(board.query("#gate-confirm")), 1)

    async def test_escape_during_gate_skips(self):
        """unset state + esc: esc treated as No — no board panels, adopt=False (m1)."""
        ctx = _fake_ctx_layout()  # status_line state = "unset" by default
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._to_arrange(app, pilot)
            await pilot.press("escape")  # esc during gate → key_n
            await pilot.pause()
            board = app.query_one(wizard_app.LayoutBoard)
            self.assertFalse(app.state["adopt"])
            self.assertEqual(len(board.query("#board-lanes")), 0)

    async def test_lane_gating_subtitle_on_short_terminal(self):
        """short terminal: ours board lanes carry the 'needs ≥ N rows' subtitle (I2)."""
        ctx = _fake_ctx_layout()._replace(
            status_line={"state": "ours", "current_command": None},
        )
        app = wizard_app.WizardApp(ctx)
        # height 10 < LANE_GATE[1]=20 and < LANE_GATE[2]=30 → both thresholds unmet
        async with app.run_test(size=(80, 10)) as pilot:
            await self._to_arrange(app, pilot)
            await pilot.pause()          # let _init_board fire after_refresh
            board = app.query_one(wizard_app.LayoutBoard)
            lanes = board.query_one("#board-lanes")
            self.assertIn("needs", lanes.border_subtitle)
            self.assertIn("≥ 20 rows", lanes.border_subtitle)


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
            "adopt": False,
        }
        engine = types.SimpleNamespace(
            render_preview=_render_preview,
            apply_command=_ts._apply_wizard_command,  # pylint: disable=protected-access
            groups=_ts._wizard_groups,  # pylint: disable=protected-access
            order=_ts._wizard_order,  # pylint: disable=protected-access
            layout_move=_ts.layout_move,
            layout_toggle=_ts.layout_toggle,
            off_tray=_ts.off_tray,
            layout_defaults=lambda: copy.deepcopy(_ts.LAYOUT_DEFAULTS),
        )
        return wizard_app.WizardContext(
            selection=selection,
            state=state,
            sample_json=sample_json,
            engine=engine,
            status_line={"state": "unset", "current_command": None},
            segment_meta={},
            external_segments=[],
        )

    async def _navigate_to_board(self, app, pilot):
        """Navigate from picks screen to the LayoutBoard and answer adoption gate."""
        await pilot.pause()
        await pilot.press("tab")
        await pilot.pause()
        await pilot.press("y")       # answer adoption gate Yes
        await pilot.pause()

    async def test_preview_widget_exists_after_mount(self):
        """#board-preview Static is present in LayoutBoard after mount."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            board = app.query_one(wizard_app.LayoutBoard)
            preview = board.query_one("#board-preview", wizard_app.Static)
            self.assertIsNotNone(preview)

    async def test_toggle_updates_preview(self):
        """Toggling a segment via space + debounce changes the #board-preview text.

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
            board = app.query_one(wizard_app.LayoutBoard)
            before = str(board.query_one("#board-preview", wizard_app.Static).content)
            # Toggle the focused chip (path) → segments["path"] flips
            await pilot.press("space")
            # Wait for debounce + subprocess round-trip
            await pilot.pause(0.3)
            after = str(board.query_one("#board-preview", wizard_app.Static).content)
        self.assertNotEqual(before, after,
                            "preview text must change after toggling a segment")

    async def test_move_updates_preview(self):
        """Moving a segment (→ arrow swaps path↔model) changes #board-preview after debounce.

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
            board = app.query_one(wizard_app.LayoutBoard)
            before = str(board.query_one("#board-preview", wizard_app.Static).content)
            # Move path → right (swaps with model; layout becomes [model, path])
            await pilot.press("right")
            # Wait for debounce + subprocess round-trip (longer pause for slow CI)
            await pilot.pause(0.5)
            after = str(board.query_one("#board-preview", wizard_app.Static).content)
        self.assertNotEqual(before, after,
                            "preview text must change after a layout move")

    async def test_unavailable_shown_when_renderer_returns_empty(self):
        """When render_preview returns "", #board-preview shows the unavailable sentinel."""
        # _fake_ctx_layout() uses render_preview=lambda segments, layout=None: ""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            # Wait for debounce to fire
            await pilot.pause(0.3)
            board = app.query_one(wizard_app.LayoutBoard)
            text = str(board.query_one("#board-preview", wizard_app.Static).content)
        self.assertIn("— preview unavailable —", text)

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
            board = app.query_one(wizard_app.LayoutBoard)

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

    def _fake_ctx_with_failing_preview(self):
        """Return a WizardContext whose render_preview always raises RuntimeError.

        Used by test_unavailable_sentinel_on_raise to verify that an exception
        inside the preview worker shows the sentinel rather than crashing.
        Engine includes all attributes required by LayoutBoard so the board can
        mount and navigate to the preview pane correctly.
        """
        from tools import setup as _setup  # pylint: disable=import-outside-toplevel

        def _bad_render(_segments, layout=None):
            raise RuntimeError("injected render failure")

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
            "adopt": False,
        }
        engine = types.SimpleNamespace(
            render_preview=_bad_render,
            apply_command=_setup._apply_wizard_command,  # pylint: disable=protected-access
            groups=_setup._wizard_groups,  # pylint: disable=protected-access
            order=_setup._wizard_order,  # pylint: disable=protected-access
            layout_move=_setup.layout_move,
            layout_toggle=_setup.layout_toggle,
            off_tray=_setup.off_tray,
            layout_defaults=lambda: copy.deepcopy(_setup.LAYOUT_DEFAULTS),
        )
        return wizard_app.WizardContext(
            selection=selection,
            state=state,
            sample_json="{}",
            engine=engine,
            status_line={"state": "unset", "current_command": None},
            segment_meta={},
            external_segments=[],
        )

    async def test_unavailable_sentinel_on_raise(self):
        """When render_preview raises, #board-preview must show the unavailable sentinel.

        Verifies the failure path in _run_preview: an exception is caught and
        the text falls through to "— preview unavailable —" instead of crashing.
        """
        ctx = self._fake_ctx_with_failing_preview()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            # Wait for debounce + worker round-trip
            await pilot.pause(0.3)
            board = app.query_one(wizard_app.LayoutBoard)
            text = str(board.query_one("#board-preview", wizard_app.Static).content)
        self.assertIn("— preview unavailable —", text,
                      "widget must show sentinel when render_preview raises")

    async def test_stale_epoch_discard(self):
        """A _run_preview call with a stale epoch must not update the widget.

        Strategy (deterministic — no subprocess timing involved):
          1. Navigate to the board; wait for the initial debounced preview.
          2. Patch board._update_preview to record every call.
          3. Bump _preview_epoch manually so any worker carrying the old epoch
             is stale.
          4. Call _run_preview(stale_epoch) directly — the entry-guard must
             discard it immediately.
          5. Assert _update_preview was never called.
        """
        ctx = _fake_ctx_layout()   # render_preview returns "" → sentinel
        app = wizard_app.WizardApp(ctx)
        update_calls: list = []

        async with app.run_test() as pilot:
            await self._navigate_to_board(app, pilot)
            await pilot.pause(0.3)   # let initial preview settle
            board = app.query_one(wizard_app.LayoutBoard)

            # Snapshot the epoch from the initial preview (should be 1)
            stale_epoch = board._preview_epoch  # pylint: disable=protected-access

            # Patch _update_preview BEFORE bumping the epoch
            original_update = board._update_preview
            def _tracking_update(text):  # pylint: disable=cell-var-from-loop
                update_calls.append(text)
                original_update(text)
            board._update_preview = _tracking_update  # pylint: disable=protected-access

            # Bump epoch so that stale_epoch is now outdated
            board._preview_epoch += 1  # pylint: disable=protected-access

            # Fire worker with the stale epoch — entry guard must discard it
            board._run_preview(stale_epoch)  # pylint: disable=protected-access
            await pilot.pause(0.3)   # give the worker time to (not) run

        self.assertEqual(update_calls, [],
                         "_update_preview must NOT be called for a stale epoch")


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestCrashSafety(unittest.IsolatedAsyncioTestCase):
    """Task 4.1 — crash detection and small-terminal guard in run_wizard."""

    def _fake_ctx_with_failing_preview(self):
        """Return a WizardContext whose render_preview always raises RuntimeError.

        This lets us confirm that an unhandled exception inside the app
        surfaces as WizardCrash rather than being silently swallowed.
        All WizardContext fields are populated (status_line, segment_meta,
        external_segments) to avoid a latent TypeError on construction.
        """
        def _bad_render(_segments, layout=None):
            raise RuntimeError("injected render failure")

        selection = _fake_selection()
        state = {
            "segments": {"git_branch": True},
            "layout": [{"min_rows": 0, "segments": ["git_branch"]}],
            "dirty": False,
            "adopt": False,
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
            status_line={"state": "unset", "current_command": None},
            segment_meta={},
            external_segments=[],
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
        # The crash reason must mention "too small" and the actual dimensions.
        reason = str(cm.exception.args[0])
        self.assertIn("too small", reason)
        self.assertIn("10", reason)
        self.assertIn("5", reason)


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestWizardContextShape(unittest.TestCase):
    """Task 10: the WizardContext NamedTuple carries the new Plan-B fields."""

    def test_context_carries_new_fields(self):
        ctx = wizard_app.WizardContext(
            selection=object(),
            state={"segments": {}, "layout": [], "dirty": False, "adopt": False},
            sample_json="{}",
            engine=object(),
            status_line={"state": "unset", "current_command": None},
            segment_meta={"path": {"description": "d", "sample": "s",
                                   "icon": "", "line": 0}},
            external_segments=[],
        )
        self.assertEqual(ctx.status_line["state"], "unset")
        self.assertEqual(ctx.segment_meta["path"]["line"], 0)
        self.assertEqual(ctx.external_segments, [])
        self.assertFalse(ctx.state["adopt"])

    def test_status_line_field_shape(self):
        """status_line must carry 'state' (one of the 3 sentinels) and
        'current_command' (str or None)."""
        for state_val, cmd_val in [
            ("unset", None),
            ("ours", "/path/to/status-line.py"),
            ("foreign", "other-cmd"),
        ]:
            with self.subTest(state=state_val):
                ctx = wizard_app.WizardContext(
                    selection=object(),
                    state={"segments": {}, "layout": [], "dirty": False, "adopt": False},
                    sample_json="{}",
                    engine=object(),
                    status_line={"state": state_val, "current_command": cmd_val},
                    segment_meta={},
                    external_segments=[],
                )
                self.assertIsInstance(ctx.status_line["state"], str)
                self.assertIn(ctx.status_line["state"], ("unset", "ours", "foreign"))
                self.assertIn("current_command", ctx.status_line)

    def test_segment_meta_field_shape(self):
        """Each segment_meta value must have description/sample/icon (str) and
        line (int)."""
        meta = {
            "path": {"description": "current dir", "sample": "~/proj",
                     "icon": "", "line": 1},
            "git_branch": {"description": "branch", "sample": "main",
                           "icon": "", "line": 2},
        }
        ctx = wizard_app.WizardContext(
            selection=object(),
            state={"segments": {}, "layout": [], "dirty": False, "adopt": False},
            sample_json="{}",
            engine=object(),
            status_line={"state": "unset", "current_command": None},
            segment_meta=meta,
            external_segments=[],
        )
        for key, val in ctx.segment_meta.items():
            with self.subTest(segment=key):
                self.assertIsInstance(val["description"], str)
                self.assertIsInstance(val["sample"], str)
                self.assertIsInstance(val["icon"], str)
                self.assertIsInstance(val["line"], int)

    def test_external_segments_field_shape(self):
        """Each external_segments entry must carry the required keys."""
        ext = [{"id": "my_seg", "name": "My Segment", "path": "/p/seg.py",
                "description": "desc", "icon": "", "sample": "hello",
                "line": 42, "provenance": "user"}]
        ctx = wizard_app.WizardContext(
            selection=object(),
            state={"segments": {}, "layout": [], "dirty": False, "adopt": False},
            sample_json="{}",
            engine=object(),
            status_line={"state": "unset", "current_command": None},
            segment_meta={},
            external_segments=ext,
        )
        self.assertIsInstance(ctx.external_segments, list)
        required_keys = ("id", "name", "path", "description", "icon",
                         "sample", "line", "provenance")
        for entry in ctx.external_segments:
            with self.subTest(id=entry.get("id")):
                for key in required_keys:
                    self.assertIn(key, entry)

    def test_adopt_flag_initial_value(self):
        """ctx.state['adopt'] is False on a fresh install where detect_statusline
        returns state='unset'."""
        import tempfile  # pylint: disable=import-outside-toplevel

        from tools import setup as _setup  # pylint: disable=import-outside-toplevel
        with tempfile.TemporaryDirectory() as tmp:
            paths = _setup.resolve_paths({"HOME": tmp})
            entries = {cat: [] for cat in _setup.CATEGORIES}
            installed = {cat: set() for cat in _setup.CATEGORIES}
            ctx = _setup._build_wizard_context(  # pylint: disable=protected-access
                paths, entries, installed, "{}", wizard_app
            )
        self.assertIn("adopt", ctx.state)
        self.assertIsInstance(ctx.state["adopt"], bool)
        self.assertFalse(ctx.state["adopt"])

    def test_initial_enabled_snapshot(self):
        """_initial_enabled snapshot must equal {(cat, name): on} for every
        item in the selection at construction time."""
        import tempfile  # pylint: disable=import-outside-toplevel

        from tools import setup as _setup  # pylint: disable=import-outside-toplevel
        entries = {
            "agents":   [("coder", None), ("reviewer", None)],
            "commands": [("commit", None)],
            "skills":   [("coding", None)],
        }
        installed = {"agents": {"coder"}, "commands": set(), "skills": set()}
        with tempfile.TemporaryDirectory() as tmp:
            paths = _setup.resolve_paths({"HOME": tmp})
            ctx = _setup._build_wizard_context(  # pylint: disable=protected-access
                paths, entries, installed, "{}", wizard_app
            )
        self.assertIn("_initial_enabled", ctx.state)
        expected = {(cat, name): on for cat, name, on in ctx.selection.items}
        self.assertEqual(ctx.state["_initial_enabled"], expected)

    def test_initial_enabled_first_run_is_installed_baseline_not_selection(self):
        """On a FIRST run the wizard pre-checks all entries (selection all-on),
        but _initial_enabled must reflect the INSTALLED baseline (all-off) so the
        nothing-to-do guard does not wrongly block a fresh install. This is the
        case that motivated keying _initial_enabled by installed state rather
        than by the selection snapshot."""
        import tempfile  # pylint: disable=import-outside-toplevel

        from tools import setup as _setup  # pylint: disable=import-outside-toplevel
        entries = {
            "agents":   [("coder", None), ("reviewer", None)],
            "commands": [("commit", None)],
            "skills":   [("coding", None)],
        }
        installed = {cat: set() for cat in _setup.CATEGORIES}  # nothing installed = first run
        with tempfile.TemporaryDirectory() as tmp:
            paths = _setup.resolve_paths({"HOME": tmp})
            ctx = _setup._build_wizard_context(  # pylint: disable=protected-access
                paths, entries, installed, "{}", wizard_app
            )
        # Selection is pre-checked (all True) on first run ...
        self.assertTrue(all(on for _cat, _name, on in ctx.selection.items))
        # ... but the baseline is all-False (installed), so accepting the
        # defaults counts as a real change (guard does not block).
        self.assertTrue(all(v is False for v in ctx.state["_initial_enabled"].values()))
        self.assertNotEqual(
            ctx.state["_initial_enabled"],
            {(cat, name): on for cat, name, on in ctx.selection.items},
            "first-run baseline must DIFFER from the all-on selection snapshot",
        )


class TestRenderers(unittest.TestCase):
    """Unit tests for pure rendering helpers (Task 2).

    All helpers are pure functions — no Textual app required.
    """

    def test_render_header_step0_exactly_one_accent_three_line(self):
        """_render_header(0): exactly one ACCENT pip, exactly two LINE pips (3-pip design)."""
        result = wizard_app._render_header(0)
        self.assertEqual(
            result.count(wizard_app.ACCENT), 1,
            f"expected 1 ACCENT pip, got: {result!r}",
        )
        self.assertEqual(
            result.count(wizard_app.LINE), 2,
            f"expected 2 LINE pips, got: {result!r}",
        )

    def test_render_header_step_done_has_green_pip(self):
        """_render_header(STEP_DONE): at least one GREEN pip."""
        result = wizard_app._render_header(wizard_app.STEP_DONE)
        self.assertIn(wizard_app.GREEN, result)
        self.assertIn("●", result)

    def test_chip_focused_contains_escaped_focus_bracket(self):
        """`_chip("path", focused=True)` raw string contains escaped ``\\[>``."""
        result = wizard_app._chip("path", focused=True)
        # Rich silently drops ``[>`` as an unknown tag; we must emit ``\[>`` so
        # it renders as a literal bracket.  Assert the escaped form is present.
        self.assertIn(r"\[>", result)
        self.assertIn("path", result)

    def test_chip_unfocused_no_wrapping_brackets(self):
        """`_chip("model", focused=False)` label present, no ``[model]`` brackets."""
        result = wizard_app._chip("model", focused=False)
        self.assertIn("model", result)
        # Unfocused chips use space-padding; ``[model]`` would be eaten by Rich.
        self.assertNotIn("[model]", result)

    def test_cap_primary_contains_blue_background(self):
        """`_cap("enter", primary=True)` contains `#10325c` background."""
        result = wizard_app._cap("enter", primary=True)
        self.assertIn("#10325c", result)

    def test_cap_secondary_uses_keycap_background(self):
        """`_cap("q", primary=False)` uses KEYCAP background."""
        result = wizard_app._cap("q", primary=False)
        self.assertIn(wizard_app.KEYCAP, result)

    def test_render_footer_contains_step_keys(self):
        """_render_footer for STEP_CHOOSE contains key labels from that step's FOOTERS."""
        result = wizard_app._render_footer(
            wizard_app.FOOTERS[wizard_app.STEP_CHOOSE]
        )
        # FOOTERS[STEP_CHOOSE][0] is ("Continue", "enter", True) — assert the label.
        self.assertIn("Continue", result)

    def test_render_footer_quit_separate_from_footer(self):
        """_render_footer_quit() returns Quit; _render_footer() does not include it."""
        left = wizard_app._render_footer(wizard_app.FOOTERS[wizard_app.STEP_CHOOSE])
        quit_str = wizard_app._render_footer_quit()
        # Quit must be absent from the left panel and present in the quit panel.
        self.assertNotIn(wizard_app.QUIT_KEY[0], left)   # "Quit" not in left
        self.assertIn(wizard_app.QUIT_KEY[0], quit_str)   # "Quit" in right

    def test_render_footer_quit_contains_quit_key_label(self):
        """_render_footer_quit() always includes the QUIT_KEY label ('Quit')."""
        result = wizard_app._render_footer_quit()
        self.assertIn(wizard_app.QUIT_KEY[0], result)  # "Quit"

    def test_render_footer_has_pipe_separator(self):
        """_render_footer separates entries with the │ pipe glyph."""
        result = wizard_app._render_footer(
            wizard_app.FOOTERS[wizard_app.STEP_CHOOSE]
        )
        self.assertIn("│", result)


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestChrome(unittest.IsolatedAsyncioTestCase):
    """Chrome-presence pilot tests: WizardHeader + WizardFooter mount on every step."""

    async def test_step_choose_has_header(self):
        """Step 1 (Choose): WizardHeader present and renders 'Step 1 of 3' + correct title."""
        ctx = _fake_ctx()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            node = app.screen.query_one("#headerbar")
            self.assertIsNotNone(node)
            self.assertIsInstance(node, wizard_app.WizardHeader)
            # Content assertions: right side shows step label; #step-title shows screen title.
            right = app.screen.query_one("#header-right", wizard_app.Static)
            self.assertIn("Step 1 of 3", str(right.content))
            title = app.screen.query_one("#step-title", wizard_app.Static)
            self.assertIn(wizard_app.TITLES[wizard_app.STEP_CHOOSE], str(title.content))

    async def test_step_choose_has_footer(self):
        """Step 1 (Choose): WizardFooter present and #footer-left contains 'Continue'."""
        ctx = _fake_ctx()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            node = app.screen.query_one("#footerbar")
            self.assertIsNotNone(node)
            self.assertIsInstance(node, wizard_app.WizardFooter)
            # Content assertion: left panel must show the primary action for this step.
            footer_left = app.screen.query_one("#footer-left", wizard_app.Static)
            self.assertIn("Continue", str(footer_left.content))

    async def test_step_arrange_has_header(self):
        """Step 2 (Arrange): WizardHeader present and renders 'Step 2 of 3' + correct title."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("tab")
            await pilot.pause()
            node = app.screen.query_one("#headerbar")
            self.assertIsNotNone(node)
            self.assertIsInstance(node, wizard_app.WizardHeader)
            # Content assertions: right side shows step label; #step-title shows screen title.
            right = app.screen.query_one("#header-right", wizard_app.Static)
            self.assertIn("Step 2 of 3", str(right.content))
            title = app.screen.query_one("#step-title", wizard_app.Static)
            self.assertIn(wizard_app.TITLES[wizard_app.STEP_ARRANGE], str(title.content))

    async def test_step_arrange_has_footer(self):
        """Step 2 (Arrange): WizardFooter present and #footer-left contains 'Reset' or 'On/off'."""
        ctx = _fake_ctx_layout()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("tab")
            await pilot.pause()
            node = app.screen.query_one("#footerbar")
            self.assertIsNotNone(node)
            self.assertIsInstance(node, wizard_app.WizardFooter)
            # Content assertion: left panel must show arrange-step keys.
            footer_left = app.screen.query_one("#footer-left", wizard_app.Static)
            content = str(footer_left.content)
            self.assertTrue(
                "Reset" in content or "On/off" in content,
                f"Expected 'Reset' or 'On/off' in footer-left, got: {content!r}",
            )

    async def test_review_screen_has_header(self):
        """Step 3 (Review): WizardHeader present and renders 'Step 3 of 3' + correct title."""
        ctx = _fake_ctx()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await app.push_screen(wizard_app.SummaryScreen())
            await pilot.pause()
            node = app.screen.query_one("#headerbar")
            self.assertIsNotNone(node)
            self.assertIsInstance(node, wizard_app.WizardHeader)
            # Content assertions: right side shows step label; #step-title shows screen title.
            right = app.screen.query_one("#header-right", wizard_app.Static)
            self.assertIn("Step 3 of 3", str(right.content))
            title = app.screen.query_one("#step-title", wizard_app.Static)
            self.assertIn(wizard_app.TITLES[wizard_app.STEP_REVIEW], str(title.content))

    async def test_review_screen_has_footer(self):
        """Step 3 (Review): WizardFooter present and #footer-left contains 'Install'."""
        ctx = _fake_ctx()
        app = wizard_app.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await app.push_screen(wizard_app.SummaryScreen())
            await pilot.pause()
            node = app.screen.query_one("#footerbar")
            self.assertIsNotNone(node)
            self.assertIsInstance(node, wizard_app.WizardFooter)
            # Content assertion: left panel must show the primary action for this step.
            footer_left = app.screen.query_one("#footer-left", wizard_app.Static)
            self.assertIn("Install", str(footer_left.content))


class TestModuleSeam(unittest.TestCase):
    """Task 10 constraint: wizard_app imports NOTHING from setup.py. The new
    context fields are plain data/callables injected by setup.py; the seam must
    stay intact so the render path never pulls in the wizard's heavy deps."""

    def test_wizard_app_does_not_import_setup(self):
        import ast
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "tools", "wizard_app.py")
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotEqual(alias.name, "setup",
                                        "wizard_app must not import setup")
                    self.assertFalse(alias.name.endswith(".setup"),
                                     "wizard_app must not import setup")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                self.assertNotEqual(mod, "setup",
                                    "wizard_app must not import from setup")
                self.assertFalse(mod.endswith(".setup"),
                                 "wizard_app must not import from setup")


if __name__ == "__main__":
    unittest.main()
