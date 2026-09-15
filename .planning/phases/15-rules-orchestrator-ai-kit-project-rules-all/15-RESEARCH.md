# Phase 15: Rules Orchestrator (ai-kit-project-rules-all) - Research

**Researched:** 2026-09-15
**Domain:** Python stdlib CLI orchestration — subprocess dispatch, JSON aggregation, cross-domain ordering, documentation-level (not code-level) hand-off to a sibling skill
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 (Invocation model):** The orchestrator invokes each of the 6 checkers via subprocess dispatch, parsing each one's stdout JSON — NOT via direct Python import across skill packages. Confirmed via the current codebase: every checker already exposes a standalone CLI entry script (e.g. `skills/ai-kit-agents-md-rules-checker/ai-kit-agents-md-rules-checker.py`) whose `check` subcommand does `print(json.dumps(check(repo_root), indent=2))` — this is the existing, working contract every checker already honors. Subprocess dispatch is also the only invocation model consistent with the "no skill imports another skill's package directly" convention (`.planning/intel/constraints.md` §"Shared package import convention") — a direct Python import would make the orchestrator the one skill in the family that violates its own family's independently-copyable design rationale.
— **Reversibility:** costly — switching to direct imports later means restructuring every checker's packaging/import surface, not a local tweak.

**D-02 (Partial-failure handling):** If one checker's subprocess invocation fails (non-zero exit, crash, malformed JSON on stdout), the orchestrator reports that failure inline as a labeled entry in the aggregated report and continues aggregating the other 5 checkers' real findings — it does NOT abort the whole run. Rationale: ROADMAP Success Criterion 1's "none silently dropped" would itself be violated by a crashed checker's domain vanishing from the report with no explanation; this also follows `PROJECT.md`'s confidence-labeling Core Value — "couldn't check this domain" must be visibly distinct from "checked, no findings," never conflated.
— **Reversibility:** reversible — switching to abort-on-any-failure later is a small control-flow change, not a migration.

**D-03 (already locked by ROADMAP + design spec):** The criticality-ordered aggregation (Success Criterion 2), the AGENTS.md-only `/agent-md-refactor` hand-off preservation (Success Criterion 3), the stubbed-integration-test shape (Success Criterion 4), and the cross-skill-merging-only-in-the-orchestrator boundary (Success Criterion 5) are accepted as written — no scope changes surfaced.

### Claude's Discretion
- Exact subprocess-invocation mechanics (parallel vs. sequential dispatch of the 6 checkers; timeout handling) — D-01/D-02 lock the model and the failure-reporting behavior, not the exact orchestration code shape.
- Exact schema for a D-02 failure entry in the aggregated report (e.g. `{"domain": "docker", "error": "...", "status": "failed"}` vs. some other shape) — left to the planner, as long as it's visibly distinct from a normal empty-findings entry.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within Phase 15's scope. `cross_reference_todos` found the same 3 historical todos (`resolves_phase: 6/7/8`) already confirmed not live candidates during Phases 9-14's discussions.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| REQ-rules-all | A new skill `ai-kit-project-rules-all` (orchestrator) runs all 6 checkers' `check`/`remediate` against one target repo and aggregates into one criticality-ordered report; keeps the existing `/agent-md-refactor` hand-off for AGENTS.md-domain findings only. | Full CLI contract for all 6 sibling checkers documented (Code Examples); shared criticality vocabulary and `build_remediation` mechanics documented (Architecture Patterns, Don't Hand-Roll); the existing Step A/B/C hand-off mechanism fully quoted and cross-referenced (Architecture Patterns, Pattern 2); D-02 failure-isolation schema recommended (Open Questions #2); SC4's testability requirement addressed via the dispatch/aggregate separation (Architecture Patterns, Pattern 1; Validation Architecture) |
</phase_requirements>

## Summary

Phase 15 does not introduce any new external technology. It is a pure-Python,
stdlib-only orchestration layer over six already-shipped sibling skills
(`ai-kit-project-rules-agents/makefile/precommit/arch/docker/cicd`), all of
which are complete, tested, and expose an identical CLI contract:
`python3 <skill-dir>/<skill-name>.py check|remediate [repo_root]`, printing
JSON to stdout. Every finding across all six domains already carries an
integer `criticality` field drawn from one shared vocabulary
(`skills/_shared/ai_kit_rules_common/criticality.py`:
`CRITICALITY_CRITICAL=1`, `CRITICALITY_HIGH=2`, `CRITICALITY_MEDIUM=3`,
`CRITICALITY_ADVISORY=4`, ascending = most severe first). Each sibling's
`remediate` subcommand already runs that finding through the shared
`ai_kit_rules_common.remediation.build_remediation()` helper
(`skills/_shared/ai_kit_rules_common/remediation.py:34-122`), producing a
per-domain `{"remediate": [...], "blocked": [...]}` payload whose entries are
already criticality-sorted and already carry a `kind` field that uniquely
identifies the owning domain (`"workflow"` for the agents skill, `"makefile"`,
`"precommit"`, `"arch"`, `"docker"`, `"cicd"` for the rest).

This means Phase 15's real work is narrow: (1) subprocess-dispatch each of
the six sibling entrypoints against the same `repo_root`, (2) parse each
one's stdout JSON, tolerating any individual failure per D-02, (3) merge the
six already-per-domain-sorted `remediate`/`blocked` lists into ONE list and
re-sort it by the same `criticality` integer field (a stable sort over a
list concatenated in a fixed, deterministic domain order — not
invocation-completion order), and (4) for `"workflow"`-kind entries only,
point at the already-fully-documented Step A/B/C hand-off that
`ai-kit-project-rules-agents/SKILL.md` already specifies for
`/agent-md-refactor` — a documentation cross-reference, not new code, since
`/agent-md-refactor` "has no CLI, no importable/callable interface"
(`skills/ai-kit-project-rules-agents/SKILL.md`, "Wrap mechanism" section,
read this session).

The single open design question this research surfaces (see Open Questions)
is whether the orchestrator's per-checker subprocess calls should invoke
`remediate` (get pre-built, pre-sorted, `auto_apply`-annotated payloads) or
`check` (get raw findings and reimplement the recommendation/needs_research
branching itself). All direct evidence — the shared builder's own docstring,
CONTEXT.md's Integration Points note, and coverage analysis below — points
at invoking `remediate`, but ROADMAP's SC1/SC4 wording literally says
"check", so this is flagged for planner/user confirmation rather than
silently assumed.

**Primary recommendation:** Subprocess-invoke each sibling's `remediate`
subcommand (which internally calls that sibling's own `check`, so "check" is
still literally invoked, just not as a separate subprocess call), merge the
six `{"remediate": [...], "blocked": [...]}` payloads into one, re-sort the
combined `remediate` list by `criticality` ascending using a fixed domain
concatenation order for deterministic tie-breaks, and separate this pure
merge/sort logic into its own function that takes already-parsed dicts —
never spawning a subprocess itself — so SC4's stubbed integration test can
call it directly with six hand-built fixture payloads.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-domain rule checking (17 workflow rules, Makefile shape, pre-commit parity, arch-test wiring, Docker conventions, CI reuse) | API/Backend-equivalent (already-shipped sibling skill process) | — | Already owned by each of the 6 existing checker skills; Phase 15 never re-implements or touches their logic. |
| Subprocess dispatch + JSON parsing of 6 sibling outputs | New orchestrator CLI module (`ai_kit_project_rules_all/cli.py` or similar) | — | Only this phase's skill has the responsibility to call all 6; none of the siblings know about each other. |
| Partial-failure isolation (D-02) | New orchestrator CLI module | — | Must not let one crashed subprocess abort the whole run; distinct from a domain's real empty-findings state. |
| Cross-domain criticality merge/sort (SC2) | New orchestrator pure-function module | — | Explicitly NOT the shared `remediation.py`'s job (constraints.md "Cross-skill remediation merging ownership") — this is the one new piece of logic this phase owns outright. |
| AGENTS.md-domain hand-off to `/agent-md-refactor` | Existing `ai-kit-project-rules-agents` skill's documented Step A/B/C (SKILL.md instruction text) | Orchestrator SKILL.md (cross-reference only) | Preserved unchanged per Phase Boundary — the orchestrator's SKILL.md points at the existing sequence rather than reimplementing it. |
| Report rendering / no-auto-apply enforcement for the other 5 domains | New orchestrator SKILL.md (instruction-level, no file-writing code) | — | Family-wide "detect and report only" scope boundary; the orchestrator inherits it and never gains new write capability. |

## Standard Stack

### Core

No new external packages. This phase is Python stdlib-only, matching every
sibling in the family — every one of the 6 checkers' modules imports only
`os`, `re`, `sys`, `json`, `subprocess` (test-only), `collections`, and each
other's own package/the shared `_shared` package
`[VERIFIED: skills/ai-kit-project-rules-*/ai_kit_project_rules_*/cli.py, read this session — every cli.py's import block lists only stdlib modules plus intra-family imports]`.
The project's own AGENTS.md states the stdlib-only constraint explicitly for
its designated runtime surfaces
(`AGENTS.md:29-31`, read this session: "Runtime code (`tools/status-line.py`,
`tools/statusline-doctor.py`, `tools/setup.py`'s non-wizard paths) stays
**stdlib-only** — no third-party imports, ever.") — the rules-checker family
is not literally named in that list, but every existing sibling in the
family already follows it as an unbroken pattern
`[VERIFIED: skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py:1-16, skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/cli.py:1-15 — both read this session, both stdlib-only import blocks]`.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `subprocess` (stdlib) | n/a | Dispatch each of the 6 sibling entrypoints | D-01 locks subprocess dispatch over direct import, matching every sibling's own subprocess-CLI test pattern (`tests/test_ai_kit_project_rules_cicd.py:22-25,839-840`, read this session) |
| `json` (stdlib) | n/a | Parse each sibling's stdout | Every sibling already emits `json.dumps(..., indent=2)` on stdout for `check`/`remediate` |
| `unittest` (stdlib) | n/a | Test framework | Project-wide convention — no `pytest` anywhere in this repo `[VERIFIED: Makefile:46, read this session — "python3 -m unittest tests.test_..." for every existing suite, including all 6 sibling test modules]` |

### Supporting

None needed. No YAML/TOML parsing, no HTTP, no new file-format readers —
those already live in the 6 sibling skills and in `skills/_shared/`, which
the orchestrator does not import.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| subprocess dispatch (D-01, locked) | Direct Python import of each sibling's `cli` module | Rejected in CONTEXT.md — would violate the "no skill imports another skill's package directly" convention (`.planning/intel/constraints.md` "Shared package import convention") and make every checker no longer independently copyable |
| Fixed sequential dispatch | `concurrent.futures.ThreadPoolExecutor` for parallel dispatch | Left to planner (CONTEXT.md Claude's Discretion). Either is fine functionally since results must be reassembled into a fixed domain order before sorting regardless of completion order — parallel dispatch only buys wall-clock speed, six subprocesses spawning `python3` are I/O/CPU-light enough that sequential is simpler to reason about and to keep deterministic in tests |

**Installation:** None — no new dependencies to add to `pyproject.toml`,
`uv.lock`, or anywhere else.

## Package Legitimacy Audit

Not applicable — this phase installs zero external packages (stdlib-only,
consistent with every sibling skill in the family). Skipping the gate per
this section's own "Required whenever this phase installs external
packages" condition.

## Architecture Patterns

### System Architecture Diagram

```
                         orchestrator SKILL.md / CLI
                                    │
                                    ▼
                    ┌────────────────────────────┐
                    │  dispatch_all(repo_root)    │   <- I/O boundary
                    │  (subprocess per domain,    │      (real subprocess.run,
                    │   fixed domain order,       │       6x python3 ... .py
                    │   D-02 failure isolation)   │       remediate <repo_root>)
                    └──────────────┬───────────────┘
                                   │  {domain: parsed-JSON-or-error, ...}
                                   ▼
        ┌───────────┬───────────┬───────────┬───────────┬───────────┬───────────┐
        │  agents    │ makefile  │ precommit │   arch    │  docker   │   cicd    │
        │ (workflow) │           │           │           │           │           │
        └─────┬──────┴─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┘
              │            │           │           │           │           │
              ▼            ▼           ▼           ▼           ▼           ▼
       {"remediate":[...], "blocked":[...]}  x 6  (already criticality-sorted PER DOMAIN,
                                                    each entry already carries "kind")
                                   │
                                   ▼
                    ┌────────────────────────────┐
                    │  aggregate(domain_results)  │   <- pure function, no I/O
                    │  concat in fixed domain     │      (SC4's stub target)
                    │  order, stable-sort combined│
                    │  remediate list by          │
                    │  criticality ascending      │
                    └──────────────┬───────────────┘
                                   │  {"remediate":[...ONE ordered list...],
                                   │   "blocked":[...], "failed":[...D-02...]}
                                   ▼
                    ┌────────────────────────────┐
                    │  render aggregated report   │
                    │  inline (all 6 domains)     │
                    └──────────────┬───────────────┘
                                   │
                       kind == "workflow"?
                          │                │
                         yes               no
                          │                │
                          ▼                ▼
        follow ai-kit-project-rules-agents/   report inline only —
        SKILL.md's existing Step A/B/C         no auto-apply, no file
        hand-off to /agent-md-refactor         write, ever (SC3)
        (documentation cross-reference,
        not new code — /agent-md-refactor
        has no CLI/importable interface)
```

### Recommended Project Structure

Matches every sibling skill's established shape exactly
`[VERIFIED: skills/ai-kit-project-rules-cicd/, skills/ai-kit-project-rules-docker/ directory listings, read this session]`:

```
skills/ai-kit-project-rules-all/
├── SKILL.md                                  # entrypoint-resolution, aggregation contract,
│                                              # Step A/B/C hand-off cross-reference (documentation, no new code)
├── ai-kit-project-rules-all.py               # thin entry script: sys.exit(main(sys.argv[1:]))
├── ai_kit_project_rules_all/
│   ├── __init__.py                           # NOT the shared-path-append pattern (no _shared import needed —
│   │                                          # see "Integration Points" in CONTEXT.md, confirmed below)
│   ├── cli.py                                # argparse-free check/remediate dispatch, matching every sibling
│   ├── dispatch.py                           # dispatch_all(repo_root) — the I/O boundary, subprocess.run x6,
│   │                                          # D-02 failure isolation, fixed domain order
│   └── aggregate.py                          # aggregate(domain_results: dict) -> dict — pure function,
│                                              # cross-domain criticality merge/sort, SC4's stub target
tests/
└── test_ai_kit_project_rules_all.py          # unittest.TestCase, stubs aggregate() with 6 hand-built
                                               # fixture payloads (SC4) + a lighter subprocess smoke test
```

### Pattern 1: Separate the I/O boundary from the pure aggregation logic
**What:** `dispatch_all()` (subprocess calls) and `aggregate()` (merge/sort)
are two separate functions/modules, never fused into one.
**When to use:** Always, for this phase — SC4 requires "an integration-style
test [that] stubs all 6 checkers' ... output and asserts the
aggregation/ordering logic, without needing every individual checker's full
logic re-exercised inside that test." That is only achievable if `aggregate()`
takes already-parsed dicts as input and never itself shells out.
**Example:**
```python
# Illustrative shape, not verbatim from any read file — matches the CLI
# dispatch style every sibling module already uses (main(argv) -> int,
# argparse-free, json.dumps(..., indent=2) on stdout for check/remediate).
def aggregate(domain_results: dict[str, dict]) -> dict:
    """domain_results: {"agents": {...}, "makefile": {...}, ...} — each
    value already the {"remediate": [...], "blocked": [...]} shape a
    sibling's own `remediate` subcommand returns, OR a D-02 failure marker.
    Never calls subprocess. This is what the SC4 test targets directly."""
    ...

def dispatch_all(repo_root: str) -> dict[str, dict]:
    """The only function in this skill that calls subprocess.run. Iterates
    the six domains in one FIXED, hardcoded order (never dict/glob order,
    never completion order) so aggregate()'s stable-sort tie-breaks are
    reproducible across runs and across sequential-vs-parallel dispatch."""
    ...
```

### Pattern 2: Preserve the AGENTS.md hand-off as a documentation cross-reference, not code
**What:** The orchestrator's `SKILL.md` instructs the executing agent, for
`"workflow"`-kind entries in the aggregated report, to follow
`ai-kit-project-rules-agents/SKILL.md`'s own "Wrap mechanism" section
(Step A/B/C) verbatim — resolved via the SAME host-neutral candidate-list
pattern every sibling already uses to find its own entrypoint
`[VERIFIED: skills/ai-kit-project-rules-agents/SKILL.md through skills/ai-kit-project-rules-precommit/SKILL.md, all 6 "Resolve the entrypoint" sections, read this session — identical 5-candidate for loop pattern, only the skill-name string and script filename change]`.
**When to use:** Only for the AGENTS.md domain (SC3). Every other domain's
findings are surfaced inline in the aggregated report with no hand-off, no
apply step, nothing beyond text.
**Example:** See `skills/ai-kit-project-rules-agents/SKILL.md`'s "Wrap
mechanism" section (read this session, quoted in full context above) — Step
A (near-miss confirmation owned by the wrapping skill), Step B (assemble one
ordered list: every `auto_apply: true` entry plus every confirmed near-miss,
most-critical-first), Step C (invoke `/agent-md-refactor` exactly once,
treating the list's `summary` strings as Phase 2/3 input for that skill's
own five-phase refactor). The orchestrator's SKILL.md should name this
exact sequence for its `"workflow"`-kind subset rather than restating it,
mirroring how `ai-kit-project-rules-agents/SKILL.md` itself points at
`rules.py` "rather than restating the rule text" for its own ruleset
reference section.

### Anti-Patterns to Avoid
- **Reimplementing `build_remediation`'s branching logic inside the
  orchestrator:** every sibling's `remediate` subcommand already returns
  the fully-built `{"remediate": [...], "blocked": [...]}` payload. There is
  no reason for the orchestrator to re-derive `auto_apply`/`recommendation`
  branching from raw `check` output — that would duplicate logic the
  shared `remediation.py` already owns, and would NOT be "the orchestrator's
  own cross-skill merging" (SC5) but a second, drifting copy of
  single-domain logic that constraints.md explicitly reserves for
  `remediation.py`.
- **Non-deterministic domain ordering:** never build the merge input from
  `os.listdir()`, dict iteration order, or subprocess-completion order if
  dispatch is parallelized — always concatenate in one fixed, explicit
  domain list (e.g. `("agents", "makefile", "precommit", "arch", "docker",
  "cicd")`) before the stable sort, or two runs of the same repo state can
  silently reorder same-criticality findings across domains.
- **Auto-applying anything for non-workflow domains:** `auto_apply: true` on
  a `makefile`/`precommit`/`arch`/`docker`/`cicd`-kind `remediate` entry
  means "safe to insert without a human confirming near-miss text" *inside
  that domain's own future tooling* — it is NOT a green light for the
  orchestrator to write to the target repo. SC3 is explicit: every domain
  except AGENTS.md is "inline and report-only, with no auto-apply."
- **Aborting the whole run on one checker's crash (D-02, locked):** a
  non-zero exit, uncaught exception, or malformed stdout JSON from any one
  of the 6 subprocess calls must produce a labeled failure entry for that
  domain and let the other 5 proceed — never a bare exception that kills
  the orchestrator's own process.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Criticality vocabulary / ordering scale | A new orchestrator-local set of severity constants | The existing `CRITICALITY_CRITICAL/HIGH/MEDIUM/ADVISORY = 1/2/3/4` values already embedded as integers on every finding from every sibling's JSON output | `skills/_shared/ai_kit_rules_common/criticality.py:23-26` (read this session) states this vocabulary exists specifically so "Phase 15's orchestrator orders findings across six domains using this vocabulary" — a private copy would let it drift |
| Per-domain recommendation/near-miss branching | A second `build_remediation`-equivalent inside the orchestrator | Each sibling's own `remediate` subcommand (which already calls the shared builder internally) | `remediation.py:34-122`'s own docstring says this exact branching is scoped "to one skill's own `remediate` output only" — Phase 15's job is the list-of-lists merge on top, not re-deriving the per-finding classification |
| AGENTS.md file editing / structural refactor | A new Markdown-rewriting routine inside the orchestrator | `/agent-md-refactor`, invoked via the exact hand-off `ai-kit-project-rules-agents/SKILL.md` already documents | That skill "has no CLI, no importable/callable interface" by design — its hand-off is always "a documented instruction sequence for whichever agent is executing this skill, never code" (`SKILL.md`, "Wrap mechanism" section, read this session) |

**Key insight:** every piece of domain logic Phase 15 might be tempted to
duplicate — criticality scoring, remediation-list building, AGENTS.md
editing — already exists and is already reachable through a documented,
stable interface (JSON-on-stdout for the first two, a five-phase Markdown
skill for the third). The orchestrator's entire novel surface area is the
subprocess fan-out, the failure-isolation wrapper, and the cross-domain
merge/sort — nothing else.

## Common Pitfalls

### Pitfall 1: Conflating "empty findings" with "checker failed"
**What goes wrong:** A domain with zero problems (e.g. a repo with a
perfectly-formed Makefile) and a domain whose subprocess crashed both
produce "nothing to report" if not handled distinctly, silently violating
SC1's "none silently dropped" and PROJECT.md's confidence-labeling Core
Value.
**Why it happens:** Both states look identical if the orchestrator only
checks "is the remediate list for this domain empty?"
**How to avoid:** D-02 locks that a subprocess failure (non-zero exit,
crash, malformed JSON) produces a distinct, labeled failure entry, separate
from a genuine empty-remediate-list success. Track exit code and
`json.loads` success/failure explicitly per domain, never inferring failure
from an empty payload.
**Warning signs:** A test fixture where one of the six stub functions
raises/returns garbage should produce a report that still shows all 5 other
domains' real findings AND a visibly distinct "docker: failed to run
(reason)" line — if the test can't tell that failure apart from "docker had
no findings" by reading the aggregated output, the schema is wrong.

### Pitfall 2: Trusting `check`'s literal wording over the shape evidence
**What goes wrong:** ROADMAP SC1 says "invokes all 6 checkers' `check`"
and SC4 says the test "stubs all 6 checkers' `check` output" — read
literally, this could mean the orchestrator subprocess-calls the `check`
subcommand specifically (not `remediate`), then has to reimplement
`build_remediation`'s branching itself (violating the Don't-Hand-Roll
guidance above) to get an `auto_apply`/ordered shape.
**Why it happens:** The roadmap's phase-boundary prose uses "check/remediate"
as a compound phrase throughout (e.g. CONTEXT.md's own Phase Boundary:
"runs all 6 checkers' `check`/`remediate` against one target repo") rather
than distinguishing the two subcommands precisely.
**How to avoid:** See Open Questions — flag this for explicit planner/user
confirmation rather than silently picking one reading. The evidence favors
subprocess-calling `remediate` (which internally calls `check`, so `check`
is still literally invoked, just not as a second subprocess round-trip),
but this is a judgment call, not a locked decision in CONTEXT.md.
**Warning signs:** If the plan ends up with two near-duplicate branching
implementations (one inside a sibling's `remediation.py`, one inside the
orchestrator) that classify findings the same way, that's a signal the
`check`-only reading was chosen and is duplicating logic unnecessarily.

### Pitfall 3: Hardcoding a `~/.claude/skills/...` path for the 6 sibling entrypoints
**What goes wrong:** The orchestrator needs to resolve 6 other skills'
entrypoint scripts, not just its own. A naive implementation might hardcode
`~/.claude/skills/ai-kit-project-rules-<domain>/ai-kit-project-rules-<domain>.py`,
breaking on opencode/`~/.agents`/plugin-root installs.
**Why it happens:** Copy-pasting a single-skill resolution snippet without
generalizing it to loop over 6 skill-name strings.
**How to avoid:** Reuse the exact host-neutral candidate-list pattern every
sibling's own `SKILL.md` "Resolve the entrypoint" section already documents
(5 candidates: `$CLAUDE_PLUGIN_ROOT`, `$HOME/.claude/skills`, opencode's XDG
path, `~/.agents/skills`, from-checkout sibling), parameterized by skill
name, run once per domain.
**Warning signs:** The orchestrator works when installed via
`tools/setup.py`'s symlink but silently reports all 6 domains as "checker
not found" when run from a different host layout.

### Pitfall 4: Forgetting the family-wide registration gates for a new skill
**What goes wrong:** The new `ai-kit-project-rules-all` skill ships without
being wired into the repo's own quality gates, so it exists on disk but is
never linted, type-checked, dead-code-scanned, or test-run by CI/pre-commit
— exactly the failure mode Phase 14's own plan called out
(`.planning/phases/14-.../14-01-PLAN.md:926`, read this session: "A new
skill added to the tree but not to these surfaces ships ungated while every
command still exits 0.").
**Why it happens:** The registration list is spread across 3 files and is
easy to miss because none of them fail loudly if a new skill's path is
absent — everything still exits 0.
**How to avoid:** Register the new skill in all of the following, following
the exact pattern every one of the 5 most recent siblings (agents through
cicd) already uses:
- `Makefile:46` — append `tests.test_ai_kit_project_rules_all` to the
  `test-unit` target's unittest module list
  `[VERIFIED: Makefile:46, read this session — literal line: "python3 -m unittest tests.test_setup tests.test_status_line ... tests.test_ai_kit_project_rules_docker tests.test_ai_kit_project_rules_cicd"]`
- `.pre-commit-config.yaml:21` — append `skills/ai-kit-project-rules-all/.*`
  to the `ruff` hook's `files:` regex
  `[VERIFIED: .pre-commit-config.yaml:21, read this session — literal regex ends "...skills/ai-kit-project-rules-cicd/.*|skills/ai-kit-gsd-curated-config/.*|skills/_shared/.*)\.py$"]`
- `.pre-commit-config.yaml:50` — same append to the `py-compile` hook's
  `files:` regex (identical list, verbatim, at line 50)
- `.pre-commit-config.yaml:55` — append
  `tests.test_ai_kit_project_rules_all` to the `unittest` hook's `entry:`
  module list (same list as `Makefile:46`, duplicated per the file's own
  "Single source of truth" comment structure)
- `pyproject.toml:88` and `:94` — append `"skills/ai-kit-project-rules-all"`
  to both the `[tool.vulture]` `paths` list (line 88, under the
  `[tool.vulture]` header at line 86) and the `[tool.pyright]` `include` list
  (line 94, under the `[tool.pyright]` header at line 93)
  `[VERIFIED: pyproject.toml:86-88,93-94, re-read live 2026-09-15 — line 86 is `[tool.vulture]`, line 88 is its `paths` list; line 93 is `[tool.pyright]`, line 94 is its `include` list; both lists list the same 9 skill paths verbatim, ending "...skills/ai-kit-project-rules-cicd", "skills/ai-kit-gsd-curated-config", "skills/_shared". Correction: an earlier pass of this document had the tool-to-line mapping swapped (claimed line 88 was `[tool.pyright]` and line 94 was `[tool.vulture]`) — cross-AI review (`15-REVIEWS.md` cycle 1, claude lane, concern L64) caught the swap; this line reflects the corrected, live-verified mapping. It did not propagate into a plan bug — `15-02-PLAN.md` Task 1's own `<action>` text already named the tools correctly and instructs re-reading live rather than trusting line numbers.]`
- `README.md` — add a table row for `ai-kit-project-rules-all`, matching
  the exact style of the `ai-kit-project-rules-docker`/`cicd` rows
  (`README.md:43-44`, read this session)
- `/skill-judge` — per this project's established pattern (every phase
  shipping or renaming a skill runs `/skill-judge` as part of code review,
  producing a `15-SKILL-JUDGE.md` artifact — see `12-SKILL-JUDGE.md`
  through `14-SKILL-JUDGE.md` for precedent, read this session via
  directory listing) and `/naming-analyzer` confirmation, both already
  Phase 14's own final-plan pattern.
**Warning signs:** `make validate` passes locally after adding the new
skill's files, but that's expected even if registration is missing — the
absence is silent by construction. The only reliable check is a literal
`grep` for `ai-kit-project-rules-all` across the 3 registration files,
confirming presence in every one, not just "the tests I wrote pass."

## Code Examples

### The shared criticality vocabulary every domain's findings already carry
```python
# Source: skills/_shared/ai_kit_rules_common/criticality.py:23-27, read this session
CRITICALITY_CRITICAL = 1
CRITICALITY_HIGH = 2
CRITICALITY_MEDIUM = 3
CRITICALITY_ADVISORY = 4
```

### A structural-kind finding shape, with an identifier (`target`) — docker example
```python
# Source: skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/docker_checker.py:153-163, read this session
{
    "category": "docker-target-family",
    "issue": "docker_target_missing",
    "criticality": CRITICALITY_MEDIUM,
    "target": name,
    "summary": recommendation,
    "recommendation": recommendation,
    "needs_research": False,
}
```

### A structural-kind finding shape, WITHOUT a `target` identifier — arch example (identifier falls back to `category`)
```python
# Source: skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/arch_checker.py:150-159, read this session
{
    "category": "arch-test-target",
    "issue": "arch_test_target_missing",
    "criticality": CRITICALITY_HIGH,
    "summary": recommendation,
    "recommendation": recommendation,
    "needs_research": False,
}
```

### The shared builder's per-domain output shape (what each sibling's `remediate` subcommand returns)
```python
# Source: skills/_shared/ai_kit_rules_common/remediation.py:95-122 (build logic) and
# skills/ai-kit-project-rules-agents/SKILL.md's trimmed example (read this session)
{
  "remediate": [
    {"kind": "workflow", "id": "R01", "status": "missing", "criticality": 1,
     "summary": "...", "matched_signals": [], "auto_apply": True},
    {"kind": "workflow", "id": "R05", "status": "near_miss", "criticality": 2,
     "summary": "...", "matched_signals": ["..."], "auto_apply": False}
  ],
  "blocked": []
}
```
For a structural kind (`makefile`/`precommit`/`arch`/`docker`/`cicd`), each
`remediate` entry instead carries
`{"kind": <domain>, "id": <target-or-category>, "criticality": <int>, "summary": ..., "issue": ..., "auto_apply": <bool>}`
— `id` is a human-readable label, not a unique key; `(kind, id, issue)`
together are what distinguish two entries
`[VERIFIED: skills/_shared/ai_kit_rules_common/remediation.py:63-69, read this session — "id is a human-readable LABEL, not a unique key... (kind, id, issue) is what tells two entries apart, not id alone."]`.

### Every sibling's uniform CLI dispatch shape (what the orchestrator's `dispatch.py` calls 6 times)
```python
# Source: skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/cli.py:29-43, read this session
# (identical shape, only the module name and the report's top-level key differ,
# across all 6 siblings: agents -> "workflow", makefile -> "makefile",
# precommit -> "precommit", arch -> "arch", docker -> "docker", cicd -> "cicd")
def check(repo_root: str) -> dict:
    findings = check_cicd_rules(repo_root)
    findings = sorted(findings, key=lambda f: f["criticality"])
    return {"cicd": findings}

def remediate(repo_root: str) -> dict:
    return build_remediation(check(repo_root))

def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: ai-kit-project-rules-cicd.py check|remediate [repo_root]")
        return 0
    cmd = argv[0]
    if cmd == "check":
        repo_root = argv[1] if len(argv) > 1 else "."
        print(json.dumps(check(repo_root), indent=2))
        return 0
    if cmd == "remediate":
        repo_root = argv[1] if len(argv) > 1 else "."
        print(json.dumps(remediate(repo_root), indent=2))
        return 0
    print(f"unknown subcommand: {cmd}", file=sys.stderr)
    return 2
```

### The standalone entry-script pattern every sibling uses (what `dispatch.py` invokes via subprocess)
```python
# Source: skills/ai-kit-project-rules-makefile/ai-kit-project-rules-makefile.py, read this session
# (byte-identical shape across all 6 siblings, only the imported module name differs)
#!/usr/bin/env python3
import sys
from ai_kit_project_rules_makefile.cli import main
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

### The entrypoint-resolution loop the orchestrator must replicate 6x
```bash
# Source: skills/ai-kit-project-rules-agents/SKILL.md "Resolve the entrypoint" section, read this session
# (identical pattern in all 6 siblings' SKILL.md — only the skill-name string differs)
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-project-rules-agents}" \
         "$HOME/.claude/skills/ai-kit-project-rules-agents" \
         "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/ai-kit-project-rules-agents" \
         "$HOME/.agents/skills/ai-kit-project-rules-agents" \
         "$(dirname "<absolute path to THIS SKILL.md>")"; do
  [ -f "$d/ai-kit-project-rules-agents.py" ] && { printf '%s\n' "$d/ai-kit-project-rules-agents.py"; break; }
done
```

## State of the Art

Not applicable in the "libraries go stale" sense this section usually
targets — nothing in this phase's own tooling ages (stdlib subprocess/json,
no framework version to track). The one relevant "state" fact is that ALL
six prerequisite phases (9 through 14) are confirmed complete as of this
research date
`[VERIFIED: .planning/ROADMAP.md, "Progress" table, read this session — rows 9-14 all show "Complete" with 2026-09-14 dates]`,
so the "BLOCKED on Phases 9-14 landing first" language in `15-CONTEXT.md`'s
own header (dated 2026-09-13) is now stale, matching the exact same
stale-status pattern Phase 14's own plan flagged for ITS blocking note one
phase earlier
`[VERIFIED: .planning/phases/14-.../14-01-PLAN.md:501, read this session — "Read its STATUS LINES AS STALE: the header says 'BLOCKED on Phases 9-13 landing first'... both untrue now"]`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The orchestrator should subprocess-invoke each sibling's `remediate` subcommand (not `check`), then merge the six pre-built `{"remediate":[...], "blocked":[...]}` payloads — rather than invoking `check` and reimplementing the recommendation/near-miss branching itself | Architecture Patterns, Pitfall 2, Summary | If wrong, the plan builds a duplicate classification layer inside the orchestrator that constraints.md's "Cross-skill remediation merging ownership" protocol does not clearly forbid but the Don't-Hand-Roll guidance argues against; SC4's literal "stubs ... check output" wording would need the stub fixtures reshaped from `remediate`-shape to `check`-shape, a mechanical but real rework |
| A2 | A fixed, deterministic domain-concatenation order (e.g. `("agents", "makefile", "precommit", "arch", "docker", "cicd")`) should be applied before the stable sort, so same-criticality findings tie-break the same way on every run regardless of dispatch order | Architecture Patterns (Pattern 1, Anti-Patterns) | If the planner instead sorts by dict/glob iteration order, two runs against the same repo could report same-criticality findings in a different relative order, which would not violate any Success Criterion literally but would make the aggregated report non-reproducible, complicating any golden-output test |
| A3 | The rules-checker family (including this new orchestrator skill) is expected to stay stdlib-only, even though `AGENTS.md:29-31`'s explicit stdlib-only rule only names 3 specific runtime files, not `skills/` generally | Standard Stack | Low risk — every one of the 6 existing siblings already follows this unbroken pattern; a planner choosing to add a dependency here would be the first deviation in the whole family and should confirm with the user first |
| A4 | `/agent-md-refactor`'s Step A/B/C hand-off is preserved via a SKILL.md-level cross-reference (the orchestrator's SKILL.md tells the executing agent to follow the existing documented sequence) rather than any new code, since `/agent-md-refactor` "has no CLI, no importable/callable interface" | Architecture Patterns (Pattern 2) | If wrong (e.g. if `/agent-md-refactor` gained a CLI since this was written), the orchestrator could over-engineer a code-level integration that duplicates a now-existing simpler path — worth a quick recheck of `~/.agents/skills/agent-md-refactor/SKILL.md` at plan time, since it lives outside this repo and was not read in full this session (only located) |

## Open Questions

1. **Does the orchestrator subprocess-call each sibling's `check` or `remediate` subcommand?**
   - What we know: Both subcommands exist on every sibling; `remediate`
     internally calls `check` then the shared `build_remediation` builder;
     every finding in `check`'s raw output already carries the same
     `criticality` integer field `remediate`'s output does; SC1 and SC4's
     literal wording says "check", while CONTEXT.md's Phase Boundary and
     Existing Code Insights consistently write "check/remediate" as one
     compound phrase and explicitly say the orchestrator's own dependency
     surface has "nothing from `skills/_shared/ai_kit_rules_common/`
     directly" (which only `remediate`-subcommand dispatch, not
     `check`-subcommand dispatch, keeps true without the orchestrator
     re-deriving branching logic itself).
   - What's unclear: Whether SC1/SC4's literal "check" wording is a
     precise, intentional CLI-subcommand choice the plan must honor exactly,
     or loose prose using "check" as a stand-in for "the checking
     operation" the way CONTEXT.md's own phase-boundary prose does.
   - Recommendation: Default to subprocess-calling `remediate` per domain
     (see A1) — this is coverage-equivalent (every `check`-output finding
     ends up in either `remediate` or `blocked`, none silently dropped),
     avoids duplicating `build_remediation`'s branching logic inside the
     orchestrator, and keeps the orchestrator's dependency surface exactly
     as CONTEXT.md's Integration Points note describes. Flag this reading
     for explicit confirmation during planning/discuss-phase rather than
     locking it silently, since it is a genuine two-way reading of the
     roadmap text.

2. **Exact D-02 failure-entry schema and timeout value.**
   - What we know: CONTEXT.md explicitly leaves this to the planner
     ("Exact schema for a D-02 failure entry ... left to the planner, as
     long as it's visibly distinct from a normal empty-findings entry").
   - What's unclear: No existing sibling has a comparable
     "subprocess of a subprocess" failure schema to copy verbatim — this is
     genuinely new ground for the family.
   - Recommendation: A shape like
     `{"domain": "docker", "status": "failed", "error": "<one-line message>", "returncode": <int-or-null>}`
     keeps the same flat-dict style every other finding entry in the family
     uses, and reuses the word `"status"` the `workflow`-kind findings
     already use for a small vocabulary win. A per-checker subprocess
     timeout (e.g. 30s, generous for a local-filesystem-only check) should
     produce the same failure shape with a `"timeout"` reason string, not a
     separate code path.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `python3` | Subprocess dispatch of all 6 sibling entrypoints, and the orchestrator's own entrypoint | ✓ | System python3 (same runtime every sibling already requires; project explicitly runs `test-unit` "under bare system python3 (stdlib-only, matching the runtime)", `Makefile:44-45`, read this session) | — |
| All 6 sibling skills (`ai-kit-project-rules-agents/makefile/precommit/arch/docker/cicd`) | Every subprocess call this phase makes | ✓ | Present on disk in this checkout (`skills/ai-kit-project-rules-*`, confirmed via directory listing this session); all 6 phases (9-14) marked Complete in ROADMAP.md | — |
| `skills/_shared/ai_kit_rules_common` | Indirectly, only inside each sibling's own subprocess (not imported by the orchestrator itself per A1's recommendation) | ✓ | Present on disk (`skills/_shared/ai_kit_rules_common/*.py`, confirmed via directory listing this session) | — |

No missing dependencies, with or without fallback — everything this phase
needs already exists in the repo.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Python stdlib `unittest` |
| Config file | none — invoked directly via `python3 -m unittest tests.<module>` (`Makefile:46`, read this session) |
| Quick run command | `python3 -m unittest tests.test_ai_kit_project_rules_all` |
| Full suite command | `make test` (aggregates `test-unit`, `test-integration`, `e2e-test`, `arch-test` per `AGENTS.md:122-127`, read this session) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-rules-all (SC1) | Aggregated report contains findings from every domain that has any, none silently dropped | unit | `python3 -m unittest tests.test_ai_kit_project_rules_all.TestAggregate -v` | ❌ Wave 0 |
| REQ-rules-all (SC2) | Aggregated report ordered by criticality across domains, using the shared vocabulary | unit | same module, an ordering-assertion test case over mixed-criticality stub fixtures | ❌ Wave 0 |
| REQ-rules-all (SC3) | `workflow`-kind findings still point at the `/agent-md-refactor` hand-off; every other kind is inline/report-only | unit + documentation review | a test asserting the aggregation output tags `workflow`-kind entries distinctly (e.g. a `hand_off: true`/domain marker), plus a manual read of the orchestrator's own `SKILL.md` for the Step A/B/C cross-reference (this half is not code-testable) | ❌ Wave 0 |
| REQ-rules-all (SC4) | Integration-style test stubs all 6 checkers' output, asserts aggregation/ordering, without re-exercising each checker's full logic | integration (stubbed) | `python3 -m unittest tests.test_ai_kit_project_rules_all.TestAggregate` — MUST call `aggregate()` directly with 6 hand-built fixture dicts, never real subprocess | ❌ Wave 0 |
| REQ-rules-all (SC5) | Cross-skill merging lives only in the orchestrator; no sibling's `remediation.py` usage changes | static/code-review | `git diff` review confirming zero edits under any `skills/ai-kit-project-rules-{agents,makefile,precommit,arch,docker,cicd}/**/remediation.py`, plus the existing `tests/test_ai_kit_rules_common.py` drift-guard suite still passing unchanged | ✅ (drift guard already exists) |

### Sampling Rate
- **Per task commit:** `python3 -m unittest tests.test_ai_kit_project_rules_all`
- **Per wave merge:** `make test-unit` (add the new module to `Makefile:46`
  first, per the registration pitfall above, or this command silently
  won't run the new suite at all)
- **Phase gate:** `make test` green, plus `git diff` confirming no
  sibling `remediation.py` file changed (SC5), before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_ai_kit_project_rules_all.py` — new file, covers all 5
      success criteria per the map above
- [ ] `skills/ai-kit-project-rules-all/` — the skill itself does not exist
      yet; this whole phase creates it
- [ ] Registration edits to `Makefile`, `.pre-commit-config.yaml` (3
      locations), `pyproject.toml` (2 locations), `README.md` — see
      Pitfall 4 for exact line numbers in the current tree
- [ ] Framework install: none — `unittest` is stdlib, already available

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no | No auth surface — a local CLI orchestrator |
| V3 Session Management | no | Not applicable |
| V4 Access Control | no | Not applicable — runs with the invoking user's own filesystem permissions, same as every sibling |
| V5 Input Validation | yes | `repo_root` is a filesystem path passed to `subprocess.run([sys.executable, entrypoint_path, "check", repo_root])` as a list (never `shell=True`, matching every sibling's own subprocess-CLI test pattern, which never shells out through a string) — never string-interpolated into a shell command. Malformed JSON on a sibling's stdout must be caught (`json.JSONDecodeError`) and folded into the D-02 failure entry, never allowed to raise uncaught |
| V6 Cryptography | no | Not applicable — no secrets, no crypto operations anywhere in this phase |
| V12 File and Resources | yes | Every sibling already resolves symlink-real paths before reading a target repo's files (e.g. the agents checker's own `os.path.realpath` containment check, `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/cli.py:26-30,49-69`, read this session) — the orchestrator does not re-read any target-repo file itself (it only reads its own 6 subprocesses' stdout), so it does not need to re-implement this, but must not introduce a NEW path-traversal surface by, e.g., building an entrypoint path from unsanitized input |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Argument/shell injection via `repo_root` | Tampering | Always pass `subprocess.run([...], shell=False)` with `repo_root` as one list element, never inside a shell-interpolated string — matches the family's existing, unbroken pattern (no sibling anywhere in this codebase uses `shell=True`) |
| A malformed or hostile sibling's stdout (e.g. a corrupted `check` output) crashing the orchestrator | Denial of Service | Wrap every `json.loads()` call in a `try/except json.JSONDecodeError`, folding a parse failure into the same D-02 failure-entry path as a non-zero exit code — never letting one bad payload take down the whole aggregation |
| Silently dropping a domain's real findings due to an unhandled exception in one dispatch call | Repudiation / confidence-labeling violation | D-02's explicit design: isolate each of the 6 dispatch calls in its own try/except, continue the loop regardless of one failure, and always emit a total-domain-count assertion somewhere testable (6 entries present in the final structure, success or failure, never 5) |

## Sources

### Primary (HIGH confidence — all read directly this session, in this repository checkout)
- `.planning/phases/15-rules-orchestrator-ai-kit-project-rules-all/15-CONTEXT.md` — locked decisions (D-01, D-02), discretion areas, canonical refs
- `.planning/phases/15-rules-orchestrator-ai-kit-project-rules-all/15-DISCUSSION-LOG.md` — alternatives considered
- `.planning/ROADMAP.md` — Phase 15 goal, success criteria, dependency note, Progress table (Phases 9-14 confirmed Complete)
- `.planning/REQUIREMENTS.md` — `REQ-rules-all` traceability row
- `.planning/intel/constraints.md` — "Shared package import convention" and "Cross-skill remediation merging ownership" protocols
- `.planning/config.json` — `nyquist_validation: true`, `security_enforcement: true`
- `docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md` — `ai-kit-project-rules-all` design-spec section, dual-knowledge pattern, tooling taxonomy
- `skills/_shared/ai_kit_rules_common/remediation.py` (full file) — `STRUCTURAL_KINDS`, `build_remediation()` contract
- `skills/_shared/ai_kit_rules_common/criticality.py` (full file) — shared vocabulary
- `skills/ai-kit-project-rules-{agents,makefile,precommit,arch,docker,cicd}/ai_kit_project_rules_*/cli.py` (all 6, full files) — CLI contract, exact `check`/`remediate` return shapes
- `skills/ai-kit-project-rules-{agents,makefile,precommit,arch,docker,cicd}/ai_kit_project_rules_*/remediation.py` (all 6) — confirmed thin re-export wrappers around the shared builder
- `skills/ai-kit-project-rules-{agents,makefile}/ai_kit_project_rules_*/__init__.py` — `sys.path` append pattern for reaching `_shared`
- `skills/ai-kit-project-rules-{agents,makefile,arch,docker,cicd}.py` entry scripts (sampled) — uniform `sys.exit(main(sys.argv[1:]))` shape
- `skills/ai-kit-project-rules-agents/SKILL.md` (full file) — the "Wrap mechanism" Step A/B/C hand-off this phase must preserve; entrypoint-resolution pattern
- `skills/ai-kit-project-rules-{arch,cicd,docker,makefile,precommit}/SKILL.md` "Resolve the entrypoint" sections — confirmed identical pattern across all 6
- `skills/ai-kit-project-rules-cicd/SKILL.md` (partial) — scope-boundary / "detect and reports only" wording precedent
- `skills/ai-kit-project-rules-arch/ai_kit_project_rules_arch/arch_checker.py` (partial, lines 1-200) — structural finding shape, `category`/`issue`/`criticality`/`summary`/`recommendation`/`needs_research` fields
- `skills/ai-kit-project-rules-docker/ai_kit_project_rules_docker/docker_checker.py` (lines 140-231) — `target`-keyed vs `category`-only structural finding examples
- `tests/test_ai_kit_project_rules_cicd.py` (partial) — subprocess-based entrypoint test pattern, `unittest`-only convention
- `tests/test_ai_kit_rules_common.py` (partial, class list) — shared-package test structure precedent
- `Makefile` (relevant sections) — `test-unit`/`test`/`validate`/lint target definitions and exact registration line (`:46`)
- `.pre-commit-config.yaml` (lines 1-60) — `ruff`/`py-compile`/`unittest` hook `files:`/`entry:` registration lines
- `pyproject.toml` (lines 88, 94) — `pyright`/`vulture` `paths`/`include` registration lines
- `README.md` (lines 42-44) — skill-listing table row convention
- `AGENTS.md` (lines 20-40, 100-135) — stdlib-only runtime rule, dev-tooling versions, testing pyramid description
- `.planning/phases/14-ci-cd-rules-checker-ai-kit-project-rules-cicd/14-01-PLAN.md` (grepped sections) — registration-gate precedent, stale-status-note precedent
- `.planning/phases/{12,14}-.../*-SKILL-JUDGE.md` (directory listing only, confirming existence) — `/skill-judge` gate precedent for a new/changed skill

### Secondary (MEDIUM confidence)
None — no web-sourced or documentation-site claims were needed for this
phase; everything relevant already lives in this repository.

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib-only, directly confirmed via reading every sibling's import block this session
- Architecture: HIGH — every contract (CLI shape, finding shape, criticality vocabulary, hand-off mechanism) read verbatim from source this session; the one genuine ambiguity (Open Question 1) is explicitly flagged rather than silently resolved
- Pitfalls: HIGH — sourced directly from Phase 14's own plan text and the shared package's own docstrings, not inferred

**Research date:** 2026-09-15
**Valid until:** No external drift risk (stdlib-only, no framework versions) — valid until the 6 sibling skills' own CLI contracts change, which would itself be a breaking change requiring re-research regardless of elapsed time
