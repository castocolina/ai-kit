---
created: 2026-11-02T16:00:00.000Z
title: Pending live checks and owner decisions from v1.3
area: verification
severity: minor
files:
  - .planning/milestones/v1.3-OWNER-FOLLOWUP.md
  - .planning/milestones/v1.3-phases/25-quota-aware-cross-ai-subprocess-supervision/25-OWNER-CAPTURES.md
  - .planning/milestones/v1.3-phases/25.1-configurable-cross-ai-retry-ladder-and-upstream-error-propag/25.1-OWNER-CAPTURES.md
  - .planning/milestones/v1.3-phases/26-session-self-resume-and-opengsd-quota-rules/26-OWNER-CAPTURES.md
  - .planning/milestones/v1.3-phases/27-one-shot-goal-and-loop-prompt-skill/27-OWNER-CAPTURES.md
---

## Problem

Owner direction of 2026-11-02: nothing from the v1.3 close may stay a floating question in a document.
Every live check and every owner decision that was still open lives here, in plain words. This todo
stays open until the owner says otherwise. Nothing below is decided or done; no skill or code is changed
by this todo. History and the closed items stay in `.planning/milestones/v1.3-OWNER-FOLLOWUP.md`.

Related and not duplicated here: the tooling defects and skill-writing principle todo
(`2026-11-02-tooling-defects-and-skill-writing-principle-found-at-the-v1.md`, which also holds the
desktop-notice work, the stop-failure hook that does not record its payload, and the Claude matcher that
reads stderr only), the skill refactor todo (`2026-10-31-refactor-execute-gsd-and-rules-agents-sj-1-sj-3.md`),
backlog 999.6 (Codex interactive confirmation) and backlog 999.16 and 999.17.

## Solution

### Group 1: live checks still to do

Use herdr windows where a second terminal helps, never real config files, and kill any window or process
spawned for a check once it is done. Each item says what it is, why it is open, and the exact next step.

- [ ] Next real Claude usage limit: what the stop-failure hook receives, and whether the resumed headless
  run exits. Open because a real limit cannot be forced and the hook does not record its payload today.
  Next step: add the small opt-in capture hook from the tooling defects todo, wait for a real limit, read
  the recorded field names and whether the host process id reaches the hook, then let the armed wake fire
  and read its journal to see whether the headless resumed run (`claude -p --resume`) exits or hangs while
  the limit is still active.
- [ ] Channel of the Claude usage limit under `claude -p` (stdout or stderr). Open because the runner reads
  stderr only. Next step: at the same real limit, capture where the "Overloaded" and "resets <time> (<zone>)"
  wordings arrive; if stdout, fix the matcher (tracked in the tooling defects todo).
- [ ] Reboot survival of the persistent wake and desktop notices after a reboot. Open because only the
  lifecycle without a reboot was run. Next step: arm a throwaway wake with user linger on, reboot, read the
  user journal for the fire, and note whether a notice appears when no graphical login exists yet.
- [ ] A real resume of a session by the wake. Open because only a throwaway "session not found" give-up was
  seen. Next step: arm from a throwaway real session, let it fire, and check that the session continues.
- [x] *(done in Phase 30.2: the live Cursor run in 30.2-VERIFICATION)* Cursor status line once logged in to Cursor. Open because the check stopped at the login screen on
  2026-11-02. Next step: log in, then capture one status-line payload, one quota response and the wired status
  line in a live `agent` session, and flip the matching unverified flags. *(amended 2026-11-03, 30.2 D-08: the
  live status-line check is Phase 30.2's verification, from its branch tip; closes with it)*
- [ ] Long-goal pointer form in a real Claude session. Open because only the length rule was read from the
  binary. Next step: with one tiny model call driven through herdr, type the generated `/goal` pointer and
  read whether the host accepts it.
- [ ] Wording of native execution in the OpenGSD runner rule. Open because it was only unit-tested. Next
  step: render once with native execution true and once false in a real OpenGSD cross-AI run and read the
  runner rule text in both.
- [ ] A one-shot wake firing while GSD asks retry, skip or abort. Open because no recorded disposition exists
  for what the wake does then. Next step: arm a one-shot wake, trigger the GSD prompt in a scratch project,
  let the wake fire, and record whether it interrupts or waits.
- [ ] Pi model-name grammar check against this machine's stored configs. Open because the grammar was
  narrowed and stored configs with bare pi or opencode ids may now be refused. Next step: run the config
  loader over the stored (copied, not real) configs and list every id that no longer parses.
- [ ] Background-host permission mode. Open because the default is `unknown`. Next step: run a headless
  background host once per primary runtime and read which permission mode it reports.
- [ ] Parallel-test forms for jest, cargo and Gradle. Open only if those stacks are ever used here; they were
  written from docs, not run. Next step (conditional): run each form once in a scratch project of that stack
  and record the exit code and worker count, then flip the unverified flag on that table entry.
- [ ] Phase 21.2 PreCompact live delivery and measurement. Open because the spike steps that need a live
  compaction were staged, not run; the hook stays off and every verdict reads `unmeasured`. Next step: run
  the staged spike steps against a logged-in host, then run the measurement and record saving versus baseline.
- [ ] Phase 21.3 advisory-hook live matrix on opencode. Open because the matrix rows and the opencode spike
  were never run live (Claude and pi are seen working). Next step: run the live matrix rows and the opencode
  spike from the Phase 21.3 live kit and record each row.
- [ ] Pending Phase 16 acceptance scenario. Open because the one scenario needs a real interactive codex
  session (optionally pi). Next step: run `detect-current-runtime` inside that session as the scenario says
  and mark the scenario in `16-UAT.md`.
- [ ] Phase 24 no-backend chain scenario. Open because the chain ran for two of three scenarios on
  2026-10-24 and the no-backend one is covered only by a unit test. Next step: run the spec/discuss chain on
  a fixture project with no decision backend installed and record the result.
- [ ] Quota-checked task on the runner's one listed CLI. Open because it was only simulated. Next step: run
  one small task through the goal-prompt runner and read its status line.
- [ ] Done-when wording against a real end-to-end run. Open because only the parse was simulated. Next step:
  paste a generated goal block into a scratch OpenGSD project and check that the run ends only when the
  end-to-end test count is above zero.
- [ ] Launch-and-wait patterns for opencode and pi. Open because they were written from docs. Next step: run
  each foreground wait once and record the result.
- [ ] Router error body through codex. Open and conditional: only if codex is ever routed. Next step: capture
  one live router error and read the `cross-ai: upstream` lines.
- [ ] Phase 22 optional live steering arms for pi. Open as optional. Next step: run the three optional arms
  from the Phase 22 interactive kit and record each.
- [ ] Goal-prompt detection output on a large roadmap (`--gsd-cmd` reading `@file:` indirection). Tracked as a
  defect in the tooling defects todo; the live check is to run the roadmap query on a large roadmap and see
  whether the output arrives inline. *(code half done in Phase 31, 31-SPEC R11: the `@file:` reader; only the
  live check is left)*

### Group 2: decisions the owner still has to take

None of these is taken. Each shows the options and what happens if nothing changes.

- [ ] Should the project's own `AGENTS.md` adopt the three workflow rules the rules-agents skill checks?
  The rules are: (1) the main agent arms the session wake before a multi-plan run (self-resume by session id
  at the reset time plus 60 s when known, else hourly; disarmed when the run ends); (2) a pointer to the
  verified cross-ai runner (`.planning/scripts/cross-ai.mjs`, read its last status line and the cross-ai
  skill before acting, never switch harness on its own); (3) the CPU share for parallel tests (use a share
  of the available CPUs, never a hardcoded worker count). Options: adopt all three; adopt only the runner
  pointer now and wait on the wake rule until the wake is verified live (the earlier recommendation); adopt
  none. Default if nothing changes: the checker reports the wake and runner rules as missing and the
  parallel-test rule as present, and `AGENTS.md` is not edited.
- [ ] Should pi install the goal-prompt skill? Pi has no goal primitive. Options: add
  `ai-kit-spec-goal-prompt` to the pi skill list, or leave it out. Default: left out.
- [ ] Should the skill-judge base score of each older skill be re-baselined to its current percent? Options:
  keep the old base score as the bar (the config skill reads 99 against a base of 105, unresolved), or set
  each base to the current percent so only regressions count. Default: old bases stay and those verdicts stay
  unresolved. This also covers the unresolved config-skill verdict and the pass bar of
  `ai-kit-spec-goal-prompt` (94.4% and 87.2% from two judges against a 90.4 base: accept the result, or lower
  the base). *(folded 2026-11-07 into Phase 32, needs owner confirmation: the baseline verdict becomes each judged
  skill's base for the batch phases' regression check; the older bases, such as spec-config's 105 and
  goal-prompt's 90.4, are history (JDG-01))*
- [ ] Phase 20 open points. (a) How many fix rounds count against the skill-judge cap (two of two rounds plus
  one voluntary edit): accept the accounting or change the counting rule; default accepted as recorded.
  (b) The 29 opencode compact agents carry no model line: file an upstream report or document the limit in
  the skill docs; default nothing, the smokes report it and do not fail.
- [ ] Phase 21.1 numbers. (a) Laya answered at accuracy 0.5 against the 0.95 floor: keep Laya advisory only
  (default), or calibrate and raise it. (b) The opencode judge lane scored 11 of 15: keep without a re-judge
  (default), or re-judge.
- [ ] Should the five remaining refusal cases of the goal-prompt render be cut or stay refusals? They are
  long lists (phase numbers, plan files) and commands (an e2e command, the runner command) that exceed the
  200-character line cap. Options: keep refusing (a cut list would hide work from the run) or wrap the list
  over several rule lines. Default: they stay refusals.
- [ ] Should the secret-shape scanner be widened beyond two key shapes? It checks an API-key-shaped token
  and a GitHub-token-shaped token, and exists in four separate copies. Options: widen the set and share one
  copy, widen each copy, or leave as is. Default: two shapes, four copies.
- [ ] Should the fixed time limits in the runner template be raised? Two end-to-end modules failed once under
  load (the template self-test with a 300 s budget, since raised to 900 s; the matrix and runner steps still
  keep fixed 60 s and 30 s budgets that a stalled, swapping host can exceed). Options: raise the remaining
  budgets, make them scale with host load, or leave them. Default: the remaining fixed budgets stay.
- [ ] What to do with the Phase 27 proposals left open: (a) older skills' markdown-only evals as refactor
  debt (24 skills have no `evals/evals.json`; propose recording it in the skill refactor todo and migrating
  each skill when next judged); (b) the Windows-compatibility entry 7 (`.planning/WINDOWS.md`, the autonomous
  block names an unverified primitive in its heading only; options: waive with a reason, or add an
  `unverified` sentence below the flags-only first line, which is the earlier recommendation; it blocks the
  ship step while enforcement is on); (c) plan-template defects seen during execution (a pyright check that
  trips on a version banner, clean-tree checks that ignore the owner's config file, a progress counter
  mismatch); (d) executor oddities (agent-branch allow-list applied unevenly, architecture test left red by
  one executor). Default: all stay proposals, nothing applied.
- [ ] Two old unmerged branches were kept on purpose at the v1.3 close (a live listing of the GitHub remote on
  2026-11-02 shows only the main branch now, so they survive only as local archive tags; the wording that
  follows is the original one): the one named
  external segments for the status line (4 commits of June 2026: provider discovery, header parser, output
  sanitization and execution with a time-limited cache; it only touches the old single-file status line that
  Phase 23 split) and the one named loop polish (1 commit of June 2026: a branch icon and an install flag for the
  branch). Decide for each: port the idea onto the current split status line, or drop it. Default: both stay on
  the remote untouched, and each is also preserved locally by an archive tag.
- [x] *(done in Phase 30.2, D-02: the segment is built; its live value is still unverified)* Optional idea left by
  the old Cursor proof of concept: a status line segment that shows the memory used by the
  cursor-agent process (today only the external system-memory example exists for both hosts). Cursor is a
  secondary runtime. Default: not built. *(amended 2026-11-03, 30.2 D-02: decided, built in Phase 30.2)*
- [x] *(done 2026-11-07: Phase 30.2 delivered it, D-11; the todo moved to completed/)* The todo about promoting the
  Cursor status line proof of concept (dated 2026-10-12) looks obsolete because
  Phase 23 delivered the real Cursor status line. It was left open on purpose; decide whether to close it.
  *(amended 2026-11-03, 30.2 D-11: not obsolete — Phase 30.2 resolves it; it closes, and the proof-of-concept
  branch and tag are deleted after owner confirmation, when 30.2's verification closes)*
- [ ] The GitLab remote still holds two old branches (the installer registry work and an old copy of the v1.3
  branch) that were not compared by content because GitLab is skipped for now. Compare them by content before
  deleting anything there when GitLab is used again. Default: untouched.
- [ ] Archive tags kept locally after the branch clean-up: two are no longer needed (the single-commit agent
  worktree summary and the already-merged rate-burn fix) and could be deleted; the Cursor proof of concept and
  the host-split spec tags are kept until the Cursor memory idea above is decided.
- [ ] After the phase directories were archived (milestones/v1.3-phases), two shipped skill files still name a moved
  path: the Laya backend note of the jev skill (it points at the Phase 21.1 evaluation results file) and the
  execute-superpowers skill text (it points at the Phase 18.1 research file for the Node requirement). Either
  edit the two paths to the archive location, or rewrite the sentences so they no longer depend on a planning
  path (preferred: shipped skill text should not point into a planning folder). Skills were left untouched on
  purpose at the close. *(folded 2026-11-07 into Phase 32, 32-SPEC R9: both sentences are rewritten without a
  planning path, and a test keeps planning pointers out of every shipped skill Markdown file)*
- [ ] The skill-judge evidence of Phase 26 for the execute-superpowers skill is stale: the package changed after its
  last judged round because the audit fixed a dead link in one of its references (a link depth, no behaviour).
  The checker therefore reports a stale verdict for that skill (the Phase 27 checker is fine). The verdict is
  already deferred to the skill refactor; re-judge it there and the evidence becomes current again. *(folded
  2026-11-07 into Phase 32: the baseline re-judges every judged skill on its current text, execute-superpowers
  included)*
- [x] *(done in Phase 28-03, GATE-03: the no-git e2e case passes with TMPDIR inside a git work tree)* The
  end-to-end test that checks a checkout without git fails when the temporary directory sits inside a git
  repository (it only passes with the system temporary directory). Make the test build its temporary folder
  outside any repository, or have the code under test tolerate it.
- [ ] The local tag for v1.3 exists, but the GitHub remote has no tags. Decide whether to push the tag
  (pushing needs the owner's consent). Default: the tag stays local.
- [ ] Stale wording and stale evidence left in archived v1.3 documents: the roadmap success criterion for the
  no-backend case, the matching requirement and two lines of the Phase 24 spec still describe the ladder before
  the decision-skill rework; the verification files of Phases 24 and 25 predate later fixes and read stale.
  Options: amend the wording and re-run verification for both, or leave the archive as history. Default: left
  as is (found by the v1.3 audit).
