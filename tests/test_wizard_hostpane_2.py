"""Host pane Done screen, doctor, extra-spend alert and acceptance fixes (tools/wizard_app.py).

Split from tests/test_wizard_hostpane.py by test class so the parts run in parallel.
"""

import threading
import types
import unittest

from tests.test_wizard_hostpane import _in_sync_ctx, _notices, _recorder
from tests.wizard_app_common import HAVE_TEXTUAL, query_static
from tools import wizard_app as wa

if HAVE_TEXTUAL:
    from textual.screen import ModalScreen
    from textual.widgets import Static

    from tests.wizard_fixtures import make_ctx

    class _FakeDoctor(ModalScreen):
        """A stand-in for the config doctor screen: Esc returns to Done."""

        BINDINGS = (("escape", "close", "Back"),)

        def compose(self):
            yield Static("fake doctor")

        def action_close(self) -> None:
            self.dismiss(None)


_OK = {"ok": True, "adopt": False, "log": "", "hosts": {}}


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestDoneDoctor(unittest.IsolatedAsyncioTestCase):
    """`d` on Done opens the config doctor after the commit; Esc returns to the same Done."""

    def _app(self, doctor=None, outcome=_OK, sl_state="unset"):
        def commit(selection, states):  # pylint: disable=unused-argument
            return outcome
        ctx = make_ctx(host_ids=("claude",), sl_states={"claude": sl_state})
        return wa.WizardApp(ctx._replace(commit=commit, doctor=doctor))

    async def _to_done(self, app, pilot, keys=()):
        await pilot.pause()
        await pilot.press("enter")                  # choose → pane
        for key in keys:
            await pilot.press(key)
        await pilot.press("enter")                  # pane → Review
        await pilot.press("enter")                  # Review → commit
        await app.workers.wait_for_complete()
        await pilot.pause()

    async def test_d_opens_doctor_and_esc_returns_to_the_same_done(self):
        app = self._app(doctor=_FakeDoctor)
        async with app.run_test() as pilot:
            await self._to_done(app, pilot, keys=("o",))
            before = str(query_static(app, "#done-next").content)
            self.assertIn(wa.DONE_DOCTOR_HINT, before)
            await pilot.press("d")
            await pilot.pause()
            self.assertEqual(len(app.screen_stack), 2)
            await pilot.press("q")                      # the doctor owns q: wizard keeps running
            await pilot.pause()
            self.assertTrue(app.is_running)
            self.assertEqual(len(app.screen_stack), 2)
            await pilot.press("escape")
            await pilot.pause()
            self.assertEqual(len(app.screen_stack), 1)
            self.assertEqual(app.flow.step, wa.STEP_DONE)
            self.assertEqual(str(query_static(app, "#done-next").content), before)

    async def test_factory_runs_each_time_and_a_failure_notifies(self):
        calls = []

        def factory():
            calls.append(1)
            return _FakeDoctor()
        app = self._app(doctor=factory)
        async with app.run_test() as pilot:
            await self._to_done(app, pilot, keys=("o",))
            before = str(query_static(app, "#done-next").content)
            for _ in range(2):
                await pilot.press("d")
                await pilot.pause()
                await pilot.press("escape")
                await pilot.pause()
            self.assertEqual(len(calls), 2)
            self.assertEqual(str(query_static(app, "#done-next").content), before)

        def broken():
            raise OSError("boom")
        app = self._app(doctor=broken)
        async with app.run_test() as pilot:
            await self._to_done(app, pilot, keys=("o",))
            await pilot.press("d")
            await pilot.pause()
            self.assertIn("config doctor failed: boom", _notices(app))
            self.assertEqual(app.flow.step, wa.STEP_DONE)

        def odd():
            raise KeyError("id")
        app = self._app(doctor=odd)
        async with app.run_test() as pilot:
            await self._to_done(app, pilot, keys=("o",))
            await pilot.press("d")
            await pilot.pause()
            self.assertTrue(app.is_running)
            self.assertIn("config doctor failed: 'id'", _notices(app))

    async def test_without_a_doctor_there_is_no_hint_and_d_is_not_consumed(self):
        app = self._app(doctor=None)
        async with app.run_test() as pilot:
            await self._to_done(app, pilot, keys=("o",))
            self.assertNotIn(wa.DONE_DOCTOR_HINT, str(query_static(app, "#done-next").content))
            await pilot.press("d")
            await pilot.pause()
            self.assertEqual(len(app.screen_stack), 1)

    async def test_kept_foreign_host_is_named_as_kept(self):
        outcome = {"ok": True, "adopt": False, "log": "", "hosts": {
            "claude": {"ok": True, "adopt": False, "log": "", "action": "keep_foreign"}}}
        app = wa.WizardApp(make_ctx(host_ids=("claude",), sl_states={"claude": "foreign"},
                                    current_command="my-line.sh")._replace(
            commit=lambda selection, states: outcome))
        async with app.run_test() as pilot:
            await self._to_done(app, pilot)
            self.assertIn("Claude Code: kept its current status line; nothing written to it.",
                          str(query_static(app, "#done-next").content))

    async def test_removed_ai_kit_status_line_is_named_in_the_subtitle(self):
        outcome = {"ok": True, "adopt": False, "log": "", "hosts": {
            "claude": {"ok": True, "adopt": False, "log": "", "action": "remove_ours"}}}
        app = self._app(outcome=outcome, sl_state="ours")
        async with app.run_test() as pilot:
            await self._to_done(app, pilot, keys=("o",))
            sub = str(query_static(app, "#step-sub").content)
            self.assertIn("Claude Code: status line removed", sub)
            self.assertNotIn("status line left unchanged", sub)
            self.assertIn("Claude Code: ai-kit's status line is off",
                          str(query_static(app, "#done-next").content))


def _modal_text(app):
    from textual.widgets import Static

    return str(app.screen.query_one("#foreign-box").query_one(Static).content)


def _one_row_catalog():
    row = {"id": "claude-retention", "check": "check claude-retention",
           "current_display": "5", "recommended_display": "3650", "confidence": "high",
           "why": "why text", "source": "source text", "apply_eligible": True,
           "apply_target": 3650, "security_relevant": False}
    return {"sections": [{"runtime": "claude", "config_path": None, "rows": [row]}]}


_ALERT_LIMIT = "Cursor spend limit: $20.00 (from Cursor, sample)"


def _alert_app(host_keys=None, limit: str | None = _ALERT_LIMIT):
    """Two hosts, both adopted, Cursor carrying the alert keys (D-03, D-12)."""
    keys = {"cursor": {"extra_alert": True}} if host_keys is None else host_keys
    ctx = make_ctx(host_ids=("claude", "cursor"),
                   sl_states={"claude": "ours", "cursor": "ours"},
                   host_keys=keys, alert_limit_text=limit)
    return wa.WizardApp(ctx)


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestExtraSpendAlert(unittest.IsolatedAsyncioTestCase):
    """The Cursor pane's alert row: the `x` toggle and the Cursor limit beside it, no override."""

    async def test_row_shows_on_cursor_pane_only_with_the_limit_text(self):
        app = _alert_app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")                  # Claude's pane
            self.assertFalse(app.query_one("#alert-row").display)
            await pilot.press("enter")                  # Cursor's pane
            self.assertTrue(app.query_one("#alert-row").display)
            self.assertIn(_ALERT_LIMIT, str(query_static(app, "#alert-limit").content))
            self.assertIn(wa.TOGGLE_ON, str(query_static(app, "#alert-toggle").content))

    async def test_every_alert_widget_is_laid_out_on_screen(self):
        # A row of width-less Statics once gave the label the whole width: nothing else showed.
        app = _alert_app()
        async with app.run_test(size=(80, 40)) as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter")
            await pilot.pause()
            for wid in ("#alert-label", "#alert-toggle", "#alert-limit"):
                with self.subTest(widget=wid):
                    region = app.query_one(wid).region
                    self.assertGreater(region.width, 0)
                    self.assertGreater(region.height, 0)
                    self.assertLessEqual(region.right, 80)

    async def test_no_override_box_is_left(self):
        app = _alert_app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter")
            self.assertEqual(len(app.query("#alert-usd")), 0)
            self.assertEqual(len(app.query("#alert-msg")), 0)
            await pilot.press("e")                      # no longer a key: nothing changes
            self.assertEqual(app.model.state["host_keys"]["cursor"], {"extra_alert": True})
            self.assertTrue(app.is_running)

    async def test_preview_callbacks_without_the_preview_box_are_a_no_op(self):
        # The debounce, deadline, resize and worker callbacks can fire after teardown removed
        # #preview (seen as a NoMatches in this class at push time).
        app = _alert_app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter")
            await app.query_one("#preview").remove()
            # pylint: disable=protected-access
            app._kick_preview()
            app._show_preview_fallback()
            app._schedule_preview()
            app._apply_preview(app.preview.seq, app.hosts[app.flow.host_index].id, "x")
            self.assertTrue(app.is_running)

    async def test_limit_text_falls_back_to_unknown_without_an_engine_callable(self):
        app = _alert_app(limit=None)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter")
            self.assertIn(wa.ALERT_LIMIT_UNKNOWN, str(query_static(app, "#alert-limit").content))

    async def test_x_flips_the_toggle_both_ways(self):
        app = _alert_app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter")
            await pilot.press("x")
            self.assertFalse(app.model.state["host_keys"]["cursor"]["extra_alert"])
            self.assertIn(wa.TOGGLE_OFF, str(query_static(app, "#alert-toggle").content))
            await pilot.press("x")
            self.assertTrue(app.model.state["host_keys"]["cursor"]["extra_alert"])
            self.assertIn(wa.TOGGLE_ON, str(query_static(app, "#alert-toggle").content))


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestAlertReview(unittest.IsolatedAsyncioTestCase):
    """Review names a changed alert setting; Enter on Review commits the alert keys."""

    async def test_review_names_the_off_toggle_at_the_cursor_limit(self):
        app = _alert_app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter", "x")
            await pilot.press("enter")                  # → Review
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            review = str(query_static(app, "#rev-what").content)
            self.assertIn("Cursor CLI: extra-spend alert off, at your Cursor spend limit "
                          "(written with its status-line config)", review)
            self.assertNotIn("override", review)

    async def test_review_adds_no_alert_line_when_nothing_changed(self):
        app = _alert_app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter", "enter")   # → Review
            review = str(query_static(app, "#rev-what").content)
            self.assertNotIn("extra-spend alert", review)

    async def test_enter_on_review_commits_the_alert_keys(self):
        calls = []
        ctx = make_ctx(host_ids=("claude", "cursor"),
                       sl_states={"claude": "ours", "cursor": "ours"},
                       host_keys={"cursor": {"extra_alert": True}},
                       alert_limit_text=_ALERT_LIMIT)
        app = wa.WizardApp(_in_sync_ctx(ctx)._replace(commit=_recorder(calls)))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter", "x")
            await pilot.press("enter")                  # → Review
            await pilot.press("enter")                  # commit
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["cursor"]["host_keys"]["cursor"], {"extra_alert": False})

    def test_help_names_x_for_the_cursor_pane_and_no_e(self):
        rows = {row.keys: row for row in wa.HELP[wa.STEP_ARRANGE]}
        self.assertIn("extra-spend alert", rows["x"].help)
        self.assertEqual(rows["x"].host, "cursor")
        self.assertNotIn("e", rows)
        self.assertFalse(any("override" in r.help or "override" in r.short
                             for step in wa.HELP.values() for r in step))
        self.assertFalse(any(cap == "e" for bar in wa.FOOTERS for _label, cap, *_ in bar))


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestAcceptanceFixes(unittest.IsolatedAsyncioTestCase):
    """Plan 30.1-05 acceptance: two-host Yes then No, stale render after off, the real doctor."""

    async def test_yes_then_no_clears_every_foreign_ok(self):
        prepared, calls = [], []

        def prepare(host_id):
            prepared.append(host_id)
            return {"entry": "statusLine = my-line.sh", "file": "/scratch/f.json",
                    "backup": "/scratch/b.bak"}

        ctx = make_ctx(host_ids=("claude", "cursor"),
                       sl_states={"claude": "foreign", "cursor": "foreign"},
                       current_command="my-line.sh")
        app = wa.WizardApp(ctx._replace(commit=_recorder(calls), prepare_foreign=prepare))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")              # choose → Claude's pane
            await pilot.press("o")                  # Claude: remove
            await pilot.press("enter")              # → Cursor's pane
            await pilot.press("o")                  # Cursor: remove
            await pilot.press("enter")              # → Review
            await pilot.press("enter")              # Review: Claude's removal modal
            await pilot.pause()
            self.assertEqual(prepared, ["claude"])
            self.assertIn("Remove Claude Code's existing status line?", _modal_text(app))
            await pilot.press("y")                  # Yes for Claude: Cursor's modal next
            await pilot.pause()
            self.assertEqual(prepared, ["claude", "cursor"])
            self.assertIn("Remove Cursor CLI's existing status line?", _modal_text(app))
            await pilot.press("n")                  # No for Cursor cancels the whole confirm
            await pilot.pause()
            self.assertEqual(len(app.screen_stack), 1)
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            self.assertEqual(calls, [])
            self.assertIs(app.views["claude"].model.state["foreign_ok"], False)
            self.assertIs(app.views["cursor"].model.state["foreign_ok"], False)
            await pilot.press("escape")             # Review → Cursor's pane
            await pilot.press("escape")             # Cursor's pane → Claude's pane
            self.assertEqual(app.flow.host_index, 0)
            await pilot.press("o")                  # Claude: remove → customize (replace)
            await pilot.press("enter")              # → Cursor's pane
            await pilot.press("enter")              # → Review
            await pilot.press("enter")              # Review: the replace modal, not removal
            await pilot.pause()
            text = _modal_text(app)
            self.assertIn("Replace Claude Code's existing status line with ai-kit's?", text)
            self.assertNotIn("Remove Claude Code's", text)
            self.assertEqual(calls, [])

    async def test_stale_render_after_off_keeps_the_off_text(self):
        release = threading.Event()
        calls = []

        def blocked(segments, layout=None, cols=None):  # pylint: disable=unused-argument
            calls.append(segments)
            if len(calls) == 1:
                release.wait(5)
                return "FIRST"
            return "SECOND"
        ctx = make_ctx(host_ids=("claude",), sl_states={"claude": "ours"})
        host = ctx.hosts[0]._replace(engine=types.SimpleNamespace(render_preview=blocked))
        app = wa.WizardApp(ctx._replace(hosts=(host,)))
        app.preview.debounce_s = 0.01
        try:
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("enter")          # → Claude's pane; the first render blocks
                for _ in range(100):
                    if calls:
                        break
                    await pilot.pause(0.02)
                self.assertTrue(calls)
                await pilot.press("o")              # off while that render is in flight
                await pilot.pause()
                release.set()
                await app.workers.wait_for_complete()
                await pilot.pause()
                shown = str(query_static(app, "#preview").content)
                self.assertIn(wa.PREVIEW_OFF_TEXT, shown)
                self.assertNotIn("FIRST", shown)
        finally:
            release.set()

    async def test_d_opens_the_real_config_doctor_screen(self):
        from tools import config_doctor_app as cda

        def factory():
            return cda.ConfigDoctorScreen(
                cda.ConfigDoctorContext(catalog=_one_row_catalog(), apply=None),
                exit_hint="Esc returns to Done.")
        ctx = make_ctx(host_ids=("claude",), sl_states={"claude": "unset"})
        app = wa.WizardApp(ctx._replace(commit=_recorder([]), doctor=factory))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")              # choose → Claude's pane
            await pilot.press("enter")              # → Review
            await pilot.press("enter")              # commit → Done
            await app.workers.wait_for_complete()
            await pilot.pause()
            await pilot.press("d")
            await pilot.pause()
            from textual.widgets import DataTable

            table = app.screen.query_one("#catalog-table", DataTable)
            self.assertEqual(table.row_count, 1)
            await pilot.press("escape")
            await pilot.pause()
            self.assertEqual(len(app.screen_stack), 1)
            self.assertEqual(app.flow.step, wa.STEP_DONE)
