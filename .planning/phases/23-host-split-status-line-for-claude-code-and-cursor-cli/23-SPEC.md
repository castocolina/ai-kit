# Phase 23: Host-split status line for Claude Code and Cursor CLI — Specification

**Created:** 2026-10-14
**Ambiguity score:** 0.16 (gate: ≤ 0.20)
**Requirements:** 12 locked

## Goal

ai-kit ships a Cursor CLI status line next to the Claude Code one, from one host-neutral core.
The phase delivers three parts in order:
- (A) `tools/status-line.py` splits into `common_*` and `claude_*` modules with a thin
  `claude-status-line.py`, rendering byte-identically;
- (B) a `cursor-status-line.py` shows model, context and three quota segments, colored by the
  shared gap gauge, with all network and credential code isolated in `cursor_quota.py`;
- (C) `setup.py` and the wizard wire every detected host.

## Background

- **Design input:** `.planning/specs/2026-10-10-host-split-statusline-design.md` and its
  `-REVIEW.md`, copied on 2026-10-14 from branch `spec/host-split-statusline` as the ROADMAP
  required. The review's owner decisions are final:
  - a hard rename with no shim;
  - `claude_host.py`/`cursor_host.py` own the `HOST` objects;
  - `AI_KIT_CURSOR_*` env overrides;
  - one TOML per host;
  - the full wizard flow per host;
  - Dashboard API quota flagged inferred.

  Its open findings R3-1..R3-6 (the wizard's host-keyed context, quota normalization, external
  providers isolated from Claude behavior, credential transport, race-safe create-if-absent,
  Cursor toggles) are HOW items for discuss-phase.
- **ROADMAP wins over the 2026-10-10 design where they differ.** Three quota segments (API,
  included, extra against its ceiling), each individually placeable, and one shared gap gauge
  on both hosts replace the design's single included-quota segment plus on-demand status. This
  matches the user's standing decision (memory: gauge bands 5/10/15 on both hosts; Cursor quota
  = API / included / extra).
- **The gap gauge already exists** on this branch (`d23749b..52def0f`). Its spec
  (`docs/superpowers/specs/2026-10-09-statusline-quota-window-gap-design.md`) was marked
  accepted on 2026-10-14, and PROJECT.md's burn-pace decision is marked superseded.
- **Cursor `cli-config.json` precedence** is documented: `CURSOR_CONFIG_DIR`, then
  `$XDG_CONFIG_HOME/cursor` on Linux/BSD, then `~/.cursor`. `tools/setup.py` honors only
  `CURSOR_CONFIG_DIR > ~/.cursor`.
- **Reference only:** POC branch `poc/cursor-statusline` (never merged); research 13 and 13b;
  todo `2026-10-12-promote-cursor-statusline-poc-into-999-4.md` on main.
- **Precondition for planning, owned by the user:** land or shelve
  `worktree-context-tools-manager-plan1`, which rewrites the same `setup.py`/`wizard_app.py`
  seams. It blocks planning Parts A and C, not this spec.

## Requirements

1. **Classification audit** (STL-01).
   - Current: `tools/status-line.py`, about 141 top-level definitions.
   - Target: a table of every top-level definition with its target module, its reason (host-neutral versus Claude-only data or semantics) and its fate (reused, generalized, deleted). A definition is host-neutral only if neither its data source nor its logic names a host.
   - Acceptance: the table covers 100% of the AST's top-level definitions (checked by a script) and is committed before Part A planning closes.
   - *Amended 2026-10-14 (23 D-01):* "definition" includes the 41 module-level assignments (`SEGMENTS`, `LAYOUT`, `PINNED`, the effort and ramp tables), so the table has 182 rows with the 141 def/class rows as a subtotal.

2. **Split** (STL-01).
   - Current: one file.
   - Target:
     - `common_*` modules, `claude_*` modules and a thin `tools/claude-status-line.py`.
     - `statusline.toml.sample` becomes `claude-statusline.toml.sample`.
     - The split files are ruff/pylint clean.
     - `tests/test_arch.py` gains a dependency-direction rule (common never imports a host module) and banner/prefix rules for the new modules, each with non-vacuity tests.
     - `docs/architecture/status-line-pipeline.md` is fixed or deleted.
   - Acceptance: the existing `tests/test_status_line.py` suite passes with loaders moved and no assertion changed. Golden renders of every existing payload fixture are byte-identical.

3. **Migration in the same change** (STL-01).
   - Current: n/a.
   - Target:
     - The rename is hard, with no shim.
     - `setup.py`'s statusline refresh rewrites a Claude `statusLine.command` that points at ai-kit's old script, idempotently and atomically.
     - It moves `ai-kit/statusline.toml` to `claude-statusline.toml` when the destination is absent; when both exist, it warns and changes nothing.
     - A foreign command is untouched.
     - Every reference is updated: `rg "status-line\.py|statusline\.toml"` returns only migration code and history. *(Amended 2026-10-14, 23 D-04: the check is the anchored `rg -P '(?<![\w-])(status-line\.py|statusline\.toml)'`, so `claude-status-line.py` does not match, with the history allowlist `.planning/**`, `docs/superpowers/**`, `docs/prds/**`.)*
   - Acceptance: upgrade-path tests (old to new, second run is a no-op, both-present warns, foreign untouched).

4. **Shared gap gauge** (STL-02).
   - Current: the Claude quota windows use it.
   - Target: one gauge function in `common_*` colors every quota segment on both hosts. It compares spend % against elapsed % of the window or cycle (bands ≤5 green, <11 yellow, 11–15 orange, >15 red) and keeps the `+`/`-` sign.
   - Acceptance: Claude renders are unchanged. Cursor segments use the same function (an import test) with cycle-based elapsed time. *(Amended 2026-10-14, 23 D-09: each Cursor segment declares its own window — the included-usage period for included and API, the billing cycle for extra; an underivable window renders neutral with no sign.)*

5. **Spike before Part B planning** (STL-04).
   - Current: facts from the bundle only.
   - Target:
     - Capture one real Cursor statusLine payload. This edits the real `~/.cursor/cli-config.json`, so it needs the user's explicit approval, an atomic backup and a verified restore. *(Amended 2026-10-14, 23 D-14: the capture runs `cursor-agent` with `CURSOR_CONFIG_DIR` pointing at a scratch copy, so the real file is never written. The CLI rewrites its own config during use, so a byte-identical restore is unreliable. Approval is still needed: the run reads the real token through `auth.json` and consumes quota.)*
     - Call the three Dashboard methods from a throwaway script under `./tmp/` and record units and on-demand classification.
     - Measure call latency (p50/p95) and the real update cadence, including a kill by the next update.
     - Choose an inline fetch with a cache, or a background refresher, from the data.
   - Acceptance: the phase RESEARCH records the payload shape (redacted), units, latencies, cadence, the kill test and the chosen design with its reason. Any fact that differs from the design spec amends it.

6. **Cursor line** (STL-02).
   - Current: none.
   - Target:
     - `tools/cursor-status-line.py` renders model (with `model.param_summary`) and context.
     - It renders three separately placeable quota segments: API usage, included usage (auto plus models) and extra (on-demand) usage against its ceiling.
     - It renders the billing-cycle reset in local time.
     - Every quota value is marked inferred (`≈`).
   - Acceptance: synthetic-payload tests per segment, including null and absent fields, each on-demand state (fixed, unlimited, disabled, unavailable) and `render_width_chars` precedence.

7. **Quota normalization** (STL-03).
   - Current: none.
   - Target: one deterministic mapping from the three Dashboard responses into a typed `QuotaResult`. It covers units (cents versus dollars), source precedence for billing dates and limits, on-demand classification precedence, and zero or absent limits.
   - Acceptance: table tests built on the spike's redacted real responses, plus synthetic edge cases.

8. **Credential and transport boundary** (STL-03).
   - Current: none.
   - Target:
     - `cursor_quota.py` is the only module that touches the network or the credential file.
     - It speaks HTTPS only, to `*.cursor.sh` (`CURSOR_API_ENDPOINT` must match), and follows no cross-origin redirect.
     - The token is read only and never persisted, logged or cached.
   - Acceptance: fake-server tests for an http endpoint, a foreign host and a cross-origin redirect (all refused), a token-never-in-cache assertion, and an arch test that no other module imports networking. The phase runs `/gsd-secure-phase`.

9. **Cache and failure behavior** (STL-03).
   - Current: none.
   - Target:
     - The cache keeps `data_fetched_at` apart from `last_attempt_at`/`last_error`.
     - Quota is hidden on 401/403 and after `cycle_end`.
     - Refresh is single-flight across processes, with an expiring lock and a negative cache.
     - Every `git` call has a timeout.
     - A bad TOML value renders an error segment instead of crashing.
     - `CC_AI_KIT_*` does not affect a Cursor render.
   - Acceptance: the tests listed in design §7 Part B pass (fresh/stale/negative, 401, timeout, killed refresher, concurrent renders, env isolation).

10. **External providers unchanged** (STL-02).
    - Current: external segment providers get Claude's input.
    - Target: a Claude provider's input, environment and cache namespace are exactly as before. Cursor providers identify their host another way.
    - Acceptance: a regression test with a strict existing provider sees byte-identical input.

11. **Multi-host setup** (STL-05).
    - Current: Claude-only `--with-statusline`.
    - Target:
      - `setup.py --with-statusline[=claude,cursor]` wires each detected host headless. An unknown or undetected name is an error, and a foreign entry is never overwritten headless.
      - Per-host detect/wire/unwire use the same `unset`/`ours`/`foreign` classification and atomic primitives. Cursor resolves `cli-config.json` with the documented precedence.
      - Host TOMLs are created with a race-safe create-if-absent.
      - `statusline-doctor.py --host claude|cursor` reports fetch status and confidence.
    - Acceptance: the detect/wire matrix (3 states × 2 hosts × interactive/headless), semantic preservation of unrelated keys, per-host uninstall, and failure-injected TOML writes.

12. **Wizard and close-out** (STL-05).
    - Current: one status-line flow.
    - Target:
      - The wizard runs verify/replace/keep, then Arrange, per detected host (Claude then Cursor) through a host-keyed context, and a declined host is left untouched.
      - Both entries are reachable after v1.3 merges to `main`.
      - `make test` and `make validate` are green.
      - The wizard is run under `uv run`, and a real `cursor-agent` is run with the wired line.
    - Acceptance: a PTY test of the two-host sequence. Both gates are green, and the live runs are recorded. Spawned processes are killed.

## Boundaries

**In scope:**
- Parts A, B and C above, the spike, the doctor's `--host`, and the arch rules

**Out of scope:**
- opencode/codex status lines; Cursor `autorun`/`vim`/`session_name` segments; team/enterprise spend views (design §9)
- Promoting the POC branch (reference only)
- A byte-preserving JSON editor (semantic preservation only)
- The plan1 land-or-shelve decision (the user's)

## Constraints

- Runtime code stays stdlib-only, and network code exists only in `cursor_quota.py`.
- Any write to the real `~/.cursor/cli-config.json` (spike or setup) needs the user's approval, with an atomic backup and restore. The spike avoids it entirely (D-14); setup re-reads and re-classifies immediately before its atomic write (D-23).
- Never use real configs or tokens as fixtures; real Dashboard responses are redacted.
- The hard-rename upgrade gap is accepted (owner decision) and is not reopened.

## Acceptance Criteria

- [ ] The audit table covers every top-level definition
- [ ] The Claude render is byte-identical; the split files are lint-clean; the arch rules have non-vacuity tests
- [ ] Migration tests pass, and `rg` finds only intentional references
- [ ] Both hosts' quota segments use the one gauge
- [ ] The spike records payload, units, latency, cadence and the chosen fetch design
- [ ] The Cursor line renders all segments, with `≈` on quota
- [ ] Normalization tests pass on redacted real responses
- [ ] Transport tests refuse http, foreign hosts and cross-origin redirects; the token is never cached
- [ ] Cache, 401/403, cycle-end, timeout and single-flight tests pass
- [ ] A strict existing provider sees identical input
- [ ] The setup matrix, uninstall and atomic TOML tests pass
- [ ] The two-host wizard PTY test passes; `make test` and `make validate` are green; live runs recorded
- [ ] MUST NOT: the bearer token never leaves `cursor_quota.py` (no log, cache or other module)
- [ ] MUST NOT: setup never overwrites a foreign `statusLine` headless, on any host

## Edge Coverage

**Coverage:** 36/39 applicable edges resolved · 3 unresolved (floor recomputed 2026-10-14 after the R4 amendment)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | A function and a same-named class are separate rows |
| empty | R1 | ✅ covered | A definition with no host dependency defaults to host-neutral only after review |
| encoding | R1 | 🧪 backstop | The table is ASCII Markdown |
| ordering | R1 | ✅ covered | Rows follow source order, and the script checks the count |
| adjacency | R2 | ✅ covered | A helper used by both hosts lands in `common_*`, never duplicated |
| empty | R2 | ✅ covered | An empty payload renders the same fallback line before and after |
| ordering | R2 | ✅ covered | Segment order is unchanged for every fixture |
| concurrency | R2 | 🧪 backstop | Rendering is single-process; no shared state added |
| adjacency | R3 | ✅ covered | A command that points at a different `status-line.py` is foreign and untouched |
| empty | R3 | ✅ covered | No existing wiring: migration is a no-op |
| ordering | R3 | ✅ covered | The command rewrite precedes the TOML move, and both are atomic |
| adjacency | R4 | ✅ covered | A gap of exactly 5 is green, 11 orange, 15 orange, 15.01 red |
| empty | R4 | ✅ covered | An uncomputable elapsed % renders white with no sign |
| ordering | R4 | 🧪 backstop | The sign is applied after rounding the display, color on the raw value |
| concurrency | R4 | 🧪 backstop | The gauge is a pure function of (percent, window, now); each segment computes its own |
| idempotency | R5 | ✅ covered | ~~The restore leaves `cli-config.json` byte-identical to the backup~~ *(superseded, D-14)* The real `cli-config.json` is never written; the scratch dir is deleted after the capture |
| concurrency | R5 | ✅ covered | The kill-by-next-update test is part of the spike |
| adjacency | R6 | ✅ covered | Included and extra segments render independently when one is absent |
| empty | R6 | ✅ covered | A payload with no `model.param_summary` omits it |
| ordering | R6 | ✅ covered | Each segment is individually placeable via the layout |
| concurrency | R6 | 🧪 backstop | Render reads the cache only |
| unclassified | R7 | ⚠ UNRESOLVED | No shape cue; normalization tables are specified in Acceptance |
| boundary | R8 | ✅ covered | `api2.cursor.sh` passes; `cursor.sh.evil.com` and `http://api2.cursor.sh` fail |
| adjacency | R8 | ✅ covered | ~~A same-origin redirect is followed~~ *(superseded, D-15)* Every redirect is refused and reported as a network error (urllib turns a redirected POST into a bodiless GET carrying the bearer) |
| empty | R8 | ✅ covered | No `auth.json` means no fetch and a hidden quota |
| ordering | R8 | 🧪 backstop | Endpoint validation precedes the token read |
| precision | R8 | 🧪 backstop | Host matching is exact-suffix on a dot boundary |
| concurrency | R8 | 🧪 backstop | Single-flight refresh (R9) bounds concurrent requests to one |
| adjacency | R9 | ✅ covered | `now == cycle_end` hides the quota |
| empty | R9 | ✅ covered | An empty cache renders no quota, then refreshes once |
| ordering | R9 | ✅ covered | A newer `last_error` never overwrites older good data |
| unclassified | R10 | ⚠ UNRESOLVED | No shape cue; the strict-provider regression is specified |
| adjacency | R11 | ✅ covered | A host dir that exists but holds no config file is detected and gets a new file |
| empty | R11 | ✅ covered | No host detected: headless reports nothing to wire, exit 0 |
| encoding | R11 | 🧪 backstop | JSON is re-serialized with 2-space indent (semantic preservation) |
| ordering | R11 | ✅ covered | Claude is wired before Cursor |
| idempotency | R11 | ✅ covered | A second headless run is a no-op |
| concurrency | R11 | ✅ covered | Race-safe create-if-absent never overwrites a concurrently created TOML |
| unclassified | R12 | ⚠ UNRESOLVED | No shape cue; the PTY test and live runs are specified |

## Prohibitions (must-NOT)

**Coverage:** 3/3 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT persist, log or pass the Cursor bearer token outside `cursor_quota.py` | R8 | resolved | test |
| MUST NOT send the token over http, to a non-`*.cursor.sh` host, or across a redirect | R8 | resolved | test |
| MUST NOT overwrite a foreign `statusLine` headless | R11 | resolved | test |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | Three ordered parts |
| Boundary Clarity   | 0.85  | 0.70 | ✓      | Design §9 exclusions kept |
| Constraint Clarity | 0.82  | 0.65 | ✓      | Credential boundary, approval for `~/.cursor` |
| Acceptance Criteria| 0.78  | 0.70 | ✓      | 14 pass/fail criteria |
| **Ambiguity**      | 0.16  | ≤0.20| ✓      | Initial 0.23 (requirements were TBD); one round |

## Interview Log

`--auto`, one round. No item needed a decision model: each open point was settled by a recorded owner decision, by the ROADMAP (newer than the design), or by documented Cursor behavior. Rule: best design over the smallest diff.

| Round | Perspective | Question summary | Laya (advisory) | TypeSafe (advisory) | Decision locked |
|-------|-------------|------------------|-----------------|---------------------|-----------------|
| 1 | Researcher | Design (2026-10-10) versus ROADMAP (2026-10-13) segments? | – | – | ROADMAP wins: three quota segments plus the shared gauge (user memory confirms) |
| 1 | Boundary Keeper | Requirements were TBD | – | – | STL-01..05 defined from the five success criteria |
| 1 | Failure Analyst | Which `cli-config.json` path? | – | – | The documented precedence, CURSOR_CONFIG_DIR > XDG > ~/.cursor (R11); the hooks' `cursor_dir` is a discuss item |
| 1 | Simplifier | Do the prerequisites block the spec? | – | – | The spec copy and the gap-spec acceptance were done; the plan1 decision is the user's and goes on the ledger |

---

*Phase: 23-host-split-status-line-for-claude-code-and-cursor-cli*
*Spec created: 2026-10-14*
*Next step: /gsd-discuss-phase 23 — implementation decisions (how to build what's specified above)*
