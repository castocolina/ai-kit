---
phase: 34
cycle: 3
reviewers: [referee-one]
reviewed_at: 2026-11-15T20:58:12Z
plans_reviewed: [34-01-PLAN.md, 34-02-PLAN.md, 34-03-PLAN.md, 34-04-PLAN.md, 34-05-PLAN.md, 34-06-PLAN.md, 34-07-PLAN.md, 34-08-PLAN.md, 34-09-PLAN.md, 34-10-PLAN.md]
models:
  referee-one: "router-env/my-referee-one"
model_sources:
  referee-one: "pinned"
---

# Cross-AI Plan Review — Phase 34

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

Review cycle 3 (re-review, the last one under the cycle cap), over the ten plans as revised in commit 5479fc5 against
cycle 2 (694ae43). Reviewer instance `referee-one` (`review.default_reviewers`) ran through the opencode lane
(`review-lane invoke --slug opencode --model router-env/my-referee-one --as referee-one`), with
`AI_KIT_REFUSE_REAL_HOME=1`, its own TMPDIR and its own process group. Lane result:
`{"slug":"opencode","ok":true,"stubbed":false,"model":{"value":"router-env/my-referee-one","source":"pinned"}}`; exit 0;
elapsed 1048 s (17:38:08 to 17:55:36 local); stderr empty, so no AIKIT-XAI status line (this lane does not go through
`cross-ai.mjs`); one attempt. The prompt (517 KB) carried everything cycle 2 carried (PROJECT.md first 80 lines, the
ROADMAP section, the jev requirements, SPEC, CONTEXT, the locked-decisions note, RESEARCH, PATTERNS, VALIDATION, the
ponytail-lens focus line verbatim, haiku-at-high executors, no network or real HOME in tests, the live calibration and
the judge loop orchestrator-driven by design), plus the whole cycle-2 REVIEWS.md and the cycle-3 brief: rate each of
the nine cycle-2 open items (C2-7, C2-9; the C1-7, C1-10, C1-11, C1-15, C1-18 residuals; C2-2, C2-4) FULLY / PARTLY /
NOT resolved, contest the twelve earlier refutations only with new evidence, and number new findings C3-n. Plan
coverage: all ten ids have their own section.

## OpenCode Review (referee-one) — cycle 3

Using the plan-review checklist and ponytail lens to verify the nine open items, preserve valid refutations, and check all ten revised plans against source. This review is read-only.

- **C3-1 — HIGH: Partial Laya identity failures do not trigger the SPEC’s fallback.** `34-06-PLAN.md:118` replaces a failed health-body read with `{}` and leaves the initial reachability result usable; `34-03-PLAN.md:123,127` can still learn under a configured version when OpenAPI is unavailable. This conflicts with `34-SPEC.md:150`, which requires unknown identity and ladder fallback when either identity endpoint is unreachable.

- **C3-2 — HIGH: Calibration timeouts can bypass the required “not run” record.** `34-09-PLAN.md:127,131` gives both subprocesses timeouts but specifies no `TimeoutExpired` handling. The record run can legitimately exceed 900 seconds: it makes 32 sequential screens (`eval_cases.py:230-247`), with retries and no total deadline in `live_env` (`34-09-PLAN.md:124`; `jev_review.py:1477-1507`). A timeout would leave the checkpoint’s required `calibration.json` missing or stale.

#### Document type
**GSD · implementation plans**, reviewed read-only at commit `5479fc5`.

Plan-file citations below are relative to `.planning/phases/34-jev-backends-by-host-and-laya-calibration/`. Resolution ratings assess the prescribed implementation and tests—not runtime completion of the plans.

### Cycle-2 resolution

| Finding | Resolution | Evidence and assessment |
|---|---|---|
| **C2-7** — overlapping Plans 07/08 | **FULLY** | Plan 07 remains wave 5; Plan 08 is now wave 6 and explicitly depends on 07 (`34-07-PLAN.md:5-6`; `34-08-PLAN.md:5-6`). Its rewording step expressly operates on Plan 07’s finished tree (`34-08-PLAN.md:132`). Plans 09/10 advance to waves 7/8 (`34-09-PLAN.md:5-6`; `34-10-PLAN.md:5-6,229`). |
| **C2-9** — unchecked calibration exit | **FULLY** | `calibrate_step` checks the return code before parsing the proposal, saves stdout/stderr, and returns a dated failure record (`34-09-PLAN.md:127`). The caller writes that failure instead of `"run": true` (`:131`). The fake self-test asserts exit 1 and retained stderr (`:129,146`). This covers the real non-zero paths in `skills/jev-fast-decision/scripts/eval_cases.py:199-220`. Timeout handling is a separate new concern below. |
| **C1-7 residual** — failed-source notice | **FULLY** | The revised success path retains notes found elsewhere and joins the failed-source notice with the feature notice (`34-03-PLAN.md:127`). The README-failure test now requires its URL, error class and “recorded from the sources that answered” (`:191,204`). This implements D-06’s notice without discarding usable notes. |
| **C1-10 residual** — feature refusal before collection | **FULLY** | Collection now runs immediately after `_feature_refusal`, before either returning or filtering dropped items (`34-06-PLAN.md:163`). The new `rank`-with-`images` case pins the pending note and fetch-free behavior (`:154,164,171`). This reaches the early-return mechanism in `skills/jev-fast-decision/scripts/jev_review.py:1910-1916`. |
| **C1-11 residual** — truth versus index fallback | **FULLY** | The truth now names failures of `changelog.md` and `models.md`, explicitly exempting the documented index fallback (`34-05-PLAN.md:28-29`). Implementation and page-by-page tests agree (`:113,144`). |
| **C1-15 residual** — “not only” negation | **FULLY** | The exact pattern excludes `not only` and `not just`; the adversarial fixture and acceptance check are present (`34-08-PLAN.md:114,128,141`). An in-memory check of the prescribed regex confirmed both affirmative phrases retain their install verb, while the permitted prohibition removes its verbs. |
| **C1-18 residual** — unusable explicit key-file setting | **FULLY** | `live_env` now replaces `JEV_API_KEY_FILE` whenever `real_state_key` reports a state-file source (`34-09-PLAN.md:123-124`); T-34-44 matches (`:235`). The source resolver does skip an unusable explicit file before selecting state (`skills/jev-fast-decision/scripts/jev_review.py:713-723,788-794`). |
| **C2-2** — URL query/fragment | **FULLY** | `valid_url` rejects both before persistence; refusal tests and acceptance criteria require them (`34-01-PLAN.md:120,127,144`). Plan 02 uses the same validator before endpoint construction (`34-02-PLAN.md:115`). This removes otherwise-discarded URL components before the CLI could echo them; the existing endpoint builder drops both (`skills/jev-fast-decision/scripts/jev_review.py:556-562`). |
| **C2-4** — secret-shaped unknown names | **FULLY** | Filtering now calls the existing sibling detector before truncating, counting or writing names, with mixed safe/secret sentinel coverage (`34-05-PLAN.md:146,151-154`). The copied-client fixture receives the newly required sibling (`34-06-PLAN.md:123`). T-34-42 explicitly accepts only the remaining **unknown-shape** limitation (`34-05-PLAN.md:188`). The existing detector recognizes the prescribed AWS-shaped sentinel (`skills/jev-fast-decision/scripts/secret_shapes.py:44-46,94-96`). |

### Earlier refutations

No new evidence establishes that an earlier rejection reason is wrong.

| Finding | Assessment |
|---|---|
| C1-1 | Not contested. |
| C1-8 | Not contested. |
| C1-12 | Not contested. |
| C1-14 | Not contested. |
| C1-16 | Not contested. |
| C1-20 | Not contested. |
| C2-1 | Not contested. |
| C2-3 | Not contested. |
| C2-5 | Not contested. |
| C2-6 | Not contested. |
| C2-8 | Not contested. |
| C2-10 | Not contested. |

In particular, the phase-wide full-test gate remains explicit in `34-VALIDATION.md:34`, and the ten prior judge drivers currently exist. Neither point is reopened.

### 34-01

**Summary:** The settings module is concrete and appropriately reuses the existing reader, splicer and publisher. The query/fragment revision is consistent across its contract, implementation instructions and tests.

**Strengths**
- The byte-read prescription preserves the splicer’s newline detection rather than normalizing input first (`34-01-PLAN.md:123,130`; `skills/ai-kit-spec-review/ai_kit_spec/toml_splice.py:105-110`).
- AST parity pins the copied definitions, while behavior tests cover the settings-specific additions (`34-01-PLAN.md:165-171,194-206`). An in-memory extraction check loaded the prescribed copy and successfully spliced CRLF input.

**Concerns**
- No new C3 concern identified.

**Suggestions**
- Retain the shared validator as the only URL acceptance rule; no additional URL parser or writer is needed.

**Risk assessment: LOW** — the revised write boundary and copy contract are well specified.

### 34-02

**Summary:** Backend wiring reaches the URL resolver, consent checks, CLI, probe and copied-client fixtures without adding a parallel consent system.

**Strengths**
- The planned gate explicitly prevents the legacy backend-name session grant from opening an off-loopback Laya (`34-02-PLAN.md:148,153`), while reusing the existing host-binding mechanism (`skills/jev-fast-decision/scripts/jev_review.py:1042-1060`).
- Keyed HTTP refusal is placed in URL resolution and tested before transport (`34-02-PLAN.md:149,152`); the existing send path attaches a bearer only after its gates (`skills/jev-fast-decision/scripts/jev_review.py:1420-1436`).

**Concerns**
- No new C3 concern identified.

**Suggestions**
- Keep the invariant and host-change tests alongside the transport refusal tests.

**Risk assessment: LOW** — the material remote-host boundaries have explicit negative coverage.

### 34-03

**Summary:** Identity, records and fetch decisions are separated behind an injected fetcher. The revised partial-success notice resolves the remaining cycle-2 issue, but malformed upstream JSON still lacks a defined failure path.

**Strengths**
- Same-version fingerprint changes and idle-with-configured-version behavior have separate tests (`34-03-PLAN.md:156-161`).
- Atomic JSON writing follows the existing consent writer’s cleanup and replacement pattern (`34-03-PLAN.md:117-118`; `skills/jev-fast-decision/scripts/jev_review.py:1013-1027`).

**Concerns**
- **C3-3 — MEDIUM: Valid JSON with an unexpected PyPI shape can escape the fetch-failure handling.** `34-03-PLAN.md:126` catches JSON parsing errors, then reads `info.description` and `info.version` without requiring the document and `info` to be objects. Responses such as `[]` or `{"info": null}` parse successfully but can raise `AttributeError`. The prescribed real fetcher returns raw bytes, not a validated PyPI object (`34-06-PLAN.md:116`), so this can abort the probe rather than preserve records and report a notice.

**Suggestions**
- Specify object checks for the parsed document and `info`, plus string checks for the extracted fields. Add fake cases for a JSON array and null `info`; require a normal failure result with unchanged prior records.

**Risk assessment: MEDIUM** — normal and source-failure cases are detailed, but malformed upstream data can bypass graceful degradation.

### 34-04

**Summary:** The knob is centralized, and internal callers stop overriding the user’s configuration. The downstream output assertions match the actual lookup consumers.

**Strengths**
- The ladder assertions pin the fields commit-fold and goal-prompt consume (`34-04-PLAN.md:149`; `skills/ai-kit-commit-fold/scripts/fold_group.py:265-273`; `skills/ai-kit-spec-goal-prompt/scripts/gp_host.py:517-533`).
- The client gate precedes stdin and sockets, while hook and judge-loop changes preserve only the user’s session override (`34-04-PLAN.md:111,179-181`).

**Concerns**
- No new C3 concern identified.

**Suggestions**
- Preserve the consumer-naming comments so these output-contract tests remain understandable.

**Risk assessment: LOW** — precedence and caller reach are explicit.

### 34-05

**Summary:** The local-pending design implements learning without adding public network work to answers. The secret-screen revision reuses the shipped detector and honestly bounds its remaining limitation.

**Strengths**
- Both required content pages must arrive before pending records become complete; index fallback is separately stated and tested (`34-05-PLAN.md:113,144`).
- The new filter uses `detect`, which returns shape names rather than matched secret text (`34-05-PLAN.md:151-152`; `skills/jev-fast-decision/scripts/secret_shapes.py:94-96`).

**Concerns**
- No new C3 concern identified.

**Suggestions**
- Keep the mixed secret/safe-name test: it proves filtering does not suppress legitimate observations along with the rejected name.

**Risk assessment: LOW** — the earlier secret-shaped-name concern is addressed without inventing another scanner.

### 34-06

**Summary:** The fetch seam, total per-fetch deadlines and answer-path separation are sound. However, partial failure of the identity GETs is not reconciled with the SPEC’s required fallback behavior.

**Strengths**
- Both new GET helpers pass real deadlines through the existing watchdog and bounded reader (`34-06-PLAN.md:115-116`; `skills/jev-fast-decision/scripts/jev_review.py:207-230`).
- The new feature-refusal collection occurs before the source’s early return or payload filtering (`34-06-PLAN.md:163`; `skills/jev-fast-decision/scripts/jev_review.py:1910-1920`).

**Concerns**
- **C3-1 — HIGH: Partial Laya identity failures do not trigger the SPEC’s fallback.** `34-06-PLAN.md:118` converts a failed health-body read to `{}` and passes a failed OpenAPI read onward without making the previously usable row unavailable. With a configured version, `34-03-PLAN.md:123,127` can still fetch or reuse a version-keyed record with no fingerprint. The initial probe remains sufficient for selection (`skills/jev-fast-decision/scripts/jev_review.py:1196-1204,1269-1278`). This contradicts `34-SPEC.md:150`: either identity endpoint being unreachable must produce unknown identity, no fingerprint and ladder fallback. The new trickle test asserts null fingerprint/unknown record but not fallback (`34-06-PLAN.md:193`).

**Suggestions**
- Define the identity-failure outcome explicitly and propagate it into selection/report usability. Test `/health` body failure and `/openapi.json` failure separately, including a configured version and an existing record; assert no learning fetch and the required fallback.

**Risk assessment: HIGH** — an explicit SPEC edge is not implemented by the prescribed control flow.

### 34-07

**Summary:** The recipe exposes the new behavior while keeping operational detail in the reference. Its exact target body remains within the existing cap.

**Strengths**
- The target body is **489 whitespace-separated words**, below the source test’s 500-word limit (`34-07-PLAN.md:272-325`; `tests/test_jev_fast_decision.py:2364-2366`).
- The limit sentence, settings pointers and MCP decision receive concrete doc-contract checks (`34-07-PLAN.md:117,142-158`).

**Concerns**
- No new C3 concern identified.

**Suggestions**
- Preserve the distinction between documented upstream capabilities and supported cells during later judge fixes.

**Risk assessment: LOW** — the documentation changes are bounded and testable.

### 34-08

**Summary:** The revised schedule removes the former race, and the negation revision addresses the specific residual without weakening the adversarial fixtures.

**Strengths**
- Dependency ordering now makes the guard inspect Plan 07’s finished tree (`34-08-PLAN.md:5-6,132`).
- The exact regex and non-vacuity fixtures distinguish affirmative “not only” wording from the allowed prohibition (`34-08-PLAN.md:114,128-129`).

**Concerns**
- No new C3 concern identified.

**Suggestions**
- Keep guard claims bounded to the implemented matcher; retain the recorded false-positive/rewording procedure rather than adding a broader prose-analysis framework.

**Risk assessment: LOW** — the two revised mechanisms are explicit and checkable.

### 34-09

**Summary:** The revised calibration-exit check correctly prevents false success, and the state-file override preserves the client’s actual credential precedence. The new helper still leaves subprocess timeouts outside the promised failure-record flow.

**Strengths**
- `calibrate_step` checks both process success and presence of the proposal before accepting calibration (`34-09-PLAN.md:127,131`), matching the source’s print-before-rewrite-failure behavior (`skills/jev-fast-decision/scripts/eval_cases.py:204-213`).
- The driver delegates address, consent and response validation to the client rather than duplicating them (`34-09-PLAN.md:125-126`).

**Concerns**
- **C3-2 — HIGH: Calibration timeouts can bypass the required “not run” record.** Both subprocess calls specify timeouts, but neither prescribes handling `subprocess.TimeoutExpired` (`34-09-PLAN.md:127,131`). The record run can exceed 900 seconds: it performs 32 sequential screens (`skills/jev-fast-decision/scripts/eval_cases.py:230-247`), each with retries (`jev_review.py:1477-1507`), while `live_env` removes the total deadline (`34-09-PLAN.md:124`). A timeout therefore leaves the checkpoint’s required `calibration.json` missing or stale instead of producing the promised dated failure (`:161,168-173`).

**Suggestions**
- Route timeout and process-start failures through the same dated `"run": false` result path, retain available diagnostics, and ensure the config snapshot check still runs. Extend `selftest` with a fake timeout result—no sleeping or live subprocess delay is needed.

**Risk assessment: HIGH** — the orchestrator’s bounded-run failure path can fail its own checkpoint gate.

### 34-10

**Summary:** The shifted final wave remains correctly dependent on all implementation plans. The configured referee pool, frozen tree and record publication are well grounded in existing machinery.

**Strengths**
- The pool policy matches `choose_pool`: first two usable external judges, with one usable judge allowed and no native fallback when omitted (`34-10-PLAN.md:26,95`; `tools/judge_loop.py:1538-1549`).
- Publication uses the existing conflict-refusing copier, and verification separates reproducibility/currentness from the bar calculation (`34-10-PLAN.md:167-174`; `tmp/judge-33/publish.py:50-70`; `tmp/judge-33/bar_table.py:77-89`).

**Concerns**
- No new C3 concern identified.

**Suggestions**
- Retain the final phase-wide `make test` after any judge-driven fixes, as already scheduled in `34-VALIDATION.md:34`.

**Risk assessment: LOW** — no new dependency or judge-policy defect found.

### Overall assessment

**All nine cycle-2 open items are fully resolved at the plan-text level. All twelve earlier refutations remain uncontested.**

Three new concerns remain:
- **HIGH:** C3-1 — partial identity failure does not implement the SPEC fallback.
- **HIGH:** C3-2 — calibration timeout can omit the required failure record.
- **MEDIUM:** C3-3 — malformed PyPI JSON shape can escape graceful failure handling.

#### Status: Issues Found — fix before execution

No repository files were modified. I did not execute the implementation plans, full test suite, live calibration/spike or judge lanes; runtime correctness remains unverified.


---

## Consensus Summary

Cycle 3. One reviewer ran (`referee-one`), so there is no cross-reviewer agreement to report and the consensus gate
does not engage. The review cites `file:line` evidence throughout and carries no evidence-quality discount marker. The
orchestrator checked every resolution verdict and every new finding against the revised plans (5479fc5) and the source
(tables below), with the same rule as cycles 1 and 2: a finding is excluded from the counts only when the source shows
it is wrong or when it asks to change a locked decision; a confirmed finding that does not meet the HIGH bar of the
review brief is kept at a lower severity with the reason. All twelve earlier refutations stand: the reviewer contested
none.

### Agreed Strengths
- (single reviewer) Every cycle-2 open item is resolved by a concrete plan change with its test or check: the wave
  split (07 alone in wave 5, 08 in wave 6 on 07), `calibrate_step`, the failed-source notice, the post-feature-pass
  note, the reworded truth, the `not(?!\W+(?:only|just)\b)` lookahead, the `JEV_API_KEY_FILE` replacement, the
  query/fragment refusal and the `secret_shapes.detect` screen, each reusing what the skill already ships.

### Agreed Concerns
- None (one reviewer). The reviewer's priority order: C3-1 (identity-endpoint failure and the SPEC R2 empty edge),
  C3-2 (a calibration subprocess timeout leaves no record), then C3-3 (a non-object PyPI JSON shape).

### Divergent Views
- None (one reviewer). The orchestrator's source check agrees with all nine FULLY verdicts and with C3-2 and C3-3, and
  refutes C3-1 (table below).

### Source check of the cycle-2 resolution verdicts (orchestrator, 2026-11-15)

| # | Reviewer | Orchestrator | Evidence |
|---|----------|--------------|----------|
| C2-7 | FULLY | FULLY (agreed) | `34-07-PLAN.md:5-6` wave 5 on 34-06; `34-08-PLAN.md:5-6` wave 6 on [34-06, 34-07]; `34-09-PLAN.md:5` wave 7; `34-10-PLAN.md:5,229` wave 8; ROADMAP plan list regrouped (`.planning/ROADMAP.md:647-674`). Plan 07 is alone in wave 5, so Plan 08's guard and rewording step (`34-08-PLAN.md:132`) read finished text. |
| C2-9 | FULLY | FULLY (agreed) | `calibrate_step` (`34-09-PLAN.md:127`) checks the rc, then the proposal line; the caller writes its `run: false` (`:131`). The self-test's missing-file case matches the source: `_run_calibration` prints `results file missing: <path>` to stderr and returns 1 before reading anything (`eval_cases.py:199-202`). |
| C1-7 residual | FULLY | FULLY (agreed) | `learn_laya` builds the notice part `Laya notes source failed (...); recorded from the sources that answered` whenever `errors` is non-empty (`34-03-PLAN.md:127`); pinned by the README-failing test (`:191,204`); truth `:31`. |
| C1-10 residual | FULLY | FULLY (agreed) | `_note_unknown_items(payload)` right after `_feature_refusal` when `stopped is not None or dropped` (`34-06-PLAN.md:163`), before the early return the source has at `jev_review.py:1910-1912`; test `:154`; acceptance requires two call sites (`:171`). |
| C1-11 residual | FULLY | FULLY (agreed) | The truth names only `changelog.md` and `models.md` and points at the llms.txt fallback truth (`34-05-PLAN.md:28-29`). |
| C1-15 residual | FULLY | FULLY (agreed) | `NEGATED_STEP` carries `not(?!\W+(?:only|just)\b)` (`34-08-PLAN.md:114`); fixture "Do not only install Laya from another repository." (`:128`); acceptance `:141`. The planner's check script (`tmp/p34/replan2/check_patterns.py`, the exact plan patterns) prints `checks: ok`, re-run here. |
| C1-18 residual | FULLY | FULLY (agreed) | `live_env` sets `JEV_API_KEY_FILE=state_key` whenever `state_key` is set, replacing an existing value (`34-09-PLAN.md:124`); the client reaches `state` only after skipping an unset or unusable key file (`jev_review.py:713-723,782-794`). |
| C2-2 | FULLY | FULLY (agreed) | `valid_url` requires empty `.query` and `.fragment` (`34-01-PLAN.md:120`), tests `:144`, T-34-02 `:238`; Plan 02's `_laya_url` calls the same check (`34-02-PLAN.md:115`). No existing test or skill file sets a Laya URL with `?` or `#` (rg over `tests/` and `skills/`). |
| C2-4 | FULLY | FULLY (agreed) | `note_unknown` keeps only names for which `_SECRET_SHAPES.detect(name)` is empty (`34-05-PLAN.md:152`), loader copied from `jev_ladder.py:61-73` (`:151`); the sentinel `"option:" + "AKIA" + "X" * 16` fits `_UNKNOWN_NAME` (`:150`) and matches `secret_shapes.py:46`; T-34-42 narrowed to the shapeless-key residual (`:188`). Knock-on reached: the spaced copied client gets `secret_shapes.py` (`34-06-PLAN.md:123`); `_isolated_ladder` already copies it; the only other test that copies a `jev_review.py` copies a stub (`tests/test_decision_probe.py:110`), and the commit-fold test copies the whole skill folder (`tests/test_ai_kit_commit_fold.py:764`). |

### Source check of the cycle-3 findings (orchestrator, 2026-11-15)

| # | Plan | Finding | Reviewer | Verdict | Evidence |
|---|------|---------|----------|---------|----------|
| C3-1 | 06, 03 | A failed `/health` body read or `/openapi.json` read leaves Laya usable and can learn under a configured version, against SPEC R2's empty edge ("version unknown, no fingerprint, the ladder falls through") | HIGH | REFUTED | The edge (`34-SPEC.md:150`) ends "the ladder falls through **as today**". `/health` unreachable is the row-unusable branch: today's gate-first probe fails, the row drops out of the ladder (`jev_review.py:1191-1204`), and the plan reports version None, `version_source` `unreachable`, fingerprint None, record `unknown` (`34-06-PLAN.md:118`). `/openapi.json` unreachable with `/health` answering: today that Laya is used (OpenAPI plays no part in selection), so "as today" means no ladder change, not a new refusal; the plan gives no fingerprint (`openapi_part` None, `34-03-PLAN.md:120`) and record `unknown` when no version exists (`:127` step a), pinned by the trickling-identity test (`34-06-PLAN.md:193`). A configured `laya_version` is locked D-04's second source (`34-CONTEXT.md:49`), independent of either endpoint, and `34-03-PLAN.md:127` step c says a version-keyed entry is not fingerprint-compared without an OpenAPI part. A `/health` body that fails on the second GET gives `health = {}`, so `loaded` is missing and the idle branch applies (`34-03-PLAN.md:160`): with no matching recorded fingerprint it is `pending_idle` and nothing is fetched (`:127` step b). Not counted. |
| C3-2 | 09 | `live.py calibrate` gives both subprocesses a timeout (900 s, 120 s) but no `subprocess.TimeoutExpired` handling, so a slow run leaves no `calibration.json` | HIGH | CONFIRMED | `34-09-PLAN.md:127,131` name the timeouts and handle only a non-zero rc; `subprocess.run(timeout=...)` raises `TimeoutExpired`, which ends the driver with a traceback before `calibration.json` is written and before the after-run `snapshot()` check. 32 sequential cases (`eval_cases.py:230-247`), each with a 20 s call timeout and the row's retries (`jev_review.py:1477-1507`), with the total deadline stripped (`34-09-PLAN.md:124`), can exceed 900 s. Task 2's gate requires `calibration.json` to exist and parse (`:165-173`), and Resolved Open Question 6 / T-34-33 require a recorded "not run" (`:233`), so this path fails the plan's own gate with no recorded fallback. Impact note: orchestrator scratch; the fix is a `TimeoutExpired` (and `OSError`) branch in both calls that writes `{"run": false, "date", "host", "reason": "eval_cases --record timed out after 900 s"}` (or the `--calibrate` form) and still runs the snapshot check, plus a selftest case (a 0.1 s timeout on a child that sleeps, or a patched `subprocess.run` raising `TimeoutExpired`). |
| C3-3 | 03 | Valid JSON with a non-object top level or a null `info` escapes `fetch_laya_notes`' error handling | MEDIUM | CONFIRMED | `34-03-PLAN.md:126` catches only `ValueError` from the parse, then says "take info.description (str, else "")" without requiring the document and `info` to be dicts; `[]` or `{"info": null}` would raise `AttributeError` in a direct reading, and `_laya_learn` calls `learn_laya` with no catch (`34-06-PLAN.md:118`), so `--probe` could fail instead of recording `fetch_failed`. Not HIGH: the source is a fixed PyPI URL that returns an object, and the fix is a type check. |

### Current HIGH Concerns (cycle 3)

Single reviewer, so the consensus gate is skipped. 1 open, confirmed against the plan and source; every cycle-1 and
cycle-2 HIGH is resolved:
- C3-2 (Plan 09): `live.py calibrate` does not handle `subprocess.TimeoutExpired` from the `--record` (900 s) or
  `--calibrate` (120 s) run, so a slow live run ends without `calibration.json` and skips the snapshot check. Change
  needed: both calls catch `subprocess.TimeoutExpired` and `OSError` and write a dated `{"run": false, ..., "reason":
  "eval_cases --record timed out after 900 s"}` (or `--calibrate ... 120 s`) record, keeping any partial stdout and
  stderr, then still run the snapshot check; `selftest` proves the timeout path without a live call.

C3-1 is refuted (above) and not counted.

### Current Actionable Non-HIGH Concerns (cycle 3)

1 open (MEDIUM), not yet in a plan:
- C3-3 (Plan 03): in `fetch_laya_notes`, a PyPI document that is not a dict, or whose `info` is not a dict, is a source
  error (`f"{url}: unexpected JSON shape"`, continue) like a parse failure; add `[]` and `{"info": null}` cases to
  `test_failed_fetch_keeps_records_and_says_so` (records unchanged, `fetch_failed` with no other source).

C1-1, C1-8, C1-12, C1-14, C1-16, C1-20, C2-1, C2-3, C2-5, C2-6, C2-8 and C2-10 stay refuted (not contested); C3-1 is
refuted and not counted.

### Verification coverage (source-grounding pass, cycle 3)

- Revision sweep: `git diff 694ae43 5479fc5` over the phase folder and each plan's `### Round 2 — 694ae43` ledger
  (`tmp/auto/r325/conv-34/review-c3/round2.py`); frontmatter waves and dependencies of all ten plans; the ROADMAP plan
  list (`.planning/ROADMAP.md:647-674`).
- Findings: each checked by reading the cited plan lines and source (`jev_review.py:556-562,700-794,1185-1210,1262-1282,
  1470-1510,1855-1928`, `eval_cases.py:180-235`, `secret_shapes.py:17,46,91-99`, `jev_ladder.py:50-80`,
  `tests/test_secret_shapes_copy_install.py:20,106`, `tests/test_decision_probe.py:110`,
  `tests/test_ai_kit_commit_fold.py:764`, `34-SPEC.md:140-158`, `34-CONTEXT.md:49,53`, plans `34-01:30,120-122,144,238`,
  `34-02:115,261`, `34-03:31,119-128,160,182-204`, `34-05:24-34,134-165,188`, `34-06:112-118,123,144-171,190-195,232`,
  `34-08:1-20,33-34,114-141`, `34-09:33,123-147,155-175,233`, `34-10:5,229`); the planner's
  `tmp/p34/replan2/check_patterns.py` re-run (`checks: ok`); rg for Laya URLs holding `?` or `#` in `tests/` and
  `skills/` (none); `check_index_coverage` reported no recorded issue for the six source files relied on. Cycle-2
  verdicts: all nine FULLY, agreed. Cycle-3 findings: 3 raised, 1 confirmed HIGH (C3-2), 1 confirmed MEDIUM (C3-3),
  1 refuted (C3-1).
- Not run: the plans themselves, the test suite, the live calibration or spike, any judge lane.

---

## Cycle 2 record (694ae43)

Review cycle 2 (re-review), over the ten plans as revised in commit a059e68 against cycle 1 (b0485b0). Reviewer instance
`referee-one` (`review.default_reviewers`) ran through the opencode lane (`review-lane invoke --slug opencode --model
router-env/my-referee-one --as referee-one`), with `AI_KIT_REFUSE_REAL_HOME=1`, its own TMPDIR and its own process
group. Lane result: `{"slug":"opencode","ok":true,"stubbed":false,"model":{"value":"router-env/my-referee-one","source":"pinned"}}`;
exit 0; elapsed 314 s (17:11:31 to 17:16:45 local); stderr empty, so no AIKIT-XAI status line (this lane does not go
through `cross-ai.mjs`); one attempt. The prompt (462 KB) carried everything cycle 1 carried (PROJECT.md first 80
lines, the ROADMAP section, the jev requirements, SPEC, CONTEXT, the locked-decisions note, RESEARCH, PATTERNS,
VALIDATION, the ponytail-lens focus line verbatim, haiku-at-high executors, no network or real HOME in tests, the live
calibration and the judge loop orchestrator-driven by design), plus the whole cycle-1 REVIEWS.md and the cycle-2 brief:
rate each confirmed cycle-1 finding FULLY / PARTLY / NOT resolved, contest the six refutations (C1-1, C1-8, C1-12,
C1-14, C1-16, C1-20) only with new evidence, and number new findings C2-n. Plan coverage: all ten ids have their own
section.

### OpenCode Review (referee-one) — cycle 2

Using the plan-review checklist to recheck the revised plans against the locked decisions and source. I’ll keep the review read-only.
#### Cycle-1 resolution

GSD · plan review. The checkout is at revised commit `a059e68`. Ratings below assess the task text and tests, not just the disposition ledgers. Paths in this table are relative to `.planning/phases/34-jev-backends-by-host-and-laya-calibration/` unless otherwise stated.

| Finding | Resolution | Evidence and remaining work |
|---|---|---|
| C1-2 | **FULLY** | `34-01-PLAN.md:123,130` now reads bytes, parses and decodes them, and tests CRLF preservation. This matches the source’s byte-read pattern in `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:332-355`. |
| C1-3 | **FULLY** | `34-02-PLAN.md:143-150` removes the name-only session-gate alternative for an off-loopback Laya and tests both gate values and a host change. Threat T-34-39 records the boundary. |
| C1-4 | **FULLY** | `34-02-PLAN.md:144-149` refuses a keyed off-loopback HTTP URL before transport and tests the refusal. The existing bearer attachment is at `skills/jev-fast-decision/scripts/jev_review.py:1429-1435`; T-34-40 records the mitigation. |
| C1-5 | **FULLY** | The tracers now explicitly unpack `code, report = self.run_probe()` in `34-02-PLAN.md:119`, `34-04-PLAN.md:113`, and `34-06-PLAN.md:126`. The helper’s tuple contract is in `tests/test_jev_fast_decision.py:368-371`. |
| C1-6 | **FULLY** | `34-03-PLAN.md:127,158-166` compares a version-keyed record’s fingerprint and makes idle-without-a-match return `pending_idle` before fetching, with tests for both cases. |
| C1-7 | **PARTLY** | The original “no notes plus one failed source” case is fixed, including forced refresh (`34-03-PLAN.md:126-127,190-191`). But the revised plan explicitly records a successful PyPI result when README fails (`:192`), without the failure notice or preservation of the previous entry required by D-06. Add the found-notes/failed-second-source refresh case and define its failure handling. |
| C1-9 | **FULLY** | `34-04-PLAN.md:34,145` records and tests the relevant output fields. The source chain is as stated: `fold_group.py:250-273` reads the decided column and `gp_host.py:497-533` reads detect’s backend map. |
| C1-10 | **PARTLY** | The local pending mechanism and tests for an unknown top-level response field and refused `rank` item are now specified (`34-05-PLAN.md:147-148`; `34-06-PLAN.md:152-162`). However, collection runs only **after** `checked_response` succeeds or on the `request_body` validation exception. A response with an unknown answer primitive fails validation first (`skills/jev-fast-decision/scripts/jev_review.py:397-415,498-532`), and feature refusals occur earlier (`:1895-1920`). Those encounters never reach either collector. Cover these paths without fetching on the answer path. |
| C1-11 | **PARTLY** | The changelog and models failures now stay pending and are tested separately (`34-05-PLAN.md:112,141-143`). An `llms.txt` failure is deliberately recorded as complete using defaults (`:112`), despite the plan’s “a failed doc fetch keeps every id pending” truth (`:28`) and the locked full doc-flow/failure requirement. The test currently pins the opposite (`:143`). Reconcile the failure behavior and tests. |
| C1-13 | **FULLY** | `34-06-PLAN.md:115-116,194-195` passes a real deadline to exchange and body reading and specifies trickle tests for both sources. The existing watchdog and body clock are in `jev_review.py:207-230,1342-1368`; T-34-20 is updated. |
| C1-15 | **PARTLY** | The named-repository, wrapped-line and unrelated-negation examples now have explicit tests (`34-08-PLAN.md:112-128`). The prescribed `NEGATED_STEP`, however, also removes an affirmative verb in “not only install Laya from another repository”; the sentence then passes (`:112,117`). Add this adversarial case and distinguish “not only …” from a prohibition. |
| C1-17 | **PARTLY** | The driver now delegates resolution and gate-first probing to the client (`34-09-PLAN.md:123-124`), addressing the wrong-layer and pre-consent socket mechanisms. The requested fake coverage for project override, declined URL and remote-without-consent is still absent: `selftest` at `:127` exercises the TypeSafe spike only. Add those driver-level fake cases. |
| C1-18 | **PARTLY** | The normal state-only case is addressed by `real_state_key` and `JEV_API_KEY_FILE` (`34-09-PLAN.md:122-123`). But if an already-set `JEV_API_KEY_FILE` is unusable, the existing resolver can skip it and choose the state file (`jev_review.py:701-723,773-794`); the plan then refuses to replace the set variable and scratch state hides the working key again. The planned state-key-only fake test is also missing (`34-09-PLAN.md:127`). |
| C1-19 | **FULLY** | `34-09-PLAN.md:125,127` defines IDs, validation, mapping, scoring and a five-request fake self-test. `checked_response` validates the exact ID set and answer shapes in `jev_review.py:510-532`. |

#### Cycle-1 refutations

| Finding | Re-review |
|---|---|
| C1-1 | Not contested. |
| C1-8 | Not contested. |
| C1-12 | Not contested. |
| C1-14 | Not contested. |
| C1-16 | Not contested. |
| C1-20 | Not contested. |

#### 34-01

**Summary:** The reader/splicer copy and byte-preserving write are well grounded, but the first-run write destination can make the question recur indefinitely.

**Strengths**
- The prescribed byte read and CRLF regression reuse the existing parser and splicer (`34-01-PLAN.md:123,130`; `config_io.py:332-355`).

**Concerns**
- **C2-1 — HIGH: A project-level empty or conflicting setting can defeat the asked-once flow.** `34-01-PLAN.md:123,202` writes answers only to the user layer while project settings win on read. If a project’s `laya_url = ""` or `enabled = false` is the effective value, a later user-layer `config set` cannot change that effective setting. More importantly, a first-run answer saved globally can be masked by a project-layer value introduced between probe and save; the prescribed workflow does not report that the saved answer is ineffective. This breaks the intended reliable first-run settings workflow.

**Suggestions**
- After saving, resolve and report the effective setting and source; give an explicit project-layer remediation when the user answer is masked. Test both keys with project overrides.

**Risk assessment: HIGH** — a successful-looking save may not take effect.

#### 34-02

**Summary:** The plan reuses host-bound consent and adds the necessary keyed-HTTP protection, with focused negative tests.

**Strengths**
- The session-gate and keyed-HTTP tests exercise the actual pre-socket boundary (`34-02-PLAN.md:143-150`; `jev_review.py:1410-1431`).

**Concerns**
- **C2-2 — HIGH: URL query credentials can be persisted and printed.** `34-01-PLAN.md:120-123` rejects URL userinfo but permits arbitrary query strings; `34-02-PLAN.md:116` prints the complete saved value. A URL such as `https://host/path?api_key=<secret>` therefore writes and echoes the credential, contrary to the no-key-output boundary.

**Suggestions**
- Define and enforce a credential-free URL contract, including query and fragment handling, before persistence or output; add sentinel tests for both CLI and probe.

**Risk assessment: HIGH** — the new settings interface can disclose a supplied credential.

#### 34-03

**Summary:** The identity and fetch-once logic has useful isolated seams, but the revised failure behavior remains incomplete as described under C1-7.

**Strengths**
- The plan tests same-version fingerprint changes and idle reuse independently (`34-03-PLAN.md:158-166`).

**Concerns**
- **C2-3 — MEDIUM: An unreadable or malformed records file is treated as empty and can be overwritten.** `34-03-PLAN.md:116-118,127` specifies `{}` for unreadable or non-object data, followed by an atomic replacement. A transient read error or malformed existing record is therefore indistinguishable from first use, and a later successful fetch can replace the prior file.

**Suggestions**
- Distinguish missing from unreadable/invalid state; report the latter and avoid replacing it. Test both malformed and permission-error cases.

**Risk assessment: MEDIUM** — learned evidence can be silently lost, though capability cells remain unchanged.

#### 34-04

**Summary:** The two-way override and downstream-output checks implement the locked knob design with minimal caller changes.

**Strengths**
- The plan removes internally forced `GSD_PATH_JEV=1` and pins the fields consumed by fold and goal-prompt (`34-04-PLAN.md:135-145`; `fold_group.py:250-273`; `gp_host.py:517-533`).

**Concerns**
- No additional C2 concern identified.

**Suggestions**
- Keep the source-chain comments next to the assertions so later consumer changes remain visible.

**Risk assessment: LOW** — the planned checks cover the identified callers and precedence.

#### 34-05

**Summary:** Local pending notes preserve the no-fetch answer path, but the partial-failure and unknown-feature gaps remain under C1-10 and C1-11.

**Strengths**
- `note_model` and `note_unknown` separate local observations from later public retrieval (`34-05-PLAN.md:105-112,147`).

**Concerns**
- **C2-4 — HIGH: Identifier filtering does not prove an unknown field name is non-secret.** `34-05-PLAN.md:146-147,181` accepts and persists any matching 64-character identifier from a caller or server. A secret-shaped value used as an unexpected JSON key can satisfy that regex and be written to `unknown_seen`, contrary to the threat row’s assertion that no key or item text enters the record.

**Suggestions**
- Apply the existing secret-shape protections or an equivalent fail-closed filter before persistence, and test a sentinel secret as an unexpected key. Do not log the rejected name.

**Risk assessment: HIGH** — attacker- or caller-controlled field names can enter persistent state.

#### 34-06

**Summary:** The plan preserves the important separation between per-item answers and public fetches; its deadline changes are materially better, but a supported response-model shape is missed.

**Strengths**
- Public fetches now reuse the existing watchdog and bounded reader (`34-06-PLAN.md:115-116`; `jev_review.py:207-230,1342-1368`).

**Concerns**
- **C2-5 — HIGH: A valid new TypeSafe model ID can be silently ignored.** The current response validator accepts `jev-1` as well as dotted IDs (`jev_review.py:830-832`), but `34-05-PLAN.md:105-106` requires at least one dot in `_VERSIONED_ID`. An answer with a new valid ID such as `jev-2` passes the client and is never noted or learned, breaking JEV-12’s new-model trigger.

**Suggestions**
- Share or explicitly align the accepted versioned-ID contract with the response validator, while still excluding aliases. Test a valid undotted version and a genuinely invalid ID.

**Risk assessment: HIGH** — a supported answer can bypass the required model-awareness flow.

#### 34-07

**Summary:** The concise recipe and contract tests make the new behavior discoverable without growing the skill unnecessarily.

**Strengths**
- The plan labels upstream notes as unverified data and preserves the calibration caveat (`34-07-PLAN.md:115-117,294-295`).

**Concerns**
- **C2-6 — MEDIUM: The exact recipe contradicts remote-Laya selection.** The target body says “Without consent, auto uses a loopback laya only” (`34-07-PLAN.md:278`), while the same plan and Plan 02 allow a previously consented off-loopback Laya (`34-07-PLAN.md:273-275`; `34-02-PLAN.md:143-149`). This can lead an agent to misdescribe a usable remote Laya.

**Suggestions**
- State that an *unconsented* off-loopback Laya is unavailable; distinguish recorded consent from a fresh question.

**Risk assessment: MEDIUM** — misleading operational guidance rather than a direct transport failure.

#### 34-08

**Summary:** The guard has substantially better non-vacuity coverage, though C1-15 remains partly open and its execution overlaps another plan.

**Strengths**
- `34-08-PLAN.md:116-128` tests wrapped prose, named repositories, unrelated negation and permitted host-folder references.

**Concerns**
- **C2-7 — HIGH: Parallel wave plans can edit and test the same skill files.** Plans 07 and 08 both run in wave 5 and depend only on Plan 06 (`34-07-PLAN.md:5-6`; `34-08-PLAN.md:5-6`). Plan 07 edits the skill tree, while Plan 08’s guard scans that tree and explicitly instructs its executor to reword offending skill text (`34-08-PLAN.md:123,130`). The guard can inspect an intermediate tree or both executors can edit the same file.

**Suggestions**
- Make Plan 08’s guard task depend on Plan 07 completion, or remove its authority to edit those files and give the orchestrator an explicit conflict-free handoff.

**Risk assessment: HIGH** — the parallel schedule can make a task gate nondeterministic or lose edits.

#### 34-09

**Summary:** The driver’s scoring contract is now concrete, but its fake self-test does not isolate all config inputs and the live fallback paths need stronger checks.

**Strengths**
- The plan validates each spike response against requested IDs and tests the scoring mapping before live use (`34-09-PLAN.md:125,127`; `jev_review.py:510-532`).

**Concerns**
- **C2-8 — HIGH: The self-test can read the real project config.** `34-09-PLAN.md:121,127` runs from the checkout root and replaces HOME/XDG paths, but does not patch the client’s `_cwd()` or change the project layer. The layered reader reads `./.aikit/config.toml` (`config_io.py:262-264,540-558`). If that file exists, the test reads real config and its settings may affect the self-test, violating the explicit test-isolation rule.
- **C2-9 — HIGH: A failed `--calibrate` subprocess is not checked before a successful record is written.** `34-09-PLAN.md:129` checks the `--record` exit code but does not specify checking the subsequent `--calibrate` exit code before parsing output and writing `"run": true`. The actual calibration command can print its proposal and then return 1 on a rewrite failure (`eval_cases.py:199-220`), so the driver can report success despite failure.

**Suggestions**
- Patch `_cwd()` to a newly created scratch project in `selftest`, and test with a hostile checkout project config that must not be read.
- Check the calibration subprocess return code and output shape; record a dated failure without claiming a completed calibration.

**Risk assessment: HIGH** — test isolation and calibration evidence can both fail.

#### 34-10

**Summary:** The frozen-tree and judge-pool requirements are explicit; the phase-wide `make test` remains scheduled in the validation strategy, as the cycle-1 source check found.

**Strengths**
- The plan records the referee order, substitutes and frozen-tree checks (`34-10-PLAN.md:95,136-158`).

**Concerns**
- **C2-10 — MEDIUM: Driver recreation depends on untracked prior-run scratch.** `34-10-PLAN.md:95,105-113` requires `tmp/judge-33/` and describes its recreation by reference to an earlier plan rather than giving this run a checked-in driver or a verified recreation command. If scratch has been cleaned, the orchestrator cannot follow the exact copy step as written.

**Suggestions**
- Specify a reproducible, checked-in source or exact recreation steps and an explicit missing-scratch failure before launching lanes.

**Risk assessment: MEDIUM** — execution depends on transient local artifacts.

##### Status: Issues Found — fix and re-invoke

This was a read-only, targeted source review. I did not execute the plans, the full test suite, live calibration, spike, or judge lanes; the proposed code and tests do not yet exist, so their runtime behavior remains unverified.


---

### Cycle 2 consensus summary

Cycle 2. One reviewer ran (`referee-one`), so there is no cross-reviewer agreement to report and the consensus gate
does not engage. The review cites `file:line` evidence throughout and carries no evidence-quality discount marker. The
orchestrator checked every resolution verdict and every new finding against the revised plans (a059e68) and the source
(tables below), with the same rule as cycle 1: a finding is excluded from the counts only when the source shows it is
wrong or when it asks to change a locked decision; a confirmed finding that does not meet the HIGH bar of the review
brief (gate failure, SPEC or locked-decision break, config loss, secret leak, network or real-HOME test, unsafe
execution) is kept at a lower severity with the reason. All six cycle-1 refutations stand: the reviewer contested none.

#### Agreed Strengths
- (single reviewer) The revisions reuse what exists: `cfg_read_bytes` for the CRLF-safe write, `_remote_url` for the
  key-over-http rule, `_Deadline` with `_exchange`/`_read_body` for the fetch bound, the client's `_laya_url`,
  `_row_probe` and `checked_response` in the live driver, and `JevStub` for the driver's self-test. Eight of the
  fourteen confirmed cycle-1 findings are fully resolved by the reviewer's own reading.

#### Agreed Concerns
- None (one reviewer). The reviewer's priority order: the wave-5 overlap of Plans 07 and 08 (C2-7), the live driver's
  unchecked `--calibrate` exit (C2-9), then the residuals of C1-7, C1-10, C1-11, C1-15 and C1-18.

#### Divergent Views
- None (one reviewer). The orchestrator's source check disagrees with the reviewer on C1-17 (fully resolved), on the
  severity of C2-2 and C2-4, and refutes C2-1, C2-3, C2-5, C2-6, C2-8 and C2-10 (table below).

#### Source check of the cycle-1 resolution verdicts (orchestrator, 2026-11-15)

| # | Reviewer | Orchestrator | Evidence |
|---|----------|--------------|----------|
| C1-2, C1-3, C1-4, C1-5, C1-6, C1-9, C1-13, C1-19 | FULLY | FULLY (agreed) | Revised task text, tests and threat rows as the reviewer cites; spot-checked `config_io.py:332,342,941`, `jev_review.py:114-131,207-230,510-539,673-681`, `tests/test_jev_fast_decision.py:132-310` (JevStub answers noul 0.9 and each choice's first option, so 7 of 8 holds). |
| C1-7 | PARTLY | HIGH resolved; LOW residual open | The HIGH (a failed source recording `no_published_notes` or replacing a good entry on force) is closed: `34-03-PLAN.md:126` returns None when a source failed and no notes were found, tests at `:190`. Residual: with the target notes found in PyPI and the README failing, `fetch_laya_notes`'s errors are dropped (`:126` "notes found in one answering source are enough to record"; `:191` pins status ok and no notice), so D-06's "prints one notice" (`34-CONTEXT.md:60`) is not met for that source. Recording the found notes is right; the notice is missing. |
| C1-10 | PARTLY | HIGH resolved; LOW residual open | Unknown item types and keys and unknown response fields now reach `note_unknown` (`34-06-PLAN.md:157-162`, tests `:152-153`). Refuted part: "an unknown answer primitive fails validation first" is not a skill-unknown primitive: the client only asks types it knows and each checker compares the answer with the asked type (`jev_review.py:397-415,501-502`), so another type is an invalid response to that question. Confirmed part: `_preflight` returns a feature refusal before validation (`jev_review.py:1910-1912`); an unknown-type item that also carries `images` or `assets` (or sits in a payload an explicit row refuses for another item, `:1872-1878`) is refused there and never reaches `_note_unknown_items`, which runs only in the `request_body` except branch (`34-06-PLAN.md:162`). |
| C1-11 | PARTLY | HIGH resolved; LOW residual open | Each content page failing alone stays pending (`34-05-PLAN.md:112,141`). llms.txt failing alone still records from the default URLs by design (`:29,112,141`), which serves the same two content pages, so the record is complete. Residual: the general truth `:28` ("A failed doc fetch keeps every id pending") contradicts `:29` and the `test_each_doc_page_failing_alone` index case; a verifier reading `:28` would fail the plan. |
| C1-15 | PARTLY | HIGH resolved; LOW residual open | Wrapped, named-repository, unrelated-negation and delegate phrasings are now caught (`34-08-PLAN.md:112,116-117,126`). Residual confirmed by tracing `NEGATED_STEP` (`:112`): in "not only install Laya from another repository" the match `not` + ` only` + ` install` removes the verb, so `delegation_problem` (`:117`) passes an affirmative hand-off. |
| C1-17 | PARTLY | FULLY (residual refuted) | The driver no longer resolves or probes on its own (`34-09-PLAN.md:123-124`; acceptance `:145` bans `tomllib` and `urllib.request` in it). The project override, the declined `""` and the off-loopback-without-consent cases live in the client helpers the driver now calls, and those are tested where they are built: `test_url_order_env_project_user_default` (34-01), `test_first_run_question_answered_and_declined`, `test_off_loopback_laya_needs_consent_and_sends_nothing`, `test_session_gate_never_opens_an_off_loopback_laya` (34-02). A driver-level copy of those tests would add nothing. |
| C1-18 | PARTLY | HIGH resolved; LOW residual open | The state-only case is handled (`34-09-PLAN.md:122-123`). Residual confirmed: `_typesafe_key` skips an unusable `JEV_API_KEY_FILE` and falls through to the state file (`jev_review.py:713-723,788-792`), so the real-env label can be `state` while `live_env` keeps the set-but-unusable variable (`34-09-PLAN.md:123`: "when state_key is set and JEV_API_KEY_FILE is not"); under the scratch state the key is hidden again. It fails safe to a recorded "not run" (`:125`). The state-key fake test is not needed: `real_state_key` only reads the client's label. |

#### Source check of the cycle-2 findings (orchestrator, 2026-11-15)

| # | Plan | Finding | Reviewer | Verdict | Evidence |
|---|------|---------|----------|---------|----------|
| C2-1 | 01 | A project-layer value can mask a user-layer `config set`, defeating the asked-once flow | HIGH | REFUTED | The question is asked only when no layer holds the key: `knob` sets `needs_answer` only for a value of None in the layered table (`34-01-PLAN.md:203`), and `laya_url_setting` returns source `default` only when neither project nor user holds `laya_url` (`:204`). A project value never triggers a question whose answer it then masks; a manual `config set` under a project value is D-01's locked "project over user per key" (`34-CONTEXT.md:36`). Not counted. |
| C2-2 | 01, 02 | A URL query can carry a credential that is saved and echoed | HIGH | CONFIRMED, LOW | `valid_url` refuses userinfo but not a query or fragment (`34-01-PLAN.md:120`); `config set` prints the saved value (`34-02-PLAN.md:116`). Not HIGH: the value is the user's own typed answer, and the client drops any query or fragment before use (`_systemone_url`, `jev_review.py:562`). A query or fragment is therefore never useful and refusing it, like userinfo, keeps credential-shaped text out of config.toml. |
| C2-3 | 03 | An unreadable or malformed records file reads as `{}` and is replaced | MEDIUM | REFUTED | Same pattern as the existing, more sensitive consent record (`read_consent`, `jev_review.py:1003-1010`); the records are a cache of public upstream text, so the worst case is one more fetch per key; capability cells live in code and are never touched. Not counted. |
| C2-4 | 05 | A secret-shaped JSON key name can enter `unknown_seen` | HIGH | CONFIRMED in part, LOW | `_UNKNOWN_NAME` (`34-05-PLAN.md:146`) bounds names to a 64-character identifier but does not screen secret shapes, while T-34-42 (`:183`) claims no key enters the record and the probe notice prints the names (`:148`). Not HIGH: it needs a caller or server to send a secret as a JSON key name, and the record is a 0600 file in the user's own state. The skill already ships a sibling secret-shape detector (`skills/jev-fast-decision/scripts/secret_shapes.py`, used by `jev_ladder.py:55-78`). |
| C2-5 | 05, 06 | `_VERSIONED_ID` needs a dot, so an undotted id such as `jev-2` that `_JEV_RESPONSE` accepts is never noted | HIGH | REFUTED | Every documented TypeSafe id is dotted (`jev-1.13.0`, `jev-1.14.0`; aliases `jev-latest`, `jev-preview`: RESEARCH's trimmed `models.md`), and the client's own comment says a remote answer names the versioned id (`jev_review.py:830-831`). Treating an undotted id as an alias follows SPEC R4 adjacency (`34-SPEC.md:155`) and fails toward recording nothing. Not counted. |
| C2-6 | 07 | "Without consent, auto uses a loopback laya only" contradicts a consented off-loopback Laya | MEDIUM | REFUTED | The sentence (`34-07-PLAN.md:271`) is conditional on no consent; with a record, the laya bullet two lines up says "consent only off loopback" (`:268`). It matches Plan 02's rule. Not counted. |
| C2-7 | 07, 08 | Plans 07 and 08 run in the same wave; 08's guard scans and may reword the skill tree 07 edits | HIGH | CONFIRMED | Both `wave: 5`, `depends_on: [34-06]` (`34-07-PLAN.md:5-6`, `34-08-PLAN.md:5-6`); `parallelization: true` (`.planning/config.json:4`). Plan 07 edits `skills/jev-fast-decision/SKILL.md`, `reference.md`, `backends/*.md` and evals (`34-07-PLAN.md:8-14`); Plan 08's gate `test_skill_tree_passes_the_guard` scans that tree (`34-08-PLAN.md:123`) and its step 2 rewords skill text (`:130`) in files outside its own `files_modified` (`:8-17`). Its gate can see a half-edited tree, and both executors can edit the same file. Impact note: the fix is one frontmatter change (Plan 08 depends on 07, wave 6; Plan 09 already depends on both). |
| C2-8 | 09 | `live.py selftest` can read the checkout's `./.aikit/config.toml` | HIGH | REFUTED | That file is the checkout's project layer, not the real HOME, and this checkout has none (`.aikit/` holds `brief/`, `flow.json`, `review-spec.toml`). Even when present, no `[jev]` key changes the TypeSafe-only self-test: `GSD_PATH_JEV=1` wins over `enabled` (`34-01-PLAN.md:203`), the typesafe row reads no `[jev]` key, and a laya row moved off loopback only needs consent for itself. Not counted. |
| C2-9 | 09 | The driver writes `"run": true` without checking the `--calibrate` exit code | HIGH | CONFIRMED | `34-09-PLAN.md:129` checks the `--record` rc but not the `--calibrate` one; `_run_calibration` prints the proposal and then returns 1 on a missing results file or a refused rewrite (`eval_cases.py:199-213`), so `calibration.json` would claim a completed run. Impact note: orchestrator scratch, one rc check, and `rewrote_min_confidence` would read false; T-34-33's "never claimed" rule is what breaks. |
| C2-10 | 10 | The driver copy depends on untracked `tmp/judge-33/` scratch | MEDIUM | REFUTED | The plan names the files, says they are present on this machine and gives the recreate path (33-12 Task 1) (`34-10-PLAN.md:95`); all ten are present (`tmp/judge-33/` listing, 2026-11-15); `copy_drivers.py` reads each source and stops on a missing one before any lane (`:112`). Not counted. |

#### Current HIGH Concerns (cycle 2)

Single reviewer, so the consensus gate is skipped. 2 open, both confirmed against the plans and source; every cycle-1
HIGH is resolved (residuals are listed below as LOW):
- C2-7 (Plans 07, 08): both in wave 5 on `depends_on: [34-06]`; Plan 08's skill-tree guard and its rewording step race
  Plan 07's edits of the same skill files. Change needed: Plan 08 `depends_on: [34-06, 34-07]`, `wave: 6` (and Plan 09
  `wave: 7`, Plan 10 `wave: 8`), or move the rewording authority to the orchestrator.
- C2-9 (Plan 09): `live.py calibrate` records `"run": true` without checking `eval_cases.py --calibrate`'s exit code.
  Change needed: a non-zero rc writes `{"run": false, "date", "host", "reason": "eval_cases --calibrate exited <rc>"}`
  with stderr saved to `RUN/calibrate-stderr.txt`.

#### Current Actionable Non-HIGH Concerns (cycle 2)

7 open (all LOW), none yet in a plan:
- C1-7 residual (Plan 03): when notes are found but another source failed, keep the record and set
  `out["notice"]` naming the failed source (`fetch_laya_notes` errors); pin it in `test_readme_failing_alone_keeps_found_notes`.
- C1-10 residual (Plan 06): call `_note_unknown_items(payload)` also before `_preflight` returns a feature refusal
  (`stopped`), and add a test with an unknown-type item that carries `images`.
- C1-11 residual (Plan 05): reword the truth "A failed doc fetch keeps every id pending" to name the content pages
  (`changelog.md` or `models.md`), matching the llms.txt fallback.
- C1-15 residual (Plan 08): keep `not only` / `not just` out of `NEGATED_STEP` (for example `not(?!\s+(?:only|just)\b)`)
  and add "Do not only install Laya from another repository." to `test_delegation_rule_reads_sentences`.
- C1-18 residual (Plan 09): `live_env` sets `JEV_API_KEY_FILE=state_key` whenever `real_state_key` returned a path,
  replacing a set-but-unusable value.
- C2-2 (Plan 01): `valid_url` also refuses a non-empty query or fragment; add the case to
  `test_set_refuses_bad_values_and_writes_nothing`.
- C2-4 (Plans 05/06): drop unknown names whose identifier part matches the sibling `secret_shapes.py` detector
  (loaded with `_load_sibling`, as `jev_ladder.py` does), with a sentinel test; or narrow T-34-42's claim to what the
  regex bounds.

C1-1, C1-8, C1-12, C1-14, C1-16 and C1-20 stay refuted (not contested); C2-1, C2-3, C2-5, C2-6, C2-8 and C2-10 are
refuted and not counted.

#### Verification coverage (source-grounding pass, cycle 2)

- Symbol and path sweep: `tmp/auto/r325/conv-34/review-c2/ground.py` (git grep outside `.planning/`, plus path and
  line-range checks) over the ten revised plans, then `crossplan.py` for every unresolved symbol. Every unresolved path
  or symbol is one a phase 34 plan creates (the cycle-1 set plus the revisions' `_needs_consent`, `insecure_url`,
  `_laya_decision`, `fetch_laya_notes`, `note_unknown`, `_unknown_response_names`, `_unknown_item_names`,
  `_note_unknown_items`, the new test names and the 34-09 driver helpers) or a stdlib name (`ast.get_docstring`). No
  plan cites a missing existing symbol and no cited line range runs past its file.
- Findings: each checked by reading the cited plan lines and source (`jev_review.py:114-131,207-230,343-370,397-415,
  498-539,556-562,565-621,673-681,701-723,773-795,828-872,910-945,1003-1010,1861-1925`, `eval_cases.py:190-225`,
  `config_io.py:332,342,941`, `tests/test_jev_fast_decision.py:132-311`, `jev_ladder.py:55-78`,
  `skills/jev-fast-decision/scripts/` listing, `.aikit/` listing, `tmp/judge-33/` listing, `.planning/config.json:4`,
  `34-CONTEXT.md:33-45,60`, `34-SPEC.md:72-77,155`, plans `34-01:115-125,198-206`, `34-02:112-120,149-166,218-223`,
  `34-03:112-127,155-161,186-194`, `34-05:25-30,100-115,140-150,176-184`, `34-06:106-133,149-162,189-208`,
  `34-07:1-16,268-282`, `34-08:1-18,108-130`, `34-09:5-14,108-145`, `34-10:5-13,90-115`);
  `check_index_coverage` reported no recorded issue for the five source files relied on. Cycle-1 verdicts: 8 fully
  resolved as the reviewer said, C1-17 fully resolved against the reviewer's PARTLY, 5 HIGHs resolved with a LOW
  residual each; the 6 refutations uncontested. Cycle-2 findings: 10 raised, 2 confirmed HIGH (C2-7, C2-9), 2 confirmed
  and kept as LOW (C2-2, C2-4), 6 refuted (C2-1, C2-3, C2-5, C2-6, C2-8, C2-10).
- Not run: the plans themselves, the test suite, the live calibration or spike, any judge lane.

---

## Cycle 1 record (b0485b0)

Review cycle 1, over the ten plans of commit 0ca123a. Reviewer instance `referee-one` (`review.default_reviewers`)
ran through the opencode lane (`review-lane invoke --slug opencode --model router-env/my-referee-one --as referee-one`),
with `AI_KIT_REFUSE_REAL_HOME=1`, its own TMPDIR and its own process group. Lane result:
`{"slug":"opencode","ok":true,"stubbed":false,"model":{"value":"router-env/my-referee-one","source":"pinned"}}`;
exit 0; elapsed 176 s (16:33:34 to 16:36:30 local); stderr empty, so no AIKIT-XAI status line (this lane does not go
through `cross-ai.mjs`); one attempt. The prompt (376 KB) carried PROJECT.md (first 80 lines), the ROADMAP section, the
jev requirements, SPEC, CONTEXT, the locked-decisions note (D-01..D-15 and RESEARCH's six Resolved Open Questions
locked; haiku-at-high executors; tests never touch the network or the real HOME; the live calibration and the judge
loop orchestrator-driven by design; HIGH reserved for gate failures, SPEC or locked-decision breaks, config loss,
secret leaks, network or real-HOME tests, or unsafe execution), RESEARCH, PATTERNS, VALIDATION, all ten plans and the
ponytail-lens focus line. Plan coverage: all ten ids have their own section.

### OpenCode Review (referee-one)

Using the plan-review checklist to check all ten plans against the locked decisions and the current source. I’ll keep this review read-only.
##### Phase 34 plan review

##### Document type

GSD · implementation plans. Reviewed against the supplied SPEC and locked decisions and targeted repository source reads. The ten plan IDs below are covered in the manifest order.

#### 34-01

**Summary:** The parity-tested reuse of Phase 33’s reader and splicer is appropriate, but the proposed write path does not preserve concurrent or CRLF-formatted config safely.

**Strengths**
- Reuses the existing parser, splicer and atomic publisher rather than introducing a separate TOML writer: `skills/ai-kit-spec-review/ai_kit_spec/toml_splice.py:429` and `:780`.

**Concerns**
- **C1-1 — HIGH: Atomic replacement does not prevent lost config updates.** `34-01-PLAN.md:122-129` specifies an unlocked read–modify–replace. Two writers changing *different* keys—or another ai-kit writer changing an unrelated table—can both read the old document and publish valid but conflicting replacements. `cache.py:27-46` provides atomic replacement, not transaction isolation. The same-key test can pass while a user’s other change is lost.
- **C1-2 — HIGH: The prescribed text read can change unrelated bytes.** The plan promises byte preservation at `34-01-PLAN.md:122`, but reading UTF-8 in ordinary text mode normalizes CRLF to LF before the splicer sees it. The splicer deliberately detects existing newline style (`toml_splice.py:105-110`); the proposed caller can defeat that preservation.

**Suggestions**
- Coordinate the complete read–splice–publish transaction with other relevant config writers, or detect concurrent changes and fail/retry. Add deterministic concurrent **different-key** and CRLF byte-preservation tests.

**Risk assessment: HIGH** — valid config can silently lose unrelated changes or formatting.

#### 34-02

**Summary:** The plan identifies the cloned-project redirection threat and reuses existing consent machinery, but the exact reuse weakens the locked host-binding decision and introduces a credential-transport risk.

**Strengths**
- It places consent checks before the send and includes an invariant test over backend rows (`34-02-PLAN.md:139-149`; current `_send` checks before opening a socket at `jev_review.py:1410-1424`).

**Concerns**
- **C1-3 — HIGH: The existing session gate bypasses host-bound consent.** `34-02-PLAN.md:149` changes `allowed_remotes` to include off-loopback Laya, but retains its existing `_gate_open` alternative. `JEV_ALLOW_REMOTE=1` or a named row grants by backend name, not host (`jev_review.py:967-979,1063-1067`). Thus a changed project URL can receive item data without the required record for its new host.
- **C1-4 — HIGH: A configured remote HTTP Laya can receive a bearer key in cleartext.** The plan accepts HTTP at any address and deliberately leaves Laya on the local exchange path (`34-02-PLAN.md:113,149`). Existing Laya reads `LAYA_API_KEY` (`jev_review.py:585-587`), and `_send` puts any key in `Authorization` (`:1429-1438`). Host consent alone does not protect that key in transit.
- **C1-5 — HIGH: The tracer misuses its existing test helper.** `34-02-PLAN.md:117` treats `run_probe()` as the report; it actually returns `(exit_code, report)` (`tests/test_jev_fast_decision.py:368-371`). The exact tracer as written cannot meet its task gate.

**Suggestions**
- Require the locked host-bound grant for off-loopback Laya even when the legacy session gate is set; test a grant followed by a host change.
- Preserve support for configured addresses while refusing to send a bearer key over non-loopback HTTP; test that refusal before any socket.
- Unpack the tracer’s probe result explicitly.

**Risk assessment: HIGH** — potential disclosure of item context and credentials.

#### 34-03

**Summary:** Separating learning logic behind an injected fetcher is a useful test seam, but the identity and failure algorithms do not fully implement the locked cache behavior.

**Strengths**
- Keeps public fetching out of the decision path and retains upstream facts as unverified (`34-03-PLAN.md:50,124-125`).

**Concerns**
- **C1-6 — HIGH: A known version masks a changed fingerprint, and idle can fetch prematurely.** `34-03-PLAN.md:121,125` keys a known server by version and returns `known` without comparing its stored fingerprint. A route or checkpoint revision change under the same version therefore does not invalidate the record, contrary to SPEC R2/R3. Also, when a configured version exists, the key is non-null even if idle has no matching fingerprint, so it fetches instead of returning `pending_idle` as required by the resolved idle decision.
- **C1-7 — HIGH: Partial source failures can permanently replace a good record.** `34-03-PLAN.md:124-125` treats one successful source as success even if the other fails. For example, a failed version-specific PyPI request plus a latest-only README can write `no_published_notes`, including during force refresh, and suppress retry for that key. This contradicts the required failed-fetch preservation.
- **C1-8 — MEDIUM: Re-reading before replacement is not concurrency control.** `34-03-PLAN.md:125` claims another writer’s keys survive, but two writers can both re-read before either replaces the file. The same-key test at `:190` does not demonstrate different-key preservation.

**Suggestions**
- Compare fingerprint as well as version, implement the idle branch before any fetch, and test each with a configured version.
- Define incomplete-source status and preserve a prior successful record on partial failure; test each source failing independently.
- Serialize record updates or use a conflict-detecting retry; test two distinct keys.

**Risk assessment: HIGH** — stale capability data can be reported as current, and failed refreshes can erase useful evidence.

#### 34-04

**Summary:** The true two-way session override and caller changes reflect the locked decision, with useful fail-closed coverage.

**Strengths**
- Explicitly removes forced `GSD_PATH_JEV=1` from the ladder and hook paths; the current forced assignments are visible in `jev_ladder.py:433-446` and `tools/hooks/precompact_core.py:115-127`.

**Concerns**
- **C1-9 — MEDIUM: Consumer reach is asserted more broadly than it is tested.** `34-04-PLAN.md:180-191` verifies the ladder, judge loop and hooks, while its success criterion says *each consumer*. The supplied research also names commit-fold and goal-prompt consumers; no concrete tests for those paths are assigned. The current ladder has its own no-answer behavior (`jev_ladder.py:575-604`), but that does not itself prove the downstream skills’ outcomes.

**Suggestions**
- Name the exact commit-fold, goal-prompt and spec-discuss test locations and assert their observable knob-off behavior, or document source-verified evidence that they only consume the already-tested ladder result.

**Risk assessment: MEDIUM** — core gating is well scoped; full “every skill” reach remains unproved.

#### 34-05

**Summary:** The local pending-note approach respects the no-fetch-on-answer-path requirement, but the plan does not cover all JEV-12 triggers or reliable doc-flow failure handling.

**Strengths**
- Separates the local note from public retrieval (`34-05-PLAN.md:103-110`), consistent with the existing response-validation and answer flow in `jev_review.py:466-473,510-532`.

**Concerns**
- **C1-10 — HIGH: Unknown primitive or option is not a trigger.** `34-05-PLAN.md:104-110` creates pending work only for a new model ID. `new_primitives` is discovered *after* a fetch already triggered by an ID; no path records an unknown primitive or option encountered while the model ID remains known. JEV-12 explicitly requires both trigger classes.
- **C1-11 — HIGH: Partial documentation failures are recorded as complete.** `34-05-PLAN.md:106,110` marks IDs `recorded` if either changelog or models page succeeds, even when the other or the index failed. Subsequent probes do not retry known IDs, so missing changes or feature information can remain permanently absent despite the failure.

**Suggestions**
- Define a bounded local pending signal for unknown primitives/options and process it on the next probe, with no answer-path fetch.
- Keep an incomplete doc flow pending, report which source failed, and test failures of each of the three pages separately.

**Risk assessment: HIGH** — the planned behavior misses an explicit requirement and can silently freeze incomplete records.

#### 34-06

**Summary:** The end-to-end wiring preserves the important separation between answers and public learning, but its tests and network deadlines do not enforce all stated boundaries.

**Strengths**
- The proposed answer-path test explicitly makes the fetch seam fail if called (`34-06-PLAN.md:147-153`).
- Reuses the existing no-redirect exchange and bounded body reader (`jev_review.py:207-230,1342-1368`).

**Concerns**
- **C1-12 — HIGH: Test isolation patches only one imported client instance.** `34-06-PLAN.md:120` patches `JR._public_get` in `_ClientCase`, but the suite also loads `jev_review.py` independently through `eval_cases.py` (`eval_cases.py:39-44`) and launches real client subprocesses (`tests/test_jev_fast_decision.py:2550,2759,3677`). Those instances do not inherit the in-process mock. A reachable fake Laya with valid identity can cause a test to fetch public endpoints, violating the explicit no-network test rule.
- **C1-13 — HIGH: A five-second socket timeout is not a five-second total fetch bound.** The planned `_public_get` passes `None` as the deadline (`34-06-PLAN.md:113-114`). The existing watchdog is armed only when a deadline exists (`jev_review.py:207-230`), and `_read_body` checks elapsed time only with a deadline (`:1342-1367`). A trickling upstream can keep a probe alive far beyond five seconds.

**Suggestions**
- Enforce network isolation across independently imported clients and subprocesses, not only `JR`; add a subprocess regression using local fakes and a tripwire for external hosts.
- Pass a real per-fetch deadline through the exchange and body reader; test a trickle response.

**Risk assessment: HIGH** — tests can reach the network, and a public probe can hang well beyond its promised bound.

#### 34-07

**Summary:** The concise skill recipe and doc-contract tests are valuable, but the exact target text contains a misleading credential requirement.

**Strengths**
- Adds an explicit calibration caveat and treats upstream notes as data rather than instructions (`34-07-PLAN.md:115-117,253-258`).
- Keeps detailed settings and records guidance in `reference.md`, avoiding unnecessary SKILL.md growth.

**Concerns**
- **C1-14 — MEDIUM: The target recipe says TypeSafe needs an environment key even when a permitted file key works.** `34-07-PLAN.md:253` says `TYPESAFE_API_KEY` is needed in the environment. Existing resolution explicitly supports other environment names and three file locations (`jev_review.py:773-795`), and JEV-01 retains the home-file fallback. An agent following the short recipe may incorrectly report an otherwise usable backend as unavailable.

**Suggestions**
- Describe TypeSafe as requiring a resolved key, with the environment preferred, and point to the documented source order. Add a doc-contract case covering file-key wording.

**Risk assessment: MEDIUM** — misleading agent guidance, rather than a direct transport or config failure.

#### 34-08

**Summary:** The guard and documentation updates are appropriate phase work, but the proposed pattern matcher does not enforce its claimed delegation prohibition.

**Strengths**
- Includes non-vacuity tests and allows legitimate host-folder references (`34-08-PLAN.md:111-123`).

**Concerns**
- **C1-15 — HIGH: The guard misses ordinary delegation phrasing.** `34-08-PLAN.md:111-116` requires install/upgrade, subject and repository to appear on the *same line*, and `ELSEWHERE` recognizes only a few repository phrases. “Ask the infrastructure repository to upgrade Laya” or a wrapped instruction can pass. A line containing “not” anywhere also suppresses a violation. This falls short of D-13’s guard against delegation to another repository.
- **C1-16 — MEDIUM: “Fact-only” is asserted rather than checked against judge scope.** The plan changes curated-config’s operational instruction at `34-08-PLAN.md:160`, while `34-10-PLAN.md:24-25` excludes it from judging. The existing skill explicitly instructs the agent about session setup (`skills/ai-kit-gsd-curated-config/SKILL.md`, referenced by the plan at `34-08-PLAN.md:147`). The plan needs an explicit, reproducible classification against the project’s material-change rule rather than assuming any one-sentence behavior change is fact-only.

**Suggestions**
- Add adversarial non-vacuity fixtures for wrapped instructions, named repositories, and unrelated negation; choose a bounded rule that detects those cases without banning legitimate host text.
- Record the basis for the curated-config classification and include it in the judge loop if the change is material under JDG-04.

**Risk assessment: HIGH** — the required guard can pass prohibited delegation steps.

#### 34-09

**Summary:** Separating live measurements from fake-backed tests is sensible, but the live driver’s specified behavior can bypass consent, measure the wrong endpoint, and fail before producing its required records.

**Strengths**
- Records a dated fallback rather than inventing calibration results when live Laya is unavailable (`34-09-PLAN.md:135-155`).
- The existing calibration script already has a bounded, AST-targeted threshold rewrite (`eval_cases.py:117-173,199-220`).

**Concerns**
- **C1-17 — HIGH: The live health check opens a remote socket before consent and can select the wrong Laya.** `34-09-PLAN.md:112` directly GETs `/health` before the client’s host-bound gate and resolves only environment and the **user** config; it ignores the project override and treats an explicit empty URL as absent. This can contact a host without its required grant or calibrate the default/user server instead of the configured project choice. The client’s existing probe deliberately gates before a socket (`jev_review.py:1170-1188`).
- **C1-18 — HIGH: Scratch state hides a valid TypeSafe state-file key.** The spike sets `XDG_STATE_HOME` to scratch (`34-09-PLAN.md:112,115`), but the actual key resolver reads `${XDG_STATE_HOME}/typesafe/api_key` (`jev_review.py:773-793`). A user with valid consent and a key only in that supported location is incorrectly reported unavailable, so the required comparison is not run.
- **C1-19 — HIGH: The spike leaves response parsing and scoring underspecified.** `34-09-PLAN.md:115` asks the orchestrator to “score the first item” for a merged request containing eight answers, without defining extraction of all response `answers`, validation, or mapping them back to eight expected IDs. The existing protocol returns an answers map and validates it against requested IDs (`jev_review.py:476-484,510-532`). The prescribed driver cannot reliably produce the promised comparable `correct/n=8` result without inventing material behavior.

**Suggestions**
- Resolve the address through the actual layered client and apply its consent gate before any health request; test project override, declined URL and remote-no-consent cases with fakes.
- Read the supported state-file credential without copying or printing it and without redirecting writes to real state; test the state-key-only case.
- Specify exact response validation, ID mapping, errors and scoring for both request shapes, and run the driver against a fake server before live use.

**Risk assessment: HIGH** — unsafe network access and invalid or missing live evidence are possible.

#### 34-10

**Summary:** The frozen-tree discipline, configured referee pool and three-round cap are sound, but the phase’s full verification gate is not scheduled.

**Strengths**
- The plan specifies no native judge, recorded substitutes and a frozen tree while lanes run (`34-10-PLAN.md:78,95,137-155`).
- Reuses the existing judge-record checks rather than editing verdicts by hand (`tmp/judge-33/check.py:33-51`).

**Concerns**
- **C1-20 — HIGH: No plan actually runs the phase’s required full test gate.** `34-10-PLAN.md:78` explicitly runs no `make test`; Plan 08 runs only `make test-unit` (`34-08-PLAN.md:193-205`), and Plan 09 changes code and skill docs afterward. The SPEC’s acceptance requires `make test`, which includes integration, e2e, installer and architecture tiers under `AGENTS.md`. A green unit tier and judge check cannot establish that gate.

**Suggestions**
- Add an orchestrator-owned `make test` after the last implementation/fix round and before phase verification, with its result recorded. Keep the judge tree frozen while lanes run.

**Risk assessment: HIGH** — the phase can be marked ready without its own full acceptance gate.

##### Status: Issues Found — fix and re-invoke

All 10 plans received a section. This was a targeted, read-only review rather than an exhaustive execution of every proposed test or live workflow; the HIGH findings above should be resolved before execution.



---

### Cycle 1 consensus summary

One reviewer ran (`referee-one`), so there is no cross-reviewer agreement to report and the consensus gate does not
engage. The review cites `file:line` evidence throughout and carries no evidence-quality discount marker. The
orchestrator checked each finding against the plans and the source (table below). A finding is excluded from the
counts only when the source shows it is wrong or when it asks to change a locked SPEC edge; every confirmed HIGH keeps
the reviewer's severity, with an impact note where the orchestrator sees a narrower blast radius.

#### Agreed Strengths
- (single reviewer) The plans reuse the Phase 33 reader, splicer and atomic publisher through a parity-tested copy,
  reuse the consent record (`record_consent` / `_row_host`) for an off-loopback Laya, keep public fetching behind an
  injected fetch seam and off the answer path, keep upstream facts unverified, and give 34-10 a frozen tree, the
  configured referee pool and a three-round cap.

#### Agreed Concerns
- None (one reviewer). The reviewer's priority order: consent and credential transport for an off-loopback Laya
  (C1-3, C1-4), record identity and partial-failure handling (C1-6, C1-7, C1-11), the missing primitive/option trigger
  (C1-10), the delegation guard's reach (C1-15), and the live driver's address, key and scoring (C1-17..C1-19).

#### Divergent Views
- None (one reviewer).

#### Source check of the findings (orchestrator, 2026-11-15)

| # | Plan | Finding | Severity | Verdict | Evidence |
|---|------|---------|----------|---------|----------|
| C1-1 | 01 | `config_set` read-modify-replace without a lock can lose a concurrent different-key write | HIGH | REFUTED (locked SPEC edge) | `34-SPEC.md:148` (R1 concurrency row) accepts saving "through Phase 33's atomic writer; two sessions asking at once keep one answer"; Phase 33's own writer has the same shape (`config_io.py:941-949`, D-25 no lock). A lost first-run answer is asked again by the next probe (`needs_answer`); nothing is corrupted. Not counted. |
| C1-2 | 01 | Reading "the file's UTF-8 text" normalizes CRLF, so the splicer's newline detection is defeated | HIGH | CONFIRMED | `34-01-PLAN.md:122` says "text = the file's UTF-8 text" and the copied set (`:251`) has no `cfg_read_bytes`; text-mode reads translate `\r\n`, so `_newline` (`toml_splice.py:109-110`) sees LF and `publish` rewrites every line ending. Phase 33 reads bytes and decodes (`config_io.py:944-948`). Impact note: values and comments survive; the file's newline style does not. |
| C1-3 | 02 | The session gate `JEV_ALLOW_REMOTE` still grants an off-loopback Laya by name, bypassing host-bound consent | HIGH | CONFIRMED | `34-02-PLAN.md:149` swaps `row["remote"]` for `_needs_consent(row)` but keeps `_gate_open(row["name"]) or record_consent(row)` in `allowed_remotes` (`jev_review.py:1063-1067`); `_gate_open` grants every remote on `JEV_ALLOW_REMOTE=1` (`:976-978`). The Laya URL can come from a project file, so a cloned repo plus a session that set `JEV_ALLOW_REMOTE=1` for TypeSafe (as 34-02's own behavior line `:144` does) sends items to the new host, against Resolved Open Question 2 ("requires the existing consent record bound to that host"). |
| C1-4 | 02 | An off-loopback http Laya would receive `LAYA_API_KEY` in cleartext | HIGH | CONFIRMED (needs `LAYA_API_KEY` set) | `34-02-PLAN.md:149` leaves `_row_probe`'s remote-only URL check as is, so `_remote_url`'s https rule (`jev_review.py:673-681`, T-21.1-07: "a remote row's key travels only over https") never applies to Laya; `_send` attaches any key as `Authorization: Bearer` (`:1430-1431`); `_laya_key` reads `LAYA_API_KEY` (`:585-587`). |
| C1-5 | 02 | The tracer treats `run_probe()` as the report, but it returns `(code, report)` | HIGH | REFUTED as HIGH; kept as a LOW wording fix | `tests/test_jev_fast_decision.py:368-371` returns the tuple. `34-02-PLAN.md:117` describes outcomes, not code, and the executor imports the helper whose docstring and every existing caller unpack the tuple; the same wording is in `34-04-PLAN.md:113` and `34-06-PLAN.md:124`. Counted as actionable LOW: write `code, report = self.run_probe()` once in each. |
| C1-6 | 03 | A known version masks a changed fingerprint; idle with a configured version can fetch | HIGH | CONFIRMED | `34-03-PLAN.md:121,125` key by version and return `known` without comparing the stored fingerprint; `34-SPEC.md:149` (R2 adjacency): "Same version, different route list or revision: a new fingerprint, so R3 treats it as unknown", and `:128`. |
| C1-7 | 03 | A partial source failure can write `no_published_notes` and suppress retry, even overwrite a good entry on force | HIGH | CONFIRMED | `34-03-PLAN.md:124` succeeds with any one source; the README holds only the latest release's section (`34-RESEARCH.md:332`), so a failed version-specific PyPI fetch plus a README read gives `no_published_notes`, recorded under the key (`:125`) and `known` thereafter; with `force` it replaces a good entry, against D-06 ("A failed fetch keeps the previous entry"). |
| C1-8 | 03 | The re-read before replace is not concurrency control | MEDIUM | REFUTED (locked SPEC edge) | `34-SPEC.md:154` (R3 concurrency row): "a parallel fetch for the same key is harmless (same content, last write wins)"; a lost other key is fetched once more on the next probe. Not counted. |
| C1-9 | 04 | "Each consumer" is asserted, but commit-fold and goal-prompt have no knob-off test | MEDIUM | CONFIRMED (evidence gap only) | `fold_group.py:250-256` runs the client's `ladder`; `gp_host.py:497-514` runs `detect` and reads `backends` (`:517-532`); 34-04 Task 2 tests both (`34-04-PLAN.md:35,141`: ladder items `own_reasoning`, detect `status disabled` with `backends {}`), which these consumers read as "no answer" and "no usable backend". The plan should record this chain (RESEARCH `:466` left it unverified). Actionable. |
| C1-10 | 05 | An unknown primitive or option is not a trigger | HIGH | CONFIRMED | `34-SPEC.md:76` (R4): "a new id, or a primitive or option the skill does not know, triggers the same unknown → fetch once step"; `34-05-PLAN.md:104-110` creates pending work only for a new model id (`new_primitives` is computed after a fetch). |
| C1-11 | 05 | A partial doc-flow failure is recorded as complete | HIGH | CONFIRMED | `34-05-PLAN.md:110` fails only when neither changelog nor models was fetched; otherwise targets become `recorded` (never retried), so a missing models page freezes `primitives_documented == []`; `force` adds only the latest id. |
| C1-12 | 06 | Patching `JR._public_get` does not cover independently loaded clients and subprocesses | HIGH | REFUTED (latent only) | A fetch needs a usable Laya with a version or fingerprint key, or a pending TypeSafe id. The subprocess tests point at closed ports or run `detect` (`tests/test_jev_fast_decision.py:2546-2552,2756-2758,3674-3679`) in scratch state; `eval_cases.py:39-44` runs the answer path, which never fetches (34-06's answer-path rule). No current or planned test reaches the fetch outside the patched module. Not counted. |
| C1-13 | 06 | A 5-second socket timeout is not a 5-second total bound | HIGH | CONFIRMED | `34-06-PLAN.md:113-114` passes no deadline to `_exchange`/`_read_body`; the watchdog arms only with a deadline (`jev_review.py:218-222`) and `_read_body` checks time only with one (`:1366`), so a trickling server holds the probe until the size cap. Impact note: the targets are fixed public hosts and only `--probe`/`--check-updates` fetch (hooks never do). |
| C1-14 | 07 | The recipe says TypeSafe needs `TYPESAFE_API_KEY` in the environment though file keys work | MEDIUM | REFUTED | Today's SKILL.md already says this (`skills/jev-fast-decision/SKILL.md:17`); the env is the documented path and the files are a transitional fallback (`jev_review.py:773-779`); usability comes from the probe, not the recipe. Not counted. |
| C1-15 | 08 | The delegation guard misses ordinary phrasing and any `not` on the line suppresses it | HIGH | CONFIRMED | `34-08-PLAN.md:111,115`: `ELSEWHERE` matches only `llm-env`, `another repo*`, `other repo*` on the same line as STEP and SUBJECT, and `NEGATION` anywhere on the line clears it, so "Ask the infrastructure repository to upgrade Laya" passes; D-13 asks the guard to fail on any step that hands the install or upgrade to another repo. |
| C1-16 | 08 | curated-config's one-sentence change is called fact-only without a check against the judge rule | MEDIUM | REFUTED | The classification and its basis are recorded in `34-10-PLAN.md:25` (one sentence about the session gate, a stale-digest note), following the Phase 33 fact-only precedent; `judged.py` checks the fact-only set (`:24`). Not counted. |
| C1-17 | 09 | The live driver resolves the address itself (no project layer, `""` read as absent) and GETs `/health` before consent | HIGH | CONFIRMED | `34-09-PLAN.md:112` `laya_url()` reads env, then the user file only, and skips an empty string, while 34-01 already provides `laya_url_setting(cwd, env)` with the project layer and the declined answer (`34-01-PLAN.md:202`). Impact note: latent in this checkout (no `.aikit/config.toml`), and the GET carries no item; the fix is to reuse `laya_url_setting` and record "declined" for `""`. |
| C1-18 | 09 | The scratch `XDG_STATE_HOME` hides a TypeSafe key kept in the state file | HIGH | CONFIRMED | `34-09-PLAN.md:112,115` set `XDG_STATE_HOME=STATE`; `_typesafe_key` reads `${XDG_STATE_HOME}/typesafe/api_key` (`jev_review.py:781,792`). Impact note: it fails safe to a recorded "not run"; passing `JEV_API_KEY_FILE` for an existing real state key keeps the scratch log. |
| C1-19 | 09 | The spike leaves response parsing, id mapping and scoring underspecified | HIGH | CONFIRMED (in part) | "score the first item" (`34-09-PLAN.md:115`) means the first element of `_send`'s tuple, not the first answer; but the eight merged items get no ids, the mapping of the `answers` map back to the expected values is not given, and the raw answer shape is assumed (`answer["noul"]`) where the client validates through `checked_response` (`jev_review.py:509-532`), which the driver could reuse. |
| C1-20 | 10 | No plan runs the full `make test` gate | HIGH | REFUTED | The full gate is scheduled at phase level: `34-VALIDATION.md:34` ("Before `/gsd-verify-work`: `make test` green") and `34-RESEARCH.md:430`, run by the phase-end verification; `34-SPEC.md:135` is a phase acceptance item, not a plan's. Not counted. |

#### Current HIGH Concerns (cycle 1)

Single reviewer, so the consensus gate is skipped. 12 open, all confirmed against the plans and source:
- C1-2 (Plan 01): `config_set` reads text mode, so a CRLF config.toml is rewritten with LF endings.
- C1-3 (Plan 02): `JEV_ALLOW_REMOTE` still grants an off-loopback Laya without a host-bound record.
- C1-4 (Plan 02): an off-loopback http Laya would get `LAYA_API_KEY` in cleartext (the https rule is skipped).
- C1-6 (Plan 03): a known version masks a changed fingerprint (SPEC R2 adjacency); idle handling with a configured version.
- C1-7 (Plan 03): a partial Laya notes fetch is recorded as `no_published_notes` and can overwrite a good entry.
- C1-10 (Plan 05): an unknown primitive or option never triggers the doc flow (SPEC R4).
- C1-11 (Plan 05): a partial TypeSafe doc fetch is recorded as complete and never retried.
- C1-13 (Plan 06): public fetches have no total deadline (trickling server).
- C1-15 (Plan 08): the delegation guard misses ordinary phrasing and over-applies negation.
- C1-17 (Plan 09): the live driver re-implements the address order (no project layer, `""` read as absent).
- C1-18 (Plan 09): the spike's scratch state hides a state-file TypeSafe key.
- C1-19 (Plan 09): the spike's ids, answer mapping and scoring are unspecified.

#### Current Actionable Non-HIGH Concerns (cycle 1)

2 open, not yet in a plan: C1-5 (Plans 02, 04, 06) write `code, report = self.run_probe()` where a test reads the
report; C1-9 (Plan 04) record that commit-fold uses `ladder` and goal-prompt uses `detect`, both covered by Task 2's
knob-off tests. C1-1, C1-8, C1-12, C1-14, C1-16 and C1-20 are refuted and not counted.


#### Verification coverage (source-grounding pass)

- Symbol and path sweep: `tmp/auto/r325/conv-34/review-c1/ground.py` (git grep outside `.planning/`, plus path and
  line-range checks) over all ten plans, then `crossplan.py` for every unresolved symbol. Every unresolved path or
  symbol is one a phase 34 plan creates (`jev_config.py`, `jev_learn.py`, `tests/test_jev_config.py`,
  `tests/test_jev_config_parity.py`, `tests/test_jev_learn.py`, `tests/test_jev_typesafe_models.py`,
  `tests/test_jev_fast_decision_guard.py`, the two fixtures, the two eval files, `FakeFetch`, `learn_laya`,
  `learn_models`, `note_model`, `_knob`, `_settings`, `_laya_learn`, `_probe_fields`, the record status words) or a
  helper of the orchestrator scratch driver (`user_config_dir`, `rewrote_min_confidence` in 34-09's `live.py`). No
  plan cites a missing existing symbol and no cited line range runs past its file.
- Findings: each checked by reading the cited plan lines and source (`jev_review.py:218-222,466-532,580-587,673-681,
  773-795,967-979,1042-1067,1170-1188,1342-1368,1410-1440`, `eval_cases.py:35-48`, `toml_splice.py:105-110`,
  `cache.py:27-46`, `config_io.py:941-949`, `fold_group.py:225-272`, `gp_host.py:484-532`,
  `tests/test_jev_fast_decision.py:360-375,2540-2556,2750-2764,3668-3682`, `skills/jev-fast-decision/SKILL.md:17`,
  `34-SPEC.md:76,128,135,148-158`, `34-VALIDATION.md:33-34`, `34-RESEARCH.md:332,430,458-470,531-570`);
  `check_index_coverage` reported no recorded issue for the nine source files relied on. 14 of 20 confirmed
  (12 HIGH, C1-9 MEDIUM, C1-5 kept as LOW wording), 6 refuted (C1-1, C1-8 locked SPEC concurrency edges; C1-12
  latent; C1-14, C1-16, C1-20 contradicted by the source or the phase documents).
- Not run: the plans themselves, the test suite, the live calibration or spike, any judge lane.

## Convergence Outcome

The loop hit its 3-cycle cap. The cycle 3 findings were applied without another cross-AI review.

- **Cycles:** 3 of 3, the workflow maximum. Reviewer: referee-one (`review.default_reviewers`) in every cycle.
- **Unresolved concerns per cycle:**
  - Cycle 1 (b0485b0): 14, of which 12 HIGH and 2 actionable. Six findings were refuted.
  - Cycle 2 (694ae43): 9, of which 2 HIGH and 7 actionable. Six findings were refuted.
  - Cycle 3 (34ce5c0): 2, of which 1 HIGH and 1 actionable. C3-1 was refuted.
  - The count fell every cycle, so the loop never stalled. Open plan-revision conflicts were 0 in every cycle.
- **Decision (coordinator, 2026-11-15, following the 32.5 and 33 precedent and the run brief):** one narrow planner pass for C3-2 and C3-3, checked by a reviews-mode plan-checker run, with no fourth review cycle. Each fix is recorded in its plan's Review Dispositions Ledger under Round 3 — 34ce5c0:
  - C3-2: plan 09's `live.py calibrate` catches `TimeoutExpired` and `OSError` on both runs and writes a dated not-run record.
  - C3-3: plan 03's `fetch_laya_notes` treats a non-object PyPI document or `info` as a source error.
  - C3-1: recorded as rejected in plan 06 (SPEC R2 empty edge, "the ladder falls through as today"; D-04).
- **What checked the fix pass:** one plan-checker run, not a cross-AI review.
