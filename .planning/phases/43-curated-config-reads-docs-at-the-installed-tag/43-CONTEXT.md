# Phase 43: curated-config reads docs at the installed tag - Context

**Gathered:** 2026-11-23 (interactive, after 43-SPEC.md)
**Status:** Ready for planning

<domain>
## Phase Boundary

curated-config reads open-gsd docs at the installed version's tag (cached per version under `.aikit/`), offers a project-local
update only when the changelog makes it worth it (labeled by impact), asks one grouped cascade in place of today's four questions,
and records a run of each v1 subcommand on a fixture project so the owner decides keep, merge or remove per command.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**5 requirements are locked.** See `43-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `43-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):** the tagged-docs fetcher and cache, the changelog reader and impact labeling, the update offer, the
cascade, the v1 run and decision records, docs, evals and the judge loop.
**Out of scope (from SPEC.md):** writing the agreed settings (Phase 44); running the update, `gsd update` or any `~/.claude`
write; removing v1 code without its decision row; docs for other hosts, other versions' caches, the shared jev client.

</spec_lock>

<decisions>
## Implementation Decisions

### Docs fetch and cache
- **D-01: The fetch uses stdlib `urllib.request` against raw GitHub at the tag** (`https://raw.githubusercontent.com/open-gsd/
  gsd-core/v<version>/<path>`), with a timeout and a size cap, after the skill's network ask. The repository slug and the tag
  prefix are seed data in one place, labeled with their source (checked 2026-11-23: repository `open-gsd/gsd-core`, tag
  `v1.22.0` exists), never a decider: a missing tag is reported. **Own reasoning** (jev not asked): runtime code is stdlib-only
  and `gh` may be absent. Ledger.
- **D-02: The first docs set is `CHANGELOG.md` plus the `docs/` pages that document the config keys curated-config writes**; the
  exact page list is found at plan time from the tagged `docs/` tree (one contents listing at the tag) and recorded as seed data.
  The installed `references/planning-config.md`, `settings.md` and `settings-advanced.md` are the offline fallback, labeled "installed
  copy, not the tagged docs". **Own reasoning.** Ledger.
- **D-03: The cache is `.aikit/gsd-docs/<version>/<path>` plus a `meta.json`** (fetched_at, tag, sha256 per file), written with a
  temp file and an atomic replace, size-capped, path-checked (a version string with a path character is refused). ai-kit prints
  a `.gitignore` suggestion and writes none. **Own reasoning.** Ledger.

### Update offer
- **D-04: The latest version comes from the package registry** (`https://registry.npmjs.org/@opengsd%2fgsd-core/latest`, stdlib
  fetch, same consent and label rule); installed newer than latest means no offer. **Own reasoning.** Ledger.
- **D-05: A new labeler module** (name at plan time) labels each changelog entry high, medium or low: jev through the
  `jev_names` pattern (summaries only, one item per entry), with a keyword default (high: security, data loss, breaking, or
  text naming a config key curated-config writes; medium: fix or feature naming a workflow curated-config relies on; low
  otherwise). Any answer that is low-confidence or missing uses the default and the run says "default". *(rule shape owner-chosen,
  details own reasoning)* Ledger.
- **D-06: The offer reuses the `followups` machinery** (approval-gated, pinned `@opengsd/gsd-core@<version> --<host> --local`
  argv, never a dist-tag name); nothing here runs an installer. *(owner rule)*

### Cascade and v1
- **D-07: Step 2 of SKILL.md becomes the cascade** in one message: MVP, UI, granularity (beside MVP), runtime (asked only when
  another host is detected), and the base branch shown for confirmation. `recommend` keeps its flags; a small mapping (seed
  table, pinned by a test) turns the MVP answer into rigor (`mvp` or `standard`), and `rigorous` and the cross-AI plan review
  choice stay reachable as `plan-set` edits shown with their derived defaults in the plan review (owner decision 2026-11-23).
  The names of the GSD keys behind MVP, UI and granularity come from the tagged docs of D-02. Ledger.
- **D-08: The base branch is read through GSD's own resolver** (`git-base-branch.cjs`: config override, `origin/HEAD`,
  `git remote show origin`, local branches, `main`), through the project's `gsd-tools` (the exact verb is a plan-time check),
  and shown for confirmation. It detects the repository's default branch; whether that equals "where the merge flow lands"
  (stacked units merge into `main`) is the owner's confirmation. **Own reasoning.** Ledger.
- **D-09: The v1 run record is produced by a script under the phase's folder** that runs the eleven subcommands in the v1 path's
  order (`ensure-project` first) on a fixture project in a scratch directory with a scratch HOME and writes one row each; the
  owner's keep, merge or remove decisions are collected at a checkpoint in this phase's plan with the record as evidence; a
  guard test blocks removing a v1 entry point without a `remove` row. Whether `apply-workflow-defaults` is also a v2 step is a
  plan-time check. **Own reasoning.** Ledger.

### Order
- **D-10: Build order is a vertical slice.** (1) the v1 run record (evidence first, it blocks nothing else); (2) the tagged-docs
  fetcher and cache; (3) the changelog reader, labeler and offer; (4) the cascade and its mapping; (5) evals, docs and the
  skill-judge loop of `ai-kit-gsd-curated-config`.

### Claude's Discretion
Module names, the seed page list, the cache metadata fields, the keyword lists, and the exact cascade wording.

### Folded Todos
None folded.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked requirements
- `.planning/phases/43-curated-config-reads-docs-at-the-installed-tag/43-SPEC.md` — Locked requirements — MUST read before planning
- `.planning/ROADMAP.md` §Phase 43 and `.planning/REQUIREMENTS.md` CUR-01, CUR-02, CUR-10

### Earlier decisions and docs
- `.planning/phases/36-spec-config-as-the-hub/36-CONTEXT.md` (hub, config check), `.planning/phases/40-resilient-review-sized-by-jev/
  40-CONTEXT.md` D-06 (the jev adapter pattern)
- `skills/ai-kit-gsd-curated-config/references/v1-path.md` (the eleven v1 subcommands and their order)

### Code and docs the phase touches
- `skills/ai-kit-gsd-curated-config/SKILL.md` (Step 1 network ask lines 79-81, Step 2 questions line 92), `ai_kit_gsd_curated_config/
  cli.py`, `gsd_catalog.py` (`resolve_gsd_tools_path`), `followups.py` (pinned install argv), `recommend.py`, `inventory.py`,
  `frontend_detect.py`, `claude_md_detect.py`
- `.claude/gsd-core/bin/lib/git-base-branch.cjs`, `.claude/gsd-core/references/planning-config.md`, `settings.md`,
  `settings-advanced.md` (read only)

### Tests that pin or must keep passing
- `tests/test_curated_config_*.py`, `tests/test_gsd_curated_eval.py`, `tests/test_ai_kit_gsd_curated_config.py`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `resolve_gsd_tools_path` and the project's `gsd-tools` for the installed version; `followups.py` for the pinned install argv;
  the `jev_names` pattern; `recommend`'s existing rigor and cross-AI inputs.

### Established Patterns
- A table is seed data labeled with its source, never a decider; a missing fact is reported, not guessed.
- Every jev path has a tested no-jev behavior; only summaries go to jev.
- Writes are atomic and never touch user-level config; tests use a scratch HOME.

### Integration Points
- SKILL.md Step 1 (network ask), Step 2 (questions), Step 3 (plan review), the follow-up approval step, `recommend` inputs.

</code_context>

<specifics>
## Specific Ideas

The installed 1.22.0 against `latest` 1.23.0 (checked 2026-11-23) gives the first real fixture for the update offer.

</specifics>

<deferred>
## Deferred Ideas

- A cache clean-up command for old versions (only the installed and the latest are cached now).
- Reading the tagged docs for hosts other than the installed gsd-core's.

### Reviewed Todos (not folded)
- 26 other todos matched by keyword only; none concerns the docs fetch, the cascade or the v1 records.

</deferred>

---

*Phase: 43-curated-config reads docs at the installed tag*
*Context gathered: 2026-11-23*
