# Path Segment: Show Project Name Inside Worktrees (Design Spec)

- **Status**: design draft — pending user review
- **Date**: 2026-07-28
- **Scope**: `tools/status-line.py` (+ `tests/test_status_line.py`) only. No wizard,
  installer, or PRD-index changes.
- **Relates to**: FR-7.2 in `docs/prds/e7-install-ux-worktree-visibility-v1.0-prd.md`,
  which introduced the dedicated `alt_git_worktree` segment (`⎇ <name>`) as the
  session's "which worktree am I in" signal. This spec is a small, independent
  follow-up: it does not reopen FR-7.2, it removes an overlap FR-7.2 left behind.

---

## 1. Intent

User-reported (verbatim, Spanish): *"cuando el agente esta en un worktree aun asi
me interesa saber el nombre del projecto en lo que es el path segment (ahora
ai-kit), sino seria redundante con el worktree segment como tal"* — "even when the
agent is in a worktree, I still want to know the project name in the path segment
(currently 'ai-kit'); otherwise it would be redundant with the worktree segment."

Today, the `path` segment and the `alt_git_worktree` segment can end up showing
**the same string** — the worktree's own directory basename — when the session
runs inside a linked git worktree. That defeats the point of having two segments:
each should carry information the other doesn't.

**Goal**: make `path` reliably show the *project/repo name* (e.g. `ai-kit`)
regardless of whether the CWD is the main checkout or any linked worktree under
it, so responsibilities split cleanly:

- **`path`** → "what project is this" (repo identity, stable across worktrees).
- **`alt_git_worktree`** → "which worktree, if any, am I sitting in" (worktree
  identity, varies per session).

**Out of scope**: renaming either segment, changing `alt_git_worktree`'s own
behavior, changing `path`'s behavior for the main checkout or for non-worktree
subdirectories (see §6 for why that's deliberately untouched), any wizard/
installer/inventory-copy changes beyond keeping `segments_inventory.toml`'s
description accurate.

---

## 2. Current behavior (traced precisely)

### 2.1 `seg_path` — `tools/status-line.py:2181-2182`

```python
def seg_path(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    return f"{theme.c('BLUE')}{util_display_dir(ctx.work_dir, ctx.home)}{RESET}"  # floor
```

It is pure string manipulation over `ctx.work_dir` / `ctx.home` — **no git probe,
no subprocess call**. `ctx.work_dir` (`core_build_context`, line 1698) is
`os.path.abspath(workspace.current_dir)` from Claude Code's own status JSON — i.e.
literally "whatever directory the session's CWD currently is," with zero
awareness of git or worktrees.

### 2.2 `util_display_dir` — `tools/status-line.py:1516-1523`

```python
def util_display_dir(work_dir: str, home: str) -> str:
    """Return work_dir with home replaced by '~'; truncate to basename if too long."""
    shown = work_dir
    if home and work_dir.startswith(home):
        shown = "~" + work_dir[len(home):]
    if len(shown) <= PATH_MAX_LEN:
        return shown
    return os.path.basename(work_dir.rstrip("/")) or shown
```

`PATH_MAX_LEN = 20` (`tools/status-line.py:89`). Two branches:

- **Short enough (≤ 20 cols after `~`-collapse)**: shows the full `~`-relative
  path, e.g. `~/proj`.
- **Too long**: collapses to `os.path.basename(work_dir)` — the CWD's own last
  path component, nothing more.

### 2.3 Why this produces the redundant/wrong output in a worktree

- **Main checkout**, e.g. `work_dir = /var/home/bazzite/git/personal/ai-kit`,
  `home = /var/home/bazzite`: `~`-relative is `~/git/personal/ai-kit` (22 chars,
  over the 20-char floor) → collapses to `os.path.basename(...)` = **`ai-kit`**.
  This is the "correct-by-accident" case the user calls "ahora ai-kit" — it
  happens to work here only because the main checkout's own directory name *is*
  the project name.
- **Inside a linked worktree**, e.g.
  `work_dir = /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/context-tools-manager-plan1`:
  `~`-relative is far past 20 chars → collapses to
  `os.path.basename(work_dir)` = **`context-tools-manager-plan1`** — the
  worktree's own directory name, not the project name. `ai-kit` disappears from
  the segment entirely.

So `seg_path` has **no worktree-awareness at all** today; it isn't "wrong git
logic," it simply reports the literal CWD basename, which happens to coincide
with the project name on the main checkout and happens to coincide with the
worktree name inside a worktree. The redundancy is exactly this coincidence.

### 2.4 `seg_alt_git_worktree` — `tools/status-line.py:2202-2214`

```python
def seg_alt_git_worktree(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    snap = probe_git_for(ctx)
    if not snap.in_repo:
        return None
    if not snap.is_worktree:
        return util_first_fitting([f"{theme.c('GREY')}\033[9m⎇ wt{RESET}"], avail)
    name = util_trunc_cols(snap.wt_name or "", 20)
    return util_first_fitting([f"{theme.c('CYAN')}⎇ {name}{RESET}"], avail)
```

`snap.wt_name` comes from `probe_git_worktree_info` (`tools/status-line.py:758-773`):
a single `git -C <work_dir> rev-parse --git-dir --git-common-dir --show-toplevel`
call. `is_worktree = git-dir != git-common-dir` (line 770); `wt_name =
os.path.basename(--show-toplevel)` when `is_worktree` (line 772) — i.e. the exact
same "worktree directory's own basename" that `seg_path` accidentally falls back
to today. **This confirms the collision**: in a worktree, once `seg_path`
collapses (which it almost always does, since `.claude/worktrees/<branch>/` paths
are long), `path` and `alt_git_worktree` show the identical string, just styled
differently (blue, no icon vs. cyan `⎇`).

### 2.5 Supporting facts

- `alt_git_worktree` defaults to **off** (`SEGMENTS["alt_git_worktree"] = False`,
  line 74) — the redundancy is only visible to sessions/configs that opt in,
  which the requesting user has.
- `git_branch` defaults to **on** (line 74) and already calls `probe_git_for(ctx)`
  every render, which memoizes one `GitSnapshot` per render in
  `ctx.probe_cache["git"]` (comment, lines 247-250: "one GitSnapshot — no
  duplicated git querying").
- The worktree-detection half of that snapshot (`is_worktree`/`wt_name`) is
  additionally disk-cached with a TTL (`probe_worktree_info_cached`, lines
  776-803; default `_GIT_CACHE_TTL = 5` seconds, line 141) — it rarely changes,
  so it is not re-run on every render even when a git segment is enabled.
  `branch`/`dirty` are *always* read fresh (full `git status --porcelain
  --branch`, no cache) by design (docstring, lines 814-820).
- `path` is in `PINNED = {"path", "context"}` (line 123) — always rendered even
  under a too-narrow terminal — and the code comment marks it `# floor` (line
  2182) and requires `SEGMENTS["path"] = True` always (line 70-71 invariant
  comment). Any change here must never make `path` return `None` or raise.

---

## 3. Proposed behavior

### 3.1 Resolve a `project_name` alongside the existing worktree probe

`probe_git_worktree_info` already runs
`git rev-parse --git-dir --git-common-dir --show-toplevel` and already parses
line 2 (`--git-common-dir`) to compare against line 1 (`--git-dir`) for
`is_worktree`, then discards it. **No new subprocess call is needed** — just
also keep that value and derive the project root from it:

```python
def probe_git_worktree_info(work_dir: str) -> tuple[bool, bool, str, str]:
    ...
    common_dir = lines[1] if len(lines) >= 2 else ""
    # git-common-dir is relative to work_dir unless it's already absolute;
    # normalize before taking its parent.
    common_abs = common_dir if os.path.isabs(common_dir) else os.path.normpath(
        os.path.join(work_dir, common_dir))
    root = os.path.dirname(common_abs) if os.path.basename(common_abs) == ".git" else common_abs
    project_name = os.path.basename(root.rstrip("/"))
    return True, is_worktree, name, project_name
```

`git-common-dir` always resolves to the **main checkout's** shared `.git`
directory — that is true whether you run it from the main checkout itself or
from any linked worktree, no matter how deeply nested the worktree's own
directory happens to be. So `project_name` is the same, correct value
("ai-kit", or whatever the repo is really called) from every worktree, and it is
computed generically from the filesystem — nothing here hardcodes "ai-kit" or
any other repo name.

### 3.2 Thread `project_name` through the shared probe

- `GitSnapshot` (line 251-258) gains one field: `project_name: str` (basename of
  the main checkout's root; `""` outside a repo).
- `probe_worktree_info_cached` (776-803) and `probe_git_snapshot` (806+) pass it
  through like `wt_name` today. The on-disk TTL-cache JSON gains a
  `"project_name"` key; old cache files that lack it simply miss the existing
  `except (OSError, ValueError, KeyError)` guard (line 793) and recompute once —
  no migration needed.

### 3.3 `seg_path` consumes it, only in the worktree branch

```python
def seg_path(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    snap = probe_git_for(ctx)
    shown = snap.project_name if (snap.in_repo and snap.is_worktree and snap.project_name) \
        else util_display_dir(ctx.work_dir, ctx.home)
    return f"{theme.c('BLUE')}{shown}{RESET}"  # floor
```

- **Inside a linked worktree**: shows `snap.project_name` (e.g. `ai-kit`) —
  unconditionally, regardless of how long the worktree's own path is (no 20-char
  floor logic applies here; the project name is what's shown, full stop).
- **Main checkout, or outside any git repo**: byte-for-byte identical to
  today's behavior (`util_display_dir(ctx.work_dir, ctx.home)`) — untouched.
- `path` can never return `None`/raise: `snap.project_name` falls back to the
  existing `util_display_dir(...)` whenever it's falsy (e.g. a bare-repo edge
  case where the heuristic in §3.1 can't confidently find a name), preserving
  the "path is the floor" invariant (§2.5).

### 3.4 Division of responsibility after the fix

| Segment | Shows | Varies by |
|---|---|---|
| `path` | Project/repo name (or CWD, outside a worktree) | Which *repo* you're in |
| `alt_git_worktree` | Active worktree name, or struck `⎇ wt` on the main checkout, or hidden outside a repo | Which *worktree* within that repo |

No overlap: `path` never shows worktree-specific detail again once `is_worktree`
is true, and `alt_git_worktree` never shows the project name (it already only
ever shows `wt_name` / the struck placeholder / nothing — unchanged by this spec).

---

## 4. Edge cases

- **Non-git directory** (`in_repo=False`): unaffected — `path` shows
  `util_display_dir` exactly as today.
- **Main checkout, not a worktree** (`in_repo=True, is_worktree=False`):
  unaffected — same `util_display_dir` collapse-to-basename behavior as today,
  including for subdirectories of the main checkout (e.g. `cd tools/` still
  shows whatever it shows today). This is a deliberate scope boundary (§6), not
  an oversight: the user's complaint is specifically about the worktree case.
- **Renamed or moved repo**: `project_name` is derived from the *current*
  filesystem path of the main checkout's `.git` directory on every probe (or
  within the existing ≤5s TTL window) — a rename is reflected within one cache
  window, same staleness bound `wt_name` already accepts today. No hardcoded
  name is ever baked in.
- **Nested worktree directory structures**: `git worktree add` always registers
  a new worktree against the one shared `git-common-dir`, no matter how deep or
  unusual the directory it's created under — so `project_name` resolves
  correctly regardless of nesting depth (e.g. a worktree created from inside
  another worktree still ultimately points at the same common dir).
  `is_worktree`/`wt_name` already relies on this same property today.
  Nested worktrees introduce no new case to handle.
- **Bare repository / unusual `--git-common-dir` shape** (no working tree, or a
  common-dir that doesn't end in `.git`, e.g. some submodule/bare-repo layouts):
  §3.1's heuristic falls back to using `common_abs` itself (not its parent) as
  the root, so `project_name` still resolves to *some* directory basename rather
  than crashing; if that guess is ever wrong for a real user's setup, `path`
  still never breaks — worst case it shows a less-than-ideal name, never `None`
  or an exception (see §3.3's fallback).
- **Symlinked worktree/repo paths**: `git rev-parse` already resolves symlinks
  internally before printing `--git-dir`/`--git-common-dir`/`--show-toplevel`,
  so `os.path.basename(...)` operates on git's already-resolved path, not the
  possibly-symlinked literal CWD.
- **Performance**: no new subprocess call is introduced — `project_name` is
  parsed from output the existing `git rev-parse` call already produces (§3.1),
  and it rides the existing ≤5s on-disk TTL cache (§2.5). The one real cost this
  spec adds: `seg_path` now calls `probe_git_for(ctx)` (the *full* shared
  `GitSnapshot`, not just the worktree-only probe), so in the narrow
  configuration where a user disables `git_branch`, `git_dirty`, **and**
  `alt_git_worktree` but keeps `path` on, `path` will now trigger one
  `git status --porcelain --branch` subprocess call per render that it did not
  trigger before (that half of the snapshot is deliberately never cached, per
  §2.5). In the default configuration (`git_branch: True`), this call already
  happens every render regardless of `path`, so there is no added cost for the
  common case. See §7 for the alternative considered here.

---

## 5. Alternative considered (and why the above is recommended)

**Option B**: give `seg_path` its own narrower probe call directly to
`probe_worktree_info_cached(ctx.work_dir, ttl, cache_base)`, bypassing
`probe_git_for(ctx)` / the full `GitSnapshot` entirely, so `path` truly never
gains a *new* subprocess cost in any configuration (it would only ever hit the
already-TTL-cached worktree probe, never the always-fresh `git status` call).

This preserves the "path is nearly free" property in the all-git-segments-off
configuration, but it means `path` and `git_branch`/`alt_git_worktree` no longer
strictly share one probe invocation path per render — `probe_worktree_info_cached`
would be called from two places in a render where both `path` and (say)
`alt_git_worktree` are enabled, in mild tension with the "no duplicated git
querying" comment at lines 247-250 (though the second call would almost always
be a cache hit against the same on-disk TTL file, since both calls land in the
same render/process, so the actual duplicate cost is a stat + JSON read, not a
subprocess spawn).

**Recommendation**: Option A (§3.3, shared `GitSnapshot`) — it keeps the "one
shared probe" invariant literally true, the added cost only shows up in a
non-default configuration, and that cost is one subprocess call gated by the
same 5s-ish cadence as everything else in this file. Flagged as an explicit open
question below in case the user weighs this differently.

---

## 6. Why `path`'s non-worktree behavior is deliberately untouched

It would be tempting to make `path` *always* show just the project name,
everywhere, for consistency. Rejected: that changes established behavior for
every non-worktree session (e.g. it would stop showing a short subdirectory
path like `~/proj/tools` that fits under the 20-char floor today), which is a
bigger, unrelated behavior change the user did not ask for and that existing
tests (`TestDisplayDir`, `tests/test_status_line.py:550-560`) explicitly pin.
This spec's blast radius is exactly: **inside a linked worktree, and only
inside a linked worktree, `path` shows the project name instead of the
worktree's own directory name.**

---

## 7. Testing

Extend `tests/test_status_line.py`:

- **`_data()` helper** (lines 53-95): add `project_name` to `probe_defaults`
  (default `""`) and thread it into the seeded `GitSnapshot` at line 81-84, so
  existing tests that don't care about it are unaffected.
- **`probe_git_worktree_info` / `probe_git_snapshot` parsing** (mirror
  `test_git_snapshot_clean_and_worktree_name`, lines 933-947 — fake
  `subprocess.run` returning `--git-dir`/`--git-common-dir`/`--show-toplevel`
  lines): assert `project_name` is the basename of the common-dir's parent
  (e.g. `common-dir=/repo/.git` → `project_name == "repo"`), for both the
  worktree case (`is_worktree=True`) and the main-checkout case
  (`is_worktree=False`, git-dir == git-common-dir) — confirm `project_name` is
  populated in both, even though `seg_path` only consumes it in the former.
- **`seg_path` new tests**:
  - `test_path_shows_project_name_in_worktree`: `_data(work_dir=".../worktrees/foo",
    in_repo=True, is_worktree=True, project_name="ai-kit")` → output strips to
    exactly `"ai-kit"`, and does **not** contain the worktree dir's own name
    (`"foo"`).
  - `test_path_unaffected_on_main_checkout` /
    `test_path_unaffected_outside_git_repo`: `is_worktree=False` /
    `in_repo=False` respectively → output unchanged from today's
    `util_display_dir(...)` result — regression guard against scope creep
    (§6).
  - `test_path_falls_back_when_project_name_empty`: `is_worktree=True,
    project_name=""` (the bare-repo/heuristic-miss edge case, §4) → falls back
    to `util_display_dir(...)`, never `None`/exception — guards the `path` "floor"
    invariant (§2.5).
- **Existing tests to re-verify unaffected**: `TestDisplayDir` (550-560),
  `test_path_never_none` (530-531), `test_pinned_path_present_even_when_too_narrow`
  (588-591), `test_worktree_active_shows_name_cyan` /
  `test_worktree_main_checkout_struck_placeholder` /
  `test_worktree_hidden_outside_repo` (357-371, `seg_alt_git_worktree` —
  confirm it is byte-for-byte unchanged by this spec).
- **Optional real-git smoke augmentation**: `TestProcAndGit.test_proc_rss_and_git_smoke`
  (856-866) already runs a real (unmocked) `probe_git_snapshot` call; consider
  adding a sibling smoke test that does a real `git init` + `git worktree add`
  in a `tempfile.TemporaryDirectory()` and asserts `project_name` resolves to
  the main checkout's directory name end-to-end — catches drift if a future git
  version changes `rev-parse --git-common-dir`'s output shape, which the mocked
  unit tests above can't catch.

---

## Open Questions for User Review

1. **Probe cost tradeoff (§5)**: I recommend Option A — `seg_path` reads the
   full shared `GitSnapshot` via `probe_git_for(ctx)`, which means `path` is no
   longer unconditionally git-free in the (non-default) configuration where a
   user disables `git_branch`, `git_dirty`, and `alt_git_worktree` but keeps
   `path` on. Option B (a narrower, `path`-only call straight to
   `probe_worktree_info_cached`) avoids that but slightly breaks the "one
   shared probe call site" architecture. Which do you prefer?
2. **`common-dir` → project-root heuristic (§3.1, §4)**: I assumed
   `--git-common-dir` always ends in `/.git` for a normal (non-bare) repo or
   worktree, and fall back to using the common-dir itself as the root otherwise
   (bare repos, unusual layouts). I don't have a concrete bare-repo test case
   in this codebase to validate that fallback against — is a bare-repo
   scenario something you actually hit, or is this heuristic overkill for
   ai-kit's actual usage?
3. **Absolute-path resolution (§3.1)**: I chose `os.path.normpath(os.path.join(work_dir,
   common_dir))` over adding `--path-format=absolute` to the `rev-parse` call
   (which needs git ≥ 2.31) so there's no new git-version floor. Confirm you're
   fine avoiding a version floor here, versus the arguably simpler
   `--path-format=absolute` approach.
4. **Scope boundary (§6)**: I deliberately left `path`'s behavior unchanged for
   the main checkout and for non-worktree subdirectories, reading the user's
   request as specifically about the worktree-redundancy case rather than a
   general "always show project name" rewrite. Confirm that's the intended
   scope and not an under-read of the request.
5. **`project_name` computed-but-unused on the main checkout (§3.2)**: the probe
   now always computes `project_name`, even though `seg_path` only consumes it
   when `is_worktree` is true. This costs nothing extra (parsed from output
   already fetched) but means the field exists "for free" on every
   `GitSnapshot`. Flagging in case a future segment wants to consume it
   directly (e.g. an always-on project-name display independent of worktree
   state) — no action needed now, just noting the field is generically
   available.
