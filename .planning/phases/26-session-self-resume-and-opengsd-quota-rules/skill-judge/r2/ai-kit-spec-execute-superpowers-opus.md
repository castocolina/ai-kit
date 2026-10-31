Judge: opus
Reviewed-sha256: ccbcea9bd76c22984a64850e1c56edc67e19d8f89daa963c012d71735e036195
Lane: native subagent completed
Score: 102
Critical: 0
Important: 2

# Skill Evaluation Report: ai-kit-spec-execute-superpowers

## Summary
- **Total Score**: 102/120 (85%)
- **Grade**: B
- **Pattern**: Process/Tool hybrid (phased adapter workflow, low-freedom exact bash, references for each fragile sub-procedure)
- **Knowledge Ratio**: E:A:R = about 80:15:5
- **Verdict**: A dense, well-sourced adapter with expert-grade anti-patterns. Its main gaps are two unstated scope rules: whether fix rounds 1 to 3 re-resolve, and what a woken run may do after its one re-dispatch.

## Structure check
- Frontmatter is valid. `name` is lowercase with hyphens. The description covers WHAT, WHEN, the trigger path (`docs/superpowers/plans/*.md`) and an explicit exclusion (`executing-plans`).
- SKILL.md is 498 lines, just under the 500-line ceiling and well above the 300-line ideal. The references are design-notes.md (139), escalation.md (107), quota-wake.md (43) and state-management.md (153).
- I verified these claims in the repo:
  - Shim subcommands and flags: `ai_kit_spec_superpowers/cli.py:388-466`.
  - `classify_dispatch_failure` exit 69/75 semantics and the `implementer_status` line-declaration parser: `dispatch_injection.py:398-457`.
  - The `no_usable_dispatch` fallback (`cli.py:134`) and `any_quota_recoverable` (`dispatch_injection.py:89`).
  - Codex `workspace-write` sandbox: `runner_dispatch.py:215`.
  - Node fail-closed line: `runner_dispatch.py:66`.
  - The `ignoring untrusted project-local config` line: `config_io.py:410`.
  - The `dispatching ... unverified` line: `routing.py:231`.
  - Claude native selectors fable/opus/sonnet/haiku: `detection.py:113`.
  - The `armed|refreshed <host>-<id>` output: `ai_kit_session_wake/arm.py:480`.
  - The `--host`/`--session-id` arm flags: `ai_kit_session_wake/cli.py:70-71`.
  - ai-kit-cross-ai sections 4, 6 and 8 exist, and section 6 holds the whole-minute and under-60 s rules.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 17 | 20 | Nearly all of it is proprietary contract knowledge: the three-set exclusion split, the anchor-relative floor, digest-preserving WRITE→APPEND, and status from stdout only. Small losses: the NEVER index is repeated at each point of use, and the SKILL.md:240 background paragraph is generic. |
| D2: Mindset + Procedures | 13 | 15 | Has a real thinking prompt ("is this exclusion permanent or same-wave?", SKILL.md:143). The domain procedures are ones no model would know. |
| D3: Anti-Pattern Quality | 14 | 15 | Nine specific NEVERs. Each gives its non-obvious failure (KeyError on mode shapes, a runtime id that excludes nothing, a quota exclusion that looks permanent). |
| D4: Specification Compliance | 14 | 15 | Strong description. It is router-targeted ("Use when ai-kit-spec-execute detects..."), with few user-phrased trigger words, which is acceptable for a routed adapter. |
| D5: Progressive Disclosure | 12 | 15 | MANDATORY read triggers are placed in the workflow steps, and design-notes has a "read only when a rule looks arbitrary" guard. SKILL.md sits at the 500-line ceiling, and some rationale repeats between the body and design-notes. |
| D6: Freedom Calibration | 13 | 15 | Exact bash for the fragile state, exclusion and dispatch steps is right. Scope gaps (finding 1) leave freedom exactly where the skill most wants it closed. |
| D7: Pattern Recognition | 8 | 10 | A clear phased process with checkpoints. It is long for the Process pattern (about 200 lines expected). |
| D8: Practical Usability | 11 | 15 | Rich branch handling and fallbacks, and the claims are verified. Two continuation and scope ambiguities could still steer an agent wrong. |

## Findings

### 1. Important: SKILL.md:141, SKILL.md:297, SKILL.md:184; references/escalation.md:73
**Problem:** The skill never says whether Step 2 (`resolve-injection`) re-runs at the start of fix rounds 1 to 3. Three passages point different ways:
- The Step 2 heading says "Before each task's implementer dispatch".
- Step 3 point 1 lists the fix-round order as increment, anchor, then Rounds 4–5 rule, then compose. It names no re-resolution.
- The trust-local text (SKILL.md:184) says the untrusted-config line "repeats on every task and fix round", which implies a re-resolve each round.
- escalation.md:73 re-runs resolve-injection "with this round's same --exclude-keys-json", which presumes a Step 2 ran this round.

**Why it matters:** With `external_cli`, a round-2 re-resolution can pick a different pair mid-task, for example a higher-ranked candidate whose quota recovered. That is a silent lane and model switch between fix rounds. It breaks the claim that pre-dispatch selection and the Rounds 4–5 bump are the only key choices. With `native` on Claude Code, it contradicts "fix-loop rounds 1–3 resume that same agent" (SKILL.md:243).

**Fix:** State it explicitly: "Fix rounds 1–3 reuse the task's `$INJECTION_JSON` unchanged and do not run Step 2. Only rounds 4–5 re-resolve, with the floor." Adjust the SKILL.md:184 and escalation.md:73 wording to match.

### 2. Important: references/quota-wake.md:9-25
**Problem:** The woken run is told "do not re-enter Step 2" with no scope limit. It binds `SHIM` but not `TOOLS_PY`, `SKILL_DIR` or `BRIEF_FILE`. Its step 5 then continues subagent-driven-development at "2. Handle the report". From there the review can open a fix round, or the run can move to the next task. Both need Step 2: `cache-path` via `$TOOLS_PY`, and `--task-file "$BRIEF_FILE"`.

**Why it matters:** A literal-minded woken agent will either refuse Step 2 for the rest of the run or guess the missing paths. SKILL.md:89-90 says to stop rather than guess a path.

**Fix:** Scope the ban to "for this re-dispatch only". Add `TOOLS_PY=<TOOLS_PY>` to the bindings, and update the placeholder count from twelve to thirteen. Tell the woken run to re-run Step 0 and take `BRIEF_FILE` from the restored ledger before any later fix round or task.

### Minor
3. **SKILL.md:123-126:** The arm block echoes `arm` output but ignores the `companion: create one one-shot in-session wake at <time>` line. ai-kit-session-wake SKILL.md ("When `arm` prints a companion time") says to act on it. Add one sentence that either defers to that section or says why it is skipped.
4. **SKILL.md:399-411 vs 412-418:** The wake is re-armed in point 3, before point 4 decides wait versus owner stop. On an exit-69 or bare-75 owner stop, the close step (SKILL.md:486-490) then runs `done` straight away. Move the re-arm into the one-shot-wait path.
5. **SKILL.md:327-329:** The no-JSON stop exits without the pinned state write and without `REPORT_MODE=append`. That contradicts the "After EVERY `dispatch-task` call" rule at SKILL.md:282. It is harmless because the run stops, but the resume after it has no pinned state. Say so, or write the state.
6. **references/design-notes.md:128-131:** "Both behaviors predate the owner rule… while the owner's confirmation is open" leaks planning status and names no rule. Drop it or name the rule.
7. **SKILL.md:240:** A general paragraph on the (runtime, model) pair repeats the design-notes "Why mode is checked" section. Cut it to one line to win back body length; SKILL.md is at 498 lines.
8. **SKILL.md:62 (Step 0):** The `$HOME/.claude/skills` fallback is Claude-specific. It is harmless, because the skill's own directory and the git toplevel come first, but the portable-first order could be noted.

## Top 3 Improvements
1. Close the fix-round re-resolution ambiguity (finding 1).
2. Make the quota-wake prompt self-sufficient for what follows its re-dispatch (finding 2).
3. Trim SKILL.md toward 400 lines: drop repeated rationale (SKILL.md:240, and duplicate why-text already in design-notes).

I did not check this live: I ran nothing, and I did not trace whether session-wake's `fire` plus the CronCreate one-shot could both resume one session (`liveness.py` not read).
