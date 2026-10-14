---
created: 2026-10-14T13:26:53Z
title: AGENTS.md quota-schedule rules and one-shot goal-prompt skill
area: tooling
severity: major
files:
  - skills/ai-kit-project-rules-agents
  - skills/ai-kit-spec-review
  - skills/ai-kit-spec-execute
---

## Problem

Two related requirements.

### 1. Quota-resume directives in the AGENTS.md rules skill

- Add a rule to the AGENTS.md config skill (`ai-kit-project-rules-agents`) that activates only when the project is an OpenGSD project: if an agent fails during cross-AI execution or cross-AI plan-review convergence because of quota (interpret the variants: quota exceeded, limit reached, rate limit, usage cap, "quota X", etc.), the orchestrator must create a schedule instead of failing/retrying blindly.
- The same directive must be built directly into the ai-kit reviewer and executor (`ai-kit-spec-review`, `ai-kit-spec-execute*`), not only emitted into AGENTS.md.
- In all cases: re-check every 10 minutes, capped at 4 hours.
- The same skill must also add a directive for the main agent: always create an hourly schedule that re-activates the session, so work resumes if the session runs out of quota.

### 2. One-shot goal/loop prompt skill (new)

A skill where the user says "I want a goal to complete these roadmap phases / these N superpowers plans". It should:

- Ask a few questions, detect host/runtime/harness (Claude Code, opencode, pi, jcode, Codex; check whether a goal or loop command exists, else list the options).
- Detect GSD/OpenGSD, which phases are in scope, whether spec/discuss files and plans exist (for OpenGSD, plans can be generated from discuss+spec).
- Emit a .md with rails: read the rules file (AGENTS.md), candidate skills to read, definition-of-done verifications, pre-commit enforcement.
- Superpowers plans: the orchestrator owns AGENTS.md rule compliance and deterministic rails, one subagent per plan, goal or loop command as fits, final summary of expected outcome; each execution independent, stopping only when a failure breaks another.
- OpenGSD: reinforce cross-AI convergence per plan (review each plan, cross-AI execution). The settings cross-ai flag is not enough; the planner must put the flag in the plan. Handle projects where cross-AI is not properly configured.
- Emphasize quota handling in both flows (ties to part 1).
- Input: online research (sonnet subagent) of the 3-5 best one-shot goal/loop/autonomous prompts. Results pending from that agent; fold in when it returns.

## Solution

TBD. Part 1 is a new rule in the rules catalog plus reviewer/executor changes; part 2 is a new skill under skills/ that must pass the skill-judge loop. Run /gsd-discuss-phase or /gsd-quick as the AGENTS.md workflow requires.

## Research findings (Sonnet subagent, 2026-10-14; partly third-party, verify before use)

Goal/loop command availability:
- Claude Code: `/goal` (v2.1.139+, official docs, https://code.claude.com/docs/en/goal) and `/loop`. Verified.
- Codex CLI: `/goal` (v0.128+). Third-party blogs only; partly verified.
- opencode, pi, jcode: no built-in goal/loop found. opencode and pi have community Ralph-style wrappers. Unverified.
- `/gsd-autonomous` flags: `--from N`, `--to N`, `--only N`, `--converge`/`--cross-ai`. Stop and resume behavior is undocumented.

Prompt patterns to template in the skill:
1. Verifiable end-state goal: one measurable end state, a check command, constraints, a turn cap, and "stop and report if blocked". `/goal` evaluates the transcript only, so the prompt must make the agent print the proof (max 4,000 chars).
2. Four-element Codex goal: Objective / Scope / Done-when / If-blocked, plus a token budget (advisory, so add a spend backstop).
3. Rules-and-skills-first brief (synthesis, no official source): read AGENTS.md and the spec first, read candidate skills only if relevant, rails, one fresh subagent per plan with the orchestrator verifying, done-when commands, stop-if (same failure 3x or a turn cap), final summary.
4. `/gsd-autonomous --from N --to M --converge`, optionally wrapped in `/goal` to guard on VERIFICATION.md. Existing spec/discuss files are consumed by the planner.
5. Quota-aware resume: on Claude Code, credit exhaustion, auth failure, context overflow or an unavailable model clears the goal; a rate/usage limit pauses it and it resumes on reset; `--resume` restores it but resets counters. Keep state in files and use `/loop` or a cloud routine for schedule-driven resume.

Open: GSD behavior on rate-limit stops; native goal/loop on pi, jcode, opencode.
