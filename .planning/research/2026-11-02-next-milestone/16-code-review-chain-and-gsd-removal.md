# Code-review chain, removing the GSD execute adapter, spec-review's loop (research, 2026-11-02)

Read-only. Builds on `12-herdr-and-review-lanes.md` (section 4: no ai-kit skill chains code review
today) and `8-spec-config-chain-superpowers.md` (how the superpowers adapter picks and dispatches);
neither is repeated. Scripts beside this file: `16-gsd-refs.sh` (every tracked reference to the GSD
adapter outside the v1.3 archives, output `16-gsd-refs.out`, 352 lines) and `16-shared-usage*.sh`
(who else uses each shared symbol the GSD adapter imports, outputs `16-shared-usage*.out`).
Superpowers paths are relative to
`~/.claude/plugins/cache/claude-plugins-official/superpowers/7.0.0/skills/`.

## 1. How superpowers does code review

### requesting-code-review (one review, no loop of its own)

- **Who reviews:** a fresh subagent filled from a template. Step 2 says "Dispatch a `general-purpose`
  subagent, filling the template at code-reviewer.md" (`requesting-code-review/SKILL.md:34`). The
  template header is `Subagent (general-purpose):` with no `model:` line
  (`code-reviewer.md:8-9`), so a standalone call runs on the session model. Only SDD names a model
  for it: the final whole-branch review goes on "the most capable available model, not the session
  default" (`subagent-driven-development/SKILL.md:192-194`, `:452`).
- **Input:** four placeholders, `DESCRIPTION`, `PLAN_OR_REQUIREMENTS` (plan path, task text or
  requirements), `BASE_SHA`, `HEAD_SHA` (`SKILL.md:36-40`). The reviewer runs
  `git diff BASE..HEAD` itself (`code-reviewer.md:23-31`). Under SDD the final review instead gets a
  prebuilt diff file from `scripts/review-package PLAN_FILE MERGE_BASE HEAD`
  (`subagent-driven-development/SKILL.md:447-451`).
- **Rules in the prompt:** read-only on the checkout ("never move HEAD", `code-reviewer.md:50-52`);
  "You Do Not Dispatch Subagents" (`:54-61`); a "Declined to judge" list before the verdict
  (`:43-48`).
- **Output:** Strengths; Issues as Critical / Important / Minor, each with file:line, what, why,
  fix (`code-reviewer.md:106-126`); Recommendations; then
  "**Ready to merge?** [Yes | No | With fixes]" plus a 1-2 sentence reason (`:131-135`).
  There is no machine `### Status:` line.
- **Loop:** none. "Fix Critical issues immediately / Fix Important issues before proceeding / Note
  Minor issues for later / Push back if reviewer is wrong" (`SKILL.md:42-46`). The loop lives in SDD.

### subagent-driven-development (where the loops are)

- **Per-task review:** after each implementer, a task reviewer from `task-reviewer-prompt.md` gets
  three files: brief, implementer report, review package (`SKILL.md:316-326`). Its template already
  has a model slot: `model: [MODEL — REQUIRED: choose per SKILL.md Model Selection ...]`
  (`task-reviewer-prompt.md:13-14`). Output: spec ✅/❌/⚠️, Critical/Important/Minor, and
  "**Task quality:** [Approved | Needs fixes]" (`task-reviewer-prompt.md:185`, `:206-207`).
- **Fix loop per task** (`SKILL.md:354-429`): runs on spec ❌ or any Critical/Important. Minor
  findings go to the ledger, never into the loop (`:361-365`). One round = one fix dispatch + one
  scoped re-review (`re-review-prompt.md`, verdict per finding ADDRESSED / NOT ADDRESSED,
  `:396-403`). Five rounds maximum: rounds 1-3 resume the implementer, 4-5 a fresh one on a more
  capable model (`:375-386`). At the cap the controller adjudicates each open finding (park with a
  ruling, or rule on the load-bearing one) and keeps going (`:411-429`).
- **Final review** (`SKILL.md:445-469`): one whole-branch review with `code-reviewer.md`; findings
  get ONE fix subagent and "exactly one scoped re-review"; residuals are adjudicated; "There is no
  second fix wave" (`:467`). Then `finishing-a-development-branch` (`:487`).
- **Model rule:** "Always specify the model explicitly when dispatching a subagent" (`:204-206`);
  reviewers scale with diff size and risk, re-reviews of small fixes take a cheap-to-mid tier
  (`:196-199`).
- **Rulings:** the controller never waits on a human; it records
  `Ruling: <what> — <why> — <cost if wrong>` and continues (`SKILL.md:19-25`), and lists every
  ruling in its final message (`:473-480`).

### receiving-code-review and finishing-a-development-branch

- receiving-code-review is a reading discipline, not a dispatcher: READ, UNDERSTAND, VERIFY,
  EVALUATE, RESPOND, IMPLEMENT (`SKILL.md:16-25`). For external reviewers: check correctness for
  this codebase, push back with reasons, and "IF conflicts with your human partner's prior
  decisions: Stop and discuss with your human partner first" (`:67-87`). That stop is where a jev
  classification would go before asking the user.
- finishing-a-development-branch runs no review. Step 1 runs the full test suite and stops on red
  (`SKILL.md:14-26`); then it offers merge locally / push and PR / keep (/ discard)
  (`:53-75`). It is the natural end of the chain, after the last review is clean.

### Where a (runtime, model) lane plugs in

ai-kit's adapter injects at SDD's "1. Dispatch the implementer" and says Step 4 (task review, fix
loop, final review) runs unmodified (`skills/ai-kit-spec-execute-superpowers/SKILL.md:278-283`). The
same kind of point exists for review, three times:

1. **Task reviewer dispatch** (SDD `SKILL.md:308-352`): the `model:` slot of
   `task-reviewer-prompt.md:13`. All inputs are files on disk, so an external CLI can read them.
2. **Scoped re-review in the fix loop** (`SKILL.md:396-403`, `re-review-prompt.md`).
3. **Final whole-branch review** (`SKILL.md:445-456`, `code-reviewer.md`), which is also the
   standalone `requesting-code-review` Step 2.

Point 3 is the one that matches the owner's wish ("when an implementation completes"). It is a
single dispatch with file inputs and a read-only contract, so it maps cleanly onto the runner's
`--mode review` (read-only tree gate). The review package lives in `.superpowers/sdd/<plan>/`, which
`sdd-workspace` git-ignores with its own `.gitignore` (`scripts/sdd-workspace:84-86`), so writing
it does not trip the runner's dirty-tree gate (`cross-ai.mjs:3323`, `:4254`).

Gaps to close for a lane at point 3:
- Verdict format: the reviewer prints "Ready to merge? Yes | No | With fixes", not
  `### Status:`. spec-review's `merge-reports` (double mode) and Step 2 parse `### Status:` lines
  only. Either ask the external reviewer to add a `### Status:` line or teach merge-reports the
  code-review shape.
- "Iterate until everything passes" contradicts SDD's single final fix wave (`:467`). ai-kit has to
  own that loop itself, after SDD's final review and before finishing-a-development-branch: review
  lane, then one fix subagent, then a fresh review, up to a cap, with jev classifying residual
  findings (fix, park with a ruling, or ask the user). A cap is needed (spec-review uses 3, SDD 5).
- The task reviewer and re-reviewer can stay native (cheap, frequent); putting cross-AI lanes there
  multiplies cost by the number of tasks. Treat that as an option, not the default.

## 2. Removing `ai-kit-spec-execute-gsd`

### What it is

- `skills/ai-kit-spec-execute-gsd/`: `SKILL.md`, shim `ai-kit-spec-gsd.py` (21 lines), package
  `ai_kit_spec_gsd/` (`adapter.py` 336, `cli.py` 543, `gsd_config.py` 198,
  `cross_ai_guidance.py` 43, `gsd_cross_ai.py` 30), `references/` (cross-ai-hook-setup, dispatch-notes,
  resumable-state, session-wake).
- What only it does: per-phase live-quota pair resolution, a native-tier pin or
  `workflow.cross_ai_command` written via gsd-tools with ownership and undo backups, the
  `--no-preamble --prepend-file .planning/scripts/cross-ai-guidance.md` hook, codex
  `--codex-sandbox workspace-write`, resumable state and session wake, then `/gsd-execute-phase`
  (its `SKILL.md:1-40`). GSD cross-AI execution itself does not depend on it: curated-config v2
  already writes `workflow.cross_ai_command` naming the same runner
  (`skills/ai-kit-gsd-curated-config/SKILL.md:226-236`).

### Everything that must change (from `16-gsd-refs.out`)

Delete
- `skills/ai-kit-spec-execute-gsd/` (whole folder).
- `tests/test_ai_kit_spec_gsd.py`. **Move first** its `TestDetectFramework` class
  (`:1549-1560`): it tests the router's `detect_framework`, which stays. (The superpowers test
  file also imports `detect_framework`, so some router coverage remains, not checked how much.)

Edit tests
- `tests/test_ai_kit_spec_e2e.py:1,14,17`: the `TestRealGsdConfigSet` class (`:86-110`) drives
  `ai_kit_spec_gsd.cli` `write-workflow-keys`; drop it. `TestRealGsdTools` (`:20-80`) tests the
  shared `gsd_tools` and stays (its `prior_value` checks go if `prior_value` goes).
- `tests/test_ai_kit_spec_gsd_tools.py:78-87`: reads the GSD adapter's SKILL.md to pin the
  gsd-core lookup order. Repoint to curated-config's text or drop that one test.
- `tests/test_ai_kit_spec_legacy_config.py:12,437-449` (imports `adapter.assemble_candidates`).
- `tests/test_ai_kit_spec_trust.py:17,439` (imports the GSD cli).
- `tests/test_cross_ai_runner_e2e.py:672-676` (imports the GSD cli and `build_cross_ai_command`).
- `tests/test_arch.py:782` (`_PHASE25_SKILLS`), `:786` (`_PHASE25_LADDER_PKGS`), `:1799` (a
  non-vacuity sample string naming `ai_kit_spec_gsd.cli`; keep the shape, rename the package).
- `tests/test_quota_policy_text.py:17-18`, `tests/test_cross_ai_skill_text.py:58`,
  `tests/test_ai_kit_spec_runtimes_table.py:811,831,837` (SKILL/reference text lists).
- `tests/test_gate_scope.py:38` (frozen ruff path regex).
- `tests/test_ai_kit_gsd_curated_config.py:474` (docstring only).

Edit build and config
- `Makefile:12` and `.pre-commit-config.yaml:14,59`: drop `tests.test_ai_kit_spec_gsd`
  (`tests.test_ai_kit_spec_gsd_tools` and `tests.test_ai_kit_spec_e2e` stay).
- `pyproject.toml:123` (pyright `extraPaths`).
- `tools/run_unittest_parallel.py:60` lists `tests.test_ai_kit_spec_e2e` in an exception set; it
  stays if the module stays.
- Installer: no code names the skill. `prune_stale` / `apply_stale_prune`
  (`tools/setup.py:1367-1377`) should remove the live link
  `~/.claude/skills/ai-kit-spec-execute-gsd -> <checkout>/skills/ai-kit-spec-execute-gsd`
  (present today); needs a live check on the next install.
- `.claude-plugin/plugin.json`: no mention.

Edit skill text and comments
- Router `skills/ai-kit-spec-execute/SKILL.md:3` (description), `:58` (the `"gsd"` branch), `:79`
  (anti-pattern that says the GSD adapter writes `.planning/` state).
- `skills/ai-kit-gsd-curated-config/SKILL.md:128,231-236` and `references/runner.md:31-32` (name
  the GSD adapter's hook as the copilot path and the only `--prepend-file` user).
- Comments: `ai_kit_gsd_curated_config/cross_ai_build.py:4-5`, `model_detect.py:8`,
  `skills/ai-kit-session-wake/ai-kit-session-wake.py:4`,
  `ai_kit_spec_superpowers/cli.py:2,11`, `dispatch_injection.py:166-171`,
  `ai_kit_spec/dispatch_guidance.py:2`, `ai_kit_spec/gsd_tools.py:11`.
- `README.md:38` (skills table row).
- Planning: `.planning/PROJECT.md:66`, `.planning/ROADMAP.md:384` (and backlog 999.17, which is
  scoped to all three execute skills), todo
  `2026-10-31-refactor-execute-gsd-and-rules-agents-sj-1-sj-3.md` (its execute-gsd half becomes
  moot), todo `2026-11-02-tooling-defects-...md:107`.
- History docs only (leave alone): `docs/superpowers/plans/2026-08-29-ai-kit-spec-execute-gsd.md`
  (127 hits) and other plans/specs, `.planning/research/2026-10-13-audit/*`, archives under
  `.planning/milestones/`.
- No goal-prompt text names it (the goal-prompt skill and `NEXT-MILESTONE-INPUTS.md` mention it
  only as the removal wish, `:603`, and the refactor todo, `:15,22,32,255`).

### Shared code that becomes unused

Checked with `16-shared-usage*.sh`; almost everything the adapter imports is shared with the
superpowers adapter or curated-config and stays (`execute_selection`, `quota`, `execute_dispatch`,
`tooling_guidance`, `detection`, `cache`, most of `gsd_tools`, `project_runner_command`).
What loses its last production caller:
- `runner_dispatch.project_runner_command(..., guidance=True)` and `PROJECT_GUIDANCE_PATH`
  (`runner_dispatch.py:33`, `:195-196`). The only `guidance=True` caller is
  `gsd_cross_ai.py:30`; curated-config calls it without guidance (`cross_ai_build.py:114`).
  Tests still use it (`test_ai_kit_spec_runner_dispatch.py:156`, `test_curated_config_script.py:480`).
- So the runner's `--prepend-file` loses its only hook user (`--no-preamble` stays: ai-kit's own
  dispatch passes it, `runner_dispatch.py:261`). Side effect: curated-config still writes
  `.planning/scripts/cross-ai-guidance.md` (`cross_ai_script.py:316-352`) while its own hook never
  reads it (`SKILL.md:228-229`). After removal nothing reads that file. Either wire curated's hook
  to `guidance=True` or stop writing the file.
- `gsd_tools.prior_value` (`gsd_tools.py:289`): only `gsd_config.py:126` and the e2e test use it.
- `gsd_tools.config_set` loses one of two callers (curated-config's `cli.py` keeps it).
- The `ExecuteSeams` / `build_execute_guidance` pair and `format_block` stay: the superpowers path
  passes `--format-block-file` (`ai_kit_spec_superpowers/cli.py:319-351`).

### What the router should do with a GSD plan

Keep detection (so a GSD plan is never run through superpowers SDD), and change the `"gsd"` branch
to a hand-back: "This is a GSD phase; run GSD's own `/gsd-execute-phase <N>` (project-local
install)." Add one line: cross-AI execution then happens only if `workflow.cross_ai_command` is set,
which `ai-kit-gsd-curated-config` does; ai-kit no longer picks a per-phase pair or checks quota for
GSD. Do not invoke `/gsd-execute-phase` from the router: the GSD adapter was Claude-Code-only
because it used the Skill tool on a per-project install (its description), and a portable router
should just name the command. The router's description and the `:79` anti-pattern need the same
rewording. Lost on removal (owner should know): the per-phase quota-checked pick, the codex
workspace-write sandbox for GSD runs (curated v2 passes none, `SKILL.md:226-228`), and copilot as a
GSD runner (curated refuses it, `SKILL.md:124-128`).

## 3. spec-review's loop today

All lines in `skills/ai-kit-spec-review/SKILL.md` unless named.

Iteration
- Cap: 3, "configurable per invocation if user requests" (`:190`). One iteration = one reviewer
  dispatch, then maybe one fixer dispatch (`:239`). `Issues Found` at iter == cap ends with "Hit
  iteration cap (N) ... Decide manually." (`:397`, `:446`). So at most 3 reviews and 2 fix passes.
- Convergence: the loop ends on the reviewer's `### Status: Approved` (`:396`). The checklist
  prints Approved only with no blocking findings; its Issues shape has CRITICAL and HIGH, MEDIUM
  optional (`skills/ai-kit-spec-review-checklist/SKILL.md:251-282`), and a re-review judges the
  current state fresh, never carrying "previously flagged, now fixed" (`:281-282`). Unknown status
  text counts as Issues Found (`:399`); no status line is a failure (`:400`).
- Fixer: `Edits Applied` -> next iteration "with fresh reviewer"; `Escalation Required` and
  `No Edits` end the loop (`:429-432`). Fixer is sonnet on Claude Code, session default elsewhere
  (`:189`).
- Fresh reviewer every round: "Always dispatch a NEW subagent each iteration. Do not reuse."
  (`:473`), "re-review with fresh reviewer" (`:429`). Subprocess lanes are new runner calls too.
- Disagreement: "If reviewer and fixer disagree on a finding's severity across iterations, surface
  to user. Orchestrator does not arbitrate." (`:476`).

jev
- Not used anywhere in spec-review, the checklist, the fixer, spec-config, the execute router or
  the superpowers adapter (grep). Only `ai-kit-gsd-curated-config`, `ai-kit-gsd-spec-discuss`,
  `ai-kit-spec-goal-prompt` and jev itself mention it. The ladder client a caller would use is
  `skills/ai-kit-gsd-spec-discuss/scripts/decide.py` (`ladder`, `detect`, `consent`), which lives
  inside spec-discuss, not in a shared place; jev's own client is
  `skills/jev-fast-decision/scripts/jev_review.py`. A spec-review or execute chain must find
  `decide.py` across skills or move it somewhere shared.
- Natural jev points in spec-review: the severity disagreement (`:476`), "any other text on the
  Status line" (`:399`), cap reached and escalation (`:446`, `:430-431`, today "Decide manually"),
  and the 3b-surface hand-off (`:415`). Trust (`trust-local`, `:175-183`) must stay a user yes,
  never jev. jev answers are advisory; `needs_fallback` means the orchestrator decides itself
  (jev SKILL description).

Lanes
- Chosen once per invocation, before the loop (`:151`): `probe-quota` then `resolve-reviewers`
  (`references/cross-ai-dispatch.md:146-205`). The list stays fixed for every iteration.
- `resolve_reviewers` (`ai_kit_spec/quota.py:121-189`): `--no-cross-ai` gives the session default
  (`:166-167`); the ladder is narrowed to `purpose` review/both/unset, falling back to the full
  ladder with one warning (`:173-177`); `policy.mode` `single` picks one entry, preferring a vendor
  other than the author's (`:188-189`); `double` picks a primary from the full ladder and a
  secondary of a different vendor, dropped if none (`:178-187`). Empty ladder or no quota gives the
  session default (`:189`).
- Pre-dispatch walk: an entry whose probe fails (quota, timeout, any reason) is skipped and the next
  ladder entry is used, possibly another provider; at the end, the session default, with
  "every configured reviewer unavailable; reviewed with the session default" (`:157-170`). Two parts
  are flagged as not owner-ruled: the implicit session default and skipping on non-quota failures
  (`:166-168`).
- After dispatch, no switch: "Never switch harness, provider or model." (`:352`) and "Never
  re-dispatch a failed subprocess lane to another CLI, provider, model or the native session."
  (`:477`).
  - exit 75 with `retry_after_s=` gets one one-shot re-invoke of the same lane, CLI and model at
    that delay (`:330-335`); in double mode the sibling is merged as single mode meanwhile
    (`cross-ai-dispatch.md:269`).
  - exit 69 (auth, `stopped=hard-waits`, `stopped=cap`, refusal) prints the evidence verbatim and
    stops (`:336-341`).
  - A bare exit 75 is an owner stop (`:341-342`).
  - Any other nonzero exit deletes the report, which becomes a `Failure` (`:342-343`); in double
    mode `merge-reports` prints `### Status: Failure — <lanes>` (`:371-378`), and Failure ends the
    loop (`:398`).
- So one lane failing in iteration 2 ends the whole review. The owner's "resilient fallbacks and
  switches per user preference" needs the opt-in runtime and model escalation flags from the Round 1
  decision (`NEXT-MILESTONE-INPUTS.md:345-347`), plus a re-resolve of the reviewer list per
  iteration or on failure. Today it is resolved once.

---
Not checked: how much router `detect_framework` coverage the superpowers test file has; whether
`prune_stale` removes the GSD link on a real re-install; the runner's behaviour with a code-review
prompt in `--mode review` (nothing ran).
Risk: the owner wants code review to iterate until it passes, but superpowers allows one final fix
wave by design. ai-kit must own that outer loop (with a cap and jev on residuals), or it will fight
SDD's own rules.
