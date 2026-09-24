---
phase: 16
reviewers: [opencode-plan-review, codex-sol-high]
reviewed_at: 2026-09-24T09:21:10Z
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

> Lane notes (environment, not plan findings). Reviewers came from `review.default_reviewers`:
> `opencode-plan-review` (opencode, `router-env/my-plan-review`) and `codex-sol-high` (codex,
> `gpt-5.6-sol`). No other lanes were substituted. First attempts: opencode exited 1 with no
> assistant text because router-env credentials for its backing model were rate-limited ("All
> credentials for model glm-5.2 are cooling down" / "Model opencode-zen/glm-5.2 is locked"), and
> codex hit its ChatGPT usage limit mid-review. A foreground probe loop confirmed both were
> transient quota states, not broken CLIs. codex was re-run once after its quota reset (02:58).
> opencode was retried once with a path-referencing prompt (17.8 KB: roadmap, requirements,
> CONTEXT.md and instructions inlined; PROJECT.md, RESEARCH.md and the six plans read from disk by
> the agent) in place of the 263 KB inlined prompt codex received. Both final reviews cover all six
> plan ids and cite `file:line` evidence, so neither carries an evidence-quality discount marker.
> The working tree was unchanged after both read-only runs.

## OpenCode Review (opencode-plan-review)


**Document type:** GSD · plan  
**Status:** Issues Found — revise and re-review

## 16-01

### Summary

The codex tracer is thorough and follows the existing injected-subprocess and catalog-merge architecture. Parser degradation, hidden-model filtering, reasoning metadata propagation, and payload minimization are well covered. Two process gaps remain: the “captured fixture” is reconstructed rather than directly sanitized from raw output, and the required `skill-judge` gate is outside the executor-visible blocks.

### Strengths

- The parser design correctly mirrors the established argv-list, timeout, and graceful-degradation pattern in `detect_opencode_models` and `detect_cursor_agent_models` (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:74-106`; `.planning/phases/16-ai-kit-spec-extensions/16-01-PLAN.md:164-196`).
- Runtime metadata is applied immediately before both catalog merges, which is necessary because the router and matched-model paths converge independently at `merge_catalog_entry` (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:252-314`, `skills/ai-kit-spec-review/ai_kit_spec/cli.py:415-479`; `16-01-PLAN.md:213-230`).
- The failure path deliberately omits `models`, preserving the existing single-provider reconciliation mechanism that selects installed CLIs without a model array (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:740-763`; `16-01-PLAN.md:188-196`).
- Tests explicitly ensure that the large external instruction payload never enters either cache (`16-01-PLAN.md:258-261`), matching the minimal-data parser design.

### Concerns

- **MEDIUM — Fixture provenance is weaker than the success criterion states.** The task generates a hand-constructed JSON document from values transcribed into the plan, including a replacement `instructions_template`, rather than sanitizing an actual captured output file (`16-01-PLAN.md:137-162`). That is a representative fixture derived from a capture, but not literally a fixture captured from real CLI output as required by SPEC-02.
- **MEDIUM — Required skill review is invisible to the executor.** Task 2 materially changes `skills/ai-kit-spec-config/SKILL.md` (`16-01-PLAN.md:326-361`), but `/skill-judge` appears only after `<tasks>` in the plan verification section (`16-01-PLAN.md:410-415`). The executor receives only `<objective>` and `<tasks>`, while repository policy requires every materially updated `SKILL.md` to pass that review (`AGENTS.md:45-47`).

### Suggestions

- Produce the fixture by sanitizing a preserved raw capture, retaining only the real fields needed by the parser. Record CLI version and capture date in an adjacent test constant or fixture manifest.
- Add the `skill-judge` invocation and pass criteria to Task 2 before its commit/done step.

### Risk Assessment

**MEDIUM.** The implementation path is sound, but fixture provenance and a missing executor-visible quality gate prevent unqualified approval.

## 16-02

### Summary

This plan closes the most important detection blast-radius issue: it updates both duplicated `native_runtime` validators alongside the precedence tuple. Its matrix tests are unusually complete and correctly distinguish host detection from installed-CLI enumeration. The only material gap is again the executor-invisible `skill-judge` requirement.

### Strengths

- The exact six-row tuple is compatible with the existing first-truthy-signal loop (`skills/ai-kit-spec-review/ai_kit_spec/detection.py:27-32`, `skills/ai-kit-spec-review/ai_kit_spec/detection.py:67-71`; `16-02-PLAN.md:133-143`).
- Two separate codex rows correctly implement `CODEX_THREAD_ID OR CODEX_VERSION`; no control-flow rewrite is required (`16-02-PLAN.md:133-138`).
- Adding `pi` to both duplicated validators closes a real downstream failure path. Both currently omit it (`skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:39`, `skills/ai-kit-spec-review/ai_kit_spec/config_io.py:96-129`; `16-02-PLAN.md:170-175`).
- The plan preserves the architectural distinction between `_RUNTIME_ENV_SIGNALS` and `KNOWN_CLIS`, consistent with the repository contract (`AGENTS.md:67-71`; `16-02-PLAN.md:139-143`, `16-02-PLAN.md:230-237`).
- The precedence, empty-value, environment fallback, and confidence-label tests cover both behavior and diagnostic honesty (`16-02-PLAN.md:229-254`).

### Concerns

- **MEDIUM — The `SKILL.md` gate is outside the executor-visible content.** Task 2 updates runtime values and nesting semantics in `skills/ai-kit-spec-config/SKILL.md` (`16-02-PLAN.md:256-272`), but `/skill-judge` is mentioned only in the trailing verification section (`16-02-PLAN.md:317-323`). This conflicts with `AGENTS.md:45-47` under the stated cross-AI execution model.

### Suggestions

- Move the `skill-judge` review loop into Task 2, with an explicit passing threshold before commit.
- Keep the exact tuple assertion; it provides a useful regression alarm for a deliberately costly precedence decision.

### Risk Assessment

**LOW–MEDIUM.** Functionally strong and well tested; the remaining issue is a required completion gate rather than detection correctness.

## 16-03

### Summary

The schema-version design is well integrated with the existing fetch-meta mechanism, and reserving `_meta` avoids breaking provider/model identity. However, the plan makes an incorrect concurrency claim about the current cache writer and overstates the “exactly once” refresh guarantee. The concurrency claim should either be removed or the writer must be hardened.

### Strengths

- Keeping schema awareness in command bodies rather than `cache_is_stale` preserves that helper’s generic contract and its quota-cache use (`skills/ai-kit-spec-review/ai_kit_spec/cache.py:32-36`; `16-03-PLAN.md:135-143`).
- The planned freshness expression correctly uses “TTL current AND schema current” for skipping, equivalent to refreshing on stale TTL OR stale schema (`16-03-PLAN.md:135-142`).
- `_meta` is a reasonable representation because current catalog algorithms assume every top-level model value is a mapping. For example, `_find_existing_key_for_runtime` and `current_candidate_keys` call mapping methods on each value (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:79-82`, `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:162-172`; `16-03-PLAN.md:74-82`).
- Splitting metadata before catalog operations and rejoining it for all three write paths addresses fetch, confirmation, and heuristic correction consistently (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:769-802`, `skills/ai-kit-spec-review/ai_kit_spec/cli.py:810-850`; `16-03-PLAN.md:237-251`).
- Existing sibling consumers degrade safely: provider cross-reference skips entries without `provider`/`runtimes`, while price lookup addresses a canonical key directly (`skills/ai-kit-opencode-providers/ai_kit_opencode_providers/cross_reference.py:64-94`, `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/pricing.py:24-42`).

### Concerns

- **HIGH — The concurrency statement is false for the existing writer.** The plan claims concurrent writers are last-writer-wins and each write remains atomic (`16-03-PLAN.md:33`, `16-03-PLAN.md:330-336`). In reality, `cache_write_json` uses one fixed `<path>.tmp` name (`skills/ai-kit-spec-review/ai_kit_spec/cache.py:21-29`). Concurrent opens can share/truncate the same temporary inode; one `os.replace` can remove the path before the other replaces it, causing interleaved content or `FileNotFoundError`. This is not reliable last-writer-wins behavior.
- **MEDIUM — “Exactly one automatic refresh” is overstated.** The success criterion promises exactly one refresh (`16-03-PLAN.md:347-351`), while Task 2 intentionally leaves the version unstamped after models.dev failure so every subsequent `--if-stale` call retries (`16-03-PLAN.md:243-247`). The retry behavior is sensible, but it is not exactly one attempt.
- **LOW — The reserved metadata contract expands the file format beyond this package.** The plan tests the main package’s iterators, but does not add explicit regression tests for the two sibling readers, despite documenting them as consumers. Their current implementations are safe, but this should be pinned because `_meta` becomes persistent shared state.

### Suggestions

- Either remove the E5 “concurrent writers are last-writer-wins” truth and describe concurrency as unsupported, or change `cache_write_json` to use a unique `tempfile.mkstemp` file in the destination directory with cleanup.
- Reword “exactly one refresh” to “one successful refresh; failed refreshes remain stale and retry.”
- Add focused sibling tests proving provider scanning ignores `_meta` and usage-metrics price lookup remains unchanged.

### Risk Assessment

**HIGH.** The schema design itself is good, but the plan currently elevates an incorrect cache-concurrency assumption into an acceptance truth.

## 16-04

### Summary

The Claude hybrid model shape is carefully designed: aliases remain separate from full IDs, fallback provenance is explicit, and Claude is never executed. The main integration flow has a high-severity freshness-ordering defect: the standard refresh sequence can persist fallback IDs for 30 days even after the catalog obtains live anthropic IDs.

### Strengths

- Keeping aliases outside `models` prevents the existing discovery comprehension from attempting to match bare aliases as catalog candidates (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:740-745`; `16-04-PLAN.md:83-89`).
- The lazy `catalog_fn` preserves testability and ensures no catalog read occurs unless Claude is installed (`16-04-PLAN.md:151-167`).
- The plan never invokes Claude and tests that `run_fn` remains untouched, avoiding the user’s wrapped alias entirely (`16-04-PLAN.md:190-206`, `16-04-PLAN.md:236-260`).
- Catalog provenance and fallback provenance remain visibly distinct through `models_source` and `models_as_of` (`16-04-PLAN.md:151-159`), satisfying the confidence-labeling rule in `PROJECT.md:45-51`.
- Missing anthropic data does not erase previously recorded IDs (`16-04-PLAN.md:177-181`, `16-04-PLAN.md:244-260`), which correctly treats source silence as non-authoritative.

### Concerns

- **HIGH — The normal refresh order can strand Claude on fallback IDs.** The approved architecture calls `detect-runtimes --if-stale` before `fetch-model-catalog --if-stale` (`docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md:97-99`). Current `detect-runtimes` returns immediately for a fresh runtime cache (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:716-724`). On the first upgraded run, detection can write the dated fallback before catalog refresh records `anthropic_model_ids`; the subsequent catalog refresh cannot update that fresh runtimes file. Later runs skip detection for up to 30 days. The tracer avoids this by fetching the catalog first and then running unconditional detection (`16-04-PLAN.md:183-206`), so it does not test the real prescribed order.
- **MEDIUM — Catalog freshness and runtime freshness are treated as independent despite the new dependency.** Once `clis.claude.models` derives from model-catalog metadata (`16-04-PLAN.md:151-180`), runtimes freshness must account for whether the catalog’s anthropic metadata is newer or has changed.

### Suggestions

- Add an end-to-end test using the actual architecture order: unversioned/empty caches → `detect-runtimes --if-stale` → `fetch-model-catalog --if-stale` → next refresh. Assert that Claude reaches catalog IDs without waiting for runtime TTL.
- Resolve the dependency by either:
  - refreshing the catalog before runtime detection;
  - re-running runtime detection after a successful anthropic metadata update; or
  - storing enough catalog metadata/version information in `runtimes.json` to invalidate the Claude portion when catalog IDs change.

### Risk Assessment

**HIGH.** Unit behavior is strong, but the standard refresh sequence may fail the phase goal in actual use.

## 16-05

### Summary

The source-priority and stale-field behavior are well considered, especially the distinction between explicit `false` and unknown. The major remaining parser risk is that the verbose parser trusts a header independently of the decoded object, allowing a shifted or malformed stream to assign a capability to the wrong model.

### Strengths

- Adding `image_input` only to `_FIELD_TYPES` preserves old entries because optional fields are ignored when absent (`skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:12-23`, `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:77-92`; `16-05-PLAN.md:134-138`).
- The plan uses the existing clear-on-`None` merge contract correctly: a fresh source with no statement clears stale data, while source failure omits the key and preserves cached data (`skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:141-158`, `skills/ai-kit-spec-review/ai_kit_spec/cli.py:108-144`; `16-05-PLAN.md:140-151`).
- Models.dev precedence over runtime metadata is implemented at the merge point rather than by duplicating source-selection logic (`16-05-PLAN.md:257-266`).
- The router path explicitly lets current runtime metadata replace stale cached capability data, which is necessary because that path intentionally skips external matching (`skills/ai-kit-spec-review/ai_kit_spec/cli.py:252-314`; `16-05-PLAN.md:260-266`).
- Explicit `false` is recorded only when a real source states it; no-source cases remain absent (`16-05-PLAN.md:79-89`, `16-05-PLAN.md:153-177`).

### Concerns

- **MEDIUM — The verbose parser can misattribute capability data.** It decodes each JSON object but records `result[header] = image` without validating that the header matches the object’s `providerID` and `id` (`16-05-PLAN.md:240-249`). Because Phase 17 uses this field as an eligibility gate, a shifted header or format change could assign another model’s image capability while still producing syntactically valid JSON.
- **LOW — Fixture construction is again transcription-based.** The fixture is generated from objects embedded in the plan rather than produced by a sanitizer over the recorded raw output (`16-05-PLAN.md:221-238`). This weakens the evidence that the block parser matches the actual CLI format.

### Suggestions

- Require `header == f"{providerID}/{id}"` when both object fields are valid strings; skip or stop on mismatch. Add tests for swapped headers and object IDs.
- Preserve a sanitized capture artifact or a reproducible sanitization procedure rather than manually recreating blocks.

### Risk Assessment

**MEDIUM.** Source precedence and cache semantics are strong, but parser misattribution could produce incorrect downstream model eligibility.

## 16-06

### Summary

The ranker plan provides good backward compatibility at the scoring API and cleanly separates canonical purpose names from aliases. Floor filtering is correctly placed before normalization. Two gaps remain: boolean TOML values can still pass numeric validation, and the final repository gates are outside the executor-visible tasks.

### Strengths

- Alias normalization preserves old `[execute]` files while canonicalizing newly loaded weights to `execution` (`16-06-PLAN.md:143-165`, `16-06-PLAN.md:195-203`).
- `score_candidates(entries, "execute", …)` remains compatible with both canonical loaded weights and hand-built legacy dictionaries (`16-06-PLAN.md:160-165`, `16-06-PLAN.md:193-200`).
- Missing new sections are filled from independent deep copies rather than rejecting an otherwise valid old file (`16-06-PLAN.md:157-160`).
- Floor filtering is explicitly performed before every normalization calculation, preventing excluded candidates from distorting survivor scores (`16-06-PLAN.md:250-266`).
- `_passes_floor` correctly bypasses `_MISSING_AXIS_DEFAULT`; missing, non-numeric, boolean, and non-finite raw values are excluded (`16-06-PLAN.md:250-263`).
- The invalid-UTF-8 hardening closes a real gap in the current loader, whose exception tuple only covers `OSError` and TOML decoding (`skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:64-79`; `16-06-PLAN.md:263-266`).

### Concerns

- **MEDIUM — Purpose weights and bonuses still accept booleans as numbers.** The current validator uses `isinstance(v, (int, float))`, which accepts `True` and `False` (`skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:42-61`). The plan preserves that check for normal axes and bonuses while explicitly rejecting booleans only in floor tables (`16-06-PLAN.md:151-155`, `16-06-PLAN.md:250-256`). Valid TOML such as `price = true` would therefore silently become numeric weight `1`.
- **HIGH — Final required gates are outside `<objective>`/`<tasks>`.** Task 2 runs focused and six-module unittest commands only (`16-06-PLAN.md:292-306`). `make test-unit` and `make validate` appear after `<tasks>` (`16-06-PLAN.md:340-345`), so the cross-AI executor will not see them. Moreover, repository policy requires the full `make test` pyramid before completion (`AGENTS.md:123-130`), and that command is absent from all six plans.
- **LOW — Alias normalization wording is slightly ambiguous for `review`.** `PURPOSE_ALIASES` includes `review: review`, while `_normalize_purpose_aliases` is described as copying “non-alias” keys and separately processing only aliases whose canonical name differs (`16-06-PLAN.md:143-150`). The intended result is clear from tests, but the implementation instruction should explicitly say self-aliases remain ordinary canonical sections.

### Suggestions

- Reject booleans for every numeric weight and bonus, not only floors; add malformed-axis and malformed-bonus tests.
- Add `make test`, `make lint`, and `make validate` to the final task before commit/completion so the actual executor runs them.
- Clarify that alias normalization processes only mappings where `alias != canonical`; `review` remains copied as a canonical section.

### Risk Assessment

**MEDIUM–HIGH.** Ranking mechanics are solid, but malformed boolean weights and missing executor-visible phase gates must be corrected.

## Cross-Plan Assessment

### Summary

Requirement coverage and traceability are unusually strong: all four SPEC requirements have concrete owners, fixtures, degradation tests, and end-to-end tracers. The serial dependency chain is conservative but reasonable because the plans repeatedly modify `detection.py`, `cli.py`, `model_catalog.py`, and one shared test module. Approval is blocked primarily by the Claude cache-refresh ordering defect, the incorrect concurrency claim, and missing executor-visible final quality gates.

### Cross-Plan Concerns

- **HIGH — Claude catalog enrichment is not guaranteed in the prescribed runtime-refresh flow.** Plans 16-03 and 16-04 need a shared invalidation or second-pass mechanism; otherwise current runtime schema versioning can make the fallback snapshot look fresh immediately before the catalog gains authoritative IDs.
- **HIGH — No executor-visible task runs the repository’s required full verification.** The final plan must own `make test`, `make lint`, and `make validate`; placing commands after `<tasks>` does not satisfy the stated execution model.
- **HIGH — Cache concurrency is represented as safe when the fixed temporary filename does not provide that guarantee.**
- **MEDIUM — Both external-output fixtures are manually reconstructed.** This is adequate for parser unit behavior but weaker than the milestone’s claim that fixtures were captured from real CLI output.
- **MEDIUM — Required `skill-judge` reviews for modified skills are deferred outside the executor-visible task blocks.**

### Overall Risk Assessment

**HIGH until revised.** The plans are technically detailed and mostly aligned with the live code, but the normal Claude refresh flow can miss authoritative catalog data for an entire TTL, and the completion workflow omits mandatory visible gates. After those issues and the cache-concurrency claim are corrected, the remaining implementation risk should fall to **MEDIUM–LOW**.

---

## Codex Review (codex-sol-high)


## 16-01

### Summary

The Codex enumeration tracer is well designed and follows existing dependency-injection and graceful-degradation patterns. It should achieve the normal happy path, but it misses non-zero subprocess exits and drops runtime metadata when a candidate takes the unmatched/manual-confirmation path.

### Strengths

- The proposed detector fits the established `run_fn`/argv/timeout seam used by existing model enumeration at [detection.py:74](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/detection.py:74), and snapshot wiring has a clear extension point at [detection.py:134](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/detection.py:134).
- Reusing `reasoning_modes` is correct: it is already an optional catalog field and has list-of-strings validation at [model_catalog.py:22](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:22) and [model_catalog.py:111](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:111).
- The fixture, visibility filtering, payload-minimization assertion, and end-to-end runtimes-to-catalog test cover the principal functional and information-disclosure risks.

### Concerns

- **MEDIUM — non-zero exit status is treated as success.** The planned call uses `check=False` and immediately parses `stdout` without checking `returncode` ([16-01-PLAN.md:178](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-01-PLAN.md:178)). A failing command that emits valid or stale JSON would populate models. The repository already demonstrates the safer contract by checking `returncode` before parsing at [model_detect.py:64](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/model_detect.py:64).
- **MEDIUM — runtime metadata bypasses unmatched candidates.** The plan applies metadata only immediately before two `merge_catalog_entry` calls ([16-01-PLAN.md:223](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-01-PLAN.md:223)). A new Codex model missing from external catalogs exits through the unmatched branch at [cli.py:409](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/cli.py:409), so its supported effort modes will not reach the later manual-confirmation payload.
- **HIGH — the mandatory `skill-judge` gate is invisible to the executor.** `SKILL.md` is materially changed, but the plan places `/skill-judge` only in the outer verification section at [16-01-PLAN.md:414](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-01-PLAN.md:414), outside the `<objective>/<tasks>` blocks the executor receives. This contradicts the non-negotiable rule at [AGENTS.md:45](/var/home/bazzite/git/personal/ai-kit/AGENTS.md:45).

### Suggestions

- Require `getattr(result, "returncode", 1) == 0` before parsing and add a non-zero-with-valid-JSON regression test.
- Attach applicable runtime metadata to unmatched records so `confirm-catalog-entry` can preserve it.
- Put the complete `skill-judge` review loop in Task 2’s action, verification, and acceptance criteria.

### Risk Assessment

**MEDIUM**, rising to **HIGH process risk** until the mandatory skill review is executable from the task itself.

## 16-02

### Summary

This plan cleanly resolves the host-precedence and duplicated-validator gaps. Its matrix testing is unusually thorough, but one confidence-label bullet overstates the actual signal set, and the mandatory skill review is again outside the executor-visible task.

### Strengths

- `_RUNTIME_ENV_SIGNALS` is exactly the right seam: the behavior is a simple ordered loop at [detection.py:67](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/detection.py:67), so two adjacent Codex rows correctly implement the OR without new control flow.
- Adding `pi` to both validators closes a real integration gap. The duplicated sets are currently visible at [model_catalog.py:39](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:39) and [config_io.py:97](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/config_io.py:97).
- The end-to-end render test exercises the functionally reachable `config_io` path, not just the forward-compatible catalog validator.
- The explicit guard that `KNOWN_CLIS` remains unchanged respects the documented distinction at [AGENTS.md:67](/var/home/bazzite/git/personal/ai-kit/AGENTS.md:67).

### Concerns

- **MEDIUM — the docstring claims `OPENCODE_PID` is a detection signal, but it is not.** The required exact tuple contains only `OPENCODE` ([16-02-PLAN.md:230](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-02-PLAN.md:230)), while the prescribed docstring says `OPENCODE/OPENCODE_PID` ([16-02-PLAN.md:155](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-02-PLAN.md:155)). The live baseline has the same misleading wording at [detection.py:58](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/detection.py:58). That conflicts with the project’s certainty-labeling rule.
- **HIGH — `skill-judge` remains out of task scope.** It appears only at [16-02-PLAN.md:321](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-02-PLAN.md:321), while Task 2 marks the plan done after editing `SKILL.md`. The executor will not receive this instruction.

### Suggestions

- Describe only `OPENCODE` as the detector signal. If `OPENCODE_PID` is evidence observed in the spawned process but not consumed, say that explicitly.
- Add `skill-judge` to Task 2 and require no Critical/Important findings or the documented score threshold before completion.

### Risk Assessment

**MEDIUM**. Runtime behavior is strong; documentation certainty and the missing executable quality gate need correction.

## 16-03

### Summary

The cache-versioning design is structurally sound: schema awareness remains in callers, legacy catalogs stay loadable, and `_meta` is isolated from model entries. The main flaw is an incorrect concurrency claim about the existing atomic writer.

### Strengths

- Keeping `cache_is_stale` schema-agnostic is correct because it is a generic mtime helper at [cache.py:32](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/cache.py:32).
- The planned OR semantics correctly extend the existing early-return gate at [cli.py:716](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/cli.py:716).
- Splitting catalog metadata before processing is necessary because current routines iterate catalog values as model entries, including `_find_existing_key_for_runtime` at [cli.py:79](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/cli.py:79) and `current_candidate_keys` at [model_catalog.py:169](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:169).
- The plan correctly covers all three catalog-writing CLI paths currently present: fetch, confirm, and correction at [cli.py:802](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/cli.py:802), [cli.py:828](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/cli.py:828), and [cli.py:850](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/cli.py:850).

### Concerns

- **MEDIUM — “concurrent writers are last-writer-wins” is false.** The plan asserts this at [16-03-PLAN.md:33](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-03-PLAN.md:33) and repeats it while acknowledging the shared fixed temporary name at [16-03-PLAN.md:335](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-03-PLAN.md:335). The writer uses one shared `path + ".tmp"` at [cache.py:26](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/cache.py:26); concurrent writers can replace or remove each other’s temporary file, causing a failed `os.replace`, not deterministic last-writer-wins behavior.
- **LOW — the concurrency edge is claimed but never tested.** The proposed E5 tests cover malformed files, not simultaneous writers. If concurrency remains accepted out of scope, it should not be stated as a verified truth.

### Suggestions

- Change the plan’s concurrency disposition to “single-writer atomicity; concurrent behavior unsupported.”
- Alternatively, explicitly expand scope to a unique `tempfile.mkstemp()` per writer and add a concurrency test—but that is a separate cache hardening change and should be planned deliberately.

### Risk Assessment

**MEDIUM**. Schema migration behavior is strong, but the concurrency guarantee must be corrected or implemented.

## 16-04

### Summary

The hybrid Claude source model and confidence labeling are sensible, but the plan has a high-risk cache dependency cycle: catalog refresh records authoritative Claude IDs only after runtimes detection, while `detect-runtimes --if-stale` can then retain the fallback snapshot for the entire TTL.

### Strengths

- Keeping aliases separate from full IDs prevents false `anthropic/opus`-style catalog candidates.
- The lazy `catalog_fn` preserves hermeticity and avoids reading the catalog unless Claude is installed ([16-04-PLAN.md:161](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-04-PLAN.md:161)).
- The explicit `models_source` and `models_as_of` fields satisfy the project’s confidence-labeling contract.
- Never invoking Claude is a strong mitigation given that enumeration has no supported list command.

### Concerns

- **HIGH — the tracer uses the opposite order from the real `--if-stale` flow.** The test fetches the catalog first and detects runtimes second ([16-04-PLAN.md:190](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-04-PLAN.md:190)). The approved adapter flow is `detect-runtimes --if-stale` followed by `fetch-model-catalog --if-stale` at [design spec:97](/var/home/bazzite/git/personal/ai-kit/docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md:97). Plan 16-03 makes a fresh, current-version runtimes cache skippable, and the current early return is at [cli.py:716](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/cli.py:716). Therefore:
  1. detection writes `dated-fallback`;
  2. catalog refresh records authoritative Anthropic IDs;
  3. later `detect-runtimes --if-stale` sees a fresh/current runtimes file and skips;
  4. `models_source` can remain `dated-fallback` for 30 days.
- **MEDIUM — the test does not prove the cache handoff Phase 17 will actually use.** It proves `fetch → forced detect --save → fetch`, not `detect --if-stale → fetch --if-stale → detect --if-stale`.

### Suggestions

- Add catalog dependency invalidation to runtimes freshness, or rewrite/stamp the Claude portion of runtimes after a successful models.dev refresh.
- Add an end-to-end test in the real command order. The final assertion must show the second `detect-runtimes --if-stale` produces or persists `models_source: catalog`.
- If a second detect is the intended Phase 17 responsibility, make that explicit in the design and plan rather than leaving an implicit cross-phase requirement.

### Risk Assessment

**HIGH**. Without fixing the handoff, the phase can pass all proposed tests while failing the intended catalog-backed Claude enumeration in production.

## 16-05

### Summary

The source-priority semantics are carefully designed and fit the existing clear-on-`None` merge contract. Coverage is strong for matched and name-declared router candidates, but runtime capability data is lost for ordinary unmatched candidates, and subprocess return codes are again ignored.

### Strengths

- The models.dev integration correctly extends the existing provenance-aware helper at [cli.py:108](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/cli.py:108), including preserving cached values during outages and explicitly clearing stale values after a successful non-statement.
- Optional schema placement is correct because `_FIELD_TYPES` governs optional validation while mandatory fields are separate at [model_catalog.py:11](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:11).
- Applying runtime data only when models.dev has no Boolean statement implements the locked source order.
- The proposed block parser keeps partial results after malformed later blocks, which is appropriate for independently versioned CLI output.

### Concerns

- **MEDIUM — unmatched opencode candidates lose `image_input`.** The plan applies runtime metadata only at the router/name-purpose merge and the matched merge ([16-05-PLAN.md:257](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-05-PLAN.md:257)). A router such as `router-env/custom` is recognized as a router by [model_heuristics.py:9](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_heuristics.py:9), but has no declared review/execute purpose because the purpose hints are limited at [model_heuristics.py:33](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_heuristics.py:33). With no external match, it exits through the unmatched branch at [cli.py:409](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/cli.py:409), so the later manual confirmation cannot preserve the known runtime capability.
- **MEDIUM — non-zero `opencode models --verbose` exits can still be parsed as success.** The planned detector uses `check=False` and parses `stdout` without checking `returncode` ([16-05-PLAN.md:249](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-05-PLAN.md:249)).
- **LOW — two sequential opencode commands are added to every fresh snapshot.** The current opencode branch performs one subprocess at [detection.py:145](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/detection.py:145); the plan adds another potentially large-output command. This is acceptable, but should have a timing/size regression expectation because the real output is described as ~8.5k lines.

### Suggestions

- Include applicable runtime metadata in unmatched records and specify how the wizard copies it into the confirmation entry.
- Reject non-zero subprocess results and test a non-zero result containing otherwise valid fixture output.
- Add a parser-size smoke test or a generous performance assertion using repeated fixture blocks.

### Risk Assessment

**MEDIUM**. The main examples will work, but the broader D-09 fallback contract is incomplete for unmatched models.

## 16-06

### Summary

This is the strongest plan of the set. Backward-compatible alias normalization, default filling, floor filtering before normalization, and purity tests directly address the ranker’s current weaknesses. One validation detail remains: Python booleans satisfy the proposed numeric checks.

### Strengths

- The plan correctly replaces the current hardcoded two-purpose validator at [model_ranker.py:51](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:51) with canonical-purpose validation and missing-purpose default filling.
- Alias resolution preserves existing `"execute"` callers such as the wizard snippet, which currently calls `score_candidates` for `review` and `execute` at [cli-model-selection.md:182](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-config/references/cli-model-selection.md:182).
- Floor filtering before min-max normalization is essential because normalization is candidate-set-relative at [model_ranker.py:88](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:88).
- The missing-axis, inclusive-boundary, no-mutation, invalid-UTF-8, legacy-file, and canonical-over-alias tests provide strong behavioral coverage.

### Concerns

- **MEDIUM — ordinary weights and bonuses still accept booleans as numbers.** The current validator uses `isinstance(v, (int, float))` at [model_ranker.py:55](/var/home/bazzite/git/personal/ai-kit/skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py:55), which accepts `True` and `False`. The plan explicitly excludes booleans for floor values ([16-06-PLAN.md:253](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-06-PLAN.md:253)) but describes the ordinary purpose check only as int/float plus finite ([16-06-PLAN.md:151](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-06-PLAN.md:151)). A TOML weight such as `price = true` could silently behave as `1`.
- **LOW — the final plan still does not place the repository’s full gate inside an executor task.** Its outer verification names `make test-unit` and `make validate` at [16-06-PLAN.md:343](/var/home/bazzite/git/personal/ai-kit/.planning/phases/16-ai-kit-spec-extensions/16-06-PLAN.md:343), while the repository requires `make test` before completion at [AGENTS.md:123](/var/home/bazzite/git/personal/ai-kit/AGENTS.md:123).

### Suggestions

- Introduce a shared `_is_finite_number(value)` that rejects `bool`, and use it for axes, floors, and bonuses. Add Boolean fixtures for all three.
- Add `make test` as the final phase gate after `make validate`, inside an executor-visible task or an explicit orchestrator task guaranteed to run.

### Risk Assessment

**LOW to MEDIUM**. The implementation design is coherent; validation strictness and final gating are straightforward corrections.

## Cross-plan findings

- **HIGH — mandatory skill review is not executable.** Plans 16-01 and 16-02 materially modify the same `SKILL.md`, but both place `skill-judge` only outside `<objective>/<tasks>`. Given the stated execution model, this gate will be dropped.
- **HIGH — Claude catalog freshness needs a dependency edge.** Plan 16-04 writes authoritative Anthropic IDs after runtimes detection, but no plan invalidates or refreshes a current runtimes snapshot.
- **MEDIUM — runtime metadata needs one generalized transport contract.** Plan 16-01 adds `reasoning_modes`; 16-05 extends the same mechanism with `image_input`. Both apply metadata only to entries that reach a merge site, leaving the unmatched/manual-confirmation path incomplete.
- **MEDIUM — phase verification is narrower than repository policy.** Every plan delegates only `make test-unit`; 16-06 adds `make validate`, but none schedules the required aggregate `make test`. The Python regression command does not cover installer, integration, or architecture tiers ([AGENTS.md:123](/var/home/bazzite/git/personal/ai-kit/AGENTS.md:123)).
- **LOW — plan granularity is large but dependency ordering is defensible.** All six plans modify the shared test module, and most successively extend `detection.py` or `cli.py`, so serial waves avoid high-conflict parallel edits.

## Overall Risk Assessment

**HIGH until revision.** The plans are source-aware, test-rich, and mostly align with the existing architecture. However, the Claude cache handoff can defeat a core success criterion despite green tests, and the mandatory `skill-judge` and full `make test` gates are not present where the executor can run them. Fixing those blockers, plus carrying runtime metadata through unmatched candidates and checking subprocess return codes, would reduce the phase to **MEDIUM/LOW execution risk**.

Review was read-only; no repository files were modified.

---

## Consensus Summary

Two prompt-fed, source-grounded reviewers ran (opencode-plan-review, codex-sol-high). Neither
carries a `[reviewed-without-source-citations]` or `[reviewed-without-repo-access]` marker, so both
count at full weight and the consensus gate applies to single-reviewer HIGHs. Both reviewers rate the
phase **HIGH risk until revised**. Both describe the plans as source-aware and test-rich, and say
most of the risk falls to MEDIUM/LOW once the items below are fixed. The orchestrator checked every
cited premise against source: `cache.py:25` (`tmp = path + ".tmp"`), the `cli.py:409` unmatched
branch, the `cli.py:716` `--if-stale` early return, the design spec's `:97` detect→fetch order,
`model_detect.py:64` (returncode precedent), the `detection.py:58` `OPENCODE_PID` wording, and
`model_ranker.py:55` (bool accepted as a number). All of them hold.

### Agreed Strengths

- The codex tracer (16-01) reuses the existing injected `run_fn` / argv-list / `timeout=15` /
  degrade-never-raise pattern (`detection.py:74-106`), reuses `reasoning_modes` (D-08,
  `model_catalog.py:22,111`), and pins payload minimization with a test.
- 16-02 closes a real gap: `pi` is missing from both duplicated `_VALID_NATIVE_RUNTIME` sets
  (`model_catalog.py:39`, `config_io.py:97`). Two separate codex rows implement the OR without a
  control-flow change. The `KNOWN_CLIS` scope guard is kept.
- 16-03 keeps `cache_is_stale` schema-agnostic and uses OR-refresh semantics. Splitting `_meta` off
  before processing is required because `_find_existing_key_for_runtime` (`cli.py:79`) and
  `current_candidate_keys` (`model_catalog.py:169`) treat every value as a model entry. All three
  catalog write paths are covered.
- 16-04 keeps aliases out of `models`, reads the catalog lazily, never executes claude, and labels
  provenance (`models_source` / `models_as_of`).
- 16-05's source order and stale-field handling fit the clear-on-None merge contract
  (`model_catalog.py:153,158`, `cli.py:108-144`).
- 16-06 is the strongest plan: alias normalization, default filling, floor-before-normalization,
  purity tests, and the invalid-UTF-8 hardening (`model_ranker.py:75`).
- The serial 6-wave chain is defensible because every plan edits the same `detection.py` /
  `cli.py` / test module.

### Agreed Concerns

1. **HIGH (both HIGH): the Claude catalog→runtimes freshness handoff is broken in the real refresh
   order (16-03 + 16-04).** The approved flow is `detect-runtimes --if-stale` then
   `fetch-model-catalog --if-stale` (design spec `:97`). The first upgraded run detects before the
   catalog has `_meta.anthropic_model_ids`, so it writes `dated-fallback`. The catalog then records
   the ids, but the now-current, fresh `runtimes.json` makes later `--if-stale` detects skip
   (`cli.py:716`) for up to 30 days. The 16-04 tracer runs fetch → forced detect, the opposite of
   production, so it cannot catch this. Fix: add a dependency edge (for example, stamp the catalog's
   anthropic-ids version or date into `runtimes.json` and treat a mismatch as stale, or re-stamp
   `clis.claude` after a successful models.dev refresh), plus an end-to-end test in the real order
   `detect --if-stale → fetch --if-stale → detect --if-stale` that asserts `models_source: catalog`.
2. **HIGH (codex HIGH, opencode MEDIUM): the `skill-judge` gate for the materially changed
   `skills/ai-kit-spec-config/SKILL.md` (16-01 Task 2, 16-02 Task 2) is only in `<verification>`,
   outside `<objective>`/`<tasks>`.** AGENTS.md `:45-47` requires it before completion. The plans
   route it to phase code review ("Code review for this phase should run /skill-judge"), which fits
   the project's practice of running skill-judge at code review. But "should" is not a gate, and
   nothing executor-visible or orchestrator-mandatory enforces it. Fix: either put the skill-judge
   loop and its pass threshold (no Critical/Important, or ≥96/120 with no regression) into Task 2,
   or state explicitly in `<objective>` that it is an orchestrator-owned, blocking code-review gate
   the executor must not skip or claim.
3. **HIGH (opencode HIGH, codex MEDIUM/LOW): no plan schedules the repository's full `make test`
   gate where it will run.** Every plan's executor tasks run only unittest commands. `make
   test-unit` and `make validate` appear only after `<tasks>`, and AGENTS.md `:123` requires the
   aggregate `make test`. Fix: add `make test` (and `make validate` / `make lint`) as an explicit
   final gate. It can go in the last plan's task if the executor may run `uv`, or be named as a
   mandatory orchestrator step in the `<objective>` text the executor sees.
4. **HIGH (opencode HIGH, codex MEDIUM + LOW): 16-03's E5 truth says "concurrent writers are
   last-writer-wins", which is false.** `cache_write_json` uses one fixed `path + ".tmp"`
   (`cache.py:25`), so concurrent writers can truncate or remove each other's temp file and fail
   `os.replace`. No test exercises concurrency. Fix: restate E5 as "single-writer atomicity;
   concurrent writers unsupported" (the smaller change), or deliberately plan a
   `tempfile.mkstemp` writer with a concurrency test.
5. **MEDIUM (both): 16-06 still accepts booleans as numeric weights and bonuses.** The check is
   `isinstance(v, (int, float))` (`model_ranker.py:55`), so `price = true` becomes 1.0. Only floors
   reject `bool` in the plan. Fix: a shared `_is_finite_number` that rejects `bool` for axes,
   floors and bonuses, with tests.

### Divergent Views

- **Runtime metadata dropped on the unmatched branch (codex only, MEDIUM x2 + cross-plan).**
  `_apply_runtime_meta` runs only before the two `merge_catalog_entry` calls. A candidate with no
  external match exits via `cli.py:409` (`unmatched.append(...)`), so codex `reasoning_modes` and
  opencode `image_input` never reach the manual-confirmation payload. For example, a
  `router-env/custom` id with no name-declared purpose loses `image_input`, which is the D-09
  source-2 case. opencode did not raise this.
- **Subprocess non-zero exit treated as success (codex only, MEDIUM in 16-01 and 16-05).**
  `check=False` followed by parsing `stdout` without checking `returncode`. The sibling
  `model_detect.py:64` already gates on `returncode != 0`. (The existing `detect_opencode_models`
  has the same gap, so this would be a deliberate tightening for the new parsers.)
- **`OPENCODE_PID` docstring claim (codex only, MEDIUM, 16-02).** The prescribed verbatim bullet
  says `OPENCODE/OPENCODE_PID`, but only `OPENCODE` is a signal (the same wording is already at
  `detection.py:58`). This conflicts with the certainty-labeling rule.
- **Fixture provenance (opencode only, MEDIUM 16-01, LOW 16-05, MEDIUM cross-plan).** Both fixtures
  are transcribed from values in the plan rather than sanitized from a preserved raw capture.
  Mitigating fact from the orchestrator's source-grounding pass: every transcribed value matches
  the real captures (codex-cli `debug models` slugs, visibility, priorities and efforts; opencode
  `--verbose` blocks for `openai/gpt-5.6-sol` and `router-env/my-coding`). The gap is recorded
  provenance, not wrong data.
- **Verbose-parser header/object mismatch (opencode only, MEDIUM, 16-05).** Nothing checks that
  the header equals `f"{providerID}/{id}"`, so a shifted stream could misattribute image
  capability, which is a Phase 17 eligibility gate.
- **"Exactly one automatic refresh" overstated (opencode only, MEDIUM, 16-03).** A models.dev
  failure deliberately leaves `_meta` unstamped, so every `--if-stale` retries. The wording should be
  "one successful refresh; failures retry".
- **Opencode-only LOWs:** no regression tests pin that the sibling `_meta` readers
  (`ai_kit_opencode_providers/cross_reference.py`, `ai_kit_usage_metrics/pricing.py:34`) ignore
  `_meta`; the `review: review` self-alias wording in `_normalize_purpose_aliases` is ambiguous.
- **Codex-only LOWs:** 16-05 adds a second, large-output opencode subprocess to every fresh snapshot
  with no size or performance smoke test; plan granularity is large but the ordering is defensible
  (not actionable).
- **Severity split:** opencode rates the concurrency claim and the `make test` gap HIGH while codex
  rates them MEDIUM. Codex rates the skill-judge gap HIGH while opencode rates it MEDIUM. Each is
  corroborated (both reviewers raised it), so each is carried as HIGH above.

## Verification coverage

Source-grounding pass (`plan_review.source_grounding: true`, effective authority: `grep`, from
`gsd-tools drift-guard authority`). The orchestrator ran this pass itself against the working tree at
`71b1314`. New symbols listed in 16-01's phase-wide "Artifacts this phase produces" table are
excluded. Every VERIFIED line is quoted from the current source.

### VERIFIED (existing symbols the plans cite)

- `detection.py`: `KNOWN_CLIS` :13 (`("claude", "codex", "opencode", "grok", "cursor-agent")`,
  matching 16-02's pinned value); `RUNTIMES_TTL_SECONDS` :9; `_RUNTIME_ENV_SIGNALS` :27 (today
  claude-first, 4 rows, which is the premise 16-02 replaces); `detect_current_runtime` :35;
  `detect_opencode_models` :74 (the docstring clause 16-01 Step 4 rewrites is present);
  `detect_cursor_agent_models` :88; `build_runtimes_snapshot` :134 (only opencode and cursor-agent
  branches); `_CODEGRAPH_CAPABLE_MULTI_PROVIDER_CLIS` :268 (comment :265). The imports are only
  `cache` and `vendor`, so 16-04's `split_catalog_meta` import creates no cycle (`model_catalog.py`
  imports only `cache` :8).
- `model_catalog.py`: `CATALOG_TTL_SECONDS` :10; `_MANDATORY_CATALOG_FIELDS` :12; `_FIELD_TYPES`
  :18 (`reasoning_modes: list` :22, which confirms D-08); `_VALID_NATIVE_RUNTIME` :39 (no `pi`);
  `cache_catalog_path` :42; `validate_catalog_entry` :53; list-of-strings check :111-113;
  `merge_catalog_entry` :129 (clear-on-None and strip-None-on-new behavior 16-05 relies on:
  :153 and :158); `current_candidate_keys` :162; `apply_heuristic_corrections` :175.
- `config_io.py`: `_VALID_NATIVE_RUNTIME` :97; `validate_reviewer_fields` :100 (check
  :128-129); `cfg_render_toml` :139.
- `cli.py`: `model_catalog` import :33; `infer_purpose_from_name` import :38;
  `_find_existing_key_for_runtime` :64 (iterates `existing_catalog.items()` :79, so the
  `_meta` split-off in 16-03 is required); `_preserved_or_fresh_md_fields` :108 (preserve tuple
  :130-133, md_match :134, no-source None dict :138, enrich :139); `build_model_catalog` :208;
  `merge_catalog_entry(catalog, key, entry)` :311 and :476 (the two call sites 16-01 names);
  `cache-path` local import of `cache_catalog_path` :699; `detect-runtimes` body :716-724;
  `fetch-model-catalog` :727, the single-provider comment :746, `existing_catalog = ...` :769,
  `skip_fetch` :782, catalog write :802; `confirm-catalog-entry` :810 (write :828);
  `apply-heuristic-correction` :832 (write :850).
- `model_heuristics.py`: `infer_is_router` :13, `infer_purpose_from_name` :47.
  `model_matcher.py`: `match_models_dev` :96 (exact bare-id search across every provider, which
  is what lets 16-04's bare claude ids resolve to `anthropic/<id>`).
- `model_ranker.py`: `DEFAULT_WEIGHTS` :18; `_MISSING_AXIS_DEFAULT = 49.0` :35; `_REQUIRED_AXES`
  :37; `_is_valid_weights_structure` :42 with the literal `("review", "execute")` loop :51;
  `load_ranking_weights` :64 with `except (OSError, tomllib.TOMLDecodeError)` :75, which confirms
  the `UnicodeDecodeError` gap 16-06 closes; `score_candidates` :109 with bare
  `weights[purpose]` :118.
- Tests (`tests/test_ai_kit_spec.py`): all 14 cited classes exist (`TestRenderAndWriteToml` :219,
  `TestValidateCatalogEntry` :426, `TestMergeCatalogEntry` :594, `TestCurrentCandidateKeys` :666,
  `TestApplyHeuristicCorrections` :677, `TestCacheStaleness` :774, `TestDetectCurrentRuntime`
  :807, `TestDetectOpencodeModels` :845, `TestDetectCursorAgentModels` :859,
  `TestBuildRuntimesSnapshot` :1112, `TestMainCli` :1858, `TestLoadRankingWeights` :3396,
  `TestScoreCandidates` :3483, `TestBuildModelCatalog` :4067, `TestFetchModelCatalogCli` :4815).
  All 19 cited test methods and helpers exist exactly once. `TestBuildRuntimesSnapshot.
  test_non_multi_provider_clis_have_no_models_key` :1142 uses `run_fn=lambda *a, **k: None`,
  which 16-01's `getattr(result, "stdout", None)` guard keeps green. `tests/fixtures/` exists
  (`tests/test_setup.py:46`).
- Docs: `skills/ai-kit-spec-config/SKILL.md:208` (codex paragraph) and `:243` (native_runtime
  value list); `references/cli-model-selection.md:20`, `:65`, `:190` (`for purpose in
  ('review', 'execute')`); `model_detect.py` `build_candidate_pool` docstring :75-80; design spec
  §11 Errata :278 with the `**Catalog**` / `reasoning_modes` bullet :290-291 (so 16-01 Task 2
  Step 3 is a no-op, as the plan expects); `AGENTS.md` "Architecture" :65 and the
  `native_runtime` bullet :73; `AGENTS.md` has no line describing the old precedence order (16-02
  Task 2 Step 3 expects no edit).
- Catalog readers outside `ai_kit_spec` do not iterate raw catalog values unfiltered:
  `ai_kit_usage_metrics/pricing.py:34` does a `catalog.get(canonical_key(...))` lookup, and the
  wizard snippet filters by `current_candidate_keys` (`cli-model-selection.md:178`). This
  supports 16-03's AGENTS.md claim. `ai_kit_opencode_providers/cross_reference.py` `scan_catalog`
  :64 skips non-string field values without raising (opencode reviewer's citation, confirmed).

### VERIFIED against the real captures from the research session (scratchpad, 2026-09-24)

- `codex debug models` capture: 6 slugs in fixture order, `visibility` hide/list/list/list/list/
  hide, priorities 3/4/7/8/12/43, and effort lists exactly as 16-01 Step 1 specifies.
- models.dev `anthropic` provider: all four fallback ids (`claude-fable-5-1`,
  `claude-opus-5-5`, `claude-sonnet-5`, `claude-haiku-4-5-20251001`) are present (15 anthropic
  models in total). `claude-sonnet-5.modalities == {'input': ['text','image','pdf'], ...}`.
- `opencode models --verbose` capture: 8528 lines, 110 header+JSON blocks. A `raw_decode` walk
  (16-05 Step 2's algorithm) parses all 110. `openai/gpt-5.6-sol` has image True and
  `router-env/my-coding` has image False, which matches the 16-05 fixture.

### UNCHECKABLE (INFO: the `grep` authority cannot assert these)

- Function signatures and parameter defaults of the new or extended functions (for example,
  whether `build_model_catalog` accepts a trailing keyword without breaking positional callers).
  `grep` cannot verify signatures; the plans' own verify commands cover this.
- Env signals `PI_CODING_AGENT` (external `@earendil-works/pi-coding-agent` `dist/config.js`) and
  `CODEX_THREAD_ID` (`~/.codex/sessions` snapshots): these are outside the repo and are labeled
  source-inspected / not live-verified by the plans themselves.
- `claude --help` alias list (`fable`/`opus`/`sonnet`) for Claude Code 2.1.281: not re-run. D-07
  forbids invoking the aliased `claude`.
- `~`-prefixed line numbers in plan `read_first` blocks: these are approximate by design. The
  spot-checks above all land within a few lines.

### MISSING / AMBIGUOUS

- None. Every existing symbol cited in the plans resolved to a real declaration.

### Cross-artifact fact-drift pass

- Phase status (`gsd-tools drift-guard phase-status --phase 16`): **uncheckable**
  (`reason: phase_not_in_roadmap`; STATE.md says "Ready to execute" / `status: executing`).
  The seam could not parse ROADMAP.md's `- [ ] **Phase 16: ...**` entry, so this axis was
  skipped, not found consistent.
- ROADMAP Success Criteria ↔ `must_haves.truths`: no contradiction. SC1's order
  (pi > opencode > cursor > codex > claude) = 16-02. SC2 (codex `debug models`; claude aliases +
  catalog ids + dated fallback; never functions/aliases) = 16-01 and 16-04. SC3 (optional
  `image_input` and `reasoning_modes`; old caches load) = 16-01, 16-03 and 16-05. SC4 (five
  purposes, `review`/`execute` aliases) = 16-06. Not flagged: 16-06 records that `execute`
  callers now rank with the `execution` weights. SC4 says callers keep working "unchanged", not
  that their rankings stay the same, so this is a documented behavior change and not a
  contradiction.
- ROADMAP `**Requirements:**` (SPEC-01..04) ↔ plan requirement refs: consistent (16-01
  SPEC-02/03, 16-02 SPEC-01, 16-03 SPEC-03, 16-04 SPEC-02, 16-05 SPEC-03, 16-06 SPEC-04).
- CONTEXT.md Decisions ↔ plan usage: no contradiction. The D-01 amendment, D-02, D-03, D-04,
  D-05, D-06, D-07, D-08, D-10, D-11 and D-12 are used as stated. Not flagged (advisory): D-09
  scopes source 2 to "opencode-routed ids that have no models.dev match". 16-05 also lets the
  runtime value fill a models.dev match that has no `modalities`. That widens D-09 without
  contradicting it, because models.dev made no statement.
- Advisory only: this pass contributes nothing to `current_high` / `current_actionable`.

## Cycle accounting (orchestrator)

- Consensus gate engaged (2 grounded reviewers, no discount markers). Unresolved HIGHs: 4 (Agreed
  Concerns 1-4), all corroborated by both reviewers and none addressed in the current PLAN.md files.
- Unresolved actionable MEDIUM/LOW: 11. These are the bool weights (both reviewers) plus ten
  single-reviewer items under Divergent Views: unmatched-branch metadata; returncode in 16-01;
  returncode in 16-05; `OPENCODE_PID`; fixture provenance; header/id mismatch; "exactly one
  refresh"; sibling `_meta` tests; the review self-alias wording; the verbose-call size smoke test.
  The MEDIUMs that restate a HIGH (16-04 test order, catalog/runtime freshness coupling,
  concurrency untested) are folded into that HIGH and not counted twice. The granularity LOW is not
  actionable.
- The fact-drift findings above are advisory and not counted.
