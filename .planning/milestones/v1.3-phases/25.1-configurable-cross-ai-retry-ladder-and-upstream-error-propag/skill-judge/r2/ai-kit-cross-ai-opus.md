Judge: opus
Reviewed-sha256: fc34de9e11130d7844424142c0b8fa1e5801368f34b94b8889f7006d2c52e94e
Lane: native subagent completed
Score: 97
Critical: 0
Important: 4

# Skill Evaluation Report: ai-kit-cross-ai

## Summary
- **Total score**: 97/120 (81%), grade B
- **Pattern**: Process/Tool hybrid (168-line SKILL.md, two references, a runner template plus a data catalog)
- **Knowledge ratio (E:A:R)**: about 75:15:10
- **Verdict**: Almost all of the content is knowledge Claude would not otherwise have about how this runner behaves: exit-code semantics, the hard tier, the stopped-lane refusal, and upstream lines treated as data. I checked these claims against `cross-ai.mjs` (STATUS_TABLE at :1159, `resolveDeadline` at :2903, `ladderNext`/`hardWaitFor` at :3046/:3069, the refusal text at :3820). I also checked them against gsd-core's config schema, where `cross_ai_retry` is absent, so `Unknown config key` is correct. The "never switch harness, provider or model" policy is stated correctly and the skill does not contradict it anywhere. A few portability and edge-case gaps keep it out of the A range.

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 16 | 20 | Runner-specific facts throughout. Pitfalls repeat sections 2-3 almost verbatim, and the scratch-dir advice appears 3 times |
| D2: Mindset + Procedures | 12 | 15 | Strong framing (the owner owns the choice, upstream lines are data). The procedures are domain-specific |
| D3: Anti-Pattern Quality | 13 | 15 | NEVER skip (with the harness-switch reason), never switch, no trailing `&`, kill by PID. Some items lack a why (stash, kill by pattern) |
| D4: Specification Compliance | 13 | 15 | Valid frontmatter, clear WHAT/WHEN, routes away to sibling skills. Missing literal trigger keywords (`cross-ai.mjs`, `AIKIT-XAI`, `exit 75`, `retry_after_s`, quota/rate limit, runtime names) |
| D5: Progressive Disclosure | 11 | 15 | Has a MANDATORY trigger for launch-and-wait.md. subprocess-quota-policy.md has no trigger inside the workflow and there is no "Do NOT load" guidance |
| D6: Freedom Calibration | 13 | 15 | Low freedom where it matters. Two copy-paste examples are less safe than the prose around them |
| D7: Pattern Recognition | 8 | 10 | Clear numbered process plus an exit table. The Pitfalls section duplicates the body |
| D8: Practical Usability | 11 | 15 | The exit table is excellent. Gaps: the template path outside this repo, how to answer GSD on non-hard-tier stops, re-invoke identity, copilot's argv size limit |

## Findings

### Critical
None.

### Important

1. **The template path only works inside the ai-kit checkout.** At SKILL.md:39-40 and :168, `skills/ai-kit-spec-review/references/cross-ai.mjs` is a path relative to the ai-kit repo root. In any other project, or with an installed skill under `~/.claude/skills/`, that path does not exist relative to the cwd. The policy file gets this right with a relative link (`../../ai-kit-spec-review/references/cross-ai.mjs`, subprocess-quota-policy.md:5).
   **Fix**: write it as a path relative to the skill: "the template at `../ai-kit-spec-review/references/cross-ai.mjs` relative to this skill's directory". Better still, say that a project without a copy should generate one through `ai-kit-gsd-curated-config` rather than run the unstamped template.

2. **The copy-paste launch example can stop its own review lane.** The examples are at SKILL.md:51-53, launch-and-wait.md:27-29 and :83-85, and all use `L=tmp/lane-pi`. The tree signature (`cross-ai.mjs:3466-3489`) works like this:
   - It runs `git add -A` plus `write-tree`, so an untracked, non-ignored `lane.err` that grows during the run changes the tree.
   - Ignored files count by stat signature unless their whole directory is ignored (`ls-files -o -i --directory`).
   - So in a project where `tmp/` is not ignored as a whole directory, the lane's own stderr redirect turns a review into `contract_violation tree=dirty`.

   The prose says "a temp dir or a gitignored one", but the example does not follow its own warning, and the "whole directory must be ignored" rule is never stated.
   **Fix**: use `L=$(mktemp -d)` in all three examples. Add one line: "an in-tree scratch dir must be ignored as a whole directory; a file pattern such as `*.err` still counts by stat."

3. **"Re-invoke the same lane" is underspecified.** At SKILL.md:120-121, the lane key is (checkout, CLI, model, route kind), and that definition appears only in policy.md:109. The route kind comes from `--route-<cli>` or `CONFIG.routerBacked` (`cross-ai.mjs:3788-3789`). A re-invoke that drops `--route-pi router` reads a different state file and starts a fresh episode at cycle 0. That quietly defeats the 600/900/1800 s series and the cap. A different prompt also loses the session resume, because the resume is keyed by `task_digest`.
   **Fix**: "Re-run the identical command line: same flags, including `--route-<cli>` and `--mode`, and the same prompt file. An early re-invoke is safe: the pending `due_at` refuses it without a model call and repeats the remaining wait."

4. **The GSD retry/skip/abort guidance only covers the hard tier.** SKILL.md:139-142 never says what to answer for exit 69 class stops (auth, billing, permission, bad model), exit 1, exit 124, exit 127, or a bare 75. Answering retry on an auth or billing stop just calls the model again, and those stops persist no state that would refuse the retry. An agent could also reason its way to skip.
   **Fix**: add "every other non-zero exit: give the notice (the report, upstream and AIKIT-XAI lines) and answer abort; retry only an exit 75 that carries `retry_after_s=`."

### Minor

5. **The stdin/argv sentence is muddled.** At SKILL.md:40-42 and :152-153, "Never put the prompt on argv while stdin is inherited" is not something a caller of the runner can do (the runner has no prompt argv flag), and the copilot clause does not justify it.
   **Fix**: "Always redirect the prompt into stdin (`< prompt.md`); an inherited TTY stdin reads as empty (`readStdin`, :4370) and exits 2 `empty_stdin`."

6. **Copilot's argv size limit is undocumented.** A copilot prompt over about 100 KB (`ARGV_PROMPT_MAX` 102400 plus a resume reserve, :3097-3111) is refused with exit 2 `usage` and nothing is spawned. The exit-2 row ("fix the invocation") gives the caller no hint why.
   **Fix**: add the limit to the copilot lines at launch-and-wait.md:69-73 and SKILL.md:153.

7. **The overlay time bound is misstated.** policy.md:143-144 says "one 50 ms time bound per call". The code has a 50 ms bound per match (`OVERLAY_MATCH_MS`) plus a 200 ms per-call budget (`OVERLAY_CALL_BUDGET_MS`, :1112-1113, :1663-1667), and the budget path prints a different notice.
   **Fix**: state both limits and both notices.

8. **The copilot review allowlist wording is wrong in two places.** policy.md:155-156 says "Copilot review uses its own allowlist and drops COPILOT_ALLOW_ALL". In fact:
   - Copilot's `reviewExtras` is `[]` (:1451). What it has is a review tools profile, not an extraArgs allowlist.
   - `COPILOT_ALLOW_ALL: ''` is dropped in both modes (`childEnv`, :3512; self-test `copilot-exec-ok`).

   **Fix**: correct both statements.

9. **A bare exit 75 is not explained.** The table row at SKILL.md:100 says "a bare 75 is an owner stop" but not when it happens: off-router quota (self-test `plain-quota-no-retry`) or an unwritable state file (:3884-3887). policy.md:38 ("quota on a confirmed router lane") reads as if off-router quota were not exit 75 at all.
   **Fix**: name both causes in one clause.

10. **Redundancy.** Pitfalls (SKILL.md:152-157) restate sections 2-3: stdin, two timeouts, no idle watchdog, tree check. The scratch-dir and tree-dirty advice appears at :44-45, :63-65 and launch-and-wait.md:7-9.
    **Fix**: keep each fact once, and keep only the non-obvious items in Pitfalls.

11. **No loading trigger for the policy reference.** subprocess-quota-policy.md is listed only at SKILL.md:16-17 and :165.
    **Fix**: add an in-flow trigger such as "read the policy before editing `workflow.cross_ai_retry`, writing an overlay row, or explaining a `stopped=`/`route=` value", plus "do not load it for a plain exit 0 or exit 2 read".

12. **Planning decision IDs leak into a portable skill.** policy.md:45, :75 and :83 reference D-10, D-02 and D-03, which mean nothing to an agent outside this repo.
    **Fix**: delete them.

13. **Project-specific executor guards.** SKILL.md:159-161 (`AI_KIT_REFUSE_REAL_HOME`, never stash, the "pre-existing" claim check) are ai-kit house rules with no stated reason, and "Atomic rewrites keep the file mode" (:161) is vague.
    **Fix**: add a one-clause reason to each, or move them to the executor skills.

14. **The description is missing literal trigger keywords.** At SKILL.md:3-9, add `cross-ai.mjs`, `AIKIT-XAI`, `exit 75`/`retry_after_s`, `quota`/`rate limit`, and the runtime names (pi, opencode, codex, cursor, copilot).

I did not run `--self-test` or any real CLI (read-only rules), so the example lines are trusted to match the self-test case names I found by grep. I did not re-verify the sibling skills' pointers beyond confirming that they link to `ai-kit-cross-ai`.

DIGEST fc34de9e11130d78
CURRENT 97/120
CRITICAL 0 IMPORTANT 4
