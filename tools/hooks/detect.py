"""Live-detect curated rtk tool substitutions and compose a briefing.

This module is the host-agnostic detection and message-composition core for
the tool-substitution awareness hook. It reports which of ai-kit's curated
(legacy, modern) pairs have their modern binary on PATH, and whether rtk's
own hook is genuinely active — never reciting catalog intent as verified.

The `rtk init --show` signal is reverse-engineered from human-readable CLI
output (rtk offers no machine-readable mode). A parse miss therefore
degrades toward not-active rather than raising, and any claim derived from
that parse is confidence-labelled as inferred from third-party diagnostic
text, not as an official contract.

Host coverage: Claude Code and Cursor both have a session-start injection
point and both are wired. opencode has no documented equivalent injection
point today, which is an accepted, documented gap (ROADMAP SC-4,
PROJECT.md Out of Scope).
"""

import shutil
import subprocess

CURATED_SUBSTITUTIONS = (
    ("cat", "bat"),
    ("grep", "rg"),
    ("find", "fd"),
    ("sed", "sd"),
    ("ls", "eza"),
)

RTK_PROBE_TIMEOUT_SECONDS = 2.0

RTK_SIGNAL_ABSENT = "rtk-absent"
RTK_SIGNAL_CONFIRMED = "confirmed"
RTK_SIGNAL_NOT_REGISTERED = "not-registered"
RTK_SIGNAL_UNREADABLE = "unreadable"


def detect_substitutions(search_path=None, runner=None):
    """Return the live substitution picture for `search_path` (or PATH).

    Keys: rtk_present (bool), rtk_hook_active (bool), rtk_hook_signal (str),
    pairs (list of {legacy, modern, installed} in CURATED_SUBSTITUTIONS order).
    """
    if runner is None:
        runner = subprocess.run
    rtk_path = shutil.which("rtk", path=search_path)
    rtk_present = rtk_path is not None
    signal = (
        RTK_SIGNAL_ABSENT if rtk_path is None
        else _probe_rtk_hook(rtk_path, runner)
    )
    pairs = [
        {
            "legacy": legacy,
            "modern": modern,
            "installed": shutil.which(modern, path=search_path) is not None,
        }
        for legacy, modern in CURATED_SUBSTITUTIONS
    ]
    return {
        "rtk_present": rtk_present,
        "rtk_hook_active": signal == RTK_SIGNAL_CONFIRMED,
        "rtk_hook_signal": signal,
        "pairs": pairs,
    }


# Confidence label: this signal is reverse-engineered from a third-party CLI's
# human-readable diagnostic output. The installed rtk offers no machine-readable
# mode, and a future rtk release can silently reword it — which is exactly why
# a parse miss degrades to RTK_SIGNAL_UNREADABLE rather than raising.
def _probe_rtk_hook(rtk_path, runner):
    """Classify rtk's hook from `rtk init --show` stdout. Never raises."""
    try:
        proc = runner(
            [rtk_path, "init", "--show"],
            capture_output=True,
            text=True,
            timeout=RTK_PROBE_TIMEOUT_SECONDS,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except Exception:
        return RTK_SIGNAL_UNREADABLE
    stdout = proc.stdout or ""
    for line in stdout.splitlines():
        if "Hook:" not in line or "rtk hook" not in line:
            continue
        stripped = line.lstrip()
        if stripped.startswith("[ok]"):
            return RTK_SIGNAL_CONFIRMED
        if stripped.startswith("[--]"):
            return RTK_SIGNAL_NOT_REGISTERED
        return RTK_SIGNAL_UNREADABLE
    return RTK_SIGNAL_UNREADABLE


# Flags live-verified against the binaries on this machine (2026-09-09):
#   bat 0.26.1 (979ba22) — --plain, --line-range
#   rg 15.2.0 (rev e89fff89ac) — --files-with-matches, --hidden, --glob
#   fd 10.4.2 — --hidden, --type, --glob
#   sd 1.0.0 — --preview, --fixed-strings
#   eza v0.23.5 [+git] — --long, --git, --icons
TOOL_GUIDANCE = {
    "bat": "use --plain to skip highlighting, --line-range N:M for a slice",
    "rg": "use --files-with-matches, --hidden, --glob rather than grep -r",
    "fd": "use --hidden --type f and --glob rather than find -name",
    "sd": "use --preview before a write, --fixed-strings for literal replace",
    "eza": "use --long --git; --icons never when piping",
}


def compose_message(detection):
    """Two-part briefing from a detection dict. Never interpolates probe stdout.

    Part A (rewrite notice) only when rtk_hook_active is true. All three
    non-confirmed signals share the no-rewrite-confirmed line when at least
    one modern binary is present. Returns "" when nothing is honestly worth
    saying, including on a malformed detection dict.
    """
    try:
        if not isinstance(detection, dict):
            return ""
        pairs = detection.get("pairs")
        if not isinstance(pairs, list):
            pairs = []
        present = [
            p for p in pairs
            if isinstance(p, dict) and p.get("installed")
        ]
        lines = []
        if detection.get("rtk_hook_active"):
            lines.append(
                "rtk rewrites some Bash tool calls before they run, so the "
                "command that executes is not always the one written."
            )
        elif present:
            lines.append(
                "No rtk rewrite is confirmed active, so invoke the tools "
                "below directly."
            )
        for pair in present:
            modern = pair.get("modern", "")
            legacy = pair.get("legacy", "")
            hint = TOOL_GUIDANCE.get(modern, "")
            if hint:
                lines.append(f"- {modern} ({legacy}-class): {hint}")
            else:
                lines.append(f"- {modern} ({legacy}-class)")
        return "\n".join(lines)
    except Exception:
        return ""
