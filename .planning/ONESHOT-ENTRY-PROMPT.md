# ai-kit Phases 9-15 — Claude Code Autonomous Run Driver

**v1.0 (Phase 1.1 through Phase 5) and v1.1 (Phases 6-8) are complete and evidenced.**
Phase 1.1 exercised this playbook's Rule 2 (plan-review convergence) and Rule 6
(clean-room E2E gate) for real while closing itself (`01.1-REVIEWS.md`, that phase's
own `make e2e-docker` run); Phases 1.2-8 closed under the same playbook afterward.
Copy-paste driver for a single autonomous run covering Phase 9 (AGENTS.md Checker
Prune) through Phase 15 (Rules Orchestrator, v1.2's last phase). **Unlike v1.1's
Phases 6-8 (mutually independent, any order fine), v1.2's Phases 9-15 form a strict
dependency chain — 9 → 10 → 11 → 12 → 13 → 14 → 15, each must actually land before the
next is planned** (`.planning/STATE.md`'s Accumulated Context, "v1.2 — strict
dependency chain, unlike v1.1"). Do not parallelize these phases even though
`.planning/config.json` has `parallelization: true` — that setting governs independent
plans within one phase, not this milestone's cross-phase ordering. All operational
detail — cross-AI routing, per-phase checklist, gates, non-negotiable rules — lives in
`.planning/ONESHOT-RULES.md`; this file only starts the run and points there.

**Known risk — opencode provider-credit exhaustion recurred twice during v1.1.**
`.planning/STATE.md`'s Blockers/Concerns section records a billing-driven Rule 7
circuit breaker for Phase 8's execution role and for Phase 6's review role (9 total
failed opencode invocation attempts across both). Confirm opencode provider credits
are restored (`opencode auth list`, a live `opencode run` probe against the primary
and fallback models) before starting this run — the "Cross-AI Execution — Confirm
Reachability" section of `.planning/ONESHOT-RULES.md` governs what to do if a route is
still unreachable.

Every Phase 9-15 `{N}-CONTEXT.md` already exists (gathered 2026-09-13; none of the 7
phases has a plan or execution yet) — this run's first step per phase is
`/gsd-plan-phase {N}`, not `/gsd-discuss-phase`; do not re-discuss a phase whose
`{N}-CONTEXT.md` already reflects it.

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

/gsd-autonomous --to 15 --converge --opencode

You are the Claude Code orchestrator for this ai-kit repository, running v1.2
milestone Phases 9 (AGENTS.md Checker Prune), 10 (Makefile Rules Checker), 11
(Pre-commit Rules Checker), 12 (Architecture Rules Checker), 13 (Docker Rules
Checker), 14 (CI/CD Rules Checker), and 15 (Rules Orchestrator) to completion. v1.0
and v1.1 (Phase 1.1 through Phase 8) are already complete — the cross-AI
plan-review convergence and cross-AI execution routes Phase 1.1 wired are already in
place in `.planning/config.json`; do not re-wire or re-verify that infrastructure,
just use it (after confirming reachability per the Known-risk note above). Phases 9
through 15 form a strict dependency chain — run them in numeric order only, never in
parallel, and never start planning Phase N+1 until Phase N's `VERIFICATION.md` shows
`passed`. Every phase's `{N}-CONTEXT.md` already exists; start each phase at
`/gsd-plan-phase {N}`, not discuss-phase.

Only implement Phases 9 through 15.

Read `.planning/ONESHOT-RULES.md` in full now, and again at the start of every turn,
along with `.planning/STATE.md`, `.planning/ROADMAP.md`, and `.planning/REQUIREMENTS.md`.
Follow `.planning/ONESHOT-RULES.md` exactly — it is the binding playbook, this message
is only the entry point.

Objective: run Phases 9 through 15 to completion, unattended, stopping only for
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
send a continuation command at any point between here and Phase 15's close.

Each of Phases 10, 11, and 14 carries retrofitted shared-package decisions recorded in
more than one phase's `{N}-CONTEXT.md` (Makefile-target/recipe/prerequisite parsing,
precommit-hook parsing, and stack detection all converge into
`skills/_shared/ai_kit_rules_common/` rather than staying skill-local) — read the
cross-referenced `{N}-CONTEXT.md` files named in each phase's own canonical refs before
planning that phase, not just the phase's own file in isolation.

Treat verification as an autonomous convergence loop: any failing test, review
finding, divergent behavior, incomplete evidence, or gap report must be planned,
fixed, re-tested, and independently re-verified until clean. Do not halt merely
because a previous corrective attempt failed; halt only for a real safety/confirmation
condition per `.planning/ONESHOT-RULES.md` Non-Negotiable Rule 7.

If a `gaps_found` verification result appears at any phase, choose "Run gap closure"
yourself and continue the convergence loop described in `.planning/ONESHOT-RULES.md`
Non-Negotiable Rule 8.

▲▲▲ COPY TO HERE ▲▲▲
