# Wizard Step Reorder: Statusline First, Components Second (Design Spec)

- **Status**: design ready
- **Date**: 2026-08-06
- **Scope**: `tools/wizard_app.py` only. No changes to `setup.py`, `status-line.py`,
  the headless `--examples`/non-interactive install path, or the housekeeping/
  adoption-gate mechanics themselves — only *when* (which step) they run on.
- **Relates to**: extends the same `WizardApp` Textual flow touched by
  `docs/superpowers/plans/2026-07-30-context-tools-worktree-ux-fixes.md`.

---

## 1. Intent

Today the install wizard's first step is the component picker (skills/
commands/agents — `STEP_CHOOSE`), and the status-line segment arranger
(`STEP_ARRANGE`) is second. The user wants this swapped: **status line first,
then components** — `Arrange → Choose → Review → Done`.

**Out of scope**: any change to what each step *does* internally (the
housekeeping gate, the statusline adoption gate, segment arranging mechanics,
Review/Done rendering) — this is purely a reorder of two existing steps and
the transitions between them.

---

## 2. Current mechanics (traced precisely)

- `STEP_CHOOSE, STEP_ARRANGE, STEP_REVIEW, STEP_DONE = 0, 1, 2, 3`
  (`tools/wizard_app.py:38`).
- Three parallel structures are indexed **positionally** by these integers:
  `TITLES` (line 72), `SUBS` (line 74), `FOOTERS` (line 42) — plain lists, in
  Choose/Arrange/Review/Done order. `HELP` (line 53) is a **dict** keyed by
  the constants, so it is order-independent.
- Two dispatch tuples index by `self.step` directly: the render dispatch
  (`(self._render_choose, self._render_arrange, self._render_review,
  self._render_done)[self.step]`, line ~416) and the key-handler dispatch
  (`(self._key_choose, self._key_arrange, self._key_review,
  self._key_done)[self.step](event)`, line ~663).
- Initial state: `self.step = STEP_CHOOSE` (`__init__`, line 199).
- The **housekeeping gate** (stale/predecessor component-link cleanup) is
  nested inside Choose: `_render_choose` early-returns to
  `_render_housekeeping_gate` while `not self.housekeeping_done`; `_key_choose`
  dispatches to `_key_housekeeping` the same way. It is computed once from the
  `ctx.housekeeping` snapshot passed at construction — never re-probed on
  re-entry to Choose.
- The **statusline adoption gate** (`gate_done` — "wire your status line?") is
  nested inside Arrange the same way, but *is* re-checked on entry via
  `_enter_arrange()` (line 674): `if not self.state.get("adopt"): self.gate_done
  = self.ctx.status_line().get("state") == "ours"` — this exists so a prior
  "decline" never sticks against a status line that changed underneath the
  session between visits.
- Explicit transition targets today (`self.step = STEP_X` call sites):

  | Site | From → key | Today's target |
  |---|---|---|
  | `_key_choose`, `n==0` branch | Choose, Enter (empty picker) | `_enter_arrange()` → Arrange |
  | `_key_choose`, normal Enter | Choose, Enter | `_enter_arrange()` → Arrange |
  | `_key_arrange`, gate not done, Escape | Arrange (gate), Esc | Choose |
  | `_key_arrange`, gate declined | Arrange (gate), y/n/Enter → decline | Review (segment board skipped) |
  | `_key_arrange`, post-gate Enter | Arrange, Enter | Review |
  | `_key_arrange`, post-gate Escape | Arrange, Esc | Choose |
  | `_key_review`, Escape | Review, Esc | Arrange *if* `state["adopt"]` else Choose |

- `_goto(step)` (line 670) is a small helper (`self.step = step; return True`)
  defined but not currently called from any site above or from tests — dead
  code today; this spec does not add new callers of it either (the transition
  rewrites below assign `self.step` directly, matching the existing style at
  every other call site).

---

## 3. Proposed behavior

### 3.1 Renumber, don't re-architect

Swap the two constant values only: `STEP_ARRANGE, STEP_CHOOSE, STEP_REVIEW,
STEP_DONE = 0, 1, 2, 3`. Every dict-keyed structure (`HELP`) and every
comparison against the named constants (`self.step == STEP_ARRANGE`, etc.)
continues to work unchanged. Three things must be updated to match the new
numeric order:

1. **`TITLES`, `SUBS`, `FOOTERS`** — reorder their first two positional
   entries (index 0 becomes what is today index 1, and vice versa) so index 0
   is Arrange's content and index 1 is Choose's.
2. **Render dispatch tuple** — reorder to
   `(self._render_arrange, self._render_choose, self._render_review,
   self._render_done)[self.step]`.
3. **Key dispatch tuple** — reorder to
   `(self._key_arrange, self._key_choose, self._key_review,
   self._key_done)[self.step](event)`.

### 3.2 Initial state

`self.step = STEP_ARRANGE` in `__init__` (was `STEP_CHOOSE`). `gate_done` is
already computed earlier in `__init__` from `ctx.status_line()`
(unconditionally, not just on transition) — no additional gate-refresh call
is needed at startup; the wizard opens directly on whichever state (gate
pending / board) that computed value implies.

### 3.3 Housekeeping gate stays bound to Choose

The housekeeping gate is about stale/predecessor **component** links
(skills/commands/agents) — it has no relationship to the status line. It
keeps its existing home inside `_render_choose`/`_key_choose`, unchanged
internally. Its only observable difference is *when* the user reaches it:
after arranging the status line (step 1) instead of before (step 0).

### 3.4 Rewritten transition table

| From → key | New target | Notes |
|---|---|---|
| Arrange (gate not done), Escape | **no-op** (unhandled, same as `return False`) | Arrange is now the first step — nothing to back out to, mirroring how Escape is unhandled on Choose today. |
| Arrange (gate), decline (y/n/Enter → `adopt=False`) | **Choose** | Was Review. Declining just means "nothing to arrange," so advance to the next step instead of skipping two. |
| Arrange, post-gate Enter | **Choose** | Was Review. |
| Arrange, post-gate Escape | **no-op** | Was Choose; now nothing precedes Arrange. |
| Choose, Enter (both the `n==0` and normal branches) | **Review** | Was Arrange (via `_enter_arrange()`). Arrange already happened before Choose, so Choose's Enter goes straight to Review. |
| Choose, Escape *(new)* | **Arrange** | Not handled today (Choose has no predecessor currently). Reuses `_enter_arrange()`'s existing gate-refresh logic verbatim, just called from a new site. |
| Review, Escape | **Choose, always** | Was conditional on `state["adopt"]` (Arrange vs Choose), because Arrange used to be skippable-but-adjacent to Review. In the new order Choose is *always* Review's immediate predecessor (Arrange's decline branch already routes through Choose per the row above), so the conditional collapses to a single unconditional target — a net simplification. |

`_enter_arrange()` keeps its name and its body unchanged (it already does
exactly the "re-check the adoption gate unless already opted in" job the new
Choose→Escape path needs); only its call site moves from Choose's Enter
handler to Choose's Escape handler.

### 3.5 Help/footer copy

`HELP[STEP_CHOOSE]`'s trailing entry currently reads `("Enter", "Continue to
Arrange")` → becomes `("Enter", "Continue to Review")`. `HELP[STEP_ARRANGE]`'s
`("Enter / Esc", "Continue to Review / back to Choose")` → becomes `("Enter",
"Continue to Choose")` (no Esc entry — Arrange has no back target anymore).
`HELP[STEP_REVIEW]`'s `("Esc", "Back to Arrange")` → becomes `("Esc", "Back
to Choose")`. `FOOTERS`' reordered entries need the same "Back"/"Continue"
label sweep applied at the same time, since they're the terser footer-bar
equivalent of the same copy.

---

## 4. Testing

`tests/test_wizard_app.py` — no new test *files*, but two existing test
groups assert on the old Choose-first transition semantics and need their
assertions rewritten to match §3.4, not just their setup:

- The two tests immediately above `TestAdoptionGate` (`test_tab_is_noop`,
  `test_enter_advances_to_arrange`): the latter's name and assertion invert —
  the wizard now *starts* on Arrange rather than reaching it via Enter from
  Choose. A new test should cover Choose's Enter advancing to Review instead.
- `TestAdoptionGate` (7 tests, all currently written against "Choose → Enter
  → Arrange gate"): every test's setup opens with `pilot.press("enter")` to
  reach the gate from Choose — that no longer applies, since the gate is now
  shown at init. `test_gate_escape_returns_to_choose` specifically needs to
  become "Escape during the gate is a no-op" per §3.4's first row (Arrange has
  no predecessor now). `test_review_escape_after_decline_returns_to_choose`
  keeps its target (Choose) but its precondition path (declining now lands on
  Choose directly per §3.4, not via a separate Review step first) should be
  re-verified reflects the new decline→Choose routing.
- No changes needed to `TestArrangeMoves` or later classes — those exercise
  in-step segment-arranging mechanics, unaffected by step ordering.

---

## 5. Why not a step-order indirection layer

Considered adding a `STEP_ORDER` list and making `self.step` an order-index
translated through it (decoupling "which screen" from "what position"),
which would make future reorders cheaper. Rejected: this is a one-time
reorder, not a request for configurable step ordering, and the indirection
would touch every `self.step == STEP_X` comparison across the file and tests
for a flexibility nobody asked for (YAGNI). Approach taken (§3.1) is a
same-shape renumbering with the smallest possible diff.
