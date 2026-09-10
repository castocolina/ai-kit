Cycle 3 review of the six Phase 05 plans against repo source and commit `116fb31`. Loading review guidance and checking the cited files.
Verifying Cycle 2 closures against the plan files and checking cited existing code.
Cycle 2's 3 HIGH + 12 MEDIUM/LOW findings in `116fb31` are closed. One new HIGH remains in 05-04.

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

## Cross-plan

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
