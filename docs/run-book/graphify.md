# graphify runbook

The steps to build, refresh, check and query the code and document graph that
ai-kit's agents read. Which index to use, and when, is the rule in AGENTS.md
under `## Code Exploration`; this file holds the steps.

## Build

- Run `graphify update .` from the repository root. It is AST-only (no LLM call)
  and honors the root `.graphifyignore`, which excludes `.planning/milestones/`.
- `/gsd-graphify build` runs the same build, then copies `graph.json`,
  `graph.html` and `GRAPH_REPORT.md` into `.planning/graphs/`. It stops after the
  config gate unless `graphify.enabled` is `true` in `.planning/config.json`
  (`.claude/commands/gsd-graphify.md`, Step 1).
- Two locations, one build. `graphify-out/` holds raw graphify output. The
  `.planning/graphs/` copy is for GSD's agents: `.planning/graphs/` is GSD's
  default location, the path GSD reads when `graphify.graph_path` is not set.
  The same build and the same copy feed both.
- `graphify update` cannot write to `.planning/graphs/` directly: it rejects
  `--graph` with "unknown update option". The copy step does that work, not a flag.
- `graphify.graph_path` in `.planning/config.json` moves GSD's location. When it
  is set, GSD reads that path (`.claude/gsd-core/bin/lib/graphify.cjs`,
  `resolveGraphLocation`), and the boundary step keeps `graphify-out/` only.
- A project without GSD, or with `graphify.enabled` not `true`, skips the copy into
  `.planning/graphs/` and keeps `graphify-out/` only.
- A rebuild can be rerun safely and gives the same graph at the same HEAD.
- Timings, measured on 2026-11-03 on this machine, not guarantees: about 15 s
  with the `.graphifyignore` exclusion and 21 s without it; `codegraph sync`
  0.23 s; `codegraph init -y` 12.5 s.

## Refresh

- The unit flow's boundary step refreshes both indexes at a unit's start, before
  its planning and before its first execution wave.
- Every new worktree gets a refresh through ai-kit's `post-checkout` hook. It runs
  as a detached job, one per repository at a time.
- GSD's auto-update runs after commits, only on the default branch. It does not
  fire for `node .../gsd-tools.cjs query commit`, `gsd_run query commit` or
  `git update-ref` (the fold), so stacked branches go stale unless refreshed.
- Do not start a manual build while GSD's `.planning/graphs/.rebuild.lock` or the
  step's lock `.git/ai-kit-index.lock` (in the git common dir) is held.

## Check freshness

- Run `node .claude/gsd-core/bin/gsd-tools.cjs graphify status` and compare its
  `built_at_commit` with `git rev-parse --short HEAD`.
- GSD's own staleness thresholds, as read from gsd-core 1.20.0: a graph older than
  24 h, or a running or failed last build, is stale.
- Being commits behind is reported, but it is not a staleness signal.

## Query

- `graphify query "<question>"`, `graphify path`, `graphify explain` and
  `graphify affected` answer from a graph. There is no `search` command.
- In a project without GSD, query `graphify-out/graph.json`.
- For GSD's copy, add `--graph .planning/graphs/graph.json`.
