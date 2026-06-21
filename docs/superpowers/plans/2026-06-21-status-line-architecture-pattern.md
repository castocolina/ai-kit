# Status-line Architecture Pattern — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the internal architecture of `tools/status-line.py` onto one named pattern — *functional core / imperative shell* + config-object DI + convention-discovered builders + strict types — without changing a single byte of rendered output.

**Architecture:** Six banner-delimited blocks in one stdlib-only file, in dependency order: SHELL → CONFIG → CONTEXT → HELPERS → SEGMENTS → LAYOUT/PACK. Env/TOML is read in exactly one block (CONFIG) into an immutable `Config` (stable settings only). A per-render `Context` dataclass carries eager inputs + `functools.cached_property` probes + render bookkeeping (`failed`, `slowest`); it replaces `build_data` + `_LazyData`. The `BUILDERS` dict is auto-derived from the module's `seg_*` functions. Types land last as one strict pass.

**Tech Stack:** Python 3.12 stdlib only (runtime); `dataclasses`, `functools.cached_property`, `typing`. Dev gate: `uv run pre-commit run --all-files` (ruff + pylint + pyright + vulture + shellcheck). Tests: `unittest` (not pytest).

---

## Critical context — read before starting

### This is a behavior-preserving refactor under a regression net, not feature TDD

The classic "write a failing test → make it pass" loop does **not** apply. The tests already exist. The net is:

1. **The golden snapshot** — `tests/fixtures/golden/expected.txt`, asserted by `tests/test_status_line.py::TestGoldenOutput::test_matches_golden`. It renders representative inputs (meta segments excluded) and compares byte-for-byte. **`expected.txt` is NEVER regenerated during this overhaul.** Do not run `UPDATE_GOLDEN=1`. If the golden test fails, the change altered output — revert it, do not update the snapshot.
2. **The full suite** — 543 tests across `tests/test_status_line.py` (245), `tests/test_external_segments.py` (54), `tests/test_setup.py` (174), and others.

The per-task verification loop is therefore:

```
edit code  →  migrate the unit tests coupled to the changed internals  →
run suite (green)  →  run golden (byte-identical)  →  run the phase's grep AC  →  commit
```

### Reconciling "every existing test passes unchanged" with the refactor

The PRD acceptance criterion says *"every existing test passes unchanged."* Taken literally this is impossible: Phase 2 **removes `build_data`** and changes the builder-facing data shape, and a significant number of sites in `tests/test_status_line.py` couple to the current internals (`sl.build_data(...)` — 10 sites; `sl.BUILDERS[...]` — 11 sites; `data["..."]` subscript; `sl.Config(...)`). The only reading consistent with the locked decisions (D1 `ctx` bag, D2 single file, D4 subscript ban, Phase-2 "build_data gone") is:

> **Behavior-preserving = observable behavior is preserved** (golden byte-identical; CLI; render output; config-resolution semantics). **Unit tests that pin internal structure are migrated in lockstep** with the code they cover — same assertions, same count, adapted to the new `Context`/discovery API. **No test is deleted and no coverage is dropped.**

The migration is deliberately kept **surgical**. The builder call signature stays `seg_x(ctx, avail, theme)` (only the first arg's *type* changes: dict → `Context`), so all 96 `_data(` call sites in `tests/test_status_line.py` are syntactically unchanged — 52 are `sl.seg_x(_data(...))` builder sites and ~44 are other callers (`pack_line`, `render`, local `data = _data()` in TestSlowestTiming) — only the `_data()` helper's body changes. The sites that genuinely migrate are counted per phase below.

Coupling inventory (measured on the starting commit), all in `tests/test_status_line.py` unless noted:

| Internal API | Sites | Migrated in |
|---|---|---|
| `_data(**over)` helper body (returns dict → returns `Context`) | 1 helper; 96 total `_data(` callers: 52 are `sl.seg_x(_data(...))` builder sites (stay byte-identical) + ~44 other callers (`pack_line`/`render`/local `data = _data()` in TestSlowestTiming) also syntactically unchanged at the call site | Phase 2 |
| `sl.build_data(...)` call | 10 + 1 in `test_external_segments.py` = 11 total | Phase 2 |
| direct `sl.seg_*(<data>, avail, theme)` invocation (the segment's first arg changes type dict → `Context`; signature/call shape unchanged) | 59 sites (52 wrap `sl.seg_x(_data(...))` + 7 pass a seeded local/multi-line `_data()`) | Phase 2 (covered by the `_data()` → `Context` rewrite — no call-site edits) |
| `data["..."]` / `data.get(...)` subscript on builder data | ~15 | Phase 2 |
| `sl.BUILDERS` direct reference | 11 | Phase 3 |
| `sl.Config(...)` direct construction | 4 | Phase 1 (only if Config gains required fields) |
| `pack_line` positional `failed` arg (1 site, L1796) + `safe_build` positional `failed` (3 sites, L1763–L1782) + `data["slowest"]` subscript (11 sites) | 15 | Phase 2 |

### Locked decisions (D1–D7) — do NOT reopen

D1 one `ctx` bag to every builder (eager + `cached_property` probes + `failed`/`slowest`). D2 single file. D3 light prefixes + `# ═══` banners + noun-grouping. D4 ban `obj[key]` on OUR types (attribute access; `raw` JSON keeps `.get()`). D5 types LAST, one dedicated strict pass. D6 `Config` = STABLE env+TOML only; per-render terminal size + `raw` live on `Context`. D7 auto-derive `BUILDERS` only; `SEGMENTS`/`LAYOUT`/`_*_DEFAULTS` stay explicit tables.

**D8 — Config-by-contract (the env-read boundary, locked by the maintainer).** `load_config` is
the **only** method that reads env for stable settings (`env.get`/`os.environ` for config keys live
nowhere else; the SHELL additionally captures `os.environ` once and resolves per-render inputs —
terminal size, effort — at its boundary per D6). The resolved `Config` object — carrying
`cache_base`, `segments_dir`, and the git `cache_ttl` — is **passed by contract** to anything that
needs it (the git probe, `build_data`/`build_context`, and every segment via `ctx.config`).
Consumers **read `config.cache_base` / `config.git["cache_ttl"]` off the object** — they never
re-resolve by calling a helper like `_cache_base(env)` at a use site, and are never handed a bare
path/ttl string "in some other way." `_cache_base(env)` survives only as `load_config`'s internal
one-shot resolver (and the out-of-scope CLI validator). Grep guard: no `_cache_base(`,
`env.get`, or `os.environ` inside any `seg_*`, probe, `build_context`, `git_snapshot`, or
render-path function.

### The load-bearing invariant — FR-R.2 (truthful `slowest`)

A probe's cost must be captured inside the **measured build of the segment that first reads it**, so `slowest` reports real ms-scale cost, not amortized µs. `_LazyData` guaranteed this by running the thunk on first `.get()`. `functools.cached_property` preserves it identically: the first attribute access runs the probe synchronously inside the caller. **Phase 2 adds an explicit test for this** (FR-A.2 acceptance) so it can never silently regress.

### Conventions

- Output language: **English** (all code, comments, commit messages).
- TDD harness is `unittest`: `python3 -m unittest tests.test_status_line[.Class[.method]]`.
- Full suite: `make test`. Quality gate: `make validate` (= `uv run pre-commit run --all-files`).
- Commits are gated by pre-commit hooks (slow but authoritative). The plan commits at every task; if a hook is too slow for the inner loop, use `git commit` normally at task end (the hook IS the gate — let it run).
- `tools/status-line.py` and `tools/setup.py` **cannot import each other** (hyphenated filename). `SEGMENTS`/`LAYOUT` defaults are duplicated in `setup.py` and pinned by drift-guard tests in `test_setup.py` — this overhaul does **not** change `SEGMENTS`/`LAYOUT` values, so those guards stay green untouched.
- `setup.py` does **not** import `Config`/`build_data`/`BUILDERS` (verified). Config/Context/discovery changes are contained to `status-line.py` + its tests.

---

## Target architecture (the end-state shapes)

These are the concrete shapes every task builds toward. Defined here once so no task re-decides them.

### `Config` (CONFIG block) — stable settings only (D6)

Stays a `namedtuple` (tests use `cfg._replace(...)` and `cfg.segments[...]`). New fields are appended **with defaults** so existing keyword construction keeps working. Added fields are the env/TOML-derived values currently re-resolved by scattered helpers:

```python
Config = namedtuple(
    "Config",
    "segments layout palette ramps git external cache_base segments_dir",
    defaults=(None, None, "", ""),
)
```

- `cache_base` — `${XDG_CACHE_HOME:-$HOME/.cache}/ai-kit` (root of on-disk caches). Feeds the git worktree cache path and the external-segment cache dir. Resolved once in `load_config`.
- `segments_dir` — the external-providers directory. Already resolved by `_resolve_external`; now stored on `Config`.
- `git` (existing dict) keeps `cache_ttl`; the git probe reads `(config.git or {}).get("cache_ttl", _GIT_CACHE_TTL)` — dict access on a dict-valued field is allowed by D4 (the ban is on subscripting `Config`/`Context` objects themselves).
- `home` and `claude_dir` are **per-render context inputs resolved at the SHELL boundary** and handed to `Context` (see below), NOT `Config` — they pair with `raw`/`work_dir` for the todo/effort probes. (They are env-stable, but live with the per-render probe inputs they serve; this honors D6's spirit — `Config` carries *settings*, the SHELL hands *inputs* to `Context`.)

### `Context` (CONTEXT block) — per-render bag (D1, D4, D6)

A **mutable `@dataclass`** (not a dict subclass — so `ctx["x"]` is a `TypeError` by construction, enforcing D4; `failed`/`slowest` mutate during render, so not frozen). Probes are `functools.cached_property`; the shared git probe is one cached property fronted by thin `@property` accessors so any of the five git fields triggers the single `git_snapshot` call on first read (preserving FR-R.2 + probe-once).

```python
@dataclass
class Context:
    """Per-render bag handed to every builder (D1). Eager inputs are resolved at
    the SHELL/CONFIG boundary; expensive probes are `cached_property`, so a probe
    runs synchronously on first attribute read — its cost lands inside the
    *measured* build of the first segment that reads it (FR-R.2) and later reads
    are free. Render bookkeeping (`failed`, `slowest`) lives here too. Attribute
    access only — never `ctx[...]` (D4). `raw` keeps `.get()`-chain access."""
    raw: dict                       # incoming status JSON (the ONLY dict-style member)
    config: "Config"
    theme: "Theme"
    # per-render terminal geometry (resolved by the SHELL; D6 — never on Config)
    cols: int
    lines: int
    dim_assumed: bool
    t_start: "int | None"
    # cheap eager fields (were build_data's `base`)
    model_name: str
    model_id: str
    effort: str
    work_dir: str
    home: str
    clock: str
    added: int
    removed: int
    cost: float
    total_ms: int
    api_ms: int
    context_pct: int
    context_max: int
    rate_limits: dict
    # probe inputs (locate materialized todo/task state; feed the cached_property probes)
    transcript: str
    session: str
    claude_dir: str
    # render bookkeeping (D1) — mutated during the render
    failed: set = field(default_factory=set)
    slowest: "tuple | None" = None

    # ── shared git probe: one call fills five fields (branch/dirty/worktree/…) ──
    @functools.cached_property
    def _git(self):
        return git_snapshot(self.work_dir,
                            ttl=(self.config.git or {}).get("cache_ttl", _GIT_CACHE_TTL),
                            cache_base=self.config.cache_base)

    @property
    def branch(self):       return self._git.branch
    @property
    def dirty(self):        return self._git.dirty
    @property
    def is_worktree(self):  return self._git.is_worktree
    @property
    def wt_name(self):      return self._git.wt_name
    @property
    def in_repo(self):      return self._git.in_repo

    @functools.cached_property
    def ago(self):
        t = self.transcript
        if t and os.path.isfile(t):
            return fmt_ago(int(time.time()) - int(os.path.getmtime(t)))
        return ""

    @functools.cached_property
    def effort_auto(self):
        return effort_setting_is_auto(self.work_dir, self.home)

    @functools.cached_property
    def _todo(self):
        return current_todo(self.transcript, self.session, self.claude_dir)

    @property
    def todo_state(self):   return self._todo[0]
    @property
    def todo_text(self):    return self._todo[1]

    @functools.cached_property
    def chat_bytes(self):
        return transcript_bytes(self.transcript)

    @functools.cached_property
    def mem_bytes(self):
        return proc_rss_bytes()
```

### `build_context(...)` — the SHELL's factory (replaces `build_data`)

**Role (read once, applies to every call site):** `build_context` is a **module-level free function** — the factory the SHELL calls to assemble a `Context`. It is NOT a method on `Context`; `Context.__init__` is the dataclass's generated constructor that `build_context` invokes at its `return Context(...)`. Its signature is fixed at **ten parameters** in this exact order — `build_context(raw, config, theme, cols, lines, dim_assumed, t_start, effort, home, claude_dir)` — and every call site in this plan (the `build_data` shim, `safe_render`, `_dry_render_failures`, and the FR-R.2 test) uses precisely this signature. The first positional argument is named `config` in the definition; call sites pass whatever local holds the config (`cfg` or `config`) positionally into that slot — both are the same `Config` object, there is no parameter drift.

Pure assembly of eager fields from `raw` + `config` + resolved per-render inputs. No env reads (the SHELL already resolved `env`-derived inputs via CONFIG-block resolvers and passes them in):

```python
def build_context(raw, config, theme, cols, lines, dim_assumed, t_start,
                  effort, home, claude_dir):
    """Assemble the per-render Context from the parsed status JSON and the
    already-resolved per-render inputs. Segment-agnostic and env-free: every
    env read happened in the CONFIG block; the SHELL hands the resolved values
    here. Expensive probes are deferred to Context's cached_property members."""
    model = raw.get("model") or {}
    cost = raw.get("cost") or {}
    ctx_win = raw.get("context_window") or {}
    workspace = raw.get("workspace") or {}
    work_dir = os.path.abspath(workspace.get("current_dir") or ".")
    transcript = raw.get("transcript_path") or ""
    session = raw.get("session_id") or (
        os.path.splitext(os.path.basename(transcript))[0] if transcript else "")
    return Context(
        raw=raw, config=config, theme=theme,
        cols=cols, lines=lines, dim_assumed=dim_assumed, t_start=t_start,
        model_name=model.get("display_name", ""),
        model_id=model.get("id", "unknown"),
        effort=effort, work_dir=work_dir, home=home,
        clock=time.strftime("%H:%M"),
        added=cost.get("total_lines_added") or 0,
        removed=cost.get("total_lines_removed") or 0,
        cost=cost.get("total_cost_usd") or 0,
        total_ms=cost.get("total_duration_ms") or 0,
        api_ms=cost.get("total_api_duration_ms") or 0,
        context_pct=int(ctx_win.get("used_percentage") or 0),
        context_max=ctx_win.get("context_window_size") or 0,
        rate_limits=raw.get("rate_limits") or {},
        transcript=transcript, session=session, claude_dir=claude_dir,
    )
```

### Builder contract after the overhaul

`seg_x(ctx, avail, theme) -> str | None`. Body reads `ctx.<field>` (attribute access; D4) instead of `data['<field>']` / `data.get('<field>')`. `avail` and `theme` stay parameters (`avail` is per-position; `theme` is also `ctx.theme` but kept as a param to preserve the 96 unchanged `_data(` call sites). External providers read `ctx.raw` and `ctx.work_dir`.

---

## Phase 0: Branch + baseline

### Task 0: Confirm green baseline on the working branch

**Files:** none (verification only)

- [ ] **Step 1: Confirm the working branch**

Run: `git branch --show-current`
Expected: `refactor/status-line-architecture` (already created off `main`). If not, run `git checkout main && git checkout -b refactor/status-line-architecture`.

- [ ] **Step 2: Confirm the full suite + golden are green before any edit**

Run: `make test`
Expected: all suites pass (543 tests), `bash tests/test_install.sh` passes.

Run: `python3 -m unittest tests.test_status_line.TestGoldenOutput -v`
Expected: `OK` (golden byte-identical).

- [ ] **Step 3: Confirm the gate is green**

Run: `make validate`
Expected: all hooks pass (ruff, pylint, pyright basic, vulture, shellcheck).

- [ ] **Step 4: Commit the plan**

```bash
git add docs/superpowers/plans/2026-06-21-status-line-architecture-pattern.md
git commit -m "docs(plan): status-line architecture-pattern implementation plan"
```

---

## Phase 1: Config boundary (FR-A.1, D6)

**Goal:** one `Config` carrying stable settings + resolved cache paths; every `env.get`/`os.environ` token lives only in the CONFIG block (plus the single SHELL capture). Derived path helpers become `Config` fields.

**End-state check:** `grep -nE 'os\.environ|env\.get' tools/status-line.py` returns only (a) the single `env = os.environ` capture in `main`, and (b) lines physically inside CONFIG-block functions (`env_bool`, `config_path`, `_load_toml` callers, `_resolve_*`, `_segments_dir`, `_cache_base`, `terminal_size`, `resolve_effort`, `load_config`).

### Task 1.1: Resolve cache paths + segments dir onto `Config`

**Files:**
- Modify: `tools/status-line.py` (the `Config` namedtuple L150; `load_config` L285-346; `_cache_base` L406-409; `_segments_cache_dir` L412-414; `_segments_dir` L417-424; `discover_external` L427-469)
- Test: `tests/test_status_line.py`, `tests/test_external_segments.py`

- [ ] **Step 1: Extend the `Config` namedtuple with `cache_base` + `segments_dir`**

Replace L150-151:

```python
Config = namedtuple(
    "Config",
    "segments layout palette ramps git external cache_base segments_dir",
    defaults=(None, None, "", ""),
)
```

- [ ] **Step 2: Resolve and store the two paths in `load_config`; delete the standalone helpers**

In `load_config` (after `raw = _load_toml(config_path(env))`, reusing the already-computed `ext_dir`), add `cache_base` resolution and pass both new fields into the returned `Config(...)`:

```python
    ext_dir, ext_ttl = _resolve_external(raw, env)   # ext_dir is the providers dir
    cache_base = _cache_base(env)
    ...
    return Config(segments=segments, layout=layout, palette=palette, ramps=ramps,
                  git=git, external=external,
                  cache_base=cache_base, segments_dir=ext_dir)
```

`default_config()` (L154-159) does not read env; leave its `cache_base`/`segments_dir` at the `""` defaults (callers that need them go through `load_config`).

After `load_config` calls `_cache_base(env)` and `_resolve_external` (which calls `_segments_cache_dir`), these standalone helpers become callers-only-from-one-place wrappers. Update `discover_external` (L427) to receive `segments_dir` and `cache_dir` from its caller rather than re-resolving from env — replace the internal `cache_dir = _segments_cache_dir(env)` call with a parameter. Then **delete** both `_cache_base` (L406-409) and `_segments_cache_dir` (L412-414): their values now live on `Config.cache_base` and `Config.segments_dir`. The `_cache_base` call remaining in `_git_cache_path` (L1298) is removed in Task 1.2 (which routes the git cache through `Config.cache_base` instead).

- [ ] **Step 3: Run the config-resolution tests**

Run: `python3 -m unittest tests.test_status_line -k Config -v` and `python3 -m unittest tests.test_external_segments -v`
Expected: PASS. (`Config(...)` keyword construction in tests still works — new fields default. `cfg._replace(...)` unaffected.)

- [ ] **Step 4: Run golden + full status-line module**

Run: `python3 -m unittest tests.test_status_line -q`
Expected: OK (golden byte-identical; no output change — only new unused-yet fields).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py
git commit -m "refactor(config): resolve cache_base + segments_dir onto Config (FR-A.1)"
```

### Task 1.2: Pass the `Config` object to the git probe; read `cache_base` + `cache_ttl` from it

**Design rule (locked, from the maintainer):** `load_config` is the **only** method that reads
env. It produces the immutable `Config`, which carries both `cache_base` and the git
`cache_ttl`. **Anything that needs the cache is handed the `Config` object** and reads
`config.cache_base` / `config.git["cache_ttl"]` from it — no consumer re-resolves by calling
`_cache_base(env)` at a use site, and no consumer is passed a bare path/ttl string "in some other
way." This pulls Task 3.2's `git_snapshot(work_dir, config)` contract forward to here; Task 3.2 is
then left with only the `untracked`/`want_worktree` knob removal.

**Files:**
- Modify: `tools/status-line.py` (`_git_cache_path` L1294-1298; `_worktree_info_cached` L1301-1322; `git_snapshot` L1325-1355; `build_data`'s `_git()` thunk + signature; `safe_render`; `_dry_render_failures`)
- Test: `tests/test_status_line.py` (git-snapshot tests around L1408+, L947+; `build_data` callers)

- [ ] **Step 1: Change `_git_cache_path` to take a resolved `cache_base` string (internal helper)**

The two internal helpers stay value-typed (they receive the already-resolved string from
`git_snapshot`); only the public `git_snapshot` entry is `Config`-aware.

```python
def _git_cache_path(work_dir, cache_base):
    """Per-work_dir cache file for the worktree probe under <cache_base>/git/."""
    key = hashlib.sha1(os.path.abspath(work_dir).encode()).hexdigest()[:16]
    return os.path.join(cache_base, "git", key)
```

- [ ] **Step 2: `git_snapshot` takes the `Config` object and derives `cache_base` + `ttl` from it**

`_worktree_info_cached(work_dir, ttl, cache_base)` calls `_git_cache_path(work_dir, cache_base)`
(unchanged — value-typed). `git_snapshot` replaces the `ttl=…, env=None`/`cache_base=""` tail with a
single `config` parameter and reads both knobs off it:

```python
def git_snapshot(work_dir, config=None, untracked=True, want_worktree=True):
    """The single git probe behind branch/dirty/worktree. `config` is the resolved
    Config object — the probe reads its cache TTL and cache_base FROM it (never from
    env, never as bare args). config=None (direct/test calls with no Config) falls
    back to the built-in defaults. (untracked/want_worktree stay for now — Task 3.2
    removes them once laziness fully gates the call.)"""
    ttl = (config.git or {}).get("cache_ttl", _GIT_CACHE_TTL) if config else _GIT_CACHE_TTL
    cache_base = config.cache_base if config else ""
    ...  # body unchanged except _worktree_info_cached(work_dir, ttl, cache_base)
```

- [ ] **Step 3: Hand `build_data` the `Config` object; drop the bare `git_ttl` param**

`build_data` currently takes `(raw, env, t_start=None, git_ttl=_GIT_CACHE_TTL)` and its `_git()`
thunk calls `git_snapshot(work_dir, ttl=git_ttl, env=env)`. Change the signature to
`build_data(raw, env, cfg, t_start=None)` (the `Config` is passed by contract) and the thunk to
`git_snapshot(work_dir, cfg)`. Update the two production callers — `safe_render` and
`_dry_render_failures` both already hold `cfg`, so they pass it directly (and drop the
`git_ttl=(cfg.git or {}).get("cache_ttl", …)` argument they used to compute). In Phase 2 this same
`cfg` becomes `Context.config`, and `Context._git` calls `git_snapshot(self.work_dir, self.config)`
— identical contract, so this is forward motion, not throwaway.

- [ ] **Step 4: Migrate the coupled git/`build_data` tests to pass a `Config`**

In `tests/test_status_line.py`: direct `git_snapshot(work_dir, env=…)` / `git_snapshot(…, ttl=…)`
calls become `git_snapshot(work_dir, cfg)` where `cfg = sl.default_config()._replace(cache_base=tmp,
git={"cache_ttl": N})`. `build_data(raw, env, git_ttl=…)` calls become `build_data(raw, env, cfg)`.
Search: `grep -n 'git_snapshot\|_git_cache_path\|_worktree_info_cached\|build_data' tests/test_status_line.py`
and update each. The ttl/cache assertions stay identical — they now flow through `cfg` instead of
bare args.

- [ ] **Step 5: Verify env is read only by the loader; no render-path re-resolution**

Run: `grep -n '_segments_cache_dir' tools/status-line.py` → no output (deleted in Task 1.1; stays gone).

Run: `grep -n '_cache_base(' tools/status-line.py`. Expected callers: `load_config` (resolves
`Config.cache_base` — the one legitimate env→path read) and `validate_config_file` (CLI validator,
a PRD non-goal — acceptable as a config-layer reader). **No `_cache_base(env)` inside `build_data`,
`git_snapshot`, any `seg_*`, probe, or render-path function** — those now receive the `Config`
object and read `config.cache_base`. Run `grep -n 'git_snapshot(' tools/status-line.py tests/*.py`
and confirm every call passes a `Config` (or `None` for a deliberate default-only direct call),
never `env=`/`cache_base=`/`ttl=`.

- [ ] **Step 6: Run the git tests + golden**

Run: `python3 -m unittest tests.test_status_line -k 'git or Git or worktree or Worktree' -v`
Expected: PASS.
Run: `python3 -m unittest tests.test_status_line.TestGoldenOutput -v`
Expected: OK.

- [ ] **Step 7: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "refactor(git): pass Config to git_snapshot; read cache_base + ttl off the object (FR-A.1)"
```

### Task 1.3: Consolidate the single `os.environ` capture in the SHELL

**Files:**
- Modify: `tools/status-line.py` (`main` L2183-2200)
- Test: none new (covered by existing CLI/integration tests)

- [ ] **Step 1: Capture `os.environ` once and thread `env`**

In `main`, replace the five `os.environ` references with one capture and pass `env` to each consumer:

```python
def main():
    t0 = time.perf_counter_ns()
    env = os.environ                       # the single SHELL boundary read
    args = parse_args(sys.argv[1:])
    if args.check is not _NO_CHECK:
        sys.exit(cmd_check(args.check, env))
    if args.doctor:
        sys.exit(cmd_doctor(env))
    cfg = load_config(env)
    theme = build_theme(cfg)
    if args.print_config:
        print(cmd_print_config(cfg, env))
        return
    try:
        raw = json.load(sys.stdin)
    except (ValueError, OSError):
        raw = {}
    print("\n".join(safe_render(raw, env, cfg, theme, t0)))
```

(`safe_render`'s `env` param is removed in Phase 2 when it builds a `Context`; for now keep the signature stable.)

- [ ] **Step 2: Verify the env grep AC for Phase 1**

Run: `grep -nE 'os\.environ|env\.get' tools/status-line.py`
Expected: **two** `os.environ` occurrences, both legitimate — (1) the single `env = os.environ`
SHELL-boundary capture in `main` (the config read), and (2) `env = dict(os.environ)` inside
`_run_provider`, which builds the **subprocess environment** handed to an external provider (mirror
of the real process env + the `AI_KIT_SEGMENT_*` vars) — NOT a config read, and correctly left as-is
(Phase 2 / Task 2.2 migrates `_run_provider` to take `ctx`). Every `env.get` line is inside a
CONFIG-block boundary resolver (`env_bool`, `config_path`, `_resolve_external`, `_segments_dir`,
`_cache_base`, `terminal_size`, `resolve_effort`, `load_config`). **No `env.get`/`os.environ` for
config inside any `seg_*`, probe, `build_data`, `git_snapshot`, or render-path function.**
(`terminal_size` and `resolve_effort` still hold env reads — they are CONFIG/SHELL boundary
resolvers; Phase 2 moves their *results* onto `Context` while the reads stay here.)

- [ ] **Step 3: Run the full suite + gate**

Run: `make test`
Expected: all green.
Run: `make validate`
Expected: green.

- [ ] **Step 4: Commit**

```bash
git add tools/status-line.py
git commit -m "refactor(shell): single os.environ capture in main; thread env (FR-A.1)"
```

**Phase 1 deliverable check:** `grep` shows env access only in the CONFIG block + the one SHELL capture; suite + golden green.

---

## Phase 2: `Context` replaces `build_data` + `_LazyData` (FR-A.2, D1, D4, D6)

**Goal:** dissolve `build_data`/`_LazyData` into the `Context` dataclass with `cached_property` probes; segments read `ctx.<field>`; `failed`/`slowest` live on `ctx`; FR-R.2 proven by an explicit test.

### Task 2.1: Add `Context` + `build_context`; keep `build_data` temporarily as a thin shim

**Files:**
- Modify: `tools/status-line.py` (add `import functools`, `from dataclasses import dataclass, field` near the top imports L12-29; add `Context` + `build_context` in the CONTEXT region, replacing `_LazyData` L1835-1862 and `build_data` L1865-1952)
- Test: `tests/test_status_line.py`

- [ ] **Step 1: Add imports**

After the existing imports (around L22), add:

```python
import functools
from dataclasses import dataclass, field
```

- [ ] **Step 2: Add the `Context` dataclass**

Insert the full `Context` dataclass from the **Target architecture** section above, in place of `_LazyData` (delete `_LazyData` L1835-1862). Place it under a `# ═══ CONTEXT ...` banner (final banner placement is Phase 4; for now keep it where `_LazyData`/`build_data` lived).

- [ ] **Step 3: Add `build_context`**

Insert the full `build_context(...)` from the **Target architecture** section in place of `build_data` (delete the old `build_data` body L1865-1952).

- [ ] **Step 4: Add a temporary compatibility shim for `build_data`**

So Task 2 can land incrementally (callers migrate in 2.2/2.3), keep a thin shim that resolves the
per-render inputs and delegates. After the revised **Task 1.2**, `build_data` already takes the
`Config` object as `(raw, env, cfg, t_start)` — so the shim receives `cfg` and reads
`cfg.cache_base` / `cfg.git` through `build_context`; it does **not** resolve any cache path itself.
This shim is **deleted in Task 2.4**:

```python
def build_data(raw, env, cfg, t_start=None):
    """DEPRECATED shim (removed in Task 2.4): resolve the per-render SHELL inputs
    (terminal size, HOME, claude_dir, effort) and build a Context from the passed
    Config. Returns (ctx, cols, lines) to match the old build_data contract. The
    cache base + git ttl come from `cfg` (the Config object) — never re-resolved."""
    cols, lines, assumed = terminal_size(env)
    home = env.get("HOME", "")
    claude_dir = env.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
    ctx = build_context(raw, cfg, default_theme(), cols, lines, assumed, t_start,
                        effort=resolve_effort(raw, env), home=home, claude_dir=claude_dir)
    return ctx, cols, lines
```

> Note: this shim reads env only for the per-render SHELL inputs (`terminal_size`, `HOME`,
> `CLAUDE_CONFIG_DIR`, `resolve_effort`) — all CONFIG/SHELL-boundary resolvers — and gets
> `cache_base` + git `cache_ttl` from the `Config` object it was handed, never by re-resolving. The
> real render path (Task 2.2) does not use this shim — it goes through `safe_render` →
> `build_context` with `cfg.cache_base` already resolved by `load_config`.

- [ ] **Step 5: Run py_compile + the builder unit tests (expect failures to triage next)**

Run: `python3 -m py_compile tools/status-line.py`
Expected: compiles. (Segments still use `data[...]`; they will work against `Context` only after Task 2.2 flips them to attribute access. Until then, builder tests that read git fields may fail — that is expected and fixed in 2.2/2.3. Do NOT commit a red suite; this task's commit comes after Step 6 confirms only the *intended* surface is red.)

- [ ] **Step 6: Stage the wiring; defer commit to Task 2.2**

This task introduces types without yet flipping consumers. Proceed directly to Task 2.2 and commit them together (single logical unit: "introduce Context, migrate render path + segments"). Do not leave a broken commit.

### Task 2.2: Flip segments + render path to `Context` (attribute access)

**Files:**
- Modify: `tools/status-line.py` — every `seg_*` (L949-1166); `safe_build` (L1624-1638); `_crown_slowest` (L1641-1650); `pack_line` (L1653-1707); `render` (L1722-1739); `safe_render` (L2169-2180); `_run_provider` (L553-575); `_dry_render_failures` (L2089-2106); `make_external_builder` (L1185-1190)
- Test: `tests/test_status_line.py`, `tests/test_external_segments.py`

> **Atomicity note (read before starting Task 2.2):** Steps 1–7 of this task form **one indivisible commit** (Step 9). In particular, the `seg_*` signature/body change (Step 1) and the `_data()` test-helper rewrite (Step 6, which makes `_data()` return a `Context` instead of a dict) MUST land together. The 59 direct `sl.seg_*(_data(...))` call sites in `tests/test_status_line.py` break the instant either side changes alone: flip the segments first and the dict-returning `_data()` feeds them a dict (`AttributeError` on `ctx.<field>`); rewrite `_data()` first and the still-dict-reading segments fail on `Context` (no `__getitem__`). Do not run the suite for green or commit between Step 1 and Step 6 — the only green checkpoint is Step 8, after both are done.

- [ ] **Step 1: Convert every segment from subscript to attribute access (D4)**

Mechanical, per builder. The rename is `data` param kept as-is in the signature (`seg_x(data, avail, theme)` → keep the name `data` OR rename to `ctx`; **rename to `ctx`** for clarity per D3). Replace `data['key']` → `ctx.key` and `data.get('key')`/`data.get('key', d)` → `ctx.key`. The `Context` always defines every attribute (eager field or probe), so `.get(...)` defaults collapse to the attribute. Representative before/after:

```python
# before
def seg_path(data, avail, theme):
    return f"{theme.c('BLUE')}{_display_dir(data['work_dir'], data['home'])}{RESET}"
def seg_branch(data, avail, theme):
    branch = data.get("branch")
    ...
def seg_clock(data, avail, theme):
    return _first_fitting([_icon("⏰", data['clock'])], avail)

# after
def seg_path(ctx, avail, theme):
    return f"{theme.c('BLUE')}{_display_dir(ctx.work_dir, ctx.home)}{RESET}"
def seg_branch(ctx, avail, theme):
    branch = ctx.branch
    ...
def seg_clock(ctx, avail, theme):
    return _first_fitting([_icon("⏰", ctx.clock)], avail)
```

Apply to all 20 `seg_*`. Field-name map (subscript → attribute) is 1:1 with the `Context` fields/properties: `work_dir, home, branch, dirty, is_worktree, wt_name, in_repo, todo_state, todo_text, model_name, model_id, ago, clock, effort, effort_auto, added, removed, cost, total_ms, api_ms, t_start, slowest, context_pct, context_max, cols, lines, dim_assumed, chat_bytes, mem_bytes, rate_limits`. The one dict member that keeps `.get()` is `ctx.raw` (used by external providers).

- [ ] **Step 2: Move `failed`/`slowest` onto `ctx` in the render path**

`_crown_slowest` drops its `failed` param and reads/writes `ctx`:

```python
def _crown_slowest(ctx, key, ns):
    if key in _SLOWEST_META or key in ctx.failed:
        return
    cur = ctx.slowest
    if cur is None or ns > cur[1]:
        ctx.slowest = (key, ns)
```

`safe_build(key, ctx, avail, theme, builders=None)` records into `ctx.failed`:

```python
def safe_build(key, ctx, avail, theme, builders=None):
    builders = builders if builders is not None else _discover_builders()  # Phase 3; until then BUILDERS
    try:
        return builders[key](ctx, avail, theme)
    except Exception:  # pylint: disable=broad-exception-caught
        ctx.failed.add(key)
        named = f"{_WARN}⚠{key}{RESET}"
        return named if visible_width(named) <= avail else f"{_WARN}⚠{RESET}"
```

(In Phase 2 keep `builders` defaulting to `BUILDERS`; Phase 3 swaps the default to discovery.)

`pack_line(keys, ctx, cols, cfg=None, theme=None, builders=None)` — drop the `failed` param; use `ctx.failed`, `ctx.slowest`, and call `_crown_slowest(ctx, key, ns)` and `safe_build(key, ctx, avail, theme, builders)`. `cfg`/`theme` default to `ctx.config`/`ctx.theme` when None:

```python
    cfg = cfg or ctx.config
    theme = theme or ctx.theme
    builders = builders if builders is not None else _builders_for(cfg)
```

`render(ctx, cfg=None, theme=None)` — reads `ctx.cols`/`ctx.lines`, owns one `failed` set on `ctx`:

```python
def render(ctx, cfg=None, theme=None):
    cfg = cfg or ctx.config
    theme = theme or ctx.theme
    builders = _builders_for(cfg)
    for ln in cfg.layout:
        if ctx.lines < ln.min_rows:
            continue
        packed = pack_line(ln.segments, ctx, ctx.cols, cfg, theme, builders)
        if packed:
            ... # accumulate
    diag = diagnostic_line(ctx.failed)
    ...
```

- [ ] **Step 3: Update `_run_provider` + `run_external` + `make_external_builder` to read `ctx`**

First, find all internal callers to ensure no site is missed:

```bash
grep -n '_run_provider\|run_external' tools/status-line.py
```

Expected output (three sites must all be migrated together):
```
553:def _run_provider(spec, data, avail):
578:def run_external(spec, data, avail):
583:        raw_line = _run_provider(spec, data, avail)
1189:        return run_external(spec, data, avail)
```

`_run_provider(spec, ctx, avail)` reads `ctx.raw` and `ctx.work_dir`:

```python
def _run_provider(spec, ctx, avail):
    payload = json.dumps({**(ctx.raw or {}),
                          "segment": {"id": spec.id, "avail_cols": avail,
                                      "line": spec.line, "position": pos}})
    ...
    proc = subprocess.run([spec.path], input=payload, ..., cwd=ctx.work_dir or ".", ...)
```

`run_external(spec, ctx, avail)` at L578 also renames `data` → `ctx` in its signature and passes `ctx` to `_run_provider` at L583:

```python
def run_external(spec, ctx, avail):
    ...
    raw_line = _run_provider(spec, ctx, avail)
    ...
```

`make_external_builder`'s inner closure at L1189 calls `run_external(spec, data, avail)` — rename `data` → `ctx` here too:

```python
def _builder(ctx, avail, theme):
    return run_external(spec, ctx, avail)
```

All three sites (L553, L578/583, L1189) must be updated in the same edit to avoid a `TypeError` when an external segment is active.

- [ ] **Step 4: Rebuild the SHELL render path (`safe_render`) on `build_context`**

```python
def safe_render(raw, env, cfg, theme, t_start):
    try:
        cols, lines, assumed = terminal_size(env)
        home = env.get("HOME", "")
        claude_dir = env.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
        ctx = build_context(raw, cfg, theme, cols, lines, assumed, t_start,
                            effort=resolve_effort(raw, env), home=home, claude_dir=claude_dir)
        return render(ctx)
    except Exception:  # pylint: disable=broad-exception-caught
        return [f"{_WARN}⚠ status-line error — run the doctor: {_doctor_cmd()}{RESET}"]
```

This keeps `env.get`/`terminal_size`/`resolve_effort` reads at the CONFIG boundary (`safe_render` is the SHELL's render entry). The grep AC for env is satisfied: these are boundary resolvers; no env reads leak into `Context`/segments. (Optionally extract the three-line input resolution into a `resolve_render_inputs(raw, env)` CONFIG-block helper returning a small tuple — recommended for D3 tidiness; not required for green.)

- [ ] **Step 5: Update `_dry_render_failures` (doctor) to build a Context**

```python
def _dry_render_failures(cfg, theme, env):
    cols, lines, assumed = terminal_size(env)
    home = env.get("HOME", "")
    claude_dir = env.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
    ctx = build_context(dict(_DOCTOR_SAMPLE), cfg, theme, cols, lines, assumed,
                        time.perf_counter_ns(),
                        effort=resolve_effort(_DOCTOR_SAMPLE, env), home=home, claude_dir=claude_dir)
    for key in BUILDERS:                      # Phase 3 → _discover_builders()
        safe_build(key, ctx, 200, theme)
    return ctx.failed
```

- [ ] **Step 6: Migrate the `_data()` test helper to return a seeded `Context`**

This is the single most important test change — it keeps all 96 `_data(` call sites unchanged. Replace `_data(**over)` (L40-55 in `tests/test_status_line.py`) so it builds a real `Context` and **seeds the probe caches** from the same kwargs the old dict exposed:

```python
def _data(**over):
    eager = {
        "model_name": "Opus 4.8", "model_id": "claude-opus-4-8",
        "effort": "high", "work_dir": "/home/u/proj", "home": "/home/u",
        "clock": "14:30", "added": 12, "removed": 3, "cost": 0.5,
        "total_ms": 65000, "api_ms": 4200, "context_pct": 12,
        "context_max": 1_000_000, "rate_limits": {},
        "cols": 200, "lines": 50, "dim_assumed": False, "t_start": None,
        "transcript": "", "session": "", "claude_dir": "/home/u/.claude",
    }
    # probe-backed defaults (seeded into the cached_property caches below)
    probe_defaults = {
        "branch": "main", "dirty": "modified", "is_worktree": False,
        "in_repo": False, "wt_name": "",
        "ago": "5m 0s ago", "effort_auto": False,
        "todo_state": None, "todo_text": None,
        "chat_bytes": 305000, "mem_bytes": 448_790_528,
    }
    eager_over = {k: over.pop(k) for k in list(over) if k in eager}
    probe_over = {**probe_defaults, **over}        # remaining kwargs are probe fields
    eager.update(eager_over)
    ctx = sl.Context(raw={}, config=sl.default_config(), theme=THEME, **eager)
    # seed the shared git probe so reading ctx.branch/dirty/... never shells out
    ctx.__dict__["_git"] = sl.GitSnapshot(
        in_repo=probe_over["in_repo"], branch=probe_over["branch"],
        dirty=probe_over["dirty"], is_worktree=probe_over["is_worktree"],
        wt_name=probe_over["wt_name"])
    ctx.__dict__["_todo"] = (probe_over["todo_state"], probe_over["todo_text"])
    for k in ("ago", "effort_auto", "chat_bytes", "mem_bytes"):
        ctx.__dict__[k] = probe_over[k]
    return ctx
```

All 96 `_data(` call sites are unchanged — 52 `sl.seg_x(_data(...), avail, THEME)` builder sites and ~44 other callers (`pack_line`, `render`, local assignments). `_data(branch="feat")`, `_data(in_repo=True, is_worktree=True, wt_name="x")`, `_data(effort="")`, `_data(t_start=...)`, `_data(chat_bytes=None)` etc. all still work because the helper routes each kwarg to the right eager field or probe-cache seed.

- [ ] **Step 7: Migrate `build_data` call sites + `data[...]`/positional `failed` args in tests**

In `tests/test_status_line.py` and `tests/test_external_segments.py`:
- `data, cols, lines = sl.build_data(raw, env, ...)` → build a Context. Where the test only needs a Context for rendering, use `ctx = _data(...)` (seeded) or the golden-style `build_context` path (Task 2.8 covers the golden harness). For the segment-agnostic probe tests (`test_status_line.py` L875-960 area, `test_external_segments.py` L364) that assert probe-laziness/git-ttl flow, construct via `build_context` with patched probes and assert on `ctx.<field>` access triggering the probe.
- `data["slowest"]` → `ctx.slowest`; `data.get("slowest", (None,))` → `ctx.slowest or (None,)`. (11 subscript sites in TestSlowestTiming.)
- Remove the positional `failed` arg from `pack_line` (1 site, L1796: `sl.pack_line([...], _data(), 80, cfg, THEME, failed)` → `sl.pack_line([...], ctx, 80, cfg, THEME)`) and from `safe_build` (3 sites, L1763/1772/1782). **Note:** there is no `failed=` keyword argument to grep for — all four sites pass `failed` positionally. Assert the failure state by reading `ctx.failed` after the call.
- `data["cols"], data["lines"] = ...` → pass `cols=/lines=` into `_data(...)` or `build_context(...)`.

Work module-by-module; run after each file.

- [ ] **Step 8: Run the full status-line + external suites + golden**

Run: `python3 -m unittest tests.test_status_line tests.test_external_segments -q`
Expected: OK.
Run: `python3 -m unittest tests.test_status_line.TestGoldenOutput -v`
Expected: OK (byte-identical — the whole point).

- [ ] **Step 9: Commit (single logical unit with 2.1)**

```bash
git add tools/status-line.py tests/test_status_line.py tests/test_external_segments.py
git commit -m "refactor(context): replace build_data/_LazyData with Context dataclass (FR-A.2, D1/D4/D6)"
```

### Task 2.3: Add the explicit FR-R.2 truthful-`slowest` test (FR-A.2 acceptance)

**Files:**
- Test: `tests/test_status_line.py` (add to `TestSlowestTiming`, near L460)

- [ ] **Step 1: Write the probe-cost-captured test**

```python
def test_probe_cost_counted_in_triggering_segment(self):
    # FR-A.2 / FR-R.2: a Context cached_property probe runs synchronously on first
    # read, so its cost lands INSIDE the measured build of the segment that reads
    # it — not amortized to µs. Proven by making the git probe sleep and checking
    # the `branch` segment (which reads ctx.branch) is crowned with a ms-scale time.
    def slow_git(work_dir, **kw):
        time.sleep(0.005)
        return sl.GitSnapshot(in_repo=True, branch="main", dirty="clean",
                              is_worktree=False, wt_name="")
    cfg = sl.default_config()
    cfg.segments.update({"slowest": True, "branch": True})
    # A live Context whose _git probe is NOT seeded, so reading ctx.branch fires it.
    ctx = sl.build_context(
        raw={"workspace": {"current_dir": "/tmp"}}, config=cfg, theme=THEME,
        cols=200, lines=50, dim_assumed=False, t_start=sl.time.perf_counter_ns(),
        effort="high", home="/home/u", claude_dir="/home/u/.claude")
    with mock.patch.object(sl, "git_snapshot", side_effect=slow_git):
        sl.pack_line(["branch"], ctx, 200, cfg=cfg)
    # Confirm the cached_property actually ran during pack_line (not prematurely during build_context).
    # If _git is absent from __dict__, the probe was never triggered — the mock wouldn't have fired
    # and ns would be sub-ms, silently defeating the invariant.
    self.assertIsNotNone(ctx.__dict__.get("_git"))
    name, ns = ctx.slowest
    self.assertEqual(name, "branch")
    self.assertGreaterEqual(ns, 4_000_000)   # >= ~4ms: probe cost is inside the build
```

- [ ] **Step 2: Run it**

Run: `python3 -m unittest tests.test_status_line.TestSlowestTiming.test_probe_cost_counted_in_triggering_segment -v`
Expected: PASS.

- [ ] **Step 3: Run the whole `TestSlowestTiming` class + golden**

Run: `python3 -m unittest tests.test_status_line.TestSlowestTiming -v`
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_status_line.py
git commit -m "test(slowest): assert probe cost is captured in the triggering build (FR-A.2)"
```

### Task 2.4: Remove the `build_data` shim

**Files:**
- Modify: `tools/status-line.py` (delete the shim from Task 2.1 Step 4)
- Test: `tests/test_external_segments.py`, `tests/test_status_line.py`

- [ ] **Step 1: Confirm no production caller of `build_data` remains**

Run: `grep -n 'build_data' tools/status-line.py`
Expected: only the shim definition (no callers in render/doctor paths after 2.2). If a caller remains, migrate it to `build_context` first.

- [ ] **Step 2: Confirm no test references `sl.build_data`**

Run: `grep -rn 'build_data' tests/`
Expected: empty (all migrated in 2.2 Step 7). If any remain, migrate them.

- [ ] **Step 3: Delete the shim**

Remove the `def build_data(...)` shim entirely.

- [ ] **Step 4: Run the full suite + golden + gate**

Run: `make test`
Expected: all green.
Run: `make validate`
Expected: green (note: pylint design thresholds are still the ratcheted values; the `build_data`/`pack_line` arg-count wins land via Phase 5).

- [ ] **Step 5: Verify Phase 2 ACs**

Run: `grep -nE '_LazyData|def build_data' tools/status-line.py`
Expected: empty (both gone).
Run: `grep -nE 'ctx\[|config\[|self\[' tools/status-line.py`
Expected: empty (no subscript on our types; `ctx.raw[...]`/`.get` is on the dict member, which is fine — verify any hit is `ctx.raw.get(...)` style, not `ctx[...]`).

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py
git commit -m "refactor(context): remove build_data shim — Context is the only data path (FR-A.2)"
```

**Phase 2 deliverable check:** `build_data` + `_LazyData` gone; `slowest` still ms-scale (proven by 2.3); segments read `ctx.<attr>`; suite + golden green.

---

## Phase 3: Convention registry + encapsulated helpers (FR-A.3, FR-A.4, D7)

**Goal:** auto-derive the builder map from `seg_*` functions (drop the hand-maintained `BUILDERS` literal); the git probe owns its TTL/caching so callers never thread knobs.

### Task 3.1: Auto-discover builders from `seg_*` functions

**Files:**
- Modify: `tools/status-line.py` (replace `BUILDERS` literal L1172-1182; `_builders_for` L1193-1200; `safe_build` default; `_dry_render_failures`; `validate_config_file` L2033; `cmd_doctor` L2104,2131)
- Test: `tests/test_status_line.py` (the 11 `BUILDERS` sites: L408-409, 530, 600, etc.)

- [ ] **Step 1: Add the discovery function**

The homologous convention: a builder is a module-level callable named `seg_<key>`; its key is the suffix. Discover once (module import time is fine; or memoize). Place under the SEGMENTS registry banner, replacing the literal:

```python
def _discover_builders():
    """The built-in builder map, derived by convention from this module's
    `seg_<key>` functions (the homologous suffix is the segment key). Replaces the
    hand-maintained BUILDERS literal (FR-A.3, D7): adding a `seg_x` auto-registers
    it. SEGMENTS/LAYOUT stay explicit defaults tables — discovery removes only the
    redundant name→fn list, never the tables that encode intent."""
    g = globals()
    return {name[len("seg_"):]: fn
            for name, fn in g.items()
            if name.startswith("seg_") and callable(fn)}


BUILDERS = _discover_builders()   # module-level snapshot; same object shape as before
```

Keeping a module-level `BUILDERS = _discover_builders()` preserves the 11 test references (`sl.BUILDERS`, `dict(sl.BUILDERS)`, `key in sl.BUILDERS`) **unchanged** — they now read the discovered map. `_builders_for(cfg)` keeps merging externals onto `dict(BUILDERS)`.

- [ ] **Step 2: Delete the "add it to BUILDERS" maintenance instruction**

Update the contract comment near the old literal (L921) and the HOW TO CUSTOMIZE block (L1790-1798): adding a segment is now (1) write `seg_x`, (2) place in a LAYOUT line, (3) add a SEGMENTS flag. Remove the "Register it: add to BUILDERS" step (it is automatic).

- [ ] **Step 3: Confirm the discovered map equals the old literal**

Add a one-off assertion test (keep it — it guards the convention):

```python
def test_discovered_builders_cover_segments(self):
    # Every SEGMENTS key has a discovered seg_* builder, and discovery finds no
    # stray builders. Guards the convention registry (FR-A.3).
    self.assertEqual(set(sl.BUILDERS), set(sl.SEGMENTS))
```

(Place in the registry test class near L408. `SEGMENTS` keys and `seg_*` suffixes are 1:1 — verified against the current 20 builders.)

- [ ] **Step 4: Run the registry + render tests + golden**

Run: `python3 -m unittest tests.test_status_line -k 'Builder or Registry or Segment or Golden' -v`
Expected: PASS.
Run: `python3 -m unittest tests.test_status_line tests.test_external_segments -q`
Expected: OK.

- [ ] **Step 5: Verify the FR-A.3 AC**

Run: `grep -nE '^\s*"path": seg_path' tools/status-line.py`
Expected: empty (the hand-maintained literal is gone; only `BUILDERS = _discover_builders()` remains).

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "refactor(registry): auto-discover BUILDERS from seg_* functions (FR-A.3, D7)"
```

### Task 3.2: Encapsulate the git probe's caching policy (FR-A.4)

> **Already done in Task 1.2:** `git_snapshot(work_dir, config, …)` and reading
> `config.cache_base` + `config.git["cache_ttl"]` off the object. This task only **removes the
> remaining `untracked`/`want_worktree` knobs** — the last per-call policy the probe should own
> itself.

**Files:**
- Modify: `tools/status-line.py` (`git_snapshot`; `Context._git`)
- Test: `tests/test_status_line.py` (git tests)

- [ ] **Step 1: Remove the `untracked`/`want_worktree` knobs**

`git_snapshot(work_dir, config, untracked=True, want_worktree=True)` still exposes the
`untracked`/`want_worktree` knobs. After Phase 2 the only production caller is `Context._git`, which always probes in full (laziness — not flags — gates the call; a disabled git segment never reads a git field, so `_git` never runs). Drop those two params: the probe owns its policy entirely, reading TTL + cache location from the `Config` it was already given in Task 1.2.

`Context._git` already passes a single `config` (written in Phase 2):

```python
    @functools.cached_property
    def _git(self):
        return git_snapshot(self.work_dir, self.config)
```

And `git_snapshot(work_dir, config)` reads `(config.git or {}).get("cache_ttl", _GIT_CACHE_TTL)` and `config.cache_base` internally; it always does the full untracked walk + worktree probe (the historical `untracked=False`/`want_worktree=False` fast-paths were per-segment gating that laziness now subsumes). Keep `_branch_from_porcelain`, `_worktree_info_cached`, `_git_worktree_info` as the internal helpers (grouped under one HELPERS banner in Phase 4).

> Caution: confirm via the golden that always-full probing does not change output (it cannot — the golden mocks `git_snapshot` wholesale; the real-render fidelity is covered by `make test`'s worktree/sysmem e2e suites). If any non-golden test asserted `untracked=False` behavior, migrate it to assert the full-probe result (behavior for the rendered segments is identical).

- [ ] **Step 2: Migrate git tests to the new signature**

`grep -n 'git_snapshot' tests/test_status_line.py` and update calls to `git_snapshot(work_dir, cfg)` where `cfg = sl.default_config()._replace(git={"cache_ttl": N}, cache_base=tmp)`. Tests asserting the ttl flow (L947-960) assert through `cfg.git["cache_ttl"]`.

- [ ] **Step 3: Run git + worktree + sysmem suites + golden**

Run: `python3 -m unittest tests.test_status_line -k 'git or Git or worktree or Worktree' -v`
Expected: PASS.
Run: `python3 -m unittest tests.test_worktree_e2e tests.test_sysmem_e2e -v`
Expected: PASS.
Run: `python3 -m unittest tests.test_status_line.TestGoldenOutput -v`
Expected: OK.

- [ ] **Step 4: Verify FR-A.4 AC**

Run: `grep -nE 'untracked=|want_worktree=' tools/status-line.py`
Expected: empty (no caller threads probe knobs).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "refactor(git): probe owns its TTL/cache policy; callers pass Config (FR-A.4)"
```

**Phase 3 deliverable check:** adding a `seg_x` auto-registers; git probe self-encapsulated; suite + golden green.

---

## Phase 4: Block/structure reorg (FR-A.5, D2, D3)

**Goal:** the six banner-delimited blocks in dependency order; D3 naming (noun-grouping `_git_*`/`_cache_*`, `# ═══` banners); externals in their own delimited block; an in-file contract note describing the pattern. **No behavior change — pure motion.**

### Task 4.1: Reorder the file into the six blocks

**Files:**
- Modify: `tools/status-line.py` (whole-file section motion)
- Test: full suite + golden

- [ ] **Step 1: Establish the six top-level banners in dependency order**

```
# ═══ 1. SHELL ═══         main(), arg parsing, the single os.environ capture, stdin read, print
# ═══ 2. CONFIG ═══        env/TOML → Config (the ONLY env-reading block): env_bool, config_path,
#                          _load_toml, _resolve_*, _segments_dir, _cache_base, terminal_size,
#                          resolve_effort, effort_setting_is_auto's settings reader, load_config,
#                          default_config, the *_DEFAULTS / SEGMENTS / LAYOUT tables, Config
# ═══ 3. CONTEXT ═══       Context dataclass, build_context, resolve_render_inputs
# ═══ 4. HELPERS ═══       probes own their caching: git_snapshot + git helpers, proc_rss_bytes +
#                          readers, transcript/todo readers, display-width, color engine,
#                          formatters, rate helpers
# ═══ 5. SEGMENTS ═══      seg_* builders, _discover_builders, _builders_for, external block
# ═══ 6. LAYOUT / PACK ═══ pack_line, safe_build, _crown_slowest, render, safe_render,
#                          diagnostic_line
```

Move existing functions under the right banner. This is cut-and-paste only — **do not edit any function body**. The CLI introspection functions (`cmd_check`, `cmd_doctor`, `cmd_print_config`, `validate_config_file`, `_dry_render_failures`, `_DOCTOR_SAMPLE`, `parse_args`) form a final `# ═══ CLI introspection ═══` block after PACK (out of the render-path scope but kept in-file, D2).

**Move one block at a time, and checkpoint after each move** — do not relocate all six blocks before testing. Phase 4 reorders large swaths of a ~2200-line file; a name-order-dependent reference (e.g. `BUILDERS = _discover_builders()` landing above the `seg_*` defs it scans) or a banner comment that accidentally splits a `def` produces a silent failure that is far cheaper to bisect one move at a time. After relocating each banner's contents (SHELL, then CONFIG, then CONTEXT, then HELPERS, then SEGMENTS, then LAYOUT/PACK, then CLI introspection), run this checkpoint before starting the next block:

```bash
python3 -m py_compile tools/status-line.py \
  && python3 -m unittest tests.test_status_line.TestGoldenOutput -v \
  && python3 -m unittest tests.test_status_line tests.test_external_segments -q
```
Expected after every single move: compiles, golden `OK`, suites `OK`. If a move goes red, the offending block is the one you just moved — fix or revert it before moving the next.

- [ ] **Step 2: Give externals their own delimited block (D-A.5)**

Group `ExtSpec`, `_SEG_HEADER_RE`, `parse_segment_header`, `discover_external`, `_cache_read`/`_cache_write`/`_run_provider`/`run_external`, `_sanitize_external`/`_truncate_visible`, `make_external_builder` under `# ── External drop-in segments (E4c) ──` within (or adjacent to) the SEGMENTS block.

- [ ] **Step 3: Verify motion changed nothing — compile + full suite + golden**

Run: `python3 -m py_compile tools/status-line.py`
Expected: compiles (no forward-reference breakage — module-level `BUILDERS = _discover_builders()` must sit AFTER all `seg_*` defs; `Config` namedtuple must be defined before `default_config`; `Context` references helpers it calls at *runtime*, not import time, so ordering of helper defs vs. the class is flexible, but keep CONTEXT after the names it calls are defined OR rely on late binding — verify by compile + run).
Run: `make test`
Expected: all green.
Run: `python3 -m unittest tests.test_status_line.TestGoldenOutput -v`
Expected: OK.

- [ ] **Step 4: Apply D3 naming touch-ups**

Where helpers are not yet noun-grouped, rename to the `_git_*` / `_cache_*` / `_rate_*` conventions (private `_` prefix; no heavy `_seg_helper_*`). Use a rename that updates all references in one move; re-run the suite after each rename. Keep public/test-referenced names (`git_snapshot`, `pack_line`, `safe_build`, `render`, `BUILDERS`, `Context`, `Config`, `build_context`, all `seg_*`) **unchanged** — they are the test surface.

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py
git commit -m "refactor(structure): six banner-delimited blocks in dependency order (FR-A.5, D2/D3)"
```

### Task 4.2: Add the in-file architecture contract note

**Files:**
- Modify: `tools/status-line.py` (module docstring L2-9 + a contract banner)

- [ ] **Step 1: Write the contract note**

At the top (after the module docstring), add a short note stating the pattern so a contributor can follow it:

```python
# ARCHITECTURE — functional core / imperative shell, one file, six blocks:
#   SHELL     side effects only (env capture, stdin, print); calls the core.
#   CONFIG    the ONLY block that reads env/TOML → one immutable Config (stable
#             settings + resolved cache paths). SEGMENTS/LAYOUT/*_DEFAULTS are the
#             explicit intent tables.
#   CONTEXT   per-render Context: eager inputs + cached_property probes (git/todo/
#             ago/rss/effort-auto) + render bookkeeping (failed, slowest). Probes
#             run on first attribute read, so their cost lands in the measured
#             build of the reading segment (FR-R.2). Attribute access only (D4).
#   HELPERS   probes own their caching/TTL; read only what ctx/config give them.
#   SEGMENTS  seg_x(ctx, avail, theme) -> str | None, self-sourcing; the builder
#             map is auto-discovered from seg_* names (add a seg_x, it registers).
#   PACK      fully segment-agnostic: keys, the discovered map, widths, two passes.
# To add a segment: write seg_<key>(ctx, avail, theme); add <key> to a LAYOUT line;
# add <key>: True to SEGMENTS. The registry wires itself.
```

- [ ] **Step 2: Run the full suite + golden (note must not change output)**

Run: `make test` → green. `python3 -m unittest tests.test_status_line.TestGoldenOutput -v` → OK.

- [ ] **Step 3: Commit**

```bash
git add tools/status-line.py
git commit -m "docs(status-line): in-file architecture contract note (FR-A.5)"
```

**Phase 4 deliverable check:** six blocks present; externals delimited; contract note in file; suite + golden green.

---

## Phase 5: Strict typing — LAST (FR-A.6, D4, D5)

**Goal:** full type hints; pyright `strict` on `status-line.py`; the `obj[key]` subscript ban on our types; pylint design thresholds at defaults for the render path. Resolve every finding by **fixing**, not suppressing.

### Task 5.1: Add type hints throughout the render path

**Files:**
- Modify: `tools/status-line.py` (annotate signatures + the `Context`/`Config` fields)
- Test: full suite

- [ ] **Step 1: Annotate the data types first**

`Context` fields are already annotated (Target architecture). Add a `TypeAlias` for the recurring shapes and annotate `Config` field access points. Define near the top:

```python
from typing import Callable, Optional
Builder = Callable[["Context", int, "Theme"], Optional[str]]
```

- [ ] **Step 2: Annotate every function signature in the render path**

Add parameter + return annotations to: all `seg_*` (`(ctx: Context, avail: int, theme: Theme) -> str | None`), `build_context`, `pack_line`, `safe_build`, `_crown_slowest`, `render`, `safe_render`, `git_snapshot`, `_discover_builders` (`-> dict[str, Builder]`), `_builders_for`, the formatters, the color engine, `terminal_size` (`-> tuple[int, int, bool]`), `resolve_effort`, `load_config` (`-> Config`), etc. Annotate local variables only where pyright strict requires it.

- [ ] **Step 3: Iterate against pyright strict locally (file-scoped)**

Add a file-level opt-in near the top of `tools/status-line.py` so only this file goes strict (keeps out-of-scope `setup.py` at the project's `basic` mode — D5 isolation, PRD non-goal "no change to setup.py").

**Exact placement:** the file begins shebang (L1) → module docstring (L2–9) → `# pylint: disable=invalid-name` (L10). A `# pyright: strict` comment is a file-scoped override that pyright honors anywhere in the file's leading comment region, but it must NOT displace the shebang (line 1 must stay `#!/usr/bin/env python3` or the installed script breaks). Insert it as its **own line immediately after the closing `"""` of the module docstring and before the existing `# pylint: disable` line** — i.e. it becomes the new L10, pushing the pylint-disable to L11:

```python
"""...module docstring ends here..."""
# pyright: strict
# pylint: disable=invalid-name  # installed script name is hyphenated (status-line.py)
```

This file-scoped comment **overrides** the project-wide `typeCheckingMode = "basic"` (`pyproject.toml` L100) for this one file only; it does not replace or require editing the `pyproject.toml` setting, which stays `basic` so every other file (including `setup.py`) is unaffected. (Task 5.2 Step 2 confirms the pre-commit pyright hook honors this file comment, with a documented fallback if it does not.)

Run: `uv run pyright tools/status-line.py`
Expected initially: many findings. Fix each by adding/correcting annotations (not by `# type: ignore`). Re-run until clean. Common fixes: `Optional[...]` for nullable returns; narrowing `raw.get(...) or {}`; typing the `namedtuple` access; `cast` only where a stdlib boundary genuinely erases types (document why).

- [ ] **Step 4: Run the full suite (types must not change behavior)**

Run: `make test`
Expected: all green.
Run: `python3 -m unittest tests.test_status_line.TestGoldenOutput -v`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py
git commit -m "types(status-line): full hints + pyright strict on the render file (FR-A.6, D5)"
```

### Task 5.2: Enforce the subscript ban (D4) + flip the gate config

**Files:**
- Modify: `pyproject.toml` (pyright/pylint sections L60-100); `tools/status-line.py` (any residual subscript)

- [ ] **Step 1: Confirm the subscript ban holds by construction**

`Context` is a dataclass (not subscriptable) and `Config` is a namedtuple (string-subscript raises `TypeError`), so `ctx["x"]`/`config["x"]` are both type errors under pyright strict AND runtime errors. Verify no such access exists:

Run: `grep -nE '\bctx\[|\bconfig\[|\bcfg\[' tools/status-line.py`
Expected: empty. (Dict members keep subscript: `ctx.raw[...]` is allowed but prefer `.get`; `cfg.segments[k]`/`cfg.git[...]` are dict-valued fields, allowed by D4.)

- [ ] **Step 2: Decide the pyright project config**

Keep `[tool.pyright] typeCheckingMode = "basic"` at the project level (so `setup.py` is unaffected) and rely on the `# pyright: strict` file comment added in 5.1. Confirm the gate runs pyright over the include list and that `status-line.py` is checked strict:

Run: `uv run pyright tools/status-line.py setup.py 2>&1 | tail -5` (via the configured include)
Expected: 0 errors. If the pre-commit pyright hook ignores file-level strict, instead set the project to `strict` and add `# pyright: basic` at the top of `tools/setup.py` (the inverse isolation) — pick whichever the hook honors; verify with `make validate`.

- [ ] **Step 3: Ratchet pylint design thresholds toward defaults**

The dissolved `build_data` (was 25 locals) and the single `ctx` bag (cut `pack_line`/`safe_build` from 6–7 args to 2–4) close the args/locals gap. The current ratcheted baseline (`pyproject.toml` L71-76, verified) is **above** pylint defaults — this step tightens each to its default. Exact diff:

```toml
# [tool.pylint.design] — current (ratcheted)  →  target (pylint defaults)
max-args                  = 7   # was: pack_line threaded the builder context   →  5
max-positional-arguments  = 7                                                    →  5
max-locals                = 25  # was: build_data / validate_config_file         →  15
max-branches              = 28  # was: validate_config_file                      →  12
max-returns               = 10  # was: _apply_wizard_command (setup wizard)      →  6
max-statements            = 50  # unchanged (already at default)                 →  50
```

Resulting target block:

```toml
max-args = 5
max-positional-arguments = 5
max-locals = 15
max-branches = 12
max-returns = 6
max-statements = 50
```

Run: `uv run pylint tools/status-line.py`
Expected: the render-path functions pass at defaults (the Phase 2 dissolution of `build_data` and the `ctx`-bag arg collapse are what make this achievable — do NOT attempt this tighten before Phase 2 lands). The functions that drove the original ratchet are **out of scope** per the PRD and may still legitimately exceed the defaults after the tighten:

- `validate_config_file` (CLI introspection block in `status-line.py`) — likely still `too-many-branches`.
- `_apply_wizard_command` (in `setup.py`) — likely still `too-many-returns`. Note `setup.py` is a separate file with its own pylint pass; the global ceiling change affects it too, so expect violations there as well.

For each such function, apply a **localized** per-function `# pylint: disable=too-many-branches`/`too-many-returns` (or `too-many-locals`) with a one-line justification at the `def` — do NOT relax the global ceiling back up (this matches the PRD: defaults "for the render path", with named local exceptions for the out-of-scope CLI/setup functions). If `pylint` surfaces a violation on a *render-path* function, that is a real finding: **fix it** (split the function / reduce locals), never suppress. Update the `[tool.pylint.design]` section comment to record that the global is now at defaults with the named local exceptions enumerated.

- [ ] **Step 4: Run the gate end-to-end**

Run: `make validate`
Expected: green under pyright strict (file-scoped) + pylint design defaults + ruff + vulture + shellcheck.
Run: `make test`
Expected: all green.
Run: `python3 -m unittest tests.test_status_line.TestGoldenOutput -v`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py pyproject.toml
git commit -m "types(gate): pyright strict + subscript ban + pylint design at defaults (FR-A.6, D4/D5)"
```

**Phase 5 deliverable check:** `make validate` green under the strict ruleset; suite + golden green.

---

## Final acceptance sweep (run before declaring done)

Run each PRD acceptance criterion as a command:

- [ ] **All tests + golden:** `make test` → all green; `python3 -m unittest tests.test_status_line.TestGoldenOutput -v` → OK (golden byte-identical, never regenerated).
- [ ] **FR-R.2 test present:** `python3 -m unittest tests.test_status_line.TestSlowestTiming.test_probe_cost_counted_in_triggering_segment -v` → PASS.
- [ ] **No env outside CONFIG:** `grep -nE 'os\.environ|env\.get' tools/status-line.py` → only the one SHELL `os.environ` capture + CONFIG-block resolver lines.
- [ ] **No subscript on our types:** `grep -nE '\bctx\[|\bconfig\[|\bcfg\[' tools/status-line.py` → empty.
- [ ] **BUILDERS auto-derived:** `grep -nE '"path": seg_path' tools/status-line.py` → empty; `python3 -c "import importlib.util,sys; ..."` or the `test_discovered_builders_cover_segments` test → PASS; `SEGMENTS`/`LAYOUT` still explicit tables (present in CONFIG block).
- [ ] **Config stable-only / terminal size on Context:** inspect — `Config` has no `cols`/`lines`/`raw`; `Context` has `cols`/`lines`/`dim_assumed`/`raw`.
- [ ] **Gate green at defaults:** `make validate` → green; `[tool.pylint.design]` at `args=5, locals=15, branches=12, returns=6`; pyright strict on `status-line.py`.
- [ ] **Six-block structure + contract note:** the six `# ═══` banners present; the ARCHITECTURE note at the top.

---

## Self-review (author's check against the PRD)

**Spec coverage:** FR-A.1 → Phase 1 (Config boundary, env consolidation). FR-A.2 → Phase 2 (Context replaces build_data + the truthful-slowest test). FR-A.3 → Phase 3.1 (discovery). FR-A.4 → Phase 3.2 (git encapsulation). FR-A.5 → Phase 4 (blocks + contract note). FR-A.6 → Phase 5 (strict types + subscript ban + pylint defaults). All eight acceptance criteria map to commands in the Final sweep. D1–D7 honored and cited inline.

**Placeholder scan:** No TBD/TODO. New artifacts (`Context`, `build_context`, `_discover_builders`, `_data()` rewrite, FR-A.2 test) are given in full. Bulk mechanical edits (segment subscript→attribute, env relocation, file motion) are specified as exact rules with representative before/after and a 1:1 field map — not "handle the rest."

**Type/name consistency:** Builder signature is `seg_x(ctx, avail, theme)` everywhere (the data arg's type changes dict→Context; `avail`/`theme` stay params, preserving all 96 `_data(` call sites unchanged — 52 builder sites + ~44 other callers). `Context`/`Config`/`build_context`/`BUILDERS`/`pack_line`/`safe_build`/`render`/`git_snapshot` names are stable across phases and kept as the test surface. `_crown_slowest`/`safe_build`/`pack_line` consistently drop the `failed` param in favor of `ctx.failed` from Phase 2 onward.

**Known judgment calls (within the locked D-decisions, flagged for the executor):**
1. `home`/`claude_dir` placed on `Context` (per-render probe inputs handed by the SHELL), not `Config` — honors D6's "Config = settings; SHELL hands inputs to Context." If review prefers them on `Config`, it is a localized move.
2. The git probe's `untracked`/`want_worktree` fast-path knobs are collapsed (laziness subsumes per-segment gating). Confirmed behavior-identical for rendered output; the e2e worktree/sysmem suites + golden guard it.
3. pyright strict is applied **file-scoped** via `# pyright: strict` to avoid touching out-of-scope `setup.py`; fall back to project-strict + `# pyright: basic` on `setup.py` if the pre-commit hook does not honor the file comment.
