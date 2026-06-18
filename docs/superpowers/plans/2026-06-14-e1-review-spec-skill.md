# E1 — review-spec skill + framework-aware fix routing: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `/review-spec` from a slash command into a portable orchestrator **skill**, and route the *rewrite* stage to each document's originating framework's native authoring tool instead of always using the generic fixer.

**Architecture:** Two real deliverables, nothing else.
1. **Routing data model** — each framework profile's `revise_protocol` gains a per-archetype `routes:` list (archetype → rewrite handler). This is plain YAML data guarded by a Python validator test.
2. **The `review-spec` skill** — built/optimized with `/skill-creator:skill-creator` (migrating the existing `commands/review-spec.md` orchestration), carrying the new per-archetype routing in Step 3 + a transparent routing table, then graded with `/skill-judge:skill-judge`.

The reviewer (`reviewing-specs`) and the generic fixer (`applying-review-feedback`) are unchanged in role — only the rewrite stage is re-routed.

**Tech Stack:** Markdown skills (`SKILL.md`), YAML frontmatter profiles, Python 3 `unittest` + PyYAML 6.0.1 (installed), `skill-creator` + `skill-judge` skills. Tests run directly (`python3 tests/<file>.py`).

**Tooling (explicit, per request):** `/skill-creator:skill-creator` authors/optimizes the skill package; `/skill-judge:skill-judge` evaluates it. The framework-profile edits are plain data + a validator test (no skill tooling needed there).

**Grounding facts (from prior code evaluation):** only `gsd.md` uses `revise_protocol` today (small blast radius); PyYAML 6.0.1 is available; `tools/install.sh` links any dir-with-`SKILL.md` and prunes the stale command symlink automatically (so re-wiring is one verification line, not a task); a skill has no guaranteed `CLAUDE_PLUGIN_ROOT`, so the seed-dir path must be resolved by first-existing fallback (and the old `uz-kit` path is dead).

---

## Phase A — Routing data model (framework profiles)

This is the substrate FR-1.3 routes on. TDD against a profile validator. Self-contained and testable without the skill existing yet.

### Task A1: Profile validator + document `routes` in SCHEMA.md

**Files:**
- Create: `tests/test_framework_profiles.py`
- Modify: `skills/reviewing-specs/references/frameworks/SCHEMA.md`

- [ ] **Step 1: Write the validator test**

Create `tests/test_framework_profiles.py`:

```python
#!/usr/bin/env python3
"""Validate framework profile frontmatter, especially revise_protocol shape."""
import glob
import os
import re
import unittest

import yaml

_HERE = os.path.dirname(__file__)
_FRAMEWORKS_DIR = os.path.join(
    _HERE, "..", "skills", "reviewing-specs", "references", "frameworks"
)

_REQUIRED_FIELDS = ["id", "display_name", "doc_types", "lifecycle_order"]
_VALID_INVOKE = re.compile(r"^(skill:\S+|slash_command|surface)$")
_VALID_VALIDATE = re.compile(r"^agent:\S+$")
_ARCHETYPES = {"intent", "requirements", "design", "plan", "state", "constitution"}


def _profiles():
    """Yield (path, frontmatter_dict) for every profile file (not SCHEMA.md)."""
    for path in sorted(glob.glob(os.path.join(_FRAMEWORKS_DIR, "*.md"))):
        if os.path.basename(path) == "SCHEMA.md":
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        assert m, f"{path}: no YAML frontmatter block"
        yield path, yaml.safe_load(m.group(1))


def _check_route(path, route):
    assert isinstance(route, dict), f"{path}: route is not a mapping: {route!r}"
    assert route.get("archetype") in _ARCHETYPES, \
        f"{path}: route archetype invalid: {route.get('archetype')!r}"
    invoke = str(route.get("invoke", ""))
    assert _VALID_INVOKE.match(invoke), f"{path}: route invoke invalid: {invoke!r}"
    if invoke == "slash_command":
        assert route.get("command"), f"{path}: slash_command route needs a 'command'"
    if route.get("validate") is not None:
        assert _VALID_VALIDATE.match(str(route["validate"])), \
            f"{path}: validate must be 'agent:<name>', got {route['validate']!r}"


class TestFrameworkProfiles(unittest.TestCase):
    def test_required_fields_present(self):
        for path, fm in _profiles():
            for field in _REQUIRED_FIELDS:
                self.assertIn(field, fm, f"{path}: missing required field {field!r}")

    def test_revise_protocol_shape(self):
        for path, fm in _profiles():
            rp = fm.get("revise_protocol")
            if rp is None:
                continue
            self.assertIn(rp.get("mode"), ("direct_edit", "native_command"),
                          f"{path}: revise_protocol.mode invalid: {rp.get('mode')!r}")
            if "routes" in rp:
                self.assertIsInstance(rp["routes"], list, f"{path}: routes must be a list")
                self.assertTrue(rp["routes"], f"{path}: routes must be non-empty")
                for route in rp["routes"]:
                    _check_route(path, route)
            else:
                invoke = str(rp.get("invoke", ""))
                self.assertRegex(invoke, _VALID_INVOKE, f"{path}: flat invoke invalid")
                self.assertIsInstance(rp.get("applies_to", []), list,
                                      f"{path}: applies_to must be a list")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it — expect PASS against the current repo**

Run: `python3 tests/test_framework_profiles.py -v`
Expected: PASS. (Current `gsd.md` flat form is valid; other profiles have no `revise_protocol`.) This is the known-good baseline — if it fails, fix the validator, not the profiles.

- [ ] **Step 3: Document the `routes:` form in SCHEMA.md**

In `skills/reviewing-specs/references/frameworks/SCHEMA.md`, replace the section starting at `## \`revise_protocol\` — apply findings the framework's own way` (through the `Default (\`mode: direct_edit\`) keeps the existing fixer …` line) with:

````markdown
## `revise_protocol` — apply findings the framework's own way

Some frameworks own plan/spec generation through a dedicated authoring tool (superpowers authors
designs via `brainstorming` and plans via `writing-plans`; GSD regenerates a phase plan via
`/gsd-plan-phase <id> --reviews`). For those, editing files directly with the generic fixer can
desync the framework's state or break its conventions. When `mode: native_command`, the
orchestrator routes findings to the native tool instead of the direct-edit fixer.

Routing is **per archetype** via a `routes:` list — different archetypes of the same framework can
go to different tools (a superpowers `design` doc → `brainstorming`; a `plan` → `writing-plans`):

```yaml
revise_protocol:
  mode: native_command
  routes:
    - archetype: design                          # intent | requirements | design | plan
      invoke: "skill:superpowers:brainstorming"  # skill:<name> | slash_command | surface
      command: null                              # required when invoke: slash_command
      validate: null                             # optional "agent:<name>" run after a successful revise
      notes: "why the native path is preferred"
    - archetype: plan
      invoke: "skill:superpowers:writing-plans"
```

Route fields:
- `archetype` — which archetype this route handles. A report may flag findings in more than one
  archetype (fused docs, doc sets); each is routed independently.
- `invoke` —
  - `skill:<name>` — dispatch a subagent that invokes that skill to revise the doc; if the skill
    stalls on interactive input, the orchestrator **surfaces** the command instead (hybrid).
  - `slash_command` — run `command` via a slash-command tool if one is available this session; else
    **surface** the pre-filled command for the user to run.
  - `surface` — always hand the user the pre-filled `command` + findings report; never auto-run.
- `command` — the human-facing invocation (required for `slash_command`; shown when surfacing).
- `validate` — optional `agent:<name>`; after a successful native revise the orchestrator runs that
  agent to validate the regenerated doc before re-review.
- `notes` — why the native path is preferred.

An archetype **without** a matching route falls back to the direct-edit fixer
(`applying-review-feedback`). `mode: direct_edit` (or no `revise_protocol`) keeps the direct-edit
fixer for every archetype — most frameworks (generic) want this.

**Shorthand (flat) form** — still accepted for single-archetype profiles and learned cache
profiles: `mode` + `invoke` + `command` + `applies_to: [<archetype>, …]`. The orchestrator treats
it as one route per listed archetype. Prefer the explicit `routes:` list in curated seeds.
````

- [ ] **Step 4: Re-run the validator**

Run: `python3 tests/test_framework_profiles.py -v`
Expected: PASS (SCHEMA.md is skipped by the validator).

- [ ] **Step 5: Commit**

```bash
git add tests/test_framework_profiles.py skills/reviewing-specs/references/frameworks/SCHEMA.md
git commit -m "test(e1): framework-profile revise_protocol validator + routes schema docs"
```

### Task A2: superpowers routes (design→brainstorming, plan→writing-plans)

**Files:**
- Modify: `skills/reviewing-specs/references/frameworks/superpowers.md`
- Test: `tests/test_framework_profiles.py`

- [ ] **Step 1: Add the failing assertion** — append inside `class TestFrameworkProfiles`:

```python
    def test_superpowers_routes(self):
        profiles = {fm["id"]: fm for _, fm in _profiles()}
        sp = profiles["superpowers"]["revise_protocol"]
        self.assertEqual(sp["mode"], "native_command")
        by_arch = {r["archetype"]: r for r in sp["routes"]}
        self.assertEqual(by_arch["design"]["invoke"], "skill:superpowers:brainstorming")
        self.assertEqual(by_arch["plan"]["invoke"], "skill:superpowers:writing-plans")
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `python3 tests/test_framework_profiles.py TestFrameworkProfiles.test_superpowers_routes -v`
Expected: FAIL (`KeyError: 'revise_protocol'`).

- [ ] **Step 3: Add `revise_protocol`** to `superpowers.md` frontmatter, immediately after `filename_date_prefix: true` (before the closing `---`):

```yaml
revise_protocol:
  mode: native_command
  routes:
    - archetype: design
      invoke: "skill:superpowers:brainstorming"
      command: "Re-run the brainstorming skill on this design doc, addressing the review findings"
      validate: null
      notes: "The design doc (intent+requirements+design fusion) is authored by brainstorming;
        revise it there so its structure and house style stay intact rather than hand-editing
        with the generic fixer."
    - archetype: plan
      invoke: "skill:superpowers:writing-plans"
      command: "Re-run the writing-plans skill on this plan, addressing the review findings"
      validate: null
      notes: "Plans are authored by writing-plans; regenerate the plan addressing findings so the
        bite-sized TDD step structure and exact-paths discipline are preserved."
```

- [ ] **Step 4: Run the suite** — `python3 tests/test_framework_profiles.py -v` → all PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_framework_profiles.py skills/reviewing-specs/references/frameworks/superpowers.md
git commit -m "feat(e1): route superpowers design/plan rewrites to brainstorming/writing-plans"
```

### Task A3: GSD route migration + gsd-plan-checker validation

**Files:**
- Modify: `skills/reviewing-specs/references/frameworks/gsd.md`
- Test: `tests/test_framework_profiles.py`

- [ ] **Step 1: Add the failing assertion** — append inside `class TestFrameworkProfiles`:

```python
    def test_gsd_route_validates_with_checker(self):
        profiles = {fm["id"]: fm for _, fm in _profiles()}
        gsd = profiles["gsd"]["revise_protocol"]
        self.assertEqual(gsd["mode"], "native_command")
        plan = next(r for r in gsd["routes"] if r["archetype"] == "plan")
        self.assertEqual(plan["invoke"], "slash_command")
        self.assertEqual(plan["command"], "/gsd-plan-phase {phase_id} --reviews")
        self.assertEqual(plan["validate"], "agent:gsd-plan-checker")
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `python3 tests/test_framework_profiles.py TestFrameworkProfiles.test_gsd_route_validates_with_checker -v`
Expected: FAIL (current `gsd.md` is flat form, no `routes`).

- [ ] **Step 3: Replace the gsd.md `revise_protocol` block** — replace:

```yaml
revise_protocol:
  mode: native_command
  command: "/gsd-plan-phase {phase_id} --reviews"
  invoke: slash_command
  applies_to: [plan]
  notes: "The GSD planner owns each phase's plan structure and STATE.md; regenerate the phase
    plan by passing review findings to its own command rather than hand-editing, so the
    framework's phase/state conventions stay intact. {phase_id} comes from the plan's path
    (.planning/<phase>/) or ROADMAP.md."
```

with:

```yaml
revise_protocol:
  mode: native_command
  routes:
    - archetype: plan
      invoke: slash_command
      command: "/gsd-plan-phase {phase_id} --reviews"
      validate: "agent:gsd-plan-checker"
      notes: "The GSD planner owns each phase's plan structure and STATE.md; regenerate the phase
        plan by passing review findings to its own command rather than hand-editing. After
        regeneration, validate with the gsd-plan-checker agent before re-review. {phase_id} comes
        from the plan's path (.planning/<phase>/) or ROADMAP.md."
```

- [ ] **Step 4: Run the full suite** — `python3 tests/test_framework_profiles.py -v` → all PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_framework_profiles.py skills/reviewing-specs/references/frameworks/gsd.md
git commit -m "feat(e1): GSD plan rewrites via routes + gsd-plan-checker validation"
```

---

## Phase B — Build the `review-spec` skill with skill-creator

The orchestration logic already exists in `commands/review-spec.md`. `skill-creator` is used to **create the skill package** (structure, frontmatter, optimized triggering description, evals) while we **port the existing orchestration verbatim** and **graft the new routing**. The exact routing content below is the authoritative spec skill-creator must embed — it is not optional prose.

### Task B1: Scaffold the skill via skill-creator

**Files:**
- Create: `skills/review-spec/SKILL.md` (+ any `evals/` skill-creator generates)

- [ ] **Step 1: Invoke skill-creator with this brief**

Invoke the `skill-creator` skill (`/skill-creator:skill-creator`) to **create a new skill `review-spec`** by migrating `commands/review-spec.md`. Brief to give it:

- **Name:** `review-spec`. **Location:** `skills/review-spec/SKILL.md`.
- **Source to migrate:** the entire body of `commands/review-spec.md` (orchestration: Step 0 persist, Step 0.1 worktree root, Step 0.5 detect/resolve/classify, Step 0.6 lifecycle scope, Constants, the Loop digraph, Step 1 reviewer dispatch, Step 2 parse reviewer status, Step 5 surface, hard rules, cleanup) — **preserve verbatim** except the four adaptations below.
- **Adaptation 1 — frontmatter:** replace the command frontmatter with the skill frontmatter in Step 2 of this task. Ask skill-creator to **optimize the `description`** for triggering accuracy while keeping its routing summary.
- **Adaptation 2 — framing:** in `## Your Task`, restate "you are an orchestrator skill (invocable via `/review-spec` or by asking to review a spec/plan)" instead of "the user invoked the command".
- **Adaptation 3 — Step 3 routing:** replace the old single-mode Step 3 with the per-archetype routing block in **Task B2** (verbatim).
- **Adaptation 4 — Constants path + routing table:** apply the seed-dir resolution and routing table in **Task B3** (verbatim).
- **Evals:** have skill-creator generate/refresh `skills/review-spec/evals/` covering: (a) a superpowers plan with findings routes to `writing-plans` and surfaces if the subagent emits `Needs Input`; (b) a GSD plan routes to `/gsd-plan-phase --reviews` then `gsd-plan-checker`; (c) a generic doc uses `applying-review-feedback`; (d) ambiguous detection falls back to generic.

- [ ] **Step 2: Skill frontmatter** (skill-creator writes this; verify it matches):

```markdown
---
name: review-spec
description: Use when a design, spec, requirements, or plan document needs a clean-context review-and-fix loop before the next step. Orchestrates a reviewer subagent (reviewing-specs), then routes the rewrite by the document's originating framework — superpowers docs back to brainstorming/writing-plans, GSD plans to /gsd-plan-phase --reviews then gsd-plan-checker, everything else to the applying-review-feedback fixer. Persists in-memory docs to disk first; worktree- and framework-aware; scopes each doc to its lifecycle stage; loops until approved or the iteration cap. Triggered by "review-spec", "review my spec/plan", or passing document path(s).
---
```

- [ ] **Step 3: Verify the scaffold exists and preserved the orchestration**

Run: `test -f skills/review-spec/SKILL.md && grep -c "Step 0.1 — Resolve the codebase root" skills/review-spec/SKILL.md`
Expected: prints `1` (the migrated orchestration is present). Routing edits land in B2/B3.

- [ ] **Step 4: Commit**

```bash
git add skills/review-spec/
git commit -m "feat(e1): scaffold review-spec skill from command via skill-creator"
```

### Task B2: Per-archetype routing (Step 3)

**Files:** Modify `skills/review-spec/SKILL.md` — replace everything from `### Step 3 — Apply findings (when Issues Found, iter < cap)` up to **but not including** `### Step 4 — Parse fixer Status` with:

````markdown
### Step 3 — Apply findings (when Issues Found, iter < cap)

Save the reviewer's report to a temp file (`/tmp/review-spec-report-iter<N>.md`) so downstream subagents/skills can `Read` it.

**Resolve a revise route per flagged archetype.** A report may flag findings across more than one archetype (a fused superpowers design doc, or a doc set). For each archetype with at least one CRITICAL/HIGH/actionable finding, resolve its route from the profile's `revise_protocol`:

1. `revise_protocol.routes` exists → pick the entry whose `archetype` equals the flagged archetype.
2. Else a flat `revise_protocol` exists (shorthand `mode`/`invoke`/`command`/`applies_to`) and `applies_to` contains the archetype → treat it as one route `{archetype, invoke, command, validate: null}`.
3. Else (no `revise_protocol`, `mode: direct_edit`, or the archetype isn't covered) → the route is **direct edit**.

Dispatch per the route's `invoke`:

| `invoke` | Handler |
|---|---|
| (direct edit / archetype not covered) | **Step 3a** — generic `applying-review-feedback` fixer |
| `skill:<name>` | **Step 3b-skill** — hybrid native-skill revise; surface if it stalls |
| `slash_command` | **Step 3b-cmd** — run the command if a slash tool is available, else surface |
| `surface` | **Step 3b-surface** — always hand the user the pre-filled command, then stop |

If findings span a native-owned archetype AND a direct-edit archetype, handle the direct-edit ones via 3a and the native one via 3b in the same iteration, then re-review once; note both in the eventual Surface message. After ANY successful native revise (3b-skill / 3b-cmd) whose route declares `validate: agent:<name>`, run **Step 3c** before re-reviewing.

#### Step 3a — Generic fixer (direct edit)

Use the `Agent` tool, fresh subagent:

- `subagent_type`: `general-purpose`
- `model`: `sonnet`
- `description`: `review-spec iter N fixer`
- `prompt`: template below

Fixer prompt template — use VERBATIM:

```
You are the fixer.

Step 1: Invoke the Skill tool with skill name "applying-review-feedback" and follow it exactly.

Inputs:
- Document(s) to edit: <DOC_PATHS>
- Review report: <REPORT_TEMP_PATH>
- Codebase root: <CODEBASE_ROOT>
- FRAMEWORK_PROFILE_PATH: <FRAMEWORK_PROFILE_PATH>  (a file path on disk, or "none"). If a path,
  Read it and respect the framework's conventions while editing — keep EARS phrasing / RFC-2119
  SHALL, the task-checkbox format, delta section headers; never introduce implementation detail
  into a spec/requirements doc the framework keeps behavior-only.

Apply the skill. Edit the document(s) in place. Emit the structured Fix Summary at the end.

Do not assume any context outside what you read. Do not edit the review report.
```

Then parse the fixer's Status (Step 4).

#### Step 3b-skill — Hybrid native-skill revise (surface if it stalls)

The document was authored by a framework skill that owns its house style (superpowers `brainstorming` for design docs, `writing-plans` for plans). Revise through that skill so the structure survives — but those skills can expect human input, so fall back to surfacing if the subagent stalls.

Dispatch a fresh subagent:

- `subagent_type`: `general-purpose`
- `model`: `sonnet`
- `description`: `review-spec iter N native-revise (<SKILL_NAME>)`
- `prompt`: VERBATIM, substitute `<SKILL_NAME>` (the route's `invoke` minus the `skill:` prefix, e.g. `superpowers:writing-plans`), `<DOC_PATHS>`, `<REPORT_TEMP_PATH>`, `<CODEBASE_ROOT>`:

```
You are revising an existing document to address review findings, using its own authoring skill.

Step 1: Invoke the Skill tool with skill name "<SKILL_NAME>" and follow it.

Step 2: This is a REVISE, not a fresh authoring pass. Your inputs:
- Document(s) to revise (edit in place, SAME path): <DOC_PATHS>
- Review report (the findings to resolve): <REPORT_TEMP_PATH>
- Codebase root for grounding: <CODEBASE_ROOT>
Treat the existing document plus the findings as your brief. Regenerate or edit the document so
every CRITICAL and HIGH finding is resolved, preserving the skill's required structure and house
style. Write the result to the same path(s).

Step 3: If you cannot proceed without interactive input a human must provide (the skill needs a
decision you cannot infer from the document or the findings), DO NOT guess. Stop and emit:
### Status: Needs Input
followed by the one or two questions you would ask.
Otherwise, when done, emit exactly one of:
### Status: Edits Applied
### Status: No Edits

Do not assume any context beyond what you read.
```

Parse the subagent's `### Status:` line:

| Status | Action |
|---|---|
| `### Status: Edits Applied` | If the route has `validate`, run Step 3c; then increment iter and re-review (Step 1). |
| `### Status: Needs Input` | The authoring skill stalled. Go to **Step 3b-surface**, including the subagent's questions, and stop the loop. |
| `### Status: No Edits` | Loop ends. Surface (escalation — the authoring skill made no progress). |
| No Status line | Loop ends. Surface failure: "Native-revise subagent did not emit a Status line." |

#### Step 3b-cmd — Native slash-command revise

Following the route's `command` (substitute `{phase_id}`/ids from the doc path or roadmap):

- If a slash-command tool is available this session → invoke the `command` with the findings (report path), then if the route has `validate` run **Step 3c**, then re-review (Step 1).
- If no slash-command tool is available → fall back to **Step 3b-surface**.

#### Step 3b-surface — Surface the native command

Hand the user the pre-filled `command` + the report path and **stop the loop** (do not edit files yourself). Use the Surface "Native revise handed off" row. Example: `This plan is owned by the GSD planner. Run: /gsd-plan-phase 2 --reviews  (findings: /tmp/review-spec-report-iter<N>.md), then re-run /review-spec.`

#### Step 3c — Validate the regenerated doc (route has `validate: agent:<name>`)

The native planner regenerated the doc; validate with the framework's own checker before spending another review iteration. Dispatch the named agent:

- `subagent_type`: `<name>` (from `validate: agent:<name>`, e.g. `gsd-plan-checker`)
- `description`: `review-spec iter N validate (<name>)`
- `prompt`: `Validate the regenerated document(s) at: <DOC_PATHS>. Codebase root: <CODEBASE_ROOT>. Report whether the plan is sound and ready, or list the blocking problems.`

- Validator reports **sound** → proceed to re-review (Step 1).
- Validator reports **blocking problems** → **surface** to the user with the validator's reasons + the report path, and stop the loop (do not burn a review iteration on a plan its own checker rejects). Do **not** feed the validator's text into the reviewer prompt — the reviewer stays clean-context.
````

- [ ] **Verify no dangling references**

Run: `grep -nE "Step 3b\b" skills/review-spec/SKILL.md`
Expected: no bare `Step 3b` without a `-skill`/`-cmd`/`-surface` suffix in prose (the digraph's `Dispatch fixer subagent` node label is fine).

- [ ] **Commit**

```bash
git add skills/review-spec/SKILL.md
git commit -m "feat(e1): per-archetype rewrite routing (direct/native-skill/native-cmd+validate)"
```

### Task B3: Routing table, low-confidence fallback, skill-relative seed-dir

**Files:** Modify `skills/review-spec/SKILL.md`.

- [ ] **Step 1: Seed-dir resolution** — in `## Constants`, replace the `**Framework profile seeds dir** (\`SEEDS_DIR\`) …` bullet (the whole bullet) with:

````markdown
- **Framework profile seeds dir** (`SEEDS_DIR`) — resolve once to an **absolute** path. As a skill
  you are not guaranteed a `CLAUDE_PLUGIN_ROOT`; take the **first existing** of, in order:
  1. `${CLAUDE_PLUGIN_ROOT}/skills/reviewing-specs/references/frameworks/` (when set)
  2. `~/.claude/skills/reviewing-specs/references/frameworks/` (symlinked install — what `tools/install.sh` creates)
  3. the sibling of this skill: `<dir-of-this-SKILL.md>/../reviewing-specs/references/frameworks/`

  ```bash
  for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/reviewing-specs/references/frameworks}" \
           "$HOME/.claude/skills/reviewing-specs/references/frameworks"; do
    [ -d "$d" ] && { SEEDS_DIR="$d"; break; }
  done
  ```
  It holds the curated seed profiles `<id>.md` and `SCHEMA.md`. **Never reference these as a bare
  relative `references/frameworks/…`** — your CWD is the user's repo (often a worktree), not the kit.
````

- [ ] **Step 2: Low-confidence fallback** — at the end of `## Step 0.5`, before "Pass both `FRAMEWORK_PROFILE_PATH` and `ARCHETYPE` …", insert:

```markdown
**Low-confidence detection → generic.** If the framework stays ambiguous and the user cannot
disambiguate, set `FRAMEWORK_PROFILE_PATH = none` and route every archetype through the generic
`applying-review-feedback` fixer (Step 3a). State this in the final Surface message ("Framework
ambiguous — used the generic fixer.") so routing stays transparent.
```

- [ ] **Step 3: Routing table** — after the `## Hard rules for the orchestrator` table and before `## Cleanup`, insert:

```markdown
## Routing table — who rewrites what

Routing is data-driven from each profile's `revise_protocol.routes`. Seed-profile snapshot (FR-1.5):

| Framework (detected) | Archetype | Rewrite handled by | Mechanism |
|---|---|---|---|
| superpowers | design | `brainstorming` skill | hybrid subagent → surface if it stalls (Step 3b-skill) |
| superpowers | plan | `writing-plans` skill | hybrid subagent → surface if it stalls (Step 3b-skill) |
| GSD | plan | `/gsd-plan-phase {phase_id} --reviews`, then `gsd-plan-checker` | slash-command or surface (3b-cmd) + validate (3c) |
| GSD | intent / requirements / design | `applying-review-feedback` | direct edit (3a) |
| any other framework, generic, or `none` | all | `applying-review-feedback` | direct edit (3a) |
| ambiguous / low-confidence detection | all | `applying-review-feedback` | direct edit (3a) — Surface notes the ambiguity |

The reviewer (`reviewing-specs`) is identical for every framework; only the **rewrite** stage is
routed. To change routing, edit the framework profile's `revise_protocol.routes` — never hard-code
tools here.
```

- [ ] **Step 4: Sanity grep**

Run: `for n in brainstorming writing-plans gsd-plan-phase gsd-plan-checker applying-review-feedback uz-kit; do printf '%s: ' "$n"; grep -c "$n" skills/review-spec/SKILL.md; done`
Expected: each of the five tool names ≥ 1; `uz-kit: 0`.

- [ ] **Step 5: Commit**

```bash
git add skills/review-spec/SKILL.md
git commit -m "docs(e1): routing table, low-confidence fallback, skill-relative seed-dir"
```

---

## Phase C — Evaluate, retire the command, close out

### Task C1: Grade with skill-judge and iterate

- [ ] **Step 1: Run skill-judge** on `skills/review-spec/SKILL.md` via `/skill-judge:skill-judge`. (Optionally include `reviewing-specs` + `applying-review-feedback`, the trio it orchestrates.) Capture the scored findings.
- [ ] **Step 2: Address CRITICAL/HIGH findings** in `skills/review-spec/SKILL.md`; defer MEDIUM/LOW with a note. Re-run `/skill-judge` until no CRITICAL/HIGH remain.
- [ ] **Step 3: Run any skill-creator evals** generated in B1: follow skill-creator's eval-run instructions; confirm the four routing scenarios pass.
- [ ] **Step 4: Commit** (only if edits were made)

```bash
git add skills/review-spec/
git commit -m "chore(e1): address skill-judge findings on review-spec"
```

### Task C2: Retire the command and verify wiring

- [ ] **Step 1: Delete the migrated command**

```bash
git rm commands/review-spec.md
```

- [ ] **Step 2: Re-link (one step — install.sh handles it automatically)**

`install.sh` links any dir-with-`SKILL.md` and prunes broken symlinks pointing into the install dir, so it links the new skill and removes the old command symlink with no install.sh change.

Run: `bash tools/install.sh`
Expected: `ok` summary. Verify:

Run: `ls -ld ~/.claude/skills/review-spec; ls -l ~/.claude/commands/review-spec.md 2>&1`
Expected: the skill symlink resolves into this repo; the command path reports "No such file or directory".

- [ ] **Step 3: Full test run**

Run: `python3 tests/test_framework_profiles.py -v && bash tests/test_install.sh`
Expected: all green. (`test_install.sh` already covers generic skill linking — no skill-specific install test needed.)

- [ ] **Step 4: Commit**

```bash
git add commands/ skills/review-spec/
git commit -m "feat(e1): migrate /review-spec from command to skill"
```

### Task C3: Mark E1 done

- [ ] In `docs/prds/000-ai-kit-overhaul-requirements.md`, change the E1 status from `requirements captured · PRD pending` to `done → skills/review-spec/ + revise_protocol.routes (plan: docs/superpowers/plans/2026-06-14-e1-review-spec-skill.md)`.
- [ ] **Commit**

```bash
git add docs/prds/000-ai-kit-overhaul-requirements.md
git commit -m "chore(e1): mark E1 complete in requirements index"
```

---

## Self-Review

**Scope discipline:** Only two deliverables — the routing data model (Phase A) and the skill (Phase B), graded in Phase C. `install.sh` is a single verification line in C2, not a task. Nothing from E2–E5 is touched.

**Requirement coverage:** FR-1.1 (command→skill) — Phase B + C2. FR-1.2 (reuse detection) — Step 0.5 preserved. FR-1.3 (routing) — Phase A profiles + Step 3 (B2). FR-1.4 (reviewer unchanged) — `reviewing-specs` not edited. FR-1.5 (documented routing table) — B3.

**Tooling per request:** `/skill-creator` builds the skill (B1) + evals; `/skill-judge` grades it (C1).

**Placeholder scan:** Every test, profile block, and routing block is shown verbatim; the only delegated authorship (skill-creator) is given the exact content to embed.

**Name consistency:** Route fields (`archetype`/`invoke`/`command`/`validate`/`notes`) and skill names (`superpowers:brainstorming`, `superpowers:writing-plans`, `reviewing-specs`, `applying-review-feedback`) match across SCHEMA, profiles, validator, and Step 3. Step labels `3a`/`3b-skill`/`3b-cmd`/`3b-surface`/`3c` are used consistently.
```
