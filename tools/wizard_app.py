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

Preview pane (Task 3.3 / FR-W.4):
  A ``#preview`` Static widget in LayoutBoard shows the real rendered status
  line by calling ``ctx.engine.render_preview(app.state["segments"])``, which
  shells out to ``python3 -S status-line.py``.  Rapid edits are debounced with
  a ~100 ms Textual timer so only the latest state fires the subprocess.  If
  render_preview returns ``""`` the widget shows ``"(preview unavailable)"``.
  The subprocess runs in a thread worker (``@work(thread=True, exclusive=True)``)
  so the UI event loop is never blocked.
  Epoch guard (review fix 3.3): ``_preview_epoch`` is incremented on every
  ``_schedule_preview`` call.  ``_run_preview`` snapshots the epoch before the
  subprocess and discards stale results via a closure passed to
  ``call_from_thread`` — prevents a slow W1 from overwriting a faster W2's
  output when both threads complete out of order.  Render failures are logged
  at error level via ``self.app.log.error`` so they are visible in the Textual
  devtools log without changing user-visible behaviour.
"""
from __future__ import annotations

import shutil
import types
from typing import ClassVar, NamedTuple

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen, Screen
from textual.timer import Timer
from textual.widgets import Footer, Header, Label, SelectionList, Static

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_PREVIEW_DEBOUNCE_SECS: float = 0.1   # 100 ms quiet period before firing subprocess

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
    state: dict                 # {"segments": {key: bool}, "layout": [...], "dirty": bool}
    sample_json: str            # rendered sample input JSON for preview
    engine: types.SimpleNamespace  # callables: render_preview, apply_command, groups, order


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

    Readable without color (FR-W.7 accessibility).
    ``state`` is the live edited state (app.state), not the initial ctx.state.
    """
    lines: list[str] = ["─" * 50, "  Install Summary", "─" * 50, ""]

    # Enabled picks section
    enabled = [(cat, name) for cat, name, on in ctx.selection.items if on]  # type: ignore[union-attr]
    if enabled:
        lines.append("  Picks to install:")
        for cat, name in enabled:
            lines.append(f"    ◉  {cat}/{name}")
    else:
        lines.append("  (no picks selected)")
    lines.append("")

    # Layout info section
    layout = state.get("layout") if state else None
    if layout:
        lines.append("  Layout:")
        for row in layout:
            segs = ", ".join(row.get("segments", []))
            lines.append(f"    row (min_rows={row.get('min_rows', 0)}): {segs}")
        lines.append("")

    lines.append("─" * 50)
    lines.append("  Press enter/y to confirm  |  q/esc to cancel")
    lines.append("─" * 50)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------

class EmptyConfirmModal(ModalScreen):  # type: ignore[type-arg]
    """Modal asking whether to install nothing.

    Defaults to No.  Only 'y' returns True (proceed with empty install).
    enter/n/esc/q all return False (go back to picks).

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
        ("y", "confirm_yes", "Yes — install nothing"),
        # enter handled via key_enter — see class docstring.
        ("n", "confirm_no", "No — go back"),
        ("escape", "confirm_no", "No — go back"),
        ("q", "confirm_no", "No — go back"),
    ]

    def key_enter(self, event) -> None:  # type: ignore[override]
        """Default no — handled as key_enter to avoid the forwarded-enter double-fire."""
        self.action_confirm_no()

    def compose(self) -> ComposeResult:
        yield Label(
            "\n"
            "  Nothing selected — install nothing?\n"
            "\n"
            "  [y] Yes, install nothing   [enter/n/esc] No, go back\n",
            id="empty-confirm-label",
        )

    def action_confirm_yes(self) -> None:
        """Explicit yes: proceed with empty install."""
        self.dismiss(True)

    def action_confirm_no(self) -> None:
        """Default no: return to picks."""
        self.dismiss(False)


class SummaryScreen(Screen):  # type: ignore[type-arg]
    """Plain-text summary of selected picks + layout info.

    enter/y → confirm (or, if empty, push EmptyConfirmModal).
    q/esc   → abort (result stays None).
    """

    BINDINGS: ClassVar[list] = [
        # enter is handled via key_enter (NOT a BINDING) to avoid the spurious
        # double-fire bug: when _PicksScreen.key_enter pushes SummaryScreen in
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
        ("escape", "abort", "Cancel"),
    ]

    async def key_enter(self, event) -> None:  # type: ignore[override]
        """Confirm via enter key.

        Handled as key_enter (not a BINDING) to avoid the spurious double-fire
        when on_event forwards the navigation enter to SummaryScreen's binding
        chain before the user has seen the summary.
        """
        await self.action_confirm()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(
            _build_summary_text(self.app.ctx, self.app.state),  # type: ignore[attr-defined]
            id="summary-text",
        )
        yield Footer()

    async def action_confirm(self) -> None:  # type: ignore[override]
        """enter/y — confirm or open empty-confirm modal if nothing selected."""
        enabled = [
            row for row in self.app.ctx.selection.items if row[2]  # type: ignore[attr-defined, union-attr]
        ]
        if enabled:
            self.app.result = WizardResult(  # type: ignore[attr-defined]
                self.app.ctx.selection,  # type: ignore[attr-defined]
                self.app.state,  # type: ignore[attr-defined]
            )
            self.app.exit()  # type: ignore[attr-defined]
        else:
            await self.app.push_screen(EmptyConfirmModal(), self._on_empty_confirm)  # type: ignore[attr-defined]

    def _on_empty_confirm(self, proceed: bool | None) -> None:
        """Callback from EmptyConfirmModal.

        True  → install nothing (set result and exit).
        False → return to picks (pop back to _PicksScreen).
        """
        if proceed:
            self.app.result = WizardResult(  # type: ignore[attr-defined]
                self.app.ctx.selection,  # type: ignore[attr-defined]
                self.app.state,  # type: ignore[attr-defined]
            )
            self.app.exit()  # type: ignore[attr-defined]
        else:
            # Pop this SummaryScreen too — return to install picks.
            self.app.pop_screen()  # type: ignore[attr-defined]

    def action_abort(self) -> None:
        """q/esc from summary — clean abort."""
        self.app.result = None  # type: ignore[attr-defined]
        self.app.exit()  # type: ignore[attr-defined]


class LayoutBoard(Screen):  # type: ignore[type-arg]
    """Interactive layout editor board.

    Displays one row per layout line (chips in order) plus an OFF-TRAY row.
    Focused chip is shown with [>chip<]; unfocused with [chip] (FR-W.7: shape
    not color encodes state).

    Navigation (arrow keys / h j k l): calls ctx.engine.layout_move.
    space: calls ctx.engine.layout_toggle to move chip to/from tray.
    n/p: cycle focus among visible chips without moving them.
    tab/escape: pop back to _PicksScreen.
    enter: push SummaryScreen.
    """

    BINDINGS: ClassVar[list] = [
        ("right,l", "move_right", "Move right"),
        ("left,h", "move_left", "Move left"),
        ("down,j", "move_down", "Move down"),
        ("up,k", "move_up", "Move up"),
        ("space", "toggle_tray", "Toggle tray"),
        ("n", "focus_next_chip", "Next chip"),
        ("p", "focus_prev_chip", "Prev chip"),
        ("tab", "back", "Back to picks"),
        ("escape", "back", "Back to picks"),
        ("enter", "to_summary", "Summary"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.focused_seg: str | None = None
        self._preview_timer: Timer | None = None   # debounce handle
        self._preview_epoch: int = 0               # monotonic counter; stale-render guard

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("", id="board-label")
        yield Static("(preview unavailable)", id="preview")
        yield Footer()

    def on_mount(self) -> None:
        """Seed focused_seg to the first chip in the first non-empty layout line."""
        groups = self.app.ctx.engine.groups(self.app.state)  # type: ignore[attr-defined]
        for _label, chips in groups:
            if chips:
                self.focused_seg = chips[0]
                break
        self._render_board()
        self._schedule_preview()

    def _all_chips(self) -> list[str]:
        """Return all visible chips: layout-line chips first, then off-tray chips."""
        groups = self.app.ctx.engine.groups(self.app.state)  # type: ignore[attr-defined]
        tray = self.app.ctx.engine.off_tray(self.app.state)  # type: ignore[attr-defined]
        chips: list[str] = []
        for _label, segs in groups:
            chips.extend(segs)
        chips.extend(tray)
        return chips

    def _render_board(self) -> None:
        """Rebuild the #board-label text from current app.state."""
        groups = self.app.ctx.engine.groups(self.app.state)  # type: ignore[attr-defined]
        tray = self.app.ctx.engine.off_tray(self.app.state)  # type: ignore[attr-defined]

        text_lines: list[str] = []
        for label, chips in groups:
            chips_str = "  ".join(
                f"[>{c}<]" if c == self.focused_seg else f"[{c}]"
                for c in chips
            )
            text_lines.append(f"  {label}: {chips_str}")

        if tray:
            tray_str = "  ".join(
                f"[>{c}<]" if c == self.focused_seg else f"({c})"
                for c in tray
            )
            text_lines.append(f"  OFF-TRAY: {tray_str}")

        text_lines.append("")
        text_lines.append(
            "  Keys: ←/h left  →/l right  ↑/k up  ↓/j down"
            "  space toggle  n/p focus  tab/esc back  enter summary"
        )

        self.query_one("#board-label", Label).update("\n".join(text_lines))

    # ------------------------------------------------------------------
    # Preview pane — debounced real-renderer (Task 3.3 / FR-W.4)
    # ------------------------------------------------------------------

    def _schedule_preview(self) -> None:
        """Cancel any pending debounce timer and schedule a new one.

        After _PREVIEW_DEBOUNCE_SECS of inactivity the thread worker
        ``_run_preview`` fires the subprocess and updates #preview.
        Increments ``_preview_epoch`` so the worker can discard results
        that were superseded by a later edit while the subprocess ran.
        """
        if self._preview_timer is not None:
            self._preview_timer.stop()
        self._preview_epoch += 1
        self._preview_timer = self.set_timer(
            _PREVIEW_DEBOUNCE_SECS, self._run_preview
        )

    @work(thread=True, exclusive=True, exit_on_error=False)
    def _run_preview(self) -> None:
        """Thread worker: call render_preview, update #preview widget.

        Runs in a background thread so the event loop is never blocked.
        ``exclusive=True`` cancels any in-flight worker from a prior edit.
        ``exit_on_error=False`` keeps a renderer crash from killing the app.

        Epoch guard: snapshots ``_preview_epoch`` before the subprocess and
        discards the result if a newer render was scheduled while this one
        ran — prevents a slow W1 from overwriting a fast W2's output.
        """
        epoch: int = self._preview_epoch          # snapshot before subprocess
        segments: dict = self.app.state.get("segments", {})  # type: ignore[attr-defined]
        layout = self.app.state.get("layout")  # type: ignore[attr-defined]
        try:
            result: str = self.app.ctx.engine.render_preview(segments, layout)  # type: ignore[attr-defined]
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.app.log.error(  # type: ignore[attr-defined]
                f"render_preview failed (epoch {epoch}): {exc!r}"
            )
            result = ""
        text: str = result if result else "(preview unavailable)"

        def _apply(widget: Static, content: str, my_epoch: int, board: LayoutBoard) -> None:
            """Update widget only if no newer render has been scheduled."""
            if board._preview_epoch == my_epoch:  # pylint: disable=protected-access
                widget.update(content)

        self.app.call_from_thread(  # type: ignore[attr-defined]
            _apply,
            self.query_one("#preview", Static),
            text,
            epoch,
            self,
        )

    def _move(self, direction: str) -> None:
        """Call layout_move, update app.state, keep focus on moved chip."""
        if self.focused_seg is None:
            return
        new_state, err = self.app.ctx.engine.layout_move(  # type: ignore[attr-defined]
            self.app.state, self.focused_seg, direction  # type: ignore[attr-defined]
        )
        if err is None:
            self.app.state = new_state  # type: ignore[attr-defined]
        self._render_board()
        self._schedule_preview()

    def action_move_right(self) -> None:
        self._move("right")

    def action_move_left(self) -> None:
        self._move("left")

    def action_move_down(self) -> None:
        self._move("down")

    def action_move_up(self) -> None:
        self._move("up")

    def action_toggle_tray(self) -> None:
        """space — toggle focused chip to/from the off-tray."""
        if self.focused_seg is None:
            return
        new_state, err = self.app.ctx.engine.layout_toggle(  # type: ignore[attr-defined]
            self.app.state, self.focused_seg  # type: ignore[attr-defined]
        )
        if err is None:
            self.app.state = new_state  # type: ignore[attr-defined]
        self._render_board()
        self._schedule_preview()

    def action_focus_next_chip(self) -> None:
        """n — advance focus to the next chip in display order."""
        chips = self._all_chips()
        if not chips:
            return
        if self.focused_seg not in chips:
            self.focused_seg = chips[0]
        else:
            idx = chips.index(self.focused_seg)
            self.focused_seg = chips[(idx + 1) % len(chips)]
        self._render_board()

    def action_focus_prev_chip(self) -> None:
        """p — retreat focus to the previous chip in display order."""
        chips = self._all_chips()
        if not chips:
            return
        if self.focused_seg not in chips:
            self.focused_seg = chips[-1]
        else:
            idx = chips.index(self.focused_seg)
            self.focused_seg = chips[(idx - 1) % len(chips)]
        self._render_board()

    def action_back(self) -> None:
        """tab / escape — pop back to _PicksScreen."""
        self.app.pop_screen()  # type: ignore[attr-defined]

    def action_to_summary(self) -> None:
        """enter — push SummaryScreen from the board."""
        self.app.push_screen(SummaryScreen())  # type: ignore[attr-defined]


class _PicksScreen(Screen):  # type: ignore[type-arg]
    """Install-picks surface: the primary wizard screen.

    Contains the Header, SelectionList, and Footer.  Owns all picks-related
    logic (toggle, all, none, refresh).  Pushed as the first screen by
    WizardApp.on_mount.

    enter   → push SummaryScreen.
    tab     → push LayoutBoard.
    a       → enable all picks.
    n       → disable all picks.
    space   → handled natively by SelectionList (via SelectionToggled message).
    """

    BINDINGS: ClassVar[list] = [
        ("a", "all", "All"),
        ("n", "none", "None"),
        ("tab", "layout_board", "Layout Board"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="install-picks"):
            yield SelectionList(id="picks")
        yield Footer()

    def on_mount(self) -> None:
        """Populate the picks list from the injected selection."""
        self._refresh_picks()
        self.query_one("#picks", SelectionList).focus()

    def _refresh_picks(self) -> None:
        """Rebuild the SelectionList from ctx.selection (the authoritative model).

        Preserves the highlighted (cursor) position across refreshes so the
        user's focus stays on the same row after a toggle.
        """
        ctx = self.app.ctx  # type: ignore[attr-defined]
        picks = self.query_one("#picks", SelectionList)
        old_highlighted = picks.highlighted
        picks.clear_options()
        for i, (cat, name, on) in enumerate(ctx.selection.items):  # type: ignore[union-attr]
            picks.add_option((_pick_label(cat, name, bool(on)), i, bool(on)))
        count = picks.option_count
        if count > 0:
            new_pos = min(old_highlighted, count - 1) if old_highlighted is not None else 0
            picks.highlighted = new_pos

    def key_enter(self, event) -> None:  # type: ignore[override]
        """enter on the picks screen → push SummaryScreen.

        Handled as key_enter (not a BINDING) to avoid firing during the
        forwarded-enter event when SummaryScreen or EmptyConfirmModal is on top.
        """
        event.stop()
        self.app.push_screen(SummaryScreen())  # type: ignore[attr-defined]

    def on_selection_list_selection_toggled(
        self, event: SelectionList.SelectionToggled
    ) -> None:
        """space / click — the widget toggled a row; sync ctx.selection then relabel."""
        item_index: int = event.selection.value  # type: ignore[assignment]
        self.app.ctx.selection.toggle(item_index)  # type: ignore[attr-defined, union-attr]
        self._refresh_picks()

    def action_all(self) -> None:
        """a — enable all picks in ctx.selection, then refresh."""
        self.app.ctx.selection.set_all(True)  # type: ignore[attr-defined, union-attr]
        self._refresh_picks()

    def action_none(self) -> None:
        """n — disable all picks in ctx.selection, then refresh."""
        self.app.ctx.selection.set_all(False)  # type: ignore[attr-defined, union-attr]
        self._refresh_picks()

    def action_layout_board(self) -> None:
        """tab — push LayoutBoard on top of picks."""
        self.app.push_screen(LayoutBoard())  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class WizardApp(App):  # type: ignore[type-arg]
    """Screen manager over two surfaces: _PicksScreen (Phase 2) and LayoutBoard
    (Phase 3).  ``q``/``esc`` aborts (returns None) from any screen."""

    BINDINGS: ClassVar[list] = [
        ("q", "abort", "Cancel"),
        ("escape", "abort", "Cancel"),
    ]

    def __init__(self, ctx: WizardContext) -> None:
        super().__init__()
        self.ctx = ctx
        self.state: dict = dict(ctx.state)  # live state; mutated by board ops
        self.result: WizardResult | None = None

    # ------------------------------------------------------------------
    # Compose / Lifecycle
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        """App yields nothing — all content lives on pushed screens."""
        return
        yield  # make this a generator for type-checkers

    def on_mount(self) -> None:
        """Push _PicksScreen as the initial screen."""
        self.push_screen(_PicksScreen())

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_abort(self) -> None:
        """q / esc — leave result as None and exit (fires from any screen)."""
        self.result = None
        self.exit()


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
            RuntimeError(
                f"terminal too small ({cols}×{rows}); "
                f"need at least {_MIN_TERMINAL_COLS}×{_MIN_TERMINAL_ROWS}"
            )
        )
    app = WizardApp(ctx)
    app.run()
    exc = getattr(app, "_exception", None)  # private Textual 8.x attr; getattr degrades safely
    if exc is not None:                     # Textual swallows; re-signal as crash
        raise WizardCrash(exc) from exc
    return app.result
