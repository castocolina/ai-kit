---
phase: 19-evaluation-on-claude
plan: 09
executor: orchestrator (live Claude Code session; pi judges through the shipped runner in review mode; headless claude -p cells)
requirements-completed: [EVAL-02]
product_commit: deb85b3
key-files:
  modified:
    - skills/ai-kit-gsd-curated-config/SKILL.md, references/v1-path.md (f88594a fix round 1; 86ad793 fix round 2)
    - tests/test_curated_config_apply.py (three 19-09 pins)
    - tests/gsd_curated_eval.py, tests/test_gsd_curated_eval.py (6b35dfe, e7937f9, 7bbd664 ask detection; c326bbd import isolation)
    - .planning/phases/19-evaluation-on-claude/19-SKILL-JUDGE.md, 19-PRESSURE-TESTS.md
    - .planning/phases/19-evaluation-on-claude/skill-judge/*-r1.md, *-r2.md
    - .planning/phases/19-evaluation-on-claude/pressure/*-green-j1.*, *-green-j2.*, *-green-opus.*, D-green-resample.*
orchestrator_verify: ""
---

# Plan 19-09 Summary: skill-judge fix loop (2 rounds) and opus confirmation on digest 9cddf0a5892fba97

base: 1def2b75681997b7dbd6fc3af47cdc429b0b4532

Verdict: `PASS`, with `FIX_ITERATIONS_USED: 2 of 3`. On the final digest `9cddf0a5892fba97`:
- The in-session judge scores 109/120, 0/0.
- pi gpt-6.1-sol scores 114/120, 0/0.
- pi glm-5.3 is `unavailable, capacity` in every round, which matches its weekly limit until 2026-10-21.
- GREEN (sonnet) B-E passes every gating check (B `ensure_runner_disclosed` is non-gating).
- No `harness-failed` cell occurred.

## Rounds

- Round 1, f88594a, digest `235e930d29d7d34c`. Finding: gpt-6.1-sol round-0 F1 (Important), the unscoped NEVER never-skip rule against the v1 path, which has no review or dry run. Change: the NEVER rule is scoped to v2, and v1-path.md gets a rule to ask before each write.
  - GREEN j1 passes all gating checks.
  - Judges: in-session 109/120 0/0; gpt-6.1-sol 113/120 0/1; glm-5.3 unavailable. The stop rule is unmet.
- Round 2, 86ad793, digest `9cddf0a5892fba97`. Finding: gpt-6.1-sol r1 finding 1 (Important), that v1 asks for approval without a way to preview the effects. Change: the v1 rule asks for the command and its passed values, names the `apply-*` commands that write keys their flags do not show (checked against `cli.py`), and routes a full preview to the v2 dry run.
  - GREEN j2 passes all gating checks.
  - Judges: in-session 109/120 0/0; gpt-6.1-sol 114/120 0/0; glm-5.3 unavailable. The stop rule is met.
- Rejected findings: none. Minor findings stay recorded in the reports.

## Grader fixes made during the loop (tests only, no product change)

- 6b35dfe: B and E green-j1 asked without a "?" ("Reply yes to run the follow-up", "Reply with an answer for choices 1 and 2"). The ask detector now accepts sentences that open with a request verb, and `_grouped_question` uses it.
- e7937f9: E green-j2 asked "Please answer these two." The detector now accepts `please <verb>`.
- 7bbd664: C green-opus listed "Choices for you" with the candidate values for each key. `_offers_choice` counts a key plus two or more of its values as putting the choice to the user.
- c326bbd: run after `tests.test_ai_kit_gsd_curated_config` in one process, three v1-hook grader tests failed. That suite's blocked re-import leaves a degraded `cross_ai_build`/`preference_match` bound on the package. The harness now imports through `sys.modules` (`product_module`). The v1 test module was left untouched (Run rule 8).
- Every red/green test proves the old detector missed the transcript phrase.
- After each fix, the faithful set was re-graded: RED cells rebuilt from state, plus j1/j2/opus from kept run dirs. The old grader on the rebuilt RED dirs reproduced the committed records exactly.
- Every RED cell still fails at least one gating check.
- The superseded GREEN rounds green/r1/r2 keep their records from `05a0c6e`, because a rebuild from state is not faithful for them.

## Opus confirmation (`--model opus --effort high`, digest `9cddf0a5892fba97`)

- B: `ensure_runner_disclosed` fails (non-gating), the same as sonnet. C and E pass every check.
- D: opus never ran the real apply. After the turn-2 answer it named the 25 removals by full key, then refused to read the bare "yes" as answering the open trusted-roots `needs_choice`, so no scripted answer was left. Five gating checks have nothing to grade (`no real apply`).
- D re-sample (sonnet, `pressure/D-green-resample.md`) passes every check. All three D results are recorded, and the sonnet column keeps its gating role.
- Costs: j1 $1.47, j2 $1.66, opus $3.90, re-sample $0.56.

## Human needed

- none blocking the verdict.

## Owner review (non-blocking)

- Eval D's scripted answers never answer the trusted-roots `needs_choice` explicitly. Sonnet reads "Yes, go ahead with the diff you showed" as approving the proposed list; opus does not. Decide whether `evals/03-v1-written-config.md` should answer the choice explicitly.
- glm-5.3 never produced a score (capacity in all three rounds). The PASS rests on the in-session judge and gpt-6.1-sol.
- `tests/test_ai_kit_gsd_curated_config.py` `_reimport_with_ai_kit_spec_blocked` should also restore the package attribute. The harness now works around it.

## Judge attempts
- ai-kit-gsd-curated-config-pi-glm-5.3-xhigh-r1 1: AIKIT-XAI status=capacity cli=pi model=zai-coding-cn/glm-5.3:xhigh exit=75 cli_rc=1 elapsed=146s out=0 tree=clean action=retry-later -> retry
- ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh-r1 1: AIKIT-XAI status=ok cli=pi model=openai/gpt-6.1-sol:xhigh exit=0 cli_rc=0 elapsed=153s out=6102 tree=clean action=stop -> kept
- ai-kit-gsd-curated-config-pi-glm-5.3-xhigh-r1 2: AIKIT-XAI status=capacity cli=pi model=zai-coding-cn/glm-5.3:xhigh exit=75 cli_rc=1 elapsed=146s out=0 tree=clean action=retry-later -> unavailable
- ai-kit-gsd-curated-config-pi-glm-5.3-xhigh-r2 1: AIKIT-XAI status=capacity cli=pi model=zai-coding-cn/glm-5.3:xhigh exit=75 cli_rc=1 elapsed=146s out=0 tree=clean action=retry-later -> retry
- ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh-r2 1: AIKIT-XAI status=ok cli=pi model=openai/gpt-6.1-sol:xhigh exit=0 cli_rc=0 elapsed=157s out=5509 tree=clean action=stop -> kept
- ai-kit-gsd-curated-config-pi-glm-5.3-xhigh-r2 2: AIKIT-XAI status=capacity cli=pi model=zai-coding-cn/glm-5.3:xhigh exit=75 cli_rc=1 elapsed=147s out=0 tree=clean action=retry-later -> unavailable

## Invalid attempts

- none

## Timeline
- round r1:
  - 18:13:28 round r1 start
  - 18:13:30 start ai-kit-gsd-curated-config-pi-glm-5.3-xhigh attempt 1
  - 18:13:30 start ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh attempt 1
  - 18:14:01 in-session r1 report written
  - 18:15:56 exit ai-kit-gsd-curated-config-pi-glm-5.3-xhigh attempt 1
  - 18:16:03 exit ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh attempt 1
  - 18:16:56 start ai-kit-gsd-curated-config-pi-glm-5.3-xhigh attempt 2
  - 18:19:22 exit ai-kit-gsd-curated-config-pi-glm-5.3-xhigh attempt 2
  - 18:21:59 r1 scan clean; batch move of r1 reports and j1 transcripts
- round r2:
  - 18:23:11 round r2 start
  - 18:23:13 start ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh attempt 1
  - 18:23:13 start ai-kit-gsd-curated-config-pi-glm-5.3-xhigh attempt 1
  - 18:23:33 in-session r2 report written
  - 18:25:39 exit ai-kit-gsd-curated-config-pi-glm-5.3-xhigh attempt 1
  - 18:25:50 exit ai-kit-gsd-curated-config-pi-gpt-6.1-sol-xhigh attempt 1
  - 18:26:39 start ai-kit-gsd-curated-config-pi-glm-5.3-xhigh attempt 2
  - 18:29:06 exit ai-kit-gsd-curated-config-pi-glm-5.3-xhigh attempt 2
  - 18:29:13 all r2 judges exited
  - 18:30:01 r2 scan clean; batch move of r2 reports and j2 transcripts
- In each round, the GREEN cells wrote only under gitignored `tmp/pressure/out-*` while the judges ran. The r1 evidence was committed (7d493ef) before the r2 judges started, so both rounds began on a clean tree. No tracked write happened between a judge start and its batch move.

## Redactions
- `skill-judge/in-session-r1.md` line 12: the orchestrator's own hyphenated phrase for "ask before each write" matched SECRET_RX (its `sk-` substring), a false positive. It was reworded to "rule to ask before each write" before staging. The file had already been moved when the scan flagged it; no judge was alive.
- The runner's `bin=<home>/...` lines in the `.err` files were replaced by `<home>`; the `.err` files are not tracked.

## Host-managed changes

- `snapshot --check` printed `snapshot ok` for every j1, j2 and opus batch, except Bopus, Dopus and the D re-sample, which reported `changed (host-managed) <home>/.claude/plugins/known_marketplaces.json`.
- `plan09.before.json` reports the same host-managed file. The strict set is unchanged.

## Leak check

- The diff against `tmp/pids-19-09.before` printed two `gsd-tools.cjs run-with-timeout 3600 -- pi -p --model router-env/my-coding` processes. Their cwd is the `tools-installer` checkout, and their parent is another session's run script, so they are not this plan's and were not touched.
- No runner, `claude -p` or `gsd_curated_eval` process from this plan was left.
