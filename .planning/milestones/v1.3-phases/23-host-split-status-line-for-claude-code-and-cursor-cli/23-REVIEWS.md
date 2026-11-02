---
phase: "23"
cycle: 1
reviewers: ["opencode router-env/my-plan-review (plan review)", "opencode router-env/my-plan-review (ponytail)"]
high: 12
---

# Phase 23 plan reviews, cycle 1

## Cross-AI plan review (verbatim)

## Summary

**Revise before unattended execution.** The architecture largely follows the locked decisions, but the plans contain migration safety defects, verification gaps, and incomplete setup/wizard integration.

I found **9 HIGH concerns and 26 additional actionable concerns**. Shared problems are counted once, with affected plans cross-referenced below.

The review covered all 18 plans, SPEC, CONTEXT including the October 23 rulings, RESEARCH, VALIDATION, and the repository instructions. I checked the named implementation and test files through source inspection. Additional read-only checks confirmed:

- The renderer contains **134 functions + 7 classes + 41 assignments = 182 audit rows**.
- The declared dependency waves are topologically consistent, with **no overlapping declared `files_modified` paths within a wave**.
- All **43 automated verification snippets pass `bash -n` syntax checking**. This does not establish correct failure propagation.
- No `tail -N | grep` verification pattern was found.
- Integration-group commands use uv correctly; however, some wizard-related setup tests can still be skipped under system Python.

Paths below are relative to `.planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/` unless stated otherwise.

### 23-01

**Strengths**

- Establishes separate raw-ANSI, subprocess-entry, and strict-provider oracles before extraction.
- Correctly excludes the two timing-dependent segments under ruling Q7.

**Concerns**

- **MEDIUM — The full oracle is not portable across timezone, locale, or checkout location** (`23-01-PLAN.md:248–260`). The prescribed mocks freeze `time.time` and `time.strftime`, but reset suffixes use `datetime.fromtimestamp(...).strftime(...)` in `tools/status-line.py:1662–1674`. The empty payload also resolves its path from the current directory at `:1805`. **Fix:** control reset timezone/locale and the empty case’s working directory; verify that changing the checkout/scratch-directory name does not change the committed output.

- **MEDIUM — Fixture-preservation checks use the wrong baseline** (`23-01-PLAN.md:146–147,235`; consumers in `23-05:268`, `23-06:293`, `23-07:255`, and `23-18:180–182`). The recorded base precedes creation of the oracle files. A diff against it cannot be empty, and an additions-only diff cannot prove that those files were never subsequently changed. **Fix:** record separate `production_base` and completed `oracle_commit` SHAs. Compare fixture blobs against `oracle_commit`. This repairs D-05 without weakening byte identity.

### 23-02

**Strengths**

- The 182-row count and pinned taint vocabulary reproduce against the actual renderer.
- Ordered rows, AST hashes, reviewed reasons, and non-vacuity checks provide useful extraction controls.

**Concerns**

- **MEDIUM — `core_default_theme` is incorrectly classified as reused** (`23-02-PLAN.md:197–207`; `23-06-PLAN.md:188,323`). Its current implementation calls parameterless `core_build_theme(cfg_default_config())` (`tools/status-line.py:1935–1937`). Plan 06 requires a host argument and changed calls, so the reused-row hash gate will reject the required change. **Fix:** classify it as `generalized` in the initial audit map, with Host/ConfigSpec parameterization as the reason.

### 23-03

**Strengths**

- Separates synthetic evidence from owner-only observations.
- Specifies loopback-only fakes, redirect refusal, token-free summaries, and pending-owner status rather than claiming a live pass.

**Concerns**

- **MEDIUM — Leak checks can match their own checker process** (`23-03-PLAN.md:399`; repeated in plans 08, 11–13, 16–17). The newly started `awk` argv contains its program text, including `cursor_fakes`, so `ps ... args` can report that checker as a new matching process. **Fix:** track the actual spawned child PIDs and relevant descendants, then verify those processes were reaped. Do not kill by this broad argv match.

- **MEDIUM — Semicolon-separated verify chains can mask earlier failures** (`23-03-PLAN.md:310`; also `23-04:298,328` and especially `23-18:190`). A semicolon starts a new command list regardless of the preceding chain’s result. Later output checks can determine the final successful status, including from stale logs. **Fix:** explicitly capture and assert every command’s exit status, use failure-propagating control flow, and treat log matching as additional evidence. In 23-18, assign `D` independently and explicitly capture the spike checker’s expected exit code.

### 23-04

**Strengths**

- Uses a reproducible mover and AST conformance instead of relying only on manually reviewed file movement.
- Correctly identifies caller-namespace patching and rejects a compatibility façade.

**Concerns**

- **MEDIUM — Rule 5’s live check is redirected to an incompatible module** (`23-04-PLAN.md:322–323`). The unchanged checker requires a DEFAULTS block, but the move map gives `common_config.py` cfg functions and external discovery without DEFAULTS rows. The later wrapper does not make Task 2’s instruction pass. **Fix:** update the live test and wrapper together in Task 2: check data-only DEFAULTS where that block exists, and ordering only where DEFAULTS and cfg functions coexist.

- **MEDIUM — The 3600-second execution envelope lacks a credible budget for this scope** (`23-04-PLAN.md:267–369`; related risk in `23-06` and `23-16`). Plan 04 combines three migration tools, two extraction stages, test rewriting, strict typing, and architecture checks. Plan 16 similarly combines the seam, previews, inventory, and persistence with repeated integration/full gates. VALIDATION estimates roughly 600 seconds for full verification but supplies no measured per-plan headroom. **Fix:** separate the largest extraction/seam tasks into smaller runs or establish explicit measured gate budgets and resumable task boundaries. This is a sizing risk, not a claim that a timeout was observed.

- **MEDIUM — Multi-module quick checks bypass the required parallel runner** (`23-04-PLAN.md:298,328`; repeated in plans 05–07, 12, and 16). AGENTS.md requires one subprocess per module through `tools/run_unittest_parallel.py`, not sequential `python3 -m unittest` module lists. **Fix:** use the runner’s explicit module arguments, under uv when the selected coverage requires it.

The shared failure-propagation concern under 23-03 also applies here.

### 23-05

**Strengths**

- Names the one intentional registry change during extraction.
- Removes the doctor’s import shim and adds thin-entry non-vacuity coverage.

**Concerns**

- **MEDIUM — Required migration-tool edits are outside the permitted file lists** (`23-05-PLAN.md:7–24,245–250`). Task 1 extends `split_move.py` and stage-3 rewriting, but the scripts are absent from both `files_modified` and the task’s file list. Following the staging restriction leaves required changes uncommitted. **Fix:** include `live/split_move.py` and `live/split_rewrite_tests.py`; include the checker only if it actually changes.

- **MEDIUM — A permanent exact-mismatch assertion blocks later planned changes** (`23-05-PLAN.md:283,289`). The test requires exactly one generalized AST mismatch, `core_discover_builders`. Plan 06 intentionally generalizes numerous additional definitions. **Fix:** make the “exactly one mismatch” assertion a Plan 05 checkpoint, not a permanent invariant. Keep permanent hash equality for reused rows and location checks for all rows.

The incorrect oracle baseline under 23-01 also affects this plan.

### 23-06

**Strengths**

- ConfigSpec avoids the config/render dependency cycle.
- Host supplies margins, registries, and provider namespaces while bad-TOML loading moves inside the never-blank boundary.

**Concerns**

- **MEDIUM — Task 2 assigns to an immutable NamedTuple field** (`23-06-PLAN.md:177–180,319`). `Host` is a NamedTuple, but the task says `HOST.config = SPEC`, which raises `AttributeError`. **Fix:** construct `HOST` after the final `SPEC` definition; remove the assignment. Use reconstruction or `_replace` only if genuinely necessary.

- **MEDIUM — The catastrophic-failure mock must follow the adapter’s lookup namespace** (`23-06-PLAN.md:198–200,280–283`; existing `tests/test_status_line.py:2614–2621`). After this change, `safe_render` invokes `host.build_context`, whose Claude adapter looks up `core_build_context` in `claude_payload`. An argument-only rewrite does not retarget the existing mock. **Fix:** explicitly patch `claude_payload.core_build_context` and assert the patched function was called while retaining the diagnostic assertions.

The reused-theme classification and oracle-baseline concerns above must also be corrected before this plan’s gates can pass.

### 23-07

**Strengths**

- Enumerates the Claude field readers that must move behind `ctx.host`.
- Preserves Claude’s null coalescing and specifies exact gauge arithmetic and boundary tests.

**Concerns**

- **MEDIUM — The slow-git subprocess deadline is too short** (`23-07-PLAN.md:304–313`). Production permits two seconds for `git status`, then another two seconds for worktree discovery. Actual call order is visible at `tools/status-line.py:848–860,818`. A cold-cache entry can consume four seconds in timeouts before startup/render overhead. Patching the constant in the parent test does not patch the separately launched entry. **Fix:** allow both production timeouts plus startup overhead for the entry test; retain the short patched deadline for the direct probe test.

The oracle baseline, multi-module runner, and parallel-checkout concerns also apply here.

### 23-08

**Strengths**

- Follows the locked hard-rename/no-shim decision.
- Covers migration order, idempotency, malformed JSON, dry-run, and race-safe creation.

**Concerns**

- **HIGH — Substring matching can rewrite foreign commands** (`23-08-PLAN.md:199–203`). Both `python3 <install>/tools/status-line.py.backup` and a foreign program receiving the legacy path as a data argument match the prescribed substring replacement. Neither invokes the legacy entry. **Fix:** recognize supported invocation shapes and require the script argument to equal the legacy path exactly. Add suffix, foreign-argument, and quoted-path cases. The current algorithm violates R3’s foreign-command protection.

- **HIGH — The TOML fallback can delete the losing migration’s source** (`23-08-PLAN.md:204–207`). `create_if_absent` returns `False` when another writer wins, but the instruction then unlinks the old TOML unconditionally. The winning destination may contain different bytes. **Fix:** unlink only after confirmed successful publication. On `False`, preserve the source and issue the both-present warning; add a failure-injected race test.

- **MEDIUM — The required reference sweep includes an unowned file** (`23-08-PLAN.md:257,269–271,284`). `tools/hooks/precompact_core.py:16` names the old renderer, but neither Plan 08 nor Plan 09 includes that file in its edit list. The reference gate therefore fails unless the executor violates its declared scope. **Fix:** include the file and update its reference to the moved probe’s actual module.

- **MEDIUM — Parallel plans require exclusive-checkout verification without providing it** (`23-08-PLAN.md:329`; corresponding final checks in plans 01–03, 04/10, 05/11, 07/12, 13, and 09/15). Declared edit sets are disjoint, but global clean-tree checks and project-wide gates run while sibling executors may have legitimate unfinished changes. **Fix:** serialize these plans or move global gates and cleanliness checks to an orchestrator-controlled wave barrier. Preserve sibling work; never stage or discard it to make a plan appear clean.

### 23-09

**Strengths**

- Adds live architecture checks with non-vacuity counterparts.
- Covers function-local and annotation imports, host boundaries, segment IDs, and lazy networking.

**Concerns**

- **MEDIUM — The legacy-reference check can flag its own test source** (`23-09-PLAN.md:292–305`). The live scan includes `tests/test_arch.py`, while its negative examples and regex need the forbidden spellings. Writing those literally creates self-matches outside the narrow allowlist. **Fix:** explicitly construct the regex and examples from split fragments or the setup constants, including comments/docstrings. Do not exempt the whole test file.

The parallel-checkout and failure-propagation concerns above also affect this plan’s final verification.

### 23-10

**Strengths**

- Specifies strict numeric parsing, cents/dollars conversion, optional percentages, inferred confidence, and separate failure timestamps.
- Covers freshness boundaries and auth-based hiding.

**Concerns**

- **HIGH — The team-without-hard-limit case contradicts locked D-10** (`23-10-PLAN.md:269,278–279`). The plan requires `usage_team` with `hard_limit=None` to become `fixed`; CONTEXT D-10 says failed or absent `GetHardLimit` is `unavailable`. Calling this a recorded deviation does not authorize changing a locked decision. **Fix:** make this case unavailable and test it. Any exception requires a formal decision amendment.

- **MEDIUM — Billing-date source precedence lacks an executable case** (`23-10-PLAN.md:233–242,265–273`). R7 requires source precedence, and RESEARCH identifies usage `billingCycleEnd` with fallback to plan info. Neither precedence nor the fallback appears in the behavior table. This value controls quota hiding and reset display. **Fix:** add cases where usage wins conflicting values and where plan info supplies a missing usage end.

### 23-11

**Strengths**

- Validates endpoints before credential access.
- Tests exact hostname boundaries, redirect refusal, torn reads, unsupported auth, and token-free diagnostics without weakening production validation.

**Concerns**

- **MEDIUM — Socket timeout is overstated as a total fetch deadline** (`23-11-PLAN.md:176–177,240–243,270`; dependency in `23-12:163`). `opener.open(..., timeout=8)` does not bound the complete response to eight wall-clock seconds. A trickling response can keep body reading active while the thread pool waits. This invalidates the “near one timeout” claim and the twenty-second lock-expiry reasoning. **Fix:** enforce a total fetch/refresher deadline, size lock expiry against it, and add a slow-trickle response test.

### 23-12

**Strengths**

- Correctly specifies cache-only rendering, DEVNULL stdio, session detachment, 0600 atomic cache writes, and directory ownership checks.

**Concerns**

- **HIGH — The permitted lock-takeover race contradicts single-flight** (`23-12-PLAN.md:144–146,168,240–245,270–271`). “At most two refreshers” is not established: multiple contenders can observe the expired lock and remove newer replacements. An unconditional release can also remove a successor’s lock. Expiry alone does not establish that the old worker died. **Fix:** serialize reclamation with a process-safe primitive and make release ownership-aware. Add multiprocess expired-lock contention and old-owner-release tests. This directly contradicts D-13/D-16 and R9; it is not an authorized shortcut.

- **MEDIUM — The kill test does not prove killed-refresher recovery** (`23-12-PLAN.md:270–276`). It proves that a detached marker-writing child survives termination of its parent. It never kills a real refresher after lock acquisition or proves competing processes recover the abandoned lock and publish quota. Eight threads do not establish across-process behavior. **Fix:** add that subprocess recovery test and assert exactly one replacement fetch and an eventual valid cache.

### 23-13

**Strengths**

- Preserves four independently placeable segments, API-off defaults, per-segment windows, local reset time, inferred/stale markers, and Q1’s provider namespace.
- Tests shared gauge identity and fresh-cache render isolation.

**Concerns**

- No additional plan-specific concern beyond the shared **MEDIUM parallel-checkout verification defect** recorded under 23-08. Its disjoint primary file ownership does not make a global clean-tree check safe while Plan 08 is editing.

### 23-14

**Strengths**

- Preserves the separate Cursor config resolver without changing the hooks path.
- Covers schema-valid wiring, quoted install paths, foreign entries, reclassification, and per-host uninstall.

**Concerns**

- **HIGH — Invalid host selection can be rejected after other writes** (`23-14-PLAN.md:238–245,269–274`). Plan 08 inserts migration at the start of `cmd_install_headless`; actual setup also replaces/links skills before wiring (`tools/setup.py:3583–3595`). Validating an undetected selection only at wiring time therefore violates “before any write.” **Fix:** validate unknown/undetected selections before migration, replacement, linking, hooks, or examples. Test invalid selection combined with legacy migration and other requested writes using a complete scratch-tree snapshot. This enforces D-23.

- **MEDIUM — Reusing Claude uninstall preserves an inconsistent ownership test** (`23-14-PLAN.md:264,273,277–278`). Actual `unwire_statusline` handles only object-form commands and treats commands containing the install directory as owned (`tools/setup.py:2032–2052`). Owned bare strings can survive, while foreign scripts inside the checkout can be removed. **Fix:** use the same exact ownership classifier for both hosts’ detect/wire/unwire; test bare-string Claude wiring, foreign same-directory scripts, and near-match filenames.

### 23-15

**Strengths**

- Keeps Claude’s default doctor behavior and help text stable.
- Labels Cursor quota as inferred and undocumented.

**Concerns**

- **HIGH — The prescribed fetch mock does not replace the bound default** (`23-15-PLAN.md:217,224–225`; `23-12-PLAN.md:174`). `probe_refresh(..., fetch_quota=probe_fetch_quota)` captures the original callable at definition time. Patching `cursor_quota.probe_fetch_quota` afterward does not replace it. With synthetic auth present, the test can attempt the real endpoint. **Fix:** pass the fake explicitly through the doctor seam or resolve defaults at call time. Add a network-denial backstop and assert the fake was invoked.

- **MEDIUM — Dry rendering can start the refresher before the foreground report** (`23-15-PLAN.md:151–160,217–225`). Cursor’s context builder calls `probe_read_quota`, which acquires the lock and spawns on empty/stale cache. The subsequent foreground diagnostic can then report “refresh in progress” instead of performing its intended fetch. **Fix:** order the foreground quota operation explicitly and give dry rendering its result without allowing another spawn. Test empty/stale cache with one refresh, zero detached spawns, and lock cleanup.

### 23-16

**Strengths**

- Uses one host-keyed wizard seam rather than duplicating the app.
- Specifies independent host outcomes and a real-entry preview against synthetic quota.

**Concerns**

- **HIGH — The result-shape migration omits a production consumer** (`23-16-PLAN.md:251–256`). `WizardResult.state` becomes host-keyed, but `cmd_install` still reads `result.state["segments"]` when installing bundled examples (`tools/setup.py:3200–3214`). **Fix:** explicitly include `cmd_install` and post-wizard result handling in Task 1. Move examples into per-host commit or deliberately migrate that consumer, preserving `--examples` precedence and declined-host behavior. Test a confirmed install with examples.

- **HIGH — Zero detected hosts crashes the prescribed `hosts[0]` implementation** (`23-16-PLAN.md:251–253,283`). No zero-host branch is specified here or in Plan 17. A fresh component-only installation is valid; an existing system-memory E2E fixture also supplies a Claude path without creating that directory. **Fix:** define Choose → Review → Done with no status-line writes for zero hosts. Add zero-host and Cursor-only pilot tests, and correct fixtures that intend to represent detected hosts. This implements D-22 without inventing a host.

- **HIGH — TOML validation invokes the network-active doctor** (`23-16-PLAN.md:325,328,332–334`). Plan 15 makes `--doctor --host cursor` perform a foreground credential-backed refresh. Actual `write_toml_preserving` inherits the environment and has a ten-second subprocess timeout (`tools/setup.py:485–491`). Saving a layout can therefore access the real login/network or roll back valid TOML because quota diagnostics are slow. **Fix:** make persistence validation explicitly offline—host-aware structural checking plus an offline dry render—and assert neither foreground fetch nor detached spawn occurs.

- **MEDIUM — System-Python setup checks can skip the seam coverage** (`23-16-PLAN.md:262,308`). `tests.test_setup` contains Textual-guarded wizard-context and housekeeping coverage. Running the integration group afterward does not run that module (`tools/run_unittest_parallel.py:46–51`). **Fix:** additionally run the relevant setup coverage through the runner under uv, or relocate it to integration modules; assert the critical cases ran rather than accepting skipped tests.

The sizing concern under 23-04 also applies strongly here.

### 23-17

**Strengths**

- Specifies exact host-labelled screens, cross-host navigation, independent Done outcomes, and real two-host PTY scenarios.
- Preserves declined-host behavior.

**Concerns**

- **MEDIUM — An existing real-wizard E2E driver is omitted from matcher migration** (`23-17-PLAN.md:231–233,260–266`). `tests/test_system_memory_e2e.py:145–163` still drives accumulated output using bare `Choose`, `Arrange`, and `Review` matches. It is outside this plan’s edit list and can advance on earlier captured text. **Fix:** include it, use exact current-screen prompts, consume/reset captured output between transitions, and preserve cleanup.

### 23-18

**Strengths**

- Reserves close-out for the orchestrator and reruns project-wide gates.
- Keeps owner-only live work pending rather than calling synthetic coverage a live pass.

**Concerns**

- **MEDIUM — Exit 1 does not prove “only owner work remains”** (`23-18-PLAN.md:179–190`). The spike checker’s exit 1 means not all rows passed; it does not distinguish pending owner rows from failed evidence. Its output is discarded. **Fix:** assert every required result is exactly `not run (owner)` and preserve checker output. Also apply the completed-oracle baseline fix from 23-01.

- **MEDIUM — POC path parsing weakens the exact-path deletion safeguard** (`23-18-PLAN.md:184–190`). `awk ... {w=$2}` truncates a whitespace-containing worktree path, so absence can be checked at the wrong location. **Fix:** parse the complete machine-readable worktree record, require the exact branch and one unambiguous path, reject unexpected symlinked parent traversal, and use the same quoted pathname for `rm -f --` and the absence check. This preserves D-12’s authorized deletion; it does not reopen that decision.

The shared failure-propagation issue is especially important here: line 190 can continue after a failed audit check.

## Overall Risk

**High until the migration, lock ownership, credential-test seam, and wizard integration issues are fixed.**

The declared file ownership and dependency graph are sound, but shared-checkout execution is not compatible with the plans’ independent global gates and clean-tree requirements. The byte-identical Claude strategy is strong in principle; its baseline errors, permanent intermediate assertions, and environment-dependent oracle would currently undermine that proof.

The review does **not** challenge the locked hard rename, detached cache refresher, API-off default, separate provider namespace, or owner-only live spike. The explicit contradictions requiring correction are the missing-hard-limit classification and the permitted single-flight race.

Not checked: runtime tests, live CLI behavior, network behavior, or actual 3600-second completion time. No files or git state were changed, and no protected configuration or credential files were read.

CYCLE_SUMMARY: current_high=9 current_actionable=26


## Ponytail review (verbatim)

What this change does: The plans split the Claude renderer, add a cache-backed Cursor status line, and extend setup, doctor and wizard to both hosts. I reviewed all 18 plans against the SPEC, CONTEXT—including the later rulings—and the connected code. The required features stay; the main savings are in migration machinery, duplicated configuration and temporary intermediate designs.

References below use filenames relative to `.planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/`. Savings are rough estimates, not measured diffs.

## HIGH

1. **The single-flight shortcut explicitly breaks single-flight** — `23-12-PLAN.md`, Tasks 1–2, especially lines 144–146 and 270–276.
   - **Problem:** The plan permits competing processes to remove an expired lock and claims this produces “at most two refreshers.” With several contenders, one can remove another contender’s newly created lock; the number is not bounded at two. An unconditional release can also remove a successor’s lock. Testing eight threads against an initially uncontended lock does not cover this.
   - **Smaller complete change:** Keep the required `O_EXCL`/expiry design, but serialize expired-lock recovery and release only the lock belonging to that acquisition. Replace the thread-only proof with subprocess contenders starting against one expired lock, plus a late-owner-release case.
   - **Estimated saving:** No honest code saving here; approximately **two weak tests replaced by two useful tests**, and avoidance of a later locking rewrite. This is a cut that went too far: a `shortcut:` comment cannot waive SPEC R9.

2. **“Ours” still means “our path occurs somewhere in a command”** — `23-08-PLAN.md`, Task 2; `23-14-PLAN.md`, Tasks 1–2.
   - **Problem:** Migration explicitly replaces a substring. Existing `detect_statusline()` and `wire_statusline()` also use substring membership (`tools/setup.py:1962,2011`). A foreign command such as `python3 /other/report.py --label '<install>/tools/status-line.py'`, or a path ending in `status-line.py.bak`, can therefore be rewritten or classified as ours.
   - **Smaller complete change:** Introduce **one command-ownership parser** shared by migration, detection, refresh and uninstall. For Cursor, match the actual interpreter/script arguments, not arbitrary text. For Claude, recognize the known ai-kit invocation and conservatively leave unrecognized shell forms foreign. Add argument-only and filename-suffix counterexamples.
   - **Estimated saving:** Roughly **20–40 lines of repeated ownership checks**, several overlapping tests, and one shared fix instead of four inconsistent policies. Do not simplify this to another substring helper.

3. **Saving Cursor TOML would invoke a live quota refresh as validation** — `23-15-PLAN.md`, Task 1; `23-16-PLAN.md`, Task 3.
   - **Problem:** Plan 15 makes `--host cursor --doctor` perform a foreground refresh. Plan 16 then uses that invocation inside `write_toml_preserving()`. Today that writer publishes the file, runs the doctor with a 10-second timeout, and restores the previous file on failure (`tools/setup.py:463–519`). A layout save would now read credentials and perform Dashboard calls; a slow request could reject valid TOML. Cursor dry-rendering through `HOST.build_context` can also trigger a detached refresh before the foreground report.
   - **Smaller complete change:** Keep the manual doctor’s required fetch report, but separate it from **config validation and synthetic dry-rendering**. Validate the candidate before publication, using the existing `--check` path and a synthetic quota result for builder checks. Do not add another CLI flag or make HTTP success part of a TOML save.
   - **Estimated saving:** Approximately **30–60 lines of rollback/network-test plumbing** by avoiding the new coupling. More importantly, valid configuration changes stop depending on network timing.

## MEDIUM

4. **The owner probe duplicates the most security-sensitive production code** — `23-03-PLAN.md`, Task 3; `23-11-PLAN.md`, Tasks 1–2.
   - **Problem:** `live/spike_probe.py` independently implements endpoint validation, credential-path resolution, token reading, redirect refusal and concurrent requests. Plan 11 then implements the same machinery in `cursor_quota.py`. The probe’s self-tests can pass while production differs, and the literal SPEC boundary says credential/network handling belongs in `cursor_quota.py`.
   - **Smaller complete change:** Keep the required owner runbook, capture and checker. Implement the probe’s network portion **after Plan 11**, calling the production transport from `cursor_quota`; leave only timing, redaction and evidence formatting in the owner script. Expose a token-free result, not the token.
   - **Estimated saving:** **100–180 lines**, one duplicate security test table, and one transport implementation to maintain. No spike feature needs to disappear.

5. **A one-time source move has become a small source-code generator product** — `23-04-PLAN.md`, Task 1 and mover contract; `23-05-PLAN.md`, Task 1.
   - **Problem:** Three committed tools must reconstruct imports, annotation-only edges, comment spans, banners, public renames, patch targets and permissible test diffs. The mover regenerates modules from the old blob, yet Plans 6–7 immediately hand-edit those generated modules. Most of this machinery becomes obsolete as soon as the split lands.
   - **Smaller complete change:** Keep the **required audit map, AST conformance check, mechanical assertion check and byte oracle**. Use a task-specific mover/rewriter under `tmp/`, rather than a durable regeneration interface with `--stage`. Move production code once into its intended modules; retain the pure-move commit before behavioral changes.
   - **Estimated saving:** Approximately **250–450 committed lines** and much of the generator debugging in Plan 4. **Plans 04 and 05 merge cleanly into one move plan with staged commits** after this reduction; the oracle and audit remain separate prerequisites.

6. **The plans add another copy of defaults despite the binding lazy-import ruling** — `23-08-PLAN.md`, Task 1; `23-16-PLAN.md`, “This plan” and Task 2.
   - **Problem:** Plan 8 preserves duplicated Claude defaults, and Plan 16 adds `CURSOR_SEGMENT_DEFAULTS`, `CURSOR_LAYOUT_DEFAULTS` and another host-settings table with drift tests. CONTEXT ruling Q2 instead selects lazy host imports on preview/wire paths. Existing `current_segments()` and `current_layout()` need defaults, not independent copies of them (`tools/setup.py:215–235`).
   - **Smaller complete change:** Lazily obtain `HOST.config` when constructing each `HostView`; pass its defaults, prefix and doctor information into the existing setup helpers. Keep uninstall independent of renderer imports. Retain one integration check of the conversion to wizard layout dictionaries.
   - **Estimated saving:** **50–90 production lines**, roughly **20–40 drift-test lines**, and several synchronized configuration surfaces.

7. **Cursor config-path resolution is duplicated instead of reused** — `23-14-PLAN.md`, Task 1.
   - **Problem:** The plan adds `cursor_cli_config_dir()` while separately updating `config_doctor_checks.resolve_runtime_config_paths()` and proving parity. That existing function already contains the three-step Cursor resolver (`tools/config_doctor_checks.py:64–94`). A parity test maintains two implementations of the same rule.
   - **Smaller complete change:** Factor the Cursor branch into one lightweight shared resolver and call it from both places. Apply the required whitespace-only fallback there. Leave the hooks’ separate `cursor_dir` untouched, as CONTEXT requires.
   - **Estimated saving:** **10–20 implementation lines** and one duplicated parity table. Keep one explicit precedence table testing expected paths.

8. **The fake payload “contract” proves that a fixture matches a schema written beside it** — `23-03-PLAN.md`, Task 2.
   - **Problem:** `PAYLOAD_FIELDS`, `payload_contract_problems()` and the synthetic payload all come from the same authored field list. Removing a field and asserting that the checker notices tests the checker, not compatibility with Cursor. The fallback also calls a payload reconstructed from RESEARCH `payload_poc_redacted.json`, obscuring whether it is actually captured evidence.
   - **Smaller complete change:** Feed the fixtures directly into the **real payload adapter** in Plan 13 and assert observable behavior for required, optional, null and malformed fields. Label reconstructed data synthetic; retain “captured POC” provenance only when that file actually supplied the data.
   - **Estimated saving:** **40–70 lines** of schema/checker/self-tests. The required synthetic and redacted fixtures remain; their provenance becomes more honest.

9. **The kill test proves a generic detached child survives, not that the refresher works** — `23-12-PLAN.md`, Task 2, line 276.
   - **Problem:** A generated `refresh_child` sleeps and writes a marker through `probe_spawn_detached()`. This passes if `probe_spawn_refresher()` constructs the wrong argv, `--refresh` fails, the real refresher mishandles its lock, or no valid quota cache is written. Plan 3 already tests the underlying pipe/detachment premise.
   - **Smaller complete change:** Kill a parent that calls the **real `probe_read_quota()` spawn path**, then wait for the actual refresher’s negative cache under a scratch HOME with no auth file. Assert `auth_missing`, lock release, closed inherited pipes, and that the next read observes the cache. Keep production-fetch success covered separately by the loopback transport test.
   - **Estimated saving:** One throwaway child program and approximately **20–40 test lines**, while checking substantially more production code. This replaces—not removes—the required killed-refresher evidence.

10. **The wizard is rebuilt twice around a knowingly temporary `hosts[0]` design** — `23-16-PLAN.md`, Task 1; `23-17-PLAN.md`, Task 1.
    - **Problem:** Plan 16 rewrites every single-host reader to `hosts[0]`, updates the tests, and introduces Cursor views that the UI cannot yet walk. Plan 17 revisits those readers, models, boards, gate state, Review and Done to make them genuinely per-host. Existing `WizardModel` and `LayoutBoard` already supply the units to keep per host.
    - **Smaller complete change:** Build the final host-keyed seam and current-host accessor once, alongside the host loop. Keep separate commits for seam/flow, setup persistence and PTY acceptance if needed; do not commit the temporary first-host-only implementation.
    - **Estimated saving:** Approximately **60–120 lines of temporary adapters and test churn**, plus one implementation/review cycle. **Plans 16 and 17 merge cleanly as one wizard workstream**, preserving all per-host gates, navigation, previews and PTY scenarios.

11. **Architecture enforcement arrives as a separate three-commit reconstruction pass** — `23-09-PLAN.md`, Tasks 1–3.
    - **Problem:** The split plans already update per-module architecture tests; Plan 6 adds duplicate-ID rejection and prefix rules; Plan 12 edits the spawn allowlist. Plan 9 later reopens the same files to install dependency, networking, inventory and final-location enforcement, with a rule that violations in unlisted production files must wait for another owner.
    - **Smaller complete change:** Add dependency/host-import rules with the split, networking rules with Plan 11, and Cursor uniqueness checks with Plan 13. Fold the remaining reference sweep, AGENTS update and required pipeline-doc deletion into Plan 8’s rename work.
    - **Estimated saving:** **One standalone plan and three handoffs/commits**, plus repeated discovery and gate work. Little test-code deletion is appropriate: the SPEC requires these rules and their non-vacuity checks. **Drop Plan 09 as a separate execution unit, not its acceptance criteria.**

## LOW

12. **Every executor receives roughly a hundred lines of duplicated operating instructions** — all plans, “Executor rules,” “Run rules” and the repeated phase-wide artifact list.
    - **Problem:** The repeated text already contains inherited wording such as “every 18.1 plan,” a one-commit rule overridden later by a per-task rule, and oversized artifact inventories unrelated to the current task. Changes to safety instructions must be synchronized across 18 files.
    - **Smaller complete change:** Put the shared run contract and artifact inventory in one referenced phase document. Keep each plan’s own allowed files, dependencies, prohibitions, task actions and acceptance commands local.
    - **Estimated saving:** Roughly **1,500–2,000 lines of plan duplication** and repeated executor input. Do not remove credential isolation, approval rules or task-specific safety checks.

### Recommended consolidation

Reduce **18 execution plans to about 15**:

- **04 + 05:** one mechanical split plan, retaining staged pure-move commits.
- **09:** distribute its required checks to their owning implementation plans; fold its remaining sweep into **08**.
- **16 + 17:** one final-form wizard workstream, without the temporary `hosts[0]` phase.

Keep **10, 11 and 12 separate**: normalization, credential transport and cross-process refresh are real boundaries, not needless paperwork. Keep the oracle, reviewed audit and final verification gates too.

Not checked: tests, live Cursor behavior, installed CLI bundles or private configuration; no files or git state were changed, and no AI CLI or network calls were made. The HIGH findings are static plan defects; owner-only evidence remains pending as the plans acknowledge.

PONYTAIL high=3 medium=8 low=1


# Cycle 2 (2026-10-23)

## Cross-AI plan review, cycle 2 (verbatim)

## Summary

**Revise before unattended execution.** Cycle 2 finds **3 HIGH concerns and 22 additional actionable concerns**. Shared defects are counted once and cross-referenced below.

Of the **nine unique cycle-1 HIGH findings**, seven are repaired in the operative plan contracts. Two remain incompletely resolved: **single-flight lock ownership** and **offline Cursor configuration persistence**. A new HIGH concerns verification cleanup that can recursively delete an inherited, non-scratch path.

The dependency waves are topologically consistent, with **no overlapping declared `files_modified` paths within a wave**. However, undeclared required edits and executor-side global gates still undermine that arrangement.

Read-only checks also established:

- All **43 intended shell bodies** parse with `bash -n` when isolated from surrounding markup.
- **Five verification blocks lack `</automated>`**, so their complete extracted content is not valid shell.
- Plans 03–08 introduce an unsupported **`--modules`** runner argument.
- No `tail -N | grep` verification pattern was found.
- Several cycle-1 dispositions describe fixes that remain absent from, or contradicted by, task bodies.

Plan references below are relative to `.planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/`. Resolved findings are not repeated as concerns.

### 23-01

**Strengths**

- Raw-ANSI, entry-subprocess and strict-provider oracles precede production changes.
- Timezone, locale, scratch-root and checkout-name portability checks are now explicit.
- Separate `production_base` and completed `oracle_commit` references repair the original fixture-baseline defect.
- Timing-dependent exclusions follow ruling Q7.

**Concerns**

No new plan-specific concern. The shared execution-barrier defect under **23-08** also affects this parallel wave.

### 23-02

**Strengths**

- The 182-row audit, pinned taint vocabulary and reviewed classification disagreements provide useful extraction controls.
- `core_default_theme` is now correctly classified as generalized.
- The prescribed move map accounts for the extraction stages without an identified earlier-stage dependency on a later stage.

**Concerns**

No new plan-specific concern beyond the shared execution-barrier defect under **23-08**.

### 23-03

**Strengths**

- Owner-only observations remain distinct from synthetic evidence.
- The task body now replaces its process-name scan with tracked-child cleanup.
- Delegating owner transport to production `cursor_quota` avoids a second credential-handling implementation.

**Concerns**

- **MEDIUM — Five verification blocks have unclosed automated markup** (`23-03-PLAN.md:347,396`; also `23-04:293`, `23-12:293`, `23-18:198`). Each opens `<automated>` without closing it before `<fails_when>`. An extractor expecting paired tags can consume prose or later tasks; the resulting command is not valid shell. **Fix:** close each block immediately after its command and mechanically check balanced verification tags across all 18 plans.

- **MEDIUM — The owner Dashboard probe has no implementation owner** (`23-03-PLAN.md:368–373`; `23-11-PLAN.md:7–9,224–299`). Plan 03 delegates `live/spike_probe.py` to Plan 11, but Plan 11 neither permits that file nor assigns its creation in a task. The owner’s Dashboard and latency steps therefore reference an undelivered tool. **Fix:** add the probe to Plan 11’s scope and task body, using production transport and returning only token-free response/timing evidence, with its required self-test.

The unsupported runner argument is counted under **23-04**.

### 23-04

**Strengths**

- AST equality, caller-namespace patching and the byte oracle are appropriate controls for the split.
- Making the mover disposable avoids committing a permanent source-generation interface.
- The extraction stages themselves remain coherently ordered.

**Concerns**

- **MEDIUM — Revised quick commands use an unsupported runner option** (`23-04-PLAN.md:287,293,325`; also Plans 03, 05, 06, 07 and 08). Actual `tools/run_unittest_parallel.py:195–217` accepts positional module names or `--group`; it does not parse `--modules`. That token becomes an additional unittest target, so the expected `N/N modules passed` result cannot occur. **Fix:** remove `--modules`, retaining uv where needed: `uv run python tools/run_unittest_parallel.py tests.test_status_line …`. No runner feature is needed.

- **MEDIUM — Rule 5’s repair still arrives after the task that needs it** (`23-04-PLAN.md:319–321,342–355`). Task 2 still points the unchanged DEFAULTS checker at `common_config.py`, which receives cfg functions but no DEFAULTS rows. Actual `tests/test_arch.py:287–303` rejects that shape. Task 3’s conditional wrapper cannot make Task 2’s preceding gate and commit pass. **Fix:** introduce and use the wrapper in Task 2: check DEFAULTS contents where present, and ordering only where DEFAULTS and cfg functions coexist.

- **MEDIUM — The orchestrator’s assertion-preservation proof is deleted before it can rerun it** (`23-04-PLAN.md:27,355–359`; `23-05-PLAN.md:28,244,290–294`). Both plans promise an orchestrator rerun of the scratch checker, then remove its directory and logs. **Fix:** provide a rerunnable assertion-preservation check or retain durable, independently verifiable proof until the orchestrator verifies it. The mover can remain disposable.

- **MEDIUM — The 3600-second sizing concern remains unsupported by a usable execution budget** (`23-04-PLAN.md:263–356`; related `23-05:244`, `23-06:253–337`, `23-16:250–340`; `23-VALIDATION.md:26`). Plan 04 still combines three migration scripts, two extraction stages, caller-sensitive rewrites, strict typing and architecture enforcement. Plan 05 reconstructs the deleted tooling. Plans 06 and 16 retain broad interface migrations and repeated full gates. No measured gate budget, remaining-time threshold or explicit resume procedure is supplied. **Fix:** reduce per-dispatch scope or specify measured verification headroom and resumable task boundaries. This is an unresolved sizing risk, not an observed timeout.

### 23-05

**Strengths**

- The single intended registry generalization is clearly isolated.
- The exact generalized-mismatch assertion is now checkpoint-only rather than a permanent invariant.
- Fixture preservation explicitly uses the completed oracle commit.
- Doctor-loader removal and thin-entry non-vacuity coverage are retained.

**Concerns**

- **MEDIUM — An existing setup-test consumer breaks before its later migration plan** (`23-05-PLAN.md:248–258,289–294`; also `23-04:283–287`). Actual `tests/test_setup.py:118–132` loads `tools/status-line.py` and reads `sl.LAYOUT`. Plan 04 introduces sibling-import requirements; Plan 05’s thin entry definitively removes `sl.LAYOUT`. Neither extraction plan permits editing this test, yet Plan 05 requires full gates. **Fix:** include and retarget this consumer during extraction, preserving its equality assertion and adding the necessary import path. Do not restore entry re-exports.

- **MEDIUM — The mechanical rewrite contract omits existing introspection and dynamic patch targets** (`23-05-PLAN.md:174–178`; `23-04:199–216`). Actual `tests/test_status_line.py:2872–2873` uses `hasattr(sl, "seg_alt_process_memory")`, and `:1410–1411` supplies a patch name through `patch_target`. These are not ordinary `sl.NAME` or literal-name patch rewrites. The positive introspection assertion fails against the thin entry, while its required operand change is outside the stated assertion-normalization contract. **Fix:** explicitly normalize introspection operands and resolved dynamic patch targets through the audit map, preserving the asserted names and expected results.

- **LOW — The scratch file list names the previous plan’s directory** (`23-05-PLAN.md:236,244`). Task 1 lists `tmp/p23/04/split_*.py`, but its action recreates and runs them under `tmp/p23/05/`; Plan 04 removes the former directory. **Fix:** make the task file list agree with the action and specify what reconstruction evidence Plan 04’s summary must retain.

### 23-06

**Strengths**

- ConfigSpec avoids the config/render dependency cycle.
- Final immutable HOST construction replaces the invalid NamedTuple-field assignment.
- The catastrophic-failure mock explicitly follows `claude_payload.core_build_context`.
- Claude provider namespaces remain oracle-gated.

**Concerns**

- **MEDIUM — Final verification can still mask an earlier gate failure** (`23-06-PLAN.md:340`; analogous remaining chains in Plans 09, 10 and 13–17). A failed `make test` chain can skip `make validate`, then execution resumes after a semicolon. A previous successful `validate.log` can satisfy subsequent greps and allow a successful final status. **Fix:** use explicit failure-propagating command execution, as already prescribed in Plan 07, and assert every exit status independently. Log matching must be supplementary evidence.

- **LOW — Two fixture criteria still leave the baseline ambiguous** (`23-06-PLAN.md:293`; `23-07-PLAN.md:255`). “Base sha” and “B from 23-01-SUMMARY.md” no longer identify one reference, because that summary now records both `production_base` and `oracle_commit`. Choosing the former makes an empty fixture diff impossible. **Fix:** explicitly name the completed `oracle_commit` in both criteria.

### 23-07

**Strengths**

- Claude-specific context readers are enumerated before neutralization.
- Claude null coalescing and exact gauge boundary behavior are preserved.
- The cold-entry deadline now allows both production git timeouts plus overhead; the direct probe retains its short patched deadline.

**Concerns**

No additional plan-specific concern. Apply the runner correction under **23-04**, explicit oracle baseline under **23-06**, and execution-barrier correction under **23-08**.

### 23-08

**Strengths**

- The operative contract now requires conservative interpreter/exact-script ownership parsing, including suffix and data-argument counterexamples.
- TOML source removal now depends on successful publication; lost races retain the source.
- These changes resolve both cycle-1 migration HIGH findings without reopening the hard-rename decision.

**Concerns**

- **MEDIUM — The required reference fix remains outside permitted edit scope** (`23-08-PLAN.md:7–31,249,256–257`). Task 1 explicitly requires updating `tools/hooks/precompact_core.py`, but that file is absent from frontmatter and the task file list. Following the staging restriction leaves the reference gate failing or the required change uncommitted. **Fix:** add the file to both scope lists.

- **MEDIUM — Serialized wave barriers remain a disposition, not an executable scheduling contract** (`23-08-PLAN.md:37,274,326,359–364`; corresponding checks in other parallel waves). Task bodies and `orchestrator_verify` still demand project-wide gates and a globally clean tree immediately after each plan, while sibling executors can have legitimate unfinished work. No dependency or task-body instruction assigns those checks exclusively to a post-wave barrier. **Fix:** either serialize affected plans or move global gates and global cleanliness to an explicit orchestrator-owned wave barrier. Executors should verify their own scope and preserve sibling changes.

### 23-09

**Strengths**

- Dependency, host-import and networking checks retain live coverage and non-vacuity counterparts.
- Forbidden examples are now assembled without making the reference test match itself.
- The architecture documentation and AGENTS updates remain assigned.

**Concerns**

No additional independent concern. Its Task 3 verification still needs the failure-propagation correction under **23-06** and barrier correction under **23-08**.

### 23-10

**Strengths**

- Missing or failed hard-limit evidence now produces unavailable team quota, resolving the cycle-1 HIGH.
- Billing-end precedence and fallback now have explicit cases.
- Strict numeric parsing, inferred confidence and separate fetch/attempt timestamps remain well specified.

**Concerns**

- **MEDIUM — The replacement normalization contract drops the remaining team/pooled-limit branch** (`23-10-PLAN.md:28,265–279`; `23-CONTEXT.md:105–116`). The revised summary describes individual limits followed by ordinary hard-limit handling, but omits locked D-10’s team branch when hard-limit evidence is present. Its only team-specific case supplies no hard limit. **Fix:** explicitly retain the first-party team branch and add cases for individual-limit precedence, present hard-limit evidence, positive pooled limit and absent/zero pooled limit, including units. This completes D-10; it must not reverse the corrected missing-hard-limit result.

### 23-11

**Strengths**

- Endpoint validation precedes credential access.
- Redirect refusal, unsupported auth, torn reads and token-free diagnostics remain covered.
- The total-deadline requirement and slow-trickle test are now in task bodies, not merely the ledger.

**Concerns**

- **MEDIUM — Several PID-cleanup dispositions remain contradicted by task commands** (`23-11-PLAN.md:279–281`; `23-12:286–289`, `23-13:353–355`; also `23-08:320–321`). These still prescribe broad `ps | awk` argument matching. In Plan 11, the checker’s own argv contains `cursor_fakes`, so it can report itself as a leak. **Fix:** remove the broad scans and assert termination/reaping of recorded child identities and relevant descendants. Do not kill processes selected by these patterns.

The missing owner-probe implementation is counted under **23-03**.

### 23-12

**Strengths**

- Cache-only rendering, DEVNULL stdio, detached sessions and 0600 atomic cache publication remain explicit.
- Ownership-aware release and multiprocess contention requirements have been added.
- Negative caching and auth-based hiding remain covered.

**Concerns**

- **HIGH — Verification cleanup can delete an inherited non-scratch directory** (`23-12-PLAN.md:258`; also `23-14:249`, `23-15:232`). `D=$(mktemp -d)` is conditional on an earlier `&&` chain succeeding, but `rm -rf "$D"` runs unconditionally afterward. If a prerequisite fails and the shell inherited `D`, cleanup targets that existing value. Quoting does not establish ownership. **Fix:** initialize a dedicated scratch variable unconditionally, create it under `tmp/p23/<plan>/`, register cleanup only after successful creation, and constrain cleanup to that generated directory while preserving the verification status. Adding `set -e` alone is insufficient.

- **HIGH — The lock protocol still admits successor takeover and unchecked handoff** (`23-12-PLAN.md:25,144–149,175–181,247–252`). “Atomic rename-to-claim” alone does not serialize reclamation: a delayed contender can rename a successor’s newly created lock. Task 1 also says the child rewrites the lock with its own PID without specifying a checked parent-to-child handoff. The boolean acquisition and pathname-only release APIs do not carry an acquisition identity. **Fix:** choose one complete protocol—such as a persistent sibling advisory lock—covering acquisition, reclamation, handoff, publication and release. Carry a unique acquisition identity and reject delayed-child or stale-owner actions. Do not start a replacement while the prior fetch can still publish. This remains a contradiction of **SPEC R9 and locked D-13/D-16**, not an authorized shortcut.

- **MEDIUM — Kill coverage still does not prove real abandoned-refresher recovery** (`23-12-PLAN.md:152–155,276–290`). The introduction says to kill the real refresher and then expect it to write a negative cache; Task 2 still uses a generic marker-writing `refresh_child`. **Fix:** specify two distinct tests: kill the render parent and prove its real refresher survives; then kill the actual refresher after lock acquisition and prove competing processes recover with exactly one replacement fetch and an eventual valid cache. Remove the generic-child substitute.

### 23-13

**Strengths**

- Four independently placeable segments, API-off defaults, per-segment windows and inferred/stale markers follow the locked decisions.
- Q1’s provider namespace is retained.
- Fresh-cache rendering and shared-gauge identity receive explicit tests.

**Concerns**

No additional independent concern. Apply tracked-PID cleanup under **23-11**, failure propagation under **23-06**, and wave barriers under **23-08**.

### 23-14

**Strengths**

- Host selection is now required to validate before migration or any other write, resolving the cycle-1 HIGH.
- Detection, refresh and uninstall reuse the exact ownership classifier.
- Fresh-content reclassification, sibling-key preservation and refusal matrices remain strong safeguards.

**Concerns**

No additional independent concern. Its Task 1 cleanup has the **HIGH arbitrary-path deletion defect counted under 23-12**.

### 23-15

**Strengths**

- Explicit fake injection, call-time defaults and network denial repair the cycle-1 mock escape.
- Manual quota diagnostics are distinguished from offline structural validation and dry rendering.
- Claude’s default output remains a preservation requirement.

**Concerns**

No additional independent concern. Apply the cleanup correction under **23-12**. The conflicting persistence invocation is counted under **23-16**.

### 23-16

**Strengths**

- Task 1 now includes the production `cmd_install` result consumer and examples handling.
- Zero-host and Cursor-only flows are explicitly valid, resolving those cycle-1 HIGH design omissions.
- The final host-keyed seam avoids a temporary first-host-only implementation.

**Concerns**

- **HIGH — Persistence still explicitly invokes the network-active doctor** (`23-16-PLAN.md:328–336`; `23-15-PLAN.md:217–228`). Task 3 validates saved Cursor TOML with `statusline-doctor.py --doctor --host cursor`, while Plan 15 reserves that invocation for foreground credential-backed fetching. This contradicts the new offline requirements. Actual `tools/setup.py:463–519` reinforces the dangerous interpretation: publish, inherit the environment, run `--doctor`, then potentially roll back. **Fix:** replace the invocation with an explicitly named offline structural-validation and synthetic dry-render path before publication. Retain zero-fetch and zero-spawn assertions. The cycle-1 HIGH is not closed by the review note.

- **MEDIUM — The prescribed setup verification can still skip wizard seam coverage** (`23-16-PLAN.md:259–265,307–311`). `tests.test_setup` runs under system Python, then uv runs the integration group—which excludes that module. Actual setup tests include Textual-guarded coverage. **Fix:** explicitly run the relevant setup coverage through the parallel runner under uv, using positional module arguments, and establish that critical cases ran rather than accepting skips.

- **MEDIUM — Task actions still require copied defaults despite binding Q2** (`23-16-PLAN.md:148–149,301–302`; `23-08-PLAN.md:267–268`). Task 2 says to add `CURSOR_SEGMENT_DEFAULTS` and `CURSOR_LAYOUT_DEFAULTS`; Plan 08 preserves Claude duplication under a new justification. That contradicts the lazy-host-import ruling and the claimed disposition. **Fix:** remove those instructions and obtain defaults from lazily resolved host configuration. Retain only necessary presentation metadata and conversion tests. This finding explicitly concerns a contradiction of **orchestrator ruling Q2**.

### 23-17

**Strengths**

- Exact host-labelled prompts, backward navigation and independent host outcomes are specified.
- Real two-host PTY scenarios preserve the declined-host guarantee.

**Concerns**

- **MEDIUM — The claimed system-memory driver migration remains outside scope and tasks** (`23-17-PLAN.md:7–12,228–247,253–267`). The ledger says `tests/test_system_memory_e2e.py` is included, but neither frontmatter nor task file lists include it. Actual `tests/test_system_memory_e2e.py:145–163` still matches accumulated bare screen words; its fixture also names a Claude directory without creating it at `:210–234`. **Fix:** include the file, explicitly migrate to exact current-screen prompts with consumed/reset output, and create the Claude directory where the fixture intends a detected host.

### 23-18

**Strengths**

- Completed-oracle comparison replaces the incorrect production-base comparison.
- Owner-only work remains pending rather than being represented as live verification.
- POC deletion remains limited by the owner-authorized D-12 intent.

**Concerns**

- **MEDIUM — The independent owner-status assertion cannot validate its specified table** (`23-18-PLAN.md:198`; table contract `23-03-PLAN.md:388`). The doubled-backslash raw regex has empty alternatives and matches arbitrary lines. The table is Step/Evidence/Result, but `split("|")[2]` reads Evidence rather than Result. It also fails to require the complete unique step set. **Fix:** parse the specified columns, require every required ID exactly once, and assert each Result is exactly `not run (owner)`. Keep checker output and exit-status evidence separate.

- **MEDIUM — POC deletion verification does not establish exact targeting or absence** (`23-18-PLAN.md:190–199`). `raw.split("\\n\\n")` splits literal backslash sequences rather than porcelain records; substring branch matching also accepts a suffixed branch name. The automated check never verifies backup absence. A symlinked intermediate `tmp` directory can escape the intended worktree despite a safe root. **Fix:** parse actual record separators and exact branch fields, enforce the stated parent constraint, reject symlinked traversed directories, and verify absence using the identical authorized pathname. Do not inspect backup contents.

- **MEDIUM — Close-out omits the active run’s clean-room gate** (`23-18-PLAN.md:154–164`; `.planning/goals/2026-10-14-v1.3-phases-16-27.md:79–82`). The five prescribed gates omit `make e2e-docker`, required by the run contract for phases changing `tools/*.py`. Existing-environment success does not establish clean-room bootstrap/wizard behavior. **Fix:** add the orchestrator-run gate, exit/log evidence and container/process cleanup evidence.

## Overall Risk

**High until the cleanup, lock protocol and persistence contradictions are corrected.**

The byte-identical Claude strategy remains sound in principle, but extraction currently breaks an unowned consumer and lacks a complete mechanical rewrite contract. Verification is also not yet dependable: unsupported commands, malformed blocks, masked failures and ledger-only scheduling fixes can prevent completion or overstate evidence.

The cycle-1 HIGH fixes for migration ownership, TOML lost-publication races, missing-hard-limit classification, before-write host validation, doctor mock injection, host-keyed result consumption and zero-host design are present in the revised contracts. **Single-flight and offline persistence remain unresolved.**

Not checked: runtime tests, live CLIs, network behavior or actual 3600-second completion time. No files or git state were changed, and no protected configuration, credential files or POC backups were read.

CYCLE_SUMMARY: current_high=3 current_actionable=22


## Ponytail review, cycle 2 (verbatim)

What this change does: The plans split the Claude renderer, add the required cache-backed Cursor line, and extend setup, doctor and wizard to both hosts. I used the ponytail-review approach against all 18 plans, the governing documents, cycle-1 dispositions and connected source. No required feature is proposed for removal.

**Cycle-1 HIGH check:** exact command ownership, conditional TOML-source deletion, missing-hard-limit classification, doctor fetch injection, the omitted `cmd_install` consumer and zero-host handling now have corrective task instructions. Locking and offline save validation remain incomplete or contradictory, as detailed below. Host-selection validation is stated correctly, but its decisive regression test is still missing.

Paths below are relative to `.planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/`. Savings are estimates, not measured diffs.

## HIGH

1. **Saving TOML still explicitly invokes the network-active doctor** — `23-16-PLAN.md`, Task 3, lines 328–336; `23-15-PLAN.md`, Task 1.
   - **Problem:** Plan 16’s revised requirements say validation is offline, but Task 3 still specifies `statusline-doctor.py --doctor --host cursor`. Plan 15 explicitly makes that invocation fetch quota. Existing `write_toml_preserving()` publishes the candidate before invoking the doctor and rolls back afterward (`tools/setup.py:463–519`), so merely adding host arguments preserves the original defect.
   - **Smaller complete change:** Specify one offline candidate-validation path: structural checking plus synthetic-quota dry rendering, followed by one atomic publication. Thread the host through the existing persistence chain, including `_recover_incompatible_config()`—its current `--check` invocation is Claude-only—and keep manual quota diagnostics separate. Remove the contradictory Task 3 command.
   - **Estimated saving:** **30–60 lines of network/rollback plumbing**, plus avoidance of a second persistence implementation. This cycle-1 HIGH is not resolved by the ledger wording.

2. **“Atomic rename-to-claim” still permits the expired-lock race** — `23-12-PLAN.md`, lock contract at line 25 and Tasks 1–2.
   - **Problem:** Renaming `usage.lock` to a claim file is atomic, but it does not prove it is the expired file previously inspected. Contender A can move the expired lock, contender B can then move A’s replacement, and both can refresh. The task also transfers ownership by rewriting the lock, while the declared acquire/release interface carries no acquisition identity.
   - **Smaller complete change:** Choose the already-listed sibling `fcntl` lock rather than leaving two algorithms available. Use it to serialize every ownership transition: acquisition, parent-to-refresher transfer, reclamation and release. Carry an acquisition identity through those operations. Test a contender paused between observing expiry and attempting takeover, and an expired-but-still-running refresher.
   - **Estimated saving:** **One competing locking design and its tests**; no honest net line reduction promised. Removing this validation would cut below SPEC R9’s single-flight guarantee.

## MEDIUM

3. **The task still tests a marker-writing child, not refresher recovery** — `23-12-PLAN.md`, Task 2, lines 277–289.
   - **Problem:** The new introductory text promises the production path, but the behavior table still calls `probe_spawn_detached()` with a generated `refresh_child` that writes a marker. That passes with broken refresher argv, cache handling or lock cleanup. Killing a render and letting its child survive also does not prove recovery after the *refresher* dies.
   - **Smaller complete change:** Replace the marker test with the real `probe_read_quota()` → refresher path under scratch HOME, asserting an `auth_missing` negative cache and lock cleanup. Add the separate required case that kills a real refresher after lock acquisition and proves subprocess contenders recover it once.
   - **Estimated saving:** **20–40 throwaway test lines**, replacing weak evidence rather than deleting required coverage. The cycle-1 disposition has not reached the task table.

4. **Duplicate defaults and the duplicate resolver remain in executable instructions** — `23-16-PLAN.md`, Task 2, lines 300–302; `23-14-PLAN.md`, Task 1, lines 234–239; `23-08-PLAN.md`, Task 1, lines 266–268.
   - **Problem:** Plan 16 still instructs the executor to add `CURSOR_SEGMENT_DEFAULTS`, `CURSOR_LAYOUT_DEFAULTS` and `STATUSLINE_HOSTS`, despite its revised prohibition on copied tables. Plan 14 still prescribes a second resolver plus parity testing, despite its ledger promising reuse. Plan 8 still describes retaining duplicated Claude defaults as Q2.
   - **Smaller complete change:** Read defaults and prefixes lazily from `HOST.config`; convert layout values only at the wizard boundary. Derive Cursor’s directory from the shared `resolve_runtime_config_paths()` implementation after fixing blank-value handling there. Test expected precedence, not agreement between two implementations.
   - **Estimated saving:** **70–130 production/test lines** and several synchronized tables. These cycle-1 duplication findings remain unresolved in the task bodies.

5. **Deleting the disposable mover now forces the next plan to rebuild it** — `23-04-PLAN.md`, Task 3, line 356; `23-05-PLAN.md`, Task 1, line 244.
   - **Problem:** Plan 4 removes its scratch directory. Plan 5 then recreates the mover, rewriter and assertion checker from notes, although it must reproduce the same earlier stages before applying stage 3. Plan 4’s own orchestrator verification also expects the deleted checker to exist.
   - **Smaller complete change:** **Merge 04 + 05 into one mechanical-move workstream**, retaining the staged commits and purity gates. Keep its scratch tools until the final stage and orchestrator checks finish, then remove them once. Keep resumable execution boundaries rather than requiring one uninterrupted run.
   - **Estimated saving:** **One three-script reconstruction, one handoff and one duplicate verification setup**. Committed code savings are near zero because the tools are already designated disposable.

6. **The wizard’s final flow is still assigned to two implementation plans** — `23-16-PLAN.md`, Task 1, lines 250–262; `23-17-PLAN.md`, Task 1, lines 228–234.
   - **Problem:** Plan 16 now requires final host-indexed accessors and traversal, explicitly rejecting the temporary first-host design. Plan 17 then independently implements that traversal, per-host models, boards and gate state. Meanwhile Plan 16’s objective and success criteria still say Plan 17 will supply the flow.
   - **Smaller complete change:** **Merge 16 + 17 into one wizard workstream.** Implement seam and traversal once; retain separate commits for host-aware persistence and real PTY acceptance. If execution units must stay separate, make 17 acceptance-and-documentation only, not another flow implementation.
   - **Estimated saving:** **One implementation handoff and roughly 40–80 lines of intermediate adapters/test churn**. All gates, navigation and declined-host behavior remain.

7. **The deferred owner probe has no implementing task** — `23-03-PLAN.md`, Task 3, lines 368–373; `23-11-PLAN.md`, Tasks 1–2.
   - **Problem:** Plan 3 correctly removed its duplicate transport and delegates `spike_probe.py` to Plan 11. Plan 11’s file list, task actions and verification never create that probe or run its promised self-test. Its public fetch result is normalized data, whereas the owner kit also needs redacted response evidence and sequential/concurrent timings.
   - **Smaller complete change:** Assign the deferred probe explicitly to Plan 11, reusing production transport and keeping credential handling inside `cursor_quota.py`. Give the wrapper only timing, redaction and evidence formatting; add its canned self-test to that plan’s verification.
   - **Estimated saving:** Preserves the cycle-1 **100–180-line duplicate-client saving** and avoids a later gap plan. No new transport implementation is needed.

8. **Invalid host selection lacks the test that proves “before any write”** — `23-14-PLAN.md`, Tasks 1–2; `23-08-PLAN.md`, Task 2.
   - **Problem:** The revised requirement correctly orders validation before migration and other writes. The task’s error cases still only assert that invalid selection writes no file in a simple fixture. Existing `cmd_install_headless()` performs replacement/linking before wiring (`tools/setup.py:3583–3596`), and Plan 8 adds early migration. A wiring-time rejection can therefore pass those simple cases.
   - **Smaller complete change:** Add one table-driven scratch-tree snapshot test combining invalid/undetected host selection with legacy migration and requested skill/hook/example writes. Assert the complete tree is unchanged. Place selector validation explicitly at command entry.
   - **Estimated saving:** **One focused regression test instead of several shallow no-file tests**; little net line saving. This is the remaining verification gap for the cycle-1 HIGH, not a request to remove validation.

9. **The close-out assertion reads Evidence instead of Result** — `23-18-PLAN.md`, Task 2, line 198; table contract in `23-03-PLAN.md`, line 388.
   - **Problem:** Plan 3 defines `| Step | Evidence | Result |`. Plan 18 splits each row on `|` and checks `cells[2]`, which is Evidence; Result is `cells[3]`. Valid pending rows fail unless their evidence text accidentally matches. The assertion also does not require all seven owner rows to exist.
   - **Smaller complete change:** Reuse the checker’s parsed results and assert the exact required key set `S1`–`S7`, with every value equal to `not run (owner)`. Keep the checker output; remove this second ad-hoc Markdown parser.
   - **Estimated saving:** **One duplicate parser, approximately 5–15 lines**, and a reliable close-out check.

10. **Barrier-only gates and PID-based cleanup are still contradicted by task commands** — examples: `23-08-PLAN.md:320–326`, `23-12-PLAN.md:287–293`, `23-13-PLAN.md:353–359`.
    - **Problem:** Review ledgers say global gates/cleanliness run at serialized barriers and cleanup tracks spawned PIDs. Task bodies still run full gates and global clean-tree checks inside parallel plans, and still prescribe the self-matching `ps | awk` scans. Plan 3 was updated more thoroughly than its consumers.
    - **Smaller complete change:** Leave targeted checks in executor tasks; assign full gates and global cleanliness once per orchestrator-controlled wave barrier. Replace the remaining broad process scans with assertions against recorded child PIDs and descendants.
    - **Estimated saving:** **Several duplicate full-gate runs and roughly 30–60 lines of inconsistent verification commands**. Do not remove process cleanup or the final project-wide gates.

## LOW

11. **Plan 09 remains a separate reconstruction pass after its owning changes** — `23-09-PLAN.md`, Tasks 1–3.
    - **Problem:** The cycle-1 consolidation suggestion remains unaddressed. Split, namespace and spawn work already reopen `tests/test_arch.py`; Plan 9 later reopens it for dependency, networking, uniqueness and final-location checks.
    - **Smaller complete change:** Drop **09 as a standalone execution unit**, not its criteria: add dependency rules with the split, networking rules with transport, Cursor uniqueness with its host, and fold final references/docs into 08. Keep every required non-vacuity test.
    - **Estimated saving:** **One execution plan and three handoffs/commits**; little test-code deletion. Together with **04 + 05** and **16 + 17**, this reduces 18 execution units to about **15** without dropping a feature.

**Verdict:** Fix 1–2 before execution, then reconcile the remaining task-body/ledger disagreements. Keep normalization, transport and cross-process refresh as separate work units; those are useful boundaries.

Not checked: tests, live CLI behavior, network behavior or execution-time budgets. No files or git state were changed, no AI CLI/network calls were made, and no protected config or credential files were read.

PONYTAIL high=2 medium=8 low=1


# Cycle 3 (2026-10-23, final)

## Cross-AI plan review, cycle 3 (verbatim)

## Summary

**Revise before unattended execution.** Cycle 3 finds **3 HIGH concerns and 14 additional actionable concerns**. Shared findings are counted once and cross-referenced below.

Most earlier HIGH findings now have substantive fixes in task bodies: exact command ownership, conditional TOML-source removal, validation before other writes, doctor fake injection, offline persistence validation, host-keyed result handling, and zero-host support. Two areas remain problematic: **missing-hard-limit normalization has regressed**, and **the flock design lacks a complete inherited-descriptor lifecycle**. A newly identified unsafe E2E fixture can also reach real host configuration through inherited environment overrides.

Read-only checks confirmed:

- The renderer still has **134 functions + 7 classes + 41 assignments = 182 audit rows**.
- Dependencies are topologically consistent, with **no same-wave overlap among declared `files_modified` paths**.
- All **43 actual task verification bodies** parse with `bash -n`.
- No `tail -N | grep` pattern was found.
- Shell syntax passing does **not** resolve the failure-propagation defects below.

Plan references are relative to `.planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/`.

### 23-01

**Strengths**

- Establishes raw-ANSI, entry-subprocess, and strict-provider oracles before extraction.
- Separates `production_base` from the completed `oracle_commit`.
- Explicitly controls timezone, locale, and scratch-root portability.

**Concerns**

- **HIGH — The first full-suite barrier can execute an unsafe existing fixture** (`23-01-PLAN.md:17`; `tests/test_system_memory_e2e.py:228–237`). That fixture inherits `CURSOR_CONFIG_DIR`, `PI_CODING_AGENT_DIR`, and `OPENCODE_CONFIG_DIR` while replacing HOME and only some roots. With an inherited real Cursor directory, the wizard’s default-on session-briefing hook reaches `wire_hook_cursor()` and can write its real `hooks.json`, pointing it at the temporary installation subsequently deleted. This is an existing fixture defect exposed by the prescribed gates, not an observed write. **Fix:** isolate every host/config/state root before the first wave’s `make test`; leave unintended host directories absent. Add a synthetic outside-scratch sentinel test proving inherited overrides cannot escape. Do not postpone this safety fix until Plan 17.

- **MEDIUM — Wave-barrier ownership remains contradicted by executable task instructions** (`23-10-PLAN.md:279–285`, `23-11-PLAN.md:286–287`, `23-15-PLAN.md:265–266`). Plans 10 and 11 still run whole-unit/project checks while Plans 04 and 05 modify the renderer and its consumers. Plan 15 explicitly runs `make test` and `make validate` while Plan 09 edits architecture tests. These checks can observe legitimate intermediate sibling changes despite the new barrier wording. **Fix:** remove those executor-side project-wide commands and place them exclusively at the existing post-wave barriers; retain targeted checks locally. Apply the same rule consistently to remaining whole-project executor checks. Counted once here.

### 23-02

**Strengths**

- The 182-row audit and pinned taint vocabulary match the current source.
- `core_default_theme` is correctly classified as generalized.
- Ordered rows, hashes, reviewed reasons, and non-vacuity checks provide useful extraction controls.

**Concerns**

No additional independent concern. The shared execution-barrier concern is recorded under **23-01**.

### 23-03

**Strengths**

- Keeps synthetic evidence separate from owner-only observations.
- Uses loopback fakes and tracked child identities.
- Reuses production transport rather than introducing another credential-handling implementation.

**Concerns**

- **MEDIUM — Task 1’s successful negative check fails under `set -e`** (`23-03-PLAN.md:310`). The final brace executes `grep <forbidden-bind-pattern>; test $? -eq 1`. When the forbidden pattern is correctly absent, grep returns 1 and the shell exits before the status assertion. **Fix:** use an explicit conditional that accepts status 1, rejects status 0, and propagates actual grep errors. This differs from Plan 01’s non-final `&&` brace, where errexit is suppressed.

- **MEDIUM — Task 3 deletes the directory its verification immediately needs** (`23-03-PLAN.md:393,397`). The action removes `tmp/p23/03`, but verification redirects checker output to `tmp/p23/03/check.log` without recreating it. The redirect fails before the checker runs. **Fix:** recreate the directory at verification entry or postpone cleanup until verification finishes.

- **LOW — The probe now has contradictory implementation owners** (`23-03-PLAN.md:369,374,410–418`; `23-11-PLAN.md:244–246`). Plan 03 still says Plan 11 tasks do not create `spike_probe.py` and delegates it to “the first plan after 23-11.” Revised Plan 11 explicitly creates and tests it. **Fix:** make Plan 11 the sole owner and remove the stale deferred implementation assignment. The earlier missing-owner finding itself is resolved.

### 23-04

**Strengths**

- Retains disposable extraction tools through Plan 05 and orchestrator verification.
- Introduces Rule 5’s wrapper before the task that needs it.
- Explicitly handles introspection and dynamic mock targets.
- Adds task-commit resume boundaries and verification headroom.

**Concerns**

- **MEDIUM — Another setup-test consumer remains unmigrated** (`23-04-PLAN.md:297–300,320,327–334`). The special setup repair handles `LAYOUT`, but `tests/test_setup.py:477–490` separately loads the monolith and asserts equality with `sl._SEG_HEADER_RE.pattern`. That constant moves to `common_config` in stage 2; the prescribed three-file rewriter does not cover this setup test. The required six-module gate therefore fails. **Fix:** add `tests/test_setup.py` to Task 2’s file list and retarget this drift guard to `common_config._SEG_HEADER_RE`, preserving its equality assertion. This also prevents the later thin-entry failure in Plan 05.

### 23-05

**Strengths**

- Isolates the one intentional registry generalization.
- Keeps exact generalized-mismatch checking checkpoint-only.
- Preserves the completed-oracle baseline and thin-entry checks.
- Reuses retained extraction tools rather than reconstructing them.

**Concerns**

No additional independent concern. The missed regex drift guard is counted under **23-04**.

### 23-06

**Strengths**

- `ConfigSpec` avoids the config/render dependency cycle.
- Immutable HOST construction replaces the invalid field assignment.
- Catastrophic-failure mocking follows the adapter’s lookup namespace.
- Task 2 now independently propagates full-gate failures.

**Concerns**

No additional independent concern identified.

### 23-07

**Strengths**

- Enumerates Claude-specific Context readers before moving them.
- Preserves Claude null coalescing and exact gauge arithmetic.
- Allows both production git timeouts in the entry-level deadline.
- Names `oracle_commit` unambiguously.

**Concerns**

- **MEDIUM — Nullable typing lands before the shared segment can type-check** (`23-07-PLAN.md:230,243–249,265,276–280`). Task 1 changes `context_pct` and `context_max` to `int | None` and requires pyright green. The unchanged `seg_context` still calls `int(ctx.context_pct)` and `fmt_tokens(ctx.context_max)` (`tools/status-line.py:2442–2454`). Its guards are assigned only to Task 2, and `common_segments.py` is absent from Task 1’s scope. **Fix:** move the nullable guards and focused tests into Task 1, including that file in its task list. Leave gauge generalization in Task 2.

### 23-08

**Strengths**

- Exact interpreter/script ownership and suffix/data-argument counterexamples resolve the migration-ownership HIGH.
- Source removal now requires successful TOML publication.
- The required `precompact_core.py` reference update is in scope.
- Preserves the locked hard rename without a compatibility façade.

**Concerns**

No additional independent concern. The earlier lost-publication and foreign-command HIGH findings are resolved in the operative contract.

### 23-09

**Strengths**

- Retains live dependency, host-import, networking, and uniqueness checks with non-vacuity counterparts.
- Constructs forbidden reference examples without self-matching.
- Assigns AGENTS updates and stale architecture-document removal.
- Explicitly separates its executor checks from the wave barrier.

**Concerns**

No additional independent concern. Plan 15’s conflicting same-wave full-gate instructions are counted under **23-01**.

### 23-10

**Strengths**

- Specifies strict numeric parsing, optional percentages, billing-date precedence, and inferred confidence.
- Separates successful-fetch and failed-attempt timestamps.
- Covers freshness and cycle-end boundaries.

**Concerns**

- **HIGH — The missing-hard-limit result again contradicts locked D-10** (`23-10-PLAN.md:28,269,278–279`). The revised contract makes absent hard-limit evidence plus positive `pooled_limit` become `fixed`; `usage_team` supplies that counterexample. CONTEXT D-10 explicitly says failed or absent `GetHardLimit` is `unavailable`, and no October 23 ruling authorizes this exception. **Fix:** retain `unavailable` for the missing/failed-hard-limit case and add `core_normalize(usage_team, None, …)` as the exact regression. Any exception requires a formal amendment to the locked decision, not a review-ledger explanation.

- **MEDIUM — Verification can still report success after failed tests** (`23-10-PLAN.md:247,285`; also verification bodies in Plans 11–17 and `23-18:165,199,229`). These semicolon-separated bodies generally lack fail-fast handling. For example, Plan 11 Task 2 can ignore both a failed quota suite and its failed result grep, then return success from the final secret scan. Plan 18 Task 2 runs the audit assertion before enabling `set -e`, allowing that failure to be masked too. **Fix:** explicitly propagate every required command’s status, including pipeline producers; use `set -euo pipefail` where appropriate and explicit handling for expected nonzero results. Keep log greps supplementary. Counted once here.

### 23-11

**Strengths**

- Validates endpoints before credential access.
- Specifies exact hostname boundaries, redirect refusal, unsupported auth, and torn-read handling.
- Requires a total deadline covering slow response bodies and executor shutdown.
- Now explicitly owns the production-backed owner probe and its self-test.

**Concerns**

No additional independent concern. Apply the shared verification and barrier fixes under **23-10** and **23-01**.

### 23-12

**Strengths**

- The binding persistent flock decision removes expiry-reclamation races.
- Retains cache-only rendering, detached sessions, DEVNULL stdio, and 0600 publication.
- Replaces the marker-child substitute with real parent-kill and refresher-kill scenarios.
- Repairs the earlier inherited-variable cleanup defect.

**Concerns**

- **HIGH — The inherited flock has no complete child-adoption or parent-release contract** (`23-12-PLAN.md:173–181,240–253`). The parent passes `lock_fd` with `pass_fds`, but argv identifies no descriptor, the environment is passed unchanged, and neither `main()` nor `probe_refresh()` accepts the inherited descriptor. Reopening and locking the pathname is a new open-file description, not adoption. Conversely, calling the declared unlock-and-close helper in the parent unlocks the child’s shared lock too. **Fix:** pass the descriptor number explicitly, thread it through the child interface, and distinguish parent **close-only after successful spawn** from worker **unlock-and-close after publication**, with appropriate spawn-failure cleanup. Standalone `--refresh` acquires its own lock. Test a live parent and fetching child against another contender. This completes the locked flock decision; it does not reopen it.

- **MEDIUM — Delayed stale readers can trigger redundant sequential refreshes** (`23-12-PLAN.md:178–180,240–253,279`). Two processes can observe stale cache; one refreshes and releases the lock, then the delayed reader acquires it and refreshes again using its old observation. **Fix:** re-read the cache and re-evaluate `core_needs_refresh` after acquiring the lock, before spawning or fetching. Add a synchronized subprocess case that pauses one reader until the other publishes.

### 23-13

**Strengths**

- Preserves four independently placeable segments and API-off defaults.
- Uses per-segment windows, shared gauge identity, local reset time, and inferred/stale markers.
- Retains the amended provider namespace and fresh-cache render isolation.

**Concerns**

No additional independent concern. Shared verification failure propagation is counted under **23-10**.

### 23-14

**Strengths**

- Host selection is explicitly validated before migration or other writes.
- The full-tree snapshot combines invalid selection with migration and requested operations.
- Uses the shared ownership parser for detect/wire/unwire.
- Reuses the existing Cursor resolver rather than maintaining a second implementation.

**Concerns**

No additional independent concern. The earlier before-write validation HIGH is resolved in the task contract.

### 23-15

**Strengths**

- Call-time defaults, explicit fake injection, and network denial repair the mock escape.
- Separates manual quota diagnostics from offline save/preview validation.
- Preserves default Claude doctor behavior and labels Cursor confidence.

**Concerns**

No additional independent concern. Its Task 2 full-gate instructions and verification failure propagation are counted under **23-01** and **23-10**.

### 23-16

**Strengths**

- Includes the production `cmd_install` result consumer.
- Explicitly supports zero-host and Cursor-only flows.
- Owns the final host-keyed flow rather than an intermediate first-host implementation.
- Removes the network-active persistence doctor and explicitly requires offline validation before publication.
- Uses lazily obtained host defaults.

**Concerns**

- **MEDIUM — Existing PTY prompt migration arrives after the gate that requires it** (`23-16-PLAN.md:246–262`; `23-17-PLAN.md:223–229`). Plan 16 implements host-labelled prompts and must pass integration, but existing `tests/test_wizard_pty.py:525,649,910` waits for `Wire your status line?`. That file is outside Plan 16’s scope; Plan 17 migrates it later. **Fix:** move existing matcher repairs and file ownership into Plan 16 Task 1. Leave new two-host acceptance scenarios in Plan 17.

- **MEDIUM — Cursor provider discovery is assigned, but its installation destination is not** (`23-16-PLAN.md:253–255,284,297–305,333–338`). Actual `install_example_segments()` hardcodes `config_dir/segments` (`tools/setup.py:778–790`). Merely making discovery host-aware can leave a Cursor layout referencing bundled `system_memory` while its executable is installed only in Claude’s directory. Structural validation can reject even an off-but-listed provider. **Fix:** explicitly migrate the installation helper and commit/post-wizard callers to the host provider directory. Test Cursor-only adoption with the example on and off, including `--examples` precedence, and assert installation under `segments-cursor`.

- **MEDIUM — The earlier 3600-second execution-control gap remains here** (`23-16-PLAN.md:246–346`). This dispatch now owns the complete seam and navigation, host construction, inventory, previews, and persistence, with repeated integration runs and three commits. Unlike revised Plans 04–06, it has no remaining-time threshold or resume procedure. **Fix:** add task-commit resume boundaries and verification headroom accounting for integration checks, or reduce the dispatch scope. This is an unresolved sizing risk, not an observed timeout.

### 23-17

**Strengths**

- Is now acceptance/documentation-only rather than a second flow implementation.
- Assigns exact current-screen matching and consumed/reset output.
- Includes the system-memory driver and creation of its intended Claude directory.
- Preserves declined-host and independent-outcome scenarios.

**Concerns**

- **MEDIUM — Its modified E2E driver is not run by its task checks** (`23-17-PLAN.md:223–232,260–273`). Both tasks touch `tests/test_system_memory_e2e.py`, but verification runs only the integration group. The runner places that module in **e2e**, not integration. **Fix:** add `uv run python tools/run_unittest_parallel.py tests.test_system_memory_e2e` to the task that changes it. Its environment isolation must already be repaired before earlier full-suite barriers, as recorded under **23-01**.

### 23-18

**Strengths**

- Keeps close-out with the orchestrator.
- Adds the clean-room Docker gate and cleanup evidence.
- Uses the completed oracle baseline.
- Keeps owner-only live work pending rather than claiming synthetic coverage proves it.

**Concerns**

- **MEDIUM — The exact owner-row assertion requires two rows its producer never promises** (`23-18-PLAN.md:199`; `23-03-PLAN.md:388–401`). Plan 03 specifies owner steps S1–S7. Plan 18 requires those seven **plus standalone `R5` and `R12` IDs**. A correctly produced seven-row table therefore fails. **Fix:** use the agreed S1–S7 schema, or explicitly add the extra rows to the producer and checker contract. The corrected Result-column parsing itself is sound.

- **MEDIUM — Automated deletion verification still proves neither exact targeting nor absence** (`23-18-PLAN.md:175–199`). The action now requires complete paths and symlink rejection, but its automated command only checks that at most one branch record matches. It never verifies the parent constraint, traversed directories, or backup absence. It succeeds while the backup still exists. **Fix:** use one checked path through authorization, deletion, and `lstat`-based absence verification; reject symlinked traversed directories and fail if the named backup remains. If the worktree cannot be identified, record removal as unverified rather than “gone.” Do not read backup contents.

## Overall Risk

**High until the normalization contradiction, flock lifecycle, and unsafe E2E environment are fixed.** The earlier offline-persistence HIGH is now resolved at the plan-contract level.

The Claude preservation approach remains strong, but the missed regex consumer, nullable-type ordering, and delayed PTY migration can stop execution before later plans repair them. Verification also still needs consistent failure propagation and barrier ownership before its green results are trustworthy.

Not checked: runtime tests, live CLIs/network behavior, or measured execution duration. No files or git state were changed; no protected configuration, credentials, or POC backups were read.

CYCLE_SUMMARY: current_high=3 current_actionable=14


## Ponytail review, cycle 3 (verbatim)

What this change does: The plans split the Claude renderer, add the required cache-backed Cursor line, and extend setup, doctor and wizard to both hosts. I used **ponytail-review** to check all 18 plans against SPEC, CONTEXT, RESEARCH, earlier reviews and connected source.

**Earlier HIGHs:** command ownership, lost-publication source deletion, pre-write host selection, doctor fake injection, result consumption, zero-host handling, unsafe scratch-variable cleanup and offline save validation now have corrective task instructions. Two areas remain problematic: the replacement lock protocol is incomplete, and normalization reintroduces an exception to the locked missing-hard-limit rule.

Paths below are relative to `.planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/`. Savings are estimates.

## HIGH

1. **The inherited lock descriptor never reaches the refresher’s declared interface** — `23-12-PLAN.md`, Task 1 and interfaces, lines 169–181, 240–253.
   - **Problem:** The parent acquires `flock` and passes its descriptor through `pass_fds`, but the child receives only `--refresh --cache-base`. Neither `main()` nor `probe_refresh()` accepts or identifies that descriptor. Reopening the lock creates a different file description and can conflict with the inherited lock. Also, calling the prescribed unlock helper in the parent would unlock the child’s shared lock.
   - **Smaller complete change:** Let the refresher acquire and own the flock itself, then **re-read freshness/negative-cache state under the lock before fetching**. Remove parent acquisition, descriptor inheritance and handoff plumbing. Concurrent renders may launch short-lived contenders, but only one fetches; SPEC requires single-flight refresh, not exactly one process launch. Test the actual child path and killed-holder recovery.
   - **Estimated saving:** **25–50 lines**, the descriptor-transfer protocol and its special cases. The switch to `flock` fixes expiry reclamation, but does not by itself complete this new protocol.

2. **Missing hard-limit evidence can again produce a fixed team quota** — `23-10-PLAN.md`, normalization contract line 28 and Task 2 line 269.
   - **Problem:** The task explicitly makes a positive pooled limit without hard-limit evidence `fixed`. CONTEXT D-10 says a failed or absent `GetHardLimit` is `unavailable`; cycle 1 identified that contradiction as HIGH. The cycle-2 ledger says it preserves that correction, but the task now adds an exception without a corresponding decision amendment.
   - **Smaller complete change:** Apply the locked unavailable result when `GetHardLimit` failed or is absent. Keep the required team/pooled branch for cases with the necessary evidence. Pin the failed-call-plus-positive-pooled-limit case in the table.
   - **Estimated saving:** **One unsupported fallback branch and approximately 10–20 implementation/test lines**. Do not turn incomplete evidence into a confident ceiling.

## MEDIUM

3. **A second setup-test loader still breaks the pure move** — `23-04-PLAN.md`, Task 2; `23-05-PLAN.md`, Task 1.
   - **Problem:** The revisions explicitly migrate the layout drift test, but miss `tests/test_setup.py:477–490`, `test_seg_header_regex_literal_matches_renderer`. It loads the old entry and reads `sl._SEG_HEADER_RE`. Stage 2 moves and renames that value; the thin entry cannot provide it. The required setup-suite gates therefore still fail.
   - **Smaller complete change:** Retarget this existing test to `common_config.SEG_HEADER_RE` during stage 2, preserving the pattern equality assertion. Add `tests/test_setup.py` to that task’s file list; no facade or replacement test is needed.
   - **Estimated saving:** **One obsolete importlib loader, roughly 7–10 lines**, and a predictable repair cycle.

4. **Host-labelled wizard flow lands before the tests that must accept it** — `23-16-PLAN.md`, Task 1, lines 247–258; `23-17-PLAN.md`, Task 1, lines 223–229.
   - **Problem:** Plan 16 now correctly owns the final flow and runs the entire integration group before committing. Existing PTY tests still wait for literal `Wire your status line?` prompts (`tests/test_wizard_pty.py:525,649,910`). Their matcher migration belongs to Plan 17, which depends on Plan 16. The system-memory driver/host-fixture repair is likewise deferred until after Plan 16’s full wave gate.
   - **Smaller complete change:** Move **existing matcher and fixture migrations** into Plan 16’s flow commit. Leave Plan 17 only the new two-host acceptance scenarios and documentation. Alternatively, **16 + 17 merge cleanly as one resumable wizard workstream**, with separate buildable commits.
   - **Estimated saving:** **One guaranteed failing intermediate gate and one cross-plan repair handoff**. No required coverage disappears.

5. **Verification blocks still discard earlier failures** — representative cases: `23-11-PLAN.md`, Task 2 line 292; `23-16-PLAN.md`, Task 1 line 262; `23-18-PLAN.md`, Task 2 line 199.
   - **Problem:** These bodies run independent commands separated by semicolons without initial failure propagation. In Plan 11, a failed quota test or probe self-test can be followed by a successful secret scan, yielding exit 0. Plan 18 runs the audit assertion before enabling `set -e`, so that assertion can fail and execution continue. Pipeline checks also need `pipefail`; `set -eu` alone does not preserve the producer’s failure.
   - **Smaller complete change:** Use one consistent failure-propagating shell form—`set -euo pipefail` for these Bash bodies—with the checker’s expected exit 1 captured in an explicit `if`. Keep temporary-directory initialization unconditional and cleanup registered afterward.
   - **Estimated saving:** **Repeated bespoke exit/log plumbing and at least one verification-debug cycle**. I checked all automated bodies with `bash -n`; syntax passes, but that does not establish correct failure status.

6. **Close-out still maintains a second, incompatible owner-results parser** — `23-18-PLAN.md`, Task 2 line 199; producer contract in `23-03-PLAN.md`, Task 3 lines 387–389.
   - **Problem:** Plan 3 creates rows **S1–S7**. Plan 18 now requires **S1–S7 plus R5 and R12**, so a correctly generated pending-owner table fails close-out. The column indexing is repaired, but the independent parser still disagrees with its producer.
   - **Smaller complete change:** Reuse the checker’s parsed results and assert exactly S1–S7, each once and each `not run (owner)`. R5/R12 are requirements covered by those steps, not additional result rows.
   - **Estimated saving:** **One duplicate Markdown parser, approximately 5–15 lines**, and removal of a deterministic close-out failure.

7. **Cursor wiring validates only part of the shape it promises to preserve** — `23-14-PLAN.md`, Tasks 1–2, especially lines 238–240 and 268–270.
   - **Problem:** The concrete validation contract checks `type` and non-empty `command`, then preserves timing/padding siblings for an owned entry. It does not specify rejecting invalid sibling values or extra keys. An owned entry with `timeoutMs: false`, negative padding or an unknown key can therefore pass the prescribed checks and remain invalid under the locked D-23 contract.
   - **Smaller complete change:** Add one small object-shape validator: allowed keys only, nonnegative integer padding, positive integer timing values, with booleans explicitly rejected. Use it for detection and writing; add a compact malformed-shape table.
   - **Estimated saving:** **One shared validation decision instead of separate detect/write interpretations**; likely **10–20 net lines added**, not removed. This is a trust-boundary check that should not be cut.

## LOW

8. **Plan 17 assigns the same new PTY scenarios to both tasks** — `23-17-PLAN.md`, Task 1 lines 223–225 and Task 2 lines 261–270.
   - **Problem:** Task 1 says to add/finish both-host PTY scenarios; Task 2 then adds/completes `TestTwoHostE2E` for the same adoption and decline paths, rerunning the integration group. The former implementation task has become a second acceptance task without a distinct deliverable.
   - **Smaller complete change:** After moving existing matcher repairs into Plan 16, **merge Plan 17 Tasks 1 and 2** into one acceptance-and-docs task. Keep both scenarios, navigation assertions, file checks and cleanup.
   - **Estimated saving:** **One task/commit handoff and one repeated integration run**. This is a clean task merge; normalization, transport and refresh should remain separate work units.

**Verdict:** Fix 1–2 before execution; reconcile 3–7 before relying on unattended gates. The required features and safeguards remain intact.

Not checked: runtime tests, live CLI/API behavior or execution-time budgets. No files or git state were changed; no AI CLI, network calls, protected configuration or credential files were accessed.

PONYTAIL high=2 medium=5 low=1


## Escalation at the cycle cap

jev ladder: Laya B (fallback, 0.44); decided by own reasoning: A. The orchestrator rules on the three remaining HIGHs (see 23-CONTEXT.md "Cycle-3 rulings"), a cross-AI amend run applies every cycle-3 fix, and the orchestrator verifies the HIGHs line by line before execution. Precedent: 21.3.
