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
ApplyHousekeepingFn = Callable[..., dict]


# ---------------------------------------------------------------------------
# Public data types (the seam — consumed/produced across setup.py)
# ---------------------------------------------------------------------------

class HostView(NamedTuple):
    """Everything the wizard needs about ONE detected status-line host.
    Built by setup.py's _host_view: ``state`` is that host's {"segments",
    "layout", "dirty", "adopt"}; ``status_line`` re-reads the host's wiring
    state live; segment_meta/external_segments/sample_json/engine are
    host-scoped; ``done_hint`` is the one-sentence next action (open a new
    session of that CLI)."""
    id: str
    label: str
    config_label: str
    wiring_label: str
    state: dict
    status_line: StatusLineFn
    segment_meta: dict
    external_segments: list
    sample_json: str
    engine: object
    done_hint: str


class WizardResult(NamedTuple):
    """Returned by run_wizard on confirm; None on abort. ``state`` is keyed by
    host id: {"claude": {"segments", …}, "cursor": {…}, …}."""
    selection: SelectionLike
    state: dict


class WizardContext(NamedTuple):
    """All data and behaviour the wizard needs, injected by setup.py at
    call-time.  wizard_app imports nothing from setup.py; this is the seam.
    ``state`` is component-level only ({"_initial_enabled", …}); every
    status-line field lives on a per-host ``HostView`` in ``hosts``."""
    selection: SelectionLike
    state: dict                 # {"_initial_enabled": {(cat, name): bool}}
    component_meta: dict          # {name: description} across all CATEGORIES
    housekeeping: dict = {}  # noqa: RUF012 -- copied on read (__init__), never mutated
                                # {"stale": [...], "predecessors": [...]} — "cat/name"
                                #  display strings; empty = nothing pending, gate skipped.
    hosts: tuple[HostView, ...] = ()  # detected hosts, Claude then Cursor
    # Injected by launch_wizard: commit(selection, states) -> {"ok", "adopt",
    # "log", "hosts": {host_id: {"ok", "adopt", "log"}}}; ``states`` is the
    # host-keyed WizardResult.state. Runs the real install (symlinks + each adopted
    # host's doctor-validated status-line write) IN-UI on Review-confirm.
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
class HostPane:
    """ONE host's Arrange state: its model/board pair and whether that host's
    adoption gate has been answered. Grouped so the app keeps one active pane
    instead of mirroring a model/board pair as separate attributes."""
    model: WizardModel
    board: LayoutBoard
    answered: bool


@dataclass
class FlowState:
    step: int = STEP_CHOOSE
    help_open: bool = False
    gate_done: bool = False
    host_index: int = 0    # the detected host whose gate/board is on Arrange
    result: WizardResult | None = None


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
        self.ctx = ctx
        hk_data = dict(ctx.housekeeping) if ctx.housekeeping else {}
        hk_pending = [k for k in ("stale", "predecessors", "replace") if hk_data.get(k)]
        self.views = {host.id: self._host_pane(host) for host in ctx.hosts}
        # Zero detected hosts: the flow never arranges the status line, but
        # Choose/Review/Done still render off a component-only pane, so there is
        # always SOME pane — never an index into a nonexistent first host.
        self.pane = (self.views[ctx.hosts[0].id] if ctx.hosts
                     else self._component_pane())
        # A host already wired to ours has effectively answered its own gate;
        # with zero hosts there is no gate at all. Otherwise the gate is re-asked
        # on the first Arrange entry.
        self.flow = FlowState(gate_done=not ctx.hosts or
                              all(p.answered for p in self.views.values()))
        self.commit = CommitState()
        self.hk = HousekeepingState(
            data=hk_data,
            pending=hk_pending,
            done=not hk_pending,
        )
        super().__init__()

    # ---- the active pane (derived reads, never a mirrored attribute) ------
    @property
    def hosts(self) -> tuple[HostView, ...]:
        """The detected hosts, in detection order (Claude Code, then Cursor)."""
        return self.ctx.hosts

    @property
    def model(self) -> WizardModel:
        """The segment model of the pane currently on the Arrange step."""
        return self.pane.model

    @property
    def board(self) -> LayoutBoard:
        """The layout board of the pane currently on the Arrange step."""
        return self.pane.board

    def _component_pane(self) -> HostPane:
        """The zero-host pane: an empty board the component-only flow renders
        Choose/Review/Done from, with no segment to arrange and no gate to ask."""
        model = WizardModel(sel=self.ctx.selection, state={}, meta={},
                            ext_by_id={}, home_line={})
        board = LayoutBoard(lines=[[], [], []], tray=[], focus_zp=(0, 0),
                            min_rows=[0, 20, 30],
                            initial_lines=[[], [], []], initial_tray=[])
        return HostPane(model=model, board=board, answered=True)

    def _host_pane(self, host: HostView) -> HostPane:
        """One host's Arrange-state snapshot: the serialized model/board pair,
        shared selection, and the gate's live adoption state."""
        state = dict(host.state)
        gate_done = host.status_line().get("state") == "ours"
        if gate_done:
            state["adopt"] = True
        for ext in host.external_segments:
            state["segments"].setdefault(ext["id"], False)
        home_line = {k: min(max(int(m.get("line", 0)), 0), 2)
                     for k, m in host.segment_meta.items()}
        for ext in host.external_segments:
            home_line[ext["id"]] = 2
        model = WizardModel(
            sel=self.ctx.selection,
            state=state,
            meta=host.segment_meta,
            ext_by_id={e["id"]: e for e in host.external_segments},
            home_line=home_line,
        )
        board = LayoutBoard(
            lines=[[], [], []],
            tray=[],
            focus_zp=(0, 0),
            min_rows=[*(r.get("min_rows", 0) for r in state["layout"][:3]), 0,
                      20, 30][:3],
            initial_lines=[[], [], []],
            initial_tray=[],
        )
        self._build_lists_from_state(model, board)
        board.initial_lines = [list(x) for x in board.lines]
        board.initial_tray = list(board.tray)
        return HostPane(model=model, board=board, answered=gate_done)

    def _pane(self, index=None) -> HostPane:
        """The Arrange pane for host ``index`` (default: the active one). With
        zero detected hosts there is no host to index, so the component-only
        pane stands in — the flow never asks for more than that."""
        if not self.hosts:
            return self.pane
        i = self.flow.host_index if index is None else index
        return self.views[self.hosts[i].id]

    def _enter_host_arrange(self, index):
        """Put host ``index``'s pane on the Arrange step and settle its gate:
        the gate is re-asked only when the host is not already adopted/ours."""
        self.flow.host_index = index
        self.pane = self._pane(index)
        self.flow.gate_done = self.pane.answered
        self.flow.step = STEP_ARRANGE

    # ---- model -----------------------------------------------------------
    def _build_lists_from_state(self, model: WizardModel, board: LayoutBoard) -> None:
        segs = model.state["segments"]
        board.lines = [[], [], []]
        placed = set()
        for i, row in enumerate(model.state["layout"][:3]):
            for seg in row["segments"]:
                if segs.get(seg) and seg not in placed:
                    board.lines[i].append(seg)
                    placed.add(seg)
        # ON segments not in any layout row (e.g. an enabled external): home line
        for seg, on in segs.items():
            if on and seg not in placed:
                board.lines[model.home_line.get(seg, 2)].append(seg)
                placed.add(seg)
        # tray = every OFF segment, in stable state-key order (built-ins then externals)
        board.tray = [seg for seg in segs if not segs.get(seg)]
        board.focus_zp = (0, 0)

    # ---- metadata accessors ---------------------------------------------
    def _icon(self, seg: str, model: WizardModel | None = None) -> str:
        model = model or self.model
        if seg in model.ext_by_id:
            return model.ext_by_id[seg].get("icon") or "●"
        return model.meta.get(seg, {}).get("icon", "")

    def _sample(self, seg: str, model: WizardModel | None = None) -> str:
        model = model or self.model
        if seg in model.ext_by_id:
            return model.ext_by_id[seg].get("sample", "")
        return model.meta.get(seg, {}).get("sample", "")

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

    def _preview_lines(self, pane: HostPane) -> list[str]:
        """Sample-preview markup built from ONE host's board — review may show
        hosts other than the Arrange pane's, so icons/samples are per-model."""
        model, board = pane.model, pane.board
        out = []
        for ln in board.lines:
            parts = [f"{self._icon(s, model)} {self._sample(s, model)}" for s in ln]
            if parts:
                out.append(f" [{LINE}]|[/] ".join(parts))
        return out or [f"[{DIM}](all segments off)[/]"]

    def _preview(self):
        return self._preview_lines(self._pane())

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
            pv.border_title = ("live preview — " + (self.hosts[self.flow.host_index].label
                               if self.hosts else "no host")
                               + "  (full width, like the real status line)")
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

    # ---- render ----------------------------------------------------------
    _STEP_PANEL = ("step-choose", "step-arrange", "step-review", "step-done")

    def _render_hide_steps(self) -> None:
        for sid in self._STEP_PANEL:
            self.query_one(f"#{sid}").display = False
        self.query_one("#step-help").display = self.flow.help_open

    def _step_title(self) -> str:
        """The current screen's title. Every formerly Claude-only string is
        host-labelled (D-22): the Arrange title names the host whose board is
        showing ("Arrange your Cursor CLI status line")."""
        if self.flow.step == STEP_ARRANGE and self.hosts:
            host = self.hosts[self.flow.host_index]
            return f"Arrange your {host.label} status line"
        return TITLES[self.flow.step]

    def _done_title_parts(self, done_failed: bool) -> tuple[str, str]:
        if self.flow.step == STEP_DONE and self.commit.committing:
            return ACCENT, "Installing…"
        if self.flow.step == STEP_DONE and done_failed:
            return WARN, "⚠ install incomplete"
        if self.flow.step == STEP_DONE:
            return GREEN, self._step_title()
        return "#f0f6fc", self._step_title()

    def _adopted_views(self) -> list[HostView]:
        """The hosts whose status line the user is adopting, in detection order."""
        return [h for h in self.hosts if (self.views[h.id].model.state or {}).get("adopt")]

    def _render_done_subtitle(self, sub_w: Static, done_failed: bool) -> None:
        ncomp = sum(1 for _c, _n, on in self.model.sel.items if on)
        adopted = self._adopted_views()
        if self.commit.committing:
            sub_w.update(f"[{DIM}]writing your selection…[/]")
        elif done_failed:
            sub_w.update(f"[{WARN}]components installed · some settings "
                         "could not be written[/]")
        elif adopted:
            parts = []
            for h in adopted:
                board = self.views[h.id].board
                nseg = sum(len(line) for line in board.lines)
                nlines = sum(1 for line in board.lines if line)
                if len(self.hosts) > 1:
                    parts.append(f"{h.label}: {nseg} segments · {nlines} lines")
                else:
                    parts.append(f"{nseg} segments · {nlines} lines")
            lines_word = "status line" if len(adopted) == 1 else "status lines"
            sub_w.update(f"[{DIM}]{ncomp} components · " + " · ".join(parts) +
                         f" — your {lines_word} {'is' if len(adopted) == 1 else 'are'} "
                         "ready[/]")
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
        elif kind == "replace":
            gate = (f"[b {WARN}]⚠  {len(items)} skill path(s) hold a real directory "
                    "or a foreign link[/]\n"
                    f"{listing}\n\n"
                    f"[{DIM}]y moves each to ai-kit's backups dir under the XDG "
                    "state dir — never deleted — and links the repo copy.[/]\n"
                    f"[#0d1117 on {WARN}] y = back up and link the repo copy · "
                    "N / Enter = leave them [/]")
        else:
            gate = (f"[b {WARN}]⚠  {len(items)} dangling link(s) shaped like an "
                    "earlier ai-kit install[/]\n"
                    f"{listing}\n\n"
                    f"[{DIM}]Their targets are gone. Either answer first moves each "
                    "old link to ai-kit's backups dir.[/]\n"
                    f"[#0d1117 on {WARN}] Y / Enter = re-point to this install · "
                    "n = remove them (kept in backups) [/]")
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

    def _adoption_gate_markup(self, host: HostView) -> str:
        sl = host.status_line()
        if sl.get("state") == "foreign":
            cmd = sl.get("current_command") or "(unknown)"
            return (f"[b {WARN}]⚠  Existing {host.label} status line detected[/]\n"
                    f"[{DIM}]Current:[/] {cmd}\n\n"
                    f"[#0d1117 on {WARN}] Replace it with ai-kit?  "
                    f"y = replace · N / Enter = keep mine [/]")
        return (f"[b #f0f6fc]Wire your {host.label} status line?[/]\n"
                f"[{DIM}]ai-kit can render git/model/diagnostics in your "
                f"{host.label} status line.[/]\n\n"
                f"[#0d1117 on {ACCENT}] Y / Enter = set it up · "
                "n = skip (leave it unset) [/]")

    def _render_adoption_gate(self, lane0: Static) -> None:
        lane0.add_class("gate-attention")
        lane0.border_title = (f"⚠ status line "
                              f"({self.hosts[self.flow.host_index].label}) — action needed")
        lane0.update(self._adoption_gate_markup(
            self.hosts[self.flow.host_index]))
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
        host = self.hosts[self.flow.host_index]
        prov = (f"  [{CYAN}]external · {host.label} · "
                f"{self.model.ext_by_id[seg].get('provenance', '')}[/]"
                if seg in self.model.ext_by_id else
                f"  [{DIM}]built-in segment · {host.label} · inventory[/]")
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

    def _review_component_rows(self) -> tuple[list[str], int]:
        """Review's per-category component lines plus the non-hook count — the
        number of components Confirm actually symlinks."""
        cats: list[str] = []
        by_cat: dict[str, list[str]] = {}
        for cat, name, on in self.model.sel.items:
            if cat not in by_cat:
                cats.append(cat)
                by_cat[cat] = []
            if on:
                by_cat[cat].append(name)
        rows = [f"[{CYAN}]{cat}[/]: "
                + (", ".join(by_cat[cat]) if by_cat[cat] else f"[{DIM}](none)[/]")
                for cat in cats]
        ncomp = sum(1 for cat, _n, on in self.model.sel.items
                    if on and cat != "hooks")
        return rows, ncomp

    def _review_status_blocks(self, adopted: list[HostView]) -> tuple[int, list[str]]:
        """(on-line segment count, preview blocks) over the ADOPTED hosts only —
        a declined host skips the whole status-line section. A multi-host Review
        labels each host's first block so two panes can never read as one line."""
        nseg = 0
        shown: list[str] = []
        for host in adopted:
            pane = self.views[host.id]
            nseg += sum(len(line) for line in pane.board.lines)
            block = self._preview_lines(pane)
            if len(self.hosts) > 1 and block:
                block = [f"[{DIM}]{host.label} —[/]" + block[0], *block[1:]]
            shown.extend(block)
        return nseg, shown

    def _review_what_lines(self, ncomp: int, adopted: list[HostView]) -> list[str]:
        """What happens on Confirm: the components, then EVERY detected host's
        outcome — each adopted host's own config + wiring file, each declined
        host named as left untouched (SPEC R12), the honest "left unchanged"
        line when every detected host declined, or the "no host detected" line
        when none did."""
        what = [f"[{DIM}]•[/] Symlink [bold]{ncomp}[/] components into "
                f"~/.claude/(agents|commands|skills)/"]
        if adopted:
            adopted_ids = {h.id for h in adopted}
            for host in adopted:
                what.append(f"[{DIM}]•[/] {host.label}: write {host.config_label} "
                            f"+ wire {host.wiring_label}")
            for host in self.hosts:
                if host.id not in adopted_ids:
                    what.append(f"[{DIM}]•[/] {host.label}: left untouched")
            what.append(f"[{DIM}]•[/] Validate with the status line doctor "
                        "before saving")
        elif self.hosts:
            what.append(f"[{DIM}]•[/] Status line left unchanged (components only)")
        else:
            what.append(f"[{DIM}]•[/] No status-line host detected — nothing "
                        "will be written for one")
        return what

    def _render_review(self) -> None:
        rows, ncomp = self._review_component_rows()
        self.query_one("#rev-components", Static).update("\n".join(rows))
        adopted = self._adopted_views()
        rp = self.query_one("#rev-preview", Static)
        rp.display = bool(adopted)
        nseg, shown = self._review_status_blocks(adopted)
        if adopted:
            rp.update("\n".join(f"[#d6dee8]{p}[/]" for p in shown))
        self.query_one("#rev-what", Static).update(
            "\n".join(self._review_what_lines(ncomp, adopted)))
        seg_note = f" · {nseg} segments" if adopted else ""
        self.query_one("#cta", Static).update(
            f"▸ [bold #7ee2a0]Install ai-kit[/]  [{DIM}]{ncomp} components"
            f"{seg_note}[/]   [#d6ffe4 on #10421f] Enter [/]")

    def _done_failure_lines(self, outcome: dict) -> list[str]:
        """Done-screen failure text, ONE LINE PER HOST: a failing host names
        itself and its own captured reason, while every host that did write
        stays visible on its own line. A component-only failure (no per-host
        outcomes) keeps the single generic reason."""
        hosts = outcome.get("hosts")
        per = hosts if isinstance(hosts, dict) else {}
        lines = [f"[{WARN}]Components were installed, but some settings could "
                 "not be written:[/]"]
        failed, written = [], []
        for h in self.hosts:
            entry = per.get(h.id)
            if not isinstance(entry, dict):    # a missing host row is not a failure
                entry = {}
            if entry.get("ok") is False:
                failed.append(h)
                reason = escape((entry.get("log") or "").strip()) \
                    or "a settings write was refused or failed."
                lines.append(f"[{DIM}]{h.label}:[/] {reason}")
            elif entry.get("ok") is True and entry.get("adopt"):
                written.append(h)
        if not failed:                       # component-only failure (hooks, links)
            reason = escape((outcome.get("log") or "").strip()) \
                or "a settings write was refused or failed."
            lines.append(f"[{DIM}]{reason}[/]")
        if written:
            names = ", ".join(h.label for h in written)
            lines.append(f"[{GREEN}]written OK:[/] {names}")
        lines.append("")
        lines.append(f"[{DIM}]Re-run  uv run tools/setup.py  to try again.[/]")
        return lines

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
            nxt_w.update("\n".join(self._done_failure_lines(outcome)))
            return
        art.update(f"[{GREEN}]┌─┐ ┬[/]\n[{GREEN}]├─┤ │[/]\n[{GREEN}]┴ ┴ ┴[/] ─kit")
        adopted = self._adopted_views()
        nxt = [f"[{DIM}]•[/] Re-run  uv run tools/setup.py  any time to "
               f"change picks."]
        if adopted:
            for h in adopted:
                nxt.insert(0, f"[{DIM}]•[/] Tweak segments later in  "
                              f"{h.config_label}.")
                nxt.insert(0, f"[{DIM}]•[/] {h.done_hint}")
        else:
            nxt.append(f"[{DIM}]•[/] Want a status line? Run it again and "
                       "choose Yes at the status-line gate.")
        nxt_w.update("\n".join(nxt))

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
        # Entering the status-line step from Choose walks the detected hosts
        # (Claude then Cursor); WITH ZERO detected hosts there is nothing to
        # arrange or wire — Choose goes straight to Review, and Review → Done
        # writes nothing for the status line.
        if not self.hosts:
            self.flow.step = STEP_REVIEW
            return True
        self._enter_host_arrange(0)
        return True

    def _advance_host(self) -> None:
        """Host traversal contract (the seam plan 23-17 walks): after the
        current host's gate decision or board Enter, move to the NEXT host's
        gate, or to Review once every detected host's pane has been visited."""
        nxt = self.flow.host_index + 1
        if nxt < len(self.hosts):
            self._enter_host_arrange(nxt)
        else:
            self.flow.step = STEP_REVIEW

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
        default = kind == "predecessors"   # stale and replace default to decline
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
        kwargs: dict = ({"replace": self.hk.answers.get("replace", False)}
                        if "replace" in self.hk.pending else {})
        try:
            if self.ctx.apply_housekeeping is None:
                outcome = {"selection": self.model.sel,
                          "initial_enabled": self.model.state.get("_initial_enabled", {})}
            else:
                outcome = self.ctx.apply_housekeeping(prune, repoint, **kwargs)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            outcome = {}
            self.hk.error = f"housekeeping failed: {exc}"
        if outcome.get("selection") is not None:
            for pane in self.views.values():
                pane.model.sel = outcome["selection"]
            self.model.sel = outcome["selection"]
        self.ctx.state["_initial_enabled"] = outcome.get(
            "initial_enabled", self.ctx.state.get("_initial_enabled", {}))
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
        host = self.hosts[self.flow.host_index]
        if k == "escape":
            self.flow.step = STEP_CHOOSE        # back out without answering
            return True
        if ch == "y":
            self.model.state["adopt"] = True
        elif ch == "n":
            self.model.state["adopt"] = False
        elif k == "enter":                 # follow the shown default
            self.model.state["adopt"] = host.status_line().get("state") != "foreign"
        else:
            return False
        self.flow.gate_done = True
        self.pane.answered = True
        if not self.model.state["adopt"]:
            # Declined: nothing to arrange and the host's config files are left
            # untouched, so skip the segment board straight to the next host.
            self._advance_host()
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
            "enter": self._advance_host,
            "escape": self._board_back,
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

    def _review_from_board(self) -> None:
        """Board Enter: walk to the NEXT host's gate, or Review only once every
        detected host has answered its own gate (23-16's host traversal)."""
        self._advance_host()

    def _board_back(self) -> None:
        """Board Esc (D-22): on a LATER host's board step back to the previous
        host's board — its own arrangement stays intact. When no earlier host
        actually arranged a board (first host, or every earlier one declined),
        back out to Choose."""
        prev = max((i for i in range(self.flow.host_index)
                    if self.views[self.hosts[i].id].model.state.get("adopt")),
                   default=None)
        if prev is None:
            self.flow.step = STEP_CHOOSE
        else:
            self._enter_host_arrange(prev)

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

    def _all_hosts_gate_done(self) -> bool:
        """Host traversal invariant behind Review: every detected host answered
        its own gate. False on a direct-to-Review fixture jump, so a key handler
        can never bypass a host's gate (the two-host PTY scenario pins this)."""
        return all(self.views[h.id].answered for h in self.hosts)

    def _key_review(self, event: events.Key) -> bool:
        if event.key == "enter":
            if not self._has_net_change():
                self.query_one("#cta", Static).update(
                    f"[{WARN}]Nothing to write — Esc to go back, q to quit[/]")
                # Return False so on_key does NOT re-render: a re-render would
                # call _render_review and overwrite this #cta message with the
                # install CTA. Step stays REVIEW; the warning persists.
                return False
            states = self._states()
            if self.ctx.commit is None:
                # No commit injected (unit fixtures): keep the legacy behavior —
                # stash the result and show the Done screen without installing.
                self.flow.result = WizardResult(self.model.sel, states)
                self.flow.step = STEP_DONE
                return True
            # Full in-UI commit: advance to Done in a "committing" state and run
            # the real install in a worker thread (it touches files + a doctor
            # subprocess; doing it on the event loop would freeze the UI).
            self.commit.commit_state = states
            self.commit.committing = True
            self.commit.outcome = None
            self.flow.step = STEP_DONE
            self._run_commit()
            return True
        if event.key == "escape":
            # Back to the last host whose BOARD the user actually arranged (an
            # adopted host). A declined host skipped its board, so Review Esc
            # steps to Choose instead of dropping the user onto a board they
            # never saw.
            adopted = [i for i, h in enumerate(self.hosts)
                       if self.views[h.id].model.state.get("adopt")]
            if adopted:
                self._enter_host_arrange(adopted[-1])
            else:
                self.flow.step = STEP_CHOOSE
            return True
        return False

    def _has_net_change(self) -> bool:
        # `_initial_enabled` is component-level state (ctx.state), not per-host:
        # a host's own state dict carries segments/layout/adopt only.
        initial = self.ctx.state.get("_initial_enabled", {})
        current = {(c, n): on for c, n, on in self.model.sel.items}
        return current != initial or self.model.state.get("adopt", False)

    def _states(self) -> dict:
        """Every host's Arrange-state serialized for the commit and the result,
        keyed by host id in detection order. A host the user declined still
        carries its untouched state (`adopt` False); the commit writes nothing
        for it. With zero hosts this is an empty dict — not a Claude-shaped
        fallback."""
        if not self.hosts:
            return {}
        return {h.id: self._serialize_state(h.id) for h in self.hosts}

    def _serialize_state(self, host_id=None) -> dict:
        """Board -> {segments, layout} for one host (default: the active pane).
        Off segments stay addressable: they ride in their home line's row so an
        explicit `<id> = false` can be written when the user declined one."""
        pane = self.views[host_id] if host_id else self._pane()
        model, board = pane.model, pane.board
        st = dict(model.state)
        on = set()
        for ln in board.lines:
            on.update(ln)
        segs = {k: (k in on) for k in model.state["segments"]}
        st["segments"] = segs
        # Both built-ins AND externals go into the written layout: the whole
        # point of letting the user drag an external segment's chip onto a
        # line is that the resulting toml's explicit [[line]] placement then
        # OVERRIDES that segment's own header line=/after=/before= fallback
        # (cfg_place_external only falls back to the header when the id is
        # absent from every row) — an arrangement the user made here must win.
        layout = []
        for i in range(3):
            on_row = list(board.lines[i])
            off_home = [s for s in board.tray if model.home_line.get(s, 2) == i]
            layout.append({"min_rows": board.min_rows[i], "segments": on_row + off_home})
        st["layout"] = layout
        st["adopt"] = bool(model.state.get("adopt"))
        st["dirty"] = True
        return st

    @work(thread=True, exclusive=True)
    def _run_commit(self) -> None:
        """Worker: run the injected commit (real install) off the event loop, then
        update the Done screen with the outcome. Any failure is captured so the UI
        never hangs in the 'Installing…' state. The commit receives the host-keyed
        states and returns the component outcome plus per-host {ok, adopt, log}
        — the per-host log/ok land on WizardResult.state as `_commit_log` and
        `_commit_ok` under each host's id so cmd_install can surface them."""
        commit_fn = self.ctx.commit
        commit_state = self.commit.commit_state if self.commit.commit_state is not None else {}
        try:
            if commit_fn is None:
                raise RuntimeError("commit callback not configured")
            outcome = commit_fn(self.model.sel, commit_state)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            outcome = {"ok": False,
                       "adopt": any(bool((st or {}).get("adopt"))
                                    for st in (commit_state or {}).values()),
                       "log": f"commit failed: {exc}"}
        host_out = ((outcome or {}).get("hosts") if isinstance(outcome, dict) else None) or {}
        result_state: dict = {}
        for hid, st in (commit_state or {}).items():
            merged = dict(st or {})
            per = dict(host_out.get(hid)
                       or {"ok": outcome.get("ok", True),
                          "adopt": outcome.get("adopt", False),
                          "log": outcome.get("log", "")})
            merged["_commit_log"] = per.get("log", "")
            merged["_commit_ok"] = per.get("ok", True)
            result_state[hid] = merged
        self.flow.result = WizardResult(self.model.sel, result_state)
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
    return app.flow.result
