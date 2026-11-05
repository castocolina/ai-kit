# Goal prompt: phases 16, 16.1, 17

The recommended block is one /goal condition that stops when DONE WHEN holds. Paste one block between the markers into a fresh session in this repository.

▼▼▼ COPY FROM HERE ▼▼▼

## Strategy 1 (recommended): goal

````
/goal read document `.planning/goals/2026-01-02-phases-16-16-1-17.md` at section `Full goal` and finish only when that section's DONE WHEN conditions hold
````

## Strategy 2: autonomous

````
/gsd-autonomous --from 16 --to 17 --converge

OBJECTIVE
- Finish phases 16, 16.1, 17, each verified. Then leave the repository clean.
- Ship phases 16 to 17 with the curated config checks green, keep every migration reversible, and leave a short n... (full text: .planning/goals/2026-01-02-phases-16-16-1-17.md section Full objective)

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
- Pre-commit hooks always run on every commit; fix a real failure at its root, never skip it.

ORDER
- Phases in numeric order: 16, 16.1, 17.
- No SPEC (spec, then discuss, then plan): 17.
- Plans already exist (execute them; the plan checker still runs): 16, 16.1, 17.
- Already verified (verify only): 16.
- Existing plans missing cross_ai: true (add it, then execute): 16.1, 17.

QUOTA
- A. This session (its own quota): before the first plan, arm the ai-kit-session-wake skill, a self-resume by session id at the host-reported reset when known, else hourly.
   Run its done step when the run ends. Only this orchestrator arms or disarms it.
   Wake primitive on this host: systemd user timer.
- B. Cross-AI children (a child CLI hits its limit): follow the ai-kit-cross-ai skill. The runner cross-ai.mjs owns the retry ladder and never switches CLI, provider or model.
   Read its last AIKIT-XAI status line before acting.
   A quota stop whose AIKIT-XAI line has a whole-number retry_after_s: wait that exact time once (one one-shot job, never a fixed-interval re-check), then re-invoke the same lane.
   Check the working tree and resume only the unfinished work. After stopped=hard-waits or stopped=cap schedule nothing more.
   A quota stop without retry_after_s is an owner stop: report the evidence and stop. Whether this host can run a one-shot job is unverified.
   Runner: node .planning/scripts/cross-ai.mjs (usability unverified).

DECISIONS
- Verifiable questions: check and fix them directly; do not ask.
- Gray areas: ask the jev-fast-decision skill and follow its SKILL.md. Advisory only: on needs_fallback or no answer you decide; verify before acting. Prefer the best design over the easiest.
- Never pause for questions or UAT. Put a blocking item in the ledger and continue.
- Never remove existing features.

SAFETY
- Never touch the real ~/.claude, ~/.cursor, ~/.config/opencode, ~/.codex, ~/.pi or ~/.gsd; use a scratch HOME.
- Never print secrets. Never push. Never stage everything blindly.
- Pre-commit hooks and every test tier always run; no step may skip one.

DONE WHEN
- Print each command with its exact exit code, its count line and the last 20 lines of output, ANSI codes stripped.
- Gates first: make test-unit.
- E2E: `make e2e-test` exits 0 and prints a test count above zero. Exit 0 with a zero count is not green.
- Zero-count markers: read the count line yourself.
- Print the paths of the screenshots or TUI text snapshots the e2e run produced.
- Start each long-lived e2e process in its own process group and record its group id in tmp/. After the run kill those groups and print a process listing (ps) that shows none remain.
- Phase status: VERIFICATION shows passed for every phase in scope, or the item is listed as human verification with its reason.
- Unit tests alone never count as done.

CLEANUP
- Leave no stray files: commit, ignore or remove each.
- Remove the backlog entries and directories of finished work; list the rest.
- Merge the working branch into the main checkout; never push.
- Archive unmerged work of every intermediate worktree as a tag, then remove the worktree and its branch; remove this worktree last.

STOP IF
- The same failure repeats 3 times with no progress.
- Stop after 120 turns and report.
- A decision blocks other work and nothing resolves it.
- A step needs a real config write, a login or sudo.
- Every cross-AI candidate for a role is unusable.
- In each case park the item, continue independent work, then report.

REPORT
- Per item: status, verification, the evidence printed, the cross-AI CLI used.
- The ledger of your decisions, the commits made, nothing pushed.
- The advisory closeness check was omitted: no usable backend.
````

▲▲▲ COPY TO HERE ▲▲▲

## Rails

OBJECTIVE
- Finish phases 16, 16.1, 17, each verified. Then leave the repository clean.
- Ship phases 16 to 17 with the curated config checks green, keep every migration reversible, and leave a short n... (full text: .planning/goals/2026-01-02-phases-16-16-1-17.md section Full objective)

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
- Pre-commit hooks always run on every commit; fix a real failure at its root, never skip it.

ORDER
- Phases in numeric order: 16, 16.1, 17.
- No SPEC (spec, then discuss, then plan): 17.
- Plans already exist (execute them; the plan checker still runs): 16, 16.1, 17.
- Already verified (verify only): 16.
- Existing plans missing cross_ai: true (add it, then execute): 16.1, 17.

QUOTA
- A. This session (its own quota): before the first plan, arm the ai-kit-session-wake skill, a self-resume by session id at the host-reported reset when known, else hourly.
   Run its done step when the run ends. Only this orchestrator arms or disarms it.
   Wake primitive on this host: systemd user timer.
- B. Cross-AI children (a child CLI hits its limit): follow the ai-kit-cross-ai skill. The runner cross-ai.mjs owns the retry ladder and never switches CLI, provider or model.
   Read its last AIKIT-XAI status line before acting.
   A quota stop whose AIKIT-XAI line has a whole-number retry_after_s: wait that exact time once (one one-shot job, never a fixed-interval re-check), then re-invoke the same lane.
   Check the working tree and resume only the unfinished work. After stopped=hard-waits or stopped=cap schedule nothing more.
   A quota stop without retry_after_s is an owner stop: report the evidence and stop. Whether this host can run a one-shot job is unverified.
   Runner: node .planning/scripts/cross-ai.mjs (usability unverified).

DECISIONS
- Verifiable questions: check and fix them directly; do not ask.
- Gray areas: ask the jev-fast-decision skill and follow its SKILL.md. Advisory only: on needs_fallback or no answer you decide; verify before acting. Prefer the best design over the easiest.
- Never pause for questions or UAT. Put a blocking item in the ledger and continue.
- Never remove existing features.

SAFETY
- Never touch the real ~/.claude, ~/.cursor, ~/.config/opencode, ~/.codex, ~/.pi or ~/.gsd; use a scratch HOME.
- Never print secrets. Never push. Never stage everything blindly.
- Pre-commit hooks and every test tier always run; no step may skip one.

DONE WHEN
- Print each command with its exact exit code, its count line and the last 20 lines of output, ANSI codes stripped.
- Gates first: make test-unit.
- E2E: `make e2e-test` exits 0 and prints a test count above zero. Exit 0 with a zero count is not green.
- Zero-count markers: read the count line yourself.
- Print the paths of the screenshots or TUI text snapshots the e2e run produced.
- Start each long-lived e2e process in its own process group and record its group id in tmp/. After the run kill those groups and print a process listing (ps) that shows none remain.
- Phase status: VERIFICATION shows passed for every phase in scope, or the item is listed as human verification with its reason.
- Unit tests alone never count as done.

CLEANUP
- Leave no stray files: commit, ignore or remove each.
- Remove the backlog entries and directories of finished work; list the rest.
- Merge the working branch into the main checkout; never push.
- Archive unmerged work of every intermediate worktree as a tag, then remove the worktree and its branch; remove this worktree last.

STOP IF
- The same failure repeats 3 times with no progress.
- Stop after 120 turns and report.
- A decision blocks other work and nothing resolves it.
- A step needs a real config write, a login or sudo.
- Every cross-AI candidate for a role is unusable.
- In each case park the item, continue independent work, then report.

REPORT
- Per item: status, verification, the evidence printed, the cross-AI CLI used.
- The ledger of your decisions, the commits made, nothing pushed.
- The advisory closeness check was omitted: no usable backend.

## Full objective

Ship phases 16 to 17 with the curated config checks green, keep every migration reversible, and
leave a short note per phase on what changed and why. Ship phases 16 to 17 with the curated config
checks green, keep every migration reversible, and leave a short note per phase on what changed and
why. Ship phases 16 to 17 with the curated config checks green, keep every migration reversible, and
leave a short note per phase on what changed and why. Ship phases 16 to 17 with the curated config
checks green, keep every migration reversible, and leave a short note per phase on what changed and
why. Ship phases 16 to 17 with the curated config checks green, keep every migration reversible, and
leave a short note per phase on what changed and why. Ship phases 16 to 17 with the curated config
checks green, keep every migration reversible, and leave a short note per phase on what changed and
why. Ship phases 16 to 17 with the curated config checks green, keep every migration reversible, and
leave a short note per phase on what changed and why. Ship phases 16 to 17 with the curated config
checks green, keep every migration reversible, and leave a short note per phase on what changed and
why.

## Full goal

Finish phases 16, 16.1, 17, each verified. Then leave the repository clean. Ship phases 16 to 17
with the curated config checks green, keep every migration reversible, and leave a short note per
phase on what changed and why. Ship phases 16 to 17 with the curated config checks green, keep every
migration reversible, and leave a short note per phase on what changed and why. Ship phases 16 to 17
with the curated config checks green, keep every migration reversible, and leave a short note per
phase on what changed and why. Ship phases 16 to 17 with the curated config checks green, keep every
migration reversible, and leave a short note per phase on what changed and why. Ship phases 16 to 17
with the curated config checks green, keep every migration reversible, and leave a short note per
phase on what changed and why. Ship phases 16 to 17 with the curated config checks green, keep every
migration reversible, and leave a short note per phase on what changed and why. Ship phases 16 to 17
with the curated config checks green, keep every migration reversible, and leave a short note per
phase on what changed and why. Ship phases 16 to 17 with the curated config checks green, keep every
migration reversible, and leave a short note per phase on what changed and why. Done when every DONE
WHEN item in .planning/goals/2026-01-02-phases-16-16-1-17.md section Rails holds, with the exit code
and count line of every command printed. Unit tests alone never count as done. If it does not hold,
stop and report after 120 turns.
