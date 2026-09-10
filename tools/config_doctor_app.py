"""Textual review screen for Config Doctor.

Own separate module (D-06). Imports nothing from setup.py, wizard_app.py, or
config_doctor_checks.py — driven entirely through ConfigDoctorContext.
"""

from __future__ import annotations

from typing import ClassVar, NamedTuple

from rich.markup import escape
from textual.app import App, ComposeResult
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
    """Injected by setup.py. apply stays None until Wave 3.

    catalog/apply are typed ``object`` so this module stays free of any import
    from config_doctor_checks.py (mirrors WizardContext.commit: object = None).
    """

    catalog: object
    apply: object = None


class ConfigDoctorApp(App):
    ENABLE_COMMAND_PALETTE = False
    BINDINGS: ClassVar[list] = [("q", "quit", "Quit")]
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


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_config_doctor(ctx: ConfigDoctorContext) -> None:
    """Run the Config Doctor TUI (read-only in this phase)."""
    ConfigDoctorApp(ctx).run()
