# AI-Kit Cross-Runtime Usage Metrics & Dashboard - Product Requirements Document (PRD)

> **Status note**: everything in this document is a PROPOSAL, not an
> accepted decision. Every specific mechanism below is a recommendation
> after weighing alternatives — not a foregone conclusion. This is also
> the largest and least-precedented of this session's PRDs; expect more
> of its Design Decisions to be revisited during implementation than the
> smaller sibling PRDs.

## Requirements Description

### Background

- **Business Problem**: usage data (sessions, tokens, costs, commands run,
  failures) across Claude Code, opencode, Codex, and Cursor is scattered
  across each tool's own local session-log format, in a mix of JSONL and
  SQLite, with no cross-runtime view. There is no way today to answer
  even a simple question like "how many `grep` invocations happened this
  month, across all runtimes, grouped by session" without manually
  parsing multiple incompatible log formats by hand.
- **Target Users**: ai-kit's own maintainer/user, working across 4
  runtimes on one or more machines.
- **Value Proposition**: a single, local, privacy-preserving pipeline that
  turns each runtime's raw session logs into a queryable, filterable view
  — without ever uploading session content anywhere.

### Feature Overview

- **Core Features**: a raw-capture layer (parse each runtime's own local
  session logs, verbatim, lossless); a layered refinement pipeline
  (mechanical command decomposition → cwd/path resolution → future,
  explicitly-improvable layers); a local, file-based storage format;
  a locally-rendered interactive dashboard (Artifact HTML) that reads a
  local export and lets the user filter/sort/select axes.
- **Feature Boundaries**:
  - IN: the 4 runtimes' local session logs (Claude Code, opencode, Codex,
    Cursor — Cursor's local storage format is community-reverse-engineered
    only, not officially documented — see Risk Assessment); the MVP axes
    (date, model, commands, tokens, price — see Checks below); the raw→
    refined layering architecture itself.
  - NOT IN: configuration/settings auditing (belongs to a separate,
    unnamed configuration-review effort — "effort" and "service tier" in THIS PRD
    are observed historical attributes of a past request, never settings
    to change); any cloud/hosted storage of session content (explicitly
    rejected — see Design Decisions); reliably decomposing shell script
    blocks containing control flow (`if`/`for`/etc.) into their
    hypothetical individual executed commands — explicitly out of scope,
    an accepted limitation (see Non-Goals); the rtk substitution mechanism
    itself (already covered by a separate, unnamed tool-substitution
    effort) — this PRD only
    records that rtk rewrote something as a data point, never
    re-investigates how rtk decides what to rewrite.
- **User Scenarios**:
  - User asks (via the dashboard's filters, or a future query skill):
    "how many `grep`-family invocations happened this month, grouped by
    unique session" — the dashboard answers this from already-refined
    local data, no live re-parsing needed per query.
  - A session ran `cd src && grep -r TODO .` — the refined layer records
    this as two logical steps (a cwd change, then a grep against the
    resolved path `src/`), not one opaque compound string.
  - A later tool call in the SAME session runs `grep -r FIXME .` with no
    preceding `cd` in that same call — the refined layer resolves its
    effective cwd from the session's running cwd-state (last `cd` seen,
    possibly several tool-calls earlier), not from that single call in
    isolation.
  - A session runs a `for f in *.py; do rg pattern "$f"; done` block — the
    refined layer stores this as one opaque "script block" entry
    (`command_shape: control_flow_script`), and does NOT attempt to guess
    how many times the loop body actually ran or with what literal
    arguments. If, after enough real sessions, this exact shape (a `for`
    loop whose body is a single recognizable tool invocation) turns out
    to recur often, the classification refinement pass may promote it to
    its own recognized pattern with a best-effort, confidence-flagged
    `inferred_family` (e.g. "this loop body most likely invokes `rg`") —
    never a hard per-iteration count.

### Detailed Requirements

- **Input/Output**: Input = each runtime's local session-log files (see
  table below). Output = (a) a raw-capture store (append-only, one record
  per parsed raw event, never mutated after write — the event-sourcing
  "log" layer); (b) a refined store (derived from raw, safe to
  regenerate/improve without re-touching raw); (c) a local export file the
  dashboard Artifact reads.

| Runtime | Raw log location | Format | Confidence |
|---|---|---|---|
| Claude Code | `~/.claude/projects/*.jsonl` | JSONL | High (own machine's data) |
| opencode | `~/.local/share/opencode/storage/{message,part,session}/` + `opencode.db` (SQLite, v1.2+) | Mixed JSON + SQLite | High (confirmed this session) |
| Codex | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` (`$CODEX_HOME`, default `~/.codex`) | JSONL | High (confirmed this session) |
| Cursor | `~/.cursor/projects/<project>/agent-transcripts/<session-id>/<session-id>.jsonl` + `~/.cursor/chats/<md5(path)>/<session-id>/store.db` | JSONL + SQLite | **Low-to-medium — community reverse-engineering only, no official docs** ([source](https://jazzyalex.github.io/agent-sessions/blog/where-agents-store-history/)) |

- **Command-exec duration (confirmed feasible, researched this session)**:
  Claude Code's own JSONL transcript has no explicit `duration`/timing
  field on a tool call, but each JSONL line carries its own `timestamp`,
  and a `tool_use` entry's id (`message.content[].id`) matches a later
  `tool_result` entry's `tool_use_id` — empirically verified against a
  real local transcript (5,640 matched pairs in one session file;
  observed Bash-call durations in the tens-to-hundreds-of-milliseconds
  range). So exec duration is a **derived** refined-layer field
  (`tool_result.timestamp − tool_use.timestamp`), never a raw-captured
  one — consistent with this PRD's raw/refined split, and with the
  deferred "longest/shortest request/response" axis (Phase 5) being
  genuinely buildable, not just aspirational. opencode/Codex/Cursor
  equivalents are unverified — confirm per-runtime during Phase 5 rather
  than assuming the same derivation transfers.
- **User Interaction**: no interaction for the capture/refine pipeline
  (runs as a local script, likely on-demand or via a periodic local job —
  exact trigger mechanism TBD); the dashboard itself is the interactive
  surface (filter/sort/select axes on already-refined local data).
- **Data Requirements**: the raw layer's schema is "whatever each
  runtime's own log format already contains, parsed but not
  reinterpreted" — effectively one raw-record shape per runtime, since
  forcing a single unified raw schema across 4 incompatible native
  formats would lose information at the one layer that must never lose
  information. The refined layer is where cross-runtime normalization
  happens (a single unified schema: session id, runtime, model, timestamp,
  command text, resolved cwd, tokens in/out, estimated cost,
  `command_shape` (`simple` | `compound_decomposed` | `control_flow_script`
  | `unclassified`), an optional confidence-flagged `inferred_family` for
  patterns the refinement pass has learned to recognize inside an
  otherwise-opaque `control_flow_script`/`unclassified` entry, and whether
  rtk rewrote it).
- **Edge Cases**:
  - A raw log file changes format across a runtime's own version upgrades
    (already observed: opencode added a SQLite `opencode.db` only in
    v1.2+) — the raw parser must version-detect or degrade gracefully,
    never crash the whole pipeline on one unparseable file.
  - A `cd` targets a path outside the working tree, or a path that no
    longer exists by the time refinement runs — resolved cwd is still
    recorded as the resolved string; the refinement layer does not
    verify the path exists on disk (that would require touching the
    filesystem for historical, possibly-stale sessions).
  - Compound commands mixing recognized decomposition (`&&`/`;`/`|`) with
    a script-block sub-part (e.g. `cd src && for f in *.py; do ...; done`)
    — the `cd` half is decomposed normally (`command_shape: simple`,
    chained via `compound_decomposed`); the `for` half is captured as its
    own opaque `control_flow_script` entry within the same logical step.
  - A segment that matches neither the compound-decomposer's operators nor
    any recognized control-flow keyword (e.g. a heredoc, a nested
    subshell `( ... )`, unusual quoting) — stored as `unclassified` rather
    than forced into `control_flow_script`, so the two failure modes
    ("we know it's a script, just not decomposing it" vs. "we don't even
    recognize the shape") stay distinguishable in the data.

## Non-Goals

- **Reliable decomposition of control-flow script blocks into their
  actual executed sub-commands.** This would require either static
  shell-script analysis (fragile — variable expansion, glob results, and
  loop bounds are often only knowable at actual execution time) or
  re-executing/tracing the block (out of scope — this pipeline is a
  passive log reader, never a re-execution engine). Accepted limitation —
  but not a single undifferentiated bucket: the refined schema's
  `command_shape` field separates a **recognized** script/control-flow
  block (`control_flow_script` — shell grammar matched `if`/`for`/`while`/
  `case`/etc., just not decomposed further) from a genuinely
  **unclassified** one (`unclassified` — matched no known shape at all,
  e.g. unusual syntax, heredocs, nested subshells the decomposer doesn't
  yet parse). See Design Decisions ("Classification refinement loop") for
  how these two buckets get smaller over time instead of staying static.
- **Cloud/hosted storage of any session content.** Explicitly rejected —
  see Design Decisions.
- **A fast/compiled refinement engine in the MVP.** Explicitly deferred —
  see Design Decisions (Python MVP, forward-compatible architecture only).

## Design Decisions

### Technical Approach

**Alternatives Considered:**

1. **(Rejected) Store refined data in the dashboard Artifact's own hosted
   database capability.** More convenient to iterate on, but session data
   (commands, file paths, potentially code snippets) would leave the
   local machine — rejected on privacy grounds, per this PRD's explicit
   clarification.
2. **(Recommended) 100%-local raw + refined stores, dashboard reads a
   local export.** The capture/refine pipeline runs entirely locally
   (Python, matching this codebase's existing convention); the dashboard
   Artifact is published as a visualization shell that loads a
   user-provided local export (exact load mechanism — a pasted/uploaded
   JSON blob, a local file the user drags in, or an `assets` capability
   upload — is an implementation detail to resolve when the dashboard
   phase is actually built, not fixed here).
3. **(Rejected for MVP, noted as future direction) A compiled/fast
   refinement engine (Rust/Go) from day one.** The user's own concern
   (some existing session-analysis plugins take minutes) is real, but
   premature for an MVP whose actual data volume is unknown. Recommended
   instead: architect the raw/refined boundary so a future faster
   refinement engine could be swapped in without re-touching the raw
   capture layer (raw stays whatever-format-each-runtime-uses; refined
   is a well-defined, engine-agnostic intermediate schema) — this is the
   real payoff of the layered, event-sourcing-style design the user
   proposed: performance becomes a refinement-layer concern only, never a
   raw-capture-layer rewrite.
- **Key Components**:
  - Per-runtime raw parsers (4, one per runtime table row above) — each
    isolated, so a format change or bug in one never breaks the others.
  - The cwd-resolution state machine: replays `cd` occurrences in
    session-chronological order (across separate tool-calls, not just
    within one compound command) to compute each command's effective
    working directory, used to normalize relative → absolute paths for
    consistent cross-command aggregation (the user's own "how do we know
    a `grep` happened" question).
  - The mechanical decomposer: splits `&&`/`;`/`|`-joined compound
    commands into ordered logical steps; detects (via basic shell
    grammar, not full parsing) when a segment contains control-flow
    keywords (`if`/`for`/`while`/`case`/etc.) and tags it
    `control_flow_script` rather than decomposing it further; a segment
    matching neither a compound operator nor a control-flow keyword is
    tagged `unclassified` instead of being forced into one of the other
    buckets.
  - The classification refinement pass (see "Classification refinement
    loop" below): a periodic, offline analysis step — not part of the
    live capture/refine pipeline — that mines accumulated
    `control_flow_script`/`unclassified` entries for recurring shapes and
    feeds confirmed patterns back into the mechanical decomposer's rule
    set.
  - The refined-schema writer (the single, cross-runtime-normalized
    output format the dashboard actually reads).
  - The dashboard Artifact (reads a local export, renders
    filterable/sortable tables/charts across the MVP axes).
- **Data Storage**: raw layer — one store per runtime, in whatever shape
  keeps that runtime's own data lossless (likely SQLite per runtime, or a
  single local SQLite DB with per-runtime tables — exact choice an
  implementation detail). Refined layer — a single local SQLite DB (or
  equivalent) with the unified cross-runtime schema. Both entirely local
  (e.g. under `~/.local/share/ai-kit/usage-metrics/` or similar — exact
  path TBD).
- **Interface Design**: a new ai-kit skill/command to run the
  capture→refine pipeline on demand (exact invocation TBD — could be
  triggered manually, or on a schedule the user sets up themselves,
  outside this PRD's own scope); a local export step that produces
  whatever file format the dashboard Artifact will read.

### MVP Axes

Per this PRD's clarification, the MVP ships with exactly these 5 axes,
each filterable and sortable; every other axis mentioned in the original
idea (session/task duration, LOC generated, quota/resource-pressure
failures, service_tier, runtime/CLI as its own explicit axis, etc.) is
real and valuable but deferred to a later phase, once the refined schema
and dashboard shape have proven out on the smaller axis set:

1. **Date** — single day, week, month, custom range, and a "current
   month" preset.
2. **Model** — which model served the request.
3. **Commands** — which command (family) was run. Family membership
   follows the pattern a separate, unnamed tool-substitution effort
   already establishes: a classic tool and its modern
   individual are related-but-distinct members of one family, never
   merged into a single count and never treated as unrelated —
   `grep`↔`rg`, `cat`↔`bat`, `sed`↔`sd`, `ls`↔`eza`, `find`↔`fd` (that
   effort's own curated set is the single source of truth for this mapping;
   this PRD reads/mirrors it rather than maintaining an independent,
   possibly-drifting copy). The refined schema records BOTH the literal
   command run AND its family, so a query can ask for "how much `rg`
   specifically" or "how much of the `grep` family overall" equally well.
   This also enables, with no extra mechanism beyond the date + family
   axes already in this MVP, a before/after comparison once the
   substitution-awareness-hook (or any future rtk-side change) starts
   measurably shifting the agent from the classic tool to its modern
   individual — e.g. "how did `rg` vs. `grep` usage change after the hook
   shipped on `<date>`" is just a filtered query, not new infrastructure.
4. **Tokens** — input/output token counts per command/session.
5. **Price** — estimated cost, derived from tokens + model + (where
   knowable) service tier.

### Classification refinement loop

Per this PRD's raw-retained/refined-improvable principle, the
`control_flow_script`/`unclassified` buckets are not meant to stay static
dumping grounds — they are the explicit seed for future decomposer rules,
but ONLY once real usage data exists, not designed speculatively now.

- **Trigger**: after the first real end-to-end runs of the capture→refine
  pipeline against actual historical session logs (i.e., after Phase 1-3
  ship and have ingested real data, not synthetic test fixtures) — not on
  a fixed schedule, and not before real data exists to mine.
- **What it does**: an offline analysis pass over the accumulated
  `control_flow_script` and `unclassified` refined entries, looking for
  recurring textual/structural shapes (e.g., "a `for … do <single tool
  invocation> …; done` loop" recurs across N sessions). This is explicitly
  a **pattern-mining/inference** step, not a shell-execution or tracing
  step — it never re-derives what actually ran, only what shape recurs.
- **What it produces**: two possible outcomes per recognized recurring
  shape, both additive and reversible:
  1. A new rule added to the mechanical decomposer, so future occurrences
     of that exact shape reclassify from `unclassified` to
     `control_flow_script` (or, where the shape is simple enough, get
     properly decomposed into ordered steps like any compound command).
  2. Where full decomposition still isn't safe/reliable (e.g. a loop body
     whose target varies but whose invoked tool doesn't), a
     confidence-flagged `inferred_family` annotation is attached to
     matching entries — surfaced in the dashboard as an inference, never
     presented with the same certainty as a hard-decomposed command.
- **Why this is safe**: because raw is retained losslessly (Design
  Decisions, Alternatives Considered #2/#3), re-running this pass with
  improved pattern rules can reclassify *historical* entries too, not just
  future ones — nothing about waiting until real data exists costs any
  information.
- **Alternatives Considered**: (rejected) building speculative
  pattern-recognition rules into the MVP decomposer before any real data
  exists — rejected as premature/YAGNI, since the actual shapes worth
  recognizing are exactly the ones this session's own conversation
  couldn't fully predict in advance; (rejected) leaving
  `control_flow_script`/`unclassified` permanently opaque with no
  improvement path — rejected because it wastes the raw-retention design's
  whole point; (recommended) the triggered, post-real-data pattern-mining
  pass described above.

### Constraints

- **Performance**: no hard MVP requirement (see Alternatives Considered)
  — but the raw/refined architectural separation is a hard constraint
  regardless of MVP performance, since it's what makes a later
  performance fix possible without a raw-capture rewrite.
- **Compatibility**: a raw parser for one runtime must never crash the
  whole pipeline if that runtime's log format is missing, empty, or
  differently-shaped than expected (e.g. a machine with no Cursor
  installed) — skip that runtime's contribution, don't fail the whole run.
- **Security/Privacy**: raw and refined data never leave the local
  machine; the dashboard Artifact itself never has a hosted-database
  capability wired to session content (per Design Decisions).
- **Skill quality gate**: if this work is wrapped in a `SKILL.md` (likely,
  for the capture/refine pipeline's invocation), it must pass the same
  `skill-judge` review loop established across this initiative's other
  PRDs before being marked complete.

### Risk Assessment

- **Technical Risks**: Cursor's log format is confirmed only via
  community reverse-engineering, not official docs — the highest-risk
  parser in this PRD, most likely to break on a Cursor version update.
  Mitigated by the per-runtime parser isolation (Constraints above) — a
  broken Cursor parser degrades that one runtime's data, never the whole
  pipeline.
- **Dependency Risks**: none new (Python, matching existing codebase
  conventions).
- **Schedule Risks**: this is the largest PRD in this initiative by a
  wide margin — explicitly phased below to ship a narrow, real MVP first
  (one or two runtimes, the 5 MVP axes) rather than attempting all 4
  runtimes and every axis simultaneously.

## Acceptance Criteria

### Functional Acceptance

- [ ] Raw parsers exist for at least Claude Code and opencode (the two
      confirmed-high-confidence formats) in Phase 1; Codex and Cursor
      follow in later phases.
- [ ] The cwd-resolution state machine correctly resolves a relative-path
      command's effective absolute path using prior `cd` state from
      earlier in the same session — pinned by a test reproducing the
      user's own example (`cd` in one call, `grep` with a relative path
      in a later, separate call).
- [ ] A compound command mixing plain segments and a control-flow segment
      is decomposed for its plain parts and stored as one opaque
      `command_shape: control_flow_script` entry for its script-block part
      — never silently mis-decomposed into fabricated sub-commands.
- [ ] A segment matching neither a compound operator nor a recognized
      control-flow keyword is tagged `command_shape: unclassified`,
      distinct from `control_flow_script` — the two never collapse into
      one bucket.
- [ ] The refined schema records both a command's literal text and its
      "family" (e.g. `rg` invocations tagged with family `grep`).
- [ ] The classification refinement pass exists as a runnable, documented
      step (even if not yet triggered on real data at ship time) and,
      when run against a fixture with a recurring `for`-loop shape,
      demonstrably reclassifies matching entries from `unclassified`/
      `control_flow_script` toward a recognized pattern or
      `inferred_family` annotation — pinned by a test.
- [ ] A raw parser failure for one runtime never crashes the pipeline for
      the others (empirically tested: simulate a malformed/missing log
      file for one runtime, confirm the rest still produce output).
- [ ] The dashboard Artifact never has a hosted-database capability
      pointed at session content — confirmed by inspecting its published
      capability declaration.

### Quality Standards

- [ ] Test Coverage: per-runtime raw parser tests (happy path +
      malformed/missing file); cwd-resolution state machine tests
      (including the multi-call, cross-tool-call `cd` scenario); the
      mechanical decomposer's control-flow detection tests.
- [ ] Skill Quality: any `SKILL.md` this work creates passes the
      skill-judge review loop.
- [ ] Security Review: confirmed no raw or refined data path writes
      outside the local machine.

### User Acceptance

- [ ] User Experience: the dashboard answers the user's own example query
      ("how many greps this month, by session") directly from
      already-refined local data.
- [ ] Documentation: the refined schema's exact field list and the
      `contains_control_flow` limitation are documented wherever this
      pipeline's `SKILL.md` (or equivalent) lives.

## Execution Phases

### Phase 1: Raw capture (2 runtimes)
**Goal**: Lossless raw capture for Claude Code and opencode.
- [ ] Task 1: Claude Code raw parser (`~/.claude/projects/*.jsonl`).
- [ ] Task 2: opencode raw parser (`~/.local/share/opencode/storage/` +
      `opencode.db`).
- **Deliverables**: two isolated, tested raw parsers producing
  runtime-native raw records.

### Phase 2: Refinement — mechanical decomposition + cwd resolution
**Goal**: Turn raw records into the unified, cross-runtime refined schema
for the 5 MVP axes.
- [ ] Task 1: mechanical decomposer (`&&`/`;`/`|` splitting +
      control-flow-segment detection).
- [ ] Task 2: cwd-resolution state machine (per-session, chronological
      `cd` replay).
- [ ] Task 3: refined-schema writer covering the 5 MVP axes (date, model,
      commands with family tagging, tokens, price).
- **Deliverables**: a working raw→refined pipeline for 2 runtimes, tested
  against the user's own example query pattern.

### Phase 3: Dashboard (local-only)
**Goal**: A locally-loading, filterable/sortable Artifact dashboard over
the refined export.
- [ ] Task 1: local export format (from the refined store to whatever the
      dashboard loads).
- [ ] Task 2: the dashboard Artifact itself — filter/sort UI over the 5
      MVP axes, confirmed to declare no hosted-database capability.
- **Deliverables**: a working dashboard answering the user's own example
  query.

### Phase 4: Classification refinement pass (after first real e2e runs)
**Goal**: Build the pattern-mining tool that mines accumulated
`control_flow_script`/`unclassified` entries and feeds recognized shapes
back into the mechanical decomposer — run for real only once Phase 1-3
have ingested actual historical session logs, not synthetic fixtures.
- [ ] Task 1: pattern-mining analysis tool (reads refined-store entries
      tagged `control_flow_script`/`unclassified`, surfaces recurring
      shapes above a frequency threshold — exact threshold TBD once real
      data volume is known).
- [ ] Task 2: decomposer-rule promotion path (a recognized recurring
      shape becomes either a new decomposer rule or a confidence-flagged
      `inferred_family` annotation, both re-applicable to historical
      entries, never just future ones).
- **Deliverables**: the tool itself, tested against synthetic fixtures
  reproducing the user's own for-loop example; actually running it
  against real data is a follow-up action once Phase 1-3 have real
  history to mine, not a Phase 4 deliverable itself.

### Phase 5: Remaining runtimes + deferred axes (follow-up, not this PRD's MVP)
**Goal**: Codex and Cursor raw parsers; the deferred axes (duration, LOC,
failures, service_tier where knowable, explicit runtime axis).
- [ ] Task 1: Codex raw parser.
- [ ] Task 2: Cursor raw parser (flagged low-confidence — build defensively,
      expect breakage on Cursor updates).
- [ ] Task 3: deferred-axis design, informed by how Phases 1-3 actually
      performed and what real queries the user found valuable.
- **Deliverables**: explicitly scoped as a follow-up phase, not committed
  to this PRD's initial delivery — revisit scope once Phases 1-3 ship.

---

**Document Version**: 1.0
**Created**: 2026-09-07
**Clarification Rounds**: 3 (plus 2 research passes: raw-log locations
and Cursor/service_tier confirmation)
**Quality Score**: 85/100 — intentionally not pushed higher: several
Design Decisions (dashboard load mechanism, exact storage path/engine,
grep/rg family-counting UI) are explicitly left as implementation-time
decisions rather than prematurely fixed, given this PRD's own scale and
the "propose, don't decide prematurely" framing requested for this whole
initiative.
