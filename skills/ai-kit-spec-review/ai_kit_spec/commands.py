import shlex
from typing import NamedTuple

from ai_kit_spec.detection import RUNTIMES, exec_formula_source, has_exec_formula, runtime_id

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


# The runtimes the runner can execute: rows whose exec formula has a head (36 D-08). Derived from
# the runtime table, never hand-maintained; any other choice is refused by execute_cli_error.
SUPPORTED_EXECUTE_CLIS = tuple(sorted(
    rid for rid, row in RUNTIMES.items() if has_exec_formula(row)
))


def execute_cli_error(cli) -> str | None:
    """None when the runner has an exec formula for `cli` (exact, case-sensitive; a legacy
    name maps to its runtime id), else the refusal naming the fact: the missing formula for a
    table row, or the custom-lane rule for a runtime outside the table. Callers fail before any
    spawn or config write when this returns a message (36 SPEC R7)."""
    row = RUNTIMES.get(runtime_id(cli))
    if row is None:
        return (f"{cli!r} is not a runtime in the table; store it as a custom `command` lane "
                "(custom lanes run in review mode only)")
    if has_exec_formula(row):
        return None
    return (f"{cli!r} has no exec formula in the runner (route no_formula): "
            f"{exec_formula_source(row)}")


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
