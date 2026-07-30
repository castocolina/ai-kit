# Context Tools Worktree UX Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the `path` statusline segment always show the project/repo root name — in every git-repo session, not only inside a worktree — so it never duplicates the `alt_git_worktree` ("worktree"/"gittree") segment's worktree-specific name; and move the installer's pre-wizard raw-terminal prompts/detection (stale-link prune, predecessor-link repoint, status-line state) so they run live, inside the Textual wizard, instead of as CLI output printed before the TUI ever mounts.

**Architecture:** `path` is redefined to always render the git *common-dir*'s parent basename (the main checkout's folder name) instead of the literal cwd, for every git-repo session — main checkout or any linked worktree, at any cwd depth — reusing the single shared git probe (`probe_git_for`) that `alt_git_worktree` already uses. This is a deliberately broader scope than "inside a worktree only": a session at `~/proj/tools/` in the main checkout now also shows `proj`, not the old tilde-collapsed `~/proj/tools`. Non-repo sessions are unaffected and keep today's `util_display_dir` behavior. The two functions that currently print raw ANSI banners and block on `input()` before `launch_wizard()` is even called (`prune_stale`, `adopt_predecessor_links`) are split into pure "detect candidates" + "apply decision" halves; detection feeds a new `WizardContext.housekeeping` gate rendered inside Step 0 (mirroring the existing status-line adopt gate already rendered inside Step 1/Arrange), and the apply half runs from an injected callable the wizard invokes once the gate is answered — immediately and unconditionally, exactly like today, just from inside the TUI. `detect_statusline()` becomes a callable field on `WizardContext` instead of a frozen dict, called fresh every time the gate needs it (mirroring how `status-line.py` itself always re-probes rather than caching git state indefinitely).

**Tech Stack:** Python 3, Textual (TUI), `unittest` (stdlib), `git` CLI (subprocess).

## Correction to originating PRD

`docs/prds/context-tools-worktree-ux-fixes-v1.0-prd.md` was partly researched while the session was still inside the `worktree-context-tools-manager-plan1` git worktree, which has an unmerged `tools/context_tools.py` (rtk/codegraph/grapify/gitnexus catalog detection) not present on `main`. That module, `_build_context_tools_rows()`, and `WizardContext.context_tools` **do not exist on `main`** — verified by direct grep after returning to the project root. This plan targets `main` as it actually is: the "component/context-tools catalog probing" bullet from the PRD is dropped from scope. The PRD's other claims (`adopt_predecessor_links` at `tools/setup.py:1126`, `detect_statusline` at `tools/setup.py:1352`, `_build_wizard_context` calling it synchronously before `WizardApp` is constructed) were verified directly against `main` and are accurate.

## Correction to / supersession of the sibling design spec

Task 1 knowingly supersedes `docs/superpowers/specs/2026-07-28-path-segment-worktree-name-design.md` on two points, both confirmed with the user outside this plan's original research pass. That spec's own Status line now records the supersession in place; this is the plan-side pointer back to it:

- **Scope boundary**: the design spec's §3.3/§6 gate the project-name substitution on `is_worktree` and explicitly reject "always show project name" as scope creep. This plan implements the broader "always, in every git-repo session" behavior instead (see Goal/Architecture above) — the user was asked directly and chose the broader scope.
- **`--git-common-dir` → root resolution**: the design spec's Open Question 3 weighs `--path-format=absolute` (git ≥2.31 version floor) against a version-floor-free `os.path.normpath` approach. This plan's Task 1 uses `--path-format=absolute` — a deliberate, confirmed choice accepting the git ≥2.31 floor, not an oversight.

The field is named `root_name` here (not the design spec's proposed `project_name`); no other behavior from that spec carries over into this plan.

## Global Constraints

- `tools/wizard_app.py` imports nothing from `tools/setup.py` or `tools/context_tools.py` — every fact/behavior it needs arrives through the injected `WizardContext` (this is the locked A.4 seam per the file's own module docstring). Do not violate it.
- Predecessor-link and stale-link decisions apply **immediately and unconditionally** once answered in the gate — not deferred to the wizard's Review→Confirm `commit`. (User-confirmed requirement.)
- Statusline/detection state read by the wizard must be **live** — re-computed on each read via an injected callable, not a value frozen once before the UI exists. (User-confirmed requirement, "similar to how `status-line.py`" re-probes.)
- Every existing test in `tests/test_status_line.py`, `tests/test_setup.py`, and `tests/test_wizard_app.py` must keep passing unmodified except where a task explicitly calls out the touch.
- `cmd_install()` is interactive-only and fail-closed (`require_tty` guarantees a real tty before it is ever reached) — no headless behavior change is in scope.

---

### Task 1: `path` segment shows the project root, not the raw working directory

**Files:**
- Modify: `tools/status-line.py:251-258` (`GitSnapshot`), `tools/status-line.py:758-773` (`probe_git_worktree_info`), `tools/status-line.py:776-803` (`probe_worktree_info_cached`), `tools/status-line.py:806-835` (`probe_git_snapshot`), `tools/status-line.py:2181-2182` (`seg_path`), `tools/status-line.py:89` (`PATH_MAX_LEN` comment), `tools/statusline.toml.sample:27` (stale doc comment)
- Test: `tests/test_status_line.py:53-98` (`_data()` helper), `tests/test_status_line.py:933-947` (`test_git_snapshot_clean_and_worktree_name`), new tests near there and near `tests/test_status_line.py:1230`

**Interfaces:**
- Consumes: `probe_git_for(ctx) -> GitSnapshot` (existing, `tools/status-line.py:1106-1109`), `util_trunc_cols(s, limit) -> str` (existing, `tools/status-line.py:1535`), `util_display_dir(work_dir, home) -> str` (existing, unchanged).
- Produces: `GitSnapshot.root_name: str` — the main checkout's directory basename, stable regardless of which worktree the probe ran in; `""` outside any git repo. `seg_path(ctx, avail, theme)` now renders `root_name` when `ctx` is inside a repo, falling back to today's `util_display_dir` behavior otherwise. No other task depends on this one.

- [x] **Step 1: Write the failing tests**

In `tests/test_status_line.py`, update `_data()` (lines 53-98) to seed and route a `root_name` probe field:

```python
    probe_defaults = {
        "branch": "main", "dirty": "modified", "is_worktree": False,
        "in_repo": False, "wt_name": "", "root_name": "",
        "ago": "5m 0s ago", "effort_auto": False,
        "todo_state": None, "todo_text": None,
        "chat_bytes": 305000, "mem_bytes": 448_790_528,
        "chat_since": None, "chat_compactions": 0,
    }
```

```python
    ctx.probe_cache["git"] = sl.GitSnapshot(
        in_repo=probe_over["in_repo"], branch=probe_over["branch"],
        dirty=probe_over["dirty"], is_worktree=probe_over["is_worktree"],
        wt_name=probe_over["wt_name"], root_name=probe_over["root_name"])
```

Extend `test_git_snapshot_clean_and_worktree_name` (line 933) with a `root_name` assertion (the fixture's git-common-dir line, `/main/.git`, already implies root `main`):

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
```

Add a new test directly after it for the non-worktree case:

```python
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

    def test_probe_git_worktree_info_requests_absolute_paths(self):
        # --git-common-dir must be absolute or root_name's dirname() math breaks.
        seen = []
        def fake_run(cmd, **kw):
            seen.append(cmd)
            class R:
                returncode = 0
                stdout = "/repo/.git\n/repo/.git\n/repo\n"
            return R()
        with mock.patch.object(sl.subprocess, "run", side_effect=fake_run):
            sl.probe_git_worktree_info(".")
        self.assertIn("--path-format=absolute", seen[0])

    def test_probe_git_worktree_info_bare_repo_common_dir_guard(self):
        # --git-common-dir doesn't always end in "/.git" — a bare repo's
        # common-dir IS the repo dir itself. root_name must not blindly take
        # dirname() of a path that isn't "<root>/.git"; it should fall back
        # to the common-dir's own basename instead of walking one level too
        # far up (which would report the bare repo's PARENT dir as the name).
        def fake_run(cmd, **kw):
            class R:
                returncode = 0
                stdout = "/srv/bare-repo\n/srv/bare-repo\n/srv/bare-repo\n"
            return R()
        with mock.patch.object(sl.subprocess, "run", side_effect=fake_run):
            in_repo, _is_worktree, _name, root_name = sl.probe_git_worktree_info(".")
        self.assertTrue(in_repo)
        self.assertEqual(root_name, "bare-repo")
```

Near `test_path_emits_true_blue_not_bold_ansi` (line 1230), add `seg_path` behavior tests:

```python
class TestSegPathProjectRoot(unittest.TestCase):
    def test_shows_root_name_inside_a_repo(self):
        ctx = _data(in_repo=True, root_name="ai-kit",
                    work_dir="/home/u/proj/.claude/worktrees/feat-x")
        out = sl.seg_path(ctx, 80, THEME)
        self.assertIn("ai-kit", out)
        self.assertNotIn("feat-x", out)

    def test_ignores_cwd_depth_inside_a_repo(self):
        ctx = _data(in_repo=True, root_name="ai-kit",
                    work_dir="/home/u/proj/very/deeply/nested/subdir")
        out = sl.seg_path(ctx, 80, THEME)
        self.assertIn("ai-kit", out)

    def test_non_worktree_short_subdir_shows_root_not_old_cwd_display(self):
        # Regression pin for the deliberately widened scope (confirmed with the
        # user; see the plan's "Correction to / supersession of the sibling
        # design spec" section): a short subdirectory of the MAIN checkout
        # (not a worktree, and under PATH_MAX_LEN so the old code path never
        # truncated it) used to render via util_display_dir as "~/proj/tools".
        # It must now render the project root name instead, proving the
        # substitution applies to every git-repo session, not only worktrees.
        work_dir = "/home/u/proj/tools"
        home = "/home/u"
        old_display = sl.util_display_dir(work_dir, home)
        self.assertEqual(old_display, "~/proj/tools")  # sanity: old behavior would show this
        ctx = _data(in_repo=True, root_name="proj", work_dir=work_dir, home=home)
        out = sl.seg_path(ctx, 80, THEME)
        self.assertIn("proj", out)
        self.assertNotIn(old_display, out)

    def test_truncates_long_root_name(self):
        long_name = "a" * 30
        ctx = _data(in_repo=True, root_name=long_name)
        out = sl.seg_path(ctx, 80, THEME)
        self.assertIn("…", out)
        self.assertNotIn(long_name, out)

    def test_falls_back_to_cwd_outside_a_repo(self):
        ctx = _data(in_repo=False, work_dir="/home/u/scratch", home="/home/u")
        out = sl.seg_path(ctx, 80, THEME)
        self.assertIn(sl.util_display_dir("/home/u/scratch", "/home/u"), out)
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run python3 -m pytest tests/test_status_line.py -k "root_name or SegPathProjectRoot or absolute_paths or common_dir_guard" -v`
Expected: FAIL — `GitSnapshot() got an unexpected keyword argument 'root_name'` / `AttributeError: 'GitSnapshot' object has no attribute 'root_name'`.

- [x] **Step 3: Implement**

In `tools/status-line.py`, update the `GitSnapshot` NamedTuple (lines 251-258):

```python
class GitSnapshot(NamedTuple):
    """One-shot result from the shared git probe (branch, dirty, worktree)."""

    in_repo: bool
    branch: str
    dirty: str
    is_worktree: bool
    wt_name: str
    root_name: str = ""    # main checkout's dir basename; same across every worktree
```

Replace `probe_git_worktree_info` (lines 758-773):

```python
def probe_git_worktree_info(work_dir: str) -> tuple[bool, bool, str, str]:
    """(in_repo, is_worktree, wt_name, root_name) from ONE `git rev-parse`.
    is_worktree is True when work_dir sits in a linked worktree (git-dir !=
    git-common-dir). wt_name is that worktree directory's basename (from
    --show-toplevel), only when in a linked worktree; "" otherwise. root_name
    is the MAIN checkout's directory basename — dirname of --git-common-dir,
    the one physical .git store every worktree of a repo shares, so it stays
    the same no matter which worktree work_dir is in. --git-common-dir
    normally ends in "/.git" and dirname() of that is the repo root; but a
    bare repo (or an unusual layout) can report a --git-common-dir that does
    NOT end in "/.git" — there, dirname() would walk one directory too far up
    and report the repo's PARENT as root_name. Guard: only take dirname()
    when the common-dir's basename is literally ".git"; otherwise the
    common-dir IS the root, so use its own basename directly.
    --path-format=absolute forces all three rev-parse outputs to be absolute
    so this dirname()/basename() math is correct regardless of the caller's
    cwd. Outside any repo → (False, False, "", "")."""
    out = subprocess.run(
        ["git", "-C", work_dir, "rev-parse", "--path-format=absolute",
         "--git-dir", "--git-common-dir", "--show-toplevel"],
        capture_output=True, text=True, check=False).stdout
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False, False, "", ""                 # not a git repo
    is_worktree = lines[0] != lines[1]          # git-dir != git-common-dir
    common_dir = lines[1].rstrip("/")
    if os.path.basename(common_dir) == ".git":
        root_dir = os.path.dirname(common_dir)
    else:
        root_dir = common_dir           # bare repo / unusual layout: no ".git" to strip
    root_name = os.path.basename(root_dir)
    top = lines[2] if len(lines) >= 3 else ""
    name = os.path.basename(top.rstrip("/")) if (is_worktree and top) else ""
    return True, is_worktree, name, root_name
```

Update `probe_worktree_info_cached` (lines 776-803) to thread the 4th value through, with a `.get()` fallback so a stale on-disk cache file written by the OLD 3-field code doesn't crash:

```python
def probe_worktree_info_cached(work_dir: str, ttl: int, cache_base: str) -> tuple[bool, bool, str, str]:
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
                return d["in_repo"], d["is_worktree"], d["wt_name"], d.get("root_name", "")
        except (OSError, ValueError, KeyError):
            pass
    info = probe_git_worktree_info(work_dir)
    if cached:                          # caching off (ttl<=0 or no cache_base) -> never write
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"in_repo": info[0], "is_worktree": info[1],
                           "wt_name": info[2], "root_name": info[3]}, f)
        except OSError:
            pass
    return info
```

Update `probe_git_snapshot` (lines 806-835) — only the unpacking/return line changes:

```python
    in_repo, is_worktree, wt_name, root_name = probe_worktree_info_cached(work_dir, ttl, cache_base)
    return GitSnapshot(in_repo, branch, dirty, is_worktree, wt_name, root_name)
```

Replace `seg_path` (lines 2181-2182):

```python
def seg_path(ctx: "Context", avail: int, theme: "Theme") -> str | None:
    snap = probe_git_for(ctx)
    if snap.in_repo and snap.root_name:
        shown = util_trunc_cols(snap.root_name, PATH_MAX_LEN)
    else:
        shown = util_display_dir(ctx.work_dir, ctx.home)
    return f"{theme.c('BLUE')}{shown}{RESET}"  # floor
```

Update the `PATH_MAX_LEN` comment (line 89) since it now also bounds the project-root name, not only the tilde-collapsed cwd:

```python
PATH_MAX_LEN = 20       # ~-collapsed path or project-root name longer than this collapses/truncates
```

In `tools/statusline.toml.sample`, update the now-stale `path` doc comment (line 27) — it still describes the old "working directory" behavior:

```
# path = true                # 📂 project root name (main checkout, even inside a worktree)   (pinned)
```

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run python3 -m pytest tests/test_status_line.py -v`
Expected: PASS — full file green, including every pre-existing test (the `root_name: str = ""` default keeps every positional 5-arg `GitSnapshot(...)` construction elsewhere in the suite working unmodified).

- [x] **Step 5: Commit**

```bash
git add tools/status-line.py tools/statusline.toml.sample tests/test_status_line.py
git commit -m "fix(statusline): path segment shows project root, not raw cwd

Inside a worktree, path used to collapse to the same basename the
alt_git_worktree segment already shows. path now always renders the
main checkout's name (dirname of git's common-dir), which is stable
across every linked worktree, so the two segments never duplicate."
```

---

### Task 2: extract pure candidate/apply halves from `prune_stale` and `adopt_predecessor_links`

**Files:**
- Modify: `tools/setup.py:1055-1092` (`prune_stale`), `tools/setup.py:1126-1167` (`adopt_predecessor_links`)
- Test: `tests/test_setup.py:1052-1103` (`TestPruneStale`), `tests/test_setup.py:1104-1199` (`TestAdoptPredecessorLinks`)

**Interfaces:**
- Consumes: `installed_links(claude_dir, install_dir) -> dict[cat, dict[name, target]]` (existing, `tools/setup.py:832`), `predecessor_candidates(claude_dir, install_dir, entries) -> list[(cat, name, old, new_target)]` (existing, unchanged, `tools/setup.py:1095`), `unlink_one(link, dry, counts)` (existing).
- Produces: `stale_link_candidates(claude_dir, install_dir, present) -> list[str]` ("cat/name"), `apply_stale_prune(claude_dir, stale, dry, counts) -> None`, `apply_predecessor_links(claude_dir, cands, repoint, dry, counts) -> None`. Task 3 calls all three directly; `prune_stale`/`adopt_predecessor_links` keep their exact existing signatures/behavior (still used nowhere except by Task 3's factory, which is being removed from `cmd_install` — kept here as thin wrappers so their documented headless/interactive contract and existing tests stay intact for any future caller).

- [x] **Step 1: Write the failing tests**

In `tests/test_setup.py`, add after `TestPruneStale` (after line 1103):

```python
class TestStaleLinkCandidatesPure(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")
        self.claude = os.path.join(self.tmp, ".claude")
        os.makedirs(os.path.join(self.install, "skills"))
        os.makedirs(os.path.join(self.claude, "skills"))
        self.gone = os.path.join(self.claude, "skills", "gone")
        os.symlink(os.path.join(self.install, "skills", "gone"), self.gone)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_detects_without_mutating(self):
        stale = setup.stale_link_candidates(self.claude, self.install, present={})
        self.assertEqual(stale, ["skills/gone"])
        self.assertTrue(os.path.lexists(self.gone))   # detection never mutates

    def test_apply_removes_and_counts(self):
        c = setup.new_counts()
        setup.apply_stale_prune(self.claude, ["skills/gone"], dry=False, counts=c)
        self.assertFalse(os.path.lexists(self.gone))
        self.assertEqual(c["pruned"], 1)

    def test_apply_dry_run_leaves_link_but_counts(self):
        c = setup.new_counts()
        setup.apply_stale_prune(self.claude, ["skills/gone"], dry=True, counts=c)
        self.assertTrue(os.path.lexists(self.gone))
        self.assertEqual(c["pruned"], 1)
```

Add after `TestAdoptPredecessorLinks` (after line 1199, immediately before `TestSelectionModel` at line 1200):

```python
class TestApplyPredecessorLinksPure(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.install = os.path.join(self.tmp, "ai-kit")
        self.old = os.path.join(self.tmp, "uz-kit")
        self.claude = os.path.join(self.tmp, ".claude")
        for root in (self.install, self.old):
            os.makedirs(os.path.join(root, "skills"))
        os.makedirs(os.path.join(self.claude, "skills"))
        self.link = os.path.join(self.claude, "skills", "alpha")
        os.symlink(os.path.join(self.old, "skills", "alpha"), self.link)
        self.new_target = os.path.join(self.install, "skills", "alpha")
        self.cands = [("skills", "alpha",
                       os.path.join(self.old, "skills", "alpha"), self.new_target)]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_repoint_true_relinks_to_new_target(self):
        c = setup.new_counts()
        setup.apply_predecessor_links(self.claude, self.cands, repoint=True,
                                      dry=False, counts=c)
        self.assertEqual(os.readlink(self.link), self.new_target)
        self.assertEqual(c["relinked"], 1)

    def test_repoint_false_deletes_link(self):
        c = setup.new_counts()
        setup.apply_predecessor_links(self.claude, self.cands, repoint=False,
                                      dry=False, counts=c)
        self.assertFalse(os.path.lexists(self.link))
        self.assertEqual(c["pruned"], 1)

    def test_dry_run_mutates_nothing(self):
        c = setup.new_counts()
        setup.apply_predecessor_links(self.claude, self.cands, repoint=True,
                                      dry=True, counts=c)
        self.assertEqual(os.readlink(self.link), os.path.join(self.old, "skills", "alpha"))
        self.assertEqual(c["relinked"], 1)   # still counted as intended
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run python3 -m pytest tests/test_setup.py -k "StaleLinkCandidatesPure or ApplyPredecessorLinksPure" -v`
Expected: FAIL — `AttributeError: module 'tools.setup' has no attribute 'stale_link_candidates'` (and similarly for the other two new names).

- [x] **Step 3: Implement**

Replace `prune_stale` (`tools/setup.py:1055-1092`) with the extracted pure detector, a pure applier, and a thin wrapper preserving the exact original behavior:

```python
def stale_link_candidates(claude_dir, install_dir, present):
    """B - A: ai-kit symlinks under ~/.claude whose repo entry no longer exists
    (deleted upstream). `present` maps cat -> set(names) still in the repo.
    Pure detection — read-only, never mutates. Returns the 'cat/name' list."""
    installed = installed_links(claude_dir, install_dir)
    stale = []
    for cat in CATEGORIES:
        keep = present.get(cat, set())
        for name in sorted(installed[cat]):
            if name in keep:
                continue
            link = os.path.join(claude_dir, cat, name)
            # only stale if its target no longer resolves (entry removed upstream)
            if os.path.exists(link):
                continue
            stale.append(f"{cat}/{name}")
    return stale


def apply_stale_prune(claude_dir, stale, dry, counts):
    """Remove each 'cat/name' stale link (mutating). Counts as pruned, not
    unlinked — pruned/unlinked are distinct tallies."""
    for item in stale:
        cat, name = item.split("/", 1)
        unlink_one(os.path.join(claude_dir, cat, name), dry, counts)
        counts["pruned"] += 1
        counts["unlinked"] -= 1


def prune_stale(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    claude_dir, install_dir, present, tty, dry, counts,
):
    """B − A: ai-kit symlinks under ~/.claude whose repo entry no longer exists
    (deleted upstream). `present` maps cat -> set(names) still in the repo.
    Interactive: warn by name, offer to prune (confirmed). Headless: auto-remove
    the dead link + print a warning (§4). Returns the list of 'cat/name' pruned
    (or, when the user declines, the list that WAS offered)."""
    stale = stale_link_candidates(claude_dir, install_dir, present)
    if not stale:
        return []
    if is_interactive(tty):
        banner = "\nThese ai-kit links point at entries removed upstream:\n"
        banner += "".join(f"  - {item}\n" for item in stale)
        _tty_write(tty, banner)
        if not ask_yes_no(tty, "prune them?", default=False):
            return stale  # offered, declined
    else:
        for item in stale:
            print(f"warn: removing dead ai-kit link {item} (entry removed upstream)",
                  file=sys.stderr)
    apply_stale_prune(claude_dir, stale, dry, counts)
    return stale
```

Replace `adopt_predecessor_links` (`tools/setup.py:1126-1167`) the same way — extract the mutation loop into `apply_predecessor_links`, keep `predecessor_candidates` untouched, and turn `adopt_predecessor_links` into a thin wrapper:

```python
def apply_predecessor_links(claude_dir, cands, repoint, dry, counts):
    """Apply the repoint/delete decision for each predecessor-link candidate
    (mutating). `cands` is predecessor_candidates()'s output:
    (cat, name, old, new_target)."""
    for cat, name, _old, new_target in cands:
        link = os.path.join(claude_dir, cat, name)
        if not dry:
            if os.path.lexists(link):
                os.remove(link)
            if repoint:
                os.symlink(new_target, link)
        counts["relinked" if repoint else "pruned"] += 1


def adopt_predecessor_links(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    claude_dir, install_dir, entries, tty, dry, counts,
):
    """Resolve links from a previous ai-kit install. Interactive: list them and
    ask whether to re-point to THIS install (default) or drop them. Headless:
    warn only and leave them alone — never silently clobber a foreign link.
    Returns the list of 'cat/name' candidates found."""
    cands = predecessor_candidates(claude_dir, install_dir, entries)
    items = [f"{cat}/{name}" for cat, name, _, _ in cands]
    if not cands:
        return []
    if not is_interactive(tty):
        for it in items:
            print(f"warn: {it} links to a previous ai-kit install — run setup "
                  "interactively to re-point or delete it", file=sys.stderr)
        return items
    n = len(items)
    warn = _WARN if _use_color(tty) else ""
    bold = _BOLD if _use_color(tty) else ""
    rst = _RESET if _use_color(tty) else ""
    banner = "\nThese links point at a PREVIOUS ai-kit install (e.g. a renamed repo):\n"
    banner += "".join(f"  - {it}\n" for it in items)
    banner += (
        f"\n{warn}  ⚠  Answering No DELETES these {n} stale link(s) — "
        f"this cannot be undone.{rst}\n\n"
        f"  {bold}Yes{rst} → re-point all {n} link(s) to THIS install (each link recreated here)\n"
        f"  {bold}No{rst}  → {warn}DELETE{rst} all {n} stale link(s) from ~/.claude\n"
        "         (only these dangling links are removed — your files and this\n"
        "         install are left untouched)\n")
    _tty_write(tty, banner)
    prompt = (f"Re-point them to this install?  "
              f"{warn}(No DELETES the {n} stale link(s)){rst}")
    repoint = ask_yes_no(tty, prompt, default=True)
    apply_predecessor_links(claude_dir, cands, repoint, dry, counts)
    return items
```

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run python3 -m pytest tests/test_setup.py -k "PruneStale or AdoptPredecessorLinks or StaleLinkCandidatesPure or ApplyPredecessorLinksPure" -v`
Expected: PASS — the new tests pass, and every pre-existing `TestPruneStale`/`TestAdoptPredecessorLinks` test still passes unmodified (observable behavior of the public functions is unchanged).

- [x] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "refactor(setup): split stale/predecessor-link detection from apply

Extracts pure stale_link_candidates/apply_stale_prune and
apply_predecessor_links out of prune_stale/adopt_predecessor_links so
the wizard can detect candidates and apply a decision separately,
without duplicating the mutation logic. prune_stale and
adopt_predecessor_links keep their exact existing behavior."
```

---

### Task 3: wire housekeeping detection + a live `status_line` callable into the wizard, off the CLI pre-UI path

**Files:**
- Modify: `tools/setup.py:1865-1930` (`_build_wizard_context`), `tools/setup.py:1962-2025` (`launch_wizard`), `tools/setup.py:2028-2053` (`cmd_install`)
- Test: `tests/test_setup.py:2623-2673` (`TestWizardContextPopulation`), new tests near it

**Interfaces:**
- Consumes: `stale_link_candidates`, `apply_stale_prune`, `predecessor_candidates`, `apply_predecessor_links` (all from Task 2), `detect_statusline(paths) -> dict` (existing, `tools/setup.py:1352`), `Selection`, `_default_selection`, `CATEGORIES` (existing).
- Produces: `WizardContext.housekeeping: dict` — `{"stale": [...cat/name...], "predecessors": [...cat/name...]}`, display strings only. `WizardContext.status_line` changes from a frozen `dict` to a zero-arg **callable** `() -> {"state": str, "current_command": str|None}`. `WizardContext.apply_housekeeping: object` — new callable `(prune: bool, repoint: bool) -> {"selection": Selection, "initial_enabled": dict}`, built by `_make_apply_housekeeping`. Task 4 (wizard_app.py) consumes all three.

- [x] **Step 1: Write the failing tests**

In `tests/test_setup.py`, update `test_context_shape_and_user_external_on_by_default` (lines 2654-2657) — `status_line` becomes a callable:

```python
        ctx = captured["ctx"]
        # status_line is now a live callable, not a frozen dict
        sl_state = ctx.status_line()
        self.assertIn("state", sl_state)
        self.assertIn("current_command", sl_state)
        self.assertEqual(sl_state["state"], "unset")
```

Add a new test class after `TestWizardContextPopulation` (after line 2673):

```python
@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestWizardHousekeeping(unittest.TestCase):
    """launch_wizard surfaces stale/predecessor link candidates via
    ctx.housekeeping and an apply_housekeeping callable, instead of
    prune_stale/adopt_predecessor_links running raw-terminal prompts
    pre-wizard."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.install = os.path.join(self.tmp, "ai-kit")
        self.old = os.path.join(self.tmp, "uz-kit")
        self.claude = os.path.join(self.tmp, ".claude")
        os.makedirs(os.path.join(self.install, "skills"))
        os.makedirs(os.path.join(self.install, "tools"))
        os.makedirs(os.path.join(self.old, "skills"))
        skill_dir = os.path.join(self.install, "skills", "alpha")
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write("---\nname: alpha\n---\n")
        open(os.path.join(self.install, "tools", "status-line.py"), "w").close()
        with open(os.path.join(self.install, "tools", "statusline.toml.sample"), "w") as f:
            f.write("# recipe\n")
        for cat in setup.CATEGORIES:
            os.makedirs(os.path.join(self.claude, cat), exist_ok=True)
        # predecessor link: 'alpha' installed from the OLD (renamed) repo
        os.symlink(os.path.join(self.old, "skills", "alpha"),
                  os.path.join(self.claude, "skills", "alpha"))
        self.env = {"HOME": self.tmp, "AI_KIT_DIR": self.install,
                    "CLAUDE_CONFIG_DIR": self.claude,
                    "XDG_CONFIG_HOME": os.path.join(self.tmp, ".config")}

    def _paths(self):
        return setup.resolve_paths(self.env)

    def test_housekeeping_lists_predecessor_candidate(self):
        paths = self._paths()
        entries = setup.enumerate_entries(paths.install_dir)
        installed = setup.installed_links(paths.claude_dir, paths.install_dir)
        wa = _import_wizard_app()
        captured = {}

        def _fake_run(ctx):
            captured["ctx"] = ctx
            return None

        class _FakeTty:
            def isatty(self):
                return True

        import contextlib
        with mock.patch.object(wa, "run_wizard", _fake_run), \
             mock.patch.object(setup, "stdin_on_tty", return_value=contextlib.nullcontext()):
            setup.launch_wizard(paths, entries, installed, _FakeTty(), True,
                                setup.new_counts())

        ctx = captured["ctx"]
        self.assertEqual(ctx.housekeeping["predecessors"], ["skills/alpha"])
        self.assertEqual(ctx.housekeeping["stale"], [])

    def test_apply_housekeeping_repoints_and_refreshes_selection(self):
        paths = self._paths()
        entries = setup.enumerate_entries(paths.install_dir)
        installed = setup.installed_links(paths.claude_dir, paths.install_dir)
        wa = _import_wizard_app()
        captured = {}

        def _fake_run(ctx):
            captured["ctx"] = ctx
            return None

        class _FakeTty:
            def isatty(self):
                return True

        import contextlib
        with mock.patch.object(wa, "run_wizard", _fake_run), \
             mock.patch.object(setup, "stdin_on_tty", return_value=contextlib.nullcontext()):
            setup.launch_wizard(paths, entries, installed, _FakeTty(), False,
                                setup.new_counts())

        ctx = captured["ctx"]
        outcome = ctx.apply_housekeeping(False, True)   # decline prune (none), repoint yes
        link = os.path.join(self.claude, "skills", "alpha")
        self.assertEqual(os.readlink(link), os.path.join(self.install, "skills", "alpha"))
        # repointed link now counts as installed -> alpha defaults ON
        self.assertTrue(outcome["initial_enabled"][("skills", "alpha")])
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run python3 -m pytest tests/test_setup.py -k "TestWizardHousekeeping or test_context_shape_and_user_external_on_by_default" -v`
Expected: FAIL — `TypeError: 'dict' object is not callable` (status_line test) and `AttributeError`/`KeyError` for `ctx.housekeeping`/`ctx.apply_housekeeping` (new tests).

- [x] **Step 3: Implement**

In `tools/setup.py`, change `_build_wizard_context`'s signature and body (lines 1865-1930) to accept the pre-computed candidates and build `housekeeping` + the live `status_line` callable:

```python
def _build_wizard_context(  # pylint: disable=too-many-locals,too-many-arguments,too-many-positional-arguments
    paths, entries, installed, sample_json, wizard_app_mod, stale=None, predecessor_cands=None,
):
    """Construct WizardContext for launch_wizard (extracted for testability).

    ``wizard_app_mod`` is the already-imported wizard_app module, passed
    explicitly so tests can supply ``tools.wizard_app`` without module-identity
    issues (the bare ``import wizard_app`` in launch_wizard is a different object
    than ``from tools import wizard_app``).

    ``stale``/``predecessor_cands`` are launch_wizard's pre-computed detection
    results (Task 3): supplying them here only shapes ``ctx.housekeeping``'s
    display strings — defaulting to empty when omitted (existing callers that
    don't care about housekeeping keep working unmodified).

    ``_initial_enabled`` is keyed by the INSTALLED state, not the wizard's
    visual pre-selection.  On a first run the wizard pre-checks everything, but
    nothing is installed yet — so the baseline must be all-False to let
    ``_has_net_change`` (Task 5) correctly detect that confirming the defaults
    IS a write.  On a reconfigure, installed state equals the pre-selection so
    both representations agree."""
    stale = stale if stale is not None else []
    predecessor_cands = predecessor_cands if predecessor_cands is not None else []
    default = _default_selection(entries, installed)
    sel = Selection(
        (cat, name, name in default[cat])
        for cat in CATEGORIES
        for name, _ in entries[cat]
    )
    initial_enabled = {
        (cat, name): (name in installed[cat])
        for cat in CATEGORIES
        for name, _ in entries[cat]
    }

    sl_state = detect_statusline(paths)
    inventory = load_segment_inventory(INVENTORY_PATH)
    overrides = _statusline_icon_line_overrides(paths.config_toml)
    segment_meta = build_segment_meta(inventory, overrides)
    examples_dir = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "examples", "segments")
    external = discover_external_segments(paths, examples_dir)

    # Wizard segment state = built-in defaults/recipe, plus every discovered
    # external keyed by id. A discovered external's default mirrors the renderer:
    # provenance "user" means it lives in the segments dir and renders by default
    # (default ON, unless statusline.toml disables it); a "bundled" example is only
    # in examples/ and not yet installed, so it is an OFF offer until chosen.
    segments = current_segments(paths.config_toml)
    for e in external:
        on_by_default = e["provenance"] == "user"   # "user" = present in segments dir
        segments[e["id"]] = _external_enabled_in_toml(
            paths.config_toml, e["id"], default_on=on_by_default)

    component_meta = {
        name: _read_component_desc(abspath)
        for cat in CATEGORIES
        for name, abspath in entries[cat]
    }

    housekeeping = {
        "stale": stale,
        "predecessors": [f"{cat}/{name}" for cat, name, _old, _new in predecessor_cands],
    }

    return wizard_app_mod.WizardContext(
        selection=sel,
        state={"segments": segments,
               "layout": current_layout(paths.config_toml), "dirty": False,
               "adopt": sl_state["state"] == "ours",
               "_initial_enabled": initial_enabled},
        sample_json=sample_json,
        engine=_engine_ns(paths, sample_json),
        # Live callable, not a frozen dict — re-read fresh every time the
        # wizard's gate needs it, mirroring status-line.py's own re-probing.
        status_line=lambda: detect_statusline(paths),
        segment_meta=segment_meta,
        external_segments=external,
        component_meta=component_meta,
        housekeeping=housekeeping,
    )
```

Add `_make_apply_housekeeping` right after `_make_wizard_commit` (after line 1959):

```python
def _make_apply_housekeeping(paths, entries, stale, predecessor_cands, dry, counts):
    """Build the apply_housekeeping(prune, repoint) callable the wizard runs
    IN-UI right after its housekeeping gate is answered (before Choose becomes
    usable). Applies the stale-prune and/or predecessor-repoint decision, then
    rebuilds installed_links + the default component selection from scratch —
    a repointed predecessor link becomes a current ai-kit link, which can
    change which components default to pre-checked on Choose (mirrors the
    ordering the old CLI-side prune_stale/adopt_predecessor_links ->
    installed_links sequence relied on)."""
    def apply_housekeeping(prune, repoint):
        if stale and prune:
            apply_stale_prune(paths.claude_dir, stale, dry, counts)
        if predecessor_cands:
            apply_predecessor_links(paths.claude_dir, predecessor_cands, repoint, dry, counts)
        installed = installed_links(paths.claude_dir, paths.install_dir)
        default = _default_selection(entries, installed)
        sel = Selection(
            (cat, name, name in default[cat])
            for cat in CATEGORIES
            for name, _ in entries[cat]
        )
        initial_enabled = {
            (cat, name): (name in installed[cat])
            for cat in CATEGORIES
            for name, _ in entries[cat]
        }
        return {"selection": sel, "initial_enabled": initial_enabled}
    return apply_housekeeping
```

Update `launch_wizard` (lines 1962-2025) to compute `present`/`stale`/`predecessor_cands` once, pass them into `_build_wizard_context`, and inject `apply_housekeeping` alongside `commit`:

```python
    import wizard_app  # pylint: disable=import-outside-toplevel

    with open(_sample_input_path(), encoding="utf-8") as f:
        sample_json = f.read()
    present = {cat: {n for n, _ in entries[cat]} for cat in CATEGORIES}
    stale = stale_link_candidates(paths.claude_dir, paths.install_dir, present)
    predecessor_cands = predecessor_candidates(paths.claude_dir, paths.install_dir, entries)
    ctx = _build_wizard_context(paths, entries, installed, sample_json, wizard_app,
                                stale, predecessor_cands)
    # The real install (component symlinks + doctor-validated status-line write +
    # settings.json wiring) now runs INSIDE the wizard on Review-confirm, so the
    # Done screen reflects the actual result. Inject the commit + housekeeping
    # callables here, where paths/entries/dry/counts are in scope.
    ctx = ctx._replace(
        commit=_make_wizard_commit(paths, entries, dry, counts),
        apply_housekeeping=_make_apply_housekeeping(
            paths, entries, stale, predecessor_cands, dry, counts),
    )
```

Update `cmd_install` (lines 2028-2053) to stop calling `prune_stale`/`adopt_predecessor_links` pre-UI — that detection+apply now happens inside `launch_wizard`/the wizard gate:

```python
def cmd_install(env, tty, dry, examples_flag=None):
    """Reconcile skills/agents/commands and wire the status line. Interactive-only
    and fail-closed: ``require_tty`` exits before this function is ever called with
    tty=None, so tty is always a real terminal here. The ``reconfigure`` subcommand
    is install without first-run defaults — when anything is already linked,
    _first_run() is False, so the selection keeps existing state."""
    paths = resolve_paths(env)
    entries = enumerate_entries(paths.install_dir)
    counts = new_counts()
    installed = installed_links(paths.claude_dir, paths.install_dir)

    # A: choose what to install + segment layout via Textual wizard (Task 2.1+).
    # Stale-link pruning and predecessor-link repointing (previously raw
    # pre-UI terminal prompts here) now happen INSIDE the wizard's housekeeping
    # gate — see launch_wizard / _build_wizard_context / _make_apply_housekeeping.
    result = launch_wizard(paths, entries, installed, tty, dry, counts)
```

(The rest of `cmd_install` — the examples block and the summary prints — is unchanged.)

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run python3 -m pytest tests/test_setup.py -v`
Expected: PASS — full file green, including:
- `TestCmdInstallExternalReconcile` (its `mock.patch.object(setup, "prune_stale")`/`"adopt_predecessor_links")` patches — verified at `tests/test_setup.py:2760-2761, 2797-2798, 2833-2834` — become harmless no-ops since `cmd_install` no longer calls them, but nothing asserts they were called);
- `TestCmdInstall` (`tests/test_setup.py:1444-1510`) — unaffected for a *different* reason: it never mocks `prune_stale`/`adopt_predecessor_links` at all. Its fixtures pass `tty=None` and start with empty `~/.claude` categories, so both functions already found nothing stale/predecessor to act on before this change; removing their call sites from `cmd_install` doesn't alter that outcome;
- `TestWizardContextPopulation` (both call sites to `_build_wizard_context` — the one at what was line 2054/2945 — keep working since `stale`/`predecessor_cands` default to `[]`).

- [x] **Step 5: Commit**

```bash
git add tools/setup.py tests/test_setup.py
git commit -m "feat(setup): move stale/predecessor-link + statusline detection into the wizard

cmd_install no longer runs prune_stale/adopt_predecessor_links as raw
pre-UI terminal prompts before launch_wizard. Detection now feeds
WizardContext.housekeeping and an injected apply_housekeeping
callable the wizard runs once its gate is answered; status_line
becomes a live callable re-read on demand instead of a frozen dict."
```

---

### Task 4: housekeeping gate + live status-line reads inside `WizardApp`

**Files:**
- Modify: `tools/wizard_app.py:101-119` (`WizardContext`), `tools/wizard_app.py:183-214` (`__init__`), `tools/wizard_app.py:419-427` (`_render_footer`), `tools/wizard_app.py:436-467` (`_render_choose`), `tools/wizard_app.py:480-501` (`_render_arrange` gate reads), `tools/wizard_app.py:606-663` (`on_key`/`_key_choose`/`_enter_arrange`/`_key_arrange`)
- Modify: `tests/wizard_fixtures.py:34-41` (`make_ctx`)
- Test: `tests/test_wizard_app.py`, new `TestHousekeepingGate` class

**Interfaces:**
- Consumes: `WizardContext.housekeeping: dict`, `WizardContext.apply_housekeeping: callable|None`, `WizardContext.status_line: callable` (all from Task 3).
- Produces: `WizardApp.housekeeping_done: bool`, gate rendered inline in `#picksbox` at Step 0 before the component picker is usable. No later task depends on this one — it is the last code task.

- [x] **Step 1: Write the failing tests**

In `tests/wizard_fixtures.py`, update `make_ctx` (lines 34-41) — `status_line` becomes a callable and `housekeeping` is supplied:

```python
    return wa.WizardContext(
        selection=sel,
        state={"segments": segments, "layout": layout, "dirty": False,
               "adopt": sl_state == "ours", "_initial_enabled": initial},
        sample_json="{}", engine=None,
        status_line=lambda: {"state": sl_state, "current_command": None},
        segment_meta=meta, external_segments=external,
        component_meta={name: "" for _, name, _ in sel.items},
        housekeeping={"stale": [], "predecessors": []})
```

In `tests/test_wizard_app.py`, add `import threading` to the top-of-file imports (used by the re-entrancy test below), then add a new test class (after `TestStructuralFidelity` or any existing class — append near the end of the file):

```python
@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")
class TestHousekeepingGate(unittest.IsolatedAsyncioTestCase):
    def _ctx(self, **housekeeping):
        hk = {"stale": [], "predecessors": [], **housekeeping}
        return make_ctx()._replace(housekeeping=hk)

    async def test_no_candidates_skips_gate(self):
        app = wa.WizardApp(self._ctx())
        self.assertTrue(app.housekeeping_done)
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertIn("of", str(app.query_one("#picksCount", Static).content))

    async def test_stale_only_prune_on_yes(self):
        seen = {}
        def apply_hk(prune, repoint):
            seen["prune"], seen["repoint"] = prune, repoint
            return {"selection": None, "initial_enabled": {}}
        ctx = self._ctx(stale=["skills/gone"])._replace(apply_housekeeping=apply_hk)
        app = wa.WizardApp(ctx)
        self.assertFalse(app.housekeeping_done)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("y")
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertTrue(app.housekeeping_done)
        self.assertEqual(seen["prune"], True)

    async def test_stale_then_predecessors_sequenced(self):
        seen = {}
        def apply_hk(prune, repoint):
            seen["prune"], seen["repoint"] = prune, repoint
            return {"selection": None, "initial_enabled": {}}
        ctx = self._ctx(stale=["skills/gone"], predecessors=["skills/alpha"]
                        )._replace(apply_housekeeping=apply_hk)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertFalse(app.housekeeping_done)
            await pilot.press("n")               # stale: decline prune
            self.assertFalse(app.housekeeping_done)   # predecessors still pending
            await pilot.press("y")               # predecessors: repoint
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertTrue(app.housekeeping_done)
        self.assertEqual(seen["prune"], False)
        self.assertEqual(seen["repoint"], True)

    async def test_apply_housekeeping_none_falls_back_to_legacy(self):
        # apply_housekeeping=None (unit fixtures without it) -> pressing an
        # answer still resolves the gate using the existing selection/state.
        ctx = self._ctx(stale=["skills/gone"])
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("y")
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertTrue(app.housekeeping_done)

    async def test_apply_housekeeping_raises_resolves_gate(self):
        # apply_housekeeping raising must not leave the wizard stuck showing
        # "Applying…" forever — the gate resolves and the failure is captured,
        # not swallowed into a hang or an unhandled exception.
        def apply_hk(prune, repoint):
            raise OSError("disk exploded")

        ctx = self._ctx(stale=["skills/gone"])._replace(apply_housekeeping=apply_hk)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("y")
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertTrue(app.housekeeping_done)   # gate resolved, no hang
        self.assertFalse(app._hk_applying)
        self.assertIn("disk exploded", app._hk_error)

    async def test_second_keypress_during_apply_is_noop(self):
        # A keypress that arrives while the apply worker is still in flight
        # (_hk_applying=True) must not re-enter _key_housekeeping's
        # self._hk_pending[self._hk_stage] indexing — by the time the last
        # pending answer is recorded, self._hk_stage == len(self._hk_pending),
        # so an unguarded second read raises IndexError.
        release = threading.Event()
        seen = {"calls": 0}

        def apply_hk(prune, repoint):
            seen["calls"] += 1
            release.wait(timeout=2)   # held open until the test releases it
            return {"selection": None, "initial_enabled": {}}

        ctx = self._ctx(stale=["skills/gone"])._replace(apply_housekeeping=apply_hk)
        app = wa.WizardApp(ctx)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("y")             # kicks off the apply worker
            self.assertTrue(app._hk_applying)  # still in flight (blocked on release)
            await pilot.press("y")             # arrives mid-flight; must be a no-op
            self.assertEqual(seen["calls"], 1)   # guard swallowed the second keypress
            release.set()
            await app.workers.wait_for_complete()
            await pilot.pause()
        self.assertTrue(app.housekeeping_done)
        self.assertEqual(seen["calls"], 1)
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run python3 -m pytest tests/test_wizard_app.py -k "Housekeeping" -v`
Expected: FAIL — `TypeError: WizardContext.__new__() missing 1 required positional argument: 'housekeeping'` and/or `AttributeError: 'WizardApp' object has no attribute 'housekeeping_done'`.

Also run the full existing suite to confirm it currently fails on the fixture's `status_line` dict-vs-callable mismatch is NOT yet an issue (it still passes at this point, since production code hasn't changed):

Run: `uv run python3 -m pytest tests/test_wizard_app.py -v`
Expected: PASS (unaffected so far — production code in `wizard_app.py` hasn't changed yet).

- [x] **Step 3: Implement**

In `tools/wizard_app.py`, update `WizardContext` (lines 101-119):

```python
class WizardContext(NamedTuple):
    """All data and behaviour the wizard needs, injected by setup.py at
    call-time.  wizard_app imports nothing from setup.py; this is the seam."""
    selection: object           # setup.Selection instance
    state: dict                 # {"segments": {key: bool}, "layout": [...],
                                #  "dirty": bool, "adopt": bool}
    sample_json: str            # rendered sample input JSON for preview
    engine: object                   # callables: render_preview, apply_command, groups, order
    # New Plan-A fields (Task 10) — always populated by setup.py.launch_wizard.
    status_line: object         # callable () -> {"state": str, "current_command": str|None}
                                #  — called fresh each read, never cached in the context.
    segment_meta: dict          # {key: {description, sample, icon, line}}
    external_segments: list     # [{id, name, path, default_on, description,
                                #   icon, sample, line, provenance}, …]
    component_meta: dict          # {name: description} across all CATEGORIES
    housekeeping: dict = {}     # {"stale": [...], "predecessors": [...]} — "cat/name"
                                #  display strings; empty = nothing pending, gate skipped.
    # Injected by launch_wizard: commit(selection, state) -> {"ok", "adopt", "log"}.
    # Runs the real install (symlinks + doctor-validated status-line write) IN-UI on
    # Review-confirm. None in unit fixtures → the view falls back to a no-op commit.
    commit: object = None
    # Injected by launch_wizard: apply_housekeeping(prune, repoint) ->
    # {"selection", "initial_enabled"}. Runs IN-UI once the housekeeping gate is
    # answered. None → legacy no-op (fine when housekeeping is empty).
    apply_housekeeping: object = None
```

Update `__init__` (lines 183-214) — the `gate_done` line now calls the live `status_line`, and new housekeeping state is initialized:

```python
        # adoption gate: 'ours' adopts silently; otherwise the gate is shown on Arrange entry
        self.gate_done = ctx.status_line().get("state") == "ours"
        if self.gate_done:
            self.state["adopt"] = True
        # housekeeping gate (Step 0): stale/predecessor link candidates, answered
        # in sequence before the component picker is usable.
        self.housekeeping = dict(ctx.housekeeping) if ctx.housekeeping else {}
        self._hk_pending = [k for k in ("stale", "predecessors") if self.housekeeping.get(k)]
        self._hk_stage = 0
        self._hk_answers: dict = {}
        self._hk_applying = False
        self._hk_error: str | None = None
        self.housekeeping_done = not self._hk_pending
```

Update the two remaining `ctx.status_line` reads inside `_render_arrange`/`_enter_arrange`/`_key_arrange` (lines 480-501, 633-639, 665-676) to call it:

```python
    def _render_arrange(self) -> None:
        lane0 = self.query_one("#lane0", Static)
        if not self.gate_done:
            sl = self.ctx.status_line()
```

```python
    def _enter_arrange(self) -> bool:
        # Entering the status-line step from Choose. Re-ask the adoption gate
        # unless the user already opted in (adopt True) or the status line is
        # already ours — so a prior "decline" never lands on a stale board.
        if not self.state.get("adopt"):
            self.gate_done = self.ctx.status_line().get("state") == "ours"
        self.step = STEP_ARRANGE
        return True
```

```python
            elif k == "enter":                 # follow the shown default
                self.state["adopt"] = self.ctx.status_line().get("state") != "foreign"
```

Insert the housekeeping-gate check at the top of `_key_choose` (line 642):

```python
    def _key_choose(self, event: events.Key) -> bool:
        if not self.housekeeping_done:
            return self._key_housekeeping(event)
        ch, k = event.character, event.key
```

(the rest of `_key_choose` is unchanged)

Add `_key_housekeeping` and `_apply_housekeeping` right after `_key_choose` (after its closing `return True` around line 663):

```python
    def _key_housekeeping(self, event: events.Key) -> bool:
        if self._hk_applying:
            return True             # ignore keys until the apply worker finishes
        ch, k = event.character, event.key
        kind = self._hk_pending[self._hk_stage]
        default = kind != "stale"          # stale defaults to decline; predecessors to repoint
        if ch == "y":
            answer = True
        elif ch == "n":
            answer = False
        elif k == "enter":
            answer = default
        else:
            return False
        self._hk_answers[kind] = answer
        self._hk_stage += 1
        if self._hk_stage >= len(self._hk_pending):
            self._hk_applying = True
            self._apply_housekeeping()
        return True

    @work(thread=True, exclusive=True)
    def _apply_housekeeping(self) -> None:
        """Worker: apply the housekeeping decision(s) off the event loop, then
        refresh the Choose selection/state and unblock the gate. Any failure is
        captured so the UI never hangs in the 'Applying…' state, mirroring how
        _run_commit already guards ctx.commit() failures below."""
        prune = self._hk_answers.get("stale", False)
        repoint = self._hk_answers.get("predecessors", True)
        try:
            if self.ctx.apply_housekeeping is None:
                outcome = {"selection": self.sel,
                          "initial_enabled": self.state.get("_initial_enabled", {})}
            else:
                outcome = self.ctx.apply_housekeeping(prune, repoint)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            outcome = {}
            self._hk_error = f"housekeeping failed: {exc}"
        if outcome.get("selection") is not None:
            self.sel = outcome["selection"]
        self.state["_initial_enabled"] = outcome.get(
            "initial_enabled", self.state.get("_initial_enabled", {}))
        self.housekeeping_done = True
        self._hk_applying = False
        if self._hk_error:
            # Surface the captured failure once, via Textual's own toast — the
            # gate has already resolved (housekeeping_done=True, no hang), so
            # there is no gate screen left to render it inline on; this runs
            # on the main thread via call_from_thread, same as _render below.
            self.call_from_thread(self.notify, self._hk_error, severity="error")
        self.call_from_thread(self._render)
```

Update `_render_choose` (lines 436-467) to render the gate instead when housekeeping is pending:

```python
    def _render_choose(self) -> None:
        if not self.housekeeping_done:
            self._render_housekeeping_gate()
            return
        items = self.sel.items
```

(the rest of `_render_choose` is unchanged; keep its existing body under the new early return)

Add `_render_housekeeping_gate` right before `_render_choose` (before line 436):

```python
    def _render_housekeeping_gate(self) -> None:
        picksbox = self.query_one("#picksbox", Static)
        self.query_one("#picksCount", Static).update("")
        if self._hk_applying:
            picksbox.update(f"[{DIM}]Applying…[/]")
            return
        kind = self._hk_pending[self._hk_stage]
        items = self.housekeeping.get(kind, [])
        listing = "\n".join(f"  [{DIM}]-[/] {it}" for it in items)
        if kind == "stale":
            gate = (f"[b {WARN}]⚠  {len(items)} link(s) point at entries removed upstream[/]\n"
                    f"{listing}\n\n"
                    f"[#0d1117 on {WARN}] y = prune them · N / Enter = keep them [/]")
        else:
            gate = (f"[b {WARN}]⚠  {len(items)} link(s) point at a PREVIOUS ai-kit install[/]\n"
                    f"{listing}\n\n"
                    f"[{DIM}]No deletes them — this cannot be undone.[/]\n"
                    f"[#0d1117 on {WARN}] Y / Enter = re-point to this install · n = delete them [/]")
        picksbox.update(gate)
```

Update `_render_footer` (lines 419-427) to show the Y/N key bar during the housekeeping gate too:

```python
    def _render_footer(self) -> None:
        sep = f"   [{LINE}]│[/]   "
        if self.step == STEP_ARRANGE and not self.gate_done:
            keys = [("Yes", "Y", True), ("No", "N", False), ("Back", "Esc", False)]
        elif self.step == STEP_CHOOSE and not self.housekeeping_done:
            keys = [("Yes", "Y", True), ("No", "N", False)]
        else:
            keys = FOOTERS[self.step]
        left = sep.join(self._cap(*k) for k in keys)
        self.query_one("#footer-left", Static).update(left)
        self.query_one("#footer-q", Static).update(self._cap(*QUIT_KEY, False))
```

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run python3 -m pytest tests/test_wizard_app.py -v`
Expected: PASS — full file green, including every pre-existing gate/arrange/review/commit test (they all go through `make_ctx()`, which now supplies `housekeeping={"stale": [], "predecessors": []}` → `housekeeping_done=True` at construction, so Step 0 renders exactly as before for all of them).

Then run the complete test suite to confirm nothing elsewhere regressed:

Run: `uv run python3 -m pytest tests/ -v`
Expected: PASS — all files green.

- [x] **Step 5: Commit**

```bash
git add tools/wizard_app.py tests/wizard_fixtures.py tests/test_wizard_app.py
git commit -m "feat(wizard): housekeeping gate for stale/predecessor links, live status_line

Step 0 now blocks on a sequenced Y/N gate (mirroring the existing
Arrange status-line gate) for any pending stale/predecessor link
candidates, applying the decision immediately via the injected
apply_housekeeping worker before the component picker is usable.
status_line is read through the live callable everywhere the gate
needs it, instead of the frozen dict computed before launch."
```

---

### Task 5: integration verification

**Files:** none (verification only)

**Interfaces:** none — this task runs the full suite and a manual smoke check; it produces no new interface.

- [x] **Step 1: Run the full automated test suite**

Run: `uv run python3 -m pytest tests/ -v`
Expected: PASS — every test in the repository green, including `tests/test_wizard_pty.py` (PTY-level wizard tests) and `tests/test_statusline_doctor.py`.

- [x] **Step 2: Manually verify the path/gittree fix in a live worktree**

Run: `cd .claude/worktrees/context-tools-manager-plan1 2>/dev/null || git worktree add /tmp/ai-kit-verify-wt -b verify-wt-tmp` then, from inside that worktree directory, run the statusline renderer directly against a sample payload with `alt_git_worktree` enabled and confirm the `path` segment prints the main repo's name (`ai-kit`) while the worktree segment prints the worktree's own name — the two must differ.

Run: `git -C /tmp/ai-kit-verify-wt rev-parse --path-format=absolute --git-common-dir` and confirm it prints an absolute path ending in `/ai-kit/.git` (or the actual main-repo root's `.git`), matching what `probe_git_worktree_info` now expects.

Clean up: `git worktree remove /tmp/ai-kit-verify-wt --force` if the temporary worktree from this step was created (skip if you reused the existing `context-tools-manager-plan1` worktree).

- [x] **Step 3: Manually verify the housekeeping gate**

Run: `uv run tools/setup.py` from a HOME/CLAUDE_CONFIG_DIR with a symlink left over from a renamed/previous ai-kit install (or construct one per `TestWizardHousekeeping.setUp` in Task 3) and confirm: (a) no raw-terminal banner/prompt appears before the Textual UI takes over the screen, (b) Step 0 shows the Y/N gate inline in the picks box before any components are selectable, (c) answering it immediately repoints/deletes the link on disk (checkable via `readlink`) regardless of whether you complete or quit the rest of the wizard afterward.

- [x] **Step 4: Update the PRD's implementation-status note (optional but recommended)**

If any Task above changed line numbers/behavior described in `docs/prds/context-tools-worktree-ux-fixes-v1.0-prd.md`, add a short "Implemented — see `docs/superpowers/plans/2026-07-30-context-tools-worktree-ux-fixes.md`" line under the PRD's `Document Version` footer. No other PRD edits are required.
