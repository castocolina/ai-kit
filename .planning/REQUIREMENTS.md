# Requirements: ai-kit

**Defined:** 2026-09-23
**Core Value:** ai-kit must never corrupt uz's AI-CLI configuration and must never claim more certainty than it has.
**Milestone:** v1.3 GSD Curated Config v2
**Source spec:** `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md` (approved 2026-09-23)

Previous milestones' requirements are archived in `.planning/milestones/v1.2-REQUIREMENTS.md`
(cumulative v1.0–v1.2).

## v1.3 Requirements

### ai_kit_spec Extensions

Host facts (live-verified 2026-10-15): gsd-core: 1.16.0; GSD installs missing on: ~/.codex/gsd-core, ~/.config/opencode/gsd-core, ~/.cursor/gsd-core, ~/.pi/gsd-core; ~/.gsd/defaults.json runtime: codex; Artificial Analysis key: set; Live catalog fetch scored: 150 of 195 entries

- [x] **SPEC-01**: `detect-current-runtime` identifies pi (`PI_CODING_AGENT`) and codex (`CODEX_THREAD_ID`/`CODEX_VERSION`) in addition to opencode/cursor/claude, with precedence pi > opencode > cursor > codex > claude when several signals are set *(2026-10-14: `CODEX_VERSION` is absent from the codex 0.153.4 binary and is expected to be dropped by Phase 20 D-05)*
- [x] **SPEC-02**: `detect-runtimes` enumerates codex (`codex debug models`) and claude (hardcoded aliases + full ids from the catalog + dated fallback), invoking real binaries (never shell functions/aliases); parsers covered by fixtures captured from real CLI output (pi moved to SPEC-05 per Phase 16 D-06)
- [x] **SPEC-03**: Model catalog entries carry optional `image_input` and populated `reasoning_modes` (existing field, per 16 D-08); cache files without them still load
- [ ] **SPEC-05**: `detect-runtimes` enumerates pi (`pi --list-models`) with a fixture-backed parser, and `pi` is a known CLI (deferred from SPEC-02, Phase 16 D-06; moved from Phase 22 to Phase 18 on 2026-10-14, because cross-AI execution prefers pi)
- [ ] **SPEC-06**: `cursor-agent` is detected and enumerated even when the user's shell wraps it as a function/alias (real binary located without executing the wrapper; Phase 16 D-06)
- [x] **SPEC-04**: Ranker supports purposes `planning`, `general`, `mechanical`, `execution`, `review` via the ranking-weights file; `review`/`execute` keep working as aliases

### Inventory

- [ ] **INV-01**: `inventory --project-dir` emits one JSON with host, the host's own gsd-core (path/version/valid keys), model candidates as (runtime, model) pairs (scores, price, `image_input`, reasoning levels; amended 2026-10-14 from separate host/other-CLI lists, per Phase 18.1), skills, project facts (frontend, db, instruction files `AGENTS.md`/`CLAUDE.md`, intel index), existing config and conflicts
- [ ] **INV-02**: Catalog is read from `~/.cache/ai-kit/spec` and refreshed `--if-stale`; a stale cache is used with a warning when refresh fails; with no cache, Claude/Codex use native tier maps and Cursor/opencode/pi ask the user per slot; a catalog with prices but no scores takes the same path (amended 2026-10-14)
- [ ] **INV-03**: Conflicts are detected only when they change resolution: `model_policy` in the project config, `model_policy` in `~/.gsd/defaults.json` when no project config exists, a project `resolve_model_ids: "omit"` on a claude host, and a project `runtime` set to another host. A global value gsd-tools ignores (a global `model_policy` beside a project config, any global `runtime`) is info only (amended 2026-10-14)

### Recommendation

- [ ] **REC-01**: `recommend` is a pure function of inventory + profile + rigor + cross-AI answers; every `plan.json` entry has `key`, `value`, `why`, `source`
- [ ] **REC-02**: Tier layer — `model_profile` (quality/balanced/budget/adaptive, adaptive recommended) plus `models.<phase_type>` only where the rigor preset shifts a whole phase
- [ ] **REC-03**: Tier→model layer — `model_profile_overrides.<host>.{opus,sonnet,haiku}` chosen by role score under the rigor price ceiling (Claude skips unless pinned; Codex ids with `reasoning_effort`; Cursor effort-suffixed ids; `-fast` twins never auto-chosen when the non-fast model exists, amended 2026-10-14)
- [ ] **REC-04**: ≤7 specialist `model_overrides` — plan-checker counterpart provider to the planning slot; code-reviewer ≠ execution provider; ui-auditor/dom-verifier with `image_input`; ui-researcher frontend-capable when a frontend exists; executor + code-fixer on the execution role with effort `medium`. A single-provider host gets an explicit "no in-runtime counterpart → use cross-AI review" note
- [ ] **REC-05**: MVP/Standard/Rigorous presets set granularity, effort tiers, gates (nyquist, TDD, code-review depth, ASVS, UI review), `intel.enabled` (Standard and Rigorous) and `dynamic_routing` (Rigorous) per spec §5
- [ ] **REC-06**: Keys unknown to the host's gsd-core version are dropped from the plan with a note

### Cross-AI

- [ ] **XAI-01**: Cross-AI review sets `workflow.plan_review_convergence` + `review.default_reviewers` (lane ≠ host, reviewer provider ≠ planning provider, best `review` score) + `review.models.<lane>` / `review.effort.<lane>`
- [ ] **XAI-02**: Cross-AI execution sets `workflow.cross_ai_execution` + `workflow.cross_ai_command = node .planning/scripts/cross-ai.mjs`, picking the best `execution` score in another CLI; default yes on Claude/Codex and no on opencode/cursor/pi; the report says to run `--cross-ai` and sets `manager.flags.execute`. *(Amended 2026-10-13, replacing "built by `build_execute_command`, bare CLI name, rigor-dependent timeout".)* curated-config generates the script per project from a template: preference order (default pi > cursor > opencode; grok is not a target), a model per CLI, unattended full-permission flags per CLI, a bare tool profile by default with opt-in skills (SKILL.md paths) or MCP servers. A sha256 header protects user edits: an edited script is never overwritten, and the new version goes to `cross-ai.mjs.new`. `workflow.cross_ai_timeout` is ≥ 1800 s, with the script's own deadline below it. The script follows the supervision contract: finite stdin, model pre-validated against the CLI's list, process-group kill, errors matched on stderr and structured fields only, exit codes 0/1/2/69/75/124/127, one `AIKIT-XAI status=… action=fallback|retry-later|stop` line, falls back to the next CLI only when HEAD and the tree are unchanged, and counts success only when HEAD moved or the tree changed. Every config write goes through `gsd-tools query config-set`; effort keys take effect only after `gsd-tools effort sync --apply`

### Skills

- [ ] **SKL-01**: Skill inventory covers host skill dirs, project `skills/`, and Claude plugin skills (Claude host only)
- [ ] **SKL-02**: `skill_affinity.json` maps skill families to agents gated by project facts (TDD mode, frontend, db), capped per rigor (≈ MVP 2 / Standard 3 / Rigorous 5, file order), shown to the user as bare names and written as `agent_skills.<agent>` in gsd-core's required form (`global:<name>` / project path / `global:<plugin>:<skill>` on claude) (Phase 18 D-02/D-04)
- [ ] **SKL-03**: A recommended-but-missing skill is silently omitted — never mentioned, offered or installed (Phase 18 D-03); unknown installed skills get host-agent-proposed mappings the user confirms; a `trusted_global_roots` entry is proposed for symlinked skills escaping the global root
- [ ] **SKL-04**: When a System One backend is detected, `jev-fast-decision` is recommended in `agent_skills` for `gsd-advisor-researcher` and `gsd-assumptions-analyzer`; never when no backend is present

### Plan and Apply

- [ ] **APP-01**: The user adjusts the plan with `plan-set` / `plan-unset` (`source: user`)
- [ ] **APP-02**: `apply --dry-run` validates every key against the host gsd-core's valid keys and prints a diff without writing
- [ ] **APP-03**: `apply` backs up to `config.json.bak-<ts>`, writes only through `gsd-tools` `config-new-project` / `config-set`, reconciles keys `config-new-project` copied from global defaults against the plan, and on any failure restores the backup and names the failing key
- [ ] **APP-04**: Follow-ups (gsd-core's own installer pinned to the resolved version with local scope, `npx -y @opengsd/gsd-core@<version> --<host> --local`; `effort sync --apply`) run only after one grouped user approval; `/gsd-map-codebase` is only recommended *(amended 2026-10-14: the bare `gsd` binary is a different package)*
- [ ] **APP-05**: After `apply`, `gsd-tools resolve-model <agent>` with `GSD_RUNTIME=<host>` returns the planned model for all 35 agents (integration test against the real gsd-tools)

### Evaluation and Live Validation

- [ ] **EVAL-01**: SKILL.md rewritten for the four-question + review flow; passes writing-skills RED/GREEN pressure scenarios B (Claude Rigorous with cross-AI), C (opencode host with routers, no catalog), D (existing v1-written config), E ("just apply it" pressure); RED baselines = no skill, plus v1 SKILL.md on B/D (Phase 19 D-01/D-02; cursor/pi scenarios moved to Phases 21/22)
- [ ] **EVAL-02**: `/skill-judge` runs as part of code review; SKILL.md scores ≥96/120 with no Critical/Important findings
- [ ] **EVAL-03**: Live smoke on the claude host — `inventory` + `recommend` + `apply` (dry-run, then real on a scratch project)
- [ ] **EVAL-04**: Live smoke on the codex host, including confirmation of the codex session env signal
- [ ] **EVAL-05**: Live smoke on the opencode host, including whether the opencode review lane is usable from an opencode host
- [ ] **EVAL-06**: v2 subcommands coexist with the unchanged v1 CLI (no module removal — Phase 18 D-08); v2 registered in all gates; `make test` (v1 tests still passing) and `make validate` green; README row updated; SKILL.md labels cursor and pi "not live-validated" until EVAL-07/EVAL-08 pass
- [ ] **EVAL-07**: Live smoke on the cursor host (own phase, scheduled after codex/opencode; may run later without blocking earlier phases)
- [ ] **EVAL-08**: Live smoke on the pi host (own phase, scheduled last; may run later without blocking earlier phases)

### Hardening

- [x] **HARD-01**: The pre-commit gate covers every shipped Python file and `make validate` runs every test module; `make validate` is green
- [x] **HARD-02**: Skill-embedded Python resolves sibling packages before `~/.claude/skills`, with a test proving a branch checkout imports branch code
- [x] **HARD-03**: A project-local reviewer command runs only after the user trusts its file (per content hash), and no reviewer command runs with `shell=True`; the dashboard escapes `<` against case-variant `</script` breakouts
- [x] **HARD-04**: A failed review lane never merges into Approved; error classifiers read only stderr and structured error fields; inherited host env signals are scrubbed from child processes; the unrunnable claude and grok execute builders are deleted; `gsd_config.py` writes via `config-set`
- [ ] **HARD-05**: The audit's smaller safety items are fixed (codegraph probe timeout and no silent global install, reported `review-spec.toml` parse errors, `install.sh --branch`/`--dry-run` on an existing clone, unique cache temp names, atomic uninstall write, AGENTS.md checker image links); GSD-adjacent code resolves the project-local gsd-core before any global one

### One Runtime Model

- [ ] **RTM-01**: Model candidates are (runtime, model) pairs: native subagent when the runtime is the current host and the host can select the model, subprocess through `cross-ai.mjs` otherwise; `native_runtime` is removed, and old configs carrying it load with a visible note
- [ ] **RTM-02**: The `native_claude` naming and the cursor / cursor-agent split are removed (one `cursor` runtime id, binary `cursor-agent`)
- [ ] **RTM-03**: Affected SKILL.md files and AGENTS.md's Architecture section use the one-model wording; each rewritten SKILL.md passes `/skill-judge`

### Spec-and-Discuss Chain Skill

- [ ] **SDC-01**: An installable ai-kit skill runs `/gsd-spec-phase N --auto` then `/gsd-discuss-phase --analyze --all --batch --assumptions N` for each phase of a given range, or proposes the not-yet-discussed range and asks once
- [ ] **SDC-02**: Decision models are optional and detected (Laya health, a TypeSafe key present by name with no hardcoded path, jev-fast-decision install; amended 2026-10-14); the ladder is Laya (one item per call) → TypeSafe direct on `needs_fallback` → the main model's reasoning; with no backend the chain still completes; remote calls need standing consent and carry summaries only
- [ ] **SDC-03**: Each decision is logged with one column per backend and the locked decision with its reason; doc-contradicting model answers are overridden and logged; the chain stops only on a critical, contradictory question
- [ ] **SDC-04**: The best design wins over the smallest diff, except under `workflow.mvp_mode` (simpler design, without lowering what reaches the product's user); the skill is registered in setup and README and passes `/skill-judge`

### Cursor Executor Agents

- [ ] **AGT-01**: ai-kit ships Cursor executor subagents `composer-worker` (pinned to non-fast `composer-2.5`) and `grok-worker` (pinned to the explicit non-fast `grok-4.7-medium`; amended 2026-10-14, a bare `grok-4.7` resolves through local `modelParameters`), with short bodies for executing an already-planned task and names that do not collide with the 35 GSD agents. They live in their own `cursor-agents/` folder (never `agents/`, which links into `~/.claude/agents` where Claude would load an unrunnable model pin), added to `tools/setup.py` as a fourth category whose link target is `~/.cursor/agents` (honoring `CURSOR_CONFIG_DIR`). The wizard's Choose step lists the category only when Cursor is detected (same detection as the Cursor hook wiring), and a headless `--cursor-agents=all|name1,name2` flag mirrors `--skills`; tests cover the wizard row and the headless link. Ordered after the `worktree-context-tools-manager-plan1` land-or-shelve decision (same `setup.py`/`wizard_app.py` seams). A live delegation from a cursor parent shows the pinned model in the Task call, and one run is confirmed non-fast in the Cursor usage dashboard (pin an explicit effort-suffixed id if the bare id relies on local `modelParameters`)

### Host-Split Status Line

- [ ] **STL-01**: `tools/status-line.py` splits into host-neutral `common_*` modules, `claude_*` host modules and a thin `claude-status-line.py` entry; the Claude render is byte-identical; a hard rename with an idempotent, atomic migration of the Claude `statusLine.command` and `statusline.toml` ships in the same change; the split files stay ruff/pylint clean; the stale status-line pipeline doc is fixed or deleted
- [ ] **STL-02**: A `cursor-status-line.py` entry renders model, context and three separately placeable quota segments (API, included, extra against its ceiling) plus the billing-cycle reset; every quota segment on both hosts uses the shared gap gauge (bands 5/10/15, sign kept); Cursor quota is marked inferred (`≈`)
- [ ] **STL-03**: `cursor_quota.py` is the only network and credential code: HTTPS to `*.cursor.sh` only (`CURSOR_API_ENDPOINT` validated), no cross-origin redirects, token never persisted or logged; the cache separates `data_fetched_at` from `last_attempt_at`/`last_error`, hides quota on 401/403 and after `cycle_end`; every `git` call has a timeout; resets show in local time; a bad TOML value renders an error segment; redacted real Dashboard responses are fixtures
- [ ] **STL-04**: Render-versus-fetch timing is measured in a spike before choosing an inline fetch with a cache or a background refresher
- [ ] **STL-05**: `setup.py --with-statusline[=claude,cursor]` wires each detected host headless, and the wizard runs verify/replace/keep per detected host; both entries are reachable after v1.3 merges; `tests/test_arch.py` covers the new modules; `make test` and `make validate` are green

### Quota Resilience

- [ ] **QTA-01**: A per-CLI table of quota, limit and billing message patterns, built from observed child output and labelled verified/unverified, classifies a stop as wait-recoverable or not by route: billing or limit errors on a router-backed route (`infer_fallback_quota`) are wait-recoverable (fallback chains return to subscription tiers within minutes or hours); billing or access errors on a direct third-party provider route (OpenCode Zen, Cursor API models) are not
- [ ] **QTA-02**: Limits are detected live in the child's stdout/stderr and after the fact (timeout or partial exit), feeding the shared typed reason (16.1 D-13) and the runner's status line (18 D-27, 18.1 D-12)
- [ ] **QTA-03**: A wait-recoverable stop is re-checked every 10 minutes for at most 4 hours; resume checks the working tree and re-dispatches only unfinished work; after 4 hours it stops and reports; the policy runs in the runner and in `ai-kit-spec-review`/`ai-kit-spec-execute*`, replacing the hourly `CronCreate` wake
- [ ] **QTA-04**: The orchestrating session sets an hourly self-wake that survives its own quota stall, chosen per host by survival (OS timer or cloud routine over in-session primitives), with unverified host behavior flagged *(amended 2026-10-14, 26 D-03: the wake resumes the exact session id; cloud routines cannot re-enter a local session, so the surviving primitive is an OS timer)*
- [ ] **QTA-05**: `ai-kit-project-rules-agents` gains an OpenGSD-only rule that checks and remediates the session-resume and subprocess-quota directives as separate items *(amended 2026-10-14, 26-SPEC R7: two rules, R18 and R19)*

- [ ] **QTA-06**: `ai-kit-project-rules-agents` gains a language-agnostic rule, active for every project with a detected stack, that checks and remediates an AGENTS.md rule: unit tests run in parallel with a worker count of at most 40% of the available CPUs, never a hardcoded core count, written in the detected stack's own form *(added 2026-10-14 by uz; 26 D-27)*

### Goal-Prompt Skill

- [ ] **GPS-01**: A skill detects the host, its goal/loop/schedule primitives (tools, not only slash commands) and the GSD/OpenGSD or superpowers scope, and picks one to three strategies from a selection matrix (`/goal`, schedule or `/loop`, `/gsd-autonomous`)
- [ ] **GPS-02**: It emits a `.md` with a ready-to-paste prompt carrying rails (AGENTS.md first, candidate skills, pre-commit, done checks, stop-if, final summary), one subagent per superpowers plan, cross-AI convergence declared per OpenGSD plan, and the QTA quota directives
- [ ] **GPS-03**: The definition of done requires the project's real e2e tests (app launch, PTY/TUI drive, browser for web) to pass, with the evidence printed into the transcript; with no e2e suite, creating one comes first
- [ ] **GPS-04**: jev is advisory and text-only (objective closeness), never a gate and never a UI-quality or mockup-fidelity judge; the skill passes `/skill-judge`

## Future Requirements

None deferred beyond v1.3 at definition time.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Portable multi-runtime configs | Explicit decision: the config targets the host runtime only |
| API keys and integrations | Stay in `/gsd-config --integrations` |
| Installing skills or CLIs without consent | Config-safety constraint; missing skills are explained and offered only |
| Using `model_policy` | Only selects stale named-provider presets and would shadow `model_profile_overrides` |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SPEC-01 | Phase 16 | Complete |
| SPEC-02 | Phase 16 | Complete |
| SPEC-05 | Phase 18 | Pending |
| SPEC-06 | Phase 21 | Pending |
| SPEC-03 | Phase 16 | Complete |
| SPEC-04 | Phase 16 | Complete |
| INV-01 | Phase 17 | Pending |
| INV-02 | Phase 17 | Pending |
| INV-03 | Phase 17 | Pending |
| REC-01 | Phase 17 | Pending |
| REC-02 | Phase 17 | Pending |
| REC-03 | Phase 17 | Pending |
| REC-04 | Phase 17 | Pending |
| REC-05 | Phase 17 | Pending |
| REC-06 | Phase 17 | Pending |
| XAI-01 | Phase 18 | Pending |
| XAI-02 | Phase 18 | Pending |
| SKL-01 | Phase 18 | Pending |
| SKL-02 | Phase 18 | Pending |
| SKL-03 | Phase 18 | Pending |
| SKL-04 | Phase 18 | Pending |
| APP-01 | Phase 18 | Pending |
| APP-02 | Phase 18 | Pending |
| APP-03 | Phase 18 | Pending |
| APP-04 | Phase 18 | Pending |
| EVAL-06 | Phase 18 | Pending |
| EVAL-01 | Phase 19 | Pending |
| EVAL-02 | Phase 19 | Pending |
| EVAL-03 | Phase 19 | Pending |
| APP-05 | Phase 19 | Pending |
| EVAL-04 | Phase 20 | Pending |
| EVAL-05 | Phase 20 | Pending |
| EVAL-07 | Phase 21 | Pending |
| EVAL-08 | Phase 22 | Pending |
| AGT-01 | Phase 21 | Pending |
| HARD-01 | Phase 16.1 | Complete |
| HARD-02 | Phase 16.1 | Complete |
| HARD-03 | Phase 16.1 | Complete |
| HARD-04 | Phase 16.1 | Complete |
| HARD-05 | Phase 16.1 | Pending |
| RTM-01 | Phase 18.1 | Pending |
| RTM-02 | Phase 18.1 | Pending |
| RTM-03 | Phase 18.1 | Pending |
| SDC-01 | Phase 24 | Pending |
| SDC-02 | Phase 24 | Pending |
| SDC-03 | Phase 24 | Pending |
| SDC-04 | Phase 24 | Pending |
| STL-01 | Phase 23 | Pending |
| STL-02 | Phase 23 | Pending |
| STL-03 | Phase 23 | Pending |
| STL-04 | Phase 23 | Pending |
| STL-05 | Phase 23 | Pending |
| QTA-01 | Phase 25 | Pending |
| QTA-02 | Phase 25 | Pending |
| QTA-03 | Phase 25 | Pending |
| QTA-04 | Phase 26 | Pending |
| QTA-05 | Phase 26 | Pending |
| QTA-06 | Phase 26 | Pending |
| GPS-01 | Phase 27 | Pending |
| GPS-02 | Phase 27 | Pending |
| GPS-03 | Phase 27 | Pending |
| GPS-04 | Phase 27 | Pending |

**Coverage:**
- v1.3 requirements: 61 total (SPEC 6, INV 3, REC 6, XAI 2, SKL 4, APP 5, EVAL 8, AGT 1, HARD 5, RTM 3, SDC 4, STL 5, QTA 5, GPS 4). SPEC-05 (pi
  enumeration) and SPEC-06 (cursor wrapper) were split out of SPEC-02 during the Phase 16
  discussion, 2026-09-23.
- Mapped to phases: 61/61
- Unmapped: 0

---
*Requirements defined: 2026-09-23*
*Last updated: 2026-10-14 — Phases 25–27 (QTA, GPS) added from the quota/goal-prompt todo; Phase 23 (STL) defined; Phase 24 (SDC) added, SKL-04 added; earlier: 16.1 (HARD), 18.1 (RTM), XAI-02 amended (100% coverage)*
