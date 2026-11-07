---
phase: 32
cycle: 2
reviewers: [referee-two]
reviewed_at: 2026-11-07T12:52:07-03:00
plans_reviewed: [32-01-PLAN.md, 32-02-PLAN.md, 32-03-PLAN.md, 32-04-PLAN.md, 32-05-PLAN.md, 32-06-PLAN.md, 32-07-PLAN.md, 32-08-PLAN.md, 32-09-PLAN.md]
models:
  referee-two: "router-env/my-referee-two"
model_sources:
  referee-two: "pinned"
---

# Cross-AI Plan Review — Phase 32

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## Review conditions (cycle 2)

Cycle 2 reviewed the nine plans as revised at `96d73cc`. Cycle 1 had reviewed them at `d9117a4`, and its review and
triage are kept below under "Cycle 1 (history)".

The only reviewer was referee-two: it is `review.default_reviewers`, uses the opencode lane, and has the model
`router-env/my-referee-two` pinned through `review.reviewer_instances`. No other reviewer, harness, provider or model
was used. The probe at 12:23:45 was a one-word prompt; it came back `OK`, exit 0, in 4 s.

The batches were the same as in cycle 1, each with its own run dir under the gitignored `tmp/p32-review-c2/`:

- A: 32-01, 32-02 (166 KB)
- B: 32-03, 32-05 (143 KB)
- C: 32-04, 32-07 (180 KB)
- D: 32-08, 32-09 (142 KB)
- E: 32-06 (119 KB)

C is the largest prompt referee-two has taken so far. The opencode lane declares no prompt cap (`review-lane plan`
reports `promptBudget` null), and C finished in 415 s.

Each prompt inlined what cycle 1's did:

- PROJECT.md (first 80 lines), the ROADMAP Phase 32 section (now with criterion 3's amendment), the JDG-01..JDG-08
  rows, 32-SPEC.md and 32-CONTEXT.md;
- a pointer to 32-RESEARCH.md and 32-PATTERNS.md;
- a wave map of all nine plans;
- the batch's plans in full;
- the source-grounding instructions, the owner's ponytail lens verbatim, the haiku-executor note, the same-wave
  overlap check and the batch's plan coverage manifest.

New in cycle 2, each prompt also inlined cycle 1's triage for the batch's plans, read from the committed `df3319f`
version:

- the confirmed findings, with the change each asked for;
- the refuted findings, with their evidence;
- for A and C, the roadmap drift note.

The instructions asked the reviewer to:

- give each confirmed cycle-1 item a FIXED, PARTIALLY FIXED or NOT FIXED verdict under `##### Cycle 1 fixes`;
- re-raise a refuted finding only with new `file:line` or command evidence;
- focus on problems the revision introduced.

The read-only rule also forbade scratch files outside the repository.

Each batch ran through `review-lane invoke --slug opencode --as referee-two --model router-env/my-referee-two`. At
most two batches ran at a time, each in its own process group, under a 15-minute no-I/O-growth stall watch. There
was no stall, retry, quota stop or auth stop, so the ai-kit-cross-ai retry ladder was never entered: one attempt per
batch, five in all.

- **referee-two** (`router-env/my-referee-two`): A 241 s, B 282 s, C 415 s, D 117 s, E 234 s (12:25:40 to 12:38:17).
  Every lane returned `ok`, not stubbed, model source `pinned`. The plan coverage check found every plan id of each
  batch in its review (9/9).

Each batch's leading progress narration (the lines before its first heading) is left out below. In A and E those
lines also restate findings that the body repeats; in E the fold finding is MEDIUM in the narration and HIGH in the
body, and the triage uses HIGH. The raw outputs are preserved under `.review-diagnostics/`. Nothing appeared under
`/tmp/opencode/` during the run, and no tracked file changed (`git status` was clean afterwards).

Triage ran in two steps, as in cycle 1. First jev-fast-decision gave an advisory answer from a value-free summary of
each finding and its verification. Then the orchestrator checked each finding against the plan text and the source:
codegraph for code, rg for Markdown. Where a finding was about behaviour, the orchestrator ran it, with scripts under
`tmp/p32-review-c2/`:

- a live run of 32-04's exact `ask_jev` call (`ask_jev_live.py`);
- the revised fixture verdicts under the phase 27 validator (`sim_fixtures.py`);
- every 32-03 edit applied in memory under the plan's rules (`sim_postedit.py`);
- 32-06's fold rule against PyYAML (`fold_check.py`);
- the four base commits and the old-score cells (`bases_and_scores.py`).

A finding counts as real only when that check confirms it. Six findings the reviewer withdrew or said need no change
were not sent to jev: A2-6, B2-2, B2-3, B2-4, C2-4 and D2-10, listed in the Triage.

### jev log (cycle 2; advisory; Laya, then TypeSafe; "fallback" means `needs_fallback`)

Triage was four calls at 12:43 with 32 items. Each item stayed under Laya's 2,000-character guard and each call under
TypeSafe's 8,000.

- A2-1: laya real 0.43 (fallback), typesafe real 0.48 (fallback); own reasoning. Refuted as stated (the round number
  comes from the folder); a weaker version is confirmed at LOW.
- A2-2: laya not_real 0.45 (fallback), typesafe not_real 0.95; typesafe; refuted.
- A2-3: laya not_real 0.44 (fallback), typesafe real 0.65 (fallback); own reasoning; refuted.
- A2-4: laya lower 0.47 (fallback), typesafe not_real 0.87; typesafe; refuted.
- A2-5: laya lower 0.42 (fallback), typesafe lower 0.86; typesafe; not actionable.
- A2-7: laya not_real 0.45 (fallback), typesafe not_real 0.92; typesafe; refuted.
- A2-8: laya not_real 0.42 (fallback), typesafe not_real 0.43 (fallback); own reasoning; not actionable.
- A2-9: laya not_real 0.35 (fallback), typesafe not_real 0.75 (fallback); own reasoning; not actionable.
- B2-1: laya not_real 0.43 (fallback), typesafe real 0.70 (fallback); own reasoning; refuted by the post-edit
  simulation.
- C2-1: laya real 0.53 (fallback), typesafe not_real 0.99; typesafe; refuted (live run).
- C2-2: laya real 0.45 (fallback), typesafe real 0.91; typesafe says real. Not followed: the commit-stage pylint hook
  and the rails' split rule refute it, as with cycle 1's A5, A8 and C13.
- C2-3: laya lower 0.36 (fallback), typesafe lower 0.49 (fallback); own reasoning; not actionable.
- C2-5: laya not_real 0.56 (fallback), typesafe not_real 0.98; typesafe; refuted.
- C2-6: laya not_real 0.47 (fallback), typesafe not_real 0.62 (fallback); own reasoning; refuted.
- C2-7: laya real 0.54 (fallback), typesafe real 0.96; typesafe; confirmed MEDIUM.
- C2-8: laya lower 0.55 (fallback), typesafe real 0.93; typesafe says real. Not followed, for the same reason as C2-2.
- C2-9: laya not_real 0.41 (fallback), typesafe lower 0.67 (fallback); own reasoning; not actionable.
- C2-10: laya lower 0.64 (fallback), typesafe not_real 0.87; typesafe; refuted.
- D2-1: laya not_real 0.47 (fallback), typesafe not_real 0.98; typesafe; refuted.
- D2-2: laya not_real 0.46 (fallback), typesafe not_real 0.59 (fallback); own reasoning; refuted.
- D2-3: laya not_real 0.42 (fallback), typesafe not_real 0.86; typesafe; refuted.
- D2-4: laya real 0.50 (fallback), typesafe not_real 0.62 (fallback); own reasoning; refuted.
- D2-5: laya lower 0.41 (fallback), typesafe not_real 0.98; typesafe; refuted.
- D2-6: laya not_real 0.55 (fallback), typesafe not_real 0.82; typesafe; refuted.
- D2-7: laya not_real 0.46 (fallback), typesafe not_real 0.93; typesafe; refuted.
- D2-8: laya not_real 0.43 (fallback), typesafe not_real 0.96; typesafe; refuted.
- D2-9: laya lower 0.45 (fallback), typesafe lower 0.95; typesafe; not actionable.
- E2-1: laya not_real 0.60 (fallback), typesafe not_real 0.94; typesafe; refuted.
- E2-2: laya not_real 0.50 (fallback), typesafe not_real 0.94; typesafe; refuted.
- E2-3: laya not_real 0.38 (fallback), typesafe not_real 0.59 (fallback); own reasoning; refuted.
- E2-4: laya real 0.36 (fallback), typesafe not_real 0.92; typesafe; not actionable.
- E2-5: laya lower 0.55 (fallback), typesafe not_real 0.92; typesafe; refuted.

## OpenCode Review (referee-two), cycle 2

### Batch A (32-01, 32-02)

#### Review: .planning/phases/32-re-judge-baseline/32-01-PLAN.md, 32-02-PLAN.md
##### Document Type
GSD · plan

##### Files Read
- `.planning/phases/32-re-judge-baseline/32-01-PLAN.md`, `32-02-PLAN.md`, `32-04-PLAN.md`, `32-07-PLAN.md` (handoffs), `32-SPEC.md` (grounding)
- `.planning/milestones/v1.3-phases/27-one-shot-goal-and-loop-prompt-skill/skill-judge/check_verdicts.py` (lines 1–180)
- `tools/check_dogfood.py` (1–40, 460–543), `tools/run_unittest_parallel.py` (240–269, 575–614), `tools/staged_mapper.py` (80–239)
- `skills/jev-fast-decision/scripts/jev_ladder.py` (25–114)
- `tests/test_arch.py` (1680–1749), `tests/test_gate_scope.py` (1–20, 620–669), `tests/test_check_dogfood.py` (510–549)
- `.planning/ROADMAP.md` (385–457, headings at 147, 886, 930)

##### MEDIUM
- **`check` crashes on a record whose `round` is missing or not an int** — Location: `.planning/phases/32-re-judge-baseline/32-01-PLAN.md` Task 1 `check` (the paragraph that starts `check(root, records, opts)`). Required: a record that is not a dict, or whose `round` is absent or not an int, becomes a named problem and the function returns; it never raises. Why: the latest round is "the highest" `r<N>` folder, then every record of that round is read and `record["round"]` is used as the round number. `validate_verdict` checks only the verdict object (`check_verdicts.py:41-79`), never the record envelope, so a hand-written or half-written record (D-07 says check-dogfood runs this on every push) raises `KeyError` or `TypeError` instead of exit 1. The tracer only feeds a record the tool itself wrote.
- **A finding whose `file` does not exist raises instead of failing the attempt** — Location: `32-01-PLAN.md` Task 2 step 2 (`finding_path_errors`). Required: a finding `file` that does not exist, or whose parent is not a directory, is the attempt error, and the record is written with `verdict` null. Why: the behavior line says `../../outside.md` or a file that "does not exist" is a failed attempt (exit 0, record written). The action says the resolved path "must stay under it and be a file" and then "a non-null `line` must be <= the file's line count". Counting lines of a missing file raises `FileNotFoundError`, which `main` turns into a traceback, not exit 1. The confinement check has to come first and a missing file has to be the error text, not an exception.
- **"Highest counts" does not say which verdict's critical and high** — Location: `32-01-PLAN.md` Task 1 `check`, the sentence "critical and high = the highest counts over those verdicts". Required: one rule, the maximum of each count taken separately over the verdict-bearing records. Why: one judge at 1 critical and 0 high and another at 0 critical and 2 high is either "1 critical, 2 high" or "the worst judge's counts". The tracer uses one judge, so it passes either reading. `32-07-PLAN.md` later says "the highest raw counts", which confirms the separate-max reading, but this plan is what the executor implements first.

##### Cross-Document Consistency
- **L5 probe shape matches 32-04.** `32-01` writes `AIKIT-SENTINEL-<8 hex>-...` (one code per embedded file, hyphens, one word) and `32-04` `probe_result` compares `lane.out.strip()` with that `token` file exactly (`32-04-PLAN.md` Task 1). The fixture answer there is three codes of the same shape. No mismatch.
- **M2 arithmetic holds.** `make_verdict(..., drops={"D1": (125, "high"), "D2": (75, "medium")}, maxima={d: 125 for d in DIMS})` gives scores D1 0, D2 50, six at 125, total 800 of 1000, percent 80.0, grade B, findings F1 and F2. The 79.9 call (D2 loses 76) gives total 799, percent 79.9, grade C. Both stay non-negative, and both have one finding per below-max dimension, which is what `validate_verdict` requires (`32-01-PLAN.md` Task 1, "plus ... a finding for every dimension scored below its max").
- **No same-wave file overlap.** Wave 1 is 32-01 and 32-02. 32-01 edits `tools/judge_loop.py`, `tests/test_judge_loop.py`, `tests/test_arch.py`, `agents/ai-kit-judge.md`, `README.md`, `Makefile`, `.pre-commit-config.yaml`. 32-02 edits `tools/check_dogfood.py`, `tests/test_check_dogfood.py`, `tests/test_gate_scope.py`. 32-02 adds no test module, so it does not regenerate the listings. `depends_on` is empty on both, and neither reads the other's output.

##### Status: Issues Found — fix and re-invoke

#### 32-01

`tools/judge_loop.py` is specified tightly enough to build: one stdlib module, three subcommands, a fixture git repo, and a tracer that walks prompt, ingest and check. The revision fixed the three cycle-1 items that named this plan, and the 80.0 / 79.9 fixtures now survive the validator they are tested against. What is left is error handling around records and finding paths the tracer never feeds, plus one count rule the one-judge tracer cannot pin.

##### Strengths
- The prompt rules are literal sentences, including both D7 splits in one fixed rule 5, so two skills differ only in the name and the rule 4 line (`32-01-PLAN.md` Task 1, rules 3-5). That matches SPEC R2.
- `module_list` reuses `staged_mapper.covering_modules(build_index(root), "skills/<name>/SKILL.md")`. `build_index` returns `tests.<stem>` (`tools/staged_mapper.py:94-95`), and `removeprefix("tests.")` turns that back into `tests/<stem>.py`. SKILL.md is a data file, so the data-file path in `covering_modules` (`tools/staged_mapper.py:218-223`) is the one that runs. Correct.
- `SKILLS_ROOTS` is specified as the same five-row tuple as `jev_ladder.py:35-41`, and `LOOKUP_COPIES` gains `tools/judge_loop.py` (`tests/test_arch.py:1687-1694`). `python_roots` reads it with `ast.literal_eval` (`tests/test_arch.py:1728-1734`), so the copy is drift-checked.
- Digest, pin and ingest refusals are concrete: trailing-slash pathspec, sha256 over `<hash>  <path>\n`, pin from the rubric's first two lines, a verdict record never overwritten (`32-01-PLAN.md` Task 1 and Task 2).
- The probe revision is the right shape: one 8-hex code after each embedded file, joined with hyphens into one word, and `32-04` compares it exactly.

##### Cycle 1 fixes
- **L1 (null verdict) — FIXED.** `32-01-PLAN.md` Task 1 `check`: "a record whose `verdict` is null (failed attempts only) is skipped for validation and for the summary line ... only a round where no record holds a verdict is `not judged`". The artifacts section repeats it.
- **M2 (80.0 and 79.9 fixtures) — FIXED.** `32-01-PLAN.md` Task 2 behavior "Validator" gives the two `make_verdict` calls (maxima 125 each, D1 and D2 drops, totals 800 and 799, findings F1 and F2). Task 1 step 2 makes `make_verdict` assert every score stays >= 0 and number findings in dimension order. Arithmetic checked against `grade_of` at `check_verdicts.py:37-38` and the percent formula at `check_verdicts.py:65-66`.
- **L5 (probe reads only the end) — FIXED.** `32-01-PLAN.md` Task 2 step 1: one code per embedded block, `PROBE PART {n}: {code}` right after each END marker, answer `AIKIT-SENTINEL-` plus every code. The behavior line requires five codes for the five-file fixture and different codes on two builds. `32-04-PLAN.md` compares the token exactly, including a last-code-only answer and a reordered answer.

##### Concerns
- **MEDIUM — `check` raises on a bad record envelope.** See the first MEDIUM above. `32-01-PLAN.md` Task 1 `check`. The round number comes from `record["round"]` with no type check, and `validate_verdict` (`check_verdicts.py:43`) only checks the verdict's key set.
- **MEDIUM — a missing finding file is an exception, not a failed attempt.** See the second MEDIUM above. `32-01-PLAN.md` Task 2 step 2 versus the behavior line "a finding whose `file` is `../../outside.md` or does not exist".
- **MEDIUM — critical and high "highest counts" has two readings.** See the third MEDIUM above. `32-01-PLAN.md` Task 1 `check`. `32-07-PLAN.md` Task 1 says "the highest raw counts over the round's verdicts", which is the separate-max reading, but this plan is implemented first.
- **LOW — `finding_path_errors` is named in the artifacts list and used in Task 2, but Task 1 never says to create it.** `32-01-PLAN.md` artifacts `provides` lists `finding_path_errors`; Task 1 step 1 does not. A Task-1-only commit would not have the function Task 2 calls. Say "add the function in Task 2" in the Task 1 list, or move the name.
- **LOW — `check` with an empty `--skills` list prints nothing and exits 0.** `32-01-PLAN.md` Task 1 `main`: `--skills` is `nargs='*'`, and `check` iterates `opts.skills`. The tracer always passes one skill, so this passes. SPEC R5's "a skill with no tracked files is an error naming it" is not reachable from `check` until 32-07. Acceptable for an interim checker if the plan says the empty list is not a gate.
- **LOW — `parse_status_line` is copied as-is, and a status line with a value containing spaces splits wrong.** `check_verdicts.py:30-34` splits on whitespace. The fixture status lines have no spaces in values, so the tests pass. Not a new gap.

##### Suggestions
- In `check`, read the round number from the `r<N>` folder name, and treat a record that is not a dict or lacks `verdict`, `judge`, `rubric_version` or `spec_sha` as the problem `<skill> r<N>: record is not a verdict record`.
- In `finding_path_errors`, resolve and confine first; if the path is not a file, return that as the error and do not open it.
- Replace "the highest counts" with "the maximum critical count and the maximum high count, each taken over the verdict-bearing records".

##### Risk Assessment
**MEDIUM.** The happy path, the digest, the pin and the two boundary percents are specified and check out against the phase 27 checker. The remaining risk is records and finding paths the tracer does not build: those hit the push hook later, and an exception there fails the hook with a traceback instead of a named problem.

##### Ponytail findings
- **Needed.** SPEC R2, R5 (digest and validator) and R6 (attempts), plus D-01, D-02, D-10, D-13, D-14, D-15. Not a half feature.
- **Not over-built.** One module, three subcommands, the other three deferred to 32-04 and 32-07. `CheckOptions` is a NamedTuple the later plan extends, which the CONTEXT decision already requires.
- **Reuse.** `validate_verdict`, `grade_of` and `parse_status_line` from `check_verdicts.py:30-79`. `_load_mapper` from `tools/run_unittest_parallel.py:587-595`. `covering_modules` and `build_index` from `tools/staged_mapper.py:86` and `:218`. `SKILLS_ROOTS` and `skills_roots` from `jev_ladder.py:35-41` and `:101-109`. The temp-repo helper pattern from `tests/test_staged_mapper.py` (the plan cites the right helper).
- **Reach.** New module joins the generated listings through `gen_test_groups.py` in the same commit. `LOOKUP_COPIES` is the one arch caller. README row and the agent frontmatter are in Task 3. No caller of a function that does not exist yet.
- **LOW — rule 6 (attribution) is not in SPEC R2 or D-13.** `32-01-PLAN.md` Task 1, prompt rule 6. It changes what the judge scores and no test asserts it. Either cite the decision that requires it or drop it; a judge instruction nobody asked for is scope.

#### 32-02

The citation guard and the stray-module guard are both small, both tested on fixtures, and both match the code they extend. The live ROADMAP already has the `JDG-04` citations the guard requires, and the scan window stops at `## Progress`, so the backlog is outside it. No confirmed cycle-1 finding named this plan. No new defect from the revision.

##### Strengths
- The scan window is right. `## Phase Details` is at `.planning/ROADMAP.md:147` and the next `## ` heading is `## Progress` at `:886`; `## Backlog` is at `:930`, past it. `_PHASE_HEAD` (`^### Phase (\d+(?:\.\d+)*):`) matches `### Phase 32.1: Batch 1, general small skills` (`:428`).
- The criteria span is right on the live file. Every phase block uses `**Success Criteria** (what must be TRUE):` (`:435`, `:450`, and the rest of the 74 hits) and ends at `**Plans**`. `JDG-04` as a whole token, with the lookaround the plan gives, rejects `JDG-040` and `jdg-04`.
- Phase ordering matches the decision. `tuple(int(part) for part in number.split(".")) > (32,)` keeps 32.1 and drops 32 and 31.1, which is what the behavior lines require.
- `check_jdg04_citations` returns `(problems, notes)` and `main()` composes it the way `check_edge_floors` is composed (`tools/check_dogfood.py:529-530`). The fixture helper copies `TestEdgeFloors._root` (`tests/test_check_dogfood.py:518-531`).
- `stray_test_modules` uses `fnmatch.fnmatchcase` against `test_*.py`, the same case-sensitive pattern `discover_modules` globs (`tools/run_unittest_parallel.py:246-248`). It skips `tests/` itself and `__pycache__`, so the seven-file fixture returns exactly the two nested `test_*.py` paths. The non-vacuity class already exists (`tests/test_gate_scope.py:633`).

##### Cycle 1 fixes
none for this plan. A6, A7, A8 and A9 were refuted in cycle 1, and the revised plan records that. Rechecked: the scan still stops at the next `## ` heading, which on the live file is `## Progress` (`ROADMAP.md:886`), and the marker `**Success Criteria**` occurs in every phase block. No new evidence against those refutations.

##### Concerns
- **LOW — `_criteria` stops at the first `**Plans**`, and the plan does not say "first".** `32-02-PLAN.md` Task 1 step 1. On the live ROADMAP every block has exactly one (`ROADMAP.md:442` and the other `**Plans**` hits), so the tree passes. A fixture that put `**Plans**` inside a criterion before the real heading would hide a later `JDG-04`. The behavior tests never do that. Say "the first `**Plans**`".
- **LOW — a phase heading with a trailing space before the colon is skipped.** `_PHASE_HEAD` requires `:` immediately after the number. The live headings have no space (`ROADMAP.md:428`). A fixture written with `### Phase 33 :` would not be flagged. The plan's own fixtures use `### Phase 33:`, so the tests pass. Worth one sentence so the executor anchors the regex as written.

##### Suggestions
- State that `_criteria` ends at the first `**Plans**` line, and that a block with no such line runs to the block end (the plan already says "or the block end").

##### Risk Assessment
**LOW.** Both guards are read-only, the live file matches the regexes, and `make check-dogfood` on the tree is the verify step. The fixture tests cover the boundary the SPEC lists (32 versus 32.1, `JDG-040`, citation outside the criteria, backlog excluded, empty tree, nested `test_*.py` named, a `.py.txt` not named).

##### Ponytail findings
- **Needed.** SPEC R1 and R10, D-16 and D-21. D-22 is already committed; this plan only guards it.
- **Not over-built.** Two functions and one walk. No new module, so no listing regeneration.
- **Reuse.** `check_edge_floors` composition at `tools/check_dogfood.py:529-530`. `TestEdgeFloors._root` at `tests/test_check_dogfood.py:519`. `TestGateScopeNonVacuity` at `tests/test_gate_scope.py:633`. `discover_modules`' glob at `tools/run_unittest_parallel.py:248`.
- **Reach.** `main()` is the only caller, and the plan adds the call. Docs are deferred to 32-07, which the plan says explicitly. No missed caller.

##### Same-wave overlap
None. 32-01 and 32-02 share no file, and 32-02 does not regenerate `Makefile` or `.pre-commit-config.yaml`. Neither plan's `depends_on` is missing a same-wave predecessor.

Skipped: did not run the suites or simulate the regex over the whole ROADMAP (read-only review). Risk: a phase block whose success criteria use a marker other than `**Success Criteria**` would be flagged; every current block uses that marker.

### Batch B (32-03, 32-05)

#### 32-03

The plan implements SPEC R9’s main-flow half and the AGENTS.md sentences from R6 and R9. The cited lines still match the tree, the planned edits cover the current history hits, and the tests that pin those phrases are either updated or unaffected. One planned Evidence bullet fails the version rule the same task defines, so Task 2’s tree test cannot pass as written.

##### Strengths

- The history scan is exact. The current SKILL.md hits are cross-ai line 91, curated-config lines 329 and 334, spec-config lines 221 and 314, spec-review line 164, spec-discuss line 206, review-checklist line 199, and jev line 62.
- `confirmed live` is narrowed to a colon or date, so spec-config line 194 remains a coverage statement. The fence rule matches SPEC R9: dates fail inside fences, versions do not.
- The new module is generated into the listings, and 32-03 is the only wave-2 plan that edits `Makefile` and `.pre-commit-config.yaml`. 32-04 edits only `tools/judge_loop.py` and `tests/test_judge_loop.py`.
- The doc pins reuse `_flat`, `_missing_clauses`, and `_design_bullet` from `tests/test_rules_docs.py:36-143`. The three sentences stay inside the existing bullet at `AGENTS.md:55-60`, and 32-07 later edits different AGENTS.md bullets.

##### Cycle 1 fixes

none for this plan

##### Concerns

- **MEDIUM — the cursor Evidence bullet fails the version rule this task adds.** At `.planning/phases/32-re-judge-baseline/32-03-PLAN.md:170`, the plan appends `- The cursor-host validation ran from a cursor-agent 2026.10.14-941492e session.` `cursor-agent` is in `VERSION_TOOLS`, and that sentence has no constraint word. Simulating the planned `version_hits` returns `cursor-agent 2026.10.14`. The Evidence section is still main flow because Task 1 appends it after `## Subcommand reference` (line 340), `## NEVER` (line 353), `## Common mistakes` (line 380), and `## Reporting rule` (line 394). Task 2’s tree assertion therefore fails. Put the build string in backticks, or append Evidence only after the last section.

- **LOW — the main-flow rule misses the same shape of history in references.** `skills/jev-fast-decision/reference.md:110-117` contains `## What Jev 1.14 changed (as of 2026-10-15)` and `## Capability matrix (as of 2026-10-18)`. This matches D-18’s split and was the basis of refuted B5, so it is not re-raised as a defect. It remains a real gap against JDG-05’s “no dates in the main flow” wording.

##### Suggestions

- Change the cursor bullet to `` `cursor-agent 2026.10.14-941492e` ``, or move the final Evidence append to the real end of the file.
- State explicitly that Task 1’s Evidence section is temporary and Task 2’s tree test is the first full-rule check.

##### Risk Assessment

**MEDIUM.** The implementation is otherwise executable, but Task 2 fails its own acceptance test until the Evidence bullet or heading placement changes.

##### Ponytail findings

- Needed: SPEC R9 and R6, D-18, D-19, and D-20. No extra abstraction.
- Reuse is correct: the clause-pin helpers and `tools/gen_test_groups.py`.
- The version scanner is the minimum new logic the rule needs. The failing Evidence bullet is a completeness miss, not over-engineering.
- Callers reached: the pinned tests for the edited phrases are updated or do not assert them. `test_node_floor` at `tests/test_ai_kit_spec_runtimes_table.py:888` reads spec-review, not execute-superpowers.

#### 32-05

The pointer half is accurate and executable. Its regexes hit exactly the listed planning artifacts, preserve the required generic paths and placeholders, and update the two curated-config tests that would otherwise break. It adds no test module and shares no file with wave-3 plans 32-06 or 32-07.

##### Strengths

- The pointer inventory matches the tree: curated-config lines 333, 334, and 338; spec-config line 332; usage-metrics lines 43 and 313; the named spec-discuss reference lines; `backends/laya.md:57`; and `backends/typesafe.md:18`.
- The patterns reject `18.1-one-runtime-model/`, `21-SMOKE-CURSOR.md`, `999.2`, `(D-07)`, `20 D-11`, and `router-env/`, while accepting `.planning/config.json`, `.planning/phases/<phase>/`, `NN-SPEC.md`, `D-<n>`, `NN D-xx`, `JDG-04`, and URL-contained ids.
- The bold exception is concrete: the two characters before `D-14` at `references/log-formats.md:38` are `**`, and `:` follows it. `D-01..D-06` is deliberately replaced rather than exempted.
- `tests/test_curated_config_apply.py:2608-2635` is the only test pinning the removed phase-file names, and the plan updates both assertions. The spec-discuss and usage-metrics tests do not pin the removed strings.

##### Cycle 1 fixes

none for this plan

##### Concerns

- **LOW — the bold-example exemption is narrower than the SPEC’s example.** At `.planning/phases/32-re-judge-baseline/32-05-PLAN.md:101`, exemption requires the two preceding characters to be exactly `**` and the next character to be `:`. The current example qualifies, but `**D-14 : …**` or a line-broken marker would fail. This is an executor-safe rule, just stricter than the prose example.

- **LOW — one reference date sample remains unchecked by design.** `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:91` contains `2026-09-02-ai-kit-model-discovery-config.md`. It is not a numbered phase file, and D-18 keeps date rules off references. This restates the accepted scope boundary; it does not contradict the refutation of B5.

##### Suggestions

- No change is required before execution. If the bold exemption should match the SPEC literally, define it as a Markdown bold span beginning with `D-<digits>:` rather than a two-character lookbehind.

##### Risk Assessment

**LOW.** The edits are literal, the regex behavior was checked against the current files, and the known dependent tests are in the plan.

##### Ponytail findings

- Needed: SPEC R9’s pointer amendment, D-18, and D-19. No new module, option, or wrapper.
- It correctly extends 32-03’s `history_hits` instead of creating a second checker, and its `depends_on: [32-03]` covers the file it reads.
- The test, fixture, and generated-listing surface is complete: no new `tests/test_*.py`, no listing regeneration, and the curated-config pins move in the same commit.

Skipped: no tests or make targets were run; regex behavior was checked with read-only Python. The remaining risk is the cursor Evidence bullet in 32-03, which fails its own version rule.

### Batch C (32-04, 32-07)

#### 32-04

`pool` and `count` are specified tightly enough for a haiku executor, and the cycle-1 fixes land. One new contract bug remains: `ask_jev` runs `jev_review.py ladder` with a payload that command never answers, so the advisory jev step (SPEC R4 / D-05) cannot raise a count on a real run.

**Strengths**
- Probe usability is an exact, ordered check (`token` / `lane.out` / `lane.err`, then `lane_ok`, then stripped equality) and matches 32-01's probe token (`32-01-PLAN.md:214`).
- `choose_pool` covers two, one, none and an empty list, refuses a native id that is also a judge, and writes substitutes into the loop file 32-08 reads (`32-08-PLAN.md:65`).
- The band test uses integer tenths (`abs(round(percent * 10) - 800) <= 70`), so 73.0 and 87.0 cannot drift on float comparison.
- The jev item is pinned byte-for-byte, and `json.dumps(item)` is asserted to contain neither a path nor the skill name (T-32-08).
- `numstat` rejects a base that is not 7-40 hex before any git call, and an unresolvable commit stays one judge with a recorded reason (`32-RESEARCH.md:66`).

##### Cycle 1 fixes
- **L2 — FIXED.** `load_inputs` rejects a name in both maps (`32-04-PLAN.md:22`, `:160`); `count` iterates `inputs["skills"]` only and refuses an unknown `--skill` (`32-04-PLAN.md:153-154`).
- **L3, 32-04 part — FIXED.** The `jev` record contract is explicit: `asked`, `item`, `level` (int or null), and `note` stored without the `: asks for two` / `: keeps one` suffix, with a `final_count` round-trip (`32-04-PLAN.md:23`, `:151`, `:170`).
- **L5, 32-04 part — FIXED.** `probe_result` compares the whole `token` file, and TestPool covers a last-code-only and a reordered answer (`32-04-PLAN.md:21`, `:109`, `:117`).

**Concerns**
- **HIGH — `ask_jev` calls a command that never returns the shape `jev_level` reads.** `32-04-PLAN.md:166` runs `python3 -B <client> ladder` with stdin `{"items": [item]}` and no `reviewed_head`. `jev_review.py:2051-2055` hands `ladder` to `jev_ladder.main`, which parses stdin and then calls `run_ladder` (`jev_ladder.py:629-639`). `run_ladder` does not answer the item. It looks up another client and calls that client with `{"reviewed_head": ..., "items": valid}` (`jev_ladder.py:559-569`, `:562`). The item's answer is produced by the screen path, which is the command with no subcommand (`jev_review.py:2047-2061`), and that path requires `{"reviewed_head", "items"}` (`jev_review.py:346-350`) plus `GSD_PATH_JEV=1` and a positive timeout (`jev_review.py:1992-1998`). The plan's payload fails that check, and the env it sets is stripped by `child_env` before the inner call anyway (`jev_ladder.py:411-424`). The TestCount fake stands in for the whole program, so the tests pass while a real `count` records `jev unavailable` or `own_reasoning` and keeps one. That leaves SPEC R4's "unless jev's score asks for two" dead for the only two skills that reach it (`32-RESEARCH.md:233`). The research row that this plan cites describes the screen's answer fields, not the `ladder` output (`32-RESEARCH.md:272`).
- **MEDIUM — `count_skill` is specified as one function that will not pass pylint as written.** It must branch on deterministic two, `--no-jev`, missing `judged_at`, missing `numstat`, the `ask` call, three exception classes and `jev_level`, then build the `jev` dict (`32-04-PLAN.md:170`). pylint's limits are 5 args, 12 branches and 50 statements (`pyproject.toml:74-79`), and the plan's own pylint step is only in 32-07 (`32-07-PLAN.md:206`). 32-04's verify runs the unit tests and pyright, not pylint (`32-04-PLAN.md:177-179`), so the split lands on the next plan's executor.
- **LOW — the CLI test's canned client is under-specified.** `32-04-PLAN.md:153` says a temp script "printing a canned ladder JSON", but does not give that JSON. A haiku executor has to invent a valid `run_ladder` document. The direct `ask` tests pin the shape; this one does not.
- **LOW — `percent_words(88.0)` says "just outside" while the same number is 8.0 points from 80, outside the 7.0 trigger band and also outside the `d <= 100` tenth-band (which ends at 90.0).** The text is internally consistent with the stated cuts (`32-04-PLAN.md:146`, `:162`), and D-05 leaves the wording to discretion. The phrase still overstates the distance. Not re-raised as C5.

**Suggestions**
- Make `ask_jev` call `jev_review.py` with no subcommand (the screen), stdin `{"reviewed_head": "<40-hex HEAD or 40 zeros>", "items": [item]}`, and keep `GSD_PATH_JEV=1` plus the timeout. Read `status`, `answers["judge-count"].level`, `needs_fallback` and `model` from that response (`32-RESEARCH.md:272`). Keep the fake tests on the same shape.
- Split `count_skill` in the plan the way 32-07 already splits `check`: one function for the "why jev was not asked" note, one for the call.
- Paste the canned ladder JSON into the CLI behavior line.

**Risk Assessment: MEDIUM.** The pool rule and the deterministic count are sound and tested. The one path that can change a real baseline (jev raising 88.0 and 88.8) is wired to the wrong command, and the unit tests cannot see it.

##### Ponytail findings
- Needed: yes. SPEC R3 and R4, D-05 and D-08. No extra options beyond the locked `--no-jev` and `--client`.
- Reuse is right: `lane_ok`, `parse_status_line`, `skills_roots`, `atomic_write_json` and `JEV_ENTRY_REL` come from 32-01 rather than new copies (`32-01-PLAN.md:146`, `:170`).
- The jev call should reuse the screen entry the research already verified (`jev_review.py:2047-2061`), not a second invocation of the ladder. **HIGH**, same as the concern above.
- `count_skill` as one function fights the repo's pylint limits. **MEDIUM.**
- Callers reached: 32-07 consumes `final_count`, `deterministic_count`, `load_inputs` and the `jev` contract; 32-08 consumes `pool` and `count`. No listing or doc change belongs in this plan.

#### 32-07

The report and the full checker cover SPEC R5, R6 and R7, and the cycle-1 fixture and tracer fixes are real. Two new seams can make a correct records folder fail `check`, and one of them is already contradicted by 32-01's checker.

**Strengths**
- `render_report` is a pure function of the records: no git, no clock, no absolute path, and `check` compares the committed file byte for byte (`32-07-PLAN.md:21`, `:144`).
- The fixture arithmetic holds. Default maxima 20+7×15 = 125: drops `(20,"high")+(5,"medium")` give 100/125 = 80.0 B; `(20,"high")+(7,"medium")` give 98/125 = 78.4 C; `(20,"medium")` gives 105/125 = 84.0 B. `BIG` (125 each, total 1000): `(125,"high")+(76,"medium")` gives 799/1000 = 79.9 C; `(100,"medium")` gives 900/1000 = 90.0 A. All scores stay non-negative and every below-max dimension has one finding, matching `make_verdict` (`32-01-PLAN.md:178`, `:209`).
- Bar clauses match the SPEC edges: 80.0 with a high is `met: grade B or better`; 79.9 with a high is `not met`; a complete refutation flips it; a missing command or output does not (`32-07-PLAN.md:115`, `:165`).
- `check_judge_records` follows `check_edge_floors`: injected loader, `(problems, notes)`, missing folder is a note, and `main()` composes it after the JDG-04 lines (`tools/check_dogfood.py:478-530`).
- Same-wave file check is clean. 32-05 edits skill text; 32-06 edits the frontmatter tests, runner and listings. 32-07 is the only wave-3 editor of `AGENTS.md`, `README.md` and `tools/check_dogfood.py`. `depends_on: [32-04, 32-02, 32-03]` names the plans whose output it reads. 32-03's three AGENTS.md sentences do not overlap the Testing and Commands lines 32-07 edits (`32-03-PLAN.md:191`, `AGENTS.md:226-230`, `:358`).

##### Cycle 1 fixes
- **M1 — FIXED.** `TestTracer` gains `inputs.json`, `loops/32.json` (`pool` plus `counts` from `count_skill`, equal to `deterministic_count(None)`) and a `report` run before each `check` (`32-07-PLAN.md:119`). `render_report` raises `JudgeLoopError` naming the skill, and `check` reports `REJUDGE.md not checked: ...` (`32-07-PLAN.md:117-118`, `:136`).
- **M2, 32-07 part — FIXED.** Every boundary verdict has an exact `make_verdict` call with maxima and drops (`32-07-PLAN.md:93`, `:114-116`, `:165-166`). The 90.0 judge is reworded to "90.0 with no critical or high finding" on maxima of 125 each.
- **M3 — FIXED.** TestCheck states `demo-c: not judged (no verdict in loop 32 round 1)`, no per-skill line, exit 1 in default mode, and exit 0 once a verdict exists (`32-07-PLAN.md:169`). 32-09's stop sentence names `not judged` (`32-09-PLAN.md:92`).
- **L3, 32-07 part — FIXED.** The count round-trip writes a real `count_skill` result with a level-2 fake and expects `check` to accept it (`32-07-PLAN.md:168`).

**Concerns**
- **HIGH — `check` fails a correct records folder because its judge list and 32-08's pool disagree.** With no `--judges`, `_default_judges` accepts `pool.judges` plus `pool.native` (`32-07-PLAN.md:162`, `:180`). 32-08 builds the pool from the configured list and then, for a failed lane, creates a new lane judged by `NATIVE` and records it with `--replaces` (`32-08-PLAN.md:141-142`). When two configured judges were usable, `choose_pool` puts neither native into `members` and records no substitute (`32-04-PLAN.md:116`), so native is absent from `pool.judges` and `pool.native` is the only native id. The plan says "every loop's `pool.judges` plus `pool.native`" (`32-07-PLAN.md:162`). Read as the pool's own fields, a native substitute verdict is `judge native:... is not in the judge list` and `check` exits 1. 32-09 runs exactly that default-shaped check (`32-09-PLAN.md:92`). The plan must say the accepted list is the union of `pool.members`, `pool.judges` and `pool.native`.
- **MEDIUM — the "not judged" rewrite contradicts the checker 32-01 already ships.** 32-01's `check` skips a null verdict and emits `f"{skill}: not judged (no verdict in loop {loop} round {n})"` with no summary line (`32-01-PLAN.md:176`). 32-07 Task 1 adds `; bar <clause>` and, for `demo-c`, requires the report cell `not judged` while its `check` behavior still expects exit 0 and a per-skill line for `demo-a` (`32-07-PLAN.md:119`). Task 2 then says a last round with no verdict gives the problem and no per-skill line (`32-07-PLAN.md:183`). Task 1's TestReport `check` invocation passes `--skills demo-a` only (`32-07-PLAN.md:119`), so it does not exercise `demo-c`. An executor that follows Task 1's "add the bar clause" literally keeps 32-01's exit 1, and Task 1's verify fails. The plan should say Task 1 preserves 32-01's existing problem and only Task 2's test asserts it.
- **MEDIUM — `worst_record`'s tie key is not computable as written.** It minimizes `(judge_bar(...)[0], round(percent * 10), position of the judge in order)` (`32-07-PLAN.md:135`) but never says what `order` is. The Verdicts section later orders by `pool.members`, then `pool.judges`, then `pool.native`, then the judge string (`32-07-PLAN.md:138`). Two verdicts at the same percent and the same bar rank therefore have no defined winner, and the report's grade, digest and bar clause follow that winner. Name the same order in `worst_record`.
- **LOW — `render_report` is one function the lint limits cannot hold.** The layout is about ten sections (`32-07-PLAN.md:136-141`). pylint allows 50 statements and 15 locals (`pyproject.toml:76-79`), and `too-many-lines` is disabled but `max-statements` is not (`pyproject.toml:82-83`). Task 2's verify runs pylint (`32-07-PLAN.md:203`) after Task 1 committed the function. The plan should require one function per section from the start.
- **LOW — three report fields are named but not given their cell text.** "why that many ran" is specified (`<count>: <reasons>`); the judge-count inputs and the per-skill reasons inside the judged row are not pinned beyond the column list (`32-07-PLAN.md:21`, `:139`). A haiku executor can fill them from the count record, but two implementations will not match byte for byte. Pin one fixture line of `## Judge count inputs`.
- **LOW — `check_judge_records` loads the tool by a path-derived module name.** The plan copies `_script`'s `spec_from_file_location` (`32-07-PLAN.md:218`) but `_script` inserts a package path and imports by name (`tools/check_dogfood.py:54-58`). The test-loading pattern it should copy is 32-01's: register the module in `sys.modules` before `exec_module` (`32-01-PLAN.md:178`). As written, a dataclass or string-annotation lookup of `judge_loop` during import can fail only on the live `make check-dogfood` run.

**Suggestions**
- Define the default judge list as the sorted-unique union of `pool.members`, `pool.judges` and `pool.native`, and add a TestCheck case whose verdict judge is `pool.native` while `pool.members` is the two configured ids.
- In Task 1's action, say "keep 32-01's not-judged problem and skipped summary line; do not invent a second one."
- Pass `worst_record` the same judge order the Verdicts table uses, and split `render_report` into one pure function per section before Task 1's commit.
- Pin one full `## Judge count inputs` row in the behavior block.
- Load the tool the way `tests/test_judge_loop.py` loads it (`32-01-PLAN.md:178`).

**Risk Assessment: MEDIUM.** The bar math, refutations, round cap and byte compare are right and well tested. The default judge list omits the native substitute 32-08 actually records, so the first real `check` of a two-judge pool with one failed lane fails a correct report.

##### Ponytail findings
- Needed: yes. SPEC R5, R6, R7, D-03, D-04, D-06, D-07 and D-12. No new option beyond the locked `--gate` and `--require-current`.
- Reuse is right: `validate_verdict`, `skill_digest`, `record_path`, `judge_slug`, `load_inputs`, `deterministic_count` and `final_count` are extended, not rewritten (`32-07-PLAN.md:88`).
- `render_report` as a single function, and a default judge list that ignores `pool.members`, are the two places new code does less than the records already express. **MEDIUM** and **HIGH** respectively.
- The plan reaches the checker, its tests, check-dogfood, AGENTS.md and README. It correctly does not touch `Makefile` or `.pre-commit-config.yaml` (no new module). 32-09's publish and stop sentence match the problems this plan defines (`32-09-PLAN.md:92`).

Skipped: did not run the suites or import `judge_loop` (read-only review; the tool does not exist until 32-01). Did not re-check the seven refuted cycle-1 items; no new evidence contradicts them.

### Batch D (32-08, 32-09)

#### 32-08

The baseline run plan is a careful, executable script of the judge run: it freezes the tree, probes the configured judges with the hardened sentinel, records one or two judges per skill, and keeps every external lane inside the cross-AI runner's own retry rules. The cycle-1 fixes landed. The new problems are a wait budget that can never cover the probe it bounds, a pool-file shape the launcher reads a field that does not exist in, and a worker that treats the runner's own hard-tier stop as a reason to retry.

##### Cycle 1 fixes

- **L4 — FIXED.** Task 1's `effort-env` records all three variables the research names, prints set or unset only, and the acceptance expects exactly three lines (`.planning/phases/32-re-judge-baseline/32-08-PLAN.md:97`, `:123`).
- **L5 — FIXED.** The run-directive-5 truth says the probe carries a code after each embedded file's END marker and `pool` accepts only the exact one-word answer in the `token` file, with no second check in the run scripts (`32-08-PLAN.md:20`). That matches 32-01's `build_probe` and 32-04's `probe_result`.

##### Concerns

- **HIGH — the probe wait can never report `probes ended`.** Task 1 step 3 repeats `wait --what probes --max-seconds 170` "until it prints `probes ended` (at most about 11 minutes)" (`32-08-PLAN.md:112`). The `--max-seconds` budget is consumed by `run-with-timeout 660` plus the lane itself, not by wall-clock sleep: `wait` polls every 15 s and exits 3 when N seconds pass (`32-08-PLAN.md:102`), and the runner's own `--outer-timeout 600` is the pass condition (`32-RESEARCH.md:120`). A probe that takes its full budget returns after about 660 s, and the eleventh 170 s call lands at about 1,870 s — past it. The verify then demands `probes ended` within 5 s (`32-08-PLAN.md:115-116`). This is the D4 concern with a new, concrete bound the revision added; the earlier refutation ("repeats until ended, each probe bounded at 660 s") does not cover the "at most 11 minutes" cap.

- **HIGH — `launch` reads `pool.members` entries as judge ids, but the pool file stores objects.** `choose_pool` returns `{"judges", "native", "probes", "members", "substitutes"}` (`32-04-PLAN.md:122`) and `probe_result` returns `{"judge", "usable", "status_line", "reason"}` (`32-04-PLAN.md:121`). Task 2's `launch` iterates "each external judge in `members`" and spawns `work <judge>` (`32-08-PLAN.md:137`), while `work ID` looks that string up in `judges.json` for `cli` and `model` (`32-08-PLAN.md:138`). Nothing says `members` holds bare id strings rather than the probe dicts. A haiku executor that follows the 32-04 shape literally builds a worker it cannot map back to a runtime.

- **MEDIUM — the hard-tier wait is re-implemented, and the runner's own stop is misread as retryable.** The worker treats any `exit=75` carrying `retry_after_s=` as "sleep exactly that long and run the same lane again" (`32-08-PLAN.md:138`). The skill says one such wait per line, and the runner itself ends the episode with `stopped=hard-waits` or `stopped=cap` and exit 69 (`skills/ai-kit-cross-ai/SKILL.md:137-149`). The worker only stops on exit 69, a bare 75, 2 or 127 (`32-08-PLAN.md:138`). A line that still says `exit=75 retry_after_s=600` after the runner has already counted its cycle — the runner prints that line and then the stop (`SKILL.md:134`, `:148`) — sends the worker into another 600 s sleep and another full lane. D2's refutation assumed the runner's exit 69 arrives first; the plan never says to read `stopped=` before `retry_after_s=`.

- **MEDIUM — `count` is invoked with jev on, against commits the plan does not show are reachable.** Task 1 step 3 runs `count` with no `--no-jev` (`32-08-PLAN.md:112`), and the inputs name base commits `3410359`, `76fa531`, `d2855bc`, `16153d6` (`32-08-PLAN.md:109`). 32-04 records `jev input absent: base commit … not found` when `rev-parse --verify` fails (`32-04-PLAN.md:166`, `:171`), so the count still completes, but the two skills that reach the jev step (`ai-kit-gsd-spec-discuss` 88.0, `ai-kit-spec-goal-prompt` 88.8, per CONTEXT D-05) get no jev judgment whenever those short shas are only on archive tags. D9 was refuted because the *committed* record reproduces; it does not say the baseline run itself gets the jev answer. The plan should state the expected note when the base is absent, so the executor does not treat it as a failure and retry.

- **LOW — the frozen-tree window and the scope check disagree about what "this run" is.** `scope.py start` snapshots `/proc` (`29-01-PLAN.md:103`) and `close` flags any new process whose cwd is the checkout (`29-01-PLAN.md:105`). The plan says the workers have exited before `close` (`32-08-PLAN.md:207`), which is true only if Task 3 reached `all lanes ended`. A checkpoint resume that runs `close` while a detached `work` child is still alive — its cwd is `ROOT` (`32-08-PLAN.md:96`) — fails the plan for a process the plan itself started. Worth one sentence naming that `close` runs only after `status` says no worker is alive.

##### Suggestions

- Drop the "at most 11 minutes" sentence and bound the probe wait by the runner: repeat the 170 s wait until `probes ended` or until `run-with-timeout` has returned, and say which status line ends a probe that never wrote `done`.
- State the `members` element type in Task 2: "each entry of `pool.members` is the judge id string `pool` printed", or, if 32-04 stores the probe dict, "`member['judge']`".
- In `work`, stop the judge when the status line carries `stopped=hard-waits` or `stopped=cap`, and only sleep on `retry_after_s` when the same line does not.
- Name the four base shas' reachability: if `git rev-parse --verify` fails, the recorded note `jev input absent` is the expected result, not a stop.

##### Risk Assessment

MEDIUM. The run is well fenced (review mode, `AI_KIT_REFUSE_REAL_HOME=1`, outputs under `tmp/`, HEAD checked at the end), but the probe-wait cap and the ambiguous pool shape can stall the run before a single verdict is recorded, and both are decisions a haiku executor would have to make alone.

##### Ponytail findings

- **MEDIUM — the lane worker re-implements the cross-AI skill.** `work`'s exit table (`32-08-PLAN.md:138`) duplicates `skills/ai-kit-cross-ai/SKILL.md:111-170`, including the hard-tier wait the runner already counts. D-08 requires the run to follow that skill, so the worker should call the runner and trust its `stopped=` line rather than re-deciding the ladder. The rest of the plan earns its size: the frozen tree, the sentinel probe and the recorded substitutes are SPEC R3, R4 and R7, and no existing tool launches a judge lane.

#### 32-09

Publishing the staging records unchanged, generating the report and refusing to hand-edit either one is the right shape for SPEC R7, and the one confirmed cycle-1 item for this plan is fixed. The audit the plan adds cannot pass against the report layout 32-07 actually generates, so Task 2 fails on a green run.

##### Cycle 1 fixes

- **M3 — FIXED.** Task 1 step 3 names a skill reported `not judged` as a stop-and-report case beside a stale digest and a mismatch (`32-09-PLAN.md:92`), and the verify fails on a `judge-loop:` line holding `not judged` (`32-09-PLAN.md:98`). The exit-1 behaviour itself is pinned in 32-07's TestCheck (`32-07-PLAN.md:181`).

##### Concerns

- **HIGH — `audit.py` checks columns the report does not have.** Task 2 checks "every `## Verdicts` row whose Score is not `not judged`" for a non-empty Judge and Lane status, and "every `## Verdicts` row whose Substitute is not `-`" for the text `replaces <judge>: <reason>` (`32-09-PLAN.md:114`). 32-07's `## Verdicts` table is `| Skill | Loop | Round | Judge | Lane status | Substitute | Score | Percent | Grade | Critical | High |` (`32-07-PLAN.md:145`), so those columns exist — but `render_report` writes `Substitute = replaces <judge>: <reason> or -` and `Lane status = the last attempt's status_line, else its note` (`32-07-PLAN.md:145`). The audit's check is therefore only as good as its row parser, which the plan never specifies. A parser that splits on `|` and takes cells by the header works; one that matches the literal `replaces` anywhere in the row also matches the `## Judge pool` section's `Substitutes:` line (`32-07-PLAN.md:147`). The plan gives the executor neither the column indexes nor the section boundary, so the audit can pass while reading the wrong table or fail while reading the right one.

- **MEDIUM — the old-score check compares the wrong strings.** Task 2 fails when any `old_score.value` string of `inputs.json` occurs in `## Judged skills` (`32-09-PLAN.md:114`). The values 32-08 copies verbatim from the inventory include `old 102/120 (85.0%) PASS, 2026-10-25, phase 25.1` (`15-skills-vs-new-judge.md:106`). 32-07 puts old scores only under `## History: last 120-point results` (`32-07-PLAN.md:126`), so the check passes today. It breaks the moment a judged skill's percent happens to be `85.0` or `88.3`, because the audit looks for the raw `value` substring with no section fence stated beyond the heading. The plan should say the scan stops at the next `##`.

- **LOW — `publish.py` refuses a destination that differs, but not one a rerun would clobber with equal bytes.** The copy refuses when a destination exists with different bytes (`32-09-PLAN.md:90`). A rerun after a partial copy of identical bytes succeeds and prints `published <n> files` again, hiding that the tree was already dirty. Harmless given the precondition, but the script should say `unchanged` for an equal existing file so the SUMMARY does not report a fresh publish.

##### Suggestions

- Give `audit.py` the header row and the cell indexes from 32-07 (`32-07-PLAN.md:145`): Judge is cell 4, Lane status cell 5, Substitute cell 6, Score cell 7, and the scan of each section ends at the next `##`.
- Compare old scores only inside `## Judged skills`, cut off before `## Verdicts`, and match the whole `value` string rather than a substring a new percent could collide with.
- Have `publish.py` print `unchanged <path>` for a byte-identical destination instead of counting it as published.

##### Risk Assessment

MEDIUM. The publish and the checker gate are sound and match D-06, D-07 and D-11, and `--gate` is correctly kept out of the baseline. The risk is Task 2: its audit is the only check that the committed report carries the SPEC R7 fields, and as written it parses a layout it does not pin down.

##### Ponytail findings

- **LOW — `audit.py` repeats the checker.** Row counts, judge names and the history separation are already enforced by `judge_loop.py check` (`32-07-PLAN.md:144-148`), which Task 1 runs with `--require-current`. The audit's only new content is the per-skill work-list line D-12 asks the SUMMARY to hold (`32-09-PLAN.md:115`). Keep that line; the six `ok/FAIL` checks duplicate the tool. D14 was judged not a defect, and this agrees — it is duplication, not a failure.

Same-wave overlap: none. 32-08 is alone in wave 4 and 32-09 alone in wave 5 (`32-08-PLAN.md` frontmatter, `32-09-PLAN.md` frontmatter); 32-09's `depends_on: [32-08]` names the plan whose scratch it reads, and neither plan edits a file the other touches.

Skipped: I did not run the plans or the test suite, and `tools/judge_loop.py` does not exist yet, so the pool, count and report shapes are taken from plans 32-01, 32-04 and 32-07 rather than from code. Risk: if 32-04's `choose_pool` actually stores bare id strings, the HIGH pool-shape finding drops to a wording gap.

### Batch E (32-06)

#### 32-06

##### Summary

Plan 32-06 is an executable GSD plan for SPEC R8 and D-17: a stdlib strict frontmatter gate, a PyYAML cross-check in `unit-uv`, and a one-time npm `yaml` comparison. The tree coverage, fixture list, and generated-listing steps match the source. Two instructions contradict the source or the YAML comparison they depend on, and a haiku executor would have to invent YAML behavior the plan does not pin.

##### Strengths

- The gate covers every installable entry through `setup.enumerate_entries` (`tools/setup.py:966-980`), which returns skills, agents, then commands. `entry_files` then maps a skill directory to `SKILL.md`. That matches `validate_entry` (`tools/setup.py:948-963`).
- It replaces exactly the two real-tree guards at `tests/test_setup.py:5524` and `:5538`, and keeps the installer reader tests. The research says `_read_frontmatter` is lossy and must not be reused for the strict gate (`32-RESEARCH.md:267`).
- The PyYAML module is placed in `UNIT_UV_MODULES` (`tools/run_unittest_parallel.py:93-94`). `gen_test_groups.py` regenerates both listings from `--list-groups` (`tools/gen_test_groups.py:25-35`), so the Makefile line the acceptance criterion greps is the line the generator writes.
- The fixture labels cover every SPEC R8 failure and the two designed-stricter cases from research Pitfall 3 (`32-RESEARCH.md:360`).
- Same-wave overlap is clean: 32-05 and 32-07 do not edit `Makefile`, `.pre-commit-config.yaml`, `tools/run_unittest_parallel.py`, or `tests/test_setup.py`. `depends_on: [32-03]` is correct because the history edits land before this gate runs.

##### Cycle 1 fixes

None for this plan. E1, E2, and E3 were refuted, and the revised text does not reopen them.

##### Concerns

- **HIGH — the `UNIT_UV_MODULES` edit breaks the test the plan says it preserves.** Task 2 step 3 writes `frozenset({"tests.test_framework_profiles", "tests.test_skill_frontmatter_pyyaml"})` (`32-06-PLAN.md:150`) and the read-first line says `sorted(UNIT_UV_MODULES)[0]` must stay `tests.test_framework_profiles` (`32-06-PLAN.md:139`). String order is the opposite: `tests.test_skill_frontmatter_pyyaml` sorts first. `tests/test_staged_mapper.py:552-564` then passes that first name to `_run_staged_modules` as a covering uv module. The Task 2 verify runs this test and requires `ok`, so the task cannot pass as written. Research already states the required order (`32-RESEARCH.md:462`).

- **HIGH — the fold rule disagrees with the parsers the comparison must match.** `parse_strict` joins every run of non-blank folded lines with a space and turns each blank line into one `\n` (`32-06-PLAN.md:114`). YAML 1.2 fold rule 6 keeps a blank line as a line break and does not put a space across it, so `>\n  a\n\n  b\n` is `a\nb\n`, not `a \nb\n`. No current skill description contains an internal blank line, so the tree test would still pass, but the plan gives this algorithm as the only definition and then requires the npm parser to agree. A haiku executor has to choose YAML behavior the plan got wrong.

- **MEDIUM — the npm script is told to import a Python module.** `yaml_compare.mjs` must “import `FIXTURES` and `DESIGNED_STRICTER` from `tests/test_skill_frontmatter.py`” (`32-06-PLAN.md:152`). Node cannot import that module. The preceding `dump_fixtures.py` already writes `fixtures.json`, so the script should read that file. As written, the executor has to redesign the comparison, and its non-zero exit fails the verify command.

- **MEDIUM — quoted scalars and block headers are under-specified against the tree.** The plan says a double-quoted value “must end with `"`” and then calls `json.loads`, and a block header must be exactly `[>|][-+]?` (`32-06-PLAN.md:114`). Every current block description is `>` or `>-` with equally indented lines (`skills/ai-kit-cross-ai/SKILL.md:3-11`, `skills/markdown-to-pdf/SKILL.md:3-11`), so the tree passes. It does not say whether the quotes in the match include the key’s separating space, or how a YAML escaped quote or trailing comment is handled. `json.loads` also rejects legal YAML forms such as a multiline quoted scalar, which the installer reader accepts (`tests/test_setup.py:5498`). The executor must invent those boundaries.

- **LOW — chomp and clip behavior is easy to mis-count.** “Drop trailing blank lines, then chomp” does not say whether the dropped lines are content-final blanks only, and `+` “adds one `\n` plus one per dropped blank line” can double-count the YAML clip newline. The acceptance fixture uses `>-` and `|` without internal blanks, so the stated tests do not catch it. Predates this revision’s ledger; the fold wording is part of the revised parser text.

##### Suggestions

- Put the new module second in the written set only if a comment records why, or change `tests/test_staged_mapper.py:553` in this plan to select a named module instead of `sorted(...)[0]`. The acceptance grep already expects `framework_profiles` first in the generated Makefile line.
- Replace the fold sentence with the YAML 1.2 rule: a blank line breaks the fold, and no space is inserted across that break. Add one fixture whose text has a blank line inside `>`.
- Point `yaml_compare.mjs` at `tmp/p32/06/fixtures.json` only. Keep the Python dump as the single reader of `FIXTURES`.
- Pin quote handling with one example each: `"say \"hi\""`, a single-quoted `''`, and a trailing-comment case. State that the quote check applies to the value after the `: ` separator.

##### Risk Assessment

**HIGH.** The plan implements the right requirement and its file ownership is sound, but Task 2’s verify command fails on the existing staged-mapper test, and the parser rule can make the required npm comparison fail or silently measure the wrong description length.

##### Ponytail findings

- The new parser is needed: SPEC R8 and D-17 require a strict subset, and `setup._read_frontmatter` (`tools/setup.py:908-939`) folds every shape and cannot reject the required errors.
- `entry_files` and `entry_problems` are small and justified. `UniqueKeyLoader` is the minimum way to make PyYAML reject duplicate keys; research shows plain `safe_load` keeps the last value (`32-RESEARCH.md:360`).
- No unused abstraction or option. The plan reuses `enumerate_entries`, `gen_test_groups.py`, and the existing `unit-uv` slot.
- It reaches the generated listings, the runner set, and the two old guards. It does not reach the sort assumption in `tests/test_staged_mapper.py:553`, which its own edit changes.
- Severity: **HIGH** for that missed caller. The rest is the smallest complete version of R8.

Skipped: I did not run the test suite or the npm probe, per the read-only review limit. The fold mismatch is from the YAML rule and the plan text, not from executing the missing parser.

## Consensus Summary (cycle 2)

Only one reviewer ran, so no finding can be agreed or disputed across reviewers. The orchestrator weighed
referee-two's findings against the source instead, and ran them where they described behaviour (Triage below). The
review carries no `[reviewed-without-repo-access]` or `[reviewed-without-source-citations]` marker: every batch read
the repository and cites `path:line` evidence.

### Agreed Strengths

None across reviewers (one reviewer). These strengths referee-two named were also confirmed by the orchestrator:

- Every confirmed cycle-1 item is fixed. referee-two gave eight FIXED verdicts, and the orchestrator re-checked each,
  including a simulation of all eight revised fixture verdicts.
- 32-01's probe answer (one 8-hex code per embedded file, joined with hyphens into one word) matches 32-04's exact
  comparison.
- 32-03's and 32-05's cited skill lines still match the tree.
- No batch has a same-wave file overlap or a missing `depends_on`.

### Agreed Concerns

None (one reviewer).

### Divergent Views

The orchestrator's check diverged from referee-two on all 7 HIGH labels; each was refuted against source or by a run.
It confirmed one MEDIUM as raised (C2-7) and one MEDIUM at LOW (A2-1).

## Triage (cycle 2, orchestrator, 2026-11-07)

7 HIGH labels were raised: C2-1, C2-5, D2-1, D2-2, D2-7, E2-1 and E2-2. Each was refuted against source or by
running the claim, so 0 HIGH remain. Every confirmed cycle-1 item is fixed. Two findings are confirmed: one MEDIUM
and one LOW, both in 32-07 and both older than the revision. Each comes with the plan change it still needs. Every
other finding is listed under "Rejected or not actionable" with its evidence.

### Cycle 1 fixes verified

referee-two marked each confirmed cycle-1 item FIXED, and the orchestrator re-checked them:

- **M1 (32-07, the tracer after the `check` rewrite; the unguarded count lookup): FIXED.**
  - TestTracer gains `inputs.json`, `loops/32.json` and a `report` before each `check` (32-07-PLAN.md:130).
  - Its count record comes from `count_skill` with no jev and a null `last_v4`. It equals `deterministic_count(None)`,
    so it also passes Task 2's count check.
  - `render_report` guards its inputs (:142), and `check` turns that error into `REJUDGE.md not checked: <message>`
    (:152).
- **M2 (32-01 and 32-07, the boundary fixtures): FIXED.** Every fixture names its maxima and drops (32-01-PLAN.md:209;
  32-07-PLAN.md:99, :127, :177-178). The orchestrator ran all eight through the phase 27 validator plus 32-01's two
  extra rules: each is valid, with the stated total, grade and bar clause (`tmp/p32-review-c2/sim_fixtures.py`).
- **M3 (32-07 and 32-09, no test for a skill with no verdict): FIXED.** TestCheck `not judged` exits 1 in default mode
  (32-07-PLAN.md:181, :193), and 32-09 stops on `not judged` (32-09-PLAN.md:92).
- **L1 (32-01, the interim `check` and null verdicts): FIXED** (32-01-PLAN.md:176).
- **L2 (32-04, a name in both input maps): FIXED** (32-04-PLAN.md:24, :154, :161, :172).
- **L3 (32-04 and 32-07, the count record's `jev` contract): FIXED** (32-04-PLAN.md:23, :150, :171; 32-07-PLAN.md:180,
  :195).
- **L4 (32-08, the third effort variable): FIXED** (32-08-PLAN.md:24, :97, :122).
- **L5 (32-01, 32-04 and 32-08, a probe code after every embedded file): FIXED** (32-01-PLAN.md:205, :214;
  32-04-PLAN.md:21, :107, :112, :121; 32-08-PLAN.md:20).
- **Roadmap drift (advisory): resolved.** ROADMAP Phase 32 criterion 3 now carries the bar-boundary amendment (see
  Verification coverage).

### Confirmed HIGH

None.

### Confirmed actionable (MEDIUM and LOW)

- **C2-7 MEDIUM, 32-07: `worst_record` breaks ties by an `order` the plan never defines, and no test renders a
  substitute.**
  - `worst_record(recs, refutations, order)` minimizes `(judge_bar(...)[0], round(percent * 10), position of the
    judge in order)` (32-07-PLAN.md:140, unchanged since `d9117a4`). No step says what `order` is. The bar, worst
    percent and digest cells and the `check` line all come from that record (:144, :194).
  - Ties alone are harmless: the tied records share their percent, grade and clause.
  - The risk is an implementer who passes `pool.members` as the order. When both configured judges were usable,
    `members` holds only the two external ids (32-04-PLAN.md:108). A native substitute's record then has no position.
    That is exactly the record 32-08 writes for a failed external lane (32-08-PLAN.md:141-142).
  - No test catches it: no TestReport or TestCheck behavior line holds a substitute record (32-07-PLAN.md:124-130,
    :173-184). Yet the prohibition "MUST NOT substitute a judge model without recording which ran and why" claims
    test verification (:46).
  - It would surface only in 32-09, after the multi-hour run.

  Change, in 32-07 Task 1:
  - Define `order` as the Verdicts row order already written for the report: the loop's `pool.members`, then
    `pool.judges`, then `pool.native`, then any other judge string in sorted order (:145). Use it in `render_report`
    and in `check`.
  - Add one TestReport behavior line: a loop whose `pool.members` are `cli-a:model-a` and `cli-b:model-b`, and a skill
    whose round holds a `cli-a:model-a` verdict and a `native:fixture` verdict whose `substitute` is
    `{"replaces": "cli-b:model-b", "reason": "<text>"}`. Its Verdicts row shows `replaces cli-b:model-b: <text>`, and
    `report` then `check` (default judge list) exit 0 with the worst record picked by that order.
- **A2-1 LOW (raised as MEDIUM), 32-07: a record that is valid JSON but lacks the record keys raises a bare
  `KeyError`.**
  - As stated, the finding is wrong: the round number comes from the `r<N>` folder, not from the record
    (32-01-PLAN.md:176). A weaker version holds.
  - The checker reads each record's `verdict`, `rubric_version`, `spec_sha` and `judge` with no shape check
    (32-01-PLAN.md:176; 32-07-PLAN.md:192). `load_round` turns only a JSON load failure into `JudgeLoopError`
    (32-07-PLAN.md:137).
  - That breaks the plan's own contract: every refusal or bad input raises `JudgeLoopError` (32-01-PLAN.md:147).
  - check-dogfood's wrapper catches only that error (32-07-PLAN.md:227), so a hand-edited committed record would end
    the push hook with a traceback instead of a `judge records:` problem.
  - The push still fails, because an uncaught exception exits 1. Hence LOW.

  Change, in 32-07 Task 1:
  - `load_round` also raises `JudgeLoopError` naming the file when a record is not a JSON object holding the record
    keys (the manifest keys plus `substitute`, `attempts` and `verdict`).
  - Add one TestCheck behavior line: a record with its `verdict` key removed makes `check` exit 1 with a problem or
    message naming the file.
  - 32-01's interim checker needs no change: it runs only in tests until 32-07 replaces it.

### Rejected or not actionable

Batch A (32-01, 32-02):

- **A2-2 (MEDIUM) 32-01, a missing finding file crashes ingest.** Refuted. The checks run in the stated order:
  confinement under the root, then the file check, then the line count (32-01-PLAN.md:215). The task is test-first
  (:196), and its behavior line requires a missing file to be a failed attempt with exit 0 (:207). A crash would fail
  that test.
- **A2-3 (MEDIUM) 32-01, "highest counts" has two readings.** Refuted. "The highest counts over those verdicts"
  (32-01-PLAN.md:176) is the maximum of each count:
  - SPEC R5 uses the same wording ("the highest critical and high counts", 32-SPEC.md:108);
  - the phase 27 checker takes the two maxima separately (check_verdicts.py:191-192);
  - 32-07 says "the highest raw counts" (32-07-PLAN.md:144).

  The wording is unchanged by the revision.
- **A2-4 (LOW) 32-01, `finding_path_errors` is not created in Task 1.** Refuted. Task 2 step 2 defines and uses it
  (32-01-PLAN.md:215); the artifacts list covers the whole plan.
- **A2-5 (LOW) 32-01, an empty `--skills` list exits 0.** Not actionable. This is the interim checker; 32-07's defaults
  cover every `inputs.json` skill (32-07-PLAN.md:173), and the reviewer calls the interim behavior acceptable.
- **A2-6 (LOW) 32-01, the copied status-line parser splits on spaces.** Withdrawn by the reviewer ("Not a new gap");
  not sent to jev.
- **A2-7 (ponytail LOW) 32-01, prompt rule 6 (attribution) has no source.** Refuted. The research requires the new
  prompt to keep the judging package's attribution rule (32-RESEARCH.md:274).
- **A2-8 (LOW) 32-02, `_criteria` does not say "the first" `**Plans**`.** Not actionable. "Up to `**Plans**`" stops at
  the first occurrence (32-02-PLAN.md:111), every live phase block has exactly one, and the wording is unchanged by the
  revision.
- **A2-9 (LOW) 32-02, a heading with a space before its colon is skipped.** Not actionable. The exact pattern is given
  (32-02-PLAN.md:111), and every live heading matches it.

Batch B (32-03, 32-05):

- **B2-1 (MEDIUM) 32-03, the cursor Evidence bullet fails the version rule.** Refuted. `main_flow` drops everything
  from a last non-fenced `## Evidence` heading (32-03-PLAN.md:123), and the Rails append that heading at the very end
  of the file (:103). The orchestrator applied every 32-03 edit in memory (each target matched exactly once) and ran
  the plan's exact rules. curated-config's Evidence section is detected as trailing, and all 16 kept skills give 0
  main-flow hits (`tmp/p32-review-c2/sim_postedit.py`).
- **B2-2 (LOW) 32-03, reference files keep dated headings.** Withdrawn by the reviewer (D-18's split, cycle 1's B5);
  not sent to jev.
- **B2-3 (LOW) 32-05, the bold-example exemption is narrower than the prose.** The reviewer says no change is required;
  not sent to jev.
- **B2-4 (LOW) 32-05, one reference date sample stays unchecked.** The reviewer says it restates D-18's scope boundary;
  not sent to jev.

Batch C (32-04, 32-07):

- **C2-1 (HIGH) 32-04, `ask_jev` calls a command that never answers the item.** Refuted.
  - `ladder` reads `{"items": [...]}`, builds the inner request with `reviewed_head` itself and sets its own child
    environment (jev_ladder.py:546-582, :562, :411-425).
  - It maps a score item's `level` to the level text that `jev_level` reads (:500-504).
  - A live run of exactly 32-04's call returned exit 0, `client.found` true, and typed `laya` and `typesafe` columns
    whose `choice` is one of the item's levels. The run copied the plan's argv, stdin and env and used the pinned,
    value-free item and the checkout's client (`tmp/p32-review-c2/ask_jev_live.py`).
  - That run was low-confidence on both backends, so `decided_by` was `own_reasoning`. 32-04 already maps that
    advisory outcome to one judge.
  - One cosmetic residual: `child_env` replaces the caller label `JEV_CALLER=judge_loop` with its own
    (jev_ladder.py:424). It is outside this phase and changes no answer.
- **C2-2 (MEDIUM) 32-04, `count_skill` will not pass pylint as one function.** Refuted (TypeSafe leaned real; not
  followed). The shared rails require splitting helpers within the limits and forbid disable comments
  (32-01-PLAN.md:113). pylint runs at the commit stage on `tools/` (.pre-commit-config.yaml:9, :26-31), so an
  over-limit function blocks its own commit. This is the same class as cycle 1's A5, A8 and C13.
- **C2-3 (LOW) 32-04, the CLI test's canned ladder document is not given.** Not actionable. The output shape is in the
  plan's context (32-04-PLAN.md:81), and a concrete answer is in the fake-`ask` line (:150). The CLI line checks only
  that counts are written and bad inputs are refused (:153-154).
- **C2-4 (LOW) 32-04, `percent_words(88.0)` says "just outside".** The reviewer does not re-raise C5 (D-05 leaves the
  wording to discretion); not sent to jev.
- **C2-5 (HIGH) 32-07, the default judge list leaves out the native substitute.** Refuted.
  - The default accepts `pool.judges` plus `pool.native` (32-07-PLAN.md:173).
  - `choose_pool` records the native id under `native` (32-04-PLAN.md:122). 32-08 passes the same `NATIVE` as
    `--native` and as every native lane's `--judge` (32-08-PLAN.md:95, :103, :141), so a substitute's judge is
    `pool.native`.
  - 32-09 passes an explicit judge list built from the records anyway (32-09-PLAN.md:92).
- **C2-6 (MEDIUM) 32-07, the not-judged rewrite contradicts 32-01.** Refuted. Task 1's `check` test lists only
  `demo-a` (32-07-PLAN.md:129). 32-01's not-judged problem (32-01-PLAN.md:176) is kept, and Task 2 restates the same
  string and adds its test (32-07-PLAN.md:181, :193).
- **C2-8 (LOW) 32-07, `render_report` as one function exceeds the lint limits.** Refuted (TypeSafe leaned real; not
  followed). The reason is the same as C2-2: the rails' split rule and the commit-stage pylint hook. 32-07's artifacts
  list already allows helpers "or equivalents" (32-07-PLAN.md:283).
- **C2-9 (LOW) 32-07, some `## Judge count inputs` cells are not given exact text.** Not actionable. The report is
  only compared with a fresh render by the same code (32-07-PLAN.md:152), so two implementations never have to match.
  The global cell rules cover the formatting (:141), and the wording is unchanged by the revision.
- **C2-10 (LOW) 32-07, `_judge_loop` loads the tool without registering it.** Refuted. The plan says "register in
  `sys.modules` before `exec_module`" (32-07-PLAN.md:227).

Batch D (32-08, 32-09):

- **D2-1 (HIGH) 32-08, the probe wait can never report `probes ended`.** Refuted. Each probe runs in its own detached
  child under `run-with-timeout 660` (32-08-PLAN.md:98, :100), and the 170 s wait repeats until `probes ended`
  (:112). "At most about 11 minutes" is that 660 s bound. That wording was already in the plan before the revision
  (`d9117a4`, line 112). This repeats cycle 1's D4 with no valid new evidence.
- **D2-2 (HIGH) 32-08, `pool.members` holds objects, not ids.** Refuted. 32-04's behavior lines give `members` as id
  strings, for example `["cli-a:m", "cli-b:m"]` and `["cli-b:m", "native:fixture"]` (32-04-PLAN.md:108, :110). The
  reviewer itself says the finding then drops to a wording gap.
- **D2-3 (MEDIUM) 32-08, the worker misreads the runner's hard-tier stop.** Refuted. Every hard-tier stop, including
  `stopped=hard-waits` and `stopped=cap`, exits 69 (ai-kit-cross-ai SKILL.md:110, :161-162). The worker stops the
  judge on 69 (32-08-PLAN.md:138). One wait, then one re-run per `retry_after_s`, is the skill's own rule
  (SKILL.md:137-139). This repeats cycle 1's D2.
- **D2-4 (MEDIUM) 32-08, `count` runs jev against possibly unreachable base commits.** Refuted. All four base commits
  resolve in this checkout: `git rev-parse --verify` exits 0 for 3410359, 76fa531, d2855bc and 16153d6. An
  unresolvable base records `jev input absent: base commit <base> not found` and keeps the count, with exit 0
  (32-04-PLAN.md:25, :171). This is cycle 1's D9.
- **D2-5 (LOW) 32-08, `scope.py close` may meet a live worker.** Refuted. `close` runs after `status` prints `all
  lanes ended`, which requires no live worker (32-08-PLAN.md:139, :207). This is cycle 1's D3.
- **D2-6 (ponytail MEDIUM) 32-08, the worker re-implements the runner skill.** Refuted. This repeats cycle 1's D13
  without new evidence: D-08 makes the run follow ai-kit-cross-ai.
- **D2-7 (HIGH) 32-09, the audit checks columns the report does not have.** Refuted. The reviewer then confirms the
  columns exist (32-07-PLAN.md:145), and the audit reads the `## Verdicts` section by its column names
  (32-09-PLAN.md:117). The rest repeats cycle 1's D11: reading table rows after the header row is a standard parse.
- **D2-8 (MEDIUM) 32-09, an old score could collide with a new percent.** Refuted. Each `old_score.value` is a whole
  inventory cell with its result, date and phase, for example `old 102/120 (85.0%) PASS, 2026-10-25, phase 25.1`
  (15-skills-vs-new-judge.md:106-129). The check looks for that whole string, never for a percent
  (32-09-PLAN.md:117).
- **D2-9 (LOW) 32-09, `publish.py` counts an identical existing file as published.** Not actionable. The script runs
  once, after every lane ended on a clean tree, and refuses different bytes before copying anything (32-09-PLAN.md:84,
  :90). The reviewer calls it harmless.
- **D2-10 (ponytail LOW) 32-09, the audit repeats the checker.** The reviewer agrees with cycle 1's D14 that this is
  not a defect; not sent to jev.

Batch E (32-06):

- **E2-1 (HIGH) 32-06, the new module sorts before `tests.test_framework_profiles`.** Refuted.
  `sorted(["tests.test_framework_profiles", "tests.test_skill_frontmatter_pyyaml"])` keeps
  `tests.test_framework_profiles` first ('f' sorts before 's'), as the plan says (32-06-PLAN.md:139, :150).
- **E2-2 (HIGH) 32-06, the fold rule puts a space across a blank line.** Refuted. The plan joins only *consecutive*
  non-blank lines with one space and turns each blank line into `\n` (32-06-PLAN.md:114). That rule matched PyYAML on
  nine cases, including the reviewer's own `>` example (`a\nb\n`) and the clip, strip and keep modes (`uv run python
  tmp/p32-review-c2/fold_check.py`: 0 differing).
- **E2-3 (MEDIUM) 32-06, the npm script imports a Python module.** Refuted. The import belongs to `dump_fixtures.py`,
  which writes `fixtures.json` with exactly the fields the `.mjs` prints; the `.mjs` then processes each fixture
  (32-06-PLAN.md:152).
- **E2-4 (MEDIUM) 32-06, quoting and block headers are under-specified.** Not actionable. Each case has a defined
  outcome under the stated rules (32-06-PLAN.md:113-114):
  - the value is the text after `: `, taken by `KEY_LINE_RE`;
  - a quoted value must end with its quote and decode with `json.loads`;
  - indented continuation lines and ` #` are rejected.

  D-17 makes the parser a deliberately stricter subset, the tree passes it, and the wording is unchanged by the
  revision.
- **E2-5 (LOW) 32-06, the chomp rules are easy to miscount.** Refuted by the same nine-case PyYAML comparison (keep,
  clip and strip all match).

## Verification coverage (cycle 2)

### Source-grounding pass (authority: grep)

`drift-guard authority --raw` returned `grep`. `drift-guard severity` gives, per verdict:

- VERIFIED: none;
- MISSING: needs-acknowledgement, no hard block;
- AMBIGUOUS: MEDIUM;
- UNCHECKABLE: INFO.

640 cited symbols were enumerated across the nine revised plans: paths, CLI flags and code names from inline code
spans, plus paths and flags inside fenced blocks. The pass reused cycle 1's script with one fix: the artifacts section
now ends at the new "Review Dispositions Ledger" heading, so names that a ledger cites are checked, not excluded
(`tmp/p32-review-c2/grounding.py`).

- 282 excluded: every symbol a phase 32 plan lists under "Artifacts this phase produces", plus each plan's own new
  files.
- 151 VERIFIED: the path exists, or the name has a declaration form in tracked source.
- 163 MISSING. Each is acknowledged and classified (`tmp/p32-review-c2/grounding_classify.py`, 0 unclassified). None
  is a missing reference to existing code:
  - 33 synthetic fixtures that tests build in temp dirs, now including the `skills/demo-a`, `demo-b` and `demo-c` repo
    that 32-07 builds;
  - 29 scratch paths the plans create;
  - 28 new names: test names, record and inputs keys, the records layout, 32-07's `fake_ask` and 32-09's
    `publish.py`;
  - 13 phase files written later;
  - 34 generic tokens;
  - 6 skill-relative paths, verified on disk;
  - 4 installed skill-judge entries, verified on disk outside the repo;
  - 2 npx-cache paths, re-verified live (`yaml` 2.9.0 and `skills` 1.5.20, `tmp/p32-review-c2/yaml_probe.mjs`);
  - 8 external names, not repository source: PyYAML's `SafeLoader`, `yaml.YAMLError`,
    `yaml.constructor.ConstructorError` and `flatten_mapping` (named in 32-06's ledger); Node's `module.createRequire`;
    Claude Code's `CLAUDE_CODE_EFFORT_LEVEL`, `CLAUDE_CODE_SUBAGENT_EFFORT` and `CLAUDE_CODE_AUTO_COMPACT_WINDOW` (the
    last added for L4);
  - 5 pointer and referee examples that the plans remove or use as failing fixtures;
  - 1 replaced name: `--judge-dir`, replaced by `--judge-package`.
- 8 AMBIGUOUS, each resolved by inspection, none actionable:
  - bare `SKILL.md` (5) and `__init__.py` (1) are generic;
  - `jev_review.py` is `skills/jev-fast-decision/scripts/jev_review.py`;
  - `22-INTERACTIVE-PI.md` is a pointer that 32-05 removes.
- 36 UNCHECKABLE (placeholders or globs, by design):
  - 32-01: `tests/test_*.py`, `tests/skills/<name>/`, `tests/<stem>.py`, three `<tmp>/...` lane and record paths, the
    `<tmp>/probe/...` prompt path, `skills/<name>/`, `skills/<skill>/SKILL.md`;
  - 32-02: `test_*.py`, `tests/skills/<name>/`;
  - 32-03: `skills/*/SKILL.md`;
  - 32-04: `<r>/loops/32.json`;
  - 32-05: `.planning/phases/<phase>/`, `.planning/phases/**/*-CONTEXT.md`, the `PHASE_DIR_RE` pattern;
  - 32-06: `skills/*/SKILL.md`, `<HOME>/.npm/_npx/`;
  - 32-07: `<records>/REJUDGE.md`, `loops/*.json`, `verdicts/**`, `refutations/*.json`, `refutations/<loop>.json`,
    `<tmp>/rec/inputs.json`, `<tmp>/rec/loops/32.json`, `*.json`;
  - 32-08: six `<DIR>/`, `RUN/` and `RECORDS/` placeholder paths;
  - 32-09: three `tmp/p32/judge/` globs and two `RUN/*.pid` globs.
- Signature claims are UNCHECKABLE under grep. Every reviewer claim about existing code was checked by hand or by a
  run; the Triage records each.

### Cross-artifact fact-drift pass

- **Phase status:** `drift-guard phase-status --phase 32` returned `lag`: STATE.md says "Ready to execute" and
  ROADMAP.md "Not started". Not a finding.
- **Success criteria versus must-have truths: no drift.** Cycle 1's advisory drift is resolved. Criterion 3 now
  carries the amendment: the bar's pass boundary at 80, from 73.0 to 87.0 inclusive. That matches JDG-06, SPEC R4 and
  32-04's band test (32-04-PLAN.md:22). The other seven criteria contradict no plan truth.
- **Requirement IDs versus plan requirements:** consistent. ROADMAP lists JDG-01, 02, 04, 05, 06, 07 and 08, which
  equals the union of the nine plans' `requirements` (`tmp/p32-review-c2/drift_facts.py`).
- **Glossary versus plan usage: no contradiction.** The revised probe still asks for one word: `AIKIT-SENTINEL`
  followed by the codes, joined with hyphens. That fits SPEC R3's "expected one-word answer" (32-SPEC.md:204) and the
  CONTEXT's discretion over the probe wording. Cycle 1's notes on `--judge-package` and on the wave numbering still
  hold.
- **Coverage:** STATE.md, ROADMAP.md, REQUIREMENTS.md and 32-CONTEXT.md were all present, so no axis was skipped.

## Cycle 1 (history)

Cycle 1 as committed at `df3319f` (reviewed_at 2026-11-07T11:57:52-03:00, plans at `d9117a4`, same reviewer and model). Its text is unchanged; only its headings are nested one level down. Line numbers of the form `32-0N-PLAN.md:<line>` in it cite the plans at `d9117a4`.

### Review conditions

Cycle 1, over the nine plans at `d9117a4`. The only reviewer was referee-two (`review.default_reviewers`, opencode lane,
model `router-env/my-referee-two` pinned through `review.reviewer_instances`). No other reviewer, harness, provider or
model was used. The probe at 11:25 was a one-word prompt; it came back `OK`, exit 0, in 4 s.

The full phase prompt would be about 370 KB, so the plans were split into batches. The suggested four batches by wave
put three plans and 163 KB into one batch. That is above referee-two's largest recorded prompt (about 150 KB), and a
two-plan batch had taken 1425 s in phase 31 against the lane's 1800 s cap. jev leaned to five cohesive batches (see
the jev log), and own reasoning decided the same: pair the plans that edit the same files along a dependency chain.

- A: 32-01, 32-02 (151 KB)
- B: 32-03, 32-05 (137 KB)
- C: 32-04, 32-07 (149 KB)
- D: 32-08, 32-09 (130 KB)
- E: 32-06 (114 KB)

Each prompt inlined:

- PROJECT.md (first 80 lines), the ROADMAP Phase 32 section, the JDG-01..JDG-08 rows, 32-SPEC.md and 32-CONTEXT.md;
- a pointer to 32-RESEARCH.md and 32-PATTERNS.md, which the reviewer can read in the repository;
- a wave map of all nine plans (wave, dependencies, files);
- the batch's plans in full;
- the source-grounding instructions and the owner's ponytail lens, verbatim;
- an executor note: execution is native on haiku at high effort, so flag any step that needs a design decision;
- a same-wave overlap check and the batch's plan coverage manifest.

Each batch ran through `review-lane invoke --slug opencode --as referee-two --model router-env/my-referee-two`, with
one run dir per batch, at most two batches at a time, each in its own process group, under a 15-minute no-I/O-growth
stall watch. There was no stall, retry, quota stop or auth stop, so the ai-kit-cross-ai retry ladder was never entered.

- **referee-two** (`router-env/my-referee-two`): A 294 s, B 233 s, C 201 s, D 297 s, E 249 s (11:29:55 to 11:41:20).
  Every lane returned `ok`, not stubbed, model source `pinned`. The plan coverage check found every plan id of each
  batch in its review (9/9).

These runs were much faster than phase 31's (907 to 1425 s). Still, every batch cites `path:line` evidence and has a
section per plan. Each batch's leading progress narration (the lines before its first heading) is left out below. The
raw outputs are preserved under `.review-diagnostics/`. While checking 32-06 the reviewer wrote seven probe scripts
into the opencode scratch folder `/tmp/opencode/`. They are reported, not deleted, under the local rule against
deleting outside `tmp/`. No tracked file changed during the review (`git status` was clean after every batch).

Every finding was triaged in two steps. First jev-fast-decision gave an advisory answer from a value-free summary.
Then the orchestrator checked the finding against the plan text and the source, using codegraph for code, rg for
Markdown, and simulations of the plans' exact rules under `tmp/p32-review/`. A finding counts as real only when that
check confirms it. Duplicate findings and findings the reviewer withdrew were not sent to jev.

#### jev log (advisory; Laya, then TypeSafe; "fallback" means `needs_fallback`)

- batching (11:28): laya regroup_cohesive 0.34 (fallback), typesafe regroup_cohesive 0.79 (fallback); own reasoning;
  used the five cohesive batches above.

Triage (11:48; six calls, 44 items, each item under Laya's 2,000-character guard and each call under TypeSafe's 8,000):

- A1: laya not_real 0.47 (fallback), typesafe not_real 0.79 (fallback); own reasoning; refuted (the plan's order
  matches the research recipe); the residual gap is kept as L5.
- A2: laya real 0.43 (fallback), typesafe not_real 0.93; typesafe; refuted.
- A3: laya real 0.43 (fallback), typesafe lower 0.67 (fallback); own reasoning; refuted as stated; the residual is
  folded into M2.
- A4: laya real 0.48 (fallback), typesafe real 0.84; typesafe (medium); confirmed at LOW, because only the interim
  checker is affected and 32-07 rewrites it (L1).
- A5: laya lower 0.40 (fallback), typesafe not_real 0.98; typesafe; refuted.
- A6: laya lower 0.44 (fallback), typesafe not_real 0.98; typesafe; refuted.
- A7: laya lower 0.62 (fallback), typesafe not_real 0.66 (fallback); own reasoning; refuted.
- A8: laya real 0.51 (fallback), typesafe not_real 0.94; typesafe; refuted.
- B1: laya not_real 0.48 (fallback), typesafe not_real 0.96; typesafe; refuted.
- B2: laya lower 0.37 (fallback), typesafe real 0.50 (fallback); own reasoning; refuted.
- B3: laya lower 0.55 (fallback), typesafe not_real 0.58 (fallback); own reasoning; refuted.
- B5: laya not_real 0.44 (fallback), typesafe not_real 0.92; typesafe; refuted.
- B7: laya real 0.47 (fallback), typesafe not_real 0.65 (fallback); own reasoning; refuted.
- B8: laya lower 0.39 (fallback), typesafe real 0.69 (fallback); own reasoning; refuted (D-19).
- C1: laya not_real 0.54 (fallback), typesafe not_real 1.0; typesafe; refuted.
- C2: laya not_real 0.50 (fallback), typesafe not_real 0.99; typesafe; refuted.
- C3: laya not_real 0.43 (fallback), typesafe not_real 0.88; typesafe; refuted.
- C4: laya real 0.44 (fallback), typesafe not_real 0.99; typesafe; refuted.
- C5: laya lower 0.52 (fallback), typesafe not_real 0.84; typesafe; refuted.
- C6: laya lower 0.38 (fallback), typesafe real 0.86; typesafe (medium); confirmed at LOW, because only a
  hand-written inputs file can collide (L2).
- C8: laya lower 0.57 (fallback), typesafe not_real 0.83; typesafe; refuted.
- C11: laya real 0.48 (fallback), typesafe not_real 0.41 (fallback); own reasoning; downgraded to MEDIUM (M2).
- C12: laya not_real 0.47 (fallback), typesafe not_real 0.97; typesafe; refuted as stated. The residual test gap is
  kept as L3 by own reasoning: the contract would fail only after the multi-hour run.
- C13: laya real 0.57 (fallback), typesafe not_real 0.93; typesafe; refuted.
- C14: laya not_real 0.40 (fallback), typesafe not_real 0.52 (fallback); own reasoning; refuted.
- C15: laya not_real 0.38 (fallback), typesafe real 0.97; typesafe; confirmed MEDIUM (M1).
- C16: laya lower 0.46 (fallback), typesafe lower 0.51 (fallback); own reasoning; not actionable (the layout already
  defines the cell).
- C17: laya lower 0.61 (fallback), typesafe not_real 0.90; typesafe; refuted.
- D1: laya not_real 0.52 (fallback), typesafe not_real 0.59 (fallback); own reasoning; refuted as stated; the residual
  gap became X2.
- D2: laya not_real 0.51 (fallback), typesafe not_real 1.0; typesafe; refuted.
- D3: laya not_real 0.57 (fallback), typesafe not_real 0.98; typesafe; refuted.
- D4: laya not_real 0.52 (fallback), typesafe not_real 0.97; typesafe; refuted.
- D5: laya not_real 0.50 (fallback), typesafe not_real 0.63 (fallback); own reasoning; refuted.
- D6: laya not_real 0.48 (fallback), typesafe not_real 0.97; typesafe; refuted.
- D7: laya not_real 0.48 (fallback), typesafe not_real 0.97; typesafe; refuted.
- D8: laya real 0.49 (fallback), typesafe real 0.82; typesafe (medium); confirmed at LOW, because the missing variable
  does not override effort (L4).
- D9: laya real 0.40 (fallback), typesafe not_real 0.97; typesafe; refuted.
- D10: laya lower 0.58 (fallback), typesafe not_real 0.89; typesafe; refuted.
- D12: laya lower 0.62 (fallback), typesafe real 0.61 (fallback); own reasoning; refuted.
- D13: laya not_real 0.41 (fallback), typesafe not_real 0.83; typesafe; refuted.
- E1: laya not_real 0.45 (fallback), typesafe real 0.55 (fallback); own reasoning; refuted (live npm `yaml` probe).
- E2: laya not_real 0.45 (fallback), typesafe not_real 0.46 (fallback); own reasoning; refuted.
- E3: laya lower 0.45 (fallback), typesafe not_real 0.88; typesafe; refuted.
- X1 (residual of A1): laya none 0.35 (fallback), typesafe low 0.58 (fallback); own reasoning; kept as LOW (L5).
- X2 (residual of D1): laya medium 0.42 (fallback), typesafe medium 0.92; typesafe; kept as MEDIUM (M3).

### OpenCode Review (referee-two)

#### Batch A (32-01, 32-02)

##### Review: `.planning/phases/32-re-judge-baseline/32-01-PLAN.md`, `.planning/phases/32-re-judge-baseline/32-02-PLAN.md`
###### Document Type
GSD · plan
###### Files Read
- `.planning/phases/32-re-judge-baseline/32-01-PLAN.md` (311 lines)
- `.planning/phases/32-re-judge-baseline/32-02-PLAN.md` (208 lines)
- Grounding: `32-SPEC.md`, `32-CONTEXT.md`, `32-RESEARCH.md`, `32-PATTERNS.md`, `32-04-PLAN.md`, `32-07-PLAN.md`, `32-08-PLAN.md`
- Source: `tools/check_dogfood.py`, `tools/staged_mapper.py`, `tools/run_unittest_parallel.py`, `tests/test_arch.py`, `tests/test_gate_scope.py`, `tests/test_check_dogfood.py`, `.planning/ROADMAP.md`, phase-27 `check_verdicts.py`, installed `skill-judge/references/rubric.md`, `agents/ai-kit-judge.md`, `README.md`

###### CRITICAL
- **The probe does not test that a judge saw the embedded package.** Location: `32-01-PLAN.md:218-220`; consumed by `32-08-PLAN.md:20`. Required: the probe token must occur before the final instruction, and the instruction must require the model to print that earlier token and nothing else. Why: research defines a pass as an exact echo of a sentinel placed after the package (`32-RESEARCH.md:418-423`). The planned prompt instead ends with the token followed by “Reply now with only that word,” so a model that ignored the preceding ~92 KB still passes. Plan 32-08 then accepts that exact echo as proof the judge can take the package.

###### HIGH
- **The JDG-04 scan includes Progress and Backlog.** Location: `32-02-PLAN.md:150`; source: `.planning/ROADMAP.md:886-949`. Required: the scan must stop at the first level-2 heading after Phase Details and before Progress. Why: the first such heading is `## Progress` at line 886; `## Backlog` is later, at line 930. Progress contains `### Phase 32.1` through `### Phase 54` rows whose text includes `SKILL.md` but no success criteria, so the proposed parser flags completed phases and `make check-dogfood` fails on the current tree. The fixture hides this because it places Backlog immediately after Phase Details.
- **The prompt contract contradicts itself and the rubric.** Location: `32-01-PLAN.md:42, 187-193`. Required: one explicit rule stating that only the skill name and rule-4 module line vary, while the runnable-code classification stays fixed in both prompts. Why: `build_prompt` has no ships-code argument, but rule 5 requires the judge to choose 5/5/5 or 8/7. The acceptance test then requires alpha and beta prompts to become identical after replacing only the name and rule-4 line, which fails once rule 5 states their different classifications. The rubric also fixes D1-D8 maxima (`rubric.md:8-17`), while the 79.9/80.0 fixture requires every maximum to be 125 (`32-01-PLAN.md:224`), so the exact-key validator copied from `check_verdicts.py:41-69` rejects the SPEC boundary case.
- **An executor must choose a prompt layout the plan does not define.** Location: `32-01-PLAN.md:187-193`. Required: the exact rule-5 sentence for both classifications, or an explicit second varying field in the equality test. Why: the current wording asks for both “rules 5 verbatim” and prompts differing only by name and module list. Those outcomes cannot both be true.

###### MEDIUM
- **Task 1’s `check` implementation is under-specified for its tracer.** Location: `32-01-PLAN.md:202-204`. Required: state that the printed line uses only verdict-bearing records, reports the highest round, and exits 0 on a stale digest. Why: the behavior block requires those outcomes, but the implementation paragraph does not say how attempts without verdicts or several `rN` folders affect the line.
- **The ROADMAP criteria boundary is looser than the real heading.** Location: `32-02-PLAN.md:150`; source: `.planning/ROADMAP.md:397`. Required: match `**Success Criteria**` and `**Plans**` as heading prefixes, including the parenthetical text. Why: the live heading is `**Success Criteria** (what must be TRUE):`. A literal marker search can still work, but it also accepts those words inside criterion prose.
- **Two large functions risk the lint cap.** Location: `32-01-PLAN.md:202-206` and `32-02-PLAN.md:150-151`; limits pinned at `tests/test_gate_scope.py:27-30`. Required: name the helper split before implementation. Why: `check` and `check_jdg04_citations` are specified with more control flow than pylint’s 12 branches and 50 statements allow, while `check_dogfood.main` (`tools/check_dogfood.py:511-539`) is already near that cap.

###### Cross-Document Consistency
- Plan 32-08 depends on 32-01’s probe proving package visibility, but 32-01 places the sentinel after the instruction rather than before it.
- Plan 32-07’s byte-compared report depends on 32-01’s checker line. The line format is testable, but its handling of null verdicts and round selection is not specified tightly enough for a later rewrite to preserve it.
- Wave 1 has no file overlap: 32-01 owns `judge_loop.py`, its test, the arch lookup entry, generated listings, the agent, and README; 32-02 owns `check_dogfood.py`, its test, and `test_gate_scope.py`.
- The `tools/judge_loop.py` lookup copy is covered by the explicit `LOOKUP_COPIES` comparison (`tests/test_arch.py:2231-2238`). The automatic assigner scan only covers `skills/` and `tools/hooks/` (`tests/test_arch.py:2240-2251`), so the manual tuple entry is the correct mechanism, not an omission.

##### 32-01

###### Summary
The plan correctly splits the judge tool into a tested prompt, ingest, and check core, and its repository-root, digest, lookup-copy, and path-confinement decisions match the existing code. The probe and prompt contracts need correction before execution because later plans consume them as proof of judge capability and layout consistency.

###### Strengths
- Reuses `validate_verdict`, `grade_of`, and `parse_status_line` from phase-27 `check_verdicts.py:30-79`, and `_load_mapper` from `tools/run_unittest_parallel.py:587-595`.
- `find_root` and `skill_digest` correctly avoid the old working-directory digest bug in `check_verdicts.py:101-107`.
- `LOOKUP_COPIES` is a real drift check, and the prescribed five-row `SKILLS_ROOTS` literal matches `jev_ladder.py:35-41` and `python_roots` at `tests/test_arch.py:1728-1734`.
- `covering_modules` is the correct module-list source (`tools/staged_mapper.py:218-232`), including the tight `ai-kit-spec-review` exception.
- Ingest has the required security boundaries: exact judge and skill checks, root-confined finding paths, atomic writes, and no overwrite of a valid verdict.
- The native `effort: xhigh` edit matches the existing frontmatter shape in `agents/ai-kit-judge.md:1-6` and the README row at `README.md:51`.

###### Concerns
- **HIGH — Probe accepts a truncated read.** `32-01-PLAN.md:218-220` places the sentinel after the instruction. `32-RESEARCH.md:418-423` requires it before the instruction so the model must have read the embedded package. `32-08-PLAN.md:20` treats the echo as the capability gate.
- **HIGH — Prompt equality and D7 classification conflict.** `32-01-PLAN.md:187-193` demands identical prompts after replacing only name and module line, while rule 5 must distinguish runnable and non-runnable skills. `build_prompt` has no ships-code field (`32-01-PLAN.md:42`).
- **HIGH — The percent boundary fixture cannot satisfy the fixed rubric.** `32-01-PLAN.md:224` changes every dimension maximum to 125, but the installed rubric fixes those maxima (`skill-judge/references/rubric.md:8-17`) and the copied validator enforces exact keys rather than a separate maxima table (`check_verdicts.py:41-69`).
- **MEDIUM — `check` behavior is not fully executable as specified.** `32-01-PLAN.md:202-204` does not define how verdict-less attempts are excluded or which round supplies the printed line.
- **LOW — `main` may exceed pylint limits.** The subparser setup at `32-01-PLAN.md:205-206` adds many branches; the plan states the limits but does not pre-split this function.

###### Suggestions
- Put the sentinel before the final line and make that line say to print the preceding sentinel exactly, matching `32-RESEARCH.md:418-423`.
- State the classification explicitly in rule 5 and exclude that rule from the equality normalization.
- Keep D1-D8 maxima at 20/15 and derive 79.9/80.0 from a total of 100 or 101 against `max_total` 125, unless the schema is explicitly extended with a tested exception.
- Specify that `check` selects the highest `rN`, ignores attempts with a null verdict, and keeps exit 0 for stale output.

###### Risk Assessment
**HIGH.** The core tool structure is sound, but the probe can certify a judge that did not read the rubric, and the prompt tests encode two incompatible outputs.

###### Ponytail findings
- **LOW — Needed, with no material speculative API.** The module, six eventual subcommands, record schema, and agent effort line all implement locked D-01, D-02, D-10, and D-13 through D-15. The unused jev constants are justified because plan 32-04 consumes them.
- **LOW — Existing helpers are reused appropriately.** The plan copies the phase-27 validator and uses `staged_mapper.covering_modules` (`tools/staged_mapper.py:218`) instead of creating a skill-to-test table.
- **MEDIUM — The prompt contract over-constrains the implementation.** Requiring both a variable D7 classification and byte-level equality after only two substitutions forces either an unrequested abstraction or a failing test (`32-01-PLAN.md:187-193`).

##### 32-02

###### Summary
The stray-module guard is precise and grounded in the runner’s non-recursive discovery. The citation guard has the right behavior matrix, but its section boundary is wrong for the live ROADMAP and would fail the very tree the plan says passes.

###### Strengths
- `stray_test_modules` matches `discover_modules`, which uses a flat `tests_dir.glob("test_*.py")` (`tools/run_unittest_parallel.py:246-248`), and correctly skips direct files, non-test fixtures, case variants, and `__pycache__`.
- The guard is placed in `tests/test_gate_scope.py`, beside the discovery rules and the existing non-vacuity class at lines 633-655.
- The JDG-04 regex and phase-number tuple comparison correctly distinguish 32.1 from 32 and 31.1, and reject `JDG-040` and `jdg-04`.
- Fixture tests follow the existing `TestEdgeFloors._root` pattern (`tests/test_check_dogfood.py:518-531`) and do not make tests read the repository’s `.planning/`.
- The plan reuses `check_edge_floors`’s `(problems, notes)` contract and `main()` composition (`tools/check_dogfood.py:478-539`).
- No generated listing or same-wave file overlap exists.

###### Concerns
- **HIGH — The live section boundary is `## Progress`, not `## Backlog`.** `32-02-PLAN.md:150` scans until the next `## `, but `.planning/ROADMAP.md:886-949` places Progress before Backlog. Progress rows such as `32.1. Batch 1, general small skills` contain `SKILL.md` and no success criteria, so the guard flags them.
- **MEDIUM — Marker matching is not anchored to headings.** `32-02-PLAN.md:150` uses substring boundaries, while the real criteria heading includes `(what must be TRUE):` at `.planning/ROADMAP.md:397`.
- **MEDIUM — `check_jdg04_citations` is too large as one function.** Its specified missing-file, missing-section, phase, criteria, and token branches exceed the pinned pylint budget (`tests/test_gate_scope.py:27-30`) without a named split.
- **LOW — The fixture passes while the live scan fails.** `32-02-PLAN.md:141-146` models a roadmap ending directly in Backlog, so its tests cannot catch the Progress heading.

###### Suggestions
- Stop at the next level-2 heading and add a fixture containing `## Progress` before `## Backlog`.
- Match criteria and plans headings with prefixes, not bare substrings.
- Split phase parsing from citation checking so `main()` only needs the same two composition lines as `check_edge_floors`.

###### Risk Assessment
**HIGH.** The stray-test task is ready, but the citation task as written fails `make check-dogfood` on the current ROADMAP despite its explicit acceptance criterion saying that command passes.

###### Ponytail findings
- **No extra scope.** Both functions implement locked D-16, D-21, and D-22; no new dependency, option, or abstraction is introduced.
- **Existing patterns are reused.** The plan follows `check_edge_floors` (`tools/check_dogfood.py:478-508`) and `TestEdgeFloors._root` (`tests/test_check_dogfood.py:518-531`).
- **MEDIUM — The section parser is not the smallest correct rule.** A prefix check for the next `## ` heading is sufficient, but the plan names Backlog as the boundary even though the file contradicts it (`.planning/ROADMAP.md:886-930`).

###### Status: Issues Found — fix and re-invoke

#### Batch B (32-03, 32-05)

##### 32-03

The plan covers SPEC R9's main-flow half and the AGENTS.md sentences of R6 and R9 (D-18, D-19, D-20). I re-ran its regexes against the tree: the eight SKILL.md hits it names are exactly the ones that exist (`ai-kit-cross-ai/SKILL.md:91`, `ai-kit-gsd-curated-config/SKILL.md:329` and `:334`, `ai-kit-spec-config/SKILL.md:221` and `:314`, `ai-kit-spec-review/SKILL.md:164`, `ai-kit-gsd-spec-discuss/SKILL.md:206`, `ai-kit-spec-review-checklist/SKILL.md:199`, `jev-fast-decision/SKILL.md:62`), and the two judgment calls it makes are right. "every model family confirmed live in the CLI profiles" (`skills/ai-kit-spec-config/SKILL.md:194`) does not match `\bconfirmed live\s*(?::|\d{4}-\d{2}-\d{2})`, and the current `gsd-core 1.17.0` sits inside a code span in a sentence that already contains `older` (`skills/ai-kit-spec-execute-superpowers/SKILL.md:280-281`), so the version rule never fires on it. The replacement sentence "dispatch needs Node 24 (GSD's declared floor; older versions untested)." still carries `older`, and `tests/test_ai_kit_spec_runtimes_table.py:888-890` pins a different file (`skills/ai-kit-spec-review/SKILL.md:215`), so Task 2's verify command is not broken by the edit. `tests/test_rules_docs.py:137-143` splits a bullet at the next `\n- `, and the plan's "no new `- ` line" instruction matches that. Same-wave 32-04 touches only `tools/judge_loop.py` and `tests/test_judge_loop.py`.

**Strengths**

- Every edit is an exact string replacement with a before/after, so a haiku executor does not invent wording.
- The non-vacuity list is concrete: a fenced ISO timestamp fails, the same date under a last `## Evidence` passes, `## Evidence` followed by `## Notes` fails, and a fenced `## Evidence` is not a section.
- `confirmed live` is narrowed to "colon or date follows" with both outcomes pinned, which is the only reading that keeps `SKILL.md:194` green.
- The exempt set is pinned equal to the folders with the prefix, not just written down.
- Task 1 regenerates the listings with `python3 tools/gen_test_groups.py` and its verify fails on a "stale listing" line, which is the message `tests/test_gate_scope.py:536` actually prints.

**Concerns**

- **HIGH** — Task 2's verify cannot pass as written. `version_hits` groups consecutive non-blank lines into one paragraph and splits sentences on `(?<=[.!?])\s+`. In `skills/ai-kit-gsd-spec-discuss/references/decision-table.md` the heading on line 52 has no blank line before the paragraph, so it joins the sentence "…(23 B12: jev 0.97 "fix both"…)" and that sentence has no constraint word. `VERSION_TOOLS` contains `jev`, so the hit is `version jev 0.97`. Task 2's tree assertion is `history_hits` returns `[]` for every kept skill, and its verify runs `tests.test_skill_text_history`. The plan says a hit it did not list "gets the same treatment", but this file is one 32-05 edits, and 32-05 only adds pointer rules. 32-03's own success criterion is that the history test passes on every kept skill.
- **MEDIUM** — The date rule is applied to fenced lines and code spans, but the version and run-log rules skip fenced lines. A fenced `node 24.1.0` is a required passing fixture, while a fenced `2026-10-25T17:26:29Z` is a required failing one. The asymmetry is deliberate (research open question 1), but it is stated only in the fixture list, not in the rule text an executor implements from, and it is the opposite of what "a date fails anywhere, code spans included" suggests for versions.
- **LOW** — `depends_on: [32-01]` is not earned. 32-03 reads no output of 32-01; the only shared thing is the rails section, which is text in the plan file and exists before 32-01 executes.

**Suggestions**

- Make headings paragraph breaks in `version_hits` (a line starting `## ` ends the paragraph), and add the decision-table line as a non-vacuity case so the grouping cannot regress. That also fixes the false hit without touching a file 32-05 owns.
- State the fence rule in one sentence in the action: dates and `as of` scan every main-flow line including fenced lines and code spans; versions and run logs skip fenced lines.
- Drop 32-01 from `depends_on`, or say the dependency is documentary only.

**Risk Assessment: MEDIUM.** The SKILL.md edits and the AGENTS.md pins are executable as written and match the tree, but Task 2's green-tree assertion fails on a reference file the plan never mentions, and the failure shows up in the task's own verify command.

###### Ponytail findings

- Needed: yes. SPEC R9's main-flow rules, D-18, D-19 and D-20's three AGENTS.md sentences. No extra option or abstraction; the test is one module of regexes plus fixtures.
- Reuse is right: `_design_bullet` and `_missing_clauses` at `tests/test_rules_docs.py:40-42` and `:137-143`, `tools/gen_test_groups.py:1-7`, and the stale-listing check at `tests/test_gate_scope.py:535-536`.
- **MEDIUM** — the version rule reaches a caller the plan does not. `decision-table.md:54-55` fails it, and no task edits that file.

##### 32-05

The plan covers SPEC R9's pointer half as amended (D-18, D-19). I ran `PHASE_DIR_RE`, `PHASE_FILE_RE`, `BACKLOG_RE`, `DECISION_RE` and `REFEREE_RE` over every `.md` outside `evals/` in the 16 kept skills. The hits are exactly the lines the plan names: curated-config `SKILL.md:333`, `:334`, `:338`; spec-config `:332`; usage-metrics `:43` and `:313`; spec-discuss `decision-table.md:64,70`, `log-formats.md:51,60,95,96,114`, `worked-examples.md:14,24,47,54`; jev `backends/laya.md:57` and `backends/typesafe.md:18`. The bold example at `log-formats.md:38` (`- **D-14: …**`) is exempt by the two-character check, `NN D-xx` at line 61 does not match, and `D-NN` at line 55 does not match. `tests/test_curated_config_apply.py:2608-2638` pins the three phase-file names the plan removes, and the plan updates both pins. `tests/test_ai_kit_spec_runtimes_table.py:109` pins `21-SMOKE-CURSOR.md` inside a code label, not the skill text, so it survives. Same-wave 32-06 and 32-07 share no file with this plan: 32-06 owns `Makefile` and `.pre-commit-config.yaml`, 32-07 owns `AGENTS.md`.

**Strengths**

- The regexes do what the plan claims. I checked the bold-example exception, the URL exclusion and the whole-token rule against the real lines, including `JDG-04`-shaped text, and each behaves as specified.
- The three research additions D-19 missed are in the plan: bare `D-14` at `log-formats.md:95`, the `D-01..D-06` range at `:114`, and backlog `999.2` at `worked-examples.md:47`.
- The laya edit removes the planning path and keeps the measurement sentence, which is the behaviour-preserving form R9 requires.
- The curated-config pin tests move in the same commit as the row edit, so the suite does not go red between commits.
- `depends_on: [32-03]` is correct: this plan extends `history_hits`, `kept_skills` and `TestHistoryRulesNonVacuity`, which 32-03 creates.

**Concerns**

- **HIGH** — the tree assertion fails after every edit in this plan. `history_hits` runs `pointer_hits` over every shipped `.md`, but `DATE_RE`, `AS_OF_RE` and `RUNLOG_RES` stay SKILL.md-only, and the behavior block says `history_hits` returns `[]` for every kept skill. After the pointer fixes, the same function still reports dates, `as of`, run logs and versions in references. Counted with the plan's own regexes, the leftovers are 49 date lines, 2 `as of`, 5 run logs and 6 version hits, among them `skills/ai-kit-cross-ai/references/launch-and-wait.md:42` (the literal 32-03 explicitly keeps), `skills/ai-kit-gsd-spec-discuss/references/log-formats.md:50-61` and `:112` (dated format templates 32-05 rewrites around but never de-dates), `skills/ai-kit-gsd-spec-discuss/references/worked-examples.md:1`, `skills/jev-fast-decision/reference.md:110` and `:117` ("as of 2026-10-15", "as of 2026-10-18"), and `skills/ai-kit-spec-review/references/cli-profiles/opencode.md:24` (`opencode 2.0.29`). Task 2's verify runs `tests.test_skill_text_history`, so it fails. The plan's "any other hit gets the same treatment" only covers pointer hits.
- **MEDIUM** — the version rule's paragraph joining makes `skills/ai-kit-gsd-spec-discuss/references/decision-table.md:54-55` a hit (`jev 0.97`), and 32-05 is the plan that edits that file. Its Task 2 read_first includes it, and its fixes do not touch line 54. This is the same hit that breaks 32-03's Task 2.
- **MEDIUM** — `DECISION_RE` matches the whole range. `(D-01..D-06 kept)` at `log-formats.md:114` yields two matches, `D-01` and `D-06`. The plan's replacement `(D-<first>..D-<last> kept)` handles this one line, but nothing in the regex or the fixtures says a range counts twice, so a later `D-1..D-2` in a file the plan does not list fails with no stated rule for it.
- **LOW** — the usage-metrics edit drops the quoted backlog title "Cron/scheduling automation for usage-metrics daily ingestion" (`SKILL.md:43-44`). The limitation stays, so R9 is met, but the provenance is deleted rather than moved to evidence, unlike every other edit in the two plans.

**Suggestions**

- Decide the scope in the plan, since the executor cannot. Either scan references with the date, version and run-log rules too, and list each of the 49 date lines as a move into `## Evidence` or a rewording, or keep those rules on SKILL.md only and say so in `history_hits`. The second matches D-18's split ("main-flow rules on SKILL.md, pointer rules on all shipped Markdown") and the plan's own must-have, which limits dates and versions to SKILL.md. The first matches the behavior block as written.
- Whichever way: add one sentence to `version_hits` so a `## ` line ends a paragraph, and name `decision-table.md:54` in the fix list or the fixture list.
- State that `D-01..D-06` is two decision ids, and that the placeholder form is the required fix.

**Risk Assessment: HIGH.** The pointer regexes and the listed edits are correct and complete against the tree, but the acceptance line "history_hits returns [] for every kept skill" is false once references are included, the verify command runs that test, and the plan gives the executor no edit for those files.

###### Ponytail findings

- Needed: yes. SPEC R9's pointer rules and the 2026-11-07 amendment, D-18 and D-19. The placeholder swap is the whole feature, not a trimmed one.
- Reuse is right: it extends 32-03's `history_hits` instead of a second scanner, and it updates the existing pins at `tests/test_curated_config_apply.py:2615-2629` rather than adding a test.
- **HIGH** — the change does not reach every file it makes the test read. Pointer scanning widens `history_hits` to all shipped Markdown while the date and version rules stay unscoped, so files such as `launch-and-wait.md`, `log-formats.md`, `reference.md` and the cli profiles fail with no planned edit.

##### Cross-plan

32-03 and 32-05 agree on the function shape and the dependency direction, and neither collides with a same-wave plan. They disagree on what `history_hits` covers. 32-03's must-have limits dates, versions and run logs to SKILL.md above `## Evidence`, and its research note says `references/launch-and-wait.md:42` may keep its literal. 32-05's behavior block then requires `history_hits` to return `[]` for every kept skill while scanning every shipped `.md`. Both cannot hold, and each plan's verify command runs the test that exposes it. One sentence in 32-05, choosing which rules apply to references, removes the conflict.

#### Batch C (32-04, 32-07)

##### 32-04

`pool` and `count` are the right split of SPEC R3 and R4, and the pool half is concrete enough to execute. The count half will not survive contact with the real jev ladder: the plan tells the executor to read a response shape that `jev_ladder.py` does not produce, and the tests it specifies only pass against a fake that returns that invented shape.

###### Strengths

- Pool membership is decided from lane files, not from a hand-picked name. `probe_result` checks missing files, then a missing `AIKIT-XAI` line, then `lane_ok`, then an exact sentinel echo (`.planning/phases/32-re-judge-baseline/32-04-PLAN.md:168-169`), which matches the status contract the runner already prints (`status=ok`, `exit=0`, `tree=clean`, `32-RESEARCH.md:337`).
- The one-usable and zero-usable cases are named, including the "never count one judge twice" rule (`32-04-PLAN.md:55`, `:153`), and `--native` colliding with `--judges` is a hard error (`:158`).
- `update_loop_file` merges one key at a time and the test re-writes `counts` while keeping `pool` (`:170`, `:159`), so a later batch phase does not clobber the probe record.
- Integer tenths for the band (`abs(round(percent * 10) - 800) <= 70`, `:46`) is the comparison Pattern 5 asks for (`32-RESEARCH.md:233`), and the 72.9 / 73.0 / 87.0 / 87.1 cases are listed as tests.
- The jev item is pinned to fixed word bands, and the prohibition test asserts the serialized item contains neither `skills/` nor the skill name (`32-04-PLAN.md:193`). That is the right check for T-32-08.
- `numstat` refuses a base that is not `^[0-9a-f]{7,40}$` and treats `git rev-parse --verify --quiet` failure as "jev input absent" (`:210`, `:186`), which is the unresolvable-commit case research recorded (`32-RESEARCH.md:312`).
- The tool reuses `skills_roots`, `JEV_ENTRY_REL` and `SKILLS_ROOTS` from 32-01 instead of inventing a third lookup, and `CODE_SUFFIXES` for the script-file band.

###### Concerns

- **HIGH — `jev_level` reads a field the ladder never writes.** The plan's context says a score column carries `"choice": <winning level text>` (`32-04-PLAN.md:88`), and `jev_level` looks up `column["choice"]` in `item["criteria"]` (`:215`). `typed_answer` does put the level *text* in `choice`, but only by indexing the criteria with the client's `level` string (`skills/jev-fast-decision/scripts/jev_ladder.py:500-504`). The real stdout is `{choice, top, fallback, forced, model}` — there is no `level` key on the column (`jev_ladder.py:510-511`). The fake in the behavior block returns exactly that invented shape (`32-04-PLAN.md:195`), so `TestCount` passes and the live `count` in 32-08 raises `KeyError` or records `jev answer is not one of the levels` for every skill that reaches jev. With today's verdicts that is `ai-kit-gsd-spec-discuss` and `ai-kit-spec-goal-prompt` (`32-RESEARCH.md:233`). The fix is to read `column["choice"]` as the level text (it already is) and to have the fake return `{"choice": JEV_LEVELS[2], "top": 0.9, "fallback": false, "forced": false, "model": "m"}` with no `level` key.

- **HIGH — `decided_by != "own_reasoning"` is not "a backend decided".** `fill_columns` sets `decided_by` to the last rung whose column has a `choice` and `fallback is False` (`jev_ladder.py:533-541`). A low-confidence rung (`needs_fallback` true, `jev_review.py:1578-1587`) stays `own_reasoning` only when *every* rung fell back. A rung with `fallback: true` followed by a later confident rung reports the later backend. The plan treats any non-`own_reasoning` value as a raise (`32-04-PLAN.md:46`, `:215`) and never reads `column["fallback"]`. D-05 says raise only when `needs_fallback` is false (`32-CONTEXT.md` D-05). A low first rung plus a confident second one is fine; a confident column whose `fallback` the plan ignores is the bug: the plan has no branch for `fallback: true` on the winning column, and the test never sends one (`32-04-PLAN.md:195-196`). Read the decided column's `fallback` and keep one judge when it is true.

- **MEDIUM — `ask_jev` calls `ladder` with no `--client`, so the lookup runs twice and the override is dropped.** `find_jev_client` resolves `--client` or the skills-root copy (`:211`), then `ask_jev` runs `[sys.executable, "-B", client, "ladder"]` (`:212`). `jev_review.py ladder` parses its own `--client` and `jev_ladder.main` calls `find_client(seams.env, args.client)` again (`jev_ladder.py:638`). The path found by the tool is the program, not the client the ladder looks up. Under the unit-test baseline (temporary HOME, host config stripped, `32-RESEARCH.md:353`) the ladder's own lookup finds nothing, `run_ladder` sets every item to `own_reasoning` (`jev_ladder.py:574-576`) and exits 0. `count` then records "jev needs_fallback" instead of "no client", and a `--client` pointing at a fake jev client is never forwarded. The plan should pass `--client <path>` through, or document that `client` here is `jev_review.py` and the real client path is a separate argument. As written, the CLI test (`:198`) papers over this because its fake script ignores argv and prints canned JSON.

- **MEDIUM — `final_count` appends the whole `jev_level` note, so the recorded reasons cannot match the test.** `jev_level` returns `f"jev level {index} ({choice}) from {decided_by}"` (`:215`). `final_count` then stores `f"{note}: asks for two"` (`:216`). The required reason is `jev level 2 (<level text>) from laya: asks for two` (`:195`). That only matches if `note` is the `jev_level` string *and* the level text contains no colon that the later checker splits on. State one composition. Also `count_skill` calls `final_count(det, level, note)` where `det` is documented as both a tuple (`deterministic_count` returns `(int, list[str])`, `:203`) and something with `[1]` (`final_count` reads `det[1]`, `:216`). A haiku executor has to guess which.

- **MEDIUM — `percent_words` bands disagree with the stated examples.** `d <= 100` tenths is "just outside", `d <= 150` is "moderately far", else "far" (`:205`). For 96.0, `d = abs(960 - 800) = 160`, which is "far above" — the example passes (`:192`). For 68.0, `d = 120`, which falls in `<= 150` only if the cut is 150; the example says "moderately far below" (`:192`). 88.0 gives `d = 80`, "just outside" — fine. The cuts 100 and 150 are not derived from the 7.0-point variation, and 73.0 (`d = 70`) would be described as "just outside judge variation" even though it is *inside* the band and never reaches `percent_words` (jev is skipped at two). Pin one table of (percent, expected sentence) pairs, including a value on each cut (90.0, 95.0, 95.1), so the executor does not invent the boundary.

- **MEDIUM — `load_inputs` does not say which skills are judged.** The shape is `skills` plus `excluded` (`:86`), but `count` defaults to "every skill of `inputs.json`" (`:218`). If that includes `excluded`, the baseline run will try to count the eight skills SPEC says are not judged. Say: count `skills` only, in `(batch tuple, name)` order, and a name present in both maps is an error.

- **LOW — `probe_result` reason order omits a missing token as its own file.** Behavior says missing `token`, `lane.out` or `lane.err` all map to `no probe output` (`:169`). Good. But a probe dir whose `lane.out` is the sentinel with a trailing explanation and a clean status is unusable — covered. A status line with `exit=0` and `tree=clean` but `status=ok` padded with spaces is not covered; `lane_ok` is specified as exact equality in 32-01 (`32-01-PLAN.md:170`). Fine if the executor copies it. Not a gap if `lane_ok` stays exact.

- **LOW — `numstat` against `HEAD` while the tree is dirty.** `git diff --numstat <base> HEAD` (`:210`) ignores uncommitted edits. D-09 says nothing tracked changes while lanes run, so this is safe for the baseline and wrong for a later `count` run on a dirty skill. One line in the function docstring is enough.

###### Suggestions

- Change the `<context>` ladder paragraph (`32-04-PLAN.md:88`) to the keys `typed_answer` actually returns: `choice` (the level text), `top`, `fallback`, `forced`, `model`. Drop `level` from the column.
- In `jev_level`, treat the decided column as a raise only when `fallback is False` and `choice` is one of `item["criteria"]`; `fallback is True` keeps one judge with note `jev needs_fallback (<backend>)`. Add one behavior line for that case.
- `ask_jev` argv should be `[sys.executable, "-B", jev_review, "ladder", "--client", client]` when a real client path is known, and the missing-client branch should fire *before* the subprocess when `find_jev_client` returns None. The canned-script test can stay, but one test should assert the argv.
- Make `final_count`'s `det` parameter explicitly `tuple[int, list[str]]` and build the reason in one place. Add the colon-in-level-text case or ban colons in `JEV_LEVELS` (the current four strings have none — keep it that way and test it).
- Write the percent-word cuts as a table with one example on each boundary.
- `count` iterates `inputs["skills"]` only.

###### Risk Assessment

**HIGH.** The pool half is executable and matches SPEC R3. The count half's tests cannot fail on the bug that matters, because they stub `ask` with a shape the ladder does not emit (`jev_ladder.py:510-541` versus `32-04-PLAN.md:88,195`). Two of the fifteen skills depend on this path (`32-RESEARCH.md:233`), and 32-08 has no second chance to notice before the report is committed.

###### Ponytail findings

- **Needed.** SPEC R3 and R4, CONTEXT D-05 and D-08. No extra subcommand.
- **Over-built, MEDIUM.** `percent_words` and `change_words` are four bands times four file classes (`32-04-PLAN.md:205-207`). D-05 asks for fixed word bands so jev does not count; three bands would do. Not a reason to cut the feature — the bands are the feature — but the cuts should be a table, not new knobs.
- **Reuse.** `lane_ok` and `parse_status_line` from 32-01 (`32-01-PLAN.md:170`); `skills_roots` copied from `jev_ladder.skills_roots` (`skills/jev-fast-decision/scripts/jev_ladder.py:101`); `CODE_SUFFIXES` from 32-01 (`32-01-PLAN.md:145`). `atomic_write_json` is the same shape as `tools/config_doctor_appliers.py:30`. Good.
- **Missed caller, MEDIUM.** `ask_jev` does not pass `--client`, so `find_jev_client`'s result never reaches `find_client` (`jev_ladder.py:638`). That is the one caller that matters.
- **Does not reach.** No Makefile or pre-commit edit, correct: 32-01 adds `tests/test_judge_loop.py` and 32-04 only extends it (`32-04-PLAN.md:9-10`). `tests/test_arch.py` is in the verify command (`:239`) but not in `files_modified`, also correct.

###### Executor notes

A haiku executor cannot implement `jev_level` from the plan text alone without choosing between the plan's `"choice"` column (`32-04-PLAN.md:88`) and the `"level"` string `typed_answer` actually consumes (`jev_ladder.py:501-504`). The task says "per the `<context>` output shape" (`32-04-PLAN.md:215`) and the read-first points at `jev_ladder.py:470-582`, which contradict each other. Same for `final_count(det, ...)` versus `det[1]`. Those two are design decisions, not transcription.

###### Same-wave

Wave 2 is 32-03 and 32-04. 32-03's files are the history test, skill text, `AGENTS.md`, `tests/test_rules_docs.py`, `Makefile`, `.pre-commit-config.yaml` (`32-03-PLAN.md:7-20`). 32-04 touches only `tools/judge_loop.py` and `tests/test_judge_loop.py` (`32-04-PLAN.md:9-10`). No shared file. 32-04 does not read 32-03's output. `depends_on: [32-01]` is right: it needs `lane_ok`, `judge_slug`, `atomic_write_json`, `LOOP_RE`, `CODE_SUFFIXES`, `SKILLS_ROOTS` (`32-01-PLAN.md:292`). It does not need 32-02.

---

##### 32-07

The report and the full checker are the right shape for SPEC R5-R7 and D-06, and the byte-compare rule is the correct way to keep `REJUDGE.md` honest. Two of the checker's rules are stated in a way that will reject a well-formed record, and the dogfood wiring undercounts the cost of adding one more check to `main`.

###### Strengths

- `render_report` is specified as a pure function of the records folder: no git, no clock, no absolute path (`32-07-PLAN.md:25`, `:160`), which is Pitfall 7 (`32-RESEARCH.md:371-372`). The acceptance grep forbids `import time` and `import datetime` (`32-07-PLAN.md:178`).
- The bar clause is named and tested at both edges: 80.0 with a high finding is `met: grade B or better`, 79.9 with a high finding is `not met` (`:148-149`). That is SPEC R7's boundary row and Pattern 4 (`32-RESEARCH.md:229-230`).
- Worst-of-two is a tuple `(bar rank, percent tenths, judge position)` (`:156`), so a tie has a defined winner. Spread is information only (`:164`).
- Refutations need finding id, location, command and output, and the id must belong to *that* judge's verdict (`:152`, `:224`). A borrowed finding id keeps counting. That is T-32-17 and D-04.
- Rounds are per loop: r1..r3 passes, r4 is over the cap, a gap is an error, and loop `32` does not add to loop `32.1` (`:222`). That matches D-03 rather than a lifetime count.
- `check` recomputes the judge count from `deterministic_count` and `final_count` and fails when `last_v4` drifts from `inputs.json` (`:226`, `:248`). A hand-edited count cannot survive a push.
- Judge ids are exact strings, and the file name must equal `judge_slug` (`:221`, `:247`). The invariant test greps the tool source for `referee` (`:229`).
- `--gate` and `--require-current` are already on the 32-01 parser (`32-01-PLAN.md:177`); 32-07 only starts honouring them. No new flag spelling to invent.
- Loading the checker by path from `check_dogfood.py` (`32-07-PLAN.md:276`) follows `_script` (`tools/check_dogfood.py:54-58`) and keeps tests from importing a `.planning` reader. The arch rule only flags path expressions, and the plan never writes the literal `.planning` into `judge_loop.py` (`32-07-PLAN.md:118`, acceptance grep at `:259`).
- Same-wave file split is clean: 32-05 edits skill text and the history test, 32-06 edits frontmatter tests and the runner, 32-07 is the only wave-3 editor of `AGENTS.md`, `README.md` and `tools/check_dogfood.py` (`32-07-PLAN.md:111`).

###### Concerns

- **HIGH — `judge_bar` treats "no findings" as the top clause and will contradict `validate_verdict`.** `judge_bar` returns `met: no critical or high finding` whenever no critical or high finding remains (`32-07-PLAN.md:154`). 32-01's validator rejects a below-max dimension with no finding (`32-01-PLAN.md:171`, `:209`). Those two only agree if every dropped point has a finding. A verdict that drops points on a medium finding and has no critical or high finding is legitimately `met: no critical or high finding` — that part is what JDG-04 says. The hole is the other way: the plan's 79.9 fixture "uses maxima of 125 per dimension, max_total 1000, total 799" (`32-07-PLAN.md:143`) and "one high finding". `make_verdict` in 32-01 creates one finding per dropped dimension (`32-01-PLAN.md:178`). A single high finding covering a 201-point drop is an invalid verdict under the below-max rule, so the bar test fails inside `validate_verdict` before `judge_bar` runs, or the executor weakens the validator. The fixture has to drop one point on one dimension (total 999 of 1000 is 99.9, not 79.9) or attach one finding to each dropped dimension and mark one of them high. Say which.

- **HIGH — the count recomputation calls `final_count` with `jev.level`, which is an int or null, while 32-04 stores the level only as a formatted note.** 32-07 says `final_count(deterministic_count(last_v4), jev.level, jev.note)` must equal the recorded `(count, reasons)` (`32-07-PLAN.md:248`). 32-04's `jev_level` returns `(index, "jev level {index} ...")` and `final_count` appends `: asks for two` to that string (`32-04-PLAN.md:215-216`). If `jev.level` in the record is the int and `jev.note` is already `...: asks for two`, feeding both back into `final_count` appends the suffix a second time and every jev-raised skill fails `check`. If `jev.note` is the short note, the recorded reasons from 32-04 (`from laya: asks for two`) do not equal the recomputed ones. The plan needs one sentence: the record stores `level` as the int and `note` as the *reason tail before* `: asks for two` / `: keeps one`, and `check` recomputes with those. As written, 32-08's real records will fail 32-09's `check` for the two skills that reach jev.

- **MEDIUM — `check_dogfood.main` cannot grow by two assignments and a call without a split, and 32-02 already added one.** `main` today is 19 body statements, 26 walked statements, 4 branches, 3 returns (`tools/check_dogfood.py:511-539`). Pylint's cap is 50 statements (`pyproject.toml:79`). 32-02 adds a JDG-04 pair (`32-02-PLAN.md:22`). 32-07 adds another pair plus the call (`32-07-PLAN.md:276`). Each pair is two assignments and one call expression; walked-statement count goes up by about six, still under 50. The branch cap (`max-branches = 12`, `pyproject.toml:77`) is safe. This is not a cap breach. It becomes one if 32-02's composition is written as an `if` per the research note that `main` must stay one-liners (`32-RESEARCH.md:347`). The plan should say: compose exactly like the edge-floor lines at `tools/check_dogfood.py:529-530`, two assignments, no new `if`. I am not calling this a defect; I am calling the "keep it a one-liner" instruction unstated, so a haiku executor who wraps it in `if judge_problems` will add a branch for no reason. Severity stays medium because the verify step runs pylint only on `judge_loop.py` (`32-07-PLAN.md:261`), not on `check_dogfood.py`. A branchy `main` ships green.

- **MEDIUM — `latest_loop` is "the highest-key folder under `verdicts/`" (`:151`), but the row's count and pool come from `loops/<loop>.json`.** A skill judged in `32` and again in `32.1` takes the `32.1` folder even when `32.1` has only a failed attempt and `32` holds the verdict. The plan says the latest loop's last round decides the bar (`:247`). SPEC R7 concurrency says a batch phase refreshes only its own rows. That is what you want, but a skill whose latest loop folder exists and contains no verdict becomes `not judged` and fails the default check, hiding the earlier good verdict. Say it: a loop folder with no verdict-bearing round does not count as latest. Otherwise 32.1's first failed attempt blanks the baseline row.

- **MEDIUM — the report reads `loops/<loop>.json` `counts` and `pool` with no schema check, while `check` only recomputes the count.** `render_report` prints `Why this many` straight from `counts[skill].reasons` (`:163`) and probe rows from `pool` (`:167`). A missing `counts` key is a `KeyError` inside `report`, not a `JudgeLoopError` naming the skill. `check` then cannot byte-compare because `render_report` raises first (`:248` says the byte compare stays last). A records folder that has verdicts and no loop file — the state 32-01's tests produce — makes `report` throw. The Task 1 fixture writes loop files (`:144`), so `TestReport` passes; `TestTracer` from 32-01 calls `check` on a records folder with no `loops/` and no `REJUDGE.md` (`32-01-PLAN.md:138`). 32-07 changes that `check` to require `REJUDGE.md` (`32-07-PLAN.md:171`) and to recompute counts (`:248`). The plan says to update `TestTracer`'s expected line (`:171`) but does not say to give the tracer fixture a loop file, `inputs.json` and a generated report. Without that, 32-01's tracer fails and the executor "fixes" it by weakening `check`. Name the fixture updates.

- **MEDIUM — digest cell versus digest state.** The report's Digest column is `digest[:12]` (`:164`). `check`'s line says `digest stale` or `digest current` (`:146`). Those are different facts, which is correct (Pitfall 7: current/stale must not be baked into the file). But the per-skill line in the behavior block is `digest stale` for zero digests (`:150`), while the report cell would show `000000000000`. The test has to assert both, or an executor will print the state word in the report and the byte-compare becomes unstable the moment 32-08 re-runs `check` after a skill edit. The plan does say this; the behavior block only shows the `check` line (`:150`). Add one assertion that the report cell is the hex prefix and does not contain `stale`.

- **LOW — `refuted_ids` matches on `location` being non-empty, not on the `path:line` shape.** D-04 asks for `path:line` (`32-CONTEXT.md` D-04). A refutation with `location: "yes"` counts (`32-07-PLAN.md:152`). Cheap to require one colon and a positive line number. Not a SPEC miss — SPEC R6 says "the finding id, `path:line`, the command and its observed output" (`32-SPEC.md` R6). Worth one regex.

- **LOW — excluded skills and judged skills can collide.** `render_report` sorts `inputs.json` skills and then excluded (`:163`, `:168`). `load_inputs` in 32-04 does not reject a name in both maps (`32-04-PLAN.md:202`). A duplicate would appear twice. Reject it in `load_inputs` rather than here.

- **LOW — README paragraph lists subcommands the tree does not have until 32-09, which is fine, but it also says `check` lives in `.planning/judge/`** (`32-07-PLAN.md:279`). `judge_loop.py` must not contain that string (`:259`). The README is allowed to. No conflict. Just do not let the executor "fix" the grep by deleting the README sentence.

###### Suggestions

- Specify the 79.9 fixture as eight dimensions at max 125, seven findings at the lost points, and exactly one of them `high`, with `total` equal to the sum. Do not use one finding for a 201-point drop.
- Write the `jev` record fields once, in 32-04's artifact list, as `{asked, level: int | null, note: <text without the asks-for-two suffix>, item}` and point 32-07's recomputation at that. Add a `TestCheck` case that round-trips a level-2 record through `final_count` and expects equal reasons.
- In the Task 1 action, list the 32-01 fixtures `check` now requires: `inputs.json`, `loops/32.json` with `counts` and `pool`, and a `REJUDGE.md` produced by `render_report` before the tracer's `check` call.
- Define `latest_loop` as the highest loop folder that contains at least one verdict.
- Compose `check_judge_records` in `main` as two assignments mirroring `tools/check_dogfood.py:529-530`, and add `tools/check_dogfood.py` to the pylint verify line (`32-07-PLAN.md:261` greps it but does not lint it).
- Assert the report digest cell is twelve hex characters and not the word `stale`.

###### Risk Assessment

**MEDIUM.** The report layout, the cap, the refutation gate and the byte compare will work if the executor transcribes them. The two HIGH items are contract mismatches with 32-04 and 32-01, and both show up only when `check` runs on real records in 32-09, after the lanes have already run. Fixing the contract in the plan is cheap; discovering it after a multi-hour judge run is not.

###### Ponytail findings

- **Needed.** SPEC R5, R6, R7 and the exact-string half of R3; CONTEXT D-03, D-04, D-06, D-07, D-12. The seven report sections are the SPEC R7 field list, not decoration.
- **Over-built, LOW.** `worst_record`'s tie break by judge position (`:156`) is one comparison and avoids a non-deterministic bar. Keep it. The probe-status table inside the report (`:167`) repeats `loops/<loop>.json`; D-06 says the report shows why that many judges ran, so the pool section stays.
- **Reuse.** `validate_verdict`, `skill_digest`, `judge_slug`, `record_path`, `CheckOptions` from 32-01 (`32-01-PLAN.md:171-177`). `load_inputs`, `deterministic_count`, `final_count` from 32-04. `check_edge_floors`'s `(problems, notes)` composition at `tools/check_dogfood.py:529-530`. The path loader copies `_script` at `tools/check_dogfood.py:54-58`. No new dependency.
- **Missed reach, MEDIUM.** `TestTracer` (`32-01-PLAN.md:138,178`) calls the `check` this plan rewrites, and the plan mentions its expected line (`32-07-PLAN.md:171`) but not the loop file and `inputs.json` that the rewrite requires. `tests/test_rules_docs.py` is in the verify command (`:284`) and is not modified here; 32-03 owns the AGENTS.md pins. 32-07's AGENTS.md edits are in the Testing and Commands sections (`:278`), which 32-03's doc-contract test does not pin (it pins the skill-judge bullet, `32-03-PLAN.md:36`). No collision, and `tests/test_agents_md_links.py` is in the verify list (`:284`) in case a new backtick path is a broken link. Good.
- **Pylint scope, LOW.** Task 2 lints `judge_loop.py` only (`:261`). `check_dogfood.py` is the file whose `main` is closest to the statement cap (`tools/check_dogfood.py:511`).

###### Executor notes

`render_report`'s layout (`32-07-PLAN.md:157-169`) is specific enough to transcribe. Two steps are not. First, "a max_total 1000 fixture" for 79.9 (`:143,149`) conflicts with 32-01's one-finding-per-dropped-dimension rule (`32-01-PLAN.md:171`); the executor has to invent a finding list. Second, `final_count(deterministic_count(last_v4), jev.level, jev.note)` (`32-07-PLAN.md:248`) does not say what `jev.level` and `jev.note` contain; 32-04 uses those names for a different pair (`32-04-PLAN.md:215-217`). That is a design choice, and the wrong one fails `check` on the baseline.

###### Same-wave

Wave 3 is 32-05, 32-06, 32-07.

- 32-05 edits `tests/test_skill_text_history.py` and skill Markdown (`32-05-PLAN.md:7-17`). No overlap with 32-07.
- 32-06 edits frontmatter tests, `tests/test_setup.py`, `tools/run_unittest_parallel.py`, `Makefile`, `.pre-commit-config.yaml` (`32-06-PLAN.md:7-13`). 32-07 does not touch those. 32-07's verify runs `tests.test_arch`, which imports neither.
- Both 32-05 and 32-06 depend only on 32-03. 32-07 depends on 32-04, 32-02 and 32-03 (`32-07-PLAN.md:6`). It reads 32-04's `load_inputs`, `deterministic_count`, `final_count` and the loop-file shape, 32-02's `check_jdg04_citations` in `main`, and 32-03's AGENTS.md bullet so it can insert sentences around it (`32-07-PLAN.md:278` says "in the bullet", and 32-03 is the plan that creates the three sentences). The AGENTS.md edit is an insertion into the Testing bullet and the Commands line, not into the skill-judge bullet 32-03 edits (`32-03-PLAN.md:36` versus `32-07-PLAN.md:278`). Depending on 32-03 is still right if 32-03's edit lands in the same Testing section; they edit different bullets, so a missing 32-03 would not make 32-07's patch fail. No missing dependency. No same-wave file overlap.

---

Skipped: did not run the suites or `make pyright`, and did not execute either plan. `tools/judge_loop.py` does not exist yet (32-01 is uncommitted on this branch), so the 32-01 citations are plan lines, not code. The jev and check-dogfood citations are the files on disk.

Risk: both HIGH items are contracts between plans. They pass each plan's own tests and fail when 32-08's real ladder output hits 32-07's `check`.

#### Batch D (32-08, 32-09)

##### Review: .planning/phases/32-re-judge-baseline/32-08-PLAN.md, 32-09-PLAN.md
###### Document Type
GSD · plan
###### Files Read
- `.planning/phases/32-re-judge-baseline/32-08-PLAN.md`, `32-09-PLAN.md`, `32-SPEC.md`, `32-CONTEXT.md`, `32-RESEARCH.md` (grounding)
- `32-01-PLAN.md`, `32-04-PLAN.md`, `32-07-PLAN.md` (the tool contracts these plans call; `tools/judge_loop.py` does not exist yet)
- `.planning/config.json:52-69`, `.claude/gsd-core/bin/gsd-tools.cjs:5076-5125`, `.planning/scripts/cross-ai.mjs:36,4454`, `skills/ai-kit-cross-ai/SKILL.md:50-54,103-172`, `tools/check_dogfood.py:511-539`, `agents/ai-kit-judge.md:1-10`, `29-JUDGE.md:82-99`, `15-skills-vs-new-judge.md:104-129`
- git: `16153d6` and `d2855bc` resolve and `git diff --numstat` against HEAD works, but neither is an ancestor of HEAD

###### CRITICAL
- **A failed lane is not a verdict, but the acceptance demands one anyway** — Location: `32-09-PLAN.md` must-have 2 and Task 1 step 3; `32-SPEC.md` edge row R7 empty; `32-07-PLAN.md:37,173`. Required: state what happens when a lane ends with a recorded failure and no verdict, and make the acceptance match it. Why: SPEC R7 says a skill with no finished verdict is reported "not judged" and "the checker run fails until a verdict exists". `32-07` records a skill with no records as `<skill>: no verdict records` and never says a record whose `verdict` is null fails `check`. `32-09` then requires `check --skills <15> --judges <the judges that ran> --require-current` to exit 0. The two readings give opposite outcomes: either the baseline cannot close whenever one of ~28 lanes dies (quota, auth, a truncated answer), or the SPEC acceptance is quietly dropped. `32-08` Task 3 step 4 allows one re-run, then stops. An executor cannot choose between failing the phase and overriding the spec.

- **The hard-tier wait loops forever and contradicts the skill it says it follows** — Location: `32-08-PLAN.md` Task 2 `work`. Required: one wait of exactly `retry_after_s` per `exit=75`, then stop that judge, as `skills/ai-kit-cross-ai/SKILL.md:137-139` and `:160-166` state. Why: the plan's loop is `exit=75` with `retry_after_s=` → sleep → run the same lane again, with no cycle cap. A lane that keeps returning 75 never ends, so Task 3's "until `lanes ended`" never arrives and the frozen-tree rule holds the whole checkout. Section 7 of the same skill answers abort, not retry, for every other non-zero exit, and says a later retry is the owner's. The plan also says "the worker follows `ai-kit-cross-ai`", so the two readings are opposite.

###### HIGH
- **`scope.py close` fails on the workers this plan starts** — Location: `32-08-PLAN.md` `<verification>` and `32-01-PLAN.md:112`. Required: exclude the plan's own detached workers from the close check, or run close only after they have exited and say which. Why: the rails copy `29-01-PLAN.md:105`, whose `close` fails on any process started after `start` whose cwd is this checkout. Task 1 starts probe children and Task 2 starts the lane workers, all with `cwd=ROOT`, and `start_new_session=True` keeps them alive after the executor returns. `32-08` then says the continuation executor runs `scope.py close` and expects `clean` last. It cannot be clean while those workers live, and the plan gives no step that reaps them.

- **`wait --max-seconds 170` can return before the probes finish** — Location: `32-08-PLAN.md` Task 1 step 3. Required: a wait budget that covers the probe it launches. Why: each probe is one `cross-ai.mjs` call with `--outer-timeout 600`, and the runner retries a dead model for about 200 s before `exit=75` (`32-RESEARCH.md:337`). The probe children are detached, so the 170 s cap measures nothing about them; it exits 3 while they still run. The instruction "repeat until `probes ended`, at most about 11 minutes" is the only bound, and a haiku executor has to invent the retry count.

- **The probe's "exact token echo" is not defined** — Location: `32-08-PLAN.md` must-have 2 versus `32-04-PLAN.md:119`. Required: one comparison rule. Why: `probe_result` compares `lane.out` stripped with the token stripped, so any surrounding text is `answer is not the sentinel`. `32-08` says "an exact token echo". A model that prints the token and a newline-terminated sentence fails one reading and passes the other. The plan should say the tool's comparison is the one that counts, so the executor does not add its own check.

- **`audit.py` rejects the report the tool generates** — Location: `32-09-PLAN.md` Task 2 versus `32-07-PLAN.md:138`. Required: match the report's real cells. Why: `render_report` writes a Lane status of the last attempt's `status_line`, else its `note`, and both can be empty, which the renderer turns into `-`. `audit.py` fails a `## Verdicts` row whose Score is not `not judged` unless Judge and Lane status are non-empty. A counted verdict with an empty status cell fails the audit even though `check` passed. The plan also never says how to tell a heading line from a data row, so the "exactly 15 data rows" count is the executor's guess.

- **`publish.py` has no answer for a record that appears after the copy** — Location: `32-09-PLAN.md` Task 1 step 1. Required: say what a destination that does not exist yet, and a second file that arrives after the copy starts, should do. Why: the copy refuses when a destination exists with different bytes, but the staging tree can still be changing: `32-08`'s workers call `ingest` until `all lanes ended`, and nothing asserts that state inside `publish.py` itself. A file written between the walk and the copy is silently missing from the commit, and `check` then reports `no verdict records` for that skill.

###### MEDIUM
- **The effort check drops a variable the research says matters** — Location: `32-08-PLAN.md` Task 1 `effort-env` versus `32-RESEARCH.md:86,341`. Required: also record `CLAUDE_CODE_AUTO_COMPACT_WINDOW`. Why: the research says the judging task repeats the check of three variables, because the env var overrides the frontmatter. The plan checks two and the acceptance asks for exactly two lines.

- **`count` re-asks jev for the two skills whose base commits are not ancestors** — Location: `32-08-PLAN.md` Task 1 step 2; `32-RESEARCH.md:312`. Required: record that `16153d6` and `d2855bc` are reachable only through `archive/phase-29.1-raw` and `archive/phase-29-raw`. Why: `git diff --numstat` against HEAD works today (verified: both resolve, both diffs print), so `count` will call jev, but a clone without those local tags takes the "jev input absent" path (`32-04-PLAN.md:168`). The plan never says the tags must be present, so the same inputs give different judge counts on another machine.

- **The frozen-tree window and the precondition disagree** — Location: `32-08-PLAN.md` Rails and Task 1 step 0. Required: one statement of when the freeze starts. Why: the rails say the freeze starts at Task 1 step 1, while step 0 writes `head.txt` and runs `scope.py`, and the precondition demands a clean tracked tree before that. `scope.py start` only reads, so it is safe, but an executor that treats step 0 as inside the freeze will refuse its own scratch writes.

###### Cross-Document Consistency
- `32-08` and `32-09` are different waves and share no file. `32-09` depends on `32-08` and reads its scratch, which is right. No same-wave plan exists for either.
- `32-09`'s `check` invocation matches `32-07`'s CLI (`--skills`, `--judges`, `--require-current`), and its judge list is "the sorted distinct `judge` values of every record", which is exactly the set `32-07` checks membership against.
- `32-08`'s `inputs.json` matches the research table (`32-RESEARCH.md:300-309`) and the old-score column (`15-skills-vs-new-judge.md:104-129`), including the four `no record found` rows and the goal-prompt override.
- The lane argv matches the real wrapper: `gsd-tools.cjs run-with-timeout <seconds> [--] <command>` at `.claude/gsd-core/bin/gsd-tools.cjs:5106`, and `--outer-timeout` is a real flag at `.planning/scripts/cross-ai.mjs:4454`.

###### Status: Issues Found — fix and re-invoke

##### 32-08

**Summary.** The plan is the right shape for the spec: probes, pool and counts come from the tool, lanes stay under `tmp/`, the tree is frozen, and native lanes are a separate orchestrator step. It breaks on the failure paths. The worker's quota loop never ends, the acceptance cannot be met when a lane dies, and the cleanup check flags the workers the plan itself starts.

**Strengths.**
- Judge ids are built from `.planning/config.json:52-69` at run time, and the plan writes none into code. That matches D-08 and the research warning that phase 29 ran the same referees through pi (`32-RESEARCH.md:66`).
- The lane command matches the installed wrapper. `run-with-timeout` takes `<seconds> [--] <command>` (`.claude/gsd-core/bin/gsd-tools.cjs:5106`) and exits 124 on expiry (`:5089`), and `cross-ai.mjs` has `--outer-timeout` (`:4454`).
- Scratch stays inside `tmp/`, which the runner treats as wholly ignored (`skills/ai-kit-cross-ai/SKILL.md:50-54`), so lane output cannot trip `tree=dirty`.
- The `inputs.json` content is copied from the research table, not invented: the seven v4 rows (`32-RESEARCH.md:302-308`) and the old scores (`15-skills-vs-new-judge.md:106-129`).

**Concerns.**
- **HIGH.** The `work` loop retries `exit=75` with `retry_after_s=` forever (`32-08-PLAN.md` Task 2). The skill it claims to follow waits once and then stops (`skills/ai-kit-cross-ai/SKILL.md:137-139,160-166`). A lane that keeps returning 75 holds the frozen tree indefinitely.
- **HIGH.** `scope.py close` fails while the detached workers live. The close rule counts any process started after `start` whose cwd is the checkout (`29-01-PLAN.md:105`), and the workers are spawned with `cwd=ROOT` and `start_new_session=True`. The verification expects `clean`.
- **HIGH.** `wait --max-seconds 170` is shorter than the 600 s probe it wraps, and the "about 11 minutes" cap is prose, not a number the executor can check.
- **MEDIUM.** "Exact token echo" (`32-08` must-have 2) is looser than `probe_result`, which compares the stripped stdout to the stripped token (`32-04-PLAN.md:119`).
- **MEDIUM.** `effort-env` records two variables; the research names three, including `CLAUDE_CODE_AUTO_COMPACT_WINDOW` (`32-RESEARCH.md:86`).
- **MEDIUM.** The two commits that reach the jev step, `16153d6` and `d2855bc`, are not ancestors of HEAD (verified: `merge-base --is-ancestor` exits 1). `git diff --numstat` works here only because the archive tags keep them. The plan never says those tags must exist.
- **LOW.** The freeze is said to start at Task 1 step 1, while step 0 writes files. Harmless, but the executor has to decide which sentence wins.

**Suggestions.**
- Cap the 75-retry at one wait, then mark that judge `failed: owner stop` and let Task 3's substitute step cover its remaining skills.
- Make `scope.py close` ignore the pids in `probe-*.pid` and `work-*.pid`, and run it only after `status` prints `all lanes ended`.
- Replace the 170 s probe wait with a budget above 600 s, and state the retry count as a number.
- Say the probe passes only when `probe_result` says `usable`, and drop the separate "echo" wording.
- Add `CLAUDE_CODE_AUTO_COMPACT_WINDOW` to `effort-env`, still printing only set or unset.
- Note that `count` needs the `archive/phase-29-raw` and `archive/phase-29.1-raw` tags, and that without them the two skills skip jev.

**Risk Assessment.** HIGH. The run is several hours and the failure path does not terminate, so one quota stop stalls the phase and the checkout.

###### Ponytail findings
- **Needed.** The probe, pool, count and ingest steps are SPEC R3, R4 and R7 and decisions D-05, D-08, D-09, D-10. Nothing here is a new feature.
- **Over-built, MEDIUM.** `lanes.py` re-implements the cross-AI exit table and the hard-tier wait instead of doing the one thing the skill says. The retry loop is the part to delete.
- **Reuse.** `probe_result` and `choose_pool` (`32-04-PLAN.md:119-120`) already decide usability; the plan should not add a second token check. `atomic_write_json` (`32-01-PLAN.md:172`) already covers the record writes.
- **Reach.** No code, test or doc changes, so no listings to update. The plan correctly leaves the publish to 32-09.

##### 32-09

**Summary.** Publishing the staging records byte for byte and generating the report is the right close, and the checker command matches the tool. The acceptance is wrong for the records it will actually receive: a skill whose lanes failed has no verdict, and both the spec and this plan require `check` to exit 0 anyway. The audit script also rejects a report the tool is specified to write.

**Strengths.**
- The copy refuses to overwrite different bytes and the report is regenerated, never edited. That keeps D-09's "one commit after the lanes" and the never-edit-a-raw-verdict rule.
- `check` is invoked with the flags `32-07` defines (`--skills`, `--judges`, `--require-current`), and the judge list is taken from the records rather than typed in.
- The commit is scoped to `.planning/judge/` and reviewed with `git diff --cached --stat` first, which matches the repo's commit rule.
- `check-dogfood` really does print `check-dogfood: ok` and prefixes every problem (`tools/check_dogfood.py:534-538`), so the verify command matches the tool.

**Concerns.**
- **CRITICAL.** The plan requires `check ... --require-current` to exit 0 for all 15 skills (`32-09` must-have 2, Task 1 step 3). SPEC R7 says a skill with no finished verdict fails the checker (`32-SPEC.md` edge row R7 empty), and `32-07` only fails a skill that has no record at all (`32-07-PLAN.md:173`), not one whose record has `verdict: null`. One dead lane makes the acceptance unsatisfiable, and the plan says "never edit a record", so the executor has no legal move.
- **HIGH.** `audit.py` demands a non-empty Lane status on every scored row. `render_report` writes `-` when both the status line and the note are empty (`32-07-PLAN.md:135,138`). A legal report then fails the audit.
- **HIGH.** `publish.py` refuses a destination that differs, but it never checks that the staging tree is still being written. `32-08`'s workers ingest until the last lane ends. A record created mid-copy is missing from the commit, and `check` then reports `no verdict records`.
- **MEDIUM.** The audit's "exactly 15 data rows" needs a rule for separating the heading, the separator and the rows. The plan leaves that parsing to the executor.
- **LOW.** The verify greps for `not judged` as a failure. The report's own bar cell is `not judged` for a failed skill (`32-07-PLAN.md:137`), so the grep and the report can disagree about whether that word is an error.

**Suggestions.**
- Decide the failed-lane case in the plan: either a skill with no verdict is an allowed "not judged" row and `check` must be specified to exit 0 for it, or the baseline stops and reports that skill to the owner. Point the SPEC row and the `32-07` check at the same sentence.
- Make the audit read the cells the renderer writes, and accept `-` as a lane status.
- Have `publish.py` abort unless `lanes.py status` ends with `all lanes ended`, and copy from a snapshot so nothing arrives mid-copy.

**Risk Assessment.** HIGH. The publish step is small, but its acceptance cannot pass on the records the previous plan produces when any lane fails, and lanes failing is the case the phase is built around.

###### Ponytail findings
- **Needed.** The publish, the generated report and the checker run are SPEC R7 and decisions D-06, D-07, D-11, D-12.
- **Over-built, LOW.** `audit.py` re-checks things `check` already proves (judge in the list, digest current). The one thing it adds, the row counts and the history-column check, is worth keeping; the lane-status rule is the part that fights the tool.
- **Reuse.** `judge_loop.py report` and `check` (`32-07-PLAN.md:144,179`) do the real verification. The audit should read their output instead of parsing the markdown itself.
- **Reach.** The commit covers `.planning/judge/` only, which is what D-06 asks. No test listing changes. The plan correctly leaves `make test` to the phase close in the orchestrator steps.

Skipped: did not run the suites or import `judge_loop.py`, because the review is read-only and that module does not exist yet. The tool's behavior is taken from plans 32-01, 32-04 and 32-07, so a later edit to those plans can move the line numbers cited above.

#### Batch E (32-06)

##### Review: `.planning/phases/32-re-judge-baseline/32-06-PLAN.md`
###### Document Type
GSD · plan

###### Files Read
- `.planning/phases/32-re-judge-baseline/32-06-PLAN.md` (218 lines)
- `32-SPEC.md` R8, `32-CONTEXT.md` D-17, `32-RESEARCH.md` Pitfalls 3–4, `32-PATTERNS.md`, `32-01-PLAN.md` rails
- `tools/setup.py` (`_front_scalar` 889, `_read_frontmatter` 908, `enumerate_entries` 966)
- `tests/test_setup.py` (25–35, 5476–5554), `tools/run_unittest_parallel.py:94`, `tests/test_staged_mapper.py:553`
- `tests/test_framework_profiles.py:1–31`, `tools/gen_test_groups.py:72–104`, `pyproject.toml` ruff/pylint
- `agents/ai-kit-judge.md:1–6`; all 23 `skills/*/SKILL.md` frontmatters plus the agent
- Wave-3 file lists in `32-05-PLAN.md` and `32-07-PLAN.md`
- Live probe: npm `yaml` 2.9.0 beside `skills` 1.5.20; PyYAML 6.0.3 `SafeLoader.construct_mapping`

###### HIGH
- **The SPEC continuation fixture is not a fixture.** Location: `32-06-PLAN.md:141` and `:148`–`:152`. Required: the label `colon on continuation line` has one full file string, and `node tmp/p32/06/yaml_compare.mjs` exits 0 on it. Why: SPEC R8 acceptance (`32-SPEC.md:124`) requires an unquoted `: ` on a continuation line whose result equals npm `yaml`. Research measured `description: a` plus `  second: bad` (`32-RESEARCH.md:360`). I parsed both shapes with the cached package (`yaml` 2.9.0, `skills` 1.5.20). `description: Use when: testing.` is rejected; `description: Use when\n  testing: now.` is also rejected, but the natural reading, `description: Use when\n  second: bad`, is accepted and folded to `"Use when second: bad"`. Task 2 step 5 exits 1 on any `DIFFERENT`. The only legal fixture text is therefore the colon-on-the-first-content-line form, and the plan never says that. A haiku executor cannot pick it without a design decision, and the wrong pick fails the plan's own verify.

###### MEDIUM
- **Most of the shared corpus is still prose.** Location: `32-06-PLAN.md:141`, `:148`. Required: every label has its full frontmatter text, folder, and expected gate and npm result. Why: only five cases have text (`colon on first line`, `non-string name`, `uppercase name`, `inline comment`, `empty description`, `no frontmatter`, `empty frontmatter`). `tab-indented line`, `unterminated quote`, `duplicate key`, `name differs from folder`, `double hyphen`, `leading hyphen`, `trailing hyphen`, and every accepted block fixture are left for the executor to invent. The npm script then treats that invention as the recorded comparison.

###### LOW
- **The PyYAML recipe flattens twice.** Location: `32-06-PLAN.md:149`. Required: no change if the fixtures stay free of merge keys; otherwise call `flatten_mapping` only through `super()`. Why: PyYAML 6.0.3 already calls `self.flatten_mapping(node)` at the start of `SafeLoader.construct_mapping`. A second call before `super()` accepted a folded block, an explicit `!!str` tag, and a duplicate key in a probe. A merge key (`<<:`) is flattened twice but still loaded. Harmless for this corpus.

###### Non-blocking notes
- No same-wave file overlap. `32-05` edits history text and references; `32-07` edits `judge_loop.py`, `check_dogfood.py`, `AGENTS.md`, and `README.md`. Only `32-06` touches `Makefile`, `.pre-commit-config.yaml`, and `tools/run_unittest_parallel.py`. `depends_on: [32-03]` is a wave dependency, not a file dependency.
- The current tree passes the planned subset: 23 skills plus `agents/ai-kit-judge.md`, shapes plain, double-quoted, `>`, and `>-`, zero problems. `tools: Read, Grep, Glob` is legal because the indicator check is the first character only.
- `sorted(UNIT_UV_MODULES)[0]` stays `tests.test_framework_profiles` (`tests/test_staged_mapper.py:553`). Pylint does not cover `tests/` (`.pre-commit-config.yaml:30–31`), so the large parser does not trip the 12-branch limit. Ruff still does: `parse_strict` needs helper functions.
- `enumerate_entries` also returns commands (`tools/setup.py:44`, `:966`). There is no `commands/` directory today. The plan's `agent_problems` path covers one if it appears.
- The npm cache is present on this machine, so the missing-cache branch is a fallback, not the expected result.

###### Status: Issues Found — fix and re-invoke

##### 32-06

###### Summary

The plan covers SPEC R8 and D-17: a stdlib frontmatter gate over every installable entry, the two old guards removed, a PyYAML cross-check in `unit-uv`, and one recorded npm `yaml` comparison. The parser, entry walk, listings, and wave boundaries are concrete and match the code. It is not executable as written because the fixture that proves agreement with the skills CLI has no canonical text, and one natural reading makes the comparison exit 1.

###### Strengths

- `parse_strict` has an ordered rule list, exact error strings, and the three folding examples Task 1 asserts (`32-06-PLAN.md:114`).
- It reuses `setup.enumerate_entries` (`tools/setup.py:966`) and the `load_module` pattern (`tests/test_setup.py:25–35`) instead of a second file walk. It does not reuse the lossy `_read_frontmatter` (`tools/setup.py:908`).
- The two replaced tests are real and at the cited lines (`tests/test_setup.py:5524` and `:5538`). `_REPO_ROOT` stays in use at `tests/test_setup.py:7292`.
- `gen_test_groups.py` is the existing listing writer (`tools/gen_test_groups.py:72–104`). The unit-uv name sorts after `tests.test_framework_profiles`.
- No overlap with `32-05` or `32-07`. Shared-machinery cost is named and kept to the commits that need it.
- The live tree already satisfies the gate, including the judge agent's comma-separated `tools` line.

###### Concerns

- **HIGH — continuation fixture is unspecified and one reading fails npm `yaml`.** `32-06-PLAN.md:141`. SPEC R8 (`32-SPEC.md:124`) and the verify command at `32-06-PLAN.md:161` require the fixture's result to equal npm `yaml` 2.9.0. A continuation whose first content line contains `: ` is rejected; a later `key: value` continuation is accepted. The plan gives neither string.
- **MEDIUM — the rest of `FIXTURES` is named, not specified.** `32-06-PLAN.md:148` says to add them "exactly as the behavior block lists," but that block has labels, not bodies, for the tab, quote, duplicate-key, hyphen, and block cases. The scratch comparison records whatever the executor writes.
- **LOW — duplicate `flatten_mapping`.** `32-06-PLAN.md:149` repeats work `SafeLoader.construct_mapping` already does in PyYAML 6.0.3. Safe for the planned fixtures; wrong for a merge key if one is ever added.

###### Suggestions

- Pin `colon on continuation line` to a full string whose first content line contains `: `, for example `description: Use when: testing.\n  more.\n`, and state that a later `key: value` line is not this fixture.
- Give every other label its full `---\n...\n---\n` body in the behavior block, including which line holds the tab and which scalar is unterminated.
- Drop the extra `flatten_mapping` call, or add the comment that PyYAML 6.0.3 already flattens inside `super()`.

###### Risk Assessment

**MEDIUM.** The gate design and the current tree agree, and the wave can run beside `32-05` and `32-07`. The comparison step can still fail after a faithful implementation because the one fixture SPEC R8 adds beyond D-17's designed-stricter pair has two opposite YAML outcomes.

###### Ponytail findings

- **Needed.** SPEC R8 and locked D-17 require both layers, the fixture comparison, and removal of the two guards. No extra option or config was added.
- **Reuse is right.** `enumerate_entries` (`tools/setup.py:966`), `load_module` (`tests/test_setup.py:25`), `json.loads` (`tools/setup.py:900`), and `gen_test_groups.py` are the existing pieces. A new strict parser is required because `_read_frontmatter` folds and accepts shapes the gate must reject.
- **LOW — the second parser is the locked design, not extra flexibility.** D-17 explicitly asks for a stdlib subset plus an independent PyYAML loader. Collapsing them would not meet the decision.
- **Reach.** Both generated listings, `UNIT_UV_MODULES`, and the staged-mapper sort are in the plan. No README change belongs here. `32-01` updates the judge row; `32-07` updates the checker docs.

Skipped: did not run the test suite or `make` targets, and did not import PyYAML's merge-key behavior beyond the one probe. Risk: the review found no second continuation shape that satisfies both the plan's label and npm `yaml`.

### Consensus Summary

Only one reviewer ran, so no finding can be agreed or disputed across reviewers. referee-two's findings were weighed
against the source instead (Triage below). The review carries no `[reviewed-without-repo-access]` or
`[reviewed-without-source-citations]` marker: every batch read the repository and cites `path:line` evidence.

#### Agreed Strengths

None across reviewers (one reviewer). These strengths referee-two named were also confirmed by the orchestrator:

- 32-01 reuses the phase 27 validator, `grade_of` and `parse_status_line`, and takes the module list from
  `staged_mapper.covering_modules`.
- 32-03 and 32-05 have exact edit lists. Simulating their regexes over the tree reproduces their hit lists exactly.
- 32-04 does the band test in integer tenths.
- 32-07's report is a pure function of the records, compared byte for byte.
- 32-06 reuses `setup.enumerate_entries`, and the live tree already fits its strict subset.

#### Agreed Concerns

None (one reviewer).

#### Divergent Views

The orchestrator's source check diverged from referee-two on all 18 unique HIGH or CRITICAL labels:

- 16 were refuted with evidence; three of those leave a lower-severity residual (A1 to L5, A3 to M2, D1 to M3).
- 2 were downgraded: C11 to MEDIUM (M2) and C12 to LOW (L3).

### Triage (orchestrator, 2026-11-07)

18 unique HIGH or CRITICAL labels were raised. None is confirmed at HIGH, so 0 HIGH remain. The confirmed findings are
3 MEDIUM and 5 LOW, listed with the plan change each still needs. Every other finding is listed under "Rejected or
not actionable" with the evidence that refutes it.

#### Confirmed HIGH

None.

#### Confirmed actionable (MEDIUM and LOW)

- **M1 (C15) MEDIUM, 32-07: the 32-01 tracer test breaks when `check` is rewritten.** 32-07 makes `check` require
  `REJUDGE.md` (32-07-PLAN.md:145), a count record in `loops/<loop>.json` and `inputs.json` (32-07-PLAN.md:184). But
  32-01's `TestTracer` runs `check` on a records folder that has none of them and expects exit 0 twice: once with
  `digest current`, once with `digest stale` (32-01-PLAN.md:138). 32-07 only says to update the tracer's expected
  line (32-07-PLAN.md:95, :145). Also, `render_report` reads `counts[skill]` with no guard. A records folder without
  a count record therefore raises `KeyError` inside the byte compare instead of a named problem.
  Change: in 32-07, extend the tracer fixture with:
  - `inputs.json` (demo-alpha with a batch, `last_v4` null, `old_score` null, `excluded` empty);
  - `loops/32.json` holding `pool` and a `counts` entry equal to `deterministic_count(None)`;
  - a `report` run before each `check` call.

  Have `render_report` raise `JudgeLoopError` naming the skill when its count record is missing.
- **M2 (C11, with the A3 residual) MEDIUM, 32-01 and 32-07: the boundary fixtures do not say which dimensions lose
  points, and one fixture cannot exist.** `validate_verdict` rejects negative scores (copied from the phase 27
  checker, `check_verdicts.py:46-50`). It also requires a finding for every dimension below its max
  (32-01-PLAN.md:171). So each of these fixtures needs drops across at least two dimensions:
  - 80.0 and 79.9 on maxima of 125 (32-01-PLAN.md:209; 32-07-PLAN.md:120, :123);
  - 80.0 on the default 125-point maxima (32-07-PLAN.md:121);
  - 78.4 (32-07-PLAN.md:170).

  The fixture "two judges at 90.0 (no findings)" (32-07-PLAN.md:170) is impossible. No findings means every score at
  its max, which is 100.0, and 90.0 cannot be reached at all on the default maxima.
  Change: give each fixture its exact `make_verdict` call (maxima and drops with severities). For example:
  - 79.9: maxima 125 each, drops `{"D1": (125, "high"), "D2": (76, "medium")}`;
  - 80.0 with one high on the default maxima: drops `{"D1": (20, "high"), "D2": (5, "medium")}`.

  Reword the 90.0 judge as "90.0 with no critical or high finding", on maxima of 125 each.
- **M3 (X2, residual of D1) MEDIUM, 32-07: no checker test for a skill that has no verdict.** SPEC R7's empty edge
  says the checker run fails until a verdict exists (32-SPEC.md:222). That rule is a 32-07 must-have
  (32-07-PLAN.md:37). But Task 2's behavior list, from which one test per line is written, has no case for a skill
  whose last round holds only failed attempts (32-07-PLAN.md:164-174). TestReport checks only the report cell.
  `check` runs on every push in later phases, so a regression here would let a not-judged skill pass.
  Change: add a TestCheck line stating that such a skill is the problem
  `<skill>: not judged (no verdict in loop <L> round <N>)` and that `check` exits 1 in default mode. Also name
  `not judged` in 32-09 Task 1 step 3's stop sentence, beside a stale digest and a mismatch (32-09-PLAN.md:92).
- **L1 (A4) LOW, 32-01: the interim `check` does not say what to do with an empty verdict.** It validates every record
  of the round (32-01-PLAN.md:176) without saying that a record whose `verdict` is null is skipped for validation and
  for the summary line. Only a round with no verdict at all is "not judged".
  Change: one clause in Task 1's `check` description.
- **L2 (C6, C18) LOW, 32-04: `load_inputs` accepts a name in both maps.** It does not reject a skill name present in
  both `skills` and `excluded` (32-04-PLAN.md:158). Such a skill would appear twice in the report.
  Change: one validation line with a TestCount case. Also say that `count` iterates `inputs["skills"]` only.
- **L3 (C12 residual) LOW, 32-04 and 32-07: the count record's `jev` contract is implicit and untested.** 32-07's
  recomputation (32-07-PLAN.md:184) relies on `jev.level` (int or null) and `jev.note` (the note passed to
  `final_count`, without the `: asks for two` or `: keeps one` suffix). 32-04 implies that contract but never states
  it (32-04-PLAN.md:168), and no test round-trips a `count_skill` result through `check`.
  Change: one sentence in 32-04's count record description. Plus one TestCheck case that writes a `count_skill`
  result with a fake jev level-2 answer into the loop file and expects `check` to accept it.
- **L4 (D8) LOW, 32-08: `effort-env` records two variables, the research names three.** The research says to repeat
  the check of `CLAUDE_CODE_EFFORT_LEVEL`, `CLAUDE_CODE_SUBAGENT_EFFORT` and `CLAUDE_CODE_AUTO_COMPACT_WINDOW`
  (32-RESEARCH.md:86). `effort-env` records two (32-08-PLAN.md:24, :97), and its acceptance expects two lines (:122).
  Change: add the third, still printing set or unset only, and expect three lines.
- **L5 (X1, residual of A1) LOW, 32-01 and 32-04: the probe proves a judge read the end of the prompt, not the
  middle.** The token sits after the last END marker (32-01-PLAN.md:214), as in the research recipe
  (32-RESEARCH.md:119, :418-423). A lane whose context drops the middle of the ~92 KB package would still pass, then
  judge without the rubric. That is the failure the CONTEXT deferred item guards against ("a lane whose answer shows
  a truncated rubric is not counted").
  Change (cheap hardening, within the discretion over the probe wording): put one token after each embedded file's END
  marker; the expected reply is all tokens in order, and `probe_result` compares the joined tokens.

#### Rejected or not actionable

Batch A (32-01, 32-02):

- **A1 (CRITICAL, HIGH) 32-01, probe order.** Refuted. The research recipe appends the sentinel after the package and
  then the instruction (32-RESEARCH.md:119, :418-423), the same order as 32-01 (32-01-PLAN.md:214). Residual: L5.
- **A2 (HIGH, plus a ponytail MEDIUM) 32-01, prompt equality versus the D7 split.** Refuted. Rule 5 is one fixed
  sentence stating both splits (32-01-PLAN.md:165). SPEC R2 says only the skill name and the module list vary
  (32-SPEC.md:93-94). The judge applies rule 5 by reading the skill folder, and the manifest records `ships_code`.
- **A3 (HIGH) 32-01, 125-point maxima rejected.** Refuted. The copied validator checks only that `max` holds eight
  non-negative integers and that the sums match (`check_verdicts.py:46-60`). It never compares the maxima with the
  rubric's. Residual (unspecified drops): M2.
- **A5 (LOW) 32-01, `main` lint size.** Refuted. The rails require splitting helpers inside the limits
  (32-01-PLAN.md:113), and pylint runs at commit on `tools/` (.pre-commit-config.yaml:26-32).
- **A6 (CRITICAL, HIGH) 32-02, Progress and Backlog scanned.** Refuted. The scan stops at the next `## ` heading after
  `## Phase Details`, which is `## Progress` (ROADMAP.md:886). A simulation of the exact rule on the live file
  (`tmp/p32-review/sim_jdg04.py`) checked the 25 phases above 32 that name SKILL.md and found 0 offenders.
- **A7 (MEDIUM) 32-02, unanchored criteria marker.** Refuted. The substring `**Success Criteria**` matches the real
  line (ROADMAP.md:397), and the simulation found no false hit.
- **A8 (MEDIUM) 32-01 and 32-02, function size.** Refuted. 32-02 names `_phase_blocks` and `_criteria`
  (32-02-PLAN.md:111), 32-07 names the checker split (32-07-PLAN.md:179), and the commit hook lints `tools/`.
- **A9 (LOW) 32-02, fixture versus live.** Refuted with A6. The verify step runs `make check-dogfood` on the live tree
  (32-02-PLAN.md:119).

Batch B (32-03, 32-05):

- **B1 (HIGH, with the duplicates B4 and B6) 32-03 and 32-05, the version rule on `decision-table.md`.** Refuted.
  `history_hits` reads only each kept skill's SKILL.md (32-03-PLAN.md:123), and `version_hits` runs on its main flow
  (:159). 32-05 widens only `pointer_hits` to the other shipped Markdown (32-05-PLAN.md:132). Simulating the exact
  rules (`tmp/p32-review/sim_history.py`) gives 13 main-flow hits, exactly 32-03's list (32-03-PLAN.md:86).
- **B2 (MEDIUM) 32-03, fence asymmetry stated only in fixtures.** Refuted. It is stated in the must-have
  (32-03-PLAN.md:32) and in the action (:159), and it comes from SPEC R9 (32-SPEC.md:236).
- **B3 (LOW) 32-03, the dependency on 32-01.** Refuted. Both plans add a test module and regenerate `Makefile` and
  `.pre-commit-config.yaml`, which must not share a wave (32-01-PLAN.md:91).
- **B5 (HIGH, with the duplicate B9) 32-05, reference files fail the date rules.** Refuted. The main-flow rules stay
  on SKILL.md, and only the pointer rules read other shipped Markdown (32-05-PLAN.md:101, :132). That is SPEC R9's
  split (32-SPEC.md:128; interview S7 at :284). The simulation found 24 pointer hits: exactly 32-05's list
  (32-05-PLAN.md:70) plus the 18.1 pointer that 32-03 removes. The 73 dated lines in reference files are unchecked
  by design.
- **B7 (MEDIUM) 32-05, a range counts as two ids.** Refuted. Each id is a hit by design, and the plan replaces the only
  range with placeholders (32-05-PLAN.md:134).
- **B8 (LOW) 32-05, the backlog title is deleted rather than moved.** Refuted. D-19 says the backlog id and `(D-07)`
  go (32-CONTEXT.md:199), and the pointer rules also cover evidence sections (32-05-PLAN.md:29).

Batch C (32-04, 32-07):

- **C1 (HIGH) 32-04, `jev_level` reads a field the ladder never writes.** Refuted. `typed_answer` maps a score item's
  `level` to the level text and returns it as `choice` (jev_ladder.py:500-511). That is the field `jev_level` reads,
  and the plan's fake returns the same shape (32-04-PLAN.md:148).
- **C2 (HIGH) 32-04, `decided_by` versus the low-confidence flag.** Refuted. `fill_columns` names a backend only for a
  column with `choice` and `fallback is False` (jev_ladder.py:533-541). Otherwise it reports `own_reasoning`, which
  the plan keeps at one judge (32-04-PLAN.md:166).
- **C3 (MEDIUM, with the duplicate C10) 32-04, `--client` not forwarded.** Refuted. `find_jev_client` returns
  `jev_review.py` itself (`JEV_ENTRY_REL`, 32-01-PLAN.md:146; 32-04-PLAN.md:164), which `ladder` runs as the
  program. The ladder finds its inner client through the same skills-roots lookup (jev_ladder.py:116-128). Tests
  replace the whole program with a fake.
- **C4 (MEDIUM) 32-04, `final_count` composition.** Refuted. `jev_level`'s note plus `: asks for two` is exactly the
  pinned reason (32-04-PLAN.md:148, :166-167), and `det` is `deterministic_count`'s `(count, reasons)` tuple (:159).
- **C5 (MEDIUM, with the ponytail C9) 32-04, `percent_words` bands.** Refuted. The cuts are exact (32-04-PLAN.md:160)
  and the three examples agree with them (:146). D-05 asks for fixed word bands and leaves their wording to
  discretion (32-CONTEXT.md:84-93, :229).
- **C7 (LOW) 32-04, `lane_ok` exactness.** Withdrawn by the reviewer ("Not a gap").
- **C8 (LOW) 32-04, `numstat` ignores uncommitted edits.** Not a concern for this phase. D-09 freezes a clean,
  committed tree for the run (32-CONTEXT.md:118-121).
- **C12 (HIGH) 32-07, count recomputation adds the suffix twice.** Refuted as stated. 32-04 stores the note it passes
  to `final_count` (32-04-PLAN.md:168), so recomputation reproduces the stored reasons. Residual: L3.
- **C13 (MEDIUM, with C21) 32-07, `main` composition and pylint scope.** Refuted. 32-07 gives the two assignments
  (32-07-PLAN.md:216), and pylint runs at commit on `tools/` (.pre-commit-config.yaml:26-32).
- **C14 (MEDIUM) 32-07, a later loop holding only a failed attempt.** Refuted. SPEC R7 requires exactly that the
  checker fails until a verdict exists (32-SPEC.md:222). Records are published only after every lane ends (D-09),
  and phase 32 runs one loop.
- **C16 (MEDIUM) 32-07, assert on the digest cell.** Not actionable. The layout already defines the cell as
  `digest[:12]` (32-07-PLAN.md:137).
- **C17 (LOW) 32-07, shape of the refutation location.** Refuted. The plan matches D-04: all four fields must be
  non-empty (32-CONTEXT.md:77-79).
- **C19 (LOW) 32-07, the README sentence.** The reviewer states there is no conflict.

Batch D (32-08, 32-09):

- **D1 (CRITICAL) 32-09, a failed lane versus the acceptance.** Refuted as stated. 32-07 keeps SPEC R7's empty edge
  in its must-haves (32-07-PLAN.md:37), 32-01's `check` reports `not judged` (32-01-PLAN.md:176), and 32-09's verify
  fails on `not judged` (32-09-PLAN.md:98). After that, the rails say stop and report (32-01-PLAN.md:99). Residual:
  M3.
- **D2 (CRITICAL) 32-08, the hard-tier wait loops forever.** Refuted. The runner counts hard-tier cycles and ends the
  episode with `stopped=hard-waits` or `stopped=cap`, an exit-69 owner stop (ai-kit-cross-ai SKILL.md:110, :116-120,
  :141-149). The worker already treats exit 69 as a judge stop (32-08-PLAN.md:138). One wait per exit 75 with
  `retry_after_s` is the skill's own rule (SKILL.md:137-139).
- **D3 (HIGH) 32-08, `scope.py close` versus the workers.** Refuted. `close` counts only live processes
  (29-01-PLAN.md:105). It runs after `status` prints `all lanes ended`, which requires no live worker
  (32-08-PLAN.md:139, :207).
- **D4 (HIGH) 32-08, the wait budget is shorter than a probe.** Refuted. The 170 s wait repeats until it prints
  `probes ended` (32-08-PLAN.md:112), and each probe is bounded by `run-with-timeout` at 660 s (:98).
- **D5 (HIGH; MEDIUM in its plan section) 32-08, "exact token echo" wording.** Refuted. Usability is decided by
  `judge_loop.py pool` (32-08-PLAN.md:20, :103), and no second check is specified.
- **D6 (HIGH, with D11) 32-09, the audit rejects a `-` lane status; row parsing.** Refuted. A verdict record's last
  attempt always carries either a status line or the native note. External lanes need a usable status line to record
  a verdict (32-01-PLAN.md:215); native lanes carry the note (32-08-PLAN.md:142). Ingest appends nothing after a
  verdict. Counting the table rows after the separator row is a standard parse.
- **D7 (HIGH) 32-09, `publish.py` races the workers.** Refuted. The precondition is `all lanes ended`
  (32-09-PLAN.md:84), which requires no live worker and every native lane ingested (32-08-PLAN.md:139).
- **D9 (MEDIUM) 32-08, base commits reachable only through archive tags.** Refuted. 32-04 records `jev input absent`
  for an unresolvable base (32-04-PLAN.md:23, :163), and `check` recomputes from the recorded answer
  (32-07-PLAN.md:184). So the committed baseline reproduces on any clone.
- **D10 (LOW) 32-08, the freeze window.** Refuted. Step 0 writes only under `tmp/`, which the freeze allows
  (32-08-PLAN.md:82).
- **D12 (LOW) 32-09, the `not judged` grep.** Refuted. The grep reads the checker's output lines (32-09-PLAN.md:98),
  and a not-judged skill must fail the baseline (32-SPEC.md:222).
- **D13 (ponytail MEDIUM) 32-08, the retry loop is over-built.** Refuted. D-08 makes the run a plan task that follows
  ai-kit-cross-ai (32-CONTEXT.md:110-117), and the loop is that skill's section 6 rule.
- **D14 (ponytail LOW) 32-09, the audit repeats checks.** Not a defect. The reviewer keeps the row counts and the
  history check it adds.

Batch E (32-06):

- **E1 (HIGH) 32-06, the continuation fixture.** Refuted. npm `yaml` 2.9.0, beside `skills` 1.5.20, rejects
  `description: Use when` followed by an indented `second: bad` line ("Nested mappings are not allowed in compact
  mappings"; probe `tmp/p32-review/yaml_probe.mjs`), as the research measured (32-RESEARCH.md:360). The gate rejects
  every plain continuation line, so the fixture compares `same`. The reviewer's own probe trace shows repeated
  require-path errors.
- **E2 (MEDIUM) 32-06, fixtures named without full text.** Refuted. Each label fixes the expected outcome
  (32-06-PLAN.md:141), and the research measured those shapes with both parsers (32-RESEARCH.md:360). Writing a
  fixture text is transcription, not a design decision.
- **E3 (LOW) 32-06, double `flatten_mapping`.** Refuted. The first flatten serves the duplicate check across merged
  keys (32-06-PLAN.md:149), and the parent's second flatten is then a no-op. The reviewer's own probe found it
  harmless.

### Verification coverage

#### Source-grounding pass (authority: grep)

`drift-guard authority --raw` returned `grep`. `drift-guard severity` gives, per verdict:

- VERIFIED: none;
- MISSING: needs-acknowledgement, no hard block;
- AMBIGUOUS: MEDIUM;
- UNCHECKABLE: INFO.

611 cited symbols were enumerated across the nine plans: paths, CLI flags and code names from inline code spans, plus
paths and flags inside fenced blocks (`tmp/p32-review/grounding.py`).

- 265 excluded: every symbol a phase 32 plan lists under "Artifacts this phase produces", plus each plan's own new
  files.
- 147 VERIFIED: the path exists, or the name has a declaration form in tracked source (`def`, `class`, an assignment,
  `add_argument`, a JSON key).
- 156 MISSING. Each is acknowledged and classified (`tmp/p32-review/grounding_classify.py`, 0 unclassified). None is
  a missing reference to existing code:
  - 30 synthetic fixtures that tests build in temp dirs;
  - 29 scratch paths the plans create (`tmp/p32/...`, and the `RUN/`, `RECORDS/`, `D/` placeholders of the run
    scripts);
  - 26 new names: test names; record and inputs keys such as `old_score`, `judged_at` and `native_note`; the run
    script's `--max-seconds`; `audit.py`; and the records layout `verdicts/`, `refutations/32.json`,
    `.planning/judge/`;
  - 13 phase files written later (SUMMARY, VERIFICATION);
  - 34 generic tokens (file extensions, bare `scripts/` and `evals/`, path suffixes);
  - 6 skill-relative paths, verified on disk: `references/launch-and-wait.md` (cross-ai); `references/log-formats.md`,
    `references/decision-table.md` and `references/worked-examples.md` (spec-discuss); `backends/laya.md` and
    `backends/typesafe.md` (jev);
  - 4 installed skill-judge entries, verified on disk outside the repo: `references/`, `references/rubric.md`,
    `references/verdict.schema.json`, and the schema key `max_total`;
  - 2 npx-cache paths, verified by the yaml probe outside the repo: `node_modules/yaml/package.json` and
    `node_modules/skills/package.json`;
  - 6 external names, not repository source: PyYAML `SafeLoader`, `yaml.YAMLError` and
    `yaml.constructor.ConstructorError`; Node's `module.createRequire`; Claude Code's `CLAUDE_CODE_EFFORT_LEVEL` and
    `CLAUDE_CODE_SUBAGENT_EFFORT`;
  - 5 pointer and referee examples the plans remove or use as failing fixtures: `.planning/phases/18.1-...`,
    `.planning/phases/21.1-...`, `18.1-one-runtime-model/`, `router-env/`, `router-env/my-referee-two`;
  - 1 replaced name: `--judge-dir`. 32-01 uses `--judge-package` instead, under the CONTEXT discretion over flag
    spellings.
- 8 AMBIGUOUS, each resolved by inspection:
  - bare `SKILL.md` (5) and `__init__.py` (1) are generic references to every skill;
  - `jev_review.py` resolves to `skills/jev-fast-decision/scripts/jev_review.py`; the other copies are archived
    scratchpads under `.planning/docs/`;
  - `22-INTERACTIVE-PI.md` is a pointer that 32-05 removes.
- 35 UNCHECKABLE (placeholders or globs, by design):
  - 32-01: `tests/test_*.py`, `tests/skills/<name>/`, `tests/<stem>.py`, three `<tmp>/...` fixture paths,
    `skills/<name>/`, `skills/<skill>/SKILL.md`;
  - 32-02: `test_*.py`, `tests/skills/<name>/`;
  - 32-03: `skills/*/SKILL.md`;
  - 32-04: `<r>/loops/32.json`;
  - 32-05: `.planning/phases/<phase>/`, `.planning/phases/**/*-CONTEXT.md`, the `PHASE_DIR_RE` pattern;
  - 32-06: `skills/*/SKILL.md`, `<HOME>/.npm/_npx/`;
  - 32-07: `<records>/REJUDGE.md`, `loops/*.json`, `verdicts/**`, `refutations/*.json`, `refutations/<loop>.json`,
    `loops/<loop>.json`, `*.json`;
  - 32-08: six `<DIR>/`, `RUN/` and `RECORDS/` placeholder paths;
  - 32-09: three `tmp/p32/judge/` globs and two `RUN/*.pid` globs.
- Signature claims (the argument shapes of planned and existing functions) are UNCHECKABLE under grep. Every reviewer
  claim about existing code was checked by hand and is recorded in the Triage.

#### Cross-artifact fact-drift pass

- **Phase status:** `drift-guard phase-status --phase 32` returned `lag` (STATE.md "Ready to execute", ROADMAP.md "Not
  started", one lifecycle step apart). Not a finding.
- **Success criteria versus must-have truths: one advisory drift.** ROADMAP Phase 32 criterion 3 (ROADMAP.md:400)
  still says two judges run "when the last verdict sat within judge noise of a grade boundary". The other artifacts
  read "a grade boundary" as the bar's pass boundary at 80, so two judges run from 73.0 to 87.0:
  - REQUIREMENTS JDG-06 (REQUIREMENTS.md:151-156), confirmed by the owner on 2026-11-07;
  - SPEC R4 (32-SPEC.md:103);
  - plan 32-04's must-haves (32-04-PLAN.md:22, :29).

  D-22 amended JDG-06 but not criterion 3. Authority: ROADMAP.md for success criteria, but the owner's confirmed
  reading post-dates that wording, so the fix is to add JDG-06's amendment note to criterion 3. Advisory: counted in
  neither the HIGH total nor the actionable total.
- **Requirement IDs versus plan requirements:** consistent. ROADMAP lists JDG-01, 02, 04, 05, 06, 07 and 08, which
  equals the union of the nine plans' `requirements`.
- **Glossary versus plan usage: no contradiction.**
  - `--judge-package` replaces D-13's `--judge-dir` under the discretion over flag spellings.
  - The sentinel probe asks for a one-word reply, within D-08 and the discretion over the probe wording.
  - D-11 numbers three waves while the plans use five. Wave numbering is not one of this pass's fact classes, and the
    order D-11 protects still holds: every SKILL.md edit before the run, the records after it.
- **Coverage:** STATE.md, ROADMAP.md, REQUIREMENTS.md and 32-CONTEXT.md were all present, so no axis was skipped.
