# ai-kit-spec-review — skill-judge report (native Opus subagent, clean context)

Round 5 (evidence round), skill digest `458a2dd3c1b61497`, judged at commit e2bb140. Rubric: the skill-judge skill (120 points).

The skill scores **100/120 (grade B)**. The Phase 25 runner policy is described and linked correctly, and nothing in the skill tells the agent to switch harness, provider or model after a failure. The deductions come from two gaps: the resume procedure when both review lanes are pending, and a fallback to the native session that happens without being stated.

**Verified against the code:**
- The settings in `cross-ai.mjs` match the policy file: 3 same-session retries, 3 new-session retries, a 600 s cooldown, a 4-hour cap (14400 s), and the stated limits (`cross-ai.mjs:64-83, 1755-1777`).
- Exit codes match: a quota or transient stop exits 75, the cap and auth stops exit 69, a missing CLI exits 127 (`cross-ai.mjs:790-810`).
- The status line carries `retry_after_s=` and `cycle=` only on a router cooldown that is still under the cap (`cross-ai.mjs:907-911, 2459-2468`).
- The runner runs only the first CLI named and says there is no automatic fallback (`cross-ai.mjs:6078-6101`).
- The 11 `unverified` pattern ids listed in the policy match the pattern table exactly.
- The route is confirmed through `fallback_quota` in the model catalog and passed as `--route-<cli> router` (`runner_dispatch.py:179-229, 575-576`).
- Exit code 75 passes through `dispatch-reviewer --stdout-only` unchanged (`cli.py:976-978`).
- The no-status-line fallback table matches `_EXIT_FALLBACK` (`error_classifier.py:59-61`).

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 17 | 20 | Almost all project-specific: dispatch contract, exit-75 branching, a fail-closed missing report. Some rationale is verbose. |
| D2 Mindset + Procedures | 13 | 15 | "Ask yourself" prompts at Steps 0.5, 0.7, 3 and 5, plus procedures an agent would not know. |
| D3 Anti-patterns | 12 | 15 | The NEVER list has only 2 items; the hard-rules table gives reasons, including the new "never re-dispatch a failed lane" rule. |
| D4 Spec / Description | 14 | 15 | Says what it does, when to use it, and gives trigger phrases; valid frontmatter. |
| D5 Progressive Disclosure | 12 | 15 | Required reads sit inside the workflow, with "Do NOT load" for `cross-ai.mjs` and `cli-profiles/`. But SKILL.md is 487 lines, close to the 500 limit, and the Step 1 subprocess branch is dense. |
| D6 Freedom Calibration | 13 | 15 | Fragile dispatch steps get fixed commands, which is right. The resume procedure is fixed but ambiguous (finding 1). |
| D7 Pattern | 8 | 10 | A clear Process skill, but about 2.4 times the usual ~200 lines. |
| D8 Usability | 11 | 15 | Edge cases are covered well, but there is a resume race, an unstated native fallback, and some stale companion docs. |

**Findings**

1. **Important. When both lanes are pending, they share one `resume.json`.**
   - Evidence: `references/cross-ai-dispatch.md:277-288, 301-314`. Each pending lane writes the same `$RUN_TMP_DIR/resume.json` with its own `key`, `index` and `sibling_key`, so the second write overwrites the first. Lane A's wake then reads `key=B, sibling_key=A` and treats itself as the sibling.
   - There is also a race. The re-run command truncates `.err` at start but writes `.exit` only at the end, so "the sibling is still pending" cannot be decided while the sibling is mid-run. Two wakes due at the same minute can both merge and run the fixer twice, or both stop and neither merges. Either way the rule "last lane to resolve merges" and "no fixer while pending" breaks.
   - Fix: write one resume file per lane (`resume-<key>.json`), chosen by the key in the resume pointer, and take the sibling from `reviewers.json`. Before each re-run, mark the lane as running (for example, write `running` to its `.exit` file). Let only the lane that wins a lock merge, e.g. via `mkdir "$RUN_TMP_DIR/iter<N>-merge.lock"`.

2. **Important. The ladder walk can land on the native session, and the skill never says so.**
   - Evidence: `SKILL.md:157-162` says a failed probe moves the review to "the next configured entry". But `quota.py:145-191` returns `NO_CONFIG_FALLBACK` (the session default, same vendor as the author) when no entry in the ladder has quota.
   - `SKILL.md:208-210` ("the session default still runs" without Node) is true only through that path. A missing Node at dispatch time actually returns code 1 with reason `dispatch_unavailable`, which ends as a Failure (`runner_dispatch.py:532-566`, `cli.py:976-978`).
   - This clashes with the owner rule at `SKILL.md:336-338` ("never moves the work to the native session on its own"), and the Step 5 message only adds `unavailable:` lines.
   - Fix: state in Step 0.7 that running out the ladder falls back to the session default as part of the authorized pre-dispatch walk, or stop and ask the owner. Add a Step 5 line: "every configured reviewer unavailable; reviewed with the session default (vendor = author)". Correct the Runner bullet in Constants: without Node, probes fail before dispatch; during dispatch it is a Failure, never a session-default run.

3. **Minor. The loop diagram is stale.** `references/loop-diagram.md:30-37` has no resume entry and no pending-lane branch (Step 2's first row, `SKILL.md:390`). Fix: add a "lane pending" exit to the router-quota Surface node and a "Resume entry" node that goes into Step 1.

4. **Minor. The router-quota Surface row assumes a sibling exists.** `SKILL.md:447` always says "Its sibling lane is merged now as single mode", but `SKILL.md:390` allows a single-reviewer pending lane. Fix: add a variant for the no-sibling case.

5. **Minor. The probe-unavailable list is lost across a resume.** The Step 5 `unavailable:` lines (`SKILL.md:164-165, 453-454`) come from Step 0.7, which the resume entry skips (`SKILL.md:226-229`), and `resume.json` (`cross-ai-dispatch.md:277-284`) has no field for them. Fix: add an `unavailable` key to `resume.json`.

6. **Minor. Two files disagree on what a host without `CronCreate` prints.** The policy (`subprocess-quota-policy.md:92-93`) says `retry_after_s`, the state path and the re-invoke command. The dispatch reference (`cross-ai-dispatch.md:290-294`) says `retry_after_s`, the resume pointer and the `-argv.json` path. Fix: the policy file is the source of truth, so align the dispatch reference to it, or name both sets.

7. **Minor. The owner rule is restated right after "do not restate".** `SKILL.md:335-338` says "link it, do not restate it" and then restates the owner rule in one line. The duplication is acceptable, but drop the "do not restate" phrase or label the line as a summary.

I did not run `--self-test` or the Python tests (read-only), and did not score the `evals/` files. Outside the skill's text: a router-lane probe runs in a random temp directory, so a quota stop during a probe leaves a stray state file in the XDG state dir that is never cleaned up. That is a code issue, not a skill-doc defect.

DIGEST 458a2dd3c1b61497
CURRENT 100/120
CRITICAL 0 IMPORTANT 2
