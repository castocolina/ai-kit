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
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import NamedTuple, Protocol

from rich.markup import escape
from textual import events, work
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


class SelectionLike(Protocol):
    """Component picker injected by setup.py (structural — no import from setup)."""
    items: list[tuple[str, str, bool]]
    cursor: int

    def toggle_cursor(self) -> None: ...

    def set_category(self, cat: str, select: bool) -> None: ...

    def set_all(self, select: bool) -> None: ...


StatusLineFn = Callable[[], dict[str, str | None]]
CommitFn = Callable[[SelectionLike, dict], dict]
ApplyHousekeepingFn = Callable[[bool, bool], dict]


# ---------------------------------------------------------------------------
# Public data types (the seam — consumed/produced across setup.py)
# ---------------------------------------------------------------------------

class WizardResult(NamedTuple):
    """Returned by run_wizard on confirm; None on abort."""
    selection: SelectionLike
    state: dict


class WizardContext(NamedTuple):
    """All data and behaviour the wizard needs, injected by setup.py at
    call-time.  wizard_app imports nothing from setup.py; this is the seam."""
    selection: SelectionLike
    state: dict                 # {"segments": {key: bool}, "layout": [...],
                                #  "dirty": bool, "adopt": bool}
    sample_json: str            # rendered sample input JSON for preview
    engine: object                   # callables: render_preview, apply_command, groups, order
    # New Plan-A fields (Task 10) — always populated by setup.py.launch_wizard.
    status_line: StatusLineFn     # () -> {"state": str, "current_command": str|None}
    segment_meta: dict          # {key: {description, sample, icon, line}}
    external_segments: list     # [{id, name, path, default_on, description,
                                #   icon, sample, line, provenance}, …]
    component_meta: dict          # {name: description} across all CATEGORIES
    housekeeping: dict = {}  # noqa: RUF012 -- copied on read (__init__), never mutated
                                # {"stale": [...], "predecessors": [...]} — "cat/name"
                                #  display strings; empty = nothing pending, gate skipped.
    # Injected by launch_wizard: commit(selection, state) -> {"ok", "adopt", "log"}.
    # Runs the real install (symlinks + doctor-validated status-line write) IN-UI on
    # Review-confirm. None in unit fixtures → the view falls back to a no-op commit.
    commit: CommitFn | None = None
    # Injected by launch_wizard: apply_housekeeping(prune, repoint) ->
    # {"selection", "initial_enabled"}. Runs IN-UI once the housekeeping gate is
    # answered. None → legacy no-op (fine when housekeeping is empty).
    apply_housekeeping: ApplyHousekeepingFn | None = None


@dataclass
class WizardModel:
    sel: SelectionLike
    state: dict
    meta: dict
    ext_by_id: dict[str, dict]
    home_line: dict[str, int]


@dataclass
class LayoutBoard:
    lines: list[list[str]]
    tray: list[str]
    focus_zp: tuple[int, int]
    min_rows: list[int]
    initial_lines: list[list[str]]
    initial_tray: list[str]


@dataclass
class FlowState:
    step: int = STEP_CHOOSE
    help_open: bool = False
    gate_done: bool = False
    result: WizardResult | None = None
    exception: BaseException | None = None


@dataclass
class CommitState:
    committing: bool = False
    outcome: dict | None = None
    commit_state: dict | None = None


@dataclass
class HousekeepingState:
    data: dict
    pending: list[str]
    stage: int = 0
    answers: dict = field(default_factory=dict)
    applying: bool = False
    error: str | None = None
    done: bool = True


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
    .lane.gate-attention {{ border: round {WARN}; background: #211803;
                            border-title-color: {WARN}; }}
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
        state = dict(ctx.state)
        gate_done = ctx.status_line().get("state") == "ours"
        if gate_done:
            state["adopt"] = True
        hk_data = dict(ctx.housekeeping) if ctx.housekeeping else {}
        hk_pending = [k for k in ("stale", "predecessors") if hk_data.get(k)]
        home_line = {k: min(max(int(m.get("line", 0)), 0), 2)
                     for k, m in ctx.segment_meta.items()}
        for ext in ctx.external_segments:
            home_line[ext["id"]] = 2
        rows = [r.get("min_rows", 0) for r in state["layout"]]
        self.ctx = ctx
        self.model = WizardModel(
            sel=ctx.selection,
            state=state,
            meta=ctx.segment_meta,
            ext_by_id={e["id"]: e for e in ctx.external_segments},
            home_line=home_line,
        )
        self.board = LayoutBoard(
            lines=[[], [], []],
            tray=[],
            focus_zp=(0, 0),
            min_rows=[*rows, 0, 20, 30][:3],
            initial_lines=[[], [], []],
            initial_tray=[],
        )
        self.flow = FlowState(gate_done=gate_done)
        self.commit = CommitState()
        self.hk = HousekeepingState(
            data=hk_data,
            pending=hk_pending,
            done=not hk_pending,
        )
        super().__init__()
        self._build_lists_from_state()
        self.board.initial_lines = [list(x) for x in self.board.lines]
        self.board.initial_tray = list(self.board.tray)

    def __getattr__(self, name: str) -> object:
        """Legacy flat attribute paths used by tests and key handlers."""
        try:
            model = object.__getattribute__(self, "model")
            board = object.__getattribute__(self, "board")
            flow = object.__getattribute__(self, "flow")
            commit = object.__getattribute__(self, "commit")
            hk = object.__getattribute__(self, "hk")
        except AttributeError:
            raise AttributeError(name) from None
        table: dict[str, object] = {
            "sel": model.sel,
            "state": model.state,
            "meta": model.meta,
            "ext_by_id": model.ext_by_id,
            "home_line": model.home_line,
            "lines": board.lines,
            "tray": board.tray,
            "focus_zp": board.focus_zp,
            "step": flow.step,
            "help_open": flow.help_open,
            "gate_done": flow.gate_done,
            "result": flow.result,
            "_exception": flow.exception,
            "_committing": commit.committing,
            "_commit_outcome": commit.outcome,
            "_commit_state": commit.commit_state,
            "housekeeping": hk.data,
            "housekeeping_done": hk.done,
            "_hk_pending": hk.pending,
            "_hk_stage": hk.stage,
            "_hk_answers": hk.answers,
            "_hk_applying": hk.applying,
            "_hk_error": hk.error,
            "_min_rows": board.min_rows,
            "_initial_lines": board.initial_lines,
            "_initial_tray": board.initial_tray,
        }
        if name in table:
            return table[name]
        raise AttributeError(name)

    # ---- model -----------------------------------------------------------
    def _build_lists_from_state(self) -> None:
        segs = self.model.state["segments"]
        self.board.lines = [[], [], []]
        placed = set()
        for i, row in enumerate(self.model.state["layout"][:3]):
            for seg in row["segments"]:
                if segs.get(seg) and seg not in placed:
                    self.board.lines[i].append(seg)
                    placed.add(seg)
        # ON segments not in any layout row (e.g. an enabled external): home line
        for seg, on in segs.items():
            if on and seg not in placed:
                self.board.lines[self.model.home_line.get(seg, 2)].append(seg)
                placed.add(seg)
        # tray = every OFF segment, in stable state-key order (built-ins then externals)
        self.board.tray = [seg for seg in segs if not segs.get(seg)]
        self.board.focus_zp = (0, 0)

    # ---- metadata accessors ---------------------------------------------
    def _icon(self, seg: str) -> str:
        if seg in self.model.ext_by_id:
            return self.model.ext_by_id[seg].get("icon") or "●"
        return self.model.meta.get(seg, {}).get("icon", "")

    def _sample(self, seg: str) -> str:
        if seg in self.model.ext_by_id:
            return self.model.ext_by_id[seg].get("sample", "")
        return self.model.meta.get(seg, {}).get("sample", "")

    def _desc(self, seg: str) -> str:
        if seg in self.model.ext_by_id:
            return self.model.ext_by_id[seg].get("description", "")
        return self.model.meta.get(seg, {}).get("description", "")

    def _component_desc(self, cat: str, name: str) -> str:  # pylint: disable=unused-argument
        # `cat` keeps the prototype's (cat, name) accessor shape; lookup is by name.
        return self.ctx.component_meta.get(name, "")  # populated by Task 1's _read_component_desc

    # ---- layout state ----------------------------------------------------
    def _reset_layout(self) -> None:
        self.board.lines = [list(x) for x in self.board.initial_lines]
        self.board.tray = list(self.board.initial_tray)
        self.board.focus_zp = (0, 0)

    def _zones(self):
        return [self.board.lines[0], self.board.lines[1], self.board.lines[2], self.board.tray]

    def _clamp_focus(self) -> None:
        z, p = self.board.focus_zp
        z = max(0, min(3, z))
        if not self._zones()[z]:
            z = next((k for k in range(4) if self._zones()[k]), 0)
        zone = self._zones()[z]
        self.board.focus_zp = (z, max(0, min(len(zone) - 1, p)) if zone else 0)

    def _preview(self):
        out = []
        for ln in self.board.lines:
            parts = [f"{self._icon(s)} {self._sample(s)}" for s in ln]
            if parts:
                out.append(f" [{LINE}]|[/] ".join(parts))
        return out or [f"[{DIM}](all segments off)[/]"]

    # ---- compose ---------------------------------------------------------
    def _compose_header(self) -> ComposeResult:
        with Horizontal(id="headerbar"):
            yield Static("─ ai-kit install wizard", id="header-title")
            yield Static("", id="header-right")

    def _compose_choose(self) -> ComposeResult:
        with VerticalScroll(id="step-choose"):
            pb = Static("", id="picksbox")
            pb.border_title = "select components"
            yield pb
            yield Static("", id="picksCount")

    def _compose_arrange(self) -> ComposeResult:
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

    def _compose_review(self) -> ComposeResult:
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

    def _compose_done(self) -> ComposeResult:
        with VerticalScroll(id="step-done"):
            yield Static("", id="done-art")
            dn = Static("", id="done-next", classes="rbox")
            dn.border_title = "next"
            yield dn

    def _compose_help(self) -> ComposeResult:
        with VerticalScroll(id="step-help"):
            hb = Static("", id="help-box", classes="rbox")
            hb.border_title = "keys"
            yield hb

    def _compose_footer(self) -> ComposeResult:
        with Horizontal(id="footerbar"):
            yield Static("", id="footer-left")
            yield Static("", id="footer-q")

    def compose(self) -> ComposeResult:
        yield from self._compose_header()
        with Container(id="bodywrap"):
            yield Static("", id="step-title")
            yield Static("", id="step-sub")
            yield from self._compose_choose()
            yield from self._compose_arrange()
            yield from self._compose_review()
            yield from self._compose_done()
            yield from self._compose_help()
        yield from self._compose_footer()

    def on_mount(self) -> None:
        self._render()

    def on_exception(self, exception: BaseException) -> None:
        """Textual lifecycle hook — capture the unhandled exception so that
        run_wizard can re-raise it as WizardCrash after app.run() returns."""
        self.flow.exception = exception
        self.exit()

    # ---- render ----------------------------------------------------------
    _STEP_PANEL = ("step-choose", "step-arrange", "step-review", "step-done")

    def _render_hide_steps(self) -> None:
        for sid in self._STEP_PANEL:
            self.query_one(f"#{sid}").display = False
        self.query_one("#step-help").display = self.flow.help_open

    def _done_title_parts(self, done_failed: bool) -> tuple[str, str]:
        if self.flow.step == STEP_DONE and self.commit.committing:
            return ACCENT, "Installing…"
        if self.flow.step == STEP_DONE and done_failed:
            return WARN, "⚠ install incomplete"
        if self.flow.step == STEP_DONE:
            return GREEN, TITLES[self.flow.step]
        return "#f0f6fc", TITLES[self.flow.step]

    def _render_done_subtitle(self, sub_w: Static, done_failed: bool) -> None:
        ncomp = sum(1 for _c, _n, on in self.model.sel.items if on)
        if self.commit.committing:
            sub_w.update(f"[{DIM}]writing your selection…[/]")
        elif done_failed:
            sub_w.update(f"[{WARN}]components installed · status line "
                         "could not be configured[/]")
        elif self.model.state.get("adopt", False):
            nseg = sum(len(line) for line in self.board.lines)
            nlines = sum(1 for line in self.board.lines if line)
            sub_w.update(f"[{DIM}]{ncomp} components · {nseg} segments · "
                         f"{nlines} lines — your status line is ready[/]")
        else:
            sub_w.update(f"[{DIM}]{ncomp} components installed · "
                         "status line left unchanged[/]")

    def _render(self) -> None:
        self._render_header()
        self._render_footer()
        self._render_hide_steps()
        title_w = self.query_one("#step-title", Static)
        sub_w = self.query_one("#step-sub", Static)
        title_w.display = sub_w.display = not self.flow.help_open
        if self.flow.help_open:
            self._render_help()
            return
        done_failed = (self.commit.outcome is not None
                       and not self.commit.outcome.get("ok", True))
        title_color, done_title = self._done_title_parts(done_failed)
        title_w.update(f"[{title_color}]{done_title}[/]")
        if self.flow.step == STEP_DONE:
            self._render_done_subtitle(sub_w, done_failed)
        else:
            sub_w.update(SUBS[self.flow.step])
        self.query_one(f"#{self._STEP_PANEL[self.flow.step]}").display = True
        (self._render_choose, self._render_arrange,
         self._render_review, self._render_done)[self.flow.step]()

    def _render_header(self) -> None:
        if self.flow.step < STEP_DONE:
            pips = " ".join(f"[{ACCENT}]●[/]" if k <= self.flow.step else f"[{LINE}]○[/]"
                            for k in range(3))
            label = f"[{DIM}]Step {self.flow.step + 1} of 3[/]"
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
        if self.flow.step == STEP_ARRANGE and not self.flow.gate_done:
            keys = [("Yes", "Y", True), ("No", "N", False), ("Back", "Esc", False)]
        elif self.flow.step == STEP_CHOOSE and not self.hk.done:
            keys = [("Yes", "Y", True), ("No", "N", False)]
        else:
            keys = FOOTERS[self.flow.step]
        left = sep.join(self._cap(*k) for k in keys)
        self.query_one("#footer-left", Static).update(left)
        self.query_one("#footer-q", Static).update(self._cap(*QUIT_KEY, False))

    def _render_help(self) -> None:
        title = ["Choose", "Arrange", "Review", "Done"][self.flow.step]
        rows = "\n".join(f"[#e6edf3 on {KEYCAP}] {_pad(k, 12)}[/]  {d}"
                         for k, d in HELP[self.flow.step])
        self.query_one("#help-box", Static).update(
            f"[bold {ACCENT}]{title} — keys[/]\n\n{rows}\n\n[{DIM}]? or Esc to close[/]")

    def _render_housekeeping_gate(self) -> None:
        picksbox = self.query_one("#picksbox", Static)
        self.query_one("#picksCount", Static).update("")
        if self.hk.applying:
            picksbox.update(f"[{DIM}]Applying…[/]")
            return
        kind = self.hk.pending[self.hk.stage]
        items = self.hk.data.get(kind, [])
        listing = "\n".join(f"  [{DIM}]-[/] {it}" for it in items)
        if kind == "stale":
            gate = (f"[b {WARN}]⚠  {len(items)} link(s) point at entries removed upstream[/]\n"
                    f"{listing}\n\n"
                    f"[#0d1117 on {WARN}] y = prune them · N / Enter = keep them [/]")
        else:
            gate = (f"[b {WARN}]⚠  {len(items)} link(s) point at a PREVIOUS ai-kit install[/]\n"
                    f"{listing}\n\n"
                    f"[{DIM}]No deletes them — this cannot be undone.[/]\n"
                    f"[#0d1117 on {WARN}] Y / Enter = re-point to this install · "
                    "n = delete them [/]")
        picksbox.update(gate)

    def _choose_category_groups(
        self, items: list[tuple[str, str, bool]],
    ) -> tuple[list[str], dict[str, list[int]]]:
        cats: list[str] = []
        by_cat: dict[str, list[int]] = {}
        for idx, (cat, _name, _on) in enumerate(items):
            if cat not in by_cat:
                cats.append(cat)
                by_cat[cat] = []
            by_cat[cat].append(idx)
        return cats, by_cat

    def _choose_component_row(self, cat: str, name: str, selected: bool, focused: bool) -> str:
        glyph = f"[{GREEN}]◉[/]" if selected else f"[{DIM}]◯[/]"
        gut = f"[{PINK}]▌[/]" if focused else " "
        nm = _pad(name, 30)
        row = (f"{gut} {glyph} [{'#f0f6fc' if focused else FG}]{nm}[/]"
               f"[{DIM}]{self._component_desc(cat, name)}[/]")
        return f"[on #161b22]{row}[/]" if focused else row

    def _render_choose(self) -> None:
        if not self.hk.done:
            self._render_housekeeping_gate()
            return
        items = self.model.sel.items
        cur_cat = items[self.model.sel.cursor][0] if items else None
        cats, by_cat = self._choose_category_groups(items)
        out: list[str] = []
        for cat in cats:
            idxs = by_cat[cat]
            on = sum(1 for i in idxs if items[i][2])
            hint = f"[{GREEN}]{on}[/]/{len(idxs)} on"
            if cat == cur_cat:
                hint += f"   [{DIM}]· a all · n none[/]"
            out.append(f"[{CYAN}]▌ {cat.upper()}[/]   {hint}")
            for i in idxs:
                _c2, name, selected = items[i]
                out.append(self._choose_component_row(
                    cat, name, selected, i == self.model.sel.cursor))
        self.query_one("#picksbox", Static).update("\n".join(out))
        sel_n = sum(1 for _c, _n, on in items if on)
        self.query_one("#picksCount", Static).update(
            f"[{GREEN}]{sel_n}[/] of {len(items)} components selected")

    def _chip(self, seg: str, focused: bool, parked: bool) -> str:
        is_ext = seg in self.model.ext_by_id
        label = f"{self._icon(seg)} {seg}"
        if is_ext:
            label = f"◆ {label}"             # external marker
        if focused:
            return (f"[{PINK}]\\[>[/][bold #ffffff on #1b1016]{label}[/]"
                    f"[{PINK}]<][/]")
        col = CYAN if is_ext else (DIM if parked else FG)
        return f"[{col} on #0d1117] {label} [/]"

    def _adoption_gate_markup(self) -> str:
        sl = self.ctx.status_line()
        if sl.get("state") == "foreign":
            cmd = sl.get("current_command") or "(unknown)"
            return (f"[b {WARN}]⚠  Existing status line detected[/]\n"
                    f"[{DIM}]Current:[/] {cmd}\n\n"
                    f"[#0d1117 on {WARN}] Replace it with ai-kit?  "
                    f"y = replace · N / Enter = keep mine [/]")
        return ("[b #f0f6fc]Wire your status line?[/]\n"
                f"[{DIM}]ai-kit can render git/model/diagnostics in your "
                "status line.[/]\n\n"
                f"[#0d1117 on {ACCENT}] Y / Enter = set it up · "
                "n = skip (leave it unset) [/]")

    def _render_adoption_gate(self, lane0: Static) -> None:
        lane0.add_class("gate-attention")
        lane0.border_title = "⚠ status line — action needed"
        lane0.update(self._adoption_gate_markup())
        for wid in ("#lane1", "#lane2", "#focchip", "#tray", "#preview"):
            self.query_one(wid, Static).update("")

    def _render_focus_chip(self, zones: list[list[str]]) -> None:
        fz, fp = self.board.focus_zp
        zone = zones[fz]
        focchip = self.query_one("#focchip", Static)
        if not zone:
            focchip.update("")
            return
        seg = zone[fp]
        state = "off · in tray" if fz == 3 else f"on · Line {fz + 1}"
        prov = (f"  [{CYAN}]external · {self.model.ext_by_id[seg].get('provenance', '')}[/]"
                if seg in self.model.ext_by_id else "")
        focchip.update(
            f"[#f0f6fc]{self._icon(seg)} [bold]{seg}[/][/]{prov}\n"
            f"[{DIM}]{self._desc(seg)}[/]\n[{DIM}]{state}[/]")

    def _render_arrange_board(self) -> None:
        self._clamp_focus()
        zones = self._zones()
        for li in range(3):
            chips = [self._chip(s, self.board.focus_zp == (li, ci), False)
                     for ci, s in enumerate(zones[li])]
            self.query_one(f"#lane{li}", Static).update(
                "  ".join(chips) if chips else f"[{DIM}](empty)[/]")
        tray_chips = [self._chip(s, self.board.focus_zp == (3, ci), True)
                      for ci, s in enumerate(self.board.tray)]
        empty_tray = f"[{DIM}](none — every segment is on a line)[/]"
        self.query_one("#tray", Static).update(
            "  ".join(tray_chips) if tray_chips else empty_tray)
        self._render_focus_chip(zones)
        on_count = sum(len(line) for line in self.board.lines)
        self.query_one("#preview", Static).update(
            "\n".join(f"[#d6dee8]{p}[/]" for p in self._preview())
            + f"\n[{DIM}]{on_count} on · {len(self.board.tray)} off[/]")

    def _render_arrange(self) -> None:
        lane0 = self.query_one("#lane0", Static)
        if not self.flow.gate_done:
            self._render_adoption_gate(lane0)
            return
        lane0.remove_class("gate-attention")
        lane0.border_title = "Line 1"
        self._render_arrange_board()

    def _render_review(self) -> None:
        items = self.model.sel.items
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
        ncomp = sum(1 for _c, _n, on in items if on)
        nseg = sum(len(line) for line in self.board.lines)
        adopt = self.model.state.get("adopt", False)
        # Status-line preview panel: only shown when adopting — declining skips
        # the whole status-line section.
        rp = self.query_one("#rev-preview", Static)
        rp.display = adopt
        if adopt:
            rp.update("\n".join(f"[#d6dee8]{p}[/]" for p in self._preview()))
        if adopt:
            what = (f"[{DIM}]•[/] Symlink [bold]{ncomp}[/] components into "
                    f"~/.claude/(agents|commands|skills)/\n"
                    f"[{DIM}]•[/] Write ~/.config/ai-kit/statusline.toml + "
                    f"wire settings.json\n"
                    f"[{DIM}]•[/] Validate with statusline-doctor before saving")
        else:
            what = (f"[{DIM}]•[/] Symlink [bold]{ncomp}[/] components into "
                    f"~/.claude/(agents|commands|skills)/\n"
                    f"[{DIM}]•[/] Status line left unchanged (components only)")
        self.query_one("#rev-what", Static).update(what)
        seg_note = f" · {nseg} segments" if adopt else ""
        self.query_one("#cta", Static).update(
            f"▸ [bold #7ee2a0]Install ai-kit[/]  [{DIM}]{ncomp} components"
            f"{seg_note}[/]   [#d6ffe4 on #10421f] Enter [/]")

    def _render_done(self) -> None:
        art = self.query_one("#done-art", Static)
        nxt_w = self.query_one("#done-next", Static)
        if self.commit.committing:
            art.update(f"[{ACCENT}]Installing…[/]")
            nxt_w.update(f"[{DIM}]Writing component symlinks and validating the "
                         "status-line config with the doctor…[/]")
            return
        outcome = self.commit.outcome
        if outcome is not None and not outcome.get("ok", True):
            art.update(f"[{WARN}]⚠  install incomplete[/]")
            reason = escape((outcome.get("log") or "").strip()) \
                or "the status-line config was rejected by the doctor."
            nxt_w.update(
                f"[{WARN}]Components were installed, but the status line could "
                f"not be configured:[/]\n[{DIM}]{reason}[/]\n\n"
                f"[{DIM}]Re-run  uv run tools/setup.py  to try again.[/]")
            return
        art.update(f"[{GREEN}]┌─┐ ┬[/]\n[{GREEN}]├─┤ │[/]\n[{GREEN}]┴ ┴ ┴[/] ─kit")
        if self.model.state.get("adopt", False):
            nxt = (f"[{DIM}]•[/] Open a new Claude Code session to see your "
                   f"status line.\n"
                   f"[{DIM}]•[/] Re-run  uv run tools/setup.py  any time to "
                   f"change picks.\n"
                   f"[{DIM}]•[/] Tweak segments later in  "
                   f"~/.config/ai-kit/statusline.toml.")
        else:
            nxt = (f"[{DIM}]•[/] Re-run  uv run tools/setup.py  any time to "
                   f"change picks.\n"
                   f"[{DIM}]•[/] Want a status line? Run it again and choose "
                   f"Yes at the status-line gate.")
        nxt_w.update(nxt)

    # ---- input -----------------------------------------------------------
    def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+c":
            return
        if event.character == "?":
            self.flow.help_open = not self.flow.help_open
            self._render()
            event.stop()
            return
        if self.flow.help_open:
            if event.key == "escape":
                self.flow.help_open = False
                self._render()
            event.stop()
            return
        if event.character == "q":
            self.exit()
            return
        handled = (self._key_choose, self._key_arrange,
                   self._key_review, self._key_done)[self.flow.step](event)
        if handled:
            event.stop()
            self._render()

    def _goto(self, step: int) -> bool:
        self.flow.step = step
        return True

    def _enter_arrange(self) -> bool:
        # Entering the status-line step from Choose. Re-ask the adoption gate
        # unless the user already opted in (adopt True) or the status line is
        # already ours — so a prior "decline" never lands on a stale board.
        if not self.model.state.get("adopt"):
            self.flow.gate_done = self.ctx.status_line().get("state") == "ours"
        self.flow.step = STEP_ARRANGE
        return True

    def _key_choose(self, event: events.Key) -> bool:
        if not self.hk.done:
            return self._key_housekeeping(event)
        ch, k = event.character, event.key
        n = len(self.model.sel.items)
        if not n:
            return k == "enter" and self._enter_arrange()
        if k == "up":
            self.model.sel.cursor = (self.model.sel.cursor - 1) % n
        elif k == "down":
            self.model.sel.cursor = (self.model.sel.cursor + 1) % n
        elif k == "space":
            self.model.sel.toggle_cursor()
        elif ch in ("a", "n"):
            self.model.sel.set_category(self.model.sel.items[self.model.sel.cursor][0], ch == "a")
        elif ch in ("A", "N"):
            self.model.sel.set_all(ch == "A")
        elif k == "enter":
            return self._enter_arrange()
        elif k == "tab":
            pass          # consume — Tab is a no-op on Choose (never advances)
        else:
            return False
        return True

    def _key_housekeeping(self, event: events.Key) -> bool:
        if self.hk.applying:
            return True             # ignore keys until the apply worker finishes
        ch, k = event.character, event.key
        kind = self.hk.pending[self.hk.stage]
        default = kind != "stale"          # stale defaults to decline; predecessors to repoint
        if ch == "y":
            answer = True
        elif ch == "n":
            answer = False
        elif k == "enter":
            answer = default
        else:
            return False
        self.hk.answers[kind] = answer
        self.hk.stage += 1
        if self.hk.stage >= len(self.hk.pending):
            self.hk.applying = True
            self._apply_housekeeping()
        return True

    @work(thread=True, exclusive=True)
    def _apply_housekeeping(self) -> None:
        """Worker: apply the housekeeping decision(s) off the event loop, then
        refresh the Choose selection/state and unblock the gate. Any failure is
        captured so the UI never hangs in the 'Applying…' state, mirroring how
        _run_commit already guards ctx.commit() failures below."""
        prune = self.hk.answers.get("stale", False)
        repoint = self.hk.answers.get("predecessors", True)
        try:
            if self.ctx.apply_housekeeping is None:
                outcome = {"selection": self.model.sel,
                          "initial_enabled": self.model.state.get("_initial_enabled", {})}
            else:
                outcome = self.ctx.apply_housekeeping(prune, repoint)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            outcome = {}
            self.hk.error = f"housekeeping failed: {exc}"
        if outcome.get("selection") is not None:
            self.model.sel = outcome["selection"]
        self.model.state["_initial_enabled"] = outcome.get(
            "initial_enabled", self.model.state.get("_initial_enabled", {}))
        self.hk.done = True
        self.hk.applying = False
        if self.hk.error:
            # Surface the captured failure once, via Textual's own toast — the
            # gate has already resolved (housekeeping_done=True, no hang), so
            # there is no gate screen left to render it inline on; this runs
            # on the main thread via call_from_thread, same as _render below.
            self.call_from_thread(self.notify, self.hk.error, severity="error")
        self.call_from_thread(self._render)

    def _key_arrange_gate(self, event: events.Key) -> bool:
        ch, k = event.character, event.key
        if k == "escape":
            self.flow.step = STEP_CHOOSE        # back out without answering
            return True
        if ch == "y":
            self.model.state["adopt"] = True
        elif ch == "n":
            self.model.state["adopt"] = False
        elif k == "enter":                 # follow the shown default
            self.model.state["adopt"] = self.ctx.status_line().get("state") != "foreign"
        else:
            return False
        self.flow.gate_done = True
        if not self.model.state["adopt"]:
            # Declined: nothing to arrange and settings.json is left
            # untouched, so skip the segment board straight to Review.
            self.flow.step = STEP_REVIEW
        return True

    def _arrange_swap_horizontal(self, direction: int) -> bool:
        z, p = self.board.focus_zp
        zone = self._zones()[z]
        if z == 3 or not zone:
            return False
        other = p + direction
        if other < 0 or other >= len(zone):
            return False
        zone[p], zone[other] = zone[other], zone[p]
        self.board.focus_zp = (z, other)
        return True

    def _key_arrange_board(self, event: events.Key) -> bool:
        ch, k = event.character, event.key
        board_keys: dict[str, Callable[[], None]] = {
            "up": lambda: self._move_chip_v("up"),
            "down": lambda: self._move_chip_v("down"),
            "space": self._toggle_chip,
            "tab": lambda: self._cycle_focus(+1),
            "shift+tab": lambda: self._cycle_focus(-1),
            "enter": lambda: setattr(self.flow, "step", STEP_REVIEW),
            "escape": lambda: setattr(self.flow, "step", STEP_CHOOSE),
        }
        if k == "left" and self._arrange_swap_horizontal(-1):
            return True
        if k == "right" and self._arrange_swap_horizontal(+1):
            return True
        if k in board_keys:
            board_keys[k]()
            return True
        if ch == "r":
            self._reset_layout()
            return True
        return False

    def _key_arrange(self, event: events.Key) -> bool:
        if not self.flow.gate_done:
            return self._key_arrange_gate(event)
        return self._key_arrange_board(event)

    def _move_chip_v(self, direction: str) -> None:
        z, p = self.board.focus_zp
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
        self.board.focus_zp = (target, len(self._zones()[target]) - 1)

    def _toggle_chip(self) -> None:
        z, p = self.board.focus_zp
        zone = self._zones()[z]
        if not zone:
            return
        seg = zone.pop(p)
        if z == 3:  # off -> on -> its inventory "home" line (not a fixed Line 1)
            home = self.model.home_line.get(seg, 2)  # default matches the other call sites
            self.board.lines[home].append(seg)
            self.board.focus_zp = (home, len(self.board.lines[home]) - 1)
        else:
            self.board.tray.append(seg)
            self.board.focus_zp = (3, len(self.board.tray) - 1)

    def _cycle_focus(self, direction: int) -> None:
        z, p = self.board.focus_zp
        zone = self._zones()[z]
        if zone and 0 <= p + direction < len(zone):
            self.board.focus_zp = (z, p + direction)
            return
        for step in range(1, 5):
            nz = (z + direction * step) % 4
            tgt = self._zones()[nz]
            if tgt:
                self.board.focus_zp = (nz, 0 if direction > 0 else len(tgt) - 1)
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
            state = self._serialize_state()
            if self.ctx.commit is None:
                # No commit injected (unit fixtures): keep the legacy behavior —
                # stash the result and show the Done screen without installing.
                self.flow.result = WizardResult(self.model.sel, state)
                self.flow.step = STEP_DONE
                return True
            # Full in-UI commit: advance to Done in a "committing" state and run
            # the real install in a worker thread (it touches files + a doctor
            # subprocess; doing it on the event loop would freeze the UI).
            self.commit.commit_state = state
            self.commit.committing = True
            self.commit.outcome = None
            self.flow.step = STEP_DONE
            self._run_commit()
            return True
        if event.key == "escape":
            # Declining skipped Arrange, so step back to Choose rather than a
            # screen the user never saw.
            self.flow.step = STEP_ARRANGE if self.model.state.get("adopt") else STEP_CHOOSE
            return True
        return False

    def _has_net_change(self) -> bool:
        initial = self.model.state.get("_initial_enabled", {})
        current = {(c, n): on for c, n, on in self.model.sel.items}
        return current != initial or self.model.state.get("adopt", False)

    def _serialize_state(self) -> dict:
        st = dict(self.model.state)
        on = set()
        for ln in self.board.lines:
            on.update(ln)
        segs = {k: (k in on) for k in self.model.state["segments"]}
        st["segments"] = segs
        # Both built-ins AND externals go into the written layout: the whole
        # point of letting the user drag an external segment's chip onto a
        # line is that the resulting toml's explicit [[line]] placement then
        # OVERRIDES that segment's own header line=/after=/before= fallback
        # (cfg_place_external only falls back to the header when the id is
        # absent from every row) — an arrangement the user made here must win.
        layout = []
        for i in range(3):
            on_row = list(self.board.lines[i])
            off_home = [s for s in self.board.tray if self.model.home_line.get(s, 2) == i]
            layout.append({"min_rows": self.board.min_rows[i], "segments": on_row + off_home})
        st["layout"] = layout
        st["adopt"] = self.model.state.get("adopt", False)
        st["dirty"] = True
        return st

    @work(thread=True, exclusive=True)
    def _run_commit(self) -> None:
        """Worker: run the injected commit (real install) off the event loop, then
        update the Done screen with the outcome. Any failure is captured so the UI
        never hangs in the 'Installing…' state."""
        commit_fn = self.ctx.commit
        commit_state = self.commit.commit_state if self.commit.commit_state is not None else {}
        try:
            if commit_fn is None:
                raise RuntimeError("commit callback not configured")
            outcome = commit_fn(self.model.sel, commit_state)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            outcome = {"ok": False,
                       "adopt": bool((self.commit.commit_state or {}).get("adopt")),
                       "log": f"commit failed: {exc}"}
        state = dict(self.commit.commit_state or {})
        state["_commit_log"] = outcome.get("log", "")
        state["_commit_ok"] = outcome.get("ok", True)
        self.flow.result = WizardResult(self.model.sel, state)
        self.commit.outcome = outcome
        self.commit.committing = False
        self.call_from_thread(self._render)

    def _key_done(self, event: events.Key) -> bool:
        if self.commit.committing:
            return True            # ignore keys until the install finishes
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
    return object.__getattribute__(app, "flow").result
