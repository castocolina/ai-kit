"""Quote-aware mechanical decomposer for shell command text."""

from __future__ import annotations

from dataclasses import dataclass

_OPENERS = {
    "if": "fi",
    "case": "esac",
    "for": "done",
    "while": "done",
    "until": "done",
    "select": "done",
}

_CONTROL_FLOW_FIRST = frozenset(_OPENERS)


@dataclass
class ScanResult:
    """One left-to-right scan of a command string."""

    segments: list[tuple[str, str | None]]
    unterminated_quote: bool
    has_unsupported_shape: bool


def classify_segment(segment_text: str) -> str:
    """Return `control_flow_script` or `simple` from the segment's first token."""
    stripped = segment_text.strip()
    if not stripped:
        return "simple"
    first = stripped.split(None, 1)[0]
    if first in _CONTROL_FLOW_FIRST:
        return "control_flow_script"
    return "simple"


def decompose(command_text: str) -> list[dict]:
    """Split command text into ordered step dicts.

    `unclassified` is decided here from the scan flags, never by
    `classify_segment`.
    """
    if not command_text:
        return []
    scan = scan_command(command_text)
    if scan.unterminated_quote or scan.has_unsupported_shape:
        return [
            {
                "step_index": 0,
                "text": command_text,
                "operator": None,
                "command_shape": "unclassified",
            }
        ]
    return [
        {
            "step_index": index,
            "text": text,
            "operator": operator,
            "command_shape": classify_segment(text),
        }
        for index, (text, operator) in enumerate(scan.segments)
    ]


def scan_command(command_text: str) -> ScanResult:
    """Single left-to-right character scan producing segments and flags."""
    return _Scanner(command_text).run()


class _Scanner:
    """Walk command text tracking quotes, control-flow depth, and operators."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.n = len(text)
        self.i = 0
        self.in_single = False
        self.in_double = False
        self.escaped = False
        self.closers: list[str] = []
        self.segments: list[tuple[str, str | None]] = []
        self.buf: list[str] = []
        self.preceding: str | None = None
        self.has_unsupported = False
        self.word: list[str] = []
        self.seen_non_ws = False

    def run(self) -> ScanResult:
        while self.i < self.n:
            self._step()
        self._flush_word()
        self._emit_remaining()
        return ScanResult(
            segments=self.segments,
            unterminated_quote=self.in_single or self.in_double,
            has_unsupported_shape=self.has_unsupported,
        )

    def _step(self) -> None:
        char = self.text[self.i]
        if self.escaped:
            # Only set inside double quotes; single quotes never honor `\`.
            self.buf.append(char)
            self.escaped = False
            self.i += 1
            return
        if self.in_single:
            self._step_single(char)
            return
        if self.in_double:
            self._step_double(char)
            return
        self._step_unquoted(char)

    def _step_single(self, char: str) -> None:
        # Inside single quotes, `\` is a LITERAL backslash, never an escape —
        # the one concrete divergence from JSON-string escaping rules.
        self.buf.append(char)
        if char == "'":
            self.in_single = False
        self.i += 1

    def _step_double(self, char: str) -> None:
        self.buf.append(char)
        if char == "\\":
            self.escaped = True
        elif char == '"':
            self.in_double = False
        self.i += 1

    def _step_unquoted(self, char: str) -> None:
        if char in "'\"":
            self._begin_quote(single=char == "'")
        elif char == "&":
            self._consume_ampersand()
        elif char == "|":
            self._consume_pipe()
        elif char == ";":
            self._consume_semicolon()
        elif char == "<":
            self._consume_lt()
        elif char == "$":
            self._consume_dollar()
        elif char == "`":
            self.has_unsupported = True
            self._append_raw("`")
        elif char == "(" and not self.seen_non_ws:
            self.has_unsupported = True
            self._append_raw("(")
        elif char.isspace():
            self._flush_word()
            self.buf.append(char)
            self.i += 1
        elif char.isalnum() or char == "_":
            self.word.append(char)
            self.buf.append(char)
            self.seen_non_ws = True
            self.i += 1
        else:
            self._flush_word()
            self.buf.append(char)
            self.seen_non_ws = True
            self.i += 1

    def _begin_quote(self, *, single: bool) -> None:
        self.word.clear()
        self.buf.append("'" if single else '"')
        self.seen_non_ws = True
        if single:
            self.in_single = True
        else:
            self.in_double = True
        self.i += 1

    def _consume_ampersand(self) -> None:
        self._flush_word()
        nxt = self.text[self.i + 1] if self.i + 1 < self.n else ""
        if nxt == "&":
            if self.closers:
                self.buf.append("&&")
                self.seen_non_ws = True
            else:
                self._split_on("&&")
            self.i += 2
            return
        self._append_raw("&")

    def _consume_pipe(self) -> None:
        self._flush_word()
        nxt = self.text[self.i + 1] if self.i + 1 < self.n else ""
        if nxt == "|":
            self.has_unsupported = True
            self.buf.append("||")
            self.seen_non_ws = True
            self.i += 2
            return
        if self.closers:
            self._append_raw("|")
            return
        self._split_on("|")
        self.i += 1

    def _consume_semicolon(self) -> None:
        self._flush_word()
        if self.closers:
            self._append_raw(";")
            return
        self._split_on(";")
        self.i += 1

    def _consume_lt(self) -> None:
        nxt = self.text[self.i + 1] if self.i + 1 < self.n else ""
        if nxt != "<":
            self._flush_word()
            self._append_raw("<")
            return
        self.has_unsupported = True
        self._flush_word()
        self.buf.append("<<")
        self.i += 2
        if self.i < self.n and self.text[self.i] in "-~":
            self.buf.append(self.text[self.i])
            self.i += 1
        self.seen_non_ws = True

    def _consume_dollar(self) -> None:
        nxt = self.text[self.i + 1] if self.i + 1 < self.n else ""
        if nxt == "(":
            self.has_unsupported = True
            self._flush_word()
            self.buf.append("$(")
            self.i += 2
            self.seen_non_ws = True
            return
        self._flush_word()
        self._append_raw("$")

    def _append_raw(self, token: str) -> None:
        self.buf.append(token)
        self.seen_non_ws = True
        self.i += len(token)

    def _split_on(self, operator: str) -> None:
        text = "".join(self.buf).strip()
        self.buf.clear()
        if text:
            self.segments.append((text, self.preceding))
        self.preceding = operator
        self.seen_non_ws = False

    def _flush_word(self) -> None:
        word = "".join(self.word)
        self.word.clear()
        if not word:
            return
        closer = _OPENERS.get(word)
        if closer is not None:
            self.closers.append(closer)
            return
        if self.closers and word == self.closers[-1]:
            self.closers.pop()

    def _emit_remaining(self) -> None:
        text = "".join(self.buf).strip()
        self.buf.clear()
        if text:
            self.segments.append((text, self.preceding))
