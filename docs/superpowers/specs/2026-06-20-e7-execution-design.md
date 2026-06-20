# E7 — Install UX + Worktree Visibility — Execution Design

> **Purpose.** This document closes the four E7 findings to *final, build-ready* designs and
> defines an **autonomous `/loop` execution strategy** that an agent drives to completion with
> agent-run E2E verification. It supersedes the "open" status of FR-7.3 / FR-7.4 in
> `docs/prds/e7-install-ux-worktree-visibility-v1.0-prd.md` and adds **FR-7.5** (sysmem
> bootstrap). No implementation happens in the planning session that produced this doc.

- **Date**: 2026-06-20
- **Source PRD**: `docs/prds/e7-install-ux-worktree-visibility-v1.0-prd.md`
- **Execution model**: single dynamic `/loop` session, on-disk ledger, agent-verified gates.
- **Companion artifacts**: the PLAN ledger (`docs/superpowers/plans/2026-06-20-e7-loop-PLAN.md`)
  and the launch guide (`docs/superpowers/LOOP-GUIDE-e7.md`).

---

## 0. Fresh-start recipe (start from zero)

The existing `feat/e7-install-ux-fixes` branch is abandoned: its tip `36bc313` and all
uncommitted WIP implement the **rejected "list of all worktrees" design**. Only one commit on
it is worth keeping — `1236345` (FR-7.1), which is **branch-only and not on `main`**.

```
# main already carries the E7 PRD (4722a60) and the E6 merge.
git switch main && git pull             # ensure up to date
git switch -c feat/e7-loop              # fresh branch off main
git cherry-pick 1236345                 # FR-7.1 adopt-links (clean, +148 lines, 8 tests)
make test                               # confirm green baseline before the loop starts
```

Everything else is rebuilt by the loop from this doc + the PLAN ledger. The old branch is left
untouched on disk for reference but is never built upon.

---

## 1. Final designs — the four findings + FR-7.5

### FR-7.1 — Adopt predecessor skill links · **DONE (adopted via cherry-pick)**
No new work. `predecessor_candidates()` + `adopt_predecessor_links()` in `tools/setup.py`,
wired into `cmd_install` after `prune_stale`, covered by `TestAdoptPredecessorLinks` (8 tests).
The loop's first ledger task only confirms the cherry-pick applied and tests pass.

### FR-7.2 — `branch` and `worktree` as two independent segments · **FINAL**

- **`branch` is now *only* the branch.** The 🌳/🌿 glyph baked into `seg_branch`
  (`status-line.py:883`) is **removed**. Branch has nothing to do with worktrees.
- **`worktree` is a separate, independent segment** showing only the worktree the current
  session is in — the *active* one, never a list, even when 10 exist:
  - In a linked worktree → `⎇ <worktree-basename>` (basename, truncated to 20 chars with `…`,
    the same treatment `path` gives a long repo dir).
  - In a repo but on the main checkout → struck-through `⎇ wt` placeholder.
  - Not in a git repo → hidden (returns `None`), like `branch`.
- **Shared core probe (DRY).** `branch`, `dirty`, and `worktree` are independent *segments* but
  read from **one** cached `git_snapshot(work_dir)` core function — a single probe feeds all
  three. The loop applies `/simplify` (or `/reducing-entropy`) so there is zero duplicated git
  querying across the three builders. Branch + worktree info (rarely changing) are cached ~5s;
  `dirty` is always read fresh.
- **ON by default**, toggled via `segments.worktree` like any other segment. The **starting state
  on `feat/e7-loop`** (= `main`) is the legacy opt-in glyph-on-branch design: `seg_branch`
  (`status-line.py:887`) bakes the 🌳/🌿 glyph at L891; worktree detection is gated by a
  `[git] worktree` boolean knob (`_GIT_DEFAULTS = {"worktree": False}` at `status-line.py:74`),
  read at ~L268, ~L1840, ~L1911 and via env `CC_AI_KIT_GIT_WORKTREE`; there is no separate
  worktree segment of any kind. FR-7.2 **migrates** this design: the `[git] worktree` knob and
  `CC_AI_KIT_GIT_WORKTREE` env read are removed and replaced by `segments.worktree` ON by default;
  the legacy `[git] worktree` TOML key becomes tolerated-but-ignored (no error); no plural
  `worktrees` segment ever existed on this branch and nothing of that kind requires removal.

**Cache TTL is a real config knob.** The shared probe TTL is configurable:
- TOML: `[git] cache_ttl = 5` — `[git]` is **no longer fully retired**; it now *recognizes*
  `cache_ttl` (seconds). The legacy `worktree` key under `[git]` is still tolerated-but-ignored
  (no error); any *other* `[git]` key still warns.
- Env override: `CC_AI_KIT_GIT_TTL` wins over the TOML value.
- Precedence: default `5` < TOML `[git] cache_ttl` < env `CC_AI_KIT_GIT_TTL`.

### FR-7.3 — Slowest-segment diagnostic + one shared SLO/SLA color ramp · **FINAL**

- **`slowest` is a normal segment, ON by default**, registered in `SEGMENTS` (default `True`),
  `BUILDERS`, and `LAYOUT` (sibling to `render_time`, on the diagnostic row). It names the
  single most-expensive segment of the last render: e.g. `🐌 todo 38ms`.
- **Per-segment timing.** The packer measures each segment's build time (via
  `time.perf_counter_ns()`, the same clock `render_time` already uses) and records the max.
- **One single shared SLO/SLA color ramp — not per-segment.** There is exactly **one** timing
  ramp applied to whatever segment is slowest: a single max SLO (green threshold) and single max
  SLA (yellow threshold), chosen with the most-expensive-average segment in mind. Reuses the
  existing ramp subsystem (`pick_color(pct, ramp)`, `Theme.ramps`, `_RAMP_DEFAULTS`), exactly as
  `render_time` already does (its own ramp `[("50ms","GREEN"),("150ms","YELLOW"),("inf","RED+bold")]`
  resolved to nanoseconds — green under SLO, yellow under SLA, red beyond):
  - A **single** new ramp band `[ramp.slowest]` (one SLO, one SLA) e.g.
    `[("15ms","GREEN"),("40ms","YELLOW"),("inf","RED+bold")]`. **No `[ramp.timing.<segment>]`
    per-segment overrides** — one ramp for all.
  - The `slowest` segment colors the culprit's `Nms` using this single ramp, regardless of which
    segment is the culprit.
  - `render_time` keeps its own existing dedicated ramp (unchanged).
- **No new color machinery.** Pure reuse of `pick_color` / `Theme.ramps` — a `/simplify` target,
  not a new subsystem.

### FR-7.4 — Wizard UX rework: hybrid **B + A** · **FINAL** (per `ui-ux-designer` review)

Build the **polished numbered menu (B)** as the always-correct contract on a **shared
selection-state model**, then layer **arrow-key chips (A)** as a purely additive enhancement.
**Reject full curses (C).** Rationale (grounded in how uv / rustup / SvelteKit `create` /
`npm init` / gum / fzf actually behave): the "modern installer feel" is approach A applied to a
*small bounded prompt block*, never a full-screen TUI. SvelteKit's `create` uses
`@clack/prompts`, which *is* approach A under the hood.

**Shared model.** One ordered selection-state object `(category, name, enabled)` + a `cursor`
(and, for the status-line flow, an `order` list). Both renderers mutate it identically; key
semantics map 1:1 (space/a/n/enter ⇄ number/a/n/enter). Build B first so the loop always has a
correct fallback to test against; A becomes individually revertable.

**Mode A specifics (all required):**
- **Bounded redraw, never full-screen / never alt-screen.** Render a fixed-height block; on each
  keypress move cursor up by block height (`\033[{n}A`) and rewrite each line with erase-line
  (`\033[2K`). Emit each frame in a single `write()`. Hide cursor (`\033[?25l`) during, restore
  (`\033[?25h`) after. The confirmed selection stays in scrollback.
- **Terminal teardown guaranteed.** A context manager saves `termios.tcgetattr(fd)` and restores
  via `tcsetattr(..., TCSADRAIN, saved)` + cursor-show in `finally`. SIGINT → restore + newline +
  exit 130. Keep the raw region as tight as possible (cooked mode everywhere else).
- **Windowed scrolling** when the list exceeds the viewport: read `shutil.get_terminal_size()`
  each frame, reserve header + footer lines, clamp a `top` so the cursor stays in view, show
  `▲ N more` / `▼ N more` edge affordances. Trap `SIGWINCH` to force redraw; truncate every line
  to `cols-1` with `…`.
- **Glyph-primary state (not color-only):** enabled `◉` (accent), disabled `◯` (dim); cursor
  gutter `❯`. Survives `NO_COLOR`/WCAG. ASCII fallback `[x]`/`[ ]`/`>` under narrow/`TERM=dumb`.
- **Live status-line preview** pinned as a footer **inside** the managed block, prefixed
  `preview ▏`, calling the real `render(data, cols, lines, cfg, theme)` with a fixed sample data
  dict + the live `cfg`, truncated to `cols`. Updates on every toggle/reorder.

**Conjunctive activation gate for mode A** (any failure → mode B):
`stdin.isatty() and stdout.isatty() and TERM not in {"dumb",""} and not NO_COLOR-forcing-plain
and cols >= 40 and rows >= 8`. Plus an explicit `--plain` / `AIKIT_PLAIN=1` escape hatch.

**Non-tty fallback contract (explicit + tested):** non-interactive/headless ⇒ **no prompting,
ever** — use explicit flags (`--skills=…`, `--segments=…`, `--yes`) or the computed default
selection, and proceed. The same final selection must be reachable purely via flags so CI and
the interactive path can't diverge. A test drives the selector with a non-tty stub and asserts
the default is returned with zero reads.

### FR-7.5 — Bootstrap offers example external segments (sysmem) · **FINAL (new)**

Today `examples/segments/sysmem` ships but the wizard never installs it. New behavior:
- During install the wizard **scans `examples/segments/`** and offers **every** example as a
  **pre-checked (default ON)** multi-select (reusing the same shared selection-state model as
  FR-7.4).
- For each chosen example: **copy** it to `~/.config/ai-kit/segments/` (XDG-aware), `chmod +x`,
  and **enable** its `segments.<id>` toggle in the resolved config. The `id` comes from the
  segment's `# ai-kit-segment:` header.
- Idempotent: re-running does not duplicate; an already-installed example is shown as such and
  not re-copied unless changed. Headless/non-tty ⇒ governed by the same flag/default contract
  (e.g. `--examples=all|none|<ids>`), never prompts.

---

## 2. Autonomous `/loop` execution strategy

### 2.1 Why a loop, and which `/loop`
`/loop <prompt>` **without an interval** runs in **dynamic / self-paced** mode: the model
re-fires the **same prompt verbatim** each iteration and schedules its own next wake-up. This is
the correct mode for a build pipeline (readiness-driven, not clock-driven). The interval form
(`/loop 10m …`) is wrong here — it fires on a clock.

**Key consequence:** each iteration may begin after a context compaction, with only a summary +
files + git history surviving. Therefore **all durable state lives on disk**, and the prompt is
**self-orienting** — it never assumes memory of the previous iteration.

### 2.2 The ledger — the loop's memory
`docs/superpowers/plans/2026-06-20-e7-loop-PLAN.md` holds atomic TDD tasks with checkboxes,
grouped by FR, each with an explicit **agent-run verification command** and a **done-definition**.
Checkboxes + git history *are* the loop's memory. The loop reads it first, every iteration.

### 2.3 The driver — one-shot prompt (idempotent)
Each iteration performs exactly:
1. **Orient** — read the PLAN ledger + `git log`/`git status`; determine the next unchecked task.
2. **Guard** — if no unchecked tasks remain, run the full completion-promise verification; if it
   passes, emit the completion promise and **stop** (schedule no wake-up); else re-open the
   failing item.
3. **Implement** — the next task via **TDD** (red → green → refactor). UI tasks consult
   `ui-ux-designer` at plan time.
4. **Verify** — dispatch a **fresh, independent verification subagent** (clean context) that runs
   the task's real test/E2E command and returns **PASS/FAIL with command output**. The driver
   never self-certifies. UI tasks additionally get a `ui-ux-designer` exec/e2e review.
5. **Commit** — only on PASS: check the box, atomic commit (one logical unit), update the ledger.
6. **FR gates** — when an FR's tasks all pass: run `/requesting-code-review` (quality/security)
   and `/simplify` (or `/reducing-entropy`) to drive entropy down; address findings as new ledger
   tasks before moving on.
7. **Re-evaluate** — schedule the next wake-up and repeat.

### 2.4 Verification gates (agent-driven E2E)
- **Per task:** fresh general-purpose subagent runs the unit/integration command, returns
  evidence. Box checked only on PASS.
- **UI tasks (FR-7.4 / FR-7.5):** `ui-ux-designer` gates **plan, exec, and e2e** (user directive).
- **TUI proof:** stdlib **`pty`-driven tests** — spawn the wizard on a pseudo-terminal, send
  arrow/space/enter byte sequences, assert on rendered frames. Mode A is verified headlessly.
- **Per FR:** `/requesting-code-review` (holistic, catches cross-file seam bugs the per-task
  checks miss — the E5 pattern) + `/simplify`.
- **Final:** one holistic `/requesting-code-review` over the whole branch before the promise.

### 2.5 Stop condition — the completion promise
Dynamic loop; the model stops scheduling wake-ups **only** when this is *literally* true:

> All PLAN ledger boxes are checked **AND** `make test` is green **AND** lint is clean **AND**
> `status-line.py --doctor` exits 0 with all segments rendering **AND** worktree E2E passes for
> **both** locations (`.claude/worktrees/` and `../worktrees/.ai-kit/`) and the main checkout
> shows struck `⎇ wt` **AND** the pty wizard E2E passes for both mode B and mode A **AND** the
> final `/requesting-code-review` has no unresolved HIGH/CRITICAL findings.

A **max-iteration cap** is the runaway backstop: if hit before the promise is true, the loop
stops and reports the remaining unchecked tasks + last failing evidence (no false "done").

### 2.6 Single session?
**One `/loop` session.** The work is large (~30–40 tasks across four FRs) and *will* compact
several times — but the design is built for exactly that: every iteration re-orients from the
on-disk ledger + git, so progress is never lost to compaction. Launch once with the one-shot
prompt; it self-paces to the promise or the cap. No multi-session hand-offs.

---

## 3. Acceptance criteria (roll-up)

- [ ] **FR-7.1**: cherry-pick applied; `TestAdoptPredecessorLinks` green.
- [ ] **FR-7.2**: `branch` shows only the branch (no 🌳/🌿); independent `worktree` segment shows
      `⎇ <name>` / struck `⎇ wt` / hidden; singular; ON by default; `worktrees` plural gone;
      `branch`+`dirty`+`worktree` share one cached probe; `[git] cache_ttl` + `CC_AI_KIT_GIT_TTL`
      both honored with correct precedence.
- [ ] **FR-7.3**: `slowest` segment ON by default names culprit + ms; **one single** shared
      SLO/SLA ramp `[ramp.slowest]` (no per-segment overrides) colors the culprit; reuses
      `pick_color`/`Theme.ramps` (no new color subsystem).
- [ ] **FR-7.4**: shared selection-state model; mode B correct + fully tty-agnostic; mode A
      behind the conjunctive gate with bounded redraw, guaranteed teardown, windowed scroll,
      glyph-primary state, live preview footer; non-tty fallback contract tested; pty E2E green.
- [ ] **FR-7.5**: wizard offers all `examples/segments/` pre-checked; installs chosen to
      `~/.config/ai-kit/segments/` + `chmod +x` + enables toggle; idempotent; headless via flags.
- [ ] **Quality**: `make test` green; lint clean; `--doctor` exit 0; README + `statusline.toml`
      sample updated; branch compacted into clean per-FR logical commits; final review clean.

---

**Document Version**: 1.0 · **Created**: 2026-06-20 · supersedes the open status of FR-7.3/7.4
in the E7 PRD and adds FR-7.5.
