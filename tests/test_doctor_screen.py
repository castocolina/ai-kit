"""Pilot tests for ConfigDoctorScreen: one Screen for the doctor app and a host App (R5, D-13).

Textual needed (run under uv; the module skips without it).
"""

import ast
import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_TOOLS_DIR = os.path.join(_REPO, "tools")

try:
    import textual  # noqa: F401

    _HAVE_TEXTUAL = True
except ImportError:
    _HAVE_TEXTUAL = False


def load_app():
    """Load config_doctor_app.py. Requires textual (run under uv)."""
    if _TOOLS_DIR not in sys.path:
        sys.path.insert(0, _TOOLS_DIR)
    path = os.path.join(_TOOLS_DIR, "config_doctor_app.py")
    spec = importlib.util.spec_from_file_location("config_doctor_app", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["config_doctor_app"] = mod
    spec.loader.exec_module(mod)
    return mod


def _row(row_id, **overrides):
    row = {
        "id": row_id,
        "check": f"check {row_id}",
        "current_display": "5",
        "recommended_display": "3650",
        "confidence": "high",
        "why": "why text",
        "source": "source text",
        "apply_eligible": True,
        "apply_target": 3650,
        "security_relevant": False,
    }
    row.update(overrides)
    return row


def _catalog(*rows):
    return {"sections": [{"runtime": "claude", "config_path": None, "rows": list(rows)}]}


def _table(owner):
    from textual.widgets import DataTable

    return owner.query_one("#catalog-table", DataTable)


def _detail_text(owner):
    from textual.widgets import Static

    return str(owner.query_one("#detail", Static).content)


def _bare_host_app():
    """A host App with no doctor code: it only holds the screen the test pushes."""
    from textual.app import App

    class BareHostApp(App):
        """Stands in for the setup wizard's App."""

    return BareHostApp


@unittest.skipUnless(_HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestDoctorScreen(unittest.IsolatedAsyncioTestCase):
    async def test_doctor_app_uses_screen_as_default_and_a_opens_confirm(self):
        app_mod = load_app()
        calls = []

        def apply(row_id, dry):
            calls.append((row_id, dry))
            return {"ok": True, "after": 3650, "current_display": "3650"}

        ctx = app_mod.ConfigDoctorContext(
            catalog=_catalog(_row("claude-retention"), _row("claude-other")), apply=apply
        )
        app = app_mod.ConfigDoctorApp(ctx)
        async with app.run_test() as pilot:
            self.assertIsInstance(app.screen, app_mod.ConfigDoctorScreen)
            self.assertEqual(len(app.screen_stack), 1)
            self.assertEqual(_table(app).row_count, 2)
            await pilot.press("a")
            self.assertIsInstance(app.screen, app_mod.ConfirmApplyScreen)
            await pilot.press("y")
            table = _table(app)
            cell = table.get_cell("claude-retention", table.ordered_columns[2].key)
            self.assertEqual(str(cell), "3650")
        self.assertEqual(calls, [("claude-retention", False)])

    async def test_doctor_app_escape_exits_and_q_quits(self):
        app_mod = load_app()
        ctx = app_mod.ConfigDoctorContext(catalog=_catalog(_row("claude-retention")))
        app = app_mod.ConfigDoctorApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("escape")
            await pilot.pause()
            self.assertEqual(app.return_code, 0)
        app = app_mod.ConfigDoctorApp(ctx)
        async with app.run_test() as pilot:
            await pilot.press("q")
            await pilot.pause()
            self.assertEqual(app.return_code, 0)

    async def test_bare_host_pushes_screen_with_rows_and_escape_pops(self):
        app_mod = load_app()
        ctx = app_mod.ConfigDoctorContext(
            catalog=_catalog(_row("claude-retention"), _row("claude-other"))
        )
        host = _bare_host_app()()
        async with host.run_test() as pilot:
            host.push_screen(
                app_mod.ConfigDoctorScreen(ctx, exit_hint="Esc returns to Done.")
            )
            await pilot.pause()
            self.assertIsInstance(host.screen, app_mod.ConfigDoctorScreen)
            self.assertEqual(_table(host.screen).row_count, 2)
            await pilot.press("escape")
            await pilot.pause()
            self.assertNotIsInstance(host.screen, app_mod.ConfigDoctorScreen)
            self.assertEqual(len(host.screen_stack), 1)
            host.push_screen(app_mod.ConfigDoctorScreen(ctx, exit_hint="Esc returns to Done."))
            await pilot.pause()
            self.assertEqual(_table(host.screen).row_count, 2)

    async def test_bare_host_gets_detail_border_from_screen_css(self):
        app_mod = load_app()
        ctx = app_mod.ConfigDoctorContext(catalog=_catalog(_row("claude-retention")))
        host = _bare_host_app()()
        async with host.run_test() as pilot:
            host.push_screen(app_mod.ConfigDoctorScreen(ctx))
            await pilot.pause()
            detail = host.screen.query_one("#detail")
            self.assertEqual(detail.styles.border_top[0], "solid")

    def test_screen_bindings_are_apply_row_and_close_only(self):
        app_mod = load_app()
        actions = [binding[1] for binding in app_mod.ConfigDoctorScreen.BINDINGS]
        self.assertEqual(actions, ["apply_row", "close"])


@unittest.skipUnless(_HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestEmptyCatalog(unittest.IsolatedAsyncioTestCase):
    async def test_bare_host_shows_no_rows_line_with_exit_hint_and_escape_pops(self):
        app_mod = load_app()
        ctx = app_mod.ConfigDoctorContext(catalog={"sections": []})
        host = _bare_host_app()()
        async with host.run_test() as pilot:
            host.push_screen(app_mod.ConfigDoctorScreen(ctx, exit_hint="Esc returns to Done."))
            await pilot.pause()
            detail = _detail_text(host.screen)
            self.assertEqual(detail, f"{app_mod.EMPTY_CATALOG_TEXT} Esc returns to Done.")
            await pilot.press("escape")
            await pilot.pause()
            self.assertEqual(len(host.screen_stack), 1)

    async def test_doctor_app_empty_line_ends_with_q_quits(self):
        app_mod = load_app()
        ctx = app_mod.ConfigDoctorContext(catalog={"sections": []})
        app = app_mod.ConfigDoctorApp(ctx)
        async with app.run_test():
            detail = _detail_text(app.screen)
            self.assertEqual(detail, f"{app_mod.EMPTY_CATALOG_TEXT} q quits.")


def _is_catalog_table(call):
    func = call.func
    name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
    if name != "DataTable":
        return False
    return any(
        keyword.arg == "id"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value == "catalog-table"
        for keyword in call.keywords
    )


def doctor_table_classes(src):
    """Names of the classes in one module whose body builds DataTable(id="catalog-table")."""
    names = []
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.ClassDef):
            continue
        calls = (call for call in ast.walk(node) if isinstance(call, ast.Call))
        if any(_is_catalog_table(call) for call in calls):
            names.append(node.name)
    return names


class TestOneDoctorTable(unittest.TestCase):
    def test_only_the_doctor_screen_builds_the_catalog_table(self):
        owners = []
        for name in sorted(os.listdir(_TOOLS_DIR)):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(_TOOLS_DIR, name), encoding="utf-8") as handle:
                owners.extend(doctor_table_classes(handle.read()))
        self.assertEqual(owners, ["ConfigDoctorScreen"])

    def test_non_vacuity_two_table_owners_are_both_named(self):
        src = (
            "class A:\n"
            "    def f(self):\n"
            '        return DataTable(id="catalog-table")\n'
            "\n"
            "class B:\n"
            "    def g(self):\n"
            '        return DataTable(id="catalog-table")\n'
            "\n"
            "class C:\n"
            "    def h(self):\n"
            '        return DataTable(id="other")\n'
        )
        self.assertEqual(doctor_table_classes(src), ["A", "B"])


if __name__ == "__main__":
    unittest.main()
