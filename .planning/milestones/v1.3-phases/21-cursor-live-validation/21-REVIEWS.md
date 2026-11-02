---
phase: 21
reviewers: [opencode-plan-review]
reviewed_at: 2026-10-18T21:45:45Z
plans_reviewed: [21-01-PLAN.md, 21-02-PLAN.md, 21-03-PLAN.md, 21-04-PLAN.md, 21-05-PLAN.md, 21-06-PLAN.md, 21-07-PLAN.md]
models:
  opencode-plan-review: "router-env/my-plan-review"
model_sources:
  opencode-plan-review: "pinned"
---

# Cross-AI Plan Review — Phase 21

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

Cycle 3 of 3 (the last), against the plan set at 9e7384c (replanned from cycle 2's review at
d64ed18; seven plans, each with Round 1 and Round 2 disposition ledgers). Reviewer lane:
`review.default_reviewers = ["opencode-plan-review"]` (reviewer instance on the opencode adapter,
model `router-env/my-plan-review`, no effort flag because `review.effort.opencode` is `inherit`).
The prompt also carried cycle 2's REVIEWS.md so prior findings could be judged against the
ledgers. The lane ran once, exit 0, empty stderr, about 18 minutes. Plan coverage: 7/7 ids. No
evidence-quality discount marker. No prompt trimming. The reviewer's one-line tool-loading
preamble was dropped; the raw output is kept under `.review-diagnostics/`.

## OpenCode Review (opencode-plan-review)

**Framework:** GSD · implementation plans  
**Review:** Convergence cycle 3 of 3, grounded in the current worktree’s plans and source.

Plan-file references below are relative to `.planning/phases/21-cursor-live-validation/`.

## 21-01

### Summary
The resolver, parser and snapshot changes are well scoped. The refresh-path correction and ASCII validation address the earlier findings. The trailing-empty-PATH case is now covered, but the proposed first-hit shortcut still leaves one detection/dispatch discrepancy.

### Strengths
- Records `real_path` at both snapshot writers, addressing the cached-row reconstruction in `skills/ai-kit-spec-review/ai_kit_spec/routing.py:269–299`, not just initial construction.
- Preserves existing positional resolver callers and the thin listing wrapper in `skills/ai-kit-spec-review/ai_kit_spec/detection.py:300–313`.
- The no-schema-bump decision follows the actual rule—data **a consumer relies on**—in `skills/ai-kit-spec-review/ai_kit_spec/detection.py:22–28`.
- Adds focused captured-output, ANSI, nameless-model and non-ASCII-token tests without introducing another dependency.

### Concerns
- **CARRIED-OVER · MEDIUM — Empty-PATH agreement is only partially resolved.** `21-01-PLAN.md:256–268` reaches the directory scan only after finding a wrong-basename `agent`. With `PATH=""`, `shutil.which("agent", path="")` returns `None`, so this shortcut never scans cwd. The runner’s walker instead treats that empty entry as cwd (`skills/ai-kit-spec-review/references/cross-ai.mjs:404–409`, retained by Plan 07). I reproduced the underlying distinction: empty-path lookup returned `None`, whereas lookup with `path=os.curdir` returned `./agent`. The new trailing-empty test covers `/grok/bin:`, not this entirely empty PATH.

### Suggestions
- Define the missing-versus-empty PATH behavior explicitly.
- When the effective PATH is empty, test cwd consistently with the runner; retain hermetic handling for injected test resolvers.

### Prior-finding disposition
- Stale `real_path` on refresh: **RESOLVED**.
- Runner’s guarded first-hit mismatch: **RESOLVED at the planned lookup level** by 21-07; its new launch issue is reported under that plan.
- Parser ASCII alphabet: **RESOLVED**.
- Empty PATH segments: **PARTIALLY RESOLVED**—the trailing-empty case is fixed; the entirely empty case remains.

**Risk Assessment: MEDIUM** — ordinary PATH layouts are covered, but the unconditional agreement claim still exceeds the proposed behavior.

## 21-02

### Summary
The static agents and tests are appropriately separated from installation and live delegation. The revised catalog discovery removes the 1.16.0 restriction that previously prevented the collision check from running against this checkout.

### Strengths
- Keeps Cursor model pins outside Claude’s `agents/` directory and checks explicit non-fast twin membership against the captured listing.
- Discovers the specific catalog prerequisite rather than using `real_gsd_paths()`, whose 1.16.0 restriction is real (`tests/test_curated_config_e2e.py:94–110`).
- The inherited `_RealGsdTestCase.setUp` introduces no hidden version skip; it only creates the temporary environment (`tests/test_curated_config_e2e.py:58–63`).
- Correctly treats a failed available query as a failure. `query_agent_catalog` returns `None` for failed or malformed results, not only missing prerequisites (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/gsd_catalog.py:128–146`).
- Limits the Node parity claim to selected fields in the two shipped files instead of claiming full parser equivalence.

### Concerns
- No additional blocking concern found.

### Suggestions
- Keep the required bare-`OK`, non-skipped catalog result in the phase evidence, as specified at `21-02-PLAN.md:327–331`.

### Prior-finding disposition
- Query returning `None` silently skipped: **RESOLVED**.
- Installed 1.17.0 catalog skipped by the 1.16.0 helper: **RESOLVED**.
- Parity-oracle scope overclaim: **RESOLVED**.

**Risk Assessment: LOW** — the remaining account-specific model-availability limitation is already honestly bounded by using a captured listing.

## 21-03

### Summary
The host-root fix, matrix extension and complete baked-map rejection address the identified harness gaps. One existing evidence-producing path is omitted from the wording changes, so the resulting smoke document would contradict its resolve-model-only qualification and fail a stated acceptance criterion.

### Strengths
- Adds Cursor through the existing host-first insertion points rather than creating another resolution mechanism (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py:61–75`).
- Separates canonical-agent existence checking from complete-map model rejection. This correctly addresses `_baked_mismatches` iterating only `promised_map` (`tests/gsd_curated_eval.py:4288–4298`).
- Adds a compact-file negative case, covering files returned by `_baked_models` but absent from canonical promises (`tests/gsd_curated_eval.py:4274–4285`).
- Explicitly scopes Cursor directory protection to names, while hashing `hooks.json`, rather than implying directory-content protection.

### Concerns
- **NEW · MEDIUM — The Steps section still claims baked-model equality.** Task 2 changes `_baked_lines` at `21-03-PLAN.md:350–353`, but the smoke independently emits:
  - `planned == baked == resolve-model` from `tests/gsd_curated_eval.py:4455`;
  - the step name `post-apply install and planned == baked` at `tests/gsd_curated_eval.py:4470`.

  These enter `## Steps` through `tests/gsd_curated_eval.py:4673–4675`, independently of `_baked_lines`. Consequently, following the specified edits leaves the false equality in the evidence and violates `21-03-PLAN.md:443`, which requires zero occurrences of `planned == baked`.

### Suggestions
- Extend the Cursor wording branch to the step name and detail returned by `_smoke_project_a`.
- Check the complete rendered Cursor evidence for the absence of baked-equality claims, not only `_baked_lines` output.

### Prior-finding disposition
- Complete baked map not checked: **RESOLVED**.
- Smoke command returns `echo` status: **RESOLVED** by the captured `rc` and final status test.
- Specialist overrides omitted from artifact checking: **RESOLVED**.
- Cursor protected entries absent: **RESOLVED within the explicitly documented hash/name-list scope**.
- Rejection of additional attempt-output machinery: **ACCEPTED**; renaming prior outputs before reruns is sufficient for the local rehearsal.

**Risk Assessment: MEDIUM** — the executable checks improve substantially, but the remaining evidence strings would contradict the phase’s central certainty qualification.

## 21-04

### Summary
The revised entry ordering, attempt-bound verdict and process-record requirement resolve the main stale-evidence problems. The specified scratch-HOME lifetime is now consistent with probes and retries. A smaller deterministic problem remains in the raw-output path scan.

### Strengths
- Checks the previous baseline before replacing it, then archives the entire previous output directory before attempt 1 (`21-04-PLAN.md:270–285`).
- Requires a spawn record for the selected attempt and re-derives the verdict from its runner status, smoke exit and passing steps (`21-04-PLAN.md:467–477,522`).
- The cleanup explanation now matches actual runner finalization: SIGTERM and SIGKILL are attempted on normal exit as well as failure (`skills/ai-kit-spec-review/references/cross-ai.mjs:553–571`).
- Restores the real environment only for the harness while documenting the limits of Cursor’s scratch-HOME isolation.

### Concerns
- **NEW · MEDIUM — The HOME-path scan fails on its directory operand and does not search its contents.** `21-04-PLAN.md:458–460` passes `cursor-artifacts/` to `secret-scan`, then runs nonrecursive `grep -F -l` on “the same list.” Unlike `secret-scan`, that grep does not descend into directories. A clean existing directory operand produces exit **2**, not the expected **1**, and its artifact files remain unsearched by that check. I reproduced this behavior without reading user configuration.

### Suggestions
- Recurse over the explicitly named artifact directory, or enumerate its files, while continuing to exclude the credential-bearing scratch HOME and wrapper.
- Keep cleanup recovery as documented; another supervisor abstraction is not required to resolve the corrected timing issue.

### Prior-finding disposition
- Stale outputs and overwritten baseline on re-entry: **RESOLVED**.
- Scratch-HOME timing contradiction: **RESOLVED**. The revised lifetime lasts through the final probe/retry; re-entry and late teardown provide recovery.
- Vacuous process-record verification: **RESOLVED for the reported gap**.
- Incorrect normal-exit cleanup explanation: **RESOLVED**.
- Cursor protection breadth: **RESOLVED through the preceding 21-03 G6 work**, with names-only limitations stated.
- Rejection of additional per-attempt machinery: **ACCEPTED** given wholesale entry archiving and retry renaming.

**Risk Assessment: MEDIUM** — the principal evidence-integrity problems are addressed, but the specified path-scan command rejects a clean run.

## 21-05

### Summary
The formal amendment is now an adequate reconciliation of headless label eligibility with interactive acceptance. The qualified wording, mandatory human follow-up and digest-bound judge criteria are internally consistent.

### Strengths
- Amends the actual conflicting sources rather than merely softening shipped wording. The original prerequisites are at `21-SPEC.md:45–58`; the explicit replacement rule is specified at `21-05-PLAN.md:271–286`.
- Preserves interactive R1 acceptance and reserves removal of `pending` for the commit recording that run.
- Requires each report’s findings, score floor and digest, matching the byte-bound skill/reference digest implemented in `tests/gsd_curated_eval.py:384–402`.
- Makes the in-session pending marker a real downstream precondition, not a passing score.

### Concerns
- **NEW · LOW — The README row being edited retains a stale runner version.** `README.md:45` currently calls this the “template-3” runner. Plan 07 upgrades the runner to template 5, while `21-05-PLAN.md:257–258` changes only the validation-label phrase in that same row.

### Suggestions
- Correct or remove the stale template number while editing the README row.

### Prior-finding disposition
- LIFT before interactive R1: **RESOLVED by the explicit formal amendment**, not by treating headless execution as interactive acceptance.
- LIFT based on unrelated success strings: **RESOLVED** through the identified-attempt verdict.
- Judge PASS missing findings/digest criteria: **RESOLVED**.
- Pending in-session hand-off not enforced downstream: **RESOLVED**.

**Risk Assessment: LOW** — the remaining concern is documentation accuracy, not premature acceptance.

## 21-06

### Summary
The mandatory `human_needed` outcome and final digest revalidation address the earlier completion-gate failures. The optional probe now preserves CLI status and uses environment evidence rather than age for ownership. The custom-config rejection, however, is not fail-closed as written.

### Strengths
- Applies the host-rewrite filtering at the contiguous smoke snapshot-diff point, allowing step success, returned differences and exit status to agree (`tests/gsd_curated_eval.py:4604–4634`).
- Restricts the CLI exemption to one label and leaves unflagged checks strict.
- Revalidates both judge reports against the current digest rather than trusting a stored PASS (`21-06-PLAN.md:491–507,568–583`).
- Always leaves interactive R1 outstanding and the phase `human_needed`, independent of judge success (`21-06-PLAN.md:551–563`).
- The probe reads Task-associated model fields and labels workers by the inherited marker, without automatically killing newly observed processes (`21-06-PLAN.md:384–403`).

### Concerns
- **CARRIED-OVER · MEDIUM — The default-config-dir guard continues after rejection.** The paste at `21-06-PLAN.md:347` uses:

  ```sh
  test ... || { echo 'non-default CURSOR_CONFIG_DIR: unsupported by this run'; false; };
  mkdir -p ... && ...
  ```

  The semicolon starts the baseline/digest chain regardless of the failed guard. I reproduced `unsupported` followed by execution of the next command and final exit 0. Thus the cycle-2 config-path mismatch is only partially fixed: both checks read the default path, but the command does not enforce rejection of a session using another config directory. The verifier checks for the message’s presence, not stopping behavior (`21-06-PLAN.md:437`).

- **NEW · LOW — “Every other protected entry is byte-identical” remains too broad.** That wording appears at `21-06-PLAN.md:331–332,376–377`. Snapshot protection includes name-only listings (`tests/gsd_curated_eval.py:217–226`) and normalized Codex TOML with scratch-trust exclusions (`tests/gsd_curated_eval.py:305–306`). Equal snapshots do not establish byte identity for all underlying files.

### Suggestions
- Put the baseline/digest chain inside the successful branch of the guard, or connect the guarded group with `&&`.
- Add a synthetic non-default-config test proving the baseline branch is not reached.
- Say “other protected snapshot entries are unchanged within their documented hash, listing and normalization scope.”

### Prior-finding disposition
- Interactive acceptance does not block completion: **RESOLVED**.
- Cursor agents/hooks/skills absent from protection: **RESOLVED via 21-03 G6**, within its stated scope.
- Stale judge PASS accepted: **RESOLVED**.
- Worker ownership inferred from age: **RESOLVED**.
- Arbitrary model fields extracted and CLI status lost: **RESOLVED**.
- Digest/snapshot custom-path mismatch: **PARTIALLY RESOLVED**, because rejection does not stop execution.
- Snapshot-to-grep rejection: **ACCEPTED**; the specified `snapshot ok` invariant prevents a strict failure from satisfying that gate.
- Names-only directory protection: **ACCEPTED as an explicitly limited policy**, not content-integrity proof.

**Risk Assessment: MEDIUM** — phase completion is now guarded, but the interactive rejection path does not enforce its stated precondition.

## 21-07

### Summary
The saved pre-upgrade CONFIG comparison and authorized snapshot-delta gate resolve both deterministic cycle-2 failures. The newly added cwd self-test nevertheless validates only the printed binary string, missing a launch-time PATH re-resolution that can execute the rejected binary.

### Strengths
- Uses the correct newer-template upgrade path in `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:242–265`.
- Saves actual pre-upgrade bytes rather than selecting a commit by position (`21-07-PLAN.md:338–343`).
- The CONFIG comparison matches `_upgrade_config`: existing keys win, with `scrubEnv` deliberately replaced (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:227–235`).
- Correctly permits exactly the authorized tracked-runner change while rejecting other protected differences.

### Concerns
- **NEW · HIGH — The cwd resolver result can launch the rejected `agent`.** The new case explicitly expects the resolved binary to be the bare string `agent` because `path.join('.', 'agent')` removes `./` (`21-07-PLAN.md:291–294`). That string is later passed unchanged to Node’s subprocess launch (`skills/ai-kit-spec-review/references/cross-ai.mjs:583–585,675–678,852`). A bare command triggers another PATH search, which selects the earlier Grok `agent` that the resolver deliberately rejected.

  I reproduced the planned mechanism using harmless synthetic executables:

  ```text
  selected: "agent"
  actual output: "WRONG-AGENT"
  exit: 0
  ```

  The proposed `--print-argv` test passes because that path returns before spawning anything (`skills/ai-kit-spec-review/references/cross-ai.mjs:2796–2810`). This is therefore a false-green regression test for the full-permission dispatch boundary.

### Suggestions
- Return an absolute path, or preserve an explicit `./agent`, for cwd-derived hits.
- Add a hermetic listing/exec test proving the later Cursor executable actually runs and the rejected earlier `agent` never runs; printing the selected string is insufficient.

### Prior-finding disposition
- Authorized runner rewrite rejected by snapshot: **RESOLVED**.
- CONFIG compared against wrong revision: **RESOLVED**.
- Empty-segment lookup semantics: **RESOLVED at lookup level**, but the added bare cwd result exposes the new launch-time defect above.
- Rejection of an unused post-upgrade baseline: **ACCEPTED**; subsequent plans establish their own baselines.

**Risk Assessment: HIGH** — the new edge case can cross the guarded executable boundary and launch another CLI, not merely report Cursor unavailable.

## Overall assessment

**Coverage: 7/7 plans.**  
**Status: Issues Found — revise before execution.**

Most cycle-2 findings are resolved. The remaining work is narrow:

1. **Fix the runner’s cwd-hit launch identity** and test an actual hermetic spawn.
2. Make the interactive config-directory guard stop execution.
3. Remove baked-equality claims from the smoke step name/detail.
4. Fix Plan 04’s directory path scan.
5. Align empty-PATH behavior and make the two minor documentation qualifications.

No repository files were changed. Verification used source tracing and small synthetic probes; no live AI CLI, full smoke, or project test/build suite was run. The main remaining risk is wrong-binary execution in Plan 07.

---

## Consensus Summary

One reviewer ran, so there is no cross-reviewer consensus and the convergence consensus gate
does not apply: every HIGH counts unless the orchestrator spot-check shows it inaccurate. The
reviewer raised 1 HIGH (new), 4 MEDIUM (2 carried over as partially resolved, 2 new) and 2 LOW,
and judged every other cycle-1 and cycle-2 finding resolved, including all nine cycle-2 HIGHs,
and accepted every ledger rejection.

Orchestrator spot-checks against source (verification only, no disposition):

- Confirmed HIGH, 21-07 cwd launch identity: `path.join('.', 'agent')` is the bare string
  `agent` (checked in node), and the runner's `which` returns it as-is
  (`skills/ai-kit-spec-review/references/cross-ai.mjs:405-411`); `runChild`/`runOnce` pass it
  straight to `spawn(bin, ...)` (`:580-582`, `:675`, `:852`), which re-resolves a bare name over
  PATH and so reaches the earlier grok `agent` the guard rejected. The planned self-test checks
  only the `--print-argv` line (`21-07-PLAN.md:291-293`), so it passes on this defect. Python's
  `os.path.join(os.curdir, "agent")` is `./agent`, so 21-01 does not share the bug.
- Confirmed MEDIUM, 21-03 step wording: `baked_check` returns
  `planned == baked == resolve-model` and the step is named
  `project (a) post-apply install and planned == baked` (`tests/gsd_curated_eval.py:4455,4470`);
  21-03 only changes `_baked_lines`, so its own criterion
  `grep -c 'planned == baked' tmp/p21/local-cursor.md` is 0 (`21-03-PLAN.md:443`) fails.
- Confirmed MEDIUM, 21-04 `$HOME` scan: with GNU grep 3.12, `grep -F -l -- PAT <dir>` prints
  "Is a directory", exits 2 and searches nothing inside, so `test $? -eq 1` fails on a clean run
  and the artifact files go unscanned. (The local interactive `grep` here is ugrep, which
  recurses; the executor's shell may get either.)
- Confirmed MEDIUM, 21-06 guard: `test a = b || { echo ...; false; }; next` runs `next` and the
  line exits 0 (reproduced), so the `CURSOR_CONFIG_DIR` guard at `21-06-PLAN.md:347` does not stop
  the baseline and digest chain.
- Confirmed MEDIUM, 21-01 entirely empty PATH: `shutil.which` returns `None` when PATH is empty,
  so the scan in `21-01-PLAN.md:256-268` (reached only after a wrong-basename first hit) never
  runs, while the runner's `''.split(':')` yields one empty entry, mapped to `.`.
- Confirmed LOWs: `README.md:45` says "template-3" runner and neither 21-05 nor 21-07 touches
  that number; `21-06-PLAN.md:124,332,377` say "byte-identical" while the snapshot holds name
  listings and a normalized Codex TOML hash (`tests/gsd_curated_eval.py:217-226,305-306`).
- Orchestrator observation, not raised by the reviewer and not counted: 21-07 Task 2's exact
  gate `test "$(snapshot --check ...)" = 'changed <worktree>/.planning/scripts/cross-ai.mjs'`
  also fails when Claude rewrites a host-managed `<home>/.claude/plugins/*.json` during the run,
  because `_snapshot_report` prints a `changed (host-managed) ...` line too
  (`tests/gsd_curated_eval.py:330-339`); filtering `(host-managed)` lines before the comparison
  would keep the gate strict.

### Agreed Strengths
- Single reviewer. It judged resolved: the 21-07 snapshot delta gate and saved pre-upgrade
  CONFIG bytes, 21-04 per-entry archive, baseline check before replacement, scratch-HOME lifetime
  and spawn-record condition, the 21-05 SPEC R1/R3 and ROADMAP SC2 amendment, 21-06's
  unconditional `human_needed`, current-digest judge revalidation, environ-based probe ownership
  and Task-call parse, 21-03 G6 Cursor protected entries and the complete baked-map rejection,
  and the 21-02 version-free catalog discovery.

### Agreed Concerns
- Not applicable with one reviewer. Highest priority: return an explicit `./agent` (or an
  absolute path) for cwd hits in the 21-07 runner and test a real hermetic spawn; then the 21-06
  guard, the 21-03 step wording and the 21-04 directory scan.

### Divergent Views
- None (one reviewer).
