---
created: 2026-11-02T14:54:45.801Z
title: Tooling defects and skill-writing principle found at the v1.3 close-out
area: tooling
severity: major
files:
  - skills/ai-kit-session-wake/ai_kit_session_wake/fire.py
  - skills/ai-kit-spec-review/ai_kit_spec/routing.py
  - .planning/milestones/v1.3-OWNER-FOLLOWUP.md
---

## Problem

Collected 2026-11-02 during the v1.3 close-out. Owner rule: these go to the todo/backlog, not into the
closed v1.3 skills. This todo stays open until the owner says otherwise.

Related: the SJ-1/SJ-3 refactor todo
(`2026-10-31-refactor-execute-gsd-and-rules-agents-sj-1-sj-3.md`), backlog 999.16 (event-keyed playbooks
for the `ai-kit-project-rules-*` family), backlog 999.17 (lite or strong executor choice through
jev-fast-decision) and `.planning/milestones/v1.3-OWNER-FOLLOWUP.md`.

## Solution

### Desktop notices of the session-wake skill (owner report)

Facts, verified in the code and the user journal:

- The only desktop notice in ai-kit is `notify()` in
  `skills/ai-kit-session-wake/ai_kit_session_wake/fire.py`. It runs `notify-send <summary> <body>` only
  (Linux). There is no macOS path: no `osascript` / `terminal-notifier`, and the whole skill has no mention
  of macOS or launchd (its timers are systemd only).
- It is called from `give_up()` when a fired wake finds that the session does not exist
  ("session <id> not found"). The notice uses the default expiry and urgency, so it flashes for a few
  seconds with a short body.
- The two quick "not found" notices the owner saw came from the live lifecycle check run on 2026-11-02
  (a throwaway session id on purpose; the journal shows the give-up lines at 10:41 and 10:50 and no other
  wake in 3 days). It was not a bug in real use, but the notice itself is hard to read.

Checklist:

- [ ] Check the paths before notifying: the notice must say what was checked (the host, the session id, the
  transcript or session-store location that was looked at, and the state file), and only be sent when the
  situation is real (state valid, host not alive, the store path exists but the session id is absent). If
  the store path itself is missing, say "session store not found at <redacted path>" instead of
  "session not found".
- [ ] Make the notice readable: include host, session id (shortened), the reason, and the journal command to
  read the full line; set an urgency and an expire time long enough to read (for notify-send `--urgency` and
  `--expire-time`), or keep it until dismissed for a give-up.
- [ ] macOS parity: if notices exist on Linux they must exist on macOS (`osascript -e 'display notification ...'`
  or `terminal-notifier`), with the same path checks, and the same best-effort rule (never fail the wake
  because a notice failed). The wake itself (persistent timer, one-shot unit) is systemd only: macOS needs a
  launchd equivalent or an explicit "unsupported host" refusal at arm time. Decide which, and label the macOS
  behaviour unverified until run on a Mac.
- [ ] Tests for the notices: a fake notifier for each platform; a test that a missing store path produces the
  path-specific text.

### Tooling defects found during the v1.3 close-out

- [ ] `edge_floor.py check` on the committed Phase 25.1 SPEC returns `ok:false` (floor 48 rows, table 47; the
  encoding case R9 is missing).
- [ ] `goal_prompt.py detect --gsd-cmd` parses output as JSON only; real GSD workflows use `@file:` indirection
  for large outputs, which it does not handle.
- [ ] Stale docstring at `skills/ai-kit-spec-review/ai_kit_spec/routing.py:49` ("until Phases 20-22").
- [ ] Error bodies seen in real runs with no dedicated row in the runner's error catalogue:
  provider_not_configured, `Policy budget exceeded` (429), data_inspection_failed (400),
  context_length_exceeded (400), the Zhipu plan-not-open code 1311, and the 502/503
  "Connection capacity reached for <member>" body (now generic transient).
- [ ] The Claude matcher in the runner reads stderr only; if `claude -p` prints a usage limit on stdout the lane
  is classified as a crash without a class. Verify on the next real limit and fix.
- [ ] ai-kit-session-wake and the other ai-kit-* skills are not installed in pi although setup marks them for
  pi (observed in a live pi session: 29 skills listed, none of the ai-kit-* wake or cross-ai ones). Find out
  why.
- [ ] The StopFailure hook of session-wake does not record the payload; to capture the real body of the next
  Claude usage limit a small opt-in hook that writes field names and the redacted payload is needed.
- [ ] The rows `vendor-zhipu-1310`, `vendor-monthly-limit`, `text-insufficient-funds`,
  `text-model-access-disabled`, `model_cooldown` have real evidence now (see the Phase 25 / 25.1 follow-up
  sections) but are still marked unverified in the runner data; flipping them changes behaviour and the
  pinned template, so it is a separate change. `model_cooldown` also lasted from 2 minutes to over 2 hours
  in real logs while its row is transient.
- [ ] pi exports only PI_CODING_AGENT; the Phase 22 guide expects PI_PROVIDER and PI_MODEL (they do not exist).
- [ ] Fix-up idea: the OmniRoute container logs do not contain the router error codes the catalogue matches
  on; the full bodies live in its database. Decide whether to match on the log wording that does exist
  ("all N active accounts cooling down for model X (reset after ...)").
- [ ] Runtime lists copied by hand with no test that compares them with the runtime table: the runner-capable
  list, the host list, the host-binary map and the error text of the plan editor. The JavaScript template list
  is only tested as a superset. Add one drift test (found by the v1.3 audit).
- [ ] The project `AGENTS.md` links `.claude/cli-environment.md`, but that file is gitignored, so the link
  dangles in a clean checkout. Either track the file or remove the link (found by the v1.3 audit).
- [ ] One goal-prompt test depends on the length of the checkout path because of a separate test of the
  tool-substitution hook; it passes only from a short path. Make the pair independent of path length
  (noted in the v1.3 close handoff).

### Skill-writing principle (owner, 2026-11-02): a SKILL.md carries behaviour, not history

- [ ] No version history in the main flow: no pinned CLI or tool versions, release history or observation
  dates. Use a short conditional only where behaviour truly differs by version ("if v1 ... if v2 ...");
  otherwise stay host-agnostic and state a limitation in one plain line.
- [ ] Mention Claude-, GSD- or other tool-specific facts only where the agent must act differently because
  of them.
- [ ] Provenance (where a claim was observed, binary strings, past sessions, versions, dates) goes at the end
  of the skill or in a `references/evidence.md` loaded only when a rule looks arbitrary or must be
  re-verified. In the flow an unobserved claim keeps a short `unverified` tag and at most one line of
  reason.
- [ ] Rare cases and caveats go to the end or to a reference, so common-path token cost stays low.
- [ ] Audit each refactor candidate SKILL.md for version numbers, dates and observation history in the main
  flow, together with the SJ-1 / SJ-2 / SJ-3 refactor and the event-keyed playbook idea (999.16):
  ai-kit-session-wake, ai-kit-spec-execute-gsd, ai-kit-spec-execute-superpowers, ai-kit-cross-ai,
  ai-kit-spec-review, ai-kit-gsd-curated-config and the rules family.
- [ ] Proposal (not applied): an AGENTS.md line under the SKILL.md rule: "SKILL.md describes behaviour;
  provenance and version history live in a trailing section or a reference, and version-specific text
  exists only as a conditional."
- [ ] Note to keep: the project rule that reverse-engineered or unverified facts must be visibly flagged
  stays; the flag is a short tag, not a history.
