# Phase 13: Docker Rules Checker (ai-kit-project-rules-docker) - Context

**Gathered:** 2026-09-13
**Status:** Ready for planning — BLOCKED on Phases 9-12 landing first (see Phase Boundary)

> **Corrected 2026-09-14 (Phase 13 plan 04):** Phases 9-12 have since landed — each has a
> committed `SKILL.md` (`skills/ai-kit-project-rules-agents/SKILL.md`,
> `skills/ai-kit-project-rules-makefile/SKILL.md`,
> `skills/ai-kit-project-rules-precommit/SKILL.md`,
> `skills/ai-kit-project-rules-arch/SKILL.md`, all confirmed present live during this phase's own
> Task 3 precondition). This phase's hard prerequisite REASONING is unchanged and was satisfied,
> not waived — the dependency was real, it is simply now met. Phase 14 reads this file and would
> otherwise read a satisfied prerequisite as an open blocker.

<domain>
## Phase Boundary

New skill `ai-kit-project-rules-docker` checks docker-compose/Makefile
conventions for local-dev Docker workflows: the 8-target family
(`docker-up`/`docker-health`/`docker-stop`/`docker-clean`/`docker-prune`/
`docker-events-up`/`docker-events-monitor`/`docker-events-test`),
healthcheck timing bounds, `depends_on` discipline (`condition:
service_healthy`), the hot-reload convention for local-dev services, and
runbook (`docker/local/README.md`) presence. ai-kit's own repo has no
`docker-compose.yml`/`Dockerfile` today (confirmed by scouting) — unlike
Phase 12's `arch-test`, this skill has no real self-example in ai-kit;
every behavior is proven by synthetic fixtures only (already the ROADMAP's
own framing — all 5 success criteria are fixture-based).

> **Corrected 2026-09-14 (Phase 13 plan 04):** True of the LOCAL-DEV workflow this skill checks
> and true at the repository ROOT (re-confirmed live: no `docker-compose.yml`/`docker-compose.yaml`/
> `compose.yml`/`compose.yaml`/`Dockerfile` at ai-kit's own repo root), but the repo does carry a
> CI-only `tests/e2e/docker/Dockerfile` behind its `e2e-docker` Makefile target — exactly the pair
> of edges 13-01's root-scoped applicability gate (D-D4) is shaped around. The distinction is not
> pedantry: a later reader who takes the original wording literally would conclude the gate's
> nested-evidence negative case was invented rather than drawn from this repository. The original
> claim's CONCLUSION — that this phase has no real self-example and must be proven by synthetic
> fixtures — is unchanged and correct.

**Hard prerequisite — this phase cannot be planned or executed before
Phases 9-12 actually land.** `.planning/ROADMAP.md`'s "Depends on" line
for Phase 13 names Phase 12 directly; the full chain back to Phase 9 is
unbroken. As of this discussion, NONE of Phases 9-12 have a plan or
execution yet (each has only a CONTEXT.md).

> **Corrected 2026-09-14 (Phase 13 plan 04):** Phases 9-12 have all since landed with committed
> `SKILL.md` files (see the correction on the header `**Status:**` line above for the exact paths
> confirmed live). The hard-prerequisite REASONING above is unchanged and was satisfied, not
> waived — the dependency chain back to Phase 9 was real, it is simply now fully met.

</domain>

<decisions>
## Implementation Decisions

### YAML parsing approach
- **D-01:** `docker-compose.yml` is parsed with indentation-aware regex/
  text parsing, stdlib-only — NOT a YAML library dependency. Rationale:
  `.pre-commit-config.yaml` is already parsed this exact way in the
  current codebase (`_iter_precommit_hook_blocks`/`_ID_LINE_RE`/
  `_ENTRY_LINE_RE` in `makefile_checker.py`), no `yaml` package is
  installed, and `PROJECT.md`'s "Runtime dependency discipline" constraint
  keeps shipped/runtime code stdlib-only. Because `docker-compose.yml`
  nests more deeply than the flat pre-commit-hooks list (`services:` →
  service name → `healthcheck:`/`depends_on:` sub-keys), the parser MUST
  track indentation level to correctly attribute a `healthcheck:` or
  `depends_on:` block to its owning service — a flat line-scan (adequate
  for pre-commit hooks) is not sufficient here.
  — **Reversibility:** costly — switching to a real YAML library later
  means rewriting this skill's parsing layer, not a local tweak, and would
  be the first dependency-discipline exception in this skill family.

  > **Corrected 2026-09-14 (Phase 13 plan 04):** This precedent citation is now stale in its
  > exact names. The `.pre-commit-config.yaml` block-reading logic converged into
  > `skills/_shared/ai_kit_rules_common/precommit_parse.py`, where the block iterator is now
  > PUBLIC (`iter_precommit_hook_blocks`, no leading underscore) while `_ID_LINE_RE`,
  > `_ENTRY_LINE_RE`, and `_strip_yaml_quotes` stayed private in that module. The `makefile_checker.py`
  > that now exists (`skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/makefile_checker.py`)
  > does NOT house this pre-commit-hook parsing logic. The PRECEDENT itself was real and was
  > followed — see the correction on "Existing parsing precedent" below for the full path history.
- **D-02:** No new dependency is added anywhere in this skill or
  `skills/_shared/` as a result of D-01.

### Local-dev service identification
- **D-03:** Local-dev service definitions are identified by a dedicated
  file-name convention (`docker-compose.override.yml` or
  `docker-compose.local.yml`), not by Compose "profiles" detection.
  Rationale: matches the design spec's own framing that local-dev assets
  live at a dedicated location (`docker/local/container/`) — a dedicated
  local-dev compose file is the consistent counterpart, and profiles
  support isn't hinted at anywhere in the design spec.

### Hot-reload check scope (expanded from the design spec's own wording)
- **D-04:** The hot-reload check is stack-aware, not a generic bind-mount-
  only heuristic. Beyond confirming a local-dev service uses a bind-mount
  plus a dev-command override (the design spec's literal wording), the
  checker must also verify the override command actually invokes a
  stack-appropriate hot-reload/dev-server tool — e.g. a Node service's dev
  command should run a dev server with HMR (Vite, webpack-dev-server,
  `nodemon`, etc.), a Python/Flask service should run Flask's own
  debug/reloader mode (or an equivalent watcher) — rather than treating
  "any bind-mount + any override command" as sufficient. This came
  directly from the user: a bind-mount alone proves nothing about whether
  the dev workflow actually reloads on change if the override command
  itself is just the production entrypoint with no watch/reload flag.
  — **Reversibility:** costly — this expands the check's data needs to
  per-stack hot-reload-tool knowledge; descoping back to the generic
  bind-mount-only check later would mean removing a check users may
  already depend on, not a local tweak.
- **D-05:** D-04's per-stack hot-reload-tool knowledge is a natural
  extension of the already-converged per-language tool catalog from
  Phase 11's D-01 (`skills/_shared/ai_kit_rules_common/`) — add a
  hot-reload/dev-server column/category to that same shared catalog
  rather than hardcoding a third, independent per-stack tool list local to
  this skill. Uses the already-shared `detect_stacks()` (Phase 10's D-02)
  to determine which stack's hot-reload convention applies to a given
  service.
  — **Reversibility:** reversible — adding one more column to an existing
  shared catalog is a small, additive change; no migration.

### Everything else — already locked by ROADMAP + design spec
- **D-06:** The target family, healthcheck numeric bounds (timeout ≤ 2s,
  start_period ≤ 10s, interval ≤ 5s), `depends_on` discipline, and runbook-
  presence check are accepted as written in ROADMAP Success Criteria 1-3
  and 5 — no scope changes surfaced for those.

### Claude's Discretion
- Exact regex/indentation-tracking implementation for D-01 (e.g. a small
  state-machine tracking current indentation depth vs. a simpler "next
  line at a shallower or equal indent ends this block" heuristic like
  `_iter_precommit_hook_blocks` already uses for hook blocks).
- Exact shape of D-05's hot-reload-tool catalog extension (new top-level
  category vs. a dedicated dict keyed by stack) — left to whoever
  implements Phase 11's shared catalog first; Phase 13 just needs to
  consume it.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design spec and roadmap
- `docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`
  §"`ai-kit-project-rules-docker` (new)" — the authoritative target
  family, healthcheck/depends_on/hot-reload/runbook requirements this
  phase implements (D-04/D-05 expand the hot-reload item beyond this
  section's literal text — see rationale above)
- `.planning/ROADMAP.md` §"Phase 13: Docker Rules Checker
  (ai-kit-project-rules-docker)" — goal, the Phase-12 dependency note, and
  the 5 fixture-provable success criteria
- `.planning/REQUIREMENTS.md` — `REQ-rules-docker` (Traceability table,
  v1.2 section)
- `.planning/PROJECT.md` §"Constraints" — "Runtime dependency discipline"
  line motivating D-01/D-02
- `.planning/phases/10-makefile-rules-checker-ai-kit-project-rules-
  makefile/10-CONTEXT.md` and `.planning/phases/11-pre-commit-rules-
  checker-ai-kit-project-rules-precommit/11-CONTEXT.md` — the precedent
  D-05 extends (Phase 10's shared `detect_stacks()`, Phase 11's converged
  per-language tool catalog)

### Existing parsing precedent
- `skills/ai-kit-agents-md-rules-checker/ai_kit_agents_md_rules_checker/
  makefile_checker.py` — `_iter_precommit_hook_blocks`/`_ID_LINE_RE`/
  `_ENTRY_LINE_RE`/`_strip_yaml_quotes` — the exact regex/text-based YAML-
  parsing-without-a-library pattern D-01 follows, applied to a flatter
  structure; this phase's parser generalizes it to handle nesting

  > **Corrected 2026-09-14 (Phase 13 plan 04):** That directory no longer exists (re-confirmed
  > live: `skills/ai-kit-agents-md-rules-checker` is absent from this worktree). The helpers
  > converged into `skills/_shared/ai_kit_rules_common/precommit_parse.py`, where the block reader
  > is now PUBLIC (`iter_precommit_hook_blocks`, no leading underscore) while `_ID_LINE_RE`,
  > `_ENTRY_LINE_RE`, and `_strip_yaml_quotes` stayed private. Cite the real module and the real
  > names — a reader who follows the old citation finds nothing and may otherwise conclude D-01's
  > rationale was invented; the precedent itself was real and was followed exactly as this section
  > describes, only its filesystem location moved.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None directly — ai-kit's own repo has no Docker setup to exercise this
  skill against (confirmed via scouting: no `docker-compose*.yml` or
  `Dockerfile*` found, no `docker-*` Makefile targets)

  > **Corrected 2026-09-14 (Phase 13 plan 04):** True at the repository ROOT and of the LOCAL-DEV
  > workflow (re-confirmed live), but the repo does carry a CI-only `tests/e2e/docker/Dockerfile`
  > behind its `e2e-docker` Makefile target. See the correction on the Phase Boundary paragraph
  > above for the full reasoning; the conclusion here ("None directly" reusable for exercising
  > THIS skill's local-dev checks) is unchanged and correct — the CI-only Dockerfile does not
  > satisfy this skill's LOCAL-DEV runbook/healthcheck/`depends_on`/hot-reload checks either way.
- `skills/_shared/ai_kit_rules_common/stack_cache.py`, once `detect_stacks`
  lands there per Phase 10's D-02 — this phase's D-05 consumes it directly

  > **Corrected 2026-09-14 (Phase 13 plan 04):** `detect_stacks` landed in
  > `skills/_shared/ai_kit_rules_common/stack_detect.py`, not `stack_cache.py`. `stack_cache.py`
  > is the generic per-skill on-disk tooling-cache helper module (used by the Phase 10/11
  > siblings' research-and-cache surface); this skill (D-D12) has no research step and no cache at
  > all, so it does not use `stack_cache.py` either. Plan 13-03 (D-D16) consumed `detect_stacks`
  > directly from the real path, `ai_kit_rules_common.stack_detect`.

### Established Patterns
- Regex/text-based YAML parsing without a library (`makefile_checker.py`'s
  `.pre-commit-config.yaml` handling) — D-01's direct precedent, though
  this phase's nested structure needs indentation tracking the existing
  pattern doesn't currently need

  > **Corrected 2026-09-14 (Phase 13 plan 04):** The `.pre-commit-config.yaml`-handling logic
  > this bullet points at converged into `skills/_shared/ai_kit_rules_common/precommit_parse.py`
  > (`iter_precommit_hook_blocks`, public). The `makefile_checker.py` that exists today
  > (`skills/ai-kit-project-rules-makefile/ai_kit_project_rules_makefile/makefile_checker.py`)
  > checks Makefile target SHAPE and does not handle `.pre-commit-config.yaml` at all — confirmed
  > live (no `pre-commit`/`precommit` string match in that file's own `.pre-commit-config.yaml`-
  > reading sense). The PATTERN this bullet names (regex/text-based YAML parsing without a
  > library) is still the real precedent D-01 followed; only the module housing it moved.

### Integration Points
- D-05 adds a new category to the shared per-language tool catalog Phase
  11's D-01 creates — this phase cannot be fully planned until that
  catalog's shape is known, reinforcing the Phase 9→10→11→12→13 dependency
  chain already in place for other reasons

  > **Corrected 2026-09-14 (Phase 13 plan 04):** Plan 13-03 deliberately did NOT do this (D-D16):
  > `HOT_RELOAD_TOOLS`/`HOT_RELOAD_BASELINE_GAPS`/`SCRIPT_INDIRECTION_PREFIXES` sit BESIDE the
  > six-category taxonomy in `skills/_shared/ai_kit_rules_common/tool_catalog.py` and never reach
  > `TOOL_CATEGORY_INDEX` or `resolve_tool_category` (re-confirmed live: `resolve_tool_category`
  > still answers `None` for every hot-reload marker) — because a dev server is not a static
  > analyzer, and feeding one into the shared classifier would misclassify a real hook in the
  > `ai-kit-project-rules-precommit` sibling this phase never opens. This section's own "Claude's
  > Discretion" bullet ("new top-level category vs. a dedicated dict keyed by stack") is what
  > actually offered the choice — the dict was chosen, so this Integration Points line and that
  > Decisions-section bullet were never in agreement. This is the most dangerous of this sweep's
  > corrections: a later reader following the stale prose instead of the decision text could
  > corrupt the pre-commit sibling's classifier. See `13-03-SUMMARY.md` and
  > `skills/_shared/ai_kit_rules_common/tool_catalog.py` for the real shape.

</code_context>

<specifics>
## Specific Ideas

- The user's own example for D-04: "lo importante del hotreload cuando son
  server es que se deben usar tecnologias dependiendo del stack, como por
  ejemplo node → vite, para python → flask" (hot-reload correctness
  depends on using the right stack-specific technology — Vite for Node,
  Flask's own dev/reload mode for Python) — this is the direct source of
  D-04/D-05's stack-aware expansion beyond the design spec's generic
  bind-mount wording.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 13's scope (D-04 expands a check's
rigor, not the phase's boundary).

### Reviewed Todos (not folded)
None — `cross_reference_todos` found the same 3 historical todos
(`resolves_phase: 6/7/8`) already confirmed not live candidates during
Phases 9-12's discussions.

</deferred>

---

*Phase: 13-Docker Rules Checker (ai-kit-project-rules-docker)*
*Context gathered: 2026-09-13*
