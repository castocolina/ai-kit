import shlex
from typing import NamedTuple

# ── Policy resolution ────────────────────────────────────────────────────

class ResolvedReviewer(NamedTuple):
    """A reviewer chosen for this run. cli/command are None for native
    (current-runtime) dispatch. model == "" means "no override — inherit
    the current session's own default model" (never a hardcoded name).
    extra holds any reviewer-entry fields beyond key/model/vendor/cli/
    command (e.g. effort, service_tier) for the caller to interpolate into
    `command`."""

    key: str
    model: str
    vendor: str
    cli: str | None
    command: str | None
    extra: dict


# ── Command building (Strategy/Factory, one builder per CLI) ────────────

# Every CLI has its own real syntax for reasoning-effort/service-tier/
# execution-mode knobs — codex wants two separate `-c key='"val"'` flags,
# cursor-agent encodes effort/fast/context as bracket-parameter overrides
# on the --model argument itself, others take no such knob at all today.
# Hand-writing that per-CLI quoting into a review-spec.toml `command`
# string (the old approach) pushed CLI-specific knowledge onto whoever
# configures a reviewer; centralizing it here means review-spec-config's
# setup wizard (and `build-command`/`build-model-id`, its CLI entrypoints
# below) only ever has to pass structured params, never hand-transcribe
# a quoting idiom. Each builder returns a `command`-template STRING with
# {model}/{prompt} left as literal placeholders — render_reviewer_command
# (below) fills those at dispatch time from the reviewer entry's own
# stored `model` and the real prompt text, exactly as before; builders
# here only ever see structural params (effort, service_tier, mode), not
# prompt/model text, and must never be called with either.

def _build_codex_command(effort=None, service_tier=None, **_params):
    """No {prompt} in this template — confirmed live (codex --help): the
    positional PROMPT arg, when omitted, reads instructions from stdin.
    Prompt delivery is stdin-only for every builder below except gemini's
    (unverified, no installed CLI to confirm against) — see
    probe_reviewer_quota's unconditional `input=` and review-spec/
    SKILL.md's Step 1 external-CLI dispatch, which both redirect the
    already-on-disk prompt file as stdin regardless of whether a given
    template still inlines a literal {prompt} placeholder (the open
    hand-written-command escape hatch, and gemini today, still can)."""
    parts = ["codex exec --sandbox read-only --skip-git-repo-check", "-m {model}"]
    if effort:
        parts.append(f"-c model_reasoning_effort='\"{effort}\"'")
    if service_tier:
        parts.append(f"-c service_tier='\"{service_tier}\"'")
    return " ".join(parts)


def _build_claude_command(**_params):
    """No {prompt} — confirmed live: `claude -p` with no positional
    prompt argument reads it from stdin."""
    return "claude -p --model {model} --output-format text"


def _build_grok_command(**_params):
    """`-p -` (dash-as-value), not bare `-p` — confirmed live: grok's
    `-p`/`--single <PROMPT>` requires a value; only literal `-` makes it
    read that value from stdin instead of a positional arg. No {prompt}
    placeholder — see _build_codex_command's docstring."""
    return "grok -p - -m {model} --output-format plain"


def _build_gemini_command(**_params):
    return "gemini -m {model} --sandbox --approval-mode yolo {prompt}"


def _build_opencode_command(**_params):
    """No {prompt} — confirmed live: `opencode run -m {model}` with no
    positional message reads the prompt from stdin."""
    return "opencode run -m {model}"


def _build_cursor_agent_command(mode="plan", **_params):
    """--mode plan|ask are cursor-agent's own confirmed read-only modes
    (--help: "plan: read-only/planning (analyze, propose plans, no
    edits). ask: Q&A style ... (read-only)") — any other mode would allow
    edits, so this refuses rather than silently building a write-capable
    command for a reviewer.

    No {prompt} placeholder — confirmed live: cursor-agent's `-p`/
    `--print` is a boolean flag (no value), and with it set the process
    reads the prompt from stdin rather than a positional argument."""
    if mode not in ("plan", "ask"):
        raise ValueError(
            f"cursor-agent reviewer dispatch must use a read-only --mode "
            f"('plan' or 'ask'), got {mode!r}"
        )
    return f"cursor-agent -p --output-format text --mode {mode} --model {{model}}"


_COMMAND_BUILDERS = {
    "codex": _build_codex_command,
    "claude": _build_claude_command,
    "grok": _build_grok_command,
    "gemini": _build_gemini_command,
    "opencode": _build_opencode_command,
    "cursor-agent": _build_cursor_agent_command,
}


def build_reviewer_command(cli: str, **params) -> str:
    """Factory entry point: dispatch to `cli`'s own builder. Unrecognized
    kwargs are silently ignored by each builder's `**_params` (so a
    caller can pass one params dict without filtering it per CLI first —
    e.g. `effort`/`service_tier` for codex are simply unused by grok's
    builder rather than raising). Raises ValueError for an unregistered
    `cli` — never falls back to a guessed shape — and for structural
    params a specific builder rejects as unsafe (e.g. cursor-agent's
    write-capable modes, above)."""
    builder = _COMMAND_BUILDERS.get(cli)
    if builder is None:
        raise ValueError(
            f"no command builder registered for cli={cli!r} (known: "
            f"{', '.join(sorted(_COMMAND_BUILDERS))})"
        )
    return builder(**params)


def build_cursor_agent_model_id(base_model: str, effort=None, fast=None, context=None) -> str:
    """cursor-agent's own per-call effort/fast/context tuning lives in
    the --model argument itself via bracket-parameter overrides
    (confirmed live, --help: "Parameterized models accept quoted bracket
    overrides, e.g. 'claude-opus-4-8[context=1m,effort=high,
    fast=false]'"), not a separate CLI flag the command builder above
    could set — this builds that string for the reviewer entry's own
    `model` field instead. Returns `base_model` unchanged when no
    overrides are given, so calling this is always safe even with
    nothing to override."""
    overrides = []
    if effort:
        overrides.append(f"effort={effort}")
    if fast is not None:
        overrides.append(f"fast={'true' if fast else 'false'}")
    if context:
        overrides.append(f"context={context}")
    if not overrides:
        return base_model
    return f"{base_model}[{','.join(overrides)}]"


def build_reviewer_model_id(cli: str, base_model: str, effort=None, fast=None,
                             context=None) -> str:
    """Like build_reviewer_command, but for the `model` field itself —
    only cursor-agent encodes structural params there today; every other
    known CLI takes effort/service_tier as command-line flags instead
    (see build_reviewer_command), so this returns base_model unchanged
    for them rather than raising (no params to lose, unlike an
    unrecognized cli in build_reviewer_command)."""
    if cli == "cursor-agent":
        return build_cursor_agent_model_id(base_model, effort=effort, fast=fast, context=context)
    return base_model


def render_reviewer_command(resolved: "ResolvedReviewer", prompt: str) -> str:
    """Fill a resolved reviewer's `command` template. {model} and {prompt}
    are always available; any of the entry's extra fields (effort,
    service_tier, ...) fill their own {placeholder} when the command
    references it. Shared by probe_reviewer_quota (below) and
    review-spec/SKILL.md's real dispatch step (via the `render-command`
    CLI subcommand), so probing and dispatching can never drift apart.

    Only {prompt} is shell-escaped (via shlex.quote) before substitution —
    it is free text built from document paths/content signals and MUST
    survive as exactly one shell argument no matter what it contains (this
    fixes a real command-injection risk: an unescaped {prompt} spliced into
    a `shell=True` command string via a document path containing `"`, `$`,
    or `` ` `` would corrupt or inject into the command). {model} and any
    `extra` field are deliberately left unescaped — they're short,
    human-typed config values, and some CLIs need their own literal
    quoting idiom in the template around them (e.g. codex's `-c
    key='"{effort}"'`), which auto-quoting would break. Command templates
    must therefore write a bare `{prompt}` (never `"{prompt}"` or
    `'{prompt}'` — the quoting is already applied here).

    Raises `ValueError` — never a raw `KeyError`/`AttributeError`/
    `IndexError`/`TypeError` — when `resolved.command` is missing (a
    `cli`-set entry with no `command` is a malformed config, per the
    schema's "required iff `cli` present"), the template references a
    placeholder that isn't `{model}`/`{prompt}`/one of `extra`'s keys,
    contains a literal unescaped brace, or `extra` itself defines a
    `model`/`prompt` key (a hand-written config collision with the two
    reserved placeholder names — `str.format`'s duplicate-keyword-argument
    `TypeError` in that case is exactly as much a malformed-config problem
    as a bad placeholder, and gets the same treatment). A malformed
    `review-spec.toml` entry must surface as a reportable config error,
    never crash the caller."""
    if not resolved.command:
        raise ValueError(
            f"reviewer {resolved.key!r} has cli={resolved.cli!r} set but no command template"
        )
    try:
        return resolved.command.format(
            model=resolved.model, prompt=shlex.quote(prompt), **resolved.extra
        )
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise ValueError(
            f"reviewer {resolved.key!r} has a malformed command template: {exc}"
        ) from exc


def _require_target_dir(cli_name, target_dir):
    if not target_dir:
        raise ValueError(
            f"execute-mode dispatch for {cli_name!r} requires target_dir -- a write-capable "
            f"CLI invoked without an explicit scratch directory would write to the "
            f"orchestrator's own cwd instead, which is never the intended target."
        )
    return shlex.quote(target_dir)


def _build_codex_execute_command(target_dir=None, **_params):
    """--sandbox workspace-write -C <target_dir> -- confirmed live 2026-08-29: reads broadly
    (any absolute path, unrestricted), writes ONLY within target_dir -- a write attempt outside
    target_dir failed with a real "Read-only file system" error.

    CAVEAT, also confirmed live: codex's workspace-write sandbox additionally, always grants
    write access to /tmp and $TMPDIR regardless of -C. If target_dir itself is under /tmp, an
    out-of-target_dir write inside /tmp still succeeds -- confinement only holds when target_dir
    is OUTSIDE /tmp (e.g. a real project/worktree path), which is the intended real-world usage
    here. Never pass a target_dir under /tmp expecting confinement from this builder."""
    quoted = _require_target_dir("codex", target_dir)
    return f"codex exec --sandbox workspace-write -C {quoted} -m {{model}}"


def _unimplemented_execute_command(cli_name):
    def _builder(**_params):
        raise ValueError(
            f"no execute-mode (write-capable) command builder for {cli_name!r} yet -- "
            f"mechanism not yet verified live (design spec open risk). Refusing rather "
            f"than guessing at an untested invocation."
        )
    return _builder


_EXECUTE_COMMAND_BUILDERS = {
    "codex": _build_codex_execute_command,
    # cursor-agent and opencode: demoted 2026-08-29 after Task 5's live confinement smoke test
    # (Step 5) -- `--workspace`/`--dir` are BOTH plain cwd defaults, not write sandboxes. Both
    # CLIs successfully wrote a file OUTSIDE target_dir when explicitly asked to, confirming no
    # real confinement guarantee exists for either. Per this task's own escalation clause, they
    # are refused loudly (same as grok/claude) rather than shipped with a false promise.
    "cursor-agent": _unimplemented_execute_command("cursor-agent"),
    "opencode": _unimplemented_execute_command("opencode"),
    "grok": _unimplemented_execute_command("grok"),
    "claude": _unimplemented_execute_command("claude"),
}


def build_execute_command(cli: str, **params) -> str:
    """Factory entry point for write-capable execute dispatch -- parallel to, and never
    merged with, build_reviewer_command's read-only catalog."""
    builder = _EXECUTE_COMMAND_BUILDERS.get(cli)
    if builder is None:
        raise ValueError(f"no execute-mode command builder registered for cli={cli!r}")
    return builder(**params)
