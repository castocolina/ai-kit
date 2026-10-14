# Phase 18: Cross-AI, Skills & Apply Pipeline - Context

**Gathered:** 2026-09-23
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase completes the v2 pipeline on top of Phase 17's `inventory`/`recommend`:
- `plan-set` / `plan-unset`;
- cross-AI review lane and execution command selection (XAI-01/02);
- skill inventory and skill → agent wiring (SKL-01..03);
- `apply` with dry-run diff, backup/restore and approved follow-ups (APP-01..04);
- registration and green gates (EVAL-06, amended).

**Scope change from the discussion:** v1 is **not** removed. The v2 subcommands are added next
to the 11 v1 subcommands, and v1 keeps working unchanged (D-08).

</domain>

<decisions>
## Implementation Decisions

### Carried forward (locked elsewhere — do not re-decide)
- **Spec §6/§7:**
  - the reviewer lane is never the host (pi has no lane);
  - the reviewer provider differs from the planning-slot provider;
  - execution is delegated to the best `execution` score in another CLI
    *(amended 2026-10-13: through the generated `.planning/scripts/cross-ai.mjs`, not
    `build_execute_command` with the bare CLI name; see "Amendment 2026-10-13" below)*;
  - execution defaults to yes on claude/codex and no on opencode/cursor/pi;
  - the report tells the user to run `--cross-ai` and sets `manager.flags.execute`;
  - ~~the timeout is 300 s (MVP) or 600 s~~ *(superseded 2026-10-13: `workflow.cross_ai_timeout` ≥ 1800 s)*.
- **Phase 17:**
  - D-04: a user-curated router wins the slot for its declared role
    (`router-env/my-plan-review` → review lane model, `router-env/my-coding` → execution);
  - D-05: `apply` refuses while any `needs_choice` remains;
  - D-06: deterministic ties;
  - D-08: plan-managed families are authoritative (`op: unset`, `existing` diff).
- **v1 D-01:** every write goes through `gsd-tools` (`config-new-project` / `config-set`).

### Amendment 2026-10-13 (cross-AI execution runner)

Source: `.planning/research/2026-10-13-audit/` reports 08, 10, 15, 17, 18; XAI-02 amended to match.
- **D-09:** curated-config generates `.planning/scripts/cross-ai.mjs` per project from a template
  (prototype: `research/2026-10-13-audit/cross-ai.mjs`) and sets
  `cross_ai_command = node .planning/scripts/cross-ai.mjs`. A sha256 header protects user edits
  (an edited file is never overwritten; the new version goes to `.mjs.new`).
- **D-10:** Preference order default pi > cursor > opencode, a model per CLI. grok is not a
  target; its models are reached through opencode or router-env. Claude is the main agent, never
  a cross-AI target. Every target runs unattended: no sandbox, no ask mode, no permission waits.
- **D-11:** Bare tool profile by default (pi `--no-skills --no-extensions`, opencode with its
  Claude-skill loading off); specific skills by SKILL.md path or MCP servers are opt-in.
- **D-12:** `workflow.cross_ai_timeout` ≥ 1800 s; the script's own deadline sits below it.
- **D-13:** Supervision contract: finite stdin, model pre-validated, process-group kill, errors
  matched on stderr and structured fields only, one `AIKIT-XAI status=… action=…` line, success
  only when HEAD moved or the tree changed, fallback only when both are unchanged.
- **D-14:** Every write goes through `gsd-tools query config-set` (it resolves the active
  workstream's config path). Effort keys need `gsd-tools effort sync --apply` to take effect, and
  the sync targets the project's local gsd-core install when one exists (D-05 follow-up).
- Review lanes keep GSD's own lane definitions; `cross-ai.mjs` is for execution only.

### Cross-AI review
- **D-01:** The number of reviewer lanes depends on rigor:
  - **Standard: 1 lane.**
  - **Rigorous: 2 lanes** when two eligible lanes exist. The second lane's provider must differ
    from both the planner's and the first reviewer's. When only one is eligible, use 1 lane and
    add a note.
  - MVP keeps convergence off by default (spec §5).
  - Rationale: the diversity and resilience matter most in Rigorous. The opencode route and the
    xai lane have both failed transiently before (v1.0 01.1-REVIEWS; the 2026-09-14 billing
    block).

### Skill wiring
- **D-02:** Users see and edit **bare skill names only** (in `plan.json` and the review pass).
  The skill translates them to the form gsd-core requires when writing
  `agent_skills.<agent>`:
  - `global:<name>` when the skill is in the host runtime's global skills dir;
  - a project-relative path when it is in the project's `skills/`;
  - `global:<plugin>:<skill>` for Claude plugin skills, and only on a claude host.
  - Evidence: gsd-core `init.cjs` agent-skills resolution treats a bare name as a
    **project-relative path** and skips it, with a hint to use `global:`.
  - Skills whose real path escapes the global root still need a
    `agent_skills_security.trusted_global_roots` entry, proposed in the plan for approval
    (spec §7).
- **D-03:** **Missing skills are silently omitted.** A recommended skill that is installed gets
  wired; one that is not installed is neither mentioned nor offered, and nothing is ever
  installed.
  - This **replaces** SKL-03's "explain and offer" and the spec §7 install offer.
  - Unknown installed skills (not in `skill_affinity.json`) are still only proposed from their
    descriptions, and the user confirms. Nothing new is installed.
- **D-04:** The **skills-per-agent cap depends on rigor**, replacing the fixed 3.
  - Defaults: MVP 2, Standard 3, Rigorous 5. The exact values are Claude's discretion; the
    user gave these as the example.
  - Order within the cap follows `skill_affinity.json`, which is curated and editable.
  - gsd-core itself has no limit. The cap exists because every wired skill injects its full
    SKILL.md into each invocation of that agent.

### Apply
- **D-05:** *(Amended by Phase 20 D-03: on opencode, the install follow-up is a **local** gsd
  install into the target project; the global alternative is explained, never run.)*
  Follow-ups get **one grouped confirmation** after a successful `apply`:
  - one yes/no covers the required commands (`gsd install <host>` when the host bakes models
    into agents, e.g. opencode, and `gsd-tools effort sync --apply` when effort keys changed);
  - on yes, the agent runs them and reports each result;
  - `/gsd-map-codebase` (intel on, no index) is only **recommended**, never part of the block,
    because it is long and costly.
- **D-06:** **Keep the last 3 backups.** `apply` writes `.planning/config.json.bak-<timestamp>`,
  restores it on any failed write, and prunes older backups beyond the newest 3.
- **D-07:** `op: unset` is implemented as `gsd-tools config-set <key> null`. Verified live
  against gsd-core 1.14 in a scratch project: it deletes the key. This stays within v1 D-01
  (writes only through gsd-tools).
  - Also verified: object values (`model_profile_overrides.<host>.<tier>` =
    `{"model", "reasoning_effort"}`) and list values (`review.default_reviewers`) are accepted
    by `config-set`.
  - **Amended 2026-10-14 (Phase 17 discuss):** gsd-core 1.16 rejects `config-set model_policy
    null` on the whole object, so an unset of an object-valued key goes per leaf
    (`model_policy.provider|budget|high|medium|low`). Phase 17 R13 emits per-leaf unsets.

### v1 coexistence
- **D-08:** **v1 is kept intact.**
  - The 11 v1 subcommands (`ensure-project`, `apply-profile`, `apply-critical-agents`,
    `detect-execution-candidate`, `detect-review-candidate`, `apply-execution`, `apply-review`,
    `detect-claude-md-path`, `detect-frontend`, `apply-claude-md-path`,
    `apply-workflow-defaults`) and their modules (`preference_match`, `critical_agents`,
    `workflow_defaults`, …) stay working and tested.
  - v2 adds `inventory`, `recommend`, `plan-set`, `plan-unset` and `apply` alongside them.
  - Rationale (the user's own words): nothing in v1 has been tested by the user, and v1 "tried
    to cover a lot but did little". Removing it without evidence is premature.
  - v1's future is decided in a later milestone, after v2 is evaluated (Phases 19–20).
  - SKILL.md documents the v2 flow as the primary path.
  - **This amends EVAL-06:** no module removal. EVAL-06 becomes: v2 registered in all gates,
    `make test` / `make validate` green with the v1 tests still passing, the README row
    updated, and cursor/pi labeled "not live-validated".
  - **Reversibility:** reversible.

### Claude's Discretion
- The exact skill caps per rigor (around 2/3/5).
- The backup timestamp format.
- How the grouped follow-up prompt is worded.
- Internal module layout for v2 next to v1: shared helpers such as `gsd_write.py`,
  `gsd_catalog.py`, `frontend_detect.py`, `claude_md_detect.py` and `cross_ai_build.py` are
  reused by both.
- How `plan-set` validates keys: at minimum, check against the host gsd-core's
  `isValidConfigKey` and reject non-candidate models for `needs_choice` slots unless forced.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec and phase contracts
- `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md`:
  - §3 — architecture: the `apply` flow and `gsd_write.py` as the only writer;
  - §6 — cross-AI;
  - §7 — skills: superseded by D-03 (no install offer) and D-04 (cap per rigor);
  - §8 — error handling.
- `.planning/REQUIREMENTS.md` — XAI-01..02, SKL-01..03 (SKL-02/03 amended), APP-01..04,
  EVAL-06 (amended).
- `.planning/phases/17-curated-config-inventory-recommendation-engine/17-CONTEXT.md` — the
  plan.json contract (`needs_choice`, `op: unset`, `existing`, routers).
- `.planning/phases/16-ai-kit-spec-extensions/16-CONTEXT.md` — host detection and catalog.

### gsd-core (host install; claude = `~/.claude/gsd-core`, v1.14.0)
- `bin/lib/init.cjs` — agent-skills resolution (around lines 3400–3530): `global:` handling,
  project-path containment, `trusted_global_roots`, the plugin directive (claude only). This is
  the evidence for D-02.
- `bin/lib/config-schema.cjs` — `isValidConfigKey`, used for `apply --dry-run` and `plan-set`.
- `bin/lib/capability-registry.cjs` — the reviewer-lane slug vocabulary (e.g.
  `cursor-agent` → `cursor`).

### v1 (kept, D-08)
- `skills/ai-kit-gsd-curated-config/SKILL.md` and
  `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/*` — the current v1 flow and
  modules.
- `.planning/milestones/v1.1-phases/07-curated-gsd-config-skill/` — v1 decisions D-01..D-10.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `gsd_write.py`:
  - `ensure_config_exists`, `config_set` (the only writer), `config_get`;
  - `_coerce_value` handles booleans; it needs to pass `null`, JSON objects and lists (D-07).
- `cross_ai_build.py`:
  - `build_execution_command` wraps `ai_kit_spec.commands.build_execute_command`;
  - `CLI_TO_REVIEWER_SLUG` covers only opencode, cursor and claude, so extend it for codex and
    the other lanes.
- `gsd_catalog.py` — gsd-tools and node resolution (host-first per Phase 17).
- `frontend_detect.py` / `claude_md_detect.py` — project facts, shared with v1.

### Established Patterns
- CLI subcommands emit JSON and take an injected `run_fn`/`which_fn`/`env_fn`.
- `tests/test_ai_kit_gsd_curated_config.py` holds the v1 suite. It must stay green (D-08); add
  the v2 tests next to it.

### Integration Points
- Makefile unittest list, `pyproject.toml` (pyright/vulture), `.pre-commit-config.yaml` and the
  README row already register this skill. Add the new modules to the globs where needed.
- Phase 19 evaluates SKILL.md's v2 flow (writing-skills RED/GREEN, `/skill-judge`) and the
  `resolve-model` check for all 35 agents.

</code_context>

<specifics>
## Specific Ideas

- Installed skills on this machine: 132 in `~/.claude/skills` and 112 in `~/.agents/skills`.
  `reducing-entropy`, `react-dev`, `mermaid-diagrams` and `gsd-debug` exist; `ponytail` did
  not at discussion time. *(Superseded 2026-10-13: ponytail is now installed as a Claude plugin
  and is a recommended skill set; see ROADMAP Phase 18 success criterion 6.)*
- Scratch-project probe used for D-07:
  `config-set model_overrides.gsd-planner opus` followed by `… null` → `model_overrides` is `{}`.

</specifics>

<deferred>
## Deferred Ideas

- **The v1 CLI's future** (keep, merge into v2 or remove) → a later milestone, after v2 is
  evaluated with evidence (D-08). The user asked for v1 to be reviewed and tested first.

</deferred>

---

*Phase: 18-cross-ai-skills-apply-pipeline*
*Context gathered: 2026-09-23*
