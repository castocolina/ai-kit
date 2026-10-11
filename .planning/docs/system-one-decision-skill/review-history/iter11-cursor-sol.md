## Review: 2026-10-10-system-one-provisioning.md; 2026-10-10-system-one-decision-skill.md
### Document Type
Superpowers · plan (both documents)

### HIGH
- **Required execution workflow cannot track the global skill changes** — Location: Decision-skill preamble; Global Constraints; Tasks 0–8. Required: define an execution/checkpoint/review workflow compatible with `/home/bazzite/.claude/skills/jev-fast-decision` being outside Git, or remove the requirement to use Git-dependent execution skills. Why: both required execution skills depend on worktrees, commits, BASE/HEAD diffs, and review packages, while this plan explicitly forbids commits and modifies an untracked external directory.
- **Non-loopback Laya can bypass the consent boundary** — Location: Decision-skill Global Constraints; Task 3 `_send`/`_dispatch`. Required: `_send` must reject a non-loopback Laya URL before opening a socket, with direct `_send` and `_dispatch` tests proving no transmission. Why: `screen()` probes the URL, but direct `_send("laya", …)` treats Laya as permanently local and can send content off-machine without consent.
- **Most of the calibration corpus is unspecified** — Location: Decision-skill Task 5, lines 1030–1058. Required: provide the complete fixed 32-case corpus or a deterministic source from which every omitted case is derived and verified. Why: different implementers can author materially different 26-case datasets, producing different accuracy results and confidence thresholds.
- **Calibration is implemented but never run** — Location: Decision-skill Task 7, Steps 2–5. Required: execute `eval_cases.py --calibrate`, verify the production defaults were updated exactly once, rerun tests, and record the resulting thresholds. Why: the task only implements and tests the command, so Task 7 can finish without calibrating anything.
- **Evaluation fixes can regress untested backends** — Location: Decision-skill Task 8, round-failure `FIX` workflow. Required: after every automated fix, run the complete skill test suite and reject the round if it fails before starting another evaluation. Why: the fixer may edit any skill script, while the following live checks primarily exercise Laya and do not cover TypeSafe/OpenCode behavior.

### MEDIUM
- **System One health-timeout behavior lacks a regression test** — Location: Provisioning Task 7, Step 1. Required: add a test where `/health` never succeeds and verify nonzero exit, the timeout message, and the System One log command. Why: the success test only proves that a health request is attempted, not that an unhealthy container blocks startup.
- **Research cleanup is not resumable** — Location: Provisioning Task 10, Step 1. Required: make removal of the research container, image, and volume succeed when any artifact is already absent. Why: interruption after cleanup makes a resumed Task 10 fail immediately.
- **Laya fixture ordering is implicit** — Location: Decision-skill Task 2, `clean_env` and `laya` fixtures. Required: make `laya` depend explicitly on `clean_env` or otherwise guarantee that its live URL override happens last. Why: sibling pytest fixture setup order is not a dependable contract.

### Cross-Document Consistency
- **Printed skill configuration is not runnable as advertised** — Location: Provisioning Task 7 `print-endpoints`; Decision-skill Global Constraints and Task 6. Required: print a complete activation example including the mandatory kill switch and timeout, or label the current output explicitly as endpoint-selection variables only. Why: `JEV_BACKEND` and `JEV_LAYA_URL` alone always leave `screen()` disabled.

### Status: Issues Found — fix and re-invoke
