# Phase 40: Resilient review sized by jev — Specification

**Created:** 2026-11-23
**Ambiguity score:** 0.20 (gate: ≤ 0.20)
**Requirements:** 8 locked

## Goal

A review survives a failing lane without ever running on a lane nobody chose: a lane the owner flagged `usage_limited` switches at
once to its fallback, every chosen lane is pinged before a round and a blocked one is replaced from the owner's order, a review
in which a lane was replaced, failed or never resolved is reported partial, jev classifies reviewer-fixer disagreements before the
owner is asked and sizes the review (reviewer and one or two lanes) on top of deterministic signals, and a superpowers plan with
no fold step at its end gets a high finding.

## Background

Requirements REV-01, REV-02, REV-06, REV-07 and REV-08 (REQUIREMENTS.md) with the ROADMAP's Phase 40 criteria 1 to 8, including
the amendments of 2026-11-16 (free models, the lane-handling study, the free-lane pool study, PROVISIONAL) and 2026-11-03
(Phase 29 D-03). Phase 36 stored the `usage_limited` flag "for the lane-switching phase"; Phase 38.1 records a pool's
blocked-until time and keeps a direct lane's quota stop (D-12).

**The owner's decisions (highest priority):**

- 2026-11-02 and 2026-11-16: transient failures retry in the same session, then a new session; quota and auth stop and report;
  the runner never switches harness, provider or model on its own; a lane flagged `usage_limited` switches at once to the first
  unflagged lane of the same role; a lane without the flag never switches on its own; a direct lane stops at once on quota.
- 2026-11-23, answers to this phase's question batch: (1) a mid-round switch happens only for a flagged lane that hits quota;
  every other mid-round failure of an unflagged lane is reported partial and the owner decides; a failed pre-round ping replaces
  the lane before the round; (2) each lane is pinged before round 1, and later only a lane that failed or went stale; (3)
  deterministic signals force two lanes and jev picks the rest; without jev, or on a low answer, today's count stays; (4) the
  missing-fold-step finding is HIGH and the fixer adds the step.
- jev is advisory and never gates; every jev path has a tested no-jev behavior (2026-11-16).

**Decided by own reasoning on 2026-11-23, the owner may overrule:** the partial status wording ("Approved (partial)" and a header
line that names the lanes that judged). **Confirmed by the owner at the gate (2026-11-23):** the jev classes for a disagreement
(`owner_decision`, `mechanical`, `reviewer_wrong`) route as written in requirement 5, and jev never closes a CRITICAL or HIGH
finding (the fixer rule stays: address it anyway and note the disagreement).

**Live facts checked for this spec (2026-11-23, this machine):**

- `skills/ai-kit-spec-review/SKILL.md`: line 540 "Never re-dispatch a failed subprocess lane to another CLI, provider, model or the
  native session"; lines 398 and 419 "never switch lanes after a refusal" and "never switch harness, provider or model"; lines
  177-190 describe `probe-quota` as a walk of the review order before any dispatch, "pre-dispatch selection, not a recovery", run
  once per invocation (Step 0.7); the iteration cap is 3 (line 203); the fixer statuses `Escalation Required` and `No Edits` end
  the loop (488-497).
- `ai_kit_spec/quota.py`: `probe_reviewer_quota` (271) and `refresh_quota_cache` with a TTL (290) already probe a lane;
  `lane_settings.py`: `lane_usage_limit` (103) and `lane_fallback` (150, first different, unflagged, different-pool lane in
  order) exist with no caller in spec-review; `reviewer_dispatch.py:dispatch_reviewer` (85) and `routing.py:route_all` (353) are
  the dispatch and route entry points.
- No spec-review Python module reads a pool's blocked-until record (grep `blocked_until`, no hit); where the 38.1 record lives
  and its reader are plan-time checks.
- jev adapters exist in the skill (`jev_names.py` `ask_items`, `skill_classify.py`, `lane_order.py`); none sizes a review or
  classifies a disagreement.
- The fixer (`ai-kit-spec-review-fixer/SKILL.md`) addresses every CRITICAL and HIGH finding even when it disagrees (line 48) and
  may skip a MEDIUM or LOW one with a reason.
- `evals/evals.json` holds 14 evals (the last: `edge-refused-lane-exit-65`, `edge-edit-lens-pass-owner-started`); none covers a
  lane failing mid-review. The word "fold" does not appear in SKILL.md or `references/` of the skill. *(amended 2026-11-25,
  40 plan: the live count is 15 evals; `merge-reports` today fails the whole merge when any lane fails (`cli.py`
  `_cmd_merge_reports`), so R4 changes that behaviour and its tests; `RunnerSpec` has no `pool` field yet; a superpowers plan
  revises through Step 3b-skill (`skill:superpowers:writing-plans`), so "the fixer adds the step" means the revise route that
  receives the finding)*

## Requirements

1. **A flagged lane that hits quota switches at once; nothing else switches mid-round (REV-01)**: when a lane the owner flagged
   `usage_limited` fails after dispatch with a quota class, spec-review switches it at once to `lane_fallback` of its role (the
   first unflagged lane of a different pool in the role's order) and the round finishes with that lane; every other failure of a
   lane after dispatch leaves that lane `failed` with a reason, no other lane takes its place in that round, and the owner decides;
   lane selection skips a lane whose pool's blocked-until time (the 38.1 record) has not passed *(PROVISIONAL, needs owner
   confirmation)*, tries it once after that time, and a second failure renews the record under the 38.1 rule.
   - Current: SKILL.md forbids any switch after a dispatch; `lane_usage_limit` and `lane_fallback` have no caller in spec-review.
   - Target: the SKILL.md hard rule is narrowed to "an unflagged lane never switches" and names the flagged-lane exception; the
     flagged switch calls `lane_usage_limit` and `lane_fallback`.
   - Acceptance: fake-lane tests: a flagged lane failing with quota is replaced by the fallback and the review finishes; an
     unflagged lane failing with quota, a transient error or a crash is not replaced and is reported failed; a lane whose pool is
     still blocked is skipped at selection and a fixture lane after the blocked time is tried once; a doc-contract test pins the
     narrowed rule and fails when the old blanket wording returns.

2. **Each chosen lane is pinged before round 1, and later only a lane that failed or went stale (REV-07)**: before round 1 of a
   review, and before a judge round, every chosen lane is pinged at once with a short probe, each ping with its own timeout; a
   blocked lane is replaced from the owner's order by the same selection as requirement 1 (only the blocked ones are replaced);
   the round continues with at least one lane; before a later round a lane that returned a report in the previous round is not
   pinged again.
   - Current: `probe-quota` walks the order once per invocation before any dispatch; there is no ping per round and no parallel
     ping.
   - Target: a ping step beside `route_all` in `routing.py` and `dispatch_reviewer`, reusing `probe_reviewer_quota` and its cache
     TTL; with no lane left the review stops with the reason and never runs on zero lanes.
   - Acceptance: fake-lane tests: one blocked lane of two is replaced and the round runs with both slots filled; both blocked with
     no fallback stops with a reason and no dispatch; pings run concurrently (two lanes with a 2 s fake probe finish in under 3.5
     s); a lane that answered in round 1 triggers no probe in round 2 while a lane that failed does; a judge round pings too.

3. **Every ping or lane failure records a reason from one closed list (REV-07)**: one list of reasons, in one place, covers a ping
   or lane failure (the runner's closed class list of Phase 38.1 mapped in, plus ping-only reasons such as a ping timeout, a
   missing runtime and no lane left); a test fails when a key is added or removed without the list changing.
   - Current: `REASONS` in `ai_kit_spec/error_classifier.py` is a closed nine-member tuple the probe stores as the entry's reason
     and tests read; a replaced lane, a lane that never resolved and "no lane left" have no reason of their own. *(amended
     2026-11-23, 40 discuss: the first draft said no list existed; live read of `error_classifier.py:16`)*
   - Target: the existing list is extended with the review-level reasons and is the one list read by the ping, the switch and
     the report.
   - Acceptance: a lock test compares the keys with the documented list and fails on an added or removed key; a non-vacuity case
     adds a key and sees the test fail; every fake-lane failure in requirements 1, 2 and 4 records a key from the list.

4. **A review with a replaced, failed or unresolved lane is reported partial (REV-07)**: the final report names the lanes that
   judged and, for every other lane, its reason from requirement 3; a review in which a lane was replaced, failed or never
   resolved is never reported as a clean run and an approval in it reads "Approved (partial)"; one lane's failure never cancels
   another lane's result; the review log records which lanes judged each round; `loop-diagram.md` and `apply-findings.md` show the
   ping, the switch and the partial status.
   - Current: a pending lane surfaces as its own row and never as Approved (SKILL.md:524); there is no partial status.
   - Target: the Step 5 report gains the partial status and the judged-lanes line.
   - Acceptance: fake-lane tests: a replaced lane, a failed lane and a lane that never resolved (timeout) each yield a partial
     report with the judged lanes named; two lanes where one fails still merge the other's findings; an all-clean run is not
     marked partial; a doc-contract test pins the status wording and the two documents.

5. **jev classifies reviewer-fixer disagreements before the owner is asked (REV-02)**: when the fixer escalates a finding, skips
   a finding, or the loop reaches the cap with a finding still open, spec-review asks jev (when present) to classify each as
   `owner_decision`, `mechanical` or `reviewer_wrong`; only `owner_decision` items and items jev answers with low confidence reach
   the owner, with jev's class shown as advisory; a confident `mechanical` item gets one more fixer pass inside the iteration cap;
   a confident `reviewer_wrong` MEDIUM or LOW item is listed as skipped with jev's reason; a CRITICAL or HIGH finding is never
   closed on jev's word; without jev the owner is asked as before. *(amended 2026-11-25, 40 plan, orchestrator decision: a
   CRITICAL or HIGH finding never takes the `mechanical` route either; whatever class jev gives, it reaches the owner with the
   class shown as advisory (CONTEXT D-06); only MEDIUM and LOW items get the extra fixer pass)*
   - Current: every escalation, skip and cap stop goes to the owner as one message; jev is not consulted.
   - Target: a classification step before the Step 5 surface, through the existing jev client, one item per finding.
   - Acceptance: fake-jev tests: each class routes as written; a low answer goes to the owner; a CRITICAL finding classed
     `reviewer_wrong` still reaches the owner; no jev installed gives today's message; a doc-contract test pins that no code, diff
     or file content is sent to jev (summaries only).

6. **jev sizes the review on top of deterministic signals (REV-06)**: deterministic signals (security, data, irreversible
   operations, computed from the plan) force two lanes; otherwise jev picks the reviewer from the owner's order and one or two
   lanes from files touched, complexity, task count and category, and the review log shows why; without jev, or on a low answer,
   the lane count and order stay as configured today; jev never picks a lane outside the roster.
   - Current: the roster and order come from the config; nothing sizes a review.
   - Target: a sizing step in the reviewer resolution (Step 0.7 to 1) that takes the signals and the jev answer and writes the
     reason into the log.
   - Acceptance: fake-jev tests: a plan with a security signal gets two lanes whatever jev says; a plain plan with a jev answer of
     one gets one lane and a logged reason; no jev or a low answer keeps today's count and order; a jev pick outside the roster is
     discarded.

7. **A superpowers plan with no fold step at its end gets a HIGH finding (REV-08)**: spec-review reports a superpowers plan
   fixture that has no explicit fold step at its end as a HIGH finding, and the fixer adds the step (the wording
   `ai-kit-spec-execute-superpowers` documents); the same plan with the step gets no such finding.
   - Current: no check; the word "fold" is absent from the skill and its references.
   - Target: a deterministic check for the superpowers plan archetype that names the missing step as a HIGH finding with a
     `Required:` outcome.
   - Acceptance: a fixture pair: the plan without the step yields the finding with severity HIGH and a `Required:` line; the same
     plan with the step yields none; a non-superpowers plan is never flagged.

8. **Every changed SKILL.md meets the judge bar (JDG-04)**: `ai-kit-spec-review`, `ai-kit-spec-review-fixer` and
   `ai-kit-spec-review-checklist` (and any other SKILL.md this phase changes) carry new-shape evals and tests and pass the
   skill-judge loop.
   - Current: `ai-kit-spec-review` carries 14 evals, none for a failing lane. *(amended 2026-11-25, 40 plan: 15 evals live)*
   - Target: each judged result has no critical or high finding, or grade B or better, and no regression beyond the judge's
     run-to-run variation (Phase 36 and 39 brought the first skill to the bar; this phase keeps it).
   - Acceptance: the judge record of each changed skill meets the bar of AGENTS.md and `make check-dogfood` validates the records;
     `evals.json` gains one eval for each of a flagged-lane switch, a blocked lane replaced by a ping, a partial report and a
     jev-classified disagreement.

## Boundaries

**In scope:**
- The flagged-lane switch, the per-round ping, the closed reason list and the partial report of `ai-kit-spec-review`.
- jev classification of disagreements and jev sizing of a review, with their no-jev behavior.
- The superpowers fold-step finding in the review.
- Docs: `SKILL.md`, `references/apply-findings.md`, `references/loop-diagram.md`; evals and tests; the judge loop.

**Out of scope:**
- Switching an unflagged lane on any failure class (owner decision 2026-11-23).
- The runner's own retry and error classification (Phases 38 and 38.1) and the blocked-until record's writer.
- Execute-side lane switching and the superpowers adapter's quota logic (Phase 41, 42).
- Code review after execution and jev-picked executors (Phase 42).
- A new jev backend or any change to the shared jev client.

## Constraints

- Runtime code stays stdlib-only; jev is reached only through the existing client and never gates (no jev means today's behavior).
- Only summaries go to jev, never code, diffs, file contents or config values.
- A lane switch or replacement stays inside the owner's roster; the runner and spec-review never pick a runtime or model outside it.
- Pings run concurrently under one per-ping timeout; a test seam replaces the clock and the probe (no real model call in tests).
- No machine-specific absolute path in skill text, tests or fixtures; model names in fixtures are placeholders.
- The free-lane pool decisions are PROVISIONAL and flagged as such in every artifact until the owner confirms them.

## Acceptance Criteria

- [ ] A flagged lane failing with quota is replaced by `lane_fallback` and the review finishes; an unflagged lane failing is
  reported failed and not replaced
- [ ] A lane whose pool is still blocked is skipped at selection; after the blocked time it is tried once
- [ ] The SKILL.md hard rule is narrowed and pinned; the old blanket wording fails a doc-contract test
- [ ] Each chosen lane is pinged concurrently before round 1; only a blocked lane is replaced; no lane left stops with a reason
- [ ] A lane that answered last round is not pinged again; a failed lane is
- [ ] A lock test fails when a reason key is added or removed without the list changing; every recorded failure uses a listed key
- [ ] A review with a replaced, failed or unresolved lane is reported partial with the judged lanes named; an approval reads
  "Approved (partial)"; one lane's failure keeps the other's result
- [ ] jev classifies escalated, skipped and cap-open findings; each class routes as written; a CRITICAL or HIGH finding is never
  closed on jev's word; no jev gives today's message
- [ ] A security, data or irreversible plan gets two lanes; otherwise jev sizes within the roster and logs why; no jev keeps
  today's count
- [ ] A superpowers plan without a fold step gets a HIGH finding with a `Required:` line; with the step none; other archetypes
  never
- [ ] Every changed SKILL.md meets the judge bar of AGENTS.md

## Edge Coverage

**Coverage:** 37/37 applicable edges resolved (26 covered or backstop, 11 dismissed with the owner's approval of 2026-11-23) · 0 unresolved *(amended 2026-11-23, 40 discuss: the R3 amendment removed the R3 encoding row, which had been dismissed)*

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| boundary | R1 | 🧪 backstop | Held-out fixture: a pool blocked-until time equal to now counts as passed (a lane is skipped only while now is before the time). |
| adjacency | R1 | 🧪 backstop | Held-out fixture: when the next lane shares the failed lane's pool, `lane_fallback` skips it and takes the next different-pool lane. |
| empty | R1 | 🧪 backstop | Held-out fixture: a flagged lane failing with quota and no eligible fallback is reported failed and not replaced. |
| encoding | R1 | ⛔ dismissed | Lane keys are opaque strings compared for equality (`_keyed`); no length or normalization semantics. |
| ordering | R1 | 🧪 backstop | Held-out fixture: with two eligible fallbacks the earlier one in the role's order is taken. |
| precision | R1 | 🧪 backstop | Held-out fixture: only the quota class triggers the flagged switch; billing, auth, permission and transient classes do not. |
| boundary | R2 | 🧪 backstop | Held-out fixture: a ping that returns at its timeout is recorded with the ping-timeout reason and the lane is treated as blocked. |
| adjacency | R2 | 🧪 backstop | Held-out fixture: two chosen lanes with the same key are pinged once. |
| empty | R2 | ✅ covered | R2 acceptance: no lane left stops with a reason and no dispatch. |
| ordering | R2 | 🧪 backstop | Held-out fixture: pings finishing out of order are matched to lanes by key, and replacements keep the owner's order. |
| precision | R2 | 🧪 backstop | Held-out fixture: a lane that answered at the TTL minus one second is not pinged again and one at the TTL plus one second is. |
| adjacency | R3 | ✅ covered | R3 acceptance: the lock test compares the full key set, so a near-duplicate key changes the list. |
| empty | R3 | 🧪 backstop | Held-out fixture: a failure the list cannot classify records the list's default reason, never an empty one. |
| ordering | R3 | ⛔ dismissed | The lock test compares a set of keys; order carries no meaning. |
| boundary | R4 | ✅ covered | R4 acceptance: two lanes where one fails still merge the other's findings and the report is partial. |
| adjacency | R4 | 🧪 backstop | Held-out fixture: a replaced lane and its replacement both appear in the report, the first with its reason, the second as judging. |
| empty | R4 | 🧪 backstop | Held-out fixture: no lane judged yields "not reviewed" with the reasons, never an approval. |
| encoding | R4 | ⛔ dismissed | Report text; lane keys print verbatim. |
| ordering | R4 | 🧪 backstop | Held-out fixture: the judged-lanes line follows the owner's roster order. |
| precision | R4 | ✅ covered | R4 acceptance: an all-clean run is not marked partial. |
| idempotency | R4 | ⛔ dismissed | The report is built once per invocation from the round log. |
| concurrency | R4 | ✅ covered | R4 acceptance: one lane's failure never cancels another lane's result. |
| boundary | R5 | 🧪 backstop | Held-out fixture: a jev answer with `needs_fallback` true counts as low and goes to the owner. |
| adjacency | R5 | ⛔ dismissed | One jev item per finding (the jev skill's own rule); items never merge. |
| empty | R5 | 🧪 backstop | Held-out fixture: no escalated, skipped or open finding means no jev call. |
| encoding | R5 | ✅ covered | R5 acceptance: a doc-contract test pins that only summaries go to jev. |
| ordering | R5 | ⛔ dismissed | Each answer is independent; the order of items does not change any class. |
| precision | R5 | ✅ covered | R5 acceptance: a low answer goes to the owner and a CRITICAL `reviewer_wrong` finding still reaches the owner. |
| concurrency | R5 | ⛔ dismissed | One orchestrator classifies sequentially before the surface step. |
| boundary | R6 | 🧪 backstop | Held-out fixture: the deterministic-signal function is tested at each trigger and with none (two lanes versus the jev or default count). |
| precision | R6 | ✅ covered | R6 acceptance: a jev pick outside the roster is discarded and a low answer keeps today's count. |
| concurrency | R6 | ⛔ dismissed | Sizing runs once before dispatch. |
| empty | R7 | 🧪 backstop | Held-out fixture: an empty superpowers plan gets no fold finding (its other findings apply). |
| encoding | R7 | 🧪 backstop | Held-out fixture: the fold step is recognized by its documented wording in a heading or a checkbox, case-insensitively. |
| adjacency | R8 | ⛔ dismissed | The judge loop is a process over files; no values touch. |
| empty | R8 | ⛔ dismissed | A skill with no change is not judged; the requirement names the changed ones. |
| ordering | R8 | ⛔ dismissed | Judge rounds have no order semantics beyond the three-round cap of AGENTS.md. |

## Prohibitions (must-NOT)

**Coverage:** 5/5 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT switch an unflagged lane, or switch any lane to one outside the owner's roster, on any failure class | R1, R2 | resolved | test (R1 acceptance and the held-out precision fixture); wired-check descriptor left empty until plan time |
| MUST NOT run a round with zero lanes, and MUST NOT report a review with a replaced, failed or unresolved lane as a clean run | R2, R4 | resolved | test (R2 and R4 acceptance); wired-check descriptor left empty until plan time |
| MUST NOT send code, diffs, file contents, config values or secrets to jev | R5, R6 | resolved | test (doc-contract plus a seam that records the payload) and judgment review; wired-check descriptor left empty until plan time |
| MUST NOT let jev close or downgrade a CRITICAL or HIGH finding, or lower the lane count below the deterministic floor of two | R5, R6 | resolved | test (R5 and R6 acceptance); wired-check descriptor left empty until plan time |
| MUST NOT change today's behavior when jev is absent, errors or answers with low confidence | R5, R6 | resolved | test (no-jev fixtures for each jev path); wired-check descriptor left empty until plan time |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                                       |
|--------------------|-------|------|--------|-----------------------------------------------------------------------------|
| Goal Clarity       | 0.85  | 0.75 | ✓      | switch, ping, partial, jev sizing, fold finding                              |
| Boundary Clarity   | 0.80  | 0.70 | ✓      | explicit out-of-scope list; unflagged-lane switching excluded by the owner   |
| Constraint Clarity | 0.72  | 0.65 | ✓      | blocked-until reader and reason list contents left to plan time             |
| Acceptance Criteria| 0.78  | 0.70 | ✓      | 11 pass/fail criteria                                                       |
| **Ambiguity**      | 0.20  | ≤0.20| ✓      |                                                                             |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

Run mode `interactive`, 1 question round plus the gate question. jev was not asked: in the interactive path it screens only
items the owner asks it to screen. Rule: mvp-mode inactive, the best design wins over the smallest diff.

| Round | Perspective     | Question summary                                                   | jev (advisory) | Decision locked |
|-------|-----------------|--------------------------------------------------------------------|----------------|-----------------|
| 1     | Researcher      | What exists today for lane failure, ping and jev in spec-review?   | none           | Hard rule at SKILL.md:540; probe walk once per invocation; `lane_fallback` unused; jev adapters exist (Background) |
| 1     | Boundary Keeper | When does a lane switch to the next lane of the order?             | none           | Only a flagged lane on quota, plus the pre-round ping; everything else partial (R1) |
| 1     | Simplifier      | How often is each lane pinged?                                     | none           | Before round 1, then only failed or stale lanes (R2) |
| 1     | Boundary Keeper | How far does jev go in sizing a review?                            | none           | Signals force two lanes, jev picks the rest, no jev keeps today's count (R6) |
| 1     | Failure Analyst | How severe is the missing-fold-step finding?                       | none           | HIGH, the fixer adds the step (R7) |
| —     | Own reasoning   | Partial status wording                                             | none           | "Approved (partial)" with a judged-lanes line (R4). Ledger. |
| gate  | Seed Closer     | How much does jev's class change routing? Edges and prohibitions? | none           | Route by class, never CRITICAL or HIGH (owner, 2026-11-23); 12 dismissals, 26 covered or backstop rows and five prohibitions approved |

---

*Phase: 40-resilient-review-sized-by-jev*
*Spec created: 2026-11-23*
*Next step: /gsd-discuss-phase 40 — implementation decisions (ping seam, reason list home, sizing step placement, fold-step check home)*
