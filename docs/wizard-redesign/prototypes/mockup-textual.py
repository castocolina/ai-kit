# /// script
# requires-python = ">=3.10"
# dependencies = ["textual==8.2.7"]
# ///
"""Prototype — the Textual install wizard, a faithful .py port of mockup-textual.html.

Run:        uv run --script mockup-textual.py
Self-test:  uv run --script mockup-textual.py --selftest   (headless)

Same wizard as the HTML mockup, as a real Textual TUI — and now matching the
HTML's RICHNESS: a bordered header bar and a footer key-bar with emphasized
keycaps, bordered panels for every area (each status-line LANE, a dedicated OFF
tray, a live-preview panel with its own background, and a focused-chip detail
panel), fr-based responsive two-column layout, and pink-bracket chip focus.

It is a PROTOTYPE: writes NOTHING to disk and does NOT import tools/setup.py.
Data comes from the sibling _protodata.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _protodata as D  # noqa: E402

from textual import events  # noqa: E402
from textual.app import App, ComposeResult  # noqa: E402
from textual.containers import Container, Horizontal, Vertical, VerticalScroll  # noqa: E402
from textual.widgets import Static  # noqa: E402

# ---- palette lifted verbatim from mockup-textual.html :root -----------------
FG = "#c9d1d9"
DIM = "#6e7681"
LINE = "#30363d"
ACCENT = "#58a6ff"
GREEN = "#3fb950"
WARN = "#d29922"
PINK = "#db61a2"
CYAN = "#39c5cf"
KEYCAP = "#21262d"

# One-line copy the data module doesn't carry.
SEG_DESC = {
    "path": "Current working directory", "git_branch": "Active git branch",
    "alt_git_worktree": "Git worktree name (alt)", "git_dirty": "Uncommitted change count",
    "todo": "Open todo count", "model": "Active Claude model",
    "alt_time_ago": "Time since last message", "alt_time_clock": "Wall-clock time",
    "effort": "Reasoning effort level", "lines": "Lines added / removed",
    "alt_cost": "Session cost (USD)", "alt_time_session": "Session duration",
    "alt_time_api": "Last API latency", "render_time": "Status-line render time",
    "slowest": "Slowest segment", "alt_term_dimensions": "Terminal dimensions",
    "context": "Context window used", "chat_size": "Transcript load time",
    "alt_process_memory": "Agent process memory", "alt_rate_limits": "Rate-limit status",
}
ITEM_DESC = {
    "ui-ux-designer": "Design critique agent",
    "mermaid-diagram-specialist": "Diagram generator agent",
    "code-reviewer": "Code review agent",
    "code-review": "Review the current branch",
    "gsd-plan-phase": "Plan a project phase",
    "brainstorm": "Brainstorm ideas into a design",
    "brainstorming": "Idea → design skill",
    "writing-plans": "Write implementation plans",
    "markdown-to-pdf": "Render markdown to PDF",
    "subagent-driven-development": "Execute plans via subagents",
}

STEP_CHOOSE, STEP_ARRANGE, STEP_REVIEW, STEP_DONE = 0, 1, 2, 3
LANE_GATE = {1: 20, 2: 30}  # Line 2 needs ≥20 rows, Line 3 needs ≥30

# footer key-bar per step: (label, cap, primary?)  — order matches the HTML
FOOTERS = [
    [("Continue", "Enter", True), ("Toggle", "Space", False), ("Move", "↑↓", False),
     ("Category", "a/n", False), ("Help", "?", False)],
    [("Continue", "Enter", True), ("Back", "Esc", False), ("Move", "←→", False),
     ("Line", "↑↓", False), ("On/off", "Space", False), ("Reset", "r", False),
     ("Help", "?", False)],
    [("Install", "Enter", True), ("Back", "Esc", False), ("Help", "?", False)],
    [("Finish & exit", "Enter", True)],
]
QUIT_KEY = ("Quit", "q")

HELP = {
    STEP_CHOOSE: [("↑ ↓", "Move the highlight between components"),
                  ("Space", "Install / skip the highlighted component"),
                  ("a / n", "Select all / none in the current category"),
                  ("A / N", "Select all / none across every category"),
                  ("Enter", "Continue to Arrange"), ("q", "Quit the installer")],
    STEP_ARRANGE: [("← →", "Reorder the focused chip within its line"),
                   ("↑ ↓", "Move the chip across lines (↑ off Line 1 → OFF tray)"),
                   ("Space", "Turn the focused segment on/off (off → tray)"),
                   ("Tab / ⇧Tab", "Focus the next / previous chip"),
                   ("r", "Reset the layout to defaults"),
                   ("Enter / Esc", "Continue to Review / back to Choose"),
                   ("q", "Quit the installer")],
    STEP_REVIEW: [("Enter", "Install (prototype — nothing is written)"),
                  ("Esc", "Back to Arrange"), ("q", "Quit")],
    STEP_DONE: [("Enter", "Finish and exit"), ("q", "Quit")],
}


TITLES = ["Choose what to install", "Arrange your status line",
          "Review & confirm", "✓ ai-kit is installed"]
SUBS = [
    "↑↓ move · Space toggle · ◉ install · ◯ skip · a/n this category · "
    "A/N everything · ? help",
    f"Focus is the [{PINK}]\\[>chip<][/] brackets. ←→ move within a line · "
    "↑↓ across lines (↑ off Line 1 → OFF tray) · Space turns on/off · "
    "Tab/⇧Tab next/prev chip · r reset to defaults · ? help. "
    "The preview at the bottom updates live.",
    "Nothing has been written yet. Confirm to apply.",
    "",  # Done's sub is built dynamically with the run counts
]


def _pad(s: str, n: int) -> str:
    return s if len(s) >= n else s + " " * (n - len(s))


class WizardApp(App):
    ENABLE_COMMAND_PALETTE = False
    CSS = f"""
    Screen {{ background: #0d1117; }}

    #headerbar {{ height: 2; background: #161b22; border-bottom: solid {LINE}; padding: 0 1; }}
    #header-title {{ width: 1fr; color: {ACCENT}; text-style: bold; content-align: left middle; }}
    #header-right {{ width: auto; color: {DIM}; content-align: right middle; }}

    #bodywrap {{ height: 1fr; padding: 1 2; }}
    #step-title {{ height: auto; text-style: bold; }}
    #step-sub {{ height: auto; color: {DIM}; margin-bottom: 1; }}
    #step-arrange {{ height: 1fr; }}
    #board {{ width: 1fr; height: auto; }}

    .lane {{ border: round {CYAN}; height: auto; padding: 0 1; margin-bottom: 1;
            background: #0f141b; border-title-color: {CYAN}; }}
    .lane.gated {{ border: dashed {CYAN}; border-subtitle-color: {WARN}; }}
    #focchip {{ border: round {PINK}; background: #1b1016; height: auto; padding: 0 1;
               margin-bottom: 1; border-title-color: {PINK}; }}
    #tray {{ border: dashed {DIM}; height: auto; padding: 0 1; margin-bottom: 1;
            background: #0d1117; border-title-color: {DIM}; }}
    #preview {{ border: round {LINE}; background: #010409; height: auto; padding: 0 1;
               border-title-color: {DIM}; }}

    #picksbox {{ border: round {LINE}; background: #0f141b; height: auto; padding: 0 1;
                border-title-color: {DIM}; }}
    #picksCount {{ padding: 1 0 0 0; }}

    .rbox {{ border: round {LINE}; background: #0f141b; height: auto; padding: 0 1;
            margin-bottom: 1; border-title-color: {DIM}; }}
    #rev-preview {{ background: #010409; }}
    #cta {{ border: round {GREEN}; background: #0c1f12; height: auto; padding: 0 1; }}
    #done-art {{ height: auto; padding: 1 0; }}

    #footerbar {{ height: 2; background: #010409; border-top: solid {LINE}; padding: 0 1; }}
    #footer-left {{ width: 1fr; content-align: left middle; }}
    #footer-q {{ width: auto; content-align: right middle; }}
    """

    def __init__(self) -> None:
        super().__init__()
        self.step = STEP_CHOOSE
        self.help_open = False
        self.picks = D.default_picks()
        self.cat_order = list(self.picks.keys())
        self.rows = [(c, name) for c in self.cat_order for name in self.picks[c]]
        self.row_i = 0
        self._reset_layout()
        # each segment's ideal "home" line (stands in for the inventory `line`)
        self.home_line = {seg: li for li, line in enumerate(D.LAYOUT) for seg in line}

    # ---- layout state ----------------------------------------------------
    def _reset_layout(self) -> None:
        self.lines = [[s for s in line if D.DEFAULT_ON[s]] for line in D.LAYOUT]
        self.tray = [s for s in D.ALL_SEGMENTS if not D.DEFAULT_ON[s]]
        self.focus_zp = (0, 0)

    def _zones(self):
        return [self.lines[0], self.lines[1], self.lines[2], self.tray]

    def _clamp_focus(self) -> None:
        z, p = self.focus_zp
        z = max(0, min(3, z))
        if not self._zones()[z]:
            z = next((k for k in range(4) if self._zones()[k]), 0)
        zone = self._zones()[z]
        self.focus_zp = (z, max(0, min(len(zone) - 1, p)) if zone else 0)

    def _preview(self):
        out = []
        for ln in self.lines:
            parts = [f"{D.ICON[s]} {D.SAMPLE[s]}" for s in ln]
            if parts:
                out.append(f" [{LINE}]|[/] ".join(parts))
        return out or [f"[{DIM}](all segments off)[/]"]

    # ---- compose ---------------------------------------------------------
    def compose(self) -> ComposeResult:
        with Horizontal(id="headerbar"):
            yield Static("─ ai-kit install wizard", id="header-title")
            yield Static("", id="header-right")

        with Container(id="bodywrap"):
            yield Static("", id="step-title")
            yield Static("", id="step-sub")
            with VerticalScroll(id="step-choose"):
                pb = Static("", id="picksbox")
                pb.border_title = "select components"
                yield pb
                yield Static("", id="picksCount")

            with Vertical(id="step-arrange"):
                with Vertical(id="board"):
                    for i in range(3):
                        lane = Static("", id=f"lane{i}",
                                      classes="lane" + (" gated" if i in LANE_GATE else ""))
                        lane.border_title = f"Line {i + 1}"
                        if i in LANE_GATE:
                            lane.border_subtitle = f"needs ≥ {LANE_GATE[i]} rows"
                        yield lane
                fc = Static("", id="focchip")
                fc.border_title = "focused chip"
                yield fc
                tray = Static("", id="tray")
                tray.border_title = "OFF — disabled  (Space activates → its home line)"
                yield tray
                pv = Static("", id="preview")
                pv.border_title = "live preview  (full width — like the real status line)"
                yield pv

            with VerticalScroll(id="step-review"):
                rc = Static("", id="rev-components", classes="rbox")
                rc.border_title = "components to install"
                yield rc
                rp = Static("", id="rev-preview", classes="rbox")
                rp.border_title = "status line"
                yield rp
                rw = Static("", id="rev-what", classes="rbox")
                rw.border_title = "what happens on confirm"
                yield rw
                yield Static("", id="cta")

            with VerticalScroll(id="step-done"):
                yield Static("", id="done-art")
                dn = Static("", id="done-next", classes="rbox")
                dn.border_title = "next"
                yield dn

            with VerticalScroll(id="step-help"):
                hb = Static("", id="help-box", classes="rbox")
                hb.border_title = "keys"
                yield hb

        with Horizontal(id="footerbar"):
            yield Static("", id="footer-left")
            yield Static("", id="footer-q")

    def on_mount(self) -> None:
        self._render()

    # ---- render ----------------------------------------------------------
    def _render(self) -> None:
        self._render_header()
        self._render_footer()
        steps = {STEP_CHOOSE: "step-choose", STEP_ARRANGE: "step-arrange",
                 STEP_REVIEW: "step-review", STEP_DONE: "step-done"}
        for sid in steps.values():
            self.query_one(f"#{sid}").display = False
        self.query_one("#step-help").display = self.help_open
        title_w = self.query_one("#step-title", Static)
        sub_w = self.query_one("#step-sub", Static)
        title_w.display = sub_w.display = not self.help_open
        if self.help_open:
            self._render_help()
            return
        color = GREEN if self.step == STEP_DONE else "#f0f6fc"
        title_w.update(f"[{color}]{TITLES[self.step]}[/]")
        if self.step == STEP_DONE:
            ncomp = sum(sum(v.values()) for v in self.picks.values())
            nseg = sum(len(line) for line in self.lines)
            nlines = sum(1 for line in self.lines if line)
            sub_w.update(f"[{DIM}]{ncomp} components · {nseg} segments · "
                         f"{nlines} lines — nothing was written to disk[/]")
        else:
            sub_w.update(SUBS[self.step])
        self.query_one(f"#{steps[self.step]}").display = True
        (self._render_choose, self._render_arrange,
         self._render_review, self._render_done)[self.step]()

    def _render_header(self) -> None:
        if self.step < STEP_DONE:
            pips = " ".join(f"[{ACCENT}]●[/]" if k <= self.step else f"[{LINE}]○[/]"
                            for k in range(3))
            label = f"[{DIM}]Step {self.step + 1} of 3[/]"
        else:
            pips = " ".join(f"[{GREEN}]●[/]" for _ in range(3))
            label = f"[{GREEN}]Done[/]"
        self.query_one("#header-right", Static).update(f"{label}    {pips}")

    def _cap(self, label: str, cap: str, primary: bool) -> str:
        if primary:
            pill = f"[#cae3ff on #10325c] {cap} [/]"
            return f"{pill} [#cae3ff]{label}[/]"
        pill = f"[#e6edf3 on {KEYCAP}] {cap} [/]"
        return f"{pill} [{DIM}]{label}[/]"

    def _render_footer(self) -> None:
        sep = f"   [{LINE}]│[/]   "
        left = sep.join(self._cap(*k) for k in FOOTERS[self.step])
        self.query_one("#footer-left", Static).update(left)
        self.query_one("#footer-q", Static).update(self._cap(*QUIT_KEY, False))

    def _render_help(self) -> None:
        title = ["Choose", "Arrange", "Review", "Done"][self.step]
        rows = "\n".join(f"[#e6edf3 on {KEYCAP}] {_pad(k, 12)}[/]  {d}"
                         for k, d in HELP[self.step])
        self.query_one("#help-box", Static).update(
            f"[bold {ACCENT}]{title} — keys[/]\n\n{rows}\n\n[{DIM}]? or Esc to close[/]")

    def _render_choose(self) -> None:
        out, idx, last = [], 0, None
        cur_cat = self.rows[self.row_i][0]
        for (c, name) in self.rows:
            if c != last:
                on = sum(self.picks[c].values())
                hint = f"[{GREEN}]{on}[/]/{len(self.picks[c])} on"
                if c == cur_cat:
                    hint += f"   [{DIM}]· a all · n none[/]"
                out.append(f"[{CYAN}]▌ {c.upper()}[/]   {hint}")
                last = c
            sel = self.picks[c][name]
            foc = idx == self.row_i
            glyph = f"[{GREEN}]◉[/]" if sel else f"[{DIM}]◯[/]"
            gut = f"[{PINK}]▌[/]" if foc else " "
            nm = _pad(name, 30)
            row = (f"{gut} {glyph} [{'#f0f6fc' if foc else FG}]{nm}[/]"
                   f"[{DIM}]{ITEM_DESC.get(name, '')}[/]")
            out.append(f"[on #161b22]{row}[/]" if foc else row)
            idx += 1
        self.query_one("#picksbox", Static).update("\n".join(out))
        sel_n = sum(sum(v.values()) for v in self.picks.values())
        self.query_one("#picksCount", Static).update(
            f"[{GREEN}]{sel_n}[/] of {len(self.rows)} components selected")

    def _chip(self, seg: str, focused: bool, parked: bool) -> str:
        label = f"{D.ICON[seg]} {seg}"
        if focused:
            return (f"[{PINK}]\\[>[/][bold #ffffff on #1b1016]{label}[/]"
                    f"[{PINK}]<][/]")
        col = DIM if parked else FG
        return f"[{col} on #0d1117] {label} [/]"

    def _render_arrange(self) -> None:
        self._clamp_focus()
        zones = self._zones()
        for li in range(3):
            chips = [self._chip(s, self.focus_zp == (li, ci), False)
                     for ci, s in enumerate(zones[li])]
            self.query_one(f"#lane{li}", Static).update(
                "  ".join(chips) if chips else f"[{DIM}](empty)[/]")
        tray_chips = [self._chip(s, self.focus_zp == (3, ci), True)
                      for ci, s in enumerate(self.tray)]
        self.query_one("#tray", Static).update(
            "  ".join(tray_chips) if tray_chips else f"[{DIM}](none — every segment is on a line)[/]")
        fz, fp = self.focus_zp
        zone = zones[fz]
        if zone:
            seg = zone[fp]
            state = "off · in tray" if fz == 3 else f"on · Line {fz + 1}"
            self.query_one("#focchip", Static).update(
                f"[#f0f6fc]{D.ICON[seg]} [bold]{seg}[/][/]\n"
                f"[{DIM}]{SEG_DESC.get(seg, '')}[/]\n[{DIM}]{state}[/]")
        on_count = sum(len(line) for line in self.lines)
        self.query_one("#preview", Static).update(
            "\n".join(f"[#d6dee8]{p}[/]" for p in self._preview())
            + f"\n[{DIM}]{on_count} on · {len(self.tray)} off[/]")

    def _render_review(self) -> None:
        rows = []
        for c in self.cat_order:
            chosen = [n for n, v in self.picks[c].items() if v]
            rows.append(f"[{CYAN}]{c}[/]: "
                        + (", ".join(chosen) if chosen else f"[{DIM}](none)[/]"))
        self.query_one("#rev-components", Static).update("\n".join(rows))
        self.query_one("#rev-preview", Static).update(
            "\n".join(f"[#d6dee8]{p}[/]" for p in self._preview()))
        ncomp = sum(sum(v.values()) for v in self.picks.values())
        nseg = sum(len(line) for line in self.lines)
        self.query_one("#rev-what", Static).update(
            f"[{DIM}]•[/] Symlink [bold]{ncomp}[/] components into "
            f"~/.claude/(agents|commands|skills)/\n"
            f"[{DIM}]•[/] Write your status line ([bold]{nseg}[/] segments) to "
            f"~/.claude/statusline.toml\n"
            f"[{DIM}]•[/] Validate with statusline-doctor before saving\n"
            f"[{WARN}]Prototype:[/] this run writes nothing to disk.")
        self.query_one("#cta", Static).update(
            f"▸ [bold #7ee2a0]Install ai-kit[/]  [{DIM}]{ncomp} components · "
            f"{nseg} segments[/]   [#d6ffe4 on #10421f] Enter [/]")

    def _render_done(self) -> None:
        self.query_one("#done-art", Static).update(
            f"[{GREEN}]┌─┐ ┬[/]\n[{GREEN}]├─┤ │[/]\n[{GREEN}]┴ ┴ ┴[/] ─kit")
        self.query_one("#done-next", Static).update(
            f"[{DIM}]•[/] Open a new Claude Code session to see your status line.\n"
            f"[{DIM}]•[/] Re-run  uv run tools/setup.py  any time to change picks.\n"
            f"[{DIM}]•[/] Tweak segments later in  ~/.claude/statusline.toml.")

    # ---- input -----------------------------------------------------------
    def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+c":
            return
        if event.character == "?":
            self.help_open = not self.help_open
            self._render()
            event.stop(); return
        if self.help_open:
            if event.key == "escape":
                self.help_open = False
                self._render()
            event.stop(); return
        if event.character == "q":
            self.exit(); return
        handled = (self._key_choose, self._key_arrange,
                   self._key_review, self._key_done)[self.step](event)
        if handled:
            event.stop()
            self._render()

    def _key_choose(self, event: events.Key) -> bool:
        ch, k = event.character, event.key
        n = len(self.rows)
        if k == "up":
            self.row_i = (self.row_i - 1) % n
        elif k == "down":
            self.row_i = (self.row_i + 1) % n
        elif k == "space":
            c, name = self.rows[self.row_i]
            self.picks[c][name] = not self.picks[c][name]
        elif ch in ("a", "n"):
            c = self.rows[self.row_i][0]
            for name in self.picks[c]:
                self.picks[c][name] = ch == "a"
        elif ch in ("A", "N"):
            for v in self.picks.values():
                for name in v:
                    v[name] = ch == "A"
        elif k == "enter":
            self.step = STEP_ARRANGE
        else:
            return False
        return True

    def _key_arrange(self, event: events.Key) -> bool:
        ch, k = event.character, event.key
        z, p = self.focus_zp
        zone = self._zones()[z]
        if k == "left" and z != 3 and zone and p > 0:  # z==3 is OFF tray — not movable
            zone[p - 1], zone[p] = zone[p], zone[p - 1]
            self.focus_zp = (z, p - 1)
        elif k == "right" and z != 3 and zone and p < len(zone) - 1:
            zone[p + 1], zone[p] = zone[p], zone[p + 1]
            self.focus_zp = (z, p + 1)
        elif k in ("up", "down"):
            self._move_chip_v("up" if k == "up" else "down")
        elif k == "space":
            self._toggle_chip()
        elif k == "tab":
            self._cycle_focus(+1)
        elif k == "shift+tab":
            self._cycle_focus(-1)
        elif ch == "r":
            self._reset_layout()
        elif k == "enter":
            self.step = STEP_REVIEW
        elif k == "escape":
            self.step = STEP_CHOOSE
        else:
            return False
        return True

    def _move_chip_v(self, direction: str) -> None:
        z, p = self.focus_zp
        zone = self._zones()[z]
        if not zone:
            return
        up_map = {0: 3, 1: 0, 2: 1, 3: None}      # ↑: Line1→tray (disable), else up a line
        down_map = {3: None, 0: 1, 1: 2, 2: None}  # disabled chips don't move out via ↓
        target = (up_map if direction == "up" else down_map)[z]
        if target is None:
            return
        seg = zone.pop(p)
        self._zones()[target].append(seg)
        self.focus_zp = (target, len(self._zones()[target]) - 1)

    def _toggle_chip(self) -> None:
        z, p = self.focus_zp
        zone = self._zones()[z]
        if not zone:
            return
        seg = zone.pop(p)
        if z == 3:  # off -> on -> its inventory "home" line (not a fixed Line 1)
            home = self.home_line.get(seg, 0)
            self.lines[home].append(seg)
            self.focus_zp = (home, len(self.lines[home]) - 1)
        else:
            self.tray.append(seg)
            self.focus_zp = (3, len(self.tray) - 1)

    def _cycle_focus(self, direction: int) -> None:
        z, p = self.focus_zp
        zone = self._zones()[z]
        if zone and 0 <= p + direction < len(zone):
            self.focus_zp = (z, p + direction)
            return
        for step in range(1, 5):
            nz = (z + direction * step) % 4
            tgt = self._zones()[nz]
            if tgt:
                self.focus_zp = (nz, 0 if direction > 0 else len(tgt) - 1)
                return

    def _key_review(self, event: events.Key) -> bool:
        if event.key == "enter":
            self.step = STEP_DONE
        elif event.key == "escape":
            self.step = STEP_ARRANGE
        else:
            return False
        return True

    def _key_done(self, event: events.Key) -> bool:
        if event.key == "enter":
            self.exit()
            return True
        return False


def _selftest() -> None:
    import asyncio

    async def run() -> None:
        app = WizardApp()
        async with app.run_test() as pilot:
            await pilot.press("down", "space", "a", "enter")
            assert app.step == STEP_ARRANGE, app.step
            await pilot.press("right", "down", "space", "tab", "shift+tab", "r")
            await pilot.press("enter")
            assert app.step == STEP_REVIEW, app.step
            await pilot.press("question_mark", "question_mark")
            await pilot.press("enter")
            assert app.step == STEP_DONE, app.step
    asyncio.run(run())
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        WizardApp().run()
