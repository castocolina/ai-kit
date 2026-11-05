"""Install wizard view tests (tools/wizard_app.py), part 3 of 3.

Covers the housekeeping gate and host traversal.

The wizard is a faithful port of docs/wizard-redesign/prototypes/mockup-textual.py. The three
parts run in parallel; the Textual guard and the Static helper live in
tests/wizard_app_common.py.
"""
import threading
import unittest

from tests.wizard_app_common import HAVE_TEXTUAL, query_static
from tools import wizard_app as wa

if HAVE_TEXTUAL:
    from tests.wizard_fixtures import make_ctx


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
            self.assertIn("of", str(query_static(app, "#picksCount").content))

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
            gate = str(query_static(app, "#picksbox").content)
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
            gate = str(query_static(app, "#picksbox").content)
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
            lane0 = str(query_static(app, "#lane0").content)
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
            nxt = str(query_static(app, "#done-next").content)
            title = str(query_static(app, "#step-title").content)
            sub = str(query_static(app, "#step-sub").content)
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
            what = str(query_static(app, "#rev-what").content)
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
            what = str(query_static(app, "#rev-what").content)
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
            nxt = str(query_static(app, "#done-next").content)
            title = str(query_static(app, "#step-title").content)
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
            lane0 = str(query_static(app, "#lane0").content)
            self.assertIn("Wire your Claude Code status line?", lane0)
            await pilot.press("y")                      # accept → the board
            await pilot.pause()
            title = str(query_static(app, "#step-title").content)
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
            self.assertFalse(query_static(app, "#rev-preview").display)
            what = str(query_static(app, "#rev-what").content)
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
