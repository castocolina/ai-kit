# Phase 22: Pi Live Validation — Specification

**Created:** 2026-10-14
**Ambiguity score:** 0.17 (gate: ≤ 0.20)
**Requirements:** 7 locked

## Goal

The v2 `ai-kit-gsd-curated-config` is shown working from the user's own interactive pi session,
and pi's "not live-validated" label is lifted. `detect-runtimes` enumerates pi models through a
fixture-backed parser. The phase settles, with live evidence, whether per-agent models take
effect on a pi host at all, and the plan says only what was proven.

## Background

- **pi 1.2.0** is at `~/.bun/bin/pi`. `pi --list-models` prints a table with the columns
  `provider  model  context  max-out  thinking  images`. On 2026-10-14 it listed 85 models:
  anthropic 17, opencode-go 31, radius 29, router-env 4 and xai 4. The openai-codex login is
  gone (pi repair belongs to tools-installer).
- **gsd-core 1.16's capability registry** declares the pi host as follows:
  - `dispatch.namedDispatch: false`, `nested: false`, `maxDepth: 0`;
  - `subagentToolkit: "undocumented"`;
  - `installSurface: "profile-marker-only"` with `pluginOnlyInstall: true`: one extension,
    `extensions/gsd.js`, and no agent files.

  GSD therefore does not spawn named subagents on pi. `RUNTIME_PROFILE_MAP.pi` exists and maps
  to anthropic ids (`claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5`).
- **pi's own subagent extension** (`~/.pi/agent/extensions/subagent`) spawns
  `pi --mode json -p --no-session [--model M] …` per agent, with frontmatter `model` mapped to
  `--model` (research 07). The user's `~/.pi/agent/agents/` holds their own agents (planner,
  reviewer, scout, worker, sdd-*), not GSD agents.
- **The ROADMAP criterion assumed per-agent `pi --model` wiring "via the subagent extension".**
  The registry contradicts that, so this phase verifies it first. The criterion is amended to
  the verified outcome (Interview Log).
- **Inherited contracts:** the smoke script and the local, pinned gsd-core per scratch project
  (Phases 19/20 R1), the runtime-id table with `pi` (18.1 R1), and pi as the first cross-AI
  execution target (18 R3).

## Requirements

1. **pi enumeration** (SPEC-05, delivered by Phase 18 as of 2026-10-14; this phase re-verifies it live and extends it).
   - Current: Phase 18 adds the parser (18 D-25).
   - Target: `detect-runtimes` runs `pi --list-models` (argv, host-signal scrub) and parses the table into candidates. Each candidate carries `provider/model`, context, max output, thinking (to `reasoning_modes`) and images (to `image_input`). `pi` is in the runtime-id table.
   - Acceptance: a parser test on captured output (header, aligned columns, the `K`/`M` suffixes, yes/no flags) yields 85 entries with the right provider split. An empty or garbled output gives a structured error, not a crash.
   - *Amended 2026-10-14 (22 D-04):* the source is pi's RPC `get_available_models` (`pi --mode rpc --offline --no-session --no-extensions --no-skills --no-context-files --no-mcp`), which returns the same 85 models with exact `contextWindow`/`maxTokens` and per-model `thinkingLevelMap`. The table's `K`/`M` cells are lossy (`toFixed(1)`), and every table failure mode exits 0. Acceptance: a parser test on a trimmed RPC capture (no `baseUrl` values) yields 85 entries with exact integers; an empty list, a non-JSON line or a missing response is a structured error.

2. **Per-agent model spike**.
   - Current: assumed, not verified.
   - Target: a live spike on a scratch project with GSD installed locally for pi shows how GSD agents run on a pi host. Either:
     - they run inline in the main session (as `namedDispatch: false` implies), or
     - some mechanism runs a named agent with its own model.

     It records which `resolve-model` keys, if any, change the model a GSD step actually uses.
   - Acceptance: `22-SPIKE-PI-AGENTS.md` shows the observed spawn commands or their absence, the model actually used per step, and a verdict: per-agent effective, tier-only effective, or inert.
   - *Amended 2026-10-14 (22 D-01, D-02):* a fourth verdict, **session-steer (sonnet key only)**, is added with per-key labels. Static and mock evidence: GSD on pi spawns nothing; its one `before_provider_request` hook replaces the wire `model` with `model_profile_overrides.pi.sonnet` on every request of a trusted project's session; `pi.opus`, `pi.haiku` and per-agent `model_overrides` are inert. The unit of "model actually used" is the session request (`message.model` vs `message.responseModel` in the session JSONL).

3. **Honest plans on pi**.
   - Current: Phase 17 would write overrides for a pi host like any other host.
   - Target: until R2 proves an effect, a pi-host plan writes no per-agent `model_overrides`, and every model-layer entry for pi carries `effect unverified on pi (gsd-core registry: namedDispatch false)`. After R2, the label and the rule follow the verdict.
   - Acceptance: golden pi plans match the verdict, and a test pins the label text while it applies.
   - *Amended 2026-10-14 (22 D-05, D-06):* `agent_skills.*` (and other agent-bound keys) are labelled `no effect on pi (no GSD agent files installed)` too. If the verdict is session-steer, the plan offers only `model_profile_overrides.pi.sonnet` as an opt-in `needs_choice` limited to bare ids of the session's active provider, labelled session-wide.

4. **pi smoke** (EVAL-08).
   - Current: none.
   - Target: from the user's interactive pi session, the host-agnostic smoke installs gsd-core locally and pinned into each scratch project, then runs `inventory`, `recommend`, `apply --dry-run` and a real `apply` on both scratch projects. On ai-kit, only `inventory` and the dry run.
   - Acceptance: `22-SMOKE-PI.md` records the plan, the config, the diff and a forced-failure restore. ai-kit is byte-identical.

5. **pi matrix** (APP-05 on pi).
   - Current: none.
   - Target: the 5 × 35 matrix runs with `GSD_RUNTIME=pi`. It asserts what R2 proved: `model` and `tier` match the plan where an effect exists, and the label otherwise.
   - Acceptance: a recorded run consistent with the R2 verdict.

6. **Label lifted** (EVAL-08).
   - Current: SKILL.md says pi is "not live-validated".
   - Target: the label is removed only after R4 and R5 pass. SKILL.md states the R2 verdict for pi.
   - Acceptance: the SKILL.md diff lands with the evidence. `/skill-judge` shows no regression.

7. **Fixes and gates**.
   - Current: n/a.
   - Target: small, local fixes land here with regression tests (20 D-04 threshold); larger ones become decimal phases. `make test` and `make validate` are green.
   - Acceptance: both gates are green; each fix links its evidence.

## Boundaries

**In scope:**
- pi enumeration, the per-agent spike, honest pi plans, the smoke and the matrix, lifting the label

**Out of scope:**
- Writing GSD agent files for pi's subagent extension, unless R2 proves GSD would use them (TypeSafe 0.89 against building the wiring first)
- pi auth repair, extension sync and router-env defects: tools-installer and llm-env (2026-10-13 hand-offs)
- cursor (Phase 21), codex/opencode (Phase 20)

## Constraints

- Never modify `~/.pi/agent` without consent; scratch projects use a local GSD install.
- Never print `auth.json` content or any key.
- Labels state only verified effects (core value).

## Acceptance Criteria

- [ ] The pi parser yields 85 entries from captured output, with `image_input` and `reasoning_modes`
- [ ] The spike verdict is recorded with the evidence
- [ ] pi-host plans carry no per-agent overrides and are labelled until the verdict proves an effect
- [ ] The pi smoke passes on both scratch projects, and ai-kit is unchanged
- [ ] The pi matrix is consistent with the verdict
- [ ] The label is removed with the evidence, and SKILL.md states the verdict
- [ ] `make test` and `make validate` are green
- [ ] MUST NOT: a pi-host plan never claims a per-agent model effect that was not verified
- [ ] MUST NOT: no `auth.json` content or key appears in output or evidence

## Edge Coverage

**Coverage:** 32/32 applicable edges resolved · 0 unresolved (floor recomputed 2026-10-14 after the R1–R3 amendments)

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| boundary | R1 | ✅ covered | ~~A row with exactly six columns parses~~ *(superseded, D-04)* A response with exactly one `get_available_models` result parses; a second or missing result is a structured error |
| adjacency | R1 | ✅ covered | Two providers serving the same model name stay distinct `provider/model` entries |
| empty | R1 | ✅ covered | ~~Header only~~ *(superseded, D-04)* An empty `models` array yields an empty list, not an error |
| ordering | R1 | 🧪 backstop | Entries keep the CLI's order; consumers sort |
| concurrency | R1 | 🧪 backstop | One RPC process per enumeration; closing stdin ends it and the supervisor kills it on timeout |
| precision | R1 | ✅ covered | ~~`1M`/`128K`/`200K` parse to exact integers~~ *(superseded, D-04)* `contextWindow`/`maxTokens` are exact JSON integers |
| adjacency | R2 | ✅ covered | Runs with and without the override differ only in the wire `model`; selection (`message.model`) and served model (`responseModel`) are recorded side by side |
| concurrency | R2 | 🧪 backstop | Spike rungs run one at a time, one mock provider per run, killed afterwards |
| empty | R2 | ✅ covered | With no override set the hook fails open and the wire model equals the selection |
| encoding | R2 | 🧪 backstop | Model ids are compared as exact strings; the hook passes them verbatim |
| ordering | R2 | 🧪 backstop | Rungs run L0 → L3; L3 only after approval |
| adjacency | R3 | ✅ covered | A tier-only verdict keeps tier entries and still writes no per-agent overrides |
| empty | R3 | ✅ covered | With no verdict yet, every pi model-layer entry carries the label |
| encoding | R3 | 🧪 backstop | The label text is pinned verbatim by a test |
| ordering | R3 | 🧪 backstop | Entries stay sorted by key |
| boundary | R3 | ✅ covered | Exactly one opt-in key (`pi.sonnet`) is offered; `pi.opus`/`pi.haiku` are never written |
| concurrency | R3 | 🧪 backstop | Plans are pure functions of the inventory, with no shared state |
| precision | R3 | ✅ covered | The label text is pinned verbatim; the opt-in value is a bare id matched exactly against the session provider's list |
| adjacency | R4 | ✅ covered | Two scratch projects run in separate dirs |
| empty | R4 | ✅ covered | A failed local install stops the smoke before `inventory` |
| ordering | R4 | ✅ covered | The dry run always precedes the real apply |
| idempotency | R4 | ✅ covered | A second apply changes nothing but adds a backup |
| concurrency | R4 | 🧪 backstop | Smoke steps are sequential |
| empty | R5 | ✅ covered | `model: ""` passes only where the verdict says inert and the plan promised no model |
| encoding | R5 | 🧪 backstop | The matrix report is plain text, stable order |
| empty | R6 | ✅ covered | The label stays when any of R4/R5 fails |
| encoding | R6 | 🧪 backstop | SKILL.md stays valid after the edit (skill-judge rerun) |
| boundary | R7 | ✅ covered | A fix touching exactly one module stays in-phase; two modules make a decimal phase |
| adjacency | R7 | 🧪 backstop | A fix that changes a CONTEXT decision becomes a decimal phase |
| empty | R7 | ✅ covered | No fixes needed: the evidence says so explicitly |
| ordering | R7 | 🧪 backstop | A fix's regression test lands in the same commit |
| precision | R7 | 🧪 backstop | The one-module threshold counts Python modules |

## Prohibitions (must-NOT)

**Coverage:** 2/2 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT claim a per-agent model effect on pi that was not verified | R3 | resolved | test |
| MUST NOT print `auth.json` content or any key | R1, R4 | resolved | judgment |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.85  | 0.75 | ✓      | Spike outcome open by design |
| Boundary Clarity   | 0.85  | 0.70 | ✓      | tools-installer/llm-env hand-offs named |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Verified-only labels |
| Acceptance Criteria| 0.78  | 0.70 | ✓      | 9 pass/fail criteria |
| **Ambiguity**      | 0.17  | ≤0.20| ✓      | Initial 0.27 (registry contradicted the roadmap); one round |

## Interview Log

`--auto`, one round. jev-fast-decision screened the open item (Laya first; `needs_fallback` to TypeSafe direct). Summaries only, advisory. Rule: best design over the smallest diff.

| Round | Perspective | Question summary | Laya (advisory) | TypeSafe (advisory) | Decision locked |
|-------|-------------|------------------|-----------------|---------------------|-----------------|
| 1 | Researcher | What does `pi --list-models` print? | – | – | A 6-column table, 85 models (R1) |
| 1 | Failure Analyst | gsd-core's registry says pi has no named dispatch. What does the phase require? | build_wiring 0.47 (fb) | verify_then_label 0.89 | R2 spike first; R3 honest labels; ROADMAP SC1 amended to the verified outcome |

---

*Phase: 22-pi-live-validation*
*Spec created: 2026-10-14*
*Next step: /gsd-discuss-phase 22 — implementation decisions (how to build what's specified above)*
