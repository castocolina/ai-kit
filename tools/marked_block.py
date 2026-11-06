"""Byte-preserving edits inside one marker-fenced block.

Shared by the global-rules rewrite (Phase 30) and the jev block (Phase 54). No file I/O here.
"""


def find_block(data: bytes, start: bytes, end: bytes) -> tuple[int, int] | str:
    """Return the (begin, finish) span strictly between the first start and the next end.

    A skip reason string instead: "no_block" (neither marker) or "one_marker".
    """
    at = data.find(start)
    if at < 0 and data.find(end) < 0:
        return "no_block"
    if at < 0 or data.find(end, at + len(start)) < 0:
        return "one_marker"
    begin = at + len(start)
    return begin, data.find(end, begin)


def replace_in_block(
    data: bytes, start: bytes, end: bytes, old: bytes, new: bytes
) -> tuple[bytes | None, str]:
    """Replace the first `old` inside the block; return (new bytes or None, reason).

    The reason is "replaced", "already" (the block holds `new` and not `old`),
    "no_sentence" (neither), or a find_block reason. Bytes outside the block never change.
    """
    span = find_block(data, start, end)
    if isinstance(span, str):
        return None, span
    begin, finish = span
    inner = data[begin:finish]
    at = inner.find(old)
    if at < 0:
        return (None, "already") if new in inner else (None, "no_sentence")
    edited = inner[:at] + new + inner[at + len(old) :]
    return data[:begin] + edited + data[finish:], "replaced"
