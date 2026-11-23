"""Lane capability facts read from the runner's --print-argv lines,

and the block built from them (SPEC R3, R4; D-02 to D-04).
"""

import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from typing import NamedTuple

from ai_kit_spec import lens_delivery, prompt_guard, skill_table
from ai_kit_spec.detection import (
    CBM_NAME,
    CBM_REGISTRATION_KEYS,
    cbm_registration,
    detect_tool_availability,
    resolve_agents_tooling_path,
    runtime_id,
)
from ai_kit_spec.prompt_guard import escape_value
from ai_kit_spec.runner_dispatch import (
    PREVIEW_TIMEOUT_S,
    SETTING_LINE_RE,
    RunnerSeams,
    RunnerSpec,
    child_env,
    print_argv_lines,
    review_spec,
    spec_with_effort,
)
from ai_kit_spec.secret_shapes import redact
from ai_kit_spec.tooling_guidance import (
    CBM_TOOLS,
    _code_index_line,
    resolve_shared_tooling_reference_path,
)

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


class LaneRequest(NamedTuple):
    """Inputs for one lane composition."""
    runtime: str | None
    model: str
    role: str
    cwd: str
    runner_spec: RunnerSpec | None
    native: bool = False
    soft_confinement: str | None = None
    lens_role: str = "review_lens"


def _print_argv(spec: RunnerSpec, env: dict) -> list[str] | None:
    return print_argv_lines(spec, RunnerSeams(env_fn=lambda: dict(env)))


class ComposeSeams(NamedTuple):
    """Replaceable external observations for composition."""
    print_argv_fn: Callable[[RunnerSpec, dict], list[str] | None] = _print_argv
    scan_fn: Callable[[dict, str], dict] = skill_table.scan
    window_fn: Callable[..., dict] = prompt_guard.window_for


DEFAULT_SEAMS = ComposeSeams()


class ComposeResult(NamedTuple):
    """Block and run-scoped resources produced for a lane."""
    block: str = ""
    skill_names: tuple = ()
    skill_paths: tuple = ()
    mcp_config: str | None = None
    run_dir: str | None = None
    refusal: dict | None = None
    window: dict | None = None
    facts: object = None


class LaneRefused(ValueError):
    """A closed refusal at a dispatch boundary."""
    def __init__(self, record: dict):
        self.record = record
        super().__init__(f"refused: {record.get('reason')}")


def with_block(block: str, prompt_text: str) -> str:
    """Prepend a nonempty block to a prompt."""
    return f"{block}\n\n{prompt_text}" if block else prompt_text


def lane_spec(spec: RunnerSpec, composed: ComposeResult) -> RunnerSpec:
    """Apply the composed delivery arguments to a runner spec."""
    return spec._replace(skill_names=composed.skill_names, skill_paths=composed.skill_paths,
                         mcp_config=composed.mcp_config)


def cleanup(composed: ComposeResult) -> None:
    """Remove run-scoped resources."""
    if composed.run_dir:
        shutil.rmtree(composed.run_dir, ignore_errors=True)


def _table_host(scan: dict, runtime: str | None) -> dict:
    shared = scan.get("agents", {})
    if runtime in scan:
        own = scan[runtime]
        return {**own, "skills": [*own.get("skills", []), *shared.get("skills", [])],
                "mcp": own.get("mcp", "unknown")}
    return {"skills": list(shared.get("skills", [])), "mcp": "unknown"}


def _git_value(directory: str, *args: str) -> str | None:
    try:
        result = subprocess.run(["git", "-C", directory, "rev-parse", *args],
                                capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _doc_worktrees(files, repo: str, cwd: str) -> tuple:
    common = _git_value(repo, "--path-format=absolute", "--git-common-dir")
    if not common:
        return ()
    roots = set()
    for value in files:
        if not isinstance(value, str) or not value.strip():
            continue
        path = os.path.realpath(os.path.join(cwd, value))
        if os.path.commonpath((path, repo)) == repo:
            continue
        parent = os.path.dirname(path)
        while not os.path.isdir(parent):
            next_parent = os.path.dirname(parent)
            if next_parent == parent:
                break
            parent = next_parent
        top = _git_value(parent, "--show-toplevel")
        if top and _git_value(top, "--path-format=absolute", "--git-common-dir") == common:
            roots.add(os.path.realpath(top))
    return tuple(sorted(roots))


class _Lane(NamedTuple):
    req: LaneRequest
    env: dict
    child: dict
    host: dict
    repo: str
    roots: list
    doc_roots: tuple
    notes: tuple
    seams: ComposeSeams
    shared_path: str | None
    agents_path: str | None
    tooling_omitted: tuple


def guidance_paths(env: dict, repo: str, roots: list) -> tuple[str | None, str | None, tuple]:
    """Resolve guidance paths without embedding rejected values."""
    values = (resolve_shared_tooling_reference_path(),
              resolve_agents_tooling_path(child_env(env=env)))
    accepted, omitted = [], []
    for name, value in zip(("SHARED_TOOLING_PATH", "AGENTS_TOOLING_PATH"), values, strict=True):
        bad = (prompt_guard.validate_values([(name.lower(), str(value))], repo, roots)
               if value else [])
        accepted.append(str(value) if value and not bad else None)
        if bad:
            omitted.append((name, bad[0]["reason"]))
    return accepted[0], accepted[1], tuple(omitted)


def _lane(spec, env, seams, files) -> _Lane:
    scan = seams.scan_fn(env, spec.cwd)
    repo = prompt_guard.repo_root(spec.cwd)
    doc_roots = _doc_worktrees(files, repo, spec.cwd)
    notes = (f"documents from other worktrees: {len(doc_roots)} "
             f"({', '.join(doc_roots)})",) if doc_roots else ()
    roots = skill_table.skill_roots(scan)
    shared, agents, omitted = guidance_paths(env, repo, roots)
    return _Lane(spec, env, child_env(env=env), _table_host(scan, spec.runtime), repo,
                 roots, doc_roots, notes, seams, shared, agents, omitted)


def _value_refusal(lane: _Lane, files, skill_paths, run_dir, mcp_file) -> dict | None:
    values: list[tuple[str, object]] = [("cwd", lane.req.cwd)]
    values.extend((f"skill_path[{i}]", p) for i, p in enumerate(skill_paths))
    docs = [(f"files[{i}]", value) for i, value in enumerate(files)]
    bad = prompt_guard.validate_values(values, lane.repo, lane.roots, base=lane.req.cwd)
    bad += prompt_guard.validate_values(docs, lane.repo, lane.roots, extra_roots=lane.doc_roots,
                                        base=lane.req.cwd)
    if mcp_file:
        bad += prompt_guard.validate_values([("mcp_config", mcp_file)], lane.repo, lane.roots,
                                            extra_roots=(run_dir,), base=lane.req.cwd)
    return prompt_guard.refusal_record(bad[0]["reason"], {"rejections": bad}) if bad else None


def _checked(lane: _Lane, files) -> list:
    rows = lens_delivery.lens_set(lane.host, list(files or ()), role=lane.req.lens_role,
                                  native_host=lane.req.runtime if lane.req.native else None)
    return [lens_delivery.check_lens(row, lane.repo, lane.roots) for row in rows]


def _mcp(lane: _Lane) -> tuple[str | None, str | None]:
    picks = lens_delivery.mcp_pick(
        lane.host, child_path(lane.child.get("PATH") or "", lane.req.cwd),
        user=skill_table.table_inputs(lane.req.cwd, lane.env)[1])
    if not picks:
        return None, None
    run_dir = tempfile.mkdtemp(prefix="aikit-mcp-")
    try:
        os.chmod(run_dir, 0o700)
        mcp_file = lens_delivery.write_mcp_file(run_dir, picks)
    except BaseException:
        shutil.rmtree(run_dir, ignore_errors=True)
        raise
    return run_dir, mcp_file


class _Fit(NamedTuple):
    facts0: LaneFacts
    window: dict
    cap: int | None
    run_dir: str | None
    mcp_file: str | None
    files: object


def _block_input(lane: _Lane, facts, rows) -> BlockInput:
    return BlockInput(facts, lane.child, lane.host, rows, lane.req.role,
                      lane.req.runtime or "custom", lane.req.model, lane.req.soft_confinement,
                      shared_path=lane.shared_path, agents_path=lane.agents_path,
                      tooling_omitted=lane.tooling_omitted, notes=lane.notes, cwd=lane.req.cwd)


def _delivery_bytes(facts: LaneFacts, delivered: list) -> tuple[int, int]:
    prose = {b["name"]: b["bytes"] for b in facts.skill_blocks}
    state = {s["name"]: (s["state"], s["form"]) for s in facts.skill_settings}
    total = argv_total = 0
    for row in delivered:
        applied, form = state.get(row["skill_name"], (None, None))
        if applied == "applied":
            size = prose.get(row["skill_name"], 0) if form == "prose" else (
                row["bytes"] if form in ("path", "name") else 0)
            total += size
            if form == "prose":
                argv_total += size
    return total, argv_total


def _final(lane: _Lane, fit: _Fit, delivered: list, skipped: list, prompt_text: str):
    composed = ComposeResult(skill_names=tuple(r["skill_name"] for r in delivered),
                             skill_paths=tuple(r["path"] for r in delivered),
                             mcp_config=fit.mcp_file, run_dir=fit.run_dir, window=fit.window)
    assert lane.req.runner_spec is not None
    runner = lane_spec(lane.req.runner_spec, composed)
    facts = (fit.facts0 if runner == lane.req.runner_spec else
             lane_facts(lane.seams.print_argv_fn(runner, lane.env)))
    block = build_block(_block_input(lane, facts, [*delivered, *skipped]))
    refusal = _value_refusal(lane, fit.files, composed.skill_paths, fit.run_dir, fit.mcp_file)
    if refusal is not None:
        return composed._replace(block=block, refusal=refusal, facts=facts), False
    total, argv_total = _delivery_bytes(facts, delivered)
    base = len(with_block(block, prompt_text).encode("utf-8"))
    total += base
    argv_total += base
    refusal = prompt_guard.check_window(math.ceil(total / prompt_guard.BYTES_PER_TOKEN), fit.window)
    retry = bool(delivered) and (refusal is not None or
                                (fit.cap is not None and argv_total > fit.cap))
    return composed._replace(block=block, refusal=None if retry else refusal, facts=facts), retry


# pylint: disable-next=line-too-long
def compose_for_lane(spec: LaneRequest, prompt_text: str, files, env: dict, seams: ComposeSeams) -> ComposeResult:  # noqa: E501
    """Compose the tracer block from this lane's own preview."""
    if files is None:
        return ComposeResult()
    lane = _lane(spec, env, seams, files)
    if spec.native:
        return ComposeResult(block=build_block(_block_input(lane, None, _checked(lane, files))),
                             refusal=_value_refusal(lane, files, (), None, None))
    if spec.runner_spec is None:
        facts = lane_facts([])
        return ComposeResult(block=build_block(_block_input(lane, facts, [])),
                             refusal=_value_refusal(lane, files, (), None, None), facts=facts)
    facts = lane_facts(seams.print_argv_fn(spec.runner_spec, env))
    window = seams.window_fn(spec.runtime, spec.model, env, spec.cwd, context_form_applied(facts))
    cap = facts.prompt["max_bytes"] if facts.prompt["channel"] == "argv" else None
    run_dir, mcp_file = _mcp(lane)
    fit = _Fit(facts, window, cap, run_dir, mcp_file, files)
    try:
        return _plan(lane, fit, prompt_text)
    except BaseException:
        if run_dir:
            shutil.rmtree(run_dir, ignore_errors=True)
        raise


def _plan(lane: _Lane, fit: _Fit, prompt_text: str) -> ComposeResult:
    draft = build_block(_block_input(lane, fit.facts0, []))
    delivered, skipped = lens_delivery.plan_lenses(
        _checked(lane, fit.files), len(with_block(draft, prompt_text).encode("utf-8")),
        fit.window["value"], fit.cap)
    while True:
        composed, retry = _final(lane, fit, delivered, skipped, prompt_text)
        if not retry:
            return composed
        skipped.append({**delivered.pop(), "note": "over_window"})


def _soft_confinement(target_dir: str) -> str:
    # Local import: execute_dispatch imports this module.
    # pylint: disable=import-outside-toplevel,cyclic-import
    from ai_kit_spec.execute_dispatch import build_soft_confinement_guidance

    return build_soft_confinement_guidance(target_dir)


def cmd_capability_block(args, deps) -> int:
    """Print a lane's block without executing the lane."""
    env = deps.env_fn()
    cwd = os.path.abspath(args.cwd)
    runner = (None if args.native else
              review_spec(args.runtime, args.model, None, PREVIEW_TIMEOUT_S, cwd=cwd)
              if args.role == "review" else
              spec_with_effort(args.runtime, args.model, "exec", PREVIEW_TIMEOUT_S, {"cwd": cwd}))
    soft = _soft_confinement(cwd) if args.role == "execute" else None
    composed = compose_for_lane(LaneRequest(args.runtime, args.model, args.role, cwd, runner,
                                            native=args.native, soft_confinement=soft),
                                "", tuple(args.files), env, DEFAULT_SEAMS)
    try:
        if composed.refusal:
            print(json.dumps(composed.refusal, sort_keys=True), file=sys.stderr)
            return prompt_guard.REFUSED_EXIT
        print(composed.block)
        return 0
    finally:
        cleanup(composed)


def register_parsers(sub) -> None:
    """Register the read-only capability command."""
    parser = sub.add_parser("capability-block",
                            help="print a lane's capability block without spawning it (read only)")
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--role", required=True, choices=["review", "execute"])
    parser.add_argument("--files", nargs="*", default=[])
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("--native", action="store_true",
                        help="a native lane: the host runs it; prints its lens lines only")


COMMANDS = {"capability-block": cmd_capability_block}


def lane_summary(entry: dict, role: str, cwd: str, env: dict,
                 seams: ComposeSeams) -> tuple[str, str, str]:
    """Preview one resolved lane without executing it."""
    roots = skill_table.skill_roots(seams.scan_fn(env, cwd))
    omitted = guidance_paths(env, prompt_guard.repo_root(cwd), roots)[2]
    notes = tuple(f"guidance omitted: {name} ({reason})" for name, reason in omitted)
    label = escape_value(str(entry.get("model") or entry.get("key", "")))
    if "runtime" not in entry and not entry.get("command"):
        return "native", label, summary_line(None, "native", label, role, notes=notes)
    runtime = entry.get("runtime")
    if (("runtime" in entry and (not isinstance(runtime, str) or not runtime))
            or ("extra" in entry and not isinstance(entry["extra"], dict))):
        return (escape_value(repr(runtime)), label,
                "invalid lane entry: runtime must be a string and extra a table")
    if entry.get("command") and not runtime:
        return "custom", label, summary_line(lane_facts([]), "custom", label, role, notes=notes)
    assert isinstance(runtime, str)
    rt = runtime_id(runtime)
    knobs = {**entry, **(entry.get("extra") or {}), "cwd": cwd}
    runner = spec_with_effort(rt, entry.get("model", ""),
                              "review" if role == "review" else "exec", PREVIEW_TIMEOUT_S, knobs)
    shown = escape_value(rt)
    return shown, label, summary_line(lane_facts(seams.print_argv_fn(runner, env)),
                                      shown, label, role, notes=notes)


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
