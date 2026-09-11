---
phase: 07-curated-gsd-config-skill
plan: 02
subsystem: cli-tooling
tags: [python, argparse, gsd-config, cross-ai, preference-matching, subprocess]

# Dependency graph
requires:
  - phase: 07-curated-gsd-config-skill (plan 01)
    provides: skills/ai-kit-gsd-config/ai_kit_gsd_config/{gsd_catalog,gsd_write,critical_agents,cli}.py -- the config-write plumbing and CLI entrypoint this plan extends
provides:
  - model_detect.py -- {cli: [model_id, ...]} candidate pool built by shelling out to ai_kit_spec's own detect-runtimes subcommand (D-02)
  - preference_match.py -- the two literal D-03 preference ladders (execution/plan-review), each with an ordered rule tuple and a nested opencode-then-cursor-agent search
  - cross_ai_build.py -- renders workflow.cross_ai_command as a bare-command-name string by reusing ai_kit_spec.commands.build_execute_command (D-04/D-05)
  - cli.py detect-execution-candidate/detect-review-candidate/apply-execution/apply-review subcommands
  - gsd_write.config_get -- JSON-decoded config-get wrapper (non-raw, see Deviations)
affects: [07-curated-gsd-config-skill plan 03, 07-curated-gsd-config-skill plan 04]

# Actuals (#2632)
actuals:
  tokens: 10328
  tasks: 2
  commits: 2
plan_head_before: 835e1f5bc9d0ee26a7b2a5aa8ea15717042352c7

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sibling-skill sys.path injection via model_detect.resolve_ai_kit_spec_path, duplicated identically in preference_match.py and cross_ai_build.py (each module self-contained at import time, order-independent)"
    - "Nested rule-then-runtime search order (all of one rule's candidates checked across opencode-then-cursor-agent before the next rule is tried) for both preference ladders"

key-files:
  created:
    - skills/ai-kit-gsd-config/ai_kit_gsd_config/model_detect.py
    - skills/ai-kit-gsd-config/ai_kit_gsd_config/preference_match.py
    - skills/ai-kit-gsd-config/ai_kit_gsd_config/cross_ai_build.py
  modified:
    - skills/ai-kit-gsd-config/ai_kit_gsd_config/cli.py
    - skills/ai-kit-gsd-config/ai_kit_gsd_config/gsd_write.py
    - tests/test_ai_kit_gsd_config.py

key-decisions:
  - "gsd_write.config_get omits the plan text's literal --raw flag and instead parses config-get's plain JSON output -- --raw serializes an array via JS's String(array), a bare comma-joined string, not valid JSON (live-verified regression the plan text didn't anticipate)."
  - "config_get takes node_bin/gsd_tools_path as explicit leading params (mirroring config_set's own shape) rather than re-resolving them internally, per the plan's own 'no duplicated path-resolution logic' instruction."

patterns-established:
  - "Detection stays subprocess-only (D-02); decision logic (preference_match) and command-string reuse (cross_ai_build) each independently inject ai_kit_spec's own directory onto sys.path via model_detect.resolve_ai_kit_spec_path before importing one proven helper each -- never the whole sibling skill."

requirements-completed: [REQ-cfg-curated-questions, REQ-cfg-writes-config]

coverage:
  - id: D1
    description: "model_detect.py builds a candidate pool from ai_kit_spec's own detect-runtimes output; preference_match.py resolves the two literal execution/plan-review preference ladders in declared priority order, with best_review_candidate always resolving (native claude/opus last resort)."
    requirement: "REQ-cfg-curated-questions"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_gsd_config.py#TestBuildCandidatePool"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_gsd_config.py#TestVersionAtLeast"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_gsd_config.py#TestBestExecutionCandidate"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_gsd_config.py#TestBestReviewCandidate"
        status: pass
      - kind: integration
        ref: "manual: python3 ai-kit-gsd-config.py detect-execution-candidate / detect-review-candidate against real installed opencode CLI"
        status: pass
    human_judgment: false
  - id: D2
    description: "cli.py apply-execution writes workflow.cross_ai_execution unconditionally and workflow.cross_ai_command only when a real candidate+builder exist, as a bare command-name string (never a resolved absolute path). apply-review writes workflow.plan_review_convergence + review.effort.opencode unconditionally and a dedupe-merged review.default_reviewers + review.models.<slug>."
    requirement: "REQ-cfg-writes-config"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_gsd_config.py#TestApplyExecutionCli"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_gsd_config.py#TestApplyReviewCli"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_gsd_config.py#TestBuildExecutionCommand"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_gsd_config.py#TestCliToReviewerSlug"
        status: pass
      - kind: integration
        ref: "manual: apply-execution/apply-review against a real gsd-tools-managed scratch project (fresh, and with a pre-seeded review.default_reviewers list)"
        status: pass
    human_judgment: false

duration: ~45min
completed: 2026-09-11
status: complete
---

# Phase 7 Plan 2: Live Model Detection + Cross-AI Preference Ladders Summary

**Live opencode/cursor-agent CLI/model detection reused from `ai_kit_spec`, two literal preference ladders (execution + plan-review) resolved against it, and the winning candidates wired into `workflow.cross_ai_command` (bare command name) and `review.default_reviewers`/`review.models.<slug>`/`review.effort.<slug>` (structured keys).**

## Performance

- **Duration:** ~45 min
- **Tasks:** 2
- **Files modified:** 6 (3 created, 3 modified)

## Accomplishments

- `model_detect.py`: `resolve_ai_kit_spec_path` mirrors `ai-kit-spec-execute-gsd/SKILL.md`'s Step 0 multi-candidate resolution; `detect_runtimes_snapshot` shells out to `ai_kit_spec`'s own `detect-runtimes` subcommand (never re-implements detection); `build_candidate_pool` reshapes the snapshot into a plain `{cli: [model_id, ...]}` pool, omitting CLIs that were never enumerable (claude/codex/grok never carry a `"models"` list).
- `preference_match.py`: the two literal D-03 ladders (`EXECUTION_RULES`/`REVIEW_RULES`), each an ordered tuple of `(label, predicate)` pairs, walking `opencode` then `cursor-agent` per rule before advancing. `best_review_candidate` never returns "no match" — an empty pool resolves to `("claude", "opus", "native-last-resort")`. Reuses `ai_kit_spec.model_heuristics._hint_matches` for delimiter-bounded substring matching (`"review"` never fires on `"preview"`).
- `cross_ai_build.py`: `build_execution_command` reuses `ai_kit_spec.commands.build_execute_command` (already-live-verified) to render `workflow.cross_ai_command` — confirmed via a zero-hit grep hygiene check that no local path-resolution call (`shutil.which`/`os.path.expanduser`) exists in this file, satisfying D-05's bare-command-name guarantee structurally, not just by convention. `CLI_TO_REVIEWER_SLUG` maps `cursor-agent` to the shorter `cursor` slug (confirmed against `capability-registry.cjs`'s real reviewer-slug vocabulary).
- `cli.py`: four new subcommands — `detect-execution-candidate`, `detect-review-candidate` (Task 1), `apply-execution`, `apply-review` (Task 2) — alongside Plan 01's `ensure-project`/`apply-profile`/`apply-critical-agents`.
- Live end-to-end verification against this machine's real installed opencode CLI and a real gsd-tools-managed scratch project: `detect-execution-candidate` resolved `router-env/my-coding` (rule `coding-or-executor`); `detect-review-candidate` resolved `router-env/my-plan-review` (rule `plan-review`); `apply-execution`/`apply-review` correctly wrote a working `opencode run -m ... --dir ... --auto` command and correctly deduped into a pre-seeded `review.default_reviewers` list sourced from this machine's real `~/.gsd/defaults.json` global layer (the exact realistic path called out in the plan's Task 2 `read_first`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Detection pool + the two literal preference ladders** - `c017eae` (feat)
2. **Task 2: Wire the winning candidates into config** - `5c8952b` (feat)

_Both commits are on branch `worktree-agent-a4dcffe8dcc6abe6b`, built on top of `main`'s `835e1f5` (Plan 07-01's completion commit), which this worktree fast-forward-merged in before starting (see Issues Encountered)._

## Files Created/Modified

- `skills/ai-kit-gsd-config/ai_kit_gsd_config/model_detect.py` - detection layer: sibling-skill path resolution, subprocess-based `detect-runtimes` invocation, pure pool-building
- `skills/ai-kit-gsd-config/ai_kit_gsd_config/preference_match.py` - pure decision logic: the two literal preference ladders, `_version_at_least`, `_hint_matches` reuse
- `skills/ai-kit-gsd-config/ai_kit_gsd_config/cross_ai_build.py` - `build_execution_command` (reuses `ai_kit_spec.commands.build_execute_command`), `CLI_TO_REVIEWER_SLUG`
- `skills/ai-kit-gsd-config/ai_kit_gsd_config/cli.py` - `detect-execution-candidate`, `detect-review-candidate`, `apply-execution`, `apply-review` subcommands
- `skills/ai-kit-gsd-config/ai_kit_gsd_config/gsd_write.py` - `config_get` (JSON-decoded, non-`--raw` — see Deviations)
- `tests/test_ai_kit_gsd_config.py` - 71 total tests (62 after Task 1, 71 after Task 2); all pass

## Decisions Made

- Kept detection strictly subprocess-based (D-02) while decision logic (`preference_match`) and command reuse (`cross_ai_build`) each independently inject `ai_kit_spec`'s directory onto `sys.path` via the SAME `model_detect.resolve_ai_kit_spec_path` function — duplicated at each import site rather than factored into a shared helper, since the plan named only `resolve_ai_kit_spec_path` as the function to implement and each module must be import-order-independent (a module imported before its sibling must still self-resolve).
- Applied the same `opencode`-then-`cursor-agent` runtime search order to both ladders, per the plan's own instruction ("07-CONTEXT.md's Specifics section states this order for plan-review explicitly and gives no contrary order for execution... one consistent, documented search policy rather than inventing a second one").

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `gsd_write.config_get` omits the plan text's literal `--raw` flag**
- **Found during:** Task 2, while implementing `config_get`'s subprocess invocation
- **Issue:** The plan's `<action>` text instructs invoking `config-get <key_path> --project-dir <target_dir> --raw`. Live-verified against the installed `gsd-tools.cjs` (`bin/lib/io.cjs`'s `output()`): for a non-secret key, `--raw` mode emits `String(rawValue)`. For a JS array, `String(["opencode","cursor"])` produces the bare, comma-joined string `"opencode,cursor"` — no brackets, not valid JSON, and indistinguishable from a genuine single-element string value. This directly contradicts the SAME plan's `<behavior>` contract two lines above it: "`config_get`... returns the JSON-decoded current value at `key_path` (e.g. `["opencode"]`)". Following the literal `--raw` instruction would make `json.loads` raise (or silently mis-parse) on every real multi-element `review.default_reviewers` list — breaking the exact merge feature (`apply-review`'s dedupe) this function exists to support.
- **Fix:** `config_get` invokes `config-get <key_path> --project-dir <target_dir>` WITHOUT `--raw`. Confirmed live: non-raw mode always emits real `JSON.stringify`'d output (`["opencode","cursor"]` for a list, `"adaptive"` for a scalar), which `json.loads` decodes correctly and unambiguously for both cases.
- **Files modified:** `skills/ai-kit-gsd-config/ai_kit_gsd_config/gsd_write.py`
- **Verification:** Live end-to-end test against a real gsd-tools install: `apply-review` correctly merged into a pre-existing `["claude"]` list to produce `["claude", "opencode"]`, and correctly deduped against a pre-existing `["opencode"]` list without adding a duplicate. `TestApplyReviewCli`'s three cases (different-slug merge, absent-key fresh list, already-contains-slug dedupe) all pass.
- **Committed in:** `5c8952b` (Task 2 commit)

**2. [Rule 3 - Blocking] `gsd_write.config_get`'s signature takes `node_bin`/`gsd_tools_path` explicitly rather than the literal 3-param form quoted in the plan's `<behavior>` bullet**
- **Found during:** Task 2, while implementing `config_get`
- **Issue:** The plan's `<behavior>` bullet literally quotes `gsd_write.config_get(project_dir, key_path, run_fn=subprocess.run)` — a 3-parameter signature with no `node_bin`/`gsd_tools_path`. Implementing exactly that would require `config_get` to internally re-derive `node_bin`/`gsd_tools_path` (via `gsd_catalog.resolve_node_binary`/`resolve_gsd_tools_path`), which directly contradicts the SAME sentence's own instruction: "same `resolve_gsd_tools_path`/`resolve_node_binary` plumbing from `gsd_catalog.py`, no duplicated path-resolution logic" — and would also make `config_get` untestable via the established `make_fake_run`/fake-install-root pattern every other `gsd_write` function in this test file already uses (which all take `node_bin`/`gsd_tools_path` as explicit, caller-resolved params).
- **Fix:** Implemented `config_get(node_bin, gsd_tools_path, project_dir, key_path, run_fn=subprocess.run)` — mirroring `config_set`'s own parameter shape exactly, called from `_cmd_apply_review` with the SAME `node_bin`/`gsd_tools_path` already resolved once via `_resolve_node_and_gsd_tools`.
- **Files modified:** `skills/ai-kit-gsd-config/ai_kit_gsd_config/gsd_write.py`, `skills/ai-kit-gsd-config/ai_kit_gsd_config/cli.py`
- **Verification:** `TestApplyReviewCli`'s three cases all pass via the standard fake-install-root/`make_fake_run` DI pattern, consistent with every other CLI-level test in this file.
- **Committed in:** `5c8952b` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking — both isolated to `gsd_write.config_get`'s exact call shape)
**Impact on plan:** Both deviations are narrow, load-bearing corrections to a single new function's exact invocation contract. All of `07-02-PLAN.md`'s locked `must_haves` (bounded-substring priority order, unconditional boolean presets, bare-command-name `cross_ai_command`, structured `review.*` keys, native last-resort, D-09 merge-mode) are satisfied exactly as specified. No scope creep.

## Issues Encountered

- **Stale worktree, resolved before any implementation work.** This worktree's branch (`worktree-agent-a4dcffe8dcc6abe6b`) was forked from an ancestor commit (`091bf76`) that predated Phase 7 entirely — `.planning/phases/07-curated-gsd-config-skill/` and `skills/ai-kit-gsd-config/` (Plan 07-01's own deliverable, which this plan directly depends on) did not exist in the working tree at task start. Confirmed via `git merge-base --is-ancestor HEAD main` that the worktree's HEAD was a clean ancestor of `main` (no divergent/unique commits on the worktree branch), then fast-forward-merged (`git merge main --ff-only`, not a rebase or reset) to bring the worktree up to `main`'s `835e1f5` before starting any plan work. This was a genuine environment-setup gap, not a deviation from the plan's own content.
- **`ruff` findings on first pass** (import sorting, one line-length violation, one `SIM117` nested-`with` suggestion, one unused-loop-variable in a test) — all cosmetic, fixed inline before committing, confirmed via `uv run ruff check` returning "All checks passed!" on every touched file.
- **`pyright` (run standalone, outside its currently-configured `include` list) flags `ai_kit_spec.commands`/`ai_kit_spec.model_heuristics` as unresolved imports** in `cross_ai_build.py`/`preference_match.py`. This is expected and not a regression: `pyproject.toml`'s `[tool.pyright] include` list does not yet cover ANY `skills/ai-kit-gsd-config` or `skills/ai-kit-spec-execute-gsd` file (confirmed: `ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_cross_ai.py`, which has the IDENTICAL `from ai_kit_spec.commands import build_execute_command` pattern, is also outside the current include list). `pyproject.toml`'s pyright/vulture path registration for this skill is explicitly scoped to Plan 07-04, per 07-01-SUMMARY.md's own precedent ("Not yet wired into `make test`/`make lint`/`.pre-commit-config.yaml`/`pyproject.toml` — this is intentional and explicitly scoped to Plan 07-04").
- **`make test`/`make lint` do not yet include `tests.test_ai_kit_gsd_config` or `skills/ai-kit-gsd-config/**`** — same intentional Plan 07-04 deferral as above (confirmed by reading 07-04-PLAN.md's own `files_modified`/`<action>` before starting, per 07-01-SUMMARY.md's precedent). `python3 -m unittest tests.test_ai_kit_gsd_config -v` (71 tests, OK) and `uv run ruff check` (all clean) were run directly per this plan's own `<verify>` blocks; the full `make test`/`make lint` suite was also run standalone twice (before and after both commits) to confirm zero regressions to the existing baseline (1595-test/16-install-test, unchanged).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `detect-execution-candidate`/`detect-review-candidate`/`apply-execution`/`apply-review` are all real, tested, live-verified subcommands ready for Plan 07-03/07-04 to wire into the curated question flow and `SKILL.md`.
- `~/.gsd/defaults.json`'s real global-config-precedence effect on `apply-review`'s merge path (confirmed live on this machine) is now covered by `TestApplyReviewCli`'s already-contains-slug case — no longer an unaccounted-for path for downstream plans.
- No blockers. `pyproject.toml`/`Makefile`/`.pre-commit-config.yaml` registration for this whole skill remains Plan 07-04's explicit scope, as already noted in 07-01-SUMMARY.md.

---
*Phase: 07-curated-gsd-config-skill*
*Completed: 2026-09-11*

## Self-Check: PASSED
