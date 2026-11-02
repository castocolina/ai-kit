# Phase 25: Quota-aware cross-AI subprocess supervision — Specification

**Created:** 2026-10-14
**Ambiguity score:** 0.14 (gate: ≤ 0.20)
**Requirements:** 8 locked

## Goal

When a cross-AI child (pi, opencode, cursor, codex) stops on a usage limit, ai-kit tells a limit
that recovers by waiting from one that will not. For the first it waits (a re-check every 10
minutes, at most 4 hours) and resumes only the unfinished work; for the second it reports and
moves on. It never fails blindly and never loops forever.

## Background

- **Source:** todo `2026-10-14-agents-md-quota-schedule-rules-and-goal-prompt-skill.md`, part 1,
  mechanism B (subprocess quota), and uz's 2026-10-14 clarification on routes:
  - router-backed models (`router-env/*`) are fallback combos. The first models sit behind
    subscriptions that hit their limit; the chain then reaches a paid/API model that reports
    billing exhausted. Within minutes to a couple of hours the subscriptions recover, so the
    error is wait-recoverable;
  - direct third-party provider models (OpenCode Zen, Cursor API models) that fail on billing
    or access usually cannot be fixed by waiting.
- **The designed contract this phase extends** (research 18 §4.3–4.6; 18 D-27; 18.1 D-12;
  16.1 D-13):
  - closed classes `auth`, `billing` (never wait), `quota` (fall back now, hourly `CronCreate`
    wake), `capacity` (≤ 2 resume-retries in the deadline);
  - exit 69 (fatal for this CLI: auth, billing, …) and 75 (quota, capacity after retries);
  - one last-line `AIKIT-XAI status=… tree=clean|dirty action=fallback|retry-later|stop`;
  - classification on stderr and structured fields only, never the model's answer text.
- **Current code:**
  - the prototype runner `cross-ai.mjs` has only `TRANSIENT` and `FATAL`; `FATAL` includes
    `quota exceeded`, `spending limit`, `billing` and `40[123]`;
  - `ai-kit-spec-execute-gsd` and `-superpowers` schedule an hourly `CronCreate` wake on quota
    exhaustion, with resumable state (`dispatch.write_resumable_state`), gated by
    `any_quota_recoverable`;
  - `model_heuristics.infer_fallback_quota()` already marks router entries as having internal
    multi-backend fallback.
- **GSD's own cross-AI step** runs the command under `gsd_run run-with-timeout
  "${CROSS_AI_TIMEOUT}"` (default 300 s) and offers retry / skip / abort on a non-zero exit
  (`execute-phase.md` step 2.5). So a multi-hour wait cannot live inside one command call.
- **Observed limit messages** (local session logs, 2026-08..10):
  - codex: `ERROR: You've hit your usage limit... try again at 6:30 PM`; a structured
    `"codex_error_info":"usage_limit_exceeded"` with `purchase more credits or try again at Aug
    1st, 2026 3:36 PM`;
  - cursor: `ActionRequiredError: You've hit your usage limit` (monthly Agent usage limit);
  - opencode on `openai/gpt-5.6-sol`: `usage limit reached`; *(amended 2026-10-14, 25 D-04: the live stdout event is `{"type":"error",…"name":"APIError","data":{"message":"The usage limit has been reached","statusCode":429}}`; codex's `codex_error_info` was seen only in its private rollout files, never on `exec --json` stdout)*
  - xai via opencode: 403 spending limit (memory, 2026-09-14); OpenCode Zen: 403 `Model access
    is disabled` (2026-10-14);
  - claude: `Overloaded ... try again in a moment` (capacity, not quota);
  - router-env (Phase 16): capacity, 402 billing, credential gate.

## Requirements

1. **Pattern table** (QTA-01).
   - Current: phrase sets live in the runner's two regexes and in the Python classifier.
   - Target: one per-CLI table of limit, billing and access patterns (pi, opencode, cursor, codex, claude). Structured fields win over text (codex `codex_error_info`). Every pattern carries its evidence and a `verified` or `unverified` label. The runner and the Python classifier read the same table.
   - Acceptance: every observed message in Background is a fixture with its expected class; an unverified pattern is reported as unverified in the status detail.
   - *Amended 2026-10-14 (25 D-01..D-04):* the table and matcher live only in the runner (Python reads the status line); structured fields mean stdout error events where the CLI emits them (opencode, codex JSONL, cursor result); codex matches on text until its field is seen on stdout; bare status codes match last.

2. **Route-aware classes** (QTA-01).
   - Current: billing is always fatal and quota always means "fall back now".
   - Target: a stop becomes `quota_wait` (recovers by waiting) or `billing_or_access` (does not), by message and route:
     - on a router-backed route (`infer_fallback_quota`), billing and limit messages are `quota_wait`;
     - on a direct third-party provider route, billing and access messages are `billing_or_access`;
     - on an unknown route, quota and rate-limit messages are `quota_wait` and billing or access messages are `billing_or_access`.

     `quota_wait` exits 75 with `action=retry-later`; `billing_or_access` exits 69. 18 D-27 is amended to match.
   - *Amended 2026-10-14 (25 D-05..D-08):* route kind comes from the catalog's user-confirmable `fallback_quota` (`infer_fallback_quota` is only the default); "direct" is a closed evidence-labelled prefix list; on a direct route known monthly/account-cap wordings are `billing_or_access` and other quota text follows the unknown-route rule; on a router route, fallback-tail access and credential errors are `quota_wait` and only the router's own entry-point auth is `auth`.
   - Acceptance: fixtures cover each class on each route kind, including a billing message on a router route and on a direct route.

3. **Reset time** (QTA-03).
   - Current: ignored.
   - Target: a reset time in the message (`try again at <time>`, `resets <time>`) is parsed into an absolute local time. A reset beyond the 4-hour window means stop and report now, with the reset time. A reset inside the window sets the first re-check at the reset time, then every 10 minutes.
   - Acceptance: fixtures with a same-day time, a dated time days ahead, and no time.

4. **Live and post-hoc detection** (QTA-02).
   - Current: classification only after exit, over text that includes the model's answer.
   - Target: the runner watches the child's stderr and structured events while it runs and stops the child on a limit signal. After a timeout or an exit with partial work it classifies the captured stderr and structured fields. The model's answer text is never matched.
   - Acceptance: a fake child that prints a limit line mid-run is stopped early with `status=quota_wait`; a fake child that times out after printing one is classified the same; a limit phrase inside the answer text alone is not.

5. **Where the wait lives** (QTA-03).
   - Current: an hourly `CronCreate` wake in two skills.
   - Target: the runner exits at once with `action=retry-later`, the reset time if known, and a resume-state file (runtime, model, session id, plan or task reference, attempt count, first-seen time). The orchestrating agent schedules the re-checks with the host's in-session scheduler (Claude Code `ScheduleWakeup` or `CronCreate`; other hosts flagged). Under GSD's cross-AI step it answers the retry prompt only after the wait. The runner never sleeps for hours inside one call.
   - Acceptance: a test drives exit 75 → state file → a re-check that sees the limit still active → a re-check that succeeds; the attempt cap is enforced from the state file, not from memory.

6. **Fallback or wait** (QTA-03).
   - Current: always fall back on quota; hourly wake when every candidate is exhausted.
   - Target: with `tree=clean` and another usable candidate, fall back now and mark the limited CLI for re-check. With `tree=dirty`, wait and resume the same CLI's session (its `resume` argv), so the partial edits stay with the agent that made them. After 4 hours from first-seen, stop and report what is done and what is not.
   - Acceptance: tests for clean+candidate (fallback), dirty (wait then resume), and the 4-hour cap (stop with a report).

7. **Resume only unfinished work** (QTA-03).
   - Current: a retry re-runs the whole prompt.
   - Target: before resuming, the orchestrator compares the working tree with the pre-dispatch snapshot. A resume continues the captured session when the CLI supports it; otherwise the re-dispatch prompt names what is already done (from the tree diff) and asks only for the rest.
   - Acceptance: a fixture with partial edits produces a resume prompt that lists them; a clean tree produces the original prompt.

8. **Skills follow the policy** (QTA-03).
   - Current: `ai-kit-spec-execute-gsd` and `-superpowers` describe an hourly wake. *(amended 2026-10-14, 25 D-22: `ai-kit-spec-review` has none; it gains the policy, with a waiting lane marked pending)*
   - Target: their SKILL.md files and code follow R2–R7 and drop the hourly wake for subprocess limits (the session's own resume is Phase 26). Each touched SKILL.md passes `/skill-judge`.
   - Acceptance: no hourly-wake instruction remains for subprocess limits; skill-judge evidence is committed.

## Boundaries

**In scope:**
- The pattern table, route-aware classes, reset parsing, live and post-hoc detection, the resume-state file and wait policy, and the three skills

**Out of scope:**
- The orchestrating session's own quota and self-wake (Phase 26)
- The AGENTS.md rule (Phase 26)
- Changing GSD's retry prompt or `run-with-timeout` (upstream)
- Buying credits or switching accounts

## Constraints

- Runtime code stays stdlib-only; the runner stays a single Node file from the 18 template.
- Patterns come from observed output; anything else is labelled unverified.
- Never classify on the model's answer text.
- No key or token in any status line, state file or log.

## Acceptance Criteria

- [ ] Every observed limit message is a classified fixture, labelled verified or unverified
- [ ] Route kind changes the class of a billing message as specified
- [ ] A reset beyond 4 hours stops at once; a reset inside sets the first re-check
- [ ] Live detection stops a child early; post-hoc detection classifies a timed-out child
- [ ] The runner exits at once with `retry-later` and a resume-state file; the cap comes from the file
- [ ] Clean + candidate falls back; dirty waits and resumes; 4 hours stops with a report
- [ ] A resume names the already-done work
- [ ] The three skills follow the policy and pass `/skill-judge`
- [ ] `make test` and `make validate` are green
- [ ] MUST NOT: a wait never exceeds 4 hours from first-seen
- [ ] MUST NOT: a billing or access error on a direct third-party route is never waited on

## Edge Coverage

**Coverage:** 41/41 applicable edges resolved · 0 unresolved

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | A message matching both a limit and a billing pattern takes the first match in table order (billing/access before quota), recorded in the fixture |
| boundary | R1 | ✅ covered | A structured field (codex `codex_error_info`) wins over any text pattern |
| empty | R1 | ✅ covered | Empty stderr and no structured error classify as `crash`, never as a limit |
| encoding | R1 | ✅ covered | Patterns match case-insensitively on decoded UTF-8 with replacement; ANSI codes are stripped first |
| ordering | R1 | 🧪 backstop | Table order is fixed and pinned by a test |
| precision | R1 | ✅ covered | Status codes match on word boundaries (`\b402\b`), so `4021 tokens` never matches |
| adjacency | R2 | ✅ covered | The same billing message is `quota_wait` on a router route and `billing_or_access` on a direct route |
| boundary | R2 | ✅ covered | ~~A route counts as router-backed exactly when `infer_fallback_quota` is true~~ *(superseded, D-05)* A route is router-backed when the catalog's confirmed `fallback_quota` says so, defaulting to `infer_fallback_quota` |
| concurrency | R2 | 🧪 backstop | Classification is a pure function of (pattern table, message, route) |
| empty | R2 | ✅ covered | No route information means the unknown-route rule |
| encoding | R2 | 🧪 backstop | Route kind comes from the candidate's runtime and model id, not from message text |
| idempotency | R2 | 🧪 backstop | Re-classifying the same captured output gives the same class |
| ordering | R2 | 🧪 backstop | Route kind is decided before message patterns are applied |
| precision | R2 | ✅ covered | Exit codes are exact: 75 for `quota_wait`, 69 for `billing_or_access` |
| adjacency | R3 | ✅ covered | A reset exactly 4 hours after first-seen is inside the window; one minute later is outside |
| empty | R3 | ✅ covered | No parsable reset time means the 10-minute cadence from the first check |
| encoding | R3 | ✅ covered | Times are parsed as local time unless a zone is given; a time already past today means tomorrow |
| ordering | R3 | 🧪 backstop | After the reset-time check, re-checks continue every 10 minutes |
| boundary | R4 | ✅ covered | A limit line in stderr stops the child within one watch interval |
| empty | R4 | ✅ covered | A timed-out child with no limit signal stays `timeout` |
| encoding | R4 | 🧪 backstop | Live watching reads stderr and structured events as decoded lines |
| precision | R4 | ✅ covered | Only stderr and structured fields are matched; a limit phrase only in the answer text is ignored |
| boundary | R5 | ✅ covered | The attempt cap is 24 re-checks (4 h at 10 min), counted from the state file's first-seen time |
| concurrency | R5 | ✅ covered | The state file is written atomically (mkstemp + replace); two waits for one task are refused by a task-keyed state path |
| idempotency | R5 | ✅ covered | A re-check that finds the state file already resolved does nothing |
| precision | R5 | ✅ covered | Elapsed time is measured from first-seen wall-clock time in the file, not from scheduler ticks |
| adjacency | R6 | ✅ covered | A clean tree with no other usable candidate waits for the same CLI |
| boundary | R6 | ✅ covered | At exactly 4 hours from first-seen the run stops and reports |
| empty | R6 | ✅ covered | No candidates at all: wait if `quota_wait`, else stop and report |
| ordering | R6 | 🧪 backstop | Fallback candidates are tried in the plan's ladder order |
| precision | R6 | 🧪 backstop | `tree=clean|dirty` comes from the runner's pre/post snapshot compare, not a heuristic |
| adjacency | R7 | ✅ covered | A resume after a fallback does not reuse the other CLI's session id |
| concurrency | R7 | 🧪 backstop | Only one dispatch per task is live at a time; the state file holds the lock |
| empty | R7 | ✅ covered | A clean tree means the original prompt is re-sent unchanged |
| encoding | R7 | 🧪 backstop | The done-work list in the resume prompt is file paths and diff stats, never file contents |
| idempotency | R7 | ✅ covered | Resuming twice from the same state never duplicates already-done work in the prompt |
| ordering | R7 | 🧪 backstop | Done work is listed in path order |
| adjacency | R8 | 🧪 backstop | The session's own resume (Phase 26) stays separate; these skills only handle subprocess limits |
| concurrency | R8 | 🧪 backstop | Each skill re-checks only its own tasks' state files |
| empty | R8 | ✅ covered | A skill run with no cross-AI dispatch never schedules a re-check |
| ordering | R8 | 🧪 backstop | Skills print the `AIKIT-XAI status=` line before acting on `action=` |

## Prohibitions (must-NOT)

**Coverage:** 4/4 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT wait longer than 4 hours from first-seen | R3, R5, R6 | resolved | test (cap read from the state file) |
| MUST NOT wait on a billing or access error from a direct third-party route | R2 | resolved | test |
| MUST NOT classify on the model's answer text | R4 | resolved | test (a limit phrase only in the answer is ignored) |
| MUST NOT write a key or token into a status line, state file or log | R5 | resolved | test (sentinel key absent from all outputs) |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | One policy, two classes, one wait |
| Boundary Clarity   | 0.85  | 0.70 | ✓      | Session self-resume and the rule are Phase 26 |
| Constraint Clarity | 0.85  | 0.65 | ✓      | Observed patterns only; no answer-text matching |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | 11 pass/fail criteria |
| **Ambiguity**      | 0.14  | ≤0.20| ✓      | Initial 0.24; one round |

## Interview Log

`--auto`, one round. The open items went through `ai-kit-gsd-spec-discuss`'s ladder (`decide.py`: Laya per item, `needs_fallback` to TypeSafe). Summaries only, advisory. Rule: best design over the smallest diff.

| Round | Perspective | Question summary | Laya (advisory) | TypeSafe (advisory) | Decision locked |
|-------|-------------|------------------|-----------------|---------------------|-----------------|
| 1 | Failure Analyst | A limit with another candidate available: fall back or wait? | always_fallback 0.54 (fb) | fallback_if_clean_else_wait 0.99 | Fall back when clean; wait and resume when dirty (R6) |
| 1 | Researcher | Use a reset time printed in the message? | ignore_reset 0.53 (fb) | use_reset_time 0.76 | Beyond 4 h stop now; inside, first re-check at the reset (R3) |
| 1 | Boundary Keeper | Where does the wait run? | runner_sleeps 0.44 (fb) | orchestrator_scheduler 0.99 | The runner exits at once; the orchestrator schedules (R5) |
| 1 | Simplifier | Default for an unknown route? | always_wait 0.56 (fb) | by_message 0.75 | Quota/rate-limit waits; billing/access does not (R2) |

---

*Phase: 25-quota-aware-cross-ai-subprocess-supervision*
*Spec created: 2026-10-14*
*Next step: /gsd-discuss-phase 25 — implementation decisions (how to build what's specified above)*


## Owner decision (2026-10-24): External Agent Runs ladder — supersedes the wait-and-resume design

Relayed from the owner (also in llm-env AGENTS.md "External Agent Runs"); binding over every
earlier requirement, decision and ruling in this phase that conflicts with it:
1. Transient (`[400]: event: error`, 5xx, cut stream, timeout): retry up to 3 times in the SAME
   session.
2. Still failing: a NEW session on the same lane (a router pins each session to one combo member;
   a new session lets the combo choose again), up to 3 more attempts.
3. Quota / rate limit / auth (429 monthly limit, 401/403): never retry the same model; stop and
   report.
4. Out of rungs: stop and report with evidence (status, lane/combo, model, times) for the owner.
The harness catalog (cursor, codex, claude, pi, opencode...) is a menu used only when the owner
names one: the runner never switches harness, provider or model on its own, and the automatic
fallback to another CLI is removed. Superseded here: the 10-minute / 4-hour wait-and-resume, any
"move to the next candidate" step, and the earlier ruling's single-retry transient rule (now 3+3).
Kept: the per-CLI pattern table, live and after-the-fact detection, the typed reason, session-id
continuation per CLI (used by rung 1), and the dirty-tree rule (a quota-class stop now ends in
stop-and-report, so the rule only matters for the transient rungs).

**Placement (owner correction, 2026-10-24):** the full ladder lives in the runner template
(`cross-ai.mjs`), implemented and pinned by its self-tests, and travels in every rendered copy
(`ai-kit-gsd-curated-config` `apply-execution` / `ensure-runner` and the `ai-kit-spec-execute*`
skills). Anything a skill writes into a project's AGENTS.md / CLAUDE[.local].md is a concise 3-4
line summary that points at the runner, never the detailed rule (Phase 26's rules emitter
follows this).

**Rule adjustment (owner, 2026-10-24, replaces step 3 "quota = stop without retrying"):** on a
quota or rate-limit error from a router lane, the orchestrator manages the session: it retries the
same lane up to 3 times, then switches session (the combo picks a member again) up to 3 times.
Only if the error persists after those 3 session switches does it report with evidence (status,
combo, model, times) and wait several minutes before trying again or reporting again. It still
never switches harness, provider or model on its own (the CLI catalog is used only when the owner
names one). Orchestrator interpretation, to confirm with the owner: auth errors (401/403) are not
covered by the adjustment and keep stop-and-report. The "several minutes" cooldown defaults to 10
minutes between full cycles and is bounded by this phase's existing 4-hour cap, so a cycle never
loops forever. Detail and tests live in `cross-ai.mjs`; instruction files keep the short pointer.

## Acceptance after the owner decision (2026-10-24)

The owner decision above supersedes the wait-and-resume design. Each criterion and edge maps to
**kept**, **adapted** (with the plan that pins it) or **superseded** (with the reason). The
caller contract is `skills/ai-kit-spec-review/references/subprocess-quota-policy.md`; the runner
template 7 self-test is the source of truth.
*(Amended 2026-10-25, Phase 25.1: the in-call rungs are now the configurable soft series of QTA-07, and the
router cooldown cycles are the caller's hard tier of QTA-08 (`hard_waits_s`, then notify and stop); the
caller contract moved to `skills/ai-kit-cross-ai/`.)*

### Acceptance criteria

- Every observed limit message is a classified fixture, labelled verified or unverified:
  **kept** (25-02 pattern table, 25-03 `--classify-only`, 25-04 live detection).
- Route kind changes the class of a billing message: **adapted** (25-03, 25-06, 25-08). Only a
  confirmed router route (`--route-<cli> router` or `CONFIG.routerBacked[cli]: true`) turns a
  billing or limit message into `quota` (exit 75, router cycles); a direct route, or a name-only
  `router-inferred` guess, keeps `billing` (exit 69, stop and report).
- A reset beyond 4 hours stops at once; a reset inside sets the first re-check:
  **superseded**. No reset time is parsed; every router cycle waits the fixed 600 s cooldown
  under the 14400 s cap. Phase 25.1 passes the upstream error through and leaves the
  reset inference to the waiting harness (owner, 2026-10-24).
- Live detection stops a child early; post-hoc detection classifies a timed-out child:
  **kept** (25-04).
- The runner exits at once with `retry-later` and a resume-state file; the cap comes from the
  file: **adapted** (25-06). Exit 75 with `retry_after_s=` and `cycle=` comes only after the
  3 + 3 ladder on a confirmed router lane; the cycle state file is keyed by lane, model and
  project, and the cap is measured from its first-seen time.
- Clean + candidate falls back; dirty waits and resumes; 4 hours stops with a report:
  **superseded** for the fallback and the dirty wait (one CLI per call, 25-01; a failure that
  changed the tree stops for the owner); **kept** for the 4-hour stop (exit 69, `stopped=cap`,
  25-06).
- A resume names the already-done work: **superseded**. There is no done-work list; a dirty
  failure stops for the owner instead of resuming.
- The three skills follow the policy and pass `/skill-judge`: **kept**, now four skills
  (25-09, 25-10; verdicts in `25-SKILL-JUDGE.md`).
- `make test` and `make validate` are green: **kept** (25-11 Task 3, plus `make e2e-docker`).
- MUST NOT: a wait never exceeds 4 hours from first-seen: **kept** (25-06 cap clamp, 14400 s).
- MUST NOT: a billing or access error on a direct third-party route is never waited on:
  **kept** (25-03, 25-06 self-tests).

### Edges

- **R1** (adjacency, boundary, empty, encoding, ordering, precision): **kept** (25-02).
- **R2** adjacency, empty, precision: **adapted** (25-03, 25-08). The router class needs a
  confirmed route; exit codes are 75 for `quota` and 69 for `billing`. Concurrency, encoding,
  idempotency, ordering: **kept** (pure classification, 25-03 `--classify-only`).
- **R3** encoding: **superseded** (no reset parsing). Adjacency, empty, ordering: **adapted**
  (25-06). The 4-hour boundary applies to the cycle cap from first-seen, a missing reset is the
  only case, and cycles repeat every 600 s until the cap.
- **R4** (boundary, empty, encoding, precision): **kept** (25-04).
- **R5** boundary: **adapted** (25-06). The cap is 14400 s elapsed from first-seen, not 24
  re-checks. Precision: **kept**. Concurrency and idempotency: **adapted** to 25-06's cross-call
  cycle state file, which carries:
  - an atomic 0600 write;
  - the quota budget keyed by lane and model;
  - the last session id stored with its task digest (the `<objective>` text), so one task never
    resumes another's session;
  - early re-entry refused (exit 75, `elapsed=0s`, the remaining `retry_after_s`);
  - a file whose last attempt is older than the 4-hour cap replaced as a fresh episode, noted
    `stale-state-fresh-start`.
- **R6** adjacency: **superseded** (no candidate fallback; the same lane cycles). Ordering:
  **superseded** (no fallback order). Empty: **adapted** (25-01). One CLI per call; a missing
  one stops with `not_installed`, exit 127. Boundary and precision: **kept** (25-06 cap,
  `tree=clean|dirty` from the runner's snapshot).
- **R7** adjacency, encoding, ordering, idempotency: **superseded**. There is no done-work list
  and no other CLI's session to avoid. Concurrency: **adapted** (25-06; early re-entry is refused
  by the state file's `due_at`). Empty: **kept** (a same-session or new-session retry re-sends the
  prompt unchanged, 25-05).
- **R8** concurrency: **superseded** (no recurring re-checks; one one-shot re-invoke per router
  exit 75, 25-09). Adjacency, empty, ordering: **kept** (25-09, 25-10; skills relay the
  `cross-ai: report` and `AIKIT-XAI` lines before acting).

### Reason set

25 D-21's `billing_or_access` reason is superseded as a behavior. A billing or access stop is
stop-and-report off a router (exit 69). On a confirmed router lane it is a router quota cycle:
the runner classifies it as `quota`, exit 75. Python keeps the label in `STATUS_TO_REASON` for
the status line it maps.
