# ai-kit skills against the new skill-judge (inventory for a re-judge phase)

Date: 2026-11-02. Read-only. No judge or model was run. Checkout at commit 27337d5.

Scripts in this folder:

- `15_inventory.py` lists, per skill, the SKILL.md line count, the `evals/` files, the tests that
  name the skill, and each script with a flag for whether a skill doc invokes it. Output is in
  `15_inventory.out`. The test list it prints is broad, because it matches module names, so the
  table below gives the curated main tests.
- `15_judge_history.py` collects every recorded score (`NNN/120`, `NNN/125`, verdict JSON) from
  `SKILL-JUDGE*.md` files and `skill-judge/` round folders. Output is in `15_judge_history.out`.
  The "last result" column below was then checked by hand against each report's verdict block.

## 1. What the new judge expects

Source: `~/.claude/skills/skill-judge/` (a symlink to `~/.agents/skills/skill-judge`).
`references/rubric.md` starts with `rubric_version: 4` and
`spec_sha: 69ef37e9424c0a7ea9dd2293b559e43ec8176379`. The rubric is byte-identical to the source
copy in `agent-toolkit/skills/skill-judge/`. The source copy is newer in two places. Its SKILL.md
adds one line that loads `references/profiles/command.md` or `agent.md` "only when the prompt
judges a command or agent". It also has two more eval fixtures (`ship-note.md`,
`triage-agent.md`). Neither change affects judging a skill. To use the source copy, reinstall it
first.

### Dimensions (125 points)

- D1 Knowledge Delta, 20 points: "Value = expert-only knowledge minus what the agent already
  knows". Each H2 section is classed as expert, activation or redundant, and the ratio is
  weighted by line count. Content that the harness does natively (plan mode, todo tracking,
  sub-agent dispatch, memory files) is flagged.
- D2 Mindset, Procedures and Patterns, 15 points: mindset and procedures score 0-11, and pattern
  fit scores 0-4 (Mindset, Navigation, Philosophy, Process or Tool). Pattern fit used to be its
  own dimension.
- D3 Anti-Pattern Quality, 15 points: a NEVER list with reasons. The 12-15 band needs "a Gotchas
  section of environment-specific facts that defy assumptions".
- D4 Specification Compliance, 15 points: the frontmatter and the description. The description
  needs WHAT, WHEN, KEYWORDS and a boundary against near-miss neighbours. A D4 fix "is the full
  replacement description text".
- D5 Progressive Disclosure, 15 points: the body stays under 500 lines (over 500 is "at least
  high"). Optional references are gated by a condition, with "Do NOT Load" where over-loading is
  a risk.
- D6 Freedom Calibration, 15 points: specificity matches fragility. The skill should give
  "a clear default with an escape hatch" rather than a menu.
- D7 Tests and Evals, 15 points. This dimension is new; the old one was "Pattern Recognition
  (10)".
- D8 Practical Usability, 15 points: decision trees, working examples, fallbacks, edge cases,
  validation loops.

Grades go by percent: "A at 90 or more, B at 80, C at 70, D at 60, otherwise F". Severity: "high =
a wrong or harmful instruction, or a dimension scored in its bottom band". So a skill with no
evals at all gets D7 in its bottom band (0-3), and that also produces a high finding.

### What D7 (evals and tests) requires

- Output evals go in `evals/evals.json`, with input files in `evals/files/`. The judge looks for
  "realistic prompts (casual and precise phrasings, at least one edge case), expected output,
  input files, and verifiable assertions". The working shape, from the judge's own file and from
  `ai-kit-spec-goal-prompt`, is
  `{"skill_name", "evals": [{"id", "prompt", "expected_output", "files", "assertions"}]}`.
- Trigger queries go in `evals/trigger-queries.json`: "about 20 queries, 8-10 should-trigger and
  8-10 should-not-trigger, with near-misses among the negatives". The shape is a list of
  `{"query", "should_trigger"}`.
- Script tests: "The runnable script test lives in the repository's `tests/skills/<name>/`". The
  scripts must also be "runnable non-interactively, document usage with `--help`, emit structured
  output and have at least a smoke test".
- Point split: when `scripts/` exists, output evals, trigger queries and the script test are worth
  5 points each. Without `scripts/`, the split is "output evals 8, trigger queries 7".
- Bands: "0-3 no tests; 4-8 partial ... 9-11 solid ... 12-15 complete, realistic, verifiable and
  maintained alongside the skill".
- Repository-required files, which are never a deduction: `README.md`, `evals/`, bundled
  `references/` files and `SOURCE.json`.

### What "decision-branch" means

This is D8 combined with protocol step 4: "Then D8: identify the inputs, follow each decision
branch and each example to its outcome, and cite the failing branch in the finding. Credit D8
only for branches you actually followed." The rubric adds: "Mentally run each decision tree to
see whether it reaches the right choice." In practice, every if/else in a SKILL.md, every row of
a routing table and every example gets traced. A branch that leads to a wrong or undefined
outcome costs D8 points. This is why skills with many resume or fallback paths, such as
execute-superpowers, keep losing points.

### Two traps for ai-kit

- No `tests/skills/<name>/` folder exists in ai-kit. Tests are flat files named
  `tests/test_<skill>_*.py`. Phase 27 handled this by naming the test files in the prompt. The
  re-judge must do the same for every skill, or move the tests (the test runner and
  `test_gate_scope.py` would need changes for that).
- Only 5 skills have a `scripts/` folder: spec-discuss, goal-prompt, jev, markdown-to-pdf and
  mermaid-audit. The other code skills keep a top-level `ai-kit-*.py` entry point plus a package.
  A literal judge applies the 8/7 split to those skills and never looks at their tests. Which
  split a judge picks is unverified, so the prompt should state it, and it should stay the same
  for every skill.

## 2. Per-skill inventory

Key: "lines" is the SKILL.md line count. "Scripts" are top-level code files plus `scripts/` and
`evals/` code; package modules are left out (`13-orphaned-scripts.md` checked those, and all have
an importer). The last result is the newest final verdict on record. "old" means the 120-point
rubric and "new" means the 125-point rubric version 4. Old scores are not comparable with new
ones.

| Skill | Lines | evals/ | Main tests | Scripts (invoked?) | Last judge result | Slated for removal |
|---|---|---|---|---|---|---|
| ai-kit-cross-ai | 191 | none | test_cross_ai_skill_text, test_cross_ai_runner_e2e, test_quota_policy_text (text only) | none of its own; names `.planning/scripts/cross-ai.mjs` and spec-review's template | old 102/120 (85.0%) PASS, 2026-10-25, phase 25.1 | no |
| ai-kit-gsd-curated-config | 406 | 4 old markdown evals (`01-..04-*.md`) | test_ai_kit_gsd_curated_config(+_matrix), 12 test_curated_config_*, test_gsd_curated_eval | 1 entry, invoked | old 106/120 (88.3%) PASS, 2026-10-25, phase 25.1 | no |
| ai-kit-gsd-spec-discuss | 294 | none | test_ai_kit_gsd_spec_discuss, _e2e | 3 in scripts/, all invoked | old 106/114/109 per judge (Opus/referee-two/referee-one, round 4), PASS conditional, 2026-10-24, quick 261024-ryk | no |
| ai-kit-opencode-providers | 175 | none | test_ai_kit_opencode_providers | 1 entry, invoked | old 108/120 PASS, 2026-10-17, phase 18.1 | yes |
| ai-kit-project-rules-agents | 156 | none | test_ai_kit_project_rules_agents, test_ai_kit_rules_common (shared) | 1 entry, invoked | old 93/120 (77.5%) FAIL, owner accepted and deferred, 2026-10-30, phase 26 round 15 | no |
| ai-kit-project-rules-all | 242 | none | test_ai_kit_project_rules_all, _all_e2e | 1 entry, invoked | old 102/120 PASS, 2026-10-30, phase 26 | no |
| ai-kit-project-rules-arch | 181 | none | test_ai_kit_project_rules_arch | 1 entry, invoked | old 100/120, 2026-09-14, phase 12 | no |
| ai-kit-project-rules-cicd | 299 | none | test_ai_kit_project_rules_cicd | 1 entry, invoked | old 103/120, 2026-09-14, phase 14 | no |
| ai-kit-project-rules-docker | 251 | none | test_ai_kit_project_rules_docker | 1 entry, invoked | old 103/120, 2026-09-14, phase 13 | no |
| ai-kit-project-rules-makefile | 231 | none | test_ai_kit_project_rules_makefile | 1 entry, invoked | old 103/120, 2026-09-14, phase 10 | no |
| ai-kit-project-rules-precommit | 245 | none | test_ai_kit_project_rules_precommit | 1 entry, invoked | old 103/120, 2026-09-14, phase 11 | no |
| ai-kit-session-wake | 185 | none | test_ai_kit_session_wake, _fire, _reset, test_claude_session_wake_hook | 1 entry, invoked | old 108/120 PASS, 2026-10-30, phase 26 | no |
| ai-kit-spec-config | 493 | none | no own test; the shared `ai_kit_spec` tests plus test_cross_ai_skill_text, test_ai_kit_spec_runtimes_table | none of its own; drives spec-review's `ai-kit-spec.py` | old 99/120 UNRESOLVED, 2026-10-25, phase 25.1 | no |
| ai-kit-spec-execute | 79 | none | test_ai_kit_spec_gsd, test_ai_kit_spec_superpowers (detect_framework) | 1 (`detect_framework.py`), invoked | no record found | no |
| ai-kit-spec-execute-gsd | 398 | none | test_ai_kit_spec_gsd, _gsd_tools | 1 entry, invoked | old 101/120 UNRESOLVED, owner accepted and deferred, 2026-10-30, phase 26 round 15 | yes |
| ai-kit-spec-execute-superpowers | 289 | none | test_ai_kit_spec_superpowers | 1 entry, invoked | old 86/120 (71.7%) FAIL, owner accepted and deferred, 2026-10-31, phase 26 round 24 | no |
| ai-kit-spec-goal-prompt | 194 | new shape: evals.json (10), trigger-queries.json (20: 10 positive, 10 negative), files/ | 15 test_ai_kit_spec_goal_prompt_* (one of them checks the evals) | 8 in scripts/; goal_prompt.py invoked, 7 helpers imported by it | new: referee-one 118/125 (94.4% A), referee-three 109/125 (87.2% B), verdict UNRESOLVED (below its own base 90.4), 2026-11-02, phase 27 round 7 | no |
| ai-kit-spec-review | 492 | 4 old markdown evals | test_ai_kit_spec, _e2e, _env_scrub, _legacy_config, _routing, _runner_dispatch, _runtimes_table, _trust, test_cross_ai_catalog | 1 entry, invoked; package module `cross_ai_catalog.py` used only by its test | old 99/120 PASS, 2026-10-25, phase 25.1 | no |
| ai-kit-spec-review-checklist | 296 | old: test-scenarios.md, orchestrator-integration.md, fixtures/ | test_framework_profiles | none | no record found | no |
| ai-kit-spec-review-fixer | 115 | old: test-scenarios.md | none (only named in test_wizard_pty) | none | no record found | no |
| ai-kit-usage-metrics | 313 | none | test_ai_kit_usage_metrics | 1 entry, invoked | old 108/120, 2026-09-10, phase 5 (v1.0); phase 15.1 planned a re-judge, but no score was found | no |
| cst-refactor | 102 | none | no own test (test_gate_scope only checks that the template ships) | none; ships `codemod_template.py.txt`, which SKILL.md tells the agent to copy in | old 91/120 FAIL (1 Important open), 2026-10-15, phase 16.1 independent judge | no |
| jev-fast-decision | 62 | `cases.jsonl` (32 labelled cases for `screen()`; backend calibration, not skill evals) | test_jev_fast_decision, test_jev_skill_install_e2e, test_decision_probe | 2 in scripts/; jev_review.py invoked; **eval_cases.py never invoked by the skill** | old: Opus 107/120 pass, opencode 101/120 (usability below its floor), UNRESOLVED, 2026-10-23, phase 21.1 | no |
| markdown-to-pdf | 103 | none | test_markdown_to_pdf | 3 in scripts/; markdown_to_pdf.py invoked, 2 helpers imported by it | no record found | no |
| mermaid-audit | 273 | fixtures, gold.json, judge-protocol.md, score_consensus.py (plus stray `__pycache__`) | test_mermaid_style | 3 in scripts/, all invoked; evals/score_consensus.py is named only by evals/judge-protocol.md (an eval tool) | no record found | yes |

### Scripts the skill never uses

- `skills/jev-fast-decision/scripts/eval_cases.py`: only `tests/test_jev_fast_decision.py` runs
  it. SKILL.md and reference.md never name it. It re-scores `evals/cases.jsonl`, and
  `--calibrate` rewrites `min_confidence` in `jev_review.py`. Fix: add a short "re-calibrate"
  step to `reference.md`, or move it out of the shipped skill.
- `skills/ai-kit-spec-review/ai_kit_spec/cross_ai_catalog.py`: a package module that only its
  drift test calls. No doc tells a maintainer to run it after editing `cross-ai-errors.json`.
- `skills/mermaid-audit/evals/score_consensus.py`: an eval-side tool, named only by
  `evals/judge-protocol.md`. It does not matter, because the skill is being removed.
- All other entry scripts and `scripts/` files are named in their own SKILL.md or imported by a
  script that is.

### Summary of the gaps

- Only one skill (goal-prompt) has evals in the new judge's shape. Four skills have old markdown
  evals (curated-config, spec-review, checklist, fixer), one has JSONL calibration cases (jev),
  and 19 have nothing. Owner capture P2 in `27-OWNER-CAPTURES.md` already logs this as refactor
  debt.
- No skill has `tests/skills/<name>/`.
- Two bodies sit just under the 500-line D5 limit: spec-config (493) and spec-review (492).
- Five skills were never judged: spec-execute, review-checklist, review-fixer, markdown-to-pdf
  and mermaid-audit. Only goal-prompt has a new-rubric score.
- Three verdicts are accepted but open (execute-gsd, execute-superpowers, rules-agents). The todo
  `.planning/todos/pending/2026-10-31-refactor-execute-gsd-and-rules-agents-sj-1-sj-3.md` tracks
  them, and it asks for a re-judge "with the NEW percent-based skill-judge rubric".

## 3. Proposed batches (a proposal, not decided)

Assumption: first, one re-judge phase scores all 22 kept skills on the new rubric. That gives
each skill a new-rubric base. The decimal phases below then improve the skills batch by batch.
They run lowest risk first, so the eval format and the test-naming convention settle on the
cheap skills before the large ones. Removal of opencode-providers, mermaid-audit and
spec-execute-gsd should land before the re-judge, so no judging is spent on them.

1. **General small skills**: cst-refactor, markdown-to-pdf, jev-fast-decision,
   spec-review-fixer. Main gap: no evals in the new shape. jev also needs `eval_cases.py`
   adopted, and its usability lane is the one that stayed below its floor. These skills are
   small and isolated, so they are cheap to try the evals/trigger-queries template on (copy the
   goal-prompt shape and its `test_*_evals.py` checker).
2. **Rules checkers**: project-rules-arch, -cicd, -docker, -makefile, -precommit. They share
   `skills/_shared/ai_kit_rules_common`, have the same structure, and all have the same gap: no
   evals or trigger queries, last judged in September on the old rubric. One template covers all
   five. Their near-miss negatives write themselves, because each description already names its
   siblings.
3. **Rules agents and orchestrator, plus usage-metrics**: project-rules-agents, project-rules-all,
   usage-metrics. Main gap: rules-agents is an accepted FAIL waiting for a refactor. That depends
   on the decision in backlog 999.16 (one event-keyed playbook skill), so decide 999.16 first.
   usage-metrics just needs evals. Medium risk.
4. **Spec review family**: spec-review, spec-review-checklist, spec-config, spec-execute. They
   share the `ai_kit_spec` package and its tests. Main gaps: body size near 500 lines
   (spec-review, spec-config), old markdown evals that need converting, and checklist and
   spec-execute never judged. Higher risk, because the routing tables give D8 many branches to
   trace.
5. **Execution and session chain**: spec-execute-superpowers, spec-goal-prompt, session-wake,
   cross-ai, gsd-curated-config, gsd-spec-discuss. This is the largest and riskiest group: many
   resume and fallback paths, and the accepted superpowers FAIL. Split it in two if one round does
   not fit: superpowers, session-wake and cross-ai first (single pinned-resume path, as the todo
   asks), then curated-config, spec-discuss and goal-prompt (goal-prompt mainly needs its
   UNRESOLVED verdict closed). Backlog 999.17 touches the same execute skills, so order it after
   this batch or merge it in.

## 4. How judging ran in v1.3, and what to reuse

- **Lanes**: the judges are `router-env/my-referee-one`, `-two` and `-three`. They run through pi:
  `node .planning/scripts/cross-ai.mjs --runtime pi --model router-env/<ref> --route-pi router
  --mode review --outer-timeout 3600`, wrapped in
  `node .claude/gsd-core/bin/gsd-tools.cjs run-with-timeout 3600` with
  `AI_KIT_REFUSE_REAL_HOME=1`. A PONG probe picks the lanes that are up. Native Opus stopped after
  2026-10-30, so it is now only a fallback.
- **Prompt building**: in phase 27, `tmp/p27/judge_prep.sh` copies the 9 installed judge files
  (SKILL.md, rubric.md, verdict.schema.json and the 6 agentskills spec files) into `tmp/` as
  read-only files. `tmp/p27/judge/prompt-template-r7.txt` is a 4-step prompt adapted from the
  judge's `references/judge-prompt.md`: read the copied SKILL.md and run its protocol, read the
  rubric and the cited spec files in full, name the `tests/test_<skill>_*.py` files because
  `tests/skills/<name>/` is absent, and print only the verdict line. `run_lane7.sh` fills in the
  judge name and runs one lane. `build_report.py` turns lane output into a report under
  `skill-judge/rN/`. `digest.py` prints the package digest. `show_findings.py` lists the findings.
  All of these live in `tmp/p27/`, which is gitignored and so is not durable. Copy them into the
  new phase folder before relying on them.
- **The round-23 failure** (phase 26, execute-superpowers): the round was "judged without its
  rubric, discarded". The old prompt builder "embedded only `SKILL.md`" (from the pending todo
  above). Phase 26 kept its other round scratch in an ignored directory, and that older builder
  (the `build.py`-style one) is not on disk any more. The only `build.py` found is
  `.planning/docs/system-one-decision-skill/scratchpad/build.py`, which is unrelated jev authoring
  scratch. Lesson for the new phase: the rubric and its spec files must be read or embedded on
  every run, and the checker should reject a verdict whose `rubric_version` or `spec_sha` does not
  match `rubric.md`. The phase 27 checker already does this.
- **Checkers**, all archived:
  - `.planning/milestones/v1.3-phases/27-one-shot-goal-and-loop-prompt-skill/skill-judge/check_verdicts.py`
    (219 lines). This is the new-rubric checker and the best base to reuse. It validates the
    schema (keys, D1..D8, severities, `rubric_version` and `percent` types), recomputes the grade
    and percent, computes the package digest, applies the pass rule
    `((critical 0 and high 0) or percent >= 80) and percent >= base`, has `--gate` (owner
    acceptance) and `--self-test`.
  - `26-.../skill-judge/check_verdicts.py` (99 lines), `25.1-.../check_verdicts.py` (68 lines) and
    `21.1-.../check_verdict.py` (269 lines) are old 120-point checkers.
  - Fixes needed before reuse: the phase 27 checker hardcodes `SKILL = "ai-kit-spec-goal-prompt"`
    and its judge table, so make both arguments to cover 22 skills. `tmp/p27/digest.py` loads
    `.planning/phases/27-.../check_verdicts.py`, a path the archive commit 0c9c863 moved to
    `.planning/milestones/v1.3-phases/`, so that path is now stale.
- **Pass rule**: AGENTS.md already uses percent bands ("a grade of B or better ... and no
  regression ... beyond the judge's run-to-run variation"). Every old score is on the 120-point
  scale, so the first re-judge sets new bases. Treat that as a baseline round, not a regression
  check. Run-to-run noise was measured at about 7-10 points on unchanged packages (phase 26:
  session-wake 115 then 108; superpowers 86-104). Phase 27 on the new rubric gave the same
  package 94.4% from one referee and 87.2% from another.

What I skipped: I did not read the SKILL.md bodies for quality, so the batch gaps come from
structure (evals, tests, size, verdict history) and not from a dimension-by-dimension read. Dates
for archived phases come from the dates written in the reports, because the archive move reset
the git dates to 2026-11-02.
