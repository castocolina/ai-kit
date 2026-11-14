"""Host pane band, on/off toggle and per-host Review outcomes (tools/wizard_app.py).

Plan 30.1-05, Task 1: the yes/no adoption gate is gone; each host pane shows a band
(bold host name on the host accent) with the on/off toggle, `o` turns it on or off,
and a foreign host cycles keep -> remove -> customize (owner decision 2026-11-06).
"""
import types
import unittest

from tests.wizard_app_common import HAVE_TEXTUAL, query_static
from tools import wizard_app as wa

if HAVE_TEXTUAL:
    from textual.widgets import Static

    from tests.wizard_fixtures import make_ctx


def _in_sync_ctx(ctx):
    """Make the components equal to their initial state (no component change)."""
    ctx.state["_initial_enabled"] = {(c, n): on for c, n, on in ctx.selection.items}
    return ctx


def _recorder(calls):
    def commit(selection, states):
        calls.append(states)
        return {"ok": True, "adopt": True, "log": "",
                "hosts": {h: {"ok": True, "adopt": st.get("adopt", False), "log": ""}
                          for h, st in states.items()}}
    return commit


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestBandToggleTracer(unittest.IsolatedAsyncioTestCase):
    """Band, toggle and Review outcomes on a two-host (claude, cursor) fixture."""

    TWO = ("claude", "cursor")

    def _app(self, sl_states, calls=None, components_equal=False):
        ctx = make_ctx(host_ids=self.TWO, sl_states=sl_states)
        if components_equal:
            ctx = _in_sync_ctx(ctx)
        if calls is not None:
            ctx = ctx._replace(commit=_recorder(calls))
        return wa.WizardApp(ctx)

    async def test_each_pane_shows_its_band_and_toggle(self):
        app = self._app({"claude": "ours", "cursor": "unset"})
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")                  # choose → Claude's pane, no gate
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)
            self.assertIn("Claude Code", str(query_static(app, "#band-name").content))
            self.assertIn("[ off │●on ]", str(query_static(app, "#band-toggle").content))
            await pilot.press("enter")                  # → Cursor's pane
            self.assertIn("Cursor CLI", str(query_static(app, "#band-name").content))
            self.assertIn("[ ●off │on ]", str(query_static(app, "#band-toggle").content))
            await pilot.press("enter")                  # → Review
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)

    async def test_o_on_cursor_then_commit_passes_its_state(self):
        calls = []
        app = self._app({"claude": "ours", "cursor": "unset"}, calls=calls,
                        components_equal=True)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")                  # → Claude's pane
            await pilot.press("enter")                  # → Cursor's pane
            await pilot.press("o")                      # turn Cursor on
            self.assertIn("[ off │●on ]", str(query_static(app, "#band-toggle").content))
            await pilot.press("enter")                  # → Review
            review = str(query_static(app, "#rev-what").content)
            self.assertIn("Claude Code: unchanged", review)
            self.assertIn("Cursor CLI: wire ai-kit", review)
            await pilot.press("enter")                  # commit
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertEqual(len(calls), 1)
        cursor = calls[0]["cursor"]
        self.assertIs(cursor["adopt"], True)
        self.assertEqual(cursor["start_state"], "unset")
        self.assertIsNone(cursor["adopt_command"])
        self.assertIs(cursor["foreign_ok"], False)
        self.assertIs(cursor["dirty"], False)
        self.assertIs(calls[0]["claude"]["adopt"], True)
        self.assertEqual(calls[0]["claude"]["start_state"], "ours")

    async def test_claude_off_reviews_remove_and_esc_walks_back(self):
        app = self._app({"claude": "ours", "cursor": "unset"})
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")                  # → Claude's pane
            await pilot.press("o")                      # Claude off
            await pilot.press("enter")                  # → Cursor's pane
            await pilot.press("enter")                  # → Review
            self.assertIn("Claude Code: remove ai-kit's",
                          str(query_static(app, "#rev-what").content))
            await pilot.press("escape")                 # Review → last host (Cursor)
            self.assertEqual(app.flow.host_index, 1)
            await pilot.press("escape")                 # Cursor → Claude's pane
            self.assertEqual((app.flow.step, app.flow.host_index), (wa.STEP_ARRANGE, 0))
            await pilot.press("escape")                 # Claude's pane → Choose
            self.assertEqual(app.flow.step, wa.STEP_CHOOSE)

    async def test_nothing_changed_writes_nothing(self):
        calls = []
        ctx = _in_sync_ctx(make_ctx(host_ids=("cursor",), sl_states={"cursor": "unset"}))
        app = wa.WizardApp(ctx._replace(commit=_recorder(calls)))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")                  # → Cursor's pane (left off)
            await pilot.press("enter")                  # → Review
            await pilot.press("enter")                  # confirm: blocked
            self.assertIn("Nothing to write",
                          str(query_static(app, "#cta").content))
        self.assertEqual(calls, [])

    async def test_ours_host_untouched_still_commits_its_upkeep(self):
        calls = []
        ctx = _in_sync_ctx(make_ctx(host_ids=("claude",), sl_states={"claude": "ours"}))
        app = wa.WizardApp(ctx._replace(commit=_recorder(calls)))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")                  # → Claude's pane
            await pilot.press("enter")                  # → Review
            self.assertIn("Claude Code: unchanged",
                          str(query_static(app, "#rev-what").content))
            await pilot.press("enter")                  # upkeep runs: commit once
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertEqual(len(calls), 1)

    async def test_edited_board_on_ours_host_says_update(self):
        calls = []
        ctx = _in_sync_ctx(make_ctx(host_ids=("claude",), sl_states={"claude": "ours"}))
        app = wa.WizardApp(ctx._replace(commit=_recorder(calls)))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")                  # → Claude's pane
            await pilot.press("space")                  # move the focused chip off
            await pilot.press("enter")                  # → Review
            self.assertIn("Claude Code: update ai-kit's layout",
                          str(query_static(app, "#rev-what").content))
            await pilot.press("enter")                  # commit
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertIs(calls[0]["claude"]["dirty"], True)

    async def test_forced_examples_turn_clean_ours_host_into_update(self):
        calls = []
        ctx = _in_sync_ctx(make_ctx(host_ids=("claude",), sl_states={"claude": "ours"}))
        ctx.state["_examples_forced"] = True
        app = wa.WizardApp(ctx._replace(commit=_recorder(calls)))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")                  # → Claude's pane
            await pilot.press("enter")                  # → Review
            self.assertIn("Claude Code: update ai-kit's layout",
                          str(query_static(app, "#rev-what").content))
            await pilot.press("enter")                  # commit (not "Nothing to write")
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertEqual(len(calls), 1)


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestForeignChoice(unittest.IsolatedAsyncioTestCase):
    """One Claude host with another tool's status line (`my-line.sh`)."""

    def _app(self, calls=None, components_equal=False):
        ctx = make_ctx(host_ids=("claude",), sl_states={"claude": "foreign"},
                       current_command="my-line.sh")
        if components_equal:
            ctx = _in_sync_ctx(ctx)
        if calls is not None:
            ctx = ctx._replace(commit=_recorder(calls))
        return wa.WizardApp(ctx)

    async def test_pane_opens_at_keep_and_cycles_through_remove_and_custom(self):
        app = self._app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")                  # → Claude's pane
            self.assertEqual(app.model.state["foreign_choice"], "keep")
            self.assertIs(app.model.state["adopt"], False)
            self.assertIn("[ ●keep │remove │customize ]",
                          str(query_static(app, "#band-toggle").content))
            await pilot.press("enter")                  # → Review
            self.assertIn("Claude Code: keep its current status line; nothing written",
                          str(query_static(app, "#rev-what").content))
            await pilot.press("escape")                 # back to the pane
            await pilot.press("o")
            self.assertEqual(app.model.state["foreign_choice"], "remove")
            self.assertIs(app.model.state["adopt"], False)
            self.assertIn("[ keep │●remove │customize ]",
                          str(query_static(app, "#band-toggle").content))
            await pilot.press("enter")
            self.assertIn("Claude Code: remove the foreign entry, backed up; "
                          "Claude Code shows its own default",
                          str(query_static(app, "#rev-what").content))
            await pilot.press("escape")
            await pilot.press("o")                      # custom
            self.assertEqual(app.model.state["foreign_choice"], "custom")
            self.assertIs(app.model.state["adopt"], True)
            self.assertIn("[ keep │remove │●customize ]",
                          str(query_static(app, "#band-toggle").content))
            self.assertEqual(app.board.lines, app.board.initial_lines)
            before = [list(x) for x in app.board.lines]
            await pilot.press("space")                  # board is editable in custom
            self.assertNotEqual(app.board.lines, before)
            await pilot.press("enter")
            self.assertIn("Claude Code: replace the foreign entry with your ai-kit layout, "
                          "backed up", str(query_static(app, "#rev-what").content))

    async def test_keep_is_not_a_change_and_nothing_is_written(self):
        calls = []
        app = self._app(calls=calls, components_equal=True)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")                  # → Claude's pane (keep)
            await pilot.press("enter")                  # → Review
            await pilot.press("enter")                  # blocked: nothing to write
            self.assertIn("Nothing to write", str(query_static(app, "#cta").content))
        self.assertEqual(calls, [])

    async def test_keep_still_commits_when_components_changed(self):
        calls = []
        app = self._app(calls=calls)                    # components differ from initial
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.press("enter")
            await pilot.press("enter")                  # commit
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertEqual(app.flow.step, wa.STEP_DONE)
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0]["claude"]["adopt"], False)
        self.assertEqual(calls[0]["claude"]["foreign_choice"], "keep")

    async def test_o_clears_a_pending_foreign_ok(self):
        app = self._app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")                  # → Claude's pane
            app.model.state["foreign_ok"] = True
            await pilot.press("o")
            self.assertIs(app.model.state["foreign_ok"], False)

    async def test_full_cycle_returns_to_keep(self):
        app = self._app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            for _ in range(3):
                await pilot.press("o")
            self.assertEqual(app.model.state["foreign_choice"], "keep")
            self.assertIs(app.model.state["adopt"], False)


def _notices(app):
    return [str(n.message) for n in app._notifications]


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestLockedBoard(unittest.IsolatedAsyncioTestCase):
    """An off or foreign-keep/remove board is locked, says why, and ignores edit keys."""

    async def test_off_pane_locks_board_and_notes_what_review_does(self):
        app = wa.WizardApp(make_ctx(host_ids=("claude",), sl_states={"claude": "unset"}))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            self.assertTrue(app.query_one("#board").has_class("locked"))
            note = str(query_static(app, "#band-note").content)
            self.assertIn("Off: no status line is set for Claude Code", note)
            self.assertIn("Press o to turn ai-kit's status line on", note)
            await pilot.press("o")
            self.assertFalse(app.query_one("#board").has_class("locked"))
            self.assertFalse(query_static(app, "#band-note").display)

    async def test_off_edit_keys_do_nothing_and_notify(self):
        app = wa.WizardApp(make_ctx(host_ids=("claude",), sl_states={"claude": "unset"}))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            before = [list(x) for x in app.board.lines]
            tray = list(app.board.tray)
            await pilot.press("space")
            await pilot.press("r")
            self.assertEqual(app.board.lines, before)
            self.assertEqual(app.board.tray, tray)
            self.assertIn(wa.LOCKED_NOTICE, _notices(app))
            await pilot.press("enter")                  # Enter still moves on
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)

    async def test_off_preview_says_host_default_and_calls_no_engine(self):
        calls = []

        def fake(segments, layout=None, cols=None):  # pylint: disable=unused-argument
            calls.append(segments)
            return "RENDER"
        ctx = make_ctx(host_ids=("claude",), sl_states={"claude": "unset"})
        ctx = ctx._replace(hosts=(ctx.hosts[0]._replace(
            engine=types.SimpleNamespace(render_preview=fake)),))
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            await pilot.pause()
            self.assertIn(wa.PREVIEW_OFF_TEXT, str(query_static(app, "#preview").content))
            self.assertEqual(calls, [])

    async def test_foreign_keep_and_remove_are_locked_custom_is_not(self):
        app = wa.WizardApp(make_ctx(host_ids=("claude",), sl_states={"claude": "foreign"},
                                    current_command="my-line.sh"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            self.assertTrue(app.query_one("#board").has_class("locked"))
            note = str(query_static(app, "#band-note").content)
            # The old adoption gate's warning: the pane names the line it would remove.
            self.assertIn("⚠ Claude Code already has another status line: my-line.sh", note)
            self.assertIn("Keep: Review leaves Claude Code's current status line", note)
            await pilot.press("space")
            self.assertIn(wa.FOREIGN_LOCKED_NOTICE, _notices(app))
            await pilot.press("o")                      # remove: still locked
            self.assertTrue(app.query_one("#board").has_class("locked"))
            await pilot.press("o")                      # customize: editable
            self.assertFalse(app.query_one("#board").has_class("locked"))


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestForeignConfirm(unittest.IsolatedAsyncioTestCase):
    """Backup first, then the modal (default No), then the commit."""

    INFO = {"entry": "statusLine.command = my-line.sh",
            "file": "/scratch/settings.json", "backup": "/scratch/backups/settings.json.bak"}

    def _app(self, prepare, commit):
        ctx = make_ctx(host_ids=("claude",), sl_states={"claude": "foreign"},
                       current_command="my-line.sh")
        return wa.WizardApp(ctx._replace(commit=commit, prepare_foreign=prepare))

    async def test_keep_asks_nothing_and_commits(self):
        prepared, calls = [], []
        app = self._app(lambda host_id: prepared.append(host_id) or dict(self.INFO),
                        _recorder(calls))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")                  # keep (the start state)
            await pilot.press("enter")                  # → Review
            await pilot.press("enter")                  # commit, no modal
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertEqual(prepared, [])
            self.assertEqual(len(app.screen_stack), 1)
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0]["claude"]["adopt"], False)

    async def test_remove_backs_up_then_modal_default_no_then_yes_commits(self):
        prepared, calls = [], []
        app = self._app(lambda host_id: prepared.append(host_id) or dict(self.INFO),
                        _recorder(calls))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")                  # → pane
            await pilot.press("o")                      # remove
            await pilot.press("enter")                  # → Review
            await pilot.press("enter")                  # Review Enter: backup, then modal
            await pilot.pause()
            self.assertEqual(prepared, ["claude"])
            self.assertEqual(len(app.screen_stack), 2)
            text = str(app.screen.query_one("#foreign-box").query_one(Static).content)
            self.assertIn("Remove Claude Code's existing status line?", text)
            self.assertIn("/scratch/backups/settings.json.bak", text)
            await pilot.press("enter")                  # default No: back to Review
            await pilot.pause()
            self.assertEqual(len(app.screen_stack), 1)
            self.assertEqual(calls, [])
            self.assertIs(app.model.state["foreign_ok"], False)
            await pilot.press("enter")                  # Review Enter again: modal again
            await pilot.press("y")                      # Yes: commit once
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0]["claude"]["foreign_ok"], True)
        self.assertEqual(calls[0]["claude"]["foreign_choice"], "remove")
        self.assertEqual(calls[0]["claude"]["foreign_backup"], self.INFO["backup"])

    async def test_two_queued_enters_push_one_modal_and_one_backup(self):
        from textual import events

        prepared, calls = [], []
        app = self._app(lambda host_id: prepared.append(host_id) or dict(self.INFO),
                        _recorder(calls))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.press("o")
            await pilot.press("enter")                  # → Review
            app.post_message(events.Key("enter", "\r"))  # both queued before the deferred push
            app.post_message(events.Key("enter", "\r"))
            await pilot.pause()
            self.assertEqual(prepared, ["claude"])
            self.assertEqual(len(app.screen_stack), 2)
            await pilot.press("n")
            await pilot.pause()
            self.assertFalse(app.flow.modal_pending)
        self.assertEqual(calls, [])

    async def test_prepare_error_shows_notice_and_stays_on_review(self):
        calls = []
        app = self._app(lambda host_id: {"error": "x"}, _recorder(calls))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.press("o")
            await pilot.press("enter")
            await pilot.press("enter")
            self.assertEqual(len(app.screen_stack), 1)
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            self.assertIn("x", _notices(app))
        self.assertEqual(calls, [])

    async def test_dry_run_modal_says_nothing_will_be_written(self):
        app = self._app(lambda host_id: dict(self.INFO, backup=""), _recorder([]))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")
            await pilot.press("o")
            await pilot.press("enter")
            await pilot.press("enter")
            await pilot.pause()
            text = str(app.screen.query_one("#foreign-box").query_one(Static).content)
            self.assertIn("Dry run: no backup taken; nothing will be written.", text)
            self.assertNotIn("A backup was saved", text)


