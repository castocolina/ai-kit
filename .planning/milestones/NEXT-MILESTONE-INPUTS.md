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

The full research reports behind these rounds (one file per question, including the project-rules playbook
design `28-project-rules-playbook-design.md`) are in `.planning/research/2026-11-02-next-milestone/`.

Shared in rounds before the milestone starts. Each topic states the owner's wish, then the facts already
checked against the code, the open-gsd docs (`next` branch) and the local GSD install. Decisions marked
"for jev" are settled through the decision ladder during discussion, preferring the best design over the easy
one and resilience over speed. Memory entries that a decision contradicts are cleaned as each one is decided.

### Decisions by skill (summary of rounds 1-5; details and evidence in the rounds below)

**Every skill**
- Re-judged early with the new judge (two judges chosen from what the environment offers, native opus xhigh as
  fallback); decimal batch phases improve groups of skills; evals and tests become part of each skill.
- A committed `dist/` without tests and evals; README install via plugin and `npx skills`; setup syncs the
  selected hosts headless through `npx skills` (shared code vendored or installed as a group).
- Each skill's scripts are used by that skill; orphaned scripts are adopted, merged or deleted.
- Every skill that classifies uses jev-fast-decision, as a black box, and still works when jev is absent.
- Skill text is behaviour, not history; no hardcoded referee names; rtk appears nowhere.
- A clean per-host list of skills (and MCP servers where possible), passed to each subprocess, subagent or
  agent window by role (the 2026-10-13 design, revived).

**`ai-kit-gsd-curated-config`**
- Fetch open-gsd docs at the installed version's tag, cached per version under `.aikit/`; report and offer a
  local update only when the changelog makes it worth it, labelled by impact.
- Grouped questions in a cascade: MVP, UI, granularity beside MVP (our rule), runtime (Claude preferred; ask
  when another host is detected), base branch detected from the merge flow.
- `balanced` profile, dynamic routing on, `tier_models`, per-agent models and effort classified with jev from
  agents.md; every write through the project's own `gsd-tools`, effort values validated.
- Never remove settings it did not plan. UI phase and review only for UI projects; cross-AI execution asks
  for confirmation; English `response_language`; AGENTS.md for `claude_md_path` (confirm otherwise); branch per
  phase; intel on; graph refresh our own choice.
- Assign skills to GSD agents by responsibility from the skills actually available (ponytail family,
  reducing-entropy, naming-analyzer, impeccable for UI, others), not a fixed table alone.
- Fix: stop writing `review.effort.opencode = "high"` (breaks opencode 2.x).

**`ai-kit-gsd-spec-discuss`**
- Always SPEC.md, CONTEXT.md and the discussion log for a batch of phases, jev in both modes.
- Default interactive (spec asks; discuss `--analyze --all --batch`); `--auto` decides automatically in
  assumptions mode (never the literal `--assumptions` flag) and prepares the autonomous run built by
  goal-prompt, which stops only on a blocker.

**`ai-kit-spec-config`**
- The hub every `ai-kit-spec-*` skill chains to when no config exists; callers fail clearly when it is missing.
- Owns discovery across claude, opencode, pi, cursor, codex and copilot, and the model catalog (models.dev,
  Artificial Analysis, Arena ELO; tiers by effort, class, cost, modalities, strengths; source and usability
  state per model; cache times); jev ranks, the user picks.
- Writes a TOML that separates reviewers from executors, each with priorities, effort per model and opt-in
  runtime and model escalation flags; flags stale entries (such as removed models).
- Takes over the useful pieces of `ai-kit-opencode-providers`.
- Fix: the cheap-execution ranking depends on Artificial Analysis indexes that are now null.

**`ai-kit-spec-review`** (with checklist and fixer)
- Iterates and uses jev where possible; chains spec-config; uses the review lanes with resilient fallback and
  switching per the user's preferences (today one failing lane ends the review).
- Chains lens skills when available (ponytail planning or review skills, reducing-entropy, naming-analyzer,
  simplify, impeccable for UI) through the prompt guidance, or as a post-approval pass for file-editing ones.
- Lanes get a capability block built from the real argv (tools verified present, read-only or write) and
  per-task skills (by path, or inlined for hosts that cannot load them).

**`ai-kit-spec-execute` and `ai-kit-spec-execute-superpowers`**
- Superpowers only for now; GSD plans are handed back to GSD's own execute.
- After implementation, chain superpowers' `requesting-code-review` and iterate in ai-kit's own capped loop
  until it passes, with the same review models and lanes; jev classifies gray areas before the user is asked;
  lens skills help when the model must decide.
- Lane transport per lane: subprocess, resumed session or herdr pane, reused per plan and renewed after N
  rounds (spike first).

**Shared runner (`cross-ai.mjs`, `ai-kit-cross-ai`)**
- One runner for open-gsd cross-AI and ai-kit review/execute, taking runtime, provider/model and effort,
  with opt-in escalation flags; session ids in and out; capability block per lane; copilot's "not available"
  error classified; a test that keeps the template and the rendered copy in sync.

**Removed:** `ai-kit-spec-execute-gsd`, `ai-kit-opencode-providers`, `mermaid-audit`.

**`jev-fast-decision`:** a black box with its own fallback ladder; whether it leaves ai-kit and which backends
it keeps is a later discussion; its calibration script gets documented.

**Still to discuss:** the project-rules skills (next round), goal-prompt, session-wake, usage-metrics and the
general skills.

### Round 6 (2026-11-02): project-rules baseline, before the owner's wishes

Checked (read-only; checkers run on ai-kit itself with the GSD step off):
- Seven skills, all `check|remediate [repo_root]` printing JSON (fix list, findings waiting on per-stack
  research, rules whose condition could not be proven). Only the agents checker edits (through the external
  `/agent-md-refactor` or directly); the rest report; rules-all runs the six as subprocesses. Five stacks from
  marker files (Python, Node, Go, Java Maven/Gradle, Rust); CI reads GitHub Actions and GitLab CI only.
- Old-rubric scores only (agents 93 accepted fail, all 102, arch 100, the other three 103); no evals anywhere.
- New defects: the docker description is 1,092 characters (spec cap 1,024); agents, cicd and docker
  descriptions have an unquoted `: ` (strict YAML and `npx skills` reject them); the CI checker never follows
  GitLab `include:`, so it sees almost nothing of ai-kit's include-built `.gitlab-ci.yml`; the research cache
  goes stale after 30 days in code but 180 in the design spec.
- ai-kit fails its own rules 11 times: five missing `validate-*` aliases, no help path for an unknown target,
  one recipe too long, two Makefile targets without a matching pre-commit hook, no duplicate-code tool, and the
  arch test cannot be checked because `make arch-test` goes through the parallel runner.
- House rules (20, in `ai_kit_project_rules_agents/rules.py`): the rtk rule is stale; three rules apply only to
  GSD projects (cross-AI plan rules, arming session wake, the cross-AI runner pointer); one SKILL.md example names
  Claude Code's `Agent` tool; the September todo's long guidance for codegraph, graphify and process leaks was
  cut to one sentence each.
- Recorded already: backlog 999.16 (one skill with event-keyed playbooks), the rules-agents refactor todo, the
  history-out-of-skills todo, the live-checks todo's open decision on ai-kit adopting the session-wake, runner
  and CPU-share rules. The todo `2026-10-14-agents-md-quota-schedule-rules-and-goal-prompt-skill.md` is still
  pending although Phases 26 and 27 delivered it: close it.
- History: the September request was one wrapper skill with 17 rules; the 2026-09-12 design split it into six
  checkers plus the orchestrator (v1.2, Phases 9-15); no deferred ideas recorded; the one explicit cut was real
  layering enforcement in the arch checker.
- Copy installs break all seven (the shared library is never installed; the orchestrator finds siblings only
  in the same folder; the GSD check needs two other ai-kit skills), so the family installs as a group even after
  vendoring.

### Round 7 (2026-11-02): project rules become one skill of event playbooks and host hooks

**Hooks as knobs per host.** Claude Code has many hook events (https://code.claude.com/docs/en/hooks); ai-kit
already built some (the advisory hooks). They become setup knobs per host, whether the host runs directly or
an agent raises it through herdr as a window, subagent or subprocess, and the owner can see which are enabled
in each environment. A hook says what happens on an event or development stage: at session start; on worktree
creation (run `make setup-dev`, `setup-docker`...); at the end of a phase, plan or task (destroy the worktree,
compact commits per phase, plan or task depending on the framework, run a local or AWS e2e check, wait for CI
and read automated review feedback, stay in a receive-PR-review loop that evaluates and sends fixes or
feedback), and many more.

Checked 2026-11-02 (docs; only a git `post-checkout` probe was run):
- Claude Code: 35 events, 5 hook types; settings and plugin hooks also run inside subagents; under `claude -p`
  the folder counts as trusted, so repo hooks run unprompted; in a worktree `CLAUDE_PROJECT_DIR` still points
  at the original root (the worktree is in the input's `cwd`). `WorktreeCreate` replaces creation (the hook
  must create it and print the path) and fires only for worktrees Claude makes. `StopFailure` has a
  `rate_limit` matcher but no documented reset-time field. `TaskCompleted` is Claude's own task list, not GSD
  phases. Background hooks with `asyncRewake` can wake an idle session.
- Codex hooks mirror Claude's events but each needs trust approval first; Copilot CLI also runs a repo's
  `.claude/settings*.json` hooks; pi 1.3.0 has `session_start` (ai-kit's README calling it a gap may be stale).
  No host has a phase, plan, CI or PR-review event. The host-neutral "worktree created" signal is git's
  `post-checkout` hook (runs in the new worktree with an all-zero previous commit; tested).
- ai-kit ships six hooks (session briefing, tool advisor, tool reminder, decision probe, precompact, session
  wake) in a registry at `tools/setup.py`, toggled per hook and host for the user (`--with-hooks`, `--hooks`,
  the wizard). Missing: per-project and per-event settings, per launch mode (direct, herdr, subagent,
  subprocess), any Codex hook, and any report of which hooks are enabled (`doctor`/`check` cover the status
  line only). On this machine session wake is not wired in Claude, and opencode lacks ai-kit's precompact.
- Proposal: one shared event catalogue mapped per host; one small dispatcher hook per host that reads layered
  settings when it fires (defaults, `~/.config/ai-kit/hooks.toml`, `<repo>/.aikit/hooks.toml`), so toggling
  never rewrites host configs; launch mode from an `AI_KIT_RUN_CONTEXT` variable set by ai-kit launchers, then
  `HERDR_ENV`, then the hook's agent id; a `hooks status` command; hooks print one line naming the playbook to
  load (advise, never block), with an opt-in command list for agentless events such as the git hook. Spikes:
  reset time in `StopFailure`, pi's briefing, opencode child sessions, Cursor CLI hooks, Codex trust under
  `codex exec`, Copilot running `.claude` hooks, `asyncRewake` for CI watching.

**One skill instead of the `ai-kit-project-rules-*` family.** The checker family was not the smartest approach
everywhere. The rules become playbooks/runbooks: assets inside the skill, adaptable per project by the
developer, or both; scripts decide at invocation what to generate, what to edit, where each thing lives, what
belongs to every phase and what runs each time. Some content lives in README.md; AGENTS.md keeps only the top
rules and points to runbooks (for example "run everything in docker, see `docs/run-book/<x>.md`"); other assets
explain how to validate and configure arch tests, CI/CD, docker, Makefile and pre-commit; one clear rule on
language and interaction; one on using jev for decisions; and the quota-wake cases: wake on rate limits with
periodic checks hoping for an early reset or at the reported reset time, keeping the 5-hour windows consistent
to avoid hitting a limit, and anticipating when usage nears the limit before the window ends (check the
schedule). The logic lives in the skill, driven from AGENTS.md.
The skill runs on a strong model: opus at xhigh, or it delegates by area to opus or sonnet subagents as each
area needs, when it applies or writes the rules into a project, because there are many points to weigh.

**AGENTS.md is the mandatory file.** Detect AGENTS.md versus CLAUDE.md-only projects; AGENTS.md is mandatory and
CLAUDE.md an optional symlink to it. Respect an existing AGENTS.local.md (or create it in place of
CLAUDE.local.md) and always symlink the Claude file to AGENTS(.local).md, since current Claude models read
AGENTS(.local).md. curated-config must set `claude_md_path` to AGENTS.md or AGENTS.local.md explicitly (not
stated before).

Checked 2026-11-02 (official docs, plus a local symlink test):
- Claude Code reads `AGENTS.md` natively since v2.1.277 (a CLI version, not a model; this machine has 2.1.316),
  but by default only when no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` exists in the folder or
  above; a `claude-md-and-agents-md` setting changes that. It does NOT read `AGENTS.local.md`, and no host reads
  `AGENTS.local.md` on its own (opencode can through `instructions`). So a lone `CLAUDE.local.md` linked to
  `AGENTS.local.md` silently drops `AGENTS.md`. The owner's premise holds for AGENTS.md, not for the `.local`
  file.
- Codex and pi read `AGENTS.override.md` / `AGENTS.md`; Cursor reads `AGENTS.md` (its CLI also `CLAUDE.md`);
  Copilot CLI merges `AGENTS.md`, `CLAUDE.md` and `GEMINI.md`; opencode and pi fall back to `CLAUDE.md` only
  without `AGENTS.md`. Gemini CLI is being replaced by Antigravity CLI.
- A `CLAUDE.md -> AGENTS.md` symlink is officially supported by Claude; on Windows Git checks committed symlinks
  out as one-line text files unless `core.symlinks` is on, so a one-line `@AGENTS.md` import file is the
  portable form.
- open-gsd's `claude_md_path` accepts any path (incl. `AGENTS.local.md`), honoured only by the claude runtime.
  It must not point at a symlink: GSD writes a temp file and renames it over the path, which replaced a
  `CLAUDE.md -> AGENTS.md` link with a plain file in the test. Its default `./.claude/CLAUDE.md`, once created,
  stops Claude reading `AGENTS.md`, so curated-config must set the path explicitly to the real AGENTS file.
Owner decision (2026-11-02): ignore Windows. Forget CLAUDE.md and its variants: the skill works only with
AGENTS.md and AGENTS.local.md and configures each host to read them where the host does not do so natively
(for example opencode's `instructions` lists AGENTS.local.md). open-gsd's `claude_md_path` always points at
AGENTS.md or AGENTS.local.md, a real file. Gaps to spike, not blockers: an existing CLAUDE.md hides AGENTS.md
from Claude, so the skill migrates it into AGENTS.md (asking first); Claude does not read AGENTS.local.md
natively, so find how (for example an `@AGENTS.local.md` import from AGENTS.md, if Claude honours imports
there; unverified).

**Vertical slices as a top AGENTS.md rule.** Agents asked for a multi-layer app tend to build layer after layer
(database, then backend, then frontend, then security), showing nothing until the end. Build by vertical
slices instead, each feature through a cycle: mocks -> basic front -> backend -> database -> real data
(non-mock) -> security -> infra -> observability -> accessibility. Example: login, people list, departments
with people and hierarchy, registration CRUD: first the list mockup and a basic front, then a backend endpoint
over fixed mocks, then its database, then login the same way, then departments with people, each pass
following security, infra and observability. Emphasise the matching skills in the matching stages (software
architecture with ponytail among others, UI/UX patterns with impeccable or similar ones discoverable on
skills.sh, security, infra) as a playbook, with a top-3 of "never / avoid" recommendations in AGENTS.md.

Checked 2026-11-02: the best-fitting names are outside-in vertical slices, each feature a tracer bullet or steel
thread, the first one a walking skeleton (Cockburn), with mock-first order; the security -> infra ->
observability -> accessibility tail has no classic name and works as a per-slice definition of done. Putting
security and accessibility last runs against "shift left"; a note on both at the mock stage is a researcher's
suggestion, not an owner decision. open-gsd already plans tracer-first (tracer -> real data -> validation ->
polish/accessibility), and MVP mode adds user stories and a walking-skeleton `SKELETON.md` for phase 1, with
security as its own gate; it lacks an explicit mocks stage (its tracer must be production quality), an infra
stage and an observability stage. Lens skills installed: ponytail, frontend-design, built-in security-review,
playwright, superpowers; impeccable only project-local in this repo (`.agents/skills`, untracked together with
`skills-lock.json`); `claude-security` plugin downloaded but not enabled; no infra or observability skill.
Quota-wake gaps: early-reset polling conflicts with the "no repeating job" rule and has no cheap quota probe;
nothing lets the agent act on the pace gauge; no rule arms a wake before the limit; how Claude's 5-hour
window starts is unverified.

**The user sees part of the deliverable from phase 1.** Part of the vertical-slice rule: a UI project closes
phase 1 with a mockup deployed on minimal infra; an API without a front closes it with at least a service
contract (a JSON sample tied to a schema that meets the contract, an OpenAPI/Swagger document).

**Top-5 AGENTS.md rule: no command confirmations in bypass mode.** When the developer runs in bypass mode,
anything that is more than a one-liner goes into a `.sh` (or `.py`) file that is then run, so the session
never stops for confirmation; long inline commands (five or more lines on screen even on a PC) defeat bypass,
since the user ends up accepting them anyway. This belongs in the top 5 rules of the generated AGENTS.md.

**Skills the rules skill chains.** `crafting-effective-readmes` to write or update README.md; `draw-io` or
`mermaid-diagrams` to create or update useful diagrams in the README; `agent-md-refactor` through a wrapper that
adds the project-rules rules and runbook references to AGENTS.md. History: the owner asked for this in the
2026-09-09 todo (`.planning/todos/completed/2026-09-09-agents-md-rules-checker-skill-wrapping-agent-md-refactor.md`:
rule 11 "the README must be updated using the `crafting-effective-readmes` skill", and "use the
`mermaid-diagrams` skill when a doc needs one"); the shipped house rules kept only the generic "update READMEs"
wording, so the skill names were lost; today no ai-kit skill chains `crafting-effective-readmes` or a diagram
skill, while the agents checker already wraps `/agent-md-refactor` optionally.

**Process.** Review everything in the current `ai-kit-project-rules-*` skills and the October context capture,
classify the best strategy, find blind spots, and design one cleaner skill. Per-ecosystem tooling (pre-commit
for Java, Go, Node and others; what CI must run before an image build or a deploy; splitting pre-commit and CI
tasks; arch tests by layers) is too open to fix in advance and needs research, partly at invocation time.

### Round 8 (2026-11-02): jev sizes the review

**jev decides how many review lanes a plan needs.** Before a plan is executed, jev scores confidence in it and
the result sets one or two review lanes for `ai-kit-spec-review`; the same for `skill-judge` (one or two
judges). Constraint to respect: jev is advisory and its own rules forbid letting an answer select a route on
its own, so the lane count comes from deterministic signals plus jev's score, with a floor of one lane: for
example two lanes when the plan touches security, data, irreversible operations or many files, when jev's
confidence is low, or when jev returns `needs_fallback`; for the judge, two judges when the last verdict sits
within the judge's noise (7-10 points) of a grade boundary or had a high finding. The rule and its thresholds
are decided in discussion.

### Project-rules design proposal (synthesis, 2026-11-02; awaiting owner answers)

- Strategy: one skill of event playbooks plus the kept deterministic check scripts (hybrid). The shared library
  moves inside the one skill (no `_shared`, no vendoring); about 10k lines of tested detection code stay; the
  branching lives in a `plan` script's output, so each playbook reads as a straight checklist.
- Proposed name `ai-kit-project-rules`. AGENTS.md gets only a marked block; runbooks go to
  `docs/run-book/<topic>.md` with a hash header so developer edits are never overwritten. Event playbooks:
  bootstrap, session start, worktree created, end of task/plan/phase, CI wait, PR review loop, delegation, quota,
  audit; 16 area runbooks.
- Runs as an orchestrator on a strong model with three waves of subagents on strong or standard models; only
  the orchestrator writes; research time-boxed per stack and cached (14/30/90 days by category); without
  subagents the waves run in sequence; on a weak model templates only, pending items labelled.
- Draft AGENTS.md block (24 lines). Top 5: AGENTS.md is the only instructions file; vertical slices outside-in
  with something visible at the end of phase 1; bypass mode means no multi-line inline commands; done means the
  gates pass; talk in the user's language, write in English, settle gray areas with jev. Never: a whole layer
  before one slice works end to end (and no mock outliving its slice); print, log or commit a secret; reset,
  clean, force-push, push or touch the user's real config without consent. A pointer to the events runbook,
  and an `@AGENTS.local.md` line (unverified).
- Instruction files: migrate any Claude file into the matching AGENTS file after asking, then remove it; the
  audit flags a reappearing one (GSD's default `.claude/CLAUDE.md` is the likely source); `claude_md_path` names
  a real AGENTS file; AGENTS.local.md reaches Claude by the import line, opencode by `instructions`, other hosts
  by the session-start hook injecting it (all spikes); in a worktree AGENTS.local.md is a link, except when GSD
  writes to it (then a copy).
- Hooks: host wiring stays user-level; the skill writes only `.aikit/hooks.toml` and a git `post-checkout`
  script.
- Order: before dist (so dist does not vendor seven skills about to go); the seven leave the re-judge list.
  ai-kit's 11 self-violations: two fixed in the repo, two in the checker, one rule change, five owner's call.
  Five phases; phase 1 reproduces today's audit findings on ai-kit and turns a CLAUDE.md-only fixture into
  AGENTS.md.
- Open questions (14): commit compaction unit; setup target names; pace gauge; 5-hour grid; early polling
  versus the no-repeat rule; skill name; which AGENTS file GSD writes, where opencode wiring lives, dispatcher
  injection default; never list general or slice-only; strict Makefile rules; runbook location; ai-kit's own
  AGENTS.md generated or hand-written; PR review loop consent; extra stacks and CI platforms; commit
  `.aikit/hooks.toml` or keep it personal.

### Round 9 (2026-11-02): owner answers at the milestone start

Asked during `/gsd-new-milestone` questioning. Answers are the owner's; "for jev" items are settled in the
phase's discussion through the decision ladder.

**Commits, push and tests.**
- Compaction is by logical unit, never one squash per phase: a plan with two features may become two commits.
  jev proposes the grouping. Push after each finished plan (GSD) or plan (superpowers); in MVP mode on a
  main-only project the same point merges without review. Rule and thresholds for jev in discussion.
- Early phase: pre-commit runs, in parallel, only the test modules that cover the staged files; pre-push keeps
  the full suite; slow modules get faster. Found while answering: the owner's push failed on
  `test_long_goal_eval_renders_the_pointer_form` because the eval tests passed the caller's environment to the
  CLI (a plain terminal has no host signal, so the goal form was dropped); fixed on the test side (commit
  "pin Claude Code as the current host"). Still open: the goal-prompt eval tests call the real `claude`
  binary (`--version`/`--help`, about 16 s per test, 146 s for the module) and fail on another line when
  `claude` is not on PATH; tests must use fakes, never real host binaries.

**Project rules (answers to the design proposal's 14 questions).**
- Setup targets: `setup-dev` (everything a fresh worktree needs) and `setup-docker` (build and start the local
  stack); `setup-env` stays as an alias for one milestone.
- Quota: keep it simple in this milestone. A fixed wake on a 5-hour grid from the first detected window (for
  example 01:01, then every 5 hours, capped at 7 days for one session; Claude passes the window to the status
  line, so reading it deterministically should be cheap) plus one wake just before the session is known to
  die. The pace-gauge reaction (above 80 % used while the pace says the limit comes before half the window,
  then check for a reset every 10 %) is wanted but needs quota logic shared by session-wake, the rules
  playbook and `cross-ai.mjs`; where that shared logic lives (library, playbook or skill; session-wake may
  belong in a playbook) is a design point for this milestone, not built before it is settled.
- Skill name `ai-kit-project-rules`. GSD's `claude_md_path` points at AGENTS.md. AGENTS.md carries one line
  such as "Load and prioritize the rules in AGENTS.local.md if it exists" instead of per-host wiring or
  dispatcher injection. The never list stays general, as drafted.
- Makefile: `validate-<category>` aliases only when a category has more than one tool, with as few
  categories as possible and a cap (agents have split linting into dozens of validations); the 3-line recipe
  cap stays.
- Runbooks at `docs/run-book/<topic>.md`; the docker one moves from `docker/local/README.md`.
- ai-kit's own AGENTS.md: the owner's hand-written sections stay on top; the generated rules go below them,
  matched against the existing rules to avoid collision, redundancy and contradiction.
- PR review loop: first look for an existing skill or user rule (for example a receiving-bot-feedback skill
  that wraps superpowers' `receiving-code-review`, checks each comment against the code, replies, fixes and
  re-triggers review) and reuse it; ask-once-per-loop consent is only the fallback.
- No extra stacks or CI platforms in the first version.
- Hook settings follow the existing personal `.aikit/` (gitignored) plus `~/.config/ai-kit/` pattern.

**One config design for every ai-kit skill.** `review-spec.toml` already drives executors too (the
superpowers adapter filters it by `purpose`), so its name is misleading, and a separate `hooks.toml` beside it
would add a file without a plan. Inventory every skill and tool that keeps settings (reviewers and executors
with the trust file, hooks, project rules, status line, jev consent, secrets), decide with evidence between
one file with a section per area and one file per concern under neutral names (project layer over user
layer), rename `review-spec.toml` with automatic migration and every caller updated, keep writes atomic and
lossless. Before or together with the spec-config phase.

**Review and execute.** `--no-cross-ai` still means session model, no config needed. When no configured
executor is available, an opt-in fallback to the session's own model, with jev choosing haiku or sonnet;
when off, the error names spec-config as the fix. The superpowers adapter refactor and the spec-config
handoff land in one phase.

**Decisions left at the v1.3 close.**
- The three workflow rules (arm the wake, runner pointer, CPU share) arrive through the new rules skill's
  block, not by hand now. pi does not get goal-prompt.
- Skill-judge: only the new judge counts. Any skill it has not judged, or that scores below the bar, is
  judged by it; the old /120 scores (a different judge, not only a different scale) stay as history only.
- Runner self-test budgets (30 s / 60 s per fake-CLI case; real runs keep the 30-minute outer limit) scale
  with host load.
- Phase 20 defaults stay. Laya is calibrated in this milestone (and the opencode judge lane re-judged).
- The secret-shape scanner is widened to more key shapes and shared as one copy.
- goal-prompt wraps long lists and commands instead of refusing.
- Each skill gets new-shape evals in its batch phase. Windows entry 7 is waived (Windows is out of scope).
  Plan-template and executor-brief fixes (always list the unit and arch groups and the guard block, harden
  verify lines) land with the execute adapter work.

**A rule for every skill.** Prefer simplicity over complexity, but the best implementation over the easiest
one; MVP mode shifts the weight toward simplicity, yet in every case the best implementation beats the easy
one. When the environment has jev, use it to classify and to decide on certainty and stated criteria. Home:
one line in the generated AGENTS.md top rules (every session and host reads it), detailed in the decisions
runbook the line points to.

**Milestone version:** v2.0.

### Round 1 (2026-11-02)

**First step.** Start with `/gsd-new-milestone` fed by this document, not `/gsd-onboard`: onboard only routes to
a codebase map here and raises a false "planning incomplete" alarm because REQUIREMENTS.md was archived at the
v1.3 close.

**One shared cross-AI runner.** open-gsd's cross-AI review/execution and ai-kit's own review/execute lanes do the
same job. Wish: one shared runner script usable by both, taking runtime, provider/model, effort, and whether to
escalate across runtimes (declared order) or across models of one runtime. The lane TOML ai-kit writes today
does not separate review models from execution models; the redesign must. Builds on the pending todo that
unifies the review/execute lane TOML.
Checked 2026-11-02: the TOML has one `[policy]` ladder and one `[[reviewers]]` list; the only role marker is an
optional `purpose` field, absent from every entry in the repo file, so one order serves both roles. Effort is a
flat field only codex turns into a flag (cursor, opencode and pi carry it in the model id). The runner runs one
runtime per call today. Owner decision (round 2): runtime escalation and model escalation are opt-in flags,
off by default; this replaces the old "never switch harness, provider or model on failure" rule, which stays
the default behaviour. open-gsd execute already pipes to our runner through
`workflow.cross_ai_command`; open-gsd review runs its own per-CLI lanes and never reaches the runner. One
config source should replace today's three (the TOML, `.planning/config.json`, the runner's settings block).
Live defect: curated-config writes `review.effort.opencode = "high"`, which open-gsd turns into `--variant`,
a flag opencode 2.x rejects, so every opencode review lane it configures in another project fails (this repo
was fixed by hand).

**Curated-config redesign.**
- Always fetch open-gsd's `docs/CONFIGURATION.md`, `docs/reference/agents.md` and
  `docs/how-to/configure-model-profiles.md` for current facts, and keep a per-version cache under `.aikit/`.
  Fetch them at the release tag that matches the installed version (for example `v1.18.0`), since that is what
  the install obeys. Checked 2026-11-02: `next` is the default branch and holds unreleased work (39 commits past
  v1.19.0); `main` carries the released state (a release commit on the v1.19.0 day). Read `main` or the newest
  tag only to judge an update, never `next` for configuring.
- Ask grouped questions, ordered so one answer removes later ones. First: MVP or not, UI project or not (from
  README/requirements, an explicit user statement, or asked for a new project).
- MVP does not imply a granularity in GSD (checked): granularity only sets phase and plan counts, MVP is a
  per-phase planning mode. Our rule on top of GSD: ask granularity next to MVP (fewer, faster phases vs more,
  precise phases), guided by the docs' "Common Setting Combinations" section.
- Model and effort: preferred profile `balanced`, dynamic routing enabled, models per tier
  (`dynamic_routing.tier_models`, slots light/standard/heavy; inert unless `dynamic_routing.enabled`), per-agent
  model overrides and effort per tier and per agent, classified with jev from agents.md by our own criteria,
  so quality goes where it is needed and tokens are saved elsewhere. Respect "Per-Phase-Type Models" and
  "Resolution precedence".
- Apply every setting through `gsd-tools` with the parameters each setting needs (config-set, effort sync), not
  by writing config.json directly. Checked on 1.18.0: always run the target project's own `gsd-tools`
  (`effort sync` writes the agents of the install it runs from), and validate effort values first
  (`config-set` accepts any string and GSD then ignores it). The how-to on model profiles names no
  `gsd-tools` command and no effort; CONFIGURATION.md and the settings workflows do.
- Granularity facts: 2-4 / 4-6 / 6-10 phases and 1-3 / 3-5 / 5-10 plans per phase (roadmapper and
  CONFIGURATION.md); the new-project question still shows older numbers upstream. The docs' presets are
  Prototyping (coarse, budget, checks off), Normal (standard, balanced) and Production (fine, quality); none
  mentions `mvp_mode` or dynamic routing.
- The skill must never remove settings it did not plan. Today it deletes the whole model-override family on
  apply, which would wipe this repo's `tier_models` and the planner pin.
- Runtime: Claude is preferred, not forced. When the detected runtime is not Claude, ask whether to change
  open-gsd's runtime in `.planning/config.json` or treat the session as temporary.
- UI phase and UI review only for real UI projects (all three UI toggles default on, and keyword detection fires
  on CLI phases). Avoid cross-AI execution; when configured, ask the user to confirm (GSD never asks).
  `response_language` English unless asked. `claude_md_path`: prefer AGENTS.md; confirm when set otherwise.
  Branch per phase (`git.branching_strategy: "phase"`); GSD has no worktree-per-phase setting. `intel.enabled`
  true; graph refresh depends on whether open-gsd is used. Checked: open-gsd rebuilds the graph only through
  an opt-in hook (`graphify.enabled` + `graphify.auto_update`) after commits or merges on the default branch,
  never at phase close; intel refreshes only its API-surface file before each plan-phase. A phase-close
  refresh would be our own addition.
- Base branch detection must be smart: if only main/master exists, skip dev/sandbox; otherwise detect where
  merged commits flow (for example dev/develop -> rr/uat/st/staging -> main, some stages optional or
  switchable). main, dev and sandbox are likely protected.
- GSD version: compare local with upstream, read the changelog, and offer a local, Claude-target update only
  when it is worth it, labelled by impact (patch/minor/major/critical). Installing remains tools-installer's job
  outside this offer. Checked: the changelog uses Keep a Changelog sections with no severity labels (Security
  is the only automatic signal); the version can be read from the npm registry dist-tags of
  `@opengsd/gsd-core` without the npm CLI; the npm `next` tag is stale. 1.18.0 -> 1.19.0 is minor but worth it:
  a shell-injection fix, Pi agent steps working, and fixes for the UI gate on non-UI projects and worktree
  commits; its stricter plan checker can loop plans that passed with warnings.

**Spec-discuss.** Always produce SPEC.md, CONTEXT.md and the discussion log for a batch of phases, with jev in
both modes. Default interactive: spec-phase asks, discuss runs `--analyze --all --batch`. Auto: decided
automatically, ready for an autonomous run (the goal-prompt skill) that executes what was decided and stops only
on a blocker. Checked: the literal `--assumptions` flag on `/gsd-discuss-phase` only lists assumptions and
writes no CONTEXT.md, and `--auto` chains into plan and execute; the skill already avoids both, so "auto" means
assumptions mode decided automatically.

**Provider/model discovery.** `ai-kit-opencode-providers` is only an opencode.jsonc list/remove editor that
nothing uses. Wish: a shared discovery script for opencode and every other runtime. `detection.py` is already
the one place that lists models; duplicated pieces (config paths, the JSONC scanner, the atomic writer) should
be shared. opencode moved from 1.x to 2.x during v1.3, so model-listing code and docs must be re-checked
against the installed version. Checked on 2.0.31: our model listing and parsing are right, but the official CLI
docs still describe 1.x and no 2.x release notes are published, so only the installed binary's `--help` is
trustworthy. Stale: runner comments claiming `opencode models` lacks `--standalone`, the opencode CLI profile
(providers that no longer exist, effort called uncheckable though the model API lists valid levels), and
review-spec files naming `router-env/my-plan-review`, which no longer exists. Plan together with backlog 999.14 (skills installed as copies, which breaks
shared modules reached through symlinks).

**jev in every skill that classifies.** Every skill that classifies something uses jev-fast-decision for quick
decisions with a certainty level, and stays resilient when jev is not installed. jev is a black box: its
fallback order (Laya, then a remote provider, then the native model) belongs inside it. Adding or removing
backends is a later discussion.

**Remove `mermaid-audit`.** It is being rebuilt in the owner's agent-toolkit repository with its rules built in.

**Resilience policy (for jev).** The stack must survive a failing runtime, provider or model: soft retries for
transient server or proxy faults, periodic retries for 5xx and quota errors (quotas have reset times but may
reset early), and model fallback (a new model may fail under load while an older one answers; a proxy may
blacklist a model and route to another). This mixes deterministic rules and inference. It must also settle the
three conflicts found: the retry-ladder memory (wait 10 min, 4 h cap) vs the shipped single wait; the three
referees run in parallel through opencode vs referee-one and two through pi with three only as a replacement;
and llm-env's finding that only the native lane found real defects vs the "no native Opus judge" rule.

### Round 2 (2026-11-02): spec-config, model catalog and the review/execute lanes

Focus for now is the superpowers flows; the GSD execute adapter and ai-kit's review of GSD plans look
redundant with GSD's own review lanes and are deferred to a later round about rules that detect GSD review
and execution prompts.

**`ai-kit-spec-config` is the hub every `ai-kit-spec-*` skill chains to.** If a review or execute starts and no
config exists, the config workflow runs: it discovers models, picks review models in review mode and execution
models in execute mode, and writes the TOML. The caller fails clearly when spec-config or its scripts are
missing. Common scripts live inside spec-config or a shared folder (`skills/_shared`). `ai-kit-opencode-providers`
stops being a skill; its useful pieces move behind the existing skills.
Checked 2026-11-02:
- No skill hands off to spec-config today. spec-review falls back to the session default (and also falls back
  quietly when its own script is missing, by its "never block the review" rule, which the wish reverses);
  spec-execute-superpowers returns `quota_exhausted` with no candidates and no hint; spec-config has no scripts
  of its own (it calls spec-review's `ai-kit-spec.py`) and only sets up reviewers, never executors.
- The superpowers adapter filters the shared list by `purpose`, task type and context size, then list order and
  quota; it runs spec-review's own copy of `cross-ai.mjs`. Effort is dropped silently except for codex; the
  `strength` field is free text no code reads.
- The spec skills' real shared library is `skills/ai-kit-spec-review/ai_kit_spec`, reached as a sibling folder;
  `skills/_shared` holds only the project-rules library and is never linked by the installer. Moving shared
  code either way must be planned with backlog 999.14 (copy installs).
- The router-env names all exist live (my-referee-one/two/three, my-coding, my-coding-lite); pi reports no
  effort levels for them while opencode lists low/medium/high. Both real TOMLs still name the removed
  `router-env/my-plan-review` and no referee or my-coding entry.
- Removing opencode-providers touches its test, the test lists (Makefile, pre-commit, gate-scope test,
  pyproject), the runtimes-table test, the README and three "copied from" comments. Its one unique behaviour,
  finding TOML entries that name a provider, fits a spec-config stale-entry check (which would have caught
  `my-plan-review`).
Open for the owner: does `--no-cross-ai` still mean "session default, no config needed"; is a native fallback
for execution wanted (new behaviour); and does the deferred superpowers refactor go before or together with
the spec-config handoff (same code).

**Discovery across runtimes.** spec-config collects providers and models registered in copilot CLI,
cursor-agent, pi, opencode and claude.

**Model catalog.** A script downloads model data from models.dev, Artificial Analysis and possibly the Arena
leaderboard ELO (OmniRoute syncs it periodically for model-intelligence rankings), or combines the three, into
one detailed file per runtime and model with a cache time. Properties wanted:
- tier, with four or more tiers, where a model's tier can shift with effort (for Claude: haiku, sonnet, opus,
  fable land differently by effort);
- class: agentic, lightweight or frontier; relative cost;
- modalities: view or edit images, video, text;
- strengths: UI (web vs TUI), security, agentic execution of a plan with a clear recipe, planning.
These wishes should have been recorded in the discussion log of the phase that built the catalog; check and
carry them forward. An Artificial Analysis key was left by the owner in a tmp folder (never print it).
Checked 2026-11-02:
- The catalog exists (`model_sources.py`, `catalog_build.build_model_catalog`, CLI `fetch-model-catalog`,
  cache `~/.cache/ai-kit/spec/model-catalog.json`, 30-day expiry or schema change). It stores context and
  output limits, tool calling, structured output, one image-input flag, prices, three Artificial Analysis
  scores, speed, name-based router guesses, and effort levels for 7 of 195 models. No tier field; no class,
  cost band, video/output modalities or strengths. It was built from a superpowers design spec (2026-09-02)
  with no discussion log; the later extension phase only discussed effort levels and the image flag, so the
  capability wishes were never recorded before this document.
- Live defect, urgent for the milestone: Artificial Analysis now returns its Coding and Agentic indexes as
  always null, and the cheap-execution ranking needs a coding score of 35 or more. The cached catalog is on
  schema 2 while the code is on 3, so the next refresh happens at once and leaves that ranking with no
  candidates (from the API spec; not called live).
- Artificial Analysis free tier: 100 requests a day, attribution required, no redistribution; intelligence
  index, six domain indexes, prices, speed, release date; modalities and per-benchmark scores are paid. ai-kit
  already reads its key from `~/.config/ai-kit/secrets.env`.
- Arena ELO: OmniRoute uses an unofficial top-20 mirror; the official source is the Hugging Face dataset
  `lmarena-ai/leaderboard-dataset` (CC-BY-4.0, plain JSON through the datasets server), 23 boards incl.
  coding, webdev, vision and agent, rated per effort variant.
- models.dev gives full modalities, tool calling, reasoning, limits, prices, effort options and release date
  for 8,931 models, incl. a `github-copilot` provider but no cursor provider.
- Copilot CLI 1.0.105 is installed: `--model`, `--reasoning-effort none..max`, but no model-listing command
  (only ids printed in `copilot help config`); its RUNTIMES row has no host signal and no list command. TUI
  and security strengths have no public measure and must be judged (jev or the owner), marked as judged.

**Selection, with jev.** After classification with jev over the catalog, the user picks; the TOML records the
choice and separates reviewers from executors, each with priorities. That TOML is the input to the shared runner
that spec-execute, spec-review or both generate and use. Defaults when router-env is present:
- review: `router-env/my-referee-one|two|three`, one required, two desirable, the third only as a pivot when
  one of the first two fails;
- execute: `router-env/my-coding*` optional; a native model is an alternative.
Without router-env: cursor-agent, copilot CLI or pi with frontier models at high or xhigh for plan and code
review, or a native reviewer (a third-level tier model); execution prefers a code/flash model or haiku-class
models at high. How jev helps the user choose a better model/effort than the current setting is settled when
the spec-review and spec-execute details are discussed.

### Round 3 (2026-11-02): model availability, herdr sessions, orphaned scripts

**Copilot and free tiers.** Copilot CLI lists models only through `/models` in an interactive session, and
that list matters. Options: an online catalog (as for cursor); short probes to see which models actually
answer, since on free tiers a listed model may be unusable (cursor free may allow only `auto`); or driving an
interactive session through the herdr skill chained from our skill.
Checked 2026-11-02:
- This Copilot account is on Free, where GitHub allows models through auto selection only. An undocumented
  per-account endpoint (`GET https://api.individual.githubcopilot.com/models` with the `gh auth token`) lists
  42-48 models with a `policy.state`; 6 are "enabled". Yet `--model` with a disabled and with an enabled id both
  failed with `Model "X" from --model flag is not available.` (exit 1, ~4 s, no quota used), so "enabled" is not
  "usable" and a rejection probe is free. That error text matches no rule in the runner's error catalogue
  (lands unclassified). Premium-request multipliers are gone (AI credits per token since 2026-06-01). Still
  open: whether Free accepts `--model auto` or `mai-code-1.1-flash`, and paid-plan behaviour.
- Cursor: `cursor-agent` is not logged in on this machine, so its list, tier and probes are unchecked; the docs
  say Free has no third-party models but do not say Free is Auto-only (the catalogue rule stays unverified).
- Proposal: per model, record where it was listed from and a separate usability state (verified with date,
  rejected with the error, or unverified, shown visibly). Copilot: list from the models API, fallback the
  `copilot help config` ids; on Free/Student only `auto` usable; probe only models a lane uses; cache one day.
  Cursor: list, gate by the tier `about` reports, one probe per configured model. opencode, pi, codex: no
  probes, record error classes from real runs. Screen-scraping `/model` through herdr is a last resort.

**herdr as a lane transport.** For spec-review, the execute skills and code review: switch between one-shot
`cross-ai.mjs` subprocesses and live herdr sessions when herdr is available. Launch an agent, keep it alive,
reuse it in later rounds of the same plan, kill it when the plan closes, or renew it when review rounds pass
a set count. Open question: does execute chain code-review lanes today (for example through
`superpowers:requesting-code-review`)?
Checked 2026-11-02 (herdr 0.9.3, docs and code only):
- herdr can create panes, start an agent CLI in one (pi, claude, codex, cursor, opencode, copilot), prompt and
  wait, read the screen, and report idle/working/blocked/done/unknown. No kill command (close the pane); no
  JSON, exit code or error class, so a report file must be the result channel, and the runner's retry ladder,
  quota hints and clean-tree gate do not apply inside a pane. Detection needs `HERDR_ENV=1`,
  `HERDR_SOCKET_PATH` and `HERDR_PANE_ID`. No ai-kit code uses herdr today; only manual live checks did.
- Session reuse without herdr: the runner resumes cursor, opencode, pi and codex (exec only) but only inside one
  call's retry ladder; it takes no session id in and does not print one out; claude and copilot have resume
  flags but no resume formula. Nothing keeps a session per plan across rounds; spec-review uses a fresh reviewer
  each round on purpose. superpowers itself resumes its implementer for rounds 1-3, then starts fresh on a
  stronger model, a ready pattern for "renew after N rounds". Trade-off: reuse saves re-reading, but each round
  costs more, compaction loses detail, and a reviewer anchors on its own earlier findings.
- Code review: the superpowers adapter chains none and leaves superpowers' task and final reviews untouched;
  nothing references `requesting-code-review`; spec-review has no diff mode; no skill routes code review to
  cross-AI reviewers. GSD offers an unused `workflow.code_review_command` hook (diff in, APPROVED/REVISE JSON
  out, 120 s timeout).
- Proposal to discuss: a transport setting per lane (subprocess, resumed session, herdr pane, auto); one record
  per plan and lane, renewed after N rounds (default 3), on runtime/model change or failed resume, closed at
  plan close, with a start-of-run sweep of panes we created; the runner gains a session-id flag and prints the
  id. Spike first: does `herdr agent get` expose the session id, can a pane session be resumed headless, and do
  claude and copilot resume in print mode.

**Milestone objective: adopt orphaned scripts.** Scripts left with no caller are found and either adopted into
the skill that should own them, merged with their live copy, or deleted.
Checked 2026-11-02 (266 tracked scripts, 242 with a live caller, incl. modules loaded by name):
- Fully orphaned: `.planning/docs/system-one-decision-skill/scratchpad/` (82 files, three stale copies of the
  jev skill, one script writing into the real `~/.claude/skills`); only planning text names it. Fate: delete,
  keep `PLAN.md` and `review-history/` as research, and repoint the three todos that name it.
- Used only by their own test: `ai_kit_spec/cross_ai_catalog.py` (renders the error catalogue into the runner
  template; add a Makefile target or a doc line) and `jev-fast-decision/scripts/eval_cases.py` (calibration;
  document it).
- Planning-only: the four `.planning/spikes/` scripts, whose findings shipped in session-wake (keep as research).
- Duplicates: the runner template and this repo's rendered `.planning/scripts/cross-ai.mjs` differ only in the
  stamp and baked settings, but no test checks they stay in sync (add one); the 2026-10-13 audit prototype is
  stale. The JSONC scanner has three copies (two inside `tools/`), the atomic writer about eight variants.
- Dead functions (defined, never called): `tools/setup.py` `_visible_len`, `_trunc_visible`, `_env_truthy`;
  `tools/wizard_app.py` `_goto`, `_review_from_board`, `_all_hosts_gate_done`; `gsd_config.py`
  `resolve_model_profile`. Vulture at the project's 80% bar reports none.
- Side finding: `ai-kit-cross-ai`, `ai-kit-session-wake` and `ai-kit-spec-goal-prompt` are not installed for
  any host on this machine and the session-wake hook is not wired; the machine's install is behind `main`
  (re-run the installer).

### Round 4 (2026-11-02): re-judge every skill, dist layout and install, execute and review loops

**Scripts belong to their skill.** The orphan objective covers every script in the repo, above all each skill's
own scripts: a skill's scripts must be the ones that skill actually uses.

**Re-judge every skill.** An early phase re-judges every ai-kit skill with the new judge and writes a report.
Judge rails: two when possible; `router-env/my-referee-one` at minimum, referee-two or three optional; native
opus at xhigh when the referees are unavailable. Its result spawns decimal batch phases (`{phase}.{batch}`),
each improving one group of skills, because the judge changed a lot (it now expects evals and tests) and one
round for all skills could stay incomplete.
Checked 2026-11-02 (inventory, no judge run):
- The judge is rubric version 4, 125 points; the new tests-and-evals dimension (15) wants `evals/evals.json`
  and `evals/trigger-queries.json` (about 20 queries, half near-misses), plus `tests/skills/<name>/` when a
  `scripts/` folder exists; no evals at all is a high-severity finding. "Decision branch": usability credit
  only for branches the judge traced to an outcome, so skills with many resume/fallback paths lose points.
- Two traps: ai-kit keeps flat `tests/test_*.py` (no `tests/skills/<name>/`), and only 5 skills have a
  `scripts/` folder; the re-judge prompt must fix one reading of both for every skill.
- 25 skills: only goal-prompt has new-shape evals (its last verdict is unresolved, 94.4% vs 87.2%); four have
  old markdown evals; 19 none. Every other score is on the old /120 scale; five skills were never judged;
  spec-config and spec-review are near the 500-line limit.
- Proposed order: remove opencode-providers, mermaid-audit and spec-execute-gsd first, then one baseline round
  for the 22 kept skills, then batches: general small skills (cst-refactor, markdown-to-pdf, jev,
  review-fixer); the five rules checkers; rules-agents, rules-all and usage-metrics (after backlog 999.16);
  the spec review family (spec-review, checklist, spec-config, spec-execute); the execution and session chain
  (superpowers, goal-prompt, session-wake, cross-ai, curated-config, spec-discuss), possibly split in two.
- Reuse: the Phase 27 verdict checker
  (`.planning/milestones/v1.3-phases/27-one-shot-goal-and-loop-prompt-skill/skill-judge/check_verdicts.py`)
  is the only one built for the new rubric; it hardcodes the skill and judge list (make them arguments).
  The Phase 27 lane, prompt and report scripts were copied from the gitignored `tmp/p27/` into
  `.planning/research/2026-11-02-next-milestone/p27-judge-scripts/` (paths inside them still point at the
  pre-archive phase folder). Judge noise is 7-10 points between runs on an unchanged skill.

**dist layout and install.** Build a `dist` folder as the owner's agent-toolkit repository does, with tests (and
evals) kept outside what ships with each skill. This may change how skills are downloaded and installed. Update
the README like agent-toolkit's (install as a plugin and with `npx skills`). An early phase adjusts setup to use
`npx skills` headless to sync skills to the host runtimes ai-kit detects and the user selects (pre-filtered),
showing only its output.
Checked 2026-11-02 (`skills@1.7.5`, help and `--list` only, nothing installed):
- agent-toolkit keeps evals in each skill folder and tests in `tests/skills/<name>/`; `scripts/build_plugins.py`
  copies each plugin into a committed `dist/plugins/<name>/skills/<name>/` without evals, tests and caches and
  rewrites `.claude-plugin/marketplace.json`; PR CI rebuilds and fails on a diff. Gap not to copy:
  `npx skills add` of that repo finds the source `skills/` before the dist folders, so non-Claude hosts get the
  source copies with evals (read in the CLI code, not installed).
- The CLI: `add`, `list`, `remove`, `check`, `update`, `use`, `find`, `init`; its `sync` handles npm-shipped
  skills only. Headless flags `-a`, `-s`, `-g`, `-y`, `--copy`, `--json`; local paths and git subfolder URLs
  work (22 ai-kit skills found). Setup must always pass `-a` (inside an agent it installs only for that agent).
  Link mode first copies into `~/.agents/skills`, which pi and Codex read, breaking ai-kit's three-skills-for-pi
  rule; `--copy` avoids it but pi and Codex share that folder. Copies skip symlinks pointing outside a skill.
  On this machine `npx` is a `pnpm dlx` shim.
- Live defect: the CLI skips `ai-kit-project-rules-agents`, `-cicd` and `-docker` with a YAML error (unquoted
  `: ` in `description:`); Claude Code accepts them. Needs quoting plus a strict frontmatter check.
- Copy installs break: `_shared` (no SKILL.md, never installed) for the six rules checkers and rules-all; and
  session-wake (hard), spec-execute-gsd, spec-execute-superpowers, curated-config and spec-config unless
  `ai-kit-spec-review` is installed beside them. The other 13 skills stand alone.
- Proposal: source in `skills/`, a committed generated `dist/skills/<name>/` without evals and tests, a
  rebuild-and-diff check; vendor `_shared` into the rules skills at build time; for `ai_kit_spec`, vendor or
  always install the group together (spike). Setup pre-checks detected hosts, shows a dry run, then runs one
  `npx -y skills@<pinned> add <checkout>/dist/skills --skill ... -a <host> -g --copy -y` per host, passing the
  output through, removing only ai-kit's own links (never `remove --all`: `~/.agents/skills` holds 12 skills
  from tools-installer). Open: lock-file drift for local sources, GitHub folder URLs, whether opencode lists
  skills twice from both folders, whether Cursor and Copilot load the CLI's folders, `--json` stability.

**Execute: superpowers only, with code review.** Remove `ai-kit-spec-execute-gsd`; keep the superpowers adapter.
When an implementation completes, chain superpowers' `requesting-code-review` flow and iterate until everything
passes. Use jev-fast-decision throughout to classify gray areas before handing a decision to the user.

Checked 2026-11-02:
- superpowers: `requesting-code-review` dispatches one fresh subagent from `code-reviewer.md` (no model line, so
  the session model) with a description, the plan and a base/head commit, and returns Strengths, issues as
  Critical/Important/Minor with file:line, and "Ready to merge? Yes | No | With fixes" (no `### Status:` line,
  which is all spec-review's report merge reads). It has no loop. The loops are in subagent-driven-development:
  up to 5 fix rounds per task (1-3 resume the implementer, 4-5 a fresh one on a stronger model, then the
  controller rules), and for the final review one fix pass and one re-review ("There is no second fix wave").
  So "iterate until everything passes" needs ai-kit's own capped loop. Lane injection points: the task
  reviewer (its prompt already has a `model:` slot), the fix-loop re-review, and the final whole-branch review,
  whose inputs are files on disk and fit the runner's read-only review mode. `receiving-code-review`'s "stop and
  discuss with your human partner" step is where jev would classify first.
- Removing spec-execute-gsd does not break GSD cross-AI execution (curated-config already wires
  `workflow.cross_ai_command` to the runner). It touches the skill and its test (move the router's framework
  detection test out first), about ten other test files, the Makefile, pre-commit, pyproject, the README, the
  router and curated-config docs, and comments; the installer's stale-link cleanup should drop the live link.
  Left unused: the runner guidance prepend (`project_runner_command(guidance=True)`, `PROJECT_GUIDANCE_PATH`,
  the `cross-ai-guidance.md` curated-config still writes) and `gsd_tools.prior_value`. The router keeps
  detection and hands GSD plans back to `/gsd-execute-phase`. Lost: per-phase quota-checked model picks, the
  codex write sandbox and copilot as a GSD runner.
- spec-review today: cap 3 rounds, ends on `### Status: Approved` (no Critical or High left), fresh reviewer each
  round, reviewer-fixer disagreements go to the user; lanes chosen once before the loop, unavailable ones
  skipped to the session default; after dispatch it never switches lanes (one delayed retry on a quota hint,
  stop on auth, otherwise the whole review fails), so one failing lane in round 2 ends the review. No jev
  anywhere in spec-review, checklist, fixer, spec-config, the router or the superpowers adapter; the jev ladder
  client (`decide.py`) lives inside spec-discuss's scripts and would need a shared home.

**Review iterates with jev.** `ai-kit-spec-review` also iterates and uses jev where possible.

**Judges and reviewers are preferences, not fixed names.** The user selects the judges and reviewers available in
each environment; the router-env referees are only this machine's preference. Examples: here, three
router-env referees, plus models such as gpt-6.x-sol, glm-5.3 and kimi-k3 on pi and opencode; elsewhere maybe
only gpt-x-sol through cursor or copilot; native opus everywhere. Discovery offers what the environment has,
jev may rank it, and the user picks. No skill, phase rail or default may hardcode the referee names; the
re-judge rails above read "two judges chosen from what is available, native opus xhigh as fallback".

**Both chain spec-config and use resilient lanes.** Execute and review use, extend or chain `ai-kit-spec-config`.
Plan review, spec-review and its derivatives use the review-model lanes with fallbacks and switches per the
user's preferences; execute does the same when it reaches code review.

### Round 5 (2026-11-02): plugin skills as lenses, lane tools and skills

**Artificial Analysis key.** The owner put a key in the repo's `tmp/aa-key.txt` (gitignored, never print it);
ai-kit already reads the key from `~/.config/ai-kit/secrets.env`, so decide which one is the source.

**Plugin skills chained into review, execute and code review.** `ai-kit-spec-review` chains important plugin
skills whenever they are available: ponytail (some of its skills fit planning, others audit), simplify,
naming-analyzer, reducing-entropy, and impeccable for UI. Execute considers some of them when something is
unclear and the model must decide. Code review gets the same review models.

**Curated-config wires them too.** curated-config links these skills (and others) to GSD agents through
`agent_skills`. The owner once asked for a plugin discovery where jev decides which skill fits each stage of the
project workflow (simplify maybe optional, others depending on the stage).
Checked 2026-11-02:
- Installed: ponytail 5.1.0 (portable skills; Claude plugin with a hook that turns ponytail on in every Claude
  subagent; opencode and Codex plugins; not on pi): `ponytail` (planning, execute, fixer), `ponytail-review`
  (code review), `ponytail-audit` (audit), `ponytail-debt` (verifier, milestone close). simplify, code-review
  and security-review are built into the Claude binary (no file; Claude-only; simplify edits files, so only a
  post-review pass). reducing-entropy is installed and portable but triggers only when named. naming-analyzer
  is not installed (used in phases 6-15; source in the owner's agent-toolkit). impeccable is not found under any
  spelling (alternatives: installed `frontend-design`, agent-toolkit's `ui-ux-principles`).
- curated-config finds skills in the project, the host's global folder and Claude plugins, and maps them with
  a fixed table (`skill_affinity.json`): ponytail to planner/executor/fixer, ponytail-review and audit to
  reviewer and auditors, ponytail-debt to the verifier, reducing-entropy to reviewer and fixer; no row for
  naming-analyzer, simplify, impeccable or the code-review skills. Caps of 2/3/5 skills per agent by rigor.
  jev never chooses a mapping. GSD skips plugin skills on every runtime except Claude.
- History: the 2026-10-11 ponytail-in-GSD request was built (Phase 18 rows). The 2026-10-13 request (a per-turn
  inventory of skills, MCP servers and commands, jev helping decide what each subagent gets) produced the
  research report `.planning/research/2026-10-13-audit/09-tool-inventory-curation.md` (skill-hint line in prompt
  guidance, a role-keyed table shared by every adapter, jev sorting unknown skills into roles), but only the
  inventory and fixed table were built; the rest never reached a roadmap or todo: lost.
- Where lenses plug in: spec-review, checklist, fixer and the execute adapters chain no plugin skill today. Best
  fit: a named list of lens-skill paths in `build_tooling_guidance` next to the checklist path (reaches native,
  cross-AI and execute prompts, matching the "lens in the reviewers' prompt" rule); an extra lane only for a
  lens too big to inline; a post-approval pass for file-editing skills (simplify, naming-analyzer). Cross-AI
  reviewers cannot load a Claude plugin by name and the runner disables skill discovery on opencode and pi on
  purpose; give the SKILL.md path to read (pi also takes `--skill <path>`); built-ins must be inlined or left to
  the Claude lane.
Owner answers and actions (2026-11-02):
- impeccable is `pbakaus/impeccable` (skills.sh), installed by the owner; it is the UI lens.
- naming-analyzer was installed from agent-toolkit for every host (skills CLI 1.7.5, global, link mode, same
  route as the other agent-toolkit skills). ponytail, ponytail-review, ponytail-audit and ponytail-debt were
  installed for pi from `DietrichGebert/ponytail`; they landed in `~/.agents/skills`, which opencode and codex
  also read, so those hosts may now list ponytail twice (plugin plus copy): check during the milestone.
- The 2026-10-13 design (research report 09) is to be explained and revived or dropped in discussion. Its core:
  extend the existing guidance block with one named list of skills confirmed present, passed by path; rescan
  on every run (a scan costs 6-20 ms, so no cache); make `skill_affinity.json` role-keyed so the execute
  adapters reuse it; jev only as an optional config-time classifier of unknown skills into role buckets,
  always confirmed by the user; skip per-subagent MCP curation.
- Owner decision on that design: build it. Keep a clean list of skills, and of MCP servers where a host allows
  it, per host; pass the right subset to each subprocess, subagent or agent window depending on what is
  available and most appropriate. curated-config does the same per project when it assigns skills to GSD
  agents: by each agent's responsibilities and the skills actually available.
- Artificial Analysis key: both keys work (HTTP 200); they differ. ai-kit keeps reading
  `~/.config/ai-kit/secrets.env` (mode 600, outside the repo); the repo's `tmp/aa-key.txt` is redundant.
  Live check confirmed the defect: on page 1, the coding, math and agentic indexes are null for 200 of 200
  models; the intelligence index is present for only 34.
- rtk is dropped from consideration: it gives no warning and forces agents to re-run commands instead of
  learning, which can cost more. It is still installed (`~/.local/bin/rtk`); remove it from every tool list
  and guidance text (AGENTS.md Tools and Stack, `.claude/cli-environment.md`, the shared tooling notes, any
  lane capability block). Machine uninstall prepared 2026-11-02 (two copies: `~/.local/bin/rtk` 0.44.1 from
  rtk's install script and Homebrew 0.49.0; only Codex was still wired). ai-kit follow-ups: the config doctor's
  rtk Cursor check advises `rtk init -g --agent cursor` (would reinstall it); the agents-file rules checker has
  an rtk house rule; usage-metrics reads rtk's `history.db` as a source; AGENTS.md, `.claude/cli-environment.md`
  and the README list rtk. ai-kit's hooks are already clean (a test fails on any rtk mention). Outside ai-kit:
  tools-installer still recommends rtk and runs `rtk init` for every host after install, so it would re-wire
  them; remove it there.

**Lane tools and skills.** Some cross-AI runs called pi with no tools and no skills. Depending on the task a lane
should get specific skills and tools; for bash, name the tools this repo already knows that cut tokens or speed
work up, but only when they are verified present for that agent and it will use them correctly.
Checked 2026-11-02 (runner `--print-argv` dry runs, `--help`; no real lane run):
- pi exec: `--no-skills --no-extensions --no-approve --offline`, default tools (read, bash, edit, write),
  AGENTS.md loaded. pi review adds `--tools read,grep,find,ls --no-mcp --no-context-files` (no bash, no
  AGENTS.md; its grep/find use bundled rg/fd). A `none` profile (`--no-tools`) exists but nothing selects it.
  opencode exec `--auto`, review `--agent plan` (still loads `~/.agents/skills`); cursor exec
  `--force --sandbox disabled`, review `--mode ask`; codex review read-only sandbox; claude review in plan mode
  with every skill, hook and MCP; copilot review drops the shell (never run for real). The runner's child env
  removes only host-signal variables; PATH and HOME pass through.
- Why pi runs bare: token cost and determinism, for exec and review. Measured: with skills one plan took 278k
  tokens and 54.8 s, stripped 16.9k and 16.6 s; the owner's 2026-10-13 rule was "start bare, opt into skills
  when needed"; Phase 18 made bare the default, Phase 25.1 added the review allowlist. The no-tools calls the
  owner saw were mostly direct `pi -p` probes and judge lanes, not runner launches.
- Tools: rtk, rg, fd, bat, sd, eza, delta, difft, codegraph and graphify are installed and reachable by any
  lane with a shell. The codegraph MCP tool is registered for claude, cursor and codex only; `codegraph
  explore` needs a `.codegraph/` index a fresh worktree lacks. No rtk rewrite hook is wired in Claude, pi or
  opencode now, so `.claude/cli-environment.md` looks stale on rtk.
- The hammer problem is real today: `build_tooling_guidance` checks tool presence in the calling process, never
  against the lane's profile, so a pi review lane without bash is told about rg, fd, bat and sd, and the shared
  notes suggest `sd` in-place edits to a read-only reviewer. This repo's GSD execute hook passes no guidance.
- Proposal: the runner builds the capability block from the final argv (read-only or write, shell or not, one
  usage line per tool found on the child's PATH; rtk, eza and diff viewers off by default; codegraph only with
  an index; MCP only when present and not disabled). Per-task skills: pi through an allow-listed `--skill`
  path (useless under `none`); other runtimes get the skill text inlined (for example ponytail-review on review
  lanes). Unknown: what opencode `plan` and cursor `ask` allow for shell, and whether cursor and copilot load
  `~/.agents/skills` headless.

### History of the round 1 and 2 wishes (traced 2026-11-02)

Traced through archived planning artifacts and the owner's past chat messages; the code was checked for every
"built" claim.
- Model catalog: asked 2026-09-02, built (models.dev + Artificial Analysis fetch, matching, ranking) from a
  design doc outside GSD with no discussion log. Tier, class, strengths, video/editing modalities, Arena ELO and
  a per-model cache time are new on 2026-11-02.
- Lane TOML: a per-entry `purpose` field (review, execute, both) exists since 2026-09-02, but no entry in the
  repo file uses it, so in practice one order serves both roles; separate priority lists per role were never
  designed. Effort detection and opt-in escalation sit in the 2026-10-29 lane-TOML todo.
- Discovery: built for pi, opencode, cursor, codex and claude; copilot has an unverified runner entry only.
- Chaining into spec-config: the 2026-08-27 design chose a one-time hint plus session-default fallback; the
  chaining wish is new.
- opencode-providers: the owner asked on 2026-09-06 for "an installer flag, or a skill or command"; the
  assistant chose a skill (2026-09-07 PRD). The owner now reverses that.
- Curated-config: the 2026-09-23 request was built, but separate MVP, granularity, effort and UI questions were
  merged into one "rigor" question (v2 spec). Lost: "worktrees on" (Phase 7 discussion, turned into "copy this
  repo's config", which never wrote `use_worktrees`), and `claude_md_path` (v1 wrote it, v2 stopped with no
  recorded decision). Decided otherwise: tiers from gsd-core's table, docs read from the install, cross-AI
  execution default yes on Claude and Codex hosts (Phase 18). New: runtime doc fetch, jev tiers, base-branch
  detection.
- Spec-discuss: auto mode built 2026-10-24, recorded only in a review-score row, not as a decision; the
  interactive path does not run `--analyze --all --batch`.
- jev everywhere: asked 2026-10-14, 10-18, 10-30 and 10-31, recorded (two todos, phase 21.1, backlog 999.17);
  only four skills use it; "every skill" was never part of a phase.
- Shared runner: one `cross-ai.mjs` template already serves ai-kit review, ai-kit execute and open-gsd
  execute (`workflow.cross_ai_command`); open-gsd's own review lanes were left out on purpose (Phase 18.1).
- Lost: the model class for review versus execution (flagship reviews, coding models execute), stated
  2026-08-29 and kept only in a memory note; the `strength` field is free text no code reads.
- Claims the code contradicts: the v2 design says only planned keys are touched, but a Phase 17 decision makes
  whole families authoritative and the code clears them; the 2026-09-02 design calls `strength`
  "schema-validated" though nothing validates or reads it; a curated-config note says gsd-core has no
  `tier_models`, untrue on 1.18.0.
- Process failures: on 2026-09-09 the assistant promised cross-AI execution from phase 1.2 on, while execution
  stayed local until at least phase 14 and the reason surfaced only when the owner asked (three times); on
  2026-10-18 an earlier "advisory tools hook" claim the owner never saw working was turned into new work
  without first checking whether the claim was true.

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
