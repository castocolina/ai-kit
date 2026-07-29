# Skills-Directory Drift Detection Inside the Wizard TUI (Design Spec)

- **Status**: design ready
- **Date**: 2026-07-28
- **Relates to**: E5 (installer wizard) / E7 FR-7.1 (adopt predecessor skill
  links) — moves an existing pre-wizard raw-terminal CLI prompt in
  `tools/setup.py` into the Textual wizard (`tools/wizard_app.py`), following
  the same `WizardContext`-injection / in-step "gate" pattern the wizard
  already uses for the status-line adoption decision. Does not touch
  `prune_stale` (a different, adjacent pre-wizard prompt) or the
  not-yet-implemented context-tools-manager "Step 0"
  (`docs/superpowers/specs/2026-07-28-context-tools-manager-design.md`).

---

## 1. Intent

Reported behavior (verbatim, translated): when a user moves their working
directory into a git worktree, ai-kit's install script detects that the
user's installed skills (symlinks under `~/.claude/skills`, `agents`,
`commands`) point at a now-stale ai-kit directory (because the repo the
symlinks were created against has moved — e.g. the main checkout path vs. a
worktree path, or literally a renamed/relocated install), and asks whether to
re-point them. Today this question is asked as a raw `y/n` prompt on the bare
terminal, **before** the Textual wizard even starts. The user's complaint is
specifically that this decision should be made **inside** the wizard, not as
a plain-CLI pre-step — the polished, footer-key-bar, live-preview experience
of the rest of the installer is interrupted by a prompt that looks and
behaves nothing like it.

This spec proposes moving that detection + decision into the wizard as a
small "gate" screen, reusing a mechanic the wizard already has for an
analogous problem (the status-line adoption decision), rather than inventing
a new UI paradigm.

**Out of scope**: `prune_stale` (a sibling pre-wizard prompt for a different
condition — entries removed *upstream*, not links pointing at a *previous
install location*); any change to `predecessor_candidates()`'s detection
logic itself (it is correct and already unit-tested); the not-yet-built
context-tools-manager "Step 0" (a separate, still-unimplemented design).

---

## 2. Current behavior (verified against this checkout)

**Call chain**: `tools/install.sh` does no drift detection of its own — it
only fetches the repo (bootstrap mode) and `exec`s straight into
`tools/setup.py` (`tools/install.sh:167`, `exec python3
"$INSTALL_DIR/tools/setup.py" ...`). All the logic the user is describing
lives in `tools/setup.py`.

`cmd_install()` (`tools/setup.py:2028-2085`) runs, in order:

1. `prune_stale(...)` at `tools/setup.py:2040` — **different feature**, out
   of scope here (handles repo entries deleted upstream, not a moved
   install).
2. `adopt_predecessor_links(...)` at `tools/setup.py:2044` — **this is the
   exact function the user is describing.**
3. `launch_wizard(...)` at `tools/setup.py:2053` — the Textual wizard,
   called **after** both of the above have already run to completion,
   including any prompting and any filesystem mutation.

`predecessor_candidates()` (`tools/setup.py:1095-1123`) is a small, pure,
read-only function: for every symlink under `~/.claude/<cat>/<name>`, it
checks whether the link's target is foreign to the *current* `install_dir`
(`_is_inside` check, line 1114) yet still carries the ai-kit
`<root>/<cat>/<name>` shape (basename match at 1116, parent-dir-name match at
1118) *and* whether `<name>` is still a current repo entry it could be
re-pointed to (1120-1121). It returns a list of `(cat, name, old_target,
new_target)` tuples. This is exactly what fires when a repo moves from a main
checkout to a worktree path: the symlink's `old_target` still points inside
the vanished/renamed directory.

`adopt_predecessor_links()` (`tools/setup.py:1126-1167`) is where the
prompt lives:

- Calls `predecessor_candidates()` (line 1133); if empty, returns
  immediately (no-op — this part already respects "never show a screen for
  nothing to decide").
- `is_interactive(tty)` (line 1137) — in production this is **always
  True**, because `cmd_install`'s own docstring states it is
  "interactive-only and fail-closed: `require_tty` exits before this
  function is ever called with `tty=None`" (`tools/setup.py:2029-2030`). The
  `if not is_interactive(tty)` warn-only branch (1137-1141) is therefore
  dead in the real call graph today; it exists for direct unit-testing of
  the function in isolation (mirrors the same "unreachable, kept as
  defense-in-depth" comment style already used for `open_tty` at
  `tools/setup.py:936-943`).
- Builds a plain-ANSI banner (`tools/setup.py:1146-1154`) and writes it
  directly to the raw tty via `_tty_write` (line 1155) — a helper that
  writes straight to fd 0/the terminal stream, entirely independent of
  Textual and the alternate screen the wizard will open moments later.
- Calls `ask_yes_no(tty, prompt, default=True)` (line 1158) — a blocking
  synchronous read on the same raw tty.
- **Immediately mutates the filesystem** in the same function call
  (1159-1166): `os.remove` + (if re-pointing) `os.symlink`, once per
  candidate — regardless of whether the user goes on to complete, abort, or
  crash out of the wizard that hasn't even started yet.

So today: detection, the y/n decision, and the actual symlink mutation all
happen synchronously in `cmd_install`, entirely before `launch_wizard` is
reached, on the raw terminal, with no relationship to whatever happens in
the wizard afterward.

---

## 3. Why this matters (the worktree scenario, concretely)

1. User has ai-kit installed from the main checkout; symlinks under
   `~/.claude/skills/*` point into that path.
2. User creates/enters a git worktree whose ai-kit checkout resolves to a
   different `install_dir` (worktree path != main checkout path).
3. User re-runs the installer from inside the worktree.
4. `predecessor_candidates()` correctly flags every old symlink as foreign
   (points at the old path) but ai-kit-shaped and re-pointable.
5. Before the Textual app has drawn a single frame, the user is dropped into
   a bare-ANSI y/n prompt that doesn't share the wizard's visual language
   (no header, no footer key-bar, no live preview) — it reads as a different
   program, is easy to blink past, and breaks the "this is one polished
   tool" impression the rest of the flow (E5/E7) was designed to create.

---

## 4. Proposed behavior

### 4.1 Split detection / decision / mutation into three independent pieces

- **Detection** — `predecessor_candidates()` is unchanged: still pure,
  still read-only, still called early in `cmd_install`. It stops being
  called *by* `adopt_predecessor_links()` and is instead called directly by
  `cmd_install`, with no prompt attached:

  ```python
  cands = predecessor_candidates(paths.claude_dir, paths.install_dir, entries)
  ```

  `cands` is threaded through `_build_wizard_context(...)`
  (`tools/setup.py:1865-1930`) into a **new `WizardContext` field**,
  `predecessor_links: list = ()` (empty-tuple default, matching the existing
  `commit: object = None` default so no other `WizardContext(...)`
  construction site — tests included — needs to change).

- **Decision** — moves entirely into the wizard (§4.2 below). Nothing about
  `predecessor_links` is prompted for or acted on in `cmd_install` anymore.

- **Mutation** — the `os.remove`/`os.symlink` loop currently inlined in
  `adopt_predecessor_links()` (1159-1166) is extracted into a small, pure,
  prompt-free function, e.g.:

  ```python
  def apply_predecessor_decision(claude_dir, cands, repoint, dry, counts):
      """Given an ALREADY-MADE repoint/delete decision (made in the wizard),
      mutate ~/.claude accordingly. No prompting — see WizardContext.predecessor_links
      and the wizard's gate on STEP_CHOOSE for where the decision comes from."""
      for cat, name, _old, new_target in cands:
          link = os.path.join(claude_dir, cat, name)
          try:
              if not dry:
                  if os.path.lexists(link):
                      os.remove(link)
                  if repoint:
                      os.symlink(new_target, link)
              counts["relinked" if repoint else "pruned"] += 1
          except OSError as exc:
              print(f"warn: {cat}/{name} — {exc}", file=sys.stderr)
  ```

  This is called only from the wizard's in-UI `commit()` callable (§4.4),
  not from `cmd_install` directly.

  `adopt_predecessor_links()` itself (the combined prompt+mutate function)
  is retired — `grep -n "adopt_predecessor_links(" tools/*.py` in this
  checkout shows exactly one call site (`cmd_install`, line 2044), so there
  is no other caller to preserve compatibility for. See Open Question 6.

### 4.2 Where the decision lives in the wizard

**Recommendation: a gate on entry to `STEP_CHOOSE`** (step 0, the wizard's
first screen), not a new dedicated step. The wizard already has exactly this
UI shape for an analogous problem: the **status-line adoption gate**, shown
on entry to `STEP_ARRANGE` when the status line's ownership state isn't
already `"ours"` (`tools/wizard_app.py:199-201`, rendering at `420-501`, key
handling at `665-684`). This spec proposes the same mechanic one step
earlier, for the predecessor-links decision:

- `WizardApp.__init__` gains `self.predecessor_gate_done = not
  ctx.predecessor_links` — empty list → gate already "done", `STEP_CHOOSE`
  renders exactly as it does today. This mirrors the existing
  `self.gate_done = ctx.status_line.get("state") == "ours"` line
  (`tools/wizard_app.py:200`) and the same "never show a screen for nothing
  to decide" philosophy already used for empty external-segment lists and
  empty catalogs elsewhere in this codebase.
- `self.state["predecessor_repoint"]` holds the pending/decided boolean,
  mirroring the existing `self.state["adopt"]` slot.
- `_render_choose()` (`tools/wizard_app.py:436+`): when
  `not self.predecessor_gate_done`, the `#picksbox` Static — Choose's single
  content widget, structurally the same kind of "one takeover-able panel"
  that `lane0` is for Arrange — is replaced with a gate banner: every
  `cat/name` candidate, plus the same warning copy the CLI banner already
  uses today (`tools/setup.py:1146-1154`: "These links point at a PREVIOUS
  ai-kit install…", "⚠ Answering No DELETES these N stale link(s) — this
  cannot be undone."). `#picksCount` is blanked while the gate is showing,
  the same way `lane1`/`lane2`/`focchip`/`tray`/`preview` are blanked during
  the Arrange gate (`tools/wizard_app.py:499-500`).
- `_key_choose()` (`tools/wizard_app.py:642+`): before its existing
  cursor/toggle/category branches, if `not self.predecessor_gate_done`,
  handle `y` / `Enter` (repoint = True, the shown default — matches
  `ask_yes_no(..., default=True)` today) and `n` (repoint = False). No
  Escape-to-back: there is no earlier step to return to, this is the first
  thing the wizard shows. `q` still quits the whole wizard unconditionally,
  since that check runs in `on_key` above the per-step dispatch
  (`tools/wizard_app.py:620-622`) — quitting mid-gate needs no new code.
  Once answered: `self.predecessor_gate_done = True`,
  `self.state["predecessor_repoint"] = <bool>`, and the step stays at
  `STEP_CHOOSE`, which now renders its normal component-picker content.
- `_render_footer()` (`tools/wizard_app.py:419-427`): the existing
  special-case `if self.step == STEP_ARRANGE and not self.gate_done:` gets a
  sibling branch, `elif self.step == STEP_CHOOSE and not
  self.predecessor_gate_done:`, showing `[Re-point Y] [Delete N]` (no Back
  key, for the reason above).
- **No new `STEP_*` constant.** No changes to the shapes of `TITLES`,
  `SUBS`, `FOOTERS`, `HELP` (all currently indexed 0-3 for
  Choose/Arrange/Review/Done), no change to the header step-pips math
  (`_render_header`, `tools/wizard_app.py:402-410`, which hardcodes "Step X
  of 3"). Living inside step 0 rather than adding a new screen keeps this a
  small, additive diff.

### 4.3 Alternative considered: a dedicated `STEP_DRIFT` screen

A new step before `STEP_CHOOSE` (shifting `STEP_CHOOSE`/`ARRANGE`/`REVIEW`/
`DONE` by one) was considered and rejected as the primary recommendation:

- It requires renumbering every positionally-indexed table (`TITLES`,
  `SUBS`, `FOOTERS`, `HELP`, the `_render_help` title list, the `_render()`
  dispatch tuple) and generalizing the header's hardcoded "3 steps before
  Done" pip math — a materially larger diff for a screen whose entire
  content is one yes/no question.
- The still-unimplemented context-tools-manager design
  (`docs/superpowers/specs/2026-07-28-context-tools-manager-design.md §5`)
  already proposes its own new "Step 0... before today's
  Choose/Arrange/Review" for a *different* purpose (tool install/configure).
  If this feature also claimed a dedicated pre-Choose step, the two designs
  would collide over the same "first thing you see" slot. Keeping this
  feature as a gate *inside* `STEP_CHOOSE` sidesteps that collision
  entirely (see Open Question 2).

If the human reviewer prefers the dedicated-step approach anyway (e.g. for
visual weight, or because several predecessor links want a richer per-item
list than a single banner affords), §4.2's gate mechanics still apply almost
unchanged — only the screen it's attached to changes.

### 4.4 Execution — deferred to Review-confirm, not immediate

`_make_wizard_commit()`'s `commit(selection, state)` closure
(`tools/setup.py:1933-1959`) gains one more step, alongside the existing
`apply_selection(...)` and `persist_statusline(...)` calls, inside the same
`contextlib.redirect_stdout`/`redirect_stderr` guard (so nothing corrupts the
alternate screen):

```python
if predecessor_links:
    apply_predecessor_decision(paths.claude_dir, predecessor_links,
                                state.get("predecessor_repoint", True), dry, counts)
```

`predecessor_links` is closed over from `cmd_install`'s scope, the same way
`entries`/`dry`/`counts` already are for this closure. Because `counts` is
the *same dict object* threaded from `cmd_install` through
`_make_wizard_commit` into this closure, the post-wizard summary line
(`tools/setup.py:2078-2080`, the `relinked`/`pruned` tallies) keeps working
with zero additional plumbing — this mutation just contributes to the same
counters the CLI-side `adopt_predecessor_links()` used to.

**Per-item failure handling**: `apply_predecessor_decision` wraps each
candidate's `os.remove`/`os.symlink` pair in its own `try/except OSError`
(shown in §4.1), logging a warning and continuing with the remaining
candidates rather than the current unguarded call, which would raise
straight out of `commit()` on the very first permission error and abort the
whole install (components + status line included) over one stale link. A
partial failure should set the commit outcome's `ok=False`, which the Done
screen already renders as "⚠ install incomplete"
(`tools/wizard_app.py:369`, `378-379`) — no new Done-screen state is needed.

---

## 5. Edge cases

- **Empty candidate list** — gate is skipped entirely at `__init__`
  (`predecessor_gate_done = not ctx.predecessor_links` is `True`);
  `STEP_CHOOSE` behaves exactly as it does today. No regression for the
  common case (no stale links).
- **Multiple candidates, or multiple "generations" of a moved/renamed
  install** — `predecessor_candidates()` already collapses everything
  foreign-but-ai-kit-shaped relative to the *current* `install_dir` into one
  flat list; the gate's copy already speaks in terms of "N link(s)", so no
  special-casing is needed for more than one candidate or more than one
  prior source directory.
- **Wizard aborted before Review-confirm** (`q` at Choose, or any later
  step, or a crash) — **this is an intentional behavior change** from
  today. Currently the CLI-side decision executes unconditionally in
  `cmd_install` regardless of what happens in the wizard afterward — even a
  full abort still relinks/deletes, because the mutation already happened
  before the wizard opened. Under this proposal, since the mutation is
  deferred to `commit()`, aborting the wizard leaves the stale links
  completely untouched. This is consistent with the wizard's existing
  "nothing has been written yet — confirm to apply" contract for the Review
  step (`tools/wizard_app.py:81`, `SUBS[STEP_REVIEW]`), but it is a real,
  observable change in when the mutation happens. Flagged in Open Questions.
- **`--dry-run`** — `apply_predecessor_decision` takes the same `dry` flag
  as `apply_selection`; a dry run answers/records the gate decision and
  updates `counts`, but performs no `os.remove`/`os.symlink`, exactly like
  every other dry-run-respecting mutation in this module.
- **Declining is destructive and irreversible** (deletes the stale links
  outright) — the gate's copy must preserve the bold inline warning already
  present in the CLI banner (`tools/setup.py:1149-1150`); no additional
  confirmation step is proposed (matches the existing UX weight for an
  equally destructive action).
- **Interaction with `prune_stale`** — a different, adjacent pre-wizard
  prompt for a different condition (repo entries deleted upstream, not a
  moved install target). Explicitly out of scope for this spec; noted only
  as a parallel candidate for a possible future, separate migration (Open
  Question 5).
- **Interaction with the context-tools-manager "Step 0"** — both features
  want to be "the first thing the wizard shows." This spec's in-step-0 gate
  approach avoids a hard numbering collision with that (also
  still-unimplemented) design, but the two should be explicitly reconciled
  whichever ships second (Open Question 2).

---

## 6. Testing

- **`tests/test_setup.py`** — `predecessor_candidates()`'s existing tests in
  `TestAdoptPredecessorLinks` (`tests/test_setup.py:1104-1152`:
  `test_detects_predecessor_link`, `test_ignores_link_into_current_install`,
  `test_ignores_unrelated_foreign_symlink`,
  `test_ignores_predecessor_with_no_current_entry`) are already prompt-free
  and unaffected by this change. The tty-driven tests further down
  (`test_interactive_repoint_default`, `test_interactive_drop_on_no`, and
  their siblings, `tests/test_setup.py:1154+`) exercise the retired
  `adopt_predecessor_links()` prompt+mutate combo and should be replaced
  with tests against the new pure `apply_predecessor_decision(claude_dir,
  cands, repoint, dry, counts)` — no `tty`/`io.StringIO` fixture needed
  anymore, since there is no prompting left in this function. Add a new
  case for a permission error mid-loop (mock `os.symlink` to raise `OSError`
  on the 2nd of 3 candidates) asserting the 1st and 3rd still complete and
  the error is logged rather than raised.
- **`tests/wizard_fixtures.py`** — `make_ctx()` gains a
  `predecessor_links=()` parameter (default empty), matching the shape of
  every other optional fixture knob already there (`with_external`,
  `sl_state`), so every existing caller is unaffected.
- **`tests/test_wizard_app.py`** — a new `TestPredecessorGate` class
  mirroring `TestAdoptionGate`'s shape
  (`tests/test_wizard_app.py:141-209`): gate visible at init when
  `predecessor_links` is non-empty (`predecessor_gate_done` starts `False`),
  hidden when empty (`True`); `y`/`Enter` set
  `state["predecessor_repoint"] = True` and `predecessor_gate_done = True`;
  `n` sets it `False`; `q` quits cleanly from mid-gate; the footer swaps to
  `[Re-point][Delete]` while ungated and back to the normal Choose footer
  once answered.
- **`tests/test_wizard_pty.py`** — one new PTY end-to-end scenario, seeded
  the same way `TestPhase2E2E.test_pick_skill_and_confirm_creates_symlink`
  already seeds real symlinks under a temp `~/.claude`: create a stale
  predecessor-shaped symlink before spawning `setup.py` under the PTY, drive
  the keypresses through the gate and the rest of the flow to Review-confirm,
  then assert the on-disk result (`os.readlink` resolves into the *new*
  install dir when re-pointed, or the link is gone when deleted) — this is
  the test that actually proves the decision now happens inside the
  alternate screen and takes effect only on confirm, which is the entire
  point of this feature.

---

## Open Questions for User Review

1. **Placement** — I recommend a gate *inside* `STEP_CHOOSE` (reusing the
   status-line adoption gate's mechanic one step earlier) over a dedicated
   new step, to keep the diff small and avoid renumbering every
   step-indexed table. Confirm this matches your intent, or say if you'd
   rather it be its own titled/numbered step (§4.3 describes what would
   change).
2. **Ordering vs. the context-tools-manager "Step 0"** — that design (also
   not yet implemented) wants its own new pre-Choose step. If both land,
   which should render first, and should they be visually distinguished
   from each other? Not designed here — flagging so it isn't forgotten.
3. **Behavior change on abort** — aborting the wizard now leaves stale
   predecessor links completely untouched, whereas today they're resolved
   unconditionally before the wizard even starts. I believe deferring to
   commit-time is the more correct and consistent behavior (matches "nothing
   is written until you confirm"), but it is an observable change from
   today's behavior and I want explicit sign-off before it's implemented.
4. **All-or-nothing vs. per-item** — I kept the CLI's existing single yes/no
   for the *whole batch* of candidates, rather than a per-link
   accept/reject list. Confirm that's still sufficient, or whether you'd
   want a scrollable per-item toggle (a bigger UI, closer to Choose's own
   component picker) for the case where a user wants to re-point some links
   and delete others in the same run.
5. **`prune_stale`** — a sibling pre-wizard CLI prompt for a related but
   distinct condition (repo entries deleted upstream). Should it get the
   same treatment in a follow-up? Not designed here, only flagged as a
   parallel candidate.
6. **Retiring `adopt_predecessor_links()`** — I assumed full retirement of
   the combined prompt+mutate function, since `cmd_install` is its only
   caller in this checkout today. Flag if you'd rather keep it as a thin
   deprecated wrapper for some other caller I haven't seen.
7. **Surfacing the outcome in Review/Done** — should the Review step's
   "what happens on confirm" panel (`#rev-what`) and the Done screen's
   summary explicitly mention the predecessor-link outcome (e.g. "2 stale
   skill link(s) re-pointed")? I assumed yes, consistent with this wizard's
   existing transparency conventions, but didn't nail down exact copy — the
   wording is worth confirming during review rather than guessing further.
