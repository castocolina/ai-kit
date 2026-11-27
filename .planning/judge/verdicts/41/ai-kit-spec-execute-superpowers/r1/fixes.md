# Loop 41 round 1 fixes: ai-kit-spec-execute-superpowers

Decide row: `next-round` (4 critical, important or high findings: referee-one 4, referee-two 0, the
Opus substitute for referee-three 0). With more than 3 such findings the three-round rule applies, so round 2 judges
the fixed text.

- referee-one D8-1 (high, `references/state-management.md:215`, also 181-182): both state-write blocks now check
  `write-resumable-state`'s exit status and stop with an error before printing `RESUME_STATE_PATH=`; a sentence says a
  failed write saved nothing, so no wake is scheduled or re-armed, and the Write state step skips Schedule-or-stop on
  that exit. Files: skills/ai-kit-spec-execute-superpowers/references/state-management.md,
  skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md.
- referee-one D8-2 (high, `references/quota-wake.md:45`): an unchanged task digest now keeps the task identity, not the
  CLI session; sandboxed codex exec has no resume form (ai-kit-cross-ai SKILL.md, runner `sameSessionArgv`), so the wake
  re-dispatches in a fresh codex session and continuity is claimed only from the runner's `session` line. The same
  claim in the Compose step was corrected. Files: references/quota-wake.md, references/dispatch-external-cli.md.
- referee-one D8-3 (high, `references/fold-step.md:51`): the no-change promise is gone; on a refused checkpoint or ready
  the agent names the failed stage and checks the local tip, `fold.py show --plan` (recorded state and PR number) and
  the remote branch and PR state read-only before reporting what completed (fold skill unit-contract: steps before a
  refusal stay done). The start step's identical promise was corrected too. Files: references/fold-step.md,
  references/start-step.md.
- referee-one D8-4 (high, `SKILL.md:35`): both mentions now keep the `--next` prohibition for its real reason (it
  rewrites the current unit's brief as `unit: next`) and state that `boundary` takes `--repo`, defaulting to the
  current directory (`fold.py boundary --help`). File: skills/ai-kit-spec-execute-superpowers/SKILL.md.
- referee-one D7-1 and the Opus substitute D7-1 (medium, `evals/evals.json:187`): the scripted executor-fallback answer
  carries `"exclude": ["execute-primary"]`, and a new assertion checks that resolve-injection receives that list as
  `--escalation-excluded-keys-json` with `--no-fallback`. File: skills/ai-kit-spec-execute-superpowers/evals/evals.json.
- the Opus substitute D8-3 (medium, `SKILL.md:207`): a restored round of 4 or more with no pinned `injection_json` goes
  to escalation.md's resolve block; rounds 1-3 or a pinned injection dispatch through Step 3 unchanged. File: SKILL.md.
- the Opus substitute D8-1 and referee-one D8-5 (medium, `SKILL.md:290`, `SKILL.md:271`): Node 24 is stated as ai-kit's
  tested floor, separate from GSD's declared floor, which the agent reads live with `npm view @opengsd/gsd-core engines`;
  no version or date in the text. File: SKILL.md.
- the Opus substitute D8-2 and referee-one D8-6 (medium, `SKILL.md:267`): the official Codex page is named as where the
  workspace-write writable roots and protected paths are defined (Evidence and design notes), and a task that must
  commit checks the lane's effective policy first, stopping for the owner when Git metadata is read-only. Files:
  SKILL.md, references/design-notes.md.
- referee-one D5-2 (medium, `SKILL.md:101`): the config-check load rule names three triggers (before the start step;
  block 3 in session-model mode; the notice line when closing such a run) in SKILL.md and in the reference. Files:
  SKILL.md, references/config-check.md.

Not done in this round (the fixer's 30-minute time box ran out after the required fixes; round 2 judges them again): the description rewrite (referee-one D4-1), the
body moves (the Opus substitute D5-1), the shared host-config audit reference (referee-one D5-1) and the pre-dispatch
write-boundary rule for full-permission lanes (referee-one D6-1).

Tests before commit (text-only change, no test edited): `bash tmp/judge-41/fix_tests.sh`: 22/22 modules passed.
