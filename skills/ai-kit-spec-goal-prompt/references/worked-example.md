# Worked example: one OpenGSD run

One complete pass, from the four answers to the hand-off, as a shape to copy.

Load when: you want to see a whole run, or to check the golden excerpt before you quote it.

## The four answers

1. Work set: phases 16, 16.1 and 17.
2. Target host: `claude`, the current host.
3. Native execution: no.
4. Mockups: none.

The answers file holds `"work_set": {"kind": "phases", "numbers": ["16", "16.1", "17"]}`, the
`target_host`, `"native_execution": false`, `"mockups": []`, and `"strategy": null`, because the user
asked for no particular strategy.

## Detect, read back

The facts below come from a real read-only detect run on this repository (work set `phases:27`).
The golden fixture uses a fake GSD seam, so its own facts come from the test instead:

- Scope: `opengsd`, with identity `opengsd`.
- E2E: the `make e2e-test` and `make e2e-docker` commands (detected), and a PTY driver (inferred).
- Primitives on `claude`: `/goal` is `available` (official docs). `ScheduleWakeup` and the other
  tool rows are `available` only when their names are in `--tools`, else `not seen`. `/loop` is
  `unverified`.
- Derived: `must_outlive` is true (three phases); `provable` is true (an e2e command exists and
  there are no mockups).

## The strategy chosen

An OpenGSD scope with no request fires row M01. The result has one strategy, `autonomous`,
recommended, with the reason "OpenGSD scope: /gsd-autonomous with --from/--to/--only and
--converge". It has no `/goal` condition, so render reports no condition lengths.

## The paste block (excerpt)

The first 24 lines of the block, copied from `tests/fixtures/goal_prompt/golden/opengsd-recommended.md`
(golden lines 10 to 33). The rest of the block, from ORDER to REPORT, is in that file:

```
/gsd-autonomous --from 16 --to 17 --converge

OBJECTIVE
- Finish phases 16, 16.1, 17, each verified. Then leave the repository clean.
- Ship phases 16 to 17 with the curated config checks green.

ROLE
- You are the orchestrator: the session that received this prompt. Dispatch plan work to subagents, reusing one or starting a fresh one, as you judge best.
- Verify every result yourself; never accept a reported pass.

RULES FOR EVERY PLAN
- Every PLAN.md frontmatter carries cross_ai: true, so GSD delegates it to cross-AI.
- First step, before any execution: confirm .planning/config.json enables workflow.cross_ai_execution and sets workflow.cross_ai_command.
- Then confirm the runner script exists, that its argv listing names at least one installed CLI, and that every default reviewer CLI is installed.
- These checks prove installation only, never quota or auth. If any check fails, stop and report what to fix.
- Reviewers come from .planning/config.json. Probe each one once before the first review. Record any failure; never substitute a model.
- Read AGENTS.md first, then each phase SPEC and CONTEXT. Their decisions are locked; never re-discuss them.
- Read a skill only when the task needs it. Candidate skills: ai-kit-gsd-spec-discuss, ai-kit-session-wake.

ORDER
- Phases in numeric order: 16, 16.1, 17.
- No SPEC (spec, then discuss, then plan): 17.
- Plans already exist (execute them; the plan checker still runs): 16, 16.1, 17.
- Already verified (verify only): 16.
```

## Render relay

- Path: the file is `<date>-<slug>.md` in the output directory. A `phases:27` run wrote
  `<date>-phases-27.md` into a scratch directory (observed). The default directory, `.planning/goals`
  on OpenGSD, is read from the code and was not run here.
- Conditions: none.
- Warnings: only readiness problems, such as a missing runner or reviewer. They are printed, never
  written into the file.

## Hand off

Give the path, then say why: "This repository is an OpenGSD project, so the run uses
`/gsd-autonomous` with convergence." Tell the user to paste the block between the markers into a
new session at the repository root. Offer to commit the file. Then stop.

## A superpowers run, in prose

The user names two plan files under `docs/superpowers/plans`, with the work set `plans:<a>,<b>`.
Detect finds no `.planning/` project, so the scope is `superpowers`. The plans are restricted to the
two named files and ordered by their dependencies.

- If the user asks for `autonomous`, the request is dropped with the reason that `/gsd-autonomous`
  needs a GSD phases work set. Nothing is emitted for it.
- If the host has a `goal` primitive that reads `available`, and the work is provable, row M04 fires
  and the file gets a `/goal` block. Render prints the condition's length in characters and
  `goal_form`. An inline condition over 1,800 characters or 4,000 code points is refused; a
  condition over 1,000 characters becomes the pointer form instead (see the strategy matrix).
- If the work must outlive the session and a loop primitive is available, rows M06 or M07 fire
  instead. The file is then a loop prompt, and its label carries whatever the primitive table says.

## A long goal, in the pointer form

The user asked for `strategy: "goal"` with a long `objective` (about 1,000 characters or more).
With `goal_style` left at `auto`, render prints `"goal_form": "pointer"`. The first block line is a
short pointer to the file's own section, copied from the committed pointer golden:

```
/goal read document `.planning/goals/2026-01-02-phases-16-16-1-17.md` at section `Full goal` and finish only when that section's DONE WHEN conditions hold
```

The file ends with a `## Full goal` section that holds the whole condition, wrapped at about 100
columns. Tell the user the file must stay at that path, and that whether the host follows the
pointer is unverified.
