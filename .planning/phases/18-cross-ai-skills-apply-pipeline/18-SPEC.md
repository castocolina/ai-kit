# Phase 18: Cross-AI, Skills & Apply Pipeline — Specification

**Created:** 2026-10-14
**Ambiguity score:** 0.13 (gate: ≤ 0.20)
**Requirements:** 15 locked

## Goal

On top of Phase 17's `inventory`/`recommend`, the user can adjust `plan.json`, get cross-AI
review lanes and a generated cross-AI execution script, get per-agent skills wired in the form
gsd-core requires, and apply the plan to a project's `.planning/config.json` through gsd-tools
with a dry-run diff, backups, restore on failure and one grouped approval for follow-ups. v1
keeps working unchanged.

## Background

- **Phase 17 produces the plan contract.** Entries carry `op` (`set | unset | keep`), `source`
  (`preset | catalog-score | curated-affinity | router-declared | user | native`), `existing`
  and `why`. Cross-AI answers of yes leave `needs_choice` placeholders for the reviewer list and
  the execution command (17 D-19). Candidates carry `fast_twin_of` (17 D-13), vendors are
  inferred strictly (17 D-14) and valid keys are probed per key (17 D-09).
- **Live key names (gsd-core 1.16, checked 2026-10-14).**
  - The cross-AI keys live under `workflow.`: `workflow.plan_review_convergence`,
    `workflow.cross_ai_execution`, `workflow.cross_ai_command` and `workflow.cross_ai_timeout`.
    The bare names in the ROADMAP are rejected by `isValidConfigKey`.
  - `review.default_reviewers`, `review.models.<lane>`, `review.effort.<lane>`,
    `manager.flags.execute`, `agent_skills.<agent>` and
    `agent_skills_security.trusted_global_roots` are valid.
  - `review.models.pi` is rejected: pi has no review lane.
  - The effort keys are `effort.default`, `effort.routing_tier_defaults.<light|standard|heavy>`
    and `effort.agent_overrides.<agent>`. `gsd-tools effort sync` is the only effort
    subcommand.
- **Lanes come from gsd-core's capability registry** (`bin/lib/capability-registry.cjs`). A
  lane's key suffix can differ from its slug (Antigravity: slug `antigravity`, key
  `review.models.agy`), so the registry is the source for both.
- **Plugin skills.** `init.cjs` accepts `global:<seg>(:<seg>)*` and turns a plugin-namespaced
  reference into a Skill-tool directive. That directive works on Claude only. Ponytail 5.1.0 is
  installed as a Claude plugin with the skills `ponytail`, `ponytail-review`, `ponytail-audit`,
  `ponytail-debt`, `ponytail-gain` and `ponytail-help`. The plugin also ships `AGENTS.md` and
  `gemini-extension.json`.
- **The installer command.** The bare `gsd` on this machine's PATH is a different package
  (`@opengsd/gsd-pi`), and its loader crashes. gsd-core's own installer is
  `npx -y @opengsd/gsd-core@<version> --<host> --local`. Machine-level GSD installs belong to
  tools-installer.
- **Dogfood prototype.** `.planning/scripts/cross-ai.mjs` (479 lines, `template=1` header) runs
  in this repo with pi first. Its exit-code table predates XAI-02 (it passes the CLI's own code
  through), so the template must be brought to the XAI-02 contract.
- **18-CONTEXT D-01..D-14 stay locked.** They cover lanes per rigor, bare skill names, silent
  omission, caps per rigor, the grouped follow-up, 3 backups, unset through `config-set`, v1
  intact, and the 2026-10-13 runner amendment.

## Requirements

1. **Plan adjustment** (APP-01): the user edits the plan, and the plan remembers it.
   - Current: none.
   - Target:
     - `plan-set <key> <value> [--force]` and `plan-unset <key>` rewrite `plan.json` atomically and record `source: user`.
     - A key the inventory's probe rejected is refused.
     - A model that is not a candidate of a `needs_choice` slot is refused unless `--force`.
     - Pinning a model that has `fast_twin_of` set warns.
     - Filling a cross-AI placeholder clears its `needs_choice`.
   - Acceptance: fixtures cover a rejected key (exit 2), a non-candidate refused and then forced, the `-fast` warning, and a filled placeholder. Output is byte-stable.

2. **Review lanes** (XAI-01): reviewers are another CLI and another vendor.
   - Current: v1 `detect-review-candidate`; `CLI_TO_REVIEWER_SLUG` covers opencode, cursor and claude only.
   - Target:
     - A lane is a capability-registry reviewer slug whose CLI is installed and is not the host. pi is never a lane.
     - The reviewer's inferred vendor differs from the planning slot's.
     - The lane model is a declared `review` router first, otherwise the best `review` score (ties per 17 D-06).
     - Standard uses 1 lane. Rigorous uses 2 when two eligible lanes exist, and the second vendor differs from both the planner's and the first reviewer's; otherwise 1 lane plus a note. MVP leaves convergence off.
     - The plan sets `workflow.plan_review_convergence`, `review.default_reviewers`, `review.models.<key-suffix>` and `review.effort.<key-suffix>`, with the suffix taken from the registry.
   - Acceptance: golden plans for each host and rigor show the lane count and the vendor rules. A fixture with one eligible lane under Rigorous shows 1 lane and the note. No plan names the host or pi as a lane.

3. **Execution targets** (XAI-02): another CLI runs the plans, with one model each.
   - Current: v1 `apply-execution` with a bare CLI name.
   - Target:
     - `workflow.cross_ai_execution` defaults to yes on claude and codex hosts, no on opencode, cursor and pi.
     - The targets are the preference order (default pi > cursor > opencode) filtered to installed CLIs that are not the host. grok is never a target.
     - Each target's model is a declared `execute` router first, otherwise the best `execution` score within the rigor ceiling (17 D-03).
     - An empty target list leaves a `needs_choice`.
     - The report tells the user to run `--cross-ai`, and the plan sets `manager.flags.execute` to `--cross-ai`.
   - Acceptance: golden plans on a claude host pick pi with `router-env/my-coding`. A fixture without pi falls to cursor. A fixture with no other CLI keeps `needs_choice`.

4. **Script generation** (XAI-02): the per-project runner never loses a user edit.
   - Current: the hand-placed dogfood file.
   - Target:
     - `apply` renders `.planning/scripts/cross-ai.mjs` from a versioned template shipped with the skill.
     - The header records the generator, the template version and the sha256 of the body.
     - An absent file, or one whose body still matches its header, is written atomically.
     - An edited file is never overwritten: the new render goes to `cross-ai.mjs.new` with a note.
     - `workflow.cross_ai_command` is `node .planning/scripts/cross-ai.mjs`.
     - The tool profile is bare by default (pi `--no-skills --no-extensions`, opencode with Claude-skill loading off). Skills by SKILL.md path, or MCP servers, are opt-in.
   - Acceptance: tests for absent, unedited (same bytes on re-render), edited (`.new` written, original untouched) and a template-version bump. The rendered command splits into argv without a shell.

5. **Supervision contract** (XAI-02): GSD can trust the script's outcome.
   - Current: the prototype passes the CLI's own exit code through.
   - Target:
     - stdin is finite, and the model is validated against the CLI's own list before spawning.
     - The deadline kills the whole process group.
     - Errors are matched on stderr and structured fields only, never on the answer text.
     - Exit codes are 0, 1, 2, 69, 75, 124 and 127, and exactly one `AIKIT-XAI status=… action=fallback|retry-later|stop` line is printed.
     - It falls back to the next CLI only when HEAD and the working tree are unchanged.
     - Success counts only when HEAD moved or the tree changed.
   - Acceptance: the script's offline `--self-test` covers each exit code, the status line, process-group kill and both git-state rules. A Python test runs the self-test of a rendered script.

6. **Timeout** (XAI-02): the outer limit always wins the race.
   - Current: this repo uses 1800 by hand.
   - Target: `workflow.cross_ai_timeout` ≥ 1800 s, and the script's inner deadline is strictly below it.
   - Acceptance: the plan never sets less than 1800. A rendered script's default deadline is less than the configured timeout.

7. **Skill inventory** (SKL-01): every visible skill, with its real location.
   - Current: Phase 17 lists skill directories only.
   - Target: the inventory lists:
     - the host's global skills directory, resolved the way gsd-core resolves it for the host runtime;
     - the project's `skills/`;
     - Claude plugin skills, on a claude host only.

     Each skill records its name, its real path and whether that path escapes its root.
   - Acceptance: fixtures with a plain skill, a symlinked skill outside the root, a project skill and a plugin skill (claude host versus another host) report correctly.

8. **Skill affinity** (SKL-02): the right skills on the right agents, in gsd-core's form.
   - Current: none.
   - Target:
     - `skill_affinity.json` maps skill families to agents, gated by project facts (TDD mode, frontend, db), and is capped per rigor (MVP 2, Standard 3, Rigorous 5) in file order.
     - `plan.json` shows bare names.
     - `apply` writes `agent_skills.<agent>` as `global:<name>` (host global dir), a project-relative path (project `skills/`), or `global:<plugin>:<skill>` (Claude plugin, claude host only).
   - Acceptance: golden plans never exceed the cap. A frontend-gated skill appears only with a frontend fixture. The written values pass gsd-core's own reference check (`agent-skills` resolution in a scratch project) with no skip warning.

9. **Missing and unknown skills** (SKL-03): nothing is offered or installed.
   - Current: none.
   - Target:
     - A recommended skill that is not installed is omitted, with no mention.
     - An unknown installed skill gets a proposed mapping from its description, which the user confirms.
     - A symlinked skill whose real path escapes the global root gets a proposed `agent_skills_security.trusted_global_roots` entry.
   - Acceptance: plan, report and notes never name an uninstalled recommended skill. An unknown skill appears only as a proposal. An escaping symlink yields one proposed trusted root.

10. **Ponytail set** (ROADMAP SC6): first-class on Claude, checked elsewhere.
    - Current: 18-CONTEXT's "ponytail does not exist" note is stale.
    - Target:
      - `skill_affinity.json` maps `ponytail` → planner, executor, code-fixer; `ponytail-review`/`ponytail-audit` → code-reviewer and the auditors; `ponytail-debt` → planner or verifier, within the cap.
      - On claude these are written as `global:ponytail:<skill>`.
      - For every other host, the inventory checks whether the skills are visible in that host's global skills directory, and records the result. A host that cannot address them gets nothing (R9).
    - Acceptance: golden plans on claude include the set within the cap. A non-Claude fixture without visible ponytail skills has none. The check result is recorded in SKILL.md.

11. **System One decision agents** (SKL-04): jev only when a backend exists.
    - Current: this repo sets it by hand.
    - Target:
      - `jev-fast-decision` is recommended for `gsd-advisor-researcher` and `gsd-assumptions-analyzer` only when the skill is installed and a backend is detected.
      - A backend means either a health probe succeeding at `JEV_API_URL` (or the documented local default), or a key present by name in `JEV_API_KEY` or ai-kit's secrets file.
      - No machine-specific path is used, and no key value enters the inventory or the plan.
    - Acceptance: fixtures for skill without backend (none), backend without skill (none), skill with a healthy probe and skill with a key by name (both recommended). A test asserts that the key value never appears in output.

12. **Dry run** (APP-02): see everything, write nothing.
    - Current: none.
    - Target:
      - `apply --dry-run` re-validates every key against the host gsd-core at apply time and refuses (exit 2) while any `needs_choice` remains.
      - It prints an add / change / keep / remove diff (from `op`, `existing` and `value`) and writes nothing.
    - Acceptance: a dry run leaves the project byte-identical. A plan with one `needs_choice` exits 2 naming it. The diff shows all four kinds.

13. **Apply** (APP-03): safe writes with a way back.
    - Current: v1 writes per key with no backup.
    - Target:
      - `apply` backs up to `.planning/config.json.bak-<timestamp>` and keeps the newest 3.
      - It creates the config with `gsd-tools config-new-project` when it is absent. That command copies `~/.gsd/defaults.json`, so `apply` re-reads the new config and reconciles the copied keys against the plan's managed families (for example a copied `resolve_model_ids: "omit"` on claude, or a copied `model_policy`) before writing. It then writes each entry with `gsd-tools query config-set`, unsetting object-valued keys per leaf (18 D-07 as amended).
      - On any failure it restores the backup and names the failing key.
      - It reuses Phase 16.1's shared gsd-tools resolver, ownership sidecar and undo log.
    - Acceptance:
      - an integration test against the real gsd-tools in a scratch project applies a golden plan;
      - an injected failure on the Nth key restores the original bytes and names the key;
      - a fourth apply prunes the oldest backup.

14. **Follow-ups** (APP-04): one approval and the real installer.
    - Current: none.
    - Target:
      - After a successful `apply`, the required follow-ups are listed and run only after one grouped yes/no:
        - gsd-core's own installer, pinned to the version the inventory resolved, with local scope (`npx -y @opengsd/gsd-core@<version> --<host> --local`), when the host bakes models into agents (opencode, per Phase 20 D-03);
        - `gsd-tools effort sync --apply` against the project's local install when effort keys changed.
      - `/gsd-map-codebase` is only recommended.
      - Machine-level installs are never run.
    - Acceptance: with no approval, nothing runs. With approval, each command's result is reported. The installer argv carries the pinned version and `--local`, and never a bare `gsd`.

15. **Coexistence and gates** (EVAL-06): v2 next to v1, green.
    - Current: the v1 CLI with 11 subcommands.
    - Target:
      - v1 and its modules work unchanged next to `inventory`, `recommend`, `plan-set`, `plan-unset` and `apply`.
      - The new modules are in every gate (test discovery, pyright, vulture, pylint).
      - The README row is updated, and SKILL.md documents v2 as the primary flow and labels cursor and pi "not live-validated".
    - Acceptance: the v1 test suite passes unmodified. `make test` and `make validate` are green. SKILL.md passes `/skill-judge` (≥ 96/120 or no Critical/Important finding).

## Boundaries

**In scope:**
- `plan-set`, `plan-unset` and `apply` (with `--dry-run`)
- Review-lane and execution-target selection, the cross-AI script template and its renderer
- Skill inventory, `skill_affinity.json` (ponytail and jev included), reference-form translation
- Backups, restore, follow-ups behind one approval
- Gate registration, the README row and the SKILL.md v2 flow

**Out of scope:**
- `inventory`/`recommend` internals: Phase 17
- The (runtime, model) schema change inside `ai_kit_spec`: Phase 18.1
- The `resolve-model` check for all 35 agents (APP-05) and the RED/GREEN skill evaluation: Phase 19
- Live validation on codex/opencode (Phase 20), the cursor wrapper (Phase 21), pi enumeration (Phase 22)
- Machine-level GSD installs, pi repair and plugin installs: tools-installer
- Removing v1 (18 D-08)

## Constraints

- Runtime code is stdlib-only, and the generated script uses only Node's standard library.
- Every config write goes through gsd-tools. Plan and script writes are atomic (`tempfile.mkstemp()` + `os.replace()`).
- No secret value is read into the inventory, the plan or any output.
- Nothing is installed without the grouped approval, and a missing skill is never offered.
- No machine-specific absolute path in source, template, fixtures or plan.

## Acceptance Criteria

- [ ] `plan-set`/`plan-unset` record `source: user`, refuse rejected keys, refuse non-candidates unless `--force`, and warn on `-fast` pins
- [ ] No plan names the host or pi as a review lane; reviewer vendors differ from the planner's; Rigorous uses 2 lanes when eligible
- [ ] On a claude host the execution target is pi with the declared router; the fallbacks follow the preference order
- [ ] An edited `cross-ai.mjs` is never overwritten, and `.new` receives the render
- [ ] The rendered script's self-test covers exit codes 0/1/2/69/75/124/127, the single status line and both git-state rules
- [ ] `workflow.cross_ai_timeout` ≥ 1800 and the script deadline is below it
- [ ] The skill inventory reports real paths, root escapes, and plugin skills on claude only
- [ ] Written `agent_skills` values resolve in gsd-core with no skip warning, within the rigor cap
- [ ] No uninstalled recommended skill is ever named
- [ ] The ponytail set is wired on claude, and non-Claude visibility is recorded
- [ ] jev is recommended only with the skill plus a detected backend
- [ ] `apply --dry-run` writes nothing and refuses on `needs_choice`
- [ ] A failed `apply` restores the original bytes and names the key; only 3 backups remain
- [ ] Follow-ups run only after one approval, with the pinned local installer
- [ ] The v1 tests pass unmodified; `make test` and `make validate` are green
- [ ] MUST NOT: no secret value appears in inventory, plan or output
- [ ] MUST NOT: the host CLI is never a review lane or an execution target
- [ ] MUST NOT: nothing is installed, and no follow-up runs, without the grouped approval

## Edge Coverage

**Coverage:** 47/49 applicable edges resolved · 2 unresolved

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | Setting a key to its current value is a no-op entry with `source: user` |
| empty | R1 | ✅ covered | `plan-unset` of an absent key exits 2 naming it |
| ordering | R1 | ✅ covered | Entries stay sorted by key after every edit |
| boundary | R2 | ✅ covered | Exactly one eligible lane under Rigorous gives 1 lane plus the note |
| precision | R2 | 🧪 backstop | Review scores compare at full precision (`score_exact`) |
| boundary | R3 | ✅ covered | A host that is itself the first preference is skipped |
| adjacency | R3 | ✅ covered | Equal execution scores break by price, then id |
| empty | R3 | ✅ covered | No other installed CLI leaves `needs_choice` |
| ordering | R3 | ✅ covered | The target order follows the preference list, not the install order |
| precision | R3 | 🧪 backstop | A price exactly at the ceiling counts as within |
| adjacency | R4 | ✅ covered | A body differing only in a trailing newline counts as edited |
| empty | R4 | ✅ covered | An absent `.planning/scripts/` is created |
| ordering | R4 | 🧪 backstop | The header is always the second line after the shebang |
| idempotency | R4 | ✅ covered | Re-rendering an unedited file gives identical bytes |
| concurrency | R4 | 🧪 backstop | Atomic replace; a stale `.new` is overwritten, never the original |
| adjacency | R5 | ✅ covered | A HEAD move with a clean tree counts as success |
| empty | R5 | ✅ covered | Empty stdin exits 2 |
| ordering | R5 | ✅ covered | The status line is the last stderr line |
| unclassified | R6 | ⚠ UNRESOLVED | No shape cue; the 1800 floor and the strict inequality are in Acceptance |
| adjacency | R7 | ✅ covered | A skill visible in two roots is listed once per root with its real path |
| empty | R7 | ✅ covered | No skills directory gives an empty list, not an error |
| ordering | R7 | ✅ covered | Skills are sorted by root, then name |
| empty | R8 | ✅ covered | No matching family gives no `agent_skills` entry for that agent |
| encoding | R8 | ✅ covered | Plugin references use only `[A-Za-z0-9_-]` segments (gsd-core's own pattern) |
| idempotency | R8 | ✅ covered | Applying the same plan twice writes the same values |
| concurrency | R8 | 🧪 backstop | Writes are sequential through gsd-tools |
| unclassified | R9 | ⚠ UNRESOLVED | No shape cue; omission and proposals are specified in Acceptance |
| boundary | R10 | ✅ covered | The set is cut at the rigor cap in file order |
| adjacency | R10 | ✅ covered | An agent that already holds a ponytail skill from another family gets no duplicate |
| empty | R10 | ✅ covered | No ponytail plugin gives no entries |
| ordering | R10 | ✅ covered | File order decides which skills survive the cap |
| precision | R10 | 🧪 backstop | Visibility is recorded per host, not inferred from one host |
| empty | R11 | ✅ covered | An empty `JEV_API_URL` falls back to the documented default only |
| encoding | R11 | ✅ covered | The key is checked by name only; its value never enters output |
| adjacency | R12 | ✅ covered | A key whose value equals `existing` shows as keep |
| empty | R12 | ✅ covered | An empty plan prints an empty diff and exits 0 |
| ordering | R12 | ✅ covered | The diff is sorted by key |
| idempotency | R12 | ✅ covered | Two dry runs print the same diff |
| concurrency | R12 | 🧪 backstop | A dry run takes no lock and writes nothing |
| adjacency | R13 | ✅ covered | Two applies in the same second get distinct backup names |
| empty | R13 | ✅ covered | An absent config is created with `config-new-project` first |
| encoding | R13 | 🧪 backstop | Values are passed as JSON for objects and lists |
| ordering | R13 | ✅ covered | Unsets run before sets in the same family |
| idempotency | R13 | ✅ covered | Re-applying an applied plan changes nothing but a new backup |
| concurrency | R13 | 🧪 backstop | `apply` refuses when another apply's undo log is open |
| idempotency | R14 | ✅ covered | An approved re-run reports already-current results |
| concurrency | R14 | 🧪 backstop | Follow-ups run sequentially |
| empty | R15 | ✅ covered | No new subcommand changes a v1 subcommand's output |
| encoding | R15 | 🧪 backstop | The README row stays ASCII-table compatible |

## Prohibitions (must-NOT)

**Coverage:** 6/6 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT read a secret value into the inventory, the plan or any output | R11 | resolved | test |
| MUST NOT overwrite a user-edited `cross-ai.mjs` | R4 | resolved | test |
| MUST NOT name, offer or install a missing skill | R9 | resolved | test |
| MUST NOT run a follow-up or an installer without the grouped approval | R14 | resolved | test |
| MUST NOT make the host CLI a review lane or an execution target | R2, R3 | resolved | test |
| MUST NOT write `.planning/config.json` except through gsd-tools | R13 | resolved | test |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes |
|--------------------|-------|------|--------|-------|
| Goal Clarity       | 0.92  | 0.75 | ✓      | Three subcommands plus the script |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | 17, 18.1, 19–22 and tools-installer named |
| Constraint Clarity | 0.82  | 0.65 | ✓      | gsd-tools only, no secrets, approval gate |
| Acceptance Criteria| 0.84  | 0.70 | ✓      | 18 pass/fail criteria |
| **Ambiguity**      | 0.13  | ≤0.20| ✓      | Initial 0.19 after the key-name facts; one auto round |

## Interview Log

`--auto`, one round. The open items went to jev-fast-decision (Laya first, one item per call; `needs_fallback` to TypeSafe direct). Summaries only, advisory. 18-CONTEXT D-01..D-14 are kept as locked. Rule: best design over the smallest diff (`workflow.mvp_mode` unset).

| Round | Perspective | Question summary | Laya (advisory) | TypeSafe (advisory) | Decision locked |
|-------|-------------|------------------|-----------------|---------------------|-----------------|
| 1 | Researcher | Do the ROADMAP key names exist? | – | – | No: the cross-AI keys live under `workflow.`; `review.models.pi` is rejected (live probe). Background, R2/R3/R6 |
| 1 | Failure Analyst | Which installer does the follow-up run? | pinned_local_installer 0.57 (fb) | pinned_local_installer 0.96 | R14: gsd-core's installer pinned to the resolved version, local scope, after approval; never the bare `gsd` (a broken different package here) |
| 1 | Boundary Keeper | How is a System One backend detected on any machine? | env_and_declared 0.48 (fb) | env_and_declared 1.00 | R11: skill installed plus a health probe at `JEV_API_URL` (or the documented default), or a key by name |
| 1 | Simplifier | Does the prototype's exit-code table stand? | – | – | No: XAI-02's 0/1/2/69/75/124/127 contract governs the template (R5) |

---

*Phase: 18-cross-ai-skills-apply-pipeline*
*Spec created: 2026-10-14*
*Next step: /gsd-discuss-phase 18 — implementation decisions (how to build what's specified above)*
