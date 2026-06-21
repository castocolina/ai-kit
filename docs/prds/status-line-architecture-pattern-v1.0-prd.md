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

### The pattern (target architecture)

*Functional core, imperative shell* + config-object DI + convention-based registry. Six
banner-delimited blocks in one file, in dependency order:

```
1. SHELL (main)      side effects only: timestamp, read os.environ, read stdin JSON, print
2. CONFIG            the ONLY block that reads env/TOML → one immutable Config object
3. CONTEXT           per-render bag: raw, config, theme, terminal, t_start (eager)
                     + cached_property probes (git/todo/ago/rss/effort-auto)
                     + render bookkeeping (failed, slowest)
4. HELPERS           probes own their own caching/TTL; read only what ctx/config give them
5. SEGMENTS          seg_x(ctx) -> str | None, self-sourcing, auto-discovered by convention
6. LAYOUT / PACK     fully segment-agnostic: knows keys, the discovered builder map, widths
```

### Feature Overview

- **FR-A.1 — Config object boundary.** All env/TOML reads consolidate into the CONFIG block, which
  produces one immutable `Config`. No `os.environ` / `env.get` access anywhere downstream; derived
  paths (e.g. the segments cache dir) become `Config` fields, not standalone helpers. (D2/D4)
- **FR-A.2 — `Context` replaces `build_data` + `_LazyData`.** A `Context` object carries eager
  inputs, `cached_property` lazy probes, and the render-bookkeeping fields. The hand-enumerated
  core fields collapse: each is read by the single segment that needs it, directly from
  `ctx.raw`. The first read of a probe still fires inside the measured build of the segment that
  triggers it — **FR-R.2 (truthful `slowest`) must be preserved, with a test proving it.** (D1)
- **FR-A.3 — Convention-discovered builders.** Replace the hand-maintained `BUILDERS` dict with a
  one-time discovery of module `seg_*` functions, keyed by the homologous suffix. External
  providers merge into the same map. `SEGMENTS` (the on/off flags + defaults) stays explicit.
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

- Every existing test passes unchanged; the golden snapshot is byte-identical (no output drift).
- A test asserts a probe's cost is captured inside the triggering segment's measured build
  (FR-R.2 invariant survives the `Context` move).
- `grep` finds **no** `os.environ`/`env.get` outside the CONFIG block; **no** `ctx[...]`/`config[...]`
  subscript on our own types.
- `BUILDERS` hand-maintenance is gone; adding a `seg_x` function auto-registers it.
- `make validate` is green with pyright in `strict` mode and the design thresholds at pylint
  defaults (the render-refactor branch ratcheted them part-way; this branch finishes the job by
  dissolving `build_data` and cutting builder arg-counts via `ctx`).
- The six-block structure is present and a short in-file contract note describes the pattern.

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
