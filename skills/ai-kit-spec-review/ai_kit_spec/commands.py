import shlex
from typing import NamedTuple

from ai_kit_spec.detection import runtime_id

# ── Policy resolution ────────────────────────────────────────────────────

class ResolvedReviewer(NamedTuple):
    """A reviewer chosen for this run. runtime None with model == "" is the
    session default; command set with no runtime is a custom entry. Other
    runtime/model pairs use the selected runtime. Extra holds other fields."""

    key: str
    model: str
    vendor: str
    runtime: str | None
    command: str | None
    extra: dict


# ── Command building (Strategy/Factory, one builder per CLI x kind) ─────

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
#
# `review` (read-only) and `execute` (write-capable) dispatch share this ONE registry and ONE
# factory (`_build_command`, below), keyed by (kind, cli) -- not two parallel dicts/factories.
# Only the underlying per-CLI *builder function* legitimately differs between the two kinds (a
# real, different CLI invocation: read-only sandbox vs. workspace-write, different flags
# entirely) -- the registry/lookup/error-shape around them was pure duplication and is unified
# here. `kind` is a distinct axis from cursor-agent's own `mode` structural param (plan/ask) --
# never conflate the two names.
_REVIEW = "review"
_EXECUTE = "execute"


def _codex_effort_service_tier_flags(effort=None, service_tier=None) -> str:
    """Shared by BOTH codex builders (review's --sandbox read-only and execute's --sandbox
    workspace-write) -- effort/service_tier are orthogonal to sandbox mode, which is the only
    thing that should ever differ between review and execute for a given CLI (the whole point of
    the unified (kind, cli) registry above: same behavior, gated by a flag/enum, never
    duplicated-and-drifted). This is the ONE place that builds these two `-c key='"val"'` flags;
    previously only the review builder used them, and the execute builder silently dropped
    effort/service_tier via its own bare **_params -- a real gap, not an intentional asymmetry,
    fixed 2026-08-31."""
    parts = []
    if effort:
        parts.append(f"-c model_reasoning_effort='\"{effort}\"'")
    if service_tier:
        parts.append(f"-c service_tier='\"{service_tier}\"'")
    return " ".join(parts)


def _build_codex_command(effort=None, service_tier=None, **_params):
    """No {prompt} in this template — confirmed live (codex --help): the
    positional PROMPT arg, when omitted, reads instructions from stdin.
    Prompt delivery is stdin-only for every builder below except grok's —
    see probe_reviewer_quota's unconditional `input=` and review-spec/
    SKILL.md's Step 1 external-CLI dispatch, which both redirect the
    already-on-disk prompt file as stdin regardless of whether a given
    template still inlines a literal {prompt} placeholder (the open
    hand-written-command escape hatch, and grok's builder, still can).

    `{model}` here MUST be codex's BARE model id (e.g. "gpt-5.6-sol"),
    never suffixed with an effort/tier tag like "gpt-5.6-sol-high" —
    confirmed live 2026-08-29: codex rejects a suffixed id outright
    ("The 'gpt-5.6-sol-high' model is not supported..."). Unlike
    cursor-agent (which bakes effort/fast/context into the model-id
    string via build-model-id), codex takes effort/service_tier as these
    SEPARATE `-c` flags below — never encode them into `{model}` itself."""
    parts = ["codex exec --sandbox read-only --skip-git-repo-check", "-m {model}"]
    flags = _codex_effort_service_tier_flags(effort, service_tier)
    if flags:
        parts.append(flags)
    return " ".join(parts)


def _build_claude_command(**_params):
    """No {prompt} — confirmed live: `claude -p` with no positional
    prompt argument reads it from stdin."""
    return "claude -p --model {model} --output-format text"


def _build_grok_command(**_params):
    """Corrected 2026-08-29 by live re-reproduction: `-p -` does NOT read the prompt from
    stdin -- `-p`/`--single <PROMPT>` is a required VALUE, and passing a literal `-` sends
    the two-character string "-" as the prompt itself (confirmed live: grok replied "A
    single dash is too little to act on"). The `-p -` design here was an earlier unverified
    assumption inherited from this builder before it was ever run against a real grok CLI.
    Correct form uses the {prompt} placeholder like every other builder in this module --
    render_reviewer_command substitutes it raw into one argv element (no shell, no quoting),
    delivered as a real positional argument value, never via stdin."""
    return "grok -p {prompt} -m {model} --output-format plain"


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

    --trust: live-verified finding (2026-08-31) -- a directory cursor-agent has never seen
    before (e.g. a fresh throwaway worktree) fails with "Workspace Trust Required" before it
    ever gets to --mode's own read-only guarantee, making probe-quota/check-reviewer falsely
    report the candidate unavailable. --help: "Trust the current workspace without prompting"
    -- it only skips that interactive confirmation, it does not grant any write capability
    --mode plan/ask doesn't already withhold, so it's safe to always include here.

    No {prompt} placeholder — confirmed live: cursor-agent's `-p`/
    `--print` is a boolean flag (no value), and with it set the process
    reads the prompt from stdin rather than a positional argument."""
    if mode not in ("plan", "ask"):
        raise ValueError(
            f"cursor-agent reviewer dispatch must use a read-only --mode "
            f"('plan' or 'ask'), got {mode!r}"
        )
    return f"cursor-agent -p --output-format text --mode {mode} --trust --model {{model}}"


def split_command_template(key: str, template: str | None) -> list[str]:
    """Tokenizes a reviewer `command` template into the argv tokens that
    render_reviewer_command then fills -- the consent display (`trust-local --show`) prints
    that RENDERED argv, so every substituted value a user approves is what executes (D-10).
    Raises `ValueError` naming `key` when
    the template is missing/empty/whitespace (a config error, never a silent no-op or a
    Popen IndexError) or when it relies on shell syntax: a token made only of `();<>|&`
    punctuation, a `$` or a backtick anywhere in the template. Argv dispatch runs no shell,
    so such a template would silently change meaning -- it fails loudly instead."""
    if not template or not template.strip():
        raise ValueError(f"reviewer {key!r} has an empty command template")
    if "$" in template or "`" in template:
        raise ValueError(f"reviewer {key!r} command uses shell syntax, which argv dispatch "
                         f"does not run: {template!r}")
    lexer = shlex.shlex(template, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    tokens = list(lexer)
    if any(tok and all(ch in "();<>|&" for ch in tok) for tok in tokens):
        raise ValueError(f"reviewer {key!r} command uses shell syntax, which argv dispatch "
                         f"does not run: {template!r}")
    return shlex.split(template)


def _require_target_dir(cli_name, target_dir):
    if not target_dir:
        raise ValueError(
            f"execute-mode dispatch for {cli_name!r} requires target_dir -- a write-capable "
            f"CLI invoked without an explicit scratch directory would write to the "
            f"orchestrator's own cwd instead, which is never the intended target."
        )
    # Braces are doubled AFTER quoting so a target_dir containing `{` or `}` survives both
    # argv dispatch (shlex.split restores the doubled braces) and GSD's own
    # `.format(model=...)` string path (which un-doubles them) without a KeyError.
    return shlex.quote(target_dir).replace("{", "{{").replace("}", "}}")


def _build_codex_execute_command(target_dir=None, effort=None, service_tier=None, **_params):
    """--sandbox workspace-write -C <target_dir> -- confirmed live 2026-08-29: reads broadly
    (any absolute path, unrestricted), writes ONLY within target_dir -- a write attempt outside
    target_dir failed with a real "Read-only file system" error.

    CAVEAT, also confirmed live: codex's workspace-write sandbox additionally, always grants
    write access to /tmp and $TMPDIR regardless of -C. If target_dir itself is under /tmp, an
    out-of-target_dir write inside /tmp still succeeds -- confinement only holds when target_dir
    is OUTSIDE /tmp (e.g. a real project/worktree path), which is the intended real-world usage
    here. Never pass a target_dir under /tmp expecting confinement from this builder.

    `--skip-git-repo-check` added 2026-08-30, caught by a real live end-to-end dispatch test: a
    target_dir that isn't inside a trusted git repo made codex refuse outright ("Not inside a
    trusted directory and --skip-git-repo-check was not specified"), exit 1, before ever
    attempting a write -- every prior live test of this builder happened to run inside a real git
    worktree, which masked this. Matches _build_codex_command's own review-mode builder, which
    already carries this flag.

    `effort`/`service_tier` added 2026-08-31 -- this builder used to silently drop them via its
    own bare **_params while the review builder honored them, a real asymmetry the unified
    (kind, cli) registry was built specifically to prevent (review/execute should only ever
    differ by their own structural sandbox-mode flag, never by which params one builder bothers
    to read). Shares _codex_effort_service_tier_flags with the review builder -- same flags, same
    place they're built, only the sandbox mode differs."""
    quoted = _require_target_dir("codex", target_dir)
    parts = [f"codex exec --sandbox workspace-write --skip-git-repo-check -C {quoted} -m {{model}}"]
    flags = _codex_effort_service_tier_flags(effort, service_tier)
    if flags:
        parts.append(flags)
    return " ".join(parts)


def _build_cursor_agent_execute_command(target_dir=None, **_params):
    """NO real OS-level write confinement -- re-confirmed live 2026-08-30 even WITH the CLI's own
    `--sandbox enabled` flag (an earlier test only tried `--workspace`, a plain cwd default; this
    flag doesn't help either -- a write to an absolute path outside target_dir still succeeded).
    Kept in NO_HARD_SANDBOX_CLIS (below) by explicit, accepted user risk decision (2026-08-30) --
    the caller MUST pair this with dispatch_guidance's soft-confinement prose (see
    ai_kit_spec.execute_dispatch) since the CLI itself provides no enforcement whatsoever.

    `--force`/`-f` allows all commands (needed for a headless, non-interactive write); `--sandbox
    enabled` and `--workspace` are still passed even though neither confines writes -- they're
    real flags this CLI exposes for exactly this purpose and cost nothing to include, in case a
    future CLI version tightens their enforcement.

    --trust: same "Workspace Trust Required" finding as _build_cursor_agent_command's own
    docstring -- a fresh target_dir fails before --force even matters unless this is passed.

    No {prompt} placeholder -- confirmed live (see _build_cursor_agent_command's own docstring):
    `-p`/`--print` reads the prompt from stdin, matching GSD's stdin-only delivery contract."""
    quoted = _require_target_dir("cursor", target_dir)
    return (f"cursor-agent --sandbox enabled --workspace {quoted} -p --output-format text "
            f"--model {{model}} --trust --force")


def _build_opencode_execute_command(target_dir=None, **_params):
    """NO real OS-level write confinement -- confirmed live 2026-08-29 (`--dir` is a plain cwd
    default) and re-confirmed live 2026-08-30 with `--dir` + `--auto` together (a write to an
    absolute path outside target_dir still succeeded). No CLI flag equivalent to codex's -C/grok's
    --cwd/cursor's --sandbox exists for opencode at all (confirmed via `opencode run --help`).
    Kept in NO_HARD_SANDBOX_CLIS (below) by explicit, accepted user risk decision (2026-08-30) --
    the caller MUST pair this with dispatch_guidance's soft-confinement prose (see
    ai_kit_spec.execute_dispatch) since the CLI itself provides no enforcement whatsoever.

    `--auto` auto-approves permissions (needed for a headless, non-interactive write) -- without
    it a headless run stalls on an interactive approval prompt, same class of requirement as
    grok's --always-approve and claude's --permission-mode acceptEdits.

    No {prompt} placeholder -- confirmed live (see _build_opencode_command's own docstring):
    `opencode run` with no positional message reads the prompt from stdin."""
    quoted = _require_target_dir("opencode", target_dir)
    return f"opencode run -m {{model}} --dir {quoted} --auto"


_COMMAND_BUILDERS = {
    (_REVIEW, "codex"): _build_codex_command,
    (_REVIEW, "claude"): _build_claude_command,
    (_REVIEW, "grok"): _build_grok_command,
    (_REVIEW, "opencode"): _build_opencode_command,
    (_REVIEW, "cursor"): _build_cursor_agent_command,
    (_EXECUTE, "codex"): _build_codex_execute_command,
    (_EXECUTE, "cursor"): _build_cursor_agent_execute_command,
    (_EXECUTE, "opencode"): _build_opencode_execute_command,
}

# CLIs whose execute builder above is real and dispatchable but provides NO operating-system-level
# write confinement -- accepted-risk decision, not an oversight (see each builder's own docstring
# for the live re-tests that ruled out every confinement flag each CLI actually exposes). A caller
# dispatching to one of these MUST append ai_kit_spec.execute_dispatch's own soft-confinement
# guidance to the prompt -- it is the only mitigation that exists for these two.
NO_HARD_SANDBOX_CLIS = {"cursor", "opencode"}

# The CLIs with a real, live-verified execute builder in the registry above. Derived, never
# hand-maintained: deleting a registry entry automatically drops it from this set (and makes any
# explicit choice of it a hard error via execute_cli_error, below). claude and grok were removed
# on purpose (Phase 16.1 D-15): both builders nested `sh -c` and could not run under GSD's
# no-shell word splitting.
SUPPORTED_EXECUTE_CLIS = tuple(sorted(cli for kind, cli in _COMMAND_BUILDERS if kind == _EXECUTE))


def execute_cli_error(cli) -> str | None:
    """None when `cli` is a supported execute CLI (exact, case-sensitive match -- the same
    convention as KNOWN_CLIS), otherwise the human-readable error naming the supported set.
    Callers must fail before any spawn or config write when this returns a message."""
    if runtime_id(cli) in SUPPORTED_EXECUTE_CLIS:
        return None
    return (f"{cli!r} cannot be an execution CLI; supported execute CLIs: "
            f"{', '.join(SUPPORTED_EXECUTE_CLIS)}")


def _build_command(kind: str, cli: str, **params) -> str:
    """Shared factory for both `review` and `execute` dispatch -- the ONE lookup-and-raise shape
    both `build_reviewer_command`/`build_execute_command` (below) delegate to. Unrecognized
    kwargs are silently ignored by each builder's own `**_params` (so a caller can pass one
    params dict without filtering it per CLI first — e.g. `effort`/`service_tier` for codex are
    simply unused by grok's builder rather than raising). Raises ValueError for a `(kind, cli)`
    pair with no registered builder at all — never falls back to a guessed shape — and for
    structural params a specific builder rejects as unsafe (e.g. cursor-agent's write-capable
    review modes). For `kind == execute`, an unregistered `cli` raises execute_cli_error's
    message naming the supported execute CLIs -- an explicit claude/grok executor choice is a
    hard error (D-15), never a fallback to another CLI."""
    cli = runtime_id(cli)
    builder = _COMMAND_BUILDERS.get((kind, cli))
    if builder is None:
        if kind == _EXECUTE:
            raise ValueError(execute_cli_error(cli))
        known = ", ".join(sorted(c for k, c in _COMMAND_BUILDERS if k == kind))
        raise ValueError(f"no command builder registered for cli={cli!r} (known {kind} CLIs: "
                          f"{known})")
    return builder(**params)


def build_reviewer_command(cli: str, **params) -> str:
    """Factory entry point for read-only reviewer dispatch. See `_build_command`'s own docstring
    for the shared lookup/error behavior."""
    return _build_command(_REVIEW, cli, **params)


def build_execute_command(cli: str, **params) -> str:
    """Factory entry point for write-capable execute dispatch. See `_build_command`'s own
    docstring for the shared lookup/error behavior."""
    return _build_command(_EXECUTE, cli, **params)


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
    if runtime_id(cli) == "cursor":
        return build_cursor_agent_model_id(base_model, effort=effort, fast=fast, context=context)
    return base_model


def render_reviewer_command(resolved: "ResolvedReviewer", prompt: str) -> list[str]:
    """Fill a resolved reviewer's `command` template and return the argv LIST to run -- argv
    dispatch with no shell (D-10). The template is tokenized by split_command_template
    (which rejects shell syntax loudly), then each token is formatted: {model} and {prompt}
    are always available; any of the entry's extra fields (effort, service_tier, ...) fill
    their own {placeholder} when the command references it. Shared by probe_reviewer_quota
    (below) and review-spec/SKILL.md's real dispatch step (via the `render-command` CLI
    subcommand), so probing and dispatching can never drift apart.

    The prompt is substituted RAW and UNQUOTED: it is already one argv element by
    construction (tokenization happens before substitution), so no quoting is needed -- free
    text built from document paths/content can never inject into anything because no shell
    ever re-splits it. Templates may write `{prompt}` bare or quoted ("{prompt}" and
    '{prompt}' both tokenize to the same single token under posix shlex). {model} and extra
    fields are likewise substituted raw -- short, human-typed config values.

    Raises `ValueError` -- never a raw `KeyError`/`AttributeError`/`IndexError`/`TypeError`
    -- when `resolved.command` is missing (a `cli`-set entry with no `command` is a
    malformed config, per the schema's "required iff `cli` present"), the template is empty
    or uses shell syntax (see split_command_template), references a placeholder that isn't
    {model}/{prompt}/one of `extra`'s keys, contains a literal unescaped brace, or `extra`
    itself defines a `model`/`prompt` key (a hand-written config collision with the two
    reserved placeholder names). A malformed `review-spec.toml` entry must surface as a
    reportable config error, never crash the caller."""
    if resolved.command:
        try:
            tokens = split_command_template(resolved.key, resolved.command)
            return [token.format(model=resolved.model, prompt=prompt, **resolved.extra)
                    for token in tokens]
        except (KeyError, IndexError, ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"reviewer {resolved.key!r}: {exc}") from exc
    if resolved.runtime and not resolved.model:
        raise ValueError(f"reviewer {resolved.key!r} has a runtime but no model")
    if not resolved.runtime:
        raise ValueError(
            f"reviewer {resolved.key} has no runtime or command; "
            "the session default is run by the host"
        )
    template = build_reviewer_command(
        resolved.runtime, effort=resolved.extra.get("effort"),
        service_tier=resolved.extra.get("service_tier"),
        mode=resolved.extra.get("cursor_mode", "plan"),
    )
    try:
        tokens = split_command_template(resolved.key, template)
        return [token.format(model=resolved.model, prompt=prompt, **resolved.extra)
                for token in tokens]
    except (KeyError, IndexError, ValueError, TypeError, AttributeError) as exc:
        raise ValueError(f"reviewer {resolved.key!r}: {exc}") from exc
