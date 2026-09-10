I'll load the plan-review skills and Cycle 1 findings first, then verify each plan against the repo.
Using gsd-review as the reviewer, not the orchestrator. Next I’ll locate the phase files and ground each plan against the repo.
Cycle 1 is on disk; next I’ll ground the Round 1 fixes against the code and hunt leftover contradictions.
Using gsd-review against the revised plans (commit `19131c2`) and the live repo.

## 05-01

### Summary

Round 1’s blocking gaps are closed in the plan text. The tracer now has a real identity (`raw_ref`), lossless envelopes, UPSERT, crash-safe append, `0700`/`0600` modes, and `CaptureResult`. Grounded against this repo, the cited patterns are real: `CURATED_SUBSTITUTIONS` at `tools/hooks/detect.py:23-29`, `catalog_path` at `skills/ai-kit-opencode-providers/ai_kit_opencode_providers/config_paths.py:41-47`, and `write_preserving_mode` at `atomic_write.py:40-41` still does an unguarded `os.stat(target)` — the new `FileNotFoundError` branch is required. Residual issues are small (test-count wording, catalog still absent on disk).

### Strengths

- `UNIQUE(raw_ref, step_index)` plus `ON CONFLICT ... DO UPDATE` excluding `inferred_family`/`inferred_confidence` makes the second-`run` row-count claim implementable (`05-01-PLAN.md` key_links / `insert_commands` behavior).
- Every JSONL line becomes an envelope with `raw_text` and `parse_status` (`ok` / `malformed` / `recognized_no_data`). That matches `REQ-usage-metrics-raw-capture` at `.planning/REQUIREMENTS.md:41`.
- `append_records` dedupes on the target file’s own `raw_ref` set, so a crash between append and cursor write cannot duplicate lines.
- Mode `0700`/`0600` with an umask test is a real mitigation, not an ambient-permission hope. `atomic_write.py:41` still assumes the destination exists; the plan names that bug and adds the missing branch.
- `CAPTURE_SOURCES = {"claude": ...}` matches Config Doctor’s registry taste (`tools/config_doctor_checks.py:566`). Gate edits target the real surfaces: `Makefile:33-39`, `.pre-commit-config.yaml:21,48,53`, `pyproject.toml:93`.
- Live check: no `model-catalog.json` on this machine. The `(None, "unknown")` price degrade is the correct path, not a fake dollar figure.

### Concerns

- **LOW:** Task 2 says “Task 1’s 10+” tests while Task 1’s floor is 14 (`05-01-PLAN.md` Task 1 acceptance vs Task 2 acceptance). The floors still work; the comment is wrong.
- **LOW:** `cli.py` `refine` this wave reads only `raw/claude.jsonl`. Intended, but 05-04 must actually switch the entry point to `refine_all` or later sources never refine.

### Suggestions

- Align the Task 2 “10+” sentence with Task 1’s 14-test floor.
- Keep `open_refined_db_readonly` in Wave 1 as specified; 05-05 depends on it.

### Risk Assessment

**LOW.** Cycle 1 HIGHs for this plan are addressed with testable contracts. Safe to execute after the leftover comment nit.

---

## 05-02

### Summary

The TEXT-PK cursor rewrite and the session/message/part + `storage/` capture match the installed databases. I re-checked live: `part.id` / `message.id` / `session.id` are `TEXT` primary keys with `time_created INTEGER`; `rtk` `commands.id` / `parse_failures.id` are `INTEGER` primary keys. Cycle 1’s schema error is gone. One leftover identity formula in `key_links` disagrees with behavior/action.

### Strengths

- `(time_created, id)` tuple cursor is the right model for TEXT PKs. Same-timestamp two-id test actually exercises that, not `time_created > cursor`.
- Top-level `session_id` / `message_id` / `time_created` / `record_id` give 05-04 join keys. Cycle 1’s “05-04 cannot correlate opencode” finding is fixed here.
- `mode=ro` plus `urllib.parse.quote` is the right external-DB boundary. Python’s `quote()` default `safe='/'` leaves slashes intact and still escapes `?`/`#`.
- Tee SHA-256 plus filename membership closes the immutability assumption. OTEL stays out (D-06).
- Absent-file short-circuit without `sqlite3.connect` is specified and mock-tested.

### Concerns

- **MEDIUM:** Identity formula still disagrees with itself. `key_links` (`05-02-PLAN.md:39`) says `raw_ref = f"opencode:{source_file}:{record_id}"`. Behavior (`05-02-PLAN.md:248-250`) and action (`05-02-PLAN.md:295`) say `f"opencode:{source_file}:{source_kind}:{record_id}"` specifically to stop part/message id collisions. An executor following `key_links` reintroduces the collision the Round 1 text exists to prevent.
- **LOW:** Session `raw_text = json.dumps(row dict)` is not verbatim DB text. The plan documents the exception; keep it labeled.

### Suggestions

- Make `key_links` use the 4-part `raw_ref` everywhere, and define `source_line` as `f"{source_kind}:{record_id}"` if you still want Wave 1’s three-field template to hold.
- Do not parse `raw_ref` by splitting on `:`; `source_file` is an absolute path.

### Risk Assessment

**LOW.** Schema and capture scope are now live-correct. Fix the `raw_ref` string in `key_links` before execution so the executor has one formula.

---

## 05-03

### Summary

Codex recursive glob, opaque `arguments`, Cursor `source_confidence`/`session_id` as siblings, 2-step `CURSOR_CONFIG_DIR` path, AST `sqlite3` ban, and the REQUIREMENTS.md `store.db` amendment all address Cycle 1. Two Round 1 leftovers in the Codex task and the plan-level `<verification>` block would still ship the wrong envelope or fail the plan’s own grep.

### Strengths

- Cursor payload is the parsed line; `source_confidence="low"` and `session_id` sit beside it. That matches 05-02’s envelope-extension rule and feeds `refined_commands.source_confidence`.
- `timestamp=None` plus `source_line` order is an honest chronology fallback for a format with no clock field.
- Dropping the unverified `XDG_CONFIG_HOME` leg for session data follows `PROJECT.md`’s confidence rule. Config-file precedence in `04-RESEARCH.md` is a different concern.
- Task 2’s AST `sqlite3` check is the right test: the docstring must name `store.db`/`blobs`.
- `git ls-files skills/ai-kit-usage-metrics` is empty, as the earlier plans claim. Codex/Cursor modules are still new files.

### Concerns

- **HIGH:** Task 1 action still says Codex uses “Wave 1’s exact 4-key-plus-payload contract” (`05-03-PLAN.md:209-210`). Wave 1 Round 1 is an 8-key envelope (`raw_ref`, `captured_at`, `runtime`, `source_file`, `source_line`, `parse_status`, `raw_text`, `payload`). Task 2 already uses the 8-key contract. If the executor follows Task 1’s action, Codex lines lose `parse_status`/`raw_text` and break every later consumer.
- **HIGH:** Plan-level `<verification>` (`05-03-PLAN.md:444-447`) still says grep that `capture_cursor.py` never references `sqlite3`/`store.db`/`blobs`. That is Cycle 1’s impossible test, left in place after Task 2 switched to AST. The required docstring contains `store.db`/`blobs`, so this grep cannot pass.
- **MEDIUM:** Task 1 action still says “malformed-line skip-and-count discipline” (`05-03-PLAN.md:206`). After Round 1, Claude capture does not skip malformed lines. “Skip” vs “capture with `parse_status=malformed`” is the losslessness bug Cycle 1 already flagged.
- **LOW:** Plan-level verification wants ≥37 tests; Task 2 acceptance wants ≥40 (`05-03-PLAN.md:404-405` vs `:445-446`).

### Suggestions

- Rewrite Task 1 action to the 8-key envelope and “malformed line still captured, never skipped.”
- Replace the plan-level `store.db`/`blobs` grep with the same AST `sqlite3` check Task 2 already specifies.
- Align the 37 vs 40 test floor.

### Risk Assessment

**MEDIUM.** Cursor’s contract is now executable. Codex Task 1 action is stale enough that a literal implementation would violate the envelope 05-04 depends on.

---

## 05-04

### Summary

The decomposer, cwd machine, 3-value `command_shape`, turn-level tokens, rtk column split, and opencode `workdir` rebase close Cycle 1’s classification and accounting HIGHs in this plan. The remaining hole is that 05-04 orders 05-05 to `SELECT DISTINCT session_id, turn_id, ...` before summing (`05-04-PLAN.md:35`), and 05-05’s `groupBySession` still does a raw per-row sum. One `read_first` paragraph still demands the retired 4th `command_shape` value.

### Strengths

- `has_unsupported_shape` for `||`, heredocs, `$(`, backticks, and leading `(` makes `a || b` unclassified instead of `simple`. Cycle 1’s internal contradiction is gone from behavior/acceptance.
- Control-flow closers now include `until`/`select` → `done`, with a nesting depth counter and token-boundary matching. Nested `for`/`if` test is specified.
- `command_shape` is `simple | control_flow_script | unclassified`; compound is `step_count > 1`. Grep gates forbid `compound_decomposed` in `decomposer.py` and `refiner.py`.
- `CwdState` resolve-then-observe, no `os.path.exists`, reproduces both PRD cwd examples. Live opencode `workdir` rebase-before-observe is specified, including a subsequent-record regression test.
- rtk history → `rtk_*` columns, `tokens_input`/`tokens_output` stay `None`. Cursor tokens/price stay `None`. Codex uses incremental `token_count` deltas. Catalog still absent on disk, so price tests correctly target the degrade path.
- `json.loads(arguments)` for Codex is isolated with `JSONDecodeError` → skip that record (T-05-12).

### Concerns

- **HIGH (cross-plan, originates here):** Token/price figures are duplicated onto every step row sharing a `turn_id` (`05-04-PLAN.md:35, 550-551`). The plan says 05-05 must dedup before summing. 05-05 does not (see 05-05). Cycle 1’s overcount is moved, not removed.
- **MEDIUM:** Task 1 `<read_first>` still tells the executor to emit four `command_shape` values including `compound_decomposed` (`05-04-PLAN.md:159-163`). Behavior, acceptance, and the grep verify all forbid that literal. First-read vs later-read conflict.
- **MEDIUM:** Action prose says Cursor `working_directory` updates `CwdState` (`05-04-PLAN.md:621-623`), but `RESOLVE_CWD` rebase is opencode-only (`05-04-PLAN.md:513-518, 627-638`). A Cursor `Shell` with `working_directory` still resolves against `"unknown"` unless a `cd` appears. Same “authoritative per-call cwd” principle as opencode, not applied.
- **LOW:** Task 2’s test floor stays 56, same as Task 1, even though Task 2 adds `TestCwdState`. Harmless; the floor does not prove Task 2 landed.

### Suggestions

- Delete `compound_decomposed` from `<read_first>`. Point at the 3-value enum and `step_count`.
- Give Cursor (and Codex `workdir` if present on `exec_command`) the same rebase-then-observe path as opencode, or strike the sentence that claims `working_directory` updates state.
- Specify `groupBySession` in 05-05 as distinct-on-`turn_id` for tokens/price, count-of-rows for invocations.

### Risk Assessment

**MEDIUM.** Refiner contracts are now coherent. Dashboard totals will still lie unless 05-05 consumes `turn_id` as this plan requires.

---

## 05-05

### Summary

Wave 6 + `depends_on: ["05-04", "05-06"]` removes the SKILL.md race. Five-axis filter+sort, `node`-executed pure JS, `createElement`/`textContent`, inferred-family labeling, readonly connection, and AST import scan all address Cycle 1. The Round 1 token-dedup rule was never written into `groupBySession`. `grep -c innerHTML` must be 0, so even a comment saying “do not use innerHTML” fails the gate.

### Strengths

- Every MVP axis now has both a filter control and a sortable header, including command-text substring and token/price ranges (`05-05-PLAN.md:153-174`). That matches `docs/prds/ai-kit-usage-metrics-dashboard-v1.0-prd.md` MVP axes.
- `test_shipped_js_canonical_query_via_node` runs the shipped `filterRows`/`sortRows`/`groupBySession`, and `skipTest`s if `node` is missing. `node` is on this machine (`/home/linuxbrew/.linuxbrew/bin/node`), so that test can actually run here.
- `dashboard.generate` takes an already-open conn; 05-01 already added `open_refined_db_readonly`. The readonly test is real.
- `displayFamily` plus a Cursor `source_confidence` badge implements `PROJECT.md:121-125`.
- Sole final `SKILL.md` editor after 05-06, then `skill-judge`, then `make test && make lint && make validate`. That closes Cycle 1’s quality-gate bypass.
- No usage-metrics package exists yet (`git ls-files` empty), so this remains an edit of Wave 1’s `dashboard.py`, not a greenfield rewrite.

### Concerns

- **HIGH:** `groupBySession` still “sum of `tokens_input`/`tokens_output`, sum of `price`” per `session_id` (`05-05-PLAN.md:170-173`). 05-04 Round 1 (`05-04-PLAN.md:35`) requires `SELECT DISTINCT session_id, turn_id, tokens_input, tokens_output, price` before any sum, and says 05-05 exercises that rule. It does not. A turn with `cd src && rg TODO` writes the same token/price on two rows; grouped session totals double-count. Token min/max filters have the same bias.
- **MEDIUM:** T-05-17 says the dashboard can distinguish `execution_certain=False` (`&&`-gated) steps. 05-05 never renders that column. Conditional steps still look like confirmed invocations.
- **MEDIUM:** `<verify>` `grep -c "innerHTML"` must be exactly 0 (`05-05-PLAN.md` Task 1 verify). A comment or docstring mentioning the ban fails the gate. The rule should be “no `innerHTML` assignment,” not “the substring never appears.”
- **MEDIUM (deferred, still true):** No browser/DOM test of click wiring. Honest skip; the `<human-check>` is the remaining coverage.

### Suggestions

- Dedup token/price by `turn_id` inside `groupBySession` (and in any token/price totals). Keep invocation counts as row counts; those are per-command.
- Render `execution_certain` (badge or filter). Do not present `&&` steps as confirmed.
- Change the innerHTML verify to a regex for assignment, or allow the word in comments.
- Fold 05-06’s classify-then-dashboard sequence into `SKILL.md` before `skill-judge`, as specified.

### Risk Assessment

**MEDIUM.** UI completeness is specified. Session token/price totals will be wrong on compound commands until grouping respects `turn_id`.

---

## 05-06

### Summary

Wave 5 with no `SKILL.md` edits, reset-then-remine, a skeleton that can actually equate the two PRD loops, curated-member set lookup, and one SQLite transaction close Cycle 1. Remaining items are small. This plan should not close the phase; 05-05 does.

### Strengths

- `files_modified` no longer lists `SKILL.md`. Task 2 forbids editing it. `<verify>` greps `git diff --name-only HEAD` for that path. Cycle 1’s same-wave race is gone.
- `normalize_skeleton` 4-step walk can reduce `for f in *.py; do rg pattern "$f"; done` and `for x in *.md; do rg other "$x"; done` to the same skeleton. Dedicated test runs before end-to-end classify.
- Candidate detection uses the flat curated set from `tools/hooks/detect.py:23-29` (`cat`/`bat`/`grep`/`rg`/…). Literal `grep` is no longer rejected. Dedicated regression test.
- `BEGIN` / reset all eligible rows / remine / `commit`, `rollback` on failure. Stale-annotation test (low then high threshold → `NULL`) is specified. `update_inferred_family` does not commit.
- `classify` is not in `run`. Trigger wording and `classify` then `dashboard` sequence go in `05-06-SUMMARY.md` for 05-05 to publish.
- `DEFAULT_MIN_OCCURRENCES = 2` is labeled a placeholder, not a researched constant.

### Concerns

- **LOW:** Placeholder tokens `<STR>` after step 2 could be rewritten to `<ARG>` in step 4 unless the walk skips existing placeholders. Both PRD examples still match either way; pin “do not rewrite `<VAR>`/`<STR>`/`<ARG>`” so the documented skeleton string stays stable.
- **LOW:** Ambiguous-group test (two tool tokens → no inference) is specified; keep it. A `for` body with `rg` and `fd` must not guess.

### Suggestions

- State that placeholder tokens are terminal.
- Keep `run` as capture → refine → dashboard only.

### Risk Assessment

**LOW.** Cycle 1 HIGHs for this plan are addressed. Execute in Wave 5; let 05-05 publish docs and run repo gates.

---

## Cross-plan

Round 1 HIGHs are mostly incorporated. What is still blocking is leftover text, not missing architecture.

| Cycle 1 theme | Status |
|---|---|
| 05-01 lossless / idempotent / permissions | Fixed |
| 05-02 TEXT PK + session/message/part + storage/ | Fixed (live-reverified) |
| 05-03 Cursor identity, confidence, AST vs grep | Task 2 fixed; plan-level `<verification>` still has the old `store.db` grep |
| 05-04 scanner / shape / rtk columns / workdir rebase | Fixed in 05-04; `read_first` still cites 4 shapes |
| Token overcount | Stored once per `turn_id`, then summed per row in 05-05 |
| 05-05/05-06 SKILL.md race | Fixed (Wave 6 after Wave 5) |
| `PROJECT.md:76-78` “dashboard Artifact… local export” | Still stale (Cycle 1 consensus, not amended in `19131c2`) |

**Fix before execute:** (1) 05-03 Codex 8-key envelope + drop plan-level `store.db` grep, (2) 05-05 `groupBySession` distinct-on-`turn_id` for tokens/price, (3) 05-02/`05-04` leftover formula/enum strings. Then overall risk is **LOW**. As written, overall risk is **MEDIUM**.
