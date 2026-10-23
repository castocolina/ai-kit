DIGEST 072501208698e46f
TREE 08f340ecdf86e27bf7f2aeb2f05c56d99282de6e

# Skill evaluation: ai-kit-gsd-spec-discuss

Read-only review of `SKILL.md`, all four references, all three bundled scripts, and the shared client/backend contracts. Tests were inspected, not executed. The 500-word body cap was not applied.

Paths in dimension notes are relative to `skills/ai-kit-gsd-spec-discuss/`.

D1 19/20 — 95.0% — Strong knowledge delta: workflow-routing traps, evidence-based overrides, confidence instability, and cross-phase amendments (`SKILL.md:85–89`, `134–142`, `166–170`).
D2 14/15 — 93.3% — Transfers evidence-first thinking alongside specific spec/discuss procedures and a meaningful blocking-confidence matrix (`SKILL.md:12–16`; `references/decision-table.md:42–54`).
D3 15/15 — 100% — Concrete anti-patterns explain their consequences: lost CONTEXT decisions, context contamination, unintended planning, and sensitive-data exposure (`SKILL.md:178–195`).
D4 15/15 — 100% — Valid frontmatter; description supplies functionality, activation scenarios, searchable terms, and explicit exclusions (`SKILL.md:1–4`).
D5 15/15 — 100% — References have mandatory workflow triggers, conditional example loading, and explicit “Do NOT load” guidance (`SKILL.md:62`, `102–107`, `204–214`).
D6 12/15 — 80.0% — Consent, validation, advisory answers, and discretionary reasoning are appropriately constrained; the delegated workflow’s config-driven auto-advance needs an explicit exclusion (`SKILL.md:49–57`, `85–87`).
D7 10/10 — 100% — Clear Process pattern with a well-contained Tool-style decision ladder and appropriately separated reference material.
D8 12/15 — 80.0% — Actionable request shapes, per-item rejection, client compatibility handling, and fallback recipes; the auto-advance ambiguity and one inconsistent logging example reduce reliability.

## Changed-section checks

- **Setup steps 3 and 5:** Detection and consent instructions match the shared-client wrapper: per-backend status/key-source checks avoid depending solely on the aggregate probe status.
- **Section 3:** Correctly delegates backend ordering, thresholds, and rung execution to the client while retaining agent ownership of decisions.
- **Special `needs_fallback` check: present.** `SKILL.md:141–142` explicitly connects `fallback: true` to the client’s `needs_fallback` and directs the agent to use **own reasoning** against the SPEC, earlier CONTEXT, and live facts.

## Findings

### Important — Explicitly exclude config-driven planning

**File:** `skills/ai-kit-gsd-spec-discuss/SKILL.md:85–87`

Omitting `--auto` does not eliminate every planning transition in the delegated workflow. The installed `.claude/gsd-core/workflows/discuss-phase-assumptions/steps/auto-advance-dispatch.md:1–10` also launches plan-phase when `AUTO_MODE` is true.

Although the skill says it never plans, its instruction to execute that workflow leaves conflicting guidance under an enabled auto-mode preference. Explicitly skip the workflow’s `auto_advance` step regardless of configuration, without changing the user’s settings.

### Minor — Low-confidence second-opinion example omits required attribution

**File:** `skills/ai-kit-gsd-spec-discuss/references/log-formats.md:26`

The template labels a TypeSafe `0.74 (fb, second opinion)` override only as **Laya overridden**. However, `references/decision-table.md:26` requires **own reasoning, ledgered** when no remote answer is high.

Retain the override explanation, but explicitly mark it as an own-reasoning decision and include its ledger attribution.

CURRENT 112/120
CRITICAL 0
IMPORTANT 1
FLOORS ok
VERDICT pass


DIGEST 072501208698e46f
TREE 08f340ecdf86e27bf7f2aeb2f05c56d99282de6e

# Skill evaluation: ai-kit-gsd-spec-discuss

Read-only static review of `SKILL.md`, all four references, all three bundled scripts, the shared decision client, and relevant installed GSD workflow contracts. No files changed or tests executed. The 500-word body cap was not applied.

**Pattern:** Process/Tool hybrid. **Knowledge ratio:** approximately 80% Expert / 17% Activation / 3% Redundant.

## PART 1 — Dimensions

D1 18/20 — 90.0% — Strong repository-specific knowledge; trim repeated ladder explanations and historical narration.
D2 14/15 — 93.3% — Evidence-first judgment, locked decisions and blocking rules transfer expert thinking; clarify the shared client's remote stopping rule.
D3 15/15 — 100% — Specific, consequential anti-patterns explain why batching, workflow flags and wholesale regeneration fail.
D4 15/15 — 100% — Valid frontmatter; description clearly supplies capabilities, invocation scenarios, keywords and exclusions.
D5 15/15 — 100% — Mandatory loading triggers, conditional examples and explicit “Do NOT load” guidance provide excellent layering.
D6 13/15 — 86.7% — Appropriate discretion for decisions and tight operational recipes; input validation and commit-result handling need stronger guarantees.
D7 9/10 — 90.0% — Clear phased Process pattern with Tool-style decision tables; setup density slightly obscures the central execution path.
D8 12/15 — 80.0% — Common paths and recovery are actionable, but the edge-floor checker can pass without examining any requirements.

### Findings

**Important — Edge-floor validation can succeed vacuously.**  
`skills/ai-kit-gsd-spec-discuss/scripts/edge_floor.py:36–43,146–157,175–184`

If the Requirements section is missing, empty or contains no recognized numbered-bold entries, extraction returns `[]`. The installed engine accepts that array; with no parsed coverage rows, `compare()` returns `ok: true`, and `check` exits 0. Thus the prescribed gate can report success without checking a requirement. Reject zero extracted requirements before invoking the engine, validate required sections, and add malformed/empty-input regression tests.

**Minor — Remote ladder wording omits an important stopping condition.**  
`skills/ai-kit-gsd-spec-discuss/SKILL.md:138–139`; `skills/ai-kit-gsd-spec-discuss/references/log-formats.md:84–85`

“Remotes answer in table order” does not explain that the first valid remote answer ends escalation **even when low-confidence**. Only escalation-class errors continue to another remote. This behavior is explicit in `skills/jev-fast-decision/scripts/jev_review.py:1723–1735` and covered by `tests/test_jev_fast_decision.py:1342–1360`. State that rule in the recipe and audit-log template so agents do not imply that every consented remote was consulted.

**Minor — The log-format definition equates fallback with below-threshold probability.**  
`skills/ai-kit-gsd-spec-discuss/references/log-formats.md:8–10`

`needs_fallback` can also be forced by truncation or excessive state size, including for a high-probability answer. Define `(fb)` by the returned flag, not merely “below the threshold,” and include a high-probability forced-fallback example.

**Minor — The unconditional SPEC commit claim overlooks configuration.**  
`skills/ai-kit-gsd-spec-discuss/SKILL.md:81`

The installed workflow explicitly returns `skipped` when `commit_docs` is false (`.claude/gsd-core/workflows/spec-phase.md:520`). Require checking the commit result and reporting uncommitted artifacts rather than assuming the workflow committed them.

### Special check — `needs_fallback` recipe

**Present.** `skills/ai-kit-gsd-spec-discuss/SKILL.md:143–144` explicitly directs own reasoning against the SPEC, earlier CONTEXT files and live facts when all answering columns are fallback-marked or errored. The wrapper maps the client's `needs_fallback` to those `fallback` flags. No missing-recipe Critical finding.

## PART 2 — Verdict

**111/120 (92.5%, A).** The revised setup correctly uses per-backend consent status, separates configured keys from permission, and delegates backend policy to the shared client. Every dimension meets its floor.

CURRENT 111/120
CRITICAL 0
IMPORTANT 1
FLOORS ok
VERDICT pass


DIGEST 072501208698e46f
TREE 08f340ecdf86e27bf7f2aeb2f05c56d99282de6e

# Skill evaluation: ai-kit-gsd-spec-discuss

Read-only review of `SKILL.md`, all four references, all three bundled scripts, and the shared client/backend contracts. Tests were inspected, not executed. The 500-word body cap was not applied.

Paths in dimension notes are relative to `skills/ai-kit-gsd-spec-discuss/`.

D1 19/20 — 95.0% — Strong knowledge delta: workflow-routing traps, evidence-based overrides, confidence instability, and cross-phase amendments (`SKILL.md:85–89`, `134–142`, `166–170`).
D2 14/15 — 93.3% — Transfers evidence-first thinking alongside specific spec/discuss procedures and a meaningful blocking-confidence matrix (`SKILL.md:12–16`; `references/decision-table.md:42–54`).
D3 15/15 — 100% — Concrete anti-patterns explain their consequences: lost CONTEXT decisions, context contamination, unintended planning, and sensitive-data exposure (`SKILL.md:178–195`).
D4 15/15 — 100% — Valid frontmatter; description supplies functionality, activation scenarios, searchable terms, and explicit exclusions (`SKILL.md:1–4`).
D5 15/15 — 100% — References have mandatory workflow triggers, conditional example loading, and explicit “Do NOT load” guidance (`SKILL.md:62`, `102–107`, `204–214`).
D6 12/15 — 80.0% — Consent, validation, advisory answers, and discretionary reasoning are appropriately constrained; the delegated workflow’s config-driven auto-advance needs an explicit exclusion (`SKILL.md:49–57`, `85–87`).
D7 10/10 — 100% — Clear Process pattern with a well-contained Tool-style decision ladder and appropriately separated reference material.
D8 12/15 — 80.0% — Actionable request shapes, per-item rejection, client compatibility handling, and fallback recipes; the auto-advance ambiguity and one inconsistent logging example reduce reliability.

## Changed-section checks

- **Setup steps 3 and 5:** Detection and consent instructions match the shared-client wrapper: per-backend status/key-source checks avoid depending solely on the aggregate probe status.
- **Section 3:** Correctly delegates backend ordering, thresholds, and rung execution to the client while retaining agent ownership of decisions.
- **Special `needs_fallback` check: present.** `SKILL.md:141–142` explicitly connects `fallback: true` to the client’s `needs_fallback` and directs the agent to use **own reasoning** against the SPEC, earlier CONTEXT, and live facts.

## Findings

### Important — Explicitly exclude config-driven planning

**File:** `skills/ai-kit-gsd-spec-discuss/SKILL.md:85–87`

Omitting `--auto` does not eliminate every planning transition in the delegated workflow. The installed `.claude/gsd-core/workflows/discuss-phase-assumptions/steps/auto-advance-dispatch.md:1–10` also launches plan-phase when `AUTO_MODE` is true.

Although the skill says it never plans, its instruction to execute that workflow leaves conflicting guidance under an enabled auto-mode preference. Explicitly skip the workflow’s `auto_advance` step regardless of configuration, without changing the user’s settings.

### Minor — Low-confidence second-opinion example omits required attribution

**File:** `skills/ai-kit-gsd-spec-discuss/references/log-formats.md:26`

The template labels a TypeSafe `0.74 (fb, second opinion)` override only as **Laya overridden**. However, `references/decision-table.md:26` requires **own reasoning, ledgered** when no remote answer is high.

Retain the override explanation, but explicitly mark it as an own-reasoning decision and include its ledger attribution.

CURRENT 112/120
CRITICAL 0
IMPORTANT 1
FLOORS ok
VERDICT pass



DIGEST 072501208698e46f
TREE 08f340ecdf86e27bf7f2aeb2f05c56d99282de6e

# Skill evaluation: ai-kit-gsd-spec-discuss

Read-only static review of `SKILL.md`, all four references, all three bundled scripts, the shared decision client, and relevant installed GSD workflow contracts. No files changed or tests executed. The 500-word body cap was not applied.

**Pattern:** Process/Tool hybrid. **Knowledge ratio:** approximately 80% Expert / 17% Activation / 3% Redundant.

## PART 1 — Dimensions

D1 18/20 — 90.0% — Strong repository-specific knowledge; trim repeated ladder explanations and historical narration.
D2 14/15 — 93.3% — Evidence-first judgment, locked decisions and blocking rules transfer expert thinking; clarify the shared client's remote stopping rule.
D3 15/15 — 100% — Specific, consequential anti-patterns explain why batching, workflow flags and wholesale regeneration fail.
D4 15/15 — 100% — Valid frontmatter; description clearly supplies capabilities, invocation scenarios, keywords and exclusions.
D5 15/15 — 100% — Mandatory loading triggers, conditional examples and explicit “Do NOT load” guidance provide excellent layering.
D6 13/15 — 86.7% — Appropriate discretion for decisions and tight operational recipes; input validation and commit-result handling need stronger guarantees.
D7 9/10 — 90.0% — Clear phased Process pattern with Tool-style decision tables; setup density slightly obscures the central execution path.
D8 12/15 — 80.0% — Common paths and recovery are actionable, but the edge-floor checker can pass without examining any requirements.

### Findings

**Important — Edge-floor validation can succeed vacuously.**  
`skills/ai-kit-gsd-spec-discuss/scripts/edge_floor.py:36–43,146–157,175–184`

If the Requirements section is missing, empty or contains no recognized numbered-bold entries, extraction returns `[]`. The installed engine accepts that array; with no parsed coverage rows, `compare()` returns `ok: true`, and `check` exits 0. Thus the prescribed gate can report success without checking a requirement. Reject zero extracted requirements before invoking the engine, validate required sections, and add malformed/empty-input regression tests.

**Minor — Remote ladder wording omits an important stopping condition.**  
`skills/ai-kit-gsd-spec-discuss/SKILL.md:138–139`; `skills/ai-kit-gsd-spec-discuss/references/log-formats.md:84–85`

“Remotes answer in table order” does not explain that the first valid remote answer ends escalation **even when low-confidence**. Only escalation-class errors continue to another remote. This behavior is explicit in `skills/jev-fast-decision/scripts/jev_review.py:1723–1735` and covered by `tests/test_jev_fast_decision.py:1342–1360`. State that rule in the recipe and audit-log template so agents do not imply that every consented remote was consulted.

**Minor — The log-format definition equates fallback with below-threshold probability.**  
`skills/ai-kit-gsd-spec-discuss/references/log-formats.md:8–10`

`needs_fallback` can also be forced by truncation or excessive state size, including for a high-probability answer. Define `(fb)` by the returned flag, not merely “below the threshold,” and include a high-probability forced-fallback example.

**Minor — The unconditional SPEC commit claim overlooks configuration.**  
`skills/ai-kit-gsd-spec-discuss/SKILL.md:81`

The installed workflow explicitly returns `skipped` when `commit_docs` is false (`.claude/gsd-core/workflows/spec-phase.md:520`). Require checking the commit result and reporting uncommitted artifacts rather than assuming the workflow committed them.

### Special check — `needs_fallback` recipe

**Present.** `skills/ai-kit-gsd-spec-discuss/SKILL.md:143–144` explicitly directs own reasoning against the SPEC, earlier CONTEXT files and live facts when all answering columns are fallback-marked or errored. The wrapper maps the client's `needs_fallback` to those `fallback` flags. No missing-recipe Critical finding.

## PART 2 — Verdict

**111/120 (92.5%, A).** The revised setup correctly uses per-backend consent status, separates configured keys from permission, and delegates backend policy to the shared client. Every dimension meets its floor.

CURRENT 111/120
CRITICAL 0
IMPORTANT 1
FLOORS ok
VERDICT pass
