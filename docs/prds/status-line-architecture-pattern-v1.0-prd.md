# Status-line Architecture Pattern — PRD

> **Scope.** A structural overhaul of `tools/status-line.py` (and the shared parts of
> `tools/setup.py` it touches) to a single, named, maintainable pattern. It is the **follow-up**
> to the render refactor (`refactor/status-line-render`, PRD `status-line-render-refactor-v1.0`).
> It is **behavior-preserving** — every existing test must stay green and the rendered output must
> not change — while the file's internal architecture is rebuilt. Forks off `main` **after** the
> render refactor has merged.
>
> **Origin.** Review of the render refactor surfaced that `build_data` hand-enumerates every core
> field, which couples the data layer to the segment set (see `docs/architecture/status-line-pipeline.md`
> §7). The maintainer's broader critique: env is read in ~12 scattered places; the `BUILDERS`
> registry is redundant hand-maintenance; helpers leak their TTL knobs to callers; there are no
> type hints; and the file lacks a clear, repeatable structure for a single-file script.

## Requirements Description

### Background

- **Business problem.** `tools/status-line.py` grew feature-by-feature (E4–E7, then the render
  refactor) into a ~2000-line single file with no overarching pattern. Concrete symptoms:
  1. **Scattered config.** `env.get(...)` / `os.environ` is read in ~12 places across the file
     (`config_path`, `_resolve_external`, git-ttl resolver, `_cache_base`, `_segments_dir`,
     `_run_provider`, `terminal_size`, `resolve_effort`, `build_data`, `main`). There is no single
     "resolve config at the edge" boundary.
  2. **A coupling data layer.** `build_data` builds a flat dict by hand-enumerating ~15 core fields,
     each read by exactly one segment. The enumeration tracks the segment set, so adding a core
     segment that needs new data forces a `build_data` edit.
  3. **A redundant registry.** `BUILDERS` maps `"name": seg_name` for all 20 segments — every entry
     is homologous (`seg_time_ago` → `time_ago`), so the dict is hand-maintained drift risk.
  4. **Leaky helpers.** Callers thread `git_ttl`/`untracked`/`want_worktree` into the git probe; the
     probe should own its own caching policy.
  5. **No types.** The file is untyped; pyright runs in `basic`. There is no static guarantee of the
     shapes flowing between layers.
  6. **No pattern.** Functions are grouped by loose banners but there is no stated architecture a
     contributor can follow to add or change a segment safely.
- **Target users.** ai-kit maintainers (a file they can hold in their head and edit without fear)
  and contributors (one obvious way to add a segment).
- **Value.** A status line built on a single, named pattern — *functional core / imperative shell*
  with a config object, a per-render context, convention-discovered builders, and strict types — so
  the script stays a script but reads as intentional, scalable engineering.

### Locked architectural decisions

These were settled in the brainstorming dialogue and are **not** open during implementation:

| # | Decision | Resolution |
|---|---|---|
| D1 | Per-render data shape | **One `ctx` bag** passed to every builder. Eager inputs + `functools.cached_property` lazy probes + the two render-bookkeeping fields (`failed`, `slowest`) live on it. Pragmatic uniformity over purity. |
| D2 | File layout | **Single file.** `status-line.py` is installed as one standalone script (symlinked/copied; the `statusLine` setting points at one path). No module split. Structure is carried by banner-delimited blocks. |
| D3 | Naming convention | **Light prefixes + banners.** `# ═══` section banners + noun-grouping (`_git_*`, `_cache_*`) + plain `_` for private. No heavy role prefixes (`_seg_helper_git`). |
| D4 | `obj[key]` subscript ban | Applies to **our own types** (the `ctx`/`Config` objects → attribute access only). The incoming `raw` JSON keeps `.get()`-chain access (safer; avoids `KeyError`). |
| D5 | Typing sequence | **Types last.** Strict hints + strict linters (incl. the subscript ban) land **after** all structural simplification, dedup, prefix/block reorg, and tests are green — as one dedicated pass, not interleaved. |
| D6 | Config vs Context boundary | **`Config` = stable only** (env + TOML: palette, ramps, thresholds, segment on/off defaults, git ttl, cache dirs). **Per-render** inputs — terminal size and the stdin `raw` JSON — live on `Context`, never `Config`. Mirrors dotenv (stable config) vs per-request data. |
| D7 | Discovery scope | **Auto-derive `BUILDERS` only** from the module's `seg_*` functions (homologous suffix). `SEGMENTS` (on/off) stays an **explicit internal-defaults table** alongside `_RAMP_DEFAULTS`/`_PALETTE_DEFAULTS`/`_EFFORT_DEFAULTS`; `LAYOUT` stays explicit (deliberate order/lines). Discovery removes only the redundant name→fn list, not the tables that encode intent. |

### The pattern (target architecture)

*Functional core, imperative shell* + config-object DI + convention-based registry. Six
banner-delimited blocks in one file, in dependency order:

```
1. SHELL (main)      side effects only: timestamp, read os.environ, read stdin JSON, print
2. CONFIG            the ONLY block that reads env/TOML → one immutable Config (STABLE only)
3. CONTEXT           per-render bag: raw JSON, config, theme, terminal size, t_start (eager)
                     + cached_property probes (git/todo/ago/rss/effort-auto)
                     + render bookkeeping (failed, slowest)
4. HELPERS           probes own their own caching/TTL; read only what ctx/config give them
5. SEGMENTS          seg_x(ctx) -> str | None, self-sourcing, auto-discovered by convention
6. LAYOUT / PACK     fully segment-agnostic: knows keys, the discovered builder map, widths
```

### Feature Overview

- **FR-A.1 — Config object boundary.** All env/TOML reads consolidate into the CONFIG block, which
  produces one immutable `Config` carrying **stable settings only**. No `os.environ` / `env.get`
  access anywhere downstream; derived paths (e.g. the segments cache dir) become `Config` fields,
  not standalone helpers. Per-render inputs — terminal size and the stdin `raw` JSON — are resolved
  by the SHELL and handed to the `Context`, **not** folded into `Config`. (D4/D6)
- **FR-A.2 — `Context` replaces `build_data` + `_LazyData`.** A `Context` object carries eager
  inputs, `cached_property` lazy probes, and the render-bookkeeping fields. The hand-enumerated
  core fields collapse: each is read by the single segment that needs it, directly from
  `ctx.raw`. The first read of a probe still fires inside the measured build of the segment that
  triggers it — **FR-R.2 (truthful `slowest`) must be preserved, with a test proving it.** (D1)
- **FR-A.3 — Convention-discovered builders.** Replace **only** the hand-maintained `BUILDERS` dict
  with a one-time discovery of module `seg_*` functions, keyed by the homologous suffix. External
  providers merge into the same map. `SEGMENTS` (on/off) stays an **explicit internal-defaults
  table** alongside the existing `_RAMP_DEFAULTS`/`_PALETTE_DEFAULTS`/`_EFFORT_DEFAULTS`, and
  `LAYOUT` stays explicit — discovery removes the redundant name→fn list, never the tables that
  encode intent (which segments default on, in what order, on which line). (D7)
- **FR-A.4 — Encapsulated helpers.** The git probe (and any other shared helper) owns its caching
  policy and TTL; callers pass `ctx`/`Config`, never raw knobs. Helper grouped under one banner.
- **FR-A.5 — Block/structure reorg.** Reorganize the whole file into the six blocks above with
  banners and the D3 naming convention. Externals get their own delimited block. No behavior change.
- **FR-A.6 — Strict typing pass (last).** Add input/output/variable type hints throughout; flip
  pyright to `strict`; enable the linter rules that enforce typing and **ban `obj[key]` subscript
  on our types**. Resolve every finding (fix, not suppress). This is the final task. (D5)

### Non-goals

- No new segments, no rendering/layout behavior changes, no new config surface. Pure restructure.
- No multi-file split (D2). No change to the external-provider protocol (only its code location).
- No change to `make test` running on system python3, or to the pre-commit-is-source-of-truth gate.

### Acceptance criteria

**Behavior preservation (the safety net — D-reuse).** The render refactor's golden snapshot +
508-test suite **are** the net; no new test infra is added. They must stay green and the golden
byte-identical at **every step** of the overhaul (verify after each task, not just at the end).

- [ ] Every existing test passes unchanged; the golden snapshot is byte-identical (no output drift).
- [ ] A test asserts a probe's cost is captured inside the triggering segment's measured build
      (FR-R.2 invariant survives the `Context` move).
- [ ] `grep` finds **no** `os.environ`/`env.get` outside the CONFIG block.
- [ ] `grep` finds **no** `ctx[...]`/`config[...]` subscript on our own types (attribute access only).
- [ ] `BUILDERS` hand-maintenance is gone; adding a `seg_x` function auto-registers it; `SEGMENTS`/
      `LAYOUT` remain explicit defaults tables.
- [ ] `Config` carries stable settings only; terminal size + `raw` JSON live on `Context`.
- [ ] `make validate` green with pyright `strict` and pylint design thresholds at defaults
      (args=5, locals=15, branches=12, returns=6) for the render path — closed by dissolving
      `build_data` and the single `ctx` bag.
- [ ] The six-block structure is present and a short in-file contract note describes the pattern.

## Execution Phases

> Detailed task breakdown is the `writing-plans` deliverable; this is the phase skeleton and
> ordering. Each phase keeps the golden + suite green before the next begins. **Behavior-preserving
> throughout** — types are the last phase (D5).

### Phase 1: Config boundary
**Goal:** one `Config` (stable only); zero downstream env reads.
- [ ] Consolidate every `env.get`/`os.environ` read into the CONFIG block; turn derived paths
      (cache dirs, segments dir) into `Config` fields; delete the now-redundant path helpers.
- [ ] **Deliverable:** `grep` shows no env access outside CONFIG; suite green.

### Phase 2: Context replaces build_data
**Goal:** dissolve `build_data`/`_LazyData` into a `Context` with `cached_property` probes.
- [ ] Introduce `Context`; move the hand-enumerated core fields into the single consuming segment
      (read from `ctx.raw`); keep the FR-R.2 truthful-slowest test green.
- [ ] **Deliverable:** `build_data` gone; `slowest` still ms-scale; suite green.

### Phase 3: Convention registry + encapsulated helpers
**Goal:** auto-derive `BUILDERS`; helpers own their TTL/caching.
- [ ] Replace the `BUILDERS` literal with `seg_*` discovery; route the git probe's ttl through
      `Config` so no caller threads knobs.
- [ ] **Deliverable:** adding a `seg_x` auto-registers; suite green.

### Phase 4: Block/structure reorg
**Goal:** the six banner-delimited blocks + D3 naming; externals in their own block.
- [ ] Reorder the file into the blocks; apply naming convention; add the in-file contract note.
- [ ] **Deliverable:** structure present; behavior unchanged; suite + golden green.

### Phase 5: Strict typing (last)
**Goal:** full type hints; pyright `strict`; subscript ban; pylint design at defaults.
- [ ] Add hints throughout; flip pyright to `strict`; enable typing + subscript-ban rules; resolve
      every finding by fixing (not suppressing); push pylint design thresholds to defaults.
- [ ] **Deliverable:** `make validate` green under the strict ruleset; suite + golden green.

---

**Document Version:** 1.0
**Clarification:** requirements-clarity pass — 1 round (config boundary, discovery scope, safety
net resolved → D6/D7 + reused net). **Quality Score:** 94/100.

### Risks / notes

- **`slowest` truthfulness is the load-bearing invariant.** `cached_property` preserves it (first
  access runs synchronously inside the caller), but any redesign must keep an explicit test or it
  silently regresses to µs-scale.
- **Behavior-preservation is verified by the golden snapshot + full suite**, which already exist
  from the render refactor — this overhaul inherits them as its safety net.
- **Strict typing on a ~2000-line untyped file** will surface many findings at once; D5 isolates it
  as the final pass so it is reviewable on its own and never blocks the structural work.
- Out-of-scope CLI/setup complexity (`validate_config_file`, `select_skills`, etc.) is not a target
  here; only the render path and the shared config/cache helpers are in scope.
