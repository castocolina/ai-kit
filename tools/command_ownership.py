"""Conservative ownership checks for ai-kit's status-line command."""

import os
import shlex


def _interpreter_command(argv):
    """Whether argv begins with a supported Python interpreter and script."""
    if len(argv) < 2 or any(token in {"|", ";", "&&", "||", ">", "<"} for token in argv):
        return False
    interpreter = os.path.basename(argv[0])
    suffix = interpreter[6:].replace(".", "") if interpreter.startswith("python") else ""
    return bool(suffix.isdigit())


def _script_index(argv):
    """Return the first positional script argument after Python flags."""
    return next((index for index, arg in enumerate(argv[1:], 1)
                 if not arg.startswith("-")), None)


def rewrite_owned_command(command, old_entry, new_entry):
    """Replace an exact script argv in a supported Python command; otherwise None."""
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
    if script_index is not None and os.path.normpath(script) == os.path.normpath(old_entry):
        argv[script_index] = new_entry
        rendered = shlex.join(argv)
        return rendered.replace("'", '"') if "'" in rendered and '"' not in rendered else rendered
    return None
