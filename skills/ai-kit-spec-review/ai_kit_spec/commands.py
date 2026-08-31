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
    render_reviewer_command shlex.quotes it before substitution, delivered as a real
    positional argument value, never via stdin."""
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


def _require_target_dir(cli_name, target_dir):
    if not target_dir:
        raise ValueError(
            f"execute-mode dispatch for {cli_name!r} requires target_dir -- a write-capable "
            f"CLI invoked without an explicit scratch directory would write to the "
            f"orchestrator's own cwd instead, which is never the intended target."
        )
    return shlex.quote(target_dir)


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


def _build_grok_execute_command(target_dir=None, **_params):
    """--sandbox workspace --cwd <target_dir> --always-approve -- confirmed live 2026-08-30: a
    write inside target_dir succeeded, a write to an absolute path outside it failed with a real
    "Permission denied (os error 13)". `--always-approve` is required for a headless run -- without
    it grok stalls indefinitely on an unapproved tool-use permission prompt with no interactive
    terminal to answer it (confirmed live: two prior attempts without this flag produced no file
    writes and no error, just silence until the process was killed).

    Unlike every other execute builder in this module, this one is wrapped in `sh -c '... "$(cat)"'`
    -- grok's `-p`/`--single <PROMPT>` is a required VALUE, not a stdin reader (confirmed via
    `grok --help`), but GSD's own cross_ai_delegation step only ever pipes the prompt via stdin
    (`echo "$TASK_PROMPT" | ... ${CROSS_AI_CMD}`), never fills a `{prompt}` placeholder. This
    wrapper bridges that gap: the outer pipe's stdin is captured by `$(cat)` inside the `sh -c`
    string and handed to grok as its positional prompt argument -- confirmed live end-to-end with
    a real piped prompt, the exact way GSD invokes this command.

    CAVEAT, same class as codex's own: never pass a target_dir under /tmp expecting confinement --
    not separately confirmed for grok's sandbox, but codex's own workspace-write sandbox has this
    exact carve-out, and target_dir here is always a real project/worktree path in practice."""
    quoted = _require_target_dir("grok", target_dir)
    return (f"sh -c 'grok --sandbox workspace --cwd {quoted} -m {{model}} --always-approve "
            f"--output-format plain -p \"$(cat)\"'")


def _build_claude_execute_command(target_dir=None, **_params):
    """`--restricted --permission-mode acceptEdits` -- confirmed live 2026-08-30: `--restricted`
    ("confines the file tools to the working directories") plus `acceptEdits` (auto-approves file
    edits so a headless run doesn't stall on an interactive permission prompt) genuinely confines
    writes -- a write inside the working directory succeeded, a write to an absolute path outside
    it was refused with the CLI's own real error naming the confining directory. `--restricted`
    also strips Bash/PowerShell/REPL/WebFetch by design (per --help), which is fine here: this
    dispatch only ever needs file-edit tools, never arbitrary command execution.

    Unlike codex/grok, claude has no `-C`/`--cwd` flag to pass target_dir directly -- confinement
    is anchored to the process's own working directory at launch, which is exactly why this
    builder (like grok's) wraps the whole invocation in `sh -c 'cd <dir> && exec claude ...'`
    rather than relying on whatever cwd GSD's own orchestrator happens to be running from.
    `exec` replaces the shell so stdin (GSD's own prompt delivery mechanism, per `claude -p`'s
    stdin-reading behavior -- see _build_claude_command's docstring) still reaches claude
    directly. Confirmed live end-to-end with a real piped prompt, the exact way GSD invokes this
    command."""
    quoted = _require_target_dir("claude", target_dir)
    return (f"sh -c 'cd {quoted} && exec claude -p --restricted --permission-mode acceptEdits "
            f"--model {{model}} --output-format text'")


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
    quoted = _require_target_dir("cursor-agent", target_dir)
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


# CLIs whose execute builder above is real and dispatchable but provides NO operating-system-level
# write confinement -- accepted-risk decision, not an oversight (see each builder's own docstring
# for the live re-tests that ruled out every confinement flag each CLI actually exposes). A caller
# dispatching to one of these MUST append ai_kit_spec.execute_dispatch's own soft-confinement
# guidance to the prompt -- it is the only mitigation that exists for these two.
NO_HARD_SANDBOX_CLIS = {"cursor-agent", "opencode"}


def _unimplemented_execute_command(cli_name):
    def _builder(**_params):
        raise ValueError(
            f"no execute-mode (write-capable) command builder for {cli_name!r} yet -- "
            f"mechanism not yet verified live (design spec open risk). Refusing rather "
            f"than guessing at an untested invocation."
        )
    return _builder


_COMMAND_BUILDERS = {
    (_REVIEW, "codex"): _build_codex_command,
    (_REVIEW, "claude"): _build_claude_command,
    (_REVIEW, "grok"): _build_grok_command,
    (_REVIEW, "opencode"): _build_opencode_command,
    (_REVIEW, "cursor-agent"): _build_cursor_agent_command,
    (_EXECUTE, "codex"): _build_codex_execute_command,
    (_EXECUTE, "grok"): _build_grok_execute_command,
    (_EXECUTE, "claude"): _build_claude_execute_command,
    (_EXECUTE, "cursor-agent"): _build_cursor_agent_execute_command,
    (_EXECUTE, "opencode"): _build_opencode_execute_command,
}


def _build_command(kind: str, cli: str, **params) -> str:
    """Shared factory for both `review` and `execute` dispatch -- the ONE lookup-and-raise shape
    both `build_reviewer_command`/`build_execute_command` (below) delegate to. Unrecognized
    kwargs are silently ignored by each builder's own `**_params` (so a caller can pass one
    params dict without filtering it per CLI first — e.g. `effort`/`service_tier` for codex are
    simply unused by grok's builder rather than raising). Raises ValueError for a `(kind, cli)`
    pair with no registered builder at all — never falls back to a guessed shape — and for
    structural params a specific builder rejects as unsafe (e.g. cursor-agent's write-capable
    review modes). A `cli` that IS registered for `kind` but whose builder itself always raises
    (e.g. `_unimplemented_execute_command`'s placeholders above) is a different, intentional
    case — that builder's own message explains why, not this function's."""
    builder = _COMMAND_BUILDERS.get((kind, cli))
    if builder is None:
        known = ", ".join(sorted(c for k, c in _COMMAND_BUILDERS if k == kind))
        label = "command" if kind == _REVIEW else "execute-mode (write-capable) command"
        raise ValueError(f"no {label} builder registered for cli={cli!r} (known {kind} CLIs: "
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
