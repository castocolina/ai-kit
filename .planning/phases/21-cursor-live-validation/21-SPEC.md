# Phase 21: Cursor Live Validation — Specification

**Created:** 2026-10-14
**Ambiguity score:** 0.15 (gate: ≤ 0.20)
**Requirements:** 8 locked

## Goal

The v2 `ai-kit-gsd-curated-config` is shown working from the user's own interactive cursor
session, and cursor's "not live-validated" label is lifted. cursor is found even behind the
user's shell wrapper. ai-kit ships two Cursor executor subagents pinned to non-fast models,
linked by `tools/setup.py`.

## Background

- **The wrapper (verified 2026-10-14).** In an interactive shell, `cursor-agent` is a shell
  function that injects `--model gpt-5.6-sol-high` when no `--model` is given. With a plain env,
  `shutil.which` finds the real binaries on PATH under both names: `~/.local/bin/cursor-agent`
  and `~/.local/bin/agent`, the latter a symlink into
  `~/.local/share/cursor-agent/versions/2026.10.01-e373342/`. Phase 18.1 R1's runtime-id table
  maps `cursor` to both binary names.
- **Cursor subagents** were verified live on 2026-10-13 (todo
  `2026-10-13-add-cursor-subagents-pinned-to-non-fast-composer-2-5-and-grok.md`).
  - The bundle parses `name`, `description`, `model` (default `inherit`),
    `force-default-model`, `readonly`, `background` and `tools`.
  - A per-agent pin `model: composer-2.5` ran with `"model":"composer-2.5"`.
  - The bare `grok-4.7` resolved through the local `~/.cursor/cli-config.json`
    `modelParameters` (this user: `reasoning_effort=high, fast=false`), so a bare id does not
    pin non-fast on another machine.
  - Every non-fast id has a `-fast` twin that spends about 5× the tokens.
- **No name collisions.** `~/.claude/agents` holds the 35 `gsd-*` agents and no
  `composer-*`/`grok-worker`. Cursor also reads `~/.claude/agents`, which is why AGT-01 keeps
  ai-kit's agents in `cursor-agents/` and never in `agents/`.
- **Ownership.** ai-kit owns its own agents (project scope); tools-installer owns third-party
  sets.
- **A user decision is a precondition for planning AGT-01.** The ROADMAP orders it after the
  land-or-shelve decision on branch `worktree-context-tools-manager-plan1` (not merged into
  `main`; it rewrites the same `setup.py`/`wizard_app.py` seams). That decision belongs to the
  user. It blocks planning, not this spec.
- cursor has no gsd-core `RUNTIME_PROFILE_MAP` entry, so its plans always carry overrides
  (17-CONTEXT).

## Requirements

1. **Cursor smoke** (EVAL-07).
   - Current: none.
   - Target: from the user's interactive cursor session, the host-agnostic smoke script (Phases 19/20) installs gsd-core locally and pinned into each scratch project (20 R1). It then runs `inventory`, `recommend`, `apply --dry-run` and a real `apply` on both scratch projects. On ai-kit, only `inventory` and the dry run.
   - Acceptance: `21-SMOKE-CURSOR.md` records the plan, the config, the diff and a forced-failure restore. ai-kit is byte-identical.

2. **Cursor matrix** (APP-05 on cursor).
   - Current: none.
   - Target: the 5 × 35 matrix with `GSD_RUNTIME=cursor`; `model` and `tier` match the plan, and no `-fast` id is chosen automatically.
   - Acceptance: a recorded run with every row passing.

3. **Label lifted** (EVAL-07).
   - Current: SKILL.md says cursor is "not live-validated".
   - Target: the label is removed only after R1 and R2 pass.
   - Acceptance: the SKILL.md diff lands in the same commit as the evidence. `/skill-judge` shows no regression.

4. **Wrapper-proof detection** (SPEC-06).
   - Current: `KNOWN_CLIS` names `cursor-agent` only.
   - Target:
     - Detection resolves cursor by PATH lookup over the runtime-id table's binaries (`cursor-agent`, then `agent`). It never runs an interactive shell and never executes a wrapper.
     - Enumeration runs the resolved real binary with an explicit argv, through a fixture-backed parser of captured `models` output.
     - The resolved real path is recorded in `runtimes.json`.
   - Acceptance: fixtures with only `agent` on PATH, only `cursor-agent`, both, and a shell function of the same name (invisible to the subprocess) resolve correctly. A test proves no shell is spawned. The parser test uses captured output.

5. **Two pinned subagents** (AGT-01).
   - Current: none.
   - Target: `cursor-agents/composer-worker.md` (`model: composer-2.5`) and `cursor-agents/grok-worker.md` (`model: grok-4.7-medium`, explicit, so it does not depend on local `modelParameters`). Each has a short body for executing an already-planned task. The names collide with no GSD agent.
   - Acceptance: a test parses both files' frontmatter (only fields the bundle parses), asserts the pinned ids are non-fast ids from captured `models` output, and asserts no name collides with the 35 GSD agents.

6. **Setup category** (AGT-01).
   - Current: `tools/setup.py` links skills, agents and hooks.
   - Target:
     - A fourth category links `cursor-agents/*` into `~/.cursor/agents`, honoring `CURSOR_CONFIG_DIR`, and reuses the existing link and removal code.
     - The wizard's Choose step lists it only when Cursor is detected (the same detection as the Cursor hook wiring).
     - A headless `--cursor-agents=all|name1,name2` mirrors `--skills`.
   - Acceptance: tests cover the wizard row (shown with Cursor, hidden without), headless all/subset/unknown-name, and `CURSOR_CONFIG_DIR`. The wizard is run under `uv run` before reporting done. Planning waits for the plan1 decision.

7. **Live delegation proof** (AGT-01).
   - Current: verified once by hand (2026-10-13).
   - Target: from a cursor parent session, a delegation to each linked agent shows the pinned model in the Task call. The user confirms one run as non-fast in the Cursor usage dashboard.
   - Acceptance: `21-SMOKE-CURSOR.md` quotes both Task calls' model fields and records the user's dashboard confirmation.

8. **Fixes and gates**.
   - Current: n/a.
   - Target: small, local fixes land here with regression tests (20 D-04 threshold); anything larger becomes a decimal phase. `make test` and `make validate` are green.
   - Acceptance: both gates are green; each fix links its evidence.

## Boundaries

**In scope:**
- The cursor smoke run and matrix, and lifting the label
- Wrapper-proof detection and enumeration
- The two subagents, the setup category, the wizard row and the headless flag

**Out of scope:**
- Overriding Cursor's built-in explore subagent model (a `cli-config.json` user setting; noted in the todo, not shipped)
- Any write to the user's `~/.cursor/cli-config.json`
- pi (Phase 22); codex/opencode (Phase 20)
- The plan1 land-or-shelve decision itself (the user's)

## Constraints

- Never execute the user's shell wrapper; always pass `--model` explicitly to cursor subprocesses.
- Ask before any write to `~/.cursor` beyond the `agents/` links the user selects.
- Pins are explicit non-fast ids, never bare ids that depend on local config.

## Acceptance Criteria

- [ ] The cursor smoke passes on both scratch projects, and ai-kit is unchanged
- [ ] The cursor matrix passes for 5 × 35 with no automatic `-fast` choice
- [ ] The label is removed in the same commit as the evidence
- [ ] Detection finds cursor under either binary name, without a shell
- [ ] Both subagents pin explicit non-fast ids and collide with no GSD agent
- [ ] The setup category, wizard row and headless flag are tested; the wizard was run live
- [ ] Both Task calls show the pinned models; one dashboard check confirms non-fast
- [ ] `make test` and `make validate` are green
- [ ] MUST NOT: never execute the user's `cursor-agent` shell wrapper
- [ ] MUST NOT: a shipped subagent never pins a `-fast` id or a bare id that resolves through local config

## Edge Coverage

**Coverage:** 30/30 applicable edges resolved · 0 unresolved

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | Two scratch projects run in separate dirs; one's backup never touches the other |
| empty | R1 | ✅ covered | A failed local install stops the smoke before `inventory` |
| ordering | R1 | ✅ covered | The dry run always precedes the real apply |
| idempotency | R1 | ✅ covered | A second apply changes nothing but adds a backup |
| concurrency | R1 | 🧪 backstop | Smoke steps are sequential |
| adjacency | R2 | ✅ covered | A specialist override and its tier are checked separately |
| empty | R2 | ✅ covered | `model: ""` is a failure unless inheritance was planned |
| ordering | R2 | ✅ covered | Agents are reported in sorted order |
| empty | R3 | ✅ covered | The label stays when either R1 or R2 has any failing row |
| encoding | R3 | 🧪 backstop | SKILL.md stays valid Markdown after the label removal (skill-judge rerun) |
| empty | R4 | ✅ covered | Neither binary on PATH means cursor is not installed, with no error |
| encoding | R4 | 🧪 backstop | Model ids are parsed as ASCII tokens from captured output |
| adjacency | R4 | ✅ covered | `agent` and `cursor-agent` resolving to one real file are reported once (added by the author) |
| adjacency | R5 | ✅ covered | An id whose `-fast` twin exists is still the non-fast one |
| empty | R5 | ✅ covered | A frontmatter field the bundle does not parse fails the test |
| encoding | R5 | 🧪 backstop | Frontmatter is plain YAML scalars |
| ordering | R5 | 🧪 backstop | Field order in frontmatter is irrelevant to the bundle (test reads by key) |
| concurrency | R5 | 🧪 backstop | Static files; no runtime concurrency |
| adjacency | R6 | ✅ covered | An unknown agent name in `--cursor-agents` exits non-zero naming it |
| empty | R6 | ✅ covered | Without Cursor the wizard shows no row, and the headless flag reports not detected |
| encoding | R6 | 🧪 backstop | Names are matched exactly, as `--skills` does |
| ordering | R6 | 🧪 backstop | The new row follows the existing category order |
| adjacency | R7 | ✅ covered | Both agents are delegated in one session; each Task call shows its own pin |
| empty | R7 | ✅ covered | A Task call without a model field counts as a failure |
| ordering | R7 | 🧪 backstop | The dashboard check follows the recorded runs |
| boundary | R8 | ✅ covered | A fix touching exactly one module stays in-phase; two modules make a decimal phase |
| adjacency | R8 | 🧪 backstop | A fix that changes a CONTEXT decision always becomes a decimal phase |
| empty | R8 | ✅ covered | No fixes needed: the evidence says so explicitly |
| ordering | R8 | 🧪 backstop | A fix's regression test lands in the same commit |
| precision | R8 | 🧪 backstop | The one-module threshold counts Python modules |

## Prohibitions (must-NOT)

**Coverage:** 3/3 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT execute the user's shell wrapper or an interactive shell during detection | R4 | resolved | test |
| MUST NOT ship a subagent pinned to a `-fast` id or a config-dependent bare id | R5 | resolved | test |
| MUST NOT write `~/.cursor/cli-config.json` or any `~/.cursor` file beyond the selected agent links | R6 | resolved | test |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Smoke, detection, two agents |
| Boundary Clarity   | 0.85  | 0.70 | ✓      | plan1 decision and cli-config excluded |
| Constraint Clarity | 0.82  | 0.65 | ✓      | No wrapper, explicit pins |
| Acceptance Criteria| 0.80  | 0.70 | ✓      | 10 pass/fail criteria |
| **Ambiguity**      | 0.15  | ≤0.20| ✓      | Initial 0.21; one round |

## Interview Log

`--auto`, one round. jev-fast-decision screened the open item (Laya first; `needs_fallback` to TypeSafe direct). Summaries only, advisory. Rule: best design over the smallest diff.

| Round | Perspective | Question summary | Laya (advisory) | TypeSafe (advisory) | Decision locked |
|-------|-------------|------------------|-----------------|---------------------|-----------------|
| 1 | Researcher | Is the real cursor binary visible without the wrapper? | – | – | Yes: both names on PATH; the function exists only in interactive shells (R4) |
| 1 | Failure Analyst | Which grok pin is non-fast on every machine? | bare 0.40 (fb) | explicit_medium 0.90 | R5: `grok-4.7-medium` |
| 1 | Boundary Keeper | Does the plan1 branch block this spec? | – | – | No; it blocks AGT-01 planning only. It is the user's decision and goes on the end-of-run ledger |

---

*Phase: 21-cursor-live-validation*
*Spec created: 2026-10-14*
*Next step: /gsd-discuss-phase 21 — implementation decisions (how to build what's specified above)*
