# Phase 5: Usage Metrics Dashboard - Context

**Gathered:** 2026-09-08
**Status:** Ready for planning

<domain>
## Phase Boundary

A single, periodic, non-concurrent ingestion script pulls raw session data
from all supported AI CLI runtimes (Claude Code and opencode first, per REQ
scope; Codex and Cursor as later plans within this phase) plus `rtk`'s own
local data stores, writes it losslessly into a per-runtime raw store, then
runs one pipeline pass that normalizes it into a single refined, queryable
store. A locally-generated static HTML view reads directly from the refined
store's already-processed data — filterable/sortable across the 5 MVP axes —
with no export/import step and no data ever leaving the machine.

</domain>

<decisions>
## Implementation Decisions

### Store architecture (two-tier: raw + refined)
- **D-01:** The user corrected the initial framing of this decision: there is
  no concurrent-writer scenario to design around, because exactly one script
  runs the entire pipeline periodically (ingest → process → write final
  store) — nothing else writes to either store while it runs. This resolved
  what looked like a SQLite-concurrency question into a simpler two-tier
  split.
- **D-02:** **Raw store = JSONL, one append-only file per runtime.** Verbatim,
  lossless capture — matches `REQ-usage-metrics-raw-capture`'s "write session
  logs verbatim/losslessly." One runtime's parser failure or format change
  never corrupts or blocks another runtime's file.
- **D-03:** **Refined store = SQLite**, one database holding the normalized
  cross-runtime schema (date, model, commands + family, tokens, price) that
  the dashboard queries directly. No concurrency concern here either, since
  only the single pipeline script ever writes to it — the dashboard is
  read-only against it.
- **D-04:** **Location:** `~/.local/share/ai-kit/usage-metrics/{raw,refined}/`
  — follows the XDG data-dir convention already used on this machine by both
  `rtk` (`~/.local/share/rtk/`) and opencode (`~/.local/share/opencode/`).
  `raw/` holds one `.jsonl` file per runtime; `refined/` holds the SQLite
  database.

### cwd-resolution scope (per-runtime, not uniform)
- **D-05:** The chronological cwd-resolution state machine (tracking `cd`
  across separate tool-calls in the same session to resolve relative-path
  commands) applies **only where it's actually needed**, not uniformly to
  all four runtimes:
  - **Claude Code**: already carries a per-message `cwd` field natively
    (live-verified against a real `~/.claude/projects/*.jsonl` sample). The
    refiner simply reads this field — no state machine required.
  - **opencode / Codex / Cursor**: lack per-command cwd (opencode's `session`
    table has only a session-level `directory` field, live-verified against
    the real SQLite schema at `~/.local/share/opencode/opencode.db` — no
    per-command tracking). For these, the refiner seeds its state machine
    with the session's initial directory and updates it whenever a `cd`
    command is detected in a parsed tool-call.
  — **Reversibility:** reversible — an internal refiner-logic branch per
  runtime; adding cwd-tracking uniformly later (if a runtime's log format
  ever gains native per-command cwd) is additive, not a rewrite.

### Raw sources: rtk history.db AND tee logs (both included)
- **D-06:** The raw-capture stage also ingests `rtk`'s own local data as a
  complementary source, in addition to each runtime's session logs:
  - **`~/.local/share/rtk/history.db`** (SQLite, live-verified schema): the
    `commands` table (id, timestamp, original_cmd, rtk_cmd, input_tokens,
    output_tokens, saved_tokens, savings_pct, exec_time_ms, project_path)
    provides precomputed token/savings data per rewritten command, plus a
    `parse_failures` table.
  - **`~/.local/share/rtk/tee/*.log`** (failure-only output capture, capped
    by `[tee]` config — `mode="failures"`, `max_file_size=1048576`,
    `max_files` currently 20): the user explicitly overrode the initial
    recommendation to exclude these ("also include tee logs") — final
    decision includes both stores as raw sources.
  - **Explicitly excluded:** any runtime's OTEL/vendor telemetry export.
    Telemetry leaves the machine by design (external export target); this
    directly contradicts the local-only constraint and PROJECT.md's
    never-more-certainty-than-verified value, so it stays out regardless of
    what data it might otherwise offer.
  — Cross-reference: the user separately proposed raising `rtk`'s
  `[tee].max_files` (currently 20) toward ~100 as a **Config Doctor (Phase 4)
  check row**, not a Phase 5 decision — this is captured as Open Research
  Question #7 in `04-CONTEXT.md` (commit `9aaf107`). Phase 5's decision to
  ingest tee logs stands regardless of what value `max_files` ultimately
  gets tuned to; a larger `max_files` just means more historical tee entries
  available to ingest.
- **D-07:** **Ingestion cadence: once per day.** Consistent with the
  single-script, no-concurrent-writers design already confirmed in D-01. The
  ingestion script itself is built idempotent and incremental (safe to run
  daily), but wiring an actual daily trigger (cron/systemd timer) is
  explicitly **out of this phase's scope** — see Deferred Ideas. Manual
  invocation only for now.

### Dashboard: no export/import step, static HTML first
- **D-08:** The user directly corrected a mismatched premise in
  `REQUIREMENTS.md`'s literal wording ("dashboard Artifact...reads a
  user-provided local export"): they never asked for an export step at all.
  What they actually want is a skill/command that runs the ingestion +
  refinement script against local data, then a view that reads that
  already-processed local data directly — with filter/toggle/cross-axis
  capability — with **no export, no import, and no sandboxed Claude Code
  Artifact mechanism** (an Artifact's browser sandbox has no filesystem
  access, which is *why* an export step existed in the original wording in
  the first place; that constraint doesn't apply here since this is a
  locally-running view with direct disk access). This is a genuine
  requirements-wording gap, not just a phase-scope clarification — see the
  Requirements Amendment note below.
- **D-09:** **Start with static HTML, regenerated with data embedded at
  generation time — not a local HTTP server.** The user asked directly which
  is simpler to start with rather than picking a side, and per the
  established "verify before committing to complexity" pattern in this
  session, static-HTML-first was recommended and confirmed: it needs no
  server process, no port, no `file://`-vs-`http://` CORS/fetch friction —
  the generation script embeds the refined SQLite query results as JSON
  directly into the HTML output, which is then opened via `file://`. A local
  HTTP server serving the SQLite DB live remains a valid future evolution
  **only if** data volume ever makes full-regeneration-per-view impractical
  — not built now.
  — **Reversibility:** reversible — the refined SQLite store (D-03) is the
  same either way; only the presentation layer would need to change from
  "regenerate static HTML" to "serve a live query endpoint."

### Requirements Amendment (2026-09-08, this discussion)
- **D-10:** `REQUIREMENTS.md`'s `REQ-usage-metrics-dashboard-ui` and
  `ROADMAP.md`'s Phase 5 success criteria #3 both currently say "dashboard
  Artifact...reads a user-provided local export" — this wording is now
  **stale** given D-08/D-09 above (no export step, no Claude Code Artifact
  sandbox mechanism; a locally-regenerated static HTML page with direct
  filesystem access instead). Both files must be formally amended to match,
  following this session's established pattern (Phase 4's Cursor-scope
  amendment) of correcting REQUIREMENTS.md/ROADMAP.md whenever a
  live-confirmed decision contradicts their literal wording, rather than
  leaving the contradiction to be discovered downstream by the researcher or
  planner.
  — **Reversibility:** reversible — wording-only correction; no requirement
  ID changes, no scope change to what data the dashboard shows.

### Claude's Discretion
None — every gray area in this phase had an explicit user decision.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source PRD and synthesized intel
- `docs/prds/ai-kit-usage-metrics-dashboard-v1.0-prd.md` — the proposal PRD
  this phase implements
- `.planning/intel/requirements.md` — synthesized requirement detail
- `.planning/REQUIREMENTS.md` §Usage Metrics Dashboard —
  REQ-usage-metrics-raw-capture, REQ-usage-metrics-refinement-pipeline,
  REQ-usage-metrics-dashboard-ui (amended per D-10),
  REQ-usage-metrics-classification-refinement-loop
- `.planning/ROADMAP.md` §Phase 5 — success criteria this phase must make
  true (success criterion #3 amended per D-10)
- `.planning/PROJECT.md` — core value (never claim more certainty than
  verified) directly drove D-06's OTEL exclusion and D-08's requirements
  correction

### Cross-phase references
- `.planning/phases/03-tool-substitution-awareness-hook/03-CONTEXT.md` —
  the curated tool-substitution pair list this phase's command-family
  tagging mirrors (per `REQ-usage-metrics-refinement-pipeline` and
  ROADMAP.md's Phase 5 "Depends on" note)
- `.planning/phases/04-config-doctor/04-CONTEXT.md` — Open Research Question
  #7 (rtk `[tee].max_files` tuning) — related to but distinct from this
  phase's D-06 decision to ingest tee logs

### Third-party tool documentation (external, not a repo path)
- `github.com/rtk-ai/rtk/blob/develop/docs/guide/getting-started/configuration.md`
  — referenced by the user for `rtk`'s `[tee]`/`[tracking]` config keys;
  `rtk gain` and its flags for metrics viewing
- Live-verified locally, more authoritative than docs where they might
  diverge: `~/.local/share/rtk/history.db` schema (`commands` +
  `parse_failures` tables), `~/.local/share/opencode/opencode.db` schema
  (`session`.`directory`, `message`, `part`, `event`, etc.), a real
  `~/.claude/projects/*.jsonl` sample (per-message `cwd` field confirmed
  present)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `~/.local/share/rtk/history.db` (SQLite): `commands` table columns —
  id, timestamp, original_cmd, rtk_cmd, input_tokens, output_tokens,
  saved_tokens, savings_pct, exec_time_ms, project_path — directly
  ingestible without needing to re-derive token counts.
- `~/.claude/projects/*.jsonl`: per-message `cwd` field already present —
  no cwd-resolution state machine needed for Claude Code (D-05).

### Established Patterns
- XDG data-dir convention (`~/.local/share/<tool>/`) — already used by
  `rtk` and opencode on this machine; this phase's raw/refined stores follow
  the same convention under `~/.local/share/ai-kit/usage-metrics/`.
- Single-pipeline-script, no-concurrent-writers design (D-01) removes the
  need for any database-level concurrency handling in either store.

### Integration Points
- `~/.local/share/opencode/opencode.db` (SQLite, live-verified via `file`
  command as a real SQLite 3.x database) — `session` table (`directory`
  field), `message`, `part` (opaque JSON `data` column with a `type` field),
  `event`, `permission`, `project`, `credential`, `account`, `todo` tables.
- `~/.local/share/rtk/tee/*.log` — failure-only capture, capped by
  `[tee]` config (`mode="failures"`, `max_file_size=1048576`, `max_files`
  currently 20) — see D-06's cross-reference to `04-CONTEXT.md`'s Open
  Research Question #7.

</code_context>

<specifics>
## Specific Ideas

- The two-tier raw(JSONL)/refined(SQLite) split emerged directly from the
  user correcting a false premise: the initial question assumed a
  concurrency trade-off that doesn't exist, because the actual design is one
  periodic script running the full pipeline with no concurrent writers
  (D-01).
- The "no export step" clarification (D-08) emerged the same way: the
  original REQUIREMENTS.md wording assumed a browser-sandboxed Claude Code
  Artifact (which has no filesystem access, hence needing an export/import
  step to get data in) — but the user's actual mental model was always a
  locally-running view with direct disk access, making the export step
  unnecessary from the start.

</specifics>

<deferred>
## Deferred Ideas

- **Cron/scheduling automation for the daily ingestion run**: the ingestion
  script (D-07) is built idempotent and incremental — safe to run daily —
  but actually wiring a recurring trigger (cron job, systemd user timer, or
  equivalent) is explicitly deferred. Manual invocation only in this phase.
  Captured as a new backlog entry (`ROADMAP.md` §Backlog, Phase 999.2) per
  the user's explicit instruction ("el cron lo podemos dejar diferido por
  ahora al backlog" — "the cron can stay deferred to the backlog for now").
- **Local HTTP server serving the refined SQLite DB live**: raised as an
  alternative to static-HTML-first (D-09) and explicitly deferred — only
  worth building if data volume ever makes full static regeneration
  impractical. Not a backlog entry (no committed intent to build it, just a
  noted future option) — mentioned here for downstream awareness only.

### Reviewed Todos (not folded)
None — no matching todos found for Phase 5.

</deferred>

---

*Phase: 5-Usage Metrics Dashboard*
*Context gathered: 2026-09-08*
