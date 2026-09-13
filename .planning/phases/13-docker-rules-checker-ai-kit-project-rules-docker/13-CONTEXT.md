# Phase 13: Docker Rules Checker (ai-kit-project-rules-docker) - Context

**Gathered:** 2026-09-13
**Status:** Ready for planning — BLOCKED on Phases 9-12 landing first (see Phase Boundary)

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

**Hard prerequisite — this phase cannot be planned or executed before
Phases 9-12 actually land.** `.planning/ROADMAP.md`'s "Depends on" line
for Phase 13 names Phase 12 directly; the full chain back to Phase 9 is
unbroken. As of this discussion, NONE of Phases 9-12 have a plan or
execution yet (each has only a CONTEXT.md).

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

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None directly — ai-kit's own repo has no Docker setup to exercise this
  skill against (confirmed via scouting: no `docker-compose*.yml` or
  `Dockerfile*` found, no `docker-*` Makefile targets)
- `skills/_shared/ai_kit_rules_common/stack_cache.py`, once `detect_stacks`
  lands there per Phase 10's D-02 — this phase's D-05 consumes it directly

### Established Patterns
- Regex/text-based YAML parsing without a library (`makefile_checker.py`'s
  `.pre-commit-config.yaml` handling) — D-01's direct precedent, though
  this phase's nested structure needs indentation tracking the existing
  pattern doesn't currently need

### Integration Points
- D-05 adds a new category to the shared per-language tool catalog Phase
  11's D-01 creates — this phase cannot be fully planned until that
  catalog's shape is known, reinforcing the Phase 9→10→11→12→13 dependency
  chain already in place for other reasons

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
