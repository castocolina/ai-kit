"""Lane capability facts read from the runner's --print-argv lines,

and the block built from them (SPEC R3, R4; D-02 to D-04).
"""

import json
import re
from typing import NamedTuple

from ai_kit_spec.runner_dispatch import SETTING_LINE_RE

CAPABILITIES_PREFIX = "cross-ai: capabilities "
SKILL_BLOCK_RE = re.compile(
    r"^cross-ai: skill-block (?P<name>\S+) bytes=(?P<bytes>\d+) sha256=(?P<sha256>[0-9a-f]{64})$"
)
# 39-02's closed values per field (SPEC R3 and its 2026-11-23 amendment).
CAPABILITY_VALUES = {
    "write": ("none", "workspace", "full", "unknown"),
    "shell": ("yes", "no", "unknown"),
    "skills": ("none", "path", "discovery", "unknown"),
    "mcp": ("none", "host_config", "call_file", "unknown"),
}
PROMPT_CHANNELS = ("argv", "stdin")
APPLIED_SETTINGS = ("model", "effort", "context")
NO_PREVIEW_REASON = (
    "the runner preview did not run (node or the runner template is missing, "
    "or the runner exited non-zero)"
)
NO_LINE_REASON = "the runner printed no capabilities line (an older runner copy)"
BAD_LINE_REASON = "the runner's capabilities line could not be parsed"
LABEL_STATES = ("verified", "unverified", "unknown")
SKILL_FORMS = ("name", "path", "prose")


class LaneFacts(NamedTuple):
    """One lane's facts from one --print-argv run.

    Each capability is {"value", "label": {"state", "source"}} (39-02's shape);
    prompt is {"channel", "max_bytes"}; reason is None unless every capability is unknown.
    """

    write: dict
    shell: dict
    skills: dict
    mcp: dict
    prompt: dict
    skill_settings: tuple = ()
    mcp_settings: tuple = ()
    skill_blocks: tuple = ()
    settings: tuple = ()
    context_setting: dict | None = None
    reason: str | None = None


def context_form_applied(facts: LaneFacts) -> bool:
    """True when the final argv carries a context form (39-06's window_for argument).

    The context setting is applied, or ignored because the model id already carries it
    (reason id_carries).
    """
    return facts.context_setting is not None and (
        facts.context_setting["state"] == "applied"
        or facts.context_setting["reason"] == "id_carries"
    )


def unknown_facts(reason: str) -> LaneFacts:
    """Return independent unknown capability records with their reason."""
    w = {"value": "unknown", "label": {"state": "unknown", "source": reason}}
    s = {"value": "unknown", "label": {"state": "unknown", "source": reason}}
    k = {"value": "unknown", "label": {"state": "unknown", "source": reason}}
    m = {"value": "unknown", "label": {"state": "unknown", "source": reason}}
    return LaneFacts(w, s, k, m, {"channel": "unknown", "max_bytes": None}, reason=reason)


def _label_ok(label) -> bool:
    return (isinstance(label, dict) and label.get("state") in LABEL_STATES
            and isinstance(label.get("source"), str) and bool(label["source"]))


def _prompt_ok(prompt) -> bool:
    if not isinstance(prompt, dict):
        return False
    channel, maximum = prompt.get("channel"), prompt.get("max_bytes")
    if channel == "stdin":
        return "max_bytes" in prompt and maximum is None
    return (channel == "argv" and isinstance(maximum, int)
            and not isinstance(maximum, bool) and maximum >= 0)


def _well_formed(data) -> bool:
    if not isinstance(data, dict):
        return False
    for key, values in CAPABILITY_VALUES.items():
        item = data.get(key)
        if not isinstance(item, dict) or item.get("value") not in values:
            return False
        if not _label_ok(item.get("label")):
            return False
    return _prompt_ok(data.get("prompt"))


def _capabilities(lines) -> dict | str:
    matches = [line for line in lines if line.startswith(CAPABILITIES_PREFIX)]
    if not matches:
        return NO_LINE_REASON
    if len(matches) != 1:
        return BAD_LINE_REASON
    try:
        data = json.loads(matches[0][len(CAPABILITIES_PREFIX):])
    except ValueError:
        return BAD_LINE_REASON
    if not _well_formed(data):
        return BAD_LINE_REASON
    result = {
        key: {"value": data[key]["value"], "label": {
            "state": data[key]["label"]["state"], "source": data[key]["label"]["source"]
        }} for key in CAPABILITY_VALUES
    }
    result["prompt"] = {"channel": data["prompt"]["channel"],
                        "max_bytes": data["prompt"]["max_bytes"]}
    return result


def _setting_rows(lines) -> tuple[tuple, tuple, tuple, dict | None]:
    skills, mcp, settings = [], [], []
    context = None
    for line in lines:
        match = SETTING_LINE_RE.fullmatch(line)
        if not match:
            continue
        name, value, state, reason, form = (match.group(key) for key in
                                            ("name", "value", "state", "reason", "form"))
        if name == "context" and context is None:
            context = {"value": value, "state": state, "reason": reason}
        if name == "skill" and (form is None or form in SKILL_FORMS):
            skills.append({"name": value, "state": state, "reason": reason, "form": form})
        elif name == "mcp":
            mcp.append({"name": value, "state": state, "reason": reason})
        elif name in APPLIED_SETTINGS and state == "applied":
            settings.append({"name": name, "value": value})
    return tuple(skills), tuple(mcp), tuple(settings), context


def _skill_blocks(lines) -> tuple:
    blocks = []
    for line in lines:
        match = SKILL_BLOCK_RE.fullmatch(line)
        if match:
            blocks.append({"name": match.group("name"), "bytes": int(match.group("bytes")),
                           "sha256": match.group("sha256")})
    return tuple(blocks)


def lane_facts(lines: list[str] | None) -> LaneFacts:
    """The lane's facts from one print_argv_lines result.

    None (no preview), a missing line or a malformed line gives every capability unknown
    with the reason as its label; setting and skill-block lines are read whenever lines
    exist (D-03).
    """
    if lines is None:
        return unknown_facts(NO_PREVIEW_REASON)
    caps = _capabilities(lines)
    base = (unknown_facts(caps) if isinstance(caps, str) else
            LaneFacts(caps["write"], caps["shell"], caps["skills"], caps["mcp"], caps["prompt"]))
    skills, mcp, settings, context = _setting_rows(lines)
    return base._replace(skill_settings=skills, mcp_settings=mcp, settings=settings,
                         context_setting=context, skill_blocks=_skill_blocks(lines))
