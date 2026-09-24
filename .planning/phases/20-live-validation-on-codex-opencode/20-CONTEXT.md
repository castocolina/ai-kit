# Phase 20: Live Validation on Codex + Opencode - Context

**Gathered:** 2026-09-23
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase proves the v2 `ai-kit-gsd-curated-config` works from **real codex and opencode host
sessions**:
- EVAL-04: live smoke from codex, plus live confirmation of the codex env signal;
- EVAL-05: live smoke from opencode, plus settling whether the opencode review lane is usable
  from an opencode host;
- fixing what surfaces, under D-05's threshold.

Cursor and pi are out of scope (Phases 21/22).

</domain>

<decisions>
## Implementation Decisions

### Carried forward (locked elsewhere — do not re-decide)
- **19 D-03:** a real `apply` runs only on scratch projects (a copy of this repo's
  `.planning/config.json`, plus an empty project). On ai-kit itself, only `inventory` and
  `apply --dry-run`.
- **19 D-04/D-05:** the 5-combination `resolve-model` matrix for 35 agents, run with
  `GSD_RUNTIME=codex` and `GSD_RUNTIME=opencode` here, recorded as live evidence.
- **17 D-02:** codex's native sol/terra/luna slots are kept when valid; opencode's
  `anthropic/*` slots get overridden.
- **17 D-04:** the user's routers win the slot for their declared role.

### Driving the hosts
- **D-01:** **Headless iteration first, then a final interactive run.**
  - Iterate and fix using headless runs launched from the Claude session (`codex exec …`,
    `opencode run …`) with a **cleaned env**: remove `CLAUDECODE` and other outer-host signals.
  - Only the user's **own interactive session** in each host counts as the EVAL-04/EVAL-05
    evidence.
  - For that run, give the user a short script (steps and prompts to paste). Afterwards,
    analyze the artifacts it leaves: `plan.json`, the resulting `config.json`, the smoke log and
    the `resolve-model` output.
  - When a headless dispatch is killed or hangs, follow the user's memory rule: probe with a
    short foreground run that polls output growth before retrying.
  - Known transient blockers: opencode's xai/grok lane billing block (2026-09-14) and opencode's
    sandbox denying `external_directory` access to `~/.claude/gsd-core` (v1.1 Phase 07). If
    either recurs, record it as an environment finding, not a skill bug.

### Host precedence (amends 16 D-01)
- **D-02:** The host order becomes **pi > opencode > cursor > codex > claude**, with claude
  last.
  - Rationale: env signals are inherited, and Claude is the user's usual **outer**
    orchestrator (it dispatches cross-AI review/execution to codex and opencode). A codex
    launched from Claude carries `CLAUDECODE`, and under the previous order it would read as
    claude.
  - The reverse nesting (claude launched from codex) is rare for this user and is accepted as a
    known limitation, documented in the detection docstring.
  - Headless runs also clean the env (D-01), as belt and braces.
  - Phase 16 has not been planned yet, so this is a free change. 16-CONTEXT D-01,
    REQUIREMENTS SPEC-01 and the ROADMAP Phase 16 success criteria are updated to match.
  - **Reversibility:** costly — the same reasoning as 16 D-01.

### opencode model application (amends 18 D-05)
- **D-03:** On an opencode host, the models written by `apply` only take effect through a
  **local (project) gsd install**.
  - Evidence: gsd-core `install-model-override-resolver.cjs` bakes models into agent frontmatter
    at install time. It merges `<project>/.planning/config.json` only when the install target is
    inside a project. A global install (`~/.config/opencode/agents`, the user's current gsd
    1.13.0, agents with no `model:` line) reads only `~/.gsd/defaults.json`.
  - So the opencode follow-up in 18 D-05's grouped confirmation is **a local gsd install into
    the target project** (e.g. `.opencode/`).
  - The report also **explains, without running it**, the global alternative
    (`~/.gsd/defaults.json` plus a global reinstall), which would change every opencode project.
  - The user's global opencode setup is never modified.
  - **Research must confirm:**
    - the exact local-install flag/command for the installed gsd version;
    - that opencode prefers project `.opencode/agents` over the global agents;
    - whether the `.opencode/` output should be gitignored or committed in target projects.

### Fix policy
- **D-04:** Bugs found in this phase are handled by a threshold:
  - **Small, local fixes** (a parser, a flag, a message, one module) are fixed within Phase 20,
    each with a regression test.
  - Anything that **changes a decision recorded in a CONTEXT.md**, or touches **more than one
    module**, becomes a decimal phase (`/gsd-phase --insert 20` → 20.x) with its own plan and
    verification.

### Open verifications this phase settles (from spec §6 / EVAL-04/05)
- **D-05:** The codex env signal:
  - confirm `CODEX_THREAD_ID` and/or `CODEX_VERSION` in the user's interactive codex session;
  - update the detection docstring label from "observed in session snapshots" to
    "live-verified";
  - drop whichever signal does not appear.
- **D-06:** The opencode lane from an opencode host:
  - determine whether `/gsd-review` self-skips the opencode lane on an opencode host, or whether
    it can be used intentionally (e.g. a different provider/model through the same CLI);
  - reflect the answer in `recommend`'s lane eligibility and in SKILL.md. Until settled, the
    spec's default stands: not recommended.

### Claude's Discretion
- The headless command templates.
- The interactive-run script format.
- The names of the evidence files (e.g. `20-SMOKE-CODEX.md`, `20-SMOKE-OPENCODE.md`).
- How the env is cleaned for headless runs.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Contracts
- `.planning/REQUIREMENTS.md` — EVAL-04, EVAL-05, SPEC-01 (order amended by D-02).
- `.planning/ROADMAP.md` — the Phase 20 success criteria.
- `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md` §6 — the open
  verification about the opencode lane from an opencode host.
- `.planning/phases/19-evaluation-on-claude/19-CONTEXT.md` — the smoke procedure and matrix
  reused here.
- `.planning/phases/16-ai-kit-spec-extensions/16-CONTEXT.md` — D-01 (amended here) and
  D-02 (codex signals).
- `.planning/phases/18-cross-ai-skills-apply-pipeline/18-CONTEXT.md` — D-05 follow-ups
  (amended here for opencode).

### gsd-core
- `~/.claude/gsd-core/bin/lib/install-model-override-resolver.cjs` — the model-baking source
  merge (global defaults vs project config), the evidence for D-03.
- `~/.config/opencode/gsd-core/` (1.13.0) and `~/.codex/gsd-core/` (1.13.0) — the hosts' own
  installs. Version differences from claude's 1.14.0 matter for REC-06 unknown-key dropping.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The Phase 19 scripted smoke procedure, which should be host-agnostic per 19-CONTEXT.
- The `ai_kit_spec` detection module (`_RUNTIME_ENV_SIGNALS`), where D-02's order change lands.

### Established Patterns
- Evidence files are committed in the phase dir and referenced from VERIFICATION.md.
- Env-signal verification labels (live-verified vs source-inspected vs observed) are kept in the
  detection docstring (16 D-02/D-03).

### Integration Points
- The user's global opencode config (`~/.config/opencode/`) must stay untouched (D-03).
- The codex sandbox may restrict writes outside the project. Scratch projects should live under
  a path codex can write to.

</code_context>

<specifics>
## Specific Ideas

- The user's opencode currently has global gsd agents **without** `model:` lines, so every gsd
  agent inherits the session model today. The local install is what makes per-agent models real
  on opencode.
- Memory notes to respect: diagnosing killed background CLI dispatches (probe before retrying);
  the opencode xai billing block (fall back to `--codex`, it isn't retryable).

</specifics>

<deferred>
## Deferred Ideas

- **Process-tree host detection** (walking parent PIDs for the nearest CLI) was considered and
  not chosen. Revisit only if env-signal ordering proves insufficient in real use.

</deferred>

---

*Phase: 20-live-validation-on-codex-opencode*
*Context gathered: 2026-09-23*
