---
created: 2026-11-21T13:04:12Z
title: Hand cross-AI setup to curated-config instead of stopping
area: skills
severity: major  # suggested by capture agent, not confirmed by the owner
files:
  - skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py:99-113
  - skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py:255-257
  - skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py:448-476
  - skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py:535-546
  - skills/ai-kit-spec-goal-prompt/scripts/gp_host.py:348-364
  - skills/ai-kit-spec-goal-prompt/SKILL.md:43-45
  - skills/ai-kit-cross-ai/SKILL.md:39-45
  - skills/ai-kit-cross-ai/SKILL.md:168-172
  - skills/ai-kit-gsd-curated-config/SKILL.md:353
  - skills/ai-kit-gsd-curated-config/SKILL.md:379-381
  - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py:358-368
---

## Problem

Owner idea (translated from Spanish): both when goal-prompt runs and when the autonomous run runs,
other skills must be checked and triggered. Example: the skill behind gsd-config
(`ai-kit-gsd-curated-config`) when the project is a GSD project: copy the script that enables
cross-AI execution (`cross-ai.mjs` through `ensure-runner`) and the cross-AI review configuration when
the user asks for them. In another project an agent stopped on cross-AI execution only because
`cross-ai.mjs` did not exist, although it could have run with pi. Cross-AI was not required there;
required or not, the agent should hand the flow to the other skill (set up the runner) or use the repo's
normal mode, not stop.

What exists today (read on 2026-11-21):

- A GSD render with `native_execution: false` (the default of question 3, `SKILL.md:43-44`) emits
  `CROSS_AI_RULE` plus `READINESS_RULES` (`gp_sections.py:99-113`, `255-257`). The text ends: "Then confirm
  the runner script exists ... If any check fails, stop and report what to fix." That is a stop with no
  hand-off to a setup skill. Verified 2026-11-21 (section "Evidence from the gitid project" below): in
  the gitid session no generated prompt was ever run; the stop happened at goal-prompt time. The
  render warned `cross-AI readiness failed: script missing`, and the agent, reading this rule, judged
  that the cross-AI run "would stop at its first step", rendered a second native-execution file and
  asked the owner to pick. The warning itself was a false positive (a slash in the model id of a direct
  `opencode run --model router-env/my-coding` command read as a missing script path).
- STOP IF also carries "A step needs a real config write, a login or sudo" and, for OpenGSD, "Every
  cross-AI candidate for a role is unusable" (`gp_sections.py:535-546`).
- goal-prompt only observes readiness at detect time: `_runner_problems` reports `cross_ai_execution off`,
  `no cross_ai_command`, `executable missing`, `script missing` (`gp_host.py:348-364`); render prints
  them as warnings on stdout, never into the file (`SKILL.md:138`). It never offers a fix.
- goal-prompt and the autonomous block name no setup skill. The block's candidate skills include
  `ai-kit-cross-ai` (`goal_prompt.py:39`); `ai-kit-gsd-curated-config` is not among the ones the
  rendered file lists (rendered file line 24).
- `ai-kit-cross-ai` already says a project without `.planning/scripts/cross-ai.mjs` uses the template
  `skills/ai-kit-spec-review/references/cross-ai.mjs`, and routes the owner to curated-config
  `ensure-runner` only for a lower template or a waiting `.new` (`SKILL.md:41-45`). Its section 8 and the
  curated-config NEVER list forbid moving work to the native session after a runner stop
  (`ai-kit-cross-ai/SKILL.md:168-172`, `ai-kit-gsd-curated-config/SKILL.md:379-381`). Those rules are about
  a lane that already started or stopped, not about a runner that was never set up; whether they apply
  before the first launch is a decision to make.
- `ensure-runner --cwd <project>` renders or upgrades only `.planning/scripts/cross-ai.mjs` and prints
  `{ready, runner, notes}`, exit 0 ready / 1 not ready / 2 error (`curated-config SKILL.md:353`,
  `cross_ai_script.py:358-368`; read the code: it writes the script, not `.planning/config.json`).
  Readiness rule 1 (`workflow.cross_ai_execution`, `workflow.cross_ai_command`) is NOT satisfied by it:
  that needs the v2 flow with plan review and dry run before any apply (`SKILL.md:360-363`), and
  `recommend` takes `--cross-ai-review y|n --cross-ai-exec y|n` (`SKILL.md:105`).
- Cross-AI review lanes (reviewer and executor sets in ai-kit's `config.toml` `[lanes]`) belong to
  `ai-kit-spec-config` (its description), a different skill from curated-config's GSD review keys.

## Solution

Wanted behaviour:
1. goal-prompt (detect and relay, not run): when the project is GSD and the readiness problems say the
   runner or its config is missing, relay that and name the skill and command that fixes it
   (`ai-kit-gsd-curated-config` `ensure-runner`, or the v2 flow for config). No fifth question
   (`SKILL.md:160`); the offer is part of the hand-off text. It never runs the generated prompt and never
   edits project config itself (`SKILL.md:159`).
2. The rendered cross-AI rules replace "stop and report what to fix" with an ordered ladder: a missing
   runner script -> run curated-config `ensure-runner` (a project file only, report `ready`); config keys
   missing -> report and park the cross-AI items, because the v2 flow needs the owner's plan review;
   still not ready -> run the plan in normal (native) mode and say so in the report. Never a silent stop,
   never a real config write without the owner.
3. The same hand-off exists in the execution entry points that learn the runner is missing mid-run
   (`ai-kit-spec-execute`, `ai-kit-cross-ai` section 2), so an agent without goal-prompt behaves the same.

Acceptance checks a test can pin:
- Detect/render with a GSD fixture whose runner script is missing: the relay names `ensure-runner` and
  the file text carries the ladder, not "stop and report what to fix".
- With `native_execution: true` the ladder text is absent (no change from today).
- A test runs `ensure-runner --cwd <tmp fixture>`: the script exists afterwards, `.planning/config.json`
  bytes are unchanged, `ready` is reported, and an edited runner is kept or gets `.new`.
- A fixture with the script present but config keys off: the text parks cross-AI items and does not
  call `apply`.
- No path or command in the rendered text is absolute (AGENTS.md rule), and the length caps hold
  (60 rule lines, 7,000 characters; the cross-AI render with every owner field set can already hit 60,
  `SKILL.md:122`).
- Skill text tests: `ai-kit-cross-ai` and curated-config SKILL.md still pass their doc-contract tests
  (`tests/test_cross_ai_skill_text.py`, `tests/test_quota_policy_text.py`).

Where to change: `gp_sections.py` (`READINESS_RULES`, `plan_rule_lines`, `stop_lines`),
`gp_host.py` (readiness relay), goal-prompt `SKILL.md` (hand-off and the When-something-is-missing
table), `ai-kit-cross-ai/SKILL.md` section 2, optionally `ai-kit-spec-execute/SKILL.md`; tests in
`tests/test_ai_kit_spec_goal_prompt_variants.py`, `_render.py`, `_golden.py`, plus a new ensure-runner
hand-off case. Docs: READMEs of the touched skills. The repo requires tests, docs and the skill-judge
loop for every changed `SKILL.md` (three-round cap, then the owner decides). Phase 37 and 38.1 already
edit `ai-kit-cross-ai` and the runner template (`.planning/ROADMAP.md` Phase 37/38.1 code anchors), and
Phase 47.2 edits `rail_sections`; sequence this after them or fold it into one of them.

Risks and open questions:
- Which skill triggers: curated-config for runner and GSD config keys; `ai-kit-spec-config` for lanes.
  Does the owner want one hand-off or two?
- What counts as the owner asking for cross-AI: question 3's default (`native_execution: false`) is a
  default, not an ask. Candidate rule: only an explicit statement in the request, a stated rails file or
  an existing `cross_ai: true` plan counts; otherwise the safe default is normal mode. Needs the
  owner's decision. The 2026-11-16 goal file chose native and says cross-AI "stays off".
- Is a missing runner a state to repair or a reason for native mode? `ensure-runner` writes an executable
  script that later runs with full permissions (`curated-config SKILL.md:230-233`); the owner may want a
  consent step even though it is a project file, and the block's SAFETY text ("real config write") needs a
  line saying whether a project-local runner render counts.
- Reconcile with "never move the work to the native session" (`ai-kit-cross-ai/SKILL.md:170-172`): the
  rule must be scoped to a stop after a launch, and the wording changed on purpose, with the judge loop.
- Pi as a fallback: calling the template `skills/ai-kit-spec-review/references/cross-ai.mjs` directly
  with `--runtime pi` (allowed by `ai-kit-cross-ai/SKILL.md:41-42`) is not the same as GSD's
  `cross_ai: true` delegation, which needs `workflow.cross_ai_command`. Whether GSD can use a direct call
  is NOT verified.
- Unverified: how `/gsd-autonomous` itself behaves when `cross_ai: true` plans meet a missing
  `cross_ai_command` (not read in this capture).

## Evidence from the gitid project (2026-11-21)

References (read-only; do not copy the transcripts):
- Transcript: `~/.claude/projects/-var-home-bazzite-git-personal-gitid/b7185951-7d7e-4b13-89b2-350c6267edc8.jsonl`
  (one session, first entry 2026-11-21T11:15:39Z, last read entry 13:12:33Z = 10:12 local; file mtime
  10:12:33 -0300 and still growing while read). No other gitid session exists after 2026-09-27; no pi,
  opencode or codex session ran the rendered goal (searched `~/.pi/agent/sessions`, opencode and codex
  stores for gitid after 08:00).
- Rendered file: `gitid/.planning/goals/2026-11-21-phases-09-8.md` (untracked; rewritten 10:07 and 10:12
  local, the last one hand-edited by the agent). Findings: `gitid/.planning/research/09.8-resume-findings.md`.
- gitid `.planning/config.json` (uncommitted diff only adds `response_language` and drops the reviewer
  fallback keys) has `workflow.cross_ai_execution: true` and
  `workflow.cross_ai_command: "opencode run --model router-env/my-coding"`; `.planning/scripts/` does not exist.

What happened (transcript line numbers are JSONL lines):
1. Owner asked (L1937, 11:35:02Z) for an app review and then "ai-kit-spec-goal-prompt to create a prompt
   to continue in autonomous mode". Skill loaded from `/home/bazzite/.claude/skills/ai-kit-spec-goal-prompt`
   (L2493, 11:38:34Z).
2. Render with `native_execution: false` returned `warnings: [ 'cross-AI readiness failed: script missing' ]`
   (L2878, 11:41:45Z). The rendered RULES carried "If any check fails, stop and report what to fix."
3. Decisive agent reasoning (L2897, 11:41:57Z): "The cross-AI prompt's runner script is missing from this
   repo, so that run would stop at its first step. I'll render a native-execution variant as a labelled
   alternative for you to choose." It wrote `...-09-8.md` and `...-09-8-2.md` (native); the owner asked
   "why two similar goals?" and then: "use cross-ai runner router-env my-coding-lite on pi, also use
   reviwer lines using opencode router-env/my-referee-one (default) and my-referee-two" (both ~11:44Z).
4. The agent loaded `ai-kit-gsd-curated-config` (L2979, 11:46:30Z), ran `inventory` and
   `recommend --cross-ai-review y --cross-ai-exec y` in a scratch dir, then paused (L3114, 11:48:25Z,
   translated): "Applying standard would rewrite about 55 keys of your config.json and change things you
   did not ask for, so I leave it paused to decide with you." It never ran `ensure-runner`, never
   offered a trimmed plan on its own, and asked the owner again in its 12:21:32Z report (L4563).
5. The final goal moved runner setup into step (2) of the objective with the note "the RULES readiness
   checks run after this step", while the autonomous block still renders "First step, before any
   execution: confirm ... If any check fails, stop and report what to fix" (rendered file lines 63-65),
   which contradicts the objective's own order.

Cause, ranked with evidence:
1. (d) Detection bug, verified: `_runner_problems` (`skills/ai-kit-spec-goal-prompt/scripts/gp_host.py:362-363`)
   reports "script missing" for any later token that contains `/` and is not a repo path. A model id like
   `router-env/my-coding` matches. Reproduced with the repo's current code and a scratch repo:
   `'opencode run --model router-env/my-coding' -> (['script missing'], [...])`
   (`tmp/run-2026-11-19/capture/repro_script_missing.py`, removed after the run). The gitid command was a
   direct opencode call with `opencode` installed, so no runner script was needed; the warning was wrong.
2. (a) The rendered stop rule, verified as the trigger of the agent's choice: the agent quoted no other
   source; it predicted the stop from READINESS_RULES (`gp_sections.py:106-113`) plus the warning, and
   offered a native variant instead of a fix.
3. (c) Uncovered case, verified: goal-prompt names no setup hand-off (no `ensure-runner` in its text),
   and curated-config has no runner-only or trimmed-plan path that the agent saw as allowed, so it
   parked the owner's explicit pi request twice. The rules also never say what a direct-CLI
   `cross_ai_command` (not `node .../cross-ai.mjs`) means for the "argv listing" check, which only
   the ai-kit runner can satisfy (`gp_host.py:367-379`).
4. (b) Stale skill: ruled out (next section).

Staleness: not stale. `~/.claude/skills/ai-kit-spec-goal-prompt`, `ai-kit-cross-ai` and
`ai-kit-gsd-curated-config` are symlinks into this checkout (`skills/<name>`); there is no copy, manifest or
version file, and no `~/.agents/skills` copy. At 11:38Z the checkout was on
`gsd/phase-37-shared-runner-options-and-session-ids` (reflog: b3ca3e9 at 08:38 local);
`git diff --stat b3ca3e9 HEAD` and `git diff --stat main HEAD` over the three skill folders are empty, and
no branch changed `skills/ai-kit-spec-goal-prompt` after 2026-11-13. Latent risk: a symlinked install
follows whatever branch an executing agent checks out in this checkout.

Eval coverage:
- GSD project without the runner script: covered only as a direct `node .planning/scripts/cross-ai.mjs`
  config with the file removed (`tests/test_ai_kit_spec_goal_prompt_host.py:564-568`) and as a canned
  `problems` list in render tests (`_variants.py:461-477`, `_render.py:783-789`, `_golden.py:506-508`).
- Direct-CLI `cross_ai_command` with a `provider/model` id: NOT covered (the false positive above).
- `native_execution` true/false: covered for wording and warnings (`_variants.py`
  `test_native_execution_gives_no_readiness_warnings`, `_render.py`
  `test_native_execution_removes_the_readiness_lines`).
- Readiness warnings stay out of the file: covered. What the agent must do with a warning (hand off,
  not fork a second file): NOT covered; `evals/evals.json` has no case for it (its only readiness mention
  is the hand-off text of `precise-opengsd-range`, and its one fixture config uses the runner command).
- An agent that must continue after a missing runner, or an objective that creates the runner before
  the readiness rules: NOT covered.

Acceptance checks to add:
- Host test: `cross_ai_command = "opencode run --model router-env/my-coding"` with `opencode` on the fake
  PATH gives no "script missing" (and a non-vacuity case where a real `./x/run.sh` token is absent still
  does).
- Eval case reproducing the gitid stop: GSD fixture, direct-CLI command, no `.planning/scripts/`, owner
  asks for a pi runner; expected: one file, a hand-off naming curated-config `ensure-runner` (or the
  trimmed v2 plan), no second native file, no "would stop at its first step" fork.
- Render test: when the objective (or a setup step) creates the runner, the readiness rules are ordered
  after that step and no block says "stop" before it.
- An installed-version check (doctor or detect) that reports a symlinked install and the branch it
  points at, so a stale or mid-phase checkout is visible.

## Owner design rule: every instruction lives in the blocks

Owner words (2026-11-21, translated): "Any idea the agent needs must live in the blocks: block 1 and 2, or
only one if no more than one is needed." For this todo: the readiness ladder (ensure-runner, park, normal
mode) must be written inside every block that has `cross_ai: true` plans, not only in the shared `## Rails`
section after the markers or in the hand-off text; the gitid `/goal` block got its readiness rule only by a
hand edit (rendered file line 22). Full rule and checks: the sibling todo
`2026-11-21-point-the-goal-block-back-to-its-rendered-goal-file.md`. See also its section "Owner follow-up:
block layout and markers (captured 2026-11-21, design deferred)": dropping the copy markers and the
one-versus-two-block cases decide where this readiness ladder is written.
