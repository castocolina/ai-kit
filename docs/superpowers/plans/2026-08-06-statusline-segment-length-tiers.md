# Statusline Segment Length Tiers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the `path`, `git_branch`, and `alt_git_worktree` status-line segments a consistent length-tiering model — a preferred "long" form, a "short" fallback, and (for the two non-pinned segments) a "hidden" tier — replacing today's inconsistent flat caps (`path` at 20 cols, `alt_git_worktree` at 20 cols) and `git_branch`'s complete absence of any fixed cap.

**Architecture:** A new shared helper `util_two_state_cap(s, high, low)` returns `s` unchanged if it fits `high` columns, else ellipsis-truncates it to `low` columns — a discrete jump, not a continuous shrink. `path` additionally tries two *structural* variants (home-relative/absolute root path, then `parent/name`) against a fixed 50-column budget via the existing `util_first_fitting` (repurposed here against a fixed cap instead of the live terminal `avail` — the function itself is budget-agnostic); if neither structural variant fits, it falls to the bare name via `util_two_state_cap(name, 30, 20)`, and never hides. `git_branch` and `alt_git_worktree` skip the structural cascade entirely and go straight to `util_two_state_cap(name, 30, 20)`, layered *before* their existing `avail`-based fit/hide logic, which is otherwise unchanged.

**Tech Stack:** Python 3.12 (`.venv`), stdlib `unittest` (this repo's test runner — not pytest; see `Makefile`'s `test:` target).

## Global Constraints

- `PATH_MAX_LEN` moves from `20` to `50` and becomes the fixed budget for
  `path`'s two *structural* variants (full path, `parent/name`) — both the
  in-repo and non-repo cases (per the approved design's §2.1/§2.2 — this is
  a deliberate behavior change to the non-repo case, not an oversight).
- `path`'s final fallback (the bare name, when neither structural variant
  fits `PATH_MAX_LEN`), and `git_branch`/`alt_git_worktree` directly, all use
  `util_two_state_cap(s, 30, 20)`: shown in full up to **30** columns, else
  ellipsis-truncated to **20** — a discrete jump, not a continuous shrink.
- No new git subprocess calls. `root_path` is captured from a value
  `probe_git_worktree_info` already computes and previously discarded.
- `path` must never return `None` or raise (existing "floor"/pinned
  invariant) — every change here preserves that.
- Test runner for this repo: `.venv/bin/python3 -m unittest tests.test_status_line[.Class[.test]] -v` (NOT pytest — it is not a project dependency).

---

### Task 1: Thread `root_path` through the shared git probe

This is the one narrow, explicit exception to the design's §1 "no
`GitSnapshot` field changes" bullet — necessitated by §2.2's requirement
that the repo root's absolute path (not just its basename) be available to
build the home-relative/`parent/name` variants, and now called out as such
in the design doc itself (§1). It is purely a field *addition* carrying an
already-computed value further, not a change to any existing field's
meaning or how it's probed — no new git subprocess call.

**Files:**
- Modify: `tools/status-line.py:251-259` (`GitSnapshot`), `:759-792`
  (`probe_git_worktree_info`), `:795-823` (`probe_worktree_info_cached`),
  `:826-855` (`probe_git_snapshot`)
- Test: `tests/test_status_line.py:53-98` (`_data()` helper), `:933-991`
  (probe tests)

**Interfaces:**
- Produces: `GitSnapshot.root_path: str` (default `""`) — the absolute
  directory path of the main checkout (the same directory `root_name` is
  already the basename of). Consumed by Task 4.
- Produces: `probe_git_worktree_info(work_dir: str) -> tuple[bool, bool, str, str, str]`
  — now `(in_repo, is_worktree, wt_name, root_name, root_path)`, was a 4-tuple.
- Produces: `probe_worktree_info_cached(work_dir, ttl, cache_base) -> tuple[bool, bool, str, str, str]`
  — same 5-tuple shape, threaded through the on-disk TTL cache.

- [ ] **Step 1: Write the failing tests**

Extend `tests/test_status_line.py`. First, `_data()` (lines 53-98) needs a
`root_path` probe default and must thread it into the seeded `GitSnapshot`:

```python
# In _data(), inside probe_defaults (around line 69), add root_path:
    probe_defaults = {
        "branch": "main", "dirty": "modified", "is_worktree": False,
        "in_repo": False, "wt_name": "", "root_name": "", "root_path": "",
        "ago": "5m 0s ago", "effort_auto": False,
        "todo_state": None, "todo_text": None,
        "chat_bytes": 305000, "mem_bytes": 448_790_528,
        "chat_since": None, "chat_compactions": 0,
    }
```

```python
# And thread it into the GitSnapshot construction (around line 81-84):
    ctx.probe_cache["git"] = sl.GitSnapshot(
        in_repo=probe_over["in_repo"], branch=probe_over["branch"],
        dirty=probe_over["dirty"], is_worktree=probe_over["is_worktree"],
        wt_name=probe_over["wt_name"], root_name=probe_over["root_name"],
        root_path=probe_over["root_path"])
```

Then add `root_path` assertions to the existing probe tests (lines 933-991):

```python
    def test_git_snapshot_clean_and_worktree_name(self):
        def fake_run(cmd, **kw):
            class R:
                returncode = 0
                stdout = ("## main\n" if "status" in cmd
                          else "/wt/.git/worktrees/feat-x\n/main/.git\n/path/to/feat-x\n")
            return R()
        env = self._home_env()
        cfg = sl.cfg_default_config()._replace(cache_base=sl.cfg_cache_base(env))
        with mock.patch.object(sl.subprocess, "run", side_effect=fake_run):
            snap = sl.probe_git_snapshot(".", cfg)
            self.assertEqual((snap.branch, snap.dirty), ("main", "clean"))
            self.assertTrue(snap.is_worktree)        # git-dir != git-common-dir
            self.assertTrue(snap.in_repo)
            self.assertEqual(snap.wt_name, "feat-x")  # basename of --show-toplevel
            self.assertEqual(snap.root_name, "main")  # dirname of --git-common-dir
            self.assertEqual(snap.root_path, "/main")  # --git-common-dir's dirname, absolute

    def test_git_snapshot_root_name_non_worktree(self):
        def fake_run(cmd, **kw):
            class R:
                returncode = 0
                stdout = ("## main\n" if "status" in cmd
                          else "/repo/.git\n/repo/.git\n/repo\n")
            return R()
        env = self._home_env()
        cfg = sl.cfg_default_config()._replace(cache_base=sl.cfg_cache_base(env))
        with mock.patch.object(sl.subprocess, "run", side_effect=fake_run):
            snap = sl.probe_git_snapshot(".", cfg)
            self.assertFalse(snap.is_worktree)
            self.assertEqual(snap.root_name, "repo")
            self.assertEqual(snap.root_path, "/repo")

    def test_probe_git_worktree_info_bare_repo_common_dir_guard(self):
        # --git-common-dir doesn't always end in "/.git" — a bare repo's
        # common-dir IS the repo dir itself. root_name/root_path must not
        # blindly take dirname() of a path that isn't "<root>/.git"; they
        # should fall back to the common-dir's own path instead of walking
        # one level too far up (which would report the bare repo's PARENT
        # dir as the name/path).
        def fake_run(cmd, **kw):
            class R:
                returncode = 0
                stdout = "/srv/bare-repo\n/srv/bare-repo\n/srv/bare-repo\n"
            return R()
        with mock.patch.object(sl.subprocess, "run", side_effect=fake_run):
            in_repo, _is_worktree, _name, root_name, root_path = sl.probe_git_worktree_info(".")
        self.assertTrue(in_repo)
        self.assertEqual(root_name, "bare-repo")
        self.assertEqual(root_path, "/srv/bare-repo")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python3 -m unittest tests.test_status_line.TestProcAndGit.test_git_snapshot_clean_and_worktree_name tests.test_status_line.TestProcAndGit.test_git_snapshot_root_name_non_worktree tests.test_status_line.TestProcAndGit.test_probe_git_worktree_info_bare_repo_common_dir_guard -v`

Expected: FAIL — `AttributeError: 'GitSnapshot' object has no attribute 'root_path'` (first two) and `ValueError: not enough values to unpack` (third, since `probe_git_worktree_info` still returns a 4-tuple). These three tests live in `TestProcAndGit` (`tests/test_status_line.py:856`).

- [ ] **Step 3: Implement**

`tools/status-line.py:251-259` — add the field:

```python
class GitSnapshot(NamedTuple):
    """One-shot result from the shared git probe (branch, dirty, worktree)."""

    in_repo: bool
    branch: str
    dirty: str
    is_worktree: bool
    wt_name: str
    root_name: str = ""    # main checkout's dir basename; same across every worktree
    root_path: str = ""    # main checkout's absolute dir path; root_name is its basename
```

`tools/status-line.py:759-792` — return `root_dir` alongside `root_name`:

```python
def probe_git_worktree_info(work_dir: str) -> tuple[bool, bool, str, str, str]:
    """(in_repo, is_worktree, wt_name, root_name, root_path) from ONE `git
    rev-parse`. is_worktree is True when work_dir sits in a linked worktree
    (git-dir != git-common-dir). wt_name is that worktree directory's
    basename (from --show-toplevel), only when in a linked worktree; ""
    otherwise. root_name/root_path are the MAIN checkout's directory
    basename/absolute-path — dirname of --git-common-dir, the one physical
    .git store every worktree of a repo shares, so both stay the same no
    matter which worktree work_dir is in. --git-common-dir normally ends in
    "/.git" and dirname() of that is the repo root; but a bare repo (or an
    unusual layout) can report a --git-common-dir that does NOT end in
    "/.git" — there, dirname() would walk one directory too far up and
    report the repo's PARENT as root_name/root_path. Guard: only take
    dirname() when the common-dir's basename is literally ".git"; otherwise
    the common-dir IS the root, so use it directly.
    --path-format=absolute forces all three rev-parse outputs to be absolute
    so this dirname()/basename() math is correct regardless of the caller's
    cwd, and so root_path is always a usable absolute path. Outside any repo
    -> (False, False, "", "", "")."""
    out = subprocess.run(
        ["git", "-C", work_dir, "rev-parse", "--path-format=absolute",
         "--git-dir", "--git-common-dir", "--show-toplevel"],
        capture_output=True, text=True, check=False).stdout
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False, False, "", "", ""                 # not a git repo
    is_worktree = lines[0] != lines[1]          # git-dir != git-common-dir
    common_dir = lines[1].rstrip("/")
    if os.path.basename(common_dir) == ".git":
        root_dir = os.path.dirname(common_dir)
    else:
        root_dir = common_dir           # bare repo / unusual layout: no ".git" to strip
    root_name = os.path.basename(root_dir)
    top = lines[2] if len(lines) >= 3 else ""
    name = os.path.basename(top.rstrip("/")) if (is_worktree and top) else ""
    return True, is_worktree, name, root_name, root_dir
```

`tools/status-line.py:795-823` — thread the 5th value through the cache:

```python
def probe_worktree_info_cached(work_dir: str, ttl: int, cache_base: str) -> tuple[bool, bool, str, str, str]:
    """probe_git_worktree_info wrapped in an on-disk TTL cache — the worktree rev-parse
    rarely changes, so it is cached ~ttl s keyed by work_dir. The cache is active
    only when ttl > 0 AND a cache_base is resolved: ttl <= 0 forces a fresh
    rev-parse every render, and an empty cache_base means no cache location was
    resolved (a direct/test call with no Config) so we never touch disk — this is
    what keeps such calls from writing a stray `./git/` under the cwd. In
    production cfg_load_config always supplies a real cache_base. Cache I/O is
    best-effort."""
    cached = ttl > 0 and bool(cache_base)
    path = util_git_cache_path(work_dir, cache_base) if cached else ""
    if cached:
        try:
            if time.time() - os.stat(path).st_mtime < ttl:
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
                return (d["in_repo"], d["is_worktree"], d["wt_name"],
                        d.get("root_name", ""), d.get("root_path", ""))
        except (OSError, ValueError, KeyError):
            pass
    info = probe_git_worktree_info(work_dir)
    if cached:                          # caching off (ttl<=0 or no cache_base) -> never write
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"in_repo": info[0], "is_worktree": info[1],
                           "wt_name": info[2], "root_name": info[3],
                           "root_path": info[4]}, f)
        except OSError:
            pass
    return info
```

`tools/status-line.py:826-855` — unpack the 5th value in `probe_git_snapshot`:

```python
    in_repo, is_worktree, wt_name, root_name, root_path = probe_worktree_info_cached(work_dir, ttl, cache_base)
    return GitSnapshot(in_repo, branch, dirty, is_worktree, wt_name, root_name, root_path)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python3 -m unittest tests.test_status_line -v 2>&1 | tail -40`

Expected: PASS for all three tests above, and no new failures anywhere else
in the file (every other `_data(...)` call site is unaffected since
`root_path` defaults to `""`).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(statusline): thread root_path through the shared git probe"
```

---

### Task 2: Add `util_two_state_cap`

**Files:**
- Modify: `tools/status-line.py` (new function, placed immediately after
  `util_first_fitting`, i.e. after line 1365)
- Test: `tests/test_status_line.py` (new `TestTwoStateCap` class, placed
  immediately after `TestFirstFitting`, i.e. after line 264)

**Interfaces:**
- Consumes: `util_visible_width(s: str) -> int` (`tools/status-line.py:1352`),
  `util_trunc_cols(s: str, limit: int) -> str` (`tools/status-line.py:1555`
  — defined later in the file, but Python resolves module-level names at
  call time, not definition time, so this forward reference is safe; every
  other function in this file already relies on the same property).
- Produces: `util_two_state_cap(s: str, high: int, low: int) -> str`.
  Consumed by Tasks 3, 4, 5, and 6.

- [ ] **Step 1: Write the failing test**

```python
class TestTwoStateCap(unittest.TestCase):
    def test_returns_unchanged_when_it_fits_high(self):
        self.assertEqual(sl.util_two_state_cap("proj", 30, 20), "proj")

    def test_boundary_exactly_at_high_is_unchanged(self):
        s = "a" * 30
        self.assertEqual(sl.util_two_state_cap(s, 30, 20), s)

    def test_one_over_high_clips_to_low(self):
        # 31 > high(30) -> util_trunc_cols(s, 20): limit-1=19 reserved for
        # text, appends 19 'a's and stops (19+1>19) -> 19 a's + "…", 20
        # display columns wide, matching low.
        s = "a" * 31
        out = sl.util_two_state_cap(s, 30, 20)
        self.assertEqual(out, "a" * 19 + "…")
        self.assertEqual(sl.util_visible_width(out), 20)

    def test_far_over_high_still_clips_to_exactly_low(self):
        out = sl.util_two_state_cap("a" * 40, 30, 20)
        self.assertEqual(out, "a" * 19 + "…")
        self.assertEqual(sl.util_visible_width(out), 20)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3 -m unittest tests.test_status_line.TestTwoStateCap -v`

Expected: FAIL with `AttributeError: module 'status_line' has no attribute 'util_two_state_cap'`.

- [ ] **Step 3: Implement**

Insert immediately after `util_first_fitting` (after line 1365 in
`tools/status-line.py`):

```python
def util_two_state_cap(s: str, high: int, low: int) -> str:
    """Return s unchanged if it fits `high` columns; otherwise ellipsis-
    truncate it down to `low` columns via util_trunc_cols. A discrete jump,
    not a continuous shrink — the value either shows in full up to a
    comfortable width, or drops straight to a much shorter floor beyond it."""
    return s if util_visible_width(s) <= high else util_trunc_cols(s, low)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3 -m unittest tests.test_status_line.TestTwoStateCap -v`

Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(statusline): add util_two_state_cap, a full-or-clip-to-floor helper"
```

---

### Task 3: `util_display_dir` — structural cascade + 30/20 name floor (non-repo `path` fallback)

**Files:**
- Modify: `tools/status-line.py:89` (`PATH_MAX_LEN`), `:1536-1543`
  (`util_display_dir`)
- Test: `tests/test_status_line.py:550-560` (`TestDisplayDir`)

**Interfaces:**
- Consumes: `util_first_fitting(variants, cap)` (existing,
  `tools/status-line.py:1357`, repurposed here against a fixed cap instead
  of the live `avail`), `util_two_state_cap(s, high, low)` (Task 2).
- Produces: `util_display_dir(work_dir: str, home: str) -> str` — same
  signature, new internals. Consumed today by `seg_path`'s non-repo branch
  (`tools/status-line.py:2206`, unchanged call site).

- [ ] **Step 1: Write the failing tests**

Replace the three tests in `TestDisplayDir` (`tests/test_status_line.py:550-560`)
— the old ones pin the 20-char/2-tier behavior this task deliberately
replaces:

```python
class TestDisplayDir(unittest.TestCase):
    def test_short_path_kept_whole(self):
        self.assertEqual(sl.util_display_dir("/home/u/proj", "/home/u"), "~/proj")

    def test_medium_path_collapses_to_parent_slash_name(self):
        # full (~/workspaces/very-long-organization-name-here/short-repo) is
        # 56 cols, over the 50 structural cap -> falls to parent/name, which
        # is 43 cols, under the cap -> shown.
        work_dir = "/home/u/workspaces/very-long-organization-name-here/short-repo"
        self.assertEqual(sl.util_display_dir(work_dir, "/home/u"),
                          "very-long-organization-name-here/short-repo")

    def test_falls_to_basename_alone_when_both_structural_forms_too_long(self):
        # full is 73 cols and parent/name is 71 cols, both over the 50
        # structural cap -> falls to the basename alone; "short-name" (10
        # cols) fits the 30-col name-floor high threshold, so it's shown
        # unclipped.
        work_dir = "/home/u/" + "a" * 60 + "/short-name"
        self.assertEqual(sl.util_display_dir(work_dir, "/home/u"), "short-name")

    def test_basename_clipped_to_20_when_over_30(self):
        # full is 88 cols and parent/name is 75 cols, both over the 50
        # structural cap; the basename alone ("another-very-long-repository-name",
        # 33 cols) exceeds the 30-col name-floor high threshold, so it's
        # clipped to 20 via util_two_state_cap.
        work_dir = ("/home/u/workspaces/very-long-organization-name-here-extended"
                    "/another-very-long-repository-name")
        self.assertEqual(sl.util_display_dir(work_dir, "/home/u"),
                          "another-very-long-r…")

    def test_no_ellipsis_when_a_variant_fits_whole(self):
        work_dir = "/home/u/workspaces/very-long-organization-name-here/short-repo"
        self.assertNotIn("…", sl.util_display_dir(work_dir, "/home/u"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python3 -m unittest tests.test_status_line.TestDisplayDir -v`

Expected: of the 5 tests in this class, 2 genuinely FAIL and 3 already PASS
unmodified — the current (pre-Step-3) `util_display_dir` is still
`shown = "~"+work_dir[len(home):]` (or `work_dir` verbatim) returned as-is
when `len(shown) <= 20` (the old `PATH_MAX_LEN`), else
`os.path.basename(work_dir.rstrip("/"))`, with no `parent/name` middle
form and no 30/20 name-floor split at all.

- `test_short_path_kept_whole` already PASSES: `"~/proj"` is 6 cols, under
  both the old 20-col cap and the new 50-col structural cap, so it comes
  back unchanged either way — this fixture doesn't distinguish old from
  new behavior.
- `test_medium_path_collapses_to_parent_slash_name` genuinely FAILS: the
  old code collapses straight to the basename `"short-repo"` once the
  home-relative form exceeds the old 20-char threshold; it never produces
  the `"very-long-organization-name-here/short-repo"` `parent/name` form
  the test expects.
- `test_falls_to_basename_alone_when_both_structural_forms_too_long`
  already PASSES: the pre-Task-3 fallback is
  `os.path.basename(work_dir.rstrip("/"))`, taken whenever the
  home-relative `shown` exceeds the old 20-char cap. For this fixture
  (`"/home/u/" + "a"*60 + "/short-name"`) that basename is `"short-name"`
  — byte-for-byte the same value the new name-floor logic produces (10
  cols comfortably fits the 30-col high threshold, so it's returned
  unclipped). The match is coincidental — the old code has no 30/20
  tiering at all — it just means this particular fixture doesn't
  distinguish old from new behavior at this checkpoint.
- `test_basename_clipped_to_20_when_over_30` genuinely FAILS: the old
  fallback returns the basename verbatim regardless of its length (there
  is no 30/20 split to clip it), so the full 33-char
  `"another-very-long-repository-name"` comes back instead of the
  expected 20-col `"another-very-long-r…"`.
- `test_no_ellipsis_when_a_variant_fits_whole` already PASSES: the
  pre-Step-3 fallback for this fixture is also `"short-repo"` (same
  basename math as above) — no ellipsis either before or after Step 3, so
  this loose `assertNotIn("…", ...)` assertion can't tell old from new
  behavior here.

- [ ] **Step 3: Implement**

`tools/status-line.py:89`:

```python
PATH_MAX_LEN = 50      # fixed budget for path's two structural variants (full path, parent/name)
```

`tools/status-line.py:1536-1543`:

```python
def util_display_dir(work_dir: str, home: str) -> str:
    """Return work_dir tiered: try the full ~-relative (or absolute) path
    and parent/basename against the PATH_MAX_LEN structural budget (richest
    first); if neither fits, fall to the basename alone via
    util_two_state_cap(name, 30, 20)."""
    stripped = work_dir.rstrip("/")
    full = ("~" + work_dir[len(home):]) if (home and work_dir.startswith(home)) else work_dir
    parent = os.path.basename(os.path.dirname(stripped))
    name = os.path.basename(stripped) or work_dir
    structural = util_first_fitting([full, f"{parent}/{name}"], PATH_MAX_LEN)
    return structural if structural is not None else util_two_state_cap(name, 30, 20)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python3 -m unittest tests.test_status_line.TestDisplayDir -v`

Expected: PASS, 5 tests. Also run the full suite to confirm no other test
relied on the old 20-char threshold:

Run: `.venv/bin/python3 -m unittest tests.test_status_line -v 2>&1 | tail -60`

Expected: only pre-existing, unrelated failures (if any) — no new ones. In
particular confirm `test_pinned_path_present_even_when_too_narrow` and
`test_falls_back_to_cwd_outside_a_repo` still pass (both use short paths
that fit the full-path structural form either way).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(statusline): tier util_display_dir (50-cap structural, 30/20 name floor)"
```

---

### Task 4: `seg_path` (in-repo) — structural cascade + 30/20 name floor via `root_path`/`root_name`

**Files:**
- Modify: `tools/status-line.py:2201-2207` (`seg_path`)
- Test: `tests/test_status_line.py:1280-1321` (`TestSegPathProjectRoot`)

**Interfaces:**
- Consumes: `GitSnapshot.root_path`/`.root_name` (Task 1),
  `util_first_fitting` (existing, fixed-cap use), `util_two_state_cap`
  (Task 2).
- Produces: `seg_path(ctx, avail, theme) -> str | None` — same signature,
  still never returns `None` (floor invariant unchanged).

- [ ] **Step 1: Write the failing tests**

Replace `test_truncates_long_root_name` and add six new tests to
`TestSegPathProjectRoot` (`tests/test_status_line.py:1280-1321`); the other
existing tests in this class (`test_shows_root_name_inside_a_repo`,
`test_ignores_cwd_depth_inside_a_repo`,
`test_non_worktree_short_subdir_shows_root_not_old_cwd_display`,
`test_falls_back_to_cwd_outside_a_repo`) are unaffected and stay as-is:

```python
    def test_truncates_long_root_name_when_root_path_unknown(self):
        # root_path unset (as every GitSnapshot built before Task 1 shipped,
        # or cache read from a pre-Task-1 disk cache) -> no structural
        # cascade is attempted; falls straight to the name floor
        # (util_two_state_cap(root_name, 30, 20)), which clips a 60-col name.
        long_name = "a" * 60
        ctx = _data(in_repo=True, root_name=long_name)
        out = sl.seg_path(ctx, 80, THEME)
        self.assertIn("…", out)
        self.assertNotIn(long_name, out)

    def test_shows_full_home_relative_root_path_when_short(self):
        ctx = _data(in_repo=True, root_name="proj", root_path="/home/u/proj", home="/home/u")
        out = sl.seg_path(ctx, 80, THEME)
        self.assertIn("~/proj", strip(out))

    def test_falls_to_parent_slash_name_when_full_path_too_long(self):
        # full (~/workspaces/very-long-organization-name-here/short-repo) is
        # 56 cols, over the 50 structural cap -> falls to parent/name (43
        # cols, fits).
        root_path = "/home/u/workspaces/very-long-organization-name-here/short-repo"
        ctx = _data(in_repo=True, root_name="short-repo", root_path=root_path, home="/home/u")
        out = sl.seg_path(ctx, 80, THEME)
        self.assertIn("very-long-organization-name-here/short-repo", strip(out))
        self.assertNotIn("~/workspaces", strip(out))

    def test_falls_to_root_name_unclipped_when_both_structural_forms_too_long(self):
        # full (73 cols) and parent/name (71 cols) both exceed the 50
        # structural cap; root_name alone ("short-name", 10 cols) fits the
        # 30-col name-floor high threshold, so it's shown unclipped.
        root_path = "/home/u/" + "a" * 60 + "/short-name"
        ctx = _data(in_repo=True, root_name="short-name", root_path=root_path, home="/home/u")
        out = sl.seg_path(ctx, 80, THEME)
        self.assertIn("short-name", strip(out))
        self.assertNotIn("…", strip(out))

    def test_falls_to_root_name_clipped_when_over_30(self):
        # full (88 cols) and parent/name (75 cols) both exceed the 50
        # structural cap; root_name alone ("another-very-long-repository-name",
        # 33 cols) exceeds the 30-col name-floor high threshold, so it's
        # clipped to 20.
        root_path = ("/home/u/workspaces/very-long-organization-name-here-extended"
                     "/another-very-long-repository-name")
        ctx = _data(in_repo=True, root_name="another-very-long-repository-name",
                    root_path=root_path, home="/home/u")
        out = sl.seg_path(ctx, 80, THEME)
        self.assertIn("another-very-long-r…", strip(out))
        self.assertNotIn("very-long-organization-name-here-extended/", strip(out))

    def test_shows_raw_absolute_root_path_when_not_under_home(self):
        # root_path doesn't start with ctx.home -> the home-relative "~"
        # substitution is skipped and the raw absolute root_path is used
        # verbatim as the first structural variant (design doc §3 edge case:
        # "Repo root not under ctx.home" falls back to the raw absolute path).
        ctx = _data(in_repo=True, root_name="proj", root_path="/mnt/other/proj", home="/home/u")
        out = sl.seg_path(ctx, 80, THEME)
        self.assertIn("/mnt/other/proj", strip(out))
        self.assertNotIn("~", strip(out))

    def test_falls_through_to_display_dir_when_root_name_empty(self):
        # in_repo=True but root_name=="" fails the `if snap.in_repo and
        # snap.root_name:` guard (pre-existing, unchanged by this plan) -> the
        # non-repo util_display_dir branch runs instead, exactly as it did
        # before this plan touched seg_path.
        ctx = _data(in_repo=True, root_name="", root_path="/home/u/proj",
                    work_dir="/home/u/proj", home="/home/u")
        out = sl.seg_path(ctx, 80, THEME)
        self.assertEqual(strip(out), sl.util_display_dir("/home/u/proj", "/home/u"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python3 -m unittest tests.test_status_line.TestSegPathProjectRoot -v`

Expected: of the 7 tests written in this step, 4 genuinely FAIL and 3
already PASS unmodified — the pre-Step-3 `seg_path` is still
`shown = util_trunc_cols(snap.root_name, PATH_MAX_LEN)` (with
`PATH_MAX_LEN` already 50 from Task 3) whenever `snap.in_repo and
snap.root_name`, and never reads `snap.root_path` at all.

- `test_truncates_long_root_name_when_root_path_unknown` (the renamed
  test) already PASSES: with `long_name = "a"*60` and `root_path` unset,
  both the pre-Task-4 code (`util_trunc_cols(snap.root_name, 50)`) and the
  post-Task-4 name-floor branch (`util_two_state_cap(long_name, 30, 20)`)
  produce a truncated string containing `"…"` and not containing the full
  60-char name. The test's loose assertions (`assertIn("…", out)`,
  `assertNotIn(long_name, out)`) can't tell the two implementations apart,
  so it passes at every checkpoint.
- `test_shows_full_home_relative_root_path_when_short` genuinely FAILS:
  the old code ignores `root_path` and shows the bare `root_name`
  (`"proj"`), which does not contain `"~/proj"`.
- `test_falls_to_parent_slash_name_when_full_path_too_long` genuinely
  FAILS: the old code shows `root_name` alone (`"short-repo"`), never the
  `parent/name` structural form.
- `test_falls_to_root_name_unclipped_when_both_structural_forms_too_long`
  already PASSES: `root_name="short-name"` (10 cols) is untouched by
  `util_trunc_cols(name, 50)` (10≤50) — the old output is exactly
  `"short-name"`, identical to the post-Step-3
  `util_two_state_cap(name, 30, 20)` output (10≤30, also unchanged). Both
  loose assertions (`assertIn("short-name", ...)`,
  `assertNotIn("…", ...)`) hold either way — this is the same
  coincidental-match class as the previous test, just reached via a
  different code path (name-floor vs. root-path-unknown fallback).
- `test_falls_to_root_name_clipped_when_over_30` genuinely FAILS: the old
  code shows the full 33-char `root_name` untruncated (33 ≤ 50, the old
  `PATH_MAX_LEN`), never clipping it to the 20-col
  `"another-very-long-r…"` the test expects.
- `test_shows_raw_absolute_root_path_when_not_under_home` genuinely FAILS:
  the old code ignores `root_path` and shows the bare `root_name`
  (`"proj"`), which does not contain `"/mnt/other/proj"`.
- `test_falls_through_to_display_dir_when_root_name_empty` already
  PASSES — not coincidentally, but because `root_name=""` fails the
  pre-existing `if snap.in_repo and snap.root_name:` guard both before and
  after this task, so the non-repo `util_display_dir` fallback runs
  identically either way; this task doesn't touch that branch at all.

- [ ] **Step 3: Implement**

`tools/status-line.py:2201-2207`:

```python
def seg_path(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    snap = probe_git_for(ctx)
    if snap.in_repo and snap.root_name:
        if snap.root_path:
            root = snap.root_path.rstrip("/")
            full = ("~" + root[len(ctx.home):]) if (ctx.home and root.startswith(ctx.home)) else root
            parent = os.path.basename(os.path.dirname(root))
            structural = util_first_fitting([full, f"{parent}/{snap.root_name}"], PATH_MAX_LEN)
            shown = structural if structural is not None else util_two_state_cap(snap.root_name, 30, 20)
        else:
            shown = util_two_state_cap(snap.root_name, 30, 20)   # root_path unknown -> name-only floor
    else:
        shown = util_display_dir(ctx.work_dir, ctx.home)
    return f"{theme.c('BLUE')}{shown}{RESET}"  # floor
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python3 -m unittest tests.test_status_line.TestSegPathProjectRoot -v`

Expected: PASS, 11 tests (4 existing unchanged + 1 renamed
`test_truncates_long_root_name` → `test_truncates_long_root_name_when_root_path_unknown`
+ 6 new).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(statusline): tier seg_path's in-repo form via root_path"
```

---

### Task 5: `seg_git_branch` — 30/20 two-state cap

**Files:**
- Modify: `tools/status-line.py:2210-2219` (`seg_git_branch`)
- Test: `tests/test_status_line.py:337-355` (`TestCooperativeBuilders`,
  branch tests)

**Interfaces:**
- Consumes: `util_two_state_cap(s, high, low)` (Task 2) — branch/worktree
  use this directly, per the design's §2.3/§2.4; there's no structural
  cascade here (branches have no `parent/name` concept), just "full or
  truncated."
- Produces: `seg_git_branch(ctx, avail, theme) -> str | None` — same
  signature; still returns `None` when nothing fits `avail` (unchanged
  self-hide behavior).

- [ ] **Step 1: Write the failing tests**

Add to `TestCooperativeBuilders` (`tests/test_status_line.py`, after the
existing branch tests at line 355):

```python
    def test_branch_full_up_to_30_cols(self):
        branch = "feature/" + "x" * 20   # 28 cols, under the 30 cap
        out = sl.seg_git_branch(_data(branch=branch), 100, THEME)
        self.assertIn(branch, strip(out))
        self.assertNotIn("…", out)

    def test_branch_over_30_truncates_to_20(self):
        branch = "feature/" + "x" * 50   # 58 cols, over the 30 cap
        out = sl.seg_git_branch(_data(branch=branch), 100, THEME)
        expected = "feature/" + "x" * 11 + "…"   # util_trunc_cols(branch, 20)
        self.assertIn(expected, strip(out))
        self.assertEqual(sl.util_visible_width(expected), 20)

    def test_branch_hides_when_even_20col_form_does_not_fit_avail(self):
        branch = "feature/" + "x" * 50
        self.assertIsNone(sl.seg_git_branch(_data(branch=branch), 5, THEME))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python3 -m unittest tests.test_status_line.TestCooperativeBuilders -v`

Expected: of the 3 tests written in this step, 1 genuinely FAILS and 2
already PASS unmodified — the pre-Step-3 `seg_git_branch` has no length
cap at all; it feeds the raw `branch` straight into
`util_first_fitting(...avail)`.

- `test_branch_full_up_to_30_cols` already PASSES: with no cap, the
  28-col branch shows in full whenever it fits `avail=100` (it does), and
  no ellipsis is ever introduced — both `assertIn(branch, ...)` and
  `assertNotIn("…", ...)` hold identically before and after Step 3, since
  28 cols also fits under the new 30-col high threshold.
- `test_branch_over_30_truncates_to_20` genuinely FAILS: with no cap, the
  full 58-char branch shows as-is (it fits `avail=100`), so the expected
  20-col truncated form `"feature/" + "x"*11 + "…"` never appears.
- `test_branch_hides_when_even_20col_form_does_not_fit_avail` already
  PASSES: at `avail=5`, neither `util_first_fitting` variant — icon+branch
  or bare branch, whether capped or not — fits, so it already returns
  `None` regardless of any length-cap logic Step 3 adds.

- [ ] **Step 3: Implement**

`tools/status-line.py:2210-2219`:

```python
def seg_git_branch(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    branch = probe_git_for(ctx).branch
    if not branch:
        return None
    # git_branch carries its own STATIC 🌿 icon. It does NOT encode worktree state
    # (no 🌳) — that moved to the dedicated `alt_git_worktree` ⎇ segment (FR-7.2);
    # the leaf glyph here is purely "this is the branch". Falls back to the bare
    # name when too narrow for the icon, so the branch never drops just for it.
    shown = util_two_state_cap(branch, 30, 20)
    return util_first_fitting([f"{theme.c('GREY')}[{util_icon('🌿', shown)}]{RESET}",
                           f"{theme.c('GREY')}[{shown}]{RESET}"], avail)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python3 -m unittest tests.test_status_line.TestCooperativeBuilders -v`

Expected: PASS, all branch tests (existing + 3 new).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(statusline): cap git_branch at 30, truncate to 20 when over"
```

---

### Task 6: `seg_alt_git_worktree` — 30/20 two-state cap

**Files:**
- Modify: `tools/status-line.py:2227-2239` (`seg_alt_git_worktree`)
- Test: `tests/test_status_line.py:357-378` (`TestCooperativeBuilders`,
  worktree tests)

**Interfaces:**
- Consumes: `util_two_state_cap(s, high, low)` (Task 2).
- Produces: `seg_alt_git_worktree(ctx, avail, theme) -> str | None` — same
  signature and hide-outside-repo / struck-placeholder-on-main-checkout
  behavior, unchanged.

- [ ] **Step 1: Write the failing tests**

Replace `test_worktree_name_truncated_to_20_cols`
(`tests/test_status_line.py:373-378`) — its `"a" * 40` fixture is only 40
cols, which fits fine under the new 50-cap and so no longer exercises
truncation at all — with the new three-case set, mirroring Task 5's
`test_branch_hides_when_even_20col_form_does_not_fit_avail`:

```python
    def test_worktree_name_full_up_to_30_cols(self):
        name = "a" * 28
        out = sl.seg_alt_git_worktree(
            _data(in_repo=True, is_worktree=True, wt_name=name), 100, THEME)
        self.assertIn(name, strip(out))
        self.assertNotIn("…", out)

    def test_worktree_name_over_30_truncates_to_20(self):
        name = "a" * 60
        out = sl.seg_alt_git_worktree(
            _data(in_repo=True, is_worktree=True, wt_name=name), 100, THEME)
        expected = "a" * 19 + "…"   # util_trunc_cols(name, 20)
        self.assertIn(expected, strip(out))
        self.assertEqual(sl.util_visible_width(expected), 20)

    def test_worktree_name_hides_when_even_20col_form_does_not_fit_avail(self):
        name = "a" * 60
        self.assertIsNone(sl.seg_alt_git_worktree(
            _data(in_repo=True, is_worktree=True, wt_name=name), 5, THEME))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python3 -m unittest tests.test_status_line.TestCooperativeBuilders -v`

Expected: FAIL — `test_worktree_name_full_up_to_30_cols` fails because
today's flat `util_trunc_cols(name, 20)` truncates a 28-char name (since
28>20) to a 20-col ellipsis-bearing form, while the new rule must show it
in full (28≤30). `test_worktree_name_over_30_truncates_to_20` already
PASSES unmodified — the current flat `util_trunc_cols(name, 20)` on a
60-char name already happens to produce the exact same 20-col clipped
shape (`"a"*19 + "…"`) the new test expects, by coincidence: the old code
has no 30/20 tiering, but a name that's over both the old flat cap and the
new 30-col high threshold lands on the same 20-col floor either way.
`test_worktree_name_hides_when_even_20col_form_does_not_fit_avail`
already PASSES unmodified — `avail=5` is too narrow for the `⎇ ` icon plus
even the current flat 20-col form, so `util_first_fitting` already returns
`None` regardless of which cap produced the candidate string; this test
exists to pin that hide-on-no-fit behavior so Step 3 can't regress it,
exactly as Task 5's mirrored test does for `seg_git_branch`.

- [ ] **Step 3: Implement**

`tools/status-line.py:2227-2239`:

```python
def seg_alt_git_worktree(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    # alt_git_worktree names the ACTIVE linked worktree the session sits in —
    # never a list. Mirrors git_dirty's "absence is the neutral state": hidden
    # outside a repo. On the main checkout it shows a dimmed, struck `⎇ wt`
    # placeholder — GREY (not just strikethrough) so it stays distinct from the
    # cyan active form even on terminals that don't render SGR-9.
    snap = probe_git_for(ctx)
    if not snap.in_repo:
        return None
    if not snap.is_worktree:
        return util_first_fitting([f"{theme.c('GREY')}\033[9m⎇ wt{RESET}"], avail)
    name = util_two_state_cap(snap.wt_name or "", 30, 20)
    return util_first_fitting([f"{theme.c('CYAN')}⎇ {name}{RESET}"], avail)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python3 -m unittest tests.test_status_line.TestCooperativeBuilders -v`

Expected: PASS, all worktree tests (existing + 3 new).

Then run the full suite once more to confirm the whole file is green end to
end:

Run: `.venv/bin/python3 -m unittest tests.test_status_line -v 2>&1 | tail -20`

Expected: `OK` (or exactly the same pre-existing, unrelated
failures/errors the repo already had before this plan — no new ones).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(statusline): cap alt_git_worktree at 30, truncate to 20 when over"
```
