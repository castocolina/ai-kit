---
created: 2026-11-21T13:04:12Z
title: Point the goal block back to its rendered goal file
area: skills
severity: minor  # suggested by capture agent, not confirmed by the owner
files:
  - skills/ai-kit-spec-goal-prompt/scripts/gp_render.py:422-444
  - skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py:81
  - skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py:232-243
  - skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py:328-367
  - skills/ai-kit-spec-goal-prompt/assets/prompt-template.md:1-24
  - skills/ai-kit-spec-goal-prompt/SKILL.md:145-155
  - .planning/goals/2026-11-16-phases-35-36-37-38-38-1-39.md:9-14
---

## Problem

Owner idea (translated from Spanish): when goal-prompt builds a goal that launches an autonomous run,
the short block the user copies must itself tell the agent to read the rest of the same file where
the goal was saved, so the whole idea is captured. Claude limits the characters of a goal, so the
copied block is small and the file holds the rest.

What exists today (read in the repo on 2026-11-21):

- The file template has the block between the markers and a shared `## Rails` section after them
  (`assets/prompt-template.md`, `=== FILE ===`; `gp_render.py:8` says non-inline blocks share `## Rails`).
- `goal`, `loop` and `plain` blocks already name the file: the `/goal` line says "Done when every DONE
  WHEN item in {path} section Rails holds" (`gp_sections.py:338-341`); loop and plain say "Continue the
  work described in {path} section Rails" (`gp_sections.py:345-346`, `349-354`).
- A `/goal` condition over 1,000 characters becomes the pointer form `/goal read document `{path}` at
  section `Full goal` ...` (`gp_render.py:101-105`, `410-412`, `439-442`; documented in
  `references/strategy-matrix.md:58-75`).
- An objective cut at the 200-character line cap ends with "(full text: {path} section Full objective)"
  (`gp_sections.py:81`, `232-243`).
- The autonomous block is the exception: `_one_block` renders `autonomous` from `BLOCK_INLINE` with the
  rails inline and no file path at all (`gp_render.py:424-427`). In the rendered file
  `.planning/goals/2026-11-16-phases-35-36-37-38-38-1-39.md` the block (lines 9-83) names its own file
  only in line 14, and only because the objective was cut. An uncut objective leaves no pointer to the
  file, so an agent in a fresh session cannot tell that a file holds more (here a `## Full objective`
  section, lines 87-92).
- Hand-off text says to paste the block and, for the pointer form only, that the file must stay at its
  printed path (`SKILL.md:149-152`).

Not verified: whether Claude follows a path pointer from a pasted `/gsd-autonomous` block; the pointer
form for `/goal` is itself still unverified (`SKILL.md:185`, and the open live check in
`.planning/todos/pending/2026-11-02-pending-live-checks-and-owner-decisions-from-v1.3.md:52-54`).

## Solution

Wanted: every block that has a rendered file behind it carries one rule line that names the file by its
repository-relative path and says to read it before the first step, including the sections that hold
text cut from the block (`Full objective`, `Full goal`, `Rails`). For the autonomous block the line goes
into the rule lines (for example under OBJECTIVE or ROLE), never onto the `/gsd-autonomous` first line
(`SKILL.md:165`: only `--from`, `--to`, `--only`, `--converge` may follow the command).

Acceptance checks a test can pin:
- Render an autonomous block with a short objective: the block contains the file's own final path
  (the unique path from `choose_path`) in a read-the-file line; the first line is unchanged flags only.
- Same for an objective that is cut: exactly one file pointer sentence, not two conflicting ones.
- The line fits `LINE_CAP` 200 and the block stays under `INLINE_CAP` 7000 and the 60 rule-line cap
  with a long repository-relative path (test with a deep `output_dir`).
- `goal`, `loop` and `plain` blocks keep their current pointers (goldens unchanged except where wanted).
- The render check (`gp_render.py:341-344` style) fails when the pointer names a path other than the
  file written, and a non-vacuity case proves it.
- Goldens under `tests/fixtures/goal_prompt/` are regenerated, not hand edited.

Where to change: `gp_sections.py` (`rail_sections` takes `path` already, `gp_sections.py:675-695`),
`gp_render.py` (`_one_block` autonomous branch, render-time check), tests
`tests/test_ai_kit_spec_goal_prompt_render.py`, `_golden.py`, `_objective.py`, `_skilltext.py`,
`_pointer.py`; docs `SKILL.md`, `README.md`, `references/strategy-matrix.md`, `references/worked-example.md`.
The repo requires tests and docs with the change and the skill-judge loop for any `SKILL.md` change
(AGENTS.md, rule on new or materially updated `SKILL.md`; at most three rounds, then the owner decides).

Risks and open questions:
- The file may be absent in the session that receives the paste (a different worktree, an uncommitted
  file, a deleted `tmp/` output for a free-text work set). The pointer should say what to do then
  (report and use the block alone), not stop.
- A path in the block is an extra line in a block already near its caps; check
  `.planning/ROADMAP.md` Phase 47.2 (it also edits `rail_sections`) so the two changes do not collide.
- `SKILL.md:166` says the paste block holds run instructions only: a pointer line is an instruction, a
  rationale for it is not.
- Decide whether the pointer is added for the inline `goal` form too (its `/goal` line already names
  the file, `gp_sections.py:339`, so probably not).

## Evidence from the gitid project (2026-11-21)

Transcript `~/.claude/projects/-var-home-bazzite-git-personal-gitid/b7185951-7d7e-4b13-89b2-350c6267edc8.jsonl`
(entries 11:15:39Z to 13:12:33Z; same session as the cross-AI todo). The rendered file is
`gitid/.planning/goals/2026-11-21-phases-09-8.md` (untracked, last written 10:12 local). No session ever
pasted or ran a block: every problem below is in how the goal-prompt agent built the blocks.

- Render for the owner's `/goal` request gave two blocks: Strategy 1 `goal` (recommended) and Strategy 2
  `autonomous`. The `/goal` line pointed at the handoff and at "section Rails" only. Owner (L4841,
  12:56:16Z, translated): "I see the goal, but instead of referencing the same file it goes only to the
  handoff and does not reference the rest of what the goal file has."
- The agent added "Obey every section of the goal file ... not only DONE WHEN" to the shared `objective`
  answer. Because one `objective` feeds every block, Strategy 2 still carries that sentence (current file
  line 55) although no file is named in that block: a dangling cross-block reference.
- Owner (L4929, 13:05:57Z, translated): the file should be "title, description, goal block, autonomous
  block, done; the rest is superfluous". The agent hand-trimmed `## Rails` and `## Full objective`
  (L4982, 13:07:04Z) and repointed `/goal` at "every DONE WHEN item of the Strategy 2 block in <file>"
  (L5031, 13:07:21Z): block 1 now depended on block 2.
- Owner (L5035, 13:11:07Z, translated): "the point is not that there are no rails or full objectives; the
  point is that if the agent needs it, it must be in the block." The agent then hand-wrote a
  self-contained block 1 (3,895 characters, file lines 9-46) and said (L5111, 13:12:33Z, translated) the
  renderer "cannot produce a /goal with rules inside: its only mode is the pointer to a section outside
  the block". Partly right: the inline form also points outside (`gp_sections.py:339`, "section Rails").
- Both edits break `SKILL.md:141` and `:162` ("Never edit the rendered file by hand"), forced by the
  renderer gap. Block 1 never passed the render checks; the agent's 4,000-character `/goal` cap and
  multi-line `/goal` acceptance are unverified.

## Owner design rule: every instruction lives in the blocks

Owner words (2026-11-21, translated): "Any idea the agent needs must live in the blocks: block 1 and 2, or
only one if no more than one is needed."

Rule: everything the agent needs to act sits inside the pasted block. The file is a reference for long
text (and for the human), never the only holder of an instruction. Render one block when one is enough,
two (block 1 and block 2) only when two are needed, and never a block that depends on text outside
itself, including the other block. This refines the Solution above: a "read the rest of the file" line
may stay as a pointer to optional detail, but it can no longer carry rules.

What it means for the current render (verified in the repo, 2026-11-21):
- `assets/prompt-template.md:1-12` puts `§§SHARED_RAILS` after the COPY TO HERE marker; `gp_render.py:7-8`
  says every non-autonomous block shares that `## Rails` section. So `goal`, `loop` and `plain` blocks
  hold no rules themselves: `goal_block` ends "Done when every DONE WHEN item in {path} section Rails
  holds" (`gp_sections.py:328-342`), loop and plain say "Continue the work described in {path} section
  Rails" (`gp_sections.py:345-354`).
- The pointer form moves the whole condition to `## Full goal` after the markers (`gp_render.py:101-105`,
  `410-412`, `438-442`), and `evals/evals.json` `precise-long-goal-pointer` (line 184-186) pins that form:
  it must be rewritten under this rule.
- A cut objective moves to `## Full objective` (`gp_sections.py:81`).
- Only the autonomous block carries its rails inline (`gp_render.py:424-427`, `BLOCK_INLINE`).
- One `objective` answer feeds every block, so block-specific wording leaks across blocks (gitid line 55).
- Unverified: whether a self-contained `/goal` block with full rails fits the host's `/goal` limit, and
  whether a multi-line `/goal` paste is taken whole; both need a live check before choosing between a
  condensed rail set for `goal` and dropping the `goal` block in favour of one autonomous block.

Acceptance checks a test could pin:
- Each rendered block, taken alone, contains every rule section its strategy needs (RULES, SAFETY, DONE
  WHEN, CLEANUP, STOP IF, REPORT or their condensed form); no block contains "section Rails", "section Full
  goal", "section Full objective", "Strategy 2" or "the other block" as the holder of a rule.
- A one-strategy render has exactly one fenced block between the markers; the number of blocks equals the
  number of strategies detect selected (ranked list after `dropped`).
- Text after COPY TO HERE is optional reference: deleting it leaves every block's rules unchanged (a
  render-time check, with a non-vacuity case).
- No sentence of the shared `objective` names something only one block has (for example "the goal file
  named at the end" in an autonomous block).
- Readiness rules inside a block are ordered after any objective step that creates the runner (ties to
  the cross-AI todo).

## Owner follow-up: block layout and markers (captured 2026-11-21, design deferred)

Owner points (2026-11-21, translated from Spanish). Capture only; nothing below is decided.
- With the rule that every instruction lives in the blocks, markers such as `▼▼▼ COPY FROM HERE ▼▼▼` and
  `▲▲▲ COPY TO HERE ▲▲▲` should lose their meaning and use.
- The skill should be clear about the cases: (1) a goal (the user asked for one explicitly, or the project
  is not GSD): one or two blocks, depending on the size of the resulting goal; (2) an autonomous run: one
  block, or two if that simplifies it; (3) the user asks for a goal that triggers an autonomous run (a goal
  block that launches the autonomous run); (4) depending on the runtime, an alternative to a `goal` may
  exist (for example a loop or a plain instruction block) and the layout should account for it.
- The owner only wants this captured. Design decisions can wait for a later review of the skill, unless it
  blocks work before phase 40.

### Where the markers are produced and what depends on them (read-only grep, 2026-11-21)

Paths below are under `skills/ai-kit-spec-goal-prompt/` unless they start with `tests/` or `.planning/`.
- Source of the markers: `scripts/gp_render.py:82-83` (`OPEN_MARKER`, `CLOSE_MARKER`) and
  `assets/prompt-template.md:6` and `:10` (the file template). The module docstring `gp_render.py:8` names
  the marker as the start of the shared `## Rails` section.
- Code that splits the file on the markers (`gp_render.py`): `:272-273` (`## Full goal` after the close
  marker), `:288-289` (shared `## Rails` after it), `:303-304` (prose before the open marker: at most three
  sentences and 15 percent of the file), `:349-350` (render check "copy markers not exactly once each");
  `:606` (a docstring only).
- Hand-off text that tells the user to paste "between the markers": `gp_render.py:119`, `:123`, `:130`
  (`PASTE_ONE`), `SKILL.md:149`, `references/worked-example.md:81`. The SKILL.md has no literal marker,
  only the phrase. Nothing in `evals/`, `README.md` (repo root) or the skill folder's other references
  names a marker (grep found no hit).
- Tests that name a marker or the phrase (counts of lines): `tests/test_ai_kit_spec_goal_prompt_render.py` 6
  (`:32`, `:150`, `:388-390`, `:734-735`; exactly-once check at `:734-735`),
  `tests/test_ai_kit_spec_goal_prompt_strategies.py` 3 (`:321`, `:353`, `:398`),
  `tests/test_ai_kit_spec_goal_prompt_pointer.py` 2 (`:254-255`),
  `tests/test_ai_kit_spec_goal_prompt_objective.py` 3 (`:114`, `:169-170`),
  `tests/test_ai_kit_spec_goal_prompt_golden.py` 1 (`:401`). These split on the marker, so they change with
  any replacement.
- Fixtures: `tests/fixtures/goal_prompt/golden/` 2 files (`opengsd-recommended.md`, `opengsd-goal-pointer.md`),
  one open and one close marker each (4 lines). Regenerated, not hand edited (see Solution).
- Rendered examples: `.planning/goals/` 5 files, one open and one close marker each (10 lines):
  `2026-10-14-v1.3-phases-16-27.md`, `2026-11-03-phases-28-29-29-1-30-30-1-30-2-31.md`,
  `2026-11-13-phases-33.md`, `2026-11-14-phases-32-5-33-34.md`,
  `2026-11-16-phases-35-36-37-38-38-1-39.md`. These are history; a new layout need not rewrite them.

### How strategies map to blocks today

- One block per strategy, recommended first, capped at three strategies (`gp_render.py:447-454`
  `build_blocks`; `references/strategy-matrix.md:16-17`). Block kinds are the strategy ids `autonomous`,
  `goal`, `loop`, `plain` (`_one_block`, `gp_render.py:422-444`).
- `autonomous`: template `BLOCK_INLINE`, first line flags only, rails inline in the block
  (`gp_render.py:424-427`). `goal`, `loop`, `plain`: template `BLOCK_PLAIN`; they point at the shared
  `## Rails` after the close marker (`gp_sections.py:328` `goal_block`, `:349` `plain_block`, `:357`
  `loop_block`). So today only the autonomous block is self-contained.
- Which strategy fires: `references/strategy-matrix.md:24-42` (M01 OpenGSD with no request or
  `autonomous` gives `autonomous`; M02/M03 give `goal` or `loop` on request, with `autonomous` behind it as
  M02b; M04-M07 and M11g/M11l for non-OpenGSD scopes; M09 fallback `plain`). A request for `autonomous` on a
  superpowers scope is dropped (`strategy-matrix.md:52-53`).
- `/goal` forms, as the skill states them (the skill's claim, not verified here): inline up to 1,000
  characters (`SKILL.md:109`, `GOAL_POINTER_THRESHOLD` `gp_render.py:88`); the renderer refuses an inline
  condition over 1,800 (`GOAL_BUDGET`, `gp_render.py:87`) or 4,000 code points (`GOAL_CAP`, `:86`;
  `strategy-matrix.md:62-63`, `SKILL.md:134`); a longer condition becomes the pointer form `/goal read
  document <path> at section Full goal ...` (`strategy-matrix.md:64-68`). `SKILL.md:191` says a
  4,000-character `/goal` is accepted and the 1,800 budget is a margin; `strategy-matrix.md:97-99` says no
  live run shows the host following the pointer form. The `autonomous` block's cap is `INLINE_CAP` 7000
  (`gp_render.py:95`).

### Runtimes with a goal-like primitive (`references/host-primitives.md`, labels as the file gives them)

- `claude`: `/goal` documented, version floor 2.1.139 (official docs); `/goal`, `/loop`, `CronCreate`,
  `ScheduleWakeup`, `RemoteTrigger` strings in the installed binary (binary strings); `/loop` is a bundled
  skill with no floor, read as `unverified` (`host-primitives.md:33-37`).
- `codex`: `/goal [<objective>|clear|edit|pause|resume]`, reverse-engineered syntax; `codex features list`
  printed `goals stable true`; detect still labels codex `unverified` when it is not the current host
  (`:38-41`).
- `opencode`, `pi`, `cursor` (binary `agent`): `--help` shows no goal, loop, schedule or cron keyword
  (live probe); community wrappers unchecked (`:42-48`). Every non-current host is `unverified` by rule.
  So for these three the equivalent of a `goal` today is a `loop` or `plain` block, not a goal primitive.

### Open questions for the later design discussion

- What replaces the markers so that a paste still copies exactly the instruction text? A fenced block
  already bounds the text; do the fences alone suffice, or does the render check need a new delimiter?
- How does the size rule pick one block versus two for a goal, and where does the split go? Which limit
  decides: the host's `/goal` limit (unverified in practice), `INLINE_CAP`, or the 60 rule-line cap?
- May block 2 ever depend on block 1 (for example block 1 sets the objective, block 2 holds rails)? The
  owner rule says no block depends on text outside itself; does "two blocks" then mean two alternatives
  (today's reading) or two parts of one run?
- Which block does a "goal that triggers an autonomous run" paste: a `/goal` whose text launches
  `/gsd-autonomous` with its flags, or the `/gsd-autonomous` block itself? Where do its rails live, given
  the `/gsd-autonomous` first line carries flags only (`SKILL.md:165`)?
- How does a runtime without a goal primitive (opencode, pi, cursor, unverified codex) get the equivalent:
  a `loop` block, a `plain` block, or an autonomous-style block with the rails inline? Who labels it
  unverified, and how does the file name the choice?
- Do goldens, the `.planning/goals/` history and the hand-off wording ("paste the block between the
  markers") get rewritten, or is the old format still read by `gp_render.py:272-289`-style splitters?
- Does case (2) with two blocks mean the second is a fallback for hosts that cannot take the first?

Acceptance checks a test could pin later (candidates only, not decided):
- The rendered file contains no `COPY FROM HERE` or `COPY TO HERE` text, and the hand-off text names the
  blocks (by heading or number) instead of "the markers".
- A render of each case (goal, autonomous, goal-that-launches-autonomous, no-goal runtime) holds the
  expected number of blocks: one for a small goal, two only above the chosen size rule.
- Each block, copied alone with its fences removed, equals the instruction text the agent needs (ties to
  the self-contained check above), and no block names another block.
- A runtime with no goal primitive renders a loop or plain block with the label from `host-primitives.md`
  (`unverified` where the file says so) and never a `/goal` line.
- The render check that today counts markers (`gp_render.py:349-350`) counts blocks or fences instead, with
  a non-vacuity case.

Scheduling: per ROADMAP.md no phase before 40 touches goal-prompt's blocks (phase 32.4 is done); the phases
that edit goal-prompt later are 47 (`rail_sections` header via the delegation playbook, ROADMAP.md:1089,
1094) and 47.2 (`rail_sections`, learned rails, ROADMAP.md:141, 1120-1123), so the design discussion fits
before 47.2; the standalone readiness-check bug fix (`gp_host.py:362-363`) does not depend on it.
