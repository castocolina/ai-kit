---
phase: 05
reviewers: [opencode]
reviewed_at: 2026-09-10T09:22:47Z
plans_reviewed: [05-01-PLAN.md, 05-02-PLAN.md, 05-03-PLAN.md, 05-04-PLAN.md, 05-05-PLAN.md, 05-06-PLAN.md]
models:
  opencode: "xai/grok-4.6 (reasoning=high)"
model_sources:
  opencode: "pinned"
cycles:
  - cycle: 1
    reviewed_at: 2026-09-10T07:03:58Z
    reviewers: [opencode]
    models:
      opencode: "openai/gpt-5.6-sol (reasoning=high)"
  - cycle: 2
    reviewed_at: 2026-09-10T08:57:30Z
    reviewers: [opencode]
    models:
      opencode: "xai/grok-4.6 (reasoning=high)"
    note: "Reviews plans as revised in commit 19131c2 to address Cycle 1's findings."
  - cycle: 3
    reviewed_at: 2026-09-10T09:22:47Z
    reviewers: [opencode]
    models:
      opencode: "xai/grok-4.6 (reasoning=high)"
    note: "Reviews plans as revised in commit 116fb31 to address Cycle 2's 3 HIGH + 12 MEDIUM/LOW findings."
---

# Cross-AI Plan Review — Phase 05

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
(none)
<!-- gsd:plan-revision-conflicts:end -->

## Cycle 1 (2026-09-10T07:03:58Z)

## OpenCode Review

## 05-01

### Summary

The tracer-first structure is sensible, and the plan correctly reuses several established repository patterns. However, the specified pipeline cannot meet its own losslessness or second-run idempotency criteria. Stable raw identities, refined uniqueness, crash recovery, and private file permissions need explicit designs before execution.

### Strengths

- The family mapping matches the shipped source exactly: `tools/hooks/detect.py:23-29` defines the five pairs named in `05-01-PLAN.md:155`.
- The pricing-cache path matches the existing implementation at `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/config_paths.py:41-47`.
- Hermetic path resolution through explicit environment dictionaries is consistent with the repository's testing discipline and `pyproject.toml:91-95`.
- The planned `</script` escaping and parameterized SQL address real injection boundaries (`05-01-PLAN.md:228-239`, `05-01-PLAN.md:548-549`).
- Test and gate registration targets the actual aggregate surfaces in `Makefile:33-45` and `.pre-commit-config.yaml:14-56`.

### Concerns

- **HIGH: Refined idempotency is not implementable as specified.** `05-01-PLAN.md:333-343` rereads the complete raw file and inserts every resulting row on each `refine` run. The schema and insertion contract at `05-01-PLAN.md:191-201` define no unique constraint, deletion/rebuild transaction, UPSERT, or duplicate check. This contradicts the unchanged row-count requirement at `05-01-PLAN.md:383-385`.
- **HIGH: Capture is not lossless across malformed or newly introduced event shapes.** The plan skips malformed lines, queue operations, and later malformed tool entries (`05-01-PLAN.md:170-182`, `05-01-PLAN.md:293-300`, `05-01-PLAN.md:446-467`). The source requirement calls for verbatim, lossless, append-only capture at `.planning/REQUIREMENTS.md:41` and `docs/prds/ai-kit-usage-metrics-dashboard-v1.0-prd.md:79-84`. Skipping unknown lines prevents future reparsing after format support improves.
- **HIGH: Raw append and cursor advancement are not one atomic operation.** The sequence at `05-01-PLAN.md:333-339` appends records and then writes a separate cursor file. A crash between those writes causes the same source lines to be appended again on the next run.
- **HIGH: `raw_ref` has no stable identity contract.** It appears in the schema at `05-01-PLAN.md:191-195` but is never defined. Without a deterministic identity such as `(runtime, source_file, source_record_id)`, later plans cannot enforce idempotency or safely update historical rows.
- **HIGH: The reused atomic writer assumes the destination already exists.** The source implementation calls `os.stat(target)` before creating its temporary file at `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/atomic_write.py:40-44`. Raw files, cursor files, and `dashboard.html` are new files, but the plan does not define the required absent-file branch.
- **HIGH: Sensitive output permissions are unspecified.** The claim that data is readable by the local user only at `05-01-PLAN.md:550` does not follow from ordinary `os.makedirs` and SQLite creation. Session logs can contain commands, paths, code, and secrets; the plan needs `0700` directories and `0600` files, with tests under a permissive umask.
- **MEDIUM: The capture interface is ambiguous.** The plan alternately describes yielded records, an updated cursor, and a stats dictionary without defining one return type (`05-01-PLAN.md:170-181`, `05-01-PLAN.md:333-339`).

### Suggestions

- Define a concrete capture result contract containing `records`, `cursor`, and `stats`.
- Store original line text or bytes plus parse status in every raw envelope. Preserve unknown and malformed records rather than dropping them.
- Give each raw event a deterministic identity and enforce `UNIQUE(raw_ref, step_index)` in SQLite.
- Use UPSERT or a transactional full refined-store rebuild. Document how inferred classifications survive subsequent refinement.
- Make raw append deduplicate by stable identity so a cursor-write crash remains safe.
- Adapt the atomic writer for absent files and enforce private directory/file modes.

### Risk Assessment

**HIGH.** The overall architecture is appropriate, but the current mechanics violate the tracer's central losslessness and idempotency claims.

## 05-02

### Summary

Read-only access to external SQLite stores and independent source isolation are good choices. The opencode design is nevertheless based on an incorrect primary-key type and omits the session/message data that Plan 05-04 requires.

### Strengths

- Opening external databases in read-only URI mode is a strong defensive boundary (`05-02-PLAN.md:187-192`, `05-02-PLAN.md:375-376`).
- The three independent RTK cursors correctly recognize that database rows and tee files have different incremental-capture semantics (`05-02-PLAN.md:311-323`).
- Capturing RTK parse failures as a distinct source type preserves useful diagnostic data (`05-02-PLAN.md:27-28`).
- Missing source handling aligns with the isolation requirement in `.planning/REQUIREMENTS.md:41`.

### Concerns

- **HIGH: The opencode cursor premise is factually wrong.** `05-02-PLAN.md:193-205` and `05-02-PLAN.md:266-267` call `part.id` an incrementing integer primary key. A live read-only `PRAGMA table_info(part)` against `~/.local/share/opencode/opencode.db` returned `id TEXT PRIMARY KEY`. The proposed integer fixture and `last_part_rowid` contract do not model the installed database.
- **HIGH: Plan 05-04 cannot correlate opencode commands.** Plan 05-02 stores only parsed `part.data` in the payload (`05-02-PLAN.md:225-237`) and explicitly creates only a `part` fixture (`05-02-PLAN.md:244-252`). Plan 05-04 later requires `part.message_id`, `part.session_id`, timestamps, matching message data, and session directories at `05-04-PLAN.md:452-467` and `05-04-PLAN.md:503-514`. Those values were discarded.
- **HIGH: The title and objective promise session/message/part capture, but the task captures only `part`.** See `05-02-PLAN.md:40-57`, `05-02-PLAN.md:165`, and `05-02-PLAN.md:193-205`.
- **HIGH: The plan contradicts itself on which parts are captured.** The must-have says only `data.type == "tool"` at `05-02-PLAN.md:26`; task behavior and done criteria say every valid part type at `05-02-PLAN.md:198-204` and `05-02-PLAN.md:282-286`.
- **HIGH: Current and legacy opencode sources are not both covered.** The authoritative detailed requirement names `storage/` plus `opencode.db` at `.planning/intel/requirements.md:126-133`, while this plan handles only the database. It either needs a legacy-storage parser/version branch or a formal requirements amendment.
- **HIGH: Parsed dictionary equality is not verbatim capture.** `05-02-PLAN.md:209-219` calls payloads byte-identical and then weakens that to parsed equality. Whitespace, duplicate keys, number spelling, and key ordering are lost.
- **MEDIUM: Tee idempotency relies only on filenames.** `05-02-PLAN.md:318-323` assumes tee files are immutable and names never recur. The plan supplies no live evidence or size/hash validation for that assumption.
- **MEDIUM: SQLite URI construction does not account for URI-significant path characters.** The literal `file:{path}?mode=ro` form at `05-02-PLAN.md:187-188` needs correct URI escaping.

### Suggestions

- Cursor opencode with SQLite `rowid` if available, or a deterministic `(time_created, id)` tuple after verifying ordering.
- Capture complete session, message, and part rows, including IDs and timestamps. Use separate cursors per table or one joined snapshot contract.
- Preserve each database row's original JSON text alongside parsed data and parse status.
- Resolve the legacy `storage/` requirement explicitly.
- Replace source-content grep checks with tests that attempt a write and confirm SQLite rejects it.

### Risk Assessment

**HIGH.** The installed schema contradicts the plan, and the data needed by the dependent refiner would never reach the raw store.

## 05-03

### Summary

The Codex recursive capture strategy is appropriately conservative, and Cursor confidence is treated as machine-readable data. The Cursor plan contains an impossible source-text acceptance condition and does not define the session identity needed by the next wave.

### Strengths

- Recursive Codex rollout discovery matches the documented layout at `docs/prds/ai-kit-usage-metrics-dashboard-v1.0-prd.md:86-91`.
- Keeping Codex `function_call.arguments` opaque during raw capture preserves the raw/refined boundary (`05-03-PLAN.md:109-116`, `05-03-PLAN.md:179-192`).
- Cursor's low-confidence marker directly supports the project's confidence-labeling constraint at `.planning/PROJECT.md:121-129`.
- Explicitly refusing to infer structure from undocumented blobs follows the project's core value.

### Concerns

- **HIGH: The Cursor source-text test is impossible to pass.** The required module docstring explicitly contains `store.db` and `blobs` at `05-03-PLAN.md:315-324`, while acceptance and verification require zero occurrences of those exact strings at `05-03-PLAN.md:351-363`.
- **HIGH: Cursor session identity and chronology are undefined.** The observed transcript shape contains no timestamp or session ID (`05-03-PLAN.md:117-129`). Capture stores only the parsed line and source path, yet Plan 05-04 groups by `(runtime, session_id)` and chronological timestamp at `05-04-PLAN.md:428-451`. The plan must define extraction from the transcript path and deterministic line-order fallback.
- **HIGH: Cursor confidence is dropped before the dashboard.** Plan 05-03 stores confidence in raw payloads (`05-03-PLAN.md:286-296`), but the full refined schema at `05-01-PLAN.md:191-195` has no source-confidence field. The dashboard therefore cannot visibly label Cursor-derived records as required by `.planning/PROJECT.md:121-125`.
- **HIGH: The Cursor source exclusion conflicts with the detailed source inventory.** The PRD names both transcripts and `store.db` at `docs/prds/ai-kit-usage-metrics-dashboard-v1.0-prd.md:86-92`. Exclusion may be correct, but claiming full requirement completion at `05-03-PLAN.md:399-408` requires a formal requirement amendment or evidence that transcripts alone are the complete usable source.
- **HIGH: The payload contract now diverges from Plan 05-01.** Plan 05-01 says every source uses one uninterpreted payload shape with no variations (`05-01-PLAN.md:52`, `05-01-PLAN.md:293-300`); Cursor introduces `{"confidence": "low", "line": ...}` at `05-03-PLAN.md:286-296`.
- **MEDIUM: Cursor session-data path resolution borrows a config-file rule without evidence.** The cited research only establishes `CURSOR_CONFIG_DIR` and `XDG_CONFIG_HOME` for `cli-config.json` (`.planning/phases/04-config-doctor/04-RESEARCH.md:580-592`). It does not establish that Cursor relocates `projects/` session data the same way.
- **MEDIUM: Cursor malformed-file isolation is asserted but not tested.** The task's Cursor tests cover valid entries with optional fields but not malformed JSON or invalid UTF-8 (`05-03-PLAN.md:333-341`), despite the plan-wide claim at `05-03-PLAN.md:29`.

### Suggestions

- Put `source_confidence` in the common envelope and refined schema instead of wrapping only Cursor's payload.
- Derive Cursor `session_id` from the transcript directory and preserve per-file line order explicitly.
- Test prohibited behavior through AST/import/call inspection rather than banning explanatory words from docstrings.
- Verify Cursor session-root override behavior independently from config-file resolution.
- Formally amend the source requirement if `store.db` remains excluded.

### Risk Assessment

**HIGH.** Capture itself is tractable, but the present contract cannot feed correctly grouped or visibly confidence-labeled Cursor records into later waves.

## 05-04

### Summary

Separating decomposition from cwd state is a good design. The specified scanner, state machine, and accounting model still contain several contradictions that would produce incorrect classifications and inflated token/price totals.

### Strengths

- Independent `decomposer.py` and `cwd_state.py` modules create focused, testable contracts (`05-04-PLAN.md:37-40`).
- The resolve-before-observe ordering is clearly specified and directly tests the cross-call cwd scenario (`05-04-PLAN.md:323-337`, `05-04-PLAN.md:361-373`).
- Claude's native cwd and Cursor's unknown token/price handling avoid inventing unavailable data (`05-04-PLAN.md:31`, `05-04-PLAN.md:471-477`).
- Codex nested JSON parsing is assigned to the refined layer and guarded against malformed data (`05-04-PLAN.md:611-619`).

### Concerns

- **HIGH: The opencode branch depends on data Plan 05-02 does not capture.** Message IDs, session IDs, message records, and session directories required at `05-04-PLAN.md:452-467` and `05-04-PLAN.md:503-514` are absent from the Plan 05-02 envelope.
- **HIGH: The `||` behavior is internally impossible.** The plan says an otherwise plain `a || b` becomes `unclassified` at `05-04-PLAN.md:160-168`, but `classify_segment` returns `simple` for every non-control-flow first token at `05-04-PLAN.md:175-182`. The only described whole-command fallback is an unterminated quote.
- **HIGH: Heredocs and subshells will not reach `unclassified`.** They are required examples at `05-04-PLAN.md:30` and in the PRD at `docs/prds/ai-kit-usage-metrics-dashboard-v1.0-prd.md:139-144`, but the proposed scanner tracks only quotes and control-flow blocks (`05-04-PLAN.md:206-244`).
- **HIGH: Control-flow suppression is underdefined.** The closer mapping at `05-04-PLAN.md:235-239` omits `until` and `select`, despite classifying them as control-flow keywords. It also does not specify nested blocks, comments, command substitutions, or token boundaries.
- **HIGH: `compound_decomposed` has no coherent persisted meaning.** The must-have says compound rows may carry that shape at `05-04-PLAN.md:33`; behavior says every decomposed step is `simple` at `05-04-PLAN.md:183-196`; acceptance says the overall shape is tracked separately at `05-04-PLAN.md:258-273`. The schema has only one per-row `command_shape` column and no parent-shape column (`05-01-PLAN.md:191-195`).
- **HIGH: Token and cost attribution will overcount.** Claude and opencode turn-level usage is copied onto each command, while Codex's nearest preceding `total_token_usage` is assigned to command rows (`05-04-PLAN.md:452-477`). A turn containing multiple commands will be counted multiple times, and Codex's cumulative totals may be repeated across many rows. The PRD requires meaningful per-command/session token and price axes at `docs/prds/ai-kit-usage-metrics-dashboard-v1.0-prd.md:266-268`.
- **HIGH: RTK bookkeeping is placed in columns defined as LLM usage.** `05-04-PLAN.md:478-491` acknowledges RTK's counts are not LLM tokens but stores them in `tokens_input` anyway. Session grouping in Plan 05-05 then sums semantically incompatible values.
- **HIGH: Authoritative opencode `workdir` is not used to rebase state before observing `cd`.** `05-04-PLAN.md:522-531` returns the direct workdir for the row but still observes the command against the old carried state. A call executed in `/actual` with `cd child` can therefore set the next fallback cwd relative to a stale seed.
- **MEDIUM: Connector semantics are lost.** The decomposer returns operators, but the refined schema does not store them. Counts can treat a command after failed `&&` as an invocation even though no per-segment execution evidence exists.

### Suggestions

- Resolve Plan 05-02's raw contract before this plan executes.
- Define a conservative scanner with explicit unsupported-shape detection and complete control-flow closer/nesting rules.
- Add a parent command shape or persist `compound_decomposed` consistently.
- Separate request-level usage from command rows, or define a documented allocation strategy that prevents double counting.
- Keep RTK savings fields in separate columns or a separate refined table.
- Rebase `CwdState.current` from an authoritative per-call cwd before observing that call.
- Preserve operators and execution certainty so dashboard counts do not present conditional segments as confirmed invocations.

### Risk Assessment

**HIGH.** This plan implements the core normalization logic, but its current contracts would misclassify shell input and produce misleading usage totals.

## 05-05

### Summary

The local static dashboard approach matches the amended phase decision and keeps the implementation dependency-free. The proposed controls and tests do not prove, or fully implement, the requirement that all five axes are both filterable and sortable.

### Strengths

- Static embedded data follows the accepted no-server/no-export decision at `.planning/phases/05-usage-metrics-dashboard/05-CONTEXT.md:95-122`.
- Querying only the refined store supports the no-live-reparse requirement (`05-05-PLAN.md:23-26`).
- Full-column embedding provides a useful forward-compatible data contract (`05-05-PLAN.md:115-119`).
- Null-last numeric sorting and session aggregation are concrete, testable behaviors (`05-05-PLAN.md:127-134`).
- The plan includes the required `skill-judge` loop, consistent with `.planning/PROJECT.md:126-129`.

### Concerns

- **HIGH: All five axes are not both filterable and sortable.** The PRD requires each axis to be filterable and sortable at `docs/prds/ai-kit-usage-metrics-dashboard-v1.0-prd.md:237-268`. The plan provides family/model filters, date filters, and sorting only for token and price columns (`05-05-PLAN.md:120-134`). It lacks literal-command filtering, token/price filters, and sorting for date/model/command/family.
- **HIGH: The shipped JavaScript is not executed by any test.** The must-have says the same JS shipped in the file answers the canonical query (`05-05-PLAN.md:23`), but the test reimplements that logic in Python and explicitly verifies only the data contract (`05-05-PLAN.md:174-194`). Broken event handlers, date calculations, grouping, or rendering would pass.
- **HIGH: The dashboard's read-only database claim lacks a read-only connection path.** Plan 05-01's `open_refined_db` creates directories, opens read-write SQLite, and ensures the schema (`05-01-PLAN.md:285-291`). Plan 05-05 does not define a separate read-only opener for the `dashboard` subcommand.
- **HIGH: Inferred classifications are embedded but not visibly labeled.** The project's confidence rule requires lower-confidence results to be visible (`.planning/PROJECT.md:121-125`). Plan 05-05 renders/filter-groups on `family` and does not specify displaying `inferred_family` with `inferred_confidence`.
- **HIGH: Safe DOM rendering is contradictory.** The action proposes template-string row rendering into `<tbody>` at `05-05-PLAN.md:158-165`, while the threat mitigation requires data to flow through `textContent` and not `innerHTML` at `05-05-PLAN.md:343-347`. The construction mechanism must be unambiguous.
- **MEDIUM: Source-string absence is not sufficient proof of no network capability.** The grep at `05-05-PLAN.md:216-220` can miss aliased or indirect calls and can fail on harmless prose. AST import/call checks are more precise.
- **MEDIUM: There is no real browser or DOM verification.** Presence of `<select>` and `<option>` strings does not establish usable desktop/mobile behavior, date controls, sorting, or safe rendering.

### Suggestions

- Add filter and sort contracts for every axis, including literal command, numeric token/price ranges, and sortable date/model/family columns.
- Extract pure JavaScript filter/sort/group functions and execute them in a JS runtime, or add a live-DOM/browser verification step.
- Add `open_refined_db_readonly` using SQLite URI mode and define missing/corrupt database behavior.
- Render inferred values and their confidence separately from mechanically determined family.
- Require DOM construction with `createElement` and `textContent`; prohibit data-driven `innerHTML`.

### Risk Assessment

**HIGH.** The presentation mechanism is appropriate, but the plan's acceptance tests can pass while the interactive dashboard is broken or incomplete.

## 05-06

### Summary

The explicit, user-triggered classification pass and separate inferred columns fit the requirement. The plan cannot run safely in parallel with 05-05, its example skeleton algorithm does not produce the claimed groups, and its database updates lack a commit contract.

### Strengths

- Keeping classification out of `run` respects the requirement that it occur only after real history exists (`05-06-PLAN.md:24-27`, `.planning/REQUIREMENTS.md:44`).
- Updating only `inferred_family` and `inferred_confidence` preserves the mechanical result (`05-06-PLAN.md:167-173`).
- Ambiguous groups are intentionally left unclassified instead of guessed (`05-06-PLAN.md:146-157`).
- The historical lower-threshold rerun test addresses accumulated records rather than only new input (`05-06-PLAN.md:174-179`).

### Concerns

- **HIGH: Plans 05-05 and 05-06 are not parallel-safe.** Both are Wave 5 and both edit `SKILL.md` and `tests/test_ai_kit_usage_metrics.py` (`05-05-PLAN.md:5-13`, `05-06-PLAN.md:5-14`, `05-06-PLAN.md:264-305`). Plan 05-06 nevertheless claims zero overlap at `05-06-PLAN.md:31`.
- **HIGH: `SKILL.md` is missing from 05-06 frontmatter.** Task 2 edits it at `05-06-PLAN.md:264-296`, but `files_modified` at `05-06-PLAN.md:10-14` does not list it.
- **HIGH: The final material `SKILL.md` edit bypasses the skill-quality gate.** Plan 05-05 runs `skill-judge`, then same-wave Plan 05-06 may append classification documentation afterward. The final file is therefore not necessarily the reviewed version, contrary to `.planning/PROJECT.md:126-129`.
- **HIGH: The proposed skeleton normalization cannot make its own examples equal.** The two examples differ in loop variable declaration, glob, and bare search term (`05-06-PLAN.md:128-138`). The implementation replaces only quoted strings and `$` references (`05-06-PLAN.md:182-194`), leaving `f` versus `x`, `*.py` versus `*.md`, and `pattern` versus `other`.
- **HIGH: Family inference recognizes aliases asymmetrically.** The candidate rule at `05-06-PLAN.md:146-157` accepts tokens only when `family_of(token) != token`. That recognizes `rg -> grep` but rejects a literal `grep` token because `family_of("grep") == "grep"`, even though both are curated family members.
- **HIGH: SQLite persistence is unspecified.** `update_inferred_family` executes an UPDATE, and `run_classification` calls it repeatedly (`05-06-PLAN.md:158-173`), but neither task specifies a transaction or `conn.commit()`. Closing a normal Python SQLite connection without commit rolls those writes back.
- **HIGH: Improved reruns do not clear stale inference.** The pass only updates currently qualifying groups (`05-06-PLAN.md:158-169`). If improved rules invalidate an earlier inference or make it ambiguous, the old annotation remains and is still presented as current.
- **HIGH: Dashboard regeneration and visibility are not connected.** `classify` updates SQLite but does not regenerate `dashboard.html`, and Plan 05-05 does not specify visibly rendering inferred confidence. Users can run classification successfully and continue viewing stale or unlabeled output.
- **MEDIUM: Final verification does not execute all commands claimed by acceptance.** Acceptance requires `make test`, `make lint`, and `make validate` at `05-06-PLAN.md:307-313`; the `<verify>` block runs only the focused unittest and `make validate` at `05-06-PLAN.md:316-320`.

### Suggestions

- Make 05-06 depend on 05-05, or make 05-05 depend on 05-06 and move final documentation plus `skill-judge` to the last plan.
- Add `SKILL.md` to frontmatter and eliminate same-wave shared-file edits.
- Design and test a normalization that actually abstracts loop variables, globs, and literal arguments.
- Detect curated members by explicit pair membership rather than `family != token`.
- Run classification in one transaction with an explicit commit and rollback on failure.
- Recompute annotations from scratch or clear stale annotations before applying current rules.
- Make `classify` regenerate the dashboard, or document and test the required `classify` then `dashboard` sequence.
- Run every repository gate named by acceptance.

### Risk Assessment

**HIGH.** The intended behavior is reasonable, but current wave ordering and algorithm details make the plan non-executable as written.

## Consensus (OpenCode's own)

### Overall Assessment

**Status: Issues Found. Overall risk: HIGH.**

The six-plan sequence has a sound high-level architecture: isolated runtime capture, raw/refined separation, a static local dashboard, and confidence-labeled inference. Four blocking themes prevent execution:

- The raw contract is not genuinely lossless or crash-idempotent.
- Plan 05-02 discards the opencode metadata Plan 05-04 requires and assumes the wrong primary-key type.
- Token, cost, RTK bookkeeping, command execution, and compound-shape semantics are mixed in ways that would make dashboard totals misleading.
- Plans 05-05 and 05-06 conflict in Wave 5, and the final `SKILL.md` would not necessarily be the version reviewed by `skill-judge`.

There is also an unresolved planning-source contradiction: `.planning/PROJECT.md:76-78` still says the dashboard reads a local export, while `.planning/REQUIREMENTS.md:43`, `.planning/ROADMAP.md:153-156`, and `05-CONTEXT.md:95-137` require no export/import step. The project document should be formally amended before execution.

### Required Resolution Order

1. Define one stable, lossless raw envelope and transactional idempotency model.
2. Correct opencode capture against the live TEXT-ID schema and include session/message/part metadata.
3. Redesign refined identities, command-shape semantics, source confidence, and token/cost attribution.
4. Make the decomposer conservative and test every unsupported shell shape it claims to classify.
5. Complete all five dashboard filter/sort axes and execute the shipped JavaScript during verification.
6. Serialize 05-05 and 05-06, then run `skill-judge` against the final merged `SKILL.md`.
7. Run the focused suite plus `make test`, `make lint`, and `make validate` before phase closure.

### Cycle 1 Consensus Summary

Only one reviewer (OpenCode, model `openai/gpt-5.6-sol`, reasoning=high) ran this cycle — no cross-reviewer corroboration is possible, so every finding below is single-reviewer. The reviewer cited concrete `path:line` evidence throughout and independently verified two live-data claims against the actual `opencode.db` schema (finding the `part.id` primary key is TEXT, not integer, contradicting Plan 05-02), so this review counts as source-grounded (no `[reviewed-without-source-citations]` or `[reviewed-without-repo-access]` marker applies).

#### Agreed Strengths
N/A — single reviewer this cycle; see OpenCode's per-plan Strengths sections above.

#### Agreed Concerns
N/A — single reviewer this cycle; see OpenCode's per-plan Concerns sections above. The most structurally significant single-reviewer HIGH findings are:
- 05-01's raw/refined pipeline is not lossless or crash-idempotent as specified.
- 05-02 captures the wrong opencode `part.id` type (TEXT, not integer) and omits session/message metadata that 05-04 depends on.
- 05-04's token/cost attribution would overcount, and several shell-shape classifications (`||`, heredocs, subshells, `until`/`select`) are internally contradictory or unimplemented.
- 05-05 does not fully implement the "all five axes filterable and sortable" requirement, and its test suite never executes the shipped JavaScript.
- 05-05 and 05-06 are scheduled in the same wave but both edit `SKILL.md` and the same test file, and 05-06's frontmatter omits `SKILL.md` from `files_modified`.

#### Divergent Views
N/A — single reviewer this cycle.

---

## Cycle 2 (2026-09-10T08:57:30Z)

Reviews the plans as revised in commit `19131c2` to address Cycle 1's findings above. Reviewer: OpenCode, model `xai/grok-4.6`, reasoning=high.

## OpenCode Review

## 05-01

### Summary

Round 1's blocking gaps are closed in the plan text. The tracer now has a real identity (`raw_ref`), lossless envelopes, UPSERT, crash-safe append, `0700`/`0600` modes, and `CaptureResult`. Grounded against this repo, the cited patterns are real: `CURATED_SUBSTITUTIONS` at `tools/hooks/detect.py:23-29`, `catalog_path` at `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/config_paths.py:41-47`, and `write_preserving_mode` at `atomic_write.py:40-41` still does an unguarded `os.stat(target)` — the new `FileNotFoundError` branch is required. Residual issues are small (test-count wording, catalog still absent on disk).

### Strengths

- `UNIQUE(raw_ref, step_index)` plus `ON CONFLICT ... DO UPDATE` excluding `inferred_family`/`inferred_confidence` makes the second-`run` row-count claim implementable (`05-01-PLAN.md` key_links / `insert_commands` behavior).
- Every JSONL line becomes an envelope with `raw_text` and `parse_status` (`ok` / `malformed` / `recognized_no_data`). That matches `REQ-usage-metrics-raw-capture` at `.planning/REQUIREMENTS.md:41`.
- `append_records` dedupes on the target file's own `raw_ref` set, so a crash between append and cursor write cannot duplicate lines.
- Mode `0700`/`0600` with an umask test is a real mitigation, not an ambient-permission hope. `atomic_write.py:41` still assumes the destination exists; the plan names that bug and adds the missing branch.
- `CAPTURE_SOURCES = {"claude": ...}` matches Config Doctor's registry taste (`tools/config_doctor_checks.py:566`). Gate edits target the real surfaces: `Makefile:33-39`, `.pre-commit-config.yaml:21,48,53`, `pyproject.toml:93`.
- Live check: no `model-catalog.json` on this machine. The `(None, "unknown")` price degrade is the correct path, not a fake dollar figure.

### Concerns

- **LOW:** Task 2 says "Task 1's 10+" tests while Task 1's floor is 14 (`05-01-PLAN.md` Task 1 acceptance vs Task 2 acceptance). The floors still work; the comment is wrong.
- **LOW:** `cli.py` `refine` this wave reads only `raw/claude.jsonl`. Intended, but 05-04 must actually switch the entry point to `refine_all` or later sources never refine.

### Suggestions

- Align the Task 2 "10+" sentence with Task 1's 14-test floor.
- Keep `open_refined_db_readonly` in Wave 1 as specified; 05-05 depends on it.

### Risk Assessment

**LOW.** Cycle 1 HIGHs for this plan are addressed with testable contracts. Safe to execute after the leftover comment nit.

## 05-02

### Summary

The TEXT-PK cursor rewrite and the session/message/part + `storage/` capture match the installed databases. Re-checked live: `part.id` / `message.id` / `session.id` are `TEXT` primary keys with `time_created INTEGER`; `rtk` `commands.id` / `parse_failures.id` are `INTEGER` primary keys. Cycle 1's schema error is gone. One leftover identity formula in `key_links` disagrees with behavior/action.

### Strengths

- `(time_created, id)` tuple cursor is the right model for TEXT PKs. Same-timestamp two-id test actually exercises that, not `time_created > cursor`.
- Top-level `session_id` / `message_id` / `time_created` / `record_id` give 05-04 join keys. Cycle 1's "05-04 cannot correlate opencode" finding is fixed here.
- `mode=ro` plus `urllib.parse.quote` is the right external-DB boundary. Python's `quote()` default `safe='/'` leaves slashes intact and still escapes `?`/`#`.
- Tee SHA-256 plus filename membership closes the immutability assumption. OTEL stays out (D-06).
- Absent-file short-circuit without `sqlite3.connect` is specified and mock-tested.

### Concerns

- **MEDIUM: Identity formula still disagrees with itself.** `key_links` (`05-02-PLAN.md:39`) says `raw_ref = f"opencode:{source_file}:{record_id}"`. Behavior (`05-02-PLAN.md:248-250`) and action (`05-02-PLAN.md:295`) say `f"opencode:{source_file}:{source_kind}:{record_id}"` specifically to stop part/message id collisions. An executor following `key_links` reintroduces the collision the Round 1 text exists to prevent.
- **LOW:** Session `raw_text = json.dumps(row dict)` is not verbatim DB text. The plan documents the exception; keep it labeled.

### Suggestions

- Make `key_links` use the 4-part `raw_ref` everywhere, and define `source_line` as `f"{source_kind}:{record_id}"` if you still want Wave 1's three-field template to hold.
- Do not parse `raw_ref` by splitting on `:`; `source_file` is an absolute path.

### Risk Assessment

**LOW.** Schema and capture scope are now live-correct. Fix the `raw_ref` string in `key_links` before execution so the executor has one formula.

## 05-03

### Summary

Codex recursive glob, opaque `arguments`, Cursor `source_confidence`/`session_id` as siblings, 2-step `CURSOR_CONFIG_DIR` path, AST `sqlite3` ban, and the REQUIREMENTS.md `store.db` amendment all address Cycle 1. Two Round 1 leftovers in the Codex task and the plan-level `<verification>` block would still ship the wrong envelope or fail the plan's own grep.

### Strengths

- Cursor payload is the parsed line; `source_confidence="low"` and `session_id` sit beside it. That matches 05-02's envelope-extension rule and feeds `refined_commands.source_confidence`.
- `timestamp=None` plus `source_line` order is an honest chronology fallback for a format with no clock field.
- Dropping the unverified `XDG_CONFIG_HOME` leg for session data follows `PROJECT.md`'s confidence rule. Config-file precedence in `04-RESEARCH.md` is a different concern.
- Task 2's AST `sqlite3` check is the right test: the docstring must name `store.db`/`blobs`.
- `git ls-files skills/ai-kit-usage-metrics` is empty, as the earlier plans claim. Codex/Cursor modules are still new files.

### Concerns

- **HIGH: Task 1 action still says Codex uses "Wave 1's exact 4-key-plus-payload contract"** (`05-03-PLAN.md:209-210`). Wave 1 Round 1 is an 8-key envelope (`raw_ref`, `captured_at`, `runtime`, `source_file`, `source_line`, `parse_status`, `raw_text`, `payload`). Task 2 already uses the 8-key contract. If the executor follows Task 1's action, Codex lines lose `parse_status`/`raw_text` and break every later consumer.
- **HIGH: Plan-level `<verification>` (`05-03-PLAN.md:444-447`) still says grep that `capture_cursor.py` never references `sqlite3`/`store.db`/`blobs`.** That is Cycle 1's impossible test, left in place after Task 2 switched to AST. The required docstring contains `store.db`/`blobs`, so this grep cannot pass.
- **MEDIUM: Task 1 action still says "malformed-line skip-and-count discipline"** (`05-03-PLAN.md:206`). After Round 1, Claude capture does not skip malformed lines. "Skip" vs "capture with `parse_status=malformed`" is the losslessness bug Cycle 1 already flagged.
- **LOW:** Plan-level verification wants ≥37 tests; Task 2 acceptance wants ≥40 (`05-03-PLAN.md:404-405` vs `:445-446`).

### Suggestions

- Rewrite Task 1 action to the 8-key envelope and "malformed line still captured, never skipped."
- Replace the plan-level `store.db`/`blobs` grep with the same AST `sqlite3` check Task 2 already specifies.
- Align the 37 vs 40 test floor.

### Risk Assessment

**MEDIUM.** Cursor's contract is now executable. Codex Task 1 action is stale enough that a literal implementation would violate the envelope 05-04 depends on.

## 05-04

### Summary

The decomposer, cwd machine, 3-value `command_shape`, turn-level tokens, rtk column split, and opencode `workdir` rebase close Cycle 1's classification and accounting HIGHs in this plan. The remaining hole is that 05-04 orders 05-05 to `SELECT DISTINCT session_id, turn_id, ...` before summing (`05-04-PLAN.md:35`), and 05-05's `groupBySession` still does a raw per-row sum. One `read_first` paragraph still demands the retired 4th `command_shape` value.

### Strengths

- `has_unsupported_shape` for `||`, heredocs, `$(`, backticks, and leading `(` makes `a || b` unclassified instead of `simple`. Cycle 1's internal contradiction is gone from behavior/acceptance.
- Control-flow closers now include `until`/`select` → `done`, with a nesting depth counter and token-boundary matching. Nested `for`/`if` test is specified.
- `command_shape` is `simple | control_flow_script | unclassified`; compound is `step_count > 1`. Grep gates forbid `compound_decomposed` in `decomposer.py` and `refiner.py`.
- `CwdState` resolve-then-observe, no `os.path.exists`, reproduces both PRD cwd examples. Live opencode `workdir` rebase-before-observe is specified, including a subsequent-record regression test.
- rtk history → `rtk_*` columns, `tokens_input`/`tokens_output` stay `None`. Cursor tokens/price stay `None`. Codex uses incremental `token_count` deltas. Catalog still absent on disk, so price tests correctly target the degrade path.
- `json.loads(arguments)` for Codex is isolated with `JSONDecodeError` → skip that record (T-05-12).

### Concerns

- **HIGH (cross-plan, originates here): Token/price figures are duplicated onto every step row sharing a `turn_id`** (`05-04-PLAN.md:35, 550-551`). The plan says 05-05 must dedup before summing. 05-05 does not (see 05-05 below). Cycle 1's overcount is moved, not removed.
- **MEDIUM:** Task 1 `<read_first>` still tells the executor to emit four `command_shape` values including `compound_decomposed` (`05-04-PLAN.md:159-163`). Behavior, acceptance, and the grep verify all forbid that literal. First-read vs later-read conflict.
- **MEDIUM:** Action prose says Cursor `working_directory` updates `CwdState` (`05-04-PLAN.md:621-623`), but `RESOLVE_CWD` rebase is opencode-only (`05-04-PLAN.md:513-518, 627-638`). A Cursor `Shell` with `working_directory` still resolves against `"unknown"` unless a `cd` appears. Same "authoritative per-call cwd" principle as opencode, not applied.
- **LOW:** Task 2's test floor stays 56, same as Task 1, even though Task 2 adds `TestCwdState`. Harmless; the floor does not prove Task 2 landed.

### Suggestions

- Delete `compound_decomposed` from `<read_first>`. Point at the 3-value enum and `step_count`.
- Give Cursor (and Codex `workdir` if present on `exec_command`) the same rebase-then-observe path as opencode, or strike the sentence that claims `working_directory` updates state.
- Specify `groupBySession` in 05-05 as distinct-on-`turn_id` for tokens/price, count-of-rows for invocations.

### Risk Assessment

**MEDIUM.** Refiner contracts are now coherent. Dashboard totals will still lie unless 05-05 consumes `turn_id` as this plan requires.

## 05-05

### Summary

Wave 6 + `depends_on: ["05-04", "05-06"]` removes the SKILL.md race. Five-axis filter+sort, `node`-executed pure JS, `createElement`/`textContent`, inferred-family labeling, readonly connection, and AST import scan all address Cycle 1. The Round 1 token-dedup rule was never written into `groupBySession`. `grep -c innerHTML` must be 0, so even a comment saying "do not use innerHTML" fails the gate.

### Strengths

- Every MVP axis now has both a filter control and a sortable header, including command-text substring and token/price ranges (`05-05-PLAN.md:153-174`). That matches `docs/prds/ai-kit-usage-metrics-dashboard-v1.0-prd.md` MVP axes.
- `test_shipped_js_canonical_query_via_node` runs the shipped `filterRows`/`sortRows`/`groupBySession`, and `skipTest`s if `node` is missing. `node` is on this machine (`/home/linuxbrew/.linuxbrew/bin/node`), so that test can actually run here.
- `dashboard.generate` takes an already-open conn; 05-01 already added `open_refined_db_readonly`. The readonly test is real.
- `displayFamily` plus a Cursor `source_confidence` badge implements `PROJECT.md:121-125`.
- Sole final `SKILL.md` editor after 05-06, then `skill-judge`, then `make test && make lint && make validate`. That closes Cycle 1's quality-gate bypass.
- No usage-metrics package exists yet (`git ls-files` empty), so this remains an edit of Wave 1's `dashboard.py`, not a greenfield rewrite.

### Concerns

- **HIGH: `groupBySession` still "sum of `tokens_input`/`tokens_output`, sum of `price`" per `session_id`** (`05-05-PLAN.md:170-173`). 05-04 Round 1 (`05-04-PLAN.md:35`) requires `SELECT DISTINCT session_id, turn_id, tokens_input, tokens_output, price` before any sum, and says 05-05 exercises that rule. It does not. A turn with `cd src && rg TODO` writes the same token/price on two rows; grouped session totals double-count. Token min/max filters have the same bias.
- **MEDIUM:** T-05-17 says the dashboard can distinguish `execution_certain=False` (`&&`-gated) steps. 05-05 never renders that column. Conditional steps still look like confirmed invocations.
- **MEDIUM:** `<verify>` `grep -c "innerHTML"` must be exactly 0 (`05-05-PLAN.md` Task 1 verify). A comment or docstring mentioning the ban fails the gate. The rule should be "no `innerHTML` assignment," not "the substring never appears."
- **MEDIUM (deferred, still true):** No browser/DOM test of click wiring. Honest skip; the `<human-check>` is the remaining coverage.

### Suggestions

- Dedup token/price by `turn_id` inside `groupBySession` (and in any token/price totals). Keep invocation counts as row counts; those are per-command.
- Render `execution_certain` (badge or filter). Do not present `&&` steps as confirmed.
- Change the innerHTML verify to a regex for assignment, or allow the word in comments.
- Fold 05-06's classify-then-dashboard sequence into `SKILL.md` before `skill-judge`, as specified.

### Risk Assessment

**MEDIUM.** UI completeness is specified. Session token/price totals will be wrong on compound commands until grouping respects `turn_id`.

## 05-06

### Summary

Wave 5 with no `SKILL.md` edits, reset-then-remine, a skeleton that can actually equate the two PRD loops, curated-member set lookup, and one SQLite transaction close Cycle 1. Remaining items are small. This plan should not close the phase; 05-05 does.

### Strengths

- `files_modified` no longer lists `SKILL.md`. Task 2 forbids editing it. `<verify>` greps `git diff --name-only HEAD` for that path. Cycle 1's same-wave race is gone.
- `normalize_skeleton` 4-step walk can reduce `for f in *.py; do rg pattern "$f"; done` and `for x in *.md; do rg other "$x"; done` to the same skeleton. Dedicated test runs before end-to-end classify.
- Candidate detection uses the flat curated set from `tools/hooks/detect.py:23-29` (`cat`/`bat`/`grep`/`rg`/…). Literal `grep` is no longer rejected. Dedicated regression test.
- `BEGIN` / reset all eligible rows / remine / `commit`, `rollback` on failure. Stale-annotation test (low then high threshold → `NULL`) is specified. `update_inferred_family` does not commit.
- `classify` is not in `run`. Trigger wording and `classify` then `dashboard` sequence go in `05-06-SUMMARY.md` for 05-05 to publish.
- `DEFAULT_MIN_OCCURRENCES = 2` is labeled a placeholder, not a researched constant.

### Concerns

- **LOW:** Placeholder tokens `<STR>` after step 2 could be rewritten to `<ARG>` in step 4 unless the walk skips existing placeholders. Both PRD examples still match either way; pin "do not rewrite `<VAR>`/`<STR>`/`<ARG>`" so the documented skeleton string stays stable.
- **LOW:** Ambiguous-group test (two tool tokens → no inference) is specified; keep it. A `for` body with `rg` and `fd` must not guess.

### Suggestions

- State that placeholder tokens are terminal.
- Keep `run` as capture → refine → dashboard only.

### Risk Assessment

**LOW.** Cycle 1 HIGHs for this plan are addressed. Execute in Wave 5; let 05-05 publish docs and run repo gates.

## Cross-plan (OpenCode's own, Cycle 2)

Round 1 HIGHs are mostly incorporated. What is still blocking is leftover text, not missing architecture.

| Cycle 1 theme | Status |
|---|---|
| 05-01 lossless / idempotent / permissions | Fixed |
| 05-02 TEXT PK + session/message/part + storage/ | Fixed (live-reverified) |
| 05-03 Cursor identity, confidence, AST vs grep | Task 2 fixed; plan-level `<verification>` still has the old `store.db` grep |
| 05-04 scanner / shape / rtk columns / workdir rebase | Fixed in 05-04; `read_first` still cites 4 shapes |
| Token overcount | Stored once per `turn_id`, then summed per row in 05-05 |
| 05-05/05-06 SKILL.md race | Fixed (Wave 6 after Wave 5) |
| `PROJECT.md:76-78` "dashboard Artifact… local export" | Still stale (Cycle 1 consensus, not amended in `19131c2`) |

**Fix before execute:** (1) 05-03 Codex 8-key envelope + drop plan-level `store.db` grep, (2) 05-05 `groupBySession` distinct-on-`turn_id` for tokens/price, (3) 05-02/05-04 leftover formula/enum strings. Then overall risk is **LOW**. As written, overall risk is **MEDIUM**.

---

## Consensus Summary

Only one reviewer (OpenCode, model `xai/grok-4.6`, reasoning=high) ran Cycle 2 — no cross-reviewer corroboration is possible, so every finding below is single-reviewer. The reviewer re-verified live schema/tooling facts (opencode `part`/`message`/`session` TEXT PKs, `rtk` INTEGER PKs, `node` binary presence) rather than taking Cycle 1's or the plans' word for them, so this review counts as source-grounded (no `[reviewed-without-source-citations]` or `[reviewed-without-repo-access]` marker applies).

### Agreed Strengths
N/A — single reviewer this cycle; see OpenCode's per-plan Strengths sections above. Headline: all of Cycle 1's HIGH findings for 05-01, 05-02, 05-05/05-06 wave-race, and most of 05-04 are now closed with testable contracts, live-reverified against the actual repo and installed databases.

### Agreed Concerns
N/A — single reviewer this cycle; see OpenCode's per-plan Concerns sections above. Remaining HIGH findings this cycle:
- 05-03: Task 1's Codex capture action still describes the retired 4-key envelope (contradicts Task 2's 8-key contract) and the plan-level `<verification>` still greps for the old (now-impossible) `store.db`/`blobs`-absence condition.
- 05-04/05-05 (cross-plan): 05-04 requires `SELECT DISTINCT session_id, turn_id, ...` before summing tokens/price; 05-05's `groupBySession` still sums per-row, so compound commands sharing a `turn_id` double-count tokens and price in session totals.

### Divergent Views
N/A — single reviewer this cycle.

---

## Cycle 3 (2026-09-10T09:22:47Z)

Reviews the plans as revised in commit `116fb31` to address Cycle 2's 3 HIGH + 12 MEDIUM/LOW findings above. Reviewer: OpenCode, model `xai/grok-4.6`, reasoning=high.

## OpenCode Review

Cycle 3 review of the six Phase 05 plans against repo source and commit `116fb31`. Cycle 2's 3 HIGH + 12 MEDIUM/LOW findings in `116fb31` are closed. One new HIGH remains in 05-04.

## 05-01

**Summary.** Tracer is executable against real repo patterns: XDG/`CLAUDE_CONFIG_DIR` matching `tools/setup.py:57`, curated pairs matching `tools/hooks/detect.py:23-29`, `canonical_key` at `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py:46-50`, catalog absent on disk. Round 2 nits (14-test floor, `refine`→`refine_all` handoff) are in the text.

**Strengths**
- `write_preserving_mode` in `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/atomic_write.py:41` does `os.stat(target)` with no missing-file path. The plan's `FileNotFoundError` → `0600` fallback is required.
- Gate edits match live files: `Makefile:34` unittest list, `Makefile:37-39` `py_compile`, `.pre-commit-config.yaml:21,48,53`, `pyproject.toml:93`.
- `tests/test_ai_kit_opencode_providers.py:14-17` is the `sys.path.insert` shape to copy. `git ls-files skills/ai-kit-usage-metrics` is empty.

**Concerns**
- **MEDIUM:** Envelope contract vs `queue-operation`. `05-01-PLAN.md:53,189` say `payload` is set only when `parse_status=="ok"`, else `None`. Behavior at `05-01-PLAN.md:198-200` keeps the parsed dict for `recognized_no_data`. Tests never assert which.
- **LOW:** Port atomic write from `tools/config_doctor_appliers.py:121-122` (`existed = os.path.isfile(target)`) rather than wrapping `atomic_write.py:41`. Same contract, already in-tree.

**Suggestions**
- One rule: `recognized_no_data` keeps `payload` (parsed, no command data); only `malformed` uses `payload=None`.
- Port `_atomic_write_text`'s existed-check.

**Risk:** **LOW.** Cycle 2 leftovers are gone. Payload rule is the only executor fork.

## 05-02

**Summary.** Live schema still matches: `part.id` is `TEXT` PK, `time_created` is `INTEGER`; rtk `commands.id` is `INTEGER` PK. Round 2 4-part `raw_ref` is in `05-02-PLAN.md:39`. `urllib.parse.quote` default `safe='/'` (verified) leaves slashes; `?`/`#` still encode.

**Strengths**
- `(time_created, id)` cursor matches installed `PRAGMA table_info(part)`.
- `session`/`message`/`part` plus top-level `session_id`/`message_id` give 05-04 join keys.
- `mode=ro` + `quote(path)` is the right external-DB boundary. Tee SHA-256 + filename membership is specified. OTEL stays out.

**Concerns**
- **LOW:** `storage/**/*.json` needs `glob(..., recursive=True)` or `pathlib.rglob`. Bare `glob.glob` will not recurse.
- **LOW:** Session `raw_text = json.dumps(row)` is not verbatim DB text. The plan already labels this.

**Suggestions**
- Name `recursive=True` in Task 1. Do not parse `raw_ref` by splitting on `:`; `source_file` is an absolute path (`05-02-PLAN.md:39`).

**Risk:** **LOW.** Cycle 2 identity formula is closed.

## 05-03

**Summary.** Both Cycle 2 HIGHs are closed in the file: Task 1 action names the 8-key envelope (`05-03-PLAN.md:215-221`); plan-level `<verification>` uses the AST `sqlite3` scan (`05-03-PLAN.md:460-468`). Malformed lines are captured, not skipped (`:192-195`, `:209-212`). Test floor is 40.

**Strengths**
- Cursor `source_confidence="low"` and `session_id` are envelope siblings; `payload` is the parsed line. 2-step `CURSOR_CONFIG_DIR` then `$HOME/.cursor` is documented as a deliberate drop of the unverified XDG leg.
- `store.db` exclusion plus REQUIREMENTS.md amendment matches `PROJECT.md`'s confidence rule. AST check allows the docstring to name `store.db`/`blobs`.
- Catalog still absent; Codex `arguments` stay a string.

**Concerns**
- **MEDIUM (feeds 05-04):** Codex envelopes are the 8-key set only — no `session_id` sibling. `session_id` lives in `session_meta` payload (`05-03-PLAN.md` live facts). 05-04 groups by `(runtime, session_id)`.
- **LOW:** `timestamp=None` on Cursor is honest if transcripts have no clock field; 05-04 must sort those files by `source_line`.

**Suggestions**
- Stamp `session_id` from the nearest `session_meta` onto every Codex envelope (same pattern as Cursor's uuid-from-path), or state that 05-04 groups Codex by `source_file`.

**Risk:** **LOW** for this plan. Remaining session-id gap is 05-04's to consume.

## 05-04

**Summary.** Decomposer, 3-value `command_shape`, turn-level tokens, rtk column split, and opencode `workdir` rebase still hold. Cycle 2 leftovers (`compound_decomposed` in `<read_first>`, Cursor `working_directory` "updates" state, test floor 56) are closed (`05-04-PLAN.md:159-167`, `:633-641`, Task 2 floor 60). One new chronology bug will make the PRD's cross-call cwd example wrong for opencode.

**Strengths**
- `has_unsupported_shape` for `||` / heredoc / `$(` / backtick / leading `(`; closers include `until`/`select`; nested `for`/`if` test is specified. Grep gates forbid `compound_decomposed`.
- `CwdState` resolve-then-observe, no `os.path.exists`. Opencode rebase-before-observe plus subsequent-record test.
- rtk → `rtk_*` columns; Cursor tokens/price stay `None`. Price tests target the degrade path (catalog absent).

**Concerns**
- **HIGH:** Chronological walk sorts by envelope `timestamp`, then `source_line` (`05-04-PLAN.md:508-512`). Opencode envelopes carry `time_created`, not `timestamp` (`05-02-PLAN.md:39`). Fallback `source_line` is the TEXT `record_id`. Installed `part.id` is a TEXT PK, not insertion order. `CwdState` would walk UUID order. Must-have `:28` (later `grep` reuses prior `cd`) fails for opencode, the runtime that needs the state machine (D-05).
- **MEDIUM:** `source_confidence` is never written onto refined rows (`05-04-PLAN.md:513-532` lists family, operator, cwd, turn_id — not this column). Wave 1 hardcodes `"high"` (`05-01-PLAN.md:299`). Cycle 1's "Cursor confidence dropped before the dashboard" returns at refine unless 05-04 copies the envelope field. 05-03 `:28` requires it to reach `refined_commands.source_confidence`.
- **MEDIUM:** Claude `_native_cwd_resolver` applies the pre-command message `cwd` to every decomposed step (`:32`, `:521-522`). Must-have `:27` wants `cd src && grep`'s grep step resolved to `src`. That needs an intra-record `CwdState` seeded from native cwd, without carrying it to the next tool-call (Claude Bash does not persist `cd`).
- **MEDIUM:** T-05-12 claims a dedicated malformed-`arguments` test. Task 3's test list does not include one.
- **MEDIUM:** Codex grouping by `session_id` has no envelope field to read (05-03). Token-delta and `session_meta.cwd` need a stated grouping key (`source_file` or stamped `session_id`).
- **LOW:** Unquoted background `&` is not an operator; Wave 1 excluded any `&`, Wave 4 may tag those commands `simple`.

**Suggestions**
- Sort opencode (and any epoch-ms source) by `time_created`, then `record_id`. Do not use TEXT ids as a time axis.
- Set `source_confidence = envelope.get("source_confidence") or "high"` on every refined row; assert Cursor rows are `"low"`.
- Claude: per-record `CwdState` seeded from native `cwd`, discarded after that record's steps. Other runtimes keep the session-long machine.
- Add the malformed-`arguments` test T-05-12 already names.
- Group Codex by rollout `source_file`, or stamp `session_id` in 05-03.

**Risk:** **MEDIUM.** Cross-call cwd for opencode is wrong as specified. Dashboard Cursor badge is empty unless refine copies `source_confidence`.

## 05-05

**Summary.** Cycle 2 HIGH (`groupBySession` per-row sum) is closed at `05-05-PLAN.md:49` with `(session_id, turn_id)` dedup, Python + `node` tests. `execution_certain` marker and `.innerHTML[[:space:]]*=` grep are in the file (`:50`, Task 1 `<verify>`). Wave 6 after 05-06 removes the SKILL.md race.

**Strengths**
- All 5 axes have filter + sortable header. `node` is at `/home/linuxbrew/.linuxbrew/bin/node`; `skipTest` if absent.
- `createElement`/`textContent` only. `displayFamily` vs inferred vs Cursor `source_confidence`. Readonly conn from 05-01. AST import scan, not a string grep.
- Sole final `SKILL.md` editor; `skill-judge` then `make test && make lint && make validate`.

**Concerns**
- **MEDIUM:** Dashboard rendering of `source_confidence` is specified; 05-04 never populates the column. The badge test can pass on a hand-seeded DB and still fail on real `run` output.
- **LOW:** `PROJECT.md:76-78` still says "dashboard Artifact" / "local export". `REQUIREMENTS.md:43` and `ROADMAP.md:155` were amended (D-10). `.planning/intel/requirements.md:151-158` is still the old Artifact/export text. Not this plan's file list, but AGENTS.md treats intel as requirement detail.
- **LOW (deferred, still true):** No browser/DOM click test. `<human-check>` is the remaining coverage.

**Suggestions**
- Seed the Cursor-row dashboard test the same way `refine_all` will write `source_confidence`, or add an end-to-end capture→refine→dashboard case.
- Amend `PROJECT.md:76-78` and intel dashboard bullets in 05-03's REQUIREMENTS pass, or a one-line 05-05 docs fix.

**Risk:** **LOW** for this plan's own text. Depends on 05-04 writing `source_confidence`.

## 05-06

**Summary.** Cycle 2 LOWs are closed: step (4) skips existing `<VAR>`/`<STR>`/`<ARG>` (`05-06-PLAN.md` key_links/behavior/action) with `test_normalize_skeleton_does_not_rewrite_existing_placeholders`; ambiguous-group test was already specified. No `SKILL.md` edits. Wave 5, then 05-05 publishes.

**Strengths**
- 4-step skeleton can equate the two PRD `for`/`rg` loops. Curated-member set from `tools/hooks/detect.py:23-29` recognizes literal `grep`. Reset-then-remine in one `BEGIN`/`commit`. Stale-annotation test. `classify` is not in `run`.
- `DEFAULT_MIN_OCCURRENCES = 2` is labeled a placeholder. `classify` then `dashboard` sequence goes in `05-06-SUMMARY.md`.

**Concerns**
- **LOW:** `git diff --name-only HEAD` SKILL.md check fails if 05-01–05-03 SKILL.md edits are still uncommitted. Fine if GSD commits per plan.
- **LOW:** `infer_family_for_group` scans original command tokens, not the skeleton. That is what you want for `rg`/`grep`; keep the test on the original text.

**Suggestions**
- Keep `run` as capture → refine → dashboard only.
- Pin the exact skeleton string `for <VAR> in <ARG>; do rg <ARG> <STR>; done` (already in the new test).

**Risk:** **LOW.** Cycle 1/2 HIGHs for this plan stay closed.

## Cross-plan (OpenCode's own, Cycle 3)

**Cycle 2 closure (`116fb31` vs `8ce88ae`)**

| Cycle 2 finding | Status in `116fb31` |
|---|---|
| 05-03 4-key Codex envelope (HIGH) | Closed — `05-03-PLAN.md:215-221` |
| 05-03 `store.db` grep (HIGH) | Closed — AST scan `:460-468` |
| 05-04/05-05 `groupBySession` double-count (HIGH) | Closed — `05-05-PLAN.md:49` + tests |
| 05-02 3-part `raw_ref` (MEDIUM) | Closed — `05-02-PLAN.md:39` |
| 05-03 skip-and-count (MEDIUM) | Closed — `:192-195`, `:209-212` |
| 05-04 `compound_decomposed` in `<read_first>` (MEDIUM) | Closed — `:159-167` |
| 05-04 Cursor `working_directory` (MEDIUM) | Closed — retracted `:633-641` |
| 05-05 `execution_certain` (MEDIUM) | Closed — `:50` |
| 05-05 `innerHTML` grep (MEDIUM) | Closed — `.innerHTML[[:space:]]*=` |
| Six LOWs (test floors, refine handoff, placeholder rewrite, ambiguous-group) | Closed or confirmed already specified |

**New Cycle 3 HIGH:** 05-04 sorts opencode by missing `timestamp` then TEXT `record_id`. Live `part.id` is TEXT; `time_created` is the time axis 05-02 already captures. Cross-call cwd (ROADMAP SC-2) is wrong for opencode until the sort key is `time_created`.

**New MEDIUMs:** (1) `source_confidence` not copied in 05-04, so 05-05's Cursor badge is ungrounded on real data; (2) Claude intra-record compound cwd vs native per-message cwd; (3) 05-01 `payload` for `recognized_no_data`; (4) T-05-12 test missing from Task 3; (5) Codex session identity not on the envelope.

**Live rechecks (this cycle):** opencode `part.id TEXT` PK; rtk `commands.id INTEGER` PK; `node` present; usage-metrics tree untracked; model catalog absent; `quote()` `safe='/'` default.

**Overall risk:** **MEDIUM** until 05-04 sorts opencode by `time_created` and writes `source_confidence`. After those two edits, **LOW**. Do not execute 05-04 as written.

---

### Cycle 3 Consensus Summary

Only one reviewer (OpenCode, model `xai/grok-4.6`, reasoning=high) ran Cycle 3 — no cross-reviewer corroboration is possible, so every finding below is single-reviewer. The reviewer re-verified live schema/tooling facts (opencode `part.id` TEXT PK, rtk `commands.id` INTEGER PK, `node` binary presence, `urllib.parse.quote` default `safe='/'`) rather than taking the plans' word for them, so this review counts as source-grounded (no `[reviewed-without-source-citations]` or `[reviewed-without-repo-access]` marker applies).

**CYCLE_SUMMARY: current_high=1 current_actionable=16**

### Agreed Strengths
N/A — single reviewer this cycle. Headline: all 3 HIGH + 12 MEDIUM/LOW findings from Cycle 2 are closed in commit `116fb31`, live-reverified against the actual repo and installed databases.

### Current HIGH Concerns
- **05-04 (`05-04-PLAN.md:508-512`):** The chronological walk sorts envelopes by `timestamp` then `source_line`, but opencode envelopes carry `time_created` (`05-02-PLAN.md:39`), not `timestamp`. The `source_line` fallback is the TEXT `record_id`, and the installed `part` table's `id` is a TEXT primary key — not insertion order — so sorting by it does not recover chronology. `CwdState` would walk UUID order instead of time order. This breaks the phase's own must-have (`05-04-PLAN.md:28`, later `grep` reusing a prior `cd`) specifically for opencode, the runtime the cwd-resolution state machine exists to serve (ROADMAP D-05/SC-2). Fix: sort opencode (and any epoch-ms source) by `time_created`, then `record_id`.

### Current Actionable MEDIUM/LOW Concerns
**MEDIUM (7):**
- 05-01: Envelope contract vs `queue-operation` — `05-01-PLAN.md:53,189` say `payload` is `None` unless `parse_status=="ok"`, but behavior at `:198-200` keeps the parsed dict for `recognized_no_data`; no test asserts which rule holds.
- 05-03 (feeds 05-04): Codex envelopes are the 8-key set only, with no `session_id` sibling — `session_id` lives only in the `session_meta` payload, but 05-04 groups by `(runtime, session_id)`.
- 05-04: `source_confidence` is never written onto refined rows (`05-04-PLAN.md:513-532` lists family/operator/cwd/turn_id, not this column); Wave 1 hardcodes `"high"` (`05-01-PLAN.md:299`), so Cycle 1's "Cursor confidence dropped before the dashboard" regresses at refine time unless the envelope field is copied through.
- 05-04: Claude's `_native_cwd_resolver` applies the pre-command message `cwd` to every decomposed step (`:32`, `:521-522`), but the must-have at `:27` wants an intra-record `CwdState` seeded from native cwd that is discarded after that record (Claude Bash does not persist `cd` across tool-calls).
- 05-04: T-05-12 claims a dedicated malformed-`arguments` test, but Task 3's test list does not include one.
- 05-04: Codex grouping by `session_id` has no envelope field to read per 05-03's finding above; token-delta and `session_meta.cwd` need a stated grouping key (`source_file` or a stamped `session_id`).
- 05-05: Dashboard rendering of `source_confidence` is specified, but 05-04 never populates the column, so the badge test can pass on a hand-seeded DB and still fail against real `run` output.

**LOW (9):**
- 05-01: Port the atomic-write existed-check from `tools/config_doctor_appliers.py:121-122` rather than wrapping `atomic_write.py:41`, which has no missing-file path.
- 05-02: `storage/**/*.json` needs `glob(..., recursive=True)` or `pathlib.rglob` — bare `glob.glob` will not recurse.
- 05-02: Session `raw_text = json.dumps(row)` is not verbatim DB text (the plan already labels this).
- 05-03: `timestamp=None` on Cursor is honest given no clock field in transcripts, but 05-04 must sort those files by `source_line` as a result.
- 05-04: Unquoted background `&` is not an operator; Wave 1 excluded any `&`, Wave 4 may tag those commands `simple`.
- 05-05: `PROJECT.md:76-78` still says "dashboard Artifact"/"local export" — `REQUIREMENTS.md:43` and `ROADMAP.md:155` were amended (D-10) but `.planning/intel/requirements.md:151-158` still has the old Artifact/export text.
- 05-05 (deferred, still true): No browser/DOM click test — `<human-check>` remains the coverage for that gap.
- 05-06: `git diff --name-only HEAD` SKILL.md check fails if 05-01–05-03's SKILL.md edits are still uncommitted (fine if GSD commits per plan).
- 05-06: `infer_family_for_group` scans original command tokens, not the skeleton — correct for `rg`/`grep`, keep the test on the original text.

### Divergent Views
N/A — single reviewer this cycle.
</content>
