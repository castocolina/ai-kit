# Phase 20: Live Validation on Codex + Opencode - Context

**Gathered:** 2026-09-23 (interactive); updated 2026-10-14 (assumptions mode, after 20-SPEC.md)
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
  - **Refined 2026-10-14:** `CODEX_VERSION` has 0 hits in the codex 0.153.4 binary; its only hits
    under `~/.codex/sessions` are the user's own `env | grep` probe. `CODEX_THREAD_ID` is a
    shell-snapshot override in the binary and appears in 20 snapshots. Expected outcome:
    `CODEX_THREAD_ID` confirmed, `CODEX_VERSION` dropped from `_RUNTIME_ENV_SIGNALS` and from
    the 16.1 D-14 scrub list. `CODEX_THREAD_ID` stays scrubbed (gsd-core reads it as a
    workstream key). The interactive run prints all `CODEX_*` names, names only. If
    `CODEX_THREAD_ID` is also absent, codex env detection is empty and a replacement signal is
    chosen from that names list.
  - **Outcome (2026-10-18):** Headless codex exec 0.162.1 listed `CODEX_THREAD_ID` and
    `CODEX_VERSION`; detection keeps both with headless-evidence labels. TUI confirmation is
    pending the interactive run; any drop is deferred to the post-TUI follow-up in 20-07.
- **D-06:** The opencode lane from an opencode host:
  - determine whether `/gsd-review` self-skips the opencode lane on an opencode host, or whether
    it can be used intentionally (e.g. a different provider/model through the same CLI);
  - reflect the answer in `recommend`'s lane eligibility and in SKILL.md. Until settled, the
    spec's default stands: not recommended.

### Added 2026-10-14 (assumptions mode, after 20-SPEC.md)
- **D-07: "Planned == baked" is its own check.** The `GSD_RUNTIME=<host>` `resolve-model`
  matrix cannot prove R5/R7.
  - The installer bakes through `readGsdRuntimeProfileResolver`, whose runtime is the project
    config's `runtime`, else `~/.gsd/defaults.json`'s, else null (bakes nothing). It never
    reads `GSD_RUNTIME` (gsd-core 1.16.0 `install-model-override-resolver.cjs:172-197`).
  - Scratch experiment: with this machine's global `runtime: "codex"` and no project
    `runtime`, opencode agents bake bare `gpt-5.6-*` ids, which `opencode debug agent` parses
    as `providerID=gpt-5.6-terra, modelID=""`.
  - The chain recorded per agent: plan → project-local `resolve-model` → baked `model:` line →
    `opencode debug agent <name>` (model-free; non-empty `providerID`/`modelID`, id in
    `opencode models`). Codex: explicit `model_overrides` pins only, read from
    `.codex/agents/gsd-*.toml` with `tomllib`.
  - Baked values are compared only after the post-apply installer run (18 D-37). R1's
    idempotency edge holds only for unchanged config.
  - Amended 2026-10-18: opencode v2.0.31 has no `debug agent <name>`; the fourth link is the interactive step 7 in `20-INTERACTIVE-OPENCODE.md` (`opencode run --standalone --agent` JSON model fields, or `debug agents` listing against the user's service, recorded as such). The three headless links are unchanged. Scope: the per-agent chain consists of those three headless links, which the smoke proves for every agent (20-03); the loader observation is a one-agent sample (`gsd-planner`) unless the `debug agents` listing names a model per agent, in which case every `gsd-*` entry is compared.
- **D-08: `runtime` is a managed key on opencode and codex** (amends 17 R5 and adds 17 D-23).
  `recommend` emits `runtime: <host>` (`source: preset`). On codex the tier layer is labelled
  "resolve-model only": `generateCodexAgentToml` embeds `model =` only for an explicit
  `model_overrides` entry (#3241). Laya amend_both 0.90.
- **D-09: Scratch installs run under a throwaway HOME** seeded with a copy of the real
  `~/.gsd/defaults.json`.
  - A `--local` install still runs `writeNonClaudeDefaults` (rewrites `~/.gsd/defaults.json`)
    and `cleanupLegacyGsdCc` (scans `~/.config/opencode`, `~/.codex`) (`bin/install.js:6972-7014,
    12234, 14360-14375`). On this machine the write is a no-op by luck.
  - `GSD_TEST_MODE=1` is rejected: it also skips the opencode permission writer.
  - 18 D-37's approval block must disclose these global writes (amended there).
  - Laya isolated_home 0.44 (fb), TypeSafe 0.96.
- **D-10: The "global config unchanged" prohibition is a semantic allowlist guard**, not a
  directory checksum.
  - Files: `~/.codex/{config.toml, agents, hooks.json}`,
    `~/.config/opencode/{opencode.jsonc, agents, commands, skills, plugins}`,
    `~/.gsd/defaults.json`.
  - `config.toml` is compared with `tomllib` minus any `projects."<scratch path>"` table: the
    codex TUI persists project trust there (`tui-project-trust-write`).
  - opencode's own `package.json`/`bun.lock` refresh is excluded. The 20-SPEC prohibition row
    is amended.
- **D-11: The host is never a review lane** (settles D-06's policy half).
  - gsd-core has no code-level self-skip: `SELF_CLI` is deterministic only for antigravity,
    cursor and claude, and `auto` (LLM-judged) elsewhere (`workflows/review.md:126-149`).
    `resolveReviewerSelection` takes no host input.
  - `recommend` never proposes the host slug, with a test. A copied
    `review.default_reviewers=["opencode"]` on an opencode host is flagged for replacement
    (17 D-08). SKILL.md documents the manual `review.reviewer_instances` route as user-owned.
  - The live run still records the mechanics both ways (`--opencode` and `default_reviewers`),
    two trials each.
  - Laya instance_after_proof 0.41 (fb), TypeSafe never_host_lane 0.98.
- **D-12: GSD-generated paths are gitignored by prefix; baked output is never committed.**
  - opencode: `.opencode/{gsd-core/, agents/gsd-*, commands/gsd-*, skills/gsd-*,
    plugins/gsd-core.js, gsd-*.json}`; the `.codex/` equivalents.
  - Codex agent TOMLs bake an absolute `gsd-core/` path; the opencode permission writer adds an
    absolute allow and an unpinned `mcp.gsd`.
  - A blanket ignore is wrong: opencode drops its own `.gitignore` into `.opencode/`, so the
    dir is shared by design. curated-config only reports this; it never edits `.gitignore`.
  - Answers D-03's open gitignore question. Laya prefix_ignore 0.50 (fb), TypeSafe 0.86.

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
- The v2 code (`inventory`, `recommend`, `apply`, the Phase 19 smoke script, `child_env`) is not
  in the tree yet; the touch points above are contracts.

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

- Open for research (2026-10-14): whether `-c 'projects."<scratch>".trust_level="trusted"'`
  gives session-only codex trust, and whether project `.codex` agents load only after trust;
  whether `CODEX_THREAD_ID` is present in the TUI shell and `codex exec`; the opencode
  background `@opencode-ai/plugin` install inside scratch `.opencode/` dirs (a network side
  effect); an upstream gsd-core issue about `--local` writing `~/.gsd/defaults.json`.
- **Process-tree host detection** (walking parent PIDs for the nearest CLI) was considered and
  not chosen. Revisit only if env-signal ordering proves insufficient in real use.

</deferred>

---

*Phase: 20-live-validation-on-codex-opencode*
*Context gathered: 2026-09-23*
