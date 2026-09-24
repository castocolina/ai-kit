# Requirements: ai-kit

**Defined:** 2026-09-23
**Core Value:** ai-kit must never corrupt uz's AI-CLI configuration and must never claim more certainty than it has.
**Milestone:** v1.3 GSD Curated Config v2
**Source spec:** `docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md` (approved 2026-09-23)

Previous milestones' requirements are archived in `.planning/milestones/v1.2-REQUIREMENTS.md`
(cumulative v1.0–v1.2).

## v1.3 Requirements

### ai_kit_spec Extensions

- [ ] **SPEC-01**: `detect-current-runtime` identifies pi (`PI_CODING_AGENT`) and codex (`CODEX_THREAD_ID`/`CODEX_VERSION`) in addition to opencode/cursor/claude, with precedence pi > opencode > cursor > claude > codex when several signals are set
- [ ] **SPEC-02**: `detect-runtimes` enumerates codex (`codex debug models`) and claude (hardcoded aliases + full ids from the catalog + dated fallback), invoking real binaries (never shell functions/aliases); parsers covered by fixtures captured from real CLI output (pi moved to SPEC-05 per Phase 16 D-06)
- [ ] **SPEC-03**: Model catalog entries carry optional `image_input` and `reasoning_levels`; cache files without them still load
- [ ] **SPEC-05**: `detect-runtimes` enumerates pi (`pi --list-models`) with a fixture-backed parser, and `pi` is a known CLI (deferred from SPEC-02 to the pi phase, Phase 16 D-06)
- [ ] **SPEC-06**: `cursor-agent` is detected and enumerated even when the user's shell wraps it as a function/alias (real binary located without executing the wrapper; Phase 16 D-06)
- [ ] **SPEC-04**: Ranker supports purposes `planning`, `general`, `mechanical`, `execution`, `review` via the ranking-weights file; `review`/`execute` keep working as aliases

### Inventory

- [ ] **INV-01**: `inventory --project-dir` emits one JSON with host, the host's own gsd-core (path/version/valid keys), host models (scores, price, `image_input`, reasoning levels), other CLIs' models, skills, project facts (frontend, db, CLAUDE.md, intel index), existing config and conflicts
- [ ] **INV-02**: Catalog is read from `~/.cache/ai-kit/spec` and refreshed `--if-stale`; a stale cache is used with a warning when refresh fails; with no cache, Claude/Codex use native tier maps and Cursor/opencode/pi ask the user per slot
- [ ] **INV-03**: Conflicts are detected: `model_policy` in the project or `~/.gsd/defaults.json`, and `runtime` set to another host

### Recommendation

- [ ] **REC-01**: `recommend` is a pure function of inventory + profile + rigor + cross-AI answers; every `plan.json` entry has `key`, `value`, `why`, `source`
- [ ] **REC-02**: Tier layer — `model_profile` (quality/balanced/budget/adaptive, adaptive recommended) plus `models.<phase_type>` only where the rigor preset shifts a whole phase
- [ ] **REC-03**: Tier→model layer — `model_profile_overrides.<host>.{opus,sonnet,haiku}` chosen by role score under the rigor price ceiling (Claude skips unless pinned; Codex ids with `reasoning_effort`; Cursor effort-suffixed ids)
- [ ] **REC-04**: ≤7 specialist `model_overrides` — plan-checker counterpart provider to the planning slot; code-reviewer ≠ execution provider; ui-auditor/dom-verifier with `image_input`; ui-researcher frontend-capable when a frontend exists; executor + code-fixer on the execution role with effort `medium`. A single-provider host gets an explicit "no in-runtime counterpart → use cross-AI review" note
- [ ] **REC-05**: MVP/Standard/Rigorous presets set granularity, effort tiers, gates (nyquist, TDD, code-review depth, ASVS, UI review), `intel.enabled` (Standard and Rigorous) and `dynamic_routing` (Rigorous) per spec §5
- [ ] **REC-06**: Keys unknown to the host's gsd-core version are dropped from the plan with a note

### Cross-AI

- [ ] **XAI-01**: Cross-AI review sets `plan_review_convergence` + `review.default_reviewers` (lane ≠ host, reviewer provider ≠ planning provider, best `review` score) + `review.models.<lane>` / `review.effort.<lane>`
- [ ] **XAI-02**: Cross-AI execution sets `cross_ai_execution` + `cross_ai_command` (built by `build_execute_command`, bare CLI name) with a rigor-dependent timeout, picking the best `execution` score in another CLI; default yes on Claude/Codex and no on opencode/cursor/pi; the report says to run `--cross-ai` and sets `manager.flags.execute`

### Skills

- [ ] **SKL-01**: Skill inventory covers host skill dirs, project `skills/`, and Claude plugin skills (Claude host only)
- [ ] **SKL-02**: `skill_affinity.json` maps skill families to agents gated by project facts (TDD mode, frontend, db), capped per rigor (≈ MVP 2 / Standard 3 / Rigorous 5, file order), shown to the user as bare names and written as `agent_skills.<agent>` in gsd-core's required form (`global:<name>` / project path / `global:<plugin>:<skill>` on claude) (Phase 18 D-02/D-04)
- [ ] **SKL-03**: A recommended-but-missing skill is silently omitted — never mentioned, offered or installed (Phase 18 D-03); unknown installed skills get host-agent-proposed mappings the user confirms; a `trusted_global_roots` entry is proposed for symlinked skills escaping the global root

### Plan and Apply

- [ ] **APP-01**: The user adjusts the plan with `plan-set` / `plan-unset` (`source: user`)
- [ ] **APP-02**: `apply --dry-run` validates every key against the host gsd-core's valid keys and prints a diff without writing
- [ ] **APP-03**: `apply` backs up to `config.json.bak-<ts>`, writes only through `gsd-tools` `config-new-project` / `config-set`, and on any failure restores the backup and names the failing key
- [ ] **APP-04**: Follow-ups (`gsd install <host>`, `effort sync --apply`, `/gsd-map-codebase`) are printed and run only after user approval
- [ ] **APP-05**: After `apply`, `gsd-tools resolve-model <agent>` with `GSD_RUNTIME=<host>` returns the planned model for all 35 agents (integration test against the real gsd-tools)

### Evaluation and Live Validation

- [ ] **EVAL-01**: SKILL.md rewritten for the four-question + review flow; passes writing-skills RED/GREEN pressure scenarios (Cursor MVP, Claude Rigorous with cross-AI, pi with ponytail missing)
- [ ] **EVAL-02**: `/skill-judge` runs as part of code review; SKILL.md scores ≥96/120 with no Critical/Important findings
- [ ] **EVAL-03**: Live smoke on the claude host — `inventory` + `recommend` + `apply` (dry-run, then real on a scratch project)
- [ ] **EVAL-04**: Live smoke on the codex host, including confirmation of the codex session env signal
- [ ] **EVAL-05**: Live smoke on the opencode host, including whether the opencode review lane is usable from an opencode host
- [ ] **EVAL-06**: v2 subcommands coexist with the unchanged v1 CLI (no module removal — Phase 18 D-08); v2 registered in all gates; `make test` (v1 tests still passing) and `make validate` green; README row updated; SKILL.md labels cursor and pi "not live-validated" until EVAL-07/EVAL-08 pass
- [ ] **EVAL-07**: Live smoke on the cursor host (own phase, scheduled after codex/opencode; may run later without blocking earlier phases)
- [ ] **EVAL-08**: Live smoke on the pi host (own phase, scheduled last; may run later without blocking earlier phases)

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
| SPEC-01 | Phase 16 | Pending |
| SPEC-02 | Phase 16 | Pending |
| SPEC-05 | Phase 22 | Pending |
| SPEC-06 | Phase 21 | Pending |
| SPEC-03 | Phase 16 | Pending |
| SPEC-04 | Phase 16 | Pending |
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

**Coverage:**
- v1.3 requirements: 33 total (SPEC 6, INV 3, REC 6, XAI 2, SKL 3, APP 5, EVAL 8). SPEC-05 (pi
  enumeration) and SPEC-06 (cursor wrapper) were split out of SPEC-02 during the Phase 16
  discussion, 2026-09-23.
- Mapped to phases: 33/33
- Unmapped: 0

---
*Requirements defined: 2026-09-23*
*Last updated: 2026-09-23 after v1.3 roadmap creation (Phases 16–22, 100% coverage)*
