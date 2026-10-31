Judge: opus
Reviewed-sha256: a0d23c0d4767515f02cdee66fc698a9a5a7f81ecc093893a8f36966bc4321852
Lane: native subagent completed
Score: 88
Critical: 0
Important: 4

# Skill Evaluation Report: ai-kit-project-rules-all

## Summary
- **Total score:** 88/120 (73%), grade C
- **Pattern:** Process. It resolves the entry script, runs it, reads the payload and then hands off. The JSON contract makes parts of it work like a Tool skill.
- **Knowledge ratio (Expert:Activation:Redundant):** about 60:25:15.
- **Verdict:** The skill describes the merge and failure-isolation contract well, and the description matches the code: `aggregate.py`, `dispatch.py` and `cli.py` behave as described. It falls short on what the agent should do with the merged report. One rule contradicts another, the restated Step C leaves out a rule, `blocked` entries have no next step, and broken-link findings are dropped without any mention.

Claims I checked against the repository and found accurate:
- **Report shape:** four keys, as `aggregate.py:53` builds it.
- **`hand_off` tagging:** set only on `remediate` entries with `kind == "workflow"` (`aggregate.py:49-51`).
- **Domain order and tie-break:** `DOMAIN_ORDER` and the stable sort match (`dispatch.py:129`, `aggregate.py:46-47`).
- **Timeout and dispatch:** 30-second budget, run one domain at a time (`dispatch.py:144`, `dispatch.py:250`).
- **Sibling resolution:** five candidate locations, checkout copy first, no `$PATH` search (`dispatch.py:154-184`).
- **Failure entries:** all four failure modes produce one (`dispatch.py:199-243`).
- **`check` equals `remediate`:** `cli.py`, where `remediate` simply calls `check`.
- **Usage text and exit codes:** match `cli.py` `main`.
- **`(kind, id, issue)` as the identity key:** `_shared/ai_kit_rules_common/remediation.py:75`.
- **Step A and Step B summaries:** match `ai-kit-project-rules-agents/SKILL.md:57-59`.

## Dimension Scores

- **D1 Knowledge Delta: 13/20.** The real expert content is the merge semantics, the fixed tie-break order, the rule that a failed domain never also appears in `remediate`/`blocked`, the meaning of `(kind, id, issue)`, and the caller trap in Limit 7. It is diluted in three ways:
  - Planning-internal IDs (SC2, SC3, D-04, D-05, D-06) mean nothing to an agent working in another repo.
  - Text about maintaining the document itself (SKILL.md:930-934 on the "floor of 8 limits", SKILL.md:968-970 on the deletion detector) is not knowledge for the agent.
  - Some points are restated three times: the single `hand_off` exception (SKILL.md:783-786, 962-966, 899-901) and "never re-implement the siblings' logic" (SKILL.md:780-787, 962, 981).
- **D2 Mindset + Procedures: 10/15.** The domain procedure is good: resolve the entry script, then fan out, then run the hand-off from Step A to Step C. The thinking framework for the agent's real job is thin. Nothing covers how to read and present a mixed report of `remediate`, `blocked`, `failed` and `notices`.
- **D3 Anti-Patterns: 11/15.** The NEVER items are specific and give reasons. Two of them (SKILL.md:978-983, about the `DOMAIN_ORDER` iteration and `build_remediation`) are rules for whoever maintains the code, not for the agent running the skill. The one NEVER an agent most needs is missing: "never report a clean result while `failed` or `notices` is non-empty". Limit 7 warns about this but gives no directive.
- **D4 Specification: 14/15.** The frontmatter is valid. The description covers WHAT and WHEN, includes the trigger phrases "check everything" and "run all the rules checkers", and routes single-domain questions elsewhere with examples. It is long and somewhat dense.
- **D5 Progressive Disclosure: 11/15.** At 221 lines it is self-contained. It depends on the sibling's "Wrap mechanism" section but never says to load it. It names the section, then restates it in part instead of saying "MANDATORY: read `ai-kit-project-rules-agents/SKILL.md` Wrap mechanism".
- **D6 Freedom Calibration: 12/15.** Entry-script resolution and the report-only boundary are correctly kept tight. The two contradictory `auto_apply` statements (finding 1) leave the most fragile decision undetermined.
- **D7 Pattern: 8/10.** Clear Process shape with minor drift into notes meant for developers.
- **D8 Practical Usability: 9/15.** Running the check is easy to act on. After it runs, there are gaps: no next step for `blocked`, an incomplete Step C, findings silently lost, and the contradiction above.

## Findings

1. **Important: SKILL.md:924-926 vs SKILL.md:974-975 contradict each other on `auto_apply`.**
   - Lines 925-926 say `auto_apply: true` on an entry outside the AGENTS.md (`workflow`) domain "means it is safe for the CALLER to apply automatically".
   - Line 974 says "NEVER auto-apply anything for a non-`workflow`-kind domain, whatever its `auto_apply` field says".
   - The agent running this skill is the caller, so one text both permits and forbids applying these findings.
   - **Fix:** pick one. Given the report-only design, rewrite 925-926 to say the field is passed through for the matching sibling or the user to act on, and that this skill's caller must not apply it inside this flow.

2. **Important: SKILL.md:905-917 claims to point at the sibling's sequence "BY NAME rather than restating it", then restates Step C incompletely.**
   - `ai-kit-project-rules-agents/SKILL.md:61` requires entries with `verbatim: true` (R18-R20) to be inserted exactly, as one block, never reworded.
   - `remediation.py:35` carries `verbatim` into these entries.
   - SKILL.md:915-917 leaves this out. Step B also leaves out the sibling's "declined near-misses are reported as skipped" rule.
   - An agent following this document would paraphrase the verbatim rules and break their signal phrases.
   - **Fix:** either delete the Step A-C bullets and add "MANDATORY: read the Wrap mechanism section of `ai-kit-project-rules-agents/SKILL.md` before acting on any `hand_off` entry", or restate it fully, including `verbatim`.

3. **Important: SKILL.md:846-847 (and Limit 2, SKILL.md:939-941) define `blocked` but give the agent no next step.**
   - In the shared builder (`remediation.py:120-131`), `blocked` entries are the findings marked `needs_research`.
   - The makefile sibling resolves them through a research step and `cache-update` (`ai-kit-project-rules-makefile/SKILL.md:154-192`).
   - Here the agent gets them with no route, so it either stalls or presents unresolved findings as final.
   - **Fix:** add one line: for each `blocked` entry, report it as needing research and route the user to that entry's `kind` sibling skill (makefile or precommit) for its research and `cache-update` flow. This skill never runs that flow itself.

4. **Important: SKILL.md:853-858 and the "check everything" promise hide a lost finding class.**
   - The agents sibling's `check` returns `links`, the broken relative links (`ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py:196`).
   - `dispatch.py:209` only ever calls `remediate`, and `build_remediation` reads only `workflow` plus `STRUCTURAL_KINDS` (`remediation.py:31`, `remediation.py:84-140`). Broken-link findings never reach this report.
   - The Limits section does not mention it, and the document implies nothing is lost. That breaks this repo's own rule against claiming more certainty than verified.
   - **Fix:** add a Limit: "AGENTS.md broken-link findings (`links`) from the agents sibling's `check` are not carried into this report; run that sibling's `check` directly for them." Alternatively, carry `links` through in code.

5. **Minor: SKILL.md:890-892 is garbled.** It says `... bogus <repo_root>` "prints usage ... and exits 0 for a missing/help argument, or unknown subcommand". Split it into two cases: no argument or `-h`/`--help` prints usage and exits 0; an unknown subcommand prints to stderr and exits 2.

6. **Minor: SKILL.md:930-934 and 968-970 are text about maintaining the document**, the "floor of 8" policy and the deletion-detector note. Delete both; the agent gains nothing from them.

7. **Minor: planning-internal IDs at SKILL.md:845, 848, 853, 899, 903, 936 and elsewhere** (SC2, SC3, D-04, D-05, D-06) are opaque outside this repo's `.planning`. Replace them with plain words or drop them.

8. **Minor: SKILL.md:978-983 are rules for the code's maintainer** (domain iteration order, re-implementing `build_remediation`), not for the agent running the skill. Replace them with agent-facing NEVERs, for example "NEVER summarize the run as clean while `failed` or `notices` is non-empty" (this turns Limit 7 into an instruction).

9. **Minor: SKILL.md:848-851 is slightly over-precise.** It describes every `failed` entry as `{"domain", "status", "error", "returncode"}`. But a sibling that prints valid JSON without a `remediate` key gets appended to `failed` as-is (`aggregate.py:39-44`), so the entry may lack those keys. Soften to "normally".

## Top 3 Improvements
1. Resolve the `auto_apply` contradiction (finding 1). Add a short "Act on the report" decision list: `failed`/`notices` are always surfaced, `blocked` goes to the matching sibling's research step, `hand_off` entries go to the agents sibling's Wrap mechanism (loaded as MANDATORY), and everything else is report-only.
2. Replace the partial Step A-C restatement with a mandatory load of the sibling section, or restate it in full including `verbatim` (finding 2).
3. Add the missing Limit about dropped broken-link findings (finding 4), and remove the maintenance notes and planning IDs to recover token budget (findings 6 and 7).

I did not run the skill's `check`, since a sibling might write a cache. So the claim that a run against this repo returns findings from several domains (SKILL.md:896-898) is not verified. The makefile sibling's research flow is confirmed in its SKILL.md; the precommit sibling's is not.
