---
phase: 16
cycle: 3
reviewers: [opencode-plan-review, codex-sol-high]
reviewed_at: 2026-09-24T11:45:39Z
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

> This is cycle 3 (the final cycle) of plan-review convergence. It reviews the plans as revised in
> `9a0f0fc`. The cycle-1 review (`6789a06`) and the cycle-2 review (`92c2ef4`) are kept in git
> history. Each PLAN.md's "Review Dispositions Ledger" cites them by line (`L<n>@<sha>`).
>
> Lane notes (environment findings, not plan findings). Both reviewers came from
> `review.default_reviewers`: `opencode-plan-review` (opencode, `router-env/my-plan-review`) and
> `codex-sol-high` (codex, `gpt-5.6-sol`). No lane was substituted, and the xai/grok lane was not
> used.
> - **codex-sol-high:** full review in about 8 minutes (08:18 to 08:26 -03). It got the full
>   inlined prompt (336 KB: plans, CONTEXT.md, roadmap, requirements, with RESEARCH.md and the
>   cycle-2 REVIEWS.md referenced on disk). It covers all six plan ids and cites `file:line`
>   evidence.
> - **opencode-plan-review:** full review in about 26 minutes (08:18 to 08:44 -03). It got a
>   compact 11 KB prompt that pointed at the plans, RESEARCH.md, the cycle-2 REVIEWS.md and
>   `git show 9a0f0fc` on disk. The router backend was reachable this cycle, unlike cycle 2. The
>   opencode log showed steady tool-loop progress (steps 6 to 18 and later), so no probe or retry
>   was needed. It covers all six plan ids and cites `file:line` evidence.
> - The two lanes ran at the same time. They use different providers, so they share no rate
>   limit.
> - **Effect on counting:** two reviewers produced a review section, so the consensus gate
>   engages. Neither section opens with a `[reviewed-without-source-citations]` or
>   `[reviewed-without-repo-access]` marker, so both count at full weight.
> - The working tree was unchanged after both read-only runs (`git status`: only the pre-existing
>   `.planning/state.json` modification).

## OpenCode Review (opencode-plan-review)

## 16-01

### Summary

The Codex enumeration plan remains implementation-ready. It follows existing subprocess-injection patterns, preserves reasoning metadata through matched and unmatched paths, and explicitly rejects unsuccessful subprocess results.

### Cycle-2 dispositions

- **RESOLVED — provisional failure classification.** Failures outside this plan’s files are now marked provisional until 16-06 reproduces them at `PHASE_BASE` (`.planning/phases/16-ai-kit-spec-extensions/16-01-PLAN.md:112-122`, `:645-651`).
- **RESOLVED — phase-wide artifact table.** It now includes the 16-04 materialization/provider-hint additions and 16-05 provenance field (`16-01-PLAN.md:547-562`, `:651`).
- **EXPLICITLY REJECTED WITH VALID RATIONALE — raw fixture/hash workflow.** The plan records command, version, date, retained fields, substitutions, and omission rationale without committing the 259 KB vendor prompt payload (`16-01-PLAN.md:277-290`, `:653-656`).
- **EXPLICITLY DEFERRED WITH VALID RATIONALE — stricter existing opencode/cursor return-code handling.** D-06 preserves those existing paths while the new Codex parser gets the stricter gate (`16-01-PLAN.md:217-240`, `:639-643`).

### Strengths

- The proposed Codex invocation uses an argv list, the PATH-resolved executable, a 15-second timeout, and no shell (`16-01-PLAN.md:208-221`). This matches the existing injected subprocess seams in `skills/ai-kit-spec-review/ai_kit_spec/detection.py:74-106`.
- The plan reuses the existing `reasoning_modes` schema instead of introducing a competing field (`16-01-PLAN.md:248-275`; `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:18-23`).
- Both current unmatched exits are explicitly targeted for metadata propagation (`16-01-PLAN.md:262-269`); those exits currently occur at `skills/ai-kit-spec-review/ai_kit_spec/cli.py:270-274` and `:409-413`.
- The fixture/parser tests cover hidden models, duplicate slugs, malformed levels, nonzero exits, missing return codes, and instruction-payload leakage (`16-01-PLAN.md:305-322`, `:358-393`).

### Concerns

- **No new blocking concern found.**

### Suggestions

- Execute as written.
- Preserve the explicit test that catalog files never contain `model_messages` or `instructions_template`; the external response is much larger and more sensitive than the data actually needed.

### Risk Assessment

**LOW.** The plan is narrow, hermetic, and well covered. Remaining fixture provenance limitations are explicitly accepted and do not affect runtime correctness.

## 16-02

### Summary

This remains a strong table-driven host-detection plan. It changes the precedence tuple, closes both downstream `"pi"` validation gaps, and tests both individual signals and nested-session precedence.

### Cycle-2 dispositions

- **RESOLVED — provisional failure classification.** Per-plan failures are no longer finally labeled pre-existing; 16-06 owns causal classification (`.planning/phases/16-ai-kit-spec-extensions/16-02-PLAN.md:103-113`, `:414-419`).
- **EXPLICITLY DEFERRED WITH VALID RATIONALE — duplicated `_VALID_NATIVE_RUNTIME` sets.** The definitions remain duplicated, but the plan permanently pins equality between them (`16-02-PLAN.md:195-200`, `:235-236`, `:421-424`). Current source confirms the two independent definitions at `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:39` and `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:96-97`.

### Strengths

- The exact six-row tuple correctly represents Codex’s two independent signals and required precedence (`16-02-PLAN.md:156-166`).
- It preserves the architectural distinction between current host detection and installed CLI detection; the plan explicitly leaves `KNOWN_CLIS` unchanged (`16-02-PLAN.md:165-166`, `:255-263`), matching `AGENTS.md:67-71`.
- The tracer verifies the complete detection → validator → TOML-render path for `"pi"`, not just the pure detection return value (`16-02-PLAN.md:208-224`).
- Confidence labels are tied to the actual tuple and checked for invented signal names such as `OPENCODE_PID` (`16-02-PLAN.md:262-283`).

### Concerns

- **No new blocking concern found.**

### Suggestions

- Keep the validator-set equality assertion as a permanent regression test.
- Preserve the exact tuple assertion; it protects both adjacency and the two-row Codex representation.

### Risk Assessment

**LOW.** The behavior is data-driven, exhaustively pinned, and consistent with the current module boundaries.

## 16-03

### Summary

The cache migration is carefully designed. It keeps TTL logic generic, introduces schema-aware refresh at the CLI boundary, isolates catalog metadata under `_meta`, and preserves backward compatibility for existing catalogs and sibling readers.

### Cycle-2 dispositions

- **RESOLVED in the operative plan — false “shared with quota.py” claim.** The current truth, objective, test description, and threat entry now identify the real consumers and correctly state that `quota.py` imports only `cache_base` (`.planning/phases/16-ai-kit-spec-extensions/16-03-PLAN.md:39`, `:101-108`, `:212-214`, `:438`, `:496-502`).
- **RESOLVED — provisional failure classification.** Final classification is delegated to 16-06’s baseline reproduction (`16-03-PLAN.md:121-131`, `:502`).
- **RESOLVED CROSS-PLAN — Claude cache convergence.** This plan creates the `cached_runtimes` and `_meta` seams; revised 16-04 now performs same-fetch entry materialization (`16-03-PLAN.md:80-83`, `:507`; `16-04-PLAN.md:299-320`).
- **EXPLICITLY DEFERRED WITH VALID RATIONALE — concurrent cache writers.** The plan now claims only single-writer atomic replacement and accurately declares the fixed temporary path unsafe for concurrent writers (`16-03-PLAN.md:35`, `:87-91`, `:437-439`, `:491-494`). Current implementation uses one fixed `<path>.tmp` before `os.replace` (`skills/ai-kit-spec-review/ai_kit_spec/cache.py:21-29`).

### Strengths

- The proposed refresh condition correctly requires fresh TTL **and** current schema before skipping, so either stale condition forces refresh (`16-03-PLAN.md:172-183`). The current skip seam is exactly where expected at `skills/ai-kit-spec-review/ai_kit_spec/cli.py:716-725`.
- `_meta` is split before model-entry iteration, which is necessary because current loops call entry methods directly (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:79-82`; `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:162-172`).
- The plan covers every catalog-writing command—fetch, confirmation, and heuristic correction—so `_meta` cannot disappear on a later write (`16-03-PLAN.md:275-289`).
- Sibling-reader regression tests target the actual access patterns rather than merely asserting that `_meta` exists (`16-03-PLAN.md:345-363`).

### Concerns

- **LOW — the grounding research still contains the corrected false claim.** Executors are told to read `16-RESEARCH.md` (`16-03-PLAN.md:141-148`), but that document still says `cache_is_stale` is shared with `quota.py` at `.planning/phases/16-ai-kit-spec-extensions/16-RESEARCH.md:153` and `:496-502`. Current source contradicts it: the TTL checks are in `skills/ai-kit-spec-review/ai_kit_spec/cli.py:717` and `:782`, while `quota.py` imports only `cache_base`. The Round-2 ledger supersedes the plan wording, but not this upstream grounding text.

### Suggestions

- Correct `16-RESEARCH.md:153` and `:496-502` before execution so the executor does not receive contradictory authoritative context.
- Optionally annotate the old Round-1 deferred wording at `16-03-PLAN.md:494` as superseded inline, rather than relying solely on the later ledger entry.

### Risk Assessment

**MEDIUM.** The implementation mechanism is sound, but this changes shared persistent formats and still carries one contradictory grounding claim.

## 16-04

### Summary

The revision substantively resolves the cycle-2 bootstrap defect. The first successful models.dev fetch now records Anthropic IDs and materializes their catalog entries in the same transaction, including IDs absent from the dated fallback.

### Cycle-2 dispositions

- **RESOLVED — non-fallback Anthropic IDs lacked catalog entries.** Extra Claude candidates are passed into `build_model_catalog` during the recording fetch, while remaining outside caller-visible discovery scope (`.planning/phases/16-ai-kit-spec-extensions/16-04-PLAN.md:299-320`).
- **RESOLVED — tracer masked the issue by using fallback IDs only.** The revised tracer includes `claude-new-not-in-fallback` and verifies entry creation, validation, runtime convergence, skipped refetch, and ranking visibility (`16-04-PLAN.md:322-380`).
- **RESOLVED — reseller collision.** Claude candidates receive an Anthropic-only tie-breaking hint (`16-04-PLAN.md:288-297`). Current matching behavior otherwise returns `None` for ambiguous provider matches (`skills/ai-kit-spec-review/ai_kit_spec/model_matcher.py:96-142`).
- **RESOLVED — false “one more detect completes convergence” statement.** Another detection is now sufficient because the prior fetch has already built every catalog entry; the erratum also documents the installed-after-fetch exception (`16-04-PLAN.md:471-485`, `:624-631`).
- **RESOLVED — provisional failure classification.** Final pre-existing status belongs to 16-06 (`16-04-PLAN.md:178-188`, `:632`).

### Strengths

- The fix targets the actual current bottleneck: discovery currently comes only from runtime `models` arrays and only those candidates enter `build_model_catalog` (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:740-745`, `:800-802`).
- Scope isolation is explicit and tested: internal materialization candidates do not alter printed `discovered` or `unmatched` (`16-04-PLAN.md:303-316`, `:429-432`).
- The provider hint is narrowly scoped to Claude; all other CLIs preserve collision-safe current behavior (`16-04-PLAN.md:293-297`, `:431-432`).
- The real-order tracer covers detect → fetch → detect → skipped fetch → skipped detect and proves the new ID is scoreable through `current_candidate_keys` (`16-04-PLAN.md:345-380`).
- Claude remains non-executable throughout enumeration (`16-04-PLAN.md:251-257`, `:379-380`).

### Concerns

- **MEDIUM — malformed Anthropic model rows can violate the “every recorded ID has an entry” invariant or crash the fetch.** `_anthropic_model_ids` accepts every nonblank key from an Anthropic `models` dictionary (`16-04-PLAN.md:285-287`), but current matching spreads each selected model value as a dictionary (`skills/ai-kit-spec-review/ai_kit_spec/model_matcher.py:121-134`). A `null`, list, string, or malformed `limit` value can therefore fail during matching/enrichment. `fetch_models_dev` validates JSON transport, not the response schema (`skills/ai-kit-spec-review/ai_kit_spec/model_sources.py:30-38`). The plan stamps all extracted IDs into `_meta` and filters their internal unmatched records without testing malformed per-model rows (`16-04-PLAN.md:307-320`).

### Suggestions

- Add a malformed-Anthropic-row test with one valid sibling and values such as `null`, a string, and an invalid `limit`.
- Record an ID in `_meta.anthropic_model_ids` only if its row can be materialized into a validated Claude catalog entry, or fail the fetch without stamping the new ID set.
- Assert after every successful materializing fetch that each recorded ID maps to a validated `anthropic/<id>` entry carrying a Claude runtime.

### Risk Assessment

**MEDIUM.** The cycle-2 HIGH is resolved on valid source data. Remaining risk is defensive schema handling for a third-party catalog response.

## 16-05

### Summary

The provenance revision fixes the stale True→False capability transition identified in cycle 2. It distinguishes models.dev assertions from opencode runtime readings and preserves backward compatibility with source-less legacy values.

### Cycle-2 dispositions

- **RESOLVED — missing `image_input` provenance.** The plan adds optional `image_input_source`, preserves only models.dev-sourced values during source outages, and allows current runtime data to replace cached runtime-derived data (`.planning/phases/16-ai-kit-spec-extensions/16-05-PLAN.md:96-108`, `:188-220`, `:351-373`).
- **RESOLVED — requested transition coverage.** Tests cover runtime True→False, models.dev precedence, runtime silence, source-less legacy entries, and opencode-only extraction (`16-05-PLAN.md:299-303`, `:393-403`).
- **RESOLVED — provisional failure classification.** Per-plan failures remain provisional pending 16-06 (`16-05-PLAN.md:138-148`, `:550-557`).
- **RESOLVED — post-16-04 hermeticity.** Every fetch test explicitly supplies `which_fn`, preventing real PATH-dependent Claude materialization (`16-05-PLAN.md:129-132`, `:398-403`, `:557`).
- **EXPLICITLY REJECTED WITH VALID RATIONALE — raw verbose capture/hash workflow.** The raw output exposes private configured providers, while the committed fixture carries inline provenance (`16-05-PLAN.md:375-383`, `:559-562`).

### Strengths

- The plan uses the current merge distinction correctly: omitted keys preserve cached values, while incoming `None` clears stale values (`skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:143-158`; `16-05-PLAN.md:203-220`).
- Header-to-object identity validation prevents shifted verbose blocks from assigning one model’s capability to another (`16-05-PLAN.md:325-340`).
- Nonzero/missing subprocess return codes degrade to no capability map (`16-05-PLAN.md:341-346`).
- Runtime metadata is applied on both current unmatched paths, allowing later user confirmation without losing the CLI-reported capability (`16-05-PLAN.md:366-373`; current exits at `skills/ai-kit-spec-review/ai_kit_spec/cli.py:270-274` and `:409-413`).
- The generated 110-block test directly covers the observed output scale and the index-based parsing strategy (`16-05-PLAN.md:290`, `:389-392`).

### Concerns

- **MEDIUM — schema validation does not enforce provenance/value co-presence.** The plan repeatedly requires `image_input` and `image_input_source` to be written, cleared, or omitted together (`16-05-PLAN.md:33-34`, `:203-220`), but its validator tests explicitly accept `"models_dev"` or `"opencode"` independently on an entry shape without requiring boolean `image_input` (`16-05-PLAN.md:246-251`). That permits meaningless orphan provenance through `confirm-catalog-entry`, which persists any entry accepted by `validate_catalog_entry` (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:810-829`).

### Suggestions

- Reject non-null `image_input_source` unless `image_input` is a boolean.
- Continue accepting legacy `image_input` without provenance so old caches remain compatible.
- Add tests for orphan-source rejection, paired clear-on-`None`, and legacy value-without-source acceptance.

### Risk Assessment

**MEDIUM.** The cycle-2 stale-value defect is resolved, but the new field pair needs one schema-level consistency rule.

## 16-06

### Summary

The ranker work is thorough, and the revised baseline comparison fixes the original false “pre-existing” classification problem. The final gate remains unsafe, however: aggregate Make targets may stop before all required tiers run, and the acceptance criteria allow unresolved failures while simultaneously saying the gate has not passed.

### Cycle-2 dispositions

- **RESOLVED — path-only pre-existing classification.** Every failure outside `PHASE_FILES` now requires reproduction at `PHASE_BASE`; passing or differing at baseline makes it phase-caused, while inability to reproduce is unresolved rather than pre-existing (`.planning/phases/16-ai-kit-spec-extensions/16-06-PLAN.md:416-466`, `:584-590`). Treating a failure that directly names a phase-modified file as phase-caused is conservative and does not recreate the original false-excusal defect.
- **RESOLVED — `score_candidates` docstring.** The prescribed wording now matches current behavior: missing normalized axes use 49.0 and all axis weights remain in the divisor (`16-06-PLAN.md:204-213`, `:275`, `:590`; current implementation at `skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:109-148`).
- **RESOLVED — per-plan provisional classifications.** 16-06 is now the sole authority for final baseline classification (`16-06-PLAN.md:105-122`).

### Strengths

- Alias normalization preserves loaded legacy `[execute]` sections and hand-built legacy dictionaries while making `execution` canonical (`16-06-PLAN.md:175-204`, `:241-260`).
- One `_is_finite_number` rejects booleans and non-finite values across axes, bonuses, floors, and candidate scores (`16-06-PLAN.md:186-196`, `:310-327`).
- Floors run before normalization, so excluded candidates cannot distort survivor scores (`16-06-PLAN.md:317-323`).
- The baseline workflow records exact commands, result classifications, cleanup state, and justified out-of-phase fixes (`16-06-PLAN.md:421-481`).
- The planned aggregate commands correspond to the repository’s intended gates: `make test` covers four tiers and `make validate` covers all hook targets (`Makefile:45-66`, `:74-122`; `AGENTS.md:121-136`).

### Concerns

- **HIGH — aggregate Make targets may stop before later required tiers or hooks run.** `test` and `validate` are prerequisite aggregates (`Makefile:66`, `:122`). Without keep-going behavior, an early failure can prevent later prerequisites from running. The plan permits a nonzero aggregate result after classifying its visible failures (`16-06-PLAN.md:408-418`, `:491-494`), so a proven pre-existing unit-test failure could leave integration, E2E, architecture, or later validation hooks completely unexecuted and conceal phase regressions.
- **HIGH — unresolved gate failures are both blocking and accepted by completion criteria.** Step 4 correctly says an unreproducible failure is unresolved and “the gate is not passed while it stands” (`16-06-PLAN.md:448-451`). But the must-have, acceptance criteria, and `<done>` permit completion when failures are merely listed as unresolved (`16-06-PLAN.md:36`, `:491-499`). This internal contradiction can mark the phase done despite an explicitly unpassed repository gate, contrary to `AGENTS.md:60-63` and `:123-130`.
- **MEDIUM — the temporary worktree path is hardcoded.** The plan embeds `/tmp/ai-kit-p16-base.*` in generated commands and acceptance checks (`16-06-PLAN.md:421-425`, `:488-495`), while project instructions require portable discovered or passed base paths (`AGENTS.md:57-59`).
- **LOW — global `git worktree prune` is unnecessary.** After removing `$BASE_WT`, pruning may alter unrelated stale worktree metadata (`16-06-PLAN.md:452-456`). This is broader than the task needs and conflicts with preserving unrelated work (`AGENTS.md:54-56`).

### Suggestions

- Run each test tier and validation target independently, collecting all results even when an earlier target fails. At minimum: `test-unit`, `test-integration`, `e2e-test`, `arch-test`, and each validation hook target.
- Require final `make test` and `make validate` success unless every nonzero item is proven pre-existing **and every constituent tier/hook actually ran**.
- Make any unresolved gate failure block `<done>` and phase completion; reporting it is not equivalent to passing.
- Use `${TMPDIR:-/tmp}` or Python’s `tempfile` rather than embedding `/tmp`.
- Remove only the worktree created by the task; omit global `git worktree prune`.

### Risk Assessment

**HIGH.** The ranker changes themselves are well specified, and the cycle-2 causal-triage defect is resolved. The final phase gate can still omit required verification and accept an explicitly unresolved failure.

## Cross-plan assessment

The serial wave ordering remains appropriate because the plans intentionally build on shared `detection.py`, `cli.py`, catalog formats, and one central test module. Cycle-2’s primary implementation defects in 16-04, 16-05, and 16-06 are substantively addressed.

Execution should still be blocked on the two 16-06 HIGH findings. Recommended pre-execution fixes:

1. Ensure every test tier and validation hook runs even when an earlier one fails.
2. Make unresolved gate failures block plan and phase completion.
3. Add the 16-04 malformed-source-row test and 16-05 provenance/value consistency validation.
4. Correct the stale `quota.py` consumer claims in `16-RESEARCH.md`.

**Overall phase risk: HIGH until the 16-06 gate contract is corrected.** No files were modified during this review.

---

## Codex Review (codex-sol-high)

## 16-01

### Summary

The codex enumeration plan is implementation-ready. It follows the repository’s existing injected-subprocess pattern, filters internal models, preserves reasoning metadata through both catalog and unmatched-candidate paths, and has strong malformed-output coverage.

### Cycle-2 dispositions

- **RESOLVED — provisional failure classification.** Per-plan failures are explicitly provisional until 16-06 reproduces them at the phase base, preventing path-only claims of pre-existence. [16-01-PLAN.md:112](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-01-PLAN.md:112)
- **RESOLVED — phase artifact inventory.** The phase-wide table now includes the later Claude materialization and `image_input_source` artifacts. [16-01-PLAN.md:541](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-01-PLAN.md:541)
- **EXPLICITLY REJECTED — raw fixture hash/redaction recipe.** The rationale is reasonable: the source capture contains a large vendor prompt that should not be committed, while the retained fields, command, version, date, and transformations are documented beside the fixture constant. [16-01-PLAN.md:645](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-01-PLAN.md:645)

### Strengths

- The wrapper mirrors the existing safe argv-list pattern and adds the missing return-code gate. The current enumerators already use injected `run_fn`, `capture_output`, and a 15-second timeout. [detection.py:74](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/detection.py:74)
- Reusing `reasoning_modes` is schema-compatible: it is already an optional field with list-of-strings validation. [model_catalog.py:18](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:18) [model_catalog.py:111](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:111)
- The plan correctly updates both existing unmatched exits, which currently append records before either catalog merge path. [cli.py:270](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/cli.py:270) [cli.py:409](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/cli.py:409)
- Failure behavior preserves the existing single-provider reconciliation path because no `models` key is emitted when enumeration fails. The current discovery logic distinguishes precisely on that key. [cli.py:740](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/cli.py:740)

### Concerns

- None beyond the explicitly accepted fixture-reproducibility tradeoff.

### Suggestions

- Execute as written. Keep the fixture provenance comment adjacent to the path constant so it cannot drift away from the fixture.

### Risk Assessment

**LOW.** Parsing, invocation safety, partial degradation, hidden-model filtering, and end-to-end metadata propagation are all explicitly tested.

---

## 16-02

### Summary

The host-detection plan accurately implements the amended nesting order and closes the downstream validation gap for `native_runtime = "pi"`. Tests cover the exact tuple, individual signals, precedence removal sequence, empty values, and confidence wording.

### Cycle-2 dispositions

- **RESOLVED — provisional failure classification.** Failures outside plan files remain provisional until the causal phase gate. [16-02-PLAN.md:89](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-02-PLAN.md:89)
- **EXPLICITLY DEFERRED — duplicated native-runtime allowlists.** The rationale is sound for this phase: both definitions are updated together and permanently equality-pinned, while consolidating modules would exceed SPEC-01’s scope. [16-02-PLAN.md:414](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-02-PLAN.md:414)

### Strengths

- The proposed six-row tuple fixes the stale current order and keeps the two codex signals separate, avoiding Python’s string-`or` pitfall. The current tuple still puts Claude first and only recognizes `CODEX_VERSION`. [detection.py:25](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/detection.py:25)
- Updating both validators is necessary: they are genuinely duplicated in separate modules today. [model_catalog.py:39](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:39) [config_io.py:97](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/config_io.py:97)
- The documentation correction is source-grounded: the current docstring mentions `OPENCODE_PID`, although the detector never reads it. [detection.py:53](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/detection.py:53)
- Keeping `pi` out of `KNOWN_CLIS` preserves the Phase 22 enumeration boundary. [detection.py:13](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/detection.py:13)

### Concerns

- None.

### Suggestions

- Retain the equality assertion for the two `_VALID_NATIVE_RUNTIME` sets even if they are consolidated in a future phase.

### Risk Assessment

**LOW.** The behavioral change is costly to reverse but is explicitly user-approved, narrowly implemented, and comprehensively pinned.

---

## 16-03

### Summary

The cache-schema migration plan is sound. It separates runtime and catalog schema placement correctly, preserves old cache entries, makes version staleness an additional CLI-level condition, and explicitly avoids overstating concurrent-writer safety.

### Cycle-2 dispositions

- **RESOLVED — incorrect quota consumer claim.** The revised plan now correctly limits schema-aware stale checks to the two CLI commands rather than claiming quota shares these helpers. [16-03-PLAN.md:496](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-03-PLAN.md:496)
- **RESOLVED — provisional failure classification.** Final classification is delegated to 16-06’s mandatory base reproduction. [16-03-PLAN.md:503](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-03-PLAN.md:503)
- **RESOLVED CROSS-PLAN — Claude catalog/runtime convergence.** The remaining dependency is now handled by 16-04’s catalog-aware runtime freshness and same-fetch materialization rather than by this generic schema migration.

### Strengths

- `_meta` is the correct catalog location because current catalog consumers treat every ordinary top-level key as a model identifier. [model_catalog.py:162](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:162)
- The planned split/join boundary prevents `_meta` from reaching `merge_catalog_entry`, which currently assumes a model entry and applies field-level merge semantics. [model_catalog.py:129](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:129)
- Tests for sibling readers are well targeted. The provider scanner already ignores records without provider/runtime data, while pricing directly retrieves the requested model key. [cross_reference.py:64](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cross_reference.py:64) [pricing.py:16](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-usage-metrics/ai_kit_usage_metrics/pricing.py:16)
- The concurrency statement is now honest: atomic replacement protects interrupted single-writer operations, but the fixed temporary name does not support competing writers.

### Concerns

- None newly introduced.

### Suggestions

- Execute as written. Keep schema interpretation in the two CLI consumers rather than making the generic mtime helper format-aware.

### Risk Assessment

**MEDIUM.** Persistent-format migrations have inherently broad compatibility impact, but the plan covers old caches, reserved-key isolation, sibling consumers, failed refreshes, and atomic replacement.

---

## 16-04

### Summary

The cycle-2 blocker is substantively fixed. Newly fetched Anthropic IDs are materialized into catalog entries during the same fetch, Claude matching gets a narrowly scoped first-party provider hint, and the real detect→fetch→detect convergence sequence is exercised.

### Cycle-2 dispositions

- **RESOLVED — non-fallback Anthropic IDs were not materialized.** The recording fetch now adds extra Claude candidates and builds entries for all newly recorded IDs. [16-04-PLAN.md:285](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-04-PLAN.md:285)
- **RESOLVED — reseller collisions.** Claude alone receives the `anthropic` provider hint. This uses the matcher’s existing provider-specific disambiguation path. [model_matcher.py:123](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_matcher.py:123)
- **RESOLVED — misleading convergence erratum.** The revised wording makes the second detection sufficient only because the preceding fetch already materialized every recorded ID.
- **RESOLVED — provisional failure classification.** Final causality remains owned by 16-06. [16-04-PLAN.md:624](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-04-PLAN.md:624)

### Strengths

- The fix addresses the actual source gap: current fetch behavior only builds from snapshot candidates and then writes the result, so catalog-only IDs cannot presently become entries. [cli.py:740](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/cli.py:740) [cli.py:800](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/cli.py:800)
- Materialization is gated by the real PATH-resolved Claude binary and remains outside reported discovery/unmatched scope, avoiding unexpected wizard prompts.
- Tests include a non-fallback ID and a colliding reseller row, so they exercise both cycle-2 defects rather than only the dated fallback.
- The catalog freshness dependency is lazy and no-loop: it is consulted only after TTL/schema eligibility and only for installed Claude.

### Concerns

- **LOW — malformed Anthropic rows may now reach the matcher.** The proposed `_anthropic_model_ids` accepts every nonblank model-map key without requiring its value to be a dictionary. [16-04-PLAN.md:285](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-04-PLAN.md:285) Same-fetch materialization then feeds every such key to `match_models_dev`, whose successful path expands the matched value with `{**model, ...}` and therefore assumes a mapping. [model_matcher.py:123](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_matcher.py:123) A malformed upstream row could make `fetch-model-catalog` raise instead of degrading.

### Suggestions

- Filter `_anthropic_model_ids` to entries whose key is a nonblank string **and whose value is a dict**, and add one malformed-row test.

### Risk Assessment

**LOW.** The former HIGH convergence defect is resolved. The remaining concern is defensive hardening against malformed third-party data.

---

## 16-05

### Summary

The provenance revision correctly fixes the stale-capability problem. `image_input` and `image_input_source` travel together, models.dev statements retain priority, current opencode readings can replace older runtime-derived values during skipped fetches, and absence remains distinct from a sourced `false`.

### Cycle-2 dispositions

- **RESOLVED — missing field-level provenance.** The schema, preservation rules, runtime application, and transition tests now distinguish `models_dev` from `opencode`. [16-05-PLAN.md:188](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-05-PLAN.md:188)
- **RESOLVED — provisional failure classification.** Non-plan failures remain provisional until 16-06. [16-05-PLAN.md:550](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-05-PLAN.md:550)
- **RESOLVED — post-16-04 test hermeticity.** Every relevant fetch test injects `which_fn=lambda name: None`, preventing the real host PATH from widening candidates. [16-05-PLAN.md:129](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-05-PLAN.md:129)
- **EXPLICITLY REJECTED — raw fixture hash/redaction recipe.** The rejection is justified because the full capture exposes private provider/router configuration; detailed local provenance remains recorded beside the fixture path. [16-05-PLAN.md:558](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-05-PLAN.md:558)

### Strengths

- The proposed preservation semantics align with the existing merge contract: explicit `None` clears a field, while an omitted key preserves the cached value. [model_catalog.py:145](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:145)
- Reading runtime image capability only from `clis.opencode` ensures that `image_input_source: opencode` is truthful.
- Header equality with decoded `providerID/id` prevents a shifted block stream from attributing one model’s capability to another.
- The parser uses `JSONDecoder.raw_decode` with an index, providing linear behavior for the observed multi-thousand-line output.
- Tests cover both matched and unmatched paths, runtime True→False transitions, models.dev precedence, source silence, legacy sourceless entries, malformed blocks, and non-zero subprocess exits.

### Concerns

- None newly introduced.

### Suggestions

- Execute as written. Preserve the five provenance-transition tests as regression tests because they encode the most subtle cache behavior in this phase.

### Risk Assessment

**LOW.** The source ordering and unknown-versus-false semantics are explicit and extensively tested.

---

## 16-06

### Summary

The ranker work is well specified and the cycle-2 causal-triage defect is largely corrected. However, the revised cleanup proof contains a conditional false failure: it compares the complete worktree listing before and after a task that may create a fix commit.

### Cycle-2 dispositions

- **RESOLVED IN MECHANISM — path-based gate triage.** Every failure outside phase files must now be reproduced at `PHASE_BASE`; only an identical failure counts as pre-existing, while base-pass/HEAD-fail results are phase-caused. [16-06-PLAN.md:416](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-06-PLAN.md:416)
- **RESOLVED — inaccurate `score_candidates` docstring.** The plan now documents the actual 49.0 substitution and full-weight divisor, matching the current implementation. [model_ranker.py:109](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:109) [model_ranker.py:144](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:144)

### Strengths

- `_is_finite_number` directly closes the existing Python-bool hole: current validation accepts `True` because it uses `isinstance(value, (int, float))`. [model_ranker.py:42](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:42)
- Catching `UnicodeDecodeError` makes the documented never-raise loader contract complete; the current exception list does not catch decoding failures. [model_ranker.py:64](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:64)
- Floors are checked against raw scores before normalization, preventing excluded candidates from shifting survivor normalization.
- The phase gate matches repository policy: `make test` aggregates all four tiers, and `make validate` runs the configured hook suite. [Makefile:42](/var/home/bazzite/git/personal/ai-kit/Makefile:42) [Makefile:66](/var/home/bazzite/git/personal/ai-kit/Makefile:66) [Makefile:122](/var/home/bazzite/git/personal/ai-kit/Makefile:122)
- Detached base-worktree reproduction with the matching interpreter/tool is a materially stronger causal test than the earlier path heuristic.

### Concerns

- **MEDIUM — the before/after worktree equality check fails after a legitimate fix commit.** Step 1 records the exact `git worktree list`, and cleanup later requires exact equality. [16-06-PLAN.md:400](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-06-PLAN.md:400) But the same task may fix and commit a phase-caused failure. [16-06-PLAN.md:457](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-06-PLAN.md:457) The default worktree listing includes each worktree’s current HEAD SHA, so a new commit changes the main-worktree line even when the temporary worktree was removed perfectly. The final acceptance check can therefore report cleanup failure precisely when the causal-fix path worked.

### Suggestions

- Compare normalized worktree identity rather than complete output:
  - compare only `worktree` paths and `branch` refs from `git worktree list --porcelain`;
  - separately assert no path begins `/tmp/ai-kit-p16-base.`;
  - retain the before/after `git branch --list` comparison to prove no branch was created.
- Alternatively, explicitly permit the main worktree’s HEAD field to change when Task 3 creates a `fix(16-06):` commit.

### Risk Assessment

**MEDIUM.** Product behavior and causal failure classification are strong, but the cleanup acceptance logic can falsely fail execution when a legitimate gate fix is committed.

---

## Cross-plan assessment

The serial dependency chain is coherent:

`codex metadata plumbing → host detection → cache schemas → Claude convergence → image capability → ranker and phase gate`

All cycle-2 HIGH product defects are addressed. No new HIGH concern was found. Before execution, I recommend two final edits:

1. Fix 16-06’s worktree comparison so a legitimate fix commit does not invalidate cleanup verification.
2. Harden 16-04’s Anthropic ID extraction against non-dictionary model rows.

**Overall risk: MEDIUM**, driven by the 16-06 gate false-negative rather than by an unresolved Phase 16 feature defect. After that correction, the plan set is ready for execution.

---

## Consensus Summary

Two prompt-fed, source-grounded reviewers produced a review this cycle, and both count at full
weight (no discount markers). They agree that `9a0f0fc` resolves every cycle-2 finding: the
16-04 HIGH (non-fallback anthropic ids now get catalog entries in the same fetch), the 16-06 HIGH
(triage now needs a mandatory PHASE_BASE reproduction), the 16-05 MEDIUM (`image_input_source`
provenance), the 16-06 LOW (`score_candidates` docstring) and the 16-03 LOW (real
`cache_write_json` / `cache_is_stale` consumers). Plans 16-01 and 16-02 are LOW risk and ready as
written.

The reviewers differ on the overall verdict. Codex rates the phase **MEDIUM** and ready once two
small edits land. Opencode rates it **HIGH** until the 16-06 gate contract is fixed. Every
remaining item is in 16-06 Task 3's gate mechanics or is defensive hardening in 16-04 and 16-05.
No Phase 16 feature defect remains.

### Cycle-2 finding status (both reviewers, checked by the orchestrator)

- Cycle-2 HIGH 1 (16-04, new anthropic ids learned but not materialized as catalog entries):
  **RESOLVED** (both reviewers). The recording fetch passes `claude_candidates` to
  `build_model_catalog`. They are gated on `which_fn("claude")` and kept out of the printed
  `discovered` and `unmatched`. Claude candidates get the `anthropic` provider hint. The tracer
  uses `claude-new-not-in-fallback` plus a colliding `reseller` row
  (16-04-PLAN.md:285-320, :322-380). The orchestrator traced the fetch-skipped step 4 through
  current source. With `md_match` and `aa_match` both None, `_find_existing_key_for_runtime`
  (`cli.py:64`) finds the materialized `anthropic/<id>` entry by its claude runtime, so the id is
  preserved, not reported unmatched. The hinted tie-break is real code
  (`model_matcher.py:135-141`).
- Cycle-2 HIGH 2 (16-06, path-based triage): **RESOLVED in mechanism** (both reviewers). The
  PHASE_BASE reproduction is now mandatory for every failure outside PHASE_FILES
  (16-06-PLAN.md:416-466). Opencode raises two new, separate HIGHs about the gate's execution
  and completion semantics (below).
- Cycle-2 MEDIUM (16-05, `image_input` provenance): **RESOLVED** (both reviewers).
- Cycle-2 LOWs: the `score_candidates` docstring is **RESOLVED** (both reviewers). The 16-03
  "shared with quota.py" wording is **RESOLVED in the plan** (both reviewers). Opencode notes the
  same false claim is still in `16-RESEARCH.md` (see Other findings).
- Accepted deferrals and rejections that both reviewers found sound: fixture hash and redaction
  recipe (16-01, 16-05), duplicated `_VALID_NATIVE_RUNTIME` sets (16-02), per-writer cache temp
  files (16-03), existing opencode/cursor return-code handling (16-01).

### Agreed Strengths

- 16-01 and 16-02 are implementation-ready: argv-list subprocess seams, `reasoning_modes` reused,
  both unmatched exits covered, and an exact precedence tuple.
- 16-03 isolates `_meta` before model-entry iteration and makes schema staleness a CLI-level
  condition.
- 16-04's fix targets the real bottleneck (`cli.py:740-745`, `:800-802`). The materialization is
  scope-isolated, and the provider hint applies only to claude.
- 16-05's preserve/clear semantics match `merge_catalog_entry`'s omitted-key versus None contract
  (`model_catalog.py:143-158`).
- 16-06's `_is_finite_number` closes the bool hole, and floors are checked on raw values before
  normalization.

### Agreed Concerns

1. **MEDIUM (codex LOW, opencode MEDIUM): 16-04 `_anthropic_model_ids` does not require each
   model row to be a dict.** Materialization then sends every key to `match_models_dev`, which
   spreads the matched row (`{**model, "provider": ...}`, `model_matcher.py:122`, `:134`, `:141`).
   `fetch_models_dev` checks only the JSON transport, not the schema (`model_sources.py:30-38`).
   So a malformed upstream anthropic row (null, string or list) raises a `TypeError` in
   `fetch-model-catalog` instead of degrading. The id would also be stamped into
   `_meta.anthropic_model_ids` with no entry behind it. Fix: in `_anthropic_model_ids`, keep only
   keys whose value is a dict, and add one malformed-row test with a valid sibling.

### Divergent Views

- **16-06 Task 3 gate.** Codex found only a MEDIUM there (the worktree-list equality check). Opencode
  found two HIGHs, one MEDIUM and one LOW. The orchestrator checked opencode's two HIGH premises
  against the Makefile and the plan text and confirmed both (see Current HIGH Concerns below).
- **Overall risk.** Codex says MEDIUM, opencode says HIGH. The gap is entirely the 16-06 gate
  items.

### Current HIGH Concerns (single-reviewer, judgment-class; they count under the consensus gate)

1. **HIGH (opencode; orchestrator-confirmed): an aggregate Make target stops at its first failing
   prerequisite, so the later tiers and hooks never run.** `test: test-unit test-integration
   e2e-test arch-test` (`Makefile:66`) and `validate: ruff pylint pyright vulture shellcheck
   py-compile unittest unittest-wizard` (`Makefile:122`) are prerequisite lists. The Makefile has
   no `-k`, `MAKEFLAGS` or `.IGNORE` (checked with grep). Task 3 Step 2 says `make test` "runs the
   four tiers in order", and the acceptance criteria accept a non-zero exit once every visible
   failure is triaged (16-06-PLAN.md:408-418, :491-494). So a failure proven pre-existing, or one
   left unresolved, in an early tier hides every later tier. Example: e2e-test cannot get a
   terminal in the executor session, so `arch-test` never runs. Every hook after a failing
   `ruff` is skipped the same way. Fix: run each tier target (`test-unit`, `test-integration`,
   `e2e-test`, `arch-test`) and each `validate` hook target on its own, or run `make -k test` /
   `make -k validate`. Record every constituent's result. Require that every constituent actually
   ran before a failure can be excused.
2. **HIGH (opencode; orchestrator-confirmed as an internal contradiction): an unresolved gate
   failure is called blocking but is still accepted by the completion criteria.** Step 4 says an
   item that cannot be reproduced at PHASE_BASE is UNRESOLVED and that "the gate is not passed
   while it stands" (16-06-PLAN.md:448-451). But the must_haves truth (:36), the acceptance
   criteria (:492-493) and `<done>` (:499) all accept completion once it is "listed under
   `## Unresolved gate failures`". Nothing tells the orchestrator or verifier that such a listing
   blocks phase completion. AGENTS.md:60-63 requires saying so explicitly to uz. Fix: state in
   the objective, the must_haves truth and `<done>` that any `## Unresolved gate failures` entry
   means the Phase 16 gate has NOT passed. The plan then ends as "gate not passed, escalate to
   uz", never as complete.

### Other findings (single reviewer; the orchestrator checked each premise)

- **MEDIUM (codex): the before/after `git worktree list` equality check fails after a
  legitimate fix commit.** Step 1 records `git worktree list` exactly, and the acceptance
  criteria require the final output to equal it (16-06-PLAN.md:405-406, :495). The default
  output includes each worktree's HEAD SHA (checked: `/var/home/.../ai-kit 9a0f0fc
  [gsd/v1.3-curated-config-v2]`). A `fix(16-06):` commit changes the main worktree's line even
  when cleanup worked. Fix: compare only the `worktree` paths and `branch` refs from `--porcelain`,
  assert that no `ai-kit-p16-base.` path remains, and keep the `git branch --list` equality check.
- **MEDIUM (opencode): 16-05's validator does not require `image_input_source` to come with
  `image_input`.** The planned test accepts `image_input_source` `"models_dev"`/`"opencode"` on
  `_valid_entry` without a bool `image_input` (16-05-PLAN.md:246-251). `confirm-catalog-entry`
  persists anything `validate_catalog_entry` accepts. The "written, cleared or omitted together"
  rule (16-05-PLAN.md:203-220) is therefore enforced only by the writers, not by the schema. Fix:
  reject a non-null `image_input_source` unless `image_input` is a bool, and keep accepting a
  legacy `image_input` without a source.
- **MEDIUM → orchestrator LOW (opencode): 16-06 hardcodes `/tmp` for the base worktree**
  (`mktemp -d /tmp/ai-kit-p16-base.XXXXXX`, and the verify and acceptance greps,
  16-06-PLAN.md:423-425, :488-495). AGENTS.md:57-59 bans absolute paths in source, tests and
  project assets. This is a one-off executor shell command, so the rule applies only loosely.
  The fix is trivial either way: `${TMPDIR:-/tmp}` in the command, and match on the
  `ai-kit-p16-base.` basename in the checks.
- **LOW (opencode): 16-06 runs a global `git worktree prune`.** `git worktree remove --force
  "$BASE_WT"` already removes that worktree's admin entry. A global prune can also drop stale
  metadata for unrelated worktrees, against AGENTS.md:54-56 (preserve unrelated work). The repo
  has other worktrees under `.claude/worktrees/`. It also combines badly with the exact-equality
  check above. Fix: drop the `git worktree prune` step.
- **LOW (opencode): `16-RESEARCH.md` still says `cache_is_stale` / `cache_write_json` are
  "shared with quota.py"** (`16-RESEARCH.md:153`, `:497-498`, confirmed). 16-03 now names the real
  consumers, and 16-03's read_first sends the executor to RESEARCH.md, so the executor gets
  contradictory context. Fix: correct those RESEARCH.md lines, or add an erratum pointer in
  16-03's read_first. (16-03's Round-1 ledger text at :494 is already marked superseded by its
  Round-2 row.)

## Verification coverage

Source-grounding pass (`plan_review.source_grounding: true`; the effective authority is `grep`,
from `gsd-tools drift-guard authority`). The orchestrator ran it against the working tree at
`9a0f0fc`. The symbol inventories from cycles 1 and 2 (`6789a06`, `92c2ef4`) still apply to the
unchanged citations. This cycle re-verified every existing-code symbol that the `9a0f0fc`
revision newly cites (taken from the backticked identifiers on added lines of
`git show 9a0f0fc -- .planning/phases`). New symbols in the plans' "Artifacts this phase produces"
tables are excluded, for example `_anthropic_model_ids`, `_FIRST_PARTY_PROVIDER_BY_CLI`,
`claude_candidates`, `_VALID_IMAGE_INPUT_SOURCE`, `image_input_source`,
`TestClaudeCatalogMaterialization` and the new test names.

### VERIFIED (existing symbols the revision cites)

- `model_matcher.match_models_dev` :96 (signature `provider_hint=None, allow_fuzzy=True`). The
  bare-id exact pool is at :123-126, a single match wins at :132-134, and the hint tie-break is at
  :135-141, returning None when a collision stays ambiguous. This supports 16-04's claim that
  "an unhinted multi-provider bare id returns no match".
- `cli.py`: `_find_existing_key_for_runtime` :64; `_preserved_or_fresh_md_fields` :108;
  `build_model_catalog` :208; the ordinary-path `md_match = match_models_dev(model_id,
  models_dev_data) if models_dev_ok else None` line (inside `build_model_catalog`, :315);
  `md_enrich_match` :330-345; `fetch-model-catalog` `discovered` built from runtimes :740-745;
  `fetch_meta_path` / `skip_fetch` :781-782; `build_model_catalog` call :800-801; `main(argv,
  which_fn=shutil.which, ...)` :482 (so `which_fn` is available to `fetch-model-catalog`).
- `model_catalog.py`: `_MANDATORY_CATALOG_FIELDS` :12, `_FIELD_TYPES` :18,
  `_VALID_NAME_DECLARED_PURPOSE` :38, `_VALID_NATIVE_RUNTIME` :39, `cache_catalog_path` :42,
  `validate_catalog_entry` :53, `merge_catalog_entry` :129 (omitted key preserved, explicit None
  cleared, :143-158), `current_candidate_keys` :162.
- `model_ranker.py`: `_MISSING_AXIS_DEFAULT = 49.0` :35, `score_candidates` :109.
- 16-03's corrected consumer list, checked by grep over `skills/`. `cache_is_stale` is called only
  at `cli.py:717` and `:782`. `cache_write_json` is used at `cli.py:723`, `:798`, `:802`, `:828`,
  `:850`, `:859`, `dispatch.py:201` (`write_resumable_state`), `ai_kit_spec_gsd/gsd_config.py`
  (:66, :85, :116, :156, :177), `ai_kit_spec_gsd/cli.py:142` and
  `ai_kit_spec_superpowers/cli.py:226`. All VERIFIED.
- 16-06 Task 3's references: Makefile `test-unit` :45 (its second command is `uv run python3 -m
  unittest tests.test_framework_profiles`, :47), `test-integration` :51, `e2e-test` :56,
  `arch-test` :61 (bare `python3`), `test` :66, `validate` :122 plus the eight single-tool
  targets it lists; `.pre-commit-config.yaml` hook ids ruff, pylint, pyright (with
  `pass_filenames: false`), vulture, shellcheck, py-compile, unittest and unittest-wizard;
  `pyproject.toml` `package = false` :13; `.venv/bin/python` and `.venv/bin/ruff` exist in the
  main checkout.

### MISSING / AMBIGUOUS

- None found among the existing symbols the revision cites.
- Stale grounding text (LOW, needs acknowledgement): `16-RESEARCH.md:153` and `:497-498` still
  state the corrected-away "shared with quota.py" claim (see Other findings).

### UNCHECKABLE (INFO: the `grep` authority cannot assert these)

- Signatures and keyword defaults of new or extended functions (`build_runtimes_snapshot(...,
  catalog_fn=None)`, `claude_runtime_is_current(runtimes_data, catalog_fn=None)`,
  `_apply_runtime_meta(..., runtime_wins_image_input=False)`). The plans' own verify commands
  cover them.
- Live models.dev shape claims from the `9a0f0fc` revision ("on 2026-09-24 every anthropic id
  also appears under 9-21 reseller providers"). They were not re-fetched this cycle. The
  hint-based design is correct whether or not such collisions exist.
- Whether `make test`'s `test-integration` / `e2e-test` tiers can get a terminal in the cross-AI
  executor's session. This is the concrete trigger for Current HIGH 1.
- External facts carried from cycle 1 (codex-cli 0.147.0 `debug models` shape, opencode 1.18.32
  `--verbose` shape, `PI_CODING_AGENT` / `CODEX_THREAD_ID`): verified against real captures in
  cycle 1 and not re-captured.

### Cross-artifact fact-drift pass

- Phase status (`gsd-tools drift-guard phase-status --phase 16`): **uncheckable**
  (`reason: phase_not_in_roadmap`; STATE.md says "Ready to execute"). The seam cannot parse
  ROADMAP.md's `- [ ] **Phase 16: ...**` entry. The axis was skipped, not found consistent.
- ROADMAP Success Criteria ↔ `must_haves.truths`: no contradiction. The `9a0f0fc` ROADMAP plan-list
  edits (16-04 "every recorded id materialized as an `anthropic/<id>` catalog entry in the same
  fetch", 16-05 "`image_input_source` provenance", 16-06 "causal triage against the pre-phase
  base") match the revised plans. SC2's "claude (hardcoded aliases + catalog full ids + dated
  fallback)" matches 16-04's truths.
- ROADMAP `**Requirements:**` (SPEC-01..04) ↔ plan requirement refs: consistent, unchanged since
  cycle 1.
- CONTEXT.md Decisions ↔ plan usage: no contradiction. 16-04's same-fetch materialization and
  claude-only `anthropic` hint add to D-04 (hybrid sourcing) and do not contradict it. 16-05's
  `image_input_source` adds provenance under D-09's source order and does not contradict it.
- RESEARCH.md ↔ 16-03 (not a judgment pair in the table; recorded for completeness): the
  "shared with quota.py" claim contradicts 16-03's corrected truth. It is counted once, as the
  opencode LOW above.
- Advisory only: this pass contributes nothing to `current_high` / `current_actionable`.

## Cycle accounting (orchestrator)

- Consensus gate: **engaged**, because two reviewers (opencode-plan-review, codex-sol-high)
  produced review sections and neither carries a discount marker. No HIGH was raised by both.
  Opencode's two 16-06 HIGHs are **judgment-class** (gate execution and completion semantics),
  so they count without corroboration. The orchestrator also confirmed both premises against
  source and plan text. No existence-class HIGH was raised.
- `current_high = 2`: (1) 16-06 aggregate `make test` / `make validate` stop at the first failing
  prerequisite, so later tiers and hooks can go unrun while the visible failure is excused;
  (2) 16-06 completion criteria accept `## Unresolved gate failures` although Step 4 says the
  gate has not passed. All cycle-1 and cycle-2 HIGHs are fully resolved.
- `current_actionable = 6`: (1) 16-04 non-dict anthropic rows (agreed, MEDIUM); (2) 16-06
  worktree-list equality broken by a fix commit (MEDIUM); (3) 16-05 orphan `image_input_source`
  accepted by the validator (MEDIUM); (4) 16-06 hardcoded `/tmp` (LOW); (5) 16-06 global
  `git worktree prune` (LOW); (6) stale "shared with quota.py" claim in 16-RESEARCH.md read by
  the 16-03 executor (LOW). Not counted: the accepted deferrals and rejections listed above, and
  the advisory fact-drift items.
