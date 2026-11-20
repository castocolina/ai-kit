"""35 D-11, D-20, Amend-11 / R3(c): read a host's interactive model view through herdr
when present. The copilot view is unverified until the spike runs; names are labeled
'interactive view, unverified'. Pane text is data."""

import json
import re
import shutil
import subprocess
import time

from ai_kit_spec.optional_sources import sanitize_name

# Step names and waits are unverified until the copilot /model spike runs (Amend-11).
COPILOT_ARGV = ("copilot", "--allow-all", "--no-auto-update")
READY_REGEX = "(?i)copilot"
LIST_REGEX = "(?i)model"
WAIT_MS = "30000"
READ_LINES = "120"
LABEL = "interactive view, unverified"
_MODELISH_RX = re.compile(r"[0-9/.:-]")
_BOUNDARY = "/model"
_LEAD_RX = re.compile(r"^[\s>*\-•❯›●○◉0-9.)]+")


def herdr_available(env, which_fn=shutil.which) -> tuple:
    """Return the herdr binary only when explicitly enabled and on PATH."""
    if env.get("HERDR_ENV") != "1":
        return None, "herdr absent: HERDR_ENV is not 1"
    binary = which_fn("herdr", path=env.get("PATH"))
    if binary is None:
        return None, "herdr absent: no herdr CLI on PATH"
    return binary, ""


def parse_pane_names(text: str) -> list | None:
    """Extract model-shaped first tokens only after an exact /model command echo."""
    lines = text.splitlines()
    boundary = next((index for index, line in enumerate(lines)
                     if _LEAD_RX.sub("", line).strip() == _BOUNDARY), None)
    if boundary is None:
        return None
    names = []
    seen = set()
    for line in lines[boundary + 1:]:
        tokens = _LEAD_RX.sub("", line).strip().split(maxsplit=1)
        if not tokens or tokens[0].endswith(":"):
            continue
        name = sanitize_name(tokens[0])
        if name is not None and len(name) >= 3 and _MODELISH_RX.search(name) and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _herdr(binary, args, env, run_fn):
    try:
        return run_fn(
            [binary, *args], capture_output=True, text=True, env=env, timeout=60, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _step(binary, args, env, run_fn):
    result = _herdr(binary, ["pane", *args], env, run_fn)
    return result if result is not None and result.returncode == 0 else None


def _read_pane(binary, pane_id, env, run_fn):
    steps = (
        ("run", ["run", pane_id, " ".join(COPILOT_ARGV)]),
        ("wait-output", ["wait-output", pane_id, "--regex", READY_REGEX, "--timeout", WAIT_MS]),
        ("send-text", ["send-text", pane_id, "/model"]),
        ("send-keys", ["send-keys", pane_id, "enter"]),
        ("wait-output", ["wait-output", pane_id, "--regex", LIST_REGEX, "--timeout", WAIT_MS]),
        ("read", ["read", pane_id, "--source", "recent-unwrapped", "--lines", READ_LINES]),
    )
    for step_name, args in steps:
        result = _step(binary, args, env, run_fn)
        if result is None:
            return [], f"pane failed: {step_name}"
        if step_name == "read":
            names = parse_pane_names(result.stdout)
            if names is None:
                return [], "no list boundary"
            if not names:
                return [], "no names read"
            escaped = _step(binary, ["send-keys", pane_id, "esc"], env, run_fn)
            if escaped is None:
                return [], "pane failed: send-keys"
            date = time.strftime("%Y-%m-%d")
            records = [
                {"name": name, "source": "interactive view", "label": LABEL, "date": date}
                for name in names
            ]
            return records, "ok"
    return [], "no names read"


def read_interactive_names(
    runtime: str, env, run_fn=subprocess.run, which_fn=shutil.which, cwd="."
) -> tuple:
    """Read and label interactive model names, reporting every pane failure."""
    if runtime != "copilot":
        return [], f"no interactive view known for {runtime}"
    binary, reason = herdr_available(env, which_fn)
    if binary is None:
        return [], reason
    split = _herdr(
        binary, ["pane", "split", "--current", "--direction", "right", "--cwd", cwd,
                 "--no-focus"], env, run_fn
    )
    if split is None or split.returncode != 0:
        return [], "pane failed: split"
    try:
        pane_id = json.loads(split.stdout)["result"]["pane"]["pane_id"]
    except (ValueError, TypeError, KeyError):
        pane_id = None
    if not isinstance(pane_id, str) or not pane_id:
        return [], (
            "pane failed: split (pane id unknown; no command was started; "
            "check herdr for an empty pane)"
        )
    records, status = [], "pane failed: read"
    try:
        records, status = _read_pane(binary, pane_id, env, run_fn)
    finally:
        closed = _herdr(binary, ["pane", "close", pane_id], env, run_fn)
        if closed is None or closed.returncode != 0:
            status += f"; pane close failed: {pane_id}"
            records = []
    return records, status
