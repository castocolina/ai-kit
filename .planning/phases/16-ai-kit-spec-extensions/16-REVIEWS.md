---
phase: 16
cycle: 2
reviewers: [opencode-plan-review, codex-sol-high]
reviewed_at: 2026-09-24T10:53:45Z
plans_reviewed: [16-01-PLAN.md, 16-02-PLAN.md, 16-03-PLAN.md, 16-04-PLAN.md, 16-05-PLAN.md, 16-06-PLAN.md]
models:
  opencode-plan-review: "router-env/my-plan-review (reasoning=high)"
  codex-sol-high: "gpt-5.6-sol (reasoning=high)"
model_sources:
  opencode-plan-review: "pinned"
  codex-sol-high: "pinned"
---

# Cross-AI Plan Review — Phase 16

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

> Cycle 2 of plan-review convergence. It reviews the plans as revised in `8834ead`. The cycle-1
> review (6789a06) stays in git history. Each PLAN.md's "Review Dispositions Ledger" cites it by
> line (`L<n>@6789a06`).
>
> Lane notes (environment findings, not plan findings). Reviewers came from
> `review.default_reviewers`: `opencode-plan-review` (opencode, `router-env/my-plan-review`) and
> `codex-sol-high` (codex, `gpt-5.6-sol`). No lane was substituted, and the xai/grok lane was not
> used.
> - **codex-sol-high:** produced a full review. It got the full inlined prompt (339 KB), covers all
>   six plan ids, and cites `file:line` evidence.
> - **opencode-plan-review: FAILED (environment).** It got a compact 19.3 KB prompt that pointed
>   at the plans, RESEARCH.md and the cycle-1 REVIEWS.md on disk. The first dispatch exited 1
>   with no assistant text (stop reason `tool-calls`, 193 output tokens). A short foreground probe
>   ("Reply with exactly: PROBE-OK") showed the router backend refusing requests:
>   `Model opencode-zen/glm-5.2 is locked` (HTTP 503, `isRetryable: true`) and then
>   `All credentials for model glm-5.2 are cooling down` (`rate_limit_error` / `model_cooldown`).
>   All 19 probes between 07:05 and 07:50 (-03) failed the same way, so the CLI is working
>   but the backing model is quota-blocked. The single permitted lane retry (same compact prompt)
>   also exited 1 with no assistant text. Stubs and stderr are kept in `.review-diagnostics/`.
> - **Effect on counting:** only ONE reviewer produced a review section this cycle, so the
>   consensus gate does not engage. Every codex HIGH counts on its own, as the contract requires.
>   The orchestrator independently confirmed both HIGH premises against source (see Verification
>   coverage).
> - The working tree was unchanged after both read-only runs (`git status`: only the pre-existing
>   `.planning/state.json` modification).

## OpenCode Review (opencode-plan-review)

opencode review failed or returned empty output. stderr:

Raw response body:
OpenCode review returned no assistant text (#1936: agent ended its turn with no final message).
Diagnostic: stop reason=tool-calls, output tokens=193 (first dispatch); stop reason=?, output tokens=? (retry)
Diagnosis: opencode ran at effort=high and exited with status 1. Root cause from the foreground
probe: router-env backend `glm-5.2` locked / all credentials cooling down (transient quota state,
not a broken CLI). Recorded as an environment finding; this lane contributes no findings this cycle.

---

## Codex Review (codex-sol-high)

## 16-01

### Summary

The Codex enumeration plan is implementation-ready and follows the repository’s existing injected-subprocess conventions. It now covers the complete `codex debug models` → runtimes snapshot → catalog path, preserves reasoning metadata on unmatched records, and rejects unsuccessful subprocess results.

### Cycle-1 dispositions

- **RESOLVED — blocking `skill-judge` gate.** The executor-visible objective now identifies it as an orchestrator-owned blocking gate with the exact pass threshold and pending-summary requirement (`16-01-PLAN.md:121-129`), matching `AGENTS.md:45-47`.
- **RESOLVED — full repository verification scheduling.** This plan runs `make test-unit`, while 16-06 Task 3 schedules the actual `make test` and `make validate` gates (`16-01-PLAN.md:439-461`; `16-06-PLAN.md:385-420`).
- **RESOLVED — unmatched `reasoning_modes`.** Both unmatched exits receive `_apply_runtime_meta` before append (`16-01-PLAN.md:246-269`). This targets the real current exits at `skills/ai-kit-spec-review/ai_kit_spec/cli.py:409-413`.
- **RESOLVED — non-zero Codex exit.** The proposed `getattr(result, "returncode", 1) != 0` guard and degradation tests are explicit (`16-01-PLAN.md:206-219`, `:356-364`).
- **PARTIALLY RESOLVED — fixture provenance.** The revision records command, version, date, retained fields, substitutions, and omission rationale (`16-01-PLAN.md:275-288`). The fixture remains manually transcribed rather than reproducibly sanitized from a preserved capture.
- **NOT RESOLVED, accepted scope deferral — existing opencode/cursor return-code handling.** The current parsers still parse stdout without checking return status (`detection.py:74-106`); the plan deliberately limits stricter behavior to new parsers (`16-01-PLAN.md:637-638`).

### Strengths

- Uses the existing argv-list, timeout, injected-`run_fn` pattern from `detection.py:74-106`.
- Filters internal Codex entries and strips the large instruction payload before persistence.
- Correctly reuses the existing validated `reasoning_modes` field (`model_catalog.py:22`, `:111-113`).
- Tests malformed items, duplicate slugs, hidden entries, missing return codes, payload leakage, and unmatched metadata.
- Preserves the pre-existing single-provider fallback by omitting `models` when enumeration fails.

### Concerns

- **LOW — fixture reproducibility remains limited.** The detailed provenance makes the fixture auditable, but a future maintainer cannot regenerate it mechanically from the original capture.

### Suggestions

- Record a hash of the original raw capture and a short deterministic redaction recipe without committing the vendor prompt text.
- Otherwise execute as written after the cross-plan blockers under 16-04 and 16-06 are corrected.

### Risk Assessment

**LOW.** The runtime and catalog paths are well bounded, degradation behavior is explicit, and the remaining issue is provenance quality rather than functional correctness.

## 16-02

### Summary

This is a strong, narrow plan. It changes the precedence table rather than adding unnecessary control flow, closes the duplicated `pi` schema gap, and pins both individual signals and the complete nested-runtime matrix.

### Cycle-1 dispositions

- **RESOLVED — blocking `skill-judge` gate.** The objective makes it explicit and orchestrator-owned (`16-02-PLAN.md:112-120`).
- **RESOLVED — full verification scheduling.** `make test-unit` is executor-visible here, with the full repository gates in 16-06 (`16-02-PLAN.md:302-323`).
- **RESOLVED — false `OPENCODE_PID` claim.** The prescribed docstring names only `OPENCODE`, and the tests assert that no undocumented signal appears (`16-02-PLAN.md:166-191`, `:253-280`).

### Strengths

- The six-row tuple exactly encodes the required precedence and correctly represents Codex’s two independent signals (`16-02-PLAN.md:155-164`).
- It preserves the deliberate distinction between runtime identity and installed CLIs: current `KNOWN_CLIS` is separate at `detection.py:13`, while runtime signals are at `detection.py:25-32`.
- It closes both currently duplicated validation gaps: `model_catalog.py:39,103-106` and `config_io.py:96-129`.
- The end-to-end tracer verifies that `pi` survives detection, validation, and TOML rendering—not merely that the tuple returns a string.
- Confidence labels are tested against the actual signal table.

### Concerns

- No new blocking concern found.
- **LOW — duplicated runtime allow-lists remain a maintenance hazard.** The plan mitigates this with equality tests and comments, but the two source definitions still require coordinated updates.

### Suggestions

- Keep the equality assertion between both `_VALID_NATIVE_RUNTIME` sets as a permanent regression test.
- Do not add `pi` to `KNOWN_CLIS` in this phase; the plan correctly preserves that Phase 22 boundary.

### Risk Assessment

**LOW.** The change is table-driven, fully pinned by tests, and closes a real schema incompatibility discovered during research.

## 16-03

### Summary

The cache-version migration is well designed: it keeps generic TTL logic schema-agnostic, reserves `_meta` without exposing it as a model, preserves metadata through every writer, and honestly narrows atomicity claims to the behavior the current cache writer actually provides.

### Cycle-1 dispositions

- **RESOLVED — false concurrent-writer claim.** The objective now says single-writer atomicity and explicitly declares concurrent writers unsupported (`16-03-PLAN.md:87-101`). That matches the fixed temporary name in `cache.py:21-29`.
- **RESOLVED — “exactly one refresh” overstatement.** The plan now says one successful refresh and explicitly retries failures (`16-03-PLAN.md:71-76`).
- **RESOLVED — sibling `_meta` reader coverage.** It adds regression tests for both catalog consumers (`16-03-PLAN.md:337-354`); their current mechanisms naturally ignore `_meta`.
- **RESOLVED — full verification scheduling.** Unit verification occurs here and the aggregate gates are in 16-06.
- **PARTIALLY RESOLVED — Claude catalog-to-runtime freshness.** This plan creates the `cached_runtimes` seam and the correct TTL-or-schema logic (`16-03-PLAN.md:165-174`), but the phase-wide convergence remains incomplete because of the 16-04 catalog-materialization issue below.
- **NOT RESOLVED, accepted deferral — per-writer temporary files.** The code remains concurrency-unsafe by design (`16-03-PLAN.md:482-485`); that is acceptable only while the unsupported-concurrency contract remains true.

### Strengths

- Correctly leaves shared `cache_is_stale` unchanged (`cache.py:32-36`).
- Uses OR refresh semantics: stale TTL or old schema triggers refresh.
- Separates catalog metadata before existing functions iterate model entries.
- Protects `_meta` from accidental confirmation or correction writes.
- Tests invalid JSON, non-object caches, old versions, newer compatible versions, and source-fetch failures.
- Documents why the catalog version belongs under `_meta` rather than as an ordinary entry.

### Concerns

- No independent blocker inside this plan.
- Its ultimate success depends on 16-04 correctly closing the catalog-to-runtime dependency, which the current revision only partially achieves.

### Suggestions

- Keep 16-03 ordered before 16-04.
- Do not mark D-12 fully verified until the revised 16-04 tracer includes a catalog ID not present in the dated fallback and proves it becomes a usable catalog entry.

### Risk Assessment

**MEDIUM.** The migration itself is careful, but it changes a shared persistent format and participates in the unresolved Claude bootstrap path.

## 16-04

### Summary

The revision fixes the narrow stale-`runtimes.json` problem and significantly improves source labeling and hermeticity. However, it does not complete the actual catalog bootstrap needed for Phase 17 scoring. The tracer masks this because every models.dev ID in the test is already present in the dated fallback.

### Cycle-1 dispositions

- **PARTIALLY RESOLVED — real-order Claude freshness handoff.** `claude_runtime_is_current` correctly invalidates a fresh runtime snapshot when catalog metadata changes (`16-04-PLAN.md:209-242`), and the tracer now uses detect → fetch → detect (`:244-276`).
- **PARTIALLY RESOLVED — catalog and runtime cache dependency.** Runtime IDs converge, but catalog entries for newly learned non-fallback IDs do not.
- **RESOLVED — executor-visible verification scheduling.** Unit gates are in this plan and full gates are scheduled in 16-06.
- **NOT RESOLVED — same-run second detection/fetch convergence.** The plan explicitly defers this to Phase 17 (`16-04-PLAN.md:482-485`), but the source trace shows that another detect alone is insufficient.

### Strengths

- Aliases are kept separate from full IDs, preventing bogus `anthropic/opus` catalog matches (`16-04-PLAN.md:103-113`).
- Claude is never executed; the catalog is read lazily only when Claude is installed.
- Fallback provenance is explicit through `models_source` and `models_as_of`.
- The freshness comparison includes aliases, IDs, source, and date, with no-loop tests.
- It uses the standard catalog path through injected `env_fn`, avoiding real user caches.

### Concerns

- **HIGH — new catalog IDs are learned but not materialized as scored catalog entries.** Current `fetch-model-catalog` builds `discovered` exclusively from the runtime snapshot’s `models` arrays (`cli.py:740-745`) and calls `build_model_catalog` only for those candidates (`cli.py:800-802`). On the first upgraded run, Claude contains only the four fallback IDs. The fetch records every Anthropic ID into `_meta`, but it builds entries only for fallback candidates. The second detect updates `runtimes.json` to the full ID list, yet the plan does not fetch again (`16-04-PLAN.md:268-274`). A subsequent `fetch-model-catalog --if-stale` skips models.dev because the fetch marker is fresh (`cli.py:781-785`), so non-fallback IDs become unmatched rather than enriched until the TTL expires.
- The tracer cannot detect this because its only IDs—`claude-opus-5-5` and `claude-sonnet-5`—are already in `CLAUDE_FALLBACK_MODEL_IDS` (`16-04-PLAN.md:184-185`, `:251-267`).
- This conflicts with the stated purpose that full IDs are needed “for scoring” (`16-04-PLAN.md:81-83`) and with Phase 17’s adapter, which is specified to run one detect plus one fetch (`docs/.../2026-09-23-gsd-curated-config-v2-design.md:97-99`).

### Suggestions

- Make the first successful models.dev fetch add the fetched Anthropic IDs to discovery when Claude is installed, so their entries are built during that same fetch; or introduce an explicit candidate-set freshness key that forces a second real fetch after runtime IDs change.
- Extend the tracer with `claude-new-not-in-fallback` and assert all of the following:

  - it appears in `_meta.anthropic_model_ids`;
  - the subsequent runtime snapshot lists it;
  - `anthropic/claude-new-not-in-fallback` exists as a validated catalog entry;
  - Phase 17 can score it without waiting for the fetch TTL.

- Update the erratum at `16-04-PLAN.md:354-360`; another detect alone does not currently complete catalog convergence.

### Risk Assessment

**HIGH.** The plan meets the enumeration-labeling requirement but can leave most current Anthropic IDs unavailable for scoring for up to the catalog TTL.

## 16-05

### Summary

The source-order design is mostly sound and the revised verbose parser is substantially safer. Header-to-object validation, non-zero-exit rejection, partial parsing, and unmatched propagation are now covered. A remaining provenance ambiguity can preserve stale runtime capability values.

### Cycle-1 dispositions

- **RESOLVED — unmatched `image_input`.** Runtime metadata is now applied to both unmatched paths and the wizard copies it into confirmed entries (`16-05-PLAN.md:298-311`, `:336-344`).
- **RESOLVED — non-zero verbose exit.** The new parser wrapper rejects it (`16-05-PLAN.md:287-293`).
- **RESOLVED — header/object attribution.** A block is accepted only when its header equals `providerID/id` (`16-05-PLAN.md:279-286`).
- **RESOLVED — large-output expectation.** The parser walks by index and has a generated 110-block performance test (`16-05-PLAN.md:285-287`, `:322-330`).
- **PARTIALLY RESOLVED — fixture provenance.** Command, version, date, retained fields, and privacy rationale are documented (`16-05-PLAN.md:313-321`), but regeneration remains manual.
- **RESOLVED — repository gate scheduling.** Unit checks occur here; the full gate is in 16-06.

### Strengths

- Keeps `image_input` optional, so old catalog entries remain valid.
- Correctly distinguishes unknown from a sourced `False`.
- Uses models.dev first and runtime metadata only when models.dev made no statement.
- The clear-on-`None` design aligns with current merge behavior at `model_catalog.py:145-158`.
- The parser is linear, bounded by a subprocess timeout, and rejects mismatched headers.
- The test matrix covers matched, unmatched, router, malformed, source outage, source precedence, and performance paths.

### Concerns

- **MEDIUM — the cache does not remember which source supplied `image_input`.** Task 1 preserves cached `image_input` whenever models.dev is skipped or unavailable (`16-05-PLAN.md:167-176`). Task 2 then lets runtime metadata replace it only when the entry lacks a boolean, except on the router path (`16-05-PLAN.md:298-307`). Consider this sequence:

  1. models.dev matches a non-router model but has no modalities;
  2. opencode runtime metadata supplies `image_input: true`;
  3. that value is cached;
  4. a later runtime snapshot reports `false`, while models.dev fetch is skipped;
  5. the cached `true` is copied as though models.dev owned it, and `_apply_runtime_meta` refuses to replace it.

  The result is stale capability data in a field Phase 17 uses as an eligibility gate.

### Suggestions

- Track field-level provenance, such as `image_input_source: models_dev|opencode`, or keep independently sourced values until precedence is resolved.
- Add a transition test for a non-router, models.dev-matched-without-modalities candidate whose runtime value changes `True → False` during a fetch-skipped run.
- Preserve cached models.dev assertions during outages, but allow a newly observed runtime value to replace a cached runtime-derived value.

### Risk Assessment

**MEDIUM.** Normal fresh-fetch behavior is strong, but stale capability data could lead Phase 17 to select or reject a vision agent incorrectly.

## 16-06

### Summary

The ranker work is thorough: aliases, backward-compatible partial files, bool-safe numeric validation, raw-score floors, purity, and invalid-UTF-8 fallback are all well planned. The final repository gate is now scheduled, but its failure-classification rule is unsafe and can mislabel phase-caused integration failures as pre-existing.

### Cycle-1 dispositions

- **RESOLVED — missing full gates.** Task 3 now runs the actual aggregate `make test` and `make validate` (`16-06-PLAN.md:375-420`), matching `Makefile:42-66`, `:119-122` and `AGENTS.md:121-134`.
- **RESOLVED — booleans accepted as numbers.** `_is_finite_number` is shared by axes, bonuses, floors, and candidate floor checks (`16-06-PLAN.md:179-189`, `:294-311`).
- **RESOLVED — `review` self-alias ambiguity.** Only aliases whose canonical name differs are moved, with a dedicated test (`16-06-PLAN.md:168-178`, `:243-245`).
- **RESOLVED — `skill-judge` ownership.** It remains a blocking orchestrator gate and is reported as pending, as explicitly permitted by the review instructions (`16-06-PLAN.md:501`).

### Strengths

- The plan directly fixes the current bool hole at `model_ranker.py:51-61`.
- It preserves legacy hand-built `execute` dictionaries while canonicalizing loaded TOML.
- Missing new purposes are filled from independent deep copies of defaults.
- Floors are applied before normalization, preventing excluded candidates from shifting survivor scores.
- Missing, boolean, nonnumeric, or unknown floor axes are rejected.
- Invalid UTF-8 is added to the loader’s never-raise contract; current handling only catches `OSError` and TOML errors (`model_ranker.py:64-79`).
- The floor and alias consequences are explicitly documented for Phase 17.

### Concerns

- **HIGH — Task 3’s path-based gate triage is not causal analysis.** The plan says a failure is phase-caused only when the test module, traceback, or hook mentions a `PHASE_FILES` path; every other failure is declared pre-existing (`16-06-PLAN.md:393-400`). A change to shared CLI output or cache shape can break an installer, PTY, or integration test whose failure mentions only its own test file. The acceptance criteria repeat the same unsafe inference (`16-06-PLAN.md:423-425`). This can produce a “completed” phase with a real regression, contrary to `AGENTS.md:60-63`.
- **LOW — a stale ranker docstring is left behind.** Current `score_candidates` says absent axes are excluded and weights renormalized (`model_ranker.py:109-117`), but the code actually substitutes `_MISSING_AXIS_DEFAULT` for every missing axis (`model_ranker.py:144-148`). The plan updates the purpose line but does not correct this false behavior description.

### Suggestions

- Treat every newly failing full-gate test as phase-caused unless it is reproduced at `PHASE_BASE`. Make the detached-worktree comparison mandatory for failures outside `PHASE_FILES`, not optional.
- Allow causally required downstream test or documentation fixes to extend `PHASE_FILES` with an explicit justification; do not prohibit them solely because they were not predicted before running the gate.
- Update the `score_candidates` docstring to describe the 49-point missing-axis default and clarify that floor validation occurs before that default is relevant.

### Risk Assessment

**HIGH.** The ranker implementation plan is strong, but the final completion gate can incorrectly excuse real cross-component regressions.

## Cross-plan assessment

The cycle-2 revision resolves most cycle-1 findings, especially subprocess exit handling, unmatched metadata propagation, confidence labeling, `_meta` reader coverage, numeric validation, `skill-judge` ownership, and actual full-gate scheduling.

Three changes are needed before execution:

1. **16-04 HIGH:** make newly learned non-fallback Claude IDs become enriched catalog entries, not merely runtime IDs.
2. **16-06 HIGH:** replace path-based failure classification with mandatory baseline reproduction or equivalent causal evidence.
3. **16-05 MEDIUM:** preserve field-level source provenance so runtime-derived `image_input` can change during a models.dev-skipped run.

The serial six-wave ordering remains appropriate because the plans intentionally build on the same `detection.py`, `cli.py`, cache format, and central test module.

**Overall phase risk: HIGH until 16-04 and 16-06 are revised.** No files were modified during this review.

---

## Consensus Summary

Only one prompt-fed, source-grounded reviewer produced a review this cycle (codex-sol-high). The
opencode-plan-review lane failed for environment reasons (see Lane notes). So there is no
cross-reviewer consensus: "Agreed" below means the codex reviewer and the orchestrator's own
source-grounding pass agree. The codex review has no `[reviewed-without-source-citations]` or
`[reviewed-without-repo-access]` marker, so it counts at full weight. Codex rates the phase
**HIGH risk until 16-04 and 16-06 are revised**. It also says the revision resolves most cycle-1
findings.

### Cycle-1 finding status (codex dispositions, checked by the orchestrator)

- Agreed Concern 1 (HIGH, Claude catalog→runtimes freshness edge): **PARTIALLY RESOLVED**.
  `claude_runtime_is_current` plus the real-order tracer fix the stale-`runtimes.json` half. The
  remainder is new HIGH 1 below, and it is not counted twice.
- Agreed Concern 2 (HIGH, skill-judge gate): **RESOLVED**. The gate is an orchestrator-owned
  blocking gate stated in each affected plan's `<objective>` (16-01:121-129, 16-02:112-120,
  16-05:124-129, 16-06:118-123), and every SUMMARY lists it under `## Pending orchestrator gates`.
- Agreed Concern 3 (HIGH, `make test` never executor-visible): **RESOLVED**. `make test-unit`
  runs in every plan's final task. 16-06 Task 3 runs `make test` (all four tiers,
  `Makefile:66`) and `make validate` (`Makefile:122`). Task 3's triage rule raises new HIGH 2.
- Agreed Concern 4 (HIGH, false concurrent-writer claim): **RESOLVED**. The truth now reads
  "single-writer atomic replace; concurrent writers unsupported", which matches `cache.py:26`.
  The code change is deferred with rationale.
- Agreed Concern 5 (MEDIUM, bool weights): **RESOLVED** (`_is_finite_number` for axes, bonuses
  and floors).
- Cycle-1 single-reviewer items: unmatched-branch metadata (16-01, 16-05), returncode (16-01,
  16-05), `OPENCODE_PID` docstring, header/id check, "exactly one refresh" wording, sibling
  `_meta` tests, `review` self-alias wording, and the verbose-parse size test are all **RESOLVED**.
  Fixture provenance is **explicitly rejected with rationale** (vendor prompt text and private
  router endpoints must not be committed; inline provenance recorded instead). Codex calls it
  "partially resolved" and raises only a LOW, which the rejection covers.

### Agreed Concerns (codex + orchestrator source verification)

1. **HIGH: newly learned anthropic ids never become catalog entries in the real refresh order
   (16-04).** `fetch-model-catalog` builds `discovered` only from the runtimes snapshot's
   `models` arrays (`cli.py:740-745`) and only builds entries for those (`cli.py:800-802`). On
   the first upgraded run, `clis.claude.models` holds only the four fallback ids, so the fetch
   records every anthropic id in `_meta` but builds entries only for the fallback four. The
   next `detect-runtimes --if-stale` then lists every id. The next `fetch-model-catalog
   --if-stale` skips models.dev because the sidecar `fetch-meta.json` is fresh (`cli.py:781-785`),
   so `models_dev_ok` is False and any non-fallback id becomes `unmatched` until the catalog TTL
   runs out. The 16-04 tracer cannot catch this: both of its models.dev ids (`claude-opus-5-5`,
   `claude-sonnet-5`) are already in `CLAUDE_FALLBACK_MODEL_IDS`. The 16-04 erratum and ledger
   ("a caller may call `detect-runtimes --if-stale` once more") therefore overstate convergence.
   Fix options: (a) when claude is installed and models.dev succeeded, add the fetched anthropic
   ids to `discovered` in the same fetch so their entries are built immediately; or (b) add a
   candidate-set freshness key that forces a real fetch when the runtime candidate set changes.
   Also extend the tracer with an id that is NOT in the fallback list, and assert that
   `anthropic/<that id>` exists as a validated catalog entry after the standard sequence.
2. **HIGH: 16-06 Task 3's failure triage is path-based, not causal.** A failure counts as
   phase-caused only when its test module, traceback or hook finding names a `PHASE_FILES` path.
   Everything else is declared pre-existing, and the `PHASE_BASE` worktree reproduction is only
   optional ("When unsure, you may…"). A Phase 16 change to shared CLI output or cache shape can
   break an integration, PTY or installer test whose traceback names only its own test file. The
   acceptance criteria repeat the inference. Fix: make the `PHASE_BASE` reproduction MANDATORY
   for every failure outside `PHASE_FILES` (pre-existing only if it also fails at `PHASE_BASE`).
   Also allow a causally required fix outside `PHASE_FILES` when it is justified explicitly in
   the SUMMARY.

### Divergent Views

- Not applicable: only one reviewer produced a review this cycle.

### Other codex findings

- **MEDIUM (16-05): `image_input` has no field-level provenance, so a runtime-derived value can
  go stale.** Take a non-router model that models.dev matches but that has no `modalities`, so
  its `image_input` came from opencode runtime metadata. On a later fetch-skipped run,
  `_preserved_or_fresh_md_fields` copies the cached value as if models.dev owned it (16-05 Task 1
  Step 2). `_apply_runtime_meta` (default `runtime_wins_image_input=False`) then refuses to
  replace it with a new runtime reading (16-05 Task 2 Step 3). A True→False change is lost, and
  this field is a Phase 17 eligibility gate. Fix: record `image_input_source` (`models_dev` or
  `opencode`), or let a runtime reading replace a cached runtime-derived value. Add a
  fetch-skipped True→False transition test. The orchestrator confirmed the premise against the
  plan text.
- **LOW (16-06): the `score_candidates` docstring is already false and the plan leaves it
  false.** The docstring says absent axes are "excluded from the weighted sum and the remaining
  weights renormalize" (`model_ranker.py:110-112`). The code actually substitutes
  `_MISSING_AXIS_DEFAULT` (49.0) for every missing axis (`model_ranker.py:144-145`). 16-06
  changes the purpose line but not this sentence. Fix: rewrite it in 16-06 Task 1 to describe the
  49.0 default and say that floors are checked on raw values before that default applies.
- **LOW (16-01, 16-05): fixture reproducibility.** Codex suggests recording a hash of the raw
  capture plus a redaction recipe. Not counted: the ledgers explicitly reject committing or
  regenerating from the raw captures, with rationale.
- **LOW (16-02): duplicated `_VALID_NATIVE_RUNTIME` allow-lists.** Not counted: the plan already
  pins them with an equality test.
- Explicit deferrals codex accepted: existing opencode/cursor returncode handling (16-01 ledger)
  and a per-writer `mkstemp` cache writer (16-03 ledger).

## Verification coverage

Source-grounding pass (`plan_review.source_grounding: true`; effective authority `grep` from
`gsd-tools drift-guard authority`). The orchestrator ran it against the working tree at `8834ead`.
Cycle 1's full symbol inventory (see 6789a06) still applies to the unchanged citations. This
cycle re-verified every existing-code symbol that the `8834ead` revision added. New symbols in
16-01's phase-wide "Artifacts this phase produces" table (for example `_apply_runtime_meta`,
`claude_runtime_is_current`, `_is_finite_number`, `TestCodexEnumerationEndToEnd`) are excluded.

### VERIFIED (existing symbols the revision cites)

- `cache.py`: `cache_write_json` :21, fixed temp path `tmp = path + ".tmp"` :26 (the ledgers say
  `:25`; that is off by one and not material), `os.replace` :29; `cache_is_stale` :32.
- `cli.py`: both `unmatched.append` sites that 16-01 and 16-05 extend, :270 (router
  vendor-unknown branch) and :410 (ordinary branch, the `cli.py:409` the plans cite);
  `merge_catalog_entry` call sites :311 and :476; `fetch-model-catalog` discovery from runtimes
  `models` :740-745; `fetch_meta_path` / `skip_fetch` :781-782; `build_model_catalog` call
  :800-801; `detect-runtimes` early return :717.
- `cross_reference.scan_catalog` (`ai_kit_opencode_providers/cross_reference.py:64`) and test
  scaffolding `TestCrossReferenceCatalog` :895, `_XrefScratch` :852, `_write_file` :823
  (`tests/test_ai_kit_opencode_providers.py`).
- `pricing.estimate_price` (`ai_kit_usage_metrics/pricing.py:16`, `catalog.get(canonical_key(...))`
  :34); `ai_kit_usage_metrics.paths.catalog_path` (`paths.py:106`); `TestPricing`
  (`tests/test_ai_kit_usage_metrics.py:2523`).
- `model_ranker.py`: `_REQUIRED_BONUS_FIELDS` :39, `_is_valid_weights_structure` :42 (bool hole
  :55), `score_candidates` :109 (docstring :110-112 vs `_MISSING_AXIS_DEFAULT` use :144-145).
- `TestBuildRuntimesSnapshot.test_lists_opencode_models_when_installed`
  (`tests/test_ai_kit_spec.py:1118`).
- Makefile targets that 16-06 Task 3 and the per-plan gates run: `test-unit` :45,
  `test-integration` :51, `e2e-test`, `arch-test`, the aggregate `test` :66 (four tiers), `lint`
  :68, and `validate` :122 (ruff, pylint, pyright, vulture, shellcheck, py-compile, unittest,
  unittest-wizard). This supports 16-06's claim that `make validate` subsumes `make lint`'s
  shellcheck and py-compile checks.
- `cli-model-selection.md` item 4, "Unmatched-candidate research and confirmation" (:104), which
  16-01 Step 2 and 16-05 Step 5 extend.
- The `PHASE_BASE` recipe `git log --grep='(16-01):'` matches no commit today (checked with raw
  git output), so it will resolve to the first real `feat(16-01)` commit once execution starts.

### MISSING / AMBIGUOUS

- **Inaccurate relational claim (LOW, needs acknowledgement), 16-03.** A must_haves truth
  (16-03-PLAN.md:39), the objective (:101) and a Task 1 test description (:205) say
  `cache_is_stale` is "shared with quota.py". `quota.py` imports only `cache_base` (`quota.py:6`).
  `cache_is_stale`'s only callers are `cli.py:717` and `cli.py:782`. The 16-03 deferral ledger
  also says `cache_write_json` is "shared with `quota.py`". In fact it is shared with the cli.py
  quota write (:859), `dispatch.py:201` and the execute adapters (`ai_kit_spec_gsd`,
  `ai_kit_spec_superpowers`). The design conclusion (keep both helpers generic; changing the
  writer widens scope beyond D-12) still holds. Only the named consumer is wrong. Fix: name the
  real consumers.

### UNCHECKABLE (INFO: the `grep` authority cannot assert these)

- Signatures and keyword defaults of new or extended functions (`build_runtimes_snapshot(...,
  catalog_fn=None)`, `_apply_runtime_meta(..., runtime_wins_image_input=False)`): the plans'
  own verify commands cover them.
- Whether `make test`'s `e2e-test` / `test-integration` tiers can run in the cross-AI executor's
  session (PTY allocation, `uv` offline venv). 16-06 reports these as environment limitations
  instead of working around them.
- External facts carried from cycle 1 (codex-cli 0.147.0 `debug models` shape, opencode 1.18.32
  `--verbose` shape, models.dev anthropic ids, `PI_CODING_AGENT` / `CODEX_THREAD_ID`): verified
  against real captures in cycle 1 and not re-captured this cycle.

### Cross-artifact fact-drift pass

- Phase status (`gsd-tools drift-guard phase-status --phase 16`): **uncheckable**
  (`reason: phase_not_in_roadmap`; STATE.md says "Ready to execute"). The seam cannot parse
  ROADMAP.md's `- [ ] **Phase 16: ...**` entry. The axis was skipped, not found consistent.
- ROADMAP Success Criteria ↔ `must_haves.truths`: no contradiction. The `8834ead` ROADMAP edits
  (16-04 "catalog-aware `--if-stale`", 16-06 "phase gate") match the revised plans. SC2's
  "claude (hardcoded aliases + catalog full ids + dated fallback)" matches 16-04's truths. (New
  HIGH 1 is about whether catalog ids become scoreable entries. That is a correctness gap, not a
  contradiction between artifacts.)
- ROADMAP `**Requirements:**` (SPEC-01..04) ↔ plan requirement refs: consistent, unchanged from
  cycle 1.
- CONTEXT.md Decisions ↔ plan usage: no contradiction. 16-04's catalog-aware skip adds to D-12
  ("schema_version ... staleness") and does not contradict it. The cycle-1 D-09 advisory
  (16-05 also fills a models.dev match that lacks `modalities`) still stands. New MEDIUM (16-05
  provenance) is where that widening becomes a correctness issue.
- Advisory only: this pass contributes nothing to `current_high` / `current_actionable`.

## Cycle accounting (orchestrator)

- Consensus gate: **not engaged**, because exactly one reviewer (codex-sol-high) produced a
  review section; opencode-plan-review failed for environment reasons. The single reviewer's
  HIGHs count as-is. Both HIGH premises were also confirmed against source by the orchestrator.
- `current_high = 2`: (1) 16-04 newly learned anthropic ids are not materialized as catalog
  entries in the real refresh order; this is the unresolved remainder of cycle-1 Agreed
  Concern 1, counted once; (2) 16-06 Task 3's path-based, non-causal failure triage. Cycle-1
  HIGHs 2-4 are fully resolved.
- `current_actionable = 3`: (1) 16-05 `image_input` provenance / stale runtime value (MEDIUM);
  (2) 16-06 `score_candidates` docstring still describes renormalization (LOW); (3) 16-03 "shared
  with quota.py" relational inaccuracy in a truth, the objective and the ledger (LOW,
  source-grounding). Not counted: the fixture-reproducibility LOW (covered by the explicit
  ledger rejection), the duplicated allow-list LOW (already pinned by an equality test), the
  accepted deferrals, and the advisory fact-drift items.
