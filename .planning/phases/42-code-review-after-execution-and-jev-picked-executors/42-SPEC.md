# Phase 42: Code review after execution and jev-picked executors — Specification

**Created:** 2026-11-23
**Ambiguity score:** 0.24 (gate: ≤ 0.20) — gate missed by 0.04; every dimension meets its minimum; written flagged at the owner's choice
**Requirements:** 8 locked

## Goal

After the superpowers adapter executes a plan, a capped code-review loop runs on the same review lanes as spec review with
`ponytail-review` (and `impeccable` for a UI diff), jev classifies lane results and gray areas before the loop continues or the
owner is asked, jev picks the executor from the owner's roster (and a lite executor gets a lite block in the plan-writer brief),
and each lane's transport (subprocess, resumed session or herdr pane) is chosen from what a recorded spike verified, reused within
a plan and renewed after a set number of rounds.

## Background

Requirements EXE-02, EXE-03, EXE-06, EXE-07 and LENS-02 (REQUIREMENTS.md) and the ROADMAP's Phase 42 criteria 1 to 6, including
the amendments of 2026-11-16 (Phase 37 D-27: a runner-hosted headless lane already closes its own herdr tab per call and the
protocol is Phase 37's; Phase 38 D-25 and D-27: the start-of-run sweep is the runner's `--sweep`). Phase 40 builds the lane
ping, the flagged switch, the partial report and the jev classification and sizing modules this phase reuses; Phase 41 builds the
executor-side flags, fallback, guidance and audit.

**The owner's decisions (highest priority):**

- 2026-11-23, answers to this phase's question batch: (1) the code-review loop uses spec review's rule: cap 3 rounds, it passes
  when no CRITICAL or HIGH finding is open, MEDIUM and LOW are listed and never block, and at the cap an owner stop shows the
  last report; (2) a short lite block is added to the plan-writer brief when a lite executor was picked, ai-kit-owned text only
  and labeled unverified; (3) the transport chooser offers only transports the spike verified, an unverified one is listed as
  unverified and never picked automatically; (4) when several transports are verified, a verified resumed session wins over a
  subprocess for a headless lane and a herdr pane is used only for an interactive lane (Phase 37's scope for panes), so the
  default never opens a pane; the interactive marker is a lane setting added at plan time.
- 2026-11-02 and 2026-11-16: the runner never switches harness, provider or model on its own; jev is advisory and never gates;
  every jev path and every herdr path has a tested no-jev or no-herdr behavior; a lane or pick stays inside the owner's roster.
- A live probe that costs model quota needs the owner's consent line (no consent line existed on 2026-11-23, so no live probe
  has run for this phase).

**Decided by own reasoning on 2026-11-23, the owner may overrule:** the review loop reuses Phase 40's jev classification
(`owner_decision`, `mechanical`, `reviewer_wrong`) at the stop-and-discuss point; the executor pick happens after the existing
affinity and context filters and before dispatch; the renewal count is a named constant fixed at plan time.

**Live facts checked for this spec (2026-11-23, this machine):**

- The adapter has no code-review step: `requesting-code-review` and `receiving-code-review` appear nowhere in
  `ai-kit-spec-execute-superpowers/SKILL.md` or its references.
- `task_classification.classify_task` sorts a task by its **Files:** block into frontend, backend, mixed or none; the executor
  candidate filters are `filter_by_purpose`, `filter_by_affinity` and `filter_by_context` in `ai_kit_spec/execute_selection.py`;
  `resolve_execute_candidates` and `candidates_to_ladder` produce the order the adapter walks. Nothing asks jev.
- The role-keyed table `skill-roles.json` (Phase 39) already lists `ponytail-review` as `review_lens` and `impeccable` as
  `ui_lens`; `lens_delivery.LENS_NOTES` carries the notes for a missing lens.
- `cross-ai.mjs` holds 38 mentions of herdr and per-runtime `resume` forms with verified or unverified labels (for example
  cursor's `--resume <sid>`, line 1769), a `--session-id` option (line 38) and the `--sweep` flag; the Phase 37 protocol is the
  `aikit:<role>:<runtime>:<token>` label, the run directory files and the exit or result file as the only verdict.
- ai-kit's shipped code contains no transport chooser and no code that reuses a session across rounds.

## Requirements

1. **A capped code-review loop runs after execution (EXE-02)**: after the last task of a superpowers plan, `requesting-code-review`
   runs and ai-kit's loop iterates with the same review lanes as spec review (including Phase 40's ping, flagged switch and
   partial report) for at most 3 rounds, passing when no CRITICAL or HIGH finding is open; at `receiving-code-review`'s
   stop-and-discuss point jev classifies each gray area (`owner_decision`, `mechanical`, `reviewer_wrong`) before the owner is
   asked, with Phase 40's routing and its CRITICAL and HIGH exception; at the cap the owner gets the last report.
   - Current: no code-review step in the adapter.
   - Target: a step after the final task and before the fold step, with its own reference file.
   - Acceptance: fake-lane tests: a review that finds a HIGH finding fixed in round 1 passes in round 2; a review that never
     clears stops at round 3 with the last report; a MEDIUM finding never blocks; a gray area classified `owner_decision` or low
     reaches the owner; no jev asks the owner as today; a doc-contract test pins the cap and the pass rule.

2. **The code review loads the lenses from the role-keyed table (LENS-02)**: the review loads `ponytail-review` and, when the diff
   touches UI, `impeccable`, from `skill-roles.json` on the same lanes as spec review; a missing lens is skipped with a note and
   the review still runs.
   - Current: no code review, so no lens loading.
   - Target: the existing lens delivery (`lens_delivery`) is called for the review lanes with the diff's changed paths.
   - Acceptance: fixture diffs: a `.tsx` change gets both lenses, a `.py` change only `ponytail-review`; with `ponytail-review`
     absent the review runs and prints the lens note; `impeccable` never loads for a diff with no UI path.

3. **jev picks the executor from the owner's roster (EXE-03, part 1)**: after the purpose, affinity and context filters, jev picks
   the executor for a plan or a task among the remaining roster candidates (router lite or strong coding models, haiku or sonnet
   at low, medium or high effort on native Claude, composer on Cursor, a cheap Copilot model); the run log shows the pick and why;
   without jev, or on a low answer, the existing order decides and the log says so; jev never picks outside the roster.
   - Current: the first candidate of the filtered order is used; jev is not asked.
   - Target: a pick step in `execute_selection` flow with a sentinel for "no jev answer".
   - Acceptance: fake-jev tests: a confident pick moves that candidate first and logs the reason; a low or missing answer keeps
     today's order and logs "default"; a pick outside the roster is discarded; a candidate removed by the filters is never picked.

4. **A lite executor gets a lite block in the plan-writer brief (EXE-03, part 2)** *(effect on a lite model unverified)*: when the
   picked executor is lite, a short block of ai-kit-owned text (smaller tasks, exact commands, one file group per task, no
   inference needed) is delivered beside the plan-writer brief as its own file; with a strong executor nothing is written;
   superpowers' own prose and the brief file are never edited. *(amended 2026-11-23, 42 discuss: the first draft appended the
   block to the brief; `fold.py boundary` writes that brief with no extra-text option and the fold tool stays system-neutral, so
   the block is a separate file)*
   - Current: the plan-writer brief (`.aikit/brief/SKILL.md`) has no executor-specific text and no second file.
   - Target: a lite block file and the rule that selects it (a lite class from the model catalog; the selector is fixed at plan
     time), handed to the plan writer by the same rail that hands over the brief.
   - Acceptance: fixtures: a lite pick yields the lite file; a strong pick yields none; the brief file bytes are unchanged; a
     diff-scope check shows no third-party file changed; a doc-contract test pins the block's text and its unverified label.

5. **A recorded spike verifies session ids and headless resume per host (EXE-06, part 1)**: a spike record states, for each
   installed host, whether a session id can be obtained and a headless resume run, with the run's version, date, result and a
   verified or unverified label; the spike runs only with the owner's consent line and in a scratch directory with a scratch HOME.
   - Current: the runner holds resume forms with labels from Phase 37 help captures; no live resume run is recorded.
   - Target: a dated spike record under the phase directory, one row per host.
   - Acceptance: the record exists with a row for each installed host and every row carries version, date, result and label; a
     row with no run says "not run" and is labeled unverified; no real host config changed (the audit of Phase 41, or mtimes
     compared by hand).

6. **Each lane's transport is chosen per lane, reused within a plan and renewed (EXE-06, part 2)**: for execute, spec-review and
   code-review lanes the chooser picks subprocess, resumed session or herdr pane, offering only transports the spike (or the
   runner's verified label) shows verified; the choice is reused for the lane within a plan and renewed after a set number of
   rounds; a herdr lane reports through a result file, its pane closes at plan close, and leftovers are closed by the runner's
   `--sweep`, never a second sweep; every pane carries Phase 37's label and run record.
   - Current: every lane runs as one subprocess call; no chooser, no reuse.
   - Target: a chooser seam next to the runner dispatch, a per-plan lane-transport record, and a herdr result-file reader.
   - Acceptance: fake-lane and fake-herdr tests: an unverified transport is never chosen; a verified resume is reused in round 2
     and renewed after the set count; with herdr absent the lane runs as a subprocess; the pane closes at plan close and a
     leftover pane is closed by `--sweep`; the verdict is read from the result or exit file only.

7. **jev classifies each lane result before the loop continues (EXE-07)**: before a loop continues or stops, jev classifies an
   execute result as done, partial or another round, and a review finding by whether its severity fits the kind of problem, the
   test tier, reproducibility, end-user reach and MVP versus production; without jev a deterministic default decides (the
   runner's outcome for execute, the reviewer's own severity for review) and the run log shows which one decided.
   - Current: no lane result goes through jev.
   - Target: one classification call per result, summaries only, through Phase 40's jev module pattern.
   - Acceptance: fake-jev tests: each execute class and each review fit routes as written; no jev uses the default and logs
     "default"; a CRITICAL or HIGH review finding is never lowered on jev's word; a doc-contract test pins that only summaries
     go to jev.

8. **Every changed SKILL.md meets the judge bar (JDG-04)**: `ai-kit-spec-execute-superpowers` and any other SKILL.md this phase
   changes carry new-shape evals and tests and pass the skill-judge loop.
   - Current: the adapter carries 14 evals, none for code review, the executor pick or the transport.
   - Target: each judged result has no critical or high finding, or grade B or better, and no regression beyond the judge's
     run-to-run variation.
   - Acceptance: the judge records meet the bar of AGENTS.md and `make check-dogfood` validates them; `evals.json` gains one eval
     each for the review loop, the executor pick, the lite block and the transport choice.

## Boundaries

**In scope:**
- The code-review step and loop, lens loading, the jev executor pick, the lite block, the spike record, the transport chooser
  and reuse, jev lane-result classification, docs, evals and the judge loop.

**Out of scope:**
- The lane ping, the flagged switch, the partial report and the jev modules (Phase 40) and the executor flags, fallback,
  guidance builders and audit (Phase 41): reused, not rebuilt.
- Redefining the herdr protocol, the pane label or the sweep (Phases 37 and 38).
- Editing superpowers' skills or GSD's files.
- A new jev backend or a change to the shared jev client; switching an unflagged lane.

## Constraints

- Runtime code stays stdlib-only; jev and herdr are optional with a tested no-jev and no-herdr behavior on every path.
- Only summaries go to jev, never code, diffs, file contents, config values or secrets.
- A pick or transport choice stays inside the owner's roster and never changes harness, provider or model on its own.
- The spike needs the owner's consent line, runs in a scratch directory with a scratch HOME and records only version, date and
  result.
- Tests use fake lanes, a fake herdr and a fake clock; no real host runs in the suite.
- No machine-specific absolute path in skill text, tests or fixtures; model names in fixtures are placeholders.

## Acceptance Criteria

- [ ] A code review with a HIGH finding fixed in round 1 passes in round 2; one that never clears stops at round 3 with the last
  report; MEDIUM and LOW never block
- [ ] jev classifies gray areas and lane results; no jev falls back to the deterministic default and the log says which decided
- [ ] `ponytail-review` always and `impeccable` only for a UI diff load on the review lanes; a missing lens is noted and skipped
- [ ] jev picks the executor among roster candidates after the filters; a low or missing answer keeps today's order; the log shows
  the pick and why
- [ ] A lite pick adds the lite block to the plan-writer brief; a strong pick adds nothing; no third-party file changes
- [ ] The spike record has one dated row per installed host with version, result and label
- [ ] An unverified transport is never chosen; a verified resume is reused and renewed after the set count; herdr absent means a
  subprocess; a pane closes at plan close and `--sweep` closes leftovers
- [ ] Every changed SKILL.md meets the judge bar of AGENTS.md

## Edge Coverage

**Coverage:** 32/34 applicable edges resolved (20 covered or backstop, 12 dismissed with the owner's approval of 2026-11-23) · 2 unresolved (R2 and R3 unclassified; flagged assumptions) *(amended 2026-11-23, 42 discuss: the R4 amendment added the R4 boundary and precision rows)*

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| boundary | R1 | 🧪 backstop | Held-out fixture: a review that clears exactly in round 3 passes; round 3 is the last round and a still-open HIGH there is the cap stop. |
| adjacency | R1 | ✅ covered | R1 acceptance: a MEDIUM finding never blocks while a HIGH one does. |
| empty | R1 | 🧪 backstop | Held-out fixture: a review with no findings passes in round 1 and jev is not called. |
| ordering | R1 | ✅ covered | R1 acceptance: a HIGH finding fixed in round 1 passes in round 2 (review, then fix, then review). |
| precision | R1 | ✅ covered | R1 acceptance: MEDIUM and LOW never block; the CRITICAL and HIGH exception follows Phase 40. |
| concurrency | R1 | ✅ covered | R1 reuses Phase 40's partial report: one lane's failure never cancels another lane's result. |
| unclassified | R2 | ⚠ UNRESOLVED | Edge unresolved — planner must treat as assumption (no shape cue matched the lens requirement). |
| unclassified | R3 | ⚠ UNRESOLVED | Edge unresolved — planner must treat as assumption (no shape cue matched the executor-pick requirement). |
| boundary | R4 | 🧪 backstop | Held-out fixture: a model whose catalog class sits exactly at the lite edge is read as the catalog states; a missing class means no lite file. |
| precision | R4 | ✅ covered | R4 acceptance: the brief file bytes are unchanged and no third-party file changes. |
| adjacency | R4 | 🧪 backstop | Held-out fixture: a model whose catalog class is unknown gets no lite block. |
| empty | R4 | 🧪 backstop | Held-out fixture: no executor picked adds nothing to the brief. |
| encoding | R4 | ⛔ dismissed | The lite block is a fixed ai-kit text; no length or normalization semantics. |
| ordering | R4 | ⛔ dismissed | The block is appended once at a fixed place. |
| concurrency | R4 | ⛔ dismissed | The brief is written once per unit by one agent. |
| adjacency | R5 | ⛔ dismissed | Spike rows are independent per host. |
| empty | R5 | ✅ covered | R5 acceptance: a row with no run says "not run" and is labeled unverified. |
| encoding | R5 | ⛔ dismissed | A planning document; no text-encoding semantics. |
| ordering | R5 | ⛔ dismissed | Rows are listed per host; order carries no meaning. |
| boundary | R6 | 🧪 backstop | Held-out fixture: at the set renewal count the session is renewed before the next round, never mid-round. |
| adjacency | R6 | 🧪 backstop | Held-out fixture: two lanes on the same runtime and model keep separate sessions. |
| empty | R6 | ✅ covered | R6 acceptance: with herdr absent the lane runs as a subprocess. |
| encoding | R6 | ⛔ dismissed | The pane label and token format belong to Phase 37's protocol. |
| ordering | R6 | 🧪 backstop | Held-out fixture (owner decision 4 above): with a verified resume and a verified pane a headless lane takes the resume, an interactive lane takes the pane, and with neither verified a subprocess runs. |
| precision | R6 | 🧪 backstop | Held-out fixture: a verified label is bound to the recorded host version, and a different version reads as unverified. |
| concurrency | R6 | 🧪 backstop | Held-out fixture: two runs on one checkout keep the runner's one-run lock and never share a pane. |
| boundary | R7 | 🧪 backstop | Held-out fixture: a jev answer with `needs_fallback` true counts as low and the default decides. |
| adjacency | R7 | ⛔ dismissed | One jev item per lane result; results never merge. |
| empty | R7 | 🧪 backstop | Held-out fixture: no lane result means no jev call. |
| ordering | R7 | ⛔ dismissed | Each result is classified independently. |
| precision | R7 | ✅ covered | R7 acceptance: a CRITICAL or HIGH review finding is never lowered on jev's word. |
| adjacency | R8 | ⛔ dismissed | The judge loop is a process over files; no values touch. |
| empty | R8 | ⛔ dismissed | A skill with no change is not judged; the requirement names the changed ones. |
| ordering | R8 | ⛔ dismissed | Judge rounds have no order semantics beyond the three-round cap of AGENTS.md. |

## Prohibitions (must-NOT)

**Coverage:** 6/6 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT pick an executor or transport outside the owner's roster, and MUST NOT pick an unverified transport automatically | R3, R6 | resolved | test (R3 and R6 acceptance); wired-check descriptor left empty until plan time |
| MUST NOT lower or drop a CRITICAL or HIGH finding on jev's word, and MUST NOT pass a review with one open | R1, R7 | resolved | test (R1 and R7 acceptance); wired-check descriptor left empty until plan time |
| MUST NOT send code, diffs, file contents, config values or secrets to jev | R1, R3, R7 | resolved | test (a seam that records the payload) and judgment review; wired-check descriptor left empty until plan time |
| MUST NOT edit another framework's prose or files to deliver the lite block or the review step | R2, R4 | resolved | test (a diff-scope check over the changed files); wired-check descriptor left empty until plan time |
| MUST NOT run a live host probe without the owner's consent line, and MUST NOT touch a real host config in the spike | R5 | resolved | judgment review (the spike record states its consent line) and test (scratch HOME in the spike script); wired-check descriptor left empty until plan time |
| MUST NOT change today's behavior when jev or herdr is absent, errors or answers with low confidence | R1, R3, R6, R7 | resolved | test (no-jev and no-herdr fixtures for each path); wired-check descriptor left empty until plan time |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                                       |
|--------------------|-------|------|--------|-----------------------------------------------------------------------------|
| Goal Clarity       | 0.82  | 0.75 | ✓      | review loop, executor pick, lite block, transports, lane-result classes      |
| Boundary Clarity   | 0.75  | 0.70 | ✓      | Phase 40 and 41 modules reused, herdr protocol not redefined                 |
| Constraint Clarity | 0.68  | 0.65 | ✓      | renewal count, lite selector and spike host list fixed at plan time          |
| Acceptance Criteria| 0.72  | 0.70 | ✓      | 8 pass/fail criteria                                                        |
| **Ambiguity**      | 0.24  | ≤0.20| ⚠      | gate missed by 0.04; no dimension below its minimum                          |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

Run mode `interactive`, 1 question round plus the gate question. jev was not asked: in the interactive path it screens only
items the owner asks it to screen. Rule: mvp-mode inactive, the best design wins over the smallest diff.

| Round | Perspective     | Question summary                                              | jev (advisory) | Decision locked |
|-------|-----------------|---------------------------------------------------------------|----------------|-----------------|
| 1     | Researcher      | What exists for code review, executor pick and transport?     | none           | No review step, no pick, no chooser; resume forms and herdr in the runner from Phase 37 (Background) |
| 1     | Boundary Keeper | How does the code-review loop stop?                           | none           | Spec review's rule: cap 3, pass on no CRITICAL or HIGH (R1) |
| 1     | Simplifier      | What are the lite executor's plan instructions?               | none           | A short ai-kit-owned lite block in the plan-writer brief, unverified (R4) |
| 1     | Failure Analyst | How are unverified transports treated?                        | none           | Offer only verified ones (R6) |
| 1     | Boundary Keeper | Which transport wins when several are verified?               | none           | Resume over subprocess for headless lanes; pane only for interactive lanes (owner, 2026-11-23; R6) |
| —     | Own reasoning   | Reuse Phase 40's jev classes; pick after the filters          | none           | Recorded in R1 and R3. Ledger. |
| gate  | Seed Closer     | Approve the flagged SPEC (0.24), edges and prohibitions?      | none           | Approved and committed flagged (owner, 2026-11-23): 12 dismissals, 18 covered or backstop rows, 2 unresolved, six prohibitions |

---

*Phase: 42-code-review-after-execution-and-jev-picked-executors*
*Spec created: 2026-11-23*
*Next step: /gsd-discuss-phase 42 — implementation decisions (loop placement, pick step, lite selector, chooser seam, spike hosts)*
