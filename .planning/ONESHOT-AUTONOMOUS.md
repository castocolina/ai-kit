# ai-kit Phases 1.1-5 — Claude Code Autonomous Run Driver

**Phase 1.1 has exercised this playbook's Rule 2 (plan-review convergence) and Rule 6 (clean-room E2E gate) for real while closing itself — see `01.1-REVIEWS.md` and this phase's own `make e2e-docker` run. Phases 1.2 through 5 have not yet run under this playbook; treat those sections as reviewed-but-unexercised until each phase actually closes.** Copy-paste driver for a single autonomous run
covering Phase 1.1 (Autonomous-Run Infrastructure) through Phase 5 (Usage Metrics
Dashboard). All operational detail — cross-AI routing, per-phase checklist, gates,
non-negotiable rules — lives in `.planning/ONESHOT-RULES.md`; this file only starts
the run and points there.

## How To Run

From the repository root, in a fresh Claude Code session:

```sh
claude --dangerously-skip-permissions
```

`--dangerously-skip-permissions` is required so the session doesn't stall on a
tool-permission prompt partway through an unattended run — the real safety gates for
this run are `.planning/ONESHOT-RULES.md`'s own Non-Negotiable Rules (rules 4 and 6),
not Claude Code's generic per-call confirmation.

Paste the block below as the first message, then leave it running.

---

▼▼▼ COPY FROM HERE ▼▼▼

/gsd-autonomous --to 5 --converge --opencode

You are the Claude Code orchestrator for this ai-kit v1.0 milestone: Phase 1.1
(Autonomous-Run Infrastructure) through Phase 5 (Usage Metrics Dashboard). Phase 1.1
itself wires the cross-AI plan-review convergence and cross-AI execution routes this
run depends on — do not skip it, and do not plan Phase 1.2 until Phase 1.1's success
criteria are all evidenced.

Only implement through Phase 5.

Read `.planning/ONESHOT-RULES.md` in full now, and again at the start of every turn,
along with `.planning/STATE.md`, `.planning/ROADMAP.md`, and `.planning/REQUIREMENTS.md`.
Follow `.planning/ONESHOT-RULES.md` exactly — it is the binding playbook, this message
is only the entry point.

Objective: run Phase 1.1 through Phase 5 to completion, unattended, stopping only for
a real destructive anomaly, an unrecoverable tool/authentication failure, or a circuit
breaker (`.planning/ONESHOT-RULES.md` Non-Negotiable Rule 7). Never trust a subagent's
or delegate's self-reported "passed" — independently re-run the real verification
commands yourself before advancing any phase (Rule 1). Never run `tools/install.sh`,
`tools/setup.py`'s wizard, or any config-doctor apply against uz's real
`~/.claude`, `~/.cursor`, `~/.config/opencode`, or `~/.codex` during verification —
this project's own core value ("never corrupt uz's AI-CLI configuration") is the
single highest-risk surface in this repo; every verification run uses a scratch
`HOME`/`CLAUDE_CONFIG_DIR`/`AI_KIT_DIR` or the `make e2e-docker` clean-room harness,
never the real machine's real config (Rule 5). Defer everything a human needs to see
to the end-of-phase UAT report (`workflow.human_verify_mode: "end-of-phase"`) and this
run's final report — uz reviews once, after waking up, not mid-run. Do not ask uz to
send a continuation command at any point between here and Phase 5's close.

Treat verification as an autonomous convergence loop: any failing test, review
finding, divergent behavior, incomplete evidence, or gap report must be planned,
fixed, re-tested, and independently re-verified until clean. Do not halt merely
because a previous corrective attempt failed; halt only for a real safety/confirmation
condition per `.planning/ONESHOT-RULES.md` Non-Negotiable Rule 7.

If a `gaps_found` verification result appears at any phase, choose "Run gap closure"
yourself and continue the convergence loop described in `.planning/ONESHOT-RULES.md`
Non-Negotiable Rule 8.

▲▲▲ COPY TO HERE ▲▲▲
