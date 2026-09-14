---
phase: 13-docker-rules-checker-ai-kit-project-rules-docker
plan: 03
subsystem: testing
tags: [python, stdlib, tool-catalog, hot-reload, docker, compose, advisory-findings]

requires:
  - phase: 13-docker-rules-checker-ai-kit-project-rules-docker
    plan: 02
    provides: "compose_parse.py's D-D7 accessor contract (iter_services/block_scalar/block_subblock/block_sequence), discover_local_dev_compose_files, and docker_checker.check_docker_rules's gate-then-extend aggregator shape"
provides:
  - "tool_catalog.py: HOT_RELOAD_TOOLS/HOT_RELOAD_BASELINE_GAPS/SCRIPT_INDIRECTION_PREFIXES/resolve_hot_reload -- per-stack hot-reload marker knowledge, kept out of the six-category taxonomy and TOOL_CATEGORY_INDEX"
  - "hot_reload.py: check_hot_reload -- ROADMAP SC4, the three-outcome (conforming / convention-missing / not-confirmable-with-a-reason) hot-reload convention check over local-dev compose files only"
affects: [13-04-docker-skill-md-and-registration, 15-rules-orchestrator]

actuals:
  tokens: 16534
  tasks: 3
  commits: 3
  plan_head_before: d7c271ebc5ea1465c4af0fad5fe978bc77a60487

tech-stack:
  added: []
  patterns:
    - "Three-outcome advisory design (D-D15): conforming / convention-missing (non-advisory) / not-confirmable (advisory with a named reason) -- the same shape ast_only.py's _not_verifiable_finding established for the arch sibling, reused here so a hardcoded, staleable baseline never becomes a confident false accusation"
    - "Three-valued bind-mount answer (present/absent/unreadable, D-D17) computed BEFORE any branching, with unreadable outranking the missing-override half -- the mixed-state precedence rule"
    - "Runtime-joined recommendation text (D-D16's fourth prohibition): no marker or script-prefix literal anywhere in hot_reload.py's source, including docstrings -- every such string is built by joining from the shared catalog at call time"

key-files:
  created:
    - skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/hot_reload.py
  modified:
    - skills/_shared/ai_kit_rules_common/tool_catalog.py
    - skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/docker_checker.py
    - tests/test_ai_kit_project_rules_docker.py
    - tests/test_ai_kit_rules_common.py

key-decisions:
  - "D-D16's catalog extension landed exactly as specified: HOT_RELOAD_TOOLS/HOT_RELOAD_BASELINE_GAPS/SCRIPT_INDIRECTION_PREFIXES and resolve_hot_reload sit in their own section of tool_catalog.py, after the six-category taxonomy, explicitly excluded from _derive_tool_category_index/TOOL_CATEGORY_INDEX."
  - "D-D17's five-rule volume-entry grammar landed IN ORDER, with rule 1 (no colon -> anonymous, readable, never a bind mount) evaluated before rule 4's leading-character test -- pinned by its own negative fixture (a bare '/app/data' entry) rather than left implicit."
  - "D-D17's mixed-state precedence landed: an unreadable bind answer ALWAYS produces the advisory volumes_unreadable outcome, even when the override is also missing, and never contributes to a confident convention-missing finding."
  - "D-D15's fixed five-reason evaluation order (volumes_unreadable -> script_indirection -> no_stack_detected -> stack_without_baseline -> command_not_matched) is implemented as an explicit branch order in hot_reload.py, not as 'whichever check runs first' -- proven end-to-end by the stackless-repo fixture where a script-indirection service keeps its reason rather than moving to no_stack_detected."
  - "D-D16's marker-selection total order (longest, then earliest position in its own stack's tuple, then alphabetically first stack) is implemented as an explicit sort key over (-len(marker), stack_index, marker_index), never a first-match loop."

patterns-established:
  - "A hardcoded baseline table that is expected to go stale gets its own advisory outcome rather than a confident claim built on it -- the same discipline the arch sibling's Rust/Go architecture-fitness gaps already established, now generalized to a second domain."

requirements-completed: [REQ-rules-docker]

coverage:
  - id: SC4
    description: "A local-dev service definition using the production image/entrypoint baked at build time -- no bind mount, or no dev command override -- is flagged as missing the hot-reload convention, and a paired fixture using the bind-mount-plus-override convention is not; stack-aware (D-04), not a generic bind-mount heuristic"
    requirement: "REQ-rules-docker"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_docker.py#TestHotReloadProductionEntrypointAdvisory.test_bind_mount_plus_production_command_is_advisory_command_not_matched"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_docker.py#TestHotReloadConformingBindPlusRecognizedCommand.test_bind_mount_and_recognized_command_yields_no_finding"
        status: pass
      - kind: command
        ref: "HOT-RELOAD-OK, UNREADABLE-VOLUME-PRECEDENCE-OK, NO-LOCAL-DEV-FILE-OK, STACK-DETECT-ONCE-OK, NO-LOCAL-COPIES-OK, HOT-RELOAD-COVERAGE-OK, MARKER-SELECTION-OK"
        status: pass
    human_judgment: false

duration: ~2h
completed: 2026-09-14
status: complete
---

# Phase 13 Plan 03: Hot-Reload Convention Check Summary

**Stack-aware hot-reload convention check (ROADMAP SC4, 13-CONTEXT D-04's expansion) with a three-outcome advisory design -- conforming, convention-missing, or not-confirmable-with-one-of-five-named-reasons -- built on a new per-stack marker mapping added beside (never into) the shared catalog's six-category taxonomy.**

## Performance

- **Duration:** ~2h
- **Tasks:** 3
- **Commits:** 3 (measured: `git rev-list --count d7c271e..HEAD`)
- **Files modified:** 5 (1 created, 4 modified) across the three tasks

## Accomplishments

- `tool_catalog.py`: `HOT_RELOAD_TOOLS` (37 markers across 5 stacks), `HOT_RELOAD_BASELINE_GAPS` (empty today, a named constant anyway), `SCRIPT_INDIRECTION_PREFIXES` (5 prefixes), and `resolve_hot_reload` -- a stack-scoped, token-boundary-aware, total-order marker resolver, added beside the six-category taxonomy without joining it.
- `hot_reload.py`: `check_hot_reload` -- D-D13 through D-D18's local-dev-only, three-outcome, five-advisory-reason hot-reload convention check, reading exclusively through `compose_parse`'s accessors and the shared catalog's resolver.
- `docker_checker.py`: one appended call inside the applicable branch, passing the LOCAL-DEV compose file list only.
- Test suite grown from 106 to 151 docker-skill tests (+45) and the shared suite from 113 to 128 (+15), plus four independently-applied-and-reverted non-vacuity mutations proving the resolver call, the local-dev-only scope, the bind-mount discrimination, and the three-valued unreadable-precedence rule are all load-bearing.

## Task Commits

1. **Task 1: Extend the shared tool catalog with per-stack hot-reload knowledge and its resolver** - `cd4c1e2` (feat)
2. **Task 2: Add the three-outcome hot-reload check over local-dev compose files and wire it into the aggregator** - `d8b9db9` (feat)
3. **Task 3: Fill out the hot-reload coverage, prove non-vacuity, confirm no gate file was touched** - `61bf1e4` (test)

## Files Created/Modified

- `skills/_shared/ai_kit_rules_common/tool_catalog.py` - the hot-reload marker mapping and resolver, added as a new section
- `skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/hot_reload.py` - the check itself (new file)
- `skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/docker_checker.py` - one appended call
- `tests/test_ai_kit_project_rules_docker.py` - 45 new tests across Tasks 2-3 (106 -> 151)
- `tests/test_ai_kit_rules_common.py` - 15 new tests across Tasks 1 and 3 (113 -> 128)

## Decisions Made

### Environment recovery before Task 1

This worktree's base (`b30c0b2`) predated plans 13-01/13-02's merge to `main` (`d7c271e`) -- the docker skill directory did not exist yet. Confirmed `git merge-base --is-ancestor HEAD main` succeeded, then fast-forwarded (`git merge --ff-only main`, `b30c0b2` -> `d7c271e`). Recorded as `plan_head_before` in this SUMMARY's frontmatter (also `actuals.plan_head_before`).

### The hot-reload marker table AS COMMITTED, per stack, verbatim

```
python: --reload, --reload-dir, flask run, runserver, watchmedo, watchfiles, hupper, adev runserver
node:   vite, webpack-dev-server, webpack serve, nodemon, next dev, nuxt dev, ng serve,
        react-scripts start, tsx watch, ts-node-dev, --watch, remix dev, astro dev
go:     air, compiledaemon, realize, gow, reflex, fresh
rust:   cargo watch, cargo-watch, bacon, dioxus serve, trunk serve
java:   spring-boot:run, bootrun, quarkus:dev, quarkus dev, --continuous
```

`flask run` is listed WITHOUT requiring a debug flag (Flask's reloader is commonly enabled via `FLASK_DEBUG` in the environment -- permissive on purpose, cost is only a missed advisory). `--reload`/`--watch` are bare flags on purpose (the shared reload idiom across `uvicorn`/`gunicorn`/`node` and others). `nodemon`'s position immediately before `--watch` in the `node` tuple is load-bearing for the marker-selection tie-break (both seven characters).

### The three outcomes and five advisory reasons, as implemented, with the exact fixture producing each

| Outcome / Reason | Issue | Advisory | Fixture (test method) |
|---|---|---|---|
| 1. Conforming | (no finding) | -- | `TestHotReloadConformingBindPlusRecognizedCommand.test_bind_mount_and_recognized_command_yields_no_finding`; also `TestHotReloadOutcomeOneEveryStackWithBaseline` (all 5 stacks, driven from `HOT_RELOAD_TOOLS`'s own keys) |
| 2. Convention missing | `docker_hot_reload_convention_missing` | No | `TestHotReloadMissingBothHalves`, `TestHotReloadMissingBindHalfOnly`, `TestHotReloadMissingOverrideHalfOnly`, `TestHotReloadNamedVolumeIsMissingNotUnreadable`, `TestHotReloadAnonymousVolumeIsMissingNotBind` |
| 3. `volumes_unreadable` | `docker_hot_reload_tool_unrecognized` | Yes | `TestHotReloadInterpolatedVolumeIsAdvisory`, `TestHotReloadLongFormVolumeIsAdvisory`, `TestHotReloadMixedStateUnreadableAndMissingOverride`, `TestHotReloadUnreadableVolumePrecedenceFiveCombos` (all 5 combinations) |
| 3. `script_indirection` | `docker_hot_reload_tool_unrecognized` | Yes | `TestHotReloadScriptIndirectionAdvisory.test_script_runner_override_is_advisory_script_indirection` |
| 3. `no_stack_detected` | `docker_hot_reload_tool_unrecognized` | Yes | `TestHotReloadStacklessRepoReasonPrecedence.test_no_detected_stack_moves_non_script_services_to_no_stack_detected` |
| 3. `stack_without_baseline` | `docker_hot_reload_tool_unrecognized` | Yes | `TestHotReloadOutcomeThreeReasonsPaired.test_stack_without_baseline_reason_skipped_when_gaps_tuple_empty` -- **SKIPPED** (see below) |
| 3. `command_not_matched` | `docker_hot_reload_tool_unrecognized` | Yes | `TestHotReloadProductionEntrypointAdvisory.test_bind_mount_plus_production_command_is_advisory_command_not_matched` |

`HOT_RELOAD_BASELINE_GAPS` is empty today -- no stack has a deliberately-empty marker tuple, so `stack_without_baseline` is unreachable via a real detected stack. Its dedicated test method is `self.skipTest(...)`-ed with a stated reason (not silently passing), so the branch is documented as untested-today rather than invisible. If a future stack is added to `HOT_RELOAD_TOOLS` with an empty tuple (recorded in `HOT_RELOAD_BASELINE_GAPS`), this method activates immediately.

### The four non-vacuity mutations (Task 3), each OBSERVED failing before revert

1. **Drop the resolver call** (`hot_reload.py`, `_evaluate_service`: `marker = resolve_hot_reload(override_text, stacks)` -> `marker = override_text`, i.e. any override satisfies clause iii): **9 tests failed** (7 failures + 2 errors), including the direct evidence that D-04's expansion is real: `TestHotReloadProductionEntrypointAdvisory.test_bind_mount_plus_production_command_is_advisory_command_not_matched` and `TestHotReloadScriptIndirectionAdvisory.test_script_runner_override_is_advisory_script_indirection` both failed, along with every other test asserting an unrecognized-command advisory (the reason-paired class, the stackless-precedence class, the recommendation-text-built-at-runtime test). Nothing outside the unrecognized-marker domain broke. Reverted; suite green again (151/151, 1 skipped).
2. **Widen the file scope** (`docker_checker.py`: pass `compose_files` -- the full base+local-dev discovery list -- instead of `local_dev_compose_files`): **47 failures + 1 error**, a MUCH broader break than the plan's own minimum bar ("makes exactly the base-file-scope methods fail"), because nearly every fixture in this entire plan's suite declares a base `docker-compose.yml` service with no bind mount/override, and widening the scope now evaluates those services too -- breaking assertions across the whole hot-reload domain and even unrelated tracer/target-family fixtures whose base services now acquire spurious hot-reload findings. This is stronger evidence than the plan anticipated: the local-dev-only scope is load-bearing pervasively, not just in one dedicated test class. Reverted; suite green again.
3. **Treat every `volumes:` entry as a bind mount** (`hot_reload.py`, `_bind_mount_answer`: `kind = _classify_volume_entry(entry)` -> `kind = "bind"` unconditionally): **10 failures**, exactly the named-volume, anonymous-volume, and long-form/interpolated methods (`TestHotReloadAnonymousVolumeIsMissingNotBind`, `TestHotReloadInterpolatedVolumeIsAdvisory`, `TestHotReloadLongFormVolumeIsAdvisory`, `TestHotReloadNamedVolumeIsMissingNotUnreadable`, the mixed-state/precedence classes), and nothing else silently passed. Reverted; suite green again.
4. **Collapse the three-valued bind answer to two values** (`hot_reload.py`, `_evaluate_service`: force `bind_answer = _BIND_ABSENT` whenever it was `_BIND_UNREADABLE`, right after computing it): **8 failures**, exactly the mixed-state and interpolated/long-form-volume methods (`TestHotReloadMixedStateUnreadableAndMissingOverride`, `TestHotReloadInterpolatedVolumeIsAdvisory`, `TestHotReloadLongFormVolumeIsAdvisory`, `TestHotReloadUnreadableVolumePrecedenceFiveCombos`'s interpolated/long-form cases, `TestHotReloadReasonDeterminism.test_mixed_state_reason_is_stable_across_runs`) -- this is direct evidence that an unreadable volume cannot reach a confident finding: under the collapsed (two-valued) implementation, the mixed-state fixture (an interpolated volume source, no override at all) would instead produce a non-advisory `docker_hot_reload_convention_missing` finding claiming "no bind mount" from a value the parser never read -- exactly the false-confidence failure D-D15/D-D17 exist to prevent. Reverted; suite green again.

All four mutations were applied directly to the committed production source, observed failing via `python3 -m unittest tests.test_ai_kit_project_rules_docker`, then reverted via `Edit` back to the exact committed text (confirmed byte-identical by `git status --porcelain` showing no diff and the full 536-test cross-suite run passing after revert).

### Marker-selection order as implemented

Sort key: `(-len(marker), stack_index, marker_index)` with `stack_index` taken from `sorted(stacks)` and `marker_index` from the marker's position in its own stack's `HOT_RELOAD_TOOLS` tuple. Collects ALL matching markers first, then picks the minimum under this key -- never a first-match loop. `MARKER-SELECTION-OK` output (re-run at completion):

```
MARKER-SELECTION-OK webpack-dev-server nodemon ['nodemon']
```

`webpack-dev-server` (19 chars) beats `--watch` (7 chars) on clause 1 (true longest-wins). `nodemon` beats `--watch` on clause 2 (both 7 characters, `nodemon` sits earlier in the shipped `node` tuple -- confirmed from the live tuple, not assumed). The six-subprocess `PYTHONHASHSEED` sweep (clause 3's cross-process determinism) returned exactly `{'nodemon'}` across all six seeds. No catalog edit made the seeded `nodemon`/`--watch` tie stop being a tie -- no fixture substitution was needed.

### No marker literal in `hot_reload.py`; every list is joined at runtime

`NO-LOCAL-COPIES-OK` (re-run at completion): `NO-LOCAL-COPIES-OK 50 0` -- 50 candidate pool entries (37 markers + 5 script prefixes + 4 local-dev filenames + 4 base filenames), 0 leftover copies. Every recommendation string that lists markers or script prefixes (`_markers_text`, `_script_prefixes_text` in `hot_reload.py`) joins from `HOT_RELOAD_TOOLS`/`SCRIPT_INDIRECTION_PREFIXES` at call time; `TestHotReloadRecommendationMarkerBuiltAtRuntime` asserts the expected marker is read FROM the live tuple in the test, never typed into it.

### 13-CONTEXT's stale "Integration Points" line

`.planning/phases/13-docker-rules-checker-ai-kit-project-rules-docker/13-CONTEXT.md` line 156 still reads: **"D-05 adds a new category to the shared per-language tool catalog Phase 11's D-01 creates"**. This plan deliberately did the OPPOSITE -- D-D16 keeps `HOT_RELOAD_TOOLS` OUT of the six-category taxonomy and its derived index, per D-D16's own text and the "Claude's Discretion" bullet that actually hands this plan the choice ("new top-level category VS a dedicated dict keyed by stack" -- D-D16 chose the dict). This SUMMARY records the stale line so plan 13-04 Task 3's stale-line sweep (finding 7 from cycle-2 review) has a pointer to the correction it must write. No `.planning/` file was edited by this plan.

### The THREE limits this check carries, in `SKILL.md`-ready wording

1. **Stack attribution is repo-wide, not per-service.** The override command is resolved against the union of every stack `detect_stacks(repo_root)` returns, because a compose service definition carries no per-service language signal. In a polyglot repo, a Node dev server can satisfy a Python service's command line.
2. **A repo with no local-dev compose file produces no hot-reload finding at all.** This is a stated limit, not a silent gap: the hot-reload convention is evaluated ONLY over `docker-compose.override.yml`/`docker-compose.local.yml` (and their `.yaml` spellings) -- confirmed by `NO-LOCAL-DEV-FILE-OK`.
3. **Long-form (mapping-style) volume entries are not read.** A service that declares its bind mount as `- type: bind` / `source:` / `target:` (rather than short-form `./src:/app/src`) is reported as **advisory, not-confirmable** (`volumes_unreadable`), never flagged as missing the convention and never confirmed conforming. This is a descope decided in cycle-2 review finding 1, not an unfinished edge -- long-form detection appears in no source artifact, and widening the shared parser for it would contradict 13-CONTEXT D-01's narrow-reader premise. The user will see an advisory finding naming which of the two unreadable forms applied (an interpolated source, or a mapping-style entry), never a false "no bind mount" claim.

### The anonymous-volume exclusion (D-D17 rule 1)

Landed as the FIRST of the five ordered classification rules in `_classify_volume_entry`: an entry with no colon anywhere (`- /app/data`) is classified `"anonymous"` -- readable, contributes to the `absent` bind answer -- BEFORE any leading-character test runs. Pinned by its own negative fixture: `TestHotReloadAnonymousVolumeIsMissingNotBind.test_bare_path_anonymous_volume_is_convention_missing` (the bare-path entry, non-advisory convention-missing) paired with `test_same_leading_characters_with_separator_is_a_bind_mount` (`- /app/data:/app/data`, same leading characters WITH a separator, IS a bind mount, no finding). `TestHotReloadVolumeEntryGrammarFullFamily` additionally pins the classifier directly for all five rules.

### The catalog extension as it landed

Three new module-level names (`HOT_RELOAD_TOOLS`, `HOT_RELOAD_BASELINE_GAPS`, `SCRIPT_INDIRECTION_PREFIXES`) plus `resolve_hot_reload`, added in a clearly-headed new section after the existing taxonomy content, with a docstring paragraph explaining why the section exists and why it is NOT part of the six-category taxonomy. Asserted undisturbed: `CATALOG-HOT-RELOAD-OK` confirms the key set matches `detect_stacks`'s derivable stacks, the resolver behaves stack-scoped/token-boundary-aware/production-command-negative, no marker leaked into `TOOL_CATEGORY_INDEX` or is answerable by `resolve_tool_category`, and `BASELINE_STACKS`/`resolve_tool_category` sampled facts are unchanged. `HOT_RELOAD_BASELINE_GAPS` is empty today; the corresponding `stack_without_baseline` test method is `skipTest`-ed with a stated reason (see above), never silently passing on the empty tuple.

### Divergence from D-D13 through D-D18

None. Every rule -- D-D13 (local-dev scope), D-D14 (the three-clause convention), D-D15 (three outcomes, five reasons, fixed evaluation order), D-D16 (the catalog extension, the total-order marker selection, the fourth no-literal prohibition), D-D17 (the five-rule volume grammar, the three-valued bind answer, the mixed-state precedence, the long-form descope), D-D18 (the finding vocabulary, no `target` key) -- was implemented exactly as specified.

### The resolved commit range and file list for the no-gate-file assertion

`FIRST=cd4c1e2` (this plan's own first commit). `git diff --name-only cd4c1e2^..HEAD`:

```
skills/_shared/ai_kit_rules_common/tool_catalog.py
skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/docker_checker.py
skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/hot_reload.py
tests/test_ai_kit_project_rules_docker.py
tests/test_ai_kit_rules_common.py
```

`NO-GATE-FILES-OK` -- none of these match a gate-configuration path (`Makefile`, `.pre-commit-config.yaml`, `pyproject.toml`, `README.md`, or any `SKILL.md`).

## Deviations from Plan

None - plan executed exactly as written. The one procedural addition (fast-forwarding the stale worktree base before Task 1) was an explicit instruction from the dispatch prompt, not a plan deviation, and is recorded above under "Environment recovery."

## Issues Encountered

`make validate` fails (exit 2), but ONLY on the same four pre-existing, out-of-scope findings STATE.md already names as deferred (going back to Phase 07/09): `tools/status-line.py`, `tools/wizard_app.py`, `tests/test_ai_kit_spec.py`, `tests/test_ai_kit_spec_superpowers.py`. None of these files were touched by this plan (confirmed by extracting every file path ruff cited: exactly those 4). `make test` and `make lint` both exit 0; a scoped `uv run ruff check` against this plan's own 5 touched files is clean.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `check_hot_reload` is wired into `docker_checker.check_docker_rules` and ready for plan 13-04's `SKILL.md` to document, including the THREE stated limits above and the five advisory reasons.
- The `docker-hot-reload` category and its two issue names (`docker_hot_reload_convention_missing`, `docker_hot_reload_tool_unrecognized`) are ready for plan 15's cross-domain orchestrator.
- 13-CONTEXT's stale "Integration Points" line (quoted above) is ready for plan 13-04 Task 3's stale-line sweep to correct, append-only.
- The skill remains uninstallable (no `SKILL.md`) until plan 13-04.
- No blockers.

---
*Phase: 13-docker-rules-checker-ai-kit-project-rules-docker*
*Completed: 2026-09-14*

## Self-Check: PASSED

All created/modified files confirmed present on disk (5 files: 1 created, 4 modified, plus this SUMMARY.md). All three commit hashes (`cd4c1e2`, `d8b9db9`, `61bf1e4`) confirmed present in `git log`.
