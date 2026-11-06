"""Conservative ownership checks for ai-kit's status-line command."""

import os
import shlex

# Interpreter flags that take NO value and therefore may precede the script
# argument. Anything else (-c, -m, -X, -W, long options, unknown shorts) makes
# the command foreign: it either consumes the would-be script token as its own
# value or runs no script file at all, so the first bare token cannot be
# trusted as a script path ai-kit may rewrite or uninstall.
_NO_ARG_FLAGS = frozenset({"-B", "-E", "-I", "-O", "-OO", "-P", "-S", "-q", "-s", "-u"})


def _interpreter_command(argv):
    """Whether argv begins with a supported Python interpreter and script."""
    if len(argv) < 2 or any(token in {"|", ";", "&&", "||", ">", "<"} for token in argv):
        return False
    interpreter = os.path.basename(argv[0])
    suffix = interpreter[6:].replace(".", "") if interpreter.startswith("python") else ""
    return bool(suffix.isdigit())


def _script_index(argv):
    """Return the script-argument index, or None for any unsupported form.

    Only allowlisted no-argument flags may precede the script. Any other option
    (-c/-m run no file; -X/-W and every other option consume the next token as
    their value) makes the command foreign rather than letting an option value
    be mistaken for the script path."""
    index = 1
    while index < len(argv):
        arg = argv[index]
        if arg in _NO_ARG_FLAGS:
            index += 1
            continue
        if arg.startswith("-"):
            return None
        return index
    return None


def rewrite_owned_command(command, old_entry, new_entry):
    """Replace an exact script argv in a supported Python command; otherwise None.

    The rewritten command is `shlex.join(argv)` verbatim: re-quoting (e.g.
    swapping shlex's single quotes for double quotes) would change shell
    semantics for literal `$`/`$(...)` directory names, turning a safely
    quoted path into an active substitution."""
    if not isinstance(command, str):
        return None
    try:
        argv = shlex.split(command, posix=True)
    except ValueError:
        argv = []
    script_index = _script_index(argv) if _interpreter_command(argv) else None
    script = argv[script_index] if script_index is not None else ""
    if script.endswith((".backup", ".bak")):
        script_index = None
    if script and not os.path.isabs(script):
        script = os.path.abspath(script)
    # realpath: a line written through an alias spelling of the kit (a symlinked HOME) is ours.
    if script_index is not None and os.path.realpath(script) == os.path.realpath(old_entry):
        argv[script_index] = new_entry
        return shlex.join(argv)
    return None
