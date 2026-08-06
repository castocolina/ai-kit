# Statusline Segment Length Tiers: path / git_branch / alt_git_worktree (Design Spec)

- **Status**: design ready
- **Date**: 2026-08-06
- **Scope**: `tools/status-line.py` (+ `tests/test_status_line.py`) only. No
  wizard/installer changes.
- **Relates to**: builds directly on the `root_name`-based `path` rework in
  `docs/superpowers/plans/2026-07-30-context-tools-worktree-ux-fixes.md` —
  this spec changes how that value is *displayed*, not how it's computed.

---

## 1. Intent

Three segments currently have inconsistent, ad-hoc length handling:

- **`path`**: in-repo shows only `snap.root_name` (the project name) truncated
  at a flat 20-column ellipsis cap (`PATH_MAX_LEN`); outside a repo it falls
  back to `util_display_dir`, a separate flat 20-char **2-tier** rule (full
  `~`-relative path, or basename-only if that's too long).
- **`git_branch`**: **no fixed-length cap at all** — shows the full branch
  name if it fits the terminal's live available width, otherwise vanishes
  entirely. No ellipsis-truncation floor exists today.
- **`alt_git_worktree`**: flat 20-column ellipsis truncation
  (`util_trunc_cols(snap.wt_name, 20)`), no middle tier.

**Goal**: give all three a consistent **3-tier** length model — a preferred
"long" form, a "medium" fallback form, and (for the two non-pinned segments)
a "hidden" tier when even the medium form doesn't fit the terminal. `path`
never hides (see §2.5 background — it is a pinned "floor" segment) — its
third tier is a guaranteed-to-fit short form, not hiding.

**Out of scope**: any change to *what* `root_name`/`branch`/`wt_name` mean or
how they're probed (no new git subprocess calls) — this is purely a
display/formatting layer on top of values the probes already produce. The
one narrow exception: §2.2 needs the repo root's absolute *path*, not just
its basename, to build the home-relative/`parent/name` variants — captured
by adding `GitSnapshot.root_path` (§2.2) alongside the existing `root_name`,
threaded through the same probe functions with no new subprocess call (the
value is already computed and discarded today — see §2.2 for the exact
mechanism). This is a field *addition* purely to carry an already-derived
value further, not a change to any existing field's meaning or how it's
probed.

---

## 2. Proposed behavior

### 2.1 New shared utility: `util_two_state_cap`

```python
def util_two_state_cap(s: str, high: int, low: int) -> str:
    """Return s unchanged if it fits `high` columns; otherwise ellipsis-
    truncate it down to `low` columns via util_trunc_cols. A discrete jump,
    not a continuous shrink — the value either shows in full up to a
    comfortable width, or drops straight to a much shorter floor beyond it."""
    return s if util_visible_width(s) <= high else util_trunc_cols(s, low)
```

Placed alongside `util_first_fitting` (`tools/status-line.py:1357`) and
`util_trunc_cols` (`tools/status-line.py:1555`), which it composes: no new
truncation algorithm, just a named "full or drop-to-floor" decision reused
by all three segments below at their own `high`/`low` values.

### 2.2 `seg_path` — a structural cascade, then a two-state name floor

Both the in-repo and non-repo cases share the same shape: try the two
*structural* variants (full path, then `parent/name`) against a fixed
50-column budget via the existing `util_first_fitting` (repurposed here
against a fixed cap instead of the live terminal `avail` — the function
itself is budget-agnostic, it just returns the first variant that fits);
if **neither** fits, fall to the bare name, itself capped via
`util_two_state_cap(name, 30, 20)`:

- **In-repo** (`snap.in_repo and snap.root_name`): let `root_path` be the
  repo root's absolute filesystem path (already resolvable the same way
  `root_name` is derived — no new subprocess call) and `parent` be
  `os.path.basename(os.path.dirname(root_path))`.
  ```python
  home_relative = ("~" + root_path[len(ctx.home):]) if (ctx.home and root_path.startswith(ctx.home)) else root_path
  structural = util_first_fitting([home_relative, f"{parent}/{snap.root_name}"], 50)
  shown = structural if structural is not None else util_two_state_cap(snap.root_name, 30, 20)
  ```
  e.g. `~/parent-a/parent-b/ai-kit` (if ≤50, shown as-is) → else
  `parent-b/ai-kit` (if ≤50) → else `ai-kit` (if ≤30, shown as-is) → else
  `ai-kit` clipped to 20 columns.
- **Non-repo fallback** (replaces `util_display_dir`'s current body): same
  shape, over `ctx.work_dir`/`ctx.home` instead of the repo root — full
  `~`-relative (or absolute) cwd path and `parent/basename` as the two
  structural variants at cap 50, falling to `basename` alone via
  `util_two_state_cap(basename, 30, 20)`. `util_display_dir` keeps its name
  and signature; only its internals change, so nothing outside this
  function needs to change to pick up the new behavior in the non-repo case.
- **Never hidden**: `seg_path` still returns a string unconditionally in
  both branches — `util_two_state_cap`'s `low` branch always produces a
  bounded, non-empty result (`util_trunc_cols` never returns an empty
  string for a non-empty input), and `path` is never passed through
  `util_first_fitting`/`avail` for the *live* fit check, preserving the
  existing "floor" invariant (pinned, always rendered, never `None`). (The
  fixed-cap `util_first_fitting([home_relative, parent_name], 50)` call
  above is a different, avail-independent use of the same function — see
  §2.5.)

### 2.3 `seg_git_branch` — two-state cap ahead of the existing avail-fit

```python
def seg_git_branch(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    branch = probe_git_for(ctx).branch
    if not branch:
        return None
    shown = util_two_state_cap(branch, 30, 20)
    return util_first_fitting([f"{theme.c('GREY')}[{util_icon('🌿', shown)}]{RESET}",
                           f"{theme.c('GREY')}[{shown}]{RESET}"], avail)
```

Two discrete states, not a smooth shrink: the full name up to 30 columns, or
— once it exceeds that — an ellipsis-truncated 20-column form. The existing
icon/no-icon `avail`-fit cascade wraps around `shown` exactly as it does
today, so a terminal too narrow even for the 20-column form still makes the
segment vanish entirely (the "doesn't appear" tier).

### 2.4 `seg_alt_git_worktree` — same two-state rule

```python
name = util_two_state_cap(snap.wt_name or "", 30, 20)
return util_first_fitting([f"{theme.c('CYAN')}⎇ {name}{RESET}"], avail)
```

Replaces the current flat `util_trunc_cols(snap.wt_name or "", 20)`. The
struck-placeholder branch (main checkout, not a worktree) is untouched — it
never had a name to cap.

### 2.5 Division of the two budgets, made explicit

| Layer | What it answers | Used by |
|---|---|---|
| Fixed-cap layer — `util_first_fitting([...], 50)` for `path`'s structural cascade, `util_two_state_cap(s, 30, 20)` for `path`'s name floor and for `git_branch`/`alt_git_worktree` directly | "Which representation should I *prefer* to show, regardless of terminal size?" | `path` (both branches), `git_branch`, `alt_git_worktree` |
| `util_first_fitting([...], avail)` — the *live* terminal width | "Does the terminal actually have room for that representation right now?" | `git_branch`, `alt_git_worktree` (not `path` — pinned) |

`path` only uses the first layer (it must never disappear); `git_branch`
and `alt_git_worktree` use both, in that order. Note `util_first_fitting`
appears in *both* layers for `path` — once against a fixed 50-column budget
(structural cascade) and, for the other two segments, again against the
live `avail` (unrelated call, different budget) — the function itself does
not care which kind of budget it's handed.

---

## 3. Edge cases

- **`git_branch`'s 20-column truncated form is itself wider than a very
  narrow `avail`**: unchanged from today's behavior for the icon/no-icon
  cascade — `util_first_fitting` already hides the segment when nothing fits,
  regardless of which fixed-length tier produced the candidate string.
- **Repo root not under `ctx.home`**: `home_relative` falls back to the raw
  absolute `root_path` (same substitution rule `util_display_dir` already
  uses today) — no new edge case, same substitution logic reused.
- **`parent` at filesystem root** (e.g. repo root is `/ai-kit`, no real
  parent directory): `os.path.dirname("/ai-kit")` is `/`, so `parent =
  os.path.basename("/")` is `""` — the `parent/name` structural variant
  becomes `"/ai-kit"` (leading slash, empty parent). This is an extreme,
  unlikely-in-practice layout; since it's just one candidate in the
  `util_first_fitting([home_relative, parent_name], 50)` cascade, and the
  name-only floor (`util_two_state_cap(root_name, 30, 20)`) is always
  reached if neither structural variant fits, `path` never breaks even if
  this one variant looks odd — flagged as acceptable rather than
  special-cased.
- **Combined `repo:/external/path` display when cwd diverges from the repo
  tree**: confirmed out of scope — the git probe only succeeds
  (`snap.in_repo`) when the cwd is already inside the repo's tree, so this
  situation cannot occur; no code path needs to handle it.
- **Performance**: no new subprocess calls. `os.path.dirname`/`basename` are
  pure string operations on values (`root_path`, `ctx.work_dir`) already
  available; `util_two_state_cap` and the fixed-cap `util_first_fitting`
  call are pure Python over already-computed strings.

---

## 4. Testing

Extend `tests/test_status_line.py`:

- **`util_two_state_cap` (new, standalone)**: value returned unchanged when
  it fits `high`; ellipsis-truncated to `low` when it exceeds `high`
  (never wider than `low`, and never re-checked against `high` again — a
  single discrete jump, not iterative shrinking).
- **`seg_path` in-repo**: four tests covering the full cascade — full
  home-relative path under 50 cols → shown verbatim; over 50 →
  `parent/root_name` (still ≤50) → shown verbatim; both structural variants
  over 50 but `root_name` alone ≤30 → shown verbatim (the untruncated branch
  of the name floor); both structural variants over 50 **and** `root_name`
  alone over 30 → clipped to 20. Plus the non-under-home case (absolute
  path variant) and the empty-`root_name` fallback (existing behavior,
  reverify unaffected).
- **`seg_path` non-repo**: mirror set of tests against `util_display_dir`
  directly, confirming the new cascade (50-cap structural, 30/20-cap name
  floor) replaces the old flat 20-cap/2-tier behavior — this is a
  deliberate behavior change, so the old `TestDisplayDir` assertions pinned
  to the 20-char threshold need updating, not just re-verifying.
- **`seg_git_branch`**: branch ≤30 cols shown in full (existing icon-fit
  tests still pass, since they use short branch names); branch >30 cols
  capped to 20 with ellipsis before the icon-fit cascade runs; a branch
  whose 20-col form still doesn't fit a very narrow `avail` still hides
  entirely (existing hide-on-no-fit test extended with a long-branch-name
  case).
- **`seg_alt_git_worktree`**: same three-case shape as branch, replacing the
  existing flat-20-cap assertions with the new 30/20 two-state ones.
- **Existing tests to re-verify unaffected**: `test_worktree_main_checkout_struck_placeholder`,
  `test_worktree_hidden_outside_repo` (no name to cap in either case).
