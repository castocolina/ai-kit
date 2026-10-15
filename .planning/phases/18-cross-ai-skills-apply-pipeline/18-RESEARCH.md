# Phase 18: Cross-AI, Skills & Apply Pipeline - Research

**Researched:** 2026-10-15
**Domain:** Python stdlib CLI (curated GSD config) driving gsd-core 1.16.0 (`gsd-tools.cjs`, node), a generated Node runner script, per-agent skill wiring, and a backed-up atomic config apply
**Confidence:** HIGH for gsd-core behavior (every claim below was run live in a scratch project this session); MEDIUM for host CLIs other than pi; LOW only where an item is listed under Open Questions or Assumptions.

<user_constraints>
## User Constraints (from CONTEXT.md)

(Copied verbatim from `18-CONTEXT.md`; markdown heading levels inside the copied blocks are demoted by two so they nest under this section. Nothing else is altered.)

### Locked Decisions

##### Carried forward (locked elsewhere — do not re-decide)
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

##### Amendment 2026-10-13 (cross-AI execution runner)

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

##### Cross-AI review
- **D-01:** The number of reviewer lanes depends on rigor:
  - **Standard: 1 lane.**
  - **Rigorous: 2 lanes** when two eligible lanes exist. The second lane's provider must differ
    from both the planner's and the first reviewer's. When only one is eligible, use 1 lane and
    add a note.
  - MVP keeps convergence off by default (spec §5).
  - Rationale: the diversity and resilience matter most in Rigorous. The opencode route and the
    xai lane have both failed transiently before (v1.0 01.1-REVIEWS; the 2026-09-14 billing
    block).

##### Skill wiring
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

##### Apply
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

##### v1 coexistence
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

##### Added 2026-10-14 (assumptions-mode discuss, jev-screened)

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
    - *(amended 2026-10-14, Phase 25 QTA-01)* the 69/75 split is route-aware: a billing or
      limit error on a router-backed route (`infer_fallback_quota`) is 75 (`retry-later`),
      because the router's fallback chain returns to subscription tiers; on a direct
      third-party provider route it stays 69. Phase 25 owns the pattern table and the
      10-minute / 4-hour wait;
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

### Deferred Ideas (OUT OF SCOPE)

- **The v1 CLI's future** (keep, merge into v2 or remove) → a later milestone, after v2 is
  evaluated with evidence (D-08). The user asked for v1 to be reviewed and tested first.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| XAI-01 | Cross-AI review lanes: `workflow.plan_review_convergence`, `review.default_reviewers`, `review.models.<suffix>`, `review.effort.<suffix>` | Lane vocabulary = `mergeReviewerLanes(REVIEWER_LANES, loadRegistry(...))`; fields `slug`, `probe.binary`, `modelConfigKey`, `effortConfigKey`, `defaultEffort` verified live (Live Verification L5). Key validity per lane verified (L3). Existing vendor/counterpart machinery in `recommend.py`/`roles.py` is reusable. |
| XAI-02 | Cross-AI execution: targets, generated `cross-ai.mjs`, supervision contract, timeout, `manager.flags.execute` | Prototype read in full (`.planning/scripts/cross-ai.mjs`); GSD's call site and 300 s default confirmed (L7); pi RPC enumeration shape captured live (L8); tree-id technique verified (L11). |
| SKL-01 | Skill inventory: host global dir, project `skills/`, Claude plugin skills | `gsd-tools query skills-root <host>` verified for 5 hosts (L9); plugin layout and `installed_plugins.json` shape verified; symlink-escape reality on this machine (L9). |
| SKL-02 | `skill_affinity.json`, caps per rigor, bare names in plan, gsd-core reference forms at apply | `buildAgentSkillsBlock` read and exercised for every reference form (L4); `skills_count` pitfall; `GSD_RUNTIME` behavior including the pi gap. |
| SKL-03 | Missing skills silently omitted; unknown skills proposed; trusted-root proposal | Trusted-root semantics (`loadTrustedGlobalRoots`) read and exercised (L4). |
| SKL-04 | jev recommended only with skill + System One backend | Env var names and fallbacks from the jev skill (L10); existing `reachable()` precedent in `decide.py`; `local_secrets.load_secret` returns values, so a presence-only helper is required. |
| APP-01 | `plan-set` / `plan-unset` (`source: user`) | `plan_io`/`plan_schema` read; no plan loader exists yet (Phase 17 only writes plans); needs_choice shape read in `recommend._cross_ai_layer`. |
| APP-02 | `apply --dry-run` validates keys against host gsd-core, prints diff, writes nothing | One-call `isValidConfigKey` pattern already exists in `gsd_catalog.query_gsd_tables`; `config-set --dry-run` behavior differs by gsd-core version (L2). |
| APP-03 | `apply` backs up, writes through gsd-tools, reconciles copied keys, restores on failure | `config-new-project` copy behavior (L1), `config-set` semantics (L2), workstream path behavior (L12), 16.1 helper inventory (the "undo log" is in-memory only: see Corrections). |
| APP-04 | Follow-ups: pinned local installer, `effort sync --apply`, one grouped approval | Installer flags and `@opengsd/gsd-core@1.16.0` publication verified (L6); `effort sync` flags, output shape, and runtime behavior verified (L6). |
| EVAL-06 | v2 registered in all gates; v1 unchanged; README row; SKILL.md v2 flow; skill-judge | Gate machinery read: `tools/run_unittest_parallel.py`, `tools/gen_test_groups.py`, `tests/test_gate_scope.py`; baseline skill-judge scores found (98 / 97 / 99). |
</phase_requirements>

## Summary

Phase 18 is mostly integration of seams that already exist and were exercised live this session: the shared `ai_kit_spec.gsd_tools` resolver and wrappers, Phase 17's `inventory`/`recommend`/`plan.json`, gsd-core's `config-set`/`config-new-project`/`agent-skills`/`effort sync`, and the dogfood runner `.planning/scripts/cross-ai.mjs`. The genuinely new code is (1) the Node runner template with the XAI-02 contract and a black-box self-test, (2) the pure selection layers (lanes, targets, skills) added to `recommend`, (3) `plan-set`/`plan-unset` with a plan loader, and (4) the `apply` pipeline with backup, restore and follow-ups. The riskiest items are the runner template (largest new code, node-only, executed by a cheap model) and `apply` atomicity.

Live verification found several premises in the locked documents that do not hold as written. They do not change the decisions, but each changes what a plan must do, so they are collected under **Corrections to carry into plans** below and in Open Questions: the 16.1 "undo log" is an in-memory list (no persisted marker exists), the ownership sidecar lives inside the execute-gsd skill, "integration tier" real-node tests belong to the **e2e** tier, `GSD_RUNTIME=pi` does not canonicalize (so the `agent-skills` verification is meaningless on a pi host), `skills_count` counts configured entries not resolved ones, `RUNTIMES_SCHEMA_VERSION` is already 3, and the SPEC R3 execution default conflicts with what Phase 17 shipped.

**Primary recommendation:** Build bottom-up and serially in 13 plans (Plan Decomposition below): shared `ai_kit_spec` additions, inventory extensions, pure selection layers with golden regeneration, runner template then renderer, plan editing, then the apply pipeline (backup, dry run, write path, follow-ups), and last the SKILL.md/gate/skill-judge plan. Never touch `.planning/scripts/cross-ai.mjs` during execution: it is the supervisor running the plans.

## Corrections to carry into plans

These are facts verified this session that contradict wording in CONTEXT/SPEC/REQUIREMENTS. AGENTS.md (Workflow) says to amend those files formally; the planner should include that in the closing plan.

1. **No persisted undo log exists (D-21, SPEC R13).** `gsd_config.apply_changes` keeps `reverts` in a local list and reverts through `config-set` (`skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_config.py:109-149`). The only on-disk artifacts are the per-run `.bak` (`gsd_config.py:193-198`) and the ownership sidecar. `apply` therefore needs a NEW persisted "apply in progress" marker (file beside the config, written before the first write, deleted on success or after restore) for D-21's "leftover log makes the next apply refuse". [VERIFIED: gsd_config.py:109-149, 193-198]
2. **The ownership sidecar is not shared code.** `read_ownership`/`write_ownership`/`OWNERSHIP_SIDECAR = "ai-kit-gsd-owned.json"` live in `ai_kit_spec_gsd` (the execute-gsd skill), not in `ai_kit_spec` (`gsd_config.py:76-90`). Curated-config's only sanctioned bridge is the one-way sibling to `ai-kit-spec-review`. SPEC R13 says apply "reuses ... ownership sidecar"; this cannot be done without a cross-skill import. Recommendation: do not use it (its fail-safe default already treats every value as user-owned); record the deviation (Open Question O2).
3. **D-23's "integration (`test-integration` tier)" is the e2e tier.** `INTEGRATION_MODULES` is only the Textual/PTY suites; real-node runs against the checkout-local gsd-core are in `E2E_MODULES` (`tools/run_unittest_parallel.py:45-60`; `tests/test_curated_config_e2e.py:1-8` docstring; AGENTS.md Testing). New real-gsd-tools tests belong in a module added to `E2E_MODULES`.
4. **`config-set --dry-run` is honored by gsd-core 1.16.0.** Live: it returned `{"dry_run": true, "would_update": true, ...}` and the key stayed absent. D-18's claim that "the cached gsd-core 1.13.0 ignored that flag" is a 1.13 fact. The decision (use `isValidConfigKey` in one read-only node call, never `config-set --dry-run`) is still right because it is version-independent. [VERIFIED: live run]
5. **`GSD_RUNTIME=pi` does not take effect.** `canonicalizeRuntimeName('pi')` returns `null` in 1.16.0 (`bin/lib/runtime-name-policy.cjs:312`), so `fillRuntimeIdentity` (`bin/lib/config-loader.cjs:1084`) leaves the runtime unset and `buildAgentSkillsBlock` falls back to `claude` (`bin/lib/init.cjs:3627`+). Live: `GSD_RUNTIME=pi` accepted a `global:ponytail:ponytail` plugin directive with no warning. D-22 step 7 (`agent-skills` under `GSD_RUNTIME=<host>`) is therefore valid for claude, codex, opencode and cursor only; on pi it must be skipped with a stated reason (22 D-06 already says agent skills have no effect on pi). [VERIFIED: live runs, node probe of `canonicalizeRuntimeName`]
6. **`skills_count` counts configured entries, not resolved ones.** Live: a list of 6 entries of which 3 were skipped still reported `"skills_count": 6`. The check must use the JSON `warnings` array and the number of `@`/`Load the` lines in `block`. [VERIFIED: live run]
7. **`RUNTIMES_SCHEMA_VERSION` is already 3** (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:27`, bumped by Phase 17's opencode 2.x probe). Adding `clis.pi` makes it 4. 18.1 D-04 says "2 -> 3"; 18.1 must be restated as "4 -> 5" (or "current + 1"). [VERIFIED: detection.py:27]
8. **SPEC R3 / XAI-02 execution default vs shipped Phase 17 code.** REQUIREMENTS/SPEC: `workflow.cross_ai_execution` "defaults to yes on claude and codex hosts, no on opencode, cursor and pi". Shipped `recommend.cross_ai_answers` defaults exec to `y` only when rigor is MVP, the host is claude/codex AND a cheap other-CLI candidate exists, else `n` (`recommend.py:96-123`). The design spec §5/§6 says "recommended on Claude/Codex" (MVP: only "when a cheap candidate exists"). Open Question O1.
9. **Phase 17 goldens and tests change.** `_cross_ai_layer` reserves `needs_choice` placeholders with `candidates: []` and `why: "reserved for Phase 18 cross-AI selection (D-19)"` (`recommend.py:744-776`). Filling them changes all 17 golden files (`tests/fixtures/curated_config_v2/golden/*.json`) and the assertions at `tests/test_curated_config_recommend.py:1540-1561` and `:2381`. Regenerate with `UPDATE_GOLDEN=1` in the same commit.
10. **The `recommend` purity guard allow-lists three modules.** `ALLOWED_RELATIVE_IMPORTS = frozenset(("presets", "roles", "plan_schema"))` (`tests/test_curated_config_recommend.py:1720`). New pure modules imported by `recommend` (`cross_ai`, `skills`) must be added there, with the existing non-vacuity counterpart pattern.
11. **opencode 2.0.29 `run` has no `--variant` flag** (`opencode run --help`: flags are `--standalone --server --continue --session --fork --model --agent --format --file --title --thinking --auto`; model syntax is `provider/model#variant`), while gsd-core's opencode review lane renders effort as `--variant <level>` (live `renderEffortArgv`). This is a Phase 20 live-validation risk for the opencode review lane; the runner's own opencode formulas (`run --model m --auto --format json`, `--agent plan`) do match the 2.0.29 help. [VERIFIED: `opencode run --help`, node `renderEffortArgv`]
12. **`OPENCODE_DISABLE_CLAUDE_CODE_SKILLS` does not hide `~/.agents/skills`.** opencode docs: the variable "Disable loading `.claude/skills`" and no variable mentions `.agents`; the v2 skills page lists global discovery in `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills` and does not mention the variable at all. The "bare tool profile" for opencode is therefore partial; the template comment and SKILL.md must say so. [CITED: opencode.ai/docs/cli/ ; opencode.ai/v2/docs/skills/]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Skill/lane/jev facts (I/O) | Python `inventory` (reads FS, runs one node call) | gsd-core (lane registry, `skills-root`) | Inventory is the only place that touches the machine; `recommend` stays pure (17 REC-01). |
| Lane, target and skill selection | Pure Python (`recommend` layers via `cross_ai.py`, `skills.py`) | - | Deterministic, golden-testable, no I/O. |
| Key validity | gsd-core `isValidConfigKey` (node) | Python caches the answer in the inventory | gsd-core is the schema authority; dry run re-checks live (D-18). |
| Config write | gsd-tools (`query config-set`, `config-new-project`) | Python verbatim restore (sole exception) | v1 D-01; restore must not reformat (D-21). |
| Backup / prune / marker | Python `config_backup.py` | - | New code; no gsd-tools verb exists for it. |
| Reference translation (`global:` / project path / plugin) | Python `apply` (uses inventory skill locations) | gsd-core `agent-skills` as post-write check | D-02: users see bare names; gsd-core defines the forms. |
| Script supervision (spawn, kill, classify, tree id) | Generated Node runner | - | Runs inside GSD's `run-with-timeout`; stdlib-only Node. |
| Script rendering and edit protection | Python `cross_ai_script.py` | - | Hash header and atomic write are file-level policy. |
| Installer / effort sync | Python `followups.py` (argv, after approval) | gsd-core installer, `gsd-tools effort sync` | Only after one grouped yes; machine installs never run. |
| Approval prompt wording | SKILL.md (agent) | - | The CLI prints the block data; the agent asks. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.14.7 on this machine (ruff target py312) | All runtime code | AGENTS.md: runtime code stays stdlib-only. [VERIFIED: `python3 --version`; AGENTS.md] |
| Node.js | v24.21.0 here; gsd-core 1.16.0 declares `engines.node >=24.0.0` | gsd-tools and the generated runner | The runner can assume Node 24 (GSD itself requires it). [VERIFIED: `node --version`; `@opengsd/gsd-core@1.16.0` package.json `engines`] |
| gsd-core | 1.16.0 (project-local `.claude/gsd-core/VERSION`) | `gsd-tools.cjs` (config, agent-skills, effort, review-lane) | The validator and writer of record. [VERIFIED: `.claude/gsd-core/VERSION`] |
| `unittest` via `tools/run_unittest_parallel.py` | stdlib | Test tiers | Repo convention (AGENTS.md Testing). |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pi | 1.2.0 | Execution target; RPC `get_available_models` enumerator | Probe argv from 22 D-04; `--model` accepts `provider/id` [VERIFIED: `pi --help`] |
| git | 2.55.0 | Tree id via temporary index in the runner | `GIT_INDEX_FILE=<tmp> git add -A; git write-tree` (L11) |
| `pnpm dlx` / `npx` | pnpm 11.18.0; `~/.local/bin/npx` is a redirect shim to `pnpm dlx` | Follow-up installer launcher | See Open Question O6 |
| ruff ~0.14, pylint ~4.0, pyright ~1.1, vulture ~2.14 | pinned in `uv.lock` | Gates | pylint limits: max-args 5, max-locals 15, max-branches 12, max-returns 6, max-statements 50 (AGENTS.md) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Per-leaf `config-set` | Direct JSON write | Forbidden by v1 D-01 except the verbatim restore. |
| `gsd-tools skill-manifest` | Own scan via `skills-root` | `skill-manifest` lacks opencode/pi/cursor roots (D-31). |
| Python supervisor fallback | None | 18.1 D-13: no node means fail closed. |

**Installation:** none. This phase adds no dependency. The only external package named anywhere is `@opengsd/gsd-core@<resolved version>`, run only after the grouped approval.

**Version verification:** `pnpm view @opengsd/gsd-core dist-tags` -> latest `1.17.0`; `@opengsd/gsd-core@1.16.0` is published (tarball `https://registry.npmjs.org/@opengsd/gsd-core/-/gsd-core-1.16.0.tgz`, `time` 2026-10-05). bin map: `gsd-core -> bin/install.js`. [VERIFIED: pnpm view, this session]

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `@opengsd/gsd-core` | npm | 4.5 months (created 2026-05-30); pinned 1.16.0 is 10 days old; latest 1.17.0 is 1 day old | 10,356/wk | github.com/open-gsd/gsd-core | [SUS] ("too-new", from the latest tag) | Flagged. Not installed by this phase's code or tests. Run only after the APP-04 grouped approval, which is already a human gate; the approval block must show the pinned version, `npx -y` download-and-run disclosure and the `pnpm dlx` equivalent (D-37). The planner needs no extra `checkpoint:human-verify` task beyond the approval path itself. |

`postinstall`: none (`signals.postinstall: null`). **Packages removed due to [SLOP] verdict:** none. **Packages flagged [SUS]:** `@opengsd/gsd-core` (above). [VERIFIED: `gsd-tools package-legitimacy check --ecosystem npm @opengsd/gsd-core`, output captured this session]

## Architecture Patterns

### System Architecture Diagram

```
                         (read-only, existing in Phase 17)                 (new in Phase 18)
 host CLIs / FS / env ──► inventory ─────────────► inventory.json ──► recommend ──► plan.json
   pi RPC models            + review_lanes[] (1 node call)               (pure: presets + roles
   skills-root x host       + skills[] (roots, realpath, plugins)         + cross_ai.py + skills.py
   plugins json             + system_one_backend (TCP / key NAME)         + artifacts[] block)
   JEV_API_URL / key name   + valid_keys probe incl. agent_skills.*,              │
                              review.models.*, workflow.cross_ai_timeout          ▼
                                                                          plan-set / plan-unset
                                                                          (load_plan + digest check
                                                                           vs sibling inventory.json;
                                                                           source: user; atomic write)
                                                                                  │
                    ┌─────────────────────────────────────────────────────────────┘
                    ▼
 apply [--dry-run] --plan --inventory --project-dir
   1 load+validate plan, refuse needs_choice ──► (dry run: print add/change/keep/remove diff, STOP, write nothing)
   2 refuse if apply marker present
   3 backup (reuse newest if byte-identical) ──► .planning/config.json.bak-<UTC>[-n]   (keep newest 3)
   4 write marker; config-new-project if config absent; re-read; reconcile copied keys
   5 render .planning/scripts/cross-ai.mjs  (absent|pristine -> atomic write; edited -> .mjs.new)
   6 per entry: gsd-tools query config-set (unsets first, per leaf; bare skill names -> global:/path/plugin refs)
   7 gsd-tools query agent-skills <agent> --json under GSD_RUNTIME=<host>  (report warnings; skip on pi)
   8 prune backups, delete marker, print follow-up block
   fail in 4-6 ──► verbatim atomic restore of backup bytes (or delete created file) ──► name the key ──► exit non-zero
                    │
                    ▼
 followups (only with explicit approval flag): installer argv (pinned, --local, cwd=project) ──► re-resolve project gsd-tools
                                                ──► effort sync --apply (claude|codex|opencode; dry-run count shown first)

 At execution time (inside GSD):  echo prompt | gsd_run run-with-timeout $T -- node .planning/scripts/cross-ai.mjs
   runner: preflight model ─► spawn CLI (own process group, finite stdin) ─► parse stdout/structured fields
           ─► classify on stderr+structured only ─► kill group ─► tree id (temp index) ─► ONE `AIKIT-XAI` last stderr line
```

### Recommended Project Structure

```
skills/ai-kit-gsd-curated-config/
├── SKILL.md                                  # v2 primary flow, v1 kept (EVAL-06)
├── skill_affinity.json                       # D-33 (beside the package)
└── ai_kit_gsd_curated_config/
    ├── cli.py                                # _COMMAND_HANDLERS already a name->handler table (cli.py:583-597); add plan-set, plan-unset, apply, followups
    ├── cross_ai.py                           # PURE lane + target selection (imported by recommend)
    ├── skills.py                             # PURE affinity resolution (imported by recommend)
    ├── skill_scan.py                         # I/O: roots, realpath, plugins, descriptions (imported by inventory only)
    ├── plan_edit.py                          # pure plan-set/unset (+ plan loader/validator in plan_io.py)
    ├── apply.py  config_backup.py  followups.py
    └── cross_ai_script.py                    # renderer + header hash + pristine/edited/.new
skills/ai-kit-spec-review/
├── references/cross-ai.mjs                   # runnable template, header sha256=UNSTAMPED (path is Claude's discretion: A1)
└── ai_kit_spec/ detection.py (parse_pi_models, detect_pi_models) · gsd_tools.py (strict encoder) · local_secrets.py (presence-only) · cross_ai_template.py (path resolver, tooling_guidance.py style)
tests/ test_curated_config_cross_ai.py · _skills.py · _plan_edit.py · _apply.py · _followups.py · _script.py   (unit)
       test_curated_config_apply_e2e.py       (real node/gsd-tools; add to E2E_MODULES)
```

Splitting I/O from pure code matters: `inventory` may import I/O helpers, `recommend` may import only pure modules (the purity guard and `TestPurity` patch subprocess/socket/time/open to raise).

### Pattern 1: Pure layers added to `recommend`
**What:** New layers after `_cross_ai_layer` (lanes/targets, skills) and a separate `artifacts[]` block, each a pure function of the inventory, the earlier entries and `RecommendOpts`. Curated data (`skill_affinity.json`) is loaded by the CLI and passed in through `RecommendOpts` (not read inside `recommend`); record its `as_of`/digest in the plan so the plan stays reproducible.
**When:** Always; keeps REC-01 (same inputs, same plan, byte-identical).
**Reuse:** `roles` already implements strict vendor inference (17 D-14), counterpart picks and tie-breaks (17 D-06); lane selection should call the same helpers rather than re-deriving vendors.

### Pattern 2: Lane vocabulary from gsd-core, matched to candidates by binary name
`probe.binary` of each lane equals the inventory candidate `runtime` today (`claude`, `codex`, `opencode`, `cursor-agent`); the lane slug for cursor is `cursor` and its binary `cursor-agent`; antigravity's binary is `agy` (no candidates). Matching on `lane.binary == candidate.runtime` removes the hand-written `CLI_TO_REVIEWER_SLUG` map for v2 and survives 18.1's later rename (the match becomes `runtime_id`).

### Pattern 3: One node call for lanes and extra key probes
Extend the existing single `node -e` script (`gsd_catalog._GSD_TABLES_QUERY_SCRIPT`, `gsd_catalog.py:146`) or add a sibling script with the same `null`-on-failure convention. The lane query is (verified live, 11 lanes in 1.16.0):

```js
// Source: .claude/gsd-core/bin/lib/review-lane-descriptor.cjs (REVIEWER_LANES, mergeReviewerLanes:509) + capability-loader.cjs
const d = require(laneDescriptorPath), l = require(capabilityLoaderPath);
const merged = d.mergeReviewerLanes(d.REVIEWER_LANES, l.loadRegistry({ includeInstalled: true, cwd }));
const lanes = merged.map(x => ({
  slug: x.slug, transport: x.transport,
  binary: (x.probe && x.probe.binary) || null,           // http-reachable lanes have none
  model_key: x.modelConfigKey || null, effort_key: x.effortConfigKey || null,
  default_effort: x.defaultEffort || null }));
```
The same call must also probe `agent_skills.<agent>` for every agent in `AGENT_TO_PHASE_TYPE` and each lane's `model_key`/`effort_key`, because `recommend._drop_rejected` raises for any plan key that was never probed (`recommend.py:900-923`), and `presets.closed_key_set` (`presets.py:185`) cannot know lane suffixes or agent names before the tables are loaded.

### Pattern 4: Backup naming and claim (D-19)
`<config dir>/config.json.bak-<YYYYMMDDTHHMMSSZ>[-<n>]` (gsd-core itself uses the `X.bak-<timestamp>` convention for `STATE.md`, `health-diagnostic.cjs:294`). Claim the name with an exclusive create: write a `mkstemp` copy, then `os.link(tmp, final)` (fails with `FileExistsError` on a collision), unlink the temp. Copy the source file's mode (`mkstemp` creates 0600). Prune parses `(timestamp, n)` with an anchored regex and never touches `config.json.bak-manual`.

### Pattern 5: Verbatim atomic restore (D-21)
`mkstemp` in the config's directory, write the backup bytes, `os.chmod(tmp, original_mode)`, `os.replace`. Plain `cache_write_text` (`ai_kit_spec/cache.py:27`) would leave mode 0600 unless `mode=` is passed (it supports it). When no config existed before apply, restore deletes the file `config-new-project` created (record "existed before" from `os.path.isfile(config_path)` before step 4).

### Anti-Patterns to Avoid
- **Running `config-set` before `config-new-project`.** `config-set --cwd` on a project with no config creates a bare file holding only that key, and later `config-new-project` reports `already_exists` (L1), so the defaults are never written.
- **Trusting `--project-dir` for a fresh project.** It fails with "no .planning/ directory found" (L1); only `--cwd` creates `.planning/`. Order: `config-new-project --cwd`, then `--project-dir` writes.
- **Parsing `skills_count`** (Correction 6).
- **Presenting the `AIKIT-XAI` line only to the log.** SKILL.md rule from the audit: print it verbatim after every external dispatch.
- **Letting an executor plan edit `.planning/scripts/cross-ai.mjs`.** It is the live supervisor running the plans; edits mid-run change the running process's next invocation.
- **Calling `cursor-agent models` in tests or probes.** It rewrites `~/.cursor/cli-config.json` (`privacyCache`, documented in `detection.py:144-157`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| gsd-tools / node resolution | Another launcher-order copy | `ai_kit_spec.gsd_tools.resolve_gsd_tools` / `gsd_catalog.resolve_gsd_tools_path` | Already drift-tested against `edge_floor.py` (`gsd_tools.py:1-17`). |
| Config path | `.planning/config.json` literal | `gsd_tools.config_path(...)` (`gsd-tools config-path --cwd`) | Workstream-aware (L12). |
| Key validity | A copy of the key list | `isValidConfigKey` via the batch node call | 125 central + 16 dynamic + capability-federated keys (17 D-09). |
| Atomic file write | New tempfile code | `ai_kit_spec.cache.cache_write_text(path, text, mode=)` | Already crash-safe, per-writer temp names (`cache.py:27-46`). |
| Canonical plan JSON / digest | New serializer | `plan_schema.canonical_json`, `plan_schema.inventory_digest` | Byte-stable plans; digest check for plan-set/apply. |
| Value encoding for config-set | Ad-hoc `str()` | New `encode_value_strict` next to `_coerce_value` (D-16) | gsd-core re-types strings (12, true, 1e3, `{...}` become non-strings; L2). |
| Vendor inference / ties | Name heuristics | `ai_kit_spec.vendor`, `roles` helpers | 17 D-06, D-14. |
| Process-group kill, deadlines | Python supervisor | The node runner only (18.1 D-13) | One supervisor, one contract. |
| Outer timeout wrapper | Python timer | GSD's own `gsd_run run-with-timeout` | Already SIGTERM then SIGKILL at +3 s, exit 124 (`gsd-tools.cjs:4871-5075`). |
| Secrets presence | `load_secret(...)` then discard | New presence-only helper that never returns the value | `load_secret` returns the value (`local_secrets.py:11-28`). |

**Key insight:** every hard part of this phase already has an owner (gsd-core validates, writes and resolves skill references; `run-with-timeout` enforces the outer limit). Custom code is limited to policy: what to write, in what order, how to back out, and what the runner reports.

## Live Verification Log (AGENTS.md Required Start #3)

All runs: checkout-local gsd-core 1.16.0 (`node .claude/gsd-core/bin/gsd-tools.cjs`), scratch project and scratch `HOME`/`GSD_HOME` under the job tmp dir, synthetic `~/.gsd/defaults.json`, 2026-10-15. This repo's `.planning/config.json` was never passed to a write verb. Quoted strings are copied from the command output.

### L1. `config-new-project`
- Fresh project, synthetic defaults `{"resolve_model_ids":"omit","runtime":"cursor","model_policy":{"provider":"cursor","budget":"low"},"custom_unrelated":"keepme"}`: `--raw` prints `created`, exit 0. Second call prints `exists`; JSON form `{"created": false, "reason": "already_exists"}`.
- It copies global keys into the project config: the written file contained `"resolve_model_ids": "omit"`, `"model_policy": {"provider": "cursor", "budget": "low"}` and the unknown `"custom_unrelated": "keepme"`. It did NOT copy `runtime` (matches 17 D-10). `~/.gsd/defaults.json` sha256 was identical before and after.
- It honors both `GSD_HOME` (base dir holding `.gsd/defaults.json`) and `HOME`.
- Afterwards every gsd-tools call prints two stderr warnings: `unknown config key(s) in .planning/config.json: custom_unrelated` and `... project config takes precedence here ... (#3532)`. They are stderr noise, not part of the JSON.
- `--project-dir <dir>` without `.planning/` fails: `Error: Invalid --project-dir: ... (no .planning/ directory found ...)`. `config-path --cwd` on a project with no `.planning/` still prints `<dir>/.planning/config.json`. `config-set --cwd` there creates `.planning/config.json` holding only the one key.
- Consequence for R13 reconcile: copied keys can include arbitrary unknown keys; reconcile only the plan's managed families (`resolve_model_ids`, `model_policy.*`, `model_overrides.*`, ...) and leave the rest.

### L2. `query config-set` / `config-unset`
- There is no `config-unset`; unset is `config-set <key> null`. Both `node gsd-tools.cjs config-set ...` and `... query config-set ...` work (v1 wrapper uses the first form, `gsd_tools.py:176-182`).
- Success: exit 0, stdout `{"updated": true, "key": ..., "value": ..., "previousValue": ...}` (`previousValue` only when the key existed). Unset of a present key: `{"updated": true, "unset": true, "key": "model_policy.provider", "value": null, "previousValue": "cursor"}`. Unset of an absent key: exit 0, `{"updated": false, "unset": true, "key": "model_policy.high", "value": null}`.
- Whole-object unset is rejected: `config-set model_policy null` -> exit 1, stderr `Error: Unknown config key: "model_policy". Valid keys: ...` (a ~4 KB list; truncate it in reports). Per-leaf unset works and leaves an empty parent: after unsetting `provider` and `budget`, `model_policy` is `{}` (so a gsd-tools "revert" does not restore the original bytes, as D-21 says).
- Invalid key: exit 1, stderr `Error: Unknown config key: "bogus.key"...`.
- gsd-core re-types strings and does no value validation: `12` -> number 12, `true` -> boolean, `1e3` -> 1000, `{"a":1}` -> object, `"[1"` stays a string, `workflow.cross_ai_timeout abc` is accepted as the string "abc", 900 is accepted (no 1800 floor). So the strict encoder (D-16) and the 1800 refusal (D-17) are ai-kit's job.
- `config-set ... --dry-run` in 1.16.0 prints `{"dry_run": true, "would_update": true, "key": ..., "value": ...}` and does not write.
- `config-get <absent>` -> exit 1, stderr `Error: Key not found: <key>` (the clean-miss string `gsd_tools.config_get` already matches).

### L3. `isValidConfigKey` per family (node, `bin/lib/config-schema.cjs`)
Accepted: `agent_skills.gsd-executor`, `agent_skills_security.trusted_global_roots`, `review.default_reviewers`, `review.models.{codex,opencode,cursor,agy,claude}`, `review.effort.{codex,opencode,claude}`, `workflow.plan_review_convergence`, `workflow.cross_ai_execution`, `workflow.cross_ai_command`, `workflow.cross_ai_timeout`, `manager.flags.execute`, `effort.agent_overrides.gsd-executor`, `effort.routing_tier_defaults.heavy`.
Rejected: `agent_skills.bogus agent` (space), `review.models.pi`, `review.models.antigravity` (the key suffix is `agy`), `review.models.gemini`, `review.models.qwen`, `review.models.kimi` (the lane key is `review.models.kimi-code`), `review.effort.cursor`, `review.effort.agy`, `review.models.xai`, `review.effort.xai`.
`review.effort.<lane>` accepts any string at write time; gsd-core's lane resolver only forwards `minimal, low, medium, high, xhigh, max` (anything else falls back to the lane default; `review-lane-invocation.cjs` `EFFORT_LEVELS`).

### L4. `agent_skills` resolution (`bin/lib/init.cjs:3627-3754`, `buildAgentSkillsBlock`)
Resolution rules, from source and confirmed by running `gsd-tools query agent-skills gsd-executor --json` against a scratch project:
- `global:<name>`: name must match `^[A-Za-z0-9_-]+(:[A-Za-z0-9_-]+)*$`; a name with a colon is a plugin directive: claude emits `Load the \`ponytail:ponytail\` skill via the Skill tool before proceeding (plugin-provided).` with NO existence check; every other runtime warns `Plugin-namespaced skill "global:ponytail:ponytail" requires a Skill-tool-capable runtime (claude) — skipping on runtime "codex"`.
- Bare `global:<name>`: file `<getGlobalSkillsBase(runtime)>/<name>/SKILL.md` must exist (`Global skill not found at "~/.claude/skills/foo/SKILL.md" — skipping`) and its real path must be inside that base (`Global skill "escaped" failed path check (symlink escape?) — skipping`) unless inside a `agent_skills_security.trusted_global_roots` entry (then a stderr-only NOTE, not a warning).
- Anything else is a project-relative path confined to the project root: `skills/projskill` resolved; bare `bar` gave `Skill not found at "bar/SKILL.md" — a global skill named "bar" exists; use "global:bar" to reference it — skipping`.
- Runtime comes from `config.runtime`, else `GSD_RUNTIME`/install marker via `fillRuntimeIdentity`; live: with no env the base was `~/.claude/skills`; with `GSD_RUNTIME=codex` it switched to `~/.agents/skills`. `GSD_RUNTIME=pi` is not canonicalized (Correction 5).
- Output: JSON `{"agent_type", "block", "skills_count", "warnings": [...], "configured", "reason", "source", "degraded", ...}`; warnings also go to stderr, together with unrelated gsd-tools noise, so parse only stdout JSON.
- Trusted roots: `loadTrustedGlobalRoots` (`bin/lib/security.cjs:177`) accepts `~` and `~/x` forms, rejects relative paths, nonexistent paths, the filesystem root and the home dir itself, and realpaths each entry. A root equal to the skill's own real directory works (live: `["~/vault/esc2"]` made the symlinked `esc2` resolve; before it, `failed path check`).

### L5. Review-lane registry
`gsd-tools review-lane flags` prints `--claude --codex --coderabbit --opencode --qwen --cursor --antigravity --agy --ollama --lm-studio --llama-cpp --kimi-code`. Lane fields (node, `REVIEWER_LANES`), slug / probe binary / model key / effort key / default effort:
`claude / claude / review.models.claude / review.effort.claude / high`; `codex / codex / review.models.codex / review.effort.codex / high`; `coderabbit / coderabbit / null / null / null`; `opencode / opencode / review.models.opencode / review.effort.opencode / high`; `qwen / qwen / null / null / null`; `cursor / cursor-agent / review.models.cursor / null / null`; `antigravity / agy / review.models.agy / null / null`; `ollama, lm_studio, llama_cpp / (http-reachable, no binary) / review.models.<slug> / null`; `kimi-code / kimi (capability probe) / review.models.kimi-code / null`. Rendered effort argv for `xhigh`: claude `["--effort","xhigh"]`, codex `["-c","model_reasoning_effort=xhigh"]`, opencode `["--variant","xhigh"]`, cursor and agy none. `claude --help` lists `--effort <level> (low, medium, high, xhigh, max)`. So `xhigh` is forwarded verbatim; whether a given codex or opencode model honors it depends on that model's reasoning modes (use the candidate's `reasoning_modes` when present, else write the lane default `high`).

### L6. `effort sync` and the installer
- `gsd-tools effort sync [--apply|--dry-run] [--config-dir D] [--runtime R]` (+ global `--project-dir`); default is dry run (`gsd-tools.cjs:4343-4372`; `commands.cjs:764`). Runtime branches: `codex` (`.toml`), `opencode` (`variant:` frontmatter), `claude` (`effort:` frontmatter); any other runtime returns `{"synced": 0, "skipped": 0, "changes": [], "dry_run": true, "reason": "runtime 'pi' does not use effort: frontmatter"}` (verified for pi and cursor). Dry-run output shape: `{"synced", "skipped", "changes": [], "dry_run", "agents_dir"}`; the "dry-run change count" for the approval block is `len(changes)`.
- Installer (npx cache `@opengsd/gsd-core@1.16.0/bin/install.js`, 14,852 lines): `--local`/`-l` parsed at line 873, `--opencode` at 940, `--pi` at 941, `--codex` at 943, `--cursor` at 946, `--no-legacy-cleanup` at 1192 (`return args.includes('--no-legacy-cleanup')`), `--relative-includes` (worktree-friendly local installs) in the help. I did not run it.
- `@opengsd/gsd-core@1.16.0` is published (answers the open question); `latest` is 1.17.0.

### L7. Outer timeout
`gsd-core/workflows/execute-phase/detail/elaboration.md:74`: `CROSS_AI_TIMEOUT=$(gsd_run query config-get workflow.cross_ai_timeout --raw 2>/dev/null || echo "300")`; call site (same file): `echo "$TASK_PROMPT" | gsd_run run-with-timeout "${CROSS_AI_TIMEOUT}" -- ${CROSS_AI_CMD} > "$CANDIDATE_SUMMARY" 2>"$ERROR_LOG"` (command word-split, no shell; stdout is the SUMMARY candidate, stderr the error log). `templates/config.json:21` carries `"cross_ai_timeout": 300` but a fresh `config-new-project` did NOT write the key (L1 config). `run-with-timeout`: SIGTERM at the deadline, SIGKILL after 3 s, exit 124 on timeout; blank/negative/NaN seconds -> exit 2 (`gsd-tools.cjs:4871-5075`). So an absent key means 300 s, confirmed.

### L8. pi RPC `get_available_models`
`printf '{"id":"1","type":"get_available_models"}\n' | pi --mode rpc --offline --no-session --no-extensions --no-skills --no-context-files --no-mcp` -> exit 0, one stdout line, empty stderr, process exits on stdin EOF. Shape: `{"id":"1","type":"response","command":"get_available_models","success":true,"data":{"models":[...]}}`. 56 models on this machine today (22 D-04 recorded 85 on another run; the count depends on configured providers). Per-model keys seen: `api, baseUrl, compat, contextWindow, cost{input,output,cacheRead,cacheWrite}, id, input[], inputLimits (some), maxTokens, name, provider, reasoning, thinkingLevelMap (some), type`. `id` is bare (`my-coding`); `provider` is separate (`router-env`); `input` is `["text"]` or `["text","image"]`; `thinkingLevelMap` maps levels to a string or null. Router entries present: `router-env/my-planning`, `my-plan-review`, `my-coding`, `smart-executor`. The capture holds `baseUrl` values: keep it in scratch, never commit; the committed fixture strips them. pi accepts `--model provider/id` (`pi --help`: `--model <pattern>  Model pattern or ID (supports "provider/id" and optional ":<thinking>")`), so the parser should emit `provider/id` strings to avoid bare-id collisions across providers (22 D-05).

### L9. Skill roots and plugins
`gsd-tools query skills-root <host>` (live, this machine): claude `~/.claude/skills`; codex `~/.agents/skills`; opencode `~/.config/opencode/skills`; cursor `~/.cursor/skills`; pi `~/.pi/agent/skills` (JSON `{"skills_root": ...}`; `--raw` prints the path; unknown host -> error). Under a scratch `HOME` the same rows re-root correctly.
- Real machine facts: `~/.claude/skills` has 63 entries, 60 of them symlinks (to `~/.agents/skills/...` or to this repo's `skills/`); `~/.agents/skills` has 42 real dirs; pi/cursor/opencode skill roots are empty; none of the five roots contains a `ponytail*` skill (D-35's dated result: ponytail is visible nowhere outside the Claude plugin cache). Consequence: on a claude host most global skills have `escapes_root: true`, so wiring `react-dev` or `reducing-entropy` needs a per-skill trusted root (`~/.agents/skills/react-dev`), exactly D-34's design; expect several proposals per plan.
- Plugin layout (ponytail 5.1.0): `~/.claude/plugins/installed_plugins.json` is `{"version": 2, "plugins": {"ponytail@ponytail": [{"scope": "user", "installPath": ".../plugins/cache/ponytail/ponytail/5.1.0", "version": "5.1.0", ...}]}}`; skills at `<installPath>/skills/<name>/SKILL.md` (six: `ponytail ponytail-audit ponytail-debt ponytail-gain ponytail-help ponytail-review`); manifest `plugin.json` has `"name": "ponytail"` and no `skills` field. Enabled state: `~/.claude/settings.json` `enabledPlugins` has `"ponytail@ponytail": true`. The reference for a plugin skill is `global:<plugin name>:<skill dir>`, e.g. `global:ponytail:ponytail-review` (resolves to the directive on a claude runtime; live).
- Claude Code docs: plugin.json `skills` "Directories to scan for skills ... Adds to the default `skills/` scan", and the manifest lives at `.claude-plugin/plugin.json`; a plugin with a root `SKILL.md`, no `skills/` and no `skills` key loads as one skill (D-32's scan must read the manifest's `skills` paths too). [CITED: https://code.claude.com/docs/en/plugins-reference] Settings precedence puts local above project above user; the per-key merge behavior of the `enabledPlugins` object across files was not stated in the pages I could read (Open Question O13).

### L10. jev backend detection inputs (names only; no value read)
From the installed jev skill (`~/.claude/skills/jev-fast-decision/SKILL.md` env table): `GSD_PATH_JEV` (exactly `1` enables), `GSD_PATH_JEV_TIMEOUT_SECONDS` (required), `JEV_API_URL` (optional repoint), `JEV_API_KEY` (optional bearer; "falls back to `OPENCODE_API_KEY`"), `JEV_MODEL`, `JEV_RESPONSE_MODEL`, `JEV_MIN_CONFIDENCE`. ai-kit's secrets file is `$HOME/.config/ai-kit/secrets.env` in `local_secrets.secrets_env_path` (`local_secrets.py:7-8`), whereas `decide.config_dir` honors `XDG_CONFIG_HOME`; the new presence helper should use the same directory rule as the rest of `ai_kit_spec` and never read `OPENCODE_API_KEY`/opencode `auth.json` (credential file). `skills/ai-kit-gsd-spec-discuss/scripts/decide.py:96` `reachable(url, connect)` with `CONNECT_TIMEOUT_SECONDS = 2.0` (line 36) is the TCP-connect precedent (that skill ships alone, so copy the pattern, do not import); its `config_dir(env)` (line 67) is `${XDG_CONFIG_HOME:-~/.config}/ai-kit`.

### L11. Tree id and process facts
`GIT_INDEX_FILE=<tmp>/i git add -A; GIT_INDEX_FILE=<tmp>/i git write-tree` on this repo: 0.12 s, exit 0. Re-editing an untracked file between two snapshots changed the tree id while `git status --porcelain f.txt` printed `?? f.txt` both times (so porcelain cannot see it), confirming D-27's rationale. Side effect to document: `git add -A` writes blob objects into the object database (no refs or worktree changes).

### L12. Workstreams
`config-path --cwd P` -> `P/.planning/config.json`; with `GSD_WORKSTREAM=wsx` (or `--ws wsx`) -> `P/.planning/workstreams/wsx/config.json`. A `config-set` under `GSD_WORKSTREAM=wsx` CREATED `.planning/workstreams/wsx/` and wrote there with no existence check. Active-workstream precedence in gsd-core is `--ws` > `GSD_WORKSTREAM` > stored pointer (`bin/lib/active-workstream-store.cjs` header). So `apply` must resolve `config-path` with exactly the environment it uses for the writes, print the resolved path, and the runner can only honor the env case (Open Question O11).

## What exists today: runner, helpers, tests

### The cross-AI script
- **Dogfood file:** `.planning/scripts/cross-ai.mjs` (479 lines, committed in `ef2daf6`). Line 2 is `// ai-kit-cross-ai generator=ai-kit-gsd-curated-config template=1 sha256=41d4a79c1fc423662c7ad9a07c68d92605472da20640e4d00c6f87b6ab3d24ec`; the body (bytes after the second `\n`) hashes to `c1cb32d631d68452cbd6f0d709531154b103d0b818bfd25cc633f11345f07094`, so it reads as user-edited (`node .planning/scripts/cross-ai.mjs --self-test` prints `header: edited`, verified). The first real `apply` here would write `.mjs.new` (19 D-03: never during v1.3). It is also the supervisor that runs this milestone's plans through pi.
- **Prototype copy:** `.planning/research/2026-10-13-audit/cross-ai.mjs` differs only in the doc path comment, `prefer` (includes grok), and `models.pi`.
- **No template exists yet** in `skills/ai-kit-spec-review`. `references/` holds `apply-findings.md cli-profiles/ cross-ai-dispatch.md loop-diagram.md ranking-weights.toml routing-table.md tooling-guidance.md`; the resolver precedent is `tooling_guidance.resolve_shared_tooling_reference_path()` (package-relative `references/<file>`).
- **Prototype structure to evolve (template=2):** `CONFIG` block between `// <config>` markers (`prefer`, `models`, `timeoutMarginS`, `defaultOuterTimeoutS`, `retries`, `backoffS`, `heartbeatS`); `RUNTIMES` blocks for cursor, opencode, grok, pi, codex with `bins/exec/review/resume/parse/env`; `SCRUB_ENV` (misses `AI_AGENT` and `CODEX_VERSION`, which `HOST_SIGNAL_ENV_VARS` has, `detection.py:76`); `TRANSIENT`/`FATAL` regexes applied to a blob that includes `r.stdout.slice(-4000)` (the answer text: the bug D-27 removes); exit codes pass through the CLI's code (N), 124, 127, 2, 128+n; success = exit 0 + no parse error + non-empty text; fallback compares `git rev-parse HEAD` + `git status --porcelain`; `headerState` hashes `lines.slice(2).join('\n')` as a decoded string (D-26 requires raw bytes); `--self-test` is white-box and in-process (D-27 requires black-box).
- **Inner deadline already matches D-29:** `innerTimeoutS(outer) = outer - Math.min(timeoutMarginS, Math.floor(outer / 5))`: 300 -> 270, 1800 -> 1770, 20 -> 16.
- **Contract source for the rewrite:** `.planning/research/2026-10-13-audit/18-runtime-detection-and-subprocess-supervision.md` §4 (spawn invariants, error classes in match order, exit-code table, `AIKIT-XAI` line example, retry vs fall back vs stop). Closed exit set (D-27): `0` ok; `1` crash or empty answer; `2` usage/no model/empty stdin; `69` permission_blocked, bad_model, auth, billing (direct route); `75` quota, or capacity after retries, and billing on a router-backed route (25 QTA-01); `124` deadline; `127` no CLI installed; plus `128+n` when the runner itself is signalled (kept from the prototype and the audit; D-27 does not list it, so it is the one code to confirm, see O5). One last stderr line: `AIKIT-XAI status=… cli= model= exit= cli_rc= elapsed= out= tree=clean|dirty action=fallback|retry-later|stop`, from every exit path.
- **Phase 25 forward-compat:** 25 D-02 wants the pattern table as its own marked JSON block OUTSIDE `// <config>` and inside the hashed region, and 25 D-01 adds `reset_at=`/`pattern=` fields to the status line. Give Phase 18's template a delimited `// <patterns>` block (even if minimal) so Phase 25 extends rather than restructures.
- **Node floor:** Node 24 (gsd-core's own engines). ESM `.mjs`, `node:` imports, `crypto.randomUUID`, `fs.rmSync`, top-level `import.meta.url` are all safe.
- **CLI formulas re-checked against installed binaries:** opencode 2.0.29 `run` flags match the prototype (`--model`, `--auto`, `--format`, `--agent`); pi 1.2.0 `-p --model --session-id --no-skills --no-extensions --no-approve --offline` are all in `pi --help`; cursor-agent 2026.10.14 and codex-cli 0.162.1 present. Nothing was executed against a model (no spend).

### Phase 16.1 helpers apply can reuse (and what is NOT there)
| Helper | Where | Reuse |
|---|---|---|
| Resolver (`resolve_gsd_tools`, `gsd_tools_candidates`, `local_gsd_core_roots`, `project_root`) | `ai_kit_spec/gsd_tools.py:115,102,83,31` | Yes, as-is (curated-config reaches it through `gsd_catalog.load_gsd_tools`). |
| `GsdTools`, `config_set`, `config_get`, `config_path`, `ensure_config_exists`, `prior_value`, `gsd_core_version` | `gsd_tools.py:134,163,205,234,272,190,259` | Yes. `config_set` has no timeout and no env parameter (inherits process env: set both `HOME` and `GSD_HOME` in e2e). Add a strict encoder next to `_coerce_value` (`gsd_tools.py:150`) and leave `config_set`'s v1 argv unchanged. |
| Atomic write with mode | `ai_kit_spec/cache.py:27 cache_write_text(path, text, mode=None)` | Yes (restore, `.new`, template output, plan). |
| Undo list from `previousValue` | `gsd_config.apply_changes` (execute-gsd skill) | Pattern only; in-memory, other skill. |
| Ownership sidecar | `ai_kit_spec_gsd.gsd_config` | Not importable from curated-config (Correction 2). |
| Per-run `.bak` | `gsd_config._backup_once` (`<config>.ai-kit-spec-execute-gsd.<run_id>.bak`) | Different naming from D-19; do not reuse. |
| Env scrub | `detection.HOST_SIGNAL_ENV_VARS` (frozenset of 11 names: `AI_AGENT CLAUDECODE CLAUDE_CODE_ENTRYPOINT CLAUDE_CODE_SSE_PORT CODEX_SANDBOX CODEX_THREAD_ID CODEX_VERSION CURSOR_AGENT GROK_AGENT OPENCODE PI_CODING_AGENT`, verified by import) and `dispatch.child_env` (`dispatch.py:69`) | Render `scrubEnv` as a SORTED list (a set is not JSON-serializable and is unordered: byte-stability). |
| `local_secrets.load_secret` | `local_secrets.py:11` | Returns the value; add `secret_is_set(env, key) -> bool`. |

The new modules therefore own: the backup/prune/restore code, the persisted apply marker, plan loading and validation, and everything in the runner.

### Test infrastructure facts
- Groups (`tools/run_unittest_parallel.py`): `unit` = every `tests/test_*.py` not named in an explicit set (system python3; this is what `make validate` and pre-commit run); `arch` = `tests.test_arch`; `unit-uv`; `integration` = Textual/PTY modules only; `e2e` = `E2E_MODULES` (verbatim line 53: `E2E_MODULES = frozenset({`) containing `tests.test_worktree_e2e`, `tests.test_system_memory_e2e`, `tests.test_curated_config_e2e`, `tests.test_ai_kit_spec_e2e`, `tests.test_ai_kit_gsd_spec_discuss_e2e`, run by `make e2e-test` only.
- After adding any `tests/test_*.py`, run `python3 tools/gen_test_groups.py`; `tests/test_gate_scope.py` fails on a stale generated listing in `Makefile` and `.pre-commit-config.yaml`. A new e2e module must also be added to `E2E_MODULES` (a `stale_exception_names` check fails on names with no file).
- The real-gsd e2e pattern to copy: `tests/test_curated_config_e2e.py` (`_RealGsdTestCase`: temp HOME, `RUNTIME_DIR` pointing at this checkout, `skipTest` when node or gsd-tools is missing, real node executable rather than a volta shim).
- Golden machinery: `tests/test_curated_config_golden.py` (`ALL_GOLDEN_CASES`: 5 hosts x 3 rigors + 2 spot cases; regenerate with `UPDATE_GOLDEN=1 python3 -m unittest tests.test_curated_config_golden`), fixtures in `tests/fixtures/curated_config_v2/` (`gsd_tables_1_16.json`, `runtimes.json`, `model-catalog.json`; pi models there are synthetic and labelled).
- The v1 suite is `tests/test_ai_kit_gsd_curated_config.py` (1,205 lines); it passes today (`Ran 90 tests ... OK`, run this session) and must not need edits in this phase (18.1 D-14 edits it later).

## Common Pitfalls

### Pitfall 1: Write order on a fresh project
**What goes wrong:** `config-set` before `config-new-project` creates a bare config with one key; `config-new-project` then says `already_exists` and the defaults never arrive.
**Avoid:** D-22 order exactly: ensure config first (`--cwd`), re-read, reconcile, then `--project-dir` writes. Test with a project that has no `.planning/` at all.

### Pitfall 2: Stray `GSD_WORKSTREAM`
**What goes wrong:** the environment variable silently redirects every write to `.planning/workstreams/<ws>/config.json` and creates the directory. The backup, marker and restore must all live beside that resolved file.
**Avoid:** resolve `config-path` with the same env as the writes, print it in the report, and name it in the dry-run diff header.

### Pitfall 3: gsd-core re-types strings and validates no values
**What goes wrong:** `plan-set workflow.cross_ai_command 12` is stored as the number 12; `cross_ai_timeout abc` is accepted. A model id such as `true` or `1e3` would be re-typed.
**Avoid:** `encode_value_strict` refusing strings that `config-set` would re-type (`true`, `false`, `null`, finite numbers, leading `[`/`{`) naming the key; `plan-set` refuses `workflow.cross_ai_timeout` < 1800 even with `--force` (D-17). Because `config-set` accepts anything, also refuse `workflow.cross_ai_command` values other than the rendered `node .planning/scripts/cross-ai.mjs` unless `--force` (not locked: O14).

### Pitfall 4: Verifying with `skills_count`, or on pi
See Corrections 5 and 6. Verify with `warnings == []` and the block's line count; skip the check (with a stated reason) when the host is pi.

### Pitfall 5: Symlinked global skills escape the root
**What goes wrong:** 60 of 63 entries in `~/.claude/skills` on this machine are symlinks, so they fail gsd-core's containment check and are skipped unless trusted.
**Avoid:** `escapes_root` from `realpath(skill_dir)` vs `realpath(root)`; one trusted root per wired escaping skill, written `~/`-relative; if the real directory is outside `$HOME` it cannot be written `~/`-relative, so do not wire that skill and say why in a note (the skill is installed, so D-03's silence rule does not apply). Prefer the project-relative `skills/<name>` when the same skill exists in the project (no root needed, D-34).

### Pitfall 6: Restoring with the wrong mode, or from a stale backup
`mkstemp` files are mode 0600; restore must `chmod` to the original mode (or the config silently becomes private). Reuse of an identical newest backup (D-20) compares bytes of the current config, not mtimes. Prune orders by the parsed `(timestamp, n)`, never by mtime or lexical order of mixed `-n` suffixes (`-10` sorts before `-2` lexically).

### Pitfall 7: A restore that cannot run
If the process dies between marker write and restore, the next `apply` must refuse and print the marker's backup path and the exact restore instruction; it must not auto-restore (the user may have edited the file since). Test by killing between steps with an injected exception, not a real kill.

### Pitfall 8: Golden churn and the unprobed-key raise
Filling the cross-AI placeholders and adding `agent_skills.*`/`review.*` entries changes all 17 goldens; any new plan key that was not probed by `inventory` makes `recommend` raise (`ValueError: keys not probed by this inventory`, `recommend.py:900-915`) and the CLI exit 2. Probe the new key families in the same plan that introduces the entries, and regenerate goldens in that commit.

### Pitfall 9: Rendering must be byte-deterministic
The hash covers CONFIG. Render with `json.dumps(config, indent=2, sort_keys=True, ensure_ascii=True)`, scrubEnv sorted, LF newlines only, no trailing-space drift, and hash raw bytes in both Python and Node (the prototype hashes a decoded string). A one-byte edit must read as edited (SPEC R4 adjacency edge). A stale `.new` is overwritten; the original is never touched.

### Pitfall 10: Runner classification must never read the answer
D-27: match stderr and structured fields only; the prototype's blob includes stdout's tail so `assert resp.status == 503` in the model's text classified as transient (audit §4.7). Add a black-box test where the CLI prints an error phrase as its answer and the runner still exits 0.

### Pitfall 11: Tests that need node leak into the unit tier
`make validate` and pre-commit run the whole `unit` group. A test that spawns node or fake CLIs belongs in an `E2E_MODULES` module (or must `skipUnless(shutil.which("node"))` with a visible reason and stay fast). The rendered-script `--self-test` run (R5) is e2e.

### Pitfall 12: Installer launcher on this machine
`~/.local/bin/npx` is a redirect shim: `exec /home/bazzite/.volta/bin/pnpm dlx "$@"` (read this session); `pnpm dlx --help` has no `-y` option. Whether `npx -y` survives the shim is unverified (O6). The approval block already names `pnpm dlx`; resolve the launcher with `shutil.which` and print the exact argv that will run, never an alias (aliases are invisible to `subprocess`).

### Pitfall 13: Reachability URL hygiene
`JEV_API_URL` may carry userinfo (`user:pass@host`). Connect to host:port only; never echo the URL with userinfo; an invalid URL or missing port is "no URL backend" (https defaults to 443, http to 80, as in `decide.reachable`); bound the connect at 1-2 s; IPv6 literals need `socket.create_connection((host, port))`, not string concatenation.

### Pitfall 14: Backups are untracked files in the user's repo
`.planning/config.json.bak-*` are not ignored by default. Whether GSD's doc commits stage them was not verified; the apply report should say where the backups are so the user can ignore or delete them.

### Pitfall 15: Plan values arrive as strings
`plan-set <key> <value>` receives text. Parse as JSON only for keys whose existing plan value is a list/dict/bool/number (type taken from the entry's current `value` or from the key family), otherwise keep the string; then apply the strict encoder. `agent_skills.<agent>` and `review.default_reviewers` are lists of strings; `workflow.*` booleans are booleans.

## Code Examples

### Strict value encoder (D-16)
```python
# Source: derived from ai_kit_spec/gsd_tools.py:150 _coerce_value + live behavior L2
import json, math

_RETYPED = {"true", "false", "null"}

def encode_value_strict(key: str, value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text in _RETYPED or text[:1] in "[{" or _is_finite_number(text):
        raise ValueError(f"{key}: string {text!r} would be re-typed by config-set")
    return text

def _is_finite_number(text: str) -> bool:
    try:
        return math.isfinite(float(text))
    except ValueError:
        return False
```
(`float()` also accepts `inf`/`nan`; `isfinite` excludes them, matching "a finite number" in D-16. Leading-whitespace numerics such as `"  12"` were re-typed live, so test with `.strip()` too.)

### Header, hash and state (Python)
```python
# Source: 18 D-26 + live check of the dogfood file (body sha256 c1cb32d6...)
import hashlib, re
HEADER_RE = re.compile(rb"^// ai-kit-cross-ai generator=(\S+) template=(\d+) sha256=([0-9a-f]{64}|UNSTAMPED)$")

def split(raw: bytes):
    first = raw.index(b"\n"); second = raw.index(b"\n", first + 1)
    return raw[:first], raw[first + 1:second], raw[second + 1:]      # shebang, header, body

def state(raw: bytes) -> str:             # "pristine" | "edited" | "unstamped" | "foreign"
    _, header, body = split(raw)
    m = HEADER_RE.match(header)
    if not m: return "foreign"
    if m.group(3) == b"UNSTAMPED": return "unstamped"
    return "pristine" if hashlib.sha256(body).hexdigest().encode() == m.group(3) else "edited"
```
```js
// Node twin (bytes, not decoded strings): the prototype's headerState decodes; change it.
const raw = fs.readFileSync(p); const a = raw.indexOf(0x0a); const b = raw.indexOf(0x0a, a + 1);
const digest = crypto.createHash('sha256').update(raw.subarray(b + 1)).digest('hex');
```

### Tree id from a temporary index (runner)
```js
// Source: 18 D-27; verified live (L11)
function treeId(cwd) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'xai-idx-')); const env = { ...process.env, GIT_INDEX_FILE: path.join(dir, 'index') };
  try {
    const add = spawnSync('git', ['add', '-A'], { cwd, env }); if (add.status !== 0) return null;
    const wt = spawnSync('git', ['write-tree'], { cwd, env, encoding: 'utf8' }); return wt.status === 0 ? wt.stdout.trim() : null;
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
}
// success in exec mode: exit 0 && non-empty answer && (headAfter !== headBefore || treeAfter !== treeBefore)
// review mode: headAfter === headBefore && treeAfter === treeBefore, else status=contract_violation action=stop
```
A `null` tree id (git failure) must be treated as "unknown": never fall back to the next CLI on unknown (prototype: `before === null` returns the CLI's code).

### Post-write skill verification (D-22 step 7)
```python
# Source: live run L4. Parse stdout JSON only; stderr carries unrelated warnings.
argv = [node, gsd_tools_path, "query", "agent-skills", agent, "--json", "--project-dir", project_dir]
env = {**os.environ, "GSD_RUNTIME": host}            # claude, codex, opencode, cursor; SKIP on pi
data = json.loads(proc.stdout)                        # {"warnings": [...], "block": "...", "skills_count": N (configured!)}
problems = data["warnings"]                           # report verbatim, never fail the apply on them
```

### pi parser contract (D-25 / 22 D-04)
```python
# Source: live L8. Pure, never raises; non-str / bad JSON / success != true -> [].
# return [{"id": f"{m['provider']}/{m['id']}", "reasoning_modes": [lvl for lvl, v in (m.get('thinkingLevelMap') or {}).items() if v],
#          "image_input": 'image' in m.get('input', []), "context_window": m.get('contextWindow')} ...]  (dedupe, first wins)
# snapshot entry: clis.pi = {"installed": True, "path": ..., "models": [ids], "reasoning_modes": {id: [...]}, "image_input": {id: bool}}
```
Fixture rule (22 D-04): trim to a handful of models including one `router-env` entry, drop every `baseUrl`, label provenance in the test docstring like `tests/test_ai_kit_spec.py:105-125` does for codex. Verify with a test that `catalog_build` joins `clis.pi` ids into existing router catalog entries (A5).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `build_execute_command` bare CLI name for `cross_ai_command` | `node .planning/scripts/cross-ai.mjs` generated per project | 2026-10-13 amendment | v1 builders stay until 18.1 D-14 re-points them |
| Bare keys `cross_ai_*` in ROADMAP | `workflow.cross_ai_*` | gsd-core 1.16 (SPEC Background) | Bare names are rejected by `isValidConfigKey` |
| `status --porcelain` for "tree changed" | tree id from a temporary index | 2026-10-14 (D-27) | Sees re-edits of already-dirty and untracked files |
| pi `--list-models` table | RPC `get_available_models` JSON | 22 D-04 | Exact context windows, image input, thinking levels |
| opencode `models --verbose` | `GET /api/model` on the v2 API | Phase 17 D-24 | Not Phase 18's concern, but opencode 2.x flags differ (Correction 11) |

**Deprecated/outdated:** Gemini CLI review lane (retired in gsd-core, see `review-lane-descriptor.cjs` comment); `review.models.antigravity` (the key suffix is `agy`); the design spec §6 timeouts 300/600 (superseded by D-12: >= 1800).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Template lives at `skills/ai-kit-spec-review/references/cross-ai.mjs` with an `ai_kit_spec/cross_ai_template.py` resolver (Claude's discretion in CONTEXT) | Architecture | Low: path is internal; renaming costs one plan edit |
| A2 | `npx -y @opengsd/gsd-core@<ver> --<host> --local` works under the `pnpm dlx` redirect shim | Pitfall 12, follow-ups | Installer follow-up fails on this machine; fall back to printing the exact argv for the user |
| A3 | `review.models.claude` takes a raw string passed to `--model` (alias or full id) | Cross-AI | Wrong lane model value; gsd-core review lane errors at review time |
| A4 | `enabledPlugins` merges per key across user/project/local settings | Skills scan | Plugin skill reported enabled/disabled wrongly |
| A5 | `catalog_build` merges `clis.pi` ids into existing router entries so pi candidates get `router_confirmed` | pi parser | Golden "claude host picks pi with router-env/my-coding" would not hold; needs fixture test first |
| A6 | opencode 2.x review lane fails on `--variant` (inferred from `--help` only) | Cross-AI, O8 | Review lane effort broken for opencode; Phase 20 risk |
| A7 | `npx` runs the bin named after the package when the package has several bins (D-37) | Follow-ups | Installer argv needs `--package`/`-c` form |
| A8 | `cursor-agent models` offline/unauthenticated either fails fast or times out within 15 s | Runner preflight | Preflight stalls; bound it and continue with a note |
| A9 | Skill `description` is truncated at about 300 chars for unknown-skill proposals | Skills | Cosmetic only |

## Open Questions (RESOLVED)

1. **O1 Execution default conflict.** SPEC R3/XAI-02 says `workflow.cross_ai_execution` defaults yes on claude/codex hosts and no on opencode/cursor/pi; shipped `recommend.cross_ai_answers` (`recommend.py:96-123`) defaults exec `y` only for MVP + claude/codex + a cheap other-CLI candidate. Recommendation: follow SPEC when the flag is omitted; with zero eligible targets fall to `n` plus a note (not `needs_choice`). Needs uz confirmation. **RESOLVED: D-39.**
2. **O2 No persisted undo log.** 16.1 keeps undo in memory and the ownership sidecar lives in `ai_kit_spec_gsd` (not importable by the curated-config skill). Apply needs its own persisted marker beside the backup. Recommend not using the sidecar; amend SPEC R13/D-21 wording. **RESOLVED: D-40.**
3. **O3 Trusted-root approval item.** Recommend a plan entry with `status: needs_choice` and candidates; approve = `plan-set <key> '<list>'`, decline = `plan-unset`. **RESOLVED: D-41.**
4. **O4 `apply --inventory`.** Apply needs skill locations/lanes and a digest check, so it takes `--inventory`; D-17/D-22 text does not say so. **RESOLVED: D-42.**
5. **O5 Idle watchdog and `128+n` exit.** Not in SPEC R5/D-27. Recommend: defer the watchdog, keep the status vocabulary and `128+n`. **RESOLVED: D-43 (backlog 999.5).**
6. **O6 Installer launcher.** See A2/Pitfall 12; installer was not run. **RESOLVED: carried fact in 18-CONTEXT (print the exact argv on installer failure); manual check in 18-VALIDATION.**
7. **O7 Claude lane model/effort format.** Raw string vs alias; `xhigh` honored per model only when the candidate's `reasoning_modes` lists it, else lane default `high`. **RESOLVED (RUN-48, orchestrator): `review.models.claude` gets the Claude Code alias the plan already writes on a claude host (D-01; `claude --model` accepts aliases and full ids), and `review.effort.claude` is `xhigh` only when the picked candidate's `reasoning_modes` lists it, else the lane default `high`.**
8. **O8 opencode 2.x has no `--variant`** vs gsd-core review-lane effort argv (Phase 20). **RESOLVED: carried fact (Phase 20 risk note in the plan).**
9. **O9 opencode "bare" profile is partial.** `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS` is documented for `.claude/skills` only; opencode loads `~/.agents/skills` and `~/.config/opencode/skills` regardless. **RESOLVED: carried fact (template comment and SKILL.md say the opencode bare profile is partial).**
10. **O10 `RUNTIMES_SCHEMA_VERSION`.** Renumber 3 -> 4 in Phase 18; 18.1 must restate. **RESOLVED: carried fact (3 -> 4 here; 18.1 restates as current + 1).**
11. **O11 Live timeout.** The runner can honor only the `GSD_WORKSTREAM` env for the live `workflow.cross_ai_timeout` read, not the stored session pointer; D-29 `min(baked, live)`; document the limit. **RESOLVED: carried fact (documented limit).**
12. **O12 `cursor-agent models` preflight offline.** Unverified (not run; it rewrites `~/.cursor/cli-config.json`); existing code uses 15 s; runner continues with a note on listing failure. **RESOLVED: carried fact (15 s bound, continue with a note).**
13. **O13 `enabledPlugins` merge semantics** across settings files (A4). **RESOLVED (RUN-48, orchestrator): plugin enabled state is read from the user-level settings only and reported with an `unverified` label (A4); no per-key merge across settings files is claimed.**
14. **O14 `plan-set workflow.cross_ai_command` guard.** Whether to refuse arbitrary commands without `--force` (command-injection surface; not locked). **RESOLVED: D-44.**
15. **O15 `catalog_build` and `runtimes.pi`** (A5): needs a fixture test before goldens depend on it. **RESOLVED: D-45.**

Also: `skill_affinity.json` is loaded by the CLI, validated, and passed via `RecommendOpts`; the plan records `as_of` and its digest (keeps `recommend` pure).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| node | runner, project-local gsd-tools | yes | v24.21.0 | none (gsd-core engines need >= 24) |
| python3 | all code | yes | 3.14.7 | none |
| uv | wizard/dev tiers | yes | 0.11.28 | none |
| make | `make test`/`validate` | yes | GNU Make 4.4.1 | none |
| git | tree id, commits | yes | 2.55.0 | none |
| shellcheck | `make lint` | yes | present | none |
| pnpm | `npx` redirect shim | yes | 11.18.0 | print installer argv for manual run |
| pi | RPC model listing | yes | 1.2.0 | `clis.pi` empty with note |
| opencode | runner candidate | yes | v2.0.29 | candidate skipped |
| cursor-agent | runner candidate | yes | 2026.10.14-941492e | candidate skipped |
| codex | runner candidate | yes | 0.162.1 | candidate skipped |
| gsd-core (project-local) | apply, followups | yes | 1.16.0 | none (apply refuses without it) |

**Missing with no fallback:** none. **Not exercised live:** the installer follow-up, `cursor-agent models`, model-spending CLI runs.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | stdlib `unittest` via `tools/run_unittest_parallel.py` (groups unit / arch / unit-uv / integration / e2e) |
| Config file | `Makefile`, `tools/gen_test_groups.py` (generated group lists), `E2E_MODULES` |
| Quick run command | `python3 -m unittest tests.test_<module>` |
| Full suite command | `make test` |
| Phase gate | `make validate` and `make test` green; v1 suite `python3 -m unittest tests.test_ai_kit_gsd_curated_config` unchanged (90 tests) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| XAI-01 | lane/target selection, vendor rule, standard 1 / rigorous 2 lanes, empty -> convergence off | unit + goldens | `python3 -m unittest tests.test_curated_config_cross_ai` | Wave 0 |
| XAI-02 | runner renders byte-deterministic; header hash; `.new` on edit; `--self-test` exit classes 0/1/2/69/75/124/127, one `AIKIT-XAI` last line, process-group kill, both git rules | unit (renderer) + e2e (node) | `python3 -m unittest tests.test_curated_config_script tests.test_curated_config_apply_e2e` | Wave 0 |
| SKL-01 | skill scan: plain, symlink escape, project, plugin, per-host root | unit | `python3 -m unittest tests.test_curated_config_skills` | Wave 0 |
| SKL-02 | wiring, caps 2/3/5, jev gating, translation to `global:`/project/`global:<plugin>:<skill>`, agent-skills verification | unit + e2e | same modules | Wave 0 |
| SKL-03 | affinity table, ponytail entries, unknown-skill proposals | unit | `tests.test_curated_config_skills` | Wave 0 |
| SKL-04 | trusted roots per escaping skill, `~`-relative, needs_choice item | unit | `tests.test_curated_config_skills` | Wave 0 |
| APP-01 | `plan-set`/`plan-unset` refusals, atomic, `source: user`, sorted | unit | `python3 -m unittest tests.test_curated_config_plan_edit` | Wave 0 |
| APP-02 | dry-run diff, needs_choice refusal exit 2, pre-flight | unit | `python3 -m unittest tests.test_curated_config_apply` | Wave 0 |
| APP-03 | D-22 order, backup/prune/restore, injected Nth-key failure restores bytes and names key, fourth apply prunes | unit (fake `run_fn`, `now_fn`) + e2e (real gsd-tools) | `tests.test_curated_config_apply`, `tests.test_curated_config_apply_e2e` | Wave 0 |
| APP-04 | follow-up argv pinned, nothing runs without approval flag, effort sync only for claude/codex/opencode | unit | `python3 -m unittest tests.test_curated_config_followups` | Wave 0 |
| EVAL-06 | gates cover new modules; SKILL.md passes skill-judge | gate | `python3 -m unittest tests.test_gate_scope`; `make test`; `make validate` | exists |
| pi parser | RPC JSON -> ids/modes/image | unit | `python3 -m unittest tests.test_ai_kit_spec` | extend |
| encoder | strict value encoder | unit | `python3 -m unittest tests.test_ai_kit_spec_gsd_tools` | extend |

### Sampling Rate
- **Per task commit:** the touched module's `python3 -m unittest tests.<module>` plus `python3 -m unittest tests.test_arch` when `status-line.py` or purity allowlists change.
- **Per wave merge:** `make test-unit` (and `make e2e-test` for waves 4, 6, 7).
- **Phase gate:** `make test` and `make validate` green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] pi RPC fixture (trimmed, `baseUrl` stripped, provenance in docstring)
- [ ] skills/plugin fixtures: plain, symlink escape, project, plugin, claude vs other host
- [ ] jev fixtures plus a sentinel test that the key value never appears in any output
- [ ] regenerated 17 goldens and `tests/test_curated_config_recommend.py:1540-1561,2381` edits; purity-guard allowlist (`:1720`) with a non-vacuity counterpart
- [ ] `python3 tools/gen_test_groups.py` rerun; e2e module added to `E2E_MODULES`
- [ ] fake CLIs on PATH for the runner `--self-test`

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | none; no credentials handled, key presence by name only |
| V3 Session Management | no | not applicable |
| V4 Access Control | yes | trusted roots `~`-relative and per-skill only; project's own gsd-core run only from trusted checkouts (17-SECURITY AR-02) |
| V5 Input Validation | yes | skill-name regex `^[A-Za-z0-9_-]+$`, `isValidConfigKey` batch pre-flight, strict value encoder, plan-set value parsing |
| V6 Cryptography | no | sha256 integrity of the script header only (not authenticity) |
| V10/V14 Supply chain, config | yes | pinned `@opengsd/gsd-core@1.16.0` (SUS "too-new" on latest tag), grouped approval, argv arrays, no shell |
| V12 Files and resources | yes | symlink escape via realpath, atomic writes, `.mjs.new` never overwrites an edited script, backup mode preserved, exclusive create |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Command injection via `workflow.cross_ai_command` or installer argv | Tampering / EoP | fixed rendered string, argv lists, `plan-set` guard (O14) |
| Symlink / path escape in skill scan | Tampering | realpath containment, trusted roots per skill |
| Secret leakage (jev key, URL userinfo, opencode `auth.json`) | Info disclosure | presence-only by name, strip userinfo, never read credential files, sentinel test |
| TOCTOU on backup/restore | Tampering | exclusive create (`os.link`), persisted marker, refuse on stale marker |
| Runner executes CLIs with full permissions unattended | EoP | accepted risk (16/18.1 notes); disclose in SKILL.md; review-mode tree-unchanged rule |
| Installer rewrites `~/.gsd/defaults.json` and scans home dirs on non-Claude `--local` | Tampering | disclose; pass `--no-legacy-cleanup`; require explicit approval |
| Malicious project gsd-core run under node | EoP | trusted checkouts only; documented in SKILL.md |

## Recommended Plan Decomposition (serial, 13 plans)

- **Wave 1 / 18-01:** `ai_kit_spec` additions: `parse_pi_models`/`detect_pi_models`, `clis.pi` in snapshot, `RUNTIMES_SCHEMA_VERSION` 3 -> 4, trimmed fixture, strict encoder in `gsd_tools.py`, presence-only `secret_is_set` in `local_secrets.py`. XAI-02, SKL-04, APP-03.
- **Wave 2 / 18-02:** inventory extensions: `review_lanes[]`, `skills[]` v2 via new `skill_scan.py`, `system_one_backend`, extended key probe set, presets MANAGED keys (`workflow.cross_ai_timeout`, `manager.flags.execute`, `agent_skills_security.trusted_global_roots`); keep `schema_version` 1 additive. XAI-01, SKL-01, SKL-04.
- **Wave 3 / 18-03:** `cross_ai.py` (pure selection) + recommend layer + `artifacts[]` block (pseudo-keys `script:cross-ai.model.pi`) + `manager.flags.execute=--cross-ai` + timeout >= 1800 + golden regen + purity allowlist. **18-04:** `skills.py`, `skill_affinity.json`, caps, jev gating, ponytail entries, trusted-root proposals, golden regen. XAI-01, XAI-02, SKL-02, SKL-03, SKL-04.
- **Wave 4 / 18-05 (a/b):** runner template `references/cross-ai.mjs` with the full contract and black-box `--self-test`; e2e test runs `node --check` and `--self-test`. **18-06:** `cross_ai_script.py` renderer and artifact diff kinds. XAI-02.
- **Wave 5 / 18-07:** `plan_io.load_plan`, `plan_edit.py`, `plan-set`/`plan-unset`. APP-01.
- **Wave 6 / 18-08:** `config_backup.py` (backup/prune/restore + marker). **18-09:** `apply --dry-run`, diff, pre-flight. **18-10:** apply write path (D-22 order, key translation, reconcile, agent-skills verification, E2E). **18-11:** `followups.py`. APP-02, APP-03, APP-04, SKL-02.
- **Wave 7 / 18-12:** SKILL.md v2 flow, README row, gate registration, `/skill-judge` loop (baseline 98/97/99 in 16.1-SKILL-JUDGE-independent.md; need >= 96, no regression), amend REQUIREMENTS/SPEC/CONTEXT for the Corrections. EVAL-06.

Plan constraints: never edit `.planning/scripts/cross-ai.mjs` (live supervisor); each plan is one buildable commit with tests and docs; all commands path-agnostic; `make test` and `make validate` green at the end.

## Project Constraints (from AGENTS.md)

- English only in every written artifact; no mixed languages.
- Runtime code stays stdlib-only; `uv`/`textual` dev- or wizard-only.
- Every config write atomic (`mkstemp` + `os.replace`), reuse `_read_json`/`_write_json`; JSONC edits preserve unrelated bytes.
- Never present inferred, reverse-engineered, or informational results at documented-behavior confidence (flag pi/cursor "not live-validated").
- New or updated SKILL.md passes `skill-judge` (>= 96/120 or no Critical/Important, no regression).
- One coherent buildable commit per change with tests and docs; never `--no-verify`; preserve unrelated dirty work.
- No hardcoded absolute paths in source, tests, or assets; plan commands path-agnostic.
- pylint limits: max-args 5, max-locals 15, max-branches 12, max-returns 6, max-statements 50; ruff line-length 100; pyright basic; vulture 80.
- `tests/test_arch.py` is extended, not bypassed; every structural rule gets a non-vacuity counterpart.
- Tests use temp dirs and synthetic content, never real user configs.
- Scratch files under `./tmp/`; kill any ephemeral process spawned for verification.
- `make test` and `make validate` before done; update READMEs/docs with the feature.

## Sources

### Primary (HIGH confidence, read or run this session)
- `.planning/phases/18-cross-ai-skills-apply-pipeline/18-CONTEXT.md`, `18-SPEC.md`, `17-VERIFICATION.md`
- `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py`, `recommend.py`, `detection.py`, `tests/test_ai_kit_spec.py`
- Project-local gsd-core 1.16.0: `bin/lib/init.cjs:3627-3754`, `bin/lib/security.cjs:177`, live `config-new-project`, `config-set`, `agent-skills`, `effort sync` runs in a scratch project
- Live probes: `pi --mode rpc` `get_available_models`, `--help`/`--version` of opencode, cursor-agent, codex, pnpm
- `.planning/scripts/cross-ai.mjs` and its `--self-test`

### Secondary (MEDIUM)
- opencode, Claude Code settings/plugin documentation (precedence local > project > user)

### Tertiary (LOW, `[ASSUMED]`)
- A1 to A9 above

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (versions read from installed tools and registry)
- Architecture: HIGH for apply/inventory (live-verified gsd-tools behavior); MEDIUM for runner details (prototype plus audit, no new live run of model-spending CLIs)
- Pitfalls: HIGH for items with a live repro; MEDIUM for O-numbered items

**Research date:** 2026-10-15
**Valid until:** 2026-10-22 for CLI behavior (opencode, pi, cursor change fast); 30 days for gsd-core 1.16.0 internals
