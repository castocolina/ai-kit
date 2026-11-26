import shlex
from typing import NamedTuple

from ai_kit_spec import runner_facts
from ai_kit_spec.detection import removed_runtime_message, runtime_id

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


def execute_cli_error(cli, fact=None) -> str | None:
    """None unless `cli` names a removed runtime (39.1 D-02: the one removal message, before any
    spawn) or a recorded runner fact says the runner has no exec formula for it (a legacy name
    maps to its runtime id; 37 R9). An absent fact never refuses: the runner refuses at run time
    with its own named reason."""
    runtime = runtime_id(cli)
    removed = removed_runtime_message(runtime)
    if removed is not None:
        return removed
    if runner_facts.runner_has_exec(fact, runtime) is False:
        return (f"{cli!r} has no exec formula in the runner (route no_formula): "
                f"{runner_facts.FACT_SOURCE}")
    return None


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
