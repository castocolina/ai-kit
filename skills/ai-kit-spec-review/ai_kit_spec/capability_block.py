"""Lane capability facts read from the runner's --print-argv lines,

and the block built from them (SPEC R3, R4; D-02 to D-04).
"""

import json
import os
import re
import shutil
from typing import NamedTuple

from ai_kit_spec.detection import (
    CBM_NAME,
    CBM_REGISTRATION_KEYS,
    cbm_registration,
    detect_tool_availability,
    runtime_id,
)
from ai_kit_spec.prompt_guard import escape_value
from ai_kit_spec.runner_dispatch import SETTING_LINE_RE
from ai_kit_spec.secret_shapes import redact
from ai_kit_spec.tooling_guidance import CBM_TOOLS, _code_index_line

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


SECTIONS = ("LANE", "ACCESS", "TOOLS", "CODE INDEX", "SKILLS", "SETTINGS")
UNKNOWN_TEXT = "unknown: make no assumption"
# One of 39-11's LENS_NOTES: only this section sees the runner's ignored line for a passed lens.
HOST_CANNOT_LOAD = "host_cannot_load"
ACCESS_TEXT = {
    "write": {"none": "read-only", "workspace": "writes confined by the host's sandbox to the "
              "working tree and the roots that sandbox allows",
              "full": "full write, not confined by the host"},
    "shell": {"yes": "a shell tool is available", "no": "no shell tool"},
    "skills": {"none": "your host loads no skills", "path": "your host loads skills passed by path",
               "discovery": "your host loads skills by name"},
    "mcp": {"none": "no MCP tools", "host_config": "MCP servers from your host's own config",
            "call_file": "MCP servers from the file this call passed"},
}
NO_SHELL_LINE = "none: this lane has no shell tool"
NO_TOOL_LINE = "no listed tool was found on this lane's PATH"
NO_INDEX_LINE = "none: no code index for this lane"
SHELL_IF = "If you have a shell: "
ENABLED_INDEX_LINE = (
    "codebase-memory-mcp is passed to your host for this call (the runner reported its MCP file "
    "applied; whether the server starts is not tested): if its tools are present, use "
    + ", ".join(CBM_TOOLS)
    + " before broad file reads or grep; when list_projects shows no project for this checkout, "
    "run index_repository on it first."
)


class BlockInput(NamedTuple):
    """Everything one lane's block is built from (SPEC R4).

    A NamedTuple because the inputs exceed pylint's argument cap.
    """

    facts: LaneFacts | None  # None is a native lane: the host runs it, no argv.
    child_env: dict
    table_host: dict
    lens_report: list
    role: str
    runtime: str
    model: str
    soft_confinement: str | None = None
    shared_path: str | None = None
    agents_path: str | None = None
    cwd: str | None = None
    notes: tuple = ()
    tooling_omitted: tuple = ()


def _shown(value) -> str:
    return escape_value(redact(str(value), "<redacted>"))


def _lane_section(lane: BlockInput) -> list[str]:
    return ["LANE", f"runtime: {_shown(lane.runtime)}", f"model: {_shown(lane.model)}",
            f"role: {_shown(lane.role)}", *(f"note: {_shown(text)}" for text in lane.notes)]


def _fact_line(key, fact) -> str:
    label = f"{_shown(fact['label']['state'])}: {_shown(fact['label']['source'])}"
    value = fact["value"]
    if value == "unknown":
        return f"{key}: {UNKNOWN_TEXT} [{label}]"
    return f"{key}: {_shown(value)} ({ACCESS_TEXT[key][value]}) [{label}]"


def _access_section(lane: BlockInput) -> list[str]:
    facts = lane.facts
    assert facts is not None
    lines = ["ACCESS", *(_fact_line(key, getattr(facts, key))
                          for key in ("write", "shell", "skills", "mcp"))]
    if (lane.role == "execute" and facts.write["value"] in ("full", "unknown")
            and lane.soft_confinement):
        lines.append(_shown(lane.soft_confinement))
    return lines


def child_path(path_value: str, _cwd: str | None) -> str:
    """Keep only the absolute entries of the child's PATH, never the parent's.

    An empty or relative entry would find tools (and the MCP command) in the working
    directory, so it is dropped: a missing or empty PATH finds nothing. `_cwd` stays in the
    signature for the callers that pass the lane's cwd.
    """
    return os.pathsep.join(entry for entry in path_value.split(os.pathsep)
                           if os.path.isabs(entry))


def _tool_map(lane: BlockInput) -> dict:
    path = child_path(lane.child_env.get("PATH") or "", lane.cwd)
    return detect_tool_availability(which_fn=lambda name: shutil.which(name, path=path))


def _tools_section(lane: BlockInput, tools: dict) -> list[str]:
    facts = lane.facts
    assert facts is not None
    if facts.shell["value"] == "no":
        return ["TOOLS", NO_SHELL_LINE]
    lines = ["TOOLS"]
    for name, path, suffix in (
        ("SHARED_TOOLING_PATH", lane.shared_path, "for this repo's confirmed tool preferences."),
        ("AGENTS_TOOLING_PATH", lane.agents_path,
         "for confirmed tool preferences on this machine."),
    ):
        if path is not None:
            shown = _shown(path)
            lines.extend((f"{name} = {shown}", f"Read {shown} {suffix}"))
        lines.extend(f"{name}: omitted ({_shown(reason)})" for key, reason in lane.tooling_omitted
                     if key == name)
    found = {name: True for name, present in tools.items() if present}
    if found:
        lines.append("TOOL_AVAILABILITY = " +
                     json.dumps(found, sort_keys=True, separators=(",", ":")))
        lines.append("If you have a shell, these tools are on its PATH: " +
                     ", ".join(sorted(found)) + ".")
    else:
        lines.append(NO_TOOL_LINE)
    return lines


def _index_route(lane: BlockInput, tools: dict) -> str | None:
    facts = lane.facts
    assert facts is not None
    if not tools.get(CBM_NAME):
        return None
    if any(s["name"] == CBM_NAME and s["state"] == "applied" for s in facts.mcp_settings):
        return ENABLED_INDEX_LINE
    name = runtime_id(lane.runtime)
    if (facts.mcp["value"] in ("host_config", "unknown") and name in CBM_REGISTRATION_KEYS
            and cbm_registration(name, lane.child_env).registered is True):
        return _code_index_line(True, name)
    if facts.shell["value"] != "no":
        prefix = SHELL_IF if facts.shell["value"] == "unknown" else ""
        return prefix + _code_index_line(False, name)
    return None


def _code_index_section(lane: BlockInput, tools: dict) -> list[str]:
    line = _index_route(lane, tools)
    lines = ["CODE INDEX", line or NO_INDEX_LINE]
    rows = lane.table_host.get("mcp")
    if isinstance(rows, list):
        for row in rows:
            if row.get("role") != "code_index":
                continue
            if row["name"] == CBM_NAME and (line is not None or not tools.get(CBM_NAME)):
                continue
            lines.append(f"MCP server {_shown(row['name'])}: present in the host config, "
                         "not enabled for this call")
    return lines


def _skill_line(lane: BlockInput, row: dict) -> str:
    name = _shown(row["name"])
    facts = lane.facts
    if facts is None:
        return f"{name}: load the skill {name} by name if your host provides it (unverified)"
    runner_name = row.get("skill_name") or row["name"]
    setting = next((s for s in facts.skill_settings if s["name"] == runner_name), None)
    if setting is None or setting["state"] != "applied":
        status = UNKNOWN_TEXT if setting is None else f"skipped ({HOST_CANNOT_LOAD})"
        return f"{name}: {status}"
    form = setting.get("form")
    path = _shown(row.get("path"))
    if form == "path":
        return f"{name}: delivered by path, loaded by your host from {path}"
    if form == "prose":
        block = next((b for b in facts.skill_blocks if b["name"] == runner_name), None)
        detail = f"path {path}"
        if block is not None:
            detail += f", sha256 {_shown(block['sha256'])}, {_shown(block['bytes'])} bytes"
        return f"{name}: inlined in this prompt between <skill> delimiters ({detail})"
    if form == "name":
        return f"{name}: loaded by name by your host"
    return f"{name}: {UNKNOWN_TEXT}"


def _skills_section(lane: BlockInput) -> list[str]:
    if not lane.lens_report:
        return []
    lines = ["SKILLS"]
    lines.extend(_skill_line(lane, row) for row in lane.lens_report if row.get("note") is None)
    lines.extend(f"{_shown(row['name'])}: skipped ({_shown(row['note'])})"
                 for row in lane.lens_report if row.get("note") is not None)
    return lines


def _settings_section(facts: LaneFacts) -> list[str]:
    lines = ["SETTINGS"]
    lines.extend(f"{_shown(s['name'])}: {_shown(s['value'])} (applied)" for s in facts.settings)
    if not facts.settings:
        lines.append(UNKNOWN_TEXT if facts.reason is not None else "none reported applied")
    return lines


def build_block(lane: BlockInput) -> str:
    """Build one lane's capability block from its own facts; native lanes get only lenses."""
    facts = lane.facts
    if facts is None:
        return "\n".join(_skills_section(lane))
    tools = _tool_map(lane)
    sections = (_lane_section(lane), _access_section(lane), _tools_section(lane, tools),
                _code_index_section(lane, tools), _skills_section(lane), _settings_section(facts))
    return "\n\n".join("\n".join(section) for section in sections if section)


def summary_line(facts: LaneFacts | None, runtime: str, model: str, role: str,
                 notes: tuple = ()) -> str:
    """Return facts for the capability summary; runtime and model belong to its prefix."""
    del runtime, model
    if facts is None:
        text = "native lane, no tool claims"
    else:
        w, s, k, m = (fact["value"] for fact in (facts.write, facts.shell, facts.skills, facts.mcp))
        text = f"write={_shown(w)} shell={_shown(s)} skills={_shown(k)} mcp={_shown(m)} "
        text += f"prompt={_shown(facts.prompt['channel'])}"
        if facts.prompt["max_bytes"] is not None:
            text += f" max_bytes={_shown(facts.prompt['max_bytes'])}"
        if role == "execute" and w in ("full", "unknown"):
            text += " soft-confinement=prose"
        if facts.reason is not None:
            text += f" ({_shown(facts.reason)})"
    return text + "".join(f"; note: {_shown(note)}" for note in notes)
