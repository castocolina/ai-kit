"""Textual wizard UI for ai-kit setup. Pure view layer: imports textual and
receives all engine behaviour via an injected WizardContext (plan A.4 seam).
Resolved on demand via ``uv run tools/setup.py`` (PEP-723 deps in setup.py).

Scope by phase:
  Phase 2 (Task 2.1) — skeleton: install-picks list visible, q/esc abort.
  Phase 2 (Task 2.2) — toggle / all / none interaction on install-picks.
  Phase 2 (Task 2.3) — summary + confirm; allow-but-confirm empty; clean abort.
  Phase 3 (Task 3.2) — _PicksScreen + LayoutBoard; layout chip moves + off-tray.
  Phase 3 (Task 3.3) — #preview Static widget; debounced real-renderer call.

Toggle approach (Task 2.2):
  ctx.selection is the authoritative model.  We use a HYBRID strategy:

  space (toggle):
    SelectionList has a built-in ``space`` binding (widget level) that fires
    before any App-level binding.  We do NOT override it; instead we listen for
    the ``SelectionList.SelectionToggled`` message that the widget emits after
    each native toggle.  The message carries the option value (= index into
    ctx.selection.items), so we call ctx.selection.toggle(index) to keep the
    model in sync, then refresh the glyph labels via _refresh_picks().

  a / n (all / none):
    These are _PicksScreen-level bindings (no widget conflict).  They call
    ctx.selection.set_all(True/False) first, then _refresh_picks() to
    rebuild the SelectionList — which also re-sets the widget's native
    selected state from the authoritative model.

  After any interaction ctx.selection.items enabled flags are accurate, so
  result.selection.category_sets(CATEGORIES) in setup.py is correct.

  Glyph rendering (FR-W.7): on/off state is conveyed by glyph SHAPE (◉/◯),
  not color alone, so the label itself carries the signal.  SelectionList's
  built-in checkbox is a secondary redundant indicator.

Summary + confirm flow (Task 2.3):
  enter on the picks screen pushes SummaryScreen (a plain Screen).
  SummaryScreen shows a plain-text list of enabled picks and any layout info
  from app.state — readable without color (FR-W.7 accessibility).
  enter/y on SummaryScreen confirms (sets app.result) and exits.
  If no picks are enabled, enter/y on SummaryScreen first pushes
  EmptyConfirmModal (ModalScreen[bool]).  The modal defaults to No;
  only an explicit 'y' returns True to install nothing.  Any other key
  (enter, n, esc, q) returns False which dismisses the modal back to picks.
  q/esc from the picks screen  → clean abort (result = None).
  q/esc from SummaryScreen     → clean abort (result = None).
  q/esc from EmptyConfirmModal → dismiss modal, return to picks (result unchanged).

Layout board (Task 3.2 / FR-W.4):
  tab from _PicksScreen pushes LayoutBoard.  The board renders one row per
  layout line (using ctx.engine.groups) plus an OFF-TRAY row.  Arrow keys
  (and h/j/k/l) move the focused chip; space toggles it to/from the tray.
  Focus glyph: [>chip<] vs [chip] — shape-only, no color (FR-W.7).
  tab/escape from the board pops back to picks; enter pushes SummaryScreen.
  n/p cycle chip focus without moving chips.
  app.state carries the live-edited state; ctx.state is the read-only initial.

Preview pane (Task 3.3 / FR-W.4 / Task 6):
  A ``#board-preview`` Static widget in LayoutBoard shows the real rendered
  status line by calling ``ctx.engine.render_preview(segments, layout=layout)``,
  which shells out to ``python3 -S status-line.py``.  Rapid edits are debounced
  with a ~100 ms Textual timer so only the latest state fires the subprocess.
  If render_preview returns ``""`` or raises, the widget shows
  ``"— preview unavailable —"``.
  The subprocess runs in a thread worker (``@work(thread=True, exclusive=True)``)
  so the UI event loop is never blocked.
  Epoch guard (Task 6): the epoch is captured at schedule time and passed as an
  argument to ``_run_preview(epoch)``.  The worker discards stale results by
  checking ``epoch != self._preview_epoch`` at ENTRY and again before calling
  ``call_from_thread`` — prevents a slow W1 from overwriting a faster W2's
  output when both threads complete out of order.
"""
from __future__ import annotations

import shutil
from typing import ClassVar, NamedTuple

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen, Screen
from textual.widget import Widget
from textual.widgets import Label, Static

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_PREVIEW_DEBOUNCE_SECS: float = 0.1   # 100 ms quiet period before firing subprocess

# ---------------------------------------------------------------------------
# Color palette (GitHub-dark — lifted verbatim from mockup-textual.py)
# ---------------------------------------------------------------------------

FG      = "#c9d1d9"
DIM     = "#6e7681"
LINE    = "#30363d"
ACCENT  = "#58a6ff"
GREEN   = "#3fb950"
WARN    = "#d29922"
PINK    = "#db61a2"
CYAN    = "#39c5cf"
KEYCAP  = "#21262d"

# ---------------------------------------------------------------------------
# Step constants
# ---------------------------------------------------------------------------

STEP_CHOOSE  = 0
STEP_ARRANGE = 1
STEP_REVIEW  = 2
STEP_DONE    = 3

LANE_GATE: dict[int, int] = {1: 20, 2: 30}  # 0-based line index → min terminal rows required

TITLES = [
    "Choose what to install",
    "Arrange your status line",
    "Review & confirm",
    "✓ ai-kit is installed",
]

SUBS = [
    "Toggle skills, agents and commands",
    "Drag segments across lines",
    "Check your selections before writing",
    "Run the doctor to verify your setup",
]

# Each tuple: (label, key, is_primary)
FOOTERS: list[list[tuple[str, str, bool]]] = [
    [("Continue", "enter", True), ("Toggle", "space", False),
     ("Move", "↑↓", False), ("Category", "a/n", False), ("Help", "?", False)],
    [("Continue", "enter", True), ("Back", "esc", False), ("Move", "←→", False),
     ("Line", "↑↓", False), ("On/off", "space", False), ("Reset", "r", False),
     ("Help", "?", False)],
    [("Install", "enter", True), ("Back", "esc", False), ("Help", "?", False)],
    [("Finish & exit", "enter", True)],
]

QUIT_KEY: tuple[str, str] = ("Quit", "q")

# Per-step key legend for the Help modal (Task 8).
# Each entry: (key, description).
HELP: dict[int, list[tuple[str, str]]] = {
    STEP_CHOOSE: [
        ("↑ ↓", "Move the highlight between components"),
        ("Space", "Install / skip the highlighted component"),
        ("a / n", "Select all / none in the current category"),
        ("A / N", "Select all / none across every category"),
        ("Enter", "Continue to Arrange"),
        ("q", "Quit the installer"),
    ],
    STEP_ARRANGE: [
        ("← →", "Reorder the focused chip within its line"),
        ("↑ ↓", "Move the chip across lines (↑ off Line 1 → OFF tray)"),
        ("Space", "Turn the focused segment on/off (off → tray)"),
        ("Tab / ⇧Tab", "Focus the next / previous chip"),
        ("r", "Reset the layout to defaults"),
        ("Enter", "Continue to Review"),
        ("Esc", "Back to Choose"),
        ("q", "Quit the installer"),
    ],
    STEP_REVIEW: [
        ("Enter", "Install / write the config"),
        ("Esc", "Back to Arrange"),
        ("q", "Quit the installer"),
    ],
    STEP_DONE: [
        ("Enter", "Finish and exit"),
        ("q", "Quit"),
    ],
}

# ---------------------------------------------------------------------------
# Public data types (consumed by setup.py via lazy import)
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


class WizardCrash(Exception):
    """Raised by run_wizard when the Textual app exits due to an unhandled
    exception.

    Textual 8.x swallows unhandled exceptions (stores in app._exception and
    triggers a graceful shutdown rather than propagating).  run_wizard checks
    app._exception after app.run() returns and re-signals it as WizardCrash
    so callers can distinguish a crash from a clean user abort (None result).

    The original exception is available as __cause__ (via ``raise … from``).
    """


class _StepChange(Message):
    """Internal message: wizard should advance to ``step``."""

    def __init__(self, step: int) -> None:
        super().__init__()
        self.step = step


class AdvanceStep(Message):
    """Posted by _PicksScreen to request a step transition to ``step``."""

    def __init__(self, step: int) -> None:
        super().__init__()
        self.step = step


# Minimum terminal dimensions required to enter the alternate screen.
# Any sane terminal (80×24) is well above these; they exist to catch
# CI / headless / pipe mis-uses early, before the TUI messes up the screen.
_MIN_TERMINAL_COLS: int = 40
_MIN_TERMINAL_ROWS: int = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pick_label(cat: str, name: str, on: bool) -> str:
    """Return the glyph-prefixed label for a pick option.

    Glyph shape encodes state (FR-W.7 accessibility): ◉ = enabled, ◯ = disabled.
    """
    glyph = "◉" if on else "◯"
    return f"{glyph} {cat}/{name}"


def _build_summary_text(ctx: WizardContext, state: dict) -> str:
    """Build a plain-text summary of the current selection and state.

    ``state`` must be the LIVE app.state (not the frozen ctx.state initial copy).
    Readable without color (FR-W.7 accessibility).
    """
    lines: list[str] = ["─" * 50, "  Install Summary", "─" * 50, ""]

    # Box 1: Components to install, grouped by category
    all_items = list(ctx.selection.items)  # type: ignore[union-attr]
    enabled = [(cat, name) for cat, name, on in all_items if on]
    n_enabled = len(enabled)
    n_disabled = len(all_items) - n_enabled
    if enabled:
        lines.append("  Components to install:")
        cats_seen: list[str] = []
        cat_items: dict[str, list[str]] = {}
        for cat, name in enabled:
            if cat not in cat_items:
                cats_seen.append(cat)
                cat_items[cat] = []
            cat_items[cat].append(name)
        for cat in cats_seen:
            lines.append(f"    [{cat}]")
            for name in cat_items[cat]:
                lines.append(f"      ◉  {name}")
    else:
        lines.append("  (no components selected)")
    lines.append("")

    # Box 2: Status-line plan — reads LIVE state["adopt"], not frozen ctx.state
    sl = ctx.status_line if ctx.status_line else {}
    sl_state = sl.get("state", "unset")
    adopt = state.get("adopt", False)  # LIVE app.state — ctx.state is frozen initial
    if adopt:
        lines.append(f"  Status line: {sl_state}  →  Will configure")
        lines.append("    • Writes ~/.config/ai-kit/statusline.toml")
        lines.append("    • Sets settings.json statusLine")
        lines.append("    • Runs doctor")
    else:
        kept = sl.get("current_command") or "(none)"
        lines.append(f"  Status line: unchanged  (kept: {kept})")
    lines.append("")

    # Layout info — reads LIVE state["layout"]
    layout = state.get("layout")
    if layout:
        lines.append("  Layout:")
        for row in layout:
            segs = ", ".join(row.get("segments", []))
            lines.append(f"    row (min_rows={row.get('min_rows', 0)}): {segs}")
        lines.append("")

    # Box 3: What happens (always shown) — filesystem consequences
    lines.append("  What happens:")
    lines.append(
        f"    • Symlink {n_enabled} selected component(s)"
        " into ~/.claude/{skills,agents,commands}/"
    )
    if n_disabled > 0:
        lines.append(f"    • Unlink {n_disabled} deselected component(s)")
    lines.append("")

    lines.append("─" * 50)
    lines.append("  enter = install  |  esc = back  |  q = quit")
    lines.append("─" * 50)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Rendering helpers (Task 2)
# ---------------------------------------------------------------------------

def _render_header(step: int, total: int = 3) -> str:
    """Return a Rich markup string of step pips for the wizard header.

    At STEP_DONE all *total* pips are GREEN.  Otherwise pips at index
    <= *step* are filled ACCENT (current + past), future pips are LINE.
    Matches the mockup-textual.py ``range(3)`` design exactly.
    """
    if step == STEP_DONE:
        return " ".join(f"[{GREEN}]●[/]" for _ in range(total))
    return " ".join(
        f"[{ACCENT}]●[/]" if k <= step else f"[{LINE}]○[/]"
        for k in range(total)
    )


def _cap(label: str, primary: bool = True) -> str:
    """Return a Rich markup keycap pill for *label*.

    Primary (action keys): blue-tinted background.
    Secondary (e.g. Quit): dark KEYCAP background.
    """
    if primary:
        return f"[#cae3ff on #10325c] {label} [/]"
    return f"[#e6edf3 on {KEYCAP}] {label} [/]"


def _render_footer(keys: list[tuple[str, str, bool]]) -> str:
    """Return Rich markup for the left footer key entries (QUIT_KEY excluded).

    *keys* is a list of ``(label, key, is_primary)`` tuples.  Entries are
    separated by a │ glyph.  The QUIT_KEY entry is rendered separately via
    ``_render_footer_quit()`` and placed in a right-aligned ``#footer-q``
    Static widget (matching the two-widget approach in mockup-textual.py).
    """
    sep = f"   [{LINE}]│[/]   "
    parts = [
        _cap(key, primary) + " " + label
        for label, key, primary in keys
    ]
    return sep.join(parts)


def _render_footer_quit() -> str:
    """Return Rich markup for the right-aligned QUIT_KEY footer entry."""
    quit_label, quit_key = QUIT_KEY
    return _cap(quit_key, False) + " " + quit_label


def _chip(label: str, focused: bool, parked: bool = False) -> str:
    """Return a Rich markup chip for a segment label.

    Focused chips use ``\\[>label<]`` bracket notation (FR-W.7 shape encoding).
    The ``[>`` is backslash-escaped so Rich renders it as a literal bracket
    rather than silently dropping it as an unknown markup tag.  Parked
    (disabled) chips wrap the label in parentheses — ``(label)`` — with a
    dimmed colour so the literal ``(label)`` string appears contiguously in raw
    PTY bytes (used as an assertion anchor by PTY tests).  Active unfocused
    chips are space-padded with the standard FG colour.
    """
    if focused:
        return (
            f"[{PINK}]\\[>[/]"
            f"[bold #ffffff on #1b1016]{label}[/]"
            f"[{PINK}]<][/]"
        )
    if parked:
        # Parked (disabled) chips render as (label) with dimmed colour so the
        # literal "(label)" appears as a contiguous string in raw PTY bytes —
        # PTY tests use this as an assertion anchor.
        return f"[{DIM} on #0d1117]({label})[/]"
    return f"[{FG} on #0d1117] {label} [/]"


class WizardHeader(Horizontal):
    """Step-pip header widget.  Horizontal container with a left brand title
    and a right step/pips indicator — matching mockup-textual.py #headerbar.

    Layout: ``#header-title`` (1fr, ACCENT) ← "─ ai-kit install wizard"
             ``#header-right`` (auto, DIM)  ← "Step N of 3  ● ○ ○"
    """

    def __init__(self, step: int) -> None:
        super().__init__(id="headerbar")
        self._step = step

    def compose(self) -> ComposeResult:
        yield Static("─ ai-kit install wizard", id="header-title")
        yield Static("", id="header-right")

    def on_mount(self) -> None:
        pips = _render_header(self._step)
        if self._step < STEP_DONE:
            label = f"[{DIM}]Step {self._step + 1} of 3[/]"
        else:
            label = f"[{GREEN}]Done[/]"
        self.query_one("#header-right", Static).update(f"{label}    {pips}")


class WizardFooter(Horizontal):
    """Step-key footer widget.  Renders the key bar for *step* via
    ``_render_footer`` (left) and ``_render_footer_quit`` (right).

    The widget is a ``Horizontal`` container composed of two Static children:
    ``#footer-left`` (``width: 1fr``) holds the step keys, and ``#footer-q``
    (``width: auto``, right-aligned via CSS) holds the Quit entry — matching
    the two-widget pattern from mockup-textual.py.  Pass *keys* to override
    the default ``FOOTERS`` entry.
    """

    def __init__(
        self,
        step: int,
        keys: list[tuple[str, str, bool]] | None = None,
    ) -> None:
        super().__init__(id="footerbar")
        self._step = step
        self._keys = keys if keys is not None else FOOTERS[step]

    def compose(self) -> ComposeResult:
        yield Static(id="footer-left")
        yield Static(id="footer-q")

    def on_mount(self) -> None:
        self.query_one("#footer-left", Static).update(_render_footer(self._keys))
        self.query_one("#footer-q", Static).update(_render_footer_quit())

    def update_step(self, step: int) -> None:
        """Re-render the footer key bar for *step*."""
        self._step = step
        self._keys = FOOTERS[step]
        self.query_one("#footer-left", Static).update(_render_footer(self._keys))


# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------

class EmptyConfirmModal(ModalScreen):  # type: ignore[type-arg]
    """Modal shown when nothing is selected or when there is no net change.

    Accepts an optional ``message`` to display context-sensitive text:
    - "Nothing selected — confirm abort?"  (empty selection)
    - "No changes — nothing to write. Confirm exit?"  (no net change)

    Defaults to No.  Only 'y' returns True (proceed / confirm).
    enter/n/esc/q all return False (continue editing).

    'enter' is handled via key_enter (not a BINDING) for the same reason as
    SummaryScreen: the forwarded enter event that caused SummaryScreen.key_enter
    to push this modal continues through the event loop; if 'enter' were in
    BINDINGS, App._check_bindings would find it on EmptyConfirmModal immediately
    after mount — before the user has seen the modal — and dismiss it via
    action_confirm_no.  key_enter() is dispatched only when EmptyConfirmModal is
    the direct recipient of a NEW key event, not during the App's forwarded-event
    _check_bindings pass.
    """

    BINDINGS: ClassVar[list] = [
        ("y", "confirm_yes", "Yes — confirm"),
        # enter handled via key_enter — see class docstring.
        ("n", "confirm_no", "No — continue editing"),
        ("escape", "confirm_no", "No — continue editing"),
        ("q", "confirm_no", "No — continue editing"),
    ]

    def __init__(self, message: str | None = None) -> None:
        super().__init__()
        self._modal_message: str = message or "Nothing selected — confirm abort?"

    def key_enter(self, event) -> None:  # type: ignore[override]
        """Default no — handled as key_enter to avoid the forwarded-enter double-fire."""
        self.action_confirm_no()

    def compose(self) -> ComposeResult:
        yield Label(
            f"\n"
            f"  {self._modal_message}\n"
            "\n"
            "  [y] Yes, confirm   [enter/n/esc] No, continue editing\n",
            id="empty-confirm-label",
        )

    def action_confirm_yes(self) -> None:
        """Explicit yes: proceed with empty install."""
        self.dismiss(True)

    def action_confirm_no(self) -> None:
        """Default no: return to picks."""
        self.dismiss(False)


class HelpModal(ModalScreen):  # type: ignore[type-arg]
    """Contextual help overlay — shows the full key legend for *step*.

    Reads ``HELP[step]`` (not ``FOOTERS``) so that bindings the footer
    omits for space (e.g. ``A/N`` global all/none at STEP_CHOOSE) are
    still visible.  Dismissed by Esc, q, or ?.
    """

    BINDINGS: ClassVar[list] = [
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
        ("question_mark", "dismiss", "Close"),
    ]

    def __init__(self, step: int) -> None:
        super().__init__()
        self._step = step

    def compose(self) -> ComposeResult:
        rows = HELP.get(self._step, [])
        lines = "\n".join(
            f"[bold {ACCENT}]{key}[/]  {desc}"
            for key, desc in rows
        )
        yield Vertical(
            Static(
                f"[bold {FG}]Keys — {TITLES[self._step]}[/]\n\n{lines}",
                id="help-body",
            ),
            id="help-modal",
        )

    def action_dismiss(self) -> None:
        """Dismiss the help modal."""
        self.dismiss()


class SummaryScreen(Screen):  # type: ignore[type-arg]
    """Review-only summary of selected picks, status-line plan, and layout.

    enter/y → guard check, then confirm (or push EmptyConfirmModal if blocked).
    escape  → pop back to STEP_ARRANGE (LayoutBoard).
    q       → abort (result stays None, app exits).
    """

    BINDINGS: ClassVar[list] = [
        # enter is handled via key_enter (NOT a BINDING) to avoid the spurious
        # double-fire bug: when LayoutBoard.key_enter pushes SummaryScreen in
        # response to an enter keypress, the textual event loop processes a
        # forwarded copy of that same enter event with self.screen already set to
        # SummaryScreen.  If enter were in BINDINGS, _check_bindings() (called
        # from App._on_key for the forwarded event) would find it and fire
        # action_confirm immediately — before the user gets to see the summary.
        # key_enter() is dispatched via dispatch_key(self, event) where self is
        # the SummaryScreen instance; it only fires when SummaryScreen is the
        # DIRECT recipient of an event, not during the App's forwarded-event
        # _check_bindings pass.
        ("y", "confirm", "Confirm"),
        ("q", "abort", "Cancel"),
        ("escape", "back_to_arrange", "Back"),
    ]

    def _has_net_change(self, ctx: WizardContext) -> bool:
        """True if the wizard would produce any write.

        Component-change comparison uses the frozen ctx.state["_initial_enabled"]
        snapshot (correct baseline).  The adopt flag MUST be read from the LIVE
        app.state — ctx.state is the frozen initial snapshot and never reflects
        the user's gate choice.
        """
        initial = ctx.state.get("_initial_enabled", {})
        current = {(cat, name): on for cat, name, on in ctx.selection.items}  # type: ignore[union-attr]
        component_changed = current != initial
        adopt = self.app.state.get("adopt", False)  # LIVE — not frozen ctx.state
        return component_changed or adopt

    async def key_enter(self, event) -> None:  # type: ignore[override]
        """Confirm via enter key.

        Handled as key_enter (not a BINDING) to avoid the spurious double-fire
        when on_event forwards the navigation enter to SummaryScreen's binding
        chain before the user has seen the summary.
        """
        await self.action_confirm()

    def compose(self) -> ComposeResult:
        yield WizardHeader(STEP_REVIEW)
        yield Static(TITLES[STEP_REVIEW], id="step-title")
        yield Static(SUBS[STEP_REVIEW], id="step-sub")
        yield Label(
            _build_summary_text(self.app.ctx, self.app.state),  # type: ignore[attr-defined]
            id="summary-text",
        )
        yield WizardFooter(STEP_REVIEW)

    async def action_confirm(self) -> None:  # type: ignore[override]
        """enter/y — two-trigger guard, then commit or open EmptyConfirmModal."""
        ctx = self.app.ctx  # type: ignore[attr-defined]

        # Trigger 1: no net change (selection unchanged AND adopt=False)
        if not self._has_net_change(ctx):
            await self.app.push_screen(  # type: ignore[attr-defined]
                EmptyConfirmModal("No changes — nothing to write. Confirm exit?"),
                self._on_empty_confirm,
            )
            return

        # Trigger 2: selection is empty and no external segments enabled
        has_enabled = any(row[2] for row in ctx.selection.items)  # type: ignore[union-attr]
        has_external = any(
            self.app.state["segments"].get(seg["id"], False)  # type: ignore[attr-defined]
            for seg in ctx.external_segments
        ) if ctx.external_segments else False
        if not has_enabled and not has_external:
            await self.app.push_screen(  # type: ignore[attr-defined]
                EmptyConfirmModal("Nothing selected — confirm abort?"),
                self._on_empty_confirm,
            )
            return

        # All guards passed — commit result and exit
        self.app.result = WizardResult(  # type: ignore[attr-defined]
            ctx.selection,
            self.app.state,  # type: ignore[attr-defined]
        )
        self.app.exit()  # type: ignore[attr-defined]

    def _on_empty_confirm(self, proceed: bool | None) -> None:
        """Callback from EmptyConfirmModal.

        True  → confirm (set result and exit).
        False → stay on SummaryScreen (do nothing — user can Esc to go back).
        """
        if proceed:
            ctx = self.app.ctx  # type: ignore[attr-defined]
            self.app.result = WizardResult(  # type: ignore[attr-defined]
                ctx.selection,
                self.app.state,  # type: ignore[attr-defined]
            )
            self.app.exit()  # type: ignore[attr-defined]
        # False → do nothing, stay on SummaryScreen

    def action_back_to_arrange(self) -> None:
        """escape — pop SummaryScreen back to STEP_ARRANGE (LayoutBoard)."""
        self.app._step = STEP_ARRANGE  # type: ignore[attr-defined]  # I-1: sync step before pop
        self.app.pop_screen()  # type: ignore[attr-defined]

    def action_abort(self) -> None:
        """q from summary — clean abort."""
        self.app.result = None  # type: ignore[attr-defined]
        self.app.exit()  # type: ignore[attr-defined]


class GatePrompt(Widget):
    """Adoption-gate prompt shown at the start of STEP_ARRANGE.

    Renders the appropriate question based on ``ctx.status_line["state"]``:
    - ``"ours"``    → gate skipped entirely (LayoutBoard handles it in on_mount)
    - ``"unset"``   → "Wire status line? [Y/n]"
    - ``"foreign"`` → "Existing status line detected. Replace with ai-kit? [y/N]"
    """

    can_focus = False

    def compose(self) -> ComposeResult:
        yield Static("", id="gate-text", markup=False)

    def on_mount(self) -> None:
        sl = self.app.ctx.status_line  # type: ignore[attr-defined]
        state = sl.get("state", "unset")
        if state == "unset":
            text = "Wire status line? [Y/n]"
        elif state == "foreign":
            cmd = sl.get("current_command") or "(unknown)"
            text = (
                f"Existing status line detected.\n"
                f"Current command: {cmd}\n"
                "Replace with ai-kit? [y/N]"
            )
        else:
            text = ""
        self.query_one("#gate-text", Static).update(text)


class LayoutBoard(Widget):  # type: ignore[type-arg]
    """Interactive layout editor board (STEP_ARRANGE body widget).

    Opens with an adoption gate (GatePrompt).  Once the user answers y/n/enter,
    the gate is replaced by four bordered panels:
      #board-lanes   — active line chips
      #board-detail  — focused-chip metadata
      #board-tray    — off-tray chips
      #board-preview — live preview placeholder (wired in Task 6)

    ``#board-label`` is a hidden test-helper Label that mirrors the lane text as
    plain (non-Rich) strings for unit-test assertions.

    FR-W.7 shape encoding: focused = [>chip<], unfocused = [chip].
    """

    can_focus = True

    BINDINGS: ClassVar[list] = [
        ("right,l", "move_right", "Move right"),
        ("left,h", "move_left", "Move left"),
        ("down,j", "move_down", "Move down"),
        ("up,k", "move_up", "Move up"),
        ("space", "toggle_tray", "Toggle tray"),
        ("n", "focus_next_chip", "Next chip"),
        ("p", "focus_prev_chip", "Prev chip"),
        ("tab", "focus_next_panel", "Next panel"),
        ("shift+tab", "focus_prev_panel", "Prev panel"),
        ("r", "reset_layout", "Reset"),
        ("enter", "advance_step", "Next"),
    ]

    def __init__(self) -> None:
        super().__init__(id="step-arrange")
        self._focused_seg: str | None = None
        self._focus_panel: int = 0
        self._gate_done: bool = False
        self._preview_epoch: int = 0

    def compose(self) -> ComposeResult:
        yield WizardHeader(STEP_ARRANGE)
        yield Static(TITLES[STEP_ARRANGE], id="step-title")
        yield Static(SUBS[STEP_ARRANGE], id="step-sub")
        yield GatePrompt()
        yield WizardFooter(STEP_ARRANGE)

    def on_mount(self) -> None:
        """Skip gate when status_line state is 'ours'; else show GatePrompt."""
        sl = self.app.ctx.status_line  # type: ignore[attr-defined]
        if sl.get("state") == "ours":
            self._gate_done = True
            self.app.state["adopt"] = True  # type: ignore[attr-defined]
            self._open_board()
        self.call_after_refresh(self.focus)

    # ------------------------------------------------------------------
    # Board lifecycle
    # ------------------------------------------------------------------

    def _open_board(self) -> None:
        """Remove GatePrompt, mount four panels + test-helper label."""
        footer = self.query_one("#footerbar")
        for w in list(self.query(GatePrompt)):
            w.remove()
        self.mount(
            Static("", id="board-lanes", markup=True),
            Static("", id="board-detail", markup=True),
            Static("", id="board-tray", markup=True),
            Static("— preview unavailable —", id="board-preview", markup=True),
            Label("", id="board-label", classes="sr-only"),
            before=footer,
        )
        self.call_after_refresh(self._init_board)

    def _show_skip_confirm(self) -> None:
        """Replace GatePrompt with a one-line 'no writes' confirmation.

        Called when the user declines adoption (key_n, or Enter on a foreign
        status line).  Does NOT open the board editor panels.
        """
        footer = self.query_one("#footerbar")
        for w in list(self.query(GatePrompt)):
            w.remove()
        self.mount(Static(
            "No status-line writes — component install only.",
            id="gate-confirm",
            markup=False,
        ), before=footer)

    def _init_board(self) -> None:
        """Seed _focused_seg and trigger first render + preview."""
        groups = self.app.ctx.engine.groups(self.app.state)  # type: ignore[attr-defined]
        for _label, chips in groups:
            if chips:
                self._focused_seg = chips[0]
                break
        self._render_board()
        self._schedule_preview()

    # ------------------------------------------------------------------
    # Gate key handlers
    # ------------------------------------------------------------------

    def key_y(self, event) -> None:  # type: ignore[override]
        """y — answer adoption gate Yes."""
        if self._gate_done:
            return
        event.prevent_default()
        event.stop()
        self.app.state["adopt"] = True  # type: ignore[attr-defined]
        self._gate_done = True
        self._open_board()

    def key_n(self, event) -> None:  # type: ignore[override]
        """n — answer adoption gate No (skip status-line writes)."""
        if self._gate_done:
            return
        event.prevent_default()
        event.stop()
        self.app.state["adopt"] = False  # type: ignore[attr-defined]
        self._gate_done = True
        self._show_skip_confirm()

    def key_enter(self, event) -> None:  # type: ignore[override]
        """enter — answer gate with default (Yes for unset, No for foreign).

        When gate is already dismissed, allow the BINDING action_advance_step
        to fire normally by returning early without prevent_default.
        """
        if self._gate_done:
            return
        event.prevent_default()
        event.stop()
        sl_state = self.app.ctx.status_line.get("state", "unset")  # type: ignore[attr-defined]
        adopt = sl_state != "foreign"
        self.app.state["adopt"] = adopt  # type: ignore[attr-defined]
        self._gate_done = True
        if adopt:
            self._open_board()
        else:
            self._show_skip_confirm()

    def key_escape(self, event) -> None:  # type: ignore[override]
        """esc during gate — treat as No/Keep (same as key_n).

        After the gate is dismissed, escape bubbles to WizardApp.action_back.
        """
        if not self._gate_done:
            self.key_n(event)

    # ------------------------------------------------------------------
    # Board rendering
    # ------------------------------------------------------------------

    def _all_chips(self) -> list[str]:
        """Return all visible chips: layout-line chips first, then off-tray."""
        groups = self.app.ctx.engine.groups(self.app.state)  # type: ignore[attr-defined]
        tray = self.app.ctx.engine.off_tray(self.app.state)  # type: ignore[attr-defined]
        chips: list[str] = []
        for _label, segs in groups:
            chips.extend(segs)
        chips.extend(tray)
        return chips

    def _render_board(self) -> None:
        """Update all four panels and the #board-label test-helper."""
        state = self.app.state  # type: ignore[attr-defined]
        engine = self.app.ctx.engine  # type: ignore[attr-defined]
        groups = engine.groups(state)
        tray = engine.off_tray(state)

        # --- #board-lanes (Rich markup for visible panel) ---
        lanes_lines: list[str] = []
        for label, chips in groups:
            row_chips = "  ".join(
                _chip(c, focused=(c == self._focused_seg))
                for c in chips
            )
            lanes_lines.append(f"  {label}: {row_chips}")
        lanes_widget = self.query_one("#board-lanes", Static)
        lanes_widget.update("\n".join(lanes_lines))
        lanes_widget.border_title = "Lines"
        # Apply lane gating: cosmetic/informational only — shows "needs ≥ N rows"
        # in the border subtitle when the terminal is too short for a lane.
        # The board does NOT suppress segments; the renderer (status-line.py)
        # handles actual row-gating at render time.
        gated_notes: list[str] = []
        for _idx in sorted(LANE_GATE):
            if self.app.size.height < LANE_GATE[_idx]:  # type: ignore[attr-defined]
                gated_notes.append(f"≥ {LANE_GATE[_idx]} rows")
        if gated_notes:
            lanes_widget.border_subtitle = "needs " + ", ".join(gated_notes)
            lanes_widget.add_class("gated")
        else:
            lanes_widget.border_subtitle = ""
            lanes_widget.remove_class("gated")

        # --- #board-detail ---
        detail_text = ""
        if self._focused_seg:
            meta = self.app.ctx.segment_meta.get(self._focused_seg, {})  # type: ignore[attr-defined]
            desc = meta.get("description", "")
            sample = meta.get("sample", "")
            icon = meta.get("icon", "")
            detail_text = f"{icon}  {self._focused_seg}\n{desc}\nSample: {sample}"
        self.query_one("#board-detail", Static).update(detail_text)
        self.query_one("#board-detail", Static).border_title = "Detail"

        # --- #board-tray ---
        tray_chips = "  ".join(_chip(c, focused=False, parked=True) for c in tray)
        tray_text = f"  OFF-TRAY: {tray_chips}" if tray else "  (empty)"
        self.query_one("#board-tray", Static).update(tray_text)
        self.query_one("#board-tray", Static).border_title = "Off Tray"

        # --- #board-preview border title ---
        self.query_one("#board-preview", Static).border_title = "Preview"

        # --- #board-label (plain text, no Rich markup — test-helper) ---
        label_lines: list[str] = []
        for label, chips in groups:
            plain = "  ".join(
                f"[>{c}<]" if c == self._focused_seg else f"[{c}]"
                for c in chips
            )
            label_lines.append(f"  {label}: {plain}")
        if tray:
            tray_plain = "  ".join(
                f"[>{c}<]" if c == self._focused_seg else f"({c})"
                for c in tray
            )
            label_lines.append(f"  OFF-TRAY: {tray_plain}")
        self.query_one("#board-label", Label).update("\n".join(label_lines))

    # ------------------------------------------------------------------
    # Preview pane — debounced real-renderer (Task 3.3 / FR-W.4)
    # ------------------------------------------------------------------

    def _schedule_preview(self) -> None:
        """Debounce-schedule a preview render, capturing the epoch at call time.

        Increments ``_preview_epoch`` and snapshots it into the timer lambda so
        the worker can detect whether it has been superseded by a later schedule.
        """
        self._preview_epoch += 1
        epoch = self._preview_epoch
        self.set_timer(_PREVIEW_DEBOUNCE_SECS, lambda: self._run_preview(epoch))

    @work(thread=True, exclusive=True, exit_on_error=False)
    def _run_preview(self, epoch: int) -> None:
        """Thread worker: call render_preview, update #board-preview widget.

        Guards against stale results with two epoch checks:
          1. At entry — discard immediately if superseded.
          2. Before calling call_from_thread — discard if superseded while the
             subprocess ran (prevents a slow W1 from overwriting a faster W2).
        """
        if epoch != self._preview_epoch:
            return  # stale — discard
        segments = {
            k: bool(v) for k, v in self.app.state["segments"].items()  # type: ignore[attr-defined]
        }
        layout = self.app.state["layout"]  # type: ignore[attr-defined]
        try:
            text: str = self.app.ctx.engine.render_preview(segments, layout=layout)  # type: ignore[attr-defined]
        except Exception:
            text = "— preview unavailable —"
        if epoch == self._preview_epoch:
            self.app.call_from_thread(self._update_preview, text)  # type: ignore[attr-defined]

    def _update_preview(self, text: str) -> None:
        """UI-thread callback: push rendered text (or sentinel) into the widget."""
        preview = self.query_one("#board-preview", Static)
        preview.update(text or "— preview unavailable —")

    # ------------------------------------------------------------------
    # Movement helpers
    # ------------------------------------------------------------------

    def _move(self, direction: str) -> None:
        """Call layout_move, update app.state, schedule preview."""
        if self._focused_seg is None:
            return
        new_state, err = self.app.ctx.engine.layout_move(  # type: ignore[attr-defined]
            self.app.state, self._focused_seg, direction  # type: ignore[attr-defined]
        )
        if err is None:
            self.app.state = new_state  # type: ignore[attr-defined]
        self._render_board()
        self._schedule_preview()

    # ------------------------------------------------------------------
    # Actions (all guarded: no-op while gate is still open)
    # ------------------------------------------------------------------

    def action_move_right(self) -> None:
        if not self._gate_done:
            return
        if self._focused_seg is None:
            return
        tray = self.app.ctx.engine.off_tray(self.app.state)  # type: ignore[attr-defined]
        if self._focused_seg in tray:
            return
        self._move("right")

    def action_move_left(self) -> None:
        if not self._gate_done:
            return
        if self._focused_seg is None:
            return
        tray = self.app.ctx.engine.off_tray(self.app.state)  # type: ignore[attr-defined]
        if self._focused_seg in tray:
            return
        self._move("left")

    def action_move_down(self) -> None:
        if not self._gate_done:
            return
        self._move("down")

    def action_move_up(self) -> None:
        if not self._gate_done:
            return
        self._move("up")

    def action_toggle_tray(self) -> None:
        """space — toggle focused chip to/from the off-tray."""
        if not self._gate_done:
            return
        if self._focused_seg is None:
            return
        new_state, err = self.app.ctx.engine.layout_toggle(  # type: ignore[attr-defined]
            self.app.state, self._focused_seg  # type: ignore[attr-defined]
        )
        if err is None:
            self.app.state = new_state  # type: ignore[attr-defined]
        self._render_board()
        self._schedule_preview()

    def action_focus_next_chip(self) -> None:
        """n — advance focus to the next chip in display order."""
        if not self._gate_done:
            return
        chips = self._all_chips()
        if not chips:
            return
        if self._focused_seg not in chips:
            self._focused_seg = chips[0]
        else:
            idx = chips.index(self._focused_seg)
            self._focused_seg = chips[(idx + 1) % len(chips)]
        self._render_board()

    def action_focus_prev_chip(self) -> None:
        """p — retreat focus to the previous chip in display order."""
        if not self._gate_done:
            return
        chips = self._all_chips()
        if not chips:
            return
        if self._focused_seg not in chips:
            self._focused_seg = chips[-1]
        else:
            idx = chips.index(self._focused_seg)
            self._focused_seg = chips[(idx - 1) % len(chips)]
        self._render_board()

    def action_focus_next_panel(self) -> None:
        """tab — cycle panel focus forward."""
        if not self._gate_done:
            return
        self._focus_panel = (self._focus_panel + 1) % 4

    def action_focus_prev_panel(self) -> None:
        """shift+tab — cycle panel focus backward."""
        if not self._gate_done:
            return
        self._focus_panel = (self._focus_panel - 1) % 4

    def action_reset_layout(self) -> None:
        """r — reset layout to LAYOUT_DEFAULTS."""
        if not self._gate_done:
            return
        self.app.state["layout"] = self.app.ctx.engine.layout_defaults()  # type: ignore[attr-defined]
        layout = self.app.state["layout"]  # type: ignore[attr-defined]
        if layout and layout[0]["segments"]:
            self._focused_seg = layout[0]["segments"][0]
        self._render_board()
        self._schedule_preview()

    def action_advance_step(self) -> None:
        """enter — advance to STEP_REVIEW (only when gate is done)."""
        if not self._gate_done:
            return
        self.post_message(AdvanceStep(STEP_REVIEW))


class _PicksScreen(Widget):
    """Install-picks step body (STEP_CHOOSE). Widget composed into WizardApp.

    Space   → toggle cursor row.
    a/n     → per-category all-on / all-off.
    A/N     → global all-on / all-off.
    Up/Down → cursor navigation.
    Enter   → post AdvanceStep(STEP_ARRANGE) to parent app.
    Tab     → push LayoutBoard.
    """

    can_focus = True

    def __init__(self) -> None:
        super().__init__(id="step-choose")
        self._cur_cat: str = ""

    def compose(self) -> ComposeResult:
        yield WizardHeader(STEP_CHOOSE)
        yield Static(TITLES[STEP_CHOOSE], id="step-title")
        yield Static(SUBS[STEP_CHOOSE], id="step-sub")
        with Vertical(id="install-picks"):
            yield Static("", id="picks-body", markup=True)
            yield Static("", id="picks-count", markup=True)
        yield WizardFooter(STEP_CHOOSE)

    def on_mount(self) -> None:
        ctx = self.app.ctx  # type: ignore[attr-defined]
        items = ctx.selection.items
        if items:
            self._cur_cat = items[ctx.selection.cursor][0]
        self.call_after_refresh(self.focus)
        self._refresh_picks()

    def _sync_selection_to_state(self) -> None:
        ctx = self.app.ctx  # type: ignore[attr-defined]
        ctx.state["segments"].update(ctx.selection.enabled_map())

    def _refresh_picks(self) -> None:
        ctx = self.app.ctx  # type: ignore[attr-defined]
        body_lines: list[str] = []
        # Group selection items by category in first-appearance order from
        # selection.items — not engine.groups(), which orders statusline layout
        # segments and does not cover install picks.
        cats_seen: list[str] = []
        cat_idx: dict[str, list[int]] = {}
        for idx, it in enumerate(ctx.selection.items):
            cat = it[0]
            if cat not in cat_idx:
                cats_seen.append(cat)
                cat_idx[cat] = []
            cat_idx[cat].append(idx)
        for cat in cats_seen:
            indices = cat_idx[cat]
            on = sum(1 for i in indices if ctx.selection.items[i][2])
            total = len(indices)
            header = f"[{DIM}]─── {cat}  [{GREEN}]{on}[/]/{total} on ───[/]"
            body_lines.append(header)
            for idx in indices:
                it = ctx.selection.items[idx]
                on_flag = it[2]
                glyph = f"[{GREEN}]◉[/]" if on_flag else f"[{DIM}]◯[/]"
                key = it[1]
                meta = ctx.segment_meta.get(key, {})
                icon = meta.get("icon", "")
                desc = meta.get("description", "")
                foc = idx == ctx.selection.cursor
                gut = f"[{PINK}]▌[/]" if foc else " "
                nm = f"[{'#f0f6fc' if foc else FG}]{key}[/]"
                row = f"{gut} {glyph} {icon} {nm}  {desc}"
                if foc:
                    row = f"[on #161b22]{row}[/]"
                body_lines.append(row)
        if ctx.external_segments:
            ext_map = ctx.selection.enabled_map()
            on = sum(1 for ext in ctx.external_segments if ext_map.get(ext["id"], False))
            total = len(ctx.external_segments)
            body_lines.append(
                f"[{DIM}]─── external  [{GREEN}]{on}[/]/{total} on ───[/]"
            )
            for ext in ctx.external_segments:
                key = ext["id"]
                idx = next(
                    (i for i, it in enumerate(ctx.selection.items) if it[1] == key),
                    None,
                )
                on_flag = False if idx is None else ctx.selection.items[idx][2]
                glyph = f"[{GREEN}]◉[/]" if on_flag else f"[{DIM}]◯[/]"
                icon = ext.get("icon", "")
                desc = ext.get("description", "")
                foc = idx is not None and idx == ctx.selection.cursor
                gut = f"[{PINK}]▌[/]" if foc else " "
                nm = f"[{'#f0f6fc' if foc else FG}]{key}[/]"
                row = f"{gut} {glyph} {icon} {nm}  {desc}"
                if foc:
                    row = f"[on #161b22]{row}[/]"
                body_lines.append(row)
        self.query_one("#picks-body", Static).update("\n".join(body_lines))
        sel_n = sum(1 for _, _, on in ctx.selection.items if on)
        total_n = len(ctx.selection.items)
        self.query_one("#picks-count", Static).update(
            f"[{GREEN}]{sel_n}[/] of {total_n} components selected"
        )

    def key_space(self, event) -> None:  # type: ignore[override]
        event.prevent_default()
        event.stop()
        ctx = self.app.ctx  # type: ignore[attr-defined]
        ctx.selection.toggle_cursor()
        self._sync_selection_to_state()
        self._refresh_picks()

    def key_a(self, event) -> None:  # type: ignore[override]
        event.stop()
        ctx = self.app.ctx  # type: ignore[attr-defined]
        ctx.selection.set_category(self._cur_cat, True)
        self._sync_selection_to_state()
        self._refresh_picks()

    def key_n(self, event) -> None:  # type: ignore[override]
        event.stop()
        ctx = self.app.ctx  # type: ignore[attr-defined]
        ctx.selection.set_category(self._cur_cat, False)
        self._sync_selection_to_state()
        self._refresh_picks()

    def key_upper_a(self, event) -> None:  # type: ignore[override]
        event.stop()
        ctx = self.app.ctx  # type: ignore[attr-defined]
        ctx.selection.set_all(True)
        self._sync_selection_to_state()
        self._refresh_picks()

    def key_upper_n(self, event) -> None:  # type: ignore[override]
        event.stop()
        ctx = self.app.ctx  # type: ignore[attr-defined]
        ctx.selection.set_all(False)
        self._sync_selection_to_state()
        self._refresh_picks()

    def key_up(self, event) -> None:  # type: ignore[override]
        event.prevent_default()
        event.stop()
        ctx = self.app.ctx  # type: ignore[attr-defined]
        ctx.selection.move_cursor(-1)
        items = ctx.selection.items
        if items:
            self._cur_cat = items[ctx.selection.cursor][0]
        self._refresh_picks()

    def key_down(self, event) -> None:  # type: ignore[override]
        event.prevent_default()
        event.stop()
        ctx = self.app.ctx  # type: ignore[attr-defined]
        ctx.selection.move_cursor(1)
        items = ctx.selection.items
        if items:
            self._cur_cat = items[ctx.selection.cursor][0]
        self._refresh_picks()

    def key_enter(self, event) -> None:  # type: ignore[override]
        event.stop()
        self.post_message(AdvanceStep(STEP_ARRANGE))

    def key_tab(self, event) -> None:  # type: ignore[override]
        event.prevent_default()
        event.stop()
        self.post_message(AdvanceStep(STEP_ARRANGE))


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class WizardApp(App):  # type: ignore[type-arg]
    """Single-screen wizard; body container is swapped per step.

    ``q`` aborts from any step.  ``escape`` goes back one step (from
    STEP_CHOOSE it is equivalent to abort).  ``?`` opens the help modal
    (Task 8).

    ``self.ctx`` is kept alongside ``self._ctx`` for backward-compatibility:
    existing screens (_PicksScreen, LayoutBoard, SummaryScreen) reference
    ``self.app.ctx``.
    """

    ENABLE_COMMAND_PALETTE = False

    CSS = f"""
    Screen {{ background: #0d1117; }}

    #headerbar {{ height: 2; background: #161b22; border-bottom: solid {LINE}; padding: 0 1; }}
    #header-title {{ width: 1fr; color: {ACCENT}; text-style: bold; content-align: left middle; }}
    #header-right {{ width: auto; color: {DIM}; content-align: right middle; }}

    #step-choose {{ height: 1fr; }}
    #step-title {{ height: auto; text-style: bold; padding: 0 2; }}
    #step-sub {{ height: auto; color: {DIM}; margin-bottom: 1; padding: 0 2; }}
    #step-arrange {{ height: 1fr; }}
    #install-picks {{ height: 1fr; padding: 0 2; }}
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

    #board-lanes {{ border: round {CYAN}; height: auto; padding: 0 1; margin-bottom: 1;
                   background: #0f141b; border-title-color: {CYAN}; }}
    #board-detail {{ border: round {PINK}; height: auto; padding: 0 1; margin-bottom: 1;
                    background: #1b1016; border-title-color: {PINK}; }}
    #board-tray {{ border: dashed {DIM}; height: auto; padding: 0 1; margin-bottom: 1;
                  background: #0d1117; border-title-color: {DIM}; }}
    #board-preview {{ border: round {LINE}; background: #010409; height: auto; padding: 0 1;
                     border-title-color: {DIM}; }}
    .sr-only {{ display: none; }}
    """

    BINDINGS: ClassVar[list] = [
        ("q", "quit", "Cancel"),
        ("escape", "back", "Back"),
        ("question_mark", "help", "Help"),
    ]

    def __init__(self, ctx: WizardContext) -> None:
        super().__init__()
        self.ctx = ctx           # backward-compat: existing screens use self.app.ctx
        self._ctx = ctx          # new primary attr (Tasks 2+)
        self.state: dict = dict(ctx.state)  # live state; mutated by board ops
        self.result: WizardResult | None = None
        self._step: int = STEP_CHOOSE
        self._exception: BaseException | None = None

    # ------------------------------------------------------------------
    # Compose / Lifecycle
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        """Compose _PicksScreen as the default-screen body."""
        yield _PicksScreen()

    def on_mount(self) -> None:
        """Nothing to push — _PicksScreen is composed in."""

    def on_exception(self, exception: BaseException) -> None:
        """Textual lifecycle hook — called on any unhandled exception in the run loop.

        Captures the exception in ``self._exception`` so that ``run_wizard``
        can re-raise it as ``WizardCrash`` after ``app.run()`` returns.
        Textual 8.x swallows these exceptions internally; without this hook
        they would be silently discarded.
        """
        self._exception = exception
        self.exit()

    def on_advance_step(self, message: AdvanceStep) -> None:
        """Handle AdvanceStep: swap or push the appropriate body for the requested step."""
        if message.step == STEP_ARRANGE:
            self._step = STEP_ARRANGE
            self._swap_body(STEP_ARRANGE)
        elif message.step == STEP_REVIEW:
            self._step = STEP_REVIEW
            self.push_screen(SummaryScreen())
        _footer = next(iter(self.query(WizardFooter)), None)
        if _footer is not None:
            _footer.update_step(self._step)

    # ------------------------------------------------------------------
    # Step body management (scaffold — fully wired in Task 2)
    # ------------------------------------------------------------------

    def _swap_body(self, step: int) -> None:
        """Swap the active body widget for ``step``."""
        if step == STEP_ARRANGE:
            for w in list(self.query(_PicksScreen)):
                w.remove()
            self.mount(LayoutBoard())
        elif step == STEP_CHOOSE:
            for w in list(self.query(LayoutBoard)):
                w.remove()
            self.mount(_PicksScreen())

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_quit(self) -> None:
        """q — leave result as None and exit (fires from any step)."""
        self.result = None
        self.exit()

    # Alias so that existing screen BINDINGS (SummaryScreen, EmptyConfirmModal)
    # that reference ``action_abort`` by name continue to resolve correctly.
    action_abort = action_quit

    def action_back(self) -> None:
        """esc — go back one step; from STEP_CHOOSE this is equivalent to quit."""
        if self._step == STEP_CHOOSE:
            self.action_quit()
        elif self._step == STEP_ARRANGE:
            self._swap_body(STEP_CHOOSE)
            self._step = STEP_CHOOSE
            _footer = next(iter(self.query(WizardFooter)), None)
            if _footer is not None:
                _footer.update_step(self._step)
        elif self._step == STEP_REVIEW:
            self.pop_screen()
            self._step = STEP_ARRANGE
            _footer = next(iter(self.query(WizardFooter)), None)
            if _footer is not None:
                _footer.update_step(self._step)
        # STEP_DONE: no-op

    def action_help(self) -> None:
        """? — show the contextual help modal (Task 8)."""
        self.push_screen(HelpModal(self._step))


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
        Textual 8.x guarantees terminal teardown via
        ``driver.stop_application_mode()`` in a ``finally`` block, so no
        extra cleanup is needed here — but because it *swallows* exceptions
        (storing them in ``app._exception`` rather than propagating), we
        must inspect that attribute after ``app.run()`` returns.

        ``app._exception`` is a private Textual 8.x attribute (initialized in
        ``App.__init__``).  A defensive ``getattr`` with a ``None`` default is
        used so that if a future Textual version renames or removes the
        attribute, this degrades safely to "no crash detected → return result
        normally" rather than raising an ``AttributeError``.
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
