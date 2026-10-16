import shlex
from typing import NamedTuple

from ai_kit_spec.detection import RUNTIMES, runtime_id

# ── Policy resolution ────────────────────────────────────────────────────────


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


# Table runtimes have no command string: the runner builds their argv. Only grok, which has
# no runner formula, still generates a custom-entry template here (D-21, D-29).

def build_grok_command() -> str:
    """The command a custom grok entry stores. Grok has no runner formula (D-21).

    Corrected 2026-08-29 by live re-reproduction: `-p -` does NOT read the prompt from
    stdin -- `-p`/`--single <PROMPT>` is a required VALUE, and passing a literal `-` sends
    the two-character string "-" as the prompt itself (confirmed live: grok replied "A
    single dash is too little to act on"). The `-p -` design here was an earlier unverified
    assumption inherited from this builder before it was ever run against a real grok CLI.
    render_reviewer_command substitutes {prompt} raw into one argv element (no shell, no
    quoting), delivered as a real positional argument value, never via stdin."""
    return "grok -p {prompt} -m {model} --output-format plain"


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


# The runner runtimes that are not review-only. Derived from the runtime table, never
# hand-maintained: a review-only or runner-less row drops out of this set (and makes any
# explicit choice of it a hard error via execute_cli_error, below). claude is review-only and
# grok has no runner (Phase 16.1 D-15, Phase 18.1 D-14): both are a hard error here.
SUPPORTED_EXECUTE_CLIS = tuple(sorted(
    rt for rt, row in RUNTIMES.items() if row.runner and not row.review_only
))


def execute_cli_error(cli) -> str | None:
    """None when `cli` is a supported execute CLI (exact, case-sensitive match -- the same
    convention as KNOWN_CLIS), otherwise the human-readable error naming the supported set.
    Callers must fail before any spawn or config write when this returns a message."""
    if runtime_id(cli) in SUPPORTED_EXECUTE_CLIS:
        return None
    return (f"{cli!r} cannot be an execution CLI; supported execute CLIs: "
            f"{', '.join(SUPPORTED_EXECUTE_CLIS)}")


def build_cursor_agent_model_id(base_model: str, effort=None, fast=None, context=None) -> str:
    """cursor's own per-call effort/fast/context tuning lives in the --model
    argument itself via bracket-parameter overrides (confirmed live, --help:
    "Parameterized models accept quoted bracket overrides, e.g.
    'claude-opus-4-8[context=1m,effort=high, fast=false]'"), not a separate
    runner flag — this builds that string for the reviewer entry's own
    `model` field instead. Returns `base_model` unchanged when no overrides
    are given, so calling this is always safe even with nothing to override."""
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
    """The `model` field itself. Only cursor encodes effort/fast/context as
    bracket overrides on the model id; every other runtime takes its knobs as
    runner flags, so this returns base_model unchanged for them rather than
    raising."""
    if runtime_id(cli) == "cursor":
        return build_cursor_agent_model_id(base_model, effort=effort, fast=fast, context=context)
    return base_model


def render_reviewer_command(resolved: "ResolvedReviewer", prompt: str) -> list[str]:
    """Fill a custom reviewer's `command` template and return the argv list to run, with no
    shell (D-21). Table-runtime entries have no command: the runner builds their argv, so this
    raises rather than inventing one. The template is tokenized by split_command_template
    (which rejects shell syntax loudly), then each token is formatted: {model} and {prompt}
    are always available; any of the entry's extra fields fill their own {placeholder}.

    The prompt is substituted raw: tokenization happens before substitution, so it is already
    one argv element and no shell ever re-splits it. {model} and extra fields are likewise
    substituted raw.

    Raises `ValueError` -- never a raw `KeyError`/`AttributeError`/`IndexError`/`TypeError` --
    when the entry has no command, the template is empty or uses shell syntax, references a
    placeholder that isn't {model}/{prompt}/one of `extra`'s keys, contains a literal brace, or
    `extra` defines a `model`/`prompt` key."""
    if not resolved.command:
        raise ValueError(
            f"reviewer {resolved.key} has no command; table runtimes run through the runner"
        )
    try:
        tokens = split_command_template(resolved.key, resolved.command)
        return [token.format(model=resolved.model, prompt=prompt, **resolved.extra)
                for token in tokens]
    except (KeyError, IndexError, ValueError, TypeError, AttributeError) as exc:
        raise ValueError(f"reviewer {resolved.key!r}: {exc}") from exc
