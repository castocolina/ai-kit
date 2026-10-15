---
phase: 18
reviewers: [opencode-plan-review]
reviewed_at: 2026-10-15T18:48:11Z
plans_reviewed: [18-01-PLAN.md, 18-02-PLAN.md, 18-03-PLAN.md, 18-04-PLAN.md, 18-05-PLAN.md, 18-06-PLAN.md, 18-07-PLAN.md, 18-08-PLAN.md, 18-09-PLAN.md, 18-10-PLAN.md, 18-11-PLAN.md, 18-12-PLAN.md, 18-13-PLAN.md, 18-14-PLAN.md, 18-15-PLAN.md, 18-16-PLAN.md, 18-17-PLAN.md, 18-18-PLAN.md, 18-19-PLAN.md, 18-20-PLAN.md, 18-21-PLAN.md, 18-22-PLAN.md]
models:
  opencode-plan-review: "router-env/my-plan-review"
model_sources:
  opencode-plan-review: "pinned"
---

# Cross-AI Plan Review — Phase 18

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review (opencode-plan-review)

### Reviewer report: Phase 18 Plan Review

**Framework:** GSD · implementation plans  
**Coverage:** All **22 plans**, 18-01 through 18-22, read from disk and reviewed against referenced source in this checkout.  
**Method:** Read-only source inspection, with independent reviews of selection, runner, and apply subsystems. No repository files changed.

For readable citations, these prefixes identify exact repository directories:

- **P/** — `.planning/phases/18-cross-ai-skills-apply-pipeline/`
- **C/** — `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/`
- **S/** — `skills/ai-kit-spec-review/ai_kit_spec/`
- **G/** — `.claude/gsd-core/bin/lib/`

## 18-01

**Summary:** Good shared groundwork, but enumeration failure semantics and strict JSON encoding need tightening.

**Strengths**
- The tracer proves RPC discovery reaches the catalog and curated candidate join, rather than testing the parser alone (`P/18-01-PLAN.md:168–224`).
- Keeping the v1 writer unchanged limits compatibility risk.

**Concerns**
- **MEDIUM:** Exit-zero malformed RPC output becomes `models: []`. The parser returns `[]` for invalid envelopes, and detection accepts that result as a successful listing (`P/18-01-PLAN.md:196–199,248`). This loses the promised distinction between failed enumeration and a genuinely empty list.
- **MEDIUM:** Container serialization permits nested NaN/Infinity and can raise `TypeError`, although the wrapper promises clean refusals (`P/18-01-PLAN.md:147–151,283–296`).

**Suggestions**
- Validate the successful response envelope separately; reserve `None` for unusable responses.
- Use `allow_nan=False` and convert nested serialization failures into key-naming `ValueError`s.

**Risk Assessment:** **MEDIUM** — bounded changes, but these are shared trust-boundary helpers.

## 18-02

**Summary:** The registry-driven inventory extension is appropriate; loading externally edited inventory needs stronger validation.

**Strengths**
- Roots come from gsd-core’s actual resolver, including descriptor overrides (`G/runtime-homes.cjs:491–519`).
- Excluding HOME-derived roots from committed fixtures preserves portability (`P/18-02-PLAN.md:210–214`).

**Concerns**
- **MEDIUM:** The loader requires a lane’s string `slug`, but not correctly typed `binary`, model/effort keys, or root values (`P/18-02-PLAN.md:186–189`). Later selectors consume these fields directly (`P/18-06-PLAN.md:143–168`).
- **LOW:** Root discovery failure becomes `{}` without the warning promised by the task’s completion statement (`P/18-02-PLAN.md:178–183,304`).

**Suggestions**
- Validate all six lane fields and roots at the inventory-file boundary.
- Distinguish unavailable discovery from a legitimately empty skills installation.

**Risk Assessment:** **MEDIUM** — malformed data otherwise reaches downstream pure functions.

## 18-03

**Summary:** Strong inventory coverage, with a consequential mismatch between scanner containment and gsd-core containment.

**Strengths**
- Plugin scope, layered enablement, duplicate roots, deterministic ordering, and credential sentinels receive explicit tests.
- Backend detection clearly labels reachability rather than verified service identity.

**Concerns**
- **MEDIUM:** Escape detection resolves the skill directory (`P/18-03-PLAN.md:158–163`), while gsd-core checks the actual `SKILL.md` path (`G/init.cjs:3691–3701`). An in-root directory containing an escaping `SKILL.md` symlink is misclassified.
- **MEDIUM:** Task 1 says unreadable skill files cause entry omission; Task 2 expects the entry retained with an empty description (`P/18-03-PLAN.md:204–208,255`).

**Suggestions**
- Check resolved skill-file containment.
- Define one consistent unreadable-file policy and test it.

**Risk Assessment:** **MEDIUM** — inaccurate inventory can recommend skills gsd-core subsequently rejects.

## 18-04

**Summary:** The artifact structure is sensible, but Task 1 cannot pass its prescribed verification as ordered.

**Strengths**
- Runner settings have one authoritative artifact representation.
- Schema pins and golden changes accompany the behavior change (`P/18-04-PLAN.md:188–224`).

**Concerns**
- **HIGH:** Task 1 imports `.cross_ai` and runs the entire recommendation suite; the required purity-allowlist update waits until Task 2 (`P/18-04-PLAN.md:188,227,251`). The existing guard explicitly rejects that import (`tests/test_curated_config_recommend.py:1720,1733–1740`).

**Suggestions**
- Move the allowlist and inspected-module additions into Task 1, alongside the new import. Additional non-vacuity tests can remain in Task 2.

**Risk Assessment:** **HIGH** — this is a deterministic execution-order blocker, not a hypothetical regression.

## 18-05

**Summary:** Useful selection-edge coverage with one overstated verification claim.

**Strengths**
- Tests cover host exclusion, preference ordering, router priority, price ceilings, and explicit installation state (`P/18-05-PLAN.md:159–167`).

**Concerns**
- **LOW:** The plan claims interruption preserves the old plan, but its concurrency case tests only repeated pure builds and input immutability (`P/18-05-PLAN.md:33,167`). Existing normal-write coverage does not inject a replacement failure (`tests/test_curated_config_recommend.py:1825–1833`).

**Suggestions**
- Either narrow the claim to determinism or add a small injected failure-before-replace test.

**Risk Assessment:** **LOW** — selection coverage is good; the gap concerns evidence precision.

## 18-06

**Summary:** Review selection is detailed and mostly executable, but host exclusion should follow executable identity.

**Strengths**
- Registry-verbatim keys, full-precision ranking, explicit router exemption, and rigorous second-lane re-selection are clearly defined (`P/18-06-PLAN.md:143–168`).

**Concerns**
- **MEDIUM:** Eligibility excludes the host by lane slug and candidate `is_host`. An extensible registry can expose another slug using the host binary. The codebase already distinguishes host `cursor` from executable runtime `cursor-agent` (`C/host.py:37–39`).

**Suggestions**
- Also reject a lane whose binary equals the host’s mapped runtime.
- Test an alternate registry slug pointing to the host executable.

**Risk Assessment:** **MEDIUM** — the hard “another CLI” guarantee should not depend on registry naming or editable candidate flags.

## 18-07

**Summary:** A well-contained pure affinity layer; no blocking design issue found in this plan.

**Strengths**
- Explicit file-order caps, installed/addressable filtering, and missing-skill silence make resolution predictable.
- The additional shipped-affinity read is narrowly allowed in the CLI I/O test (`P/18-07-PLAN.md:199–216`).

**Concerns**
- **LOW:** Malformed `when` tests cover an unknown gate but not list/dict values (`P/18-07-PLAN.md:162–164,256`). Membership implementations can throw on unhashable inputs rather than return validation errors.

**Suggestions**
- Add non-string `when` cases and require clean loader diagnostics.
- Preserve the distinction between Claude-only plugin visibility and global roots shared by other runtimes.

**Risk Assessment:** **LOW** — clear responsibility boundaries and modest new policy.

## 18-08

**Summary:** Explicit trust approval is good, but partial existing trust and project escapes need defined handling.

**Strengths**
- Per-skill roots avoid unnecessarily broad approvals.
- Outside-HOME exclusion is correctly scoped to escaping global skills (`P/18-08-PLAN.md:125–129`).

**Concerns**
- **MEDIUM:** The replacement-list proposal does not clearly preserve existing roots or recognize already trusted canonical ancestors (`P/18-08-PLAN.md:131–136`). gsd-core canonicalizes roots and accepts descendants (`G/security.cjs:199–215`).
- **MEDIUM:** Project skills remain preferred even when their resolved files escape the project; gsd-core rejects such references (`G/init.cjs:3718–3721`).

**Suggestions**
- Test one existing root plus one newly required root, preserving unrelated approvals.
- Filter project copies by project containment before preferring them over usable global/plugin copies.

**Risk Assessment:** **MEDIUM** — otherwise recommendations can revoke trust or select unloadable skills.

## 18-09

**Summary:** The hermetic harness is a strong foundation, but its state isolation and replacement coverage are incomplete.

**Strengths**
- Fake-only PATH and scratch HOME prevent model spend and real-config access (`P/18-09-PLAN.md:160–181`).
- Keeping Python as a launcher avoids duplicate fake-runtime implementations.

**Concerns**
- **MEDIUM:** All cases share `calls.log` without specified clearing (`P/18-09-PLAN.md:164–179`). Later tests require an empty log or absence of previously invoked CLIs.
- **MEDIUM:** Deleting the old self-test removes runtime-flag and Cursor/OpenCode parsing checks (`.planning/scripts/cross-ai.mjs:413–435`) without equivalent coverage for all supported runtimes.

**Suggestions**
- Give each case its own log/state.
- Replace valuable existing assertions with black-box OpenCode/Codex output and structured-error cases.

**Risk Assessment:** **MEDIUM** — a passing harness otherwise offers uneven runtime confidence.

## 18-10

**Summary:** Correct safety goals, but child cleanup and Git operations can defeat the supervision contract.

**Strengths**
- Content snapshots catch re-edits that porcelain misses.
- The quoted-error-answer case directly tests the classification regression (`P/18-10-PLAN.md:117–124,153–159`).

**Concerns**
- **HIGH:** Cleanup waits for child `close` (`P/18-10-PLAN.md:202–205`). A departed parent’s grandchild can retain output pipes, preventing `close`; the existing runner resolves there (`.planning/scripts/cross-ai.mjs:305–310`).
- **HIGH:** Synchronous Git snapshot commands have no specified timeout (`P/18-10-PLAN.md:121–124`). Filters or slow filesystems can block timers and final status emission.

**Suggestions**
- Initiate cleanup on `exit`, with bounded pipe draining and one finalization path.
- Bound every Git operation by the shared remaining budget; test inherited-pipe grandchildren and a hanging filter.

**Risk Assessment:** **HIGH** — these gaps can prevent both cleanup and the promised final status line.

## 18-11

**Summary:** Preflight semantics are clear, but timing and retries need lifecycle-level safety.

**Strengths**
- Positive model absence is distinguished from listing unavailability.
- `--print-argv` explicitly runs no listing or CLI (`P/18-11-PLAN.md:108–115,135–141`).

**Concerns**
- **HIGH:** Fixed 15-second synchronous listing can exceed a two- or five-second remaining budget and block signal/timer callbacks.
- **HIGH:** Retaining the prototype retry loop permits another attempt before Git safety checks; retries are inside `runCli`, while state checking is outside it (`.planning/scripts/cross-ai.mjs:324–342,396–402`).
- **MEDIUM:** The “no edit” flaky attempt writes its counter inside the snapshotted repository (`P/18-11-PLAN.md:121–123`).

**Suggestions**
- Supervise listing processes with `min(15s, remaining budget)`.
- Check state after every attempt; stop review writes immediately and define safe exec-resume behavior.
- Keep fake counters outside repositories.

**Risk Assessment:** **HIGH**.

## 18-12

**Summary:** The review and timeout contracts need stronger failure semantics than arithmetic-only tests provide.

**Strengths**
- Commit and non-commit review violations are both covered.
- Claude read-only enforcement is honestly labelled unverified (`P/18-12-PLAN.md:124–127,143`).

**Concerns**
- **HIGH:** “Any change, otherwise answer rules” does not explicitly reject unknown before/after Git snapshots (`P/18-12-PLAN.md:148–150`). Unknown is not proof of unchanged.
- **HIGH:** `--print-argv` formula tests do not prove completion before outer kill (`P/18-12-PLAN.md:176–180,230–232`), especially with listing, Git, backoff, and cleanup overhead.

**Suggestions**
- Require valid snapshots for review success; detected writes must override other outcomes.
- Define one absolute lifecycle deadline and test hanging preflight, slow Git, and resistant descendants against elapsed time.

**Risk Assessment:** **HIGH**.

## 18-13

**Summary:** Deterministic rendering is well specified, but edit protection has a plan/write race.

**Strengths**
- Raw-byte hashes, trailing-newline edits, CRLF, and synthetic dogfood-state tests are appropriate (`P/18-13-PLAN.md:205–216`).
- Reusing a shared bytes writer avoids duplicate atomic-write machinery.

**Concerns**
- **HIGH:** `plan_script` classifies the file, then `write_script` trusts that earlier decision (`P/18-13-PLAN.md:139–143`). A file edited or created between those calls can be overwritten.

**Suggestions**
- Carry expected original identity/bytes and revalidate at publication; on mismatch, refuse or produce `.new`.
- Add intervening-edit and intervening-create tests, and document any residual concurrency limitation.

**Risk Assessment:** **HIGH** — the current tests can pass while user edits are still lost.

## 18-14

**Summary:** Good CLI refusal rules, but the plan-file loader is too shallow to enforce them at apply time.

**Strengths**
- Forceable and non-forceable checks are explicitly separated.
- Refusals must preserve plan bytes (`P/18-14-PLAN.md:87–93,229–240`).

**Concerns**
- **HIGH:** `load_plan` validates an envelope, not the executable schema (`P/18-14-PLAN.md:145–148`). Missing set values, duplicate keys, unsupported hosts, and malformed or unconstrained artifacts can bypass editor checks.

**Suggestions**
- Define one complete schema-2 validator shared by editing, apply, and follow-ups.
- Constrain supported artifact kind/path/config and test malformed nested input before any write.

**Risk Assessment:** **HIGH** — plans are user-editable inputs driving executable artifacts and configuration.

## 18-15

**Summary:** Single-path pseudo-key editing is good, but generic unset can leave inconsistent execution dependencies.

**Strengths**
- One target-set operation and explicit artifact/command status synchronization reduce ambiguity (`P/18-15-PLAN.md:125–137`).

**Concerns**
- **MEDIUM:** Only timeout unset is protected while execution is enabled. Generic unset can keep an absent/stale command or restore a different existing execution value without reconciling dependent entries (`P/18-15-PLAN.md:55–61,139–141`).

**Suggestions**
- Validate effective execution/command/timeout/artifact invariants after every set and unset.
- Add command-unset and execution-unset cases, not just explicit false toggles.

**Risk Assessment:** **MEDIUM** — inconsistent plans may pass choice checks but fail when GSD executes them.

## 18-16

**Summary:** Backup publication is careful; transaction ownership is not yet exclusive.

**Strengths**
- Exclusive backup naming, numeric collision ordering, and mode-preserving restoration are explicit (`P/18-16-PLAN.md:134–142,164–168`).

**Concerns**
- **HIGH:** Checking marker absence and later atomically replacing the marker is not exclusive acquisition (`P/18-16-PLAN.md:118–120`; `P/18-18-PLAN.md:183–186`). Two applies can both proceed and interleave writes.
- **MEDIUM:** Byte-only backup reuse can restore an older, broader mode after a permission-only change.

**Suggestions**
- Acquire transaction ownership exclusively before reading/backing up mutable config.
- Require both bytes and mode equality for reuse; test simultaneous contenders and chmod-only changes.

**Risk Assessment:** **HIGH** — backup-name uniqueness does not serialize configuration transactions.

## 18-17

**Summary:** Live diffing is correct, but digest pairing does not identify the intended destination.

**Strengths**
- Shared skill translation makes the dry-run show actual written reference forms (`P/18-17-PLAN.md:155–160`).
- Read-only validation avoids unsafe simulated config writes.

**Concerns**
- **HIGH:** `load_inputs` checks the inventory digest and that the destination is a directory, but not that it is the inventory’s project/workstream (`P/18-17-PLAN.md:137–147`). Inventory already records its resolved config path (`C/inventory.py:91–103,350–365`).

**Suggestions**
- Bind plan/inventory to canonical project and resolved configuration identity.
- Refuse project-A→project-B and same-project/different-workstream applications before backup or rendering.

**Risk Assessment:** **HIGH** — a valid pair can otherwise configure the wrong destination.

## 18-18

**Summary:** The main transaction needs two additional rollback guarantees.

**Strengths**
- Real gsd-tools integration, sequential writes, and post-write skill warnings are appropriate (`P/18-18-PLAN.md:179–195,219–225`).

**Concerns**
- **HIGH:** Restore failure has no defined safe terminal state; the plan generally says restore and clear the marker (`P/18-18-PLAN.md:34,221`).
- **HIGH:** Leaving a replaced runner behind is not necessarily inert (`P/18-18-PLAN.md:84–85`). The restored original config may already point at the same script path.

**Suggestions**
- Preserve marker and backup when rollback fails; report both original and restoration errors.
- Restore any replaced active runner too, or define staged publication/recovery.
- Test failure with an original config already pointing at a pristine runner.

**Risk Assessment:** **HIGH** — rollback can leave active behavior inconsistent with restored configuration.

## 18-19

**Summary:** The existing real-write proofs are valuable but do not cover the most dangerous transaction variants.

**Strengths**
- Correct second-apply versus third-apply backup expectations (`P/18-19-PLAN.md:28,153`).
- Nth-key testing proves actual byte restoration rather than fake writer behavior.

**Concerns**
- **MEDIUM:** Failure coverage uses an existing config; absent-config coverage is success-only (`P/18-19-PLAN.md:125,154`). Failed restoration, newly created config deletion, runner restoration, and simultaneous applies remain unproven.
- **LOW:** One non-vacuity fixture covers only `open`, not all prohibited write mechanisms (`P/18-19-PLAN.md:181–182`).

**Suggestions**
- Add the transaction variants above and an apply-level edited-runner `.new` case.
- Give each AST rule a minimal violating fixture.

**Risk Assessment:** **MEDIUM** — strong tests, but incomplete safety claims.

## 18-20

**Summary:** Approval and disclosures are strong; effort synchronization has a verified workstream mismatch.

**Strengths**
- Pinned installer, grouped approval, one resolver, and explicit ordering are well designed (`P/18-20-PLAN.md:31–43,205–218`).

**Concerns**
- **HIGH:** Installed effort sync reads root `.planning/config.json`, not the workstream config. It calls `readGsdEffectiveEffortConfig(cwd)` (`G/commands.cjs:789–796`), whose lookup explicitly searches root configuration (`G/install-effort-resolver.cjs:130–141,156–168`).
- **MEDIUM:** Plan-time “changed” keys can miss real writes caused by live drift: apply compares live values, whereas follow-ups compare recorded `existing` (`P/18-20-PLAN.md:185–186`).

**Suggestions**
- Block or honestly disable unsupported workstream sync pending real verification.
- Persist actual successful-apply changes in a receipt, or conservatively trigger relevant follow-ups.
- Test conflicting root/workstream effort and live drift.

**Risk Assessment:** **HIGH** — sync can succeed while applying the wrong effort settings.

## 18-21

**Summary:** Good documentation verification, but `.new` requires an explicit inactive-state procedure.

**Strengths**
- Parser-backed commands, independent-review distinction, and judged-blob binding improve documentation reliability (`P/18-21-PLAN.md:125–149,179–200`).

**Concerns**
- **MEDIUM:** The flow explains that edited scripts produce `.new`, but does not prescribe activation, merge, or verification (`P/18-21-PLAN.md:137–141`). New plan choices may therefore be reported while the old script remains active.

**Suggestions**
- State prominently that `.new` is not active.
- Require manual review/merge preserving customizations, followed by verification of active model/timeout settings.
- Reflect this incomplete activation state in apply reporting.

**Risk Assessment:** **MEDIUM** — operational ambiguity at a full-permission execution boundary.

## 18-22

**Summary:** Appropriate closing checks, with contradictory execution constraints.

**Strengths**
- Revalidates the judged committed blob and formally amends downstream source-of-truth documents (`P/18-22-PLAN.md:136–140,168–200`).

**Concerns**
- **MEDIUM:** Mandatory Docker verification conflicts with “never install anything.” The target builds an image (`Makefile:133–138`) whose Dockerfile installs packages and downloads uv (`tests/e2e/docker/Dockerfile:12–14,24`).
- **MEDIUM:** “Fix every gate” conflicts with stage-only-listed-files and unrelated-failure restrictions (`P/18-22-PLAN.md:65–72,88–91,118–131`).
- **LOW:** Treating any `error:` output as failure can reject expected negative-test diagnostics despite successful exit status.

**Suggestions**
- Explicitly authorize isolated container provisioning or define a blocked outcome.
- Define controlled scope expansion for gate repairs.
- Use exit codes and structured test outcomes rather than unrestricted text matching.

**Risk Assessment:** **MEDIUM** — closure is not unambiguously executable as written.

## Overall Assessment

### Status: Issues Found — revise before execution

The plans have substantial strengths: explicit contracts, real-gsd-tools tests, deterministic recommendation, conservative trust proposals, preserved v1 behavior, and unusually thorough operational documentation.

The highest-priority revisions are:

1. **Fix the immediate 18-04 purity-guard task-order blocker.**
2. **Define exclusive apply ownership and safe failed-rollback behavior.**
3. **Treat runner publication/restoration as part of the configuration transaction.**
4. **Fully validate executable plans and bind them to the destination project/workstream.**
5. **Enforce one lifecycle deadline across preflight, Git, retries, cleanup, and status emission.**
6. **Check Git state after every attempt and reject unknown-state review success.**
7. **Prevent workstream effort sync from falsely reporting effective synchronization.**
8. **Make `.new` an explicit inactive, unresolved activation state.**

**Overall risk: HIGH**, primarily because the current gaps affect configuration recovery and unattended full-permission execution—not because the phase is missing broad feature coverage.

Skipped implementation and full test execution; proposed v2 modules remain unproven until built. The main risk is reporting successful configuration or rollback while a mismatched runner or effort configuration remains active.

---

## Consensus Summary

One reviewer ran (`opencode-plan-review`, opencode adapter, pinned model
`router-env/my-plan-review`, about 5 minutes), so there is no cross-reviewer consensus. The
review is source-grounded (`file:line` citations into the plans, `cross-ai.mjs`, the
curated-config modules and the checkout-local gsd-core) and covers all 22 plan ids (plan
coverage check: no missing ids). Every finding below was checked by the orchestrator against
the PLAN.md text and, where it cites source, against that source.

Reviewer verdict: overall risk HIGH, "revise before execution". The gaps are concentrated in
two subsystems: the cross-AI runner's supervision lifecycle (18-10 to 18-12) and the apply
transaction (18-13, 18-14, 18-16 to 18-18, 18-20).

### Agreed Strengths

Single reviewer, so none are "agreed". Its main strengths: tracer-first plans whose E2E cases
use the real gsd-tools, registry-driven review lanes, deterministic recommendation, conservative
trusted-root proposals, the hermetic black-box runner harness, v1 kept intact, and
parser-backed SKILL.md command checks.

### Agreed Concerns

None (single reviewer). Orchestrator triage of every concern against the plan text follows.

**HIGH, verified and still open (11; three runner-deadline HIGHs merged into one):**

1. 18-04 task order (existence-class, confirmed). Task 1 adds `from . import cross_ai` to
   `recommend.py` and its verify runs all of `tests.test_curated_config_recommend`, but
   `ALLOWED_RELATIVE_IMPORTS` (`tests/test_curated_config_recommend.py:1720`) only gains
   `cross_ai` in Task 2, so `test_recommend_and_presets_import_nothing_forbidden` fails at
   Task 1's verify. Fix: move the allow-list and module-tuple edit into Task 1.
2. 18-10 cleanup waits for the child `close` event. A grandchild that inherits the CLI's
   stdout or stderr keeps the pipes open, so a CLI that finished still burns the whole deadline
   and ends `timeout` (the prototype has the same shape, `.planning/scripts/cross-ai.mjs:305-310`).
   Fix: act on `exit`, then drain the pipes for a bounded time and kill the group.
3. Runner lifecycle deadline (merges 18-10 HIGH 2, 18-11 HIGH 1, 18-12 HIGH 2). `treeState`'s
   git calls have no timeout (a hanging filter or fsmonitor blocks the event loop, signal
   handlers included); `listModels` uses a fixed 15 s even when less budget remains (the 30 s
   `TIMEOUT_MARGIN_S` absorbs one listing but not listing plus unbounded git plus cleanup); and
   the 18-12 deadline tests check the `--print-argv` arithmetic, not elapsed time. Fix: bound
   every git and listing call by `min(own cap, remaining budget)` and add one elapsed-time case.
4. 18-12 unknown tree state. `treeState` returns null when git fails (18-10 `<interfaces>`).
   18-09's `finish()` demotes a fallback to stop when the tree is unknown, but nothing stops
   review mode, or exec `ok`, from succeeding when the before or after state is null. Fix:
   null on either side means no success in review mode and `stop` in exec mode, with a case.
5. 18-13 plan/write race. `plan_script` classifies the existing runner and `write_script`
   trusts that result, so an edit or create between the two calls (apply spawns several
   gsd-tools calls between them) is overwritten. Fix: re-check the bytes at write time and
   fall back to `.new` when they changed.
6. 18-14/18-17 apply input validation. `load_plan` checks the envelope only. A hand-edited
   plan can carry a set entry with no value, duplicate keys, an artifact `path` outside the
   project, or a `workflow.cross_ai_command` the editor would refuse without `--force`, and
   apply never re-checks any of it (T-18-24's mitigation lives only in `plan-set`). Fix: one
   schema-2 validator shared by plan-edit, apply and followups, with the artifact pinned to
   `.planning/scripts/cross-ai.mjs` and the command rule re-checked at apply time.
7. 18-16/18-18 apply marker. "Refuse an open marker, then `write_marker`" is
   check-then-write, so two applies can both pass. Fix: create the marker with `O_EXCL` (or
   `os.link`, as the backup claim already does) before the backup.
8. 18-17 destination binding. `load_inputs` checks the digest and that `--project-dir` is a
   directory, but not that it is the inventory's project; the inventory records
   `existing_config.path` (`inventory.py:91-104`). Fix: refuse when the resolved config path
   differs from the inventory's.
9. 18-18 failed restore. The must-have says a failure "restores the backup ... clears the
   marker". Nothing defines what happens when `restore_backup` itself raises. Fix: keep the
   marker and backup, and report both errors.
10. 18-18 runner after restore. "The rendered script is inert while `workflow.cross_ai_command`
    does not point at it" is false on a re-apply: the restored config can already point at
    the runner that apply just replaced. Fix: back up and restore a replaced pristine runner too.
11. 18-20 effort sync and workstreams (existence-class, confirmed). `effort sync` reads only
    the root `.planning/config.json` (`.claude/gsd-core/bin/lib/commands.cjs:795`,
    `install-effort-resolver.cjs:130-168`), while apply writes through the workstream-aware
    `config-set`. 18-20 never mentions workstreams. Fix: skip or refuse the sync follow-up when
    `GSD_WORKSTREAM` is set, saying why.

**HIGH reconsidered on verification (not counted as HIGH):**

- 18-11 "retries happen before the git safety check". The before-state is taken before the
  first attempt and compared after the last, so the review contract and exec stop rules still
  hold. Retrying the same CLI with resume after a partial exec edit is the prototype's
  deliberate resume design. What remains is LOW: review mode may retry once after a write
  before stopping. Kept as actionable below.

**MEDIUM/LOW, actionable (not yet in any PLAN.md):**

- 18-01 M: an exit-0 run with a malformed RPC envelope becomes `models: []`, which looks like a
  pi with zero models. Return None when no valid `get_available_models` response exists, or
  record why `[]` is intended.
- 18-01 M: `encode_value_strict` uses `json.dumps` with the default `allow_nan=True`, and a
  non-serializable nested value raises TypeError, which `config_set_strict` does not catch.
  Use `allow_nan=False` and turn TypeError/ValueError into the key-naming refusal, with a case.
- 18-02 M: `_validate_gsd_core` checks only the lane `slug`. Validate the six lane fields as
  str-or-None and the `skills_roots` values at the inventory-file boundary.
- 18-02 L: `skills_roots` discovery failure becomes `{}` with no warning, but Task 2's
  `<done>` claims a warning. Add the warning or fix the claim.
- 18-03 M: `escapes_root` resolves the skill directory, but gsd-core checks the `SKILL.md`
  path (`.claude/gsd-core/bin/lib/init.cjs:3697`). Use realpath(`SKILL.md`), with a case.
- 18-03 M: Task 1 step 1 says an unreadable SKILL.md gives `description` "" and also "skip that
  entry"; Task 2 expects the entry kept. Pick one rule.
- 18-05 L: the "interrupted run leaves the old plan" truth is backed only by a determinism
  test. Narrow the claim, or add a failure-before-replace case.
- 18-08 M: trusted-root candidates are a replacement list that drops roots the user already
  approved, and a root already covered by an approved ancestor is proposed again. Merge with the
  existing list and skip covered roots, with a case.
- 18-08 M: a project copy wins even when its `SKILL.md` resolves outside the project, which
  gsd-core rejects. Skip escaping project copies in `locate`.
- 18-09 M: every case shares `<tmp>/calls.log`, but later cases assert an empty log (18-11
  `print-argv-no-preflight`) or the absence of a CLI. Give each case its own log.
- 18-09 M: deleting the white-box `selfTest` drops the per-runtime exec permission-flag
  checks and the opencode/cursor/grok/codex parser checks (`.planning/scripts/cross-ai.mjs:413-435`).
  Keep equivalent `--print-argv` and parser cases for every supported runtime.
- 18-11 M: the `flaky` fake writes its counter inside the snapshotted repo. Move it to the
  scratch HOME.
- 18-11 L: in review mode, check the tree state before a transient retry and stop at once on
  a write.
- 18-15 M: only unsetting `workflow.cross_ai_timeout` is guarded while execution is on.
  Check the execution, command, timeout and artifact invariants after every set and unset,
  with command-unset and execution-unset cases.
- 18-16 M: backup reuse compares bytes only, so a chmod-only change restores the old mode.
  Compare the mode too.
- 18-19 M: failure coverage uses an existing config only. Add an absent-config failure case
  (the created config is deleted).
- 18-19 L: the write-discipline scan has one non-vacuity fixture (`open`). Add one per rule
  (`os.replace`, `shutil.copy*`, `cache_write_*`, `restore_backup` outside the helper).
- 18-20 M: `changed_keys` compares against the plan-time `existing`, but apply compares the
  live value, so drift can hide a real write from the follow-ups. Use apply's report `writes`.
- 18-21 M: SKILL.md mentions `.new` without saying that it is inactive and must be merged by
  hand. State that, and say how to verify the active runner's CONFIG afterwards.
- 18-22 M: `make e2e-docker` builds an image that downloads packages, which conflicts with
  "never install anything". Explicitly allow the container build, or define a blocked outcome.
- 18-22 M: "a failing gate is fixed in the code it names" conflicts with staging only Task 1's
  listed files and the pre-existing-failure rule. Define how far a gate fix may reach.
- 18-22 L: `fails_when` treats any `error:` line as failure, which negative tests can print
  even when the run passes. Use exit codes and `FAILED`.

**Not actionable (verified as already covered):**

- 18-06 M "host exclusion should follow the executable": `is_host` is
  `runtime == host_cli` (`catalog_adapter.py:383`) and `eligible_lanes` requires a candidate
  with `runtime == binary` and `is_host` false. A lane whose binary is the host's executable
  therefore has no eligible candidate, whatever its slug.
- 18-07 L "non-string `when` can throw": `GATES` is a tuple, and tuple membership compares by
  equality, so a list or dict `when` returns False and the loader refuses it cleanly.

### Divergent Views

None (single reviewer).

## Verification coverage

Source-grounding pass (`plan_review.source_grounding` unset, so default on; authority `grep`
from `drift-guard authority`):

- Method: every backticked token in each plan body (Review Dispositions Ledger excluded) was
  classified. 753 symbol and path references were checked against the repo (skills/, tools/,
  tests/, the checkout-local `.claude/gsd-core/`, Makefile, config files). 2,690 tokens were
  skipped as non-symbols (prose, values, CLI argv fragments, regexes, JSON snippets).
  Symbols named in a plan's "Artifacts this phase produces" or frontmatter `artifacts`/
  `files_modified` were excluded as new.
- MISSING after cross-plan resolution: 0 hallucinated existing-code references. 79 tokens did
  not resolve to current source, and all were triaged as legitimate:
  - new test classes and methods a plan's own tasks create (for example `TestRealGsdLanes`,
    `TestPlanSetTracer`, `TestBackupNaming`, `TestWritePathDiscipline`);
  - new symbols created in a plan's `<interfaces>` or action text rather than its artifact
    list (for example `PI_RPC_FIXTURE_PATH`, `CONNECT_TIMEOUT_S`, `DESCRIPTION_MAX`,
    `EXEC_DEFAULT_HOSTS`, `FollowupCtx`, `changed_keys`, `_cmd_followups`, `failed_key`,
    `skill_check`, `write_path`);
  - runner-template JS identifiers that 18-09 to 18-12 create (`hermeticEnv`, `writeCopy`,
    `FAKE_MODES`, `GSD_DEFAULT_TIMEOUT_S`, `runCli`, `treeState`; `runCli` and `gitState`
    exist in the prototype `.planning/scripts/cross-ai.mjs`, which the corpus scan excluded
    under `.planning/`);
  - scratch-fixture paths inside temp dirs (`skills/projskill/SKILL.md`,
    `skills/ponytail*/SKILL.md`, `.planning/workstreams/ws/config.json`);
  - external names: pi JSON fields (`maxTokens`, `thinkingLevelMap`, `baseUrl`), Claude's
    `enabledPlugins` settings key, git env vars (`GIT_AUTHOR_EMAIL`, `GIT_INDEX_FILE`), and
    Python stdlib/builtins (`os.path.commonpath`, `FileExistsError`).
- AMBIGUOUS: none recorded. UNCHECKABLE: function signatures and behavior claims (the `grep`
  authority cannot assert signatures), and the live behavior of external CLIs (pi RPC,
  `opencode models`, `cursor-agent models`, `codex debug models`). Neither was run.
- Reviewer citations spot-checked and confirmed:
  `tests/test_curated_config_recommend.py:1717-1782`, `.claude/gsd-core/bin/lib/init.cjs:3685-3721`,
  `.claude/gsd-core/bin/lib/commands.cjs:789-796`,
  `.claude/gsd-core/bin/lib/install-effort-resolver.cjs:125-168`,
  `.claude/gsd-core/bin/lib/security.cjs:195-215`,
  `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py:37-39`,
  `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py:91-104`,
  `.planning/scripts/cross-ai.mjs:285-345,390-440`, `Makefile:133-138`.

Cross-artifact fact-drift pass:

- Phase status: `drift-guard phase-status --phase 18` returned `uncheckable`
  (`phase_not_in_roadmap`: no ROADMAP status was parsed for Phase 18; STATE.md says
  "Ready to execute"). Recorded here, not read as consistent.
- Requirement IDs: ROADMAP Phase 18 lists XAI-01, XAI-02, SKL-01 to SKL-04, APP-01 to APP-04,
  EVAL-06 and SPEC-05. The union of the 22 plans' `requirements` is the same 12 IDs, so there
  is no contradiction.
- Success criteria vs must-haves: SC1 to SC5 were sampled against 18-04, 18-14, 18-16, 18-18
  and 18-21 (cross-AI defaults, `plan-set`/`plan-unset` with `source: user`, three kept
  backups, gsd-tools-only writes, v1 kept). There are refinements (D-39: no execution default
  without an installed target) but no contradictions. Advisory only; nothing here is counted.
- CONTEXT.md glossary vs PLAN usage: not compared term by term (skipped for size). Recorded as
  partial coverage.
