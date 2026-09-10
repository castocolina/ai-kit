"""Textual review screen for Config Doctor.

Own separate module (D-06). Imports nothing from setup.py, wizard_app.py, or
config_doctor_checks.py — driven entirely through ConfigDoctorContext.
"""

from __future__ import annotations

import json
from typing import ClassVar, NamedTuple

from rich.markup import escape
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import DataTable, Static

# Palette lifted verbatim from tools/wizard_app.py:27-36
FG = "#c9d1d9"
DIM = "#6e7681"
LINE = "#30363d"
ACCENT = "#58a6ff"
GREEN = "#3fb950"
WARN = "#d29922"
PINK = "#db61a2"
CYAN = "#39c5cf"
KEYCAP = "#21262d"


class ConfigDoctorContext(NamedTuple):
    """Injected by setup.py. apply is a (row_id, dry) -> result closure.

    catalog/apply are typed ``object`` so this module stays free of any import
    from config_doctor_checks.py (mirrors WizardContext.commit: object = None).
    """

    catalog: object
    apply: object = None


class ConfirmApplyScreen(ModalScreen):
    """Per-item confirm: names the exact current -> target change.

    Preview of the write is fetched exclusively through ``ctx.apply(row_id,
    dry=True)`` — this module never imports config_doctor_checks. Confirm
    calls ``ctx.apply(row_id, dry=False)`` exactly once. A refused result
    stays on this screen until acknowledged; cancel never calls apply.
    """

    BINDINGS: ClassVar[list] = [
        ("y", "confirm", "Confirm"),
        ("enter", "confirm", "Confirm"),
        ("n", "cancel", "Cancel"),
        ("escape", "cancel", "Cancel"),
    ]
    CSS = f"""
    ConfirmApplyScreen {{
        align: center middle;
    }}
    #confirm-box {{
        width: 80;
        max-height: 80%;
        background: #161b22;
        border: solid {ACCENT};
        padding: 1 2;
    }}
    #confirm-title {{ color: {ACCENT}; text-style: bold; }}
    #confirm-body {{ color: {FG}; height: auto; }}
    #confirm-hint {{ color: {DIM}; }}
    """

    def __init__(self, row, ctx) -> None:
        super().__init__()
        self.row = row
        self.ctx = ctx
        self._awaiting_ack = False

    def compose(self) -> ComposeResult:
        check = escape(str(self.row.get("check", "")))
        current = escape(str(self.row.get("current_display", "")))
        target = escape(str(self.row.get("apply_target", "")))
        body = f"{check}\n  {current} -> {target}"
        if self.row.get("security_relevant") and callable(self.ctx.apply):
            preview = self.ctx.apply(self.row["id"], True)
            if isinstance(preview, dict):
                literal = preview.get("literal_resulting_config")
                if literal is not None:
                    if not isinstance(literal, str):
                        literal = json.dumps(literal, indent=2)
                    body = f"{body}\n\n{escape(str(literal))}"
        with VerticalScroll(id="confirm-box"):
            yield Static("Confirm apply", id="confirm-title")
            yield Static(body, id="confirm-body")
            yield Static(
                f"[{KEYCAP}] y / Enter [/] confirm   "
                f"[{KEYCAP}] n / Esc [/] cancel",
                id="confirm-hint",
            )

    def action_confirm(self) -> None:
        if self._awaiting_ack:
            self.dismiss({"ok": False})
            return
        if not callable(self.ctx.apply):
            self.dismiss({"ok": False, "reason": "apply not wired"})
            return
        result = self.ctx.apply(self.row["id"], False)
        if not isinstance(result, dict):
            result = {"ok": False, "reason": "apply returned a non-dict result"}
        if result.get("ok"):
            self.dismiss(result)
            return
        reason = escape(str(result.get("reason", "apply refused")))
        self._awaiting_ack = True
        self.query_one("#confirm-body", Static).update(reason)
        self.query_one("#confirm-hint", Static).update(
            f"[{WARN}]refused[/]  [{KEYCAP}] any key / Esc [/] acknowledge"
        )

    def action_cancel(self) -> None:
        if self._awaiting_ack:
            self.dismiss({"ok": False})
            return
        self.dismiss(None)

    def on_key(self, event) -> None:
        if self._awaiting_ack:
            event.stop()
            self.dismiss({"ok": False})


class ConfigDoctorApp(App):
    ENABLE_COMMAND_PALETTE = False
    BINDINGS: ClassVar[list] = [
        ("q", "quit", "Quit"),
        ("a", "apply_row", "Apply"),
    ]
    CSS = f"""
    Screen {{ background: #0d1117; }}
    #header {{ height: 1; color: {ACCENT}; text-style: bold; padding: 0 1; }}
    #catalog-table {{ height: 1fr; }}
    #detail {{ height: auto; color: {DIM}; padding: 1 1; border-top: solid {LINE}; }}
    """

    def __init__(self, ctx: ConfigDoctorContext) -> None:
        super().__init__()
        self.ctx = ctx
        self._rows_by_id: dict = {}

    def compose(self) -> ComposeResult:
        yield Static("- ai-kit config doctor", id="header")
        yield DataTable(id="catalog-table")
        yield Static(id="detail")

    def on_mount(self) -> None:
        table = self.query_one("#catalog-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Runtime", "Check", "Current", "Recommended", "Confidence")
        catalog = self.ctx.catalog if isinstance(self.ctx.catalog, dict) else {}
        sections = catalog.get("sections") or []
        if not sections:
            table.display = False
            self.query_one("#detail", Static).update(
                "No supported AI-CLI config file was found on this machine."
            )
            return
        first_id = None
        for section in sections:
            runtime = str(section.get("runtime", ""))
            for row in section.get("rows") or []:
                row_id = row["id"]
                if first_id is None:
                    first_id = row_id
                self._rows_by_id[row_id] = row
                table.add_row(
                    escape(runtime),
                    escape(str(row.get("check", ""))),
                    escape(str(row.get("current_display", ""))),
                    escape(str(row.get("recommended_display", ""))),
                    escape(str(row.get("confidence", ""))),
                    key=row_id,
                )
        if first_id is not None:
            self._show_detail(first_id)

    def _show_detail(self, row_id) -> None:
        row = self._rows_by_id.get(row_id)
        if row is None:
            return
        why = escape(str(row.get("why", "")))
        source = escape(str(row.get("source", "")))
        self.query_one("#detail", Static).update(f"{why}\n\n{source}")

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        key = event.row_key
        row_id = getattr(key, "value", key)
        if row_id:
            self._show_detail(row_id)

    def _highlighted_row(self):
        table = self.query_one("#catalog-table", DataTable)
        if not table.row_count:
            return None
        cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
        row_id = getattr(cell_key.row_key, "value", cell_key.row_key)
        return self._rows_by_id.get(row_id)

    def action_apply_row(self) -> None:
        # Silent no-op on a non-apply-eligible row is the CORRECT behavior
        # (there is nothing to apply), unlike every other "no-op on invalid
        # input" case this project treats as a bug elsewhere.
        row = self._highlighted_row()
        if row is None:
            return
        if self.ctx.apply is None or not row.get("apply_eligible"):
            return
        self.push_screen(
            ConfirmApplyScreen(row=row, ctx=self.ctx),
            self._on_apply_dismissed,
        )

    def _on_apply_dismissed(self, result) -> None:
        if not isinstance(result, dict) or not result.get("ok"):
            return
        row_id = None
        row = None
        highlighted = self._highlighted_row()
        if highlighted is not None:
            row_id = highlighted.get("id")
            row = highlighted
        if row_id is None:
            return
        display = result.get("current_display")
        if display is None:
            display = result.get("after")
        if display is None:
            return
        display_s = escape(str(display))
        table = self.query_one("#catalog-table", DataTable)
        current_col = table.ordered_columns[2].key
        table.update_cell(row_id, current_col, display_s)
        if row is not None:
            row["current_display"] = str(display)
            self._show_detail(row_id)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_config_doctor(ctx: ConfigDoctorContext) -> None:
    """Run the Config Doctor TUI."""
    ConfigDoctorApp(ctx).run()
