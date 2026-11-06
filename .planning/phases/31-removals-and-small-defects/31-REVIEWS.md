---
phase: 31
cycle: 1
reviewers: [referee-two, referee-three]
reviewed_at: 2026-11-06T10:41:25-03:00
plans_reviewed: [31-01-PLAN.md, 31-02-PLAN.md, 31-03-PLAN.md, 31-04-PLAN.md, 31-05-PLAN.md, 31-06-PLAN.md]
models:
  referee-two: "router-env/my-referee-two"
  referee-three: "router-env/my-referee-three"
model_sources:
  referee-two: "pinned"
  referee-three: "pinned"
---

# Cross-AI Plan Review — Phase 31

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## Review conditions

Cycle 1, the only cycle for this phase (owner priority: speed), over the six plans at `e8e3761`. referee-one was away
and was not called. Each of the two reviewers was probed once with a one-word prompt (09:44). The prompts were split
into three batches (A 31-01 and 31-02; B 31-03 and 31-04; C 31-05 and 31-06). Each batch inlined PROJECT.md (first 80
lines), the ROADMAP Phase 31 section, the RMV-01..04, DEF-01 and JDG-04 requirement rows, 31-SPEC.md, 31-CONTEXT.md, a
pointer to 31-RESEARCH.md, the batch's plans, the source-grounding instructions, the ponytail lens, removal and
same-wave overlap checks, and the batch's plan coverage manifest. Each call ran through the opencode lane
(`review-lane invoke --slug opencode --as <instance>`), at most two at a time, each in its own process group, with a
15-minute no-output-growth stall watch. No retry was needed.

- **referee-two** (`router-env/my-referee-two`): probe OK in 7 s. Every batch produced full per-plan sections with
  `file:line` evidence: A 1425 s, B 1303 s, C 907 s. No stall, retry or quota stop.
- **referee-three** (`router-env/my-referee-three`): probe OK in 4 s. Every batch produced full per-plan sections
  with `file:line` evidence: A 910 s, B 981 s, C 398 s. No stall, retry or quota stop.

Both reviewers covered every plan, so each finding below was triaged once: first with jev-fast-decision (advisory),
then against the plan text and the source.

## OpenCode Review (referee-two)

### Batch A (31-01, 31-02)

### Cross-AI Plan Review — Phase 31, Batch 1 (31-01, 31-02)

All findings below were verified against the working tree at `tmp/wt-31` (HEAD `e8e3761`) and the 30.1/30.2 branches. Line anchors were spot-checked against the actual files, not taken from the plans' word.

#### 31-01

**Plan:** `.planning/phases/31-removals-and-small-defects/31-01-PLAN.md`

##### Summary

An unusually well-researched removal plan: virtually every line anchor I checked (router SKILL.md lines 3/58/79, `tests/test_ai_kit_spec_trust.py:17,439`, `tests/test_ai_kit_spec_legacy_config.py:12,437,449`, `tests/test_cross_ai_runner_e2e.py:851`, `tests/test_ai_kit_spec_e2e.py:17,77-89`, `tests/test_ai_kit_spec_runtimes_table.py:811,818,831,837`, `tests/test_arch.py:1315,1611-1627,1681-1688,3083`, `tests/test_quota_policy_text.py:17-18`, the guidance writer at `cross_ai_script.py:21-26,306,316,349,404` and `cli.py:218-237,785`, the guidance tests at `tests/test_curated_config_script.py:68-72,457-480,632-661,710-759`, `tests/test_ai_kit_spec_runner_dispatch.py:153-160`) is accurate to within two lines. The one real defect is in the acceptance machinery, not the edit list: the central R1 grep cannot ever return what the plan promises, because `ai_kit_spec_gsd` is a substring of the *kept* module `tests.test_ai_kit_spec_gsd_tools`, which the generated Makefile/pre-commit listings name forever.

##### Strengths

- **The edit inventory is complete and correct.** I ran the R1 grep today: 33 files match. Subtracting exactly the files Tasks 1–3 edit/delete leaves precisely the 10 paths claimed at `31-01-PLAN.md:207` — except the two generated files (see HIGH below). Nothing was missed, including hidden-file entries (`.pre-commit-config.yaml:15,71`, `tests/test_gate_scope.py:38`, `pyproject.toml:124`).
- **The `PAIR_RULE_SKILLS` slice pitfall is real and correctly fixed.** `tests/test_ai_kit_spec_runtimes_table.py:818` reads `REWRITTEN[:4]`; after the gsd entry leaves `REWRITTEN` (line 811), `[:4]` would silently pull in `ai-kit-gsd-curated-config` (line 812). The explicit-list replacement preserves today's semantics exactly.
- **The D-13 move is viable.** `TestGsdPurposeFilterInertness` (`tests/test_ai_kit_spec_gsd.py:1965-1993`) tests `execute_selection.resolve_execute_candidates`, and `execute_selection` is a kept `ai_kit_spec` module (`skills/ai-kit-spec-review/ai_kit_spec/execute_selection.py`) — the moved test imports only kept code, as claimed.
- **No hidden guidance caller breaks.** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_build.py:114` already calls `project_runner_command(...)` without `guidance`; the only `guidance=True` callers are `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_cross_ai.py:30` (deleted Task 2), `tests/test_curated_config_script.py:480` and `tests/test_ai_kit_spec_runner_dispatch.py:153-160` (both deleted Task 3). `_plan_rendered` (`cross_ai_script.py:194`) keeps its other caller at line 212, so keeping it is right.
- **Intermediate commits are buildable.** Task 2 keeps the `prior_value` asserts at `tests/test_ai_kit_spec_e2e.py:77,83,89` while the function still exists; Task 3 deletes function and asserts together.
- **Rebase notes verified exactly.** The 30.1 branch's README hunks are `@@ -70,10` and `@@ -111,59`, and the test_arch hunk is `@@ -1841,6 _BROAD_EXCEPT_BACKSTOPS` — all far from the regions Task 2 edits (1309-1315, 1611-1688, 3083).
- **Wave-1 file ownership holds.** 31-03 edits only `tools/setup.py`, `tools/install.sh`, `tests/test_setup.py`, `tests/test_install.sh`; 31-04 owns `routing.py`, `check_dogfood.py`, `plan_edit.py`, `goal_prompt.py` — no overlap with 31-01's files except the generated listings.

##### Concerns

- **HIGH — The R1 acceptance grep can never pass as written.** `ai_kit_spec_gsd` is a substring of the kept test module name `tests.test_ai_kit_spec_gsd_tools`, which appears permanently in the generated blocks of `Makefile:12` and `.pre-commit-config.yaml:15,71` (regenerated, never removed — the module is kept per Task 2's own edits to it at `31-01-PLAN.md:186`). I confirmed with `git grep -n 'ai_kit_spec_gsd' -- Makefile .pre-commit-config.yaml ...`: those lines match via `tests.test_ai_kit_spec_gsd_tools` alone. Therefore:
  - Task 2's acceptance "lists only these 10 paths" (`31-01-PLAN.md:207`) will list 12;
  - Task 3's "now lists only the seven" (`:241`) will list 9;
  - must_haves' "the search prints nothing after plan 05" (`:59`) and success criteria (`:278`) are unachievable — the same false claim propagates to `31-05-PLAN.md:71,192`.
  The SPEC's adjacency edge ("searches match the full removed names only") is simply not true for this regex. An executor hitting the Task 2 gate will stall or improvise. Fix is cheap: `ai_kit_spec_gsd(?![a-z_])` (a `\b` also works — `_` is a word char, so no boundary before `_tools`), or name the generated files as permanent exemptions.
- **MEDIUM — Task 3's `gsd_tools.py` docstring instruction mischaracterizes line 11** (`31-01-PLAN.md:223`). The actual match at `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:11` is the *kept* module `tests/test_ai_kit_spec_gsd_tools.py` cited in the D-18 drift-pin sentence — not "a deleted package". `31-RESEARCH.md:63` even says "(the test file it cites stays)". Following "name the kept caller, curated-config" literally would delete accurate, load-bearing documentation (the resolver-order pin with `edge_floor.py`). And this reword is the only mechanism that removes `gsd_tools.py` from the R1 list, so it is entangled with the HIGH finding: reword it to keep the meaning while avoiding the substring, and fix the pattern anyway for the generated files.
- **LOW — Stale docstring survives in kept code.** `gsd_tools.py:269-271` (`config_set`) justifies omitting `--raw` with "per RUN-11 the undo log reads the prior value from the JSON result's `previousValue`" — the only in-tree reader of that field is `prior_value`, deleted by this plan. The R2 acceptance search (`rg 'prior_value'`) won't catch it ("prior value" has a space). One sentence of docstring repair belongs in Task 3.
- **LOW — `read_first` cites a nonexistent file**: `skills/ai-kit-spec-review/evals/evals.json` (`31-01-PLAN.md:156`) does not exist — `skills/ai-kit-spec-review/evals/` holds four `.md` evals. The real `evals.json` shape lives in `skills/ai-kit-spec-goal-prompt/evals/evals.json` (or the superpowers/commit-fold/jev siblings). Recoverable via `tests/test_skill_evals_shape.py` (also cited), but the pointer is wrong.
- **LOW — Minor anchor drift, all harmless under the Haiku-precise rail**: "all 14 tracked files" (`:186`; `git ls-files skills/ai-kit-spec-execute-gsd` counts 12), "whole, 150 lines" for `tests/test_ai_kit_spec_e2e.py` (`:187`; actual 175), `_PHASE25_SKILLS` at ~1311 (actual `tests/test_arch.py:1309`).

##### Suggestions

- Change the three R1 grep patterns in this plan (and tell plan 05) to `ai_kit_spec_gsd(?![a-z_])`, and re-verify the promised path lists with the fixed pattern before execution starts.
- Reword the Task 3 `gsd_tools.py:11` instruction to: "reword the sentence citing `tests/test_ai_kit_spec_gsd_tools.py` so it names the test without the `ai_kit_spec_gsd` substring, keeping the drift-pin meaning" — and drop the wrong "(name the kept caller, curated-config)" parenthetical.
- Add to Task 3: trim the `config_set` docstring's RUN-11/undo-log parenthetical at `gsd_tools.py:269-271` (its consumer is gone).

##### Risk Assessment

**MEDIUM.** The deletions themselves are safe, complete, and correctly sequenced (each commit buildable, shared behaviors keep tests, no hidden callers), and the rebase/wave-ownership analysis checks out against the actual 30.1 branch. The risk is concentrated in the acceptance gate: three falsifiable criteria in this plan (plus two in plan 05) provably cannot pass as written, which will stall a compliant executor at the Task 2 verification step. One regex fix resolves it.

##### Ponytail findings

- [ponytail] Nothing over-built: the plan is deletion plus one text-pin test module, one 6-eval file (the shape test's minimum is 5 — `tests/test_skill_evals_shape.py:33`), and one output-key assert. All are required by JDG-04/R15 or the house text-pin pattern.
- [ponytail] Good reuse: the moved test class instead of a rewrite; `gsd_tools.config_set` reused in the e2e rewrite instead of keeping a shim.
- [ponytail] The only dead weight found is documentation, not code: the stale `config_set` docstring (LOW above) — the plan's own R2 search is too narrow to catch it.

#### 31-02

**Plan:** `.planning/phases/31-removals-and-small-defects/31-02-PLAN.md`

##### Summary

A clean, well-anchored build plan for the `check-providers` subcommand. Every code anchor I checked is accurate (`cli.py` `CliDeps`:120, `detect-runtimes` parser:148, `_COMMANDS`:990, `main(argv, deps)`:1024; `config_io.py` `cfg_local_path`:263, `cfg_global_path`:289, `cfg_read_bytes`:329, `cfg_parse_toml_bytes`:339; `model_catalog.py` `cache_catalog_path`:54, `split_catalog_meta`:78; `detection.py` `detect_installed_clis`:205, `detect_opencode_models`:297; `tools/config_doctor_readers.py` 26-201), the carried warning/status wording matches the removed skill's actual output verbatim, and the security posture (apiKey markers, wrapped `open`, no `auth.json`, 1 MiB cap, strict UTF-8) is backed by real mechanisms rather than assertions. The only concrete error is a wrong `read_first` pointer.

##### Strengths

- **The port is honest about what changes.** The old scan is a substring match on a *given* provider id (`skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cross_reference.py:57-60` — `provider_id in value`); the new report inverts to "warn on providers absent from the served list" with exact-prefix matching on the model id. The plan forbids porting the old match (`31-02-PLAN.md:125` acceptance `grep -c 'provider_id in'` → 0) and pins the adjacency case (a reviewer with `runtime = "opencode"` never matched on the runtime field).
- **Carried wording verified against source.** `SourceStatus` with `.reason` (`cross_reference.py:118-147`), the fixed source order local→global→catalog (`:150-173`), the `cross-reference: <path> <status>` lines and `warning: "<provider>" is referenced in <path>: <locator> <field>=<value>` with the `(not active: …)` qualifier (`ai_kit_opencode_providers/cli.py:41-61`) all exist exactly as the must_haves describe.
- **Reuses existing helpers instead of re-implementing**: `cfg_read_bytes`/`cfg_parse_toml_bytes` for TOML, `split_catalog_meta` for `_meta` (the house rule), `detect_opencode_models` for the listing. `jsonc_read.py` is a forced copy under the D-13 "skills cannot import tools/" pattern with a drift test — not gratuitous duplication, and the precedent (`tests/test_ai_kit_rules_common.py` copy-vs-source test, `~:1280`) exists.
- **Security tests trace to mechanisms.** The `ConfigError`-raising readers (`config_io.py:329-337,339-352`) justify the fail-soft spec; the wrapped-`open` assertion directly proves `auth.json` is never opened; the drift test's non-vacuity case (trailing-comma strip disabled) is a real discriminator against `tools/config_doctor_readers.py:137`.
- **No wave-1 or 30.1/30.2 conflicts.** None of the plan's files appear in the 30.1 branch diff (52 files, README/test_arch/Makefile/hooks/setup/wizard only) or the 30.2 branch diff (63 files, wizard/status-line only). The port source is deleted only in wave 2 (plan 05), with a `git show 0e6e021:` fallback provided (`31-02-PLAN.md:85`).
- **Interpretation risk is flagged, not hidden**: the catalog-reference rule (model_id's provider part, not the entry's `provider` field) is explicitly marked "planning interpretation … the owner may override".

##### Concerns

- **LOW — `read_first` cites a nonexistent file**: `skills/ai-kit-spec-review/evals/evals.json` (`31-02-PLAN.md:176`) does not exist (that directory ships `.md` evals). The correct shape source is `skills/ai-kit-spec-goal-prompt/evals/evals.json` or the superpowers sibling. Recoverable via the also-cited `tests/test_skill_evals_shape.py`.
- **LOW — Empty successful listing is unspecified.** `detect_opencode_models` returns `[]` on exit 0 with no output (`detection.py:297-306`), which the plan would turn into an empty served set: every configured opencode reviewer warns and the label prints `listed by opencode ()`. Unlikely live (keyless `opencode/` models exist per the SPEC's background), and the R5-empty must-have covers "no reviewer / empty catalog" but not this case. One behavior line ("empty listing ⇒ `not checked` with its reason" or "no warning on an empty set") would close it.
- **LOW — Task 1's `stdout is exactly … five lines` assertion** is brittle if `main()` ever grows a preamble; fine today (`_dispatch`/handlers print nothing extra), just worth writing as "starts with / contains in order" if the executor finds drift.

##### Suggestions

- Fix the `read_first` pointer to `skills/ai-kit-spec-goal-prompt/evals/evals.json` (or `ai-kit-spec-execute-superpowers`).
- Add the empty-listing edge to Task 1 or 2's behavior list; it is two lines of spec and prevents a false-positive class.
- Consider asserting the sources' *order* (local, global, catalog) rather than exact full stdout, to keep the tracer test robust.

##### Risk Assessment

**LOW.** All seams exist as described, the security prohibitions have real tests behind them, no plan in this wave or an overlapping phase touches these files, and the one wrong citation has an in-plan fallback (`test_skill_evals_shape.py` rules). The empty-listing edge is a correctness polish, not a blocker.

##### Ponytail findings

- [ponytail] Nothing speculative: two modules where one is a forced D-13 copy with a drift test; no options, wrappers, or config nobody asked for. Exit-0-always, read-only, one subcommand — matches SPEC R5 exactly.
- [ponytail] Reuse is exemplary: TOML parsing, catalog `_meta` splitting, the opencode listing, and the JSONC scanner all come from existing code (`config_io.py:263-352`, `model_catalog.py:54-95`, `detection.py:297`, `tools/config_doctor_readers.py:26-201`); only the inverted matching logic is new.
- [ponytail] No broken callers: the subcommand is additive (`_COMMANDS` at `cli.py:990` grows one row); spec-config's SKILL.md change is two insertions with a text-pin test.

#### Cross-plan comparison

- **Shared files:** 31-01 ∩ 31-02 = ∅ except the generated `Makefile`/`.pre-commit-config.yaml`, exactly as both plans' context sections claim (verified against 31-03/31-04 file lists too). 31-02's verify runs `tests.test_ai_kit_spec_runtimes_table`, which 31-01 Task 2 edits — read-only dependency, no conflict.
- **The HIGH finding is 31-01's alone but propagates**: 31-02 has no grep-based acceptance of this shape. However, `31-05-PLAN.md:71,192` (wave 2, "R1 completion") inherits the same "prints nothing" claim, so the regex fix must be coordinated across both plans even though only 31-01 is in this batch.
- **Sequencing:** both are wave 1 with `depends_on: []`; the port source for 31-02 is still present in wave 1 (deleted by 05 in wave 2) — correct ordering.

#### Overall risk assessment

**MEDIUM for the batch** — dominated entirely by 31-01's unachievable R1 acceptance grep (`ai_kit_spec_gsd` matching the kept `tests.test_ai_kit_spec_gsd_tools` in the generated listings). The underlying edits in both plans are accurate, complete, and safe; a one-token regex change (plus the two LOW doc fixes in 31-01) would drop both plans to LOW risk before execution.

### Batch B (31-03, 31-04)

### Cross-AI Plan Review — Phase 31, Batch 2 (31-03, 31-04)

All file/line claims below were verified against this worktree (`tmp/wt-31`), the `gsd/phase-30.1-*` branch, and live runs of the edge-floor engine (read-only).

#### 31-03

**Summary.** A mechanically sound, correctly root-caused plan. The alias-path defect is real in the code exactly where the plan says (`tools/setup.py:1076-1079` string compare; `tools/setup.py:1277-1279` the `cur == target` string compare that produced the "28 linked then 25 foreign-skipped" symptom), all five `_is_inside` callers are correctly enumerated (`tools/setup.py:1097,1279,1426,2824,2865`), the headless-prune design correctly reuses `prune_stale`'s already-implemented headless branch (`tools/setup.py:1395-1399` prints exactly the warn line the plan quotes), and the 30.1 rebase notes match the actual branch (backups_root at `tools/setup.py:121`, `functools` import at `:27`, `_make_apply_housekeeping` still calls the prune helpers at `:4010/:4098` on the branch). The gaps are documentation-staleness and two small mechanical placement issues, not design flaws.

**Strengths.**
- Root cause and fix point verified: `_is_inside` is a string `startswith` (`tools/setup.py:1079`) and `installed_links` feeds it the raw `os.readlink` value (`tools/setup.py:1096-1097`); one resolved-compare helper used by all five callers is the minimal correct fix, not a new abstraction.
- The prune insertion correctly identifies the code that already exists: `prune_stale`'s non-interactive branch (`tools/setup.py:1395-1399`) already prints `warn: removing dead ai-kit link {item} (entry removed upstream)` — the plan wires documented behavior rather than writing a second printer, and `is_interactive(None) is False` (`tools/setup.py:1205-1207`) makes the `tty=None` call work as planned.
- The pi-root filter mirrors the wizard's real code (`tools/setup.py:3972-3975`, `item.startswith("skills/")`), and "only when `os.path.isdir(paths.pi_dir)`" matches `sync_pi_links`' never-create rule (`tools/setup.py:1712-1714`).
- The fixture rule (real kit copy, `ignore_patterns` naming the three removed skills) is a good wave-order-independent design — the dead links are dangling in the copy whether or not the removal waves landed.
- Threat register matches the real mutation surfaces: `apply_stale_prune` unlinks only `islink` paths already proven dangling-and-inside by `stale_link_candidates` (`tools/setup.py:1349-1365`); `unlink_one` already guards with `os.path.lexists` (`tools/setup.py:1302`).
- `install --headless` and `reconfigure --headless` both dispatch to `cmd_install_headless` (`tools/setup.py:4909-4915`), so one insertion covers both, as claimed.
- `tests/test_install.sh`'s existing style (env -i, marker setup.py echoing `AI_KIT_DIR`, `tests/test_install.sh:43-55`) supports the planned alias-export case with no new harness.

**Concerns.**
- **MEDIUM — stale contract docs left behind.** The new unconditional prune (inserted after `_headless_paths_and_entries`, before the `requested` check) falsifies `cmd_install_headless`'s docstring "Bare (all flags falsy) is a pure no-op — 'nothing touched unless asked'" (`tools/setup.py:4484-4486`) and the comment "Only a run that named --skills touches the pi root; bare --headless … leave every pi link exactly as it was" (`tools/setup.py:4546-4548`). The plan rewrites only the comment at `:4527-4529`. AGENTS.md counts stale docs as a defect; the docstring's locals-budget note (`:4517-4520`, "8 locals = 14 of 15") also goes stale (one new local for the pi stale list).
- **LOW — mechanical placement bug: `counts` doesn't exist yet at the insertion point.** The plan inserts the prune "before `migrate_statusline`", but `counts = new_counts()` is created at `tools/setup.py:4540`, *after* `migrate_statusline` (`:4539`). The prune needs `counts`; the executor must hoist its creation. Unmentioned in the plan; combined with the 15-local pylint budget this can fail lint and needs the plan's disable comment updated.
- **LOW — self-tripping acceptance criterion (Task 1).** "`rg -n '/var/home|/home/[a-z]|/Users/' tests/test_setup.py` prints no line added by this plan" cannot hold: Task 2 rewrites `tests/test_setup.py:883-911`, whose fixture style is `{"HOME": "/home/u"}` (`tests/test_setup.py:881-911`), and `/home/[a-z]` matches `/home/u`. Either exempt synthetic `/home/u` or rewrite those fixtures off scratch-tmp paths.
- **LOW — wrong function named for the `present` computation.** "read them by name in `_make_apply_housekeeping`" — `_make_apply_housekeeping` *receives* `stale`/`pi_stale` as parameters (`tools/setup.py:3843-3845`); the `present` map and the pi filter the plan wants to mirror live in `launch_wizard` (`tools/setup.py:3966-3979`).
- **LOW — ambiguous ordering claim vs install.sh reality.** The must_have "AI_KIT_DIR wins over the running checkout … (install.sh only)" contradicts what the plan actually implements: in LOCAL mode `detect_mode` overrides `AI_KIT_DIR` with the script's own checkout (`tools/install.sh:76-82`), and Task 2 keeps that, only resolving `INSTALL_DIR` before the export at `tools/install.sh:290`. The resulting behavior is right; the must_have wording could mislead an executor into "fixing" `detect_mode`.
- **LOW — weak grep gate.** "`grep -c 'pwd -P' tools/install.sh` prints at least 2 (baseline 2)" passes on the unmodified file; the intended count (3) lives only in a parenthetical.
- **[ponytail] LOW — blast radius wider than tested.** Changing `resolve_paths`' default (`tools/setup.py:114-117`) moves `install_dir` for *every* subcommand — `check`, `doctor`, `uninstall` run from a checkout now target the checkout, not `~/.local/share/ai-kit`. That is SPEC R8's intent, but only `install` is tested; one line in the SUMMARY acknowledging the wider effect (or a `check`/`uninstall` default assertion) would be cheap.

**Suggestions.**
- Add to Task 3's action: rewrite the `:4484-4486` "pure no-op" sentence, the `:4546-4548` pi comment, and the `:4517-4520` budget note in the same commit; hoist `counts = new_counts()` above the prune call explicitly.
- Fix the Task 1 acceptance regex (exclude `/home/u`) or migrate the rewritten `:883-911` fixtures to scratch-tmp paths.
- Point Task 3's read at `launch_wizard:3966-3979` for `present`/`pi_present`.

**Risk Assessment: MEDIUM.** The design is verified-correct against the code and the defect is real; the residual risk is executor friction (hoisting `counts`, doc staleness, a self-failing grep gate) rather than wrong behavior — and the plan's own scratch-HOME tests would catch any misfire.

---

#### 31-04

**Summary.** The best-verified plan of the batch: every factual claim I checked holds, including the two decisive ones I re-ran live — the edge-floor engine passes all 7 current SPECs under `.planning/phases/` today except 30.1-SPEC, which fails with exactly `missing [['encoding','R3']]`, and 25.1-SPEC fails with exactly `missing encoding R9` (floor 48, table 47) — so the guard can actually reach green with only the two added rows. The D-08 deviation (guard in `tools/check_dogfood.py` instead of an e2e test) is necessary and correct: `check_no_planning_reader` (`tests/test_arch.py:1154`) with `PLANNING_READER_EXCEPTIONS = {}` (`tests/test_arch.py:986`) forbids any test reading `.planning/`. The remaining issues are one real mechanical gap (the engine file is not self-contained) and one operational hazard the plan doesn't name.

**Strengths.**
- **Live-verified core claim**: `edge_floor.py check` on the worktree's 7 current SPECs → 28 ok, 29 ok, 29.1 ok, 30 ok, 30.2 ok, 31 ok, 30.1 missing `encoding R3`. The guard lands on a tree that already passes except for the row this plan adds. The 25.1 delta is exactly `encoding R9` (`.planning/milestones/v1.3-phases/25.1-.../25.1-SPEC.md` line 342 holds `| empty | R9 |`, matching the plan's insertion point).
- The deviation from D-08 is grounded: the arch rule has no exceptions, `make check-dogfood` is already "the only reader of `.planning/`" (AGENTS.md), and it already runs read-only node against the checkout-local gsd-core (`check_dogfood.py:258-261`) — `check_edge_floors` is the same pattern with a `run` seam and a `which` seam, wired into `main` where the notes/problems merge already happens (`check_dogfood.py:468-475`).
- `edge_floor.py`'s CLI contract matches the plan's use: `check <spec> --engine PATH` (`edge_floor.py:190-192`), exit 1 with `missing` JSON on stdout / exit 2 fail closed (`:207-216`), `find_engine` exists (`:118`).
- Task 2 verified end-to-end: `_gsd_json`'s bare `json.loads` (`goal_prompt.py:254-257`), the exact existing error text at `:276`, `_gsd_json` really is the only gsd-tools parser (the other `json.loads` at `:425` reads a config file), and `resolveAtFileOutput` is a `startsWith('@file:')` + `readFileSync` mirror (`io.cjs:197-201`).
- Task 3's comparison sets all verified: `RUNNER_IDS = ("pi","cursor","opencode","codex")` (`cross_ai.py:49`) = runner-flagged runtimes (`detection.py:75` `runner=True` default; grok `runner=False` at `:123`) minus claude (`review_only=True`, `:114`) and copilot; `HOSTS` (`host.py:19`) = all ids minus copilot/grok; `HOST_BINARY` cursor→`agent` (`gp_host.py:21-27`) within `("cursor-agent","agent")` (`detection.py:95`); the template's `const RUNTIMES` (`cross-ai.mjs:1333`) holds exactly the six runner keys, so the new equality check holds today; and `', '.join(RUNNER_IDS)` reproduces the current hardcoded text byte-for-byte (`plan_edit.py:373-375`), so the existing regex in `tests/test_curated_config_plan_edit.py` keeps matching as the plan claims.
- Rebase note verified against the branch: the 30.1 branch carries an amended 30.1-SPEC.md that also lacks any `encoding | R3` row (grep count 0 on `git show`), and its amendment hunk sits at `:169+`, far from the R3 rows at `:269` — the "keep exactly one encoding R3 row" instruction is well-founded.
- Same-wave file check confirmed: 31-01/31-02/31-04 share only the generated `Makefile`/`.pre-commit-config.yaml`; every other file in 31-04's list is untouched by wave 1, and the superset-check removal is correctly deferred to 31-05 (wave 2), which lists `tests/test_ai_kit_spec_runtimes_table.py`.

**Concerns.**
- **MEDIUM — the engine is not self-contained; the plan's test mechanics break on it.** `edge-probe.cjs` requires siblings: `require("./probe-core.cjs")` and `require("./cli-exit.cjs")` (`.claude/gsd-core/bin/lib/edge-probe.cjs:29,31`). `_run_floor` hardcodes `--engine str(root / EDGE_ENGINE_REL)`, so the real-engine non-vacuity test must place a *working* engine at that path inside the temp root — copying the single file (the naive reading of "finds the engine through `find_engine`") yields exit 2. The plan never says how (symlink the engine file — Node resolves a symlinked module's relative requires against its real path — or copy `bin/lib/`). This will cost the executor a debugging round.
- **MEDIUM — unnamed workflow hazard: an in-progress SPEC blocks every push.** A phase SPEC with a `## Requirements` section but no `## Edge Coverage` table yields `table_rows=[]` → every floor row missing → rc 1 → `make validate`/pre-push fails (`edge_floor.py:158-183`). 31-SPEC passes today, but the *next* phase's SPEC exists in a drafts window before its table lands, and during that window all pushes from that checkout — including unrelated work — are blocked. The SPEC's R10 wording ("a test fails when a current-milestone SPEC drifts") arguably accepts this, but the plan should state it and ideally soften the no-section case to a named note (drift still fails once the section exists but is incomplete).
- **LOW — Task 3 helper spec is garbled.** "`runtime_list_differences` returns `[]` when `set(copy) - set(allowed_extra)` and `set(expected) - set(allowed_missing)` match" — two set differences never "match"; the actual design is the `DELIBERATE` reasons table, which is clear. The behavior line should say: empty result iff every difference is keyed in `DELIBERATE`.
- **LOW — patched-`RUNTIMES` test needs the right binding.** `routing.py` binds `RUNTIMES` via `from ai_kit_spec.detection import …` (`routing.py:14`), so the "no runtime has selectors" test must patch `ai_kit_spec.routing.RUNTIMES`, not `detection.RUNTIMES`. Unnamed in the plan.
- **[ponytail] LOW — the brace-matched template parser re-invents an existing tested one.** `tests/test_ai_kit_spec_runtimes_table.py:484-485` already extracts the template's runtime keys with `source.split("const RUNTIMES = {", 1)[1].split("};", 1)[0]` + `re.findall(r"^  ([\w-]+): \{", …, re.MULTILINE)`. The plan's depth-counted brace parse is more robust but is new code next to a proven one-liner that already exists in the file this test will sit beside; reuse it (or say why the split is insufficient — I found no `};` inside the block that would break it).
- **LOW — Coverage-line edits underspecified.** The two parentheticals differ: 30.1 reads "46 engine rows …, 0 added" (`.planning/phases/30.1-.../30.1-SPEC.md:254`) → must become "47 engine rows …, 1 added"; 25.1 reads "47/47 … (floor recomputed 2026-10-24)" (`.planning/milestones/.../25.1-SPEC.md:296`) → "48/48" with the parenthetical kept. "raise by 1 where stated" is executable but the exact final lines would remove all judgment.

**Suggestions.**
- Add one sentence to Task 1's action: the real-engine test symlinks `edge-probe.cjs` (or copies `bin/lib/`) into the temp root so `_run_floor`'s hardcoded engine path actually runs; the skip reason stays for when the real engine is absent.
- Decide the no-`## Edge Coverage`-section case explicitly (named note vs. drift) and record it in the SUMMARY; it determines whether the guard can block unrelated pushes mid-phase.
- Name the patch target `ai_kit_spec.routing.RUNTIMES` in Task 2.

**Risk Assessment: MEDIUM.** The plan's claims are unusually well-grounded (I re-ran the engine and confirmed every list/set equality), and the D-08 deviation is the right call. The risk is concentrated in one unmechanical test detail (the non-self-contained engine) and one operational hazard (in-progress SPECs blocking `make validate`) — both cheap to fix now, annoying to discover during execution.

---

#### Cross-plan comparison

- **Same-wave file overlap: none beyond the generated listings.** 31-03's four files are exclusive to it in wave 1; 31-04's files overlap 31-01/31-02 only on `Makefile`/`.pre-commit-config.yaml`, which all regenerate via `python3 tools/gen_test_groups.py` — exactly the sanctioned exception. Verified against both other plans' `files_modified`.
- **Handoffs are consistent.** 31-04 correctly leaves `tests/test_ai_kit_spec_runtimes_table.py`'s superset-check removal to 31-05 (which lists it), and 31-05's `depends_on` includes 03 and 04 for the setup.py comment and the drift test respectively. No circular or missing dependency in this batch (both plans correctly declare `depends_on: []`).
- **Rebase notes: 31-03's verified against the real 30.1 branch** (resolve_paths hunk adjacency, `_make_apply_housekeeping` retains the prune calls, 30.2-05's setup.py areas — segment inventory/`render_preview` — genuinely disjoint from 31-03's regions). **31-04's 30.1 note verified**: the branch's SPEC lacks the `encoding R3` row too, and its amendment hunk sits ~100 lines away from the insertion point, so "keep exactly one row" is the only rebase judgment needed.
- **Neither plan removes anything the SPEC doesn't name.** Both are defect-fix plans; the only deletions are the dead-link prune (R6) and code the SPEC explicitly retires.

**Overall: both plans are approvable with the fixes above — MEDIUM risk, dominated by the two MEDIUM mechanical/operational items (31-03's stale `cmd_install_headless` contract docs; 31-04's non-self-contained engine fixture and the in-progress-SPEC push-block hazard).**

### Batch C (31-05, 31-06)

### Cross-AI Plan Review — Phase 31, Batch 2 (plans 31-05, 31-06)

All findings below were verified against the checkout at `tmp/wt-31` (branch `gsd/phase-31-removals-and-small-defects`, HEAD `e8e3761`) and, where rebase behavior matters, against branch `gsd/phase-30.1-setup-wizard-component-cards-and-host-status-line-panes-inse`. Read-only; no files were changed.

#### 31-05

##### Summary

A well-anchored removal plan whose every file/line claim I checked against the tree is accurate (providers skill = exactly the 8 listed files; mermaid-audit = exactly 24 tracked files; all origin comments, list entries and docstring locations match; the pi-variable messages live exactly where the plan says). Its one real defect is a self-defeating acceptance gate: the "R1 complete" grep can never print nothing because the kept module name `test_ai_kit_spec_gsd_tools` contains `ai_kit_spec_gsd` as a substring, so an autonomous executor will hit an unpassable criterion and have to improvise.

##### Strengths

- **Removal inventories are complete.** A full tracked-file grep for `ai-kit-opencode-providers|ai_kit_opencode_providers` and for `mermaid-audit|mermaid_audit|test_mermaid_style` (hidden files included) returns exactly the files Task 1 and Task 2 list — nothing extra survives: skill folders, `pyproject.toml:113,133,137`, `tests/test_gate_scope.py:39` (with `skills/ai-kit-usage-metrics/.*|` correctly kept on the same line), `tests/test_ai_kit_spec_runtimes_table.py:813`, `README.md:31,40`, origin comments at `tools/config_doctor_readers.py:89,109,123,140` / `tools/config_doctor_appliers.py:30,148` / `tools/setup.py:1881` / usage-metrics `paths.py:6` / `raw_store.py:34`, the generated lists (`Makefile:12`, `.pre-commit-config.yaml:15,71`, regenerated via the existing `tools/gen_test_groups.py`), and `render_mermaid.py:5`. `.claude-plugin/plugin.json:3` contains exactly `, a Mermaid diagram auditor` and names neither of the other two skills.
- **The R1-completion handoff from plan 01 is exact.** The seven docstring-only adapter mentions the plan rewords are precisely the ones that remain after plan 01's scope (verified against the tree and 31-01-PLAN.md:59,207,241): `cross_ai_build.py:4-5`, `model_detect.py:8`, `tests/test_ai_kit_gsd_curated_config.py:474`, `ai-kit-session-wake.py:4`, superpowers `cli.py:2,11` + `dispatch_injection.py:166,171`, `dispatch_guidance.py:2`.
- **The `test_run_unittest_parallel.py` sample swap is sound.** The three `tests.test_mermaid_style` uses are at :47, :52, :182; the replacement `tests.test_ai_kit_spec_execute_router` is created by plan 01 (31-01-PLAN.md:155,167) and reads its fixture via `Path(__file__).resolve()`, so the `cwd=tmp` case at :182 still works.
- **Pi-wording task is correctly scoped.** The unset messages live at `recommend.py:323-326` and `plan_io.py:540-541` (not in `inventory.py`, which only reads the env var at :472 and whose comment at :471 already says the right thing); the existing pins (`tests/test_curated_config_recommend.py:940`, `tests/test_curated_config_plan_edit.py:256`) still match the proposed new text, so no test churn; the "inside the pi session" baseline really is 2 files. `evals/` has the four `01-04*.md` scenarios and no `evals.json` yet.
- **R13 follow-through loses no coverage.** The two deleted lines exist at `tests/test_ai_kit_spec_runtimes_table.py:471-472` and `test_runner_template_keys_use_table_ids` at :477; plan 04's `tests/test_runtime_list_drift.py` (31-04-PLAN.md:46) compares the same lists for equality with documented deliberate differences — strictly stronger. The "drop `re` if unused" hedge is right: `re` is used at :521+, so it stays.
- Verify commands fail fast if wave 1 slipped (they run the wave-1-produced `tests.test_ai_kit_spec_check_providers`, `tests.test_ai_kit_spec_jsonc_read`, `tests.test_runtime_list_drift`).
- [ponytail] Nothing new is built: the stale-provider warning already lives in plan 02's port, the evals file is required by JDG-04, and the doc-contract class is the house text-pin pattern.

##### Concerns

- **HIGH — the R1-completion acceptance grep can never pass.** `31-05-PLAN.md:71` and `31-05-PLAN.md:192` require `'ai-kit-spec-execute-gsd|ai_kit_spec_gsd|ai-kit-spec-gsd\.py'` to print nothing, but the kept module `tests/test_ai_kit_spec_gsd_tools` (kept by the SPEC's own amendment, and by `gsd_tools.py:11`'s docstring naming it) contains `ai_kit_spec_gsd` as a substring. Permanent hits: `Makefile:12` and `.pre-commit-config.yaml:15,71` (`tests.test_ai_kit_spec_gsd_tools`) and `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:11`. The SPEC's R1 adjacency row ("a name that contains a removed one as a prefix is kept; searches match the full removed names only") requires a boundary the regex lacks. An `autonomous: true` executor facing an impossible gate will either loop or "fix" it the wrong way (e.g. renaming the kept test module, violating the spec amendment). Fix: `ai_kit_spec_gsd\b` (underscore after `gsd` blocks the `_tools` match, still matches `ai_kit_spec_gsd.cli`).
- **LOW — rebase notes cover 30.1 only, not 30.2.** 30.2-05 also edits `tools/setup.py` and `README.md` (30.2-05-PLAN.md:8,15) before phase 31 lands, yet the section header promises "30.1 / 30.2 overlap". Harmless in practice because the acceptance criteria are content greps, not line numbers, and the plan already says "re-run the R3 search after rebase" for setup.py — but the note is incomplete as written.
- **LOW — pinned base commit in acceptance.** Task 2's `git diff 0e6e021 --stat -- skills/markdown-to-pdf` holds only while no wave-1 plan touches markdown-to-pdf (true today for all four) and only until the phase's base is rebased.

##### Suggestions

- Change the two grep instances (31-05-PLAN.md:71,192) to `'ai-kit-spec-execute-gsd|ai_kit_spec_gsd\b|ai-kit-spec-gsd\.py'` — one character-class fix, gate becomes passable. Apply the same fix to 31-01-PLAN.md:59 and :207, whose "lists only the seven/10 paths" claims have the identical substring false-positive (Makefile and .pre-commit-config.yaml would also be listed).
- Add one 30.2 line to the rebase notes: "30.2-05 also edits `tools/setup.py` and `README.md`; both edits are far from the rows/comments this plan touches; re-run the R3/R4 greps after rebase."

##### Risk Assessment

**MEDIUM.** The changes themselves are correct, complete, and precisely anchored — every removal claim I traced holds. The single HIGH finding is an impossible acceptance gate, not a code defect, but in an autonomous plan that is enough to stall execution or trigger a wrong workaround; it must be fixed before execution.

#### 31-06

##### Summary

The strongest of the two plans. The whole-tree rtk inventory maps one-to-one onto the plan's edits plus its exemptions (nothing unaccounted survives), the `rtk-hint` rebase rename is a correct and load-bearing catch (`\brtk\b` matches `rtk-hint` because the hyphen is a word boundary), the doctor row-count arithmetic checks out against the live catalog, and the new R14 link test will pass on the tree as edited. The only real deviation is one ban-test exemption (`tests/fixtures/archived/`) that the SPEC's R7 list does not name and that currently guards nothing.

##### Strengths

- **Complete rtk coverage.** Every non-exempt tracked `rtk` hit — `AGENTS.md:128`, `README.md:52,654,661`, `tool_presence.py:33`, rules-agents `SKILL.md:37,66,67`, `rules.py:110-115`, `tests/test_ai_kit_project_rules_agents.py:130,176,204,206,552`, `tests/test_ai_kit_rules_common.py:144`, `tests/test_config_doctor.py` (~776-940), `tests/test_config_doctor_pty.py` (~144-152), `tests/test_tool_substitution_hook.py:1308`, `tools/config_doctor_checks.py:565,567,1022,1025,1027`, `tools/config_doctor_readers.py:212,218,222` — is edited by Task 1, 2 or 3, so the tree passes the new ban test exactly as planned.
- **The `rtk-hint` rename is necessary and exactly scoped.** 30.1 adds `("hooks", "rtk-hint", False)` at `tests/wizard_fixtures.py:102` and asserts it at `tests/test_wizard_app_1.py:181,188`; since `-` is a word boundary, the ban pattern would hit it. The rebase note (31-06-PLAN.md:108,113) owns the rename and its instruction (`rg -n 'rtk-hint' tests`) is drift-robust. Verified: those are the only `rtk-hint` occurrences on the 30.1 branch.
- **Baselines verified.** The `20-rule` search returns exactly the 7 claimed hits (README.md:41; rules-agents SKILL.md:3,10,156; `rule_checker.py:9`; `rules.py:1`; rules-makefile SKILL.md:17). R05 is referenced exactly at `rules.py:107`, `SKILL.md:65`, `tests/test_ai_kit_project_rules_agents.py:208` — all covered. The doctor catalog has 26 rows today (`id="` at checks.py:587-1040), so `== 25` after removal and 26 after 30.1's +1 is right (31-06-PLAN.md:111).
- **`usage_metrics_invites_rtk` is False on today's SKILL.md.** I checked every rtk occurrence in `skills/ai-kit-usage-metrics/SKILL.md` (lines 3,14,23-24,90,109-113,124,300) against the plan's pattern: none is `install rtk`, `rtk init`, or a backticked `rtk <subcommand>` — so D-01's "usage-metrics SKILL.md unchanged, not judged" holds.
- **R14 passes on the tree.** AGENTS.md has exactly two relative links: `.claude/cli-environment.md` (removed by Task 1 step 4; nothing under `.claude/` is tracked) and `docs/run-book/graphify.md` (tracked, not ignored). [ponytail] The test reuses `_LINK_RE`/`_parse_link_target`/`_without_fenced_code` (`ai_kit_project_rules_agents/cli.py:22,30,51`) and the `_git` temp-repo helper (`tests/test_ai_kit_project_rules_agents.py:1010`) instead of writing new ones.
- [ponytail] `TestRtkHistoryStillRead` is conditional, and correctly so: scratch rtk capture/refine tests already exist in `tests/test_ai_kit_usage_metrics.py` (e.g. the `mkdtemp(prefix="ai-kit-um-rtk-")` class and the `runtime == "rtk"` refine cases), so no duplicate helper gets written. The ban replacement subsumes the hooks-only ban (`tools/hooks/` stays covered).
- Ordering is right: the ban test lands in Task 3, after Tasks 1-2 removed every mention it would flag.

##### Concerns

- **LOW — an exemption beyond SPEC R7's list.** 31-06-PLAN.md:188 adds `tests/fixtures/archived/` to `EXEMPTIONS`; SPEC R7 (as amended in RMV-04) names only `.planning/`, `docs/prds/`, `docs/superpowers/`, the test itself, and usage-metrics' reader + test. Verified: `tests/fixtures/archived/` contains **zero** rtk hits today, so the exemption currently guards nothing — it only widens the ban's blind spot for future archived fixtures. Either drop it or amend SPEC R7's exemption list to match (the plan cites "planning ruling 2"; per the AGENTS.md workflow rule, a spec-level exemption list should be changed in the spec, not only in the plan).
- **LOW — rebase notes are 30.1-only in substance.** 30.2-05 also edits `tests/wizard_fixtures.py`, `README.md` and `tools/setup.py` (30.2-05-PLAN.md:8,10,15) before phase 31. The rename mechanism is grep-based and the row-count assertion is "the live number", so the plan tolerates the drift — but the section titled "30.1 / 30.2 overlap" never mentions 30.2.
- **LOW — stale count-test name left behind.** Task 2 renames `test_five_sections_twenty_six_rows` but leaves `test_catalog_contains_at_least_twenty_four_rows` (`tests/test_config_doctor.py:641`) asserting `>= 24` against a 25/26-row catalog. Functionally fine; cosmetically stale. [ponytail] acceptable to leave — renaming it is churn — but then the SUMMARY should not claim the count tests are all current.

##### Suggestions

- Drop the `tests/fixtures/archived/` exemption (no hits today), or amend SPEC R7's named-exemptions sentence to include it with the "byte copies of archived planning data" reason — pick one so spec and test agree.
- Add one 30.2 sentence to the rebase notes naming `tests/wizard_fixtures.py`, `README.md`, `tools/setup.py` as also-touched by 30.2-05, so the executor does not assume 30.1 is the only source of drift.

##### Risk Assessment

**LOW.** The mechanism was verified end to end against both the current tree and the 30.1 branch: the ban test passes exactly on the post-plan tree and the rename it depends on is correctly anticipated. The findings are a spec-drift nit and rebase-note completeness, both cheap to fix and neither execution-blocking.

#### Cross-plan comparison

- **Wave discipline holds.** 31-05 is the only wave-2 plan and 31-06 the only wave-3 plan (plan map at 31-01-PLAN.md:114), so no same-wave file sharing exists. The files the two plans share across waves — `README.md` (05: rows 31/40; 06: rows 41/52/654/661), `tools/config_doctor_readers.py` (05: comments 89-140; 06: constants 16-19 + probe 211-248), and the regenerated `Makefile`/`.pre-commit-config.yaml` — touch disjoint regions in a strict order (06 depends_on 05).
- **Nothing is removed that the SPEC does not name.** 31-05's deletion of `test_runner_template_keys_use_table_ids` and the two `RUNNER_IDS` superset lines is exactly SPEC R13's "compared for equality, not superset"; 31-06's replacement of the hooks-only ban is SPEC R7's own wording.
- **The one defect that propagates across plans** is the missing word boundary in the adapter grep: created in 31-01 (:59, :207), repeated in 31-05 (:71, :192). Fix it once in all four places.
- **30.1 rebase notes are correct where they matter** (rtk-hint files, doctor row arithmetic, README doctor sentence, `tests/test_run_unittest_parallel.py` hunk separation); **30.2 is under-covered in both plans** (shared files: `tools/setup.py`, `README.md`, `tests/wizard_fixtures.py`, and `tests/test_arch.py` via 30.2-04, which 31-05 only runs, never edits). All affected criteria are content greps or live-number assertions, so the risk stays LOW.

#### Overall risk assessment

**MEDIUM for the batch** — driven entirely by 31-05's impossible R1-completion acceptance gate (one-character fix, but it will definitely fire in an autonomous run); 31-06 alone is LOW. Both plans' substantive changes verified correct against source: inventories complete, no orphaned references outside history folders, no same-wave file collisions, and no unrequested removals.

**Not checked:** the internal shape rules of `tests/test_skill_evals_shape.py` (the evals.json "2-3 assertions of 20+ characters" claim), the `scope.py` Rails script contents in 31-01-PLAN.md (referenced, not read in full), and any runtime behavior (herdr/pi live check, skill-judge outcomes) — those are execution-time steps, not plan-text claims.

## OpenCode Review (referee-three)

### Batch A (31-01, 31-02)

### Phase 31 plan review, batch: 31-01 and 31-02

#### 31-01

##### Summary
The plan is broad and mostly accurate. The removal inventory matches the tree, and the guidance-code removal is complete across `runner_dispatch.py`, `cross_ai_script.py`, `cli.py`, the docs and the tests. Each D-13 case has a stated fate. There is one blocking defect: the R1 acceptance search can never reach "prints nothing" as the plan claims, so Task 2's acceptance check and the plan-05 handoff both fail as written. There are also two smaller documentation gaps.

##### Strengths
- The line anchors check out:
  - `tests/test_arch.py:1309-1315` (`_PHASE25_SKILLS` and `_PHASE25_LADDER_PKGS`), `:1607-1627`, `:1680-1688` and `:3083`.
  - `tests/test_ai_kit_spec_runtimes_table.py:811, 819, 831, 837`.
  - `tests/test_quota_policy_text.py:17-18, 106, 126`.
  - `tests/test_gate_scope.py:38`, `pyproject.toml:124` and `README.md:38`.
- The plan catches the `REWRITTEN[:4]` slice trap. The slice exists at `tests/test_ai_kit_spec_runtimes_table.py:819`, and once the gsd row is gone it would pull curated-config into `PAIR_RULE_SKILLS`. Replacing it with an explicit list is correct.
- The new non-vacuity string, `from ai_kit_spec_superpowers.cli import write_resumable_state`, is still flagged. `ai_kit_spec_superpowers` stays in `_PHASE25_LADDER_PKGS` (`tests/test_arch.py:1315`, `:1340`).
- The R2 symbol list is complete. A repo search finds `GUIDANCE_PATH`, `GUIDANCE_HEADER_RE`, `plan_guidance` and `_guidance_step` only in `cross_ai_script.py:21-23, 316-368`, `runner_dispatch.py:33, 185-196` and `tests/test_curated_config_script.py:72`. The only other caller of `project_runner_command` is `cross_ai_build.py:114`, which passes no guidance argument.
- Dropping the `guidance` key is safe. The only readers are `tests/test_curated_config_script.py:462, 638, 656, 726` and the two error dicts (`cross_ai_script.py:332`, `cli.py:233`). The v1 path at `cli.py:316` reads only `ready`.
- Hidden files are covered: `.claude-plugin/plugin.json` has no reference to the removed skills, and `.pre-commit-config.yaml` is regenerated.

##### Concerns
- **HIGH: the R1 acceptance search cannot pass.** The pattern `ai_kit_spec_gsd` is a substring of the kept module name `test_ai_kit_spec_gsd_tools`, so three kept files always match:
  - `Makefile:12` and `.pre-commit-config.yaml:15, 71` (the generated lists name `tests.test_ai_kit_spec_gsd_tools`).
  - `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:11` (its docstring cites `tests/test_ai_kit_spec_gsd_tools.py`; RESEARCH line 63 says that file stays).

  The consequences:
  - Task 2's "lists only these 10 paths" check fails, because `Makefile` and `.pre-commit-config.yaml` are not in the list (`31-01-PLAN.md`, Task 2 acceptance).
  - Task 3's "now lists only the seven plan-05 docstring files" fails too.
  - The must_haves truth that "the search prints nothing after plan 05" can never hold, because plan 05 has no reason to touch these files.
  - SPEC R1's acceptance search has the same defect.
- **MEDIUM: curated-config `SKILL.md:128` becomes false, and the planned rewrite does not fix it.** The sentence says copilot is not a curated runner and that "`ai-kit-spec-execute-gsd`'s hook is the path that can name it". Task 3 step 5 rewrites "~128 and ~231" as hook mentions, which does not fit a sentence about copilot. After the removal, nothing in ai-kit can name copilot as a GSD runner, and the doc should say exactly that.
- **MEDIUM: `SKILL.md:231-236` mixes the kept v1 `apply-execution` path with the removed hook.** Only the clause at 234-236 goes. The plan should state that the v1 `--codex-sandbox workspace-write` clause stays, so an executor does not drop v1 wording along with the adapter.
- **LOW [ponytail]: moving `TestGsdPurposeFilterInertness` largely duplicates existing tests.** `tests/test_ai_kit_spec.py:5604-5629` (`TestFilterByPurpose`) already covers both behaviours: a review-tagged entry is dropped and an entry with no purpose key passes through. At the `resolve_execute_candidates` level, `TestExecuteLadderScreen` (`:5518`) is the natural home. Putting the class in `test_ai_kit_spec_superpowers.py` means adding an `execute_selection` import there (it imports only `detection, routing, runner_dispatch` at `:28`). A one-case addition beside `:5518`, or plain deletion, would be smaller.
- **LOW [ponytail]: the `TestRealGsdConfigSet` rewrite becomes nearly redundant.** `TestRealGsdTools.test_previous_value_contract_on_real_gsd_core` (`tests/test_ai_kit_spec_e2e.py:66-100`) already runs `config_set`/`config_get` on the real gsd-core. What the rewrite adds is a boolean value and an on-disk read, which is fine to keep. Whichever way it goes, `_CASES` at `:154-155` must keep naming real classes.
- **LOW: the rebase notes leave out 30.2's README edit.** 30.2's plans list `README.md` in `files_modified`, but the notes mention only the 30.1 README hunks. The 30.1 hunks (`README.md` 73+, 114-190, 664+) and its `test_arch.py:1843` hunk do sit away from rows 38 and 49 and the 1309/1607/1680/3083 regions, so that part of the notes is correct.

##### Suggestions
- Pick one fix for the HIGH item:
  1. Make the search word-bounded: `git grep -n -E 'ai-kit-spec-execute-gsd|\bai_kit_spec_gsd\b|ai-kit-spec-gsd\.py'`. Since `\b` treats `_` as a word character, this no longer matches `ai_kit_spec_gsd_tools`.
  2. Rename the kept test to `tests/test_gsd_tools.py`.

  Then amend the SPEC R1 acceptance to match.
- Give an exact replacement for `SKILL.md:128`: "Runner ids are pi, cursor, opencode and codex; copilot is not a curated runner (`plan-set` refuses it)."
- For `SKILL.md:231-236`, quote the target text in full: keep v1 and its sandbox clause, drop the hook and the guidance file.

##### Risk Assessment
**MEDIUM.** The code removal itself is low-risk and well mapped. The broken acceptance search will block the executor or produce a false "done", and the curated-config text fixes are underspecified.

#### 31-02

##### Summary
The plan is a clean port into `ai_kit_spec` and reuses the existing seams: `cfg_local_path`/`cfg_global_path` (`config_io.py:263, 289`), `cache_catalog_path` (`model_catalog.py:54`), `split_catalog_meta` (`:78`), `detect_opencode_models` (`detection.py:297`), and `CliDeps` with `env_fn`/`run_fn`/`which_fn` (`cli.py:120-128`). It correctly drops the old substring matcher (`cross_reference.py:59, 82, 91`). Its weakness is accuracy: in its current form the report will give false "stale" warnings in two common cases.

##### Strengths
- The handler-coverage test `tests/test_ai_kit_spec.py:4071-4075` (`set(_COMMANDS) == subparsers.choices`) is in Task 1's verify, so a missed `_COMMANDS` row is caught.
- Matching on the provider part of the model id (and never on the `runtime` field) fixes a real false positive in the old scan: `provider_id in value` against `runtime` meant `"opencode"` matched every opencode reviewer.
- The secrets test checks both an `apiKey` marker and a wrapped `open` that must never see `auth.json`. That is good evidence for the must-not.
- The JSONC reader is copied with a drift test and a non-vacuity case, which is the house pattern (29 D-13, `tests/test_ai_kit_rules_common.py:1619`).
- No file overlaps with 31-01 apart from the generated listings. Wave 1 has no conflict.

##### Concerns
- **HIGH: the config-file fallback reports built-in providers as stale.** When the listing fails, served providers come only from the `provider`/`providers` config keys. Built-in providers never appear there: the keyless `opencode/` models, `anthropic/` served from an environment key, and any provider from a login. So a reviewer using `opencode/free-y` or `anthropic/...` gets a `warning:` line even though the label admits those sources were not checked. The behaviour list (Task 2, case 3) never says whether warnings print in fallback mode. Either suppress warnings for providers the fallback cannot see, or mark them as "(not confirmed: config file only)". Note that SPEC R5 lists "a served provider producing no warning" as an acceptance case.
- **MEDIUM: providers defined only in a project config are flagged as stale.** `detect_opencode_models` runs through `_run_opencode`, which uses a private empty cwd and `_probe_env()`. That env sets `OPENCODE_DISABLE_PROJECT_CONFIG=1` (`detection.py:762-775, 794-809`). The listing therefore never includes providers from the project's `opencode.json`, while the fallback reader explicitly reads those files (`<cwd>/opencode.json`, `.opencode/...`). The two sources disagree, and the primary one is the narrower. Either union the project-config provider names into the listing result, or say in the label that project config is excluded.
- **MEDIUM: `strategy` and trust state come from an untrusted local file.** `cfg_resolve` ignores an untrusted local review-spec (`config_io.py:394-410`), but the plan reads its `strategy = "local-only"` and marks the global file inactive, and it reports the local file's references as active. Use `trust.is_trusted` (already used at `config_io.py:406`): show an untrusted local file as `scanned-inactive (untrusted)`, and do not let it deactivate the global file.
- **MEDIUM: `check-providers` reads `os.getcwd()` with no `--cwd`.** Every sibling subcommand takes `--cwd` (`cli.py:173, 217, 225, 261, 267`), and spec-config passes `--cwd "$(pwd)"` to `probe-quota`. Without it, running from a subdirectory misses `./.aikit/review-spec.toml`, and the tests have to patch `os.getcwd`. Add `--cwd`, defaulting to the cwd.
- **LOW: one unreadable/malformed path is not specified.** `cfg_read_bytes` and `cfg_parse_toml_bytes` raise `ConfigError` (`config_io.py:329-354`). The plan says such a file is `scanned` with no references, so the executor must catch `ConfigError` explicitly. "scanned" also hides that nothing was actually parsed; `scanned (unreadable: …)` would be more honest, in line with the project's core value.
- **LOW: `--check-only` may write to the cache.** `_private_dir` creates the cache base and removes only its own temp subdirectory (`detection.py:778-791`). That is a small mkdir in `--check-only` mode, whose contract is "nothing persisted to caches". Worth one line in the SKILL.md, or accept it.
- **LOW [ponytail]:**
  - Resolve the binary with `detection.resolve_runtime_binary("opencode", which_fn=deps.which_fn)` (`detection.py:182`), not `detect_installed_clis`, which probes every runtime (`:205`).
  - Read the catalog with `cache.cache_read_json` (`cache.py:15`).
  - Porting `SourceStatus` as a `str` subclass with `.reason` (`cross_reference.py:118-139`) is more machinery than a three-state line needs. A plain `(status, reason)` tuple is enough.
- **LOW: `opencode_config_paths` is narrower than opencode's own lookup.** It ignores `OPENCODE_CONFIG` (an explicit file path) and the walk up to the git root. The fallback label covers this, but the drift between "files opencode reads" and "files we read" is not named anywhere.

##### Suggestions
- Add a behaviour case: listing failed, the config file lists `mine`, and the reviewer uses `opencode/free-y`. The expected result is no warning, or a qualified one, never a plain stale warning.
- Add a project-only provider case to the tracer: a provider defined in `<cwd>/opencode.json`, the listing lacks it, and the result is no warning (union) or a labelled caveat.
- Add an untrusted-local-file case.
- Add `p.add_argument("--cwd", default=None)` and pass it through.

##### Risk Assessment
**MEDIUM.** The report never blocks and never writes, so a wrong warning cannot corrupt anything. As planned, though, it will show confident "stale" warnings for providers that are actually served (the fallback mode and project-config providers). That goes against the project's core value of never claiming more certainty than it has, and the SPEC acceptance "a served provider producing no warning" would fail in those modes.

---

I read the code, plans and research but ran no tests. I did not open the 30.2 README diff hunk by hunk, so a README conflict with 30.2 is possible but unconfirmed.

### Batch B (31-03, 31-04)

### Cross-AI review of Phase 31, batch 31-03 and 31-04

Both plans are close to ready, but neither should run as written. 31-03 has three HIGH problems:

- **Task 3 uses `counts` before the variable exists.**
- **The empty-HOME test passes for the wrong reason.**
- **The R8 tracer runs a command that links nothing.**

31-04 is sound, with two MEDIUM problems: its runtime-list drift test leaves out two hand-copied lists, and the wording it adds to the 30.1 SPEC miscounts the new row.

I read each plan against the current files in this checkout (base `0e6e021`) and against the 30.1 branch. I did not run any test suite.

#### 31-03

**Summary.** The plan has the right causes and the right design. It compares resolved paths in one helper, uses the running checkout by default, and wires the headless install into the existing `prune_stale`. But there is one ordering bug, and two tests that would pass without proving anything. The plan also moves a few documented promises without updating the files that state them.

**Strengths**
- It reuses the existing pruning code: `prune_stale` (`tools/setup.py:1378-1400`), `stale_link_candidates` (`:1349`) and `apply_stale_prune` (`:1368`) already exist. Moving the non-interactive branch into `_prune_headless` is the smallest change that fits.
- It finds the real cause of the alias bug. `_is_inside` compares strings today (`tools/setup.py:1076-1079`), and every `os.readlink` caller passes the raw link value (`:1096`, `:1276-1279`, `:1425`, `:2825`, `:2865`).
- The pi filter matches what the wizard already does: `item.startswith("skills/")` at `tools/setup.py:3973-3975`.
- No other wave-1 plan lists `tools/setup.py`, `tools/install.sh` or either test file. Plan 31-05 touches `tools/setup.py` only in wave 2.
- The `pwd -P` count is right. The baseline is 2 (`tools/install.sh:78`, `:80`).

**Concerns**
- **HIGH: `counts` is used before it is created.** Task 3 step 2 calls `prune_stale(..., dry, counts)` "after `_headless_paths_and_entries` and before `migrate_statusline`". But `counts = new_counts()` runs only at `tools/setup.py:4540`, after `migrate_statusline` (`:4539`). As written, this is a `NameError`. Either create `counts` at the top or put the prune after `:4540`.
- **HIGH: the empty-HOME test passes vacuously.** The behaviour asks for exit ≠ 0 with `HOME` in stderr. Under the runner, `AI_KIT_REFUSE_REAL_HOME=1` is set. In `_refuses_real_home`, `home = env.get("HOME") or real` (`tools/setup.py:4793`) treats an empty HOME as the real home, so the run exits 2 with the refusal message (`:4899`), which also contains "HOME". The test passes even if the new guard is never written. Also, `resolve_paths(env)` already runs at `:4889` for `--with-statusline`.
  - Fix: put the new check before `:4884`.
  - Fix: assert on the new message (`HOME is unset or empty`), not just `HOME`.
- **HIGH: the R8 tracer runs bare `install --headless`, which links nothing.** A bare run prints only "nothing requested" (`tools/setup.py:4435-4437`). The pi root is touched only when `--skills` is given (`:4546-4551`). So the test would see no "0 foreign-skipped" summary line and no pi links. Both installs need `--skills all`, and Task 2's checkout-run case needs it too.
- **MEDIUM: the documented "bare `--headless` does nothing" promise changes, but the files that state it are not edited.** With the prune before `requested`, a bare `--headless` now removes links. The promise appears in:
  - `README.md:530-531` ("Bare `--headless` links and wires nothing") and `:99-102`;
  - the `--headless` help text, `tools/setup.py:4818-4821`;
  - the `cmd_install_headless` docstring, `:4484-4486` ("pure no-op").

  The SPEC (R6, "every install") supports the new behaviour. The plan should add `README.md` to `files_modified` and reword all three. Otherwise it leaves stale docs, which AGENTS.md calls a defect.
- **MEDIUM: the README is not updated for the new kit default.** `tools/setup.py:18` and `:104` are in scope, but nothing covers `README.md:621` (the `AI_KIT_DIR` env override). Check whether it states the old default.
- **MEDIUM: the realpath fix may resolve too far.** `os.path.realpath(path)` follows the last component as well. An ai-kit link whose target in the kit is itself a symlink pointing outside the kit would become "foreign". The kit has no internal symlinks today (`find skills agents tools examples -type l` prints nothing), so this is latent. Resolving only the parent (`realpath(dirname(p))` plus `basename(p)`) avoids it and still handles dangling targets.
- **MEDIUM: the subprocess install tests are in the unit tier.** They sit in `tests/test_setup.py`, which runs at pre-push and inside the 60 s budget. Real `setup.py` runs under a temp HOME are e2e by convention: `tests.test_jev_skill_install_e2e` and `tests.test_hook_registry_e2e` are in `E2E_MODULES` (`tools/run_unittest_parallel.py:115-116`). Three classes each copying `skills/` (4.6 MB) plus subprocess runs belong in an e2e module. A new e2e module also needs listing in `tools/run_unittest_parallel.py` and the gen step.
- **LOW: a variable name that does not exist.** Task 3 names `pi_present`; no such variable exists. The wizard passes the full `present` (`tools/setup.py:3966`, `:3974`). Say "use `present`, as `:3966` builds it".
- **LOW: a misleading "check all five" list.** Task 1 step 2 names `stale_link_candidates` as a `readlink` caller, but it calls `installed_links`. The real five are `:1096`, `:1276`, `:1425`, `:2825` and `:2865`.
  - `link_one`'s `cur == target` (`:1277`) stays a string compare. After the fix, an alias re-install counts as "relinked" rather than a no-op. That is acceptable, but the test should not assert 0 relinked.
- **LOW: placement of the `install.sh` HOME guard.** It must come before `tools/install.sh:49`, where `$HOME` is expanded under `set -u` (`:45`). "Near the top" should say "before line 49".
- **LOW: the race fix.** `unlink_one` (`tools/setup.py:1299-1303`) uses `lexists` then `os.remove`, so the race can only raise between the two calls. The planned `FileNotFoundError` catch is right; patch `os.remove` in the held-out test.
- **[ponytail] LOW: the fixture copies more than it needs.** The `--skills all` paths need only `skills/` and `tools/setup.py` with its siblings. A copy of `tools/` plus the three pi skills and the dead names is enough. `examples/` and the status-line files are not needed, because nothing passes `--with-statusline` or `--examples`. This is not blocking, since the plan explains why it uses a real copy.
- **Rebase notes:** correct as far as I can check. The 30.1 branch changes `tools/setup.py` near `resolve_paths` (the `@@ -117,8` hunk), the housekeeping area (the `@@ -3931` hunk) and the header (the `@@ -24` hunk). None of its new lines add a `startswith`/`readlink` ownership check outside `_is_inside`. Add a note that the 30.1 branch re-calls `stale_link_candidates` for `pi_stale` in `launch_wizard`, so the shared helper change reaches it automatically.

**Suggestions**
- Move `counts = new_counts()` above the prune call.
- Put the HOME guard first in `main`, and assert on its exact text.
- Add `--skills all` to every install in Tasks 1 and 2.
- Add `README.md` and the help and docstring rewording to Task 3.
- Put the subprocess classes in a new `tests/test_setup_install_e2e.py` in `E2E_MODULES`.

**Risk: MEDIUM.** The design is right, but the plan cannot run as written (the `NameError`), and two acceptance tests would pass without proving the behaviour.

#### 31-04

**Summary.** The changes are small, correct and well placed. Moving the guard into `check_dogfood.py` is properly justified by `check_no_planning_reader` (`tests/test_arch.py:1154`), and the engine is fast (about 0.07 s per SPEC here). I confirmed live that 30.1-SPEC.md currently fails with `missing [["encoding","R3"]]`, and that the other current SPECs (28, 29, 29.1, 30, 30.2, 31) pass, so the guard adds no surprise red. The main gap is that R13 covers only some of the hand-copied lists.

**Strengths**
- It reuses existing shapes: the notes and problems pattern of `check_lens_wiring` (`tools/check_dogfood.py:416-452`), the `main` merge (`:468-475`), and `edge_floor.main`'s exit codes (0 ok, 1 drift, 2 fail closed; `skills/ai-kit-gsd-spec-discuss/scripts/edge_floor.py:186-216`).
- It catches that 30.1 needs a row too. Without that, the new guard would block the push at once.
- The R13 sets are right against the live table:
  - `RUNNER_IDS = (pi, cursor, opencode, codex)` (`cross_ai.py:49`) is the runner set minus claude and copilot.
  - `HOSTS` (`host.py:19`) is all ids minus copilot and grok.
  - `HOST_BINARY["cursor"] = "agent"` (`gp_host.py:26`) is in `('cursor-agent', 'agent')`.
  - The JS keys at `cross-ai.mjs:1334-1439` equal the runner set exactly.
- The R11 scope is right. The other `json.loads` calls in `gp_host.py` (`:96`, `:154`, `:412`, `:520`) parse ai-kit-spec or jev output, not gsd-tools output. `_gsd_json` (`goal_prompt.py:248-257`) is the only gsd-tools parser.
- It handles the hidden test: the old superset check (`tests/test_ai_kit_spec_runtimes_table.py:477-487`) is left to plan 05, so wave 1 has no file overlap.

**Concerns**
- **MEDIUM: R13 leaves out two hand-copied runtime lists.** SPEC R13 says one test compares "every hand-copied runtime list". The plan covers four, but `cross_ai_build.REVIEWER_SLUGS = ("claude", "cursor", "opencode")` (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_build.py:62`) and `preference_match._RUNTIME_ORDER = ("opencode", "cursor")` (`preference_match.py:44`) are also hand copies. Today they are checked only as supersets (`tests/test_ai_kit_spec_runtimes_table.py:474-475`). Plan 05 will drop those weak lines, so either add both to `DELIBERATE` with their reasons, or say explicitly that they stay with the superset test.
- **MEDIUM: the 30.1 SPEC wording miscounts the new row.** `encoding | R3` is an engine floor row that was missing, not an extra row. The coverage line `30.1-SPEC.md:254` reads "46/46 … (46 engine rows …, 0 added)". After the edit it should read 47 engine rows and 0 added, not "added +1". The `(added …)` marker only matters for rows above the floor (`edge_floor.py:177-178`). For floor rows it is harmless but misleading. The same reasoning applies to 25.1, whose coverage line `:296` has no added count. Mark the rows "(restored 2026-11-06, Phase 31 guard)", or keep "(added" but count the row as an engine row.
- **LOW: the engine is gitignored.** `.claude/gsd-core/bin/lib/edge-probe.cjs` is ignored (`.gitignore:8`, `.claude/`). The named note "no project-local gsd-core engine" covers fresh clones and the long-path matrix, so this is fine. Just record in the SUMMARY that the guard is silent on a clone without gsd-core.
- **LOW: the docstring test is brittle.** Matching "runtime ids the docstring names" against the native set depends on picking ids out of free text: a future word like "pi" in prose would break it. The SPEC asks for the docstring to name the selector source rather than repeat the runtime list. A simpler assertion is: no `Phase`, contains `RUNTIMES`, and `{rid for rid, r in RUNTIMES.items() if r.native_selectors} == {"claude"}` checked against the table.
- **LOW: the `@file:` helper is close enough to gsd-core.** gsd-core's `resolveAtFileOutput` does not strip the path (`.claude/gsd-core/bin/lib/io.cjs:197-201`), while the plan strips it, which tolerates a trailing newline. That difference is harmless.
- **[ponytail] LOW: the plan-editor test is circular.** Once the error text is built from `RUNNER_IDS`, a test that "the error names exactly the RUNNER_IDS ids" checks the code against itself. Keep it short (one assertion), or drop it. The existing regex in `tests/test_curated_config_plan_edit.py` already pins the text.
- **Rebase notes:** correct. The 30.1 branch's change to 30.1-SPEC.md is a prose amendment around line 169 that does not touch the Edge Coverage table, so the added row merges cleanly. The Makefile and pre-commit regeneration is the right step.

**Suggestions**
- Add `REVIEWER_SLUGS` and `_RUNTIME_ORDER` to the drift test, or record why they stay out.
- Fix the coverage wording for floor rows.
- Simplify the docstring test to "no Phase, names `RUNTIMES`".

**Risk: LOW.** The changes are small and read-only, every new path has a test, and the guard has been checked live against the current SPECs.

---

The 31-03 rebase notes are only checked against the hunk headers in the 30.1 diff; I did not read each changed line. I also did not check `README.md:621` for default-path wording. Main risk: if 31-03's ordering bug and its vacuous HOME test are not fixed before execution, the executor will either crash or record a false green.

### Batch C (31-05, 31-06)

### Cross-AI plan review: Phase 31, batch 31-05 and 31-06

I checked both plans against the base worktree (`e8e3761`) and the 30.1 branch. I used read-only `git grep`, `rg` and `git show` only. I edited nothing and ran no tests.

#### 31-05

**Summary.** The plan is mostly sound. Its lists of files to delete and edit match the live search results. It covers both hidden items the research flagged: `.claude-plugin/plugin.json:3` and the sample module in `tests/test_run_unittest_parallel.py` at lines 47, 52 and 182. The pi wording change targets the right files. One acceptance search cannot pass as written, and a few smaller gaps need fixing.

**Strengths**
- The removal inventory is complete. A tracked-file `git grep`, hidden files included and history folders excluded, finds the providers skill and mermaid-audit only where the plan already lists them: `README.md:31` and `:40`, `pyproject.toml:113`, `:133` and `:137`, `tests/test_gate_scope.py:39`, `tests/test_ai_kit_spec_runtimes_table.py:813` and `:816`, `tools/config_doctor_readers.py:89`, `:109`, `:123` and `:140`, `tools/config_doctor_appliers.py:30` and `:148`, `tools/setup.py:1881`, usage-metrics `paths.py:6` and `raw_store.py:34`, `render_mermaid.py:5`, and the generated listings.
- No kept code imports either removed skill. `render_mermaid.py:5` names mermaid-audit only in its docstring, so the claim that only the docstring changes holds.
- The R9 messages point at the right places. The text lives in `recommend.py:325` and `plan_io.py:540-541`, not in `inventory.py`, which only reads the variable (`inventory.py:472`). The existing pins still match the new text: `"PI_PROVIDER is unset"` (`tests/test_curated_config_recommend.py:940`) and `PI_PROVIDER.*plan-unset` (`tests/test_curated_config_plan_edit.py:256`).
- The superset checks it removes really are weak and duplicated. `test_runner_template_keys_use_table_ids` stops at the first `};` (`tests/test_ai_kit_spec_runtimes_table.py:484`), as the research says. The two `RUNNER_IDS` lines at `:471-472` are the ones plan 04's drift test replaces. `re` is still used elsewhere (`:521`, `:615` and others), so the import stays.
- 30.1 does not touch `skills/markdown-to-pdf` (`git diff --stat` against the 30.1 branch is empty). It also adds no new mention of either removed skill outside the README and `plugin.json` lines the plan already handles.

**Concerns**
- **HIGH: the R1 acceptance search can never print nothing.** The pattern `ai_kit_spec_gsd` also matches the kept module name `tests.test_ai_kit_spec_gsd_tools`. That name appears in the generated `Makefile:12` and `.pre-commit-config.yaml` (lines 15 and 71). It also appears in the docstring at `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py:11`, which points at `tests/test_ai_kit_spec_gsd_tools.py`. That test file is kept on purpose (SPEC Background). So the check at `31-05-PLAN.md` Task 2 and the matching truth fail even when the work is correct. 31-01 has the same pattern, and so does SPEC R1's acceptance.
  - Fix: add a word boundary, `ai_kit_spec_gsd\b`. The underscore in `_tools` is a word character, so the kept name no longer matches.
- **MEDIUM: `tests/test_run_unittest_parallel.py` depends on a module that is only fast by assumption.** The new sample, `tests.test_ai_kit_spec_execute_router`, comes from plan 01 and has never been timed. Research assumption A4 says to "choose and time one". The case at `:182` also runs it from a foreign working directory, so the module must load its SKILL.md through `__file__` (31-01 says it does). Record its run time in the SUMMARY.
- **MEDIUM: the `test_ai_kit_spec_runtimes_table.py` comment edit assumes 31-01 finished.** The new comment "curated-config is checked for forbidden tokens only" (`:816`) is only true if 31-01 already replaced `PAIR_RULE_SKILLS = REWRITTEN[:4]` (`:818`) with an explicit list. If that edit did not land, removing the providers entry shrinks the list, and `[:4]` would quietly pull curated-config into the pair-rule check. Add a read-first check that `:818` no longer slices.
- **LOW: the "no old wording" check misses the SKILL.md phrasing.** The SKILL.md says "reads inside **a** pi session" (`SKILL.md:134-135`). The acceptance search `rg -c 'inside the pi session'` (baseline 2 files) only finds the two Python messages. The sentence is rewritten anyway, but `TestPiSessionVariableWording` should also forbid `inside a pi session`.
- **LOW: `git diff 0e6e021 --stat -- skills/markdown-to-pdf` hardcodes the base commit.** After the 30.1/30.2 rebase the base changes. Use `git diff <merge-base> ...` or `git log --stat` over the plan's own commits.
- **LOW [ponytail]:** Task 3's evals need 6 entries. `tests/test_skill_evals_shape.py:33` asks for at least 5 and one of each kind (`casual`, `precise`, `edge`). Six is fine, not over-built.
- **LOW:** the dated correction notes edit `.planning/milestones/...`. No test reads them, because `tests/test_pi_live_tools.py:18` reads `tests/fixtures/archived/22`, which stays untouched. That is correct, and the plan says so.

**Suggestions**
- Change every R1 search in 31-01, 31-05 and the verification to `ai_kit_spec_gsd\b`.
- Add a guard step: `grep -c 'REWRITTEN\[:4\]' tests/test_ai_kit_spec_runtimes_table.py` must print 0 before the comment is edited.
- Have `TestPiSessionVariableWording` also forbid `inside a pi session`.

**Risk: MEDIUM.** The deletion work is low risk. The R1 acceptance check fails on a correct tree, so an executor will stall or "fix" it the wrong way unless the pattern changes.

#### 31-06

**Summary.** The rtk inventory is complete. After the plan runs, every tracked hit outside the named exemptions is gone, on the base and the 30.1 branch alike: AGENTS.md, README, `tool_presence`, rules-agents, the doctor files and tests, the hook test, plus the wizard fixtures that the rebase note covers. The R05 retirement fits the existing count test. Two test changes are under-specified and would break or confuse the run: the PTY doctor test's sentinel and the full-catalog regression test.

**Strengths**
- The inventory is complete: `git grep -i -w -I rtk` with the exemptions applied lists exactly the plan's files, on the base and the 30.1 branch. On 30.1 the extra hits are `tests/test_wizard_app_1.py:181,188` and `tests/wizard_fixtures.py:102`, and the rebase note handles them. `docs/run-book`, `.github`, `tools/hooks` and the Makefile have none.
- The count words are already guarded. `TestRuleCountStrings` (`tests/test_ai_kit_project_rules_agents.py:1165-1180`) ties every `<n>-rule` string to `len(rules.RULES)`. The 7 hits the plan lists match the live search exactly. No test counts 20 rules any other way; `:859` checks only the last four ids, R17 to R20.
- `tool_presence["rtk"]` has exactly one consumer, `condition_tool_presence("rtk")` at `rules.py:110`. Removing the key breaks nothing else.
- usage-metrics' SKILL.md passes the D-06 pattern unchanged. Its rtk mentions are "`rtk`'s own local stores" (line 14), "rtk `${XDG...}`" (line 23) and column names (lines 109-113). None of them is a backticked `rtk <subcommand>`. So "SKILL.md unchanged, not judged" holds.
- The link test reuses the right helpers: `_LINK_RE`, `_parse_link_target` and `_without_fenced_code` (`skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py:22,30,51`). Using `git check-ignore -q` without `--no-index` reports only untracked ignored paths, which matches the intent. AGENTS.md has exactly two relative links, at lines 132 and 291, and only the first is bad.
- The row counts are right: 26 today, 27 on 30.1 (`git show <30.1>:tests/test_config_doctor.py:943`). After this plan they become 25 and 26. The `cross` section still exists afterwards, because the second cross row at `tools/config_doctor_checks.py:1041` stays.

**Concerns**
- **HIGH: the PTY doctor test breaks once its stub goes.** `tests/test_config_doctor_pty.py` waits for `b"registered"` (`:200`) and asserts `assertIn("registered", decoded)` (`:220`). The word `registered` is the display string of the rtk row (`tools/config_doctor_checks.py:569-570`). The plan says "keep the case, drop only its rtk stub". Once the row is gone, the wait runs out its 30 s deadline and the assertion fails. The plan must swap the sentinel for another row's text that the fixture already produces, for example `cleanupPeriodDays`, and remove the `registered` assertion.
- **MEDIUM: Task 2's instructions for the full-catalog test overlap.** It says "delete the rtk fixtures and every rtk case (~776-940)". `TestFullCatalogRegression.test_five_sections_twenty_six_rows` starts at `:932`, inside that range, yet the same step says to rename and keep it. That test also:
  - builds an rtk stub (`:936-940`), which must be removed, not the test;
  - asserts `total == 26` on the rendered catalog (`:949`), which the plan never mentions. It must become 25, then 26 after the rebase, next to `len(CONFIG_DOCTOR_ROWS)`.
  
  Spell out both edits.
- **MEDIUM: the rebase timing leaves 30.1 able to bring rtk back.** The rename of `rtk-hint` happens "after the 30.1 rebase". If 31 lands first and 30.1 merges later without the rename, `tests/wizard_fixtures.py:102` brings the word back and the new ban fails on main. Either do the rename in 30.1 now, or make the ban test run part of the merge checklist. The plan's orchestrator step already lists it, so this is mainly about timing.
- **LOW: `banned_mentions` does not handle a missing file.** `git ls-files` lists paths that may be deleted in the working tree but not yet staged. The reader should skip a missing file (FileNotFoundError) instead of erroring.
- **LOW: `bad_links` does not say what a missing, ignored target reports.** The behavior lists missing and ignored separately but not a target that is both. Report `missing` first, since check-ignore on a missing path still matches by pattern.
- **LOW: the SKILL.md example swap.** R06's `signals` are nested pairs, `(("rg", ("rg","ripgrep")), ...)` (`rules.py:123-129`). Replacing the R05 example at `SKILL.md:65-67` "with R06's real values" should copy what `remediate` actually prints for R06, not the Python tuple.
- **LOW [ponytail]:** after the rtk reader goes, `ReadContext.runner` and `build_catalog(runner=...)` have no consumer: `ctx.runner` is read only at `tools/config_doctor_checks.py:568`. 30.1 review notes discuss passing a runner into `_config_doctor_ctx`, so keep it, but say in the SUMMARY that it is unused for now. Don't delete it in this plan, because 30.1 code builds on it.
- **[ponytail] OK:** the `\b20[- ](house )?rules?\b` search duplicates `TestRuleCountStrings`. That is harmless as a one-off acceptance check; add no new test for it.

**Suggestions**
- Task 2: switch the PTY sentinel to a non-rtk row's text, and list the `total` assertion (`:949`) with the stub removal (`:936-940`).
- Task 3: have `banned_mentions` skip unreadable or missing paths. Order the `bad_links` labels as missing, then ignored.
- Ask the 30.1 owner to rename `rtk-hint` in 30.1 itself, so neither merge order breaks the ban.

**Risk: MEDIUM.** The removals are mechanical and well inventoried. The PTY test failure is certain as written, and the full-catalog edit is ambiguous enough that an executor could delete the regression test.

#### Cross-plan notes
- **Shared files:** 05 (wave 2) and 06 (wave 3) share `README.md`, `tools/config_doctor_readers.py` and the generated listings. They run in different waves, so this is fine.
- **Rebase notes:** they are correct for `config_doctor_checks.py`, the row count 27→26, the wizard `rtk-hint` hits and README context. They are incomplete only for the `total` assertion in `test_config_doctor.py` (`:949`).

---

I did not run tests, time the new sample module, or check that `skills/ai-kit-spec-execute/SKILL.md` and the 31-01 to 31-04 code exist; plans 01 to 04 are not executed on this base. The two issues that will fail as written are the `ai_kit_spec_gsd` search pattern and the PTY test's `registered` sentinel.


## Consensus Summary

### Agreed Strengths

- The removal inventory is complete. Both reviewers ran the tracked-file search, hidden files included, and found
  every hit outside the history folders inside some plan's edits, including `.claude-plugin/plugin.json:3` and the
  `tests/test_run_unittest_parallel.py` sample module.
- Same-wave plans share only the generated `Makefile` and `.pre-commit-config.yaml` listings.
- The line anchors match the tree, and the D-08 deviation (the edge-floor guard in `tools/check_dogfood.py`) follows
  from `check_no_planning_reader`. Both reviewers re-ran the engine: only 25.1 and 30.1 fail, each by one row.
- The 30.1 rebase notes hold against the 30.1 branch (`rtk-hint` fixture, doctor row count 26, README doctor sentence,
  `resolve_paths` hunk). No plan removes a feature the SPEC does not name.

### Agreed Concerns

- **HIGH (both reviewers; 31-01 and 31-05):** the R1 search `ai_kit_spec_gsd` also matches the kept module
  `tests.test_ai_kit_spec_gsd_tools` in the generated listings and in the `gsd_tools.py:11` docstring, so "prints
  nothing" can never pass.
- **31-03 (both reviewers; referee-three HIGH, referee-two LOW):** the prune call uses `counts` before
  `counts = new_counts()` exists (`tools/setup.py:4539-4540`).
- **31-03 (both, MEDIUM):** a bare `--headless` run now prunes, so the "nothing touched" docstring, the help text, a
  code comment and README text go stale.
- **Rebase notes (both, LOW):** they name 30.1 only; the 30.2 plans also edit `tools/setup.py`, `README.md`,
  `tests/wizard_fixtures.py` and `tests/test_arch.py`.

### Divergent Views

- **Template parser (31-04):** referee-two suggested reusing the split-based key extraction in
  `tests/test_ai_kit_spec_runtimes_table.py:484-485`. Rejected: the orchestrator ran it, and it returns only `['cursor']`
  of six keys, so the plan's brace-matched parse stays.
- **The `tests/fixtures/archived/` exemption (31-06):** referee-two found zero rtk hits there and asked to drop it
  from the rtk test. Accepted: the exemption stays only in the removed-skill searches, which do have hits there.

## Triage (orchestrator, 2026-11-06)

Every finding was first screened by jev-fast-decision (calls `jev-2`, typesafe backend, batch mode: every item
`needs_fallback: true`, so jev's leanings are advisory only and the orchestrator decided). It was then checked against
the plan text and the source (`tmp/review-31/verify.sh`). "Confirmed" means the source proves the defect.

### Confirmed HIGH (6 unique; 9 HIGH labels across the six reviews)

| # | Plan | Finding | Evidence | Plan change |
|---|------|---------|----------|-------------|
| H1 | 31-01, 31-05 | R1 search can never pass (substring of the kept `tests.test_ai_kit_spec_gsd_tools`) | `Makefile` 1 hit, `.pre-commit-config.yaml` 2 hits on the kept name | Every R1 search uses `ai_kit_spec_gsd\b` (the SPEC R1 adjacency edge: full removed names only); the `gsd_tools.py:11` docstring keeps its accurate citation of the kept test, and its reword instruction is dropped |
| H2 | 31-02 | In config-file fallback mode, built-in, environment and login providers are reported as plainly stale | Those providers never appear in `provider`/`providers` keys; SPEC labels the fallback "config file only; login and environment providers not checked" | Fallback-mode warnings carry the qualifier `(unconfirmed: config file only; built-in, login and environment providers not checked)`; a test covers a built-in provider in fallback mode |
| H3 | 31-03 | `counts` used before it exists | `tools/setup.py:4539` `migrate_statusline`, `:4540` `counts = new_counts()` | Hoist `counts = new_counts()` above the prune call; update the locals note and pylint budget comment |
| H4 | 31-03 | The empty-HOME test passes for the wrong reason | `_refuses_real_home` maps an empty HOME to the real home (`tools/setup.py:4793`) | The HOME check runs first in `main`, before the refusal and before `resolve_paths`; the test asserts the exact new message |
| H5 | 31-03 | The R8 alias tracer runs bare `install --headless`, which links nothing | `_headless_summary` "nothing requested" (`tools/setup.py:4435-4437`); pi is touched only with `--skills` | Every install in the R8 tests passes `--skills all` |
| H6 | 31-06 | The kept PTY doctor test waits for and asserts `registered`, the removed rtk row's text | `tests/test_config_doctor_pty.py:200,220`; `tools/config_doctor_checks.py:570` | Swap the sentinel to a kept row's text that the fixture already prints, and drop the `registered` assertion |

### Confirmed actionable (MEDIUM and LOW)

| # | Plan | Finding | Plan change |
|---|------|---------|-------------|
| A1 | 31-01 | `SKILL.md:128` copilot sentence becomes false; `:231-236` mixes the kept v1 clause with the removed hook | Exact replacement text; keep the v1 `--codex-sandbox workspace-write` clause |
| A2 | 31-01 | `gsd_tools.config_set` docstring cites the undo log that read `previousValue` (`gsd_tools.py:269-271`) | Trim that parenthetical in the R2 task |
| A3 | 31-01, 31-02 | `read_first` names a nonexistent `skills/ai-kit-spec-review/evals/evals.json` | Point at `skills/ai-kit-spec-goal-prompt/evals/evals.json` |
| A4 | 31-01 | Moving `TestGsdPurposeFilterInertness` duplicates `TestFilterByPurpose` (`tests/test_ai_kit_spec.py:5604`) | Keep one case at the `resolve_execute_candidates` level, placed in a file no other wave-1 plan edits |
| A5 | 31-02 | Untrusted local review-spec still deactivates the global file | Use `trust.is_trusted` as `cfg_resolve` does (`config_io.py:394-410`): an untrusted local file prints `scanned-inactive (untrusted)` and never deactivates the global one |
| A6 | 31-02 | The listing runs with project config disabled (`detection.py:762`), so project-only providers look stale | When the listing succeeds, add the project config files' provider names and say so in the label |
| A7 | 31-02 | No `--cwd` on `check-providers`; siblings take one (`cli.py:173`, `:371`) | Add `--cwd` (default: the current directory) |
| A8 | 31-02 | Empty successful listing and unreadable files are unspecified | Empty listing gives `not checked: opencode listed no models`; an unreadable file prints `scanned (unreadable: <reason>)` |
| A9 | 31-02 | [ponytail] reuse `detection.resolve_runtime_binary` (`:182`) and `cache.cache_read_json` (`cache.py:15`) | Adopt both |
| A10 | 31-03 | Bare `--headless` docs go stale (docstring `:4484-4486`, comment `:4546-4548`, help text, `README.md:531` and `:99-102`) | 31-03 rewords the docstring, comment and help text; the README lines go to 31-05 (the README owner after wave 1) |
| A11 | 31-03 | Full `realpath` also follows the last component | Resolve the parent folder and keep the leaf name |
| A12 | 31-03 | Small mechanics: `present` is built in `launch_wizard` (`:3966`), not `_make_apply_housekeeping`, and `pi_present` does not exist; the `/home/[a-z]` gate trips on the `/home/u` fixtures; `pwd -P` count must be 3; the `install.sh` HOME guard goes before line 49; do not assert 0 relinked; the must_have wording on `AI_KIT_DIR` vs LOCAL mode is misleading | Each fixed in the task text |
| A13 | 31-03 | Subprocess install tests in the unit tier (jev `c1`: a, low confidence; orchestrator agrees) | Keep them in `tests/test_setup.py` with the copy in `setUpClass`; the executor records the module time in the SUMMARY and moves the classes to a new e2e module only if the module grows by more than 5 s |
| A14 | 31-04 | The engine needs its sibling modules (`edge-probe.cjs:29,31`) | The real-engine test links the engine's `bin/lib/` folder into the temp root |
| A15 | 31-04 | An in-progress SPEC with no Edge Coverage section would block every push (jev `c2`: a) | Such a SPEC is a named note `not checked: no Edge Coverage section`; a SPEC whose section exists and drifts fails |
| A16 | 31-04 | R13 misses `cross_ai_build.REVIEWER_SLUGS` (`:62`) and `preference_match._RUNTIME_ORDER` (`:44`) | Both join the drift test with their deliberate differences |
| A17 | 31-04 | The restored 30.1/25.1 rows are floor rows, not extra rows | Keep the SPEC's `(added …)` marker text as `(added 2026-11-06: restores the missing engine floor row)`, and count the row among the engine rows in the coverage line |
| A18 | 31-04 | Small mechanics: patch `ai_kit_spec.routing.RUNTIMES`; the docstring test asserts no `Phase`, names `RUNTIMES`, and the native-selector set equals `{"claude"}` from the table; the garbled helper sentence; the circular plan-editor test | Each fixed; the circular test is dropped (the existing regex pins the text) |
| A19 | 31-05 | Guard on 31-01's `REWRITTEN[:4]` fix; forbid `inside a pi session` too; record the new sample module's time; no hardcoded `0e6e021` in an acceptance diff | Each added |
| A20 | 31-06 | The full-catalog regression test: keep and rename it, remove only its rtk stub (`:936-940`), and set the rendered `total` (`:949`) to 25 (26 after the 30.1 rebase) | Spelled out |
| A21 | 31-06 | `banned_mentions` skips a listed but missing file; `bad_links` reports `missing` before `ignored`; the R06 example uses `remediate`'s printed output; `ReadContext.runner` stays (30.1 builds on it) and the SUMMARY says it is unused for now | Each added |
| A22 | 31-06 | `tests/fixtures/archived/` has no rtk hits (jev `c3`: a) | Dropped from the rtk test's exemptions; kept for the removed-skill searches |
| A23 | all | Rebase notes omit 30.2 | One 30.2 line in each plan that touches `tools/setup.py`, `README.md`, `tests/wizard_fixtures.py` or `tests/test_arch.py` |

### Rejected or not actionable

- 31-04 template parser reuse: refuted (the split returns one key of six).
- 31-02 `opencode_config_paths` narrower than opencode's own lookup (`OPENCODE_CONFIG`, git-root walk): the fallback
  label already says "config file only"; no change.
- 31-02 `--check-only` may create the cache base through `_private_dir`: pre-existing behaviour of
  `detect-runtimes`, which `--check-only` already runs; out of scope, no change.
- 31-06 `rtk-hint` merge timing: the stacked PRs merge 30.1 before 31, and 31 is rebased onto 30.1 first, so the
  rename lands with the ban; the orchestrator step already lists it.
- 31-06 the stale `>= 24` row-count test name: cosmetic, no change.

**Counts:** 6 unique HIGH, all confirmed; 23 actionable groups confirmed; 1 refuted; 4 not actionable.
