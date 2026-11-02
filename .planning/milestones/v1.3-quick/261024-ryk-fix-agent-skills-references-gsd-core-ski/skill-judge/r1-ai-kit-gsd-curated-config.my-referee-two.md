# Skill Evaluation Report: ai-kit-gsd-curated-config (round 2, post-5b4ec21)

**Verdict:** A dense, expert-grade Tool-pattern skill. The diff's core claim — "wire only what gsd-core resolves" — is fully implemented, documented, and pinned by tests. Doc-code consistency verified claim by claim; no Critical or Important findings.

## Dimension table

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 19 | 20 | ~95% expert: gsd-core skip semantics, per-flow permission matrix, marker recovery, trust model. Near-zero redundancy. |
| D2 Mindset + Procedures | 13 | 15 | Thinking frame in the preamble ("ask yourself: trusted checkout? where do files live?") + exact domain pipeline. Body is (appropriately) procedural. |
| D3 Anti-Pattern Quality | 13 | 15 | NEVER list with non-obvious WHYs (SKILL.md:299-317) + mistake→fix table (321-331). A few entries restate procedure rather than independent landmines. |
| D4 Specification Compliance | 13 | 15 | Valid name (25 chars); 669-char description with WHAT, WHEN (4 quoted triggers), keywords. Deducted for run-on structure (Minor 3). |
| D5 Progressive Disclosure | 13 | 15 | 342-line SKILL.md; both references gated ("Read only when…", "Read when … comes up"). No orphan refs. Missing explicit "Do NOT load" on runner.md (Minor 4). |
| D6 Freedom Calibration | 13 | 15 | Fragile config mutation → exact commands, fingerprint-bound approvals, dry-run gate, never-hand-write rules. Correctly low-freedom. |
| D7 Pattern Recognition | 9 | 10 | Textbook Tool pattern (decision tables, exact scripts, ~340 lines vs ~300 archetype). |
| D8 Practical Usability | 12 | 15 | Exit-code tables, failure states, refusals print their own recovery commands, eval scenarios with gating criteria. Deducted for Minor 1. |

**Total: 105/120 (87.5%) — Grade B**

## Verified diff claims (the focus area) — all hold

- Exit-2 table lists the skipped-`agent_skills` refusal (SKILL.md:35 ↔ `apply.py:907`, `plan_edit.py:182-192`).
- Refusal is force-immune in code and docs (SKILL.md:262 ↔ `plan_edit.py:178` raising after force handling; `_check_agent_skills` returns `forced=False`, plan_edit.py:522-523).
- Dry-run refuses before any write (SKILL.md:262 ↔ `cli.py:669` → `apply_mod.prepare` → skip check before `resolve_target`).
- Declined-root refusal while agents hold covered skills (SKILL.md:124, 256 ↔ `plan_unset` at plan_edit.py:137 + `effective_trusted_roots`).
- "Two marker skills" ↔ `skill_scan.py:38`; "install outside $HOME gets no candidate" ↔ `_ai_kit_skills_dir`/`_home_rel`; one merged candidate ↔ `recommend.py:1134`.
- Pinned by tests: `test_curated_config_apply.py:717`, `test_curated_config_plan_edit.py:1103/1131/1149`.

## Findings

1. **Minor** — `_kept_names` (`plan_io.py:626-641`): the printed drop-fix excludes *healthy* kept refs (`global:<name>`, plugin refs) from the keep list, so running it verbatim silently unwires them (e.g. v1-written `["global:healthy","global:escaping"]` → printed fix is `plan-set agent_skills.x []`). Deliberate and test-pinned (`test_…:1149-1169`), and the roots-fix alternative is printed first, but the only disclosure is the cryptic "re-resolves by name" note. **Fix:** reduce single-colon `global:<name>` kept refs to their bare name in the keep list (project-copy precedence already disclosed in the note), exclude only namespaced plugin refs, or name the dropped refs explicitly.
2. **Minor** — Trusted-root decline-refusal stated twice verbatim (SKILL.md:124-128 and 253-258); drift risk on the next behavioral change. **Fix:** keep full text in §Skills, shrink the step-3 bullet to the rule + pointer.
3. **Minor** — Description (SKILL.md:3) is one 669-char run-on embedding body-level mechanism ("Config keys are written only through gsd-tools…", the v1 aside). **Fix:** split into 2-3 sentences; move mechanism detail to §Scope.
4. **Minor** — `references/runner.md:3` says "Read when … comes up" but lacks the explicit do-not-load gate `v1-path.md:3` has. **Fix:** add "Do NOT load for the stock v2 flow."

Skipped: did not execute the test suite (read-only mandate — a run writes `__pycache__`); doc-code claims were verified by reading source and existing tests instead. Risk: none beyond that.

DIGEST a7baccdc7bd3a6f1
CURRENT 105/120
CRITICAL 0 IMPORTANT 0
