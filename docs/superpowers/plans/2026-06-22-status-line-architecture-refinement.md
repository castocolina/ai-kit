# Status-Line Architecture Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine the merged `tools/status-line.py` so its regions are predictable by role, segments are decoupled from a thin per-render model, the truthful-timing invariant is structural (not positional), one place reads config env, introspection lives in its own script, and an AST fitness test keeps all of this true — all with byte-identical rendered output.

**Architecture:** Keep the functional-core / imperative-shell pattern; refine *within* it. The data model moves from a typed god-bag `Context` to a thin root (`ctx` = Claude JSON + SHELL-injected runtime) plus a bounded nested `ctx.line_conf` (today's `Config`) plus memoized `probe_*` data-gatherers the owning segment calls. The packer moves from per-line build+fit to global measure → global meta → per-line pack. Classification is a full role-prefix vocabulary (`seg_`/`seg_alt_`/`probe_`/`fmt_`/`util_`/`core_`/`cfg_`) over contiguous banner blocks. Introspection extracts to `tools/statusline-doctor.py` depending one-way on the render core. An `ast`-based unittest enforces the invariants in the gate.

**Tech Stack:** Python 3.12 stdlib only (runtime); dev gate is `uv run pre-commit` (ruff, pylint at defaults, pyright strict, vulture, shellcheck, py-compile) + `python3 -m unittest`. No new runtime dependency.

---

## Hard Constraints (apply to EVERY task)

These are gates, not goals. A task is not "done" until all hold:

1. **Golden byte-identical.** `tests/fixtures/golden/expected.txt` is never regenerated. **Never run `UPDATE_GOLDEN=1`.** `python3 -m unittest tests.test_status_line.TestGoldenOutput -v` must pass after every task.
2. **Full suite green.** `make test` (the seven unittest modules + shell tests) green after every task. The FR-R.2 probe-timing test (`tests.test_status_line.TestSlowestTiming.test_probe_cost_counted_in_triggering_segment`) must stay green through every Phase-2 task in particular.
3. **Full gate green.** `make validate` (= `uv run pre-commit run --all-files`) green after every task: ruff, pylint (defaults), pyright (strict), vulture, shellcheck, py-compile.
4. **Runtime stays stdlib-only.** No new runtime import that isn't in the 3.12 stdlib.
5. **Behavior preserved.** Renames of internal segment keys do not change rendered output (keys are identifiers). User-facing config keys and env-var names that change get back-compat mapping.

**Verification shorthand used below:**

```bash
# GATE = the full per-task gate. Run after each task's final step.
make validate && make test
# GOLDEN = the fast inner-loop check during motion tasks
python3 -m unittest tests.test_status_line.TestGoldenOutput -v
# FRR2 = the probe-timing invariant (Phase 2 especially)
python3 -m unittest tests.test_status_line.TestSlowestTiming.test_probe_cost_counted_in_triggering_segment -v
```

## Branch Setup (do this once, before Task 1.1)

- [ ] **Step 1: Create the implementation branch off main.**

```bash
cd /home/user-zero/git/personal/ai-kit
git checkout main
git status        # expect clean
git checkout -b refactor/status-line-architecture-refinement
```

- [ ] **Step 2: Confirm the baseline is green before touching anything.**

```bash
make validate && make test
```

Expected: all green. If not, STOP — the baseline must be clean before refactoring.

---

## File Structure

| File | Role in this plan |
|------|-------------------|
| `tools/status-line.py` | Primary target. Renders only by end of Phase 4. Reorganized into role blocks (Phase 1), thinned data model (Phase 2), three-phase packer + alt keys (Phase 3), introspection removed (Phase 4). |
| `tools/statusline-doctor.py` | **New** (Phase 4). Owns `--doctor`/`--check`/`--print-config`, `validate_config_file`, `_dry_render_failures`, `_DOCTOR_SAMPLE`. Imports the render core via the `importlib`/`sys.modules` shim. |
| `tests/test_status_line.py` | The 247-test suite. `_data()` helper rewritten in Phase 2; `resolve_effort` env tests repointed in Phase 2 (FR-1.9); env-var-name tests updated in Phase 2 (FR-1.6); segment-key tests updated in Phase 3 (FR-5). |
| `tests/test_arch.py` | **New** (Phase 5). `ast`-based fitness test enforcing FR-8.1. |
| `tools/setup.py` | Mirrors segment keys/descriptions (lines ~66, ~170) and shells `status-line.py --doctor` (line ~345). Updated in Phase 3 (renames) and Phase 4 (doctor path). |
| `tests/test_setup.py`, `tests/test_external_segments.py` | Touched where they assert renamed keys (Phase 3) or the doctor path (Phase 4). |
| `tools/install.sh` | Learns to install the doctor script (Phase 4). |
| `tools/statusline.toml.sample`, `docs/*` | Env-name convention (Phase 2), renamed keys + back-compat note (Phase 3), doctor CLI migration (Phase 4). |
| `.pre-commit-config.yaml`, `pyproject.toml` | Add `statusline-doctor.py` to pyright/vulture/pylint/py-compile includes (Phase 4); add `test_arch` to the unittest hook (Phase 5). |

---

# Phase 1 — Classification + reorganization (FR-2, FR-6)

**Goal:** Establish structure by pure motion + renames. No logic change. This phase de-risks everything after it: once the role blocks exist, later phases edit *within* a known region.

**Why first:** The PRD orders it first specifically because structure-only motion is the safest change and gives every later phase a home. Golden + gate are the safety net for "motion only."

**Current → role mapping** (the canonical rename/placement table for this phase; derived from the live file):

| New role block | Functions that move into it (current names) |
|---|---|
| `1. SHELL` | `main`, `parse_args` (until Phase 4 moves CLI out), `safe_render` |
| `2. DEFAULTS` (data only, FR-6.1) | `SEGMENTS`, `LAYOUT`, `Line`, `PINNED`, `_SLOWEST_META`, `PATH_MAX_LEN`, `CONTEXT_BAR_CELLS`, `RIGHT_MARGIN`, `SEP`, `_GIT_CACHE_TTL`, `_GIT_DEFAULTS`, `_GIT_LEGACY_IGNORED`, `_PALETTE_DEFAULTS`, `_RAMP_DEFAULTS`, `_EFFORT_DEFAULTS`, `_EFFORT_GLYPHS`, the fixed colors `RESET`/`BG_LIGHTGRAY`/`_DIM`/`_WARN`/`INF`, the `Config` NamedTuple + `GitSnapshot`/`ExtSpec`/`Theme` type decls |
| `3. cfg_` (immediately after DEFAULTS, FR-6.2) | `load_config`, `default_config`, `env_bool`, `config_path`, `_load_toml`, `_resolve_segments`, `_resolve_layout`, `_resolve_external`, `_place_external`, `_cache_base`, `_segments_dir`, `_to_int`, `_git_key_problem` |
| `4. probe_` | `git_snapshot`, `_git_worktree_info`, `_git_cache_path`, `_worktree_info_cached`, `proc_rss_bytes` + the `_*_via_proc`/`_*_via_ps`/`_ps_field` helpers, `transcript_bytes`, `current_todo` + its `_todo_from_*`/`_pick_from_*`/`_iter_tool_uses`/`_safe_session` helpers, `effort_setting_is_auto`, `resolve_effort`, `terminal_size` |
| `5. fmt_` | `fmt_number`, `fmt_time_ms`, `fmt_tokens`, `fmt_ago`, `fmt_bytes`, `fmt_duration`, `rate_key_label` |
| `6. util_` | `pick_color`, `char_width`, `visible_width`, `_first_fitting`, `_icon`, `_hex_to_sgr`, `parse_color`, `_parse_threshold`, `_truncate_visible`, `_trunc_cols`, `_dirty_mark`, `_display_dir`, `_branch_from_porcelain`, `_position_str`, `rate_color`, `_reset_suffix`, `_sanitize_external` |
| `7. core_` | `build_context` + `Context`, `build_theme`, `default_theme`, `_resolve_palette`, `_resolve_ramp`, `_build_effort`, `_discover_builders`, `BUILDERS`, `_builders_for`, `make_external_builder`, `parse_segment_header`, `discover_external`, `_cache_read`, `_cache_write`, `_run_provider`, `run_external`, `safe_build`, `_crown_slowest`, `_pass1_non_meta`, `_pass2_meta`, `_assemble_line`, `pack_line`, `diagnostic_line`, `render`, `_doctor_cmd` |
| `8. seg_` | all `seg_*` builders |
| `9. CLI` (extracted in Phase 4) | `parse_args` flags, `cmd_print_config`, `validate_config_file`, `_DOCTOR_SAMPLE`, `_dry_render_failures`, `cmd_doctor`, `cmd_check`, `_NO_CHECK`, `_ENV_HELP` |

> Rationale for keeping `_doctor_cmd` in `core_`: it is called only in the exception handler of `safe_render` and in `diagnostic_line` when `failed` is non-empty — never on the success render path. It is NOT introspection; it only formats a command string that must be available inside a failed render without importing the doctor module. It stays in the render module; Phase 4 repoints the string it builds to name `statusline-doctor.py`.

> `resolve_effort` placement: **place it in the `cfg_` block for Phase 1.** Until Phase 2.6 removes the `CLAUDE_EFFORT` env read, it touches `os.environ` — and the FR-8.1 arch test (Phase 5) requires env reads to live in `cfg_` functions. After Phase 2.6 removes that read the function is pure-from-raw JSON; at that point it may stay in `cfg_` (acceptable, since config loading is its consumer) or move to `probe_` — but the Phase 5 arch test must be written to accept it in whichever block it lands. **Default: keep it in `cfg_` throughout, since its primary consumer is `build_context` which reads `cfg_`.**

### Task 1.1: Rename pure formatters to `fmt_` (they already are) and confirm the vocabulary baseline

The `fmt_*` functions already carry the prefix. This task only verifies the starting point and writes down the rename deltas the rest of the phase applies, so later steps are pure motion.

**Files:**
- Modify: `tools/status-line.py`

- [ ] **Step 1: Enumerate every function and its target role.** Run:

```bash
grep -nE '^(def |class |    def )' tools/status-line.py
```

Cross-check each name against the Current → role table above. There are no `fmt_`/`seg_` renames in this phase (those prefixes already match). The renames in this phase are the `util_`/`probe_`/`cfg_`/`core_` prefixes applied to functions currently named with a bare `_` or no prefix.

- [ ] **Step 2: Confirm golden + gate are green before motion.**

Run: `make validate && make test`
Expected: all green (no edits yet).

### Task 1.2: Apply `util_` prefix to the pure non-format helpers

**Files:**
- Modify: `tools/status-line.py`

Rename (definition + every call site) using a codemod to avoid false positives — prefer the bundled LibCST codemod (`cst-refactor` skill) or `python -m libcst.tool`; do NOT use bare `sed` on these short names (`_icon`, `pick_color`) — they risk matching substrings.

Rename map (apply all in one commit):

| Current | New |
|---|---|
| `pick_color` | `util_pick_color` |
| `char_width` | `util_char_width` |
| `visible_width` | `util_visible_width` |
| `_first_fitting` | `util_first_fitting` |
| `_icon` | `util_icon` |
| `_hex_to_sgr` | `util_hex_to_sgr` |
| `parse_color` | `util_parse_color` |
| `_parse_threshold` | `util_parse_threshold` |
| `_truncate_visible` | `util_truncate_visible` |
| `_trunc_cols` | `util_trunc_cols` |
| `_dirty_mark` | `util_dirty_mark` |
| `_display_dir` | `util_display_dir` |
| `_branch_from_porcelain` | `util_branch_from_porcelain` |
| `_position_str` | `util_position_str` |
| `rate_color` | `util_rate_color` |
| `_reset_suffix` | `util_reset_suffix` |
| `_sanitize_external` | `util_sanitize_external` |

- [ ] **Step 1: Apply the renames** (definitions + call sites + any string references in tests). Note the test file (`tests/test_status_line.py`) calls several of these as `sl.pick_color`, `sl.visible_width`, `sl.parse_color`, `sl.char_width` — update those `sl.<name>` references too.

```bash
grep -nE '\b(pick_color|char_width|visible_width|parse_color)\b' tests/test_status_line.py
```

- [ ] **Step 2: GOLDEN check.** Run: `python3 -m unittest tests.test_status_line.TestGoldenOutput -v` — Expected: PASS (rename can't change output).
- [ ] **Step 3: GATE.** Run: `make validate && make test` — Expected: all green.
- [ ] **Step 4: Commit.**

```bash
git add -A && git commit -m "refactor(status-line): util_ prefix for pure helpers (FR-2.1)"
```

### Task 1.3: Apply `probe_` prefix to side-effecting data gatherers

**Files:**
- Modify: `tools/status-line.py`, `tests/test_status_line.py` (mock targets reference `sl.git_snapshot`, `sl.proc_rss_bytes`, `sl.transcript_bytes`, `sl.current_todo`, `sl.effort_setting_is_auto`)

Rename map:

| Current | New |
|---|---|
| `git_snapshot` | `probe_git_snapshot` |
| `_git_worktree_info` | `probe_git_worktree_info` (or `util_` — it's pure parse of `git` output; keep `probe_` since it shells out) |
| `_worktree_info_cached` | `probe_worktree_info_cached` |
| `_git_cache_path` | `util_git_cache_path` (pure path build) |
| `proc_rss_bytes` | `probe_rss_bytes` |
| `_comm_via_proc`/`_ppid_via_proc`/`_rss_kb_via_proc`/`_ps_field`/`_comm_via_ps`/`_ppid_via_ps`/`_rss_kb_via_ps` | `probe_*` (all shell/`/proc` reads) |
| `transcript_bytes` | `probe_transcript_bytes` |
| `current_todo` | `probe_current_todo` |
| `_todo_from_tasks_dir`/`_todo_from_todos_dir`/`_todo_from_transcript` | `probe_*` |
| `_pick_from_tasks`/`_pick_from_todos`/`_iter_tool_uses`/`_safe_session` | `util_*` (pure) |
| `effort_setting_is_auto` | `probe_effort_setting_is_auto` |
| `terminal_size` | `probe_terminal_size` |

> The golden/probe-timing tests `mock.patch.object(sl, "git_snapshot", ...)`, `"proc_rss_bytes"`, `"transcript_bytes"`, `"current_todo"`, `"effort_setting_is_auto"`. After renaming, update those `mock.patch.object` targets to the new names. This is the highest-risk step for the golden — the mocks must bind to the renamed symbols or the golden's determinism breaks.

- [ ] **Step 1: Apply renames** (definitions + call sites + `sl.<name>` test references + `mock.patch.object(sl, "<name>", ...)` targets in `tests/test_status_line.py`).
- [ ] **Step 2: FRR2 + GOLDEN.** Run:

```bash
python3 -m unittest tests.test_status_line.TestSlowestTiming.test_probe_cost_counted_in_triggering_segment tests.test_status_line.TestGoldenOutput -v
```

Expected: PASS. (If the golden fails here, a mock target was missed — fix before continuing.)

- [ ] **Step 3: GATE.** `make validate && make test` — Expected: all green.
- [ ] **Step 4: Commit.**

```bash
git add -A && git commit -m "refactor(status-line): probe_ prefix for side-effecting gatherers (FR-2.1)"
```

### Task 1.4: Apply `cfg_` and `core_` prefixes

**Files:**
- Modify: `tools/status-line.py`, `tests/test_status_line.py` (`sl.load_config`, `sl.default_config`, `sl.build_context`, `sl.build_theme`, `sl.default_theme`, `sl.pack_line`, `sl.render`, `sl.safe_build`, `sl.config_path`, `sl.env_bool`, `sl.terminal_size` references), `tests/test_external_segments.py`, `tools/setup.py` (shells the module but does not import symbols — no rename needed there).

Apply `cfg_` to the loader family and `core_` to the render/theme/registry/external-machinery family per the Current → role table. Keep public-API-ish names the tests lean on heavily (`build_context`, `pack_line`, `render`, `load_config`, `default_config`, `build_theme`, `default_theme`, `safe_build`) — the PRD's role scheme targets *internal* helpers; widely-referenced entrypoints may keep their names if the arch test (Phase 5) is written to accept them as the block's public surface.

> DECISION POINT for the executor: FR-2.1 says "every function carries its role." The cleanest reading renames even `pack_line` → `core_pack`, `render` → `core_render`, etc., and updates all `sl.*` test references in one sweep. The lighter reading keeps the test-facing entrypoints. **Default: rename everything to the prefix** (matches the user's structure-obsession and the FR-8.1 "role-prefix integrity" rule, which is simplest when there are no exceptions). Update every `sl.<old>` reference across `tests/test_status_line.py` and `tests/test_external_segments.py` in the same commit. If the sweep proves too broad to land safely in one task, split by family (`cfg_` commit, then `core_` commit).

- [ ] **Step 1: Apply `cfg_` renames** (loader family) + update all `sl.<name>` test references.
- [ ] **Step 2: GOLDEN + GATE.** `python3 -m unittest tests.test_status_line.TestGoldenOutput -v` then `make validate && make test`.
- [ ] **Step 3: Commit.** `git add -A && git commit -m "refactor(status-line): cfg_ prefix for config loader family (FR-2.1)"`
- [ ] **Step 4: Apply `core_` renames** (render/theme/registry/external machinery) + update all references.
- [ ] **Step 5: GOLDEN + FRR2 + GATE.** Run the golden, the probe-timing test, then `make validate && make test`.
- [ ] **Step 6: Commit.** `git add -A && git commit -m "refactor(status-line): core_ prefix for render machinery (FR-2.1)"`

### Task 1.5: Reorganize into contiguous banner blocks; DEFAULTS first, `cfg_` immediately after

This is the big motion task. No renames here (done in 1.2–1.4) — only moving function/constant definitions so every role is one contiguous region, in the order: SHELL → DEFAULTS → cfg_ → probe_ → fmt_ → util_ → core_ → seg_ → CLI.

**Files:**
- Modify: `tools/status-line.py`

- [ ] **Step 1: Move the DEFAULTS data block to the top** (right after the SHELL block), containing only data (FR-6.1): `SEGMENTS`, `LAYOUT`, `Line`, `PINNED`, `_SLOWEST_META`, the tuning scalars, the `_*_DEFAULTS` dicts, `_EFFORT_GLYPHS`, the fixed colors, `INF`, and the type declarations (`Config`, `GitSnapshot`, `ExtSpec`, `Theme`). No function with logic lives here. `Theme` is a class with methods — if pylint/pyright object to a class in "data only," keep the `Theme` *class definition* in `core_` and only its default-construction data in DEFAULTS; the arch test in Phase 5 defines "data-only" as "no module-level executable statements besides literals/dataclass/NamedTuple decls," so a class with a `c()` method belongs in `core_`. **Place `Theme` in `core_`.**
- [ ] **Step 2: Place the `cfg_` block immediately after DEFAULTS** (FR-6.2).
- [ ] **Step 3: Order the remaining blocks** probe_ → fmt_ → util_ → core_ → seg_ → CLI, each under a single `# ═══ N. <ROLE> ═══` banner.
- [ ] **Step 4: Update the module-level forward references.** `BUILDERS = _core_discover_builders()` must run *after* all `seg_*` defs (it scans `globals()`); keep it at the end of the `seg_` block. The `_ENV_HELP`/`_NO_CHECK` constants used by `parse_args` stay near the CLI block (Phase 4 moves them out).
- [ ] **Step 5: GOLDEN + FRR2 + full suite.**

```bash
python3 -m unittest tests.test_status_line -v
```

Expected: all 247 tests PASS. Pay attention to import-time ordering errors (a symbol referenced before definition) — Python resolves module-level names at call time for functions, but `BUILDERS = ...` and any other module-level *call* must come after its dependencies.

- [ ] **Step 6: GATE.** `make validate && make test` — Expected: all green.
- [ ] **Step 7: Commit.** `git add -A && git commit -m "refactor(status-line): contiguous role blocks, DEFAULTS first (FR-2.2, FR-6)"`

### Task 1.6: Update the ARCHITECTURE banner comment to describe the new block scheme

**Files:**
- Modify: `tools/status-line.py` (the header comment at lines ~11–25)

- [ ] **Step 1: Rewrite the `# ARCHITECTURE` comment** to list the new ordered blocks (SHELL / DEFAULTS / cfg_ / probe_ / fmt_ / util_ / core_ / seg_ / CLI) and the role-prefix vocabulary, replacing the old six-block description.
- [ ] **Step 2: GATE.** `make validate && make test`.
- [ ] **Step 3: Commit.** `git add -A && git commit -m "docs(status-line): architecture banner reflects role blocks (FR-2.2)"`

**Phase 1 deliverable:** role-prefixed, block-reorganized `status-line.py`; golden byte-identical; gate green. No logic changed.

---

# Phase 2 — Data-model decoupling + env consolidation (FR-1)

**Goal:** Thin the per-render object to `ctx` (Claude JSON + SHELL-injected runtime) + nested `ctx.line_conf`; move single-consumer probes out to memoized `probe_*` the owning segment calls; one config env reader via the `CC_AI_KIT_<...>` → `line_conf.<group>.<field>` convention; drop `CLAUDE_EFFORT`.

**Critical invariant:** FRR2 (probe-timing) must stay green at every step. The mechanism shifts from `cached_property` on the god-bag to a module-level memoize on `probe_*` — but the cost must still land inside the first segment's timed build.

### Task 2.1: Rename `git_snapshot` → `probe_git_snapshot` (the underlying I/O only)

This task is purely a rename — no memoization yet. Memoization is introduced in Task 2.3 once `ctx._probe_cache` exists.

**Files:**
- Modify: `tools/status-line.py`, `tests/test_status_line.py`

- [ ] **Step 1: Rename `git_snapshot` → `probe_git_snapshot`** (definition + every call site in `status-line.py`, plus `mock.patch.object(sl, "git_snapshot", ...)` in `tests/test_status_line.py` → `mock.patch.object(sl, "probe_git_snapshot", ...)`).

```bash
grep -n "git_snapshot" tools/status-line.py tests/test_status_line.py
```

Update every occurrence (approximately 3–5 sites in the module, plus several mock targets in the test file).

- [ ] **Step 2: FRR2 + GOLDEN.** Run:

```bash
python3 -m unittest tests.test_status_line.TestSlowestTiming.test_probe_cost_counted_in_triggering_segment tests.test_status_line.TestGoldenOutput -v
```

Expected: PASS (rename can't change output; mocks bind to the new name).

- [ ] **Step 3: GATE.** `make validate && make test` — Expected: all green.
- [ ] **Step 4: Commit.**

```bash
git add -A && git commit -m "refactor(status-line): rename git_snapshot -> probe_git_snapshot (FR-2.1)"
```

> Note: Do NOT introduce a memoized wrapper in this task. The `probe_git_for(ctx)` accessor that segments will call is introduced in Task 2.3 once `ctx._probe_cache` exists.

---

> **Tasks 2.2, 2.3, and 2.4 form one atomic behavior-preserving change.** You cannot remove the probe fields from `Context` without simultaneously repointing the segments and the `_data()` test helper. Execute Tasks 2.2 + 2.3 + 2.4 as a single subagent task and land them in **one commit** (the commit in Task 2.4 Step 7). The numbered steps in each task are a checklist within that single unit — do not commit between tasks.

### Task 2.2: Define the thin per-render model — `ctx` root (Claude JSON + runtime) + nested `ctx.line_conf`

**Files:**
- Modify: `tools/status-line.py`
- Test: `tests/test_status_line.py`

FR-1.1: the per-render object's root represents Claude's incoming JSON (typed) + SHELL-injected runtime (`cols`/`lines`/`dim_assumed` geometry, resolved `effort`, `t_start`, the raw JSON) + `line_conf` (today's `Config`) + `theme` + render bookkeeping (`failed`, `slowest`). FR-1.3: NO single-consumer probe fields (RSS, chat size, ago, effort-auto, todo, git).

- [ ] **Step 1: Write the failing test** asserting the new shape — root carries Claude-JSON-derived fields and `line_conf`, and the removed probe fields are gone:

```python
class TestThinContext(unittest.TestCase):
    def test_root_has_claude_json_and_line_conf(self):
        ctx = _data()
        self.assertTrue(hasattr(ctx, "line_conf"))      # our config sub-object
        self.assertIsInstance(ctx.line_conf, sl.Config)
        self.assertTrue(hasattr(ctx, "cols"))           # SHELL-injected runtime
        self.assertEqual(ctx.model_name, "Opus 4.8")    # Claude JSON, eager
    def test_no_single_consumer_probe_fields(self):
        ctx = _data()
        for gone in ("ago", "effort_auto", "chat_bytes", "mem_bytes",
                     "branch", "dirty", "is_worktree", "wt_name",
                     "todo_state", "todo_text"):
            self.assertNotIn(gone, type(ctx).__dict__,
                             f"{gone} must no longer be a ctx member")
```

- [ ] **Step 2: Run it — Expected: FAIL** (both assertions fail against the current god-bag).
- [ ] **Step 3: Rename `Context.config` → `Context.line_conf`** across the module and tests (this is the `ctx.line_conf` split — the field that *was* `config` now reads as our settings sub-object). Keep the eager Claude-JSON fields (`model_name`, `cost`, `context_pct`, …) on the root. Remove the `cached_property` probe members (`_git`, `branch`, `dirty`, `is_worktree`, `wt_name`, `in_repo`, `ago`, `effort_auto`, `_todo`, `todo_state`, `todo_text`, `chat_bytes`, `mem_bytes`). Add a per-render probe cache field: `_probe_cache: dict[str, Any] = field(default_factory=dict)`.

Do not commit yet — the segments that read the removed members are repointed in Task 2.4.

### Task 2.3: Memoized `probe_*` accessors keyed through the ctx cache; co-locate `core_build_context` with the model

**Files:**
- Modify: `tools/status-line.py`
- Test: `tests/test_status_line.py`

FR-1.3 functions to implement as memoized probes the owning segment calls: `probe_git_for(ctx)` plus `probe_ago(ctx)`, `probe_effort_auto(ctx)`, `probe_todo(ctx)`, `probe_chat_size(ctx)`, `probe_rss(ctx)`. Each memoizes on `ctx._probe_cache` so it runs once per render and its cost lands in the triggering segment's timed build (FR-1.4).

- [ ] **Step 1: Write the failing test** for `probe_git_for` — the memoized ctx-keyed git accessor:

```python
class TestGitProbeMemoized(unittest.TestCase):
    def test_probe_git_for_runs_once_per_render(self):
        calls = []
        def fake(work_dir, conf):
            calls.append(work_dir)
            return sl.GitSnapshot(in_repo=True, branch="main", dirty="clean",
                                  is_worktree=False, wt_name="")
        ctx = _data()
        with mock.patch.object(sl, "probe_git_snapshot", side_effect=fake):
            snap1 = sl.probe_git_for(ctx)
            snap2 = sl.probe_git_for(ctx)
        self.assertEqual(snap1.branch, "main")
        self.assertIs(snap1, snap2)       # same object — memoized on ctx
        self.assertEqual(len(calls), 1)   # underlying I/O ran exactly once
```

- [ ] **Step 2: Run it — Expected: FAIL** (`probe_git_for` undefined). `python3 -m unittest tests.test_status_line.TestGitProbeMemoized -v`

- [ ] **Step 3: Implement the memoize helper + all six memoized probe accessors** in `tools/status-line.py` (in the `core_` or `probe_` block, after the `Context` dataclass):

```python
def _memo(ctx: "Context", key: str, fn: "Callable[[], Any]") -> Any:
    """Run fn() once per render, caching on ctx._probe_cache.
    Preserves FR-R.2 timing: the first caller (inside the packer's per-segment
    bracket) pays the I/O cost; subsequent callers in the same render are free."""
    cache = ctx._probe_cache
    if key not in cache:
        cache[key] = fn()
    return cache[key]

def probe_git_for(ctx: "Context") -> "GitSnapshot":
    """Memoized git snapshot for this render. Calls probe_git_snapshot once;
    branch/dirty/worktree segments all share the result (FR-1.3/FR-1.4)."""
    return _memo(ctx, "git",
                 lambda: probe_git_snapshot(ctx.work_dir, ctx.line_conf))

def probe_ago(ctx: "Context") -> str:
    def _compute() -> str:
        t = ctx.transcript
        if t and os.path.isfile(t):
            return fmt_ago(int(time.time()) - int(os.path.getmtime(t)))
        return ""
    return _memo(ctx, "ago", _compute)

def probe_effort_auto(ctx: "Context") -> bool:
    return _memo(ctx, "effort_auto",
                 lambda: probe_effort_setting_is_auto(ctx.work_dir, ctx.home))

def probe_todo(ctx: "Context") -> tuple[str | None, str | None]:
    return _memo(ctx, "todo",
                 lambda: probe_current_todo(ctx.transcript, ctx.session, ctx.claude_dir))

def probe_chat_size(ctx: "Context") -> int | None:
    return _memo(ctx, "chat_size", lambda: probe_transcript_bytes(ctx.transcript))

def probe_rss(ctx: "Context") -> int | None:
    return _memo(ctx, "rss", lambda: probe_rss_bytes())
```

- [ ] **Step 4: Move `core_build_context` + the `Context` dataclass adjacent** (FR-1.5) — the assembler immediately follows the dataclass it constructs, both in the `core_` block.

Do not commit yet — segments are repointed in Task 2.4.

### Task 2.4: Repoint every probe-consuming segment to its `probe_*`; rewrite the `_data()` test helper

**Files:**
- Modify: `tools/status-line.py` (segments), `tests/test_status_line.py` (`_data()` + probe-injection)

- [ ] **Step 1: Rewrite the segments** to call probes instead of reading ctx members:
  - `seg_branch`: `branch = probe_git_for(ctx).branch`
  - `seg_dirty`: `mark = util_dirty_mark(probe_git_for(ctx).dirty, theme)`
  - `seg_worktree`: read `probe_git_for(ctx).in_repo` / `.is_worktree` / `.wt_name`
  - `seg_time_ago`: `ago = probe_ago(ctx)`
  - `seg_effort`: `if probe_effort_auto(ctx): ...`
  - `seg_todo`: `state, text = probe_todo(ctx)`
  - `seg_chat_size`: `n = probe_chat_size(ctx)`
  - `seg_memory`: `n = probe_rss(ctx)`
- [ ] **Step 2: Rewrite `_data()` in `tests/test_status_line.py`.** The helper currently seeds `cached_property` slots in `ctx.__dict__`. Replace with seeding `ctx._probe_cache` directly:

```python
def _data(**over):
    eager = { ... }   # unchanged eager Claude-JSON fields, but config= -> line_conf=
    probe_defaults = {
        "git": sl.GitSnapshot(in_repo=False, branch="main", dirty="modified",
                              is_worktree=False, wt_name=""),
        "ago": "5m 0s ago", "effort_auto": False,
        "todo": (None, None), "chat_size": 305000, "rss": 448_790_528,
    }
    # pop probe overrides expressed as flat kwargs (branch=, dirty=, in_repo=, etc.)
    # and fold them into the GitSnapshot / tuple as before, then:
    ctx = sl.Context(raw={}, line_conf=sl.cfg_default_config(), theme=THEME, **eager)
    ctx._probe_cache.update(probe_defaults_resolved)
    return ctx
```

Preserve the existing override surface (`branch=`, `dirty=`, `in_repo=`, `wt_name=`, `is_worktree=`, `ago=`, `effort_auto=`, `todo_state=`, `todo_text=`, `chat_bytes=`/`mem_bytes=`) by mapping them onto the cache keys, so the ~50 call sites that pass these don't all need editing. Map `chat_bytes`→`chat_size`, `mem_bytes`→`rss`, `todo_state`/`todo_text`→the `todo` tuple, and the git fields→the `git` GitSnapshot.

- [ ] **Step 3: Update the golden's `_deterministic()` mocks.** It patches `sl.git_snapshot`→ now `sl.probe_git_snapshot`, `sl.proc_rss_bytes`→`sl.probe_rss_bytes`, `sl.transcript_bytes`→`sl.probe_transcript_bytes`, `sl.current_todo`→`sl.probe_current_todo`, `sl.effort_setting_is_auto`→`sl.probe_effort_setting_is_auto`. These are the underlying I/O fns the memoized probes call, so patching them keeps the golden deterministic.
- [ ] **Step 4: Update the FRR2 test** (`test_probe_cost_counted_in_triggering_segment`) — it builds a live Context and patches `sl.git_snapshot`. Repoint to `sl.probe_git_snapshot` (the underlying I/O that `probe_git_for` delegates to) and assert the probe cost landed via `ctx._probe_cache.get("git")` instead of `ctx.__dict__.get("_git")`.
- [ ] **Step 5: GOLDEN + FRR2 + full suite.** Run:

```bash
python3 -m unittest tests.test_status_line -v
```

Expected: all PASS. The golden MUST be byte-identical.

- [ ] **Step 6: GATE.** `make validate && make test`.
- [ ] **Step 7: Commit** (Tasks 2.2 + 2.3 + 2.4 as one atomic unit — this is the single commit for all three tasks):

```bash
git add -A && git commit -m "refactor(status-line): thin ctx + line_conf split, probes out of the data model (FR-1.1–1.5)"
```

### Task 2.5: Single config env reader — the `CC_AI_KIT_<...>` → `line_conf.<group>.<field>` convention

**Files:**
- Modify: `tools/status-line.py` (the `cfg_` loader), `tests/test_status_line.py`, `tools/statusline.toml.sample`, docs

FR-1.6: all config env reading happens in exactly one `cfg_` function, by a generic convention with full names — no hardcoded per-variable branch. FR-1.8: SHELL/runtime + third-party reads are the whitelisted exceptions. The rename map (FR-1.6 / FR-5.3 overlap):

| Current env var | New env var | Resolves to |
|---|---|---|
| `CC_AI_KIT_GIT_TTL` | `CC_AI_KIT_GIT_CACHE_TTL` | `line_conf.git.cache_ttl` |
| `CC_AI_KIT_EXTERNAL_TTL` | `CC_AI_KIT_EXTERNAL_CACHE_TTL` | `line_conf.external.cache_ttl` |
| `CC_AI_KIT_SEGMENTS_DIR` | `CC_AI_KIT_EXTERNAL_DIR` | `line_conf.external.dir` |
| `CC_AI_KIT_SEGMENT_<KEY>` | (unchanged) | `line_conf.segments[<key>]` |
| `CC_AI_KIT_CONFIG` | `CC_AI_KIT_CONFIG_FILE` | bootstrap (FR-1.7, hardcoded read) |

- [ ] **Step 1: Write the failing tests** for the convention + back-compat:

```python
class TestEnvConvention(unittest.TestCase):
    def test_git_cache_ttl_via_convention(self):
        cfg = sl.cfg_load_config({"HOME": "/h", "CC_AI_KIT_GIT_CACHE_TTL": "42"})
        self.assertEqual(cfg.git["cache_ttl"], 42)
    def test_segment_toggle_via_convention(self):
        cfg = sl.cfg_load_config({"HOME": "/h", "CC_AI_KIT_SEGMENT_BRANCH": "false"})
        self.assertFalse(cfg.segments["branch"])
    def test_external_dir_via_convention(self):
        cfg = sl.cfg_load_config({"HOME": "/h", "CC_AI_KIT_EXTERNAL_DIR": "/x/seg"})
        self.assertEqual(cfg.segments_dir, "/x/seg")
    def test_old_git_ttl_name_still_works(self):
        # back-compat: old name maps forward with at most a dim warning
        cfg = sl.cfg_load_config({"HOME": "/h", "CC_AI_KIT_GIT_TTL": "7"})
        self.assertEqual(cfg.git["cache_ttl"], 7)
```

- [ ] **Step 2: Run — Expected: FAIL** (new names unrecognized).
- [ ] **Step 3: Implement the single env reader** in the `cfg_` block. One function walks `env` for keys matching `CC_AI_KIT_<TOKEN>_<REST>` and routes by the leading token: `SEGMENT` → `segments[rest.lower()]` (via `cfg_env_bool`), `GIT` → `git[rest.lower()]`, `EXTERNAL` → `external.<rest.lower()>` (dir/cache_ttl). The bootstrap `CC_AI_KIT_CONFIG_FILE` is read by an explicit hardcoded line in `cfg_config_path` (FR-1.7) — documented as the exception. Map the old names (`CC_AI_KIT_GIT_TTL`, `CC_AI_KIT_EXTERNAL_TTL`, `CC_AI_KIT_SEGMENTS_DIR`, `CC_AI_KIT_CONFIG`) forward to the new ones with at most a dim deprecation warning. Remove the scattered `env.get("CC_AI_KIT_...")` reads from `_resolve_external`/`_segments_dir`/`load_config`/`config_path` — they all funnel through the one reader (except the FR-1.7 bootstrap).
- [ ] **Step 4: Update `_ENV_HELP`** and `tools/statusline.toml.sample` + any docs naming the env vars to the new names (note old names accepted).
- [ ] **Step 5: GATE + GOLDEN.** `make validate && make test`. The golden is env-driven only via `STATUSLINE_COLS`/`LINES` (whitelisted runtime) — unaffected.
- [ ] **Step 6: Commit.** `git add -A && git commit -m "refactor(status-line): single config env reader, structure-aware convention (FR-1.6–1.8)"`

### Task 2.6: Drop `CLAUDE_EFFORT` (FR-1.9)

**Files:**
- Modify: `tools/status-line.py` (`resolve_effort`), `tests/test_status_line.py` (the 2 env tests)

- [ ] **Step 1: Remove the env fallback** in `resolve_effort` — `level = str(effort_block.get("level") or "")` (drop `or env.get("CLAUDE_EFFORT")`). The function no longer takes `env` if `env` is now unused; check callers (`safe_render`, `_ctx_from_env`, `_dry_render_failures`) and drop the `env` argument if it becomes dead, OR keep the signature and ignore env — **default: drop the now-unused `env` parameter** and update the three call sites (vulture will flag an unused param otherwise).
- [ ] **Step 2: Repoint the two affected tests** in `TestResolveEffort`. Replace `test_env_auto_normalized_away` and `test_level_wins_over_env` (which inject via `CLAUDE_EFFORT`) with raw-JSON injection:

```python
def test_level_auto_normalized_away(self):
    self.assertEqual(sl.resolve_effort({"effort": {"level": "auto"}}), "")
def test_case_normalized(self):
    self.assertEqual(sl.resolve_effort({"effort": {"level": "HIGH"}}), "high")
def test_missing_is_empty(self):
    self.assertEqual(sl.resolve_effort({}), "")
# (drop the two CLAUDE_EFFORT-based tests; effort now resolves from JSON + settings only)
```

- [ ] **Step 3: GATE + GOLDEN + FRR2.** `make validate && make test`.
- [ ] **Step 4: Commit.** `git add -A && git commit -m "refactor(status-line): drop redundant CLAUDE_EFFORT env source (FR-1.9)"`

**Phase 2 deliverable:** thin `ctx` + nested `line_conf`; single-consumer probes are memoized `probe_*`; one config env reader; `CLAUDE_EFFORT` gone; FRR2 + golden green.

---

# Phase 3 — Packer refactor + alt segments (FR-4, FR-5)

**Goal:** Three-phase packer (measure-all global → meta-once global → pack-per-line); position-independent meta; `seg_alt_`/`alt_` dispensable tier with the confirmed core/alt partition and the `time_` family rename; back-compat for every renamed key.

### Task 3.1: Lift measurement to a global Phase A; compute meta once in Phase B; pack per-line in Phase C

**Files:**
- Modify: `tools/status-line.py` (the `core_` packer: `pack_line`, `_pass1_non_meta`, `_pass2_meta`, `_assemble_line`, `render`)
- Test: `tests/test_status_line.py`

Today `render` calls `pack_line` per layout line; `pack_line` does pass1 (build+time non-meta, with a provisional `used_est` fit) + pass2 (meta) + assemble. FR-4 restructures to: `core_render` runs Phase A (build+time every active non-meta segment across ALL lines, crowning the single global slowest), Phase B (compute `render_time`/`slowest` once globally), Phase C (per-line `core_pack` over already-built strings). The only logic change is that `ctx.slowest` is now crowned across ALL lines before Phase B; golden byte-identical is preserved because Phase A passes each segment the same per-line shrinking `avail` it received in the old `_pass1_non_meta` (see below).

**`avail` semantics for Phase A (critical for golden parity):**

The current `_pass1_non_meta` maintains a per-line `used_est` counter and passes `avail = max(budget - used_est - sep, 0)` to each builder — this is a shrinking per-line remaining budget. Several builders (`seg_path`, `seg_branch`, etc.) use `_first_fitting(variants, avail)` to choose compact vs. rich variants. Phase A MUST replicate this per-line walk exactly to keep variant selection identical and preserve the golden. The three-phase refactor does NOT collapse all segments to `avail = budget` — that would change variant selection and break the golden. Concretely:

- Phase A iterates each layout line separately, maintaining its own `used_est = 0` per line.
- For each non-meta segment on that line: `sep = sep_w if used_est else 0`; `avail = max(budget - used_est - sep, 0)`; build the segment; if it fits (or is PINNED), add to `built` for that (line, key) and advance `used_est += visible_width(s) + sep`. Crown `ctx.slowest` from the timing.
- Phase A's `built` dict is therefore keyed `(line_index, segment_key)` — or equivalently, Phase A runs the current `_pass1_non_meta` logic for each line but crowns `ctx.slowest` globally across all lines rather than discarding it at the end of each line.
- Phase B builds `render_time`/`slowest` once into a separate `meta_built: dict[str, str]`.
- Phase C assembles each line from its slice of `built` plus `meta_built`, using `_assemble_line` unchanged.

This means the real semantic change is: old `render` crowned `ctx.slowest` inside `pack_line` (per-line scope, with the last line's crowning being final), while new `core_render` crowns globally before Phase B. The `_pass1_non_meta` fit logic is preserved line-for-line.

- [ ] **Step 1: Write the failing test** — meta values are position-independent (FR-4.5):

```python
class TestMetaPositionIndependent(unittest.TestCase):
    def test_slowest_same_regardless_of_line(self):
        """slowest segment text must be identical whether slowest is on line 1 or line 2."""
        import re

        def _make_cfg_with_slowest_on_line(line_idx: int) -> "sl.Config":
            """Return a config where `slowest` lives on `line_idx` (0 or 1)."""
            core_keys = ["path", "model"]
            meta_keys = ["render_time", "slowest"]
            lines = [sl.Line(min_rows=1, segments=core_keys),
                     sl.Line(min_rows=1, segments=core_keys)]
            lines[line_idx] = sl.Line(
                min_rows=1, segments=core_keys + meta_keys
            )
            cfg = sl.cfg_default_config()
            # enable only the keys we use; ensure slowest/render_time enabled
            segs = {k: False for k in cfg.segments}
            for k in core_keys + meta_keys:
                segs[k] = True
            return cfg._replace(layout=lines, segments=segs)

        ctx0 = _data()
        ctx1 = _data()
        cfg0 = _make_cfg_with_slowest_on_line(0)
        cfg1 = _make_cfg_with_slowest_on_line(1)

        lines0 = sl.core_render(ctx0, cfg=cfg0)
        lines1 = sl.core_render(ctx1, cfg=cfg1)

        # Extract the `slowest` segment text from whichever output line it landed on
        def _find_slowest(rendered: list[str]) -> str:
            for line in rendered:
                # seg_slowest emits the slowest builder name + duration
                m = re.search(r'slowest[^|]*\d+ms', line)
                if m:
                    return m.group(0)
            return ""

        slowest0 = _find_slowest(lines0)
        slowest1 = _find_slowest(lines1)
        self.assertTrue(slowest0, "slowest segment not found in layout 0 output")
        self.assertTrue(slowest1, "slowest segment not found in layout 1 output")
        self.assertEqual(slowest0, slowest1,
                         f"slowest differs by position: {slowest0!r} vs {slowest1!r}")
```

- [ ] **Step 2: Run — Expected: FAIL** (today's per-line meta makes `ctx.slowest` position-dependent — last line wins). `python3 -m unittest tests.test_status_line.TestMetaPositionIndependent -v`
- [ ] **Step 3: Implement the three phases.** FR-4.1: active per line = `[k for k in line.segments if cfg.segments.get(k, False)]`. Phase A: `core_measure_all` — for each layout line, walk its active non-meta segments left-to-right with per-line `used_est = 0`, passing `avail = max(budget - used_est - sep, 0)` to each builder (exactly as `_pass1_non_meta` does today), storing built strings in `built: dict[tuple[int, str], str]` keyed by `(line_index, segment_key)`, and calling `_crown_slowest` globally for all lines. Phase B: `core_build_meta` — build `render_time`/`slowest` once (passing `avail = budget`) into `meta_built: dict[str, str]`. Phase C: `core_pack` — for each line, first **strip the line index** out of the global tuple-keyed `built` into a plain `dict[str, str]` (because `_assemble_line(enabled, built, budget, sep_w)` takes a string-keyed dict — verified against the live signature), then merge `meta_built` on top, then call `_assemble_line` unchanged:

```python
for line_index, line in enumerate(cfg.layout):
    enabled = [k for k in line.segments if cfg.segments.get(k, False)]
    line_built = {k: v for (i, k), v in built.items() if i == line_index}
    line_built.update(meta_built)   # render_time / slowest, built once in Phase B
    out.append(_assemble_line(enabled, line_built, budget, sep_w))
```

`_assemble_line` itself is unchanged. Keep `_SLOWEST_META`, `PINNED`, `SEP`, `RIGHT_MARGIN` semantics unchanged.
- [ ] **Step 4: GOLDEN + FRR2 + new test + full suite.** The golden disables meta, so it guards Phase A/C output. FRR2 guards the timing. Run `python3 -m unittest tests.test_status_line -v`. Expected: all PASS, golden byte-identical.
- [ ] **Step 5: GATE.** `make validate && make test`.
- [ ] **Step 6: Commit.** `git add -A && git commit -m "refactor(status-line): three-phase packer, global meta, no double-fit (FR-4)"`

### Task 3.2: Apply the confirmed core/alt partition + `time_` family rename + `seg_alt_` prefix

**Files:**
- Modify: `tools/status-line.py`, `tests/test_status_line.py`, `tools/setup.py`, `tests/test_setup.py`, `tools/statusline.toml.sample`, docs

Confirmed partition (FR-5.2) — **stacked-name default confirmed at plan time**:

- **Core (11, unchanged keys):** `path`, `branch`, `dirty`, `todo`, `model`, `effort`, `lines`, `render_time`, `slowest`, `context`, `chat_size`.
- **Alt (9):** `alt_cost`, `alt_rate_limits`, `alt_dimensions`, `alt_worktree`, `alt_memory`, and the time family `alt_time_clock` (was `clock`), `alt_time_ago` (was `time_ago`), `alt_time_session` (was `total_time`), `alt_time_api` (was `api_time`).

Builder/key rename map:

| Current builder | New builder | New key | Old key (back-compat) |
|---|---|---|---|
| `seg_cost` | `seg_alt_cost` | `alt_cost` | `cost` |
| `seg_rate_limits` | `seg_alt_rate_limits` | `alt_rate_limits` | `rate_limits` |
| `seg_dimensions` | `seg_alt_dimensions` | `alt_dimensions` | `dimensions` |
| `seg_worktree` | `seg_alt_worktree` | `alt_worktree` | `worktree` |
| `seg_memory` | `seg_alt_memory` | `alt_memory` | `memory` |
| `seg_clock` | `seg_alt_time_clock` | `alt_time_clock` | `clock` |
| `seg_time_ago` | `seg_alt_time_ago` | `alt_time_ago` | `time_ago` |
| `seg_total_time` | `seg_alt_time_session` | `alt_time_session` | `total_time` |
| `seg_api_time` | `seg_alt_time_api` | `alt_time_api` | `api_time` |

- [ ] **Step 1: Write the failing back-compat test** (FR-5.3): every old key still loads from its old spelling and its old `CC_AI_KIT_SEGMENT_<OLDKEY>` env name, mapped forward:

```python
class TestAltBackCompat(unittest.TestCase):
    def test_old_segment_key_in_toml_maps_forward(self):
        # a config with [segments] clock = false hides alt_time_clock
        cfg = _load_cfg_with_toml("[segments]\nclock = false\n")
        self.assertFalse(cfg.segments["alt_time_clock"])
    def test_old_segment_env_maps_forward(self):
        cfg = sl.cfg_load_config({"HOME": "/h", "CC_AI_KIT_SEGMENT_CLOCK": "false"})
        self.assertFalse(cfg.segments["alt_time_clock"])
```

(Provide a `_load_cfg_with_toml` helper writing a temp TOML and pointing `CC_AI_KIT_CONFIG_FILE` at it.)

- [ ] **Step 2: Run — Expected: FAIL.**
- [ ] **Step 3: Apply the renames** (builders + `SEGMENTS` keys + `LAYOUT` keys + `_SLOWEST_META` unaffected) via codemod. Update the `SEGMENTS` dict and `LAYOUT` lists to the new keys. The auto-discovery registry (`core_discover_builders`) strips the `seg_` prefix, so `seg_alt_time_clock` → key `alt_time_clock` automatically — verify the prefix-strip handles `seg_alt_` correctly (it strips only `seg_`, leaving `alt_time_clock`, which is the intended key — good).
- [ ] **Step 4: Add the back-compat key mapping** in the `cfg_` segment resolver: a `_LEGACY_SEGMENT_KEYS = {"clock": "alt_time_clock", "time_ago": "alt_time_ago", "total_time": "alt_time_session", "api_time": "alt_time_api", "cost": "alt_cost", "rate_limits": "alt_rate_limits", "dimensions": "alt_dimensions", "worktree": "alt_worktree", "memory": "alt_memory"}` consulted when a file/env key is an old name — mapped forward with at most a dim deprecation warning (mirror the existing `_GIT_LEGACY_IGNORED` handling). Note `worktree` already had legacy `[git] worktree` handling — keep that distinct from the new `[segments] worktree → alt_worktree` mapping.
- [ ] **Step 5: Update `tools/setup.py`** — the `_SEG_DESCRIPTIONS`/segment mirror (lines ~66, ~170–175) and any LAYOUT mirror must use the new keys; update `tests/test_setup.py` assertions accordingly.
- [ ] **Step 6: Update `tests/test_status_line.py`** — every test referencing `clock`/`total_time`/`api_time`/`cost`/`rate_limits`/`dimensions`/`worktree`/`memory`/`time_ago` as keys, and the `_data()`/segment tests, to the new keys. The golden `inputs.json` uses `default_config()` which now has the new keys — **the rendered output is unaffected** (keys are identifiers; the emoji/text each builder emits is unchanged), so `expected.txt` stays byte-identical. Verify this explicitly.
- [ ] **Step 7: GOLDEN (critical) + full suite.** Run `python3 -m unittest tests.test_status_line.TestGoldenOutput -v` first — Expected: byte-identical PASS. Then `python3 -m unittest tests.test_status_line tests.test_setup tests.test_external_segments -v`.
- [ ] **Step 8: GATE.** `make validate && make test`.
- [ ] **Step 9: Commit.** `git add -A && git commit -m "refactor(status-line): alt_ tier + time_ family rename, back-compat keys (FR-5)"`

### Task 3.3: Update sample config + docs for the renamed keys and the alt convention

**Files:**
- Modify: `tools/statusline.toml.sample`, `README`/`docs` mentioning segment keys

- [ ] **Step 1: Update the sample TOML** comments and any example `[segments]` entries to the new keys, with a one-line note that old keys still load.
- [ ] **Step 2: GATE.** `make validate && make test`.
- [ ] **Step 3: Commit.** `git add -A && git commit -m "docs(status-line): sample + docs for alt_ keys and back-compat (FR-5.3)"`

**Phase 3 deliverable:** three-phase packer with position-independent meta; `alt` block greppable via `seg_alt_`; back-compat config; golden byte-identical.

---

# Phase 4 — Introspection extraction (FR-7)

**Goal:** `tools/statusline-doctor.py` owns `--doctor`/`--check`/`--print-config` + `validate_config_file` + `_dry_render_failures` + `_DOCTOR_SAMPLE`; `status-line.py` renders only; install.sh + docs + tests updated; setup.py repointed.

### Task 4.1: Create `tools/statusline-doctor.py` importing the render core

**Files:**
- Create: `tools/statusline-doctor.py`
- Test: `tests/test_status_line.py` (the `TestDoctor`/`TestCheck`/`TestPrintConfig` classes move to a new `tests/test_statusline_doctor.py`)

- [ ] **Step 1: Create the doctor script** with the `importlib`/`sys.modules` shim to import the hyphenated render module (mirror `tests/test_status_line.py:load_module`):

```python
#!/usr/bin/env python3
"""ai-kit status-line doctor — config validation + dry-render introspection.

Renders nothing. Imports the render core (status-line.py) one-way and exercises
every builder against a sample to surface a builder that raises. CLI:
  --doctor         validate config AND dry-render every segment
  --check [FILE]   validate a config file
  --print-config   print the resolved config as JSON
"""
import argparse, importlib.util, os, sys
_CORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "status-line.py")
def _load_core():
    spec = importlib.util.spec_from_file_location("status_line", _CORE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod
sl = _load_core()
# ... move cmd_print_config, validate_config_file, _DOCTOR_SAMPLE,
#     _dry_render_failures, cmd_doctor, cmd_check, _NO_CHECK, _ENV_HELP, parse_args here,
#     rewriting bare calls (build_context, terminal_size, load_config, ...) as sl.<name>.
def main() -> None:
    ...
if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Move the introspection symbols** out of `status-line.py` into the doctor script: `cmd_print_config`, `validate_config_file`, `_DOCTOR_SAMPLE`, `_dry_render_failures`, `cmd_doctor`, `cmd_check`, `_NO_CHECK`, `_ENV_HELP`, and the `--doctor`/`--check`/`--print-config` flags from `parse_args`. The render module's `main()` becomes render-only (read stdin → `safe_render` → print).
- [ ] **Step 3: Repoint `_doctor_cmd`** in `status-line.py` so its "run the doctor" hint builds `python3 <doctor-script-path> --doctor` (resolve the sibling `statusline-doctor.py` path), not `status-line.py --doctor`. Keep `_doctor_cmd` in the render `core_` block — it is called only in the exception handler of `safe_render` and in `diagnostic_line` when a builder crashed; it must remain in the render module so it is available without importing the doctor script.
- [ ] **Step 4: Move the doctor tests** to `tests/test_statusline_doctor.py` with their own `load_module` for the doctor script; keep the render-module tests in `tests/test_status_line.py`. Add the new test module to `make test` and the pre-commit `unittest` hook.
- [ ] **Step 5: GATE + full suite.** `make validate && make test`. Run the moved tests explicitly: `python3 -m unittest tests.test_statusline_doctor -v`.
- [ ] **Step 6: Commit.** `git add -A && git commit -m "refactor(status-line): extract introspection to statusline-doctor.py (FR-7.1–7.3)"`

### Task 4.2: Repoint `setup.py`'s self-validation to the doctor script + install.sh + gate config

**Files:**
- Modify: `tools/setup.py` (line ~345 `subprocess.run([..., status_line, "--doctor"])` and the `status_line` path resolution at ~62), `tools/install.sh`, `pyproject.toml`, `.pre-commit-config.yaml`, docs

- [ ] **Step 1: Repoint `setup.py`'s doctor call.** Add a `statusline_doctor` path to `resolve_paths()` (sibling of `status_line`) and change the self-validation `subprocess.run` to invoke `[sys.executable, "-S", statusline_doctor, "--doctor"]` with `CC_AI_KIT_CONFIG_FILE=path`. Update `tests/test_setup.py` if it asserts the invoked command.
- [ ] **Step 2: Install the doctor script.** Update `tools/install.sh` / `setup.py` install logic to copy `statusline-doctor.py` alongside `status-line.py` and document it as the doctor entrypoint.
- [ ] **Step 3: Add `statusline-doctor.py` to the gate.** In `pyproject.toml`: add to `[tool.pyright] include`, `[tool.vulture] paths`. In `.pre-commit-config.yaml`: extend the `pylint` and `py-compile` `files:` regexes to `^tools/(status-line|statusline-doctor|setup)\.py$`.
- [ ] **Step 4: Update docs** — any reference to `status-line.py --doctor`/`--check`/`--print-config` becomes the doctor script; note the CLI migration (the render module intentionally no longer accepts these flags).
- [ ] **Step 5: GATE + full suite + shell tests.** `make validate && make test`. Verify `tools/statusline-doctor.py --doctor` runs against a temp config end-to-end.
- [ ] **Step 6: Commit.** `git add -A && git commit -m "build(status-line): install + gate + setup self-check use the doctor script (FR-7.4)"`

**Phase 4 deliverable:** dedicated doctor script; render module renders only; install/docs/tests/setup repointed; gate covers both modules.

---

# Phase 5 — Architecture (AST fitness) test (FR-8)

**Goal:** Lock the invariants in the gate via a stdlib-`ast` unittest.

### Task 5.1: Implement `tests/test_arch.py` with the FR-8.1 rules

**Files:**
- Create: `tests/test_arch.py`
- Modify: `.pre-commit-config.yaml`, `Makefile` (`test` target), `pyproject.toml` (ruff per-file-ignores if needed)

FR-8.1 rules to enforce (each a failing assertion):
1. Config env reads (`os.environ`/`env.get("CC_AI_KIT_...")`) occur only in the `cfg_` loader; whitelist FR-1.7 bootstrap + FR-1.8 SHELL/runtime (`STATUSLINE_*`, `COLUMNS`/`LINES`) + third-party (`CLAUDE_CONFIG_DIR`, `XDG_*`).
2. No subscript-load on the typed models (`Context`, `Config`/`line_conf`, `GitSnapshot`) — attribute access only (D4); `raw`/dict members exempt.
3. Only `seg_render_time`/`seg_slowest` read render bookkeeping (`ctx.slowest`, `t_start`).
4. Every `seg_*`/`seg_alt_*` has signature `(ctx, avail, theme)`.
5. The DEFAULTS block precedes the `cfg_` block and contains only data (FR-6).
6. Role-prefix integrity: a function's prefix matches the block it lives in.
7. The render module contains no introspection/doctor symbols (FR-7): no `cmd_doctor`/`cmd_check`/`cmd_print_config`/`validate_config_file`/`_DOCTOR_SAMPLE`.

- [ ] **Step 1: Write the test scaffold** that parses both modules with `ast`:

```python
import ast, os, unittest
_TOOLS = os.path.join(os.path.dirname(__file__), "..", "tools")
def _parse(name):
    with open(os.path.join(_TOOLS, name), encoding="utf-8") as f:
        return ast.parse(f.read(), filename=name)

class TestArchitecture(unittest.TestCase):
    def setUp(self):
        self.render = _parse("status-line.py")
        self.doctor = _parse("statusline-doctor.py")
    # one test method per FR-8.1 rule below
```

- [ ] **Step 2: Implement rule 7 first** (simplest, already true after Phase 4) — assert none of the doctor symbol names are defined in `self.render`. Run it — Expected: PASS (proves the harness works against the real tree).
- [ ] **Step 3: Implement rule 4** (segment signatures): walk `FunctionDef` nodes named `seg_*`; assert `args.args` names == `["ctx", "avail", "theme"]`.
- [ ] **Step 4: Implement rule 1** (env reads): find all `Attribute`/`Subscript` reads of `os.environ` or `.get(` on an `env`-typed name with a `CC_AI_KIT_` string arg; assert the enclosing `FunctionDef` name starts with `cfg_` or is the FR-1.7 bootstrap, except the FR-1.8 whitelist set.
- [ ] **Step 5: Implement rule 2** (no subscript-load on typed models): detect `ctx[...]`, `line_conf[...]`, `<GitSnapshot>[...]` `Subscript` in `Load` context; assert none. (Heuristic: flag `Subscript` where `.value` is a Name `ctx`/`line_conf` or attribute access to those — exclude `ctx.raw[...]`, `ctx.rate_limits[...]`, and dict members.)
- [ ] **Step 6: Implement rules 3, 5, 6** (bookkeeping readers; DEFAULTS-before-cfg ordering + data-only; role-prefix integrity). For ordering, compute the line numbers of the DEFAULTS banner and the first `cfg_` def. For role-prefix integrity, map each top-level `FunctionDef` to the banner block it falls under (by line ranges parsed from the `# ═══ N. <ROLE>` comments) and assert its prefix matches.
- [ ] **Step 7: Run the full arch test — Expected: PASS** against the refactored tree. If a rule fails, that is a real FR-8 violation introduced earlier — fix the source, not the test.
- [ ] **Step 8: Negative check (FR-8.3).** Temporarily introduce a deliberate violation (e.g. add `os.environ["CC_AI_KIT_X"]` inside a `seg_` function) and confirm the arch test FAILS; then revert.
- [ ] **Step 9: Wire into the gate.** Add `tests.test_arch` to the `Makefile` `test` target and the `.pre-commit-config.yaml` `unittest` hook entry (FR-8.2).
- [ ] **Step 10: GATE.** `make validate && make test` — Expected: all green including the arch test.
- [ ] **Step 11: Commit.** `git add -A && git commit -m "test(status-line): AST architecture fitness test in the gate (FR-8)"`

**Phase 5 deliverable:** green arch test enforcing every FR-8.1 invariant in `make validate`.

---

# Phase 6 — Commit compaction + merge

**Goal:** Land per the working agreements (commit compaction by logical unit; merge to local main `--no-ff`).

### Task 6.1: Compact working history into per-logical-unit commits

**Files:** none (git history)

`rebase -i` is blocked in this environment. Use the path-disjoint cherry-pick `-n` replay onto a temp branch (see memory `noninteractive-branch-compaction`). Target logical units (one coherent concern each), e.g.:
- `refactor(status-line): role-prefix vocabulary + contiguous blocks (Phase 1, FR-2/FR-6)`
- `refactor(status-line): thin ctx + line_conf + single env reader (Phase 2, FR-1)`
- `refactor(status-line): three-phase packer + alt tier (Phase 3, FR-4/FR-5)`
- `refactor(status-line): extract statusline-doctor.py (Phase 4, FR-7)`
- `test(status-line): AST architecture fitness test (Phase 5, FR-8)`

- [ ] **Step 1: Verify the branch is fully green before compaction.** `make validate && make test`.
- [ ] **Step 2: Replay commits grouped by logical unit** onto a fresh temp branch via `git cherry-pick -n` (squashing the WIP commits within each unit), committing each unit with a self-contained message. Confirm the working tree after each unit matches the pre-compaction tree (`git diff <pre-compaction-branch> --stat` is empty at the end).
- [ ] **Step 3: GATE on the compacted branch.** `make validate && make test`.

### Task 6.2: Final whole-implementation review + merge to local main

- [ ] **Step 1: Run `/review-spec`** (or `superpowers:requesting-code-review`) on the full diff against the PRD's Acceptance Criteria — confirm every FR-1…FR-8 checkbox is satisfied.
- [ ] **Step 2: Final gate.** `make validate && make test`. Confirm `tests/fixtures/golden/expected.txt` is byte-identical to `main`'s version (`git diff main -- tests/fixtures/golden/expected.txt` is empty).
- [ ] **Step 3: Merge to local main `--no-ff`.**

```bash
git checkout main
git merge --no-ff refactor/status-line-architecture-refinement \
  -m "merge: status-line architecture refinement (FR-1..FR-8)"
make validate && make test    # final post-merge gate
```

(Per the standing choice, do NOT push unless the user asks.)

- [ ] **Step 4: Update memory** — record the refinement merged to local main, the new env-name convention, the alt-key back-compat, and the doctor script split.

**Phase 6 deliverable:** clean per-unit history; merged refinement on local main; golden byte-identical; memory updated.

---

## Acceptance Criteria → Task Map (self-review coverage)

| PRD criterion | Covered by |
|---|---|
| FR-1 (thin ctx + line_conf; probes out) | Tasks 2.1–2.4 |
| FR-1.6 (single env reader, convention) | Task 2.5 |
| FR-1.9 (`CLAUDE_EFFORT` gone) | Task 2.6 |
| FR-2 (role prefixes + blocks) | Tasks 1.2–1.6 |
| FR-4 (three-phase packer, position-independent meta) | Task 3.1 |
| FR-5 (core/alt partition, `time_` family, back-compat) | Tasks 3.2–3.3 |
| FR-6 (DEFAULTS-first data-only, `cfg_` after) | Task 1.5 |
| FR-7 (doctor script; render-only module; install/docs/tests) | Tasks 4.1–4.2 |
| FR-8 (AST arch test in the gate) | Tasks 5.1 |
| Golden byte-identical every task | Hard Constraint 1, every task's verify step |
| Static gates green | Hard Constraint 3, every task |
| No new runtime dependency | Hard Constraint 4 |
| Commit compaction + merge | Tasks 6.1–6.2 |

## Open implementation choices left to the executor (per PRD)

- Whether `_DOCTOR_SAMPLE` stays a literal in the doctor script or moves to a fixture (FR-7.5) — default: keep it a literal in the doctor script (self-contained, no fixture file).
- `probe_git_for(ctx)` memoization is locked: per-render ctx cache via `_memo(ctx, "git", ...)` — no `lru_cache` (avoids cross-render leak across the multi-case golden).
- Whether widely-referenced entrypoints (`pack_line`/`render`/`load_config`/`build_context`) get the `core_`/`cfg_` prefix or keep their names — default: rename them and update all `sl.*` test references (cleanest for FR-8.1 role-prefix integrity).
