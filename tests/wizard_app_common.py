"""Shared guard and helper for the tests/test_wizard_app_*.py modules (tools/wizard_app.py).

The Textual runtime requires ``uv run``; plain ``python3`` will not have it, so every test
class in those modules is guarded by ``@skipUnless(HAVE_TEXTUAL, ...)``.
"""
import importlib.util

HAVE_TEXTUAL = importlib.util.find_spec("textual") is not None


def query_static(app, selector: str):
    """The Static at ``selector``; its text is ``str(widget.content)`` (Textual 8.2.7)."""
    from textual.widgets import Static

    return app.query_one(selector, Static)
