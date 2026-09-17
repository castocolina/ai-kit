"""SQLite refined-commands store (full Wave-1 schema, UPSERT writes).

Token/price figures on `refined_commands` are turn-level values duplicated
onto every step-row of one decomposed command. Consumers computing a session
or date total MUST deduplicate before summing, using this two-branch
identity:

- when `turn_id` is non-null: dedup on `(session_id, turn_id)`.
- when `turn_id` is null (e.g. rtk, which has no turn concept at all — see
  the 29,437 null-turn rtk rows this fallback exists for): dedup on
  `(session_id, raw_ref)`, NOT `(session_id, raw_ref, step_index)`. Every
  step of one decomposed command shares one `raw_ref` and the SAME
  turn-level `tokens_input`/`tokens_output`/`price`, so keying on the step
  as well would count each sibling's duplicated figures separately and
  multiply the total by the step count.

A plain `SELECT DISTINCT session_id, turn_id, tokens_input, tokens_output,
price` is NOT sufficient on its own: SQLite's `DISTINCT` treats two NULL
`turn_id` values as equal, so every null-turn row in a session collapses to
one row and silently under-sums every other null-turn row's figures — the
null-turn fallback above exists specifically to avoid that collapse.

`turnKey()` in `dashboard.py`'s embedded JavaScript is the canonical
implementation of this identity; `groupBySession()` there calls it rather
than constructing its own key. Any other consumer of this schema (a new
report, a chart aggregation) MUST reuse or replicate that same two-branch
rule, never a bare per-row `SUM` or a single-branch `DISTINCT`.
"""

from __future__ import annotations

import os
import sqlite3
import urllib.parse

from ai_kit_usage_metrics import paths

_INSERT_COLUMNS = (
    "raw_ref",
    "runtime",
    "session_id",
    "turn_id",
    "date",
    "timestamp",
    "model",
    "command_text",
    "family",
    "command_shape",
    "step_index",
    "step_count",
    "operator",
    "execution_certain",
    "resolved_cwd",
    "source_confidence",
    "tokens_input",
    "tokens_output",
    "price",
    "price_confidence",
    "rtk_input_tokens",
    "rtk_output_tokens",
    "rtk_saved_tokens",
    "rtk_savings_pct",
    "rtk_rewrote",
    "inferred_family",
    "inferred_confidence",
    "exec_duration_ms",
)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS refined_commands (
    id INTEGER PRIMARY KEY,
    raw_ref TEXT NOT NULL,
    runtime TEXT,
    session_id TEXT,
    turn_id TEXT,
    date TEXT,
    timestamp TEXT,
    model TEXT,
    command_text TEXT,
    family TEXT,
    command_shape TEXT,
    step_index INTEGER NOT NULL,
    step_count INTEGER,
    operator TEXT,
    execution_certain INTEGER,
    resolved_cwd TEXT,
    source_confidence TEXT,
    tokens_input INTEGER,
    tokens_output INTEGER,
    price REAL,
    price_confidence TEXT,
    rtk_input_tokens INTEGER,
    rtk_output_tokens INTEGER,
    rtk_saved_tokens INTEGER,
    rtk_savings_pct REAL,
    rtk_rewrote INTEGER,
    inferred_family TEXT,
    inferred_confidence TEXT,
    exec_duration_ms INTEGER,
    UNIQUE(raw_ref, step_index)
)
"""

_INSERT_SQL = """
INSERT INTO refined_commands (
    raw_ref, runtime, session_id, turn_id, date, timestamp, model,
    command_text, family, command_shape, step_index, step_count, operator,
    execution_certain, resolved_cwd, source_confidence, tokens_input,
    tokens_output, price, price_confidence, rtk_input_tokens,
    rtk_output_tokens, rtk_saved_tokens, rtk_savings_pct, rtk_rewrote,
    inferred_family, inferred_confidence, exec_duration_ms
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(raw_ref, step_index) DO UPDATE SET
    runtime=excluded.runtime,
    session_id=excluded.session_id,
    turn_id=excluded.turn_id,
    date=excluded.date,
    timestamp=excluded.timestamp,
    model=excluded.model,
    command_text=excluded.command_text,
    family=excluded.family,
    command_shape=excluded.command_shape,
    step_count=excluded.step_count,
    operator=excluded.operator,
    execution_certain=excluded.execution_certain,
    resolved_cwd=excluded.resolved_cwd,
    source_confidence=excluded.source_confidence,
    tokens_input=excluded.tokens_input,
    tokens_output=excluded.tokens_output,
    price=excluded.price,
    price_confidence=excluded.price_confidence,
    rtk_input_tokens=excluded.rtk_input_tokens,
    rtk_output_tokens=excluded.rtk_output_tokens,
    rtk_saved_tokens=excluded.rtk_saved_tokens,
    rtk_savings_pct=excluded.rtk_savings_pct,
    rtk_rewrote=excluded.rtk_rewrote,
    exec_duration_ms=excluded.exec_duration_ms
"""


def _ensure_private_dir(directory: str) -> None:
    os.makedirs(directory, mode=0o700, exist_ok=True)
    os.chmod(directory, 0o700)


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_TABLE)


def insert_commands(conn: sqlite3.Connection, rows: list[dict]) -> None:
    try:
        conn.execute("BEGIN")
        for row in rows:
            conn.execute(_INSERT_SQL, tuple(row.get(col) for col in _INSERT_COLUMNS))
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def update_inferred_family(
    conn: sqlite3.Connection,
    row_id: int,
    inferred_family: str | None,
    inferred_confidence: str | None,
) -> None:
    conn.execute(
        "UPDATE refined_commands SET inferred_family=?, inferred_confidence=? WHERE id=?",
        (inferred_family, inferred_confidence, row_id),
    )


def open_refined_db(env: dict) -> sqlite3.Connection:
    db_path = paths.refined_db_path(env)
    _ensure_private_dir(os.path.dirname(db_path))
    conn = sqlite3.connect(db_path)
    os.chmod(db_path, 0o600)
    ensure_schema(conn)
    return conn


def open_refined_db_readonly(env: dict) -> sqlite3.Connection:
    db_path = os.path.abspath(paths.refined_db_path(env))
    uri = f"file:{urllib.parse.quote(db_path)}?mode=ro"
    return sqlite3.connect(uri, uri=True)
