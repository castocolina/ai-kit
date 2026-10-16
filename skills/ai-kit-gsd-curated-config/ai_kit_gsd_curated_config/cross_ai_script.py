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

from . import gsd_catalog

HEADER_RE = re.compile(
    rb"^// ai-kit-cross-ai generator=ai-kit-gsd-curated-config "
    rb"template=(\d+) sha256=([0-9a-f]{64}|UNSTAMPED)$"
)
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


def script_state(data: bytes) -> str:
    parts = split_header(data)
    if parts is None:
        return "foreign"
    _shebang, header, body = parts
    match = HEADER_RE.match(header)
    if not match:
        return "foreign"
    digest = match.group(2)
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


def _read_target(path: str) -> bytes | None:
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


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


def plan_script(project_dir: str, artifact: dict, template: bytes, scrub_env) -> ScriptPlan:
    rel = artifact["path"]
    path = os.path.abspath(os.path.join(project_dir, rel))
    rendered = render(template, runner_config(template, artifact, scrub_env))
    existing = _read_target(path)
    if existing is None:
        return ScriptPlan("add", path, path, rendered, None, "", None)
    state = script_state(existing)
    if state == "pristine":
        if existing == rendered:
            return ScriptPlan("keep-pristine", path, None, rendered, state, "", existing)
        return ScriptPlan("change", path, path, rendered, state, "", existing)
    new_path = path + ".new"
    return ScriptPlan(
        "new-as-.new", path, new_path, rendered, state, _note_new(state, path), existing
    )


def _publish(write_path: str, data: bytes) -> None:
    cache = gsd_catalog.load_ai_kit_spec_module("cache")
    if cache is None:
        raise OSError(gsd_catalog.SIBLING_MISSING)
    cache.cache_write_bytes(write_path, data, mode=cache.umask_file_mode())


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
