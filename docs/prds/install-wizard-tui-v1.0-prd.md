# Install Wizard TUI + Segment Layout Editor — PRD

> **Scope.** Lives on its own branch (`feat/install-wizard-tui`, forked off `feat/e7-loop`). It
> replaces the hand-rolled `termios` selector in `tools/setup.py` with a **unified Textual
> full-screen app** that (a) picks which skills/agents/commands/example-segments to install and
> (b) provides a **2-D status-line layout editor** — toggle segments on/off and move them
> `←→` within a line / `↑↓` across lines, with a **live preview** that redraws as you edit.
> It also fixes two latent bugs that make the *current* wizard show no menu at all on a direct
> local run. **Out of scope:** the render refactor + truthful `slowest` (that's
> `refactor/status-line-render`), and the `install.sh` branch-pointing flags (those stay on
> `feat/e7-loop`).
>
> **Clarified via the requirements-clarity flow (decisions locked):**
> 1. **Architecture = Unified Textual app** (install-picks + layout board + live preview in one).
> 2. **Layout interactions = toggle on/off · move `←→` within a line · move `↑↓` across lines.**
>    Mouse drag is explicitly *deferred* (not in v1.0).
> 3. **Three hard requirements locked:** `uv` ask→install→`uv run`; fix headless `open_tty()`;
>    kill the silent mode-A fallback.
> 4. **`uv` install method = the official astral installer** (`curl -LsSf https://astral.sh/uv/install.sh | sh`),
>    exact command shown before running.
> 5. **Live preview = a fixed representative fixture**, *not* the live session — because a
>    standalone wizard run (outside any Claude session) cannot obtain the Claude-only segment
>    fields (model/context/cost/todo/rate-limits); only environment-derived fields would be real,
>    so a stable, machine-independent fixture is both simpler and the only coherent choice.
> 6. **Layout scope kept tight:** toggle + move only. **Add/remove lines and min-width-gate
>    editing are deferred** to a later version (not in v1.0).
> 7. **Success metric = replaces manual TOML editing:** a user never needs to hand-edit the
>    status-line TOML for layout/segment changes.

---

## Requirements Description

### Background

- **Business problem.** ai-kit is a Claude Code status-line + skills toolkit installed locally via
  `make install`, `bash tools/install.sh`, or `uv run tools/setup.py`. The interactive wizard that
  lets a user choose *what* to install and *how their status line is arranged* is the product's
  first-impression surface — and today it is broken and underwhelming:
  1. **No menu on a direct local run.** `open_tty()` (`tools/setup.py:582`) only ever opens
     `/dev/tty`, returning `None` on `OSError` with **no fallback to `sys.stdin`/`sys.stdout`**.
     When a process has no controlling terminal that can be opened as `/dev/tty` (common in IDE
     task runners, some `uv run`/sandbox contexts, multiplexers), `is_interactive()` is `False`
     everywhere — `select_skills` returns defaults with **no prompt** (`:860`), the status-line
     wizard is **skipped** (`:1599`), and the user sees only `checkout / summary / installed /
     doctor`. The one invocation that *should* be the most interactive (a direct local run, where
     `sys.stdin` literally is the keyboard) is pessimized to fully headless. **Reproduced:**
     `open('/dev/tty','r+')` → `[Errno 6] No such device or address` on the user's machine.
  2. **Silent rich→plain collapse.** Even when interactive, the mode-A arrow-key selector degrades
     to a plain numbered `a/n/number` menu on *any* exception via `except Exception: pass`
     (`tools/setup.py:881`) — with **no message** that the rich path was attempted or why it
     failed. Users land in the fallback never knowing the rich UI existed.
  3. **Hand-rolled fragility.** The selector is bespoke raw-mode `termios` code
     (`chip_select`/`_read_key`/`_parse_key`, `tools/setup.py:1325–1470`) with a wide surface of
     terminal edge cases the project must maintain forever.
- **Target users.** The repo owner and other developers installing ai-kit **interactively on their
  own machine**. Non-interactive / CI / headless robustness is **explicitly a non-goal** (the user
  stated this directly) — the wizard optimizes for a human at a real terminal.
- **Value proposition.** A genuinely navigable, togglable, *spatial* installer — the "rich UI feel"
  (referenced as "the SvelteKit feel": navigable + togglable + live) — that also lets the user
  **arrange their status line visually** instead of hand-editing TOML. Plus: the wizard actually
  appears on a direct local run, every time.
- **Success metric (measurable "done").** The wizard **replaces manual TOML editing**: a user can
  perform every supported layout/segment change (toggle on/off, reorder within a line, move across
  lines) through the UI and never needs to hand-edit the status-line TOML for those changes — and
  the wizard reliably appears on every interactive local run. Verified by: (a) a round-trip test
  proving the UI emits a config equivalent to the hand-edited form for each operation, and (b) the
  `open_tty()` matrix proving interactivity on a direct local run.

### Feature Overview

- **Core features.**
  - **FR-W.1** — Fix `open_tty()` so a direct local run is never wrongly headless.
  - **FR-W.2** — `uv` bootstrap: detect `uv`; if absent, ask consent and install; then `uv run` the
    Textual app. Loud, explained fallback if declined.
  - **FR-W.3** — Unified **Textual** wizard app: install-picks panel.
  - **FR-W.4** — **Segment layout editor**: toggle + move `←→`/`↑↓` + live preview.
  - **FR-W.5** — Persist the layout to the status-line TOML (round-trips the real contract).
  - **FR-W.6** — Kill the silent fallback; any degrade is announced with a reason.
  - **FR-W.7** — Accessibility + confirmation: glyph-not-color state, plain-text summary + final
    confirm, clean `Ctrl-C`, allow-but-confirm empty selection.
- **Feature boundaries (what is NOT included in v1.0).**
  - Mouse drag of chips (keyboard moves only; deferred to a later version).
  - The render-pass refactor and truthful-`slowest` fix (separate branch).
  - `install.sh` branch-pointing flags (separate branch).
  - CI / non-tty / headless rich UI — headless still works, but only via the always-correct plain
    path; the rich app is interactive-only by design.
  - New segments or changes to segment *rendering* — the editor arranges existing segments only.
- **User scenarios.**
  - *Fresh install, has uv:* `uv run tools/setup.py` → Textual app opens → pick skills → arrange
    segments live → confirm summary → installed.
  - *Fresh install, no uv:* `make install` → "uv not found — install it to get the rich wizard?
    [Y/n]" → installs uv → relaunches under `uv run` → Textual app. If declined → loud notice +
    basic numbered menu (never silent, never menu-less).
  - *Reconfigure:* `bash tools/install.sh reconfigure` → app pre-loads the *current* selection and
    *current* layout from the existing TOML so the board reflects reality, not defaults.

### Detailed Requirements

- **Input/Output.**
  - *Inputs:* keyboard (arrows + `j/k/h/l`, `space`, `a`, `n`, `/`, `enter`, `esc`, `Ctrl-C`); the
    existing config TOML (for reconfigure); the repo's discoverable skills/agents/commands and
    `examples/segments/`; the live `SEGMENTS`/`LAYOUT` defaults for a first run.
  - *Outputs:* the symlink set under `~/.claude` (unchanged install mechanics), the status-line
    TOML with `[line]`/`[segments]` reflecting the arranged layout, a plain-text summary to stdout,
    and the existing `doctor:` hint.
- **User interaction (layout editor).** Each segment is a chip. A focused chip is moved with
  `←→` (reorder within its line) and `↑↓` (move to the previous/next line; from the top line up
  goes to the *off tray*, from the off tray down re-activates onto line 1). `space` toggles
  active/off (off chips live in a dedicated **off tray**). The **live preview** pane renders the
  current arrangement via the real renderer and redraws on every edit.
- **Data requirements (the contract this must round-trip).** The status line is defined by two
  duplicated-but-authoritative structures in `tools/status-line.py`:
  - `SEGMENTS` — 20 segments with default on/off: `path, branch, dirty, worktree, todo, model,
    time_ago, clock, effort, lines, cost(off), total_time, api_time, render_time, slowest,
    dimensions(off), context, chat_size, memory, rate_limits`.
  - `LAYOUT` — ordered lines, each with a **min-width gate** and an ordered segment list. Default:
    - `Line(0,  [path, branch, worktree, dirty, todo])`
    - `Line(20, [model, time_ago, clock, effort, lines, cost, total_time, api_time])`
    - `Line(30, [render_time, dimensions, context, chat_size, memory, rate_limits, slowest])`
  - The editor's three operations map 1:1 onto this: `←→` reorders a line's list; `↑↓` moves a
    segment between line lists (or to/from "off"); `space` flips the `[segments]` toggle. **The
    line min-width gate is preserved** — moving a segment does not change a line's gate. v1.0
    **does not expose gate editing, nor adding/removing lines** (both deferred to a later version);
    the editor operates only on the existing lines and their segment lists.
- **Edge cases.**
  - Terminal too small for the full-screen app → announce + fall back to the plain menu (FR-W.6),
    never crash into a corrupted alternate screen.
  - `uv` install fails or is declined → loud notice + plain menu.
  - Empty selection (nothing to install) → allowed, but confirmed: "Nothing selected — install
    nothing? [y/N]".
  - A segment in the saved TOML that no longer exists in `SEGMENTS` → shown greyed in the off tray
    with a "(unknown)" note, never silently dropped.
  - `Ctrl-C` at any point → clean abort, no partial writes, original config intact.
  - A `curl | bash` run where stdin is the script pipe → still reads the terminal correctly (the
    `/dev/tty`-first behavior is retained; FR-W.1 only *adds* the stdin/stdout fallback).

---

## Design Decisions

### Technical Approach

- **Architecture choice — Unified Textual app (locked).** A single `textual` application hosts both
  surfaces (install-picks + layout board + live preview). Rationale: the layout editor is an
  inherently **2-D, stateful, live-preview** task; a 1-D prompt library (questionary) structurally
  cannot express "move `←→`/`↑↓` with live redraw". A full-screen reactive app is the right tool
  *because the feature demands it* — the complexity is bought by the requirement, not spent on
  spectacle. Keeping install-picks in the same app yields one coherent experience (the requested
  "rich feel") rather than a rich board bolted onto a plain prompt.
- **`uv` as the delivery mechanism (locked).** Textual is a third-party dependency; the kit is
  otherwise stdlib-only. Rather than vendoring or a venv, the wizard uses **`uv run` with PEP-723
  inline script metadata** so `textual` is resolved into an ephemeral environment on demand. Flow:
  1. `setup.py` detects whether it is already running under `uv` (env marker) and whether `textual`
     is importable. 2. If not, detect the `uv` binary. 3. If `uv` is missing → **ask consent** →
     install via **the official astral installer** (`curl -LsSf https://astral.sh/uv/install.sh |
     sh`), with the **exact command printed before it runs** (no hidden network fetch; `wget` form
     offered when `curl` is absent) → 4. **re-exec** the wizard under `uv run` so the inline deps
     resolve. 5. If consent declined or `uv` unavailable → loud notice → plain menu. The official
     installer is preferred over `pipx`/`brew`/`pip` to keep the path single and predictable across
     machines.
- **Live preview = fixed representative fixture (locked).** The preview pane shells out to the real
  renderer fed a **baked-in sample JSON** (a realistic repo path, branch, worktree/dirty state,
  model, context %, timings) — *not* the live session. Rationale: a standalone wizard run lives
  outside any Claude session, so the Claude-supplied segment fields (`model`, `context`,
  `chat_size`, `cost`, `todo`, `time_ago`, `api_time`, `rate_limits`) have no live source; only
  environment-derived fields (`path`, `branch`, `worktree`, `dirty`, `render_time`) would be real.
  A fixture makes the preview complete, deterministic, and identical on every machine. The fixture
  is checked in next to the wizard and exercised by tests so it can't silently drift from the
  renderer's expected input shape.
- **Key components.**
  - `tools/setup.py` — keeps the install *mechanics* (symlink reconcile, prune, adopt, examples).
    Gains: the fixed `open_tty()`, the `uv` bootstrap/relaunch, and a dispatch that launches the
    Textual app when interactive + available, else the plain menu.
  - A new Textual app module (PEP-723 inline deps) — the UI only. It **imports nothing from
    `status-line.py`** (hyphenated filename forbids it); it obtains the live preview by the existing
    subprocess contract (`python3 status-line.py` fed a sample JSON on stdin), and it reads the
    `SEGMENTS`/`LAYOUT` defaults via the same duplication-guarded mechanism the wizard already uses.
  - The plain numbered menu — **retained** as the always-correct fallback, but reached only via an
    announced degrade, never silently.
- **Data storage / interface design.** The app edits an in-memory model (lines → ordered segment
  ids, plus an off set), seeded from the existing TOML on reconfigure or from `SEGMENTS`/`LAYOUT`
  on first run. On confirm it writes the TOML using the *existing* surgical writer/validator
  (`set_segment_toggles` / `validate_config_file`) so the on-disk contract and drift-guards remain
  authoritative. The live preview shells out to the real renderer fed the **checked-in fixture
  JSON** — the preview is therefore truthful to the renderer's logic (not a re-implementation),
  while being deterministic and machine-independent (see "Live preview" decision above for why a
  live-session feed is not possible standalone).

### Constraints

- **Performance.** Live-preview redraw must feel instant (< ~100 ms per edit). The preview
  subprocess is debounced/coalesced so rapid `←→` presses don't spawn a backlog.
- **Compatibility.** Python 3 + a terminal. `uv` is *fetched with consent* when absent — the kit's
  zero-runtime-dependency property for the **plain** path is preserved (plain menu needs only
  stdlib); only the **rich** path requires `uv`+`textual`.
- **Security.** `uv` is installed only after explicit consent, via its official installer; the
  command shown to the user before running. No silent network fetch.
- **Scalability.** The 20-segment inventory fits one screen; the off tray and per-line lists scroll
  if a future kit grows the inventory. `/` filter planned if any list exceeds ~10 items.
- **Non-goal (explicit).** CI/headless rich UI. Headless degrades to the plain path by design.

### Risk Assessment

- **Technical risks.**
  - *Textual full-screen crash corrupts the terminal.* Mitigation: wrap the app so any unhandled
    exception restores the screen (alternate-buffer teardown) and falls through to the announced
    plain menu; size-check before launch.
  - *`uv` bootstrap complexity / re-exec loops.* Mitigation: a single env marker guards re-exec;
    if running under `uv` and `textual` still missing, do **not** re-exec — go straight to plain
    menu with a reason. Covered by tests.
  - *Two-file contract drift* (`SEGMENTS`/`LAYOUT`/`_SEG_HEADER_RE` duplicated across
    `setup.py`/`status-line.py`). Mitigation: extend the existing drift-guard tests to the layout
    round-trip; the editor reuses the existing writer/validator rather than re-encoding TOML.
- **Dependency risks.** `textual`/`uv` availability. Mitigation: the plain path needs neither, and
  is always reachable with a clear reason.
- **Schedule risks.** Textual has a learning curve. Mitigation: phase the work (bugs+bootstrap
  first — they stand alone and ship value even before the rich app lands).

---

## Acceptance Criteria

### Functional Acceptance

- [ ] **FR-W.1 — headless fix.** A direct local run (`uv run tools/setup.py`, `bash
      tools/install.sh`, `make install`) with usable `sys.stdin`/`sys.stdout` TTYs presents an
      interactive wizard even when `/dev/tty` cannot be opened. A `curl | bash` run still reads the
      terminal correctly. A genuinely headless run (no usable terminal at all) still degrades to
      defaults without error.
- [ ] **FR-W.2 — uv bootstrap.** With `uv` present and `textual` resolvable, the rich app launches.
      With `uv` absent: the user is asked, and on consent `uv` is installed and the wizard re-execs
      under `uv run`. On decline / failure: a loud, explained fallback to the plain menu. No re-exec
      loop is possible.
- [ ] **FR-W.3 — install picks.** The Textual app lists discovered skills/agents/commands/example
      segments with glyph on/off state; `space` toggles, `a` all, `n` none; selection drives the
      same symlink reconcile as today.
- [ ] **FR-W.4 — layout editor.** A focused segment moves `←→` within its line and `↑↓` across
      lines (including to/from the off tray); `space` toggles active/off; the live preview redraws
      on every edit, driven by the checked-in fixture, and matches the real renderer's output for
      that fixture. (Add/remove lines and gate editing are out of v1.0 scope.)
- [ ] **FR-W.5 — persistence.** On confirm, the arranged layout is written to the status-line TOML
      via the existing surgical writer/validator; re-opening the wizard pre-loads exactly that
      arrangement; `status-line.py --doctor` and `--check` pass on the written config.
- [ ] **FR-W.6 — no silent fallback.** Every rich→plain degrade (small terminal, missing
      uv/textual, runtime error) prints a one-line reason. A grep proves `except Exception: pass`
      no longer guards the selector path.
- [ ] **FR-W.7 — accessibility + confirm.** On/off is conveyed by glyph shape (not color alone);
      a plain-text install+layout summary is shown with a final `[Y/n]`; empty selection is
      allowed but confirmed; `Ctrl-C` aborts cleanly with the original config intact.

### Quality Standards

- [ ] **Code quality.** Clean separation: install mechanics (setup.py) vs UI (Textual module) vs
      the always-correct plain fallback. No new duplication of the segment contract beyond the
      existing guarded duplication.
- [ ] **Test coverage (`python3 -m unittest`).** Unit tests for: `open_tty()` fallback matrix
      (`/dev/tty` ok / fails + stdin/stdout tty / not); uv detect + consent + re-exec guard (no
      loop); the layout model's move/toggle operations and TOML round-trip; the announced-degrade
      paths. The Textual view itself is tested via its model + Textual's test harness (`run_test`)
      for keybindings where feasible; UI rendering verified by snapshot where practical.
- [ ] **Drift guards.** Existing `_SEG_HEADER_RE` / `SEGMENTS` / `LAYOUT` duplication tests extended
      to cover the layout round-trip.
- [ ] **Lint.** `make lint` (shellcheck for install.sh) stays clean; Python stays import-safe.
- [ ] **No regression.** The plain path still passes the full existing `tests/test_setup.py` /
      `tests/test_install.sh` suites.

### User Acceptance

- [ ] **UX.** Keybindings: `↑↓`/`j k` move-across, `←→`/`h l` move-within, `space` toggle, `a` all,
      `n` none, `/` filter (lists > ~10), `enter` confirm, `esc`/`Ctrl-C` abort. Verified by the
      ui-ux-designer agent on the running app.
- [ ] **Docs.** README updated: the rich wizard, the `uv` requirement for it, the plain fallback,
      and the layout editor keybindings.
- [ ] **Verification.** A fresh subagent runs the acceptance commands and returns PASS with raw
      output before any box is checked.

---

## Execution Phases

### Phase 1: Foundations — fix the bugs, stand up uv (ships value alone)
**Goal:** the wizard always appears on a local run; uv path is ready.
- [ ] **T1.1** Fix `open_tty()` to try `/dev/tty`, then fall back to `sys.stdin`/`sys.stdout` when
      both are TTYs; only `None` when nothing is usable. TDD the fallback matrix first.
- [ ] **T1.2** Kill the silent `except Exception: pass` selector fallback; route every degrade
      through an announced path with a reason string.
- [ ] **T1.3** `uv` detect + consent + install + re-exec-under-`uv` with a loop guard; plain-menu
      fallback on decline/failure. TDD with a fake `uv` on PATH.
- **Deliverables:** local runs are interactive again; uv bootstrap with tests. **Est:** ~1 day.

### Phase 2: Textual install-picks panel
**Goal:** replace the chip selector with a Textual install-picks view.
- [ ] **T2.1** PEP-723 Textual app skeleton; launched from `setup.py` when interactive+available.
- [ ] **T2.2** Install-picks list (skills/agents/commands/examples) with glyph state + keybindings;
      drives the existing reconcile. Model unit-tested; view tested via Textual `run_test`.
- [ ] **T2.3** Plain-text summary + final confirm; allow-but-confirm empty; clean `Ctrl-C`.
- **Deliverables:** rich install-picks with the plain fallback intact. **Est:** ~1.5 days.

### Phase 3: Segment layout editor + live preview
**Goal:** the 2-D board that motivated this work.
- [ ] **T3.1** In-memory layout model (lines→ordered ids + off set) seeded from TOML/defaults;
      `←→`/`↑↓`/toggle operations; unit tests incl. off-tray transitions and min-width-gate
      preservation.
- [ ] **T3.2** Textual board view: chips per line, off tray, focus + moves; ui-ux-designer review.
- [ ] **T3.3** Live preview pane via the real renderer subprocess fed the checked-in fixture JSON,
      debounced; redraw on edit. A test pins the fixture to the renderer's expected input shape.
- [ ] **T3.4** Persist via existing surgical writer/validator; round-trip + drift-guard tests;
      `--doctor`/`--check` pass on output.
- **Deliverables:** the live layout editor (image D), persisted truthfully. **Est:** ~2.5 days.

### Phase 4: Hardening, docs, gate
**Goal:** ship-ready.
- [ ] **T4.1** Small-terminal + crash-recovery: restore screen, announce, fall to plain menu.
- [ ] **T4.2** README + keybinding docs; update memory.
- [ ] **T4.3** Full-suite green (`make test`, `make lint`, `--doctor`); fresh-subagent verification.
- [ ] **G-W** Code-review gate (`/requesting-code-review` + `/simplify`) scoped to the branch;
      resolve HIGH/CRITICAL before merge.
- **Deliverables:** verified, reviewed, documented. **Est:** ~1 day.

---

**Document Version**: 1.0
**Created**: 2026-06-20
**Clarification Rounds**: 5 (wizard-flavor mockups → design-agent verdict → layout requirement →
architecture/interaction/hard-requirement locks → uv-method / preview-source / scope / success-metric locks)
**Quality Score**: 100/100

---

## Addendum A — Main reconciliation (2026-06-23)

> The PRD body above is preserved byte-for-byte (the v1.0 lock is auditable). This addendum
> re-anchors it to the codebase as it actually stands on `main` today, because the branch was
> forked off `feat/e7-loop` *before* the status-line architecture + config-binding refactors
> landed on `main`. The implementation follows this addendum where it differs from the body.

### A.1 — Verified base state

- Implementation starts from **`main`** (`2513183`; `origin/main == main`; working tree clean;
  gate green). **No separate worktree** — the prior refactor work is already merged into `main`.
  Branch: **`feat/install-wizard-tui-v2`** (the old `feat/install-wizard-tui` is dropped; its only
  unique content was this PRD, now ported, plus `c54b273` which is already in `main`).
- **`c54b273` is already in `main`** (the 🌿 static branch icon at `status-line.py:2114`; the
  `install.sh --branch` flag at `install.sh:22-152`; README + tests). Nothing to carry forward.

### A.2 — Stale anchors → current API (names moved during the refactor)

| PRD body says | Current `main` reality |
|---|---|
| writer `set_segment_toggles` | `patch_segments(text, changes)` + `write_toml_preserving(path, text, statusline_doctor)` (setup.py); high-level entry `save_statusline_config(path, seg_changes, layout, statusline_doctor)` |
| validator `validate_config_file` in `status-line.py` | moved to **`tools/statusline-doctor.py:148`**; reached by **subprocess** (`python3 -S statusline-doctor.py --doctor`, `CC_AI_KIT_CONFIG_FILE=path`), never import |
| FR-W.6 silent fallback at `setup.py:881` | now at **`setup.py:~901`** (`except Exception … pass`, still silent) |
| live preview "to be built" | **already exists**: `render_preview(status_line, segments, sample_json, env)` shells `python3 -S status-line.py` with sample JSON on stdin |

### A.3 — Anchors the PRD got right (unchanged)

- `SEGMENTS` (`status-line.py:110`), `LAYOUT` (`status-line.py:149`), `_SEG_HEADER_RE`
  (`status-line.py:1789`) remain canonical in the renderer, mirrored as `LAYOUT_DEFAULTS` in
  setup.py under a **drift-guard test** (`test_setup.py:80-92`).
- FR-W.1 (`open_tty`) and the FR-W.6 silent-degrade bug are **both still present** — the fixes
  are still needed (see the amendment for their revised, simplified form).

### A.4 — Module seam (load-bearing invariant)

```
settings.json statusLine ──exec──▶ status-line.py   (render-only; python3 -S; NO --doctor flag; stdlib-only)
                                        ▲ imports core as `sl` (ONE-WAY)
   setup.py (wizard; MAY use uv) ──subproc──▶ statusline-doctor.py   (--doctor / --check)
        └──subproc──▶ status-line.py   (render_preview → live-preview feed)
```

**Invariant.** The Textual app is a UI layer that **composes existing setup.py engine helpers**
(`render_preview`, `save_statusline_config`/`write_toml_preserving`, `apply_selection`). It imports
nothing from the hyphenated modules and reaches `status-line.py` / `statusline-doctor.py` only by
subprocess. **The status-line render path stays `python3 -S`, stdlib-only — `uv`/`textual` exist
exclusively to launch the `setup.py` wizard, never on the render path.** As a result, FR-W.5
persistence (atomic write → doctor self-validation → auto-revert) and FR-W.4 preview feed are
*already built and doctor-wired*; the app produces `seg_changes` + `layout` and calls the existing
helpers.

---

## Addendum B — Scope amendment: single path, minimal failure axes (2026-06-23)

> Owner decision (2026-06-23): **collapse the dual-path design into one path.** The wizard is
> interactive-only and requires a real terminal + `uv` + `textual`; if any prerequisite is absent
> it **fails loudly and exits non-zero** — there is no plain-menu fallback and no headless-defaults
> path. This *reduces* the failure surface and is largely a deletion. It supersedes the body where
> they conflict.

### B.1 — Amended requirements

- **FR-W.1 (amended).** `open_tty()` tries `/dev/tty`, then `sys.stdin`/`sys.stdout` when **both
  are `isatty()`** (this fixes the real bug — a direct local run wrongly classified as headless).
  When no usable terminal exists → **print a clear one-line reason and exit non-zero.** The
  "degrade to defaults silently" tail is **removed**. (`curl | bash` still works: `/dev/tty` is
  tried first; the stdin fallback is gated on `isatty`, so the script pipe is never mistaken for a
  keyboard.)
- **FR-W.2 (amended).** `uv` missing → ask consent → install via the official astral installer
  (exact command shown) → re-exec under `uv run` (single env-marker loop guard). **Declined /
  install-failed / still-missing-after-re-exec → clear error, exit non-zero.** No fallback.
- **FR-W.6 (amended → trivial).** There is no rich→plain degrade because **there is no plain
  path.** Every missing prerequisite is one loud, explained exit. The grep assertion becomes:
  the bespoke selector and its silent `except` are **gone from the tree**, not merely un-guarded.
- **Crash safety (amended, was T4.1).** On an unhandled Textual exception: restore the screen
  (alternate-buffer teardown), print the reason, **exit non-zero.** No menu to fall through to.

### B.2 — Deletions (the failure surface that goes away)

- **Mode-A selector:** `chip_select` / `_read_key` / `_parse_key` and the raw-`termios` machinery.
- **Mode-B menus:** the numbered `select_skills` toggle loop and `_render_segment_menu`.
- **Headless-defaults path** in `select_skills` and the silent `except Exception` degrade.
- Their tests in `test_setup.py` / `test_wizard_pty.py` are removed or rewritten against the
  single path.

### B.3 — Retained non-interactive surface (scoped, not a wizard fallback)

`install.sh` keeps its **bootstrapper mechanics** path (symlink reconcile, `--branch`, dry-run)
and its existing `test_install.sh` coverage — this is installer plumbing, **not** the interactive
selection/layout UI, and does not reintroduce a second wizard path. *(Owner may elect to strip even
this; default is to keep it so the bootstrapper stays CI-testable.)*

### B.4 — Net effect on the body's FRs

FR-W.3 / FR-W.4 / FR-W.5 / FR-W.7 (Textual install-picks, layout editor, persistence,
accessibility/confirm) are **unchanged**. FR-W.1 / FR-W.2 / FR-W.6 are **simplified** as above.
The four execution phases stand; Phase 1 shrinks (open_tty fix + uv bootstrap, both fail-closed)
and Phase 4 drops the "fall to plain menu" crash-recovery in favor of "restore screen → exit".

**Addendum Version**: 1.0 · **Created**: 2026-06-23 · supersedes body on FR-W.1/W.2/W.6 + fallback.

---

## Addendum C — E2E testing (2026-06-23, mandatory)

> Owner requirement (2026-06-23): E2E testing is a **first-class, must-have** dimension of both
> planning and execution — not just unit/component tests. Because the wizard is now tty-only
> (Addendum B), E2E is driven through a **real pseudo-terminal (PTY)**, the same vehicle as the
> existing `tests/test_wizard_pty.py` (which is rewritten for the single path, not deleted).

### C.1 — Test pyramid for this feature

- **Unit** — the in-memory layout model (`←→`/`↑↓`/toggle, off-tray transitions, min-width-gate
  preservation); the TOML round-trip via `patch_segments` → `save_statusline_config`; the
  `open_tty()` matrix; the uv detect/consent/re-exec loop-guard.
- **Component (Textual)** — keybindings + view state via Textual's `run_test`/`Pilot` harness over
  the real app and model (no subprocess).
- **E2E (PTY, mandatory)** — drive the **whole** `tools/setup.py` flow under a pseudo-terminal:
  allocate a pty, launch the wizard, send keystrokes (navigate, `space` toggle, move chips across
  lines, `enter` confirm), and assert on real side effects.

### C.2 — Mandatory E2E scenarios (each asserts real artifacts, not mocks)

1. **Fresh install happy path.** PTY launch → pick skills → arrange one segment move + one toggle →
   confirm → assert: the symlink set under a temp `CLAUDE_CONFIG_DIR`, the written status-line TOML
   reflects the arrangement, and `statusline-doctor.py --doctor` / `--check` **pass** on the output.
2. **Reconfigure round-trip.** Pre-seed a TOML → relaunch → assert the board pre-loads exactly that
   arrangement → make a change → re-assert the TOML round-trips (UI-emitted == hand-edited form).
3. **FR-W.1 interactivity.** A direct local run where `/dev/tty` can't be opened but `stdin/stdout`
   are PTYs → the wizard **appears** (not headless).
4. **Fail-closed (Addendum B).** No usable terminal → process exits **non-zero with a clear reason**
   and writes nothing. uv declined/missing → same. (Replaces the old headless-defaults assertion.)
5. **uv bootstrap.** Fake `uv` on PATH + env marker → re-exec happens **once** (no loop), app
   launches; declined → loud non-zero exit.
6. **Clean `Ctrl-C`.** Abort mid-flow → original config intact, no partial/temp files left.
7. **Live-preview fidelity.** The preview pane output equals `render_preview()` for the checked-in
   fixture; a test **pins the fixture** to the renderer's expected input shape so it can't drift.

### C.3 — Execution discipline

- E2E scenarios are written **alongside** each phase (TDD where practical), not deferred to Phase 4
  — Phase 1 lands the `open_tty`/uv E2E (scenarios 3–5), Phase 2 the install-picks E2E (1 partial),
  Phase 3 the layout/preview/persistence E2E (1, 2, 7), Phase 4 hardens 4 and 6.
- The gate (`make test` / `make validate`) must run the PTY E2E suite; a fresh-subagent
  verification re-runs the acceptance commands and returns raw PASS output before any box is ticked.

**Addendum Version**: 1.0 · **Created**: 2026-06-23.
