# ai-kit-gsd-curated-config — skill-judge report (native Opus subagent, clean context)

Round 6, skill digest `c3f432f44f2da7b7`, judged at commit 12083a7. Rubric: the skill-judge skill (120 points).

**Evaluation: ai-kit-gsd-curated-config, scored as a whole with focus on the Phase 25 changes**

The Phase 25 claims I checked hold against the code. That covers the one-CLI-per-call rule, the runner's exit table, `router_backed` derivation and recompute, the cap and early re-entry, `tree=unknown` on git errors, the readiness floor of 7, and the newer-template guard in `plan_runner_upgrade`. The checks were against `cross-ai.mjs` (STATUS_TABLE:798-819, routeOf:1621-1633, cycle preflight:2432-2455, the "only X runs" log:6150), `cross_ai.py:79-89` and `plan_edit.py:209-250` / `cross_ai_script.py:32,243-272`.

Nothing in the skill tells the agent to switch harness, provider or model by itself. The policy is linked correctly from both files, with a MANDATORY trigger on any non-ok `AIKIT-XAI` status. Pattern is Process/Tool. SKILL.md is 405 lines.

| Dimension | Score | Max | Note |
|---|---|---|---|
| D1 Knowledge Delta | 17 | 20 | Nearly all of it is project-specific: exits, refusals, how `router_backed` authorizes cycles. Some internals (function names, `--force`-immune check details) the CLI already enforces. |
| D2 Mindset + Procedures | 13 | 15 | Strong ordered procedure with a trust and v1-history pre-check; few "ask yourself" framings beyond that. |
| D3 Anti-patterns | 13 | 15 | NEVER list and mistakes table, mostly with reasons; the runner-stop NEVER is clear. |
| D4 Spec / Description | 14 | 15 | Valid frontmatter; WHAT, WHEN and keywords are present. |
| D5 Progressive Disclosure | 12 | 15 | Good triggers and a "Do NOT load", but a non-ok dispatch loads both runner.md and the policy, which overlap; the body is over the 300-line ideal. |
| D6 Freedom Calibration | 14 | 15 | Low freedom on config writes, exact commands, `--force` gated. |
| D7 Pattern | 8 | 10 | Clear Process flow; the Cross-AI execution section is one dense block. |
| D8 Usability | 12 | 15 | Thorough exit and refusal handling; gaps below (wrong field name, unclear owner of the re-entry, no eval for a runner stop). |

**Findings**

1. **Important:** `script.active: false` is attributed to `ensure-runner`, but that command never emits it.
   - Evidence: SKILL.md:354 (subcommand table) and references/runner.md:57-58. `ensure_runner` returns only `{ready, runner, guidance, notes[, error]}` (cross_ai_script.py:340-345). `active` exists only in the v2 `apply` report (apply.py:519-526).
   - Fix: for `ensure-runner`, say "`runner: "new-as-.new"` and `ready: false`". Keep `script.active` for v2 `apply` only.

2. **Important:** The skill doesn't say who performs the "one sanctioned re-entry".
   - Evidence: SKILL.md:224-225 sanctions the one-shot after exit 75 with `retry_after_s=`. SKILL.md:244-245 says this skill never dispatches a model call, and live dispatches happen only on user request. Policy:89-96 asks for a `CronCreate`. An agent can't tell whether it should schedule the wake.
   - Fix: add one sentence. When the dispatch came from GSD, the re-entry belongs to that caller. This skill only reports the `AIKIT-XAI` and report lines plus `retry_after_s`. It schedules the one-shot only for a dispatch the user explicitly asked it to run, same lane, never another runner.

3. **Important:** The mitigation for an active runner below template 7 reads as an action the agent takes.
   - Evidence: SKILL.md:265-267 says "tell the user, and merge `.new` (runner.md) or set `workflow.cross_ai_execution false` before any dispatch". It doesn't say who decides, and gives no route for the config change. That brushes against "never move the work to the native session" and "never hand-write config".
   - Fix: "tell the user. The owner chooses: merge `.new`, or `plan-set workflow.cross_ai_execution false` then dry-run and apply. Do neither unasked."

4. **Minor:** runner.md copies the ladder knobs the policy says must not be copied.
   - Evidence: references/runner.md:43-51 restates `sameSessionRetries`/`newSessionRetries`/`cooldownS`/`capS`/`attemptTimeoutS` clamps and the router-inferred rule. Policy:5 says "A skill links here; it does not copy the rules." Both files load on a non-ok dispatch, so the content is duplicated and can drift.
   - Fix: cut that section to the pointer plus the facts specific to this skill: `router_backed` maps to CONFIG `routerBacked` for the pinned model, and upgrades keep an unused `retries` key.

5. **Minor:** The policy asks callers on other hosts to "print … the state path", but no path is given.
   - Evidence: policy:95 asks for it. The runner logs the path only when the state file is unwritable (cross-ai.mjs:2488), and the policy says only "XDG state dir" (policy:43).
   - Fix: document `$XDG_STATE_HOME(or ~/.local/state)/ai-kit/spec/cycles/<sha16(realpath cwd)>/<cli>-<sha16(model)>.json` (cross-ai.mjs:1866-1871), or have the runner log the path on an exit 75 with `retry_after_s`.

6. **Minor:** SKILL.md:106-112 tells the agent to review "the plan's `router_backed` value per runner" without saying where it is.
   - Fix: name `artifacts[0].config.router_backed`.

7. **Minor:** No eval tests the main Phase 25 rule under pressure.
   - Evidence: evals/01-04 contain no scenario like "runner exited 75 / not_installed, just switch to opencode".
   - Fix: add an evals/05 that gates on the verbatim `AIKIT-XAI` and report lines, no reordered `prefer`, no other CLI, and no native takeover.

8. **Minor:** The Cross-AI execution block packs about seven rules into one paragraph (SKILL.md:216-229): template, ladder link, MANDATORY trigger, re-entry, owner menu, CONFIG edit ban, hook naming.
   - Fix: split it into bullets. Consider moving the runner exit list (SKILL.md:38-42) to runner.md to get the body toward 300 lines.

9. **Minor (code, not docs):** v2 `apply` has no guard against downgrading a newer runner.
   - Evidence: `plan_script` (cross_ai_script.py:208-211, then `_plan_rendered`:191-205) would rewrite a pristine runner stamped by a newer ai-kit. `plan_runner_upgrade`:257-259, used by `ensure-runner`, refuses to.
   - Fix: apply the same `newer` check in `plan_script`.

I didn't run the runner's `--self-test` or any CLI command, and I didn't recheck the non-Phase-25 Skills-section internals beyond a spot check. The main thing to know: finding 2 leaves it open whether an agent schedules a wake itself.

DIGEST c3f432f44f2da7b7
CURRENT 103/120
CRITICAL 0 IMPORTANT 3
