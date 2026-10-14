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

## Clarification (user, 2026-10-14): purpose of the prompt research

The prompt-framework research exists so the skill can pick the best-matching execution strategy from what the user states. The outcome may be one, two or three strategies, depending on whether the fit is a `/goal`, a schedule/`/loop`, or OpenGSD autonomous. The skill therefore needs a strategy-selection matrix, not a single template.

Required additions to the skill:
- **Deliverable:** the generated .md must contain a ready-to-copy prompt that the user pastes into a separate agent session; that prompt carries everything needed to reach the objectives.
- **E2E verification:** the file must say how to run e2e tests (real app launch, PTY/TUI drive, browser for web) and require them to pass before declaring done.
- **Jev-assisted decisions** (`jev-fast-decision`, advisory only, never a gate by itself): score how close the delivered work is to the user's objectives, and, when the user supplied a mockup (image or HTML), judge fidelity of the delivered React screen or TUI against it (similar / worse / better, plus UI and experience quality). Jev answers typed questions on supplied text, so image/HTML judgment needs a textual or rendered-description input; verify the feasibility of this before promising it.

## Research: scheduling primitives exposed as system tools (Sonnet subagent, 2026-10-14)

Requirement: the skill must detect which primitives the host actually exposes (tools, not only slash commands) and instruct the LLM to use them, with an OS fallback when none outlive the session.

Claude Code (official docs: code.claude.com/docs scheduled-tasks, goal, routines, tools-reference):
- `CronCreate`/`CronList`/`CronDelete`: 5-field cron, 1 min granularity, session-scoped, max 50, recurring tasks expire after 7 days, restored on `--resume`, no catch-up, dies with the session. Prompt: "every 10 minutes check CI and tell me when it's green".
- `ScheduleWakeup` (self-paced `/loop`): delay 1 min to 1 h, `stop: true` ends it, about 20 min fallback wakeup, not restored on resume.
- `Monitor` and background Bash: stream or deliver output back as a new turn, not restored on resume.
- `/goal`: Stop-hook judged, 4,000 char cap, works headless with `claude -p "/goal ..."`, restored on resume with the turn counter reset. Rate/usage limit pauses it and it resumes after reset; auth failure, exhausted credits or an unavailable model clear it.
- Routines (`RemoteTrigger`, `/schedule`): cloud-run, survive session death, minimum interval 1 h, draw on subscription usage and are rejected when exhausted unless overage is on. Research preview, claude.ai login required.

Others (NOT verified against official docs):
- Codex CLI: `/goal` (v0.128+, third-party blogs; reportedly `goals = true` in config.toml). No cron primitive found; fall back to `codex exec`.
- opencode: no native scheduler; community plugins `@bybrawe/opencode-loop` and `opencode-ralph-loop`, an MCP Cron server, external `opencode run` timers.
- pi: third-party `@jl1990/pi-scheduler` exposes `schedule_task`/`list_scheduled_tasks`/`cancel_scheduled_task` (once/interval/cron, `maxRuns`, `stopOn`, `wakeOn`); persists to `~/.pi/agent/state/scheduler/tasks.json` but needs pi running.
- jcode: nothing found; check the 1jehuang/jcode repo directly.

OS fallback (general knowledge): cron, systemd timers with `Persistent=true`, or `at` running `claude -p --continue`, `codex exec` or `opencode run`. This survives session death and reboot, but retry on quota failure must live in the script.

Key takeaway: in-session primitives die with the process. Anything that must survive quota exhaustion or session death needs an OS timer or a cloud routine. The skill should pick the primitive by what survives, and say so in the generated prompt.

## Clarification (user, 2026-10-14): two distinct quota mechanisms (do not conflate)

The skill and the AGENTS.md directives must keep these separate; each has its own trigger and its own detection.

### A. Session resume (main agent's own quota)

- Applies to the orchestrating session itself. The main agent creates a detached wake-up mechanism (hourly) that re-enters this same session, so work resumes after its own quota runs out.
- Example: created now, quota hit at +15 min, session usable again at +45 min; the wake-up must act on this session (e.g. `claude -p --continue`/`--resume`, or an in-session primitive when it outlives the stall).
- Constraint from the research above: in-session primitives die with the process; prefer an OS timer or cloud routine so the wake-up survives the stall. Which one is detected per host.

### B. Subprocess quota failure (cross-AI child: pi / opencode / cursor / codex)

- Applies when the orchestrator spawns a child agent CLI with a timeout (e.g. 30 min for work that takes about 25).
- Two cases to handle:
  1. Active watching: the limit-reached message is seen in the live stdout/stderr, so react immediately.
  2. Post-hoc: the child hit its timeout, or exited, having done only part of the work. Inspect stdout and stderr for quota, limit-reached or rate-limit patterns before treating it as a plain failure.
- Policy: on a quota signal, retry every 10 min for up to 4 h, until the error stops. Beyond 4 h, stop and report; never loop forever.
- The retry must resume or re-dispatch only the unfinished work, and must check the working tree first, since the child may have left partial edits.
- Needs a per-CLI table of quota/limit message patterns (the todo's "interpret these different messages"); build it from observed outputs rather than guesses, and flag unverified patterns.
