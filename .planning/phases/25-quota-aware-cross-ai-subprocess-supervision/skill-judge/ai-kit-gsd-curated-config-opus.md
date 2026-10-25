# ai-kit-gsd-curated-config — skill-judge report (native Opus subagent, clean context)

Round 5 (evidence round), skill digest `089d13c6a215b519`, judged at commit e2bb140. Rubric: the skill-judge skill (120 points).

# Skill-judge report: ai-kit-gsd-curated-config (read-only review)

**Verdict:** 104/120, grade B. The skill follows a Process/Tool hybrid pattern. I estimate its knowledge mix at about 80% expert, 15% activation and 5% redundant. It describes the Phase 25 runner contract correctly: the claims I checked match the code. The main weaknesses are one unclear statement about live dispatches and text that repeats itself.

I read SKILL.md (403 lines), `references/runner.md`, `references/v1-path.md`, `evals/`, the linked policy, the Phase 25 diff (`11ac3eb..HEAD`) and the code behind the key claims (`cross_ai.py`, `cross_ai_script.py`, `plan_edit.py`, `apply.py`, `catalog_adapter.py`, `recommend.py`, and the runner template `skills/ai-kit-spec-review/references/cross-ai.mjs`).

## Phase 25 claims checked against the code (all match)

- **One CLI per call:** the runner starts only the first `prefer` entry and logs "no automatic fallback". A missing first CLI stops with `not_installed` (exit 127) (`cross-ai.mjs:6074-6100`).
- **Exit map:** SKILL.md:38-42 matches `STATUS_TABLE` (`cross-ai.mjs:799-819`). The 4-hour cap stop exits 69 (`cross-ai.mjs:2413`).
- **Status lines:** every status line carries `action=stop` (`cross-ai.mjs:905-910`). The `cross-ai: report` line is printed only when the status is not `ok` (`cross-ai.mjs:885-892`).
- **Router lanes:** `routerBacked` true means `router`. A name-only match gives `router-inferred`, which gets no quota cycles (`cross-ai.mjs:1605-1617`).
- **`router_backed` rule:** `recommend` and `plan-set` use the same rule: `is_router`, `router_confirmed` and the `execute` purpose (`cross_ai.py:78-89`, `plan_edit.py:208-243`).
- **Readiness and upgrades:** `ensure-runner` treats template 7 as the minimum ready template (`cross_ai_script.py:32`, `:301-306`). A pristine runner takes a same-version fix (`cross_ai_script.py:255-262`). An upgrade keeps the old CONFIG, including an unused `retries` key (`_upgrade_config`).
- **Policy links:** both relative links resolve. The skill points to the policy instead of copying it, which is what the policy asks for. It forbids switching harness, provider or model in three places (SKILL.md:225-228, 247-249, 376-378).

## Dimension scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 17 | 20 | Almost all project-specific expert facts. Repeated statements cost tokens (finding 2). |
| D2 Mindset + Procedures | 13 | 15 | Has an "ask yourself" step before v2, a correct non-obvious order (dry run, end the turn, then apply) and a failure-state guide. |
| D3 Anti-patterns | 14 | 15 | Specific NEVER list with reasons, plus a mistake / why / fix table. |
| D4 Specification | 14 | 15 | Valid frontmatter. Description covers what it does, when to use it, and trigger words (`ensure-runner`, `cross-ai.mjs.new`). |
| D5 Progressive Disclosure | 12 | 15 | Good loading triggers and a "Do NOT load" line. But SKILL.md is 403 lines (over the ~300 ideal), and the same `.new` and readiness text sits in both SKILL.md and runner.md. |
| D6 Freedom Calibration | 14 | 15 | Exact commands for fragile writes; judgment left only for reporting. |
| D7 Pattern | 8 | 10 | Clear Process/Tool hybrid, but over the target length. |
| D8 Usability | 12 | 15 | Thorough on errors. Gaps around dispatch scope, the owner re-invoke, and the upgrade behaviour change. |

## Findings

1. **Important: "verification runs" invites a live, full-permission dispatch the flow never needs.**
   SKILL.md:244 says "After every external dispatch you run through the runner, verification runs included". No step in v2 or v1 runs a model call; the only check is `--print-argv` (runner.md:82-88). SKILL.md:233-236 says the v2 hook runs every target with full permissions, codex included. The current wording lets an agent "verify" the runner by sending a real task to an unsandboxed CLI on the target project.
   *Fix:* add one line under "Cross-AI execution": "This skill never dispatches a model call. Check the runner with `--print-argv` only. A live dispatch runs with full permissions and only when the user asks for one." Then reword :244 to "When you see a dispatch's output (a GSD run or one the user asked for)…".

2. **Minor: the same rules are written several times.**
   - "Never answer a runner stop by reordering `prefer`…" appears almost word for word at SKILL.md:247-249 and :376-378.
   - The template-7 readiness rule appears at SKILL.md:263-267, :352 and runner.md:62-69.
   - "`.new` is not active" appears at SKILL.md:261-270, :373-375, and runner.md:54-60 and :81-84.

   *Fix:* keep each rule once, in "Cross-AI execution" or runner.md. Shorten the NEVER entry to its bold line. Cut the `ensure-runner` table cell at :352 to "prints `{ready, runner, guidance, notes}`; see runner.md". This brings SKILL.md toward 350 lines.

3. **Minor: an upgraded runner keeps its old `prefer` list, but the list now means something different, and the user is not told.**
   `_upgrade_config` keeps the old CONFIG (`cross_ai_script.py:228-236`). In a template 6 or earlier runner, `prefer` was a fallback chain. After the upgrade to template 7 only the first entry runs. runner.md:54-60 says the CONFIG is kept but not that its meaning changed.
   *Fix (runner.md, "Runner upgrade"):* "After an upgrade from template 6 or earlier, tell the user that the runners after the first `prefer` entry no longer run automatically; they are now the owner's menu."

4. **Minor: the owner re-invoke at SKILL.md:226-227 is hard to carry out as written.**
   It says to re-invoke "with the same prompt on stdin". But GSD builds that prompt and the owner usually doesn't have it. A manual run also bypasses GSD's capture of stdout into the SUMMARY. It also does not mention checking the tree first: the policy's dirty-tree rule (policy:32-33) can stop the ladder.
   *Fix:* make the main route "re-plan `script:cross-ai.prefer`, re-apply, then retry from GSD". Keep the manual `--prefer <id>` command as a secondary option, with "check `git status` first; its output does not reach GSD's SUMMARY".

5. **Minor: no fix is given for a router lane that is not yet confirmed.**
   SKILL.md:106-112 says `router_backed` cannot be edited directly but does not say how to earn it. The code emits a `router_unconfirmed` note telling the user to confirm the router via `ai-kit-spec-config` (`recommend.py:447-466`).
   *Fix:* add "for a `router_unconfirmed` note, confirm the router through `ai-kit-spec-config`, then re-run `inventory` and `recommend`; until then that lane gets no quota cycles".

6. **Minor: runner.md lists the failure-ladder settings without saying how they are changed.**
   runner.md:43-47 lists `sameSessionRetries`, `cooldownS` and the others. None of them are plan keys: `runner_config` fills them from the template (`cross_ai_script.py:101-114`). Changing one means hand-editing CONFIG, which pins the runner to `.new` upgrades (runner.md:78-79).
   *Fix:* "These are not plan keys. Changing one is a hand edit of CONFIG, and the next apply writes `.new`."

7. **Minor: runner.md is loaded for every non-ok dispatch, but holds nothing about what to do at a stop.**
   Both SKILL.md:271-273 and runner.md:3-6 send the agent to runner.md for any non-ok status. Its failure-ladder section only lists settings and links to the policy, which SKILL.md:221-223 already makes mandatory reading.
   *Fix:* drop the non-ok trigger from runner.md's header and from SKILL.md:273. The policy is the one document to read at a stop.

8. **Minor: no eval covers the Phase 25 stop behaviour.**
   `evals/01` to `04` test setup under time pressure only. None gives a runner stop together with pressure to "just use another CLI".
   *Fix:* add `evals/05-runner-stop.md` (exit 75 off-router, with the user asking to retry on another CLI). It should pass only if the agent prints both lines verbatim, schedules nothing, and switches nothing.

9. **Minor: a few long lines that are hard to read in raw markdown.** SKILL.md:218, :226-227 and :377 run well past 100 characters. *Fix:* re-wrap them to about 100 characters.

I did not run the runner's `--self-test` or any test suite (the task was read-only), so the code checks above come from reading the source. I also did not compare against `ai-kit-spec-execute-gsd`'s hook, beyond what this skill says about it.

DIGEST 089d13c6a215b519
CURRENT 104/120
CRITICAL 0 IMPORTANT 1
