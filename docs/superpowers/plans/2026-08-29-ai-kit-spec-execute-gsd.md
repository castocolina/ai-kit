# ai-kit-spec-execute-gsd Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the GSD (Get Sh*t Done) adapter for `ai-kit-spec-execute`: a skill that resolves the best available model/CLI for a GSD phase's execution task, then dispatches it either through GSD's own native tiering (`model_overrides`/`model_profile`) or, if genuinely a real hook, GSD's `workflow.cross_ai_execution`/`cross_ai_command` — falling back to explicit user notification (never silent failure) when neither native tiering nor a real cross-provider hook can carry the chosen model.

**Architecture:** Task 1 is a live spike against a real GSD install that settles the one fact this entire adapter's shape depends on: is `cross_ai_command` a general arbitrary-shell-command hook, or a closed enum restricted to specific known providers? Every later task is written as two branches gated on that spike's finding — this plan cannot be collapsed to a single path before Task 1 runs, because the correct adapter architecture literally differs depending on the answer.

**Tech Stack:** Python 3 stdlib only, `unittest`, GSD's own `.planning/config.json` TOML/JSON config surface (read live during the spike to determine which it actually is).

**Spec:** `docs/superpowers/specs/2026-08-28-ai-kit-spec-execute-design.md` (§7, GSD adapter)

## Global Constraints

- Depends on Plan 1 (Foundation) being complete: `ai_kit_spec.execute_selection`, `ai_kit_spec.commands.build_execute_command`, `ai_kit_spec.dispatch.dispatch_with_heartbeat` must all exist and be tested before this plan's Task 2 onward.
- Never silently fail to honor the user's chosen model — if GSD's config surface can't carry it (native tier map too coarse, `cross_ai_command` unusable), the adapter must explicitly tell the user which model it fell back to and why (design spec §7, §12).
- `cross_ai_command`'s real behavior is disputed (WebFetch-sourced docs said "general hook"; user's own direct prior experience says "closed enum") — this plan trusts neither claim until Task 1 confirms one against a real install.
- GSD's built-in tier maps are hardcoded to claude/codex/gemini only, with static (staling) model IDs (confirmed during design brainstorming) — do not assume any other vendor is reachable through native tiering.

---

## File Structure

```
skills/ai-kit-spec-execute/                    (new skill directory)
  SKILL.md                                      (router: classifies GSD vs superpowers vs other, delegates)
skills/ai-kit-spec-execute-gsd/                 (new skill directory, this plan's primary deliverable)
  SKILL.md                                      (GSD-specific dispatch flow)
  ai_kit_spec_gsd/
    __init__.py
    gsd_config.py                               (read/write .planning/config.json, native-tier mapping)
    gsd_cross_ai.py                             (cross_ai_command usage -- shape depends on Task 1's finding)
tests/test_ai_kit_spec_gsd.py                   (new test file)
```

`ai-kit-spec-execute` (the router skill) is a thin dispatcher: detect which framework generated
the plan/phase (GSD's `.planning/` markers vs. superpowers' plan-file conventions), then delegate
to `ai-kit-spec-execute-gsd` or `ai-kit-spec-execute-superpowers` (Plan 3). This plan only builds
the GSD-specific half plus a minimal router stub (Task 6) — Plan 3 fills in the superpowers half
of the same router file.

---

### Task 1: SPIKE — confirm `cross_ai_command`'s real behavior against a live GSD install

**Files:** none created/modified — this is a research task, its deliverable is a finding recorded in this plan (Step 5) and used to gate every later task.

**Interfaces:** none — spike output is a plain-English finding, not code.

- [ ] **Step 1: Obtain a real GSD install to test against**

If a GSD-managed project already exists locally (check for `.planning/PROJECT.md` under any
known repo, or the ai-kit repo's own git history for a GSD reference), use it. Otherwise, install
GSD fresh in a scratch directory per its own README (`gsd-build/get-shit-done` or its current
relocated home — confirmed during design brainstorming that the canonical repo moved from
`gsd-build` to "Open GSD"/"GSD Core"; resolve the current canonical location first, do not
assume the old org name still resolves) and run its own init flow to produce a real
`.planning/config.json`.

- [ ] **Step 2: Read the real `.planning/config.json` schema and any `workflow.cross_ai_*` keys**

```bash
cat .planning/config.json 2>&1 | head -100
```

Look specifically for `workflow.cross_ai_execution`, `workflow.cross_ai_command`,
`workflow.cross_ai_timeout` keys or their equivalents. Note their actual current key names —
the design spec's names are provisional, sourced from a WebFetch summary that may be stale or
wrong.

- [ ] **Step 3: Read GSD's own source/docs for how it consumes `cross_ai_command`**

Locate the actual code path that reads this config value (grep the GSD source tree for
`cross_ai` or `cross_ai_command`). Answer definitively:
- Is the value a shell command string GSD executes verbatim (general hook), or
- Is it a closed enum/set of recognized provider identifiers GSD switches on internally (closed enum, matching the user's direct prior experience)?
- What does GSD do with the *output* of whatever this produces — does it expect a specific file (e.g. `SUMMARY.md`) to exist afterward, parse stdout directly, or something else?

- [ ] **Step 4: Attempt a live round-trip if the finding suggests a general hook**

Only if Step 3 concludes "general shell-command hook": configure `cross_ai_command` to invoke
a trivial script (`echo done`), run whatever GSD command actually consumes this
(`gsd-execute-phase` or equivalent) against a throwaway phase, and confirm GSD actually shells
out to it and reads the output the way Step 3 predicted. If Step 3 concludes "closed enum",
skip this — there is nothing to round-trip, document the enum's fixed value set instead.

- [ ] **Step 5: Record the finding**

Add a dated note directly to this plan file (edit this file, insert a subsection here) with:
one paragraph stating definitively which of the two it is, the exact config key names
confirmed live, and (if a hook) the exact invocation contract (env vars/args passed, expected
output shape) or (if an enum) the exact fixed value set GSD recognizes. This finding gates
which of Task 2's two branches every subsequent task follows — do not proceed to Task 2 until
this is written down.

---

### Task 2: `gsd_config.py` — read GSD's native tier map and resolve model_overrides

**Files:**
- Create: `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_config.py`
- Test: `tests/test_ai_kit_spec_gsd.py`

**Interfaces:**
- Consumes: nothing from Plan 1 directly (pure GSD-config-format parsing).
- Produces:
  - `read_gsd_config(path: str, read_fn=open) -> dict` — parses `.planning/config.json`, returns `{}` if the file doesn't exist (a project not yet GSD-configured is a valid, non-error state)
  - `resolve_native_tier(gsd_config: dict, phase_type: str) -> str | None` — looks up `model_overrides`/`model_profile`/built-in tier map for the given phase type in that priority order, returns the resolved model id string or `None` if nothing resolves
  - `NATIVE_TIER_VENDORS = {"claude", "codex", "gemini"}` — confirmed-live constant (design spec §7); any resolved model outside this vendor set could not have come from native tiering, a defensive assertion point for Task 4

- [ ] **Step 1: Write the failing tests**

```python
class TestReadGsdConfig(unittest.TestCase):
    def test_returns_empty_dict_when_file_missing(self):
        def raise_not_found(*a, **k):
            raise FileNotFoundError()
        self.assertEqual(gsd_config.read_gsd_config("/nonexistent", read_fn=raise_not_found), {})

    def test_parses_real_config_shape(self):
        import io
        fake = io.StringIO('{"model_overrides": {"backend": "claude-opus-5"}}')
        result = gsd_config.read_gsd_config("/x", read_fn=lambda *a, **k: fake)
        self.assertEqual(result["model_overrides"]["backend"], "claude-opus-5")


class TestResolveNativeTier(unittest.TestCase):
    def test_model_overrides_takes_priority(self):
        config = {"model_overrides": {"backend": "claude-opus-5"},
                   "model_profile": {"backend": "codex-tier-1"}}
        self.assertEqual(gsd_config.resolve_native_tier(config, "backend"), "claude-opus-5")

    def test_falls_back_to_model_profile(self):
        config = {"model_profile": {"backend": "codex-tier-1"}}
        self.assertEqual(gsd_config.resolve_native_tier(config, "backend"), "codex-tier-1")

    def test_returns_none_when_phase_type_unresolved(self):
        config = {"model_overrides": {"frontend": "claude-opus-5"}}
        self.assertIsNone(gsd_config.resolve_native_tier(config, "backend"))
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestReadGsdConfig \
  tests.test_ai_kit_spec_gsd.TestResolveNativeTier -v 2>&1 | tail -20
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""GSD's .planning/config.json read/resolve -- confirmed live shape from Task 1's spike."""
import json


NATIVE_TIER_VENDORS = {"claude", "codex", "gemini"}


def read_gsd_config(path: str, read_fn=open) -> dict:
    try:
        with read_fn(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, TypeError):
        return {}


def resolve_native_tier(gsd_config: dict, phase_type: str):
    for key in ("model_overrides", "model_profile"):
        value = gsd_config.get(key, {}).get(phase_type)
        if value is not None:
            return value
    return None
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestReadGsdConfig \
  tests.test_ai_kit_spec_gsd.TestResolveNativeTier -v 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(ai-kit-spec-execute-gsd): add gsd_config.py (native tier resolution)"
```

---

### Task 3: `gsd_cross_ai.py` — branch A (general hook) OR branch B (closed enum), per Task 1's finding

**Files:**
- Create: `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_cross_ai.py`
- Test: `tests/test_ai_kit_spec_gsd.py`

**Interfaces:**
- Consumes: `ai_kit_spec.commands.build_execute_command`, `ai_kit_spec.dispatch.dispatch_with_heartbeat` (Plan 1).
- Produces: `build_cross_ai_dispatch(gsd_config: dict, resolved_candidate: dict) -> dict | None` — returns a dispatch plan `{"mode": "cross_ai_hook" | "native_enum", ...}` or `None` when cross-provider dispatch isn't usable for this candidate at all (caller falls back to Task 4's native-tier path).

This task's implementation body is written AFTER Task 1 completes, using whichever branch below
matches Task 1's recorded finding. Both branches are specified now so the plan is complete
regardless of outcome — the implementer picks the one matching Task 1's Step 5 finding and
deletes the other branch's tests/code from this task, never implements both.

**Branch A — if Task 1 confirms `cross_ai_command` is a general shell-command hook:**

- [ ] **Step 1A: Write the failing tests**

```python
class TestBuildCrossAiDispatchGeneralHook(unittest.TestCase):
    def test_builds_hook_config_pointing_at_dispatch_module(self):
        gsd_config = {"workflow": {}}
        candidate = {"cli": "codex", "model": "gpt-5.6-terra", "key": "codex/gpt-5.6-terra"}
        result = gsd_cross_ai.build_cross_ai_dispatch(gsd_config, candidate)
        self.assertEqual(result["mode"], "cross_ai_hook")
        self.assertIn("gpt-5.6-terra", result["cross_ai_command"])

    def test_vendor_already_in_native_tier_set_returns_none(self):
        # already reachable via native tiering -- cross_ai hook is unnecessary overhead
        gsd_config = {"workflow": {}}
        candidate = {"cli": "claude", "model": "claude-opus-5", "key": "claude/claude-opus-5"}
        self.assertIsNone(gsd_cross_ai.build_cross_ai_dispatch(gsd_config, candidate))
```

- [ ] **Step 2A: Run to verify failure, then implement** (exact command construction depends on
  Task 1's Step 3 confirmed invocation contract — env vars vs. args, expected output file. Write
  the implementation using that confirmed contract; do not guess the shape.)

```python
"""Cross-provider dispatch via GSD's cross_ai_command hook -- confirmed a general shell-command
hook by Task 1's live spike (see this plan's Task 1, Step 5 finding)."""
from ai_kit_spec.commands import build_execute_command
from ai_kit_spec_gsd.gsd_config import NATIVE_TIER_VENDORS


def build_cross_ai_dispatch(gsd_config: dict, resolved_candidate: dict):
    if resolved_candidate["cli"] in NATIVE_TIER_VENDORS:
        return None
    execute_cmd = build_execute_command(resolved_candidate["cli"], target_dir="{target_dir}")
    filled = execute_cmd.format(model=resolved_candidate["model"], target_dir="{target_dir}")
    return {"mode": "cross_ai_hook", "cross_ai_command": filled}
```

- [ ] **Step 4A: Run tests to verify pass, commit**

**Branch B — if Task 1 confirms `cross_ai_command` is a closed enum:**

- [ ] **Step 1B: Write the failing tests**

```python
class TestBuildCrossAiDispatchClosedEnum(unittest.TestCase):
    def test_returns_native_enum_mode_when_candidate_vendor_in_enum(self):
        gsd_config = {}
        candidate = {"cli": "gemini", "model": "gemini-3.7-pro", "key": "gemini/gemini-3.7-pro"}
        result = gsd_cross_ai.build_cross_ai_dispatch(gsd_config, candidate)
        self.assertEqual(result["mode"], "native_enum")
        self.assertEqual(result["provider"], "gemini")

    def test_returns_none_when_candidate_vendor_outside_enum(self):
        # e.g. grok/opencode/cursor-agent are not part of the closed enum -- no hook path exists
        gsd_config = {}
        candidate = {"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast"}
        self.assertIsNone(gsd_cross_ai.build_cross_ai_dispatch(gsd_config, candidate))
```

- [ ] **Step 2B: Run to verify failure, then implement** (fill `_CLOSED_ENUM_PROVIDERS` with the
  exact fixed value set Task 1's Step 3 confirmed GSD recognizes — do not guess this set.)

```python
"""Cross-provider dispatch via GSD's closed cross_ai_command enum -- confirmed a fixed provider
set, not a general hook, by Task 1's live spike (see this plan's Task 1, Step 5 finding)."""

# Exact value set confirmed live in Task 1, Step 3 -- fill from that finding, not guessed.
_CLOSED_ENUM_PROVIDERS = {}  # e.g. {"gemini", "grok"} -- placeholder, replace per spike finding


def build_cross_ai_dispatch(gsd_config: dict, resolved_candidate: dict):
    if resolved_candidate["cli"] not in _CLOSED_ENUM_PROVIDERS:
        return None
    return {"mode": "native_enum", "provider": resolved_candidate["cli"]}
```

Note: `_CLOSED_ENUM_PROVIDERS = {}` is intentionally empty here because Task 1 has not yet run
as this plan document is written — the implementer fills this from Task 1's actual recorded
finding before writing Step 1B's tests (the test in Step 1B above assumes `"gemini"` is a member
as an example only; adjust both the test and the implementation together to match the real set).

- [ ] **Step 4B: Run tests to verify pass, commit**

```bash
git add -A
git commit -m "feat(ai-kit-spec-execute-gsd): add gsd_cross_ai.py (cross-provider dispatch)"
```

---

### Task 4: Adapter entry point — resolve candidate, dispatch native or cross-AI, explicit fallback notice

**Files:**
- Create: `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/adapter.py`
- Test: `tests/test_ai_kit_spec_gsd.py`

**Interfaces:**
- Consumes: `execute_selection.resolve_execute_candidates` (Plan 1), `gsd_config.resolve_native_tier`, `gsd_config.NATIVE_TIER_VENDORS`, `gsd_cross_ai.build_cross_ai_dispatch` (Tasks 2–3).
- Produces: `resolve_gsd_dispatch(candidates: list, phase_type: str, gsd_config: dict) -> dict` — returns exactly one of:
  - `{"mode": "native_tier", "model": str}` when GSD's own config already resolves a model for this phase type (native tiering wins outright — the user configured it, honor it)
  - `{"mode": "cross_ai_hook" | "native_enum", ...}` from Task 3, when the top-ranked *ai-kit-spec* candidate isn't natively reachable but cross-AI dispatch can carry it
  - `{"mode": "fallback_notice", "message": str, "model": str}` when neither path can carry the chosen candidate — `model` is whichever native-tier vendor model was substituted instead, `message` explicitly states the original choice and why it couldn't be honored

- [ ] **Step 1: Write the failing tests**

```python
class TestResolveGsdDispatch(unittest.TestCase):
    def test_native_tier_wins_when_gsd_already_configures_this_phase_type(self):
        gsd_config = {"model_overrides": {"backend": "claude-opus-5"}}
        result = adapter.resolve_gsd_dispatch([], "backend", gsd_config)
        self.assertEqual(result, {"mode": "native_tier", "model": "claude-opus-5"})

    def test_falls_back_with_explicit_notice_when_nothing_can_carry_the_candidate(self):
        candidates = [{"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast",
                        "task_affinity": None, "context_limit": None}]
        gsd_config = {}
        result = adapter.resolve_gsd_dispatch(candidates, "backend", gsd_config)
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertIn("grok", result["message"])
        self.assertIn(result["model"], gsd_config.get("model_profile", {}).values()
                       or ["claude", "codex", "gemini"])  # some native vendor substituted
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestResolveGsdDispatch -v 2>&1 | tail -20
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""Top-level GSD adapter dispatch resolution -- never silently drops the user's chosen model
(design spec §7, §12): native tiering wins if GSD already configures it, else cross-AI if
reachable, else an explicit fallback notice naming what was substituted and why."""
from ai_kit_spec_gsd.gsd_config import resolve_native_tier, NATIVE_TIER_VENDORS
from ai_kit_spec_gsd.gsd_cross_ai import build_cross_ai_dispatch


def resolve_gsd_dispatch(candidates: list, phase_type: str, gsd_config: dict) -> dict:
    native = resolve_native_tier(gsd_config, phase_type)
    if native is not None:
        return {"mode": "native_tier", "model": native}

    for candidate in candidates:
        cross_ai = build_cross_ai_dispatch(gsd_config, candidate)
        if cross_ai is not None:
            return cross_ai

    fallback_vendor = next(iter(NATIVE_TIER_VENDORS))
    top_choice = candidates[0]["key"] if candidates else "no candidate resolved"
    return {
        "mode": "fallback_notice",
        "model": fallback_vendor,
        "message": (
            f"ai-kit-spec-execute chose {top_choice} for this task, but GSD's config has no "
            f"native tier for phase type {phase_type!r} and no cross-AI dispatch path exists "
            f"for that candidate's provider. Falling back to GSD's default {fallback_vendor} "
            f"tiering instead -- update .planning/config.json's model_overrides to carry your "
            f"preferred model natively if this matters."
        ),
    }
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestResolveGsdDispatch -v 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(ai-kit-spec-execute-gsd): add adapter.py (dispatch resolution with explicit fallback)"
```

---

### Task 5: `SKILL.md` for `ai-kit-spec-execute-gsd`

**Files:**
- Create: `skills/ai-kit-spec-execute-gsd/SKILL.md`

**Interfaces:**
- Consumes: `adapter.resolve_gsd_dispatch`, `dispatch.dispatch_with_heartbeat` (Plan 1), the codegraph/tooling-guidance helpers from Plan 1 Tasks 3/7/8.

- [ ] **Step 1: Write the skill body**

Structure (Process pattern, per skill-judge's pattern table — this is a multi-step phased
workflow like `mcp-builder`, not a Mindset/Navigation skill):

```markdown
---
name: ai-kit-spec-execute-gsd
description: Dispatches a GSD (Get Sh*t Done) phase's execution to the best available model/CLI, honoring GSD's own native tiering when configured and falling back to cross-AI dispatch or an explicit substitution notice otherwise. Use when ai-kit-spec-execute detects a GSD-managed plan (.planning/ directory present) and needs to actually run gsd-execute-phase (or equivalent) with a resolved model.
---

# ai-kit-spec-execute-gsd

## Step 1: Read GSD config and resolve candidates

1. Read `.planning/config.json` via `ai_kit_spec_gsd.gsd_config.read_gsd_config`.
2. Read the runtime/quota caches and this phase's task-type classification (frontend/backend/
   etc — inferred from the phase's own docs, e.g. `NN-CONTEXT.md`) via
   `ai_kit_spec.execute_selection.resolve_execute_candidates`.
3. Call `ai_kit_spec_gsd.adapter.resolve_gsd_dispatch(candidates, phase_type, gsd_config)`.

## Step 2: Act on the dispatch mode

- `native_tier`: invoke GSD's own execution entry point unmodified — GSD already knows the
  model from its own config, nothing more to do here.
- `cross_ai_hook` / `native_enum`: write the resolved value into `.planning/config.json`'s
  `workflow.cross_ai_command` (or the confirmed equivalent key) before invoking GSD's execution
  entry point, so GSD's own dispatch picks it up.
- `fallback_notice`: print the returned `message` to the user BEFORE invoking GSD's execution
  entry point with the substituted `model` — never proceed silently.

## Step 3: Dispatch with heartbeat, using codegraph/tooling guidance when confirmed

Before dispatch: run `ai_kit_spec.detection.ensure_codegraph_registered` for whichever CLI is
about to execute, and `ai_kit_spec.tooling_guidance.build_tooling_guidance` to build any
confirmed-only tool-preference prose. Append that prose to the phase's own prompt content —
never fabricate guidance for a tool/registration that wasn't confirmed present this session.

Use `ai_kit_spec.dispatch.dispatch_with_heartbeat` for any cross-AI external-CLI path (native
GSD tiering dispatches through GSD's own subagent mechanism, unmodified — this wrapper's
heartbeat only applies to ai-kit-spec's own external-CLI dispatch, not to GSD's Claude-native
subagent path).

## Step 4: Resumable state on quota exhaustion

If dispatch fails with a quota-exhaustion signal (same `_UNAVAILABLE_SIGNALS`-style detection
as the review family's `probe_reviewer_quota`), write resumable state via
`ai_kit_spec.dispatch.write_resumable_state` (phase id, framework=gsd, candidates already
tried, iteration) before surfacing the failure — a future auto-wake mechanism resumes from this
file rather than restarting phase resolution from scratch.
```

- [ ] **Step 2: Run skill-judge against this skill**

Invoke `skill-judge` on `skills/ai-kit-spec-execute-gsd/SKILL.md`. Fix any finding before
proceeding — in particular check description quality (WHAT/WHEN/keywords) and that Step 2's
dispatch-mode branching reads as a decision tree, not vague prose.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "docs(ai-kit-spec-execute-gsd): add SKILL.md"
```

---

### Task 6: Router stub — `ai-kit-spec-execute`'s framework detection

**Files:**
- Create: `skills/ai-kit-spec-execute/SKILL.md`
- Create: `skills/ai-kit-spec-execute/detect_framework.py`
- Test: `tests/test_ai_kit_spec_gsd.py` (or a new `tests/test_ai_kit_spec_execute.py` — either is fine, this task creates whichever doesn't already exist from Plan 3 running first; if Plan 3 already created `tests/test_ai_kit_spec_execute.py`, add to it instead of creating a duplicate)

**Interfaces:**
- Produces: `detect_framework(cwd: str, isfile_fn=os.path.isfile, isdir_fn=os.path.isdir) -> str` — returns `"gsd"` when `.planning/PROJECT.md` exists, `"superpowers"` when a plan file matching superpowers' own naming convention is findable (Plan 3 defines the exact check), `"unknown"` otherwise.

- [ ] **Step 1: Write the failing tests**

```python
class TestDetectFramework(unittest.TestCase):
    def test_detects_gsd_via_planning_project_md(self):
        result = detect_framework.detect_framework(
            "/repo", isfile_fn=lambda p: p == "/repo/.planning/PROJECT.md",
            isdir_fn=lambda p: False)
        self.assertEqual(result, "gsd")

    def test_unknown_when_no_markers_present(self):
        result = detect_framework.detect_framework(
            "/repo", isfile_fn=lambda p: False, isdir_fn=lambda p: False)
        self.assertEqual(result, "unknown")
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestDetectFramework -v 2>&1 | tail -10
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""Framework detection for ai-kit-spec-execute's router. GSD's marker is confirmed
(.planning/PROJECT.md, per skills/ai-kit-spec-review-checklist/references/frameworks/gsd.md).
superpowers' marker is defined by Plan 3 (ai-kit-spec-execute-superpowers) -- this stub only
wires the GSD branch; Plan 3 fills in the superpowers check in this same function."""
import os


def detect_framework(cwd: str, isfile_fn=os.path.isfile, isdir_fn=os.path.isdir) -> str:
    if isfile_fn(os.path.join(cwd, ".planning", "PROJECT.md")):
        return "gsd"
    return "unknown"
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestDetectFramework -v 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Write the router `SKILL.md` stub**

```markdown
---
name: ai-kit-spec-execute
description: Routes execution of an already-generated plan/phase to the framework-specific ai-kit-spec-execute adapter (GSD or superpowers), based on which framework produced the plan. Use when the user asks to execute/run/implement a plan or phase and the generating framework isn't already known.
---

# ai-kit-spec-execute

1. Run `detect_framework(cwd)` from `detect_framework.py`.
2. `"gsd"` → delegate to `ai-kit-spec-execute-gsd`.
3. `"superpowers"` → delegate to `ai-kit-spec-execute-superpowers` (see that skill's own SKILL.md).
4. `"unknown"` → ask the user which framework generated this plan; do not guess.
```

- [ ] **Step 6: Run the full test suite and commit**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd 2>&1 | grep -E "^(Ran|OK|FAILED)"
git add -A
git commit -m "feat(ai-kit-spec-execute): add router skill and GSD framework detection"
```

---

### Task 7: End-to-end smoke test against a real GSD phase

**Files:** none created — verification-only task.

- [ ] **Step 1: Run the full adapter against a real (or realistic scratch) GSD phase**

Using the same GSD install from Task 1's spike, run `ai-kit-spec-execute-gsd`'s full flow
(Task 5's SKILL.md steps) against one real, small phase. Confirm:
- The correct dispatch mode is chosen (native_tier if config already has an override, else
  cross_ai/fallback per Task 4's logic).
- If `fallback_notice` fires, the message actually reaches the user/log before dispatch proceeds.
- Heartbeat output appears for any external-CLI dispatch path taken.

- [ ] **Step 2: Record the outcome and fix any discrepancy found**

Do not consider this plan complete if the live run diverges from Task 1's recorded contract —
fix `gsd_cross_ai.py`/`adapter.py` and re-run this step until it matches.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore(ai-kit-spec-execute-gsd): smoke-test verified against a live GSD phase"
```
