---
phase: 27
cycle: 1
reviewers: [plan-checker, referee-two]
reviewed_at: 2026-10-31T03:33:00Z
plans_reviewed: [27-01-PLAN.md, 27-02-PLAN.md, 27-03-PLAN.md, 27-04-PLAN.md, 27-05-PLAN.md, 27-06-PLAN.md, 27-07-PLAN.md, 27-08-PLAN.md, 27-09-PLAN.md, 27-10-PLAN.md, 27-11-PLAN.md, 27-12-PLAN.md, 27-13-PLAN.md]
models:
  referee-two: "router-env/my-referee-two"
model_sources:
  referee-two: "pinned"
---

# Cross-AI Plan Review - Phase 27

## Review conditions

Cycle 1 of at most 3, over the 13 plans committed in c84e513. The cross-AI lane ran through `node .planning/scripts/cross-ai.mjs --runtime pi --model router-env/my-referee-two --route-pi router --mode review --outer-timeout 3600`: exit 0, 367 s, tree clean afterwards (status line `AIKIT-XAI status=ok ... tree=clean`). The prompt (48 KB) inlined the ROADMAP Phase 27 section, GPS-01..GPS-04, PROJECT.md (first 80 lines), 27-SPEC.md and 27-CONTEXT.md, referenced the plans, 27-RESEARCH.md, 27-PATTERNS.md, 27-VALIDATION.md, AGENTS.md and 26-12-PLAN.md by repo path, and asked for the ponytail lens, cheap-model executability (greppable criteria, path-agnostic commands, no real-home access), cross-AI reviewability, SPEC coverage and safety, with locked decisions not re-litigable.

Not run: `my-referee-one` (reported down by the owner on 2026-10-31); `my-referee-three` (its route did not answer the PONG probe at 0, 60 and 120 s; the probe was stopped before the tree was edited). No native Opus reviewer was used (owner rule). One available reviewer is enough; the plan checker is the second reader. The review is read-only: the lane did not edit the tree.

## Referee-two review (verbatim)

## Verdict
REVISE

## Concerns
1. [HIGH] 27-06/Task 1 and 27-07/Task 1: D-27 says an OpenGSD scope yields one strategy and `/goal` or a loop only when the project or plans are not OpenGSD or the user asks. The matrix and renderer instead always add `autonomous` as a second block (M02b), and the shared-rails rule puts `## Rails` after `COPY TO HERE` whenever the list is not exactly `autonomous`. The workflow greps the whole argument string (`autonomous.md:28-58`), so a following `/goal` block or `## Rails` is inside `$ARGUMENTS`. -> For OpenGSD with a user-requested goal/loop, emit one flags-only block; put the requested strategy in the three-sentence wrapper, not in the fenced text.
2. [HIGH] 27-06/Task 1: the fixed QUOTA text uses `never switches`, while R19's group is `("never switches", "never switch")` and the match is a raw substring (`classification.py:121-123`). `never switches` contains `never switch`, so removing QUOTA still leaves R19 `present` and the non-vacuity test in 27-09/Task 2 cannot pass. The same lines name `~/.claude` and similar homes, which `scan_text` flags whenever `home` is non-empty. -> Use `never switches CLI` (no bare `never switch`) and write the homes as words (`the Claude, Cursor, opencode, Codex, pi and GSD config dirs`).
3. [HIGH] 27-06/Task 1: `quota_lines` hard-codes `cross-ai.mjs` and `AIKIT-XAI`, but D-16 supports other runners and says to label them `usability unverified`. Those tokens are also exactly what makes R19 `present`. -> Keep both phrases, and add one line that names the detected runner and its label.
4. [HIGH] 27-13/Task 3: the verify greps for an `amended <date>, 27 execution` line in `27-SPEC.md` and fails the task when absent. Task 3 says to add a note only where a SUMMARY supports a changed fact, so a phase with no such contradiction cannot finish. The `**Plans**: TBD` check is already vacuous: `ROADMAP.md:1011` says `0/13 plans executed`. -> Require the version note that 27-RESEARCH already establishes (Claude Code 2.1.314, OpenGSD 1.17.0), and drop the TBD check.
5. [HIGH] 27-13/Task 2: `27-VALIDATION.md` has no `(planner)` marker, but the verify fails while any such marker remains. Replacing the seeded rows does not make that command pass. -> Assert every per-task status is `green` or `pending (owner)` and that `nyquist_compliant: true`.
6. [MEDIUM] 27-01/Task 1: `make_targets(text)` is tested for equality with `parse_makefile_targets_ordered(path)`, which reads a file and returns `[]` when missing (`makefile_parse.py:34-36`). A literal copy cannot satisfy that test. -> Compare `make_targets(text)` with the original regex applied to the same text, and keep a separate call that writes the Makefile and checks the original's file result.
7. [MEDIUM] 27-03/Task 2: the contract's `usage_source` allows `live`, but the task maps verified Claude rows to `official docs` and every other verified row to `live`. A current-host row is therefore never both `available` and `live`, contradicting D-07. -> Set `available` from the version/tool probe and `usage_source` independently: `official docs` only for the documented Claude primitives, `live` for the others whose matrix `source` is `verified`.
8. [MEDIUM] 27-04/Task 2: the dogfood test runs `detect_e2e` on this repo, whose `tests/test_wizard_pty.py` imports `pty`. D-18 says mapped PTY drivers are e2e and Textual-pilot tests are not, but gives no rule for an unmapped `import pty`. The test only requires `make e2e-test` and `make e2e-docker`, so the model can wrongly add `python3 -m unittest tests.test_wizard_pty` as e2e. -> State that an unmapped driver is e2e only when its first 80 lines contain none of `textual.pilot`, `pytest`, `unittest` or `from textual`.
9. [MEDIUM] 27-05/Task 2: the sweep asserts no reason contains `/` followed by `home`. The legitimate primitive `/loop` makes `/loop` match that shape, so the property fails for a good reason. -> Forbid the exact strings `FAKE_HOME`, `/home/` and `/var/home/`, not the two-character shape.
10. [MEDIUM] 27-06/Task 1: the rendered block starts with a four-backtick fence, but 27-13 extracts arguments with `awk '/^````/{n++; next} n==1'`. That starts after the opening fence and stops at the first rail line containing four backticks, so the upstream-grep check can pass while flags remain elsewhere. -> Pin the fence token in the contract as a line of exactly four backticks, forbid that token inside every block, and extract through the matching close.
11. [MEDIUM] 27-09/Task 1: `--work-set phases:16-27` is documented only as an inclusive numeric range. `phase_key("16-27")` raises `ValueError` (`phase_range.py:28-35`), so a model can reasonably reject the required form. -> Parse `phases:<from>-<to>` by splitting on the dash and applying `phase_key` to each side; document that a phase number itself never contains a dash.
12. [MEDIUM] 27-11/Task 1: the verify installs and then requires `git status --porcelain` to be empty. The install command is not part of the earlier README commit, so a correct scratch install that touches the repo fails the task. -> Split the checks: assert the README row and clean tree in one command, and the scratch install separately, followed by an explicit second clean-tree check.
13. [MEDIUM] 27-12/Task 3: `check_verdicts.py` imports `ai_kit_spec.runner_dispatch` (`check_verdicts.py:1-3`), while the plan says to copy it and only name the changes to `SKILLS`, `JUDGES` and `BASE`. The copied import keeps the skill-directory coupling D-03 forbids. -> Copy the status-line parser into the checker, or reimplement the two-judge comparison without that import.
14. [LOW] 27-06/Task 3 and 27-07/Task 2: `choose_path` receives `kind` `gsd`, while the contract's scope kinds are `opengsd` and `gsd-unproven`. Both GSD kinds must reach `.planning/goals/`. -> Name the two accepted scope values in `choose_path` and test both.
15. [LOW] 27-01/Task 2: `gsd_project` is specified as identical to `opengsd_project`, so the original-GSD fixture is only a different identity JSON and the second builder is unused. -> Delete `gsd_project` and have the original-GSD tests call `opengsd_project` plus `identity_json(False)`.

## Per-plan status
27-01: `make_targets` parity test calls a file reader with text; drop `gsd_project`.
27-02: ready
27-03: availability and usage source are not computed independently.
27-04: unmapped `import pty` can classify the repo's own Textual test as e2e.
27-05: property treats `/loop` as a forbidden home path.
27-06: user-requested second strategy violates D-27; QUOTA text fails both guard and R19 tests.
27-07: shared rails for an OpenGSD second block violate D-27.
27-08: ready
27-09: `phases:<from>-<to>` is not parseable by the specified `phase_key`.
27-10: ready
27-11: installer verify demands a clean tree after a command that can dirty it.
27-12: copied checker retains the cross-skill import.
27-13: SPEC amendment and validation verifies do not match their tasks or current files.

## Spec coverage gaps
none. R1–R8, the applicable edge rows, and all four prohibitions have a planned test or an explicit owner capture; the gaps above are contradictions in those planned tests, not missing coverage.


## Plan checker (gsd-plan-checker, fresh context, read-only)

Verdict ISSUES: 0 blockers, 8 warnings, 4 info. Held: `cross_ai: true` in all 13 plans; the run rules forbid touching the real home configs; GPS-01..GPS-04 all claimed; 2 or 3 tasks per plan (33 in total); waves match dependencies; every SPEC criterion and Prohibition maps to a test; 27-13 mirrors 26-12; 27-12 caps at three rounds.

Warnings (W) and info (I), condensed:
- W1 27-06 T1 and 27-07 T2: no source for `candidate_skills`, the wake primitive and label for `quota_lines`, and the OpenGSD OBJECTIVE builder; no test for the "none" candidate-skills form.
- W2 27-09 T1 vs T3: the dogfood `detect` on this repo (has `.planning/PROJECT.md`) with `free:dogfood` and no capture contradicts the exit-2 rule; say that `free:` and `plans:` work sets need no GSD captures.
- W3 27-09 T3 verify: `run_unittest_parallel.py --group e2e -- <module>` ignores the module list and runs the whole e2e tier; drop that run (membership is pinned by the grep and `test_gate_scope`).
- W4 27-10 T3 and 27-11: clean-tree checks conflict with a parallel sibling plan in wave 8; sequence 27-11 after 27-10.
- W5 27-12 T1: lane choice rests on an asserted "referee-one is down"; probe instead.
- W6 27-12 T1: the rubric read from the real Claude config dir; make the one read-only exception explicit.
- W7 27-12 T3: refuted findings are not checked for a `file:line`; make the checker fail on a `refuted by` line without one.
- W8 count thresholds below the sum of described tests: 27-02 T3 (22 vs 29), 27-04 T2 (20 vs 22), 27-05 T2 (24 vs 26), 27-08 T2 (14 vs 15).
- W9 (D-25) the character budget is not pinned by a test; D-28 supersedes the 1,500-character figure for the OpenGSD block and that should be recorded; pin a ceiling and the 1,800-character `/goal` soft budget.
- I10 27-06 T1/T3 ordering of `done_lines` versus the render tests; I11 pin D-27's "first rule" as index 0; I12 27-05 context should load the 27-02 and 27-04 summaries; I13 27-13 hardcodes `target_host` `claude` in the verify.


---

# Cycle 2

Cycle 2 of at most 3, over the 13 plans as replanned in dc82f3c. Reviewers: referee-two through pi (`AIKIT-XAI status=ok ... elapsed=132s ... tree=clean`, exit 0) and the plan checker, resumed with its cycle-1 context. The prompt listed the two deliberate cycle-1 dispositions (the QUOTA wording against `check_rules`, and the per-block rails rule), pointed at `git show dc82f3c` and each plan's `### Round 1` ledger, and asked for new concerns only plus a cycle-1 status table. `my-referee-one` and `my-referee-three` were not run (down / not answering). No native Opus. The lane did not edit the tree.

## Referee-two review, cycle 2 (verbatim)

## Verdict
REVISE

## Concerns
1. [HIGH] 27-06/Task 1 and 27-07/Task 1: the OpenGSD block is fenced with a line of exactly four backticks, but `.claude/gsd-core/workflows/autonomous.md:27-40` assigns `FROM_PHASE`, `TO_PHASE` and `ONLY_PHASE` from `grep -oE ... | awk '{print $2}'` over the whole `$ARGUMENTS`. `awk` prints the last match, and `--only` then overwrites `FROM_PHASE`. The closing fence line is ```` ``` ````, which is `--only` followed by whitespace and a backtick; a backtick is not a word character, so it matches `[0-9]*`. Pasting the recommended block therefore runs `--only` with an empty phase instead of `--from 16 --to 27`. The hand-written reference uses a three-backtick fence and never hits this. -> Fence the block with three backticks and forbid a three-backtick line inside it, or put the flags on the last line of the block. Extend the 27-13 upstream-grep check to compare the extracted phase values, not only the match count.
2. [MEDIUM] 27-01/Task 2 and 27-06/Task 2: the vulture checks pipe `uv run vulture` into `grep -c`, and the Makefile hook runs bare `vulture` with `min_confidence = 80` and no whitelist. `phase_spec`, `Phase`, `PromptTemplate.pattern` and `PromptTemplate.delimiter` are assigned but not called, so vulture names them and the commit hook fails. -> Call or drop the unused fixture helpers, and count the vulture lines without a pipe, the way 27-11 does.
3. [LOW] 27-03/Task 2: `OFFICIAL_DOCS_CLAUDE` includes `/loop`, `ScheduleWakeup` and `cloud routine`, but the live matrix marks those rows `unverified` and 27-RESEARCH gives `/loop` no official-docs cell. -> Keep `official docs` for `/goal` and the two `CronCreate` rows only; leave the unverified Claude rows `unverified`.

## Per-plan status
27-01: ready, except the vulture command can pass while the commit hook fails.
27-02: ready
27-03: `/loop`, `ScheduleWakeup` and `cloud routine` are labelled `official docs` against the matrix.
27-04: ready
27-05: ready
27-06: the four-backtick fence becomes an empty `--only` for `/gsd-autonomous`.
27-07: same fence, same empty `--only`, on every inline autonomous block.
27-08: ready
27-09: ready
27-10: ready
27-11: ready
27-12: ready
27-13: the upstream-grep check counts matches but does not catch the empty `--only`.

## Cycle-1 finding status
1: partly
2: not adopted (agree)
3: resolved
4: resolved
5: resolved
6: resolved
7: resolved
8: resolved
9: resolved
10: partly
11: resolved
12: resolved
13: resolved
14: resolved
15: resolved

## Spec coverage gaps
none.


## Plan checker, cycle 2

Verdict PASS (0 blockers, 0 warnings, 2 info). Items 1-9 of its cycle-1 list resolved (sources for `candidate_skills`, the wake line and runner; the `free:` work set; the dropped e2e-tier run; the re-sequenced waves 1-11 agreeing with ROADMAP and validation; the live probe order for judges; the rubric exception; the refuted-finding check; thresholds; the D-25 budget pinned with the D-28 supersession recorded); items 10-13 (INFO) not re-read. The deliberate dispositions were accepted. New info only:
- INFO 27-07 T1: stale wording (`autonomous_shared_block`, shared form) while the rule is now "always inline"; add a test that an autonomous block never contains `Rails: read <path>`.
- INFO 27-12 T1: step 1 should say "the sanctioned read in the guard line".


---

# Cycle 3 (last)

Cycle 3 of 3, over the plans as replanned in d955f02. Reviewers: referee-two through pi (`status=ok`, exit 0, tree clean) and the plan checker (PASS, no open item). `my-referee-one` and `my-referee-three` were not run. No native Opus.

## Referee-two review, cycle 3 (verbatim)

## Verdict
REVISE. Two verify commands fail on a correct implementation, and the copied Makefile helper is specified against the wrong original.

## Concerns
1. [HIGH] 27-13/Task 1: the live-check verify extracts the block with `awk '/^````/{n++; next} n==1'`, but `.claude/gsd-core/workflows/autonomous.md:27-40` matches `--only` with `grep -oE '--only\s+[0-9]+[A-Z]?(\.[0-9]+)*'`. A line of exactly four backticks is `--only` plus a backtick, and a backtick is not a word character, so the real parser sets `ONLY_PHASE` empty and overwrites `FROM_PHASE`. The command then requires that extraction to equal `27` (`test ... = 27`), so the phase gate fails on the fence the plans themselves mandate. -> Change the fence to three backticks and forbid a three-backtick line inside the block (27-06 Task 1, 27-07 Task 1, 27-PATTERNS.md Contracts), and make the 27-09 property and this verify compare the values the real regexes extract, fences included.
2. [HIGH] 27-01/Task 1: `make_targets(text)` is specified as a copy of `_TARGET_HEADER_RE` (`makefile_parse.py:16`), but its parity test asserts equality with `parse_makefile_targets_ordered(path)`. On the mandated Makefile (`.PHONY: a`, `VAR := x`, `e2e-test:`, a tab recipe, a repeated `e2e-test:`, `e2e-docker: build`, `test-unit:`) the regex returns `["a", "e2e-test", "e2e-docker", "test-unit"]` while the file reader returns `["e2e-test", "e2e-docker", "test-unit"]`, and the test also requires the latter list. No implementation satisfies both. -> Compare `make_targets(text)` with the original regex applied to the same text, and separately write the file and compare with `parse_makefile_targets_ordered(path)`.
3. [MEDIUM] 27-01/Task 2: `uv run vulture` with no arguments scans the working directory, not the configured `paths = ["tools", "skills", "tests"]` (`pyproject.toml:96-99`), so it reports the worktree's `.venv` and `.gsd-venv` and the commit hook (`uv run vulture`, `pass_filenames: false`) fails. The same bare command is in 27-06/Task 3. -> Run `uv run vulture skills/ai-kit-spec-goal-prompt tests/goal_prompt_fixtures.py tests/test_ai_kit_spec_goal_prompt_common.py` and require empty output.
4. [LOW] 27-11/Task 2: the plan says the new skill is the 26th and that `_PTY_ROWS = 160` was sized for 25, but `skills/*/SKILL.md` already numbers 24 and `tests/test_wizard_pty.py:36-44` says 160 fits 25 with headroom. -> Say the skill is the 25th and rerun the PTY suite, raising the rows only if it actually fails.

## Per-plan status
27-01: `make_targets` parity test contradicts the copied regex; bare `vulture` scans the worktree.
27-02: ready
27-03: ready
27-04: ready
27-05: ready
27-06: ready, except its bare `vulture` verify
27-07: ready
27-08: ready
27-09: ready
27-10: ready
27-11: "26th skill" miscounts the existing 24
27-12: ready
27-13: the upstream-grep verify cannot pass with the mandated four-backtick fence

## Cycle-2 finding status
1: open. The ledger records it as checked, but the real `--only` regex matches the four-backtick fence and the new simulation asserts the resulting empty value.
2: resolved
3: not adopted (agree)

## Spec coverage gaps
none.


## Dispositions of cycle 3

- HIGH 1 (four-backtick fence read as `--only`): not adopted. The fence lines contain no `--` token; running the upstream `grep -oE` lines from `autonomous.md` on a fenced block gives FROM 16, TO 27 and an empty ONLY (checked twice). The 27-09 sweep simulates the parser on the fenced block anyway.
- HIGH 2 (`make_targets` parity): not adopted. The regex's `(?!\.)` lookahead skips `.PHONY: a`, so the regex on the text returns `e2e-test, e2e-docker, test-unit`, the same list as the file reader (checked by running it).
- MEDIUM 3 (bare vulture scans `.venv`): not adopted. `uv run vulture` reads `[tool.vulture] paths` and exited 0 in this worktree.
- LOW 4 (skill count wording): adopted; 27-11 and 27-VALIDATION.md now say "one more skill".

## Plan checker, cycle 3

PASS: both INFO items resolved; no new blocker or warning from the d955f02 edits.

## Convergence

Three cycles ran. The plan checker passes. The reviewer's remaining objections were checked against the files and the live parser and are recorded above as not adopted; no unresolved concern remains that the code or the workflow does not refute.
