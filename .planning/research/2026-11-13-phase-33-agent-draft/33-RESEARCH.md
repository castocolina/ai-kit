# Phase 33: One config design - Research

**Researched:** 2026-11-13
**Domain:** stdlib-only config layering, comment-keeping TOML splice, one-time roster and retry-block migration, node runner JSON edit, resolver parity
**Confidence:** HIGH for code facts (read this session), MEDIUM for the splicer and JS span-scanner designs (designed, not yet run), LOW only where tagged `[ASSUMED]`

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
D-01..D-20 of `33-CONTEXT.md` are locked; they are not repeated here. Read them in `.planning/phases/33-one-config-design/33-CONTEXT.md` (decisions section) and in `33-SPEC.md` (R1-R10, edge table, prohibitions). One-line index so the planner can cross-check:
- D-01 one file per concern, same name at both layers; D-02 `lanes.toml` + `lanes-trust/`; D-03 assignment of every inventory row; D-04 record `docs/config/design.md`; D-05 `tests/test_config_design_record.py`.
- D-06 TOML for Python-only files, JSON for runner-read files; D-07 region splicer in `ai_kit_spec`; D-08 atomic publish everywhere (fsync in `cache_write_bytes`, runner temp+rename, status-line recovery via temp+`os.replace`).
- D-09 one migration module `ai_kit_spec/config_migrate.py`; check paths never write; D-10 per-layer steps (byte copy, `os.link` publish-if-absent, re-read compare, trust, rename to `review-spec.toml.migrated`, one notice); D-11 trust re-keyed, rule unchanged.
- D-12 project retry file `.aikit/cross-ai.json` with the user file's shape; D-13 the node runner migrates and removes the GSD block (invariant at `cross-ai.mjs:3206` retired); D-14 write order values, remove block, `migrated_from` marker last; D-15 `scopes` map kept per GSD scope, notice says per checkout; D-16 only the template is edited, dogfood copy re-rendered.
- D-17 one resolver rule per code boundary + `tests/test_config_dir_parity.py`; D-18 docs list; D-19 loop `33` judges `ai-kit-spec-config` and `ai-kit-gsd-curated-config` only, referee-one and referee-two, never native opus; D-20 reusable layered reader, `config.toml` named only.

### Claude's Discretion
- Module and function names inside `ai_kit_spec` beyond those named; exact notice wording (one line, both paths, no values).
- Test module split, as long as each new module joins the runner's groups by its rules.

### Deferred Ideas (OUT OF SCOPE)
- Section-scoped trust hash for a combined file; resolving the project layer from the main worktree (flow.json style). Also out of scope: Phase 34/36/38.1/49 keys themselves, GSD's own keys, moving status line / `jev-consent.json` / trust records / `secrets.env` / `.aikit/flow.json`.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFG-01 | Inventory + one recorded design, neutral names | Q7 (callers, line cites refreshed), Q9 (record/fitness test pattern), Validation map R1-R3 |
| CFG-02 | Roster migrates on first run, trust carried, every caller on new paths | Q3 splicer, Q7 caller list, migration state machine (Architecture Pattern 2), pitfalls 3-5 |
| CFG-03 | Runner reads retry from ai-kit config; GSD block migrated once and removed | Q1 concurrency + lock guard, Q2 gsd-core writes, Q4 re-render, Q5 leak-fix coordination, Q6 line cites, JS scanner (Pattern 4) |
| CFG-04 | Every config write atomic and lossless | Q2 (gsd-core writer behaviour), Q3 splicer, Pattern 5 (publish helpers), status-line recovery fix |
</phase_requirements>

## Project Constraints (from CLAUDE.md / AGENTS.md / CLAUDE.local.md)

- Runtime code stays stdlib-only; runner stays node built-ins only; no new dependency (AGENTS.md "Non-Negotiable Rules"). No new package is recommended here.
- Every write to a runtime config file is atomic (`tempfile.mkstemp()` + `os.replace()`), reusing `_read_json_checked()`/`_atomic_write_json()`; JSONC surgical edits keep every other byte.
- No result is shown with more certainty than its sourcing (record rows that are "unverified" stay labelled).
- Any new or materially updated `SKILL.md` goes through the `skill-judge` loop (D-19 scope), at most three rounds, never native opus (rails, 2026-11-13).
- Never hardcode an absolute path in source, tests or project assets; plans use relative paths and `--cwd .`.
- Tests: scratch HOME with `AI_KIT_REFUSE_REAL_HOME=1`; no test reads `.planning/`; new `tests/test_*.py` join the runner groups automatically; `tests/test_gate_scope.py` enforces the generated listing (run `python3 tools/gen_test_groups.py` after adding a module). `tests/test_arch.py` rules need a non-vacuity counterpart if extended.
- Shell: owner's AGENTS.local rules apply word for word (one simple command per call, no `cd`, no heredocs, no `$(...)`, scripts under `tmp/`). Pass them verbatim to every subagent/executor.
- Plans must be haiku-executable (exact paths and commands, no open design decision); ponytail lens in plan review.

## Summary

The phase is mostly mechanical once five facts are pinned. (1) The runner can be started concurrently on one project: ai-kit's own judge loop spawns one detached worker per referee and every lane runs `node .planning/scripts/cross-ai.mjs` (two concurrent runner processes); GSD itself runs `workflow.cross_ai_command` one plan at a time and its review lanes use known CLI adapters, not the runner. (2) gsd-core writes `.planning/config.json` through a sibling temp + `renameSync` (`platformWriteSync`), serialises the whole parsed object (so `workflow.cross_ai_retry` survives every gsd-tools write; verified live), and every `config-set` family write holds a `wx` lock file `<scope dir>/.lock` across load-modify-write. The simplest correct guard for the runner's block removal is to take that same lock (same file, same JSON body with its own pid), re-read the file under the lock, then rename; on a timeout skip the removal (values are already merged first, D-14). (3) The TOML splicer must not reuse `_KEY_RE` as is: it mis-parses a `#` inside a quoted value (verified by a run below), and roster values like `command` and opencode `model#variant` carry `#`. (4) The dogfood runner is re-rendered by `ensure-runner`, which accepts a same-version body change for a pristine copy; new self-test cases need no shard module (membership is computed from `--self-test-list`); only the timings fixture and `E2E_RECORDED_SECS` are refreshed. (5) The `/tmp`-leak fix already exists on branch `fix/cross-ai-tmp-leak` (commit `a25784c`, worktree locked); it adds a per-case `TMPDIR` and a "left in TMPDIR" assertion, so every new non-pure self-test case must leave its case TMPDIR empty and every new pure case must remove its own `os.tmpdir()` folder.

**Primary recommendation:** build in five vertical slices in this order: (a) record + fitness test, (b) layered reader + splicer + atomic publish, (c) migration module with every roster caller and test moved, (d) runner retry sources + block migration + self-test cases + dogfood re-render, (e) resolver parity, docs, judge loop `33`. Keep every new Python module inside `ai_kit_spec` (skills never import tools).

## Answers to the ten research questions (verified this session)

### Q1. Does GSD (or ai-kit) run several runner processes on one project at once?

- **GSD itself: no for `cross_ai_command`.** The delegation step runs "for each marked plan", one at a time, with retry / skip / abort after a failure, and the command is wrapped in `run-with-timeout` [VERIFIED: `.claude/gsd-core/workflows/execute-phase.md:437-440`, quote: "For each marked plan: build a self-contained prompt ... then run the configured command"]. Review lanes are sequential by default and use `review-lane invoke`; with `review.parallel_lanes: true` the selected lanes are dispatched together and all joined [VERIFIED: `.claude/gsd-core/workflows/review.md:344-348`, quote: "Lanes run **sequentially by default**" and "opts in with `review.parallel_lanes: true`"]. But a review lane's `cli` "MUST be a known adapter (`KNOWN_REVIEWER_SLUGS`) - never an arbitrary shell command" [VERIFIED: `.claude/gsd-core/references/reviewer-instances.md:29`], so parallel GSD review lanes do not start `cross-ai.mjs`. `plan_bounce_script` and `code_review_command` are user-set commands that could name the runner; both are `null` in this project (`.planning/config.json:35,38`). This repo sets `review.parallel_lanes: true` (`.planning/config.json:76`) [VERIFIED].
- **ai-kit's own consumers: yes.** `tmp/judge-32.4/lanes.py` (the driver loop `33` copies) starts one detached worker per external judge (`cmd_launch`, lines 419-427) and each lane runs `node .claude/gsd-core/bin/gsd-tools.cjs run-with-timeout ... node .planning/scripts/cross-ai.mjs --runtime <cli> --model <model> --mode review ...` (`lane_argv`, lines 132-137): two judges give two runner processes at once in the same project [VERIFIED]. `ai-kit-cross-ai/SKILL.md:72` also says "Each parallel lane gets its own scratch directory" [VERIFIED]. So treat concurrency as real for the migration.
- **What goes wrong** if two runner calls migrate at once: (i) both merge identical values into `.aikit/cross-ai.json` and both rename: harmless (same bytes) except the `migrated_from` marker and a hand edit made between read and rename; (ii) both remove the block: with read-modify-rename and no lock the second rename restores a file computed from a stale read, or, worse, clobbers a `gsd-tools config-set` write made between the runner's read and rename (lost update).
- **Recommended guard (simplest correct):** take gsd-core's own planning lock for the GSD file you edit, re-read under the lock, rename, release. Evidence: `withPlanningLock` creates `path.join(planningDir(cwd), '.lock')` with `writeFileSync(lockPath, JSON.stringify({pid, cwd, acquired}), { flag: 'wx' })` [VERIFIED: `.claude/gsd-core/bin/lib/planning-workspace.cjs:387,407-411`], retries up to 10 s, steals a lock only when its recorded pid is not alive or it is older than 60 s [VERIFIED: same file lines 388-394, 444-517], and `setConfigValue`, `setConfigValues` and `unsetConfigValue` hold it across load -> modify -> write [VERIFIED: `config.cjs:824-860,894-915`]. A writer's lock directory equals `dirname(config.json)` for that scope (`planningDir(cwd)` is also where `config.cjs:847` reads/writes), so the runner locks `path.join(path.dirname(realConfigPath), '.lock')`. Protocol for the runner (about 30 lines of JS): `openSync(lock, 'wx')` writing `{pid: process.pid, cwd, acquired}`; on EEXIST poll 50 ms for at most about 2 s then SKIP the removal this run (log one line; the values are already in `.aikit/cross-ai.json` because step 1 of D-14 ran first, so the run is correct and the block is removed by a later call); read the GSD file again under the lock, abort when the block is gone; write temp, fsync, `renameSync`; `unlinkSync(lock)` in `finally` and on the signal/exit path. Never steal a lock (gsd-core steals a dead holder's lock itself because the body carries `pid`).
- **Residual window to accept, with a reason:** two gsd-core write paths do not take the lock: `loadConfig` persisting a legacy-key normalisation (`config-loader.cjs:712,782`) and `migrate-config` (`configuration.cjs:294`, non-atomic `writeFileSync`). They run only for legacy keys or a sub-repo change, so the window is the same one gsd-tools already has against itself [VERIFIED by reading the lines; frequency not measured]. A byte-compare just before rename is NOT recommended: it narrows but cannot close the window, and with the lock it adds nothing.
- Also lock-free and safe: the `.aikit/cross-ai.json` merge. Two concurrent runners compute identical output from identical GSD input, and the file is replaced by temp + rename, so last writer wins with equal bytes. A user hand edit between read and rename can be lost (accept; the file is tiny and the window is milliseconds). Create-if-absent (`os.link`-style, `wx` open of the temp then `linkSync`) is not required in JS; use rename.
- **Judge-loop side effect to document:** a migration edits a tracked `.planning/config.json` once; a concurrent in-flight `--mode review` lane whose `before` snapshot (`cross-ai.mjs:10761`) predates the edit reports `tree=dirty`. The migrating process itself is safe because `resolveRetry` runs at `cross-ai.mjs:10677`, before its own snapshot at `:10761` [VERIFIED]. ai-kit's own `.planning/config.json` has no `cross_ai_retry` today, so loop `33` is unaffected; note it in `docs/config/design.md` and the runner docs.

### Q2. gsd-core's own writes to `.planning/config.json`

- `config.cjs:658` is in `cmdConfigNewProject` (creation only; it returns early when the file exists, `config.cjs:634-637`): `platformWriteSync(configPath, JSON.stringify(config, null, 2))` [VERIFIED: quote of line 658: `(0, shell_command_projection_cjs_1.platformWriteSync)(configPath, JSON.stringify(config, null, 2));`]. D-13's citation is right about the serialisation and the temp + rename, but the path that matters for `config-set` is `setConfigValue` (`config.cjs:846-860`), `setConfigValues` (`:894-915`) and `unsetConfigValue` (`:824-838`). Suggested citation fix for the record: 658 (new-project), 690 (`ensureConfigFile`), 831/853/908 (unset/set/set-many).
- `platformWriteSync` = sibling temp `filePath + '.tmp.' + process.pid`, `writeFileSync`, `atomicRenameWithRetry`, with two fallbacks to a direct non-atomic write (temp write fails; `EXDEV`) [VERIFIED: `.claude/gsd-core/bin/lib/shell-command-projection.cjs:1340-1379`, quote of 1348: `const tmpPath = filePath + '.tmp.' + process.pid;`]. The temp name is built from the path as given, not the realpath: a symlinked `config.json` is replaced by a regular file after any gsd-tools write. D-13's "symlinked config.json stays a link" is therefore a runner-side property only (write beside the realpath).
- **Unknown workflow keys survive every config-set family write:** the file is parsed whole, mutated at one path and stringified whole [VERIFIED: `loadConfigJson` `config.cjs:811-823`, `_setNestedValue` use at 850]. Live falsification run (scratch dir, `tmp/p33-plan/research/gsd_probe.sh`): after `config-set workflow.research false` the file read `"cross_ai_timeout": 300, "cross_ai_retry": { "base_s": 2 }, "research": false`, reformatted to two-space JSON [VERIFIED by run]. Consequence: after any gsd-tools write the file is reformatted, so "keeps every other byte" only holds for the runner's own edit; the span scanner must accept both compact and 2-space layouts.
- **Paths that drop the block:** `/gsd-health --repair` with `RESET_CONFIG`/`CREATE_CONFIG` writes `defaultConfigPayload()` (a factory reset; every unknown key goes) [VERIFIED: `health-diagnostic.cjs:279-283`]. No other path found.
- **Read-path writes exist:** `loadConfig` with `persist` rewrites the file (whole object) when `normalizeLegacyKeys` migrated something or sub-repos changed, without the planning lock (`config-loader.cjs:710-715,780-785`) [VERIFIED]; `migrate-config` `writeFileSync`s non-atomically (`configuration.cjs:293-299`) [VERIFIED]; `roadmap-upgrade.cjs:2119` writes non-atomically on a phase-id migration [VERIFIED]. All keep unknown keys.
- **Nothing re-adds `cross_ai_retry`:** `rg cross_ai_retry .claude/gsd-core` has zero hits (no default, no template, no manifest entry) [VERIFIED: ran it]. The only re-add vectors are a hand edit or a restore of a dated backup (ai-kit-curated-config writes `config.json.bak-<stamp>` backups, `config_backup.py:17-21,110-130` per the inventory); both land in the D-14 "re-added block ignored with a notice" path.
- The runner's span-scanner removal survives later gsd-core writes (the block is simply absent) [VERIFIED by reasoning from the above]. `config-set workflow.cross_ai_retry.base_s 1` is refused: `Error: Unknown config key: "workflow.cross_ai_retry.base_s". Valid keys: ...` [VERIFIED by run; source `config.cjs:205-209`; manifest `bin/shared/config-schema.manifest.json:68-70` lists only `workflow.cross_ai_execution`, `workflow.cross_ai_command`, `workflow.cross_ai_timeout`].

### Q3. Comment-keeping TOML splicer for `lanes.toml`

Survey (all [VERIFIED] by reading):
- `tools/setup.py:461-464` `_KEY_RE = re.compile(r"^(?P<indent>\s*)#?\s*(?P<key>\w+)\s*=\s*[^#\n]*?(?P<trail>\s*#.*)?$")`; `_header_name` (467-471); `patch_host_keys` (545-592) is the closest model (find table by header, rewrite key line in place keeping the trailing comment, insert missing key after the last rewritten key, keep every other byte); `drop_host_keys` (595-607). `create_if_absent` (2752-2783) is the `os.link` publish-if-absent (temp via `mkstemp`, fsync, `os.link`, EEXIST means another process won, `O_EXCL` fallback).
- `tools/config_doctor_appliers.py`: `write_toml_region_replace` (69), JSONC classifier `_classify` (219), `_skip_value` (248), `find_object_span` (281), `_find_top_level_key_span` (312; depth-1 keys only, returns `(key_start, value_start, value_end)`, no comma handling), `set_jsonc_value` (376).
- `ai_kit_spec/config_io.py`: `cfg_render_toml` (602-636), `cfg_write_toml` (639-640), `_toml_value` (453-461): bool -> `true/false`; int/float -> `str(v)`; list -> `[a, b]` recursive; everything else -> a double-quoted string with only `\` and `"` escaped (a raw newline or tab in a value would produce invalid TOML; the re-parse gate catches it). Roster value types: strings (`key`, `model`, `vendor`, `runtime`, `command`, `purpose`, `effort`, `service_tier`), bools (`is_router`, `fallback_quota`), ints (`context_limit`), string lists (`ladder`, `task_affinity`, `timeout_tiers` is an int list), top-level `strategy` string, `[policy]` `mode` string. Nested dicts are refused on save for every reviewer field (`config_io.py:518-525`) but can load (`extra = { timeout_tiers = [...] }` or a `[reviewers.extra]` sub-table).
- **Pitfall verified by a run** (`tmp/p33-plan/research/keyre_probe.py`): `_KEY_RE` takes a `#` inside a quoted value as a comment start: for `command = "run {model} # not a comment"` its `trail` group captured ` # not a comment"` and for `model = "a/b#fast" # real comment` it captured `#fast" # real comment`. Rewriting a changed key with `_KEY_RE` would duplicate or lose text. The splicer needs a quote-aware statement scanner, not that regex. Also verified: tomllib attaches `[reviewers.sub]` to the preceding `[[reviewers]]` entry.

**Recommended algorithm (least code that meets R3/R8 and the SPEC edges), one module `ai_kit_spec/toml_splice.py`, about 150 lines, no third-party code:**

1. `scan(text)`: one pass that classifies characters well enough to find **statement starts at depth 0**: states for basic string, literal string, multi-line `"""` and `'''` strings, comment, and bracket depth for a value array/inline table that spans lines. Output a list of lines with `(start_offset, kind)`, `kind` in `header`, `array_header`, `key`, `other`, plus for each `key` line the end offset of its statement (multi-line arrays/strings) and the offset of its trailing comment (found only outside strings). Header detection: first non-space char of a depth-0 statement is `[`.
2. Segment the file into blocks: preamble (everything before the first header, holds top-level keys such as `strategy`), then one block per header, from its header line to the line before the next header (comments and blank lines directly above a header stay with the block above, so removing an entry removes only its own lines and its trailing blank line).
3. Blocks with header `reviewers` (array header) plus any immediately following `[reviewers.*]` sub-table blocks form one entry. Match entries to the new list by their `key` value (parse the entry text with `tomllib.loads` after stripping nothing; `tomllib.loads(entry_text)["reviewers"][0]`).
4. For each new entry in new order: an existing entry whose parsed value equals the new entry (compare after the known-field projection, see 5) keeps its bytes. A changed entry: for each owned key whose value differs, replace the value span of that statement with `_toml_value(v)` and keep the trailing comment and the newline style; a missing owned key is appended after the entry's last key statement (before trailing blank lines) as `key = value`; an owned key absent from the new entry is deleted (whole statement). Keys not in the owned set are never touched (this is what keeps R3's unknown key inside a known section). A dict value that changed raises `ConfigError` (save refuses nested dicts today); an unchanged dict is kept as bytes.
5. **Owned key set** = one constant: reviewer `key, model, vendor, runtime, command, purpose, is_router, fallback_quota, effort, service_tier, task_affinity, context_limit, extra` (plus legacy `cli`, `native_runtime`, which save refuses); policy `mode, ladder, timeout_tiers`; top-level `strategy`. [ASSUMED: this list is from reading `config_io.py:20,464-540`, `dispatch_injection.py:180-187`, `DEFAULT_POLICY` at `config_io.py:18`; confirm against the wizard's output keys in `ai-kit-spec-config/SKILL.md`.]
6. Entry placement: put entry `i` of the new list in the slot of old entry `i` (so unknown sections between entries keep their position); extra entries append after the last slot; removed entries' slots are deleted. Top-level `strategy`: edit in place, else insert as the last statement of the preamble (a top-level key written after a header would become a table key). `[policy]`: edit keys in place, append missing keys to the block, create the block before the first reviewers block when absent. Unknown sections, comments, and blank lines outside changed statements are copied verbatim.
7. Newlines: detect `\r\n` in the old text once and use it for every generated line; a last line with no final newline gets one only if something is appended after it. A UTF-8 BOM is kept as part of the first line. Empty old file -> render fresh.
8. **Publish gate:** `tomllib.loads(result)` must equal the intended dict (old parsed dict with the roster keys replaced by the new values, unknown sections kept); otherwise raise and publish nothing (`write_toml_region_replace` and `write_toml_preserving` use the same re-parse-then-publish shape).
9. Pitfalls to cover in tests: `#` inside a value, key line with trailing comment, a multi-line array value (`task_affinity = [\n "a",\n "b",\n]`), an inline table (`extra = { ... }`), a `[reviewers.extra]` sub-table, dotted keys (`a.b = 1` inside an entry: treat as an unknown key, never owned), CRLF, a missing final newline, an empty unknown section header, comments directly above a removed entry, entry reorder.
10. Known limit to record with a `shortcut:` comment: the generated `# Priority fallback order` comment block (`config_io.py:566-573`) is not regenerated on a splice (the ladder lines it lists can go stale); a fresh render (no existing file) still writes it.

`render-toml`: no existing `--out` file -> `cfg_render_toml` as today; existing and `--replace` -> splice; existing without `--replace` -> refuse as today (`cli.py:759-764`). `cfg_write_toml` has only test callers (inventory; re-verify with `rg cfg_write_toml tests`) and can be pointed at the splice or kept for fresh renders.

### Q4. Runner template, dogfood re-render, self-test harness

- **Render:** `skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py ensure-runner --cwd <project>` (CLI `_cmd_ensure_runner`, `cli.py:218-224`; prints JSON `{ready, runner, notes}`; exit 0 ready, 1 not ready, 2 error [VERIFIED: SKILL.md table row for `ensure-runner`]). It loads the template through `ai_kit_spec.tooling_guidance.resolve_cross_ai_template_path` via the sibling-skill shim (`cross_ai_script.py:147-155`, `gsd_catalog.py:28-42`), so run it from the checkout to render the checkout's template. Substitution: `_replace_config` swaps the text between `// <config>` and `// </config>` with `const CONFIG = <json, indent 2, sort_keys>;`, `_stamp` writes the header line `// ai-kit-cross-ai generator=ai-kit-gsd-curated-config template=<n> sha256=<sha of body>` (`cross_ai_script.py:111-144`). The template header is `template=8 sha256=UNSTAMPED` (template line 2) [VERIFIED].
- **No version bump needed:** a pristine copy "takes every template fix, a same-version body fix included" (`plan_runner_upgrade`, `cross_ai_script.py:282-289`) and the existing CONFIG is kept (`_upgrade_config`, 238-258). Command the executor runs after editing the template (path-agnostic, from the repo root, `AI_KIT_REFUSE_REAL_HOME=1` exported): `python3 skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py ensure-runner --cwd .` then `python3 tools/check_dogfood.py` (the hook's script, `main` at `tools/check_dogfood.py:622`; it needs `node`; `make check-dogfood` is the same via pre-commit and is run by the orchestrator, not by the research). Expect `check-dogfood: ok`. Edge: if the leak-fix branch merges first, re-render instead of merging text in `.planning/scripts/cross-ai.mjs` (both branches touch it).
- **What check-dogfood proves:** `check_runner_copy` compares template version, `script_state(copy) == "pristine"` (sha256 of body equals the header digest) and equality of copy and template outside the `// <config>` block (`tools/check_dogfood.py:91-117`) [VERIFIED].
- **Self-test:** `node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test` runs every case (minutes); `--self-test-list` prints `name<TAB>kind` (ran it: about 480 cases, `retry-config-*` at the end of the retry block); `AIKIT_XAI_SELFTEST_CASES=a,b` selects cases (`tests/cross_ai_selftest.py:275-279`). Cases are objects in the `cases` array of `blackBoxSelfTest` with `name`, `kind: 'logic'|'runtime'`, `args`, `stdin`, `planningConfig`, `workstream`, `files`, `setup`, `check`, `env`, `config`, `second` or `pure: () => ...` [VERIFIED: `cross-ai.mjs:5551-5598,9033-9302`]. `runSelfTestCase` writes `planningConfig` to `<repo>/.planning/config.json` and `files` (JSON-stringified) under the repo; `hermeticEnv` (`:4637-4653`) gives `PATH`, `HOME`, `XDG_CONFIG_HOME` and git identity. A case is `runtime` when it waits on or measures a real clock; else `logic`.
- **Sharding:** `tests/cross_ai_selftest.py` deals each kind into `SHARD_COUNTS = {"logic": 4, "runtime": 4}` shards by recorded seconds, "Membership is never a hand list" (`split_cases`, 238-255; `shard_names`, 258-261) [VERIFIED]. **New cases need no new shard module**; a name missing from the timing fixture weighs the median. Fixed modules: `tests/test_cross_ai_selftest_{logic,runtime}_{1..4}_e2e.py`. Refresh timings on a quiet machine: `python3 tests/cross_ai_selftest.py --record-times` (about 4 minutes; rewrites `tests/fixtures/cross_ai_selftest_secs.json` atomically). `E2E_RECORDED_SECS` (`tools/run_unittest_parallel.py:159-175`) holds e.g. `"tests.test_cross_ai_selftest_logic_1_e2e": 22,` and `...runtime_1_e2e": 24,`; refresh it from the `=== <module>: ok in <s>` lines of `make e2e-test` when a shard's time changes; the commit budget is `COMMIT_E2E_BUDGET_SECS = 60` (line 154). Adding about a dozen mostly-`logic` cases (a few seconds each) stays under budget; if a shard exceeds it, the commit hook defers it to push, which is acceptable.
- **Existing cases that break and must be rewritten:** every case that seeds `planningConfig: { workflow: { cross_ai_retry: ... } }` or a `workstream.config` block: `hard-tier-config-waits` (`cross-ai.mjs:6912`), `retry-config-drives-ladder` (8487), `retry-config-project` (9037), `retry-config-per-key` (9071), `retry-config-workstream` (9090-9091), `retry-config-workstream-fallback` (9103-9104), `retry-config-refused` (9114), `retry-config-unknown-key` (9174), `retry-config-read-only` (9202; asserts the GSD file bytes AND mtime unchanged: now the first run must change them and the second must not), `retry-config-outside` (9281; see Open Question 3), `retry-config-malformed` (the notice names `.planning/config.json`). Their expected log lines name `(.planning/config.json)` as the source label; the new label is the `.aikit/cross-ai.json` path. Also doc-pinning tests: `tests/test_cross_ai_skill_text.py:194,299-315` (text about `workflow.cross_ai_retry`, the policy doc's example block `{"workflow": {"cross_ai_retry": retry}}`, `config-set refuses`, `${XDG_CONFIG_HOME:-~/.config}/ai-kit/cross-ai.json`) and `tests/test_quota_policy_text.py` (retry_after_s rows, unaffected unless edited).

### Q5. Coordination with the `/tmp`-leak fix

Found on branch `fix/cross-ai-tmp-leak` (worktree `.claude/worktrees/agent-ae4d0f48dd173410a`, locked), commit `a25784c` "fix(cross-ai): drop runner temp folders on every exit; keep self-test temp out of /tmp", not on `gsd/phase-33-one-config-design` (`rg exitFlushed` in this tree shows no sweep) [VERIFIED: `git diff eabcd1a a25784c`]. It touches, in `skills/ai-kit-spec-review/references/cross-ai.mjs`: `exitFlushed` (adds a `tempDirs` sweep before `process.exitCode`), the `uncaughtException` handler and the signal `backstop` (their own sweeps removed), `hermeticEnv` (adds `TMPDIR`, default `path.join(tmp, 'tmpdir')`), `runSelfTestCase` (per-case `tmpdir = path.join(tmp, 'tmp-<name>')`, passes `TMPDIR`, adds `tmpdir` to the case context `c`, and after the case fails with `left in TMPDIR: <names>` unless `spec.keepsTmp`), one case marked `keepsTmp: true`; in `tests/cross_ai_selftest.py` `runner_env` (adds `"TMPDIR": tmp`); and the rendered `.planning/scripts/cross-ai.mjs`. Plans must not redo these.

What new cases must do under the per-case empty-TMPDIR assertion:
- Non-pure (harness) cases: leave `c.tmpdir` empty. The assertion reads only the case TMPDIR (runner temp folders, `makeTemp` uses `os.tmpdir()`). The migration must therefore write its temp files **beside the target** (`.aikit/` and `.planning/` or the config's realpath folder), never in `os.tmpdir()`, and must delete its temp file in a `finally`. Fixtures belong under `c.repo`/`c.home` (already outside `c.tmpdir`); never create fixtures in `c.tmpdir`.
- Pure cases (`pure: () => ...`) return before the assertion and use `fs.mkdtempSync(path.join(os.tmpdir(), 'xai-...-'))`; they must `fs.rmSync(root, { recursive: true, force: true })` in a `finally`, as `pure-retry-user-config-without-home` does (`cross-ai.mjs:5990-6014`). With the fix, `TMPDIR` in the self-test process is the shard's tmp, so a forgotten folder lands in the shard's `tmp` rather than `/tmp`, but still must not be left.
- A case that kills the runner on purpose may set `keepsTmp: true`; none of the new cases should.
- Conflict handling: the fix edits `exitFlushed`, `hermeticEnv` and `runSelfTestCase`; phase 33 edits `resolveRetry`, `aiKitConfigDir` neighbours, the case list near `retry-config-*`, and the header comment at `:62-63`. Hunks do not overlap; the only overlap is the dogfood copy, which is regenerated.

### Q6. Current runner retry code (template `cross-ai.mjs`, line numbers verified this session)

- `exitFlushed` 1307; `parseJson` 1486 (`function parseJson(s) { try { return JSON.parse(s); } catch { return null; } }`); header comment naming the sources 62-63.
- `CONFIG` block 77-113; `CONFIG.retry` 86-96 (`base_s 1, factor 1.5, hard_waits_s [600,900,1800], max_retries 5, session_resets 1`); `GSD_DEFAULT_TIMEOUT_S` 115.
- `ownTimeout` 3006-3010 (`workflowValue(cfgPath, 'cross_ai_timeout').value`, no root, follows symlinks); `scopedConfigPaths` 3016-3025; `liveOuterTimeoutS` 3026-3032; `confinementError` 3036-3051; `CONFIG_READ_MAX` 3054 (1 MiB); `readJsonObject(file, rootDir = null)` 3056-3069 (missing file -> `{obj: null}`; with `rootDir` the realpath must stay inside; regular file only; size cap; `{error}` strings); `aiKitConfigDir(env)` 3073-3076 (`const configHome = env.XDG_CONFIG_HOME || path.join(env.HOME || os.homedir(), '.config'); return path.join(configHome, 'ai-kit');`); `loadOverlay` 3078-3126; `workflowValue` 3127-3136; `RETRY_DEFAULTS` 3172-3175 (frozen, `hard_waits_s: [600, 900, 1800]`); `RETRY_KEYS` 3176 (`['base_s', 'factor', 'max_retries', 'session_resets', 'hard_waits_s']`); `validateRetryKey` 3178-3204 (bounds: `base_s` 0..60, `factor` 1..3, `max_retries` int 0..10, `session_resets` int 0..3, `hard_waits_s` 1..6 ints each 0..capS); comment "Read once per call. Nothing here writes a config file." 3206-3207; `resolveRetry(cwd, env)` 3208-3268 (sources: scoped GSD files via `workflowValue(cfgPath, 'cross_ai_retry', path.join(cwd, '.planning'))` 3215-3224, user file 3225-3233, `CONFIG.retry` 3234; per-key first-valid wins 3249-3263; logs one `cross-ai: retry ...` line 3265); `writeCycleState` 3410-3423 (`mkdirSync` 0700 dir, temp `.${base}.${pid}.${uuid}.tmp` opened `wx` 0600, write, close, `renameSync`, chmod 0600; no fsync); `resolveRetry` called at 10677 inside the run path (also reached by `--print-argv`), `before` tree snapshot 10761 [VERIFIED].
- **Scope -> path mapping** (`scopedConfigPaths`): `ws = (env.GSD_WORKSTREAM||'').trim()`, `project = (env.GSD_PROJECT||'').trim()`; a `/`, `\` or `..` in either returns `[]`; `root = <cwd>/.planning`; `scoped = join(root, project, ws ? join('workstreams', ws) : '')`; returns `[scoped/config.json]` plus `root/config.json` only when `ws` is set. So the D-15 scope labels are `path.relative(root, dirname(scoped/config.json))`: `''` (root), `<project>`, `<project>/workstreams/<ws>`, `workstreams/<ws>`. Today a project-only scope reads only the project file (no fallback to the root file); a workstream scope falls back to the **root** file (not the project file). gsd-core's own ladder is the same (`planning-workspace.cjs:290-295`).

### Q7. Every caller and test to update (line cites refreshed; `rg` and reads this session)

Runtime code naming `review-spec.toml` / `review-spec-trust` literally (25 lines; the R6 test matches the literals): `ai_kit_spec/config_io.py` (15: 7 docstring/comment lines, `:265`, `:286`, `:291`, 446, 448 note strings), `trust.py` (3: docstring 1, 3, 10), `cli.py` (4: 169, 180, 185, 874 help/message text), `quota.py` (2: 134, 177), `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py` (167 docstring). All must be reworded or moved into `config_migrate.py`. Strings such as `LOCAL_ONLY_REASON = 'local review-spec sets strategy...'` (`provider_check.py:19-20`) and `argparse prog="review-spec"` (`cli.py:398`) do not match the literal; reword anyway for the neutral-name goal.

Function callers [VERIFIED by rg]: `cfg_resolve` -> `cli.py:486` (`_discovered_catalog_candidates`), `:689` (`probe-quota`), `:720` (`resolve-reviewers`), `:811` (`resolve-timeout-tiers`), `dispatch_injection.py:175` (`assemble_candidates`, default arg `cfg_resolve_fn=cfg_resolve`). `cfg_combine` -> `cli.py:824` (`_trust_local_argv_lines`, comment says it renders a file not yet trusted). `cfg_local_path` -> `config_io.py:399`, `cli.py:836`, `provider_check.py:172`. `cfg_global_path` -> `config_io.py:440`, `provider_check.py:173`. `cfg_trust_store_dir` -> `config_io.py:406`, `provider_check.py:85`, `cli.py:839`. `trust.is_trusted` -> `config_io.py:406`, `provider_check.py:88`, `cli.py:850`; `record_trust` -> `cli.py:855`; `revoke_trust` -> `cli.py:841`. `cfg_render_toml` -> `cli.py:767` (`_cmd_render_toml` 759-773, atomic write at 771 via `cache_write_text`). `cfg_write_toml` -> tests only (re-verify). `quota` has no path call (strings only). `provider_check.scan_review_spec` (92-110) and `_scan_sources` (171-186) read local and global through `cfg_local_path`/`cfg_global_path` and must read a legacy file read-only through the migration module (D-09). `local_secrets.secrets_env_path` (`local_secrets.py:8-9`: `return os.path.join(env.get("HOME", ""), ".config", "ai-kit", "secrets.env")`, ignores `XDG_CONFIG_HOME`) -> callers `load_secret` (same file, 19). `jev_review._config_dir` (981-985) and `consent_path` (988-990) [VERIFIED]. `tools/common_config.py:273` (`cfg_config_path`: `base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", ""), ".config")`) and `:506` (`cfg_segments_dir` has the same expression: a second copy to fold into the one function) and `tools/setup.py:122` (`config_base = env.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")`) [VERIFIED]. `_recover_incompatible_config` is `tools/setup.py:3467-3504` (the two `shutil.copyfile` calls at 3496-3497); its tests are `tests/test_setup.py:3420-3477`.

Tests that name the old paths or functions and must move to the new ones (`rg -c`): `tests/test_ai_kit_spec.py` (32 literal hits), `test_ai_kit_spec_legacy_config.py` (14), `test_ai_kit_spec_trust.py` (7), `test_ai_kit_spec_routing.py` (5), `test_ai_kit_spec_check_providers.py` (2), `test_ai_kit_spec_superpowers.py` (2), `tests/gsd_curated_eval.py` (1) and `test_gsd_curated_eval.py` (1); other test files that call the path helpers: `test_setup.py`, `test_config_doctor_pty.py`, `test_wizard_pty.py`, `test_tool_substitution_hook.py`, `test_ai_kit_usage_metrics.py`, `test_jev_fast_decision.py` (they match `_config_dir`/`consent_path`/helper names; check each for a roster path before editing).

Docs and evals to update (literal hits): `README.md:35` (skills-table row), `skills/ai-kit-spec-config/SKILL.md` (12: lines 3, 78, 143, 145, 212, 247, 278, 340, 392-393, 446, 449; line 143 tells the agent to `Read ~/.config/ai-kit/review-spec.toml` directly, which must become a CLI read), `references/check-only.md` (8-9), `references/cli-model-selection.md` (73, 82, 301), `skills/ai-kit-spec-review/SKILL.md` (23, 176), `references/cross-ai-dispatch.md` (143, 192), `references/cli-profiles/cursor.md` (76, 103), `evals/01..04-*.md` (one each), `skills/ai-kit-spec-review-checklist/evals/orchestrator-integration.md` (2), `skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md:10`, `skills/ai-kit-spec-config/evals/evals.json` (2) and `evals/trigger-queries.json` (1): the R6 doc test must scan `*.json` evals too, not only `*.md`. Retry text: `skills/ai-kit-cross-ai/SKILL.md:20`, `references/subprocess-quota-policy.md:59-84`, `skills/ai-kit-gsd-curated-config/SKILL.md:272,365`, `references/runner.md:4,41-42` (D-18). History under `docs/prds/` and `docs/superpowers/` is excluded by decision.

Dogfood facts: the repo's own roster `.aikit/review-spec.toml` and the owner's `~/.config/ai-kit/review-spec.toml` exist on this machine (inventory); `.aikit/` is untracked (`.gitignore:12` is `.aikit/`; `git ls-files .aikit` is empty). Migration of the real files must never run during execution (rails: no real config write); tests use a scratch HOME. The first real run after shipping migrates them (report to the orchestrator as a ship-step note).

### Q8. Layered reader reusable by Phase 34

Recommended shape, one small module `ai_kit_spec/layered_config.py` (name at the planner's discretion), pure functions plus one thin file-reading wrapper:

```python
# Source: derived from config_io.cfg_combine/_combine_layers (config_io.py:418-450)
def layer_paths(name, cwd, env):  # (project_path, user_path); user via the one resolver
    return (os.path.join(cwd, ".aikit", name), os.path.join(cfg_config_base(env), name))

def merge_layers(user: dict, project: dict) -> dict:
    """Project over user per key; two dict values merge per key (recursively); lists and scalars
    are replaced. Unknown sections and keys pass through untouched."""

def load_layered(name, cwd, env, *, parse, gate=None, skip_user_if=None) -> dict:
    """Read each layer once (bytes -> parse), project first for the gate, then merge."""
```
Rules mirrored from `cfg_combine`: a missing file is `{}`; a malformed or non-UTF-8 file raises `ConfigError` (exit 2); the project layer passes through `gate(path, raw) -> bool` (trust for `lanes.toml`, `None` for `config.toml`); `skip_user_if(project_dict)` carries the one stated exception (`strategy = "local-only"` skips the user file, `config_io.py:442`, B-WR-01: it is never read). Arrays of tables keep their domain merge: `[[reviewers]]` still merge by `key` through `cfg_merge_reviewers` (`config_io.py:358-382`), so the generic rule is "dicts merge per key, everything else replaces" and `lanes.toml` overrides `reviewers` with the domain merge after the generic pass (the same split `_combine_layers` already has). `jev-fast-decision` copies `layer_paths`, `merge_layers` and a stdlib `tomllib` loader (no gate, no `ai_kit_spec` import: cross-skill reaches are frozen in `tests/test_arch.py`); the parity test feeds one table of `(user, project)` pairs to both copies and compares merged dicts. Put the pure `merge_layers` cases in `tests/test_config_layered.py` (R2 adjacency and idempotency edges) so Phase 34 can import the same case table.

### Q9. Test patterns to copy

- Markdown scanners: `tests/test_skill_text_history.py` (`shipped_markdown(skill_dir)` at 125-133 = every `.md` under a skill outside `evals/` and `__pycache__`; `main_flow`, regex tables, `history_hits`); for R6 write a sibling scanner that walks `skills/**/*.md`, `skills/**/evals/**` (`.md` and `.json`), `skills/**/*.py`, `tools/**/*.py` and `README.md`, excludes `docs/prds/`, `docs/superpowers/`, `docs/config/design.md` and `ai_kit_spec/config_migrate.py`, and allows a line that names both old and new paths (a migration note). Include a non-vacuity case (a synthetic file that must be flagged) as `TestArchNonVacuity` does.
- Structure/AST rules: `tests/test_arch.py` (non-vacuity requirement, AGENTS.md); R9 parity can follow the same "load the module by path" approach used by `tests/test_gate_scope.py` `load_tool`.
- Runner groups: a new flat `tests/test_*.py` is discovered into `unit` automatically (`tools/run_unittest_parallel.py` docstring lines 36-42); a module needing uv/PTY/Textual goes in a commented exception set; `tests/test_gate_scope.py:570-583` fails with "stale listing; run: python3 tools/gen_test_groups.py" when the generated listing in the Makefile and hooks lacks a module: **run `python3 tools/gen_test_groups.py` after adding test modules** and commit the regenerated Makefile and `.pre-commit-config.yaml`.
- Recommended new modules: `tests/test_config_design_record.py` (R1, R2, D-05), `tests/test_config_layered.py` (R2, R3), `tests/test_toml_splice.py` (R3, R8), `tests/test_config_migrate.py` (R4, R5, prohibitions), `tests/test_config_doc_names.py` (R6 doc and code scan), `tests/test_config_dir_parity.py` (R9), `tests/test_atomic_publish.py` (R8 interruption cases, status-line recovery). All unit group, stdlib only.
- R1 collector: call each path function with a scratch `cwd`/`env` and take `os.path.basename`; load `jev_review.py` by path (`importlib.util.spec_from_file_location`, skills stay self-contained) for `consent_path`; take the runner's file names (`cross-ai.json`, `cross-ai-errors.json`) from the template text by exact string (`path.join(userRoot, 'cross-ai.json')`, `:3226`; `:3080`) so a rename in the runner fails the test; `flow.json` from `flow_record.SETTINGS_REL`. The record's inventory rows carry a fixed "Assignment" column with exactly one of `moves-now`, `conforms`, `separate`, `later:<phase>`; the test counts one token per row.

### Q10. What a phase-33 judge plan must copy from 32.4-07

Source: `.planning/phases/32.4-batch-4-planning-skills-and-the-closing-report/32.4-07-PLAN.md` (read in full).
- Shape: three tasks (tracer: drivers, judged set, staging copy, probes, pool, counts, lane prompts, detached workers; checkpoint for the orchestrator: wait for lanes; auto: publish, report, checks, bar table, verifier facts) with `autonomous: false`, wave last, depends on every doc/code plan, run in the main checkout, frozen tree from launch until `lanes.py status` prints `all lanes ended` (no tracked edit, no commit, HEAD unmoved).
- Mechanics (`tools/judge_loop.py` verbs, usage at the top of the file): `prompt --probe --judge ID --out DIR`; `pool --loop L --probe-dir DIR --records DIR [--judges J ...] [--native ID]` (the tool's usage line: "the first two usable judges in list order, or one with a note; no usable judge exits 1; --native ID keeps the old native fallback for old loops"); `count --loop L --records DIR [--skill S ...]` (bases each skill on its latest prior loop's lowest valid percent; `REGRESSION_TENTHS = 70`); `prompt --loop L --round N --judge J --skill S --out DIR`; `ingest --lane-dir DIR --records DIR [--replaces ID --reason TEXT]`; `report RECORDS` (rewrites `REJUDGE.md` and `facts.json`); `check RECORDS [--skills ...] [--judges ...] [--gate] [--require-current]`. `.planning/judge/` is copied to `tmp/judge-33/records/`, lanes publish byte for byte in one commit per round, at most three rounds, probes run through `.planning/scripts/cross-ai.mjs --mode review`, lanes under `run-with-timeout --outer-timeout 3600`.
- **Changes versus 32.4 that D-19 and the 2026-11-13 rails force** (the 32.4 copy does the opposite): `tmp/judge-32.4/lanes.py` has `NATIVE = "native:opus-xhigh"` (line 30), `INSTANCES = ("referee-two", "referee-three")` (32) and calls `pool ... --native NATIVE` (381); the native lane/`natives.txt`/`ingest-natives` steps and Task 2's `ai-kit-judge` agent spawns must be dropped. Phase 33 judges are referee-one and referee-two (`opencode:router-env/my-referee-one`, `...two`), referee-three replaces one that fails mid-run (`ingest --replaces <judge> --reason <text>` with an external referee-three lane), one usable referee is accepted with its reason recorded, zero usable stops the round. `.planning/config.json` has all three `reviewer_instances` but only `referee-two` in `default_reviewers` (`:67-69`), so the driver must take its judge list from the rails, not from `default_reviewers`. [ASSUMED: referee-one's probe will pass; probe first and record any failure.]
- Judged set: exactly `ai-kit-spec-config` and `ai-kit-gsd-curated-config` (D-19). 32.4's `judged.py` computes the set from `git diff --name-only <BASE> -- skills/<name>/` with `.md` outside `evals/`; for phase 33 use `BASE` = the phase's start commit (`eabcd1a`, the last pre-execution commit) and `EXPECTED = ["ai-kit-gsd-curated-config", "ai-kit-spec-config"]`; it must exit 1 on any other set (fact-only skills `ai-kit-spec-review`, `ai-kit-cross-ai`, `ai-kit-spec-review-checklist`, `ai-kit-spec-execute-superpowers` stay out and are listed as stale-digest notes with the reason in `33-VERIFICATION.md`). Never judge `ai-kit-commit-fold` or `ai-kit-project-rules-*`.
- Regression bases are computed by `bar_with_base`, never by hand. Current records: `ai-kit-spec-config` loop 32 round 1, worst 79.2 C, bar "met: no critical or high finding" (`.planning/judge/REJUDGE.md:20`; D-19 cites 77.6, which is the "last percent 77.6" text of the "Why this many" cell, not the worst percent: let `count` print the base); `ai-kit-gsd-curated-config` loop 32.4 round 2, worst 88.0 B (`REJUDGE.md:27`) [VERIFIED].
- Closing commands (copy from 32.4-07 `<orchestrator_steps>`): `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/judge_loop.py check .planning/judge` and `... check .planning/judge --skills ai-kit-spec-config ai-kit-gsd-curated-config --require-current --gate` (an unscoped `--require-current` fails on stale digests of unjudged skills); `make check-dogfood` after the records commit (the orchestrator runs make targets). The drivers are scratch under `tmp/judge-32.4/` (present), copied with `32.4` replaced by `33` and a script that refuses to finish unless the retry cap line (`fields.get("status") == "transient" and attempt <= 3`) is present.
- Order: all SKILL.md and reference edits are committed before the first judge run; judging happens after the doc change is committed (SPEC edge R10 ordering).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Settings record + fitness test | Docs (`docs/config/design.md`) + unit test | - | Tests may read `docs/`, never `.planning/` (AGENTS.md) |
| Layered reader, splicer, atomic publish | `ai_kit_spec` Python package (spec-review skill) | `tools/common_config.py` copy for the user-dir resolver only | Skills never import `tools/`; shared logic is copied with a parity test |
| Roster migration + trust carry | `ai_kit_spec/config_migrate.py` (only module naming the old names) | CLIs `cfg_resolve`, `trust-local`, `render-toml` call it first | D-09; check paths read legacy files read-only |
| Runner retry sources + GSD block migration | `cross-ai.mjs` template (node built-ins) | dogfood render | The runner is called directly by GSD; no Python on that path (D-13) |
| Resolver rule | one function per code boundary | parity test (Python + node) | D-17 |
| Judge loop | `tools/judge_loop.py` + tmp drivers | orchestrator (no native lanes) | D-19 |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`tomllib`, `os`, `tempfile`, `hashlib`, `re`, `json`) | project pin 3.12 (`pyproject.toml:9` per inventory; the system `python3` here is 3.15.2) | readers, splicer, migration | AGENTS.md: stdlib-only runtime |
| Node built-ins (`fs`, `path`, `os`, `crypto`) | node v24.21.0 on this machine [VERIFIED: ran `node --version`] | runner migration, JSON span edit | AGENTS.md: runner node built-ins only |
| `ai_kit_spec.cache` (`cache_write_bytes/text/json`) | in repo (`cache.py:27-69`) | atomic publish (add fsync, D-08) | existing helper, already used by trust, render-toml |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tools/judge_loop.py` | in repo | loop `33` | judge step |
| `tools/gen_test_groups.py` | in repo | regenerate the Makefile/hook listings | after adding test modules |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Own splicer | `tomlkit`/`tomli_w` | adds a dependency and breaks stdlib-only (AGENTS.md); rejected |
| gsd-core `.lock` | byte-compare before rename | cannot close the window; lock reuses gsd-core's own protocol |

**Installation:** none. No package is installed by this phase.

**Version verification:** no external package is recommended, so no registry check applies.

## Package Legitimacy Audit

No external package is installed or recommended in this phase (stdlib, node built-ins, in-repo tools only). Audit table: none. Packages removed (SLOP): none. Packages flagged (SUS): none. `gsd_run query package-legitimacy check` was not run because there is nothing to check.

## Architecture Patterns

### System Architecture Diagram

```
 any roster reader (cfg_resolve / trust-local / render-toml)          check paths (check-providers, --check-only)
            |                                                                  |
            v                                                                  v
   config_migrate.ensure_migrated(cwd, env)  -- once per process --      config_migrate.peek_legacy() (read-only)
     per layer (project, user):                                                |  report "migration pending"
       old review-spec.toml present?                                           v
        |no -> nothing                                              provider_check reads legacy bytes, never writes
        |yes, new absent -> parse old (ConfigError exit 2 on bad)
              copy bytes -> temp in same dir -> os.link(temp, lanes.toml)  [EEXIST: another process won, skip]
              re-read new, compare bytes
              project layer only: if is_trusted(old store, realpath(old), raw): record_trust(lanes-trust, realpath(new), raw)
              rename old -> review-spec.toml.migrated ; print ONE notice (both paths)
        |yes, new present, bytes equal -> finish interrupted run (trust carry + rename), see Pitfall 4
        |yes, new present, bytes differ -> new wins; report old on each run; never merge
            |
            v
   layered_config.load_layered("lanes.toml", cwd, env, parse, gate=trust, skip_user_if=local-only)
            |                                  \-> merge_layers(user, project)  (dicts per key, rest replaced)
            v
   cfg_combine domain merge ([[reviewers]] by key, policy ladder)  -> {"policy","reviewers"}

 writers:  render-toml --out lanes.toml --replace --> toml_splice.splice(old_text, new_cfg) -> tomllib re-parse == intended
                                                      -> cache_write_bytes (mkstemp, fsync, os.replace, fsync dir)

 runner (node), every run, before the tree snapshot:
   resolveRetry(cwd, env):
     0. migrateGsdBlocks(cwd, env)   for each file of scopedConfigPaths (confined to <cwd>/.planning, realpath):
          block absent -> nothing (a GSD file without the block is never written)
          block present and file already in migrated_from -> ignore + one-line notice naming the file
          else: (1) merge values into .aikit/cross-ai.json (ai-kit keys win, conflicting GSD value named in notice)
                (2) lock <dir>/.lock (wx), re-read, remove member with span scanner, re-parse check, temp beside realpath, rename, unlock
                (3) append file to migrated_from, write .aikit/cross-ai.json (temp + rename)
     1. sources per key: .aikit/cross-ai.json[scopes[label]] then top-level -> user cross-ai.json -> CONFIG.retry -> RETRY_DEFAULTS
```

### Recommended Project Structure
```
skills/ai-kit-spec-review/ai_kit_spec/
  layered_config.py   # layer_paths, merge_layers, load_layered (reusable; Phase 34 copies)
  toml_splice.py      # scan/segment/splice + tomllib equality gate
  config_migrate.py   # the only runtime code naming review-spec.toml / review-spec-trust
  cache.py            # + fsync of file and folder in cache_write_bytes
docs/config/design.md             # the record (D-04), inventory rows with exactly one assignment token
tests/test_config_*.py, test_toml_splice.py, test_atomic_publish.py   # see Q9
```

### Pattern 1: per-key layered merge with one stated exception
**What:** project over user per key, dict values merge, anything else replaces; `strategy = "local-only"` skips the user file. **When:** every `<name>` file at both layers. **Example:** `_combine_layers`/`cfg_combine` at `config_io.py:418-450` (read this session).

### Pattern 2: migration as a resumable state machine
**What:** the five D-10 steps are idempotent individually; the observable states are `{old only, new only, both-equal, both-different, neither}`. `both-equal` means an interrupted run and is finished (trust carry, rename); `both-different` is "new wins, old reported". **Why:** otherwise a cut between `os.link` and the trust record leaves a previously trusted project roster untrusted forever (fail-safe but a regression for the user, and R5's concurrency edge wants "at least one valid trust"). Order stays: trust record written before the old file is renamed.

### Pattern 3: temp beside target, fsync, rename (all writers)
Python: `cache_write_bytes` (`cache.py:27-42`): add `f.flush(); os.fsync(f.fileno())` before `os.replace`, then fsync the parent directory; new files `0600` through the existing `mode` argument (D-08). JS: copy `writeCycleState` (`cross-ai.mjs:3410-3423`) and add `fs.fsyncSync(fd)` before close. Status-line recovery: replace `shutil.copyfile(sample, cfg)` (`setup.py:3497`) by a temp-file publish; `_atomic_write_executable` (`setup.py:1122-1135`) is the nearest helper (mkstemp in the target dir, `os.replace`) but sets `0o755`: add a `mode` parameter (default `0o755`) rather than writing a second helper; keep `shutil.copyfile(cfg, bak)` for the backup.

### Pattern 4: JS span scanner for `workflow.cross_ai_retry`
Port the classifier idea of `_find_top_level_key_span` (`config_doctor_appliers.py:312-350`) but generalised to "member `K` of the object that is the value of top-level `P`": scan the text with a minimal JSON tokenizer (strings with `\` escapes, braces/brackets depth, no comments since GSD parses with `JSON.parse`), find the depth-1 member `workflow` (refuse and skip the migration when the key occurs twice at that depth: `JSON.parse` keeps the last, a scanner would take the first), then inside its object the depth-2 member `cross_ai_retry`. Remove `key_start .. value_end` plus: the following comma and whitespace if a comma follows; else the preceding comma and whitespace; plus the member's own indentation and newline when the member sits on its own line (so pretty-printed files get no blank line). Gate: `JSON.parse(result)` must deep-equal `JSON.parse(original)` minus that key (compare `JSON.stringify` of both), else abort without writing. An empty object `{}` block migrates nothing and is still removed (SPEC R7 empty edge). Write the temp beside `fs.realpathSync(file)` so a symlinked `config.json` stays a link, only when the realpath stays inside `<cwd>/.planning` (reuse `confinementError`, `cross-ai.mjs:3036-3051`).

### Pattern 5: new runner file shape
`.aikit/cross-ai.json`: `{"cross_ai_retry": {...}, "scopes": {"<label>": {"cross_ai_retry": {...}}}, "migrated_from": ["<relative path of each migrated GSD file>"]}`; reads go through the existing `readJsonObject(file, <cwd>/.aikit)` (confined, 1 MiB cap, regular file). Unknown keys are ignored on read and preserved on write (parse, set own keys, stringify; the file is tool-owned JSON with no comments, so a whole-object rewrite is lossless apart from layout, which a user hand-edit may change: keep layout 2-space JSON plus final newline).

### Anti-Patterns to Avoid
- Reusing `_KEY_RE` on roster values (breaks on `#` in strings).
- Writing the marker with the values (a cut leaves the GSD block forever; D-14 says marker last).
- Reading the GSD block as a fifth live source (D-12 says the runner never reads it again after migration).
- Calling migration from `check-providers` or `--check-only` (promised read-only).
- Putting a temp file in `os.tmpdir()` for the migration (trips the per-case TMPDIR assertion and leaks on a crash).
- A new dev dependency for TOML or locking.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic publish (Python) | a second temp/rename helper | `ai_kit_spec.cache.cache_write_bytes` (+fsync) | already used by trust, render-toml, curated-config |
| Publish-if-absent | own locking | `create_if_absent` pattern (`os.link`, `tools/setup.py:2752-2783`) | race-free, tested |
| Trust record format | new trust scheme | `trust.record_trust/is_trusted` as is | D-11: rule unchanged, key = realpath + raw sha |
| Runner config confinement and size cap | new reader | `readJsonObject` / `confinementError` | already handles FIFO, symlink-out, 1 MiB |
| Planning lock | custom lock protocol | gsd-core's `wx` `.lock` with `{pid,cwd,acquired}` body | gsd-tools honours it and steals dead holders |
| Resolver | a fifth copy per call site | one function per code boundary + parity test | D-17 |
| Judge loop | new scripts | `tools/judge_loop.py` verbs + copied `tmp/judge-32.4` drivers | proven in loops 32.1-32.4 |

**Key insight:** every hard part (atomic publish, trust, confinement, lock) already exists; the phase is wiring, one splicer and one JS span scanner.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Roster files `.aikit/review-spec.toml` (project) and `<xdg>/ai-kit/review-spec.toml` (user); trust records `<xdg>/ai-kit/review-spec-trust/<sha>.json` (`path`, `sha256`, `trusted_at`) [VERIFIED: `trust.py:44-53`]; this machine has all three (inventory, names only) | data migration by `config_migrate` (copy, carry trust, rename to `.migrated`); never run on the real home during execution |
| Live service config | GSD `.planning/config.json` `workflow.cross_ai_retry`: none present in this project (`rg` of `.planning/config.json` shows only `cross_ai_timeout`, line 47) [VERIFIED]; other projects unknown | runtime migration by the runner on first call; no manual step |
| OS-registered state | none: no systemd unit, task or hook names the roster or retry files (the session-wake units are unrelated) | none - verified by rg of `skills`/`tools` for the old names (25 Python lines, all code/doc, no registration) |
| Secrets/env vars | `secrets.env` location resolves differently in `local_secrets` (ignores `XDG_CONFIG_HOME`) vs `jev_review`; env names `JEV_*`, `GSD_PATH_JEV` unchanged | code edit (resolver parity, R9); no secret value is ever copied into a config file (prohibition test) |
| Build artifacts | `.planning/scripts/cross-ai.mjs` is a stamped render of the template and goes stale after the template edit; `tests/fixtures/cross_ai_selftest_secs.json`, `E2E_RECORDED_SECS`, the generated test listings in `Makefile`/`.pre-commit-config.yaml`, `.planning/judge/*` | re-render via `ensure-runner`, refresh timings, run `gen_test_groups.py`, judge loop |

**Canonical question answered:** after every repo file is updated, the live systems still holding the old name are the user's `review-spec.toml` files and `review-spec-trust/` records (migrated on first run, kept as `.migrated` and in the old store which only the migration reads) and any GSD `config.json` with the old block (removed on the first runner call).

## Common Pitfalls

### Pitfall 1: `#` inside a quoted value
**What goes wrong:** key-line rewriting with `_KEY_RE` truncates or duplicates `command = "... # ..."` and `model = "a/b#variant"`. **Avoid:** quote-aware statement scanner; test both lines. **Warning sign:** re-parse equality gate fails.

### Pitfall 2: top-level key written after a header
**What goes wrong:** appending `strategy = ...` at EOF nests it under the last `[[reviewers]]`. **Avoid:** insert into the preamble.

### Pitfall 3: `[reviewers.extra]` sub-tables
**What goes wrong:** treating a sub-table block as a separate entry, so entry matching and slot placement break. **Avoid:** group `[reviewers.*]` blocks with the preceding entry (verified tomllib semantics).

### Pitfall 4: interrupted migration widens or loses trust
**What goes wrong:** cut between `os.link` and the trust record leaves new file present, trust missing; next run treats it as "both present, new wins" and the previously trusted roster is untrusted. **Avoid:** equal bytes = resume; also write the trust record before renaming the old file.

### Pitfall 5: realpath differs between old and new file
**What goes wrong:** trust keys use `os.path.realpath`; if `.aikit` is a symlink or the new path is built from a non-real cwd, a record keyed on the wrong path never matches. **Avoid:** always `realpath` the new path after publishing; test with a symlinked `.aikit`.

### Pitfall 6: runner migration in the middle of concurrent lanes
See Q1: lock, re-read under lock, skip on timeout; document the one-time `tree=dirty` effect on in-flight review lanes.

### Pitfall 7: symlink and confinement on a write
`readJsonObject` refuses a config that resolves outside its root; the migration write must apply the same rule to the GSD file (`<cwd>/.planning`) and to `.aikit/cross-ai.json` (`<cwd>/.aikit`), else a stow-style link makes the runner rewrite a file outside the project.

### Pitfall 8: existing self-test cases assert `.planning/config.json` bytes and mtime unchanged
`retry-config-read-only` (`cross-ai.mjs:9198-9248`) would now fail by design; rewrite it as the "second run writes nothing" case.

### Pitfall 9: doc tests pin retry text
`tests/test_cross_ai_skill_text.py:194,299-315` fail when `subprocess-quota-policy.md` changes; update them in the same plan as the doc.

### Pitfall 10: `tomllib` and encoding
Old files are read as UTF-8 TOML; a BOM or non-UTF-8 stops with `ConfigError` before any write (SPEC encoding edge). Byte-copy keeps the BOM in `lanes.toml`.

## Code Examples

### Lock around the GSD block removal (runner)
```js
// Source: lock protocol read in .claude/gsd-core/bin/lib/planning-workspace.cjs:384-425
function withGsdLock(configRealPath, fn) {
  const lock = path.join(path.dirname(configRealPath), '.lock');
  const body = JSON.stringify({ pid: process.pid, cwd: process.cwd(), acquired: new Date().toISOString() });
  const deadline = Date.now() + 2000;
  for (;;) {
    try { fs.writeFileSync(lock, body, { flag: 'wx' }); break; }
    catch (e) {
      if (e.code !== 'EEXIST' || Date.now() > deadline) return { skipped: e.code || 'lock busy' };
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 50);
    }
  }
  try { return { value: fn() }; } finally { try { fs.unlinkSync(lock); } catch { /* gone */ } }
}
```

### Interruption test shape (Python writers)
```python
# patch os.replace to raise, call the writer, assert the old file bytes are unchanged and no temp file is left
with mock.patch("os.replace", side_effect=OSError("boom")):
    with self.assertRaises(OSError): cache_write_bytes(path, b"new")
self.assertEqual(open(path, "rb").read(), b"old")
self.assertEqual([n for n in os.listdir(folder) if n.endswith(".tmp")], [])
```

### Resolver parity case table
```python
CASES = [("/abs/cfg", "/home/u"), ("rel/cfg", "/home/u"), ("", "/home/u"), ("  ", "/home/u"), ("/home/u/.config", "/home/u"), ("", None)]
# every copy returns an absolute path or the string "no-home"; the node copy runs through a tiny node -e script
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Roster in `review-spec.toml`, retry in GSD `workflow.cross_ai_retry` | one file per concern, same name at both layers (`lanes.toml`, `cross-ai.json`, later `config.toml`) | this phase | callers, docs, tests move |
| Runner "writes nothing" invariant | runner migrates and removes the GSD block once | this phase (D-13) | new write paths need lock, confinement, tests |
| Full-rewrite roster writer | region splicer with re-parse gate | this phase (D-07) | comments survive saves |

**Deprecated/outdated:** the `review-spec-trust/` store and `review-spec.toml` (kept as `.migrated`/old records, read only by the migration); `cfg_write_toml` (test-only).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The owned-key set for the splicer (Q3 item 5) is complete against the wizard's output keys | Q3 | an unlisted owned key would be treated as unknown and never updated or deleted |
| A2 | referee-one passes its probe and is usable as a judge | Q10 | loop falls back to one usable referee with a recorded reason (allowed by D-19) |
| A3 | A harness one-liner `python3 -c` calling `tests/cross_ai_selftest.run_cases(names)` works from the repo root for single-case runs | Validation | the executor falls back to the shard modules (documented) |
| A4 | Adding about a dozen `logic` cases keeps each shard under the 60 s commit budget | Q4 | a shard is deferred to push; acceptable, no correctness impact |
| A5 | `gsd-tools config-set` family writers always run with the same `GSD_PROJECT`/`GSD_WORKSTREAM` env as the scope whose file they edit, so the lock directory equals `dirname(config.json)` | Q1 | a writer under a different env locks a different file; the window reopens only for that mismatched writer |
| A6 | Freshly migrated notice lines and the `scopes` label scheme (Open Question 1) match the owner's intent | Q6/Pattern 5 | wrong label means a workstream's block is read under another scope |

## Open Questions

1. **`scopes` mapping and read order (D-15 wording)**
   - Known: today's ladder is workstream file, then root file only under a workstream; a project-only scope reads only the project file.
   - Unclear: D-15 says the top-level key comes "from the project or root GSD file" and `scopes` is "read before the top-level key for the active scope".
   - Recommendation: root file's block -> top-level `cross_ai_retry`; every other scoped file's block -> `scopes[<label>]`; read order per key: `scopes[activeLabel]`, then top-level only when there is no scope or a workstream is set (reproduces today's behaviour exactly, including "project-only scope ignores the root block"). Planner records this in the record doc and the notice; a deviation changes nothing for projects without the block (today's state here).
2. **Review-mode runs and the tracked-file edit**
   - Known: migration edits tracked `.planning/config.json` once; the migrating process's own snapshot is later (`:10761` after `:10677`).
   - Unclear: whether judge/review lanes should skip the migration to stay read-only.
   - Recommendation: migrate in every mode (single behaviour, simplest), document the one-time `tree=dirty` effect on concurrent in-flight lanes; no project here has the block.
3. **Symlinked `config.json` pointing outside `.planning`**
   - Known: today's retry read refuses it; D-13 says a symlinked config stays a link.
   - Recommendation: honour confinement for the write too (skip with a one-line notice when the realpath leaves `<cwd>/.planning`; an in-tree link is followed and stays a link). Rewrite `retry-config-outside` accordingly. Needs a quick owner nod only if the owner stows `.planning` out of tree.
4. **spec-config regression base** - D-19 says "lowest 77.6 C"; `REJUDGE.md:20` shows worst 79.2 C and 77.6 only inside the reason cell. Let `judge_loop.py count` print the base; do not hand-copy either number.
5. **Not verified by a run:** the splicer and the JS span scanner (designed here, no prototype), the `run_cases` one-liner, the runtime behaviour of the node `Atomics.wait` poll inside the runner (the runner is async; a busy sync wait of at most 2 s at startup is acceptable but unmeasured).
6. **Real-home migration** - the first real run after shipping migrates the owner's real roster files and trust records. Execution never touches them (rails); the orchestrator should plan the live re-check on a scratch HOME and tell the owner what the first real run will print.

## Orchestrator resolutions (locked before planning)

Decided by the orchestrator through the jev ladder (advisory; `tmp/p33-plan/jev-open-q*.out.json`) after checking the
cited source. Plans treat these like CONTEXT decisions.

1. **`scopes` mapping (Open Question 1):** the root GSD file's block goes to the top-level `cross_ai_retry`; every other
   scoped file's block goes to `scopes[<label>]` with the labels of D-15. Per key the runner reads `scopes[activeLabel]`,
   then the top-level key only where today's ladder reads the root file (no scope, or a workstream set), then the user
   `cross-ai.json`, `CONFIG.retry`, `RETRY_DEFAULTS`. jev q1: typesafe `root_top_level_others_in_scopes` 0.86 (laya
   low 0.41).
2. **Every mode migrates (Open Question 2):** the runner migrates in review and execute mode alike; the record and the
   runner reference state the one-time dirty-tree effect on a concurrent lane. jev q2: laya yes 0.91.
3. **Confinement holds for writes (Open Question 3):** a `config.json` whose realpath leaves `<cwd>/.planning` is
   neither read nor written; one notice names it; an in-tree link is followed and stays a link. The
   `retry-config-outside` self-test case is rewritten to assert this. jev q3: laya yes 0.81.
4. **Lost-update guard (Q1):** the runner takes gsd-core's own lock (`<dirname(config.json)>/.lock`, created with flag
   `wx`, the protocol of `withPlanningLock`, `.claude/gsd-core/bin/lib/planning-workspace.cjs:384-425`), re-reads the
   file under it, removes the block, writes temp beside the realpath, renames, and removes the lock in `finally`; it
   never steals a lock; after about 2 s of waiting it skips the removal for this run with a notice (the values are
   already merged, D-14 step 1, so the next run finishes). A byte compare before rename is not used. jev q4: typesafe
   `take_gsd_wx_lock_skip_on_timeout` 0.97 (laya low 0.49, same choice).
5. **Regression base (Open Question 4):** the judge plan takes each skill's base from `python3 tools/judge_loop.py
   count` output, never from a number copied into the plan.
6. **Leak fix first (Q5):** the /tmp-leak fix is commit `a25784c` on branch `fix/cross-ai-tmp-leak` (template, dogfood
   copy, `tests/cross_ai_selftest.py`); it lands on this branch before execution. Runner plans start by checking for it
   and stop if it is absent; after it lands, the dogfood copy is re-rendered, never hand-merged.
7. **Test registration:** every plan that adds a `tests/test_*.py` module runs `python3 tools/gen_test_groups.py` and
   commits the regenerated `Makefile` and `.pre-commit-config.yaml` listings with it (`tests/test_gate_scope.py`).
8. **Judges (D-19):** the judge plan copies 32.4-07's drivers but drops every native-opus path (`NATIVE`, `--native`,
   `natives.txt`); the pool is referee-one and referee-two with referee-three as the replacement lane.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| node | runner migration, self-test, check-dogfood | yes | v24.21.0 | none (self-test shards skip without node) |
| python3 | all Python code and tests | yes | 3.15.2 on PATH; project pin 3.12 via uv | uv env for pinned runs |
| codegraph CLI | code mapping | yes | 1.6.2 | rg |
| git | self-test, judge loop | yes | not probed | - |
| gsd-core (project-local) | lock/protocol facts, ensure-runner | yes | read only | - |
| referee-one/two/three (opencode via router-env) | loop `33` | not probed here | - | one usable referee accepted; zero stops the round |

**Missing dependencies with no fallback:** none found.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `unittest` through `tools/run_unittest_parallel.py`; node self-test harness for the runner |
| Config file | none (`pyproject.toml` pins py312; generated group listings in `Makefile` and `.pre-commit-config.yaml`) |
| Quick run command | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_toml_splice tests.test_config_migrate tests.test_config_layered tests.test_config_design_record tests.test_config_doc_names tests.test_config_dir_parity tests.test_atomic_publish` |
| Runner self-test (shards) | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_cross_ai_selftest_logic_1_e2e tests.test_cross_ai_selftest_logic_2_e2e tests.test_cross_ai_selftest_logic_3_e2e tests.test_cross_ai_selftest_logic_4_e2e tests.test_cross_ai_selftest_runtime_1_e2e tests.test_cross_ai_selftest_runtime_2_e2e tests.test_cross_ai_selftest_runtime_3_e2e tests.test_cross_ai_selftest_runtime_4_e2e` |
| One new case while writing it | a `tmp/` script calling `tests.cross_ai_selftest.run_cases([<case names>])` (A3), or `AIKIT_XAI_SELFTEST_CASES=<names> node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test` with the harness env |
| Existing roster tests moved to new paths | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec tests.test_ai_kit_spec_legacy_config tests.test_ai_kit_spec_trust tests.test_ai_kit_spec_routing tests.test_ai_kit_spec_check_providers tests.test_ai_kit_spec_superpowers tests.test_cross_ai_skill_text tests.test_gate_scope tests.test_check_dogfood tests.test_setup` |
| Full suite command | `make test` (orchestrator only; research did not run it) |
| Dogfood | `python3 tools/check_dogfood.py` after `ensure-runner --cwd .`; `make check-dogfood` by the orchestrator |
| Judge records | `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/judge_loop.py check .planning/judge` and the scoped `--require-current --gate` form |

### Phase Requirements -> Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| R1 | record lists every settings file name from the path functions; every row has exactly one assignment | unit | `... tests.test_config_design_record` | Wave 0 |
| R2 | per-key precedence, empty = defaults with no file, names lowercase ASCII without `review-spec`/host name, idempotent resolve | unit | `... tests.test_config_layered tests.test_config_design_record` | Wave 0 |
| R3 | unknown section/key (also empty section, ordering) read without error and kept byte for byte through one-key write | unit | `... tests.test_toml_splice` | Wave 0 |
| R4 | local, global, both, `local-only`, comments + legacy fields, second run no byte change, old+new present, empty old, malformed/non-UTF-8 stops exit 2, interruption after new write | unit (scratch HOME) | `... tests.test_config_migrate` | Wave 0 |
| R5 | trusted custom `command` stays runnable, untrusted stays inert; resume from both-equal | unit | `... tests.test_config_migrate` | Wave 0 |
| R6 | no runtime code or doc names `review-spec.toml`/`review-spec-trust` outside migration code/notes; existing roster tests pass on new paths | unit | `... tests.test_config_doc_names` + moved roster tests | Wave 0 + edit |
| R7 | project and workstream migration, block removal keeps other bytes, re-added block ignored with notice, second run no write, precedence across three sources, invalid key falls through, empty block, no-block file never written, symlinked config stays a link, conflicting key keeps ai-kit value | runner self-test | the shard command above | new cases in template |
| R8 | per writer: diff limited to the written key, interrupted write leaves the old file, recovery never writes the live file in place, new file `0600`, concurrent lock skip | unit + self-test | `... tests.test_atomic_publish tests.test_toml_splice tests.test_setup` | Wave 0 + edit `test_setup.py:3420-3477` |
| R9 | resolver parity on absolute/relative/empty/whitespace XDG and no home across Python copies and the node copy; `load_secret` and jev read one `secrets.env` | unit | `... tests.test_config_dir_parity` | Wave 0 |
| R10 | changed SKILL.md bar results, records valid | judge loop | `judge_loop.py check` forms above | records written by loop `33` |
| prohibitions | a seeded secret appears in no written file; untrusted command inert; old content kept until new re-read | unit | migration + record tests | Wave 0 |

### Sampling Rate
- **Per task commit:** the quick command for the touched module plus the moved roster tests.
- **Per wave merge:** the shard command (runner changes) and the moved-roster group.
- **Phase gate:** `make test` green, `check-dogfood: ok`, `judge_loop.py check` exit 0, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] the seven new test modules above, plus `python3 tools/gen_test_groups.py` and committing the regenerated listings
- [ ] updated roster tests (eight files, Q7) and `tests/test_cross_ai_skill_text.py:194,299-315`
- [ ] new self-test cases in the template; refreshed `tests/fixtures/cross_ai_selftest_secs.json` and `E2E_RECORDED_SECS`
- [ ] Framework install: none

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | - |
| V3 Session Management | no | - |
| V4 Access Control | yes | trust gate on the project roster only (`lanes.toml`); rule "a key that names a command to run lives only in `lanes.toml`" |
| V5 Input Validation | yes | `tomllib` strict parse (exit 2), `validateRetryKey` bounds, re-parse equality gates for both splicers |
| V6 Cryptography | no (sha256 trust key unchanged, stdlib) | `hashlib` as today |
| V12 File handling | yes | temp + fsync + rename, `0600` new files, realpath confinement for runner reads and writes, never follow a link out of the tree |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A cloned repo ships `.aikit/lanes.toml` with a `command` | Elevation | trust record keyed on realpath + raw bytes; migration carries trust only if the old file was trusted; untrusted stays inert |
| A cloned repo ships `.aikit/cross-ai.json` with huge `hard_waits_s` | DoS | same bounds as today (`validateRetryKey`, `capS` clamp 14400); no command-bearing key allowed in this file |
| Symlinked `config.json` or `.aikit/cross-ai.json` out of tree | Tampering | confinement check on write, refuse and log |
| Secret copied into a config by migration | Disclosure | byte copy of a file that holds no secrets by rule; test seeds an env/`secrets.env` secret and asserts it appears in no written file |
| Torn write on crash | Tampering/Availability | temp beside target, fsync, `os.replace`/`renameSync`; old file untouched on failure |
| Lost update against `config-set` | Tampering | gsd-core `.lock` around the block removal |

## Sources

### Primary (HIGH confidence, read or run this session)
- `skills/ai-kit-spec-review/references/cross-ai.mjs` (lines cited above); `tests/cross_ai_selftest.py`; `tools/run_unittest_parallel.py`; `tools/check_dogfood.py`; `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py`, `cli.py`.
- `skills/ai-kit-spec-review/ai_kit_spec/config_io.py`, `trust.py`, `cache.py`, `provider_check.py`, `cli.py`, `local_secrets.py`; `skills/jev-fast-decision/scripts/jev_review.py`; `tools/setup.py`, `tools/common_config.py`, `tools/config_doctor_appliers.py`.
- gsd-core (project-local, read only): `bin/lib/config.cjs`, `planning-workspace.cjs`, `shell-command-projection.cjs`, `config-loader.cjs`, `configuration.cjs`, `health-diagnostic.cjs`, `workflows/execute-phase.md`, `workflows/review.md`, `references/reviewer-instances.md`, `bin/shared/config-schema.manifest.json`.
- Live runs: `tmp/p33-plan/research/gsd_probe.sh` (config-set refusal, unknown key survives a write), `tmp/p33-plan/research/keyre_probe.py` (`_KEY_RE` mis-parse, tomllib sub-table semantics), `node cross-ai.mjs --self-test-list`.
- `git diff eabcd1a a25784c` (leak fix); `.planning/phases/32.4-.../32.4-07-PLAN.md`; `.planning/judge/REJUDGE.md`; `tmp/judge-32.4/lanes.py`, `judged.py`.

### Secondary / Tertiary
- none; no web source was used (all claims are about this repository and its project-local gsd-core).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependency, all helpers read in the tree.
- Architecture: MEDIUM-HIGH - the splicer and JS scanner are designs with named tests, not yet run.
- Pitfalls: HIGH for 1-3 and 7-9 (verified by run or read), MEDIUM for 4-6 (reasoned from the code).

**Research date:** 2026-11-13
**Valid until:** 2026-12-13 (gsd-core is project-local and pinned; revisit if the leak-fix branch lands or gsd-core is upgraded)
