# Phase 31: Removals and small defects - Context

**Gathered:** 2026-11-03 (interactive, standard discuss mode `--analyze --all --batch`, after 31-SPEC.md)
**Status:** Ready for planning

<domain>
## Phase Boundary

Three skills (`ai-kit-spec-execute-gsd`, `ai-kit-opencode-providers`, `mermaid-audit`) leave the tree with every
reference and the code only execute-gsd used; spec-config takes over the stale opencode provider warning; installs
prune dead ai-kit links; nothing recommends, installs or wires rtk; seven small defects are fixed, each with a
regression test; changed skills meet the judge bar.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**15 requirements are locked.** See `31-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `31-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- Deleting the three skills, their tests and every list, doc and comment entry (R1, R3, R4).
- Removing the code only execute-gsd used (R2).
- spec-config's stale opencode provider report, its config fallback and JSONC reader (R5).
- Dead-link pruning in non-interactive installs, claude and pi roots (R6).
- The rtk ban and its test, R05 retired, the doctor row removed (R7).
- The seven defects with their tests (R8-R14).
- The judge bar for changed skills (R15).

**Out of scope (from SPEC.md):**
- The runner template (`cross-ai.mjs`) and its `--prepend-file` / `--no-preamble` flags.
- Migrating projects whose `cross_ai_command` names the guidance file.
- Deleting stored rtk data or the usage-metrics rtk reader.
- The five other archived SPECs whose floors drift (17, 18, 18.1, 21, 24).
- Stale models and providers beyond opencode, `--standalone` in spec-config's listing, opencode profile and runner
  comments against 2.x `--help` — Phase 35.
- Pruning `.agents/skills` or opencode skills dirs.
- The other tooling-todo items; the path-length and no-git tests (Phase 28, GATE-03).

</spec_lock>

<decisions>
## Implementation Decisions

### Judge bar (SPEC R15)

- **D-01: The execute router, spec-config and curated-config are judged in this phase; the rules-agents edit is
  non-material.** `ai-kit-spec-execute` (its `gsd` branch), `ai-kit-spec-config` (the new detection step) and
  `ai-kit-gsd-curated-config` (the guidance writer gone) each go through the judge loop to the bar. The
  rules-agents change is a data entry retired in `rules.py` plus "20-rule" → "19-rule" and one example's signals in
  its SKILL.md; its flow is unchanged, so it is not judged here. `ai-kit-project-rules-agents` carries its failing
  verdict (SJ-3: round 15, 93, one Critical refuted as wording, two Important) until Phase 45 refactors it; the
  verification records that.
  - spec-config's last verdict is UNRESOLVED (ROADMAP §v1.3 follow-ups); meeting the bar here closes it for this skill.
  - Owner choice (recommended option).

### Stale opencode providers (SPEC R5)

- **D-02: A new `check-providers` subcommand of `ai-kit-spec.py`, called from spec-config's detection step** in
  both normal setup and `--check-only`. It prints the per-source scanned / scanned-inactive / absent lines, the
  served-provider source label, and one warning per stale reference; exit 0 whatever it finds (non-blocking).
  `detect-runtimes` stays a cached runtime listing that review also reads.
  - The served providers come from the existing `detect_opencode_models` (plain `opencode models`, through the
    owner's background service in real use; tests use fakes). Adding `--standalone` there is Phase 35's (coupling
    handed to Phase 35's discuss: its criteria 3 and 4 extend this command and may change the listing flags).
  - Owner choice (recommended option).
- **D-03: The JSONC reader is a new read-only module in `ai_kit_spec`** (comments, trailing commas, strings with
  escapes), reading only the `provider` and `providers` keys' child names from the opencode config files that
  opencode itself reads (`${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-~/.config}/opencode}/opencode.json(c)` and the
  project's `opencode.json(c)` / `.opencode/opencode.json(c)`). A drift test runs it and
  `tools/config_doctor_readers.py`'s scanner on shared synthetic fixtures and compares the parsed `provider` keys.
  - Skills cannot import `tools/` (copy-install), so a small copy with a drift test is the house pattern (29 D-13).
  - Own reasoning, follows the owner's round 2 answer.

### Dead links and installer paths (SPEC R6, R8)

- **D-04: `install --headless` and `reconfigure --headless` both call the pruning step** for the claude root and,
  when it exists, the pi root, before linking; the wizard keeps its confirm. `prune_stale` becomes the one entry
  for the headless path (its documented behaviour).
  - Own reasoning (listed to the owner, not objected to).
- **D-05: One resolved-path helper decides "inside the kit"** in `tools/setup.py` (`os.path.realpath` on both
  sides, then a path-component comparison, so `ai-kit` is not inside `ai-kit-old`), used by `installed_links`,
  stale detection and linking; `tools/install.sh` compares with `pwd -P` / `readlink -f` the same way. The home is
  `os.path.expanduser("~")` / `$HOME`. `setup.py`'s kit dir is `AI_KIT_DIR`, else the checkout holding the running
  script (`realpath(__file__)`'s parent of `tools/`); `install.sh` keeps `~/.local/share/ai-kit` only as the
  bootstrap clone target, and that clone's own `setup.py` resolves to the clone.
  - Tests build the alias inside the scratch HOME (a symlinked home folder and a symlinked kit folder); no machine
    path in source or tests. The macOS `/Users` and `/private/var` links are the same model.
  - Own reasoning, follows the owner's round 2 answer.

### rtk (SPEC R7)

- **D-06: The rtk test exempts the whole `skills/ai-kit-usage-metrics/` folder and `tests/test_ai_kit_usage_metrics.py`,
  plus a check that usage-metrics' SKILL.md never tells the agent to install, init or run rtk** (no `install rtk`,
  `rtk init`, or an `rtk <subcommand>` invocation). The other named exemptions are `.planning/`, `docs/prds/`,
  `docs/superpowers/` and the test itself, each listed with its reason in the test.
  - Owner choice (recommended option).
- **D-07: The test scans `git ls-files` from the repository root it resolves itself** (whole-word, case-insensitive,
  UTF-8 with replacement, binary files skipped); outside a git work tree it skips with a named reason. It replaces
  `test_no_hook_file_mentions_the_rewrite_tool`. A `TestArchNonVacuity`-style case proves it fails on a synthetic
  tracked file.
  - Own reasoning.

### Defects (SPEC R9-R14)

- **D-08: The edge-floor guard lives in the e2e tier** (it needs node and the checkout-local gsd-core engine), with a
  named skip when either is missing; it checks every SPEC under `.planning/phases/` in sorted order.
  - Own reasoning (listed, not objected to).
  - *Amended 2026-11-06 (planning): the guard lives in `tools/check_dogfood.py` (`make check-dogfood`), not an e2e
    test, because `check_no_planning_reader` forbids any test reading `.planning/`; its logic is unit-tested on
    fixture SPECs (see 31-SPEC.md R10 amendment). Planning ruling the owner may override.*
- **D-09: goal-prompt gets one small `@file:` helper** used by `_gsd_json` and every other place goal-prompt parses
  gsd-tools output; it mirrors `resolveAtFileOutput` (prefix check, read the path, then parse).
  - Own reasoning.
- **D-10: The AGENTS.md link test reuses the house-rules checker's relative-link extraction** and adds a
  `git check-ignore` step for each resolved target.
  - Own reasoning.
- **D-11: The pi variables live check uses a herdr pane in verification** (SPEC R9 acceptance): pi is started in a
  pane (scratch HOME where pi allows it, no copied credentials), its agent runs `env | grep '^PI_'` through its own
  bash tool, and the answer is read back, names only.
  - Owner direction (round 2).

### Removals (SPEC R1-R4)

- **D-12: Logical commits:** one per removed skill with its tests, lists and docs; one for the guidance-code
  removal; one per rtk area (docs and house rule, doctor, test); one per defect. Each is buildable on its own.
  - Own reasoning (AGENTS.md logical-commit rule).
- **D-13: A removed adapter test whose shared behaviour has no other test moves to a kept caller** (review or
  superpowers); otherwise it is deleted. The plan lists each case of `test_ai_kit_spec_trust`,
  `test_ai_kit_spec_legacy_config`, `test_cross_ai_runner_e2e`, `test_ai_kit_spec_e2e` and `test_arch` with its fate.
  - Own reasoning, follows SPEC R1.

### Claude's Discretion

- Module and test file names for the JSONC reader, `check-providers`, the rtk test, the drift test and the link test.
- The exact reworded text of origin comments that name deleted files (SPEC R3, R4).
- Whether usage-metrics' SKILL.md changes at all (only if its wording recommends rtk; then it is judged, D-01).

### Folded Todos

- **Tooling defects (`2026-11-02-tooling-defects-and-skill-writing-principle-found-at-the-v1.md`):** its seven DEF-01
  items (pi install, pi variables, 25.1 edge floor, goal-prompt `@file:`, routing docstring, runtime-list drift,
  AGENTS.md link) are folded and marked there; its other items stay open.
- **Refactor todo (`2026-10-31-refactor-execute-gsd-and-rules-agents-sj-1-sj-3.md`):** SJ-1 is closed (the skill is
  removed by this phase); SJ-2 and SJ-3 stay open (SJ-3 with Phase 45, D-01).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### This phase
- `.planning/phases/31-removals-and-small-defects/31-SPEC.md` — Locked requirements, Background facts — MUST read before planning
- `.planning/REQUIREMENTS.md` — RMV-01..04 (RMV-04 amended), DEF-01 (amended), JDG-04, DESIGN-01
- `.planning/ROADMAP.md` — Phase 31 goal, criteria, code anchors (amended); Phase 35 criteria 3-4 (coupling, D-02)

### Sources of the defects
- `.planning/todos/pending/2026-11-02-tooling-defects-and-skill-writing-principle-found-at-the-v1.md` — the seven items
- `.planning/milestones/v1.3-MILESTONE-AUDIT.md` line 93 — the hand-copied runtime lists
- `.planning/milestones/v1.3-OWNER-FOLLOWUP.md` line 72 and `.planning/milestones/NEXT-MILESTONE-INPUTS.md` lines 78-84 — the pi claims
- `.planning/milestones/v1.3-phases/22-pi-live-validation/22-INTERACTIVE-PI.md` S2 — the guide's variable check
- `.planning/milestones/v1.3-phases/25.1-configurable-cross-ai-retry-ladder-and-upstream-error-propag/25.1-SPEC.md` — the drifted floor
- `.planning/todos/pending/2026-10-31-refactor-execute-gsd-and-rules-agents-sj-1-sj-3.md` — SJ-1 and SJ-3 verdicts

### External
- pi 1.3.0 `docs/environment-variables.md` (Bash Tool Session Environment) and `dist/core/tools/bash.js` — the variables and their path
- OpenCode v2 migration guide (https://opencode.ai/v2/docs/migrate-v1/) and config/providers docs — `provider` → `providers`, v1 still read

### Prior phases
- `.planning/phases/28-fast-environment-proof-gates/28-CONTEXT.md` — tripwire PATH, fake helper, scratch HOME, D-09 Mermaid skip
- `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-CONTEXT.md` — D-02 (no fallback through execute-gsd), D-13 copy plus drift test pattern
- `.planning/phases/30.1-setup-wizard-component-cards-and-host-status-line-panes-inse/30.1-CONTEXT.md` — component cards that the removals change

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tools/setup.py`: `prune_stale` / `stale_link_candidates` / `apply_stale_prune` (pruning), `installed_links`, `_is_inside`, `resolve_paths`, `_headless_*` steps.
- `tools/config_doctor_readers.py`: the ported JSONC scanner the new reader is compared with.
- `ai_kit_spec/detection.py`: `detect_opencode_models`, `_run_opencode` (private cwd, probe env).
- `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cross_reference.py`: the three-source scan and its scanned / inactive wording to carry over before the folder is deleted.
- `skills/ai-kit-project-rules-agents`: relative-link extraction for D-10.
- `tests/test_tool_substitution_hook.py::test_no_hook_file_mentions_the_rewrite_tool`: the ban the new test replaces.

### Established Patterns
- Copy plus drift test where a skill cannot import shared code (29 D-13).
- Every tier runs one subprocess per module; new `tests/test_*.py` join `unit` automatically, e2e modules go in the runner's e2e set.
- Atomic writes for config; stdlib-only runtime.

### Integration Points
- `ai-kit-spec.py` subcommand table (new `check-providers`); spec-config SKILL.md detection step.
- `Makefile:12`, `.pre-commit-config.yaml:14,59`, `pyproject.toml` `extraPaths`, `tests/test_gate_scope.py`, `tests/test_arch.py` lists.
- README skills table and the hook and config-doctor paragraphs; AGENTS.md Tools and Stack.

</code_context>

<specifics>
## Specific Ideas

- Warning line shape carried from the removed skill: `warning: "<provider>" is referenced in <file>: <reviewer or key> model=<provider>/<model>`, with the `(not active: local review-spec sets strategy = "local-only")` qualifier.
- Scratch scripts behind the SPEC facts: `tmp/p31/pi_alias_machine.sh`, `tmp/p31/pi_env.sh`, `tmp/p31/oc_models.sh`, `tmp/p31/stale_prune.sh`, `tmp/p31/floor_all.sh` (not committed).

</specifics>

<deferred>
## Deferred Ideas

- Repairing the five other archived SPEC floors (17, 18, 18.1, 21, 24) — history, by owner choice (SPEC R10).
- rules-agents' SJ-3 refactor — Phase 45 (D-01).
- `--standalone` and 2.x-accurate opencode listing — Phase 35 (D-02 coupling).

### Reviewed Todos (not folded)
- Eleven other keyword matches (jev skill plans, Cursor subagents, decision-system skills, hooks, cross-AI lanes,
  status-line POC, live-check list) — not removals or these defects.

</deferred>

---

*Phase: 31-removals-and-small-defects*
*Context gathered: 2026-11-03*
