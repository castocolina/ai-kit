# Status-line External Drop-in Segments — Product Requirements Document (PRD)

> Epic **E4c** of the ai-kit status-line overhaul (was E4b before the color subsystem took
> that slot). **Split out of E4a** (status-line config). E4a ships the config engine; E4c
> adds the extensibility layer — user-supplied drop-in segment providers — on top of it.
> Scheduled **after E5**; not on E5's critical path. Depends on **E4a** (config model +
> resolved layout).

## Requirements Description

### Background
- **Problem**: even with E4a's config (toggles, layout, palette), there is no way to add
  a *new* segment — e.g. "AWS session expires in 12m" — without patching
  `tools/status-line.py`. The author has already had to hand-patch a custom segment on
  another machine.
- **Users**: anyone who wants a status-line datum ai-kit doesn't ship, without forking.
- **Value**: drop an executable in a directory and it appears as a segment on the next
  refresh — context-aware (it sees the workspace dir and the status JSON), bounded
  (timeout + TTL cache), and safe (display-text only; no shell-eval, control sequences
  stripped). The upstream source file stays the default.

### Feature Overview
- **Core**: discover executables in a segments directory; place each via a metadata
  header into E4a's resolved layout; execute with a timeout, feeding it the status JSON on
  stdin and running in the workspace dir; sanitize output to display text (SGR colors
  only); cache output per-provider with a TTL; degrade safely on any failure.
- **Boundaries (in)**: external-segment discovery, header grammar, execution + timeout,
  output sanitization + width truncation, placement into the layout, TTL caching, the
  `[external]` config block + env scalars (added to E4a's schema), README docs + a sample
  provider, and tests for all of it.
- **Boundaries (out)**: the E4a config engine itself (tiers, toggles, layout, palette,
  recipe, introspection); the E5 wizard; a curated library of ready-made providers.

### User Scenarios
- Add an AWS-session-expiry segment: drop an executable in `~/.config/ai-kit/segments/`
  with `# ai-kit-segment: line=2 after=clock` — it appears next refresh, cached 30s.
- A provider keyed off the current directory picks its AWS profile from
  `workspace.current_dir` (its cwd) and the status JSON on stdin.

### Detailed Requirements

**External segment contract**
- Discovery: each executable file in the segments dir is a provider. Directory:
  `${CC_AI_KIT_SEGMENTS_DIR:-${[external].dir:-${XDG_CONFIG_HOME:-~/.config}/ai-kit/segments}}`.
- Metadata header (first 10 lines), regex-matched:
  `# ai-kit-segment: line=<N> (after=<key>|before=<key>|start|end) [id=<slug>] [timeout=<s>] [ttl=<s>]`
  - Defaults: `line` = last layout row, position = `end`, `id` = filename stem,
    `timeout` = 2s, `ttl` = `[external].ttl`.
- Input: the script receives the **same status JSON Claude passes to status-line** on
  **stdin**, and runs with **cwd = `workspace.current_dir`** — so it can be context-aware
  (e.g. pick an AWS profile by directory). Env is inherited.
- Execution: run with the timeout; capture stdout. Output handling:
  - take the **first non-empty line**, strip the trailing newline;
  - allowed inline escapes are **SGR color codes only** (`\033[…m`); any other
    control/CSI sequence is stripped (no cursor moves, no clears);
  - width is measured with the same `visible_width` used for built-in segments, and the
    line is truncated to the available budget like any other segment.
  - Non-zero exit, timeout, or empty output → segment omitted; never breaks rendering.
- Placement: insert into the resolved layout (E4a) at the declared row/position.
  - Target row gated out by `min_rows` → simply not shown.
  - `line=<N>` out of range → clamp to the last existing row + a dim stderr warning.
  - Multiple externals resolving to the same slot → deterministic order by **filename,
    then `id`**.
- Caching: per `id`, output cached `ttl` seconds at
  `${XDG_CACHE_HOME:-~/.cache}/ai-kit/segments/<id>`; stale or missing → re-run.

**Config surface (added to E4a's schema)**
```toml
[external]
ttl = 10                   # seconds (overridden by CC_AI_KIT_EXTERNAL_TTL)
dir = "~/.config/ai-kit/segments"
```
- Env: `CC_AI_KIT_SEGMENTS_DIR` (dir), `CC_AI_KIT_EXTERNAL_TTL` (int seconds). Env wins
  over the file per E4a's precedence (default < file < env).
- The E4a shipped recipe gains a commented `[external]` block (no-op until edited).

### Edge Cases
- External script not executable → skipped with a warning.
- Cache dir unwritable → run without caching (best effort).
- A `line=<N>` references a row that is gated out by `min_rows` → not rendered.
- Provider prints multi-line / huge output → only the first non-empty line, truncated.
- Provider hangs → killed at `timeout`; segment omitted.

## Design Decisions

### Technical Approach
- **No new deps**: `subprocess` (already used), `os`/`time`. Preserves zero-install
  execution.
- **External segments modeled as synthetic builders** inserted into E4a's resolved
  layout, so the existing packing/overflow logic handles them unchanged. This is the
  seam that made the E4a/E4c split near-zero-rework.
- **Safety**: external output is treated as display text only (no shell-eval); control
  sequences other than SGR are stripped; failures never break rendering.

### Key Components
- `discover_external(cfg)` — parse headers → list of external segment specs.
- `run_external(spec, cfg)` — TTL-cached execution with timeout.
- Placement of synthetic builders into E4a's `cfg.layout`.
- A sample external segment shipped as a reference (e.g. clock or AWS-expiry stub).

### Constraints
- **Performance**: external scripts only re-run past their TTL. Warm cache adds ~one
  small file read per provider. Cold runs bounded by each script's `timeout`.
- **Compatibility**: no providers present → behavior identical to E4a-only.
- **Safety**: never crash on a bad/slow/failing provider.

### Risk Assessment
- **External-script latency/abuse**: bounded by per-script timeout + TTL cache; document
  that providers should be fast and print one line.
- **Security surface**: running arbitrary executables from a directory — document the
  trust model (the dir is user-owned; ai-kit never installs providers).

## Acceptance Criteria

### Functional Acceptance
- [ ] An executable in the segments dir with a valid header renders at the declared row/position.
- [ ] External output is cached for its TTL and re-runs after it expires.
- [ ] External timeout / non-zero exit / empty output omits the segment without breaking the line.
- [ ] An external script receives the status JSON on stdin and runs in `workspace.current_dir`.
- [ ] External output keeps SGR colors but has other control sequences stripped, and is width-measured/truncated like a built-in segment.
- [ ] Out-of-range `line=N` clamps to the last row; same-slot externals order deterministically by filename then id.
- [ ] `CC_AI_KIT_SEGMENTS_DIR` / `CC_AI_KIT_EXTERNAL_TTL` override the `[external]` file values.
- [ ] Non-executable provider is skipped with a warning; unwritable cache dir runs without caching.

### Quality Standards
- [ ] Existing `status-line.py` tests still pass; new tests cover discovery, placement, timeout, TTL, sanitization, and degradation.
- [ ] No new third-party dependencies.

### User Acceptance
- [ ] README documents the external-segment header grammar, the input contract (stdin JSON, cwd), caching, and the trust model.
- [ ] A sample external segment ships as a copy-and-edit starting point.

## Execution Phases

### Phase 1: Discovery + execution
**Goal**: find providers and run them safely.
- [ ] Header grammar parser + `discover_external`.
- [ ] `run_external` with timeout; output sanitization (SGR-only) + first-non-empty-line.
- [ ] Tests with fixture scripts (valid header, no header, slow/timeout, failing).
- **Deliverables**: a provider runs and its line is captured + sanitized.

### Phase 2: Placement + caching
**Goal**: integrate into the layout and bound cost.
- [ ] Insert synthetic builders into E4a's resolved layout (position, clamp, ordering).
- [ ] TTL cache at `${XDG_CACHE_HOME:-~/.cache}/ai-kit/segments/<id>`.
- [ ] `[external]` config block + env scalars (on E4a's schema); recipe gains commented block.
- [ ] Tests for placement, clamping, deterministic ordering, TTL behavior.
- **Deliverables**: AWS-session-style segment works as a drop-in.

### Phase 3: Docs + sample
**Goal**: discoverability.
- [ ] README section (header grammar, input contract, caching, trust model).
- [ ] Ship a sample external segment.
- **Deliverables**: a documented, copy-and-edit extension path.

---

**Document Version**: 1.0
**Created**: 2026-06-18
**Source**: split from `statusline-config-extensibility-v1.0-prd.md` (E4a) during an E4a
scope/sequencing brainstorm.
**Depends on**: E4a (config engine + resolved layout). **Scheduled**: after E5.
