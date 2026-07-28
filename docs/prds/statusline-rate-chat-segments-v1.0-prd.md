# Status-Line Rate-Limit Split + Compaction-Aware Chat Size — Product Requirements Document (PRD)

## Requirements Description

### Background

- **Business Problem**: Two existing diagnostic segments are less useful than they could be.
  (1) `alt_rate_limits` bundles every rate-limit bucket (today: a 5-hour and a 7-day window) into
  one string with a shared reset-stamp format (`mmm dd HH:MM`) that doesn't match reality — a
  5-hour window never crosses into a different month/day, so showing a full date for it is noise,
  and because both buckets are packed into one string, the packer can only keep-or-drop the whole
  thing, not gracefully shed the least-important half first. (2) `chat_size` shows only the raw
  on-disk transcript byte count, which **only ever grows** (the `.jsonl` transcript is append-only
  and is never shrunk by `/compact` or auto-compaction — verified against real transcripts under
  `~/.claude/projects/`, corroborated by the [official Claude Code sessions
  doc](https://code.claude.com/docs/en/sessions) and the [compaction
  doc](https://platform.claude.com/docs/en/build-with-claude/compaction)). That makes the segment
  a poor proxy for "is this chat getting unwieldy" — a session that compacted five minutes ago and
  a session that never compacted can show the same large number, even though the first is far
  "lighter" in terms of what's actually being resent to the model.
- **Target Users**: any ai-kit status-line user who enables rate-limit visibility and/or
  `chat_size`, and wants signals that degrade gracefully under tight terminal width and reflect
  reality rather than a generic/legacy format.
- **Value Proposition**: rate-limit visibility that is accurate to the two real buckets Claude Code
  reports, degrades width-gracefully with the weekly bucket sacrificed first, and a `chat_size`
  reading that distinguishes "total historical footprint" from "how much has piled up since the
  last compaction" — closing the gap between "chat file is huge" and "is it actually time for a new
  session."

### Feature Overview

- **Core Features**:
  - **FR-1 — Split `alt_rate_limits` into `alt_h_rate_limit` (hourly bucket) and
    `alt_w_rate_limit` (weekly bucket)**, each with its own 2-tier width-adaptive format and its
    own drop-first-when-tight behavior (weekly drops before hourly).
  - **FR-2 — `chat_size` becomes compaction-aware**: alongside the historical total, it shows
    bytes accumulated since the last compaction (and how many compactions have happened this
    session), computed by scanning the transcript for `compact_boundary` markers.
- **Feature Boundaries**:
  - In scope: `tools/status-line.py` (`seg_alt_rate_limits` replacement, `seg_chat_size` rework,
    ramp/registry/layout wiring), `tools/setup.py` (`SEGMENT_DEFAULTS`/inventory mirror),
    `tools/statusline.toml.sample`, `README.md`.
  - Out of scope: any change to `seg_context` (already correct — it reads Claude Code's own
    `context_window.used_percentage`/`context_window_size`, which *is* the real, live, post-
    compaction context usage; this PRD does not touch it). No subagent-context visibility is
    added — Claude Code's status-line hook is per top-level-session only and does not expose
    subagent token usage; this is a documented constraint, not a defect to fix here. No new
    external-segment provider contract changes.
- **User Scenarios**:
  - A user with a narrow terminal sees `alt_h_rate_limit` stay visible while `alt_w_rate_limit`
    disappears first as columns shrink.
  - A user glances at `chat_size` after several `/compact` cycles and sees the small "since last
    compaction" figure alongside the large historical total, instead of one undifferentiated
    number.

### Detailed Requirements

#### FR-1 — Split rate-limit segments

- **Input**: `ctx.rate_limits: dict[str, Any]`, keyed by bucket name (`"five_hour"`,
  `"seven_day"` today; format is `{number}_{unit}` per `fmt_rate_key_label`, unit ∈
  `{hour(s), day(s), week(s), month(s)}`). Each bucket value is `{"used_percentage": float,
  "resets_at": int | None}` (either or both keys may be absent/None).
- **Bucket routing**: a bucket belongs to the **hourly** segment when its unit is `hour`/`hours`;
  it belongs to the **weekly** segment when its unit is `day`/`days`/`week`/`weeks`/`month`/
  `months` (i.e. everything non-hourly is "the long window" — future-proof if Anthropic ever adds
  a different long-window bucket name). If more than one bucket routes to the same segment, join
  them with `" | "` (matching today's multi-bucket behavior), each formatted independently.
- **Output — `seg_alt_h_rate_limit`** (icon: ⚡, same as today), 2 real detail tiers via
  `util_first_fitting`, no 3rd textual tier — if the narrower tier still doesn't fit, the segment
  hides (returns `None`), same as any other segment that can't fit:
  - Tier 1 (rich): `5h: 42% (↺ 14:10)` — reset stamp is **time-only, never a date** (`%H:%M`),
    because the 5-hour bucket cannot cross into a different day/month in a way that matters.
  - Tier 2 (terse): `5h: 42%` — no reset stamp.
  - No bucket present / no `used_percentage` → segment returns `None` (hidden), matching today.
- **Output — `seg_alt_w_rate_limit`** (icon: ⚡), 2 real detail tiers:
  - Tier 1 (rich): `7d: 13% (↺ Sun 14:10)` — reset stamp is **weekday abbreviation + time**
    (`%a %H:%M`), replacing today's `mmm dd HH:MM`.
  - Tier 2 (terse): `7d: 13%` — no reset stamp.
  - No bucket present → segment returns `None` (hidden).
- **Drop priority**: `alt_w_rate_limit` is placed to the **right** of `alt_h_rate_limit` in
  `LAYOUT`'s diagnostics row (rightmost = first dropped by the packer under `RIGHT_MARGIN`
  pressure), so weekly is always the first of the two sacrificed when the line is tight.
- **Color**: both segments keep using the existing shared `theme.ramps["rate"]` band (no new ramp
  key) — percentage-based coloring is identical between the two buckets today, and splitting the
  segment doesn't change that.
- **Removal of `alt_rate_limits`**: `alt_rate_limits`, its builder, its `SEGMENTS`/`LAYOUT` entries,
  and its `setup.py`/sample-TOML mirrors are deleted outright — **no legacy alias**. This follows
  the project's already-established canonical-only convention (see the `d9c1d7f` "canonical-only
  scope amendment — drop back-compat" precedent), and risk is low because `alt_rate_limits` is
  `False` (off) by default today. Both new segments also default to `False`, matching the segment
  they replace.

#### FR-2 — Compaction-aware `chat_size`

- **Mechanism** (verified empirically against real transcripts under `~/.claude/projects/*/*.jsonl`
  and against official docs — see Design Decisions): Claude Code's transcript `.jsonl` is
  append-only and never shrinks. Each compaction event appends a `{"type":"system","subtype":
  "compact_boundary","compactMetadata":{"trigger":...,"preTokens":...,"postTokens":...}}` record,
  followed by a synthetic summary `user` message. The **byte offset of the start of the last such
  record** marks where "current" transcript content begins; the **count** of such records across
  the file is the number of compactions this session has had.
- **New probe**: given `ctx.transcript` (the path already used by `probe_chat_size`), scan the file
  once for lines containing `"subtype":"compact_boundary"` (a plain substring check before any JSON
  parse, for speed — only lines that match get `json.loads`'d to confirm and to read the byte
  offset). Compute:
  - `total_bytes` — the file's total size (unchanged from today's `probe_transcript_bytes`).
  - `compact_count` — number of `compact_boundary` records found (0 if none).
  - `since_bytes` — bytes from the start of the last `compact_boundary` record's line to EOF; equal
    to `total_bytes` when `compact_count == 0` (there is nothing to exclude).
  - Missing/unreadable transcript → all `None`, segment hides (unchanged from today).
- **Output — `seg_chat_size`** (icon: 💾), 2 real detail tiers, no 3rd textual tier (matches FR-1's
  hide-not-truncate pattern):
  - When `compact_count == 0`: **both tiers are identical** — just the total, e.g. `850K` (there is
    nothing to abbreviate away; `since == total` by construction).
  - When `compact_count >= 1`:
    - Tier 1 (rich): `320K/4.2M (3x)` — `since_bytes`/`total_bytes` formatted via the existing
      `fmt_bytes`, then `(<compact_count>x)`.
    - Tier 2 (terse): `320K` — `since_bytes` alone.
  - If neither tier fits, the segment hides (`None`), same as any other segment.
- **Color**: the existing `chat_size` ramp (`theme.ramps["chat_size"]`, thresholds `512k`..`10M`)
  is now keyed off **`since_bytes`**, not `total_bytes` — the ramp's purpose is "is this getting
  unwieldy *right now*," which is what `since_bytes` measures; `total_bytes` is historical
  bookkeeping only and was never a meaningful health signal on its own.
- **`seg_context` is unchanged.** No new cross-segment coupling is introduced — `chat_size` and
  `context` remain independent segments; this PRD only makes `chat_size` itself compaction-aware.

### Edge Cases

- A bucket with `used_percentage` present but `resets_at` absent → Tier 1 degrades to Tier 2's
  content within the same string (no reset suffix), consistent with today's `util_reset_suffix`
  behavior.
- A `rate_limits` dict with only one of the two buckets present → the other segment's builder
  returns `None` and simply doesn't render (no placeholder, no error).
- A transcript with a `compact_boundary` substring appearing inside ordinary message *text* (e.g. a
  user pastes JSON containing that string) → guarded by requiring the line to `json.loads` into an
  object with `"type":"system"` **and** `"subtype":"compact_boundary"` before it counts; a
  substring match inside an unrelated string field doesn't parse into that shape and is ignored.
- Very large transcripts (seen up to ~16 MB in real usage): the substring pre-filter avoids
  `json.loads`-ing every line just to find the rare boundary lines, keeping the added probe cost
  close to a single file read — consistent with `render_time`'s existing SLO/SLA framing (FR-7.3);
  no new SLO exception is introduced by this PRD.

## Design Decisions

### Technical Approach

- **Architecture**: both FRs are additive within the existing builder-registry pattern
  (`SEGMENTS`/`BUILDERS`/`LAYOUT`/`_RAMP_DEFAULTS`) — no changes to the packer, `Context`, or
  `Theme` machinery. `seg_alt_rate_limits` is deleted and replaced by two builders;
  `seg_chat_size` is modified in place; `probe_chat_size` gains the boundary-scan logic (or a
  sibling probe is added and `seg_chat_size` reads both).
- **Key Components**: `fmt_rate_key_label` (reused, unmodified), a new unit-routing helper
  (hour vs. non-hour) shared by both new rate builders, a new transcript boundary-scan helper
  (mirrors the existing `probe_todo_from_transcript` full-replay precedent — this codebase already
  reads transcripts line-by-line for derived state, so this isn't a new capability class).
- **Data Storage**: none — everything is computed per-render from `ctx.transcript` and
  `ctx.rate_limits`, both already present in `Context`.
- **Interface Design**: no external interface changes; this is internal to `status-line.py`'s
  segment set. `tools/setup.py`'s `SEGMENT_DEFAULTS`/inventory-description mirror and
  `tools/statusline.toml.sample` are updated to match (drop `alt_rate_limits`, add the two new
  keys) so the install wizard's segment picker stays accurate.

### Constraints

- **Performance**: the new transcript boundary-scan for FR-2 adds one additional pass over the
  transcript file (substring pre-filter, not full JSON parse per line) on sessions that enable
  `chat_size` (on by default). This is bounded by file size the same way `probe_todo_from_transcript`
  already is; no new caching layer is introduced beyond the existing per-render `Context.probe_cache`
  memoization (`_memo`).
- **Compatibility**: `.jsonl` compaction-marker fields (`compactMetadata`, `subtype`) are described
  by Claude Code as **internal, version-dependent format** ("The entry format is internal to
  Claude Code and changes between versions" — official sessions doc). This probe degrades quietly
  (treats the file as having 0 compactions) if the marker shape is ever renamed/removed in a future
  Claude Code version — it must never raise or block `chat_size` from rendering the total.
- **Security**: none beyond what already applies to transcript reads (local file, already trusted
  by the existing `chat_size`/todo probes).
- **Scalability**: N/A — single-user, per-render, local-file scope.

### Risk Assessment

- **Technical Risks**: the compaction-marker JSON shape is undocumented/internal and could change
  between Claude Code versions. *Mitigation*: treat any parse/shape mismatch as "0 compactions
  found," never as an error — `chat_size` always falls back to showing just the total, its current
  behavior.
- **Dependency Risks**: none — no new external dependency; uses the stdlib `json` already imported.
- **Schedule Risks**: low — both FRs are isolated, additive changes to a single file with existing
  test infrastructure (`tests/test_status_line.py`) covering the same patterns (`util_first_fitting`
  tiering, `theme.ramps` lookups, transcript-path probes).

## Acceptance Criteria

### Functional Acceptance

- [ ] `alt_rate_limits` (segment, builder, `SEGMENTS`/`LAYOUT` entries, `setup.py` mirror, sample
      TOML line) is fully removed with no legacy alias.
- [ ] `alt_h_rate_limit` renders `5h: NN% (↺ HH:MM)` when room allows, else `5h: NN%`, else hides;
      reset stamp is time-only, never a date.
- [ ] `alt_w_rate_limit` renders `7d: NN% (↺ Ddd HH:MM)` when room allows, else `7d: NN%`, else
      hides; reset stamp uses weekday abbreviation, never `mmm dd`.
- [ ] Under column pressure, `alt_w_rate_limit` is dropped before `alt_h_rate_limit` (verified by
      a fixed-width render test with both segments enabled and just enough room for one).
- [ ] `chat_size` with 0 compactions shows just the total at both tiers.
- [ ] `chat_size` with ≥1 compactions shows `since/total (Nx)` when room allows, else `since` alone,
      else hides.
- [ ] `chat_size`'s color ramp is driven by `since_bytes`, not `total_bytes`.
- [ ] `seg_context` is byte-for-byte unmodified by this PRD (diff-verified).
- [ ] A malformed/renamed compaction-marker shape degrades to "0 compactions," never raises.

### Quality Standards

- [ ] Code Quality: follows existing `util_/probe_/seg_/cfg_` naming and `_memo` caching
      conventions; `make lint` (ruff/pylint/pyright/vulture/shellcheck) clean.
- [ ] Test Coverage: new tests in `tests/test_status_line.py` for both segments' tiering, drop
      order, the boundary-scan probe (0/1/N compactions, malformed marker), and the ramp-source
      change; `make test` green.
- [ ] Performance Metrics: no measurable `render_time` regression beyond the cost of one additional
      transcript read (verified via the existing `render_time`/`slowest` diagnostics).
- [ ] Security Review: N/A (local file reads only, no new trust boundary).

### User Acceptance

- [ ] User Experience: `--doctor` renders all segments cleanly with the new keys; a real narrow-
      terminal smoke test shows the documented drop order.
- [ ] Documentation: README's segment list and `statusline.toml.sample` reflect the two new
      rate-limit keys (removing `alt_rate_limits`) and the updated `chat_size` description,
      including the "never shrinks on disk, but `since`/`(Nx)` reflect the last compaction"
      distinction from `context`.
- [ ] Training Materials: N/A.

## Execution Phases

### Phase 1: Preparation

**Goal**: Confirm current behavior as a regression baseline and land the shared unit-routing
helper.
- [ ] Task 1: Snapshot current `alt_rate_limits`/`chat_size` test behavior (baseline).
- [ ] Task 2: Add the hour-vs-non-hour bucket router (pure function, unit-tested standalone).
- **Deliverables**: baseline test run recorded; router helper + tests green.
- **Time**: 0.5 day.

### Phase 2: Core Development

**Goal**: Implement both FRs.
- [ ] Task 1: Replace `seg_alt_rate_limits` with `seg_alt_h_rate_limit` + `seg_alt_w_rate_limit`;
      update `SEGMENTS`, `LAYOUT` (weekly right of hourly), remove `alt_rate_limits` everywhere.
- [ ] Task 2: Add the transcript compaction-boundary probe (`since_bytes`/`total_bytes`/
      `compact_count`); rewire `seg_chat_size`'s tiering and ramp source.
- [ ] Task 3: Update `tools/setup.py` (`SEGMENT_DEFAULTS`, inventory descriptions) and
      `tools/statusline.toml.sample`.
- **Deliverables**: both FRs implemented behind the existing registry; `make test` green.
- **Time**: 1.5 days.

### Phase 3: Integration & Testing

**Goal**: Full-suite verification + drop-order and malformed-input coverage.
- [ ] Task 1: Width-pressure tests proving weekly drops before hourly.
- [ ] Task 2: Compaction-count tests (0 / 1 / 3 boundaries; malformed/renamed marker shape).
- [ ] Task 3: `--doctor` full-segment smoke; confirm `seg_context` untouched via diff.
- **Deliverables**: `make test` + `make lint` clean; doctor exit 0.
- **Time**: 1 day.

### Phase 4: Deployment

**Goal**: Docs + release.
- [ ] Task 1: README segment-list + sample TOML update; document the `chat_size` vs `context`
      distinction plainly (disk total vs. live post-compaction usage) so this doesn't need
      re-explaining later.
- [ ] Task 2: Commit, gate, merge per the project's normal branch-finish flow.
- **Deliverables**: README/sample updated; branch ready to merge.
- **Time**: 0.5 day.

---

**Document Version**: 1.0
**Created**: 2026-07-27
**Clarification Rounds**: 6
**Quality Score**: 90/100
