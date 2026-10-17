"""Render and write the per-project cross-AI runner (18 D-09/D-26/D-28).

The sha256 in line 2 covers raw bytes after the second newline (no decoding or newline
normalization). ``script_state`` is the only implementation of that hash rule; this module
is the only writer of the generated script.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import NamedTuple

from . import cross_ai, gsd_catalog

HEADER_RE = re.compile(
    rb"^// ai-kit-cross-ai generator=ai-kit-gsd-curated-config "
    rb"template=(\d+) sha256=(?P<sha>[0-9a-f]{64}|UNSTAMPED)$"
)
GUIDANCE_PATH = ".planning/scripts/cross-ai-guidance.md"
GUIDANCE_HEADER_RE = re.compile(
    rb"^<!-- ai-kit-cross-ai-guidance generator=ai-kit-gsd-curated-config "
    rb"template=1 sha256=(?P<sha>[0-9a-f]{64}|UNSTAMPED) -->$"
)
_GUIDANCE_NOTICE = (
    b"<!-- Rendered by ai-kit; edits produce a .new file on the next render. -->"
)
# A floor, not the current version: template 3 is the first with the flags the GSD hook
# emits (--codex-sandbox, --no-preamble, --prepend-file; D-18/D-27/D-30).
_READY_TEMPLATE = 3
_CONFIG_START = b"// <config>"
_CONFIG_END = b"// </config>"
_CONFIG_MARKER = b"const CONFIG = "


class ScriptPlan(NamedTuple):
    kind: str
    path: str
    write_path: str | None
    data: bytes
    state: str | None
    note: str
    expected: bytes | None


def split_header(data: bytes) -> tuple[bytes, bytes, bytes] | None:
    first = data.find(b"\n")
    if first == -1:
        return None
    second = data.find(b"\n", first + 1)
    if second == -1:
        return None
    return data[:first], data[first + 1 : second], data[second + 1 :]


def script_state(data: bytes, header_re: re.Pattern[bytes] = HEADER_RE) -> str:
    parts = split_header(data)
    if parts is None:
        return "foreign"
    _shebang, header, body = parts
    match = header_re.match(header)
    if not match:
        return "foreign"
    digest = match["sha"]
    if digest == b"UNSTAMPED":
        return "unstamped"
    expected = hashlib.sha256(body).hexdigest().encode("ascii")
    return "pristine" if digest == expected else "edited"


def template_version(data: bytes) -> int:
    parts = split_header(data)
    if parts is None:
        raise ValueError("template header missing")
    _shebang, header, _body = parts
    match = HEADER_RE.match(header)
    if not match:
        raise ValueError("template header not recognized")
    return int(match.group(1))


def template_config(template: bytes) -> dict:
    start = template.find(_CONFIG_START)
    end = template.find(_CONFIG_END)
    if start == -1 or end == -1 or end <= start:
        raise ValueError("CONFIG block missing")
    block = template[start:end]
    idx = block.find(_CONFIG_MARKER)
    if idx == -1:
        raise ValueError("CONFIG assignment missing")
    rest = block[idx + len(_CONFIG_MARKER) :].strip()
    if rest.endswith(b";"):
        rest = rest[:-1].strip()
    parsed = json.loads(rest)
    if not isinstance(parsed, dict):
        raise ValueError("CONFIG is not an object")
    return parsed


def runner_config(template: bytes, artifact: dict, scrub_env) -> dict:
    base = dict(template_config(template))
    cfg = artifact.get("config") or {}
    if "prefer" in cfg:
        base["prefer"] = cfg["prefer"]
    if "models" in cfg:
        base["models"] = cfg["models"]
    if "outer_timeout_s" in cfg:
        base["outerTimeoutS"] = cfg["outer_timeout_s"]
    if "router_backed" in cfg:
        base["routerBacked"] = cfg["router_backed"]
    base["effort"] = cfg.get("effort", {})
    base["scrubEnv"] = sorted(scrub_env)
    return base


def _config_block(config: dict) -> bytes:
    payload = json.dumps(config, indent=2, sort_keys=True)
    return _CONFIG_MARKER + payload.encode("utf-8") + b";\n"


def _replace_config(template: bytes, config: dict) -> bytes:
    start = template.find(_CONFIG_START)
    end = template.find(_CONFIG_END)
    if start == -1 or end == -1:
        raise ValueError("CONFIG block missing")
    line_end = template.find(b"\n", start)
    if line_end == -1:
        raise ValueError("CONFIG block malformed")
    inner_start = line_end + 1
    return template[:inner_start] + _config_block(config) + template[end:]


def _stamp(body_source: bytes, version: int) -> bytes:
    parts = split_header(body_source)
    if parts is None:
        raise ValueError("cannot stamp without header")
    shebang, _old_header, body = parts
    digest = hashlib.sha256(body).hexdigest()
    header = (
        f"// ai-kit-cross-ai generator=ai-kit-gsd-curated-config "
        f"template={version} sha256={digest}"
    ).encode()
    return shebang + b"\n" + header + b"\n" + body


def render(template: bytes, config: dict) -> bytes:
    version = template_version(template)
    replaced = _replace_config(template, config)
    return _stamp(replaced, version)


def load_template() -> tuple[bytes | None, str | None]:
    mod = gsd_catalog.load_ai_kit_spec_module("tooling_guidance")
    if mod is None:
        return None, gsd_catalog.SIBLING_MISSING
    path = mod.resolve_cross_ai_template_path()
    if path is None:
        return None, gsd_catalog.SIBLING_MISSING
    with open(path, "rb") as f:
        return f.read(), None


class ScriptReadError(ValueError):
    """A target exists but could not be read, so it must not be treated as absent."""


def _read_target(path: str) -> bytes | None:
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise _read_error(path, exc) from exc


_STATE_DETAIL = {
    "edited": "edited (its body no longer matches its sha256 header)",
    "unstamped": "unstamped (sha256=UNSTAMPED)",
    "foreign": "foreign (unrecognized generator header)",
}


def _note_new(state: str, path: str) -> str:
    return (
        f"existing {path} was {_STATE_DETAIL[state]}; "
        f"the new render is {path}.new; merge it by hand"
    )


def _plan_rendered(path: str, rendered: bytes, header_re: re.Pattern[bytes]) -> ScriptPlan:
    """Add, keep a pristine match, change a pristine file, or write `.new` beside any other."""
    existing = _read_target(path)
    if existing is None:
        return ScriptPlan("add", path, path, rendered, None, "", None)
    state = script_state(existing, header_re)
    if state == "pristine" and existing == rendered:
        return ScriptPlan("keep-pristine", path, None, rendered, state, "", existing)
    if state == "pristine":
        return ScriptPlan("change", path, path, rendered, state, "", existing)
    return ScriptPlan(
        "new-as-.new", path, path + ".new", rendered, state, _note_new(state, path), existing
    )


def plan_script(project_dir: str, artifact: dict, template: bytes, scrub_env) -> ScriptPlan:
    path = os.path.abspath(os.path.join(project_dir, artifact["path"]))
    rendered = render(template, runner_config(template, artifact, scrub_env))
    return _plan_rendered(path, rendered, HEADER_RE)


def _scrub_env() -> list[str]:
    detection = gsd_catalog.load_ai_kit_spec_module("detection")
    if detection is None:
        return []
    return sorted(detection.HOST_SIGNAL_ENV_VARS)


def _publish(write_path: str, data: bytes) -> None:
    cache = gsd_catalog.load_ai_kit_spec_module("cache")
    if cache is None:
        raise OSError(gsd_catalog.SIBLING_MISSING)
    cache.cache_write_bytes(write_path, data, mode=cache.umask_file_mode())


def _upgrade_config(template: bytes, existing: bytes, scrub_env) -> dict:
    """The existing CONFIG wins; a file that is not ours keeps the template's."""
    try:
        kept = template_config(existing)
    except ValueError:
        kept = {}
    merged = {**template_config(template), **kept}
    merged["scrubEnv"] = sorted(scrub_env)
    return merged


def _kept_note(state: str, path: str) -> str:
    return f"existing {path} is {_STATE_DETAIL[state]} and current; kept"


def plan_runner_upgrade(project_dir: str, template: bytes, scrub_env) -> ScriptPlan:
    """Upgrade a project's runner in place, keeping its CONFIG over the template's."""
    path = os.path.abspath(os.path.join(project_dir, cross_ai.SCRIPT_PATH))
    existing = _read_target(path)
    if existing is None:
        config = template_config(template)
        config["scrubEnv"] = sorted(scrub_env)
        return ScriptPlan("add", path, path, render(template, config), None, "", None)
    state = script_state(existing)
    try:
        older = template_version(existing) < template_version(template)
    except ValueError:
        older = True
    if state == "pristine" and older:
        data = render(template, _upgrade_config(template, existing, scrub_env))
        return ScriptPlan("change", path, path, data, state, "", existing)
    if state == "pristine":
        return ScriptPlan("keep-pristine", path, None, existing, state, "", existing)
    if older:
        data = render(template, _upgrade_config(template, existing, scrub_env))
        return ScriptPlan(
            "new-as-.new", path, path + ".new", data, state, _note_new(state, path), existing
        )
    return ScriptPlan("keep-edited", path, None, existing, state, _kept_note(state, path), existing)


def _guidance_bytes(text: str) -> bytes:
    body = text.encode("utf-8")
    digest = hashlib.sha256(body).hexdigest()
    header = (
        b"<!-- ai-kit-cross-ai-guidance generator=ai-kit-gsd-curated-config "
        b"template=1 sha256=" + digest.encode("ascii") + b" -->"
    )
    return _GUIDANCE_NOTICE + b"\n" + header + b"\n" + body


def plan_guidance(project_dir: str, text: str) -> ScriptPlan:
    path = os.path.abspath(os.path.join(project_dir, GUIDANCE_PATH))
    return _plan_rendered(path, _guidance_bytes(text), GUIDANCE_HEADER_RE)


class _EnsureStep(NamedTuple):
    kind: str | None
    notes: list[str]


def _read_error(path: str, exc: OSError) -> ScriptReadError:
    return ScriptReadError(f"cannot read {path}: {exc}")


def _error_result(runner: str | None, notes: list[str], message: str) -> dict:
    return {
        "ready": False, "runner": runner, "guidance": None,
        "notes": notes, "error": message,
    }


def _runner_ready(path: str) -> bool:
    data = _read_target(path)
    if data is None or script_state(data) == "foreign":
        return False
    return template_version(data) >= _READY_TEMPLATE


def _write_plan(plan: ScriptPlan) -> _EnsureStep:
    performed = write_script(plan)
    return _EnsureStep(performed.kind, [performed.note] if performed.note else [])


def _guidance_step(project_dir: str, text: str | None) -> _EnsureStep:
    if text is None:
        return _EnsureStep(None, [])
    return _write_plan(plan_guidance(project_dir, text))


def _ensure_runner_plans(
    project_dir: str, runner_plan: ScriptPlan, guidance_text: str | None
) -> dict:
    runner = _write_plan(runner_plan)
    try:
        guidance = _guidance_step(project_dir, guidance_text)
    except (OSError, ScriptReadError, ValueError) as exc:
        message = str(exc) or type(exc).__name__
        note = f"runner {runner.kind} already written; guidance failed: {message}"
        return _error_result(runner.kind, [*runner.notes, note], message)
    runner_path = os.path.abspath(os.path.join(project_dir, cross_ai.SCRIPT_PATH))
    ready = _runner_ready(runner_path)
    if guidance_text is not None:
        guidance_path = os.path.abspath(os.path.join(project_dir, GUIDANCE_PATH))
        ready = ready and os.path.isfile(guidance_path)
    return {
        "ready": ready,
        "runner": runner.kind,
        "guidance": guidance.kind,
        "notes": runner.notes + guidance.notes,
    }


def _require_project_dir(project_dir: str) -> None:
    """A missing project dir is a read error, not an absent runner (T-18.1-84)."""
    try:
        if os.path.isdir(project_dir):
            return
    except OSError as exc:
        raise _read_error(project_dir, exc) from exc
    raise ScriptReadError(f"cannot read {project_dir}: not a directory")


def _checked_template() -> tuple[bytes | None, str | None]:
    """The shipped template, or `(None, error)` for a missing or unusable one."""
    try:
        template, error = load_template()
    except OSError as exc:
        return None, f"cannot read template: {exc}"
    if template is None:
        return None, error or "template unavailable"
    try:
        template_version(template)
        template_config(template)
    except ValueError as exc:
        return None, f"template unusable: {exc}"
    return template, None


def ensure_runner(project_dir: str, guidance_text: str | None = None) -> dict:
    """Render or upgrade the project runner; optionally write the guidance file (D-33)."""
    if guidance_text is not None and not guidance_text.strip():
        return _error_result(None, [], "guidance text is empty")
    template, error = _checked_template()
    if template is None:
        return _error_result(None, [], error or "template unavailable")
    try:
        _require_project_dir(project_dir)
        runner_plan = plan_runner_upgrade(project_dir, template, _scrub_env())
        return _ensure_runner_plans(project_dir, runner_plan, guidance_text)
    except (OSError, ScriptReadError, ValueError) as exc:
        return _error_result(None, [], str(exc) or type(exc).__name__)


def write_script(plan: ScriptPlan) -> ScriptPlan:
    # shortcut: a write landing between the re-read and os.replace is still lost; closing that
    # needs a lock the runner does not take
    current = _read_target(plan.path)
    if current != plan.expected:
        note = (
            f"{plan.path} changed after planning; the new render is {plan.path}.new; "
            "merge it by hand"
        )
        performed = plan._replace(kind="new-as-.new", write_path=plan.path + ".new", note=note)
        _publish(plan.path + ".new", performed.data)
        return performed
    if plan.kind == "keep-pristine":
        return plan
    write_path = plan.write_path
    if write_path is None:
        return plan
    _publish(write_path, plan.data)
    return plan
