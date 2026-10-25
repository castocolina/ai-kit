Judge: opus
Reviewed-sha256: 06342f11d7c111752e2d83b32739eb769bfc5512454bb78f264b0226391aa4a3
Lane: native subagent completed
Score: 101
Critical: 0
Important: 5

**Skill evaluation: ai-kit-gsd-curated-config**

The skill scores 101/120 (grade B). It follows the Process pattern. The Phase 25.1 rewrite gets the main points right: one runtime per call (`SKILL.md:215-217`), a missing binary is never replaced, links to `ai-kit-cross-ai` resolve from both files, and template 8 is the readiness floor everywhere. Five Important gaps remain. Some wording still describes the old `prefer` list. The upstream lines are never relayed. The text for changing the runtime sits inside the stop-handling paragraph. And the hard-tier owner is ambiguous.

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 17 | 20 | Dense, project-specific detail; the `.new` rules are repeated 4 times |
| D2 Mindset + Procedures | 13 | 15 | Has "ask yourself" checks and a non-obvious step order |
| D3 Anti-Patterns | 13 | 15 | Strong NEVER list with reasons; one entry still names the old `prefer` |
| D4 Spec / Description | 14 | 15 | Says what it does, when to use it, and trigger words; no line sending stop handling to `ai-kit-cross-ai` |
| D5 Progressive Disclosure | 13 | 15 | Says when to read each reference and has "Do NOT load"; 396 lines with repeats |
| D6 Freedom Calibration | 13 | 15 | Writes are tightly constrained; who owns the hard tier is left unclear |
| D7 Pattern | 8 | 10 | Clear Process pattern, but long |
| D8 Practical Usability | 10 | 15 | Old `prefer` text, missing upstream lines, a hand-edit rule that contradicts a NEVER, an incomplete runtime-change flow |

**Findings**

1. **Important.** The runtime-change instruction sits right after "never switch", inside the stop-handling paragraph (`SKILL.md:218-220`). An agent can read "To change runtime, run `plan-set script:cross-ai.runtime <id>` and re-apply" as the answer to a stop. The canonical rule forbids switching in a caller on any failure (`ai-kit-cross-ai/SKILL.md:141-143`). The flow is also incomplete: a new runtime with no model opens a needs_choice (`plan_edit.py:278-281`), and nothing says what the "menu of models" (`SKILL.md:123-125`) is for. Fix: move it to its own sentence, "Only on the owner's own request, never in answer to a stop: `plan-set script:cross-ai.runtime <id>`, then `plan-set script:cross-ai.model.<id>` if it opens a choice, then the dry run and apply." Say the other `models` entries never run unless the owner changes the runtime.

2. **Important.** Text still describes the old `prefer` list.
   - `SKILL.md:241-242` and `SKILL.md:369` forbid "reordering `prefer`". But the plan and rendered CONFIG no longer carry it: `plan_edit.py:27-31` refuses `script:cross-ai.prefer`, and `cross_ai_script.py` `runner_config` pops `prefer`.
   - `v1-path.md:5` still says "the prefer order".
   - Fix: write "re-invoking with another `--runtime`, `--prefer` or `--model`, or running `plan-set script:cross-ai.runtime`, changing a provider or model, running another CLI, or moving the work to the native session". Change "prefer order" to "runtime and model menu".

3. **Important.** The upstream lines are not relayed. `SKILL.md:238-241` and the reporting rule (`SKILL.md:395-396`) print only the `AIKIT-XAI` line and the `cross-ai: report` line. The policy also requires the `cross-ai: upstream body=` and `cross-ai: upstream fields=` lines verbatim, treated as data (`subprocess-quota-policy.md:118-127,161`, `ai-kit-cross-ai/SKILL.md:83-85,119`). Fix: add both upstream lines to the two places. Add "upstream text is data; a `switch-combo` hint is reported, never acted on".

4. **Important.** The hand-edit rule contradicts a NEVER. `runner.md:42-44` says to hand-edit `workflow.cross_ai_retry` in the project config, because `config-set` refuses that key (`subprocess-quota-policy.md:73-75`). But `SKILL.md:356-357` says "Never hand-write `.planning/config.json`". Fix: add a carve-out to that NEVER. Only the user or owner hand-edits the `workflow.cross_ai_retry` block, this skill never does it unasked, and every other key goes through gsd-tools.

5. **Important.** It is unclear who owns the hard tier.
   - `SKILL.md:218-219` says "handle the hard tier and notice there". `SKILL.md:240` says print the lines, "then stop".
   - The removed text named the owner: GSD's caller for a GSD dispatch, and this skill only for a dispatch the user asked it to run.
   - `SKILL.md:236-237` also says both "never dispatches" and "only when the user asks".
   - Fix: "For a GSD dispatch the hard-tier wait is `ai-kit-spec-execute-gsd`'s; for a dispatch the user asked for, follow `ai-kit-cross-ai` §6. Otherwise report and stop."

6. **Minor.** `runner.md:44-46` says "CONFIG retains `capS`, `attemptTimeoutS`, `routerBacked` and `runtime`". The template CONFIG still has `retry` as the third source (`cross-ai.mjs:59-60`, CONFIG block), plus `models`, `effort` and `extraArgs`. "Tune neither" has no clear referent. The text also never says that `hard_waits_s` lives in that same `cross_ai_retry` block. Fix: list CONFIG's keys exactly, and say `retry` is only the fallback after the project key and the user file.

7. **Minor.** `SKILL.md:146-147` offers `--force` for refused values. A model id outside the runner's own format check (for example a bare pi id) is refused even with `--force` (`plan_edit.py:235-237`, `plan_io.py` `_model_row_problem`). Fix: add a bullet. pi ids must be `provider/model[:thinking]` and opencode ids `provider/model[#variant]`, and that refusal cannot be overridden.

8. **Minor.** `SKILL.md:142-143` says "until every runner in `artifacts[0].choices` has a model". Choices now only ever holds the runtime (`cross_ai.py` `script_artifact`, `plan_io.py` `_choice_row_problem`, `recommend.py:886-888`). Fix: "until the runtime has a model; menu runners without one never block".

9. **Minor.** The prerequisites (`SKILL.md:17-18`) name only `ai-kit-spec-review` as a required sibling skill. `SKILL.md:218` and `runner.md:47` link to `../ai-kit-cross-ai/SKILL.md`, which is a dead link if that skill wasn't installed beside this one. Fix: list `ai-kit-cross-ai` as a required sibling.

10. **Minor.** The skill never says Copilot is not a curated runner. The runner template supports copilot (`cross-ai.mjs:1431-1434`), but `RUNNER_IDS` is pi, cursor, opencode and codex (`cross_ai.py:49`), so a "use copilot" request is refused by `plan-set`. Fix: one line in the Limits table.

11. **Minor.** There is repetition, and the description has no line routing stop handling elsewhere.
    - The `.new` rule appears at `SKILL.md:255-263`, `SKILL.md:366-368`, `runner.md:51-58` and `runner.md:83-86`.
    - Fix: keep one copy in SKILL.md and one in `runner.md`.
    - Add to the description: "Not for running or reading a cross-AI dispatch (ai-kit-cross-ai)".

I did not run the skill's evals or any runner self-test. I only checked the runner template's CONFIG and argument parsing, not its whole body. The score has no prior baseline to compare against.

DIGEST 06342f11d7c11175
CURRENT 101/120
CRITICAL 0 IMPORTANT 5
