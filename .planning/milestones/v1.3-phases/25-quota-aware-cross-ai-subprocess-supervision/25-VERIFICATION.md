---
phase: 25-quota-aware-cross-ai-subprocess-supervision
verified: 2026-10-25T12:00:00Z
status: gaps_found
score: 5/6 must-haves verified (5/5 roadmap success criteria; the skill-judge acceptance gate fails)
covered_files:
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-01-PLAN.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-01-SUMMARY.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-02-PLAN.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-02-SUMMARY.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-03-PLAN.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-03-SUMMARY.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-04-PLAN.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-04-SUMMARY.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-05-PLAN.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-05-SUMMARY.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-06-PLAN.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-06-SUMMARY.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-07-PLAN.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-07-SUMMARY.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-08-PLAN.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-08-SUMMARY.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-09-PLAN.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-09-SUMMARY.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-10-PLAN.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-10-SUMMARY.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-11-PLAN.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-11-SUMMARY.md
  - .planning/scripts/cross-ai.mjs
  - README.md
  - skills/ai-kit-gsd-curated-config/SKILL.md
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py
  - skills/ai-kit-gsd-curated-config/references/runner.md
  - skills/ai-kit-spec-execute-gsd/SKILL.md
  - skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py
  - skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_cross_ai.py
  - skills/ai-kit-spec-execute-superpowers/SKILL.md
  - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py
  - skills/ai-kit-spec-review/SKILL.md
  - skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py
  - skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py
  - skills/ai-kit-spec-review/references/cross-ai-dispatch.md
  - skills/ai-kit-spec-review/references/cross-ai.mjs
  - skills/ai-kit-spec-review/references/subprocess-quota-policy.md
  - tests/test_ai_kit_spec_runner_dispatch.py
  - tests/test_cross_ai_runner_e2e.py
  - tests/test_quota_policy_text.py
covered_digest: "v3:sha256:997cadb7f7c4a84efbd41d3d8a482ae61fc609464939df420354bd2664dcfb8e"
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "The four changed skills follow the policy and pass /skill-judge (25-SPEC acceptance 'kept, now four skills'; AGENTS.md: a materially updated SKILL.md passes the skill-judge loop before it is marked complete)"
    status: failed
    reason: "25-SKILL-JUDGE.md records all four skills as BLOCKED. Two of the three judge lanes did not finish round 5: my-referee-one hit quota exit 75, and my-referee-two crashed on an OmniRoute 404 'Combo has no executable targets'. On the only finished lane (native Opus), execute-gsd (96 vs base 104), execute-superpowers (100 vs 110) and curated-config (104 vs 106) score below their base scores, so the no-regression rule fails on the numbers. All four SKILL.md files changed again after round 5 (ed63b5e, then 8c3dbfa for curated-config/runner text) and were not judged again."
    artifacts:
      - path: "skills/ai-kit-spec-review/SKILL.md"
        issue: "BLOCKED: 100 >= 97 passes on Opus numbers, but the referee lanes did not complete; changed after round 5"
      - path: "skills/ai-kit-spec-execute-gsd/SKILL.md"
        issue: "BLOCKED: 96 < base 104, I3; changed after round 5"
      - path: "skills/ai-kit-spec-execute-superpowers/SKILL.md"
        issue: "BLOCKED: 100 < base 110, I2; changed after round 5"
      - path: "skills/ai-kit-gsd-curated-config/SKILL.md"
        issue: "BLOCKED: 104 < base 106, I1; changed after round 5"
    missing:
      - "Re-run all three judges (clean-context Opus, router-env/my-referee-one, router-env/my-referee-two) on the current SKILL.md bytes once the referee lanes recover (my-referee-one after its 5-hour session reset; my-referee-two once its combo has an executable target)"
      - "Owner decision recorded in 25-SKILL-JUDGE.md on whether the Phase 18.1 base scores (execute-gsd 104, execute-superpowers 110) remain the no-regression bar for the much longer Phase 25 skills; if they do, fix the remaining Important findings until each skill reaches its base"
      - "Update the four Verdict blocks in 25-SKILL-JUDGE.md to PASS (or to an owner-accepted override in this file's overrides: block) before the phase is marked complete"
human_verification:
  - test: "C1 cursor limit channel (25-OWNER-CAPTURES.md): capture one real cursor -p --output-format json run that hits a usage limit, redact it, run --classify-only"
    expected: "Channel (stderr vs result event), exit code and session_id presence are recorded; the classify status matches the intended row"
    why_human: "Needs a live vendor limit on the owner's own account; the cursor-action-usage-limit row ships unverified"
  - test: "C2 pi weekly limit on zai-coding-cn: record the exact wording and classify it"
    expected: "Wording recorded; the classify check shows whether it hits a limit row or stays transient"
    why_human: "Live vendor text never captured; pi-chatgpt-usage-limit ships unverified"
  - test: "C3 router bodies (MonthlyLimitError, Zen 'Model access is disabled', Go 'Insufficient account funds'), classified with route router; answer whether any body names the combo member"
    expected: "Each body is recorded redacted with its pattern; the member question is answered yes or no"
    why_human: "Live router bodies; vendor-monthly-limit, text-model-access-disabled, text-insufficient-funds ship unverified; the combo member is never printed today (SC2 'when known')"
  - test: "C4 claude Overloaded and 'resets <time> (<zone>)' wording and channel"
    expected: "Both wordings and channels recorded with classify status"
    why_human: "claude-hit-your-limit, text-hit-your-limit, claude-overloaded ship unverified"
  - test: "C5 codex reconnect: a transcript where a bare error event is followed by a completed turn"
    expected: "The transcript or a 'not found' note settles whether a bare codex error is terminal"
    why_human: "Live codex behavior; the runner treats it as non-terminal (live-codex-bare-error-no-kill) on assumption"
  - test: "C6 router recovery time from a failing run to the first success"
    expected: "Elapsed time recorded (informs cooldownS 600)"
    why_human: "Needs a real router quota episode"
  - test: "C7 owner confirmation of the orchestrator interpretations (auth stop + off-router quota stop A2; cycles span calls with exit 75 retry_after_s; router-tail [401]/missing-credential rows as quota; timeout reading; review-mode rung 1; pre-dispatch candidate selection A1 kept; one-shot CronCreate consumer; review lanes re-invoking the same router lane)"
    expected: "Every bullet answered yes, or no with a correction"
    why_human: "These are owner-policy readings, not code facts; in particular A1 (pre-dispatch candidate selection) sits next to the 'never switches model on its own' rule and only the owner can settle it"
---

# Phase 25: Quota-aware cross-AI subprocess supervision Verification Report

**Phase Goal:** When a cross-AI child (pi, opencode, cursor, codex) fails, the runner classifies the failure from its output and follows one owner-defined ladder: transient errors retry in the same session, then in a new session on the same lane; quota, rate-limit and auth stops are never retried on the same model and stop and report with evidence. It never switches harness, provider or model on its own and never falls back to another CLI. *(amended 2026-10-24, plus the same-day rule adjustment: router quota cycles 3 + 3, then report and a cooldown under the 4-hour cap.)*
**Verified:** 2026-10-25
**Status:** gaps_found
**Re-verification:** No, initial verification

## Verdict in one paragraph

The runtime goal is met in code. All five roadmap success criteria and QTA-01..QTA-03 are implemented and pinned by tests I ran myself: the template runner self-test (`self-test ok`, about 2 minutes), the dogfood copy's self-test (`self-test ok`), and 9 Python modules (1186 tests, including the 16-test hermetic runner e2e). One gap blocks completion: the skill-judge gate. It is a project rule (AGENTS.md) and a kept 25-SPEC acceptance criterion, and it is recorded BLOCKED for all four changed skills. Three skills score below their base on the only finished lane, and every SKILL.md changed after the last round. Seven owner captures (C1-C7) are `not run (owner)`. The 11 pattern rows without a live capture are honestly labelled `unverified`.

## Goal Achievement

### Observable Truths (roadmap success criteria + SPEC acceptance gate)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1: a per-CLI table of quota, limit, billing, auth and transient patterns, built from observed output, each row labelled verified or unverified | VERIFIED | `cross-ai.mjs:129-797` `PATTERNS`: 65 rows with `cli` in `*`, cursor, pi, claude, opencode. Classes are quota, billing, auth, permission_blocked, bad_model, transient. Every row has a `label` in {verified, unverified} and an `evidence` field (checked by parsing the table). The 11 unverified ids match the list in `subprocess-quota-policy.md` "Checking a capture" exactly. Codex has no row of its own and is covered by `*` rows plus event extraction (C5 is open). Self-test: 56 `CLASSIFY_CASES` (`:1276-1621`), `classify-only-fixtures` (`:5928`), and `pure-classify-order-mutation`. |
| 2 | SC2: failures are classified transient, quota/rate-limit, auth/billing or other. Route-aware only for the evidence it reports (a router lane names the combo and member when known) | VERIFIED | `classifyStop` `:1156-1173` (`routerLane && row.routerClass==='quota'`). `routeOf`/`confirmedRoute` `:1622-1635`: only the flag or `CONFIG.routerBacked===true` confirms a route. A name hint gives `router-inferred`, which is advisory. I ran `--classify-only` myself: direct `check your billing` gives `billing`/text-billing, the same text with route router gives `quota`, `401 Unauthorized` gives `auth`, `[400]: event: error` gives `transient`, and the WR-06 stack-trace `:401:17` and path `src/billing/x.ts` give `crash` (not misread). The report line names `lane=<cli>/<model>`, so the combo is the model id. The member is never printed because no probed CLI reports it (25-06 must-have; C3 open), so "when known" holds vacuously. Self-tests: `billing` `:3842`, `billing-router` `:3848`, `inferred-quota-no-cycle` `:4147`. |
| 3 | SC3: failures detected live (stdout/stderr while running) and after the fact (timeout, partial exit) | VERIFIED | Live: `runOnce` `:2279-2328` arms `armLimit` `:2266` from stderr lines, partial lines and terminal events, then kills after `LIMIT_GRACE_MS`. Post-hoc: `runCli` `:2553-2561` scans stderr, partial out/err and events on a timeout. CR-01 fix `:2544-2545`: a live hit is dropped when the child finished on its own with exit 0 and an answer. Self-tests: `live-limit-kill` `:4340`, `live-partial-kill`, `live-codex-turn-failed` `:4436`, `post-hoc-timeout-429` `:4417`, `post-hoc-timeout-transient-stays`, `answer-only-ok` `:4361` (an answer-only limit phrase is ignored, a SPEC prohibition), `live-hit-then-success` `:4111`. |
| 4 | SC4: transient gets 3 same-session retries, then 3 new sessions on the same lane. Router quota/rate-limit gets 3 + 3, then a report (status, lane, model, times) and a cooldown before the next cycle, never past 4 h. Auth stops and reports | VERIFIED | `ladderNext` `:1801-1830`, `ladderLimits` `:1786` (counts clamped 0..3, cap clamped to 14400, cooldown clamped to the cap). CONFIG `:63-98`: same 3, fresh 3, cooldownS 600, capS 14400. The cycle state file `:1847-1902` is atomic, 0600, keyed by checkout + lane + model, and carries the task digest. `cycleStop` `:2485-2496` exits 75 with `retry_after_s`/`cycle`, or 69 at the cap. The expired-cap early stop is `:2430-2436`. Report line: `logReport` `:2383`. Auth: `STATE_DELETE` plus the class stop `:2580-2590`. Self-tests: `ladder-transient-exhausted` `:4847` (7 calls, same model, rung-1 same sid, 3 fresh sids), `pure-ladder-sequence` `:4980`, `router-quota-one-cycle` `:3895` (7 calls, exit 75, cycle 0 persisted), `router-quota-second-cycle`, `router-quota-early-reentry` `:3969`, `expired-state-cap-stop` `:4012`, `quota-deadline-near-cap` `:4074`, `pure-ladder-quota-cycle` `:5065`, `pure-ladder-cap-boundary` `:5088`, `plain-quota-no-retry` `:4134`, `auth` `:3868`. Interpretation: the cooldown is not slept inside the runner. The caller waits `retry_after_s` and re-invokes (one-shot), as amended in 25-SPEC "Acceptance after the owner decision". Owner confirmation is pending in C7. |
| 5 | SC5: no automatic fallback to another CLI and no harness/provider/model switch. The same policy runs in ai-kit-spec-review and ai-kit-spec-execute*. The skill, README and runner self-tests document and pin it | VERIFIED | `main` `:6066-6168`: only `cands[0]` runs. The rest is logged as "the owner's menu (no automatic fallback)" `:6144`, and a missing first CLI gives `not_installed` 127 `:6160`. Self-tests: `config-prefer-first-only` `:5848`, `no-change-no-fallback` `:4318`, `non-git-no-fallback`, `review-edit-no-fallback`, `no-second-cli-review-edit`, `not-installed-first`. Python: `runner_flags` (`runner_dispatch.py:177-193`) passes one `--prefer <runtime>` and the confirmed `--route-<cli>`. `resolve_route` `:213-227` uses user-confirmed catalog booleans only. `run_runner_tiers` `:596-608` re-runs only the same spec on a timeout. `error_classifier.py:30-39` maps quota, transient, billing. Skills: spec-review `SKILL.md:326-350`, execute-superpowers `SKILL.md:42-57,339-350` and curated-config `SKILL.md:220-266` link `subprocess-quota-policy.md` and relay `cross-ai: report`/`AIKIT-XAI`; execute-gsd `SKILL.md:27-42` and `gsd_cross_ai.py:25-28` (route pinned from the catalog). The README row `README.md:45` says "one CLI per call with a failure ladder, no automatic fallback" (thin, see Anti-Patterns). `tests/test_quota_policy_text.py` (13 tests) pins the text. |
| 6 | 25-SPEC acceptance (kept): the four changed skills pass /skill-judge (AGENTS.md non-negotiable) | FAILED | `25-SKILL-JUDGE.md` "Verdicts": all four BLOCKED. On Opus numbers, execute-gsd scores 96 vs base 104, execute-superpowers 100 vs 110 and curated-config 104 vs 106. The referee lanes stopped (quota exit 75, combo 404). `git log` shows ed63b5e (all four SKILL.md) and 8c3dbfa changed them after round 5, and they were not re-judged. |

**Score:** 5/6 truths verified (0 present-but-behavior-unverified). All 5 roadmap success criteria are verified. The failed truth is the skill-judge acceptance gate.

### Deferred Items

None. Phase 25.1 (configurable ladder, upstream error passthrough, error catalog) and Phase 26 (session self-resume, rules emitter) do not cover the skill-judge gate for these Phase 25 SKILL.md changes, so the gap is not deferred.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skills/ai-kit-spec-review/references/cross-ai.mjs` | template-7 runner with pattern table, ladder, cycle state, self-tests | VERIFIED | 6285 lines. `--self-test` gives `self-test ok` (run here). |
| `.planning/scripts/cross-ai.mjs` | dogfood render of template 7 | VERIFIED | The diff against the template is only the stamp line and the CONFIG block (models, legacy `retries`/`timeoutMarginS`/`defaultOuterTimeoutS` keys). `--self-test` gives `self-test ok` (run here). |
| `skills/ai-kit-spec-review/references/subprocess-quota-policy.md` | caller contract | VERIFIED | Matches the runner's CONFIG, clamps and unverified ids. |
| `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py` | one-CLI flags, confirmed route, status-line parse | VERIFIED | Wired from `gsd_cross_ai.py` and the review dispatch. Tests pass. |
| `skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py` | typed reason from runner status (QTA-02, 16.1 D-13) | VERIFIED | `STATUS_TO_REASON` `:30-39`. |
| `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py` | renders/keeps the template-7 runner (CR-02 fix) | VERIFIED | `test_curated_config_script` 42 tests pass. |
| four changed `SKILL.md` files | document the policy, pass skill-judge | PARTIAL | The policy is documented and linked. Skill-judge is BLOCKED (gap). |
| `25-OWNER-CAPTURES.md` | owner kit for unverified rows | VERIFIED (as a kit) | C1-C7 are all `not run (owner)`, routed to human verification. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `runner_dispatch.run_runner` | `cross-ai.mjs` | `build_runner_argv` (node + template + `--prefer` one runtime + `--route-<cli>`) | WIRED | `runner_dispatch.py:230-238, 561-593` |
| `gsd_cross_ai.py` | `resolve_route` | catalog-confirmed route pinned into the hook | WIRED | `gsd_cross_ai.py:9,25-28` |
| runner status line | Python typed reason | `parse_status_line` -> `reason_for_status` | WIRED | `runner_dispatch.py:241-248, 546-558`; `error_classifier.py:121-128` |
| runner exit 75 + `retry_after_s` | caller one-shot re-invoke | skill text (`CronCreate` once at `retry_after_s`) | WIRED (text) | spec-review `SKILL.md:344-350`, superpowers `SKILL.md:339-350`. Whether the wake fires while GSD's prompt is pending is flagged unverified in the policy. |
| curated-config `ensure-runner` | template 7 | `cross_ai_script.py` render | WIRED | The dogfood copy carries template=7 with a sha256 stamp. |

### Data-Flow Trace (Level 4)

Not applicable: no rendered UI data. The evidence lines (`cross-ai: attempt`, `cross-ai: report`, `AIKIT-XAI ... retry_after_s= cycle=`) come from real runCli counters (`:2453-2462`). The sentinel self-tests (`sentinel-evidence` `:4181`, `sentinelsplit`, `sentinel-overlong`) prove no key reaches them.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Template runner ladder, cycles, live/post-hoc detection, no fallback | `node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test` | `self-test ok` (1m59s) | PASS |
| Dogfood runner copy behaves the same | `node .planning/scripts/cross-ai.mjs --self-test` | `self-test ok`, exit 0 | PASS |
| Route-aware classification and WR-06 fix | `--classify-only` on 7 synthetic cases (tmp, deleted) | stack/path -> crash; direct billing -> billing; router billing/429 -> quota; 401 -> auth; `[400]: event: error` -> transient | PASS |
| Python callers and policy text | `python3 tools/run_unittest_parallel.py` on test_quota_policy_text, test_ai_kit_spec_runner_dispatch, test_ai_kit_spec_gsd, test_ai_kit_spec_superpowers, test_curated_config_script, test_curated_config_plan_edit, test_ai_kit_spec, test_ai_kit_spec_runtimes_table | 8/8 modules, 1170 tests ok | PASS |
| Hermetic runner e2e through Python | `python3 tools/run_unittest_parallel.py tests.test_cross_ai_runner_e2e` | 16 tests ok (251 s) | PASS |

I did not re-run `make test`/`make validate` as a whole. 25-11-SUMMARY and the 25-REVIEW fix status claim both are green; that claim is not re-verified here.

### Probe Execution

No `scripts/*/tests/probe-*.sh` is declared for this phase. The runner's `--self-test` is the phase's declared probe, and it was executed above (PASS for both copies).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| QTA-01 | 25-02, 25-03, 25-08 | Per-CLI verified/unverified pattern table. The route decides wait-recoverable: router billing/limit is quota, direct third-party billing/access stops. The class feeds the ladder and never selects another candidate | SATISFIED | Truths 1-2. `billing` vs `billing-router` self-tests. The classify-only spot-check. |
| QTA-02 | 25-04, 25-06 | Live and after-the-fact detection, feeding the typed reason and the status line | SATISFIED | Truth 3. `error_classifier.py:30-39`. The `AIKIT-XAI` tail `finish` `:894-918`. |
| QTA-03 | 25-01, 25-05, 25-06, 25-09, 25-10 | The 3+3 transient ladder, the router quota 3+3 then report + cooldown (600 s, 4 h cap), auth stop, no harness/provider/model switch, no CLI fallback, documented in the skill, README and runner tests | SATISFIED (code). The skill-judge gate on the documenting SKILL.md files is open (gap). | Truths 4-5. |

No orphaned requirements: REQUIREMENTS.md maps only QTA-01..03 to Phase 25. QTA-07..09 belong to 25.1.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (33 reviewed files + dogfood runner) | - | TBD/FIXME/XXX/TODO/HACK | none found | - |
| `skills/ai-kit-spec-execute-gsd/SKILL.md` / `cli.py:763-773` | - | WR-05, only partly fixed: `--min` + `clear-workflow-keys` can delete a user's lower `cross_ai_timeout` (the per-run backup holds it) | Warning | The documented exception. A data-loss-adjacent config edit the user can recover from the backup. |
| `cross-ai.mjs` | 2275 | IN-01: unused `watchChunk` params; IN-03 redundant code; IN-05 stdout lines relayed to stderr; IN-07 wake-line pin evadable | Info | Left open by the review, low impact. |
| `cross-ai.mjs` | 2435 | an empty line inside the returned object literal (cosmetic leftover of the WR fix) | Info | None. |
| `README.md` | 45 | The ladder is documented as one table-cell phrase. The detail (3+3, 600 s, 4 h cap) lives only in the skill reference | Info | Meets the 25-10 must-have wording. A reader of the README alone does not see the cap. |

### Human Verification Required

#### 1-6. C1-C6 owner captures (`25-OWNER-CAPTURES.md`)

**Test:** Capture your own failing runs as they happen, redact them, and run `node skills/ai-kit-spec-review/references/cross-ai.mjs --classify-only <file>`. The captures are C1 cursor limit channel, C2 pi weekly-limit wording, C3 router bodies and combo member, C4 claude Overloaded/reset wording, C5 codex reconnect order, and C6 router recovery time.
**Expected:** Each pass rule in the kit is met. Matching rows flip from `unverified` to `verified` via `/gsd-plan-phase 25 --gaps`.
**Why human:** Live vendor/router behavior on the owner's account. The 11 `unverified` rows stay `unverified` until then, and they are labelled that way in the table and the policy.

#### 7. C7 owner confirmation of the orchestrator interpretations

**Test:** Answer each C7 bullet yes or no (with a correction if no).
**Expected:** Every bullet is answered. Pay particular attention to A1: pre-dispatch candidate selection, and the round 4-5 escalation, sit next to the "never switches model on its own" rule.
**Why human:** These are owner-policy readings, not code facts.

### Gaps Summary

One gap, from one root cause: the AGENTS.md skill-judge gate for the four Phase 25 SKILL.md files is not passed. Two of three judge lanes could not complete. The runner itself stopped them correctly (quota exit 75; combo 404 crash), which is the phase's ladder working as designed. On the remaining lane, three skills score below their Phase 18.1 base scores. All four files also changed after the last judged round. The runtime goal and every roadmap success criterion are achieved, but the phase cannot be marked complete under the project's own rule until the judges are re-run on the current bytes and either pass, or the owner records a decision on the base-score bar (possibly as an `overrides:` entry here).

---

_Verified: 2026-10-25_
_Verifier: Claude (gsd-verifier)_
