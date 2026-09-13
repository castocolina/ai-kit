# Context (from DOCs)

One DOC-type document in this ingest set:
`docs/superpowers/plans/2026-09-12-ai-kit-rules-shared-package.md` (manifest
precedence `1` — lower precedence than the sibling SPEC in this same batch,
`2026-09-12-ai-kit-rules-skill-family-design.md`, precedence `0`).

---

## Topic: ai-kit Rules Shared Package implementation plan
- source: docs/superpowers/plans/2026-09-12-ai-kit-rules-shared-package.md

Task-driven implementation plan (6 tasks) extracting the domain-agnostic rule-
classification engine, tool-presence detection, generic per-stack tooling
cache, and remediation-ordering helper out of `ai-kit-agents-md-rules-checker`
into `skills/_shared/ai_kit_rules_common/`, with a stated goal of zero
behavior change to the existing skill's public CLI/test surface. Reached via a
`sys.path` insert computed from `os.path.realpath(__file__)` — never a
hardcoded path. Python 3.12 stdlib only, `unittest`. Spec:
`docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`.

Confirmed portability gap: the `sys.path` bootstrap only resolves correctly
for 2 of `SKILL.md`'s 5 documented install candidates (the `~/.claude/skills`
symlink install via `tools/setup.py`'s `link_one`, and a direct git checkout).
For the other 3 (a Claude Code plugin root, an opencode install, an
`~/.agents` install), `skills/_shared/` is not guaranteed to exist beside the
installed skill — out of this plan's scope to fix. The plan makes the
bootstrap fail loudly (a named `ImportError`) instead of a bare
`ModuleNotFoundError` on those 3 hosts, rather than fixing them.

### Recorded deviations from the SPEC (per the plan's own Self-Review Notes)

The plan names 4 deliberate deviations from
`2026-09-12-ai-kit-rules-skill-family-design.md`. Per this ingest's precedence
(SPEC = 0, DOC = 1 — SPEC wins), the SPEC's version is what is recorded in
`constraints.md`; each deviation and its stated rationale is preserved here
for traceability (see `../INGEST-CONFLICTS.md` INFO section for the
auto-resolution record):

1. **Cache-payload validation contract location** — SPEC assigns
   `ALL_TOOLING_KEYS` membership / non-empty-string / `(source: ...)`-
   provenance validation to the shared module. Plan deliberately leaves
   `_validate_tooling_payload` in `ai-kit-agents-md-rules-checker`'s own
   `cli.py` (unmoved), since it validates against that skill's own
   Makefile-specific `ALL_TOOLING_KEYS` schema — moving the validator
   without moving its schema would split one concern across two packages
   for no behavior change. Deferred to a named follow-up plan.
2. **Cache staleness threshold** — SPEC says "older than 180 days"; the
   plan's `ai_kit_rules_common.stack_cache.STALE_AFTER_DAYS` is `30`,
   copied verbatim from the existing skill-local value, per the plan's own
   zero-behavior-change constraint. Reconciling the two values is
   explicitly out of scope for this plan.
3. **Cross-kind remediation merging ownership** — SPEC assigns cross-skill/
   cross-kind merging of remediation findings to the orchestrator, not the
   single-domain helper. The plan's `build_remediation` instead merges
   `"workflow"` and `"makefile"` findings into one ordered list within the
   helper itself — a deliberate carry-over of the existing skill's current
   single-skill report shape, since no orchestrator exists yet. Named
   removal point: the future orchestrator plan must take over this merging.
4. **`skills/_shared/` portability claim** — SPEC states every consuming
   skill is "independently copyable to a different host — only `_shared/`
   must travel with it." This does not hold for 3 of `SKILL.md`'s 5
   documented install candidates (see portability gap above). Fixing those
   installers is explicitly out of this plan's scope.

### Scope note

This plan implements only the shared-package migration half of the SPEC's
"ai-kit-agents-md-rules-agents (pruned)" component — NOT the "drops
`makefile_checker.py` entirely" half, deliberately deferred to a follow-up
`ai-kit-makefile-rules-checker` plan (pruning capability before its
replacement skill exists would leave a capability gap). Every other SPEC
component (makefile/precommit/arch/docker-compose/cicd checkers,
orchestrator) is out of scope for this plan by design.
