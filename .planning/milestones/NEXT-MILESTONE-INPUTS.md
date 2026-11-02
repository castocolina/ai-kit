# Inputs for the next milestone

Written 2026-11-02, after milestone v1.3 was closed. By the owner's direction, everything still open is
classified here and deferred; the next step is a new milestone made of these items plus topics the owner has
not shared yet. Nothing here is decided, started or approved: where an item says "owner", it needs a decision or
a live check that only the owner can give; "agents alone" means an agent can do it without asking.
Every item lives in a todo file (`.planning/todos/pending/`), in a backlog entry (`.planning/ROADMAP.md`,
section Backlog) or in a document named on the bullet; this file only classifies them. Sizes are guesses:
small (hours), medium (about a day), large (several plans).

Short names of the todo files used below:

- "live-checks todo" = `2026-11-02-pending-live-checks-and-owner-decisions-from-v1.3.md`
- "tooling todo" = `2026-11-02-tooling-defects-and-skill-writing-principle-found-at-the-v1.md`
- "refactor todo" = `2026-10-31-refactor-execute-gsd-and-rules-agents-sj-1-sj-3.md`

## Theme 1: Skill refactor and the skill-writing principle

Goal: make the big skills small and stable enough to pass a re-judge without a carried exception, following the
rule that a SKILL.md carries behaviour, not history.

- Refactor the execute-gsd skill and the project-rules-agents skill so a re-judge passes. The judge kept finding
  new detail in both; the rules-agents wording issue about an unattended restore was refuted, not fixed. Lives in:
  refactor todo. Size: large. Depends on: the playbook feasibility check below (it may change where the
  rules-agents content lives). Needs: agents alone to edit; the judges (referee-one and referee-two) to re-judge.
- Refactor the execute-superpowers skill: remove the alternative resume paths, keeping one pinned-resume path and
  one owner-stop path, then re-judge with the percent-based rubric and the spec sources embedded in the judge
  prompt (the old prompt embedded only the SKILL.md). Lives in: refactor todo (section on this skill). Size:
  large. Depends on: nothing; the lite-or-strong executor feature depends on it. Needs: agents alone; owner only
  if the percent bar is questioned.
- Audit seven skills for version numbers, dates and observation history in the main flow (session-wake,
  execute-gsd, execute-superpowers, cross-ai, spec-review, curated-config, the rules family) and move provenance
  to a trailing section or an evidence reference; keep short `unverified` tags. Lives in: tooling todo (section
  on the writing principle). Size: medium. Depends on: do it together with the two refactors above to avoid
  editing twice. Needs: agents alone.
- Possible project rule: one line in `AGENTS.md` stating that a SKILL.md describes behaviour and provenance lives
  in a trailing section. Lives in: tooling todo (proposal, not applied). Size: small. Depends on: nothing. Needs:
  owner (it is a rule change).
- Evaluate one skill with event-keyed playbooks (new project, new worktree, phase finished, worktree closed,
  subagent delegated, quota error) instead of seven sibling rules checkers; a feasibility check comes first and
  its result may be "keep the siblings". Lives in: backlog 999.16 (event-keyed playbook skill). Size: medium for
  the check, large if it is built. Depends on: the rules-agents refactor decision. Needs: owner (the verdict).
- Older skills without machine-readable evals (24 skills have only markdown evals): migrate each to an evals
  file when it is next judged. Lives in: live-checks todo, decision on the Phase 27 proposals (part a). Size:
  large across all skills, small each. Depends on: the percent-based judge needing evals in each changed skill.
  Needs: owner to accept the proposal; agents alone for the migration.
- Two shipped skill files name planning paths that moved with the archive (the Laya backend note of the
  jev skill and the execute-superpowers text about the Node requirement); preferred fix is to rewrite the
  sentences so they no longer point into a planning folder. Lives in: live-checks todo. Size: small. Depends
  on: the writing-principle audit (same files). Needs: agents alone once the owner confirms the preferred fix.
- Re-judge the execute-superpowers skill because its package changed after its last judged round (a dead
  link fix); the verdict reads stale. Lives in: live-checks todo. Size: small. Depends on: the
  execute-superpowers refactor (re-judge there). Needs: agents alone.

## Theme 2: Tooling and runner defects

Goal: fix the concrete defects found in real runs and at the v1.3 close, without changing the owner's policy.

- Error bodies seen in real runs with no row in the runner's error catalogue (provider not configured, policy
  budget exceeded 429, data inspection failed 400, context length exceeded 400, the Zhipu plan-not-open code,
  and the 502/503 connection-capacity body). Lives in: tooling todo. Size: medium. Depends on: nothing.
  Needs: agents alone.
- Flip five catalogue rows that have real evidence now but are still marked unverified (a Zhipu row, the
  monthly limit, insufficient funds, model access disabled, model cooldown); model cooldown lasted from 2
  minutes to over 2 hours, so its transient class needs a look. It changes behaviour and the pinned template.
  Lives in: tooling todo. Size: medium. Depends on: the error-row item above (same data). Needs: agents alone;
  owner if the cooldown class changes.
- Match router errors on the wording the router logs actually contain ("all N active accounts cooling down for
  model X") because its full error bodies live only in its database. Lives in: tooling todo (fix-up idea).
  Size: medium. Depends on: error-row items. Needs: owner (decide whether to match on log wording).
- The Claude matcher in the runner reads stderr only; if a usage limit is printed on stdout the lane is
  classified as a crash without a class. Lives in: tooling todo. Size: small. Depends on: the live check of the
  limit channel (needs a real limit). Needs: owner indirectly (waits for a real limit), then agents alone.
- The stop-failure hook of the session-wake skill does not record its payload; a small opt-in capture hook that
  writes field names and a redacted payload is needed to learn the real body of the next Claude usage limit.
  Lives in: tooling todo. Size: small. Depends on: nothing; the three live checks on the next real limit depend
  on it. Needs: agents alone to build; the limit itself cannot be forced.
- The installer does not place the wake and cross-ai skills into pi although setup marks them for pi (29
  skills seen in a live pi session, none of those). Find out why. Lives in: tooling todo. Size: medium.
  Depends on: nothing. Needs: agents alone (a live pi listing is available through herdr).
- Pi exports only `PI_CODING_AGENT`; the Phase 22 interactive guide expects `PI_PROVIDER` and `PI_MODEL`, which
  do not exist. Lives in: tooling todo. Size: small. Depends on: nothing. Needs: agents alone.
- The edge-floor check on the Phase 25.1 spec returns not-ok (floor 48 rows, table 47; the encoding case is
  missing). Lives in: tooling todo. Size: small. Depends on: nothing. Needs: agents alone.
- The goal-prompt detect command reads its output as JSON only; real GSD workflows use file indirection for
  large outputs. Lives in: tooling todo. Size: small. Depends on: the matching live check on a large roadmap.
  Needs: agents alone.
- Stale docstring in `skills/ai-kit-spec-review/ai_kit_spec/routing.py` ("until Phases 20-22"). Lives in:
  tooling todo. Size: small. Depends on: nothing. Needs: agents alone.
- The end-to-end test of a checkout without git fails when the temporary directory sits inside a git
  repository; build the folder outside any repository or make the code tolerate it. Lives in: live-checks
  todo. Size: small. Depends on: nothing. Needs: agents alone.
- Runtime lists copied by hand (runner-capable list, host list, host-binary map, plan-editor error text) have no
  test comparing them with the runtime table. Lives in: tooling todo (added at this classification, from the v1.3
  audit). Size: small. Depends on: nothing. Needs: agents alone.
- The project `AGENTS.md` links a gitignored file (`.claude/cli-environment.md`), so the link dangles in a
  clean checkout. Lives in: tooling todo (added, from the v1.3 audit). Size: small. Depends on: nothing. Needs:
  owner (track the file or drop the link).
- One goal-prompt test passes only from a short checkout path because of another test of the tool-substitution
  hook. Lives in: tooling todo (added, from the close handoff). Size: small. Depends on: nothing. Needs: agents
  alone.

## Theme 3: Runner, hooks and config-path improvements

Goal: harden the machinery that already exists (cross-AI runner, session hooks, config paths) with items captured
as backlog.

- Idle watchdog for the cross-AI runner: kill the child's process group after N seconds without output, using
  the existing exit vocabulary. Lives in: backlog 999.5 (idle watchdog). Size: medium. Depends on: nothing; the
  runner cleanup touches the same file. Needs: agents alone (the safe default for slow models is a design
  choice to confirm).
- Runner and adapter cleanup found by the Phase 25 reviews (one shared "confirmed router" rule, a quota-cycle
  class, calling gsd-core's skill block builder, dead state, moving the 3,300-line self-test out of rendered
  copies, restoring the user's lower timeout on cleanup). Lives in: backlog 999.12 (runner and adapter cleanup).
  Size: large. Depends on: the idle watchdog is easier after it. Needs: agents alone.
- Register `workflow.cross_ai_retry` with gsd-core so `config-set` accepts it instead of hand-editing the
  config. Lives in: backlog 999.13 (register the retry key). Size: medium. Depends on: research into gsd-core
  capability manifests and the consent gate. Needs: agents alone; owner for the global-versus-project scope.
- Cursor hooks path ignores `CURSOR_CONFIG_DIR`: the CLI always reads user hooks from `~/.cursor/hooks.json`.
  Lives in: backlog 999.2 (Cursor hooks path). Size: small. Depends on: re-verifying against current Cursor
  docs. Needs: agents alone.
- Polish of the spec-and-discuss chain skill (forced local answer matching no table row, commit counting, analyzer
  start timing, session record on early stop, late trigger keywords, action on missing client). Lives in:
  backlog 999.11 (spec-discuss polish). Size: medium. Depends on: nothing. Needs: agents alone; judges after.
- Make the session hooks dynamic: worktree and new-checkout indexing advice (codegraph, graphify), install-relative
  doc paths in the model context too, and compaction metrics (window size and duration). Lives in: todo
  `2026-10-24-make-the-ai-kit-session-hooks-dynamic-worktree-indexing-advi.md`. Size: medium. Depends on: per-host
  research (which hosts expose a post-compact event). Needs: agents alone.

## Theme 4: Notifications and platform parity

Goal: make the desktop notice of the session-wake skill trustworthy, readable and available on macOS.

- Check the paths before notifying: say what was checked (host, session id, store location, state file) and send
  the notice only when the situation is real; a missing store path gets its own text. Lives in: tooling todo
  (desktop notices section). Size: small. Depends on: nothing. Needs: agents alone.
- Make the notice readable: host, shortened session id, reason, the journal command to read the full line, with
  an urgency and an expire time long enough to read. Lives in: tooling todo. Size: small. Depends on: the path
  check. Needs: agents alone.
- macOS parity: the same notice with the same checks and best-effort rule, plus a launchd equivalent of the
  persistent wake or an explicit "unsupported host" refusal at arm time; macOS behaviour stays labelled
  unverified until run on a Mac. Lives in: tooling todo. Size: medium. Depends on: the two items above. Needs:
  owner (choose launchd or refusal; a Mac is needed to verify).
- Tests for the notices: a fake notifier per platform and a test that a missing store path produces the
  path-specific text. Lives in: tooling todo. Size: small. Depends on: the items above. Needs: agents alone.

## Theme 5: Live checks only a real session can answer

Goal: close the live checks that no log or unit test can answer. All live in the live-checks todo (group 1). Use
herdr windows, never real config files, and kill spawned windows afterwards. Sub-grouped by what they need.

Waiting for something agents cannot force:

- Next real Claude usage limit: what the stop-failure hook receives, and whether the resumed headless run exits.
  Size: small once the capture hook exists. Depends on: the capture hook (Theme 2). Needs: owner (wait for a real
  limit).
- Channel of the usage limit under `claude -p` (stdout or stderr). Size: small. Depends on: the same real limit.
  Needs: owner (wait for a real limit).
- Reboot survival of the persistent wake and of desktop notices. Size: small. Depends on: nothing. Needs: owner
  (a reboot with linger on).
- Cursor status line after logging in to Cursor (one payload, one quota response, the wired line). Size: small.
  Depends on: nothing. Needs: owner (a Cursor login).
- Phase 21.2 PreCompact live delivery and measurement. Size: medium. Depends on: a logged-in host. Needs:
  owner (login).
- Phase 21.3 advisory-hook live matrix on opencode. Size: medium. Depends on: a logged-in opencode. Needs:
  owner (login).
- Phase 16 acceptance scenario in a real interactive codex session. Size: small. Depends on: nothing. Needs:
  owner (secondary runtime, interactive codex).
- Phase 22 optional live steering arms for pi. Size: small. Depends on: nothing. Needs: owner (optional).

Agents can run them with herdr and a scratch home:

- A real resume of a session by the wake (throwaway real session, one tiny model call). Size: small. Depends
  on: nothing. Needs: agents alone.
- A one-shot wake firing while GSD asks retry, skip or abort (record whether it interrupts or waits). Size:
  medium. Depends on: nothing. Needs: agents alone.
- Long-goal pointer form accepted by a real Claude session. Size: small. Depends on: nothing. Needs: agents
  alone.
- Wording of native execution in the OpenGSD runner rule, rendered with native true and false in a real run.
  Size: medium. Depends on: nothing. Needs: agents alone.
- Done-when wording against a real end-to-end run in a scratch OpenGSD project. Size: medium. Depends on:
  nothing. Needs: agents alone.
- Quota-checked task on the runner's one listed CLI. Size: small. Depends on: nothing. Needs: agents alone.
- Phase 24 chain with no decision backend installed, on a fixture project. Size: medium. Depends on: nothing.
  Needs: agents alone.
- Pi model-name grammar against copied stored configs (list every id that no longer parses). Size: small.
  Depends on: nothing. Needs: agents alone.
- Background-host permission mode, once per primary runtime, headless. Size: small. Depends on: nothing. Needs:
  agents alone.
- Launch-and-wait patterns for opencode and pi. Size: small. Depends on: nothing. Needs: agents alone.
- Goal-prompt detection output on a large roadmap (file indirection). Size: small. Depends on: the matching
  defect in Theme 2. Needs: agents alone.

Conditional (only if the stack or route is ever used):

- Parallel-test forms for jest, cargo and Gradle. Size: small each. Depends on: using those stacks. Needs:
  agents alone.
- Router error body through codex. Size: small. Depends on: codex being routed. Needs: agents alone.

## Theme 6: Owner decisions waiting

Goal: the questions the owner has not answered. They are copied from the live-checks todo (group 2) with their
defaults; none is decided.

- Should the project's `AGENTS.md` adopt the three workflow rules the rules-agents skill checks (arm the session
  wake before a multi-plan run; a pointer to the verified cross-ai runner; the CPU share for parallel tests)?
  Options: all three; only the runner pointer now (the earlier recommendation); none. Default: not edited.
  Lives in: live-checks todo. Size: small. Depends on: the wake being verified live. Needs: owner.
- Should pi install the goal-prompt skill? Options: add it to the pi list, or leave it out. Default: left out.
  Lives in: live-checks todo. Size: small. Depends on: nothing. Needs: owner.
- Re-baseline the skill-judge base score of older skills to their current percent? Options: keep old bases (the
  config skill reads 99 against 105 and stays unresolved) or set each base to the current percent. Also covers the
  goal-prompt pass bar (94.4 and 87.2 percent from two judges against a 90.4 base). Default: old bases stay.
  Lives in: live-checks todo. Size: small. Depends on: nothing. Needs: owner.
- Phase 20 open points: how many fix rounds count against the judge cap (default accepted as recorded), and the 29
  opencode compact agents that carry no model line (default: nothing, the smokes report it). Lives in:
  live-checks todo. Size: small. Depends on: nothing. Needs: owner.
- Phase 21.1 numbers: keep Laya advisory only at accuracy 0.5 against the 0.95 floor (default) or calibrate it;
  keep the opencode judge lane at 11 of 15 without a re-judge (default) or re-judge. Lives in: live-checks todo.
  Size: small, or medium if calibrating. Depends on: nothing. Needs: owner.
- Should the five remaining refusal cases of the goal-prompt render (long lists and commands over the
  200-character line cap) stay refusals or be wrapped over several lines? Default: they stay refusals. Lives in:
  live-checks todo. Size: small. Depends on: nothing. Needs: owner.
- Should the secret-shape scanner be widened beyond two key shapes, and its four copies shared? Options: widen and
  share one copy, widen each copy, or leave as is. Default: two shapes, four copies. Lives in: live-checks todo.
  Size: medium. Depends on: nothing. Needs: owner.
- Should the remaining fixed time limits in the runner template (60 s and 30 s) be raised, scaled with host load,
  or left? Default: they stay. Lives in: live-checks todo. Size: small to medium. Depends on: nothing. Needs:
  owner.
- What to do with the Phase 27 proposals: (a) record the markdown-only evals as refactor debt, (b) the Windows
  ledger entry 7 (the autonomous block names an unverified primitive in its heading only; waive with a reason or
  add an `unverified` sentence below the flags-only first line; it blocks the ship step while enforcement is on),
  (c) plan-template defects seen in execution, (d) executor oddities. Default: all stay proposals. Lives in:
  live-checks todo and `.planning/WINDOWS.md` entry 7. Size: small each. Depends on: nothing. Needs: owner.

## Theme 7: Features

Goal: new capabilities already captured as backlog or todo.

- Install ai-kit skills as real copies through the `skills` CLI instead of symlinks, with install, remove and
  sync across pi, cursor, copilot, codex, opencode and claude; the CLI's subcommands and flags are unverified
  and must be checked live first. Lives in: backlog 999.14 (real copies through the skills CLI). It was named the
  next feature after v1.3. Size: large. Depends on: a live check of the CLI; the setup's atomic-write and
  scratch-home rules. Needs: owner for the migration policy; agents alone otherwise.
- Config doctor reachable from the setup wizard (reuse the existing engine and screen; no second
  implementation). Lives in: backlog 999.1 (config doctor in the wizard). Size: medium. Depends on: nothing
  (the status-line step it was to coordinate with already shipped). Needs: agents alone, with a real wizard run.
- Cursor project-level subagent linking: link the shipped pinned Cursor subagents per file into a project's
  `.cursor/agents`, and confirm one run as non-fast in the Cursor usage dashboard. Lives in: backlog 999.7
  (Cursor subagent linking) and the Cursor subagents todo
  `2026-10-13-add-cursor-subagents-pinned-to-non-fast-composer-2-5-and-grok.md`. Size: medium. Depends on:
  nothing. Needs: owner (the dashboard check; Cursor is a secondary runtime).
- Lite or strong executor choice for the execute skills, decided by asking the jev-fast-decision skill as a
  black box, requested by the llm-env project; reference patches there must be re-made against the current main.
  Lives in: backlog 999.17 (lite or strong executor choice). Size: large. Depends on: the execute-gsd and
  execute-superpowers refactors; a GSD-first waiver note. Needs: owner (waiver note, gates).
- A cross-AI chain skill that bundles the execute and review script with its calling convention, retry ladder,
  coverage gates and result classifier. Lives in: backlog 999.15 (cross-AI chain skill) and its lessons file under
  `.planning/phases/999.15-cross-ai-chain-skill-for-execute-and-review-runs/`. Size: large. Depends on: the
  lane-table unification below. Needs: owner (design choices); agents alone for the build.
- Unify the review and execute lane table, with effort support detected per model, optional runtime and model
  escalation (off by default), and optional jev classification of input and output behind an on/off knob. Lives
  in: todo `2026-10-29-unify-review-execute-lane-toml-effort-escalation-and-jev-classification.md`. Size: large
  (a spike on effort per runtime comes first). Depends on: nothing; it must respect the "never switch harness on
  failure" rule. Needs: owner (table shape, escalation policy).
- Optional status-line segment showing the memory used by the cursor-agent process. Lives in: live-checks
  todo (owner idea). Size: small. Depends on: nothing. Needs: owner (default: not built).

## Theme 8: Decision-system (jev-fast-decision) work

Goal: finish the parts of the decision-skill family that v1.3 left as backlog or todo.

- Image and box questions for the jev client (one image, several compared, bounding box), after a spike against
  TypeSafe direct. Lives in: backlog 999.8 (jev image and box questions). Size: medium. Depends on: a TypeSafe
  key and consent. Needs: owner (key and consent).
- Backend detection and selection by host (Laya first with a configurable URL and a first-run question, TypeSafe
  from the environment, the free tier only under opencode with its provider). Lives in: backlog 999.9 (backend
  selection by host). Size: medium. Depends on: nothing. Needs: owner (a Zen answer is partly recorded; confirm).
- TypeSafe key sources: make the home-file fallback strictly last, document environment inheritance for long-lived
  terminal multiplexers, remove the fallback once agents inherit the environment. Lives in: backlog 999.10 (key
  sources). Size: small. Depends on: backend selection above. Needs: owner (when to remove the fallback).
- Cross-host discovery wiring: add a short marker block about the jev skill (triggers, activation line, probe,
  never-when-no-backend) to the four global instruction files, and credential guidance for non-interactive shells.
  The skill is already in pi's listing; a read-only check on 2026-11-02 found no mention of it in the global
  instruction files. Lives in: todo `2026-10-14-wire-jev-fast-decision-cross-host-discovery-scaffolding.md`. Size:
  medium. Depends on: the installer being the delivery path (real-copy feature). Needs: owner (it edits the
  owner's global files through ai-kit's atomic writers).

## Theme 9: Housekeeping

Goal: close or tidy things that look finished or are only clutter. All of these are suggestions for the owner; none
is done.

- Todos that look delivered by v1.3 phases and may be closed, keeping any remaining piece in the item named:
  the System One decision-skill plan todo (delivered as the jev client in Phase 21.1; remaining pieces are
  backlog 999.8 to 999.10), the atomic decision-system skills todo (marked promoted to Phase 21.1), the PreCompact
  todo (marked promoted to Phase 21.2; its live steps are in Theme 5), the tool-advisory hooks todo (marked
  promoted to Phase 21.3), the todo about promoting the Cursor status line proof of concept (Phase 23 delivered the
  real status line; the owner left it open on purpose), and the quota-schedule and goal-prompt todo (delivered by
  Phases 25.1, 26 and 27; its `AGENTS.md` part is the first decision in Theme 6, so it duplicates that decision).
  Lives in: `.planning/todos/pending/` and the pending list in `.planning/STATE.md`. Size: small. Depends on:
  the owner's confirmation per todo. Needs: owner.
- The two June branches (external status-line segments, loop polish): the live-checks todo says they sit on the
  GitHub remote, but a live listing on 2026-11-02 shows the remote has only main, so they survive as local archive
  tags; the open question is only whether to port the idea onto the split status line or drop it. Lives in:
  live-checks todo. Size: small to medium if ported. Depends on: nothing. Needs: owner.
- The GitLab remote still holds two old branches (installer registry work and an old copy of the v1.3 branch) that
  were never compared by content; compare before deleting anything when GitLab is used again. Lives in:
  live-checks todo. Size: small. Depends on: GitLab access working. Needs: owner (access and consent).
- Local tags: 22 exist. Two archive tags are named as no longer needed (the single-commit agent worktree summary and
  the already-merged rate-burn fix); the Cursor proof of concept and host-split spec tags wait for the memory-segment
  idea; five older tags (two backups, two pre-compaction references, one pre-curl-fix) are not discussed anywhere.
  Lives in: live-checks todo (the first two sets only). Size: small. Depends on: the memory-segment decision. Needs:
  owner (deleting tags).
- The local tag for v1.3 is not on the GitHub remote (a live listing shows no tags there). Lives in: live-checks
  todo (added at this classification). Size: small. Depends on: nothing. Needs: owner (pushing needs consent).
- Stale wording and stale verification files left in archived v1.3 documents (no-backend criterion, Phase 24 spec
  lines, verification files of Phases 24 and 25). Lives in: live-checks todo (added at this classification, from
  the v1.3 audit). Size: small. Depends on: nothing. Needs: owner (amend, or leave as history).
- Codex interactive confirmation of the runtime-detection labels (codex is secondary; the headless evidence stands).
  Lives in: backlog 999.6 (Codex interactive confirmation). Size: small. Depends on: nothing. Needs: owner
  (deferred by the owner's decision of 2026-10-18).

## Topics the owner will bring

These are not shared yet. Nothing is listed here on purpose; the owner will bring them in the discussion that
comes before the milestone is started.

## Suggested order and why

This is a suggestion for the discussion, not a decision.

- Start with Theme 1 (skill refactor): the lite-or-strong executor feature, the cross-AI chain skill and the
  rules-family playbook idea all build on it, and the writing principle is cheaper to apply once.
- Small agent-only fixes in Themes 2 and 4 can run in parallel with it because they touch different files.
- Add the opt-in capture hook early (Theme 2) so the next real Claude usage limit answers three live checks
  without anyone watching.
- Real copies through the skills CLI (Theme 7) was named the next feature; it needs one live check of the CLI
  before planning.
- Theme 6 decisions are quick to take in one sitting and unblock several items (pi list, rules in `AGENTS.md`,
  judge bases), so they fit at the start of the discussion.

## How to start

1. Discuss the owner's own topics first and add them to the section above.
2. Review this file with the owner and settle the Theme 6 decisions and the Theme 9 closures.
3. Run `/gsd-new-milestone` and give it this file (`.planning/milestones/NEXT-MILESTONE-INPUTS.md`) as the input for the
   milestone goals; it updates `PROJECT.md` and routes to requirements.
4. Promote the chosen backlog entries with `/gsd-review-backlog`.
5. Check the planning tree: `node .claude/gsd-core/bin/gsd-tools.cjs validate health`.
