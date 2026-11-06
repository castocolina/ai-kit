"""Test fixture builder for the install wizard.

Builds a realistic host-keyed ``WizardContext`` from the shipped segment
inventory and a small representative ``Selection``.  It may import
``tools.setup`` to reuse the real ``Selection`` / inventory loaders / host
config — the wizard view itself imports nothing from setup, so exercising it
through a real context (with one or more ``HostView`` entries) is the faithful
test seam.
"""
import types
from typing import cast

from tools import setup
from tools import wizard_app as wa

_HOST_LABELS = {"claude": "Claude Code", "cursor": "Cursor CLI"}
_WIRING = {"claude": "settings.json", "cursor": "cli-config.json"}


def _host_sample(host_id):
    """The host's sample payload JSON for preview; missing file → ``"{}"``."""
    try:
        with open(setup._sample_input_path(host_id), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return "{}"


def make_hosts(host_ids=("claude",), sl_state="unset", with_external=False, engine=None,
               current_command=None, sl_states=None, host_keys=None, alert_limit_text=None):
    """Build HostView entries for the named host ids (detection order kept).

    The harness can't know a real Cursor install's files here, so every entry
    is built the same way _build_wizard_context does per host — from that
    host's ConfigSpec defaults and the shared bundled inventory — but wiring
    stays a fixture-level sl_state reading. The Claude host reads the real
    inventory; the Cursor host additionally gets one stub `cursor_*` segment
    so per-host traversal is exercised in shape. Plan 23-17's two-host PTY
    acceptance scenarios drive the real context end to end.
    """
    hosts = []
    for host_id in host_ids:
        spec = setup.host_config(host_id)
        # Per-host inventory view: the same file, filtered by that host's own
        # `hosts` list — exactly what _host_view does for a real context.
        inv = setup.load_segment_inventory(setup.INVENTORY_PATH, host_id)
        meta = setup.build_segment_meta(inv, {})
        missing = sorted(set(spec.default_segments) - set(meta))
        assert not missing, f"{host_id} segment lacks inventory metadata: {missing}"
        segments = dict(spec.default_segments)
        external: list = []
        if with_external:
            external = [{"id": "system_memory", "filename": "system_memory",
                         "name": "System memory", "path": "/dev/null",
                         "default_on": False, "description": "System available RAM",
                         "icon": "💻", "sample": "12.0 GiB free", "line": 1,
                         "provenance": "bundled"}]
            segments["system_memory"] = False
        label = _HOST_LABELS[host_id]
        # Per-host status-line state: sl_states[host_id] wins over the shared sl_state.
        host_state = (sl_states or {}).get(host_id, sl_state)
        host_engine = engine
        if host_id == "cursor" and alert_limit_text is not None:
            host_engine = types.SimpleNamespace(alert_limit_text=lambda: alert_limit_text)
        hosts.append(wa.HostView(
            id=host_id, label=label,
            config_label=f"~/.config/ai-kit/{spec.config_filename}",
            wiring_label=_WIRING[host_id],
            state={"segments": segments,
                   "layout": [{"min_rows": ln.min_rows, "segments": list(ln.segments)}
                              for ln in spec.default_layout],
                   "dirty": False, "adopt": host_state == "ours",
                   "host_keys": ({t: dict(v) for t, v in host_keys.items()}
                                 if host_id == "cursor" and host_keys else {})},
            status_line=lambda _s=host_state, _c=current_command: {
                "state": _s, "current_command": _c},
            segment_meta=meta, external_segments=external,
            sample_json=_host_sample(host_id) if host_id == "claude" else "{}",
            engine=host_engine,
            done_hint=f"Open a new {label} session to see your status line.",
        ))
    return tuple(hosts)


def make_ctx(with_external=False, sl_state="unset", host_ids=("claude",), engine=None,
             current_command=None, sl_states=None, host_keys=None, alert_limit_text=None):
    """A component-level context plus the named hosts' views."""
    sel = setup.Selection([
        ("agents", "ui-ux-designer", True),
        ("agents", "code-reviewer", False),
        ("commands", "code-review", True),
        ("skills", "brainstorming", True),
    ])
    initial = {(c, n): False for c, n, _ in sel.items}
    return wa.WizardContext(
        selection=cast(wa.SelectionLike, sel),
        state={"_initial_enabled": initial},
        component_meta={name: "" for _, name, _ in sel.items},
        housekeeping={"stale": [], "predecessors": []},
        hosts=make_hosts(host_ids=host_ids, sl_state=sl_state,
                         with_external=with_external, engine=engine,
                         current_command=current_command, sl_states=sl_states,
                         host_keys=host_keys, alert_limit_text=alert_limit_text))


_KIND_ITEMS = [
    ("skills", "brainstorming", True), ("skills", "tdd", True), ("skills", "debugging", True),
    ("agents", "ui-ux-designer", True),
    ("hooks", "tool-advisor", True), ("hooks", "extra-hint", False),
]


def make_ctx_kinds(items=None, host_ids=("claude",), sl_state="ours", engine=None,
                   global_rules=False):
    """A commands-free multi-kind selection for the Choose tabs; ``global_rules`` adds
    Phase 30's global-rules item and its per-file preview (ctx.state)."""
    sel_items = list(_KIND_ITEMS if items is None else items)
    if global_rules:
        sel_items.append(("global rules", "codegraph sentence", True))
    sel = setup.Selection(sel_items)
    state: dict = {"_initial_enabled": {(c, n): False for c, n, _ in sel.items}}
    if global_rules:
        state["_global_rules"] = {"changes": [],
                                  "preview": ["- old sentence", "+ new sentence"]}
    return wa.WizardContext(
        selection=cast(wa.SelectionLike, sel),
        state=state,
        component_meta={name: "" for _, name, _ in sel.items},
        housekeeping={"stale": [], "predecessors": []},
        hosts=make_hosts(host_ids=host_ids, sl_state=sl_state, engine=engine))
