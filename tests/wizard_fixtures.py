"""Test fixture builder for the install wizard.

Builds a realistic ``WizardContext`` from the shipped segment inventory and a
small representative ``Selection``.  It may import ``tools.setup`` to reuse the
real ``Selection`` / inventory loaders / defaults — the wizard view itself
imports nothing from setup, so exercising it through a real context is the
faithful test seam.
"""
from tools import setup
from tools import wizard_app as wa


def make_ctx(with_external=False, sl_state="unset"):
    inv = setup.load_segment_inventory(setup.INVENTORY_PATH)
    meta = setup.build_segment_meta(inv, {})
    sel = setup.Selection([
        ("agents", "ui-ux-designer", True),
        ("agents", "code-reviewer", False),
        ("commands", "code-review", True),
        ("skills", "brainstorming", True),
    ])
    segments = dict(setup.SEGMENT_DEFAULTS)
    external = []
    if with_external:
        external = [{"id": "system_memory", "filename": "system_memory",
                     "name": "System memory", "path": "/dev/null",
                     "default_on": False, "description": "System available RAM",
                     "icon": "💻", "sample": "12.0 GiB free", "line": 1,
                     "provenance": "bundled"}]
        segments["system_memory"] = False
    layout = [{"min_rows": r["min_rows"], "segments": list(r["segments"])}
              for r in setup.LAYOUT_DEFAULTS]
    initial = {(c, n): False for c, n, _ in sel.items}
    return wa.WizardContext(
        selection=sel,
        state={"segments": segments, "layout": layout, "dirty": False,
               "adopt": sl_state == "ours", "_initial_enabled": initial},
        sample_json="{}", engine=None,
        status_line=lambda: {"state": sl_state, "current_command": None},
        segment_meta=meta, external_segments=external,
        component_meta={name: "" for _, name, _ in sel.items},
        housekeeping={"stale": [], "predecessors": []})
