"""Offline pattern-mining pass over opaque refined_commands rows.

normalize_skeleton is intentionally lossy/approximate: it exists to group
STRUCTURALLY similar commands, not to be a second parser.
"""

from __future__ import annotations

import re
import sqlite3

from ai_kit_usage_metrics import family, refined_store

# A deliberately conservative default (mine any shape repeated at least
# twice), not a researched constant. Overridable per-call because the right
# threshold depends on how much history a given install has accumulated,
# which this module has no way to know in advance.
DEFAULT_MIN_OCCURRENCES = 2

_VAR_RE = re.compile(r"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?")
_QUOTE_RE = re.compile(r"\"[^\"]*\"|'[^']*'")

_KEYWORDS = frozenset(
    {
        "for",
        "in",
        "do",
        "done",
        "if",
        "then",
        "elif",
        "else",
        "fi",
        "while",
        "until",
        "select",
        "case",
        "esac",
    }
)
_OPERATORS = frozenset({";", "&&", "||", "|"})
_COMMAND_STARTERS = frozenset({"do", "then"})
_PLACEHOLDERS = frozenset({"<VAR>", "<STR>", "<ARG>"})
_OPAQUE_SHAPES = ("control_flow_script", "unclassified")
_CURATED_MEMBERS = {part for pair in family.CURATED_SUBSTITUTIONS for part in pair}
_GLUE_BEFORE = {";"}


def normalize_skeleton(command_text: str) -> str:
    """Reduce a command to a structural skeleton for grouping similar shapes."""
    text = _VAR_RE.sub("<VAR>", command_text or "")
    text = _QUOTE_RE.sub("<STR>", text)
    tokens = _tokenize(text)
    rewritten = _rewrite_tokens(tokens)
    return _join_tokens(rewritten)


def _tokenize(text: str) -> list[str]:
    pieces: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("&&", i):
            pieces.append(" && ")
            i += 2
        elif text.startswith("||", i):
            pieces.append(" || ")
            i += 2
        elif text[i] in ";|":
            pieces.append(f" {text[i]} ")
            i += 1
        else:
            pieces.append(text[i])
            i += 1
    return "".join(pieces).split()


def _rewrite_tokens(tokens: list[str]) -> list[str]:
    rewritten: list[str] = []
    expect_command_name = True
    after_for = False
    for token in tokens:
        if token in _PLACEHOLDERS:
            rewritten.append(token)
            continue
        if after_for:
            rewritten.append("<VAR>")
            after_for = False
            expect_command_name = False
            continue
        if token == "for":
            rewritten.append(token)
            after_for = True
            expect_command_name = False
            continue
        if token in _KEYWORDS:
            rewritten.append(token)
            expect_command_name = token in _COMMAND_STARTERS
            continue
        if token in _OPERATORS:
            rewritten.append(token)
            expect_command_name = True
            continue
        if expect_command_name and not token.startswith("-"):
            rewritten.append(token)
            expect_command_name = False
            continue
        rewritten.append("<ARG>")
        if not token.startswith("-"):
            expect_command_name = False
    return rewritten


def _join_tokens(tokens: list[str]) -> str:
    if not tokens:
        return ""
    parts = [tokens[0]]
    for token in tokens[1:]:
        if token in _GLUE_BEFORE:
            parts.append(token)
        else:
            parts.append(" ")
            parts.append(token)
    return "".join(parts)


def mine_recurring_shapes(rows: list[dict], min_occurrences: int) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        skeleton = normalize_skeleton(row.get("command_text") or "")
        groups.setdefault(skeleton, []).append(row)
    return {skel: grouped for skel, grouped in groups.items() if len(grouped) >= min_occurrences}


def infer_family_for_group(
    skeleton: str, sample_command_text: str
) -> tuple[str | None, str | None]:
    del skeleton
    candidates = []
    for token in (sample_command_text or "").split():
        if token in _CURATED_MEMBERS and token not in _KEYWORDS and token not in candidates:
            candidates.append(token)
    if len(candidates) != 1:
        return (None, None)
    return (family.family_of(candidates[0]), "LOW")


def run_classification(
    conn: sqlite3.Connection,
    min_occurrences: int = DEFAULT_MIN_OCCURRENCES,
) -> dict:
    try:
        conn.execute("BEGIN")
        conn.execute(
            "UPDATE refined_commands SET inferred_family=NULL, inferred_confidence=NULL "
            "WHERE command_shape IN (?, ?)",
            _OPAQUE_SHAPES,
        )
        fetched = conn.execute(
            "SELECT id, command_text, command_shape FROM refined_commands "
            "WHERE command_shape IN (?, ?)",
            _OPAQUE_SHAPES,
        ).fetchall()
        rows = [
            {"id": row_id, "command_text": command_text, "command_shape": shape}
            for row_id, command_text, shape in fetched
        ]
        groups = mine_recurring_shapes(rows, min_occurrences)
        reclassified = 0
        for skeleton, grouped in groups.items():
            inferred, confidence = infer_family_for_group(
                skeleton, grouped[0].get("command_text") or ""
            )
            if inferred is None:
                continue
            for row in grouped:
                refined_store.update_inferred_family(
                    conn, row["id"], inferred, confidence
                )
                reclassified += 1
        conn.commit()
        return {"groups_found": len(groups), "rows_reclassified": reclassified}
    except Exception:
        conn.rollback()
        raise
