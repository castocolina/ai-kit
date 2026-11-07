# Phase 32: Re-judge baseline — Specification

**Created:** 2026-11-07
**Ambiguity score:** 0.13 (gate: ≤ 0.20)
**Requirements:** 10 locked

## Goal

The owner has one committed report that scores each of the 15 judged skills with the current skill-judge
rubric (judges picked from what the environment offers, one or two per skill by a recorded rule), lists the
8 excluded skills with the reason, and records each skill's judge bar result; a tracked verdict checker
reproduces every number in it; every SKILL.md passes a strict frontmatter check and every kept skill passes
a history-free text check.

## Background

Live checks on 2026-11-07 (read-only; scripts in `tmp/p32-spec/`; unit branch `gsd/phase-32-re-judge-baseline`):

- **Skills.** 23 skill folders: 16 non-rules skills and 7 `ai-kit-project-rules-*`. 15 are judged. Excluded:
  `ai-kit-commit-fold` (temporary; Phase 45 absorbs it, RULE-27) and the seven rules skills (replaced in Phases
  45-47) (owner, 2026-11-07). Owning batches: 32.1 `cst-refactor`, `markdown-to-pdf`, `jev-fast-decision`,
  `ai-kit-spec-review-fixer`, `ai-kit-usage-metrics`; 32.2 `ai-kit-spec-review`, `ai-kit-spec-review-checklist`,
  `ai-kit-spec-config`, `ai-kit-spec-execute`; 32.3 `ai-kit-spec-execute-superpowers`, `ai-kit-cross-ai`,
  `ai-kit-session-wake`; 32.4 `ai-kit-spec-goal-prompt`, `ai-kit-gsd-spec-discuss`, `ai-kit-gsd-curated-config`.
- **The judge.** The installed `skill-judge` (`~/.claude/skills/skill-judge`, a link into `~/.agents/skills/`)
  carries rubric v4 with spec_sha `69ef37e9…`: eight dimensions, 125 points, grade by percent (A ≥ 90, B ≥ 80,
  C ≥ 70, D ≥ 60, else F); critical means the skill will not load or never triggers, high means a wrong or harmful
  instruction or a bottom-band dimension. D7 splits 5/5/5 (output evals, trigger queries, a script test in
  `tests/skills/<name>/`) when `scripts/` exists and 8/7 otherwise. Its `references/judge-prompt.md` tells a judge
  to read the rubric files. Phase 26 discarded a round "judged without its rubric" because its prompt builder
  embedded only SKILL.md (research 15).
- **Verdict history.** Rubric v4 verdicts are committed for 7 judged skills (29-JUDGE.md, 29.1-JUDGE.md,
  30-JUDGE.md, 31-VERIFICATION.md): `jev-fast-decision` 85.6 B, `ai-kit-gsd-spec-discuss` 88.0 B,
  `ai-kit-spec-execute-superpowers` 83.2 B, `ai-kit-spec-goal-prompt` 88.8 B, `ai-kit-spec-execute` 80.8 B
  (1 high), `ai-kit-spec-config` 77.6 C (0 high), `ai-kit-gsd-curated-config` 84.0 B (1 high). The other 8 have only
  old 120-point scores or none (research 15's inventory). The recorded judge variation is 7 percentage points for
  the same judge (29-JUDGE.md, from measured noise of about 7-10 points on unchanged skills). Earlier phases ran at
  most three rounds per skill (the phase 27 checker: "the original loop is capped at three rounds"); one skill ran
  seven rounds and ended unresolved. The audit of phases 28-31 found recent verdicts kept only in `tmp/`.
- **Checkers.** Four `check_verdicts.py` copies exist (archived 25.1, 26 and 27; `tmp/judge-30/`). The phase 27
  copy (219 lines) checks the verdict schema, the arithmetic, the rubric pin, a package digest and the pass rule,
  but hardcodes one skill and three referee names and digests with `git ls-files` relative to the working
  directory, so a run from a sub-folder digests nothing. The `ai-kit-judge` agent (`agents/ai-kit-judge.md`) is
  the read-only native Opus judge lane.
- **Test-location spike** (the repo's own runner and staged mapper, run on the tree and on a scratch tree): 135
  test modules, all flat in `tests/test_*.py`, plus 11 helpers. `discover_modules` globs `tests/test_*.py`
  directly; the mapper indexes `tests/*.py` and treats only two-part `tests/test_*.py` paths as modules. A module
  placed in `tests/skills/demo-skill/` was found by neither: it ran in no group and no gate, staging it selected
  nothing, and `tests/test_gate_scope.py` did not notice because it checks groups against the same discovery.
  Moving tests would touch discovery and module naming, four explicit group sets, 12 `E2E_RECORDED_SECS` keys, the
  eight runner self-test shards and their generator, the generated listings in `Makefile` and
  `.pre-commit-config.yaml`, and root-path idioms in 15 of the movable modules. Only 35 of the 135 modules cover
  exactly one judged skill; 62 cover two or more and 32 cover none (tools, hooks, shared code); six judged skills
  (`ai-kit-cross-ai`, `ai-kit-spec-config`, `ai-kit-spec-execute`, `ai-kit-spec-execute-superpowers`,
  `ai-kit-spec-review-fixer`, `cst-refactor`) would own no module. Only 5 of the 16 kept skills have `scripts/`;
  5 more ship a top-level entry script plus a package, `ai-kit-spec-execute` ships one top-level script, and 5
  (`ai-kit-cross-ai`, `ai-kit-spec-config`, both review helpers, `cst-refactor`) ship no runnable code.
- **Frontmatter.** All 23 SKILL.md frontmatters parse with the `yaml` package and the regex the cached `skills`
  CLI 1.5.20 uses (`parseFrontmatter` in `dist/cli.mjs`); every `name` and `description` is a string, the longest
  description has 958 characters, every name has the spec's form and equals its folder, and no other key is
  present. That CLI skips a skill on a YAML error or a non-string name or description; it does not cap the
  description or compare the name with the folder. Today's guard in `tests/test_setup.py` checks a non-empty name
  and description, the 1,024 cap, and `: ` or ` #` on a plain description line only. PyYAML 6.0.3 is in `uv.lock`
  as a pre-commit dependency.
- **History text** (scan of the 16 kept skills). Dates, tool versions or run logs in SKILL.md main flows:
  `ai-kit-gsd-curated-config` (`## Limits (as of 2026-10-23)`, a cursor-agent build string),
  `ai-kit-spec-config` (two 2026-08-29 lines), `ai-kit-spec-review` ("recorded 2026-08-29"),
  `ai-kit-spec-execute-superpowers` (`@opengsd/gsd-core` 1.17.0 with a
  `.planning/phases/18.1-one-runtime-model/18.1-RESEARCH.md:231` pointer), `ai-kit-gsd-spec-discuss` ("one real
  run: the same item scored 0.74, then 0.67"), `ai-kit-spec-review-checklist` ("confirmed live: an unconstrained
  run produced ~8000 lines"), `ai-kit-usage-metrics` ("(D-07)", "Backlog 999.2"), `jev-fast-decision` ("Jev 1.14
  notes"). Concrete planning artifacts also appear by name (`21-SMOKE-CURSOR.md`, `22-INTERACTIVE-PI.md`).
  Generic project-layout paths are legitimate and common (`.planning/config.json`, `.planning/scripts/cross-ai.mjs`,
  `.planning/phases/**/*-CONTEXT.md`, `.planning/quick/<id>/`, `.planning/milestones/`). No shipped Markdown names a
  referee or a local router alias. Reference files carry dated capability cells on purpose (the certainty rule).
  *(amended 2026-11-07, 32 D-18: a scan of every `.md` outside `evals/` adds jev's `backends/laya.md`, which names a
  Phase 21.1 results file under `.planning/phases/`, and bare decision ids in `backends/typesafe.md`,
  `ai-kit-spec-config` and `ai-kit-gsd-curated-config`)*
- **JDG-04 citations.** 32.4 and every phase from 33 to 54 that changes a SKILL.md cite JDG-04, except 32.1-32.3
  (criterion 2 describes the bar without the id) and 34 (criterion 3 covers regression only, while criterion 6
  changes jev's SKILL.md).
- **AGENTS.md** states the judge bar but no round cap, no refute-by-running rule and no behaviour-not-history rule.

## Requirements

1. **Tests stay flat, and a stray test module fails the suite**: script tests stay flat in `tests/test_*.py`, evals stay in each skill's `evals/` folder, and a test fails when any `test_*.py` file sits in a subfolder of `tests/`.
   - Current: every module is flat, but nothing stops a module placed in `tests/skills/<name>/` (the rubric's default location and its fix text) from running in no gate.
   - Target: this SPEC records the decision and the spike measurements above; no test module moves; a guard test fails on any `test_*.py` file under a subfolder of `tests/` and names its path; evals stay in `skills/<name>/evals/` and Phase 52 trims them from the shipped copy (DIST-01).
   - Acceptance: the guard passes on the tree and fails on a fixture tree holding `tests/skills/demo/test_x.py`; no tracked `test_*.py` path under `tests/` has more than two parts.

2. **The judge prompt carries the judge and one reading of tests and scripts**: every judge prompt embeds the judge package and states the same test and scripts reading for every skill.
   - Current: phase-specific templates told a judge to read copied rubric files and named one skill's test files; nothing tracked builds a prompt.
   - Target: a tracked builder writes the prompt for a judge round with, inline, the installed skill-judge's SKILL.md, its `references/rubric.md`, every spec file the rubric's `source` column cites and `references/verdict.schema.json`, read from the installed skill at run time, with its `rubric_version` and `spec_sha` recorded; the prompt says script tests live flat in `tests/test_*.py` and lists each skill's test modules, computed by one rule from the tree; it says a skill that ships runnable code (runnable files in `scripts/`, a top-level entry script or a package folder) is judged with the 5/5/5 split on those modules and a skill with no runnable code with the 8/7 split; only the skill name and its module list vary between skills.
   - Acceptance: a test builds prompts from a fixture judge package and a fixture tree and finds each embedded file's full text, both reading sentences and the module list the rule gives; two skills' prompts differ only in the name and the list; a fixture skill with a top-level entry script and no `scripts/` is classed as shipping code.

3. **Judges come from the environment, and every substitution is recorded**: each round's judges are picked from what the environment offers, and a substitute never runs unrecorded.
   - Current: lanes were picked by hand per phase; native Opus ran when referees were down, recorded only in that phase's judge file.
   - Target: before the run, each judge in the list the run is given gets a short probe prompt and the first two usable judges form the pool; a judge that fails its probe or its round is replaced by native Opus at xhigh; the report records which judge produced each verdict, its lane status line, and the reason for every substitute; each verdict's `judge` field names the lane that ran it.
   - Acceptance: every verdict in the report names its judge and lane status; every substitute has a reason line; the checker rejects a verdict whose `judge` is not in the judge list it was given.

4. **The judge count per skill follows a recorded rule (JDG-06)**: each skill's round uses one or two judges, decided from deterministic signals plus jev's score with a floor of one.
   - Current: no rule; earlier phases used one to three judges chosen by hand.
   - Target: two judges when the skill has no rubric-v4 verdict, when its last verdict had a critical or high finding, or when its last percent lies within 7 points (the recorded judge variation) of 80, the bar's pass boundary, that is from 73.0 to 87.0 inclusive; otherwise one, unless jev's score on a summary of the skill's change since that verdict asks for two; jev never lowers two to one, and a jev error, `needs_fallback` or absence leaves the deterministic count; the report shows each input and the result per skill.
   - Acceptance: tests of the rule cover no verdict, a high finding, the percents 72.9, 73.0, 87.0 and 87.1, a jev raise, a jev `needs_fallback` and jev absent; the report's per-skill counts and reasons equal the rule's output for the recorded inputs.

5. **A tracked verdict checker reproduces every verdict (JDG-02)**: a tool under `tools/` checks the verdict files for the skill and judge lists it is given and reports digests, the bar and round counts.
   - Current: four untracked or archived checker copies; the phase 27 copy hardcodes one skill and three referee names and digests relative to the working directory.
   - Target: the checker takes the skill list and the judge list as arguments and names no referee; it finds the repository root itself, so a skill's digest (sha256 over each tracked file's sha256 and path) is the same from any sub-folder; per verdict it checks the schema, the arithmetic, the grade and the rubric pin; per skill it reports the judges, the worst percent and grade, the highest critical and high counts, the bar result, whether the verdict's digest matches the tree (current or stale) and how many rounds ran; it exits non-zero on an invalid, missing or mis-pinned verdict, and with a gate option also on an unmet bar or a loop over the cap.
   - Acceptance: tests show the same digest from the root and from a sub-folder of a fixture repository, a malformed or miscomputed verdict rejected with its reason, a verdict with another rubric pin rejected, a stale digest reported as stale and the round count printed; the checker's source contains no `referee` text.

6. **A judge loop is capped and a dispute is settled by running the code (JDG-08)**: AGENTS.md caps a judge loop at three rounds and requires a disputed finding to be refuted by running the code, and the checker flags a loop past the cap.
   - Current: no cap; the phase 27 checker allowed seven labelled rounds, and disputes were sometimes settled by judging again.
   - Target: AGENTS.md's skill-judge rule says a judge loop stops after three rounds per skill, its result is recorded as it stands and an unmet bar goes to the owner; a disputed finding counts as refuted only through a recorded run (the finding id, `path:line`, the command and its observed output), never through another judge round; the checker reports a skill with more than three rounds as over the cap and drops a refuted finding from the bar only when its run record is complete.
   - Acceptance: a doc-contract test pins the cap and the refute-by-running sentence in AGENTS.md; checker tests flag a four-round fixture and keep counting a finding whose refutation lacks its command or output.

7. **One committed re-judge report (JDG-01, JDG-04)**: a committed report scores each of the 15 judged skills with the current rubric and records each skill's bar result.
   - Current: no current-rubric report covers the skills; the verdicts of phases 29-31 are spread over phase files and `tmp/`.
   - Target: one committed report, refreshed in place by the batch phases, with the raw verdict files committed beside it; per judged skill it shows the judges and why that many ran (R4), each judge's score, percent, grade and critical and high counts, the bar result read from the worst judge (met through "no critical or high finding", met through "grade B or better", or not met), the digest, the round count, the owning batch phase and the last old 120-point score labelled history; it lists the 8 excluded skills with their reasons, the inter-judge spread of every two-judge skill, and the rubric version and spec_sha; the judging runs after this phase's text and frontmatter edits.
   - Acceptance: the checker run on the report's verdict files with the 15 skills and the judges that ran exits 0 and reports every skill current at the phase's close; the report lists 15 judged and 8 excluded skills; no old score appears in a grade or bar column.

8. **Every SKILL.md passes a strict frontmatter check (JDG-07)**: a test parses the frontmatter of every installable entry strictly, at least as strictly as the `skills` CLI.
   - Current: the guard checks the 1,024 cap and `: ` or ` #` on a plain description line only; a continuation line, another key or another YAML error goes unchecked.
   - Target: the frontmatter of every `skills/*/SKILL.md` and of every agent file the installer enumerates parses as strict YAML; for a skill, `name` and `description` are non-empty strings, the description has at most 1,024 characters, and the name has 1-64 lowercase letters, digits and single hyphens and equals its folder.
   - Acceptance: the test passes on the tree and fails on fixtures with an unquoted `: ` on a description's first or continuation line, a tab-indented line, an unterminated quote, a duplicate key, a non-string name, a 1,025-character description, an uppercase name and a name that differs from its folder; each fixture's accept or reject result equals the result of the `yaml` package the skills CLI uses, checked once and recorded in the verification.

9. **Kept skills carry behaviour, not history (JDG-05)**: a test fails on history text in a kept skill, every kept skill passes it, and AGENTS.md states the rule in one line.
   - Current: the history text listed in Background; nothing checks it; AGENTS.md has no such rule.
   - Target: for each of the 16 kept skills, SKILL.md above its trailing evidence section holds no date, no tool version outside a conditional or constraint and no run log; every Markdown file the skill ships (SKILL.md, its references and README; evals excluded) names no concrete planning artifact of this repository (a numbered phase folder or phase file such as `21-SMOKE-CURSOR.md`, or a backlog id such as `999.2`) and no referee name or local router alias; generic project-layout paths pass; provenance lives in the trailing evidence section or a reference; the seven rules skills are exempt by name with the reason; AGENTS.md says in one line that SKILL.md describes behaviour, provenance and version history live in a trailing section or a reference, and version-specific text appears only as a conditional.
   - Acceptance: the test passes on the tree and fails on fixtures holding an ISO date, `gsd-core 1.17.0`, "one real run: the same item scored 0.74, then 0.67", `.planning/phases/18.1-one-runtime-model/18.1-RESEARCH.md:231`, `21-SMOKE-CURSOR.md`, `Backlog 999.2` or `router-env/my-referee-two` in a main flow; it passes on the same date under the evidence heading and on `.planning/config.json`, `.planning/scripts/cross-ai.mjs`, `.planning/phases/<phase>/`, `.planning/phases/**/*-CONTEXT.md`, `NN-SPEC.md` and "gsd-core 1.20 or later"; a doc-contract test pins AGENTS.md's line.
   - *Amended 2026-11-07 (32 D-18):* the shipped Markdown is every `.md` file in the skill folder outside `evals/`, so jev's `backends/` notes count (one names a Phase 21.1 results file under `.planning/phases/`); a bare or phase-prefixed planning decision id such as `(D-07)` or `20 D-11` also fails, while placeholders such as `D-<n>` and `NN D-xx` pass.

10. **Every later phase that changes a SKILL.md cites JDG-04**: each ROADMAP phase of the current milestone after 32 whose text names a SKILL.md has a success criterion citing JDG-04, and `make check-dogfood` fails when one does not.
    - Current: 32.1, 32.2 and 32.3 describe the bar without the id; 34 changes jev's SKILL.md and covers regression only.
    - Target: those four phases cite JDG-04 (amended by this phase); `tools/check_dogfood.py`, the only reader of `.planning/`, fails on a milestone phase after 32 whose text names a SKILL.md but has no success criterion citing JDG-04, and names that phase; backlog entries are not checked until promoted.
    - Acceptance: check-dogfood passes on the tree; its unit test fails on a fixture roadmap holding such a phase and passes once the criterion is added.

## Boundaries

**In scope:**
- The test-location decision, its spike record and the stray-module guard (R1).
- A tracked judge-prompt builder, judge pool selection with recorded substitutes, the judge-count rule (R2-R4).
- A tracked verdict checker promoted from the phase 27 copy, with the round cap and refutation records (R5, R6).
- The baseline judge run of the 15 skills and the committed report with its raw verdicts (R7).
- The strict frontmatter check and the history-text check, with the text fixes the kept skills need (R8, R9).
- AGENTS.md: the round cap, the refute-by-running rule and the behaviour-not-history line (R6, R9).
- JDG-04 citations in 32.1-32.3 and 34 and the check-dogfood guard (R10).

**Out of scope:**
- Bringing any skill to the judge bar, or writing evals and trigger queries — the batch phases 32.1-32.4 (JDG-03, JDG-04).
- Moving test modules into `tests/skills/<name>/` — rejected by the spike (R1).
- Converting the spec-review family's Markdown eval scenarios to `evals.json` — Phase 32.2 (owner, 2026-11-07).
- Trimming evals from the shipped copy — Phase 52 (DIST-01); until then evals reach hosts through the install links (owner, 2026-11-07).
- Judging `ai-kit-commit-fold` and the seven rules skills — excluded (owner, 2026-11-07); they still pass the frontmatter check, and commit-fold passes the text check.
- A config file for the judge list — Phase 33 designs ai-kit's config; the checker takes the list as an argument.
- Vendoring or editing the third-party skill-judge — ai-kit installs only its own skills (DIST-07); the builder reads the installed copy.
- Code comments and docstrings in the history-text check — code names the project paths it reads and writes; shipped-copy contents are Phase 52 (DIST-05).

## Constraints

- Runtime code stays stdlib-only; the verdict checker and the prompt builder are tools, not runtime code, and add no new dependency without the check AGENTS.md requires.
- Phase 32's own SKILL.md edits only move dates, versions, run logs and planning pointers into a trailing evidence section or a reference, or reword them as behaviour; no instruction changes.
- Judge lanes run read-only (review mode) with `AI_KIT_REFUSE_REAL_HOME=1`; a lane whose status line does not report a clean tree is not counted.
- Tests never read `.planning/` (`tests/test_arch.py` `check_no_planning_reader`); the citation guard lives in `tools/check_dogfood.py` and is unit-tested on fixtures.
- No hardcoded absolute path in source, tests or assets; the installed skill-judge is found through the skills roots, and tests use a fixture judge package.
- jev receives summaries only, never skill text, code, config values or secrets; its answer is advisory.

## Acceptance Criteria

- [ ] No test module moved; the stray-module guard passes on the tree and fails on a nested fixture module.
- [ ] Each judge prompt embeds the skill-judge files in full and states the test and scripts readings; prompts differ only in skill name and module list.
- [ ] Every verdict names its judge and lane status; every substitute has a reason; the checker rejects an unlisted judge.
- [ ] The judge-count rule's tests pass, and the report's per-skill counts and reasons equal the rule's output.
- [ ] The verdict checker gives the same digest from a sub-folder, rejects malformed, miscomputed or mis-pinned verdicts, reports stale digests and round counts, and contains no `referee` text.
- [ ] AGENTS.md caps judge loops at three rounds and requires refutation by running, pinned by a doc-contract test; the checker flags a four-round loop.
- [ ] The committed report covers 15 judged and 8 excluded skills with bar results, and the checker run on it exits 0 with every skill current.
- [ ] The strict frontmatter test passes on the tree and fails on each listed fixture; the fixture results match the `yaml` package's, recorded once.
- [ ] The history-text test passes on every kept skill and fails on each listed fixture; AGENTS.md's one-line rule is pinned.
- [ ] 32.1, 32.2, 32.3 and 34 cite JDG-04, and check-dogfood fails on a fixture phase without the citation.
- [ ] `make test` and `make check-dogfood` pass.

## Edge Coverage

**Coverage:** 58/58 applicable edges resolved · 0 unresolved (58 engine rows, 0 added; 2 rows from the 2026-11-07 R9 amendment)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | A helper or fixture file in a `tests/` subfolder whose name does not match `test_*.py` (for example `tests/fixtures/archived/26/skill-judge/check_verdicts.py.txt`) never trips the guard |
| empty | R1 | ✅ covered | A `tests/` tree with no subfolder, or subfolders holding no `test_*.py`, passes; the guard on an empty fixture tree passes |
| encoding | R1 | ✅ covered | The guard matches `test_*.py` case-sensitively, the same pattern the runner's glob uses |
| ordering | R1 | ✅ covered | The guard reports every stray path in sorted order, not only the first |
| concurrency | R1 | ✅ covered | The guard reads the tree once and writes nothing, so it runs beside other modules with no shared state |
| boundary | R2 | ✅ covered | A `scripts/` folder holding only non-runnable files (a `.py.txt` template) does not make a skill ship code; one runnable `.py` or `.mjs` file at the skill root or under `scripts/` does |
| adjacency | R2 | ✅ covered | A skill that only drives another skill's code (spec-config through spec-review's package) ships no runnable code and gets the 8/7 split; its module list is shown for context and not scored |
| empty | R2 | ✅ covered | A skill whose rule finds no test module gets an explicit "no script test found" line, never an omitted list |
| encoding | R2 | ✅ covered | Embedded files are copied byte for byte as UTF-8; the builder records each file's sha256 and the test compares bytes |
| ordering | R2 | ✅ covered | Embedded files follow a fixed order (SKILL.md, the rubric, the cited spec files in the rubric's table order, the schema) and the module list is sorted, so the same tree gives the same prompt |
| precision | R2 | ✅ covered | `rubric_version` and `spec_sha` are copied from the rubric's first two lines as text; a rubric without them stops the build |
| concurrency | R2 | 🧪 backstop | Every prompt of a run records the spec_sha it embedded, and the checker rejects a verdict whose pin differs from that record, so a judge update during a run cannot mix rubrics (held-out edge test) |
| boundary | R3 | ✅ covered | With exactly one usable configured judge the pool is that judge plus native Opus at xhigh; with two or more, the first two usable |
| adjacency | R3 | ✅ covered | A judge that passes its probe but fails its round is replaced for that round only, with the reason recorded; its other rounds keep it |
| empty | R3 | ✅ covered | With no usable configured judge, or an empty list, native Opus runs alone; a skill that needs two judges then gets one and is marked "second judge unavailable", never two runs of one judge counted as two |
| encoding | R3 | ✅ covered | A verdict's `judge` field is compared with the judge list as an exact string, not case-folded or trimmed |
| ordering | R3 | ✅ covered | Judges are probed in the configured order and the first two usable win; the report lists them in that order |
| precision | R3 | ✅ covered | A probe counts as usable only on a clean exit with the expected one-word answer inside its timeout; a slow lane is unusable, never partly usable |
| concurrency | R3 | 🧪 backstop | Lanes for different skills may run in parallel; each writes its own output file, and a lane whose status line does not report a clean tree is discarded and not counted (held-out edge test) |
| boundary | R4 | ✅ covered | 73.0 and 87.0 give two judges; 72.9 and 87.1 give one, unless another trigger or jev raises it |
| adjacency | R4 | ✅ covered | A last verdict at exactly 80.0 gives two; a high finding and an in-band percent together still give two, never more |
| empty | R4 | ✅ covered | No rubric-v4 verdict gives two; a verdict with no findings and a percent outside the band gives one unless jev raises it |
| ordering | R4 | ✅ covered | The deterministic triggers are checked first and jev is asked only when they give one, so no jev call happens for a skill already at two |
| precision | R4 | ✅ covered | Percents are compared at their recorded one-decimal value, never re-rounded; the band test is a distance from 80 of at most 7.0 |
| boundary | R5 | ✅ covered | A score equal to its max, a total equal to max_total, and percents of exactly 80.0 (B) and 79.9 (C) are accepted and graded by the rubric bands |
| adjacency | R5 | ✅ covered | A skill folder whose name prefixes another (`ai-kit-spec-review` and `ai-kit-spec-review-fixer`) digests only its own files; two verdicts from one judge for one skill in one round are an error, not merged |
| empty | R5 | ✅ covered | A skill with no tracked files is an error naming it; a round without a verdict reports "no verdict"; a verdict with no findings is valid only when every score is at its max |
| encoding | R5 | ✅ covered | Digests hash raw file bytes over the git-listed POSIX paths relative to the root, so line endings and the working directory never change a digest |
| ordering | R5 | ✅ covered | Files are sorted by path before digesting and skills print in the order given, so the output is stable between runs |
| precision | R5 | ✅ covered | The percent is recomputed with the rubric's formula round(total / max_total * 100, 1); with 125 points every percent is a whole tenth, so no tie arises; any difference rejects the verdict |
| concurrency | R5 | 🧪 backstop | The checker only reads; a file changed between two runs shows as stale on the later run and two parallel runs print the same output (held-out edge test) |
| boundary | R6 | ✅ covered | Three rounds pass and a fourth is flagged over the cap; the count is per skill |
| precision | R6 | ✅ covered | A re-run of a failed lane inside the same round adds no round; rounds are counted from the recorded round entries, one per judging pass on the same skill text |
| boundary | R7 | ✅ covered | A worst judge at exactly 80.0 with a high finding meets the bar through "grade B or better"; at 79.9 with a high finding it does not |
| adjacency | R7 | ✅ covered | When two judges disagree, the worst judge decides the bar result and its clause is the one named |
| empty | R7 | ✅ covered | A skill with no finished verdict is reported "not judged" with its lane failure and no score, and the checker run fails until a verdict exists |
| encoding | R7 | ✅ covered | The report copies numbers from the verdict JSON as written; percents keep one decimal |
| ordering | R7 | ✅ covered | Judged skills are listed by owning batch phase, then by name; excluded skills follow in name order |
| precision | R7 | ✅ covered | The inter-judge spread is the absolute difference of the two percents to one decimal; it is information only and never changes a bar result |
| concurrency | R7 | ✅ covered | A batch phase refreshes only the rows of the skills it judged; the checker run always covers the whole report |
| boundary | R8 | ✅ covered | A 1,024-character description passes and a 1,025-character one fails; a 64-character name passes and a 65-character one fails |
| adjacency | R8 | ✅ covered | A name that equals its folder except for case, holds a double hyphen, or starts or ends with a hyphen fails |
| empty | R8 | ✅ covered | An empty description, a frontmatter block with no keys, or a file with no frontmatter fails with the file named |
| encoding | R8 | 🧪 backstop | The cap counts characters of the parsed string; a description with a non-ASCII character counts it as one character (held-out edge test) |
| ordering | R8 | ✅ covered | Every failing entry is reported, not only the first; key order inside the frontmatter does not matter |
| precision | R8 | ✅ covered | Folded and literal block scalars are measured after YAML folding, as the parser returns them; the cap is an exact integer comparison |
| concurrency | R8 | ✅ covered | The check only reads the tree; no shared state |
| boundary | R9 | ✅ covered | *(row from the 2026-11-07 R9 amendment, 32 D-18)* `(D-07)` and `20 D-11` fail; `D-<n>`, `NN D-xx` and a bold format example such as `**D-14: …**` pass; a `.md` file directly under `evals/` or deeper is never read |
| precision | R9 | ✅ covered | *(row from the 2026-11-07 R9 amendment, 32 D-18)* A decision id matches only as a whole token (`D-` and digits, not glued to a letter or digit), so `JDG-04` or `ID-07` never counts as a decision id |
| adjacency | R9 | ✅ covered | A version inside a URL or a code span is a literal identifier and passes; the same version written in prose beside a tool name fails; a date fails anywhere in the main flow, code spans included |
| empty | R9 | ✅ covered | A SKILL.md with no trailing evidence section is checked in full; an empty evidence section is allowed |
| encoding | R9 | ✅ covered | The check reads decoded UTF-8 text; the date form checked is ISO `YYYY-MM-DD` plus "as of" phrases |
| ordering | R9 | ✅ covered | The evidence section must be the last `##` section; text after it, or an evidence heading placed earlier, is checked as main flow |
| concurrency | R9 | ✅ covered | The check only reads the tree; no shared state |
| adjacency | R10 | ✅ covered | `JDG-04` inside a criterion's citation list counts; `JDG-04` outside the success criteria (Requirements line, code anchors) does not |
| empty | R10 | ✅ covered | A milestone phase after 32 that names a SKILL.md but has no success-criteria block is flagged; a roadmap with no such phase passes |
| encoding | R10 | ✅ covered | The id matches as the exact token `JDG-04`; `JDG-040` or `jdg-04` does not count |
| ordering | R10 | ✅ covered | Every offending phase is reported in roadmap order, not only the first |

## Prohibitions (must-NOT)

**Coverage:** 5/5 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT substitute a judge model without recording which ran and why | R3, R7 | resolved | verification: test — the checker rejects a verdict whose `judge` is not in the given list; judgment for the substitute's reason line |
| MUST NOT edit, drop or re-run over a recorded raw verdict to improve a result; a re-judge adds a round | R5, R7 | resolved | verification: test — the checker requires every report number to equal its raw verdict JSON and counts rounds from the recorded files |
| MUST NOT send skill text, code, config values or secrets to jev | R4 | resolved | verification: test — the jev item for the judge count is built from numbers and fixed summary text, pinned on a fixture |
| MUST NOT let a judge lane write to the repository, or touch the owner's real host configs or HOME | R3, R7 | resolved | verification: judgment — read-only review mode, `AI_KIT_REFUSE_REAL_HOME=1`, a lane counted only when its status line reports a clean tree |
| MUST NOT change a skill's behaviour through this phase's history-text edits | R9 | resolved | verification: judgment — each SKILL.md diff is a move into the evidence section or a reference, or a history-to-behaviour rewording |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | 15 judged and 8 excluded skills, one report, a checker, two text checks |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | Reaching the bar, evals, eval conversion and dist trimming named out of scope |
| Constraint Clarity | 0.82  | 0.65 | ✓      | Noise 7 points, cap 3 rounds, read-only lanes, no planning reader in tests; the bar-boundary reading needs owner confirmation |
| Acceptance Criteria| 0.85  | 0.70 | ✓      | Each requirement has a fixture test, a checker run or a pinned doc line |
| **Ambiguity**      | 0.13  | ≤0.20| ✓      | Round 0 (roadmap and requirements only): 0.36 |

## Interview Log

`--auto`, one round. The open items went through jev: one advisory answer per item, and `needs_fallback` items
are decided by own reasoning. Summaries only, advisory. Rule: best design over the smallest diff (`mvp-mode`
inactive). Every answer came back `needs_fallback`: Laya answered each item alone (S1 and S2 over its
2,000-character guard, the rest below its threshold), and the consented TypeSafe batch merged all ten items into
one state over that row's 8,000-character guard, so every remote answer was forced. Own reasoning decided all ten.

| Round | Perspective | Question summary | jev (advisory) | Decision locked |
|-------|-------------|------------------|----------------|-----------------|
| 1 | Researcher | Where do tests live (S1)? | low: laya flat 0.41 (forced), typesafe flat 0.81 (forced) | **Own reasoning:** flat; per-skill folders would assign shared tests to one skill, leave six skills with none, and need discovery, mapper and table changes (R1) |
| 1 | Researcher | D7 split for a skill with code but no `scripts/` (S2)? | low: laya restructure 0.36 (forced), typesafe code_counts 0.57 (forced) | **Own reasoning:** runnable code counts as scripts (5/5/5); the literal reading would never score five code skills' tests (R2) |
| 1 | Failure Analyst | Which grade boundaries count for "within judge noise" (S3)? | low: laya bar_only 0.65, typesafe every_band 0.84 (forced) | **Own reasoning:** the bar boundary 80 only; with 7-point noise every percent from 53 to 97 is near some band edge, which would leave the one-judge branch and jev's score dead (R4); needs confirmation |
| 1 | Simplifier | Judges for a skill with no rubric-v4 verdict (S4)? | low: laya one_unless_screened 0.54, typesafe two 0.68 (forced) | **Own reasoning:** two; no verdict means an unknown distance to the bar, and the baseline sets four batches' work (R4) |
| 1 | Boundary Keeper | Round cap (S5)? | low: laya five_rounds 0.54, typesafe three_rounds 0.76 (forced) | **Own reasoning:** three, the cap phases 27-31 ran; seven rounds did not converge (R6) |
| 1 | Boundary Keeper | How strict about `.planning/` paths (S6)? | low: laya history_only 0.57, typesafe allowlist 0.75 (forced) | **Own reasoning:** neither as phrased; the scan shows generic layout paths are legitimate (globs, placeholders, `milestones/`), and every history pointer names a concrete artifact, so the rule fails concrete artifacts only (R9) |
| 1 | Boundary Keeper | Which files the history check reads (S7)? | low: laya skill_md_only 0.43, typesafe split 0.88 (forced) | **Own reasoning:** split; main-flow rules on SKILL.md, pointer rules on all shipped Markdown, since references hold dated capability cells on purpose (R9) |
| 1 | Boundary Keeper | Must phase 32 bring edited skills to the bar (S8)? | low: laya reach_bar 0.68, typesafe record_only 0.98 (forced) | **Own reasoning:** record only; the roadmap gives phase 32 the record criterion, and the bar needs evals the batches write (R7, Boundaries) |
| 1 | Seed Closer | Name rules in the frontmatter check (S9)? | low: laya with_name_rules 0.58, typesafe with_name_rules 0.75 (forced) | **Own reasoning:** yes; the spec and the judge's D4 require them and all 23 pass (R8) |
| 1 | Failure Analyst | Guard against a test module in a `tests/` subfolder (S10)? | low: laya guard 0.70, typesafe guard 0.94 (forced) | **Own reasoning:** yes; the rubric's fix text points to `tests/skills/<name>/`, where a module runs in no gate (R1) |
| 1 | Seed Closer | Judge before or after this phase's text edits? | none | After: a verdict whose digest differs from the tree is stale, so a baseline taken before the edits would be stale at once (R7) |
| 1 | Seed Closer | Which noise figure? | none | 7 percentage points, the project's recorded value (29-JUDGE.md) (R4) |
| 1 | Seed Closer | A permanent citation guard or a one-time fix? | none | **Own reasoning:** a check-dogfood guard; phases are inserted mid-milestone (38.1, 45.1, 47.1) and nothing else adds the criterion (R10) |

---

*Phase: 32-re-judge-baseline*
*Spec created: 2026-11-07*
*Next step: /gsd-discuss-phase 32 — implementation decisions (how to build what's specified above)*
