# Phase 18: Cross-AI, Skills & Apply Pipeline - Context

**Gathered:** 2026-09-23 (interactive); updated 2026-10-14 (assumptions mode, after `18-SPEC.md`)
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
- Review lanes keep GSD's own lane definitions; `cross-ai.mjs` is for execution only. *(Refined
  2026-10-14: GSD's review lanes are unchanged, but the shipped runner also serves
  ai-kit-spec-review's own review dispatch in `--mode review` (18.1 D-10/D-11).)*

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

### Added 2026-10-14 (assumptions-mode discuss, jev-screened)

**Module layout and write path**
- **D-15: Subcommand dispatch.** `cli.py` registers subcommands through a name-to-handler
  table. The v1 `_cmd_*` handlers stay untouched.
  - New flat modules: `plan_edit.py` (pure plan-set/unset), `apply.py`, `config_backup.py`,
    `followups.py`, `cross_ai.py` (lane and target selection, pure), `cross_ai_script.py`
    (renderer) and `skills.py`.
  - v2 tests go in new modules, never in the v1 test file.
  - TypeSafe 0.89.
- **D-16: The v2 write path is 16.1's shared `ai_kit_spec/gsd_tools.py`** (`query config-set`,
  one call per entry), with a strict value encoder:
  - bool → `true`/`false`, `None` → `null`, dict/list → compact JSON, numbers → `str`;
  - a `str` that config-set would re-type (`true`, `false`, `null`, a finite number, a leading
    `[`/`{`) is refused, naming the key.
  - v1 `gsd_write.config_set` keeps its exact argv.
  - TypeSafe 0.96 over Laya legacy_widened 0.56 fb.
- **D-17: `plan-set` and `plan-unset` take `--plan` and `--inventory`.** The inventory defaults
  to a sibling `inventory.json`, and its digest is checked against the plan's.
  - Rejected keys come from the inventory's probe (17 D-09). `-fast` warnings come from
    `fast_twin_of` (17 D-13). Non-candidates come from the `needs_choice` top 3.
  - Two refusals ignore `--force`: a `workflow.cross_ai_timeout` below 1800, and `plan-unset`
    of an absent key.
  - Own reasoning; both models were low (Laya needs_choice_only 0.66 fb, TypeSafe
    require_inventory 0.69 fb). Provisional, so it is on the ledger.

**Apply**
- **D-18: Dry run and pre-flight validate keys with one read-only node call** to the host
  gsd-core's `isValidConfigKey(key, projectDir)`, plus the strict encoder. They never call
  `config-set`, not even with its `--dry-run`: the cached gsd-core 1.13.0 ignored that flag and
  wrote the key (verified live).
- **D-19: Backups live beside `gsd-tools config-path`**, which is workstream-aware: a
  workstream's config is `.planning/workstreams/<ws>/config.json`.
  - Name: `config.json.bak-<UTC YYYYMMDDTHHMMSSZ>`, plus `-<n>` on a collision, claimed by an
    exclusive create (`os.link` of a mkstemp copy).
  - Prune parses (timestamp, n), matches only that exact pattern, keeps the newest 3, and runs
    after a successful apply. `config.json.bak-manual` is never touched.
- **D-20 (amends 18-CONTEXT D-06 and SPEC R13's edge): No new backup** when the newest backup
  is byte-identical to the current config; the report says it was reused. Three no-op applies
  would otherwise evict every real earlier state. TypeSafe 0.77.
- **D-21: Restore is a verbatim atomic restore of the backup bytes** (mkstemp +
  `os.replace`). It is the one named exception to "only through gsd-tools", and the SPEC
  prohibition is amended.
  - Evidence (live, 1.16): a gsd-tools revert leaves `"model_overrides": {}` and rewrites
    4-space indentation as 2-space.
  - The 16.1 undo log stays as the failure record and the "apply in progress" marker; a
    leftover log makes the next apply refuse.
  - When no config existed before, restore deletes the file `config-new-project` created.
  - TypeSafe 0.92.
- **D-22: Apply order:**
  1. load, validate, and refuse any `needs_choice`;
  2. refuse if an undo log is open;
  3. back up;
  4. run `config-new-project` if the config is absent, then re-read and reconcile the copied
     global keys (SPEC R13);
  5. render `cross-ai.mjs`, so `workflow.cross_ai_command` never points at a failed render;
  6. send entries sorted by (first key segment, unset before set, key), skipping `keep`
     entries and unsets of absent keys;
  7. run `gsd-tools query agent-skills <agent> --json` per wired agent, under
     `GSD_RUNTIME=<host>`, and report its `warnings`;
  8. prune and close the log.

  A failure in steps 4–6 restores (D-21) and names the key.
- **D-23: Two test layers.**
  - Unit tests use a fake `run_fn`.
  - An integration module (the `test-integration` tier) uses the real gsd-tools, resolved by
    `gsd_catalog.resolve_gsd_tools_path`. It skips with a stated reason when gsd-tools is
    absent or older than 1.16, and works on a `mkdtemp` scratch project.
  - The Nth-key failure is injected by wrapping `run_fn`. Same-second backups use an injected
    `now_fn`.

**Cross-AI**
- **D-24: The lane vocabulary is read from the host gsd-core's capability registry** at
  inventory time (`loadRegistry({includeInstalled, cwd})`). It is stored as `review_lanes:
  [{slug, binary|null, transport, model_key|null, effort_key|null, default_effort}]`.
  - `model_key`/`effort_key` are used verbatim: antigravity's model key is `review.models.agy`,
    and `review.effort.cursor` does not exist.
  - Auto-eligible: the binary is on PATH, `model_key` is non-null, the slug is not the host,
    and the inventory has enumerated models for that runtime.
  - Lanes without model data (agy, kimi) are reachable only through `plan-set`.
  - v1 `CLI_TO_REVIEWER_SLUG` stays in v1 until 18.1 D-04 removes it.
  - TypeSafe 0.97.
- **D-25: pi is enumerated in this phase** by one `pi --list-models` parser in `ai_kit_spec`,
  so the pi pick is real on the first claude-host run. Phase 22 re-verifies and extends it, and
  SPEC-05 moves to Phase 18.
  - **Laya overridden** (needs_choice 0.79, high): Phase 19's scenario B expects pi with
    `router-env/my-coding`. TypeSafe second opinion: parser_now 0.79.
  - *(amended 2026-10-14, 22 D-04)* The parser reads pi's RPC `get_available_models` JSON, not
    the `--list-models` table (lossy `K`/`M` sizes, exit 0 on every failure).
- **D-26: The runner template is runnable in place.**
  - It lives in `ai-kit-spec-review` (18.1 D-10) with header `sha256=UNSTAMPED` and a default
    CONFIG, so `node <template> --self-test` works in the repo.
  - Header line 2: `// ai-kit-cross-ai generator=ai-kit-gsd-curated-config template=<N>
    sha256=<hex>`.
  - The hash covers the raw bytes after the second `\n`, CONFIG included. Python and Node both
    hash bytes, with no decoding or newline normalization. TypeSafe 0.81.
  - Pristine or absent means an atomic write; anything else means `.new` (a stale `.new` is
    overwritten).
  - CONFIG holds `prefer`, `models`, `outerTimeoutS`, `scrubEnv` (injected from 16.1's
    `HOST_SIGNAL_ENV_VARS`), per-CLI `extraArgs` (opt-in skills and MCP) and the
    retry/backoff/heartbeat constants. It is rendered with `json.dumps(indent=2)` between the
    `// <config>` markers.
  - The grok block is dropped. The codex block stays, marked unverified and outside the
    default `prefer`. opencode gets `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` by default. The
    version is `template=2`.
- **D-27: The XAI-02 changes to the prototype.**
  - Closed exit classes:
    - 69: permission_blocked, bad_model, auth, billing;
    - 75: quota, and capacity after retries;
    - 1: crash or empty answer;
    - 2: usage, no model, empty stdin;
    - 124: deadline;
    - 127: no CLI installed.
  - Exactly one last-line `AIKIT-XAI status=… cli= model= exit= cli_rc= elapsed= out=
    tree=clean|dirty action=fallback|retry-later|stop`, from every exit path.
  - Errors are matched on stderr and structured fields only (the prototype included the answer
    text).
  - Models are preflighted against each CLI's own list; it continues with a note if the
    listing fails.
  - The process group is killed after every child exit.
  - `exec` success needs exit 0, a non-empty answer, and a moved HEAD or tree. `review` needs
    an unchanged tree.
  - The `--self-test` is black-box: fake CLIs on PATH, one subprocess per exit code, a
    grandchild-kill check, and both git rules in a temp repo.
  - "Tree" = a tree id from a temporary git index (`GIT_INDEX_FILE=tmp git add -A; git
    write-tree`), because `status --porcelain` missed a re-edit of a dirty file live. TypeSafe
    0.79.
- **D-28: The script's data is a typed `artifacts[]` block in plan.json** (path, template,
  version, `config{prefer, models, outer_timeout_s}`, source/why/status), with its own diff
  kinds: add, change, keep-pristine, new-as-`.new`.
  - `plan-set` addresses it with reserved pseudo-keys (`script:cross-ai.model.pi`), which are
    never probed or sent to `config-set`.
  - 17 D-19's execution-command placeholder is satisfied when every target has a model.
  - TypeSafe 0.98.
- **D-29: The timeout is baked and also checked live.**
  - The rendered script bakes `outerTimeoutS`, and at run time takes the minimum with the live,
    workstream-aware config value (`GSD_WORKSTREAM`).
  - inner = outer − min(30, floor(outer/5)), which is 1770 for 1800.
  - TypeSafe 0.79.
- **D-30: Runner couplings from 18.1.**
  - A review-only claude block; it has no exec formula, so `--mode exec` exits 2.
  - Python dispatchers pass `--no-preamble`.
  - Runner flags for per-candidate knobs: codex `effort`/`service_tier`, cursor `mode`.
  - The status vocabulary and exit codes are a documented stable contract.

**Skills**
- **D-31: Global skills roots come from `gsd-tools skills-root <host>`**, plus
  `<project>/skills`. An entry is a directory containing `SKILL.md`.
  - `name` must match `^[A-Za-z0-9_-]+$`; otherwise it is `addressable:false` and never wired.
  - `escapes_root` compares the realpath of the skill directory with the realpath of the root.
  - `skill-manifest` is not used: it lacks the opencode, pi and cursor-global roots, and live
    it reported 74 of the 134 claude skills.
  - A project that keeps skills in `.claude/skills` is a stated limit in SKILL.md.
  - Both models agreed at low confidence (0.50/0.56 fb); the evidence decides.
- **D-32: A Claude plugin skill is visible only when all of these hold:**
  - it is installed in `<claude dir>/plugins/installed_plugins.json` with a matching scope
    (user, or `projectPath` == the project);
  - it is enabled in the layered `enabledPlugins` (user, project, local; last wins);
  - its skill file exists.

  The reference is `global:<plugin>:<dir>`. Wiring precedence is project, then global, then
  plugin. gsd-core emits plugin directives without an existence check, so ai-kit checks.
  TypeSafe 0.88.
- **D-33: `skill_affinity.json`** sits beside the package, with `schema_version`, `as_of` and
  `families[]` (`{id, skills, agents, when}`) in priority order.
  - Facts (`tdd_mode`, `frontend`, `db`, `system_one_backend`) come from the plan and
    inventory.
  - Resolution walks families, then skills, in file order. It skips failed gates and
    uninstalled or unaddressable skills, dedupes per agent, and stops at the cap.
  - Agent names are validated against the live `AGENT_TO_PHASE_TYPE`; an unknown name is
    dropped with a note.
  - `ponytail-debt` goes to `gsd-verifier` only. The planner already holds core `ponytail`,
    and the MVP cap is 2. Own reasoning (Laya both 0.91; TypeSafe second opinion
    one_agent_curated 0.55 fb); provisional, so it is on the ledger.
  - `agent_skills.<agent>` is the whole list, plan-managed.
- **D-34: Trusted roots.** Wire the project-relative `skills/<name>` whenever the same skill
  exists in the project (no root needed). Otherwise propose one entry per wired skill's real
  directory, `~/`-relative, as a separate approval item. A common-ancestor root is never
  proposed.
  - Own reasoning; both models were low and split (Laya per_skill_dir 0.50 fb, TypeSafe
    prefer_project_path 0.53 fb). Provisional, so it is on the ledger.
- **D-35: Ponytail on non-Claude hosts:** the six names are checked in each host's
  `skills-root`. On this machine none is visible outside the Claude plugin cache, so non-Claude
  hosts get no ponytail entries, and SKILL.md records a dated result. Other hosts' own plugin
  routes are not addressable through `agent_skills` and are never run.
- **D-36: System One detection is a reachability check, not a health check.**
  - It is a TCP connect (1–2 s) to `JEV_API_URL`'s host and port when the variable is set,
    reported as "reachable, not verified as System One". A key present by name also counts:
    `JEV_API_KEY`, or a new presence-only helper over `~/.config/ai-kit/secrets.env` that never
    returns the value.
  - No default URL is probed.
  - The plan notes the `GSD_PATH_JEV=1` / `GSD_PATH_JEV_TIMEOUT_SECONDS` session gate.
  - TypeSafe 1.00. This amends SPEC R11 and 24 R5.

**Follow-ups**
- **D-37: The installer argv** is `["npx","-y","@opengsd/gsd-core@<VERSION>","--<host>","--local"]`
  with `cwd=<project>`, where `<VERSION>` is the version the inventory resolved, never `latest`.
  - Without a location flag the installer prompts, and with no TTY it defaults to a global
    Claude install, so `--local` is always explicit (`install.js:872-873,14816-14850`).
  - The approval block prints each argv, its cwd, purpose and alternative, says `npx -y`
    downloads and runs an npm package, and names `pnpm dlx` as the equivalent.
  - *(amended 2026-10-14, 20 D-09)* It also discloses that a non-Claude `--local` install
    rewrites `~/.gsd/defaults.json` (`runtime`, `resolve_model_ids`) and scans home host dirs
    for legacy artifacts unless `--no-legacy-cleanup` is passed.
- **D-38: Effort sync** runs only when an `effort.*` key changed and the host is claude, codex
  or opencode. Its argv: `node <project-local gsd-tools> effort sync --apply --runtime <host>
  --config-dir <project>/<host dir> --project-dir <project>`.
  - The project-local gsd-tools is re-resolved after the installer runs.
  - pi and cursor are skipped (no `effort:` frontmatter).
  - The approval block shows a `--dry-run` change count first.
  - TypeSafe 0.98.

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

### gsd-core (host install; claude = `~/.claude/gsd-core`, v1.16.0 as of 2026-10-14)
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
- **Dogfood file state (2026-10-14):** this repo's `.planning/scripts/cross-ai.mjs` header says
  `41d4a79c…` while its body hashes to `c1cb32d6…`, so it reads as user-edited. The first real
  `apply` here (never during v1.3, 19 D-03) would produce `.new`, and the report must explain why.
- **Open questions for the researcher:**
  - whether each review lane honours `xhigh` (`review.effort.*` accepts any string);
  - `cursor-agent models` offline and unauthenticated behaviour (the preflight timeout);
  - whether `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS=1` also hides `~/.agents/skills`;
  - whether `@opengsd/gsd-core@<version>` is published for the pinned version;
  - the `enabledPlugins` layering and `plugin.json` custom skill paths (docs only so far).
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
*Context gathered: 2026-09-23; updated 2026-10-14*
