# AI-Kit Multi-CLI Runtime Support - Product Requirements Document (PRD)

## Requirements Description

### Background

- **Business Problem**: ai-kit's tooling (install script, model catalog, review/execute
  dispatch) was built assuming Claude Code as the sole host. Three concrete gaps surfaced
  during real multi-CLI usage (testing the model-catalog wizard against opencode on macOS,
  and reviewing `tools/install.sh`'s bootstrap fetch):
  1. `tools/install.sh`'s primary `git clone` path does not restrict the fetch to a single
     branch, so it can pull extra remote refs/branches it will never use.
  2. Nothing in the codebase can tell, at runtime, which CLI/host ai-kit's own skills are
     currently executing under (Claude Code, opencode, or codex) — only which CLIs/models
     are *installed* on the machine (`detect_installed_clis`, `detect_opencode_models` in
     `skills/ai-kit-spec-review/ai_kit_spec/detection.py`). Consequently, the existing
     "native" candidate concept (`cli is None` in
     `skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py:49`, meaning "this candidate
     executes in-process rather than being dispatched to an external CLI") implicitly
     assumes the in-process host is always Claude Code — it has no way to know or record
     that it might actually be running in-process inside opencode or codex instead.
  3. Claude Code's statusline (a customizable bottom bar showing session/git/model info)
     has no equivalent extension point confirmed in opencode's TUI: opencode's own plugin
     system (25+ lifecycle hooks, documented at https://opencode.ai/docs/plugins) has no
     hook documented for status-bar or sidebar customization; a community feature request
     for exactly this (`anomalyco/opencode#5971`) is open and unresolved as of this PRD.
- **Target Users**: ai-kit's own maintainer/user, testing and using ai-kit's skills across
  multiple installed agentic CLIs (Claude Code, opencode, codex) on the same machine.
- **Value Proposition**: Correct, minimal-footprint installs (Phase 1); accurate
  "native model" labeling that reflects the actual host CLI instead of assuming Claude
  Code, which directly fixes a real misclassification risk in the model catalog / ranking
  wizard (Phase 2); and a documented, low-risk path to eventually extend ai-kit's
  status-reporting UX into opencode, once/if opencode exposes a way to do so (Phase 3,
  research-only in this PRD).

### Feature Overview

- **Core Features**:
  1. Harden `tools/install.sh`'s primary git-based fetch to clone only the target branch.
  2. Add runtime self-detection (which CLI/host process ai-kit is currently executing
     under) covering Claude Code, opencode, and codex from the MVP, surfaced as a new
     `native_runtime` field on model-catalog entries.
  3. Research (only — no build in this PRD) how opencode's plugin hook system could be
     used to approximate status/sidebar-style output, producing a written findings
     artifact for a future PRD to act on.
- **Feature Boundaries**:
  - IN: the `git clone` fetch path in `install.sh`; a new runtime-detection utility
    consumed by the model catalog / `execute_dispatch.py`; a `native_runtime` catalog
    field; a research report on opencode plugin hooks.
  - NOT IN: any actual opencode sidebar/status-bar implementation (blocked on opencode
    not exposing the needed API — tracked as future work with no defined trigger date);
    changes to `tools/install.sh`'s tarball-fallback path (already scoped to one branch
    via GitHub's `archive/refs/heads/<branch>` URL, `install.sh:113`, and out of scope
    here); any change to `execute_dispatch.py`'s actual dispatch behavior when the
    runtime is unknown (explicitly a labeling-only change, see Detailed Requirements).
- **User Scenarios**:
  - A user runs the one-line `curl | bash` installer; the underlying `git clone` fetches
    only the target branch's history, not every remote branch.
  - ai-kit's model-catalog wizard runs under opencode; a model that is opencode's own
    in-process/native model is now correctly labeled `native_runtime: "opencode"` in the
    catalog (instead of being silently treated as if the host were Claude Code).
  - The same wizard, run under Claude Code or codex, correctly labels
    `native_runtime: "claude"` or `native_runtime: "codex"` respectively.
  - If runtime detection cannot determine the host (an unusual wrapper/invocation), the
    catalog entry is labeled `native_runtime: "unknown"` — dispatch behavior for that
    candidate is completely unchanged (still executes in-process per today's
    `cli is None` handling in `execute_dispatch.py`); `"unknown"` is informational only.

### Detailed Requirements

- **Input/Output**:
  - Phase 1: Input = the existing `REPO_SLUG`/`REPO_BRANCH` variables already used to
    build the clone URL in `fetch_repo()` (`tools/install.sh:95-103`). Output = the same
    `git clone` command, now also passing `--single-branch`.
  - Phase 2: Input = the running process's environment/invocation context (env vars,
    and/or other signals to be identified by the research task below). Output = a new
    pure function (name/location TBD by the research task, analogous to
    `infer_is_router`/`infer_purpose_from_name` in `model_heuristics.py`) returning one of
    `"claude"` / `"opencode"` / `"codex"` / `"unknown"`; this value is written to a new
    optional `native_runtime` field on catalog entries that already have `cli: None`
    (the existing native-candidate marker).
  - Phase 3: Input = opencode's published plugin/hook documentation and source. Output =
    a written research report (markdown) enumerating: every hook opencode documents,
    which (if any) could plausibly carry status/sidebar-like output, what a minimal
    proof-of-concept would look like for the most promising hook, and an explicit
    recommendation on whether/when to revisit building it. No code changes.
- **User Interaction**: All three phases are invisible to interactive use except through
  their outputs (a leaner clone, a new catalog field, a research doc) — no new CLI flags,
  no new wizard prompts.
- **Data Requirements**:
  - `native_runtime`: optional string field, one of `{"claude", "opencode", "codex",
    "unknown"}`, added to the model-catalog schema (`skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py`'s
    `_FIELD_TYPES` + a literal-value validation check, following the exact pattern already
    established for `name_declared_purpose` in this same file). Absent on any entry
    predating this feature (no migration needed — same additive-optional pattern as
    `name_declared_purpose`). Only meaningful on an entry where `cli` is `None`
    (the existing native-candidate marker) — the research/implementation task must define
    what (if anything) is written for a non-native (`cli` is a real CLI name) entry: the
    recommended default is to leave the field entirely absent for non-native entries,
    since runtime identity is only ambiguous/interesting for the in-process case.
- **Edge Cases**:
  - Runtime cannot be determined → `native_runtime: "unknown"`; `execute_dispatch.py`'s
    `cli is None` branch executes in-process exactly as it does today — no behavior
    change, no warning required (per clarification: label-only, no dispatch impact).
  - A machine with more than one of Claude Code / opencode / codex installed is not the
    question here — detection is about which one the *current process* is running
    under, not which ones are installed (that's already covered by the existing
    `detect_installed_clis`).
  - `install.sh`'s existing `--branch`/`--branch=` override flags (`install.sh:86-87`) and
    the "already cloned, `git pull --ff-only`" convergent-update path (`install.sh:99-100`,
    taken when `$INSTALL_DIR/.git` already exists) are both unaffected by adding
    `--single-branch` to the one-time initial clone — must be verified, not assumed, by
    the regression test in Acceptance Criteria.

## Design Decisions

### Technical Approach

- **Phase 1 (install.sh)**: One-line change — add `--single-branch` to the existing
  `git clone --branch "$REPO_BRANCH" --depth 1 "$url" "$INSTALL_DIR"` call
  (`tools/install.sh:103`). No other line in `fetch_repo()` changes: the tarball fallback
  (`install.sh:104-116`, taken only when `git` itself is unavailable) already fetches a
  single branch's archive via `archive/refs/heads/${REPO_BRANCH}.tar.gz` and needs no
  change; the `git pull --ff-only` convergent-update path (`install.sh:99-100`) operates
  on an already-cloned single-branch repo and needs no change either.
- **Phase 2 (runtime self-detection)**: A dedicated research task first (no committed
  env-var/mechanism is known today — grepped the codebase, found none). The research task
  investigates, for each of Claude Code / opencode / codex, what signal reliably
  identifies "I am running as a subprocess/tool-call inside this specific host" (candidate
  signal classes to investigate: process environment variables set by each host,
  characteristic parent-process/argv patterns, or a host-specific marker file/socket).
  Once a signal is confirmed for a given runtime, implement a pure detection function
  (no network, no side effects — same shape as `model_heuristics.py`'s existing
  heuristics) that the model-catalog build path (`cli.py`) calls once per run and threads
  through to any native (`cli is None`) catalog entry as `native_runtime`.
- **Phase 3 (opencode UI research)**: Read opencode's plugin documentation
  (https://opencode.ai/docs/plugins) and enumerate every documented hook; for each,
  assess whether it could carry a status/sidebar-like widget (even approximately — e.g.
  `tui.toast.show` could theoretically surface transient info, though not a persistent
  sidebar). Cross-reference the open feature request (`anomalyco/opencode#5971`) for any
  maintainer signal on timeline or intended design. Produce one markdown report;
  no plugin code is written in this PRD.
- **Key Components**:
  - `tools/install.sh` (`fetch_repo()`) — Phase 1.
  - A new runtime-detection function (module/location decided by the Phase 2 research
    task's findings, but following the existing `model_heuristics.py` pattern of a small,
    pure, independently-testable function) — Phase 2.
  - `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py` (`_FIELD_TYPES`, a new
    `_VALID_NATIVE_RUNTIME` literal set, `validate_catalog_entry`) — Phase 2.
  - Whatever in `cli.py`'s catalog-build path currently constructs a native (`cli is
    None`) entry — Phase 2 (exact insertion point to be confirmed against current code
    at implementation time, since this PRD is written after the most recent catalog
    changes and file line numbers may have shifted).
  - A new research document under `docs/` (exact path decided at implementation time,
    e.g. `docs/superpowers/research/opencode-plugin-hooks-for-ui.md`) — Phase 3.
- **Data Storage**: No new storage — `native_runtime` lives in the existing JSON model
  catalog file alongside every other per-entry field.
- **Interface Design**: No new CLI flags or wizard prompts for Phase 1 or 2. Phase 2's
  detection function signature: `detect_current_runtime() -> str` returning one of
  `{"claude", "opencode", "codex", "unknown"}`, no arguments (reads only the process's own
  environment/context) — exact internal implementation is the research task's output.

### Constraints

- **Performance Requirements**: Runtime detection must be a fast, synchronous, in-process
  check (env var reads / simple process inspection) — no network calls, no subprocess
  spawns, consistent with every existing heuristic in `model_heuristics.py`.
- **Compatibility**: `native_runtime` is optional and additive — a catalog file written
  before this feature exists must continue to validate and merge unchanged (same
  guarantee already established for `name_declared_purpose` in the same schema file).
  `install.sh`'s `--single-branch` change must not alter behavior of the existing
  `--branch`/`--branch=` override flags or the already-cloned convergent-update path.
- **Security**: None beyond what already applies — no new external input is trusted,
  runtime detection reads only the local process's own environment.
- **Scalability**: N/A — single-user local tooling, no concurrency or load concerns.
- **Skill quality gate**: Any `SKILL.md` created or modified anywhere in this PRD's
  execution (across all 3 phases) MUST go through a `skill-judge` review loop before the
  task that touches it is considered complete: invoke the `skill-judge` skill against the
  changed file, address every Critical/Important finding it raises, and re-invoke until
  either no such finding remains or the score reaches at least Grade B (96/120) — the same
  bar already established across every `ai-kit-*` skill in a prior session (commit
  `f6411c3`, "raise skill-judge scores across all ai-kit-* skills"). A skill-judge score
  regression versus the pre-change baseline is treated as a fix-required finding in its
  own right, even if the absolute score still clears 96/120. This gate applies regardless
  of which phase the change belongs to — if a phase turns out not to touch any `SKILL.md`,
  the gate simply doesn't fire for it (see per-phase notes below for where it's expected
  to apply in practice).

### Risk Assessment

- **Technical Risks**:
  - Phase 2's biggest risk is that no reliable, host-specific signal exists for one or
    more of the three runtimes (e.g. codex may expose nothing distinguishable). Mitigated
    by scoping Phase 2 as research-first: if a runtime's signal can't be confirmed, that
    runtime's detection falls through to `"unknown"` (never a crash, never a guess)
    exactly like the general unknown-runtime case already specified above — this is an
    acceptable, explicitly designed degradation, not a blocker to shipping Phase 2 for
    whichever runtimes DO have a confirmed signal.
  - Phase 3 is pure research with no implementation risk by design.
- **Dependency Risks**: Phase 3's entire value depends on opencode's own (currently
  undocumented) plugin roadmap for UI extension — explicitly out of ai-kit's control.
  Mitigated by scoping Phase 3 as research/report-only, with no committed build timeline.
- **Schedule Risks**: Phase 2's research sub-task has an open-ended discovery risk (see
  Technical Risks above); mitigated by the same per-runtime fallback-to-`"unknown"` design
  — a slow or inconclusive finding for one runtime does not block shipping the others.

## Acceptance Criteria

### Functional Acceptance

- [ ] Phase 1: `tools/install.sh`'s primary `git clone` call includes `--single-branch`
      alongside the existing `--branch "$REPO_BRANCH" --depth 1` flags.
- [ ] Phase 1: the tarball-fallback path and the already-cloned `git pull --ff-only` path
      are verified unchanged (no diff to those lines).
- [ ] Phase 1: the existing `--branch`/`--branch=` CLI override flags still work
      end-to-end with `--single-branch` added (a non-default branch still clones
      correctly, restricted to that one branch).
- [ ] Phase 2: a runtime-detection function exists and returns one of `"claude"` /
      `"opencode"` / `"codex"` / `"unknown"`, confirmed empirically for at least Claude
      Code and opencode (codex confirmed if the research finds a viable signal; if not,
      codex detection explicitly and permanently returns `"unknown"`, documented as such).
- [ ] Phase 2: `native_runtime` is a recognized, optional, literal-validated field in
      `model_catalog.py`'s schema, following the exact pattern of `name_declared_purpose`
      (`_FIELD_TYPES` entry + a `_VALID_NATIVE_RUNTIME` set + a post-type-loop validation
      check). Global constraint: mirror the check-ordering fix already established for
      `name_declared_purpose` — the literal-value check runs AFTER the generic
      `_FIELD_TYPES` type-check loop, never before, to avoid a `TypeError` on a
      non-string cached value.
- [ ] Phase 2: a catalog entry with `cli: None` gets `native_runtime` set to the detected
      value; a catalog entry with a real `cli` value never gets `native_runtime` set.
- [ ] Phase 2: when detection is inconclusive, the entry gets `native_runtime: "unknown"`
      and `execute_dispatch.py`'s existing `cli is None` in-process execution path is
      empirically confirmed unchanged (same tests pass, no new behavior gated on this
      value there).
- [ ] Phase 3: a written markdown research report exists, enumerating opencode's
      documented plugin hooks, assessing each for sidebar/status-bar viability, and
      giving an explicit recommendation (proceed / wait / re-investigate later).
- [ ] Any `SKILL.md` touched by any phase (expected: `ai-kit-spec-config/SKILL.md` in
      Phase 2, to document the new `native_runtime` labeling in the wizard's ranked
      candidate output — see Phase 2 Task 5) passes a `skill-judge` review loop per the
      Constraints section's skill quality gate before that phase's work is marked done.

### Quality Standards

- [ ] Code Quality: Phase 2's detection function and catalog-field changes follow the
      existing codebase conventions in `model_heuristics.py`/`model_catalog.py` (pure
      functions, no side effects, `\b`-bounded or exact-match logic rather than fragile
      substring checks where applicable).
- [ ] Test Coverage: Phase 1 gets a new/updated case in `tests/test_install.sh` asserting
      the `--single-branch` flag is present on the primary clone invocation. Phase 2 gets
      unit tests for the detection function (one per confirmed-detectable runtime, plus
      the `"unknown"` fallback) and for the new catalog field's validation (accepts each
      valid value, rejects an invalid one, accepts absent — mirroring
      `TestValidateCatalogEntry`'s existing `name_declared_purpose` test group), following
      this repo's existing test conventions: `tests/test_ai_kit_spec.py` via `unittest`
      (not `pytest`), `tests/test_install.sh` via its existing shell-test harness.
- [ ] Skill Quality: every `SKILL.md` touched by this PRD's execution has a `skill-judge`
      report attached to the task that touched it, showing either no remaining
      Critical/Important finding or a score ≥ 96/120 (Grade B), with no regression versus
      that file's pre-change baseline score.
- [ ] Performance Metrics: N/A (no performance-sensitive path touched).
- [ ] Security Review: N/A (no new trust boundary; see Constraints).

### User Acceptance

- [ ] User Experience: no user-facing behavior changes except a leaner `git clone` fetch
      (Phase 1) and more accurate `native_runtime` labeling in catalog output visible to
      anyone inspecting the catalog JSON or wizard output (Phase 2) — no interactive UX
      change.
- [ ] Documentation: Phase 3's research report is the phase's sole deliverable and must be
      committed under `docs/` so it's discoverable for a future PRD.
- [ ] Training Materials: Not applicable (internal tooling, single user).

## Execution Phases

### Phase 1: Harden install.sh's git clone
**Goal**: Restrict the primary bootstrap clone to a single branch, with regression coverage.
- [ ] Task 1: Add `--single-branch` to `tools/install.sh`'s primary `git clone` call
      (`fetch_repo()`, currently line 103).
- [ ] Task 2: Add/update a `tests/test_install.sh` case asserting the flag is present.
- [ ] Task 3: Manually verify the existing `--branch`/`--branch=` override flags and the
      already-cloned `git pull --ff-only` convergent-update path are unaffected.
- **Deliverables**: One-line `install.sh` change, one new/updated shell test case, full
  `tests/test_install.sh` suite green.
- **Time**: Under 1 hour (smallest, lowest-risk phase — matches the plan's own priority
  ordering, done first).
- **Skill quality gate**: does not apply — this phase touches no `SKILL.md`.

### Phase 2: Runtime self-detection + native_runtime catalog field
**Goal**: Let ai-kit's tooling know which host CLI it is currently executing under, and
record that against native (in-process) model-catalog candidates.
- [ ] Task 1 (research): investigate what signal (env var, process context, or other)
      reliably identifies the current host process for Claude Code, opencode, and codex
      respectively. Document findings (confirmed signal, or "no reliable signal found —
      permanently `unknown`") per runtime.
- [ ] Task 2: implement `detect_current_runtime() -> str` per the research findings,
      following the existing pure-heuristic pattern in `model_heuristics.py`. Unit tests
      per confirmed runtime plus the `unknown` fallback.
- [ ] Task 3: add `native_runtime` to `model_catalog.py`'s schema (`_FIELD_TYPES` +
      `_VALID_NATIVE_RUNTIME` + post-type-loop validation check, mirroring
      `name_declared_purpose`'s existing pattern exactly, including its check-ordering
      fix). Unit tests mirroring `TestValidateCatalogEntry`'s existing group for that field.
- [ ] Task 4: wire `detect_current_runtime()` into the catalog-build path so a native
      (`cli is None`) entry gets `native_runtime` set; confirm a non-native entry never
      gets the field. Confirm `execute_dispatch.py`'s `cli is None` handling is completely
      unaffected by the new field's value (including `"unknown"`).
- [ ] Task 5: update `ai-kit-spec-config/SKILL.md`'s wizard presentation guidance (the
      same Step 2.2 section touched by the `name_declared_purpose` feature) to document
      `native_runtime`: how a native candidate's runtime label should be surfaced to the
      user in the ranked candidate output, mirroring the existing `via <cli>` labeling
      convention. Then run the skill-judge review loop (Constraints: Skill quality gate)
      against `ai-kit-spec-config/SKILL.md` before this task is marked complete — record
      the pre-change and post-change scores in the task's commit message or PR notes.
- **Deliverables**: Research notes (can live in the task's own commit message or a short
  doc), `detect_current_runtime()` with tests, `native_runtime` schema support with
  tests, wiring with tests, updated wizard guidance with a passing skill-judge review,
  full existing test suite still green (no regressions).
- **Time**: Medium — the research sub-task (Task 1) is open-ended by nature; the
  implementation sub-tasks (2-5) are small once a signal is confirmed per runtime.
- **Skill quality gate**: applies to Task 5 (`ai-kit-spec-config/SKILL.md`) per the
  Constraints section above.

### Phase 3: opencode plugin-hook research (report only, no build)
**Goal**: Produce a decision-ready research report on whether/how opencode's existing
plugin hooks could approximate Claude Code's statusline UX, without committing to build
anything now.
- [ ] Task 1: Read opencode's plugin documentation (https://opencode.ai/docs/plugins) and
      enumerate every documented hook.
- [ ] Task 2: For each hook, assess (even speculatively) whether it could carry
      status/sidebar-like output; cross-reference the open feature request
      `anomalyco/opencode#5971` for any maintainer signal.
- [ ] Task 3: Write the findings to a markdown report under `docs/` with an explicit
      recommendation: proceed with a specific hook-based prototype, wait for opencode to
      ship a real sidebar API, or re-investigate at a later date (no fixed trigger
      condition required, per this PRD's own clarification — deferred without a defined
      unblocking criterion).
- **Deliverables**: One committed markdown research report.
- **Time**: Small (a few hours of documentation reading and writing) — no code, no tests.
- **Skill quality gate**: does not apply — this phase touches no `SKILL.md` (a research
  report under `docs/`, not a skill package).

---

**Document Version**: 1.0
**Created**: 2026-09-06
**Clarification Rounds**: 4
**Quality Score**: 93/100
