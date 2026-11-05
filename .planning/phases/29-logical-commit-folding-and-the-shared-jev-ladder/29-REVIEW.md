---
phase: 29-logical-commit-folding-and-the-shared-jev-ladder
reviewed: 2026-11-04T00:00:00Z
depth: standard
files_reviewed: 72
files_reviewed_list:
  - Makefile
  - README.md
  - skills/ai-kit-commit-fold/README.md
  - skills/ai-kit-commit-fold/SKILL.md
  - skills/ai-kit-commit-fold/evals/evals.json
  - skills/ai-kit-commit-fold/evals/files/git-log-07-01.txt
  - skills/ai-kit-commit-fold/evals/files/gsd-plan/07-01-PLAN.md
  - skills/ai-kit-commit-fold/evals/files/report-refused.txt
  - skills/ai-kit-commit-fold/evals/files/superpowers-plan.md
  - skills/ai-kit-commit-fold/evals/trigger-queries.json
  - skills/ai-kit-commit-fold/gsd/ai-kit-commit-fold/ai-kit-fold.cjs
  - skills/ai-kit-commit-fold/gsd/ai-kit-commit-fold/capability.json
  - skills/ai-kit-commit-fold/references/folding-policy.md
  - skills/ai-kit-commit-fold/scripts/fold.py
  - skills/ai-kit-commit-fold/scripts/fold_adapters.py
  - skills/ai-kit-commit-fold/scripts/fold_engine.py
  - skills/ai-kit-commit-fold/scripts/fold_group.py
  - skills/ai-kit-gsd-spec-discuss/SKILL.md
  - skills/ai-kit-gsd-spec-discuss/evals/evals.json
  - skills/ai-kit-gsd-spec-discuss/evals/files/locked-context.md
  - skills/ai-kit-gsd-spec-discuss/evals/files/roadmap-analyze.json
  - skills/ai-kit-gsd-spec-discuss/evals/trigger-queries.json
  - skills/ai-kit-gsd-spec-discuss/references/analyzer-brief.md
  - skills/ai-kit-gsd-spec-discuss/references/decision-table.md
  - skills/ai-kit-gsd-spec-discuss/references/log-formats.md
  - skills/ai-kit-gsd-spec-discuss/references/worked-examples.md
  - skills/ai-kit-spec-execute-superpowers/SKILL.md
  - skills/ai-kit-spec-execute-superpowers/evals/evals.json
  - skills/ai-kit-spec-execute-superpowers/evals/files/fold-refused-report.txt
  - skills/ai-kit-spec-execute-superpowers/evals/files/plan-two-features.md
  - skills/ai-kit-spec-execute-superpowers/evals/trigger-queries.json
  - skills/ai-kit-spec-execute-superpowers/references/fold-step.md
  - skills/ai-kit-spec-goal-prompt/SKILL.md
  - skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py
  - skills/ai-kit-spec-goal-prompt/scripts/gp_host.py
  - skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py
  - skills/jev-fast-decision/SKILL.md
  - skills/jev-fast-decision/evals/evals.json
  - skills/jev-fast-decision/evals/files/ci-failure-summary.md
  - skills/jev-fast-decision/evals/files/probe-consent-required.json
  - skills/jev-fast-decision/evals/trigger-queries.json
  - skills/jev-fast-decision/reference.md
  - skills/jev-fast-decision/scripts/jev_ladder.py
  - skills/jev-fast-decision/scripts/jev_review.py
  - tests/fixtures/goal_prompt/golden/opengsd-goal-pointer.md
  - tests/fixtures/goal_prompt/golden/opengsd-recommended.md
  - tests/fold_fixtures.py
  - tests/test_ai_kit_caller_text.py
  - tests/test_ai_kit_commit_fold.py
  - tests/test_ai_kit_commit_fold_adapters.py
  - tests/test_ai_kit_commit_fold_e2e.py
  - tests/test_ai_kit_gsd_spec_discuss.py
  - tests/test_ai_kit_spec_goal_prompt_cli.py
  - tests/test_ai_kit_spec_goal_prompt_golden.py
  - tests/test_ai_kit_spec_goal_prompt_host.py
  - tests/test_ai_kit_spec_goal_prompt_objective.py
  - tests/test_ai_kit_spec_goal_prompt_pointer.py
  - tests/test_ai_kit_spec_goal_prompt_render.py
  - tests/test_ai_kit_spec_goal_prompt_variants.py
  - tests/test_ai_kit_spec_superpowers.py
  - tests/test_arch.py
  - tests/test_decision_probe.py
  - tests/test_external_segments.py
  - tests/test_jev_fast_decision.py
  - tests/test_precompact_core.py
  - tests/test_precompact_shims_e2e.py
  - tests/test_setup.py
  - tests/test_skill_evals_shape.py
  - tools/hooks/claude_decision_probe.py
  - tools/hooks/precompact_core.py
  - tools/run_unittest_parallel.py
  - tools/setup.py
findings:
  critical: 1
  warning: 7
  info: 5
  total: 13
status: issues_found
---

# Phase 29: Code Review Report

**Reviewed:** 2026-11-04
**Depth:** standard
**Files Reviewed:** 72 (plus `tests/test_ai_kit_spec_e2e.py`, outside the phase list, for orchestrator item 1)
**Status:** issues_found

## Summary

I read the fold engine, its adapters, the grouping and CLI modules, the GSD command module, the jev ladder, the jev client diff, the goal-prompt host and section changes, the precompact and decision-probe hooks, and the new cross-skill and lookup-drift rules in `tests/test_arch.py`. Skill texts, references and evals were checked against the code where they make claims about it.

The fold engine is careful. It builds commits in a temp index, checks the tree, makes a backup tag, then moves the ref by compare-and-swap. I found no way for it to lose data: every rewrite ends on a tree proven equal to the tested tip. The defects are elsewhere:
- **Which commits get folded:** commits from another phase can be folded into a plan's commit.
- **Policy claims vs. code:** the merged-branch half of FOLD-8 is not enforced by either adapter, though the policy says the script enforces it.
- **What jev reports:** `consent_used` names TypeSafe whenever a consent record exists, even when TypeSafe was never called.
- **Test isolation:** one test that runs the real GSD tools wrote to the repo's real `.planning/config.json`. A fix for this is in the working tree but not committed. The fold unit tests also pass host config variables through to the code they test.

Severity mapping used below: critical = high, warning = medium or low (stated per finding), info = low/info.

The necessity reference (`gsd-core/references/necessity-review.md`) was not loaded within the time box, so no `necessity:` count is given.

### Orchestrator items, verdicts

1. **Test hermeticity (real write).** Reproduced by reading the code; root cause confirmed. See CR-01. The uncommitted working-tree change to `tests/test_ai_kit_spec_e2e.py` fixes it; CR-01 lists what is still missing.
2. **Executor-reported gaps:**
   - **29-15** (computed cross-skill import): real. Small fix, about 10 lines plus one test case that proves the rule catches a violation. Note: the import is in `skills/ai-kit-gsd-curated-config/.../gsd_catalog.py`, not in `ai-kit-spec-goal-prompt`. See WR-05.
   - **29-08** (`consent_used` with no TypeSafe answer): real, and wider than reported. The client lists every remote backend with a consent record, even when that backend was never called. Small fix, about 3 lines. See WR-02.
   - **29-09** (another phase's commit folded into a plan): real. Small fix, about 3 lines plus one test. See WR-01.

## Critical Issues

### CR-01: A test that runs the real GSD tools walks up from a temp dir in the checkout and writes the real `.planning/config.json` (high; orchestrator item 1)

**File:** `tests/test_ai_kit_spec_e2e.py:102-127` (HEAD version, `TestRealGsdConfigSet.test_write_workflow_keys_round_trip_through_real_gsd_core`). `TestRealGsdTools.setUp`, around line 37 at HEAD, has the same flaw.

**Issue:** At HEAD, the test's scratch project is a bare `tempfile.TemporaryDirectory()` with no `.planning/` inside. The ai-kit wrapper (`gsd_tools.ensure_config_exists`, `config_path`) passes `--cwd <scratch>` to gsd-tools.

gsd-tools sets `cwd = findProjectRoot(cwd)` (`.claude/gsd-core/bin/gsd-tools.cjs:5649`). In `.claude/gsd-core/bin/lib/project-root.cjs:42ff`, `findProjectRoot` returns the start dir only when that dir has its own `.planning/`. Otherwise it walks up to 10 levels and takes the nearest ancestor `.planning/`.

So with `TMPDIR` inside the checkout (e.g. `<repo>/tmp/...`), the scratch dir resolves to the repo root, and this happens:
1. `config-new-project` sees the real config already exists and does nothing. It still returns success, so the test's assert passes.
2. `config-path` returns the real `<repo>/.planning/config.json`.
3. `write-workflow-keys --run-id r1` goes through `gsd_config._backup_once` (`skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_config.py:193-198`). That copies the real config to `config.json.ai-kit-spec-execute-gsd.r1.bak`. Then `config-set workflow.cross_ai_execution=true` writes the real file.

The content stayed the same only because the real value was already `true`. A `--set` of any other key or value would have changed uz's real project config. That breaks the AGENTS.md rule "never use uz's real config files as a test fixture".

**Status of the fix:** The working tree has an uncommitted change to this file that adds:
- `_scratch_project()`: an `os.mkdir(<tmp>/.planning)`, which triggers gsd's guard (0) "own .planning".
- `_assert_inside()`, called right after `config_path`.
- A guard class, `TestRealGsdRunsStayInTheirTempRoot`, which re-runs both classes with `TMPDIR=<repo>/tmp/hermetic-guard-*`.

This is the right fix. What remains:
- The guard only compares the file names in `.planning/` that start with `config.json`. A rewrite with the same name and same content goes unseen. `_assert_inside` catches the case first today, but only in the two classes the guard re-runs.
- Other modules that run the real gsd-tools (`tests/test_curated_config_apply_e2e.py`, `tests/test_curated_config_e2e.py`, `tests/test_ai_kit_commit_fold_e2e.py`) are not re-run under `TMPDIR` inside the checkout.
- The change is not committed, so HEAD still has the bug.

**Fix:**
1. Commit the working-tree change. It resolves the project root inside the test's own temp dir and never walks up.
2. Add a guard at the runner level, so that every e2e module is covered, not just one class. In `tools/run_unittest_parallel.py`, record the checkout's `.planning/` before and after the run (file names plus each `config.json*` file's sha256), and fail the run on any change:

```python
def _planning_snapshot(root):
    planning = os.path.join(root, ".planning")
    if not os.path.isdir(planning):
        return {}
    out = {}
    for name in sorted(os.listdir(planning)):
        path = os.path.join(planning, name)
        if name.startswith("config.json") and os.path.isfile(path):
            with open(path, "rb") as fh:
                out[name] = hashlib.sha256(fh.read()).hexdigest()
    return out
# before the run: snap = _planning_snapshot(REPO_ROOT)
# after the run: if _planning_snapshot(REPO_ROOT) != snap: fail
#   ("a test wrote the checkout's .planning/")
```

3. Add a static rule to `tests/test_arch.py`, with a matching case that proves it catches a violation: any test that builds a real `gsd-tools.cjs` path must create its scratch project with its own `.planning/` (through `_scratch_project`) or pass `--project-dir`.

## Warnings

### WR-01: A commit from another phase inside a plan's run is folded into that plan (medium; orchestrator item 3, 29-09)

**File:** `skills/ai-kit-commit-fold/scripts/fold_adapters.py:203-212, 229-230, 260`

**Issue:** `_plan_unit` returns `None` when a scope parses as `NN-MM` but names another phase. For example, `fix(28-03): ...` inside a phase-29 run gets owner `None`. `gsd_checkpoint` allows `None` owners inside a run (`owner is not None and owner not in mine`), so that commit is folded into the plan. Its message is absorbed into a `feat(29-0x): ...` commit, and the result is marked `Ai-Kit-Fold: 29-0x`. After that the commit can never be attributed to phase 28 again, and `status` reports it as folded under 29.

Merge-backs have the same gap. In `_owner`, `scopes - {None}` drops other-phase scopes, so a worktree merge that carries 28-xx commits plus one 29-xx commit counts as owned by the 29 plan.

The tree proof still holds, so no file content is lost. But history attribution is rewritten, and the spec's own mitigation (T-29-27, "a commit of another plan refuses") is bypassed for exactly the case it exists for. The 29-09 summary already records this as a residual risk that jev chose to accept.

**Fix:** Treat a parsable plan scope from another phase as foreign:

```python
def _plan_unit(scope, padded):
    match = _PLAN_SCOPE.fullmatch(scope)
    if not match:
        return None
    if padded_phase(match.group(1)) != padded:
        return "foreign"      # another phase's plan: refuse plan_not_contiguous, never fold it
    return f"{padded}-{match.group(2)}"
```

`_owner`'s merge branch then sees `"foreign"` in `scopes`, giving more than one entry, which returns `"foreign"`. That is the right result. Add one adapter test: a `fix(28-03)` commit between two `feat(07-01)` commits must give `refused plan_not_contiguous`.

### WR-02: `consent_used` names every consented remote backend, even one that was never called or never answered (medium; orchestrator item 2, 29-08)

**File:** `skills/jev-fast-decision/scripts/jev_review.py:1155-1164, 1821-1823`; passed through unchanged at `skills/jev-fast-decision/scripts/jev_ladder.py:567`

**Issue:** `_consent_used()` loops over `TABLE` and adds every remote row that has a `record_consent`, with no check of `run.trail`. So a run that Laya fully answered on the local rung still reports `consent_used: [{"backend": "typesafe", ...}]`. So does a run where TypeSafe errored.

`SKILL.md:46` tells the caller to announce consent only "for backends that answered an item". That leaves the filtering to the model while the data says otherwise. It breaks the rule against presenting a result with more certainty than its sourcing supports: callers such as the goal-prompt report, spec-discuss logs and fold notes can announce a remote send that never happened.

**Fix:** Keep the client's entry only for a backend that actually answered. The smallest fix is in the ladder, after `fill_columns`:

```python
answered_by = {name for row in results.values() if isinstance(row, dict)
               for name, col in row.items() if isinstance(col, dict) and "choice" in col}
consent_used = [entry for entry in public_consent_used(got.get("consent_used"))
                if entry["backend"] in answered_by]
```

If "data was sent" also needs announcing, fix it at the source as well: have the client's `_consent_used(run)` keep rows whose name appears as a `backend` in `run.trail`. Pin it with one test: a local-only answer plus a consent record must give `consent_used == []`.

### WR-03: The merged-branch half of FOLD-8 is never enforced by the `gsd` or `superpowers` forms, but the policy says the script enforces it (medium)

**File:** `skills/ai-kit-commit-fold/scripts/fold_adapters.py:266, 308`; `skills/ai-kit-commit-fold/references/folding-policy.md` (Enforcement line); `skills/ai-kit-commit-fold/SKILL.md:37`

**Issue:** Both adapters build `merged_refs=()`, and `fold_engine._check_not_reachable` returns early when `refs` is empty. So the `range_on_merged_branch` refusal can only fire for a checkpoint written by hand.

The policy's last line says "FOLD-4, FOLD-5, FOLD-7 and FOLD-8 are enforced by this skill's script", and `SKILL.md` lists `range_on_merged_branch` as an outcome the user might see. With stacked PRs, where the base branch moves only when the stack merges, a phase branch whose PR merged into its parent branch is reachable from neither `main` nor `origin/main`. Running `fold.py gsd` on it again would rewrite merged commits.

**Fix:** Either correct the policy line ("FOLD-8's merged-branch half is enforced only when the caller supplies merged refs; the `gsd` and `superpowers` forms check the base branch only") and pin it in `tests/test_arch.py`, or add a `--merged-ref REF` option (repeatable) to both subcommands, pass it through to `merged_refs`, and have the unit flow supply the parent branch.

### WR-04: The fold unit tests pass the host config variables through, so a real jev install and the real consent record can be reached (medium)

**File:** `tests/fold_fixtures.py:16-31`

**Issue:** `git_env()` copies `os.environ` and overrides only `HOME`, the git identity and `JEV_LAYA_URL`. `CLAUDE_CONFIG_DIR`, `XDG_CONFIG_HOME`, `CURSOR_CONFIG_DIR`, `PI_CODING_AGENT_DIR` and `AI_KIT_JEV_CLIENT` pass through. The e2e helper (`tests/test_ai_kit_commit_fold_e2e.py:19-28`) does remove them, which shows the risk is known.

Every `fold.py` run in the unit tests goes through `fold_group.find_jev`. With an isolated fold copy the skill's own root holds no jev, so the lookup falls to `SKILLS_ROOTS`. If, say, `XDG_CONFIG_HOME` is set in the gate shell, it finds `$XDG_CONFIG_HOME/opencode/skills/jev-fast-decision`. The client then reads the consent record at `$XDG_CONFIG_HOME/ai-kit/jev-consent.json`, so a consented TypeSafe row gets fixture commit subjects, and the expected `grouping: rules` becomes non-deterministic.

The variables are not set in this session, so this is a latent risk, not a failure seen here.

**Fix:** In `git_env`, drop the same variables the e2e helper drops, plus `AI_KIT_JEV_CLIENT`:

```python
for name in ("CLAUDE_CONFIG_DIR", "XDG_CONFIG_HOME", "CURSOR_CONFIG_DIR",
             "PI_CODING_AGENT_DIR", "AI_KIT_JEV_CLIENT"):
    env.pop(name, None)
```

### WR-05: The cross-skill reach rule cannot see `importlib.import_module(f"ai_kit_spec.{name}")` (low; orchestrator item 2, 29-15)

**File:** `tests/test_arch.py:1368-1409` (`check_cross_skill_refs`); the reach itself is at `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/gsd_catalog.py:27-41`

**Issue:** The rule matches only `Import`/`ImportFrom` nodes, string literals with `<other>/`, `sys.path` calls with literal args, and path-join literals. `gsd_catalog.load_ai_kit_spec_module` adds a path from a variable to `sys.path` and calls `importlib.import_module(f"ai_kit_spec.{name}")`. Neither of those is a literal, so the reach into `ai-kit-spec-review` is invisible to the rule and cannot go on the allowlist. Ruling 2 says the rule covers every cross-skill path. The orchestrator's prompt placed this in `ai-kit-spec-goal-prompt`; it is actually in curated-config. A grep shows the goal-prompt scripts make no computed import.

**Fix (small):** In `check_cross_skill_refs`, read the leading literal of an `import_module` / `__import__` argument:

```python
if isinstance(node, ast.Call) and _dotted_name(node.func) in {
        "importlib.import_module", "import_module", "__import__"} and node.args:
    arg = node.args[0]
    head = arg.value if _is_text(arg) else (
        arg.values[0].value if isinstance(arg, ast.JoinedStr) and arg.values
        and _is_text(arg.values[0]) else None)
    owner = modules.get(head.split(".")[0]) if head else None
    if owner is not None and owner != own:
        hits.append((relpath, owner, node.lineno))
```

Then add the `(gsd_catalog.py, ai-kit-spec-review)` key with its one-line reason to `CROSS_SKILL_ALLOWLIST`, plus a case in `TestArchNonVacuity` that proves the rule catches a violation. `skills/_shared/ai_kit_rules_common/gsd_identity.py:43` has the same kind of import, but `_shared` is out of this rule's scope by design.

### WR-06: The GSD command accepts phase ids that `fold.py` rejects (low)

**File:** `skills/ai-kit-commit-fold/gsd/ai-kit-commit-fold/ai-kit-fold.cjs:30` vs `skills/ai-kit-commit-fold/scripts/fold.py:22`

**Issue:** The `.cjs` check is `^\d+(\.\d+)*$`, so `1.2.3` passes. `fold.py` uses `\d+(?:\.\d+)?`, so the run ends in an argparse exit 2. The GSD wave hook then logs "usage" output under `onError: skip` instead of a clean refusal.

**Fix:** Use `/^\d+(\.\d+)?$/` in the `.cjs` file.

### WR-07: jev's per-commit timeout (40 s) is shorter than the ladder's own deadline, so a slow local rung always falls back to rules without saying it timed out (low)

**File:** `skills/ai-kit-commit-fold/scripts/fold_group.py:38, 236-240`; compare `skills/jev-fast-decision/scripts/jev_ladder.py:423, 448-451`

**Issue:** A one-item ladder run gives its client `CALL_TIMEOUT_SECONDS * (1 + 3)` = 120 s, plus 10 s on the subprocess. Fold kills the run at 40 s and records it as `"no answer"`. With Laya plus its retries plus a consented remote, any answer after 40 s is lost. The note says `jev: no answer for c<i>`, which hides that it was a timeout. Calls are also serial, one per commit, inside `execute:wave:post`. So a plan with N commits that each answer just under 40 s blocks the wave for N × 40 s.

**Fix:** Send all commits as one `ladder` call (the ladder already takes many items and scales its deadline). Or at least set `JEV_TIMEOUT_SECONDS` to the ladder's per-item bound plus a margin, and report `jev: timeout for c<i>` on `subprocess.TimeoutExpired`.

## Info

### IN-01: A root commit in the range crashes with `IndexError` instead of refusing

**File:** `skills/ai-kit-commit-fold/scripts/fold_engine.py:201-202`

**Issue:** `_commit` uses `parents[0]`. If a merge in `base..end` brings in unrelated history, `rev-list --no-merges` includes that history's root commit. The uncaught `IndexError` becomes a traceback, not a `FoldError`. No write has happened yet, so this is not data loss.

**Fix:** `if not parents: raise FoldError("foreign_merge", f"{sha[:12]} is a root commit")`.

### IN-02: Any message line that starts with `Ai-Kit-Fold: ` marks a commit as already folded

**File:** `skills/ai-kit-commit-fold/scripts/fold_adapters.py:219-221`

**Issue:** `_owner` scans every line of the message body. A hand-written commit that quotes the trailer at the start of a line (for example, docs about the trailer) is treated as `folded:<x>` and skipped.

**Fix:** Read only the trailer block, the last paragraph (for example with `git interpret-trailers --parse`).

### IN-03: A group whose paths all cancel out yields an empty folded commit

**File:** `skills/ai-kit-commit-fold/scripts/fold_group.py:111-122` (`_groups`), `skills/ai-kit-commit-fold/scripts/fold_engine.py:278-284`

**Issue:** `paths` is filtered to the net `changed` set. A candidate whose commits add a file and later delete it gets an empty `paths` set, and `_build` writes a commit with no change. That breaks the spirit of FOLD-1 ("one commit per logical feature").

**Fix:** Merge a feature with no paths into its neighbour in `_features`, or skip `commit-tree` when the tree equals the parent's tree.

### IN-04: One `plan_not_contiguous` error hides every status line

**File:** `skills/ai-kit-commit-fold/scripts/fold_adapters.py:276`, `skills/ai-kit-commit-fold/scripts/fold.py:137-141`

**Issue:** `_status_line` calls `gsd_checkpoint`, which can raise. `_status` catches the error once and prints only `status: ...`, so the read-only report loses every other plan's line.

**Fix:** Catch `FoldError` per plan in `_status_line` and print `<unit>: not contiguous`.

### IN-05: The precompact lookup handles a missing HOME differently from the other copies of the lookup table

**File:** `tools/hooks/precompact_core.py:86-96` vs `skills/jev-fast-decision/scripts/jev_ladder.py:97-105`, `fold_group.py:184-192`, `gp_host.py:474-481`

**Issue:** With no `HOME`, `precompact_core.skills_roots` skips the fallback rows, while the other copies expand `~`. The drift test (`lookup_drift_problems`) compares only the `SKILLS_ROOTS` tuples, so this difference in behaviour cannot be caught.

**Fix:** Pick one rule and state it in `reference.md`'s lookup section, or note the hook's stricter rule there.

---

_Reviewed: 2026-11-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
