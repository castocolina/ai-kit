"""Install wizard view tests (tools/wizard_app.py), part 3 of 3.

Covers the housekeeping gate and host traversal.

The wizard is a faithful port of docs/wizard-redesign/prototypes/mockup-textual.py. The three
parts run in parallel; the Textual guard and the Static helper live in
tests/wizard_app_common.py.
"""
import os
import shutil
import sys
import tempfile
import threading
import unittest
from unittest import mock

from tests.wizard_app_common import HAVE_TEXTUAL, query_static
from tools import setup as setup_mod
from tools import wizard_app as wa

if HAVE_TEXTUAL:
    from tests.wizard_fixtures import make_ctx

_TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)
# The module setup.py's _sibling() loads, so mock.patch below reaches the same object.
import global_rules


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
    """Task 1's seam contract: the flow visits every detected host's pane, the band
    toggle sets each host's status line, and every host's state is serialized
    before any commit (plan 23-16; plan 30.1-05 replaces the gate with the band)."""

    TWO = ("claude", "cursor")

    async def _walk(self, app, pilot, answers=("o", "o")):
        """Choose → each host's pane: ``o`` turns that host's band on (``""`` leaves it
        off), then Enter moves to the next host's pane, or to Review after the last."""
        await pilot.pause()
        await pilot.press("enter")                  # choose → first host's pane
        for ans in answers:
            if ans:
                await pilot.press(ans)              # this host's band toggle
            await pilot.press("enter")              # pane → next host / review
        return app.flow.step

    async def test_two_hosts_walk_pane_pane_review(self):
        app = wa.WizardApp(make_ctx(host_ids=self.TWO, sl_state="unset"))
        async with app.run_test() as pilot:
            step = await self._walk(app, pilot, ("o", "o"))
            self.assertEqual(step, wa.STEP_REVIEW)
            self.assertEqual([h.id for h in app.hosts], ["claude", "cursor"])
            # Both hosts' bands were turned on in their own panes.
            self.assertTrue(all(app.views[h.id].model.state["adopt"] for h in app.hosts))

    async def test_off_first_host_still_visits_second_pane(self):
        app = wa.WizardApp(make_ctx(host_ids=self.TWO, sl_state="unset"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")              # choose → claude's pane
            await pilot.press("enter")              # claude left off → cursor's pane
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)
            self.assertEqual(app.flow.host_index, 1)    # the SECOND host is visited
            band = str(query_static(app, "#band-name").content)
            self.assertIn("Cursor", band)           # cursor's band, not Claude's

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
            await self._walk(app, pilot, ("o", "o"))
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

    async def test_review_escape_returns_to_last_host_pane(self):
        app = wa.WizardApp(make_ctx(host_ids=self.TWO, sl_state="unset"))
        async with app.run_test() as pilot:
            await self._walk(app, pilot, ("o", "o"))
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            await pilot.press("escape")
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)
            self.assertEqual(app.flow.host_index, 1)              # the LAST host's pane

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
            await self._walk(app, pilot, ("o", "o"))
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
            await self._walk(app, pilot, ("o", "o"))
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
            await pilot.press("enter")                  # choose → Claude's pane
            await pilot.press("o")                      # band on → Claude's board
            await pilot.press("enter")                  # pane → Cursor's pane
            await pilot.press("o")                      # band on → Cursor's board
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
            await self._walk(app, pilot, ("o", ""))    # Claude adopts, Cursor stays off
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            what = str(query_static(app, "#rev-what").content)
            self.assertIn("Cursor CLI: unchanged", what)
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
            await self._walk(app, pilot, ("o", "o"))
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            what = str(query_static(app, "#rev-what").content)
            self.assertIn("Claude Code: wire ai-kit (~/.config/ai-kit/claude-statusline.toml "
                          "+ settings.json)", what)
            self.assertIn("Cursor CLI: wire ai-kit (~/.config/ai-kit/cursor-statusline.toml "
                          "+ cli-config.json)", what)

    async def test_cursor_failure_shown_on_done_while_claude_succeeds(self):
        def commit(selection, states):
            return {"ok": False, "adopt": True, "log": "",
                    "hosts": {"claude": {"ok": True, "adopt": True, "log": ""},
                              "cursor": {"ok": False, "adopt": True,
                                         "log": "cursor doctor refused"}}}

        ctx = make_ctx(host_ids=self.TWO, sl_state="unset")._replace(commit=commit)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await self._walk(app, pilot, ("o", "o"))
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
        title and the band name the host even in a one-host context."""
        app = wa.WizardApp(make_ctx(host_ids=("claude",), sl_state="unset"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")                  # choose → Claude's pane
            band = str(query_static(app, "#band-name").content)
            self.assertIn("Claude Code", band)
            await pilot.press("o")                      # band on → the board
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


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestGlobalRulesReview(unittest.IsolatedAsyncioTestCase):
    """Phase 30 D-11: the global-rules item shows its bullet and preview on Review only while on."""

    PREVIEW = [
        "claude /x/CLAUDE.md: replace codegraph's sentence",
        "  - old sentence",
        "  + new sentence",
    ]

    def _ctx(self, on):
        ctx = make_ctx(host_ids=())
        # Selection rows are mutable lists at runtime; SelectionLike types them as tuples.
        ctx.selection.items.append(["global rules", "codegraph sentence", on])  # pyright: ignore[reportArgumentType]
        rules = {"changes": ["a", "b", "c", "d"], "preview": self.PREVIEW}
        return ctx._replace(state={**ctx.state, "_global_rules": rules})

    async def _to_review(self, app, pilot):
        await pilot.pause()
        for _ in range(6):
            if app.flow.step == wa.STEP_REVIEW:
                break
            await pilot.press("enter")
            await pilot.pause()
        return app.flow.step

    async def test_review_shows_bullet_and_preview_when_on(self):
        app = wa.WizardApp(self._ctx(True))
        async with app.run_test() as pilot:
            self.assertEqual(await self._to_review(app, pilot), wa.STEP_REVIEW)
            what = str(query_static(app, "#rev-what").content)
            self.assertIn("Rewrite codegraph's sentence in 4 global instruction files", what)
            self.assertIn("replace codegraph's sentence", what)

    async def test_review_hides_bullet_when_off(self):
        app = wa.WizardApp(self._ctx(False))
        async with app.run_test() as pilot:
            self.assertEqual(await self._to_review(app, pilot), wa.STEP_REVIEW)
            what = str(query_static(app, "#rev-what").content)
            self.assertNotIn("Rewrite codegraph's sentence", what)

    async def test_g_toggles_the_item_on_review(self):
        app = wa.WizardApp(self._ctx(True))
        async with app.run_test() as pilot:
            self.assertEqual(await self._to_review(app, pilot), wa.STEP_REVIEW)
            await pilot.press("g")
            await pilot.pause()
            self.assertFalse(app._global_rules_on())
            self.assertNotIn("Rewrite codegraph's sentence",
                             str(query_static(app, "#rev-what").content))
            self.assertIn("Global rules", str(query_static(app, "#footer-left").content))
            await pilot.press("g")
            await pilot.pause()
            self.assertTrue(app._global_rules_on())

    async def test_enter_commits_with_the_item_off_after_g(self):
        calls = []

        def commit(selection, states):
            calls.append([(c, n, on) for c, n, on in selection.items])
            return {"ok": True, "adopt": False, "log": [], "hosts": {}}
        ctx = self._ctx(True)._replace(commit=commit)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("space")          # a real change: the first skill goes off
            for _ in range(6):
                if app.flow.step == wa.STEP_REVIEW:
                    break
                await pilot.press("enter")
                await pilot.pause()
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            await pilot.press("g")              # the item goes off on Review
            await pilot.press("enter")          # install
            await pilot.pause()
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertEqual(len(calls), 1)
        global_rules = [on for c, _n, on in calls[0] if c == "global rules"]
        self.assertEqual(global_rules, [False])

    async def test_without_the_item_review_says_nothing_to_change(self):
        app = wa.WizardApp(make_ctx(host_ids=()))
        async with app.run_test() as pilot:
            self.assertEqual(await self._to_review(app, pilot), wa.STEP_REVIEW)
            self.assertIn("global rules: nothing to change",
                          str(query_static(app, "#rev-what").content))
            await pilot.press("g")              # no item: `g` is not consumed
            await pilot.pause()
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)


def _rules_body():
    # The installer sentence sits inside the block (rewritten) and once outside it (kept).
    return (
        b"prefix\r\n" + global_rules.START + b"\r\n" + global_rules.INSTALLER_SENTENCE
        + b"\r\n" + global_rules.END + b"\r\n" + global_rules.INSTALLER_SENTENCE
        + b" tail \xc3\xa9"
    )


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestWizardBuilders(unittest.TestCase):
    """The global-rules item through every wizard route; uv tier, the wizard module needs rich."""

    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="ai-kit-p30-")
        self.addCleanup(shutil.rmtree, self.home, True)
        codex = os.path.join(self.home, ".codex")
        self.paths = {
            "claude": os.path.join(self.home, ".claude", "CLAUDE.md"),
            "codex": os.path.join(codex, "AGENTS.md"),
            "gemini": os.path.join(self.home, ".gemini", "GEMINI.md"),
            "opencode": os.path.join(self.home, ".config", "opencode", "AGENTS.md"),
        }
        self.env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": self.home,
            "XDG_STATE_HOME": os.path.join(self.home, "state"),
            "XDG_CONFIG_HOME": os.path.join(self.home, ".config"),
            "CLAUDE_CONFIG_DIR": os.path.join(self.home, ".claude"),
            "CODEX_HOME": codex,
            "AI_KIT_REFUSE_REAL_HOME": "1",
        }
        self.item = setup_mod.GLOBAL_RULES_ITEM

    def write_all(self):
        for path in self.paths.values():
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(_rules_body())

    def read(self, host):
        with open(self.paths[host], "rb") as fh:
            return fh.read()

    def inputs(self):
        categories = setup_mod.CATEGORIES
        entries = {cat: [] for cat in categories}
        installed = {cat: set() for cat in categories}
        return setup_mod.resolve_paths(self.env), entries, installed

    def commit(self, review, selection_on):
        selection = setup_mod.Selection([(*self.item, selection_on)])
        entries = {cat: [] for cat in setup_mod.CATEGORIES}
        commit = setup_mod._make_wizard_commit(
            None, entries, False, {}, rules_env=self.env, rules_review=review)
        return commit, selection

    def test_no_review_without_a_replace(self):
        self.assertIsNone(setup_mod._global_rules_review(self.env))
        self.assertEqual(setup_mod._global_rules_items(None), ([], {}))

    def test_review_and_item_when_a_block_holds_the_installer_sentence(self):
        self.write_all()
        review = setup_mod._global_rules_review(self.env)
        assert review is not None
        self.assertEqual(len(review["changes"]), 4)
        items, initial = setup_mod._global_rules_items(review)
        self.assertEqual(items, [[*self.item, True]])
        self.assertEqual(initial, {self.item: False})

    def test_context_keeps_the_item_for_zero_one_and_two_hosts(self):
        self.write_all()
        review = setup_mod._global_rules_review(self.env)
        paths, entries, installed = self.inputs()
        for hosts in ((), ("claude",), ("claude", "cursor")):
            with self.subTest(hosts=hosts):
                ctx = setup_mod._build_wizard_context(
                    paths, entries, installed, wa, hosts=hosts, rules_review=review)
                self.assertEqual(len(ctx.hosts), len(hosts))
                self.assertIn(self.item, [(c, n) for c, n, _on in ctx.selection.items])
                self.assertFalse(ctx.state["_initial_enabled"][self.item])
                self.assertIs(ctx.state["_global_rules"], review)
                self.assertTrue(ctx.state["_global_rules"]["preview"])

    def test_context_without_a_review_has_no_item_and_no_state(self):
        paths, entries, installed = self.inputs()
        plain = setup_mod._build_wizard_context(paths, entries, installed, wa, hosts=())
        self.assertNotIn("_global_rules", plain.state)
        self.assertNotIn(self.item, [(c, n) for c, n, _on in plain.selection.items])

    def test_housekeeping_selection_keeps_the_item(self):
        self.write_all()
        review = setup_mod._global_rules_review(self.env)
        paths, entries, _installed = self.inputs()
        housekeeping = setup_mod._make_apply_housekeeping(
            paths, entries, [], [], False, {}, rules_review=review)
        result = housekeeping(False, False)
        self.assertIn(self.item, [(c, n) for c, n, _on in result["selection"].items])

    def test_commit_applies_only_when_the_item_is_on(self):
        self.write_all()
        review = setup_mod._global_rules_review(self.env)
        assert review is not None
        commit_off, sel_off = self.commit(review, False)
        commit_on, sel_on = self.commit(review, True)
        with mock.patch.object(setup_mod, "_commit_components", return_value=("", True)), \
                mock.patch.object(global_rules, "apply", return_value=(True, ["done"])) as apply:
            off = commit_off(sel_off, None)
            apply.assert_not_called()
            on = commit_on(sel_on, None)
        apply.assert_called_once()
        self.assertIs(apply.call_args.kwargs["reviewed"], review["changes"])
        self.assertTrue(off["ok"] and on["ok"])
        self.assertIn("done", on["log"])

    def test_commit_keeps_a_file_changed_after_review(self):
        self.write_all()
        review = setup_mod._global_rules_review(self.env)
        with open(self.paths["claude"], "ab") as fh:
            fh.write(b"edited")
        commit, selection = self.commit(review, True)
        with mock.patch.object(setup_mod, "_commit_components", return_value=("", True)):
            outcome = commit(selection, None)
        self.assertTrue(outcome["ok"])  # a reviewed-set skip is a note, not a failure
        self.assertIn("changed since it was reviewed", outcome["log"])
        self.assertTrue(self.read("claude").endswith(b"edited"))
        self.assertIn(global_rules.AIKIT_SENTENCE, self.read("gemini"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
