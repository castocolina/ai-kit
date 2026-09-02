# ai-kit-spec-execute-superpowers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the superpowers adapter for `ai-kit-spec-execute`: a skill that resolves the best available model/CLI for a superpowers-generated plan's task — live-quota-aware, walking the same escalation ladder the GSD adapter uses — then delegates the actual execution harness to `superpowers:subagent-driven-development` (preserving its TDD enforcement, fresh-subagent-per-task, agent-identity/resume semantics, task review, fix loops, and final review), injecting the pre-resolved model/CLI as an explicit input at its one documented implementer-dispatch point rather than bypassing the harness. **Scope note (design spec §8 formally corrected this revision — not a plan-only narrowing):** cross-AI review of an earlier revision flagged this plan's scope as narrower than design spec §8's original text, which named `executing-plans` and implied substitution at every subagent-dispatch point, without the design itself being updated to match. `docs/superpowers/specs/2026-08-28-ai-kit-spec-execute-design.md` §8 has now been amended in place (its own "Scope correction (this revision...)" paragraph) to state, as the binding design, exactly what this plan implements: `superpowers:executing-plans` is out of scope — confirmed from its own SKILL.md, its "Step 2: Execute Tasks" runs every task inline in the controller's own session ("Follow each step exactly", "Mark as completed") with no `Agent`-tool/subagent dispatch anywhere in it, so there is no point in that process to inject a resolution into; a design that named it as a target was unverified against that skill's real text, not a real integration path. The task reviewer, re-review, and final-review dispatches inside `subagent-driven-development` itself are also out of scope by that same corrected design text, and stay on that skill's own native model-selection logic — see Global Constraints for the full rationale.

**Architecture:** Unlike the GSD adapter (Plan 2), superpowers has no framework-level config surface to read or write — it is Claude-native only, with model selection happening at the point each subagent is dispatched via the `Agent` tool. This adapter's job is narrower and more mechanical: classify each plan task (frontend/backend/mixed — the same three-way axis `execute_selection.py` already expects, not a bespoke one), resolve a live-quota-checked model/CLI candidate, and produce the exact instruction string `subagent-driven-development`'s own "Dispatch the implementer" step (SKILL.md §"The Task Loop" → "1. Dispatch the implementer") consumes at each task's dispatch point — substituting native `Agent` tool calls with a real, tested dispatch path (`ai_kit_spec.execute_dispatch.dispatch_execute`) only when the resolved candidate isn't Claude itself. Because a dispatched external CLI is not a "live subagent" in the `Agent`-tool sense, this adapter uses `subagent-driven-development`'s own documented fallback branch for that case ("If your harness cannot send another message to a live subagent, dispatch a fresh implementer carrying the brief path, the report-file path, and the findings — the report file is the persistent memory either way") rather than inventing a new resume mechanism the harness doesn't already define.

**Tech Stack:** Python 3 stdlib only, `unittest`.

**Spec:** `docs/superpowers/specs/2026-08-28-ai-kit-spec-execute-design.md` (§5 model selection/escalation, §8 superpowers adapter, §10 resilience, §12 error handling)

## Global Constraints

- Depends on Plan 1 (Foundation) being complete: `ai_kit_spec.execute_selection.resolve_execute_candidates`/`candidates_to_ladder`, `ai_kit_spec.commands.build_execute_command`, `ai_kit_spec.dispatch.dispatch_with_heartbeat`/`write_resumable_state`, `ai_kit_spec.execute_dispatch.dispatch_execute`, `ai_kit_spec.quota.resolve_ladder_pick`/`refresh_quota_cache`, `ai_kit_spec.config_io.cfg_resolve`, `ai_kit_spec.cache.cache_read_json`/`cache_write_json`, `ai_kit_spec.detection.detect_tool_availability`/`resolve_agents_tooling_path`/`ensure_codegraph_registered`/`build_codegraph_index_command`, `ai_kit_spec.tooling_guidance.build_tooling_guidance`/`resolve_shared_tooling_reference_path` must all exist and be tested.
- Depends on Plan 2 (`ai-kit-spec-execute-gsd`) Task 6 having created `skills/ai-kit-spec-execute/detect_framework.py` and its stub `SKILL.md` — this plan's Task 5 extends both rather than recreating them. If Plan 2 has not yet run when this plan starts, Task 5 creates both files itself with the GSD branch stubbed the way Plan 2's Task 6 specifies, and Plan 2's Task 6 becomes a merge/extend instead of a create — whichever plan runs second must diff against the other's version rather than overwrite it.
- **Task classification is `"frontend"` / `"backend"` / `"mixed"` / `None`** — the same three-way axis `execute_selection.filter_by_affinity` already compares a candidate's `task_affinity` against (design spec §5, step 1: "infer task type (frontend/backend/mixed)"). `None` means no confident signal, and behaves in `filter_by_affinity` exactly like an untagged candidate: no preference expressed, never a rejection. This plan does **not** introduce a separate `infra`/`general` axis `execute_selection.py` was never built to understand.
- **Live quota drives every resolution — never `resolved[0]`.** Every dispatch decision walks the same ladder-escalation mechanism the GSD adapter already uses (`ai_kit_spec.quota.resolve_ladder_pick` over `ai_kit_spec.execute_selection.candidates_to_ladder`'s output, against a freshly-refreshed `quota.json`): the first ranked candidate that currently has quota wins; a candidate lacking a usable dispatch mechanism is dropped and the walk continues; only when every candidate in the ladder is quota-exhausted (or dispatch-failed for a quota reason, per `classify_dispatch_failure`, Task 2) does resolution raise `QuotaExhaustedError`, at which point resumable state is persisted and an hourly `CronCreate` wake is scheduled (design spec §10) — same shape of guarantee `ai_kit_spec_gsd.adapter.resolve_gsd_dispatch` already implements and tests, mirrored here rather than reinvented. **Explicit carve-out (HIGH finding): a `native_claude` fix-loop round's own model-TIER bump (rounds 4–5, `subagent-driven-development`'s own Model Selection section) is not a dispatch-mechanism resolution this ladder governs.** For a `cli is None` candidate, "availability" is the current Claude session itself — there is no separate CLI subprocess this adapter probes or waits on quota for, so there is nothing for `resolve_ladder_pick`/`quota.json` to walk. That fix-loop round's own model-alias choice among `opus`/`sonnet`/`haiku`/`fable` stays entirely `subagent-driven-development`'s own judgment call, made fresh each round exactly as its Model Selection section already specifies (Task 4's SKILL.md Step 3, `native_claude` paragraph) — the same native carve-out already applied to the review/re-review/final-review dispatches above, for the same reason: it answers a judgment-tier question, not a "which write-capable candidate can currently run this" question. If the current session's own Claude access becomes unusable, that is a session-level failure this adapter's `resolve-injection`/ladder has no visibility into and cannot route around — outside this plan's scope, not a gap in it.
- **Scope is `subagent-driven-development` only, and only its implementer-dispatch point — now the binding design, not a plan-only deviation.** `superpowers:executing-plans` (confirmed from its own SKILL.md) executes every task directly in the controller's own session — no `Agent`-tool dispatch, no subagent, no report file — so it has no extension point this adapter could inject into; this plan does not attempt to support it. Design spec §8 previously named both skills and implied substitution at every subagent-dispatch point; that text has been corrected in place (§8's own "Scope correction (this revision...)" paragraph, CRITICAL finding from cross-AI review — a plan may not silently narrow a binding design's stated contract, so the design itself was brought in sync with the verified facts below rather than left contradicting this plan) to state exactly what this plan implements: only `subagent-driven-development` has the documented extension point ("1. Dispatch the implementer") the design's substitution mechanism requires. Within `subagent-driven-development`, never bypass its own TDD enforcement, fresh-subagent-per-task, agent-identity/resume, task review, fix-loop, or final-review patterns — this adapter injects a model choice into that harness at its one documented extension point, it does not replace the harness. Task 4's SKILL.md defines exactly how that one step behaves under both `native_claude` and `external_cli` modes — no part of it is left undefined for the `external_cli` case. **Out of scope, deliberately, and not a gap (per the corrected design text):** the task reviewer, re-review, and final-review dispatches inside `subagent-driven-development`'s own "3. Review the task" / "4. The fix loop" / "Final Review" sections keep dispatching natively via the `Agent` tool, chosen by that skill's own "Model Selection" section (cost/complexity-tiered judgment — e.g. "use a model at least one tier above the implementer that got stuck"). That selection logic answers a different question (which judgment tier for a read-only review) than this adapter's live-quota execute-candidate ladder (which write-capable candidate can actually run the task) — folding review-model selection into this adapter's execute ladder would silently mix two unrelated policies. This adapter's own scope ends exactly where Task 4's SKILL.md Step 4 says it does: "This skill's own scope ends at Step 3 — it never touches review, fix-loop adjudication, or the ledger directly."
- **Only a candidate whose `cli` is unset (`None`) is native — `cli == "claude"` is a real, distinct, subprocess-invoked entry, never folded into native (CRITICAL finding).** When the resolved candidate's `cli` is `None` (a native/current-session candidate), dispatch through the native `Agent` tool exactly as `subagent-driven-development` already does (with the resolved model passed as the tool's `model` parameter). A candidate whose `cli` is the literal string `"claude"` is a configured, subprocess-dispatched `claude` CLI invocation — `ai_kit_spec.commands._COMMAND_BUILDERS` registers a real `(_EXECUTE, "claude")` builder (`_build_claude_execute_command`) for exactly this case — and is routed through `dispatch_execute`/`external_cli` mode like any other CLI-set entry; it must never be silently treated as the in-process `Agent`-tool alias. Today's config/dispatch code (confirmed by reading `commands.py`) defines every CLI-set entry, `"claude"` included, as external — only a CLI-omitted entry guarantees an `Agent`-tool alias. Never route a same-vendor dispatch through the external-CLI `dispatch_execute` path unnecessarily when the candidate's `cli` genuinely is unset.
- **A native candidate's `model` field is always a native `Agent`-tool alias — `opus`, `sonnet`, `haiku`, or `fable` — never a full model identifier** (e.g. never `claude-opus-5`). This matches the existing native-entry convention `ai_kit_spec_gsd.adapter.assemble_candidates` already documents ("a native (cli is None) entry's own `model` is already a Claude-tier-alias by this repo's existing convention") and the `Agent` tool's own contract, which accepts only those four aliases for its `model` parameter — a full identifier there is a silent runtime failure, not a degraded pick. Every test candidate and fixture in this plan uses a real alias.
- **`task_affinity`/`context_limit` are curated, optional fields — this plan does not populate them. Other optional fields DO already exist in today's real config and must not be mis-described as absent (CRITICAL finding fix).** `ai_kit_spec.config_io._KNOWN_REVIEWER_FIELDS` is `{"key", "model", "vendor", "cli", "command"}` — the schema-recognized flat fields every `[[reviewers]]` entry may carry — but `ai-kit-spec-config`'s own SKILL.md (confirmed by reading it, not assumed) actively prompts for and writes several more, ALL as flat TOML keys on the entry (this config format has no nested-object support — `ai-kit-spec-config`'s own Step 2.8 text is explicit that a nested table would silently be mis-written): an optional `strength` (Step 2.6, free text, not yet consumed by any resolution logic), and — for external-CLI entries whose builder accepts them — `effort`/`service_tier` (Step 2.4, e.g. codex's `-c model_reasoning_effort`/`-c service_tier` flags) and a per-entry `timeout_tiers` override (Step 2.8, overriding `policy.timeout_tiers` for one known-slow entry). `task_affinity` and `context_limit` are genuinely NOT among any of these — `ai-kit-spec-config` never asks for or writes either field today. Populating them (WebSearch-researched task-type fit and context-window data, design spec §5) is `ai-kit-spec-config`'s responsibility, tracked as a prerequisite outside this plan — not something this plan silently assumes into existence. Both `execute_selection.filter_by_affinity`/`filter_by_context` already treat an absent field as "no preference"/"no limit" (never as a rejection), so resolution against TODAY's real generated config degrades safely to ladder-position-only ranking — Task 2 tests this directly against a config shape matching `ai-kit-spec-config`'s actual current output, including the optional fields it DOES write (`strength`/`effort`/`service_tier`/`timeout_tiers`) alongside the two it genuinely never writes (`task_affinity`/`context_limit`), not a fixture that mischaracterizes the real shape by omitting the former.
- Every write-capable external-CLI dispatch goes through `ai_kit_spec.execute_dispatch.dispatch_execute` — never a raw call to `ai_kit_spec.dispatch.dispatch_with_heartbeat`. `dispatch_execute` is what supplies the real, live-verified execute-mode command (via `build_execute_command`, filled with a real caller-supplied `target_dir` at the moment of actual dispatch — never a literal `"{target_dir}"` placeholder baked in ahead of time), the dispatch-reinforcement prose, tooling guidance, and the soft-confinement instruction for `NO_HARD_SANDBOX_CLIS`. This plan's own dispatch code (`dispatch_superpowers_task`, Task 2) is a thin, tested wrapper around that existing path, not a reimplementation of it.

---

## File Structure

```
skills/ai-kit-spec-execute-superpowers/         (new skill directory, this plan's primary deliverable)
  SKILL.md                                       (superpowers-specific dispatch flow -- Task 4)
  ai-kit-spec-superpowers.py                     (shim invoking ai_kit_spec_superpowers.cli:main -- Task 3)
  ai_kit_spec_superpowers/
    __init__.py                                  (Task 1)
    task_classification.py                       (classify a plan task's type from its Task N heading + Files block -- Task 1)
    dispatch_injection.py                        (candidate assembly, live-quota resolution, dispatch wrapper -- Task 2)
    cli.py                                       (subcommand entrypoint: resolve-injection, dispatch-task, classify-dispatch-failure, resume-exclusions, write-resumable-state -- Task 3)
skills/ai-kit-spec-execute/
  detect_framework.py                             (extended: add the superpowers branch, make document_path/
                                                    conversation_signal the primary detection evidence -- Task 5)
  SKILL.md                                        (extended: pass document_path/conversation_signal into
                                                    detect_framework -- Task 5, CRITICAL finding)
tests/test_ai_kit_spec_superpowers.py             (new test file -- every task appends to it)
skills/ai-kit-spec-execute-superpowers/SMOKE_TEST_RESULTS.md (live smoke-test evidence -- Task 6)
```

---

### Task 1: `task_classification.py` — classify a plan task's type from its own structure

**Files:**
- Create: `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/__init__.py`
- Create: `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/task_classification.py`
- Create: `tests/test_ai_kit_spec_superpowers.py`

**Interfaces:**
- Consumes: nothing from other modules (pure text parsing over a plan task's markdown block — the same task blocks `writing-plans` itself produces, per its own `### Task N: [Component Name]` / `**Files:**` structure).
- Produces:
  - `classify_task(task_markdown: str) -> str | None` — returns `"frontend"`, `"backend"`, `"mixed"`, or `None`. Classification signal: file extensions/paths under the task's `**Files:**` block. Frontend signal: `.tsx`/`.jsx`/`.css`/`.vue`/`.scss`. Backend signal: `.py`/`.go`/`.rs`/`.sql`/`server/`/`api/`/`/api`. Both signal types present → `"mixed"`. Only frontend → `"frontend"`. Only backend → `"backend"`. Neither → `None` (no confident signal — matches `execute_selection.filter_by_affinity`'s own "untagged always passes" contract exactly; this plan never introduces a fourth category `execute_selection.py` doesn't compare against).
  - `extract_touched_paths(task_markdown: str) -> list[str]` — every backtick-quoted path under the task's `**Files:**` block, in document order. This is the SAME extraction `estimate_required_context` (below) uses internally, promoted to a public function so a caller (Task 2's `dispatch_injection.derive_files_touched_sizes`) can turn real paths into a real `{path: byte_size}` map without re-implementing this parsing — never duplicate the regex in a second module.
  - `estimate_required_context(task_markdown: str, files_touched_sizes: dict) -> int` — sums byte sizes of every path `extract_touched_paths` finds (looked up in the caller-supplied `files_touched_sizes` `{path: byte_size}` map — this function never reads the filesystem itself, keeping it pure/testable; a path missing from the map counts as 0, never an error) plus a fixed prompt/scaffolding overhead constant, returns an estimated token count (bytes // 4, the standard rough approximation)

- [ ] **Step 1: Create the package directory**

```bash
mkdir -p skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers
touch skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/__init__.py
```

- [ ] **Step 2: Write the failing tests, with the full test-file bootstrap**

This is the FIRST test class in the file — the header below (imports, `sys.path` bootstrap) goes in
ONCE, at the very top of `tests/test_ai_kit_spec_superpowers.py`. Every later Task in this plan
appends its own test classes below it, never repeats the bootstrap block.

```python
import os
import sys
import tempfile
import unittest

# Bootstraps every package root this plan's tests need. ai_kit_spec_superpowers (this plan) and
# ai_kit_spec (Plan 1, Foundation) both live outside this file's own directory, on no search path
# by default. skills/ai-kit-spec-execute is ALSO added here (not just
# skills/ai-kit-spec-execute-superpowers) because Task 5's detect_framework module lives there --
# this is the ONE bootstrap block for the whole file, at the top; it is never repeated.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                 "ai-kit-spec-execute-superpowers"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-execute"))

from ai_kit_spec_superpowers import task_classification


class TestClassifyTask(unittest.TestCase):
    def test_classifies_frontend_from_file_extensions(self):
        task = "### Task 3: Button\n**Files:**\n- Create: `src/components/Button.tsx`\n"
        self.assertEqual(task_classification.classify_task(task), "frontend")

    def test_classifies_backend_from_file_paths(self):
        task = "### Task 4: API\n**Files:**\n- Create: `server/api/handlers.py`\n"
        self.assertEqual(task_classification.classify_task(task), "backend")

    def test_classifies_mixed_when_both_signal_types_present(self):
        task = ("### Task 5: Full-stack widget\n**Files:**\n"
                "- Create: `src/components/Widget.tsx`\n- Create: `server/api/widget.py`\n")
        self.assertEqual(task_classification.classify_task(task), "mixed")

    def test_returns_none_with_no_confident_signal(self):
        task = "### Task 6: Docs\n**Files:**\n- Modify: `README.md`\n"
        self.assertIsNone(task_classification.classify_task(task))


class TestExtractTouchedPaths(unittest.TestCase):
    def test_extracts_every_backtick_path_in_order(self):
        task = "### Task 1\n**Files:**\n- Create: `a.py`\n- Modify: `b.py`\n"
        self.assertEqual(task_classification.extract_touched_paths(task), ["a.py", "b.py"])

    def test_preserves_writing_plans_line_qualified_paths_verbatim(self):
        # CRITICAL finding: writing-plans' own task template routinely emits a `Modify:` target
        # as a line-range-qualified path (`existing.py:123-145`, per the skill's own Task
        # Structure example), not a bare filesystem path. extract_touched_paths must return this
        # EXACT string, unmodified -- it is the SAME string estimate_required_context uses as a
        # files_touched_sizes dict key, and Task 2's derive_files_touched_sizes (the one place
        # that ever touches the filesystem) is where the line-range suffix gets stripped for
        # stat'ing, not here. Normalizing it in two places would let the two drift.
        task = "### Task 1\n**Files:**\n- Modify: `existing.py:123-145`\n"
        self.assertEqual(task_classification.extract_touched_paths(task),
                          ["existing.py:123-145"])


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

- [ ] **Step 3: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_superpowers.TestClassifyTask \
  tests.test_ai_kit_spec_superpowers.TestExtractTouchedPaths \
  tests.test_ai_kit_spec_superpowers.TestEstimateRequiredContext -v 2>&1 | tail -20
```

Expected: FAIL — module not found.

- [ ] **Step 4: Implement**

```python
"""Classifies a writing-plans-style Task block by file-type/path signal, and estimates the
context a resolved executor will need. Both are pure functions over caller-supplied text/data
-- neither touches the filesystem, keeping this module trivially unit-testable.

classify_task's return type is deliberately the SAME frontend/backend/mixed/None axis
ai_kit_spec.execute_selection.filter_by_affinity already compares a candidate's own
task_affinity against (design spec Section 5) -- there is no separate infra/general category
here; execute_selection.py was never built to understand one, and inventing one here would
silently make every infra-flavored task behave as an untagged (None) one anyway, just with an
extra, unused label."""
import re


OVERHEAD_TOKENS = 2000  # fixed prompt/scaffolding overhead, on top of the touched files' content

_FRONTEND_EXTENSIONS = (".tsx", ".jsx", ".css", ".vue", ".scss")
_BACKEND_SIGNALS = (".py", ".go", ".rs", ".sql", "server/", "api/", "/api")


def _files_block(task_markdown: str) -> str:
    match = re.search(r"\*\*Files:\*\*(.*?)(?:\n\*\*|\Z)", task_markdown, re.DOTALL)
    return match.group(1) if match else ""


def classify_task(task_markdown: str) -> str | None:
    block = _files_block(task_markdown).lower()
    is_frontend = any(ext in block for ext in _FRONTEND_EXTENSIONS)
    is_backend = any(sig in block for sig in _BACKEND_SIGNALS)
    if is_frontend and is_backend:
        return "mixed"
    if is_frontend:
        return "frontend"
    if is_backend:
        return "backend"
    return None


def extract_touched_paths(task_markdown: str) -> list:
    """Every backtick-quoted path under the task's **Files:** block, in document order. Public
    (not the module-private _files_block regex directly) so Task 2's dispatch_injection.
    derive_files_touched_sizes can stat the SAME paths this module classifies/estimates over --
    one extraction, two consumers, never a second hand-rolled regex drifting from this one.

    Returned VERBATIM, including a writing-plans-style line-range qualifier
    (`existing.py:123-145`, the framework's own real `Modify:` convention) when the source text
    has one -- this function never normalizes a path to a filesystem-resolvable form. That
    normalization is deliberately Task 2's own job (derive_files_touched_sizes, CRITICAL
    finding), applied ONLY at the point a path is actually joined against cwd and stat'd; keeping
    the raw string here means estimate_required_context's files_touched_sizes dict lookups (keyed
    by this exact function's output) and derive_files_touched_sizes' dict keys always agree."""
    return re.findall(r"`([^`]+)`", _files_block(task_markdown))


def estimate_required_context(task_markdown: str, files_touched_sizes: dict) -> int:
    total_bytes = sum(files_touched_sizes.get(p, 0) for p in extract_touched_paths(task_markdown))
    return total_bytes // 4 + OVERHEAD_TOKENS
```

- [ ] **Step 5: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec_superpowers.TestClassifyTask \
  tests.test_ai_kit_spec_superpowers.TestExtractTouchedPaths \
  tests.test_ai_kit_spec_superpowers.TestEstimateRequiredContext -v 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/__init__.py \
        skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/task_classification.py \
        tests/test_ai_kit_spec_superpowers.py
git commit -m "feat(ai-kit-spec-execute-superpowers): add task_classification.py"
```

---

### Task 2: `dispatch_injection.py` — live-quota candidate resolution + the real dispatch wrapper

**Files:**
- Create: `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py`
- Test: `tests/test_ai_kit_spec_superpowers.py` (append)

**Interfaces:**
- Consumes: `ai_kit_spec.config_io.cfg_resolve`; `ai_kit_spec.execute_selection.resolve_execute_candidates`/`candidates_to_ladder`; `ai_kit_spec.quota.resolve_ladder_pick`; `ai_kit_spec.commands.build_execute_command`; `ai_kit_spec.execute_dispatch.dispatch_execute` (all Plan 1); `task_classification.classify_task`/`estimate_required_context`/`extract_touched_paths` (Task 1).
- Produces:
  - `assemble_candidates(cwd: str, env: dict, cfg_resolve_fn=cfg_resolve) -> tuple[list, list]` — reads the same shared `review-spec.toml`/global config every other adapter reads (design spec §4 — the "no config surface" constraint is about a superpowers-specific config file like GSD's `.planning/config.json`, not about this shared candidate roster), returns `(candidates, top_n_keys)` in the same shape `ai_kit_spec_gsd.adapter.assemble_candidates` already produces and tests. Every candidate dict carries `task_affinity`/`context_limit` as `None` when the underlying config entry has neither (today's real `ai-kit-spec-config` output, per Global Constraints) — never a `KeyError`.
  - `derive_files_touched_sizes(task_markdown: str, cwd: str, isfile_fn=os.path.isfile, getsize_fn=os.path.getsize) -> dict` — the real `{path: byte_size}` map `estimate_required_context` needs: for every path `task_classification.extract_touched_paths` finds, strips a trailing writing-plans-style line-range qualifier (`existing.py:123-145` → `existing.py`, CRITICAL finding — the framework's own standard `Modify:` shape is line-qualified, and the raw string never resolves against the filesystem) before joining it against `cwd` and stat'ing it if it exists on disk; a path that doesn't exist yet (a `Create:` target) contributes `0`, matching `estimate_required_context`'s own "missing size counts as zero, never an error" contract — the returned dict's KEY is always the RAW (unstripped) path, so lookups via `extract_touched_paths`' own output still match. This is the ONE place in the whole plan that turns real touched-file paths into real byte counts; every caller of `build_dispatch_injection` gets its `files_touched_sizes` from here, never a manually-authored dict.
  - `class QuotaExhaustedError(RuntimeError)` — `.task_type`, `.tried` (every candidate key the walk actually visited — both quota-unavailable and dispatch-unusable, in ladder order, so a caller can persist the complete excluded set verbatim), `.reasons` (`{key: "quota" | "auth" | "timeout" | "configuration" | "dispatch_unavailable" | "no_usable_dispatch" | "real_error"}` — one entry per key in `.tried`; HIGH finding: six typed reasons, not just quota/auth — a probe timeout, a malformed command template, an unreachable CLI binary, or any other unrelated nonzero-exit failure must never be mislabeled "quota"), `.all_auth_failures` (`bool` property — `True` only when `.reasons` is non-empty and every value is `"auth"`), `.any_quota_recoverable` (`bool` property — `True` only when at least one value in `.reasons` is `"quota"`; HIGH finding: this, not `.all_auth_failures`, is the real gate a caller uses to decide whether scheduling an hourly CronCreate wake accomplishes anything — if it's `False`, every tried candidate failed for a reason waiting never fixes, and the caller must stop and surface the real problem(s) instead, design spec §12's "surface the real error; never silently retry disguised as quota-wait" rule). Both properties delegate to `reasons_summary` (below), never their own separate logic.
  - `reasons_summary(reasons: dict) -> dict` — CRITICAL finding (recurrence guard): `{"all_auth_failures": bool, "any_quota_recoverable": bool}` computed over an ARBITRARY reasons dict, not just a single `QuotaExhaustedError`'s own `.reasons`. Exists so a caller that must MERGE reasons across more than one `resolve-injection` call — cli.py, re-resolving after `--exclude-keys-json` already dropped some candidates before this call's own walk even started — can recompute the real, whole-wave recoverability instead of trusting one call's own narrower exception, which never even sees an already-excluded candidate's reason.
  - `compute_ladder_keys(task_markdown: str, candidates: list, files_touched_sizes: dict, affinity_table: dict, top_n_keys: list) -> list` — CRITICAL finding: the SAME affinity/context narrowing + ranking `build_dispatch_injection` performs internally (factored into the shared `_narrow_and_rank` helper both call), turned into the full ordered candidate-KEY list via `candidates_to_ladder`. This is deliberately NOT `list(top_n_keys)` (a prior revision's incomplete proxy — `top_n_keys` only carries `policy.ladder`'s configured keys and silently omits any candidate outside it): a candidate ranked by `resolve_execute_candidates` but absent from `policy.ladder` still gets a real, ordered (last-ranked) position here. `cli.py`'s `resolve-injection` calls this ONCE, over the FULL pre-exclusion candidate set, and exposes the result as every response's own `ladder_keys` — Task 4's SKILL.md Rounds 4–5 capability-escalation rule needs this complete, stable ranking to prove a replacement candidate is genuinely ranked strictly above the stuck one, including one `top_n_keys` alone would never have surfaced.
  - `compute_resume_exclusions(tried: list, reasons: dict, prior_excluded_keys: list) -> list` — CRITICAL finding (recurrence guard): the single place that computes what a caller may PERSIST as a resumable-state `excluded_keys` set — `prior_excluded_keys` plus every key in `tried` whose reason is NOT `"quota"` (a `"quota"` reason is deliberately dropped, so a later resume, after quota genuinely recovers, can pick that candidate again — never permanently excluded by its own time-bound exhaustion event). Returns a sorted list.
  - `build_dispatch_injection(task_markdown: str, candidates: list, files_touched_sizes: dict, affinity_table: dict, top_n_keys: list, quota: dict | None = None, resolve_ladder_pick_fn=resolve_ladder_pick, build_execute_command_fn=build_execute_command) -> dict` — walks the live-quota ladder (never `resolved[0]`), dropping (not just skipping) a quota-available candidate whose CLI has no registered execute-mode builder (`build_execute_command_fn` raises `ValueError` — CRITICAL finding: "usable-dispatch filtering", same drop-and-continue shape `ai_kit_spec_gsd.adapter.resolve_gsd_dispatch` already uses) and continuing the walk; returns `{"mode": "native_claude", "model": str, "key": str}` when the chosen candidate's `cli` is `None` (CRITICAL finding: only `cli is None` is a native `Agent`-tool alias — `cli == "claude"` is a real, subprocess-invoked entry with its own registered execute-mode builder, `ai_kit_spec.commands._build_claude_execute_command`, and is routed through `external_cli` like any other CLI-set entry, never silently folded into `native_claude`), or `{"mode": "external_cli", "key": str, "cli": str, "model": str, "effort": str | None, "service_tier": str | None}` otherwise. Raises `ValueError` if no candidate survives affinity/context narrowing at all (a curation gap, not an availability problem), or `QuotaExhaustedError` if narrowing succeeded but every narrowed candidate is either quota-exhausted or has no usable dispatch mechanism. **`candidates` empty on entry is the caller's own signal that every configured candidate is already excluded — CRITICAL finding: `cli.py`'s `resolve-injection` checks this itself and never calls this function in that case**, because an empty `candidates` list narrows to an empty `ranked` list here too, and this function cannot tell that apart from a genuine curation gap (nothing configured for this task type at all) — see `cli.py`'s own docs below for how it distinguishes the two.
  - `dispatch_superpowers_task(injection: dict, prompt: str, target_dir: str, heartbeat_interval: int, timeout: int, format_block: str | None = None, tool_availability: dict | None = None, agents_tooling_path=None, codegraph_registered: bool = False, dispatch_execute_fn=dispatch_execute) -> dict` — the ONLY place `mode: "external_cli"` actually runs a subprocess; a thin, tested wrapper around `dispatch_execute`. Raises `ValueError` for a `native_claude` injection (that mode dispatches via the `Agent` tool, in-process, and never reaches this function).
  - `classify_dispatch_failure(dispatch_result: dict) -> str` — `"ok"` (`returncode == 0`), `"quota"` (nonzero + a rate/usage-limit signal in combined stdout+stderr, never on a real timeout), or `"real_error"` (anything else, INCLUDING an authentication/entitlement/setup signal — HIGH finding: those never get better by waiting, so they must never be classified `"quota"` and trigger the hourly wake loop) — design spec §12's "never silently retry disguised as quota-wait" rule, made checkable.

- [ ] **Step 1: Write the failing tests**

```python
from ai_kit_spec_superpowers import dispatch_injection


class TestAssembleCandidates(unittest.TestCase):
    def test_reads_reviewers_and_ladder_from_shared_config(self):
        fake_resolved = {
            "policy": {"ladder": ["claude/opus-5", "codex/terra"]},
            "reviewers": [
                {"key": "claude/opus-5", "model": "opus", "cli": None, "vendor": "anthropic"},
                {"key": "codex/terra", "model": "gpt-5.6-terra", "cli": "codex", "vendor": "openai",
                 "task_affinity": "backend", "context_limit": 1_000_000},
            ],
        }
        candidates, top_n_keys = dispatch_injection.assemble_candidates(
            "/repo", {}, cfg_resolve_fn=lambda cwd, env: fake_resolved)
        self.assertEqual(top_n_keys, ["claude/opus-5", "codex/terra"])
        self.assertEqual(candidates[1]["task_affinity"], "backend")
        self.assertEqual(candidates[1]["cli"], "codex")

    def test_resolves_end_to_end_against_todays_real_config_shape(self):
        # CRITICAL finding: ai-kit-spec-config's real generated review-spec.toml carries the
        # schema-known key/model/vendor/cli/command PLUS several optional flat fields it already
        # prompts for and writes today -- strength (Step 2.6), effort/service_tier (Step 2.4, for
        # a CLI whose builder uses them), and a per-entry timeout_tiers override (Step 2.8) --
        # confirmed by reading ai-kit-spec-config/SKILL.md and ai_kit_spec.config_io.
        # _KNOWN_REVIEWER_FIELDS directly, not assumed. Only task_affinity/context_limit are
        # genuinely never written yet (Global Constraints). Proves assemble_candidates ->
        # build_dispatch_injection still resolves correctly (ladder-position-only ranking)
        # against that REAL shape -- including the optional fields it DOES carry -- not only
        # against a fixture that mischaracterizes today's real output as narrower than it is.
        fake_resolved = {
            "policy": {"ladder": ["claude/opus-5", "codex/terra"]},
            "reviewers": [
                {"key": "claude/opus-5", "model": "opus", "cli": None, "vendor": "anthropic",
                 "strength": "planning"},
                {"key": "codex/terra", "model": "gpt-5.6-terra", "cli": "codex", "vendor": "openai",
                 "strength": "coding", "effort": "high", "service_tier": "priority",
                 "timeout_tiers": [900, 1800]},
            ],
        }
        candidates, top_n_keys = dispatch_injection.assemble_candidates(
            "/repo", {}, cfg_resolve_fn=lambda cwd, env: fake_resolved)
        self.assertIsNone(candidates[0]["task_affinity"])
        self.assertIsNone(candidates[0]["context_limit"])
        self.assertEqual(candidates[1]["effort"], "high")
        self.assertEqual(candidates[1]["service_tier"], "priority")
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        result = dispatch_injection.build_dispatch_injection(
            task, candidates, {}, {}, top_n_keys, quota={})
        self.assertEqual(result, {"mode": "native_claude", "model": "opus", "key": "claude/opus-5"})


class TestDeriveFilesTouchedSizes(unittest.TestCase):
    def test_stats_real_existing_files_and_zeros_missing_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            real_path = os.path.join(tmp, "a.py")
            with open(real_path, "w") as f:
                f.write("x" * 4000)
            task = "### Task 1\n**Files:**\n- Modify: `a.py`\n- Create: `new.py`\n"
            sizes = dispatch_injection.derive_files_touched_sizes(task, tmp)
        self.assertEqual(sizes, {"a.py": 4000, "new.py": 0})

    def test_resolves_writing_plans_line_qualified_paths_to_the_real_file(self):
        # CRITICAL finding: writing-plans' own standard task shape (this plan's own Task
        # Structure, and every task in this very document) writes a Modify: target as
        # `existing.py:123-145` -- a line-range-qualified path, never a bare filesystem path.
        # Joining that literal string against cwd always misses (isfile() is False for a path
        # containing a trailing `:123-145`), so every real Modify: target silently contributed 0
        # bytes and context-size filtering was inert for the framework's own standard shape. The
        # dict KEY stays the raw, unqualified string (estimate_required_context looks sizes up by
        # extract_touched_paths' own raw output) -- only the on-disk lookup is normalized.
        with tempfile.TemporaryDirectory() as tmp:
            real_path = os.path.join(tmp, "existing.py")
            with open(real_path, "w") as f:
                f.write("x" * 4000)
            task = "### Task 1\n**Files:**\n- Modify: `existing.py:123-145`\n"
            sizes = dispatch_injection.derive_files_touched_sizes(task, tmp)
        self.assertEqual(sizes, {"existing.py:123-145": 4000})


class TestComputeLadderKeys(unittest.TestCase):
    def test_includes_a_candidate_ranked_outside_policy_ladder(self):
        # CRITICAL finding (Rounds 4-5 capability escalation): top_n_keys (policy.ladder's own
        # configured keys) is an INCOMPLETE proxy for the real, full ordered candidate set --
        # codex/terra below is narrowed/ranked by resolve_execute_candidates (no affinity/context
        # rejection) but is absent from top_n_keys entirely; it must still appear here, ranked
        # last, or a stuck top_n_keys candidate could never be proven "escalated past" it.
        candidates = [
            {"key": "claude/opus-5", "model": "opus", "cli": None, "vendor": "anthropic",
             "task_affinity": None, "context_limit": None},
            {"key": "codex/terra", "model": "gpt-5.6-terra", "cli": "codex", "vendor": "openai",
             "task_affinity": None, "context_limit": None},
        ]
        task = "### Task 1\n**Files:**\n- Create: `a.py`\n"
        result = dispatch_injection.compute_ladder_keys(task, candidates, {}, {},
                                                          ["claude/opus-5"])
        self.assertEqual(result, ["claude/opus-5", "codex/terra"])


class TestBuildDispatchInjection(unittest.TestCase):
    def test_native_claude_mode_when_top_candidate_has_quota(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "claude/opus-5", "cli": None, "model": "opus",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        result = dispatch_injection.build_dispatch_injection(
            task, candidates, {"server/api.py": 1000}, {}, ["claude/opus-5"], quota={})
        self.assertEqual(result, {"mode": "native_claude", "model": "opus",
                                   "key": "claude/opus-5"})

    def test_external_cli_mode_when_top_candidate_is_another_cli(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        result = dispatch_injection.build_dispatch_injection(
            task, candidates, {"server/api.py": 1000}, {}, ["codex/terra"], quota={})
        self.assertEqual(result, {"mode": "external_cli", "key": "codex/terra", "cli": "codex",
                                   "model": "gpt-5.6-terra", "effort": None, "service_tier": None})

    def test_escalates_past_a_quota_exhausted_top_candidate(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {"key": "claude/opus-5", "cli": None, "model": "opus",
             "task_affinity": "backend", "context_limit": 1_000_000},
            {"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
             "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        quota = {"claude/opus-5": {"available": False}, "codex/terra": {"available": True}}
        result = dispatch_injection.build_dispatch_injection(
            task, candidates, {}, {}, ["claude/opus-5", "codex/terra"], quota=quota)
        self.assertEqual(result["mode"], "external_cli")
        self.assertEqual(result["key"], "codex/terra")

    def test_drops_a_quota_available_candidate_with_no_usable_dispatch_mechanism(self):
        # CRITICAL finding: a candidate can have quota AND still be undispatchable (its cli has no
        # registered execute-mode builder -- build_execute_command raises ValueError for it). This
        # must be dropped, not returned as a broken external_cli injection that blows up later.
        # MEDIUM finding: "gemini" is used here, not "grok" -- ai_kit_spec.commands._COMMAND_
        # BUILDERS (confirmed by reading commands.py) registers a real (_EXECUTE, "grok") builder
        # today, so "grok" would misstate an existing capability as absent; "gemini" has NO entry
        # in _COMMAND_BUILDERS at all -- review builders are exactly codex/claude/grok/opencode/
        # cursor-agent, and gemini is not among them either -- so this fixture matches a real gap
        # in today's code (build_execute_command("gemini") raises ValueError) rather than
        # simulating one that doesn't exist.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {"key": "gemini/main", "cli": "gemini", "model": "gemini-3-pro",
             "task_affinity": "backend", "context_limit": 1_000_000},
            {"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
             "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        quota = {"gemini/main": {"available": True}, "codex/terra": {"available": True}}

        def fake_build_execute_command(cli, **params):
            if cli == "gemini":
                raise ValueError("no execute-mode builder registered for cli='gemini'")
            return "codex exec --sandbox workspace-write -m {model}"

        result = dispatch_injection.build_dispatch_injection(
            task, candidates, {}, {}, ["gemini/main", "codex/terra"], quota=quota,
            build_execute_command_fn=fake_build_execute_command)
        self.assertEqual(result["key"], "codex/terra")

    def test_cli_claude_is_routed_external_not_treated_as_native(self):
        # CRITICAL finding: only cli is None guarantees a native Agent-tool alias. cli == "claude"
        # is a real, subprocess-invoked entry -- ai_kit_spec.commands._COMMAND_BUILDERS registers
        # a real (_EXECUTE, "claude") builder for it -- and must be routed through external_cli
        # mode like any other CLI-set entry, never silently folded into native_claude.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "claude-cli/opus-5", "cli": "claude", "model": "opus",
                        "task_affinity": "backend", "context_limit": 1_000_000}]

        def fake_build_execute_command(cli, **params):
            return "claude -p --model {model}"

        result = dispatch_injection.build_dispatch_injection(
            task, candidates, {}, {}, ["claude-cli/opus-5"], quota={},
            build_execute_command_fn=fake_build_execute_command)
        self.assertEqual(result, {"mode": "external_cli", "key": "claude-cli/opus-5",
                                   "cli": "claude", "model": "opus", "effort": None,
                                   "service_tier": None})

    def test_no_surviving_candidates_raises_value_error(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        with self.assertRaises(ValueError):
            dispatch_injection.build_dispatch_injection(task, [], {}, {}, [], quota={})

    def test_every_candidate_quota_exhausted_raises_quota_exhausted_error_with_reasons(self):
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "claude/opus-5", "cli": None, "model": "opus",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        quota = {"claude/opus-5": {"available": False, "detail": "usage limit reached"}}
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                task, candidates, {}, {}, ["claude/opus-5"], quota=quota)
        self.assertEqual(ctx.exception.tried, ["claude/opus-5"])
        self.assertEqual(ctx.exception.reasons, {"claude/opus-5": "quota"})
        self.assertFalse(ctx.exception.all_auth_failures)
        self.assertEqual(ctx.exception.task_type, "backend")

    def test_auth_failure_is_classified_distinctly_and_flagged_all_auth_failures(self):
        # HIGH finding: an unauthenticated/unentitled candidate must never look like a real,
        # time-bound quota exhaustion -- .all_auth_failures is what tells a caller to skip the
        # futile hourly CronCreate wake and surface an actionable setup error instead.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        quota = {"codex/terra": {"available": False, "detail": "Error: not authenticated"}}
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                task, candidates, {}, {}, ["codex/terra"], quota=quota)
        self.assertEqual(ctx.exception.reasons, {"codex/terra": "auth"})
        self.assertTrue(ctx.exception.all_auth_failures)
        self.assertFalse(ctx.exception.any_quota_recoverable)

    def test_timeout_failure_classified_distinctly_not_quota(self):
        # HIGH finding: a probe timeout is a real, non-time-bound problem (a hung/broken CLI
        # invocation) -- it must never be classified "quota" and trigger a futile hourly wake.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        quota = {"codex/terra": {"available": False, "detail": "timed out after 30s"}}
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                task, candidates, {}, {}, ["codex/terra"], quota=quota)
        self.assertEqual(ctx.exception.reasons, {"codex/terra": "timeout"})
        self.assertFalse(ctx.exception.any_quota_recoverable)

    def test_malformed_command_template_classified_as_configuration_not_quota(self):
        # HIGH finding: a bad/missing command template is a config problem -- never fixed by
        # waiting for quota to refill.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        quota = {"codex/terra": {"available": False,
                                   "detail": "reviewer 'codex/terra' has a malformed command "
                                             "template: KeyError"}}
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                task, candidates, {}, {}, ["codex/terra"], quota=quota)
        self.assertEqual(ctx.exception.reasons, {"codex/terra": "configuration"})
        self.assertFalse(ctx.exception.any_quota_recoverable)

    def test_os_error_style_failure_classified_as_dispatch_unavailable(self):
        # HIGH finding: the CLI binary itself failing to launch is not a quota problem either.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        quota = {"codex/terra": {"available": False,
                                   "detail": "[Errno 2] No such file or directory: 'codex'"}}
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                task, candidates, {}, {}, ["codex/terra"], quota=quota)
        self.assertEqual(ctx.exception.reasons, {"codex/terra": "dispatch_unavailable"})
        self.assertFalse(ctx.exception.any_quota_recoverable)

    def test_arbitrary_nonzero_exit_classified_as_real_error_not_quota(self):
        # HIGH finding (the core bug): prior to this revision, EVERY non-auth detail defaulted to
        # "quota" -- a bad model id or any other unrelated failure text is a real error, not a
        # time-bound rate limit, and must never trigger a futile hourly CronCreate wake.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [{"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        quota = {"codex/terra": {"available": False, "detail": "Error: unrecognized model id"}}
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                task, candidates, {}, {}, ["codex/terra"], quota=quota)
        self.assertEqual(ctx.exception.reasons, {"codex/terra": "real_error"})
        self.assertFalse(ctx.exception.any_quota_recoverable)

    def test_any_quota_recoverable_true_when_at_least_one_reason_is_quota(self):
        # HIGH finding: any_quota_recoverable is the general gate a caller uses to decide whether
        # scheduling an hourly CronCreate wake accomplishes anything -- True as soon as ANY tried
        # candidate's reason is "quota", even when others in the same batch are permanent.
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        candidates = [
            {"key": "claude/opus-5", "cli": None, "model": "opus",
             "task_affinity": "backend", "context_limit": 1_000_000},
            {"key": "codex/terra", "cli": "codex", "model": "gpt-5.6-terra",
             "task_affinity": "backend", "context_limit": 1_000_000},
        ]
        quota = {"claude/opus-5": {"available": False, "detail": "usage limit reached"},
                  "codex/terra": {"available": False, "detail": "not authenticated"}}
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                task, candidates, {}, {}, ["claude/opus-5", "codex/terra"], quota=quota)
        self.assertTrue(ctx.exception.any_quota_recoverable)
        self.assertFalse(ctx.exception.all_auth_failures)


class TestReasonsSummary(unittest.TestCase):
    def test_summarizes_a_reasons_dict_merged_across_more_than_one_call(self):
        # CRITICAL finding (recurrence guard): this is the exact shape cli.py's resolve-injection
        # must recompute over -- a reasons dict merging an earlier wave's own already-known
        # reasons (passed in via --excluded-reasons-json) with a fresh QuotaExhaustedError's own
        # `.reasons` from THIS call, since a single call's own exception never sees a key that was
        # excluded before its ladder walk even started.
        merged = {"claude/opus-5": "auth", "codex/terra": "quota"}
        summary = dispatch_injection.reasons_summary(merged)
        self.assertFalse(summary["all_auth_failures"])
        self.assertTrue(summary["any_quota_recoverable"])

    def test_empty_reasons_is_neither_all_auth_nor_quota_recoverable(self):
        summary = dispatch_injection.reasons_summary({})
        self.assertFalse(summary["all_auth_failures"])
        self.assertFalse(summary["any_quota_recoverable"])


class TestComputeResumeExclusions(unittest.TestCase):
    def test_quota_reason_keys_are_not_permanently_excluded(self):
        # CRITICAL finding (recurrence): a persisted resume state must NOT permanently exclude a
        # candidate whose only failure reason was quota -- it must be eligible again once quota
        # recovers, or the hourly CronCreate wake can never actually resume anything.
        result = dispatch_injection.compute_resume_exclusions(
            tried=["claude/opus-5", "codex/terra"],
            reasons={"claude/opus-5": "quota", "codex/terra": "auth"},
            prior_excluded_keys=[])
        self.assertEqual(result, ["codex/terra"])

    def test_prior_permanent_exclusions_are_preserved(self):
        result = dispatch_injection.compute_resume_exclusions(
            tried=["grok/main"], reasons={"grok/main": "no_usable_dispatch"},
            prior_excluded_keys=["codex/terra"])
        self.assertEqual(result, ["codex/terra", "grok/main"])

    def test_round_trip_quota_recovery_makes_candidate_eligible_again(self):
        # The round-trip this CRITICAL finding requires: an all-quota-exhausted ladder computes a
        # resume-state exclusion set, THEN (once quota recovers) a fresh build_dispatch_injection
        # call using THAT exclusion set must be able to pick the previously-exhausted candidate
        # again -- never permanently locked out by its own earlier exhaustion event.
        candidates = [{"key": "claude/opus-5", "cli": None, "model": "opus",
                        "task_affinity": "backend", "context_limit": 1_000_000}]
        quota_when_exhausted = {"claude/opus-5": {"available": False, "detail": "usage limit"}}
        task = "### Task 1\n**Files:**\n- Create: `server/api.py`\n"
        with self.assertRaises(dispatch_injection.QuotaExhaustedError) as ctx:
            dispatch_injection.build_dispatch_injection(
                task, candidates, {}, {}, ["claude/opus-5"], quota=quota_when_exhausted)
        excluded_keys = dispatch_injection.compute_resume_exclusions(
            ctx.exception.tried, ctx.exception.reasons, [])
        self.assertEqual(excluded_keys, [])  # a quota-only reason -- nothing permanently excluded

        # Resume: candidates filtered by excluded_keys (none removed here), quota now recovered.
        surviving = [c for c in candidates if c["key"] not in excluded_keys]
        quota_recovered = {"claude/opus-5": {"available": True}}
        result = dispatch_injection.build_dispatch_injection(
            task, surviving, {}, {}, ["claude/opus-5"], quota=quota_recovered)
        self.assertEqual(result["key"], "claude/opus-5")


class TestDispatchSuperpowersTask(unittest.TestCase):
    def test_delegates_to_dispatch_execute_with_a_real_candidate_dict(self):
        injection = {"mode": "external_cli", "key": "codex/terra", "cli": "codex",
                      "model": "gpt-5.6-terra", "effort": "high", "service_tier": None}
        captured = {}

        def fake_dispatch_execute(candidate, prompt, target_dir, heartbeat_interval, timeout,
                                   format_block=None, tool_availability=None,
                                   agents_tooling_path=None, codegraph_registered=False):
            captured.update(candidate=candidate, prompt=prompt, target_dir=target_dir)
            return {"cli": "codex", "model": "gpt-5.6-terra", "command": "codex exec ...",
                    "returncode": 0, "stdout": "ok", "stderr": "", "timed_out": False}

        result = dispatch_injection.dispatch_superpowers_task(
            injection, "do the task", "/real/scratch/dir", 60, 900,
            dispatch_execute_fn=fake_dispatch_execute)
        self.assertEqual(captured["target_dir"], "/real/scratch/dir")
        self.assertEqual(captured["candidate"]["cli"], "codex")
        self.assertEqual(captured["candidate"]["effort"], "high")
        self.assertEqual(result["returncode"], 0)

    def test_native_claude_injection_raises_value_error(self):
        injection = {"mode": "native_claude", "model": "opus", "key": "claude/opus-5"}
        with self.assertRaises(ValueError):
            dispatch_injection.dispatch_superpowers_task(injection, "prompt", "/dir", 60, 900)

    def test_real_dispatch_execute_path_produces_a_real_workspace_write_command(self):
        # Confirms this wrapper genuinely reaches ai_kit_spec.execute_dispatch.dispatch_execute's
        # OWN real command-building (HIGH finding: never a raw dispatch_with_heartbeat call, never
        # a "{target_dir}" placeholder) by calling the real, un-mocked dispatch_execute and only
        # substituting ITS OWN dispatch_fn (the actual subprocess launch) -- the same pattern
        # tests.test_ai_kit_spec's own execute_dispatch.dispatch_execute tests already use.
        from ai_kit_spec.execute_dispatch import dispatch_execute as real_dispatch_execute

        injection = {"mode": "external_cli", "key": "codex/terra", "cli": "codex",
                      "model": "gpt-5.6-terra", "effort": None, "service_tier": None}
        captured_command = {}

        def fake_dispatch_fn(command, prompt, heartbeat_interval, timeout):
            captured_command["value"] = command
            return {"returncode": 0, "stdout": "DONE", "stderr": "", "timed_out": False}

        def dispatch_execute_with_fake_subprocess(candidate, prompt, target_dir,
                                                    heartbeat_interval, timeout, **kwargs):
            return real_dispatch_execute(candidate, prompt, target_dir, heartbeat_interval,
                                          timeout, dispatch_fn=fake_dispatch_fn, **kwargs)

        result = dispatch_injection.dispatch_superpowers_task(
            injection, "do the task", "/real/scratch/dir", 60, 900,
            dispatch_execute_fn=dispatch_execute_with_fake_subprocess)
        self.assertIn("workspace-write", captured_command["value"])
        self.assertIn("/real/scratch/dir", captured_command["value"])
        self.assertEqual(result["command"], captured_command["value"])


class TestClassifyDispatchFailure(unittest.TestCase):
    def test_ok_on_zero_returncode(self):
        self.assertEqual(dispatch_injection.classify_dispatch_failure(
            {"returncode": 0, "stdout": "", "stderr": "", "timed_out": False}), "ok")

    def test_quota_on_quota_signal_and_nonzero_returncode(self):
        self.assertEqual(dispatch_injection.classify_dispatch_failure(
            {"returncode": 1, "stdout": "Error: usage limit reached", "stderr": "",
             "timed_out": False}), "quota")

    def test_real_error_on_auth_signal_even_with_nonzero_returncode(self):
        # HIGH finding: an auth/entitlement/setup failure must classify as real_error, never
        # quota -- it will never be fixed by an hourly quota-wake retry.
        self.assertEqual(dispatch_injection.classify_dispatch_failure(
            {"returncode": 1, "stdout": "Error: not authenticated", "stderr": "",
             "timed_out": False}), "real_error")

    def test_real_error_on_unrelated_nonzero_returncode(self):
        self.assertEqual(dispatch_injection.classify_dispatch_failure(
            {"returncode": 1, "stdout": "SyntaxError", "stderr": "", "timed_out": False}),
            "real_error")

    def test_real_error_on_timeout_even_with_quota_looking_text(self):
        self.assertEqual(dispatch_injection.classify_dispatch_failure(
            {"returncode": -9, "stdout": "rate limit", "stderr": "", "timed_out": True}),
            "real_error")
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_superpowers.TestAssembleCandidates \
  tests.test_ai_kit_spec_superpowers.TestDeriveFilesTouchedSizes \
  tests.test_ai_kit_spec_superpowers.TestComputeLadderKeys \
  tests.test_ai_kit_spec_superpowers.TestBuildDispatchInjection \
  tests.test_ai_kit_spec_superpowers.TestReasonsSummary \
  tests.test_ai_kit_spec_superpowers.TestComputeResumeExclusions \
  tests.test_ai_kit_spec_superpowers.TestDispatchSuperpowersTask \
  tests.test_ai_kit_spec_superpowers.TestClassifyDispatchFailure -v 2>&1 | tail -20
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""Live-quota-aware candidate resolution and the real dispatch wrapper for
ai-kit-spec-execute-superpowers. Never bypasses subagent-driven-development (design spec Section
8; superpowers:executing-plans is out of scope -- see Global Constraints) -- build_dispatch_
injection's output is an INPUT to that harness's own "Dispatch the implementer" step, not a
replacement for it, and dispatch_superpowers_task is the ONLY place an external_cli injection
actually runs a subprocess -- always through the existing, live-verified
ai_kit_spec.execute_dispatch.dispatch_execute path, never a raw dispatch_with_heartbeat call and
never a target_dir placeholder baked in ahead of the real dispatch call (HIGH finding)."""
import os
import re

from ai_kit_spec.commands import build_execute_command
from ai_kit_spec.config_io import cfg_resolve
from ai_kit_spec.execute_dispatch import dispatch_execute
from ai_kit_spec.execute_selection import candidates_to_ladder, resolve_execute_candidates
from ai_kit_spec.quota import resolve_ladder_pick

from ai_kit_spec_superpowers.task_classification import (
    classify_task,
    estimate_required_context,
    extract_touched_paths,
)

# Rate/usage-limit signals only -- genuinely time-bound, worth an hourly quota-wake retry.
_DISPATCH_QUOTA_SIGNALS = ("usage limit", "quota", "rate limit", "rate_limit")
# Auth/entitlement/setup signals -- HIGH finding: these never get better by waiting, so they must
# classify as real_error (never "quota"), or an unauthenticated CLI triggers a futile hourly
# CronCreate wake loop forever. Mirrors ai_kit_spec.quota's own private _UNAVAILABLE_SIGNALS
# auth-flavored entries (duplicated, not imported -- that name is a private implementation detail
# of quota.py's probe_reviewer_quota, not a shared public constant). Keep in sync by hand.
_AUTH_SIGNALS = ("actionrequirederror", "not authenticated", "not logged in")
# A probe timeout -- quota.py's own probe_reviewer_quota literally returns this exact detail text
# ("timed out after 30s") on subprocess.TimeoutExpired. Never quota-recoverable: a hung/broken CLI
# invocation does not get better by waiting for quota to refill (HIGH finding).
_TIMEOUT_SIGNAL = "timed out"
# A malformed/missing command template -- ai_kit_spec.commands.render_reviewer_command's own
# ValueError text ("... has cli=... set but no command template" / "... has a malformed command
# template: ..."), confirmed by reading commands.py. A config problem, not a quota problem --
# waiting an hour never fixes a bad template (HIGH finding).
_CONFIGURATION_SIGNALS = ("command template", "no command builder registered",
                           "no execute-mode")
# The CLI binary itself could not be invoked at all -- quota.py's probe_reviewer_quota returns the
# raw OSError text verbatim on a failed subprocess launch (e.g. the binary isn't on PATH). Also
# never quota-recoverable (HIGH finding).
_DISPATCH_UNAVAILABLE_SIGNALS = ("no such file or directory", "command not found", "errno 2")


def reasons_summary(reasons: dict) -> dict:
    """Computes `all_auth_failures`/`any_quota_recoverable` over an ARBITRARY reasons dict --
    shared by QuotaExhaustedError's own properties (below, over `self.reasons`) and by cli.py's
    `resolve-injection` (CRITICAL finding, recurrence guard: a mid-dispatch re-resolution call's
    own QuotaExhaustedError only carries the tried/reasons IT visited this round; a candidate
    excluded earlier in the SAME wave -- via `--exclude-keys-json`, before this call's ladder walk
    even started -- never appears there at all, so a caller computing recoverability from `exc.
    reasons` alone silently drops every earlier wave-tried candidate's own reason. cli.py merges
    those earlier reasons in first (a new `--excluded-reasons-json` input) and recomputes the
    summary over the MERGED dict via this same function, so `any_quota_recoverable` reflects the
    whole wave, never just this call's own narrower remaining-ladder walk)."""
    return {
        "all_auth_failures": bool(reasons) and all(r == "auth" for r in reasons.values()),
        "any_quota_recoverable": any(r == "quota" for r in reasons.values()),
    }


class QuotaExhaustedError(RuntimeError):
    """Every candidate in the resolved ladder was quota-exhausted or had no usable dispatch
    mechanism for this task. `tried` carries every candidate key the walk actually visited, in
    ladder order, so a caller can persist the complete excluded set verbatim into resumable state
    (design spec Section 10, HIGH finding) -- never a bare string a caller has to re-parse.
    `reasons` maps each tried key to why it was skipped -- one of SIX typed reasons (HIGH finding:
    a real probe/dispatch failure has more shapes than "quota" vs "auth", and only one of them is
    ever worth an hourly wait):
      - "quota": a genuine, time-bound rate/usage-limit signal -- worth the hourly wake.
      - "auth": an authentication/entitlement/setup problem -- never fixed by waiting.
      - "timeout": the probe itself hung/timed out -- a broken invocation, not a rate limit.
      - "configuration": a missing/malformed command template -- a config problem.
      - "dispatch_unavailable": the CLI binary itself could not be invoked (OSError) --
        no registered execute-mode builder falls under this same umbrella via "no_usable_dispatch"
        below, which is set directly by build_dispatch_injection's own dispatchability check, not
        by _unavailability_reason.
      - "no_usable_dispatch": had quota, but build_execute_command_fn has no registered
        execute-mode builder for this candidate's cli (set directly by build_dispatch_injection,
        never by _unavailability_reason -- see the drop-and-continue branch below).
      - "real_error": anything else -- a real, non-time-bound failure (a bad model id, an
        unrelated nonzero exit) that must never be mistaken for a recoverable quota wait.
    `all_auth_failures` is True only when every entry in `reasons` is "auth" (kept for the
    original stop-and-ask-about-setup signal). `any_quota_recoverable` is the general HIGH-finding
    gate a caller now uses instead: True only when at least one entry in `reasons` is "quota" --
    the ONLY case where scheduling an hourly CronCreate wake accomplishes anything. If it's False,
    EVERY tried candidate failed for a reason waiting never fixes, and the caller must stop and
    report the real problem(s) instead of scheduling a futile wake."""

    def __init__(self, task_type, tried: list, reasons: dict | None = None):
        self.task_type = task_type
        self.tried = tried
        self.reasons = reasons or {}
        super().__init__(
            f"every resolved candidate for task_type={task_type!r} is unusable "
            f"(tried: {tried!r}, reasons: {self.reasons!r}) -- caller must persist resumable "
            f"state and, only if any_quota_recoverable, schedule a CronCreate quota re-check "
            f"rather than retry immediately"
        )

    @property
    def all_auth_failures(self) -> bool:
        return reasons_summary(self.reasons)["all_auth_failures"]

    @property
    def any_quota_recoverable(self) -> bool:
        """HIGH finding: the real gate for scheduling an hourly CronCreate wake. True only if at
        least one tried candidate's reason is "quota" -- a genuine, time-bound rate/usage limit.
        Every other reason (auth/timeout/configuration/dispatch_unavailable/no_usable_dispatch/
        real_error) never improves by waiting; if NONE of `reasons` is "quota", waiting an hour
        fixes nothing for any candidate, and the caller must stop and report the real problem(s)
        instead. Delegates to the shared reasons_summary (above) -- see its own docstring for why
        a caller merging reasons across more than one resolve-injection call must recompute this
        SAME summary over the merged dict rather than trust one call's own `.reasons` alone."""
        return reasons_summary(self.reasons)["any_quota_recoverable"]


def compute_resume_exclusions(tried: list, reasons: dict, prior_excluded_keys: list) -> list:
    """CRITICAL finding (recurrence guard): a persisted resumable-state `excluded_keys` set must
    NEVER permanently exclude a candidate whose only failure reason was "quota" -- once
    permanently excluded, a candidate can NEVER be retried again, even after quota genuinely
    recovers, which defeats the entire purpose of the hourly CronCreate wake this same exhaustion
    event schedules. This function is the single place that decides what belongs in a PERSISTED
    exclusion set: `prior_excluded_keys` (already permanent, carried forward unchanged) plus every
    key in `tried` whose reason is NOT "quota" (auth/timeout/configuration/dispatch_unavailable/
    no_usable_dispatch/real_error -- genuinely permanent, by construction of QuotaExhaustedError's
    own typed reasons above). A "quota" reason is deliberately DROPPED from the returned set, so
    the next resolve-injection call -- which always refreshes quota fresh -- gets a real chance to
    see that candidate recovered. Returns a sorted list (deterministic for a caller diffing/
    persisting it)."""
    permanent_new = {k for k in tried if reasons.get(k) != "quota"}
    return sorted(set(prior_excluded_keys) | permanent_new)


def assemble_candidates(cwd: str, env: dict, cfg_resolve_fn=cfg_resolve) -> tuple:
    """Reads the SAME shared candidate roster ai_kit_spec_gsd.adapter.assemble_candidates reads
    (review-spec.toml's [[reviewers]], design spec Section 4) -- the "superpowers has no config
    surface" constraint (Global Constraints) is about a superpowers-specific config file like
    GSD's .planning/config.json, which genuinely doesn't exist; it is not about this shared
    roster, which every ai-kit-spec-execute-* adapter reads identically. Duplicated here (not
    imported from ai_kit_spec_gsd.adapter) to keep the two sibling adapters independent -- neither
    should import the other's package. `task_affinity`/`context_limit` come back `None` for
    today's real ai-kit-spec-config output (Global Constraints) -- `.get()`, never `KeyError`."""
    resolved = cfg_resolve_fn(cwd, env)
    candidates = []
    for r in resolved.get("reviewers", []):
        if "key" not in r:
            continue
        candidates.append({
            "key": r["key"], "model": r.get("model", ""), "cli": r.get("cli"),
            "vendor": r.get("vendor", ""), "command": r.get("command"),
            "task_affinity": r.get("task_affinity"), "context_limit": r.get("context_limit"),
            "effort": r.get("effort"), "service_tier": r.get("service_tier"),
        })
    top_n_keys = resolved.get("policy", {}).get("ladder", [])
    return candidates, top_n_keys


_LINE_QUALIFIER = re.compile(r":\d+(?:-\d+)?$")


def _strip_line_qualifier(path: str) -> str:
    """CRITICAL finding: writing-plans' own standard task template (this plan's own Task
    Structure, `Modify: existing.py:123-145`) qualifies a Modify: path with a trailing line
    range -- that suffix is never part of a real filesystem path. Strips a trailing `:N` or
    `:N-M` ONLY for the purpose of resolving a real file on disk; the caller (derive_files_
    touched_sizes) keeps using the RAW, unstripped string as its own dict key, since
    estimate_required_context looks sizes up by extract_touched_paths' own raw output."""
    return _LINE_QUALIFIER.sub("", path)


def derive_files_touched_sizes(task_markdown: str, cwd: str, isfile_fn=os.path.isfile,
                                getsize_fn=os.path.getsize) -> dict:
    """The real {path: byte_size} map estimate_required_context needs (CRITICAL finding: context-
    size input was never populated end-to-end). Every path task_classification.extract_touched_
    paths finds is normalized via _strip_line_qualifier (CRITICAL finding: a writing-plans-style
    `existing.py:123-145` Modify: target never resolves to a real file without this -- isfile()
    on the raw, colon-suffixed string is always False, so every real Modify: target silently
    contributed 0 bytes and context-size filtering was inert for the framework's own standard
    task shape) before being joined against cwd and stat'd; a path that doesn't exist yet (a
    Create: target, which is never line-qualified in the first place) contributes 0 -- matches
    estimate_required_context's own "missing size counts as zero, never an error" contract
    exactly. The dict KEY returned is always the RAW (un-normalized) path, matching extract_
    touched_paths' own output verbatim -- only the on-disk lookup is normalized."""
    sizes = {}
    for path in extract_touched_paths(task_markdown):
        full_path = os.path.join(cwd, _strip_line_qualifier(path))
        sizes[path] = getsize_fn(full_path) if isfile_fn(full_path) else 0
    return sizes


def _has_quota(quota: dict, key: str) -> bool:
    """Mirrors ai_kit_spec.quota's own private _has_quota (no entry -> never probed -> assume
    available, never block resolution on the ABSENCE of quota data)."""
    entry = quota.get(key)
    if entry is None:
        return True
    return entry.get("available", True)


def _unavailability_reason(quota: dict, key: str) -> str:
    """Classifies why a quota-unavailable candidate is unavailable, from the SAME `detail` text
    quota.py's probe_reviewer_quota already records. HIGH finding (fixed this revision): the
    probe's own generic heuristic marks a candidate unavailable on ANY nonzero exit, a timeout, an
    OSError, or a malformed command template -- NOT only on a genuine rate/usage-limit signal --
    so this function must positively MATCH each typed reason from the real `detail` text rather
    than defaulting everything non-auth to "quota". Only a signal in _DISPATCH_QUOTA_SIGNALS ever
    returns "quota"; every other case returns its own typed reason, and an unmatched/ambiguous/
    empty detail returns "real_error" (never "quota") -- a false "quota" here would wrongly
    schedule an hourly CronCreate wake for a failure that will never improve by waiting, exactly
    the bug this finding closes."""
    detail = (quota.get(key) or {}).get("detail", "").lower()
    if any(signal in detail for signal in _AUTH_SIGNALS):
        return "auth"
    if any(signal in detail for signal in _DISPATCH_QUOTA_SIGNALS):
        return "quota"
    if _TIMEOUT_SIGNAL in detail:
        return "timeout"
    if any(signal in detail for signal in _CONFIGURATION_SIGNALS):
        return "configuration"
    if any(signal in detail for signal in _DISPATCH_UNAVAILABLE_SIGNALS):
        return "dispatch_unavailable"
    return "real_error"


# A non-empty sentinel ONLY for _is_dispatchable's own probe call below -- build_execute_command's
# real builders raise ValueError on an EMPTY target_dir (their own _require_target_dir guard, a
# separate, correct check that a write-capable dispatch never silently lands in the orchestrator's
# own cwd) unrelated to whether the cli has a registered builder at all. This sentinel exists only
# to get past that guard during registration-probing; the resulting command string is discarded
# immediately and NEVER reaches an actual dispatch -- the real target_dir is supplied later, at
# the moment of real dispatch, by dispatch_superpowers_task -> dispatch_execute (Global
# Constraints' "never a literal placeholder baked in ahead of time" rule governs THAT call, not
# this internal capability probe).
_PROBE_TARGET_DIR = "/__ai_kit_spec_execute_superpowers_dispatch_probe__"


def _is_dispatchable(candidate: dict, build_execute_command_fn) -> bool:
    """True for a native candidate (cli is None -- always executes in-process via the Agent
    tool). For ANY CLI-set candidate, including cli == "claude" (CRITICAL finding: only cli is
    None is a native Agent-tool alias -- "claude" is a real, subprocess-invoked entry with its
    own registered execute-mode builder, ai_kit_spec.commands._build_claude_execute_command, and
    must be probed/dispatched exactly like any other CLI), True only if build_execute_command_fn
    actually has a registered execute-mode builder for its cli (raises ValueError otherwise,
    design spec Section 12's "execute-mode builder not yet live-verified for a CLI: refuse ...
    never attempt an unverified invocation" rule) -- CRITICAL finding: this is what makes
    "usable-dispatch filtering" real instead of assumed."""
    cli = candidate.get("cli")
    if cli is None:
        return True
    try:
        build_execute_command_fn(cli, target_dir=_PROBE_TARGET_DIR, effort=candidate.get("effort"),
                                  service_tier=candidate.get("service_tier"))
        return True
    except ValueError:
        return False


def _narrow_and_rank(task_markdown: str, candidates: list, files_touched_sizes: dict,
                      affinity_table: dict, top_n_keys: list) -> tuple:
    """Shared by build_dispatch_injection and compute_ladder_keys (CRITICAL finding: the two
    must never compute the narrowed/ranked candidate order via two independently-drifting code
    paths) -- classifies the task, estimates required context, and narrows+ranks via
    resolve_execute_candidates. Returns (task_type, required_context, ranked)."""
    task_type = classify_task(task_markdown)
    required_context = estimate_required_context(task_markdown, files_touched_sizes)
    ranked = resolve_execute_candidates(
        candidates, task_type, required_context, affinity_table, top_n_keys)
    return task_type, required_context, ranked


def compute_ladder_keys(task_markdown: str, candidates: list, files_touched_sizes: dict,
                         affinity_table: dict, top_n_keys: list) -> list:
    """CRITICAL finding (Rounds 4-5 capability escalation): the FULL ordered candidate-key list
    -- via the SAME narrowing/ranking build_dispatch_injection itself walks (_narrow_and_rank,
    above) -- turned into keys via candidates_to_ladder. Deliberately NOT `list(top_n_keys)`: a
    candidate ranked here but absent from `top_n_keys` (policy.ladder's own configured keys)
    still gets a real, ordered (last-ranked) position, so a caller computing "every candidate
    ranked strictly above the stuck one" (Task 4's SKILL.md escalation rule) never silently misses
    an out-of-ladder candidate the live walk could actually have picked."""
    _, _, ranked = _narrow_and_rank(task_markdown, candidates, files_touched_sizes,
                                     affinity_table, top_n_keys)
    return candidates_to_ladder(ranked)


def build_dispatch_injection(task_markdown: str, candidates: list, files_touched_sizes: dict,
                              affinity_table: dict, top_n_keys: list, quota: dict | None = None,
                              resolve_ladder_pick_fn=resolve_ladder_pick,
                              build_execute_command_fn=build_execute_command) -> dict:
    task_type, required_context, ranked = _narrow_and_rank(
        task_markdown, candidates, files_touched_sizes, affinity_table, top_n_keys)
    if not ranked:
        raise ValueError(
            f"no execute candidate survived affinity/context narrowing for "
            f"task_type={task_type!r}, required_context={required_context} -- cannot build a "
            f"dispatch injection"
        )
    by_key = {c["key"]: c for c in ranked}
    remaining_ladder = candidates_to_ladder(ranked)
    quota = dict(quota or {})
    tried = []
    reasons = {}
    while remaining_ladder:
        pick = resolve_ladder_pick_fn(ranked, remaining_ladder, skip_vendor="", quota=quota)
        if pick is None:
            break  # nothing left in remaining_ladder currently has quota
        candidate = by_key[pick.key]
        if not _is_dispatchable(candidate, build_execute_command_fn):
            # Has quota, but no usable dispatch mechanism -- drop it and keep walking (CRITICAL
            # finding), same drop-and-continue shape ai_kit_spec_gsd.adapter.resolve_gsd_dispatch
            # already uses for its own equivalent case.
            tried.append(pick.key)
            reasons[pick.key] = "no_usable_dispatch"
            remaining_ladder = [k for k in remaining_ladder if k != pick.key]
            continue
        cli = candidate["cli"]
        # CRITICAL finding: only cli is None is a native Agent-tool alias. cli == "claude" is a
        # real, subprocess-invoked entry (ai_kit_spec.commands.py registers a real
        # (_EXECUTE, "claude") builder for it) -- it falls through to the external_cli branch
        # below like any other CLI-set entry, never silently treated as native.
        if cli is None:
            return {"mode": "native_claude", "model": candidate["model"], "key": candidate["key"]}
        return {
            "mode": "external_cli", "key": candidate["key"], "cli": cli,
            "model": candidate["model"], "effort": candidate.get("effort"),
            "service_tier": candidate.get("service_tier"),
        }
    # Nothing left in remaining_ladder currently has quota -- classify each one's own reason
    # (HIGH finding: distinguishes a real, time-bound quota wait from a futile auth retry) and
    # fold it into `tried` so the complete excluded set is what QuotaExhaustedError carries.
    for key in remaining_ladder:
        tried.append(key)
        reasons[key] = _unavailability_reason(quota, key)
    raise QuotaExhaustedError(task_type, tried, reasons)


def dispatch_superpowers_task(injection: dict, prompt: str, target_dir: str,
                               heartbeat_interval: int, timeout: int,
                               format_block: str | None = None,
                               tool_availability: dict | None = None, agents_tooling_path=None,
                               codegraph_registered: bool = False,
                               dispatch_execute_fn=dispatch_execute) -> dict:
    """The ONLY place a mode="external_cli" injection actually runs a subprocess. `target_dir` is
    a real, caller-supplied path at the moment of dispatch -- never resolved ahead of time and
    never a placeholder string (HIGH finding). Always routes through
    ai_kit_spec.execute_dispatch.dispatch_execute, which builds the real execute-mode command,
    composes the reinforcement/tooling/soft-confinement prose, and performs the real dispatch via
    dispatch_with_heartbeat -- this function adds no dispatch mechanics of its own."""
    if injection.get("mode") != "external_cli":
        raise ValueError(
            f"dispatch_superpowers_task is for mode='external_cli' injections only -- got "
            f"mode={injection.get('mode')!r}; a native_claude injection dispatches via the "
            f"Agent tool directly, in-process, and never reaches this function"
        )
    candidate = {"cli": injection["cli"], "model": injection["model"],
                 "effort": injection.get("effort"), "service_tier": injection.get("service_tier")}
    return dispatch_execute_fn(
        candidate, prompt, target_dir, heartbeat_interval, timeout, format_block=format_block,
        tool_availability=tool_availability, agents_tooling_path=agents_tooling_path,
        codegraph_registered=codegraph_registered,
    )


def classify_dispatch_failure(dispatch_result: dict) -> str:
    """Classifies a completed dispatch_superpowers_task result: "ok" (returncode 0), "quota"
    (nonzero returncode + a genuine rate/usage-limit signal in combined stdout+stderr -- retry
    with the next ladder candidate, never this same one), or "real_error" (anything else,
    including a timeout regardless of its own text, AND an auth/entitlement/setup signal --
    HIGH finding: those never get better by waiting, so they must never come back "quota" and
    trigger the caller's hourly CronCreate wake loop -- surfaced honestly to the harness's own
    BLOCKED/fix-loop path instead, design spec Section 12's explicit "never silently retry
    disguised as quota-wait" rule)."""
    if dispatch_result.get("timed_out"):
        return "real_error"
    returncode = dispatch_result.get("returncode", 0)
    if returncode == 0:
        return "ok"
    combined = (dispatch_result.get("stdout", "") + dispatch_result.get("stderr", "")).lower()
    if any(signal in combined for signal in _AUTH_SIGNALS):
        return "real_error"
    if any(signal in combined for signal in _DISPATCH_QUOTA_SIGNALS):
        return "quota"
    return "real_error"
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec_superpowers.TestAssembleCandidates \
  tests.test_ai_kit_spec_superpowers.TestDeriveFilesTouchedSizes \
  tests.test_ai_kit_spec_superpowers.TestComputeLadderKeys \
  tests.test_ai_kit_spec_superpowers.TestBuildDispatchInjection \
  tests.test_ai_kit_spec_superpowers.TestReasonsSummary \
  tests.test_ai_kit_spec_superpowers.TestComputeResumeExclusions \
  tests.test_ai_kit_spec_superpowers.TestDispatchSuperpowersTask \
  tests.test_ai_kit_spec_superpowers.TestClassifyDispatchFailure -v 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py \
        tests/test_ai_kit_spec_superpowers.py
git commit -m "feat(ai-kit-spec-execute-superpowers): add dispatch_injection.py"
```

---

### Task 3: `cli.py` — the executable integration point

**Files:**
- Create: `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py`
- Create: `skills/ai-kit-spec-execute-superpowers/ai-kit-spec-superpowers.py`
- Test: `tests/test_ai_kit_spec_superpowers.py` (append)

**Interfaces:**
- Consumes: `dispatch_injection.assemble_candidates`/`build_dispatch_injection`/`derive_files_touched_sizes`/`compute_ladder_keys`/`reasons_summary`/`dispatch_superpowers_task`/`classify_dispatch_failure`/`QuotaExhaustedError` (Task 2); `ai_kit_spec.cache.cache_read_json`/`cache_write_json`, `ai_kit_spec.quota.QUOTA_TTL_SECONDS`/`refresh_quota_cache`, `ai_kit_spec.detection.detect_tool_availability`/`resolve_agents_tooling_path`/`ensure_codegraph_registered`/`build_codegraph_index_command`/`CODEGRAPH_INDEX_TIMEOUT_SECONDS`, `ai_kit_spec.dispatch.write_resumable_state` (all Plan 1).
- Produces: `main(argv, ...) -> int`, one subcommand per operation Task 4's SKILL.md invokes via `Bash`: `resolve-injection`, `dispatch-task`, `classify-dispatch-failure`, `resume-exclusions`, `write-resumable-state`. Mirrors `ai_kit_spec_gsd.cli`'s own subcommand pattern (same shim/argparse shape) so an executing agent gets one concrete, runnable command for every operation — there is deliberately no `native_claude` dispatch subcommand: that mode is dispatched in-process via the `Agent` tool by Task 4's SKILL.md directly, never subprocess-invoked here. **No separate `prepare-tooling` subcommand** (removed this revision — CRITICAL finding): `dispatch-task` already computes `tool_availability`/`agents_tooling_path`/`codegraph_registered` itself and hands them straight to `dispatch_superpowers_task_fn`, which passes them into `dispatch_execute` (Task 2/Plan 1) to compose the tooling-guidance section of the real dispatched prompt — a standalone tooling-guidance subcommand whose output nothing ever read would have been dead code duplicating that same computation.
  - `resolve-injection` derives `files_touched_sizes` itself, via `dispatch_injection.derive_files_touched_sizes(task_markdown, args.cwd)` — CRITICAL finding: the caller (Task 4's SKILL.md) never had real file sizes to pass, so context-size filtering was silently inert; deriving it inside the subcommand, from the same `--cwd`/`--task-file` the caller already supplies, makes it real without adding a manual step the SKILL.md would have to get right.
  - `resolve-injection`'s `quota_exhausted` JSON output carries `reasons`, `all_auth_failures`, and `any_quota_recoverable` straight from `QuotaExhaustedError` (HIGH finding) — Task 4's SKILL.md reads `any_quota_recoverable` to decide whether this is a real, time-bound wait (schedule the hourly `CronCreate` wake) or an unfixable-by-waiting problem — auth, timeout, configuration, dispatch-unavailable, or another real error (surface `reasons` verbatim as an actionable error instead, never wake-and-retry).
  - `resolve-injection`'s JSON output carries `ladder_keys` on EVERY branch (`native_claude`, `external_cli`, AND `quota_exhausted`) — CRITICAL finding: computed via `dispatch_injection.compute_ladder_keys` over the FULL, pre-exclusion candidate roster (never `list(top_n_keys)`, a prior revision's incomplete proxy that silently omitted any candidate outside `policy.ladder`). Task 4's SKILL.md uses this to implement `subagent-driven-development`'s own "Rounds 4-5: dispatch a fresh implementer on a more capable model" contract for `external_cli` mode — only a candidate ranked strictly above the stuck one in `ladder_keys` counts as a real capability bump, never a same-or-lower-ranked fallback the plain ladder-exclusion walk could otherwise silently pick, and `ladder_keys` now genuinely includes every candidate the live walk could actually reach.
  - **`resolve-injection` takes a SEPARATE `--escalation-excluded-keys-json` argument (default `"[]"`), distinct from `--exclude-keys-json` — HIGH finding, recurrence guard.** Both narrow the candidate pool identically, but only `--exclude-keys-json` members can ever receive a reason: `--escalation-excluded-keys-json` members are healthy, never-attempted candidates dropped purely to enforce Task 4's SKILL.md Rounds 4–5 capability-bump floor, and they never enter the emitted `tried`/`reasons` — no `"no_usable_dispatch"` fallback, no permanent-shaped reason, nothing for `resume-exclusions` to later carry into persisted `excluded_keys`, and nothing for the "which candidates need a fix" user-facing report to name. Without this separation, a capability-escalation-only exclusion fed through the same channel as a real failure would be permanently blacklisted the same way a genuine quota/auth/timeout failure is — even though it was never tried.
  - **`resolve-injection` never lets an exhausted-by-exclusion wave crash with an uncaught `ValueError` — CRITICAL finding.** Before calling `build_dispatch_injection_fn` at all, it checks whether `--exclude-keys-json` filtered `candidates` down to an EMPTY list (every configured candidate for this task already excluded — a single-candidate ladder tried once, or several waves' accumulated exclusions covering the whole roster). `build_dispatch_injection_fn` cannot tell that apart from a genuine curation gap (its own `ValueError` is for "nothing configured for this task type at all", never for "we already tried everything") — so `resolve-injection` short-circuits to a controlled `quota_exhausted` response itself in that case, using a NEW `--excluded-reasons-json` input (default `"{}"`, a `{key: reason}` map for every key already in `--exclude-keys-json`, supplied by Task 4's SKILL.md from its own accumulated `$WAVE_REASONS_JSON`) to preserve WHY each already-excluded key failed, rather than fabricating a reason or losing it. The same `--excluded-reasons-json` merge also fixes a second bug in the non-empty-candidates case: a `QuotaExhaustedError` raised by `build_dispatch_injection_fn` only carries `tried`/`reasons` for candidates its OWN walk visited this call — never a key `--exclude-keys-json` had already dropped before the walk started — so `resolve-injection` merges `--excluded-reasons-json` into the exception's own `reasons` (any key in `--exclude-keys-json` still missing a reason after that merge gets `"no_usable_dispatch"`, a permanent-shaped fallback that can never be mistaken for a `"quota"` reason) and recomputes `all_auth_failures`/`any_quota_recoverable` via `dispatch_injection.reasons_summary` over the MERGED dict — never the exception's own narrower properties — so recoverability reflects the whole wave, not just this one call's remaining-ladder walk.
  - **`resolve-injection` also catches `build_dispatch_injection_fn`'s OWN `ValueError` on the one reachable path where `candidates` is non-empty but narrowing still drops every candidate (HIGH finding)** — e.g. every remaining candidate's `context_limit` is below this task's `required_context`, leaving `ranked` empty. That is a distinct, genuine curation gap ("nothing configured can run this task," never "we already tried everything" — the empty-`candidates`-by-exclusion case above), so it is reported as its own `"no_candidate"` mode (`task_type`, `detail` — the exception's own message — and `ladder_keys`), never folded into `"quota_exhausted"`, which would wrongly imply an hourly `CronCreate` wake could ever fix it.
  - `dispatch-task` takes `--report-mode {write,append}` (default `write`) — CRITICAL finding: the first dispatch of a task WRITES the report file (nothing to preserve yet), but every fix-loop round must APPEND to it, never overwrite it, or `subagent-driven-development`'s own "every round... appends its fix report to the same report file" contract (the harness's persistent memory for `external_cli` tasks, since there's no live subagent to hold context) silently loses every earlier round's evidence. **`dispatch-task` never overwrites an implementer-authored report file with captured subprocess stdout (CRITICAL finding, recurrence guard)** — it snapshots `--report-file`'s content before dispatching and again after; if the dispatched CLI wrote its own report directly to that path (the real superpowers implementer contract: detailed evidence to the report file, a short status separately), the file is left completely untouched. Only when the file is provably unchanged (the CLI never wrote to it) does `dispatch-task` fall back to writing/appending the captured stdout, and even then with a leading `[ai-kit-spec-execute-superpowers: no report file was written by the dispatched CLI -- falling back to captured stdout]` marker so a fallback report is never mistaken for a genuine one.
  - `resume-exclusions` (new subcommand, CRITICAL finding, recurrence guard) — thin CLI wrapper around `dispatch_injection.compute_resume_exclusions`; takes `--tried-json`, `--reasons-json`, `--prior-excluded-keys-json`, prints the resulting exclusion list as JSON. Task 4's SKILL.md calls this (instead of hand-rolled, untested inline `python3 -c` set arithmetic) whenever it persists a resumable-state `excluded_keys` set, so a genuinely time-bound `"quota"` reason is never turned into a permanent exclusion.

- [ ] **Step 1: Write the failing tests**

```python
import io
import json

from ai_kit_spec_superpowers import cli as superpowers_cli


class TestCliResolveInjection(unittest.TestCase):
    def test_resolve_injection_prints_native_claude_json(self):
        candidates = [{"key": "claude/opus-5", "model": "opus", "cli": None,
                        "vendor": "anthropic", "task_affinity": None, "context_limit": None}]

        def fake_assemble(cwd, env):
            return candidates, ["claude/opus-5"]

        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                 "--quota-path", quota_path],
                assemble_candidates_fn=fake_assemble,
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, ttl: {},
                stdout=out)
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result, {"mode": "native_claude", "model": "opus",
                                   "key": "claude/opus-5",
                                   "ladder_keys": ["claude/opus-5"]})

    def test_resolve_injection_prints_quota_exhausted_json_with_reasons(self):
        candidates = [{"key": "claude/opus-5", "model": "opus", "cli": None,
                        "vendor": "anthropic", "task_affinity": None, "context_limit": None}]

        def fake_assemble(cwd, env):
            return candidates, ["claude/opus-5"]

        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                 "--quota-path", quota_path],
                assemble_candidates_fn=fake_assemble,
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, ttl: (
                    {"claude/opus-5": {"available": False, "detail": "usage limit reached"}}),
                stdout=out)
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["mode"], "quota_exhausted")
        self.assertEqual(result["tried"], ["claude/opus-5"])
        self.assertEqual(result["reasons"], {"claude/opus-5": "quota"})
        self.assertFalse(result["all_auth_failures"])
        # HIGH finding: any_quota_recoverable, not all_auth_failures, is the real gate Task 4's
        # SKILL.md now uses to decide whether an hourly CronCreate wake accomplishes anything.
        self.assertTrue(result["any_quota_recoverable"])
        # CRITICAL finding (Rounds 4-5 capability escalation): ladder_keys must be present even on
        # the quota_exhausted branch -- Step 2's own resumable-state persistence path is exactly
        # where a struggling candidate is first discovered, and Step 3's mid-dispatch "quota"
        # branch reads this same field shape.
        self.assertEqual(result["ladder_keys"], ["claude/opus-5"])

    def test_resolve_injection_derives_real_file_sizes_from_cwd(self):
        # CRITICAL finding: resolve-injection must derive files_touched_sizes itself (never rely
        # on a caller-supplied, always-empty default) so context-size filtering is actually live.
        candidates = [{"key": "claude/opus-5", "model": "opus", "cli": None,
                        "vendor": "anthropic", "task_affinity": None, "context_limit": None}]
        captured = {}

        def fake_build_dispatch_injection(task_markdown, cands, sizes, affinity, top_n, **kwargs):
            captured["sizes"] = sizes
            return {"mode": "native_claude", "model": "opus", "key": "claude/opus-5"}

        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "big.py"), "w") as f:
                f.write("x" * 4000)
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Modify: `big.py`\n")
            quota_path = os.path.join(tmp, "quota.json")
            superpowers_cli.main(
                ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                 "--quota-path", quota_path],
                assemble_candidates_fn=lambda cwd, env: (candidates, ["claude/opus-5"]),
                build_dispatch_injection_fn=fake_build_dispatch_injection,
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, ttl: {},
                stdout=io.StringIO())
        self.assertEqual(captured["sizes"], {"big.py": 4000})

    def test_resolve_injection_emits_controlled_quota_exhausted_when_every_candidate_already_excluded(self):
        # CRITICAL finding: a single-candidate ladder, already excluded by --exclude-keys-json
        # (e.g. a mid-dispatch "quota" failure caught in Step 3, re-running resolve-injection with
        # that SAME candidate excluded) previously reached build_dispatch_injection_fn with an
        # EMPTY candidates list, which raised its own "no candidate survived narrowing" ValueError
        # -- the WRONG exception (a real curation-gap signal, never "we already tried everything")
        # -- UNCAUGHT here, crashing the whole resolve-injection call instead of reporting a
        # controlled quota_exhausted result the SKILL.md's own branch-on-mode logic already
        # handles. --excluded-reasons-json carries this wave's own already-known reason forward.
        candidates = [{"key": "claude/opus-5", "model": "opus", "cli": None,
                        "vendor": "anthropic", "task_affinity": None, "context_limit": None}]
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                 "--quota-path", quota_path, "--exclude-keys-json",
                 json.dumps(["claude/opus-5"]), "--excluded-reasons-json",
                 json.dumps({"claude/opus-5": "quota"})],
                assemble_candidates_fn=lambda cwd, env: (candidates, ["claude/opus-5"]),
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, ttl: {},
                stdout=out)
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["mode"], "quota_exhausted")
        self.assertEqual(result["tried"], ["claude/opus-5"])
        self.assertEqual(result["reasons"], {"claude/opus-5": "quota"})
        self.assertTrue(result["any_quota_recoverable"])
        self.assertEqual(result["ladder_keys"], ["claude/opus-5"])

    def test_resolve_injection_reports_no_candidate_when_narrowing_drops_every_candidate(self):
        # HIGH finding: `candidates` is non-empty here (never excluded down to empty -- that's the
        # separate "every configured candidate already excluded" case above) but every one gets
        # dropped by affinity/context narrowing itself (a context_limit below this task's
        # required_context) -- build_dispatch_injection_fn's own "no candidate survived narrowing"
        # ValueError, previously uncaught, must never crash this command. It is a genuine curation
        # gap, never a quota-availability problem, so it gets its own "no_candidate" mode -- never
        # folded into "quota_exhausted", which would wrongly imply a CronCreate wake could help.
        candidates = [{"key": "small-context/model", "model": "opus", "cli": None,
                        "vendor": "anthropic", "task_affinity": None, "context_limit": 10}]
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "big.py"), "w") as f:
                f.write("x" * 4000)
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Modify: `big.py`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                 "--quota-path", quota_path],
                assemble_candidates_fn=lambda cwd, env: (candidates, ["small-context/model"]),
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, ttl: {},
                stdout=out)
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["mode"], "no_candidate")
        self.assertIn("no execute candidate survived", result["detail"])
        # ladder_keys is computed via the SAME affinity/context narrowing (compute_ladder_keys
        # shares _narrow_and_rank with build_dispatch_injection) -- the one candidate that failed
        # context narrowing for the dispatch call fails it here too, so the full ranked ladder is
        # also empty. This is consistent, not a second bug: ladder_keys never claims a candidate
        # narrowing already rejected is somehow still ranked.
        self.assertEqual(result["ladder_keys"], [])

    def test_resolve_injection_merges_wave_excluded_reasons_with_this_calls_own_quota_exhaustion(self):
        # CRITICAL finding: mixed quota/auth case -- a caller re-resolving mid-wave (one candidate
        # already excluded for a KNOWN reason from an earlier call, another going quota-exhausted
        # fresh THIS call) must see BOTH reasons in the final output, never just this call's own
        # narrower remaining-ladder walk (which never even visits an already-excluded candidate).
        candidates = [
            {"key": "claude/opus-5", "model": "opus", "cli": None, "vendor": "anthropic",
             "task_affinity": None, "context_limit": None},
            {"key": "codex/terra", "model": "gpt-5.6-terra", "cli": "codex", "vendor": "openai",
             "task_affinity": None, "context_limit": None},
        ]
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                 "--quota-path", quota_path, "--exclude-keys-json",
                 json.dumps(["codex/terra"]), "--excluded-reasons-json",
                 json.dumps({"codex/terra": "auth"})],
                assemble_candidates_fn=lambda cwd, env: (
                    candidates, ["claude/opus-5", "codex/terra"]),
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, ttl: (
                    {"claude/opus-5": {"available": False, "detail": "usage limit reached"}}),
                stdout=out)
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["mode"], "quota_exhausted")
        self.assertEqual(result["reasons"], {"claude/opus-5": "quota", "codex/terra": "auth"})
        self.assertEqual(sorted(result["tried"]), ["claude/opus-5", "codex/terra"])
        self.assertTrue(result["any_quota_recoverable"])
        self.assertFalse(result["all_auth_failures"])
        self.assertEqual(result["ladder_keys"], ["claude/opus-5", "codex/terra"])

    def test_escalation_excluded_keys_never_get_a_reason_or_enter_tried(self):
        # HIGH finding: a Rounds 4-5 capability-escalation exclusion is a healthy, NEVER-tried
        # candidate dropped purely for ranking reasons -- it must never receive the
        # "no_usable_dispatch" permanent-shaped fallback reason, must never appear in `tried`, and
        # must never be counted toward any_quota_recoverable/all_auth_failures -- distinct from a
        # genuine --exclude-keys-json member, which DOES get all of that. Here every real
        # candidate is quota-exhausted (a real, recoverable reason) while one candidate is excluded
        # ONLY via --escalation-excluded-keys-json.
        candidates = [
            {"key": "claude/opus-5", "model": "opus", "cli": None, "vendor": "anthropic",
             "task_affinity": None, "context_limit": None},
            {"key": "codex/terra", "model": "gpt-5.6-terra", "cli": "codex", "vendor": "openai",
             "task_affinity": None, "context_limit": None},
        ]
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            task_file = os.path.join(tmp, "task-1-brief.md")
            with open(task_file, "w") as f:
                f.write("### Task 1\n**Files:**\n- Create: `README.md`\n")
            quota_path = os.path.join(tmp, "quota.json")
            rc = superpowers_cli.main(
                ["resolve-injection", "--cwd", tmp, "--task-file", task_file,
                 "--quota-path", quota_path, "--exclude-keys-json", json.dumps(["codex/terra"]),
                 "--excluded-reasons-json", json.dumps({"codex/terra": "quota"}),
                 "--escalation-excluded-keys-json", json.dumps(["claude/opus-5"])],
                assemble_candidates_fn=lambda cwd, env: (
                    candidates, ["claude/opus-5", "codex/terra"]),
                cache_read_json_fn=lambda path: {},
                cache_write_json_fn=lambda path, data: None,
                refresh_quota_cache_fn=lambda config, keys, existing, ttl: {},
                stdout=out)
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["mode"], "quota_exhausted")
        # claude/opus-5 was excluded ONLY for capability-escalation reasons -- it must be absent
        # from both `tried` and `reasons` entirely, never defaulted to "no_usable_dispatch".
        self.assertEqual(result["tried"], ["codex/terra"])
        self.assertEqual(result["reasons"], {"codex/terra": "quota"})
        self.assertTrue(result["any_quota_recoverable"])


class TestCliDispatchTask(unittest.TestCase):
    def test_preserves_implementer_authored_report_when_the_cli_writes_it_directly(self):
        # CRITICAL finding (recurrence -- a prior revision's fix attempt did not close every
        # path): the real superpowers implementer contract has the dispatched CLI write its OWN
        # detailed report directly to --report-file (it has write access to target_dir, being an
        # execute-mode dispatch) and return only a SHORT status separately (design spec's own
        # "writes detailed evidence to the report file and returns a short status separately").
        # dispatch-task must never overwrite that real, on-disk report with captured subprocess
        # stdout -- this is the normal case, and it must be left completely untouched.
        injection = {"mode": "external_cli", "key": "codex/terra", "cli": "codex",
                      "model": "gpt-5.6-terra", "effort": None, "service_tier": None}

        def fake_dispatch(injection_arg, prompt, target_dir, heartbeat_interval, timeout,
                           format_block=None, tool_availability=None, agents_tooling_path=None,
                           codegraph_registered=False):
            # Simulates the real dispatched CLI: per the prompt's report-file-path instruction, it
            # writes its OWN detailed report directly to disk and returns only a short status in
            # stdout -- exactly the contract this test guards.
            report_path = os.path.join(target_dir, "task-1-report.md")
            with open(report_path, "w") as f:
                f.write("## TDD Evidence\n\nfull detailed report with real test output...\n")
            return {"cli": "codex", "model": "gpt-5.6-terra", "command": "codex exec ...",
                     "returncode": 0, "stdout": "DONE", "stderr": "", "timed_out": False}

        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            prompt_file = os.path.join(tmp, "prompt.txt")
            with open(prompt_file, "w") as f:
                f.write("do the task")
            format_block_file = os.path.join(tmp, "format.md")
            with open(format_block_file, "w") as f:
                f.write("status: DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED")
            report_file = os.path.join(tmp, "task-1-report.md")
            rc = superpowers_cli.main(
                ["dispatch-task", "--injection-json", json.dumps(injection),
                 "--prompt-file", prompt_file, "--target-dir", tmp,
                 "--heartbeat-interval", "60", "--timeout", "900",
                 "--format-block-file", format_block_file, "--report-file", report_file],
                dispatch_superpowers_task_fn=fake_dispatch,
                detect_tool_availability_fn=lambda: {},
                resolve_agents_tooling_path_fn=lambda: None,
                ensure_codegraph_registered_fn=lambda cli: False,
                stdout=out)
        self.assertEqual(rc, 0)
        with open(report_file) as f:
            content = f.read()
        # The implementer's own detailed, on-disk report survives verbatim -- the short "DONE"
        # status returned separately in stdout must NEVER have replaced it.
        self.assertEqual(content, "## TDD Evidence\n\nfull detailed report with real test "
                                   "output...\n")
        self.assertNotIn("DONE", content)
        result = json.loads(out.getvalue())
        self.assertEqual(result["returncode"], 0)

    def test_falls_back_to_labeled_stdout_only_when_the_cli_never_wrote_its_own_report(self):
        # Degraded case: the dispatched CLI did not follow the report-file-path instruction and
        # wrote nothing to disk -- something evidentiary must still survive, but clearly labeled
        # as a fallback, never silently indistinguishable from a genuine implementer report.
        injection = {"mode": "external_cli", "key": "codex/terra", "cli": "codex",
                      "model": "gpt-5.6-terra", "effort": None, "service_tier": None}

        def fake_dispatch(injection_arg, prompt, target_dir, heartbeat_interval, timeout,
                           format_block=None, tool_availability=None, agents_tooling_path=None,
                           codegraph_registered=False):
            return {"cli": "codex", "model": "gpt-5.6-terra", "command": "codex exec ...",
                     "returncode": 0, "stdout": "DONE\nonly stdout, no report file written",
                     "stderr": "", "timed_out": False}

        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            prompt_file = os.path.join(tmp, "prompt.txt")
            with open(prompt_file, "w") as f:
                f.write("do the task")
            format_block_file = os.path.join(tmp, "format.md")
            with open(format_block_file, "w") as f:
                f.write("status: DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED")
            report_file = os.path.join(tmp, "task-1-report.md")
            rc = superpowers_cli.main(
                ["dispatch-task", "--injection-json", json.dumps(injection),
                 "--prompt-file", prompt_file, "--target-dir", tmp,
                 "--heartbeat-interval", "60", "--timeout", "900",
                 "--format-block-file", format_block_file, "--report-file", report_file],
                dispatch_superpowers_task_fn=fake_dispatch,
                detect_tool_availability_fn=lambda: {},
                resolve_agents_tooling_path_fn=lambda: None,
                ensure_codegraph_registered_fn=lambda cli: False,
                stdout=out)
        self.assertEqual(rc, 0)
        with open(report_file) as f:
            content = f.read()
        self.assertIn("no report file was written", content)
        self.assertIn("only stdout, no report file written", content)

    def test_report_mode_append_preserves_the_prior_rounds_report_in_the_fallback_case(self):
        # CRITICAL finding: a fix-loop round must APPEND to the existing report file, never
        # overwrite it -- subagent-driven-development's own "every round... appends its fix
        # report to the same report file" contract is the harness's persistent memory for an
        # external_cli task (there's no live subagent to hold context between rounds). Exercises
        # the STDOUT-fallback branch specifically (the dispatched CLI here does not write its own
        # report directly) -- even the degraded fallback must never destroy earlier rounds.
        injection = {"mode": "external_cli", "key": "codex/terra", "cli": "codex",
                      "model": "gpt-5.6-terra", "effort": None, "service_tier": None}

        def fake_dispatch(injection_arg, prompt, target_dir, heartbeat_interval, timeout,
                           format_block=None, tool_availability=None, agents_tooling_path=None,
                           codegraph_registered=False):
            return {"cli": "codex", "model": "gpt-5.6-terra", "command": "codex exec ...",
                     "returncode": 0, "stdout": "fix round 1 report", "stderr": "",
                     "timed_out": False}

        with tempfile.TemporaryDirectory() as tmp:
            prompt_file = os.path.join(tmp, "prompt.txt")
            with open(prompt_file, "w") as f:
                f.write("fix it")
            format_block_file = os.path.join(tmp, "format.md")
            with open(format_block_file, "w") as f:
                f.write("status: DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED")
            report_file = os.path.join(tmp, "task-1-report.md")
            with open(report_file, "w") as f:
                f.write("original implementer report")
            rc = superpowers_cli.main(
                ["dispatch-task", "--injection-json", json.dumps(injection),
                 "--prompt-file", prompt_file, "--target-dir", tmp,
                 "--heartbeat-interval", "60", "--timeout", "900",
                 "--format-block-file", format_block_file, "--report-file", report_file,
                 "--report-mode", "append"],
                dispatch_superpowers_task_fn=fake_dispatch,
                detect_tool_availability_fn=lambda: {},
                resolve_agents_tooling_path_fn=lambda: None,
                ensure_codegraph_registered_fn=lambda cli: False,
                stdout=io.StringIO())
            self.assertEqual(rc, 0)
            with open(report_file) as f:
                content = f.read()
        self.assertIn("original implementer report", content)
        self.assertIn("fix round 1 report", content)


class TestCliClassifyDispatchFailure(unittest.TestCase):
    def test_prints_the_classification_string(self):
        out = io.StringIO()
        result = {"returncode": 1, "stdout": "usage limit reached", "stderr": "",
                  "timed_out": False}
        rc = superpowers_cli.main(
            ["classify-dispatch-failure", "--dispatch-result-json", json.dumps(result)],
            stdout=out)
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue(), "quota")


class TestCliResumeExclusions(unittest.TestCase):
    def test_prints_only_permanent_exclusions(self):
        # CRITICAL finding: the executable subcommand SKILL.md's resume/wake path calls -- proves
        # the reason-based split (quota dropped, everything else kept) is real and testable, not
        # just inline, untested bash arithmetic.
        out = io.StringIO()
        rc = superpowers_cli.main(
            ["resume-exclusions",
             "--tried-json", json.dumps(["claude/opus-5", "codex/terra"]),
             "--reasons-json", json.dumps({"claude/opus-5": "quota", "codex/terra": "auth"}),
             "--prior-excluded-keys-json", json.dumps([])],
            stdout=out)
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.getvalue()), ["codex/terra"])


class TestCliWriteResumableState(unittest.TestCase):
    def test_writes_state_and_confirms(self):
        out = io.StringIO()
        captured = {}
        rc = superpowers_cli.main(
            ["write-resumable-state", "--path", "/x/state.json",
             "--state-json", json.dumps({"framework": "superpowers", "tried": []})],
            write_resumable_state_fn=lambda path, state: captured.update(path=path, state=state),
            stdout=out)
        self.assertEqual(rc, 0)
        self.assertEqual(captured["path"], "/x/state.json")
        self.assertEqual(json.loads(out.getvalue())["written"], True)
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_superpowers.TestCliResolveInjection \
  tests.test_ai_kit_spec_superpowers.TestCliDispatchTask \
  tests.test_ai_kit_spec_superpowers.TestCliClassifyDispatchFailure \
  tests.test_ai_kit_spec_superpowers.TestCliResumeExclusions \
  tests.test_ai_kit_spec_superpowers.TestCliWriteResumableState -v 2>&1 | tail -20
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""CLI entrypoint for ai-kit-spec-execute-superpowers -- invoked via the
ai-kit-spec-superpowers.py shim. Mirrors ai_kit_spec_gsd.cli's own subcommand pattern (Plan 2) so
Task 4's SKILL.md gives an executing agent one concrete, runnable command for every operation:
resolve-injection (live-quota candidate resolution), dispatch-task (the actual write-capable
dispatch, which preserves an implementer-authored report file rather than overwriting it with
stdout -- CRITICAL finding), classify-dispatch-failure, resume-exclusions (computes what's safe
to PERSIST as a resumable-state exclusion set without permanently excluding a merely
quota-exhausted candidate -- CRITICAL finding), write-resumable-state. There is no native_claude
dispatch subcommand -- that mode is dispatched in-process via the Agent tool, by Task 4's
SKILL.md directly, never subprocess-invoked here (same native/cross-AI split ai_kit_spec_gsd.cli
already uses). No separate prepare-tooling subcommand either (removed a prior revision, CRITICAL
finding) -- dispatch-task already computes and passes tooling guidance inputs itself; a
standalone subcommand whose output nothing read was dead code invoking a subcommand that never
actually existed."""
import argparse
import json
import os
import subprocess
import sys

from ai_kit_spec.cache import cache_read_json, cache_write_json
from ai_kit_spec.detection import (
    CODEGRAPH_INDEX_TIMEOUT_SECONDS,
    build_codegraph_index_command,
    detect_tool_availability,
    ensure_codegraph_registered,
    resolve_agents_tooling_path,
)
from ai_kit_spec.dispatch import write_resumable_state as _write_resumable_state_default
from ai_kit_spec.quota import QUOTA_TTL_SECONDS, refresh_quota_cache

from ai_kit_spec_superpowers.dispatch_injection import (
    QuotaExhaustedError,
    assemble_candidates,
    build_dispatch_injection,
    classify_dispatch_failure,
    classify_task,
    compute_ladder_keys,
    compute_resume_exclusions,
    derive_files_touched_sizes,
    dispatch_superpowers_task,
    reasons_summary,
)

# Prefixes a fallback report so it is never mistaken for a genuine implementer-authored one
# (CRITICAL finding, recurrence guard).
_REPORT_FALLBACK_MARKER = (
    "[ai-kit-spec-execute-superpowers: no report file was written by the dispatched CLI -- "
    "falling back to captured stdout]\n\n"
)


def main(argv: list, assemble_candidates_fn=assemble_candidates,
         build_dispatch_injection_fn=build_dispatch_injection,
         derive_files_touched_sizes_fn=derive_files_touched_sizes,
         compute_ladder_keys_fn=compute_ladder_keys, reasons_summary_fn=reasons_summary,
         classify_task_fn=classify_task,
         dispatch_superpowers_task_fn=dispatch_superpowers_task,
         classify_dispatch_failure_fn=classify_dispatch_failure,
         compute_resume_exclusions_fn=compute_resume_exclusions,
         cache_read_json_fn=cache_read_json, cache_write_json_fn=cache_write_json,
         refresh_quota_cache_fn=refresh_quota_cache,
         detect_tool_availability_fn=detect_tool_availability,
         resolve_agents_tooling_path_fn=resolve_agents_tooling_path,
         ensure_codegraph_registered_fn=ensure_codegraph_registered,
         build_codegraph_index_command_fn=build_codegraph_index_command,
         run_fn=subprocess.run, write_resumable_state_fn=_write_resumable_state_default,
         stdout=sys.stdout) -> int:
    parser = argparse.ArgumentParser(prog="ai-kit-spec-execute-superpowers")
    sub = parser.add_subparsers(dest="command", required=True)

    p_resolve = sub.add_parser("resolve-injection")
    p_resolve.add_argument("--cwd", required=True)
    p_resolve.add_argument("--task-file", required=True,
                            help="path to this task's own brief file (task-N-brief.md, per "
                                 "subagent-driven-development's own scripts/task-brief) -- read "
                                 "verbatim as task_markdown; files_touched_sizes is derived from "
                                 "this SAME file's own **Files:** block, stat'd against --cwd -- "
                                 "never a caller-supplied manual map (CRITICAL finding)")
    p_resolve.add_argument("--quota-path", required=True)
    p_resolve.add_argument("--exclude-keys-json", default="[]",
                            help="candidate keys to drop before resolution -- e.g. a key already "
                                 "confirmed quota-exhausted earlier in the same wave")
    p_resolve.add_argument(
        "--excluded-reasons-json", default="{}",
        help="CRITICAL finding, recurrence guard: a {key: reason} map for every key already in "
             "--exclude-keys-json, carried forward from this wave's own accumulated "
             "$WAVE_REASONS_JSON (Task 4's SKILL.md). Without this, a re-resolution call cannot "
             "recover WHY an already-excluded candidate failed -- neither to report a real "
             "quota_exhausted outcome when every candidate is already excluded (this call's own "
             "walk never starts, so it has no reasons of its own to report) nor to fold an "
             "earlier candidate's real reason into any_quota_recoverable when THIS call's own "
             "QuotaExhaustedError only carries the (narrower) set its own walk actually visited")
    p_resolve.add_argument(
        "--escalation-excluded-keys-json", default="[]",
        help="HIGH finding, recurrence guard: candidate keys dropped from consideration for "
             "Rounds 4-5 capability-escalation reasons ONLY (Task 4's SKILL.md ESCALATION_"
             "EXCLUDE_JSON) -- ranked at-or-below a stuck candidate's own ladder position, never "
             "themselves tried or failed. Kept in a channel separate from --exclude-keys-json/"
             "--excluded-reasons-json on purpose: these keys narrow candidate selection exactly "
             "like --exclude-keys-json does, but never enter `tried`/`reasons` and never receive "
             "the 'no_usable_dispatch' permanent-reason fallback -- a healthy, never-attempted "
             "candidate excluded only to enforce a capability floor must never be reported to the "
             "user as needing a fix, and must never be carried into resume-exclusions' persisted "
             "excluded_keys set as if it had genuinely failed.")

    p_dispatch = sub.add_parser("dispatch-task")
    p_dispatch.add_argument("--injection-json", required=True)
    p_dispatch.add_argument("--prompt-file", required=True)
    p_dispatch.add_argument("--target-dir", required=True)
    p_dispatch.add_argument("--heartbeat-interval", type=int, required=True)
    p_dispatch.add_argument("--timeout", type=int, required=True)
    p_dispatch.add_argument("--format-block-file", required=True)
    p_dispatch.add_argument(
        "--report-file", required=True,
        help="the same path subagent-driven-development's own task-brief-named report file "
             "convention expects. The dispatched CLI is instructed (via the prompt) to write its "
             "OWN detailed report directly here -- if it does, this command never touches the "
             "file. Only if it provably didn't (CRITICAL finding, recurrence guard) does this "
             "command fall back to writing/appending the captured stdout, clearly labeled.")
    p_dispatch.add_argument(
        "--report-mode", choices=["write", "append"], default="write",
        help="'write' (default) for the task's FIRST dispatch -- nothing to preserve yet. "
             "'append' for every fix-loop round -- CRITICAL finding: overwriting the report file "
             "on a fix round destroys the implementer-authored report (and any earlier rounds' "
             "evidence) subagent-driven-development's own task review / re-review reads as the "
             "task's persistent memory.")

    p_classify = sub.add_parser("classify-dispatch-failure")
    p_classify.add_argument("--dispatch-result-json", required=True)

    p_resume_excl = sub.add_parser(
        "resume-exclusions",
        help="CRITICAL finding, recurrence guard: computes the exclusion set safe to PERSIST "
             "into resumable state -- a genuinely time-bound quota reason is dropped, so a later "
             "resume (after quota recovers) can retry that candidate; only permanent reasons "
             "(auth/timeout/configuration/dispatch_unavailable/no_usable_dispatch/real_error) "
             "are kept.")
    p_resume_excl.add_argument("--tried-json", required=True)
    p_resume_excl.add_argument("--reasons-json", required=True)
    p_resume_excl.add_argument("--prior-excluded-keys-json", required=True)

    p_resume = sub.add_parser("write-resumable-state")
    p_resume.add_argument("--path", required=True)
    p_resume.add_argument("--state-json", required=True)

    args = parser.parse_args(argv)

    if args.command == "resolve-injection":
        full_candidates, full_top_n_keys = assemble_candidates_fn(args.cwd, dict(os.environ))
        with open(args.task_file, encoding="utf-8") as f:
            task_markdown = f.read()
        sizes = derive_files_touched_sizes_fn(task_markdown, args.cwd)
        # CRITICAL finding (Rounds 4-5 capability escalation, incomplete ladder): ladder_keys is
        # the FULL ordered candidate-key list -- via compute_ladder_keys_fn's own narrowing/
        # ranking, never list(top_n_keys), which silently omits any candidate outside
        # policy.ladder -- computed over the FULL, pre-exclusion candidate set (never narrowed by
        # whichever keys happen to be excluded on THIS call), so Task 4's SKILL.md can compute
        # "every candidate ranked strictly above the stuck one" for a genuine capability bump,
        # including one that never appeared in policy.ladder at all.
        ladder_keys = compute_ladder_keys_fn(task_markdown, full_candidates, sizes, {},
                                              full_top_n_keys)
        task_type = classify_task_fn(task_markdown)
        excluded_reasons = json.loads(args.excluded_reasons_json)
        exclude = set(json.loads(args.exclude_keys_json))
        # HIGH finding, recurrence guard: escalation_exclude is a SEPARATE set from exclude --
        # candidates dropped purely to enforce Rounds 4-5's capability-bump floor (Task 4's
        # SKILL.md ESCALATION_EXCLUDE_JSON), never themselves tried or failed. It narrows
        # candidate selection exactly like exclude does, but -- unlike exclude -- it is never
        # merged into `tried`/`reasons` below: a healthy, never-attempted candidate excluded only
        # for ranking reasons must never be tagged "no_usable_dispatch" (a permanent-shaped
        # reason), reported to the user as needing a fix, or carried into resume-exclusions'
        # persisted excluded_keys set as if it had genuinely failed.
        escalation_exclude = set(json.loads(args.escalation_excluded_keys_json))
        all_exclude = exclude | escalation_exclude
        candidates = [c for c in full_candidates if c["key"] not in all_exclude]
        top_n_keys = [k for k in full_top_n_keys if k not in all_exclude]

        def _emit_quota_exhausted(tried, reasons):
            # CRITICAL finding, recurrence guard: merge THIS call's own findings with every
            # already-known excluded reason (excluded_reasons -- the wave's own accumulated
            # reasons for keys excluded BEFORE this call even started walking) so any_quota_
            # recoverable/all_auth_failures reflect the WHOLE wave, never just this call's own
            # narrower remaining-ladder walk (which never visits a candidate exclude already
            # dropped). Any excluded key still missing a reason after this merge (this caller
            # never supplied --excluded-reasons-json, or omitted one) falls back to
            # "no_usable_dispatch" -- a permanent-shaped reason, deliberately never "quota", so a
            # gap in the caller's own bookkeeping can never falsely look quota-recoverable.
            # HIGH finding: this loop and the `tried` union below iterate `exclude` ONLY, never
            # `escalation_exclude` -- an escalation-only key must never receive a reason (fallback
            # or otherwise) or appear in `tried` at all, since it was never actually attempted.
            merged_reasons = dict(excluded_reasons)
            merged_reasons.update(reasons)
            for key in exclude:
                merged_reasons.setdefault(key, "no_usable_dispatch")
            merged_tried = sorted(set(tried) | exclude)
            summary = reasons_summary_fn(merged_reasons)
            stdout.write(json.dumps({
                "mode": "quota_exhausted", "task_type": task_type, "tried": merged_tried,
                "reasons": merged_reasons, "all_auth_failures": summary["all_auth_failures"],
                "any_quota_recoverable": summary["any_quota_recoverable"],
                "ladder_keys": ladder_keys,
            }))

        if not candidates:
            # CRITICAL finding: every configured candidate for this task is already excluded
            # BEFORE this call's own walk even starts (a single-candidate ladder tried once, or
            # several waves' accumulated exclusions covering the whole roster -- exclude and/or
            # escalation_exclude together). Calling
            # build_dispatch_injection_fn here would raise its OWN ValueError ("no candidate
            # survived narrowing") -- the wrong exception: that one means a genuine curation gap
            # (nothing configured for this task type at all), not "we already tried everything",
            # and it is never caught below, so it would crash this whole command instead of
            # reporting the controlled quota_exhausted result the SKILL.md's own branch-on-mode
            # logic already handles.
            _emit_quota_exhausted([], {})
            return 0

        existing_quota = cache_read_json_fn(args.quota_path) or {}
        quota = refresh_quota_cache_fn(
            {"reviewers": [
                {"key": c["key"], "model": c["model"], "vendor": c["vendor"], "cli": c["cli"],
                 "command": c.get("command")} for c in candidates
            ]},
            [c["key"] for c in candidates], existing_quota, QUOTA_TTL_SECONDS)
        cache_write_json_fn(args.quota_path, quota)
        try:
            result = build_dispatch_injection_fn(task_markdown, candidates, sizes, {},
                                                   top_n_keys, quota=quota)
            result["ladder_keys"] = ladder_keys
            stdout.write(json.dumps(result))
            return 0
        except QuotaExhaustedError as exc:
            _emit_quota_exhausted(exc.tried, exc.reasons)
            return 0
        except ValueError as exc:
            # HIGH finding: `candidates` can be non-empty here (the `if not candidates` guard
            # above only catches every candidate already EXCLUDED) and build_dispatch_injection_fn
            # can still raise its own ValueError -- e.g. execute_selection.filter_by_context drops
            # every remaining candidate because this task's required_context exceeds every one of
            # their context_limit values, leaving `ranked` empty from a non-empty `candidates`.
            # That is a genuine curation gap (a config/authoring problem: nothing configured can
            # actually run this task), never a quota-availability problem -- an hourly CronCreate
            # wake would never fix it. Report it as its own, distinctly-tagged, controlled JSON
            # result instead of letting the exception propagate uncaught and crash this command
            # (which would also leave $INJECTION_JSON empty, failing Step 2's very next
            # `json.loads` call with an unrelated decode error).
            # MEDIUM finding: build_dispatch_injection_fn raises ValueError from exactly one call
            # site -- "no execute candidate survived affinity/context narrowing for ..." (its own
            # `if not ranked` guard). Every OTHER ValueError build_execute_command_fn can raise
            # ("no execute-mode builder registered for cli=...") is already caught INSIDE
            # build_dispatch_injection_fn's own _is_dispatchable check and turned into a
            # drop-and-continue, never propagated here -- so any ValueError reaching this branch
            # whose message does NOT start with the documented narrowing-failure text is a genuine
            # code defect, not a curation gap, and must not be silently reported to the SKILL.md
            # as a "nothing configured can run this task" no_candidate result. Re-raise it instead
            # so it surfaces as an uncaught crash the agent can actually diagnose.
            if not str(exc).startswith("no execute candidate survived"):
                raise
            stdout.write(json.dumps({
                "mode": "no_candidate", "task_type": task_type, "detail": str(exc),
                "ladder_keys": ladder_keys,
            }))
            return 0

    if args.command == "dispatch-task":
        injection = json.loads(args.injection_json)
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
        with open(args.format_block_file, encoding="utf-8") as f:
            format_block = f.read()
        tool_availability = detect_tool_availability_fn()
        agents_tooling_path = resolve_agents_tooling_path_fn()
        codegraph_registered = ensure_codegraph_registered_fn(injection["cli"])
        if codegraph_registered:
            index_cmd = build_codegraph_index_command_fn(args.target_dir)
            try:
                probe = run_fn(index_cmd, shell=True, capture_output=True, text=True,
                                check=False, timeout=CODEGRAPH_INDEX_TIMEOUT_SECONDS)
                if probe.returncode != 0:
                    codegraph_registered = False
            except (subprocess.TimeoutExpired, OSError):
                codegraph_registered = False
        # CRITICAL finding (recurrence guard): never blindly overwrite --report-file with
        # captured subprocess stdout. The real superpowers implementer contract has the
        # dispatched CLI write its OWN detailed report directly to this path (it has write
        # access to target_dir -- an execute-mode dispatch -- per the prompt's report-file-path
        # instruction) and return only a short status separately. Snapshot the file's content
        # BEFORE dispatching and compare AFTER: if it changed (the CLI wrote to it, appended or
        # created it), that on-disk content IS the implementer's real report -- leave it
        # completely untouched. Only fall back to stdout when the file is provably unchanged.
        report_before = None
        if os.path.isfile(args.report_file):
            with open(args.report_file, encoding="utf-8") as f:
                report_before = f.read()
        result = dispatch_superpowers_task_fn(
            injection, prompt, args.target_dir, args.heartbeat_interval, args.timeout,
            format_block=format_block, tool_availability=tool_availability,
            agents_tooling_path=agents_tooling_path, codegraph_registered=codegraph_registered)
        report_after = None
        if os.path.isfile(args.report_file):
            with open(args.report_file, encoding="utf-8") as f:
                report_after = f.read()
        implementer_wrote_report = report_after is not None and report_after != report_before
        if not implementer_wrote_report:
            fallback_content = _REPORT_FALLBACK_MARKER + result.get("stdout", "")
            if args.report_mode == "append":
                with open(args.report_file, "a", encoding="utf-8") as f:
                    f.write("\n\n---\n\nFix round dispatch (mode=external_cli):\n\n")
                    f.write(fallback_content)
            else:
                with open(args.report_file, "w", encoding="utf-8") as f:
                    f.write(fallback_content)
        stdout.write(json.dumps(result))
        return 0

    if args.command == "classify-dispatch-failure":
        result = json.loads(args.dispatch_result_json)
        stdout.write(classify_dispatch_failure_fn(result))
        return 0

    if args.command == "resume-exclusions":
        result = compute_resume_exclusions_fn(
            json.loads(args.tried_json), json.loads(args.reasons_json),
            json.loads(args.prior_excluded_keys_json))
        stdout.write(json.dumps(result))
        return 0

    if args.command == "write-resumable-state":
        state = json.loads(args.state_json)
        write_resumable_state_fn(args.path, state)
        stdout.write(json.dumps({"written": True, "path": args.path}))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

```python
#!/usr/bin/env python3
"""Shim: `python3 ai-kit-spec-superpowers.py <subcommand> ...` from any cwd, adding this file's
own directory to sys.path first (Python only auto-adds it for `python3 <path>.py`, but this shim
must also add Plan 1's ai-kit-spec-review package root, which lives one level up under a sibling
skill directory -- neither is on the default path when invoked via an absolute path from a
different cwd)."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "ai-kit-spec-review"))

from ai_kit_spec_superpowers.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec_superpowers.TestCliResolveInjection \
  tests.test_ai_kit_spec_superpowers.TestCliDispatchTask \
  tests.test_ai_kit_spec_superpowers.TestCliClassifyDispatchFailure \
  tests.test_ai_kit_spec_superpowers.TestCliResumeExclusions \
  tests.test_ai_kit_spec_superpowers.TestCliWriteResumableState -v 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py \
        skills/ai-kit-spec-execute-superpowers/ai-kit-spec-superpowers.py \
        tests/test_ai_kit_spec_superpowers.py
git commit -m "feat(ai-kit-spec-execute-superpowers): add cli.py and its shim"
```

---

### Task 4: `SKILL.md` — the harness-injection contract

**Files:**
- Create: `skills/ai-kit-spec-execute-superpowers/SKILL.md`

**Interfaces:**
- Consumes: `cli.py`'s `resolve-injection`/`dispatch-task`/`classify-dispatch-failure`/`resume-exclusions`/`write-resumable-state` subcommands (Task 3), invoked via `Bash` exactly as `ai_kit_spec_gsd`'s own SKILL.md invokes its shim.

This is the executable integration the design (§8) requires: it does not merely say "inject the
model choice" — it defines, for `subagent-driven-development`'s own documented process (SKILL.md
§"The Task Loop"), exactly what happens at each step under both `native_claude` and `external_cli`
modes. **Scope: `subagent-driven-development` only** (Global Constraints) — `executing-plans` has
no equivalent dispatch point to hook into (confirmed from its own SKILL.md: every task runs
inline, no `Agent`-tool dispatch anywhere), so it is not addressed here.

- [ ] **Step 1: Write the skill body**

```markdown
---
name: ai-kit-spec-execute-superpowers
description: Resolves the best available, live-quota-checked model/CLI for each task in a superpowers-generated implementation plan, then delegates actual execution to superpowers:subagent-driven-development, injecting the resolved model/CLI at its implementer-dispatch point without bypassing that harness's TDD enforcement, agent-identity/resume, task review, fix-loop, or final-review pattern. Not for superpowers:executing-plans -- that skill executes every task inline with no subagent-dispatch point to inject into. Use when ai-kit-spec-execute detects a superpowers-generated plan (docs/superpowers/plans/*.md) being run under subagent-driven-development and needs to resolve a model/CLI for it.
---

# ai-kit-spec-execute-superpowers

**This skill never dispatches a task itself.** It resolves WHICH model/CLI a task should use, then
hands that resolution to `superpowers:subagent-driven-development` as an explicit input at its one
documented dispatch point — that skill keeps full ownership of TDD enforcement, fresh-subagent-
per-task, agent-identity/resume, task review, fix loops, and the final whole-branch review.
Delegating to it (rather than bypassing it) is deliberate: it carries pattern/TDD knowledge this
skill does not duplicate. **`superpowers:executing-plans` is out of scope** — confirmed from its
own SKILL.md, it runs every task directly in the controller's own session ("Follow each step
exactly", no `Agent`-tool dispatch anywhere), so there is no dispatch point here to inject a
resolution into.

## Step 0: Resolve the shim path

Same pattern `ai-kit-spec-execute-gsd/SKILL.md` uses for its own shim — take the FIRST existing of,
in order, in the same `Bash` call. Every branch is a real, executable check — HIGH finding: no
branch here is an instruction for the reading agent to manually substitute a path; a git-checkout
(this repo cloned or worktree-added, not plugin- or user-globally-installed) is resolved by
searching from the real git toplevel and, failing that, from the current working directory —
covering every supported installation shape (plugin install, user-global install, dev/worktree
checkout) with plain, portable shell:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-execute-superpowers}" \
         "$HOME/.claude/skills/ai-kit-spec-execute-superpowers" \
         "$(git rev-parse --show-toplevel 2>/dev/null)/skills/ai-kit-spec-execute-superpowers" \
         "$(pwd)/skills/ai-kit-spec-execute-superpowers"; do
  [ -n "$d" ] && [ -d "$d" ] && { SKILL_DIR="$d"; break; }
done
if [ -z "$SKILL_DIR" ]; then
  printf 'ERROR: could not resolve skills/ai-kit-spec-execute-superpowers under any known '
  printf 'installation shape (CLAUDE_PLUGIN_ROOT, ~/.claude/skills, git toplevel, or cwd) -- '
  printf 'STOP and tell the user rather than guessing a path.\n'
  exit 1
fi
SHIM="$SKILL_DIR/ai-kit-spec-superpowers.py"
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-review}" \
         "$HOME/.claude/skills/ai-kit-spec-review" \
         "$(dirname "$SKILL_DIR")/ai-kit-spec-review"; do
  [ -d "$d" ] && { REVIEW_SKILL_DIR="$d"; break; }
done
if [ -z "$REVIEW_SKILL_DIR" ]; then
  printf 'ERROR: could not resolve skills/ai-kit-spec-review under any known installation shape '
  printf '(CLAUDE_PLUGIN_ROOT, ~/.claude/skills, or alongside this skill'\''s own resolved '
  printf 'directory) -- STOP and tell the user rather than guessing a path.\n'
  exit 1
fi
TOOLS_PY="$REVIEW_SKILL_DIR/ai-kit-spec.py"
printf 'SHIM=%s\nTOOLS_PY=%s\n' "$SHIM" "$TOOLS_PY"
```

**Record both printed lines as this wave's own literal values.** Every later `python3 $SHIM
<subcommand> ...` invocation uses this resolved `$SHIM` path. `$TOOLS_PY` resolves
`ai-kit-spec-review`'s own shim for its `cache-path --kind quota` subcommand.

**Every separate `Bash` tool call starts a fresh shell** — a variable set in one call is gone by
the next. Every `$VAR` below denotes the literal value most recently captured for it via `printf`,
re-substituted verbatim into every later command.

## Step 1: Load the plan under subagent-driven-development, unmodified

Follow that skill's own Setup exactly as written (workspace, ledger, plan read, pre-flight scan).
This adapter changes nothing about Setup — it only participates at "1. Dispatch the implementer".

`$CWD`, `$PLAN_FILE`, `$TASK_N`, and `$BRIEF_FILE` below are values that skill's own process
already holds at the point it dispatches each task's implementer — this adapter reads them, it
never invents or infers them.

## Step 2: Before each task's implementer dispatch — resolve the injection

`$FIX_ROUND` and `$EXCLUDED_KEYS_JSON` are this task's own wave state, carried across every
`Bash` call for its lifetime (re-`printf`'d and re-substituted each time, per Step 0's own
convention) — HIGH finding: resumable state must capture the complete excluded-candidate set and
which fix round a resume lands on, not just the ladder position at the moment of exhaustion.

**CRITICAL finding (recurrence guard): `$EXCLUDED_KEYS_JSON` is a working union of TWO
differently-provenanced sets — never persist it wholesale as `excluded_keys`, or a same-wave
`"quota"` exclusion becomes indistinguishable from a genuinely permanent one and is never
eligible again after a resume, exactly the bug `resume-exclusions` (Task 3) was built to
prevent.** Track the two sets separately for the task's whole lifetime:

- `$PRIOR_EXCLUDED_KEYS_JSON` — the genuinely permanent exclusion set this task resumed with (or
  `'[]'` for a brand-new task). This is `compute_resume_exclusions`' own OUTPUT from a previous
  wave, already reason-filtered — every key in it stayed excluded because its reason was
  something other than `"quota"`. Never add to this set directly; it only changes across a
  resume (below).
- `$WAVE_TRIED_JSON` / `$WAVE_REASONS_JSON` — every candidate key tried and rejected DURING THIS
  LIVE WAVE (both a `resolve-injection` call's own `tried`/`reasons` when it reports
  `quota_exhausted`, and a mid-dispatch `"quota"` failure caught in Step 3), paired with the
  reason each one failed for. Reset to `'[]'`/`'{}'` at the very first dispatch of a NEW task AND
  on every resume (a resume already folded any earlier wave's non-quota reasons into
  `$PRIOR_EXCLUDED_KEYS_JSON` via `resume-exclusions`, so the new wave starts with a clean slate
  and re-discovers reasons fresh rather than replaying stale ones).
- `$EXCLUDED_KEYS_JSON` — recomputed as the UNION of the two above (`$PRIOR_EXCLUDED_KEYS_JSON`
  plus the keys in `$WAVE_TRIED_JSON`) every time either input changes; this is the ONLY one ever
  passed to `resolve-injection --exclude-keys-json`. Because it is a derived value, never persist
  it directly either — always recompute it, and always persist `$PRIOR_EXCLUDED_KEYS_JSON` /
  `$WAVE_TRIED_JSON` / `$WAVE_REASONS_JSON` (or their `resume-exclusions` output) instead. **This is
  a two-set union, never three** — Step 3's Rounds 4–5 capability-escalation rule (below) tracks a
  THIRD, unrelated set, `$ESCALATION_EXCLUDE_JSON` (healthy, never-attempted candidates excluded
  purely to enforce that round's capability floor, never a failure), and passes it to
  `resolve-injection` through its own separate `--escalation-excluded-keys-json` argument — it never
  joins this union and `$EXCLUDED_KEYS_JSON` is never reassigned to include it.

At the very first dispatch of a NEW task: `FIX_ROUND=0`, `PRIOR_EXCLUDED_KEYS_JSON='[]'`,
`WAVE_TRIED_JSON='[]'`, `WAVE_REASONS_JSON='{}'`, and `EXCLUDED_KEYS_JSON='[]'`. Resuming from a
persisted `$RESUME_STATE_PATH` (below): read `fix_round` into `$FIX_ROUND` and the persisted
`excluded_keys` into `$PRIOR_EXCLUDED_KEYS_JSON` (these are already permanent — `resume-exclusions`
dropped every quota-only key before persisting them); reset `$WAVE_TRIED_JSON='[]'` and
`$WAVE_REASONS_JSON='{}'` for the fresh wave; set `EXCLUDED_KEYS_JSON="$PRIOR_EXCLUDED_KEYS_JSON"`.

Immediately after that skill's own `scripts/task-brief PLAN_FILE N` produces the task's brief file
(`$BRIEF_FILE`), and before composing the dispatch:

```bash
QUOTA_PATH="$(python3 "$TOOLS_PY" cache-path --kind quota)"
INJECTION_JSON="$(python3 "$SHIM" resolve-injection --cwd "$CWD" --task-file "$BRIEF_FILE" \
  --quota-path "$QUOTA_PATH" --exclude-keys-json "$EXCLUDED_KEYS_JSON" \
  --excluded-reasons-json "$WAVE_REASONS_JSON")"
INJECTION_MODE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["mode"])' "$INJECTION_JSON")"
printf 'INJECTION_JSON=%s\nINJECTION_MODE=%s\n' "$INJECTION_JSON" "$INJECTION_MODE"
```

**`--excluded-reasons-json "$WAVE_REASONS_JSON"` — CRITICAL finding, recurrence guard.** Every
`resolve-injection` call in this SKILL.md passes the wave's own accumulated reasons alongside its
excluded keys, not just the keys — without it, a re-resolution call whose `--exclude-keys-json`
already covers every configured candidate for this task would have no way to report a real
`quota_exhausted` outcome at all (its own ladder walk never starts, so it discovers no reasons of
its own), and a re-resolution call that DOES find a fresh `quota_exhausted` result would lose every
earlier-excluded candidate's own reason from `any_quota_recoverable`'s computation — exactly the
"mid-dispatch quota exhaustion cannot reach resumable state" bug this revision closes.

**Record both printed lines, then branch on `$INJECTION_MODE` BEFORE reading any other field —
CRITICAL finding (recurrence guard): the `quota_exhausted` shape (`mode`, `task_type`, `tried`,
`reasons`, `all_auth_failures`, `any_quota_recoverable`) carries no `key`/`cli` at all** (Task 3's
`resolve-injection` `except QuotaExhaustedError` branch never writes one — there is no resolved
candidate to name), **and neither does the `"no_candidate"` mode (`mode`, `task_type`, `detail`,
`ladder_keys` — HIGH finding, Task 3's `except ValueError` branch)**. Unconditionally reading
`.["key"]` here, before checking `$INJECTION_MODE`, raised an uncaught `KeyError` on every genuine
quota-exhausted OR no-candidate resolution — exactly the cases this step exists to handle. Only
once `$INJECTION_MODE` is confirmed to be `native_claude` or `external_cli` (the "Otherwise" branch
below) does this SKILL.md read `key`/`cli`:

```bash
if [ "$INJECTION_MODE" != "quota_exhausted" ] && [ "$INJECTION_MODE" != "no_candidate" ]; then
  INJECTION_KEY="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["key"])' "$INJECTION_JSON")"
  INJECTION_CLI="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("cli") or "")' "$INJECTION_JSON")"
  printf 'INJECTION_KEY=%s\nINJECTION_CLI=%s\n' "$INJECTION_KEY" "$INJECTION_CLI"
fi
```

**If `INJECTION_MODE == "no_candidate"`** (HIGH finding) — a genuine curation gap: nothing
configured for this task can survive affinity/context narrowing at all (read `detail` in
`$INJECTION_JSON` for exactly why, e.g. every candidate's `context_limit` is below this task's
estimated `required_context`). This is not a quota-availability problem, so do **not** schedule
`CronCreate` — waiting an hour changes nothing here. STOP this wave and report `detail` to the
user, plainly, justified on this adapter's own terms exactly as the `any_quota_recoverable ==
False` branch below is (no ruling this adapter could make — trying a different already-configured
candidate — changes an outcome where none of them can run this task at all).

**Record `$INJECTION_KEY`/`$INJECTION_CLI` when this second block ran.** `$INJECTION_KEY` is this
exact candidate's own ladder key (e.g. `codex/terra`) — HIGH finding: distinct from
`$INJECTION_CLI`, which only carries the bare CLI name (e.g. `codex`) and is never itself a valid
`--exclude-keys-json` entry; using the wrong one there would silently fail to exclude anything and
let the ladder retry the same exhausted candidate indefinitely (see Step 3's mid-dispatch
`"quota"` branch below).

If `INJECTION_MODE == "quota_exhausted"`, read `any_quota_recoverable` from `$INJECTION_JSON`
(`python3 -c 'import json,sys; print(json.loads(sys.argv[1])["any_quota_recoverable"])' "$INJECTION_JSON"`)
and branch — HIGH finding: `any_quota_recoverable`, not `all_auth_failures`, is the real gate here.
`reasons` now carries six typed values (`"quota"`, `"auth"`, `"timeout"`, `"configuration"`,
`"dispatch_unavailable"`, `"real_error"`, `"no_usable_dispatch"`) — only `"quota"` is ever worth an
hourly wait; every other reason is a real, permanent problem for that candidate regardless of
whether every OTHER candidate also failed for a different reason:

- **`any_quota_recoverable == False`** — every excluded candidate failed for a reason waiting never
  fixes (read `reasons` in `$INJECTION_JSON` for exactly which — e.g. `"auth"` needs login/
  entitlement, `"configuration"` needs a fixed `command` template, `"timeout"`/
  `"dispatch_unavailable"` needs the CLI itself investigated, `"real_error"` needs its own
  diagnosis). Do **not** schedule `CronCreate` — it would fire forever and never accomplish
  anything. STOP this wave and report to the user, plainly, which candidate key(s) need what fix,
  read straight off `reasons`. **This is not, verbatim, one of `subagent-driven-development`'s own
  four stop-and-ask conditions** (an irreversible/destructive operation, a security-sensitive
  action, a side effect outside this worktree, or a plan so broken every path forward is a guess —
  that skill's own "Rulings, not stalls" section) — none of the six typed reasons above is any of
  those four. It is justified on this adapter's own terms instead: every configured candidate for
  this task is permanently unusable, and no ruling this adapter could make (picking a different
  candidate) changes that outcome — there is no path forward to rule past, only a real,
  human-actionable fix (credentials, a config template, an investigation) outside this session's
  reach. That is functionally the same shape as "a plan so broken every path forward is a guess,"
  so this adapter stops and asks on its own explicit authority, consistent with that skill's intent
  rather than claiming membership in its literal list.
- **`any_quota_recoverable == True`** — at least one candidate is a genuine, time-bound quota
  exhaustion, discovered before dispatch. Write resumable state and schedule an hourly
  `CronCreate` wake, then STOP this wave (do not dispatch this task):

```bash
PROJECT_KEY="$(python3 -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:12])" "$CWD")"
RESUME_STATE_PATH="$(dirname "$QUOTA_PATH")/superpowers-resume-${PROJECT_KEY}-task-${TASK_N}.json"
# CRITICAL finding (recurrence guard, second layer): fold THIS resolve-injection call's own
# tried/reasons into the wave-accumulated sets BEFORE computing what to persist. Without this
# merge, a candidate excluded earlier in the SAME wave purely because of Step 3's mid-dispatch
# "quota" branch (below) would never have its reason recorded here at all -- persisting it would
# either drop it silently (wrong: it really was tried and failed, the harness should know) or, if
# folded in unlabeled via $EXCLUDED_KEYS_JSON directly, get treated as permanent regardless of its
# real (temporary) reason. Merging into $WAVE_TRIED_JSON/$WAVE_REASONS_JSON keeps every wave-tried
# key's real reason attached no matter which step (Step 2 or Step 3) discovered it.
WAVE_TRIED_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | set(json.loads(sys.argv[2])["tried"]))))' \
  "$WAVE_TRIED_JSON" "$INJECTION_JSON")"
WAVE_REASONS_JSON="$(python3 -c 'import json,sys; a=json.loads(sys.argv[1]); a.update(json.loads(sys.argv[2])["reasons"]); print(json.dumps(a))' \
  "$WAVE_REASONS_JSON" "$INJECTION_JSON")"
# CRITICAL finding (recurrence guard): compute the PERSISTED exclusion set via the tested
# resume-exclusions subcommand, never inline, untested set arithmetic -- a "quota" reason is
# deliberately dropped so the candidate is eligible again once quota genuinely recovers; only
# permanent reasons (auth/timeout/configuration/dispatch_unavailable/no_usable_dispatch/
# real_error) are carried forward into the persisted excluded_keys set. `--prior-excluded-keys-json`
# is `$PRIOR_EXCLUDED_KEYS_JSON` (the genuinely permanent set this wave started with) -- NEVER
# `$EXCLUDED_KEYS_JSON`, which is a derived union and would re-feed already-permanent keys back in
# as if they were freshly-tried (harmless) but, worse, would offer no way to tell a same-wave
# "quota" entry apart from a permanent one, since $EXCLUDED_KEYS_JSON carries no reasons at all.
RESUME_EXCLUDED_KEYS_JSON="$(python3 "$SHIM" resume-exclusions --tried-json "$WAVE_TRIED_JSON" \
  --reasons-json "$WAVE_REASONS_JSON" --prior-excluded-keys-json "$PRIOR_EXCLUDED_KEYS_JSON")"
STATE_JSON="$(python3 -c '
import json, sys
print(json.dumps({"framework": "superpowers", "plan_path": sys.argv[1], "task_index": sys.argv[2],
                   "fix_round": int(sys.argv[3]), "excluded_keys": json.loads(sys.argv[4]),
                   "tried": json.loads(sys.argv[5]), "reasons": json.loads(sys.argv[6])}))' \
  "$PLAN_FILE" "$TASK_N" "$FIX_ROUND" "$RESUME_EXCLUDED_KEYS_JSON" "$WAVE_TRIED_JSON" "$WAVE_REASONS_JSON")"
python3 "$SHIM" write-resumable-state --path "$RESUME_STATE_PATH" --state-json "$STATE_JSON"
```

Schedule `CronCreate`: hourly interval, prompt `"re-check quota via probe-quota and, once
restored, resume ai-kit-spec-execute-superpowers from $RESUME_STATE_PATH"`. `CronCreate` jobs are
session-scoped (design spec §10) — they vanish if the session exits, only fire while the session
is idle, and recurring jobs auto-expire after 7 days; tell the user this explicitly. **On resume**,
read `fix_round` back into `$FIX_ROUND` and `excluded_keys` back into `$PRIOR_EXCLUDED_KEYS_JSON`
(never directly into `$EXCLUDED_KEYS_JSON` — see Step 0's state-variable split above), reset
`$WAVE_TRIED_JSON='[]'`/`$WAVE_REASONS_JSON='{}'` for the fresh wave, and recompute
`EXCLUDED_KEYS_JSON="$PRIOR_EXCLUDED_KEYS_JSON"` before re-entering this Step — CRITICAL finding
(recurrence guard): the persisted `excluded_keys` set contains ONLY permanent exclusions
(`compute_resume_exclusions` already dropped every merely-`"quota"`-reason key, including one
discovered mid-dispatch in Step 3), so a candidate that was genuinely quota-exhausted at persist
time — whether discovered here in Step 2 or mid-dispatch in Step 3 — is automatically eligible
again here — the very next `resolve-injection` call always refreshes quota fresh, giving it a real
chance to have recovered, rather than being permanently locked out by its own earlier exhaustion
event. The walk continues exactly where it left off otherwise: never re-trying an
already-permanently-excluded candidate and never losing which fix round the task was on.

Otherwise, `$INJECTION_JSON` carries `mode`, `key`, `model`, and (for `external_cli`) `cli`,
`effort`, `service_tier`. Proceed to Step 3.

## Step 3: Dispatch the implementer — apply the injection

**`mode == "native_claude"`:** unchanged from `subagent-driven-development`'s own process. Pass
`model` as the `Agent` tool's own `model` parameter, dispatch exactly as documented, and record
the returned agent identity — fix-loop rounds 1–3 resume this SAME live agent, exactly as that
skill's own "1. Dispatch the implementer" step already specifies. Nothing else about this mode
changes.

**`mode == "external_cli"`:** there is no live subagent to hold an identity for — a dispatched CLI
process exits when it finishes. `subagent-driven-development`'s own text already defines the
fallback for exactly this case ("If your harness cannot send another message to a live subagent,
dispatch a fresh implementer carrying the brief path, the report-file path, and the findings — the
report file is the persistent memory either way"). Every `external_cli` dispatch — the first
attempt AND every fix-loop round — uses that fallback path:

**Artifact paths — HIGH finding (recurrence guard): these are exact, plan-scoped, and created by a
real command, never left for the executing agent to improvise.** Derive all three from `$BRIEF_FILE`
(`subagent-driven-development`'s own `scripts/task-brief` already named it `…/task-N-brief.md`), and
create the scratch subdirectory they live in, once, before the first use:

```bash
TASK_STATE_DIR="$(dirname "$BRIEF_FILE")/.ai-kit-spec-execute-superpowers"
mkdir -p "$TASK_STATE_DIR"
PROMPT_FILE="$TASK_STATE_DIR/task-${TASK_N}-prompt.txt"
FORMAT_BLOCK_FILE="$TASK_STATE_DIR/task-${TASK_N}-format-block.md"
REPORT_FILE="${BRIEF_FILE%-brief.md}-report.md"
printf 'PROMPT_FILE=%s\nFORMAT_BLOCK_FILE=%s\nREPORT_FILE=%s\n' \
  "$PROMPT_FILE" "$FORMAT_BLOCK_FILE" "$REPORT_FILE"
```

`$REPORT_FILE` sits alongside `$BRIEF_FILE` itself (`…/task-N-brief.md` → `…/task-N-report.md`,
substituting the suffix), matching `subagent-driven-development`'s own naming convention exactly —
this is the SAME path that skill's own task review / re-review / ledger already expect to find the
task's report at, so no extra wiring is needed for later steps to pick it up. `$PROMPT_FILE`/
`$FORMAT_BLOCK_FILE` are pure scratch — this adapter's own working files, never read by
`subagent-driven-development` itself — so they live in a dedicated, clearly-named subdirectory next
to the brief rather than cluttering the task's own directory.

**`$REPORT_MODE`: `write` exactly once per task, `append` for every dispatch-task call after
that — CRITICAL finding.** Determine the INITIAL value the moment `$REPORT_FILE`'s path is known
(above), for BOTH a brand-new task and a resumed one — never assume `write` unconditionally, since
a resumed task may already have a partial report on disk from before the resume:

```bash
if [ -s "$REPORT_FILE" ]; then REPORT_MODE=append; else REPORT_MODE=write; fi
printf 'REPORT_MODE=%s\n' "$REPORT_MODE"
```

(`-s` is true when the file exists AND is non-empty — a brand-new task's report file does not exist
yet, so this correctly starts it at `write`; a resumed task whose report already has content from an
earlier round correctly continues at `append`, never re-triggering the CRITICAL finding this rule
exists to prevent.) Immediately after EVERY `dispatch-task` call returns from here on — success or
failure, whether or not this specific attempt's own output turns out to be a genuine implementer
report — set `REPORT_MODE=append` and never set it back to `write` for the rest of this task's
lifetime (mid-round quota-escalation retries below, and every later fix-loop round alike). This
guarantees `$REPORT_FILE` is a complete, ordered history that a `write` call can never silently
destroy — the exact failure mode the CRITICAL finding named (a fix-loop round's `dispatch-task` call
was overwriting the implementer's own report, and any earlier rounds' evidence, instead of appending
to it).

1. Compose the SAME dispatch prompt `subagent-driven-development`'s own implementer-prompt.md
   template calls for (brief path, context, report-file path, the "you do not dispatch subagents"
   contract) — write it to `$PROMPT_FILE` (path defined above). **The composed prompt must
   explicitly instruct the dispatched CLI to write its own detailed report directly to
   `$REPORT_FILE`** (it has write access to `$CWD`, being an execute-mode dispatch) **and return
   only a short status line separately** — this IS implementer-prompt.md's own real contract
   (detailed evidence to the report file, a short status separately, CRITICAL finding, recurrence
   guard): `dispatch-task` (Task 3) only falls back to capturing stdout as the report when the CLI
   provably didn't write to that path itself. **On the FIRST dispatch of a task, the prompt text
   instructs the CLI to WRITE `$REPORT_FILE`; on every dispatch after the first — every fix-loop
   round — the prompt text itself must instead instruct the CLI to APPEND its report to the END of
   `$REPORT_FILE`, never overwrite it (HIGH finding, distinct from `dispatch-task`'s own
   `--report-mode` flag).** `--report-mode append` only governs `dispatch-task`'s own
   stdout-fallback path — the case where the dispatched CLI did NOT write its own report — and
   deliberately never touches a file the CLI wrote to directly (Task 3). When the CLI DOES follow
   the prompt's instruction and writes its own report, `--report-mode` has no say over what the CLI
   itself does to that file; a prompt that told a round-2 CLI only "write your report to
   `$REPORT_FILE`" would have a fully compliant CLI overwrite round 1's evidence — the same failure
   `--report-mode` was built to close, relocated into the prompt text. Match
   `subagent-driven-development`'s own "every round... appends its fix report to the same report
   file" contract exactly: word the fix-loop-round instruction as "APPEND your detailed report to
   the end of `$REPORT_FILE` — do not overwrite its existing contents from earlier rounds." On a
   fix-loop round, also append the open findings verbatim to this same prompt, per that skill's own
   "Rounds 1–3 — resume" fallback text quoted above. Rounds 4–5 use the capability-escalation rule
   defined after the classification step below (never a plain ladder-exclusion walk, which cannot
   guarantee the required capability bump). **Increment `$FIX_ROUND` by one at the start of every
   fix-loop round, BEFORE evaluating the Rounds 4–5 `$FIX_ROUND >= 4` capability-escalation check
   below and before composing that round's prompt** (never for a same-round quota-escalation retry,
   which is not a new round) — this fixes the ordering ambiguity between the increment and the
   check (HIGH finding): round 4's own dispatch is the one where `$FIX_ROUND` first reads `4`, and
   that is exactly when capability escalation must first apply.
2. Write the implementer report-file's own required status contract (`DONE` /
   `DONE_WITH_CONCERNS` / `NEEDS_CONTEXT` / `BLOCKED`, per implementer-prompt.md's own "After
   Review Findings" section) to `$FORMAT_BLOCK_FILE` — this becomes `dispatch_execute`'s
   `format_block`, reinforcing that the dispatched CLI's own final output must match it.
3. Dispatch for real — `dispatch-task` already computes and applies tooling guidance internally
   (Task 3), so there is no separate tooling-preparation call to make first. **MEDIUM finding:
   `--timeout 900` is a fixed constant, deliberately — this adapter does not read a resolved
   candidate's own per-entry `timeout_tiers` override.** `timeout_tiers` (Global Constraints,
   optional-fields paragraph) is a real field `ai-kit-spec-config` writes, but nothing in
   `assemble_candidates` (Task 2) carries it onto a candidate dict, and no equivalent of
   `ai_kit_spec.config_io.resolve_timeout_tiers` is wired in here — propagating it would mean
   plumbing a per-candidate timeout through `resolve-injection`'s JSON, `dispatch-task`'s own
   arguments, and this call, which this plan treats as out of scope rather than a silent gap: a
   known-slow entry's `timeout_tiers` override exists for the GSD adapter's own review-dispatch
   timeout tiers (fix-round pressure that genuinely varies by round), a different axis than this
   adapter's fixed execute-mode heartbeat/timeout budget. A future revision that wants a
   known-slow execute candidate to get a longer budget here should add that plumbing explicitly
   rather than have it silently assumed to already work:

```bash
DISPATCH_RESULT_JSON="$(python3 "$SHIM" dispatch-task --injection-json "$INJECTION_JSON" \
  --prompt-file "$PROMPT_FILE" --target-dir "$CWD" --heartbeat-interval 60 --timeout 900 \
  --format-block-file "$FORMAT_BLOCK_FILE" --report-file "$REPORT_FILE" \
  --report-mode "$REPORT_MODE")"
printf 'DISPATCH_RESULT_JSON=%s\n' "$DISPATCH_RESULT_JSON"
```

Immediately after this call returns (per the rule above): `REPORT_MODE=append`.

`$REPORT_FILE` is named exactly as `subagent-driven-development`'s own convention requires (brief
`…/task-N-brief.md` → report `…/task-N-report.md`). **`dispatch-task` never overwrites an
implementer-authored report with captured stdout (CRITICAL finding, recurrence guard)**: when the
dispatched CLI followed point 1's instruction and wrote its own detailed report directly to
`$REPORT_FILE`, that on-disk content is left completely untouched — `dispatch-task` detects this
by comparing the file's content before and after the dispatch call. Only when the file is provably
unchanged (the CLI never wrote to it) does `dispatch-task` fall back to writing/appending the
captured stdout, with a leading marker line so a fallback is never mistaken for a genuine
implementer report. Either way, every later step (task review, fix loop) reads `$REPORT_FILE`
exactly as it would read a native subagent's own report, its history intact across every round.

4. Classify the outcome before treating it as the implementer's report:

```bash
CLASSIFICATION="$(python3 "$SHIM" classify-dispatch-failure --dispatch-result-json "$DISPATCH_RESULT_JSON")"
```

- `"ok"` — proceed exactly as `subagent-driven-development`'s own "2. Handle the report" step
  describes, but **read the short status line from `$DISPATCH_RESULT_JSON`'s own `stdout` field,
  never from `$REPORT_FILE`'s content — CRITICAL finding (status-channel mismatch).** The prompt
  composed in point 1 above instructs the dispatched CLI to write its DETAILED evidence directly to
  `$REPORT_FILE` and return only the short `DONE`/`DONE_WITH_CONCERNS`/`NEEDS_CONTEXT`/`BLOCKED`
  contract SEPARATELY (implementer-prompt.md's own real contract, quoted above) — that separate
  reply is exactly `$DISPATCH_RESULT_JSON["stdout"]`, the captured subprocess output, not the report
  file. `$REPORT_FILE` is free-form detailed evidence with no guaranteed status-line position or
  format (and, per `dispatch-task`'s CLI-writes-its-own-report path, `dispatch-task` never even
  inspects its content) — parsing a status keyword out of it is unreliable at best and silently
  wrong whenever the implementer's prose happens to mention one of the four words in passing.
  Extract it with:

```bash
STATUS_LINE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["stdout"])' "$DISPATCH_RESULT_JSON")"
STATUS="$(printf '%s\n' "$STATUS_LINE" | rg -o '\b(DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED|DONE)\b' | tail -1)"
```

  (MEDIUM finding: `rg -o`, not `grep -oE` — `TOOL_AVAILABILITY` already confirms `rg: true` for
  every supported environment this plan targets, and `rg`'s default regex engine is already
  extended/Perl-compatible-enough for this alternation with no `-E`-equivalent flag needed.
  `DONE_WITH_CONCERNS`/`NEEDS_CONTEXT`/`BLOCKED` are matched before the bare `DONE` alternative so
  the alternation cannot short-circuit on the `DONE` prefix of a longer status word; `tail
  -1` takes the dispatched CLI's own FINAL status line if its reply echoes the format-block's
  allowed-values list before stating its actual status.) If `$STATUS` is empty — the dispatched CLI
  never emitted a recognizable status word in `stdout` — treat this exactly like `BLOCKED`
  (`subagent-driven-development`'s own stop-and-ask path) rather than guessing; do not fall back to
  scanning `$REPORT_FILE` for one.
- `"quota"` — this specific candidate went quota-exhausted mid-dispatch (not discovered ahead of
  time in Step 2, but a real, late signal — design spec §12). **CRITICAL finding (recurrence
  guard): record this as a wave-tried key WITH its `"quota"` reason — never fold it into
  `$EXCLUDED_KEYS_JSON` directly with no reason attached**, or a later resumable-state persist
  (Step 2) would have no way to tell this temporary, mid-dispatch exclusion apart from a genuinely
  permanent one, and it would never become eligible again after a resume — the exact bug a prior
  revision's fix (the `resume-exclusions` subcommand itself) was meant to close, recurring one
  layer up:

```bash
WAVE_TRIED_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | {sys.argv[2]})))' \
  "$WAVE_TRIED_JSON" "$INJECTION_KEY")"
WAVE_REASONS_JSON="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); d[sys.argv[2]]="quota"; print(json.dumps(d))' \
  "$WAVE_REASONS_JSON" "$INJECTION_KEY")"
EXCLUDED_KEYS_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | set(json.loads(sys.argv[2])))))' \
  "$PRIOR_EXCLUDED_KEYS_JSON" "$WAVE_TRIED_JSON")"
```

  (`$INJECTION_KEY` is this exact candidate's own ladder key, e.g. `codex/terra` — HIGH finding:
  never `$INJECTION_CLI`, which only carries the bare CLI name, e.g. `codex`, and would silently
  exclude nothing, letting the ladder retry the same exhausted candidate indefinitely.) Re-run Step
  2's `resolve-injection` with the recomputed `--exclude-keys-json "$EXCLUDED_KEYS_JSON"` — this
  reuses the SAME invocation shape, including `--excluded-reasons-json "$WAVE_REASONS_JSON"`, **and,
  when this mid-dispatch quota failure happened on a Rounds 4–5 capability-escalated candidate
  (`$ESCALATION_EXCLUDE_JSON` is non-empty this round), also `--escalation-excluded-keys-json
  "$ESCALATION_EXCLUDE_JSON"` — otherwise this retry would silently drop the capability floor that
  round established and could hand back a same-or-weaker candidate the Rounds 4–5 rule below already
  ruled out** — which now already carries this exact candidate's own freshly-recorded `"quota"`
  reason (updated above) — and retry Step 3 with the newly-resolved injection — never re-dispatch the
  same candidate blind. Excluding it from `$EXCLUDED_KEYS_JSON` (the live resolve-injection input) is
  intentionally immediate and unconditional within this SAME wave — a candidate that just failed mid-dispatch
  should not be retried again a moment later — but its `"quota"` reason travels with it in
  `$WAVE_REASONS_JSON`, so if this wave later needs to persist resumable state, `resume-exclusions`
  still drops it and it is eligible again on resume, exactly like a candidate Step 2 itself caught as
  quota-exhausted ahead of time. **CRITICAL finding (recurrence guard): even if this wave's
  `EXCLUDED_KEYS_JSON` now covers every configured candidate — a single-candidate ladder tried once,
  or several exclusions in a row covering the whole roster — `resolve-injection` no longer crashes**
  (a prior revision's `build_dispatch_injection` raised an uncaught `ValueError` in exactly this
  case, mistaking "every candidate already excluded" for "nothing configured at all"); it reports a
  controlled `quota_exhausted` result instead, using `--excluded-reasons-json` to recover every
  already-known reason. If re-resolution itself now reports `quota_exhausted`, follow Step 2's own
  `any_quota_recoverable`/resumable-state/`CronCreate` branch (which merges this call's own
  `tried`/`reasons` into `$WAVE_TRIED_JSON`/`$WAVE_REASONS_JSON` too, so nothing discovered here is
  lost).
- `"real_error"` — never silently retried (design spec §12's explicit rule). Treat exactly as
  `subagent-driven-development`'s own `BLOCKED` handling: assess the blocker (more context and
  retry, a capability-escalated candidate per the Rounds 4–5 rule below, break the task down, or
  rule on a plan defect) — never force the same candidate to retry unchanged.

**Rounds 4–5 capability escalation (`mode == "external_cli"` only) — CRITICAL finding.** Applied at
the START of point 1 above, immediately AFTER that round's `$FIX_ROUND` increment (never before it
— see point 1's ordering rule above; the check reads the POST-increment value) and BEFORE composing
that round's prompt, whenever `$FIX_ROUND >= 4` (i.e. `subagent-driven-development`'s own fix-loop,
unmodified per Step 4 below, has re-entered this dispatch point for the 4th or 5th time on this
task) AND the mode in play is `external_cli` (a
`native_claude` fix-loop round is unchanged — see that mode's own paragraph above; its round 4/5
model-tier bump is that skill's own `Agent`-tool dispatch judgment, made fresh each round exactly as
`subagent-driven-development`'s own Model Selection section already specifies, with no ladder
involved). `subagent-driven-development`'s own Model Selection section requires rounds 4–5 to
"dispatch a fresh implementer on a MORE CAPABLE model" — a genuine capability bump, not merely a
different one.
Naively excluding the stuck candidate's key and letting `resolve-injection` re-walk the ladder does
NOT guarantee this: the next surviving candidate by quota/affinity/context ranking could easily be
LESS capable than the one that got stuck. Today's config schema has no dedicated capability-tier
field (Global Constraints — `strength` is free text, not yet consumed by any resolution logic), so
this adapter uses the ladder's own established preference ordering (`policy.ladder`, authored
most-preferred-first — the same convention the GSD adapter's ladder walk already relies on, and the
same ordering `resolve-injection` already walks best-first) as the capability-tier proxy: only a
candidate ranked STRICTLY ABOVE the stuck candidate's own ladder position — never at the SAME
position, and never the stuck candidate itself — counts as a real capability bump. `resolve-
injection`'s JSON output (every mode, including `quota_exhausted`) now carries `ladder_keys` — the
full ranked candidate-key list `assemble_candidates` produced, BEFORE any `--exclude-keys-json`
filtering (Task 3, CRITICAL finding fix) — precisely so this computation is possible from data this
SKILL.md already has:

```bash
LADDER_KEYS_JSON="$(python3 -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1])["ladder_keys"]))' "$INJECTION_JSON")"
ESCALATION_EXCLUDE_JSON="$(python3 -c '
import json, sys
ladder = json.loads(sys.argv[1]); stuck = sys.argv[2]
idx = ladder.index(stuck) if stuck in ladder else len(ladder)
print(json.dumps(sorted(set(ladder[idx:]) | {stuck})))
' "$LADDER_KEYS_JSON" "$INJECTION_KEY")"
```

**CRITICAL finding (incomplete ladder, recurrence guard): `{stuck}` is unioned in explicitly, and
the not-found fallback is `len(ladder)` (exclude nothing extra), never `0` (exclude the WHOLE
ladder).** `$LADDER_KEYS_JSON` now comes from `compute_ladder_keys` (Task 2/3, CRITICAL finding
fix) — the full narrowed+ranked candidate set, not merely `policy.ladder`'s configured keys — so
`stuck` (`$INJECTION_KEY`) is expected to appear in it whenever the same task/config produced both.
But relying on that alone is fragile — a prior revision's `idx = ... if stuck in ladder else 0`
fallback had a real bug even independent of `ladder_keys`' own completeness: when `stuck` is absent
from `ladder`, `ladder[idx:]` excludes ladder MEMBERS only, and `stuck` itself, never being a member,
was never added to the exclude set at all — leaving the very candidate this round is escalating away
from immediately eligible for reselection. Explicitly unioning `{stuck}` closes that regardless of
whether `stuck` is found in `ladder`, and `len(ladder)` (rather than `0`) as the not-found fallback
avoids the OPPOSITE overcorrection — excluding the entire ladder when the index is unknown, which
would have blocked every real candidate, not just same-or-weaker ones.

**CRITICAL finding (recurrence guard): `$ESCALATION_EXCLUDE_JSON` is passed ONLY via the new,
separate `--escalation-excluded-keys-json` argument, NEVER folded into `$EXCLUDED_KEYS_JSON` or
assigned back into it.** `$EXCLUDED_KEYS_JSON` keeps exactly the meaning Step 2 defines for it —
the recomputed union of `$PRIOR_EXCLUDED_KEYS_JSON` and `$WAVE_TRIED_JSON`, the ONLY value ever
passed as `--exclude-keys-json` — for this task's entire lifetime, with no third exception carved
out here. `$ESCALATION_EXCLUDE_JSON` is a different kind of thing: every key in it is a healthy,
never-attempted candidate excluded purely to enforce this round's capability floor, not a candidate
that was tried and failed — folding it into `$EXCLUDED_KEYS_JSON` (a prior revision did exactly
this) would make the very next union recompute (Step 3's own mid-dispatch `"quota"` branch above,
or a resume re-entering Step 2) silently drop those keys again, since neither
`$PRIOR_EXCLUDED_KEYS_JSON` nor `$WAVE_TRIED_JSON` ever recorded them — letting a later resolution
re-select a same-or-weaker candidate this round explicitly ruled out. Re-run `resolve-injection`
with the SAME `--exclude-keys-json "$EXCLUDED_KEYS_JSON"` and `--excluded-reasons-json
"$WAVE_REASONS_JSON"` this round already had, adding `--escalation-excluded-keys-json
"$ESCALATION_EXCLUDE_JSON"` (same call shape as Step 2's own `resolve-injection` invocation above,
plus this one extra argument) — this excludes every genuinely-tried-and-failed candidate exactly as
before, AND every candidate ranked at-or-below the stuck one — i.e. same-or-weaker — never just the
stuck one alone. If it resolves to a real candidate (`native_claude`/`external_cli`), that IS the
capability-bumped implementer for this round: proceed with the new injection WITHOUT reassigning
`$EXCLUDED_KEYS_JSON`, framing the dispatch exactly as `subagent-driven-development`'s own text
requires: "A prior implementer attempted this task [N] times; you own it now. Read the report file
for what was tried." **`$ESCALATION_EXCLUDE_JSON` needs no persistence across rounds or resumes to
guarantee round 5 never regresses to a same-or-weaker candidate already ruled out in round 4**: it
is recomputed from scratch every time this check fires, purely from `$LADDER_KEYS_JSON` (stable for
this task) and THAT round's own freshly-resolved `$INJECTION_KEY` — and `$INJECTION_KEY` for round 5
can only be a candidate this same rule already proved was ranked strictly above round 4's stuck
candidate (or round 4's escalation-bumped candidate itself, if it later failed and became round 5's
own stuck candidate) — so round 5's `idx` is never worse than round 4's, and round 5's freshly
recomputed `ladder[idx:]` is automatically at least as restrictive. A resume behaves the same way:
Step 2 resolves fresh from `$PRIOR_EXCLUDED_KEYS_JSON` alone (no escalation floor), and if
`$FIX_ROUND >= 4` still holds, this check re-fires against whatever `$INJECTION_KEY` Step 2 just
landed on, re-deriving the correct floor before that round's implementer is ever dispatched.

If re-resolution instead reports `quota_exhausted` — **HIGH finding: this must not simply discard
resumable state and the auto-wake.** Read `any_quota_recoverable` from that result exactly as Step
2 does, and branch the same way:

- **`any_quota_recoverable == True`** — at least one of the more-capable candidates is only
  temporarily unavailable. This is genuinely time-bound, so treat it exactly like Step 2's own
  `any_quota_recoverable == True` branch, verbatim: merge this call's own `tried`/`reasons` into
  `$WAVE_TRIED_JSON`/`$WAVE_REASONS_JSON`, compute `$RESUME_EXCLUDED_KEYS_JSON` via
  `resume-exclusions` against `$PRIOR_EXCLUDED_KEYS_JSON`, write `$STATE_JSON` (including this
  round's own current `$FIX_ROUND`, already incremented per point 1's ordering rule below) via
  `write-resumable-state`, and schedule the hourly `CronCreate` wake — THEN stop this wave. Never
  dispatch a same-or-weaker candidate as a substitute just because persistence happened; the
  capability-bump requirement is still unmet this round, resumable exactly as Step 2's own
  quota-exhaustion case is.
- **`any_quota_recoverable == False`, or re-resolution finds no candidate at all** (the
  `no_candidate` mode — defined in Step 2 above, "If `INJECTION_MODE == "no_candidate"`") — no
  ruling or wait fixes this: no genuinely more-capable candidate is
  currently available for reasons waiting never resolves. Do **not** silently fall through to a
  same-or-weaker one, and do **not** schedule a futile `CronCreate` wake. STOP and report to the
  user, plainly, that rounds 4–5 cannot honor the capability-bump requirement with the currently
  configured/available ladder, reading `reasons`/`detail` off the result for exactly which
  candidates and why — justified on this adapter's own terms exactly as Step 2's own
  `any_quota_recoverable == False` branch is (above), not by claiming membership in
  `subagent-driven-development`'s own four stop-and-ask conditions verbatim. **MEDIUM finding: when
  the re-resolution narrowed the pool purely via `--escalation-excluded-keys-json` — the common case,
  where the stuck candidate is top-ranked and everything at-or-below it on the ladder is
  escalation-excluded, with nothing in `--exclude-keys-json` genuinely failed — `reasons`/`detail`
  come back empty by design (escalation-excluded keys never get a reason), so there is nothing to
  read off the result.** In that case, report instead that no candidate ranked above `$INJECTION_KEY`
  on the ladder is available for a fresh (non-escalation) pick — name the excluded keys from
  `$ESCALATION_EXCLUDE_JSON` (the same ladder keys Step 2 above passed as
  `--escalation-excluded-keys-json`) explicitly, so the user sees which candidates were excluded and
  why even though the result's own `reasons` map is empty.

## Step 4: Task review, fix loop, final review — unaffected

Whichever mode Step 3 used, `subagent-driven-development`'s own "3. Review the task" and "4. The
fix loop" proceed completely unmodified from here: `scripts/review-package`, the task reviewer
dispatch, the fix-loop round structure (1–5), and the final whole-branch review all operate on
`$REPORT_FILE` and the real commits the dispatch produced, with zero awareness of which mode
produced them. This skill's own scope ends at Step 3 — it never touches review, fix-loop
adjudication, or the ledger directly.
```

- [ ] **Step 2: Run skill-judge against this skill**

Invoke `skill-judge` on `skills/ai-kit-spec-execute-superpowers/SKILL.md`. Fix any finding before
proceeding.

- [ ] **Step 3: Commit**

```bash
git add skills/ai-kit-spec-execute-superpowers/SKILL.md
git commit -m "docs(ai-kit-spec-execute-superpowers): add SKILL.md"
```

---

### Task 5: Wire the router — `detect_framework.py` + extend `ai-kit-spec-execute/SKILL.md`

**Files:**
- Modify: `skills/ai-kit-spec-execute/detect_framework.py`
- Modify: `skills/ai-kit-spec-execute/SKILL.md`
- Test: `tests/test_ai_kit_spec_superpowers.py` (append)

**Interfaces:**
- Consumes: nothing new.
- Produces: `detect_framework(cwd, document_path=None, conversation_signal=None,
  isfile_fn=os.path.isfile, isdir_fn=os.path.isdir) -> str` — CRITICAL finding: repository markers
  alone are supporting evidence, never the primary signal. The requested document's own path and an
  explicit conversation signal both outrank them, mirroring `ai-kit-spec-review`'s own Step 0.5 "A.
  Detect the framework" text verbatim ("Match the document path + nearby project markers... —
  Conversation signal wins: if the user just used a framework's skill... use it"), which design §3
  names as the approach this router must follow ("same signal-matching approach as
  `ai-kit-spec-review` Step 0.5").

**Precedence (highest first) — CRITICAL finding fix:**
1. **`conversation_signal`** — the caller (this skill's own SKILL.md Step 1, updated below) passes
   `"gsd"` or `"superpowers"` when the user just invoked that framework's own skill in this same
   conversation (superpowers `writing-plans`/`brainstorming`, or GSD's own planning skills) or
   otherwise unambiguously named the framework. Wins outright over every other signal — the same
   "Conversation signal wins" rule `ai-kit-spec-review` Step 0.5 already documents.
2. **`document_path`** — the plan/phase path the user actually asked to execute, when supplied.
   Checked against each framework's own documented path convention: GSD's phase/plan documents live
   under `.planning/` (`skills/ai-kit-spec-review-checklist/references/frameworks/gsd.md`'s own
   `doc_types` globs — `.planning/phases/**/*`, `.planning/**/*PLAN.md`); superpowers' plans live
   under `docs/superpowers/plans/` (`writing-plans`' own "Save plans to" line). A path matching
   neither convention falls through to marker-based evidence rather than guessing.
3. **Repository markers (`isfile_fn`/`isdir_fn`)** — supporting evidence only, used when neither of
   the above resolved anything: `.planning/PROJECT.md` (GSD) vs. `docs/superpowers/plans/`
   existing (superpowers), GSD's marker checked first when both are present (the more specific,
   harder-to-fake signal, so it wins ties at this fallback tier only — never overriding an explicit
   `document_path`/`conversation_signal` above it).

Before this revision, marker-based detection was the ONLY signal, so a mixed-marker repository
(both `.planning/PROJECT.md` and `docs/superpowers/plans/` present — plausible after prior
experimentation with both frameworks) always routed to GSD, even when the user explicitly supplied
a `docs/superpowers/plans/*.md` plan to execute — silently overriding their own explicit choice.
`document_path` now settles that case correctly before markers are even consulted.

- [ ] **Step 1: Write the failing tests**

```python
# skills/ai-kit-spec-execute is not a package (no __init__.py) -- the bootstrap block already put
# it on sys.path (Task 1), so detect_framework.py imports as a bare top-level module.
import detect_framework as router_detect_framework


class TestDetectFrameworkSuperpowers(unittest.TestCase):
    def test_detects_superpowers_from_plans_directory(self):
        def isdir_fn(path):
            return path == os.path.join("/repo", "docs", "superpowers", "plans")

        result = router_detect_framework.detect_framework(
            "/repo", isfile_fn=lambda p: False, isdir_fn=isdir_fn)
        self.assertEqual(result, "superpowers")

    def test_gsd_marker_wins_over_superpowers_marker_when_both_present_and_no_stronger_signal(self):
        result = router_detect_framework.detect_framework(
            "/repo",
            isfile_fn=lambda p: p == os.path.join("/repo", ".planning", "PROJECT.md"),
            isdir_fn=lambda p: p == os.path.join("/repo", "docs", "superpowers", "plans"))
        self.assertEqual(result, "gsd")

    def test_returns_unknown_when_neither_marker_present(self):
        result = router_detect_framework.detect_framework(
            "/repo", isfile_fn=lambda p: False, isdir_fn=lambda p: False)
        self.assertEqual(result, "unknown")

    def test_document_path_overrides_gsd_marker_when_both_markers_present(self):
        # CRITICAL finding (recurrence guard): a repo with BOTH markers present must still route a
        # user-supplied superpowers plan path to superpowers -- markers are supporting evidence
        # only, never the primary signal once an explicit document path is available.
        result = router_detect_framework.detect_framework(
            "/repo", document_path="/repo/docs/superpowers/plans/2026-08-29-widget.md",
            isfile_fn=lambda p: p == os.path.join("/repo", ".planning", "PROJECT.md"),
            isdir_fn=lambda p: p == os.path.join("/repo", "docs", "superpowers", "plans"))
        self.assertEqual(result, "superpowers")

    def test_document_path_under_planning_resolves_gsd_even_without_markers(self):
        result = router_detect_framework.detect_framework(
            "/repo", document_path="/repo/.planning/phases/02-widget/02-01-PLAN.md",
            isfile_fn=lambda p: False, isdir_fn=lambda p: False)
        self.assertEqual(result, "gsd")

    def test_conversation_signal_wins_over_a_contradicting_document_path_and_markers(self):
        # CRITICAL finding: conversation signal is the strongest evidence -- the user just invoked
        # writing-plans in this very conversation, which outranks even an explicit document path
        # that happens to look GSD-shaped (e.g. copied under a .planning/ scratch directory).
        result = router_detect_framework.detect_framework(
            "/repo", document_path="/repo/.planning/scratch/notes.md",
            conversation_signal="superpowers",
            isfile_fn=lambda p: p == os.path.join("/repo", ".planning", "PROJECT.md"),
            isdir_fn=lambda p: False)
        self.assertEqual(result, "superpowers")
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_superpowers.TestDetectFrameworkSuperpowers -v 2>&1 | tail -30
```

Expected: FAIL — `detect_framework()` does not yet accept `document_path`/`conversation_signal`
keyword arguments, and `test_detects_superpowers_from_plans_directory` still returns `"unknown"`.

- [ ] **Step 3: Implement**

```python
"""Framework detection for ai-kit-spec-execute's router. Precedence (design spec S3, "same
signal-matching approach as ai-kit-spec-review Step 0.5" -- CRITICAL finding fix, repository
markers are supporting evidence only, never the primary signal):
  1. conversation_signal ("gsd"/"superpowers") -- the caller's own SKILL.md passes this when the
     user just invoked that framework's own planning skill in this conversation. Wins outright.
  2. document_path -- checked against each framework's own documented path convention: GSD phase/
     plan docs live under .planning/ (skills/ai-kit-spec-review-checklist/references/frameworks/
     gsd.md's own doc_types globs); superpowers plans live under docs/superpowers/plans/
     (writing-plans' own "Save plans to" line).
  3. Repository markers (isfile_fn/isdir_fn) -- confirmed signals: .planning/PROJECT.md (GSD, per
     skills/ai-kit-spec-review-checklist/references/frameworks/gsd.md) vs. docs/superpowers/plans/
     existing (superpowers, per writing-plans' own SKILL.md). GSD's marker is checked first when
     both are present -- the more specific, harder-to-fake signal, so it wins ties AT THIS
     FALLBACK TIER ONLY; it never overrides an explicit document_path/conversation_signal above.

Also runnable directly: `python3 detect_framework.py <cwd> [document_path]` prints the result on
stdout."""
import os
import sys


def _framework_from_document_path(document_path: str) -> str | None:
    normalized = document_path.replace(os.sep, "/")
    if "/.planning/" in normalized or normalized.startswith(".planning/"):
        return "gsd"
    if "docs/superpowers/plans/" in normalized:
        return "superpowers"
    return None


def detect_framework(cwd: str, document_path: str | None = None,
                      conversation_signal: str | None = None,
                      isfile_fn=os.path.isfile, isdir_fn=os.path.isdir) -> str:
    if conversation_signal in ("gsd", "superpowers"):
        return conversation_signal
    if document_path:
        from_path = _framework_from_document_path(document_path)
        if from_path is not None:
            return from_path
    if isfile_fn(os.path.join(cwd, ".planning", "PROJECT.md")):
        return "gsd"
    if isdir_fn(os.path.join(cwd, "docs", "superpowers", "plans")):
        return "superpowers"
    return "unknown"


if __name__ == "__main__":
    doc_path = sys.argv[2] if len(sys.argv) > 2 else None
    print(detect_framework(sys.argv[1], document_path=doc_path))
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec_superpowers.TestDetectFrameworkSuperpowers -v 2>&1 | tail -20
```

Expected: PASS. Also re-run Plan 2's own GSD-marker test for this file (if present in
`tests/test_ai_kit_spec_gsd.py`) to confirm this change didn't regress it:

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd -v 2>&1 | tail -20
```

- [ ] **Step 5: Extend `ai-kit-spec-execute/SKILL.md` to pass the document path and conversation
  signal — CRITICAL finding (this task no longer merely confirms this file unchanged)**

Read `skills/ai-kit-spec-execute/SKILL.md` first — do not skip this step on the assumption of what
it says. Its current Step 1 ("Run `detect_framework(cwd)`") calls the OLD, marker-only signature and
must be updated to pass the new signal now that `detect_framework` accepts them. Replace it with:

```markdown
1. If the user just invoked a framework's own planning skill in this conversation (superpowers
   `writing-plans`/`brainstorming`, or a GSD planning skill), note it as `CONVERSATION_SIGNAL`
   (`"superpowers"`/`"gsd"`) — otherwise `CONVERSATION_SIGNAL` is unset.
2. Run `detect_framework(cwd, document_path=<the plan/phase path the user asked to execute, if
   any>, conversation_signal=CONVERSATION_SIGNAL)` from `detect_framework.py`.
3. `"gsd"` → delegate to `ai-kit-spec-execute-gsd`.
4. `"superpowers"` → delegate to `ai-kit-spec-execute-superpowers` (see that skill's own SKILL.md).
5. `"unknown"` → ask the user which framework generated this plan; do not guess.
```

This preserves every existing routing outcome for a project with only one marker present (`document_path`
absent falls straight through to the unchanged marker check) while fixing the CRITICAL finding: a
mixed-marker repository with an explicit, user-supplied superpowers plan path no longer silently
routes to GSD.

- [ ] **Step 6: Run skill-judge against the modified router skill (Cross-Document Consistency
  finding)**

Design spec §13 requires `skill-judge` "run against all 3 new skills (`ai-kit-spec-execute`,
`-gsd`, `-superpowers`) before considering them done." Task 4 (Step 2, above) already ran
`skill-judge` on `ai-kit-spec-execute-superpowers/SKILL.md`, but `ai-kit-spec-execute/SKILL.md`
itself is edited AFTER that, right here in this step — this task is the one that last touches that
file, so it is the one that must close this gate for it, rather than leaving it silently
unaddressed. Invoke `skill-judge` on `skills/ai-kit-spec-execute/SKILL.md`. Fix any finding before
proceeding to the commit below.

- [ ] **Step 7: Commit**

```bash
git add skills/ai-kit-spec-execute/detect_framework.py skills/ai-kit-spec-execute/SKILL.md \
        tests/test_ai_kit_spec_superpowers.py
git commit -m "feat(ai-kit-spec-execute-superpowers): make document path/conversation signal the router's primary evidence"
```

---

### Task 6: Live smoke test — resolve and dispatch a real trivial task through both modes

**Files:**
- Create: `skills/ai-kit-spec-execute-superpowers/SMOKE_TEST_RESULTS.md` (the verification
  artifact Step 4a writes AND commits, Step 4b appends to, and Step 5 commits again — HIGH finding:
  a purely verbal "it worked" leaves this task with nothing to commit, and nothing for a task
  reviewer to see).

Design spec §13's "End-to-end smoke test" requirement is two-part, and both parts are covered here,
by different steps: "one toy plan/phase run through the full loop (selection → dispatch →
heartbeat → completion) against at least one real external CLI" is Step 2 (below); "the adapter's
own `subagent-driven-development` integration" — a real native `Agent`-tool dispatch actually
carrying this adapter's resolved injection through that harness's own implementer-dispatch, report-
handling, and task-review contract — is Step 1b (Cross-Document Consistency finding: a prior
revision covered only the first half, leaving the native-mode harness integration itself
unverified by anything beyond `resolve-injection`'s own JSON output).

**Execution ownership (HIGH/CRITICAL findings): Step 1b is performed by the CONTROLLER, never by
Task 6's own implementer subagent — and the scratch environment Step 1b needs stays alive, and
addressable, until the CONTROLLER is done with it.** This plan's own header mandates
`superpowers:subagent-driven-development` (recommended) to execute it task-by-task; that skill's own
SKILL.md states its implementer "never dispatches subagents — not helpers, and never a reviewer" and
treats a worker-spawned reviewer as a defect to flag. Step 1b requires two real, independent
`Agent`-tool dispatches (an implementer, then a separate reviewer), so Task 6's own implementer
subagent cannot perform it without violating the very harness dispatching that subagent. The
CONTROLLER — the session actually running `subagent-driven-development`, i.e. whoever dispatches Task
6's implementer in the first place — is the one entity permitted to make those `Agent`-tool calls, so
it performs Step 1b directly instead.

Concretely: Task 6's implementer subagent performs Steps 1, 2, and 3 only, then Step 4a — it writes
`SMOKE_TEST_RESULTS.md` covering those three steps' outcomes, **records `$SMOKE_HOME` and `$SMOKE_CWD`
verbatim inside that file** (the CONTROLLER runs in a separate session/shell and has no other way to
learn `mktemp -d`'s output from the implementer's own shell), and **commits that draft** — the
implementer does NOT attempt Step 1b, but it DOES commit, because
`subagent-driven-development`'s own task review runs `scripts/review-package` over a commit range: a
task with zero implementer commits gives that reviewer nothing to see. Critically, the implementer
also does **not** delete `$SMOKE_HOME`/`$SMOKE_CWD` — Step 1b (below) still needs them live, on disk,
addressable by the exact paths recorded in the committed file. Once the implementer's Step 4a commit
is reviewed and accepted through this plan's normal task-review step, the CONTROLLER reads the
recorded paths back out of the committed `SMOKE_TEST_RESULTS.md`, re-exports them, and performs Step
1b directly in its own session against that still-live environment; it then appends Step 1b's
outcomes to `SMOKE_TEST_RESULTS.md` (Step 4b), deletes `$SMOKE_HOME`/`$SMOKE_CWD` now that nothing
further needs them (Step 4c — cleanup moves here, after Step 1b, not before it), and makes Task 6's
final commit (Step 5) itself, on top of the implementer's own commit. This preserves Step 1b's
original intent — a real end-to-end native `Agent`-tool dispatch through
`subagent-driven-development`'s own contract, task-reviewed like every other step's work — without
asking an implementer subagent to do something its own harness forbids, and without deleting the
environment the controller still needs.

**Resolve `$SHIM`/`$TOOLS_PY` first**, using the exact same real-path resolution Task 4's SKILL.md
Step 0 defines (this task runs standalone, not through that SKILL.md, so it repeats that same
executable check rather than assuming the variables already exist).

**Isolation (HIGH finding: every step below runs against a real but throwaway config/cache, never
the user's own `~/.config`/`~/.cache`).** Set this up once, in the FIRST `Bash` call of this task,
and re-source it (per Step 0's "every Bash call is a fresh shell" convention) at the top of every
later call in this task. **HIGH finding: isolate ONLY `XDG_CONFIG_HOME`/`XDG_CACHE_HOME` (this
adapter's own `cache_base`/`cfg_resolve` honor those, per `ai_kit_spec.cache`/`ai_kit_spec.
config_io`, confirmed by reading both) — never override `HOME` itself.** A prior revision replaced
`HOME` wholesale with a fresh, empty `mktemp -d` directory: that also isolates every OTHER
program's own home-relative state, including a real `codex` CLI's own credential/config store
(typically under `$HOME/.codex`), so Step 2's live `codex` dispatch would fail authentication
regardless of what command is configured — silently invalidating the whole point of a LIVE smoke
test. Leaving `$HOME` untouched keeps `codex`'s real, already-authenticated credentials reachable
while this adapter's own config/cache reads and writes stay fully confined to the throwaway dirs:

```bash
SMOKE_HOME="$(mktemp -d)"
SMOKE_CWD="$(mktemp -d)"
mkdir -p "$SMOKE_HOME/.config" "$SMOKE_HOME/.cache" "$SMOKE_CWD/.aikit"
export XDG_CONFIG_HOME="$SMOKE_HOME/.config" XDG_CACHE_HOME="$SMOKE_HOME/.cache"
printf 'SMOKE_HOME=%s\nSMOKE_CWD=%s\n' "$SMOKE_HOME" "$SMOKE_CWD"
```

**Do not delete `$SMOKE_HOME`/`$SMOKE_CWD` anywhere in Steps 1–3.** Per "Execution ownership" above,
the CONTROLLER's Step 1b runs later, in a separate session, against these same directories — Step 4a
records their paths into the committed `SMOKE_TEST_RESULTS.md` for the controller to re-export, and
only the controller's own Step 4c deletes them, after Step 1b and Step 4b are both done.

- [ ] **Step 1: Smoke test the `native_claude` mode end-to-end**

Write a real, local-only config with one native (`cli` omitted) candidate at the top of the ladder,
and a real one-task plan brief matching `writing-plans`' own `### Task N` format:

```bash
cat > "$SMOKE_CWD/.aikit/review-spec.toml" <<'EOF'
strategy = "local-only"

[policy]
ladder = ["claude/opus-5"]

[[reviewers]]
key = "claude/opus-5"
model = "opus"
vendor = "anthropic"
EOF
cat > "$SMOKE_CWD/task-1-brief.md" <<'EOF'
### Task 1: Smoke widget
**Files:**
- Create: `smoke_widget.py`
EOF
QUOTA_PATH="$(python3 "$TOOLS_PY" cache-path --kind quota)"
RESULT_JSON="$(python3 "$SHIM" resolve-injection --cwd "$SMOKE_CWD" \
  --task-file "$SMOKE_CWD/task-1-brief.md" --quota-path "$QUOTA_PATH")"
printf '%s\n' "$RESULT_JSON"
python3 -c "
import json, sys
result = json.loads(sys.argv[1])
assert result['mode'] == 'native_claude', result
assert result['model'] == 'opus', result
assert result['key'] == 'claude/opus-5', result
print('Step 1 PASS:', result)
" "$RESULT_JSON"
```

`result['model']` (`"opus"`) is exactly the string that plugs into the `Agent` tool's own `model`
parameter for the real implementer dispatch — record the printed `Step 1 PASS` line verbatim in
`SMOKE_TEST_RESULTS.md` (Step 4a).

- [ ] **Step 1b (CONTROLLER-PERFORMED — see "Execution ownership" above; never delegate this step to
  Task 6's implementer subagent): Full-loop smoke test — a REAL native `Agent`-tool dispatch through
  `subagent-driven-development`'s own contract (Cross-Document Consistency finding, design spec
  §13's "End-to-end smoke test": selection → dispatch → report handling → task review →
  completion)**

Trigger: perform this step yourself, in the controller's own session, only after Task 6's
implementer subagent has completed Steps 1, 2, and 3, written and **committed**
`SMOKE_TEST_RESULTS.md` for those three (Step 4a), and that commit has passed this plan's normal
task-review step. Before dispatching, read `$SMOKE_HOME`/`$SMOKE_CWD` back out of the committed
`SMOKE_TEST_RESULTS.md` (Step 4a recorded them verbatim) and re-export them in your own shell:

```bash
SMOKE_HOME="<value recorded in SMOKE_TEST_RESULTS.md>"
SMOKE_CWD="<value recorded in SMOKE_TEST_RESULTS.md>"
export XDG_CONFIG_HOME="$SMOKE_HOME/.config" XDG_CACHE_HOME="$SMOKE_HOME/.cache"
```

Both directories are still on disk — the implementer's Steps 1–3 never delete them, and cleanup is
now this task's Step 4c, which runs only after this step and Step 4b are both done.

Every step so far only proves `resolve-injection`'s own JSON output — it never actually hands that
resolution to `subagent-driven-development`'s real dispatch point the way Task 4's SKILL.md Step 3
describes, so the adapter's actual integration with that harness (not just its own CLI) has never
been exercised live. Do that now, using Step 1's SAME resolved candidate (`model="opus"`,
`mode="native_claude"`) and SAME brief:

1. **Dispatch a real `Agent` tool call** — `model="opus"` (Step 1's own resolved value), prompt:
   "Read the task brief at `$SMOKE_CWD/task-1-brief.md`. Implement it: create `smoke_widget.py` in
   `$SMOKE_CWD` containing a single function `def smoke_widget(): return 'ok'`. Write a detailed
   report of what you did to `$SMOKE_CWD/task-1-native-report.md` (this IS
   `subagent-driven-development`'s own real implementer contract: detailed evidence to the report
   file, a short status separately). Reply with ONLY a short status line at the very end of your
   reply: one of `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, `BLOCKED`." This is a real,
   in-process subagent dispatch — the exact mechanism `mode == "native_claude"` means (Task 4's
   SKILL.md Step 3), never simulated or mocked.
2. **Extract the status from the Agent tool's own reply text** using the SAME `rg` pattern Task 4's
   SKILL.md Step 3 defines (MEDIUM finding fix, above) — proving that extraction logic against a
   REAL model reply, not a hand-authored fixture string:

```bash
printf '%s\n' "$AGENT_REPLY_TEXT" | rg -o '\b(DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED|DONE)\b' | tail -1
```

   (`$AGENT_REPLY_TEXT` is the literal text the `Agent` tool call in point 1 returned — paste it
   into this command verbatim.) Confirm the extracted status is `DONE` (or `DONE_WITH_CONCERNS`);
   `BLOCKED`/`NEEDS_CONTEXT`/an empty extraction is a real smoke-test FAILURE, not a pass to work
   around — investigate and fix before continuing, per this task's own Step 4.
3. **Confirm report handling**: `$SMOKE_CWD/task-1-native-report.md` exists and is non-empty, and
   `$SMOKE_CWD/smoke_widget.py` exists and contains `smoke_widget` — the real deliverable, not a
   simulated one:

```bash
python3 -c "
import sys
assert __import__('os').path.getsize(sys.argv[1]) > 0, 'native report file is empty'
with open(sys.argv[2]) as f:
    assert 'smoke_widget' in f.read(), 'smoke_widget.py missing its own deliverable'
print('Step 1b dispatch PASS: real Agent-tool implementer wrote its report and deliverable')
" "$SMOKE_CWD/task-1-native-report.md" "$SMOKE_CWD/smoke_widget.py"
```

4. **Task review — a SECOND, independent real `Agent` tool call**, exactly matching
   `subagent-driven-development`'s own "3. Review the task" step's shape (a fresh subagent, never
   the same one that just implemented): `model="opus"`, prompt: "Read
   `$SMOKE_CWD/task-1-brief.md`, `$SMOKE_CWD/task-1-native-report.md`, and
   `$SMOKE_CWD/smoke_widget.py`. Confirm the deliverable satisfies the brief's own `**Files:**`
   block. Reply with exactly one word at the end: `APPROVED` or `CHANGES_NEEDED`." Confirm the
   reply's final word is `APPROVED` — this is **completion**: a real implementer dispatch, real
   report handling, and a real review pass, all through this adapter's own resolved injection,
   never simulated.

Append all of Step 1b's outcomes (the extracted status, the dispatch-PASS line, and the review
verdict) to the already-committed `SMOKE_TEST_RESULTS.md` yourself (Step 4b, below), then clean up
the scratch environment (Step 4c) — this is the step that closes the "adapter's
`subagent-driven-development` integration was never verified" gap; Steps 1–3 remain valuable for
isolating `resolve-injection`/`dispatch-task`'s own behavior in each mode, but none of them alone
proves the harness-integration contract this step does.

- [ ] **Step 2: Smoke test the `external_cli` mode end-to-end, including escalation**

Point the same isolated config at a real `codex` candidate (its execute-mode command was already
smoke-tested end-to-end in Plan 1, Task 5, Step 5 — this step exercises THIS adapter's own
`dispatch-task`/`classify-dispatch-failure` wrapper around that same real dispatch path). **HIGH
finding: the entry needs a real `command` template AND a real, live-verified model, or the quota
PROBE (never the execute-mode dispatch itself) fails before this step even gets that far** —
`ai_kit_spec.quota.probe_reviewer_quota`/`render_reviewer_command` (confirmed by reading both)
require a `cli`-set reviewer's own `command` field to render the probe invocation; a missing one
raises `ValueError` inside the probe, which `refresh_quota_cache` catches and classifies as
`available: False` with no live CLI ever actually invoked — a config that "worked" only because the
probe silently failed shut, not because codex was genuinely confirmed reachable. `command` below is
the exact real review-mode template `ai_kit_spec.commands._build_codex_command` renders (confirmed
live 2026-08-29), and `gpt-5.6-sol` is the model id already live-verified against a real installed
codex CLI (Plan 1, Task 5, Step 5) — never the placeholder `gpt-5.6-terra` id used elsewhere in this
plan's fully-mocked unit tests, which a real codex invocation would reject outright:

```bash
cat > "$SMOKE_CWD/.aikit/review-spec.toml" <<'EOF'
strategy = "local-only"

[policy]
ladder = ["codex/sol", "claude/opus-5"]

[[reviewers]]
key = "codex/sol"
model = "gpt-5.6-sol"
vendor = "openai"
cli = "codex"
command = "codex exec --sandbox read-only --skip-git-repo-check -m {model}"

[[reviewers]]
key = "claude/opus-5"
model = "opus"
vendor = "anthropic"
EOF
QUOTA_PATH="$(python3 "$TOOLS_PY" cache-path --kind quota)"
INJECTION_JSON="$(python3 "$SHIM" resolve-injection --cwd "$SMOKE_CWD" \
  --task-file "$SMOKE_CWD/task-1-brief.md" --quota-path "$QUOTA_PATH")"
printf '%s\n' "$INJECTION_JSON"
printf 'create a file named smoke.txt in the current directory containing exactly: OK\n' \
  > "$SMOKE_CWD/prompt.txt"
printf 'status: DONE|DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED\n' > "$SMOKE_CWD/format-block.md"
DISPATCH_RESULT_JSON="$(python3 "$SHIM" dispatch-task --injection-json "$INJECTION_JSON" \
  --prompt-file "$SMOKE_CWD/prompt.txt" --target-dir "$SMOKE_CWD" --heartbeat-interval 60 \
  --timeout 300 --format-block-file "$SMOKE_CWD/format-block.md" \
  --report-file "$SMOKE_CWD/task-1-report.md")"
printf '%s\n' "$DISPATCH_RESULT_JSON"
CLASSIFICATION="$(python3 "$SHIM" classify-dispatch-failure \
  --dispatch-result-json "$DISPATCH_RESULT_JSON")"
python3 -c "
import os, sys
assert os.path.isfile(os.path.join(sys.argv[1], 'smoke.txt')), 'smoke.txt was never created'
assert os.path.getsize(os.path.join(sys.argv[1], 'task-1-report.md')) > 0, 'report file is empty'
print('Step 2 dispatch PASS: smoke.txt created, report file non-empty, classification=' + sys.argv[2])
" "$SMOKE_CWD" "$CLASSIFICATION"
```

Confirm `$CLASSIFICATION` printed `"ok"` — record the printed lines in `SMOKE_TEST_RESULTS.md`.

Then force an escalation. **MEDIUM finding: setting `available: false` alone is not enough** —
`resolve-injection` always calls `refresh_quota_cache` internally, which re-probes (live!) any
entry that is missing, has no `checked_at`, or whose `checked_at` is older than
`QUOTA_TTL_SECONDS` — a forced `available: false` with no fresh `checked_at` is treated as stale
and gets silently refreshed away (probably back to the real, live-probed availability) before
resolution ever sees it, defeating the whole point of forcing the escalation. Write BOTH
`available: false` AND a fresh `checked_at` (current epoch seconds) for the top candidate's own
key, so `refresh_quota_cache` treats the forced entry as fresh and does not re-probe it:

```bash
QUOTA_PATH="$(python3 "$TOOLS_PY" cache-path --kind quota)"
python3 -c "
import json, sys, time
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
data['codex/sol'] = {'available': False, 'checked_at': time.time(),
                      'detail': 'smoke-test forced exhaustion'}
with open(path, 'w') as f:
    json.dump(data, f)
" "$QUOTA_PATH"
ESCALATED_JSON="$(python3 "$SHIM" resolve-injection --cwd "$SMOKE_CWD" \
  --task-file "$SMOKE_CWD/task-1-brief.md" --quota-path "$QUOTA_PATH")"
printf '%s\n' "$ESCALATED_JSON"
python3 -c "
import json, sys
result = json.loads(sys.argv[1])
assert result['mode'] == 'native_claude', result
assert result['key'] == 'claude/opus-5', result
print('Step 2 escalation PASS:', result)
" "$ESCALATED_JSON"
```

Confirm the printed `Step 2 escalation PASS` line shows resolution moved to `claude/opus-5` instead
of raising `QuotaExhaustedError` — the live proof CRITICAL finding "live quota selection and
escalation" is real, not just unit-tested against mocked `resolve_ladder_pick`. Record it.

- [ ] **Step 3: Smoke test that context-size filtering is actually live end-to-end**

CRITICAL finding: prior to this revision, `files_touched_sizes` was never populated from real
data, so a `context_limit`-tagged candidate could never actually be rejected on size in practice.
Prove it now is, against a real 4,000,000-byte file and two real candidates whose `context_limit`
differs by orders of magnitude:

```bash
python3 -c "
import sys
with open(sys.argv[1], 'w') as f:
    f.write('x' * 4_000_000)
" "$SMOKE_CWD/big_widget.py"
cat > "$SMOKE_CWD/task-2-brief.md" <<'EOF'
### Task 2: Big widget
**Files:**
- Modify: `big_widget.py`
EOF
cat > "$SMOKE_CWD/.aikit/review-spec.toml" <<'EOF'
strategy = "local-only"

[policy]
ladder = ["tiny-context/model", "big-context/model"]

[[reviewers]]
key = "tiny-context/model"
model = "opus"
vendor = "anthropic"
context_limit = 100

[[reviewers]]
key = "big-context/model"
model = "opus"
vendor = "anthropic"
context_limit = 5000000
EOF
QUOTA_PATH="$(python3 "$TOOLS_PY" cache-path --kind quota)"
CONTEXT_RESULT_JSON="$(python3 "$SHIM" resolve-injection --cwd "$SMOKE_CWD" \
  --task-file "$SMOKE_CWD/task-2-brief.md" --quota-path "$QUOTA_PATH")"
printf '%s\n' "$CONTEXT_RESULT_JSON"
python3 -c "
import json, sys
result = json.loads(sys.argv[1])
assert result['key'] == 'big-context/model', result
print('Step 3 PASS: low-context_limit candidate rejected, high-context_limit candidate won:', result)
" "$CONTEXT_RESULT_JSON"
```

Confirm the printed `Step 3 PASS` line and record it — the derived byte count from the real file,
not a caller-supplied fixture, is what drove the rejection.

- [ ] **Step 4a (Task 6's implementer subagent): Record Steps 1, 2, and 3's outcomes, and commit**

Write what was actually observed for Steps 1, 2, and 3 (pass/fail, and any discrepancy found and
fixed) to a real file at `skills/ai-kit-spec-execute-superpowers/SMOKE_TEST_RESULTS.md` — this draft
IS the "verification artifact" this step and Step 5 below commit. **Include `$SMOKE_HOME` and
`$SMOKE_CWD`'s own printed values verbatim** (a `## Scratch environment` section is enough — e.g.
`SMOKE_HOME=/tmp/tmp.xxxx` / `SMOKE_CWD=/tmp/tmp.yyyy`), so the controller can re-export them before
Step 1b. Do not attempt Step 1b — per "Execution ownership" above, that (and the append in Step 4b)
are the controller's own responsibility, performed next — but **do commit this draft**, because
`subagent-driven-development`'s own task review operates on real commits (`scripts/review-package`
over a commit range), and a task with nothing committed gives that reviewer nothing to see:

```bash
git add skills/ai-kit-spec-execute-superpowers/SMOKE_TEST_RESULTS.md
git commit -m "chore(ai-kit-spec-execute-superpowers): smoke-test draft — native_claude mode, external_cli mode + escalation, context-size filtering"
```

Leave `$SMOKE_HOME`/`$SMOKE_CWD` in place — do not delete them. The controller's Step 1b still needs
them, and cleanup does not happen until Step 4c, after Step 1b and Step 4b.

- [ ] **Step 4b (CONTROLLER-PERFORMED, after Step 1b): Append Step 1b's outcome**

Append Step 1b's outcomes (the extracted status, the dispatch-PASS line, and the review verdict) to
the `SMOKE_TEST_RESULTS.md` draft Step 4a already committed. Omitting Step 1b here would leave the
native-mode harness-integration gap Step 1b exists to close unverified in the one artifact this task
actually commits.

- [ ] **Step 4c (CONTROLLER-PERFORMED, after Step 4b): Clean up the isolated scratch environment**

Only now — after Step 1b has finished using `$SMOKE_HOME`/`$SMOKE_CWD` and Step 4b has recorded its
outcome — delete them:

```bash
rm -rf "$SMOKE_HOME" "$SMOKE_CWD"
```

- [ ] **Step 5 (CONTROLLER-PERFORMED): Final commit**

HIGH finding: this task's only artifact is `SMOKE_TEST_RESULTS.md` itself — Step 4a already committed
the draft (so a real task review had something to review); this final commit persists Step 4b's
append as a follow-up commit on top of it. Commit only that file, never an unconditional `git add -A`
that could sweep in unrelated dirty-worktree files:

```bash
git add skills/ai-kit-spec-execute-superpowers/SMOKE_TEST_RESULTS.md
if ! git diff --cached --quiet; then
  git commit -m "chore(ai-kit-spec-execute-superpowers): append native Agent-tool dispatch, report handling, and task-review verification through subagent-driven-development"
else
  printf 'Nothing to commit -- SMOKE_TEST_RESULTS.md unchanged since Step 4a''s commit.\n'
fi
```
