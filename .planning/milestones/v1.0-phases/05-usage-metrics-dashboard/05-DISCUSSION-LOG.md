# Phase 5: Usage Metrics Dashboard - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-08
**Phase:** 5-Usage Metrics Dashboard
**Areas discussed:** Raw store format/location, cwd-resolution scope per runtime, Overlap with rtk's own tee logs, Dashboard export/import mechanism

---

## Raw store format/location

**Trade-off analysis presented:** JSONL append-only per runtime vs. a shared
SQLite store for raw capture.

**User's first answer:** pushed back on the framing of the question itself,
clarifying the real architecture: a single periodic script ingests raw
session data from all 4 runtimes, runs one or several processing passes, and
writes a final ready-to-query result that the dashboard reads from — there
are no concurrent writers, so SQLite's concurrency limitation isn't actually
a concern for the *final* store.

| Option | Description | Selected |
|--------|-------------|----------|
| JSONL append-only per runtime | Verbatim, lossless, one runtime's failure never breaks another's file | ✓ |
| Shared SQLite | Single store, but a concurrency question that turned out not to apply | |

**User's choice:** JSONL per runtime (recommended option).

**Follow-up:** confirmed the two-tier split explicitly — raw = JSONL
per-runtime (verbatim, append-only), refined/final = SQLite (structured,
queryable by the dashboard). User confirmed: no concurrency problem either
way, since one script runs the whole pipeline.

**Location:** `~/.local/share/ai-kit/usage-metrics/{raw,refined}/`
(recommended) — follows the XDG pattern already used by `rtk` and opencode
on this machine.

---

## cwd-resolution scope per runtime

**Trade-off analysis presented:** apply the chronological cwd-resolution
state machine only where needed (opencode/Codex/Cursor, which lack
per-command cwd) vs. uniformly across all 4 runtimes (including Claude Code,
which already has per-message cwd for free — live-verified in a real
session JSONL).

| Option | Description | Selected |
|--------|-------------|----------|
| Apply only where needed | Claude Code just reads its existing cwd field; the other 3 runtimes get the state machine | ✓ |
| Apply uniformly to all 4 | Simpler mental model, but redundant work for Claude Code | |

**User's choice:** apply only where needed (recommended option).

---

## Overlap with rtk's own tee logs

**Trade-off analysis presented:** ingest `rtk`'s `history.db` (commands +
precomputed tokens) as a complementary raw source, but exclude its
failure-only tee logs and any runtime's OTEL telemetry.

| Option | Description | Selected |
|--------|-------------|----------|
| history.db yes / tee and OTEL no | Keeps scope tight to structured, already-tokenized data | |
| Also include tee logs | User overrode this half of the recommendation | ✓ |

**User's choice:** include both `history.db` and tee logs as raw sources.
OTEL telemetry from any runtime stays excluded (external export, violates
the local-only constraint).

**Ingestion frequency:** once a day (recommended) — consistent with the
single-script, no-concurrent-writers design already confirmed.

**Mid-turn message from user:** proposed that `rtk`'s `tee.max_files`
(currently 20) be raised to ~100, and that this tuning should be surfaced as
a **new Config Doctor (Phase 4) check row**, not just a Phase 5 concern —
more retained tee entries also means more data available to Phase 5's
pipeline. Cross-phase amendment made: added as Open Research Question #7 to
`04-CONTEXT.md` (commit `9aaf107`) — a candidate 13th-ish cross-runtime
Checks Catalog row (`rtk [tee].max_files`, default 20, user-proposed raise
to ~100, bounded by `max_file_size=1MiB` per file), pending researcher
citation from `rtk`'s own docs. Not re-litigated as a Phase 5 decision —
Phase 5's own decision (ingest tee logs) stands regardless of what value
`max_files` ends up at.

---

## Dashboard export/import mechanism

**Trade-off analysis presented:** `<input type=file>` + `FileReader` (client-
side only, no Artifact capability) vs. an Artifact `assets`/`db` capability
that would upload data off the machine.

**User's answer:** rejected the whole premise — never asked for an export
step at all. Wants a skill/command that runs a script extracting and
processing data from all 4 runtimes, then a view that reads directly from
that already-processed local data with filter/toggle/cross-axis capability —
no export/import step. This revealed a real mismatch with
`REQUIREMENTS.md`'s literal wording ("dashboard Artifact...reads a local
export"), which assumed a browser-sandboxed Claude Code Artifact with no
filesystem access (the reason an export step existed in the first place).
Clarified: the user wants a locally-running page/view with direct disk
access, not a sandboxed Claude Code Artifact.

| Option | Description | Selected |
|--------|-------------|----------|
| `<input type=file>` + FileReader, no capability | Still assumes an export step | |
| Artifact `assets`/`db` capability | Would move data off the machine | |
| *(neither — premise rejected)* | User wants a locally-running view with direct filesystem access instead | ✓ |

**Follow-up:** asked directly which is simpler to start with — static HTML
(regenerated with data embedded) evolving to a local HTTP server later, or
building the HTTP server from the start.

| Option | Description | Selected |
|--------|-------------|----------|
| Local HTTP server + page reading SQLite directly | More capable now, more upfront build | |
| Static HTML regenerated with embedded data | Simpler to start, no server/CORS friction | ✓ |
| TUI with textual (like Config Doctor) | Not discussed further — not a fit for a filterable data view | |

**User's choice:** static HTML now, recommended, with the daily ingestion
script's cron/scheduling automation explicitly deferred to the backlog — the
script itself is still built idempotent/incremental (safe for daily runs),
but the actual cron/systemd-timer wiring isn't built in this phase, invoked
manually for now.

---

## Claude's Discretion

None — every gray area had an explicit user decision.

## Deferred Ideas

- Cron/scheduling automation for the daily ingestion run — captured as a new
  backlog entry (`ROADMAP.md` §Backlog, Phase 999.2).
- A local HTTP server serving the refined SQLite store live — noted as a
  future evolution path if static-regeneration ever stops scaling, not
  committed as a backlog entry.
