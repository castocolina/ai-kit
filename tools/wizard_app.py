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

import contextlib
import functools
import json
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, NamedTuple, Protocol, cast

from rich.markup import escape
from rich.text import Text
from textual import events, work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.timer import Timer
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
HOST_CLAUDE = "#D97757"   # host band accents (D-03); each keeps >= 4.5:1 with BAND_TEXT
HOST_CURSOR = "#8B949E"
BAND_TEXT = "#0d1117"
HOST_ACCENTS = {"claude": HOST_CLAUDE, "cursor": HOST_CURSOR}
TOGGLE_ON = "[ off │●on ]"
TOGGLE_OFF = "[ ●off │on ]"
FOREIGN_CHOICES = ("keep", "remove", "custom")
TOGGLE_FOREIGN = {"keep": "[ ●keep │remove │customize ]",
                  "remove": "[ keep │●remove │customize ]",
                  "custom": "[ keep │remove │●customize ]"}
OUTCOME_TEXT = {
    "wire": "wire ai-kit",
    "update": "update ai-kit's layout",
    "unchanged": "unchanged",
    "remove_ours": "remove ai-kit's",
    "keep_foreign": "keep its current status line; nothing written",
    "remove_foreign": "remove the foreign entry, backed up; {label} shows its own default",
    "replace_foreign": "replace the foreign entry with your ai-kit layout, backed up",
}
LOCKED_NOTICE = "Status line is off; press o to turn it on"
FOREIGN_LOCKED_NOTICE = "Board is locked; press o until customize to arrange it"
EDIT_KEYS = ("up", "down", "left", "right", "space", "tab", "shift+tab")
DONE_DOCTOR_HINT = "d · check your AI-CLI configs (config doctor)"
DONE_OFF_LINE = ("{label}: ai-kit's status line is off; open a new {label} session "
                 "to see its default.")
DONE_KEPT_LINE = "{label}: kept its current status line; nothing written to it."
DONE_REMOVED_FOREIGN_LINE = ("{label}: removed the foreign status line; the host shows "
                             "its own default.")
PREVIEW_OFF_TEXT = "host default (ai-kit's status line off)"
PREVIEW_KEEP_TEXT = "current status line kept (another tool's; no ai-kit preview)"
PREVIEW_REMOVE_TEXT = "host default (foreign status line removed)"
OFF_NOTE = {
    "ours": "Off: Review removes ai-kit's entry; {label} shows its default status line. "
            "Press o to turn it on.",
    "unset": "Off: Review leaves {label} unchanged; it shows its default status line. "
             "Press o to turn it on.",
}
FOREIGN_NOTE = {
    "keep": "Keep: Review leaves {label}'s current status line as it is and writes nothing "
            "to it. Press o to remove it.",
    "remove": "Remove: Review backs up the file, asks you (default No), then removes the "
              "foreign status line; {label} shows its own default. Press o to customize.",
    "custom": "Customize: arrange the board, starting from ai-kit's default layout; Review "
              "backs up the file, asks you (default No), then writes ai-kit's status line "
              "with your layout. Press o to keep the current one.",
}

STEP_CHOOSE, STEP_ARRANGE, STEP_REVIEW, STEP_DONE = 0, 1, 2, 3
LANE_GATE = {1: 20, 2: 30}  # Line 2 needs ≥20 rows, Line 3 needs ≥30

# Arrange preview (D-10..D-12): the preview is a real render of the host's own
# renderer, titled for the host on screen; the fallback note says it is not one.
PREVIEW_TITLE = "live preview — {host} (sample data)"
TRAY_TITLE = "OFF (Space turns a chip on → its home line)"
PREVIEW_FALLBACK_NOTE = "sample text, render unavailable"

# Choose shows one tab per component kind; global rules is not a tab (ruling 1), it is
# toggled on Review with `g`. Empty copy is the UI-SPEC "nothing to install" body (ruling 5).
KINDS = ("skills", "agents", "commands", "hooks")
GLOBAL_RULES_CAT = "global rules"
NOTHING_TO_INSTALL = ("nothing to install: no skill, agent, command or hook is installable "
                      "from this checkout. Enter continues to the status-line panes.")
GLOBAL_RULES_NOTHING = ("global rules: nothing to change (no global instruction file holds "
                        "codegraph's installer sentence)")
# Renderer output is untrusted: keep SGR colour, drop OSC, other CSI and C0 controls.
_OSC_RE = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
_CSI_NON_SGR_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-ln-~]")
_C0_RE = re.compile(r"[\x00-\x08\x0b-\x1a\x1c-\x1f\x7f]")

# footer key-bar per step: (label, cap, primary?)  — order matches the HTML
FOOTERS = [
    [("Continue", "Enter", True), ("Toggle", "Space", False), ("Kind", "←→", False),
     ("Move", "↑↓", False), ("This kind", "a/n", False), ("Help", "?", False)],
    [("Continue", "Enter", True), ("Back", "Esc", False), ("Move", "←→", False),
     ("Line", "↑↓", False), ("On/off", "Space", False), ("Status line", "o", False),
     ("Reset", "r", False), ("Help", "?", False)],
    [("Install", "Enter", True), ("Back", "Esc", False), ("Help", "?", False)],
    [("Finish & exit", "Enter", True)],
]
QUIT_KEY = ("Quit", "q")

HELP = {
    STEP_CHOOSE: [("← →", "Switch the component kind (tab)"),
                  ("↑ ↓", "Move the highlight inside the kind"),
                  ("Space", "Install / skip the highlighted component"),
                  ("a / n", "Select all / none of this kind"),
                  ("A / N", "Select all / none of every kind"),
                  ("Enter", "Continue to Arrange"), ("q", "Quit the installer")],
    STEP_ARRANGE: [("← →", "Reorder the focused chip within its line"),
                   ("↑ ↓", "Move the chip across lines (↑ off Line 1 → OFF tray)"),
                   ("Space", "Turn the focused segment on/off (off → tray)"),
                   ("Tab / ⇧Tab", "Focus the next / previous chip"),
                   ("o", "Status line on/off; another tool's line: keep / remove / customize"),
                   ("r", "Reset the layout to defaults"),
                   ("Enter / Esc", "Continue to the next host or Review / back"),
                   ("q", "Quit the installer")],
    STEP_REVIEW: [("Enter", "Install / write the config"),
                  ("Esc", "Back to Arrange"), ("g", "Toggle the global rules rewrite"),
                  ("q", "Quit")],
    STEP_DONE: [("Enter", "Finish and exit"),
                ("d", "Check your AI-CLI configs (config doctor); Esc returns here"),
                ("q", "Quit")],
}


TITLES = ["Choose what to install", "Arrange your status line",
          "Review & confirm", "✓ ai-kit is installed"]
SUBS = [
    "←→ kind · ↑↓ move · Space toggle · a/n this kind · A/N every kind · ? help",
    f"Focus is the [{PINK}]\\[>chip<][/] brackets. ←→ move within a line · "
    "↑↓ across lines (↑ off Line 1 → OFF tray) · Space turns on/off · "
    "Tab/⇧Tab next/prev chip · r reset to defaults · ? help. "
    "The preview at the bottom updates live.",
    "Nothing has been written yet. Confirm to apply.",
    "",  # Done's sub is built dynamically with the run counts
]


def _pad(s: str, n: int) -> str:
    return s if len(s) >= n else s + " " * (n - len(s))


def _name_cell(s: str, n: int) -> str:
    """A fixed n-cell name column: a longer name ends in "…", and one space
    always separates it from the description that follows."""
    return _pad(s if len(s) < n else s[:n - 2] + "…", n)


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


# Injected by setup.py in plans 04 and 05 (doctor run and foreign-status-line preparation);
# documented here so the context shape is fixed before those plans land.
DoctorFactoryFn = Callable[..., object]
PrepareForeignFn = Callable[..., object]


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
    # Plans 04 and 05: doctor(...) runs the status-line doctor for one host; prepare_foreign
    # prepares a foreign status line for keep / remove / customize. Unused until then.
    doctor: DoctorFactoryFn | None = None
    prepare_foreign: PrepareForeignFn | None = None


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
    """ONE host's Arrange state: its model/board pair. Grouped so the app keeps
    one active pane instead of mirroring a model/board pair as separate attributes."""
    model: WizardModel
    board: LayoutBoard


@dataclass
class FlowState:
    step: int = STEP_CHOOSE
    help_open: bool = False
    host_index: int = 0    # the detected host whose band/board is on Arrange
    result: WizardResult | None = None
    kind: str = ""         # the active Choose tab (a KINDS entry)
    kind_cursor: dict = field(default_factory=dict)  # kind -> last cursor index in that kind


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


# One field per render rule (sequence, key, timer, in-flight flags, both durations); splitting
# them would only move the same bookkeeping behind another object.
@dataclass
class PreviewState:  # pylint: disable=too-many-instance-attributes
    """The Arrange preview's render bookkeeping: a sequence token (the newest
    render wins, since a cancelled thread worker still delivers), the key of the
    board last scheduled, one debounce timer, and at most one render in flight."""
    seq: int = 0
    done_seq: int = -1
    key: tuple | None = None
    timer: Timer | None = None
    debounce_s: float = 0.15
    deadline_s: float = 2.0
    running: bool = False
    pending: bool = False
    # Review's real render per host: host id -> (board/width key, output); output None while
    # the render runs, "" when it failed or no renderer exists.
    review: dict[str, tuple[str, str | None]] = field(default_factory=dict)


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


class ForeignConfirm(ModalScreen):
    """Review's confirmation before another tool's status-line entry is removed or
    replaced. Default No: Enter and Esc are No; only `y` answers Yes (T-30.1-11)."""

    BINDINGS = (("y", "yes", "Yes"), ("n", "no", "No"),
                ("enter", "no", "No"), ("escape", "no", "No"))
    DEFAULT_CSS = """
    ForeignConfirm { align: center middle; }
    #foreign-box { width: 76; height: auto; max-height: 90%; border: round #d29922;
                   background: #0d1117; padding: 1 2; }
    """

    def __init__(self, host_label: str, info: dict, replace: bool) -> None:
        super().__init__()
        self.host_label = host_label
        self.info = info
        self.replace = replace

    def compose(self) -> ComposeResult:
        label = escape(self.host_label)
        if self.replace:
            title = f"Replace {label}'s existing status line with ai-kit's?"
        else:
            title = f"Remove {label}'s existing status line?"
        backup = self.info.get("backup", "")
        backup_line = (f"A backup was saved to {escape(backup)}." if backup
                       else "Dry run: no backup taken; nothing will be written.")
        lines = [f"[b]{title}[/b]",
                 f"Entry: {escape(self.info.get('entry', ''))}",
                 f"File: {escape(self.info.get('file', ''))}",
                 backup_line,
                 f"[{DIM}]y = Yes · n / Enter / Esc = No (default)[/]"]
        with VerticalScroll(id="foreign-box"):
            yield Static("\n".join(lines))

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


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
    #band {{ height: 1; }}
    #band-name {{ width: 1fr; }}
    #band-toggle {{ width: auto; }}
    #band-note {{ height: auto; }}
    .locked {{ text-opacity: 50%; }}
    #focchip {{ border: round {PINK}; background: #1b1016; height: auto; padding: 0 1;
               margin-bottom: 1; border-title-color: {PINK}; }}
    #tray {{ border: dashed {DIM}; height: auto; padding: 0 1; margin-bottom: 1;
            background: #0d1117; border-title-color: {DIM}; }}
    #preview {{ border: round {LINE}; background: #010409; height: auto; padding: 0 1;
               border-title-color: {DIM}; }}

    #kind-tabs {{ height: 1; }}
    #picksbox {{ border: round {LINE}; background: #0f141b; height: auto; padding: 0 1;
                border-title-color: {DIM}; text-wrap: nowrap; text-overflow: clip; }}
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
        self.flow = FlowState()
        self.commit = CommitState()
        self.hk = HousekeepingState(
            data=hk_data,
            pending=hk_pending,
            done=not hk_pending,
        )
        self.preview = PreviewState()
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
        return HostPane(model=model, board=board)

    def _host_pane(self, host: HostView) -> HostPane:
        """One host's Arrange-state snapshot: the serialized model/board pair,
        shared selection, and the host's live status-line state (the band toggle's
        start state, pinned for every host)."""
        state = dict(host.state)
        sl = host.status_line()
        state["start_state"] = sl.get("state", "unset")
        # The wiring value the pane shows; the commit re-reads the host's wiring
        # and refuses to publish when it no longer matches, so a command written
        # while the wizard is open is never replaced unseen.
        state["adopt_command"] = sl.get("current_command")
        state["adopt"] = state["start_state"] == "ours"
        state["foreign_ok"] = False
        if state["start_state"] == "foreign":
            state["foreign_choice"] = "keep"
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
        return HostPane(model=model, board=board)

    def _pane(self, index=None) -> HostPane:
        """The Arrange pane for host ``index`` (default: the active one). With
        zero detected hosts there is no host to index, so the component-only
        pane stands in — the flow never asks for more than that."""
        if not self.hosts:
            return self.pane
        i = self.flow.host_index if index is None else index
        return self.views[self.hosts[i].id]

    def _enter_host_arrange(self, index):
        """Put host ``index``'s pane on the Arrange step (every host pane is visited)."""
        self.flow.host_index = index
        self.pane = self._pane(index)
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

    # ---- compose ---------------------------------------------------------
    def _compose_header(self) -> ComposeResult:
        with Horizontal(id="headerbar"):
            yield Static("─ ai-kit install wizard", id="header-title")
            yield Static("", id="header-right")

    def _compose_choose(self) -> ComposeResult:
        with VerticalScroll(id="step-choose"):
            yield Static("", id="kind-tabs")
            pb = Static("", id="picksbox")
            pb.border_title = "components"
            yield pb
            yield Static("", id="picksCount")

    def _compose_arrange(self) -> ComposeResult:
        with Vertical(id="step-arrange"):
            with Horizontal(id="band"):
                yield Static("", id="band-name")
                yield Static("", id="band-toggle")
            yield Static("", id="band-note")
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
            yield Static("", id="tray")
            yield Static("", id="preview")

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

    def _done_host_rows(self) -> dict:
        """The commit's per-host outcome rows (action, ok), keyed by host id."""
        outcome = self.commit.outcome
        hosts = outcome.get("hosts") if isinstance(outcome, dict) else None
        return hosts if isinstance(hosts, dict) else {}

    def _removed_hosts(self) -> list[HostView]:
        """Hosts whose status line the commit removed (ai-kit's or a confirmed foreign one)."""
        rows = self._done_host_rows()
        return [h for h in self.hosts
                if (rows.get(h.id) or {}).get("action") in ("remove_ours", "remove_foreign")
                and (rows.get(h.id) or {}).get("ok", True)]

    def _render_done_subtitle(self, sub_w: Static, done_failed: bool) -> None:
        ncomp = sum(1 for _c, _n, on in self.model.sel.items if on)
        adopted = self._adopted_views()
        removed = [f"{escape(h.label)}: status line removed" for h in self._removed_hosts()]
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
            sub_w.update(f"[{DIM}]{ncomp} components · " + " · ".join([*parts, *removed]) +
                         f" — your {lines_word} {'is' if len(adopted) == 1 else 'are'} "
                         "ready[/]")
        elif removed:
            sub_w.update(f"[{DIM}]{ncomp} components installed · " + " · ".join(removed) + "[/]")
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
        if self.flow.step == STEP_CHOOSE and not self.hk.done:
            keys = [("Yes", "Y", True), ("No", "N", False)]
        else:
            keys = FOOTERS[self.flow.step]
            if self.flow.step == STEP_REVIEW and self._global_rules_on() is not None:
                keys = [*keys[:-1], ("Global rules", "g", False), keys[-1]]
            if self.flow.step == STEP_DONE and self.ctx.doctor is not None:
                keys = [*keys, ("Doctor", "d", False)]
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

    def _choose_kinds(self) -> list[str]:
        """The tabs: each KINDS entry that has at least one item, in KINDS order."""
        present = {cat for cat, _name, _on in self.model.sel.items}
        return [kind for kind in KINDS if kind in present]

    def _kind_indexes(self, kind: str) -> list[int]:
        return [i for i, (cat, _name, _on) in enumerate(self.model.sel.items) if cat == kind]

    def _kind_counts(self, kind: str) -> tuple[int, int]:
        idxs = self._kind_indexes(kind)
        return sum(1 for i in idxs if self.model.sel.items[i][2]), len(idxs)

    def _active_kind(self) -> str | None:
        """The shown tab: the remembered one while it still has items, else the first."""
        kinds = self._choose_kinds()
        if not kinds:
            return None
        if self.flow.kind not in kinds:
            self.flow.kind = kinds[0]
        return self.flow.kind

    def _sync_kind_cursor(self) -> None:
        """Move the cursor into the active kind only when it lies outside it; an in-kind
        cursor (or a housekeeping-replaced selection) is left alone."""
        kind = self._active_kind()
        if kind is None:
            return
        idxs = self._kind_indexes(kind)
        if self.model.sel.cursor in idxs:
            return
        remembered = self.flow.kind_cursor.get(kind)
        self.model.sel.cursor = remembered if remembered in idxs else idxs[0]

    def _choose_component_row(self, cat: str, name: str, selected: bool, focused: bool) -> str:
        glyph = f"[{GREEN}]◉[/]" if selected else f"[{DIM}]◯[/]"
        gut = f"[{PINK}]▌[/]" if focused else " "
        nm = escape(_name_cell(name, 30))
        row = (f"{gut} {glyph} [{'#f0f6fc' if focused else FG}]{nm}[/]"
               f"[{DIM}]{self._component_desc(cat, name)}[/]")
        return f"[on #161b22]{row}[/]" if focused else row

    def _render_choose(self) -> None:
        if not self.hk.done:
            self._render_housekeeping_gate()
            return
        self._sync_kind_cursor()
        items = self.model.sel.items
        active = self._active_kind()
        tabs = []
        for kind in self._choose_kinds():
            on, total = self._kind_counts(kind)
            tabs.append(f"[b {ACCENT}]\\[{kind} {on}/{total}][/]" if kind == active
                        else f"[{DIM}]{kind} {on}/{total}[/]")
        self.query_one("#kind-tabs", Static).update("  ".join(tabs))
        picks = self.query_one("#picksbox", Static)
        if active is None:
            picks.border_title = "components"
            picks.update(f"[{DIM}]{NOTHING_TO_INSTALL}[/]")
        else:
            on, total = self._kind_counts(active)
            picks.border_title = f"{active} {on}/{total}"
            idxs = self._kind_indexes(active)
            cursor = self.model.sel.cursor
            picks.update("\n".join(
                self._choose_component_row(active, items[i][1], items[i][2], i == cursor)
                for i in idxs))
            # Keep the cursor row on screen: a kind can hold more rows than the terminal.
            scroll = self.query_one("#step-choose", VerticalScroll)
            row = max(0, idxs.index(cursor) - 3)
            self.call_after_refresh(lambda: scroll.scroll_to(y=row, animate=False))
        in_kinds = [on for cat, _n, on in items if cat in KINDS]
        self.query_one("#picksCount", Static).update(
            f"[{GREEN}]{sum(in_kinds)}[/] of {len(in_kinds)} components selected")

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
        # The preview's width is known only after layout, so it is scheduled, not drawn here.
        self.call_after_refresh(self._schedule_preview)

    def _render_band(self) -> None:
        """The host band above the board: bold host name on the host accent, the
        on/off toggle (three states on a foreign host) at the right end (D-03)."""
        band = self.query_one("#band")
        band.display = bool(self.hosts)
        if not self.hosts:
            return
        host = self.hosts[self.flow.host_index]
        state = self.model.state
        if state.get("start_state") == "foreign":
            toggle = TOGGLE_FOREIGN[state.get("foreign_choice", "keep")]
        else:
            toggle = TOGGLE_ON if state.get("adopt") else TOGGLE_OFF
        accent = HOST_ACCENTS.get(host.id, LINE)
        for wid, text in (("#band-name", f"[b] {escape(host.label)} [/]"),
                          ("#band-toggle", escape(toggle))):
            widget = self.query_one(wid, Static)
            widget.styles.background = accent
            widget.styles.color = BAND_TEXT
            widget.update(text)
        start = state.get("start_state", "unset")
        adopt = bool(state.get("adopt"))
        if start == "foreign":
            note = FOREIGN_NOTE[state.get("foreign_choice", "keep")]
        elif not adopt:
            note = OFF_NOTE[start]
        else:
            note = ""
        band_note = self.query_one("#band-note", Static)
        band_note.update(escape(note.format(label=host.label)) if note else "")
        band_note.display = bool(note)
        for wid in ("#board", "#focchip", "#tray"):
            self.query_one(wid).set_class(not adopt, "locked")

    def _render_arrange(self) -> None:
        lane0 = self.query_one("#lane0", Static)
        lane0.border_title = "Line 1"
        self._render_band()
        host_label = self.hosts[self.flow.host_index].label if self.hosts else "no host"
        self.query_one("#tray", Static).border_title = TRAY_TITLE
        self.query_one("#preview", Static).border_title = PREVIEW_TITLE.format(host=host_label)
        self._render_arrange_board()

    # ---- arrange preview: a real render through the host's renderer (D-10..D-12) ----
    async def _on_resize(self, event: events.Resize) -> None:
        """A new terminal width re-renders the preview with no key press (D-11). Textual's
        own App resize handler stops the event, so the hook runs after it, not as on_resize."""
        await super()._on_resize(event)
        if self.flow.step == STEP_ARRANGE:
            self.set_timer(0.05, self._schedule_preview)  # after the screen takes the new size
        elif self.flow.step == STEP_REVIEW:
            self.set_timer(0.05, self._rekey_review)      # re-keys Review's render on width

    def _count_markup(self) -> str:
        pane = self._pane()
        on_count = sum(len(line) for line in pane.board.lines)
        return f"[{DIM}]{on_count} on · {len(pane.board.tray)} off[/]"

    def _sample_markup(self) -> str:
        """The inventory sample lines of the pane on screen, plus the count line."""
        body = "\n".join(f"[#d6dee8]{p}[/]" for p in self._preview_lines(self._pane()))
        return f"{body}\n{self._count_markup()}"

    def _schedule_preview(self) -> None:
        """Key the preview on host, board and width. An unchanged key is a no-op; a
        changed key drops any render in flight for the old board and debounces a new one."""
        if self.flow.step != STEP_ARRANGE or not self.hosts:
            return
        host_id = self.hosts[self.flow.host_index].id
        widget = self.query_one("#preview", Static)
        st = self._serialize_state()
        cols = widget.content_size.width or 100
        adopt = bool(self.model.state.get("adopt"))
        choice = self.model.state.get("foreign_choice")
        key = (host_id, adopt, choice, json.dumps([st["segments"], st["layout"]], sort_keys=True),
               cols)
        if key == self.preview.key:
            return
        prev_host = self.preview.key[0] if self.preview.key else None
        self.preview.key = key
        self.preview.seq += 1
        if self.preview.timer is not None:
            self.preview.timer.stop()
            self.preview.timer = None
        self.preview.pending = False
        if prev_host is not None and prev_host != host_id:
            # Never show the previous host's render under the new host's title (REVIEWS).
            widget.update(Text.from_markup(self._sample_markup()))
        if not adopt:
            # Off, or a foreign keep/remove: no engine call; say what Review will do.
            text = PREVIEW_OFF_TEXT
            if self.model.state.get("start_state") == "foreign":
                text = PREVIEW_KEEP_TEXT if choice == "keep" else PREVIEW_REMOVE_TEXT
            widget.update(Text.from_markup(f"[{DIM}]{escape(text)}[/]"))
            return
        if not any(self.board.lines):
            widget.update(Text.from_markup(f"[{DIM}](all segments off)[/]\n{self._count_markup()}"))
            return
        self.preview.timer = self.set_timer(self.preview.debounce_s, self._kick_preview)

    def _kick_preview(self) -> None:
        """Start one render for the current board, or mark one pending while a render runs."""
        self.preview.timer = None
        if self.flow.step != STEP_ARRANGE:    # the user left Arrange before the debounce fired
            return
        seq = self.preview.seq
        # Armed on every kick, so a render queued behind a stuck one still gets its deadline.
        self.set_timer(self.preview.deadline_s,
                       functools.partial(self._preview_timeout, seq))
        if self.preview.running:
            self.preview.pending = True
            return
        host = self.hosts[self.flow.host_index]
        if not callable(getattr(host.engine, "render_preview", None)):
            self._show_preview_fallback()
            return
        st = self._serialize_state()
        cols = self.query_one("#preview", Static).content_size.width or 100
        self.preview.running = True
        self._render_preview_job(host.id, st["segments"], st["layout"], cols,
                                 functools.partial(self._apply_preview, seq, host.id))

    @work(thread=True, group="preview")
    def _render_preview_job(self, host_id, segments, layout, cols, done) -> None:
        """Worker: the host's renderer, off the UI thread. Any failure is None (a concrete
        tuple, so no broad except); `done(out)` runs on the UI thread and drops stale results."""
        host = next(h for h in self.hosts if h.id == host_id)
        try:
            out = cast(Any, host.engine).render_preview(segments, layout=layout, cols=cols)
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError):
            out = None
        # The app may have exited while the render ran; quitting does not wait for it.
        with contextlib.suppress(RuntimeError):
            self.call_from_thread(done, out)

    def _apply_preview(self, seq, host_id, out) -> None:
        self.preview.running = False
        if self.preview.pending:
            self.preview.pending = False
            self._kick_preview()
        on_screen = bool(self.hosts) and self.hosts[self.flow.host_index].id == host_id
        if seq != self.preview.seq or self.flow.step != STEP_ARRANGE or not on_screen:
            return
        self.preview.done_seq = seq
        if not out:
            self._show_preview_fallback()
            return
        self.query_one("#preview", Static).update(
            Text.assemble(self._preview_text(out), "\n", Text.from_markup(self._count_markup())))

    def _preview_timeout(self, seq) -> None:
        """The 2 s display deadline: a render still running shows the samples and the note."""
        if seq == self.preview.seq and self.preview.done_seq != seq:
            self.preview.seq += 1  # the late result is dropped by the seq check
            self._show_preview_fallback()

    def _show_preview_fallback(self) -> None:
        body = "\n".join(f"[#d6dee8]{p}[/]" for p in self._preview_lines(self._pane()))
        self.query_one("#preview", Static).update(Text.from_markup(
            f"{body}\n[{DIM}]{PREVIEW_FALLBACK_NOTE}[/]\n{self._count_markup()}"))

    @staticmethod
    def _preview_text(out: str) -> Text:
        """Renderer output as styled text: SGR colour only; OSC, other CSI, C0 removed."""
        clean = _OSC_RE.sub("", out)
        clean = _CSI_NON_SGR_RE.sub("", clean)
        return Text.from_ansi(_C0_RE.sub("", clean))

    def _review_component_rows(self) -> tuple[list[str], int]:
        """Review's per-category component lines plus the non-hook count — the
        number of components Confirm actually symlinks."""
        rows = []
        for kind in self._choose_kinds():   # the same counts as the tab row and the card
            on, total = self._kind_counts(kind)
            names = [name for cat, name, flag in self.model.sel.items if cat == kind and flag]
            rows.append(f"[{CYAN}]{kind}[/] {on}/{total}: "
                        + (", ".join(names) if names else f"[{DIM}](none)[/]"))
        ncomp = sum(1 for cat, _n, on in self.model.sel.items
                    if on and cat not in ("hooks", GLOBAL_RULES_CAT))
        return rows, ncomp

    def _global_rules_on(self) -> bool | None:
        """The global-rules item's state, or None when this checkout has no such item."""
        for cat, _name, flag in self.model.sel.items:
            if cat == GLOBAL_RULES_CAT:
                return bool(flag)
        return None

    def _review_global_rules_lines(self) -> list[str]:
        """Review's global-rules bullet and per-file preview, shown only while the
        item is on (Phase 30, D-11). Previews live in ctx.state, never in per-host meta.
        With no item at all, one dim line says there is nothing to change."""
        on = self._global_rules_on()
        if on is None:
            return [f"[{DIM}]{GLOBAL_RULES_NOTHING}[/]"]
        rules = self.ctx.state.get("_global_rules")
        if not rules or not on:
            return []
        count = len(rules["changes"])
        lines = [f"[{DIM}]•[/] Rewrite codegraph's sentence in {count} global "
                 "instruction files (backup first)"]
        lines.extend(f"[{DIM}]{escape(line)}[/]" for line in rules["preview"])
        return lines

    def _review_status_blocks(self, adopted: list[HostView]) -> tuple[int, list[Text]]:
        """(on-line segment count, preview blocks) over the ADOPTED hosts only —
        a declined host skips the whole status-line section. A multi-host Review
        labels each host's first block so two panes can never read as one line."""
        nseg = 0
        shown: list[Text] = []
        for host in adopted:
            nseg += sum(len(line) for line in self.views[host.id].board.lines)
            block = self._review_host_preview(host)
            if len(self.hosts) > 1:
                block = Text.assemble(Text(f"{host.label} — ", style=DIM), block)
            shown.append(block)
        return nseg, shown

    def _review_host_preview(self, host: HostView) -> Text:
        """One adopted host's Review preview: the same real render as Arrange's board
        preview (WIZ-05), started off the UI thread on first sight of a board/width.
        Samples stand in while it runs; a failed or missing renderer adds the note."""
        pane = self.views[host.id]
        samples = "\n".join(f"[#d6dee8]{p}[/]" for p in self._preview_lines(pane))
        if not any(pane.board.lines):
            return Text.from_markup(samples)            # "(all segments off)": nothing to render
        st = self._serialize_state(host.id)
        cols = self.query_one("#rev-preview", Static).content_size.width or 100
        key = json.dumps([st["segments"], st["layout"], cols], sort_keys=True)
        cached = self.preview.review.get(host.id)
        if cached is None or cached[0] != key:
            if callable(getattr(host.engine, "render_preview", None)):
                cached = self.preview.review[host.id] = (key, None)
                self._render_preview_job(
                    host.id, st["segments"], st["layout"], cols,
                    functools.partial(self._apply_review_preview, host.id, key))
            else:
                cached = self.preview.review[host.id] = (key, "")
        out = cached[1]
        if out:
            return self._preview_text(out)
        if out is None:                                 # still rendering
            return Text.from_markup(samples)
        return Text.from_markup(f"{samples}\n[{DIM}]{PREVIEW_FALLBACK_NOTE}[/]")

    def _apply_review_preview(self, host_id, key, out) -> None:
        cached = self.preview.review.get(host_id)
        if cached is None or cached[0] != key:          # the board or width changed since
            return
        self.preview.review[host_id] = (key, out or "")
        if self.flow.step == STEP_REVIEW:
            self._render_review()
            # New content can add a scrollbar and narrow the box: re-key once laid out.
            self.call_after_refresh(self._rekey_review)

    def _rekey_review(self) -> None:
        if self.flow.step == STEP_REVIEW:
            self._render_review()

    def _host_action(self, host_id: str) -> str:
        """The action one host's outcome takes, from its live pane state: the same
        table as setup's `_statusline_action`. Reads the board's own dirty flag, not
        the copy-source `model.state["dirty"]` setup seeds."""
        st = self.views[host_id].model.state
        start = st.get("start_state", "unset")
        on = bool(st.get("adopt"))
        if start == "foreign":
            if on:
                return "replace_foreign"
            return "remove_foreign" if st.get("foreign_choice") == "remove" else "keep_foreign"
        if on:
            if start != "ours":
                return "wire"
            forced = bool(self.ctx.state.get("_examples_forced"))
            return "update" if (self._serialize_state(host_id)["dirty"] or forced) else "unchanged"
        return "remove_ours" if start == "ours" else "unchanged"

    def _review_what_lines(self, ncomp: int) -> list[str]:
        """What happens on Confirm: the components, then one outcome line per detected
        host (its action text), the doctor line when a host writes ai-kit's entry, or
        the "no host detected" line when there is no host."""
        what = [f"[{DIM}]•[/] Symlink [bold]{ncomp}[/] components into "
                f"~/.claude/(agents|commands|skills)/"]
        writes = ("wire", "update", "replace_foreign")
        for host in self.hosts:
            action = self._host_action(host.id)
            text = OUTCOME_TEXT[action].format(label=escape(host.label))
            if action in writes:
                text += f" ({host.config_label} + {host.wiring_label})"
            what.append(f"[{DIM}]•[/] {escape(host.label)}: {text}")
        if any(self._host_action(h.id) in writes for h in self.hosts):
            what.append(f"[{DIM}]•[/] Validate with the status line doctor before saving")
        if not self.hosts:
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
            rp.update(Text("\n").join(shown))
        self.query_one("#rev-what", Static).update(
            "\n".join([*self._review_what_lines(ncomp),
                       *self._review_global_rules_lines()]))
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

    def _done_host_lines(self) -> list[str]:
        """One Done line per host whose status line the commit left kept or removed."""
        lines = []
        for h in self.hosts:
            row = self._done_host_rows().get(h.id) or {}
            action = row.get("action")
            text = None
            if action == "remove_ours":
                text = DONE_OFF_LINE
            elif action == "keep_foreign":
                text = DONE_KEPT_LINE
            elif action == "remove_foreign" and row.get("ok", True):
                text = DONE_REMOVED_FOREIGN_LINE
            if text:
                lines.append(f"[{DIM}]•[/] {text.format(label=escape(h.label))}")
        return lines

    def _done_hint_lines(self) -> list[str]:
        """The `d` hint, shown only when a config doctor is injected (both outcomes)."""
        return [f"[{DIM}]•[/] {DONE_DOCTOR_HINT}"] if self.ctx.doctor is not None else []

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
            nxt_w.update("\n".join([*self._done_failure_lines(outcome),
                                    *self._done_hint_lines()]))
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
                       "press o on a host pane to turn the status line on.")
        nxt_w.update("\n".join([*self._done_host_lines(), *nxt, *self._done_hint_lines()]))

    # ---- input -----------------------------------------------------------
    def on_key(self, event: events.Key) -> None:
        if len(self.screen_stack) > 1:
            return                 # a pushed screen (the modal, the doctor) owns the key
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
        kind = self._active_kind()
        if kind is None:            # nothing installable: only Enter acts
            return k == "enter" and self._enter_arrange()
        sel = self.model.sel
        if k in ("left", "right"):
            self._switch_kind(1 if k == "right" else -1)
        elif k in ("up", "down"):
            self._move_in_kind(1 if k == "down" else -1)
        elif k == "space":
            sel.toggle_cursor()
        elif ch in ("a", "n"):
            sel.set_category(kind, ch == "a")
        elif ch in ("A", "N"):
            # Per kind, never set_all: that would also flip the global-rules item.
            for every in self._choose_kinds():
                sel.set_category(every, ch == "A")
        elif k == "enter":
            return self._enter_arrange()
        elif k == "tab":
            pass          # consume — Tab is a no-op on Choose (never advances)
        else:
            return False
        return True

    def _switch_kind(self, step: int) -> None:
        kinds = self._choose_kinds()
        active = self._active_kind()
        if len(kinds) < 2 or active is None:
            return
        self.flow.kind_cursor[active] = self.model.sel.cursor
        self.flow.kind = kinds[(kinds.index(active) + step) % len(kinds)]
        self._sync_kind_cursor()

    def _move_in_kind(self, step: int) -> None:
        kind = self._active_kind()
        if kind is None:
            return
        self._sync_kind_cursor()
        idxs = self._kind_indexes(kind)
        new = idxs[(idxs.index(self.model.sel.cursor) + step) % len(idxs)]
        self.model.sel.cursor = new
        self.flow.kind_cursor[kind] = new

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

    def _cycle_foreign_choice(self) -> None:
        """`o` on a foreign host: keep -> remove -> custom -> keep. Only `custom` adopts
        (writes ai-kit's line); the board is never touched, so the arrangement is kept."""
        state = self.model.state
        index = FOREIGN_CHOICES.index(state.get("foreign_choice", "keep"))
        choice = FOREIGN_CHOICES[(index + 1) % len(FOREIGN_CHOICES)]
        state["foreign_choice"] = choice
        state["adopt"] = choice == "custom"

    def _key_arrange_board(self, event: events.Key) -> bool:  # pylint: disable=too-many-return-statements
        ch, k = event.character, event.key
        if ch == "o":
            self.model.state["foreign_ok"] = False   # a Yes for another choice no longer counts
            if self.model.state.get("start_state") == "foreign":
                self._cycle_foreign_choice()
            else:
                self.model.state["adopt"] = not self.model.state.get("adopt")
            return True
        if not self.model.state.get("adopt") and (k in EDIT_KEYS or ch == "r"):
            # A locked board (off, or a foreign keep/remove) keeps its arrangement.
            foreign = self.model.state.get("start_state") == "foreign"
            self.notify(FOREIGN_LOCKED_NOTICE if foreign else LOCKED_NOTICE)
            return True
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
        return self._key_arrange_board(event)

    def _board_back(self) -> None:
        """Board Esc: back to the PREVIOUS host's pane (every pane is visited, so
        the first host's pane backs out to Choose)."""
        if self.flow.host_index == 0 or not self.hosts:
            self.flow.step = STEP_CHOOSE
        else:
            self._enter_host_arrange(self.flow.host_index - 1)

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

    def _key_review(self, event: events.Key) -> bool:  # pylint: disable=too-many-return-statements
        if event.character == "g":
            on = self._global_rules_on()
            if on is None:
                return False       # no item in this checkout: `g` is not consumed
            self.model.sel.set_category(GLOBAL_RULES_CAT, not on)
            return True
        if event.key == "enter":
            if not self._has_net_change():
                self.query_one("#cta", Static).update(
                    f"[{WARN}]Nothing to write — Esc to go back, q to quit[/]")
                # Return False so on_key does NOT re-render: a re-render would
                # call _render_review and overwrite this #cta message with the
                # install CTA. Step stays REVIEW; the warning persists.
                return False
            return self._confirm_or_commit()
        if event.key == "escape":
            # Back to the last host's pane (every pane is visited, so none is skipped).
            if self.hosts:
                self._enter_host_arrange(len(self.hosts) - 1)
            else:
                self.flow.step = STEP_CHOOSE
            return True
        return False

    def _confirm_or_commit(self) -> bool:
        """Review Enter: the first host whose removal or replacement is not yet confirmed
        opens its ForeignConfirm; when none is left, the commit runs."""
        for host in self.hosts:
            if (self._host_action(host.id) in ("remove_foreign", "replace_foreign")
                    and not self.views[host.id].model.state.get("foreign_ok")):
                return self._confirm_foreign(host)
        return self._commit_now()

    def _confirm_foreign(self, host: HostView) -> bool:
        """Backup first (prepare_foreign), then the modal; a failed backup stays on Review."""
        if self.ctx.prepare_foreign is None:
            info: dict = {"error": "no backup helper injected; nothing will be written"}
        else:
            info = cast(dict, self.ctx.prepare_foreign(host.id))
        if "error" in info:
            self.notify(str(info["error"]), severity="error")
            return False
        replace = self._host_action(host.id) == "replace_foreign"
        # After this key event finishes, so the same Enter cannot reach the new modal.
        self.call_after_refresh(self.push_screen, ForeignConfirm(host.label, info, replace),
                                functools.partial(self._on_foreign_answer, host.id))
        return True

    def _on_foreign_answer(self, host_id: str, yes: bool) -> None:
        """The modal's answer: Yes authorises this host and continues; No cancels the
        whole confirm (every host's foreign_ok is cleared, REVIEWS HIGH 3)."""
        if yes:
            self.views[host_id].model.state["foreign_ok"] = True
            self._confirm_or_commit()
        else:
            for view in self.views.values():
                view.model.state["foreign_ok"] = False
        self._render()

    def _commit_now(self) -> bool:
        """Run the commit (or the legacy result when no commit is injected) and show Done."""
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

    def _has_net_change(self) -> bool:
        # `_initial_enabled` is component-level state (ctx.state), not per-host:
        # a host's own state dict carries segments/layout/adopt only. A net
        # change is component differences OR ANY adopted host pane — the active
        # pane may be a host the user declined (e.g. the last host visited),
        # which must not block committing an earlier adopted host (D-22).
        initial = self.ctx.state.get("_initial_enabled", {})
        current = {(c, n): on for c, n, on in self.model.sel.items}
        actions = [self._host_action(h.id) for h in self.hosts]
        # An on host with start state `ours` always runs setup's upkeep (its persist path).
        upkeep = any(self.views[h.id].model.state.get("adopt")
                     and self.views[h.id].model.state.get("start_state") == "ours"
                     for h in self.hosts)
        return (current != initial or upkeep
                or any(a not in ("unchanged", "keep_foreign") for a in actions))

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
        st["dirty"] = board.lines != board.initial_lines or board.tray != board.initial_tray
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
        if event.key == "d" and self.ctx.doctor is not None:
            try:
                screen = self.ctx.doctor()
            except (OSError, ValueError, RuntimeError, ImportError) as exc:
                self.notify(f"config doctor failed: {exc}", severity="error")
                return True
            # After this key event, so the same key cannot reach the new screen.
            self.call_after_refresh(self.push_screen, screen)
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
