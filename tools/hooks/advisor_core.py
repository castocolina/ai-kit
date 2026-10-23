"""Host-neutral advisor core: stdlib-only, advice-only and fail-safe via its caller."""

import contextlib
import fcntl
import hashlib
import importlib
import json
import math
import os
import re
import shlex
import stat
import sys

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
REPEAT_EVERY = 10
MAX_CALL_RECORDS = 256
OUTPUT_LINE_LIMIT = 200
STATE_PATTERNS = ("*.json", ".advisor-*.tmp")
LOCK_NAME = ".advisor.lock"
SHOWN = "*shown"
LEGACY_TO_MODERN = {"grep": "rg", "cat": "bat", "sed-range": "bat",
                    "sed-edit": "sd", "find": "fd"}
LEGACY_NAMES = {"grep": "grep", "cat": "cat", "sed-range": "sed",
                "sed-edit": "sed", "find": "find"}
_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_RANGE_RE = re.compile(r"^(\d+)(?:,(\d+))?p$")


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
        tokens = list(lexer)
    except ValueError:
        return []
    merged = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if _ASSIGN_RE.match(token) and token.count("'") % 2:
            while token.count("'") % 2 and index + 1 < len(tokens):
                index += 1
                token += " " + tokens[index]
        merged.append(token)
        index += 1
    return merged


def _separator(token):
    return token == NEWLINE_TOKEN or (
        bool(token) and all(char in "|&;()" for char in token))


def _command_words(tokens):
    """Yield command words and arguments bounded by each shell separator."""
    # pylint: disable=too-many-branches
    index = 0
    expect_command = True
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("#"):
            while index < len(tokens) and tokens[index] != NEWLINE_TOKEN:
                index += 1
            expect_command = True
            continue
        if _separator(token):
            expect_command = True
            index += 1
            continue
        if expect_command:
            while index < len(tokens) and unquote(tokens[index]) in KEYWORDS:
                index += 1
            while index < len(tokens):
                word = unquote(tokens[index])
                if _ASSIGN_RE.match(word):
                    index += 1
                elif word in WRAPPERS:
                    index += 1
                    while index < len(tokens) and unquote(tokens[index]).startswith("-"):
                        index += 1
                    if index < len(tokens) and unquote(tokens[index]) in ("-u", "-g"):
                        index += 1
                else:
                    break
            if index < len(tokens) and not _separator(tokens[index]):
                name = os.path.basename(unquote(tokens[index]))
                end = index + 1
                while (end < len(tokens) and not _separator(tokens[end])
                       and not tokens[end].startswith("#")):
                    end += 1
                yield name, tokens[index + 1:end]
                expect_command = False
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


def _is_substitution(arg):
    """Recognize sed s<delimiter>... forms with a linear delimiter scan."""
    if len(arg) < 4 or arg[0] != "s":
        return False
    delimiter = arg[1]
    found = 0
    escaped = False
    for char in arg[2:]:
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == delimiter:
            found += 1
            if found == 2:
                return True
    return False


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
            _is_substitution(arg) for arg in args):
        return "sed-edit", "ai-kit advice: use sd for in-place edits and sd -p to preview."
    return None


def _advice_for(name, args, installed):
    if name == "grep" and "rg" in installed:
        return "grep", _grep_line()
    if name == "cat" and "bat" in installed:
        return "cat", _cat_line(args)
    if name == "find" and "fd" in installed:
        return "find", "ai-kit advice: use fd --type f --glob for file searches."
    if name == "sed" and ("sd" in installed or "bat" in installed):
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


def _read_counts(path):
    """Read a regular path in bounded chunks, returning (bytes, newlines, last, capped)."""
    try:
        if not stat.S_ISREG(os.stat(path).st_mode):
            return None
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError:
        return None
    size = 0
    newlines = 0
    last_byte = b""
    try:
        while size < READ_CAP_BYTES:
            chunk = os.read(fd, min(READ_CHUNK_BYTES, READ_CAP_BYTES - size))
            if not chunk:
                break
            size += len(chunk)
            newlines += chunk.count(b"\n")
            last_byte = chunk[-1:]
        return size, newlines, last_byte, size >= READ_CAP_BYTES
    except OSError:
        return None
    finally:
        os.close(fd)


def read_report(path, offset, limit, installed):
    """Count a regular file with bounded, nonblocking reads and advise on large reads."""
    if (offset is not None or limit is not None or not isinstance(path, str)
            or not os.path.isabs(path)):
        return None
    counted = _read_counts(path)
    if counted is None:
        return None
    size, newlines, last_byte, capped = counted
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


def output_size(texts):
    """Count output lines and characters across texts."""
    valid = [text for text in texts if isinstance(text, str)]
    chars = sum(map(len, valid))
    lines = sum(text.count("\n") + int(bool(text) and not text.endswith("\n"))
                for text in valid)
    return lines, chars


def event_from_claude(payload, kind):
    """Map a Claude payload to the host-neutral advisor event."""
    tool_input = payload.get("tool_input") if isinstance(payload, dict) else None
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    tool = payload.get("tool_name") if isinstance(payload, dict) else None
    event = {"kind": kind, "tool": tool.lower() if isinstance(tool, str) else None,
             "command": tool_input.get("command"), "path": tool_input.get("file_path"),
             "offset": tool_input.get("offset"), "limit": tool_input.get("limit"),
             "session_id": payload.get("session_id") if isinstance(payload, dict) else None,
             "call_id": payload.get("tool_use_id") if isinstance(payload, dict) else None}
    if kind == "reminder":
        response = payload.get("tool_response") if isinstance(payload, dict) else None
        response = response if isinstance(response, dict) else {}
        event["output_lines"], event["output_chars"] = output_size(
            (response.get("stdout"), response.get("stderr")))
    return event


def _fresh_state(session_id):
    return {"session": session_id, "counts": {}, "calls": {}}


def _valid_state(state, session_id):
    if not isinstance(state, dict) or state.get("session") != session_id:
        return False
    counts, calls = state.get("counts"), state.get("calls")
    return (isinstance(counts, dict)
            and all(isinstance(value, int) and not isinstance(value, bool) and value >= 0
                    for value in counts.values())
            and isinstance(calls, dict)
            and all(isinstance(key, str) and isinstance(value, list)
                    and all(isinstance(item, str) for item in value)
                    for key, value in calls.items()))


def call_key(event):
    """Hash a host call id; events without one are intentionally uncorrelated."""
    call_id = event.get("call_id")
    if not isinstance(call_id, str) or not call_id:
        return None
    return hashlib.sha256(call_id.encode("utf-8")).hexdigest()[:16]


def count_due(state, advice_id):
    """Increment one counter and show its first and every tenth repeat."""
    count = state["counts"].get(advice_id, 0) + 1
    state["counts"][advice_id] = count
    return count == 1 or count % REPEAT_EVERY == 1


def with_state(env, session_id, update):
    """Run one state update under a per-session flock and atomic private write."""
    helpers = importlib.import_module("precompact_core")
    if not helpers.safe_session_id(session_id):
        return update(_fresh_state(session_id))
    directory = helpers.private_dir(env, name="advisor")
    if directory is None:
        return update(_fresh_state(session_id))
    flags = os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        fd = os.open(os.path.join(directory, LOCK_NAME), flags, 0o600)
    except OSError:
        return update(_fresh_state(session_id))
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        helpers.sweep(directory, patterns=STATE_PATTERNS)
        path = os.path.join(directory, f"{session_id}.json")
        try:
            state_fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            with os.fdopen(state_fd, encoding="utf-8") as handle:
                loaded = json.load(handle)
            state = loaded if _valid_state(loaded, session_id) else _fresh_state(session_id)
        except (OSError, ValueError):
            state = _fresh_state(session_id)
        result = update(state)
        state["calls"] = dict(list(state["calls"].items())[-MAX_CALL_RECORDS:])
        helpers.write_private(directory, f"{session_id}.json",
                              json.dumps(state, separators=(",", ":")), ".advisor-")
        return result
    except OSError:
        return update(_fresh_state(session_id))
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _candidate_advice(event, installed):
    if event.get("tool") == "bash":
        return bash_advice(event.get("command"), installed)
    if event.get("tool") == "read":
        item = read_report(event.get("path"), event.get("offset"), event.get("limit"), installed)
        return [item] if item else []
    return []


def advise(event, env):
    """Build frequency-limited advice for advisor or reminder events."""
    # pylint: disable=too-many-branches
    if not isinstance(event, dict):
        return None
    kind = event.get("kind", "advisor")
    if kind not in ("advisor", "reminder"):
        return None
    installed = installed_tools(env)
    if kind == "reminder" and (event.get("tool") != "bash"
                               or event.get("output_lines", 0) <= 0):
        return None
    candidates = _candidate_advice(event, installed)
    if not candidates:
        return None
    key = call_key(event)

    def update(state):
        calls = state["calls"]
        record = calls.get(key, []) if key is not None else []
        if key is not None and key not in calls:
            calls[key] = record
        due = []
        for advice_id, line in candidates:
            counted = key is None or advice_id not in record
            if kind == "advisor":
                if counted:
                    if key is not None:
                        record.append(advice_id)
                    if count_due(state, advice_id):
                        due.append((advice_id, line))
            else:
                id_due = False
                if counted:
                    if key is not None:
                        record.append(advice_id)
                    id_due = count_due(state, advice_id)
                big_due = (count_due(state, "big:" + advice_id)
                           if event.get("output_lines", 0) > OUTPUT_LINE_LIMIT else False)
                if id_due or big_due:
                    due.append((advice_id, line))
        if not due:
            return None
        already_shown = key is not None and SHOWN in record
        if event.get("single_block") and already_shown:
            return None
        if kind == "reminder":
            tokens = math.ceil(event.get("output_chars", 0) / 4)
            line = (f"ai-kit reminder: that command printed {event['output_lines']} lines, "
                    f"about {tokens} tokens; next time use "
                    f"{', '.join(LEGACY_TO_MODERN[item[0]] for item in due)} instead of "
                    f"{', '.join(LEGACY_NAMES[item[0]] for item in due)}.")
        else:
            line = "\n".join(item[1] for item in due)
        if (event.get("single_block") and event.get("output_lines", 0) > OUTPUT_LINE_LIMIT):
            tokens = math.ceil(event.get("output_chars", 0) / 4)
            line += (f"\nai-kit reminder: that command printed {event['output_lines']} lines, "
                     f"about {tokens} tokens.")
        if key is not None:
            record.append(SHOWN)
        return line

    return with_state(env, event.get("session_id"), update)


def event_from_pi(data):
    """Map a pi tool_result payload to the host-neutral advisor event."""
    if not isinstance(data, dict):
        return None
    tool_input = data.get("input")
    if not isinstance(tool_input, dict):
        return None
    tool_name = data.get("toolName")
    tool = tool_name.lower() if isinstance(tool_name, str) else None
    cwd = data.get("cwd")
    path = tool_input.get("path") if tool_input else None
    if (isinstance(path, str) and not os.path.isabs(path)
            and isinstance(cwd, str) and os.path.isabs(cwd)):
        path = os.path.join(cwd, path)
    content = data.get("content")
    texts = [block.get("text", "") for block in content
             if isinstance(block, dict) and block.get("type") == "text"
             and isinstance(block.get("text"), str)] if isinstance(content, list) else []
    text = data.get("text") if isinstance(data.get("text"), str) else "\n".join(texts)
    event = {"kind": data.get("kind", "advisor"), "tool": tool,
             "command": tool_input.get("command") if tool_input else None,
             "path": path, "offset": tool_input.get("offset") if tool_input else None,
             "limit": tool_input.get("limit") if tool_input else None,
             "call_id": data.get("toolCallId"), "session_id": data.get("sessionId"),
             "single_block": True}
    details = data.get("details")
    truncation = details.get("truncation") if isinstance(details, dict) else None
    if (isinstance(truncation, dict) and truncation.get("truncated") is True
            and isinstance(truncation.get("totalLines"), int)
            and isinstance(truncation.get("totalBytes"), int)):
        event["output_lines"] = truncation["totalLines"]
        event["output_chars"] = truncation["totalBytes"]
    else:
        event["output_lines"], event["output_chars"] = output_size([text])
    return event


def main(argv):
    """The pi adapter entry: bounded JSON in, one fail-open JSON object out."""
    from claude_session_start import read_stdin  # pylint: disable=import-outside-toplevel
    result = {}
    if argv == ["pi"]:
        raw = read_stdin(MAX_STDIN_BYTES)
        if len(raw) <= MAX_STDIN_BYTES:
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                data = None
            if isinstance(data, dict):
                advice = advise(event_from_pi(data), os.environ)
                if isinstance(advice, str) and advice:
                    result = {"text": advice}
    sys.stdout.write(json.dumps(result))
    sys.stdout.flush()
    return 0


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


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
    from claude_session_start import _fail_open  # pylint: disable=import-outside-toplevel
    sys.excepthook = _fail_open
    raise SystemExit(main(sys.argv[1:]))
