"""Declarative Config Doctor engine — check registry, path resolution, catalog.

Stdlib-only. Imports nothing from textual, setup.py, wizard_app.py, or any
skills/* package. This is the core engine Wave 2 (more rows) and Wave 3
(apply writers) extend without restructuring.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable
from typing import NamedTuple, cast

import config_doctor_appliers
import config_doctor_readers

UNKNOWN = config_doctor_readers.UNKNOWN

CONFIG_STATE_ABSENT = "absent"
CONFIG_STATE_OK = "ok"
CONFIG_STATE_UNREADABLE = "unreadable"

_READERS = {
    "claude": config_doctor_readers.read_json_checked,
    "cursor": config_doctor_readers.read_json_checked,
    "opencode": config_doctor_readers.read_jsonc_checked,
    "codex": config_doctor_readers.read_toml_checked,
}


class CheckRow(NamedTuple):
    id: str
    runtime: str
    scope: str
    check: str
    read: object
    recommended: object
    confidence: str
    why: str
    source: str
    apply: object = None
    reads_section_file: bool = True
    apply_target: object = None
    security_relevant: bool = False


class ReadContext(NamedTuple):
    """Per-evaluation inputs for a CheckRow.read function.

    data: parsed config dict, or None when the section file is unreadable.
    env: the env mapping build_catalog received.
    runner: subprocess-runner callable, or None to use the default later.
    """

    data: object
    env: object
    runner: object


def resolve_runtime_config_paths(env):
    """Absolute config-file paths for the four known runtimes.

    Precedence is each runtime's own, not ai-kit's installer paths:
    claude honors CLAUDE_CONFIG_DIR; cursor honors Cursor CLI's three-step
    layout (CURSOR_CONFIG_DIR, then XDG_CONFIG_HOME/cursor, then ~/.cursor)
    for cli-config.json; opencode honors OPENCODE_CONFIG_DIR > XDG_CONFIG_HOME
    > ~/.config; codex honors CODEX_HOME.
    """
    home = env.get("HOME", "")
    claude_dir = env.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
    if env.get("CURSOR_CONFIG_DIR"):
        cursor_dir = env["CURSOR_CONFIG_DIR"]
    elif env.get("XDG_CONFIG_HOME"):
        cursor_dir = os.path.join(env["XDG_CONFIG_HOME"], "cursor")
    else:
        cursor_dir = os.path.join(home, ".cursor")
    opencode_dir = env.get("OPENCODE_CONFIG_DIR")
    if opencode_dir:
        opencode_base = opencode_dir
    elif env.get("XDG_CONFIG_HOME"):
        opencode_base = os.path.join(env["XDG_CONFIG_HOME"], "opencode")
    else:
        opencode_base = os.path.join(home, ".config", "opencode")
    codex_dir = env.get("CODEX_HOME") or os.path.join(home, ".codex")
    return {
        "claude": os.path.join(claude_dir, "settings.json"),
        "opencode": os.path.join(opencode_base, "opencode.jsonc"),
        "codex": os.path.join(codex_dir, "config.toml"),
        "cursor": os.path.join(cursor_dir, "cli-config.json"),
    }


def evaluate_row(row, ctx):
    """Evaluate one CheckRow against a ReadContext."""
    value = UNKNOWN if ctx.data is None and row.reads_section_file else row.read(ctx)
    current_display = "unknown" if value is UNKNOWN else str(value)
    return {
        "id": row.id,
        "runtime": row.runtime,
        "scope": row.scope,
        "check": row.check,
        "current_value": value,
        "current_display": current_display,
        "recommended_value": row.recommended,
        "recommended_display": str(row.recommended),
        "confidence": row.confidence,
        "apply_eligible": row.apply is not None,
        "why": row.why,
        "source": row.source,
        "apply_target": row.apply_target,
        "security_relevant": row.security_relevant,
    }


def _row_by_id(row_id):
    for row in CONFIG_DOCTOR_ROWS:
        if row.id == row_id:
            return row
    return None


def apply_row(row_id, ctx, dry):
    """Dispatch one apply by row identity. Never raises.

    Looks up ``row_id`` in CONFIG_DOCTOR_ROWS and invokes that row's own
    ``apply(ctx, row.apply_target, dry)``. Dispatches by row identity via
    ``row.apply``, never by inspecting ``row.runtime``. An unknown id or a
    row with ``apply is None`` returns ``{"ok": False, "reason": "not
    apply-eligible"}`` — never a silent no-op write. Any exception an
    applier raises is converted to ``{"ok": False, "reason": "applier
    error: ..."}`` so an unhandled exception cannot reach ConfigDoctorApp's
    event loop (Textual 8.x swallows those into a graceful shutdown;
    tools/wizard_app.py:129-137).
    """
    row = _row_by_id(row_id)
    if row is None or row.apply is None:
        return {"ok": False, "reason": "not apply-eligible"}
    try:
        apply_fn = cast(Callable[[object, object, bool], dict], row.apply)
        result = apply_fn(ctx, row.apply_target, dry)
    except Exception as exc:
        return {"ok": False, "reason": f"applier error: {exc}"}
    if not isinstance(result, dict):
        return {"ok": False, "reason": f"applier error: non-dict result {result!r}"}
    return result


def _claude_settings_path(ctx):
    return resolve_runtime_config_paths(ctx.env)["claude"]


def _opencode_config_path(ctx):
    return resolve_runtime_config_paths(ctx.env)["opencode"]


def _codex_config_path(ctx):
    return resolve_runtime_config_paths(ctx.env)["codex"]


def _apply_claude_retention(ctx, target, dry):
    """Write cleanupPeriodDays. Categorically refuses target 0.

    The 0-guard is unconditional and independent of apply_target's declared
    value (04-RESEARCH.md Common Pitfall 2). RETURNS a refusal dict, never
    raises — an exception reaching ConfirmApplyScreen's confirm handler is
    a Textual 8.x crash-to-graceful-shutdown path, not a caught refusal
    (tools/wizard_app.py:129-137).
    """
    if target == 0:
        return {
            "ok": False,
            "reason": "refused: cleanupPeriodDays 0 is never writable",
        }
    path = _claude_settings_path(ctx)
    state, parsed = config_doctor_readers.read_json_checked(path)
    data = dict(parsed) if state == CONFIG_STATE_OK and isinstance(parsed, dict) else {}
    before = data.get("cleanupPeriodDays")
    data["cleanupPeriodDays"] = target
    if not dry:
        config_doctor_appliers.atomic_write_json(path, data)
    return {"ok": True, "before": before, "after": target, "current_display": str(target)}


def _apply_claude_sandbox_enabled(ctx, target, dry):
    path = _claude_settings_path(ctx)
    state, parsed = config_doctor_readers.read_json_checked(path)
    data = dict(parsed) if state == CONFIG_STATE_OK and isinstance(parsed, dict) else {}
    if isinstance(data.get("sandbox"), dict):
        data["sandbox"] = dict(data["sandbox"])
    sandbox = data.setdefault("sandbox", {})
    before = sandbox.get("enabled")
    sandbox["enabled"] = target
    if not dry:
        config_doctor_appliers.atomic_write_json(path, data)
    return {
        "ok": True,
        "before": before,
        "after": target,
        "current_display": str(target),
        "literal_resulting_config": data,
    }


def _parse_jsonc_text(text):
    stripped = config_doctor_readers.strip_trailing_commas(
        config_doctor_readers.strip_jsonc_comments(text)
    )
    return json.loads(stripped)


def _apply_opencode_share_mode(ctx, target, dry):
    path = _opencode_config_path(ctx)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    else:
        text = "{\n}\n"
    before = None
    try:
        parsed = _parse_jsonc_text(text)
        if isinstance(parsed, dict):
            before = parsed.get("share")
    except (ValueError, TypeError):
        before = None
    spliced = config_doctor_appliers.set_jsonc_value(text, ("share",), target)
    try:
        _parse_jsonc_text(spliced)
    except (ValueError, TypeError):
        return {
            "ok": False,
            "reason": (
                "refused: spliced JSONC failed self-validation, no write performed"
            ),
        }
    if not dry:
        config_doctor_appliers._atomic_write_text(path, spliced)
    return {
        "ok": True,
        "before": before,
        "after": target,
        "current_display": str(target),
    }


def _toml_table_span(text, table_name):
    header = f"[{table_name}]"
    start = text.find(header)
    if start < 0:
        return None
    body_start = start + len(header)
    nxt = text.find("\n[", body_start)
    end = len(text) if nxt < 0 else nxt
    return start, body_start, end


def _upsert_toml_table_key(text, table_name, key, value):
    """String-level table/key upsert; no stdlib TOML writer exists.

    04-RESEARCH.md Standard Stack: Python has no stdlib TOML writer, so
    Codex config.toml is mutated by splicing the [history] table region
    rather than a parse-mutate-dump round trip that would rewrite every
    other byte.
    """
    dumped = _toml_dump_value(value)
    span = _toml_table_span(text, table_name)
    if span is None:
        suffix = "" if text.endswith("\n") or not text else "\n"
        return f"{text}{suffix}\n[{table_name}]\n{key} = {dumped}\n"
    _start, body_start, end = span
    body = text[body_start:end]
    replaced, count = re.subn(
        rf"(?m)^(\s*{re.escape(key)}\s*=\s*).*$",
        rf"\1{dumped}",
        body,
        count=1,
    )
    if count:
        return text[:body_start] + replaced + text[end:]
    insert = f"\n{key} = {dumped}"
    if body.endswith("\n"):
        insert = f"{key} = {dumped}\n"
        return text[:end] + insert + text[end:]
    return text[:end] + insert + text[end:]


def _toml_dump_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return json.dumps(value)


def _apply_codex_history_persistence(ctx, target, dry):
    path = _codex_config_path(ctx)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    else:
        text = ""
    state, data = config_doctor_readers.read_toml_checked(path)
    before = None
    if state == CONFIG_STATE_OK and isinstance(data, dict):
        history = data.get("history")
        if isinstance(history, dict):
            before = history.get("persistence")
    new_text = _upsert_toml_table_key(text, "history", "persistence", target)
    if not dry:
        ok = config_doctor_appliers.write_toml_region_replace(path, new_text)
        if not ok:
            return {
                "ok": False,
                "reason": "refused: TOML write failed self-validation, no write committed",
            }
    return {
        "ok": True,
        "before": before,
        "after": target,
        "current_display": str(target),
    }


def _nested(ctx, *keys, default=UNKNOWN):
    return config_doctor_readers.get_nested(ctx.data, *keys, default=default)


def read_claude_retention(ctx):
    """cleanupPeriodDays, or Claude Code's documented 30-day default."""
    return _nested(ctx, "cleanupPeriodDays", default=30)


def read_claude_prompt_cache_ttl(ctx):
    """promptCacheTtl — UNKNOWN when absent (billing-mode-dependent default)."""
    return _nested(ctx, "promptCacheTtl", default=UNKNOWN)


def read_claude_subagent_prompt_cache_ttl(ctx):
    """subagentPromptCacheTtl — documented default is always 5 minutes."""
    return _nested(ctx, "subagentPromptCacheTtl", default="5m")


def read_claude_sandbox_enabled(ctx):
    return _nested(ctx, "sandbox", "enabled", default=False)


def read_claude_sandbox_fail_if_unavailable(ctx):
    return _nested(ctx, "sandbox", "failIfUnavailable", default=False)


def read_claude_telemetry(ctx):
    """Process-env CLAUDE_CODE_ENABLE_TELEMETRY only — not settings.json env."""
    env = ctx.env if isinstance(ctx.env, dict) else {}
    return env.get("CLAUDE_CODE_ENABLE_TELEMETRY") or "unset"


def read_opencode_retention(ctx):
    del ctx
    return "not currently configurable"


_OPENCODE_PERMISSION_ACTIONS = (
    ("read", "allow"),
    ("edit", "allow"),
    ("glob", "allow"),
    ("grep", "allow"),
    ("bash", "allow"),
    ("task", "allow"),
    ("skill", "allow"),
    ("lsp", "allow"),
    ("question", "allow"),
    ("webfetch", "allow"),
    ("websearch", "allow"),
    ("external_directory", "ask"),
    ("doom_loop", "ask"),
)


def read_opencode_permissions(ctx):
    """Summarize permission.* vs documented defaults; UNKNOWN if non-dict."""
    permission = _nested(ctx, "permission", default=None)
    if permission is not None and not isinstance(permission, dict):
        return UNKNOWN
    diffs = []
    for action, documented_default in _OPENCODE_PERMISSION_ACTIONS:
        value = _nested(ctx, "permission", action, default=documented_default)
        if value != documented_default:
            diffs.append(f"{action}={value}")
    if not diffs:
        return "all defaults (see Why for the full action set)"
    return ", ".join(diffs)


def read_opencode_share_mode(ctx):
    return _nested(ctx, "share", default="manual")


def read_opencode_model_options(ctx):
    """Walk provider.<id>.models.<model>.options; best-effort repr."""
    provider = _nested(ctx, "provider", default=None)
    if not isinstance(provider, dict):
        return "no per-model options configured"
    found = []
    for provider_id, pdata in provider.items():
        if not isinstance(pdata, dict):
            continue
        models = pdata.get("models")
        if not isinstance(models, dict):
            continue
        for model_id, mdata in models.items():
            if not isinstance(mdata, dict) or "options" not in mdata:
                continue
            found.append(f"{provider_id}/{model_id}: {mdata['options']!r}")
    if not found:
        return "no per-model options configured"
    return "; ".join(found)


def read_codex_sandbox_mode(ctx):
    return _nested(ctx, "sandbox_mode", default=UNKNOWN)


def read_codex_hooks(ctx):
    hooks = _nested(ctx, "features", "hooks", default=UNKNOWN)
    if hooks is not UNKNOWN:
        return hooks
    alias = _nested(ctx, "features", "codex_hooks", default=UNKNOWN)
    if alias is not UNKNOWN:
        return alias
    return False


def read_codex_model_reasoning_effort(ctx):
    model = _nested(ctx, "model", default="unknown")
    effort = _nested(ctx, "model_reasoning_effort", default=UNKNOWN)
    effort_display = "unknown" if effort is UNKNOWN else effort
    return f"model={model}, effort={effort_display}"


def read_codex_history_max_bytes(ctx):
    return _nested(ctx, "history", "max_bytes", default="unset (no cap)")


def read_codex_memories_durations(ctx):
    unused = _nested(ctx, "memories", "max_unused_days", default=30)
    rollout = _nested(ctx, "memories", "max_rollout_age_days", default=30)
    idle = _nested(ctx, "memories", "min_rollout_idle_hours", default=6)
    return (
        f"max_unused_days={unused}, max_rollout_age_days={rollout}, "
        f"min_rollout_idle_hours={idle}"
    )


def read_codex_history_persistence(ctx):
    return _nested(ctx, "history", "persistence", default="save-all")


def read_cursor_permissions(ctx):
    allow = _nested(ctx, "permissions", "allow", default=[])
    deny = _nested(ctx, "permissions", "deny", default=[])
    return f"allow={allow}, deny={deny}"


def read_cursor_approval_mode(ctx):
    return _nested(ctx, "approvalMode", default=UNKNOWN)


def read_cursor_sandbox_cli_config(ctx):
    mode = _nested(ctx, "sandbox", "mode", default=UNKNOWN)
    network = _nested(ctx, "sandbox", "networkAccess", default=UNKNOWN)
    mode_d = "unknown" if mode is UNKNOWN else mode
    net_d = "unknown" if network is UNKNOWN else network
    return f"mode={mode_d}, networkAccess={net_d}"


def read_cursor_sandbox_json(ctx):
    """Read <cursor_dir>/sandbox.json, not cli-config.json.

    This is the one catalog row whose read function performs its own file
    I/O. Common Pitfall 5: cli-config.json's sandbox.mode/networkAccess
    (row 15a) is a DISTINCT mechanism from the separate sandbox.json file
    (row 15b) and must never share a reader. Open Question 1: no official
    doc names a sandbox-policies/ directory; sandbox.json, singular file,
    is the only citable target. A generic per-runtime data blob cannot
    represent this row.
    """
    env = ctx.env if isinstance(ctx.env, dict) else {}
    cursor_path = resolve_runtime_config_paths(env)["cursor"]
    path = os.path.join(os.path.dirname(cursor_path), "sandbox.json")
    state, data = config_doctor_readers.read_json_checked(path)
    if state == CONFIG_STATE_ABSENT:
        return "type=workspace_readwrite"
    if state != CONFIG_STATE_OK or not isinstance(data, dict):
        return UNKNOWN
    stype = config_doctor_readers.get_nested(
        data, "type", default="workspace_readwrite"
    )
    net = config_doctor_readers.get_nested(
        data, "networkPolicy", "default", default="deny"
    )
    return f"type={stype}, networkPolicy.default={net}"


def read_cursor_model_parameters(ctx):
    mp = _nested(ctx, "modelParameters", default=None)
    if mp is not None and not isinstance(mp, dict):
        return UNKNOWN
    if mp is None:
        return "no modelParameters configured"
    return repr(mp)


def read_cursor_local_retention(ctx):
    del ctx
    return UNKNOWN


def read_cursor_cli_telemetry(ctx):
    del ctx
    return UNKNOWN


def read_cursor_attribution(ctx):
    commits = _nested(ctx, "attribution", "attributeCommitsToAgent", default=True)
    prs = _nested(ctx, "attribution", "attributePRsToAgent", default=True)
    return f"attributeCommitsToAgent={commits}, attributePRsToAgent={prs}"


def read_rtk_cursor_integration(ctx):
    env = ctx.env if isinstance(ctx.env, dict) else {}
    search_path = env.get("PATH")
    if not search_path:
        search_path = os.environ.get("PATH")
    rtk_path = shutil.which("rtk", path=search_path)
    if rtk_path is None:
        return "rtk not installed on PATH"
    signal = config_doctor_readers._probe_rtk_cursor_hook(rtk_path, ctx.runner)
    if signal == config_doctor_readers.RTK_SIGNAL_CONFIRMED:
        return "registered"
    if signal == config_doctor_readers.RTK_SIGNAL_NOT_REGISTERED:
        return "not registered"
    return "unreadable (see Why)"


_CODEX_SOURCE = "https://learn.chatgpt.com/docs/config-file/config-reference"
_CURSOR_CONFIG_SOURCE = "https://cursor.com/docs/cli/reference/configuration"


CONFIG_DOCTOR_ROWS = [
    CheckRow(
        id="claude-retention",
        runtime="claude",
        scope="runtime",
        check="Local transcript retention (cleanupPeriodDays)",
        read=read_claude_retention,
        recommended=3650,
        confidence="HIGH",
        why=(
            "Local transcript retention defaults to 30 days; raising it serves "
            "Phase 5's usage-metrics dashboard, which needs longer local history. "
            "cleanupPeriodDays: 0 must NEVER be recommended or applied — it is "
            "now rejected outright by Claude Code v2.1.89 rather than silently "
            "disabling persistence (the prior behavior GitHub #23710 described)."
        ),
        source="https://code.claude.com/docs/en/data-usage",
        apply=_apply_claude_retention,
        apply_target=3650,
    ),
    CheckRow(
        id="claude-prompt-cache-ttl",
        runtime="claude",
        scope="runtime",
        check="Prompt-cache TTL (main conversation, promptCacheTtl)",
        read=read_claude_prompt_cache_ttl,
        recommended='"1h" (only changes anything on the 5-min-default auth modes)',
        confidence="HIGH",
        why=(
            "The true default when promptCacheTtl is absent depends on billing/"
            "auth mode in a way the local file alone cannot reveal: 1h on a "
            "Claude subscription within-plan usage, 5m for API-key / usage-"
            "credits / cloud-provider auth. Absence is therefore unknown, not "
            "a guessed flat default. The setting requires Claude Code v2.1.242+. "
            "Apply: yes, but the reader must report depends on billing mode, "
            "not a flat current value."
        ),
        source="https://code.claude.com/docs/en/prompt-caching",
    ),
    CheckRow(
        id="claude-subagent-prompt-cache-ttl",
        runtime="claude",
        scope="runtime",
        check="Prompt-cache TTL (subagents, subagentPromptCacheTtl)",
        read=read_claude_subagent_prompt_cache_ttl,
        recommended='"1h" if idle-then-resume subagent/workflow usage is common',
        confidence="HIGH",
        why=(
            "subagentPromptCacheTtl defaults to 5 minutes always, even on a "
            "subscription — not billing-dependent. Same source as promptCacheTtl. "
            "Apply: yes."
        ),
        source="https://code.claude.com/docs/en/prompt-caching",
    ),
    CheckRow(
        id="claude-sandbox-enabled",
        runtime="claude",
        scope="runtime",
        check="Sandboxed Bash tool (sandbox.enabled)",
        read=read_claude_sandbox_enabled,
        recommended=True,
        confidence="HIGH",
        why=(
            "OS-level (Seatbelt on macOS, bubblewrap+socat on Linux/WSL2) "
            "filesystem/network isolation. This is security-relevant. "
            "Apply: yes, security-relevant."
        ),
        source="https://code.claude.com/docs/en/sandboxing",
        apply=_apply_claude_sandbox_enabled,
        apply_target=True,
        security_relevant=True,
    ),
    CheckRow(
        id="claude-sandbox-fail-if-unavailable",
        runtime="claude",
        scope="runtime",
        check="Sandbox hard-fail (sandbox.failIfUnavailable)",
        read=read_claude_sandbox_fail_if_unavailable,
        recommended=(
            "true only if sandboxing should be a hard security gate rather than "
            "best-effort — the user's own risk call, not a universal True"
        ),
        confidence="HIGH",
        why=(
            "Default false silently falls back to unsandboxed if deps are "
            "missing. Not a universal True recommendation — analogous framing "
            "to opencode permissions. Apply: yes, security-relevant, user's "
            "own risk call."
        ),
        source="https://code.claude.com/docs/en/sandboxing",
    ),
    CheckRow(
        id="claude-telemetry",
        runtime="claude",
        scope="runtime",
        check="OpenTelemetry export (CLAUDE_CODE_ENABLE_TELEMETRY)",
        read=read_claude_telemetry,
        recommended='"1" (with exporter env vars) for org/self usage-cost visibility',
        confidence="HIGH",
        why=(
            "This is DISTINCT from Anthropic's own default-on operational "
            "metrics/error-reporting stream (DISABLE_TELEMETRY / "
            "DISABLE_ERROR_REPORTING, a different mechanism entirely). This "
            "setting's real provider-conditionality is which API provider is "
            "connected through (off by default on Vertex/Bedrock/Foundry/AWS, "
            "on for direct Claude API), never individual-vs-corporate account "
            "tier. This row's claim is scoped to the process environment value "
            "only — Claude Code's settings.json separately supports its own "
            '"env" block, and a CLAUDE_CODE_ENABLE_TELEMETRY value configured '
            "only there (never exported to the process) is NOT read by this "
            "row. Apply: yes."
        ),
        source="https://code.claude.com/docs/en/data-usage",
        reads_section_file=False,
    ),
    CheckRow(
        id="opencode-retention",
        runtime="opencode",
        scope="runtime",
        check="Session retention",
        read=read_opencode_retention,
        recommended="N/A",
        confidence="HIGH",
        why=(
            "Not currently configurable: GitHub issue #22110 was closed as "
            '"not planned", and the full official config reference documents '
            "every key and has no retention/cache-TTL/cleanup-period key "
            "anywhere. Phrased as not currently configurable, never will never "
            "be configurable — a disposition, not a permanent guarantee. "
            "Apply stays None permanently (there is no setting to ever write), "
            "distinct from rows whose apply=None is merely not yet wired."
        ),
        source="https://opencode.ai/docs/config/",
    ),
    CheckRow(
        id="opencode-permissions",
        runtime="opencode",
        scope="runtime",
        check="permission block (full action set)",
        read=read_opencode_permissions,
        recommended=(
            "lock down per the user's own risk tolerance (ask/deny per action) "
            "— a personal risk-tolerance choice, not one fixed target"
        ),
        confidence="HIGH",
        why=(
            "Full documented action set and defaults: read, edit, glob, grep, "
            "bash, task, skill, lsp, question, webfetch, websearch default "
            'allow; doom_loop and external_directory default ask. A non-dict '
            '"permission" value degrades to unknown rather than a guessed '
            "per-action default. Apply: yes, security-relevant."
        ),
        source="https://opencode.ai/docs/permissions/",
    ),
    CheckRow(
        id="opencode-share-mode",
        runtime="opencode",
        scope="runtime",
        check="share mode",
        read=read_opencode_share_mode,
        recommended='"disabled" for privacy-conscious users',
        confidence="MEDIUM",
        why=(
            "Default is manual. Confidence MEDIUM — carried forward from the "
            "source PRD, not re-fetched this research session. Apply: yes."
        ),
        source="https://opencode.ai/docs/share/",
        apply=_apply_opencode_share_mode,
        apply_target="disabled",
    ),
    CheckRow(
        id="opencode-model-options",
        runtime="opencode",
        scope="model",
        check="Per-model reasoning/verbosity options",
        read=read_opencode_model_options,
        recommended=(
            "reasoningEffort/textVerbosity/reasoningSummary for "
            '"openai"; thinking.budgetTokens for "anthropic" — documented '
            "shape confirmed only for those literal provider ids; a custom "
            "router provider id (this machine's own opencode.jsonc uses "
            '"router-env") is UNVERIFIED to honor these options at all'
        ),
        confidence="LOW",
        why=(
            "Documented JSONC shape is provider.<id>.models.<model>.options."
            "{reasoningEffort, textVerbosity, reasoningSummary} for openai and "
            "options.thinking.{type, budgetTokens} for anthropic. HIGH on that "
            "documented shape, LOW on this machine's own custom-router "
            "applicability: this machine's opencode.jsonc uses provider id "
            '"router-env", which is unverified to honor these options at all '
            "(Assumption A2). Overall confidence is LOW, the honest ceiling "
            "for a reader running against this machine's real file. Apply: "
            "yes for documented provider ids; no (informational) for custom-"
            "router setups until verified."
        ),
        source="https://opencode.ai/docs/models/",
    ),
    CheckRow(
        id="codex-sandbox-mode",
        runtime="codex",
        scope="runtime",
        check="sandbox_mode",
        read=read_codex_sandbox_mode,
        recommended=(
            '"workspace-write" + approval_policy = "on-request" (or the newer '
            "granular object form)"
        ),
        confidence="MEDIUM",
        why=(
            'Enum is "read-only" | "workspace-write" | "danger-full-access". '
            "No documented default; absence is unknown, not a guessed fallback. "
            "approval_policy also supports a newer granular object form "
            "({granular = {sandbox_approval, rules, mcp_elicitations, "
            "request_permissions, skill_approval}}), distinct from a simple "
            "string enum. Apply: yes, security-relevant."
        ),
        source=_CODEX_SOURCE,
    ),
    CheckRow(
        id="codex-hooks",
        runtime="codex",
        scope="runtime",
        check="features.hooks",
        read=read_codex_hooks,
        recommended="N/A — informational only",
        confidence="HIGH",
        why=(
            "Informational only per D-04, matching opencode-retention's "
            "treatment. features.codex_hooks is a documented deprecated alias "
            "the reader must check. Apply stays None permanently (D-04 locks "
            "this, not merely not yet wired)."
        ),
        source=_CODEX_SOURCE,
    ),
    CheckRow(
        id="codex-model-reasoning-effort",
        runtime="codex",
        scope="model",
        check="model_reasoning_effort",
        read=read_codex_model_reasoning_effort,
        recommended=(
            '"high"/"xhigh" for complex/multi-file work — research found no '
            "per-model mapping backed by an official source, so this "
            "recommendation does not vary by which model is active despite the "
            'scope="model" label; the schema supports a real per-model mapping '
            "once one is sourced, without an architecture change"
        ),
        confidence="LOW",
        why=(
            'Enum is "minimal" | "low" | "medium" | "high" | "xhigh" (xhigh '
            "model-dependent, Responses API only). No documented default for "
            "the effort value itself. Confidence LOW is the honest ceiling "
            "(community-sourced default claim only; the enum values themselves "
            "are HIGH). Apply: yes, labeled low-confidence in the UI."
        ),
        source=_CODEX_SOURCE,
    ),
    CheckRow(
        id="codex-history-max-bytes",
        runtime="codex",
        scope="runtime",
        check="history.max_bytes",
        read=read_codex_history_max_bytes,
        recommended="set a cap if disk usage is a concern",
        confidence="HIGH",
        why=(
            "Caps history.jsonl by byte size (drops oldest entries), NOT a "
            "duration control. Apply: yes."
        ),
        source=_CODEX_SOURCE,
    ),
    CheckRow(
        id="codex-memories-durations",
        runtime="codex",
        scope="runtime",
        check="[memories] duration settings",
        read=read_codex_memories_durations,
        recommended="N/A — informational only unless [memories] is confirmed active",
        confidence="HIGH",
        why=(
            "These govern a SEPARATE memory-consolidation feature, NOT "
            "session-history retention, despite the duration-adjacent naming. "
            'GitHub issue #6015 ("Codex retains every conversation '
            'indefinitely") confirms Codex has no actual history-cleanup '
            "window. Apply: None."
        ),
        source="https://github.com/openai/codex/issues/6015",
    ),
    CheckRow(
        id="codex-history-persistence",
        runtime="codex",
        scope="runtime",
        check="history.persistence",
        read=read_codex_history_persistence,
        recommended=(
            '"none" only if the user wants it (privacy trade-off) — never '
            "auto-recommended"
        ),
        confidence="HIGH",
        why=(
            "Default is save-all. This is opt-in only, never defaulted to "
            '"recommended: apply". Apply: yes, opt-in only.'
        ),
        source=_CODEX_SOURCE,
        apply=_apply_codex_history_persistence,
        apply_target="none",
    ),
    CheckRow(
        id="cursor-permissions",
        runtime="cursor",
        scope="runtime",
        check="permissions.allow / permissions.deny",
        read=read_cursor_permissions,
        recommended="lock down per risk tolerance, same framing as opencode row 6",
        confidence="HIGH",
        why=(
            "Entries are typed exact-match strings (Shell(cmd), Read(glob), "
            "Write(glob), WebFetch(domain), Mcp(server:tool)); deny takes "
            "precedence over allow. Apply: yes, security-relevant."
        ),
        source="https://cursor.com/docs/cli/reference/permissions",
    ),
    CheckRow(
        id="cursor-approval-mode",
        runtime="cursor",
        scope="runtime",
        check="approvalMode",
        read=read_cursor_approval_mode,
        recommended='"allowlist" (the tightest documented mode) if not already set',
        confidence="HIGH",
        why=(
            "No documented default found; absence is unknown. Apply: yes "
            "(mostly a confirmation on this machine)."
        ),
        source=_CURSOR_CONFIG_SOURCE,
    ),
    CheckRow(
        id="cursor-sandbox-cli-config",
        runtime="cursor",
        scope="runtime",
        check="cli-config.json sandbox.mode / sandbox.networkAccess",
        read=read_cursor_sandbox_cli_config,
        recommended="N/A — informational only pending clearer official docs on exact values",
        confidence="MEDIUM",
        why=(
            "This is NOT the same mechanism as row 15b (sandbox.json) — "
            "Common Pitfall 5 — and must never be read from the same function. "
            "Keys confirmed to exist; exact semantics unconfirmed. Apply: None."
        ),
        source=_CURSOR_CONFIG_SOURCE,
    ),
    CheckRow(
        id="cursor-sandbox-json",
        runtime="cursor",
        scope="runtime",
        check="sandbox.json (separate file)",
        read=read_cursor_sandbox_json,
        recommended=(
            '"workspace_readonly" or a scoped networkPolicy, analogous to '
            "Claude Code row 3"
        ),
        confidence="HIGH",
        why=(
            "Fully documented schema: type defaults workspace_readwrite if "
            "absent, networkPolicy.default defaults deny. Protected always-"
            "write-blocked paths: .cursor/*.json, .git/hooks/**, .vscode/**. "
            "Open Question 1: this machine's ~/.cursor/sandbox-policies/ "
            "directory is present but empty; no official doc names it; "
            "sandbox.json is the correct target. Apply: yes, security-relevant."
        ),
        source="https://cursor.com/docs/reference/sandbox",
        reads_section_file=False,
    ),
    CheckRow(
        id="cursor-model-parameters",
        runtime="cursor",
        scope="model",
        check="modelParameters",
        read=read_cursor_model_parameters,
        recommended="N/A — informational only, schema undocumented",
        confidence="LOW",
        why=(
            "[VERIFIED: read from a real file] and [documented by Cursor] are "
            "NOT the same confidence tier — this key is entirely absent from "
            "the official Configuration reference. A non-dict modelParameters "
            "value degrades to unknown rather than a guessed repr(). Apply "
            "stays None permanently (never gate this behind a future apply "
            "path without a documented schema to validate against)."
        ),
        source=_CURSOR_CONFIG_SOURCE,
    ),
    CheckRow(
        id="cursor-local-retention",
        runtime="cursor",
        scope="runtime",
        check="Local CLI chat/session retention",
        read=read_cursor_local_retention,
        recommended="N/A",
        confidence="LOW",
        why=(
            "Genuinely open, not confirmed absent (unlike opencode row 5, "
            "which has a closed-not-planned GitHub issue as positive evidence). "
            "CLI chats live under ~/.cursor/chats; the only retention "
            "information found concerns cloud-side storage, not local on-disk "
            "history. No citable source exists. Apply stays None permanently."
        ),
        source="",
        reads_section_file=False,
    ),
    CheckRow(
        id="cursor-cli-telemetry",
        runtime="cursor",
        scope="runtime",
        check="CLI-specific telemetry toggle",
        read=read_cursor_cli_telemetry,
        recommended="N/A",
        confidence="LOW",
        why=(
            "No CLI docs page documents a telemetry flag/env var for "
            "cursor-agent; only the unrelated editor's VS-Code-style "
            "telemetry.* settings were found (a different product surface). "
            "Apply stays None permanently."
        ),
        source="",
        reads_section_file=False,
    ),
    CheckRow(
        id="cursor-attribution",
        runtime="cursor",
        scope="runtime",
        check="attribution.attributeCommitsToAgent / attributePRsToAgent",
        read=read_cursor_attribution,
        recommended="leave as-is or disable per privacy preference",
        confidence="HIGH",
        why=(
            'Adds a "Made with Cursor" trailer/footer to commits/PRs. '
            "Apply: yes, low-stakes."
        ),
        source=_CURSOR_CONFIG_SOURCE,
    ),
    # source is a repo-relative citation (in-repo cross-reference), not an
    # external URL — tools/hooks/README.md's own closing line.
    CheckRow(
        id="rtk-cursor-integration",
        runtime="cross",
        scope="runtime",
        check="rtk Cursor integration",
        read=read_rtk_cursor_integration,
        recommended="rtk init -g --agent cursor if reported absent",
        confidence="HIGH",
        why=(
            "Point-in-time — MUST be re-probed at build/verify time, never "
            "cached or assumed stable across sessions, not fixed by this "
            "research session. Fold-in of Phase 3's Non-Goals note per "
            "tools/hooks/README.md's own closing line: \"Phase 4's config "
            "doctor folds this non-goals note in as its cross-runtime "
            'rtk-integration check." Apply: None in this wave.'
        ),
        source="tools/hooks/README.md",
        reads_section_file=False,
    ),
]


def build_catalog(env, runner=None):
    """Presence-gated catalog: skip missing files; omit zero-row sections."""
    if runner is None:
        runner = subprocess.run
    paths = resolve_runtime_config_paths(env)
    sections = []
    for runtime in ("claude", "opencode", "codex", "cursor"):
        path = paths[runtime]
        if not os.path.isfile(path):
            continue
        state, data = _READERS[runtime](path)
        matching = [row for row in CONFIG_DOCTOR_ROWS if row.runtime == runtime]
        ctx_data = None if state == CONFIG_STATE_UNREADABLE else data
        ctx = ReadContext(data=ctx_data, env=env, runner=runner)
        rows = [evaluate_row(row, ctx) for row in matching]
        if not rows:
            continue
        sections.append({"runtime": runtime, "config_path": path, "rows": rows})
    matching_cross = [row for row in CONFIG_DOCTOR_ROWS if row.runtime == "cross"]
    if matching_cross:
        ctx = ReadContext(data=None, env=env, runner=runner)
        rows = [evaluate_row(row, ctx) for row in matching_cross]
        sections.append({"runtime": "cross", "config_path": None, "rows": rows})
    return {"sections": sections}
