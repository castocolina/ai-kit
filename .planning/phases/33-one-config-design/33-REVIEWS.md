---
phase: 33
cycle: 3
reviewers: [referee-one]
reviewed_at: 2026-11-15T11:20:58Z
plans_reviewed: [33-01-PLAN.md, 33-02-PLAN.md, 33-03-PLAN.md, 33-04-PLAN.md, 33-05-PLAN.md, 33-06-PLAN.md, 33-07-PLAN.md, 33-08-PLAN.md, 33-09-PLAN.md, 33-10-PLAN.md, 33-11-PLAN.md, 33-12-PLAN.md]
models:
  referee-one: "router-env/my-referee-one"
model_sources:
  referee-one: "pinned"
---

# Cross-AI Plan Review — Phase 33

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

Review cycle 3 (the last under the convergence cap), over the twelve plans of commit beda651 (revised from cycle 2's
C2-1..C2-7 and C1-11). Reviewer instance `referee-one` (`review.default_reviewers`) ran through the opencode lane
(`review-lane invoke --slug opencode --model router-env/my-referee-one --as referee-one`). Lane result:
`{"slug":"opencode","ok":true,"stubbed":false,"model":{"value":"router-env/my-referee-one","source":"pinned"}}`;
elapsed 363 s (08:11:13 to 08:17:16 local); stderr empty; one attempt. The prompt (555 KB) carried PROJECT.md (first 80
lines), the ROADMAP section, the One config design requirements, SPEC, CONTEXT, the locked-decisions note (D-01..D-27
locked; the owner's directive to redefine rather than preserve legacy quirks beyond SPEC R4-R6; HIGH reserved for gate
failures, SPEC or locked-decision breaks, config loss or unsafe execution), the cycle 2 source-check table and open
lists, the two cycle 3 jobs (a verdict for C1-5, C1-11 and C2-1..C2-7, then new issues), RESEARCH, PATTERNS,
VALIDATION, all twelve plans and the ponytail-lens focus line. Plan coverage: all twelve ids have their own section;
all nine verdict lines are present.

## OpenCode Review (referee-one)

Using the plan-review checklist to verify the prior findings against the revised plans and source, then check all 12 plans for new issues.
### Cycle 2 findings

- **C1-5: ACCEPTED, narrowly.** The refutation holds for two migration writers that both read a target where the `kept` key already existed: both bases contain it, and target precedence intentionally discards the conflicting source value. It does **not** prove safety against arbitrary concurrent edits; the prescribed post-check skips that key (`33-04-PLAN.md:131,293`). The separate, explicitly acknowledged late-publication race remains a data-loss risk.
- **C1-11: RESOLVED** — The parser test includes `['lanes']` as an unsupported header (`33-02-PLAN.md:171`), and the prescribed documentation and its pin now include that refusal (`33-06-PLAN.md:97,101`).
- **C2-1: RESOLVED** — The implicit-parent insertion algorithm and the precise two-added-line test are in Task 2, not just the ledger (`33-01-PLAN.md:177,185,189`). Dotted-key cases are explicitly refused.
- **C2-2: RESOLVED** — The quote-aware header matcher, parser cases, end-to-end bracketed-scope migration, and Python-splicer preservation test are prescribed in `33-02-PLAN.md:119,176-178`, `33-04-PLAN.md:130,181`, and `33-01-PLAN.md:124`.
- **C2-3: RESOLVED** — `revoke_legacy_trust` is defined and tested in `33-05-PLAN.md:142,178`; the CLI calls it before migration and has an end-to-end revoke-then-resolve test in `33-07-PLAN.md:201,243`. The existing `trust.revoke_trust` actually sweeps records by exact path (`skills/ai-kit-spec-review/ai_kit_spec/trust.py:56-75`).
- **C2-4: RESOLVED** — The four fixtures are explicitly retained and marked, with a named-test acceptance check (`33-09-PLAN.md:200-204,232`). Their current legacy fixtures are visible in `tests/test_ai_kit_spec_legacy_config.py:81-90,136-154,182-189`.
- **C2-5: RESOLVED** — Task 3 adds the seventh eval and updates the existing six-count test in the same task (`33-10-PLAN.md:175,187`); the current hard-coded assertion is at `tests/test_ai_kit_spec_check_providers.py:322-325`.
- **C2-6: RESOLVED** — The equal-lanes truth now says `completed` renames the old file **without** carrying trust, matching the migration tests (`33-05-PLAN.md:31,178`).
- **C2-7: RESOLVED** — Task 1 explicitly requires a JSON-compatible, double-quoted YAML description (`33-10-PLAN.md:117,133`); the strict parser rejects `: ` only for an unquoted scalar (`tests/test_skill_frontmatter.py:116-125`).

Review basis: GSD · implementation plans. The findings below are about the planned implementation, not results from executing it.

### 33-01

**Summary:** The splicer has explicit parsed-value and atomic-publication checks, but its header scanner still excludes a valid form the shared file must preserve.

**Strengths**
- C2-1 and C2-2 now have executable behavior and tests (`33-01-PLAN.md:124,177-189`).

**Concerns**
- **C3-1 — HIGH: Valid literal-quoted table names containing `]` are split incorrectly.** The scanner stops at the first `]` outside **double** quotes (`33-01-PLAN.md:98`). TOML also permits literal-quoted keys: `[ 'foo]bar' ]` without the spaces around its contents is valid; I verified `tomllib` parses `['foo]bar']`. A lane write against a config with that unrelated table will mis-split it or fail rather than preserve the unknown table as required. The new C2-2 test covers only double-quoted names (`:124`).

**Suggestions**
- Track both TOML basic and literal quoted key segments when finding a header terminator; add an unknown-table round-trip with a literal-quoted `]`.

**Risk assessment:** **HIGH** — valid user configuration can block roster writes.

### 33-02

**Summary:** The retry reader has concrete precedence and refusal tests; one task verification mode is not guaranteed to exist.

**Strengths**
- Shared header identity and bracketed-scope tests reach both parsing and retry resolution (`33-02-PLAN.md:119-122,176-178`).

**Concerns**
- **C3-2 — HIGH: Task 2 verifies an optional script mode.** The task says to add `mine` only “if the command line gets long” (`33-02-PLAN.md:180`), but its automated verification unconditionally calls `scope.py mine` (`:183-188`). The script initially defines `cases`, `render`, `dogfood`, `shards`, and `list` (`:116`), not `mine`. Following the short-command path makes the task fail its own gate.

**Suggestions**
- Make `mine` mandatory, with the exact case list, or verify using the explicitly defined `cases` mode.

**Risk assessment:** **HIGH** — the prescribed verification is not consistently executable.

### 33-03

**Summary:** Resolver parity and recovery are scoped to the code boundaries named in the decisions.

**Strengths**
- Explicit synthetic HOME/XDG cases prevent ambient-home lookups; recovery tests exercise interruption and mode preservation (`33-03-PLAN.md:112-131,179-190`).

**Concerns**
- No additional substantiated concern.

**Suggestions**
- None beyond running the prescribed parity and recovery tests.

**Risk assessment:** **MEDIUM** — several independent resolver copies must stay aligned.

### 33-04

**Summary:** The migration validates source snapshots and rechecks published target values, but the prescribed marker ordering has an untested interruption window.

**Strengths**
- Scope migration uses the reader’s header identity and tests a reachable bracketed `GSD_PROJECT` (`33-04-PLAN.md:130,181`; existing path validation: `skills/ai-kit-spec-review/references/cross-ai.mjs:3018-3026`).

**Concerns**
- **C3-3 — HIGH: A crash after retiring a source but before writing its marker defeats “migrate once.”** The plan removes the GSD block, then separately writes `migrated_from` (`33-04-PLAN.md:137-138`); the user JSON is likewise renamed before its marker is written (`:166`). If the marker write fails or the process stops between those steps, the next run finds no source and cannot record the marker. A subsequently re-added source is migrated again instead of ignored, contrary to `:25`. Existing interruption coverage stops before the source rename (`:199-205`), not after retirement.
- **C3-4 — HIGH: README instructions claim removed GSD data is recoverable when it is not.** The runner removes the block in place via atomic replacement, without a retained backup (`33-04-PLAN.md:137`), while Plan 11 directs the README to say “each old file stays recoverable” (`33-11-PLAN.md:195`). The original retry values are not recoverable from that GSD file after removal, particularly if a target value won a conflict.

**Suggestions**
- Specify a recoverable, idempotent intermediate state for a failure between retirement and marker publication, and test both GSD and user-source interruption at that boundary.
- Correct the README claim or prescribe an actual recovery artifact consistent with the locked migration decision.

**Risk assessment:** **HIGH** — interrupted migration can violate the one-time rule, and recovery guidance overclaims.

### 33-05

**Summary:** Migration and trust carry are separated cleanly, and the legacy revoke helper addresses the reported pre-migration case.

**Strengths**
- The old file is checked against its snapshot before retirement, and interrupted trust carry fails closed (`33-05-PLAN.md:145-149,178-181`).

**Concerns**
- No additional substantiated concern.

**Suggestions**
- Keep the end-to-end revoke test in Plan 07 as well as the module-level test.

**Risk assessment:** **MEDIUM** — correctness depends on integration with the new trust reader.

### 33-06

**Summary:** The documentation update now accurately identifies the reported unsupported-header case.

**Strengths**
- The subset wording and its tests are specified together (`33-06-PLAN.md:97-101`).

**Concerns**
- No additional substantiated concern beyond **C3-4**, whose misleading recovery claim is in Plan 11 rather than this plan.

**Suggestions**
- None.

**Risk assessment:** **LOW** — the identified prior wording issue is addressed.

### 33-07

**Summary:** The plan gives the role split, trust digest, and revoke path explicit contracts and tests.

**Strengths**
- It tests duplicate-key command influence and legacy-only revoke through the actual resolution path (`33-07-PLAN.md:239-243`).

**Concerns**
- No additional substantiated concern.

**Suggestions**
- Verify the role and trust tests against actual rendered command arguments as specified, not merely the digest.

**Risk assessment:** **MEDIUM** — this is a security-sensitive integration with several readers.

### 33-08

**Summary:** The fact-only documentation changes are bounded and sequenced after migration code exists.

**Strengths**
- The old-name scan distinguishes Markdown from the intentionally retained migration module (`33-08-PLAN.md:104,177`).

**Concerns**
- No additional substantiated concern.

**Suggestions**
- None.

**Risk assessment:** **LOW** — narrow documentation changes with a targeted scan.

### 33-09

**Summary:** The new fixture list resolves C2-4, but the tracer has conflicting expectations about generated comments.

**Strengths**
- The four migration fixtures are named and protected rather than converted indiscriminately (`33-09-PLAN.md:200-204,232`).

**Concerns**
- **C3-5 — HIGH: The one-line-diff tracer omits the generated comment that its own algorithm must add.** `test_one_model_change_is_one_line` starts with `[lanes.policy]` and three entries but does not specify a generated or user comment (`33-09-PLAN.md:109-110`). The prescribed `_refresh_ladder_comment` inserts the generated block when there are no contiguous comments above the policy header (`:97`), so a nonempty ladder produces more than the asserted one removed and one added line. The executor must infer an unstated fixture condition or fail the task gate.

**Suggestions**
- Give that fixture the exact existing generated ladder comment, or explicitly use an empty ladder, and retain a separate test proving initial comment insertion.

**Risk assessment:** **HIGH** — the tracer’s described fixture and its required algorithm can disagree at its gate.

### 33-10

**Summary:** The seven-eval test and quoted description fixes are actionable and touch the actual existing pins.

**Strengths**
- The new count assertion checks ordered IDs rather than merely changing `6` to `7` (`33-10-PLAN.md:175,187`).

**Concerns**
- No additional substantiated concern.

**Suggestions**
- Keep the eval addition and count-test update in the same commit, as prescribed.

**Risk assessment:** **LOW** — the reported mechanical failures are directly covered.

### 33-11

**Summary:** The inventory and no-GSD tests give the phase useful fitness checks, but the README’s recovery statement must match the migration.

**Strengths**
- The static scan has non-vacuity examples and explicitly records its passed-path limitation (`33-11-PLAN.md:183-190,252`).

**Concerns**
- **C3-4 — HIGH, cross-plan:** The prescribed “each old file stays recoverable” text conflicts with Plan 04’s GSD block removal without backup (`33-11-PLAN.md:195`; `33-04-PLAN.md:137`).

**Suggestions**
- Amend the exact README wording or the recovery mechanism before the phase gate.

**Risk assessment:** **HIGH** — the phase gate would otherwise publish a false data-recovery guarantee.

### 33-12

**Summary:** The judge loop specifies the pool, frozen tree, and regression gate, but its substitute path bypasses the existing retry/status handling.

**Strengths**
- Judge selection and the three-round cap are explicit (`33-12-PLAN.md:28-31,233-235`).

**Concerns**
- **C3-6 — HIGH: The substitute driver ingests immediately after a single runner call.** The plan directs `substitute.py` to call `lanes.run_lane(...)` and then ingest (`33-12-PLAN.md:118`), whereas the existing driver’s `run_one_lane` handles the status line, retry-after quota waits, owner stops, and failed ingest (`tmp/judge-32.4/lanes.py:282-308`). On a transient quota stop the substitute path attempts ingestion instead of following the stated wait behavior; a failed replacement may leave no usable verdict and block the judge gate.

**Suggestions**
- Specify a replacement-aware lane procedure that inspects the exit code and final `AIKIT-XAI` line, follows the same quota handling, and only ingests an eligible completed verdict with `--replaces`.

**Risk assessment:** **HIGH** — a required replacement judge can fail for a transient condition the normal driver handles.

#### Status: Issues Found — fix and re-review

All 12 manifest plans were covered. The review did not execute the implementation plans or the full test suite; the findings concern their prescribed behavior and verification.


---

## Consensus Summary

One reviewer ran (`referee-one`), so there is no cross-reviewer agreement to report; the consensus gate does not
engage and every reviewer HIGH counts unless the source check refutes or re-rates it against the HIGH definition the
reviewer was given (gate failure, SPEC or locked-decision break, config loss or corruption, unsafe execution). The
review cites `file:line` evidence throughout and carries no evidence-quality discount marker. The orchestrator checked
each verdict and new finding against the plans and the source (table below).

### Agreed Strengths
- (single reviewer) Every cycle 2 finding is fixed in task actions, behavior lines and acceptance lines a haiku
  executor runs, not only in the Round 2 ledgers: the implicit-parent block insertion and its two-line test (C2-1,
  `33-01-PLAN.md:177,185,189`), quote-aware headers on both sides with bracketed-scope cases end to end (C2-2,
  `33-01-PLAN.md:98,124`, `33-02-PLAN.md:120,177-178`, `33-04-PLAN.md:130,181`), `revoke_legacy_trust` wired into
  `trust-local --revoke` with module and resolve-level tests (C2-3, `33-05-PLAN.md:142,178`, `33-07-PLAN.md:201,243`),
  the four migration fixtures named, marked and counted (C2-4, `33-09-PLAN.md:198-204,223,232`), the seven-eval test
  renamed with the exact ordered ids (C2-5, `33-10-PLAN.md:175,187`), the completed-path truth (C2-6,
  `33-05-PLAN.md:31`), the quoted description (C2-7, `33-10-PLAN.md:133`) and the `['lanes']` refusal pinned and
  documented (C1-11, `33-02-PLAN.md:171`, `33-06-PLAN.md:97,101`). The reviewer accepts C1-5's refutation.

### Agreed Concerns
- None (one reviewer). The reviewer raised six new items as HIGH (C3-1..C3-6); the source check below confirms all six
  as real but keeps only C3-5 at HIGH.

### Divergent Views
- None (one reviewer). The orchestrator re-rates C3-1, C3-2, C3-3, C3-4 and C3-6 below HIGH (see the table).

### Source check of the findings (orchestrator, 2026-11-15, cycle 3)

| # | Plan | Finding | Severity | Verdict | Evidence |
|---|------|---------|----------|---------|----------|
| C1-11, C2-1..C2-7 | 01, 02, 04, 05, 06, 07, 09, 10 | Cycle 2 fixes | (cycle 2: 4 HIGH, 2 MEDIUM, 2 LOW) | RESOLVED (agreed) | Each fix is in a task body, not only the Round 2 ledger (`tmp/auto/r325/conv-33/review-c3/spot.sh`): `33-01-PLAN.md:98,124,177,189`; `33-02-PLAN.md:120,123,171,177-178,188`; `33-04-PLAN.md:130,181`; `33-05-PLAN.md:31,142,178`; `33-06-PLAN.md:97,101,110`; `33-07-PLAN.md:201,243`; `33-09-PLAN.md:198-204,223,232`; `33-10-PLAN.md:133,167,175,187`. Checked against source: `trust.revoke_trust(store_dir, real_path)` (`trust.py:56`) is what `revoke_legacy_trust` calls; the legacy store is `review-spec-trust` (`config_io.py:286`); the six HEAD eval ids are in the order Plan 10 asserts (`evals.json`); the nine marked fixture lines are `tests/test_ai_kit_spec_legacy_config.py:88-89,139-140,152-154,187-188`, and Plan 07's new assertions (`33-07-PLAN.md:144-147`) add no literal `review-spec.toml`, so `marked lines: 9` holds; Plan 02's ten new case names match "HEAD plus 10". |
| C1-5 | 04 | Residual of the post-publish check | HIGH (cycle 2: refuted) | Refutation ACCEPTED by the reviewer | The reviewer's remaining note is the late-publication race that T-33-13 already records as an accepted residual under D-25 (`33-04-PLAN.md:246`). Not counted. |
| C3-1 | 01 | A literal-quoted header name holding `]` (`['foo]bar']`) is cut at the first `]` outside double quotes | HIGH | CONFIRMED, re-rated MEDIUM | `33-01-PLAN.md:98`. Probe: `tomllib.loads("['foo]bar']\nx = 1\n")` gives `{'foo]bar': {'x': 1}}`, and the splicer's inner text `'foo` fails `tomllib.loads("'foo = 0")` with a raw `TOMLDecodeError`. It fails closed (nothing is written; no config is lost) and such a name is already outside the shared subset: the runner refuses a literal-quoted header anywhere and skips the file (`33-02-PLAN.md:120`), as Plan 06 documents (`33-06-PLAN.md:97`). Gap left: the splicer raises an unnamed `TOMLDecodeError` instead of a SpliceError naming the line, and no test pins it. |
| C3-2 | 02 | Task 2's verify calls `scope.py mine`, a mode the action makes optional | HIGH | CONFIRMED, re-rated MEDIUM | `33-02-PLAN.md:180` ("as a mode `mine` if the command line gets long") versus `:183,189`. The acceptance line `:189` requires `scope.py mine` to print `cases rc: 0`, so an executor that follows the whole task creates the mode; the gate does not fail as written. Wording fix: make `mine` mandatory with its case list. |
| C3-3 | 04 | A stop between retiring a source and recording `migrated_from` leaves no marker, so a block re-added later migrates again | HIGH | CONFIRMED as a residual, re-rated LOW | `33-04-PLAN.md:25,137-138,166`. The write order merge -> retire -> record is the locked D-14 order (`33-CONTEXT.md:127-129`); recording first would ignore a block that was never retired. A re-added block then merges under D-14's target-wins rule (its conflicting keys are named and dropped), so nothing already migrated is lost or overridden. Gap left: the residual is not recorded in Plan 04's threat model. |
| C3-4 | 11 (04) | The README line "each old file stays recoverable" overclaims for the GSD block, which is removed in place with no copy | HIGH | CONFIRMED, re-rated MEDIUM | `33-11-PLAN.md:195`; the block is removed by an atomic rewrite (`33-04-PLAN.md:23,137`; SPEC R7, `33-SPEC.md:117`), and T-33-13 itself says a GSD block's values can be lost in the accepted race (`33-04-PLAN.md:246`). Only the roster (`review-spec.toml.migrated`) and `cross-ai.json.migrated` stay recoverable. A documentation accuracy defect; no plan task loses data through it and no test pins the sentence. |
| C3-5 | 09 | `test_one_model_change_is_one_line` leaves the `[lanes.policy]` fixture unspecified while `_refresh_ladder_comment` inserts the generated block above a policy with a ladder and no comment | HIGH | CONFIRMED (HIGH) | `33-09-PLAN.md:97` (no comment above the header -> the generated lines are inserted) and `:113` (fixture: "`[lanes.policy]` and three entries", ladder and comment unspecified; exactly one `- ` and one `+ ` line asserted). The natural fixture (a policy with a ladder, no comment) fails the task's own gate, and the haiku executor is left to choose between changing the fixture and changing the refresh rule. |
| C3-6 | 12 | `substitute.py` ingests right after one `run_lane` call, without the transient `retry_after_s` wait the normal driver has | HIGH | CONFIRMED, re-rated MEDIUM | `33-12-PLAN.md:118` versus `tmp/judge-32.4/lanes.py:282-308` (`run_one_lane`: up to 3 waits on exit 75 with `status=transient` and `retry_after_s`); the rails require one wait of exactly `retry_after_s` before re-invoking the same lane. A transient stop of a substitute is reported instead (`33-12-PLAN.md:149`), and one usable judge is an accepted pool, so the judge gate does not fail; the substitute path just drops a retry the rails require. |

### Current HIGH Concerns (cycle 3)

Single reviewer, so the consensus gate is skipped; each reviewer HIGH counts unless the source check refutes or
re-rates it. 1 open, confirmed against the plan:
- C3-5 (Plan 09): the one-line-diff tracer `test_one_model_change_is_one_line` does not say what sits above
  `[lanes.policy]`; with a ladder and no comment the planned `_refresh_ladder_comment` inserts the generated block, so
  the asserted one-line diff fails. Fix: give the fixture's `[lanes.policy]` the exact generated comment block for its
  ladder (or an empty ladder) and keep the separate first-write test (`33-09-PLAN.md:120`) for the insertion.

Every cycle 2 HIGH (C2-2..C2-5) is resolved; C1-5's refutation is accepted by the reviewer.

### Current Actionable Non-HIGH Concerns (cycle 3)

5 open, not yet in a plan:
- C3-1 (Plan 01, MEDIUM): `split_blocks` should raise SpliceError naming the line when a header's inner text does not
  parse (a literal-quoted name holding `]`), with a test, instead of a raw TOMLDecodeError.
- C3-2 (Plan 02, MEDIUM): Task 2 should make the `mine` scope mode mandatory with its exact case list.
- C3-4 (Plan 11, MEDIUM): the README migration line should say the old roster and `cross-ai.json` stay recoverable as
  `.migrated` files, while the GSD block's values move into `config.toml` and the block is removed.
- C3-6 (Plan 12, MEDIUM): `substitute.py` should follow `run_one_lane`'s quota handling (one wait of exactly
  `retry_after_s` on a transient exit 75, then the same lane again) before ingesting with `--replaces`.
- C3-3 (Plan 04, LOW): record in the threat model (T-33-11 or T-33-13) the accepted residual that a stop between
  retiring a source and recording `migrated_from` lets a re-added block migrate again under D-14's target-wins rule.


### Verification coverage (source-grounding pass, cycle 3)

- Symbol and path sweep: `tmp/auto/r325/conv-33/review-c3/ground.py` (git grep outside `.planning/`, plus path and
  line-range checks) over all twelve revised plans. Every unresolved path or symbol is one the plans create (the cycle
  2 set plus the new names `revoke_legacy_trust`, `test_revoke_before_first_migration_carries_nothing`,
  `test_revoke_before_first_migration_stays_revoked`, `TestTrustLocalRevokeLegacy`, `test_new_key_under_implicit_parent`,
  `test_bracketed_scope_header_is_one_table`) or the commit id `ab06802`. Every existing helper a fix relies on exists:
  `trust.revoke_trust` (`trust.py:56`), `cfg_trust_store_dir` (`config_io.py:283-286`, the `review-spec-trust` store),
  `run_one_lane` (`tmp/judge-32.4/lanes.py:282`).
- Ledger check: `tmp/auto/r325/conv-33/review-c3/ledgers.py` prints every Round 2 ledger section, and `spot.sh` finds
  each Round 2 fix in a task action, behavior line or acceptance line (line numbers in the table above).
- Findings: each checked by reading the cited plan lines and source (`33-01-PLAN.md:96-189`, `33-02-PLAN.md:115-189`,
  `33-04-PLAN.md:23-25,130-138,166,246`, `33-05-PLAN.md:125-184`, `33-07-PLAN.md:138-151,196-203`,
  `33-09-PLAN.md:92-121,190-234`, `33-11-PLAN.md:195`, `33-12-PLAN.md:100-162`, `tmp/judge-32.4/lanes.py:282-308`,
  `tests/test_ai_kit_spec_legacy_config.py` fixture lines, `skills/ai-kit-spec-config/evals/evals.json`), plus one
  `tomllib` probe for C3-1. `check_index_coverage` reported no recorded issue for the six repository files relied on
  (`trust.py`, `config_io.py`, `tests/test_ai_kit_spec_legacy_config.py`, `tests/test_ai_kit_spec_check_providers.py`,
  `references/cross-ai.mjs`, `evals.json`); the `tmp/judge-32.4/` driver is untracked scratch and was read directly.
  Six reviewer HIGHs confirmed as real: C3-5 kept HIGH; C3-1, C3-2, C3-4 and C3-6 re-rated MEDIUM, C3-3 LOW.
- Not run: the plans themselves, the full test suite, any migration or judge lane.

---

## Cycle 2 review (history, commit 90801f2)

The cycle 2 record below is kept as written; its headings sit one level down.

Review cycle 2, over the twelve plans of commit e43af3a (revised from cycle 1's C1-1..C1-19). Reviewer instance
`referee-one` (`review.default_reviewers`) ran through the opencode lane (`review-lane invoke --slug opencode --model
router-env/my-referee-one --as referee-one`). Lane result:
`{"slug":"opencode","ok":true,"stubbed":false,"model":{"value":"router-env/my-referee-one","source":"pinned"}}`;
elapsed 757 s (07:32:20 to 07:44:57 local); stderr empty; one attempt. The prompt (525 KB) carried PROJECT.md (first 80
lines), the ROADMAP section, the One config design requirements, SPEC, CONTEXT, the locked-decisions note (D-01..D-27
locked; the owner's 2026-11-15 directive to redefine rather than preserve legacy quirks beyond SPEC R4-R6; HIGH
reserved for gate failures, SPEC or locked-decision breaks, config loss or unsafe execution), the cycle 1 source-check
table and open lists, the two cycle 2 jobs (a verdict per C1-n, then new issues), RESEARCH, PATTERNS, VALIDATION, all
twelve plans and the ponytail-lens focus line. Plan coverage: all twelve ids have their own section; all nineteen
cycle 1 findings have a verdict line.

### OpenCode Review (referee-one)

Using the plan-review checklist and ponytail lens to verify all 19 prior dispositions, then check all 12 plans against the source and locked decisions. This is read-only; I will not modify repository files.
The revised tasks address most cycle-1 findings directly. Source checks have also exposed two new transition gaps: revoking trust before migration can leave legacy consent available to carry forward, and Plan 09’s fixture conversion conflicts with migration assertions added by Plan 07. I’m checking the remaining runner and closing gates before assigning final dispositions.
#### Cycle 1 findings

Reviewed at commit `e43af3a139cc34ca8a4c304c7c6b403e1979f86e`. All plan citations below refer to `.planning/phases/33-one-config-design/`. Verdicts assess the **executable plan text**, not an implementation that has already landed.

- **C1-1: RESOLVED** — `33-01-PLAN.md:173-185` replaces whole-entry rendering with block-by-block editing and requires one-line-diff/comment-preservation tests.
- **C1-2: RESOLVED** — `33-01-PLAN.md:166-181` specifies insertion before the next retained group, with middle, start and interleaved-role regression cases.
- **C1-3: RESOLVED** — `33-03-PLAN.md:98,123-131,156-165` covers unset/empty HOME and prohibits ambient fallback. This directly replaces the existing fallback at `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:277`.
- **C1-4: RESOLVED** — `33-02-PLAN.md:120,170` explicitly rejects both table/value collision directions and tests the valid implicit-parent case.
- **C1-5: PARTIAL** — `33-04-PLAN.md:130,207` adds post-publication verification and an overlapping-publication test, but its predicate excludes `kept` keys. A replacement removing all preserved keys can therefore pass verification and permit source retirement.
- **C1-6: RESOLVED** — `33-04-PLAN.md:133-136,165,208-209` captures the migrated snapshot, checks source equality before retirement and tests changed GSD/user sources.
- **C1-7: RESOLVED** — `33-02-PLAN.md:119` and `33-04-PLAN.md:129,178-179` share decoded header identity and test `["runner"."retry"]`. A separate bracket-bearing scope issue remains below.
- **C1-8: RESOLVED** — `33-02-PLAN.md:118,121` introduces strict UTF-8 decoding; `33-04-PLAN.md:130,133,136,165,180-181` applies it to migration reads and tests unchanged invalid-byte files.
- **C1-9: RESOLVED** — `33-05-PLAN.md:146-147,178` requires a pre-publish rebuild and whole-document post-check, rather than checking only `lanes`.
- **C1-10: RESOLVED** — `33-05-PLAN.md:148,176-177` forbids trust carry on a `completed` run and tests failed rename → revoke → restart. Pre-migration revocation is a distinct uncovered path, below.
- **C1-11: PARTIAL** — `33-06-PLAN.md:97` correctly distinguishes opaque lane content, but its “only” list still omits unsupported non-runner header names rejected by `33-02-PLAN.md:119-120`.
- **C1-12: RESOLVED** — `33-05-PLAN.md:128,133` includes duplicate-key command overrides in the digest; `33-07-PLAN.md:238` adds resolve-level regressions. This reaches the actual merge and placeholder mechanisms at `config_io.py:368-382` and `commands.py:111-132`.
- **C1-13: RESOLVED** — `33-07-PLAN.md:126,206,217` explicitly sends the transitional writer test to the legacy path. This reaches `tests/test_ai_kit_spec_trust.py:279-294`.
- **C1-14: REJECTED-ACCEPTED** — `33-08-PLAN.md:98` scans the directory containing the permanent legacy constant created by its prerequisite at `33-05-PLAN.md:136`. Thus the stated no-match return-code failure is not reachable in this sequence.
- **C1-15: RESOLVED** — `33-09-PLAN.md:173,182` moves the routing import and writer calls in the API-removal commit, including the callers at `tests/test_ai_kit_spec_routing.py:679-683,706-714`.
- **C1-16: RESOLVED** — `33-09-PLAN.md:158,167-171` requires checked target reads before mutation; the existing helpers map decoding/parsing failures to `ConfigError` (`config_io.py:329-352`), caught by `cli.py:1038-1045`.
- **C1-17: RESOLVED** — `33-09-PLAN.md:157,168-170` guards before migration; `33-10-PLAN.md:117,120` detects legacy-only rosters and obtains replacement approval.
- **C1-18: RESOLVED** — The guard now precedes every migration/write (`33-09-PLAN.md:168`), and the explanation at `33-10-PLAN.md:121` matches that ordering.
- **C1-19: RESOLVED** — `33-11-PLAN.md:183-192` adds Python/JS write-site scans, explicit exceptions, mandatory migrator detection and non-vacuity checks. Its parameter-passed-path limitation is disclosed at `:252`.

#### 33-01

**Summary:** The revised splicer resolves the two original defects and preserves the validate-before-publish design. One newly prescribed sub-table editing path remains incomplete.

**Strengths**
- Comment preservation and insertion ordering now have concrete regression cases (`33-01-PLAN.md:166-185`).
- Publication reuses `cache_write_bytes`, whose existing cleanup already removes failed temporary writes (`skills/ai-kit-spec-review/ai_kit_spec/cache.py:27-42`).

**Concerns**
- **C2-1 — MEDIUM — Implicit parent tables cannot receive new sibling fields.** At `33-01-PLAN.md:181`, `_edit_group` visits only existing blocks and excludes dict-valued child keys from their parent. Given:
  ```toml
  [[lanes.review]]
  key = "a"
  [lanes.review.extra.tuning]
  depth = 1
  ```
  adding `extra.enabled = true` has no block that can emit `enabled`: the root excludes `extra`, while `extra.tuning` edits only `depth`. The equality check then refuses the otherwise valid edit. This is distinct from C1-1’s direct-subtable edit.

**Suggestions**
- Specify emission of missing intermediate blocks and add this exact regression case.

**Risk Assessment:** **MEDIUM** — incorrect output is refused rather than published, but a valid supported edit cannot complete.

#### 33-02

**Summary:** The read-side plan has explicit collision handling, strict decoding and source-precedence tests. Header recognition is still narrower than the scope names the runner accepts.

**Strengths**
- Both collision directions and parent-after-child syntax are covered (`33-02-PLAN.md:170`).
- Keeping template version 8 is grounded in the same-version pristine-copy upgrade behavior (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:282-289`).

**Concerns**
- **C2-2 — HIGH — Accepted bracket-bearing scope names cannot migrate.** Existing scope validation rejects separators and `..`, not brackets (`skills/ai-kit-spec-review/references/cross-ai.mjs:3018-3026`); the plan retains that rule at `33-02-PLAN.md:122`. Plan 04 therefore emits valid TOML such as:
  ```toml
  [runner.retry.scopes."workstreams/ws[1]"]
  ```
  But `TOML_TABLE_HEADER_RE` at `33-02-PLAN.md:119` rejects brackets even inside quoted segments. Plan 04’s merge verification consequently fails, leaving that accepted scope unmigrated.

**Suggestions**
- Make header-boundary recognition quote-aware and add a `ws[1]` migration case. This implements the locked scope rule without changing it.

**Risk Assessment:** **HIGH** — an accepted GSD scope fails SPEC R7’s migration requirement.

#### 33-03

**Summary:** The resolver revision directly addresses C1-3 and reaches the named Python boundaries, setup and runner parity.

**Strengths**
- Unset and empty HOME are tested with ambient lookups patched to fail (`33-03-PLAN.md:98,131`).
- Recovery retains the backup and replaces the real target rather than writing through the live path (`33-03-PLAN.md:192`), correcting `tools/setup.py:3496-3497`.
- The existing external-provider discovery already treats an empty directory as absent (`tools/common_config.py:540-547`).

**Concerns**
- No additional actionable concern established in this plan.

**Suggestions**
- Retain the explicit error-outcome mapping and interruption tests; avoid broadening the resolver refactor to other tools’ folders.

**Risk Assessment:** **LOW** — the changes are bounded and use existing setup/publication patterns.

#### 33-04

**Summary:** Snapshot-based retirement and strict UTF-8 handling are substantially improved. The remaining C1-5 defect is in the new verification predicate, not merely the disclosed no-lock residual window.

**Strengths**
- GSD and user-source changes are tested independently (`33-04-PLAN.md:208-209`).
- Byte-preservation, CRLF, last-key removal and symlink behavior have explicit fixtures (`:172-179`).

**Concerns**
- **C1-5 — HIGH, still partial:** `mergeTomlTable` verifies only entries **not** listed in `kept` (`33-04-PLAN.md:130`). Suppose the target already contains `max_retries=3`, the source contains `max_retries=1`, and a concurrent replacement removes the target key before the post-read. Because the key was preserved, the predicate checks nothing and passes—even against an empty document. Step 2 may then retire the source (`:135-136`). The overlapping test at `:207` covers newly inserted values only.
- **C2-2 also reaches this plan:** emitted scope headers at `:129,134` must be readable by Plan 02.

**Suggestions**
- Build the expected post-merge values from both preserved target values and inserted source values, then verify all of them before retirement.
- Add an overwritten-`kept`-key case. This requires no lock and does not reopen D-25.

**Risk Assessment:** **HIGH** — the prescribed check can approve retirement after configuration values have already disappeared.

#### 33-05

**Summary:** The migration module now has concrete rebuild, whole-document verification and restart behavior. The original C1-9/C1-10 cases are addressed.

**Strengths**
- Pre/post-publication checks and injected concurrent-write tests are executable task requirements (`33-05-PLAN.md:146-148,178`).
- Canonical trust bytes now include same-file duplicate-key overrides (`:128,133`), matching the actual field-merging behavior at `config_io.py:368-382`.

**Concerns**
- The trust-carry mechanism at `33-05-PLAN.md:148` participates in **C2-3** below: unchanged legacy consent can still be carried after a pre-migration CLI revocation.
- A minor internal contradiction remains: `:31` says the already-published/equal-lanes path carries trust, while `:148,176` explicitly prohibit it. The task action and regression test are the safer, intended behavior.

**Suggestions**
- Align the truth statement with the task action.
- Keep legacy-revocation handling inside the migration boundary so legacy identities remain centralized.

**Risk Assessment:** **MEDIUM** locally; its integration with `trust-local --revoke` remains **HIGH** until C2-3 is fixed.

#### 33-06

**Summary:** The retry documentation now describes the neutral configuration and opaque roster content much more accurately. C1-11 is not fully closed.

**Strengths**
- Documentation and its template-derived TOML pin change together (`33-06-PLAN.md:97-101`).
- Curated-config no longer directs users to hand-edit an unknown GSD key (`:125-129`).

**Concerns**
- **C1-11 — MEDIUM, still partial:** the prescribed paragraph says that outside runner tables only multiline strings, non-lanes arrays of tables and invalid UTF-8 cause refusal (`33-06-PLAN.md:97`). Yet Plan 02 validates every recognized header name before deciding whether its body is opaque (`33-02-PLAN.md:119-120`). Valid non-runner TOML such as `['lanes']` is rejected by `splitTomlName`. The documentation’s exhaustive “only” claim is therefore false.

**Suggestions**
- Describe unsupported-header refusal explicitly, or make opaque-header handling match the stated contract. Pin that distinction with a parser/doc regression.

**Risk Assessment:** **MEDIUM** — misleading troubleshooting guidance remains, though it does not itself corrupt files.

#### 33-07

**Summary:** The reader switch is carefully staged, including the transitional writer test and duplicate-key trust regression. Revocation still misses the legacy-only state.

**Strengths**
- Conversion rule 8 fixes the buildable-commit problem directly (`33-07-PLAN.md:126,217`).
- The digest regression reaches resolved entries used for command rendering (`:238`; `commands.py:111-132`).

**Concerns**
- **C2-3 — HIGH — Revocation before first migration leaves legacy consent usable.** `33-07-PLAN.md:200` leaves `--revoke` unchanged and before migration. The existing branch revokes only the selected store/path (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:835-843`), and `trust.revoke_trust` matches records by that exact path (`trust.py:56-70`). With only a trusted legacy roster present, the new CLI revokes no legacy record. The next resolve then carries that still-valid consent through `33-05-PLAN.md:148`, making the command eligible again without renewed approval.

**Suggestions**
- Revoke both current and legacy identities without first carrying trust.
- Add legacy-only trusted roster → CLI revoke → resolve coverage.

**Risk Assessment:** **HIGH** — an explicit consent-revocation action can fail to prevent subsequent command eligibility.

#### 33-08

**Summary:** The fact-only rename plan is appropriately narrow. The rejection of C1-14 remains justified by its committed prerequisite.

**Strengths**
- Exact edits preserve the warning prefix and show-before-trust sequence (`33-08-PLAN.md:79-84`; existing sequence at `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:191-196`).
- The permanent migration-module hit keeps the scan’s `git grep` return code zero (`33-05-PLAN.md:136`; `33-08-PLAN.md:98`).

**Concerns**
- No additional actionable concern established.

**Suggestions**
- Keep this as a fact-only documentation change; no additional judge scope or runtime abstraction is needed.

**Risk Assessment:** **LOW** — bounded text updates with a concrete scan.

#### 33-09

**Summary:** The revised guard ordering, checked reads and routing-call conversion resolve the original writer findings. Task 3 now conflicts with assertions deliberately introduced in Plan 07.

**Strengths**
- Guard-before-migrate makes “nothing written” truthful (`33-09-PLAN.md:167-170`).
- Routing imports and callers move in the removal commit (`:173`).

**Concerns**
- **C2-4 — HIGH — Blanket fixture conversion leaves migration assertions failing.** `33-09-PLAN.md:197` converts remaining legacy fixtures and says no migration tests are expected in those modules. But `33-07-PLAN.md:143-146` explicitly changes `TestLegacyLoad.test_tracer` to require old-file retirement/`.migrated` bytes, and two warning tests to require a migration notice. Their source fixtures are at `tests/test_ai_kit_spec_legacy_config.py:81-122,136-160`. Once converted to `config.toml`, no migration occurs; those assertions cannot pass unchanged.

**Suggestions**
- Either retain and explicitly mark these fixtures as migration cases, or specify the corresponding assertion conversion by test name. Do not leave the haiku executor to reconcile contradictory task instructions.

**Risk Assessment:** **HIGH** — the prescribed Task 3 cannot meet its own green scope/unit gate unchanged.

#### 33-10

**Summary:** The wizard replacement flow is now coherent with the CLI guard. The added eval has an existing assertion that this task does not update.

**Strengths**
- Both roster forms trigger replacement approval (`33-10-PLAN.md:117,120`).
- Check-only explicitly uses `--no-migrate` (`:146`).

**Concerns**
- **C2-5 — HIGH — Adding a seventh eval breaks the required scope test.** `33-10-PLAN.md:171` adds `edge-old-roster-migration-pending` to the existing six evals. `tests/test_ai_kit_spec_check_providers.py:322-325` asserts exactly six, and that module is explicitly run by the plan’s scope runner (`33-10-PLAN.md:109`). Neither the file list nor task action updates this assertion.

**Suggestions**
- Include the covering test in Task 3 and update its count/name or, preferably, assert the required eval IDs.
- Explicitly quote the proposed YAML description, whose embedded `: ` requires a quoted scalar under `tests/test_skill_frontmatter.py:116-125`.

**Risk Assessment:** **HIGH** — the seventh eval makes the plan’s specified verification fail.

#### 33-11

**Summary:** This plan now supplies the missing foreign-write scan rather than relying solely on identifier bans. Its limitations are visible.

**Strengths**
- Write-site discovery includes non-vacuity examples in both languages and requires finding the migrator (`33-11-PLAN.md:183-192`).
- No-GSD runs test both absence of `.planning/` and repeat-run byte stability (`:185`).
- The static scan’s passed-in-path blind spot is disclosed (`:252`).

**Concerns**
- No additional blocking concern established. The scan is a bounded structural guard, not proof that every indirect write respects another tool’s schema.

**Suggestions**
- Preserve that qualification in the design record and final verification; do not describe the scan as exhaustive data-flow analysis.

**Risk Assessment:** **MEDIUM** — broad phase gates are appropriate, but the foreign-write assurance remains intentionally bounded.

#### 33-12

**Summary:** The judge-loop adaptation is grounded in the existing scratch drivers and keeps the selected judges, frozen-tree discipline and round cap.

**Strengths**
- The prescribed replacement anchors match the actual drivers: instance list and retry cap at `tmp/judge-32.4/lanes.py:32,297`, skill lists at `loop_record_check.py:10` and `verdict_facts.py:16`.
- Removing native selection matches `tools/judge_loop.py:1520-1549`, which accepts the first two usable external judges or one alone.

**Concerns**
- No additional blocker established in the driver substitutions reviewed.

**Suggestions**
- Keep copying the existing drivers rather than introducing another runner. Preserve recorded substitution reasons and the fixed judged set.

**Risk Assessment:** **MEDIUM** — operationally long-running, but its control flow and verification are explicit.

#### Overall assessment

**Status: Issues Found — fix and re-invoke.**

Coverage: **12/12 plans**, with **19/19 cycle-1 dispositions** checked.

Cycle-1 result: **16 resolved, 2 partial, 1 rejection accepted**. The remaining prior findings are **C1-5** and **C1-11**.

New findings:
- **HIGH:** C2-2 scope-header parsing, C2-3 pre-migration revocation, C2-4 fixture/assertion mismatch, C2-5 eval-count gate.
- **MEDIUM:** C2-1 implicit-parent splicing.

The architecture does not need reopening. The necessary changes are localized: complete the verification predicate, align header parsing with accepted scope names, revoke both trust identities, and update the specific tests affected by the migration.

Skipped full implementation, suite execution and external judge lanes; only source inspection and small read-only predicate/parser probes were performed. No repository files were modified; the remaining risks are configuration retention, consent revocation and executable gates.


---

### Consensus Summary

One reviewer ran (`referee-one`), so there is no cross-reviewer agreement to report; the consensus gate does not
engage and every reviewer HIGH counts unless the source check refutes it. The review cites `file:line` evidence
throughout, ran small read-only probes, and carries no evidence-quality discount marker. The orchestrator checked each
cycle 2 verdict and new finding against the plans and the source (table below).

#### Agreed Strengths
- (single reviewer) Sixteen of the nineteen cycle 1 findings are fixed in task actions, behavior lists and acceptance
  lines a haiku executor runs, not only in the ledgers: the splicer edits sub-table blocks in place and inserts by the
  next matched entry (C1-1, C1-2), the subset parser refuses table/value collisions and invalid UTF-8 (C1-4, C1-8), the
  migrations re-read before and after publishing and retire only their snapshot (C1-6, C1-9), only the publishing run
  carries trust (C1-10), the digest covers same-key rows (C1-12), the transition commits stay buildable (C1-13,
  C1-15), render-toml guards before it migrates or writes (C1-16..C1-18), and the D-17 write scan exists with
  non-vacuity checks (C1-19). C1-14's rejection holds.

#### Agreed Concerns
- None (one reviewer). The reviewer's priority order: consent revocation (C2-3), executable gates (C2-4, C2-5),
  migration of accepted scope names (C2-2).

#### Divergent Views
- None (one reviewer). The orchestrator disagrees with the reviewer on C1-5 (see the table).

#### Source check of the findings (orchestrator, 2026-11-15)

| # | Plan | Finding | Severity | Verdict | Evidence |
|---|------|---------|----------|---------|----------|
| C1-1..C1-4, C1-6..C1-10, C1-12, C1-13, C1-15..C1-19 | 01-11 | Cycle 1 fixes | (cycle 1 HIGH/MEDIUM) | RESOLVED (agreed) | Each fix is in the task body, not only the ledger: `33-01-PLAN.md:181,185,195`; `33-02-PLAN.md:117-121,170-171`; `33-03-PLAN.md:98,131`; `33-04-PLAN.md:129-137,165,207-209`; `33-05-PLAN.md:133,146-149,176-178`; `33-07-PLAN.md:126,206,238`; `33-09-PLAN.md:157-158,167-173,182`; `33-10-PLAN.md:117,120`; `33-11-PLAN.md:183-192`. The D-17 baseline the scan relies on re-runs clean today (`tmp/auto/r325/conv-33/planner/gsd_write_scan.py`: the three fixture sites only). |
| C1-14 | 08 | Scan exit code on no match | MEDIUM | REJECTED, rejection accepted | `33-08-PLAN.md:177`; the reviewer agrees. |
| C1-5 | 04 | Post-publish check skips `kept` keys, so a removed pre-existing target key passes and the source retires | HIGH (reviewer: partial) | REFUTED as a residual; C1-5 RESOLVED | A `kept` key is one the target already held; D-14 (`33-CONTEXT.md:127-128`) makes the target's own key win and names the conflicting source value in the notice, so that source value is discarded by design whatever happens next. A concurrent runner's stale publish cannot drop a key that predates both runs (its base holds it too); only a deliberate edit can, and retiring a value D-14 already overrode loses nothing the migration owned. The overlapping-publish case for inserted keys is `33-04-PLAN.md:207`. Not counted. |
| C1-11 | 06 | The "only causes of a skip" list omits an unsupported header name outside `[runner]` | MEDIUM | CONFIRMED (partial) | `33-06-PLAN.md:97` lists multi-line string, array of tables outside `[lanes]`, invalid UTF-8 as the only outside-runner causes; `33-02-PLAN.md:120` sends every header name through `splitTomlName` and errors `unsupported table name` on null (a literal-quoted `['lanes']` segment, for example), whatever the region. |
| C2-1 | 01 | A changed entry cannot gain a key under an implicit parent table (`[lanes.review.extra.tuning]` exists, `extra.enabled` added) | MEDIUM | CONFIRMED (fails closed) | `33-01-PLAN.md:181`: the root block drops dict-valued child keys (`extra`), and no block has rel `("extra",)`, so `enabled` is never written and the equality check raises SpliceError. |
| C2-2 | 02, 04 | A scope name holding `[` or `]` cannot migrate or be read | HIGH | CONFIRMED (narrow) | `TOML_TABLE_HEADER_RE = /^\s*\[([^\[\]]+)\]\s*(#.*)?$/` (`33-02-PLAN.md:119`) rejects brackets even inside a quoted segment; `retryScope` and `scopedConfigPaths` reject only separators and `..` (`33-02-PLAN.md:122`; `cross-ai.mjs:3018-3021`). The reviewer's `workstreams/ws[1]` is not reachable (GSD's workstream policy allows only `[a-zA-Z0-9][a-zA-Z0-9._-]*`, `.claude/gsd-core/bin/lib/workstream-name-policy.cjs:40,91`), but `GSD_PROJECT` is checked for separators and `..` only (`planning-workspace.cjs:130-136`), so `GSD_PROJECT=p[1]` reaches it: Plan 04's `mergeTomlTable` check (`33-04-PLAN.md:130`) fails, the block stays unmigrated with a notice every run, and its values stop applying because Plan 02 no longer reads the GSD block. Same class as the confirmed C1-7. |
| C2-3 | 07 (05) | `trust-local --revoke` before the first migration leaves the legacy trust record, and the next read carries it into the new store | HIGH | CONFIRMED | `33-07-PLAN.md:200` keeps `--revoke` unchanged and before `cfg_migrate_project`; today it revokes only `trust.revoke_trust(store, real)` for the config path (`cli.py:840-843`, `trust.py:56-75` matches by exact path); the new store is `config-trust/` (D-11, `33-CONTEXT.md:105-106`) and the legacy record lives in `review-spec-trust/` keyed by the old path; the next `migrated` run reads that record and writes a new one (`33-05-PLAN.md:148`). A revoked roster becomes trusted again with no new consent. |
| C2-4 | 09 (07) | Task 3's blanket fixture conversion breaks the migration assertions Plan 07 added | HIGH | CONFIRMED | `33-09-PLAN.md:197` lists every `review-spec.toml`/`[[reviewers]]` line of `tests/test_ai_kit_spec_legacy_config.py` and says no migration test is expected there; Plan 07 makes `test_tracer`, `test_one_note_per_file` and `test_mixed_file_names_only_old_entries` assert the migration (`.migrated` bytes, `migrated {path} to` notices, `33-07-PLAN.md:143-146`) and keeps `test_partial_override`'s user fixture at the old path (`:148`); their fixtures are `tests/test_ai_kit_spec_legacy_config.py:88-89,139-140,152-154,187-188`. Converting them removes the migration they assert; the plan's own escape rule says none applies, so the haiku executor gets contradictory instructions. |
| C2-5 | 10 | The seventh eval breaks `test_skill_evals_have_six_cases`, which the plan's scope runner runs | HIGH | CONFIRMED | `33-10-PLAN.md:171` adds `edge-old-roster-migration-pending` (evals.json holds 6 ids today); `tests/test_ai_kit_spec_check_providers.py:322-325` asserts `len(data["evals"]) == 6` on that file (`:27`); the module is in Plan 10's MODULES (`33-10-PLAN.md:109`); no plan names the test (`rg six_cases` over the phase: no hit). |
| C2-6 | 05 | The SPEC R4 adjacency truth says the equal-lanes (`completed`) path carries trust | LOW | CONFIRMED | `33-05-PLAN.md:31` "(trust carried, old file renamed)" contradicts `:29,148,176` (a completed run never carries trust, C1-10); a verifier reading truths would check the wrong behavior. |
| C2-7 | 10 | The new spec-config description holds `: ` and must be a quoted scalar | LOW | CONFIRMED | The planned text `"Cross-AI lane setup: detects ..."` (`33-10-PLAN.md:114`) as a plain scalar fails `tests/test_skill_frontmatter.py:124-125`; today's description is plain (`skills/ai-kit-spec-config/SKILL.md:3`). The scope runner runs that test, so the failure is caught, but the plan should say to double-quote it. |

#### Current HIGH Concerns (cycle 2)

Single reviewer, so the consensus gate is skipped; each reviewer HIGH counts unless refuted. 4 open, all confirmed
against the plans and source:
- C2-2 (Plans 02, 04): a scope name with `[` or `]` (reachable through `GSD_PROJECT`) cannot be written or read by the
  header regex, so its GSD block never migrates and its values stop applying. Fix: make header recognition quote-aware
  (or refuse such scopes with a named notice) and add a bracketed-scope case.
- C2-3 (Plan 07, with 05): `trust-local --revoke` before the first migration leaves the legacy record, which the next
  migration carries forward. Fix: `--revoke` also revokes the legacy record for the old path (through
  `config_migrate`, D-10), plus a legacy-only trusted roster -> revoke -> resolve test that stays untrusted.
- C2-4 (Plan 09, with 07): Task 3 converts the fixtures of the migration-asserting tests Plan 07 kept. Fix: name
  `test_tracer`, `test_one_note_per_file`, `test_mixed_file_names_only_old_entries` and `test_partial_override` as kept
  migration fixtures (marked) and drop "none is expected here".
- C2-5 (Plan 10): the seventh eval fails `test_skill_evals_have_six_cases`. Fix: add
  tests/test_ai_kit_spec_check_providers.py to Task 3's files and update the count (or assert the eval ids).

C1-5's residual is refuted and not counted; C1-14's rejection is accepted.

#### Current Actionable Non-HIGH Concerns (cycle 2)

4 open, not yet in a plan: C1-11 (Plan 06, MEDIUM) the "only causes of a skip" wording omits an unsupported header name
outside `[runner]`; C2-1 (Plan 01, MEDIUM) a new key under an implicit parent table is never emitted (needs the missing
intermediate block, plus a test); C2-6 (Plan 05, LOW) the adjacency truth at line 31 says a completed run carries trust;
C2-7 (Plan 10, LOW) the new description must be double-quoted.


#### Verification coverage (source-grounding pass, cycle 2)

- Symbol and path sweep: `tmp/auto/r325/conv-33/review-c2/ground.py` (git grep outside `.planning/`, plus path and
  line-range checks) over all twelve revised plans. Every unresolved path or symbol is one the plans create (the same
  set as cycle 1, plus the new test names `test_duplicate_key_row_drops_trust`, `TestConcurrency`,
  `retry-migrate-overwritten`, `test_gsd_config_writes_only_through_allowed_paths`, `py_gsd_write_sites`,
  `js_gsd_write_sites`, `ALLOWED_GSD_WRITES`) or a constant Plan 02 adds and Plan 04 reuses (`TOML_ARRAY_HEADER_RE`,
  `TOML_TABLE_HEADER_RE`, `splitTomlName`, `retryScope`). Every existing helper a fix relies on exists:
  `cfg_read_bytes` and `cfg_parse_toml_bytes` (`config_io.py:329,339`), `cfg_trust_store_dir` (`config_io.py:283`),
  `revoke_trust` (`trust.py:56`). No plan cites a missing existing symbol.
- Ledger check: `tmp/auto/r325/conv-33/review-c2/ledgers.py` and `spot.sh` confirm every Round 1 ledger row has its fix
  in a task action, behavior line or acceptance line (line numbers in the table above).
- Findings: each checked by reading the cited plan lines and source (`cli.py:835-846`, `trust.py:1-75`,
  `config_io.py:283-286`, `cross-ai.mjs:3018-3027`, `tests/test_ai_kit_spec_check_providers.py:27,322-325`,
  `tests/test_ai_kit_spec_legacy_config.py` fixture lines, `tests/test_skill_frontmatter.py:116-128`,
  `skills/ai-kit-spec-config/SKILL.md:3`, gsd-core's `workstream-name-policy.cjs:40,91` and
  `planning-workspace.cjs:130-136`, `33-CONTEXT.md:97-115,127-130`); `check_index_coverage` reported no recorded issue
  for the seven repository source files relied on (the gsd-core files sit outside the index and were read directly).
  4 reviewer HIGHs confirmed (C2-2 narrowed to `GSD_PROJECT`), C1-5's residual refuted, C1-11 and C2-1 confirmed
  MEDIUM, two LOW items (C2-6, C2-7) added from the reviewer's suggestions.
- Not run: the plans themselves, the full test suite, any migration or judge lane.

---

## Cycle 1 review (history, commit 188dd18)

The cycle 1 record below is kept as written; its headings sit one level down.

Review cycle 1, over the twelve plans of commit d0136a2. Reviewer instance `referee-one` (`review.default_reviewers`)
ran through the opencode lane (`review-lane invoke --slug opencode --model router-env/my-referee-one --as referee-one`).
Lane result: `{"slug":"opencode","ok":true,"stubbed":false,"model":{"value":"router-env/my-referee-one","source":"pinned"}}`;
elapsed 1096 s (22:16:54 to 22:35:10 local); stderr empty; one attempt. The prompt (444 KB) carried PROJECT.md
(first 80 lines), the ROADMAP section, the One config design requirements (CFG-01..CFG-06), SPEC, CONTEXT, the locked
decisions note (D-01..D-27 locked; HIGH reserved for gate failures, SPEC or locked-decision breaks, config loss or
unsafe execution), RESEARCH, PATTERNS, VALIDATION, all twelve plans and the ponytail-lens focus line. Plan coverage:
all twelve ids have their own section.

### OpenCode Review (referee-one)

Using the spec-review checklist and Ponytail lens to check all 12 plans against the source, focusing on config safety, executable steps, and missing callers or tests. I won’t modify files.

- **C1-1 — HIGH:** Plan 33-01 explicitly allows changed entries with sub-tables to lose their internal comments (`33-01-PLAN.md:175`), contradicting its lossless-write contract. Parsed-value equality would not catch that loss.
- **C1-2 — HIGH:** The same insertion rule appends every new array entry after the last old entry (`33-01-PLAN.md:175`). Updating `[a, c]` to `[a, b, c]` would produce `[a, c, b]` and fail the plan’s own equality check.

- **C1-3 — MEDIUM:** Plan 33-03’s parity table omits unset and empty `HOME`. Its fallback helpers depend on the ambient process: Python’s `expanduser("~")` and Node’s `os.homedir()` behave differently with `HOME=""`, so the current table does not prove the stated parity.

Source checks found two trust risks: a duplicate project row can change a trusted command’s placeholder without changing the planned digest, and a restarted migration can recreate trust after revocation. I also found commit-boundary failures where readers or tests switch before their writers or imports do.

##### Phase 33 Plan Review

**Framework:** GSD · implementation plans  
**Coverage:** All 12 plans reviewed against the on-disk plans, locked SPEC/CONTEXT decisions, and referenced source. No repository files changed.

#### 33-01

**Summary:** The shared splicer and atomic publisher are necessary foundations. Reusing `cache_write_bytes` is appropriate, but two prescribed array-editing behaviors conflict with lossless, ordered writes.

**Strengths**
- Reuses the existing sibling-temp/rename publisher rather than introducing another Python persistence mechanism (`skills/ai-kit-spec-review/ai_kit_spec/cache.py:27-42`).
- Validation before publication follows the established TOML writer pattern (`tools/config_doctor_appliers.py:69-110`).
- Includes useful interruption, CRLF, symlink, idempotency, and non-vacuity tests.

**Concerns**
- **C1-1 — HIGH — Changed entries with sub-tables deliberately lose comments.** `.planning/phases/33-one-config-design/33-01-PLAN.md:175` directs the executor to re-render the entire entry and explicitly acknowledges losing internal comments. Changing one model field could therefore erase comments around unrelated sub-table fields. Parsed-value equality cannot detect that loss. This contradicts D-08 and CFG-04 (`.planning/phases/33-one-config-design/33-CONTEXT.md:85-89`; `33-SPEC.md:125-128`).
- **C1-2 — HIGH — Inserting an entry between retained entries fails the intended-document check.** The placement algorithm at `.planning/phases/33-one-config-design/33-01-PLAN.md:175` appends all unmatched new groups after the last old group when matched entries retain relative order. Updating `[a, c]` to `[a, b, c]` therefore produces `[a, c, b]`, then raises `SpliceError`. The existing tests cover appending and reordering, but not insertion between retained entries.

**Suggestions**
- Preserve sub-table spans during an entry edit rather than accepting comment loss.
- Add insertion-at-start and insertion-in-middle tests, including interleaved review/execute blocks.

**Risk assessment: HIGH.** These are core writer behaviors inherited by migration and `render-toml`.

#### 33-02

**Summary:** The retry-source switch is well grounded in the existing runner and test harness. The subset parser needs a stronger namespace contract before it becomes the migration verifier.

**Strengths**
- Preserves the existing per-key bounds and fallback loop (`skills/ai-kit-spec-review/references/cross-ai.mjs:3180-3205,3252-3268`).
- Correctly uses `setup(c)` for TOML fixtures: the harness’s `files` map JSON-stringifies its values (`skills/ai-kit-spec-review/references/cross-ai.mjs:5574-5598`).
- Keeping template version 8 is supported by pristine same-version body upgrades (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:282-289`).

**Concerns**
- **C1-4 — HIGH — Duplicate checks do not cover table/value collisions.** The rules at `.planning/phases/33-one-config-design/33-02-PLAN.md:115` reject duplicate explicit headers and duplicate keys within a table, but leave this case unspecified:
  ```toml
  [runner.retry]
  max_retries = 9
  [runner]
  retry = 0
  ```
  Following the prescribed object-building rules can overwrite the constructed retry table and silently use fallback sources. Python’s checked TOML reader rejects such namespace collisions (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:339-352`). The runner must instead return the promised refusal notice.

**Suggestions**
- Specify table/value namespace collision checks in both declaration orders.
- Add refusal cases for scalar-to-table, table-to-scalar, and array-to-table collisions.

**Risk assessment: HIGH until the parser contract is corrected.** Source precedence and harness integration are otherwise sound.

#### 33-03

**Summary:** Aligning user-directory resolution and fixing in-place status-line recovery are justified, bounded changes. The proposed parity suite misses a fallback condition explicitly described by the plan.

**Strengths**
- Fixes a real disagreement: `local_secrets` currently ignores XDG (`skills/ai-kit-spec-review/ai_kit_spec/local_secrets.py:8-9`), while status-line readers accept relative XDG values (`tools/common_config.py:263-274,498-507`).
- Correctly preserves opencode’s separate path rule (`tools/setup.py:122-125`).
- Targets the actual unsafe recovery operation, `shutil.copyfile(sample, cfg)` (`tools/setup.py:3495-3499`), while retaining the backup.

**Concerns**
- **C1-3 — MEDIUM — The parity table does not establish unset/empty-HOME behavior.** `.planning/phases/33-one-config-design/33-03-PLAN.md:96,120-126` tests a relative HOME but not unset or empty HOME. The fallback uses ambient-process helpers: Python’s `expanduser("~")` and Node’s `os.homedir()`. Read-only probes confirmed that, with process `HOME=""`, Python returns `/` while Node returns an empty string on this machine. Consequently, the copies can disagree despite passing every listed parity case. The existing Python fallback is at `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:277-280`.

**Suggestions**
- Add unset and empty HOME cases with controlled account-home lookup in both languages.
- Ensure those tests cannot consult real configuration files when exercising fallback resolution.

**Risk assessment: MEDIUM.** The ordinary absolute-path cases and atomic-recovery change are well specified.

#### 33-04

**Summary:** The migration covers the right sources, scopes, and recovery stages. However, its concurrency and source-retirement algorithms can lose active settings, and several accepted-input cases cannot migrate correctly.

**Strengths**
- Uses sibling temporary files, fsync, mode preservation, realpath publication, and cleanup.
- Retains the existing confinement, regular-file, and size checks (`skills/ai-kit-spec-review/references/cross-ai.mjs:3038-3070`).
- Covers last-key commas, CRLF, symlinks, conflicts, and interrupted publication.

**Concerns**
- **C1-5 — HIGH — The re-read does not prove safe concurrent publication.** `.planning/phases/33-one-config-design/33-04-PLAN.md:122,149` allows two different-scope runners to finish their target re-read before either publishes. Their subsequent unconditional renames can overwrite one another’s scope values and markers, after which both legacy blocks may be removed. The current publisher likewise has unconditional rename semantics (`skills/ai-kit-spec-review/references/cross-ai.mjs:3412-3424`). The “race” case at plan line 187 calls migration sequentially and cannot expose this interleaving. This is an implementation gap against locked D-25, not a request to reopen its no-lock decision.
- **C1-6 — HIGH — Source retirement is not tied to the migrated snapshot.** At `.planning/phases/33-one-config-design/33-04-PLAN.md:122`, step 1 migrates an initial GSD snapshot, but step 2 freshly reads and removes the block then present. If a setting changes between those steps, the newer value is removed without reaching TOML. The user JSON path at line 149 similarly retires a potentially newer snapshot. Removal verification proves only that the newer source lost its block—not that its values were retained.
- **C1-7 — HIGH — The splicer cannot locate every header the parser accepts.** Plan 02 accepts quoted header segments, but `.planning/phases/33-one-config-design/33-04-PLAN.md:121` locates tables by textual equality. Valid `["runner"."retry"]` therefore looks absent when inserting into `runner.retry`; appending `[runner.retry]` creates a duplicate definition and rejects migration. Python’s real TOML parser recognizes these as the same table (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:339-352`).
- **C1-8 — HIGH — Non-fatal UTF-8 decoding can corrupt unrelated bytes.** The planned migration reuses `readOr`, whose implementation reads with Node’s replacement-decoding UTF-8 mode (`skills/ai-kit-spec-review/references/cross-ai.mjs:3357`). An invalid byte in a TOML comment or unrelated JSON string becomes U+FFFD and can be published permanently. This violates the byte-preservation guarantee at `.planning/phases/33-one-config-design/33-04-PLAN.md:26`. Python already refuses invalid UTF-8 explicitly (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:345-348`).

**Suggestions**
- Replace the sequential race proxy with a deterministic overlapping-publication test that preserves both scopes and markers.
- Re-evaluate a source when its bytes change before retirement.
- Use semantic table identity for splicing and fatal UTF-8 decoding for migration inputs.

**Risk assessment: HIGH.** These paths write user configuration and remove the original active settings.

#### 33-05

**Summary:** Separating migration from callers avoids import cycles and makes recovery testable. Publication and trust carry need stronger restart semantics.

**Strengths**
- Keeps old bytes recoverable and compares parsed values before retiring the source (`.planning/phases/33-one-config-design/33-05-PLAN.md:139,163-170`).
- Reuses the existing trust-record key and atomic record writer (`skills/ai-kit-spec-review/ai_kit_spec/trust.py:27-53`).
- Tests trusted/untrusted migration, malformed input, failed publication, failed rename, and purpose mapping.

**Concerns**
- **C1-9 — HIGH — Roster migration omits D-25’s pre-publication re-read.** The algorithm at `.planning/phases/33-one-config-design/33-05-PLAN.md:139` reads the target, constructs appended text, then publishes without checking for a newer target. `cache_write_bytes` replaces it unconditionally (`skills/ai-kit-spec-review/ai_kit_spec/cache.py:27-37`). A runner migration publishing `[runner.retry]` between those operations can be overwritten; the subsequent comparison checks only `lanes` and misses the loss.
- **C1-10 — HIGH — Restarted migration can undo explicit trust revocation.** A failed rename intentionally leaves both files (`.planning/phases/33-one-config-design/33-05-PLAN.md:165-167`). Plan 07 leaves `--revoke` unchanged: it revokes only records for the new path/store (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:840-843`; `trust.py:56-70`). The next “completed” migration can then use the still-valid legacy trust record to recreate the revoked new record under plan line 139. Command eligibility returns without renewed consent.

**Suggestions**
- Add a forced roster/retry publication interleaving test.
- Add failed-rename → revoke → resolve coverage and ensure revocation remains effective across migration restarts.

**Risk assessment: HIGH.** Both concerns affect configuration integrity or command consent.

#### 33-06

**Summary:** Updating retry guidance and its text pins together is the right scope. The documentation should distinguish parsed runner tables from opaque shared-config regions.

**Strengths**
- Keeps documented defaults mechanically tied to the template and preserves bounds/cap assertions (`tests/test_cross_ai_skill_text.py:295-317`).
- Retains the existing upgrade and cross-AI pointers (`tests/test_cross_ai_skill_text.py:183-204`).

**Concerns**
- **C1-11 — MEDIUM — The subset description overstates whole-file restrictions.** `.planning/phases/33-one-config-design/33-06-PLAN.md:96` says a file containing anything outside the listed subset is skipped. Yet Plan 02 deliberately skips lane bodies and other regions as opaque; its positive fixture includes an inline table inside a lane (`33-02-PLAN.md:115,162`). The proposed wording would incorrectly tell users that such shared-config content disables retry settings.

**Suggestions**
- Describe the restrictions on parsed runner regions and explicitly identify the opaque-region exceptions.

**Risk assessment: MEDIUM.** No additional blocking implementation issue found in this documentation plan.

#### 33-07

**Summary:** The role lists plus compatibility view fit the existing consumers. The trust digest does not yet cover every row capable of changing an effective command, and the read-switch commit leaves a writer regression unresolved.

**Strengths**
- The compatibility view matches current quota and superpowers consumers (`skills/ai-kit-spec-review/ai_kit_spec/quota.py:169-173`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py:175-188`).
- Correctly recognizes that project overrides of user command entries must participate in trust (`.planning/phases/33-one-config-design/33-07-PLAN.md:185-187`).
- Specifies distinct role-list tests and read-only legacy inspection.

**Concerns**
- **C1-12 — HIGH — Duplicate project keys bypass the planned digest.** The digest includes explicit command rows and overrides of user command keys, but not another project row overriding a project command row (`.planning/phases/33-one-config-design/33-05-PLAN.md:129`; `33-07-PLAN.md:185-192`). After trusting:
  ```toml
  [[lanes.review]]
  key = "x"
  command = "{tool} --check"
  tool = "safe"
  ```
  adding `key="x", tool="evil"` in another review entry leaves the planned canonical bytes unchanged. The retained merge updates the effective `tool` (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:368-382`), and command rendering substitutes extra fields into argv (`commands.py:111-132`). An in-memory probe against the actual merge confirmed unchanged digest inputs and the effective value changing to `evil`.
- **C1-13 — HIGH — The required read-switch commit leaves its writer/trust test failing.** Plan 07 retains the old writer until Plan 09 (`.planning/phases/33-one-config-design/33-07-PLAN.md:115`) but converts the trust module to the new path. `test_render_toml_out_never_trusts_the_file_it_writes` renders to `cfg_local_path`, then requires an untrusted warning (`tests/test_ai_kit_spec_trust.py:279-294`). The retained writer emits top-level `[[reviewers]]` (`config_io.py:582-640`), which the new reader ignores in `config.toml`; therefore no command-bearing lanes trigger the required warning. Task 1 cannot pass its specified scope without an additional transition step.

**Suggestions**
- Ensure every row that can affect an effective custom command is trusted, or reject ambiguous duplicate keys before merge.
- Test the resulting argv, not only canonical bytes.
- Bridge the writer/trust test in the same buildable read-switch commit.

**Risk assessment: HIGH.** C1-12 is a command-execution trust bypass.

#### 33-08

**Summary:** The factual renames are narrow and preserve the existing consent instructions. The scan wrapper needs correct no-match handling to remain reusable.

**Strengths**
- Preserves the warning prefix and explicit show → consent → trust sequence (`skills/ai-kit-spec-review/references/cross-ai-dispatch.md:191-196`).
- Covers the current references and eval text naming the old roster.

**Concerns**
- **C1-14 — MEDIUM — A successful no-match scan becomes an error.** `.planning/phases/33-one-config-design/33-08-PLAN.md:98` requires failure on any nonzero `git grep` return code. `git grep` returns 1 when no matches exist. Remaining Python mentions may mask this during wave 4, but after their removal the completed-tree scan fails despite `md hits: 0`.

**Suggestions**
- Accept grep return codes 0 and 1; fail only on actual command errors or prohibited Markdown hits.

**Risk assessment: MEDIUM.** The edits themselves are straightforward; the verification command is not reliably repeatable.

#### 33-09

**Summary:** Replacing the full rewrite with surgical writes is necessary, and the plan retains important validation. Its task boundary misses an importer, and malformed-target handling is incomplete.

**Strengths**
- Preserves entry validation, rejection warnings, and dangling-ladder handling from the current writer (`skills/ai-kit-spec-review/ai_kit_spec/config_io.py:609-635`).
- Retains explicit replacement consent from the existing CLI (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:759-764`).
- Adds minimal-diff, unknown-table, idempotency, and interrupted-publication checks.

**Concerns**
- **C1-15 — HIGH — Task 2 removes an API before converting a scope-test importer.** `.planning/phases/33-one-config-design/33-09-PLAN.md:159-170` deletes `cfg_render_toml`, but its prescribed commit omits `tests/test_ai_kit_spec_routing.py`. That module imports the deleted function at line 23 and calls it in `test_render_rejects_route` at lines 706-714. It is included in the inherited scope runner, so Task 2 fails at import. Task 3’s fixture-name lister does not catch the import or JSON call.
- **C1-16 — HIGH — Malformed targets can bypass exit-2 handling.** The algorithm at `.planning/phases/33-one-config-design/33-09-PLAN.md:161` parses the existing target for the replacement guard before entering the renderer’s exception handling. It does not require conversion of malformed TOML or non-UTF-8 reads into `ConfigError`. `cli.main` catches only `ConfigError` (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:1038-1045`); the existing checked parser already provides the necessary conversion (`config_io.py:339-352`).

**Suggestions**
- Convert every importer/caller of the removed API in the deletion commit, preserving route-rejection coverage.
- Use the checked read/parse path before the replacement guard and test malformed/non-UTF-8 targets without adjacent legacy files.

**Risk assessment: HIGH.** The prescribed commit cannot meet its own gate, and the target error contract is incomplete.

#### 33-10

**Summary:** The new reference, role wording, and read-only checks largely match the intended implementation. First-use setup must account for migration creating the roster before the replacement guard runs.

**Strengths**
- Adds `--no-migrate` to the check-only quota probe, preserving the reference’s existing no-persistence intent (`skills/ai-kit-spec-config/references/check-only.md:3-27`).
- Moves the stale-provider fixture and retains generic eval-shape verification (`tests/test_skill_evals_shape.py:27-68,77-94`).

**Concerns**
- **C1-17 — HIGH — Legacy-only setup cannot complete under the specified consent flow.** `.planning/phases/33-one-config-design/33-10-PLAN.md:115,118` treats a target without `[lanes]` as “no roster” and allows `--replace` only after approval for an existing table. But Plan 09 migrates the adjacent legacy roster first, then refuses the newly created `[lanes]` without `--replace` (`33-09-PLAN.md:153,161`). The setup flow therefore reaches refusal rather than completion. The underlying consent requirement is real and must not be bypassed (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:759-764`).
- **C1-18 — MEDIUM — “Nothing was written” is inaccurate after migration.** The prescribed statement at `.planning/phases/33-one-config-design/33-10-PLAN.md:119` is false for the preceding case: migration has written `config.toml` and retired the old roster before the requested replacement is refused.

**Suggestions**
- Detect a pending legacy roster during target selection, or migrate and repeat the explicit replacement-consent gate.
- Report “the requested replacement was not written,” separately naming migration side effects.

**Risk assessment: HIGH.** First-use migration is a central acceptance path, not an unusual edge.

#### 33-11

**Summary:** The inventory, assignments, README, and complete test gate provide useful closure. The foreign-schema test is materially narrower than locked D-17.

**Strengths**
- Collects paths from code rather than relying on files existing on the current machine.
- Includes assignment and scan non-vacuity checks.
- Recognizes the legitimate verbatim backup-restore path, which uses `_atomic_copy` (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/config_backup.py:148-153`).

**Concerns**
- **C1-19 — HIGH — Identifier scans do not enforce the required foreign-write boundary.** `.planning/phases/33-one-config-design/33-11-PLAN.md:179-181` bans the literal `cross_ai_retry` in Python and restricts its enclosing runner functions. It never inspects writes to GSD configuration. A direct write of a different unknown GSD key passes every specified check. Locked D-17 explicitly requires scanning writes to `.planning/**/config.json` and rejecting unauthorized write paths (`.planning/phases/33-one-config-design/33-CONTEXT.md:140-145`).

**Suggestions**
- Add the required write-boundary check, with a synthetic direct write of another unknown key proving the check fails.
- Keep the documented `config-set`, legacy-block removal, and verbatim backup-restore exceptions narrowly identified.

**Risk assessment: HIGH.** The current gate would claim CFG-06 evidence without testing the required boundary.

#### 33-12

**Summary:** The judge loop is grounded in existing drivers and the real judge tool. Its pool selection, frozen-tree discipline, substitution recording, and regression checks are appropriate.

**Strengths**
- The planned driver substitutions match the existing pool invocation (`tmp/judge-32.4/lanes.py:379-383`).
- The no-native pool really selects the first two usable judges and permits one usable judge (`tools/judge_loop.py:1520-1549`).
- Regression comparison is computed by the existing tool, not manually (`tools/judge_loop.py:1619-1636`).
- The copied bar driver performs a gated check and records unmet skills (`tmp/judge-32.4/bar_table.py:77-122`).

**Concerns**
- No additional source-backed blocking concern identified. External judge availability and successful verdict ingestion remain execution-time evidence.

**Suggestions**
- Retain the explicit judged set and frozen-tree checks.
- Do not treat structurally valid records as proof that the skill bar passed; preserve the final gated check and unmet-results handling.

**Risk assessment: MEDIUM.** Operationally expensive, but the inspected mechanisms support the plan.

#### Cross-plan assessment

**Recommendation: Revise before execution.**

The phase’s architecture follows the owner’s decisions: neutral layered configuration, role-keyed lanes, separate state, built-in-only runtimes, and automatic migrations. The blockers are in implementation details and task boundaries—not the chosen design.

Prioritize fixes in this order:

1. **Command consent:** C1-12’s duplicate-row trust bypass and C1-10’s revocation resurrection.
2. **Configuration retention:** C1-5, C1-6, C1-8, and C1-9.
3. **Lossless and executable writers:** C1-1, C1-2, C1-7, and C1-16.
4. **Buildable transition commits:** C1-13 and C1-15.
5. **Complete first-use flow and evidence:** C1-17 and C1-19.

From the Ponytail perspective, no new dependency or broader redesign is needed. Reuse the checked parser, atomic publishers, existing fakes, and judge machinery. Spend the additional code on deterministic failure/interleaving tests rather than more narrative assertions of safety.

##### Status: Issues Found — fix and re-invoke

Skipped full-suite execution, actual migrations, installer runs, and external judge lanes; verification used source inspection and small in-memory probes.  
Primary risk: implementing the plans verbatim can lose configuration or make an altered custom command eligible without renewed trust.


---

### Consensus Summary

One reviewer ran (`referee-one`), so there is no cross-reviewer agreement to report; the consensus gate does not
engage and every HIGH from this reviewer counts. The review cites `file:line` evidence throughout, ran small
read-only probes, and carries no evidence-quality discount marker. The orchestrator checked each finding against
the plans and the source (table below).

#### Agreed Strengths
- (single reviewer) The architecture follows the owner's decisions: one neutral `config.toml` per layer, role-keyed
  lanes, separate state files, stdlib and node built-ins only, automatic migrations. Plans reuse `cache_write_bytes`,
  the existing TOML writer pattern, the runner's confinement and size checks, the trust record helpers and the
  loop 32.4 judge drivers. Plan 33-12 (judge loop) has no blocking concern.

#### Agreed Concerns
- None (one reviewer). The reviewer's priority order: command consent (C1-12, C1-10), config retention (C1-5,
  C1-6, C1-8, C1-9), lossless and executable writers (C1-1, C1-2, C1-7, C1-16), buildable transition commits
  (C1-13, C1-15), first-use flow and the foreign-write evidence (C1-17, C1-19).

#### Divergent Views
- None (one reviewer).

#### Source check of the findings (orchestrator, 2026-11-14)

| # | Plan | Finding | Severity | Verdict | Evidence |
|---|------|---------|----------|---------|----------|
| C1-1 | 01 | A changed `[[...]]` entry with sub-table headers is re-rendered whole, losing comments inside it | HIGH | CONFIRMED | `33-01-PLAN.md:175` prescribes the re-render and a `# shortcut:` comment admitting the loss; SPEC R9 (`33-SPEC.md:125-128`) and D-08 (`33-CONTEXT.md:85-89`) keep comments outside the changed lines. |
| C1-2 | 01 | Inserting a new entry between kept entries lands it after the last old group, so the result order differs and the equality check raises | HIGH | CONFIRMED | `33-01-PLAN.md:175` placement rule: when matched groups keep relative order, new groups go "right after the last old group's last line"; `[a, c]` -> `[a, b, c]` gives `[a, c, b]`, `tomllib` keeps array order, so `SpliceError`. Role order is the priority order (Plan 10), so a wizard inserting a mid-priority lane hits it. |
| C1-3 | 03 | The parity table has no unset or empty HOME case, where the copies use different fallbacks | MEDIUM | CONFIRMED | `33-03-PLAN.md:96` lists seven cases, none with HOME unset or `""`; the copies fall back through `os.path.expanduser("~")` (`:122`, `:124`, `:155`) and the runner through Node; Python's `expanduser` with `HOME=""` returns `/`. |
| C1-4 | 02 | The subset parser's duplicate rules miss table/value collisions (`[runner.retry]` then `[runner]` `retry = 0`, or the reverse) | HIGH | CONFIRMED | `33-02-PLAN.md:115` rejects a table defined twice and a key set twice by key lines only; the first order overwrites the built table with `0` and resolveRetry silently falls to the next source, the reverse order sets keys on a number (a TypeError in a strict ES module). Python's checked reader rejects both (`config_io.py:339-352`). |
| C1-5 | 04 | Two runners migrating different scopes can both pass the re-read and overwrite each other's publish, then both retire their GSD blocks | HIGH | CONFIRMED (narrow window) | `33-04-PLAN.md:122` re-reads before publishing (D-25) but retires the source in step 2 without checking the published values survived; `writeCycleState`-style rename is unconditional (`cross-ai.mjs:3412`); the race case (`:187`) runs sequentially. A post-publish re-read before step 2 fits D-25 (no lock). |
| C1-6 | 04 | Step 2 retires the block it reads fresh, not the snapshot migrated in step 1 | HIGH | CONFIRMED (narrow window) | `33-04-PLAN.md:122` step 2 is `removeRetryBlock(readOr(realpath of file))`; a block edited between steps 1 and 2 is removed without reaching TOML; the user JSON path (`:149`) renames whatever file is there. |
| C1-7 | 04 | `upsertTomlKeys` finds a header by text, but the parser accepts quoted segments, so `["runner"."retry"]` reads as absent and the append makes a duplicate table | HIGH | CONFIRMED (fails closed) | `33-04-PLAN.md:121` header match is textual; `33-02-PLAN.md:115` accepts quoted segments. Outcome: the merge does not verify, a notice prints each run and the GSD block's values are no longer applied (Plan 02 stops reading the block). |
| C1-8 | 04 | Migration reads with replacement UTF-8 decoding, so an invalid byte becomes U+FFFD and is published | HIGH | CONFIRMED | `readOr` is `fs.readFileSync(p, 'utf8')` (`cross-ai.mjs:3357`), which replaces invalid sequences; Plan 04 feeds it to `removeRetryBlock` and the TOML upsert, against its own "every other byte kept" truth (`33-04-PLAN.md:26`). Python refuses invalid UTF-8 (`config_io.py:345-348`). |
| C1-9 | 05 | Roster migration publishes without D-25's pre-publish re-read and its post-check compares only `lanes` | HIGH | CONFIRMED | `33-05-PLAN.md:139` reads the target once, publishes via `toml_splice.publish` (unconditional replace, `cache.py:27-37`), then re-reads and compares `lanes` only, so a concurrent `[runner.retry]` publish can be lost unseen; D-25 (`33-CONTEXT.md:188-191`) says both migrations re-read before publishing. |
| C1-10 | 05 | After a failed rename, `trust-local --revoke` on the new file is undone by the next "completed" run from the still-valid legacy trust | HIGH | CONFIRMED (needs a failed rename) | `33-05-PLAN.md:139` carries trust on every run that reaches the trust step, including "completed"; the failed-rename path keeps the old file (`:165-167`); `--revoke` removes records for the new realpath only (`cli.py:840-843`). |
| C1-11 | 06 | The doc says a file holding anything outside the subset is skipped, but Plan 02 skips non-runner regions as opaque | MEDIUM | CONFIRMED | `33-06-PLAN.md:96` "skips a file holding anything else with one notice"; `33-02-PLAN.md:115,162` parses only `[runner*]` and accepts an inline table inside a lane. |
| C1-12 | 07 | A second project row with the same `key` and no `command` changes an effective command's fields without changing the trust digest | HIGH | CONFIRMED | The digest covers rows with `command` plus overrides of user command keys (`33-07-PLAN.md:185-186`, `33-05-PLAN.md:129`); `cfg_merge_reviewers` updates `by_key[key]` from every later local row (`config_io.py:368-371`); `render_reviewer_command` fills placeholders from the entry's extra fields (`commands.py:111-132`). Today byte-pinned trust blocks this; D-11's digest opens it. |
| C1-13 | 07 | Task 1 converts the trust module whole, but `test_render_toml_out_never_trusts_the_file_it_writes` writes through the old writer to the new path and no conversion rule fits | HIGH | CONFIRMED | `tests/test_ai_kit_spec_trust.py:279-294` runs `render-toml --out cfg_local_path` and expects the `trust-local` warning; Plan 07 keeps the old writer (`33-07-PLAN.md:115`), whose `[[reviewers]]` the new reader ignores, so no command lane warns; rules 1-7 (`:117-124`) do not cover a CLI-written fixture; Plan 09 Task 2 converts it later (`33-09-PLAN.md:147,163`). The analogous test gets `legacy_path` at `33-07-PLAN.md:132`. |
| C1-14 | 08 | The scan exits 1 when `git grep` finds no match | MEDIUM | REFUTED (latent only) | `33-08-PLAN.md:98` does exit 1 on any non-zero rc, but the grep covers `skills/ai-kit-spec-review`, where `config_migrate.py` (Plan 05, wave 3, before Plan 08's wave 4) always holds `LEGACY_NAME = "review-spec.toml"` (D-10), so rc is 0 at every point the scan runs. Not counted. |
| C1-15 | 09 | Task 2 deletes `cfg_render_toml` but its commit leaves `tests/test_ai_kit_spec_routing.py` importing it | HIGH | CONFIRMED | `tests/test_ai_kit_spec_routing.py:23` imports `cfg_render_toml`, used at `:710`; Task 2's files (`33-09-PLAN.md:142`) omit it; its scope runner (`:122`, a copy of Plan 07's MODULES, which list `tests.test_ai_kit_spec_routing`) fails at import, and Task 2's own acceptance `rg -n "cfg_render_toml" skills tests` prints nothing (`:172`) cannot hold. |
| C1-16 | 09 | The `[lanes]` replacement guard parses the target before any error mapping, so a malformed or non-UTF-8 target escapes as a traceback, not exit 2 | HIGH | CONFIRMED | `33-09-PLAN.md:161` reads and parses `existing` before the `try` around `cfg_render_lanes`; `cli.main` maps only `ConfigError` to exit 2 (`cli.py:1038-1045`); SPEC constraint: a broken config.toml stops the CLIs with exit 2. |
| C1-17 | 10 | With only a legacy `review-spec.toml` beside the target, the wizard sees no roster, passes no `--replace`, render-toml migrates first and then refuses the new `[lanes]` | HIGH | CONFIRMED | `33-10-PLAN.md:115` (Step 2.1 counts a config.toml without `[lanes]` as no roster; `--replace` only for an existing `[lanes]`, repeated in Step 3 at `:118`); `33-09-PLAN.md:161` migrates via `cfg_migrate_target` before the guard. |
| C1-18 | 10 | "a `refusing to replace` line means nothing was written" is false after that migration | MEDIUM | CONFIRMED | `33-10-PLAN.md:119` Step 4 sentence; the migration in `33-09-PLAN.md:161` has already written `config.toml` and renamed the old file. |
| C1-19 | 11 | The foreign-key test bans the literal `cross_ai_retry` but never scans writes to `.planning/**/config.json`, which locked D-17 requires | HIGH | CONFIRMED | `33-11-PLAN.md:33,179-181` (static identifier scan only); D-17 (`33-CONTEXT.md:140-145`): "A test scans ai-kit's Python and the runner template for writes to `.planning/**/config.json` and fails on any path other than `gsd-tools config-set` and the block removal". The plan narrows a locked decision. |

#### Current HIGH Concerns (cycle 1)

Single reviewer, so the consensus gate is skipped and every reviewer HIGH counts. 15 open, all confirmed against
the plans and source:
- C1-1 (Plan 01): a changed entry with sub-tables is re-rendered whole and loses its comments.
- C1-2 (Plan 01): inserting an entry between kept entries puts it last and raises SpliceError.
- C1-4 (Plan 02): the subset parser misses table/value collisions in both orders.
- C1-5 (Plan 04): concurrent different-scope migrations can overwrite each other and still retire both blocks.
- C1-6 (Plan 04): step 2 retires a freshly read block, not the migrated snapshot.
- C1-7 (Plan 04): textual header matching misses quoted headers the parser accepts.
- C1-8 (Plan 04): replacement UTF-8 decoding can publish U+FFFD over invalid bytes.
- C1-9 (Plan 05): roster migration lacks D-25's pre-publish re-read; its post-check compares only `lanes`.
- C1-10 (Plan 05): a revoked trust is recreated from the legacy record after a failed rename.
- C1-12 (Plan 07): a duplicate-key project row changes an effective command without changing the trust digest.
- C1-13 (Plan 07): the trust module's render-toml test fails in Task 1 with no conversion rule for it.
- C1-15 (Plan 09): Task 2 deletes `cfg_render_toml` while the routing test still imports it.
- C1-16 (Plan 09): a malformed or non-UTF-8 target escapes the exit-2 mapping in render-toml.
- C1-17 (Plan 10): legacy-only first-use setup migrates, then refuses its own write.
- C1-19 (Plan 11): the foreign-key test does not scan writes to GSD config files as D-17 requires.

#### Current Actionable Non-HIGH Concerns (cycle 1)

3 open, not yet in a plan: C1-3 (Plan 03) parity cases for unset and empty HOME; C1-11 (Plan 06) the subset
wording overstates whole-file skipping; C1-18 (Plan 10) "nothing was written" is false after migration.
C1-14 is refuted (latent only) and not counted.


#### Verification coverage (source-grounding pass)

- Symbol and path sweep: `tmp/auto/r325/conv-33/review-c1/ground.py` (git grep outside `.planning/`, plus path and
  line-range checks) over all twelve plans. Every unresolved path or symbol is one the plans create (`toml_splice.py`,
  `config_migrate.py`, `tests/test_toml_splice.py`, `tests/test_config_migrate.py`, `tests/test_config_layers.py`,
  `tests/test_config_dir_parity.py`, `tests/test_config_design_record.py`, `tests/test_config_callers.py`,
  `docs/config/design.md`, `references/config-file.md`, the `cfg_*` helpers, the runner's `parseTomlSubset`,
  `readTomlSubset`, `tomlValueText`, `upsertTomlKeys`, `migrateRetrySources`, `writeCaseFile`) or a test class
  they add; the base commit `ab06802` exists. No plan cites a missing existing symbol.
- Findings: each checked by reading the cited plan lines and source (`config_io.py:339-352,360-382`,
  `cli.py:835-846,1037-1045`, `commands.py:111-132`, `cross-ai.mjs:3357,3412`,
  `tests/test_ai_kit_spec_trust.py:279-294`, `tests/test_ai_kit_spec_routing.py:23,710`, `33-CONTEXT.md:85-197`);
  `check_index_coverage` reported no recorded issue for the six source files relied on. 18 of 19 confirmed, C1-14
  refuted (latent only).
- Not run: the plans themselves, the full test suite, any migration or judge lane.

## Convergence Outcome

The loop hit its 3-cycle cap. The cycle 3 findings were applied without another cross-AI review.

- **Cycles:** 3 of 3, the workflow maximum.
- **Unresolved concerns per cycle:**
  - Cycle 1 (188dd18): 18, of which 15 HIGH and 3 actionable. C1-14 was refuted.
  - Cycle 2 (90801f2): 8, of which 4 HIGH and 4 actionable.
  - Cycle 3 (19190dc): 6, of which 1 HIGH and 5 actionable.
  - The count fell every cycle, so the loop never stalled. Open plan-revision conflicts were 0 in every cycle.
- **Decision (coordinator, 2026-11-15, following the 32.5 precedent):** one narrow planner pass for C3-1..C3-6, checked by a reviews-mode plan-checker run, with no fourth review cycle. Each fix is recorded in its plan's Review Dispositions Ledger, under Round 3 — 19190dc:
  - C3-5: plan 09's fixture for the one-line diff test carries the generated ladder comment block.
  - C3-1: plan 01's `split_blocks` raises a SpliceError that names the line.
  - C3-2: plan 02's `mine` scope mode is mandatory.
  - C3-4: plan 11's README migration wording is corrected.
  - C3-6: plan 12's `substitute.py` waits for the quota reset.
  - C3-3: the plan 04 threat model (T-33-11) records the accepted residual risk.
- **What checked the fix pass:** one plan-checker run, not a cross-AI review.
