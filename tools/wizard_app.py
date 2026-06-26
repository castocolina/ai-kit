"""Textual install wizard for ai-kit — a faithful port of the locked prototype
``docs/wizard-redesign/prototypes/mockup-textual.py``.

This is the pure view layer (the A.4 seam): it imports NOTHING from
``tools/setup.py``.  Every piece of data and behaviour the wizard needs arrives
through an injected ``WizardContext`` — the selection model, segment metadata,
external segments, component descriptions, status-line adoption state, and the
initial layout/segment state.  ``setup.py.launch_wizard`` builds the context,
calls ``run_wizard(ctx)``, and consumes the returned ``WizardResult`` (or
``None`` on a clean abort).  The structure here mirrors the prototype's single
``WizardApp`` exactly: a ``#headerbar`` (title + step pips), a ``#bodywrap`` with
one panel group per step, and a ``#footerbar`` key bar; ``_render()`` toggles
``.display`` per step.  The prototype's ``_protodata`` source is replaced by
``ctx``; the widget tree, CSS, and key handling are otherwise ported verbatim.
"""
from __future__ import annotations

import shutil
from typing import NamedTuple

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Static

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
    STEP_REVIEW: [("Enter", "Install / write the config"),
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


# ---------------------------------------------------------------------------
# Public data types (the seam — consumed/produced across setup.py)
# ---------------------------------------------------------------------------

class WizardResult(NamedTuple):
    """Returned by run_wizard on confirm; None on abort."""
    selection: object  # tools.setup.Selection — kept as `object` so wizard_app
                       # stays free of any import from setup.py.
    state: dict


class WizardContext(NamedTuple):
    """All data and behaviour the wizard needs, injected by setup.py at
    call-time.  wizard_app imports nothing from setup.py; this is the seam."""
    selection: object           # setup.Selection instance
    state: dict                 # {"segments": {key: bool}, "layout": [...],
                                #  "dirty": bool, "adopt": bool}
    sample_json: str            # rendered sample input JSON for preview
    engine: object                   # callables: render_preview, apply_command, groups, order
    # New Plan-A fields (Task 10) — always populated by setup.py.launch_wizard.
    status_line: dict           # {"state": str, "current_command": str | None}
    segment_meta: dict          # {key: {description, sample, icon, line}}
    external_segments: list     # [{id, name, path, default_on, description,
                                #   icon, sample, line, provenance}, …]
    component_meta: dict          # {name: description} across all CATEGORIES


class WizardCrash(Exception):
    """Raised by run_wizard when the Textual app exits due to an unhandled
    exception.

    Textual 8.x swallows unhandled exceptions (stores in app._exception and
    triggers a graceful shutdown rather than propagating).  run_wizard checks
    app._exception after app.run() returns and re-signals it as WizardCrash
    so callers can distinguish a crash from a clean user abort (None result).

    The original exception is available as __cause__ (via ``raise … from``).
    """


# Minimum terminal dimensions required to enter the alternate screen.
# Any sane terminal (80×24) is well above these; they exist to catch
# CI / headless / pipe mis-uses early, before the TUI messes up the screen.
_MIN_TERMINAL_COLS: int = 40
_MIN_TERMINAL_ROWS: int = 10


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

    def __init__(self, ctx: WizardContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.sel = ctx.selection
        self.meta = ctx.segment_meta
        self.ext_by_id = {e["id"]: e for e in ctx.external_segments}
        self.state = dict(ctx.state)            # adopt, _initial_enabled, dirty, segments, layout
        self.result: WizardResult | None = None
        self._exception: BaseException | None = None
        self.step = STEP_CHOOSE
        self.help_open = False
        # adoption gate: 'ours' adopts silently; otherwise the gate is shown on Arrange entry
        self.gate_done = ctx.status_line.get("state") == "ours"
        if self.gate_done:
            self.state["adopt"] = True
        # min_rows per lane, captured from the initial layout (fallback 0/20/30)
        rows = [r.get("min_rows", 0) for r in self.state["layout"]]
        self._min_rows = [*rows, 0, 20, 30][:3]
        # home line (0-based) per segment: built-ins from inventory; externals → last lane
        self.home_line = {k: min(max(int(m.get("line", 0)), 0), 2)
                          for k, m in self.meta.items()}
        for e in ctx.external_segments:
            self.home_line[e["id"]] = 2
        self._build_lists_from_state()
        # immutable snapshot for 'r' reset
        self._initial_lines = [list(x) for x in self.lines]
        self._initial_tray = list(self.tray)

    # ---- model -----------------------------------------------------------
    def _build_lists_from_state(self) -> None:
        segs = self.state["segments"]
        self.lines = [[], [], []]
        placed = set()
        for i, row in enumerate(self.state["layout"][:3]):
            for seg in row["segments"]:
                if segs.get(seg) and seg not in placed:
                    self.lines[i].append(seg)
                    placed.add(seg)
        # ON segments not in any layout row (e.g. an enabled external): home line
        for seg, on in segs.items():
            if on and seg not in placed:
                self.lines[self.home_line.get(seg, 2)].append(seg)
                placed.add(seg)
        # tray = every OFF segment, in stable state-key order (built-ins then externals)
        self.tray = [seg for seg in segs if not segs.get(seg)]
        self.focus_zp = (0, 0)

    # ---- metadata accessors ---------------------------------------------
    def _icon(self, seg: str) -> str:
        if seg in self.ext_by_id:
            return self.ext_by_id[seg].get("icon") or "●"
        return self.meta.get(seg, {}).get("icon", "")

    def _sample(self, seg: str) -> str:
        if seg in self.ext_by_id:
            return self.ext_by_id[seg].get("sample", "")
        return self.meta.get(seg, {}).get("sample", "")

    def _desc(self, seg: str) -> str:
        if seg in self.ext_by_id:
            return self.ext_by_id[seg].get("description", "")
        return self.meta.get(seg, {}).get("description", "")

    def _component_desc(self, cat: str, name: str) -> str:  # pylint: disable=unused-argument
        # `cat` keeps the prototype's (cat, name) accessor shape; lookup is by name.
        return self.ctx.component_meta.get(name, "")  # populated by Task 1's _read_component_desc

    # ---- layout state ----------------------------------------------------
    def _reset_layout(self) -> None:
        self.lines = [list(x) for x in self._initial_lines]
        self.tray = list(self._initial_tray)
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
            parts = [f"{self._icon(s)} {self._sample(s)}" for s in ln]
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

    def on_exception(self, exception: BaseException) -> None:
        """Textual lifecycle hook — capture the unhandled exception so that
        run_wizard can re-raise it as WizardCrash after app.run() returns."""
        self._exception = exception
        self.exit()

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
            ncomp = sum(1 for _c, _n, on in self.sel.items if on)
            nseg = sum(len(line) for line in self.lines)
            nlines = sum(1 for line in self.lines if line)
            sub_w.update(f"[{DIM}]{ncomp} components · {nseg} segments · "
                         f"{nlines} lines — your status line is ready[/]")
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
        items = self.sel.items
        cur_cat = items[self.sel.cursor][0] if items else None
        # category groups in first-appearance order over self.sel.items
        cats: list[str] = []
        by_cat: dict[str, list[int]] = {}
        for idx, (c, _name, _on) in enumerate(items):
            if c not in by_cat:
                cats.append(c)
                by_cat[c] = []
            by_cat[c].append(idx)
        out = []
        for c in cats:
            idxs = by_cat[c]
            on = sum(1 for i in idxs if items[i][2])
            hint = f"[{GREEN}]{on}[/]/{len(idxs)} on"
            if c == cur_cat:
                hint += f"   [{DIM}]· a all · n none[/]"
            out.append(f"[{CYAN}]▌ {c.upper()}[/]   {hint}")
            for i in idxs:
                _c2, name, sel = items[i]
                foc = i == self.sel.cursor
                glyph = f"[{GREEN}]◉[/]" if sel else f"[{DIM}]◯[/]"
                gut = f"[{PINK}]▌[/]" if foc else " "
                nm = _pad(name, 30)
                row = (f"{gut} {glyph} [{'#f0f6fc' if foc else FG}]{nm}[/]"
                       f"[{DIM}]{self._component_desc(c, name)}[/]")
                out.append(f"[on #161b22]{row}[/]" if foc else row)
        self.query_one("#picksbox", Static).update("\n".join(out))
        sel_n = sum(1 for _c, _n, on in items if on)
        self.query_one("#picksCount", Static).update(
            f"[{GREEN}]{sel_n}[/] of {len(items)} components selected")

    def _chip(self, seg: str, focused: bool, parked: bool) -> str:
        is_ext = seg in self.ext_by_id
        label = f"{self._icon(seg)} {seg}"
        if is_ext:
            label = f"◆ {label}"             # external marker
        if focused:
            return (f"[{PINK}]\\[>[/][bold #ffffff on #1b1016]{label}[/]"
                    f"[{PINK}]<][/]")
        col = CYAN if is_ext else (DIM if parked else FG)
        return f"[{col} on #0d1117] {label} [/]"

    def _render_arrange(self) -> None:
        if not self.gate_done:
            sl = self.ctx.status_line
            if sl.get("state") == "foreign":
                cmd = sl.get("current_command") or "(unknown)"
                gate = (f"[{WARN}]Existing status line detected.[/]\n"
                        f"[{DIM}]Current:[/] {cmd}\n\nReplace with ai-kit?  [y/N]")
            else:
                gate = "Wire your status line?  [Y/n]"
            self.query_one("#lane0", Static).update(gate)
            for wid in ("#lane1", "#lane2", "#focchip", "#tray", "#preview"):
                self.query_one(wid, Static).update("")
            return
        self._clamp_focus()
        zones = self._zones()
        for li in range(3):
            chips = [self._chip(s, self.focus_zp == (li, ci), False)
                     for ci, s in enumerate(zones[li])]
            self.query_one(f"#lane{li}", Static).update(
                "  ".join(chips) if chips else f"[{DIM}](empty)[/]")
        tray_chips = [self._chip(s, self.focus_zp == (3, ci), True)
                      for ci, s in enumerate(self.tray)]
        empty_tray = f"[{DIM}](none — every segment is on a line)[/]"
        self.query_one("#tray", Static).update(
            "  ".join(tray_chips) if tray_chips else empty_tray)
        fz, fp = self.focus_zp
        zone = zones[fz]
        if zone:
            seg = zone[fp]
            state = "off · in tray" if fz == 3 else f"on · Line {fz + 1}"
            prov = (f"  [{CYAN}]external · {self.ext_by_id[seg].get('provenance', '')}[/]"
                    if seg in self.ext_by_id else "")
            self.query_one("#focchip", Static).update(
                f"[#f0f6fc]{self._icon(seg)} [bold]{seg}[/][/]{prov}\n"
                f"[{DIM}]{self._desc(seg)}[/]\n[{DIM}]{state}[/]")
        else:
            self.query_one("#focchip", Static).update("")
        on_count = sum(len(line) for line in self.lines)
        self.query_one("#preview", Static).update(
            "\n".join(f"[#d6dee8]{p}[/]" for p in self._preview())
            + f"\n[{DIM}]{on_count} on · {len(self.tray)} off[/]")

    def _render_review(self) -> None:
        items = self.sel.items
        cats: list[str] = []
        by_cat: dict[str, list[str]] = {}
        for c, name, on in items:
            if c not in by_cat:
                cats.append(c)
                by_cat[c] = []
            if on:
                by_cat[c].append(name)
        rows = [f"[{CYAN}]{c}[/]: "
                + (", ".join(by_cat[c]) if by_cat[c] else f"[{DIM}](none)[/]")
                for c in cats]
        self.query_one("#rev-components", Static).update("\n".join(rows))
        self.query_one("#rev-preview", Static).update(
            "\n".join(f"[#d6dee8]{p}[/]" for p in self._preview()))
        ncomp = sum(1 for _c, _n, on in items if on)
        nseg = sum(len(line) for line in self.lines)
        adopt = self.state.get("adopt", False)
        sl_line = ("Writes ~/.config/ai-kit/statusline.toml + wires settings.json"
                   if adopt else "Status line left unchanged (components only)")
        self.query_one("#rev-what", Static).update(
            f"[{DIM}]•[/] Symlink [bold]{ncomp}[/] components into "
            f"~/.claude/(agents|commands|skills)/\n"
            f"[{DIM}]•[/] {sl_line}\n"
            f"[{DIM}]•[/] Validate with statusline-doctor before saving")
        self.query_one("#cta", Static).update(
            f"▸ [bold #7ee2a0]Install ai-kit[/]  [{DIM}]{ncomp} components · "
            f"{nseg} segments[/]   [#d6ffe4 on #10421f] Enter [/]")

    def _render_done(self) -> None:
        self.query_one("#done-art", Static).update(
            f"[{GREEN}]┌─┐ ┬[/]\n[{GREEN}]├─┤ │[/]\n[{GREEN}]┴ ┴ ┴[/] ─kit")
        self.query_one("#done-next", Static).update(
            f"[{DIM}]•[/] Open a new Claude Code session to see your status line.\n"
            f"[{DIM}]•[/] Re-run  uv run tools/setup.py  any time to change picks.\n"
            f"[{DIM}]•[/] Tweak segments later in  ~/.config/ai-kit/statusline.toml.")

    # ---- input -----------------------------------------------------------
    def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+c":
            return
        if event.character == "?":
            self.help_open = not self.help_open
            self._render()
            event.stop()
            return
        if self.help_open:
            if event.key == "escape":
                self.help_open = False
                self._render()
            event.stop()
            return
        if event.character == "q":
            self.exit()
            return
        handled = (self._key_choose, self._key_arrange,
                   self._key_review, self._key_done)[self.step](event)
        if handled:
            event.stop()
            self._render()

    def _goto(self, step: int) -> bool:
        self.step = step
        return True

    def _key_choose(self, event: events.Key) -> bool:
        ch, k = event.character, event.key
        n = len(self.sel.items)
        if not n:
            return k == "enter" and self._goto(STEP_ARRANGE)
        if k == "up":
            self.sel.cursor = (self.sel.cursor - 1) % n
        elif k == "down":
            self.sel.cursor = (self.sel.cursor + 1) % n
        elif k == "space":
            self.sel.toggle_cursor()
        elif ch in ("a", "n"):
            self.sel.set_category(self.sel.items[self.sel.cursor][0], ch == "a")
        elif ch in ("A", "N"):
            self.sel.set_all(ch == "A")
        elif k == "enter":
            return self._goto(STEP_ARRANGE)
        elif k == "tab":
            pass          # consume — Tab is a no-op on Choose (never advances)
        else:
            return False
        return True

    def _key_arrange(self, event: events.Key) -> bool:
        if not self.gate_done:
            ch, k = event.character, event.key
            if ch == "y":
                self.state["adopt"] = True
                self.gate_done = True
            elif ch == "n":
                self.state["adopt"] = False
                self.gate_done = True
            elif k == "enter":
                self.state["adopt"] = self.ctx.status_line.get("state") != "foreign"
                self.gate_done = True
            elif k == "escape":
                self.state["adopt"] = False
                self.gate_done = True
            else:
                return False
            return True
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
            if not self._has_net_change():
                self.query_one("#cta", Static).update(
                    f"[{WARN}]Nothing to write — Esc to go back, q to quit[/]")
                # Return False so on_key does NOT re-render: a re-render would
                # call _render_review and overwrite this #cta message with the
                # install CTA. Step stays REVIEW; the warning persists.
                return False
            self.result = WizardResult(self.sel, self._serialize_state())
            self.step = STEP_DONE
            return True
        if event.key == "escape":
            self.step = STEP_ARRANGE
            return True
        return False

    def _has_net_change(self) -> bool:
        initial = self.state.get("_initial_enabled", {})
        current = {(c, n): on for c, n, on in self.sel.items}
        return current != initial or self.state.get("adopt", False)

    def _serialize_state(self) -> dict:
        st = dict(self.state)
        on = set()
        for ln in self.lines:
            on.update(ln)
        segs = {k: (k in on) for k in self.state["segments"]}
        st["segments"] = segs
        builtin = set(self.meta)
        layout = []
        for i in range(3):
            on_row = [s for s in self.lines[i] if s in builtin]
            off_home = [s for s in self.tray
                        if s in builtin and self.home_line.get(s, 2) == i]
            layout.append({"min_rows": self._min_rows[i], "segments": on_row + off_home})
        st["layout"] = layout
        st["adopt"] = self.state.get("adopt", False)
        st["dirty"] = True
        return st

    def _key_done(self, event: events.Key) -> bool:
        if event.key == "enter":
            self.exit()
            return True
        return False


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_wizard(ctx: WizardContext) -> WizardResult | None:
    """Run the Textual wizard and return the result, or None on a clean abort.

    Raises
    ------
    WizardCrash
        If the terminal is too small to enter the TUI (fires *before*
        ``app.run()``), or if the app exits due to an unhandled exception.
        Textual 8.x swallows exceptions (storing them in ``app._exception``
        rather than propagating), so we inspect that attribute after
        ``app.run()`` returns and re-signal it as ``WizardCrash``.
    """
    cols, rows = shutil.get_terminal_size(fallback=(80, 24))
    if cols < _MIN_TERMINAL_COLS or rows < _MIN_TERMINAL_ROWS:
        raise WizardCrash(
            f"terminal too small: {cols}x{rows} "
            f"(need {_MIN_TERMINAL_COLS}x{_MIN_TERMINAL_ROWS})"
        )
    app = WizardApp(ctx)
    app.run()
    exc = getattr(app, "_exception", None)  # private Textual 8.x attr; getattr degrades safely
    if exc is not None:                     # Textual swallows; re-signal as crash
        raise WizardCrash(exc) from exc
    return app.result
