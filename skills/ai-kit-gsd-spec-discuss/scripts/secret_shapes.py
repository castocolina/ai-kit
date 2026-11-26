"""Distinctive key shapes shared by ai-kit's secret scanners. stdlib only.

Every copy of this file is byte-identical: a skill that cannot import across skill folders
holds its own copy, and a test compares each copy, and the runner template's KEY_SHAPES
line, with this one. Each source is case-sensitive, has no flag and no capture group, and
guards its prefix with an explicit ASCII lookbehind (a JSON or percent escape before the
key counts as a boundary), so Python and JavaScript read it the
same way. detect names the shapes found and never returns the matched text; redact
replaces every match with the caller's marker, overlapping matches as one, and returns
text with no match unchanged.
"""

import re

# Provider rows first and the generic sk-/rk- row last: detect names shapes in this order.
# redact merges the matches of every row, so the order does not change what it removes.
SHAPES = (
    (
        "github_token",
        r"(?:(?<![A-Za-z0-9_])|(?<=\\[nrt])|(?<=%[0-9A-Fa-f]{2}))"
        r"gh[pousr]_[A-Za-z0-9]{20,}",
    ),
    (
        "github_pat",
        r"(?:(?<![A-Za-z0-9_])|(?<=\\[nrt])|(?<=%[0-9A-Fa-f]{2}))"
        r"github_pat_[A-Za-z0-9_]{20,}",
    ),
    (
        "google_api_key",
        r"(?:(?<![A-Za-z0-9_])|(?<=\\[nrt])|(?<=%[0-9A-Fa-f]{2}))"
        r"AIza[0-9A-Za-z_-]{20,}",
    ),
    (
        "slack_token",
        r"(?:(?<![A-Za-z0-9_])|(?<=\\[nrt])|(?<=%[0-9A-Fa-f]{2}))"
        r"(?:xox[abposre]|xapp|xwfp)-[A-Za-z0-9_-]{12,}",
    ),
    (
        "pem_private_key",
        r"-----BEGIN [A-Z0-9 ]+-----"
        r"(?:[\s\S]{0,16384}?-----END [A-Z0-9 ]+-----|[A-Za-z0-9+/=\r\n]{0,16384})?",
    ),
    (
        "aws_access_key_id",
        r"(?:(?<![A-Za-z0-9_])|(?<=\\[nrt])|(?<=%[0-9A-Fa-f]{2}))"
        r"(?:AKIA|ASIA|ABIA|ACCA)[A-Z0-9]{16}",
    ),
    (
        "gitlab_token",
        r"(?:(?<![A-Za-z0-9_])|(?<=\\[nrt])|(?<=%[0-9A-Fa-f]{2}))"
        r"(?:glpat|gloas|gldt|glrtr?|glcbt|glptt|glft|glimt|glagent|glwt"
        r"|glsoat|glffct)-[A-Za-z0-9_-]{16,}",
    ),
    (
        "xai_api_key",
        r"(?:(?<![A-Za-z0-9_])|(?<=\\[nrt])|(?<=%[0-9A-Fa-f]{2}))"
        r"xai-[A-Za-z0-9]{16,}",
    ),
    (
        "jwt",
        r"(?:(?<![A-Za-z0-9_-])|(?<=\\[nrt])|(?<=%[0-9A-Fa-f]{2}))"
        r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
    ),
    (
        "stripe_key",
        r"(?:(?<![A-Za-z0-9_])|(?<=\\[nrt])|(?<=%[0-9A-Fa-f]{2}))"
        r"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}",
    ),
    (
        "huggingface_token",
        r"(?:(?<![A-Za-z0-9_])|(?<=\\[nrt])|(?<=%[0-9A-Fa-f]{2}))"
        r"hf_[A-Za-z0-9]{30,}",
    ),
    (
        "npm_token",
        r"(?:(?<![A-Za-z0-9_])|(?<=\\[nrt])|(?<=%[0-9A-Fa-f]{2}))"
        r"npm_[A-Za-z0-9]{36,}",
    ),
    (
        "groq_key",
        r"(?:(?<![A-Za-z0-9_])|(?<=\\[nrt])|(?<=%[0-9A-Fa-f]{2}))"
        r"gsk_[A-Za-z0-9]{20,}",
    ),
    (
        "sk_rk_key",
        r"(?:(?<![A-Za-z0-9_])|(?<=\\[nrt])|(?<=%[0-9A-Fa-f]{2}))"
        r"(?:sk|rk)-[A-Za-z0-9_-]{8,}",
    ),
)

_COMPILED = tuple((name, re.compile(source)) for name, source in SHAPES)


def detect(text: str) -> list[str]:
    """The names of the shapes found in `text`, each once, in table order; never the match."""
    return [name for name, pattern in _COMPILED if pattern.search(text)]


def redact(text: str, marker: str) -> str:
    """`text` with every match replaced by `marker`, taken literally. Every shape is matched
    on the original text and overlapping matches merge into one span, so no row cuts into a
    token another row matches; text outside the spans is kept byte for byte."""
    spans = sorted(m.span() for _name, pattern in _COMPILED for m in pattern.finditer(text))
    merged: list[list[int]] = []
    for start, end in spans:
        if merged and start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    parts: list[str] = []
    last = 0
    for start, end in merged:
        parts.append(text[last:start])
        parts.append(marker)
        last = end
    parts.append(text[last:])
    return "".join(parts)
