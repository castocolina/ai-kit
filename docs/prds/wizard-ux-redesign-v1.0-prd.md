# ai-kit Install Wizard — UX Redesign v1.0 PRD

**Status:** Design locked (mockup-approved). Ready for implementation planning.
**Amendment (2026-06-24):** corrected config path to `~/.config/ai-kit/statusline.toml`
(was wrongly `~/.claude/`); added user-segment discovery (`~/.config/ai-kit/segments/`) and a
self-describing external-segment header standard (`name`/`description`/`icon`/`sample`,
wizard-side only). See "External / user segments".
**Goal:** Rebuild the Textual install wizard's UX into a linear, panelled, next-next
carousel that matches the approved mockup — without changing the render path, the
fail-closed contract, or the doctor-validated persistence of the existing wizard.

## Source of truth (the approved design)

The visual + interaction spec is the committed prototype, not prose:

- `docs/wizard-redesign/mockup-textual.html` — interactive HTML reference (open in a browser).
- `docs/wizard-redesign/prototypes/mockup-textual.py` — a runnable Textual port that
  reproduces the HTML 1:1 (`uv run --script mockup-textual.py`). It writes nothing and
  imports nothing from `setup.py`; it is the behavioural reference.
- `docs/wizard-redesign/prototypes/_protodata.py` — illustrative fake data only
  (categories, 20 segments, 3-line layout, sample values). The REAL wizard sources its
  data from the `setup.py` engine via `WizardContext`, not from this file.

When prose here and the prototype disagree, the prototype wins; raise the conflict.

## Background — what this fixes

The current wizard (`tools/wizard_app.py`, shipped) reads as a single TUI page: the
layout editor was a hidden `Tab` side-branch (users "only saw skills"), `Enter` jumped
to the end, the bars were thin and borderless, and there was no per-screen orientation.
This redesign linearizes the flow and gives every area a dedicated bordered panel.

## Locked decisions

1. **Three numbered steps, NO Welcome screen.** Flow:
   `Choose components (1/3) → Arrange status line (2/3) → Review & confirm (3/3) → Done`.
   Done is an end card, not a numbered step. Start directly on Choose.
2. **Single screen with a swappable step body** (recommended architecture) rather than
   pushed Textual Screens. The prototype proves this sidesteps the **Enter double-fire
   gotcha** entirely: because no new screen is pushed on `Enter`, the forwarded key never
   double-fires. If the implementer instead keeps pushed Screens, every screen reached by
   `Enter` MUST advance via a `key_enter` method, never a `BINDINGS` entry (Textual 8.2.7).
3. **Header bar**: `─ ai-kit install wizard` (accent) left; `Step n of 3` + pips
   `● ● ○` right. Pips fill left-to-right and are the proof-of-progress cue.
4. **Footer key-bar = the key legend**, persistent, inside the frame, accurate per step.
   Each key is an **emphasized keycap pill**; the primary action (`Enter`) is a blue
   "primary" cap; `Quit` is pushed to the right. Exact per-step legend = the prototype's
   `FOOTERS`.
5. **Per-screen `h1` title + `sub` explainer** above the body on every step (see
   prototype `TITLES`/`SUBS`).
6. **Global keys:** `Esc` = Back (never a letter), `q` = Quit, `?` = help overlay listing
   every key for the current step. **`ENABLE_COMMAND_PALETTE = False`** (no `Ctrl+P`).
7. **Color-independence (accessibility):** state is encoded by **shape/glyph**, never
   color alone — `◉`/`◯` on/off, `[>chip<]` pink-bracket focus, `▌` left gutter for the
   highlighted row. A monochrome terminal stays fully usable.

## Functional requirements per screen

### Step 1 — Choose components
- Items grouped by category (`agents` / `commands` / `skills`), real items from the engine.
- `↑`/`↓` move a highlight (a **pink** `▌` left bar — distinct from the **cyan** category
  "kind" bar); `Space` toggles `◉`/`◯`.
- `a`/`n` select all/none **within the focused category**; `A`/`N` across **everything**.
- Live per-category `N/M on` counts and a total `X of Y components selected`.

### Step 2 — Arrange status line (the showcase)
- Three **bordered lane panels** (`Line 1/2/3`). Line 2 and Line 3 are **dashed** and
  carry a `needs ≥ 20 rows` / `needs ≥ 30 rows` border-subtitle (the real renderer's
  row-gate).
- A **dedicated, bordered OFF tray** panel for disabled segments — reachable by focus and
  re-enable-able in place.
- Chip focus is the pink `[>icon name<]` bracket shape. On the **active lanes**: `←`/`→`
  reorder within the lane, `↑`/`↓` move across lanes (`↑` off Line 1 → OFF tray to disable),
  `Space` disables (→ OFF tray). **OFF/disabled chips are NOT movable or reorderable** —
  order is meaningless for them; `Space` re-activates a disabled chip onto its home line, and
  the move keys (`←→`/`↑↓`) are no-ops in the tray. `Tab`/`Shift+Tab` cycle focus; `r` resets
  the layout to defaults.
- **Region order, top→bottom, four visually-distinct panels** — each must read as a different
  region: (1) the active **line lanes** (cyan "active/live" borders; Line 2/3 dashed + row-gate), (2) a
  **full-width focused-chip detail panel placed BEFORE the OFF section** (pink-emphasis to
  read as "focus": segment name · description · on/off + line state), (3) the **OFF / disabled
  tray** (dim/dashed "disabled" treatment), (4) a **full-width live-preview panel at the
  bottom** (dark status-line background).
- The preview renders the real status-line shape (`icon value | icon value …`) and updates on
  every move/toggle (must reflect MOVES, not just toggles).
- **Activation placement:** enabling an off segment places it on its inventory `line` (its
  ideal home), not a fixed Line 1.

### Step 3 — Review & confirm
- **components to install** box (by category) · **status line** preview box (same dark
  status-line background as Step 2, for consistency) · **what happens on confirm** box
  (symlink N components, write `~/.config/ai-kit/statusline.toml` with M segments, validate via
  `statusline-doctor`) · a green **`▸ Install ai-kit`** CTA with an `Enter` keycap.
- `Enter` = Install (the ONLY place the wizard mutates disk); `Esc` = Back to Arrange.

### Done
- Confirmation card + next-steps box (open a new session, re-run to change picks, edit
  `~/.config/ai-kit/statusline.toml`). `Enter`/`q` exits.

## Data sourcing & segment inventory

The wizard must LOAD everything it shows from real discovery — no fake/hardcoded
lists. Clarified via requirements-clarity (score 91/100). The prototype's
`_protodata.py` is illustrative only and must not ship.

### Components (Choose screen)
- Discovered from repo source per category by the engine's `validate_entry`
  (`skills` = dir with `SKILL.md`; `commands`/`agents` = `*.md` whose first line is
  the `---` front-matter fence).
- **Hide-empty:** render a category section only if it has ≥ 1 valid entry. A
  zero-entry category is **absent**, not placeholdered. "Available" = discoverable in
  the repo source; the `◉`/`◯` shows install state. (Today only `skills/` exists, so
  only Skills would render.)

### Segment metadata — new inventory (outside the render path)
- The canonical segment list is **discovered** from `tools/status-line.py`'s `SEGMENTS`
  / self-registering registry. The render file stays `python3 -S` stdlib-only and
  carries **no** UI copy or sample data.
- **New inventory data file** (proposed `tools/segments_inventory.toml`, TOML — name/format
  to confirm), keyed by segment name; each entry: `description` (UI-only; inventory is the
  SOLE source; never user-configurable), `sample` (static value shown in the preview),
  `icon` (default), `line` (default/preferred line).
- **Override layering (read by setup/wizard, not the renderer):** the current
  `~/.config/ai-kit/statusline.toml`, if present, **overrides `icon` + `line`**; the inventory
  supplies the fallback defaults for `icon` + `line` and is the only source of
  `description` + `sample`.
- **Samples are static**, authored in the inventory (not live-rendered).
- **Golden-safe icons (decided — object if wrong):** the stdlib renderer KEEPS its
  built-in icon/line defaults so golden output stays byte-identical and render-path
  purity holds; the inventory's default `icon`/`line` MUST mirror the renderer's defaults
  exactly. An arch/doctor test asserts (a) the mirror and (b) that every discovered
  segment has an inventory entry (**fail-closed coverage**). Icons are NOT ripped out of
  `status-line.py`; single-sourcing icons into the inventory is a deferred option.

### External / user segments

External segments **already render today** — the stdlib render path's `core_discover_external`
(`tools/status-line.py`) scans `${XDG_CONFIG_HOME:-~/.config}/ai-kit/segments/`, runs each as a
subprocess (stdin = status JSON, TTL-cached under `~/.cache/ai-kit/segments/<id>`, 2 s timeout,
output sanitized), and merges them into the builder registry. **No render-path change is needed
for user-dropped segments to render.** This work is wizard/installer-side only: *discover* and
*show* them with metadata.

- **Two discovery sources (wizard/installer):**
  1. **Bundled** repo `examples/segments/` (existing `discover_example_segments`, `tools/setup.py`).
  2. **User** `${XDG_CONFIG_HOME:-~/.config}/ai-kit/segments/` — the SAME directory the renderer
     already reads. Today `discover_example_segments` scans only (1); extend it to also scan (2).
  Both are surfaced in the wizard, **tagged by provenance** (`bundled` / `user`) so the UI marks
  where each came from.
- **Self-describing header standard (the contract for "drop a script and the wizard shows it"):**
  the `# ai-kit-segment: k=v …` header gains **four OPTIONAL** UI keys alongside the existing
  `line=`: `name=`, `description=`, `icon=`, `sample=`. All optional. Missing fields fall back to
  **id as name, blank description, default icon, default/last line.** A segment author self-describes
  by editing only its own header — no inventory entry, no core change.
- **Metadata source split:** built-ins get UI metadata from `segments_inventory.toml`; externals
  get it from **their own header** (the inventory does NOT carry external segments). `description`
  is UI-only either way.
- **Parsing seam (render-path purity preserved):** the new `name=`/`description=`/`icon=`/`sample=`
  keys are parsed **wizard/installer-side only** (`tools/setup.py`). The renderer's
  `core_parse_segment_header` (`tools/status-line.py`) is **NOT** extended — it still reads only
  `id`/`line`/`after`/`before`/`start`/`end`/`ttl`/`timeout`, so `status-line.py` stays
  `python3 -S` / no-UI-copy.
- **Default state:** a discovered external/user segment shows **OFF** (available, discoverable)
  unless the user's `~/.config/ai-kit/statusline.toml` already enables + places it — same
  reconfigure-layering rule as `alt_*` segments. The wizard always LISTS them so they stay
  discoverable.
- **Reference segment demonstrates the standard:** the renamed `examples/segments/system_memory`
  (see below) carries the full optional header (`name=`/`description=`/`icon=`/`sample=`) as the
  canonical copy-and-edit example of a self-describing external segment.

### Segment defaults & naming (added during clarity)
- **All `alt_*` segments default OFF — no exemptions (incl. `alt_git_worktree`).** They are
  optional extras: the renderer's `SEGMENTS` default for every `alt_*` key becomes `False`.
  The ONLY way an `alt_*` segment renders on a line is on **reconfigure**, when the user's
  existing `~/.config/ai-kit/statusline.toml` already has it `= true` AND placed on a line (env
  mirror equivalent). A fresh install shows every `alt_*` OFF (in the wizard's OFF tray,
  available to enable). The wizard always LISTS them (unchecked) so they stay discoverable.
  - **Golden impact (intended):** this makes the default rendered status line leaner (today
    several `alt_*` default on: `alt_git_worktree`, `alt_time_ago`, `alt_time_clock`,
    `alt_time_session`, `alt_time_api`). Golden baselines are regenerated to the new lean
    default — intended, not a regression.
- **Two distinct memory segments — keep both:**
  - Built-in `alt_process_memory` (process RSS) — name unchanged (was `alt_system_memory`).
    Being `alt_*`, it is now off-by-default per the rule above.
  - External example `examples/segments/sysmem` (system AVAILABLE memory) → **rename to
    `system_memory`** (to differentiate from the internal `process_memory`): file name, header
    `id=system_memory`, toggle `segments.system_memory`,
    env `CC_AI_KIT_SEGMENT_SYSTEM_MEMORY`, and — demonstrating the self-describing standard —
    the optional header keys `name=`/`description=`/`icon=`/`sample=`; plus the file's docstring examples,
    `tools/statusline.toml.sample`, the `tools/setup.py` discovery comment, `README.md` /
    `Makefile` references, and tests (`tests/test_setup.py` shipped-segment assertion,
    `tests/test_external_segments.py`, `tests/test_sysmem_e2e.py` → renamed). Historical
    `docs/superpowers/**` plans/specs are left as point-in-time records.
  - **TTL already satisfied:** the header already carries `ttl=10`, and `ttl` is in
    **seconds** — the "10s TTL" ask is already met; no change needed unless a different value
    is wanted.

### Acceptance (data sourcing)
- [ ] Every `alt_*` segment defaults OFF; enabling requires `statusline.toml`/env; golden
      regenerated to the lean default and byte-stable.
- [ ] External segment ships as `system_memory` (id/env/toggle/file/tests) with `ttl=10`;
      no stale `sysmem` reference remains in shipped code/config/tests.
- [ ] Choose renders only categories with ≥ 1 valid source entry; empty categories are
      absent (not placeholdered).
- [ ] Every `SEGMENTS` key resolves to an inventory entry; a missing entry fails the gate.
- [ ] Inventory default `icon`/`line` == renderer defaults (asserted); golden render
      byte-identical.
- [ ] `statusline.toml` `icon`/`line` overrides win over inventory defaults in the wizard.
- [ ] The wizard discovers external segments from BOTH `examples/segments/` (bundled) and
      `${XDG_CONFIG_HOME:-~/.config}/ai-kit/segments/` (user); each is shown tagged by
      provenance (`bundled` / `user`).
- [ ] External segments appear, marked external, with header-supplied
      `name`/`description`/`icon`/`sample`; absent fields fall back to id-as-name / blank
      description / default icon / default line (no crash on a header carrying only `id=`).
- [ ] The wizard-side header parser (`tools/setup.py`) reads the optional
      `name`/`description`/`icon`/`sample` keys; the renderer's header parser
      (`tools/status-line.py`) is UNCHANGED (render path stays `python3 -S` / no UI copy).
- [ ] `examples/segments/system_memory` carries the full self-describing header
      (`name`/`description`/`icon`/`sample` + `line`/`ttl`) as the canonical example.
- [ ] Config path is `~/.config/ai-kit/statusline.toml` everywhere (XDG-aware); no
      `~/.claude/statusline.toml` reference remains in shipped code, the PRD, or the prototype copy.
- [ ] No fake/hardcoded component or segment list (incl. `_protodata.py`) remains in the
      shipped wizard.

## Binding invariants (carried verbatim from the shipped wizard — do not regress)

See `docs/prds/install-wizard-tui-v1.0-prd.md` and the merged implementation.

- **Render-path purity:** `status-line.py` stays `python3 -S` stdlib-only. `uv`/`textual`
  are WIZARD-ONLY (PEP-723 dep in `setup.py`). `settings.json` statusLine stays `python3 -S`.
- **Single-path FAIL-CLOSED:** missing tty / uv / textual / too-small-term / crash →
  stderr reason + non-zero exit; clean abort (`q`/`Esc`) → exit 0, config intact. No
  plain-menu fallback, no headless defaults, no silent `except`.
- **Module seam / DI:** `wizard_app.py` imports nothing from `setup.py` or hyphenated
  modules; it receives engine callables via an injected `WizardContext`, and reaches
  `status-line.py` / `statusline-doctor.py` only by subprocess.
- **Persistence (writes on Install only):** `save_statusline_config` →
  `write_toml_preserving` → `statusline-doctor --doctor` → atomic write + auto-revert.
- **Live preview = the real renderer** fed a temp config via `CC_AI_KIT_CONFIG_FILE`
  (so moves render), debounced, `@work(thread=True, exclusive=True)`, epoch-guarded
  against stale overwrites (the existing "I1" fix).
- **curl | bash:** keep `open_tty()` (getpass-style `FileIO`+`TextIOWrapper`) and
  `stdin_on_tty()` (dup2 `/dev/tty` onto fd 0 for the wizard run). Preserve the PTY E2E.
- **Textual 8.2.7** on py3.12 — verify every API against 8.x (not the older docs).

## Adjacent changes noted

- **Segment rename `alt_system_memory` → `alt_process_memory`** (description "Agent
  process memory") is adopted in the prototype data. If the real segment defaults are
  touched, propagate the rename (and mind the golden-output / [[status-line-segment-domain-naming]]
  naming family). Golden-preserving + back-compat as the segment-naming work requires.
- **Deferred, separate (render path, NOT this wizard):** worktree icon — use `🌲` when a
  worktree is active, gray-strikeout the fallback icon when not. Tracked in memory
  `statusline-worktree-icon-idea`. Do not fold into this branch.

## Open questions — resolved

1. **Focused-chip panel placement** — RESOLVED: full-width, placed BEFORE the OFF section;
   the four Arrange regions (lines / focused / off / preview) are visually differentiated.
2. **Tray → line on activation** — RESOLVED: no number keys; enabling a segment places it on
   its inventory `line` (preferred home).
3. **Success metrics** — RESOLVED: a next-next installer's success is its acceptance
   checklist, not a quantitative KPI; no metric invented.

## Acceptance / verification

- **Mockup parity** per screen (header/footer/panels/colors/keymap) vs `mockup-textual.html`.
- All **binding invariants** above hold (grep-prove the deletions; fail-closed sweeps).
- **Persistence golden:** doctor-validated writes; config byte-identical for an unchanged
  run; auto-revert on invalid.
- **PTY E2E** drives the real app (no-tty fail-closed; picks→symlinks; arrange→TOML+doctor;
  reconfigure pre-load; curl|bash pipe-on-fd0).
- **Full gate green** (pre-commit incl. the `unittest-wizard` Textual+PTY hook).

## Implementation handoff

Recommended: a FRESH session in a new git worktree off `main`.

1. Read this PRD + open `docs/wizard-redesign/mockup-textual.html` and run
   `mockup-textual.py` — that is the design.
2. Use `superpowers:writing-plans` to produce a task-by-task plan
   (`docs/superpowers/plans/YYYY-MM-DD-wizard-ux-redesign.md`), then
   `superpowers:subagent-driven-development` to execute it.
3. Build against the SHIPPED `tools/wizard_app.py` (rework its screens/flow/panels);
   reuse the existing engine, model, persistence, preview worker, and fail-closed guards.
4. Discard the stale uncommitted WIP on `tools/wizard_app.py` / `tests/test_wizard_app.py`
   (an abandoned Enter-hint/palette experiment, superseded by this redesign).
