"""Host-neutral advisor core: stdlib-only, advice-only and fail-safe via its caller."""

import importlib
import json
import math
import os
import re
import shlex
import stat

MAX_STDIN_BYTES = 8 * 1024 * 1024
MAX_COMMAND_CHARS = 16384
NEWLINE_TOKEN = "\x00"
WRAPPERS = frozenset({"sudo", "env", "command", "time", "nohup", "xargs"})
KEYWORDS = frozenset({"if", "then", "elif", "else", "do", "while", "until", "!", "{"})
LANG_EXT_RE = re.compile(r"^[a-z0-9]{1,5}$")
READ_TOKEN_LIMIT = 10000
READ_LINE_LIMIT = 2000
READ_CAP_BYTES = 64 * 1024 * 1024
READ_CHUNK_BYTES = 1024 * 1024
_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_RANGE_RE = re.compile(r"^(\d+)(?:,(\d+))?p$")
_SUBST_RE = re.compile(r"^s(.).*\1.*\1[A-Za-z0-9]*$")


def unquote(token):
    """Remove one matching pair of surrounding quotes."""
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "'\"":
        return token[1:-1]
    return token


def _mask_escapes(text):
    """Mask escaped characters outside single quotes before non-POSIX lexing."""
    result = []
    quote = None
    index = 0
    while index < len(text):
        char = text[index]
        if quote == "'":
            result.append(char)
            if char == "'":
                quote = None
            index += 1
            continue
        if char == "\\":
            result.append("_")
            if index + 1 < len(text):
                result.append("_")
                index += 2
            else:
                index += 1
            continue
        result.append(char)
        if quote == '"' and char == '"':
            quote = None
        elif quote is None and char in "'\"":
            quote = char
        index += 1
    return "".join(result)


def _command_tokens(command):
    """Lex bounded shell text, returning [] for malformed quotes."""
    text = command[:MAX_COMMAND_CHARS]
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if "<<" in line and "<<<" not in line:
            # shortcut: commands after a heredoc line are unseen; upgrade if live checks miss.
            text = "".join(lines[:index + 1]).split("\n", 1)[0]
            break
    text = _mask_escapes(text).replace("\n", f" {NEWLINE_TOKEN} ")
    lexer = shlex.shlex(text, posix=False, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError:
        return []


def _separator(token):
    return token == NEWLINE_TOKEN or (
        bool(token) and all(char in "|&;()" for char in token))


def _command_words(tokens):
    """Yield command words and argument tokens at simple-command boundaries."""
    index = 0
    expect_command = True
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("#"):
            while index < len(tokens) and tokens[index] != NEWLINE_TOKEN:
                index += 1
            expect_command = True
        elif _separator(token):
            expect_command = True
        elif expect_command:
            while index < len(tokens) and (
                    _ASSIGN_RE.match(unquote(tokens[index]))
                    or unquote(tokens[index]) in KEYWORDS):
                index += 1
            while index < len(tokens) and unquote(tokens[index]) in WRAPPERS:
                index += 1
                while index < len(tokens) and unquote(tokens[index]).startswith("-"):
                    index += 1
                # shortcut: sudo -u root treats root as command; upgrade if live checks miss.
            if index < len(tokens) and not _separator(tokens[index]):
                yield os.path.basename(unquote(tokens[index])), tokens[index + 1:]
                expect_command = False
        else:
            index += 1
        index += 1


def installed_tools(env):
    """Return detected modern substitution names installed on this invocation's PATH."""
    detect = importlib.import_module("detect")
    result = detect.detect_substitutions(env.get("PATH", ""))
    return {pair["modern"] for pair in result["pairs"] if pair["installed"]}


def _arguments(tokens):
    return [unquote(token) for token in tokens]


def _grep_line():
    return ("ai-kit advice: use rg -n for line numbers, rg -l for matching file names, "
            "and --glob to filter files.")


def _cat_line(tokens):
    files = [token for token in _arguments(tokens) if not token.startswith("-")]
    extension = os.path.splitext(files[0])[1][1:].lower() if files else ""
    language = f" -l {extension}" if LANG_EXT_RE.fullmatch(extension) else ""
    return f"ai-kit advice: use Read or bat --plain --paging=never{language}."


def _sed_line(tokens):
    args = _arguments(tokens)
    range_requested = any(arg in ("-n", "--quiet", "--silent") for arg in args)
    for arg in args:
        match = _RANGE_RE.fullmatch(arg)
        if range_requested and match:
            start = int(match.group(1))
            end = int(match.group(2) or match.group(1))
            return "sed-range", (f"ai-kit advice: use bat --plain --paging=never -r "
                                 f"{start}:{end} or Read with offset {start} and limit "
                                 f"{max(1, end - start + 1)}.")
    if any(arg.startswith(("-i", "--in-place")) for arg in args) or any(
            _SUBST_RE.fullmatch(arg) for arg in args):
        return "sed-edit", "ai-kit advice: use sd for in-place edits and sd -p to preview."
    return None


def _advice_for(name, args, installed):
    if name == "grep" and "rg" in installed:
        return "grep", _grep_line()
    if name == "cat" and "bat" in installed:
        return "cat", _cat_line(args)
    if name == "find" and "fd" in installed:
        return "find", "ai-kit advice: use fd --type f --glob for file searches."
    if name == "sed":
        advice = _sed_line(args)
        if advice and ((advice[0] == "sed-range" and "bat" in installed)
                       or (advice[0] == "sed-edit" and "sd" in installed)):
            return advice
    return None


def bash_advice(command, installed):
    """Produce one fixed-template advice line per advice id in command order."""
    seen = set()
    advice = []
    for name, tail in _command_words(_command_tokens(command)):
        item = _advice_for(name, tail, installed)
        if item and item[0] not in seen:
            seen.add(item[0])
            advice.append(item)
    return advice


def read_report(path, offset, limit, installed):
    """Count a regular file with bounded, nonblocking reads and advise on large reads."""
    if (offset is not None or limit is not None or not isinstance(path, str)
            or not os.path.isabs(path)):
        return None
    try:
        if not stat.S_ISREG(os.stat(path).st_mode):
            return None
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError:
        return None
    size = 0
    newlines = 0
    last_byte = b""
    capped = False
    try:
        while size < READ_CAP_BYTES:
            chunk = os.read(fd, min(READ_CHUNK_BYTES, READ_CAP_BYTES - size))
            if not chunk:
                break
            size += len(chunk)
            newlines += chunk.count(b"\n")
            last_byte = chunk[-1:]
        capped = size >= READ_CAP_BYTES
    except OSError:
        return None
    finally:
        os.close(fd)
    lines = newlines + int(bool(size) and last_byte != b"\n")
    tokens = math.ceil(size / 4)
    if not capped and tokens <= READ_TOKEN_LIMIT and lines <= READ_LINE_LIMIT:
        return None
    marker = "≥" if capped else ""
    line = (f"ai-kit advice: large Read: {marker}{size} bytes, {marker}{lines} lines, "
            f"≈{marker}{tokens} tokens (estimate: bytes / 4). This note arrives with this "
            "read's result, so it applies to your next read: read a range (Read with offset "
            "and limit)")
    if "bat" in installed:
        line += ", or bat --plain --paging=never -r 1:2000 FILE"
    return "read-large", line + "."


def event_from_claude(payload, kind):
    """Map a Claude payload to the host-neutral advisor event."""
    tool_input = payload.get("tool_input") if isinstance(payload, dict) else None
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    tool = payload.get("tool_name") if isinstance(payload, dict) else None
    return {"kind": kind, "tool": tool.lower() if isinstance(tool, str) else None,
            "command": tool_input.get("command"), "path": tool_input.get("file_path"),
            "offset": tool_input.get("offset"), "limit": tool_input.get("limit"),
            "session_id": payload.get("session_id") if isinstance(payload, dict) else None,
            "call_id": payload.get("tool_use_id") if isinstance(payload, dict) else None}


def advise(event, env):
    """Build advice for a host-neutral event, or None when no advice applies."""
    if not isinstance(event, dict):
        return None
    installed = installed_tools(env)
    if event.get("tool") == "bash":
        lines = bash_advice(event.get("command"), installed)
        return "\n".join(line for _identity, line in lines) or None
    if event.get("tool") == "read":
        result = read_report(event.get("path"), event.get("offset"), event.get("limit"), installed)
        return result[1] if result else None
    return None


def run_claude(raw, kind, env):
    """Parse a bounded Claude JSON payload and return advice, failing silently."""
    if len(raw) > MAX_STDIN_BYTES:
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    return advise(event_from_claude(payload, kind), env)
