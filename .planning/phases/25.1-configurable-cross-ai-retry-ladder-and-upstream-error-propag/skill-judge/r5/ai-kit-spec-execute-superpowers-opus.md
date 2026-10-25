Judge: opus
Reviewed-sha256: 2aed7941ce4547821e04d7ec86d5741ad40e979393a065827aabf25e6688c3d8
Lane: native subagent completed
Score: 105
Critical: 0
Important: 1

**Skill evaluation: ai-kit-spec-execute-superpowers (Phase 25.1 re-judge, r5)**

- **Score:** 105/120, grade B. The skill follows the Process pattern, with Tool-pattern low-freedom bash blocks.
- **Knowledge ratio (E:A:R):** about 78:15:7.
- **Verdict:** The skill points at the new canonical ai-kit-cross-ai contract correctly:
  - It uses the right sections (4, 6, 8).
  - It describes the hard tier, `stopped=hard-waits`/`cap`, the `lane stopped=` refusal, upstream pass-through and the Copilot note accurately.
  - The `dispatch-task` path does run one `--runtime` with `--timeout`/`--outer-timeout`.
  - No stale `subprocess-quota-policy.md` or `REVIEW_SKILL_DIR` wake pointers remain.
  - Remaining issues: one policy-consistency gap (the Rounds 4–5 exception) and several clarity or token items.

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 17 | 20 | Dense, project-specific rules; the never-switch rule is restated 4 times and Step 3's routing opener duplicates Step 2 |
| D2 Mindset + Procedures | 13 | 15 | "Permanent or same-wave?" framing; the exact state and escalation procedures are expert-grade |
| D3 Anti-Patterns | 14 | 15 | NEVER index with non-obvious reasons, each repeated where it applies |
| D4 Spec / Description | 14 | 15 | WHAT, WHEN and the not-for case are all present; long, but the parent router selects it |
| D5 Progressive Disclosure | 13 | 15 | MANDATORY triggers sit in the workflow, and design-notes is marked "read only when a rule looks arbitrary"; SKILL.md is 460 lines |
| D6 Freedom Calibration | 14 | 15 | Low freedom with exact bash, which fits fragile state and resume work |
| D7 Pattern | 8 | 10 | Clear Process pattern, but heavy for it |
| D8 Usability | 12 | 15 | Ambiguous "point 4" numbering, two state files easy to confuse, no relay path for pre-spawn refusals |

**Findings**

1. **Important.** The skill claims a model-switch exception that the canonical policy does not have.
   - SKILL.md:51-53 and :413-418 say pre-dispatch selection and the Rounds 4–5 bump are "the only key changes".
   - ai-kit-cross-ai/SKILL.md:35-37 says the runtime and model are the owner's choice, set before a run. Section 8 (:168-170) says "Never switch … on any failure, in the runner or in a caller". Neither mentions this exception.
   - The Rounds 4–5 re-resolution (escalation.md:71-79) can pick a different runtime or provider after review findings, without asking. It is justified only by "assumption A1 in the Phase 25 owner captures" (design-notes.md:132). That is a `.planning` file the installed skill does not ship, and its C7 result is "not run (owner)".
   - Fix, either of:
     - add a scoped clause to ai-kit-cross-ai section 1 or 8 ("ladder selection before a dispatch, including the SDD Rounds 4–5 bump, is owner-configured selection, not a failure response");
     - or gate the Rounds 4–5 bump behind an explicit one-time owner yes, as `trust-local` is gated.
   - Also cite the rule in the skill, not a planning artifact.

2. **Minor.** Ambiguous "point 4". Step 3 has a top-level "4. Classify", and the quota branch has its own sub-point "4. Schedule or stop". SKILL.md:47 ("Step 3 point 4's print path"), :323 ("point 4 decides wait versus stop") and the wake prompt :386 ("point 3 … and point 4") mix the two. Fix: name the sub-steps ("quota branch step 4, Schedule or stop") or letter them.

3. **Minor.** Two different state files are easy to confuse.
   - SKILL.md:361-363 tells the owner to delete the runner's cycle-state file (the reset).
   - SKILL.md:371-373 tells the agent to report `$RESUME_STATE_PATH` (the adapter's state).
   - state-management.md:172-174 says "the state file the refusal names".
   - Fix: add one sentence that deleting `$RESUME_STATE_PATH` does not reset the lane; only the runner's `cross-ai: lane stopped=` path does.

4. **Minor.** Pre-spawn refusals have no evidence lines. `run_runner` refuses a model id outside the runner grammar (`reason="configuration"`, runner_dispatch.py:595-600) before any `cross-ai:`/`AIKIT-XAI` output. SKILL.md:402-404 still says to relay the report, upstream and `AIKIT-XAI` lines. Fix: "when no `AIKIT-XAI` line exists, relay the `ai-kit-spec:` line from `$DISPATCH_BASE.err` verbatim".

5. **Minor.** `classify_dispatch_failure` treats a malformed hint differently by status (dispatch_injection.py:423-430). Exit 75 with a non-numeric `retry_after_s` returns `"quota"` for status `quota` (through the `reason` fallback) but `"real_error"` for `transient` (its reason is `capacity`). The comment "only a bare one reads as the lane's wait" hides this. Both end in a stop. Fix: map every exit 69/75 with status `transient`/`quota` to `"quota"`, and let point 4's whole-number check decide.

6. **Minor.** Transient episodes are persisted as `"quota"`. SKILL.md:321-335 writes reason `"quota"` for a spent transient (5xx/`[400]`) hard tier as well. The owner-facing `reasons` then mislabel it; only the relayed `AIKIT-XAI` line shows the real class. Fix: say so in one line, or record the runner's status.

7. **Minor.** state-management.md:172 says "After the 4-hour cap". `capS` is a 14400 s ceiling and CONFIG can lower it (self-test `cap_s=300`). Fix: "the episode cap (`capS`, at most 4 h)".

8. **Minor.** design-notes.md:375-376 sends the reader to "the policy reference of ../../ai-kit-cross-ai/SKILL.md", which is one hop removed. Fix: link `../../ai-kit-cross-ai/references/subprocess-quota-policy.md` directly, and rewrap the overlong line.

9. **Minor.** Token waste.
   - The never-switch rule appears at SKILL.md:39-41, :49-53, :337 and :413-418.
   - Step 3's opener (:198) restates Step 2's routing paragraph (:145-150).
   - Fix: keep the NEVER index plus one point-of-use mention, and drop :198.

Not checked: I did not run the test suite or the runner self-test, and I only spot-checked the Copilot and model-grammar paths in code. The main risk is finding 1: until the owner rules on A1, the Rounds 4–5 bump can change runtime or model on its own.

DIGEST 2aed7941ce454782
CURRENT 105/120
CRITICAL 0 IMPORTANT 1
