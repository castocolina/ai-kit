# E5 — Installer Ergonomics + Setup Wizard (Design Spec)

- **Status**: design ready · PRD-equivalent (supersedes the "PRD pending" note in `docs/prds/000-ai-kit-overhaul-requirements.md`)
- **Date**: 2026-06-19
- **Depends on**: E4a (config model + recipe), E4b (color subsystem) — both done/merged on `main`
- **Feeds**: E4c (external drop-in segments) — deferred until after E5
- **Source FRs**: FR-5.1 … FR-5.7 (`docs/prds/000-ai-kit-overhaul-requirements.md`)

---

## 1. Intent

Make install fast and configurable. Today `tools/install.sh` (305 lines of bash) does
fetch → verify → link → prune → statusline all at once, links **every** skill, and offers
no interactive choice. E5 turns `install.sh` into a thin **bootstrapper** and moves all real
logic into a stdlib-only Python **setup wizard** (`tools/setup.py`) that lets a developer
pick what to install and configure the status line, with a live preview — driven by plain
stdin prompts and ANSI affordances, **no heavy TUI dependency**.

**Audience reality that shapes the design**: the status line is for **humans at a terminal**.
Only **skills** are ever installed headless (an agent in automation), and that path never
needs the status line. So there is exactly one interactive surface to design — the
human-at-a-terminal wizard — and one minimal non-interactive surface — skills reconcile only.

---

## 2. Bootstrap & handoff contract (FR-5.2)

The canonical entry point is the remote one-liner:

```
curl -fsSL https://raw.githubusercontent.com/castocolina/ai-kit/main/tools/install.sh | bash
```

At that instant `install.sh` is the **only** file on disk — there is no repo, no `setup.py`,
possibly no `git`. Therefore the bootstrapper **must remain standalone bash**: it is the
lowest common denominator that `curl | bash` pipes into. Python logic lives inside a repo
that does not exist yet, so it cannot run first.

### Strict ordering

```
install.sh  (the only file present)
  1. detect mode — resolve own path via BASH_SOURCE[0]:
       • tools/setup.py resolvable relative to me  → LOCAL mode  (a clone) → skip fetch
       • BASH_SOURCE not a real repo file           → BOOTSTRAP mode (piped from curl)
  2. BOOTSTRAP: fetch repo into INSTALL_DIR (git clone / tarball)  → setup.py now exists
  3. ensure python3 is present (clear error + per-OS install hint if absent)
  4. exec python3 "$INSTALL_DIR/tools/setup.py" "$@"
```

`setup.py` is only ever invoked **after** step 2 guarantees it is on disk. The remote
`curl | bash` path and the `git clone && make install` path converge at step 4 — same
wizard, two ways of arriving.

### Mode detection detail

- **LOCAL**: `install.sh` resolves its own directory from `${BASH_SOURCE[0]}`; if
  `../tools/setup.py` (and repo markers) exist there, use that checkout verbatim. This is the
  `git clone … && ./tools/install.sh` / `make install` path. Fetch is skipped.
- **BOOTSTRAP**: when piped from `curl`, `${BASH_SOURCE[0]}` is not a path into a repo
  (it is the process substitution / `bash` itself). Fall through to fetch.
- `AI_KIT_SKIP_FETCH=1` (existing env) forces LOCAL behavior for the test suite.

### What stays in bash vs moves to Python

| Concern | Lives in | Rationale |
|---|---|---|
| mode detect, ensure-python, fetch, `exec` | `install.sh` (bash) | Must run before the repo/Python exist |
| verify, select, link, prune, statusline wiring, config | `tools/setup.py` (Python) | Single source of truth; richer logic, testable |

The proven bash fetch/verify/link/prune behavior is **ported** into `setup.py`, not
discarded; existing `tests/test_install.sh` behaviors are re-expressed as Python unit tests.

---

## 3. Fetch must be convergent

A *sync* (the local checkout mirrors the remote), not an additive overlay. This matters
because deletion detection (below) is only correct if the synced repo truly reflects the
remote.

| Fetch path | Re-run behavior | Deleted-upstream file |
|---|---|---|
| git checkout exists | `git pull --ff-only` | **removed** ✅ (already convergent) |
| first time, git present | `git clone --depth 1` | n/a (fresh) |
| no git → tarball | **extract into a temp dir, then atomically swap** (`rm -rf old && mv tmp old`) | **removed** ✅ (the fix) |

**Bug closed**: today the tarball path does `tar xz --strip-components=1` *over* the existing
dir, which overwrites/adds but **never deletes** files removed upstream — orphans linger and
masquerade as live skills. The temp-dir atomic swap makes the tarball path convergent too, so
deletion detection is **method-independent**.

The atomic swap belongs in the bootstrapper's fetch step (bash), since it precedes `setup.py`.

---

## 4. Skills / agents / commands — selection & reconciliation (FR-5.3, FR-5.4)

### Source of truth: the symlinks themselves

**No state file.** "What did the user select?" is answered by **which ai-kit symlinks exist**
in `~/.claude/{skills,agents,commands}/`. The current install already symlinks each entry into
those dirs and never clobbers real files or foreign symlinks; E5 keeps that and makes the set
*chosen* rather than *all*.

### Reconciliation pass — every run (install / update / reconfigure)

After a convergent fetch, compute two sets and reconcile:

- **A = repo set**: entries present in the freshly-synced checkout.
- **B = installed set**: existing ai-kit symlinks under `~/.claude/<category>/`.

| Case | Set | Action |
|---|---|---|
| In repo, currently linked | A ∩ B | Keep; re-point the symlink if its target drifted |
| In repo, not linked (deselected **or** brand-new) | A − B | **Interactive**: show in the list, toggleable, new ones flagged `NEW`. **Headless**: leave as-is |
| Linked, but gone from repo (deleted upstream) | B − A | **Warn by name + offer to prune** (user-confirmed). Headless: auto-remove the dead link + print a warning |

Consequences:

1. **Symlinks are the persisted selection** — reconfigure pre-checks boxes by reading them; a
   non-interactive update re-applies choices by leaving them alone. The **first-ever install**
   is the only exception: nothing is linked yet, so the wizard defaults **all-on**.
2. A newly-appeared skill on a **non-interactive** update stays **OFF** (not in the link set)
   and surfaces, flagged `NEW`, the next time the wizard runs.
3. Deletion detection requires the convergent fetch of §3 — otherwise a tarball orphan would
   still appear in set A and never be pruned.

### Interactive UX (FR-5.4)

Per-entry toggle rows: `[x]`/`[ ]` marker, the name in an **accent color when enabled**,
**dimmed when disabled**, and a one-line note of what the entry delivers. Plain prompts (read
from `/dev/tty`, see §7): a numbered list; the user types numbers (or `a`/`n` for all/none) to
flip rows, `Enter` to accept. Stale links are surfaced first as a warning block with a
`prune? [y/N]` confirm.

---

## 5. Status-line configuration (FR-5.4, FR-5.7)

The status line is **humans-only** and always interactive. Its state lives in
`~/.config/ai-kit/statusline.toml` (the E4a recipe) — the TOML *is* the persisted selection,
the parallel of symlinks for skills. The recipe is copied to the default path if absent
(E4a behavior), then the wizard reads it every run and lets the user:

- **Toggle each segment** on/off — current enabled/disabled state shown with `[x]`/`[ ]`,
  accent-when-on / dim-when-off.
- **Reorder / move segments** — change order within a line and move a segment between lines
  (edits the `[[line]]` layout). Plain-stdin interaction: a numbered per-line listing with
  commands like `move <seg> up|down` and `move <seg> line <n>`.
- **Toggle the `[git] worktree` knob** — the opt-in 🌳/🌿 worktree-vs-main detection
  (default off; costs an extra `rev-parse` when on).
- **Live showcase area** — after each change, re-render a preview by feeding a representative
  **sample JSON** to `tools/status-line.py` on stdin, with the current toggles expressed as
  `CC_AI_KIT_SEGMENT_<KEY>` env overrides, and print its output. No temp files; reuses the
  live renderer.
- **Write back** the resulting `[segments]` and `[[line]]` layout to the TOML.

**Out of scope by decision — colors & ramps.** The wizard does **not** build a color picker.
It **prints where the TOML lives** and tells the user that ramps, palette, and any advanced
tuning are editable by hand in that file (the recipe is self-documenting). This keeps the
wizard small and avoids a color-grammar input surface (that detail belongs to E4b's file
schema, not an interactive prompt).

---

## 6. settings.json / statusLine wiring (FR-5.5)

The installer points `~/.claude/settings.json`'s `statusLine.command` at the bundled
`status-line.py` (with `python3 -S`, per the perf work already on `main`).

**Double-confirm guard (FR-5.5)**: before changing `statusLine`, inspect the existing value.

- Absent, or already points at the ai-kit `status-line.py` → set/refresh silently.
- Points at a **different** command (a foreign status line) → show the current value and
  require an explicit `y` confirmation before overwriting. Decline → leave it untouched and
  report that the status line was not wired.

Uninstall removes the ai-kit `statusLine` only if it currently points at ai-kit (never
clobbers a foreign one).

---

## 7. Interactive vs non-interactive (no-TTY)

The wizard reads prompts from **`/dev/tty`**, not stdin — because under `curl | bash`,
stdin is the pipe carrying the script (at EOF), while `/dev/tty` reaches the controlling
terminal. This gives a human running `curl | bash` the **full interactive wizard**.

| Condition | Behavior |
|---|---|
| `/dev/tty` opens (a human at a terminal, incl. `curl \| bash`) | Full wizard: skills + status line |
| `/dev/tty` unavailable (genuinely headless — agent automation) | **Skills reconcile only**: link first-time defaults / keep existing selection, auto-remove dead symlinks with a printed warning, **skip the status-line wizard entirely** (headless contexts never render a status line) |

CI/cron is explicitly a **non-goal** — every status-line user is a developer, not a machine.
The headless branch exists only so an agent can install skills unattended.

---

## 8. Entry points & artifacts

### Subcommands (`setup.py`)

`install` (default) · `reconfigure` · `uninstall` — dispatched from one entry point.
Pass-through flags include `--dry-run` (mutate nothing, report intended changes).

### Reconfigure (FR-5.6)

- `install.sh --reconfigure` — re-runs the wizard against the existing checkout, **skips
  fetch** (LOCAL mode forced).
- `make reconfigure` — the repo-clone convenience equivalent.

No new global `ai-kit` PATH command is installed (keeps the surface small and avoids an extra
artifact to clean up on uninstall). An `ai-kit`-on-PATH launcher is noted as a possible
future nicety, out of scope for E5.

### Makefile (FR-5.1)

For users who clone the repo. Targets: `install`, `reconfigure`, `uninstall`, `test`, `lint`.
Each is a thin wrapper over `install.sh` / `setup.py` / the test runners. Standard `make`
tab-completion covers the "shell autocomplete" ask.

### New / changed files

| File | Change |
|---|---|
| `tools/setup.py` | **New** — wizard + install engine (stdlib-only, like `status-line.py`; TDD/unittest) |
| `Makefile` | **New** — install/reconfigure/uninstall/test/lint targets |
| `tools/install.sh` | **Slimmed** from 305 lines to a bootstrapper (mode-detect, convergent fetch incl. tarball atomic-swap, ensure-python, `exec setup.py`) |
| `tests/test_setup.py` | **New** — Python unit tests for verify/reconcile/prune/statusline/config/wizard logic |
| `tests/test_install.sh` | Reduced to the bash bootstrapper's surface (mode detect, fetch, exec) |
| `README.md` | Install/reconfigure docs, the one-liner, `make` targets, headless note |

---

## 9. Top-level wizard flow

```
setup.py install        (default; reconfigure = same minus first-run defaults)
  ├─ verify     enumerate skills/commands/agents, validate shape
  ├─ TTY?  ── no ──▶ headless: reconcile skills (defaults/keep) + warn-clean dead links; exit
  │   yes
  ├─ menu (two-level): configure [Skills] and/or [Status line]?
  ├─ Skills branch    → reconciliation list (§4): toggle, prune-stale-with-confirm → link/unlink
  ├─ Status line branch → segment toggles + reorder/move + worktree knob + live preview (§5) → write TOML
  ├─ statusLine wiring with double-confirm (§6)
  └─ summary: linked/unlinked/pruned counts, TOML path, "edit colors/ramps by hand here"
```

---

## 10. Testing strategy

- **`setup.py`**: TDD with `unittest` (project convention — *not* pytest). Cover: mode/reconcile
  set math (A∩B, A−B, B−A), first-run all-on vs reconfigure keep-state, stale-link
  prune-with-confirm, double-confirm on a foreign `statusLine`, `/dev/tty` vs headless branch
  selection, live-preview command construction (sample JSON + `CC_AI_KIT_SEGMENT_*`), TOML
  read/write of `[segments]` + `[[line]]` reorder.
- **`install.sh`**: `bash tests/test_install.sh` + `shellcheck tools/install.sh` — mode detect,
  convergent fetch (git + tarball atomic-swap leaves no orphans), ensure-python error, exec
  handoff.
- **Drift**: any change to `SEGMENTS`/`LAYOUT`/palette/ramp defaults must still be mirrored in
  `tools/statusline.toml.sample` (`TestSampleRecipe`).
- Run live preview against a checked-in **sample JSON fixture** so previews are deterministic.

---

## 11. Out of scope (YAGNI)

- Interactive color/ramp/palette editing (point to the TOML; defer to manual edit / E4b schema).
- A global `ai-kit` PATH command (future nicety).
- CI/cron-oriented non-interactive status-line configuration (status line is humans-only).
- External drop-in segments (that is **E4c**, sequenced after E5).

---

## 12. Open items

None blocking. Resolved during brainstorming: bash↔Python boundary, symlinks-as-selection
(no state file), convergent tarball fetch, `/dev/tty` interactivity, status-line reorder scope,
reconfigure surface, colors-by-hand.
