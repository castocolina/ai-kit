Judge: opus
Reviewed-sha256: 29ec2a75169bb7038d204870f064fb339adf0c02441032341c64806e07067892
Lane: native subagent completed
Score: 106
Critical: 0
Important: 0

# Skill Evaluation Report: ai-kit-gsd-curated-config

- **Total:** 106/120 (88%), grade B
- **Pattern:** Process (a phased v2 pipeline with checkpoints), with Tool-style tables
- **Knowledge ratio (E:A:R):** about 80:15:5
- **Verdict:** A dense, expert-heavy skill. It points at the `ai-kit-cross-ai` policy correctly and never lets a stop become a switch of harness, provider, model or runtime. What is left are small accuracy gaps and the body's length.

The Phase 25.1 changes are described correctly:
- **One runtime per call:** `SKILL.md:218-223`, `runner.md:53-57`.
- **Retry series and caller-owned hard tier:** `runner.md:42-49`.
- **Upstream lines passed through as data:** `SKILL.md:238-247` and `405-406`.
- **Script-owned model grammar:** `v1-path.md:33-35`, `runner.md:54-57`.
- **Never-switch rule:** `SKILL.md:378-380`. It matches policy sections 6-8.

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 17 | 20 | Almost all expert content: the gsd-core resolution order, trusted-root rules, `router_backed` provenance, the runner exit and status map. Some over-specified prose. |
| D2 Mindset + Procedures | 13 | 15 | Has a "before the first command, ask yourself" check (`SKILL.md:67-74`) and non-obvious ordering (scratch dir outside `.planning/`, dry run, end the turn, then apply). |
| D3 Anti-Patterns | 14 | 15 | The NEVER list (`SKILL.md:355-380`) and the Common mistakes table give a reason for each item, including the no-switch rule. |
| D4 Spec / Description | 14 | 15 | The description covers what, when and trigger keywords (`ensure-runner`, `cross-ai.mjs.new`) and states its boundary. It is long. |
| D5 Progressive Disclosure | 13 | 15 | Loading triggers are conditional, `runner.md:7` has a "Do NOT load", and there is a MANDATORY policy read at `SKILL.md:243-244`. But the body is 406 lines, and retry tuning has no direct route to the reference that defines the keys. |
| D6 Freedom Calibration | 14 | 15 | Low freedom for config writes, `--force`, apply markers and approvals. |
| D7 Pattern | 8 | 10 | A clear Process pattern, at about twice the usual length. |
| D8 Practical Usability | 13 | 15 | Exit maps, failure states and refusal-to-fix guidance. A few factual gaps, listed below. |

## Findings

No Critical or Important findings.

1. **Minor: the copilot path is understated.**
   - **Evidence:** `SKILL.md:126-128` says "copilot is not a curated runner ... and `ai-kit-spec-execute-gsd`'s hook is the path that can name it". But v1 `apply-execution` can also write a copilot hook. `references/v1-path.md:28-30` relays "a copilot target's note". In code, `cli.py:288-333` checks the model grammar through `runtime_id` and picks up `EXEC_NOTES["copilot"]`, and `ai_kit_spec/detection.py:118` registers copilot as a runner.
   - **Fix:** change it to "the v1 `apply-execution` hook and `ai-kit-spec-execute-gsd`'s hook are the paths that can name it (its exec rows are unverified; see `v1-path.md`)".

2. **Minor: the failure ladder hardcodes "one session reset" and leaves out where the hard-wait lengths live.**
   - **Evidence:** `runner.md:42-47` says "one session reset plus second soft series" and "The caller owns the hard waits". But `session_resets` is a configurable key (default 1), and `hard_waits_s` sits in the same `cross_ai_retry` block (`cross-ai.mjs:3036-3038`, `RETRY_KEYS`). An owner tuning the hard tier can't learn that from this file.
   - **Fix:** list the five keys (`base_s`, `factor`, `max_retries`, `session_resets`, `hard_waits_s`). Say that the runner emits `hard_waits_s[cycle]` as `retry_after_s=` and that the caller performs the wait.

3. **Minor: retry tuning points at the wrong policy file.**
   - **Evidence:** `runner.md:48-49` sends the reader to `../../ai-kit-cross-ai/SKILL.md` only "for caller actions". But the keys, the error catalog and the owner overlay (`cross-ai-errors.json`) are documented in `ai-kit-cross-ai/references/subprocess-quota-policy.md` (see `ai-kit-cross-ai/SKILL.md:19-21`). Neither the curated-config `SKILL.md` nor its references mention the catalog or the overlay.
   - **Fix:** add one line: "To tune `workflow.cross_ai_retry`, add an overlay row, or read `route=`/`rule=`, read `../../ai-kit-cross-ai/references/subprocess-quota-policy.md`."

4. **Minor: the rule "the runtime must not be the plan host" is undocumented.**
   - **Evidence:** `plan_io.py:1089-1090` refuses `config.runtime == plan_host`, and `_host_menu_problem` keeps the host out of the menu. `SKILL.md:124-130` and `219-222` say nothing about this. On a pi host, for example, `plan-set script:cross-ai.runtime pi` gets refused with no warning in advance.
   - **Fix:** add to `SKILL.md:126` "(never the host CLI; `plan-set` refuses it)".

5. **Minor: the body is long.**
   - **Evidence:** `SKILL.md` is 406 lines, above the roughly 300-line ideal. The Skills section (`SKILL.md:275-329`) on trusted-root and refusal mechanics is only needed when wiring hits a refusal.
   - **Fix:** move the "Refusals `--force` cannot bypass" and "Refusal → action" detail into a `references/skills-wiring.md`, loaded when a `skill_unwired` note, a trusted-root `needs_choice` or an `agent_skills` refusal appears. Keep the four wiring routes in the body.

I did not run the CLI or the runner's self-test. The claim that `config-set` refuses `workflow.cross_ai_retry` rests on the key being absent from gsd-core's schema manifest, not on a live call.

DIGEST 29ec2a75169bb703
CURRENT 106/120
CRITICAL 0 IMPORTANT 0
