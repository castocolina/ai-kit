"""Detect curated modern-tool availability and compose a session briefing.

Detection crosses ai-kit's curated legacy/modern pairs with live binary
presence from ``shutil.which``. Claude Code and Cursor have session-start
injection points; opencode has no documented equivalent today, an accepted
and documented gap.
"""

import os
import shutil

CURATED_SUBSTITUTIONS = (
    ("cat", "bat"),
    ("grep", "rg"),
    ("find", "fd"),
    ("sed", "sd"),
    ("ls", "eza"),
)


def detect_substitutions(search_path=None):
    """Return installed modern tools in curated pair order without spawning processes."""
    pairs = [
        {
            "legacy": legacy,
            "modern": modern,
            "installed": shutil.which(modern, path=search_path) is not None,
        }
        for legacy, modern in CURATED_SUBSTITUTIONS
    ]
    return {"pairs": pairs}


# Flags live-verified 2026-10-18: bat 0.26.1, rg 15.2.0, fd 10.5.0,
# sd 1.0.0. eza keeps the 2026-09-09 verification line.
TOOL_GUIDANCE = {
    "bat": "bat --plain --paging=never; use -l <lang> and -r N:M for a slice",
    "rg": "rg -n for line numbers, rg -l for file names, and --glob to filter",
    "fd": "fd --type f --glob to find files by pattern",
    "sd": "sd -p to preview before writing",
    "eza": "--long --git",
}


def compose_message(detection):
    """Return a printable user line and concise model context, or two empty strings."""
    try:
        if not isinstance(detection, dict):
            return "", ""
        pairs = detection.get("pairs")
        if not isinstance(pairs, list):
            pairs = []
        present = [
            pair for pair in pairs
            if isinstance(pair, dict)
            and pair.get("installed") is True
            and isinstance(pair.get("modern"), str)
            and isinstance(pair.get("legacy"), str)
            and pair["modern"] in TOOL_GUIDANCE
        ]
        if not present:
            return "", ""
        user_line = "ai-kit: prefer these modern tools: " + ", ".join(
            f"{pair['modern']} over {pair['legacy']}" for pair in present
        ) + "."
        readme = os.path.join(os.path.dirname(os.path.realpath(__file__)), "README.md")
        home = os.path.realpath(os.path.expanduser("~"))  # readme is a realpath too
        if home != os.path.abspath(os.sep) and (readme == home or readme.startswith(home + os.sep)):
            readme = "~" + readme[len(home):]
        usage_suffix = f" Usage: {readme}"
        if (len(user_line + usage_suffix) <= 200
                and all(character.isascii() and character.isprintable()
                        for character in usage_suffix)):
            user_line += usage_suffix
        context_lines = [
            "Prefer these installed modern tools over their legacy counterparts "
            "(faster, quieter output):"
        ]
        context_lines.extend(
            f"- {pair['modern']} (instead of {pair['legacy']}): "
            f"{TOOL_GUIDANCE[pair['modern']]}"
            for pair in present
        )
        model_context = "\n".join(context_lines)
        if len(user_line) > 200 or len(model_context) > 2000:
            return "", ""
        if any(not character.isascii() or not character.isprintable() for character in user_line):
            return "", ""
        return user_line, model_context
    except (TypeError, AttributeError, ValueError):
        return "", ""
