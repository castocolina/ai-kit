"""Install wizard view tests (tools/wizard_app.py), part 1 of 3.

Covers structural fidelity, Choose, the key help line, the adoption gate and Arrange moves.

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
    from rich.text import Text

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


def _luminance(hex_color):
    """WCAG relative luminance of a #rrggbb colour."""
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestHostBand(unittest.IsolatedAsyncioTestCase):
    """WIZ-02: each pane's band is its host accent with bold name text at >= 4.5:1 contrast."""

    def test_band_text_contrast_on_each_accent(self):
        text = _luminance(wa.BAND_TEXT)
        for host, accent in wa.HOST_ACCENTS.items():
            with self.subTest(host=host):
                hi, lo = sorted((_luminance(accent), text), reverse=True)
                self.assertGreaterEqual((hi + 0.05) / (lo + 0.05), 4.5)
        self.assertEqual(wa.HOST_ACCENTS, {"claude": "#D97757", "cursor": "#8B949E"})

    async def test_each_pane_band_uses_its_accent_and_bold_name(self):
        app = wa.WizardApp(make_ctx(host_ids=("claude", "cursor")))
        async with app.run_test() as pilot:
            await pilot.pause()
            for host in ("claude", "cursor"):
                await pilot.press("enter")          # Choose -> Claude pane -> Cursor pane
                await pilot.pause()
                name = query_static(app, "#band-name")
                self.assertTrue(str(name.content).startswith("[b]"))
                self.assertEqual(name.styles.background.hex.upper(), wa.HOST_ACCENTS[host])


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestChooseNameColumn(unittest.TestCase):
    """The 30-cell name column never runs into the description (UI-SPEC name column)."""

    def test_long_name_ends_in_ellipsis_and_one_space(self):
        cell = wa._name_cell("ai-kit-spec-execute-superpowers", 30)
        self.assertEqual(cell, "ai-kit-spec-execute-superpow… ")
        self.assertEqual(wa._name_cell("ai-kit-project-rules-precommit", 30)[-2:], "… ")

    def test_name_that_fits_is_padded_with_its_full_text(self):
        self.assertEqual(wa._name_cell("ai-kit-project-rules-makefile", 30),
                         "ai-kit-project-rules-makefile ")
        self.assertEqual(wa._name_cell("cst-refactor", 30), "cst-refactor".ljust(30))

    def test_row_keeps_a_gap_before_the_description(self):
        ctx = make_ctx()
        ctx.component_meta["ai-kit-spec-execute-superpowers"] = "Runs a plan"
        row = wa.WizardApp(ctx)._choose_component_row(
            "skills", "ai-kit-spec-execute-superpowers", True, False)
        self.assertIn("superpow… [/]", row)
        self.assertNotIn("superpowersRuns", row)

    def test_row_shows_the_frontmatter_name_and_the_linked_name_when_they_differ(self):
        ctx = make_ctx()._replace(component_titles={"cst-refactor": "CST refactor",
                                                    "ai-kit-judge.md": "ai-kit-judge"})
        ctx.component_meta["cst-refactor"] = "Codemods [b] that keep comments"
        app = wa.WizardApp(ctx)
        row = app._choose_component_row("skills", "cst-refactor", True, False)
        self.assertIn("CST refactor", row)
        # The folder that gets linked follows, dimmed; markup in a description is escaped.
        self.assertIn(f"[{wa.DIM}](cst-refactor) Codemods \\[b] that keep comments[/]", row)
        same = app._choose_component_row("agents", "ai-kit-judge.md", True, False)
        self.assertIn("ai-kit-judge ", same)
        self.assertNotIn("(ai-kit-judge.md)", same)
        fallback = app._choose_component_row("skills", "no-title-skill", True, False)
        self.assertIn("no-title-skill", fallback)
        self.assertNotIn("(no-title-skill)", fallback)


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestChooseCards(unittest.IsolatedAsyncioTestCase):
    """Choose: one card per kind that has items, each its own screen, walked with Enter / Esc."""

    def _title(self, app):
        return str(query_static(app, "#step-title").content)

    def _card(self, app):
        return str(query_static(app, "#picksbox").border_title)

    def _header(self, app):
        return str(query_static(app, "#header-right").content)

    async def test_card_title_and_border_and_no_tab_bar(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertIn("Choose skills to install", self._title(app))
            self.assertEqual(self._card(app), "skills 3/3")
            self.assertEqual(len(app.query("#kind-tabs")), 0)
            self.assertNotIn("agents", str(query_static(app, "#picksbox").content))

    async def test_enter_walks_the_cards_then_arrange(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test() as pilot:
            await pilot.pause()
            for kind, card in (("agents", "agents 1/1"), ("hooks", "hooks 1/2")):
                await pilot.press("enter")
                self.assertEqual(app.flow.step, wa.STEP_CHOOSE)
                self.assertIn(f"Choose {kind} to install", self._title(app))
                self.assertEqual(self._card(app), card)
            self.assertNotIn("commands", self._card(app))   # an empty kind has no card
            await pilot.press("enter")          # the last card continues to Arrange
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)

    async def test_escape_walks_back_and_is_a_noop_on_the_first_card(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter")  # hooks
            await pilot.press("escape")
            self.assertEqual(app.flow.kind, "agents")
            await pilot.press("escape")
            self.assertEqual(app.flow.kind, "skills")
            await pilot.press("escape")          # first card: nothing before it
            self.assertEqual((app.flow.step, app.flow.kind), (wa.STEP_CHOOSE, "skills"))

    async def test_arrows_left_right_do_not_switch_cards(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("right", "left", "right")
            self.assertEqual((app.flow.step, app.flow.kind), (wa.STEP_CHOOSE, "skills"))

    async def test_escape_from_arrange_lands_on_the_last_card(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter", "enter")
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)
            await pilot.press("escape")
            self.assertEqual((app.flow.step, app.flow.kind), (wa.STEP_CHOOSE, "hooks"))
            self.assertIn("Choose hooks to install", self._title(app))

    async def test_escape_from_review_with_zero_hosts_lands_on_the_last_card(self):
        app = wa.WizardApp(make_ctx_kinds(host_ids=()))
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter", "enter")
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            await pilot.press("escape")
            self.assertEqual((app.flow.step, app.flow.kind), (wa.STEP_CHOOSE, "hooks"))

    async def test_header_counts_three_cards_arrange_and_review(self):
        app = wa.WizardApp(make_ctx_kinds(host_ids=("claude", "cursor")))
        async with app.run_test() as pilot:
            await pilot.pause()
            for step in (1, 2, 3, 4, 4, 5):     # three cards, two host panes share 4, Review
                header = self._header(app)
                self.assertIn(f"Step {step} of 5", header)
                self.assertEqual((header.count("●"), header.count("○")), (step, 5 - step))
                await pilot.press("enter")
            app.flow.step = wa.STEP_DONE
            app._render()
            header = self._header(app)
            self.assertIn("Done", header)
            self.assertEqual(header.count("●"), 5)

    async def test_header_without_a_host_skips_arrange(self):
        app = wa.WizardApp(make_ctx_kinds(host_ids=()))
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertIn("Step 1 of 4", self._header(app))
            await pilot.press("enter", "enter", "enter")
            self.assertEqual(app.flow.step, wa.STEP_REVIEW)
            self.assertIn("Step 4 of 4", self._header(app))

    async def test_down_wraps_inside_card_and_each_card_keeps_its_cursor(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("down")
            self.assertEqual(app.model.sel.cursor, 1)
            await pilot.press("down")
            await pilot.press("down")           # three skills: wraps to the first
            self.assertEqual(app.model.sel.cursor, 0)
            await pilot.press("down")
            await pilot.press("enter")          # agents: its own cursor
            self.assertEqual(app.model.sel.items[app.model.sel.cursor][0], "agents")
            await pilot.press("escape")         # back to skills: cursor 1 remembered
            self.assertEqual(app.model.sel.cursor, 1)

    async def test_space_changes_only_its_card_and_review_counts(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter", "enter")  # hooks; cursor on tool-advisor
            await pilot.press("down")           # extra-hint (off)
            await pilot.press("space")
            self.assertEqual(self._card(app), "hooks 2/2")
            self.assertEqual(app._kind_counts("skills"), (3, 3))
            self.assertEqual(app._kind_counts("agents"), (1, 1))
            rows, _ncomp = app._review_component_rows()
            self.assertTrue(any("2/2: tool-advisor, extra-hint" in row for row in rows), rows)

    async def test_n_and_upper_n_and_upper_a(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("enter")          # agents, one item
            await pilot.press("n")
            self.assertEqual(app.model.sel.items[3][2], False)
            self.assertEqual(self._card(app), "agents 0/1")
            self.assertEqual(app._kind_counts("skills"), (3, 3))
            self.assertEqual(app._kind_counts("hooks"), (1, 2))
            await pilot.press("N")
            self.assertTrue(all(not on for _c, _n, on in app.model.sel.items))
            await pilot.press("A")
            self.assertTrue(all(on for _c, _n, on in app.model.sel.items))

    async def test_one_kind_catalog_has_one_card_and_enter_leaves(self):
        app = wa.WizardApp(make_ctx_kinds(items=[("skills", "brainstorming", True)]))
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertEqual(self._card(app), "skills 1/1")
            self.assertIn("Step 1 of 3", self._header(app))
            await pilot.press("escape")
            self.assertEqual(app.flow.step, wa.STEP_CHOOSE)
            await pilot.press("enter")
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)

    async def test_empty_catalog_shows_nothing_to_install_and_enter_leaves(self):
        app = wa.WizardApp(make_ctx_kinds(items=[]))
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertIn("nothing to install", str(query_static(app, "#picksbox").content))
            self.assertIn("Choose what to install", self._title(app))
            self.assertIn("Step 1 of 3", self._header(app))
            await pilot.press("enter")
            self.assertEqual(app.flow.step, wa.STEP_ARRANGE)

    async def test_tab_is_noop(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("tab")
            self.assertEqual((app.flow.step, app.flow.kind), (wa.STEP_CHOOSE, "skills"))

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


def _plain(app, wid):
    return Text.from_markup(str(query_static(app, wid).content)).plain


@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestKeyHelp(unittest.IsolatedAsyncioTestCase):
    """The sub-line under each title is built from HELP, so it lists every key the footer and
    the `?` panel name; both host panes show the same keys; tall screens group them."""

    async def _show(self, app, pilot, step, host_index=0):
        app.flow.step, app.flow.host_index = step, host_index
        if step == wa.STEP_ARRANGE:
            app.pane = app._pane(host_index)
        app._render()
        await pilot.pause()
        return _plain(app, "#step-sub")

    async def test_every_footer_and_help_key_is_in_the_sub_line(self):
        ctx = make_ctx_kinds(host_ids=("claude", "cursor"), global_rules=True)
        for rows in (24, 40):
            app = wa.WizardApp(ctx)
            async with app.run_test(size=(120, rows)) as pilot:
                await pilot.pause()
                for step in (wa.STEP_CHOOSE, wa.STEP_ARRANGE, wa.STEP_REVIEW):
                    sub = await self._show(app, pilot, step)
                    # With both hosts and the global-rules item, no key of the step is dropped.
                    self.assertEqual(app._key_rows(step), wa.HELP[step])
                    help_keys = {row.keys for row in wa.HELP[step]}
                    for _label, cap, _primary in [*wa.FOOTERS[step], (*wa.QUIT_KEY, False)]:
                        with self.subTest(rows=rows, step=step, footer=cap):
                            self.assertIn(cap, help_keys)
                            self.assertIn(f"{cap} ", sub)
                    for row in wa.HELP[step]:
                        with self.subTest(rows=rows, step=step, key=row.keys):
                            self.assertIn(f"{row.keys} {row.short}", sub)

    async def test_sub_line_redraw_without_the_sub_line_is_a_no_op(self):
        # The resize timer can fire after teardown removed the sub-line (seen in test_wizard_app_3).
        app = wa.WizardApp(make_ctx())
        async with app.run_test() as pilot:
            await pilot.pause()
            await app.query_one("#step-sub").remove()
            app._render_sub()  # pylint: disable=protected-access

    async def test_arrange_lists_o_tab_r_esc_and_the_cursor_keys_by_host_name(self):
        app = wa.WizardApp(make_ctx(host_ids=("claude", "cursor")))
        async with app.run_test(size=(120, 24)) as pilot:
            sub = await self._show(app, pilot, wa.STEP_ARRANGE, host_index=1)
            for text in ("o status line on/off", "Tab/⇧Tab next/prev chip",
                         "r reset to defaults", "Esc back", "Enter next host or Review",
                         "x Cursor extra-spend alert on/off"):
                self.assertIn(text, sub)
            self.assertNotIn("e Cursor", sub)
            self.assertNotIn("override", sub)

    async def test_claude_and_cursor_panes_show_the_same_help(self):
        app = wa.WizardApp(make_ctx(host_ids=("claude", "cursor")))
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            seen = []
            for index in (0, 1):
                sub = await self._show(app, pilot, wa.STEP_ARRANGE, host_index=index)
                await pilot.press("question_mark")
                seen.append((sub, _plain(app, "#help-box")))
                await pilot.press("question_mark")
            self.assertEqual(seen[0], seen[1])
            self.assertIn("Cursor: extra-spend alert", seen[0][1])

    async def test_a_claude_only_install_shows_no_cursor_key(self):
        app = wa.WizardApp(make_ctx())
        async with app.run_test(size=(120, 24)) as pilot:
            sub = await self._show(app, pilot, wa.STEP_ARRANGE)
            self.assertNotIn("Cursor", sub)

    async def test_review_shows_g_only_with_the_global_rules_item(self):
        app = wa.WizardApp(make_ctx_kinds())
        async with app.run_test(size=(120, 24)) as pilot:
            self.assertNotIn("g global rules", await self._show(app, pilot, wa.STEP_REVIEW))
        app = wa.WizardApp(make_ctx_kinds(global_rules=True))
        async with app.run_test(size=(120, 24)) as pilot:
            self.assertIn("g global rules", await self._show(app, pilot, wa.STEP_REVIEW))

    async def test_tall_screen_groups_the_keys_and_resize_switches_back(self):
        app = wa.WizardApp(make_ctx(host_ids=("claude", "cursor")))
        async with app.run_test(size=(120, wa.TALL_HELP_ROWS - 1)) as pilot:
            short = await self._show(app, pilot, wa.STEP_ARRANGE)
            self.assertNotIn("\n", short)
            self.assertNotIn("navigation", short)
            await pilot.resize_terminal(120, wa.TALL_HELP_ROWS)
            await pilot.pause(0.2)
            tall = _plain(app, "#step-sub").splitlines()
            self.assertTrue(tall[0].startswith("Focus is the [>chip<] brackets"))
            self.assertEqual([line.split()[0] for line in tall[1:]],
                             ["navigation", "edit", "status", "continue"])
            self.assertIn("o status line on/off", tall[3])
            await pilot.resize_terminal(120, wa.TALL_HELP_ROWS - 1)
            await pilot.pause(0.2)
            self.assertEqual(_plain(app, "#step-sub"), short)


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
