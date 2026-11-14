"""Byte-preserving reads of one marker-fenced block.

Used by the global-rules rewrite (Phase 30). No file I/O here.
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
