"""Install wizard view tests (tools/wizard_app.py), part 2 of 3.

Covers external segments, writeback, Review and Done, the in-UI commit and the chrome.

The wizard is a faithful port of docs/wizard-redesign/prototypes/mockup-textual.py. The three
parts run in parallel; the Textual guard and the Static helper live in
tests/wizard_app_common.py.
"""
import unittest

from tests.wizard_app_common import HAVE_TEXTUAL, query_static
from tools import wizard_app as wa

if HAVE_TEXTUAL:
    from tests.wizard_fixtures import make_ctx


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
            tray_text = str(query_static(app, "#tray").content)
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
                          str(query_static(app, "#cta").content))

    async def test_adopted_first_host_commits_even_when_last_host_declined(self):
        # Components exactly equal to _initial_enabled; Claude adopted at its
        # gate, Cursor declined at its gate (Cursor stays the active pane).
        # The earlier adoption is a net change on its own and must commit —
        # the declined active pane must not strand it (D-22).
        commits = []
        ctx = make_ctx(host_ids=("claude", "cursor"))._replace(
            commit=lambda selection, states: commits.append(states)
            or {"ok": True, "adopt": True, "log": "", "hosts": {}})
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("N")              # components == _initial_enabled
            await pilot.press("enter")          # choose → claude gate
            await pilot.press("y")              # adopt Claude
            await pilot.press("enter")          # claude arrange → cursor gate
            await pilot.press("n")              # decline Cursor → Review
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            await pilot.press("enter")          # review → must commit, not block
            self.assertEqual(app.flow.step, wa.STEP_DONE)
            self.assertEqual(len(commits), 1)
            self.assertIs(commits[0]["claude"]["adopt"], True)
            self.assertIs(commits[0]["cursor"]["adopt"], False)

    async def test_decline_omits_status_line_on_review_and_done(self):
        app = wa.WizardApp(make_ctx(sl_state="foreign"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange (gate)
            await pilot.press("n")              # decline → Review (arrange skipped)
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            # status-line preview panel is hidden; CTA & "what" omit segments
            self.assertFalse(query_static(app, "#rev-preview").display)
            self.assertNotIn("segments", str(query_static(app, "#cta").content))
            self.assertIn("left unchanged",
                          str(query_static(app, "#rev-what").content))
            await pilot.press("enter")          # commit (components are a net change)
            self.assertEqual(app.flow.step, wa.STEP_DONE)
            result = app.flow.result
            assert result is not None
            self.assertIs(result.state["claude"]["adopt"], False)
            sub = str(query_static(app, "#step-sub").content)
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
            self.assertIn("3[/] components", str(query_static(app, "#rev-what").content))
            self.assertIn("3 components", str(query_static(app, "#cta").content))

    async def test_accept_shows_status_line_on_review(self):
        app = wa.WizardApp(make_ctx(sl_state="unset"))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # choose → arrange (gate)
            await pilot.press("y")              # accept
            await pilot.press("enter")          # arrange → review
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            self.assertTrue(query_static(app, "#rev-preview").display)
            self.assertIn("segments", str(query_static(app, "#cta").content))


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
                "art": str(query_static(app, "#done-art").content),
                "next": str(query_static(app, "#done-next").content),
                "title": str(query_static(app, "#step-title").content),
                "sub": str(query_static(app, "#step-sub").content),
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
            right = str(query_static(app, "#header-right").content)
            self.assertEqual(right.count("●") + right.count("○"), 3)

    async def test_done_header_all_green(self):
        app = wa.WizardApp(make_ctx())
        async with app.run_test() as pilot:
            app.flow.step = wa.STEP_DONE
            app._render()
            await pilot.pause()
            right = str(query_static(app, "#header-right").content)
            self.assertEqual(right.count("●"), 3)
            self.assertIn(wa.GREEN, right)

    async def test_footer_matches_step(self):
        app = wa.WizardApp(make_ctx())
        async with app.run_test() as pilot:
            await pilot.pause()
            left = str(query_static(app, "#footer-left").content)
            for _label, cap, _primary in wa.FOOTERS[wa.STEP_CHOOSE]:
                self.assertIn(cap, left)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
