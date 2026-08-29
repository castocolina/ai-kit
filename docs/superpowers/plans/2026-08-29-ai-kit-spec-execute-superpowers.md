# ai-kit-spec-execute-superpowers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the superpowers adapter for `ai-kit-spec-execute`: a skill that resolves the best available model/CLI for a superpowers-generated plan's task, then delegates the actual execution harness to `superpowers:executing-plans`/`superpowers:subagent-driven-development` (preserving their TDD enforcement, fresh-subagent-per-task, and review-between-tasks patterns), injecting the pre-resolved model/CLI as an explicit input at each dispatch point rather than bypassing the harness.

**Architecture:** Unlike the GSD adapter (Plan 2), superpowers has no config surface to read or write — it is Claude-native only, with model selection happening at the point each subagent is dispatched via the `Agent` tool. This adapter's job is narrower and more mechanical: classify each plan task, resolve a model/CLI candidate via `execute_selection.py` (Plan 1), and produce the exact instruction string the executing-plans/subagent-driven-development harness injects into its own dispatch — substituting native `Agent` tool calls with `dispatch.py`'s external-CLI path only when the resolved candidate isn't Claude itself.

**Tech Stack:** Python 3 stdlib only, `unittest`.

**Spec:** `docs/superpowers/specs/2026-08-28-ai-kit-spec-execute-design.md` (§8, superpowers adapter)

## Global Constraints

- Depends on Plan 1 (Foundation) being complete: `ai_kit_spec.execute_selection.resolve_execute_candidates`, `ai_kit_spec.commands.build_execute_command`, `ai_kit_spec.dispatch.dispatch_with_heartbeat` must all exist and be tested.
- Depends on Plan 2 (`ai-kit-spec-execute-gsd`) Task 6 having created `skills/ai-kit-spec-execute/detect_framework.py` and its stub `SKILL.md` — this plan's Task 5 extends both rather than recreating them. If Plan 2 has not yet run when this plan starts, Task 5 creates both files itself with the GSD branch stubbed the way Plan 2's Task 6 specifies, and Plan 2's Task 6 becomes a merge/extend instead of a create — whichever plan runs second must diff against the other's version rather than overwrite it.
- Never bypass `executing-plans`/`subagent-driven-development`'s own TDD enforcement, fresh-subagent-per-task, or review-between-tasks patterns — this adapter injects a model choice into that harness, it does not replace the harness (design spec §8, corrected during brainstorming from an earlier mischaracterization that superpowers had "nothing to delegate to").
- When the resolved candidate's CLI is `claude` itself, dispatch through the native `Agent` tool exactly as `subagent-driven-development` already does (with the resolved model passed as the tool's `model` parameter) — never route a same-vendor dispatch through the external-CLI `dispatch.py` path unnecessarily.

---

## File Structure

```
skills/ai-kit-spec-execute-superpowers/         (new skill directory, this plan's primary deliverable)
  SKILL.md                                       (superpowers-specific dispatch flow)
  ai_kit_spec_superpowers/
    __init__.py
    task_classification.py                       (classify a plan task's type from its Task N heading + Files block)
    dispatch_injection.py                         (build the model/CLI instruction injected into executing-plans/subagent-driven-development)
skills/ai-kit-spec-execute/
  detect_framework.py                             (extended: add the superpowers branch, per Plan 2's stub)
tests/test_ai_kit_spec_superpowers.py             (new test file)
```

---

### Task 1: `task_classification.py` — classify a plan task's type from its own structure

**Files:**
- Create: `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/task_classification.py`
- Test: `tests/test_ai_kit_spec_superpowers.py`

**Interfaces:**
- Consumes: nothing from other modules (pure text parsing over a plan task's markdown block — the same task blocks `writing-plans` itself produces, per its own `### Task N: [Component Name]` / `**Files:**` structure).
- Produces:
  - `classify_task(task_markdown: str) -> str` — returns `"frontend"`, `"backend"`, `"infra"`, or `"general"`. Classification signal: file extensions/paths under the task's `**Files:**` block (`.tsx`/`.jsx`/`.css`/`.vue` → frontend; `.py`/`.go`/`.rs`/`.sql`/`server`/`api` path segments → backend; `Dockerfile`/`.yml`/`.yaml`/`ci/`/`.github/` → infra; no confident signal → general). This mirrors `subagent-driven-development`'s own existing tiered-complexity classification approach (mechanical→cheap, architecture→most capable) but adds a task**-type** axis on top, which that skill doesn't already have.
  - `estimate_required_context(task_markdown: str, files_touched_sizes: dict) -> int` — sums byte sizes of every file path under `**Files:**` (from `files_touched_sizes`, a caller-supplied `{path: byte_size}` map — this function never reads the filesystem itself, keeping it pure/testable) plus a fixed prompt/scaffolding overhead constant, returns an estimated token count (bytes // 4, the standard rough approximation)

- [ ] **Step 1: Write the failing tests**

```python
class TestClassifyTask(unittest.TestCase):
    def test_classifies_frontend_from_file_extensions(self):
        task = "### Task 3: Button\n**Files:**\n- Create: `src/components/Button.tsx`\n"
        self.assertEqual(task_classification.classify_task(task), "frontend")

    def test_classifies_backend_from_file_paths(self):
        task = "### Task 4: API\n**Files:**\n- Create: `server/api/handlers.py`\n"
        self.assertEqual(task_classification.classify_task(task), "backend")

    def test_classifies_infra_from_ci_paths(self):
        task = "### Task 5: CI\n**Files:**\n- Modify: `.github/workflows/ci.yml`\n"
        self.assertEqual(task_classification.classify_task(task), "infra")

    def test_falls_back_to_general_with_no_confident_signal(self):
        task = "### Task 6: Docs\n**Files:**\n- Modify: `README.md`\n"
        self.assertEqual(task_classification.classify_task(task), "general")


class TestEstimateRequiredContext(unittest.TestCase):
    def test_sums_file_sizes_plus_overhead(self):
        task = "### Task 1\n**Files:**\n- Modify: `a.py`\n- Modify: `b.py`\n"
        sizes = {"a.py": 4000, "b.py": 8000}
        result = task_classification.estimate_required_context(task, sizes)
        self.assertEqual(result, (4000 + 8000) // 4 + task_classification.OVERHEAD_TOKENS)

    def test_missing_size_data_counts_as_zero_not_an_error(self):
        task = "### Task 1\n**Files:**\n- Create: `new.py`\n"
        result = task_classification.estimate_required_context(task, {})
        self.assertEqual(result, task_classification.OVERHEAD_TOKENS)
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_superpowers.TestClassifyTask \
  tests.test_ai_kit_spec_superpowers.TestEstimateRequiredContext -v 2>&1 | tail -20
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""Classifies a writing-plans-style Task block by file-type/path signal, and estimates the
context a resolved executor will need. Both are pure functions over caller-supplied text/data
-- neither touches the filesystem, keeping this module trivially unit-testable."""
import re


OVERHEAD_TOKENS = 2000  # fixed prompt/scaffolding overhead, on top of the touched files' content

_FRONTEND_EXTENSIONS = (".tsx", ".jsx", ".css", ".vue", ".scss")
_BACKEND_SIGNALS = (".py", ".go", ".rs", ".sql", "server/", "api/", "/api")
_INFRA_SIGNALS = ("dockerfile", ".yml", ".yaml", "ci/", ".github/")


def _files_block(task_markdown: str) -> str:
    match = re.search(r"\*\*Files:\*\*(.*?)(?:\n\*\*|\Z)", task_markdown, re.DOTALL)
    return match.group(1) if match else ""


def classify_task(task_markdown: str) -> str:
    block = _files_block(task_markdown).lower()
    if any(ext in block for ext in _FRONTEND_EXTENSIONS):
        return "frontend"
    if any(sig in block for sig in _BACKEND_SIGNALS):
        return "backend"
    if any(sig in block for sig in _INFRA_SIGNALS):
        return "infra"
    return "general"


def estimate_required_context(task_markdown: str, files_touched_sizes: dict) -> int:
    block = _files_block(task_markdown)
    paths = re.findall(r"`([^`]+)`", block)
    total_bytes = sum(files_touched_sizes.get(p, 0) for p in paths)
    return total_bytes // 4 + OVERHEAD_TOKENS
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec_superpowers.TestClassifyTask \
  tests.test_ai_kit_spec_superpowers.TestEstimateRequiredContext -v 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(ai-kit-spec-execute-superpowers): add task_classification.py"
```

---

### Task 2: `dispatch_injection.py` — build the model/CLI instruction injected into the harness

**Files:**
- Create: `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py`
- Test: `tests/test_ai_kit_spec_superpowers.py`

**Interfaces:**
- Consumes: `ai_kit_spec.execute_selection.resolve_execute_candidates`, `ai_kit_spec.commands.build_execute_command` (Plan 1); `task_classification.classify_task`, `task_classification.estimate_required_context` (Task 1).
- Produces: `build_dispatch_injection(task_markdown: str, candidates: list, files_touched_sizes: dict, affinity_table: dict, top_n_keys: list) -> dict` — returns:
  - `{"mode": "native_claude", "model": str}` when the top-ranked resolved candidate's `cli` is `"claude"` — the harness passes `model` straight to its own `Agent` tool call, unmodified from how `subagent-driven-development` already works
  - `{"mode": "external_cli", "command": str, "cli": str, "model": str}` when the top-ranked candidate is a different CLI — `command` is the filled `build_execute_command` template, ready for `dispatch.py`

- [ ] **Step 1: Write the failing tests**

```python
class TestBuildDispatchInjection(unittest.TestCase):
    def test_native_claude_mode_when_top_candidate_is_claude(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "claude/opus-5", "cli": "claude", "model": "claude-opus-5",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        result = dispatch_injection.build_dispatch_injection(
            task, candidates, {"server/api.py": 1000}, {}, ["claude/opus-5"])
        self.assertEqual(result, {"mode": "native_claude", "model": "claude-opus-5"})

    def test_external_cli_mode_when_top_candidate_is_another_cli(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        result = dispatch_injection.build_dispatch_injection(
            task, candidates, {"server/api.py": 1000}, {}, ["codex/terra"])
        self.assertEqual(result["mode"], "external_cli")
        self.assertEqual(result["cli"], "codex")
        self.assertIn("workspace-write", result["command"])

    def test_no_surviving_candidates_raises_value_error(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        with self.assertRaises(ValueError):
            dispatch_injection.build_dispatch_injection(task, [], {}, {}, [])
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_superpowers.TestBuildDispatchInjection -v 2>&1 | tail -20
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""Builds the exact dispatch instruction executing-plans/subagent-driven-development injects
at each task's dispatch point -- native Agent tool call when the resolved candidate is Claude
itself, otherwise a filled external-CLI command for dispatch.py. Never bypasses the harness
(design spec Section 8) -- this function's output is an INPUT to that harness's own dispatch
step, not a replacement for it."""
from ai_kit_spec.commands import build_execute_command
from ai_kit_spec.execute_selection import resolve_execute_candidates
from ai_kit_spec_superpowers.task_classification import classify_task, estimate_required_context


def build_dispatch_injection(task_markdown: str, candidates: list, files_touched_sizes: dict,
                              affinity_table: dict, top_n_keys: list) -> dict:
    task_type = classify_task(task_markdown)
    required_context = estimate_required_context(task_markdown, files_touched_sizes)
    resolved = resolve_execute_candidates(
        candidates, task_type, required_context, affinity_table, top_n_keys)
    if not resolved:
        raise ValueError(
            f"no execute candidate survived resolution for task_type={task_type!r}, "
            f"required_context={required_context} -- cannot build a dispatch injection"
        )
    top = resolved[0]
    if top["cli"] == "claude":
        return {"mode": "native_claude", "model": top["model"]}
    command = build_execute_command(top["cli"], target_dir="{target_dir}")
    filled = command.format(model=top["model"], target_dir="{target_dir}")
    return {"mode": "external_cli", "command": filled, "cli": top["cli"], "model": top["model"]}
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec_superpowers.TestBuildDispatchInjection -v 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(ai-kit-spec-execute-superpowers): add dispatch_injection.py"
```

---

### Task 3: `SKILL.md` for `ai-kit-spec-execute-superpowers`

**Files:**
- Create: `skills/ai-kit-spec-execute-superpowers/SKILL.md`

**Interfaces:**
- Consumes: `dispatch_injection.build_dispatch_injection` (Task 2), `ai_kit_spec.dispatch.dispatch_with_heartbeat`, `ai_kit_spec.detection.ensure_codegraph_registered`, `ai_kit_spec.tooling_guidance.build_tooling_guidance` (all Plan 1).

- [ ] **Step 1: Write the skill body**

```markdown
---
name: ai-kit-spec-execute-superpowers
description: Resolves the best available model/CLI for each task in a superpowers-generated implementation plan, then delegates actual execution to superpowers:subagent-driven-development (or superpowers:executing-plans for inline execution), injecting the resolved model/CLI at each dispatch point without bypassing that harness's TDD enforcement or review-between-tasks pattern. Use when ai-kit-spec-execute detects a superpowers-generated plan (docs/superpowers/plans/*.md) and needs to execute it.
---

# ai-kit-spec-execute-superpowers

**This skill never dispatches a task itself.** It resolves WHICH model/CLI a task should use,
then hands that resolution to `superpowers:subagent-driven-development` (recommended) or
`superpowers:executing-plans` as an explicit input at each dispatch point — those skills keep
full ownership of TDD enforcement, fresh-subagent-per-task, and review-between-tasks. Delegating
to them (rather than bypassing them) is deliberate: they carry pattern/TDD knowledge this skill
does not duplicate.

## Step 1: Per-task resolution, ahead of dispatch

Before `subagent-driven-development` dispatches a task's fresh subagent (or before
`executing-plans` executes a task inline), call
`ai_kit_spec_superpowers.dispatch_injection.build_dispatch_injection` with that task's markdown
block, the current resolved runtime/quota candidate list, and the user's configured top-N/
affinity table.

## Step 2: Apply the injection at the dispatch point

- `mode: native_claude` — pass `model` as the `Agent` tool's own `model` parameter, exactly as
  `subagent-driven-development` already does when a model tier is specified. No other change to
  that skill's dispatch flow.
- `mode: external_cli` — before dispatch, run `ensure_codegraph_registered` for `cli` and build
  any confirmed tooling guidance via `build_tooling_guidance`; append it to the task prompt.
  Then use `ai_kit_spec.dispatch.dispatch_with_heartbeat` to run `command` with the task's full
  prompt (including the plan's own TDD step instructions — this skill never strips those) piped
  via stdin.

## Step 3: Review-between-tasks is unaffected

Whichever mode Step 2 used, the review-between-tasks step defined by
`subagent-driven-development`/`executing-plans` proceeds unmodified afterward — this skill's
scope ends at dispatch.

## Step 4: Resumable state on quota exhaustion

Same pattern as `ai-kit-spec-execute-gsd`: on a quota-exhaustion signal, write resumable state
via `ai_kit_spec.dispatch.write_resumable_state` (plan path, task index, candidates already
tried) before surfacing the failure.
```

- [ ] **Step 2: Run skill-judge against this skill**

Invoke `skill-judge` on `skills/ai-kit-spec-execute-superpowers/SKILL.md`. Fix any finding
before proceeding.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "docs(ai-kit-spec-execute-superpowers): add SKILL.md"
```

---

### Task 4: Live smoke test — resolve and dispatch a real trivial task through both modes

**Files:** none created — verification-only task.

- [ ] **Step 1: Smoke test the `native_claude` mode**

Construct a trivial one-task plan (matching `writing-plans`' own `### Task N` format) whose
`**Files:**` block only touches a small `.py` file. Run `build_dispatch_injection` with a
candidate list where the top-ranked candidate is `claude`. Confirm the returned `mode` is
`native_claude` and hand-verify that value plugs correctly into an actual `Agent` tool call
(`model` parameter accepts it without error).

- [ ] **Step 2: Smoke test the `external_cli` mode**

Repeat with a candidate list where the top-ranked candidate is `codex` (already
smoke-tested end-to-end for its execute-mode command in Plan 1, Task 5, Step 5). Run the
returned `command` (filled) via `dispatch_with_heartbeat` against a real scratch directory with
a trivial prompt ("create a file named smoke.txt containing OK"). Confirm the file is actually
created — this is the full round-trip from task classification through actual write-capable
execution.

- [ ] **Step 3: Record the outcome and fix any discrepancy found**

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore(ai-kit-spec-execute-superpowers): smoke-test verified both dispatch modes"
```
