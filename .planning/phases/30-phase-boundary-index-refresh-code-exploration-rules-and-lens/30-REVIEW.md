---
phase: 30-phase-boundary-index-refresh-code-exploration-rules-and-lens
reviewed: 2026-11-06T08:58:24Z
depth: standard
files_reviewed: 48
files_reviewed_list:
  - .graphifyignore
  - .pre-commit-config.yaml
  - Makefile
  - skills/_shared/ai_kit_rules_common/code_exploration.py
  - skills/ai-kit-commit-fold/gsd/ai-kit-commit-fold/ai-kit-fold.cjs
  - skills/ai-kit-commit-fold/gsd/ai-kit-commit-fold/capability.json
  - skills/ai-kit-commit-fold/scripts/flow_boundary.py
  - skills/ai-kit-commit-fold/scripts/flow_brief.py
  - skills/ai-kit-commit-fold/scripts/flow_index.py
  - skills/ai-kit-commit-fold/scripts/flow_unit.py
  - skills/ai-kit-commit-fold/scripts/fold.py
  - skills/ai-kit-commit-fold/scripts/fold_adapters.py
  - skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py
  - tools/check_dogfood.py
  - tools/config_doctor_appliers.py
  - tools/config_doctor_checks.py
  - tools/global_rules.py
  - tools/hooks/advisor_core.py
  - tools/marked_block.py
  - tools/run_unittest_parallel.py
  - tools/setup.py
  - tools/setup_dev.py
  - tools/wizard_app.py
  - tests/fold_fixtures.py
  - tests/index_fakes.py
  - tests/test_ai_kit_commit_fold_e2e.py
  - tests/test_ai_kit_rules_common.py
  - tests/test_ai_kit_spec_superpowers.py
  - tests/test_arch.py
  - tests/test_check_dogfood.py
  - tests/test_config_doctor.py
  - tests/test_flow_boundary.py
  - tests/test_flow_brief.py
  - tests/test_flow_checkpoint.py
  - tests/test_flow_contract.py
  - tests/test_flow_docs.py
  - tests/test_flow_index.py
  - tests/test_flow_index_e2e.py
  - tests/test_flow_stack.py
  - tests/test_global_rules.py
  - tests/test_hook_registry.py
  - tests/test_hook_registry_e2e.py
  - tests/test_marked_block.py
  - tests/test_rules_docs.py
  - tests/test_setup.py
  - tests/test_setup_dev.py
  - tests/test_tool_advisor_core.py
  - tests/test_wizard_app_3.py
findings:
  critical: 0
  warning: 8
  info: 6
  total: 14
  necessity: 1
status: issues_found
---

# Phase 30: Code Review Report

**Reviewed:** 2026-11-06T08:58:24Z
**Depth:** standard
**Files Reviewed:** 48
**Status:** issues_found

## Summary

Scope: the `a63f1f6..HEAD` diff of the 48 listed files, plus the code around each change.
This includes commit 76fa531, where `start --plan` carries the plan's `**Spec:**` file. The
main new code is the index step (`flow_index.py`), the boundary step and unit brief
(`flow_boundary.py`, `flow_brief.py`), the GSD adapter additions (`fold_adapters.py`), the
global-rules rewrite (`global_rules.py`, `marked_block.py`, setup/wizard/doctor wiring), the
codegraph advice in `advisor_core.py`, `setup_dev.py`, and the lens-wiring check in
`check_dogfood.py`.

There are no critical findings. The runtime code is stdlib-only, config and brief writes are
atomic, every tool call passes argv lists (no shell strings), and no source file hardcodes an
absolute path. Facts checked on this machine: codegraph is 1.6.2 (matching the sentence source
`global_rules.py` cites); graphify's PyPI name is `graphifyy`; `graph.json` carries
`built_at_commit`; `git worktree add` does not export `GIT_DIR` to post-checkout hooks, but a
plain `git checkout` does; the post-checkout hook entry comes from the same checkout's
config, so a worktree of an older branch (main) runs no index hook.

Main problems:
- The refresh writes the `.graphifyignore` line after the graphify build that needs it, so the
  first build still indexes `.planning/milestones/`, which holds 16 code files in this repo.
- The unit brief is never written when the previous unit's commits are gone.
- The new codegraph advice misreads Markdown-only searches written as `--include=*.md` or
  `--glob=*.md`, and every pi grep.
- Two lean or dead-code items: a copied config reader and an unused `drift()`.
- One timing-sensitive e2e assertion.

Lenses: `ponytail:ponytail-review` loaded, `.planning/lens-brief` was applied, and the
`jev-fast-decision` skill text was read. No jev call was needed, because every finding below
rests on code evidence.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: `.graphifyignore` line is written after the graphify build it should shape

**File:** `skills/ai-kit-commit-fold/scripts/flow_index.py:196-202`
**Issue:** `refresh()` runs `graphify_step()` first (it runs `graphify update .` and copies to
`.planning/graphs/`) and calls `fold_adapters.index_ensure_graphifyignore()` only afterwards.
In a GSD project with no `.planning/milestones/` line yet, the first refresh builds and
publishes a graph that includes `.planning/milestones/`. That folder is not just Markdown:
`git ls-files ".planning/milestones/*.py" ...` lists 16 code files here (spike and verdict
scripts). The ignore rule only takes effect at the next boundary point, so GSD's agents read
a polluted `.planning/graphs/graph.json` in between. No test checks the order;
`tests/test_flow_index.py:246-258` only checks that the line is added.
**Fix:** Make sure the ignore line exists before the build:
```python
def refresh(top, run=_run_tool, which=shutil.which, clock=time.monotonic, sleep=time.sleep):
    notes = []
    if fold_adapters.index_project(top) and which("graphify") is not None:
        note = fold_adapters.index_ensure_graphifyignore(top)
        if note:
            notes.append(note)
    codegraph_line = codegraph_step(top, run, which)
    graphify_line = graphify_step(top, run, which, clock, sleep)
    ...
```
Add one test with a fake `run` that records whether `.graphifyignore` held the line when the
`update` argv ran.

### WR-02: Boundary refuses, and writes no brief, when the previous unit's range objects are gone

**File:** `skills/ai-kit-commit-fold/scripts/flow_boundary.py:51-57,63`; `skills/ai-kit-commit-fold/scripts/flow_brief.py:82-85`
**Issue:** `unit_range()` returns `(parent_tip, branch tip or pushed)` without checking that
either object still exists. Concrete case: the previous unit was squash-merged, its branch was
deleted, and later gc pruned the pushed tip (or the old `parent_tip`). `changed_files()` then
raises `FlowError("git_error")` inside the index lock, and `boundary()` aborts after the
refresh. `cmd_boundary` exits 1 with `refused git_error`, and `start` reports
`boundary: skipped`. Every later unit hits the same error, because `previous_unit()` keeps
choosing that entry. `render()` already has a `range unknown` branch (`flow_brief.py:214-216`)
for exactly this case, but nothing can reach it once a span is returned.
**Fix:** Degrade to "range unknown" instead of refusing:
```python
def unit_range(repo, entry):
    base = entry.get("parent_tip")
    tip = flow_git.rev(repo, f"refs/heads/{entry['branch']}") or entry.get("pushed")
    if not base or not tip or not flow_git.rev(repo, f"{base}^{{commit}}") \
            or not flow_git.rev(repo, f"{tip}^{{commit}}"):
        return None
    return (base, tip)
```

### WR-03: Codegraph advice treats Markdown-only searches as code searches (`--opt=value` forms and every pi grep)

**File:** `tools/hooks/advisor_core.py:310-332,361-366,581-586`
**Issue:** `_positive_filters()` and `_search_scope()` only recognize a filter option given as
its own token followed by a separate value. The joined forms most people type are missed. On
pi, `event_from_pi()` never fills `search_path`, `glob` or `type`, so `_is_code_search()` sees
a grep with no paths and no filters, and `_markdown_only([], [])` returns False. A probe run
against the current code (`tmp/phase30-close/review/advisor_probe.py`) printed:
- `grep -rn foo --include=*.md .` -> code search
- `rg -n foo --glob=*.md` -> code search
- pi `grep` with `glob: "*.md"` -> code search

Each of these gets "explore code with codegraph_explore ... keep rg for Markdown", which is
the opposite of the rule the line states. pi is a primary host (project memory). The pi gap
rests on pi's grep input fields (`path`, `glob`); that schema was not checked here.
**Fix:** Split `--flag=value` tokens before scanning:
`args = [p for a in args for p in (a.split("=", 1) if a.startswith("--") and "=" in a else [a])]`.
In `event_from_pi`, add `"search_path": tool_input.get("path"), "glob": tool_input.get("glob")`
for grep/find tools. Add one test per form.

### WR-04: `_gsd_config` is a verbatim copy of the existing `_config` in the same module

**File:** `skills/ai-kit-commit-fold/scripts/fold_adapters.py:490-496` (copy of `:344-350`)
**Issue:** Phase 30 added `_gsd_config(top)`, which reads `.planning/config.json` and returns
a dict or `{}`, line for line the same as the existing `_config(repo)` a few lines above it
(which `gsd_unit` uses). Two readers of one file must change together. Under AGENTS.md's
Design rule (via the lens brief), new code where an existing helper fits is a warning.
**Fix:** Delete `_gsd_config` and call `_config(top)` in `_graphify_config`.

### WR-05: `global_rules.drift()` has no caller

**File:** `tools/global_rules.py:237-239`
**Issue:** `drift(env)` is defined, but nothing in `tools/`, `skills/` or `tests/` calls it
(grep for `global_rules.drift` and `drift(` finds only the definition). The doctor row uses
`summary()`, and setup uses `plan_changes()`/`apply()`. Vulture's `min_confidence=80` does not
catch unused functions, so the gate stays quiet.
**Fix:** Delete `drift()`.

### WR-06: Wall-clock `< 1.0 s` assertions around two concurrent `git worktree add` + pre-commit runs

**File:** `tests/test_flow_index_e2e.py:138,154`
**Issue:** `test_two_concurrent_adds_return_fast_...` asserts that two parallel
`git worktree add` calls finish in under 1.0 s together. Each one starts a Python interpreter
plus pre-commit's `hook-impl`, then `fold.py` imports, a `git worktree list`, and a brief
write. `make e2e-test` runs modules in parallel at up to 40% of the CPUs, next to other heavy
e2e modules (real gsd-core, real git). On a loaded or slower machine, two pre-commit startups
can pass 1 s with the runner still fully detached, so the test fails without any regression.
This is a flaky-test pattern (the tests are in scope only for reliability).
**Fix:** Test what is being claimed, that git does not wait for the indexing. With the fake
`delay_s` set high (for example 5 s), assert that git returned before the log's `end` line, and
keep a loose wall-clock bound (for example `< delay_s`) instead of a fixed 1.0 s.

### WR-07: A non-`FlowError`/`OSError` from the boundary turns a successful `start` into a traceback

**File:** `skills/ai-kit-commit-fold/scripts/flow_unit.py:373-386`; triggers in `skills/ai-kit-commit-fold/scripts/fold_adapters.py:592` and `skills/ai-kit-commit-fold/scripts/flow_index.py:179`
**Issue:** `_start_and_boundary()` runs the boundary after `_start()` has already switched or
created the branch and written the record. It only catches `FlowError` and `OSError`. Concrete
case: a `.graphifyignore` or `.git/info/exclude` holding non-UTF-8 bytes. Then
`_read_bytes(path).decode("utf-8")` or `exclude.read_text(encoding="utf-8")` raises
`UnicodeDecodeError` (a `ValueError`). `start` then exits with a Python traceback instead of
its rendered report, although its state change went through. The same error kills the
detached drain runner (`run_job` -> `refresh`) part way through the queue.
**Fix:** Decode those two files with `errors="surrogateescape"` (as `flow_brief._decode`
already does), and widen the guard in `_start_and_boundary` to
`except (OSError, ValueError) as exc:`.

WR-08 (necessity) is listed under Necessity below.

## Info

### IN-01: Comment on R08's clause indexes is false

**File:** `skills/_shared/ai_kit_rules_common/code_exploration.py:45-49`
**Issue:** The comment says "clauses 2 and 6 name no graph.json or graphify-out". But
`RULE_CLAUSES[6]` ("One `graphify update .` build feeds both locations:
`graphify-out/graph.json` ...") names both. Either the indexes moved after the comment was
written, or the comment means another clause. A later editor will trust it and reorder wrongly.
**Fix:** Restate the real reason clause 7 is included, or drop the parenthetical.

### IN-02: `--next` brief says the base is `main` whatever the repo's base branch is

**File:** `skills/ai-kit-commit-fold/scripts/flow_boundary.py:71`
**Issue:** For `unit is None`, `base_branch="main"` is hardcoded. With no previous stacked unit,
the brief tells the plan writer "this is the first unit on `main`", even when
`git.base_branch` is `develop` or the repo uses `master`. That is a stated fact with no source
behind it (AGENTS.md: no certainty beyond sourcing).
**Fix:** Resolve the base the way the flow already does for units (the record's settings or
`fold_adapters.base_branch(top)` through the adapter layer), or word it as "the base branch".

### IN-03: Two hosts that resolve to one real file give a misleading "changed since it was read" line

**File:** `tools/global_rules.py:66-89,228-229`
**Issue:** `plan_changes()` plans one `replace` per host path without deduplicating by
`realpath`. Concrete case: `~/.claude/CLAUDE.md` is a symlink to `~/.config/opencode/AGENTS.md`
(the owner's AGENTS.md-first convention). The first write succeeds. The second then writes a
second backup and reports "changed since it was read; not written, retried on the next
install". Nothing is retried, and the file is already correct.
**Fix:** In `plan_changes`, keep the first host per `os.path.realpath(path)` and mark later
ones `status="same_file"` with a skip text naming the first host.

### IN-04: New git callers do not scrub `GIT_DIR`/`GIT_WORK_TREE`/`GIT_INDEX_FILE` like their siblings

**File:** `skills/ai-kit-commit-fold/scripts/flow_index.py:52-54,182,364-367`; `skills/ai-kit-commit-fold/scripts/flow_brief.py:82,137,255`
**Issue:** `flow_git`, `flow_record`, `fold_engine` and `fold_adapters` each drop these
variables before running git. The new `_git_out`, `_top_of`, `ensure_excluded`,
`changed_files`, `mentions` and `_worktrees` do not. A probe confirmed that `git worktree add`
does not export `GIT_DIR` to post-checkout (so today's queue path is safe), but a plain
`git checkout` hook does. Any future caller from a hook context, or the inherited env of the
detached runner, would point every queued checkout's git calls at one gitdir. This is
inferred risk, not a reproduced failure.
**Fix:** Route these through `flow_git.run_git`/`flow_git.rev`, which scrub already, and delete
the private `_git_out`/`_top_of` copies. `flow_boundary` imports the private `_top_of`.

### IN-05: Detached runner writes `.graphifyignore` into fresh worktrees; its "commit it" note goes only to the job log

**File:** `skills/ai-kit-commit-fold/scripts/flow_index.py:199-202,303-311`; `skills/ai-kit-commit-fold/scripts/fold_adapters.py:589-597`
**Issue:** In a GSD project without the line, each `git worktree add` leaves an untracked or
modified `.graphifyignore` in the new worktree. The `note: ... (commit it)` line lands only in
`ai-kit-index.log`, so an executor running `git add -A` there sweeps it into an unrelated plan
commit.
**Fix:** Pass a flag from `run_job` so the runner skips the write (the foreground boundary
still adds it and prints the note), or accept it and say so in `references/unit-contract.md`.

### IN-06: Codegraph lock detection by substring `"lock"`, and the `**Spec:**` regex spanning lines

**File:** `skills/ai-kit-commit-fold/scripts/flow_index.py:77`; `skills/ai-kit-commit-fold/scripts/fold_adapters.py:394`
**Issue:**
- `"lock" in err.lower()` also matches "blocked", "clock" and "unlock". The resulting "lock is
  held" line is wrong, but harmless.
- In `_SPEC_LINE`, the `\s*` after `**Spec:**` matches newlines under `re.MULTILINE`. An empty
  `**Spec:**` line captures the first word of the next non-blank line. The `isfile` check
  usually discards it.
- `value.split()[0]` cuts a bare spec path that contains a space.

**Fix:** Use `[ \t]*` in place of `\s*` in `_SPEC_LINE`. For codegraph, match a narrower phrase
(for example `"lock" in err.lower() and "held" in err.lower()`, or codegraph's exact message
once sourced).

## Necessity

### WR-08: `flow_index.SEED_HOOKS` is a plugin registry with one plugin

**Category:** necessity
**File:** `skills/ai-kit-commit-fold/scripts/flow_index.py:31-32,345-351,376-378`; `skills/ai-kit-commit-fold/scripts/flow_brief.py:293-296`
**Issue:** This is generality without instantiation. Grep over `skills/`, `tools/` and `tests/`
finds exactly one production entry: `flow_brief.seed_worktree`. It is registered as an import
side effect, plus deduplication logic for re-imports. `cmd_index` already imports
`flow_brief` by name just to trigger that registration (`importlib.import_module("flow_brief")`
at line 377). The registry exists only to avoid naming the function that `cmd_index` already
names. Tests use it as a seam, which a plain parameter would serve as well.
**Fix:** Pass the seeder in directly. In `cmd_index`'s detach branch:
`return detach(args.repo, seed=importlib.import_module("flow_brief").seed_worktree)`. Have
`_queue_checkout` call `seed(top)` under its existing `try/except` log. Then delete
`SEED_HOOKS` and the registration block in `flow_brief.py`.

Count note: `warning: 8` includes WR-08; `necessity: 1` is the subset of warning + info that is necessity and is not added to `total`.

---

_Reviewed: 2026-11-06T08:58:24Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
