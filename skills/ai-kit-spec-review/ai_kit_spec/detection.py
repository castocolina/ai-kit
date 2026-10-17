import base64
import contextlib
import http.client
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any, NamedTuple

from ai_kit_spec.cache import cache_base
from ai_kit_spec.vendor import _MODEL_TIER_SUFFIXES

RUNTIMES_TTL_SECONDS = 30 * 24 * 3600   # ~30 days: CLI/model presence is near-static

# 16 D-12: pre-Phase-16 snapshots carry no key and are treated as version 1; bump this
# whenever the snapshot shape gains data a consumer relies on. Version 3 (17 D-32) adds the
# opencode 2.x `/api/model` image source (clis.opencode.image_input_source), so snapshots
# written before it re-detect even while their TTL is still fresh. Version 4 (18 D-25) adds
# clis.pi from pi's RPC get_available_models.
# 18.1 D-04/D-13: clis keyed by runtime id, node recorded
RUNTIMES_SCHEMA_VERSION = 5

# ── Runtime/CLI detection ───────────────────────────────────────────────

PI_RPC_ARGS = (
    "--mode", "rpc", "--offline", "--no-session", "--no-extensions",
    "--no-skills", "--no-context-files", "--no-mcp",
)
PI_RPC_REQUEST = '{"id":"1","type":"get_available_models"}\n'

# One-line verification labels copied from detect_current_runtime's docstring (Pitfall 9).
_LABEL_PI = (
    "source-inspected-only — confirmed in the installed "
    "`@earendil-works/pi-coding-agent` package's `dist/config.js`, not live-verified "
    "from a real pi session (16 D-03; live validation is Phase 22)."
)
_LABEL_OPENCODE = (
    "live-verified (01.2) via a live spawned `opencode run` subprocess."
)
_LABEL_CURSOR = (
    "source-inspected-only — confirmed via the installed cursor-agent bundle's own "
    "`index.js`, not a live subprocess."
)
_LABEL_CODEX_THREAD = (
    "observed in real codex session shell snapshots under `~/.codex/sessions` (the "
    "snapshot preamble exports `CODEX_THREAD_ID` from `__CODEX_SNAPSHOT_OVERRIDE_1`; "
    "20 occurrences, 16 D-02) — not yet live-verified from a codex host (Phase 20, "
    "EVAL-04)."
)
_LABEL_CODEX_VERSION = (
    "source-inspected-only — confirmed via openai/codex's open-source `exec_env.rs`, "
    "not a live subprocess."
)
_LABEL_CLAUDE = "live-verified (01.2) via the process's own env dump."


class Runtime(NamedTuple):
    binaries: tuple[str, ...]
    host_signals: tuple[tuple[str, str], ...]
    scrub_signals: tuple[str, ...] = ()
    list_argv: tuple[str, ...] | None = None
    native_selectors: tuple[str, ...] = ()
    review_only: bool = False
    model_suffix: str | None = None
    mcp_list: bool = False
    multi_provider: bool = False
    runner: bool = True


# Insertion order is host precedence. grok is a row, never a detected host (D-03).
RUNTIMES: dict[str, Runtime] = {
    "pi": Runtime(
        ("pi",),
        (("PI_CODING_AGENT", _LABEL_PI),),
        list_argv=PI_RPC_ARGS,
        model_suffix=r":(?:off|minimal|low|medium|high|xhigh|max)$",
    ),
    "opencode": Runtime(
        ("opencode",),
        (("OPENCODE", _LABEL_OPENCODE),),
        list_argv=("models",),
        model_suffix=r"#[^#/]+$",
        mcp_list=True,
        multi_provider=True,
    ),
    "cursor": Runtime(
        ("cursor-agent", "agent"),
        (("CURSOR_AGENT", _LABEL_CURSOR),),
        list_argv=("models",),
        model_suffix=r"\[[^\]]*\]$",
        mcp_list=True,
        multi_provider=True,
    ),
    "codex": Runtime(
        ("codex",),
        (("CODEX_THREAD_ID", _LABEL_CODEX_THREAD), ("CODEX_VERSION", _LABEL_CODEX_VERSION)),
        scrub_signals=("CODEX_SANDBOX",),
        list_argv=("debug", "models"),
        mcp_list=True,
    ),
    "claude": Runtime(
        ("claude",),
        (("CLAUDECODE", _LABEL_CLAUDE),),
        scrub_signals=("CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SSE_PORT"),
        native_selectors=("fable", "opus", "sonnet", "haiku"),
        review_only=True,
        mcp_list=True,
    ),
    "grok": Runtime(
        ("grok",),
        (),
        scrub_signals=("GROK_AGENT",),
        runner=False,
    ),
}

KNOWN_CLIS = tuple(RUNTIMES)

# 16 D-04: what Claude Code's own `--model` flag resolves (real `claude --help`, version
# 2.1.281, lists fable/opus/sonnet; haiku is the fourth Agent-tool alias documented in
# ai-kit-spec-config SKILL.md). Hardcoded because Claude Code has no list-models command --
# these aliases are the only stable short names the CLI itself documents.
CLAUDE_MODEL_ALIASES = RUNTIMES["claude"].native_selectors

# 16 D-04: DATED FALLBACK, not a live list -- these four ids were verified present in
# models.dev's `anthropic` provider on 2026-09-23 (16-RESEARCH.md), one per current family
# (Fable 5.1, Opus 5.5, Sonnet 5, Haiku 4.5). Used only when model-catalog.json has no
# recorded anthropic ids; refresh the ids and the date together when a new generation ships.
CLAUDE_FALLBACK_MODEL_IDS = ("claude-fable-5-1", "claude-opus-5-5", "claude-sonnet-5",
                             "claude-haiku-4-5-20251001")
CLAUDE_FALLBACK_AS_OF = "2026-09-23"

_LEGACY_RUNTIME_NAMES = {"cursor-agent": "cursor", "agent": "cursor"}
_GUARDED_BINARIES = {"agent": "cursor-agent"}
_GENERIC_HOST_MARKERS = ("AI_AGENT",)


def cache_runtimes_path(env: dict) -> str:
    return os.path.join(cache_base(env), "runtimes.json")


def runtime_id(name: str) -> str:
    """Map a legacy binary name onto its runtime id; any other name is unchanged."""
    return _LEGACY_RUNTIME_NAMES.get(name, name)


def normalize_runtime_keys(mapping) -> dict:
    """Copy with keys passed through runtime_id. An id key wins over its legacy alias."""
    if not isinstance(mapping, dict):
        return {}
    merged: dict = {}
    exact: dict = {}
    for key, value in mapping.items():
        rid = runtime_id(key) if isinstance(key, str) else key
        if rid == key:
            exact[rid] = value
        else:
            merged[rid] = value
    merged.update(exact)
    return merged


def resolve_runtime_binary(rid, which_fn=shutil.which, realpath_fn=os.path.realpath):
    """First PATH hit for rid. A guarded name is kept only when its real basename matches."""
    for name in RUNTIMES[rid].binaries:
        found = which_fn(name)
        if not found:
            continue
        expected = _GUARDED_BINARIES.get(name)
        if expected is not None and os.path.basename(realpath_fn(found)) != expected:
            continue
        return found
    return None


def detect_installed_clis(which_fn=shutil.which, realpath_fn=os.path.realpath) -> dict:
    """{runtime id: absolute path or None} for each RUNTIMES row."""
    return {
        rid: resolve_runtime_binary(rid, which_fn=which_fn, realpath_fn=realpath_fn)
        for rid in RUNTIMES
    }


# ids come from RUNTIMES, binaries are a row detail.
_RUNTIME_ENV_SIGNALS = tuple(
    (rid, var) for rid, row in RUNTIMES.items() for var, _label in row.host_signals
)

# Every variable runtime detection reads (D-14), plus host identity markers not tied to a
# specific runtime (AI_AGENT, CLAUDE_CODE_ENTRYPOINT, CLAUDE_CODE_SSE_PORT, CODEX_SANDBOX,
# GROK_AGENT), so a cross-AI child spawned by dispatch never mistakes itself for the host.
# Phase 18 note: cross-ai.mjs's own SCRUB_ENV lacks AI_AGENT and CODEX_VERSION -- this set is
# the authoritative superset.
HOST_SIGNAL_ENV_VARS = frozenset(
    {var for _rid, var in _RUNTIME_ENV_SIGNALS}
    | {var for row in RUNTIMES.values() for var in row.scrub_signals}
    | set(_GENERIC_HOST_MARKERS)
)


def detect_current_runtime(env: Mapping[str, object] | None = None) -> str:
    """Which CLI is hosting THIS process right now.

    Walks `_RUNTIME_ENV_SIGNALS` in the documented fixed order and returns the
    first label whose env var is truthy, or `"unknown"` when none match
    (D-04: never silently omitted). A present-but-empty value (e.g.
    `CLAUDECODE=""`) is treated as falsy/absent — implemented via a plain
    truthiness check (`if env.get(var):`, never a bare `var in env` presence
    check). That is a deliberate contract matching ordinary env-var
    conventions, not an accident of `if env.get(var):`'s default behavior.

    Unlike `detect_installed_clis`/`build_runtimes_snapshot`, this is never
    cached or TTL'd (D-01/D-03): which CLI hosts a process is fixed for that
    process's whole lifetime, cheap to recompute, and never needs
    cross-process persistence. Nested-subprocess env vars accumulate, so
    two signals may both be set; the function never claims to resolve "true
    immediate parent" beyond what the fixed order establishes (D-02/D-03).
    The fixed order is pi > opencode > cursor > codex > claude
    (16 D-01, amended by Phase 20 D-02).

    Signal verification is NOT uniform — never treat all six as equally
    confirmed (AGENTS.md certainty-labeling; 01.2-RESEARCH.md Common Pitfall 2):

    - pi (`PI_CODING_AGENT`): source-inspected-only — confirmed in the
      installed `@earendil-works/pi-coding-agent` package's
      `dist/config.js`, not live-verified from a real pi session (16 D-03;
      live validation is Phase 22).
    - opencode (`OPENCODE`): live-verified (01.2) via a live spawned
      `opencode run` subprocess.
    - cursor (`CURSOR_AGENT`): source-inspected-only — confirmed via the
      installed cursor-agent bundle's own `index.js`, not a live subprocess.
    - codex (`CODEX_THREAD_ID`): observed in real codex session shell
      snapshots under `~/.codex/sessions` (the snapshot preamble exports
      `CODEX_THREAD_ID` from `__CODEX_SNAPSHOT_OVERRIDE_1`; 20 occurrences,
      16 D-02) — not yet live-verified from a codex host (Phase 20,
      EVAL-04).
    - codex (`CODEX_VERSION`): source-inspected-only — confirmed via
      openai/codex's open-source `exec_env.rs`, not a live subprocess.
    - claude (`CLAUDECODE`): live-verified (01.2) via the process's own
      env dump.
    """
    effective: Mapping[str, object] = os.environ if env is None else env
    for label, var in _RUNTIME_ENV_SIGNALS:
        if effective.get(var):
            return label
    return "unknown"


def _list_argv(rid: str) -> tuple[str, ...]:
    """Model-list argv tail for a runtime that enumerates; empty when the row has none."""
    argv = RUNTIMES[rid].list_argv
    if argv is None:
        return ()
    return argv


def _listing_stdout(result) -> str | None:
    """Stdout of an exit-0 listing. A missing or non-zero returncode is a failure."""
    if getattr(result, "returncode", 1) != 0:
        return None
    stdout = getattr(result, "stdout", None)
    return stdout if isinstance(stdout, str) else None


def detect_opencode_models(binary: str, run_fn=subprocess.run, env=None) -> list | None:
    """Runs `<binary> models`; one model id per non-blank line. None on OSError,
    TimeoutExpired, or a non-zero exit. Exit 0 returns the lines, possibly []."""
    try:
        result = _run_opencode(run_fn, [binary, *_list_argv("opencode")], 15, env)
    except (OSError, subprocess.TimeoutExpired):
        return None
    stdout = _listing_stdout(result)
    if stdout is None:
        return None
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def _parse_cursor_models(stdout: str) -> list | None:
    """[] when only the header remains. None when no id parsed and a non-blank line
    is neither the header nor `<id> - <name>` (format not recognized)."""
    models: list[str] = []
    unrecognized = False
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line or line == "Available models":
            continue
        model_id = line.split(" - ", 1)[0].strip() if " - " in line else ""
        if not model_id:
            unrecognized = True
            continue
        models.append(model_id)
    if models:
        return models
    return None if unrecognized else []


def detect_cursor_agent_models(binary: str, run_fn=subprocess.run) -> list | None:
    """Runs `<binary> models` (`<id> - <name>` after an "Available models" header).
    None on OSError, TimeoutExpired, a non-zero exit, or unrecognized output.
    Exit 0 with only the header is []. `cursor-agent models` rewrites privacyCache
    in ~/.cursor/cli-config.json, so a config fingerprint changes."""
    try:
        result = run_fn([binary, *_list_argv("cursor")], capture_output=True, text=True,
                         check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    stdout = _listing_stdout(result)
    if stdout is None:
        return None
    return _parse_cursor_models(stdout)


def _codex_reasoning_modes(item: dict) -> list[str]:
    levels = item.get("supported_reasoning_levels")
    modes: list[str] = []
    if not isinstance(levels, list):
        return modes
    for level in levels:
        if not isinstance(level, dict):
            continue
        effort = level.get("effort")
        if not isinstance(effort, str) or not effort.strip() or effort in modes:
            continue
        modes.append(effort)
    return modes


def _parse_one_codex_debug_model(item, seen: set) -> dict | None:
    if not isinstance(item, dict):
        return None
    slug = item.get("slug")
    if not isinstance(slug, str) or not slug.strip() or item.get("visibility") != "list":
        return None
    if slug in seen:
        return None
    seen.add(slug)
    return {"id": slug, "reasoning_modes": _codex_reasoning_modes(item)}


def parse_codex_debug_models(stdout) -> list | None:
    """Parses the JSON stdout of `codex debug models` into
    `[{"id": <slug>, "reasoning_modes": [<effort>, ...]}, ...]`, one entry
    per listed model, in output order. Built from a real capture
    (codex-cli 0.147.0, resolved via PATH — a volta shim, i.e. a real
    executable, not an alias/function; see
    tests/fixtures/codex_debug_models.json). Only models whose
    `visibility` is exactly the string "list" are returned: the "hide"
    entries (gpt-reserve, codex-auto-review) read as internal/reserved
    slugs, not user-selectable models, and a MISSING `visibility` key
    counts as hidden too. `reasoning_modes` collects each
    `supported_reasoning_levels[].effort` value, in order, without
    duplicates. An unusable envelope returns None and never raises: a non-`str`
    input, invalid JSON, a non-dict top level, or a missing/non-list `models`.
    Inside a valid envelope, a bad item is skipped and an empty or all-hidden
    list is []. The function reads only
    `slug`, `visibility` and `supported_reasoning_levels[].effort` — the
    real payload is ~260KB, almost all of it `model_messages`/
    `base_instructions` prompt text that must never be copied."""
    if not isinstance(stdout, str):
        return None
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("models"), list):
        return None
    parsed = []
    seen: set[str] = set()
    for item in data["models"]:
        record = _parse_one_codex_debug_model(item, seen)
        if record is not None:
            parsed.append(record)
    return parsed


def detect_codex_models(binary: str, run_fn=subprocess.run) -> list | None:
    """Runs `<binary> debug models` and keeps `visibility` "list" slugs. None on
    OSError, TimeoutExpired, a non-zero or missing returncode, or a None parse.
    A valid empty or all-hidden payload is []. Never raises."""
    try:
        result = run_fn([binary, *_list_argv("codex")], capture_output=True, text=True,
                        check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    stdout = _listing_stdout(result)
    if stdout is None:
        return None
    return parse_codex_debug_models(stdout)


def _pi_reasoning_modes(item: dict) -> list[str]:
    level_map = item.get("thinkingLevelMap")
    modes: list[str] = []
    if not isinstance(level_map, dict):
        return modes
    for level, mapped in level_map.items():
        if not isinstance(level, str) or not level.strip() or not mapped:
            continue
        if level in modes:
            continue
        modes.append(level)
    return modes


def _parse_one_pi_model(item, seen: set) -> dict | None:
    if not isinstance(item, dict):
        return None
    bare_id = item.get("id")
    provider = item.get("provider")
    if not isinstance(bare_id, str) or not bare_id.strip():
        return None
    if not isinstance(provider, str) or not provider.strip():
        return None
    full_id = f"{provider}/{bare_id}"
    if full_id in seen:
        return None
    seen.add(full_id)
    input_cap = item.get("input")
    image_input = isinstance(input_cap, list) and "image" in input_cap
    ctx = item.get("contextWindow")
    context_window = ctx if isinstance(ctx, int) and not isinstance(ctx, bool) else None
    return {
        "id": full_id,
        "reasoning_modes": _pi_reasoning_modes(item),
        "image_input": image_input,
        "context_window": context_window,
    }


def parse_pi_models(stdout) -> list | None:
    """Parses pi RPC stdout for `get_available_models` into model records with
    `provider/id` ids. Shape verified live 2026-10-15 (pi 1.2.0); not live-validated
    from a pi host (Phase 22). Scans line-by-line for the first JSON object whose
    `command` is `get_available_models`; returns None when no usable envelope exists
    (non-str input, invalid JSON on every candidate line, `success` not true, missing
    or non-list `data.models`). Inside a valid envelope, skips non-dict models and
    blank id/provider pairs, keeps the first duplicate `provider/id`, and returns []
    when every model is skipped. Never raises."""
    if not isinstance(stdout, str):
        return None
    envelope = None
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and parsed.get("command") == "get_available_models":
            envelope = parsed
            break
    if envelope is None:
        return None
    if envelope.get("success") is not True:
        return None
    data = envelope.get("data")
    if not isinstance(data, dict):
        return None
    models_raw = data.get("models")
    if not isinstance(models_raw, list):
        return None
    parsed_models = []
    seen: set[str] = set()
    for item in models_raw:
        record = _parse_one_pi_model(item, seen)
        if record is not None:
            parsed_models.append(record)
    return parsed_models


def list_runtime_models(rid, binary, run_fn=subprocess.run, env=None) -> list[str] | None:
    """Model ids for one runtime. None means the listing failed (or this runtime has no
    lister: claude's ids come from the catalog, never a listing); [] means it succeeded
    with nothing selectable. `env` locates opencode's private cwd (None: os.environ)."""
    if rid == "opencode":
        return detect_opencode_models(binary, run_fn=run_fn, env=env)
    if rid == "cursor":
        return detect_cursor_agent_models(binary, run_fn=run_fn)
    if rid == "codex":
        listed = detect_codex_models(binary, run_fn=run_fn)
        return [item["id"] for item in listed] if isinstance(listed, list) else None
    if rid == "pi":
        listed = detect_pi_models(binary, run_fn=run_fn)
        return [item["id"] for item in listed] if isinstance(listed, list) else None
    return None


def detect_pi_models(binary: str, run_fn=subprocess.run) -> list | None:
    """Runs pi RPC `get_available_models` (shape verified live 2026-10-15, pi 1.2.0;
    not live-validated from a pi host, Phase 22). A non-zero exit, OSError,
    TimeoutExpired, or parser None -> None; a parsed listing (even empty) -> the list."""
    try:
        result = run_fn(
            [binary, *_list_argv("pi")],
            input=PI_RPC_REQUEST,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if getattr(result, "returncode", 1) != 0:
        return None
    return parse_pi_models(getattr(result, "stdout", None))


def _opencode_verbose_record(obj: dict, header: str) -> bool | None:
    provider_id = obj.get("providerID")
    model_id = obj.get("id")
    if not isinstance(provider_id, str) or not provider_id.strip():
        return None
    if not isinstance(model_id, str) or not model_id.strip():
        return None
    if f"{provider_id}/{model_id}" != header:
        return None
    capabilities = obj.get("capabilities")
    if not isinstance(capabilities, dict):
        return None
    input_cap = capabilities.get("input")
    if not isinstance(input_cap, dict):
        return None
    image = input_cap.get("image")
    return image if isinstance(image, bool) else None


def parse_opencode_verbose_image_input(stdout) -> dict:
    """Parses `opencode models --verbose` output into a dict mapping
    header-line (provider/id format) to a bool (whether image is in the
    input capabilities). The output format is a repeated pattern of:
    header line (e.g., "openai/gpt-5.6-sol"), newline, 2-space-indented
    JSON object, newline.

    Records `result[header] = image` only when the decoded value has all of:
    - providerID and id are both non-blank str
    - f"{providerID}/{id}" == header (addresses review: mismatched header/
      id pairs are skipped, so a shifted or swapped stream can never
      attribute capability data to the wrong model)
    - capabilities is a dict whose input is a dict whose image is a bool

    Stops at the first undecodable JSON block; blocks that fail any check
    are silently skipped and parsing continues. Never raises. Returns {} on
    non-str input or if the first character is { (no header line)."""
    if not isinstance(stdout, str):
        return {}
    result = {}
    decoder = json.JSONDecoder()
    index = 0
    while index < len(stdout):
        # Skip whitespace
        while index < len(stdout) and stdout[index].isspace():
            index += 1
        if index >= len(stdout):
            break
        # Check for headerless JSON (format changed)
        if stdout[index] == "{":
            break
        # Read header line
        line_end = stdout.find("\n", index)
        if line_end == -1:
            break
        header = stdout[index:line_end].strip()
        if not header:
            break
        index = line_end + 1
        # Skip whitespace after header
        while index < len(stdout) and stdout[index].isspace():
            index += 1
        if index >= len(stdout):
            break
        # Decode JSON
        try:
            obj, end_index = decoder.raw_decode(stdout, index)
            index = end_index
        except ValueError:
            # Malformed JSON; stop parsing
            break
        if not isinstance(obj, dict):
            continue
        image = _opencode_verbose_record(obj, header)
        if image is not None:
            result[header] = image
    return result


# 17 D-24: opencode 2.x replaced `models --verbose` with a v2 HTTP API; the image source
# is version-gated so 1.x installs keep the verbose path.
OPENCODE_API_MIN_MAJOR = 2
OPENCODE_API_IMAGE_SOURCE = "opencode-api"
_OPENCODE_PROBE_DEADLINE_S = 15
_OPENCODE_BANNER_MAX_LINES = 50
# The probe talks to its own loopback server only: never through an http_proxy, which would
# receive the Basic-auth password (17-REVIEW C-WR-01).
_LOOPBACK_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
# The default `urlopen_fn` for the loopback probe: never routed through http_proxy.
LOOPBACK_URLOPEN = _LOOPBACK_OPENER.open
# fullmatch on the stripped stdout, so a model listing (e.g. "openai/gpt-5.6-sol") can
# never read as a version string.
_OPENCODE_VERSION_RE = re.compile(r"(?:opencode\s+)?v?(\d+)\.\d+\.\d+\S*")


def opencode_major_version(binary: str, run_fn=subprocess.run, env=None) -> int | None:
    """Returns the opencode major version parsed from `<binary> --version`
    (e.g. "opencode v2.0.29" -> 2), or None on any failure: an OSError or
    subprocess.TimeoutExpired, a non-zero `returncode` (via `getattr(..., 1)`), a
    non-str stdout, or stdout that does not fully match the version pattern. Like
    every detector here, it never raises."""
    try:
        result = _run_opencode(run_fn, [binary, "--version"], 10, env)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if getattr(result, "returncode", 1) != 0:
        return None
    stdout = getattr(result, "stdout", None)
    if not isinstance(stdout, str):
        return None
    match = _OPENCODE_VERSION_RE.fullmatch(stdout.strip())
    return int(match.group(1)) if match else None


def parse_opencode_api_models(payload) -> dict:
    """Parses a decoded `GET /api/model` body (`{"location": ..., "data":
    [Model.Info, ...]}`) into `{"providerID/id": "image" in input}`. Strict shape
    checks (17 T-17-04): items with a blank providerID/id, a non-dict `capabilities`
    or a non-list `capabilities.input` are skipped, never guessed. Returns {} for a
    non-dict payload or a payload whose `data` is not a list. Never raises."""
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    if not isinstance(data, list):
        return {}
    result = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        provider_id = item.get("providerID")
        model_id = item.get("id")
        if not isinstance(provider_id, str) or not provider_id.strip():
            continue
        if not isinstance(model_id, str) or not model_id.strip():
            continue
        capabilities = item.get("capabilities")
        if not isinstance(capabilities, dict):
            continue
        input_caps = capabilities.get("input")
        if not isinstance(input_caps, list):
            continue
        result[f"{provider_id}/{model_id}"] = "image" in input_caps
    return result


def _read_opencode_banner(stream) -> tuple:
    """Reads at most _OPENCODE_BANNER_MAX_LINES lines from `stream` (the probe
    server's stdout) and returns (port, token), either None when not found. Stops on
    EOF ("") or once both are found."""
    port = None
    token = None
    for _ in range(_OPENCODE_BANNER_MAX_LINES):
        line = stream.readline()
        if line == "":
            break
        if port is None:
            port_match = re.search(r"server listening on http://127\.0\.0\.1:(\d+)", line)
            if port_match:
                port = port_match.group(1)
        if token is None and line.startswith("server password "):
            token = line[len("server password "):].strip()
        if port is not None and token is not None:
            break
    return port, token


# Both spellings opencode has used for the project-config opt-out (NF-2).
_OPENCODE_PROJECT_CONFIG_OFF = ("OPENCODE_DISABLE_PROJECT_CONFIG",
                                "OPENCODE_CONFIG_PROJECT_DISABLE")
# A caller's server password suppresses the one-time password line (C-WR-02, NF-3).
_OPENCODE_PASSWORD_VARS = frozenset({"OPENCODE_SERVER_PASSWORD", "OPENCODE_PASSWORD"})
_PRIVATE_DIR_PREFIX = "ai-kit-opencode-probe-"


def _probe_env() -> dict:
    """The env of every opencode subprocess: never project config from the cwd or its
    ancestors (a planted opencode.json could run MCP commands, C-CR-01) under either
    opt-out name, overriding any inherited value, and never a caller's server password."""
    env = {k: v for k, v in os.environ.items() if k not in _OPENCODE_PASSWORD_VARS}
    env.update(dict.fromkeys(_OPENCODE_PROJECT_CONFIG_OFF, "1"))
    return env


def _private_dir(env=None) -> str:
    """A fresh 0700 dir under ai-kit's user-owned cache, so no ancestor is a shared,
    world-writable temp root another user could plant opencode.json in (NF-2). tempfile
    is only the fallback, also when the cache base is relative (no HOME) and would land
    in the caller's cwd. `env` is the caller's env (None: os.environ)."""
    base = cache_base(dict(os.environ if env is None else env))
    if os.path.isabs(base):
        try:
            os.makedirs(base, mode=0o700, exist_ok=True)
            return tempfile.mkdtemp(prefix=_PRIVATE_DIR_PREFIX, dir=base)
        except OSError:
            pass
    return tempfile.mkdtemp(prefix=_PRIVATE_DIR_PREFIX)


@contextlib.contextmanager
def _opencode_private_dir(env=None):
    """The private cwd of one opencode subprocess, removed afterwards: opencode loads
    opencode.json from its cwd and every ancestor (NF-1)."""
    path = _private_dir(env)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _run_opencode(run_fn, argv: list, timeout: int, env=None):
    """`run_fn(argv, ...)` from a private cwd with `_probe_env()` -- the one path every
    non-server opencode subprocess takes (NF-1)."""
    with _opencode_private_dir(env) as cwd:
        return run_fn(argv, capture_output=True, text=True, check=False, timeout=timeout,
                      cwd=cwd, env=_probe_env())


def _signal_server(proc, sig) -> None:
    """Signals the probe server's whole process group (it runs in its own session), so a
    launcher shim or an MCP child cannot outlive it (C-WR-03); plain terminate/kill where
    process groups do not exist."""
    with contextlib.suppress(OSError):
        killpg = getattr(os, "killpg", None)
        pid = getattr(proc, "pid", None)
        if killpg is not None and isinstance(pid, int):
            killpg(pid, sig)
        elif sig == signal.SIGTERM:
            proc.terminate()
        else:
            proc.kill()


_SIGKILL = getattr(signal, "SIGKILL", signal.SIGTERM)


@contextlib.contextmanager
def _sigterm_unwinds():
    """While the probe runs, SIGTERM raises SystemExit so the `finally` below still stops
    the server when a caller times this process out with SIGTERM (B-WR-05)."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return

    def _raise(signum, _frame):
        raise SystemExit(128 + signum)

    previous = signal.signal(signal.SIGTERM, _raise)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


# _stop_server's worst case; catalog_adapter's SIGTERM grace must outlast it (B-WR-05).
_STOP_TERM_WAIT_S = 5
_STOP_KILL_WAIT_S = 2  # SIGKILL cannot be ignored: only reaping is left


def _stop_server(proc) -> None:
    _signal_server(proc, signal.SIGTERM)
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=_STOP_TERM_WAIT_S)
    _signal_server(proc, _SIGKILL)  # stragglers in the group; ESRCH when none is left
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=_STOP_KILL_WAIT_S)
    with contextlib.suppress(OSError, AttributeError):
        proc.stdout.close()


def probe_opencode_api_image_input(binary: str,
                                   popen_fn: Callable[..., Any] = subprocess.Popen,
                                   urlopen_fn: Callable[..., Any] = LOOPBACK_URLOPEN,
                                   env=None) -> dict:
    """Starts a private `opencode serve --hostname 127.0.0.1 --port 0`, reads the
    printed loopback port and one-time password from its stdout, and calls
    `GET http://127.0.0.1:<port>/api/model` with HTTP basic auth `opencode:<password>`
    (17 D-24/D-32). Returns `{"providerID/id": bool}` via
    `parse_opencode_api_models`; any failure returns {}.

    The server runs in its own session from `_opencode_private_dir()` with
    `_probe_env()`: opencode loads opencode.json from its cwd and every ancestor, and can
    execute MCP commands declared there. Only the process
    group this function started is ever signalled -- a user's long-running
    `opencode serve --service` is never touched. The request bypasses proxies. The
    password stays in a local variable and never enters a return value, an exception
    message or any output (17 T-17-01). A daemon threading.Timer kills a silent server
    so `readline` cannot block forever; the `finally` block always stops the server
    group (SIGTERM -> wait -> SIGKILL). opencode writes its own state (db, log) in its
    XDG data dir, never config. opencode 1.x must not reach this (see
    opencode_image_input_with_source)."""
    with _opencode_private_dir(env) as probe_dir, _sigterm_unwinds():
        return _probe_from(binary, probe_dir, popen_fn, urlopen_fn)


def _probe_from(binary, probe_dir, popen_fn, urlopen_fn) -> dict:
    try:
        proc = popen_fn([binary, "serve", "--hostname", "127.0.0.1", "--port", "0"],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                        cwd=probe_dir, env=_probe_env(), start_new_session=True)
    except OSError:
        return {}
    timer = threading.Timer(_OPENCODE_PROBE_DEADLINE_S, _signal_server, (proc, _SIGKILL))
    timer.daemon = True
    try:
        timer.start()
        port, token = _read_opencode_banner(proc.stdout)
        if port is None or token is None:
            return {}
        request = urllib.request.Request(f"http://127.0.0.1:{port}/api/model")
        # Unredirected: a redirect never carries the password to another host.
        request.add_unredirected_header(
            "Authorization", "Basic " + base64.b64encode(f"opencode:{token}".encode()).decode())
        with urlopen_fn(request, timeout=10) as response:
            body = response.read()
        return parse_opencode_api_models(json.loads(body))
    except (OSError, subprocess.TimeoutExpired, urllib.error.URLError,
            http.client.HTTPException, ValueError):
        return {}
    finally:
        timer.cancel()
        _stop_server(proc)


def opencode_image_input_with_source(binary: str, run_fn=subprocess.run,
                                     popen_fn: Callable[..., Any] = subprocess.Popen,
                                     urlopen_fn: Callable[..., Any] = LOOPBACK_URLOPEN,
                                     env=None) -> tuple:
    """Version-gated image-capability detection for opencode. Returns
    `(map, source)` where source is OPENCODE_API_IMAGE_SOURCE ("opencode-api", the
    v2 `GET /api/model` probe) on opencode >= 2, or "opencode" (the
    `opencode models --verbose` parser) on 1.x. A `--version` output that does not
    fully match the version pattern counts as unknown and takes the 1.x verbose
    path, unchanged. The probe is called by its module-level name so tests can patch
    it."""
    major = opencode_major_version(binary, run_fn=run_fn, env=env)
    if major is not None and major >= OPENCODE_API_MIN_MAJOR:
        return probe_opencode_api_image_input(binary, popen_fn=popen_fn,
                                              urlopen_fn=urlopen_fn, env=env), \
            OPENCODE_API_IMAGE_SOURCE
    return detect_opencode_verbose_image_input(binary, run_fn=run_fn, env=env), "opencode"


def detect_opencode_verbose_image_input(binary: str, run_fn=subprocess.run, env=None) -> dict:
    """Runs `<binary> models --verbose` and parses the output via
    `parse_opencode_verbose_image_input`, returning a dict mapping model
    id/header to a bool. A non-zero exit is a FAILURE, not a success with
    stale/partial output: the result's `returncode` must be exactly 0; a
    `run_fn` stub returning None or an object without a `returncode`
    attribute yields {}. Like every parser, any failure (OSError,
    subprocess.TimeoutExpired, invalid JSON, unexpected shape) degrades to
    {} and never raises."""
    try:
        result = _run_opencode(run_fn, [binary, "models", "--verbose"], 15, env)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if getattr(result, "returncode", 1) != 0:
        return {}
    return parse_opencode_verbose_image_input(getattr(result, "stdout", None))


def group_models_by_family(models: list) -> dict:
    """Collapses tier/effort/mode variants of the same base model into one
    group, e.g. ["claude-opus-5-high", "claude-opus-5-high-fast",
    "claude-opus-5-low"] -> {"claude-opus-5": [...three ids...]}. Strips
    only a TRAILING run of tokens from `_MODEL_TIER_SUFFIXES` (hyphen-
    joined) off the end of each id — an id with no such trailing run
    becomes its own family unchanged (e.g. "auto", "composer-2.5"). This
    is a best-effort heuristic over a live-fetched, presumably-current
    catalog — it does not know which family is "newest" or "best" for
    any purpose; that judgment belongs to whoever (or whatever, e.g. a
    wizard doing live research on an unfamiliar name) is choosing among
    the returned families, not to this function. Preserves each model's
    original relative order within its group and preserves the order
    families are first seen in `models`."""
    groups = {}
    for model in models:
        parts = model.split("-")
        cut = len(parts)
        while cut > 1 and parts[cut - 1] in _MODEL_TIER_SUFFIXES:
            cut -= 1
        family = "-".join(parts[:cut]) or model
        groups.setdefault(family, []).append(model)
    return groups


def runtimes_schema_is_current(data) -> bool:
    """16 D-12: True only when `data` is a dict whose `schema_version` is a non-bool int
    >= RUNTIMES_SCHEMA_VERSION. Everything else (None, non-dict, missing key, a bool,
    a string, an older version) is False -- a missing or older version counts as stale
    whatever the TTL says. Never raises, never mutates its input."""
    if not isinstance(data, dict):
        return False
    version = data.get("schema_version")
    return isinstance(version, int) and not isinstance(version, bool) \
        and version >= RUNTIMES_SCHEMA_VERSION


def _catalog_meta(raw) -> dict:
    """Copy of a catalog `_meta` dict, or {}. Never raises."""
    if not isinstance(raw, dict):
        return {}
    meta = raw.get("_meta")
    return dict(meta) if isinstance(meta, dict) else {}


def claude_runtime_fields(catalog_raw) -> dict:
    """16 D-04 hybrid claude model sourcing: `aliases` is what Claude Code's `--model`
    resolves (see CLAUDE_MODEL_ALIASES); `models` holds full ids taken from
    model-catalog.json's recorded `anthropic_model_ids` when available
    (`models_source: "catalog"`, plus `models_as_of` when the record carries a date), or the
    dated in-code fallback otherwise (`models_source: "dated-fallback"`). Confidence labeling
    per 16 D-04: the fallback is visibly labeled as dated, never presented as a live list.
    Nothing is executed here -- claude has no list-models command, and 16 D-07 forbids
    running the alias-wrapped binary (16 D-07). Never raises: any malformed catalog shape
    (None, non-dict `_meta`, non-list or junk-filled `anthropic_model_ids`) degrades to the
    dated fallback or a filtered subset, never an exception. Aliases stay OUT of `models` so
    catalog discovery (which walks every `models` array) never tries to match a bare alias
    against models.dev or mint a bogus `anthropic/opus`-style key."""
    meta = _catalog_meta(catalog_raw)
    raw_ids = meta.get("anthropic_model_ids")
    ids: list = []
    if isinstance(raw_ids, list):
        seen = set()
        for item in raw_ids:
            if not isinstance(item, str) or not item.strip() or item in seen:
                continue
            seen.add(item)
            ids.append(item)
    if ids:
        fields = {"aliases": list(CLAUDE_MODEL_ALIASES), "models": ids,
                  "models_source": "catalog"}
        as_of = meta.get("anthropic_model_ids_as_of")
        if isinstance(as_of, str) and as_of.strip():
            fields["models_as_of"] = as_of
        return fields
    return {"aliases": list(CLAUDE_MODEL_ALIASES), "models": list(CLAUDE_FALLBACK_MODEL_IDS),
            "models_source": "dated-fallback", "models_as_of": CLAUDE_FALLBACK_AS_OF}


def _snapshot_node(which_fn) -> dict:
    """Display-only node presence. Dispatch resolves node live (D-13)."""
    path = which_fn("node")
    record = {"installed": bool(path)}
    if path:
        record["path"] = path
    return record


def _record_listed_models(entry: dict, models) -> None:
    """Successful listings include []. None leaves `models` absent (the listing failed)."""
    if isinstance(models, list):
        entry["models"] = models


def _record_codex_listing(entry: dict, listed) -> None:
    """Record codex ids and reasoning modes when the listing succeeded, [] included."""
    if not isinstance(listed, list):
        return
    entry["models"] = [item["id"] for item in listed]
    entry["reasoning_modes"] = {
        item["id"]: item["reasoning_modes"] for item in listed if item["reasoning_modes"]
    }


class OpencodeSeams(NamedTuple):
    """How the opencode 2.x image probe spawns, and the env whose cache holds every opencode
    subprocess's private cwd (None: os.environ)."""
    popen_fn: Callable[..., Any] = subprocess.Popen
    urlopen_fn: Callable[..., Any] = LOOPBACK_URLOPEN
    env: Mapping[str, str] | None = None


_DEFAULT_OPENCODE_SEAMS = OpencodeSeams()


def build_runtimes_snapshot(which_fn=shutil.which, run_fn=subprocess.run, catalog_fn=None,
                            opencode: OpencodeSeams = _DEFAULT_OPENCODE_SEAMS) -> dict:
    """{"schema_version": RUNTIMES_SCHEMA_VERSION, "clis": {name: {"installed": bool,
    "path"?: str, "models"?: [str], "reasoning_modes"?: {model_id: [effort, ...]},
    "aliases"?: [str], "models_source"?: str, "models_as_of"?: str, "image_input"?: {id: bool},
    "image_input_source"?: str, "image_input_probe"?: "failed"}}}.
    `models` is set only when a listing succeeded, an empty list included, so a missing
    key means the listing failed (opencode, cursor, codex, pi); claude's models come from
    the 16 D-04 hybrid (aliases + full ids); `reasoning_modes` maps each enumerated model id
    to CLI-reported effort/thinking levels (codex/pi), only for ids with a non-empty list;
    `image_input` (pi/opencode) maps model id to bool. `catalog_fn` (claude only) is optional
    zero-argument callable returning the parsed model-catalog.json or None -- injected rather
    than imported so the function stays pure and tests stay hermetic; it is called ONLY when
    claude is installed (claude is never executed, 16 D-07). Pure function -- the caller
    (this module's CLI entrypoint) decides whether/where to persist this via
    cache_write_json. `opencode` reaches the opencode 2.x probe, so a caller that fakes
    `run_fn` can fake the private server too, and names the env for the private cwd."""
    installed = detect_installed_clis(which_fn=which_fn)
    snapshot = {"schema_version": RUNTIMES_SCHEMA_VERSION, "clis": {}}
    for cli, binpath in installed.items():
        if not binpath:
            snapshot["clis"][cli] = {"installed": False}
            continue
        entry = {"installed": True, "path": binpath}
        if cli == "opencode":
            _record_listed_models(
                entry, detect_opencode_models(binpath, run_fn=run_fn, env=opencode.env))
            image_input_map, image_input_source = opencode_image_input_with_source(
                binpath, run_fn, opencode.popen_fn, opencode.urlopen_fn, opencode.env)
            if image_input_map:
                entry["image_input"] = image_input_map
                entry["image_input_source"] = image_input_source
            elif image_input_source == OPENCODE_API_IMAGE_SOURCE:
                # A failed 2.x probe is a recorded gap, never silently "no data" (D-24).
                entry["image_input_probe"] = "failed"
        elif cli == "cursor":
            _record_listed_models(entry, detect_cursor_agent_models(binpath, run_fn=run_fn))
        elif cli == "codex":
            _record_codex_listing(entry, detect_codex_models(binpath, run_fn=run_fn))
        elif cli == "pi":
            pi_models = detect_pi_models(binpath, run_fn=run_fn)
            if pi_models is not None:
                entry["models"] = [m["id"] for m in pi_models]
                entry["reasoning_modes"] = {
                    m["id"]: m["reasoning_modes"]
                    for m in pi_models if m["reasoning_modes"]
                }
                entry["image_input"] = {m["id"]: m["image_input"] for m in pi_models}
        elif cli == "claude":
            # 16 D-04: hybrid alias + catalog-id sourcing; never calls run_fn (claude is
            # never executed) and never calls catalog_fn unless claude is installed (the
            # `if not binpath` branch above already continued first).
            entry.update(claude_runtime_fields(catalog_fn() if catalog_fn is not None else None))
        snapshot["clis"][cli] = entry
    snapshot["node"] = _snapshot_node(which_fn)
    return snapshot


def claude_runtime_is_current(runtimes_data, catalog_fn=None) -> bool:
    """16 D-04/D-12 freshness edge (review cycle 1): runtimes.json's claude ids are DERIVED
    from model-catalog.json's `_meta`, so the catalog is an input of the runtimes cache -- a
    catalog change to the recorded anthropic ids or their as-of date makes the cached claude
    portion stale even while the file's TTL and schema are still fresh. Returns True only
    when the stored `clis.claude` entry (installed) matches what
    `claude_runtime_fields(catalog_fn())` yields for `aliases`/`models`/`models_source`/
    `models_as_of`. An unchanged catalog is always current -- including "no recorded ids" vs
    a stored dated fallback -- so the edge never loops. Everything the TTL and schema checks
    already own (a non-dict runtimes payload, a missing/uninstalled claude entry) is True
    without ever calling `catalog_fn`; never raises."""
    if not isinstance(runtimes_data, dict):
        return True
    clis = runtimes_data.get("clis")
    if not isinstance(clis, dict):
        return True
    stored = clis.get("claude")
    if not isinstance(stored, dict) or not stored.get("installed"):
        return True
    expected = claude_runtime_fields(catalog_fn() if catalog_fn is not None else None)
    return all(stored.get(k) == expected.get(k)
               for k in ("aliases", "models", "models_source", "models_as_of"))


def detect_tool_availability(which_fn=shutil.which) -> dict:
    """Deterministic presence check for the token-efficient tooling AGENTS-TOOLING.md
    recommends. codegraph is included here (binary presence only, Tier 1 of the two-tier
    check design §9 established) -- MCP registration per-client is a separate concern,
    see check_codegraph_mcp_usable below."""
    return {name: which_fn(name) is not None
            for name in ("rg", "sd", "bat", "eza", "fd", "codegraph")}


def resolve_agents_tooling_path(env=None) -> str | None:
    """Machine-level file, not project-level -- never hardcode one user's absolute path.
    AGENTS_TOOLING_PATH env override wins IF it actually exists on disk; else the conventional
    ~/.agents/AGENTS-TOOLING.md location if it exists; else None (the caller omits tooling
    guidance entirely, same never-guess principle as the codegraph MCP check below). The
    override is validated, not trusted blindly -- a stale/misconfigured env var must never put
    an unverified path into a dispatch prompt."""
    env = env if env is not None else os.environ
    override = env.get("AGENTS_TOOLING_PATH")
    if override:
        return override if os.path.isfile(override) else None
    candidate = os.path.join(env.get("HOME", ""), ".agents", "AGENTS-TOOLING.md")
    return candidate if os.path.isfile(candidate) else None


# Confirmed live, 2026-08-30, against each installed CLI's own --help AND real invocations
# (`claude mcp list`, `codex mcp list`, `cursor-agent mcp list`, `opencode mcp list` all ran
# clean, exit 0, on this machine). grok is deliberately absent -- confirmed unsupported, never
# attempt a lookup for it.
#
# claude/codex: `mcp get <name>` is the PRIMARY check where it exists -- direct per-name lookup,
#   deterministic exit code (0 = registered, nonzero = "No MCP server named ..."). `mcp list`
#   is a FALLBACK for these two as well: `get`'s nonzero exit means "not registered" in the
#   common case, but could also mean something else went wrong with the `get` invocation itself
#   (a CLI bug, an auth hiccup) -- cross-checking via `list` before concluding "not registered"
#   costs one extra subprocess call only in the nonzero-exit case, and avoids a false negative
#   from trusting a single command's exit code alone.
# cursor-agent/opencode: no `get` subcommand exists (confirmed via --help) -- `mcp list` is the
#   ONLY check, not a fallback.
# All `mcp list` parsing looks for a line whose name token (text before the first ':') is
# exactly "codegraph"; every observed list format uses that "name: ..." convention.
#
# HEALTH, not just presence: confirmed live that a registered server can be currently
# disconnected -- `claude mcp list` showed `plugin:playwright:playwright: ... - ✘ Failed to
# connect — CONNECTION_CLOSED`, moments before `claude mcp get plugin:playwright:playwright`
# printed `Status: ✔ Connected` for that same server (connection state visibly fluctuates
# between calls). Registered-but-unhealthy must be treated the same as not-registered for the
# purpose this check serves -- telling a subagent to use a currently-broken MCP tool wastes a
# dispatch on a guaranteed failure. Both `get` and `list` output include a `Status:`/inline
# health indicator; look for an explicit failure signal in the relevant text before declaring
# healthy, never assume health from presence alone.
_SUPPORTED_CODEGRAPH_CLIENTS = frozenset(
    rid for rid, row in RUNTIMES.items() if row.mcp_list
)

_MCP_GET_COMMANDS = {
    "claude": ("claude", "mcp", "get", "codegraph"),
    "codex": ("codex", "mcp", "get", "codegraph"),
}
_MCP_LIST_COMMANDS = {
    rid: (row.binaries[0], "mcp", "list")
    for rid, row in RUNTIMES.items() if row.mcp_list
}

# Confirmed live in claude's own output ("✔ Connected" / "✘ Failed to connect — ..."); codex/
# cursor-agent/opencode not yet observed with a real failing entry (nothing was registered to
# test against during this plan's own session) -- Task 3 Step 5's live smoke test must confirm
# these same signals appear (or find and add the real ones) for whichever of those three CLIs
# it tests against an actually-unhealthy server.
_UNHEALTHY_SIGNALS = ("✘", "failed to connect", "not connected")


def _text_is_healthy(text: str) -> bool:
    lowered = text.lower()
    return not any(marker.lower() in lowered for marker in _UNHEALTHY_SIGNALS)


CODEGRAPH_PROBE_TIMEOUT_SECONDS = 15


class CodegraphProbe(NamedTuple):
    registered: bool | None
    healthy: bool | None
    install_command: str | None
    detail: str


def codegraph_install_command(cli: str) -> str:
    return f"codegraph install --target={runtime_id(cli)} --location=global --yes --init"


def _probe_codegraph_from_get(cli: str, result, hint: str) -> CodegraphProbe | None:
    if result.returncode != 0:
        return None
    healthy = _text_is_healthy(result.stdout)
    if cli == "codex" and healthy:
        # A-WR-10/RUN-11: registered, but codex exposes no health -- unknown, never True.
        return CodegraphProbe(True, None, None, "registered; codex does not expose health")
    detail = result.stdout.strip() or ("healthy" if healthy else "unhealthy")
    return CodegraphProbe(True, healthy, None if healthy else hint, detail)


def _probe_codegraph_from_list(stdout: str, hint: str) -> CodegraphProbe:
    for line in stdout.splitlines():
        name = line.split(":", 1)[0].strip()
        if name != "codegraph":
            continue
        healthy = _text_is_healthy(line)
        return CodegraphProbe(True, healthy, None if healthy else hint, line.strip())
    return CodegraphProbe(False, False, hint, "codegraph not listed")


def probe_codegraph(cli: str, run_fn=subprocess.run,
                    timeout: int = CODEGRAPH_PROBE_TIMEOUT_SECONDS) -> CodegraphProbe:
    """Report-only codegraph MCP probe for one CLI. Never installs or registers anything --
    when the server is missing or unhealthy, ``install_command`` carries the suggested command
    for the user (or tools-installer) to run. Timeout/OSError yields unknown registered/healthy."""
    cli = runtime_id(cli)
    if cli not in _SUPPORTED_CODEGRAPH_CLIENTS:
        return CodegraphProbe(
            False, False, None, f"codegraph MCP is not supported for client {cli!r}")
    hint = codegraph_install_command(cli)
    try:
        get_argv = _MCP_GET_COMMANDS.get(cli)
        if get_argv is not None:
            result = run_fn(
                get_argv, capture_output=True, text=True, check=False, timeout=timeout)
            from_get = _probe_codegraph_from_get(cli, result, hint)
            if from_get is not None:
                return from_get
        list_result = run_fn(
            _MCP_LIST_COMMANDS[cli], capture_output=True, text=True, check=False, timeout=timeout)
        if list_result.returncode != 0:
            # A failed list proves nothing about registration (A-IN-05): unknown, no hint.
            return CodegraphProbe(None, None, None,
                                  f"mcp list failed (exit {list_result.returncode})")
        return _probe_codegraph_from_list(list_result.stdout, hint)
    except subprocess.TimeoutExpired:
        return CodegraphProbe(None, None, None, "probe timed out")
    except OSError as exc:
        return CodegraphProbe(None, None, None, str(exc))


def check_codegraph_mcp_usable(cli: str, run_fn=subprocess.run) -> bool:
    """True when ``probe_codegraph`` reports codegraph registered and not known unhealthy --
    health may be unknown (codex exposes none), so this never claims "healthy". The execute
    adapters' index step still requires ``healthy is True`` (D-20)."""
    probe = probe_codegraph(runtime_id(cli), run_fn)
    return probe.registered is True and probe.healthy is not False


# The two multi-provider CLIs with their own per-model catalog (a single-vendor CLI's
# list - codex's enumerated slugs included - only ever serves that one vendor's models, so
# it can never be a *target* alternative for another CLI's model here; only these two
# multi-provider CLIs can).
_CODEGRAPH_CAPABLE_MULTI_PROVIDER_CLIS = tuple(
    rid for rid, row in RUNTIMES.items() if row.multi_provider
)


def find_codegraph_alternative(cli: str, model: str, runtimes_snapshot: dict) -> str | None:
    """Best-effort only (design spec §8, §14): when `cli` has no codegraph/MCP support (not in
    _SUPPORTED_CODEGRAPH_CLIENTS) but a substring match suggests the SAME base model is also
    reachable through a codegraph-capable CLI's own model catalog, return that CLI's name --
    informational only, never a hard filter. Model-id naming conventions differ across CLIs
    (e.g. "grok-4.6" vs. "cursor-grok-4.6-high") so this is a substring heuristic, not a
    guarantee; a missed match degrades silently to None, never a false claim."""
    cli = runtime_id(cli)
    clis = normalize_runtime_keys(
        runtimes_snapshot.get("clis") if isinstance(runtimes_snapshot, dict) else None
    )
    if cli in _SUPPORTED_CODEGRAPH_CLIENTS:
        return None
    needle = model.lower()
    for candidate_cli in _CODEGRAPH_CAPABLE_MULTI_PROVIDER_CLIS:
        entry = clis.get(candidate_cli, {})
        if not entry.get("installed"):
            continue
        for candidate_model in entry.get("models", []):
            if needle in candidate_model.lower():
                return candidate_cli
    return None


CODEGRAPH_INDEX_TIMEOUT_SECONDS = 15  # agreed minimum, safety margin over the typical <5s runtime


def run_codegraph_index(target_dir: str, run_fn=subprocess.run) -> bool:
    """Run ``codegraph sync`` then ``codegraph init`` on failure, scoped to ``target_dir``.
    Only invoked after a healthy probe; returns True only when sync or init exits 0."""
    run_kw = {
        "cwd": target_dir,
        "capture_output": True,
        "text": True,
        "timeout": CODEGRAPH_INDEX_TIMEOUT_SECONDS,
    }
    try:
        sync = run_fn(["codegraph", "sync"], check=False, **run_kw)
        if sync.returncode == 0:
            return True
        init = run_fn(["codegraph", "init"], check=False, **run_kw)
        return init.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False
