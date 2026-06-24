"""Shared fake data + helpers for the three install-wizard prototypes.

Pure stdlib; imported by proto_stdio.py / proto_questionary.py / proto_textual.py
(Python puts the script's own directory on sys.path, so a sibling import works
under `python3 …` and `uv run --script …` alike).

These prototypes are for COMPARING the three frameworks' UX. They use fake,
in-memory data and write nothing to disk — the final step just prints what the
real wizard WOULD do.
"""

# category -> example installable items (name, default_selected)
CATEGORIES = {
    "agents": [
        ("ui-ux-designer", True),
        ("mermaid-diagram-specialist", True),
        ("code-reviewer", False),
    ],
    "commands": [
        ("code-review", True),
        ("gsd-plan-phase", True),
        ("brainstorm", False),
    ],
    "skills": [
        ("brainstorming", True),
        ("writing-plans", True),
        ("markdown-to-pdf", True),
        ("subagent-driven-development", False),
    ],
}

# segment -> (icon, default_on, sample rendered value)
SEGMENTS = [
    ("path", "📂", True, "~/project"),
    ("git_branch", "🌿", True, "main"),
    ("alt_git_worktree", "🌲", True, "wt:feat"),
    ("git_dirty", "±", True, "±3"),
    ("todo", "✅", True, "3 todo"),
    ("model", "🤖", True, "Opus 4.8"),
    ("alt_time_ago", "🕐", True, "2m ago"),
    ("alt_time_clock", "⏰", True, "20:35"),
    ("effort", "🔋", True, "high"),
    ("lines", "📃", True, "+128/-42"),
    ("alt_cost", "💰", False, "$0.12"),
    ("alt_time_session", "⏳", True, "12m"),
    ("alt_time_api", "📡", True, "98ms"),
    ("render_time", "⏱️", True, "2.1ms"),
    ("slowest", "🐌", True, "sysmem 85µs"),
    ("alt_term_dimensions", "📐", False, "96x34"),
    ("context", "📊", True, "10% of 200K"),
    ("chat_size", "💬", True, "0.7s"),
    ("alt_process_memory", "🧮", True, "682MB"),
    ("alt_rate_limits", "🚦", True, "ok"),
]

# default layout: 3 lines (the 2nd/3rd are row-gated in the real renderer).
LAYOUT = [
    ["path", "git_branch", "alt_git_worktree", "git_dirty", "todo"],
    ["model", "alt_time_ago", "alt_time_clock", "effort", "lines",
     "alt_cost", "alt_time_session", "alt_time_api"],
    ["render_time", "slowest", "alt_term_dimensions", "context",
     "chat_size", "alt_process_memory", "alt_rate_limits"],
]

ICON = {name: icon for name, icon, _on, _v in SEGMENTS}
SAMPLE = {name: v for name, _i, _on, v in SEGMENTS}
DEFAULT_ON = {name: on for name, _i, on, _v in SEGMENTS}
ALL_SEGMENTS = [name for name, _i, _on, _v in SEGMENTS]


def default_state():
    """A fresh editable state: {'on': {seg: bool}, 'layout': [[seg,...], ...]}."""
    return {
        "on": dict(DEFAULT_ON),
        "layout": [list(line) for line in LAYOUT],
    }


def preview_lines(state):
    """Render a fake status line from the state. Mirrors the real 3-line shape:
    each layout line shows `icon value` for its ON segments, joined by ' | '."""
    out = []
    for line in state["layout"]:
        parts = [f"{ICON.get(s, '?')} {SAMPLE.get(s, s)}"
                 for s in line if state["on"].get(s)]
        if parts:
            out.append(" | ".join(parts))
    return out or ["(all segments off)"]


def selected_summary(picks):
    """picks: {category: {item: bool}} -> list of 'category: a, b, c' strings."""
    lines = []
    for cat, items in picks.items():
        chosen = [name for name, on in items.items() if on]
        lines.append(f"{cat}: " + (", ".join(chosen) if chosen else "(none)"))
    return lines


def default_picks():
    """{category: {item: bool}} seeded from CATEGORIES defaults."""
    return {cat: {name: on for name, on in items}
            for cat, items in CATEGORIES.items()}
