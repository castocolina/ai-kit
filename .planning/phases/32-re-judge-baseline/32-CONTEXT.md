# Phase 32: Re-judge baseline - Context

**Gathered:** 2026-11-07 (assumptions mode, after 32-SPEC.md)
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 32 produces the owner's one current-judge report for the 15 judged skills (the work list of batch phases
32.1-32.4), the tracked tools that make that report reproducible (judge-prompt builder, verdict checker, judge-count
rule), and two text gates over the skill tree: a strict frontmatter check for every SKILL.md and a history-free text
check for every kept skill. It brings no skill to the judge bar and writes no evals.
</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**10 requirements are locked.** See `32-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `32-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- The test-location decision, its spike record and the stray-module guard (R1).
- A tracked judge-prompt builder, judge pool selection with recorded substitutes, the judge-count rule (R2-R4).
- A tracked verdict checker promoted from the phase 27 copy, with the round cap and refutation records (R5, R6).
- The baseline judge run of the 15 skills and the committed report with its raw verdicts (R7).
- The strict frontmatter check and the history-text check, with the text fixes the kept skills need (R8, R9).
- AGENTS.md: the round cap, the refute-by-running rule and the behaviour-not-history line (R6, R9).
- JDG-04 citations in 32.1-32.3 and 34 and the check-dogfood guard (R10).

**Out of scope (from SPEC.md):**
- Bringing any skill to the judge bar, or writing evals and trigger queries — the batch phases 32.1-32.4 (JDG-03, JDG-04).
- Moving test modules into `tests/skills/<name>/` — rejected by the spike (R1).
- Converting the spec-review family's Markdown eval scenarios to `evals.json` — Phase 32.2 (owner, 2026-11-07).
- Trimming evals from the shipped copy — Phase 52 (DIST-01); until then evals reach hosts through the install links (owner, 2026-11-07).
- Judging `ai-kit-commit-fold` and the seven rules skills — excluded (owner, 2026-11-07); they still pass the frontmatter check, and commit-fold passes the text check.
- A config file for the judge list — Phase 33 designs ai-kit's config; the checker takes the list as an argument.
- Vendoring or editing the third-party skill-judge — ai-kit installs only its own skills (DIST-07); the builder reads the installed copy.
- Code comments and docstrings in the history-text check — code names the project paths it reads and writes; shipped-copy contents are Phase 52 (DIST-05).

</spec_lock>

<decisions>
## Implementation Decisions

Quality rule: `mvp-mode` inactive, so the best design wins over the smallest diff; least-code findings decide how
code is written, never which design wins. jev answers are advisory; the attribution ends each decision.

### The judge-loop tool (SPEC R2, R4, R5, R6)

- **D-01: One stdlib module, `tools/judge_loop.py`, with the subcommands `prompt`, `pool`, `count`, `ingest`, `check`
  and `report`.** They share one repo-root resolver (`git rev-parse --show-toplevel` in the working directory, with a
  `--root` override; never `__file__`, so a fixture repository works and the sub-folder digest test can pass), one
  skill-file lister and digest (`git -C <root> ls-files -z -- skills/<name>/`, trailing slash, so
  `ai-kit-spec-review` and `ai-kit-spec-review-fixer` stay apart) and one rubric-pin reader. Exit codes follow
  `tools/check_dogfood.py`: 0 ok, 1 an invalid, missing or mis-pinned verdict (and with `--gate` also an unmet bar or
  a loop over the cap), 2 usage. Promoted from the phase 27 checker: `validate_verdict`, `grade_of`,
  `parse_status_line` and the digest idea; from `tmp/judge-30/round3/check_verdicts.py`: unique finding ids, finding
  file and line in range, a finding for every below-max dimension; from the p27 `build_report.py`: the AIKIT-XAI and
  verdict-line scan. Dropped: the hardcoded skill and judge table, the seven-round label, the `27-SKILL-JUDGE.md`
  header parsing. The tool name is the planner's to change. **Own reasoning** (jev one_module low 0.37 laya, 0.75
  typesafe): copies of the digest and root code drift, and a drifted digest marks verdicts stale or current by
  mistake. Ledger.
- **D-02: One JSON record per (loop, skill, round, judge).** `prompt` writes a manifest beside each prompt (skill,
  judge, loop, round, the skill digest at build time, `rubric_version`, `spec_sha`, each embedded file's sha256, the
  module list); `ingest` joins it with the lane's last `AIKIT-XAI ` stderr line and the verbatim verdict JSON line.
  `ingest` refuses a verdict whose `judge` differs from the lane that ran it or whose pin differs from the manifest;
  a failed lane is recorded with its status and no verdict; a later attempt in the same round adds an attempt, not a
  round; a valid verdict record is never overwritten. The digest is the one taken when the lane started.
  choice 0.98 (typesafe).
- **D-03: Rounds count per skill within one judge loop, and the cap of three applies per loop.** A loop is the phase
  that runs it (`32`, `32.1`, ...), and its id is part of the record layout. The cap stops a fix loop that does not
  settle (the case that ran seven rounds); counting over a skill's whole history would put a batch phase over the cap
  after its second round, before any fix loop ends, and SPEC R6 says "a judge loop stops after three rounds per
  skill". **Own reasoning** (jev lifetime low 0.60 laya, 0.78 typesafe): the evidence contradicts the answer, and a
  low answer is final, so no second opinion. Ledger.
- **D-04: Refutations live in `refutations/<loop>.json`, one entry per skill, round, judge and finding id**, with
  `path:line`, the command and its observed output. `check` drops a refuted finding from the bar only when all four
  fields are non-empty and the finding id exists in that judge's verdict (finding ids repeat across judges).
  choice 0.72 (laya).
- **D-05: The judge-count rule is a pure function, and the tool asks jev itself.** `count` applies SPEC R4's
  deterministic triggers first and asks jev only when they give one judge. It builds a `score` item with four ordered
  levels, from "no change likely to move the score" to "change likely to move it past the judge variation", and
  raises one judge to two when the winning level is 2 or higher and `needs_fallback` is false. The item carries fixed
  wording only: the tool turns the numbers (last percent and its distance from 80, critical and high counts, SKILL.md
  lines changed, changed reference, script and eval files, all from a git numstat against the commit the last
  verdict judged) into fixed word bands before sending, because Jev's documented weak spots include arithmetic and
  counting. The call goes through `jev_review.py ladder` found by the tool's own copy of the installed-skill lookup,
  which joins the lookup drift test in `tests/test_arch.py` (29 D-13); the same copy finds the installed skill-judge.
  `--no-jev`, a jev error, `needs_fallback` or absence leave the deterministic count; the record keeps the inputs
  and the answer. With today's recorded verdicts 13 judged skills get two judges deterministically and only
  `ai-kit-gsd-spec-discuss` (88.0) and `ai-kit-spec-goal-prompt` (88.8) reach the jev step. choice 0.93 (typesafe);
  the word-band step is own reasoning.

### Report, records and the judge run (SPEC R3, R7)

- **D-06: The living report and its records live in `.planning/judge/`, outside every phase folder.** Layout:
  `REJUDGE.md` (generated by `report`, never hand-edited), `verdicts/<loop>/<skill>/r<N>/<judge>.json`,
  `refutations/<loop>.json`, and `inputs.json` (each skill's owning batch, the exclusion reasons, the last old
  120-point score and the last rubric-v4 count inputs, each with its source). `check` regenerates the report and
  compares bytes, which proves every report number equals its raw record. The tool takes the folder as an argument
  and has no `.planning` default. **Own reasoning** (jev phase_folder low 0.39 laya, 0.76 typesafe): milestone close
  moves phase folders into `milestones/` (`complete-milestone.md`), while four batch phases and later JDG-04 phases
  refresh this report in place; top-level `.planning/` folders (`research/`, `lens-brief/`, `goals/`) survive.
  Ledger.
- **D-07: `make check-dogfood` runs `judge_loop.py check .planning/judge` in default mode.** An invalid,
  mis-pinned or report-mismatched record is a problem; a stale digest is a note (skills change between batch
  phases). It keeps the never-edit-a-raw-verdict prohibition checked on every push, from the only reader of
  `.planning/`. Own reasoning (not asked).
- **D-08: The run is a plan task that follows `ai-kit-cross-ai`, not tool code.** It probes each judge in the given
  list through `.planning/scripts/cross-ai.mjs --mode review` with a one-word prompt and an outer timeout of about
  600 seconds (the runner retries a dead model for about 200 seconds before `exit=75`); `pool` turns the status lines
  into the pool (the first two usable judges, else one plus native, else native alone). Lanes run one prompt per
  skill, each judge through its skills in order, the two judges in parallel, under `gsd-tools run-with-timeout` with
  `--outer-timeout 3600` and `AI_KIT_REFUSE_REAL_HOME=1`, outputs under `tmp/`. Judge ids are the exact lane strings
  the run builds from the list (for example `<cli>:<model>` and `native:opus-xhigh`); no id is written into code.
  choice 0.81 (typesafe).
- **D-09: Nothing tracked changes and HEAD does not move while any lane runs.** The runner fingerprints the tree and
  HEAD and stops a review lane on `tree=dirty`; fully ignored folders (`tmp/`) are skipped. Lane outputs and
  ingested records stay under `tmp/` until every lane of the run has ended, then go into `.planning/judge/` in one
  commit; the judging plan writes no SUMMARY, STATE or commit while lanes run. Analyzer, Confident; not asked.
- **D-10: The native substitute is `agents/ai-kit-judge.md` with `effort: xhigh` added to its frontmatter before
  judging, and it gets the built prompt by file path** (about 92 KB inline would land in the orchestrator's context
  on every call). The record says "native, xhigh (frontmatter)"; whether Claude Code honours `effort` in a
  user-level agent file is an open research item for the phase researcher, and until it is shown the report labels
  the effort unverified. choice 0.87 (laya).
- **D-11: Plan order.** Wave 1 in parallel: the R1 guard and the R8 frontmatter checks; the R9 test with the text
  fixes and AGENTS.md's lines; the R10 check-dogfood guard; the tool with its tests and the judge agent's effort
  line. Wave 2: the judge run, after every SKILL.md edit (SPEC R7). Wave 3: ingest, generate the report and run
  `check` in default mode (exit 0, every skill current). `--gate` is not the baseline's acceptance, since a baseline
  holds unmet bars by design. Own reasoning, corrects the analyzer's `check --gate`.
- **D-12: The baseline verdict becomes each judged skill's base for the batch phases' regression check**; older
  bases (spec-config's 105 on the old scale, goal-prompt's 90.4) are history, with JDG-01 and PROJECT.md ("only the
  current judge's verdicts count"). This closes an open owner item in the live-checks todo. **confirmed by the owner 2026-11-07**.
  Own reasoning (not asked). Ledger.

### The judge prompt (SPEC R2)

- **D-13: The builder finds skill-judge through the tool's skills-roots lookup (`--judge-dir` for tests) and embeds,
  byte for byte, its `SKILL.md`, `references/rubric.md`, the files of the rubric's `source` column (anchors
  stripped, deduplicated, table order: `best-practices.md`, `specification.md`, `optimizing-descriptions.md`,
  `evaluating-skills.md`, `using-scripts.md`) and `references/verdict.schema.json`.** The prompt says the embedded
  copies replace every "Read `references/...`" step and that the `tests/skills/<name>/` reading is replaced by the
  listed modules; otherwise a judge that cannot resolve `references/` writes a high finding against every skill.
  Analyzer, Confident; not asked.
- **D-14: Each skill's module list is `staged_mapper.covering_modules(build_index(root), "skills/<name>/SKILL.md")`,
  sorted, or the line "no script test found".** It is the set the commit hook runs when the skill changes, computed
  from the tree as SPEC R2 requires (1 to 59 modules per skill in the spike). A name-prefix rule finds nothing for
  spec-review, execute-superpowers and cross-ai, and a hand-kept table is not computed. **Own reasoning** (jev
  selector low 0.68 typesafe, manual low 0.60 laya). Ledger.
- **D-15: "Ships runnable code" means at least one tracked `.py`, `.mjs`, `.cjs`, `.js` or `.sh` file under
  `scripts/` or at the skill root, or a top-level folder holding `__init__.py`.** `.txt` templates and `references/`
  do not count: 11 kept skills ship code, 5 do not (cst-refactor's `codemod_template.py.txt` and spec-review's
  `references/cross-ai.mjs` template are not code for this reading). Analyzer, Confident; not asked.

### Text gates and AGENTS.md (SPEC R1, R6, R8, R9, R10)

- **D-16: The R1 guard lives in `tests/test_gate_scope.py`** beside the discovery rules it protects: one walk of
  `tests/`, `__pycache__` skipped, every nested `test_*.py` reported in sorted order, with a non-vacuity case in its
  non-vacuity class. Analyzer, Confident; not asked.
- **D-17: The frontmatter check has two layers.** A stdlib strict-subset validator in a new unit-group module
  (`tests/test_skill_frontmatter.py`) is the gate: it accepts single-line plain scalars without `: `, ` #` or a
  leading indicator, double- and single-quoted scalars, and `>`/`|` block scalars with space indentation; it rejects
  tabs, duplicate keys, plain continuation lines, unterminated quotes and empty frontmatter, then applies SPEC R8's
  name and description rules; it replaces the two guard tests in `tests/test_setup.py`. A second module in the
  runner's `unit-uv` set parses the same fixture corpus and the tree with PyYAML `safe_load` through a loader that
  rejects duplicate keys, as an independent cross-check (PyYAML already serves `tests/test_framework_profiles.py`
  there). The fixture results are compared once with the npm `yaml` package the skills CLI uses and recorded in the
  verification. choice 0.82 (laya).
- **D-18: The history-text test is `tests/test_skill_text_history.py`, with SPEC R9 amended for its file scope and
  decision ids.** Rules: the evidence heading is exactly `## Evidence` and must be the last `##` (goal-prompt's
  mid-file `## Evidence and limits` stays main flow and passes); dates are ISO dates and "as of" phrases; a version
  is a dotted number after a name from one constant tool list (the runtime hosts plus gsd-core, node, Node, python,
  jev, Jev, laya, Laya, uv), outside code spans and URLs, and passes when its sentence carries a constraint word ("or
  later", "or newer", "at least", "needs", ">=", "older", "before", "if", "when"); run logs are a narrow phrase list
  ("one real run", "confirmed live", "recorded <date>"), so `unverified` and "until observed" labels pass; pointers
  are numbered phase folders or files, `999.N` backlog ids, bare or phase-prefixed decision ids (`(D-07)`,
  `20 D-11`), `router-env/` and `referee-` names; the shipped Markdown is every `.md` outside `evals/`. The seven
  rules skills are an exempt set pinned equal to the folders with that prefix. The version rule is **own
  reasoning** (jev tool_list low 0.75 typesafe, any_number low 0.51 laya): skills carry thresholds such as 0.74. The
  decision-id class is **own reasoning** (jev split: yes low 0.70 laya, no low 0.67 typesafe): these ids mean nothing
  outside this repository, the SPEC Background already counts "(D-07)" as history, and placeholders keep
  spec-discuss's log format teachable. Ledger.
- **D-19: The text fixes are moves into a trailing `## Evidence` section or an existing reference, or
  history-to-behaviour rewordings; no instruction changes.**
  - `ai-kit-gsd-curated-config`: `## Limits (as of 2026-10-23)` becomes `## Limits`; the pi and cursor rows keep
    "not live-validated", "validated headless" and "pending" but drop the phase file names and the cursor-agent build
    string (date and build go to Evidence); "(20 D-11)" goes.
  - `ai-kit-spec-config`: "Confirmed live 2026-08-29" becomes a behaviour statement with the date in Evidence; the
    "(changed 2026-08-29 …)" history moves to Evidence; "(D-04)" goes.
  - `ai-kit-spec-review`: "recorded 2026-08-29 in …" moves to Evidence; "needs Node 24" stays (a constraint).
  - `ai-kit-spec-execute-superpowers`: "needs Node 24 (GSD's declared floor)" stays; the `@opengsd/gsd-core` 1.17.0
    source moves to Evidence and the `.planning/phases/18.1-…` pointer is deleted (the pointer rule covers Evidence).
  - `ai-kit-gsd-spec-discuss`: "(one real run: … 0.74, then 0.67)" becomes "the same item can score differently on a
    re-ask", with the run in Evidence; `references/log-formats.md`'s `20-SPEC.md` and `20 D-08` examples become
    `NN-SPEC.md` and `NN D-xx`; parenthesized decision-id examples in `references/decision-table.md` and
    `references/worked-examples.md` become placeholders.
  - `ai-kit-spec-review-checklist`: "(confirmed live: … ~8000 lines …)" moves to Evidence; its GSD layout globs pass.
  - `ai-kit-usage-metrics`: "Backlog 999.2" (twice) and "(D-07)" go; the limitation itself stays in plain words.
  - `jev-fast-decision`: the link text "Jev 1.14 notes" becomes "Jev release notes" (the URL keeps its version;
    32.1 rewrites the section); `backends/laya.md` loses the Phase 21.1 results path; `backends/typesafe.md` loses
    "(D-07)".
  - Already passing: commit-fold, spec-execute, goal-prompt, cross-ai, session-wake, review-fixer, cst-refactor,
    markdown-to-pdf. The test run is the final list; a hit it finds that is not here gets the same treatment.
  Analyzer, Confident; not asked.
- **D-20: AGENTS.md takes all three lines inside the existing Non-Negotiable skill-judge bullet** (the round cap of
  three with the result recorded as it stands and an unmet bar going to the owner; refutation only by a recorded
  run; SKILL.md describes behaviour, provenance and version history live in a trailing section or a reference, and
  version-specific text appears only as a conditional), each pinned in `tests/test_rules_docs.py`, which already pins
  AGENTS.md wording. choice 0.86 (laya).
- **D-21: The R10 guard is `check_jdg04_citations(root) -> (problems, notes)` in `tools/check_dogfood.py`**, composed
  in `main()` like `check_edge_floors`. It reads ROADMAP's `## Phase Details` up to the next `## `, splits on
  `### Phase <number>:`, keeps phases above 32 by number tuple, and requires `JDG-04` as a whole token between
  `**Success Criteria**` and `**Plans**` in any such phase whose block names `SKILL.md`; `## Backlog` is outside the
  scan (999.20 stays unchecked until promoted). Unit tests use fixture roots in `tests/test_check_dogfood.py`.
  Analyzer, Confident; not asked.

### Cross-phase amendments in this commit

- **D-22: ROADMAP and REQUIREMENTS amended from this phase's spec.** ROADMAP: 32 criterion 8 records the flat
  layout; 32.1-32.3 criterion 2 and 34 criterion 3 cite JDG-04 (34 gains the full judge bar, since its criterion 6
  changes jev's SKILL.md); the stale `decide.py` anchors of 32.4 and 34 point at `jev_ladder.py`. REQUIREMENTS:
  JDG-01 records the layout and the scripts reading; JDG-06 records the bar-boundary reading (**needs
  confirmation**, SPEC R4); the footer lists both. Folded todo items are marked in their todo files.

### Claude's Discretion

- The tool's final name, flag spellings, the probe prompt's wording and the four score levels' wording.
- The exact word bands of D-05 and the record field names of D-02, as long as the checker reproduces every number.
- How `report` lays out `REJUDGE.md`, as long as it carries every SPEC R7 field.

### Folded Todos

- **Skill-writing principle** (`2026-11-02-tooling-defects-and-skill-writing-principle-found-at-the-v1.md`): the
  main-flow, provenance, audit, AGENTS.md-line and unverified-tag items are folded (SPEC R9, D-17 to D-20); the
  tool-specific-facts and rare-cases items stay with the batch phases' judge rounds.
- **Base-score re-baseline** (`2026-11-02-pending-live-checks-and-owner-decisions-from-v1.3.md`): folded as D-12,
  confirmed by the owner 2026-11-07.
- **Moved planning paths in shipped skill text** (same todo): folded (D-19, jev `backends/laya.md` and
  execute-superpowers).
- **Stale execute-superpowers judge evidence** (same todo): folded; the baseline re-judges it.
- **SJ refactor** (`2026-10-31-refactor-execute-gsd-and-rules-agents-sj-1-sj-3.md`): SJ-2 gets its current-rubric
  verdict from the baseline; the refactor stays with 32.3 and 41; SJ-3 stays with 45.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/phases/32-re-judge-baseline/32-SPEC.md` — Locked requirements — MUST read before planning.
- `.planning/ROADMAP.md` — Phase 32, the batch phases 32.1-32.4 and Phase 34 (as amended 2026-11-07).
- `.planning/REQUIREMENTS.md` — JDG-01 to JDG-08 (JDG-01 and JDG-06 amended 2026-11-07).
- `AGENTS.md` — Non-Negotiable Rules (the skill-judge bullet) and Testing.
- `<skills root>/skill-judge/` — the installed judge (`SKILL.md`, `references/rubric.md`, `references/verdict.schema.json`, `references/judge-prompt.md`, `references/agentskills/`), found through the skills roots; read-only.
- `.planning/milestones/v1.3-phases/27-one-shot-goal-and-loop-prompt-skill/skill-judge/check_verdicts.py` — the checker to promote.
- `tmp/judge-30/round3/check_verdicts.py` — three extra verdict checks to keep (gitignored scratch; copy what is needed).
- `.planning/research/2026-11-02-next-milestone/p27-judge-scripts/` — `build_report.py`, `digest.py`, `prompt-template-r7.txt`.
- `.planning/research/2026-11-02-next-milestone/15-skills-vs-new-judge.md` — inventory, old scores and how judging ran in v1.3.
- `.planning/research/2026-11-02-next-milestone/14-dist-layout-and-install.md` — the skills CLI's frontmatter parsing.
- `.planning/research/2026-11-07-skill-distribution-today.md` — layout facts; its open questions 1, 5 and 9 are answered by the SPEC.
- `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-JUDGE.md` and `judge/parse.py` — the 7-point variation, lane output shape.
- `.planning/phases/31-removals-and-small-defects/31-VERIFICATION.md`, `29.1-JUDGE.md`, `30-JUDGE.md` — the last rubric-v4 verdicts.
- `skills/ai-kit-cross-ai/SKILL.md` and `references/launch-and-wait.md` — launching and reading a lane; the review-mode tree check.
- `skills/jev-fast-decision/SKILL.md`, `reference.md` (item shapes, Installed-skill lookup) and `scripts/jev_review.py` (`ladder`).
- `.claude/gsd-core/workflows/complete-milestone.md` — phase folders move at milestone close (D-06).
- `.claude/gsd-core/references/model-profiles.md` — agent `effort:` frontmatter (D-10).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The phase 27 checker's `validate_verdict`, `grade_of`, `parse_status_line`; the p27 `build_report.py` scan.
- `tools/staged_mapper.py` `build_index` and `covering_modules` (the module list, D-14).
- `tools/run_unittest_parallel.py` `discover_modules`, `group_modules`, `UNIT_UV_MODULES` (where the PyYAML module joins).
- `tools/check_dogfood.py` `check_edge_floors` pattern and `main()` composition; `tests/test_check_dogfood.py`.
- `setup._read_frontmatter` and `setup.enumerate_entries` in `tools/setup.py` (entries the frontmatter test covers).
- `skills/jev-fast-decision/scripts/jev_review.py ladder` and the lookup-copy drift test (`LOOKUP_COPIES`, `tests/test_arch.py`).
- `agents/ai-kit-judge.md`, the read-only native judge lane.

### Established Patterns
- Tests never read `.planning/` (`check_no_planning_reader`); `.planning/` checks live in check-dogfood with fixture unit tests.
- Every gate rule in `tests/test_gate_scope.py` has a non-vacuity case.
- Doc-contract tests pin AGENTS.md wording in `tests/test_rules_docs.py`.
- Lanes run through the project runner copy in review mode, outputs in a wholly ignored folder.

### Integration Points
- `make check-dogfood` (pre-push and `make validate`) gains two checks: JDG-04 citations and the judge records.
- The runner's `unit-uv` set gains the PyYAML cross-check module; the plain unit group gains the frontmatter and text tests.
- Batch phases 32.1-32.4 refresh `.planning/judge/` through the same tool.
</code_context>

<specifics>
## Specific Ideas

- Owner-locked for this phase (2026-11-07): 16 kept skills, 15 judged; commit-fold and the seven rules skills
  excluded; two judges from what the environment offers (configured referees, referee-three as a fallback, native
  Opus at xhigh when referees fail; referee-one is temporarily unavailable, referee-two answered a probe today); never
  substitute silently; the test location decided by a spike; Markdown eval scenarios converted in 32.2; evals reach
  hosts through the links until Phase 52.
</specifics>

<deferred>
## Deferred Ideas

- **jev callers do not know the TypeSafe batch guard.** A batched request merges every item's context into one
  state, and over the row's 8,000 characters every remote answer is forced (this run's spec step). Handed to 32.1's
  "Writing an item" section (JEV-09) and to 32.4's spec-discuss polish (its SKILL.md should size a request to the
  guard).
- **Whether Claude Code honours `effort:` in a user-level agent file** — a research item for the phase researcher
  (D-10).
- **Context limits of router-backed judges for a 92 KB prompt** — the phase researcher checks before the run; a lane
  whose answer shows a truncated rubric is not counted.

### Reviewed Todos (not folded)
- Eight other keyword matches (the System One plan, Cursor subagents, jev discovery scaffolding, quota-schedule
  rules, the PreCompact hook, tool-advisory and session hooks, the unified lane TOML) — not judging or skill-text work.
- The low-risk review and judge notes (`2026-11-06-…`) — their skill-text items go to the batch phases 32.1-32.4,
  which re-judge those skills; the rules-skill items go to Phases 45-46.
</deferred>

---

*Phase: 32-re-judge-baseline*
*Context gathered: 2026-11-07*
