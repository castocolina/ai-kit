# Phase 25 owner capture kit

Follow-up 2026-11-02: see .planning/milestones/v1.3-OWNER-FOLLOWUP.md

## Purpose

Turn the `unverified` pattern rows of the runner's failure ladder into evidence. Each item below
is a fact only a live vendor run can give, so it ships unverified. Nothing in this kit blocks
Phase 25: the phase closes with every result `not run (owner)`.

## Safety

- Capture only your own failing runs, as they happen. Never provoke a limit on purpose and never
  run a capture against someone else's account.
- Raw captures live under `tmp/` (gitignored) and are deleted once the check is done. Never
  commit a raw body, and never paste one into a planning file.
- Before anything else, replace every key, token, account id and URL in the capture with
  `<redacted>`. Do this on the copy you keep, before the classify check.
- Finish with a secret scan over what is kept. List the files only; never print matching lines:
  `rg -l -i 'sk-|token|key' tmp/`. Any hit means the redaction is incomplete: delete the file and
  start that capture again.

## How to check a capture

Write a one-case JSON file in the `--classify-only` shape, a JSON array of objects
`{name, cli, model?, route?, stderr?, stdout?}`, using the redacted text:

```bash
node skills/ai-kit-spec-review/references/cross-ai.mjs --classify-only <file>
```

It prints one JSON line per case (`name`, `status`, `rule`, `pattern`, `route`), spawns nothing
and writes nothing. Compare `status` and `pattern` with the pass rule of the item.

## Items

### C1 — cursor limit channel

What to capture: one cursor run under `-p --output-format json` that hits a usage limit. Record
whether the limit text arrives on stderr or inside a result event, the process exit code, and
whether a `session_id` is present.

Steps: keep the raw transcript under `tmp/`, redact it, then run the classify check with
`cli` `cursor`.

Pass rule: the record names the channel, the exit code and the `session_id` presence, and the
classify check's `status` matches the row the text should hit.

Result: not run (owner)

### C2 — pi weekly limit

What to capture: the exact wording pi prints for the weekly limit on the `zai-coding-cn` lane.
Today that lane is classified `transient` / `capacity` because the message text was never saved.

Steps: redact, then classify with `cli` `pi`.

Pass rule: the exact wording is recorded, and the classify check shows whether it lands on a
limit row or stays `transient`.

Result: not run (owner)

### C3 — router bodies

What to capture: real router error bodies for `MonthlyLimitError`, the Zen `Model access is
disabled` text and the Go `Insufficient account funds` text, and whether any body names the combo
member that served the request.

Steps: redact every body, then classify each with `route` `router`.

Pass rule: each body is recorded redacted, the member-naming question is answered yes or no, and
each classify check names its `pattern`.

Result: not run (owner)

### C4 — claude wording and channel

What to capture: claude's `Overloaded` wording and its `resets <time> (<zone>)` wording, and which
channel (stdout or stderr) each arrives on.

Steps: redact, then classify with `cli` `claude`.

Pass rule: both wordings and their channels are recorded, and the classify check's `status` is
noted for each.

Result: not run (owner)

### C5 — codex reconnect

What to capture: a codex transcript where a bare `error` event is followed by a successful turn,
so the question of whether a bare `error` is terminal gets a real example.

Steps: redact the transcript and note the event order. The classify check is optional here: the
question is about event order, not about one error line.

Pass rule: the transcript shows an `error` event with a completed turn after it, or the capture
states that no such transcript was found.

Result: not run (owner)

### C6 — router recovery time

What to capture: how long a router quota lane takes to recover, from the failing run to the first
run that succeeds again. This informs `cooldownS` (default 600) and nothing else.

Steps: note the two timestamps. No classify check applies.

Pass rule: the elapsed time is recorded, or the capture says the lane had not recovered yet when
observation stopped.

Result: not run (owner)

### C7 — owner confirmation of the orchestrator interpretations

What to confirm, each one a yes or no with a correction if no:

- Auth (401/403) stops without retry, and off-router quota stops (A2).
- Cooldown cycles span runner calls (A4 as amended by the 2026-10-24 cycle-1 ruling): the runner
  exits 75 with `retry_after_s=` and `cycle=`, and the caller waits and re-invokes the same lane.
  The cycles never stay inside one runner call.
- Whether the router-tail `[401]` and missing-credential rows are quota-wait or stop under the
  owner's step 3 (25-06 A2).
- The timeout reading: a call-deadline timeout carrying a quota signal classifies as that signal,
  and a quota-free timeout is a transient rung only while the deadline admits one.
- The review-mode rung-1 reading: a review lane continues its captured session on rung 1.
- Pre-dispatch candidate selection and rounds 4-5 escalation stay (A1).
- Whether the owner accepts a skill scheduling the one-shot `CronCreate` consumer, the single
  re-invoke and nothing more.
- Whether review lanes re-invoking the same confirmed-router lane at `retry_after_s` (the 25-10
  caller contract) is the intended behavior.

Steps: answer in writing. No capture and no classify check.

Pass rule: every bullet has an answer.

Result: not run (owner)

## Results

- C1: not run (owner)
- C2: not run (owner)
- C3: not run (owner)
- C4: not run (owner)
- C5: not run (owner)
- C6: not run (owner)
- C7: not run (owner)

## Close-out

When results land, run `/gsd-plan-phase 25 --gaps` to add fixtures from the captures, flip the
matching labels from `unverified` to `verified`, rerun the runner self-test, and run skill-judge
for any SKILL.md the fixtures changed.

## Phase status

2026-10-25, phase tip after 25-11 (logs in `tmp/p25/11/`, removed after the SUMMARY):
- Gates: ruff, pyright, vulture, `make test`, `make validate` and the clean-room
  `make e2e-docker` all exit 0. The container ran with `--rm`, and no e2e build process,
  runner self-test fake or scratch-rooted `node` process survived.
- QTA-01, QTA-02 and QTA-03 are ready for `/gsd-verify-work 25`.
- `human_needed`: C1-C7 above (every result still `not run (owner)`), plus the unverified
  pattern rows.
- **Skill-judge gate (round 6, 2026-10-25, all three judges completed):** spec-review PASS (102
  against base 97). execute-gsd (96 against 104), execute-superpowers (84, two Criticals fixed
  after the round, against 110) and curated-config (103 against 106) are UNRESOLVED on the
  no-regression bar only. Whether the old bases stay the bar is the owner's decision.
- Next: `/gsd-secure-phase 25`, then the verifier, then the merge to local main and
  `tools/setup.py install` once the gate clears. Any push needs the owner's consent.
