# Phase 22: Pi Live Validation - Context

**Gathered:** 2026-10-14 (assumptions mode, `--analyze --all --batch`, jev screening, best over easy)
**Status:** Ready for planning (the L3 spike step needs uz's approval)

<domain>
## Phase Boundary

The v2 curated-config is validated from the user's interactive pi session, pi enumeration is
fixture-backed, and the plan states only the effect the spike proves. The WHAT is locked in
`22-SPEC.md` (R1–R7, amended 2026-10-14). This file locks the HOW.
</domain>

<decisions>
## Implementation Decisions

### What GSD does on pi (R2)
- **D-01: GSD on pi is a gsd-tools bridge plus one request-steering hook.** It spawns no named
  agents and no `pi` subprocesses and installs no agents, commands or skills.
  - `pi/gsd.cjs:290-310` (`runHook` spawns only `node hook.js`), `:318-380` (`/gsd` and
    `gsd_invoke` call `dispatchGsdCommand`); `install.js:11603-11612, 11784-11797`.
  - A scratch `--pi --local` install under a temp HOME produced only `.pi/extensions/gsd.js`,
    `.pi/gsd-core/` (marker `pi`), `.pi/gsd-hooks/` and `.pi/scripts/`.
- **D-02: The verdict vocabulary gains "session-steer (sonnet key only)"** with per-key labels
  (SPEC R2 amended).
  - The hook registers with no tier argument (`gsd.cjs:386`), defaults to `sonnet` (`:233`),
    and replaces the payload `model` verbatim (`:265-272`). It fails open unless `pi.sonnet` is
    set.
  - A localhost mock provider (temp HOME) put the override on the wire; `pi.opus` alone left it
    unchanged; without `--approve` the project extension did not load, silently.
  - Laya fourth_verdict 0.94.
- **D-03: The spike climbs an evidence ladder, and records the trust state of every run.**
  - L0 static source; L1 a fake-ExtensionAPI handler probe; L2 a localhost mock provider that
    logs the wire `model`; L3 one tiny real run comparing `message.model` with
    `message.responseModel` in the session JSONL, with and without the override.
  - Only L3 spends a model call, and it needs uz's approval.
  - `resolve-model` is not an oracle on pi: under the copied `resolve_model_ids: "omit"` it
    returns `model: ""` while the hook still steers.

### Enumeration (R1)
- **D-04: The source is pi's RPC `get_available_models`** (amends 18 D-25 and SPEC R1).
  - argv: `pi --mode rpc --offline --no-session --no-extensions --no-skills
    --no-context-files --no-mcp`, one JSON command on stdin, stdin closed after the response,
    with the 18.1 supervisor's timeout. Live: 0.17 s, 85 models, 0 mismatches against the table.
  - It carries exact `contextWindow`/`maxTokens`, `input` (to `image_input`) and
    `thinkingLevelMap` (to `reasoning_modes`). The table rounds with `toFixed(1)` (41 of 42
    decimal cells lossy) and exits 0 on every failure mode.
  - A pure `parse_pi_models(stdout)` plus a thin `detect_pi_models`, as for codex. The fixture is
    a trimmed capture with `baseUrl` values removed.
  - Laya hybrid 0.46 (fb), TypeSafe rpc_source 0.75.

### Honest plans (R3, R5)
- **D-05: A pi plan writes no `model_overrides.*`, no `pi.opus`, no `pi.haiku`.** If the
  verdict is session-steer, it offers one `model_profile_overrides.pi.sonnet` as an opt-in
  `needs_choice`, limited to bare model ids served by the session's active provider, labelled
  "steers every request in this project's pi session".
  - The hook passes the value unvalidated; a `provider/model` candidate (e.g.
    `router-env/my-coding`) would break every request. Bare ids repeat across providers.
  - **Own reasoning** (Laya fill_all 0.74 contradicted the evidence; TypeSafe second opinion
    opt_in_bare 0.53 fb). Ledger.
- **D-06: `agent_skills.*` and other agent-bound keys are labelled `no effect on pi (no GSD
  agent files installed)`** (amends SPEC R3 and 17 D-22). Inferred from the missing agent
  files; the L3 run should confirm. GSD's `skills-root pi` returns only `~/.pi/agent/skills`
  while pi also loads `~/.agents/skills`: filed as an R7 finding against 18 D-31. Laya 0.73.
- **D-07: The pi matrix asserts tier equality from the independent oracle (19 D-10), `model ==
  ""` under `omit`, and five handler probes (one per combination) for the effect.** The oracle
  is host-parameterized: `omit` is the installer's intended state on pi, not poison.

### Smoke and preconditions (R4, R6)
- **D-08: The pi installer runs under a temp HOME;** 19 D-14's sha256 guard on the real
  `~/.gsd/defaults.json` stays the assertion (`writeNonClaudeDefaults` ignores `GSD_HOME`).
  Phase 17's host-first gsd-core resolver adds `<project>/.pi/gsd-core` and
  `$PI_CODING_AGENT_DIR|~/.pi/agent/gsd-core`; otherwise pi silently resolves claude's tree.
- **D-09: Phase 22 also live-verifies `PI_CODING_AGENT`** (labelled source-inspected at
  `detection.py:83-86`) from the interactive session and updates the label, as 20 D-05 does for
  codex.
- **D-10: The user script loads the skill with `pi --skill <path>`** (no `~/.pi/agent` change),
  tells the user to pick a model first (the default `openai-codex` login is gone), and treats
  the project-trust prompt as the user's consent action.

### Claude's Discretion
- Probe script names; the order of L0–L2 within the spike.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/phases/22-pi-live-validation/22-SPEC.md` (amended R1–R3)
- `.planning/phases/17-curated-config-inventory-recommendation-engine/17-CONTEXT.md` D-21, D-22
- `.planning/phases/18-cross-ai-skills-apply-pipeline/18-CONTEXT.md` D-25, D-31, D-37
- `.planning/phases/19-evaluation-on-claude/19-CONTEXT.md` D-08..D-14
- gsd-core 1.16.0 (npx cache): `pi/gsd.cjs`, `bin/install.js:6963-7012, 11603-11612, 11784-11797`, `bin/lib/capability-registry.cjs:3186-3209`
- pi 1.2.0: `dist/core/extensions/runner.js:1068-1103`, `docs/rpc-commands.md:252-270`, `docs/security.md`, `docs/environment-variables.md`
</canonical_refs>

<code_context>
## Existing Code Insights

- `detection.py:144-199` (codex parser split) and `tests/test_ai_kit_spec.py:105-125` (fixture provenance) are the precedents for D-04.
- `gsd_catalog.py:16-33` has no pi root and no project-local roots (D-08).
</code_context>

<specifics>
## Specific Ideas

- Open for research: steering on a real provider (anthropic, opencode-go, radius, router-env) and whether the router accepts `provider/model` as `model`; whether pi persists project trust under `~/.pi/agent`; the meaning of a null `thinkingLevelMap`; upstream gsd-core's hard-coded sonnet tier and the `omit` vs hook disagreement.
- The analyzer's scratch `rpc-real.json` holds router `baseUrl` values: never commit it.
</specifics>

<deferred>
## Deferred Ideas

- Writing GSD agent files for pi's own subagent extension stays out of scope (SPEC Boundaries).
</deferred>

---

*Phase: 22-pi-live-validation*
*Context gathered: 2026-10-14*

## Orchestrator rulings on 22-RESEARCH.md open questions (2026-10-23)

- **Q1 (agent-run L2 mock provider and headless pi smoke):** yes, only inside a scratch
  `PI_CODING_AGENT_DIR` with no real credentials and a local mock provider; nothing leaves the
  machine. Ladder: Laya A 0.97, consistent with the owner's scratch-HOME rule.
- **Q2 (real 85-model capture):** owner-run. It needs the real pi agent directory, which the run
  never reads; the plan ships the parser against a trimmed fixture the owner refreshes.
- **Q3 (L3 provider arms):** owner-run (real model calls, approval); the plan records the verdict
  as `session-steer (static + mock evidence)` until the owner's L3 run upgrades or refutes it.
- **Q4 (context window / max output in the snapshot):** carry the exact integers and bump
  `RUNTIMES_SCHEMA_VERSION` with a migration test (R1 names both fields). Ladder: Laya A 0.82.
- **Q5 (`_PI_SKILL_SKIP` text cites gsd-core 1.16.0):** re-check against the installed 1.17.0 and
  update the cited version only where the behaviour is unchanged.
- **Q6 (upstream hook steers the `sonnet` tier only):** a documented limitation; labels say opus
  and haiku are inert on pi. No upstream change in this phase.
- Skill-judge for the changed SKILL.md: judge the pre-change digest first (no baseline exists for
  the new lane), then the post-change digest, with the owner's judge set (one clean-context
  native Opus subagent + opencode `router-env/my-plan-review`).
